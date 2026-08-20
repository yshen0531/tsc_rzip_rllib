#!/usr/bin/env python3
"""Independent full-raw audit for the frozen ID-2Z27 campaign."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_id0_vector_tail import write_new  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2z9_late_root_branch_utility_support_independent as rawio  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2z27_dynamic_output_aligned_campaign as primary  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-id2z27-independent-raw-v1"


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


def compact_rows(run_dir: Path, expected: Sequence[dict[str, Any]],
                 failures: list[str]) -> list[dict[str, Any]]:
    excluded = {"result.json", "offline_preflight.json", "independent_raw_audit.json"}
    rows = [load_json(path) for path in sorted(run_dir.glob("*.json"))
            if path.name not in excluded]
    rows = [row for row in rows if "rollout_id" in row]
    order = {str(row["rollout_id"]): index for index, row in enumerate(expected)}
    rows.sort(key=lambda row: order.get(str(row.get("rollout_id")), 999))
    ids = [str(row.get("rollout_id")) for row in rows]
    expected_ids = [str(row["rollout_id"]) for row in expected]
    if ids != expected_ids[:len(ids)] or len(ids) != len(set(ids)):
        failures.append("COMPACT_ORDER_OR_IDENTITY")
    return rows


def _replay(left: dict[str, Any] | None, right: dict[str, Any] | None,
            semantic: Sequence[str]) -> dict[str, Any]:
    failures: list[str] = []
    if left is None or right is None or not left.get("passed") or not right.get("passed"):
        failures.append("REPLAY_INCOMPLETE")
    else:
        if len(left.get("states", [])) != len(right.get("states", [])):
            failures.append("REPLAY_STATE_COUNT")
        for index, (a, b) in enumerate(zip(left.get("states", []), right.get("states", []))):
            for key in ("time_ms", "r_geo_m", "z_geo_m", "r_mid_m", "ip_a",
                        "actual_current_decimal_a_tsc", "wire_current_a",
                        "active_command_card15_fields"):
                if a.get(key) != b.get(key):
                    failures.append(f"REPLAY_STATE:{index}:{key}")
            for name in semantic:
                if a.get("artifact_sha256", {}).get(name) != b.get("artifact_sha256", {}).get(name):
                    failures.append(f"REPLAY_ARTIFACT:{index}:{name}")
        if ([row.get("expected_card15_fields") for row in left.get("actions", [])]
                != [row.get("expected_card15_fields") for row in right.get("actions", [])]):
            failures.append("REPLAY_ACTIONS")
    return {"passed": not failures, "failures": list(dict.fromkeys(failures))}


def _geometry(vectors: Sequence[np.ndarray], count: int) -> dict[str, float]:
    if not vectors:
        return {"maximum_angular_gap_deg": 360.0,
                "weakest_best_projection_m": -1.0}
    angles = sorted((math.degrees(math.atan2(float(v[1]), float(v[0]))) + 360.0) % 360.0
                    for v in vectors)
    gap = max(angles[(index + 1) % len(angles)]
              + (360.0 if index == len(angles) - 1 else 0.0) - angles[index]
              for index in range(len(angles)))
    weak = min(max(float(np.dot(v, np.asarray([math.cos(angle), math.sin(angle)])))
                   for v in vectors)
               for angle in (2.0 * math.pi * index / count for index in range(count)))
    return {"maximum_angular_gap_deg": gap, "weakest_best_projection_m": weak}


def _preissue_semantic_row(raw: dict[str, Any], compact: dict[str, Any]) -> dict[str, Any]:
    """Restore only the preissue inputa hash overwritten by the outgoing issue.

    The retained state-k directory contains the post-record outgoing inputa for
    issue k.  The primary compact captured inputa before that rewrite.  Raw RZI,
    currents and every other artifact remain independently reparsed; rawio also
    checks the outgoing inputa fields against the frozen action stream.
    """
    value = {key: copy.deepcopy(item) for key, item in raw.items()
             if key not in ("states", "actions")}
    states: list[dict[str, Any]] = []
    saved_states = compact.get("states", [])
    for index, state in enumerate(raw.get("states", [])):
        item = copy.deepcopy(state)
        hashes = dict(item.get("artifact_sha256", {}))
        if index < len(saved_states):
            hashes["inputa"] = saved_states[index].get(
                "artifact_sha256", {}).get("inputa")
        item["artifact_sha256"] = hashes
        states.append(item)
    value["states"] = states
    value["actions"] = copy.deepcopy(raw.get("actions", []))
    return value


def scientific_metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    by_id = {str(row.get("family_id")): row for row in rows}
    baseline = by_id.get("baseline_transition_center")
    complete_baseline = bool(baseline and baseline.get("passed")
                             and len(baseline.get("states", [])) == 74)
    gates = stage["measurement_gates"]
    branches: list[dict[str, Any]] = []
    geometry: list[dict[str, Any]] = []
    all_signal = complete_baseline
    if complete_baseline:
        for phase in stage["phase_issue_steps"]:
            grouped: dict[int, list[np.ndarray]] = {4: [], 8: []}
            for axis in stage["output_aligned_axis_ids"]:
                for sign in stage["initial_signs"]:
                    family = f"issue{phase}__{axis}__{sign}_then_return"
                    row = by_id.get(family)
                    complete = bool(row and row.get("passed")
                                    and len(row.get("states", [])) == 74)
                    if not complete:
                        branches.append({"family_id": family, "complete": False,
                                         "passed": False})
                        all_signal = False
                        continue
                    values = {h: np.asarray([
                        float(row["states"][phase + h]["r_geo_m"])
                        - float(baseline["states"][phase + h]["r_geo_m"]),
                        float(row["states"][phase + h]["z_geo_m"])
                        - float(baseline["states"][phase + h]["z_geo_m"]),
                    ]) for h in (4, 8)}
                    norms = {h: float(np.linalg.norm(values[h])) for h in (4, 8)}
                    cosine = (float(np.dot(values[4], values[8])
                                    / (norms[4] * norms[8]))
                              if norms[4] and norms[8] else -1.0)
                    max_ip = max(abs(float(row["states"][index]["ip_a"])
                                     - float(baseline["states"][index]["ip_a"]))
                                 for index in range(phase + 1, 74))
                    passed = bool(
                        norms[4] >= gates["minimum_each_h4_rz_response_m"]
                        and norms[8] >= gates["minimum_each_h8_rz_response_m"]
                        and cosine >= gates["minimum_each_h4_h8_cosine"]
                        and max_ip <= gates["maximum_absolute_paired_ip_response_a"])
                    branches.append({"family_id": family, "complete": True,
                                     "h4_response_m": values[4].tolist(),
                                     "h8_response_m": values[8].tolist(),
                                     "h4_norm_m": norms[4], "h8_norm_m": norms[8],
                                     "h4_h8_cosine": cosine,
                                     "maximum_absolute_paired_ip_response_a": max_ip,
                                     "passed": passed})
                    grouped[4].append(values[4]); grouped[8].append(values[8])
                    all_signal = all_signal and passed
            for horizon in (4, 8):
                value = _geometry(grouped[horizon], gates["direction_grid_count"])
                value.update({"phase_issue": phase, "horizon": horizon,
                              "passed": bool(
                                  value["maximum_angular_gap_deg"]
                                  <= gates["maximum_each_phase_horizon_angular_gap_deg"]
                                  and value["weakest_best_projection_m"]
                                  >= gates["minimum_each_phase_horizon_weakest_best_projection_m"])})
                geometry.append(value)
                all_signal = all_signal and value["passed"]
    replay = _replay(by_id.get("issue32__q_z__plus_then_return"),
                     by_id.get("replay_issue32__q_z__plus_then_return"),
                     stage["semantic_artifacts"])
    capture: list[dict[str, Any]] = []
    if complete_baseline:
        source = baseline["states"][0]
        source_ip = abs(float(source["ip_a"]))
        for row in rows:
            if not row.get("passed") or len(row.get("states", [])) != 74:
                continue
            indices = gates["capture_terminal_state_indices"]
            distances = [math.hypot(
                float(row["states"][index]["r_geo_m"]) - float(source["r_geo_m"]),
                float(row["states"][index]["z_geo_m"]) - float(source["z_geo_m"]))
                         for index in indices]
            speeds = [math.hypot(
                float(row["states"][index]["r_geo_m"])
                - float(row["states"][index - 1]["r_geo_m"]),
                float(row["states"][index]["z_geo_m"])
                - float(row["states"][index - 1]["z_geo_m"])) / 0.001
                      for index in indices]
            ip = [abs(float(row["states"][index]["ip_a"]) - float(source["ip_a"]))
                  / source_ip for index in indices]
            capture.append({"family_id": row["family_id"],
                            "maximum_distance_m": max(distances),
                            "maximum_speed_m_per_s": max(speeds),
                            "maximum_ip_fraction": max(ip),
                            "captured": bool(
                                max(distances) <= gates["capture_distance_m"]
                                and max(speeds) <= gates["capture_speed_m_per_s"]
                                and max(ip) <= gates["capture_ip_fraction"])})
    return {"baseline_complete": complete_baseline, "branch_metrics": branches,
            "positive_span_metrics": geometry, "capture_diagnostics": capture,
            "replay_metrics": replay,
            "passed": bool(all_signal and len(branches) == 8 and replay["passed"])}


def audit(stage_path: Path, run_dir: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    stage_path = inside(stage_path, "config")
    run_dir = inside(run_dir, "run")
    result_path = run_dir / "result.json"
    result = load_json(result_path)
    try:
        stage, _, cfg, preflight, tracked = primary.load(stage_path)
        expected = primary.build_streams(stage, cfg, preflight, tracked)
    except Exception as exc:
        failures.append(f"STAGE_LOAD:{type(exc).__name__}:{exc}")
        stage, cfg, tracked, expected = load_json(stage_path), None, {}, []
    compact = compact_rows(run_dir, expected, failures)
    for row in compact:
        if row.get("schema_version") != primary.SCHEMA or row.get("source_revision") != source_revision:
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
        raw_rows, inventory_lines, inventory_bytes = rawio._raw_rows(
            run_dir, cfg, expected, compact, failures)
    digest = hashlib.sha256(
        "".join(f"{line}\n" for line in sorted(inventory_lines)).encode()).hexdigest()
    if digest != result.get("required_artifact_inventory_sha256"):
        failures.append("INVENTORY_SHA256")
    if (len(inventory_lines) != result.get("required_artifact_files")
            or inventory_bytes != result.get("required_artifact_bytes")):
        failures.append("INVENTORY_COUNT_OR_BYTES")
    raw_by_id = {str(row.get("rollout_id")): row for row in raw_rows}
    compact_by_id = {str(row.get("rollout_id")): row for row in compact}
    semantic_by_id = {
        family: _preissue_semantic_row(row, compact_by_id.get(family, {}))
        for family, row in raw_by_id.items()
    }
    centered = semantic_by_id.get("baseline_transition_center")
    prefixes: list[dict[str, Any]] = []
    for frozen in expected[:len(compact)]:
        family = str(frozen["rollout_id"])
        kind = str(frozen["kind"])
        if kind in ("center_baseline", "full_f_diagnostic"):
            reference = tracked
            state_count = 33
        else:
            reference = centered or {}
            state_count = int(frozen["prefix_checkpoint_last_state"]) + 1
        prefixes.append(primary.z6.prefix_check(
            semantic_by_id.get(family, {}), reference, state_count, state_count - 1,
            stage["semantic_artifacts"]))
    execution = bool(raw_rows and all(row.get("passed") for row in raw_rows))
    expected_files = 5 * sum(len(row.get("states", [])) for row in raw_rows)
    raw_ok = bool(len(inventory_lines) == expected_files
                  and not any(value.startswith("MISSING_ARTIFACT") for value in failures))
    prefix_ok = bool(len(prefixes) == len(compact)
                     and all(row.get("passed") for row in prefixes))
    complete = sum(bool(row.get("passed") and len(row.get("states", [])) == 74)
                   for row in raw_rows)
    scientific = scientific_metrics(raw_rows, stage)
    if not execution:
        route = stage["routes"]["execution_or_interface_fail"]
    elif not raw_ok:
        route = stage["routes"]["raw_integrity_fail"]
    elif not prefix_ok:
        route = stage["routes"]["prefix_mismatch"]
    elif not scientific["replay_metrics"]["passed"]:
        route = stage["routes"]["replay_fail"]
    elif complete != 11 or not scientific["passed"]:
        route = stage["routes"]["signal_fail"]
    else:
        route = stage["routes"]["data_pass"]
    if result.get("prefix_checks") != prefixes:
        failures.append("RECOMPUTE_PREFIX_CHECKS")
    if result.get("scientific_metrics") != scientific:
        failures.append("RECOMPUTE_SCIENTIFIC_METRICS")
    if result.get("route") != route or result.get("passed") != (
            route == stage["routes"]["data_pass"]):
        failures.append("PRIMARY_ROUTE_OR_VERDICT")
    counters = {key: sum(int(row.get(key, 0)) for row in compact) for key in
                ("reset_calls", "advance_attempts", "plant_advance_gotsc_calls",
                 "verified_plant_advances")}
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
            or result.get("stage_config_sha256") != primary.CONFIG_SHA256
            or result.get("rollouts_started") != len(compact)
            or result.get("complete_rollouts") != complete
            or result.get("models_fit_or_updated") != 0
            or result.get("calibration_or_holdout_records_read") != 0):
        failures.append("RESULT_IDENTITY_COUNTS_OR_DATA_ROLE")
    failures = list(dict.fromkeys(failures))
    return {"schema_version": SCHEMA, "source_revision": source_revision,
            "stage_config_sha256": primary.CONFIG_SHA256,
            "primary_sha256": primary.io.sha256(result_path),
            "audit_passed": not failures, "failures": failures,
            "primary_passed": result.get("passed"), "primary_route": result.get("route"),
            "recomputed_route": route, "recomputed_scientific_metrics": scientific,
            "recomputed_prefix_checks": prefixes,
            "recomputed_required_artifact_files": len(inventory_lines),
            "recomputed_required_artifact_bytes": inventory_bytes,
            "recomputed_required_artifact_inventory_sha256": digest,
            "raw_states_reparsed": sum(len(row.get("states", [])) for row in raw_rows),
            "raw_rollouts_reparsed": len(raw_rows), **counters,
            "new_tsc_or_plant_advances": 0, "models_fit_or_updated": 0,
            "calibration_or_holdout_records_read": 0,
            "claim_boundary": "Independent full-raw audit of finite ID2Z27 D0 only."}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-config", type=Path, default=primary.CONFIG)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    value = audit(args.stage_config, args.run_dir, args.source_revision)
    output = args.output or args.run_dir / "independent_raw_audit.json"
    write_new(inside(output, "audit output"), value)
    print(json.dumps(value, indent=2, sort_keys=True, allow_nan=False))
    return 0 if value["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
