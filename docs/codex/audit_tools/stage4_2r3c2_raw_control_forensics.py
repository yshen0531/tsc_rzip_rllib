#!/usr/bin/env python3
"""Independent Stage4.2R3c2 raw closed-loop control forensics.

Run on the server. The tool reads raw JSON.GZ in place and writes only a
compact JSON report outside the immutable run tree.
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
    stage4_2r3c2_restart_target_state_regulation_mpc as r3c,
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


def _r8_context(ctx: r3c.Stage42R3C2Context) -> Any:
    r13_ctx = r3c.r1._r13_ctx(ctx.source_ctx.r1_ctx)
    return r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx


def _timing_policy(
    ctx: r3c.Stage42R3C2Context,
    spec: Mapping[str, Any],
) -> dict[str, Any]:
    return r3c.r1.r13._timing_policy(
        r3c.r1._r13_ctx(ctx.source_ctx.r1_ctx),
        float(spec["slew_scale"]),
        policy_id=(
            f"r42r3c2_forensics_{spec['pair_id']}_"
            f"{spec['history_member']}_{spec['target_id']}_"
            f"{spec['action_delay_steps']}_{spec['slew_scale']}"
        ),
    )


def _formal_metrics(
    ctx: r3c.Stage42R3C2Context,
    result: Mapping[str, Any],
) -> dict[str, Any]:
    return r3c.r1.r8.tracking_metrics(
        _r8_context(ctx),
        result,
        _timing_policy(ctx, result["spec"]),
    )


def _absolute_target(
    ctx: r3c.Stage42R3C2Context,
    spec: Mapping[str, Any],
) -> np.ndarray:
    r8_ctx = _r8_context(ctx)
    base34 = r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34
    metric_ctx = SimpleNamespace(
        cfg=copy.deepcopy(base34.cfg),
        env_cfg=base34.env_cfg,
    )
    metric_ctx.cfg["gate"].update(copy.deepcopy(r8_ctx.cfg["gate"]))
    return np.asarray(
        r3c.r1.r8.s34.target_absolute(
            metric_ctx, r3c.r1.r8._target_task(spec)
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
    return {
        "formal_pass": bool(formal["stage3_4_target_tracking_pass"]),
        "minimum_signed_margin": float(
            formal["stage3_4_tracking_minimum_signed_margin"]
        ),
        "chosen_endpoint_step": chosen_step,
        "chosen_arrival_ms": int(formal["stage3_4_best_endpoint_ms"]),
        "chosen_component_margins": margins,
        "chosen_limiting_component": min(margins, key=margins.get),
        "chosen_violated_components": sorted(
            name for name, value in margins.items() if value < -1e-12
        ),
        "best_margin_by_component_over_allowed_endpoints": (
            best_by_component
        ),
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


def _longest_true_streak(mask: np.ndarray) -> int:
    longest = 0
    current = 0
    for value in mask:
        current = current + 1 if bool(value) else 0
        longest = max(longest, current)
    return longest


def _trajectory_diagnostics(
    ctx: r3c.Stage42R3C2Context,
    result: Mapping[str, Any],
    source: Mapping[str, Any],
    target: np.ndarray,
) -> dict[str, Any]:
    trajectory = list(result["trajectory"])
    source_trajectory = list(source["trajectory"])
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
    actions = np.asarray(
        [row["action_norm_tsc"] for row in trajectory[1:]], dtype=float
    )
    source_actions = np.asarray(
        [row["action_norm_tsc"] for row in source_trajectory[1:]],
        dtype=float,
    )
    trace = list(result["controller_trace"])
    phase_start = int(trace[0]["reference_phase_start"])
    dt_ms = int(
        _r8_context(ctx)
        .r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34.env_cfg["dt_ms"]
    )
    ip_scale = float(
        _r8_context(ctx).cfg["gate"]["ip_safety_tolerance_A"]
    )
    rzi_scale = np.asarray([0.03, 0.03, ip_scale], dtype=float)
    coil_scale = float(
        ctx.source_ctx.cfg["different_initial_state_gate"][
            "coil_centroid_rms_difference_A_min"
        ]
    )
    rzi_distance = np.sqrt(
        np.mean(
            ((source_y - y[0][None, :]) / rzi_scale[None, :]) ** 2,
            axis=1,
        )
    )
    full_delta = np.concatenate(
        [
            (source_y - y[0][None, :]) / rzi_scale[None, :],
            (source_currents - currents[0][None, :]) / coil_scale,
        ],
        axis=1,
    )
    full_distance = np.sqrt(np.mean(full_delta**2, axis=1))
    nearest_rzi = int(np.argmin(rzi_distance))
    nearest_full = int(np.argmin(full_distance))
    error = y - target[None, :]
    box = np.max(np.abs(error[:, :2]), axis=1)
    velocity = r3c.r1.r8._velocity_components(y, dt_ms / 1000.0)
    speed = np.linalg.norm(velocity, axis=1)
    inside = box <= 0.03
    entries = np.flatnonzero(inside)
    first_entry = int(entries[0]) if entries.size else None
    first_exit = None
    if first_entry is not None:
        exits = np.flatnonzero(~inside[first_entry + 1 :])
        if exits.size:
            first_exit = int(first_entry + 1 + exits[0])
    aligned_action_index = min(phase_start, len(source_actions) - 1)
    sample_steps = sorted(
        {
            step
            for step in (0, 1, 2, 5, 8, 10, 12, 15, 20, 25, 27, 30, 35, 37)
            if step < len(trajectory)
        }
    )
    sampled = [
        {
            "state_step": step,
            "time_ms": step * dt_ms,
            "R_error_m": float(error[step, 0]),
            "Z_error_m": float(error[step, 1]),
            "Ip_error_A": float(error[step, 2]),
            "RZ_box_error_m": float(box[step]),
            "speed_m_per_s": float(speed[step]),
        }
        for step in sample_steps
    ]
    phase_counts = Counter(
        str(row["controller_phase"]) for row in trace
    )
    return {
        "initial_state": {
            "R": float(y[0, 0]),
            "Z": float(y[0, 1]),
            "Ip": float(y[0, 2]),
            "RZ_box_error_m": float(box[0]),
        },
        "phase_alignment": {
            "selected_reference_phase": phase_start,
            "reference_phase_end": int(trace[-1]["reference_phase"]),
            "nearest_source_RZI_step": nearest_rzi,
            "nearest_source_full_visible_step": nearest_full,
            "nearest_source_RZI_normalized_rms": float(
                rzi_distance[nearest_rzi]
            ),
            "nearest_source_full_visible_normalized_rms": float(
                full_distance[nearest_full]
            ),
            "first_action_max_abs_difference_from_source_phase_zero": (
                float(np.max(np.abs(actions[0] - source_actions[0])))
            ),
            "first_action_max_abs_difference_from_selected_phase": (
                float(
                    np.max(
                        np.abs(
                            actions[0] - source_actions[aligned_action_index]
                        )
                    )
                )
            ),
            "first_action_max_abs_difference_from_nearest_RZI_phase": (
                float(
                    np.max(
                        np.abs(
                            actions[0]
                            - source_actions[
                                min(nearest_rzi, len(source_actions) - 1)
                            ]
                        )
                    )
                )
            ),
        },
        "trajectory_shape": {
            "minimum_RZ_box_error_m": float(np.min(box)),
            "minimum_RZ_box_error_step": int(np.argmin(box)),
            "first_RZ_box_entry_step": first_entry,
            "first_RZ_box_entry_ms": (
                None if first_entry is None else first_entry * dt_ms
            ),
            "first_RZ_box_exit_after_entry_step": first_exit,
            "last_RZ_box_inside_step": (
                int(entries[-1]) if entries.size else None
            ),
            "longest_RZ_box_inside_streak_steps": _longest_true_streak(
                inside
            ),
            "terminal_RZ_box_error_m": float(box[-1]),
            "maximum_RZ_box_error_m": float(np.max(box)),
            "maximum_speed_m_per_s": float(np.max(speed)),
            "terminal_speed_m_per_s": float(speed[-1]),
            "sampled_state_progression": sampled,
        },
        "action_and_solver": {
            "maximum_abs_action": float(np.max(np.abs(actions))),
            "saturated_action_element_count": int(
                np.sum(np.abs(actions) >= 1.0 - 1e-9)
            ),
            "action_element_count": int(actions.size),
            "solver_failure_count": sum(
                not bool(row.get("solver_success")) for row in trace
            ),
            "controller_phase_counts": dict(sorted(phase_counts.items())),
        },
    }


def _group_rows(
    rows: Sequence[Mapping[str, Any]],
    keys: Sequence[str],
) -> dict[str, Any]:
    groups: dict[tuple[Any, ...], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[key] for key in keys)].append(row)
    output = {}
    for key_values, members in sorted(groups.items(), key=lambda item: str(item[0])):
        label = "|".join(
            f"{key}={value}" for key, value in zip(keys, key_values)
        )
        output[label] = {
            "count": len(members),
            "formal_pass_count": sum(
                bool(row["formal"]["formal_pass"]) for row in members
            ),
            "minimum_signed_margin": _finite_range(
                row["formal"]["minimum_signed_margin"] for row in members
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
    parser.add_argument("--source-stage4-2r3b-run", required=True, type=Path)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--server-audit", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    run_dir = args.run_dir.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if output == run_dir or run_dir in output.parents:
        raise SystemExit("forensic output must remain outside run tree")
    ctx = r3c.load_stage42r3c2_config(
        args.config,
        source_stage42r3b_run=args.source_stage4_2r3b_run,
        run_dir_override=run_dir,
    )
    selected_pairs, state_by_id = r3c._recompute_selected_pairs(ctx)
    selected_by_id = {
        str(pair["pair_id"]): pair for pair in selected_pairs
    }
    raw_paths = sorted((ctx.paths.control / "raw").glob("*.json.gz"))
    results = [r3c.read_json_gz(path) for path in raw_paths]
    source_cases = r3c._source_controller_cases(ctx)
    rows = []
    recomputed_rows = []
    result_groups: dict[
        tuple[str, str, int, float], dict[str, Mapping[str, Any]]
    ] = defaultdict(dict)
    for result in results:
        spec = result["spec"]
        state = state_by_id[str(spec["state_generation_experiment_id"])]
        control_row = r3c.r3b._control_row(
            ctx.source_ctx, result, state
        )
        phase = r3c._phase_trace_valid(result)
        recomputed_rows.append({**control_row, "phase": phase})
        formal = _formal_metrics(ctx, result)
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
        pair = selected_by_id[str(spec["pair_id"])]
        trace = list(result["controller_trace"])
        row = {
            "experiment_id": str(result["experiment_id"]),
            "pair_id": str(spec["pair_id"]),
            "history_member": str(spec["history_member"]),
            "target_id": str(spec["target_id"]),
            "actual_delay_steps": int(spec["action_delay_steps"]),
            "actual_slew_scale": float(spec["slew_scale"]),
            "reference_phase_start": int(
                trace[0]["reference_phase_start"]
            ),
            "horizon_steps": int(spec["horizon_steps"]),
            "common_prefix_steps": int(pair["common_prefix_steps"]),
            "nullspace_direction_index": int(
                pair["nullspace_direction_index"]
            ),
            "environment_success": bool(result.get("success")),
            "restart_exact": bool(control_row["initial_restart_exact"]),
            "controller_trace_causal": bool(
                control_row["controller_trace_causal"]
            ),
            "phase_trace_valid": bool(phase["passed"]),
            "controller_trace_steps": len(trace),
            "restart_regulation_trace_count": int(
                phase["restart_regulation_trace_count"]
            ),
            "pair_or_history_label_trace_count": int(
                phase["pair_or_history_label_trace_count"]
            ),
            "source_result_trace_count": int(
                phase["source_result_trace_count"]
            ),
            "formal": _formal_decomposition(formal),
            "original_start_R17_source_formal": _formal_decomposition(
                _formal_metrics(ctx, source_probe)
            ),
            "trajectory": _trajectory_diagnostics(
                ctx, result, source, _absolute_target(ctx, spec)
            ),
        }
        rows.append(row)
        key = (
            row["pair_id"],
            row["target_id"],
            row["actual_delay_steps"],
            row["actual_slew_scale"],
        )
        result_groups[key][row["history_member"]] = result

    pair_rows = []
    formal_by_identity = {
        (
            row["pair_id"],
            row["history_member"],
            row["target_id"],
            row["actual_delay_steps"],
            row["actual_slew_scale"],
        ): row["formal"]
        for row in rows
    }
    for key, members in sorted(result_groups.items()):
        plus_formal = formal_by_identity[
            (key[0], "plus_first", key[1], key[2], key[3])
        ]
        minus_formal = formal_by_identity[
            (key[0], "minus_first", key[1], key[2], key[3])
        ]
        pair_rows.append(
            {
                "pair_id": key[0],
                "target_id": key[1],
                "actual_delay_steps": key[2],
                "actual_slew_scale": key[3],
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
                **r3c.r3b._control_pair_divergence(
                    members["plus_first"], members["minus_first"]
                ),
            }
        )

    limiting = Counter(
        row["formal"]["chosen_limiting_component"] for row in rows
    )
    violated = Counter()
    unavoidable = Counter()
    for row in rows:
        violated.update(row["formal"]["chosen_violated_components"])
        unavoidable.update(row["formal"]["unavoidable_violated_components"])
    raw_identity = [
        {
            "path": path.name,
            "size_bytes": int(path.stat().st_size),
            "sha256": _sha256(path),
        }
        for path in raw_paths
    ]
    server_audit = json.loads(
        args.server_audit.read_text(encoding="utf-8")
    )
    server_audit_compatible = bool(
        server_audit.get("stage") == r3c.STAGE
        and Path(str(server_audit.get("run_dir", ""))).resolve()
        == run_dir
        and int(server_audit.get("control_raw_actual", -1))
        == len(results)
        and bool(server_audit.get("control_experiment_id_set_exact"))
        and bool(server_audit.get("control_specs_exact"))
        and bool(server_audit.get("control_raw_parse_complete"))
    )
    failures = [
        row for row in rows if not bool(row["formal"]["formal_pass"])
    ]
    forensic = {
        "schema_version": 1,
        "stage": r3c.STAGE,
        "purpose": "independent_raw_closed_loop_control_forensics",
        "run_dir": str(run_dir),
        "server_audit_path": str(args.server_audit.resolve()),
        "server_audit_sha256": _sha256(args.server_audit),
        "server_audit_compatible": server_audit_compatible,
        "run_inventory": {
            "digest": server_audit["run_inventory"]["digest"],
            "n_files": int(server_audit["run_inventory"]["n_files"]),
            "total_bytes": int(server_audit["run_inventory"]["total_bytes"]),
        },
        "control_raw_inventory": {
            "digest": _canonical_digest(raw_identity),
            "n_files": len(raw_identity),
            "total_bytes": sum(
                int(row["size_bytes"]) for row in raw_identity
            ),
            "files": raw_identity,
        },
        "integrity_and_execution": {
            "expected_control_count": 32,
            "control_raw_count": len(results),
            "environment_success_count": sum(
                bool(row["environment_success"]) for row in rows
            ),
            "restart_exact_count": sum(
                bool(row["restart_exact"]) for row in rows
            ),
            "controller_trace_causal_count": sum(
                bool(row["controller_trace_causal"]) for row in rows
            ),
            "phase_trace_valid_count": sum(
                bool(row["phase_trace_valid"]) for row in rows
            ),
            "restart_regulation_trace_count": sum(
                int(row["restart_regulation_trace_count"])
                for row in rows
            ),
            "controller_trace_step_count": sum(
                int(row["controller_trace_steps"]) for row in rows
            ),
            "pair_or_history_label_trace_count": sum(
                int(row["pair_or_history_label_trace_count"])
                for row in rows
            ),
            "source_result_trace_count": sum(
                int(row["source_result_trace_count"]) for row in rows
            ),
            "runtime_or_environment_error_count": sum(
                row["failure_class"] == "runtime_or_environment_error"
                for row in recomputed_rows
            ),
            "plant_restart_fidelity_failure_count": sum(
                row["failure_class"] == "plant_restart_fidelity_failure"
                for row in recomputed_rows
            ),
            "controller_causality_failure_count": sum(
                row["failure_class"] == "controller_causality_failure"
                for row in recomputed_rows
            ),
        },
        "formal_outcome": {
            "pass_count": len(rows) - len(failures),
            "failure_count": len(failures),
            "minimum_signed_margin": _finite_range(
                row["formal"]["minimum_signed_margin"] for row in rows
            ),
            "chosen_limiting_component_counts": dict(sorted(limiting.items())),
            "chosen_violated_component_counts": dict(sorted(violated.items())),
            "unavoidable_violated_component_counts": dict(
                sorted(unavoidable.items())
            ),
            "failed_case_ids": [
                row["experiment_id"] for row in failures
            ],
        },
        "grouped_outcomes": {
            "by_target": _group_rows(rows, ["target_id"]),
            "by_actuator": _group_rows(
                rows, ["actual_delay_steps", "actual_slew_scale"]
            ),
            "by_prefix": _group_rows(rows, ["common_prefix_steps"]),
            "by_prefix_direction": _group_rows(
                rows,
                ["common_prefix_steps", "nullspace_direction_index"],
            ),
            "by_reference_phase": _group_rows(
                rows, ["reference_phase_start"]
            ),
            "by_history_member": _group_rows(
                rows, ["history_member"]
            ),
        },
        "hidden_history_pair_outcome": {
            "pair_control_group_count": len(pair_rows),
            "both_pass_count": sum(
                row["plus_first_formal_pass"]
                and row["minus_first_formal_pass"]
                for row in pair_rows
            ),
            "both_fail_count": sum(
                not row["plus_first_formal_pass"]
                and not row["minus_first_formal_pass"]
                for row in pair_rows
            ),
            "history_sensitive_pass_fail_outcome_count": sum(
                row["history_sensitive_pass_fail_outcome"]
                for row in pair_rows
            ),
            "formal_margin_absolute_difference": _finite_range(
                row["formal_margin_absolute_difference"]
                for row in pair_rows
            ),
            "maximum_action_abs_difference": _finite_range(
                row["maximum_action_abs_difference"] for row in pair_rows
            ),
            "maximum_R_abs_difference_m": _finite_range(
                row["maximum_R_abs_difference_m"] for row in pair_rows
            ),
            "maximum_Z_abs_difference_m": _finite_range(
                row["maximum_Z_abs_difference_m"] for row in pair_rows
            ),
            "maximum_wire_abs_difference_A": _finite_range(
                row["maximum_wire_abs_difference_A"] for row in pair_rows
            ),
            "interpretation_guard": (
                "both-fail groups mask hidden-history robustness"
            ),
        },
        "restart_regulation_diagnostic": {
            "selected_reference_phase_counts": dict(
                sorted(Counter(row["reference_phase_start"] for row in rows).items())
            ),
            "nearest_source_RZI_step_counts": dict(
                sorted(
                    Counter(
                        row["trajectory"]["phase_alignment"][
                            "nearest_source_RZI_step"
                        ]
                        for row in rows
                    ).items()
                )
            ),
            "first_action_difference_from_phase_zero": _finite_range(
                row["trajectory"]["phase_alignment"][
                    "first_action_max_abs_difference_from_source_phase_zero"
                ]
                for row in rows
            ),
            "first_action_difference_from_selected_phase": _finite_range(
                row["trajectory"]["phase_alignment"][
                    "first_action_max_abs_difference_from_selected_phase"
                ]
                for row in rows
            ),
            "solver_failure_count": sum(
                row["trajectory"]["action_and_solver"][
                    "solver_failure_count"
                ]
                for row in rows
            ),
            "saturated_action_element_count": sum(
                row["trajectory"]["action_and_solver"][
                    "saturated_action_element_count"
                ]
                for row in rows
            ),
            "action_element_count": sum(
                row["trajectory"]["action_and_solver"][
                    "action_element_count"
                ]
                for row in rows
            ),
        },
        "control_rows": rows,
        "control_pair_rows": pair_rows,
        "conclusion_guardrails": {
            "runtime_error": any(
                row["failure_class"] == "runtime_or_environment_error"
                for row in recomputed_rows
            ),
            "raw_or_snapshot_corruption": bool(
                len(results) != 32
                or not server_audit_compatible
                or not bool(
                    server_audit.get("raw_and_manifest_integrity_passed")
                )
            ),
            "plant_restart_failure": any(
                row["failure_class"] == "plant_restart_fidelity_failure"
                for row in recomputed_rows
            ),
            "controller_causality_failure": any(
                row["failure_class"] == "controller_causality_failure"
                for row in recomputed_rows
            ),
            "phase_selection_or_transition_design_failure": any(
                not bool(row["phase_trace_valid"]) for row in rows
            ),
            "real_closed_loop_formal_control_failure": bool(failures),
            "development_set_closure_validated": not bool(failures),
            "hidden_history_robustness_validated": False,
            "different_initial_state_independent_validation": False,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    r3c.atomic_write_json(output, forensic)
    print(
        json.dumps(
            {
                "output": str(output),
                "output_sha256": _sha256(output),
                "control_raw": len(results),
                "formal_pass": len(rows) - len(failures),
                "formal_failure": len(failures),
                "limiting": forensic["formal_outcome"][
                    "chosen_limiting_component_counts"
                ],
                "unavoidable": forensic["formal_outcome"][
                    "unavoidable_violated_component_counts"
                ],
                "phase_counts": forensic["restart_regulation_diagnostic"][
                    "selected_reference_phase_counts"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
