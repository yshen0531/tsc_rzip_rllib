#!/usr/bin/env python3
"""ID-2M1 bounded causal event/innovation model comparison."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np

import rgeo_zgeo_1ms_id2l1_structured_history_model as l1
import rgeo_zgeo_1ms_id2m0_diagnostic_refit_attribution as m0


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "rgeo_zgeo_1ms_id2m1_bounded_event_innovation_model.json"
CONFIG_SHA256 = "0ddc920f5300033d9c4c9ce3328e69f33dcc863a6634fbc7b3f19fa8ba1ebff3"
SCHEMA = "rgeo-zgeo-1ms-id2m1-bounded-event-innovation-result-v1"
MODEL_SCHEMA = "rgeo-zgeo-1ms-id2m1-bounded-event-innovation-model-v1"
CANDIDATES = ("separated_event_memory", "separated_event_bounded_innovation")


class IntegrityError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                      allow_nan=False).encode("utf-8")).hexdigest()


def inside(path: Path, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise IntegrityError(f"{label} escapes repository: {resolved}") from exc
    return resolved


def write_new(path: Path, value: Any) -> None:
    path = inside(path, "output")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def _exact(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise IntegrityError(f"frozen field changed: {label}")


def load_stage(path: Path = CONFIG) -> dict[str, Any]:
    path = inside(path, "stage config")
    if path != CONFIG.resolve() or sha256(path) != CONFIG_SHA256:
        raise IntegrityError("ID2M1 config identity changed")
    stage = json.loads(path.read_text(encoding="utf-8"))
    _exact(stage["schema_version"], "rgeo-zgeo-1ms-id2m1-bounded-event-innovation-model-v1", "schema")
    _exact((stage["new_tsc_calls"], stage["reset_calls"], stage["plant_advances"]), (0, 0, 0), "zero plant")
    _exact(tuple(stage["model"]["candidates"]), CANDIDATES, "candidate set")
    _exact(tuple(stage["model"]["simplicity_order"]), CANDIDATES, "simplicity order")
    _exact(stage["model"]["future_actual_current_forbidden"], True, "future current")
    _exact(stage["model"]["evaluator_labels_forbidden"], True, "label ban")
    _exact(stage["model"]["innovation_dimension"], 12, "innovation dimension")
    _exact(stage["evaluation"]["issue_to_effect_state_offset"], 1, "effect offset")
    for key, expected in {
        "id2m0_predictions_as_training_labels": False,
        "id2i1_records_allowed": 0,
        "id2j0_records_allowed": 0,
        "id2c2_records_allowed": 0,
        "calibration_records_allowed": 0,
        "holdout_records_allowed": 0,
        "fixture_authorized": False,
        "expert_authorized": False,
        "controller_authorized": False,
        "mpc_authorized": False,
        "authority_authorized": False,
        "recovery_authorized": False,
        "crossing_authorized": False,
        "adaptation_authorized": False,
        "rl_authorized": False,
    }.items():
        _exact(stage["data_use"][key], expected, f"data_use.{key}")
    design = inside(ROOT / stage["design"]["path"], "design")
    if sha256(design) != stage["design"]["sha256"]:
        raise IntegrityError("design hash changed")
    for field in ("id2l1_config", "id2m0_result", "id2m0_predictions", "id2m0_independent"):
        path_value = inside(ROOT / stage["source"][field], field)
        if sha256(path_value) != stage["source"][f"{field}_sha256"]:
            raise IntegrityError(f"source hash changed: {field}")
    return stage


def load_inputs(stage: dict[str, Any]) -> tuple[dict[str, Any], l1.Dataset]:
    source = stage["source"]
    m0_result = json.loads(inside(ROOT / source["id2m0_result"], "ID2M0 result").read_text(encoding="utf-8"))
    m0_audit = json.loads(inside(ROOT / source["id2m0_independent"], "ID2M0 audit").read_text(encoding="utf-8"))
    _exact(m0_result["route"], source["required_id2m0_route"], "ID2M0 route")
    if not m0_result.get("passed") or not m0_audit.get("audit_passed"):
        raise IntegrityError("ID2M0 did not pass")
    l1_stage = l1.load_stage(inside(ROOT / source["id2l1_config"], "ID2L1 config"))
    data = l1.extract_dataset(l1_stage)
    _exact(len(data.cells), source["required_unique_cells"], "cell count")
    _exact(len({cell.group_id for cell in data.cells}), source["required_whole_history_families"], "history count")
    _exact(len(l1_stage["folds"]), source["required_folds"], "fold count")
    return l1_stage, data


def _dwell_age(issued: np.ndarray, issue: int) -> int:
    age = 1
    for prior in range(issue - 1, -1, -1):
        if np.array_equal(issued[prior], issued[issue]):
            age += 1
        else:
            break
    return age


def action_event_features(cell: l1.Cell, data: l1.Dataset, stage: dict[str, Any]) -> np.ndarray:
    u = l1.action_coordinates(cell, data)
    du = np.vstack([u[0], u[1:] - u[:-1]])
    memory = l1.memory_matrix(cell, data, stage["model"]["fixed_action_poles"])
    rows = []
    for issue in range(34):
        stable = np.concatenate([
            memory["level"][issue].reshape(-1), memory["edge"][issue].reshape(-1),
            memory["level_even"][issue].reshape(-1), memory["edge_even"][issue].reshape(-1),
        ])
        lags = []
        for lag in stage["model"]["edge_lags"]:
            value = du[issue - int(lag)] if issue >= int(lag) else np.zeros(data.action_rank)
            lags.extend((value, np.abs(value)))
        dwell = min(_dwell_age(cell.issued, issue), int(stage["model"]["maximum_dwell_age"]))
        fraction = dwell / float(stage["model"]["maximum_dwell_age"])
        rows.append(np.concatenate([stable, *lags, fraction * u[issue], fraction * np.abs(u[issue])]))
    value = np.asarray(rows, dtype=np.float64)
    if value.shape != (34, 78) or not np.all(np.isfinite(value)):
        raise IntegrityError(f"invalid action/event features: {value.shape}")
    return value


def observable_innovation(cell: l1.Cell, data: l1.Dataset, origin: int) -> np.ndarray:
    previous = max(0, origin - 1)
    start = max(0, origin - 4)
    velocity_one = (cell.states[origin] - cell.states[previous]) / data.state_scale
    velocity_four = (cell.states[origin] - cell.states[start]) / max(1, origin - start) / data.state_scale
    displacement = (cell.states[origin] - data.source_state) / data.state_scale
    previous_issued = data.source_current if origin == 0 else cell.issued[origin - 1]
    current_innovation = (cell.currents[origin] - previous_issued) @ data.action_basis.T
    value = np.concatenate([displacement, velocity_one, velocity_four, current_innovation])
    if value.shape != (12,) or not np.all(np.isfinite(value)):
        raise IntegrityError("invalid observable innovation")
    return np.clip(value, -50.0, 50.0)


def feature_matrix(cell: l1.Cell, data: l1.Dataset, stage: dict[str, Any], kind: str,
                   context_origin: int | None = None) -> np.ndarray:
    action = action_event_features(cell, data, stage)
    if kind == CANDIDATES[0]:
        return action
    if kind != CANDIDATES[1]:
        raise IntegrityError(f"unknown candidate: {kind}")
    pole = float(stage["model"]["innovation_rollout_pole"])
    rows = []
    for issue in range(34):
        if context_origin is None:
            innovation = observable_innovation(cell, data, issue)
        elif issue < context_origin:
            innovation = np.zeros(12, dtype=np.float64)
        else:
            innovation = (pole ** (issue - context_origin)) * observable_innovation(cell, data, context_origin)
        rows.append(np.concatenate([action[issue], innovation]))
    value = np.asarray(rows, dtype=np.float64)
    if value.shape != (34, 90):
        raise IntegrityError(f"invalid innovation features: {value.shape}")
    return value


@dataclass
class SeparatedModel:
    kind: str
    nominal: np.ndarray
    scale: np.ndarray
    coefficients: np.ndarray
    stage: dict[str, Any]
    fit_rank: int
    fit_condition: float
    active_feature_count: int

    def normalized_deltas(self, cell: l1.Cell, data: l1.Dataset,
                          context_origin: int | None = None) -> np.ndarray:
        features = feature_matrix(cell, data, self.stage, self.kind, context_origin)
        return self.nominal + (features / self.scale) @ self.coefficients

    def payload(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "nominal_normalized_delta": self.nominal.tolist(),
            "feature_scale": self.scale.tolist(),
            "coefficients": self.coefficients.tolist(),
            "fit_rank": self.fit_rank,
            "fit_condition": self.fit_condition,
            "active_feature_count": self.active_feature_count,
        }


def _unique_training_rows(cells: Sequence[l1.Cell], data: l1.Dataset, stage: dict[str, Any], kind: str
                          ) -> tuple[list[np.ndarray], list[np.ndarray], list[int], dict[str, np.ndarray]]:
    seen: dict[str, tuple[np.ndarray, np.ndarray, int]] = {}
    features_by_cell = {cell.cell_id: feature_matrix(cell, data, stage, kind) for cell in cells}
    for cell in cells:
        target = (cell.states[1:] - cell.states[:-1]) / data.response_scale
        features = features_by_cell[cell.cell_id]
        for issue in range(34):
            key = m0.one_step_key(cell, issue)
            if key in seen:
                old_x, old_y, old_issue = seen[key]
                if old_issue != issue or not np.array_equal(old_x, features[issue]) or not np.array_equal(old_y, target[issue]):
                    raise IntegrityError("duplicate training transition disagrees")
            else:
                seen[key] = (features[issue], target[issue], issue)
    x = [value[0] for value in seen.values()]
    y = [value[1] for value in seen.values()]
    issues = [value[2] for value in seen.values()]
    return x, y, issues, features_by_cell


def fit_model(kind: str, cells: Sequence[l1.Cell], data: l1.Dataset, stage: dict[str, Any]) -> SeparatedModel:
    x_rows, y_rows, issues, by_cell = _unique_training_rows(cells, data, stage, kind)
    x_array = np.asarray(x_rows, dtype=np.float64)
    y_array = np.asarray(y_rows, dtype=np.float64)
    issue_array = np.asarray(issues, dtype=np.int64)
    mean_x = np.zeros((34, x_array.shape[1]), dtype=np.float64)
    mean_y = np.zeros((34, 3), dtype=np.float64)
    centered_x = []
    centered_y = []
    for issue in range(34):
        mask = issue_array == issue
        if not np.any(mask):
            raise IntegrityError(f"missing training issue: {issue}")
        mean_x[issue] = np.mean(x_array[mask], axis=0)
        mean_y[issue] = np.mean(y_array[mask], axis=0)
        centered_x.append(x_array[mask] - mean_x[issue])
        centered_y.append(y_array[mask] - mean_y[issue])
    fit_x = [np.concatenate(centered_x)]
    fit_y = [np.concatenate(centered_y)]
    weight = math.sqrt(float(stage["model"]["paired_loss_weight"]))
    start = int(stage["model"]["paired_loss_start_issue"])
    by_group = {group: next(cell for cell in cells if cell.group_id == group and cell.cell_kind == "baseline")
                for group in sorted({cell.group_id for cell in cells})}
    for cell in cells:
        if cell.cell_kind == "baseline":
            continue
        baseline = by_group[cell.group_id]
        target = (cell.states[1:] - cell.states[:-1]) / data.response_scale
        base_target = (baseline.states[1:] - baseline.states[:-1]) / data.response_scale
        fit_x.append(weight * (by_cell[cell.cell_id][start:] - by_cell[baseline.cell_id][start:]))
        fit_y.append(weight * (target[start:] - base_target[start:]))
    x = np.concatenate(fit_x)
    y = np.concatenate(fit_y)
    scale = np.sqrt(np.mean(x * x, axis=0))
    active = scale > 1e-10
    scale = np.where(active, scale, 1.0)
    normalized = x / scale
    singular = np.linalg.svd(normalized, compute_uv=False)
    positive = singular[singular > max(1e-12, singular[0] * 1e-12)]
    rank = int(len(positive))
    condition = float(positive[0] / positive[-1]) if len(positive) else math.inf
    ridge = float(stage["model"]["ridge"])
    coefficients = np.linalg.solve(normalized.T @ normalized + ridge * np.eye(normalized.shape[1]), normalized.T @ y)
    nominal = mean_y - (mean_x / scale) @ coefficients
    if not np.all(np.isfinite(coefficients)) or not np.all(np.isfinite(nominal)):
        raise IntegrityError("non-finite separated model")
    return SeparatedModel(kind, nominal, scale, coefficients, stage, rank, condition, int(np.count_nonzero(active)))


def _cap(values: Sequence[float], caps: Sequence[float]) -> bool:
    return all(math.isfinite(float(value)) and float(value) <= float(cap) for value, cap in zip(values, caps))


def _unique_one_step(model: SeparatedModel, held: Sequence[l1.Cell], data: l1.Dataset,
                     stage: dict[str, Any]) -> dict[str, Any]:
    start, stop = stage["evaluation"]["prediction_issue_range_inclusive"]
    rows = []
    for cell in held:
        delta = model.normalized_deltas(cell, data) * data.response_scale
        for issue in range(int(start), int(stop) + 1):
            error = cell.states[issue] + delta[issue] - cell.states[issue + 1]
            rows.append({
                "key": m0.one_step_key(cell, issue),
                "cell_id": cell.cell_id,
                "history": cell.group_id,
                "issue": issue,
                "error_rzi": error.tolist(),
                "truth_delta_rzi": (cell.states[issue + 1] - cell.states[issue]).tolist(),
                "predicted_delta_rzi": delta[issue].tolist(),
                **m0._event(cell, data, issue),
            })
    p95, count = m0._deduplicated_metrics(rows, "key")
    unique = {}
    for row in rows:
        unique.setdefault(row["key"], row)
    worst = np.max(np.abs(np.asarray([row["error_rzi"] for row in unique.values()])), axis=0).tolist()
    threshold = 0.0003
    over = [row for row in unique.values() if abs(float(row["error_rzi"][0])) > threshold]
    low, high = stage["evaluation"]["probe_issue_window_inclusive"]
    probe_max = np.max(np.abs(np.asarray([row["error_rzi"] for row in rows if low <= row["issue"] <= high])), axis=0).tolist()
    return {"cell_rows": len(rows), "unique_keys": count, "unique_p95_abs": p95,
            "worst_unique_abs": worst, "unique_r_events_over_0p3mm": over,
            "probe_window_max_abs": probe_max}


def _unique_recenter(model: SeparatedModel, held: Sequence[l1.Cell], data: l1.Dataset,
                     stage: dict[str, Any], period: int) -> dict[str, Any]:
    rows = []
    for cell in held:
        origin = int(stage["evaluation"]["recenter_origin_state"])
        while origin < 34:
            stop = min(34, origin + period)
            predicted = l1._predict_segment(model, cell, data, origin, stop)
            for offset, issue in enumerate(range(origin, stop), start=1):
                rows.append({
                    "key": m0.segment_key(cell, origin, issue),
                    "error_rzi": (predicted[offset] - cell.states[issue + 1]).tolist(),
                    "truth_delta_rzi": (cell.states[issue + 1] - cell.states[origin]).tolist(),
                    "predicted_delta_rzi": (predicted[offset] - cell.states[origin]).tolist(),
                })
            origin = stop
    p95, count = m0._deduplicated_metrics(rows, "key")
    return {"cell_rows": len(rows), "unique_keys": count, "unique_p95_abs": p95}


def eligibility(metrics: dict[str, Any], diagnostics: dict[str, Any], stage: dict[str, Any]) -> list[str]:
    gate = stage["eligibility"]
    failures = []
    if not _cap(metrics["teacher_one_step_p95_abs"], gate["teacher_one_step_p95_abs_max"]):
        failures.append("TEACHER")
    for period, key in (("1", "recenter_1ms_p95_abs_max"), ("2", "recenter_2ms_p95_abs_max"),
                        ("4", "recenter_4ms_p95_abs_max")):
        if not _cap(metrics["recenter_p95_abs"][period], gate[key]):
            failures.append(f"RECENTER_{period}")
    if not _cap(metrics["free_state25_p95_abs"], gate["free_state25_p95_abs_max"]):
        failures.append("FREE")
    if not _cap(metrics["maximum_abs_error"], gate["catastrophic_max_abs"]):
        failures.append("CATASTROPHIC")
    if not _cap(diagnostics["worst_unique_abs"], gate["worst_unique_one_step_abs_max"]):
        failures.append("WORST_UNIQUE_ONE_STEP")
    if not float(metrics["response_nrmse"]) < float(gate["each_fold_response_nrmse_strict_max"]):
        failures.append("RESPONSE")
    if int(metrics["positive_peak_cosine_count"]) < int(gate["minimum_positive_peak_cosine_per_fold"]):
        failures.append("PEAK")
    return failures


def compare(data: l1.Dataset, l1_stage: dict[str, Any], stage: dict[str, Any]) -> dict[str, Any]:
    summaries = {}
    for kind in CANDIDATES:
        folds = []
        for fold in l1_stage["folds"]:
            held_set = set(fold["held_histories"])
            train = [cell for cell in data.cells if cell.group_id not in held_set]
            held = [cell for cell in data.cells if cell.group_id in held_set]
            model = fit_model(kind, train, data, stage)
            metrics = l1.evaluate(model, held, data, l1_stage)
            one = _unique_one_step(model, held, data, stage)
            unique_recenter = {str(period): _unique_recenter(model, held, data, stage, int(period))
                               for period in stage["evaluation"]["recenter_periods_ms"]}
            failures = eligibility(metrics, one, stage)
            if model.fit_condition > float(stage["eligibility"]["maximum_scaled_feature_condition"]):
                failures.append("FEATURE_CONDITION")
            folds.append({"fold_id": fold["fold_id"], "held_histories": fold["held_histories"],
                          **metrics, "unique_one_step": one, "unique_recenter": unique_recenter,
                          "fit_rank": model.fit_rank, "fit_condition": model.fit_condition,
                          "active_feature_count": model.active_feature_count,
                          "eligibility_failures": failures, "eligible": not failures})
        mean_response = float(np.mean([row["response_nrmse"] for row in folds]))
        total_peaks = int(sum(row["positive_peak_cosine_count"] for row in folds))
        global_failures = []
        if mean_response > float(stage["eligibility"]["mean_response_nrmse_max"]):
            global_failures.append("MEAN_RESPONSE")
        if total_peaks < int(stage["eligibility"]["minimum_positive_peak_cosine_total"]):
            global_failures.append("TOTAL_PEAK")
        eligible = all(row["eligible"] for row in folds) and not global_failures
        summaries[kind] = {"folds": folds, "mean_response_nrmse": mean_response,
                           "total_positive_peak_cosine": total_peaks,
                           "global_eligibility_failures": global_failures, "eligible": eligible}
    selected = next((kind for kind in stage["model"]["simplicity_order"] if summaries[kind]["eligible"]), None)
    return {"candidates": summaries, "selected_candidate": selected,
            "selection_rule": "first_eligible_in_frozen_simplicity_order"}


def model_payload(model: SeparatedModel, data: l1.Dataset, stage: dict[str, Any]) -> dict[str, Any]:
    return {"schema_version": MODEL_SCHEMA, "stage_config_sha256": CONFIG_SHA256,
            "selected_candidate": model.kind, "action_basis": data.action_basis.tolist(),
            "nominal_issued_a": data.nominal_issued.tolist(), "state_scale": data.state_scale.tolist(),
            "response_scale": data.response_scale.tolist(), "issue_to_effect_state_offset": 1,
            "future_actual_current": "forbidden", "model": model.payload(),
            "claim_boundary": stage["claim_boundary"]}


def compute(stage_path: Path = CONFIG, source_revision: str = "development") -> tuple[dict[str, Any], dict[str, Any] | None]:
    stage = load_stage(stage_path)
    l1_stage, data = load_inputs(stage)
    comparison = compare(data, l1_stage, stage)
    selected = comparison["selected_candidate"]
    payload = None
    if selected is not None:
        payload = model_payload(fit_model(selected, data.cells, data, stage), data, stage)
    passed = selected is not None
    result = {
        "schema_version": SCHEMA, "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "source_id2m0_result_sha256": stage["source"]["id2m0_result_sha256"],
        "source_id2m0_predictions_read_as_training_labels": False,
        "unique_cells": len(data.cells), "whole_history_families": len({c.group_id for c in data.cells}),
        "candidates_fit": len(CANDIDATES) * len(l1_stage["folds"]) + int(passed),
        "selected_candidate": selected, "model_payload_sha256": canonical_sha256(payload) if payload else None,
        "comparison": comparison, "id2i1_records_read": 0, "id2j0_records_read": 0,
        "id2c2_records_read": 0, "calibration_records_read": 0, "holdout_records_read": 0,
        "reset_calls": 0, "tsc_calls": 0, "plant_advances": 0,
        "passed": passed,
        "route": stage["routes"]["pass"] if passed else stage["routes"]["no_eligible_candidate"],
        "fresh_calibration_design_authorized": passed,
        "fresh_holdout_design_authorized": passed,
        "controller_authorized": False, "claim_boundary": stage["claim_boundary"],
    }
    return result, payload


def execute(stage_path: Path, source_revision: str, output_dir: Path) -> dict[str, Any]:
    result, payload = compute(stage_path, source_revision)
    output_dir = inside(output_dir, "output directory")
    if output_dir.exists():
        raise IntegrityError(f"output directory exists: {output_dir}")
    output_dir.mkdir(parents=True)
    if payload is not None:
        write_new(output_dir / "model.json", payload)
    write_new(output_dir / "result.json", result)
    return result


def preflight(stage_path: Path = CONFIG) -> dict[str, Any]:
    stage = load_stage(stage_path)
    l1_stage, data = load_inputs(stage)
    return {"passed": True, "stage_config_sha256": CONFIG_SHA256, "candidates": list(CANDIDATES),
            "folds": len(l1_stage["folds"]), "cells": len(data.cells),
            "reset_calls": 0, "tsc_calls": 0, "plant_advances": 0}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("preflight")
    p.add_argument("--config", type=Path, default=CONFIG)
    r = sub.add_parser("run")
    r.add_argument("--config", type=Path, default=CONFIG)
    r.add_argument("--source-revision", required=True)
    r.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        value = preflight(args.config) if args.command == "preflight" else execute(args.config, args.source_revision, args.output_dir)
        print(json.dumps(value, indent=2, sort_keys=True, allow_nan=False))
        return 0 if value.get("passed") else 2
    except (IntegrityError, l1.IntegrityError, m0.IntegrityError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"passed": False, "error": f"{type(exc).__name__}: {exc}"}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
