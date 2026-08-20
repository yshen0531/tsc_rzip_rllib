#!/usr/bin/env python3
"""Independent full-raw audit for frozen ID-2Z23."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_id0_vector_tail import write_new  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2z9_late_root_branch_utility_support_independent as z9i  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2z23_moving_nominal_discrete_vertex_campaign as primary  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-id2z23-independent-raw-v1"


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


def _geometry(vectors: Sequence[np.ndarray], count: int) -> dict[str, float]:
    angles = sorted((math.degrees(math.atan2(float(v[1]), float(v[0]))) + 360.0) % 360.0
                    for v in vectors)
    gap = max(angles[(index + 1) % len(angles)]
              + (360.0 if index == len(angles) - 1 else 0.0) - angles[index]
              for index in range(len(angles)))
    weak = min(max(float(np.dot(vector, np.asarray([math.cos(angle), math.sin(angle)])))
                   for vector in vectors)
               for angle in (2.0 * math.pi * index / count for index in range(count)))
    return {"maximum_angular_gap_deg": gap, "weakest_best_projection_m": weak}


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
                if (a.get("artifact_sha256", {}).get(name)
                        != b.get("artifact_sha256", {}).get(name)):
                    failures.append(f"REPLAY_ARTIFACT:{index}:{name}")
        if ([row.get("expected_card15_fields") for row in left.get("actions", [])]
                != [row.get("expected_card15_fields") for row in right.get("actions", [])]):
            failures.append("REPLAY_ACTIONS")
    return {"passed": not failures, "failures": list(dict.fromkeys(failures))}


def scientific_metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    gates = stage["measurement_gates"]
    by_id = {str(row.get("family_id")): row for row in rows}
    baseline = by_id.get("baseline_full_f")
    baseline_complete = bool(baseline and baseline.get("passed")
                             and len(baseline.get("states", [])) == 66)
    all_passed = baseline_complete
    phase_values: list[dict[str, Any]] = []
    if baseline_complete:
        for phase in stage["phase_issue_steps"]:
            arms: list[dict[str, Any]] = []
            grouped: dict[int, list[np.ndarray]] = {4: [], 8: []}
            for vertex in stage["selected_vertex_ids"]:
                row = by_id.get(f"issue{phase}__{vertex}")
                complete = bool(row and row.get("passed")
                                and len(row.get("states", [])) == 66)
                if not complete:
                    arms.append({"vertex_id": vertex, "complete": False, "passed": False})
                    all_passed = False
                    continue
                vectors = {horizon: np.asarray([
                    float(row["states"][phase + horizon]["r_geo_m"])
                    - float(baseline["states"][phase + horizon]["r_geo_m"]),
                    float(row["states"][phase + horizon]["z_geo_m"])
                    - float(baseline["states"][phase + horizon]["z_geo_m"]),
                ]) for horizon in (4, 8)}
                norms = {horizon: float(np.linalg.norm(vector))
                         for horizon, vector in vectors.items()}
                cosine = (float(np.dot(vectors[4], vectors[8]) / (norms[4] * norms[8]))
                          if norms[4] and norms[8] else -1.0)
                max_ip = max(abs(float(row["states"][index]["ip_a"])
                                 - float(baseline["states"][index]["ip_a"]))
                             for index in range(phase + 1, 66))
                passed = bool(
                    norms[4] >= float(gates["minimum_each_h4_rz_response_m"])
                    and norms[8] >= float(gates["minimum_each_h8_rz_response_m"])
                    and cosine >= float(gates["minimum_each_h4_h8_cosine"])
                    and max_ip <= float(gates["maximum_absolute_paired_ip_response_a"]))
                arms.append({"vertex_id": vertex, "complete": True,
                             "h4_response_m": vectors[4].tolist(),
                             "h8_response_m": vectors[8].tolist(),
                             "h4_norm_m": norms[4], "h8_norm_m": norms[8],
                             "h4_h8_cosine": cosine,
                             "maximum_absolute_paired_ip_response_a": max_ip,
                             "passed": passed})
                grouped[4].append(vectors[4]); grouped[8].append(vectors[8])
                all_passed = all_passed and passed
            geometry: list[dict[str, Any]] = []
            for horizon in (4, 8):
                value = (_geometry(grouped[horizon], int(gates["direction_grid_count"]))
                         if len(grouped[horizon]) == 4 else
                         {"maximum_angular_gap_deg": math.inf,
                          "weakest_best_projection_m": -math.inf})
                value.update({"horizon": horizon, "passed": bool(
                    value["maximum_angular_gap_deg"]
                    <= float(gates["maximum_each_phase_horizon_angular_gap_deg"])
                    and value["weakest_best_projection_m"]
                    >= float(gates["minimum_each_phase_horizon_weakest_best_projection_m"]))})
                all_passed = all_passed and value["passed"]
                geometry.append(value)
            phase_values.append({"phase_issue": phase, "arm_metrics": arms,
                                 "geometry": geometry,
                                 "passed": all(item.get("passed") for item in arms)
                                           and all(item["passed"] for item in geometry)})
    replay = _replay(by_id.get("issue24__p05_plus4"),
                     by_id.get("replay_issue24__p05_plus4"),
                     stage["semantic_artifacts"])
    all_passed = all_passed and replay["passed"] and len(phase_values) == 2
    capture: list[dict[str, Any]] = []
    if baseline_complete:
        source = baseline["states"][0]
        source_ip = abs(float(source["ip_a"]))
        for row in rows:
            if not row.get("passed") or len(row.get("states", [])) != 66:
                continue
            terminal = [int(value) for value in gates["capture_terminal_state_indices"]]
            distance = [math.hypot(float(row["states"][index]["r_geo_m"])
                                   - float(source["r_geo_m"]),
                                   float(row["states"][index]["z_geo_m"])
                                   - float(source["z_geo_m"])) for index in terminal]
            speed = [math.hypot(float(row["states"][index]["r_geo_m"])
                                - float(row["states"][index - 1]["r_geo_m"]),
                                float(row["states"][index]["z_geo_m"])
                                - float(row["states"][index - 1]["z_geo_m"])) / .001
                     for index in terminal]
            ip = [abs(float(row["states"][index]["ip_a"]) - float(source["ip_a"]))
                  / source_ip for index in terminal]
            capture.append({"family_id": row["family_id"],
                            "maximum_distance_m": max(distance),
                            "maximum_speed_m_per_s": max(speed),
                            "maximum_ip_fraction": max(ip),
                            "captured": bool(max(distance) <= float(gates["capture_distance_m"])
                                             and max(speed) <= float(gates["capture_speed_m_per_s"])
                                             and max(ip) <= float(gates["capture_ip_fraction"]))})
    return {"phase_metrics": phase_values, "replay_metrics": replay,
            "capture_diagnostics": capture, "passed": bool(all_passed)}


def audit(stage_path: Path, run_dir: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    stage_path, run_dir = inside(stage_path, "config"), inside(run_dir, "run")
    result = load_json(run_dir / "result.json")
    try:
        stage, _, cfg, targets, parent, baseline = primary.load(stage_path)
        expected = primary.build_streams(stage, cfg, targets, parent)
    except Exception as exc:
        failures.append(f"STAGE_LOAD:{type(exc).__name__}:{exc}")
        stage, cfg, baseline, expected = load_json(stage_path), None, {}, []
    compact = compact_rows(run_dir, expected, failures)
    for row in compact:
        if (row.get("schema_version") != primary.SCHEMA
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
        raw_rows, inventory_lines, inventory_bytes = z9i._raw_rows(
            run_dir, cfg, expected, compact, failures)
    digest = hashlib.sha256(
        "".join(f"{line}\n" for line in sorted(inventory_lines)).encode()).hexdigest()
    if digest != result.get("required_artifact_inventory_sha256"):
        failures.append("INVENTORY_SHA256")
    if (len(inventory_lines) != result.get("required_artifact_files")
            or inventory_bytes != result.get("required_artifact_bytes")):
        failures.append("INVENTORY_COUNT_OR_BYTES")
    compact_by_id = {str(row.get("rollout_id")): row for row in compact}
    prefix_values = []
    for frozen in expected[:len(compact)]:
        family = str(frozen["rollout_id"])
        decision = int(frozen["prefix_checkpoint_last_state"])
        prefix_values.append(primary.z6.prefix_check(
            compact_by_id.get(family, {}), baseline, decision + 1, decision,
            stage["semantic_artifacts"]))
    execution = bool(raw_rows and all(row.get("passed") for row in raw_rows))
    raw_ok = bool(len(inventory_lines) == 5 * sum(len(row.get("states", []))
                                                 for row in raw_rows)
                  and not any(item.startswith("MISSING_ARTIFACT") for item in failures))
    prefix_ok = bool(len(prefix_values) == len(compact)
                     and all(row.get("passed") for row in prefix_values))
    complete = sum(bool(row.get("passed") and len(row.get("states", [])) == 66)
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
    elif complete != 10 or not scientific["passed"]:
        route = stage["routes"]["geometry_fail"]
    else:
        route = stage["routes"]["data_pass"]
    if result.get("prefix_checks") != prefix_values:
        failures.append("RECOMPUTE_PREFIX_CHECKS")
    if result.get("scientific_metrics") != scientific:
        failures.append("RECOMPUTE_SCIENTIFIC_METRICS")
    if (result.get("route") != route
            or result.get("passed") != (route == stage["routes"]["data_pass"])):
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
            "primary_sha256": primary.io.sha256(run_dir / "result.json"),
            "audit_passed": not failures, "failures": failures,
            "primary_passed": result.get("passed"), "primary_route": result.get("route"),
            "recomputed_route": route, "recomputed_scientific_metrics": scientific,
            "recomputed_prefix_checks": prefix_values,
            "recomputed_required_artifact_files": len(inventory_lines),
            "recomputed_required_artifact_bytes": inventory_bytes,
            "recomputed_required_artifact_inventory_sha256": digest,
            "raw_states_reparsed": sum(len(row.get("states", [])) for row in raw_rows),
            "raw_rollouts_reparsed": len(raw_rows), **counters,
            "new_tsc_or_plant_advances": 0, "models_fit_or_updated": 0,
            "calibration_or_holdout_records_read": 0,
            "claim_boundary": "Independent full-raw audit of finite ID2Z23 only."}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-config", type=Path, default=primary.CONFIG)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    value = audit(args.stage_config, args.run_dir, args.source_revision)
    write_new(inside(args.output, "audit output"), value)
    print(json.dumps(value, indent=2, sort_keys=True, allow_nan=False))
    return 0 if value["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
