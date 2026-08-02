#!/usr/bin/env python3
"""Frozen T13S10 combined q1/q2 post-queue first-effect audit."""

from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s6_independent_raw_audit as common,
)
from docs.codex.audit_tools import (
    stage4_2r3c3t13s7_causal_multi_history_tube_audit as s7,
)


STAGE = "Stage4.2R3c3T13S10"
PASS_ROUTE = "UNIFIED_POSTQUEUE_Q1_Q2_FIRST_EFFECT_CANDIDATE_Q3_HOLDOUT_REQUIRED"
FAIL_ROUTE = "UNIFIED_POSTQUEUE_Q1_Q2_FIRST_EFFECT_INSUFFICIENT_OBSERVER_REDESIGN"
Q1_STAGE = "Stage4.2R3c3T13S9"
Q2_STAGE = "Stage4.2R3c3T13S5"
Q1_RUN_SUBDIR = "stage4_2r3c3t13s9_unified_postqueue_q1_identification"
Q2_RUN_SUBDIR = "stage4_2r3c3t13s5_lattice_native_split_holdout"
Q1_VARIANT_DIR = "stage4_2r3c3t13s9_environment_variants"
Q2_VARIANT_DIR = "stage4_2r3c3t13s5_environment_variants"
EXPECTED_Q1_RAW_DIGEST = (
    "9ccc67d5eda2b0710d658812207d99666a50af352e42d950086b694a3fa928ad"
)
EXPECTED_Q2_RAW_DIGEST = (
    "09ee846d2fd8c2a516ec01f1b91bcbf8f303885c2377373000ab85dfc45e0f01"
)
EXPECTED_Q1_AUDIT_SHA256 = (
    "df4d7982f98a6216997d89ac5adea9ca2e3b2bf367451c3412d5458ccc5c60e0"
)
EXPECTED_Q2_AUDIT_SHA256 = (
    "dc4d0147ce4fdd8a00105f8fc8ad45466513bac8b012f6843327b1efc271b033"
)
EXPECTED_Q1_CONFIG_SHA256 = (
    "76e95c3e83195d1d0630fccabbaf845a3a5778782691162a3baaff9b4cff6783"
)
EXPECTED_Q2_CONFIG_SHA256 = (
    "a5be86e17cd2f30c569aa43d5ecd37abd66ef30996c1966c63dcc3c30f075011"
)
DESIGN_SHA256 = (
    "ecac014c21bebb04ec8940e7de41f1e82eb294638c500809767d66b40174497c"
)


def authenticate_exact_file(path: Path, expected: str, label: str) -> None:
    if common._sha256(path) != expected:
        raise ValueError(f"T13S10 {label} SHA-256 mismatch")


def _payloads(run_dir: Path, relative: str) -> dict[str, Mapping[str, Any]]:
    paths = sorted((run_dir / relative).glob("payload_*.json"))
    if len(paths) != 68:
        raise ValueError(f"T13S10 {relative} payload inventory mismatch")
    return {
        path.stem.removeprefix("payload_"): common._strict_json(path)
        for path in paths
    }


def adapt_q1_trace_contract(
    raw: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Map only the stage-specific event field to the common post-queue reader."""
    adapted: list[dict[str, Any]] = []
    for source in raw:
        result = copy.copy(source)
        trace = []
        for source_row in source["controller_trace"]:
            row = copy.copy(source_row)
            event = row.get("r3c3t13s9_lattice_event")
            if event not in {"none", "issue", "cancel"}:
                raise ValueError("T13S10 invalid q1 lattice event")
            row["r3c3t13s5_lattice_event"] = event
            trace.append(row)
        result["controller_trace"] = trace
        adapted.append(result)
    return adapted


def _probe_contract_without_schedule(cfg: Mapping[str, Any]) -> dict[str, Any]:
    contract = copy.deepcopy(dict(cfg["lattice_probe"]))
    contract.pop("schedule_by_delay", None)
    return contract


def _fit_model(
    context: Mapping[str, Any], window: str, cfg: Mapping[str, Any]
) -> dict[str, Any]:
    model = s7.fit_local_model(context, window, cfg)
    samples = context["samples"][window]
    inputs = np.asarray([row["odd_input"] for row in samples], dtype=float)
    condition = float(np.linalg.cond(inputs))
    condition_json = condition if math.isfinite(condition) else None
    scales = np.asarray(cfg["response_scales"], dtype=float)
    floor = np.asarray([1e-9, 1e-9, 1e-7, 1e-7, 1e-4], dtype=float)
    floor_scaled = float(np.linalg.norm(floor / scales))
    signal_pass = all(
        np.linalg.norm(np.asarray(row["odd_output"], dtype=float) / scales)
        >= float(cfg["signal_floor_multiplier"]) * floor_scaled
        for row in samples
    )
    condition_pass = bool(
        model["rank"] == model["expected_rank"] == 4
        and condition_json is not None
        and condition_json <= float(cfg["maximum_development_condition_number"])
    )
    model.update(
        {
            "condition_number": condition_json,
            "condition_finite": condition_json is not None,
            "signal_pass": signal_pass,
            "rank_condition_pass": condition_pass,
        }
    )
    return model


def _model_row(model: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "context_id": model["context_id"],
        "campaign": model["campaign"],
        "stratum": model["stratum"],
        "probe_window": model["window"],
        "rank": model["rank"],
        "expected_rank": model["expected_rank"],
        "condition_number": model["condition_number"],
        "condition_finite": model["condition_finite"],
        "signal_pass": model["signal_pass"],
        "rank_condition_pass": model["rank_condition_pass"],
        "tube_pass": model["tube_pass"],
        "maximum_tube_to_cap_ratio": model["maximum_tube_to_cap_ratio"],
    }


def run_audit(args: argparse.Namespace) -> dict[str, Any]:
    authenticate_exact_file(args.design, DESIGN_SHA256, "design")
    authenticate_exact_file(
        args.source_q1_audit, EXPECTED_Q1_AUDIT_SHA256, "q1 source audit"
    )
    authenticate_exact_file(
        args.source_q2_audit, EXPECTED_Q2_AUDIT_SHA256, "q2 source audit"
    )
    authenticate_exact_file(args.q1_config, EXPECTED_Q1_CONFIG_SHA256, "q1 config")
    authenticate_exact_file(args.q2_config, EXPECTED_Q2_CONFIG_SHA256, "q2 config")

    q1_audit = common._strict_json(args.source_q1_audit)
    q2_audit = common._strict_json(args.source_q2_audit)
    q1_config = common._strict_json(args.q1_config)
    q2_config = common._strict_json(args.q2_config)
    if _probe_contract_without_schedule(q1_config) != _probe_contract_without_schedule(
        q2_config
    ):
        raise ValueError("T13S10 q1/q2 nonschedule probe contract mismatch")

    q1_inventory, q1_raw, q1_digest = s7._inventory(
        args.q1_run / Q1_RUN_SUBDIR / "raw"
    )
    q2_inventory, q2_raw, q2_digest = s7._inventory(
        args.q2_run / Q2_RUN_SUBDIR / "raw"
    )
    if not (
        len(q1_raw) == len(q2_raw) == 68
        and q1_digest == EXPECTED_Q1_RAW_DIGEST
        and q2_digest == EXPECTED_Q2_RAW_DIGEST
        and s7._audit_certified(q1_audit, q1_digest)
        and s7._audit_certified(q2_audit, q2_digest)
    ):
        raise ValueError("T13S10 source raw/audit authentication failed")
    if not all(
        result.get("success")
        and result.get("completed")
        and result.get("stage") == expected_stage
        for rows, expected_stage in ((q1_raw, Q1_STAGE), (q2_raw, Q2_STAGE))
        for result in rows
    ):
        raise ValueError("T13S10 raw success/stage mismatch")

    q1_contexts, q1_trace, q1_forbidden = s7.build_contexts(
        "s5",
        adapt_q1_trace_contract(q1_raw),
        _payloads(args.q1_run, Q1_VARIANT_DIR),
        campaign_specific_effects=False,
        single_transition=True,
    )
    q2_contexts, q2_trace, q2_forbidden = s7.build_contexts(
        "s5",
        q2_raw,
        _payloads(args.q2_run, Q2_VARIANT_DIR),
        campaign_specific_effects=False,
        single_transition=True,
    )
    for context in q1_contexts:
        context["campaign"] = "q1_t13s9"
    for context in q2_contexts:
        context["campaign"] = "q2_t13s5"
    contexts = q1_contexts + q2_contexts
    contexts.sort(key=lambda row: (row["stratum"], row["feature_digest"]))
    for index, context in enumerate(contexts):
        context["context_id"] = f"context_{index:02d}"

    probe_cfg = q2_config["lattice_probe"]
    models = {
        (context["context_id"], window): _fit_model(context, window, probe_cfg)
        for context in contexts
        for window in common.WINDOWS
    }
    validation = s7.validate_leave_one_out(
        contexts,
        models,
        probe_cfg,
        all_training_hypotheses=True,
        single_transition=True,
    )
    collisions = s7.exact_collision_audit(contexts, models)
    feature_names = contexts[0]["features"]["transport"]["names"]
    if any(
        context["features"][window]["names"] != feature_names
        for context in contexts
        for window in common.WINDOWS
    ):
        raise ValueError("T13S10 causal feature schema mismatch")
    feature_forbidden = len(s7.FORBIDDEN_FEATURE_NAMES.intersection(feature_names))
    forbidden_count = q1_forbidden + q2_forbidden + feature_forbidden
    model_rows = [_model_row(model) for model in models.values()]
    first_effect_groups = sum(
        len(context["samples"][window])
        for context in contexts
        for window in common.WINDOWS
    )
    summary = {
        "q1_raw_count": len(q1_inventory),
        "q1_raw_bytes": sum(row["size_bytes"] for row in q1_inventory),
        "q1_raw_digest": q1_digest,
        "q1_source_audit_certified": True,
        "q2_raw_count": len(q2_inventory),
        "q2_raw_bytes": sum(row["size_bytes"] for row in q2_inventory),
        "q2_raw_digest": q2_digest,
        "q2_source_audit_certified": True,
        "combined_raw_count": len(q1_inventory) + len(q2_inventory),
        "combined_context_count": len(contexts),
        "combined_baseline_count": len(contexts),
        "combined_signed_probe_count": len(q1_raw) + len(q2_raw) - len(contexts),
        "trace_identity_pass_count": q1_trace + q2_trace,
        "trace_identity_expected": 136,
        "postqueue_first_effect_contract_pass_count": first_effect_groups,
        "postqueue_first_effect_contract_expected": 64,
        "single_transition_signed_extraction_count": len(validation),
        "single_transition_signed_extraction_expected": 128,
        "pre_effect_causality_pass_count": sum(
            row["pre_effect_causality_pass"] for row in validation
        ),
        "local_model_count": len(model_rows),
        "local_signal_pass_count": sum(row["signal_pass"] for row in model_rows),
        "local_rank_condition_pass_count": sum(
            row["rank_condition_pass"] for row in model_rows
        ),
        "local_tube_pass_count": sum(row["tube_pass"] for row in model_rows),
        "maximum_finite_condition_number": s7.maximum_present(
            [row["condition_number"] for row in model_rows]
        ),
        "nonfinite_condition_count": sum(
            not row["condition_finite"] for row in model_rows
        ),
        "maximum_local_tube_to_cap_ratio": max(
            row["maximum_tube_to_cap_ratio"] for row in model_rows
        ),
        "leave_one_context_out_fold_count": len(contexts),
        "heldout_prediction_count": len(validation),
        "supported_hypothesis_pass_count": sum(
            row["supported_hypothesis_pass"] for row in validation
        ),
        "componentwise_containment_pass_count": sum(
            row["componentwise_containment_pass"] for row in validation
        ),
        "scaled_relative_error_pass_count": sum(
            row["scaled_relative_error_pass"] for row in validation
        ),
        "maximum_finite_scaled_relative_error": s7.maximum_present(
            [row["nearest_scaled_relative_error"] for row in validation]
        ),
        "forbidden_feature_or_trace_input_count": forbidden_count,
        **collisions,
    }
    passed = bool(
        summary["q1_raw_count"] == summary["q2_raw_count"] == 68
        and summary["combined_raw_count"] == summary["trace_identity_pass_count"] == 136
        and summary["trace_identity_expected"] == 136
        and summary["combined_context_count"] == summary["combined_baseline_count"] == 8
        and summary["combined_signed_probe_count"] == 128
        and summary["postqueue_first_effect_contract_pass_count"]
        == summary["postqueue_first_effect_contract_expected"]
        == 64
        and summary["single_transition_signed_extraction_count"]
        == summary["single_transition_signed_extraction_expected"]
        == summary["pre_effect_causality_pass_count"]
        == 128
        and summary["local_model_count"]
        == summary["local_signal_pass_count"]
        == summary["local_rank_condition_pass_count"]
        == summary["local_tube_pass_count"]
        == 16
        and summary["nonfinite_condition_count"] == 0
        and summary["leave_one_context_out_fold_count"] == 8
        and summary["heldout_prediction_count"]
        == summary["supported_hypothesis_pass_count"]
        == summary["componentwise_containment_pass_count"]
        == summary["scaled_relative_error_pass_count"]
        == 128
        and summary["disjoint_exact_causal_alias_pair_count"] == 0
        and summary["forbidden_feature_or_trace_input_count"] == 0
    )
    return {
        "schema_version": 1,
        "stage": STAGE,
        "audit_revision": "combined_postqueue_first_effect_all_hypotheses_loco_v1",
        "preregistered_design": str(args.design),
        "preregistered_design_sha256": DESIGN_SHA256,
        "source_q1_run": str(args.q1_run),
        "source_q1_audit": str(args.source_q1_audit),
        "source_q1_audit_sha256": EXPECTED_Q1_AUDIT_SHA256,
        "source_q2_run": str(args.q2_run),
        "source_q2_audit": str(args.source_q2_audit),
        "source_q2_audit_sha256": EXPECTED_Q2_AUDIT_SHA256,
        "source_raw_rewritten": False,
        "in_memory_event_field_adapter_only": True,
        "first_effect_transition_only": True,
        "adjacent_cancellation_transition_used": False,
        "all_three_training_hypotheses_retained": True,
        "formal_timing_unchanged": True,
        "all_source_data_consumed_not_blind": True,
        "real_tsc_executed": False,
        "controller_optimizer_or_plant_step_executed": False,
        "feature_schema": list(feature_names),
        "feature_uses_pair_history_prefix_source_wire_or_future": False,
        "summary": summary,
        "local_models": model_rows,
        "validation_results": validation,
        "passed": passed,
        "route": PASS_ROUTE if passed else FAIL_ROUTE,
        "new_q3_holdout_required_before_controller": passed,
        "observer_or_state_conditioned_redesign_required": not passed,
        "real_mpc_authorized": False,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "bc_dagger_or_rl_allowed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--q1-run", required=True, type=Path)
    parser.add_argument("--source-q1-audit", required=True, type=Path)
    parser.add_argument("--q2-run", required=True, type=Path)
    parser.add_argument("--source-q2-audit", required=True, type=Path)
    parser.add_argument("--q1-config", required=True, type=Path)
    parser.add_argument("--q2-config", required=True, type=Path)
    parser.add_argument("--design", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = run_audit(args)
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
