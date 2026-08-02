#!/usr/bin/env python3
"""Read-only causal multi-history tube feasibility audit for T13S7."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s6_independent_raw_audit as common,
)


STAGE = "Stage4.2R3c3T13S7"
PASS_ROUTE = "FINITE_CAUSAL_MULTI_HYPOTHESIS_CANDIDATE_Q3_HOLDOUT_REQUIRED"
FAIL_ROUTE = "CAUSAL_MULTI_HYPOTHESIS_TUBE_INSUFFICIENT_REDESIGN"
S1_STAGE = "Stage4.2R3c3T13S1"
S5_STAGE = "Stage4.2R3c3T13S5"
S1_BASELINE = "single_step_baseline"
S5_BASELINE = "lattice_baseline"
S1_DIRECTIONS = ("mode0", "mode1", "mode2")
S5_DIRECTIONS = common.DIRECTIONS
WINDOWS = common.WINDOWS
SIGNS = common.SIGNS
EXPECTED_S1_DIGEST = "de2be508888aa503628538a795474fbf70788252e7913f87af7603c5bc034603"
EXPECTED_S5_DIGEST = "09ee846d2fd8c2a516ec01f1b91bcbf8f303885c2377373000ab85dfc45e0f01"
FORBIDDEN_FEATURE_NAMES = frozenset(
    {
        "pair_id",
        "history_member",
        "prefix",
        "q1_or_q2",
        "source_experiment_id",
        "baseline_experiment_id",
        "wire_currents_a",
        "vessel_current_total_a",
        "source_action",
        "source_result",
        "future_action",
        "future_measurement",
        "future_probe_schedule",
    }
)


def _inventory(raw_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    paths = sorted(raw_dir.glob("*.json.gz"))
    rows = [
        {"path": path.name, "size_bytes": path.stat().st_size, "sha256": common._sha256(path)}
        for path in paths
    ]
    return rows, [common._strict_json_gz(path) for path in paths], common._canonical_digest(rows)


def _audit_digest(audit: Mapping[str, Any]) -> str | None:
    inventory = audit.get("raw_inventory") or {}
    if isinstance(inventory, Mapping):
        return inventory.get("digest") or inventory.get("raw_inventory_digest")
    return None


def _audit_certified(audit: Mapping[str, Any], expected_digest: str) -> bool:
    return bool(
        audit.get("certified_scientific_result")
        and _audit_digest(audit) == expected_digest
        and (
            audit.get("control_raw_identity_exact", True)
            or audit.get("raw_and_manifest_integrity_passed", False)
        )
    )


def _raw_context_key(campaign: str, spec: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        campaign,
        str(spec["restart_snapshot_manifest_digest"]),
        str(spec["target_id"]),
        int(spec["action_delay_steps"]),
        float(spec["slew_scale"]),
    )


def _probe_identity(
    campaign: str, spec: Mapping[str, Any]
) -> tuple[str, str, int] | None:
    probe_id = str(spec["r3c3_probe_id"])
    baseline_id = S1_BASELINE if campaign == "s1" else S5_BASELINE
    if probe_id == baseline_id:
        return None
    window = str(spec["r3c3_probe_window"])
    if campaign == "s1":
        direction = f"mode{int(spec['r3c3_probe_mode'])}"
    else:
        direction = str(spec["r3c3_probe_direction"])
    return window, direction, int(spec["r3c3_probe_sign"])


def _issue_cancel(campaign: str, result: Mapping[str, Any]) -> tuple[int, int]:
    spec = result["spec"]
    if campaign == "s1":
        steps = sorted(int(step) for step in spec["r3c3_probe_delta_by_task_issue_step"])
        if len(steps) != 2:
            raise ValueError("S1 issued schedule must contain two adjacent task steps")
        issue, cancel = steps
    else:
        issue = int(spec["r3c3_probe_issue_step"])
        cancel = int(spec["r3c3_probe_cancel_step"])
    if cancel != issue + 1:
        raise ValueError("probe issue/cancel steps are not adjacent")
    return issue, cancel


def _trace_exact(campaign: str, result: Mapping[str, Any], baseline: bool) -> bool:
    trace = result["controller_trace"]
    if campaign == "s1":
        issued = [row for row in trace if row.get("r3c3_probe_issued")]
        return len(issued) == (0 if baseline else 2)
    events = [
        row.get("r3c3t13s5_lattice_event")
        for row in trace
        if row.get("r3c3t13s5_lattice_event") != "none"
    ]
    return events == ([] if baseline else ["issue", "cancel"])


def _raw_forbidden_count(result: Mapping[str, Any]) -> int:
    return sum(
        any(bool(row.get(key)) for key in common.FORBIDDEN_TRACE_KEYS)
        for row in result["controller_trace"]
    )


def _payload_dir(campaign: str, run_dir: Path) -> Path:
    return run_dir / f"stage4_2r3c3t13{campaign}_environment_variants"


def _payload_by_experiment(campaign: str, run_dir: Path) -> dict[str, Mapping[str, Any]]:
    paths = sorted(_payload_dir(campaign, run_dir).glob("payload_*.json"))
    expected = 52 if campaign == "s1" else 68
    if len(paths) != expected:
        raise ValueError(f"{campaign} payload inventory mismatch")
    return {
        path.stem.removeprefix("payload_"): common._strict_json(path) for path in paths
    }


def _current_scales(payload: Mapping[str, Any]) -> np.ndarray:
    env = payload["env_cfg"]
    minimum_display = np.asarray(env["min_current_a_display_order"], dtype=float)
    maximum_display = np.asarray(env["max_current_a_display_order"], dtype=float)
    index = np.asarray(common.DISPLAY_TO_TSC_INDEX)
    half_range = 0.5 * (maximum_display[index] - minimum_display[index])
    if half_range.shape != (14,) or np.any(half_range <= 0.0):
        raise ValueError("invalid declared current half ranges")
    return half_range


def _readback_radius_a(payload: Mapping[str, Any]) -> np.ndarray:
    turns_display = np.asarray(payload["env_cfg"]["turns_display_order"], dtype=float)
    turns_tsc = turns_display[np.asarray(common.DISPLAY_TO_TSC_INDEX)]
    if turns_tsc.shape != (14,) or np.any(turns_tsc <= 0.0):
        raise ValueError("invalid TSC-order turns for readback radius")
    return 0.001 / turns_tsc


def causal_feature(
    baseline: Mapping[str, Any],
    *,
    issue_step: int,
    current_scales: np.ndarray,
    dt_s: float,
) -> tuple[np.ndarray, tuple[str, ...]]:
    trajectory = baseline["trajectory"]
    if issue_step < 0 or issue_step >= len(trajectory):
        raise ValueError("issue step outside baseline trajectory")
    current = trajectory[issue_step]
    currents = np.asarray(current["currents_a_tsc"], dtype=float)
    history_known = float(issue_step > 0)
    if issue_step > 0:
        previous = trajectory[issue_step - 1]
        velocity = np.asarray(
            [
                (float(current["R"]) - float(previous["R"])) / dt_s,
                (float(current["Z"]) - float(previous["Z"])) / dt_s,
            ]
        )
        current_delta = currents - np.asarray(previous["currents_a_tsc"], dtype=float)
    else:
        velocity = np.zeros(2)
        current_delta = np.zeros(14)
    spec = baseline["spec"]
    formal_horizon = int(spec["formal_horizon_steps"])
    names = (
        "R",
        "Z",
        "Ip",
        "vR",
        "vZ",
        "velocity_known",
        *(f"coil_current_{i}" for i in range(14)),
        *(f"coil_current_delta_{i}" for i in range(14)),
        "coil_history_known",
        "target_R_offset",
        "target_Z_offset",
        "target_Ip_offset",
        "formal_issue_fraction",
        "normalized_delay",
        "normalized_slew",
    )
    values = np.asarray(
        [
            float(current["R"]) / 0.03,
            float(current["Z"]) / 0.03,
            float(current["Ip"]) / 10000.0,
            velocity[0] / 0.1,
            velocity[1] / 0.1,
            history_known,
            *(currents / current_scales),
            *(current_delta / current_scales),
            history_known,
            float(spec["target_R_offset_m"]) / 0.03,
            float(spec["target_Z_offset_m"]) / 0.03,
            float(spec["target_Ip_offset_A"]) / 10000.0,
            issue_step / formal_horizon,
            int(spec["action_delay_steps"]) / 2.0,
            (float(spec["slew_scale"]) - 1.0) / 0.1,
        ],
        dtype=float,
    )
    if len(names) != len(values) or not np.all(np.isfinite(values)):
        raise ValueError("invalid causal feature")
    if FORBIDDEN_FEATURE_NAMES.intersection(names):
        raise ValueError("forbidden name entered causal feature")
    return values, names


def _effect_response(
    result: Mapping[str, Any],
    baseline: Mapping[str, Any],
    *,
    issue: int,
    cancel: int,
    dt_s: float,
    radius_a: np.ndarray,
    first_effect_state: int | None = None,
    cancel_effect_state: int | None = None,
) -> tuple[np.ndarray, np.ndarray, bool]:
    first = issue + 1 if first_effect_state is None else int(first_effect_state)
    second = cancel + 1 if cancel_effect_state is None else int(cancel_effect_state)
    if second != first + 1:
        raise ValueError("physical effect states are not adjacent")
    feature = common._feature_arrays(result, dt_s)
    base_feature = common._feature_arrays(baseline, dt_s)
    currents = np.asarray([row["currents_a_tsc"] for row in result["trajectory"]])
    base_currents = np.asarray([row["currents_a_tsc"] for row in baseline["trajectory"]])
    x = (currents[[first, second]] - base_currents[[first, second]]).reshape(-1)
    y = np.concatenate(
        (feature[first] - base_feature[first], feature[second] - base_feature[second])
    )
    pre_feature = feature[:first] - base_feature[:first]
    pre_currents = currents[:first] - base_currents[:first]
    pre_pass = bool(
        (len(pre_feature) == 0 or np.max(np.abs(pre_feature[:, :2])) <= 1e-9)
        and (len(pre_feature) == 0 or np.max(np.abs(pre_feature[:, 2:4])) <= 1e-7)
        and (len(pre_feature) == 0 or np.max(np.abs(pre_feature[:, 4])) <= 1e-4)
        and (
            len(pre_currents) == 0
            or np.max(np.abs(pre_currents) / radius_a[None, :]) <= 1.0 + 1e-12
        )
    )
    return x, y, pre_pass


def build_contexts(
    campaign: str,
    raw: Sequence[Mapping[str, Any]],
    payloads: Mapping[str, Mapping[str, Any]],
    campaign_specific_effects: bool = False,
) -> tuple[list[dict[str, Any]], int, int]:
    grouped: dict[tuple[Any, ...], dict[Any, Mapping[str, Any]]] = defaultdict(dict)
    trace_count = 0
    forbidden_count = 0
    for result in raw:
        spec = result["spec"]
        key = _raw_context_key(campaign, spec)
        identity = _probe_identity(campaign, spec)
        member = "baseline" if identity is None else identity
        if member in grouped[key]:
            raise ValueError("duplicate campaign context member")
        grouped[key][member] = result
        trace_count += int(_trace_exact(campaign, result, identity is None))
        forbidden_count += _raw_forbidden_count(result)
    expected_contexts = 4
    expected_members = 13 if campaign == "s1" else 17
    if len(grouped) != expected_contexts or any(
        len(members) != expected_members for members in grouped.values()
    ):
        raise ValueError("campaign context coverage mismatch")

    contexts = []
    for members in grouped.values():
        baseline = members["baseline"]
        spec = baseline["spec"]
        campaign_directions = S1_DIRECTIONS if campaign == "s1" else S5_DIRECTIONS
        samples_by_window: dict[str, list[dict[str, Any]]] = defaultdict(list)
        features = {}
        for window in WINDOWS:
            exemplar = members[(window, campaign_directions[0], -1)]
            issue, cancel = _issue_cancel(campaign, exemplar)
            if campaign_specific_effects and campaign == "s1":
                first_effect_state = int(
                    exemplar["spec"]["r3c3_probe_first_effect_state"]
                )
                cancel_effect_state = int(
                    exemplar["spec"]["r3c3_probe_cancel_effect_state"]
                )
                if first_effect_state != issue + int(spec["action_delay_steps"]) + 1:
                    raise ValueError("S1 queue-aware effect contract mismatch")
            else:
                first_effect_state = issue + 1
                cancel_effect_state = cancel + 1
            payload = payloads[str(baseline["experiment_id"])]
            feature, names = causal_feature(
                baseline,
                issue_step=issue,
                current_scales=_current_scales(payload),
                dt_s=0.01,
            )
            features[window] = {"values": feature, "names": names}
            for direction in campaign_directions:
                signed = {}
                pre_pass = True
                for sign in SIGNS:
                    result = members[(window, direction, sign)]
                    actual_issue, actual_cancel = _issue_cancel(campaign, result)
                    if (actual_issue, actual_cancel) != (issue, cancel):
                        raise ValueError("context/window schedule mismatch")
                    x, y, causal = _effect_response(
                        result,
                        baseline,
                        issue=issue,
                        cancel=cancel,
                        dt_s=0.01,
                        radius_a=_readback_radius_a(payload),
                        first_effect_state=first_effect_state,
                        cancel_effect_state=cancel_effect_state,
                    )
                    signed[sign] = {"input": x, "output": y}
                    pre_pass = pre_pass and causal
                samples_by_window[window].append(
                    {
                        "direction": direction,
                        "signed": signed,
                        "odd_input": (signed[1]["input"] - signed[-1]["input"]) / 2.0,
                        "odd_output": (signed[1]["output"] - signed[-1]["output"]) / 2.0,
                        "pre_effect_causality_pass": pre_pass,
                    }
                )
        feature_digest = common._canonical_digest(
            {window: features[window]["values"].tolist() for window in WINDOWS}
        )
        contexts.append(
            {
                "campaign": campaign,
                "stratum": "easy" if int(spec["action_delay_steps"]) == 0 else "hard",
                "feature_digest": feature_digest,
                "features": features,
                "samples": samples_by_window,
            }
        )
    contexts.sort(key=lambda row: (row["stratum"], row["feature_digest"]))
    for index, context in enumerate(contexts):
        context["context_id"] = f"context_{index:02d}"
    return contexts, trace_count, forbidden_count


def fit_local_model(
    context: Mapping[str, Any], window: str, cfg: Mapping[str, Any]
) -> dict[str, Any]:
    samples = context["samples"][window]
    x = np.asarray([row["odd_input"] for row in samples])
    y = np.asarray([row["odd_output"] for row in samples])
    rank = int(np.linalg.matrix_rank(x))
    jacobian = np.linalg.lstsq(x, y, rcond=None)[0]
    residuals = np.asarray(
        [
            row["signed"][sign]["output"]
            - row["signed"][sign]["input"] @ jacobian
            for row in samples
            for sign in SIGNS
        ]
    )
    floor = np.tile(np.asarray([1e-9, 1e-9, 1e-7, 1e-7, 1e-4]), 2)
    caps = np.asarray(cfg["tube_caps_unscaled"], dtype=float)
    radius = floor + float(cfg["tube_residual_multiplier"]) * np.max(
        np.abs(residuals), axis=0
    )
    _, _, vt = np.linalg.svd(x, full_matrices=False)
    row_basis = vt[:rank]
    expected_rank = 3 if context["campaign"] == "s1" else 4
    return {
        "context_id": context["context_id"],
        "campaign": context["campaign"],
        "stratum": context["stratum"],
        "window": window,
        "rank": rank,
        "expected_rank": expected_rank,
        "rank_pass": rank == expected_rank,
        "jacobian": jacobian,
        "row_basis": row_basis,
        "radius": radius,
        "tube_pass": bool(np.all(radius <= caps)),
        "maximum_tube_to_cap_ratio": float(np.max(radius / caps)),
    }


def input_support(model: Mapping[str, Any], value: np.ndarray) -> tuple[float, bool]:
    basis = np.asarray(model["row_basis"])
    projection = (value @ basis.T) @ basis
    relative = float(
        np.linalg.norm(value - projection) / max(np.linalg.norm(value), 1e-300)
    )
    return relative, relative <= 0.15


def _feature_distance(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.linalg.norm(left - right) / math.sqrt(len(left)))


def nearest_contexts(
    held: Mapping[str, Any],
    training: Sequence[Mapping[str, Any]],
    *,
    window: str,
) -> list[tuple[float, Mapping[str, Any]]]:
    held_feature = held["features"][window]["values"]
    distances = sorted(
        (
            _feature_distance(held_feature, context["features"][window]["values"]),
            context["feature_digest"],
            context,
        )
        for context in training
    )
    cutoff = distances[min(1, len(distances) - 1)][0]
    return [(distance, context) for distance, _, context in distances if distance <= cutoff + 1e-15]


def _scaled_relative(actual: np.ndarray, predicted: np.ndarray, scales: np.ndarray) -> float:
    floor = float(
        np.linalg.norm(
            np.tile(
                np.asarray([1e-9, 1e-9, 1e-7, 1e-7, 1e-4])
                / scales[:5],
                2,
            )
        )
    )
    return float(
        np.linalg.norm((actual - predicted) / scales)
        / max(np.linalg.norm(actual / scales), floor)
    )


def validate_leave_one_out(
    contexts: Sequence[Mapping[str, Any]],
    models: Mapping[tuple[str, str], Mapping[str, Any]],
    cfg: Mapping[str, Any],
) -> list[dict[str, Any]]:
    scales = np.tile(np.asarray(cfg["response_scales"], dtype=float), 2)
    rows = []
    for stratum in ("easy", "hard"):
        stratum_contexts = [row for row in contexts if row["stratum"] == stratum]
        if len(stratum_contexts) != 4:
            raise ValueError("leave-one-out stratum must contain four contexts")
        for held in stratum_contexts:
            training = [row for row in stratum_contexts if row is not held]
            for window in WINDOWS:
                selected = nearest_contexts(held, training, window=window)
                for sample in held["samples"][window]:
                    for sign in SIGNS:
                        model_input = sample["signed"][sign]["input"]
                        actual = sample["signed"][sign]["output"]
                        hypotheses = []
                        for distance, context in selected:
                            model = models[(context["context_id"], window)]
                            projection_residual, supported = input_support(model, model_input)
                            if not supported:
                                continue
                            predicted = model_input @ model["jacobian"]
                            relative = _scaled_relative(actual, predicted, scales)
                            contained = bool(
                                np.all(np.abs(actual - predicted) <= model["radius"] + 1e-15)
                            )
                            hypotheses.append(
                                {
                                    "source_context_id": context["context_id"],
                                    "feature_distance": distance,
                                    "input_projection_residual": projection_residual,
                                    "contained": contained,
                                    "scaled_relative_error": relative,
                                }
                            )
                        supported = bool(hypotheses)
                        containment = supported and any(row["contained"] for row in hypotheses)
                        best_relative = (
                            min(row["scaled_relative_error"] for row in hypotheses)
                            if supported
                            else None
                        )
                        relative_pass = bool(
                            best_relative is not None
                            and best_relative
                            <= float(cfg["maximum_holdout_scaled_center_relative_error"])
                        )
                        rows.append(
                            {
                                "held_context_id": held["context_id"],
                                "held_campaign": held["campaign"],
                                "stratum": stratum,
                                "probe_window": window,
                                "probe_direction": sample["direction"],
                                "probe_sign": sign,
                                "selected_context_count": len(selected),
                                "supported_hypothesis_count": len(hypotheses),
                                "supported_hypothesis_pass": supported,
                                "componentwise_containment_pass": containment,
                                "nearest_scaled_relative_error": best_relative,
                                "scaled_relative_error_pass": relative_pass,
                                "pre_effect_causality_pass": sample[
                                    "pre_effect_causality_pass"
                                ],
                                "passed": bool(
                                    supported
                                    and containment
                                    and relative_pass
                                    and sample["pre_effect_causality_pass"]
                                ),
                                "hypotheses": hypotheses,
                            }
                        )
    return rows


def exact_collision_audit(
    contexts: Sequence[Mapping[str, Any]],
    models: Mapping[tuple[str, str], Mapping[str, Any]],
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for context in contexts:
        for window in WINDOWS:
            feature = context["features"][window]["values"]
            for sample in context["samples"][window]:
                for sign in SIGNS:
                    model_input = sample["signed"][sign]["input"]
                    key = common._canonical_digest(
                        {"feature": feature.tolist(), "input": model_input.tolist()}
                    )
                    grouped[key].append(
                        {
                            "context_id": context["context_id"],
                            "window": window,
                            "actual": sample["signed"][sign]["output"],
                            "radius": models[(context["context_id"], window)]["radius"],
                        }
                    )
    collision_groups = [rows for rows in grouped.values() if len(rows) > 1]
    disjoint = 0
    for rows in collision_groups:
        for left_index, left in enumerate(rows):
            for right in rows[left_index + 1 :]:
                if np.any(
                    np.abs(left["actual"] - right["actual"])
                    > left["radius"] + right["radius"] + 1e-15
                ):
                    disjoint += 1
    return {
        "exact_feature_input_collision_group_count": len(collision_groups),
        "disjoint_exact_causal_alias_pair_count": disjoint,
    }


def maximum_present(values: Sequence[float | None]) -> float | None:
    """Return the finite maximum, or JSON null when no prediction was supported."""
    present = [float(value) for value in values if value is not None]
    return max(present) if present else None


def run_audit(
    args: argparse.Namespace, *, campaign_specific_effects: bool = False
) -> dict[str, Any]:
    s1_audit = common._strict_json(args.source_s1_audit)
    s5_audit = common._strict_json(args.source_s5_audit)
    s1_config = common._strict_json(args.s1_config)
    s5_config = common._strict_json(args.s5_config)
    s1_raw_dir = args.s1_run / "stage4_2r3c3t13s1_minimal_transition_sentinel" / "raw"
    s5_raw_dir = args.s5_run / "stage4_2r3c3t13s5_lattice_native_split_holdout" / "raw"
    s1_inventory, s1_raw, s1_digest = _inventory(s1_raw_dir)
    s5_inventory, s5_raw, s5_digest = _inventory(s5_raw_dir)
    if not (
        len(s1_raw) == 52
        and len(s5_raw) == 68
        and s1_digest == EXPECTED_S1_DIGEST
        and s5_digest == EXPECTED_S5_DIGEST
        and _audit_certified(s1_audit, s1_digest)
        and _audit_certified(s5_audit, s5_digest)
    ):
        raise ValueError("T13S7 source authentication failed")
    if not all(
        result.get("success")
        and result.get("completed")
        and result.get("stage") == expected_stage
        for rows, expected_stage in ((s1_raw, S1_STAGE), (s5_raw, S5_STAGE))
        for result in rows
    ):
        raise ValueError("T13S7 raw success/stage mismatch")

    s1_contexts, s1_trace, s1_forbidden = build_contexts(
        "s1",
        s1_raw,
        _payload_by_experiment("s1", args.s1_run),
        campaign_specific_effects=campaign_specific_effects,
    )
    s5_contexts, s5_trace, s5_forbidden = build_contexts(
        "s5",
        s5_raw,
        _payload_by_experiment("s5", args.s5_run),
        campaign_specific_effects=campaign_specific_effects,
    )
    contexts = s1_contexts + s5_contexts
    contexts.sort(key=lambda row: (row["stratum"], row["feature_digest"]))
    for index, context in enumerate(contexts):
        context["context_id"] = f"context_{index:02d}"
    probe_cfg = s5_config["lattice_probe"]
    models = {
        (context["context_id"], window): fit_local_model(context, window, probe_cfg)
        for context in contexts
        for window in WINDOWS
    }
    validation = validate_leave_one_out(contexts, models, probe_cfg)
    collisions = exact_collision_audit(contexts, models)
    forbidden_count = s1_forbidden + s5_forbidden
    feature_names = contexts[0]["features"]["transport"]["names"]
    if any(context["features"][window]["names"] != feature_names for context in contexts for window in WINDOWS):
        raise ValueError("causal feature schema mismatch")
    feature_forbidden = len(FORBIDDEN_FEATURE_NAMES.intersection(feature_names))
    model_rows = [
        {
            "context_id": model["context_id"],
            "campaign": model["campaign"],
            "stratum": model["stratum"],
            "probe_window": model["window"],
            "rank": model["rank"],
            "expected_rank": model["expected_rank"],
            "rank_pass": model["rank_pass"],
            "tube_pass": model["tube_pass"],
            "maximum_tube_to_cap_ratio": model["maximum_tube_to_cap_ratio"],
        }
        for model in models.values()
    ]
    summary = {
        "s1_raw_count": len(s1_inventory),
        "s1_raw_bytes": sum(row["size_bytes"] for row in s1_inventory),
        "s1_raw_digest": s1_digest,
        "s1_source_audit_certified": True,
        "s5_raw_count": len(s5_inventory),
        "s5_raw_bytes": sum(row["size_bytes"] for row in s5_inventory),
        "s5_raw_digest": s5_digest,
        "s5_source_audit_certified": True,
        "combined_raw_count": len(s1_inventory) + len(s5_inventory),
        "combined_context_count": len(contexts),
        "combined_baseline_count": len(contexts),
        "combined_signed_probe_count": len(s1_raw) + len(s5_raw) - len(contexts),
        "trace_identity_pass_count": s1_trace + s5_trace,
        "trace_identity_expected": 120,
        "corrected_signed_extraction_count": len(validation),
        "corrected_signed_extraction_expected": 112,
        "pre_effect_causality_pass_count": sum(row["pre_effect_causality_pass"] for row in validation),
        "local_model_count": len(model_rows),
        "local_rank_pass_count": sum(row["rank_pass"] for row in model_rows),
        "local_tube_pass_count": sum(row["tube_pass"] for row in model_rows),
        "maximum_local_tube_to_cap_ratio": max(row["maximum_tube_to_cap_ratio"] for row in model_rows),
        "leave_one_context_out_fold_count": len(contexts),
        "heldout_prediction_count": len(validation),
        "supported_hypothesis_pass_count": sum(row["supported_hypothesis_pass"] for row in validation),
        "componentwise_containment_pass_count": sum(row["componentwise_containment_pass"] for row in validation),
        "scaled_relative_error_pass_count": sum(row["scaled_relative_error_pass"] for row in validation),
        "maximum_finite_scaled_relative_error": maximum_present(
            [row["nearest_scaled_relative_error"] for row in validation]
        ),
        "forbidden_feature_or_trace_input_count": forbidden_count + feature_forbidden,
        **collisions,
    }
    passed = bool(
        summary["s1_raw_count"] == 52
        and summary["s5_raw_count"] == 68
        and summary["combined_raw_count"] == 120
        and summary["combined_context_count"] == summary["combined_baseline_count"] == 8
        and summary["combined_signed_probe_count"] == 112
        and summary["trace_identity_pass_count"] == summary["trace_identity_expected"] == 120
        and summary["corrected_signed_extraction_count"] == summary["corrected_signed_extraction_expected"] == 112
        and summary["pre_effect_causality_pass_count"] == 112
        and summary["local_model_count"] == summary["local_rank_pass_count"] == summary["local_tube_pass_count"] == 16
        and summary["leave_one_context_out_fold_count"] == 8
        and summary["heldout_prediction_count"]
        == summary["supported_hypothesis_pass_count"]
        == summary["componentwise_containment_pass_count"]
        == summary["scaled_relative_error_pass_count"]
        == 112
        and summary["disjoint_exact_causal_alias_pair_count"] == 0
        and summary["forbidden_feature_or_trace_input_count"] == 0
    )
    return {
        "schema_version": 1,
        "stage": STAGE,
        "audit_revision": "causal_visible_state_multi_history_loco_v1",
        "source_s1_run": str(args.s1_run),
        "source_s1_audit": str(args.source_s1_audit),
        "source_s1_audit_sha256": common._sha256(args.source_s1_audit),
        "source_s5_run": str(args.s5_run),
        "source_s5_audit": str(args.source_s5_audit),
        "source_s5_audit_sha256": common._sha256(args.source_s5_audit),
        "formal_timing_unchanged": True,
        "all_source_data_consumed_not_blind": True,
        "real_tsc_executed": False,
        "controller_or_plant_step_executed": False,
        "feature_schema": list(feature_names),
        "feature_uses_pair_history_prefix_source_wire_or_future": False,
        "summary": summary,
        "local_models": model_rows,
        "validation_results": validation,
        "passed": passed,
        "route": PASS_ROUTE if passed else FAIL_ROUTE,
        "new_q3_holdout_required_before_controller": True,
        "real_mpc_authorized": False,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "bc_dagger_or_rl_allowed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--s1-run", required=True, type=Path)
    parser.add_argument("--source-s1-audit", required=True, type=Path)
    parser.add_argument("--s5-run", required=True, type=Path)
    parser.add_argument("--source-s5-audit", required=True, type=Path)
    parser.add_argument("--s1-config", required=True, type=Path)
    parser.add_argument("--s5-config", required=True, type=Path)
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
