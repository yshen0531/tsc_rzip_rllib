#!/usr/bin/env python3
"""Independent Stage4.2R3b raw closed-loop control forensics.

Run this tool on the server.  It reads the large raw result tree in place and
writes only compact recomputed metrics.  It never edits the experiment run.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3b_confirmatory_hidden_history_initial_state as r3,
)


FORMAL_MARGIN_KEYS = {
    "position": "position_signed_margin",
    "endpoint_speed": "endpoint_speed_signed_margin",
    "endpoint_late_speed": "endpoint_late_speed_signed_margin",
    "post_speed": "post_speed_signed_margin",
    "final_speed": "final_speed_signed_margin",
    "ip_safety": "ip_signed_margin",
    "ip_terminal": "stage3_4_ip_terminal_signed_margin",
    "ip_hold_rms": "stage3_4_ip_hold_rms_signed_margin",
    "ip_sustained": "stage3_4_ip_sustained_signed_margin",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_digest(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _finite_range(values: Iterable[float]) -> dict[str, float | None]:
    array = np.asarray(
        [float(value) for value in values if math.isfinite(float(value))],
        dtype=float,
    )
    if not array.size:
        return {"minimum": None, "maximum": None, "mean": None}
    return {
        "minimum": float(np.min(array)),
        "maximum": float(np.max(array)),
        "mean": float(np.mean(array)),
    }


def _read_raw(directory: Path) -> tuple[list[Path], list[dict[str, Any]]]:
    paths = sorted(directory.glob("*.json.gz"))
    return paths, [r3.read_json_gz(path) for path in paths]


def _recompute_selected_pairs(
    ctx: r3.Stage42R3BContext,
    state_results: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    state_rows = [r3._state_row(result) for result in state_results]
    state_by_id = {
        str(row["experiment_id"]): row for row in state_rows
    }
    by_pair: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in state_rows:
        by_pair[str(row["pair_id"])][str(row["history_order"])] = row
    pair_rows: list[dict[str, Any]] = []
    for pair_id in sorted(by_pair):
        members = by_pair[pair_id]
        if set(members) != {"plus_first", "minus_first"}:
            raise RuntimeError(f"incomplete raw state pair: {pair_id}")
        pair_rows.append(
            r3._pair_metrics(
                members["plus_first"],
                members["minus_first"],
                ctx.cfg["pair_gate"],
            )
        )
    accepted = [row for row in pair_rows if bool(row.get("accepted"))]
    selected: list[dict[str, Any]] = []
    prefixes = map(
        int,
        ctx.cfg["state_generation"]["common_prefix_source"][
            "prefix_lengths"
        ],
    )
    directions = list(
        map(
            int,
            ctx.cfg["state_generation"]["nullspace_direction_indices"],
        )
    )
    for prefix in prefixes:
        for direction in directions:
            candidates = [
                row
                for row in accepted
                if int(row["common_prefix_steps"]) == prefix
                and int(row["nullspace_direction_index"]) == direction
            ]
            if not candidates:
                continue
            candidates.sort(
                key=lambda row: (
                    -float(row["wire_relative_rms_difference"]),
                    -float(row["wire_rms_difference_A"]),
                    -float(row["wire_max_abs_difference_A"]),
                    float(row["visible_max_normalized_ratio"]),
                    float(row["amplitude_fraction"]),
                    -int(row["gap_steps"]),
                    str(row["pair_id"]),
                )
            )
            selected.append(copy.deepcopy(candidates[0]))
    frozen = r3._frozen_initial_state(ctx)
    for pair in selected:
        pair.update(
            r3._different_initial_metrics(
                pair, frozen, ctx.cfg["different_initial_state_gate"]
            )
        )
    return selected, state_by_id


def _r8_context(ctx: r3.Stage42R3BContext) -> Any:
    r13_ctx = r3.r1._r13_ctx(ctx.r1_ctx)
    return r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx


def _timing_policy(
    ctx: r3.Stage42R3BContext,
    spec: Mapping[str, Any],
) -> dict[str, Any]:
    return r3.r1.r13._timing_policy(
        r3.r1._r13_ctx(ctx.r1_ctx),
        float(spec["slew_scale"]),
        policy_id=(
            f"r42r3b_forensics_{spec['pair_id']}_"
            f"{spec['history_member']}_{spec['target_id']}_"
            f"{spec['action_delay_steps']}_{spec['slew_scale']}"
        ),
    )


def _formal_metrics(
    ctx: r3.Stage42R3BContext,
    result: Mapping[str, Any],
) -> dict[str, Any]:
    r8_ctx = _r8_context(ctx)
    return r3.r1.r8.tracking_metrics(
        r8_ctx,
        result,
        _timing_policy(ctx, result["spec"]),
    )


def _absolute_target(
    ctx: r3.Stage42R3BContext,
    spec: Mapping[str, Any],
) -> np.ndarray:
    r8_ctx = _r8_context(ctx)
    base34 = (
        r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34
    )
    metric_ctx = SimpleNamespace(
        cfg=copy.deepcopy(base34.cfg),
        env_cfg=base34.env_cfg,
    )
    metric_ctx.cfg["gate"].update(copy.deepcopy(r8_ctx.cfg["gate"]))
    return np.asarray(
        r3.r1.r8.s34.target_absolute(
            metric_ctx, r3.r1.r8._target_task(spec)
        ),
        dtype=float,
    ).reshape(3)


def _formal_decomposition(
    formal: Mapping[str, Any],
) -> dict[str, Any]:
    endpoint_rows = list(formal["stage3_4_endpoint_evaluations"])
    chosen_step = int(formal["stage3_4_best_endpoint_step"])
    chosen = next(
        row
        for row in endpoint_rows
        if int(row["endpoint_step"]) == chosen_step
    )
    margins = {
        name: float(chosen[key])
        for name, key in FORMAL_MARGIN_KEYS.items()
    }
    best_by_component = {
        name: max(float(row[key]) for row in endpoint_rows)
        for name, key in FORMAL_MARGIN_KEYS.items()
    }
    limiting = min(margins, key=margins.get)
    return {
        "formal_pass": bool(formal["stage3_4_target_tracking_pass"]),
        "minimum_signed_margin": float(
            formal["stage3_4_tracking_minimum_signed_margin"]
        ),
        "chosen_endpoint_step": chosen_step,
        "chosen_arrival_ms": int(formal["stage3_4_best_endpoint_ms"]),
        "chosen_component_margins": margins,
        "chosen_limiting_component": limiting,
        "chosen_violated_components": sorted(
            name for name, value in margins.items() if value < -1e-12
        ),
        "best_margin_by_component_over_allowed_endpoints": best_by_component,
        "unavoidable_violated_components": sorted(
            name
            for name, value in best_by_component.items()
            if value < -1e-12
        ),
        "terminal_R_error_m": float(formal["terminal_R_error_m"]),
        "terminal_Z_error_m": float(formal["terminal_Z_error_m"]),
        "terminal_Ip_error_A": float(formal["terminal_Ip_error_A"]),
        "terminal_velocity_m_per_s": float(
            formal["terminal_velocity_m_per_s"]
        ),
        "late_velocity_rms_m_per_s": float(
            formal["late_velocity_rms_m_per_s"]
        ),
        "sustained_box_max_error_m": float(
            formal["stage3_4_sustained_box_max_error_m"]
        ),
        "sustained_Ip_safety_max_error_A": float(
            formal["stage3_4_sustained_Ip_safety_max_error_A"]
        ),
        "ip_terminal_abs_error_A": float(
            formal["stage3_4_ip_terminal_abs_error_A"]
        ),
        "ip_hold_rms_error_A": float(
            formal["stage3_4_ip_hold_rms_error_A"]
        ),
        "ip_sustained_max_error_A": float(
            formal["stage3_4_ip_sustained_max_error_A"]
        ),
        "max_current_utilization": float(formal["max_current_utilization"]),
    }


def _trajectory_diagnostics(
    ctx: r3.Stage42R3BContext,
    result: Mapping[str, Any],
    source: Mapping[str, Any],
    target: np.ndarray,
) -> dict[str, Any]:
    trajectory = list(result["trajectory"])
    source_trajectory = list(source["trajectory"])
    horizon = int(result["spec"]["horizon_steps"])
    source_trajectory = source_trajectory[: horizon + 1]
    y = np.asarray(
        [[row["R"], row["Z"], row["Ip"]] for row in trajectory],
        dtype=float,
    )
    source_y = np.asarray(
        [[row["R"], row["Z"], row["Ip"]] for row in source_trajectory],
        dtype=float,
    )
    currents = np.asarray(
        [row["currents_a_tsc"] for row in trajectory], dtype=float
    )
    source_currents = np.asarray(
        [row["currents_a_tsc"] for row in source_trajectory], dtype=float
    )
    action = np.asarray(
        [row["action_norm_tsc"] for row in trajectory[1:]], dtype=float
    )
    source_action = np.asarray(
        [row["action_norm_tsc"] for row in source_trajectory[1:]],
        dtype=float,
    )
    r8_ctx = _r8_context(ctx)
    dt_ms = int(
        r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34.env_cfg["dt_ms"]
    )
    ip_scale = float(r8_ctx.cfg["gate"]["ip_safety_tolerance_A"])
    rzi_scale = np.asarray([0.03, 0.03, ip_scale], dtype=float)
    coil_scale = float(
        ctx.cfg["different_initial_state_gate"][
            "coil_centroid_rms_difference_A_min"
        ]
    )
    rzi_distance = np.sqrt(
        np.mean(((source_y - y[0][None, :]) / rzi_scale[None, :]) ** 2, axis=1)
    )
    full_delta = np.concatenate(
        [
            (source_y - y[0][None, :]) / rzi_scale[None, :],
            (source_currents - currents[0][None, :]) / coil_scale,
        ],
        axis=1,
    )
    full_distance = np.sqrt(np.mean(full_delta**2, axis=1))
    nearest_rzi_step = int(np.argmin(rzi_distance))
    nearest_full_step = int(np.argmin(full_distance))
    error = y - target[None, :]
    box_error = np.max(np.abs(error[:, :2]), axis=1)
    source_error = source_y - target[None, :]
    source_box_error = np.max(np.abs(source_error[:, :2]), axis=1)
    speed = np.linalg.norm(
        r3.r1.r8._velocity_components(y, dt_ms / 1000.0), axis=1
    )
    first_inside = np.flatnonzero(box_error <= 0.03)
    inside = box_error <= 0.03
    longest_inside_streak = 0
    current_inside_streak = 0
    for value in inside:
        current_inside_streak = current_inside_streak + 1 if value else 0
        longest_inside_streak = max(
            longest_inside_streak, current_inside_streak
        )
    first_exit_after_entry = None
    if first_inside.size:
        exits = np.flatnonzero(
            ~inside[int(first_inside[0]) + 1 :]
        )
        if exits.size:
            first_exit_after_entry = int(
                first_inside[0] + 1 + exits[0]
            )
    same_timeline_action_delta = action - source_action
    first_actual = action[0]
    first_source = source_action[0]
    nearest_source_action_index = min(nearest_full_step, horizon - 1)
    nearest_source_action = source_action[nearest_source_action_index]
    trace = list(result.get("controller_trace") or [])
    solver_failures = sum(
        not bool(row.get("solver_success")) for row in trace
    )
    phase_counts = Counter(
        str(row.get("controller_phase", "")) for row in trace
    )
    action_saturated = np.abs(action) >= 1.0 - 1e-9
    measurement0 = (
        np.asarray(trace[0].get("measurement_physical"), dtype=float)
        if trace
        else np.asarray([], dtype=float)
    )
    sample_steps = sorted(
        {
            step
            for step in (0, 1, 2, 5, 8, 10, 12, 15, 20, 25, 27, 30, 35, 37)
            if step < len(trajectory)
        }
    )
    sampled_progression = []
    for step in sample_steps:
        sampled_progression.append(
            {
                "state_step": step,
                "time_ms": int(step * dt_ms),
                "R_error_m": float(error[step, 0]),
                "Z_error_m": float(error[step, 1]),
                "Ip_error_A": float(error[step, 2]),
                "RZ_box_error_m": float(box_error[step]),
                "speed_m_per_s": float(speed[step]),
                "source_RZ_box_error_m": float(source_box_error[step]),
                "preceding_action_max_abs": (
                    None
                    if step == 0
                    else float(np.max(np.abs(action[step - 1])))
                ),
                "preceding_action_max_abs_difference_from_source": (
                    None
                    if step == 0
                    else float(
                        np.max(
                            np.abs(
                                action[step - 1] - source_action[step - 1]
                            )
                        )
                    )
                ),
            }
        )
    return {
        "initial_state": {
            "R": float(y[0, 0]),
            "Z": float(y[0, 1]),
            "Ip": float(y[0, 2]),
            "target_R": float(target[0]),
            "target_Z": float(target[1]),
            "target_Ip": float(target[2]),
            "R_error_m": float(error[0, 0]),
            "Z_error_m": float(error[0, 1]),
            "Ip_error_A": float(error[0, 2]),
            "RZ_box_error_m": float(box_error[0]),
            "delta_from_source_step0_R_m": float(y[0, 0] - source_y[0, 0]),
            "delta_from_source_step0_Z_m": float(y[0, 1] - source_y[0, 1]),
            "delta_from_source_step0_Ip_A": float(y[0, 2] - source_y[0, 2]),
            "coil_rms_delta_from_source_step0_A": float(
                np.sqrt(np.mean((currents[0] - source_currents[0]) ** 2))
            ),
        },
        "source_phase_match_diagnostic": {
            "controller_nominal_reference_start_step": 0,
            "nearest_source_RZI_step": nearest_rzi_step,
            "nearest_source_RZI_normalized_rms": float(
                rzi_distance[nearest_rzi_step]
            ),
            "nearest_source_full_visible_step": nearest_full_step,
            "nearest_source_full_visible_normalized_rms": float(
                full_distance[nearest_full_step]
            ),
            "source_step0_full_visible_normalized_rms": float(
                full_distance[0]
            ),
        },
        "action_diagnostic": {
            "first_action_max_abs_difference_from_source_step0": float(
                np.max(np.abs(first_actual - first_source))
            ),
            "first_action_rms_difference_from_source_step0": float(
                np.sqrt(np.mean((first_actual - first_source) ** 2))
            ),
            "nearest_source_action_step": nearest_source_action_index,
            "first_action_max_abs_difference_from_nearest_visible_phase": float(
                np.max(np.abs(first_actual - nearest_source_action))
            ),
            "same_timeline_max_abs_difference": float(
                np.max(np.abs(same_timeline_action_delta))
            ),
            "same_timeline_rms_difference": float(
                np.sqrt(np.mean(same_timeline_action_delta**2))
            ),
            "saturated_action_element_count": int(np.sum(action_saturated)),
            "action_element_count": int(action_saturated.size),
            "saturated_action_fraction": float(np.mean(action_saturated)),
            "maximum_abs_action": float(np.max(np.abs(action))),
        },
        "trajectory_shape": {
            "minimum_RZ_box_error_m": float(np.min(box_error)),
            "minimum_RZ_box_error_step": int(np.argmin(box_error)),
            "first_RZ_box_entry_step": (
                int(first_inside[0]) if first_inside.size else None
            ),
            "first_RZ_box_entry_ms": (
                int(first_inside[0] * dt_ms)
                if first_inside.size
                else None
            ),
            "last_RZ_box_inside_step": (
                int(np.flatnonzero(inside)[-1]) if np.any(inside) else None
            ),
            "first_RZ_box_exit_after_entry_step": first_exit_after_entry,
            "longest_RZ_box_inside_streak_steps": longest_inside_streak,
            "terminal_RZ_box_error_m": float(box_error[-1]),
            "maximum_RZ_box_error_m": float(np.max(box_error)),
            "sampled_state_progression": sampled_progression,
        },
        "controller_trace": {
            "row_count": len(trace),
            "first_trace_step": (
                int(trace[0]["step"]) if trace else None
            ),
            "first_measurement_physical": measurement0.tolist(),
            "solver_failure_count": solver_failures,
            "phase_counts": dict(sorted(phase_counts.items())),
        },
    }


def _pair_divergence_detail(
    plus: Mapping[str, Any],
    minus: Mapping[str, Any],
) -> dict[str, Any]:
    base = r3._control_pair_divergence(plus, minus)
    plus_trajectory = list(plus["trajectory"])
    minus_trajectory = list(minus["trajectory"])
    plus_action = np.asarray(
        [row["action_norm_tsc"] for row in plus_trajectory[1:]],
        dtype=float,
    )
    minus_action = np.asarray(
        [row["action_norm_tsc"] for row in minus_trajectory[1:]],
        dtype=float,
    )
    plus_y = np.asarray(
        [[row["R"], row["Z"], row["Ip"]] for row in plus_trajectory],
        dtype=float,
    )
    minus_y = np.asarray(
        [[row["R"], row["Z"], row["Ip"]] for row in minus_trajectory],
        dtype=float,
    )
    action_by_step = np.max(np.abs(plus_action - minus_action), axis=1)
    rzi_by_step = np.abs(plus_y - minus_y)
    sample_steps = sorted(
        {
            step
            for step in (0, 1, 2, 5, 10, 15, 20, 25, 27, 35, 37)
            if step < len(plus_trajectory)
        }
    )
    progression = []
    for step in sample_steps:
        progression.append(
            {
                "state_step": step,
                "R_abs_difference_m": float(rzi_by_step[step, 0]),
                "Z_abs_difference_m": float(rzi_by_step[step, 1]),
                "Ip_abs_difference_A": float(rzi_by_step[step, 2]),
                "preceding_action_max_abs_difference": (
                    None
                    if step == 0
                    else float(action_by_step[step - 1])
                ),
            }
        )
    return {
        **base,
        "first_action_max_abs_difference": float(action_by_step[0]),
        "final_action_max_abs_difference": float(action_by_step[-1]),
        "final_R_abs_difference_m": float(rzi_by_step[-1, 0]),
        "final_Z_abs_difference_m": float(rzi_by_step[-1, 1]),
        "final_Ip_abs_difference_A": float(rzi_by_step[-1, 2]),
        "sampled_divergence_progression": progression,
    }


def _group_rows(
    rows: Sequence[Mapping[str, Any]],
    keys: Sequence[str],
) -> dict[str, Any]:
    groups: dict[tuple[Any, ...], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[key] for key in keys)].append(row)
    output: dict[str, Any] = {}
    for group_key, members in sorted(groups.items(), key=lambda item: str(item[0])):
        label = "|".join(
            f"{key}={value}" for key, value in zip(keys, group_key)
        )
        output[label] = {
            "count": len(members),
            "formal_pass_count": sum(
                bool(row["formal"]["formal_pass"]) for row in members
            ),
            "minimum_signed_margin": _finite_range(
                row["formal"]["minimum_signed_margin"] for row in members
            ),
            "initial_RZ_box_error_m": _finite_range(
                row["trajectory"]["initial_state"]["RZ_box_error_m"]
                for row in members
            ),
            "minimum_RZ_box_error_m": _finite_range(
                row["trajectory"]["trajectory_shape"][
                    "minimum_RZ_box_error_m"
                ]
                for row in members
            ),
            "terminal_RZ_box_error_m": _finite_range(
                row["trajectory"]["trajectory_shape"][
                    "terminal_RZ_box_error_m"
                ]
                for row in members
            ),
        }
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--source-stage4-2r2-run", required=True, type=Path)
    parser.add_argument(
        "--calibration-stage4-2r3a-run", required=True, type=Path
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--server-audit", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    run_dir = args.run_dir.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if output == run_dir or run_dir in output.parents:
        raise SystemExit("forensic output must remain outside the run tree")
    ctx = r3.load_stage42r3b_config(
        args.config,
        source_stage42r2_run=args.source_stage4_2r2_run,
        calibration_stage42r3a_run=args.calibration_stage4_2r3a_run,
        run_dir_override=run_dir,
    )
    state_paths, state_results = _read_raw(
        ctx.paths.state_generation / "raw"
    )
    control_paths, control_results = _read_raw(ctx.paths.control / "raw")
    selected_pairs, state_by_id = _recompute_selected_pairs(
        ctx, state_results
    )
    selected_by_id = {
        str(pair["pair_id"]): pair for pair in selected_pairs
    }
    source_cases = r3._source_controller_cases(ctx)
    detailed_rows: list[dict[str, Any]] = []
    result_by_group: dict[
        tuple[str, str, int, float], dict[str, Mapping[str, Any]]
    ] = defaultdict(dict)
    recomputed_control_rows = []
    for result in control_results:
        spec = result["spec"]
        state_id = str(spec["state_generation_experiment_id"])
        generated_state = state_by_id[state_id]
        control_row = r3._control_row(ctx, result, generated_state)
        recomputed_control_rows.append(control_row)
        formal = _formal_metrics(ctx, result)
        target = _absolute_target(ctx, spec)
        source_key = (
            str(spec["target_id"]),
            int(spec["action_delay_steps"]),
            float(spec["slew_scale"]),
        )
        source = source_cases[source_key]
        source_probe = copy.deepcopy(source)
        source_probe["spec"] = copy.deepcopy(spec)
        source_probe["trajectory"] = list(source["trajectory"])[
            : int(spec["horizon_steps"]) + 1
        ]
        source_probe["control_trace"] = list(
            source.get("control_trace") or []
        )[: int(spec["horizon_steps"])]
        source_formal = _formal_metrics(ctx, source_probe)
        pair = selected_by_id[str(spec["pair_id"])]
        row = {
            "experiment_id": str(result["experiment_id"]),
            "pair_id": str(spec["pair_id"]),
            "history_member": str(spec["history_member"]),
            "target_id": str(spec["target_id"]),
            "actual_delay_steps": int(spec["action_delay_steps"]),
            "actual_slew_scale": float(spec["slew_scale"]),
            "horizon_steps": int(spec["horizon_steps"]),
            "common_prefix_steps": int(pair["common_prefix_steps"]),
            "nullspace_direction_index": int(
                pair["nullspace_direction_index"]
            ),
            "amplitude_fraction": float(pair["amplitude_fraction"]),
            "gap_steps": int(pair["gap_steps"]),
            "snapshot_time_ms": int(generated_state["snapshot_time_ms"]),
            "environment_success": bool(result.get("success")),
            "restart_exact": bool(control_row["initial_restart_exact"]),
            "controller_trace_causal": bool(
                control_row["controller_trace_causal"]
            ),
            "formal": _formal_decomposition(formal),
            "original_start_R17_source_formal": _formal_decomposition(
                source_formal
            ),
            "trajectory": _trajectory_diagnostics(
                ctx, result, source, target
            ),
        }
        detailed_rows.append(row)
        group_key = (
            row["pair_id"],
            row["target_id"],
            row["actual_delay_steps"],
            row["actual_slew_scale"],
        )
        result_by_group[group_key][row["history_member"]] = result

    pair_rows = []
    formal_by_identity = {
        (
            row["pair_id"],
            row["history_member"],
            row["target_id"],
            row["actual_delay_steps"],
            row["actual_slew_scale"],
        ): row["formal"]
        for row in detailed_rows
    }
    for key, members in sorted(result_by_group.items()):
        if set(members) != {"plus_first", "minus_first"}:
            raise RuntimeError(f"incomplete raw control pair: {key}")
        plus_formal = formal_by_identity[
            (key[0], "plus_first", key[1], key[2], key[3])
        ]
        minus_formal = formal_by_identity[
            (key[0], "minus_first", key[1], key[2], key[3])
        ]
        pair_meta = selected_by_id[key[0]]
        pair_rows.append(
            {
                "pair_id": key[0],
                "target_id": key[1],
                "actual_delay_steps": key[2],
                "actual_slew_scale": key[3],
                "common_prefix_steps": int(
                    pair_meta["common_prefix_steps"]
                ),
                "nullspace_direction_index": int(
                    pair_meta["nullspace_direction_index"]
                ),
                "plus_first_formal_pass": bool(
                    plus_formal["formal_pass"]
                ),
                "minus_first_formal_pass": bool(
                    minus_formal["formal_pass"]
                ),
                "history_sensitive_pass_fail_outcome": bool(
                    plus_formal["formal_pass"]
                    != minus_formal["formal_pass"]
                ),
                "formal_margin_absolute_difference": abs(
                    float(plus_formal["minimum_signed_margin"])
                    - float(minus_formal["minimum_signed_margin"])
                ),
                **_pair_divergence_detail(
                    members["plus_first"], members["minus_first"]
                ),
            }
        )

    limiting = Counter(
        row["formal"]["chosen_limiting_component"]
        for row in detailed_rows
    )
    violated = Counter()
    unavoidable = Counter()
    for row in detailed_rows:
        violated.update(row["formal"]["chosen_violated_components"])
        unavoidable.update(row["formal"]["unavoidable_violated_components"])
    server_audit = json.loads(
        args.server_audit.read_text(encoding="utf-8")
    )
    raw_identity = [
        {
            "path": path.name,
            "size_bytes": int(path.stat().st_size),
            "sha256": _sha256(path),
        }
        for path in control_paths
    ]
    selected_pair_public = [
        {
            key: value
            for key, value in pair.items()
            if key not in {"plus_first_state", "minus_first_state"}
        }
        for pair in selected_pairs
    ]
    forensic = {
        "schema_version": 1,
        "stage": r3.STAGE,
        "purpose": "independent_raw_closed_loop_control_forensics",
        "run_dir": str(run_dir),
        "server_audit_path": str(args.server_audit.resolve()),
        "server_audit_sha256": _sha256(args.server_audit),
        "run_inventory": {
            "digest": server_audit["run_inventory"]["digest"],
            "n_files": int(server_audit["run_inventory"]["n_files"]),
            "total_bytes": int(server_audit["run_inventory"]["total_bytes"]),
        },
        "state_raw_file_count": len(state_paths),
        "state_raw_success_count": sum(
            bool(result.get("success")) for result in state_results
        ),
        "control_raw_file_count": len(control_paths),
        "control_raw_success_count": sum(
            bool(result.get("success")) for result in control_results
        ),
        "control_raw_inventory": {
            "digest": _canonical_digest(raw_identity),
            "n_files": len(raw_identity),
            "total_bytes": sum(
                int(row["size_bytes"]) for row in raw_identity
            ),
            "files": raw_identity,
        },
        "selected_pairs_recomputed_from_state_raw": selected_pair_public,
        "selected_pair_ids": [
            str(pair["pair_id"]) for pair in selected_pairs
        ],
        "integrity_and_execution": {
            "expected_control_count": 32,
            "environment_success_count": sum(
                bool(row["environment_success"])
                for row in detailed_rows
            ),
            "restart_exact_count": sum(
                bool(row["restart_exact"]) for row in detailed_rows
            ),
            "controller_trace_causal_count": sum(
                bool(row["controller_trace_causal"])
                for row in detailed_rows
            ),
            "runtime_or_environment_error_count": sum(
                row["failure_class"] == "runtime_or_environment_error"
                for row in recomputed_control_rows
            ),
            "plant_restart_fidelity_failure_count": sum(
                row["failure_class"] == "plant_restart_fidelity_failure"
                for row in recomputed_control_rows
            ),
            "controller_causality_failure_count": sum(
                row["failure_class"] == "controller_causality_failure"
                for row in recomputed_control_rows
            ),
        },
        "formal_outcome": {
            "pass_count": sum(
                bool(row["formal"]["formal_pass"])
                for row in detailed_rows
            ),
            "failure_count": sum(
                not bool(row["formal"]["formal_pass"])
                for row in detailed_rows
            ),
            "minimum_signed_margin": _finite_range(
                row["formal"]["minimum_signed_margin"]
                for row in detailed_rows
            ),
            "chosen_limiting_component_counts": dict(sorted(limiting.items())),
            "chosen_violated_component_counts": dict(sorted(violated.items())),
            "unavoidable_violated_component_counts": dict(
                sorted(unavoidable.items())
            ),
        },
        "grouped_outcomes": {
            "by_target": _group_rows(detailed_rows, ["target_id"]),
            "by_actuator": _group_rows(
                detailed_rows,
                ["actual_delay_steps", "actual_slew_scale"],
            ),
            "by_prefix": _group_rows(
                detailed_rows, ["common_prefix_steps"]
            ),
            "by_prefix_direction": _group_rows(
                detailed_rows,
                ["common_prefix_steps", "nullspace_direction_index"],
            ),
            "by_history_member": _group_rows(
                detailed_rows, ["history_member"]
            ),
        },
        "hidden_history_pair_outcome": {
            "pair_control_group_count": len(pair_rows),
            "history_sensitive_pass_fail_outcome_count": sum(
                bool(row["history_sensitive_pass_fail_outcome"])
                for row in pair_rows
            ),
            "formal_margin_absolute_difference": _finite_range(
                row["formal_margin_absolute_difference"]
                for row in pair_rows
            ),
            "maximum_action_abs_difference": _finite_range(
                row["maximum_action_abs_difference"]
                for row in pair_rows
            ),
            "maximum_R_abs_difference_m": _finite_range(
                row["maximum_R_abs_difference_m"]
                for row in pair_rows
            ),
            "maximum_Z_abs_difference_m": _finite_range(
                row["maximum_Z_abs_difference_m"]
                for row in pair_rows
            ),
            "maximum_Ip_abs_difference_A": _finite_range(
                row["maximum_Ip_abs_difference_A"]
                for row in pair_rows
            ),
            "maximum_wire_abs_difference_A": _finite_range(
                row["maximum_wire_abs_difference_A"]
                for row in pair_rows
            ),
            "interpretation_guard": (
                "zero pass/fail disagreement does not validate hidden-history "
                "robustness when both members fail the common formal gate"
            ),
        },
        "controller_start_diagnostic": {
            "controller_nominal_reference_start_step_values": sorted(
                {
                    row["trajectory"]["source_phase_match_diagnostic"][
                        "controller_nominal_reference_start_step"
                    ]
                    for row in detailed_rows
                }
            ),
            "nearest_source_RZI_step_counts": dict(
                sorted(
                    Counter(
                        row["trajectory"]["source_phase_match_diagnostic"][
                            "nearest_source_RZI_step"
                        ]
                        for row in detailed_rows
                    ).items()
                )
            ),
            "nearest_source_full_visible_step_counts": dict(
                sorted(
                    Counter(
                        row["trajectory"]["source_phase_match_diagnostic"][
                            "nearest_source_full_visible_step"
                        ]
                        for row in detailed_rows
                    ).items()
                )
            ),
            "source_step0_full_visible_normalized_rms": _finite_range(
                row["trajectory"]["source_phase_match_diagnostic"][
                    "source_step0_full_visible_normalized_rms"
                ]
                for row in detailed_rows
            ),
            "nearest_source_full_visible_normalized_rms": _finite_range(
                row["trajectory"]["source_phase_match_diagnostic"][
                    "nearest_source_full_visible_normalized_rms"
                ]
                for row in detailed_rows
            ),
            "first_action_max_abs_difference_from_source_step0": _finite_range(
                row["trajectory"]["action_diagnostic"][
                    "first_action_max_abs_difference_from_source_step0"
                ]
                for row in detailed_rows
            ),
            "first_trace_step_values": sorted(
                {
                    row["trajectory"]["controller_trace"][
                        "first_trace_step"
                    ]
                    for row in detailed_rows
                }
            ),
            "solver_failure_count": sum(
                row["trajectory"]["controller_trace"][
                    "solver_failure_count"
                ]
                for row in detailed_rows
            ),
            "saturated_action_fraction": _finite_range(
                row["trajectory"]["action_diagnostic"][
                    "saturated_action_fraction"
                ]
                for row in detailed_rows
            ),
        },
        "control_rows": detailed_rows,
        "control_pair_rows": pair_rows,
        "conclusion_guardrails": {
            "runtime_error": False,
            "raw_or_snapshot_corruption": False,
            "plant_restart_failure": False,
            "controller_causality_failure": False,
            "real_closed_loop_formal_control_failure": True,
            "hidden_history_robustness_validated": False,
            "different_initial_state_control_validated": False,
            "unseen_target_extrapolation_validated": False,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    r3.atomic_write_json(output, forensic)
    concise = {
        "output": str(output),
        "output_sha256": _sha256(output),
        "state_raw": len(state_paths),
        "control_raw": len(control_paths),
        "formal_pass": forensic["formal_outcome"]["pass_count"],
        "formal_failure": forensic["formal_outcome"]["failure_count"],
        "limiting": forensic["formal_outcome"][
            "chosen_limiting_component_counts"
        ],
        "nearest_source_full_visible_step_counts": forensic[
            "controller_start_diagnostic"
        ]["nearest_source_full_visible_step_counts"],
        "pair_groups": len(pair_rows),
        "history_sensitive_pass_fail": forensic[
            "hidden_history_pair_outcome"
        ]["history_sensitive_pass_fail_outcome_count"],
    }
    print(json.dumps(concise, sort_keys=True))


if __name__ == "__main__":
    main()
