#!/usr/bin/env python3
"""Audit-only optimistic six-basis feasibility diagnostic.

This server-side tool authenticates the immutable T1 raw results, combines
their two odd transport responses with the frozen four R3c3 responses, and
solves the unchanged formal tracking envelope under several global
transport-mode0 amplitude reductions.  The calculation is design evidence
for a possible T2 identification campaign.  It does not change the failed
T1 verdict and cannot authorize R3c4 or learning stages.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import itertools
import json
import math
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.optimize import minimize

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t1_long_separation_zero_net_transport_identification as t1,
)


EXPECTED_RUN_NAME = (
    "stage4_2r3c3t1_long_separation_zero_net_transport_identification_"
    "20260730_204441"
)
EXPECTED_SERVER_AUDIT_SHA256 = (
    "0f24b44f32493b390832474d5c78cc2455a8ba0c455b496b16c04f8deaf3a2bd"
)
EXPECTED_OLD_BANK_SHA256 = (
    "51bb4eeabfc8a4c5cc3983d75469f484a2278e6ef37cf03cf93ac650f9404b32"
)
EXPECTED_RAW_COUNT = 128
EXPECTED_RAW_DIGEST = (
    "f19a04dcb6b597e97517482d602a6cfdb3c0a1f0b4bfd7a1507b90ae2cc0876f"
)
EXPECTED_BASELINE_DIGEST = (
    "3e82504dde79215ed34626531e4f926f5bd65404832790cba6a2eb2f2cc3a97e"
)
MAXIMUM_CONDITION = 25.0
MODE0_SCALES = (1.0, 0.85, 0.8, 0.75, 0.7)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_digest(value: Any) -> str:
    text = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _raw_identity(paths: Sequence[Path]) -> list[dict[str, Any]]:
    return [
        {
            "path": path.name,
            "size_bytes": int(path.stat().st_size),
            "sha256": _sha256(path),
        }
        for path in paths
    ]


def _context_key(spec: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        str(spec["pair_id"]),
        str(spec["history_member"]),
        str(spec["target_id"]),
        int(spec["action_delay_steps"]),
        float(spec["slew_scale"]),
    )


def _old_context_key(context: Mapping[str, Any]) -> tuple[Any, ...]:
    identity = context["audit_identity"]
    return (
        str(identity["pair_id"]),
        str(identity["history_member"]),
        str(identity["target_id"]),
        int(context["actual_delay_steps"]),
        float(context["actual_slew_scale"]),
    )


class FormalEvaluator:
    """Fast exact copy of the frozen formal R/Z/Ip acceptance calculation."""

    def __init__(
        self,
        ctx: t1.Stage42R3C3T1Context,
        baseline: Mapping[str, Any],
    ) -> None:
        self.baseline = baseline
        spec = baseline["spec"]
        r13_ctx = t1.r1._r13_ctx(ctx.source_ctx.r1_ctx)
        self.metric_ctx = SimpleNamespace(
            cfg=copy.deepcopy(
                r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34.cfg
            ),
            env_cfg=(
                r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34.env_cfg
            ),
        )
        r8_ctx = r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx
        self.metric_ctx.cfg["gate"].update(copy.deepcopy(r8_ctx.cfg["gate"]))
        self.gate = r8_ctx.cfg["gate"]
        self.policy = t1.r1.r13._timing_policy(
            r13_ctx,
            float(spec["slew_scale"]),
            policy_id="r42r3c3t1_six_basis_feasibility_diagnostic",
        )
        self.target = t1.r1.r8.s34.target_absolute(
            self.metric_ctx, t1.r1.r8._target_task(spec)
        )
        self.dt_s = float(self.metric_ctx.env_cfg["dt_ms"]) / 1000.0
        self.horizon = len(baseline["trajectory"]) - 1
        if self.horizon != int(self.policy["horizon_steps"]):
            raise ValueError("baseline/formal horizon mismatch")

    def endpoint_margin(
        self, values: np.ndarray, endpoint: int
    ) -> tuple[float, dict[str, Any]]:
        error = values - self.target[None, :]
        speed = np.linalg.norm(
            t1.r1.r8._velocity_components(values, self.dt_s), axis=1
        )
        gate = self.gate
        ip_cfg = gate["ip_tracking"]
        hard = t1.r1.r8.s32._endpoint_constraints_signed(
            error=error,
            speed=speed,
            endpoint=int(endpoint),
            horizon=self.horizon,
            tolerance=float(gate["precise_tolerance_m"]),
            endpoint_speed_limit=float(
                gate["terminal_velocity_max_m_per_s"]
            ),
            rms_speed_limit=float(
                gate["late_velocity_rms_max_m_per_s"]
            ),
            late_window_steps=int(gate["late_window_steps"]),
            ip_tolerance=float(gate["ip_safety_tolerance_A"]),
            streak_steps=int(gate["required_arrival_streak_steps"]),
            dt_ms=int(self.metric_ctx.env_cfg["dt_ms"]),
        )
        window_start = int(hard["window_start_step"])
        hold_ip = error[window_start:, 2]
        terminal_ip_abs = float(abs(error[-1, 2]))
        ip_margins = np.asarray(
            [
                1.0
                - terminal_ip_abs
                / float(ip_cfg["terminal_abs_tolerance_A"]),
                1.0
                - float(np.sqrt(np.mean(hold_ip**2)))
                / float(ip_cfg["hold_rms_tolerance_A"]),
                1.0
                - float(np.max(np.abs(hold_ip)))
                / float(ip_cfg["sustained_max_tolerance_A"]),
            ],
            dtype=float,
        )
        hard_margin = float(hard["minimum_signed_margin"])
        margin = float(min(hard_margin, float(np.min(ip_margins))))
        hard_fields = {
            "position": float(hard["position_signed_margin"]),
            "endpoint_speed": float(
                hard["endpoint_speed_signed_margin"]
            ),
            "endpoint_late_speed": float(
                hard["endpoint_late_speed_signed_margin"]
            ),
            "post_speed": float(hard["post_speed_signed_margin"]),
            "final_speed": float(hard["final_speed_signed_margin"]),
            "ip_safety": float(hard["ip_signed_margin"]),
            "ip_terminal": float(ip_margins[0]),
            "ip_hold_rms": float(ip_margins[1]),
            "ip_sustained": float(ip_margins[2]),
        }
        return margin, {
            "endpoint_step": int(endpoint),
            "minimum_signed_margin": margin,
            "active_constraint": min(
                hard_fields, key=lambda name: hard_fields[name]
            ),
            "constraint_margins": hard_fields,
        }

    def best(
        self, values: np.ndarray
    ) -> tuple[float, dict[str, Any]]:
        rows = [
            self.endpoint_margin(values, int(endpoint))[1]
            for endpoint in self.policy["allowed_arrival_steps"]
            if int(endpoint) <= self.horizon
        ]
        best = max(
            rows,
            key=lambda row: (
                float(row["minimum_signed_margin"]),
                -int(row["endpoint_step"]),
            ),
        )
        return float(best["minimum_signed_margin"]), best


def _velocity_condition(
    columns: Sequence[np.ndarray],
) -> tuple[int, float]:
    matrix = np.stack(
        [np.asarray(column)[3:, :2].reshape(-1) for column in columns],
        axis=1,
    )
    return int(np.linalg.matrix_rank(matrix)), float(np.linalg.cond(matrix))


def _optimize_context(
    evaluator: FormalEvaluator,
    baseline: np.ndarray,
    columns: Sequence[np.ndarray],
) -> dict[str, Any]:
    response = np.stack(columns, axis=2)

    def values(coefficients: np.ndarray) -> np.ndarray:
        return baseline + np.tensordot(
            response, np.asarray(coefficients, dtype=float), axes=(2, 0)
        )

    zero_margin, zero_row = evaluator.best(values(np.zeros(6)))
    if zero_margin >= -1.0e-12:
        return {
            "passed": True,
            "best_minimum_signed_margin": zero_margin,
            "best_endpoint_step": int(zero_row["endpoint_step"]),
            "best_coefficients": [0.0] * 6,
            "active_constraint": str(zero_row["active_constraint"]),
            "method": "exact_baseline_already_passes",
        }

    grid = np.asarray(
        list(itertools.product((-1.0, 0.0, 1.0), repeat=6)),
        dtype=float,
    )
    endpoint_values = [
        int(endpoint)
        for endpoint in evaluator.policy["allowed_arrival_steps"]
        if int(endpoint) <= evaluator.horizon
    ]
    grid_rows = []
    best = (
        zero_margin,
        np.zeros(6),
        zero_row,
        "zero_baseline",
    )
    for coefficients in grid:
        candidate_values = values(coefficients)
        margin, row = evaluator.best(candidate_values)
        grid_rows.append((margin, coefficients.copy(), row))
        if margin > best[0]:
            best = (
                margin,
                coefficients.copy(),
                row,
                "exhaustive_ternary_grid",
            )
    if best[0] < -1.0e-12:
        starts = sorted(grid_rows, key=lambda row: row[0], reverse=True)[:8]
        starts.append((zero_margin, np.zeros(6), zero_row))
        for endpoint in endpoint_values:
            endpoint_starts = sorted(
                starts,
                key=lambda item: evaluator.endpoint_margin(
                    values(item[1]), endpoint
                )[0],
                reverse=True,
            )[:4]
            for _, start, _ in endpoint_starts:
                result = minimize(
                    lambda coefficients: -evaluator.endpoint_margin(
                        values(coefficients), endpoint
                    )[0],
                    np.asarray(start, dtype=float),
                    method="SLSQP",
                    bounds=[(-1.0, 1.0)] * 6,
                    options={
                        "maxiter": 400,
                        "ftol": 1.0e-12,
                        "disp": False,
                    },
                )
                coefficients = np.clip(
                    np.asarray(result.x, dtype=float), -1.0, 1.0
                )
                margin, row = evaluator.best(values(coefficients))
                if margin > best[0]:
                    best = (
                        margin,
                        coefficients,
                        row,
                        "per_endpoint_multistart_slsqp",
                    )
    return {
        "passed": bool(best[0] >= -1.0e-12),
        "best_minimum_signed_margin": float(best[0]),
        "best_endpoint_step": int(best[2]["endpoint_step"]),
        "best_coefficients": np.round(best[1], 12).tolist(),
        "active_constraint": str(best[2]["active_constraint"]),
        "method": best[3],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3b-run", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3c3-run", required=True, type=Path)
    parser.add_argument(
        "--source-stage4-2r3c3-bank-dir", required=True, type=Path
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--server-audit", required=True, type=Path)
    parser.add_argument("--old-audit-bank", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    run_dir = args.run_dir.expanduser().resolve()
    server_audit_path = args.server_audit.expanduser().resolve()
    old_bank_path = args.old_audit_bank.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if run_dir.name != EXPECTED_RUN_NAME:
        raise SystemExit(f"unexpected immutable T1 run: {run_dir}")
    if output == run_dir or run_dir in output.parents:
        raise SystemExit("diagnostic output must remain outside run tree")
    if _sha256(server_audit_path) != EXPECTED_SERVER_AUDIT_SHA256:
        raise SystemExit("T1 server audit hash mismatch")
    if _sha256(old_bank_path) != EXPECTED_OLD_BANK_SHA256:
        raise SystemExit("old R3c3 bank hash mismatch")

    server_audit = json.loads(
        server_audit_path.read_text(encoding="utf-8")
    )
    if (
        not bool(server_audit.get("raw_and_manifest_integrity_passed"))
        or bool(server_audit.get("certified_primary_pass"))
        or bool(
            server_audit.get("combined_condition_number_gate_passed")
        )
    ):
        raise ValueError("T1 server audit outcome changed")
    ctx = t1.load_stage42r3c3t1_config(
        args.config,
        source_stage42r3b_run=args.source_stage4_2r3b_run,
        source_stage42r3c3_run=args.source_stage4_2r3c3_run,
        source_stage42r3c3_bank_dir=(
            args.source_stage4_2r3c3_bank_dir
        ),
        run_dir_override=run_dir,
    )

    raw_dir = ctx.paths.control / "raw"
    raw_paths = sorted(raw_dir.glob("*.json.gz"))
    raw_identity = _raw_identity(raw_paths)
    if (
        len(raw_paths) != EXPECTED_RAW_COUNT
        or _canonical_digest(raw_identity) != EXPECTED_RAW_DIGEST
    ):
        raise ValueError("T1 raw inventory mismatch")
    results = [t1.r3c3.read_json_gz(path) for path in raw_paths]
    if any(
        not bool(result.get("success"))
        or not bool(t1._phase_trace_valid(result)["passed"])
        for result in results
    ):
        raise ValueError("T1 raw execution authentication failed")

    old_bank = json.loads(old_bank_path.read_text(encoding="utf-8"))
    if (
        str(
            old_bank["provenance_contract"][
                "r3c1_baseline_inventory_digest"
            ]
        )
        != EXPECTED_BASELINE_DIGEST
    ):
        raise ValueError("R3c1 baseline inventory digest changed")
    old_by_key = {
        _old_context_key(context): context
        for context in old_bank["contexts"]
    }
    signed: dict[
        tuple[Any, ...], dict[str, dict[int, Mapping[str, Any]]]
    ] = defaultdict(lambda: defaultdict(dict))
    for result in results:
        spec = result["spec"]
        signed[_context_key(spec)][str(spec["r3c3_probe_id"])][
            int(spec["r3c3_probe_sign"])
        ] = result
    if set(old_by_key) != set(signed) or len(signed) != 32:
        raise ValueError("old/new context coverage mismatch")

    contexts = []
    baseline_identity = []
    reproduction_rows = []
    for key in sorted(old_by_key):
        old_context = old_by_key[key]
        baseline_id = str(
            old_context["audit_identity"]["baseline_experiment_id"]
        )
        baseline_path = (
            ctx.source_r3c1_run
            / "stage4_2r3c1_authenticated_visible_manifold_control"
            / "raw"
            / f"{baseline_id}.json.gz"
        )
        baseline = t1.r3c3.read_json_gz(baseline_path)
        baseline_identity.append(
            {
                "path": baseline_path.name,
                "size_bytes": int(baseline_path.stat().st_size),
                "sha256": _sha256(baseline_path),
            }
        )
        baseline_y, _ = t1.r3c3._trajectory_arrays(baseline, 0.01)
        expected_baseline = old_context["offline_design_only_baseline"][
            "RZI_by_state"
        ]
        if not np.array_equal(
            baseline_y, np.asarray(expected_baseline, dtype=float)
        ):
            raise ValueError(f"R3c1 baseline trajectory mismatch: {key}")
        evaluator = FormalEvaluator(ctx, baseline)
        reproduced_margin, reproduced_row = evaluator.best(baseline_y)
        saved = old_context["offline_design_only_baseline"][
            "formal_metrics"
        ]
        reproduction_rows.append(
            {
                "context": list(key),
                "saved_pass": bool(
                    saved["stage3_4_target_tracking_pass"]
                ),
                "reproduced_pass": bool(
                    reproduced_margin >= -1.0e-12
                ),
                "saved_margin": float(
                    saved[
                        "stage3_4_tracking_minimum_signed_margin"
                    ]
                ),
                "reproduced_margin": reproduced_margin,
                "absolute_margin_error": abs(
                    float(
                        saved[
                            "stage3_4_tracking_minimum_signed_margin"
                        ]
                    )
                    - reproduced_margin
                ),
                "reproduced_endpoint": int(
                    reproduced_row["endpoint_step"]
                ),
            }
        )
        old_position_columns = [
            np.asarray(
                response["delta_RZI_by_state"], dtype=float
            )
            for response in sorted(
                old_context["responses"],
                key=lambda row: int(row["basis_index"]),
            )
        ]
        old_velocity_columns = [
            np.asarray(
                response["delta_velocity_RZ_by_state"], dtype=float
            )
            for response in sorted(
                old_context["responses"],
                key=lambda row: int(row["basis_index"]),
            )
        ]
        new_position_columns = []
        new_velocity_columns = []
        for probe_id in ("transport_mode0", "transport_mode1"):
            members = signed[key][probe_id]
            if set(members) != {-1, 1}:
                raise ValueError(f"signed response coverage mismatch: {key}")
            plus_y, plus_v = t1.r3c3._trajectory_arrays(
                members[1], 0.01
            )
            minus_y, minus_v = t1.r3c3._trajectory_arrays(
                members[-1], 0.01
            )
            new_position_columns.append((plus_y - minus_y) / 2.0)
            new_velocity_columns.append((plus_v - minus_v) / 2.0)
        contexts.append(
            {
                "key": key,
                "baseline": baseline_y,
                "evaluator": evaluator,
                "old_position_columns": old_position_columns,
                "old_velocity_columns": old_velocity_columns,
                "new_position_columns": new_position_columns,
                "new_velocity_columns": new_velocity_columns,
            }
        )

    if _canonical_digest(sorted(baseline_identity, key=lambda row: row["path"])) != EXPECTED_BASELINE_DIGEST:
        raise ValueError("recomputed R3c1 baseline inventory mismatch")
    if (
        sum(row["saved_pass"] for row in reproduction_rows) != 16
        or any(
            row["saved_pass"] != row["reproduced_pass"]
            for row in reproduction_rows
        )
        or max(row["absolute_margin_error"] for row in reproduction_rows)
        > 1.0e-12
    ):
        raise ValueError("formal evaluator reproduction failed")

    scale_summaries = []
    for scale0 in MODE0_SCALES:
        rows = []
        for context in contexts:
            position_columns = [
                *context["old_position_columns"],
                context["new_position_columns"][0] * float(scale0),
                context["new_position_columns"][1],
            ]
            velocity_columns = [
                *context["old_velocity_columns"],
                context["new_velocity_columns"][0] * float(scale0),
                context["new_velocity_columns"][1],
            ]
            rank, condition = _velocity_condition(velocity_columns)
            optimized = _optimize_context(
                context["evaluator"],
                context["baseline"],
                position_columns,
            )
            rows.append(
                {
                    "pair_id": context["key"][0],
                    "history_member": context["key"][1],
                    "target_id": context["key"][2],
                    "actual_delay_steps": context["key"][3],
                    "actual_slew_scale": context["key"][4],
                    "matrix_rank": rank,
                    "condition_number": condition,
                    "condition_number_pass": bool(
                        rank == 6
                        and math.isfinite(condition)
                        and condition <= MAXIMUM_CONDITION
                    ),
                    **optimized,
                }
            )
        pass_count = sum(row["passed"] for row in rows)
        condition_pass_count = sum(
            row["condition_number_pass"] for row in rows
        )
        scale_summaries.append(
            {
                "transport_mode0_scale": float(scale0),
                "transport_mode0_amplitude": 0.0075 * float(scale0),
                "transport_mode1_scale": 1.0,
                "transport_mode1_amplitude": 0.0075,
                "context_count": len(rows),
                "optimistic_formal_pass_count": pass_count,
                "optimistic_formal_failure_count": len(rows) - pass_count,
                "failed_baseline_repair_count": sum(
                    row["passed"]
                    and not reproduction_rows[index]["saved_pass"]
                    for index, row in enumerate(rows)
                ),
                "baseline_pass_regression_count": sum(
                    not row["passed"]
                    and reproduction_rows[index]["saved_pass"]
                    for index, row in enumerate(rows)
                ),
                "best_remaining_failed_margin": (
                    max(
                        row["best_minimum_signed_margin"]
                        for row in rows
                        if not row["passed"]
                    )
                    if pass_count < len(rows)
                    else None
                ),
                "worst_remaining_failed_margin": (
                    min(
                        row["best_minimum_signed_margin"]
                        for row in rows
                        if not row["passed"]
                    )
                    if pass_count < len(rows)
                    else None
                ),
                "condition_pass_count": condition_pass_count,
                "condition_failure_count": (
                    len(rows) - condition_pass_count
                ),
                "maximum_condition_number": max(
                    row["condition_number"] for row in rows
                ),
                "all_design_gates_pass": bool(
                    pass_count == len(rows)
                    and condition_pass_count == len(rows)
                ),
                "context_rows": rows,
            }
        )

    original = scale_summaries[0]
    reported_summary = server_audit["control_summary"]
    if (
        int(original["condition_pass_count"])
        != int(reported_summary["combined_condition_pass_count"])
        or not math.isclose(
            float(original["maximum_condition_number"]),
            float(
                reported_summary[
                    "maximum_combined_velocity_condition_number"
                ]
            ),
            rel_tol=0.0,
            abs_tol=1.0e-12,
        )
    ):
        raise ValueError(
            "six-basis velocity condition reproduction failed"
        )

    result = {
        "schema_version": 2,
        "stage": "Stage4.2R3c3T1_six_basis_feasibility_diagnostic",
        "purpose": (
            "audit-only T2 amplitude selection; T1 remains failed and "
            "R3c4 remains unauthorized"
        ),
        "inputs": {
            "immutable_t1_run": str(run_dir),
            "server_audit_sha256": _sha256(server_audit_path),
            "old_audit_bank_sha256": _sha256(old_bank_path),
            "t1_raw_inventory_digest": _canonical_digest(raw_identity),
            "r3c1_baseline_inventory_digest": _canonical_digest(
                sorted(baseline_identity, key=lambda row: row["path"])
            ),
        },
        "formal_evaluator_reproduction": {
            "context_count": len(reproduction_rows),
            "saved_pass_count": sum(
                row["saved_pass"] for row in reproduction_rows
            ),
            "pass_match_count": sum(
                row["saved_pass"] == row["reproduced_pass"]
                for row in reproduction_rows
            ),
            "maximum_absolute_margin_error": max(
                row["absolute_margin_error"]
                for row in reproduction_rows
            ),
            "rows": reproduction_rows,
        },
        "coefficient_contract": {
            "basis_count": 6,
            "coefficient_lower_bound": -1.0,
            "coefficient_upper_bound": 1.0,
            "formal_timing_changed": False,
            "position_tolerance_m": 0.03,
            "speed_tolerance_m_per_s": 0.1,
        },
        "scale_summaries": scale_summaries,
        "scientific_classification": {
            "real_tsc_executed_by_this_tool": False,
            "t1_verdict_changed": False,
            "runtime_error": False,
            "statistics_or_reporting_error": False,
            "design_diagnostic_only": True,
            "linear_superposition_validated_for_six_basis": False,
            "t2_real_tsc_validation_required": True,
            "r3c4_authorized": False,
            "bc_dagger_or_rl_allowed": False,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    t1.r3c3.atomic_write_json(output, result)
    print(
        json.dumps(
            {
                "output": str(output),
                "output_sha256": _sha256(output),
                "scale_summaries": [
                    {
                        key: row[key]
                        for key in (
                            "transport_mode0_scale",
                            "optimistic_formal_pass_count",
                            "condition_pass_count",
                            "maximum_condition_number",
                            "all_design_gates_pass",
                        )
                    }
                    for row in scale_summaries
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
