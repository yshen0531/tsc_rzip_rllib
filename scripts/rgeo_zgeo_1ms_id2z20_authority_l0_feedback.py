#!/usr/bin/env python3
"""Run the frozen ID-2Z20 finite Authority-L0 feedback discriminator."""

from __future__ import annotations

import argparse
from decimal import Decimal
import json
import math
from pathlib import Path
import sys
import time
from typing import Any, Callable, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_id2z18_full_horizon_token_development as z18  # noqa: E402
from scripts import rgeo_zgeo_1ms_id0_vector_tail as base  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_contract import RGeoZGeoSignal  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    Card15Target,
    OneMsNR1SafetyEnvelope,
    assert_exact_slew,
    card15_target_decimal_a,
)
from tsc_rzip_rllib.core.inputa import format_number  # noqa: E402


z6, io = z18.z6, z18.io
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z20_authority_l0_feedback.json"
CONFIG_SHA256 = "a3d4d17f453184d5559f0b55a5d915dab5677ec976e0d44b6bddf3d29c6b3c0f"
SCHEMA = "rgeo-zgeo-1ms-id2z20-authority-l0-feedback-result-v1"
OFFLINE_SCHEMA = "rgeo-zgeo-1ms-id2z20-authority-l0-feedback-offline-v1"
ARM_IDS = ("hold", "b0_plus", "b0_minus", "b1_plus", "b1_minus",
           "b2_plus", "b2_minus", "b3_plus", "b3_minus")


def inside(path: Path, label: str) -> Path:
    return z18.inside(path, label)


def load_json(path: Path) -> dict[str, Any]:
    return z18.load_json(path)


def _error(message: str) -> Exception:
    return z6._error(message)


def _require(stage: dict[str, Any]) -> None:
    if io.sha256(CONFIG) != CONFIG_SHA256:
        raise _error("ID2Z20 config hash mismatch")
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2z20-authority-l0-feedback-v1",
        "identity": "rgeo-zgeo-1ms-id2z20-authority-l0-feedback-v1",
        "stage": "ID-2Z20", "takeover_time_ms": 1100,
        "control_period_ms": 1, "common_horizon_steps": 65,
        "common_terminal_state_index": 65, "root_last_issue": 31,
        "root_state_index": 32, "phase_issues": [32, 40],
        "maximum_rollouts": 23, "maximum_reset_calls": 23,
        "maximum_advance_attempts": 1495, "maximum_gotsc_calls": 1495,
        "maximum_verified_plant_advances": 1495,
        "maximum_retained_states": 1518,
        "required_artifact_files_if_all_complete": 7590,
        "retry_after_any_advance_attempt": "forbidden",
        "models_fit_or_updated": 0,
        "calibration_and_holdout_execution": "forbidden",
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise _error(f"frozen field changed: {key}")
    if stage.get("terminal_state_indices") != [60, 61, 62, 63, 64, 65]:
        raise _error("terminal state set changed")
    if stage.get("phase_b", {}).get("arm_order") != list(ARM_IDS):
        raise _error("selector arm order changed")
    coordinates = stage.get("basis_coordinates", [])
    if [row.get("coordinate_id") for row in coordinates] != ["b0", "b1", "b2", "b3"]:
        raise _error("basis identities changed")
    if any(len(row.get("card15_field_delta", [])) != 14 for row in coordinates):
        raise _error("basis coordinate dimension changed")
    action = stage.get("action_semantics", {})
    required_bools = (
        "absolute_card15_targets", "full_0p3_a_allowed",
        "pulse_is_returned_to_frozen_root_center_next_issue",
    )
    if any(action.get(key) is not True for key in required_bools):
        raise _error("exact action contract changed")
    if (action.get("software_queue_added") is not False
            or action.get("legacy_runner_clipping_may_be_relied_on") is not False
            or action.get("odd_symmetry_assumed") is not False
            or action.get("future_actual_or_active_current_as_selector_input") is not False):
        raise _error("forbidden action assumption enabled")
    if stage.get("data_contract", {}).get("phase_c_fit_weight") != 0:
        raise _error("Phase C data role changed")


def _verify_evidence(stage: dict[str, Any]) -> dict[str, dict[str, Any]]:
    values: dict[str, dict[str, Any]] = {}
    for name, spec in stage["evidence"].items():
        path = inside(ROOT / spec["path"], name)
        if io.sha256(path) != spec["sha256"]:
            raise _error(f"evidence hash mismatch: {name}")
        values[name] = load_json(path) if path.suffix == ".json" else {}
    result = values["id2z18_result"]
    audit = values["id2z18_independent"]
    attribution = values["id2z19r1_attribution"]
    if (result.get("route") != stage["evidence"]["id2z18_result"]["required_route"]
            or result.get("passed") is not True
            or audit.get("audit_passed") is not True
            or attribution.get("route")
            != stage["evidence"]["id2z19r1_attribution"]["required_route"]):
        raise _error("source evidence route mismatch")
    return values


def runtime_stage(stage: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    value = dict(base)
    value.update(stage)
    value["horizon_steps"] = int(stage["common_horizon_steps"])
    value["empirical_exploration"] = dict(stage["empirical_exploration"])
    value["empirical_exploration"]["inner_pulse_issue_clearance"] = dict(
        stage["empirical_exploration"]["simulator_development_preissue_clearance"])
    return value


def load(path: Path = CONFIG) -> tuple[dict[str, Any], dict[str, Any], Any,
                                       dict[str, Any], dict[str, Any], dict[str, Any]]:
    path = inside(path, "ID2Z20 config")
    if path != CONFIG.resolve():
        raise _error("alternate ID2Z20 config forbidden")
    stage = load_json(path)
    _require(stage)
    evidence = _verify_evidence(stage)
    _, base, cfg, _, _, _ = z18.load(z18.CONFIG)
    dev = evidence["development_root_reference"]
    validation = evidence["validation_root_reference"]
    for name, row in (("development", dev), ("validation", validation)):
        if (row.get("passed") is not True or len(row.get("states", [])) != 66
                or len(row.get("actions", [])) != 65):
            raise _error(f"{name} root reference incomplete")
    if dev["actions"][:32] == validation["actions"][:32]:
        raise _error("validation history is not distinct")
    return stage, runtime_stage(stage, base), cfg, evidence, dev, validation


def target_from_action(action: dict[str, Any], cfg: Any, name: str) -> Card15Target:
    return base.target_from_fields(action["expected_card15_fields"], cfg, name)


def root_targets(reference: dict[str, Any], cfg: Any, label: str) -> list[Card15Target]:
    return [target_from_action(action, cfg, f"id2z20.{label}.issue{issue}")
            for issue, action in enumerate(reference["actions"][:32])]


def offset_target(center: Card15Target, delta: Sequence[float], sign: int,
                  cfg: Any, name: str) -> Card15Target:
    if sign not in (-1, 1):
        raise _error("basis sign must be +/-1")
    fields = [format_number(Decimal(field.strip()) + Decimal(str(sign)) * Decimal(str(step)))
              for field, step in zip(center.card15_fields, delta)]
    return base.target_from_fields(fields, cfg, name)


def basis_targets(stage: dict[str, Any], center: Card15Target,
                  cfg: Any, label: str) -> dict[str, Card15Target]:
    values = {"hold": center}
    for row in stage["basis_coordinates"]:
        for sign_name, sign in (("plus", 1), ("minus", -1)):
            arm = f"{row['coordinate_id']}_{sign_name}"
            values[arm] = offset_target(center, row["card15_field_delta"], sign, cfg,
                                        f"id2z20.{label}.{arm}")
    return values


def action_row(target: Card15Target, issue: int, cfg: Any,
               previous: Sequence[Decimal], arm_id: str,
               decision: dict[str, Any] | None = None) -> dict[str, Any]:
    exact = card15_target_decimal_a(target, cfg.turns_tsc, name=f"id2z20.action.{issue}")
    maximum = assert_exact_slew(previous, exact, name=f"id2z20.issue.{issue}")
    row = {
        "issue_step": issue, "issue_time_ms": 1100 + issue,
        "effect_state_index": issue + 1, "effect_time_ms": 1101 + issue,
        "expected_card15_fields": list(target.card15_fields),
        "target_current_a_tsc": list(target.current_a_tsc),
        "maximum_issued_delta_a": maximum, "arm_id": arm_id,
    }
    if decision is not None:
        row["selector_decision"] = decision
    return row


def basis_geometry(stage: dict[str, Any], center: Card15Target,
                   cfg: Any) -> dict[str, Any]:
    arms = basis_targets(stage, center, cfg, "geometry")
    base = np.asarray(center.current_a_tsc, dtype=float)
    matrix = np.stack([np.asarray(arms[f"b{i}_plus"].current_a_tsc) - base
                       for i in range(4)], axis=1)
    singular = np.linalg.svd(matrix, compute_uv=False)
    rank = int(np.linalg.matrix_rank(
        matrix, tol=float(stage["basis_gates"]["rank_relative_tolerance"]) * singular[0]))
    condition = float(singular[0] / singular[-1])
    maximum = float(np.max(np.abs(matrix)))
    passed = bool(rank == 4
                  and condition <= float(stage["basis_gates"]["maximum_current_space_condition"])
                  and maximum <= float(stage["basis_gates"]["maximum_each_coordinate_issue_delta_a"]) + 1e-12)
    return {"coordinate_order": ["b0", "b1", "b2", "b3"],
            "current_space_columns_a_tsc": matrix.tolist(),
            "singular_values": singular.tolist(), "rank": rank,
            "condition": condition, "maximum_absolute_component_a": maximum,
            "passed": passed}


def static_spec(stage: dict[str, Any], reference: dict[str, Any], cfg: Any,
                rollout_id: str, phase_issue: int | None,
                arm_id: str, data_role: str, fit_weight: int) -> dict[str, Any]:
    sequence = root_targets(reference, cfg, rollout_id)
    center = sequence[-1]
    arms = basis_targets(stage, center, cfg, rollout_id)
    while len(sequence) < int(stage["common_horizon_steps"]):
        sequence.append(center)
    if phase_issue is not None and arm_id != "hold":
        sequence[phase_issue] = arms[arm_id]
        sequence[phase_issue + 1] = center
    return {"rollout_id": rollout_id, "family_id": rollout_id,
            "data_role": data_role, "fit_weight": fit_weight,
            "root_family_id": reference["family_id"], "phase_issue": phase_issue,
            "arm_id": arm_id, "pulse_issue_steps": [] if phase_issue is None else [phase_issue],
            "targets": sequence}


def phase_a_specs(stage: dict[str, Any], reference: dict[str, Any],
                  cfg: Any) -> list[dict[str, Any]]:
    rows = [static_spec(stage, reference, cfg, "dev_hold", None, "hold", "development", 1)]
    for phase in stage["phase_issues"]:
        for arm in ARM_IDS[1:]:
            rows.append(static_spec(stage, reference, cfg, f"dev_p{phase}_{arm}",
                                    phase, arm, "development", 1))
    return rows


def _state_velocity(states: Sequence[dict[str, Any]], index: int) -> tuple[float, float]:
    if index <= 0:
        return 0.0, 0.0
    return ((float(states[index]["r_geo_m"]) - float(states[index - 1]["r_geo_m"])) * 1000.0,
            (float(states[index]["z_geo_m"]) - float(states[index - 1]["z_geo_m"])) * 1000.0)


def _distance(state: dict[str, Any], source: dict[str, Any]) -> float:
    return math.hypot(float(state["r_geo_m"]) - float(source["r_geo_m"]),
                      float(state["z_geo_m"]) - float(source["z_geo_m"]))


def _score(distance: float, speed: float, ip_fraction: float) -> float:
    return max(distance / 0.025, speed / 0.1, ip_fraction / 0.05)


def response_library(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    by_id = {row["rollout_id"]: row for row in rows}
    baseline = by_id.get("dev_hold")
    if baseline is None or not baseline.get("passed"):
        raise _error("complete development hold required")
    values: dict[str, Any] = {"baseline_rollout_id": "dev_hold", "phases": {}}
    for phase in stage["phase_issues"]:
        phase_row: dict[str, Any] = {}
        for horizon in (4, 8):
            endpoint = phase + horizon
            base_velocity = _state_velocity(baseline["states"], endpoint)
            origin_velocity = _state_velocity(baseline["states"], phase)
            entry = {"baseline_displacement": [
                        float(baseline["states"][endpoint][key])
                        - float(baseline["states"][phase][key])
                        for key in ("r_geo_m", "z_geo_m", "ip_a")],
                     "baseline_velocity_change_m_per_s": [
                        base_velocity[0] - origin_velocity[0],
                        base_velocity[1] - origin_velocity[1]],
                     "arms": {"hold": {"response_displacement": [0.0, 0.0, 0.0],
                                        "response_velocity_m_per_s": [0.0, 0.0]}}}
            for arm in ARM_IDS[1:]:
                row = by_id[f"dev_p{phase}_{arm}"]
                velocity = _state_velocity(row["states"], endpoint)
                entry["arms"][arm] = {
                    "response_displacement": [
                        float(row["states"][endpoint][key])
                        - float(baseline["states"][endpoint][key])
                        for key in ("r_geo_m", "z_geo_m", "ip_a")],
                    "response_velocity_m_per_s": [velocity[0] - base_velocity[0],
                                                   velocity[1] - base_velocity[1]],
                }
            phase_row[str(horizon)] = entry
        values["phases"][str(phase)] = phase_row
    return values


def select_arm(stage: dict[str, Any], library: dict[str, Any], state: dict[str, Any],
               previous_state: dict[str, Any], source: dict[str, Any], issue: int,
               horizon: int, arms: dict[str, Card15Target],
               center: Card15Target) -> tuple[str, dict[str, Any]]:
    phase = 32 if issue < 40 else 40
    cell = library["phases"][str(phase)][str(horizon)]
    current_velocity = ((float(state["r_geo_m"]) - float(previous_state["r_geo_m"])) * 1000.0,
                        (float(state["z_geo_m"]) - float(previous_state["z_geo_m"])) * 1000.0)
    source_ip = abs(float(source["ip_a"]))
    candidates = []
    center_current = np.asarray(center.current_a_tsc, dtype=float)
    for order, arm in enumerate(ARM_IDS):
        response = cell["arms"][arm]
        displacement = np.asarray(cell["baseline_displacement"], dtype=float) + np.asarray(
            response["response_displacement"], dtype=float)
        predicted = {"r_geo_m": float(state["r_geo_m"]) + displacement[0],
                     "z_geo_m": float(state["z_geo_m"]) + displacement[1],
                     "ip_a": float(state["ip_a"]) + displacement[2]}
        velocity = np.asarray(current_velocity) + np.asarray(
            cell["baseline_velocity_change_m_per_s"]) + np.asarray(
                response["response_velocity_m_per_s"])
        distance = _distance(predicted, source)
        speed = float(np.linalg.norm(velocity))
        ip_fraction = abs(predicted["ip_a"] - float(source["ip_a"])) / source_ip
        score = _score(distance, speed, ip_fraction)
        current_excursion = float(np.linalg.norm(
            np.asarray(arms[arm].current_a_tsc) - center_current))
        candidates.append({"arm_id": arm, "predicted_score": score,
                           "predicted_distance_m": distance,
                           "predicted_speed_m_per_s": speed,
                           "predicted_ip_fraction": ip_fraction,
                           "current_excursion_a_l2": current_excursion,
                           "frozen_order": order})
    selected = min(candidates, key=lambda row: (row["predicted_score"],
                                                 row["current_excursion_a_l2"],
                                                 row["frozen_order"]))
    return selected["arm_id"], {"issue_step": issue, "response_phase_issue": phase,
                                 "response_horizon_ms": horizon,
                                 "selected_arm_id": selected["arm_id"],
                                 "candidate_values": candidates}


def _target_provider_static(spec: dict[str, Any]) -> Callable[..., tuple[Card15Target, str, dict[str, Any] | None]]:
    def provider(issue: int, *_: Any) -> tuple[Card15Target, str, dict[str, Any] | None]:
        arm = spec["arm_id"] if issue == spec.get("phase_issue") else "hold"
        return spec["targets"][issue], arm, None
    return provider


def policy_spec(stage: dict[str, Any], reference: dict[str, Any], cfg: Any,
                rollout_id: str, candidate_id: str, library: dict[str, Any],
                data_role: str, fit_weight: int,
                finite_return_only: bool = False) -> tuple[dict[str, Any], Callable[..., Any]]:
    prefix = root_targets(reference, cfg, rollout_id)
    center = prefix[-1]
    arms = basis_targets(stage, center, cfg, rollout_id)
    horizon = int(stage["phase_b"][candidate_id]["response_horizon_ms"])
    decisions = set(int(value) for value in stage["phase_b"][candidate_id]["decision_issues"])
    stateful = {"first_nonhold_seen": False}

    def provider(issue: int, states: Sequence[dict[str, Any]],
                 source: dict[str, Any]) -> tuple[Card15Target, str, dict[str, Any] | None]:
        if issue < 32:
            return prefix[issue], "root", None
        if issue not in decisions or (finite_return_only and stateful["first_nonhold_seen"]):
            return center, "hold", None
        arm, decision = select_arm(stage, library, states[-1], states[-2], source,
                                   issue, horizon, arms, center)
        if arm != "hold":
            stateful["first_nonhold_seen"] = True
        return arms[arm], arm, decision

    spec = {"rollout_id": rollout_id, "family_id": rollout_id,
            "candidate_id": candidate_id, "data_role": data_role,
            "fit_weight": fit_weight, "root_family_id": reference["family_id"],
            "pulse_issue_steps": sorted(decisions), "finite_return_only": finite_return_only,
            "response_horizon_ms": horizon}
    return spec, provider


def one_rollout(cfg: Any, stage: dict[str, Any], spec: dict[str, Any],
                provider: Callable[..., tuple[Card15Target, str, dict[str, Any] | None]],
                *, runner_cls: type | None = None) -> dict[str, Any]:
    runner_type = runner_cls or base.CountingRunner
    runner = None
    states: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    attempted: list[dict[str, Any]] = []
    reasons: list[str] = []
    reset_calls = attempts = successes = 0
    started = time.perf_counter()
    try:
        runner = runner_type(cfg, worker_id=f"id2z20_{spec['rollout_id']}", keep_workspace=False)
        reset_calls += 1
        state = runner.reset(episode_name=spec["rollout_id"])
        states.append(base._record(cfg, state)); base._validate_record(states[-1], "state0")
        if states[0]["time_ms"] != 1100 or int(state.get("returncode", 0)) != 0 or bool(state.get("abnormal", False)):
            reasons.append("SOURCE_RESET_INVALID")
        source_signal = RGeoZGeoSignal.from_tsc_state(state)
        envelope = OneMsNR1SafetyEnvelope.from_signal(source_signal)
        for issue in range(int(stage["common_horizon_steps"])):
            if reasons:
                break
            signal = RGeoZGeoSignal.from_tsc_state(state)
            reasons.extend(envelope.state_reasons(signal, state["currents_a_tsc"],
                                                   cfg.min_current_a_tsc, cfg.max_current_a_tsc))
            reasons.extend(base._outer_reasons(stage, source_signal, signal))
            target, arm, decision = provider(issue, states, states[0])
            if arm not in ("root", "hold"):
                reasons.extend(base._pulse_clearance(stage, source_signal, signal))
            exact = card15_target_decimal_a(target, cfg.turns_tsc,
                                            name=f"id2z20.{spec['rollout_id']}.{issue}")
            try:
                maximum = assert_exact_slew(states[-1]["active_command_decimal_a_tsc"], exact,
                                            name=f"id2z20.issue.{issue}")
                if any(value < Decimal(str(low)) or value > Decimal(str(high))
                       for value, low, high in zip(exact, cfg.min_current_a_tsc,
                                                  cfg.max_current_a_tsc)):
                    raise _error("target leaves absolute current limits")
            except Exception as exc:
                reasons.append(f"ISSUED_ACTION:{issue}:{type(exc).__name__}:{exc}")
                break
            if reasons:
                break
            action = action_row(target, issue, cfg,
                                states[-1]["active_command_decimal_a_tsc"], arm, decision)
            action["maximum_issued_delta_a"] = maximum
            attempted.append(action); attempts += 1
            try:
                successor = runner.step_current_a(np.asarray(target.current_a_tsc, dtype=float))
            except Exception as exc:
                reasons.append(f"STEP_EXECUTION:{issue}:{type(exc).__name__}:{exc}")
                break
            try:
                record = base._record(cfg, successor); base._validate_record(record, f"state{issue + 1}")
            except Exception as exc:
                reasons.append(f"SUCCESSOR_RECORD:{issue}:{type(exc).__name__}:{exc}")
                break
            if record["time_ms"] != 1101 + issue:
                reasons.append(f"TIME:{issue}:{record['time_ms']}")
                break
            states.append(record)
            if int(successor.get("returncode", 0)) != 0 or bool(successor.get("abnormal", False)):
                reasons.append(f"TSC_STATUS:{issue}:{successor.get('returncode', 0)}")
                break
            actions.append(action); successes += 1
            if tuple(record["active_command_card15_fields"]) != target.card15_fields:
                reasons.append(f"CARD15:{issue}")
            try:
                record["maximum_observed_delta_a"] = assert_exact_slew(
                    states[-2]["actual_current_decimal_a_tsc"], record["actual_current_decimal_a_tsc"],
                    name=f"id2z20.observed.{issue}")
            except Exception as exc:
                reasons.append(f"OBSERVED_SLEW:{issue}:{type(exc).__name__}:{exc}")
            successor_signal = RGeoZGeoSignal.from_tsc_state(successor)
            reasons.extend(envelope.state_reasons(successor_signal, successor["currents_a_tsc"],
                                                   cfg.min_current_a_tsc, cfg.max_current_a_tsc))
            reasons.extend(base._outer_reasons(stage, source_signal, successor_signal))
            reasons.extend(base._step_cap_reasons(stage, states[-2], states[-1]))
            state = successor
    except Exception as exc:
        reasons.append(f"ROLLOUT_EXECUTION:{type(exc).__name__}:{exc}")
    finally:
        if runner is not None:
            try:
                runner.cleanup_runtime_workspace()
            except Exception as exc:
                reasons.append(f"CLEANUP:{type(exc).__name__}:{exc}")
    reasons = list(dict.fromkeys(reasons))
    gotsc = 0 if runner is None else int(getattr(runner, "plant_advance_gotsc_calls", attempts))
    complete = bool(not reasons and reset_calls == 1 and attempts == successes == 65
                    and len(actions) == 65 and len(states) == 66)
    return {**spec, "schema_version": SCHEMA, "passed": complete, "reasons": reasons,
            "reset_calls": reset_calls, "advance_attempts": attempts,
            "plant_advance_gotsc_calls": gotsc, "verified_plant_advances": successes,
            "states": states, "actions": actions, "attempted_actions": attempted,
            "retry_attempted": False, "wall_time_s": time.perf_counter() - started}


def prefix_check(row: dict[str, Any], reference: dict[str, Any],
                 stage: dict[str, Any]) -> dict[str, Any]:
    return z6.prefix_check(row, reference, 33, 32, stage["semantic_artifacts"])


def safe_stop(row: dict[str, Any], stage: dict[str, Any]) -> bool:
    reasons = list(row.get("reasons", []))
    allowed = set(stage["empirical_exploration"]["allowed_safe_stop_reasons"])
    return bool(reasons) and set(reasons).issubset(allowed)


def _three_median(values: Sequence[float]) -> float:
    return max((float(np.median(values[i:i + 3])) for i in range(max(0, len(values) - 2))),
               default=0.0)


def _angular_gap(vectors: Sequence[Sequence[float]]) -> float:
    angles = sorted(math.degrees(math.atan2(v[1], v[0])) % 360.0 for v in vectors)
    return max((b - a for a, b in zip(angles, angles[1:] + [angles[0] + 360.0])),
               default=360.0)


def _weakest_projection(vectors: Sequence[Sequence[float]]) -> float:
    directions = [(math.cos(2 * math.pi * i / 64), math.sin(2 * math.pi * i / 64))
                  for i in range(64)]
    return min(max(v[0] * d[0] + v[1] * d[1] for v in vectors) for d in directions)


def phase_a_metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    by_id = {row["rollout_id"]: row for row in rows}
    baseline = by_id.get("dev_hold")
    gates = stage["measurement_gates"]
    arm_values = []
    geometry_states = []
    if baseline is None or not baseline.get("passed"):
        return {"passed": False, "reason": "BASELINE_INCOMPLETE", "arm_metrics": [],
                "geometry_states": []}
    for phase in stage["phase_issues"]:
        for arm in ARM_IDS[1:]:
            row = by_id.get(f"dev_p{phase}_{arm}")
            complete = bool(row and row.get("passed") and len(row.get("states", [])) == 66)
            rz, ip = [], []
            if complete:
                for index in range(phase + 1, 66):
                    dr = float(row["states"][index]["r_geo_m"]) - float(baseline["states"][index]["r_geo_m"])
                    dz = float(row["states"][index]["z_geo_m"]) - float(baseline["states"][index]["z_geo_m"])
                    rz.append(math.hypot(dr, dz))
                    ip.append(abs(float(row["states"][index]["ip_a"])
                                  - float(baseline["states"][index]["ip_a"])))
            peak, median3, max_ip = max(rz, default=0.0), _three_median(rz), max(ip, default=math.inf)
            passed = bool(complete and peak >= gates["minimum_each_signed_peak_rz_response_m"]
                          and median3 >= gates["minimum_each_signed_three_state_median_rz_response_m"]
                          and max_ip <= gates["maximum_paired_ip_response_a"])
            arm_values.append({"phase_issue": phase, "arm_id": arm, "complete": complete,
                               "peak_rz_response_m": peak,
                               "maximum_three_state_median_rz_response_m": median3,
                               "maximum_absolute_ip_response_a": max_ip, "passed": passed})
        consecutive = 0
        for index in range(phase + 1, 66):
            vectors = []
            for arm in ARM_IDS[1:]:
                row = by_id.get(f"dev_p{phase}_{arm}")
                if not row or len(row.get("states", [])) <= index:
                    break
                vectors.append((float(row["states"][index]["r_geo_m"])
                                - float(baseline["states"][index]["r_geo_m"]),
                                float(row["states"][index]["z_geo_m"])
                                - float(baseline["states"][index]["z_geo_m"])))
            if len(vectors) != 8:
                continue
            gap, weakest = _angular_gap(vectors), _weakest_projection(vectors)
            passed = bool(gap <= gates["maximum_signed_response_angular_gap_deg"] + 1e-12
                          and weakest >= gates["minimum_64_direction_weakest_best_projection_m"])
            consecutive = consecutive + 1 if passed else 0
            geometry_states.append({"phase_issue": phase, "state_index": index,
                                    "maximum_angular_gap_deg": gap,
                                    "weakest_best_projection_m": weakest, "passed": passed})
        if consecutive < gates["minimum_consecutive_geometry_states"]:
            # A passing pair can occur before a later failure; compute the true longest run below.
            pass
    longest_by_phase = {}
    for phase in stage["phase_issues"]:
        run = longest = 0
        for row in [value for value in geometry_states if value["phase_issue"] == phase]:
            run = run + 1 if row["passed"] else 0; longest = max(longest, run)
        longest_by_phase[str(phase)] = longest
    passed = bool(len(arm_values) == 16 and all(row["passed"] for row in arm_values)
                  and all(value >= gates["minimum_consecutive_geometry_states"]
                          for value in longest_by_phase.values()))
    return {"passed": passed, "arm_metrics": arm_values,
            "geometry_states": geometry_states, "longest_geometry_run_by_phase": longest_by_phase}


def terminal_metrics(row: dict[str, Any], stage: dict[str, Any]) -> dict[str, Any]:
    indices = stage["terminal_state_indices"]
    source = row["states"][0]
    complete = bool(row.get("passed") and len(row.get("states", [])) == 66)
    if not complete:
        return {"complete": False, "capture_passed": False,
                "terminal_worst_normalized_score": math.inf}
    per_state = []
    for index in indices:
        distance = _distance(row["states"][index], source)
        speed = math.hypot(*_state_velocity(row["states"], index))
        ip_fraction = abs(float(row["states"][index]["ip_a"])
                          - float(source["ip_a"])) / abs(float(source["ip_a"]))
        per_state.append({"state_index": index, "source_rz_distance_m": distance,
                          "rz_step_speed_m_per_s": speed,
                          "source_ip_fraction": ip_fraction,
                          "normalized_score": _score(distance, speed, ip_fraction)})
    return {"complete": True, "terminal_states": per_state,
            "terminal_max_source_rz_distance_m": max(v["source_rz_distance_m"] for v in per_state),
            "terminal_max_rz_step_speed_m_per_s": max(v["rz_step_speed_m_per_s"] for v in per_state),
            "terminal_max_source_ip_fraction": max(v["source_ip_fraction"] for v in per_state),
            "terminal_worst_normalized_score": max(v["normalized_score"] for v in per_state),
            "capture_passed": all(v["source_rz_distance_m"] <= 0.025
                                  and v["rz_step_speed_m_per_s"] <= 0.1
                                  and v["source_ip_fraction"] <= 0.05 for v in per_state)}


def utility_metrics(row: dict[str, Any], hold: dict[str, Any],
                    stage: dict[str, Any]) -> dict[str, Any]:
    current, baseline = terminal_metrics(row, stage), terminal_metrics(hold, stage)
    if not current["complete"] or not baseline["complete"]:
        return {"passed": False, "candidate": current, "baseline": baseline}
    gates = stage["measurement_gates"]
    improvement = ((baseline["terminal_worst_normalized_score"]
                    - current["terminal_worst_normalized_score"])
                   / baseline["terminal_worst_normalized_score"])
    speed_improvement = (baseline["terminal_max_rz_step_speed_m_per_s"]
                         - current["terminal_max_rz_step_speed_m_per_s"])
    distance_regression = (current["terminal_max_source_rz_distance_m"]
                           - baseline["terminal_max_source_rz_distance_m"])
    per_state = all(a["normalized_score"] <= b["normalized_score"]
                    + gates["per_terminal_state_normalized_score_regression_tolerance"]
                    for a, b in zip(current["terminal_states"], baseline["terminal_states"]))
    nonhold = any(action.get("arm_id") not in ("root", "hold") for action in row["actions"])
    passed = bool(improvement >= gates["minimum_policy_score_improvement_fraction"]
                  and speed_improvement >= gates["minimum_policy_terminal_speed_improvement_m_per_s"]
                  and distance_regression <= gates["maximum_policy_distance_regression_m"]
                  and per_state and nonhold)
    return {"passed": passed, "candidate": current, "baseline": baseline,
            "score_improvement_fraction": improvement,
            "terminal_speed_improvement_m_per_s": speed_improvement,
            "terminal_distance_regression_m": distance_regression,
            "every_terminal_state_not_worse": per_state,
            "at_least_one_nonhold_decision": nonhold}


def finite_return_metrics(row: dict[str, Any], hold: dict[str, Any],
                          stage: dict[str, Any]) -> dict[str, Any]:
    complete = bool(row.get("passed") and hold.get("passed"))
    maxima = {"r_m": math.inf, "z_m": math.inf, "ip_a": math.inf}
    if complete:
        maxima = {
            "r_m": max(abs(float(row["states"][i]["r_geo_m"])
                           - float(hold["states"][i]["r_geo_m"])) for i in stage["terminal_state_indices"]),
            "z_m": max(abs(float(row["states"][i]["z_geo_m"])
                           - float(hold["states"][i]["z_geo_m"])) for i in stage["terminal_state_indices"]),
            "ip_a": max(abs(float(row["states"][i]["ip_a"])
                            - float(hold["states"][i]["ip_a"])) for i in stage["terminal_state_indices"]),
        }
    gates = stage["measurement_gates"]
    passed = bool(complete and maxima["r_m"] <= gates["validation_finite_return_maximum_terminal_r_difference_m"]
                  and maxima["z_m"] <= gates["validation_finite_return_maximum_terminal_z_difference_m"]
                  and maxima["ip_a"] <= gates["validation_finite_return_maximum_terminal_ip_difference_a"])
    return {"passed": passed, "complete": complete,
            "maximum_terminal_difference": maxima,
            "final_active_target_returned_to_center": bool(complete and
                row["actions"][-1]["expected_card15_fields"]
                == hold["actions"][-1]["expected_card15_fields"])}


def _save_row(output: Path, row: dict[str, Any], source_revision: str) -> dict[str, Any]:
    row["schema_version"] = SCHEMA; row["source_revision"] = source_revision
    io.write_new(output / f"{row['rollout_id']}.json", row)
    return row


def offline(path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    geometry: dict[str, Any] = {}
    static_checks = []
    try:
        stage, _, cfg, _, dev, validation = load(path)
        for label, reference in (("development", dev), ("validation", validation)):
            roots = root_targets(reference, cfg, label); center = roots[-1]
            geometry_value = basis_geometry(stage, center, cfg)
            if label == "development": geometry = geometry_value
            if not geometry_value["passed"]:
                failures.append(f"{label.upper()}_BASIS_GEOMETRY")
            arms = basis_targets(stage, center, cfg, label)
            for arm, target in arms.items():
                center_exact = card15_target_decimal_a(center, cfg.turns_tsc, name=f"{label}.center")
                exact = card15_target_decimal_a(target, cfg.turns_tsc, name=f"{label}.{arm}")
                maximum = assert_exact_slew(center_exact, exact, name=f"{label}.{arm}.pulse")
                returned = assert_exact_slew(exact, center_exact, name=f"{label}.{arm}.return")
                within = all(value >= Decimal(str(low)) and value <= Decimal(str(high))
                             for value, low, high in zip(exact, cfg.min_current_a_tsc,
                                                        cfg.max_current_a_tsc))
                passed = bool(maximum <= 0.3 and returned <= 0.3 and within)
                static_checks.append({"root": label, "arm_id": arm,
                                      "pulse_maximum_delta_a": maximum,
                                      "return_maximum_delta_a": returned,
                                      "absolute_current_passed": within, "passed": passed})
                if not passed:
                    failures.append(f"{label.upper()}_ARM:{arm}")
        specs = phase_a_specs(stage, dev, cfg)
        if len(specs) != 17 or len({row["rollout_id"] for row in specs}) != 17:
            failures.append("PHASE_A_POPULATION")
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {"schema_version": OFFLINE_SCHEMA, "source_revision": source_revision,
            "stage_config_sha256": CONFIG_SHA256, "passed": not failures,
            "failures": list(dict.fromkeys(failures)), "basis_geometry": geometry,
            "static_arm_checks": static_checks,
            "phase_a_rollouts_planned": 17, "phase_b_maximum_rollouts_planned": 2,
            "phase_c_maximum_rollouts_planned": 4,
            "maximum_rollouts": 23, "maximum_advance_attempts": 1495,
            "reset_calls": 0, "advance_attempts": 0,
            "plant_advance_gotsc_calls": 0, "models_fit_or_updated": 0}


def _route(stage: dict[str, Any], execution: bool, raw_ok: bool, phase_a_ok: bool,
           utility_ok: bool, replay_ok: bool, validation_ok: bool,
           capture_ok: bool) -> str:
    routes = stage["routes"]
    if not execution: return routes["execution_or_interface_fail"]
    if not raw_ok: return routes["raw_integrity_fail"]
    if not phase_a_ok: return routes["phase_a_signal_or_geometry_fail"]
    if not utility_ok: return routes["phase_b_no_utility"]
    if not replay_ok: return routes["replay_fail"]
    if not validation_ok: return routes["validation_or_finite_return_fail"]
    return routes["authority_and_capture_pass" if capture_ok else "authority_pass_no_capture"]


def execute(stage: dict[str, Any], runtime: dict[str, Any], cfg: Any,
            dev: dict[str, Any], validation: dict[str, Any], source_revision: str,
            output: Path, storage_gate: dict[str, Any], *, runner_cls: type | None = None) -> dict[str, Any]:
    isolation = z18.z17.z7.configure_run_root(cfg, output)
    rows: list[dict[str, Any]] = []
    prefixes: list[dict[str, Any]] = []
    execution = True
    phase_a_rows = []
    for spec in phase_a_specs(stage, dev, cfg):
        row = one_rollout(cfg, runtime, spec, _target_provider_static(spec), runner_cls=runner_cls)
        _save_row(output, row, source_revision); rows.append(row); phase_a_rows.append(row)
        prefixes.append(prefix_check(row, dev, stage))
        if not row.get("passed"):
            if not safe_stop(row, stage):
                execution = False
            break
    phase_a = phase_a_metrics(phase_a_rows, stage)
    library = response_library(phase_a_rows, stage) if execution and phase_a.get("passed") else {}
    policy_rows: list[dict[str, Any]] = []
    utility_values: list[dict[str, Any]] = []
    if execution and phase_a.get("passed"):
        hold = phase_a_rows[0]
        for candidate in stage["phase_b"]["candidate_ids"]:
            spec, provider = policy_spec(stage, dev, cfg, candidate, candidate, library,
                                         "development", 1)
            row = one_rollout(cfg, runtime, spec, provider, runner_cls=runner_cls)
            _save_row(output, row, source_revision); rows.append(row); policy_rows.append(row)
            prefixes.append(prefix_check(row, dev, stage))
            utility_values.append({"candidate_id": candidate, **utility_metrics(row, hold, stage)})
            if not row.get("passed") and not safe_stop(row, stage):
                execution = False
                break
    eligible = [value for value in utility_values if value.get("passed")]
    selected_id = (min(eligible, key=lambda value: (
        value["candidate"]["terminal_worst_normalized_score"], value["candidate_id"]))["candidate_id"]
                   if eligible else None)
    selected_row = next((row for row in policy_rows if row["candidate_id"] == selected_id), None)
    replay = validation_hold = validation_policy = finite_return = None
    replay_value = {"passed": False, "failures": ["NOT_RUN"]}
    validation_utility = {"passed": False}
    finite_value = {"passed": False}
    if execution and selected_id is not None:
        spec, provider = policy_spec(stage, dev, cfg, "selected_replay", selected_id,
                                     library, "replay", 0)
        replay = one_rollout(cfg, runtime, spec, provider, runner_cls=runner_cls)
        _save_row(output, replay, source_revision); rows.append(replay)
        prefixes.append(prefix_check(replay, dev, stage))
        replay_value = base.compare_rows(selected_row, replay, stage)
        if not replay.get("passed") and not safe_stop(replay, stage): execution = False
    if execution and replay_value.get("passed"):
        hold_spec = static_spec(stage, validation, cfg, "validation_hold", None, "hold",
                                "validation", 0)
        validation_hold = one_rollout(cfg, runtime, hold_spec,
                                      _target_provider_static(hold_spec), runner_cls=runner_cls)
        _save_row(output, validation_hold, source_revision); rows.append(validation_hold)
        prefixes.append(prefix_check(validation_hold, validation, stage))
        if not validation_hold.get("passed") and not safe_stop(validation_hold, stage): execution = False
    if execution and validation_hold is not None:
        spec, provider = policy_spec(stage, validation, cfg, "validation_policy", selected_id,
                                     library, "validation", 0)
        validation_policy = one_rollout(cfg, runtime, spec, provider, runner_cls=runner_cls)
        _save_row(output, validation_policy, source_revision); rows.append(validation_policy)
        prefixes.append(prefix_check(validation_policy, validation, stage))
        validation_utility = utility_metrics(validation_policy, validation_hold, stage)
        if not validation_policy.get("passed") and not safe_stop(validation_policy, stage): execution = False
    if execution and validation_policy is not None:
        spec, provider = policy_spec(stage, validation, cfg, "validation_finite_return",
                                     selected_id, library, "validation", 0, True)
        finite_return = one_rollout(cfg, runtime, spec, provider, runner_cls=runner_cls)
        _save_row(output, finite_return, source_revision); rows.append(finite_return)
        prefixes.append(prefix_check(finite_return, validation, stage))
        finite_value = finite_return_metrics(finite_return, validation_hold, stage)
        if not finite_return.get("passed") and not safe_stop(finite_return, stage): execution = False
    counters = {key: sum(int(row.get(key, 0)) for row in rows) for key in
                ("reset_calls", "advance_attempts", "plant_advance_gotsc_calls",
                 "verified_plant_advances")}
    if (len(rows) > stage["maximum_rollouts"]
            or any(counters[key] > stage[limit] for key, limit in (
                ("reset_calls", "maximum_reset_calls"),
                ("advance_attempts", "maximum_advance_attempts"),
                ("plant_advance_gotsc_calls", "maximum_gotsc_calls"),
                ("verified_plant_advances", "maximum_verified_plant_advances")))):
        execution = False
    inventory = io.raw_inventory(output, rows, stage)
    expected_files = 5 * sum(len(row.get("states", [])) for row in rows)
    raw_ok = bool(not inventory["missing_required_artifacts"]
                  and inventory["required_artifact_files"] == expected_files)
    prefix_ok = bool(prefixes and all(value.get("passed") for value in prefixes))
    execution = bool(execution and prefix_ok)
    utility_ok = bool(selected_id is not None)
    validation_ok = bool(validation_utility.get("passed") and finite_value.get("passed"))
    selected_capture = bool(selected_row and terminal_metrics(selected_row, stage)["capture_passed"])
    replay_capture = bool(replay and terminal_metrics(replay, stage)["capture_passed"])
    capture_ok = bool(selected_capture and replay_capture)
    route = _route(stage, execution, raw_ok, bool(phase_a.get("passed")), utility_ok,
                   bool(replay_value.get("passed")), validation_ok, capture_ok)
    scientific = {"phase_a": phase_a, "response_library": library,
                  "phase_b_candidates": utility_values, "selected_candidate_id": selected_id,
                  "selected_replay_check": replay_value,
                  "development_capture_seed_passed": selected_capture,
                  "fresh_replay_capture_seed_passed": replay_capture,
                  "validation_policy_utility": validation_utility,
                  "validation_finite_return": finite_value,
                  "authority_l0_passed": validation_ok,
                  "six_state_capture_seed_passed": capture_ok,
                  "recourse_l1_claimed": False}
    result = {"schema_version": SCHEMA, "source_revision": source_revision,
              "stage_config_sha256": CONFIG_SHA256,
              "passed": route in (stage["routes"]["authority_pass_no_capture"],
                                   stage["routes"]["authority_and_capture_pass"]),
              "route": route, "storage_gate": storage_gate,
              "run_root_isolation": isolation, "execution_integrity_passed": execution,
              "raw_integrity_passed": raw_ok, "prefix_checks": prefixes,
              "scientific_metrics": scientific, "rollouts_started": len(rows),
              "complete_rollouts": sum(bool(row.get("passed")) for row in rows),
              "guarded_safe_stops": sum(safe_stop(row, stage) for row in rows),
              **counters, **inventory, "models_fit_or_updated": 0,
              "calibration_or_holdout_records_read": 0,
              "claim_boundary": stage["claim_boundary"]}
    io.write_new(output / "result.json", result)
    return result


def _failure_result(stage: dict[str, Any], source_revision: str, output: Path,
                    storage_gate: dict[str, Any], exc: Exception) -> dict[str, Any]:
    rows = []
    for item in sorted(output.glob("*.json")):
        if item.name in {"offline_preflight.json", "result.json", "independent_raw_audit.json"}:
            continue
        try: row = load_json(item)
        except Exception: continue
        if "rollout_id" in row: rows.append(row)
    counters = {key: sum(int(row.get(key, 0)) for row in rows) for key in
                ("reset_calls", "advance_attempts", "plant_advance_gotsc_calls",
                 "verified_plant_advances")}
    try: inventory = io.raw_inventory(output, rows, stage)
    except Exception as inv:
        inventory = {"required_artifact_files": 0, "required_artifact_bytes": 0,
                     "required_artifact_inventory_sha256": None,
                     "missing_required_artifacts": [f"FINALIZER:{type(inv).__name__}:{inv}"]}
    return {"schema_version": SCHEMA, "source_revision": source_revision,
            "stage_config_sha256": CONFIG_SHA256, "passed": False,
            "route": stage["routes"]["execution_or_interface_fail"],
            "failure": f"{type(exc).__name__}:{exc}", "storage_gate": storage_gate,
            "rollouts_started": len(rows), **counters, **inventory,
            "models_fit_or_updated": 0, "calibration_or_holdout_records_read": 0,
            "claim_boundary": "Best-effort classified failure; no Authority-L0 verdict."}


def run(path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = inside(output, "ID2Z20 output")
    if output.exists(): raise FileExistsError(str(output))
    stage, runtime, cfg, _, dev, validation = load(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    storage_gate = io.storage(stage, output)
    output.mkdir()
    preflight = offline(path, source_revision)
    io.write_new(output / "offline_preflight.json", preflight)
    if not storage_gate["passed"] or not preflight["passed"]:
        route = stage["routes"]["storage_fail" if not storage_gate["passed"] else "input_or_contract_fail"]
        result = {"schema_version": SCHEMA, "source_revision": source_revision,
                  "stage_config_sha256": CONFIG_SHA256, "passed": False,
                  "route": route, "storage_gate": storage_gate, "reasons": preflight["failures"],
                  "rollouts_started": 0, "reset_calls": 0, "advance_attempts": 0,
                  "plant_advance_gotsc_calls": 0, "verified_plant_advances": 0,
                  "models_fit_or_updated": 0, "calibration_or_holdout_records_read": 0}
        io.write_new(output / "result.json", result); return result
    try:
        return execute(stage, runtime, cfg, dev, validation, source_revision, output, storage_gate)
    except Exception as exc:
        result = _failure_result(stage, source_revision, output, storage_gate, exc)
        if not (output / "result.json").exists(): io.write_new(output / "result.json", result)
        return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-config", type=Path, default=CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--offline-only", action="store_true")
    args = parser.parse_args(argv)
    if args.offline_only:
        value = offline(args.stage_config, args.source_revision)
    else:
        if args.output is None: parser.error("--output is required unless --offline-only")
        value = run(args.stage_config, args.source_revision, args.output)
    print(json.dumps(value, indent=2, sort_keys=True, allow_nan=False))
    return 0 if value["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
