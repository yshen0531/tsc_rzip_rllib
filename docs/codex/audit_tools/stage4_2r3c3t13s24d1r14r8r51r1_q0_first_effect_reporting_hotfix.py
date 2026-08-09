#!/usr/bin/env python3
"""Primary/final zero-TSC repair for R8R51R1's q0 current comparison."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


STAGE = "Stage4.2R3c3T13S24D1R14R8R51R1"
RUN_NAME = (
    "stage4_2r3c3t13s24d1r14r8r51r1_"
    "reduced_q0_transport_bridge_q0_gate_integration_sentinel"
)
CONFIG_PATH = (
    "configs/stage4_2r3c3t13s24d1r14r8r51r1_"
    "reduced_q0_transport_bridge_q0_gate_integration_sentinel_370ms.json"
)
PRIMARY_MODULE_PATH = (
    "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r8r51r1_"
    "reduced_q0_transport_bridge_q0_gate_integration_sentinel.py"
)
ORIGINAL_INDEPENDENT_PATH = (
    "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r51r1_"
    "independent_forensics.py"
)
EXPECTED_CONFIG_SHA256 = "a40569191b5d4fc3f8b2663e52f188ed0cf3f211280574d1889750ae6d516c4f"
EXPECTED_PRIMARY_MODULE_SHA256 = "cfb026f5547ea98d3af0edb9b459e50c1b2826f51ab88b048e8f57af3ce2ccb0"
EXPECTED_ORIGINAL_INDEPENDENT_SHA256 = "a60bd077e4c4774e44385a1fcc335d11c8b6c4d50f8f662e5c0465661953b1d2"
EXPECTED_STAGE_MANIFEST_SHA256 = "c58148f603913c70d5e35626f72dc3541892ad4ec2a919db139a45b51feaa076"
EXPECTED_RAW_PRIMARY_SHA256 = "925dbed532e4dcda721592fe409158c7defd89636d94affef9157646df5981a1"
EXPECTED_RAW_INDEPENDENT_SHA256 = "bd7f4a35fbb011abfe282e386080967449f6695486954f2614f4957a12908a4b"
EXPECTED_STAGE_STATE_SHA256 = "3ba2068fdeae0e4a508e648381a080d49c35c933c9f37c76f1b1fb8e4ac34b54"
EXPECTED_PACKAGE_DIGEST = "d1d8aa2acde5b7013b2e87a0cdee1a05bde209e3f6435d2970aba377170b46ae"
EXPECTED_RAW_COUNT = 208
EXPECTED_RAW_BYTES = 6_692_740
EXPECTED_RAW_DIGEST = "0ce9ac9211c00b403f0ef7235cfde81a1e42751fa230d245cd2dc396fc3e3d33"
EXPECTED_BINARY_EXACT_COUNT = 39
CURRENT_ABSOLUTE_TOLERANCE_A = 1e-12
Q0_STEP = 10
N_COILS = 14
OLD_ROUTE = "REDUCED_Q0_TRANSPORT_BRIDGE_Q0_GATE_INTEGRATION_EXECUTION_FAIL_STOP"
PASS_ROUTE = (
    "REDUCED_Q0_TRANSPORT_BRIDGE_Q0_GATE_INTEGRATION_COMPLETE_"
    "R51R2_MODEL_PREFLIGHT_REQUIRED"
)
PRIMARY_NAME = "q0_first_effect_reporting_hotfix_primary.json"
INDEPENDENT_NAME = "q0_first_effect_reporting_hotfix_independent.json"
COMPACT_NAME = "q0_first_effect_reporting_hotfix_compact_audit.json"
FINAL_NAME = "q0_first_effect_reporting_hotfix_final_report.json"

UNCHANGED_ROW_TRUE_FIELDS = (
    "runtime_success",
    "full_horizon",
    "authentic_restart",
    "source_prefix_state_exact",
    "source_prefix_trace_exact",
    "source_trace_difference_wrapper_only",
    "calibration_exact",
    "q0_exact",
    "q0_offline_parity",
    "within_context_q0_prefix_exact",
    "candidate_exact",
    "event_sequence_exact",
    "event_gates_passed",
    "first_effect_at_issue_plus_one",
    "finite_response",
    "return_exact",
    "finite",
)


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


def _strict_constant(value: str) -> Any:
    raise ValueError(f"non-finite JSON constant: {value}")


def _read(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"), parse_constant=_strict_constant
    )


def _read_gzip(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(stream, parse_constant=_strict_constant)


def _write_new(path: Path, value: Any) -> None:
    if path.exists():
        raise ValueError(f"R8R51R1 reporting hotfix output already exists: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    ).hexdigest()


def _inventory(path: Path) -> dict[str, Any]:
    files = sorted(path.glob("*.json.gz"), key=lambda item: item.name)
    digest = hashlib.sha256()
    rows = []
    for item in files:
        size = item.stat().st_size
        sha = _sha(item)
        digest.update(f"{item.name}\0{size}\0{sha}\n".encode("utf-8"))
        rows.append({"name": item.name, "size": size, "sha256": sha})
    return {
        "count": len(rows),
        "bytes": sum(int(row["size"]) for row in rows),
        "digest": digest.hexdigest(),
        "rows": rows,
    }


def _as_vector(value: Any) -> np.ndarray:
    vector = np.asarray(value, dtype=float)
    if vector.shape != (N_COILS,):
        raise ValueError(f"R8R51R1 q0 vector shape changed: {vector.shape}")
    return vector


def _measure_q0_effect(
    trajectory: Sequence[Mapping[str, Any]], trace: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    if len(trajectory) <= Q0_STEP + 1 or len(trace) <= Q0_STEP:
        raise ValueError("R8R51R1 q0 effect prefix is incomplete")
    state10_action = _as_vector(trajectory[Q0_STEP].get("action_norm_tsc"))
    state11_action = _as_vector(trajectory[Q0_STEP + 1].get("action_norm_tsc"))
    trace9_action = _as_vector(trace[Q0_STEP - 1].get("action_norm_tsc"))
    trace10_action = _as_vector(trace[Q0_STEP].get("action_norm_tsc"))
    state10_current = _as_vector(trajectory[Q0_STEP].get("currents_a_tsc"))
    state11_current = _as_vector(trajectory[Q0_STEP + 1].get("currents_a_tsc"))
    detail = trace[Q0_STEP].get(
        "r3c3t13s24d1r14r8r51r1_event_detail"
    ) or {}
    target_current = _as_vector(detail.get("nominal_readback_current_a_tsc"))
    vectors = (
        state10_action,
        state11_action,
        trace9_action,
        trace10_action,
        state10_current,
        state11_current,
        target_current,
    )
    finite = bool(all(np.all(np.isfinite(vector)) for vector in vectors))
    current_error = np.abs(state11_current - target_current)
    action_exact = bool(np.array_equal(state11_action, trace10_action))
    previous_action_exact = bool(np.array_equal(state10_action, trace9_action))
    current_exact = bool(np.array_equal(state11_current, target_current))
    current_equivalent = bool(
        np.allclose(
            state11_current,
            target_current,
            rtol=0.0,
            atol=CURRENT_ABSOLUTE_TOLERANCE_A,
            equal_nan=False,
        )
    )
    return {
        "finite": finite,
        "state11_action_equals_trace10_exact": action_exact,
        "state10_action_equals_trace9_exact": previous_action_exact,
        "state11_current_equals_q0_target_binary_exact": current_exact,
        "state11_current_equals_q0_target_numerically": current_equivalent,
        "maximum_current_difference_a": float(np.max(current_error)),
        "state11_current_equals_state10_current_exact": bool(
            np.array_equal(state11_current, state10_current)
        ),
        "maximum_state11_to_state10_current_difference_a": float(
            np.max(np.abs(state11_current - state10_current))
        ),
        "q0_action_nonzero": bool(np.max(np.abs(trace10_action)) > 0.0),
        "passed": bool(
            finite and action_exact and previous_action_exact and current_equivalent
        ),
    }


def _stage(run_dir: Path) -> Path:
    return run_dir.expanduser().resolve() / RUN_NAME


def _authenticate(config: Path, stage: Path) -> dict[str, Any]:
    project = _root()
    expected_hashes = {
        config.expanduser().resolve(): EXPECTED_CONFIG_SHA256,
        project / PRIMARY_MODULE_PATH: EXPECTED_PRIMARY_MODULE_SHA256,
        project / ORIGINAL_INDEPENDENT_PATH: EXPECTED_ORIGINAL_INDEPENDENT_SHA256,
        stage / "stage_manifest.json": EXPECTED_STAGE_MANIFEST_SHA256,
        stage / "analysis" / "raw_primary.json": EXPECTED_RAW_PRIMARY_SHA256,
        stage / "analysis" / "raw_independent.json": EXPECTED_RAW_INDEPENDENT_SHA256,
        stage / "stage_state.json": EXPECTED_STAGE_STATE_SHA256,
    }
    for path, expected in expected_hashes.items():
        if not path.is_file() or _sha(path) != expected:
            raise ValueError(f"R8R51R1 reporting hotfix source changed: {path}")
    cfg = _read(config.expanduser().resolve())
    manifest = _read(stage / "stage_manifest.json")
    state = _read(stage / "stage_state.json")
    old_primary = _read(stage / "analysis" / "raw_primary.json")
    old_independent = _read(stage / "analysis" / "raw_independent.json")
    if (
        cfg.get("stage") != STAGE
        or manifest.get("stage") != STAGE
        or manifest.get("config_sha256") != EXPECTED_CONFIG_SHA256
        or manifest.get("package_fingerprint", {}).get("digest")
        != EXPECTED_PACKAGE_DIGEST
        or int(manifest.get("spec_count", -1)) != EXPECTED_RAW_COUNT
        or state.get("stage") != STAGE
        or state.get("phase_status") != "real_execution_failed"
        or state.get("finished") is not True
        or state.get("real_tsc_executed") is not True
        or int(state.get("new_raw_count", -1)) != EXPECTED_RAW_COUNT
        or int(state.get("plant_step_count", -1)) != 7488
        or state.get("route") != OLD_ROUTE
        or old_primary.get("route") != OLD_ROUTE
        or old_primary.get("passed") is not False
        or int(old_primary.get("q0_first_effect_at_issue_plus_one_count", -1))
        != EXPECTED_BINARY_EXACT_COUNT
        or int(old_primary.get("passed_count", -1)) != EXPECTED_BINARY_EXACT_COUNT
        or old_independent.get("route") != OLD_ROUTE
        or old_independent.get("passed") is not False
        or old_independent.get("primary_agreement") is not True
        or int(old_independent.get("q0_first_effect_at_issue_plus_one_count", -1))
        != EXPECTED_BINARY_EXACT_COUNT
    ):
        raise ValueError("R8R51R1 reporting hotfix historical precondition changed")
    required_aggregate = (
        "strict_parse_count",
        "runtime_success_count",
        "full_horizon_count",
        "authentic_restart_count",
        "source_prefix_state_exact_count",
        "source_prefix_trace_exact_count",
        "source_trace_difference_wrapper_only_count",
        "causal_forbidden_pass_count",
        "q0_exact_count",
        "q0_offline_parity_count",
        "within_context_q0_prefix_exact_count",
        "candidate_exact_count",
        "candidate_issue_gate_pass_count",
        "first_effect_at_issue_plus_one_count",
        "finite_response_count",
        "stored_center_return_exact_count",
    )
    if any(int(old_primary.get(key, -1)) != EXPECTED_RAW_COUNT for key in required_aggregate):
        raise ValueError("R8R51R1 reporting hotfix found another aggregate failure")
    if (
        int(old_primary.get("runtime_failure_count", -1)) != 0
        or int(old_primary.get("safety_stop_count", -1)) != 0
        or int(old_primary.get("forbidden_trace_count", -1)) != 0
        or len(old_primary.get("rows") or []) != EXPECTED_RAW_COUNT
    ):
        raise ValueError("R8R51R1 reporting hotfix old failure classification changed")
    for row in old_primary["rows"]:
        if (
            not all(row.get(key) is True for key in UNCHANGED_ROW_TRUE_FIELDS)
            or int(row.get("forbidden_trace_count", -1)) != 0
            or str(row.get("execution_failure_class") or "")
            or str(row.get("failure_reason") or "")
            or bool(row.get("passed"))
            != bool(row.get("q0_first_effect_at_issue_plus_one"))
        ):
            raise ValueError("R8R51R1 reporting hotfix found a non-reporting row failure")
    inventory = _inventory(stage / "raw")
    expected_inventory = {
        "count": EXPECTED_RAW_COUNT,
        "bytes": EXPECTED_RAW_BYTES,
        "digest": EXPECTED_RAW_DIGEST,
    }
    if any(inventory[key] != value for key, value in expected_inventory.items()):
        raise ValueError("R8R51R1 reporting hotfix raw inventory changed")
    if inventory != old_primary.get("raw_inventory"):
        raise ValueError("R8R51R1 reporting hotfix raw inventory/report mismatch")
    return {
        "config": cfg,
        "manifest": manifest,
        "state": state,
        "old_primary": old_primary,
        "old_independent": old_independent,
        "raw_inventory": inventory,
    }


def run_primary(config: Path, run_dir: Path) -> dict[str, Any]:
    stage = _stage(run_dir)
    source = _authenticate(config, stage)
    output = stage / "analysis" / PRIMARY_NAME
    if output.exists():
        raise ValueError("R8R51R1 primary reporting hotfix already attempted")
    old_rows = {
        str(row["experiment_id"]): row for row in source["old_primary"]["rows"]
    }
    rows = []
    for raw_path in sorted((stage / "raw").glob("*.json.gz"), key=lambda p: p.name):
        result = _read_gzip(raw_path)
        experiment_id = str(result.get("experiment_id") or "")
        spec = result.get("spec") or {}
        trajectory = result.get("trajectory") or []
        trace = result.get("controller_trace") or []
        old = old_rows.get(experiment_id)
        if (
            old is None
            or raw_path.name != f"{experiment_id}.json.gz"
            or spec.get("experiment_id") != experiment_id
            or result.get("success") is not True
            or len(trajectory) != int(spec.get("horizon_steps", -1)) + 1
            or len(trace) != int(spec.get("horizon_steps", -1))
            or trace[Q0_STEP].get("r3c3t13s24d1r14r8r51r1_event")
            != "q0_exact_issue"
        ):
            raise ValueError(f"R8R51R1 hotfix raw identity changed: {raw_path.name}")
        detail = trace[Q0_STEP].get(
            "r3c3t13s24d1r14r8r51r1_event_detail"
        ) or {}
        if (
            detail.get("event") != "q0_exact_current_target_issue"
            or detail.get("passed") is not True
            or "q0_zero_target" in (detail.get("criteria") or {})
            or not all(value is True for value in (detail.get("criteria") or {}).values())
        ):
            raise ValueError(f"R8R51R1 hotfix q0 event changed: {experiment_id}")
        measurement = _measure_q0_effect(trajectory, trace)
        if bool(old.get("q0_first_effect_at_issue_plus_one")) != bool(
            measurement["state11_current_equals_q0_target_binary_exact"]
        ):
            raise ValueError(f"R8R51R1 hotfix old binary count cannot be reproduced: {experiment_id}")
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
    binary_count = sum(
        bool(row["state11_current_equals_q0_target_binary_exact"]) for row in rows
    )
    numerical_count = sum(
        bool(row["state11_current_equals_q0_target_numerically"]) for row in rows
    )
    action_count = sum(
        bool(row["state11_action_equals_trace10_exact"]) for row in rows
    )
    previous_action_count = sum(
        bool(row["state10_action_equals_trace9_exact"]) for row in rows
    )
    unchanged_current_count = sum(
        bool(row["state11_current_equals_state10_current_exact"]) for row in rows
    )
    passed_count = sum(bool(row["passed"]) for row in rows)
    maximum_difference = max(float(row["maximum_current_difference_a"]) for row in rows)
    after_inventory = _inventory(stage / "raw")
    passed = bool(
        len(rows) == EXPECTED_RAW_COUNT
        and binary_count == EXPECTED_BINARY_EXACT_COUNT
        and numerical_count == EXPECTED_RAW_COUNT
        and action_count == EXPECTED_RAW_COUNT
        and previous_action_count == EXPECTED_RAW_COUNT
        and passed_count == EXPECTED_RAW_COUNT
        and maximum_difference <= CURRENT_ABSOLUTE_TOLERANCE_A
        and after_inventory == source["raw_inventory"]
    )
    report = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "q0_first_effect_reporting_hotfix_primary",
        "hotfix_kind": "binary64_current_reconstruction_reporting_only",
        "original_route": OLD_ROUTE,
        "route": PASS_ROUTE if passed else OLD_ROUTE,
        "current_comparison_rtol": 0.0,
        "current_comparison_atol_a": CURRENT_ABSOLUTE_TOLERANCE_A,
        "original_binary_exact_count": binary_count,
        "corrected_numerical_equivalence_count": numerical_count,
        "state11_action_exact_count": action_count,
        "state10_previous_action_exact_count": previous_action_count,
        "state11_current_unchanged_exact_count": unchanged_current_count,
        "maximum_current_difference_a": maximum_difference,
        "passed_count": passed_count,
        "bridge_coverage_count": passed_count,
        "raw_inventory": after_inventory,
        "raw_unchanged": after_inventory == source["raw_inventory"],
        "original_raw_primary_sha256": EXPECTED_RAW_PRIMARY_SHA256,
        "original_raw_independent_sha256": EXPECTED_RAW_INDEPENDENT_SHA256,
        "original_stage_state_sha256": EXPECTED_STAGE_STATE_SHA256,
        "executed_controller_module_sha256": EXPECTED_PRIMARY_MODULE_SHA256,
        "executed_package_digest": EXPECTED_PACKAGE_DIGEST,
        "response_digest": source["old_primary"]["response_digest"],
        "prefix_digest": source["old_primary"]["prefix_digest"],
        "row_digest": _digest(rows),
        "rows": rows,
        "new_raw_count_by_hotfix": 0,
        "plant_step_count_by_hotfix": 0,
        "real_tsc_executed_by_hotfix": False,
        "controller_or_action_semantics_changed": False,
        "all_stage_trajectories_allowed_in_expert_dataset": False,
        "passed": passed,
    }
    _write_new(output, report)
    return report


def finalize(config: Path, run_dir: Path) -> dict[str, Any]:
    stage = _stage(run_dir)
    source = _authenticate(config, stage)
    analysis = stage / "analysis"
    primary_path = analysis / PRIMARY_NAME
    independent_path = analysis / INDEPENDENT_NAME
    if not primary_path.is_file() or not independent_path.is_file():
        raise ValueError("R8R51R1 reporting hotfix dual audit is incomplete")
    primary = _read(primary_path)
    independent = _read(independent_path)
    agreement_fields = (
        "route",
        "original_binary_exact_count",
        "corrected_numerical_equivalence_count",
        "state11_action_exact_count",
        "state10_previous_action_exact_count",
        "state11_current_unchanged_exact_count",
        "maximum_current_difference_a",
        "passed_count",
        "bridge_coverage_count",
        "raw_inventory",
        "row_digest",
        "response_digest",
        "prefix_digest",
    )
    agreement = bool(
        all(primary.get(key) == independent.get(key) for key in agreement_fields)
        and independent.get("primary_sha256") == _sha(primary_path)
        and independent.get("primary_agreement") is True
    )
    current_inventory = _inventory(stage / "raw")
    passed = bool(
        primary.get("passed") is True
        and independent.get("passed") is True
        and agreement
        and current_inventory == source["raw_inventory"]
    )
    compact = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "q0_first_effect_reporting_hotfix_compact",
        "original_route": OLD_ROUTE,
        "route": PASS_ROUTE if passed else OLD_ROUTE,
        "raw_inventory": current_inventory,
        "current_comparison_rtol": 0.0,
        "current_comparison_atol_a": CURRENT_ABSOLUTE_TOLERANCE_A,
        "original_binary_exact_count": primary.get("original_binary_exact_count"),
        "corrected_numerical_equivalence_count": primary.get(
            "corrected_numerical_equivalence_count"
        ),
        "state11_action_exact_count": primary.get("state11_action_exact_count"),
        "state10_previous_action_exact_count": primary.get(
            "state10_previous_action_exact_count"
        ),
        "state11_current_unchanged_exact_count": primary.get(
            "state11_current_unchanged_exact_count"
        ),
        "maximum_current_difference_a": primary.get("maximum_current_difference_a"),
        "passed_count": primary.get("passed_count"),
        "bridge_coverage_count": primary.get("bridge_coverage_count"),
        "response_digest": primary.get("response_digest"),
        "prefix_digest": primary.get("prefix_digest"),
        "row_digest": primary.get("row_digest"),
        "primary_sha256": _sha(primary_path),
        "independent_sha256": _sha(independent_path),
        "primary_independent_agreement": agreement,
        "raw_unchanged": current_inventory == source["raw_inventory"],
        "new_raw_count_by_hotfix": 0,
        "plant_step_count_by_hotfix": 0,
        "real_tsc_executed_by_hotfix": False,
        "passed": passed,
    }
    compact_path = analysis / COMPACT_NAME
    _write_new(compact_path, compact)
    final = {
        **compact,
        "phase": "q0_first_effect_reporting_hotfix_final",
        "compact_audit_sha256": _sha(compact_path),
        "original_reports_and_state_preserved": True,
        "reporting_hotfix_classification": {
            "runtime_or_environment_error": False,
            "packaging_import_or_deployment_error": False,
            "raw_or_snapshot_corruption": False,
            "summary_or_reporting_error": True,
            "controller_or_action_design_failure": False,
            "real_closed_loop_mpc_executed": False,
            "gate_a_qualified": False,
        },
        "scientific_scope": (
            "finite q0-to-first-transport identification integrity only; "
            "R51R2 zero-new-TSC model preflight is the only authorized successor"
        ),
        "all_stage_trajectories_allowed_in_expert_dataset": False,
    }
    _write_new(analysis / FINAL_NAME, final)
    return final


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--command", choices=("primary", "finalize"), required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    result = (
        run_primary(args.config, args.run_dir)
        if args.command == "primary"
        else finalize(args.config, args.run_dir)
    )
    compact = {
        key: result.get(key)
        for key in (
            "stage",
            "phase",
            "route",
            "original_binary_exact_count",
            "corrected_numerical_equivalence_count",
            "maximum_current_difference_a",
            "passed_count",
            "primary_independent_agreement",
            "passed",
        )
        if key in result
    }
    print(json.dumps(compact, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
