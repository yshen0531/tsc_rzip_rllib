#!/usr/bin/env python3
"""T13S7R1 wrapper enabling authenticated campaign-specific effect states."""

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


STAGE = "Stage4.2R3c3T13S7R1"
PASS_ROUTE = (
    "CAMPAIGN_SPECIFIC_CAUSAL_MULTI_HYPOTHESIS_CANDIDATE_Q3_HOLDOUT_REQUIRED"
)
FAIL_ROUTE = "CAMPAIGN_SPECIFIC_CAUSAL_MULTI_HYPOTHESIS_TUBE_INSUFFICIENT_REDESIGN"
EFFECT_FORENSIC_SHA256 = (
    "c78bd97c5c60c526d609ea5da15547abe5cb73927552086573f4a856d12e3f4a"
)


def authenticate_effect_forensic(path: Path) -> dict[str, Any]:
    if common._sha256(path) != EFFECT_FORENSIC_SHA256:
        raise ValueError("T13S7R1 effect forensic SHA-256 mismatch")
    payload = common._strict_json(path)
    summary = payload.get("summary") or {}
    exact = bool(
        payload.get("stage") == "Stage4.2R3c3T13S7"
        and payload.get("conclusion")
        == "S1 is queue-aware; S5 is post-queue immediate"
        and summary.get("s1_group_count") == 24
        and summary.get("s1_campaign_contract_match_count") == 24
        and summary.get("s1_delay2_group_count") == 12
        and summary.get("s1_delay2_campaign_contract_match_count") == 12
        and summary.get("s1_delay2_immediate_match_count") == 0
        and summary.get("s5_group_count") == 32
        and summary.get("s5_campaign_contract_match_count") == 32
        and summary.get("s5_immediate_match_count") == 32
        and summary.get("s5_delay2_group_count") == 16
        and summary.get("s5_delay2_immediate_match_count") == 16
        and payload.get("real_tsc_executed") is False
    )
    if not exact:
        raise ValueError("T13S7R1 effect forensic content mismatch")
    return payload


def run_r1_audit(args: argparse.Namespace) -> dict[str, Any]:
    authenticate_effect_forensic(args.source_effect_forensic)
    output = s7.run_audit(args, campaign_specific_effects=True)
    output.update(
        {
            "stage": STAGE,
            "audit_revision": "campaign_specific_effect_contract_loco_v1",
            "source_t13s7_effect_forensic": str(args.source_effect_forensic),
            "source_t13s7_effect_forensic_sha256": EFFECT_FORENSIC_SHA256,
            "campaign_specific_effect_contract": {
                "s1": "issue_plus_action_delay_plus_one",
                "s5": "post_queue_issue_plus_one",
                "authenticated_group_count": 56,
                "expected_group_count": 56,
                "passed": True,
            },
        }
    )
    output["summary"]["campaign_specific_effect_timing_pass_count"] = 56
    output["summary"]["campaign_specific_effect_timing_expected"] = 56
    output["route"] = PASS_ROUTE if output["passed"] else FAIL_ROUTE
    output["t13s7_result_rewritten"] = False
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
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = run_r1_audit(args)
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
