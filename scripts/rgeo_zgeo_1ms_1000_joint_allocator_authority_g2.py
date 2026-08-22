#!/usr/bin/env python3
"""Fixed-1000 readback-reserved joint allocator Authority G2."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
import json
import math
from pathlib import Path
import sys
import time
from typing import Any, Mapping, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_1000_absolute_radial_authority_g0 as g0  # noqa: E402
from scripts import rgeo_zgeo_1ms_1000_baseline_b0 as b0  # noqa: E402
from scripts import rgeo_zgeo_1ms_1000_signed_temporal_d0 as d0  # noqa: E402
from scripts.rgeo_zgeo_1ms_nr1_qualification import _source  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    OneMsNR1SafetyEnvelope,
    assert_exact_slew,
    build_frozen_one_ms_prefixes,
    card15_target_decimal_a,
    quantize_target,
    validate_one_ms_config,
)
from tsc_rzip_rllib.control.rgeo_zgeo_contract import ContractError, RGeoZGeoSignal  # noqa: E402
from tsc_rzip_rllib.core.runner import TSCConfig, TSCStepRunner  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-1000-joint-allocator-authority-g2-v1"
CONFIG_SHA256 = "0582af5e37459ba6d6bfc39260eaebdd06356cb0d8299b6a071f49e6cfb02e52"
DEFAULT_CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_joint_allocator_authority_g2.json"
InputIntegrityError = g0.InputIntegrityError


def load(config_path: Path) -> tuple[dict[str, Any], TSCConfig, dict[str, Any]]:
    config_path = b0.inside_root(config_path, "G2 config")
    if b0.sha256(config_path) != CONFIG_SHA256:
        raise InputIntegrityError("G2 config SHA-256 mismatch")
    stage = json.loads(config_path.read_text(encoding="utf-8"))
    exact = {
        "schema_version": SCHEMA,
        "campaign_id": "rgeo_zgeo_1ms_1000_joint_allocator_authority_g2_v1",
        "takeover_time_ms": 1000,
        "control_period_ms": 1,
        "horizon_steps": 64,
        "rollout_ids": ["matched_q0", "radial_only", "path_pos_neg", "path_neg_pos", "path_pos_neg_replay"],
        "rollouts": 5,
        "maximum_reset_calls": 5,
        "maximum_advance_attempts": 320,
        "maximum_gotsc_calls": 320,
        "maximum_verified_plant_advances": 320,
        "retry_after_any_advance_attempt": "forbidden",
        "design_path": "docs/codex/reports/RGEO_ZGEO_1MS_1000_JOINT_ALLOCATOR_AUTHORITY_G2_DESIGN.md",
        "design_sha256": "4cd66d9f11a1f6dbf2fba6ac252baceae41c4a7b9be958f737bace35df30f029",
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise InputIntegrityError(f"G2 frozen field mismatch: {key}")
    design = b0.inside_root(ROOT / stage["design_path"], "G2 design")
    if b0.sha256(design) != stage["design_sha256"]:
        raise InputIntegrityError("G2 design hash mismatch")
    expected_lattice = {
        "radial_single_turn_increment_a": 0.14,
        "vertical_single_turn_increment_a": 0.07,
        "minimum_radial_level": -4,
        "maximum_radial_level": 32,
        "minimum_vertical_level": -4,
        "maximum_vertical_level": 4,
        "maximum_coordinate_change_per_issue": 1,
        "maximum_exact_issued_slew_a": 0.25,
        "maximum_hard_observed_slew_a": 0.3,
        "minimum_nominal_readback_reserve_a": 0.05,
        "silent_clipping": "forbidden",
        "axis_signs_tsc_order": {
            "even": [1] * 14,
            "odd": [1, 1, 1, -1, -1, -1, 1, -1, 1, -1, 1, -1, 1, -1],
        },
    }
    if stage.get("lattice") != expected_lattice:
        raise InputIntegrityError("G2 lattice contract changed")
    if stage.get("radial_policy") != {
        "initial_minus_depth": 4,
        "earliest_switch_issue": 4,
        "latest_switch_issue": 8,
        "switch_inward_source_displacement_mm": 1.0,
        "brake_increment_levels_per_issue": 1,
        "final_plus_level": 32,
        "future_tsc": "forbidden",
    }:
        raise InputIntegrityError("G2 radial policy changed")
    if stage.get("vertical_policy") != {
        "decision_issues": [8, 28],
        "endpoint_states": [16, 36],
        "waypoints_z_source_mm": {
            "path_pos_neg": [0.45, -0.45],
            "path_neg_pos": [-0.45, 0.45],
        },
        "macro_absolute_levels": [1, 2, 3, 4, 4, 4, 4, 4, 3, 2, 1, 0],
        "selection": "sign_of_current_exact_z_waypoint_error",
        "tie_break": "positive",
        "future_tsc": "forbidden",
    }:
        raise InputIntegrityError("G2 vertical policy changed")
    roles = stage.get("data_roles", {})
    if roles != {
        "matched_q0": "authority_reference_zero_fit_weight",
        "primary_active_paths": "authority_qualification_only_zero_fit_weight",
        "critical_replay": "integrity_only_zero_fit_weight",
        "prior_evidence": "consumed_design_evidence_zero_fit_for_g2",
        "calibration": "unopened",
        "holdout": "unopened",
        "controller_expert_bc_dagger_rl": "forbidden",
    }:
        raise InputIntegrityError("G2 data roles changed")
    base = b0.inside_root(ROOT / stage["base_tsc_config"], "G2 base config")
    if b0.sha256(base) != stage["base_tsc_config_sha256"]:
        raise InputIntegrityError("G2 base config hash mismatch")
    evidence: dict[str, Any] = {}
    for label, row in stage["prior_evidence"].items():
        path = b0.inside_root(ROOT / row["path"], f"G2 evidence {label}")
        if not path.is_file() or b0.sha256(path) != row["sha256"]:
            raise InputIntegrityError(f"G2 evidence hash mismatch: {label}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if "route" in row and payload.get("route") != row["route"]:
            raise InputIntegrityError(f"G2 evidence route mismatch: {label}")
        evidence[label] = payload
    if evidence["b0_primary"].get("passed") is not True or len(evidence["b0_primary"].get("states", ())) != 65:
        raise InputIntegrityError("G2 B0 reference incomplete")
    if evidence["d1_result"].get("passed") is not True or evidence["d1_independent"].get("passed") is not True:
        raise InputIntegrityError("G2 D1 evidence changed")
    if evidence["g0_result"].get("passed") is not False or evidence["g0_independent"].get("passed") is not True:
        raise InputIntegrityError("G2 G0 evidence changed")
    if evidence["n0_result"].get("passed") is not False or evidence["n0_independent"].get("passed") is not True:
        raise InputIntegrityError("G2 N0 evidence changed")
    if evidence["g1_result"].get("passed") is not False or evidence["g1_forensic"].get("passed") is not True:
        raise InputIntegrityError("G2 G1 evidence changed")
    cfg = TSCConfig.from_json(base)
    validate_one_ms_config(
        start_folder=cfg.start_folder,
        dt_ms=cfg.dt_ms,
        slew_a_per_ms=cfg.current_slew_a_per_ms,
        expected_start_folder="1000ms",
    )
    return stage, cfg, evidence


def targets(stage: Mapping[str, Any], cfg: TSCConfig, source: Mapping[str, Any]) -> dict[str, Any]:
    frozen = build_frozen_one_ms_prefixes(
        source_current_a_tsc=source["currents_a_tsc"],
        source_command_a_tsc=source["active_command_decimal_a_tsc"],
        turns_tsc=cfg.turns_tsc,
        min_current_a_tsc=cfg.min_current_a_tsc,
        max_current_a_tsc=cfg.max_current_a_tsc,
        maximum_command_delta_a=Decimal("0.299"),
    )
    q0 = frozen.q0
    center = card15_target_decimal_a(q0, cfg.turns_tsc, name="g2.q0")
    if tuple(center) != tuple(source["active_command_decimal_a_tsc"]):
        raise ContractError("G2 q0 is not the semantic source command")
    lattice = stage["lattice"]
    radial_increment = Decimal(str(lattice["radial_single_turn_increment_a"]))
    vertical_increment = Decimal(str(lattice["vertical_single_turn_increment_a"]))
    odd = lattice["axis_signs_tsc_order"]["odd"]
    cells: dict[tuple[int, int], Any] = {}
    exact_cells: dict[tuple[int, int], tuple[Decimal, ...]] = {}
    for radial in range(lattice["minimum_radial_level"], lattice["maximum_radial_level"] + 1):
        for vertical in range(lattice["minimum_vertical_level"], lattice["maximum_vertical_level"] + 1):
            desired = [float(base + radial_increment * radial + vertical_increment * vertical * sign)
                       for base, sign in zip(center, odd)]
            target = quantize_target(desired, cfg.turns_tsc)
            exact = card15_target_decimal_a(target, cfg.turns_tsc, name=f"g2.cell.{radial}.{vertical}")
            if any(value < Decimal(str(low)) or value > Decimal(str(high))
                   for value, low, high in zip(exact, cfg.min_current_a_tsc, cfg.max_current_a_tsc)):
                raise ContractError(f"G2 cell {(radial, vertical)} exceeds absolute current")
            cells[(radial, vertical)] = target
            exact_cells[(radial, vertical)] = exact
    if tuple(exact_cells[(0, 0)]) != tuple(center):
        raise ContractError("G2 lattice center does not exactly equal q0")
    maximum = 0.0
    transition_count = 0
    for (radial, vertical), left in exact_cells.items():
        for dr in (-1, 0, 1):
            for dz in (-1, 0, 1):
                other = (radial + dr, vertical + dz)
                if (dr == 0 and dz == 0) or other not in exact_cells:
                    continue
                transition_count += 1
                maximum = max(maximum, assert_exact_slew(left, exact_cells[other], name="g2.lattice.transition"))
    if maximum > lattice["maximum_exact_issued_slew_a"]:
        raise ContractError("G2 exact lattice transition exceeds issued reserve cap")
    columns = np.column_stack([
        np.asarray([float(value - base) for value, base in zip(exact_cells[(1, 0)], center)]),
        np.asarray([float(value - base) for value, base in zip(exact_cells[(0, 1)], center)]),
    ])
    singular = np.linalg.svd(columns, compute_uv=False)
    return {
        "q0": q0,
        "cells": cells,
        "exact_cells": exact_cells,
        "action_geometry": {
            "rank": int(np.linalg.matrix_rank(columns)),
            "singular_values_a": singular.tolist(),
            "condition": float(singular[0] / singular[-1]),
            "maximum_exact_adjacent_slew_a": maximum,
            "minimum_nominal_readback_reserve_a": lattice["maximum_hard_observed_slew_a"] - maximum,
            "cell_count": len(cells),
            "directed_transition_count": transition_count,
        },
    }


def rollout_specs(stage: Mapping[str, Any]) -> list[dict[str, Any]]:
    result = [
        {"rollout_id": "matched_q0", "family_id": "matched_q0", "kind": "matched_q0",
         "path": None, "repeat_index": 0, "data_role": stage["data_roles"]["matched_q0"]},
        {"rollout_id": "radial_only", "family_id": "radial_only", "kind": "active",
         "path": None, "repeat_index": 0, "data_role": stage["data_roles"]["primary_active_paths"]},
        {"rollout_id": "path_pos_neg", "family_id": "path_pos_neg", "kind": "active",
         "path": "path_pos_neg", "repeat_index": 0, "data_role": stage["data_roles"]["primary_active_paths"]},
        {"rollout_id": "path_neg_pos", "family_id": "path_neg_pos", "kind": "active",
         "path": "path_neg_pos", "repeat_index": 0, "data_role": stage["data_roles"]["primary_active_paths"]},
        {"rollout_id": "path_pos_neg_replay", "family_id": "path_pos_neg", "kind": "active",
         "path": "path_pos_neg", "repeat_index": 1, "data_role": stage["data_roles"]["critical_replay"]},
    ]
    if [row["rollout_id"] for row in result] != stage["rollout_ids"]:
        raise InputIntegrityError("G2 rollout matrix changed")
    return result


def radial_levels_for_switch(stage: Mapping[str, Any], switch_issue: int) -> list[int]:
    policy = stage["radial_policy"]
    if not policy["earliest_switch_issue"] <= switch_issue <= policy["latest_switch_issue"]:
        raise ValueError("G2 switch issue outside frozen range")
    levels: list[int] = []
    radial = 0
    for issue in range(stage["horizon_steps"]):
        if issue < policy["initial_minus_depth"]:
            radial -= 1
        elif issue >= switch_issue and radial < policy["final_plus_level"]:
            radial += policy["brake_increment_levels_per_issue"]
        levels.append(radial)
    return levels


def vertical_levels(stage: Mapping[str, Any], signs: Sequence[int]) -> list[int]:
    levels = [0] * stage["horizon_steps"]
    profile = stage["vertical_policy"]["macro_absolute_levels"]
    if len(signs) != len(stage["vertical_policy"]["decision_issues"]):
        raise ValueError("G2 vertical sign count changed")
    for issue0, sign in zip(stage["vertical_policy"]["decision_issues"], signs):
        if sign not in (-1, 0, 1):
            raise ValueError("G2 vertical sign must be -1, 0, or +1")
        for offset, level in enumerate(profile):
            levels[issue0 + offset] = sign * level
    return levels


def static_action_stream(
    stage: Mapping[str, Any], cfg: TSCConfig, source: Mapping[str, Any], target_map: Mapping[str, Any],
    switch_issue: int, signs: Sequence[int], name: str,
) -> list[dict[str, Any]]:
    radial = radial_levels_for_switch(stage, switch_issue)
    vertical = vertical_levels(stage, signs)
    previous = tuple(source["active_command_decimal_a_tsc"])
    result = []
    for issue, (r_level, z_level) in enumerate(zip(radial, vertical)):
        target = target_map["cells"][(r_level, z_level)]
        exact = target_map["exact_cells"][(r_level, z_level)]
        maximum = assert_exact_slew(previous, exact, name=f"g2.static.{name}.{issue}")
        result.append({
            "issue_step": issue,
            "effect_state_index": issue + 1,
            "radial_level": r_level,
            "vertical_level": z_level,
            "maximum_issued_delta_a": maximum,
            "expected_card15_fields": list(target.card15_fields),
        })
        previous = exact
    if (radial[-1], vertical[-1]) != tuple(stage["scientific_gates"]["final_active_levels"]):
        raise ContractError("G2 static branch does not end at frozen final levels")
    return result


def offline(config_path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    stage = None
    geometry = streams = None
    try:
        stage, cfg, _ = load(config_path)
        source = _source(cfg)
        envelope = OneMsNR1SafetyEnvelope.from_signal(RGeoZGeoSignal.from_tsc_state(source))
        failures.extend(envelope.state_reasons(
            RGeoZGeoSignal.from_tsc_state(source), source["currents_a_tsc"],
            cfg.min_current_a_tsc, cfg.max_current_a_tsc,
        ))
        target_map = targets(stage, cfg, source)
        geometry = target_map["action_geometry"]
        streams = []
        for switch_issue in range(stage["radial_policy"]["earliest_switch_issue"],
                                  stage["radial_policy"]["latest_switch_issue"] + 1):
            streams.append({"branch": f"radial_s{switch_issue}", "actions": static_action_stream(
                stage, cfg, source, target_map, switch_issue, (0, 0), f"radial_s{switch_issue}")})
            for signs in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                streams.append({"branch": f"joint_s{switch_issue}_{signs[0]}_{signs[1]}",
                                "actions": static_action_stream(
                                    stage, cfg, source, target_map, switch_issue, signs,
                                    f"joint_s{switch_issue}_{signs[0]}_{signs[1]}")})
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    failures = list(dict.fromkeys(failures))
    routes = (stage or {}).get("routes", {})
    return {
        "schema_version": SCHEMA,
        "kind": "offline_preflight",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_revision": source_revision,
        "passed": not failures,
        "route": routes.get("offline_pass") if not failures else routes.get(
            "offline_fail", "ONE_MS_NR1000G2_OFFLINE_FAIL_NO_TSC"),
        "failures": failures,
        "authorized_reset_calls": 5,
        "authorized_plant_advances": 320,
        "action_geometry": geometry,
        "enumerated_branch_streams": streams,
    }


def _next_radial_level(
    stage: Mapping[str, Any], issue: int, current_level: int, phase: str,
    current_r_m: float, source_r_m: float,
) -> tuple[int, str, bool, float]:
    policy = stage["radial_policy"]
    inward_mm = (source_r_m - current_r_m) * 1000.0
    switched = False
    if issue < policy["initial_minus_depth"]:
        return current_level - 1, "initial_minus", False, inward_mm
    if phase in ("initial_minus", "await_switch"):
        phase = "await_switch"
        if (issue >= policy["earliest_switch_issue"] and
                (inward_mm >= policy["switch_inward_source_displacement_mm"]
                 or issue >= policy["latest_switch_issue"])):
            phase = "brake"
            switched = True
    if phase == "brake" and current_level < policy["final_plus_level"]:
        current_level += policy["brake_increment_levels_per_issue"]
        if current_level == policy["final_plus_level"]:
            phase = "hold_final"
    return current_level, phase, switched, inward_mm


def _run_one(
    cfg: TSCConfig, stage: Mapping[str, Any], spec: Mapping[str, Any],
    target_map: Mapping[str, Any], envelope: OneMsNR1SafetyEnvelope,
    source_reference: Mapping[str, Any],
) -> dict[str, Any]:
    runner = TSCStepRunner(cfg, worker_id=f"nr1000_g2_{spec['rollout_id']}", keep_workspace=False)
    reasons: list[str] = []
    states: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    attempts = gotsc_calls = verified = reset_calls = 0
    radial_level = vertical_level = 0
    radial_phase = "initial_minus"
    radial_switch_issue: int | None = None
    vertical_signs: dict[int, int] = {}
    started = time.perf_counter()
    try:
        reset_calls = 1
        live = runner.reset(episode_name=spec["rollout_id"])
        states.append(d0._record(cfg, live))
        reasons.extend(d0.source_mismatch_reasons(states[0], source_reference))
        source_r_m = states[0]["r_geo_m"]
        source_z_m = states[0]["z_geo_m"]
        origin_time = states[0]["time_ms"]
        for issue in range(stage["horizon_steps"]):
            reasons.extend(envelope.state_reasons(
                RGeoZGeoSignal.from_tsc_state(live), live["currents_a_tsc"],
                cfg.min_current_a_tsc, cfg.max_current_a_tsc,
            ))
            if spec["kind"] == "matched_q0":
                next_radial, next_vertical = 0, 0
                inward_mm = (source_r_m - states[-1]["r_geo_m"]) * 1000.0
            else:
                next_radial, radial_phase, switched, inward_mm = _next_radial_level(
                    stage, issue, radial_level, radial_phase, states[-1]["r_geo_m"], source_r_m
                )
                if switched:
                    radial_switch_issue = issue
                next_vertical = 0
                if spec["path"] is not None:
                    for ordinal, decision_issue in enumerate(stage["vertical_policy"]["decision_issues"]):
                        if issue == decision_issue:
                            target_z_mm = stage["vertical_policy"]["waypoints_z_source_mm"][spec["path"]][ordinal]
                            current_z_mm = (states[-1]["z_geo_m"] - source_z_m) * 1000.0
                            sign = 1 if target_z_mm - current_z_mm >= 0 else -1
                            vertical_signs[decision_issue] = sign
                            decisions.append({
                                "ordinal": ordinal,
                                "issue_step": issue,
                                "endpoint_state": stage["vertical_policy"]["endpoint_states"][ordinal],
                                "target_z_source_mm": target_z_mm,
                                "current_z_source_mm": current_z_mm,
                                "selected_vertical_sign": sign,
                            })
                    for decision_issue, sign in vertical_signs.items():
                        offset = issue - decision_issue
                        if 0 <= offset < len(stage["vertical_policy"]["macro_absolute_levels"]):
                            next_vertical = sign * stage["vertical_policy"]["macro_absolute_levels"][offset]
            target = target_map["cells"][(next_radial, next_vertical)]
            exact = target_map["exact_cells"][(next_radial, next_vertical)]
            maximum = assert_exact_slew(
                states[-1]["active_command_decimal_a_tsc"], exact,
                name=f"g2.{spec['rollout_id']}.issued.{issue}",
            )
            if maximum > stage["lattice"]["maximum_exact_issued_slew_a"]:
                reasons.append(f"ISSUED_RESERVE:{issue}")
            if reasons:
                break
            actions.append({
                "issue_step": issue,
                "issue_time_ms": int(live["time_ms"]),
                "effect_state_index": issue + 1,
                "effect_time_ms": origin_time + issue + 1,
                "radial_level": next_radial,
                "vertical_level": next_vertical,
                "radial_phase": radial_phase,
                "inward_source_displacement_mm": inward_mm,
                "maximum_issued_delta_a": maximum,
                "expected_card15_fields": list(target.card15_fields),
            })
            radial_level, vertical_level = next_radial, next_vertical
            attempts += 1
            live = runner.step_current_a(np.asarray(target.current_a_tsc, dtype=float))
            gotsc_calls += 1
            record = d0._record(cfg, live)
            states.append(record)
            if int(live.get("returncode", 0)) != 0:
                reasons.append(f"TSC_RETURNCODE:{issue}:{live.get('returncode')}")
            if bool(live.get("abnormal", False)):
                reasons.append(f"TSC_ABNORMAL:{issue}:{live.get('done_reason', '')}")
            if record["time_ms"] != origin_time + issue + 1:
                reasons.append(f"TIME:{issue}")
            else:
                verified += 1
            if tuple(record["active_command_card15_fields"]) != tuple(target.card15_fields):
                reasons.append(f"CARD15:{issue}")
            if issue == 0:
                record["observed_delta_role"] = "source_bias_descriptive_matched_hold_reference"
            else:
                record["maximum_observed_delta_a"] = assert_exact_slew(
                    states[-2]["actual_current_decimal_a_tsc"],
                    record["actual_current_decimal_a_tsc"],
                    name=f"g2.{spec['rollout_id']}.observed.{issue}",
                )
            reasons.extend(envelope.state_reasons(
                RGeoZGeoSignal.from_tsc_state(live), live["currents_a_tsc"],
                cfg.min_current_a_tsc, cfg.max_current_a_tsc,
            ))
            if reasons:
                break
    except Exception as exc:
        reasons.append(f"EXECUTION:{type(exc).__name__}:{exc}")
    finally:
        try:
            runner.cleanup_runtime_workspace()
        except Exception as exc:
            reasons.append(f"CLEANUP:{type(exc).__name__}:{exc}")
    reasons = list(dict.fromkeys(reasons))
    expected_decisions = 0 if spec["path"] is None else 2
    final_levels = [radial_level, vertical_level]
    complete = (
        not reasons
        and reset_calls == 1
        and attempts == gotsc_calls == verified == stage["horizon_steps"]
        and len(states) == 65
        and len(actions) == 64
        and len(decisions) == expected_decisions
        and (spec["kind"] == "matched_q0" or final_levels == stage["scientific_gates"]["final_active_levels"])
    )
    return {
        **spec,
        "passed": complete,
        "reasons": reasons,
        "reset_calls": reset_calls,
        "advance_attempts": attempts,
        "gotsc_calls": gotsc_calls,
        "verified_plant_advances": verified,
        "radial_switch_issue": radial_switch_issue,
        "final_levels": final_levels,
        "decisions": decisions,
        "states": states,
        "actions": actions,
        "wall_time_s": time.perf_counter() - started,
    }


def compare_rows(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    comparison = g0.compare_rows(dict(left), dict(right))
    failures = list(comparison["failures"])
    if left.get("radial_switch_issue") != right.get("radial_switch_issue"):
        failures.append("RADIAL_SWITCH")
    if left.get("decisions") != right.get("decisions"):
        failures.append("DECISIONS")
    if left.get("final_levels") != right.get("final_levels"):
        failures.append("FINAL_LEVELS")
    comparison["failures"] = list(dict.fromkeys(failures))
    comparison["passed"] = not comparison["failures"]
    return comparison


def scientific_metrics(rows: Sequence[dict[str, Any]], stage: Mapping[str, Any]) -> dict[str, Any]:
    by_id = {row["rollout_id"]: row for row in rows}
    gates = stage["scientific_gates"]
    baseline = g0._window_metrics(
        by_id["matched_q0"]["states"], gates["terminal_state_start"], gates["terminal_state_end"]
    )
    utility_rows = []
    utility_pass = True
    for rollout_id in ("radial_only", "path_pos_neg", "path_neg_pos"):
        metrics = g0._window_metrics(
            by_id[rollout_id]["states"], gates["terminal_state_start"], gates["terminal_state_end"]
        )
        distance_gain = 1.0 - metrics["maximum_source_distance_mm"] / baseline["maximum_source_distance_mm"]
        speed_gain = baseline["maximum_speed_m_per_s"] - metrics["maximum_speed_m_per_s"]
        passed = (
            distance_gain >= gates["minimum_terminal_worst_source_distance_improvement_fraction"]
            and speed_gain >= gates["minimum_terminal_max_speed_improvement_m_per_s"]
            and metrics["maximum_ip_source_fraction"] <= gates["maximum_terminal_ip_source_fraction"]
        )
        utility_pass &= passed
        utility_rows.append({
            "rollout_id": rollout_id,
            **metrics,
            "source_distance_improvement_fraction": distance_gain,
            "speed_improvement_m_per_s": speed_gain,
            "passed": passed,
        })
    vertical_rows = []
    vertical_pass = True
    for rollout_id in ("path_pos_neg", "path_neg_pos"):
        row = by_id[rollout_id]
        source_z = row["states"][0]["z_geo_m"]
        for decision in row["decisions"]:
            endpoint_z = (row["states"][decision["endpoint_state"]]["z_geo_m"] - source_z) * 1000.0
            before_error = abs(decision["target_z_source_mm"] - decision["current_z_source_mm"])
            endpoint_error = abs(decision["target_z_source_mm"] - endpoint_z)
            progress = before_error - endpoint_error
            passed = (
                endpoint_error <= gates["maximum_vertical_endpoint_error_mm"]
                and progress >= gates["minimum_vertical_acquisition_progress_mm"]
            )
            vertical_pass &= passed
            vertical_rows.append({
                "rollout_id": rollout_id,
                "ordinal": decision["ordinal"],
                "endpoint_state": decision["endpoint_state"],
                "target_z_source_mm": decision["target_z_source_mm"],
                "endpoint_z_source_mm": endpoint_z,
                "endpoint_error_mm": endpoint_error,
                "acquisition_progress_mm": progress,
                "passed": passed,
            })
    mirror_rows = []
    mirror_pass = True
    positive = by_id["path_pos_neg"]
    negative = by_id["path_neg_pos"]
    source_z = positive["states"][0]["z_geo_m"]
    for ordinal, state_index in enumerate(stage["vertical_policy"]["endpoint_states"]):
        pos_z = (positive["states"][state_index]["z_geo_m"] - source_z) * 1000.0
        neg_z = (negative["states"][state_index]["z_geo_m"] - source_z) * 1000.0
        separation = abs(pos_z - neg_z)
        ordering = pos_z > neg_z if ordinal == 0 else pos_z < neg_z
        passed = ordering and separation >= gates["minimum_mirror_endpoint_separation_mm"]
        mirror_pass &= passed
        mirror_rows.append({
            "ordinal": ordinal,
            "endpoint_state": state_index,
            "path_pos_neg_z_source_mm": pos_z,
            "path_neg_pos_z_source_mm": neg_z,
            "separation_mm": separation,
            "ordering_pass": ordering,
            "passed": passed,
        })
    passed = utility_pass and vertical_pass and mirror_pass
    return {
        "passed": passed,
        "matched_q0_terminal": baseline,
        "absolute_utility_pass": utility_pass,
        "vertical_acquisition_pass": vertical_pass,
        "mirror_separation_pass": mirror_pass,
        "absolute_utility": utility_rows,
        "vertical_acquisition": vertical_rows,
        "mirror_endpoints": mirror_rows,
    }


def run(config_path: Path, source_revision: str, output_dir: Path) -> dict[str, Any]:
    preflight = offline(config_path, source_revision)
    if not preflight["passed"]:
        raise RuntimeError("G2 offline gate failed; TSC forbidden")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {output_dir}")
    output_dir.mkdir(parents=True)
    b0.write_new(output_dir / "offline_preflight.json", preflight)
    stage, cfg, evidence = load(config_path)
    cfg.run_root = output_dir / "rollouts"
    source = _source(cfg)
    target_map = targets(stage, cfg, source)
    envelope = OneMsNR1SafetyEnvelope.from_signal(RGeoZGeoSignal.from_tsc_state(source))
    rows: dict[str, dict[str, Any]] = {}
    for spec in rollout_specs(stage):
        row = _run_one(
            cfg, stage, spec, target_map, envelope, evidence["b0_primary"]["states"][0]
        )
        rows[spec["rollout_id"]] = row
        b0.write_new(output_dir / f"{spec['rollout_id']}.json", row)
        if not row["passed"]:
            break
    matched = rows.get("matched_q0", {}).get("passed") is True
    execution = len(rows) == stage["rollouts"] and all(row["passed"] for row in rows.values())
    replay = compare_rows(rows["path_pos_neg"], rows["path_pos_neg_replay"]) if execution else None
    replay_pass = replay is not None and replay["passed"]
    metrics = scientific_metrics(list(rows.values()), stage) if execution else None
    science = metrics is not None and metrics["passed"]
    passed = execution and matched and replay_pass and science
    route = stage["routes"]["pass"] if passed else (
        stage["routes"]["matched_q0_fail"] if not matched
        else stage["routes"]["execution_fail"] if not execution
        else stage["routes"]["replay_fail"] if not replay_pass
        else stage["routes"]["scientific_fail"]
    )
    result = {
        "schema_version": SCHEMA,
        "kind": "authentic_fixed_1000_joint_allocator_authority",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_revision": source_revision,
        "passed": passed,
        "route": route,
        "rollout_count": len(rows),
        "reset_calls": sum(row["reset_calls"] for row in rows.values()),
        "advance_attempts": sum(row["advance_attempts"] for row in rows.values()),
        "gotsc_calls": sum(row["gotsc_calls"] for row in rows.values()),
        "verified_plant_advances": sum(row["verified_plant_advances"] for row in rows.values()),
        "matched_q0_complete": matched,
        "action_geometry": target_map["action_geometry"],
        "critical_replay": replay,
        "scientific_metrics": metrics,
        "claim_boundary": (
            "fixed-1000 finite joint-allocation Authority development only; "
            "no model, hold, recovery, Recourse, controller, or R_mid crossing"
        ),
    }
    b0.write_new(output_dir / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("offline", "run"))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = offline(args.config.resolve(), args.source_revision) if args.mode == "offline" else run(
        args.config.resolve(), args.source_revision, args.output.resolve()
    )
    if args.mode == "offline":
        b0.write_new(args.output.resolve(), result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
