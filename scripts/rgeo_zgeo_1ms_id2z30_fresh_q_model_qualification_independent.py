#!/usr/bin/env python3
"""Independent full-raw audit for the frozen ID-2Z30 campaign."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_id2z30_fresh_q_model_qualification as primary  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2z27_dynamic_output_aligned_campaign_independent as i27  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2z9_late_root_branch_utility_support_independent as rawio  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-id2z30-fresh-q-model-qualification-independent-v1"


def _inside(path: Path, label: str) -> Path:
    value = path.resolve()
    try:
        value.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(f"{label} leaves repository") from exc
    return value


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(_inside(path, "JSON path").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON object required")
    return value


def _compact(run_dir: Path, expected: Sequence[dict[str, Any]],
             failures: list[str]) -> list[dict[str, Any]]:
    excluded = {"result.json", "offline_preflight.json", "independent_raw_audit.json"}
    values = [_read(path) for path in sorted(run_dir.glob("*.json"))
              if path.name not in excluded]
    values = [row for row in values if "rollout_id" in row]
    order = {row["rollout_id"]: index for index, row in enumerate(expected)}
    values.sort(key=lambda row: order.get(row.get("rollout_id"), 999))
    if ([row.get("rollout_id") for row in values]
            != [row["rollout_id"] for row in expected[:len(values)]]) or len(values) != len(
                {row.get("rollout_id") for row in values}):
        failures.append("COMPACT_ORDER_OR_IDENTITY")
    return values


def audit(config: Path, run_dir: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    config = _inside(config, "config"); run_dir = _inside(run_dir, "run")
    result = _read(run_dir / "result.json")
    stage, _, cfg, preflight, tracked, model_result = primary.load(config)
    expected = primary.build_streams(stage, cfg, preflight, tracked)
    compact = _compact(run_dir, expected, failures)
    rollout_root = run_dir / "rollouts"
    actual_ids = sorted(path.name for path in rollout_root.iterdir() if path.is_dir())
    if actual_ids != sorted(str(row.get("rollout_id")) for row in compact):
        failures.append("ROLLOUT_DIRECTORY_SET")
    raw_rows, inventory_lines, inventory_bytes = rawio._raw_rows(
        run_dir, cfg, expected, compact, failures)
    digest = hashlib.sha256("".join(f"{line}\n" for line in sorted(inventory_lines)).encode()).hexdigest()
    if (digest != result.get("required_artifact_inventory_sha256")
            or len(inventory_lines) != result.get("required_artifact_files")
            or inventory_bytes != result.get("required_artifact_bytes")):
        failures.append("INVENTORY")
    compact_by_id = {row["rollout_id"]: row for row in compact}
    semantic = {row["rollout_id"]: i27._preissue_semantic_row(
        row, compact_by_id.get(row["rollout_id"], {})) for row in raw_rows}
    centered = semantic.get("fresh_baseline_transition_center")
    prefixes: list[dict[str, Any]] = []
    for frozen in expected[:len(compact)]:
        family = frozen["rollout_id"]
        if frozen["kind"] == "center_baseline":
            reference = tracked; count = 33
        else:
            reference = centered or {}; count = int(frozen["prefix_checkpoint_last_state"]) + 1
        prefixes.append(primary.z27.z6.prefix_check(
            semantic.get(family, {}), reference, count, count - 1,
            stage["semantic_artifacts"]))
    execution = bool(raw_rows and all(row.get("passed") for row in raw_rows))
    raw_ok = (len(inventory_lines) == 5 * sum(len(row.get("states", [])) for row in raw_rows)
              and not any(value.startswith("MISSING_ARTIFACT") for value in failures))
    prefix_ok = len(prefixes) == len(compact) and all(row.get("passed") for row in prefixes)
    calibration = (primary.model_metrics(raw_rows, centered, 36, "cal",
                                         model_result["model"], stage["model_gates"])
                   if centered is not None and len(raw_rows) >= 6 else None)
    replay = (primary.z27.z6.replay_check(semantic.get(
        "cal_issue36__q_z__plus_then_return"), semantic.get(
        "replay_cal_issue36__q_z__plus_then_return"), stage["semantic_artifacts"])
              if len(raw_rows) >= 6 else {"passed": False, "failures": ["NOT_RUN"]})
    tube = (primary.calibrated_tube(calibration, stage["model_gates"])
            if calibration and calibration.get("passed") and replay.get("passed") else None)
    blind = (primary.model_metrics(raw_rows, centered, 44, "blind",
                                   model_result["model"], stage["model_gates"])
             if centered is not None and len(raw_rows) == 10 else {"passed": False})
    containment = (primary.blind_containment(blind, tube) if tube is not None
                   else {"passed": False, "contained": 0, "total": 96})
    if not execution:
        route = stage["routes"]["execution_or_interface_fail"]
    elif not raw_ok:
        route = stage["routes"]["raw_integrity_fail"]
    elif not prefix_ok:
        route = stage["routes"]["prefix_mismatch"]
    elif not replay.get("passed"):
        route = stage["routes"]["replay_fail"]
    elif not calibration or not calibration.get("passed"):
        route = stage["routes"]["calibration_fail"]
    elif len(raw_rows) != 10 or not blind.get("passed") or not containment.get("passed"):
        route = stage["routes"]["blind_fail"]
    else:
        route = stage["routes"]["pass"]
    if result.get("prefix_checks") != prefixes:
        failures.append("PREFIX_RECOMPUTE")
    if result.get("calibration_metrics") != calibration:
        failures.append("CALIBRATION_RECOMPUTE")
    expected_tube = None if tube is None else tube.tolist()
    if result.get("calibrated_tube") != expected_tube:
        failures.append("TUBE_RECOMPUTE")
    if result.get("blind_metrics") != blind or result.get("blind_containment") != containment:
        failures.append("BLIND_RECOMPUTE")
    if result.get("replay_metrics") != replay:
        failures.append("REPLAY_RECOMPUTE")
    if result.get("route") != route or result.get("passed") != (route == stage["routes"]["pass"]):
        failures.append("ROUTE_OR_VERDICT")
    counters = {key: sum(int(row.get(key, 0)) for row in compact) for key in
                ("reset_calls", "advance_attempts", "plant_advance_gotsc_calls",
                 "verified_plant_advances")}
    for key, value in counters.items():
        if result.get(key) != value:
            failures.append(f"COUNTER:{key}")
    if (result.get("source_revision") != source_revision
            or result.get("stage_config_sha256") != primary.CONFIG_SHA256
            or result.get("models_fit_or_updated") != 0
            or result.get("future_feedback_records_read") != 0):
        failures.append("IDENTITY_OR_FORBIDDEN_WORK")
    return {"schema_version": SCHEMA, "source_revision": source_revision,
            "primary_sha256": hashlib.sha256((run_dir / "result.json").read_bytes()).hexdigest(),
            "audit_passed": not failures, "failures": failures,
            "recomputed_route": route, "reparsed_rollouts": len(raw_rows),
            "reparsed_states": sum(len(row.get("states", [])) for row in raw_rows),
            "reparsed_required_artifacts": len(inventory_lines),
            "reparsed_required_bytes": inventory_bytes,
            "recomputed_calibration_metrics": calibration,
            "recomputed_blind_metrics": blind,
            "recomputed_blind_containment": containment,
            "models_fit_or_updated": 0, "tsc_calls": counters["plant_advance_gotsc_calls"],
            "plant_advances": counters["verified_plant_advances"],
            "claim_boundary": stage["claim_boundary"]}


def write_new(path: Path, value: dict[str, Any]) -> None:
    output = _inside(path, "output")
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=primary.CONFIG)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        value = audit(args.config, args.run_dir, args.source_revision)
    except Exception as exc:
        value = {"schema_version": SCHEMA, "source_revision": args.source_revision,
                 "audit_passed": False,
                 "failures": [f"{type(exc).__name__}:{exc}"]}
    write_new(args.output, value)
    print(json.dumps(value, sort_keys=True, allow_nan=False))
    return 0 if value["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
