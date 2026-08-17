#!/usr/bin/env python3
"""Collect diagnostic ID2I1 replications and attribute the frozen TCN failure."""

from __future__ import annotations

import argparse
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
    InputIntegrityError, inside_root, raw_inventory, sha256, write_new,
)
from scripts.rgeo_zgeo_1ms_id0_vector_tail_independent import _state  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2g1_grouped_causal_model as model  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2h1_whole_history_calibration as h1  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2i1_blind_whole_history_holdout as i1  # noqa: E402


CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2j0_post_holdout_attribution.json"
CONFIG_SHA256 = "bae5685d6ead9625343584472d666fb4b140168e1c5296470efe34c8bd4e1e7c"
RUN_SCHEMA = "rgeo-zgeo-1ms-id2j0-diagnostic-reobservation-result-v1"
ATTRIBUTION_SCHEMA = "rgeo-zgeo-1ms-id2j0-post-holdout-attribution-result-v1"


def _json(path: Path) -> dict[str, Any]:
    path = inside_root(path, "JSON")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise InputIntegrityError(f"object required: {path.relative_to(ROOT)}")
    return value


def _require_stage(stage: dict[str, Any]) -> None:
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2j0-post-holdout-attribution-v1",
        "identity": "rgeo-zgeo-1ms-id2j0-diagnostic-reobservation-v1",
        "stage": "ID-2J0", "takeover_time_ms": 1100, "control_period_ms": 1,
        "horizon_steps": 34, "whole_history_groups": 8, "cells_per_group": 2,
        "replays_per_cell": 1, "maximum_rollouts": 16, "maximum_reset_calls": 16,
        "maximum_advance_attempts": 544, "maximum_gotsc_calls": 544,
        "maximum_verified_plant_advances": 544, "maximum_retained_states": 560,
        "retry_after_any_advance_attempt": "forbidden",
        "data_use": "post_holdout_attribution_and_future_design_only",
        "blind_holdout_or_calibration_use": "forbidden",
        "model_fit_retrain_tune_select_or_recalibrate_use": "forbidden",
        "id2c2_records_read": 0,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise InputIntegrityError(f"frozen field mismatch: {key}")
    if [row.get("group_id") for row in stage.get("groups", [])] != [f"h{x:02d}" for x in range(8)]:
        raise InputIntegrityError("history group matrix changed")
    analysis = stage.get("analysis", {})
    required = {
        "selected_candidate": "causal_tcn", "member_seeds": [11, 29, 47],
        "recursive_origin_state": 16, "probe_issue_step": 25,
        "probe_first_effect_state": 26, "absolute_state_range_inclusive": [17, 34],
        "paired_response_state_range_inclusive": [26, 34],
        "truth_recenter_periods_ms": [1, 2, 4],
        "free_recursion_label": "free_from_state16", "causal_support_window_steps": 16,
        "support_embeddings": ["full_tcn_features", "without_absolute_time", "action_history_only"],
        "one_step_p95_caps": [0.0005, 0.0005, 50.0],
        "maximum_one_step_matched_response_nrmse": 1.0,
        "minimum_positive_one_step_peak_cosine_groups": 7,
        "material_nrmse_improvement_fraction": 0.25,
        "maximum_expected_next_current_residual_a": 0.00002,
        "future_actual_current_in_prediction": "forbidden", "model_or_width_update": "forbidden",
    }
    if analysis != required:
        raise InputIntegrityError("analysis contract changed")
    if stage.get("semantic_artifacts") != ["inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv"]:
        raise InputIntegrityError("semantic artifacts changed")
    if stage.get("diagnostic_artifacts") != ["sprsina"]:
        raise InputIntegrityError("diagnostic artifacts changed")


def load(path: Path = CONFIG) -> tuple[dict[str, Any], Any, dict[str, Any], dict[str, Any]]:
    path = inside_root(path, "ID2J0 config")
    if sha256(path) != CONFIG_SHA256:
        raise InputIntegrityError("ID2J0 config hash mismatch")
    stage = _json(path)
    _require_stage(stage)
    for name, item in stage["evidence"].items():
        evidence = inside_root(ROOT / item["path"], name)
        if not evidence.is_file() or sha256(evidence) != item["sha256"]:
            raise InputIntegrityError(f"evidence mismatch: {name}")
    old = _json(ROOT / stage["evidence"]["id2i1_evaluation"]["path"])
    old_independent = _json(ROOT / stage["evidence"]["id2i1_independent_evaluation"]["path"])
    if (old.get("route") != stage["evidence"]["id2i1_evaluation"]["required_route"]
            or old.get("passed") is not False or not old_independent.get("audit_passed")):
        raise InputIntegrityError("final ID2I1 failure identity changed")
    _, cfg, targets, id2c1_stage = i1.load(ROOT / stage["evidence"]["id2i1_config"]["path"])
    return stage, cfg, targets, id2c1_stage


def streams(stage: dict[str, Any], cfg: Any, targets: dict[str, Any], id2c1_stage: dict[str, Any]) -> list[dict[str, Any]]:
    rows = h1.campaign_streams(stage, cfg, targets, id2c1_stage)
    if len(rows) != 16 or any(row["replay_index"] != 0 for row in rows):
        raise InputIntegrityError("single-replay stream identity changed")
    return rows


def offline(path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    action_rows: list[dict[str, Any]] = []
    try:
        stage, cfg, targets, id2c1_stage = load(path)
        rows = streams(stage, cfg, targets, id2c1_stage)
        for row in rows:
            if len(row["targets"]) != 34 or len(row["actions"]) != 34:
                raise InputIntegrityError("stream length changed")
            if any(float(action["maximum_issued_delta_a"]) > 0.3 for action in row["actions"]):
                raise InputIntegrityError("issued slew exceeds 0.3 A")
        action_rows = [{k: v for k, v in row.items() if k != "targets"} for row in rows]
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {"schema_version": RUN_SCHEMA, "kind": "offline_preflight",
            "source_revision": source_revision, "stage_config_sha256": sha256(path),
            "passed": not failures, "failures": failures, "action_streams": action_rows,
            "reset_calls": 0, "advance_attempts": 0, "plant_advance_gotsc_calls": 0,
            "verified_plant_advances": 0, "models_fit_or_updated": 0, "id2c2_records_read": 0}


def _storage(stage: dict[str, Any], output: Path) -> dict[str, Any]:
    free = shutil.disk_usage(output.parent).free
    gate = stage["storage_gate"]
    estimate = int(gate["maximum_estimated_raw_bytes"])
    return {"free_bytes_before_run": free, "estimated_raw_bytes": estimate,
            "estimated_free_bytes_after_run": free - estimate,
            "passed": free >= int(gate["minimum_free_bytes_before_run"])
            and free - estimate >= int(gate["minimum_free_bytes_after_estimate"])}


def _matched_prefix(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    by_group: dict[str, dict[str, dict[str, Any]]] = {}
    for row in rows:
        by_group.setdefault(row["group_id"], {})[row["cell_kind"]] = row
    checks = []
    for group in sorted(by_group):
        pair = by_group[group]
        failures = []
        if set(pair) != {"baseline", "probe"}:
            failures.append("CELL_SET")
        else:
            baseline, probe = pair["baseline"], pair["probe"]
            for index in range(26):
                left, right = baseline["states"][index], probe["states"][index]
                for key in ("r_geo_m", "z_geo_m", "r_mid_m", "ip_a",
                            "actual_current_decimal_a_tsc", "wire_current_a"):
                    if left[key] != right[key]:
                        failures.append(f"STATE:{index}:{key}")
                # The state-25 folder's inputa is rewritten with outgoing issue 25,
                # which is exactly where baseline and probe intentionally diverge.
                # Physical state 25 must still match; semantic files are compared
                # only before that outgoing action is serialized.
                if index < 25:
                    for name in ("inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv"):
                        if left["artifact_sha256"].get(name) != right["artifact_sha256"].get(name):
                            failures.append(f"ARTIFACT:{index}:{name}")
            for issue in range(25):
                if baseline["actions"][issue]["expected_card15_fields"] != probe["actions"][issue]["expected_card15_fields"]:
                    failures.append(f"ACTION:{issue}")
        checks.append({"group_id": group, "passed": not failures,
                       "failures": list(dict.fromkeys(failures))})
    return checks


def run(path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = inside_root(output, "ID2J0 output")
    if output.exists():
        raise FileExistsError(str(output))
    stage, cfg, targets, id2c1_stage = load(path)
    storage = _storage(stage, output)
    output.mkdir(parents=True)
    preflight = offline(path, source_revision)
    write_new(output / "offline_preflight.json", preflight)
    if not storage["passed"] or not preflight["passed"]:
        route = stage["routes"]["storage_fail" if not storage["passed"] else "offline_or_input_fail"]
        result = {"schema_version": RUN_SCHEMA, "source_revision": source_revision,
                  "stage_config_sha256": CONFIG_SHA256, "passed": False, "route": route,
                  "storage_gate": storage, "reasons": preflight["failures"],
                  "rollouts_completed": 0, "reset_calls": 0, "advance_attempts": 0,
                  "plant_advance_gotsc_calls": 0, "verified_plant_advances": 0,
                  "models_fit_or_updated": 0}
        write_new(output / "result.json", result)
        return result
    cfg.run_root = output / "rollouts"
    runtime = dict(stage)
    runtime["empirical_exploration"] = dict(stage["empirical_exploration"])
    runtime["empirical_exploration"]["inner_pulse_issue_clearance"] = stage["empirical_exploration"]["inner_probe_issue_clearance"]
    compact = []
    for stream in streams(stage, cfg, targets, id2c1_stage):
        row = h1.one_rollout(cfg, runtime, stream)
        row.update({"schema_version": RUN_SCHEMA, "source_revision": source_revision})
        compact.append(row)
        write_new(output / f"{row['rollout_id']}.json", row)
        if not row["passed"]:
            break
    inventory = raw_inventory(output, compact, stage)
    prefix = _matched_prefix(compact) if len(compact) == 16 and all(row["passed"] for row in compact) else []
    execution = len(compact) == 16 and all(row["passed"] for row in compact)
    raw_ok = not inventory["missing_required_artifacts"]
    prefix_ok = len(prefix) == 8 and all(row["passed"] for row in prefix)
    if not execution:
        route = stage["routes"]["execution_or_interface_fail"]
    elif not raw_ok:
        route = stage["routes"]["raw_integrity_fail"]
    elif not prefix_ok:
        route = stage["routes"]["prefix_fail"]
    else:
        route = stage["routes"]["data_pass"]
    passed = route == stage["routes"]["data_pass"]
    result = {"schema_version": RUN_SCHEMA, "source_revision": source_revision,
              "stage_config_sha256": CONFIG_SHA256, "passed": passed, "route": route,
              "storage_gate": storage, "matched_prefix_checks": prefix,
              "rollouts_completed": len(compact), "unique_cells_completed": len({x["cell_id"] for x in compact}),
              "whole_history_groups_completed": len({x["group_id"] for x in compact}),
              "reset_calls": sum(x["reset_calls"] for x in compact),
              "advance_attempts": sum(x["advance_attempts"] for x in compact),
              "plant_advance_gotsc_calls": sum(x["plant_advance_gotsc_calls"] for x in compact),
              "verified_plant_advances": sum(x["verified_plant_advances"] for x in compact),
              **inventory, "models_fit_or_updated": 0, "id2c2_records_read": 0,
              "blind_holdout_or_calibration_use": "forbidden", "claim_boundary": stage["claim_boundary"]}
    write_new(output / "result.json", result)
    return result


def _cells(stage: dict[str, Any], run_dir: Path, rows: Sequence[dict[str, Any]],
           data: model.AllowedDataset, cfg: Any) -> list[model.Cell]:
    cells = []
    for stream in rows:
        records = [_state(run_dir / "rollouts" / stream["rollout_id"] / f"{1100 + k}ms", cfg)
                   for k in range(35)]
        states = np.asarray([[r[x] for x in ("r_geo_m", "z_geo_m", "ip_a")] for r in records], dtype=float)
        currents = np.asarray([[float(v) for v in r["actual_current_decimal_a_tsc"]] for r in records])
        issued = np.asarray([model._float_target(target) - data.q0 for target in stream["targets"]])
        cells.append(model.Cell(stream["cell_id"], stream["group_id"], stream["cell_kind"], states,
                                currents - data.source_current, issued, stream["direction_id"],
                                stream["sign"], int(stream["probe_duration_issues"])))
    if len(cells) != 16:
        raise InputIntegrityError("sixteen diagnostic cells required")
    return cells


def _member_segment(member: model.NeuralModel, cell: model.Cell, data: model.AllowedDataset,
                    start: int, stop: int) -> np.ndarray:
    states, currents = cell.states.copy(), cell.currents.copy()
    frames = [model.frame(cell, issue, data) for issue in range(start)]
    for issue in range(start, stop):
        frames.append(model.frame(cell, issue, data, current_state=states[issue],
                                  previous_state=states[max(0, issue - 1)],
                                  current_coordinate=currents[issue], issued_coordinate=cell.issued[issue]))
        sequence = torch.tensor(np.asarray(frames)[None, :, :], dtype=torch.float32)
        with torch.no_grad():
            delta = member.module(sequence)[0, -1].cpu().numpy().astype(float)
        states[issue + 1] = states[issue] + delta * data.state_scale
        currents[issue + 1] = cell.issued[issue] + data.q0 - data.source_current
    return states[start + 1:stop + 1]


def recentered(member: model.NeuralModel, cell: model.Cell, data: model.AllowedDataset,
               period: int, origin: int = 16) -> np.ndarray:
    predictions = []
    for start in range(origin, 34, period):
        stop = min(34, start + period)
        predictions.append(_member_segment(member, cell, data, start, stop))
    return np.concatenate(predictions, axis=0)


def _mode_predictions(members: Sequence[model.NeuralModel], cells: Sequence[model.Cell],
                      data: model.AllowedDataset, period: int | None) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    means, all_members = {}, {}
    for cell in cells:
        values = np.asarray([member.recursive(cell, data, origin=16) if period is None
                             else recentered(member, cell, data, period) for member in members])
        means[cell.cell_id], all_members[cell.cell_id] = np.mean(values, axis=0), values
    return means, all_members


def _mode_metrics(stage: dict[str, Any], cells: Sequence[model.Cell], data: model.AllowedDataset,
                  predictions: dict[str, np.ndarray], members: dict[str, np.ndarray]) -> dict[str, Any]:
    errors = np.concatenate([predictions[c.cell_id] - c.states[17:35] for c in cells])
    groups, truth_rows, prediction_rows, positive = [], [], [], 0
    for group_id in [f"h{x:02d}" for x in range(8)]:
        baseline = next(c for c in cells if c.context_id == group_id and c.cell_kind == "baseline")
        probe = next(c for c in cells if c.context_id == group_id and c.cell_kind == "probe")
        truth = probe.states[26:35] - baseline.states[26:35]
        prediction = predictions[probe.cell_id][9:] - predictions[baseline.cell_id][9:]
        truth_rows.append(truth / data.response_scale)
        prediction_rows.append(prediction / data.response_scale)
        peak = int(np.argmax(np.linalg.norm(truth[:, :2], axis=1)))
        denom = float(np.linalg.norm(truth[peak, :2]) * np.linalg.norm(prediction[peak, :2]))
        cosine = float(np.dot(truth[peak, :2], prediction[peak, :2]) / denom) if denom else -1.0
        positive += int(cosine > 0)
        spread = np.std(members[probe.cell_id][:, 9:] - members[baseline.cell_id][:, 9:], axis=0)
        groups.append({"group_id": group_id, "direction": probe.direction_id, "sign": probe.sign,
                       "duration_issues": probe.duration, "peak_state": 26 + peak,
                       "peak_direction_cosine": cosine,
                       "paired_max_abs_error": np.max(np.abs(prediction - truth), axis=0).tolist(),
                       "paired_member_spread_max": np.max(spread, axis=0).tolist(),
                       "true_response_by_state": truth.tolist(),
                       "predicted_response_by_state": prediction.tolist()})
    truth_array, prediction_array = np.concatenate(truth_rows), np.concatenate(prediction_rows)
    denominator = float(np.linalg.norm(truth_array))
    return {"p95_absolute_error": np.quantile(np.abs(errors), .95, axis=0).tolist(),
            "maximum_absolute_error": np.max(np.abs(errors), axis=0).tolist(),
            "matched_response_nrmse": float(np.linalg.norm(prediction_array - truth_array) / denominator),
            "positive_peak_direction_groups": positive, "group_metrics": groups}


def _support(data: model.AllowedDataset, cells: Sequence[model.Cell]) -> dict[str, Any]:
    window = 16
    dev_rows, dev_meta = [], []
    for cell in data.cells:
        all_frames = [model.frame(cell, issue, data) for issue in range(34)]
        for issue in range(16, 34):
            dev_rows.append(np.asarray(all_frames[issue - window + 1:issue + 1]))
            dev_meta.append((cell.cell_id, issue))
    raw = np.asarray(dev_rows)
    mean, scale = np.mean(raw, axis=(0, 1)), np.std(raw, axis=(0, 1))
    scale[scale < 1e-12] = 1.0
    standardized = (raw - mean) / scale
    masks = {"full_tcn_features": np.arange(50),
             "without_absolute_time": np.arange(48),
             "action_history_only": np.arange(6, 48)}

    def flattened(values: np.ndarray, indices: np.ndarray) -> np.ndarray:
        return values[:, indices].reshape(-1)

    thresholds = {}
    for name, indices in masks.items():
        vectors = np.asarray([flattened(row, indices) for row in standardized])
        nearest = []
        for index, vector in enumerate(vectors):
            candidates = [j for j, meta in enumerate(dev_meta) if meta[0] != dev_meta[index][0]]
            nearest.append(float(min(np.linalg.norm(vector - vectors[j]) for j in candidates)))
        thresholds[name] = max(nearest)
    rows = []
    for cell in cells:
        frames = np.asarray([model.frame(cell, issue, data) for issue in range(34)])
        normalized = (frames - mean) / scale
        for issue in range(16, 34):
            item = {"cell_id": cell.cell_id, "group_id": cell.context_id, "cell_kind": cell.cell_kind,
                    "issue_step": issue, "distances": {}, "outside_development_reference": {}}
            for name, indices in masks.items():
                vector = flattened(normalized[issue - window + 1:issue + 1], indices)
                dev_vectors = [flattened(row, indices) for row in standardized]
                distance = float(min(np.linalg.norm(vector - other) for other in dev_vectors))
                item["distances"][name] = distance
                item["outside_development_reference"][name] = distance > thresholds[name]
            rows.append(item)
    preprobe = [row for row in rows if row["issue_step"] == 25 and row["cell_kind"] == "probe"]
    return {"standardization_source": "ID2F1R1 development causal frames only",
            "window_steps": window, "development_leave_cell_out_max_distance": thresholds,
            "preprobe_outside_full_count": sum(x["outside_development_reference"]["full_tcn_features"] for x in preprobe),
            "prefix_rows": rows}


def attribute(path: Path, source_revision: str, run_dir: Path, output: Path) -> dict[str, Any]:
    stage, cfg, targets, id2c1_stage = load(path)
    run_dir, output = inside_root(run_dir, "ID2J0 run"), inside_root(output, "ID2J0 attribution")
    primary, independent = _json(run_dir / "result.json"), _json(run_dir / "independent_raw_audit.json")
    if (not primary.get("passed") or primary.get("route") != stage["routes"]["data_pass"]
            or not independent.get("audit_passed")
            or independent.get("primary_sha256") != sha256(run_dir / "result.json")):
        raise InputIntegrityError("diagnostic raw not independently accepted")
    if output.exists():
        raise FileExistsError(str(output))
    id2i1_stage = i1._read_json(ROOT / stage["evidence"]["id2i1_config"]["path"])
    development_stage = model.load_stage(ROOT / id2i1_stage["evidence"]["id2g1r1_config"]["path"])
    data = model.extract_dataset(development_stage)
    campaign = streams(stage, cfg, targets, id2c1_stage)
    cells = _cells(stage, run_dir, campaign, data, cfg)
    h1_stage, _, _, _ = h1.load(h1.CONFIG)
    members = h1._load_tcn(h1_stage)
    modes = {}
    for label, period in (("recenter_1ms", 1), ("recenter_2ms", 2), ("recenter_4ms", 4),
                          ("free_from_state16", None)):
        means, member_values = _mode_predictions(members, cells, data, period)
        modes[label] = _mode_metrics(stage, cells, data, means, member_values)
    current_residuals = []
    for cell in cells:
        predicted = cell.issued + data.q0 - data.source_current
        current_residuals.append(cell.currents[1:35] - predicted)
    current_residual = np.concatenate(current_residuals)
    max_current = float(np.max(np.abs(current_residual)))
    support = _support(data, cells)
    one, free = modes["recenter_1ms"], modes["free_from_state16"]
    contract = stage["analysis"]
    one_step_sound = (all(a <= b for a, b in zip(one["p95_absolute_error"], contract["one_step_p95_caps"]))
                      and one["matched_response_nrmse"] <= contract["maximum_one_step_matched_response_nrmse"]
                      and one["positive_peak_direction_groups"] >= contract["minimum_positive_one_step_peak_cosine_groups"])
    materially_better = one["matched_response_nrmse"] <= free["matched_response_nrmse"] * (1.0 - contract["material_nrmse_improvement_fraction"])
    far = int(support["preprobe_outside_full_count"])
    near_failures = sum(row["peak_direction_cosine"] <= 0 for row in one["group_metrics"])
    if max_current > contract["maximum_expected_next_current_residual_a"]:
        route = stage["routes"]["actuator_review"]
    elif one_step_sound and materially_better:
        route = stage["routes"]["recentered_model"]
    elif not one_step_sound and far >= 4 and near_failures:
        route = stage["routes"]["mixed"]
    elif not one_step_sound and far >= 4:
        route = stage["routes"]["factorized_data"]
    elif not one_step_sound and near_failures:
        route = stage["routes"]["structured_model"]
    else:
        route = stage["routes"]["higher_review"]
    result = {"schema_version": ATTRIBUTION_SCHEMA, "source_revision": source_revision,
              "stage_config_sha256": CONFIG_SHA256, "diagnostic_primary_sha256": sha256(run_dir / "result.json"),
              "diagnostic_independent_sha256": sha256(run_dir / "independent_raw_audit.json"),
              "selected_model_sha256": stage["evidence"]["selected_model"]["sha256"],
              "models_fit_retrained_tuned_selected_or_recalibrated": 0, "new_tsc_calls_during_attribution": 0,
              "id2c2_records_read": 0, "mode_metrics": modes,
              "next_current_residual_max_a": max_current,
              "next_current_residual_p95_a": np.quantile(np.abs(current_residual), .95, axis=0).tolist(),
              "support_diagnostics": support,
              "routing_diagnostics": {"one_step_sound": one_step_sound,
                                      "one_step_materially_better_than_free": materially_better,
                                      "preprobe_far_support_groups": far,
                                      "one_step_wrong_direction_groups": near_failures},
              "audit_completed": True, "model_passed": False, "route": route,
              "controller_or_new_tsc_authorized": False, "claim_boundary": stage["claim_boundary"]}
    write_new(output, result)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("offline", "run", "attribute"))
    parser.add_argument("--stage-config", type=Path, default=CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.mode == "offline":
            result = offline(args.stage_config, args.source_revision)
            write_new(inside_root(args.output, "offline output"), result)
        elif args.mode == "run":
            result = run(args.stage_config, args.source_revision, args.output)
        else:
            if args.run_dir is None:
                raise ValueError("--run-dir required")
            result = attribute(args.stage_config, args.source_revision, args.run_dir, args.output)
    except Exception as exc:
        result = {"schema_version": ATTRIBUTION_SCHEMA if args.mode == "attribute" else RUN_SCHEMA,
                  "source_revision": args.source_revision, "passed": False,
                  "route": "ONE_MS_ID2J0_ATTRIBUTION_INPUT_FAIL_STOP" if args.mode == "attribute"
                  else "ONE_MS_ID2J0_OFFLINE_OR_INPUT_FAIL_NO_TSC",
                  "failures": [f"{type(exc).__name__}:{exc}"]}
        if not args.output.exists():
            write_new(inside_root(args.output, "failure output"), result)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    if args.mode == "attribute":
        return 0 if result.get("audit_completed") else 2
    return 0 if result.get("passed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
