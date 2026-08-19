#!/usr/bin/env python3
"""Reporting-only ID2Z6 hotfix and in-place continuation.

The original ID2Z6 process completed all five round-0 trajectories, then
raised while adding a descriptive margin whose inherited configuration key
had been renamed.  This driver authenticates those immutable compact/raw
records, recomputes the unchanged frozen selection, and continues at round 1
without repeating a plant advance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_id2z6_early_root_branch_teacher as primary  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2z6_early_root_branch_teacher_independent as independent  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-id2z6r1-reporting-resume-v1"
PREFLIGHT_SCHEMA = "rgeo-zgeo-1ms-id2z6r1-resume-preflight-v1"


def _inside(path: Path, label: str) -> Path:
    value = path.resolve()
    try:
        value.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(f"{label} leaves repository") from exc
    return value


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"object required: {path}")
    return value


def _revision(value: str, label: str) -> str:
    if len(value) != 40 or any(ch not in "0123456789abcdef" for ch in value):
        raise ValueError(f"{label} must be a full lowercase git revision")
    return value


def _metadata_sha(value: dict[str, Any]) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def resume_preflight(stage_path: Path, run_dir: Path,
                     experiment_source_revision: str,
                     hotfix_source_revision: str) -> tuple[dict[str, Any], dict[str, Any]]:
    failures: list[str] = []
    stage_path = _inside(stage_path, "stage config")
    run_dir = _inside(run_dir, "run directory")
    experiment_source_revision = _revision(
        experiment_source_revision, "experiment source revision")
    hotfix_source_revision = _revision(
        hotfix_source_revision, "hotfix source revision")
    if experiment_source_revision == hotfix_source_revision:
        failures.append("HOTFIX_REVISION_NOT_DISTINCT")
    if not run_dir.is_dir():
        failures.append("RUN_DIRECTORY_MISSING")
    if (run_dir / "result.json").exists():
        failures.append("PRIMARY_RESULT_ALREADY_EXISTS")
    if (run_dir / "independent_raw_audit.json").exists():
        failures.append("INDEPENDENT_RESULT_ALREADY_EXISTS")
    if (run_dir / "metadata" / "id2z6r1_resume_preflight.json").exists():
        failures.append("RESUME_IDENTITY_ALREADY_CONSUMED")

    try:
        stage, cfg, targets, compact_reference, selected = primary.load(stage_path)
        streams = primary.initial_round_streams(
            stage, cfg, targets, selected)
        checks = [primary.validate_stream(stream, stage, cfg, targets)
                  for stream in streams]
        if not all(value["passed"] for value in checks):
            failures.append("ROUND0_STREAM_RECONSTRUCTION")
    except Exception as exc:
        failures.append(f"STAGE_LOAD:{type(exc).__name__}:{exc}")
        stage, cfg, targets, compact_reference, selected, streams, checks = (
            {}, None, {}, {}, {}, [], [])

    offline_path = run_dir / "offline_preflight.json"
    if offline_path.is_file():
        offline = _load_json(offline_path)
        if (not offline.get("passed")
                or offline.get("source_revision") != experiment_source_revision
                or offline.get("stage_config_sha256") != primary.CONFIG_SHA256
                or offline.get("plant_advance_gotsc_calls") != 0):
            failures.append("ORIGINAL_OFFLINE_PREFLIGHT")
    else:
        offline = {}
        failures.append("ORIGINAL_OFFLINE_PREFLIGHT_MISSING")

    expected_ids = [stream["rollout_id"] for stream in streams]
    excluded = {"offline_preflight.json", "result.json",
                "independent_raw_audit.json"}
    compact_paths = sorted(
        path for path in run_dir.glob("*.json") if path.name not in excluded)
    by_id: dict[str, dict[str, Any]] = {}
    for path in compact_paths:
        row = _load_json(path)
        by_id[str(row.get("rollout_id"))] = row
    if sorted(by_id) != sorted(expected_ids):
        failures.append("ROUND0_COMPACT_SET")
    compact = [by_id[row_id] for row_id in expected_ids if row_id in by_id]
    for row, stream in zip(compact, streams):
        if (row.get("schema_version") != primary.SCHEMA
                or row.get("source_revision") != experiment_source_revision
                or row.get("round_index") != 0
                or row.get("arm_id") != stream["arm_id"]
                or row.get("tokens") != stream["tokens"]
                or not row.get("passed")
                or len(row.get("states", [])) != 70
                or len(row.get("actions", [])) != 69):
            failures.append(f"ROUND0_COMPACT_IDENTITY:{stream['rollout_id']}")
        if ([value.get("expected_card15_fields")
             for value in row.get("actions", [])]
                != [value.get("expected_card15_fields")
                    for value in stream.get("actions", [])]):
            failures.append(f"ROUND0_FROZEN_ACTION:{stream['rollout_id']}")

    actual_dirs = (sorted(path.name for path in (run_dir / "rollouts").iterdir()
                          if path.is_dir())
                   if (run_dir / "rollouts").is_dir() else [])
    if actual_dirs != sorted(expected_ids):
        failures.append("ROUND0_RAW_DIRECTORY_SET")

    raw_failures: list[str] = []
    raw_rows: list[dict[str, Any]] = []
    inventory_lines: list[str] = []
    inventory_bytes = 0
    if cfg is not None and len(compact) == 5:
        raw_rows, inventory_lines, inventory_bytes = independent._raw_rows(
            run_dir, cfg, streams, compact, raw_failures)
        failures.extend(raw_failures)
    if len(raw_rows) != 5 or sum(len(row.get("states", [])) for row in raw_rows) != 350:
        failures.append("ROUND0_RAW_STATE_COUNT")
    if len(inventory_lines) != 1750:
        failures.append("ROUND0_RAW_ARTIFACT_COUNT")

    prefix_values: list[dict[str, Any]] = []
    if compact_reference and len(compact) == 5:
        # The live compact record is captured before the runner rewrites that
        # state's inputa with the outgoing issue.  The independent raw pass
        # above authenticates the rewritten inputa as the issued action; the
        # causal preissue-prefix comparison must therefore use the preserved
        # compact state, exactly as the original primary did online.
        prefix_values = [primary.prefix_check(
            row, compact_reference, 50, 49, stage["semantic_artifacts"])
            for row in compact]
        if not all(value.get("passed") for value in prefix_values):
            failures.append("ROUND0_PREFIX")

    round_value: dict[str, Any] = {}
    if cfg is not None and len(raw_rows) == 5:
        round_value = primary.round_metrics(raw_rows, stage, 0, cfg)
        if not round_value.get("passed"):
            failures.append("ROUND0_NO_ELIGIBLE_ARM")

    free_bytes = shutil.disk_usage(run_dir).free if run_dir.exists() else 0
    storage = stage.get("storage_gate", {})
    storage_passed = bool(
        free_bytes >= int(storage.get("minimum_free_bytes_before_run", 0))
        and free_bytes - int(storage.get("maximum_estimated_raw_bytes", 0))
        >= int(storage.get("minimum_free_bytes_after_estimate", 0)))
    if not storage_passed:
        failures.append("RESUME_STORAGE")

    failures = list(dict.fromkeys(failures))
    preflight = {
        "schema_version": PREFLIGHT_SCHEMA,
        "experiment_source_revision": experiment_source_revision,
        "hotfix_source_revision": hotfix_source_revision,
        "stage_config_sha256": primary.CONFIG_SHA256,
        "passed": not failures,
        "failures": failures,
        "original_round0_rollouts_authenticated": len(raw_rows),
        "original_round0_states_authenticated": sum(
            len(row.get("states", [])) for row in raw_rows),
        "original_round0_artifacts_authenticated": len(inventory_lines),
        "original_round0_artifact_bytes": inventory_bytes,
        "original_round0_prefix_checks": prefix_values,
        "recomputed_round0_metrics": round_value,
        "recomputed_round0_selected_arm_id": round_value.get("selected_arm_id"),
        "free_bytes_before_resume": free_bytes,
        "storage_passed": storage_passed,
        "reset_calls": 0,
        "advance_attempts": 0,
        "plant_advance_gotsc_calls": 0,
        "models_fit_or_updated": 0,
        "claim_boundary": (
            "Authentication and deterministic resumption of five immutable "
            "ID2Z6 round-0 trajectories after a post-trajectory descriptive-"
            "reporting exception; no controller, action, gate or task change."),
    }
    context = {
        "stage": stage,
        "cfg": cfg,
        "targets": targets,
        "compact_reference": compact_reference,
        "selected": selected,
        "streams": streams,
        "compact": compact,
        "raw_rows": raw_rows,
        "prefix_values": prefix_values,
        "round_value": round_value,
    }
    return preflight, context


def _finalize(stage: dict[str, Any], rows: list[dict[str, Any]],
              round_values: list[dict[str, Any] | None],
              prefix_values: list[dict[str, Any]], execution: bool,
              selected_row: dict[str, Any] | None,
              replay_row: dict[str, Any] | None,
              run_dir: Path, experiment_source_revision: str,
              hotfix_source_revision: str, preflight: dict[str, Any]) -> dict[str, Any]:
    counters = {
        "reset_calls": sum(int(row.get("reset_calls", 0)) for row in rows),
        "advance_attempts": sum(int(row.get("advance_attempts", 0)) for row in rows),
        "plant_advance_gotsc_calls": sum(
            int(row.get("plant_advance_gotsc_calls", 0)) for row in rows),
        "verified_plant_advances": sum(
            int(row.get("verified_plant_advances", 0)) for row in rows),
    }
    if (len(rows) > int(stage["maximum_rollouts"])
            or counters["reset_calls"] > int(stage["maximum_reset_calls"])
            or counters["advance_attempts"] > int(stage["maximum_advance_attempts"])
            or counters["plant_advance_gotsc_calls"] > int(stage["maximum_gotsc_calls"])
            or counters["verified_plant_advances"]
            > int(stage["maximum_verified_plant_advances"])):
        execution = False
    prefixes_ok = bool(prefix_values and all(
        value.get("passed") for value in prefix_values))
    inventory = primary.z5.z3.z1.y1r1.y1.x1.raw_inventory(run_dir, rows, stage)
    expected_files = 5 * sum(len(row.get("states", [])) for row in rows)
    raw_ok = bool(execution and not inventory["missing_required_artifacts"]
                  and inventory["required_artifact_files"] == expected_files)
    scientific = primary.final_metrics(
        round_values, rows, stage, selected_row, replay_row)
    route = primary.route_for(
        stage, execution, raw_ok, prefixes_ok, round_values, scientific)
    passed = route == stage["routes"]["pass"]
    result = {
        "schema_version": primary.SCHEMA,
        "source_revision": experiment_source_revision,
        "resume_hotfix_source_revision": hotfix_source_revision,
        "resume_preflight_sha256": _metadata_sha(preflight),
        "stage_config_sha256": primary.CONFIG_SHA256,
        "passed": passed,
        "route": route,
        "storage_gate": {
            "passed": preflight["storage_passed"],
            "free_bytes_before_resume": preflight["free_bytes_before_resume"],
            "resume_reuses_five_complete_round0_rollouts": True,
        },
        "execution_integrity_passed": execution,
        "raw_integrity_passed": raw_ok,
        "prefix_checks": prefix_values,
        "round_metrics": round_values,
        "scientific_metrics": scientific,
        "selected_three_macro_sequence": scientific[
            "selected_three_macro_sequence"],
        "rollouts_completed": len(rows),
        "complete_rollouts": sum(bool(row.get("passed")) for row in rows),
        "guarded_safe_stops": sum(primary.safe_stop(row, stage) for row in rows),
        **counters,
        **inventory,
        "original_round0_rollouts_reused_without_rerun": 5,
        "models_fit_or_updated": 0,
        "calibration_or_holdout_records_read": 0,
        "id2z5_records_read_for_fit": 0,
        "compact_data_role": stage["data_use"],
        "claim_boundary": (
            "Finite source-local early-root branch-teacher and prospective "
            "complete-window development evidence after an authenticated "
            "reporting-only resume; not hold, recovery, controller, waypoint, "
            "crossing or reachability qualification."),
    }
    primary.z5.z3.z1.y1r1.y1.x1.write_new(run_dir / "result.json", result)
    return result


def resume(stage_path: Path, run_dir: Path,
           experiment_source_revision: str,
           hotfix_source_revision: str) -> dict[str, Any]:
    run_dir = _inside(run_dir, "run directory")
    preflight, context = resume_preflight(
        stage_path, run_dir, experiment_source_revision, hotfix_source_revision)
    if not preflight["passed"]:
        return preflight
    metadata = run_dir / "metadata"
    metadata.mkdir(exist_ok=False)
    primary.z5.z3.z1.y1r1.y1.x1.write_new(
        metadata / "id2z6r1_resume_preflight.json", preflight)

    stage, cfg, targets = (
        context["stage"], context["cfg"], context["targets"])
    # The loaded W2 runner retains its historical default run root.  Resume
    # evidence must remain inside the already frozen ID2Z6 output tree.
    cfg.run_root = run_dir / "rollouts"
    rows = list(context["compact"])
    prefix_values = list(context["prefix_values"])
    round_values: list[dict[str, Any] | None] = [context["round_value"]]
    selected_arm = str(context["round_value"]["selected_arm_id"])
    selected_constructed = next(
        stream for stream in context["streams"] if stream["arm_id"] == selected_arm)
    selected_row = next(
        row for row in rows if row["arm_id"] == selected_arm)
    reference_row = selected_row
    execution = True

    for round_index in (1, 2):
        streams = primary.next_round_streams(
            stage, cfg, targets, selected_constructed, round_index)
        checks = [primary.validate_stream(stream, stage, cfg, targets)
                  for stream in streams]
        if not all(value["passed"] for value in checks):
            execution = False
            break
        decision = int(stage["rounds"][round_index]["decision_state_index"])
        reference = primary._reference(reference_row, decision + 1)
        round_rows: list[dict[str, Any]] = []
        for stream in streams:
            row = primary.execute_row(
                cfg, stage, stream, reference,
                experiment_source_revision, run_dir)
            rows.append(row)
            round_rows.append(row)
            prefix_values.append(primary.prefix_check(
                row, reference_row, decision + 1, decision,
                stage["semantic_artifacts"]))
            if not row.get("passed") and not primary.safe_stop(row, stage):
                execution = False
                break
        if not execution:
            break
        value = primary.round_metrics(round_rows, stage, round_index, cfg)
        round_values.append(value)
        if not value["passed"]:
            break
        selected_arm = str(value["selected_arm_id"])
        selected_constructed = next(
            stream for stream in streams if stream["arm_id"] == selected_arm)
        selected_row = next(
            row for row in round_rows if row["arm_id"] == selected_arm)
        reference_row = selected_row

    replay_row: dict[str, Any] | None = None
    if len(round_values) == 3 and all(
            value and value.get("passed") for value in round_values):
        replay_stream = primary.critical_replay_stream(selected_constructed)
        replay_stream["round_index"] = 2
        replay_reference = primary._reference(selected_row or {}, 70)
        replay_row = primary.execute_row(
            cfg, stage, replay_stream, replay_reference,
            experiment_source_revision, run_dir)
        rows.append(replay_row)
        prefix_values.append(primary.prefix_check(
            replay_row, selected_row or {}, 70, 69,
            stage["semantic_artifacts"]))
        if not replay_row.get("passed") and not primary.safe_stop(
                replay_row, stage):
            execution = False

    return _finalize(
        stage, rows, round_values, prefix_values, execution,
        selected_row, replay_row, run_dir, experiment_source_revision,
        hotfix_source_revision, preflight)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-config", type=Path, default=primary.CONFIG)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--experiment-source-revision", required=True)
    parser.add_argument("--hotfix-source-revision", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args(argv)
    if args.preflight_only:
        result, _ = resume_preflight(
            args.stage_config, args.run_dir,
            args.experiment_source_revision, args.hotfix_source_revision)
    else:
        result = resume(
            args.stage_config, args.run_dir,
            args.experiment_source_revision, args.hotfix_source_revision)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result.get("passed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
