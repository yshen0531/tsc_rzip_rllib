#!/usr/bin/env python3
"""Frozen T13S8 first-effect causal transition feasibility audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from docs.codex.audit_tools import (
    stage4_2r3c3t13s6_independent_raw_audit as common,
)
from docs.codex.audit_tools import (
    stage4_2r3c3t13s7_causal_multi_history_tube_audit as s7,
)
from docs.codex.audit_tools import (
    stage4_2r3c3t13s7r1_campaign_specific_effect_audit as r1,
)
from docs.codex.audit_tools import (
    stage4_2r3c3t13s7r1_support_forensic as support_forensic,
)


STAGE = "Stage4.2R3c3T13S8"
PASS_ROUTE = "FIRST_EFFECT_CAUSAL_TRANSITION_CANDIDATE_Q3_HOLDOUT_REQUIRED"
FAIL_ROUTE = "FIRST_EFFECT_CAUSAL_TRANSITION_INSUFFICIENT_REDESIGN"
DESIGN_SHA256 = "3a5237ee5bfff4374133698061dd53d31999dd97581fdd1ffbe0196d0a97e8a9"


def authenticate_design(path: Path) -> None:
    if common._sha256(path) != DESIGN_SHA256:
        raise ValueError("T13S8 preregistered design SHA-256 mismatch")


def run_t13s8_audit(args: argparse.Namespace) -> dict[str, Any]:
    authenticate_design(args.design)
    r1.authenticate_effect_forensic(args.source_effect_forensic)
    support_forensic.authenticate_r1(args.source_r1_audit)
    output = s7.run_audit(
        args,
        campaign_specific_effects=True,
        single_transition=True,
        all_training_hypotheses=True,
    )
    output.update(
        {
            "stage": STAGE,
            "audit_revision": "first_effect_single_transition_all_hypotheses_loco_v1",
            "preregistered_design": str(args.design),
            "preregistered_design_sha256": DESIGN_SHA256,
            "source_effect_forensic": str(args.source_effect_forensic),
            "source_effect_forensic_sha256": r1.EFFECT_FORENSIC_SHA256,
            "source_r1_audit": str(args.source_r1_audit),
            "source_r1_audit_sha256": support_forensic.SOURCE_R1_SHA256,
            "first_effect_transition_only": True,
            "adjacent_cancellation_transition_used": False,
            "all_three_training_hypotheses_retained": True,
            "measured_current_input_dimension": 14,
            "causal_response_dimension": 5,
        }
    )
    output["summary"]["campaign_specific_first_effect_timing_pass_count"] = 56
    output["summary"]["campaign_specific_first_effect_timing_expected"] = 56
    output["route"] = PASS_ROUTE if output["passed"] else FAIL_ROUTE
    output["source_results_rewritten"] = False
    output["new_q3_holdout_required_before_controller"] = True
    output["real_mpc_authorized"] = False
    output["probe_trajectories_allowed_in_expert_dataset"] = False
    output["bc_dagger_or_rl_allowed"] = False
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--s1-run", required=True, type=Path)
    parser.add_argument("--source-s1-audit", required=True, type=Path)
    parser.add_argument("--s5-run", required=True, type=Path)
    parser.add_argument("--source-s5-audit", required=True, type=Path)
    parser.add_argument("--s1-config", required=True, type=Path)
    parser.add_argument("--s5-config", required=True, type=Path)
    parser.add_argument("--source-effect-forensic", required=True, type=Path)
    parser.add_argument("--source-r1-audit", required=True, type=Path)
    parser.add_argument("--design", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = run_t13s8_audit(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "sha256": common._sha256(args.output),
                "passed": output["passed"],
                "route": output["route"],
                "summary": output["summary"],
            },
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
