#!/usr/bin/env python3
"""Frozen T13S12 causal natural-history observer preflight."""

from __future__ import annotations

import argparse
from collections import defaultdict
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
from docs.codex.audit_tools import (
    stage4_2r3c3t13s10_combined_postqueue_first_effect_audit as s10,
)
from docs.codex.audit_tools import (
    stage4_2r3c3t13s11_causal_calibration_conditioned_braking_preflight as s11,
)


STAGE = "Stage4.2R3c3T13S12"
PASS_ROUTE = (
    "CAUSAL_NATURAL_HISTORY_OBSERVER_PREFLIGHT_"
    "CANDIDATE_Q3_SEQUENCE_TSC_REQUIRED"
)
FAIL_ROUTE = (
    "CAUSAL_NATURAL_HISTORY_OBSERVER_PREFLIGHT_"
    "INSUFFICIENT_NONLINEAR_OBSERVER_REDESIGN"
)
DESIGN_SHA256 = (
    "0e49d9a992d27ae89bf2c6a2f0f153e38a8737459af38473576303d1ca60b541"
)
SOURCE_T13S11_SHA256 = (
    "6e595fbd4e86276d449fc953edcb06b676bd282b6f0bd68d4e5ac3effe97ffbe"
)
STATE_FIELDS = (
    "R_target_error",
    "Z_target_error",
    "Ip_target_error",
    "causal_vR",
    "causal_vZ",
    "velocity_known",
    *(f"measured_coil_current_{index}" for index in range(14)),
    *(f"backward_measured_coil_current_delta_{index}" for index in range(14)),
    "coil_history_known",
)


def _history_signature(
    baseline: Mapping[str, Any], payload: Mapping[str, Any]
) -> dict[str, Any]:
    spec = baseline["spec"]
    delay = int(spec["action_delay_steps"])
    slew = float(spec["slew_scale"])
    issue = 16 if delay == 0 else 14
    trajectory = baseline["trajectory"]
    if len(trajectory) <= issue:
        raise ValueError("T13S12 baseline history is shorter than braking issue")
    current_scales = s7._current_scales(payload)
    target = payload["cfg"]["target"]
    base_target = payload["train_cfg"]["target"]
    expected_target = {
        "R": float(base_target["R"]) + float(spec["target_R_offset_m"]),
        "Z": float(base_target["Z"]) + float(spec["target_Z_offset_m"]),
        "Ip": float(base_target["Ip"]) + float(spec["target_Ip_offset_A"]),
    }
    if any(abs(float(target[key]) - expected_target[key]) > 1e-12 for key in expected_target):
        raise ValueError("T13S12 deployed target does not match source target contract")
    values = []
    for index in range(issue + 1):
        row = trajectory[index]
        currents = np.asarray(row["currents_a_tsc"], dtype=float)
        known = float(index > 0)
        if index:
            previous = trajectory[index - 1]
            velocity = np.asarray(
                [
                    (float(row["R"]) - float(previous["R"])) / 0.01,
                    (float(row["Z"]) - float(previous["Z"])) / 0.01,
                ]
            )
            current_delta = currents - np.asarray(
                previous["currents_a_tsc"], dtype=float
            )
        else:
            velocity = np.zeros(2)
            current_delta = np.zeros(14)
        values.extend(
            [
                (float(row["R"]) - float(target["R"])) / 0.03,
                (float(row["Z"]) - float(target["Z"])) / 0.03,
                (float(row["Ip"]) - float(target["Ip"])) / 10000.0,
                velocity[0] / 0.1,
                velocity[1] / 0.1,
                known,
                *(currents / current_scales),
                *(current_delta / current_scales),
                known,
            ]
        )
    values.extend([delay / 2.0, (slew - 1.0) / 0.1])
    vector = np.asarray(values, dtype=float)
    expected_length = (issue + 1) * len(STATE_FIELDS) + 2
    finite = bool(vector.shape == (expected_length,) and np.all(np.isfinite(vector)))
    return {
        "values": vector,
        "braking_issue_step": issue,
        "history_state_count": issue + 1,
        "history_fields_per_state": len(STATE_FIELDS),
        "history_vector_length": len(vector),
        "target_contract_exact": True,
        "finite_schema_length_pass": finite,
        "causal_endpoint_pass": True,
        "passed": finite,
    }


def _history_by_digest(
    raw: Sequence[Mapping[str, Any]],
    payloads: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    output = {}
    for members in s11._raw_groups(raw).values():
        baseline = members["baseline"]
        payload = payloads[str(baseline["experiment_id"])]
        digest = s11._feature_digest(baseline, members, payload)
        if digest in output:
            raise ValueError("T13S12 duplicate baseline history digest")
        output[digest] = _history_signature(baseline, payload)
    return output


def _rms_whiten(values: np.ndarray) -> tuple[np.ndarray, np.ndarray, bool]:
    values = np.asarray(values, dtype=float)
    rms = np.sqrt(np.mean(np.square(values), axis=0))
    passed = bool(np.all(np.isfinite(rms)) and np.all(rms > 1e-12))
    return values / np.where(rms > 1e-12, rms, 1.0), rms, passed


def _fit_fold(
    held: Mapping[str, Any],
    training: Sequence[Mapping[str, Any]],
    cfg: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    histories = np.asarray([row["history_signature"] for row in training])
    mean = np.mean(histories, axis=0)
    centered = histories - mean
    history_rank = s11._affine_rank(histories)
    _, _, history_vt = np.linalg.svd(centered, full_matrices=False)
    history_basis = history_vt[:2]
    raw_scores = centered @ history_basis.T
    scores, history_rms, history_whitening_pass = _rms_whiten(raw_scores)
    score_by_context = {
        row["context_id"]: scores[index] for index, row in enumerate(training)
    }
    held_centered = held["history_signature"] - mean
    held_history_support_residual = s11._projection_residual(
        held_centered, history_basis
    )
    held_history_support = held_history_support_residual <= 0.15
    held_score = (held_centered @ history_basis.T) / np.where(
        history_rms > 1e-12, history_rms, 1.0
    )

    train_samples = [
        (context, sample, sign)
        for context in training
        for sample in context["samples"]["braking"]
        for sign in common.SIGNS
    ]
    current_matrix = np.asarray(
        [sample["signed"][sign]["input"] for _, sample, sign in train_samples]
    )
    current_rank = int(np.linalg.matrix_rank(current_matrix))
    _, _, current_vt = np.linalg.svd(current_matrix, full_matrices=False)
    current_basis = current_vt[:4]
    raw_current_coordinates = current_matrix @ current_basis.T
    current_coordinates, current_rms, current_whitening_pass = _rms_whiten(
        raw_current_coordinates
    )
    design = np.asarray(
        [
            s11._interaction_row(
                current_coordinates[index], score_by_context[context["context_id"]]
            )
            for index, (context, _, _) in enumerate(train_samples)
        ]
    )
    response = np.asarray(
        [sample["signed"][sign]["output"] for _, sample, sign in train_samples]
    )
    design_rank = int(np.linalg.matrix_rank(design))
    condition = float(np.linalg.cond(design))
    condition_json = condition if math.isfinite(condition) else None
    jacobian = np.linalg.lstsq(design, response, rcond=None)[0]
    residual = response - design @ jacobian
    floor = np.asarray([1e-9, 1e-9, 1e-7, 1e-7, 1e-4])
    radius = floor + float(cfg["tube_residual_multiplier"]) * np.max(
        np.abs(residual), axis=0
    )
    caps = np.asarray(cfg["tube_caps_unscaled"], dtype=float)[:5]
    scales = np.asarray(cfg["response_scales"], dtype=float)
    floor_scaled = float(np.linalg.norm(floor / scales))
    signal_pass = all(
        np.linalg.norm(np.asarray(sample["odd_output"]) / scales)
        >= float(cfg["signal_floor_multiplier"]) * floor_scaled
        for context in training
        for sample in context["samples"]["braking"]
    )
    whitening_pass = bool(history_whitening_pass and current_whitening_pass)
    design_pass = bool(
        history_rank == 2
        and current_rank >= 4
        and whitening_pass
        and design_rank == 12
        and condition_json is not None
        and condition_json <= 30.0
        and signal_pass
    )
    tube_pass = bool(np.all(radius <= caps))
    rows = []
    for sample in held["samples"]["braking"]:
        for sign in common.SIGNS:
            model_input = np.asarray(sample["signed"][sign]["input"])
            current_support_residual = s11._projection_residual(
                model_input, current_basis
            )
            current_support = current_support_residual <= 0.15
            supported = bool(held_history_support and current_support)
            actual = np.asarray(sample["signed"][sign]["output"])
            if supported:
                held_current = (model_input @ current_basis.T) / np.where(
                    current_rms > 1e-12, current_rms, 1.0
                )
                predicted = s11._interaction_row(held_current, held_score) @ jacobian
                error = s7._scaled_relative(actual, predicted, scales)
                contained = bool(
                    np.all(np.abs(actual - predicted) <= radius + 1e-15)
                )
            else:
                error = None
                contained = False
            error_pass = bool(error is not None and error <= 0.10)
            passed = bool(
                design_pass
                and tube_pass
                and supported
                and contained
                and error_pass
                and sample["pre_effect_causality_pass"]
            )
            rows.append(
                {
                    "held_context_id": held["context_id"],
                    "held_campaign": held["campaign"],
                    "stratum": held["stratum"],
                    "probe_window": "braking",
                    "probe_direction": sample["direction"],
                    "probe_sign": sign,
                    "causal_history_support_residual": held_history_support_residual,
                    "causal_history_support_pass": held_history_support,
                    "braking_current_support_residual": current_support_residual,
                    "braking_current_support_pass": current_support,
                    "prediction_supported": supported,
                    "componentwise_containment_pass": contained,
                    "scaled_relative_error": error,
                    "scaled_relative_error_pass": error_pass,
                    "pre_effect_causality_pass": sample[
                        "pre_effect_causality_pass"
                    ],
                    "passed": passed,
                }
            )
    model = {
        "held_context_id": held["context_id"],
        "held_campaign": held["campaign"],
        "stratum": held["stratum"],
        "training_context_ids": [row["context_id"] for row in training],
        "history_affine_rank": history_rank,
        "history_affine_rank_pass": history_rank == 2,
        "history_whitening_rms": history_rms.tolist(),
        "current_whitening_rms": current_rms.tolist(),
        "training_whitening_pass": whitening_pass,
        "braking_current_matrix_rank": current_rank,
        "braking_current_basis_rank_pass": current_rank >= 4,
        "interaction_design_rank": design_rank,
        "interaction_condition_number": condition_json,
        "interaction_signal_pass": signal_pass,
        "interaction_rank_condition_signal_pass": design_pass,
        "tube_pass": tube_pass,
        "tube_radius": radius.tolist(),
        "maximum_tube_to_cap_ratio": float(np.max(radius / caps)),
        "held_causal_history_support_residual": held_history_support_residual,
        "held_causal_history_support_pass": held_history_support,
    }
    return model, rows


def _collision_audit(
    contexts: Sequence[Mapping[str, Any]], models: Sequence[Mapping[str, Any]]
) -> dict[str, int]:
    radius = {
        row["held_context_id"]: np.asarray(row["tube_radius"]) for row in models
    }
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for context in contexts:
        for sample in context["samples"]["braking"]:
            for sign in common.SIGNS:
                key = common._canonical_digest(
                    {
                        "history": context["history_signature"].tolist(),
                        "input": sample["signed"][sign]["input"].tolist(),
                    }
                )
                grouped[key].append(
                    {
                        "context_id": context["context_id"],
                        "actual": np.asarray(sample["signed"][sign]["output"]),
                    }
                )
    collisions = [rows for rows in grouped.values() if len(rows) > 1]
    disjoint = 0
    for rows in collisions:
        for index, left in enumerate(rows):
            for right in rows[index + 1 :]:
                if np.any(
                    np.abs(left["actual"] - right["actual"])
                    > radius[left["context_id"]]
                    + radius[right["context_id"]]
                    + 1e-15
                ):
                    disjoint += 1
    return {
        "exact_history_input_collision_group_count": len(collisions),
        "disjoint_exact_causal_history_input_alias_pair_count": disjoint,
    }


def run_audit(args: argparse.Namespace) -> dict[str, Any]:
    for path, expected, label in (
        (args.design, DESIGN_SHA256, "design"),
        (args.source_t13s11_audit, SOURCE_T13S11_SHA256, "T13S11 audit"),
        (args.source_t13s10_audit, s11.SOURCE_T13S10_SHA256, "T13S10 audit"),
        (args.source_q1_audit, s10.EXPECTED_Q1_AUDIT_SHA256, "q1 audit"),
        (args.source_q2_audit, s10.EXPECTED_Q2_AUDIT_SHA256, "q2 audit"),
        (args.q1_config, s10.EXPECTED_Q1_CONFIG_SHA256, "q1 config"),
        (args.q2_config, s10.EXPECTED_Q2_CONFIG_SHA256, "q2 config"),
    ):
        s10.authenticate_exact_file(path, expected, label)
    source_t13s11 = common._strict_json(args.source_t13s11_audit)
    if source_t13s11.get("route") != s11.FAIL_ROUTE or source_t13s11.get("passed"):
        raise ValueError("T13S12 source T13S11 result mismatch")
    q1_audit = common._strict_json(args.source_q1_audit)
    q2_audit = common._strict_json(args.source_q2_audit)
    q1_config = common._strict_json(args.q1_config)
    q2_config = common._strict_json(args.q2_config)
    if s10._probe_contract_without_schedule(q1_config) != s10._probe_contract_without_schedule(
        q2_config
    ):
        raise ValueError("T13S12 source probe contract mismatch")
    q1_inventory, q1_raw, q1_digest = s7._inventory(
        args.q1_run / s10.Q1_RUN_SUBDIR / "raw"
    )
    q2_inventory, q2_raw, q2_digest = s7._inventory(
        args.q2_run / s10.Q2_RUN_SUBDIR / "raw"
    )
    if not (
        len(q1_raw) == len(q2_raw) == 68
        and q1_digest == s10.EXPECTED_Q1_RAW_DIGEST
        and q2_digest == s10.EXPECTED_Q2_RAW_DIGEST
        and s7._audit_certified(q1_audit, q1_digest)
        and s7._audit_certified(q2_audit, q2_digest)
    ):
        raise ValueError("T13S12 source authentication failed")
    q1_payloads = s10._payloads(args.q1_run, s10.Q1_VARIANT_DIR)
    q2_payloads = s10._payloads(args.q2_run, s10.Q2_VARIANT_DIR)
    q1_contexts, q1_trace, q1_forbidden = s7.build_contexts(
        "s5", s10.adapt_q1_trace_contract(q1_raw), q1_payloads, single_transition=True
    )
    q2_contexts, q2_trace, q2_forbidden = s7.build_contexts(
        "s5", q2_raw, q2_payloads, single_transition=True
    )
    q1_histories = _history_by_digest(q1_raw, q1_payloads)
    q2_histories = _history_by_digest(q2_raw, q2_payloads)
    for context in q1_contexts:
        context["campaign"] = "q1_t13s9"
        context["history"] = q1_histories[context["feature_digest"]]
    for context in q2_contexts:
        context["campaign"] = "q2_t13s5"
        context["history"] = q2_histories[context["feature_digest"]]
    contexts = q1_contexts + q2_contexts
    contexts.sort(key=lambda row: (row["stratum"], row["feature_digest"]))
    for index, context in enumerate(contexts):
        context["context_id"] = f"context_{index:02d}"
        context["history_signature"] = context["history"]["values"]
    models = []
    validation = []
    cfg = q2_config["lattice_probe"]
    for stratum in ("easy", "hard"):
        stratum_contexts = [row for row in contexts if row["stratum"] == stratum]
        for held in stratum_contexts:
            model, rows = _fit_fold(
                held, [row for row in stratum_contexts if row is not held], cfg
            )
            models.append(model)
            validation.extend(rows)
    collisions = _collision_audit(contexts, models)
    forbidden_count = q1_forbidden + q2_forbidden + len(
        s7.FORBIDDEN_FEATURE_NAMES.intersection(STATE_FIELDS)
    )
    summary = {
        "q1_raw_count": len(q1_inventory),
        "q1_raw_bytes": sum(row["size_bytes"] for row in q1_inventory),
        "q1_raw_digest": q1_digest,
        "q2_raw_count": len(q2_inventory),
        "q2_raw_bytes": sum(row["size_bytes"] for row in q2_inventory),
        "q2_raw_digest": q2_digest,
        "combined_raw_count": len(q1_inventory) + len(q2_inventory),
        "trace_identity_pass_count": q1_trace + q2_trace,
        "trace_identity_expected": 136,
        "causal_history_count": len(contexts),
        "causal_history_schema_pass_count": sum(
            row["history"]["passed"] for row in contexts
        ),
        "signed_braking_extraction_count": len(validation),
        "signed_braking_extraction_expected": 64,
        "braking_pre_effect_causality_pass_count": sum(
            row["pre_effect_causality_pass"] for row in validation
        ),
        "fold_count": len(models),
        "history_affine_rank_pass_count": sum(
            row["history_affine_rank_pass"] for row in models
        ),
        "training_whitening_pass_count": sum(
            row["training_whitening_pass"] for row in models
        ),
        "braking_current_basis_rank_pass_count": sum(
            row["braking_current_basis_rank_pass"] for row in models
        ),
        "interaction_rank_condition_signal_pass_count": sum(
            row["interaction_rank_condition_signal_pass"] for row in models
        ),
        "interaction_tube_pass_count": sum(row["tube_pass"] for row in models),
        "maximum_finite_interaction_condition_number": s7.maximum_present(
            [row["interaction_condition_number"] for row in models]
        ),
        "maximum_interaction_tube_to_cap_ratio": max(
            row["maximum_tube_to_cap_ratio"] for row in models
        ),
        "held_causal_history_support_pass_count": sum(
            row["held_causal_history_support_pass"] for row in models
        ),
        "held_braking_current_support_pass_count": sum(
            row["braking_current_support_pass"] for row in validation
        ),
        "held_prediction_supported_count": sum(
            row["prediction_supported"] for row in validation
        ),
        "componentwise_containment_pass_count": sum(
            row["componentwise_containment_pass"] for row in validation
        ),
        "scaled_relative_error_pass_count": sum(
            row["scaled_relative_error_pass"] for row in validation
        ),
        "both_response_gates_pass_count": sum(row["passed"] for row in validation),
        "maximum_finite_scaled_relative_error": s7.maximum_present(
            [row["scaled_relative_error"] for row in validation]
        ),
        "forbidden_feature_or_trace_model_input_count": forbidden_count,
        **collisions,
    }
    passed = bool(
        summary["q1_raw_count"] == summary["q2_raw_count"] == 68
        and summary["combined_raw_count"]
        == summary["trace_identity_pass_count"]
        == summary["trace_identity_expected"]
        == 136
        and summary["causal_history_count"]
        == summary["causal_history_schema_pass_count"]
        == 8
        and summary["signed_braking_extraction_count"]
        == summary["signed_braking_extraction_expected"]
        == summary["braking_pre_effect_causality_pass_count"]
        == 64
        and summary["fold_count"]
        == summary["history_affine_rank_pass_count"]
        == summary["training_whitening_pass_count"]
        == summary["braking_current_basis_rank_pass_count"]
        == summary["interaction_rank_condition_signal_pass_count"]
        == summary["interaction_tube_pass_count"]
        == summary["held_causal_history_support_pass_count"]
        == 8
        and summary["held_braking_current_support_pass_count"]
        == summary["held_prediction_supported_count"]
        == summary["componentwise_containment_pass_count"]
        == summary["scaled_relative_error_pass_count"]
        == summary["both_response_gates_pass_count"]
        == 64
        and summary["disjoint_exact_causal_history_input_alias_pair_count"] == 0
        and summary["forbidden_feature_or_trace_model_input_count"] == 0
    )
    return {
        "schema_version": 1,
        "stage": STAGE,
        "audit_revision": "causal_natural_history_whitened_braking_loco_v1",
        "preregistered_design": str(args.design),
        "preregistered_design_sha256": DESIGN_SHA256,
        "source_t13s11_audit_sha256": SOURCE_T13S11_SHA256,
        "source_t13s10_audit_sha256": s11.SOURCE_T13S10_SHA256,
        "source_q1_run": str(args.q1_run),
        "source_q2_run": str(args.q2_run),
        "history_state_field_schema": list(STATE_FIELDS),
        "history_uses_only_baseline_current_and_past_visible_measurements": True,
        "history_uses_requested_or_source_action": False,
        "support_on_full_rank_interaction_coordinate_forbidden": True,
        "training_only_history_and_current_whitening": True,
        "source_raw_rewritten": False,
        "formal_timing_unchanged": True,
        "all_source_data_consumed_not_blind": True,
        "real_tsc_executed": False,
        "controller_optimizer_or_plant_step_executed": False,
        "summary": summary,
        "fold_models": models,
        "validation_results": validation,
        "passed": passed,
        "route": PASS_ROUTE if passed else FAIL_ROUTE,
        "fresh_q3_same_trajectory_sequence_tsc_required": passed,
        "nonlinear_or_recurrent_observer_redesign_required": not passed,
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
    parser.add_argument("--source-t13s10-audit", required=True, type=Path)
    parser.add_argument("--source-t13s11-audit", required=True, type=Path)
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
