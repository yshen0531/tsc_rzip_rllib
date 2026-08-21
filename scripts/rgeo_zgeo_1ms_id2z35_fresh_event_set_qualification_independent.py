#!/usr/bin/env python3
"""Independent full-raw audit for ID2Z35."""

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

from scripts import rgeo_zgeo_1ms_id2z35_fresh_event_set_qualification as primary  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2z27_dynamic_output_aligned_campaign_independent as i27  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2z9_late_root_branch_utility_support_independent as rawio  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-id2z35-fresh-event-set-qualification-independent-v1"
KEYS = ("r_geo_m", "z_geo_m", "ip_a")


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(primary._inside(path, "audit JSON").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON object required")
    return value


def _compact(run_dir: Path, expected: Sequence[dict[str, Any]], failures: list[str]):
    excluded = {"result.json", "offline_preflight.json", "independent_raw_audit.json"}
    rows = [_read(path) for path in sorted(run_dir.glob("*.json")) if path.name not in excluded]
    rows = [row for row in rows if "rollout_id" in row]
    order = {row["rollout_id"]: index for index, row in enumerate(expected)}
    rows.sort(key=lambda row: order.get(row.get("rollout_id"), 999))
    if [row.get("rollout_id") for row in rows] != [row["rollout_id"] for row in expected[:len(rows)]]:
        failures.append("COMPACT_ORDER_OR_IDENTITY")
    return rows


def _phase_metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any],
                   model: dict[str, Any], role: str,
                   calibrated: dict[str, float] | None = None) -> dict[str, Any]:
    phase = int(stage[f"{role}_phase_issue"])
    prefix = "cal52" if role == "calibration" else "blind54"
    by_id = {row["family_id"]: row for row in rows}
    baseline = by_id.get("baseline_transition_center")
    complete = bool(baseline and baseline.get("passed") and len(baseline.get("states", [])) == 74)
    contract = stage["qualification"]
    event_key = (contract["event_axis_sign"], int(contract["event_effect_age"]))
    event = next(row for row in model["event_sets"]
                 if (row["axis_sign"], int(row["effect_age"])) == event_key)
    event_center = np.asarray(event["center"])
    event_half = np.asarray(event["half_width"])
    maximum = np.zeros(3)
    event_total = 0
    event_inside = 0
    all_total = 0
    all_inside = 0
    details: list[dict[str, Any]] = []
    for axis in stage["output_aligned_axis_ids"]:
        for sign in stage["initial_signs"]:
            family = f"{prefix}__{axis}__{sign}_then_return"
            row = by_id.get(family)
            good = bool(row and row.get("passed") and len(row.get("states", [])) == 74)
            complete = complete and good
            if not good:
                details.append({"family_id": family, "complete": False})
                continue
            key = f"{axis}:{sign}"
            center = np.asarray(model["point_centers"][key])
            local = np.zeros(3)
            local_event = 0
            for offset in range(1, 18):
                observed = np.asarray([float(row["states"][phase + offset][name])
                                       - float(baseline["states"][phase + offset][name])
                                       for name in KEYS])
                all_total += 1
                if (key, offset) == event_key:
                    inside = bool(np.all(np.abs(observed - event_center) <= event_half + 1e-15))
                    event_total += 1; event_inside += int(inside); all_inside += int(inside)
                    local_event += int(inside)
                else:
                    error = np.abs(observed - center[offset - 1])
                    maximum = np.maximum(maximum, error); local = np.maximum(local, error)
                    if calibrated is not None:
                        all_inside += int(bool(np.all(error <= np.asarray(
                            [calibrated[name] for name in KEYS]) + 1e-15)))
            details.append({"family_id": family, "complete": True,
                            "event_cells_contained": local_event,
                            "maximum_non_event_absolute_error": dict(zip(KEYS, local.tolist()))})
    event_fraction = event_inside / event_total if event_total else 0.0
    result: dict[str, Any] = {"role": role, "phase_issue": phase, "complete": complete,
                              "branch_metrics": details,
                              "maximum_non_event_absolute_error": dict(zip(KEYS, maximum.tolist())),
                              "event_cell_observations": event_total,
                              "event_containment_fraction": event_fraction}
    if role == "calibration":
        caps = contract["calibration_maximum_non_event_error"]
        dev = model["candidate_b"]["metrics"]["maximum_non_event_absolute_error"]
        floor = contract["calibrated_half_width_floor"]
        multiplier = float(contract["calibrated_non_event_multiplier"])
        half = {name: multiplier * max(float(dev[name]), float(maximum[index]))
                + float(floor[name]) for index, name in enumerate(KEYS)}
        half_caps = contract["calibrated_half_width_cap"]
        passed = bool(complete and event_fraction >= contract["required_event_containment_fraction"]
                      and all(maximum[index] <= float(caps[name]) for index, name in enumerate(KEYS))
                      and all(half[name] <= float(half_caps[name]) for name in KEYS))
        result.update({"calibrated_non_event_half_width": half, "passed": passed})
    else:
        fraction = all_inside / all_total if all_total else 0.0
        result.update({"all_cell_observations": all_total,
                       "all_cell_containment_fraction": fraction,
                       "calibrated_non_event_half_width": calibrated,
                       "passed": bool(complete
                                      and fraction >= contract["required_blind_all_cell_containment_fraction"]
                                      and event_fraction >= contract["required_event_containment_fraction"])})
    return result


def audit(config: Path, run_dir: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    run_dir = primary._inside(run_dir, "run")
    result = _read(run_dir / "result.json")
    stage, _, cfg, preflight, tracked, model = primary.load(config)
    expected = primary.build_streams(stage, cfg, preflight, tracked)
    compact = _compact(run_dir, expected, failures)
    rollout_root = run_dir / "rollouts"
    actual = sorted(path.name for path in rollout_root.iterdir() if path.is_dir())
    if actual != sorted(str(row.get("rollout_id")) for row in compact):
        failures.append("ROLLOUT_DIRECTORY_SET")
    raw_rows, inventory_lines, inventory_bytes = rawio._raw_rows(
        run_dir, cfg, expected, compact, failures)
    digest = hashlib.sha256("".join(f"{line}\n" for line in sorted(inventory_lines)).encode()).hexdigest()
    if (digest != result.get("required_artifact_inventory_sha256")
            or len(inventory_lines) != result.get("required_artifact_files")
            or inventory_bytes != result.get("required_artifact_bytes")):
        failures.append("INVENTORY")
    compact_by = {row["rollout_id"]: row for row in compact}
    semantic = {row["rollout_id"]: i27._preissue_semantic_row(
        row, compact_by.get(row["rollout_id"], {})) for row in raw_rows}
    centered = semantic.get("baseline_transition_center")
    prefixes = []
    for frozen in expected[:len(compact)]:
        family = frozen["rollout_id"]
        if frozen["kind"] == "center_baseline":
            reference = tracked; count = 33
        else:
            reference = centered or {}; count = int(frozen["prefix_checkpoint_last_state"]) + 1
        prefixes.append(primary.z33.z32.z31.z30.z27.z6.prefix_check(
            semantic.get(family, {}), reference, count, count - 1, stage["semantic_artifacts"]))
    execution = bool(raw_rows and all(row.get("passed") for row in raw_rows))
    raw_ok = (len(inventory_lines) == 5 * sum(len(row.get("states", [])) for row in raw_rows)
              and not any(item.startswith("MISSING_ARTIFACT") for item in failures))
    prefix_ok = len(prefixes) == len(compact) and all(row.get("passed") for row in prefixes)
    by_id = {row["family_id"]: row for row in raw_rows}
    replay = i27._replay(by_id.get(stage["replay_source_family_id"]),
                         by_id.get(stage["replay_family_id"]), stage["semantic_artifacts"])
    calibration = _phase_metrics(raw_rows, stage, model, "calibration")
    blind_opened = bool(result.get("blind_opened"))
    blind = (_phase_metrics(raw_rows, stage, model, "blind",
                            calibration.get("calibrated_non_event_half_width"))
             if blind_opened else {"role": "blind", "opened": False, "passed": False})
    if not execution:
        route = stage["routes"]["execution_or_interface_fail"]
    elif not raw_ok:
        route = stage["routes"]["raw_integrity_fail"]
    elif not prefix_ok:
        route = stage["routes"]["prefix_mismatch"]
    elif not replay["passed"]:
        route = stage["routes"]["replay_fail"]
    elif not calibration["passed"]:
        route = stage["routes"]["calibration_fail"]
    elif not blind_opened or len(raw_rows) != 10 or not blind["passed"]:
        route = stage["routes"]["blind_fail"]
    else:
        route = stage["routes"]["pass"]
    if result.get("prefix_checks") != prefixes:
        failures.append("PREFIX_RECOMPUTE")
    if result.get("calibration_replay_metrics") != replay:
        failures.append("REPLAY_RECOMPUTE")
    if result.get("calibration_metrics") != calibration:
        failures.append("CALIBRATION_RECOMPUTE")
    if result.get("blind_metrics") != blind:
        failures.append("BLIND_RECOMPUTE")
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
            or result.get("model_payload_sha256") != model["payload_sha256"]):
        failures.append("IDENTITY_OR_FORBIDDEN_WORK")
    return {"schema_version": SCHEMA, "source_revision": source_revision,
            "primary_sha256": hashlib.sha256((run_dir / "result.json").read_bytes()).hexdigest(),
            "audit_passed": not failures, "failures": failures,
            "recomputed_route": route, "reparsed_rollouts": len(raw_rows),
            "reparsed_states": sum(len(row.get("states", [])) for row in raw_rows),
            "reparsed_required_artifacts": len(inventory_lines),
            "reparsed_required_bytes": inventory_bytes,
            "recomputed_calibration_metrics": calibration,
            "recomputed_blind_metrics": blind, "models_fit_or_updated": 0,
            "tsc_calls": counters["plant_advance_gotsc_calls"],
            "plant_advances": counters["verified_plant_advances"],
            "claim_boundary": stage["claim_boundary"]}


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
                 "audit_passed": False, "failures": [f"{type(exc).__name__}:{exc}"]}
    primary.io.write_new(args.output, value)
    print(json.dumps(value, sort_keys=True, allow_nan=False))
    return 0 if value["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
