#!/usr/bin/env python3
"""Independent raw and deterministic attribution audit for ID-2J0."""

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
from scripts.rgeo_zgeo_1ms_id1a_context_anchor_pilot_independent import _numeric_max_difference  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2j0_post_holdout_attribution as primary  # noqa: E402


RAW_SCHEMA = "rgeo-zgeo-1ms-id2j0-independent-raw-v1"
ATTRIBUTION_SCHEMA = "rgeo-zgeo-1ms-id2j0-independent-attribution-v1"


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
    stage_path, run_dir = _inside(stage_path, "stage config"), _inside(run_dir, "run directory")
    try:
        stage, cfg, targets, id2c1_stage = primary.load(stage_path)
        expected = primary.streams(stage, cfg, targets, id2c1_stage)
    except Exception as exc:
        failures.append(f"STAGE_LOAD:{type(exc).__name__}:{exc}")
        stage, cfg, expected = _json(stage_path), None, []
    order = {row["rollout_id"]: index for index, row in enumerate(expected)}
    primary_path = run_dir / "result.json"
    result = _json(primary_path) if primary_path.is_file() else {}
    compact_paths = sorted(path for path in run_dir.glob("*.json")
                           if path.name not in ("result.json", "offline_preflight.json", "independent_raw_audit.json")
                           and "attribution" not in path.name)
    compact = [_json(path) for path in compact_paths]
    compact.sort(key=lambda row: order.get(row.get("rollout_id"), 999))
    if [row.get("rollout_id") for row in compact] != [row["rollout_id"] for row in expected[:len(compact)]]:
        failures.append("COMPACT_ORDER_OR_IDENTITY")
    actual_ids = sorted(path.name for path in (run_dir / "rollouts").iterdir() if path.is_dir()) \
        if (run_dir / "rollouts").is_dir() else []
    if actual_ids != sorted(row.get("rollout_id") for row in compact):
        failures.append("ROLLOUT_DIRECTORY_SET")
    raw_rows, lines, total = [], [], 0
    if cfg is not None:
        for row in compact:
            rollout_id, folder = row["rollout_id"], run_dir / "rollouts" / row["rollout_id"]
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
                if len(state["wire_current_a"]) != 48 or any(abs(float(a) - float(b)) > 1e-9
                        for a, b in zip(state["wire_current_a"], saved["wire_current_a"])):
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
            raw_rows.append({**{k: v for k, v in row.items() if k not in ("states", "actions")},
                             "states": states, "actions": row.get("actions", [])})
    inventory = hashlib.sha256("".join(f"{line}\n" for line in sorted(lines)).encode()).hexdigest()
    if inventory != result.get("required_artifact_inventory_sha256"):
        failures.append("INVENTORY_SHA256")
    if len(lines) != result.get("required_artifact_files") or total != result.get("required_artifact_bytes"):
        failures.append("INVENTORY_COUNT_OR_BYTES")
    prefix = primary._matched_prefix(raw_rows) if len(raw_rows) == 16 else []
    if len(prefix) != 8 or not all(row["passed"] for row in prefix):
        failures.append("MATCHED_PREFIX")
    counters = {"rollouts_completed": len(compact),
                "unique_cells_completed": len({x.get("cell_id") for x in compact}),
                "whole_history_groups_completed": len({x.get("group_id") for x in compact}),
                "reset_calls": sum(int(x.get("reset_calls", 0)) for x in compact),
                "advance_attempts": sum(int(x.get("advance_attempts", 0)) for x in compact),
                "plant_advance_gotsc_calls": sum(int(x.get("plant_advance_gotsc_calls", 0)) for x in compact),
                "verified_plant_advances": sum(int(x.get("verified_plant_advances", 0)) for x in compact)}
    for key, value in counters.items():
        if result.get(key) != value:
            failures.append(f"COUNTER:{key}")
    complete = len(raw_rows) == 16 and len(lines) == 2800 and len(failures) == 0
    if complete and (result.get("passed") is not True or result.get("route") != stage["routes"]["data_pass"]):
        failures.append("PRIMARY_ROUTE_OR_VERDICT")
    return {"schema_version": RAW_SCHEMA, "source_revision": source_revision,
            "stage_config_sha256": primary.CONFIG_SHA256,
            "primary_sha256": sha256(primary_path) if primary_path.is_file() else None,
            "audit_passed": not failures, "failures": list(dict.fromkeys(failures)),
            "raw_rollouts": len(raw_rows), "raw_states": sum(len(x["states"]) for x in raw_rows),
            "recomputed_counters": counters, "recomputed_inventory_sha256": inventory,
            "recomputed_inventory_files": len(lines), "recomputed_inventory_bytes": total,
            "recomputed_matched_prefix_checks": prefix, "models_fit_or_updated": 0,
            "claim_boundary": "Independent raw reparse of diagnostic replications; not blind holdout, fitting or control qualification."}


def audit_attribution(stage_path: Path, run_dir: Path, attribution: Path,
                      source_revision: str, recompute: Path) -> dict[str, Any]:
    stage_path, run_dir = _inside(stage_path, "stage config"), _inside(run_dir, "run directory")
    attribution, recompute = _inside(attribution, "attribution"), _inside(recompute, "recompute")
    failures = []
    raw = _json(run_dir / "independent_raw_audit.json")
    if not raw.get("audit_passed"):
        failures.append("RAW_AUDIT")
    saved = _json(attribution)
    if recompute.exists():
        failures.append("RECOMPUTE_OUTPUT_EXISTS")
        rebuilt = None
    else:
        try:
            rebuilt = primary.attribute(stage_path, source_revision, run_dir, recompute)
        except Exception as exc:
            failures.append(f"RECOMPUTE:{type(exc).__name__}:{exc}")
            rebuilt = None
    difference = _numeric_max_difference(rebuilt, saved)
    if difference > 1e-12:
        failures.append("ATTRIBUTION_NUMERIC_DIFFERENCE")
    for key in ("route", "audit_completed", "model_passed", "routing_diagnostics"):
        if rebuilt is not None and rebuilt.get(key) != saved.get(key):
            failures.append(f"ATTRIBUTION_FIELD:{key}")
    return {"schema_version": ATTRIBUTION_SCHEMA, "source_revision": source_revision,
            "stage_config_sha256": primary.CONFIG_SHA256,
            "primary_attribution_sha256": sha256(attribution),
            "recompute_sha256": sha256(recompute) if recompute.is_file() else None,
            "audit_passed": not failures, "failures": failures,
            "maximum_numeric_difference": difference, "recomputed_route": rebuilt.get("route") if rebuilt else None,
            "models_fit_retrained_tuned_selected_or_recalibrated": 0, "new_tsc_calls": 0,
            "claim_boundary": "Deterministic zero-fit attribution recomputation; not an independent model or control qualification."}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("raw", "attribution"))
    parser.add_argument("--stage-config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--attribution", type=Path)
    parser.add_argument("--recompute", type=Path)
    args = parser.parse_args(argv)
    if args.mode == "raw":
        result = audit_raw(args.stage_config, args.run_dir, args.source_revision)
    else:
        if args.attribution is None or args.recompute is None:
            raise ValueError("--attribution and --recompute required")
        result = audit_attribution(args.stage_config, args.run_dir, args.attribution,
                                   args.source_revision, args.recompute)
    write_new(_inside(args.output, "independent output"), result)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
