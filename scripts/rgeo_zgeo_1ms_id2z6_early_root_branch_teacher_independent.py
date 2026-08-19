#!/usr/bin/env python3
"""Independent full-raw audit for the frozen ID-2Z6 campaign."""

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
from scripts.rgeo_zgeo_1ms_id0_vector_tail_independent import (  # noqa: E402
    ARTIFACTS, _fields, _state,
)
from scripts.rgeo_zgeo_1ms_id2w1_sustained_branch_independent import (  # noqa: E402
    restore_arrival_active_commands,
)
from scripts import rgeo_zgeo_1ms_id2z6_early_root_branch_teacher as primary  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-id2z6-independent-raw-v1"


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


def _expected_streams(stage: dict[str, Any], cfg: Any,
                      targets: dict[str, Any], selected: dict[str, Any],
                      result: dict[str, Any]) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    parent = selected
    rounds = result.get("round_metrics", [])
    for round_index in range(min(3, len(rounds) + 1)):
        streams = (primary.initial_round_streams(stage, cfg, targets, selected)
                   if round_index == 0 else
                   primary.next_round_streams(
                       stage, cfg, targets, parent, round_index))
        values.extend(streams)
        metric = rounds[round_index] if round_index < len(rounds) else None
        arm = metric.get("selected_arm_id") if isinstance(metric, dict) else None
        if arm is None:
            break
        parent = next(row for row in streams if row["arm_id"] == arm)
    if len(rounds) == 3 and all(isinstance(row, dict) and row.get("passed")
                                for row in rounds):
        replay = primary.critical_replay_stream(parent)
        replay["round_index"] = 2
        values.append(replay)
    return values


def _raw_rows(run_dir: Path, cfg: Any, expected: Sequence[dict[str, Any]],
              compact: Sequence[dict[str, Any]],
              failures: list[str]) -> tuple[list[dict[str, Any]], list[str], int]:
    expected_by_id = {row["rollout_id"]: row for row in expected}
    rollout_root = run_dir / "rollouts"
    raw_rows: list[dict[str, Any]] = []
    inventory_lines: list[str] = []
    inventory_bytes = 0
    source_fields = list(_fields(cfg.simulation_root / cfg.start_folder / "inputa"))
    for compact_row in compact:
        rollout_id = str(compact_row["rollout_id"])
        folder = rollout_root / rollout_id
        times = (sorted(int(path.name[:-2]) for path in folder.iterdir()
                        if path.is_dir() and path.name.endswith("ms")
                        and path.name[:-2].isdigit()) if folder.is_dir() else [])
        if compact_row.get("passed") and times != list(range(1100, 1170)):
            failures.append(f"STATE_DIRECTORY_SET:{rollout_id}")
        if times and times != list(range(1100, max(times) + 1)):
            failures.append(f"NONCONTIGUOUS_STATE_DIRECTORY:{rollout_id}")
        if any(time < 1100 or time > 1169 for time in times):
            failures.append(f"FORBIDDEN_STATE_DIRECTORY:{rollout_id}")
        states: list[dict[str, Any]] = []
        issued_fields: list[list[str]] = []
        for index, time_ms in enumerate(times):
            state_folder = folder / f"{time_ms}ms"
            try:
                state = _state(state_folder, cfg)
            except Exception as exc:
                failures.append(
                    f"RAW_STATE:{rollout_id}:{time_ms}:{type(exc).__name__}:{exc}")
                continue
            states.append(state)
            if index < len(compact_row.get("states", [])):
                saved = compact_row["states"][index]
                for key, tolerance in (("r_geo_m", 1e-12), ("z_geo_m", 1e-12),
                                       ("r_mid_m", 1e-12), ("ip_a", 1e-9)):
                    if abs(float(state[key]) - float(saved[key])) > tolerance:
                        failures.append(f"STATE_VALUE:{rollout_id}:{time_ms}:{key}")
                if (len(state["actual_current_decimal_a_tsc"]) != 14
                        or state["actual_current_decimal_a_tsc"]
                        != saved.get("actual_current_decimal_a_tsc")):
                    failures.append(f"COIL_VALUE:{rollout_id}:{time_ms}")
                if (len(state["wire_current_a"]) != 48
                        or len(saved.get("wire_current_a", [])) != 48
                        or any(abs(float(a) - float(b)) > 1e-9
                               for a, b in zip(state["wire_current_a"],
                                               saved["wire_current_a"]))):
                    failures.append(f"WIRE_VALUE:{rollout_id}:{time_ms}")
            for name in ARTIFACTS:
                artifact = state_folder / name
                if not artifact.is_file():
                    failures.append(f"MISSING_ARTIFACT:{rollout_id}:{time_ms}:{name}")
                    continue
                size = artifact.stat().st_size
                inventory_bytes += size
                inventory_lines.append(
                    f"{artifact.relative_to(run_dir).as_posix()}\t{size}\t{sha256(artifact)}")
        frozen = expected_by_id.get(rollout_id, {})
        for issue, action in enumerate(compact_row.get("actions", [])):
            if issue >= len(times):
                failures.append(f"ACTION_WITHOUT_PREISSUE_STATE:{rollout_id}:{issue}")
                continue
            fields = list(_fields(folder / f"{1100 + issue}ms" / "inputa"))
            issued_fields.append(fields)
            if fields != action.get("expected_card15_fields"):
                failures.append(f"ISSUED_CARD15:{rollout_id}:{issue}")
            if (issue >= len(frozen.get("actions", []))
                    or fields != frozen["actions"][issue]["expected_card15_fields"]):
                failures.append(f"FROZEN_ACTION:{rollout_id}:{issue}")
        try:
            restore_arrival_active_commands(states, issued_fields)
            if states:
                states[0]["active_command_card15_fields"] = source_fields
        except Exception as exc:
            failures.append(
                f"ACTIVE_COMMAND_RECONSTRUCTION:{rollout_id}:{type(exc).__name__}:{exc}")
        raw_rows.append({
            **{key: value for key, value in compact_row.items()
               if key not in ("states", "actions")},
            "states": states,
            "actions": compact_row.get("actions", []),
        })
    return raw_rows, inventory_lines, inventory_bytes


def audit(stage_path: Path, run_dir: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    stage_path, run_dir = inside(stage_path, "config"), inside(run_dir, "run")
    result_path = run_dir / "result.json"
    result = load_json(result_path) if result_path.is_file() else {}
    try:
        stage, cfg, targets, compact_reference, selected = primary.load(stage_path)
        expected = _expected_streams(stage, cfg, targets, selected, result)
    except Exception as exc:
        failures.append(f"STAGE_LOAD:{type(exc).__name__}:{exc}")
        stage, cfg, compact_reference, selected, expected = (
            load_json(stage_path), None, {}, {}, [])
    order = {row["rollout_id"]: index for index, row in enumerate(expected)}
    excluded = {"result.json", "offline_preflight.json", "independent_raw_audit.json"}
    compact_paths = sorted(path for path in run_dir.glob("*.json")
                           if path.name not in excluded)
    compact = [load_json(path) for path in compact_paths]
    compact.sort(key=lambda row: order.get(row.get("rollout_id"), 999))
    expected_ids = [row["rollout_id"] for row in expected]
    if [row.get("rollout_id") for row in compact] != expected_ids[:len(compact)]:
        failures.append("COMPACT_ORDER_OR_IDENTITY")
    for row in compact:
        if (row.get("schema_version") != primary.SCHEMA
                or row.get("source_revision") != source_revision):
            failures.append(f"COMPACT_IDENTITY:{row.get('rollout_id')}")
    rollout_root = run_dir / "rollouts"
    actual_ids = (sorted(path.name for path in rollout_root.iterdir() if path.is_dir())
                  if rollout_root.is_dir() else [])
    if actual_ids != sorted(row.get("rollout_id") for row in compact):
        failures.append("ROLLOUT_DIRECTORY_SET")
    raw_rows: list[dict[str, Any]] = []
    inventory_lines: list[str] = []
    inventory_bytes = 0
    if cfg is not None:
        raw_rows, inventory_lines, inventory_bytes = _raw_rows(
            run_dir, cfg, expected, compact, failures)
    inventory_sha = hashlib.sha256(
        "".join(f"{line}\n" for line in sorted(inventory_lines)).encode()).hexdigest()
    if inventory_sha != result.get("required_artifact_inventory_sha256"):
        failures.append("INVENTORY_SHA256")
    if (len(inventory_lines) != result.get("required_artifact_files")
            or inventory_bytes != result.get("required_artifact_bytes")):
        failures.append("INVENTORY_COUNT_OR_BYTES")

    by_round = {index: [row for row in raw_rows
                        if row.get("round_index") == index
                        and row.get("rollout_id") != "critical_replay"]
                for index in range(3)}
    prefixes: list[dict[str, Any]] = []
    round_values: list[dict[str, Any] | None] = []
    parent_row = compact_reference
    selected_row: dict[str, Any] | None = None
    for round_index in range(3):
        rows = by_round[round_index]
        if len(rows) != 5:
            break
        decision = int(stage["rounds"][round_index]["decision_state_index"])
        prefixes.extend(primary.prefix_check(
            row, parent_row, decision + 1, decision,
            stage["semantic_artifacts"]) for row in rows)
        value = primary.round_metrics(rows, stage, round_index, cfg)
        round_values.append(value)
        if not value.get("passed"):
            break
        selected_row = next(row for row in rows
                            if row.get("arm_id") == value["selected_arm_id"])
        parent_row = selected_row
    replay_row = next((row for row in raw_rows
                       if row.get("rollout_id") == "critical_replay"), None)
    if replay_row is not None:
        prefixes.append(primary.prefix_check(
            replay_row, selected_row or {}, 70, 69,
            stage["semantic_artifacts"]))
    execution = bool(raw_rows and all(
        row.get("passed") or primary.safe_stop(row, stage) for row in raw_rows))
    prefixes_ok = bool(prefixes and all(row.get("passed") for row in prefixes))
    expected_files = 5 * sum(len(row.get("states", [])) for row in raw_rows)
    raw_ok = bool(execution and len(inventory_lines) == expected_files
                  and not any(value.startswith("MISSING_ARTIFACT")
                              for value in failures))
    scientific = primary.final_metrics(
        round_values, raw_rows, stage, selected_row, replay_row)
    route = primary.route_for(
        stage, execution, raw_ok, prefixes_ok, round_values, scientific)
    for key, recomputed in (("prefix_checks", prefixes),
                            ("round_metrics", round_values),
                            ("scientific_metrics", scientific)):
        if result.get(key) != recomputed:
            failures.append(f"RECOMPUTE:{key}")
    if result.get("selected_three_macro_sequence") != scientific.get(
            "selected_three_macro_sequence"):
        failures.append("RECOMPUTE:SELECTED_SEQUENCE")
    if (result.get("route") != route
            or result.get("passed") != (route == stage["routes"]["pass"])):
        failures.append("PRIMARY_ROUTE_OR_VERDICT")
    counters = {
        "rollouts_completed": len(compact),
        "complete_rollouts": sum(bool(row.get("passed")) for row in compact),
        "guarded_safe_stops": sum(primary.safe_stop(row, stage) for row in compact),
        "reset_calls": sum(int(row.get("reset_calls", 0)) for row in compact),
        "advance_attempts": sum(int(row.get("advance_attempts", 0)) for row in compact),
        "plant_advance_gotsc_calls": sum(
            int(row.get("plant_advance_gotsc_calls", 0)) for row in compact),
        "verified_plant_advances": sum(
            int(row.get("verified_plant_advances", 0)) for row in compact),
    }
    for key, value in counters.items():
        if result.get(key) != value:
            failures.append(f"COUNTER:{key}")
    if (result.get("source_revision") != source_revision
            or result.get("stage_config_sha256") != primary.CONFIG_SHA256):
        failures.append("RESULT_IDENTITY")
    if (result.get("models_fit_or_updated") != 0
            or result.get("calibration_or_holdout_records_read") != 0
            or result.get("id2z5_records_read_for_fit") != 0):
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
        "recomputed_prefix_checks": prefixes,
        "recomputed_round_metrics": round_values,
        "recomputed_scientific_metrics": scientific,
        "recomputed_selected_three_macro_sequence": scientific.get(
            "selected_three_macro_sequence"),
        "finite_teacher_pass": bool(
            not failures and route == stage["routes"]["pass"]),
        "models_fit_or_updated": 0,
        "calibration_or_holdout_records_read": 0,
        "claim_boundary": (
            "Independent full-raw finite ID2Z6 branch-teacher audit; not "
            "hold, recovery, controller, waypoint or reachability qualification."),
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
