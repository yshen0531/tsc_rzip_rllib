#!/usr/bin/env python3
"""Frozen T13S11 causal calibration-conditioned braking preflight."""

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


STAGE = "Stage4.2R3c3T13S11"
PASS_ROUTE = (
    "CAUSAL_CALIBRATION_CONDITIONED_BRAKING_PREFLIGHT_"
    "CANDIDATE_DUAL_WINDOW_TSC_REQUIRED"
)
FAIL_ROUTE = (
    "CAUSAL_CALIBRATION_CONDITIONED_BRAKING_PREFLIGHT_"
    "INSUFFICIENT_PERSISTENT_OBSERVER_REDESIGN"
)
DESIGN_SHA256 = (
    "0289c514511afe8aeaa3d7db0c2ccb506c97728ba37477d31deb803cfa393e8d"
)
SOURCE_T13S10_SHA256 = (
    "f24768f7b4899c73f68fd0a4e3991f524239951883abf3d2809461b5ab82509b"
)
CALIBRATION_DIRECTION = "mode0_coil8_component"
CALIBRATION_SIGN = 1
SIGNATURE_NAMES = (
    "calibration_delta_R",
    "calibration_delta_Z",
    "calibration_delta_vR",
    "calibration_delta_vZ",
    "calibration_delta_Ip",
    "calibration_measured_coil8_current_delta",
    "normalized_delay",
    "normalized_slew",
)


def _projection_residual(value: np.ndarray, basis: np.ndarray) -> float:
    value = np.asarray(value, dtype=float)
    basis = np.asarray(basis, dtype=float)
    projection = (value @ basis.T) @ basis
    return float(
        np.linalg.norm(value - projection) / max(np.linalg.norm(value), 1e-300)
    )


def _interaction_row(current_coordinates: np.ndarray, state: np.ndarray) -> np.ndarray:
    current_coordinates = np.asarray(current_coordinates, dtype=float)
    state = np.asarray(state, dtype=float)
    if current_coordinates.shape != (4,) or state.shape != (2,):
        raise ValueError("T13S11 interaction coordinate shape mismatch")
    return np.kron(np.asarray([1.0, state[0], state[1]]), current_coordinates)


def _raw_groups(
    raw: Sequence[Mapping[str, Any]],
) -> dict[tuple[Any, ...], dict[Any, Mapping[str, Any]]]:
    groups: dict[tuple[Any, ...], dict[Any, Mapping[str, Any]]] = defaultdict(dict)
    for result in raw:
        spec = result["spec"]
        key = s7._raw_context_key("s5", spec)
        identity = s7._probe_identity("s5", spec)
        member = "baseline" if identity is None else identity
        if member in groups[key]:
            raise ValueError("T13S11 duplicate raw context member")
        groups[key][member] = result
    if len(groups) != 4 or any(len(members) != 17 for members in groups.values()):
        raise ValueError("T13S11 raw context coverage mismatch")
    return groups


def _feature_digest(
    baseline: Mapping[str, Any],
    members: Mapping[Any, Mapping[str, Any]],
    payload: Mapping[str, Any],
) -> str:
    features = {}
    for window in common.WINDOWS:
        exemplar = members[(window, common.DIRECTIONS[0], -1)]
        issue, _ = s7._issue_cancel("s5", exemplar)
        feature, _ = s7.causal_feature(
            baseline,
            issue_step=issue,
            current_scales=s7._current_scales(payload),
            dt_s=0.01,
        )
        features[window] = feature.tolist()
    return common._canonical_digest(features)


def _calibration_signature(
    baseline: Mapping[str, Any],
    calibration: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    issue, cancel = s7._issue_cancel("s5", calibration)
    delay = int(calibration["spec"]["action_delay_steps"])
    slew = float(calibration["spec"]["slew_scale"])
    expected_issue = 2 if delay == 0 else 0
    expected_cancel = expected_issue + 1
    first = issue + 1
    if (issue, cancel) != (expected_issue, expected_cancel):
        raise ValueError("T13S11 calibration schedule mismatch")
    feature = common._feature_arrays(calibration, 0.01)
    visible_delta = feature[first] - feature[issue]
    current = np.asarray(
        [row["currents_a_tsc"] for row in calibration["trajectory"]], dtype=float
    )
    current_delta = current[first] - current[issue]
    half_range = s7._current_scales(payload)
    signature = np.asarray(
        [
            visible_delta[0] / 0.03,
            visible_delta[1] / 0.03,
            visible_delta[2] / 0.1,
            visible_delta[3] / 0.1,
            visible_delta[4] / 2000.0,
            current_delta[8] / half_range[8],
            delay / 2.0,
            (slew - 1.0) / 0.1,
        ],
        dtype=float,
    )
    _, _, pre_effect = s7._effect_response(
        calibration,
        baseline,
        issue=issue,
        cancel=cancel,
        dt_s=0.01,
        radius_a=s7._readback_radius_a(payload),
        first_effect_state=first,
        cancel_effect_state=cancel + 1,
        single_transition=True,
    )
    current_nonzero = bool(
        abs(current_delta[8])
        > float(s7._readback_radius_a(payload)[8]) + 1e-15
    )
    visible_floor = np.asarray([1e-9, 1e-9, 1e-7, 1e-7, 1e-4])
    visible_nonzero = bool(np.any(np.abs(visible_delta) > visible_floor))
    finite = bool(np.all(np.isfinite(signature)))
    return {
        "values": signature,
        "issue_step": issue,
        "first_effect_state": first,
        "cancel_effect_state": cancel + 1,
        "finite": finite,
        "measured_current_nonzero": current_nonzero,
        "visible_response_nonzero": visible_nonzero,
        "pre_effect_causality_pass": pre_effect,
        "passed": bool(finite and current_nonzero and visible_nonzero and pre_effect),
    }


def _signature_by_digest(
    raw: Sequence[Mapping[str, Any]],
    payloads: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    output = {}
    for members in _raw_groups(raw).values():
        baseline = members["baseline"]
        payload = payloads[str(baseline["experiment_id"])]
        digest = _feature_digest(baseline, members, payload)
        if digest in output:
            raise ValueError("T13S11 duplicate calibration feature digest")
        calibration = members[
            ("transport", CALIBRATION_DIRECTION, CALIBRATION_SIGN)
        ]
        output[digest] = _calibration_signature(baseline, calibration, payload)
    return output


def _fit_fold(
    held: Mapping[str, Any],
    training: Sequence[Mapping[str, Any]],
    cfg: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if len(training) != 3:
        raise ValueError("T13S11 fold requires three training contexts")
    z_train = np.asarray([row["calibration_signature"] for row in training])
    z_mean = np.mean(z_train, axis=0)
    z_centered = z_train - z_mean
    z_rank = int(np.linalg.matrix_rank(z_centered))
    _, _, z_vt = np.linalg.svd(z_centered, full_matrices=False)
    z_basis = z_vt[:2]
    z_scores = {
        row["context_id"]: (row["calibration_signature"] - z_mean) @ z_basis.T
        for row in training
    }
    held_centered = held["calibration_signature"] - z_mean
    held_state_support_residual = _projection_residual(held_centered, z_basis)
    held_state_support = held_state_support_residual <= 0.15
    held_state = held_centered @ z_basis.T

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
    design = np.asarray(
        [
            _interaction_row(
                sample["signed"][sign]["input"] @ current_basis.T,
                z_scores[context["context_id"]],
            )
            for context, sample, sign in train_samples
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
    design_pass = bool(
        z_rank == 2
        and current_rank >= 4
        and design_rank == 12
        and condition_json is not None
        and condition_json <= 30.0
        and signal_pass
    )
    tube_pass = bool(np.all(radius <= caps))
    scales = np.asarray(cfg["response_scales"], dtype=float)
    rows = []
    for sample in held["samples"]["braking"]:
        for sign in common.SIGNS:
            model_input = np.asarray(sample["signed"][sign]["input"])
            current_support_residual = _projection_residual(
                model_input, current_basis
            )
            current_support = current_support_residual <= 0.15
            supported = bool(held_state_support and current_support)
            actual = np.asarray(sample["signed"][sign]["output"])
            if supported:
                phi = _interaction_row(model_input @ current_basis.T, held_state)
                predicted = phi @ jacobian
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
                    "calibration_state_support_residual": held_state_support_residual,
                    "calibration_state_support_pass": held_state_support,
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
        "calibration_signature_rank": z_rank,
        "calibration_signature_rank_pass": z_rank == 2,
        "braking_current_matrix_rank": current_rank,
        "braking_current_basis_rank_pass": current_rank >= 4,
        "interaction_design_rank": design_rank,
        "interaction_condition_number": condition_json,
        "interaction_signal_pass": signal_pass,
        "interaction_rank_condition_signal_pass": design_pass,
        "tube_pass": tube_pass,
        "tube_radius": radius.tolist(),
        "maximum_tube_to_cap_ratio": float(np.max(radius / caps)),
        "held_calibration_state_support_residual": held_state_support_residual,
        "held_calibration_state_support_pass": held_state_support,
    }
    return model, rows


def _collision_audit(
    contexts: Sequence[Mapping[str, Any]], models: Sequence[Mapping[str, Any]]
) -> dict[str, int]:
    radius_by_context = {
        row["held_context_id"]: np.asarray(row["tube_radius"])
        for row in models
        if "tube_radius" in row
    }
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for context in contexts:
        for sample in context["samples"]["braking"]:
            for sign in common.SIGNS:
                key = common._canonical_digest(
                    {
                        "signature": context["calibration_signature"].tolist(),
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
                left_radius = radius_by_context.get(left["context_id"])
                right_radius = radius_by_context.get(right["context_id"])
                if left_radius is None or right_radius is None:
                    continue
                if np.any(
                    np.abs(left["actual"] - right["actual"])
                    > left_radius + right_radius + 1e-15
                ):
                    disjoint += 1
    return {
        "exact_signature_input_collision_group_count": len(collisions),
        "disjoint_exact_causal_signature_input_alias_pair_count": disjoint,
    }


def run_audit(args: argparse.Namespace) -> dict[str, Any]:
    for path, expected, label in (
        (args.design, DESIGN_SHA256, "design"),
        (args.source_t13s10_audit, SOURCE_T13S10_SHA256, "T13S10 audit"),
        (args.source_q1_audit, s10.EXPECTED_Q1_AUDIT_SHA256, "q1 audit"),
        (args.source_q2_audit, s10.EXPECTED_Q2_AUDIT_SHA256, "q2 audit"),
        (args.q1_config, s10.EXPECTED_Q1_CONFIG_SHA256, "q1 config"),
        (args.q2_config, s10.EXPECTED_Q2_CONFIG_SHA256, "q2 config"),
    ):
        s10.authenticate_exact_file(path, expected, label)
    source_t13s10 = common._strict_json(args.source_t13s10_audit)
    if source_t13s10.get("route") != s10.FAIL_ROUTE or source_t13s10.get("passed"):
        raise ValueError("T13S11 source T13S10 result mismatch")
    q1_audit = common._strict_json(args.source_q1_audit)
    q2_audit = common._strict_json(args.source_q2_audit)
    q1_config = common._strict_json(args.q1_config)
    q2_config = common._strict_json(args.q2_config)
    if s10._probe_contract_without_schedule(
        q1_config
    ) != s10._probe_contract_without_schedule(q2_config):
        raise ValueError("T13S11 q1/q2 nonschedule contract mismatch")
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
        raise ValueError("T13S11 source authentication failed")

    q1_payloads = s10._payloads(args.q1_run, s10.Q1_VARIANT_DIR)
    q2_payloads = s10._payloads(args.q2_run, s10.Q2_VARIANT_DIR)
    q1_adapted = s10.adapt_q1_trace_contract(q1_raw)
    q1_contexts, q1_trace, q1_forbidden = s7.build_contexts(
        "s5", q1_adapted, q1_payloads, single_transition=True
    )
    q2_contexts, q2_trace, q2_forbidden = s7.build_contexts(
        "s5", q2_raw, q2_payloads, single_transition=True
    )
    q1_signatures = _signature_by_digest(q1_raw, q1_payloads)
    q2_signatures = _signature_by_digest(q2_raw, q2_payloads)
    for context in q1_contexts:
        context["campaign"] = "q1_t13s9"
        context["calibration"] = q1_signatures[context["feature_digest"]]
    for context in q2_contexts:
        context["campaign"] = "q2_t13s5"
        context["calibration"] = q2_signatures[context["feature_digest"]]
    contexts = q1_contexts + q2_contexts
    contexts.sort(key=lambda row: (row["stratum"], row["feature_digest"]))
    for index, context in enumerate(contexts):
        context["context_id"] = f"context_{index:02d}"
        context["calibration_signature"] = context["calibration"]["values"]

    cfg = q2_config["lattice_probe"]
    model_rows = []
    validation = []
    for stratum in ("easy", "hard"):
        stratum_contexts = [row for row in contexts if row["stratum"] == stratum]
        if len(stratum_contexts) != 4:
            raise ValueError("T13S11 stratum coverage mismatch")
        for held in stratum_contexts:
            model, rows = _fit_fold(
                held, [row for row in stratum_contexts if row is not held], cfg
            )
            model_rows.append(model)
            validation.extend(rows)
    collisions = _collision_audit(contexts, model_rows)
    feature_forbidden = len(s7.FORBIDDEN_FEATURE_NAMES.intersection(SIGNATURE_NAMES))
    forbidden_count = q1_forbidden + q2_forbidden + feature_forbidden
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
        "calibration_signature_count": len(contexts),
        "calibration_signature_pass_count": sum(
            context["calibration"]["passed"] for context in contexts
        ),
        "calibration_pre_effect_causality_pass_count": sum(
            context["calibration"]["pre_effect_causality_pass"]
            for context in contexts
        ),
        "signed_braking_extraction_count": len(validation),
        "signed_braking_extraction_expected": 64,
        "braking_pre_effect_causality_pass_count": sum(
            row["pre_effect_causality_pass"] for row in validation
        ),
        "fold_count": len(model_rows),
        "calibration_pca_rank_pass_count": sum(
            row["calibration_signature_rank_pass"] for row in model_rows
        ),
        "braking_current_basis_rank_pass_count": sum(
            row["braking_current_basis_rank_pass"] for row in model_rows
        ),
        "interaction_rank_condition_signal_pass_count": sum(
            row["interaction_rank_condition_signal_pass"] for row in model_rows
        ),
        "interaction_tube_pass_count": sum(row["tube_pass"] for row in model_rows),
        "maximum_finite_interaction_condition_number": s7.maximum_present(
            [row["interaction_condition_number"] for row in model_rows]
        ),
        "maximum_interaction_tube_to_cap_ratio": max(
            row["maximum_tube_to_cap_ratio"] for row in model_rows
        ),
        "held_calibration_state_support_pass_count": sum(
            row["held_calibration_state_support_pass"] for row in model_rows
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
        and summary["calibration_signature_count"]
        == summary["calibration_signature_pass_count"]
        == summary["calibration_pre_effect_causality_pass_count"]
        == 8
        and summary["signed_braking_extraction_count"]
        == summary["signed_braking_extraction_expected"]
        == summary["braking_pre_effect_causality_pass_count"]
        == 64
        and summary["fold_count"]
        == summary["calibration_pca_rank_pass_count"]
        == summary["braking_current_basis_rank_pass_count"]
        == summary["interaction_rank_condition_signal_pass_count"]
        == summary["interaction_tube_pass_count"]
        == summary["held_calibration_state_support_pass_count"]
        == 8
        and summary["held_braking_current_support_pass_count"]
        == summary["held_prediction_supported_count"]
        == summary["componentwise_containment_pass_count"]
        == summary["scaled_relative_error_pass_count"]
        == summary["both_response_gates_pass_count"]
        == 64
        and summary["disjoint_exact_causal_signature_input_alias_pair_count"] == 0
        and summary["forbidden_feature_or_trace_model_input_count"] == 0
    )
    return {
        "schema_version": 1,
        "stage": STAGE,
        "audit_revision": "causal_calibration_conditioned_braking_loco_v1",
        "preregistered_design": str(args.design),
        "preregistered_design_sha256": DESIGN_SHA256,
        "source_t13s10_audit": str(args.source_t13s10_audit),
        "source_t13s10_audit_sha256": SOURCE_T13S10_SHA256,
        "source_q1_run": str(args.q1_run),
        "source_q1_audit_sha256": s10.EXPECTED_Q1_AUDIT_SHA256,
        "source_q2_run": str(args.q2_run),
        "source_q2_audit_sha256": s10.EXPECTED_Q2_AUDIT_SHA256,
        "calibration_direction": CALIBRATION_DIRECTION,
        "calibration_sign": CALIBRATION_SIGN,
        "calibration_signature_schema": list(SIGNATURE_NAMES),
        "calibration_uses_absolute_same_trajectory_causal_delta": True,
        "calibration_uses_no_probe_counterfactual": False,
        "support_on_full_rank_interaction_coordinate_forbidden": True,
        "separate_nonvacuous_state_and_current_support": True,
        "source_raw_rewritten": False,
        "formal_timing_unchanged": True,
        "all_source_data_consumed_not_blind": True,
        "real_tsc_executed": False,
        "controller_optimizer_or_plant_step_executed": False,
        "summary": summary,
        "fold_models": model_rows,
        "validation_results": validation,
        "passed": passed,
        "route": PASS_ROUTE if passed else FAIL_ROUTE,
        "fresh_dual_window_tsc_required_before_controller": passed,
        "persistent_observer_redesign_required": not passed,
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
