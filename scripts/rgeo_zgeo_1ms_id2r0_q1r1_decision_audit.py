#!/usr/bin/env python3
"""ID-2R0 bounded Q1R1 erratum, support, and route-decision audit."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import rgeo_zgeo_1ms_id2q1_shared_latent_model_comparison as q1


CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2r0_q1r1_decision_audit.json"
CONFIG_SHA256 = "0863c7e5e23161cba2e5c1230b2e8c99d03f34e158e34c900a5f8e63cd3dfbaa"
SCHEMA = "rgeo-zgeo-1ms-id2r0-q1r1-decision-audit-result-v1"
PREDICTION_SCHEMA = "rgeo-zgeo-1ms-id2r0-q1r1-explicit-predictions-v1"


class IntegrityError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def inside(path: Path, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError as exc:
        raise IntegrityError(f"{label} escapes repository") from exc
    return resolved


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise IntegrityError(f"{path} must contain an object")
    return value


def require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise IntegrityError(f"{label}: expected {expected!r}, got {actual!r}")


def load_stage(path: Path = CONFIG) -> tuple[dict[str, Any], dict[str, Any], q1.Dataset, dict[str, Any]]:
    path = inside(path, "ID2R0 config")
    require_equal(sha256(path), CONFIG_SHA256, "ID2R0 config hash")
    stage = read_json(path)
    require_equal(stage.get("schema_version"),
                  "rgeo-zgeo-1ms-id2r0-q1r1-decision-audit-v1", "schema")
    require_equal(stage.get("identity"), stage.get("schema_version"), "identity")
    require_equal(stage.get("execution_contract"),
                  "server_only_zero_new_tsc_frozen_q1_diagnostic_refit_and_route_audit",
                  "execution contract")
    for key in ("new_tsc_calls", "reset_calls", "plant_advances"):
        require_equal(int(stage[key]), 0, key)
    if not all(stage["forbidden_sources"].values()):
        raise IntegrityError("forbidden source gate weakened")
    require_equal(stage["diagnostic_refit"]["new_candidate_count"], 0, "new candidates")
    require_equal(stage["diagnostic_refit"]["new_hyperparameter_searches"], 0,
                  "hyperparameter searches")
    require_equal(stage["diagnostic_refit"]["full_data_model_fit"], False, "full fit")
    require_equal(stage["diagnostic_refit"]["emit_model_payload"], False, "model payload")
    require_equal(stage["causal_prefix"]["nearest_k"], 1, "nearest k")
    for key in ("normalization_search", "distance_weight_search", "kernel_search"):
        require_equal(stage["causal_prefix"][key], False, key)
    require_equal(stage["causal_prefix"]["feature_count"], 96, "prefix feature count")
    require_equal(stage["causal_prefix"]["future_actual_current"], "forbidden",
                  "future current")
    require_equal(stage["causal_prefix"]["future_state"], "forbidden", "future state")
    require_equal(stage["causal_prefix"]["family_sign_direction_or_schedule_names_as_features"],
                  "forbidden", "label feature gate")

    design = inside(ROOT / stage["design"]["path"], "design")
    require_equal(sha256(design), stage["design"]["sha256"], "design hash")
    qcfg = inside(ROOT / stage["q1"]["config"]["path"], "Q1 config")
    qresult_path = inside(ROOT / stage["q1"]["result"]["path"], "Q1 result")
    qaudit_path = inside(ROOT / stage["q1"]["independent"]["path"], "Q1 audit")
    require_equal(sha256(qcfg), stage["q1"]["config"]["sha256"], "Q1 config hash")
    require_equal(sha256(qresult_path), stage["q1"]["result"]["sha256"], "Q1 result hash")
    require_equal(sha256(qaudit_path), stage["q1"]["independent"]["sha256"],
                  "Q1 audit hash")
    qresult = read_json(qresult_path)
    qaudit = read_json(qaudit_path)
    require_equal(qresult.get("route"), stage["q1"]["result"]["required_route"],
                  "Q1 route")
    require_equal(qresult.get("passed"), False, "Q1 result must remain FAIL")
    require_equal(qresult.get("selected_kind"), None, "Q1 selected model")
    require_equal(qresult.get("model_payload_sha256"), None, "Q1 model payload")
    require_equal(qaudit.get("audit_passed"), True, "Q1 independent audit")
    require_equal(qaudit.get("primary_result_exactly_recomputed"), True,
                  "Q1 exact recomputation")
    qstage = q1.load_stage(qcfg)
    data = q1.load_dataset(qstage)
    require_equal(len(data.cells), stage["q1"]["required_primary_cells"], "primary cells")
    require_equal(len({cell.group_id for cell in data.cells}),
                  stage["q1"]["required_families"], "families")
    require_equal(list(qstage["candidates"]), stage["diagnostic_refit"]["candidates"],
                  "candidate identity")
    return stage, qstage, data, qresult


def compact_replay_counts(qstage: dict[str, Any]) -> tuple[dict[str, int], dict[str, int]]:
    cell_counts: dict[str, int] = {}
    family_counts: dict[str, int] = {}
    for source_name, source in qstage["fit_sources"].items():
        folder = inside(ROOT / source["directory"], f"{source_name} compact")
        prefix = "h" if source_name == "k1" else "f"
        for path in sorted(folder.glob(prefix + "*.json")):
            if "__r" not in path.stem:
                continue
            row = q1.read_json(path)
            cell_id = str(row["cell_id"])
            family_id = str(row["group_id"])
            replay_index = int(row["replay_index"])
            if replay_index > 0:
                cell_counts[cell_id] = cell_counts.get(cell_id, 0) + 1
                family_counts[family_id] = family_counts.get(family_id, 0) + 1
    return cell_counts, family_counts


def baseline_map(cells: Sequence[q1.Cell]) -> dict[str, q1.Cell]:
    return {cell.group_id: cell for cell in cells if cell.cell_kind == "baseline"}


def probe_delta_sequence(cell: q1.Cell, baseline: q1.Cell) -> np.ndarray:
    origin = int(cell.probe_issue)
    return cell.issued[origin:origin + 8] - baseline.issued[origin:origin + 8]


def action_signature(cell: q1.Cell, baseline: q1.Cell) -> tuple[int, str]:
    return int(cell.probe_issue), canonical_sha(probe_delta_sequence(cell, baseline).tolist())


def schedule_stratum_signature(cell: q1.Cell, baseline: q1.Cell) -> tuple[int, tuple[bool, ...]]:
    delta = probe_delta_sequence(cell, baseline)
    active = tuple(bool(np.max(np.abs(row)) > 1e-12) for row in delta)
    return int(cell.probe_issue), active


def causal_prefix(cell: q1.Cell, origin: int, stage: dict[str, Any]) -> np.ndarray:
    cfg = stage["causal_prefix"]
    ss = cfg["state_scales"]
    ds = cfg["delta_scales"]
    current = cell.states[origin]
    values: list[float] = [
        float(current[0]) / float(ss["r_geo_m"]),
        float(current[1]) / float(ss["z_geo_m"]),
        float(current[2]) / float(ss["ip_a"]),
    ]
    scales = np.asarray([ds["r_geo_m"], ds["z_geo_m"], ds["ip_a"]], dtype=float)
    for lag in cfg["delta_lags"]:
        values.extend(((current - cell.states[max(0, origin - int(lag))]) / scales).tolist())
    values.extend((cell.currents[origin] / float(cfg["actual_current_scale_a"])).tolist())
    source = cell.issued[0]
    for lag in cfg["issued_history_lags"]:
        issue = origin - int(lag)
        issued = source if issue < 0 else cell.issued[issue]
        values.extend(((issued - source) / float(cfg["issued_current_scale_a"])).tolist())
    result = np.asarray(values, dtype=float)
    if result.shape != (int(cfg["feature_count"]),) or not np.all(np.isfinite(result)):
        raise IntegrityError("invalid causal prefix")
    return result


def rms_distance(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(left - right))))


def paired_truth(cell: q1.Cell, baseline: q1.Cell) -> np.ndarray:
    origin = int(cell.probe_issue)
    return cell.states[origin + 1:origin + 9] - baseline.states[origin + 1:origin + 9]


def cosine(left: np.ndarray, right: np.ndarray) -> float:
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    return -1.0 if denominator <= 0 else float(left @ right / denominator)


def ranking_regret(truth: np.ndarray, prediction: np.ndarray) -> float:
    scale = max(float(np.max(np.linalg.norm(truth, axis=1))), 1e-12)
    maximum = 0.0
    for angle in np.linspace(0.0, 2.0 * np.pi, 16, endpoint=False):
        direction = np.asarray([np.cos(angle), np.sin(angle)])
        scores = truth @ direction
        selected = int(np.argmax(prediction @ direction))
        maximum = max(maximum, max(0.0, float(np.max(scores) - scores[selected])) / scale)
    return maximum


def expanded_design(cells: Sequence[q1.Cell], data: q1.Dataset,
                    qstage: dict[str, Any]) -> np.ndarray:
    _, _, x, _, meta = q1.arrays(cells, data, qstage)
    rows = [x]
    index = {value: idx for idx, value in enumerate(meta)}
    cell_index = {id(cell): idx for idx, cell in enumerate(cells)}
    baselines = baseline_map(cells)
    weight = math.sqrt(float(qstage["shared_latent"]["paired_loss_weight"]))
    for cell_index_value, cell in enumerate(cells):
        if cell.cell_kind == "baseline":
            continue
        baseline_index = cell_index[id(baselines[cell.group_id])]
        ids = [index[(cell_index_value, origin, horizon)]
               for origin in range(16, 27) for horizon in range(8)]
        base_ids = [index[(baseline_index, origin, horizon)]
                    for origin in range(16, 27) for horizon in range(8)]
        rows.append(weight * (x[ids] - x[base_ids]))
    return np.concatenate(rows)


def svd_stats(matrix: np.ndarray) -> dict[str, Any]:
    scale = np.sqrt(np.mean(np.square(matrix), axis=0))
    scale = np.where(scale > 1e-10, scale, 1.0)
    normalized = matrix / scale
    singular = np.linalg.svd(normalized, compute_uv=False)
    rank = int(np.linalg.matrix_rank(normalized))
    condition = math.inf if rank == 0 else float(singular[0] / singular[rank - 1])
    return {
        "rows": int(matrix.shape[0]),
        "columns": int(matrix.shape[1]),
        "rank": rank,
        "condition": condition,
        "minimum_nonzero_singular_value": None if rank == 0 else float(singular[rank - 1]),
        "maximum_singular_value": None if rank == 0 else float(singular[0]),
    }


def blockwise_design(cells: Sequence[q1.Cell], data: q1.Dataset,
                     qstage: dict[str, Any]) -> dict[str, Any]:
    matrix = expanded_design(cells, data, qstage)
    blocks = {
        "current_state_velocity_current_innovation": (0, 12),
        "stable_signed_even_action_memory": (12, 60),
        "future_issued_level": (60, 63),
        "future_issued_edge": (63, 66),
        "context_by_future_action": (66, 102),
        "time_and_horizon": (102, 104),
        "all_features": (0, 104),
    }
    return {name: svd_stats(matrix[:, start:end]) for name, (start, end) in blocks.items()}


def angle_gap(vectors: Sequence[np.ndarray]) -> dict[str, Any]:
    usable = [np.asarray(vector, dtype=float) for vector in vectors
              if float(np.linalg.norm(vector)) > 1e-12]
    if not usable:
        return {"vector_count": 0, "maximum_angular_gap_deg": 360.0,
                "positive_span_geometry": False}
    angles = sorted(float(np.degrees(np.arctan2(v[1], v[0])) % 360.0) for v in usable)
    gaps = [angles[i + 1] - angles[i] for i in range(len(angles) - 1)]
    gaps.append(angles[0] + 360.0 - angles[-1])
    maximum = max(gaps)
    return {"vector_count": len(usable), "maximum_angular_gap_deg": maximum,
            "positive_span_geometry": maximum <= 180.0 + 1e-12}


def measured_geometry(data: q1.Dataset) -> list[dict[str, Any]]:
    baselines = baseline_map(data.cells)
    rows = []
    for family in sorted(baselines):
        probes = sorted((cell for cell in data.cells
                         if cell.group_id == family and cell.cell_kind == "probe"),
                        key=lambda cell: cell.cell_id)
        peak_vectors = []
        all_vectors = []
        cell_rows = []
        for cell in probes:
            response = paired_truth(cell, baselines[family])[:, :2]
            peak = int(np.argmax(np.linalg.norm(response, axis=1)))
            peak_vectors.append(response[peak])
            all_vectors.extend(response)
            cell_rows.append({
                "cell_id": cell.cell_id,
                "peak_horizon": peak + 1,
                "peak_rz_m": response[peak].tolist(),
                "peak_norm_m": float(np.linalg.norm(response[peak])),
            })
        scale = max(float(np.max(np.linalg.norm(np.asarray(all_vectors), axis=1))), 1e-12)
        progress = []
        vectors = np.asarray(all_vectors)
        for angle in np.linspace(0.0, 2.0 * np.pi, 16, endpoint=False):
            direction = np.asarray([np.cos(angle), np.sin(angle)])
            progress.append(float(np.max(vectors @ direction)) / scale)
        rows.append({
            "family_id": family,
            "peak_geometry": angle_gap(peak_vectors),
            "all_horizon_sample_geometry": angle_gap(all_vectors),
            "minimum_normalized_direction_progress_over_16_directions": min(progress),
            "probe_cells": cell_rows,
        })
    return rows


def explicit_family_metrics(model: Any, held: Sequence[q1.Cell], data: q1.Dataset,
                            qstage: dict[str, Any], candidate: str,
                            fold_id: str, prediction_rows: list[dict[str, Any]],
                            paired_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    predictions: dict[tuple[str, int], np.ndarray] = {}
    for cell in held:
        for origin in range(16, 27):
            predicted = q1.predict(model, cell, origin, data, qstage)
            predictions[(cell.cell_id, origin)] = predicted
            truth = cell.states[origin + 1:origin + 9]
            for index in range(8):
                prediction_rows.append({
                    "candidate": candidate,
                    "fold_id": fold_id,
                    "family_id": cell.group_id,
                    "cell_id": cell.cell_id,
                    "cell_kind": cell.cell_kind,
                    "origin": origin,
                    "horizon": index + 1,
                    "truth_rzi": truth[index].tolist(),
                    "predicted_rzi": predicted[index].tolist(),
                    "error_rzi": (predicted[index] - truth[index]).tolist(),
                })
    baselines = baseline_map(held)
    family_rows = []
    for family in sorted(baselines):
        baseline = baselines[family]
        probes = sorted((cell for cell in held
                         if cell.group_id == family and cell.cell_kind == "probe"),
                        key=lambda cell: cell.cell_id)
        truth_all = []
        predicted_all = []
        truth_peak = []
        predicted_peak = []
        cell_metrics = []
        for cell in probes:
            origin = int(cell.probe_issue)
            truth = paired_truth(cell, baseline)
            predicted = (predictions[(cell.cell_id, origin)] -
                         predictions[(baseline.cell_id, origin)])
            truth_all.append(truth / data.response_scale)
            predicted_all.append(predicted / data.response_scale)
            peak = int(np.argmax(np.linalg.norm(truth[:, :2], axis=1)))
            peak_cosine = cosine(truth[peak, :2], predicted[peak, :2])
            truth_peak.append(truth[peak, :2])
            predicted_peak.append(predicted[peak, :2])
            cell_metrics.append({"cell_id": cell.cell_id, "peak_horizon": peak + 1,
                                 "peak_cosine": peak_cosine})
            for index in range(8):
                paired_rows.append({
                    "candidate": candidate,
                    "fold_id": fold_id,
                    "family_id": family,
                    "cell_id": cell.cell_id,
                    "origin": origin,
                    "horizon": index + 1,
                    "truth_response_rzi": truth[index].tolist(),
                    "predicted_response_rzi": predicted[index].tolist(),
                    "response_error_rzi": (predicted[index] - truth[index]).tolist(),
                })
        truth_scaled = np.concatenate(truth_all)
        predicted_scaled = np.concatenate(predicted_all)
        response_nrmse = float(np.linalg.norm(predicted_scaled - truth_scaled) /
                               np.linalg.norm(truth_scaled))
        regret = ranking_regret(np.asarray(truth_peak), np.asarray(predicted_peak))
        family_rows.append({
            "family_id": family,
            "response_nrmse": response_nrmse,
            "positive_peak_directions": sum(int(row["peak_cosine"] > 0)
                                             for row in cell_metrics),
            "probe_count": len(cell_metrics),
            "family_action_ranking_regret": regret,
            "probe_metrics": cell_metrics,
        })
    return family_rows


def nearest_history_diagnostic(data: q1.Dataset, qstage: dict[str, Any],
                               stage: dict[str, Any]) -> dict[str, Any]:
    baselines = baseline_map(data.cells)
    items = []
    family_items: dict[str, list[dict[str, Any]]] = {}
    for fold in qstage["whole_family_folds"]:
        held_families = set(fold["held"])
        training = [cell for cell in data.cells
                    if cell.group_id not in held_families and cell.cell_kind == "probe"]
        held = [cell for cell in data.cells
                if cell.group_id in held_families and cell.cell_kind == "probe"]
        for cell in held:
            origin = int(cell.probe_issue)
            signature = action_signature(cell, baselines[cell.group_id])
            candidates = [candidate for candidate in training
                          if action_signature(candidate, baselines[candidate.group_id]) == signature]
            row: dict[str, Any] = {
                "fold_id": fold["fold_id"], "family_id": cell.group_id,
                "cell_id": cell.cell_id, "probe_issue": origin,
                "supported": bool(candidates),
            }
            if candidates:
                vector = causal_prefix(cell, origin, stage)
                distance, nearest = min(
                    ((rms_distance(vector, causal_prefix(candidate, int(candidate.probe_issue), stage)),
                      candidate) for candidate in candidates),
                    key=lambda value: (value[0], value[1].cell_id),
                )
                truth = paired_truth(cell, baselines[cell.group_id])
                prediction = paired_truth(nearest, baselines[nearest.group_id])
                peak = int(np.argmax(np.linalg.norm(truth[:, :2], axis=1)))
                row.update({
                    "nearest_cell_id": nearest.cell_id,
                    "nearest_family_id": nearest.group_id,
                    "prefix_rms_distance": distance,
                    "truth_response_scaled": (truth / data.response_scale).tolist(),
                    "predicted_response_scaled": (prediction / data.response_scale).tolist(),
                    "peak_horizon": peak + 1,
                    "peak_cosine": cosine(truth[peak, :2], prediction[peak, :2]),
                    "truth_peak_rz_m": truth[peak, :2].tolist(),
                    "predicted_peak_rz_m": prediction[peak, :2].tolist(),
                })
            items.append(row)
            family_items.setdefault(cell.group_id, []).append(row)

    supported = [item for item in items if item["supported"]]
    truth = np.concatenate([np.asarray(item["truth_response_scaled"], dtype=float)
                            for item in supported])
    prediction = np.concatenate([np.asarray(item["predicted_response_scaled"], dtype=float)
                                 for item in supported])
    full_family_regret = []
    full_families = []
    for family, rows in sorted(family_items.items()):
        if len(rows) != 4 or not all(row["supported"] for row in rows):
            continue
        truth_peak = np.asarray([row["truth_peak_rz_m"] for row in rows], dtype=float)
        predicted_peak = np.asarray([row["predicted_peak_rz_m"] for row in rows], dtype=float)
        value = ranking_regret(truth_peak, predicted_peak)
        full_family_regret.append(value)
        full_families.append({"family_id": family, "ranking_regret": value})
    nrmse = float(np.linalg.norm(prediction - truth) / np.linalg.norm(truth))
    return {
        "probe_count": len(items),
        "supported_probe_count": len(supported),
        "unsupported_probe_count": len(items) - len(supported),
        "support_fraction": len(supported) / len(items),
        "positive_supported_peak_directions": sum(int(item["peak_cosine"] > 0)
                                                   for item in supported),
        "supported_response_nrmse": nrmse,
        "complete_supported_family_count": len(full_families),
        "maximum_supported_family_action_ranking_regret":
            max(full_family_regret) if full_family_regret else None,
        "complete_supported_families": full_families,
        "unsupported_cell_ids": [item["cell_id"] for item in items if not item["supported"]],
        "items": items,
    }


def phase_attribution(paired_rows: Sequence[dict[str, Any]], data: q1.Dataset) -> list[dict[str, Any]]:
    cell_map = {cell.cell_id: cell for cell in data.cells}
    baselines = baseline_map(data.cells)
    grouped: dict[tuple[str, str], list[np.ndarray]] = {}
    for row in paired_rows:
        cell = cell_map[row["cell_id"]]
        baseline = baselines[cell.group_id]
        origin = int(cell.probe_issue)
        horizon = int(row["horizon"])
        delta = cell.issued[origin:origin + 8] - baseline.issued[origin:origin + 8]
        active = np.asarray([np.max(np.abs(value)) > 1e-12 for value in delta])
        index = horizon - 1
        if horizon == 1:
            phase = "first_effect"
        elif active[index]:
            phase = "dwell"
        elif index > 0 and active[index - 1]:
            phase = "return_edge"
        else:
            phase = "tail"
        key = (row["candidate"], phase)
        grouped.setdefault(key, []).append(np.asarray(row["response_error_rzi"], dtype=float))
    output = []
    for (candidate, phase), errors in sorted(grouped.items()):
        array = np.asarray(errors)
        output.append({
            "candidate": candidate,
            "phase": phase,
            "row_count": len(errors),
            "p95_abs_error_rzi": np.quantile(np.abs(array), 0.95, axis=0).tolist(),
            "maximum_abs_error_rzi": np.max(np.abs(array), axis=0).tolist(),
        })
    return output


def nominal_attribution(prediction_rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[np.ndarray]] = {}
    for row in prediction_rows:
        if row["cell_kind"] != "baseline":
            continue
        grouped.setdefault(row["candidate"], []).append(
            np.asarray(row["error_rzi"], dtype=float))
    output = []
    for candidate, errors in sorted(grouped.items()):
        array = np.asarray(errors)
        output.append({
            "candidate": candidate,
            "row_count": len(errors),
            "p95_abs_error_rzi": np.quantile(np.abs(array), 0.95, axis=0).tolist(),
            "maximum_abs_error_rzi": np.max(np.abs(array), axis=0).tolist(),
        })
    return output


def route_for(stage: dict[str, Any], ridge_families: Sequence[dict[str, Any]],
              local: dict[str, Any], geometry: Sequence[dict[str, Any]],
              schedule_counts: dict[str, int], family_replays: dict[str, int]) -> tuple[str, dict[str, Any]]:
    gates = stage["route_gates"]
    critical_id = gates["critical_singleton_family_id"]
    critical = next(row for row in ridge_families if row["family_id"] == critical_id)
    wrong = critical["probe_count"] - critical["positive_peak_directions"]
    critical_key = critical["schedule_stratum_key"]
    critical_route = bool(
        schedule_counts[critical_key] == 1
        and wrong == int(gates["critical_singleton_required_wrong_ridge_directions"])
        and family_replays.get(critical_id, 0) ==
        int(gates["critical_singleton_required_exact_replays"])
    )
    local_gates = {
        "support_fraction": local["support_fraction"] >=
                            float(gates["minimum_exact_schedule_support_fraction"]),
        "all_supported_directions": local["positive_supported_peak_directions"] ==
                                    local["supported_probe_count"],
        "response_nrmse": local["supported_response_nrmse"] <=
                          float(gates["maximum_supported_response_nrmse"]),
        "ranking_regret": (
            local["maximum_supported_family_action_ranking_regret"] is not None and
            local["maximum_supported_family_action_ranking_regret"] <=
            float(gates["maximum_supported_family_action_ranking_regret_fraction"])
        ),
    }
    sequence_geometry = all(row["all_horizon_sample_geometry"]["positive_span_geometry"]
                            for row in geometry)
    detail = {"critical_singleton_gate": critical_route,
              "critical_singleton_wrong_directions": wrong,
              "critical_singleton_schedule_family_count": schedule_counts[critical_key],
              "critical_singleton_replay_count": family_replays.get(critical_id, 0),
              "local_route_gates": local_gates,
              "all_family_time_sample_direction_geometry": sequence_geometry}
    if critical_route:
        return stage["routes"]["critical_singleton_f03_replay"], detail
    if all(local_gates.values()) and local["support_fraction"] < 1.0:
        return stage["routes"]["targeted_bridge"], detail
    if not all(local_gates.values()) or not sequence_geometry:
        return stage["routes"]["sequence_authority_shooting"], detail
    if local["support_fraction"] == 1.0 and sequence_geometry:
        return stage["routes"]["support_gated_local_model"], detail
    return stage["routes"]["inconclusive"], detail


def compute(path: Path = CONFIG, source_revision: str = "development") -> tuple[dict[str, Any], dict[str, Any]]:
    stage, qstage, data, qresult = load_stage(path)
    cell_replays, family_replays = compact_replay_counts(qstage)
    prediction_rows: list[dict[str, Any]] = []
    paired_rows: list[dict[str, Any]] = []
    candidate_rows = []
    all_family_rows: dict[str, list[dict[str, Any]]] = {}
    reported = {row["kind"]: row for row in qresult["candidate_results"]}
    for candidate in stage["diagnostic_refit"]["candidates"]:
        folds = []
        family_rows = []
        for fold in qstage["whole_family_folds"]:
            held_ids = set(fold["held"])
            training = [cell for cell in data.cells if cell.group_id not in held_ids]
            held = [cell for cell in data.cells if cell.group_id in held_ids]
            model = (q1.fit_ridge(training, data, qstage)
                     if candidate.endswith("ridge") else q1.fit_gru(training, data, qstage))
            condition = model.condition if isinstance(model, q1.RidgeModel) else model.base.condition
            metrics = q1.evaluate(model, held, data, qstage)
            expected_fold = next(row for row in reported[candidate]["folds"]
                                 if row["fold_id"] == fold["fold_id"])
            aggregate_exact = (metrics == expected_fold["metrics"] and
                               condition == expected_fold["scaled_feature_condition"])
            if not aggregate_exact:
                raise IntegrityError(f"Q1 aggregate reproduction failed: {candidate}/{fold['fold_id']}")
            explicit = explicit_family_metrics(model, held, data, qstage, candidate,
                                               fold["fold_id"], prediction_rows, paired_rows)
            family_rows.extend(explicit)
            folds.append({
                "fold_id": fold["fold_id"],
                "held_families": fold["held"],
                "q1_aggregate_exactly_reproduced": aggregate_exact,
                "scaled_feature_condition": condition,
                "blockwise_design": blockwise_design(training, data, qstage),
                "family_metrics": explicit,
            })
        candidate_rows.append({"candidate": candidate, "folds": folds})
        all_family_rows[candidate] = family_rows

    baselines = baseline_map(data.cells)
    stratum_by_family = {}
    for family in sorted(baselines):
        probe = next(cell for cell in data.cells
                     if cell.group_id == family and cell.cell_kind == "probe")
        signature = schedule_stratum_signature(probe, baselines[family])
        stratum_by_family[family] = json.dumps(signature, separators=(",", ":"))
    schedule_counts: dict[str, int] = {}
    for value in stratum_by_family.values():
        schedule_counts[value] = schedule_counts.get(value, 0) + 1
    for candidate, rows in all_family_rows.items():
        for row in rows:
            row["schedule_stratum_key"] = stratum_by_family[row["family_id"]]
            row["schedule_stratum_family_count"] = schedule_counts[row["schedule_stratum_key"]]
            row["family_integrity_replay_count"] = family_replays.get(row["family_id"], 0)

    local = nearest_history_diagnostic(data, qstage, stage)
    geometry = measured_geometry(data)
    route, route_detail = route_for(stage, all_family_rows["stable_shared_latent_ridge"],
                                    local, geometry, schedule_counts, family_replays)
    predictions = {
        "schema_version": PREDICTION_SCHEMA,
        "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "endpoint_prediction_rows": prediction_rows,
        "paired_response_rows": paired_rows,
    }
    result = {
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "audit_passed": True,
        "route": route,
        "q1_original_route": qresult["route"],
        "q1_original_verdict_unchanged": True,
        "q1_aggregate_exactly_reproduced": True,
        "reporting_erratum": {
            "q03_ridge_wrong_direction_family": "f03",
            "q01_sorted_family_order": ["f01", "f05", "h01", "h05"],
            "withdrawn_bridge_targets": ["h01", "h03", "h05"],
        },
        "candidate_fold_refits": 8,
        "new_candidate_count": 0,
        "full_data_model_fits": 0,
        "model_payloads_emitted": 0,
        "gru_members_refit": 12,
        "new_tsc_calls": 0,
        "reset_calls": 0,
        "plant_advances": 0,
        "n1_records_read": 0,
        "prediction_row_count": len(prediction_rows),
        "paired_response_row_count": len(paired_rows),
        "predictions_canonical_sha256": canonical_sha(predictions),
        "candidate_diagnostics": candidate_rows,
        "local_nearest_history_diagnostic": local,
        "schedule_strata": [{"schedule_stratum_key": key, "family_count": value}
                             for key, value in sorted(schedule_counts.items())],
        "cell_integrity_replay_counts": cell_replays,
        "family_integrity_replay_counts": family_replays,
        "measured_time_resolved_action_geometry": geometry,
        "nominal_continuation_attribution": nominal_attribution(prediction_rows),
        "phase_attribution": phase_attribution(paired_rows, data),
        "route_detail": route_detail,
        "claim_boundary": stage["claim_boundary"],
    }
    return result, predictions


def write_new(path: Path, value: Any) -> None:
    path = inside(path, "output")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise IntegrityError(f"output exists: {path}")
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
                    encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result, predictions = compute(args.config, args.source_revision)
        output = inside(args.output_dir, "output directory")
        if output.exists():
            raise IntegrityError("output directory exists")
        output.mkdir(parents=True)
        write_new(output / "predictions.json", predictions)
        write_new(output / "result.json", result)
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        return 0 if result["audit_passed"] else 2
    except (IntegrityError, q1.IntegrityError, OSError, ValueError, KeyError,
            json.JSONDecodeError) as exc:
        print(json.dumps({"audit_passed": False,
                          "route": "ONE_MS_ID2R0_INPUT_OR_REPRODUCTION_FAIL_STOP",
                          "error": f"{type(exc).__name__}: {exc}"}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
