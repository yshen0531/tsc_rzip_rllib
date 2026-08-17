#!/usr/bin/env python3
"""Independent raw audit of the ID-2K1 factorized development campaign."""

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
from scripts import rgeo_zgeo_1ms_id2k1_factorized_history_sign_development as primary  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-id2k1-independent-raw-v1"


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
    failures: list[str] = []
    stage_path, run_dir = _inside(stage_path, "stage config"), _inside(run_dir, "run directory")
    try:
        stage, cfg, targets, source = primary.load(stage_path)
        expected = primary.campaign_streams(stage, cfg, targets, source)
    except Exception as exc:
        failures.append(f"STAGE_LOAD:{type(exc).__name__}:{exc}")
        stage, cfg, expected = _json(stage_path), None, []
    order = {row["rollout_id"]: index for index, row in enumerate(expected)}
    primary_path = run_dir / "result.json"
    result = _json(primary_path) if primary_path.is_file() else {}
    compact_paths = sorted(path for path in run_dir.glob("*.json")
                           if path.name not in ("result.json", "offline_preflight.json",
                                                "independent_raw_audit.json"))
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
            rollout_id, folder = row["rollout_id"], rollout_root / row["rollout_id"]
            times = sorted(int(path.name[:-2]) for path in folder.iterdir()
                           if path.is_dir() and path.name.endswith("ms"))
            if times != list(range(1100, 1135)):
                failures.append(f"STATE_DIRECTORY_SET:{rollout_id}")
                continue
            states = []
            for index, time_ms in enumerate(times):
                state_folder = folder / f"{time_ms}ms"
                try:
                    state = _state(state_folder, cfg)
                except Exception as exc:
                    failures.append(f"RAW_STATE:{rollout_id}:{time_ms}:{type(exc).__name__}:{exc}")
                    continue
                states.append(state)
                saved = row["states"][index]
                for key, tolerance in (("r_geo_m", 1e-12), ("z_geo_m", 1e-12),
                                       ("r_mid_m", 1e-12), ("ip_a", 1e-9)):
                    if abs(float(state[key]) - float(saved[key])) > tolerance:
                        failures.append(f"STATE_VALUE:{rollout_id}:{time_ms}:{key}")
                if state["actual_current_decimal_a_tsc"] != saved["actual_current_decimal_a_tsc"]:
                    failures.append(f"COIL_VALUE:{rollout_id}:{time_ms}")
                if len(state["wire_current_a"]) != 48 or any(
                    abs(float(a) - float(b)) > 1e-9
                    for a, b in zip(state["wire_current_a"], saved["wire_current_a"])
                ):
                    failures.append(f"WIRE_VALUE:{rollout_id}:{time_ms}")
                for name in ARTIFACTS:
                    artifact = state_folder / name
                    if not artifact.is_file():
                        failures.append(f"MISSING_ARTIFACT:{rollout_id}:{time_ms}:{name}")
                        continue
                    size = artifact.stat().st_size
                    total += size
                    lines.append(f"{artifact.relative_to(run_dir).as_posix()}\t{size}\t{sha256(artifact)}")
            for issue, action in enumerate(row.get("actions", [])):
                if list(_fields(folder / f"{1100 + issue}ms" / "inputa")) != action["expected_card15_fields"]:
                    failures.append(f"ISSUED_CARD15:{rollout_id}:{issue}")
            raw_rows.append({**{key: value for key, value in row.items() if key not in ("states", "actions")},
                             "states": states, "actions": row.get("actions", [])})
    inventory = hashlib.sha256("".join(f"{line}\n" for line in sorted(lines)).encode()).hexdigest()
    if inventory != result.get("required_artifact_inventory_sha256"):
        failures.append("INVENTORY_SHA256")
    if len(lines) != result.get("required_artifact_files") or total != result.get("required_artifact_bytes"):
        failures.append("INVENTORY_COUNT_OR_BYTES")
    prefixes = primary.matched_prefix_checks(raw_rows) if len(raw_rows) == 43 else []
    replays = primary.critical_replay_checks(raw_rows, stage) if len(raw_rows) == 43 else []
    metrics = primary.response_metrics(raw_rows, stage) if len(raw_rows) == 43 else {"passed": False}
    if prefixes != result.get("matched_prefix_checks"):
        failures.append("MATCHED_PREFIX_RECOMPUTE")
    if replays != result.get("critical_replay_checks"):
        failures.append("CRITICAL_REPLAY_RECOMPUTE")
    if metrics != result.get("response_metrics"):
        failures.append("RESPONSE_METRICS_RECOMPUTE")
    counters = {
        "rollouts_completed": len(compact),
        "unique_cells_completed": len({row.get("cell_id") for row in compact}),
        "whole_history_groups_completed": len({row.get("group_id") for row in compact}),
        "reset_calls": sum(int(row.get("reset_calls", 0)) for row in compact),
        "advance_attempts": sum(int(row.get("advance_attempts", 0)) for row in compact),
        "plant_advance_gotsc_calls": sum(int(row.get("plant_advance_gotsc_calls", 0)) for row in compact),
        "verified_plant_advances": sum(int(row.get("verified_plant_advances", 0)) for row in compact),
    }
    for key, value in counters.items():
        if result.get(key) != value:
            failures.append(f"COUNTER:{key}")
    complete = (len(raw_rows) == 43 and len(lines) == 7525 and len(prefixes) == 8
                and all(row["passed"] for row in prefixes) and len(replays) == 3
                and all(row["passed"] for row in replays) and metrics.get("passed"))
    if complete and (result.get("passed") is not True or result.get("route") != stage["routes"]["pass"]):
        failures.append("PRIMARY_ROUTE_OR_VERDICT")
    return {
        "schema_version": SCHEMA, "source_revision": source_revision,
        "stage_config_sha256": primary.CONFIG_SHA256,
        "primary_sha256": sha256(primary_path) if primary_path.is_file() else None,
        "audit_passed": not failures, "failures": list(dict.fromkeys(failures)),
        "raw_rollouts": len(raw_rows), "raw_states": sum(len(row["states"]) for row in raw_rows),
        "recomputed_counters": counters, "recomputed_inventory_sha256": inventory,
        "recomputed_inventory_files": len(lines), "recomputed_inventory_bytes": total,
        "recomputed_matched_prefix_checks": prefixes,
        "recomputed_critical_replay_checks": replays,
        "recomputed_response_metrics": metrics,
        "development_fit_data_eligible": complete and not failures,
        "models_fit_or_updated": 0, "id2c2_records_read": 0,
        "claim_boundary": "Independent full-raw reparse of finite ID2K1 development data; not calibration, holdout or control qualification.",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-config", type=Path, default=primary.CONFIG)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = audit(args.stage_config, args.run_dir, args.source_revision)
    write_new(_inside(args.output, "independent output"), result)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
