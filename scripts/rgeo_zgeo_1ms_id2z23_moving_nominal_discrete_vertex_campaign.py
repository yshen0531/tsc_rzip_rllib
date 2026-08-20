#!/usr/bin/env python3
"""Run the frozen ID-2Z23 moving-nominal discrete-vertex campaign."""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from pathlib import Path
from typing import Any, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_id2z18_full_horizon_token_development as z18

z17, z6, z7, io = z18.z17, z18.z6, z18.z7, z18.io
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z23_moving_nominal_discrete_vertex_campaign.json"
CONFIG_SHA256 = "b583b421a1ace59cbbcd37d04ffdb38436bae477f9c7906d691b6e74bab42561"
SCHEMA = "rgeo-zgeo-1ms-id2z23-moving-nominal-discrete-vertex-campaign-result-v1"
OFFLINE_SCHEMA = "rgeo-zgeo-1ms-id2z23-moving-nominal-discrete-vertex-campaign-offline-v1"


def _error(message: str) -> Exception:
    return z6._error(f"ID2Z23: {message}")


def _load_json(path: Path) -> dict[str, Any]:
    return z18.load_json(z18.inside(path, "ID2Z23 JSON"))


def _require(stage: dict[str, Any]) -> None:
    if io.sha256(CONFIG) != CONFIG_SHA256 or stage != _load_json(CONFIG):
        raise _error("frozen config changed")
    exact = {
        "stage": "ID-2Z23", "takeover_time_ms": 1100, "control_period_ms": 1,
        "common_horizon_steps": 65, "common_terminal_state_index": 65,
        "full_f_last_issue": 47, "held_tail_first_issue": 48,
        "held_tail_last_issue": 64,
        "selected_vertex_ids": ["p00_minus4", "p05_minus4", "p05_plus4", "p06_plus4"],
        "phase_issue_steps": [24, 32], "replacement_duration_issues": 4,
        "maximum_rollouts": 10, "maximum_reset_calls": 10,
        "maximum_advance_attempts": 650, "maximum_gotsc_calls": 650,
        "maximum_verified_plant_advances": 650, "maximum_retained_states": 660,
        "required_artifact_files_if_all_complete": 3300,
        "retry_after_any_advance_attempt": "forbidden", "models_fit_or_updated": 0,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise _error(f"frozen field mismatch: {key}")
    specs = stage.get("development_specs", [])
    replay = stage.get("replay_specs", [])
    if len(specs) != 9 or len(replay) != 1:
        raise _error("rollout matrix size changed")
    expected = ["baseline_full_f"] + [f"issue{issue}__{arm}" for issue in (24, 32)
                                      for arm in exact["selected_vertex_ids"]]
    if [row.get("family_id") for row in specs] != expected:
        raise _error("development rollout order changed")
    if any(row.get("fit_weight") != 1 for row in specs):
        raise _error("development fit weight changed")
    if replay != [{"family_id": "replay_issue24__p05_plus4",
                   "source_family_id": "issue24__p05_plus4", "fit_weight": 0}]:
        raise _error("replay identity changed")
    if stage.get("action_semantics") != {
        "exact_card15_vertices": True, "continuous_basis_inversion": False,
        "add_then_clip": False, "maximum_per_coil_issue_delta_a": 0.3,
        "full_0p3_a_allowed": True, "issue_to_effect_state_offset": 1,
        "software_queue_added": False,
        "legacy_runner_clipping_may_be_relied_on": False,
        "future_actual_current": "forbidden",
        "candidate_replaces_f_for_four_issues": True,
        "resume_f_from_attained_target": True,
    }:
        raise _error("action semantics changed")


def load(path: Path = CONFIG) -> tuple[dict[str, Any], dict[str, Any], Any,
                                       dict[str, Any], dict[str, Any], dict[str, Any]]:
    path = z18.inside(path, "ID2Z23 config")
    if path != CONFIG.resolve():
        raise _error("alternate config forbidden")
    stage = _load_json(path); _require(stage)
    evidence: dict[str, dict[str, Any]] = {}
    for name, spec in stage["evidence"].items():
        item = z18.inside(ROOT / spec["path"], name)
        if io.sha256(item) != spec["sha256"]:
            raise _error(f"evidence mismatch: {name}")
        evidence[name] = _load_json(item) if item.suffix == ".json" else {}
    if (evidence["id2z22_result"].get("route")
            != stage["evidence"]["id2z22_result"]["required_route"]
            or evidence["id2z22_result"].get("passed") is not True
            or evidence["id2z22_independent"].get("audit_passed") is not True):
        raise _error("ID2Z22 prerequisite mismatch")
    _, base_runtime, cfg, targets, parent, _ = z18.load(z18.CONFIG)
    baseline = evidence["id2z18_baseline_full_f"]
    if len(baseline.get("states", [])) != 66 or len(baseline.get("actions", [])) != 65:
        raise _error("full-F compact incomplete")
    return stage, base_runtime, cfg, targets, parent, baseline


def _build_stream(stage: dict[str, Any], cfg: Any, targets: dict[str, Any],
                  parent: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    family = str(spec["family_id"])
    decision = spec.get("phase_issue")
    arm = spec.get("vertex_id")
    horizon = int(stage["common_horizon_steps"])
    prefix = 16
    sequence = list(parent["targets"][:prefix])
    virtual_rows = [z17._extended(row["probe_virtual_action"])
                    for row in parent["actions"][:prefix]]
    current, virtual, q0 = sequence[-1], list(virtual_rows[-1]), targets["q0"]
    for issue in range(prefix, horizon):
        if decision is not None and int(decision) <= issue < int(decision) + 4:
            current, virtual = z17._apply_arm(
                current, virtual, str(arm), q0, targets, cfg,
                f"id2z23.{family}.{issue}.{arm}")
        elif issue <= int(stage["full_f_last_issue"]):
            current, virtual = z18._apply_token(
                current, virtual, "F", q0, targets, cfg,
                f"id2z23.{family}.{issue}.F")
        else:
            current, virtual = z18._apply_token(
                current, virtual, "H", q0, targets, cfg,
                f"id2z23.{family}.{issue}.H")
        sequence.append(current); virtual_rows.append(list(virtual))
    actions = z17.z6.z5.z3.z1.c1._actions(sequence, cfg, family, virtual_rows)
    checkpoint = 48 if decision is None else int(decision)
    return {"rollout_id": family, "candidate_id": family, "family_id": family,
            "phase_issue": decision, "vertex_id": arm,
            "fit_weight": int(spec["fit_weight"]), "data_role": "development",
            "round_index": 0, "round_id": "moving_nominal_discrete_vertex",
            "cell_id": family, "cell_kind": "moving_nominal_vertex_history",
            "context_id": f"canonical_full_f_state{checkpoint}",
            "coordinate": "exact_discrete_card15_vertex_replacement4_resume_f",
            "probe_issue_step": decision, "probe_duration_issues": 0 if decision is None else 4,
            "prefix_checkpoint_last_state": checkpoint,
            "non_nominal_issue_steps": [] if decision is None else list(range(int(decision), int(decision) + 4)),
            "targets": sequence, "actions": actions}


def _replay(source: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(source)
    value.update({"rollout_id": spec["family_id"], "candidate_id": spec["family_id"],
                  "family_id": spec["family_id"], "source_family_id": spec["source_family_id"],
                  "fit_weight": 0, "data_role": "replay", "cell_id": spec["family_id"],
                  "cell_kind": "moving_nominal_vertex_exact_replay"})
    return value


def build_streams(stage: dict[str, Any], cfg: Any, targets: dict[str, Any],
                  parent: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [_build_stream(stage, cfg, targets, parent, spec)
            for spec in stage["development_specs"]]
    by_id = {row["family_id"]: row for row in rows}
    rows.extend(_replay(by_id[spec["source_family_id"]], spec)
                for spec in stage["replay_specs"])
    return rows


def _runtime(stage: dict[str, Any], base: dict[str, Any], stream: dict[str, Any]) -> dict[str, Any]:
    value = dict(base); value.update(stage)
    value["horizon_steps"] = int(stage["common_horizon_steps"])
    decision = int(stream["prefix_checkpoint_last_state"])
    value["decision_state_index"] = decision
    value["rounds"] = [{"round_index": 0, "decision_state_index": decision}]
    value["prefix_gates"] = {"checkpoint_indices": list(range(decision + 1))}
    value["empirical_exploration"] = dict(stage["empirical_exploration"])
    value["empirical_exploration"]["inner_novel_issue_clearance"] = dict(
        stage["empirical_exploration"]["simulator_development_preissue_clearance"])
    return value


def validate_stream(stream: dict[str, Any], stage: dict[str, Any], cfg: Any) -> dict[str, Any]:
    failures: list[str] = []
    if len(stream["actions"]) != 65 or len(stream["targets"]) != 65:
        failures.append("STREAM_DIMENSIONS")
    for issue, action in enumerate(stream["actions"]):
        if (int(action["issue_step"]) != issue
                or int(action["effect_state_index"]) != issue + 1
                or float(action["maximum_issued_delta_a"]) > .3000000001):
            failures.append(f"ACTION:{issue}")
    headroom = float(z6._headroom(stream["targets"], cfg))
    if headroom < -1e-9:
        failures.append("ABSOLUTE_CURRENT_LIMIT")
    return {"rollout_id": stream["rollout_id"], "passed": not failures,
            "minimum_absolute_current_headroom_a": headroom, "failures": failures}


def _execute_row(cfg: Any, stage: dict[str, Any], base_runtime: dict[str, Any],
                 stream: dict[str, Any], baseline: dict[str, Any],
                 revision: str, output: Path, runner_cls: type | None = None) -> dict[str, Any]:
    runtime = _runtime(stage, base_runtime, stream)
    reference = z6._reference(baseline, int(stream["prefix_checkpoint_last_state"]) + 1)
    row = z6.one_rollout(cfg, runtime, stream, reference, runner_cls=runner_cls)
    row.update({"schema_version": SCHEMA, "source_revision": revision,
                "family_id": stream["family_id"], "phase_issue": stream["phase_issue"],
                "vertex_id": stream["vertex_id"], "fit_weight": stream["fit_weight"],
                "data_role": stream["data_role"]})
    io.write_new(output / f"{stream['rollout_id']}.json", row)
    return row


def _geometry(vectors: Sequence[np.ndarray], count: int) -> dict[str, float]:
    angles = sorted((math.degrees(math.atan2(float(v[1]), float(v[0]))) + 360) % 360
                    for v in vectors)
    gap = max(angles[(i + 1) % len(angles)] + (360 if i == len(angles) - 1 else 0)
              - angles[i] for i in range(len(angles)))
    weak = min(max(float(np.dot(v, np.asarray([math.cos(a), math.sin(a)]))) for v in vectors)
               for a in (2 * math.pi * i / count for i in range(count)))
    return {"maximum_angular_gap_deg": gap, "weakest_best_projection_m": weak}


def scientific_metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    gates = stage["measurement_gates"]
    by_id = {row.get("family_id"): row for row in rows}
    baseline = by_id.get("baseline_full_f")
    phase_rows: list[dict[str, Any]] = []
    baseline_complete = bool(
        baseline and baseline.get("passed") and len(baseline.get("states", [])) == 66)
    all_passed = baseline_complete
    if baseline_complete:
        for phase in stage["phase_issue_steps"]:
            arm_values: list[dict[str, Any]] = []
            by_horizon: dict[int, list[np.ndarray]] = {4: [], 8: []}
            for arm in stage["selected_vertex_ids"]:
                row = by_id.get(f"issue{phase}__{arm}")
                complete = bool(row and row.get("passed") and len(row.get("states", [])) == 66)
                if not complete:
                    arm_values.append({"vertex_id": arm, "complete": False, "passed": False})
                    all_passed = False; continue
                vectors = {h: np.asarray([
                    row["states"][phase + h]["r_geo_m"] - baseline["states"][phase + h]["r_geo_m"],
                    row["states"][phase + h]["z_geo_m"] - baseline["states"][phase + h]["z_geo_m"]])
                    for h in (4, 8)}
                norms = {h: float(np.linalg.norm(vectors[h])) for h in (4, 8)}
                cosine = float(np.dot(vectors[4], vectors[8]) / (norms[4] * norms[8])) if norms[4] and norms[8] else -1.0
                max_ip = max(abs(float(row["states"][i]["ip_a"])
                                 - float(baseline["states"][i]["ip_a"]))
                             for i in range(phase + 1, 66))
                passed = bool(norms[4] >= gates["minimum_each_h4_rz_response_m"]
                              and norms[8] >= gates["minimum_each_h8_rz_response_m"]
                              and cosine >= gates["minimum_each_h4_h8_cosine"]
                              and max_ip <= gates["maximum_absolute_paired_ip_response_a"])
                arm_values.append({"vertex_id": arm, "complete": True,
                                   "h4_response_m": vectors[4].tolist(),
                                   "h8_response_m": vectors[8].tolist(),
                                   "h4_norm_m": norms[4], "h8_norm_m": norms[8],
                                   "h4_h8_cosine": cosine,
                                   "maximum_absolute_paired_ip_response_a": max_ip,
                                   "passed": passed})
                by_horizon[4].append(vectors[4]); by_horizon[8].append(vectors[8])
                all_passed = all_passed and passed
            geometry = []
            for horizon in (4, 8):
                value = _geometry(by_horizon[horizon], gates["direction_grid_count"]) if len(by_horizon[horizon]) == 4 else {"maximum_angular_gap_deg": math.inf, "weakest_best_projection_m": -math.inf}
                value.update({"horizon": horizon, "passed": bool(
                    value["maximum_angular_gap_deg"] <= gates["maximum_each_phase_horizon_angular_gap_deg"]
                    and value["weakest_best_projection_m"] >= gates["minimum_each_phase_horizon_weakest_best_projection_m"])})
                all_passed = all_passed and value["passed"]; geometry.append(value)
            phase_rows.append({"phase_issue": phase, "arm_metrics": arm_values,
                               "geometry": geometry,
                               "passed": all(item.get("passed") for item in arm_values)
                                         and all(item["passed"] for item in geometry)})
    replay = z6.replay_check(by_id.get("issue24__p05_plus4"),
                             by_id.get("replay_issue24__p05_plus4"),
                             stage["semantic_artifacts"])
    all_passed = all_passed and replay["passed"] and len(phase_rows) == 2
    capture = []
    if baseline_complete:
        source = baseline["states"][0]; source_ip = abs(float(source["ip_a"]))
        for row in rows:
            if not row.get("passed") or len(row.get("states", [])) != 66:
                continue
            terminal = gates["capture_terminal_state_indices"]
            distances = [math.hypot(row["states"][i]["r_geo_m"] - source["r_geo_m"],
                                    row["states"][i]["z_geo_m"] - source["z_geo_m"]) for i in terminal]
            speeds = [math.hypot(row["states"][i]["r_geo_m"] - row["states"][i-1]["r_geo_m"],
                                 row["states"][i]["z_geo_m"] - row["states"][i-1]["z_geo_m"]) / .001 for i in terminal]
            ips = [abs(row["states"][i]["ip_a"] - source["ip_a"]) / source_ip for i in terminal]
            capture.append({"family_id": row["family_id"], "maximum_distance_m": max(distances),
                            "maximum_speed_m_per_s": max(speeds), "maximum_ip_fraction": max(ips),
                            "captured": max(distances) <= gates["capture_distance_m"] and max(speeds) <= gates["capture_speed_m_per_s"] and max(ips) <= gates["capture_ip_fraction"]})
    return {"phase_metrics": phase_rows, "replay_metrics": replay,
            "capture_diagnostics": capture, "passed": bool(all_passed)}


def offline(path: Path, revision: str) -> dict[str, Any]:
    failures: list[str] = []
    try:
        stage, _, cfg, targets, parent, _ = load(path)
        streams = build_streams(stage, cfg, targets, parent)
        checks = [validate_stream(row, stage, cfg) for row in streams]
        if len(streams) != 10 or len({row["rollout_id"] for row in streams}) != 10:
            failures.append("STREAM_POPULATION")
        if not all(row["passed"] for row in checks):
            failures.append("STATIC_STREAM_INADMISSIBLE")
    except Exception as exc:
        checks = []; failures.append(f"{type(exc).__name__}:{exc}")
    return {"schema_version": OFFLINE_SCHEMA, "source_revision": revision,
            "stage_config_sha256": CONFIG_SHA256, "passed": not failures,
            "failures": failures, "stream_checks": checks,
            "reset_calls": 0, "plant_advance_gotsc_calls": 0,
            "models_fit_or_updated": 0}


def execute(stage: dict[str, Any], base_runtime: dict[str, Any], cfg: Any,
            targets: dict[str, Any], parent: dict[str, Any], baseline: dict[str, Any],
            revision: str, output: Path, storage: dict[str, Any],
            runner_cls: type | None = None) -> dict[str, Any]:
    isolation = z7.configure_run_root(cfg, output)
    streams = build_streams(stage, cfg, targets, parent)
    rows: list[dict[str, Any]] = []; prefixes: list[dict[str, Any]] = []
    execution = True
    for stream in streams:
        row = _execute_row(cfg, stage, base_runtime, stream, baseline, revision,
                           output, runner_cls=runner_cls)
        rows.append(row)
        decision = int(stream["prefix_checkpoint_last_state"])
        prefixes.append(z6.prefix_check(row, baseline, decision + 1, decision,
                                        stage["semantic_artifacts"]))
        if not row.get("passed"):
            execution = False; break
    counters = {key: sum(int(row.get(key, 0)) for row in rows) for key in
                ("reset_calls", "advance_attempts", "plant_advance_gotsc_calls", "verified_plant_advances")}
    if len(rows) > 10 or any(counters[key] > 650 for key in counters):
        execution = False
    inventory = io.raw_inventory(output, rows, stage)
    expected_files = 5 * sum(len(row.get("states", [])) for row in rows)
    raw_ok = not inventory["missing_required_artifacts"] and inventory["required_artifact_files"] == expected_files
    prefix_ok = len(prefixes) == len(rows) and all(row["passed"] for row in prefixes)
    complete = sum(row.get("passed") and len(row.get("states", [])) == 66 for row in rows)
    scientific = scientific_metrics(rows, stage)
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
    result = {"schema_version": SCHEMA, "source_revision": revision,
              "stage_config_sha256": CONFIG_SHA256,
              "passed": route == stage["routes"]["data_pass"], "route": route,
              "storage_gate": storage, "run_root_isolation": isolation,
              "execution_integrity_passed": execution, "raw_integrity_passed": raw_ok,
              "prefix_checks": prefixes, "scientific_metrics": scientific,
              "rollouts_started": len(rows), "complete_rollouts": complete,
              **counters, **inventory, "models_fit_or_updated": 0,
              "calibration_or_holdout_records_read": 0,
              "claim_boundary": stage["claim_boundary"]}
    io.write_new(output / "result.json", result)
    return result


def _failure_result(stage: dict[str, Any], revision: str, output: Path,
                    storage: dict[str, Any], exc: Exception) -> dict[str, Any]:
    """Best-effort preservation after an identity-consuming run failure."""
    rows: list[dict[str, Any]] = []
    excluded = {"offline_preflight.json", "result.json", "independent_raw_audit.json"}
    for item in sorted(output.glob("*.json")):
        if item.name in excluded:
            continue
        try:
            row = _load_json(item)
        except Exception:
            continue
        if "rollout_id" in row:
            rows.append(row)
    counters = {key: sum(int(row.get(key, 0)) for row in rows) for key in
                ("reset_calls", "advance_attempts", "plant_advance_gotsc_calls",
                 "verified_plant_advances")}
    try:
        inventory = io.raw_inventory(output, rows, stage)
    except Exception as inv_exc:
        inventory = {"required_artifact_files": 0, "required_artifact_bytes": 0,
                     "required_artifact_inventory_sha256": None,
                     "missing_required_artifacts": [
                         f"FINALIZER:{type(inv_exc).__name__}:{inv_exc}"]}
    return {"schema_version": SCHEMA, "source_revision": revision,
            "stage_config_sha256": CONFIG_SHA256, "passed": False,
            "route": stage["routes"]["execution_or_interface_fail"],
            "failure": f"{type(exc).__name__}:{exc}", "storage_gate": storage,
            "rollouts_started": len(rows), "complete_rollouts": sum(
                bool(row.get("passed") and len(row.get("states", [])) == 66)
                for row in rows),
            "campaign_aborted_after_rollout_failure": True,
            **counters, **inventory, "models_fit_or_updated": 0,
            "calibration_or_holdout_records_read": 0,
            "claim_boundary": (
                "Best-effort classified execution failure; preserved raw is not a "
                "scientific geometry verdict and the consumed identity must not rerun.")}


def run(path: Path, revision: str, output: Path) -> dict[str, Any]:
    output = z18.inside(output, "ID2Z23 output")
    if output.exists():
        raise FileExistsError(str(output))
    stage, base_runtime, cfg, targets, parent, baseline = load(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    storage = io.storage(stage, output); output.mkdir()
    preflight = offline(path, revision); io.write_new(output / "offline_preflight.json", preflight)
    if not storage["passed"] or not preflight["passed"]:
        route = stage["routes"]["storage_fail" if not storage["passed"] else "offline_or_input_fail"]
        result = {"schema_version": SCHEMA, "source_revision": revision,
                  "stage_config_sha256": CONFIG_SHA256, "passed": False, "route": route,
                  "storage_gate": storage, "reasons": preflight["failures"],
                  "rollouts_started": 0, "reset_calls": 0, "advance_attempts": 0,
                  "plant_advance_gotsc_calls": 0, "verified_plant_advances": 0,
                  "models_fit_or_updated": 0}
        io.write_new(output / "result.json", result); return result
    try:
        return execute(stage, base_runtime, cfg, targets, parent, baseline,
                       revision, output, storage)
    except Exception as exc:
        result = _failure_result(stage, revision, output, storage, exc)
        if not (output / "result.json").exists():
            io.write_new(output / "result.json", result)
        return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-config", type=Path, default=CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--offline-only", action="store_true")
    args = parser.parse_args(argv)
    if args.offline_only:
        value = offline(args.stage_config, args.source_revision)
    else:
        if args.output is None:
            parser.error("--output is required")
        value = run(args.stage_config, args.source_revision, args.output)
    print(json.dumps(value, indent=2, sort_keys=True, allow_nan=False))
    return 0 if value["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
