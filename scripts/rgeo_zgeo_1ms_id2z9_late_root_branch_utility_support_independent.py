#!/usr/bin/env python3
"""Independent raw reparse for frozen ID-2Z9."""

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

from scripts.rgeo_zgeo_1ms_id0_vector_tail import write_new  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2z6_early_root_branch_teacher_independent as z6i  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2z9_late_root_branch_utility_support as primary  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-id2z9-independent-raw-v1"


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


def expected_streams(stage: dict[str, Any], runtime: dict[str, Any], cfg: Any,
                     targets: dict[str, Any], parent: dict[str, Any],
                     result: dict[str, Any]) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    selected = parent
    metrics = result.get("fresh_round_metrics", [])
    for round_index in primary.FRESH_ROUNDS:
        streams = primary.build_round_streams(
            stage, runtime, cfg, targets, selected, round_index)
        values.extend(streams)
        metric = metrics[round_index] if round_index < len(metrics) else None
        arm = metric.get("selected_arm_id") if isinstance(metric, dict) else None
        if arm is None:
            break
        selected = next(row for row in streams if row["arm_id"] == arm)
    if len(metrics) == 2 and all(isinstance(row, dict) and row.get("passed")
                                 for row in metrics):
        replay = primary.z6.critical_replay_stream(selected)
        replay["round_index"] = 1
        values.append(replay)
    return values


def compact_rows(run_dir: Path, expected: Sequence[dict[str, Any]],
                 failures: list[str]) -> list[dict[str, Any]]:
    excluded = {"result.json", "offline_preflight.json", "independent_raw_audit.json"}
    paths = sorted(path for path in run_dir.glob("*.json") if path.name not in excluded)
    rows = [load_json(path) for path in paths]
    order = {row["rollout_id"]: index for index, row in enumerate(expected)}
    rows.sort(key=lambda row: order.get(str(row.get("rollout_id")), 999))
    ids = [row.get("rollout_id") for row in rows]
    expected_ids = [row["rollout_id"] for row in expected]
    if ids != expected_ids[:len(ids)] or len(set(ids)) != len(ids):
        failures.append("COMPACT_ORDER_OR_IDENTITY")
    return rows


def expected_state_times(frozen: dict[str, Any]) -> list[int]:
    return list(range(1100, 1101 + len(frozen.get("actions", []))))


def _raw_rows(run_dir: Path, cfg: Any,
              expected: Sequence[dict[str, Any]],
              compact: Sequence[dict[str, Any]],
              failures: list[str]) -> tuple[list[dict[str, Any]], list[str], int]:
    """Reparse ID2Z9's 77-issue rollouts without ID2Z6's 69-step ceiling."""
    expected_by_id = {row["rollout_id"]: row for row in expected}
    rollout_root = run_dir / "rollouts"
    raw_rows: list[dict[str, Any]] = []
    inventory_lines: list[str] = []
    inventory_bytes = 0
    source_fields = list(z6i._fields(cfg.simulation_root / cfg.start_folder / "inputa"))
    for compact_row in compact:
        rollout_id = str(compact_row["rollout_id"])
        frozen = expected_by_id.get(rollout_id, {})
        folder = rollout_root / rollout_id
        times = (sorted(int(path.name[:-2]) for path in folder.iterdir()
                        if path.is_dir() and path.name.endswith("ms")
                        and path.name[:-2].isdigit()) if folder.is_dir() else [])
        expected_times = expected_state_times(frozen)
        if compact_row.get("passed") and times != expected_times:
            failures.append(f"STATE_DIRECTORY_SET:{rollout_id}")
        if times and times != list(range(1100, max(times) + 1)):
            failures.append(f"NONCONTIGUOUS_STATE_DIRECTORY:{rollout_id}")
        maximum_time = 1100 + len(frozen.get("actions", []))
        if any(time < 1100 or time > maximum_time for time in times):
            failures.append(f"FORBIDDEN_STATE_DIRECTORY:{rollout_id}")
        states: list[dict[str, Any]] = []
        issued_fields: list[list[str]] = []
        for index, time_ms in enumerate(times):
            state_folder = folder / f"{time_ms}ms"
            try:
                state = z6i._state(state_folder, cfg)
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
            for name in z6i.ARTIFACTS:
                artifact = state_folder / name
                if not artifact.is_file():
                    failures.append(f"MISSING_ARTIFACT:{rollout_id}:{time_ms}:{name}")
                    continue
                size = artifact.stat().st_size
                inventory_bytes += size
                inventory_lines.append(
                    f"{artifact.relative_to(run_dir).as_posix()}\t{size}\t{z6i.sha256(artifact)}")
        for issue, action in enumerate(compact_row.get("actions", [])):
            if issue >= len(times):
                failures.append(f"ACTION_WITHOUT_PREISSUE_STATE:{rollout_id}:{issue}")
                continue
            fields = list(z6i._fields(folder / f"{1100 + issue}ms" / "inputa"))
            issued_fields.append(fields)
            if fields != action.get("expected_card15_fields"):
                failures.append(f"ISSUED_CARD15:{rollout_id}:{issue}")
            if (issue >= len(frozen.get("actions", []))
                    or fields != frozen["actions"][issue]["expected_card15_fields"]):
                failures.append(f"FROZEN_ACTION:{rollout_id}:{issue}")
        try:
            z6i.restore_arrival_active_commands(states, issued_fields)
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
    stage_path = inside(stage_path, "config")
    run_dir = inside(run_dir, "run")
    result = load_json(run_dir / "result.json")
    try:
        stage, runtime, cfg, targets, parent, parent_compact = primary.load(stage_path)
        expected = expected_streams(stage, runtime, cfg, targets, parent, result)
    except Exception as exc:
        failures.append(f"STAGE_LOAD:{type(exc).__name__}:{exc}")
        stage, runtime, cfg, targets, parent, parent_compact, expected = (
            load_json(stage_path), {}, None, {}, {}, {}, [])
    compact = compact_rows(run_dir, expected, failures)
    for row in compact:
        if (row.get("schema_version") != primary.z7.SCHEMA
                or row.get("source_revision") != source_revision):
            failures.append(f"COMPACT_IDENTITY:{row.get('rollout_id')}")
    rollout_root = run_dir / "rollouts"
    actual_ids = (sorted(path.name for path in rollout_root.iterdir() if path.is_dir())
                  if rollout_root.is_dir() else [])
    if actual_ids != sorted(str(row.get("rollout_id")) for row in compact):
        failures.append("ROLLOUT_DIRECTORY_SET")
    raw_rows: list[dict[str, Any]] = []
    inventory_lines: list[str] = []
    inventory_bytes = 0
    if cfg is not None:
        raw_rows, inventory_lines, inventory_bytes = _raw_rows(
            run_dir, cfg, expected, compact, failures)
    digest = hashlib.sha256(
        "".join(f"{line}\n" for line in sorted(inventory_lines)).encode()).hexdigest()
    if digest != result.get("required_artifact_inventory_sha256"):
        failures.append("INVENTORY_SHA256")
    if (len(inventory_lines) != result.get("required_artifact_files")
            or inventory_bytes != result.get("required_artifact_bytes")):
        failures.append("INVENTORY_COUNT_OR_BYTES")
    compact_by_id = {str(row.get("rollout_id")): row for row in compact}
    raw_by_round = {index: [row for row in raw_rows
                            if int(row.get("round_index", -1)) == index
                            and row.get("rollout_id") != "critical_replay"]
                    for index in primary.FRESH_ROUNDS}
    prefix_values: list[dict[str, Any]] = []
    round_values: list[dict[str, Any]] = []
    selected_constructed = parent
    parent_prefix = parent_compact
    selected_row = None
    for round_index in primary.FRESH_ROUNDS:
        rows = raw_by_round[round_index]
        decision = stage["fresh_rounds"][round_index]["decision_state_index"]
        for row in rows:
            prefix_values.append(primary.z6.prefix_check(
                compact_by_id.get(str(row.get("rollout_id")), {}), parent_prefix,
                decision + 1, decision, stage["semantic_artifacts"]))
        if len(rows) != 5:
            break
        value = primary.z6.round_metrics(rows, runtime, round_index, cfg)
        round_values.append(value)
        if not value.get("passed"):
            break
        streams = primary.build_round_streams(
            stage, runtime, cfg, targets, selected_constructed, round_index)
        selected_arm = value["selected_arm_id"]
        selected_constructed = next(row for row in streams if row["arm_id"] == selected_arm)
        selected_row = next(row for row in rows if row.get("arm_id") == selected_arm)
        parent_prefix = compact_by_id.get(str(selected_row.get("rollout_id")), {})
    replay_row = next((row for row in raw_rows
                       if row.get("rollout_id") == "critical_replay"), None)
    if replay_row is not None:
        prefix_values.append(primary.z6.prefix_check(
            compact_by_id.get("critical_replay", {}), parent_prefix, 78, 77,
            stage["semantic_artifacts"]))
    execution = bool(raw_rows and all(
        row.get("passed") or primary.z6.safe_stop(row, runtime) for row in raw_rows))
    prefixes_ok = bool(prefix_values and all(row.get("passed") for row in prefix_values))
    expected_files = 5 * sum(len(row.get("states", [])) for row in raw_rows)
    raw_ok = bool(execution and len(inventory_lines) == expected_files
                  and not any(value.startswith("MISSING_ARTIFACT") for value in failures))
    scientific = primary.final_metrics(
        round_values, raw_rows, stage, selected_row, replay_row)
    route = primary.route_for(
        stage, execution, raw_ok, prefixes_ok, round_values, scientific)
    for key, recomputed in (("fresh_prefix_checks", prefix_values),
                            ("fresh_round_metrics", round_values),
                            ("scientific_metrics", scientific)):
        if result.get(key) != recomputed:
            failures.append(f"RECOMPUTE:{key}")
    if (result.get("route") != route
            or result.get("passed") != (route == stage["routes"]["pass"])):
        failures.append("PRIMARY_ROUTE_OR_VERDICT")
    counters = {
        "fresh_rollouts_completed": len(compact),
        "fresh_complete_rollouts": sum(bool(row.get("passed")) for row in compact),
        "fresh_guarded_safe_stops": sum(primary.z6.safe_stop(row, runtime)
                                          for row in compact),
        "reset_calls": sum(int(row.get("reset_calls", 0)) for row in compact),
        "advance_attempts": sum(int(row.get("advance_attempts", 0)) for row in compact),
        "plant_advance_gotsc_calls": sum(int(row.get("plant_advance_gotsc_calls", 0))
                                          for row in compact),
        "verified_plant_advances": sum(int(row.get("verified_plant_advances", 0))
                                        for row in compact),
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
    failures = list(dict.fromkeys(failures))
    return {"schema_version": SCHEMA, "source_revision": source_revision,
            "stage_config_sha256": primary.CONFIG_SHA256,
            "audit_passed": not failures, "failures": failures,
            "primary_passed": result.get("passed"), "primary_route": result.get("route"),
            "recomputed_route": route,
            "required_artifact_files": len(inventory_lines),
            "required_artifact_bytes": inventory_bytes,
            "required_artifact_inventory_sha256": digest,
            "raw_states_reparsed": sum(len(row.get("states", [])) for row in raw_rows),
            "raw_rollouts_reparsed": len(raw_rows), **counters,
            "new_tsc_or_plant_advances": 0,
            "claim_boundary": "Independent raw reparse and frozen metric recomputation; not controller qualification."}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-config", type=Path, default=primary.CONFIG)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    value = audit(args.stage_config, args.run_dir, args.source_revision)
    output = args.output or args.run_dir / "independent_raw_audit.json"
    write_new(inside(output, "output"), value)
    print(json.dumps(value, indent=2, sort_keys=True, allow_nan=False))
    return 0 if value["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
