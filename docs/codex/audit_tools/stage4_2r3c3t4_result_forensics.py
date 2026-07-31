#!/usr/bin/env python3
"""Independent compact forensics for the T4 amplitude diagnostic."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Mapping


EXPECTED_RESULT_SHA256 = (
    "64c5ee745e93cc291c58e06974c7d6292594750a81b9e5dcf81966d32cd840f3"
)
EXPECTED_LOG_SHA256 = (
    "89cbed85105fbad91d75d224e76ecf17ff4cf0aa25c0fedf0e8225cd907dcc66"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        str(row["pair_id"]),
        str(row["history_member"]),
        str(row["target_id"]),
        int(row["actual_delay_steps"]),
        float(row["actual_slew_scale"]),
    )


def _margin_summary(rows: list[Mapping[str, Any]]) -> dict[str, float]:
    margins = [float(row["best_minimum_signed_margin"]) for row in rows]
    return {
        "minimum": min(margins),
        "maximum": max(margins),
        "mean": statistics.fmean(margins),
        "median": statistics.median(margins),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    result_path = args.result.expanduser().resolve()
    log_path = args.log.expanduser().resolve()
    if _sha256(result_path) != EXPECTED_RESULT_SHA256:
        raise ValueError("T4 result hash mismatch")
    if _sha256(log_path) != EXPECTED_LOG_SHA256:
        raise ValueError("T4 log hash mismatch")
    source = json.loads(result_path.read_text(encoding="utf-8"))
    if (
        source["stage"] != "Stage4.2R3c3T4"
        or source["identity"]
        != "eight_basis_unvalidated_amplitude_envelope_v1"
        or int(source["t3_reproduction"]["context_count"]) != 32
        or int(source["t3_reproduction"]["pass_match_count"]) != 32
        or float(
            source["t3_reproduction"][
                "maximum_absolute_margin_error"
            ]
        )
        != 0.0
        or bool(
            source["scientific_classification"][
                "real_tsc_executed_by_this_tool"
            ]
        )
        or bool(
            source["scientific_classification"][
                "r3c4_implementation_authorized"
            ]
        )
    ):
        raise ValueError("T4 identity, reproduction, or guardrail mismatch")

    profile_forensics = []
    for profile in source["profile_summaries"]:
        rows = profile["rows"]
        conditions = profile["condition_rows"]
        upper = [
            float(bounds[1]) for bounds in profile["coefficient_bounds"]
        ]
        if (
            len(rows) != 32
            or len(conditions) != 32
            or len({_key(row) for row in rows}) != 32
        ):
            raise ValueError(
                f"profile inventory mismatch: {profile['profile_id']}"
            )
        pass_count = sum(
            float(row["best_minimum_signed_margin"]) >= -1.0e-12
            for row in rows
        )
        repaired = sum(
            float(row["best_minimum_signed_margin"]) >= -1.0e-12
            and not bool(row["saved_baseline_pass"])
            for row in rows
        )
        regressions = sum(
            float(row["best_minimum_signed_margin"]) < -1.0e-12
            and bool(row["saved_baseline_pass"])
            for row in rows
        )
        condition_pass = sum(
            int(row["matrix_rank"]) == 8
            and math.isfinite(float(row["condition_number"]))
            and float(row["condition_number"]) <= 25.0
            for row in conditions
        )
        if (
            pass_count != int(profile["optimistic_formal_pass_count"])
            or repaired != int(profile["failed_baseline_repair_count"])
            or regressions
            != int(profile["baseline_pass_regression_count"])
            or condition_pass
            != int(profile["extrapolated_condition_pass_count"])
        ):
            raise ValueError(
                f"profile aggregate mismatch: {profile['profile_id']}"
            )
        bound_violations = []
        for row in rows:
            for index, (coefficient, bound) in enumerate(
                zip(row["best_coefficients"], upper)
            ):
                if abs(float(coefficient)) > bound + 1.0e-10:
                    bound_violations.append(
                        {
                            "context": list(_key(row)),
                            "basis_index": index,
                            "coefficient": float(coefficient),
                            "bound": bound,
                        }
                    )
        if bound_violations:
            raise ValueError(
                f"profile bound violation: {profile['profile_id']}"
            )
        failed = [row for row in rows if not bool(row["passed"])]
        repaired_rows = [
            row
            for row in rows
            if bool(row["passed"]) and not bool(row["saved_baseline_pass"])
        ]
        saturation = [
            sum(
                abs(float(row["best_coefficients"][index]))
                >= upper[index] - 1.0e-9
                for row in failed
            )
            for index in range(8)
        ]
        profile_forensics.append(
            {
                "profile_id": profile["profile_id"],
                "profile_name": profile["profile_name"],
                "amplitude_scale": profile["amplitude_scale"],
                "formal_pass_count": pass_count,
                "repair_count": repaired,
                "regression_count": regressions,
                "remaining_failure_count": len(failed),
                "remaining_failure_margin_summary": _margin_summary(failed),
                "remaining_failure_active_constraints": dict(
                    sorted(
                        Counter(
                            str(row["active_constraint"]) for row in failed
                        ).items()
                    )
                ),
                "remaining_failure_saturation_count_by_basis": saturation,
                "repaired_contexts": [
                    {
                        "context": list(_key(row)),
                        "minimum_signed_margin": float(
                            row["best_minimum_signed_margin"]
                        ),
                    }
                    for row in repaired_rows
                ],
                "rank_counts": dict(
                    sorted(
                        Counter(
                            str(row["matrix_rank"]) for row in conditions
                        ).items()
                    )
                ),
                "condition_pass_count": condition_pass,
                "maximum_condition_number": max(
                    float(row["condition_number"])
                    for row in conditions
                ),
                "coefficient_bounds_exact": True,
            }
        )

    route = source["route_summary"]
    if (
        bool(route["transport_only_formal_32_by_2x"])
        or bool(route["uniform_all_formal_32_by_2x"])
        or bool(
            route[
                "any_profile_formal_and_extrapolated_condition_32_by_2x"
            ]
        )
    ):
        raise ValueError("T4 route outcome changed")
    repaired_scale_rows = [
        row
        for row in source["failed_context_minimum_passing_grid_scale"]
        if row["transport_only_first_passing_grid_scale"] is not None
        or row["uniform_all_first_passing_grid_scale"] is not None
    ]
    if (
        len(repaired_scale_rows) != 4
        or any(
            float(row["transport_only_first_passing_grid_scale"]) != 2.0
            or float(row["uniform_all_first_passing_grid_scale"]) != 2.0
            for row in repaired_scale_rows
        )
    ):
        raise ValueError("T4 first-passing-scale outcome changed")

    log_text = log_path.read_text(encoding="utf-8")
    clipping_warning_count = log_text.count(
        "Values in x were outside bounds during a minimize step"
    )
    if clipping_warning_count != 2:
        raise ValueError("unexpected T4 warning inventory")

    output_value = {
        "schema_version": 1,
        "stage": "Stage4.2R3c3T4_result_forensics",
        "input_hashes": {
            result_path.name: EXPECTED_RESULT_SHA256,
            log_path.name: EXPECTED_LOG_SHA256,
        },
        "integrity": {
            "strict_json_parse": True,
            "t3_reproduction_context_count": 32,
            "t3_reproduction_pass_match_count": 32,
            "t3_reproduction_maximum_margin_error": 0.0,
            "profile_count": 6,
            "profile_context_count_each": 32,
            "all_matrix_ranks": 8,
            "all_coefficients_within_profile_bounds": True,
        },
        "profile_forensics": profile_forensics,
        "first_passing_grid_scale_contexts": repaired_scale_rows,
        "route_result": {
            "transport_only_formal_32_by_2x": False,
            "uniform_all_formal_32_by_2x": False,
            "any_profile_formal_and_condition_32_by_2x": False,
            "amplitude_only_route_within_2x_rejected": True,
            "remaining_failures_at_2x": 12,
            "repairs_at_2x": 4,
        },
        "warning_inventory": {
            "slsqp_internal_bound_clipping_warning_count": (
                clipping_warning_count
            ),
            "final_coefficient_bound_violation_count": 0,
            "classification": (
                "optimizer diagnostic warning, not a runtime failure"
            ),
        },
        "classification": {
            "runtime_or_environment_error": False,
            "deployment_or_import_error_in_final_run": False,
            "raw_or_bank_corruption": False,
            "statistics_or_reporting_error": False,
            "pre_execution_amplitude_route_rejection": True,
            "real_closed_loop_control_failure": False,
            "r3c4_implementation_authorized": False,
            "r3c4_real_tsc_execution_authorized": False,
            "bc_dagger_or_rl_allowed": False,
        },
    }
    output = args.output.expanduser().resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite forensic output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            output_value,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(output),
                "output_sha256": _sha256(output),
                "route_result": output_value["route_result"],
                "warning_inventory": output_value["warning_inventory"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
