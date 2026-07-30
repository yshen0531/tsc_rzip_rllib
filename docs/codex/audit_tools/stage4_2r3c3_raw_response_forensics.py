#!/usr/bin/env python3
"""Independent Stage4.2R3c3 raw local-response forensics.

Run this on the server. It reads the 256 JSON.GZ trajectories in place,
recomputes the preregistered response gates without calling the campaign
summarizer, and writes one compact JSON report outside the immutable run tree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3_restart_task_clock_local_response_identification as r3c,
)


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


def _rmse(array: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.asarray(array, dtype=float) ** 2)))


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


def _trajectory_arrays(
    result: Mapping[str, Any], dt_s: float
) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(
        [
            [row["R"], row["Z"], row["Ip"]]
            for row in result["trajectory"]
        ],
        dtype=float,
    )
    if (
        values.ndim != 2
        or values.shape[1] != 3
        or not np.all(np.isfinite(values))
    ):
        raise ValueError("non-finite or malformed R/Z/Ip trajectory")
    velocity = r3c.r1.r8._velocity_components(values, dt_s)
    return values, velocity


def _initial_restart_arrays(
    result: Mapping[str, Any],
) -> tuple[np.ndarray, np.ndarray]:
    row = result["trajectory"][0]
    visible = np.asarray(
        [row["R"], row["Z"], row["Ip"], *row["currents_a_tsc"]],
        dtype=float,
    )
    wire = np.asarray(row["wire_currents_a"], dtype=float).reshape(-1)
    return visible, wire


def _trace_audit(result: Mapping[str, Any]) -> dict[str, Any]:
    """Recompute probe execution and explicit forbidden-input counts."""

    spec = dict(result.get("spec") or {})
    trace = list(result.get("controller_trace") or [])
    schedule = {
        int(step): np.asarray(value, dtype=float).reshape(-1)
        for step, value in (
            spec.get("r3c3_probe_delta_by_task_issue_step") or {}
        ).items()
    }
    n_modes = len(next(iter(schedule.values()))) if schedule else 3
    zeros = np.zeros(n_modes, dtype=float)
    counts = Counter()
    requested_rows: list[np.ndarray] = []
    applied_rows: list[np.ndarray] = []
    exact = bool(trace and len(schedule) == 4)
    previous_measurement_max = -1
    for row in trace:
        step = int(row.get("task_step", -1))
        expected = schedule.get(step, zeros)
        requested = np.asarray(
            row.get("r3c3_probe_requested_delta", []), dtype=float
        ).reshape(-1)
        applied = np.asarray(
            row.get("r3c3_probe_applied_desired_delta", []), dtype=float
        ).reshape(-1)
        issued = bool(row.get("r3c3_probe_issued"))
        measurement_max = int(row.get("measurement_max_state_index_used", -1))
        exact = bool(
            exact
            and requested.shape == expected.shape == (n_modes,)
            and applied.shape == (n_modes,)
            and np.array_equal(requested, expected)
            and issued == (step in schedule)
            and bool(row.get("computed_online"))
            and str(row.get("baseline_controller_revision"))
            == r3c.r3c1.CONTROLLER_REVISION
            and bool(row.get("r3c3_identification_only"))
            and str(row.get("r3c3_probe_id"))
            == str(spec.get("r3c3_probe_id"))
            and int(row.get("r3c3_probe_mode", -1))
            == int(spec.get("r3c3_probe_mode", -2))
            and int(row.get("r3c3_probe_sign", 0))
            == int(spec.get("r3c3_probe_sign", 1))
            and measurement_max <= int(row.get("step", step))
            and measurement_max >= previous_measurement_max
        )
        previous_measurement_max = measurement_max
        for key in (
            "hidden_wire_used",
            "source_action_used",
            "source_coil_current_used",
            "source_wire_current_used",
            "current_run_future_used",
            "future_measurement_used",
            "pair_or_history_label_used",
            "source_result_used",
        ):
            counts[key] += bool(row.get(key))
        counts["solver_failure"] += not bool(row.get("solver_success"))
        counts["issued"] += issued
        if issued:
            requested_rows.append(requested)
            applied_rows.append(applied)
    requested = (
        np.stack(requested_rows)
        if len(requested_rows) == 4
        else np.empty((0, n_modes), dtype=float)
    )
    applied = (
        np.stack(applied_rows)
        if len(applied_rows) == 4
        else np.empty((0, n_modes), dtype=float)
    )
    applied_exact = bool(
        requested.shape == applied.shape == (4, n_modes)
        and np.allclose(requested, applied, rtol=0.0, atol=1.0e-12)
    )
    zero_net = bool(
        requested.shape == applied.shape == (4, n_modes)
        and np.allclose(
            requested.sum(axis=0), zeros, rtol=0.0, atol=1.0e-12
        )
        and np.allclose(
            applied.sum(axis=0), zeros, rtol=0.0, atol=1.0e-12
        )
    )
    first_effect_exact = bool(
        schedule
        and min(schedule)
        + int(spec.get("action_delay_steps", -100))
        + 1
        == int(spec.get("r3c3_probe_first_effect_state", -1))
    )
    forbidden_count = sum(
        counts[key]
        for key in (
            "hidden_wire_used",
            "source_action_used",
            "source_coil_current_used",
            "source_wire_current_used",
            "current_run_future_used",
            "future_measurement_used",
            "pair_or_history_label_used",
            "source_result_used",
        )
    )
    passed = bool(
        exact
        and counts["issued"] == 4
        and applied_exact
        and zero_net
        and first_effect_exact
        and counts["solver_failure"] == 0
        and forbidden_count == 0
    )
    return {
        "passed": passed,
        "trace_exact": exact,
        "trace_steps": len(trace),
        "issued_count": counts["issued"],
        "applied_exact": applied_exact,
        "zero_net": zero_net,
        "first_effect_exact": first_effect_exact,
        "solver_failure_count": counts["solver_failure"],
        "forbidden_input_count": forbidden_count,
        "forbidden_input_counts": {
            key: counts[key]
            for key in (
                "hidden_wire_used",
                "source_action_used",
                "source_coil_current_used",
                "source_wire_current_used",
                "current_run_future_used",
                "future_measurement_used",
                "pair_or_history_label_used",
                "source_result_used",
            )
        },
    }


def _response_metrics(
    ctx: Any,
    results: list[Mapping[str, Any]],
    dt_s: float,
) -> tuple[list[dict[str, Any]], dict[Any, Any]]:
    cfg = ctx.cfg["identification_probe"]["central_symmetry"]
    signed_groups: dict[tuple[Any, ...], dict[int, Mapping[str, Any]]] = (
        defaultdict(dict)
    )
    for result in results:
        spec = result["spec"]
        key = (
            str(spec["pair_id"]),
            str(spec["history_member"]),
            str(spec["target_id"]),
            int(spec["action_delay_steps"]),
            float(spec["slew_scale"]),
            str(spec["r3c3_probe_id"]),
        )
        sign = int(spec["r3c3_probe_sign"])
        if sign in signed_groups[key]:
            raise ValueError(f"duplicate signed response: {key} {sign}")
        signed_groups[key][sign] = result
    baseline_dir = (
        ctx.source_r3c1_run
        / "stage4_2r3c1_authenticated_visible_manifold_control"
        / "raw"
    )
    baseline_cache: dict[str, Mapping[str, Any]] = {}
    odd_by_key: dict[tuple[Any, ...], tuple[np.ndarray, np.ndarray, int]] = {}
    rows: list[dict[str, Any]] = []
    for key in sorted(signed_groups):
        members = signed_groups[key]
        row = {
            "pair_id": key[0],
            "history_member": key[1],
            "target_id": key[2],
            "actual_delay_steps": key[3],
            "actual_slew_scale": key[4],
            "probe_id": key[5],
            "signed_member_count": len(members),
            "response_available": False,
            "initial_restart_exact_to_baseline": False,
            "even_velocity_rmse_m_per_s": None,
            "even_position_rmse_m": None,
            "even_ip_rmse_A": None,
            "central_symmetry_pass": False,
        }
        if set(members) == {-1, 1} and all(
            bool(member.get("success")) for member in members.values()
        ):
            plus = members[1]
            minus = members[-1]
            plus_baseline = str(plus["spec"]["baseline_experiment_id"])
            minus_baseline = str(minus["spec"]["baseline_experiment_id"])
            if plus_baseline != minus_baseline:
                raise ValueError(f"signed baseline mismatch: {key}")
            if plus_baseline not in baseline_cache:
                baseline_cache[plus_baseline] = r3c.read_json_gz(
                    baseline_dir / f"{plus_baseline}.json.gz"
                )
            baseline = baseline_cache[plus_baseline]
            plus_y, plus_v = _trajectory_arrays(plus, dt_s)
            minus_y, minus_v = _trajectory_arrays(minus, dt_s)
            base_y, base_v = _trajectory_arrays(baseline, dt_s)
            same_shape = bool(
                plus_y.shape == minus_y.shape == base_y.shape
                and plus_v.shape == minus_v.shape == base_v.shape
            )
            plus_initial = _initial_restart_arrays(plus)
            minus_initial = _initial_restart_arrays(minus)
            base_initial = _initial_restart_arrays(baseline)
            initial_exact = bool(
                np.array_equal(plus_initial[0], minus_initial[0])
                and np.array_equal(plus_initial[0], base_initial[0])
                and np.array_equal(plus_initial[1], minus_initial[1])
                and np.array_equal(plus_initial[1], base_initial[1])
            )
            first_effect = int(
                plus["spec"]["r3c3_probe_first_effect_state"]
            )
            if same_shape and first_effect < len(plus_y):
                section = slice(first_effect, len(plus_y))
                odd_y = (plus_y - minus_y) / 2.0
                odd_v = (plus_v - minus_v) / 2.0
                even_y = (plus_y + minus_y) / 2.0 - base_y
                even_v = (plus_v + minus_v) / 2.0 - base_v
                velocity_rmse = _rmse(even_v[section, :2])
                position_rmse = _rmse(even_y[section, :2])
                ip_rmse = _rmse(even_y[section, 2])
                passed = bool(
                    initial_exact
                    and velocity_rmse
                    <= float(cfg["maximum_even_velocity_rmse_m_per_s"])
                    and position_rmse
                    <= float(cfg["maximum_even_position_rmse_m"])
                    and ip_rmse <= float(cfg["maximum_even_ip_rmse_A"])
                )
                row.update(
                    {
                        "response_available": True,
                        "initial_restart_exact_to_baseline": initial_exact,
                        "first_effect_state": first_effect,
                        "even_velocity_rmse_m_per_s": velocity_rmse,
                        "even_position_rmse_m": position_rmse,
                        "even_ip_rmse_A": ip_rmse,
                        "central_symmetry_pass": passed,
                    }
                )
                odd_by_key[key] = (odd_y, odd_v, first_effect)
        rows.append(row)
    return rows, odd_by_key


def _history_metrics(
    ctx: Any,
    odd_by_key: Mapping[Any, tuple[np.ndarray, np.ndarray, int]],
) -> list[dict[str, Any]]:
    cfg = ctx.cfg["identification_probe"]["matched_hidden_history"]
    groups: dict[Any, dict[str, tuple[np.ndarray, np.ndarray, int]]] = (
        defaultdict(dict)
    )
    for key, response in odd_by_key.items():
        groups[(key[0], key[2], key[3], key[4], key[5])][key[1]] = (
            response
        )
    rows = []
    for key in sorted(groups):
        members = groups[key]
        row = {
            "pair_id": key[0],
            "target_id": key[1],
            "actual_delay_steps": key[2],
            "actual_slew_scale": key[3],
            "probe_id": key[4],
            "history_member_count": len(members),
            "odd_velocity_rmse_m_per_s": None,
            "odd_position_rmse_m": None,
            "odd_ip_rmse_A": None,
            "matched_hidden_history_pass": False,
        }
        if set(members) == {"plus_first", "minus_first"}:
            plus = members["plus_first"]
            minus = members["minus_first"]
            if plus[0].shape == minus[0].shape:
                section = slice(max(plus[2], minus[2]), len(plus[0]))
                velocity_rmse = _rmse(
                    plus[1][section, :2] - minus[1][section, :2]
                )
                position_rmse = _rmse(
                    plus[0][section, :2] - minus[0][section, :2]
                )
                ip_rmse = _rmse(
                    plus[0][section, 2] - minus[0][section, 2]
                )
                passed = bool(
                    velocity_rmse
                    <= float(cfg["maximum_odd_velocity_rmse_m_per_s"])
                    and position_rmse
                    <= float(cfg["maximum_odd_position_rmse_m"])
                    and ip_rmse <= float(cfg["maximum_odd_ip_rmse_A"])
                )
                row.update(
                    {
                        "odd_velocity_rmse_m_per_s": velocity_rmse,
                        "odd_position_rmse_m": position_rmse,
                        "odd_ip_rmse_A": ip_rmse,
                        "matched_hidden_history_pass": passed,
                    }
                )
        rows.append(row)
    return rows


def _condition_metrics(
    ctx: Any,
    odd_by_key: Mapping[Any, tuple[np.ndarray, np.ndarray, int]],
) -> list[dict[str, Any]]:
    groups: dict[Any, dict[str, tuple[np.ndarray, np.ndarray, int]]] = (
        defaultdict(dict)
    )
    for key, response in odd_by_key.items():
        groups[key[:5]][key[5]] = response
    expected_probe_ids = {
        str(row["probe_id"])
        for row in ctx.cfg["identification_probe"]["basis"]
    }
    maximum = float(
        ctx.cfg["identification_probe"][
            "maximum_selected_velocity_condition_number"
        ]
    )
    rows = []
    for key in sorted(groups):
        probes = groups[key]
        rank = None
        condition = None
        passed = False
        if set(probes) == expected_probe_ids:
            first_state = min(value[2] for value in probes.values())
            matrix = np.stack(
                [
                    probes[probe_id][1][first_state:, :2].reshape(-1)
                    for probe_id in sorted(expected_probe_ids)
                ],
                axis=1,
            )
            rank = int(np.linalg.matrix_rank(matrix))
            raw_condition = float(np.linalg.cond(matrix))
            condition = raw_condition if math.isfinite(raw_condition) else None
            passed = bool(
                rank == len(expected_probe_ids)
                and condition is not None
                and condition <= maximum
            )
        rows.append(
            {
                "pair_id": key[0],
                "history_member": key[1],
                "target_id": key[2],
                "actual_delay_steps": key[3],
                "actual_slew_scale": key[4],
                "probe_basis_count": len(probes),
                "velocity_response_matrix_rank": rank,
                "selected_velocity_condition_number": condition,
                "condition_number_pass": passed,
            }
        )
    return rows


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
    ctx = r3c.load_stage42r3c3_config(
        args.config,
        source_stage42r3b_run=args.source_stage4_2r3b_run,
        run_dir_override=run_dir,
    )
    selected_pairs, _ = r3c._recompute_selected_pairs(ctx)
    expected_specs = r3c.build_control_specs(ctx, selected_pairs)
    expected_by_id = {
        str(spec["experiment_id"]): spec for spec in expected_specs
    }
    raw_paths = sorted((ctx.paths.control / "raw").glob("*.json.gz"))
    results = [r3c.read_json_gz(path) for path in raw_paths]
    actual_by_id = {
        str(result.get("experiment_id", "")): result for result in results
    }
    id_set_exact = set(actual_by_id) == set(expected_by_id)
    specs_exact = bool(
        id_set_exact
        and all(
            actual_by_id[experiment_id].get("spec") == expected
            for experiment_id, expected in expected_by_id.items()
        )
    )
    state_map = r3c.r3b._selected_state_map(selected_pairs)
    dt_ms = int(
        r3c.r1._r13_ctx(ctx.source_ctx.r1_ctx)
        .r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34.env_cfg[
            "dt_ms"
        ]
    )
    dt_s = dt_ms / 1000.0
    execution_rows = []
    formal_pass_count = 0
    max_current_values = []
    for result in results:
        spec = result["spec"]
        base = r3c.r3b._control_row(
            ctx.source_ctx,
            result,
            state_map[str(spec["state_generation_experiment_id"])],
        )
        trace = _trace_audit(result)
        formal = (
            r3c._formal_metrics(ctx, result)
            if bool(result.get("success"))
            else {}
        )
        formal_pass = bool(
            formal.get("stage3_4_target_tracking_pass", False)
        )
        formal_pass_count += formal_pass
        if formal:
            max_current_values.append(
                float(formal["max_current_utilization"])
            )
        execution_rows.append(
            {
                "experiment_id": str(result.get("experiment_id", "")),
                "pair_id": str(spec["pair_id"]),
                "history_member": str(spec["history_member"]),
                "target_id": str(spec["target_id"]),
                "actual_delay_steps": int(spec["action_delay_steps"]),
                "actual_slew_scale": float(spec["slew_scale"]),
                "probe_id": str(spec["r3c3_probe_id"]),
                "probe_sign": int(spec["r3c3_probe_sign"]),
                "environment_success": bool(result.get("success")),
                "completed": bool(result.get("completed")),
                "failure_reason": str(result.get("failure_reason", "")),
                "trajectory_length": len(result.get("trajectory") or []),
                "restart_exact": bool(base["initial_restart_exact"]),
                "controller_trace_causal": bool(
                    base["controller_trace_causal"]
                ),
                "probe_trace": trace,
                "formal_contract_pass": formal_pass,
                "formal_minimum_signed_margin": (
                    float(
                        formal["stage3_4_tracking_minimum_signed_margin"]
                    )
                    if formal
                    else None
                ),
                "maximum_current_utilization": (
                    float(formal["max_current_utilization"])
                    if formal
                    else None
                ),
            }
        )

    response_rows, odd_by_key = _response_metrics(ctx, results, dt_s)
    history_rows = _history_metrics(ctx, odd_by_key)
    condition_rows = _condition_metrics(ctx, odd_by_key)
    expected_count = int(ctx.cfg["control_matrix"]["expected_rollouts"])
    execution_pass_count = sum(
        row["environment_success"]
        and row["completed"]
        and row["restart_exact"]
        and row["controller_trace_causal"]
        and row["probe_trace"]["passed"]
        for row in execution_rows
    )
    central_pass_count = sum(
        row["central_symmetry_pass"] for row in response_rows
    )
    history_pass_count = sum(
        row["matched_hidden_history_pass"] for row in history_rows
    )
    condition_pass_count = sum(
        row["condition_number_pass"] for row in condition_rows
    )
    maximum_current = (
        max(max_current_values) if max_current_values else None
    )
    maximum_current_allowed = float(
        ctx.cfg["identification_probe"]["maximum_current_utilization"]
    )
    independent_summary = {
        "expected_rollouts": expected_count,
        "n_rollouts": len(results),
        "execution_pass_count": execution_pass_count,
        "runtime_or_environment_error_count": sum(
            not row["environment_success"] for row in execution_rows
        ),
        "plant_restart_fidelity_failure_count": sum(
            row["environment_success"] and not row["restart_exact"]
            for row in execution_rows
        ),
        "controller_causality_failure_count": sum(
            row["environment_success"]
            and row["restart_exact"]
            and not row["controller_trace_causal"]
            for row in execution_rows
        ),
        "probe_execution_failure_count": sum(
            not row["probe_trace"]["passed"] for row in execution_rows
        ),
        "solver_failure_count": sum(
            row["probe_trace"]["solver_failure_count"]
            for row in execution_rows
        ),
        "forbidden_input_count": sum(
            row["probe_trace"]["forbidden_input_count"]
            for row in execution_rows
        ),
        "formal_contract_pass_count": formal_pass_count,
        "formal_contract_failure_count": len(results) - formal_pass_count,
        "response_group_count": len(response_rows),
        "central_symmetry_pass_count": central_pass_count,
        "history_group_count": len(history_rows),
        "matched_hidden_history_pass_count": history_pass_count,
        "condition_group_count": len(condition_rows),
        "condition_number_pass_count": condition_pass_count,
        "maximum_selected_velocity_condition_number": (
            max(
                row["selected_velocity_condition_number"]
                for row in condition_rows
                if row["selected_velocity_condition_number"] is not None
            )
            if any(
                row["selected_velocity_condition_number"] is not None
                for row in condition_rows
            )
            else None
        ),
        "maximum_current_utilization": maximum_current,
        "maximum_current_utilization_allowed": maximum_current_allowed,
        "execution_gate_passed": execution_pass_count == expected_count,
        "central_symmetry_gate_passed": (
            len(response_rows) == expected_count // 2
            and central_pass_count == expected_count // 2
        ),
        "matched_hidden_history_gate_passed": (
            len(history_rows) == expected_count // 4
            and history_pass_count == expected_count // 4
        ),
        "condition_number_gate_passed": (
            len(condition_rows)
            == int(
                ctx.cfg["control_matrix"][
                    "expected_baseline_contexts"
                ]
            )
            and condition_pass_count
            == int(
                ctx.cfg["control_matrix"][
                    "expected_baseline_contexts"
                ]
            )
        ),
        "current_utilization_pass": bool(
            maximum_current is not None
            and maximum_current <= maximum_current_allowed
        ),
    }
    independent_summary["identification_gate_passed"] = all(
        independent_summary[key]
        for key in (
            "execution_gate_passed",
            "central_symmetry_gate_passed",
            "matched_hidden_history_gate_passed",
            "condition_number_gate_passed",
            "current_utilization_pass",
        )
    )

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
    reported = dict(server_audit.get("control_summary") or {})
    comparisons = {
        "expected_rollouts": "expected_rollouts",
        "n_rollouts": "n_rollouts",
        "execution_pass_count": "execution_pass_count",
        "runtime_or_environment_error_count": (
            "runtime_or_environment_error_count"
        ),
        "plant_restart_fidelity_failure_count": (
            "plant_restart_fidelity_failure_count"
        ),
        "controller_causality_failure_count": (
            "controller_causality_failure_count"
        ),
        "formal_contract_pass_count": "formal_contract_pass_count",
        "formal_contract_failure_count": "formal_contract_failure_count",
        "response_group_count": "response_group_count",
        "central_symmetry_pass_count": "central_symmetry_pass_count",
        "history_group_count": "matched_hidden_history_group_count",
        "matched_hidden_history_pass_count": (
            "matched_hidden_history_pass_count"
        ),
        "condition_group_count": "condition_number_group_count",
        "condition_number_pass_count": "condition_number_pass_count",
        "maximum_selected_velocity_condition_number": (
            "maximum_selected_velocity_condition_number"
        ),
        "maximum_current_utilization": "maximum_current_utilization",
        "execution_gate_passed": "execution_gate_passed",
        "central_symmetry_gate_passed": (
            "central_symmetry_gate_passed"
        ),
        "matched_hidden_history_gate_passed": (
            "matched_hidden_history_gate_passed"
        ),
        "condition_number_gate_passed": "condition_number_gate_passed",
        "current_utilization_pass": "current_utilization_pass",
        "identification_gate_passed": "passed",
    }
    summary_agreement = {
        independent_key: (
            independent_summary[independent_key]
            == reported.get(reported_key)
        )
        for independent_key, reported_key in comparisons.items()
    }
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
    failed_central = [
        row for row in response_rows if not row["central_symmetry_pass"]
    ]
    failed_history = [
        row
        for row in history_rows
        if not row["matched_hidden_history_pass"]
    ]
    failed_condition = [
        row for row in condition_rows if not row["condition_number_pass"]
    ]
    if failed_history:
        next_route = (
            "observer_or_hidden_history_state_identification_before_mpc"
        )
    elif failed_central or failed_condition:
        next_route = "revise_local_response_identification_before_mpc"
    elif not independent_summary["current_utilization_pass"]:
        next_route = "reduce_probe_envelope_and_repeat_identification"
    elif independent_summary["identification_gate_passed"]:
        next_route = (
            "preregister_stage4_2r3c4_restart_integrated_deadline_mpc"
        )
    else:
        next_route = "repair_execution_or_integrity_before_scientific_route"
    forensic = {
        "schema_version": 1,
        "stage": r3c.STAGE,
        "purpose": "independent_raw_local_response_forensics",
        "run_dir": str(run_dir),
        "server_audit_path": str(args.server_audit.resolve()),
        "server_audit_sha256": _sha256(args.server_audit),
        "server_audit_compatible": server_audit_compatible,
        "control_raw_inventory": {
            "digest": _canonical_digest(raw_identity),
            "n_files": len(raw_identity),
            "total_bytes": sum(
                int(row["size_bytes"]) for row in raw_identity
            ),
            "files": raw_identity,
        },
        "raw_identity": {
            "expected_count": expected_count,
            "actual_count": len(results),
            "experiment_id_set_exact": id_set_exact,
            "specs_exact": specs_exact,
            "stage_exact_count": sum(
                result.get("stage") == r3c.STAGE for result in results
            ),
            "controller_revision_exact_count": sum(
                result.get("controller_revision")
                == r3c.CONTROLLER_REVISION
                for result in results
            ),
            "completed_count": sum(
                bool(result.get("completed")) for result in results
            ),
            "trajectory_length_counts": dict(
                sorted(
                    Counter(
                        len(result.get("trajectory") or [])
                        for result in results
                    ).items()
                )
            ),
        },
        "independently_recomputed_summary": independent_summary,
        "saved_summary_field_agreement": summary_agreement,
        "all_compared_summary_fields_agree": all(
            summary_agreement.values()
        ),
        "statistics_or_reporting_error_count": (
            0 if all(summary_agreement.values()) else 1
        ),
        "response_ranges": {
            "even_velocity_rmse_m_per_s": _finite_range(
                row["even_velocity_rmse_m_per_s"]
                for row in response_rows
                if row["even_velocity_rmse_m_per_s"] is not None
            ),
            "even_position_rmse_m": _finite_range(
                row["even_position_rmse_m"]
                for row in response_rows
                if row["even_position_rmse_m"] is not None
            ),
            "even_ip_rmse_A": _finite_range(
                row["even_ip_rmse_A"]
                for row in response_rows
                if row["even_ip_rmse_A"] is not None
            ),
            "hidden_odd_velocity_rmse_m_per_s": _finite_range(
                row["odd_velocity_rmse_m_per_s"]
                for row in history_rows
                if row["odd_velocity_rmse_m_per_s"] is not None
            ),
            "hidden_odd_position_rmse_m": _finite_range(
                row["odd_position_rmse_m"]
                for row in history_rows
                if row["odd_position_rmse_m"] is not None
            ),
            "hidden_odd_ip_rmse_A": _finite_range(
                row["odd_ip_rmse_A"]
                for row in history_rows
                if row["odd_ip_rmse_A"] is not None
            ),
            "selected_velocity_condition_number": _finite_range(
                row["selected_velocity_condition_number"]
                for row in condition_rows
                if row["selected_velocity_condition_number"] is not None
            ),
        },
        "failure_inventory": {
            "central_symmetry": failed_central,
            "matched_hidden_history": failed_history,
            "condition_number": failed_condition,
        },
        "execution_rows": execution_rows,
        "central_response_rows": response_rows,
        "matched_hidden_history_rows": history_rows,
        "condition_number_rows": condition_rows,
        "conclusion_guardrails": {
            "runtime_or_environment_error": (
                independent_summary[
                    "runtime_or_environment_error_count"
                ]
                > 0
            ),
            "raw_or_manifest_corruption": bool(
                len(results) != expected_count
                or not id_set_exact
                or not specs_exact
                or not server_audit_compatible
                or not bool(
                    server_audit.get(
                        "raw_and_manifest_integrity_passed"
                    )
                )
            ),
            "plant_restart_failure": (
                independent_summary[
                    "plant_restart_fidelity_failure_count"
                ]
                > 0
            ),
            "controller_causality_failure": (
                independent_summary[
                    "controller_causality_failure_count"
                ]
                > 0
            ),
            "statistics_or_reporting_error": not all(
                summary_agreement.values()
            ),
            "response_identification_design_failure": bool(
                failed_central or failed_history or failed_condition
            ),
            "real_formal_tracking_failure_count": (
                independent_summary["formal_contract_failure_count"]
            ),
            "formal_tracking_is_identification_acceptance_gate": False,
            "development_set_only": True,
            "independent_hidden_history_confirmation": False,
            "probe_trajectories_allowed_in_expert_dataset": False,
        },
        "next_route": next_route,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    r3c.atomic_write_json(output, forensic)
    print(
        json.dumps(
            {
                "output": str(output),
                "output_sha256": _sha256(output),
                "control_raw": len(results),
                "execution_pass": execution_pass_count,
                "central_pass": central_pass_count,
                "history_pass": history_pass_count,
                "condition_pass": condition_pass_count,
                "identification_gate_passed": independent_summary[
                    "identification_gate_passed"
                ],
                "all_compared_summary_fields_agree": all(
                    summary_agreement.values()
                ),
                "next_route": next_route,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
