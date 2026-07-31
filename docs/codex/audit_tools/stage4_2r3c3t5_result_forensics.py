#!/usr/bin/env python3
"""Independent compact forensics for the final T5 quadratic result."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Mapping


EXPECTED_RESULT_SHA256 = (
    "960a82aea9eef90c85bb2b2bc5f6ebb0772c8a8f263915b1122904a3bd13bf82"
)
EXPECTED_FINAL_LOG_SHA256 = (
    "bac22789eeb7d9e229cbb49d4f2a99293ce2941f59e919bb9ab0cb6bf1b84dd4"
)
EXPECTED_FAILED_LOG_SHA256 = (
    "ec91d06110c36ce5a30cef622c8cb792298f82b6c761b700bab2483662e32945"
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


def _comparison(values: list[float]) -> dict[str, Any]:
    return {
        "count": len(values),
        "improved_count": sum(value > 1.0e-12 for value in values),
        "unchanged_count": sum(abs(value) <= 1.0e-12 for value in values),
        "worsened_count": sum(value < -1.0e-12 for value in values),
        "minimum_delta": min(values),
        "maximum_delta": max(values),
        "mean_delta": statistics.fmean(values),
        "median_delta": statistics.median(values),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--final-log", required=True, type=Path)
    parser.add_argument("--failed-log", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    result_path = args.result.expanduser().resolve()
    final_log_path = args.final_log.expanduser().resolve()
    failed_log_path = args.failed_log.expanduser().resolve()
    expected = {
        result_path: EXPECTED_RESULT_SHA256,
        final_log_path: EXPECTED_FINAL_LOG_SHA256,
        failed_log_path: EXPECTED_FAILED_LOG_SHA256,
    }
    mismatches = {
        str(path): (_sha256(path) if path.is_file() else None)
        for path, digest in expected.items()
        if not path.is_file() or _sha256(path) != digest
    }
    if mismatches:
        raise ValueError(f"T5 forensic input mismatch: {mismatches}")
    source = json.loads(result_path.read_text(encoding="utf-8"))
    authentication = source["input_authentication"]
    if (
        source["stage"] != "Stage4.2R3c3T5"
        or source["identity"]
        != "separable_even_odd_quadratic_diagnostic_v1"
        or int(authentication["signed_raw_file_count"]) != 512
        or int(authentication["signed_pair_count"]) != 256
        or float(authentication["maximum_odd_reproduction_error"]) != 0.0
        or float(
            authentication[
                "maximum_signed_endpoint_reproduction_error"
            ]
        )
        != 0.0
        or int(authentication["t3_reproduction_pass_match_count"]) != 32
        or float(
            authentication["maximum_t3_margin_reproduction_error"]
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
        raise ValueError("T5 identity, authentication, or guardrail mismatch")

    rows = source["context_rows"]
    if len(rows) != 32 or len({_key(row) for row in rows}) != 32:
        raise ValueError("T5 context inventory mismatch")
    bound_violations = [
        {
            "context": list(_key(row)),
            "basis_index": index,
            "coefficient": float(coefficient),
        }
        for row in rows
        for index, coefficient in enumerate(row["best_coefficients"])
        if abs(float(coefficient)) > 1.0 + 1.0e-10
    ]
    if bound_violations:
        raise ValueError("T5 coefficient-bound violation")
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
    if (
        pass_count != int(source["optimistic_formal_pass_count"])
        or pass_count != 16
        or repaired != int(source["failed_baseline_repair_count"])
        or repaired != 0
        or regressions != int(source["baseline_pass_regression_count"])
        or regressions != 0
    ):
        raise ValueError("T5 formal aggregate mismatch")
    failed = [row for row in rows if not bool(row["passed"])]
    margins = [
        float(row["best_minimum_signed_margin"]) for row in failed
    ]
    deltas = [float(row["margin_delta_vs_t3"]) for row in failed]
    saturation = [
        sum(
            abs(float(row["best_coefficients"][index]))
            >= 1.0 - 1.0e-9
            for row in failed
        )
        for index in range(8)
    ]
    even = source["even_term_metrics"]
    if int(even["row_count"]) != 256 or len(even["rows"]) != 256:
        raise ValueError("T5 even-term inventory mismatch")
    recomputed_even = {
        "maximum_even_RZ_m": max(
            float(row["maximum_even_RZ_m"]) for row in even["rows"]
        ),
        "median_even_RZ_m": statistics.median(
            float(row["maximum_even_RZ_m"]) for row in even["rows"]
        ),
        "maximum_even_Ip_A": max(
            float(row["maximum_even_Ip_A"]) for row in even["rows"]
        ),
        "maximum_even_speed_m_per_s": max(
            float(row["maximum_even_speed_m_per_s"])
            for row in even["rows"]
        ),
    }
    if any(
        recomputed_even[name] != float(even[name])
        for name in recomputed_even
    ):
        raise ValueError("T5 even-term aggregate mismatch")

    failed_log_text = failed_log_path.read_text(encoding="utf-8")
    final_log_text = final_log_path.read_text(encoding="utf-8")
    if (
        "signed response reproduction mismatch" not in failed_log_text
        or "Traceback" not in failed_log_text
        or "Traceback" in final_log_text
    ):
        raise ValueError("T5 log classification mismatch")

    result = {
        "schema_version": 1,
        "stage": "Stage4.2R3c3T5_result_forensics",
        "input_hashes": {
            path.name: digest for path, digest in expected.items()
        },
        "integrity": {
            "strict_json_parse": True,
            "signed_raw_file_count": 512,
            "signed_pair_count": 256,
            "odd_reproduction_maximum_error": 0.0,
            "signed_endpoint_reproduction_maximum_error": 0.0,
            "t3_pass_match_count": 32,
            "t3_margin_reproduction_maximum_error": 0.0,
            "context_count": 32,
            "coefficient_bound_violation_count": 0,
        },
        "outcome": {
            "optimistic_formal_pass_count": 16,
            "optimistic_formal_failure_count": 16,
            "failed_baseline_repair_count": 0,
            "baseline_pass_regression_count": 0,
            "unchanged_odd_condition_pass_count": int(
                source["unchanged_odd_condition_pass_count"]
            ),
            "maximum_unchanged_odd_condition_number": float(
                source["maximum_unchanged_odd_condition_number"]
            ),
            "separable_quadratic_route_rejected": True,
            "r3c4_implementation_authorized": False,
            "real_tsc_executed": False,
        },
        "failed_margin_summary": {
            "best": max(margins),
            "worst": min(margins),
            "mean": statistics.fmean(margins),
            "median": statistics.median(margins),
        },
        "margin_change_vs_t3": _comparison(deltas),
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
                    Counter(
                        str(row["actual_slew_scale"]) for row in failed
                    ).items()
                )
            ),
            "target_counts": dict(
                sorted(
                    Counter(str(row["target_id"]) for row in failed).items()
                )
            ),
            "history_counts": dict(
                sorted(
                    Counter(
                        str(row["history_member"]) for row in failed
                    ).items()
                )
            ),
            "active_constraint_counts": dict(
                sorted(
                    Counter(
                        str(row["active_constraint"]) for row in failed
                    ).items()
                )
            ),
        },
        "coefficient_saturation_count_by_basis": saturation,
        "even_term_metrics": recomputed_even,
        "attempt_classification": {
            "first_attempt_runtime_authentication_error": True,
            "first_attempt_created_output": False,
            "hotfix_changed_scientific_semantics": False,
            "final_runtime_error": False,
        },
        "classification": {
            "runtime_or_environment_error_in_final_run": False,
            "deployment_or_import_error_in_final_run": False,
            "raw_or_bank_corruption": False,
            "statistics_or_reporting_error": False,
            "pre_execution_model_route_failure": True,
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
                "outcome": result["outcome"],
                "margin_change_vs_t3": result["margin_change_vs_t3"],
                "failed_margin_summary": result["failed_margin_summary"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
