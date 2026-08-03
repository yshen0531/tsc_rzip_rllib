#!/usr/bin/env python3
"""Reporting-only physical-state prefix correction for completed D1R6 raw.

The original D1R6 audits compared complete state-record dictionaries and thus
treated per-call wall-clock diagnostics as plant state.  This script binds to
the exact completed execution and independently proves that the only D1R4 to
D1R6 prefix differences are those runtime diagnostics.  It never changes raw,
the experiment route, controller semantics, or formal-gate interpretation.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r6_recursive_split_return_safety_sentinel as stage,
)


EXPECTED_RUN_NAME = (
    "stage4_2r3c3t13s24d1r6_recursive_split_return_safety_sentinel_"
    "20260803_195509_4177aa2_v1"
)
EXPECTED_ROUTE = "CAUSAL_RECURSIVE_SPLIT_RETURN_SENTINEL_FAIL_REDESIGN_REQUIRED"
EXPECTED_RAW_COUNT = 9
EXPECTED_RAW_BYTES = 422_133
EXPECTED_RAW_DIGEST = (
    "351f7484bd3ec2f68f76cc2f17ea6bc93a6227e2078b8be2f0cdf9e84055fd89"
)
EXPECTED_SPEC_DIGEST = (
    "f3ca434af404bb20c85e7ff2fb6da40bc13c1d873ae9c74396ab8680533b889b"
)
EXPECTED_PACKAGE_MANIFEST_SHA256 = (
    "014068b0dd2c046c5985ca11c1e5a5464092c016f0b1f7f92cedc6fc0773d6b1"
)
EXPECTED_SHA256SUMS_SHA256 = (
    "dad07a6a8fd1116bb4156326d8312c925f70cfe744f3bb3c3b79f24b7c8d30dc"
)
EXPECTED_CONFIG_SHA256 = (
    "0ead2d73de119b7c7cef4d16ffb18d0a0ebcc934aa76a6129ad48418f5cacbe4"
)
EXPECTED_IMPLEMENTATION_SHA256 = (
    "74ef096e5a7af92ab9ece03e9ec94a687b0a1a921003ceae35f45db9226827d4"
)
EXPECTED_COMPLETE_LOG_SHA256 = (
    "14da67f6caac172ad67095fcce0843d6eb595671bd8c9ee935701acdc10b5a65"
)
EXPECTED_ARTIFACT_HASHES = {
    "stage_state.json": "792be3672bdd679a271d079f682040cf6b57f38c48b9b246a0f6c6c331eda170",
    "stage_manifest.json": "de0baf9fbe2c8923b5f3c863a9273667fb6fa9c652512388fee813ebfb452ecb",
    "final_result.json": "2236231582b31957d0920c7047b0245f7de3f27cf47dce3a46951c2531d4dec4",
    "analysis/internal_execution_audit.json": (
        "3264a6ea446d7e51a7dcfcff18ef66b7f098c815f3ece156d069549b1530656a"
    ),
    "analysis/server_internal_raw_recomputation.json": (
        "0eace69afddfb35a45f5095bd358c1bfc678560bb406c27b1a836a0437454227"
    ),
    "analysis/independent_server_forensics.json": (
        "e54bfe8369ed35865771a918a8d25dd6ff1ad84d2e73175c0ba67694e4149698"
    ),
    "source_reference/snapshot_audit.json": (
        "b3298d45d36c166ba68baa9f0aaca3bdc81e5fedb46f9b845ea69647e8a38854"
    ),
    "source_reference/source_authentication.json": (
        "85c4d93593477e5b055f998cb0191727a5e44d193cf440beb93f1f3ce6351992"
    ),
}
RUNTIME_DIAGNOSTIC_KEYS = frozenset({"gotsc_subprocess_s", "step_total_s"})


def _read(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
    )


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def _inventory(raw_dir: Path) -> dict[str, Any]:
    rows = []
    digest = hashlib.sha256()
    for path in sorted(raw_dir.glob("*.json.gz")):
        sha = _sha(path)
        size = path.stat().st_size
        digest.update(f"{path.name}\0{size}\0{sha}\n".encode())
        rows.append({"path": path.name, "bytes": size, "sha256": sha})
    return {
        "count": len(rows),
        "total_bytes": sum(int(row["bytes"]) for row in rows),
        "digest": digest.hexdigest(),
        "files": rows,
    }


def _state_projection(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(value)
        for key, value in row.items()
        if key not in RUNTIME_DIAGNOSTIC_KEYS
    }


def _state_difference_keys(
    current: Mapping[str, Any], source: Mapping[str, Any]
) -> set[str]:
    return {
        key
        for key in set(current) | set(source)
        if current.get(key) != source.get(key)
    }


def _current_trace_projection(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(value)
        for key, value in row.items()
        if not key.startswith("r3c3t13s24d1r6_")
    }


def _source_trace_projection(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(value)
        for key, value in row.items()
        if not key.startswith("r3c3t13s24d1r4_")
    }


def run(
    run_dir: Path,
    source_d1r4_run: Path,
    complete_log: Path,
    output: Path,
) -> dict[str, Any]:
    project = stage._project_root()
    run_dir = run_dir.expanduser().resolve()
    source_d1r4_run = source_d1r4_run.expanduser().resolve()
    complete_log = complete_log.expanduser().resolve()
    output = output.expanduser().resolve()
    if run_dir.name != EXPECTED_RUN_NAME:
        raise ValueError("D1R6 reporting hotfix run identity changed")
    stage_dir = run_dir / stage.RUN_NAME
    if output.exists():
        raise ValueError("D1R6 reporting hotfix output must be new")
    package_hashes = {
        "package_manifest_sha256": _sha(project / "PACKAGE_MANIFEST.json"),
        "sha256sums_sha256": _sha(project / "SHA256SUMS"),
        "config_sha256": _sha(
            project
            / "configs/"
            "stage4_2r3c3t13s24d1r6_recursive_split_return_safety_sentinel_350ms.json"
        ),
        "implementation_sha256": _sha(
            project
            / "tsc_rzip_rllib/diagnostics/"
            "stage4_2r3c3t13s24d1r6_recursive_split_return_safety_sentinel.py"
        ),
    }
    expected_package = {
        "package_manifest_sha256": EXPECTED_PACKAGE_MANIFEST_SHA256,
        "sha256sums_sha256": EXPECTED_SHA256SUMS_SHA256,
        "config_sha256": EXPECTED_CONFIG_SHA256,
        "implementation_sha256": EXPECTED_IMPLEMENTATION_SHA256,
    }
    if package_hashes != expected_package:
        raise ValueError("D1R6 reporting hotfix execution package changed")
    if _sha(complete_log) != EXPECTED_COMPLETE_LOG_SHA256:
        raise ValueError("D1R6 reporting hotfix complete log changed")
    actual_artifacts = {
        relative: _sha(stage_dir / relative)
        for relative in EXPECTED_ARTIFACT_HASHES
    }
    if actual_artifacts != EXPECTED_ARTIFACT_HASHES:
        raise ValueError("D1R6 reporting hotfix artifact boundary changed")
    independent = _read(stage_dir / "analysis/independent_server_forensics.json")
    state = _read(stage_dir / "stage_state.json")
    manifest = _read(stage_dir / "stage_manifest.json")
    final = _read(stage_dir / "final_result.json")
    specs = _read(stage_dir / "specs/sentinel_specs.json")
    inventory = _inventory(stage_dir / "raw")
    if not (
        inventory["count"] == EXPECTED_RAW_COUNT
        and inventory["total_bytes"] == EXPECTED_RAW_BYTES
        and inventory["digest"] == EXPECTED_RAW_DIGEST
        and len(specs) == EXPECTED_RAW_COUNT
        and _digest(specs) == EXPECTED_SPEC_DIGEST
        and independent.get("forensic_recomputation_passed")
        and independent.get("raw_inventory") == inventory
        and independent.get("source_prefix_action_exact_count") == 9
        and independent.get("source_prefix_trace_exact_count") == 9
        and independent.get("source_prefix_state_exact_count") == 0
        and independent.get("first_d1r5_continuation_exact_count") == 9
        and independent.get("structured_deadline_safe_stop_count") == 9
        and independent.get("failure_action_not_applied_count") == 9
        and independent.get("runtime_or_raw_failure_count") == 0
        and independent.get("route") == EXPECTED_ROUTE
        and state.get("verdict", {}).get("route") == EXPECTED_ROUTE
        and manifest.get("route") == EXPECTED_ROUTE
        and final.get("route") == EXPECTED_ROUTE
    ):
        raise ValueError("D1R6 reporting hotfix source conclusion changed")
    source_raw = source_d1r4_run / stage.d1r4.RUN_NAME / "raw"
    rows = []
    for spec in specs:
        experiment_id = str(spec["experiment_id"])
        source_id = str(spec["d1r6_source_d1r4_experiment_id"])
        current = stage._read_raw(stage_dir / "raw" / f"{experiment_id}.json.gz")
        source = stage._read_raw(source_raw / f"{source_id}.json.gz")
        trajectory = list(current.get("trajectory") or [])
        source_trajectory = list(source.get("trajectory") or [])
        trace = list(current.get("controller_trace") or [])
        source_trace = list(source.get("controller_trace") or [])
        difference_counts = {key: 0 for key in sorted(RUNTIME_DIAGNOSTIC_KEYS)}
        unexpected_difference_keys: set[str] = set()
        runtime_values_finite_positive = True
        for current_state, source_state in zip(
            trajectory[:20], source_trajectory[:20]
        ):
            difference = _state_difference_keys(current_state, source_state)
            unexpected_difference_keys.update(difference - RUNTIME_DIAGNOSTIC_KEYS)
            for key in RUNTIME_DIAGNOSTIC_KEYS:
                if key in difference:
                    difference_counts[key] += 1
                    runtime_values_finite_positive = bool(
                        runtime_values_finite_positive
                        and math.isfinite(float(current_state[key]))
                        and math.isfinite(float(source_state[key]))
                        and float(current_state[key]) > 0.0
                        and float(source_state[key]) > 0.0
                    )
        physical_state_exact = bool(
            len(trajectory) >= 20
            and len(source_trajectory) == 20
            and all(
                _state_projection(current_state) == _state_projection(source_state)
                for current_state, source_state in zip(
                    trajectory[:20], source_trajectory
                )
            )
        )
        action_exact = bool(
            len(trace) >= 19
            and len(source_trace) == 19
            and all(
                current_row["action_norm_tsc"] == source_row["action_norm_tsc"]
                for current_row, source_row in zip(trace[:19], source_trace)
            )
        )
        trace_exact = bool(
            len(trace) >= 18
            and len(source_trace) == 19
            and all(
                _current_trace_projection(current_row)
                == _source_trace_projection(source_row)
                for current_row, source_row in zip(trace[:18], source_trace[:18])
            )
        )
        runtime_only = bool(
            not unexpected_difference_keys
            and difference_counts == {"gotsc_subprocess_s": 19, "step_total_s": 19}
            and runtime_values_finite_positive
        )
        passed = bool(physical_state_exact and action_exact and trace_exact and runtime_only)
        rows.append(
            {
                "experiment_id": experiment_id,
                "source_experiment_id": source_id,
                "pair_id": spec["pair_id"],
                "history_member": spec["history_member"],
                "sequence_index": int(spec["s24_sequence_index"]),
                "trajectory_count": len(trajectory),
                "source_trajectory_count": len(source_trajectory),
                "physical_state_prefix_through_state19_exact": physical_state_exact,
                "source_action_prefix_through_step18_exact": action_exact,
                "source_trace_prefix_through_step17_exact": trace_exact,
                "runtime_diagnostic_difference_counts": difference_counts,
                "unexpected_difference_keys": sorted(unexpected_difference_keys),
                "runtime_diagnostic_values_finite_positive": (
                    runtime_values_finite_positive
                ),
                "runtime_metadata_only_difference": runtime_only,
                "passed": passed,
            }
        )
    passed = bool(len(rows) == 9 and all(bool(row["passed"]) for row in rows))
    result = {
        "schema_version": 1,
        "stage": stage.STAGE,
        "classification": (
            "semantics_preserving_reporting_hotfix_physical_state_prefix"
        ),
        "execution_package_hashes": package_hashes,
        "complete_log_path": str(complete_log),
        "complete_log_sha256": EXPECTED_COMPLETE_LOG_SHA256,
        "source_independent_forensics_sha256": EXPECTED_ARTIFACT_HASHES[
            "analysis/independent_server_forensics.json"
        ],
        "raw_inventory": inventory,
        "raw_inventory_exact": True,
        "spec_digest": _digest(specs),
        "physical_source_prefix_state_exact_count": sum(
            bool(row["physical_state_prefix_through_state19_exact"]) for row in rows
        ),
        "runtime_metadata_only_difference_count": sum(
            bool(row["runtime_metadata_only_difference"]) for row in rows
        ),
        "gotsc_subprocess_difference_count": sum(
            int(row["runtime_diagnostic_difference_counts"]["gotsc_subprocess_s"])
            for row in rows
        ),
        "step_total_difference_count": sum(
            int(row["runtime_diagnostic_difference_counts"]["step_total_s"])
            for row in rows
        ),
        "unexpected_physical_state_difference_count": sum(
            len(row["unexpected_difference_keys"]) for row in rows
        ),
        "source_action_prefix_exact_count": sum(
            bool(row["source_action_prefix_through_step18_exact"]) for row in rows
        ),
        "source_trace_prefix_exact_count": sum(
            bool(row["source_trace_prefix_through_step17_exact"]) for row in rows
        ),
        "original_source_prefix_state_exact_count": 0,
        "reporting_bug_confirmed": passed,
        "controller_or_experiment_semantics_changed": False,
        "raw_changed": False,
        "experiment_route_changed": False,
        "formal_tracking_evaluable_count": 0,
        "formal_tracking_failure_count": 0,
        "formal_tracking_not_run_count": 9,
        "runtime_or_raw_failure_count": 0,
        "structured_deadline_safe_stop_count": 9,
        "failure_action_not_applied_count": 9,
        "route": EXPECTED_ROUTE,
        "full_replacement_campaign_design_authorized": False,
        "mpc_or_learning_authorized": False,
        "forensic_recomputation_passed": passed,
        "rows": rows,
    }
    _write(output, result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-d1r4-run", type=Path, required=True)
    parser.add_argument("--complete-log", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    result = run(
        args.run_dir, args.source_d1r4_run, args.complete_log, args.output
    )
    print(
        json.dumps(
            {key: value for key, value in result.items() if key != "rows"},
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
