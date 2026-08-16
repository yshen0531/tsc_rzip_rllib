#!/usr/bin/env python3
"""Read-only ID-2C0 method attribution and control-relevance audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_id2b1_structured_model_development import (  # noqa: E402
    feature_vector,
    load_config as load_id2b1_config,
    load_rows,
)


SCHEMA = "rgeo-zgeo-1ms-id2c0-control-relevance-audit-result-v1"
CONFIG_SHA256 = "e4cc745ccc8b013f5021d43b90ef2af1540cb11bcb7161113f92c34a7ec23123"
INPUT_FAIL = "ONE_MS_ID2C0_INPUT_OR_EVIDENCE_INTEGRITY_FAIL_STOP"
INCOMPLETE = "ONE_MS_ID2C0_METHOD_OR_CONTROL_RELEVANCE_AUDIT_INCOMPLETE_STOP"
PASS = "ONE_MS_ID2C0_CONTROL_RELEVANCE_AUDIT_COMPLETE_ID2C1_DESIGN_REQUIRED"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inside(root: Path, path: Path, label: str) -> Path:
    root = root.resolve()
    resolved = path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} leaves repository root") from exc
    return resolved


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def load_stage(repo_root: Path, config_path: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    path = inside(repo_root, config_path, "ID2C0 config")
    if sha256_file(path) != CONFIG_SHA256:
        raise ValueError("ID2C0 config hash mismatch")
    config = read_json(path)
    if config.get("schema_version") != "rgeo-zgeo-1ms-id2c0-control-relevance-audit-v1":
        raise ValueError("ID2C0 schema mismatch")
    if config.get("stage_id") != "rgeo_zgeo_1ms_id2c0_control_relevance_audit_v1":
        raise ValueError("ID2C0 stage identity mismatch")
    if any(
        config.get(key) != 0
        for key in (
            "plant_advances",
            "tsc_calls",
            "models_fit_or_trained",
            "calibration_records_read",
            "holdout_records_read",
        )
    ):
        raise ValueError("ID2C0 zero-execution/data counters changed")
    if config.get("routes") != {
        "input_fail": INPUT_FAIL,
        "method_fail": INCOMPLETE,
        "pass": PASS,
    }:
        raise ValueError("ID2C0 route contract mismatch")
    required = config.get("required_findings", [])
    if not isinstance(required, list) or len(required) < 5:
        raise ValueError("ID2C0 required findings are incomplete")
    bound: dict[str, dict[str, Any]] = {}
    for item in config.get("bound_inputs", []):
        relative = str(item["path"])
        source = inside(repo_root, repo_root / relative, f"bound input {relative}")
        observed = sha256_file(source)
        if observed != item["sha256"]:
            raise ValueError(f"bound input hash mismatch: {relative}")
        bound[relative] = {"sha256": observed, "bytes": source.stat().st_size, "json": read_json(source)}
    if len(bound) != 14:
        raise ValueError("ID2C0 bound input count mismatch")
    return config, bound


def _rows_by_key(rows: list[dict[str, Any]]) -> dict[tuple[str, str, str, int], dict[str, Any]]:
    result: dict[tuple[str, str, str, int], dict[str, Any]] = {}
    for row in rows:
        key = (str(row["context_id"]), str(row["direction_id"]), str(row["sign"]), int(row["duration_issues"]))
        if key in result:
            raise ValueError(f"duplicate unique row: {key}")
        result[key] = row
    return result


def _baselines(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    values: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row["direction_id"] == "baseline":
            values[str(row["context_id"])] = row
    if sorted(values) != ["anchor_p03_minus", "history_p04_plus", "late_q0"]:
        raise ValueError("baseline context set mismatch")
    return values


def feature_cancellation(
    rows: list[dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, Any]:
    by_key = _rows_by_key(rows)
    baselines = _baselines(rows)
    contexts = sorted(baselines)
    arms = sorted({key[1:] for key in by_key if key[1] != "baseline"})
    output: dict[str, Any] = {}
    for model_id in ("stable_exp_signed", "stable_exp_signed_even"):
        maximum = 0.0
        comparisons = 0
        feature_lengths: set[int] = set()
        for arm in arms:
            differences = []
            for context in contexts:
                action = by_key[(context, *arm)]
                baseline = baselines[context]
                per_horizon = []
                for horizon in range(1, 23):
                    delta = feature_vector(action, 10, horizon, model_id, config) - feature_vector(
                        baseline, 10, horizon, model_id, config
                    )
                    feature_lengths.add(int(delta.size))
                    per_horizon.append(delta)
                differences.append(np.concatenate(per_horizon))
            reference = differences[0]
            for candidate in differences[1:]:
                maximum = max(maximum, float(np.max(np.abs(candidate - reference))))
                comparisons += 1
        output[model_id] = {
            "arms": len(arms),
            "context_pair_comparisons": comparisons,
            "feature_lengths": sorted(feature_lengths),
            "maximum_cross_context_matched_baseline_feature_difference": maximum,
            "context_invariant_at_1e_12": maximum <= 1e-12,
        }
    contextual_lengths = {
        len(feature_vector(row, 10, 1, "stable_exp_contextual", config))
        for row in rows
        if row["direction_id"] != "baseline"
    }
    output["stable_exp_contextual"] = {
        "feature_lengths": sorted(contextual_lengths),
        "independent_training_contexts_per_loco_fold": 2,
        "unique_training_trajectory_cells_per_fold": 26,
        "claim": "contextual but under-supported; failure is not a theorem against compact LPV/hybrid models",
    }
    return output


def _critical_fold_metrics(id2b1: dict[str, Any]) -> dict[str, Any]:
    folds = id2b1["evaluation"]["candidate_metrics"]["stable_exp_signed"]
    selected = []
    all_signal = []
    for fold in folds:
        for arm in fold["arm_metrics"]:
            if arm["signal_eligible"]:
                all_signal.append(
                    {
                        "test_context": fold["test_context"],
                        "rollout_id": arm["rollout_id"],
                        "peak_direction_cosine": arm["peak_direction_cosine"],
                        "response_scaled_rmse": arm["response_scaled_rmse"],
                    }
                )
            if arm["rollout_id"].endswith("p09_half_exact_center_minus_d1_r0"):
                selected.append(
                    {
                        "test_context": fold["test_context"],
                        "peak_direction_cosine": arm["peak_direction_cosine"],
                        "peak_response_mm": arm["peak_response_mm"],
                        "response_scaled_rmse": arm["response_scaled_rmse"],
                    }
                )
    return {
        "p09_minus_d1_by_loco_fold": selected,
        "minimum_signal_arm_peak_direction_cosine": min(value["peak_direction_cosine"] for value in all_signal),
        "signal_arm_count": len(all_signal),
        "aggregate_fraction_is_not_a_pointwise_gate": True,
    }


def _control_relevance(bound: dict[str, dict[str, Any]]) -> dict[str, Any]:
    b0 = next(value["json"] for key, value in bound.items() if "id2b0_readiness" in key and key.endswith("result.json"))
    c1a = next(value["json"] for key, value in bound.items() if "nr2r2c1a_result" in key)
    c2a = next(value["json"] for key, value in bound.items() if "c2a_search_result" in key)
    a3 = next(value["json"] for key, value in bound.items() if "c2aa3_result" in key)
    id1b = next(value["json"] for key, value in bound.items() if "id1b_result" in key)
    q0 = b0["analysis"]["nominal_state10_to_state32"]
    maximum_nominal_pair_rz_mm = 0.0
    keys = sorted(q0)
    for left_index, left in enumerate(keys):
        for right in keys[left_index + 1 :]:
            maximum_nominal_pair_rz_mm = max(
                maximum_nominal_pair_rz_mm,
                math.hypot(
                    q0[left]["state10_to_state32_r_mm"] - q0[right]["state10_to_state32_r_mm"],
                    q0[left]["state10_to_state32_z_mm"] - q0[right]["state10_to_state32_z_mm"],
                ),
            )
    q0_compact = next(value["json"] for key, value in bound.items() if key.endswith("q0_h32_r0.json"))
    a3_compact = next(
        value["json"] for key, value in bound.items() if key.endswith("p03_cumulative_level2_r0.json")
    )
    q0_state0 = np.asarray(
        [q0_compact["states"][0][key] for key in ("r_geo_m", "z_geo_m")], dtype=float
    )
    q0_state16 = np.asarray(
        [q0_compact["states"][16][key] for key in ("r_geo_m", "z_geo_m")], dtype=float
    )
    level2_state16 = np.asarray(
        [a3_compact["states"][16][key] for key in ("r_geo_m", "z_geo_m")], dtype=float
    )
    q0_vector = q0_state16 - q0_state0
    response = level2_state16 - q0_state16
    ratio = float(np.linalg.norm(response) / np.linalg.norm(q0_vector))
    return {
        "id2a_counts": b0["analysis"]["counts"],
        "context_pairs": b0["analysis"]["context_pairs"],
        "exact_causal_collision_count": len(b0["analysis"]["exact_causal_collisions"]),
        "p09_minus_d4_peak_rz_mm": b0["analysis"]["critical_p09_minus_d4_peak_rz_mm"],
        "p09_peak_ratio": b0["analysis"]["critical_peak_maximum_to_minimum_ratio"],
        "nominal_state10_to_state32": q0,
        "maximum_nominal_pair_rz_difference_mm": maximum_nominal_pair_rz_mm,
        "q0_32ms_control_claim": c1a["claim_boundary"],
        "constant_dwell_candidates": c2a["candidate_metrics"],
        "constant_dwell_hold_candidate_found": c2a["passed"],
        "p03_level2_state16_response_to_q0_drift_norm_fraction": ratio,
        "p03_level2_state16_response_minus_q0_m": response.tolist(),
        "q0_source_to_state16_rz_m": q0_vector.tolist(),
        "id1b_positive_span_passed": id1b["scientific_metrics"]["positive_span_passed"],
        "active_nominal_and_two_axis_residual_authority_are_missing": (
            c2a["passed"] is False and ratio < 0.10 and id1b["scientific_metrics"]["positive_span_passed"] is False
        ),
    }


def audit(repo_root: Path, config_path: Path, id2a_run_dir: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    try:
        stage, bound = load_stage(repo_root, config_path)
        id2b1_path = repo_root / "configs/rgeo_zgeo_1ms_id2b1_structured_model_development.json"
        id2b1_config = load_id2b1_config(repo_root, id2b1_path)
        _, rows, source_identity = load_rows(repo_root, id2b1_config, id2a_run_dir)
        cancellation = feature_cancellation(rows, id2b1_config)
        id2b1 = next(value["json"] for key, value in bound.items() if "id2b1_model" in key and key.endswith("result.json"))
        critical = _critical_fold_metrics(id2b1)
        relevance = _control_relevance(bound)
        method_complete = (
            len(rows) == 39
            and cancellation["stable_exp_signed"]["context_invariant_at_1e_12"]
            and cancellation["stable_exp_signed_even"]["context_invariant_at_1e_12"]
            and relevance["exact_causal_collision_count"] == 0
            and relevance["active_nominal_and_two_axis_residual_authority_are_missing"]
            and len(critical["p09_minus_d1_by_loco_fold"]) == 3
        )
        if not method_complete:
            failures.append("REQUIRED_ATTRIBUTION_OR_CONTROL_RELEVANCE_FINDING_MISSING")
        route = PASS if not failures else INCOMPLETE
        result = {
            "schema_version": SCHEMA,
            "source_revision": source_revision,
            "config_sha256": CONFIG_SHA256,
            "passed": not failures,
            "route": route,
            "failures": failures,
            "counters": {
                "plant_advances": 0,
                "tsc_calls": 0,
                "models_fit_or_trained": 0,
                "calibration_records_read": 0,
                "holdout_records_read": 0,
                "unique_development_trajectory_cells_read": len(rows),
            },
            "source_identity": source_identity,
            "bound_input_sha256": {key: value["sha256"] for key, value in sorted(bound.items())},
            "method_attribution": {
                "feature_cancellation": cancellation,
                "critical_event_metrics": critical,
                "factor8_is_pure_history_result": False,
                "nominal_action_separation_required": True,
                "id2b1_total_delta_regression_did_not_supply_a_separate_time_indexed_nominal": True,
            },
            "control_relevance": relevance,
            "next_stage_contract": stage["prospective_id2c1_design_constraints"],
            "claim_boundary": (
                "Read-only development evidence audit. PASS permits only a separately frozen ID2C1 design; "
                "it is not a model, tube, controller, recovery, MPC or TSC result."
            ),
        }
        return result
    except Exception as exc:
        return {
            "schema_version": SCHEMA,
            "source_revision": source_revision,
            "config_sha256": CONFIG_SHA256,
            "passed": False,
            "route": INPUT_FAIL,
            "failures": [f"{type(exc).__name__}:{exc}"],
            "counters": {
                "plant_advances": 0,
                "tsc_calls": 0,
                "models_fit_or_trained": 0,
                "calibration_records_read": 0,
                "holdout_records_read": 0,
            },
        }


def write_new(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite: {path}")
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--id2a-run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    result = audit(ROOT, args.config, args.id2a_run_dir, args.source_revision)
    write_new(inside(ROOT, args.output, "ID2C0 output"), result)
    print(json.dumps({"passed": result["passed"], "route": result["route"]}, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
