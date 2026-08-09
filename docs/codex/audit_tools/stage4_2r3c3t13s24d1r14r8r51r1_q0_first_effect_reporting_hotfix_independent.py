#!/usr/bin/env python3
"""Structurally independent raw replay of the R8R51R1 q0 reporting hotfix."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence


STAGE = "Stage4.2R3c3T13S24D1R14R8R51R1"
RUN_NAME = (
    "stage4_2r3c3t13s24d1r14r8r51r1_"
    "reduced_q0_transport_bridge_q0_gate_integration_sentinel"
)
CONFIG_SHA256 = "a40569191b5d4fc3f8b2663e52f188ed0cf3f211280574d1889750ae6d516c4f"
STAGE_MANIFEST_SHA256 = "c58148f603913c70d5e35626f72dc3541892ad4ec2a919db139a45b51feaa076"
RAW_PRIMARY_SHA256 = "925dbed532e4dcda721592fe409158c7defd89636d94affef9157646df5981a1"
RAW_INDEPENDENT_SHA256 = "bd7f4a35fbb011abfe282e386080967449f6695486954f2614f4957a12908a4b"
STAGE_STATE_SHA256 = "3ba2068fdeae0e4a508e648381a080d49c35c933c9f37c76f1b1fb8e4ac34b54"
RAW_COUNT = 208
RAW_BYTES = 6_692_740
RAW_DIGEST = "0ce9ac9211c00b403f0ef7235cfde81a1e42751fa230d245cd2dc396fc3e3d33"
BINARY_EXACT_COUNT = 39
ATOL_A = 1e-12
Q0_STEP = 10
N_COILS = 14
OLD_ROUTE = "REDUCED_Q0_TRANSPORT_BRIDGE_Q0_GATE_INTEGRATION_EXECUTION_FAIL_STOP"
PASS_ROUTE = (
    "REDUCED_Q0_TRANSPORT_BRIDGE_Q0_GATE_INTEGRATION_COMPLETE_"
    "R51R2_MODEL_PREFLIGHT_REQUIRED"
)
PRIMARY_NAME = "q0_first_effect_reporting_hotfix_primary.json"
OUTPUT_NAME = "q0_first_effect_reporting_hotfix_independent.json"


def _fail_constant(value: str) -> Any:
    raise ValueError(f"non-finite JSON constant: {value}")


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=_fail_constant)


def _gzip(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(stream, parse_constant=_fail_constant)


def _sha(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            value.update(block)
    return value.hexdigest()


def _canonical_digest(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _inventory(path: Path) -> dict[str, Any]:
    records = []
    combined = hashlib.sha256()
    for item in sorted(path.glob("*.json.gz"), key=lambda candidate: candidate.name):
        record = {"name": item.name, "size": item.stat().st_size, "sha256": _sha(item)}
        combined.update(
            (record["name"] + "\0" + str(record["size"]) + "\0" + record["sha256"] + "\n").encode(
                "utf-8"
            )
        )
        records.append(record)
    return {
        "count": len(records),
        "bytes": sum(record["size"] for record in records),
        "digest": combined.hexdigest(),
        "rows": records,
    }


def _vector(value: Any) -> list[float]:
    if not isinstance(value, list) or len(value) != N_COILS:
        raise ValueError("R8R51R1 independent q0 vector shape changed")
    result = [float(component) for component in value]
    if not all(math.isfinite(component) for component in result):
        raise ValueError("R8R51R1 independent q0 vector is non-finite")
    return result


def _measure_q0_effect(
    trajectory: Sequence[Mapping[str, Any]], trace: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    if len(trajectory) <= 11 or len(trace) <= 10:
        raise ValueError("R8R51R1 independent q0 prefix is incomplete")
    action11 = _vector(trajectory[11].get("action_norm_tsc"))
    action10_trace = _vector(trace[10].get("action_norm_tsc"))
    action10_state = _vector(trajectory[10].get("action_norm_tsc"))
    action9_trace = _vector(trace[9].get("action_norm_tsc"))
    current11 = _vector(trajectory[11].get("currents_a_tsc"))
    current10 = _vector(trajectory[10].get("currents_a_tsc"))
    detail = trace[10].get("r3c3t13s24d1r14r8r51r1_event_detail") or {}
    target = _vector(detail.get("nominal_readback_current_a_tsc"))
    errors = [abs(actual - expected) for actual, expected in zip(current11, target)]
    action_exact = action11 == action10_trace
    previous_exact = action10_state == action9_trace
    binary_exact = current11 == target
    numerical = all(
        math.isclose(actual, expected, rel_tol=0.0, abs_tol=ATOL_A)
        for actual, expected in zip(current11, target)
    )
    return {
        "finite": True,
        "state11_action_equals_trace10_exact": action_exact,
        "state10_action_equals_trace9_exact": previous_exact,
        "state11_current_equals_q0_target_binary_exact": binary_exact,
        "state11_current_equals_q0_target_numerically": numerical,
        "maximum_current_difference_a": max(errors),
        "state11_current_equals_state10_current_exact": current11 == current10,
        "maximum_state11_to_state10_current_difference_a": max(
            abs(current - previous) for current, previous in zip(current11, current10)
        ),
        "q0_action_nonzero": max(abs(value) for value in action10_trace) > 0.0,
        "passed": action_exact and previous_exact and numerical,
    }


def run(config: Path, run_dir: Path) -> dict[str, Any]:
    stage = run_dir.expanduser().resolve() / RUN_NAME
    config = config.expanduser().resolve()
    paths = {
        config: CONFIG_SHA256,
        stage / "stage_manifest.json": STAGE_MANIFEST_SHA256,
        stage / "analysis" / "raw_primary.json": RAW_PRIMARY_SHA256,
        stage / "analysis" / "raw_independent.json": RAW_INDEPENDENT_SHA256,
        stage / "stage_state.json": STAGE_STATE_SHA256,
    }
    if any(not path.is_file() or _sha(path) != expected for path, expected in paths.items()):
        raise ValueError("R8R51R1 independent reporting-hotfix authentication failed")
    output = stage / "analysis" / OUTPUT_NAME
    if output.exists():
        raise ValueError("R8R51R1 independent reporting hotfix already attempted")
    primary_path = stage / "analysis" / PRIMARY_NAME
    if not primary_path.is_file():
        raise ValueError("R8R51R1 primary reporting hotfix is missing")
    primary = _json(primary_path)
    old_primary = _json(stage / "analysis" / "raw_primary.json")
    old_rows = {str(row["experiment_id"]): row for row in old_primary["rows"]}
    inventory = _inventory(stage / "raw")
    if (
        inventory["count"] != RAW_COUNT
        or inventory["bytes"] != RAW_BYTES
        or inventory["digest"] != RAW_DIGEST
        or inventory != old_primary.get("raw_inventory")
        or old_primary.get("route") != OLD_ROUTE
        or int(old_primary.get("q0_first_effect_at_issue_plus_one_count", -1))
        != BINARY_EXACT_COUNT
    ):
        raise ValueError("R8R51R1 independent historical evidence changed")
    rows = []
    for raw_path in sorted((stage / "raw").glob("*.json.gz"), key=lambda item: item.name):
        result = _gzip(raw_path)
        experiment_id = str(result.get("experiment_id") or "")
        old = old_rows.get(experiment_id)
        spec = result.get("spec") or {}
        trajectory = result.get("trajectory") or []
        trace = result.get("controller_trace") or []
        if (
            old is None
            or raw_path.name != experiment_id + ".json.gz"
            or spec.get("experiment_id") != experiment_id
            or result.get("success") is not True
            or len(trajectory) != int(spec.get("horizon_steps", -1)) + 1
            or len(trace) != int(spec.get("horizon_steps", -1))
        ):
            raise ValueError(f"R8R51R1 independent raw identity changed: {raw_path.name}")
        detail = trace[10].get("r3c3t13s24d1r14r8r51r1_event_detail") or {}
        if (
            trace[10].get("r3c3t13s24d1r14r8r51r1_event") != "q0_exact_issue"
            or detail.get("event") != "q0_exact_current_target_issue"
            or detail.get("passed") is not True
            or "q0_zero_target" in (detail.get("criteria") or {})
            or not all(value is True for value in (detail.get("criteria") or {}).values())
        ):
            raise ValueError(f"R8R51R1 independent q0 event changed: {experiment_id}")
        measurement = _measure_q0_effect(trajectory, trace)
        if bool(old.get("q0_first_effect_at_issue_plus_one")) != bool(
            measurement["state11_current_equals_q0_target_binary_exact"]
        ):
            raise ValueError(f"R8R51R1 independent old result mismatch: {experiment_id}")
        rows.append(
            {
                "experiment_id": experiment_id,
                "pair_id": old["pair_id"],
                "history_member": old["history_member"],
                "candidate_index": old["candidate_index"],
                "candidate_id": old["candidate_id"],
                **measurement,
            }
        )
    binary_count = sum(row["state11_current_equals_q0_target_binary_exact"] for row in rows)
    numerical_count = sum(row["state11_current_equals_q0_target_numerically"] for row in rows)
    action_count = sum(row["state11_action_equals_trace10_exact"] for row in rows)
    previous_count = sum(row["state10_action_equals_trace9_exact"] for row in rows)
    unchanged_count = sum(row["state11_current_equals_state10_current_exact"] for row in rows)
    passed_count = sum(row["passed"] for row in rows)
    maximum = max(row["maximum_current_difference_a"] for row in rows)
    row_digest = _canonical_digest(rows)
    comparison = {
        "route": PASS_ROUTE,
        "original_binary_exact_count": binary_count,
        "corrected_numerical_equivalence_count": numerical_count,
        "state11_action_exact_count": action_count,
        "state10_previous_action_exact_count": previous_count,
        "state11_current_unchanged_exact_count": unchanged_count,
        "maximum_current_difference_a": maximum,
        "passed_count": passed_count,
        "bridge_coverage_count": passed_count,
        "raw_inventory": inventory,
        "row_digest": row_digest,
        "response_digest": old_primary["response_digest"],
        "prefix_digest": old_primary["prefix_digest"],
    }
    agreement = all(primary.get(key) == value for key, value in comparison.items())
    passed = bool(
        len(rows) == RAW_COUNT
        and binary_count == BINARY_EXACT_COUNT
        and numerical_count == RAW_COUNT
        and action_count == RAW_COUNT
        and previous_count == RAW_COUNT
        and passed_count == RAW_COUNT
        and maximum <= ATOL_A
        and primary.get("passed") is True
        and agreement
    )
    report = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "q0_first_effect_reporting_hotfix_independent",
        "hotfix_kind": "scalar_binary64_current_reconstruction_reporting_only",
        "original_route": OLD_ROUTE,
        **comparison,
        "current_comparison_rtol": 0.0,
        "current_comparison_atol_a": ATOL_A,
        "primary_sha256": _sha(primary_path),
        "primary_agreement": agreement,
        "raw_unchanged": _inventory(stage / "raw") == inventory,
        "rows": rows,
        "new_raw_count_by_hotfix": 0,
        "plant_step_count_by_hotfix": 0,
        "real_tsc_executed_by_hotfix": False,
        "controller_or_action_semantics_changed": False,
        "all_stage_trajectories_allowed_in_expert_dataset": False,
        "passed": passed,
    }
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    result = run(args.config, args.run_dir)
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "stage",
                    "phase",
                    "route",
                    "original_binary_exact_count",
                    "corrected_numerical_equivalence_count",
                    "maximum_current_difference_a",
                    "passed_count",
                    "primary_agreement",
                    "passed",
                )
            },
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
