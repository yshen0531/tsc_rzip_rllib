#!/usr/bin/env python3
"""Independent full-raw audit for ID-2R1."""

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
from scripts.rgeo_zgeo_1ms_id0_vector_tail_independent import ARTIFACTS, _fields, _state  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2r1_f03_exact_replay as primary  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-id2r1-f03-exact-replay-independent-v1"


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


def audit(stage_path: Path, run_dir: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    stage_path, run_dir = inside(stage_path, "config"), inside(run_dir, "run")
    try:
        stage, cfg, targets, source, originals = primary.load(stage_path)
        expected = primary.campaign_streams(stage, cfg, targets, source)
    except Exception as exc:
        failures.append(f"STAGE_LOAD:{type(exc).__name__}:{exc}")
        stage, cfg, originals, expected = load_json(stage_path), None, {}, []
    order = {row["rollout_id"]: index for index, row in enumerate(expected)}
    result_path = run_dir / "result.json"
    result = load_json(result_path) if result_path.is_file() else {}
    paths = sorted(path for path in run_dir.glob("*.json") if path.name not in
                   ("result.json", "offline_preflight.json", "independent_raw_audit.json"))
    compact = [load_json(path) for path in paths]
    compact.sort(key=lambda row: order.get(row.get("rollout_id"), 999))
    if [row.get("rollout_id") for row in compact] != [row["rollout_id"] for row in expected[:len(compact)]]:
        failures.append("COMPACT_ORDER_OR_IDENTITY")
    rollout_root = run_dir / "rollouts"
    actual_ids = sorted(path.name for path in rollout_root.iterdir() if path.is_dir()) if rollout_root.is_dir() else []
    if actual_ids != sorted(row.get("rollout_id") for row in compact):
        failures.append("ROLLOUT_DIRECTORY_SET")
    raw_rows: list[dict[str, Any]] = []
    lines: list[str] = []
    total = 0
    if cfg is not None:
        for row in compact:
            folder = rollout_root / row["rollout_id"]
            times = sorted(int(path.name[:-2]) for path in folder.iterdir()
                           if path.is_dir() and path.name.endswith("ms")) if folder.is_dir() else []
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
                if len(state["wire_current_a"]) != 48 or any(
                        abs(float(a) - float(b)) > 1e-9
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
    execution = len(raw_rows) == 5 and all(row.get("passed") for row in compact)
    prefixes = primary.matched_prefix_checks(raw_rows, stage) if execution else []
    replays = primary.replay_checks(raw_rows, originals, stage) if execution else []
    responses = primary.response_checks(raw_rows, originals, stage) if execution else []
    if prefixes != result.get("matched_prefix_checks"):
        failures.append("PREFIX_RECOMPUTE")
    if replays != result.get("original_to_fresh_replay_checks"):
        failures.append("REPLAY_RECOMPUTE")
    if responses != result.get("paired_response_replay_checks"):
        failures.append("RESPONSE_RECOMPUTE")
    counters = {
        "rollouts_completed": len(compact),
        "reset_calls": sum(int(row.get("reset_calls", 0)) for row in compact),
        "advance_attempts": sum(int(row.get("advance_attempts", 0)) for row in compact),
        "plant_advance_gotsc_calls": sum(int(row.get("plant_advance_gotsc_calls", 0)) for row in compact),
        "verified_plant_advances": sum(int(row.get("verified_plant_advances", 0)) for row in compact),
    }
    for key, value in counters.items():
        if result.get(key) != value:
            failures.append(f"COUNTER:{key}")
    raw_ok = len(lines) == 875 and not any(reason.startswith(("RAW_STATE", "MISSING_ARTIFACT", "STATE_DIRECTORY")) for reason in failures)
    replay_ok = (len(prefixes) == 4 and all(x["passed"] for x in prefixes)
                 and len(replays) == 5 and all(x["passed"] for x in replays)
                 and len(responses) == 4 and all(x["passed"] for x in responses))
    if not execution:
        recomputed_route = stage["routes"]["execution_or_interface_fail"]
    elif not raw_ok:
        recomputed_route = stage["routes"]["raw_integrity_fail"]
    elif not replay_ok:
        recomputed_route = stage["routes"]["replay_mismatch"]
    else:
        recomputed_route = stage["routes"]["pass"]
    if result.get("route") != recomputed_route or bool(result.get("passed")) != (recomputed_route == stage["routes"]["pass"]):
        failures.append("PRIMARY_ROUTE_OR_VERDICT")
    return {
        "schema_version": SCHEMA, "source_revision": source_revision,
        "stage_config_sha256": primary.CONFIG_SHA256,
        "primary_sha256": sha256(result_path) if result_path.is_file() else None,
        "audit_passed": not failures, "failures": list(dict.fromkeys(failures)),
        "raw_rollouts": len(raw_rows), "raw_states": sum(len(row["states"]) for row in raw_rows),
        "recomputed_counters": counters, "recomputed_inventory_sha256": inventory,
        "recomputed_inventory_files": len(lines), "recomputed_inventory_bytes": total,
        "recomputed_matched_prefix_checks": prefixes,
        "recomputed_original_to_fresh_replay_checks": replays,
        "recomputed_paired_response_replay_checks": responses,
        "recomputed_route": recomputed_route,
        "fresh_records_have_zero_fit_weight": True, "models_fit_or_updated": 0,
        "claim_boundary": "Independent full-raw ID2R1 integrity replay audit only; no model or control qualification.",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-config", type=Path, default=primary.CONFIG)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = audit(args.stage_config, args.run_dir, args.source_revision)
    write_new(inside(args.output, "output"), result)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

