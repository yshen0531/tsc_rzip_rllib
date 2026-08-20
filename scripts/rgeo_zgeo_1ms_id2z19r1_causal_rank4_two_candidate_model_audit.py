#!/usr/bin/env python3
"""Independent no-fit ledger audit for ID-2Z19R1."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z19r1_causal_rank4_two_candidate_model.json"
CANDIDATES = (
    "structured_rank4_stable_memory",
    "structured_rank4_stable_memory_plus_tcn4",
)
FIT_HORIZONS = tuple(range(1, 9))
QUALIFICATION_HORIZONS = (1, 2, 4, 8)


class AuditError(RuntimeError):
    pass


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AuditError(f"expected object: {path}")
    return value


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def _inside(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise AuditError(f"outside repository: {resolved}") from exc
    return resolved


def _p95(values: Iterable[float]) -> float:
    array = np.asarray(list(values), dtype=np.float64)
    return float(np.percentile(array, 95))


def _cosine(left: np.ndarray, right: np.ndarray) -> float:
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    return float(np.dot(left, right) / denominator) if denominator > 1.0e-15 else math.nan


def _load_truth(stage: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], np.ndarray, np.ndarray]:
    folder = _inside(ROOT / stage["source"]["directory"])
    truth: dict[str, dict[str, Any]] = {}
    for family in stage["development_family_ids"]:
        payload = _read(folder / f"{family}.json")
        if payload.get("fit_weight") != 1 or payload.get("passed") is not True:
            raise AuditError(f"invalid source family {family}")
        states = np.asarray([
            [row["r_geo_m"], row["z_geo_m"], row["ip_a"]]
            for row in payload["states"]
        ], dtype=np.float64)
        active = np.asarray([
            row["active_command_decimal_a_tsc"] for row in payload["states"]
        ], dtype=np.float64)
        targets = np.asarray([
            row["target_current_a_tsc"] for row in payload["actions"]
        ], dtype=np.float64)
        if states.shape != (66, 3) or active.shape != (66, 14) or targets.shape != (65, 14):
            raise AuditError(f"source dimensions {family}")
        truth[family] = {
            "states": states,
            "active": active,
            "targets": targets,
            "pair_id": payload.get("pair_id"),
            "sign": payload.get("sign"),
        }
    first = truth[stage["development_family_ids"][0]]
    return truth, first["states"][0], first["active"][0]


def _recursive_action_diagnostics(
    row: dict[str, Any], source: dict[str, Any], source_active: np.ndarray
) -> tuple[float, float]:
    origin = int(row["origin_issue"])
    horizon = int(row["horizon_ms"])
    previous = source["active"][origin].copy()
    maximum_slew = 0.0
    maximum_excursion = 0.0
    for issue in range(origin, origin + horizon):
        target = source["targets"][issue]
        maximum_slew = max(maximum_slew, float(np.max(np.abs(target - previous))))
        maximum_excursion = max(maximum_excursion, float(np.max(np.abs(target - source_active))))
        previous = target
    return maximum_slew, maximum_excursion


def _family_rmse(rows: Sequence[dict[str, Any]], prediction: str, truth: str, scale: np.ndarray) -> float:
    energies = []
    for family in sorted({row["family_id"] for row in rows}):
        block = [row for row in rows if row["family_id"] == family]
        error = np.asarray([np.asarray(row[prediction]) - np.asarray(row[truth]) for row in block]) / scale
        target = np.asarray([
            np.asarray(row[truth]) - np.asarray(row["origin_state"])
            if truth == "truth_state" else np.asarray(row[truth])
            for row in block
        ]) / scale
        energies.append(float(np.sum(error ** 2)) / max(float(np.sum(target ** 2)), 1.0e-30))
    return math.sqrt(float(np.mean(energies)))


def _value(
    state: np.ndarray,
    terminal: np.ndarray,
    current_excursion: float,
    source_state: np.ndarray,
    stage: dict[str, Any],
) -> float:
    scales = stage["evaluation"]["value_scales"]
    return max(
        float(np.linalg.norm(state[:2] - source_state[:2])) / float(scales["distance_m"]),
        float(np.linalg.norm(terminal[:2]) / 0.001) / float(scales["terminal_speed_m_per_s"]),
        abs(float(state[2] - source_state[2])) / (abs(float(source_state[2])) * float(scales["ip_fraction"])),
        current_excursion / float(scales["current_excursion_a"]),
    )


def _summarize(rows: Sequence[dict[str, Any]], source_state: np.ndarray, stage: dict[str, Any]) -> dict[str, Any]:
    output_scale = np.asarray(stage["structured_rank4_stable_memory"]["output_scale"])
    endpoint_p95: dict[str, list[float]] = {}
    for horizon in QUALIFICATION_HORIZONS:
        block = [row for row in rows if int(row["horizon_ms"]) == horizon]
        error = np.abs(np.asarray([row["predicted_state"] for row in block]) - np.asarray([row["truth_state"] for row in block]))
        endpoint_p95[str(horizon)] = np.percentile(error, 95, axis=0).tolist()
    qualification = [row for row in rows if int(row["horizon_ms"]) in QUALIFICATION_HORIZONS]
    terminal_error = np.abs(
        np.asarray([row["predicted_terminal_increment"] for row in qualification])
        - np.asarray([row["truth_terminal_increment"] for row in qualification])
    )
    terminal_p95 = np.percentile(terminal_error, 95, axis=0)
    lookup = {(row["family_id"], int(row["origin_issue"]), int(row["horizon_ms"])): row for row in rows}
    consistency = []
    for row in rows:
        horizon = int(row["horizon_ms"])
        if horizon == 1:
            continue
        previous = lookup[(row["family_id"], int(row["origin_issue"]), horizon - 1)]
        displacement = np.asarray(row["predicted_state"]) - np.asarray(row["origin_state"])
        prior_displacement = np.asarray(previous["predicted_state"]) - np.asarray(previous["origin_state"])
        consistency.append(np.abs(displacement - prior_displacement - np.asarray(row["predicted_terminal_increment"])))
    persistence = []
    velocity = []
    for row in qualification:
        origin = np.asarray(row["origin_state"])
        truth = np.asarray(row["truth_state"])
        persistence.append(np.abs(origin - truth))
        velocity.append(np.abs(origin + int(row["horizon_ms"]) * np.asarray(row["previous_increment"]) - truth))
    result: dict[str, Any] = {
        "endpoint_p95_abs_by_horizon": endpoint_p95,
        "terminal_increment_p95_abs": terminal_p95.tolist(),
        "terminal_rz_velocity_error_p95_m_per_s": float(max(terminal_p95[:2]) / 0.001),
        "normalized_endpoint_rmse": _family_rmse(rows, "predicted_state", "truth_state", output_scale[:3]),
        "normalized_terminal_increment_rmse": _family_rmse(
            rows, "predicted_terminal_increment", "truth_terminal_increment", output_scale[3:]
        ),
        "support_coverage_fraction": float(np.mean([bool(row["supported"]) for row in rows])),
        "maximum_support_distance": max(float(row["support_distance"]) for row in rows),
        "support_threshold": float(rows[0]["support_threshold"]),
        "cross_horizon_consistency_p95_abs": np.percentile(np.asarray(consistency), 95, axis=0).tolist(),
        "persistence_endpoint_p95_abs": np.percentile(np.asarray(persistence), 95, axis=0).tolist(),
        "constant_velocity_endpoint_p95_abs": np.percentile(np.asarray(velocity), 95, axis=0).tolist(),
        "maximum_candidate_slew_a": max(float(row["candidate_maximum_slew_a"]) for row in rows),
        "maximum_candidate_current_excursion_from_source_a": max(
            float(row["candidate_maximum_current_excursion_from_source_a"]) for row in rows
        ),
        "all_predictions_finite": bool(all(
            np.all(np.isfinite(np.asarray(row[key], dtype=np.float64)))
            for row in rows
            for key in (
                "truth_state", "predicted_state", "truth_terminal_increment",
                "predicted_terminal_increment", "blind_predicted_state",
                "blind_predicted_terminal_increment",
            )
        )),
        "pair_metrics": None,
    }
    families = sorted({row["family_id"] for row in rows})
    if len(families) == 2:
        plus_family = next(family for family in families if family.endswith("_plus"))
        minus_family = next(family for family in families if family.endswith("_minus"))
        by_key = {(row["family_id"], int(row["origin_issue"]), int(row["horizon_ms"])): row for row in rows}
        response_scale = np.asarray([
            stage["evaluation"]["paired_response_scale"]["r_geo_m"],
            stage["evaluation"]["paired_response_scale"]["z_geo_m"],
            stage["evaluation"]["paired_response_scale"]["ip_a"],
        ])
        truth_responses = []
        predicted_responses = []
        blind_responses = []
        cosines = []
        ranking_total = ranking_correct = always_plus = 0
        regrets = []
        for origin in range(stage["origin_issue_range_inclusive"][0], stage["origin_issue_range_inclusive"][1] + 1):
            for horizon in QUALIFICATION_HORIZONS:
                plus = by_key.get((plus_family, origin, horizon))
                minus = by_key.get((minus_family, origin, horizon))
                if plus is None or minus is None:
                    continue
                true = np.asarray(plus["truth_state"]) - np.asarray(minus["truth_state"])
                predicted = np.asarray(plus["predicted_state"]) - np.asarray(minus["predicted_state"])
                blind = np.asarray(plus["blind_predicted_state"]) - np.asarray(minus["blind_predicted_state"])
                if float(np.linalg.norm(true / response_scale)) <= 1.0e-12:
                    continue
                truth_responses.append(true / response_scale)
                predicted_responses.append(predicted / response_scale)
                blind_responses.append(blind / response_scale)
                if float(np.linalg.norm(true[:2])) >= float(stage["evaluation"]["minimum_rz_direction_signal_m"]):
                    cosines.append(_cosine(true[:2], predicted[:2]))
                true_scores = []
                predicted_scores = []
                for item in (plus, minus):
                    true_scores.append(_value(
                        np.asarray(item["truth_state"]), np.asarray(item["truth_terminal_increment"]),
                        float(item["candidate_maximum_current_excursion_from_source_a"]), source_state, stage
                    ))
                    predicted_scores.append(_value(
                        np.asarray(item["predicted_state"]), np.asarray(item["predicted_terminal_increment"]),
                        float(item["candidate_maximum_current_excursion_from_source_a"]), source_state, stage
                    ))
                if abs(true_scores[0] - true_scores[1]) > float(stage["evaluation"]["ranking_tie_band_normalized"]):
                    best = int(np.argmin(true_scores))
                    chosen = int(np.argmin(predicted_scores))
                    ranking_total += 1
                    ranking_correct += int(best == chosen)
                    always_plus += int(best == 0)
                    regrets.append((true_scores[chosen] - true_scores[best]) / max(max(true_scores), 1.0e-12))
        truth_array = np.asarray(truth_responses)
        predicted_array = np.asarray(predicted_responses)
        blind_array = np.asarray(blind_responses)
        sse = float(np.sum((predicted_array - truth_array) ** 2))
        zero_sse = float(np.sum(truth_array ** 2))
        blind_sse = float(np.sum((blind_array - truth_array) ** 2))
        positive = sum(math.isfinite(value) and value > 0.0 for value in cosines)
        finite_cosines = [value for value in cosines if math.isfinite(value)]
        result["pair_metrics"] = {
            "informative_row_count": len(truth_responses),
            "direction_row_count": len(cosines),
            "response_nrmse": math.sqrt(sse / max(zero_sse, 1.0e-30)),
            "fitted_action_blind_response_nrmse": math.sqrt(blind_sse / max(zero_sse, 1.0e-30)),
            "action_blind_response_sse_improvement_fraction": 1.0 - sse / max(blind_sse, 1.0e-30),
            "positive_direction_count": positive,
            "positive_direction_fraction": positive / max(len(cosines), 1),
            "minimum_direction_cosine": min(finite_cosines) if finite_cosines else None,
            "ranking_non_tie_count": ranking_total,
            "ranking_correct_count": ranking_correct,
            "ranking_accuracy": ranking_correct / max(ranking_total, 1),
            "always_plus_correct_count": always_plus,
            "always_plus_accuracy": always_plus / max(ranking_total, 1),
            "maximum_normalized_value_regret": max(regrets, default=0.0),
        }
    return result


def _failures(metrics: dict[str, Any], fold: dict[str, Any], stage: dict[str, Any]) -> list[str]:
    gate = stage["evaluation"]
    reasons: list[str] = []
    if not metrics["all_predictions_finite"]:
        reasons.append("NONFINITE")
    if metrics["normalized_endpoint_rmse"] >= gate["maximum_each_fold_normalized_endpoint_rmse"]:
        reasons.append("ENDPOINT_NRMSE")
    if metrics["normalized_terminal_increment_rmse"] >= gate["maximum_each_fold_normalized_terminal_increment_rmse"]:
        reasons.append("TERMINAL_INCREMENT_NRMSE")
    if metrics["terminal_rz_velocity_error_p95_m_per_s"] > gate["maximum_terminal_rz_velocity_error_m_per_s"]:
        reasons.append("TERMINAL_VELOCITY")
    caps = gate["endpoint_p95_caps"]
    for index, horizon in enumerate(QUALIFICATION_HORIZONS):
        values = metrics["endpoint_p95_abs_by_horizon"][str(horizon)]
        if values[0] > caps["r_geo_m"][index] or values[1] > caps["z_geo_m"][index] or values[2] > caps["ip_a"][index]:
            reasons.append(f"ENDPOINT_P95_H{horizon}")
    values = metrics["terminal_increment_p95_abs"]
    caps_terminal = gate["terminal_increment_p95_caps"]
    if values[0] > caps_terminal["r_geo_m"] or values[1] > caps_terminal["z_geo_m"] or values[2] > caps_terminal["ip_a"]:
        reasons.append("TERMINAL_INCREMENT_P95")
    values = metrics["cross_horizon_consistency_p95_abs"]
    caps_consistency = gate["cross_horizon_consistency_p95_caps"]
    if values[0] > caps_consistency["r_geo_m"] or values[1] > caps_consistency["z_geo_m"] or values[2] > caps_consistency["ip_a"]:
        reasons.append("CROSS_HORIZON_CONSISTENCY")
    if metrics["support_coverage_fraction"] < stage["support"]["minimum_held_row_coverage_fraction"]:
        reasons.append("HELD_SUPPORT")
    if fold["feature_condition"] > stage["structured_rank4_stable_memory"]["maximum_projected_feature_condition"]:
        reasons.append("FEATURE_CONDITION")
    pair = metrics["pair_metrics"]
    if pair is not None:
        if pair["response_nrmse"] >= gate["maximum_each_pair_fold_response_nrmse"]:
            reasons.append("PAIR_RESPONSE_NRMSE")
        if pair["direction_row_count"] < gate["minimum_direction_row_count"]:
            reasons.append("PAIR_DIRECTION_SUPPORT")
        if pair["positive_direction_fraction"] < gate["minimum_positive_direction_fraction"]:
            reasons.append("PAIR_DIRECTION")
        if pair["action_blind_response_sse_improvement_fraction"] < gate["minimum_action_blind_response_sse_improvement_fraction"]:
            reasons.append("ACTION_BLIND_IMPROVEMENT")
    return list(dict.fromkeys(reasons))


def _numeric_equal(left: Any, right: Any, path: str, failures: list[str]) -> None:
    if isinstance(left, dict) and isinstance(right, dict):
        if set(left) != set(right):
            failures.append(f"KEYS:{path}")
            return
        for key in left:
            _numeric_equal(left[key], right[key], f"{path}.{key}", failures)
        return
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            failures.append(f"LENGTH:{path}")
            return
        for index, (a, b) in enumerate(zip(left, right)):
            _numeric_equal(a, b, f"{path}[{index}]", failures)
        return
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        a, b = float(left), float(right)
        if math.isnan(a) and math.isnan(b):
            return
        if not math.isclose(a, b, rel_tol=2.0e-10, abs_tol=2.0e-12):
            failures.append(f"VALUE:{path}:{a}:{b}")
        return
    if left != right:
        failures.append(f"VALUE:{path}:{left!r}:{right!r}")


def audit(output: Path) -> dict[str, Any]:
    output = _inside(output)
    stage = _read(CONFIG)
    result = _read(output / "result.json")
    ledger = _read(output / "oof_predictions.json")
    failures: list[str] = []
    if result.get("stage_config_sha256") != _sha(CONFIG):
        failures.append("RESULT_CONFIG_HASH")
    if ledger.get("stage_config_sha256") != _sha(CONFIG):
        failures.append("LEDGER_CONFIG_HASH")
    if result.get("oof_prediction_ledger_canonical_sha256") != _canonical(ledger):
        failures.append("LEDGER_CANONICAL_HASH")
    rows = ledger.get("rows")
    if not isinstance(rows, list):
        raise AuditError("ledger rows")
    expected_count = len(CANDIDATES) * len(stage["development_family_ids"]) * 42 * 8
    if len(rows) != expected_count or result.get("oof_prediction_row_count") != expected_count:
        failures.append(f"ROW_COUNT:{len(rows)}:{expected_count}")
    keys = [(
        row.get("candidate_id"), row.get("fold_id"), row.get("family_id"),
        row.get("origin_issue"), row.get("horizon_ms"),
    ) for row in rows]
    if len(set(keys)) != len(keys):
        failures.append("DUPLICATE_LEDGER_KEY")

    truth, source_state, source_active = _load_truth(stage)
    fold_for_family = {}
    for fold in stage["whole_history_folds"]:
        for family in fold["held_family_ids"]:
            fold_for_family[family] = fold["fold_id"]
    for row in rows:
        candidate = row.get("candidate_id")
        family = row.get("family_id")
        origin = int(row.get("origin_issue"))
        horizon = int(row.get("horizon_ms"))
        if candidate not in CANDIDATES or family not in truth:
            failures.append("ROW_IDENTITY")
            continue
        if row.get("fold_id") != fold_for_family[family] or horizon not in FIT_HORIZONS or not 16 <= origin <= 57:
            failures.append(f"ROW_CLOCK_OR_FOLD:{candidate}:{family}:{origin}:{horizon}")
            continue
        source = truth[family]
        expected_truth = source["states"][origin + horizon]
        expected_origin = source["states"][origin]
        expected_previous = source["states"][origin] - source["states"][origin - 1]
        expected_terminal = source["states"][origin + horizon] - source["states"][origin + horizon - 1]
        for label, actual, expected in (
            ("truth", row["truth_state"], expected_truth),
            ("origin", row["origin_state"], expected_origin),
            ("previous", row["previous_increment"], expected_previous),
            ("terminal", row["truth_terminal_increment"], expected_terminal),
        ):
            if not np.array_equal(np.asarray(actual), expected):
                failures.append(f"ROW_{label.upper()}:{candidate}:{family}:{origin}:{horizon}")
        maximum_slew, maximum_excursion = _recursive_action_diagnostics(row, source, source_active)
        if not math.isclose(maximum_slew, float(row["candidate_maximum_slew_a"]), abs_tol=1.0e-12):
            failures.append("ROW_SLEW")
        if not math.isclose(maximum_excursion, float(row["candidate_maximum_current_excursion_from_source_a"]), abs_tol=1.0e-12):
            failures.append("ROW_CURRENT_EXCURSION")
        if bool(row["supported"]) != (float(row["support_distance"]) <= float(row["support_threshold"]) + 1.0e-12):
            failures.append("ROW_SUPPORT_BOOLEAN")

    result_candidates = result["comparison"]["candidate_results"]
    candidate_map = {candidate["candidate_id"]: candidate for candidate in result_candidates}
    recomputed_eligibility: dict[str, bool] = {}
    for candidate_id in CANDIDATES:
        candidate = candidate_map[candidate_id]
        for fold in candidate["folds"]:
            block = [row for row in rows if row["candidate_id"] == candidate_id and row["fold_id"] == fold["fold_id"]]
            metrics = _summarize(block, source_state, stage)
            _numeric_equal(metrics, fold["metrics"], f"{candidate_id}.{fold['fold_id']}.metrics", failures)
            reasons = _failures(metrics, fold, stage)
            if reasons != fold["failures"] or bool(not reasons) != bool(fold["eligible"]):
                failures.append(f"FOLD_ROUTE:{candidate_id}:{fold['fold_id']}")
        recomputed_eligibility[candidate_id] = all(bool(fold["eligible"]) for fold in candidate["folds"])
        if recomputed_eligibility[candidate_id] != bool(candidate["eligible"]):
            failures.append(f"CANDIDATE_ELIGIBILITY:{candidate_id}")

    structured = candidate_map[CANDIDATES[0]]
    tcn = candidate_map[CANDIDATES[1]]
    improvement = 1.0 - tcn["summary"]["worst_pair_response_nrmse"] / max(structured["summary"]["worst_pair_response_nrmse"], 1.0e-30)
    regression_values = []
    for fold_a, fold_b in zip(structured["folds"], tcn["folds"]):
        for horizon in QUALIFICATION_HORIZONS:
            for a, b in zip(
                fold_a["metrics"]["endpoint_p95_abs_by_horizon"][str(horizon)],
                fold_b["metrics"]["endpoint_p95_abs_by_horizon"][str(horizon)],
            ):
                regression_values.append(float(b) / max(float(a), 1.0e-30) - 1.0)
        for metric in ("terminal_increment_p95_abs", "cross_horizon_consistency_p95_abs"):
            for a, b in zip(fold_a["metrics"][metric], fold_b["metrics"][metric]):
                regression_values.append(float(b) / max(float(a), 1.0e-30) - 1.0)
    maximum_regression = max(regression_values)
    relative = (
        improvement >= stage["selection"]["minimum_tcn_worst_pair_response_improvement_fraction"]
        and maximum_regression <= stage["selection"]["maximum_tcn_componentwise_critical_metric_regression_fraction"]
    )
    expected_selected = CANDIDATES[0] if recomputed_eligibility[CANDIDATES[0]] else None
    if recomputed_eligibility[CANDIDATES[1]] and relative:
        expected_selected = CANDIDATES[1]
    if result["comparison"]["selected_candidate_id"] != expected_selected:
        failures.append("SELECTION")
    expected_passed = expected_selected is not None
    expected_route = stage["routes"]["pass" if expected_passed else "no_eligible_candidate"]
    if bool(result["passed"]) != expected_passed or result["route"] != expected_route:
        failures.append("RESULT_ROUTE")
    selected_path = output / "selected_model.json"
    if selected_path.exists() != expected_passed:
        failures.append("MODEL_FILE_PRESENCE")

    return {
        "schema_version": "rgeo-zgeo-1ms-id2z19r1-independent-ledger-audit-v1",
        "audit_passed": not failures,
        "failures": failures[:200],
        "failure_count": len(failures),
        "stage_config_sha256": _sha(CONFIG),
        "result_sha256": _sha(output / "result.json"),
        "oof_predictions_sha256": _sha(output / "oof_predictions.json"),
        "oof_prediction_row_count": len(rows),
        "recomputed_selected_candidate_id": expected_selected,
        "recomputed_passed": expected_passed,
        "new_tsc_calls": 0,
        "calibration_records_read": 0,
        "blind_holdout_records_read": 0,
        "claim_boundary": stage["claim_boundary"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = audit(args.output)
        target = _inside(args.output) / "independent_audit.json"
        if target.exists():
            raise AuditError(f"refuse overwrite: {target}")
        target.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["audit_passed"] else 2
    except (AuditError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({
            "audit_passed": False,
            "route": "ONE_MS_ID2Z19R1_INDEPENDENT_AUDIT_EXECUTION_FAIL",
            "error": str(exc),
            "new_tsc_calls": 0,
        }, indent=2, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
