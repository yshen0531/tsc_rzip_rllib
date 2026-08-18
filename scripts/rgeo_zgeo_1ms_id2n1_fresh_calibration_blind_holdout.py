#!/usr/bin/env python3
"""Run ID-2N1 fresh calibration followed by a gated blind holdout."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import shutil
import sys
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from scripts.rgeo_zgeo_1ms_id0_vector_tail import (  # noqa: E402
    InputIntegrityError, compare_rows, inside_root, raw_inventory, sha256, write_new,
)
from scripts import rgeo_zgeo_1ms_id2k1_factorized_history_sign_development as k1  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2l1_structured_history_model as l1  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2m1_bounded_event_innovation_model as m1  # noqa: E402


CONFIG = ROOT / "configs" / "rgeo_zgeo_1ms_id2n1_fresh_calibration_blind_holdout.json"
CONFIG_SHA256 = "4b41320e6e79840b5d2234f3bfa7a9a77e0606f0d0e9cf624274b42ed2f64d08"
SCHEMA = "rgeo-zgeo-1ms-id2n1-fresh-calibration-blind-holdout-result-v1"
CAL_SCHEMA = "rgeo-zgeo-1ms-id2n1-finite-calibration-tube-v1"


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(inside_root(path, "JSON evidence").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise InputIntegrityError(f"object required: {path}")
    return value


def _require(stage: dict[str, Any]) -> None:
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2n1-fresh-calibration-blind-holdout-v1",
        "identity": "rgeo-zgeo-1ms-id2n1-fresh-calibration-blind-holdout-v1",
        "stage": "ID-2N1", "takeover_time_ms": 1100, "control_period_ms": 1,
        "horizon_steps": 34, "unique_cells": 24, "maximum_rollouts": 28,
        "maximum_reset_calls": 28, "maximum_advance_attempts": 952,
        "maximum_gotsc_calls": 952, "maximum_verified_plant_advances": 952,
        "maximum_retained_states": 980, "retry_after_any_advance_attempt": "forbidden",
        "phase_order": ["calibration", "holdout"],
        "holdout_execution_requires_written_calibration_pass": True,
        "development_refit_forbidden": True, "model_update_forbidden": True,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise InputIntegrityError(f"frozen field mismatch: {key}")
    families = stage.get("families", [])
    if len(families) != 8 or [row.get("group_id") for row in families] != [
            "c00", "c01", "c02", "c03", "v00", "v01", "v02", "v03"]:
        raise InputIntegrityError("family identity changed")
    if [row.get("role") for row in families] != ["calibration"] * 4 + ["holdout"] * 4:
        raise InputIntegrityError("family role changed")
    for family in families:
        occupied = set()
        for event in [*family["conditioners"], *[
                {**probe, "issue_step": family["probe_issue_step"],
                 "duration_issues": family["probe_duration_issues"]} for probe in family["probes"][:1]]]:
            if event["direction"] not in ("p04", "p07") or event["sign"] not in ("plus", "minus"):
                raise InputIntegrityError("event grammar changed")
            span = set(range(int(event["issue_step"]), int(event["issue_step"]) + int(event["duration_issues"])))
            if occupied & span:
                raise InputIntegrityError(f"overlapping conditioner/probe schedule: {family['group_id']}")
            occupied |= span
        if len(family["probes"]) != 2 or {row["direction"] for row in family["probes"]} != {"p04", "p07"}:
            raise InputIntegrityError("probe pair changed")
    if stage["calibration"]["prediction_horizons_ms"] != list(range(1, 9)):
        raise InputIntegrityError("calibration horizons changed")


def load(path: Path = CONFIG) -> tuple[dict[str, Any], Any, dict[str, Any], dict[str, Any],
                                       l1.Dataset, m1.SeparatedModel]:
    path = inside_root(path, "ID2N1 config")
    if sha256(path) != CONFIG_SHA256:
        raise InputIntegrityError("ID2N1 config hash mismatch")
    stage = _json(path)
    _require(stage)
    base = inside_root(ROOT / stage["base_tsc_config"], "base config")
    if sha256(base) != stage["evidence"]["base_tsc_config_sha256"]:
        raise InputIntegrityError("base config hash changed")
    for name, item in stage["evidence"].items():
        if name == "base_tsc_config_sha256":
            continue
        evidence = inside_root(ROOT / item["path"], name)
        if not evidence.is_file() or sha256(evidence) != item["sha256"]:
            raise InputIntegrityError(f"evidence mismatch: {name}")
    m1_result = _json(ROOT / stage["evidence"]["id2m1_result"]["path"])
    m1_model = _json(ROOT / stage["evidence"]["id2m1_model"]["path"])
    m1_audit = _json(ROOT / stage["evidence"]["id2m1_independent"]["path"])
    if (m1_result.get("route") != stage["evidence"]["id2m1_result"]["required_route"]
            or not m1_result.get("passed") or not m1_audit.get("audit_passed")):
        raise InputIntegrityError("ID2M1 result identity changed")
    if (m1_model.get("selected_candidate") != stage["evidence"]["id2m1_model"]["required_candidate"]
            or m1.canonical_sha256(m1_model) != stage["evidence"]["id2m1_model"]["canonical_sha256"]):
        raise InputIntegrityError("ID2M1 model identity changed")
    k1_stage, cfg, targets, source = k1.load(ROOT / stage["evidence"]["id2k1_config"]["path"])
    m1_stage = m1.load_stage(ROOT / stage["evidence"]["id2m1_config"]["path"])
    l1_stage, data = m1.load_inputs(m1_stage)
    payload = m1_model["model"]
    model = m1.SeparatedModel(
        m1_model["selected_candidate"], np.asarray(payload["nominal_normalized_delta"], dtype=float),
        np.asarray(payload["feature_scale"], dtype=float), np.asarray(payload["coefficients"], dtype=float),
        m1_stage, int(payload["fit_rank"]), float(payload["fit_condition"]), int(payload["active_feature_count"]),
    )
    return stage, cfg, targets, source, data, model


def campaign_streams(stage: dict[str, Any], cfg: Any, targets: dict[str, Any],
                     source: dict[str, Any]) -> list[dict[str, Any]]:
    selected = next(row for row in k1.phase_a_streams(source, cfg, targets)
                    if row["candidate_id"] == "p03_minus_stride1")
    held = selected["targets"][15]
    nominal = list(selected["targets"][:16]) + [held] * (34 - 16)
    translated = {f"{d}:{s}": k1._translated_target(held, targets["q0"], targets[f"{d}:{s}"], cfg,
                                                        f"id2n1.{d}.{s}")
                  for d in ("p04", "p07") for s in ("plus", "minus")}
    coordinate = {"p04": 0, "p07": 1}
    streams = []
    for family in stage["families"]:
        cells = [(None, None), *[(row["direction"], row["sign"]) for row in family["probes"]]]
        for direction, sign in cells:
            if direction is None:
                cell_id = f"{family['group_id']}__baseline"
            else:
                cell_id = (f"{family['group_id']}__{direction}_{sign}_i"
                           f"{family['probe_issue_step']}_d{family['probe_duration_issues']}")
            replays = 2 if cell_id in stage["critical_replay_cells"] else 1
            for replay in range(replays):
                sequence = list(nominal)
                virtual = [[0.0, 0.0] for _ in sequence]
                events = list(family["conditioners"])
                if direction is not None:
                    events.append({"direction": direction, "sign": sign,
                                   "issue_step": family["probe_issue_step"],
                                   "duration_issues": family["probe_duration_issues"]})
                non_nominal = []
                for event in events:
                    issue, duration = int(event["issue_step"]), int(event["duration_issues"])
                    signed = 1.0 if event["sign"] == "plus" else -1.0
                    for step in range(issue, issue + duration):
                        if sequence[step] != held:
                            raise InputIntegrityError(f"overlapping events: {cell_id}:{step}")
                        sequence[step] = translated[f"{event['direction']}:{event['sign']}"]
                        virtual[step][coordinate[event["direction"]]] = signed
                    non_nominal.append(issue)
                rollout_id = f"{cell_id}__r{replay}"
                streams.append({"rollout_id": rollout_id, "cell_id": cell_id,
                                "group_id": family["group_id"], "context_id": family["group_id"],
                                "role": family["role"], "replay_index": replay,
                                "cell_kind": "baseline" if direction is None else "probe",
                                "conditioners": family["conditioners"], "direction_id": direction, "sign": sign,
                                "probe_issue_step": None if direction is None else family["probe_issue_step"],
                                "probe_duration_issues": 0 if direction is None else family["probe_duration_issues"],
                                "non_nominal_issue_steps": sorted(set(non_nominal)),
                                "targets": sequence, "actions": k1._actions(sequence, cfg, rollout_id, virtual)})
    if len(streams) != 28 or len({row["cell_id"] for row in streams}) != 24:
        raise InputIntegrityError("campaign cardinality changed")
    return streams


def offline(path: Path, source_revision: str) -> dict[str, Any]:
    failures = []
    rows = []
    try:
        stage, cfg, targets, source, _, _ = load(path)
        streams = campaign_streams(stage, cfg, targets, source)
        for row in streams:
            if len(row["actions"]) != 34 or any(float(a["maximum_issued_delta_a"]) > 0.3 for a in row["actions"]):
                raise InputIntegrityError("action stream invalid")
        rows = [{key: value for key, value in row.items() if key != "targets"} for row in streams]
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {"schema_version": SCHEMA, "kind": "offline_preflight", "source_revision": source_revision,
            "stage_config_sha256": CONFIG_SHA256, "passed": not failures, "failures": failures,
            "action_streams": rows, "reset_calls": 0, "advance_attempts": 0,
            "plant_advance_gotsc_calls": 0, "verified_plant_advances": 0, "models_fit_or_updated": 0}


def _storage(stage: dict[str, Any], output: Path) -> dict[str, Any]:
    free = shutil.disk_usage(output.parent).free
    gate = stage["storage_gate"]
    estimate = int(gate["maximum_estimated_raw_bytes"])
    return {"free_bytes_before_run": free, "estimated_raw_bytes": estimate,
            "estimated_free_bytes_after_run": free - estimate,
            "passed": free >= int(gate["minimum_free_bytes_before_run"])
            and free - estimate >= int(gate["minimum_free_bytes_after_estimate"])}


def _primary(rows: Sequence[dict[str, Any]], role: str | None = None) -> list[dict[str, Any]]:
    return [row for row in rows if int(row["replay_index"]) == 0 and (role is None or row["role"] == role)]


def prefix_checks(rows: Sequence[dict[str, Any]], role: str) -> list[dict[str, Any]]:
    groups = sorted({row["group_id"] for row in _primary(rows, role)})
    checks = []
    for group in groups:
        members = [row for row in _primary(rows, role) if row["group_id"] == group]
        baseline = next((row for row in members if row["cell_kind"] == "baseline"), None)
        failures = []
        if baseline is None or len(members) != 3:
            failures.append("CELL_SET")
        else:
            for probe in [row for row in members if row["cell_kind"] == "probe"]:
                issue = int(probe["probe_issue_step"])
                for index in range(issue + 1):
                    left, right = baseline["states"][index], probe["states"][index]
                    for key in ("r_geo_m", "z_geo_m", "r_mid_m", "ip_a",
                                "actual_current_decimal_a_tsc", "wire_current_a"):
                        if left[key] != right[key]:
                            failures.append(f"{probe['cell_id']}:STATE:{index}:{key}")
                for step in range(issue):
                    if baseline["actions"][step]["expected_card15_fields"] != probe["actions"][step]["expected_card15_fields"]:
                        failures.append(f"{probe['cell_id']}:ACTION:{step}")
        checks.append({"group_id": group, "passed": not failures, "failures": list(dict.fromkeys(failures))})
    return checks


def replay_checks(rows: Sequence[dict[str, Any]], stage: dict[str, Any], role: str) -> list[dict[str, Any]]:
    shim = {"repeatability": stage["repeatability"], "semantic_artifacts": stage["semantic_artifacts"]}
    checks = []
    for cell_id in [value for value in stage["critical_replay_cells"] if value.startswith("c" if role == "calibration" else "v")]:
        members = [row for row in rows if row["cell_id"] == cell_id]
        check = ({"passed": False, "failures": ["REPLAY_COUNT"]} if len(members) != 2
                 else compare_rows(members[0], members[1], shim))
        checks.append({"cell_id": cell_id, **check})
    return checks


def _cell(row: dict[str, Any]) -> l1.Cell:
    states, currents = zip(*(l1._state(value) for value in row["states"]))
    issued = np.asarray([l1._target(value) for value in row["actions"]], dtype=float)
    return l1.Cell(row["cell_id"], row["group_id"], row["cell_kind"], np.asarray(states),
                   np.asarray(currents), issued, row.get("direction_id"), row.get("sign"))


def endpoint_errors(cells: Sequence[l1.Cell], data: l1.Dataset, model: m1.SeparatedModel,
                    stage: dict[str, Any]) -> dict[str, list[list[float]]]:
    result = {str(h): [] for h in stage["calibration"]["prediction_horizons_ms"]}
    start, final = stage["calibration"]["origin_state_range_inclusive"]
    for cell in cells:
        for origin in range(int(start), int(final) + 1):
            for horizon in stage["calibration"]["prediction_horizons_ms"]:
                stop = origin + int(horizon)
                if stop > 34:
                    continue
                predicted = l1._predict_segment(model, cell, data, origin, stop)[-1]
                result[str(horizon)].append((predicted - cell.states[stop]).tolist())
    return result


def response_metrics(rows: Sequence[dict[str, Any]], role: str, data: l1.Dataset,
                     model: m1.SeparatedModel) -> dict[str, Any]:
    groups = sorted({row["group_id"] for row in _primary(rows, role)})
    metrics, all_truth, all_prediction = [], [], []
    for group in groups:
        members = [_cell(row) for row in _primary(rows, role) if row["group_id"] == group]
        baseline = next(cell for cell in members if cell.cell_kind == "baseline")
        family_truth, family_prediction, cosines = [], [], []
        for cell in [value for value in members if value.cell_kind == "probe"]:
            source_row = next(row for row in _primary(rows, role) if row["cell_id"] == cell.cell_id)
            origin = int(source_row["probe_issue_step"])
            truth = cell.states[origin + 1:35] - baseline.states[origin + 1:35]
            pred = (l1._predict_segment(model, cell, data, origin, 34)[1:]
                    - l1._predict_segment(model, baseline, data, origin, 34)[1:])
            peak = int(np.argmax(np.linalg.norm(truth[:, :2], axis=1)))
            denominator = float(np.linalg.norm(truth[peak, :2]) * np.linalg.norm(pred[peak, :2]))
            cosine = float(np.dot(truth[peak, :2], pred[peak, :2]) / denominator) if denominator > 0 else -1.0
            family_truth.append(truth / data.response_scale)
            family_prediction.append(pred / data.response_scale)
            cosines.append(cosine)
            metrics.append({"group_id": group, "cell_id": cell.cell_id, "peak_cosine": cosine,
                            "peak_rz_norm_m": float(np.max(np.linalg.norm(truth[:, :2], axis=1))),
                            "maximum_abs_ip_response_a": float(np.max(np.abs(truth[:, 2])))})
        truth_array, pred_array = np.concatenate(family_truth), np.concatenate(family_prediction)
        nrmse = float(np.linalg.norm(pred_array - truth_array) / np.linalg.norm(truth_array))
        for item in metrics[-2:]:
            item["family_response_nrmse"] = nrmse
        all_truth.append(truth_array)
        all_prediction.append(pred_array)
    truth_array, pred_array = np.concatenate(all_truth), np.concatenate(all_prediction)
    return {"probe_count": len(metrics), "probe_metrics": metrics,
            "combined_response_nrmse": float(np.linalg.norm(pred_array - truth_array) / np.linalg.norm(truth_array)),
            "positive_peak_directions": sum(item["peak_cosine"] > 0 for item in metrics)}


def calibrate(rows: Sequence[dict[str, Any]], stage: dict[str, Any], data: l1.Dataset,
              model: m1.SeparatedModel, source_revision: str) -> dict[str, Any]:
    cells = [_cell(row) for row in _primary(rows, "calibration")]
    errors = endpoint_errors(cells, data, model, stage)
    maximum, tube = {}, {}
    floor = np.asarray(stage["calibration"]["tube_floor"], dtype=float)
    for horizon, values in errors.items():
        peak = np.max(np.abs(np.asarray(values)), axis=0)
        maximum[horizon] = peak.tolist()
        tube[horizon] = np.maximum(floor, float(stage["calibration"]["tube_multiplier"]) * peak).tolist()
    response = response_metrics(rows, "calibration", data, model)
    caps_ok = all(all(value <= cap for value, cap in zip(tube[str(h)], stage["calibration"][
        "tube_caps_h1_h4" if h <= 4 else "tube_caps_h5_h8"])) for h in range(1, 9))
    signal_ok = all(item["peak_rz_norm_m"] >= stage["calibration"]["minimum_peak_paired_rz_norm_m"]
                    and item["maximum_abs_ip_response_a"] <= stage["calibration"]["maximum_peak_paired_abs_ip_a"]
                    for item in response["probe_metrics"])
    response_ok = (response["combined_response_nrmse"] <= stage["calibration"]["maximum_combined_response_nrmse"]
                   and response["positive_peak_directions"] == stage["calibration"]["required_positive_peak_directions"])
    passed = len(cells) == 12 and caps_ok and signal_ok and response_ok
    return {"schema_version": CAL_SCHEMA, "source_revision": source_revision,
            "stage_config_sha256": CONFIG_SHA256, "model_payload_sha256": stage["evidence"]["id2m1_model"]["canonical_sha256"],
            "calibration_families": 4, "calibration_cells": len(cells), "endpoint_errors": errors,
            "maximum_abs_error_by_horizon": maximum, "tube_by_horizon": tube,
            "response_metrics": response, "tube_caps_passed": caps_ok, "signal_passed": signal_ok,
            "response_passed": response_ok, "model_coefficients_updated": False, "passed": passed}


def holdout_metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any], data: l1.Dataset,
                    model: m1.SeparatedModel, calibration: dict[str, Any]) -> dict[str, Any]:
    cells = [_cell(row) for row in _primary(rows, "holdout")]
    errors = endpoint_errors(cells, data, model, stage)
    by_horizon, contained = {}, True
    for horizon, values in errors.items():
        array = np.abs(np.asarray(values))
        tube = np.asarray(calibration["tube_by_horizon"][horizon])
        row_contained = np.all(array <= tube, axis=1)
        p95 = np.quantile(array, 0.95, axis=0)
        caps = stage["holdout"]["endpoint_p95_caps"][horizon]
        cap_passed = all(value <= cap for value, cap in zip(p95, caps))
        contained = contained and bool(np.all(row_contained))
        by_horizon[horizon] = {"rows": len(array), "contained": int(np.count_nonzero(row_contained)),
                               "p95_abs": p95.tolist(), "p95_caps_passed": cap_passed}
    response = response_metrics(rows, "holdout", data, model)
    family_nrmse = {item["group_id"]: item["family_response_nrmse"] for item in response["probe_metrics"]}
    point_ok = all(value["p95_caps_passed"] for value in by_horizon.values())
    response_ok = (all(value < stage["holdout"]["maximum_each_family_response_nrmse"] for value in family_nrmse.values())
                   and response["combined_response_nrmse"] <= stage["holdout"]["maximum_combined_response_nrmse"]
                   and response["positive_peak_directions"] >= stage["holdout"]["minimum_positive_peak_directions"])
    return {"holdout_families": 4, "holdout_cells": len(cells), "by_horizon": by_horizon,
            "all_endpoint_rows_contained": contained, "point_caps_passed": point_ok,
            "response_metrics": response, "family_response_nrmse": family_nrmse,
            "response_passed": response_ok, "passed": len(cells) == 12 and contained and point_ok and response_ok}


def run(path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = inside_root(output, "ID2N1 output")
    if output.exists():
        raise FileExistsError(str(output))
    stage, cfg, targets, source, data, model = load(path)
    storage = _storage(stage, output)
    output.mkdir(parents=True)
    pre = offline(path, source_revision)
    write_new(output / "offline_preflight.json", pre)
    if not storage["passed"] or not pre["passed"]:
        route = stage["routes"]["storage_fail" if not storage["passed"] else "offline_or_input_fail"]
        result = {"schema_version": SCHEMA, "source_revision": source_revision, "stage_config_sha256": CONFIG_SHA256,
                  "passed": False, "route": route, "storage_gate": storage, "reasons": pre["failures"],
                  "holdout_opened": False, "reset_calls": 0, "advance_attempts": 0,
                  "plant_advance_gotsc_calls": 0, "verified_plant_advances": 0}
        write_new(output / "result.json", result)
        return result
    cfg.run_root = output / "rollouts"
    runtime = dict(stage)
    runtime["empirical_exploration"] = dict(stage["empirical_exploration"])
    runtime["empirical_exploration"]["inner_pulse_issue_clearance"] = stage["empirical_exploration"]["inner_probe_issue_clearance"]
    streams = campaign_streams(stage, cfg, targets, source)
    rows = []
    for stream in [row for row in streams if row["role"] == "calibration"]:
        row = k1.one_rollout(cfg, runtime, stream)
        row.update({"schema_version": SCHEMA, "source_revision": source_revision})
        rows.append(row)
        write_new(output / f"{row['rollout_id']}.json", row)
        if not row["passed"]:
            break
    cal_complete = len(rows) == 14 and all(row["passed"] for row in rows)
    cal_prefix = prefix_checks(rows, "calibration") if cal_complete else []
    cal_replay = replay_checks(rows, stage, "calibration") if cal_complete else []
    cal_interface = cal_complete and all(row["passed"] for row in cal_prefix + cal_replay)
    calibration = calibrate(rows, stage, data, model, source_revision) if cal_interface else None
    if calibration is not None:
        write_new(output / "calibration.json", calibration)
    holdout_opened = bool(calibration and calibration["passed"] and (output / "calibration.json").is_file())
    if holdout_opened:
        for stream in [row for row in streams if row["role"] == "holdout"]:
            row = k1.one_rollout(cfg, runtime, stream)
            row.update({"schema_version": SCHEMA, "source_revision": source_revision})
            rows.append(row)
            write_new(output / f"{row['rollout_id']}.json", row)
            if not row["passed"]:
                break
    inventory = raw_inventory(output, rows, stage)
    hold_rows = [row for row in rows if row.get("role") == "holdout"]
    hold_complete = len(hold_rows) == 14 and all(row["passed"] for row in hold_rows)
    hold_prefix = prefix_checks(rows, "holdout") if hold_complete else []
    hold_replay = replay_checks(rows, stage, "holdout") if hold_complete else []
    hold_interface = hold_complete and all(row["passed"] for row in hold_prefix + hold_replay)
    holdout = holdout_metrics(rows, stage, data, model, calibration) if holdout_opened and hold_interface else None
    raw_ok = not inventory["missing_required_artifacts"]
    if not cal_interface or not raw_ok:
        route = stage["routes"]["calibration_execution_or_raw_fail"]
    elif not calibration or not calibration["passed"]:
        route = stage["routes"]["calibration_scientific_fail"]
    elif not hold_interface or not raw_ok:
        route = stage["routes"]["holdout_execution_or_raw_fail"]
    elif not holdout or not holdout["passed"]:
        route = stage["routes"]["holdout_scientific_fail"]
    else:
        route = stage["routes"]["pass"]
    passed = route == stage["routes"]["pass"]
    result = {"schema_version": SCHEMA, "source_revision": source_revision, "stage_config_sha256": CONFIG_SHA256,
              "model_payload_sha256": stage["evidence"]["id2m1_model"]["canonical_sha256"],
              "passed": passed, "route": route, "storage_gate": storage,
              "calibration_prefix_checks": cal_prefix, "calibration_replay_checks": cal_replay,
              "calibration": calibration, "holdout_opened": holdout_opened,
              "holdout_prefix_checks": hold_prefix, "holdout_replay_checks": hold_replay, "holdout": holdout,
              "rollouts_completed": len(rows), "unique_cells_completed": len({row["cell_id"] for row in rows}),
              "reset_calls": sum(row["reset_calls"] for row in rows),
              "advance_attempts": sum(row["advance_attempts"] for row in rows),
              "plant_advance_gotsc_calls": sum(row["plant_advance_gotsc_calls"] for row in rows),
              "verified_plant_advances": sum(row["verified_plant_advances"] for row in rows),
              **inventory, "model_coefficients_updated": False, "models_fit_or_updated": 0,
              "controller_authorized": False, "claim_boundary": stage["claim_boundary"]}
    write_new(output / "result.json", result)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("offline", "run"))
    parser.add_argument("--stage-config", type=Path, default=CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = (offline(args.stage_config, args.source_revision) if args.mode == "offline" else
              run(args.stage_config, args.source_revision,
                  args.output or ROOT / f"rgeo_zgeo_1ms_id2n1_runs_{args.source_revision[:8]}"))
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
