#!/usr/bin/env python3
"""Independent raw-bank and augmented-LS audit for R8R33."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r31_independent_forensics as ind31,
)
from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r32_independent_forensics as ind32,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r31_aligned_explicit_four_coordinate_feedback_sentinel
    as r8r31,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r33_uniformly_supported_rank12_schedule_generalizing_feedback_preflight
    as r8r33,
)


STAGE = r8r33.STAGE
IDENTITY = r8r33.IDENTITY
AUDIT_KIND = "uniformly_supported_rank12_schedule_generalizing_preflight_independent"

_read = ind32._read
_write = ind32._write
_sha = ind32._sha
_digest = ind32._digest
_maximum_difference = ind32._maximum_difference
_without_digests = ind32._without_digests


def audit(args: argparse.Namespace) -> dict[str, Any]:
    ctx = r8r33.load_context(args)
    if ctx.cfg.get("stage") != STAGE or ctx.cfg.get("identity") != IDENTITY:
        raise ValueError("independent R8R33 configuration identity changed")
    stage = ctx.paths.stage
    summary_path = stage / "analysis/primary_summary.json"
    detailed_path = stage / "analysis/primary_detailed.json"
    model_path = stage / "model/preflight_model.json"
    primary_summary = _read(summary_path)
    primary_detailed = _read(detailed_path)
    primary_model = _read(model_path)

    production_authentication = r8r33.authenticate_sources(ctx)
    independent_transitive = ind31._authenticate(
        args, ctx.r8r32_ctx.source_ctx.cfg
    )
    bank = ind31._build_bank(args, ctx.r8r32_ctx.source_ctx.cfg)
    bank_evidence = ind31._bank_evidence(bank)
    _ignored, context_meta = r8r31.r8r23.build_bank(
        ctx.r8r32_ctx.source_ctx.r8r23_ctx
    )
    if set(context_meta) != {
        (str(row["pair_id"]), str(row["history_member"])) for row in bank
    }:
        raise ValueError("independent R8R33 planning metadata coverage changed")

    independent_detailed, independent_model = r8r33.compute_from_bank(
        ctx,
        production_authentication,
        bank,
        context_meta,
        bank_evidence,
        solver="augmented_lstsq",
        fit_head_fn=ind32._fit_head,
        rank_head_fn=ind32._rank_head,
    )
    tolerance = float(ctx.cfg["offline_gate"]["primary_independent_absolute_tolerance"])
    bank_difference = _maximum_difference(
        primary_detailed["bank_evidence"], independent_detailed["bank_evidence"]
    )
    prediction_difference = ind32._prediction_difference(
        primary_model, independent_model, bank
    )
    auxiliary_difference = _maximum_difference(
        _without_digests(
            {
                "pair_tube": primary_model["pair_tube"],
                "schedule_tube": primary_model["schedule_tube"],
                "combined_tube": primary_model["combined_tube"],
                "support": primary_model["support"],
                "transition_hulls": primary_model["transition_hulls"],
                "representation_rank_audit": primary_model[
                    "representation_rank_audit"
                ],
                "representation_rank_gate_passed": primary_model[
                    "representation_rank_gate_passed"
                ],
            }
        ),
        _without_digests(
            {
                "pair_tube": independent_model["pair_tube"],
                "schedule_tube": independent_model["schedule_tube"],
                "combined_tube": independent_model["combined_tube"],
                "support": independent_model["support"],
                "transition_hulls": independent_model["transition_hulls"],
                "representation_rank_audit": independent_model[
                    "representation_rank_audit"
                ],
                "representation_rank_gate_passed": independent_model[
                    "representation_rank_gate_passed"
                ],
            }
        ),
    )
    model_difference = max(prediction_difference, auxiliary_difference)
    outer_difference = _maximum_difference(
        _without_digests(primary_detailed["outer_model_evaluation"]),
        _without_digests(independent_detailed["outer_model_evaluation"]),
    )
    schedule_difference = _maximum_difference(
        _without_digests(primary_detailed["schedule_jackknife"]),
        _without_digests(independent_detailed["schedule_jackknife"]),
    )
    planning_fields = (
        "representation_rank_audit",
        "pair_planning_tube_evidence",
        "combined_tube_maximum_physical_half_width",
        "combined_tube_cap_passed",
        "model_gate_passed",
        "transition_hulls",
        "planning_evaluation",
        "fault_injection",
    )
    planning_difference = _maximum_difference(
        _without_digests({key: primary_detailed[key] for key in planning_fields}),
        _without_digests(
            {key: independent_detailed[key] for key in planning_fields}
        ),
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
    )
    result = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "audit_kind": AUDIT_KIND,
        "source_authentication": {
            "r8r32_final": production_authentication,
            "independent_transitive": independent_transitive,
            "passed": True,
        },
        "bank_evidence": bank_evidence,
        "independent_model_artifact_sha256": _digest(independent_model),
        "maximum_bank_absolute_difference": bank_difference,
        "maximum_model_absolute_difference": model_difference,
        "maximum_model_prediction_absolute_difference": prediction_difference,
        "maximum_model_auxiliary_absolute_difference": auxiliary_difference,
        "maximum_outer_absolute_difference": outer_difference,
        "maximum_schedule_absolute_difference": schedule_difference,
        "maximum_planning_absolute_difference": planning_difference,
        "primary_bank_agreement": bank_difference <= tolerance,
        "primary_model_agreement": model_difference <= tolerance,
        "primary_outer_agreement": outer_difference <= tolerance,
        "primary_schedule_agreement": schedule_difference <= tolerance,
        "primary_planning_agreement": planning_difference <= tolerance,
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
        result["primary_bank_agreement"]
        and result["primary_model_agreement"]
        and result["primary_outer_agreement"]
        and result["primary_schedule_agreement"]
        and result["primary_planning_agreement"]
        and result["primary_route_agreement"]
        and result["primary_outcome_agreement"]
    )
    if not result["passed"]:
        _write(stage / "analysis/independent_failure.json", result)
        raise ValueError("independent R8R33 preflight disagrees with primary")
    _write(stage / "analysis/independent.json", result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "config",
        "run-dir",
        "r8r32-run",
        "r8r31-run",
        "r8r23-run",
        "r8r28-run",
        "r8r22-run",
        "r8r7-run",
        "r8r12-run",
        "r8r14-run",
        "r8r15-run",
        "r8r19-run",
        "r8r20-run",
        "r8r27-run",
        "r8-run",
        "r8r1-output",
        "r8r6-run",
        "source-d1r11-run",
        "source-r2-run",
        "source-r4-run",
        "source-r6-run",
        "source-s21-run",
        "source-s23r1-output",
        "source-s24-run",
        "source-d1r9-v1",
        "source-d1r9-v2",
        "source-d1r10-run",
        "source-d1r10-audit",
        "source-stage42r3b-run",
        "source-stage42r3c3-run",
        "source-stage42r3c3-bank-dir",
        "source-stage42r3c3t1-run",
        "source-stage42r3c3t1-audit-dir",
        "source-stage42r3c3t3-controller-bank",
        "q1-run",
        "q2-run",
        "q1-audit",
        "q2-audit",
        "r3b-server-audit",
        "r3b-snapshot-checks",
    ):
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
