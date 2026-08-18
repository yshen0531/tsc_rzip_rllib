#!/usr/bin/env python3
"""ID-2M0 deterministic diagnostic refit and attribution.

This stage refits only the four frozen ID-2L1 ``stable_signed_even`` folds.
It is a retrospective development diagnostic, not model selection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

import rgeo_zgeo_1ms_id2l1_structured_history_model as l1


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "rgeo_zgeo_1ms_id2m0_diagnostic_refit_attribution.json"
CONFIG_SHA256 = "054c1b2a35fd317a3723db8a9d022a94350f6646d96e825f3fa9b37d8b2ad662"
SCHEMA = "rgeo-zgeo-1ms-id2m0-diagnostic-refit-attribution-result-v1"
PREDICTION_SCHEMA = "rgeo-zgeo-1ms-id2m0-per-issue-predictions-v1"
KIND = "stable_signed_even"


class IntegrityError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


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


def _exact(value: Any, expected: Any, label: str) -> None:
    if value != expected:
        raise IntegrityError(f"frozen field changed: {label}")


def load_stage(path: Path = CONFIG) -> dict[str, Any]:
    path = inside(path, "stage config")
    if path != CONFIG.resolve() or sha256(path) != CONFIG_SHA256:
        raise IntegrityError("ID2M0 config identity changed")
    stage = json.loads(path.read_text(encoding="utf-8"))
    _exact(stage["schema_version"], "rgeo-zgeo-1ms-id2m0-diagnostic-refit-attribution-v1", "schema")
    _exact(stage["stage"], "ID-2M0", "stage")
    _exact((stage["new_tsc_calls"], stage["reset_calls"], stage["plant_advances"]), (0, 0, 0), "zero plant")
    _exact(stage["source"]["required_candidate"], KIND, "candidate")
    _exact(stage["source"]["required_fold_models"], 4, "fold count")
    _exact(stage["diagnostic_refit"]["new_candidates"], 0, "new candidates")
    _exact(stage["diagnostic_refit"]["hyperparameter_changes"], 0, "hyperparameters")
    _exact(stage["diagnostic_refit"]["persist_fold_coefficients"], False, "coefficient persistence")
    _exact(stage["diagnostic_refit"]["model_artifact_authorized"], False, "model artifact")
    _exact(stage["diagnostic_refit"]["prediction_issue_range_inclusive"], [16, 33], "issue range")
    _exact(stage["diagnostic_refit"]["issue_to_effect_state_offset"], 1, "effect offset")
    for key, expected in {
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
    for field in ("id2l1_config", "id2l1_implementation", "id2l1_primary", "id2l1_independent"):
        source_path = inside(ROOT / stage["source"][field], field)
        if sha256(source_path) != stage["source"][f"{field}_sha256"]:
            raise IntegrityError(f"source hash changed: {field}")
    return stage


def load_inputs(stage: dict[str, Any]) -> tuple[dict[str, Any], l1.Dataset, dict[str, Any]]:
    source = stage["source"]
    l1_stage = l1.load_stage(inside(ROOT / source["id2l1_config"], "ID2L1 config"))
    primary = json.loads(inside(ROOT / source["id2l1_primary"], "ID2L1 result").read_text(encoding="utf-8"))
    independent = json.loads(inside(ROOT / source["id2l1_independent"], "ID2L1 audit").read_text(encoding="utf-8"))
    _exact(primary["route"], source["required_id2l1_route"], "ID2L1 route")
    _exact(primary["comparison"]["selected_candidate"], source["required_selected_model"], "ID2L1 selection")
    _exact(primary["model_payload_sha256"], source["required_model_payload_sha256"], "ID2L1 model payload")
    _exact(primary["holdout_records_read"], 0, "ID2L1 holdout use")
    if not independent.get("audit_passed"):
        raise IntegrityError("ID2L1 independent refit report did not pass")
    data = l1.extract_dataset(l1_stage)
    _exact(len(data.cells), source["required_unique_cells"], "unique cells")
    _exact(len({cell.group_id for cell in data.cells}), source["required_whole_history_families"], "histories")
    return l1_stage, data, primary


def _numeric_max_difference(actual: Any, expected: Any) -> float:
    if isinstance(expected, dict):
        if set(actual) != set(expected):
            raise IntegrityError("aggregate key set changed")
        return max((_numeric_max_difference(actual[key], expected[key]) for key in expected), default=0.0)
    if isinstance(expected, list):
        if len(actual) != len(expected):
            raise IntegrityError("aggregate list length changed")
        return max((_numeric_max_difference(a, e) for a, e in zip(actual, expected)), default=0.0)
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        return abs(float(actual) - float(expected))
    if actual != expected:
        raise IntegrityError(f"aggregate categorical value changed: {actual!r} != {expected!r}")
    return 0.0


def _array_hash(parts: Iterable[np.ndarray | str | int]) -> str:
    digest = hashlib.sha256()
    for part in parts:
        if isinstance(part, np.ndarray):
            value = np.ascontiguousarray(part, dtype=np.float64)
            digest.update(str(value.shape).encode("ascii"))
            digest.update(value.tobytes())
        else:
            digest.update(str(part).encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def one_step_key(cell: l1.Cell, issue: int) -> str:
    return _array_hash(("one", issue, cell.states[:issue + 1], cell.currents[:issue + 1], cell.issued[:issue + 1]))


def segment_key(cell: l1.Cell, origin: int, issue: int) -> str:
    return _array_hash(("segment", origin, issue, cell.states[:origin + 1], cell.currents[:origin + 1], cell.issued[:issue + 1]))


def _event(cell: l1.Cell, data: l1.Dataset, issue: int) -> dict[str, Any]:
    current = cell.issued[issue]
    previous = data.source_current if issue == 0 else cell.issued[issue - 1]
    nominal = data.nominal_issued[issue]
    edge = float(np.max(np.abs(current - previous))) > 1e-12
    at_nominal = bool(np.max(np.abs(current - nominal)) <= 1e-12)
    previous_nominal = issue == 0 or bool(np.max(np.abs(previous - data.nominal_issued[issue - 1])) <= 1e-12)
    dwell_age = 1
    for prior in range(issue - 1, -1, -1):
        if np.array_equal(cell.issued[prior], current):
            dwell_age += 1
        else:
            break
    recent_non_nominal = any(
        np.max(np.abs(cell.issued[prior] - data.nominal_issued[prior])) > 1e-12
        for prior in range(max(0, issue - 4), issue)
    )
    return {
        "action_edge": edge,
        "dwell_age_steps": dwell_age,
        "return_edge": bool(edge and at_nominal and not previous_nominal),
        "delayed_tail": bool(at_nominal and previous_nominal and recent_non_nominal),
        "common_conditioner_prefix": issue < 25,
        "probe_or_return_window": 25 <= issue <= 28,
    }


def _contributions(model: l1.RidgeModel, cell: l1.Cell, data: l1.Dataset,
                   stage: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    features = l1.feature_matrix(cell, data, stage, KIND)
    width = len(stage["backbone"]["fixed_poles"]) * data.action_rank * 2
    slices = (slice(0, 34), slice(34, 34 + width), slice(34 + width, 34 + 2 * width))
    values = []
    for section in slices:
        normalized = features[:, section] / model.scale[section]
        values.append((normalized @ model.coefficients[section]) * data.response_scale)
    total = sum(values)
    direct = model.normalized_deltas(cell, data) * data.response_scale
    if not np.allclose(total, direct, rtol=0.0, atol=1e-12):
        raise IntegrityError("feature contributions do not sum to prediction")
    return values[0], values[1], values[2], total


def _deduplicated_metrics(rows: Sequence[dict[str, Any]], key_name: str) -> tuple[list[float], int]:
    unique: dict[str, np.ndarray] = {}
    truths: dict[str, np.ndarray] = {}
    predictions: dict[str, np.ndarray] = {}
    for row in rows:
        key = row[key_name]
        error = np.asarray(row["error_rzi"], dtype=np.float64)
        truth = np.asarray(row["truth_delta_rzi"], dtype=np.float64)
        prediction = np.asarray(row["predicted_delta_rzi"], dtype=np.float64)
        if key in unique:
            if not (np.array_equal(error, unique[key]) and np.array_equal(truth, truths[key])
                    and np.array_equal(prediction, predictions[key])):
                raise IntegrityError(f"duplicate causal key disagrees: {key}")
        else:
            unique[key] = error
            truths[key] = truth
            predictions[key] = prediction
    array = np.asarray(list(unique.values()), dtype=np.float64)
    return np.quantile(np.abs(array), 0.95, axis=0).tolist(), len(unique)


def _recenter_rows(model: l1.RidgeModel, held: Sequence[l1.Cell], data: l1.Dataset,
                   period: int) -> list[dict[str, Any]]:
    rows = []
    for cell in held:
        origin = 16
        while origin < 34:
            stop = min(34, origin + period)
            predicted = l1._predict_segment(model, cell, data, origin, stop)
            for offset, issue in enumerate(range(origin, stop), start=1):
                error = predicted[offset] - cell.states[issue + 1]
                rows.append({
                    "cell_id": cell.cell_id,
                    "origin_state": origin,
                    "issue": issue,
                    "segment_key": segment_key(cell, origin, issue),
                    "truth_delta_rzi": (cell.states[issue + 1] - cell.states[origin]).tolist(),
                    "predicted_delta_rzi": (predicted[offset] - cell.states[origin]).tolist(),
                    "error_rzi": error.tolist(),
                })
            origin = stop
    return rows


def _fold_rows(model: l1.RidgeModel, held: Sequence[l1.Cell], data: l1.Dataset,
               l1_stage: dict[str, Any], fold_id: str) -> list[dict[str, Any]]:
    rows = []
    for cell in held:
        nominal, signed, even, predicted = _contributions(model, cell, data, l1_stage)
        for issue in range(16, 34):
            truth = cell.states[issue + 1] - cell.states[issue]
            error = cell.states[issue] + predicted[issue] - cell.states[issue + 1]
            previous_issued = data.source_current if issue == 0 else cell.issued[issue - 1]
            row = {
                "fold_id": fold_id,
                "held_histories": sorted({item.group_id for item in held}),
                "history": cell.group_id,
                "cell_id": cell.cell_id,
                "cell_kind": cell.cell_kind,
                "direction": cell.direction,
                "sign": cell.sign,
                "issue": issue,
                "effect_state": issue + 1,
                "one_step_key": one_step_key(cell, issue),
                "truth_delta_rzi": truth.tolist(),
                "predicted_delta_rzi": predicted[issue].tolist(),
                "error_rzi": error.tolist(),
                "time_nominal_contribution_rzi": nominal[issue].tolist(),
                "signed_memory_contribution_rzi": signed[issue].tolist(),
                "even_memory_contribution_rzi": even[issue].tolist(),
                "actual_minus_previous_issued_current_a": (cell.currents[issue] - previous_issued).tolist(),
                "candidate_issued_minus_actual_current_a": (cell.issued[issue] - cell.currents[issue]).tolist(),
                **_event(cell, data, issue),
            }
            rows.append(row)
    return rows


def _gru_semantics(data: l1.Dataset, l1_stage: dict[str, Any]) -> dict[str, Any]:
    cell = data.cells[0]
    causal = l1.gru_input(cell, data, l1_stage, context_origin=None)
    rewritten = l1.gru_input(cell, data, l1_stage, context_origin=16)
    context_width = 9
    prior_difference = float(np.max(np.abs(causal[:16, -context_width:] - rewritten[:16, -context_width:])))
    return {
        "candidate": "structured_gru_residual",
        "context_origin": 16,
        "past_rows_checked": 16,
        "maximum_prior_context_rewrite": prior_difference,
        "context_origin_rewrites_prior_context": prior_difference > 0.0,
        "affects_stable_signed_even": False,
        "classification": "candidate_specific_evaluator_implementation_defect",
    }


def compute(stage_path: Path = CONFIG, source_revision: str = "diagnostic") -> tuple[dict[str, Any], dict[str, Any]]:
    stage = load_stage(stage_path)
    l1_stage, data, primary = load_inputs(stage)
    saved = primary["comparison"]["candidates"][KIND]
    fold_results = []
    predictions = []
    maximum_reproduction_difference = 0.0
    over_counts = []
    unique_over_counts = []
    probe_maxima = []
    for fold, saved_fold in zip(l1_stage["folds"], saved["folds"]):
        held_set = set(fold["held_histories"])
        train = [cell for cell in data.cells if cell.group_id not in held_set]
        held = [cell for cell in data.cells if cell.group_id in held_set]
        model = l1.fit_ridge(KIND, train, data, l1_stage)
        metrics = {"fold_id": fold["fold_id"], "held_histories": fold["held_histories"], **l1.evaluate(model, held, data, l1_stage)}
        reproduction = _numeric_max_difference(metrics, saved_fold)
        maximum_reproduction_difference = max(maximum_reproduction_difference, reproduction)
        rows = _fold_rows(model, held, data, l1_stage, fold["fold_id"])
        predictions.extend(rows)
        unique_p95, unique_count = _deduplicated_metrics(rows, "one_step_key")
        threshold = float(stage["diagnostic_refit"]["one_step_r_threshold_m"])
        over = [row for row in rows if abs(float(row["error_rzi"][0])) > threshold]
        unique_over = {row["one_step_key"]: row for row in over}
        over_counts.append(len(over))
        unique_over_counts.append(len(unique_over))
        probe_max = max(abs(float(row["error_rzi"][0])) for row in rows if row["probe_or_return_window"])
        probe_maxima.append(probe_max)
        recenter = {}
        for period in stage["diagnostic_refit"]["recenter_periods_ms"]:
            segment_rows = _recenter_rows(model, held, data, int(period))
            unique_segment_p95, unique_segment_count = _deduplicated_metrics(segment_rows, "segment_key")
            recenter[str(period)] = {
                "cell_weighted_p95_abs": metrics["recenter_p95_abs"][str(period)],
                "cell_weighted_rows": len(segment_rows),
                "unique_key_p95_abs": unique_segment_p95,
                "unique_keys": unique_segment_count,
            }
        fold_results.append({
            "fold_id": fold["fold_id"],
            "held_histories": fold["held_histories"],
            "aggregate_reproduction_max_abs_difference": reproduction,
            "cell_weighted_metrics": metrics,
            "one_step_issue16_33": {
                "cell_weighted_rows": len(rows),
                "cell_weighted_p95_abs": np.quantile(np.abs(np.asarray([row["error_rzi"] for row in rows])), 0.95, axis=0).tolist(),
                "unique_keys": unique_count,
                "unique_key_p95_abs": unique_p95,
                "cell_rows_over_r_threshold": len(over),
                "unique_events_over_r_threshold": len(unique_over),
                "over_threshold_events": [unique_over[key] for key in sorted(unique_over)],
                "maximum_probe_window_r_error_m": probe_max,
            },
            "recenter_weighting": recenter,
            "feature_support": {
                "feature_count": int(model.coefficients.shape[0]),
                "coefficient_outputs": int(model.coefficients.shape[1]),
                "coefficients_persisted": False,
            },
        })
    allowed = float(stage["diagnostic_refit"]["maximum_aggregate_numeric_difference"])
    expected = stage["expected_attribution"]
    attribution_checks = {
        "cell_rows_per_fold": [row["one_step_issue16_33"]["cell_weighted_rows"] for row in fold_results],
        "unique_one_step_keys_per_fold": [row["one_step_issue16_33"]["unique_keys"] for row in fold_results],
        "one_step_rows_over_threshold_by_fold": over_counts,
        "one_step_unique_events_over_threshold_by_fold": unique_over_counts,
        "all_over_threshold_events_before_probe": all(row["issue"] < 25 for row in predictions if abs(float(row["error_rzi"][0])) > float(stage["diagnostic_refit"]["one_step_r_threshold_m"])),
        "maximum_probe_window_r_error_m_by_fold": probe_maxima,
    }
    attribution_difference = max(abs(a - b) for a, b in zip(
        attribution_checks["maximum_probe_window_r_error_m_by_fold"], expected["maximum_probe_window_r_error_m_by_fold"]))
    attribution_ok = (
        attribution_checks["cell_rows_per_fold"] == [expected["cell_rows_per_fold"]] * 4
        and attribution_checks["unique_one_step_keys_per_fold"] == [expected["unique_one_step_keys_per_fold"]] * 4
        and over_counts == expected["one_step_rows_over_threshold_by_fold"]
        and unique_over_counts == expected["one_step_unique_events_over_threshold_by_fold"]
        and attribution_checks["all_over_threshold_events_before_probe"] is expected["all_over_threshold_events_before_probe"]
        and attribution_difference <= float(expected["maximum_numeric_tolerance"])
    )
    gru_audit = _gru_semantics(data, l1_stage)
    reproduction_ok = maximum_reproduction_difference <= allowed
    semantics_ok = gru_audit["context_origin_rewrites_prior_context"] and not gru_audit["affects_stable_signed_even"]
    passed = reproduction_ok and attribution_ok and semantics_ok
    if not reproduction_ok:
        route = stage["routes"]["aggregate_reproduction_fail"]
    elif not attribution_ok or not semantics_ok:
        route = stage["routes"]["attribution_or_semantics_fail"]
    else:
        route = stage["routes"]["pass"]
    prediction_payload = {
        "schema_version": PREDICTION_SCHEMA,
        "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "candidate": KIND,
        "model_coefficients_persisted": False,
        "rows": predictions,
        "claim_boundary": stage["claim_boundary"],
    }
    result = {
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "source_id2l1_result_sha256": stage["source"]["id2l1_primary_sha256"],
        "source_id2l1_independent_sha256": stage["source"]["id2l1_independent_sha256"],
        "source_id2l1_implementation_revision": stage["source"]["id2l1_implementation_revision"],
        "candidate": KIND,
        "diagnostic_refits": 4,
        "new_candidates": 0,
        "hyperparameter_changes": 0,
        "model_payload_sha256": None,
        "prediction_payload_sha256": canonical_sha256(prediction_payload),
        "maximum_aggregate_reproduction_difference": maximum_reproduction_difference,
        "aggregate_reproduction_passed": reproduction_ok,
        "attribution_checks": attribution_checks,
        "attribution_expectation_max_difference": attribution_difference,
        "attribution_passed": attribution_ok,
        "evaluator_semantics": gru_audit,
        "folds": fold_results,
        "id2l1_formal_verdict_unchanged": primary["route"],
        "id2l1_formal_passed_unchanged": primary["passed"],
        "id2i1_records_read": 0,
        "id2j0_records_read": 0,
        "id2c2_records_read": 0,
        "calibration_records_read": 0,
        "holdout_records_read": 0,
        "reset_calls": 0,
        "tsc_calls": 0,
        "plant_advances": 0,
        "passed": passed,
        "route": route,
        "id2m1_design_authorized": passed,
        "controller_authorized": False,
        "claim_boundary": stage["claim_boundary"],
    }
    return result, prediction_payload


def execute(stage_path: Path, source_revision: str, output_dir: Path) -> dict[str, Any]:
    result, predictions = compute(stage_path, source_revision)
    output_dir = inside(output_dir, "output directory")
    if output_dir.exists():
        raise IntegrityError(f"output directory already exists: {output_dir}")
    output_dir.mkdir(parents=True)
    write_new(output_dir / "predictions.json", predictions)
    write_new(output_dir / "result.json", result)
    return result


def preflight(stage_path: Path = CONFIG) -> dict[str, Any]:
    stage = load_stage(stage_path)
    l1_stage, data, primary = load_inputs(stage)
    return {
        "passed": True,
        "stage_config_sha256": CONFIG_SHA256,
        "candidate": KIND,
        "folds": len(l1_stage["folds"]),
        "cells": len(data.cells),
        "source_route": primary["route"],
        "reset_calls": 0,
        "tsc_calls": 0,
        "plant_advances": 0,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    pre = sub.add_parser("preflight")
    pre.add_argument("--config", type=Path, default=CONFIG)
    run = sub.add_parser("run")
    run.add_argument("--config", type=Path, default=CONFIG)
    run.add_argument("--source-revision", required=True)
    run.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "preflight":
            value = preflight(args.config)
        else:
            value = execute(args.config, args.source_revision, args.output_dir)
        print(json.dumps(value, indent=2, sort_keys=True, allow_nan=False))
        return 0 if value.get("passed") else 2
    except (IntegrityError, l1.IntegrityError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"passed": False, "error": f"{type(exc).__name__}: {exc}"}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
