#!/usr/bin/env python3
"""Independent compact forensics for the failed T3 eight-basis audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Mapping


EXPECTED_T3_MANIFEST_SHA256 = (
    "2c9389af0ea8d0f9538a0e4af34e604331981e77cfc0bc9c5bf353617c541b09"
)
EXPECTED_T3_FEASIBILITY_SHA256 = (
    "08c253f7e8b66165704ec22e7b56c7e5c1abb1a30b8738be8b1d240211729744"
)
EXPECTED_T3_AUDIT_BANK_SHA256 = (
    "f6cf5ae8642b68fc9947eaa1c2a3d18074e4e3e5be1f422f50ffa03f1a1a1970"
)
EXPECTED_T3_CONTROLLER_BANK_SHA256 = (
    "6328ef4116ea5a2ecac66d04583fb92af7830ad5ff6ea484486524cbd2021e86"
)
EXPECTED_T2_SIX_SHA256 = (
    "1c74a6c1ef05ff447eb1030f7a7ef1e13390eacfc74e795a556899405c95eacb"
)
EXPECTED_T1_SIX_SHA256 = (
    "e7bc8f0168ff1d2019f1a9a232b5152a27d46a66a92f9542d31d80c6942c3164"
)
EXPECTED_OLD_FOUR_SHA256 = (
    "0670823674a59cdf640e47a9ebc32385197336c2cbae3c66c2345f4be662b070"
)
EXPECTED_PROVENANCE_DIGEST = (
    "a536183fc8e192fafc8c28bdc9897ecf3acb5dc9f0c5ed6257f236e2e8c03935"
)
BASIS_LABELS = [
    "r3c3_early_mode0",
    "r3c3_early_mode1",
    "r3c3_deadline_mode0",
    "r3c3_deadline_mode1",
    "t1_long_separation_mode0",
    "t1_long_separation_mode1",
    "t2_held_transport_mode0",
    "t2_held_transport_mode1",
]


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


def _strata(rows: list[Mapping[str, Any]]) -> dict[str, dict[str, int]]:
    return {
        "delay_counts": dict(
            sorted(
                Counter(
                    str(row.get("actual_delay_steps", row.get("delay_steps")))
                    for row in rows
                ).items()
            )
        ),
        "slew_counts": dict(
            sorted(
                Counter(str(row["actual_slew_scale"]) for row in rows).items()
            )
        ),
        "target_counts": dict(
            sorted(Counter(str(row["target_id"]) for row in rows).items())
        ),
        "history_counts": dict(
            sorted(
                Counter(str(row["history_member"]) for row in rows).items()
            )
        ),
    }


def _condition_as_row(row: Mapping[str, Any]) -> dict[str, Any]:
    context = row["context"]
    return {
        "pair_id": str(context[0]),
        "history_member": str(context[1]),
        "target_id": str(context[2]),
        "actual_delay_steps": int(context[3]),
        "actual_slew_scale": float(context[4]),
        "matrix_rank": int(row["matrix_rank"]),
        "condition_number": float(row["condition_number"]),
        "passed": bool(row["passed"]),
    }


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", required=True, type=Path)
    parser.add_argument("--t2-six-feasibility", required=True, type=Path)
    parser.add_argument("--t1-six-feasibility", required=True, type=Path)
    parser.add_argument("--old-four-feasibility", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    result_dir = args.result_dir.expanduser().resolve()
    manifest_path = (
        result_dir / "stage4_2r3c3t3_eight_basis_manifest_v1.json"
    )
    feasibility_path = (
        result_dir / "stage4_2r3c3t3_eight_basis_feasibility_v1.json"
    )
    audit_bank_path = (
        result_dir / "stage4_2r3c3t3_eight_basis_audit_bank_v1.json"
    )
    controller_bank_path = (
        result_dir / "stage4_2r3c3t3_eight_basis_controller_bank_v1.json"
    )
    t2_six_path = args.t2_six_feasibility.expanduser().resolve()
    t1_six_path = args.t1_six_feasibility.expanduser().resolve()
    old_four_path = args.old_four_feasibility.expanduser().resolve()
    expected = {
        manifest_path: EXPECTED_T3_MANIFEST_SHA256,
        feasibility_path: EXPECTED_T3_FEASIBILITY_SHA256,
        audit_bank_path: EXPECTED_T3_AUDIT_BANK_SHA256,
        controller_bank_path: EXPECTED_T3_CONTROLLER_BANK_SHA256,
        t2_six_path: EXPECTED_T2_SIX_SHA256,
        t1_six_path: EXPECTED_T1_SIX_SHA256,
        old_four_path: EXPECTED_OLD_FOUR_SHA256,
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

    manifest = _load(manifest_path)
    current = _load(feasibility_path)
    audit_bank = _load(audit_bank_path)
    controller_bank = _load(controller_bank_path)
    t2_six = _load(t2_six_path)
    t1_six = _load(t1_six_path)
    old_four = _load(old_four_path)

    manifest_outputs = {
        str(row["path"]): (int(row["size_bytes"]), str(row["sha256"]))
        for row in manifest["outputs"]
    }
    expected_outputs = {
        audit_bank_path.name: (
            audit_bank_path.stat().st_size,
            EXPECTED_T3_AUDIT_BANK_SHA256,
        ),
        controller_bank_path.name: (
            controller_bank_path.stat().st_size,
            EXPECTED_T3_CONTROLLER_BANK_SHA256,
        ),
        feasibility_path.name: (
            feasibility_path.stat().st_size,
            EXPECTED_T3_FEASIBILITY_SHA256,
        ),
    }
    if manifest_outputs != expected_outputs:
        raise ValueError("T3 manifest inventory does not match output files")

    if (
        bool(manifest["all_preregistered_gates_pass"])
        or bool(current["all_preregistered_gates_pass"])
        or int(current["context_count"]) != 32
        or int(current["optimistic_formal_pass_count"]) != 16
        or int(current["failed_baseline_repair_count"]) != 0
        or int(current["baseline_pass_regression_count"]) != 0
        or int(current["eight_basis_condition_pass_count"]) != 11
        or bool(current["scientific_classification"]["runtime_error"])
        or bool(
            current["scientific_classification"][
                "statistics_or_reporting_error"
            ]
        )
    ):
        raise ValueError("T3 outcome changed from the result being audited")
    provenance_digests = {
        str(manifest["provenance_digest"]),
        str(current["provenance_digest"]),
        str(audit_bank["provenance_digest"]),
        str(controller_bank["provenance_digest"]),
    }
    if provenance_digests != {EXPECTED_PROVENANCE_DIGEST}:
        raise ValueError(
            f"T3 provenance digest mismatch: {provenance_digests}"
        )
    if (
        int(audit_bank["basis_count"]) != 8
        or int(controller_bank["basis_count"]) != 8
        or int(controller_bank["sample_count"]) != 32
        or bool(controller_bank["demonstration_data"])
        or not bool(controller_bank["identification_only"])
    ):
        raise ValueError("T3 bank scientific guardrail mismatch")
    reproduction = audit_bank["formal_evaluator_reproduction"]
    if (
        int(reproduction["context_count"]) != 32
        or int(reproduction["pass_match_count"]) != 32
        or float(reproduction["maximum_absolute_margin_error"]) != 0.0
    ):
        raise ValueError("frozen formal evaluator reproduction mismatch")

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
    t2_rows = {_key(row): row for row in t2_six["context_rows"]}
    if (
        len(rows) != 32
        or len(failed) != 16
        or len({_key(row) for row in rows}) != 32
        or set(map(_key, failed)) != set(old_failed)
        or not set(map(_key, failed)).issubset(t1_rows)
        or not set(map(_key, failed)).issubset(t2_rows)
    ):
        raise ValueError("T3 failed-context identity mismatch")

    condition_rows = [
        _condition_as_row(row)
        for row in audit_bank["eight_basis_condition_audit"]["rows"]
    ]
    condition_by_key = {_key(row): row for row in condition_rows}
    if (
        len(condition_rows) != 32
        or len(condition_by_key) != 32
        or set(condition_by_key) != {_key(row) for row in rows}
        or sum(row["passed"] for row in condition_rows) != 11
        or max(row["condition_number"] for row in condition_rows)
        != float(current["maximum_condition_number"])
    ):
        raise ValueError("T3 condition-audit mismatch")

    old_deltas: list[float] = []
    t1_deltas: list[float] = []
    t2_deltas: list[float] = []
    saturation_by_basis = [0] * 8
    failed_rows = []
    for row in failed:
        key = _key(row)
        margin = float(row["best_minimum_signed_margin"])
        old_margin = float(old_failed[key]["best_minimum_signed_margin"])
        t1_margin = float(t1_rows[key]["best_minimum_signed_margin"])
        t2_margin = float(t2_rows[key]["best_minimum_signed_margin"])
        coefficients = list(map(float, row["best_coefficients"]))
        for index, coefficient in enumerate(coefficients):
            if abs(coefficient) >= 1.0 - 1.0e-9:
                saturation_by_basis[index] += 1
        old_deltas.append(margin - old_margin)
        t1_deltas.append(margin - t1_margin)
        t2_deltas.append(margin - t2_margin)
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
                "t2_six_margin": t2_margin,
                "margin_delta_vs_t2_six": margin - t2_margin,
                "active_constraint": row["active_constraint"],
                "best_endpoint_step": row["best_endpoint_step"],
                "best_coefficients": coefficients,
                "coefficient_l1": sum(abs(value) for value in coefficients),
                "saturated_coefficient_count": sum(
                    abs(value) >= 1.0 - 1.0e-9
                    for value in coefficients
                ),
                "condition_number": condition_by_key[key][
                    "condition_number"
                ],
                "condition_gate_passed": condition_by_key[key]["passed"],
            }
        )
    failed_rows.sort(key=lambda row: row["best_minimum_signed_margin"])
    failed_margins = [
        float(row["best_minimum_signed_margin"]) for row in failed_rows
    ]
    condition_failed = [
        row for row in condition_rows if not bool(row["passed"])
    ]
    condition_numbers = [
        float(row["condition_number"]) for row in condition_rows
    ]
    rank_counts = dict(
        sorted(
            Counter(str(row["matrix_rank"]) for row in condition_rows).items()
        )
    )
    formal_condition_cross = Counter()
    formal_by_key = {_key(row): bool(row["passed"]) for row in rows}
    for row in condition_rows:
        label = (
            ("formal_pass" if formal_by_key[_key(row)] else "formal_fail")
            + "__"
            + ("condition_pass" if row["passed"] else "condition_fail")
        )
        formal_condition_cross[label] += 1
    worst_condition_rows = sorted(
        condition_rows,
        key=lambda row: row["condition_number"],
        reverse=True,
    )[:10]

    result = {
        "schema_version": 1,
        "stage": "Stage4.2R3c3T3_eight_basis_result_forensics",
        "input_hashes": {
            path.name: digest for path, digest in expected.items()
        },
        "integrity": {
            "manifest_inventory_exact": True,
            "provenance_digest": EXPECTED_PROVENANCE_DIGEST,
            "provenance_digest_exact_across_outputs": True,
            "formal_evaluator_context_count": 32,
            "formal_evaluator_pass_match_count": 32,
            "formal_evaluator_maximum_absolute_margin_error": 0.0,
            "controller_bank_identification_only": True,
            "controller_bank_demonstration_data": False,
        },
        "outcome": {
            "context_count": 32,
            "optimistic_formal_pass_count": 16,
            "optimistic_formal_failure_count": 16,
            "failed_baseline_repair_count": 0,
            "baseline_pass_regression_count": 0,
            "condition_pass_count": 11,
            "condition_failure_count": 21,
            "maximum_condition_number": max(condition_numbers),
            "all_preregistered_gates_pass": False,
            "r3c4_implementation_authorized": False,
            "real_tsc_executed": False,
        },
        "failed_margin_summary": {
            "best_remaining_failed_margin": max(failed_margins),
            "worst_remaining_failed_margin": min(failed_margins),
            "mean_failed_margin": statistics.fmean(failed_margins),
            "median_failed_margin": statistics.median(failed_margins),
        },
        "active_constraint_counts": dict(
            sorted(Counter(row["active_constraint"] for row in failed).items())
        ),
        "failed_endpoint_counts": dict(
            sorted(
                Counter(str(row["best_endpoint_step"]) for row in failed)
                .items()
            )
        ),
        "failure_strata": _strata(failed),
        "coefficient_saturation": {
            "failed_context_count": 16,
            "saturation_count_by_basis": saturation_by_basis,
            "basis_labels": BASIS_LABELS,
        },
        "margin_change_vs_old_four": _comparison(old_deltas),
        "margin_change_vs_t1_six": _comparison(t1_deltas),
        "margin_change_vs_t2_six": _comparison(t2_deltas),
        "condition_audit": {
            "rank_counts": rank_counts,
            "minimum_condition_number": min(condition_numbers),
            "median_condition_number": statistics.median(condition_numbers),
            "maximum_condition_number": max(condition_numbers),
            "pass_count": 11,
            "failure_count": 21,
            "formal_condition_cross_counts": dict(
                sorted(formal_condition_cross.items())
            ),
            "condition_failure_strata": _strata(condition_failed),
            "worst_contexts": worst_condition_rows,
        },
        "failed_contexts": failed_rows,
        "classification": {
            "runtime_or_environment_error": False,
            "deployment_or_import_error": False,
            "raw_or_bank_corruption": False,
            "statistics_or_reporting_error": False,
            "pre_execution_design_failure": True,
            "eight_basis_identifiability_gate_failure": True,
            "optimistic_formal_control_design_failure": True,
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
        json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(output),
                "output_sha256": _sha256(output),
                "failed_margin_summary": result["failed_margin_summary"],
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
                "margin_change_vs_t2_six": result[
                    "margin_change_vs_t2_six"
                ],
                "condition_audit": result["condition_audit"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
