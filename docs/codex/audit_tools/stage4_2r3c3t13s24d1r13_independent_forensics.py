#!/usr/bin/env python3
"""Independent server-side raw audit for Stage4.2R3c3T13S24D1R13."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Mapping, Sequence


STAGE = "Stage4.2R3c3T13S24D1R13"
RUN_NAME = "stage4_2r3c3t13s24d1r13_zero_increment_deconfounding_sentinel"
SOURCE_RUN_NAME = (
    "stage4_2r3c3t13s24d1r11_full_replacement_sequential_transition_identification"
)
CAMPAIGN_IDENTITY = "zero_increment_deconfounding_safety_sentinel_v1"
CONTROLLER_REVISION = "zero_increment_after_calibration_v42r3c3t13s24d1r13_v1"
PREFIX_LAST_STATE = 10
ZERO_START = 10
N_COILS = 14
SOURCE_COUNT = 600
SOURCE_BYTES = 35_511_922
SOURCE_DIGEST = "8812d9fb0a5cb5a8b8309e17985bd85d180a82bbb0f08c02105fb1a749c7c0e7"
NON_SEMANTIC = frozenset({"gotsc_subprocess_s", "step_total_s"})
FORBIDDEN_TRACE_KEYS = (
    "future_measurement_used",
    "hidden_wire_used",
    "source_action_used",
    "source_coil_current_used",
    "source_wire_current_used",
    "current_run_future_used",
    "pair_or_history_label_used",
    "source_result_used",
    "future_probe_schedule_available_to_underlying_controller",
    "r3c3t13s21_partition_label_used",
    "r3c3t13s24_pair_history_partition_label_used",
    "r3c3t13s24_delay_slew_target_id_label_used",
    "r3c3t13s24_source_or_matched_baseline_used",
    "r3c3t13s24_future_measurement_used",
    "r3c3t13s24_future_executed_action_used",
    "r3c3t13s24_hidden_wire_current_used",
    "r3c3t13s24_schedule_available_to_underlying_controller",
    "r3c3t13s24d1r13_future_r17_executed",
)


def _strict_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def _strict_gzip(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(
            stream,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _raw_inventory(directory: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    rows = []
    total = 0
    for path in sorted(directory.glob("*.json.gz")):
        size = path.stat().st_size
        sha = _sha256(path)
        total += size
        digest.update(f"{path.name}\0{size}\0{sha}\n".encode())
        rows.append({"name": path.name, "size": size, "sha256": sha})
    return {"count": len(rows), "bytes": total, "digest": digest.hexdigest(), "rows": rows}


def _semantic(row: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key not in NON_SEMANTIC}


def _trace_projection(source: Mapping[str, Any], current: Mapping[str, Any]) -> bool:
    return all(current.get(key) == value for key, value in source.items())


def _all_finite(values: Any) -> bool:
    if isinstance(values, bool):
        return True
    if isinstance(values, (int, float)):
        return math.isfinite(float(values))
    if isinstance(values, Sequence) and not isinstance(values, (str, bytes)):
        return all(_all_finite(value) for value in values)
    return False


def _nested_true_count(value: Any, names: frozenset[str]) -> int:
    if isinstance(value, Mapping):
        count = 0
        for key, item in value.items():
            if str(key) in names:
                if isinstance(item, Sequence) and not isinstance(item, (str, bytes)):
                    count += sum(bool(flag) for flag in item)
                else:
                    count += int(bool(item))
            count += _nested_true_count(item, names)
        return count
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return sum(_nested_true_count(item, names) for item in value)
    return 0


def _snapshot_inventory(snapshot: Path, expected_digest: str) -> dict[str, Any]:
    manifest_path = snapshot / "restart_snapshot_manifest.json"
    manifest = _strict_json(manifest_path)
    rows = list(manifest.get("files") or [])
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    row_digest = hashlib.sha256(canonical.encode()).hexdigest()
    failures = []
    for row in rows:
        path = snapshot / str(row["name"])
        if (
            not path.is_file()
            or path.stat().st_size != int(row["size_bytes"])
            or _sha256(path) != str(row["sha256"])
        ):
            failures.append(str(row["name"]))
    passed = bool(
        rows
        and not manifest.get("missing_required_files")
        and str(manifest.get("digest")) == expected_digest == row_digest
        and not failures
    )
    return {
        "snapshot_dir": str(snapshot),
        "manifest_sha256": _sha256(manifest_path),
        "file_count": len(rows),
        "total_bytes": sum(int(row["size_bytes"]) for row in rows),
        "failure_files": failures,
        "passed": passed,
    }


def _log_audit(paths: Sequence[Path]) -> list[dict[str, Any]]:
    pattern = re.compile(r"Traceback|ERROR|RayTaskError|Killed")
    rows = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="strict")
        rows.append(
            {
                "path": str(path),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
                "line_count": len(text.splitlines()),
                "error_marker_count": len(pattern.findall(text)),
                "passed": not pattern.search(text),
            }
        )
    return rows


def audit(
    run_dir: Path,
    source_run: Path,
    project: Path,
    logs: Sequence[Path],
) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    source_run = source_run.resolve()
    project = project.resolve()
    stage = run_dir / RUN_NAME
    source_stage = source_run / SOURCE_RUN_NAME
    specs = _strict_json(stage / "specs/sentinel_specs.json")
    state = _strict_json(stage / "stage_state.json")
    manifest = _strict_json(stage / "stage_manifest.json")
    final = _strict_json(stage / "analysis/final_result.json")
    root_final = _strict_json(run_dir / "final_result.json")
    source_inventory = _raw_inventory(source_stage / "raw")
    current_inventory = _raw_inventory(stage / "raw")
    rows = []
    snapshot_cache: dict[str, dict[str, Any]] = {}
    for spec in specs:
        experiment_id = str(spec["experiment_id"])
        current_path = stage / "raw" / f"{experiment_id}.json.gz"
        source_id = str(spec["source_d1r11_experiment_id"])
        source_path = source_stage / "raw" / f"{source_id}.json.gz"
        current = _strict_gzip(current_path)
        source = _strict_gzip(source_path)
        horizon = int(spec["horizon_steps"])
        trajectory = list(current.get("trajectory") or [])
        trace = list(current.get("controller_trace") or [])
        source_trajectory = list(source.get("trajectory") or [])
        source_trace = list(source.get("controller_trace") or [])
        prefix_state = bool(
            len(trajectory) >= PREFIX_LAST_STATE + 1
            and len(source_trajectory) >= PREFIX_LAST_STATE + 1
            and all(
                _semantic(left) == _semantic(right)
                for left, right in zip(
                    trajectory[: PREFIX_LAST_STATE + 1],
                    source_trajectory[: PREFIX_LAST_STATE + 1],
                )
            )
        )
        prefix_trace = bool(
            len(trace) >= ZERO_START
            and len(source_trace) >= ZERO_START
            and all(
                _trace_projection(reference, actual)
                for reference, actual in zip(
                    source_trace[:ZERO_START], trace[:ZERO_START]
                )
            )
        )
        post = trace[ZERO_START:]
        zero_actions = bool(
            len(post) == horizon - ZERO_START
            and all(
                len(row.get("action_norm_tsc") or []) == N_COILS
                and all(float(value) == 0.0 for value in row["action_norm_tsc"])
                for row in post
            )
        )
        currents = [list(map(float, row.get("currents_a_tsc") or [])) for row in trajectory]
        zero_current_delta = bool(
            len(currents) == horizon + 1
            and all(len(row) == N_COILS for row in currents)
            and all(
                currents[index + 1] == currents[index]
                for index in range(ZERO_START, horizon)
            )
        )
        wire = [row.get("wire_currents_a") or [] for row in trajectory]
        finite = bool(
            len(trajectory) == horizon + 1
            and len(trace) == horizon
            and all(
                _all_finite([row.get("R"), row.get("Z"), row.get("Ip")])
                and _all_finite(row.get("currents_a_tsc") or [])
                and bool(row.get("wire_currents_a"))
                and _all_finite(row.get("wire_currents_a") or [])
                and int(row.get("wire_current_count", -1))
                == len(row.get("wire_currents_a") or [])
                for row in trajectory
            )
        )
        payload = _strict_json(stage / "variants" / f"payload_{experiment_id}.json")
        minimum = list(map(float, payload["min_current_tsc"]))
        maximum = list(map(float, payload["max_current_tsc"]))
        utilization = max(
            abs((value - 0.5 * (lo + hi)) / (0.5 * (hi - lo)))
            for row in currents
            for value, lo, hi in zip(row, minimum, maximum)
        )
        calibration_events = [
            row.get("r3c3t13s16_lattice_event")
            for row in trace[:ZERO_START]
            if row.get("r3c3t13s16_lattice_event") != "none"
        ]
        calibration_exact = calibration_events == [
            "calibration_issue",
            "calibration_cancel",
            "calibration_issue",
            "calibration_cancel",
            "calibration_issue",
            "calibration_cancel",
            "calibration_issue",
            "calibration_cancel",
        ]
        forbidden = sum(
            any(bool(row.get(key)) for key in FORBIDDEN_TRACE_KEYS) for row in trace
        )
        solver_errors = sum(not bool(row.get("solver_success")) for row in trace)
        saturation_or_clip = _nested_true_count(
            trace, frozenset({"action_saturated", "current_limit_clipped"})
        )
        summary = current.get("hidden_history_control_summary") or {}
        fresh = bool(
            summary.get("fresh_controller_actor")
            and summary.get("fresh_tsc_process")
            and summary.get("full_tsc_hidden_state_loaded_from_sprsina")
            and not summary.get("future_r17_controller_executed")
        )
        snapshot_key = str(spec["restart_snapshot_dir"])
        if snapshot_key not in snapshot_cache:
            snapshot_cache[snapshot_key] = _snapshot_inventory(
                Path(snapshot_key).resolve(),
                str(spec["restart_snapshot_manifest_digest"]),
            )
        identity = bool(
            current.get("stage") == STAGE
            and current.get("campaign_identity") == CAMPAIGN_IDENTITY
            and current.get("controller_revision") == CONTROLLER_REVISION
            and current.get("experiment_id") == experiment_id
            and current.get("spec") == spec
            and current_path.name == f"{experiment_id}.json.gz"
            and source.get("experiment_id") == source_id
            and source.get("success") is True
            and source.get("completed") is True
            and source.get("spec", {}).get("s24_role") == "baseline"
            and _sha256(source_path) == str(spec["source_d1r11_raw_sha256"])
            and source_path.stat().st_size == int(spec["source_d1r11_raw_size_bytes"])
        )
        passed = bool(
            identity
            and current.get("success") is True
            and current.get("completed") is True
            and prefix_state
            and prefix_trace
            and calibration_exact
            and zero_actions
            and zero_current_delta
            and finite
            and not any(bool(row.get("abnormal")) for row in trajectory)
            and forbidden == 0
            and solver_errors == 0
            and saturation_or_clip == 0
            and fresh
            and utilization <= 0.55 + 1e-12
            and snapshot_cache[snapshot_key]["passed"]
        )
        rows.append(
            {
                "experiment_id": experiment_id,
                "source_experiment_id": source_id,
                "pair_id": spec["pair_id"],
                "history_member": spec["history_member"],
                "horizon": horizon,
                "identity_exact": identity,
                "runtime_success": bool(
                    current.get("success") is True
                    and current.get("completed") is True
                    and not current.get("failure_reason")
                    and not current.get("execution_failure_class")
                ),
                "source_prefix_state_exact": prefix_state,
                "source_prefix_trace_exact": prefix_trace,
                "calibration_exact": calibration_exact,
                "post_prefix_action_count": len(post),
                "post_prefix_actions_exact_zero": zero_actions,
                "post_prefix_current_increments_exact_zero": zero_current_delta,
                "finite_coil_and_wire_records": finite,
                "abnormal_state_count": sum(
                    bool(row.get("abnormal")) for row in trajectory
                ),
                "forbidden_trace_count": forbidden,
                "solver_error_count": solver_errors,
                "saturation_or_clip_count": saturation_or_clip,
                "fresh_controller_and_tsc": fresh,
                "maximum_current_utilization": utilization,
                "raw_sha256": _sha256(current_path),
                "raw_size_bytes": current_path.stat().st_size,
                "passed": passed,
            }
        )
    log_rows = _log_audit(logs)
    package_hashes = {
        name: _sha256(project / name)
        for name in (
            "PACKAGE_MANIFEST.json",
            "SHA256SUMS",
            "configs/stage4_2r3c3t13s24d1r13_zero_increment_deconfounding_sentinel_370ms.json",
            "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r13_zero_increment_deconfounding_sentinel.py",
        )
    }
    formal_count = sum(
        bool(row.get("formal_contract_pass_diagnostic_only"))
        for row in final.get("rows") or []
    )
    passed = bool(
        len(specs) == 8
        and len({row["experiment_id"] for row in specs}) == 8
        and _digest(specs) == str(manifest["spec_digest"])
        and source_inventory["count"] == SOURCE_COUNT
        and source_inventory["bytes"] == SOURCE_BYTES
        and source_inventory["digest"] == SOURCE_DIGEST
        and current_inventory["count"] == 8
        and len(rows) == 8
        and all(row["passed"] for row in rows)
        and sum(row["post_prefix_action_count"] for row in rows) == 208
        and len(snapshot_cache) == 8
        and all(row["passed"] for row in snapshot_cache.values())
        and all(row["passed"] for row in log_rows)
        and final == root_final
        and final.get("passed") is True
        and int(final.get("pass_count", -1)) == 8
        and int(final.get("formal_tracking_pass_count_diagnostic_only", -1))
        == formal_count
        and state.get("phase_status") == "complete"
        and state.get("finished") is True
        and state.get("real_tsc_executed") is True
        and int(state.get("new_raw_count", -1)) == 8
    )
    runtime_error_count = sum(not row["runtime_success"] for row in rows)
    raw_or_snapshot_error_count = (
        sum(not row["identity_exact"] for row in rows)
        + sum(not row["passed"] for row in snapshot_cache.values())
    )
    action_semantics_error_count = sum(
        not row["post_prefix_actions_exact_zero"]
        or not row["post_prefix_current_increments_exact_zero"]
        or row["forbidden_trace_count"] > 0
        for row in rows
    )
    return {
        "schema_version": 1,
        "stage": STAGE,
        "audit_revision": "independent_server_raw_snapshot_audit_v1",
        "passed": passed,
        "run_dir": str(run_dir),
        "source_run": str(source_run),
        "expected_task_count": 8,
        "strict_raw_parse_count": len(rows),
        "raw_pass_count": sum(bool(row["passed"]) for row in rows),
        "source_inventory": source_inventory,
        "current_inventory": current_inventory,
        "snapshot_unique_count": len(snapshot_cache),
        "snapshot_pass_count": sum(bool(row["passed"]) for row in snapshot_cache.values()),
        "source_prefix_state_exact_count": sum(row["source_prefix_state_exact"] for row in rows),
        "source_prefix_trace_exact_count": sum(row["source_prefix_trace_exact"] for row in rows),
        "zero_action_row_count": sum(row["post_prefix_actions_exact_zero"] for row in rows),
        "zero_current_increment_row_count": sum(
            row["post_prefix_current_increments_exact_zero"] for row in rows
        ),
        "post_prefix_action_count": sum(row["post_prefix_action_count"] for row in rows),
        "finite_row_count": sum(row["finite_coil_and_wire_records"] for row in rows),
        "runtime_or_environment_error_count": runtime_error_count,
        "solver_error_count": sum(row["solver_error_count"] for row in rows),
        "saturation_or_clip_count": sum(row["saturation_or_clip_count"] for row in rows),
        "forbidden_trace_count": sum(row["forbidden_trace_count"] for row in rows),
        "maximum_current_utilization": max(row["maximum_current_utilization"] for row in rows),
        "formal_tracking_pass_count_diagnostic_only": formal_count,
        "formal_tracking_total_diagnostic_only": 8,
        "official_result_sha256": _sha256(stage / "analysis/final_result.json"),
        "stage_state_sha256": _sha256(stage / "stage_state.json"),
        "stage_manifest_sha256": _sha256(stage / "stage_manifest.json"),
        "package_hashes": package_hashes,
        "logs": log_rows,
        "snapshots": list(snapshot_cache.values()),
        "rows": rows,
        "classification": {
            "runtime_or_environment_error": runtime_error_count > 0,
            "packaging_import_or_deployment_error": False,
            "raw_or_snapshot_corruption": raw_or_snapshot_error_count > 0,
            "summary_or_reporting_error": False,
            "plant_restart_failure": any(
                not row["source_prefix_state_exact"] for row in rows
            ),
            "action_semantics_failure": action_semantics_error_count > 0,
            "zero_increment_safety_sentinel_pass": passed,
            "real_mpc_or_control_success_established": False,
        },
        "scientific_boundary": {
            "formal_tracking_is_diagnostic_only": True,
            "transition_model_validated": False,
            "mpc_validated": False,
            "long_hold_validated": False,
            "expert_dataset_authorized": False,
            "bc_dagger_or_rl_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--log", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.run_dir, args.source_run, args.project, args.log)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(args.output.resolve()),
        "sha256": _sha256(args.output),
        "passed": result["passed"],
        "raw_pass_count": result["raw_pass_count"],
        "formal_tracking_pass_count_diagnostic_only": result[
            "formal_tracking_pass_count_diagnostic_only"
        ],
    }, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
