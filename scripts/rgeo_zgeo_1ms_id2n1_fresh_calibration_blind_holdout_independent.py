#!/usr/bin/env python3
"""Independent raw reparse of ID-2N1 calibration and blind holdout."""

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

from scripts.rgeo_zgeo_1ms_id0_vector_tail import sha256, write_new  # noqa: E402
from scripts.rgeo_zgeo_1ms_id0_vector_tail_independent import ARTIFACTS, _fields, _state  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2n1_fresh_calibration_blind_holdout as primary  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-id2n1-independent-raw-audit-v1"


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


def audit(stage_path: Path, run_dir: Path, source_revision: str) -> dict[str, Any]:
    failures = []
    stage_path, run_dir = _inside(stage_path, "config"), _inside(run_dir, "run")
    try:
        stage, cfg, targets, source, data, model = primary.load(stage_path)
        expected = primary.campaign_streams(stage, cfg, targets, source)
    except Exception as exc:
        failures.append(f"STAGE_LOAD:{type(exc).__name__}:{exc}")
        stage, cfg, expected, data, model = _json(stage_path), None, [], None, None
    order = {row["rollout_id"]: index for index, row in enumerate(expected)}
    result_path = run_dir / "result.json"
    result = _json(result_path) if result_path.is_file() else {}
    excluded = {"result.json", "offline_preflight.json", "calibration.json", "independent_raw_audit.json"}
    compact_paths = sorted(path for path in run_dir.glob("*.json") if path.name not in excluded)
    compact = [_json(path) for path in compact_paths]
    compact.sort(key=lambda row: order.get(row.get("rollout_id"), 999))
    if [row.get("rollout_id") for row in compact] != [row["rollout_id"] for row in expected[:len(compact)]]:
        failures.append("COMPACT_ORDER_OR_IDENTITY")
    rollout_root = run_dir / "rollouts"
    actual_ids = sorted(path.name for path in rollout_root.iterdir() if path.is_dir()) if rollout_root.is_dir() else []
    if actual_ids != sorted(row.get("rollout_id") for row in compact):
        failures.append("ROLLOUT_DIRECTORY_SET")
    raw_rows, lines, total = [], [], 0
    if cfg is not None:
        for row in compact:
            folder = rollout_root / row["rollout_id"]
            times = sorted(int(path.name[:-2]) for path in folder.iterdir()
                           if path.is_dir() and path.name.endswith("ms"))
            if times != list(range(1100, 1135)):
                failures.append(f"STATE_DIRECTORY_SET:{row['rollout_id']}")
                continue
            states = []
            for index, time_ms in enumerate(times):
                state_folder = folder / f"{time_ms}ms"
                try:
                    state = _state(state_folder, cfg)
                except Exception as exc:
                    failures.append(f"RAW_STATE:{row['rollout_id']}:{time_ms}:{type(exc).__name__}:{exc}")
                    continue
                states.append(state)
                saved = row["states"][index]
                for key, tolerance in (("r_geo_m", 1e-12), ("z_geo_m", 1e-12),
                                       ("r_mid_m", 1e-12), ("ip_a", 1e-9)):
                    if abs(float(state[key]) - float(saved[key])) > tolerance:
                        failures.append(f"STATE_VALUE:{row['rollout_id']}:{time_ms}:{key}")
                if state["actual_current_decimal_a_tsc"] != saved["actual_current_decimal_a_tsc"]:
                    failures.append(f"COIL_VALUE:{row['rollout_id']}:{time_ms}")
                if len(state["wire_current_a"]) != 48 or any(abs(float(a) - float(b)) > 1e-9
                        for a, b in zip(state["wire_current_a"], saved["wire_current_a"])):
                    failures.append(f"WIRE_VALUE:{row['rollout_id']}:{time_ms}")
                for name in ARTIFACTS:
                    artifact = state_folder / name
                    if not artifact.is_file():
                        failures.append(f"MISSING_ARTIFACT:{row['rollout_id']}:{time_ms}:{name}")
                        continue
                    size = artifact.stat().st_size
                    total += size
                    lines.append(f"{artifact.relative_to(run_dir).as_posix()}\t{size}\t{sha256(artifact)}")
            for issue, action in enumerate(row.get("actions", [])):
                if list(_fields(folder / f"{1100 + issue}ms" / "inputa")) != action["expected_card15_fields"]:
                    failures.append(f"ISSUED_CARD15:{row['rollout_id']}:{issue}")
            raw_rows.append({**{key: value for key, value in row.items() if key not in ("states", "actions")},
                             "states": states, "actions": row.get("actions", [])})
    inventory = hashlib.sha256("".join(f"{line}\n" for line in sorted(lines)).encode()).hexdigest()
    if inventory != result.get("required_artifact_inventory_sha256"):
        failures.append("INVENTORY_SHA256")
    if len(lines) != result.get("required_artifact_files") or total != result.get("required_artifact_bytes"):
        failures.append("INVENTORY_COUNT_OR_BYTES")
    cal_prefix = primary.prefix_checks(raw_rows, "calibration") if len(raw_rows) >= 14 else []
    cal_replay = primary.replay_checks(raw_rows, stage, "calibration") if len(raw_rows) >= 14 else []
    calibration = primary.calibrate(raw_rows, stage, data, model, source_revision) if (
        data is not None and model is not None and len(raw_rows) >= 14
        and all(row["passed"] for row in cal_prefix + cal_replay)) else None
    holdout_opened = bool(calibration and calibration["passed"] and len(raw_rows) > 14)
    hold_prefix = primary.prefix_checks(raw_rows, "holdout") if len(raw_rows) == 28 else []
    hold_replay = primary.replay_checks(raw_rows, stage, "holdout") if len(raw_rows) == 28 else []
    holdout = primary.holdout_metrics(raw_rows, stage, data, model, calibration) if (
        holdout_opened and len(raw_rows) == 28 and all(row["passed"] for row in hold_prefix + hold_replay)) else None
    for key, value in (("calibration_prefix_checks", cal_prefix), ("calibration_replay_checks", cal_replay),
                       ("calibration", calibration), ("holdout_prefix_checks", hold_prefix),
                       ("holdout_replay_checks", hold_replay), ("holdout", holdout)):
        if result.get(key) != value:
            failures.append(f"RECOMPUTE:{key}")
    counters = {"rollouts_completed": len(compact), "unique_cells_completed": len({r.get("cell_id") for r in compact}),
                "reset_calls": sum(int(r.get("reset_calls", 0)) for r in compact),
                "advance_attempts": sum(int(r.get("advance_attempts", 0)) for r in compact),
                "plant_advance_gotsc_calls": sum(int(r.get("plant_advance_gotsc_calls", 0)) for r in compact),
                "verified_plant_advances": sum(int(r.get("verified_plant_advances", 0)) for r in compact)}
    for key, value in counters.items():
        if result.get(key) != value:
            failures.append(f"COUNTER:{key}")
    expected_pass = (len(raw_rows) == 28 and calibration is not None and calibration["passed"]
                     and holdout is not None and holdout["passed"] and not failures)
    if expected_pass and (result.get("passed") is not True or result.get("route") != stage["routes"]["pass"]):
        failures.append("PRIMARY_ROUTE_OR_VERDICT")
    return {"schema_version": SCHEMA, "source_revision": source_revision,
            "stage_config_sha256": primary.CONFIG_SHA256,
            "primary_sha256": sha256(result_path) if result_path.is_file() else None,
            "audit_passed": not failures, "failures": list(dict.fromkeys(failures)),
            "raw_rollouts": len(raw_rows), "raw_states": sum(len(row["states"]) for row in raw_rows),
            "recomputed_counters": counters, "recomputed_inventory_sha256": inventory,
            "recomputed_inventory_files": len(lines), "recomputed_inventory_bytes": total,
            "recomputed_calibration": calibration, "recomputed_holdout": holdout,
            "primary_scientific_passed": result.get("passed"), "models_fit_or_updated": 0,
            "claim_boundary": "Independent raw reparse and frozen-model recomputation of finite ID2N1; not control qualification."}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-config", type=Path, default=primary.CONFIG)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = audit(args.stage_config, args.run_dir, args.source_revision)
    write_new(_inside(args.output, "audit output"), result)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
