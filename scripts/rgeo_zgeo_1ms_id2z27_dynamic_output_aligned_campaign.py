#!/usr/bin/env python3
"""Run the frozen ID-2Z27 dynamic output-aligned D0 campaign."""

from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path
import sys
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_id2z25_centered_coallocation_campaign as z25  # noqa: E402


z18, z23, z17, z6, z7, io = z25.z18, z25.z23, z25.z17, z25.z6, z25.z7, z25.io
target_from_fields = z25.target_from_fields
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z27_dynamic_output_aligned_campaign.json"
CONFIG_SHA256 = "4491648a2260ab149b19d82d55059f8d6caf7379e85cb073e2ce1296c37124d3"
SCHEMA = "rgeo-zgeo-1ms-id2z27-dynamic-output-aligned-campaign-result-v1"
OFFLINE_SCHEMA = "rgeo-zgeo-1ms-id2z27-dynamic-output-aligned-offline-v1"


def _error(message: str) -> Exception:
    return z6._error(f"ID2Z27: {message}")


def _load(path: Path) -> dict[str, Any]:
    return z18.load_json(path)


def _require(stage: dict[str, Any]) -> None:
    if io.sha256(CONFIG) != CONFIG_SHA256:
        raise _error("config hash mismatch")
    if stage != _load(CONFIG):
        raise _error("frozen config changed")
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2z27-dynamic-output-aligned-campaign-v1",
        "identity": "rgeo-zgeo-1ms-id2z27-dynamic-output-aligned-campaign-v1",
        "stage": "ID-2Z27", "takeover_time_ms": 1100,
        "control_period_ms": 1, "common_horizon_steps": 73,
        "common_terminal_state_index": 73,
        "exact_full_f_prefix_last_issue": 31,
        "transition_center_first_issue": 32,
        "transition_center_last_issue": 55,
        "held_tail_first_issue": 56, "held_tail_last_issue": 72,
        "phase_issue_steps": [32, 40],
        "output_aligned_axis_ids": ["q_r", "q_z"],
        "initial_signs": ["plus", "minus"],
        "same_sign_duration_issues": 8, "exact_return_bridge_issues": 8,
        "maximum_rollouts": 11, "maximum_reset_calls": 11,
        "maximum_advance_attempts": 803, "maximum_gotsc_calls": 803,
        "maximum_verified_plant_advances": 803,
        "maximum_retained_states": 814,
        "required_artifact_files_if_all_complete": 4070,
        "retry_after_any_advance_attempt": "forbidden",
        "models_fit_or_updated": 0,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise _error(f"frozen field changed: {key}")
    ids = [row.get("family_id") for row in stage.get("rollout_specs", [])]
    expected_ids = [
        "baseline_transition_center", "diagnostic_baseline_full_f",
        *[f"issue{phase}__{axis}__{sign}_then_return"
          for phase in (32, 40) for axis in ("q_r", "q_z")
          for sign in ("plus", "minus")],
        "replay_issue32__q_z__plus_then_return"]
    if ids != expected_ids:
        raise _error("rollout matrix changed")
    data = stage.get("data_contract", {})
    if (data.get("id2z25_fit_weight") != 0
            or data.get("development_fit_family_count") != 9
            or data.get("d0_requires_capture") is not False):
        raise _error("data/control boundary changed")


def load(path: Path = CONFIG) -> tuple[dict[str, Any], dict[str, Any], Any,
                                       dict[str, Any], dict[str, Any]]:
    path = z18.inside(path, "ID2Z27 config")
    if path != CONFIG.resolve():
        raise _error("alternate config forbidden")
    stage = _load(path); _require(stage)
    evidence: dict[str, dict[str, Any]] = {}
    for name, spec in stage["evidence"].items():
        item = z18.inside(ROOT / spec["path"], name)
        if io.sha256(item) != spec["sha256"]:
            raise _error(f"evidence mismatch: {name}")
        if item.suffix == ".json":
            evidence[name] = _load(item)
    preflight, audit = evidence["preflight_result"], evidence["preflight_independent"]
    if (preflight.get("passed") is not True
            or preflight.get("route") != stage["evidence"]["preflight_result"]["required_route"]
            or preflight.get("plant_advances") != 0
            or preflight.get("tsc_calls") != 0
            or audit.get("audit_passed") is not True
            or audit.get("primary_sha256") != stage["evidence"]["preflight_result"]["sha256"]):
        raise _error("ID2Z26R1 prerequisite mismatch")
    _, base_runtime, cfg, _, _, baseline = z23.load(z23.CONFIG)
    if len(baseline.get("states", [])) != 66 or len(baseline.get("actions", [])) != 65:
        raise _error("tracked full-F prefix incomplete")
    return stage, base_runtime, cfg, preflight, baseline


def _targets(fields: Sequence[Sequence[str]], cfg: Any, name: str) -> list[Any]:
    return [target_from_fields(row, cfg, f"{name}.{issue}")
            for issue, row in enumerate(fields)]


def _actions(targets: Sequence[Any], cfg: Any, family: str,
             reference: dict[str, Any]) -> list[dict[str, Any]]:
    width = len(reference["actions"][0].get("probe_virtual_action", [])) or 10
    virtual = [list(reference["actions"][issue].get("probe_virtual_action", [0.0] * width))
               if issue < min(32, len(reference["actions"])) else [0.0] * width
               for issue in range(73)]
    return z17.z6.z5.z3.z1.c1._actions(targets, cfg, family, virtual)


def build_streams(stage: dict[str, Any], cfg: Any, preflight: dict[str, Any],
                  baseline: dict[str, Any]) -> list[dict[str, Any]]:
    static = {row["rollout_id"]: row for row in preflight["prospective_static_streams"]}
    rows: list[dict[str, Any]] = []; by_id: dict[str, dict[str, Any]] = {}
    for spec in stage["rollout_specs"]:
        family = str(spec["family_id"])
        if spec["kind"] == "replay":
            source = by_id[str(spec["source_family_id"])]
            stream = copy.deepcopy(source)
            stream.update({"rollout_id": family, "candidate_id": family,
                           "family_id": family, "kind": "replay",
                           "source_family_id": spec["source_family_id"],
                           "fit_weight": 0, "data_role": "zero_fit_replay",
                           "cell_id": family})
        else:
            fields = static[family]["card15_targets"]
            targets = _targets(fields, cfg, family)
            actions = _actions(targets, cfg, family, baseline)
            phase = spec.get("phase_issue")
            checkpoint = 32 if phase is None else int(phase)
            stream = {
                "rollout_id": family, "candidate_id": family, "family_id": family,
                "kind": spec["kind"], "phase_issue": phase,
                "axis_id": spec.get("axis_id"), "initial_sign": spec.get("initial_sign"),
                "fit_weight": int(spec["fit_weight"]),
                "data_role": "development" if int(spec["fit_weight"]) else "zero_fit_diagnostic",
                "round_index": 0, "round_id": "dynamic_output_aligned_d0",
                "cell_id": family, "cell_kind": "dynamic_output_aligned_history",
                "context_id": f"canonical_dynamic_state{checkpoint}",
                "coordinate": "full_f_to_slack_qrz_sustained8_return_bridge8",
                "probe_issue_step": phase,
                "probe_duration_issues": 0 if phase is None else 8,
                "prefix_checkpoint_last_state": checkpoint,
                "non_nominal_issue_steps": [] if phase is None else list(
                    range(int(phase), int(phase) + 16)),
                "targets": targets, "actions": actions,
            }
        rows.append(stream); by_id[family] = stream
    return rows


def validate_stream(stream: dict[str, Any], stage: dict[str, Any], cfg: Any) -> dict[str, Any]:
    failures: list[str] = []
    if len(stream["targets"]) != 73 or len(stream["actions"]) != 73:
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
            "minimum_absolute_current_headroom_a": headroom,
            "maximum_issued_delta_a": max(float(row["maximum_issued_delta_a"])
                                           for row in stream["actions"]),
            "failures": failures}


def _runtime(stage: dict[str, Any], base: dict[str, Any], stream: dict[str, Any]) -> dict[str, Any]:
    value = dict(base); value.update(stage)
    value["horizon_steps"] = 73
    decision = int(stream["prefix_checkpoint_last_state"])
    value["decision_state_index"] = decision
    value["rounds"] = [{"round_index": 0, "decision_state_index": decision}]
    value["prefix_gates"] = {"checkpoint_indices": list(range(decision + 1))}
    value["empirical_exploration"] = dict(stage["empirical_exploration"])
    value["empirical_exploration"]["inner_novel_issue_clearance"] = dict(
        stage["empirical_exploration"]["simulator_development_preissue_clearance"])
    return value


def _reference_for(stream: dict[str, Any], baseline: dict[str, Any],
                   centered: dict[str, Any] | None) -> dict[str, Any]:
    if stream["kind"] in ("center_baseline", "full_f_diagnostic"):
        return z6._reference(baseline, 33)
    if centered is None:
        raise _error("center baseline unavailable before branch")
    return z6._reference(centered, int(stream["prefix_checkpoint_last_state"]) + 1)


def _execute_row(cfg: Any, stage: dict[str, Any], base: dict[str, Any],
                 stream: dict[str, Any], reference: dict[str, Any], revision: str,
                 output: Path, runner_cls: type | None = None) -> dict[str, Any]:
    row = z6.one_rollout(cfg, _runtime(stage, base, stream), stream, reference,
                        runner_cls=runner_cls)
    row.update({"schema_version": SCHEMA, "source_revision": revision,
                "family_id": stream["family_id"], "kind": stream["kind"],
                "phase_issue": stream["phase_issue"], "axis_id": stream["axis_id"],
                "initial_sign": stream["initial_sign"], "fit_weight": stream["fit_weight"],
                "data_role": stream["data_role"]})
    io.write_new(output / f"{stream['rollout_id']}.json", row)
    return row


def _response(row: dict[str, Any], baseline: dict[str, Any], state: int) -> np.ndarray:
    return np.asarray([float(row["states"][state]["r_geo_m"])
                       - float(baseline["states"][state]["r_geo_m"]),
                       float(row["states"][state]["z_geo_m"])
                       - float(baseline["states"][state]["z_geo_m"])])


def scientific_metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    by_id = {str(row.get("family_id")): row for row in rows}
    baseline = by_id.get("baseline_transition_center")
    complete_baseline = bool(baseline and baseline.get("passed")
                             and len(baseline.get("states", [])) == 74)
    gates = stage["measurement_gates"]
    branches: list[dict[str, Any]] = []; all_signal = complete_baseline
    geometry: list[dict[str, Any]] = []
    if complete_baseline:
        for phase in stage["phase_issue_steps"]:
            vectors = {4: [], 8: []}
            for axis in stage["output_aligned_axis_ids"]:
                for sign in stage["initial_signs"]:
                    family = f"issue{phase}__{axis}__{sign}_then_return"
                    row = by_id.get(family)
                    complete = bool(row and row.get("passed")
                                    and len(row.get("states", [])) == 74)
                    if not complete:
                        branches.append({"family_id": family, "complete": False,
                                         "passed": False})
                        all_signal = False; continue
                    value = {h: _response(row, baseline, int(phase) + h) for h in (4, 8)}
                    norms = {h: float(np.linalg.norm(value[h])) for h in (4, 8)}
                    cosine = (float(np.dot(value[4], value[8]) / (norms[4] * norms[8]))
                              if norms[4] and norms[8] else -1.0)
                    max_ip = max(abs(float(row["states"][i]["ip_a"])
                                     - float(baseline["states"][i]["ip_a"]))
                                 for i in range(int(phase) + 1, 74))
                    passed = bool(norms[4] >= gates["minimum_each_h4_rz_response_m"]
                                  and norms[8] >= gates["minimum_each_h8_rz_response_m"]
                                  and cosine >= gates["minimum_each_h4_h8_cosine"]
                                  and max_ip <= gates["maximum_absolute_paired_ip_response_a"])
                    branches.append({"family_id": family, "complete": True,
                                     "h4_response_m": value[4].tolist(),
                                     "h8_response_m": value[8].tolist(),
                                     "h4_norm_m": norms[4], "h8_norm_m": norms[8],
                                     "h4_h8_cosine": cosine,
                                     "maximum_absolute_paired_ip_response_a": max_ip,
                                     "passed": passed})
                    vectors[4].append(value[4]); vectors[8].append(value[8])
                    all_signal = all_signal and passed
            for h in (4, 8):
                value = z23._geometry(vectors[h], gates["direction_grid_count"])
                value.update({"phase_issue": phase, "horizon": h,
                              "passed": bool(
                                  value["maximum_angular_gap_deg"] <= gates["maximum_each_phase_horizon_angular_gap_deg"]
                                  and value["weakest_best_projection_m"] >= gates["minimum_each_phase_horizon_weakest_best_projection_m"])})
                geometry.append(value); all_signal = all_signal and value["passed"]
    replay = z6.replay_check(
        by_id.get("issue32__q_z__plus_then_return"),
        by_id.get("replay_issue32__q_z__plus_then_return"),
        stage["semantic_artifacts"])
    capture: list[dict[str, Any]] = []
    if complete_baseline:
        source = baseline["states"][0]; source_ip = abs(float(source["ip_a"]))
        for row in rows:
            if not row.get("passed") or len(row.get("states", [])) != 74:
                continue
            idx = gates["capture_terminal_state_indices"]
            distance = [math.hypot(float(row["states"][i]["r_geo_m"])-float(source["r_geo_m"]),
                                   float(row["states"][i]["z_geo_m"])-float(source["z_geo_m"])) for i in idx]
            speed = [math.hypot(float(row["states"][i]["r_geo_m"])-float(row["states"][i-1]["r_geo_m"]),
                                float(row["states"][i]["z_geo_m"])-float(row["states"][i-1]["z_geo_m"]))/0.001 for i in idx]
            ip = [abs(float(row["states"][i]["ip_a"])-float(source["ip_a"]))/source_ip for i in idx]
            capture.append({"family_id": row["family_id"],
                            "maximum_distance_m": max(distance),
                            "maximum_speed_m_per_s": max(speed),
                            "maximum_ip_fraction": max(ip),
                            "captured": bool(max(distance) <= gates["capture_distance_m"]
                                             and max(speed) <= gates["capture_speed_m_per_s"]
                                             and max(ip) <= gates["capture_ip_fraction"])})
    return {"baseline_complete": complete_baseline, "branch_metrics": branches,
            "positive_span_metrics": geometry, "capture_diagnostics": capture,
            "replay_metrics": replay,
            "passed": bool(all_signal and len(branches) == 8 and replay["passed"])}


def offline(path: Path, revision: str) -> dict[str, Any]:
    failures: list[str] = []
    try:
        stage, _, cfg, preflight, baseline = load(path)
        streams = build_streams(stage, cfg, preflight, baseline)
        checks = [validate_stream(row, stage, cfg) for row in streams]
        if len(streams) != 11 or len({row["rollout_id"] for row in streams}) != 11:
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


def execute(stage: dict[str, Any], base: dict[str, Any], cfg: Any,
            preflight: dict[str, Any], baseline: dict[str, Any], revision: str,
            output: Path, storage: dict[str, Any],
            runner_cls: type | None = None) -> dict[str, Any]:
    isolation = z7.configure_run_root(cfg, output)
    streams = build_streams(stage, cfg, preflight, baseline)
    rows: list[dict[str, Any]] = []; prefixes: list[dict[str, Any]] = []
    centered: dict[str, Any] | None = None; execution = True
    for stream in streams:
        reference_source = baseline if stream["kind"] in ("center_baseline", "full_f_diagnostic") else centered
        reference = _reference_for(stream, baseline, centered)
        row = _execute_row(cfg, stage, base, stream, reference, revision, output,
                           runner_cls=runner_cls)
        rows.append(row)
        state_count = 33 if stream["kind"] in ("center_baseline", "full_f_diagnostic") else int(stream["prefix_checkpoint_last_state"]) + 1
        prefixes.append(z6.prefix_check(row, reference_source or {}, state_count,
                                        state_count - 1, stage["semantic_artifacts"]))
        if stream["kind"] == "center_baseline" and row.get("passed") and len(row.get("states", [])) == 74:
            centered = row
        if not row.get("passed"):
            execution = False; break
    counters = {key: sum(int(row.get(key, 0)) for row in rows) for key in
                ("reset_calls", "advance_attempts", "plant_advance_gotsc_calls",
                 "verified_plant_advances")}
    if len(rows) > 11 or any(counters[key] > 803 for key in counters):
        execution = False
    inventory = io.raw_inventory(output, rows, stage)
    expected_files = 5 * sum(len(row.get("states", [])) for row in rows)
    raw_ok = (not inventory["missing_required_artifacts"]
              and inventory["required_artifact_files"] == expected_files)
    prefix_ok = len(prefixes) == len(rows) and all(row["passed"] for row in prefixes)
    complete = sum(bool(row.get("passed") and len(row.get("states", [])) == 74)
                   for row in rows)
    scientific = scientific_metrics(rows, stage)
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
    rows = []
    for item in sorted(output.glob("*.json")):
        if item.name in {"offline_preflight.json", "result.json", "independent_raw_audit.json"}:
            continue
        try:
            value = _load(item)
            if "rollout_id" in value:
                rows.append(value)
        except Exception:
            pass
    counters = {key: sum(int(row.get(key, 0)) for row in rows) for key in
                ("reset_calls", "advance_attempts", "plant_advance_gotsc_calls",
                 "verified_plant_advances")}
    try:
        inventory = io.raw_inventory(output, rows, stage)
    except Exception as inv:
        inventory = {"required_artifact_files": 0, "required_artifact_bytes": 0,
                     "required_artifact_inventory_sha256": None,
                     "missing_required_artifacts": [f"FINALIZER:{type(inv).__name__}:{inv}"]}
    return {"schema_version": SCHEMA, "source_revision": revision,
            "stage_config_sha256": CONFIG_SHA256, "passed": False,
            "route": stage["routes"]["execution_or_interface_fail"],
            "failure": f"{type(exc).__name__}:{exc}", "storage_gate": storage,
            "rollouts_started": len(rows), "complete_rollouts": sum(
                bool(row.get("passed") and len(row.get("states", [])) == 74) for row in rows),
            "campaign_aborted_after_rollout_failure": True,
            **counters, **inventory, "models_fit_or_updated": 0,
            "calibration_or_holdout_records_read": 0,
            "claim_boundary": "Best-effort execution failure; no scientific D0 verdict."}


def run(path: Path, revision: str, output: Path) -> dict[str, Any]:
    output = z18.inside(output, "ID2Z27 output")
    if output.exists():
        raise FileExistsError(str(output))
    stage, base, cfg, preflight, baseline = load(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    storage = io.storage(stage, output); output.mkdir()
    pre = offline(path, revision); io.write_new(output / "offline_preflight.json", pre)
    if not storage["passed"] or not pre["passed"]:
        route = stage["routes"]["storage_fail" if not storage["passed"] else "offline_or_input_fail"]
        result = {"schema_version": SCHEMA, "source_revision": revision,
                  "stage_config_sha256": CONFIG_SHA256, "passed": False, "route": route,
                  "storage_gate": storage, "reasons": pre["failures"],
                  "rollouts_started": 0, "reset_calls": 0, "advance_attempts": 0,
                  "plant_advance_gotsc_calls": 0, "verified_plant_advances": 0,
                  "models_fit_or_updated": 0}
        io.write_new(output / "result.json", result); return result
    try:
        return execute(stage, base, cfg, preflight, baseline, revision, output, storage)
    except Exception as exc:
        result = _failure_result(stage, revision, output, storage, exc)
        if not (output / "result.json").exists():
            io.write_new(output / "result.json", result)
        return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)
    if args.offline:
        value = offline(args.config, args.source_revision)
        io.write_new(args.output, value)
    else:
        value = run(args.config, args.source_revision, args.output)
    print(json.dumps(value, sort_keys=True))
    return 0 if value["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
