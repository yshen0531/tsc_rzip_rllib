#!/usr/bin/env python3
"""Structurally separate full-raw audit for ID-2Z4R1."""

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
from scripts import rgeo_zgeo_1ms_id2z4r1_earlier_switch_capture_frontier as primary  # noqa: E402


SCHEMA = (
    "rgeo-zgeo-1ms-id2z4r1-earlier-switch-capture-frontier-"
    "independent-raw-reporting-r1")


def _side_from_geometry(state: dict[str, Any]) -> str:
    """Reconstruct the contract side from independently parsed raw geometry."""
    return "HFS" if float(state["r_geo_m"]) < float(state["r_mid_m"]) else "LFS"


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
        raise ValueError("JSON object required")
    return value


def _state_times(folder: Path) -> list[int]:
    if not folder.is_dir():
        return []
    return sorted(
        int(path.name[:-2]) for path in folder.iterdir()
        if path.is_dir() and path.name.endswith("ms")
        and path.name[:-2].isdigit())


def audit(stage_path: Path, run_dir: Path,
          source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    stage_path = inside(stage_path, "config")
    run_dir = inside(run_dir, "run")
    result_path = run_dir / "result.json"
    result = load_json(result_path) if result_path.is_file() else {}
    try:
        stage, cfg, targets, reference, selected = primary.load(stage_path)
        constructed = primary.candidate_streams(stage, cfg, targets, selected)
        checks = [primary.validate_stream(stream, stage, cfg)
                  for stream in constructed]
        expected = [stream for stream, check in zip(constructed, checks)
                    if check["passed"]]
    except Exception as exc:
        failures.append(f"STAGE_LOAD:{type(exc).__name__}:{exc}")
        stage = load_json(stage_path)
        cfg = None
        reference = {}
        selected = {}
        expected = []
    expected_by_id = {stream["rollout_id"]: stream for stream in expected}
    order = {stream["rollout_id"]: index for index, stream in enumerate(expected)}
    compact_paths = sorted(
        path for path in run_dir.glob("*.json")
        if path.name not in {"result.json", "offline_preflight.json"}
        and not path.name.startswith("independent_raw_audit"))
    compact = [load_json(path) for path in compact_paths]
    compact.sort(key=lambda row: order.get(str(row.get("rollout_id")), 9999))
    compact_ids = [str(row.get("rollout_id")) for row in compact]
    expected_ids = [stream["rollout_id"] for stream in expected]
    if compact_ids != expected_ids[:len(compact_ids)]:
        failures.append("COMPACT_ORDER_OR_IDENTITY")
    if result.get("execution_integrity_passed") and compact_ids != expected_ids:
        failures.append("COMPLETE_EXECUTION_MISSING_COMPACT")
    for row in compact:
        if (row.get("schema_version") != primary.SCHEMA
                or row.get("source_revision") != source_revision):
            failures.append(f"COMPACT_IDENTITY:{row.get('rollout_id')}")

    rollout_root = run_dir / "rollouts"
    actual_ids = (sorted(path.name for path in rollout_root.iterdir()
                         if path.is_dir()) if rollout_root.is_dir() else [])
    if actual_ids != sorted(compact_ids):
        failures.append("ROLLOUT_DIRECTORY_SET")

    raw_rows: list[dict[str, Any]] = []
    inventory_lines: list[str] = []
    inventory_bytes = 0
    if cfg is not None:
        source_fields = list(_fields(
            cfg.simulation_root / cfg.start_folder / "inputa"))
        for compact_row in compact:
            rollout_id = str(compact_row["rollout_id"])
            stream = expected_by_id.get(rollout_id)
            if stream is None:
                failures.append(f"UNKNOWN_ROLLOUT:{rollout_id}")
                continue
            folder = rollout_root / rollout_id
            times = _state_times(folder)
            if (compact_row.get("passed")
                    and times != list(range(1100, 1218))):
                failures.append(f"STATE_DIRECTORY_SET:{rollout_id}")
            if times and times != list(range(1100, max(times) + 1)):
                failures.append(f"NONCONTIGUOUS_STATE_DIRECTORY:{rollout_id}")
            if any(time < 1100 or time > 1217 for time in times):
                failures.append(f"FORBIDDEN_STATE_DIRECTORY:{rollout_id}")
            states: list[dict[str, Any]] = []
            for index, time_ms in enumerate(times):
                state_folder = folder / f"{time_ms}ms"
                try:
                    state = _state(state_folder, cfg)
                    state["side"] = _side_from_geometry(state)
                except Exception as exc:
                    failures.append(
                        f"RAW_STATE:{rollout_id}:{time_ms}:"
                        f"{type(exc).__name__}:{exc}")
                    continue
                states.append(state)
                if index < len(compact_row.get("states", [])):
                    saved = compact_row["states"][index]
                    for key, tolerance in (
                            ("r_geo_m", 1e-12), ("z_geo_m", 1e-12),
                            ("r_mid_m", 1e-12), ("ip_a", 1e-9)):
                        if abs(float(state[key]) - float(saved[key])) > tolerance:
                            failures.append(
                                f"STATE_VALUE:{rollout_id}:{time_ms}:{key}")
                    if (len(state["actual_current_decimal_a_tsc"]) != 14
                            or state["actual_current_decimal_a_tsc"]
                            != saved.get("actual_current_decimal_a_tsc")):
                        failures.append(f"COIL_VALUE:{rollout_id}:{time_ms}")
                    if (len(state["wire_current_a"]) != 48
                            or len(saved.get("wire_current_a", [])) != 48
                            or any(abs(float(a) - float(b)) > 1e-9
                                   for a, b in zip(
                                       state["wire_current_a"],
                                       saved["wire_current_a"]))):
                        failures.append(f"WIRE_VALUE:{rollout_id}:{time_ms}")
                for name in ARTIFACTS:
                    artifact = state_folder / name
                    if not artifact.is_file():
                        failures.append(
                            f"MISSING_ARTIFACT:{rollout_id}:{time_ms}:{name}")
                        continue
                    size = artifact.stat().st_size
                    inventory_bytes += size
                    inventory_lines.append(
                        f"{artifact.relative_to(run_dir).as_posix()}\t"
                        f"{size}\t{sha256(artifact)}")

            issued_fields: list[list[str]] = []
            attempted = compact_row.get("attempted_actions", [])
            for issue, action in enumerate(attempted):
                if issue >= len(times):
                    failures.append(f"ACTION_WITHOUT_STATE:{rollout_id}:{issue}")
                    continue
                fields = list(_fields(folder / f"{1100 + issue}ms" / "inputa"))
                issued_fields.append(fields)
                if fields != action.get("expected_card15_fields"):
                    failures.append(f"ISSUED_CARD15:{rollout_id}:{issue}")
                if (issue >= len(stream["actions"])
                        or fields != stream["actions"][issue][
                            "expected_card15_fields"]):
                    failures.append(f"FROZEN_ACTION:{rollout_id}:{issue}")
            if len(compact_row.get("actions", [])) > len(attempted):
                failures.append(f"SUCCESS_ACTION_COUNT:{rollout_id}")
            try:
                restore_arrival_active_commands(states, issued_fields)
                if states:
                    states[0]["active_command_card15_fields"] = source_fields
            except Exception as exc:
                failures.append(
                    f"ACTIVE_COMMAND:{rollout_id}:{type(exc).__name__}:{exc}")
            raw_rows.append({
                **{key: value for key, value in compact_row.items()
                   if key not in ("states", "actions")},
                "recovered_from_complete_raw_without_tsc": True,
                "states": states,
                "actions": compact_row.get("actions", []),
            })

    inventory_sha = hashlib.sha256(
        "".join(f"{line}\n" for line in sorted(inventory_lines)).encode()
    ).hexdigest()
    if inventory_sha != result.get("required_artifact_inventory_sha256"):
        failures.append("INVENTORY_SHA256")
    if (len(inventory_lines) != result.get("required_artifact_files")
            or inventory_bytes != result.get("required_artifact_bytes")):
        failures.append("INVENTORY_COUNT_OR_BYTES")

    prefixes = [primary.prefix_check(row, reference, selected, stage)
                for row in raw_rows]
    execution = bool(raw_rows and all(
        row.get("passed") or primary.z3.z2.safe_stop(row, stage)
        for row in raw_rows))
    expected_files = 5 * sum(len(row.get("states", [])) for row in raw_rows)
    raw_ok = bool(
        execution and len(inventory_lines) == expected_files
        and not any(value.startswith("MISSING_ARTIFACT")
                    for value in failures))
    scientific = primary.metrics(raw_rows, stage, cfg)
    route = primary.route_for(stage, execution, raw_ok, prefixes, scientific)
    if result.get("prefix_checks") != prefixes:
        failures.append("RECOMPUTE:PREFIX_CHECKS")
    if result.get("scientific_metrics") != scientific:
        failures.append("RECOMPUTE:SCIENTIFIC_METRICS")
    if result.get("selected_candidate_id") != scientific.get(
            "selected_candidate_id"):
        failures.append("RECOMPUTE:SELECTED_CANDIDATE")
    if (result.get("route") != route
            or result.get("passed") != (
                route == stage["routes"]["capture_candidate"])):
        failures.append("PRIMARY_ROUTE_OR_VERDICT")
    counters = {
        "rollouts_completed": len(compact),
        "complete_rollouts": sum(bool(row.get("passed")) for row in compact),
        "guarded_safe_stops": sum(
            primary.z3.z2.safe_stop(row, stage) for row in compact),
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
    if (result.get("source_revision") != source_revision
            or result.get("stage_config_sha256") != primary.CONFIG_SHA256):
        failures.append("RESULT_IDENTITY")
    if (result.get("models_fit_or_updated") != 0
            or result.get("calibration_or_holdout_records_read") != 0):
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
        "recomputed_scientific_metrics": scientific,
        "recomputed_selected_candidate_id": scientific.get(
            "selected_candidate_id"),
        "finite_capture_candidate": bool(
            not failures and route == stage["routes"]["capture_candidate"]),
        "models_fit_or_updated": 0,
        "calibration_or_holdout_records_read": 0,
        "claim_boundary": (
            "Independent full-raw finite ID2Z4R1 audit; not hold, recovery, "
            "controller, waypoint or reachability qualification."),
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
