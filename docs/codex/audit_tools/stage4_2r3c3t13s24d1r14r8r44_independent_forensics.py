#!/usr/bin/env python3
"""Independent bank/model/planning audit for the R8R44 zero-TSC preflight."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping

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
    stage4_2r3c3t13s24d1r14r8r44_fixed_affine_dominant_global_local_affine_cold_ensemble_receding_controller_preflight
    as r8r44,
)


STAGE = r8r44.STAGE
IDENTITY = r8r44.IDENTITY
AUDIT_KIND = "fixed_affine_dominant_cold_ensemble_receding_controller_preflight_independent"

_read = ind32._read
_write = ind32._write
_sha = ind32._sha
_digest = ind32._digest
_maximum_difference = ind32._maximum_difference
_without_digests = ind32._without_digests


def _planning_selection(rows: Mapping[str, Any]) -> list[dict[str, Any]]:
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
            "selected_first_action_index": int(row["selected_first_action_index"]),
            "selected_first_action_mode": str(row["selected_first_action_mode"]),
        }
        for row in rows["plans"]
    ]


def _metric_view(detailed: Mapping[str, Any]) -> dict[str, Any]:
    model = detailed["source_model_evaluation"]
    return {
        "outer_model_evaluation": model["outer_model_evaluation"],
        "schedule_jackknife": model["schedule_jackknife"],
        "combined_tube_maximum_physical_half_width": model[
            "combined_tube_maximum_physical_half_width"
        ],
    }


def audit(args: argparse.Namespace) -> dict[str, Any]:
    ctx = r8r44.load_context(args)
    if ctx.cfg.get("stage") != STAGE or ctx.cfg.get("identity") != IDENTITY:
        raise ValueError("independent R8R44 configuration identity changed")
    stage = ctx.paths.stage
    summary_path = stage / "analysis/primary_summary.json"
    detailed_path = stage / "analysis/primary_detailed.json"
    model_path = stage / "model/preflight_model.json"
    primary_summary = _read(summary_path)
    primary_detailed = _read(detailed_path)
    primary_model = _read(model_path)

    source_authentication = ind43._authenticate_final(
        ctx.r8r43_stage, ctx.cfg["source_r8r43"], "R8R43"
    )
    independent_transitive = ind31._authenticate(args, ctx.source_ctx.cfg)
    trajectories = ind31._build_bank(args, ctx.source_ctx.cfg)
    bank = ind31._bank_evidence(trajectories)
    _ignored, context_meta = r8r31.r8r23.build_bank(ctx.source_ctx.r8r23_ctx)
    if set(context_meta) != {
        (str(row["pair_id"]), str(row["history_member"])) for row in trajectories
    }:
        raise ValueError("independent R8R44 planning metadata coverage changed")

    model_ctx = SimpleNamespace(cfg=ctx.r8r43_ctx.cfg, source_ctx=ctx.source_ctx)
    production_transitive = source_r8r43.authenticate_sources(ctx.r8r43_ctx)
    independent_base_detailed, independent_base_model = ind43._compute(
        model_ctx, production_transitive, trajectories, bank
    )
    source_detailed = _read(ctx.r8r43_stage / "analysis/primary_detailed.json")
    source_model = _read(ctx.r8r43_stage / "model/preflight_model.json")
    model_binding = {
        "recomputed_primary_detailed_digest": _digest(independent_base_detailed),
        "source_primary_detailed_digest": _digest(source_detailed),
        "recomputed_model_digest": _digest(independent_base_model),
        "source_model_digest": _digest(source_model),
        "primary_detailed_exact": independent_base_detailed == source_detailed,
        "model_artifact_exact": independent_base_model == source_model,
    }
    model_binding["passed"] = bool(
        model_binding["primary_detailed_exact"] and model_binding["model_artifact_exact"]
    )

    combined_tube = [
        np.asarray(row, dtype=np.float64)
        for row in independent_base_model["combined_tube"]
    ]
    planning, faults, support, hulls = r8r44.evaluate_planning(
        ctx,
        trajectories,
        context_meta,
        combined_tube,
        fit_model_fn=ind43._fit_model,
        predict_ensemble_fn=lambda model, row, cfg: ind43._predict(model, row, cfg)[2],
    )
    authentication = {
        "r8r43_final": source_authentication,
        "independent_transitive": independent_transitive,
        "passed": True,
    }
    independent_detailed = r8r44.assemble_result(
        ctx,
        authentication,
        bank,
        independent_base_detailed,
        planning,
        faults,
        model_binding,
    )
    independent_model = {
        "schema_version": r8r44.SCHEMA_VERSION,
        "stage": STAGE,
        "identity": IDENTITY,
        "model_kind": "fixed_affine_dominant_cold_ensemble_receding_controller_preflight",
        "base_model": independent_base_model,
        "planning_model_evidence": ind43._model_evidence(
            ind43._fit_model(trajectories, lambda _row: True, ctx.r8r43_ctx.cfg)
        ),
        "combined_tube": independent_base_model["combined_tube"],
        "support": support,
        "transition_hulls": hulls,
        "planning_evaluation": planning,
    }

    tolerance = float(
        ctx.cfg["model_contract"]["primary_independent_scaled_tolerance"]
    )
    bank_difference = _maximum_difference(
        primary_detailed["bank_evidence"], independent_detailed["bank_evidence"]
    )
    model_difference = ind43._scaled_model_difference(
        primary_model["base_model"], independent_model["base_model"]
    )
    prediction_difference = ind43._scaled_prediction_difference(
        primary_model["base_model"], independent_model["base_model"], ctx.r8r43_ctx.cfg
    )
    tube_difference = ind43._scaled_tube_difference(
        primary_model["base_model"], independent_model["base_model"], ctx.r8r43_ctx.cfg
    )
    metric_difference = ind43._scaled_metric_difference(
        _metric_view(primary_detailed), _metric_view(independent_detailed), ctx.r8r43_ctx.cfg
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
        source_authentication["passed"]
        and independent_transitive["passed"]
        and primary_detailed["source_model_binding"]["passed"]
        and independent_detailed["source_model_binding"]["passed"]
        and primary_detailed["source_model_binding"]["source_model_digest"]
        == independent_detailed["source_model_binding"]["source_model_digest"]
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
        "maximum_scaled_prediction_difference": prediction_difference,
        "maximum_scaled_tube_difference": tube_difference,
        "maximum_scaled_metric_difference": metric_difference,
        "maximum_scaled_planning_difference": planning_difference,
        "primary_source_agreement": source_agreement,
        "primary_bank_agreement": bank_difference == 0.0,
        "primary_model_agreement": model_difference <= tolerance,
        "primary_prediction_agreement": prediction_difference <= tolerance,
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
        all(result[field] is True for field in r8r44.AGREEMENT_FIELDS)
        and all(float(result[field]) <= tolerance for field in r8r44.DIFFERENCE_FIELDS)
    )
    output = stage / "analysis/independent.json"
    if not result["passed"]:
        output = stage / "analysis/independent_failure.json"
    _write(output, result)
    if not result["passed"]:
        raise ValueError("independent R8R44 preflight disagrees with primary")
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in r8r44.ARGUMENT_NAMES:
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
