#!/usr/bin/env python3
"""Independent raw and frozen-calibration audit for ID-2H1."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_id0_vector_tail import compare_rows, sha256, write_new  # noqa: E402
from scripts.rgeo_zgeo_1ms_id0_vector_tail_independent import ARTIFACTS, _fields, _state  # noqa: E402
from scripts.rgeo_zgeo_1ms_id1a_context_anchor_pilot_independent import _numeric_max_difference  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2g1_grouped_causal_model as model  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2h1_whole_history_calibration as primary  # noqa: E402


RAW_SCHEMA = "rgeo-zgeo-1ms-id2h1-independent-raw-v1"
CALIBRATION_SCHEMA = "rgeo-zgeo-1ms-id2h1-independent-calibration-v1"


def _inside(path: Path, label: str) -> Path:
    value = path.resolve()
    try:
        value.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} leaves repository") from exc
    return value


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"object required: {path}")
    return value


def audit_raw(stage_path: Path, run_dir: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    stage_path = _inside(stage_path, "stage config")
    run_dir = _inside(run_dir, "run directory")
    try:
        stage, cfg, targets, id2c1_stage = primary.load(stage_path)
        streams = primary.campaign_streams(stage, cfg, targets, id2c1_stage)
    except Exception as exc:
        failures.append(f"STAGE_LOAD:{type(exc).__name__}:{exc}")
        stage = _json(stage_path)
        cfg = None
        streams = []
    order = {row["rollout_id"]: index for index, row in enumerate(streams)}
    primary_path = run_dir / "result.json"
    result = _json(primary_path) if primary_path.is_file() else {}
    if result.get("schema_version") != primary.SCHEMA or result.get("source_revision") != source_revision:
        failures.append("PRIMARY_IDENTITY")
    compact_paths = sorted(path for path in run_dir.glob("*.json")
                           if path.name not in ("result.json", "offline_preflight.json", "independent_raw_audit.json")
                           and "calibration" not in path.name)
    compact_rows = [_json(path) for path in compact_paths]
    if any(row.get("rollout_id") not in order for row in compact_rows):
        failures.append("UNKNOWN_COMPACT_ROLLOUT")
    compact_rows.sort(key=lambda row: order.get(row.get("rollout_id"), len(order)))
    if [row.get("rollout_id") for row in compact_rows] != [row["rollout_id"] for row in streams[:len(compact_rows)]]:
        failures.append("COMPACT_ORDER")
    rollout_root = run_dir / "rollouts"
    actual_ids = sorted(path.name for path in rollout_root.iterdir() if path.is_dir()) if rollout_root.is_dir() else []
    if actual_ids != sorted(row.get("rollout_id") for row in compact_rows):
        failures.append("ROLLOUT_DIRECTORY_SET")
    raw_rows = []
    inventory_lines: list[str] = []
    inventory_bytes = 0
    if cfg is not None:
        for compact in compact_rows:
            rollout_id = compact["rollout_id"]
            folder = rollout_root / rollout_id
            expected_times = list(range(1100, 1135))
            actual_times = sorted(int(path.name[:-2]) for path in folder.iterdir()
                                  if path.is_dir() and path.name.endswith("ms"))
            if actual_times != expected_times:
                failures.append(f"STATE_DIRECTORY_SET:{rollout_id}")
                continue
            states = []
            for index, time_ms in enumerate(expected_times):
                state_folder = folder / f"{time_ms}ms"
                try:
                    state = _state(state_folder, cfg)
                    states.append(state)
                except Exception as exc:
                    failures.append(f"RAW_STATE:{rollout_id}:{time_ms}:{type(exc).__name__}:{exc}")
                    continue
                expected = compact["states"][index]
                for key, tolerance in (("r_geo_m", 1e-12), ("z_geo_m", 1e-12),
                                       ("r_mid_m", 1e-12), ("ip_a", 1e-9)):
                    if abs(float(state[key]) - float(expected[key])) > tolerance:
                        failures.append(f"STATE_VALUE:{rollout_id}:{time_ms}:{key}")
                if state["actual_current_decimal_a_tsc"] != expected["actual_current_decimal_a_tsc"]:
                    failures.append(f"COIL_VALUE:{rollout_id}:{time_ms}")
                if len(state["wire_current_a"]) != 48 or any(
                    abs(float(a) - float(b)) > 1e-9
                    for a, b in zip(state["wire_current_a"], expected["wire_current_a"])
                ):
                    failures.append(f"WIRE_VALUE:{rollout_id}:{time_ms}")
                for name in ARTIFACTS:
                    path = state_folder / name
                    if not path.is_file():
                        failures.append(f"MISSING_ARTIFACT:{rollout_id}:{time_ms}:{name}")
                        continue
                    size = path.stat().st_size
                    inventory_bytes += size
                    inventory_lines.append(f"{path.relative_to(run_dir).as_posix()}\t{size}\t{sha256(path)}")
            for issue, action in enumerate(compact.get("actions", [])):
                if list(_fields(folder / f"{1100 + issue}ms" / "inputa")) != action["expected_card15_fields"]:
                    failures.append(f"ISSUED_CARD15:{rollout_id}:{issue}")
            raw_rows.append({**{key: value for key, value in compact.items() if key not in ("states", "actions")},
                             "states": states, "actions": compact.get("actions", [])})
    inventory_sha = hashlib.sha256("".join(f"{line}\n" for line in sorted(inventory_lines)).encode()).hexdigest()
    if inventory_sha != result.get("required_artifact_inventory_sha256"):
        failures.append("INVENTORY_SHA256")
    if len(inventory_lines) != result.get("required_artifact_files") or inventory_bytes != result.get("required_artifact_bytes"):
        failures.append("INVENTORY_COUNT_OR_BYTES")
    checks = primary._repeatability(raw_rows, stage) if len(raw_rows) == 40 else []
    if len(checks) != 20 or not all(row["passed"] for row in checks):
        failures.append("REPEATABILITY")
    counters = {
        "rollouts_completed": len(compact_rows),
        "unique_cells_completed": len({row.get("cell_id") for row in compact_rows}),
        "whole_history_groups_completed": len({row.get("group_id") for row in compact_rows}),
        "reset_calls": sum(int(row.get("reset_calls", 0)) for row in compact_rows),
        "advance_attempts": sum(int(row.get("advance_attempts", 0)) for row in compact_rows),
        "plant_advance_gotsc_calls": sum(int(row.get("plant_advance_gotsc_calls", 0)) for row in compact_rows),
        "verified_plant_advances": sum(int(row.get("verified_plant_advances", 0)) for row in compact_rows),
    }
    for key, value in counters.items():
        if value != result.get(key):
            failures.append(f"COUNTER:{key}")
    expected_pass = (len(raw_rows) == 40 and len(checks) == 20 and all(row["passed"] for row in checks)
                     and not any(value.startswith(("RAW_STATE:", "MISSING_ARTIFACT:", "STATE_DIRECTORY_SET:"))
                                 for value in failures))
    expected_route = stage["routes"]["data_pass"] if expected_pass else result.get("route")
    if expected_pass and (result.get("route") != expected_route or result.get("passed") is not True):
        failures.append("PRIMARY_ROUTE_OR_VERDICT")
    return {
        "schema_version": RAW_SCHEMA,
        "source_revision": source_revision,
        "stage_config_sha256": primary.CONFIG_SHA256,
        "primary_sha256": sha256(primary_path) if primary_path.is_file() else None,
        "audit_passed": not failures,
        "failures": list(dict.fromkeys(failures)),
        "raw_rollouts": len(raw_rows),
        "raw_states": sum(len(row["states"]) for row in raw_rows),
        "recomputed_counters": counters,
        "recomputed_inventory_sha256": inventory_sha,
        "recomputed_inventory_files": len(inventory_lines),
        "recomputed_inventory_bytes": inventory_bytes,
        "recomputed_replay_pair_checks": checks,
        "calibration_data_eligible": expected_pass and not failures,
        "models_fit_or_updated": 0,
        "claim_boundary": "Independent raw reparse of fresh ID2H1 calibration histories; not model fitting, holdout or control qualification.",
    }


def audit_calibration(stage_path: Path, run_dir: Path, calibration_path: Path,
                      source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    stage, cfg, targets, id2c1_stage = primary.load(_inside(stage_path, "stage config"))
    run_dir = _inside(run_dir, "run directory")
    calibration_path = _inside(calibration_path, "calibration result")
    saved = _json(calibration_path)
    raw_audit = _json(run_dir / "independent_raw_audit.json")
    if not raw_audit.get("audit_passed"):
        failures.append("RAW_AUDIT")
    try:
        development_stage = model.load_stage(ROOT / stage["evidence"]["id2g1r1_config"]["path"])
        data = model.extract_dataset(development_stage)
        streams = primary.campaign_streams(stage, cfg, targets, id2c1_stage)
        cells = primary._calibration_cells(stage, run_dir, streams, data, cfg)
        members = primary._load_tcn(stage)
        recomputed = primary.calibration_metrics(stage, cells, data, members)
    except Exception as exc:
        failures.append(f"RECOMPUTE:{type(exc).__name__}:{exc}")
        recomputed = None
    maximum_difference = _numeric_max_difference(recomputed, saved.get("calibration_metrics"))
    if maximum_difference > 1e-12:
        failures.append("CALIBRATION_METRICS")
    if saved.get("source_revision") != source_revision or saved.get("selected_model_sha256") != stage["evidence"]["selected_model"]["sha256"]:
        failures.append("CALIBRATION_IDENTITY")
    expected_pass = bool(recomputed and recomputed.get("passed"))
    expected_route = stage["routes"]["pass"] if expected_pass else stage["routes"]["calibration_fail"]
    if bool(saved.get("passed")) != expected_pass or saved.get("route") != expected_route:
        failures.append("CALIBRATION_ROUTE_OR_VERDICT")
    return {
        "schema_version": CALIBRATION_SCHEMA,
        "source_revision": source_revision,
        "stage_config_sha256": primary.CONFIG_SHA256,
        "primary_calibration_sha256": sha256(calibration_path),
        "selected_model_sha256": stage["evidence"]["selected_model"]["sha256"],
        "audit_passed": not failures,
        "failures": list(dict.fromkeys(failures)),
        "maximum_numeric_difference": maximum_difference,
        "recomputed_calibration_metrics": recomputed,
        "primary_passed": expected_pass,
        "primary_route": expected_route,
        "models_fit_retrained_tuned_or_selected": 0,
        "id2c2_records_read": 0,
        "blind_holdout_records_read": 0,
        "controller_authorized": False,
        "claim_boundary": "Independent full raw re-extraction and frozen-TCN calibration recomputation; not holdout, tube or controller qualification.",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("raw", "calibration"))
    parser.add_argument("--stage-config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--calibration")
    args = parser.parse_args(argv)
    if args.mode == "raw":
        value = audit_raw(args.stage_config, args.run_dir, args.source_revision)
    else:
        if args.calibration is None:
            raise ValueError("--calibration is required")
        value = audit_calibration(args.stage_config, args.run_dir, Path(args.calibration), args.source_revision)
    write_new(_inside(args.output, "independent output"), value)
    print(json.dumps(value, indent=2, sort_keys=True, allow_nan=False))
    return 0 if value["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
