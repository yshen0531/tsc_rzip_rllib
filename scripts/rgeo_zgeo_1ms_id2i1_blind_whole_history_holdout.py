#!/usr/bin/env python3
"""Run and evaluate the blind ID-2I1 whole-history holdout."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_id0_vector_tail import (  # noqa: E402
    InputIntegrityError,
    inside_root,
    raw_inventory,
    sha256,
    write_new,
)
from scripts.rgeo_zgeo_1ms_id0_vector_tail_independent import _state  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2g1_grouped_causal_model as model  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2h1_whole_history_calibration as h1  # noqa: E402


CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2i1_blind_whole_history_holdout.json"
CONFIG_SHA256 = "3af0c26743d0a027f33b3efd3b237cb776c0fbe31988fa7d3128babe32d64e8f"
SCHEMA = "rgeo-zgeo-1ms-id2i1-blind-whole-history-holdout-result-v1"
EVALUATION_SCHEMA = "rgeo-zgeo-1ms-id2i1-blind-whole-history-evaluation-v1"


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
        "schema_version": "rgeo-zgeo-1ms-id2i1-blind-whole-history-holdout-v1",
        "identity": "rgeo-zgeo-1ms-id2i1-blind-whole-history-holdout-v1",
        "stage": "ID-2I1",
        "takeover_time_ms": 1100,
        "control_period_ms": 1,
        "horizon_steps": 34,
        "whole_history_groups": 8,
        "cells_per_group": 2,
        "replays_per_cell": 2,
        "maximum_rollouts": 32,
        "maximum_reset_calls": 32,
        "maximum_advance_attempts": 1088,
        "maximum_gotsc_calls": 1088,
        "maximum_verified_plant_advances": 1088,
        "maximum_retained_states": 1120,
        "retry_after_any_advance_attempt": "forbidden",
        "data_use": "blind_evaluation_only",
        "model_fit_retrain_tune_select_or_recalibrate_use": "forbidden",
        "id2c2_records_read": 0,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise InputIntegrityError(f"frozen field mismatch: {key}")
    groups = stage.get("groups")
    if not isinstance(groups, list) or len(groups) != 8:
        raise InputIntegrityError("eight blind groups required")
    if [row.get("group_id") for row in groups] != [f"h{i:02d}" for i in range(8)]:
        raise InputIntegrityError("blind group identities changed")
    for row in groups:
        probe = row.get("probe", {})
        if (probe.get("issue_step") != 25 or probe.get("direction") not in ("p04", "p07")
                or probe.get("sign") not in ("plus", "minus")
                or probe.get("duration_issues") not in (1, 2, 3)):
            raise InputIntegrityError("blind probe matrix changed")
        for event in row.get("conditioners", []):
            if (event.get("direction") not in ("p04", "p07")
                    or event.get("sign") not in ("plus", "minus")
                    or event.get("issue_step") not in (18, 21)
                    or event.get("duration_issues") not in (1, 2)):
                raise InputIntegrityError("blind conditioner matrix changed")
    holdout = stage.get("holdout", {})
    required = {
        "selected_candidate": "causal_tcn",
        "member_seeds": [11, 29, 47],
        "recursive_origin_state": 16,
        "absolute_error_state_range_inclusive": [17, 34],
        "paired_response_state_range_inclusive": [26, 34],
        "statistical_unit": "whole_blind_history_group",
        "group_count": 8,
        "frozen_absolute_recursive_half_width": [0.0005936422508353578, 0.00024051138515601006, 24.0476938080501],
        "frozen_paired_response_half_width": [0.0006950692585707685, 0.00023825926428221178, 7.717859491567651],
        "minimum_joint_contained_groups": 7,
        "absolute_catastrophic_caps": [0.0015, 0.0015, 75.0],
        "paired_response_catastrophic_caps": [0.001, 0.001, 50.0],
        "maximum_matched_response_nrmse": 1.0,
        "minimum_positive_peak_cosine_groups": 7,
        "future_actual_current_in_prediction": "forbidden",
        "model_width_or_feature_update": "forbidden",
    }
    if holdout != required:
        raise InputIntegrityError("blind holdout contract changed")
    if stage.get("semantic_artifacts") != ["inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv"]:
        raise InputIntegrityError("semantic artifact contract changed")
    if stage.get("diagnostic_artifacts") != ["sprsina"]:
        raise InputIntegrityError("diagnostic artifact contract changed")


def load(stage_path: Path = CONFIG) -> tuple[dict[str, Any], Any, dict[str, Any], dict[str, Any]]:
    stage_path = inside_root(stage_path, "ID2I1 config")
    if sha256(stage_path) != CONFIG_SHA256:
        raise InputIntegrityError("ID2I1 config hash mismatch")
    stage = _read_json(stage_path)
    _require_stage(stage)
    base = inside_root(ROOT / stage["base_tsc_config"], "base TSC config")
    if sha256(base) != stage["evidence"]["base_tsc_config_sha256"]:
        raise InputIntegrityError("base TSC config hash mismatch")
    for key in ("design", "id2f1r1_config", "id2g1r1_config", "selected_model",
                "id2h1_result", "id2h1_independent_raw", "id2h1_calibration",
                "id2h1_independent_calibration"):
        item = stage["evidence"][key]
        path = inside_root(ROOT / item["path"], key)
        if not path.is_file() or sha256(path) != item["sha256"]:
            raise InputIntegrityError(f"evidence mismatch: {key}")
    result = _read_json(ROOT / stage["evidence"]["id2h1_result"]["path"])
    raw_audit = _read_json(ROOT / stage["evidence"]["id2h1_independent_raw"]["path"])
    calibration = _read_json(ROOT / stage["evidence"]["id2h1_calibration"]["path"])
    calibration_audit = _read_json(ROOT / stage["evidence"]["id2h1_independent_calibration"]["path"])
    if (not result.get("passed")
            or result.get("route") != stage["evidence"]["id2h1_result"]["required_route"]
            or not raw_audit.get("audit_passed")):
        raise InputIntegrityError("ID2H1 raw evidence is not accepted")
    if (not calibration.get("passed")
            or calibration.get("route") != stage["evidence"]["id2h1_calibration"]["required_route"]
            or not calibration_audit.get("audit_passed")
            or calibration_audit.get("maximum_numeric_difference") != 0.0):
        raise InputIntegrityError("ID2H1 calibration is not accepted")
    metrics = calibration.get("calibration_metrics", {})
    if (metrics.get("simultaneous_absolute_recursive_half_width")
            != stage["holdout"]["frozen_absolute_recursive_half_width"]
            or metrics.get("simultaneous_paired_response_half_width")
            != stage["holdout"]["frozen_paired_response_half_width"]):
        raise InputIntegrityError("ID2H1 widths changed")
    h1_stage, cfg, targets, id2c1_stage = h1.load(h1.CONFIG)
    if h1_stage["evidence"]["selected_model"]["sha256"] != stage["evidence"]["selected_model"]["sha256"]:
        raise InputIntegrityError("selected model identity changed")
    return stage, cfg, targets, id2c1_stage


def campaign_streams(stage: dict[str, Any], cfg: Any, targets: dict[str, Any],
                     id2c1_stage: dict[str, Any]) -> list[dict[str, Any]]:
    return h1.campaign_streams(stage, cfg, targets, id2c1_stage)


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


def run(stage_path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = inside_root(output, "ID2I1 run")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    stage, cfg, targets, id2c1_stage = load(stage_path)
    storage = h1._storage(stage, output)
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
                  "blind_holdout_data_eligible": False, "models_fit_or_updated": 0}
        write_new(output / "result.json", result)
        return result
    cfg.run_root = output / "rollouts"
    runtime = dict(stage)
    runtime["empirical_exploration"] = dict(stage["empirical_exploration"])
    runtime["empirical_exploration"]["inner_pulse_issue_clearance"] = stage["empirical_exploration"]["inner_probe_issue_clearance"]
    streams = campaign_streams(stage, cfg, targets, id2c1_stage)
    rows: list[dict[str, Any]] = []
    for stream in streams:
        row = h1.one_rollout(cfg, runtime, stream)
        row["schema_version"] = SCHEMA
        row["source_revision"] = source_revision
        rows.append(row)
        write_new(output / f"{row['rollout_id']}.json", row)
        if not row["passed"]:
            break
    inventory = raw_inventory(output, rows, stage)
    raw_ok = not inventory["missing_required_artifacts"]
    checks = h1._repeatability(rows, stage) if len(rows) == 32 and all(row["passed"] for row in rows) else []
    execution_ok = len(rows) == 32 and all(row["passed"] for row in rows)
    repeatable = len(checks) == 16 and all(row["passed"] for row in checks)
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
        "blind_holdout_data_eligible": passed,
        "model_fit_retrain_tune_select_or_recalibrate_use": "forbidden",
        "controller_safety_data_eligible": False,
        "models_fit_or_updated": 0,
        "id2c2_records_read": 0,
        "claim_boundary": stage["claim_boundary"],
    }
    write_new(output / "result.json", result)
    return result


def _holdout_cells(stage: dict[str, Any], run_dir: Path,
                   streams: Sequence[dict[str, Any]], data: model.AllowedDataset,
                   cfg: Any) -> list[model.Cell]:
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
    if len(by_cell) != 16:
        raise InputIntegrityError("blind cell count changed")
    cells: list[model.Cell] = []
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


def holdout_metrics(stage: dict[str, Any], cells: Sequence[model.Cell],
                    data: model.AllowedDataset,
                    members: Sequence[model.NeuralModel]) -> dict[str, Any]:
    predictions: dict[str, np.ndarray] = {}
    for cell in cells:
        values = np.asarray([member.recursive(cell, data, origin=16) for member in members], dtype=np.float64)
        predictions[cell.cell_id] = np.mean(values, axis=0)
    contract = stage["holdout"]
    abs_width = np.asarray(contract["frozen_absolute_recursive_half_width"], dtype=float)
    pair_width = np.asarray(contract["frozen_paired_response_half_width"], dtype=float)
    abs_caps = np.asarray(contract["absolute_catastrophic_caps"], dtype=float)
    pair_caps = np.asarray(contract["paired_response_catastrophic_caps"], dtype=float)
    group_rows = []
    true_responses = []
    predicted_responses = []
    joint = 0
    positive = 0
    for group_id in [f"h{i:02d}" for i in range(8)]:
        baseline = next(cell for cell in cells if cell.context_id == group_id and cell.cell_kind == "baseline")
        probe = next(cell for cell in cells if cell.context_id == group_id and cell.cell_kind == "probe")
        absolute = np.concatenate([
            np.abs(predictions[baseline.cell_id] - baseline.states[17:35]),
            np.abs(predictions[probe.cell_id] - probe.states[17:35]),
        ], axis=0)
        absolute_score = np.max(absolute, axis=0)
        true_response = probe.states[26:35] - baseline.states[26:35]
        predicted_response = predictions[probe.cell_id][9:] - predictions[baseline.cell_id][9:]
        response_score = np.max(np.abs(predicted_response - true_response), axis=0)
        absolute_contained = bool(np.all(absolute_score <= abs_width))
        response_contained = bool(np.all(response_score <= pair_width))
        joint_contained = absolute_contained and response_contained
        joint += int(joint_contained)
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
            "absolute_width_contained": absolute_contained,
            "paired_response_width_contained": response_contained,
            "joint_width_contained": joint_contained,
            "peak_direction_cosine": cosine,
        })
    truth = np.concatenate(true_responses, axis=0)
    prediction = np.concatenate(predicted_responses, axis=0)
    response_nrmse = float(np.linalg.norm(prediction - truth) / np.linalg.norm(truth))
    all_abs = np.asarray([row["absolute_recursive_group_max"] for row in group_rows])
    all_pair = np.asarray([row["paired_response_group_max"] for row in group_rows])
    gates = {
        "joint_calibrated_width_coverage": joint >= int(contract["minimum_joint_contained_groups"]),
        "absolute_catastrophic_cap": bool(np.all(all_abs <= abs_caps)),
        "paired_response_catastrophic_cap": bool(np.all(all_pair <= pair_caps)),
        "matched_response_nrmse": response_nrmse < float(contract["maximum_matched_response_nrmse"]),
        "peak_direction": positive >= int(contract["minimum_positive_peak_cosine_groups"]),
    }
    return {
        "group_scores": group_rows,
        "frozen_absolute_recursive_half_width": abs_width.tolist(),
        "frozen_paired_response_half_width": pair_width.tolist(),
        "joint_width_contained_groups": joint,
        "matched_response_nrmse": response_nrmse,
        "positive_peak_direction_groups": positive,
        "gate_passes": gates,
        "passed": all(gates.values()),
    }


def evaluate(stage_path: Path, source_revision: str, run_dir: Path, output: Path) -> dict[str, Any]:
    stage, cfg, targets, id2c1_stage = load(stage_path)
    run_dir = inside_root(run_dir, "ID2I1 run")
    output = inside_root(output, "ID2I1 evaluation output")
    primary = _read_json(run_dir / "result.json")
    independent = _read_json(run_dir / "independent_raw_audit.json")
    if (not primary.get("passed") or primary.get("route") != stage["routes"]["data_pass"]
            or not independent.get("audit_passed")
            or independent.get("primary_sha256") != sha256(run_dir / "result.json")):
        raise InputIntegrityError("blind holdout data are not accepted")
    if output.exists():
        raise FileExistsError(str(output))
    h1_stage, _, _, _ = h1.load(h1.CONFIG)
    development_stage = model.load_stage(ROOT / stage["evidence"]["id2g1r1_config"]["path"])
    data = model.extract_dataset(development_stage)
    streams = campaign_streams(stage, cfg, targets, id2c1_stage)
    cells = _holdout_cells(stage, run_dir, streams, data, cfg)
    members = h1._load_tcn(h1_stage)
    metrics = holdout_metrics(stage, cells, data, members)
    route = stage["routes"]["pass"] if metrics["passed"] else stage["routes"]["holdout_fail"]
    result = {
        "schema_version": EVALUATION_SCHEMA,
        "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "blind_data_primary_sha256": sha256(run_dir / "result.json"),
        "blind_data_independent_sha256": sha256(run_dir / "independent_raw_audit.json"),
        "selected_model_sha256": stage["evidence"]["selected_model"]["sha256"],
        "id2h1_calibration_sha256": stage["evidence"]["id2h1_calibration"]["sha256"],
        "models_fit_retrained_tuned_selected_or_recalibrated": 0,
        "id2c2_records_read": 0,
        "tsc_calls": 0,
        "plant_advances": 0,
        "holdout_metrics": metrics,
        "passed": metrics["passed"],
        "route": route,
        "controller_safety_design_authorized": metrics["passed"],
        "controller_authorized": False,
        "claim_boundary": stage["claim_boundary"],
    }
    write_new(output, result)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("offline", "run", "evaluate"))
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
                raise InputIntegrityError("--run-dir is required for evaluation")
            result = evaluate(args.stage_config, args.source_revision, args.run_dir, args.output)
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        return 0 if result["passed"] else 2
    except Exception as exc:
        failure = {
            "schema_version": EVALUATION_SCHEMA if args.mode == "evaluate" else SCHEMA,
            "source_revision": args.source_revision,
            "stage_config_sha256": CONFIG_SHA256,
            "passed": False,
            "route": "ONE_MS_ID2I1_HOLDOUT_INPUT_FAIL_NO_VERDICT" if args.mode == "evaluate"
                     else "ONE_MS_ID2I1_OFFLINE_OR_INPUT_FAIL_NO_TSC",
            "failure_type": type(exc).__name__,
            "failure": str(exc),
            "models_fit_retrained_tuned_selected_or_recalibrated": 0,
        }
        try:
            if args.mode == "evaluate":
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
