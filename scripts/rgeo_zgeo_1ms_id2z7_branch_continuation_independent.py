#!/usr/bin/env python3
"""Independent full-raw audit for the frozen ID-2Z7 continuation."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_id0_vector_tail import sha256, write_new  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2z6_early_root_branch_teacher_independent as z6i  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2z7_branch_continuation as primary  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-id2z7-independent-raw-v1"


def inside(path: Path, label: str) -> Path:
    value = path.resolve()
    try:
        value.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(f"{label} leaves repository") from exc
    return value


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("object required")
    return value


def expected_fresh_streams(
        z6_stage: dict[str, Any], cfg: Any, targets: dict[str, Any],
        parent: dict[str, Any], result: dict[str, Any]) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    selected = parent
    rounds = result.get("fresh_round_metrics", [])
    for round_index in primary.FRESH_ROUNDS:
        streams = primary.fresh_round_streams(
            z6_stage, cfg, targets, selected, round_index)
        values.extend(streams)
        metric_index = round_index - 1
        metric = rounds[metric_index] if metric_index < len(rounds) else None
        arm = metric.get("selected_arm_id") if isinstance(metric, dict) else None
        if arm is None:
            break
        selected = next(row for row in streams if row["arm_id"] == arm)
    if len(rounds) == 2 and all(
            isinstance(row, dict) and row.get("passed") for row in rounds):
        replay = primary.z6.critical_replay_stream(selected)
        replay["round_index"] = 2
        values.append(replay)
    return values


def _compact_rows(run_dir: Path, expected: Sequence[dict[str, Any]],
                  failures: list[str]) -> list[dict[str, Any]]:
    excluded = {
        "result.json", "offline_preflight.json", "independent_raw_audit.json"}
    paths = sorted(path for path in run_dir.glob("*.json")
                   if path.name not in excluded)
    rows = [load_json(path) for path in paths]
    order = {row["rollout_id"]: index for index, row in enumerate(expected)}
    rows.sort(key=lambda row: order.get(str(row.get("rollout_id")), 999))
    expected_ids = [row["rollout_id"] for row in expected]
    ids = [row.get("rollout_id") for row in rows]
    if ids != expected_ids[:len(ids)] or len(set(ids)) != len(ids):
        failures.append("COMPACT_ORDER_OR_IDENTITY")
    return rows


def audit(stage_path: Path, run_dir: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    stage_path = inside(stage_path, "config")
    run_dir = inside(run_dir, "run")
    result_path = run_dir / "result.json"
    result = load_json(result_path) if result_path.is_file() else {}
    try:
        (stage, z6_stage, cfg, targets, _, external_rows,
         parent_constructed, parent_compact, z6_result) = primary.load(stage_path)
        expected = expected_fresh_streams(
            z6_stage, cfg, targets, parent_constructed, result)
    except Exception as exc:
        failures.append(f"STAGE_LOAD:{type(exc).__name__}:{exc}")
        stage = load_json(stage_path)
        z6_stage, cfg, targets, external_rows = {}, None, {}, []
        parent_constructed, parent_compact, z6_result, expected = {}, {}, {}, []

    compact = _compact_rows(run_dir, expected, failures)
    for row in compact:
        if (row.get("schema_version") != primary.SCHEMA
                or row.get("source_revision") != source_revision):
            failures.append(f"COMPACT_IDENTITY:{row.get('rollout_id')}")
    rollout_root = run_dir / "rollouts"
    actual_ids = (sorted(path.name for path in rollout_root.iterdir()
                         if path.is_dir()) if rollout_root.is_dir() else [])
    if actual_ids != sorted(str(row.get("rollout_id")) for row in compact):
        failures.append("ROLLOUT_DIRECTORY_SET")

    raw_rows: list[dict[str, Any]] = []
    inventory_lines: list[str] = []
    inventory_bytes = 0
    if cfg is not None:
        raw_rows, inventory_lines, inventory_bytes = z6i._raw_rows(
            run_dir, cfg, expected, compact, failures)
    inventory_sha = hashlib.sha256(
        "".join(f"{line}\n" for line in sorted(inventory_lines)).encode()
    ).hexdigest()
    if inventory_sha != result.get("required_artifact_inventory_sha256"):
        failures.append("INVENTORY_SHA256")
    if (len(inventory_lines) != result.get("required_artifact_files")
            or inventory_bytes != result.get("required_artifact_bytes")):
        failures.append("INVENTORY_COUNT_OR_BYTES")

    compact_by_id = {str(row.get("rollout_id")): row for row in compact}
    raw_by_round = {
        index: [row for row in raw_rows
                if int(row.get("round_index", -1)) == index
                and row.get("rollout_id") != "critical_replay"]
        for index in primary.FRESH_ROUNDS}
    prefix_values: list[dict[str, Any]] = []
    fresh_round_values: list[dict[str, Any]] = []
    parent_prefix = parent_compact
    selected_constructed = parent_constructed
    selected_row: dict[str, Any] | None = None
    for round_index in primary.FRESH_ROUNDS:
        rows = raw_by_round[round_index]
        decision = int(z6_stage.get("rounds", [{}, {}, {}])[round_index].get(
            "decision_state_index", 0)) if z6_stage else 0
        for row in rows:
            prefix_values.append(primary.z6.prefix_check(
                compact_by_id.get(str(row.get("rollout_id")), {}),
                parent_prefix, decision + 1, decision,
                stage.get("semantic_artifacts", [])))
        if len(rows) != 5:
            break
        value = primary.z6.round_metrics(rows, z6_stage, round_index, cfg)
        fresh_round_values.append(value)
        if not value.get("passed"):
            break
        streams = primary.fresh_round_streams(
            z6_stage, cfg, targets, selected_constructed, round_index)
        selected_arm = str(value["selected_arm_id"])
        selected_constructed = next(
            row for row in streams if row["arm_id"] == selected_arm)
        selected_row = next(
            row for row in rows if row.get("arm_id") == selected_arm)
        parent_prefix = compact_by_id.get(
            str(selected_row.get("rollout_id")), {})

    replay_row = next((row for row in raw_rows
                       if row.get("rollout_id") == "critical_replay"), None)
    if replay_row is not None:
        prefix_values.append(primary.z6.prefix_check(
            compact_by_id.get(str(replay_row.get("rollout_id")), {}),
            parent_prefix, 70, 69, stage.get("semantic_artifacts", [])))

    execution = bool(raw_rows and all(
        row.get("passed") or primary.z6.safe_stop(row, z6_stage)
        for row in raw_rows))
    prefixes_ok = bool(prefix_values and all(
        row.get("passed") for row in prefix_values))
    expected_files = 5 * sum(len(row.get("states", [])) for row in raw_rows)
    raw_ok = bool(execution and len(inventory_lines) == expected_files
                  and not any(value.startswith("MISSING_ARTIFACT")
                              for value in failures))
    external_round = z6_result.get("round_metrics", [{}])[0]
    scientific = primary._combined_final_metrics(
        external_round, fresh_round_values, external_rows, raw_rows,
        z6_stage, selected_row, replay_row)
    route = primary.route_for(
        stage, execution, raw_ok, prefixes_ok, fresh_round_values, scientific)

    for key, recomputed in (
            ("fresh_prefix_checks", prefix_values),
            ("fresh_round_metrics", fresh_round_values),
            ("scientific_metrics", scientific)):
        if key in result and result.get(key) != recomputed:
            failures.append(f"RECOMPUTE:{key}")
    if ("selected_three_macro_sequence" in result
            and result.get("selected_three_macro_sequence")
            != scientific.get("selected_three_macro_sequence")):
        failures.append("RECOMPUTE:SELECTED_SEQUENCE")
    if (result.get("route") != route
            or result.get("passed") != (route == stage["routes"]["pass"])):
        failures.append("PRIMARY_ROUTE_OR_VERDICT")

    counters = {
        "fresh_rollouts_completed": len(compact),
        "fresh_complete_rollouts": sum(bool(row.get("passed")) for row in compact),
        "fresh_guarded_safe_stops": sum(
            primary.z6.safe_stop(row, z6_stage) for row in compact),
        "reset_calls": sum(int(row.get("reset_calls", 0)) for row in compact),
        "advance_attempts": sum(
            int(row.get("advance_attempts", 0)) for row in compact),
        "plant_advance_gotsc_calls": sum(
            int(row.get("plant_advance_gotsc_calls", 0)) for row in compact),
        "verified_plant_advances": sum(
            int(row.get("verified_plant_advances", 0)) for row in compact),
    }
    for key, value in counters.items():
        if result.get(key) != value:
            failures.append(f"COUNTER:{key}")
    required_root = (run_dir / "rollouts").resolve()
    isolation = result.get("run_root_isolation", {})
    if (isolation.get("required_run_root") != str(required_root)
            or isolation.get("configured_run_root") != str(required_root)
            or isolation.get("passed") is not True):
        failures.append("RUN_ROOT_ISOLATION")
    if (result.get("source_revision") != source_revision
            or result.get("stage_config_sha256") != primary.CONFIG_SHA256):
        failures.append("RESULT_IDENTITY")
    if (result.get("models_fit_or_updated") != 0
            or result.get("calibration_or_holdout_records_read") != 0
            or result.get("interrupted_id2z6_round1_records_read_for_fit_or_selection") != 0):
        failures.append("FORBIDDEN_DATA_OR_MODEL_USE")

    failures = list(dict.fromkeys(failures))
    return {
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "stage_config_sha256": primary.CONFIG_SHA256,
        "audit_passed": not failures,
        "failures": failures,
        "primary_sha256": sha256(result_path) if result_path.is_file() else None,
        "primary_route": result.get("route"),
        "primary_scientific_passed": result.get("passed"),
        "recomputed_route": route,
        "recomputed_counters": counters,
        "raw_rollouts": len(raw_rows),
        "raw_states": sum(len(row.get("states", [])) for row in raw_rows),
        "recomputed_inventory_files": len(inventory_lines),
        "recomputed_inventory_bytes": inventory_bytes,
        "recomputed_inventory_sha256": inventory_sha,
        "recomputed_prefix_checks": prefix_values,
        "recomputed_fresh_round_metrics": fresh_round_values,
        "recomputed_scientific_metrics": scientific,
        "recomputed_selected_three_macro_sequence": scientific.get(
            "selected_three_macro_sequence"),
        "finite_teacher_pass": bool(
            not failures and route == stage["routes"]["pass"]),
        "models_fit_or_updated": 0,
        "calibration_or_holdout_records_read": 0,
        "claim_boundary": (
            "Independent full-raw finite ID2Z7 continuation audit; not hold, "
            "recovery, controller, waypoint or reachability qualification."),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-config", type=Path, default=primary.CONFIG)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = audit(args.stage_config, args.run_dir, args.source_revision)
    output = args.output or args.run_dir / "independent_raw_audit.json"
    write_new(inside(output, "output"), result)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
