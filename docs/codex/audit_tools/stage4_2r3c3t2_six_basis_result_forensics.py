#!/usr/bin/env python3
"""Compact forensic comparison for the failed post-T2 six-basis gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Mapping


EXPECTED_MANIFEST_SHA256 = (
    "46bc47cfc1b8fb779b9ed1308e1d322364e80e780e8596e58e9b9cdc5d0dc2b5"
)
EXPECTED_FEASIBILITY_SHA256 = (
    "1c74a6c1ef05ff447eb1030f7a7ef1e13390eacfc74e795a556899405c95eacb"
)
EXPECTED_AUDIT_BANK_SHA256 = (
    "0ef668da87d97012c101245556ee268b00cac535011b6025aa3fecc82bbb6081"
)
EXPECTED_CONTROLLER_BANK_SHA256 = (
    "81e3c309d9055ba23587f4162641692680464d465f68342a845184e03b53b2fe"
)
EXPECTED_OLD_FOUR_SHA256 = (
    "0670823674a59cdf640e47a9ebc32385197336c2cbae3c66c2345f4be662b070"
)
EXPECTED_T1_SIX_SHA256 = (
    "e7bc8f0168ff1d2019f1a9a232b5152a27d46a66a92f9542d31d80c6942c3164"
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
        int(row.get("actual_delay_steps", row.get("delay_steps"))),
    )


def _comparison(values: list[float]) -> dict[str, Any]:
    return {
        "count": len(values),
        "improved_count": sum(value > 1.0e-12 for value in values),
        "unchanged_count": sum(abs(value) <= 1.0e-12 for value in values),
        "worsened_count": sum(value < -1.0e-12 for value in values),
        "minimum_margin_delta": min(values),
        "maximum_margin_delta": max(values),
        "mean_margin_delta": statistics.fmean(values),
        "median_margin_delta": statistics.median(values),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", required=True, type=Path)
    parser.add_argument("--old-four-feasibility", required=True, type=Path)
    parser.add_argument("--t1-six-feasibility", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    result_dir = args.result_dir.expanduser().resolve()
    manifest_path = (
        result_dir
        / "stage4_2r3c3t2_combined_six_basis_manifest_v1.json"
    )
    feasibility_path = (
        result_dir
        / "stage4_2r3c3t2_six_basis_optimistic_feasibility_v1.json"
    )
    audit_bank_path = (
        result_dir
        / "stage4_2r3c3t2_combined_six_basis_audit_bank_v1.json"
    )
    controller_bank_path = (
        result_dir
        / "stage4_2r3c3t2_combined_six_basis_controller_bank_v1.json"
    )
    expected = {
        manifest_path: EXPECTED_MANIFEST_SHA256,
        feasibility_path: EXPECTED_FEASIBILITY_SHA256,
        audit_bank_path: EXPECTED_AUDIT_BANK_SHA256,
        controller_bank_path: EXPECTED_CONTROLLER_BANK_SHA256,
        args.old_four_feasibility.expanduser().resolve(): (
            EXPECTED_OLD_FOUR_SHA256
        ),
        args.t1_six_feasibility.expanduser().resolve(): EXPECTED_T1_SIX_SHA256,
    }
    actual_hashes = {
        path: (_sha256(path) if path.is_file() else None)
        for path in expected
    }
    mismatches = {
        str(path): actual_hashes[path]
        for path, digest in expected.items()
        if actual_hashes[path] != digest
    }
    if mismatches:
        raise ValueError(f"forensic input hash mismatch: {mismatches}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    current = json.loads(feasibility_path.read_text(encoding="utf-8"))
    old_four = json.loads(
        args.old_four_feasibility.read_text(encoding="utf-8")
    )
    t1_six = json.loads(
        args.t1_six_feasibility.read_text(encoding="utf-8")
    )
    if (
        bool(manifest["all_preregistered_gates_pass"])
        or bool(current["all_preregistered_gates_pass"])
        or int(current["optimistic_formal_pass_count"]) != 16
        or int(current["failed_baseline_repair_count"]) != 0
        or int(current["baseline_pass_regression_count"]) != 0
    ):
        raise ValueError("post-T2 feasibility outcome changed")

    rows = current["context_rows"]
    failed = [row for row in rows if not bool(row["passed"])]
    old_failed = {
        _key(row): row
        for row in old_four["bounded_oracle"]["failed_contexts"]
    }
    t1_rows = {
        _key(row): row
        for row in t1_six["scale_summaries"][0]["context_rows"]
    }
    if (
        len(rows) != 32
        or len(failed) != 16
        or set(map(_key, failed)) != set(old_failed)
        or not set(map(_key, failed)).issubset(t1_rows)
    ):
        raise ValueError("failed-context identity mismatch")

    old_deltas = []
    t1_deltas = []
    failed_rows = []
    saturation_by_basis = [0] * 6
    for row in failed:
        key = _key(row)
        margin = float(row["best_minimum_signed_margin"])
        old_margin = float(old_failed[key]["best_minimum_signed_margin"])
        t1_margin = float(t1_rows[key]["best_minimum_signed_margin"])
        coefficients = list(map(float, row["best_coefficients"]))
        for index, coefficient in enumerate(coefficients):
            if abs(coefficient) >= 1.0 - 1.0e-9:
                saturation_by_basis[index] += 1
        old_deltas.append(margin - old_margin)
        t1_deltas.append(margin - t1_margin)
        failed_rows.append(
            {
                "pair_id": row["pair_id"],
                "history_member": row["history_member"],
                "target_id": row["target_id"],
                "actual_delay_steps": row["actual_delay_steps"],
                "actual_slew_scale": row["actual_slew_scale"],
                "best_minimum_signed_margin": margin,
                "old_four_margin": old_margin,
                "margin_delta_vs_old_four": margin - old_margin,
                "t1_six_margin": t1_margin,
                "margin_delta_vs_t1_six": margin - t1_margin,
                "active_constraint": row["active_constraint"],
                "best_endpoint_step": row["best_endpoint_step"],
                "best_coefficients": coefficients,
                "coefficient_l1": sum(abs(value) for value in coefficients),
                "saturated_coefficient_count": sum(
                    abs(value) >= 1.0 - 1.0e-9
                    for value in coefficients
                ),
            }
        )
    failed_rows.sort(key=lambda row: row["best_minimum_signed_margin"])
    margins = [
        float(row["best_minimum_signed_margin"]) for row in failed_rows
    ]
    result = {
        "schema_version": 1,
        "stage": "Stage4.2R3c3T2_six_basis_result_forensics",
        "input_hashes": {
            path.name: digest for path, digest in expected.items()
        },
        "outcome": {
            "context_count": 32,
            "optimistic_formal_pass_count": 16,
            "optimistic_formal_failure_count": 16,
            "failed_baseline_repair_count": 0,
            "baseline_pass_regression_count": 0,
            "condition_pass_count": 32,
            "maximum_condition_number": float(
                current["maximum_condition_number"]
            ),
            "all_preregistered_gates_pass": False,
            "r3c4_implementation_authorized": False,
            "real_tsc_executed": False,
        },
        "failed_margin_summary": {
            "best_remaining_failed_margin": max(margins),
            "worst_remaining_failed_margin": min(margins),
            "mean_failed_margin": statistics.fmean(margins),
            "median_failed_margin": statistics.median(margins),
        },
        "active_constraint_counts": dict(
            sorted(Counter(row["active_constraint"] for row in failed).items())
        ),
        "failure_strata": {
            "delay_counts": dict(
                sorted(
                    Counter(
                        str(row["actual_delay_steps"]) for row in failed
                    ).items()
                )
            ),
            "slew_counts": dict(
                sorted(
                    Counter(str(row["actual_slew_scale"]) for row in failed)
                    .items()
                )
            ),
            "target_counts": dict(
                sorted(Counter(row["target_id"] for row in failed).items())
            ),
            "history_counts": dict(
                sorted(
                    Counter(row["history_member"] for row in failed).items()
                )
            ),
        },
        "coefficient_saturation": {
            "failed_context_count": 16,
            "saturation_count_by_basis": saturation_by_basis,
            "basis_labels": [
                "early_mode0",
                "early_mode1",
                "deadline_mode0",
                "deadline_mode1",
                "held_transport_mode0",
                "held_transport_mode1",
            ],
        },
        "margin_change_vs_old_four": _comparison(old_deltas),
        "margin_change_vs_t1_six": _comparison(t1_deltas),
        "failed_contexts": failed_rows,
        "classification": {
            "runtime_or_environment_error": False,
            "deployment_or_import_error": False,
            "raw_or_bank_corruption": False,
            "statistics_or_reporting_error": False,
            "pre_execution_design_failure": True,
            "real_closed_loop_control_failure": False,
            "r3c4_implementation_authorized": False,
            "bc_dagger_or_rl_allowed": False,
        },
    }
    output = args.output.expanduser().resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite forensic output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(output),
                "output_sha256": _sha256(output),
                "best_remaining_failed_margin": max(margins),
                "worst_remaining_failed_margin": min(margins),
                "active_constraint_counts": result[
                    "active_constraint_counts"
                ],
                "saturation_count_by_basis": saturation_by_basis,
                "margin_change_vs_old_four": result[
                    "margin_change_vs_old_four"
                ],
                "margin_change_vs_t1_six": result[
                    "margin_change_vs_t1_six"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
