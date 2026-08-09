#!/usr/bin/env python3
"""Independent bank/model/innovation/planning audit for R8R46."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r31_independent_forensics as ind31,
)
from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r32_independent_forensics as ind32,
)
from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r43_independent_forensics as ind43,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r31_aligned_explicit_four_coordinate_feedback_sentinel
    as r8r31,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r43_fixed_affine_dominant_global_ridge_local_affine_cold_ensemble_preflight
    as source_r8r43,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r46_q0_calibration_causal_innovation_controller_preflight
    as r8r46,
)


STAGE = r8r46.STAGE
IDENTITY = r8r46.IDENTITY
AUDIT_KIND = "q0_calibration_causal_innovation_controller_preflight_independent"
FACTORS = np.asarray(r8r31.OUTPUT_FACTORS, dtype=np.float64)

_read = ind32._read
_write = ind32._write
_sha = ind32._sha
_digest = ind32._digest
_maximum_difference = ind32._maximum_difference


def _without_digests(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: _without_digests(item)
            for key, item in value.items()
            if "digest" not in key.lower() and "sha256" not in key.lower()
        }
    if isinstance(value, list):
        return [_without_digests(item) for item in value]
    return value


def _planning_selection(planning: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "pair_id": str(row["pair_id"]),
            "history_member": str(row["history_member"]),
            "beam_counts": list(row["beam_counts"]),
            "counters": row["counters"],
            "safe_search_complete": bool(row["safe_search_complete"]),
            "selected_plan": row.get("selected_plan"),
            "robust_formal_plan_found": bool(row["robust_formal_plan_found"]),
            "causal_mode": str(row["causal_mode"]),
            "selected_first_transport_action_index": int(
                row["selected_first_transport_action_index"]
            ),
            "selected_first_transport_action_mode": str(
                row["selected_first_transport_action_mode"]
            ),
        }
        for row in planning["plans"]
    ]


def _prediction_map(
    model: Mapping[str, Any], family: str, held_key: str, field: str
) -> dict[tuple[str, str], np.ndarray]:
    return {
        (str(fold[held_key]), str(trajectory["trajectory_id"])): np.concatenate(
            [np.asarray(row, dtype=np.float64).reshape((-1, 5)) for row in trajectory[field]]
        )
        for fold in model[family]
        for trajectory in fold["trajectories"]
    }


def _scaled_innovation_difference(
    primary: Mapping[str, Any], independent: Mapping[str, Any], cfg: Mapping[str, Any]
) -> float:
    scales = np.asarray(
        cfg["model_contract"]["primary_independent_component_scales"], dtype=np.float64
    )
    maximum = 0.0
    for family, held_key in (
        ("outer_predictions", "held_pair"),
        ("schedule_predictions", "held_schedule"),
    ):
        for field in ("cold_predictions", "adapted_predictions"):
            left = _prediction_map(primary, family, held_key, field)
            right = _prediction_map(independent, family, held_key, field)
            if set(left) != set(right):
                return math.inf
            for key in left:
                if left[key].shape != right[key].shape:
                    return math.inf
                maximum = max(
                    maximum,
                    float(np.max(np.abs(left[key] - right[key]) * FACTORS / scales)),
                )
        left_updates = {
            (str(fold[held_key]), str(row["trajectory_id"])): row["updates"]
            for fold in primary[family]
            for row in fold["trajectories"]
        }
        right_updates = {
            (str(fold[held_key]), str(row["trajectory_id"])): row["updates"]
            for fold in independent[family]
            for row in fold["trajectories"]
        }
        if set(left_updates) != set(right_updates):
            return math.inf
        for key in left_updates:
            if len(left_updates[key]) != len(right_updates[key]):
                return math.inf
            for left, right in zip(left_updates[key], right_updates[key]):
                if (
                    int(left["interval"]) != int(right["interval"])
                    or int(left["clipped_components"]) != int(right["clipped_components"])
                ):
                    return math.inf
                for field in ("innovation", "cap", "proposed_bias", "next_bias"):
                    a = np.asarray(left[field], dtype=np.float64)
                    b = np.asarray(right[field], dtype=np.float64)
                    maximum = max(
                        maximum, float(np.max(np.abs(a - b) * FACTORS / scales))
                    )
    return maximum


def _scaled_tube_difference(
    primary: Mapping[str, Any],
    independent: Mapping[str, Any],
    primary_execution: Sequence[Any],
    independent_execution: Sequence[Any],
    cfg: Mapping[str, Any],
) -> float:
    scales = np.asarray(
        cfg["model_contract"]["primary_independent_component_scales"], dtype=np.float64
    )
    maximum = 0.0
    families = [
        (primary[field], independent[field])
        for field in ("pair_tube", "schedule_tube", "combined_tube")
    ]
    families.append((primary_execution, independent_execution))
    for left_rows, right_rows in families:
        if len(left_rows) != len(right_rows):
            return math.inf
        for left, right in zip(left_rows, right_rows):
            a = np.asarray(left, dtype=np.float64)
            b = np.asarray(right, dtype=np.float64)
            if a.shape != b.shape:
                return math.inf
            maximum = max(
                maximum, float(np.max(np.abs(a - b) * FACTORS / scales))
            )
    return maximum


def audit(args: argparse.Namespace) -> dict[str, Any]:
    ctx = r8r46.load_context(args)
    if ctx.cfg.get("stage") != STAGE or ctx.cfg.get("identity") != IDENTITY:
        raise ValueError("independent R8R46 configuration identity changed")
    stage = ctx.paths.stage
    summary_path = stage / "analysis/primary_summary.json"
    detailed_path = stage / "analysis/primary_detailed.json"
    model_path = stage / "model/preflight_model.json"
    primary_summary = _read(summary_path)
    primary_detailed = _read(detailed_path)
    primary_model = _read(model_path)

    r44_authentication = ind43._authenticate_final(
        ctx.r8r44_stage, ctx.cfg["source_r8r44"], "R8R44"
    )
    independent_transitive = ind31._authenticate(args, ctx.source_ctx.cfg)
    trajectories = ind31._build_bank(args, ctx.source_ctx.cfg)
    bank = ind31._bank_evidence(trajectories)
    r8r46._verify_bank(bank, ctx.cfg)
    _unused, context_meta = r8r31.r8r23.build_bank(ctx.source_ctx.r8r23_ctx)
    if set(context_meta) != {
        (str(row["pair_id"]), str(row["history_member"])) for row in trajectories
    }:
        raise ValueError("independent R8R46 planning metadata coverage changed")

    model_ctx = SimpleNamespace(cfg=ctx.r8r43_ctx.cfg, source_ctx=ctx.source_ctx)
    production_transitive = source_r8r43.authenticate_sources(ctx.r8r43_ctx)
    independent_cold_detailed, independent_cold_model = ind43._compute(
        model_ctx, production_transitive, trajectories, bank
    )
    source_detailed = _read(ctx.r8r43_ctx.paths.stage / "analysis/primary_detailed.json")
    source_model = _read(ctx.r8r43_ctx.paths.stage / "model/preflight_model.json")
    binding = {
        "recomputed_primary_detailed_digest": _digest(independent_cold_detailed),
        "source_primary_detailed_digest": _digest(source_detailed),
        "recomputed_model_digest": _digest(independent_cold_model),
        "source_model_digest": _digest(source_model),
        "primary_detailed_exact": independent_cold_detailed == source_detailed,
        "model_artifact_exact": independent_cold_model == source_model,
    }
    binding["passed"] = bool(
        binding["primary_detailed_exact"] and binding["model_artifact_exact"]
    )

    outer_folds, _outer_metrics, outer_predictions = ind43._outer(
        trajectories, ctx.r8r43_ctx.cfg, ctx.source_ctx.cfg
    )
    _schedule_tube, schedule_folds, _schedule_metrics, schedule_predictions = ind43._schedule(
        trajectories, ctx.r8r43_ctx.cfg
    )
    model_evaluation, adapted_model, _adapted_folds = r8r46.postcalibration_from_cold_folds(
        ctx,
        trajectories,
        outer_folds,
        outer_predictions,
        schedule_folds,
        schedule_predictions,
    )
    cold_tube = [
        np.asarray(row, dtype=np.float64)
        for row in independent_cold_model["combined_tube"]
    ]
    adapted_tube = [
        np.asarray(row, dtype=np.float64) for row in adapted_model["combined_tube"]
    ]
    execution_tube = [cold_tube[0]] + [
        np.maximum(cold_tube[index], adapted_tube[index])
        if index == 1
        else adapted_tube[index]
        for index in r8r46.POST_INTERVALS
    ]
    if bool(binding["passed"] and model_evaluation["model_gate_passed"]):
        planning, faults, support, hulls = r8r46.evaluate_planning(
            ctx,
            trajectories,
            context_meta,
            execution_tube,
            cold_tube,
            fit_model_fn=ind43._fit_model,
            predict_fn=lambda model, row, cfg: ind43._predict(model, row, cfg)[2],
        )
    else:
        planning, faults, support, hulls = r8r46.skipped_planning()
    authentication = {
        "r8r44_final": r44_authentication,
        "independent_transitive": independent_transitive,
        "passed": True,
    }
    independent_detailed = r8r46.assemble_result(
        ctx, authentication, bank, binding, model_evaluation, planning, faults
    )
    independent_model = {
        "schema_version": r8r46.SCHEMA_VERSION,
        "stage": STAGE,
        "identity": IDENTITY,
        "model_kind": "q0_calibration_fixed_ewma_causal_innovation_cold_ensemble_controller_preflight",
        "cold_base_model": independent_cold_model,
        "postcalibration_model": adapted_model,
        "combined_execution_tube": execution_tube,
        "planning_model_evidence": ind43._model_evidence(
            ind43._fit_model(
                trajectories, lambda _row: True, ctx.r8r43_ctx.cfg
            )
        ),
        "support": support,
        "transition_hulls": hulls,
        "planning_evaluation": planning,
        "cold_source_evaluation_digest": _digest(independent_cold_detailed),
    }

    tolerance = float(
        ctx.cfg["model_contract"]["primary_independent_scaled_tolerance"]
    )
    bank_difference = _maximum_difference(
        primary_detailed["bank_evidence"], independent_detailed["bank_evidence"]
    )
    cold_model_difference = ind43._scaled_model_difference(
        primary_model["cold_base_model"], independent_model["cold_base_model"]
    )
    cold_prediction_difference = ind43._scaled_prediction_difference(
        primary_model["cold_base_model"],
        independent_model["cold_base_model"],
        ctx.r8r43_ctx.cfg,
    )
    planning_model_difference = _maximum_difference(
        _without_digests(primary_model["planning_model_evidence"]),
        _without_digests(independent_model["planning_model_evidence"]),
    )
    model_difference = max(
        cold_model_difference, cold_prediction_difference, planning_model_difference
    )
    innovation_difference = _scaled_innovation_difference(
        primary_model["postcalibration_model"],
        independent_model["postcalibration_model"],
        ctx.cfg,
    )
    tube_difference = _scaled_tube_difference(
        primary_model["postcalibration_model"],
        independent_model["postcalibration_model"],
        primary_model["combined_execution_tube"],
        independent_model["combined_execution_tube"],
        ctx.cfg,
    )
    metric_difference = _maximum_difference(
        _without_digests(primary_detailed["postcalibration_model_evaluation"]),
        _without_digests(independent_detailed["postcalibration_model_evaluation"]),
    )
    planning_difference = _maximum_difference(
        _without_digests(primary_detailed["planning_evaluation"]),
        _without_digests(independent_detailed["planning_evaluation"]),
    )
    selection_agreement = bool(
        _planning_selection(primary_detailed["planning_evaluation"])
        == _planning_selection(independent_detailed["planning_evaluation"])
    )
    source_agreement = bool(
        r44_authentication["passed"]
        and independent_transitive["passed"]
        and primary_detailed["cold_source_binding"]["passed"]
        and independent_detailed["cold_source_binding"]["passed"]
        and primary_detailed["cold_source_binding"]["source_model_digest"]
        == independent_detailed["cold_source_binding"]["source_model_digest"]
    )
    route_agreement = bool(
        primary_detailed["route"] == independent_detailed["route"]
        and primary_summary["route"] == independent_detailed["route"]
    )
    outcome_agreement = bool(
        primary_detailed["integrity_gate_passed"] is True
        and independent_detailed["integrity_gate_passed"] is True
        and primary_detailed["scientific_gate_passed"]
        is independent_detailed["scientific_gate_passed"]
        and primary_summary["scientific_gate_passed"]
        is independent_detailed["scientific_gate_passed"]
        and primary_detailed["safety_gate_passed"]
        is independent_detailed["safety_gate_passed"]
        and primary_detailed["authority_gate_passed"]
        is independent_detailed["authority_gate_passed"]
    )
    result = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "audit_kind": AUDIT_KIND,
        "source_authentication": authentication,
        "bank_evidence": bank,
        "independent_model_artifact_sha256": _digest(independent_model),
        "maximum_bank_absolute_difference": bank_difference,
        "maximum_scaled_model_difference": model_difference,
        "maximum_scaled_innovation_difference": innovation_difference,
        "maximum_scaled_tube_difference": tube_difference,
        "maximum_scaled_metric_difference": metric_difference,
        "maximum_scaled_planning_difference": planning_difference,
        "primary_source_agreement": source_agreement,
        "primary_bank_agreement": bank_difference == 0.0,
        "primary_model_agreement": model_difference <= tolerance,
        "primary_innovation_agreement": innovation_difference <= tolerance,
        "primary_tube_agreement": tube_difference <= tolerance,
        "primary_metric_agreement": metric_difference <= tolerance,
        "primary_planning_agreement": planning_difference <= tolerance,
        "primary_discrete_selection_agreement": selection_agreement,
        "primary_route_agreement": route_agreement,
        "primary_outcome_agreement": outcome_agreement,
        "route": independent_detailed["route"],
        "scientific_gate_passed": bool(independent_detailed["scientific_gate_passed"]),
        "primary_summary_sha256": _sha(summary_path),
        "primary_detailed_sha256": _sha(detailed_path),
        "primary_model_sha256": _sha(model_path),
        "real_tsc_executed": False,
        "plant_step_count": 0,
        "new_raw_count": 0,
    }
    result["passed"] = bool(
        all(result[field] is True for field in r8r46.AGREEMENT_FIELDS)
        and all(
            float(result[field]) <= tolerance for field in r8r46.DIFFERENCE_FIELDS
        )
    )
    output = stage / "analysis/independent.json"
    if not result["passed"]:
        output = stage / "analysis/independent_failure.json"
    _write(output, result)
    if not result["passed"]:
        raise ValueError("independent R8R46 preflight disagrees with primary")
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in r8r46.ARGUMENT_NAMES:
        parser.add_argument(
            f"--{name}", dest=name.replace("-", "_"), type=Path, required=True
        )
    return parser


def main() -> None:
    args = _parser().parse_args()
    result = audit(args)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
