#!/usr/bin/env python3
"""Collect and calibrate the frozen ID-2G1R1 TCN on fresh histories."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
from typing import Any, Sequence

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_id0_vector_tail import (  # noqa: E402
    InputIntegrityError,
    compare_rows,
    inside_root,
    raw_inventory,
    sha256,
    write_new,
)
from scripts.rgeo_zgeo_1ms_id0_vector_tail_independent import _state  # noqa: E402
from scripts.rgeo_zgeo_1ms_id2c1_active_nominal_vector_search import (  # noqa: E402
    _actions,
    _translated_target,
    phase_a_streams,
)
from scripts.rgeo_zgeo_1ms_id2f1_repeated_context_development import (  # noqa: E402
    load as load_id2f1,
    one_rollout,
)
from scripts import rgeo_zgeo_1ms_id2g1_grouped_causal_model as model  # noqa: E402


CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2h1_whole_history_calibration.json"
CONFIG_SHA256 = "c067306fd0ce3d1e7999375138511af15d950fb9a7b50aad2da456af6715720b"
SCHEMA = "rgeo-zgeo-1ms-id2h1-whole-history-calibration-result-v1"
CALIBRATION_SCHEMA = "rgeo-zgeo-1ms-id2h1-frozen-tcn-calibration-v1"


def _read_json(path: Path, expected_hash: str | None = None) -> dict[str, Any]:
    path = inside_root(path, "JSON evidence")
    if expected_hash is not None and sha256(path) != expected_hash:
        raise InputIntegrityError(f"hash mismatch: {path.relative_to(ROOT)}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise InputIntegrityError(f"object required: {path.relative_to(ROOT)}")
    return value


def _require_stage(stage: dict[str, Any]) -> None:
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2h1-whole-history-calibration-v1",
        "identity": "rgeo-zgeo-1ms-id2h1-fresh-whole-history-calibration-v1",
        "stage": "ID-2H1",
        "takeover_time_ms": 1100,
        "control_period_ms": 1,
        "horizon_steps": 34,
        "whole_history_groups": 10,
        "cells_per_group": 2,
        "replays_per_cell": 2,
        "maximum_rollouts": 40,
        "maximum_reset_calls": 40,
        "maximum_advance_attempts": 1360,
        "maximum_gotsc_calls": 1360,
        "maximum_verified_plant_advances": 1360,
        "maximum_retained_states": 1400,
        "retry_after_any_advance_attempt": "forbidden",
        "model_fit_retrain_tune_or_select_use": "forbidden",
        "blind_holdout_use": "forbidden",
        "id2c2_records_read": 0,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise InputIntegrityError(f"frozen field mismatch: {key}")
    groups = stage.get("groups")
    if not isinstance(groups, list) or len(groups) != 10:
        raise InputIntegrityError("ten calibration groups required")
    if [row.get("group_id") for row in groups] != [f"c{i:02d}" for i in range(10)]:
        raise InputIntegrityError("group identities changed")
    for row in groups:
        probe = row.get("probe", {})
        if probe.get("issue_step") != 22 or probe.get("direction") not in ("p04", "p07"):
            raise InputIntegrityError("probe matrix changed")
        if probe.get("sign") not in ("plus", "minus") or probe.get("duration_issues") not in (1, 2, 4):
            raise InputIntegrityError("probe grammar changed")
        for event in row.get("conditioners", []):
            if event.get("direction") not in ("p04", "p07") or event.get("sign") not in ("plus", "minus"):
                raise InputIntegrityError("conditioner grammar changed")
            if event.get("issue_step") not in (17, 19, 20) or event.get("duration_issues") not in (1, 2):
                raise InputIntegrityError("conditioner timing changed")
    calibration = stage.get("calibration", {})
    required = {
        "selected_candidate": "causal_tcn",
        "member_seeds": [11, 29, 47],
        "recursive_origin_state": 16,
        "absolute_error_state_range_inclusive": [17, 34],
        "paired_response_state_range_inclusive": [23, 34],
        "statistical_unit": "whole_conditioner_group",
        "nominal_group_coverage": 0.9,
        "group_count": 10,
        "finite_sample_order_index_one_based": 10,
        "absolute_width_caps": [0.0015, 0.0015, 75.0],
        "paired_response_width_caps": [0.001, 0.001, 50.0],
        "maximum_matched_response_nrmse": 1.0,
        "minimum_positive_peak_cosine_groups": 8,
        "future_actual_current_in_prediction": "forbidden",
        "model_or_feature_update": "forbidden",
    }
    if calibration != required:
        raise InputIntegrityError("calibration contract changed")
    if stage.get("semantic_artifacts") != ["inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv"]:
        raise InputIntegrityError("semantic artifact contract changed")
    if stage.get("diagnostic_artifacts") != ["sprsina"]:
        raise InputIntegrityError("diagnostic artifact contract changed")


def load(stage_path: Path = CONFIG) -> tuple[dict[str, Any], Any, dict[str, Any], dict[str, Any]]:
    stage_path = inside_root(stage_path, "ID2H1 config")
    if sha256(stage_path) != CONFIG_SHA256:
        raise InputIntegrityError("ID2H1 config hash mismatch")
    stage = _read_json(stage_path)
    _require_stage(stage)
    base = inside_root(ROOT / stage["base_tsc_config"], "base TSC config")
    if sha256(base) != stage["evidence"]["base_tsc_config_sha256"]:
        raise InputIntegrityError("base TSC config hash mismatch")
    for key in ("design", "id2f1r1_config", "id2g1r1_config", "id2g1r1_result",
                "id2g1r1_independent", "selected_model"):
        item = stage["evidence"][key]
        path = inside_root(ROOT / item["path"], key)
        if not path.is_file() or sha256(path) != item["sha256"]:
            raise InputIntegrityError(f"evidence mismatch: {key}")
    result = _read_json(ROOT / stage["evidence"]["id2g1r1_result"]["path"])
    if (not result.get("passed") or result.get("route") != stage["evidence"]["id2g1r1_result"]["required_route"]
            or result.get("comparison", {}).get("selected_candidate") != "causal_tcn"):
        raise InputIntegrityError("ID2G1R1 selection is not accepted")
    independent = _read_json(ROOT / stage["evidence"]["id2g1r1_independent"]["path"])
    if not independent.get("audit_passed") or independent.get("selected_candidate") != "causal_tcn":
        raise InputIntegrityError("ID2G1R1 independent audit is not accepted")
    if (stage["evidence"]["selected_model"]["bytes"]
            != (ROOT / stage["evidence"]["selected_model"]["path"]).stat().st_size):
        raise InputIntegrityError("selected model size mismatch")
    source_stage, cfg, targets, id2c1_stage = load_id2f1(
        ROOT / stage["evidence"]["id2f1r1_config"]["path"]
    )
    return stage, cfg, targets, id2c1_stage


def campaign_streams(stage: dict[str, Any], cfg: Any, targets: dict[str, Any],
                     id2c1_stage: dict[str, Any]) -> list[dict[str, Any]]:
    selected = next(row for row in phase_a_streams(id2c1_stage, cfg, targets)
                    if row["candidate_id"] == "p03_minus_stride1")
    held = selected["targets"][15]
    nominal = list(selected["targets"][:16]) + [held] * (stage["horizon_steps"] - 16)
    translated = {
        f"{direction}:{sign}": _translated_target(
            held, targets["q0"], targets[f"{direction}:{sign}"], cfg,
            f"id2h1.{direction}.{sign}",
        )
        for direction in ("p04", "p07") for sign in ("plus", "minus")
    }
    coordinate = {"p04": 0, "p07": 1}
    streams: list[dict[str, Any]] = []
    for group in stage["groups"]:
        for cell_kind in ("baseline", "probe"):
            cell_id = f"{group['group_id']}__{cell_kind}"
            for replay in range(stage["replays_per_cell"]):
                sequence = list(nominal)
                virtual = [[0.0, 0.0] for _ in sequence]
                non_nominal: list[int] = []
                events = list(group["conditioners"])
                if cell_kind == "probe":
                    events.append(group["probe"])
                for event in events:
                    issue = int(event["issue_step"])
                    duration = int(event["duration_issues"])
                    key = f"{event['direction']}:{event['sign']}"
                    signed = 1.0 if event["sign"] == "plus" else -1.0
                    for step in range(issue, issue + duration):
                        if sequence[step] is not held:
                            raise InputIntegrityError(f"overlapping events: {cell_id}:{step}")
                        sequence[step] = translated[key]
                        virtual[step][coordinate[event["direction"]]] = signed
                    non_nominal.append(issue)
                rollout_id = f"{cell_id}__r{replay}"
                probe = group["probe"]
                streams.append({
                    "rollout_id": rollout_id,
                    "cell_id": cell_id,
                    "group_id": group["group_id"],
                    "replay_index": replay,
                    "cell_kind": cell_kind,
                    "context_id": group["group_id"],
                    "conditioners": group["conditioners"],
                    "direction_id": None if cell_kind == "baseline" else probe["direction"],
                    "sign": None if cell_kind == "baseline" else probe["sign"],
                    "probe_issue_step": None if cell_kind == "baseline" else probe["issue_step"],
                    "probe_duration_issues": 0 if cell_kind == "baseline" else probe["duration_issues"],
                    "non_nominal_issue_steps": sorted(non_nominal),
                    "targets": sequence,
                    "actions": _actions(sequence, cfg, rollout_id, virtual),
                })
    if len(streams) != stage["maximum_rollouts"] or len({row["rollout_id"] for row in streams}) != len(streams):
        raise InputIntegrityError("campaign cardinality changed")
    return streams


def offline(stage_path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    stream_rows: list[dict[str, Any]] = []
    try:
        stage, cfg, targets, id2c1_stage = load(stage_path)
        streams = campaign_streams(stage, cfg, targets, id2c1_stage)
        for row in streams:
            if len(row["targets"]) != 34 or len(row["actions"]) != 34:
                raise InputIntegrityError("stream length changed")
            if any(float(action["maximum_issued_delta_a"]) > 0.3 for action in row["actions"]):
                raise InputIntegrityError("issued slew exceeds 0.3 A")
        stream_rows = [{key: value for key, value in row.items() if key != "targets"} for row in streams]
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {
        "schema_version": SCHEMA,
        "kind": "offline_preflight",
        "source_revision": source_revision,
        "stage_config_sha256": sha256(inside_root(stage_path, "stage config")),
        "passed": not failures,
        "failures": failures,
        "action_streams": stream_rows,
        "reset_calls": 0,
        "advance_attempts": 0,
        "plant_advance_gotsc_calls": 0,
        "verified_plant_advances": 0,
        "id2c2_records_read": 0,
        "models_fit_or_updated": 0,
    }


def _storage(stage: dict[str, Any], output: Path) -> dict[str, Any]:
    usage = shutil.disk_usage(output.parent)
    gate = stage["storage_gate"]
    return {
        "free_bytes_before_run": usage.free,
        "estimated_raw_bytes": gate["maximum_estimated_raw_bytes"],
        "estimated_free_bytes_after_run": usage.free - gate["maximum_estimated_raw_bytes"],
        "passed": (usage.free >= gate["minimum_free_bytes_before_run"]
                   and usage.free - gate["maximum_estimated_raw_bytes"] >= gate["minimum_free_bytes_after_estimate"]),
    }


def _repeatability(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> list[dict[str, Any]]:
    by_cell: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_cell.setdefault(row["cell_id"], []).append(row)
    shim = {"repeatability": stage["repeatability"], "semantic_artifacts": stage["semantic_artifacts"]}
    checks = []
    for cell_id, members in sorted(by_cell.items()):
        if len(members) != 2:
            checks.append({"cell_id": cell_id, "passed": False, "failures": ["REPLAY_COUNT"]})
        else:
            checks.append({"cell_id": cell_id, **compare_rows(members[0], members[1], shim)})
    return checks


def run(stage_path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = inside_root(output, "ID2H1 run")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    stage, cfg, targets, id2c1_stage = load(stage_path)
    storage = _storage(stage, output)
    output.mkdir(parents=True)
    preflight = offline(stage_path, source_revision)
    write_new(output / "offline_preflight.json", preflight)
    if not storage["passed"] or not preflight["passed"]:
        route = stage["routes"]["storage_fail"] if not storage["passed"] else stage["routes"]["offline_or_input_fail"]
        result = {"schema_version": SCHEMA, "source_revision": source_revision,
                  "stage_config_sha256": CONFIG_SHA256, "passed": False, "route": route,
                  "storage_gate": storage, "reasons": preflight["failures"],
                  "rollouts_completed": 0, "reset_calls": 0, "advance_attempts": 0,
                  "plant_advance_gotsc_calls": 0, "verified_plant_advances": 0,
                  "calibration_data_eligible": False, "models_fit_or_updated": 0}
        write_new(output / "result.json", result)
        return result
    cfg.run_root = output / "rollouts"
    runtime = dict(stage)
    runtime["empirical_exploration"] = dict(stage["empirical_exploration"])
    runtime["empirical_exploration"]["inner_pulse_issue_clearance"] = stage["empirical_exploration"]["inner_probe_issue_clearance"]
    streams = campaign_streams(stage, cfg, targets, id2c1_stage)
    rows: list[dict[str, Any]] = []
    for stream in streams:
        row = one_rollout(cfg, runtime, stream)
        row["schema_version"] = SCHEMA
        row["source_revision"] = source_revision
        rows.append(row)
        write_new(output / f"{row['rollout_id']}.json", row)
        if not row["passed"]:
            break
    inventory = raw_inventory(output, rows, stage)
    raw_ok = not inventory["missing_required_artifacts"]
    checks = _repeatability(rows, stage) if len(rows) == 40 and all(row["passed"] for row in rows) else []
    execution_ok = len(rows) == 40 and all(row["passed"] for row in rows)
    repeatable = len(checks) == 20 and all(row["passed"] for row in checks)
    if not execution_ok:
        route = stage["routes"]["execution_or_interface_fail"]
    elif not raw_ok:
        route = stage["routes"]["raw_integrity_fail"]
    elif not repeatable:
        route = stage["routes"]["repeatability_fail"]
    else:
        route = stage["routes"]["data_pass"]
    passed = route == stage["routes"]["data_pass"]
    result = {
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "passed": passed,
        "route": route,
        "storage_gate": storage,
        "replay_pair_checks": checks,
        "rollouts_completed": len(rows),
        "unique_cells_completed": len({row["cell_id"] for row in rows}),
        "whole_history_groups_completed": len({row["group_id"] for row in rows}),
        "reset_calls": sum(row["reset_calls"] for row in rows),
        "advance_attempts": sum(row["advance_attempts"] for row in rows),
        "plant_advance_gotsc_calls": sum(row["plant_advance_gotsc_calls"] for row in rows),
        "verified_plant_advances": sum(row["verified_plant_advances"] for row in rows),
        **inventory,
        "calibration_data_eligible": passed,
        "model_fit_retrain_tune_or_select_use": "forbidden",
        "blind_holdout_data_eligible": False,
        "controller_safety_data_eligible": False,
        "models_fit_or_updated": 0,
        "id2c2_records_read": 0,
        "claim_boundary": stage["claim_boundary"],
    }
    write_new(output / "result.json", result)
    return result


def _load_tcn(stage: dict[str, Any]) -> list[model.NeuralModel]:
    path = inside_root(ROOT / stage["evidence"]["selected_model"]["path"], "selected model")
    try:
        payload = torch.load(path, map_location="cpu", weights_only=True)
    except TypeError:
        payload = torch.load(path, map_location="cpu")
    if payload.get("metadata", {}).get("selected_candidate") != "causal_tcn":
        raise InputIntegrityError("selected model metadata changed")
    stage_g = model.load_stage(ROOT / stage["evidence"]["id2g1r1_config"]["path"])
    cfg = stage_g["candidates"]["causal_tcn"]
    states = payload.get("state_dicts", {}).get("causal_tcn")
    if not isinstance(states, list) or len(states) != 3:
        raise InputIntegrityError("TCN member count changed")
    members = []
    for state_dict in states:
        module = model.CausalTCNDelta(int(cfg["hidden_width"]), cfg["dilations"], int(cfg["kernel_size"]))
        module.load_state_dict(state_dict, strict=True)
        members.append(model.NeuralModel(module))
    return members


def _calibration_cells(stage: dict[str, Any], run_dir: Path,
                       streams: Sequence[dict[str, Any]], data: model.AllowedDataset,
                       cfg: Any) -> list[model.Cell]:
    cells: list[model.Cell] = []
    by_cell: dict[str, list[dict[str, Any]]] = {}
    for stream in streams:
        records = [_state(run_dir / "rollouts" / stream["rollout_id"] / f"{1100 + index}ms", cfg)
                   for index in range(35)]
        states = np.asarray([[row[key] for key in ("r_geo_m", "z_geo_m", "ip_a")] for row in records], dtype=np.float64)
        currents_abs = np.asarray([[float(value) for value in row["actual_current_decimal_a_tsc"]]
                                   for row in records], dtype=np.float64)
        issued = np.asarray([model._float_target(target) - data.q0 for target in stream["targets"]], dtype=np.float64)
        if not np.array_equal(currents_abs[0], data.source_current):
            raise InputIntegrityError(f"source current mismatch: {stream['rollout_id']}")
        by_cell.setdefault(stream["cell_id"], []).append({
            "stream": stream, "states": states,
            "currents": currents_abs - data.source_current, "issued": issued,
        })
    if len(by_cell) != 20:
        raise InputIntegrityError("calibration cell count changed")
    for cell_id, rows in sorted(by_cell.items()):
        if len(rows) != 2:
            raise InputIntegrityError(f"replay count mismatch: {cell_id}")
        for key in ("states", "currents", "issued"):
            if not np.array_equal(rows[0][key], rows[1][key]):
                raise InputIntegrityError(f"non-exact replay: {cell_id}:{key}")
        stream = rows[0]["stream"]
        cells.append(model.Cell(
            cell_id=cell_id, context_id=stream["group_id"], cell_kind=stream["cell_kind"],
            states=rows[0]["states"], currents=rows[0]["currents"], issued=rows[0]["issued"],
            direction_id=stream["direction_id"], sign=stream["sign"],
            duration=int(stream["probe_duration_issues"]),
        ))
    return cells


def calibration_metrics(stage: dict[str, Any], cells: Sequence[model.Cell],
                        data: model.AllowedDataset, members: Sequence[model.NeuralModel]) -> dict[str, Any]:
    predictions: dict[str, np.ndarray] = {}
    for cell in cells:
        values = np.asarray([member.recursive(cell, data, origin=16) for member in members], dtype=np.float64)
        predictions[cell.cell_id] = np.mean(values, axis=0)
    group_rows = []
    true_responses = []
    predicted_responses = []
    positive = 0
    for group_id in [f"c{i:02d}" for i in range(10)]:
        baseline = next(cell for cell in cells if cell.context_id == group_id and cell.cell_kind == "baseline")
        probe = next(cell for cell in cells if cell.context_id == group_id and cell.cell_kind == "probe")
        absolute = np.concatenate([
            np.abs(predictions[baseline.cell_id] - baseline.states[17:35]),
            np.abs(predictions[probe.cell_id] - probe.states[17:35]),
        ], axis=0)
        absolute_score = np.max(absolute, axis=0)
        true_response = probe.states[23:35] - baseline.states[23:35]
        predicted_response = predictions[probe.cell_id][6:] - predictions[baseline.cell_id][6:]
        response_error = np.abs(predicted_response - true_response)
        response_score = np.max(response_error, axis=0)
        norms = np.linalg.norm(true_response[:, :2], axis=1)
        peak = int(np.argmax(norms))
        left = true_response[peak, :2]
        right = predicted_response[peak, :2]
        denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
        cosine = float(np.dot(left, right) / denominator) if denominator > 0 else -1.0
        positive += int(cosine > 0)
        true_responses.append(true_response / data.response_scale)
        predicted_responses.append(predicted_response / data.response_scale)
        group_rows.append({
            "group_id": group_id,
            "absolute_recursive_group_max": absolute_score.tolist(),
            "paired_response_group_max": response_score.tolist(),
            "peak_direction_cosine": cosine,
        })
    absolute_scores = np.asarray([row["absolute_recursive_group_max"] for row in group_rows])
    response_scores = np.asarray([row["paired_response_group_max"] for row in group_rows])
    order = int(stage["calibration"]["finite_sample_order_index_one_based"])
    absolute_width = np.sort(absolute_scores, axis=0)[order - 1]
    response_width = np.sort(response_scores, axis=0)[order - 1]
    truth = np.concatenate(true_responses, axis=0)
    prediction = np.concatenate(predicted_responses, axis=0)
    response_nrmse = float(np.linalg.norm(prediction - truth) / np.linalg.norm(truth))
    caps_abs = np.asarray(stage["calibration"]["absolute_width_caps"], dtype=float)
    caps_response = np.asarray(stage["calibration"]["paired_response_width_caps"], dtype=float)
    gates = {
        "absolute_width": bool(np.all(absolute_width <= caps_abs)),
        "paired_response_width": bool(np.all(response_width <= caps_response)),
        "matched_response_nrmse": response_nrmse < float(stage["calibration"]["maximum_matched_response_nrmse"]),
        "peak_direction": positive >= int(stage["calibration"]["minimum_positive_peak_cosine_groups"]),
    }
    return {
        "group_scores": group_rows,
        "nominal_group_coverage": stage["calibration"]["nominal_group_coverage"],
        "finite_sample_order_index_one_based": order,
        "simultaneous_absolute_recursive_half_width": absolute_width.tolist(),
        "simultaneous_paired_response_half_width": response_width.tolist(),
        "matched_response_nrmse": response_nrmse,
        "positive_peak_direction_groups": positive,
        "gate_passes": gates,
        "passed": all(gates.values()),
    }


def calibrate(stage_path: Path, source_revision: str, run_dir: Path, output: Path) -> dict[str, Any]:
    stage, cfg, targets, id2c1_stage = load(stage_path)
    run_dir = inside_root(run_dir, "ID2H1 run")
    output = inside_root(output, "ID2H1 calibration output")
    primary = _read_json(run_dir / "result.json")
    independent = _read_json(run_dir / "independent_raw_audit.json")
    if (not primary.get("passed") or primary.get("route") != stage["routes"]["data_pass"]
            or not independent.get("audit_passed")
            or independent.get("primary_sha256") != sha256(run_dir / "result.json")):
        raise InputIntegrityError("fresh calibration data are not accepted")
    if output.exists():
        raise FileExistsError(str(output))
    development_stage = model.load_stage(ROOT / stage["evidence"]["id2g1r1_config"]["path"])
    data = model.extract_dataset(development_stage)
    streams = campaign_streams(stage, cfg, targets, id2c1_stage)
    cells = _calibration_cells(stage, run_dir, streams, data, cfg)
    members = _load_tcn(stage)
    metrics = calibration_metrics(stage, cells, data, members)
    route = stage["routes"]["pass"] if metrics["passed"] else stage["routes"]["calibration_fail"]
    result = {
        "schema_version": CALIBRATION_SCHEMA,
        "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "fresh_data_primary_sha256": sha256(run_dir / "result.json"),
        "fresh_data_independent_sha256": sha256(run_dir / "independent_raw_audit.json"),
        "selected_model_sha256": stage["evidence"]["selected_model"]["sha256"],
        "selected_candidate": "causal_tcn",
        "models_fit_retrained_tuned_or_selected": 0,
        "id2c2_records_read": 0,
        "blind_holdout_records_read": 0,
        "tsc_calls": 0,
        "plant_advances": 0,
        "calibration_metrics": metrics,
        "passed": metrics["passed"],
        "route": route,
        "blind_whole_history_holdout_design_authorized": metrics["passed"],
        "controller_authorized": False,
        "claim_boundary": stage["claim_boundary"],
    }
    write_new(output, result)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("offline", "run", "calibrate"))
    parser.add_argument("--stage-config", type=Path, default=CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.mode == "offline":
            result = offline(args.stage_config, args.source_revision)
            write_new(args.output, result)
        elif args.mode == "run":
            result = run(args.stage_config, args.source_revision, args.output)
        else:
            if args.run_dir is None:
                raise InputIntegrityError("--run-dir is required for calibration")
            result = calibrate(args.stage_config, args.source_revision, args.run_dir, args.output)
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        return 0 if result["passed"] else 2
    except Exception as exc:
        failure = {
            "schema_version": CALIBRATION_SCHEMA if args.mode == "calibrate" else SCHEMA,
            "source_revision": args.source_revision,
            "stage_config_sha256": CONFIG_SHA256,
            "passed": False,
            "route": "ONE_MS_ID2H1_CALIBRATION_INPUT_FAIL_NO_WIDTHS" if args.mode == "calibrate"
                     else "ONE_MS_ID2H1_OFFLINE_OR_INPUT_FAIL_NO_TSC",
            "failure_type": type(exc).__name__,
            "failure": str(exc),
            "models_fit_retrained_tuned_or_selected": 0,
        }
        try:
            if args.mode == "calibrate":
                write_new(args.output, failure)
            elif args.mode == "run":
                out = inside_root(args.output, "failure output")
                out.mkdir(parents=True, exist_ok=False)
                write_new(out / "result.json", failure)
            else:
                write_new(args.output, failure)
        except Exception:
            pass
        print(json.dumps(failure, indent=2, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
