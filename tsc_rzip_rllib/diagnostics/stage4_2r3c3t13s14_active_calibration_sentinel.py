#!/usr/bin/env python3
"""Stage4.2R3c3T13S14 same-trajectory active-calibration sentinel."""

from __future__ import annotations

import argparse
import copy
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path
import time
import traceback
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s13_recurrent_sequence_tube_identification as s13,
)
from tsc_rzip_rllib.utils.ray_runtime import ensure_ray_worker_plan


s9 = s13.s9
SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S14"
RUN_NAME = "stage4_2r3c3t13s14_active_calibration_sentinel"
CAMPAIGN_IDENTITY = "same_trajectory_active_calibration_sentinel_v1"
CONTROLLER_REVISION = "active_calibration_lattice_probe_v42r3c3t13s14_v1"
PACKAGE_REVISION = "r42r3c3t13s14_active_calibration_sentinel_v1"
PASS_ROUTE = "ACTIVE_CALIBRATION_SENTINEL_PASS_FULL_PARTITIONED_CAMPAIGN_REQUIRED"
FAIL_ROUTE = "ACTIVE_CALIBRATION_SENTINEL_FAIL_REDESIGN"
BASELINE_PROBE_ID = s9.BASELINE_PROBE_ID
DIRECTIONS = s9.DIRECTIONS
SIGNS = s9.SIGNS
N_COILS = s9.N_COILS
RESPONSE_FLOOR = s13.RESPONSE_FLOOR
PHASES = ("offline_ready", "baseline_complete", "probe_complete", "campaign_complete")
NON_SEMANTIC_STATE_TIMING_FIELDS = frozenset({"gotsc_subprocess_s", "step_total_s"})
PREHOTFIX_PREACTION_FAILURE_IDS = frozenset({
    "s42r3c3_24fab3975f36ed5290d7",
    "s42r3c3_d4cb50e20cbacf45225b",
    "s42r3c3_f866adad4cfb793fd1dc",
})


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _sha256(path: Path) -> str:
    return s13._sha256(path)


def _digest(value: Any) -> str:
    return s13._digest(value)


def _read_json(path: Path) -> Any:
    return s13._read_json(path)


def _write_json(path: Path, value: Any) -> None:
    s13._write_json(path, value)


def _write_json_gz(path: Path, value: Any) -> None:
    s13._write_json_gz(path, value)


@dataclass(frozen=True)
class Paths:
    run_dir: Path
    control: Path
    raw: Path
    variants: Path
    source_reference: Path
    specs: Path
    model: Path
    analysis: Path
    manifest: Path
    state: Path


def _paths(run_dir: Path) -> Paths:
    root = run_dir.expanduser().resolve()
    return Paths(
        run_dir=root,
        control=root / RUN_NAME,
        raw=root / RUN_NAME / "raw",
        variants=root / "stage4_2r3c3t13s14_environment_variants",
        source_reference=root / "stage4_2r3c3t13s14_source_reference",
        specs=root / "stage4_2r3c3t13s14_specs",
        model=root / "stage4_2r3c3t13s14_frozen_model",
        analysis=root / "stage4_2r3c3t13s14_analysis",
        manifest=root / "stage4_2r3c3t13s14_manifest.json",
        state=root / "stage4_2r3c3t13s14_state.json",
    )


@dataclass(frozen=True)
class Context:
    cfg: dict[str, Any]
    config_path: Path
    base_ctx: s13.Context
    paths: Paths


def _validate_config(cfg: Mapping[str, Any]) -> None:
    selection = cfg["selection"]
    calibration = cfg["active_calibration"]
    observer = cfg["observer"]
    matrix = cfg["control_matrix"]
    if (
        int(cfg.get("schema_version", -1)) != 1
        or cfg.get("stage") != STAGE
        or int(cfg.get("design_revision", -1)) != 1
        or cfg.get("run_name") != RUN_NAME
        or cfg.get("campaign_identity") != CAMPAIGN_IDENTITY
        or cfg.get("controller_revision") != CONTROLLER_REVISION
        or cfg.get("probe_primitive_revision") != s9.CONTROLLER_REVISION
        or cfg.get("package_revision") != PACKAGE_REVISION
    ):
        raise ValueError("T13S14 identity changed")
    expected_pairs = (
        "p5_q1_a0p600_gap2_settle4", "p5_q1_a0p600_gap4_settle4",
        "p5_q2_a0p600_gap2_settle4", "p5_q2_a0p600_gap4_settle4",
        "p9_q1_a0p600_gap2_settle4", "p9_q1_a0p600_gap4_settle4",
        "p9_q2_a0p600_gap2_settle4", "p9_q2_a0p600_gap4_settle4",
    )
    regimes = {
        row["id"]: (row["target_id"], int(row["action_delay_steps"]), float(row["slew_scale"]))
        for row in selection["regimes"]
    }
    if (
        tuple(selection["pair_ids"]) != expected_pairs
        or tuple(selection["history_members"]) != ("plus_first", "minus_first")
        or tuple(selection["assignment_cycle"]) != tuple("ABCDABCD")
        or not bool(selection["forbid_outcome_based_selection"])
        or regimes != {
            "A": ("nominal", 0, 1.0), "B": ("nominal", 2, 0.9),
            "C": ("RZ_p10_m10", 0, 1.0), "D": ("RZ_p10_m10", 2, 0.9),
        }
    ):
        raise ValueError("T13S14 prospective selection changed")
    if (
        tuple(calibration["pulse_directions"]) != DIRECTIONS
        or int(calibration["pulse_sign"]) != 1
        or tuple(map(int, calibration["issue_steps"])) != (0, 2, 4, 6)
        or tuple(map(int, calibration["cancel_steps"])) != (1, 3, 5, 7)
        or tuple(map(int, calibration["first_effect_states"])) != (1, 3, 5, 7)
        or tuple(map(int, calibration["cancel_effect_states"])) != (2, 4, 6, 8)
        or tuple(map(int, calibration["settling_steps"])) != (8, 9)
        or tuple(int(calibration[key]) for key in (
            "response_issue_step", "response_cancel_step",
            "response_first_effect_state", "response_cancel_effect_state",
            "observer_last_state",
        )) != (10, 11, 11, 12, 10)
        or not bool(calibration["schedule_is_global_constant"])
    ):
        raise ValueError("T13S14 active-calibration schedule changed")
    probe = cfg["lattice_probe"]
    if (
        tuple(probe["probe_directions"]) != DIRECTIONS
        or tuple(map(int, probe["probe_signs"])) != SIGNS
        or float(probe["maximum_incremental_normalized_action_linf"]) != 0.25
        or float(probe["maximum_total_normalized_action_abs"]) != 1.0
        or float(probe["maximum_current_utilization"]) != 0.55
        or bool(probe["probe_trajectories_allowed_in_expert_dataset"])
        or bool(probe["post_effect_current_model_input_allowed"])
    ):
        raise ValueError("T13S14 Card15 contract changed")
    if (
        int(observer["seed"]) != 20260802
        or int(observer["reservoir_width"]) != 32
        or tuple(map(float, observer["spectral_radii"])) != (0.35, 0.65, 0.85)
        or tuple(map(float, observer["leaks"])) != (0.5, 1.0)
        or tuple(map(int, observer["observer_ranks"])) != (4, 8, 12)
        or tuple(map(float, observer["ridge_values"])) != (1e-8, 1e-6, 1e-4)
        or tuple(map(float, observer["kernel_bandwidth_multipliers"])) != (0.25, 0.5, 1.0, 2.0)
        or int(observer["feature_count_per_state"]) != 59
        or int(observer["maximum_sequence_states"]) != 17
        or int(observer["action_rank"]) != 4
        or float(observer["maximum_interaction_condition_number"]) != 30.0
        or float(observer["maximum_scaled_center_relative_error"]) != 0.1
        or float(observer["near_alias_linf_atol"]) != 1e-12
    ):
        raise ValueError("T13S14 model comparison changed")
    counts = tuple(int(matrix[key]) for key in (
        "expected_contexts", "expected_baselines", "expected_signed_probes",
        "expected_rollouts", "expected_calibration_pulse_pairs",
        "expected_calibration_trace_events", "expected_zero_net_groups",
        "expected_response_trace_events",
    ))
    if counts != (16, 16, 128, 144, 576, 1152, 704, 256):
        raise ValueError("T13S14 rollout/event counts changed")
    if (
        bool(cfg["formal_timing_contract"]["arrival_deadline_expansion_allowed"])
        or not bool(cfg["identification_only"])
        or bool(cfg["fresh_holdout_required"])
        or bool(cfg["bc_dagger_or_rl_allowed"])
    ):
        raise ValueError("T13S14 scientific route changed")


def load_config(
    config_path: Path, *, source_stage42r3b_run: Path,
    source_stage42r3c3_run: Path, source_stage42r3c3_bank_dir: Path,
    source_stage42r3c3t1_run: Path, source_stage42r3c3t1_audit_dir: Path,
    source_stage42r3c3t3_controller_bank: Path, q1_run: Path, q2_run: Path,
    q1_audit: Path, q2_audit: Path, r3b_server_audit: Path,
    r3b_snapshot_checks: Path, run_dir: Path,
) -> Context:
    path = config_path.expanduser().resolve()
    cfg = _read_json(path)
    _validate_config(cfg)
    base_path = (_project_root() / str(cfg["base_stage_config"])).resolve()
    if not base_path.is_file() or _sha256(base_path) != cfg["base_stage_config_sha256"]:
        raise ValueError("T13S14 base S13 config mismatch")
    base = s13.load_config(
        base_path,
        source_stage42r3b_run=source_stage42r3b_run,
        source_stage42r3c3_run=source_stage42r3c3_run,
        source_stage42r3c3_bank_dir=source_stage42r3c3_bank_dir,
        source_stage42r3c3t1_run=source_stage42r3c3t1_run,
        source_stage42r3c3t1_audit_dir=source_stage42r3c3t1_audit_dir,
        source_stage42r3c3t3_controller_bank=source_stage42r3c3t3_controller_bank,
        q1_run=q1_run, q2_run=q2_run, q1_audit=q1_audit, q2_audit=q2_audit,
        r3b_server_audit=r3b_server_audit,
        r3b_snapshot_checks=r3b_snapshot_checks, run_dir=run_dir,
    )
    return Context(cfg=cfg, config_path=path, base_ctx=base, paths=_paths(run_dir))


def build_context_table(ctx: Context) -> list[dict[str, Any]]:
    source = s13.build_context_table(ctx.base_ctx)
    by_key = {(str(row["pair_id"]), str(row["history_member"])): row for row in source}
    regimes = {row["id"]: row for row in ctx.cfg["selection"]["regimes"]}
    output = []
    for pair_index, pair in enumerate(ctx.cfg["selection"]["pair_ids"]):
        regime_id = str(ctx.cfg["selection"]["assignment_cycle"][pair_index])
        regime = regimes[regime_id]
        for member in ctx.cfg["selection"]["history_members"]:
            row = copy.deepcopy(by_key[(str(pair), str(member))])
            row.update({
                "partition": "sentinel", "consumed_training": False,
                "regime_id": regime_id, "target_id": regime["target_id"],
                "action_delay_steps": int(regime["action_delay_steps"]),
                "slew_scale": float(regime["slew_scale"]),
            })
            output.append(row)
    if len(output) != 16 or len({(r["pair_id"], r["history_member"]) for r in output}) != 16:
        raise ValueError("T13S14 context coverage mismatch")
    return output


def build_specs(ctx: Context, table: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    templates = s13._source_templates(ctx.base_ctx)
    calibration = ctx.cfg["active_calibration"]
    specs = []
    for row in table:
        key = (str(row["target_id"]), int(row["action_delay_steps"]), float(row["slew_scale"]))
        horizon = s13._formal_horizon(float(row["slew_scale"]))
        members = [(BASELINE_PROBE_ID, "", 0)] + [
            (f"lattice_transport_{direction}", direction, sign)
            for direction in DIRECTIONS for sign in SIGNS
        ]
        for probe_id, direction, sign in members:
            baseline = probe_id == BASELINE_PROBE_ID
            identity = {
                "stage": STAGE, "campaign_identity": CAMPAIGN_IDENTITY,
                "pair_id": row["pair_id"], "history_member": row["history_member"],
                "state_generation_experiment_id": row["state_generation_experiment_id"],
                "snapshot_manifest_digest": row["restart_snapshot_manifest_digest"],
                "target_id": row["target_id"], "delay": row["action_delay_steps"],
                "slew": row["slew_scale"], "probe_id": probe_id,
                "probe_sign": sign, "controller_revision": CONTROLLER_REVISION,
            }
            experiment_id = s9.t11.t1.r3c3._scenario_digest(identity)
            spec = copy.deepcopy(templates[key])
            spec.update({
                "kind": "stage4_2r3c3t13s14_active_calibration_sentinel",
                "stage": STAGE, "campaign_identity": CAMPAIGN_IDENTITY,
                "controller_revision": CONTROLLER_REVISION,
                "underlying_controller_revision": s9.t11.t1.r3c1.CONTROLLER_REVISION,
                "probe_primitive_revision": s9.CONTROLLER_REVISION,
                "experiment_id": experiment_id,
                "phase": "same_trajectory_active_calibration_sentinel",
                "category": "identification_only_active_calibration_sentinel",
                "pair_id": str(row["pair_id"]),
                "history_member": str(row["history_member"]),
                "state_generation_experiment_id": str(row["state_generation_experiment_id"]),
                "restart_snapshot_dir": str(row["restart_snapshot_dir"]),
                "restart_snapshot_manifest_digest": str(row["restart_snapshot_manifest_digest"]),
                "baseline_experiment_id": "", "environment_variant": f"stage4_2r3c3t13s14_{experiment_id}",
                "horizon_steps": horizon, "formal_horizon_steps": horizon,
                "identification_only": True,
                "r3c3_probe_id": probe_id,
                "r3c3_probe_window": "baseline" if baseline else "transport",
                "r3c3_probe_direction": direction,
                "r3c3_probe_sign": sign,
                "r3c3_probe_issue_step": -1 if baseline else int(calibration["response_issue_step"]),
                "r3c3_probe_cancel_step": -1 if baseline else int(calibration["response_cancel_step"]),
                "r3c3_probe_first_effect_state": -1 if baseline else int(calibration["response_first_effect_state"]),
                "r3c3_probe_cancel_effect_state": -1 if baseline else int(calibration["response_cancel_effect_state"]),
                "r3c3t13s9_schedule_contract": "s14_fixed_postqueue_active_calibration_response_v1",
                "r3c3t13s9_offline_role": "sentinel",
                "r3c3t13s9_stratum": "normal" if int(row["action_delay_steps"]) == 0 else "weak",
                "r3c3t13s9_source_r3c1_experiment_id": "",
                "s14_response_role": "baseline" if baseline else "active_response",
                "probe_trajectory_allowed_in_expert_dataset": False,
                "pair_or_history_label_available_to_controller": False,
                "source_result_available_to_controller": False,
                "source_action_available_to_controller": False,
                "source_coil_current_available_to_controller": False,
                "source_wire_current_available_to_controller": False,
                "hidden_wire_current_available_to_controller": False,
                "future_action_count": 0, "future_measurement_count": 0,
                "online_action_computation_required": True,
                "task_clock_starts_at_zero": True, "formal_timing_unchanged": True,
            })
            specs.append(spec)
    if len(specs) != 144 or len({str(row["experiment_id"]) for row in specs}) != 144:
        raise ValueError("T13S14 spec coverage mismatch")
    return specs


def _baseline_specs(specs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    output = [copy.deepcopy(dict(row)) for row in specs if row["r3c3_probe_id"] == BASELINE_PROBE_ID]
    if len(output) != 16:
        raise ValueError("T13S14 baseline spec coverage mismatch")
    return output


def _probe_specs(specs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    output = [copy.deepcopy(dict(row)) for row in specs if row["r3c3_probe_id"] != BASELINE_PROBE_ID]
    if len(output) != 128:
        raise ValueError("T13S14 response spec coverage mismatch")
    return output


def _nearest_exact_symmetric_count(
    center: Decimal, step: Decimal, nominal_count: int, *, search_radius: int = 8,
) -> tuple[int, str, str]:
    sign = 1 if nominal_count >= 0 else -1
    offsets = [0]
    for distance in range(1, search_radius + 1):
        offsets.extend((-sign * distance, sign * distance))
    for offset in offsets:
        count = nominal_count + offset
        if nominal_count > 0 and count < 0:
            continue
        if nominal_count < 0 and count > 0:
            continue
        delta = step * count
        plus, minus = center + delta, center - delta
        plus_field = s9.format_number(float(plus))
        minus_field = s9.format_number(float(minus))
        if bool(
            len(plus_field) == len(minus_field) == 10
            and s9._decimal_field(plus_field) == plus
            and s9._decimal_field(minus_field) == minus
            and s9._decimal_field(plus_field) - center
            == center - s9._decimal_field(minus_field)
        ):
            return count, plus_field, minus_field
    raise ValueError(
        f"T13S14 no nearby exact symmetric count for center={center} "
        f"step={step} nominal={nominal_count}"
    )


def _choose_exact_symmetric_displacement(
    *, center_fields: Sequence[str], measured_current_a_tsc: Sequence[float],
    baseline_action_norm_tsc: Sequence[float], mode_vector_tsc: Sequence[float],
    turns_tsc: Sequence[float], max_slew_step_a: float,
    minimum_current_a_tsc: Sequence[float], maximum_current_a_tsc: Sequence[float],
    cfg: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        plan = s9.choose_lattice_displacement(
            center_fields=center_fields,
            measured_current_a_tsc=measured_current_a_tsc,
            baseline_action_norm_tsc=baseline_action_norm_tsc,
            mode_vector_tsc=mode_vector_tsc, turns_tsc=turns_tsc,
            max_slew_step_a=max_slew_step_a,
            minimum_current_a_tsc=minimum_current_a_tsc,
            maximum_current_a_tsc=maximum_current_a_tsc, cfg=cfg,
        )
        plan["t13s14_nearest_exact_count_repair"] = False
        plan["t13s14_nominal_integer_grid_steps_tsc"] = list(plan["integer_grid_steps_tsc"])
        plan["t13s14_integer_count_repairs_tsc"] = [0] * N_COILS
        return plan
    except ValueError as original:
        if "no frozen T13S9 lattice multiplier passed" not in str(original):
            raise
    centers = tuple(s9._decimal_field(field) for field in center_fields)
    steps = tuple(s9.local_symmetric_card15_step(field) for field in center_fields)
    current = np.asarray(measured_current_a_tsc, dtype=float).reshape(N_COILS)
    baseline = np.asarray(baseline_action_norm_tsc, dtype=float).reshape(N_COILS)
    mode = np.asarray(mode_vector_tsc, dtype=float).reshape(N_COILS)
    turns = np.asarray(turns_tsc, dtype=float).reshape(N_COILS)
    minimum = np.asarray(minimum_current_a_tsc, dtype=float).reshape(N_COILS)
    maximum = np.asarray(maximum_current_a_tsc, dtype=float).reshape(N_COILS)
    step_a = np.asarray([float(value) for value in steps]) * 1000.0 / turns
    significant = np.abs(mode) >= float(cfg["significant_mode_fraction"]) * float(np.max(np.abs(mode)))
    if not np.any(significant):
        raise ValueError("T13S14 exact-symmetric mode has no significant coil")
    lambda_min = float(np.max(
        int(cfg["minimum_significant_grid_steps"]) * step_a[significant]
        / np.abs(mode[significant])
    ))
    mode_norm = float(np.linalg.norm(mode))
    if not math.isclose(mode_norm, 1.0, rel_tol=0.0, abs_tol=1e-10):
        raise ValueError("T13S14 exact-symmetric mode vector is not unit length")
    candidate_rows = []
    for multiplier in map(int, cfg["lambda_multipliers"]):
        lam = lambda_min * multiplier
        nominal = np.rint(lam * mode / step_a).astype(np.int64)
        repaired, plus_fields, minus_fields = [], [], []
        exact_counts = True
        for center, step, count in zip(centers, steps, nominal):
            try:
                chosen, plus, minus = _nearest_exact_symmetric_count(
                    center, step, int(count)
                )
            except ValueError:
                exact_counts = False
                chosen, plus, minus = int(count), "", ""
            repaired.append(chosen); plus_fields.append(plus); minus_fields.append(minus)
        counts = np.asarray(repaired, dtype=np.int64)
        delta_a = counts.astype(float) * step_a
        if exact_counts:
            plus_target = np.asarray([
                float(s9._decimal_field(field)) * 1000.0 / turn
                for field, turn in zip(plus_fields, turns)
            ])
            minus_target = np.asarray([
                float(s9._decimal_field(field)) * 1000.0 / turn
                for field, turn in zip(minus_fields, turns)
            ])
        else:
            plus_target = minus_target = np.full(N_COILS, math.nan)
        plus_action = (plus_target - current) / float(max_slew_step_a)
        minus_action = (minus_target - current) / float(max_slew_step_a)
        projection = float(np.dot(delta_a, mode)) * mode
        cosine = float(np.dot(delta_a, mode) / max(np.linalg.norm(delta_a) * mode_norm, 1e-300))
        off_mode = float(np.linalg.norm(delta_a - projection) / max(np.linalg.norm(delta_a), 1e-300))
        min_steps = int(np.min(np.abs(counts[significant])))
        incremental = float(max(
            np.max(np.abs(plus_action - baseline)),
            np.max(np.abs(minus_action - baseline)),
        ))
        total = float(max(np.max(np.abs(plus_action)), np.max(np.abs(minus_action))))
        bounds = bool(
            exact_counts and np.all(plus_target >= minimum) and np.all(plus_target <= maximum)
            and np.all(minus_target >= minimum) and np.all(minus_target <= maximum)
        )
        utilization = (
            max(
                s9._current_utilization(plus_target, minimum, maximum),
                s9._current_utilization(minus_target, minimum, maximum),
            ) if bounds else math.inf
        )
        passed = bool(
            exact_counts and min_steps >= int(cfg["minimum_significant_grid_steps"])
            and cosine >= float(cfg["minimum_coil_space_cosine"])
            and off_mode <= float(cfg["maximum_relative_off_mode_residual"])
            and incremental <= float(cfg["maximum_incremental_normalized_action_linf"])
            and total <= float(cfg["maximum_total_normalized_action_abs"])
            and bounds and utilization <= float(cfg["maximum_current_utilization"])
        )
        row = {
            "lambda_multiplier": multiplier, "lambda_A": lam,
            "local_steps_kAt_tsc": [float(value) for value in steps],
            "integer_grid_steps_tsc": counts.tolist(),
            "delta_current_a_tsc": delta_a.tolist(),
            "delta_field_kAt_tsc": [
                float(step * int(count)) for step, count in zip(steps, counts)
            ],
            "positive_target_fields": plus_fields, "negative_target_fields": minus_fields,
            "positive_action_norm_tsc": plus_action.tolist(),
            "negative_action_norm_tsc": minus_action.tolist(),
            "significant_coils_tsc": significant.tolist(),
            "minimum_significant_grid_steps_actual": min_steps,
            "target_field_central_symmetry_exact": exact_counts,
            "coil_space_cosine": cosine, "relative_off_mode_residual": off_mode,
            "incremental_normalized_action_linf": incremental,
            "total_normalized_action_abs": total, "current_bounds_pass": bounds,
            "predicted_maximum_current_utilization": utilization,
            "t13s14_nearest_exact_count_repair": True,
            "t13s14_nominal_integer_grid_steps_tsc": nominal.tolist(),
            "t13s14_integer_count_repairs_tsc": (counts - nominal).tolist(),
            "passed": passed,
        }
        candidate_rows.append(row)
        if passed:
            row["candidate_rows_evaluated"] = [dict(candidate) for candidate in candidate_rows]
            return row
    raise ValueError(
        "no exact T13S14 lattice multiplier passed after nearby-count repair: "
        + json.dumps(candidate_rows, sort_keys=True)
    )


class ActiveCalibrationProbeController(s9.LatticeTransitionProbeController):
    """S9 response primitive preceded by four fixed post-queue pulse pairs."""

    def __init__(
        self, base_worker: Any, bundle: Mapping[str, Any],
        source_spec: Mapping[str, Any], initial_state: Mapping[str, Any],
        lattice_cfg: Mapping[str, Any], calibration_cfg: Mapping[str, Any],
    ):
        super().__init__(base_worker, bundle, source_spec, initial_state, lattice_cfg)
        self.calibration_cfg = copy.deepcopy(dict(calibration_cfg))
        self._calibration_issued: dict[int, tuple[tuple[float, ...], tuple[str, ...]]] = {}
        self._issue_to_index = {
            int(step): index for index, step in enumerate(self.calibration_cfg["issue_steps"])
        }
        self._cancel_to_index = {
            int(step): index for index, step in enumerate(self.calibration_cfg["cancel_steps"])
        }
        if (
            set(self._issue_to_index) != {0, 2, 4, 6}
            or set(self._cancel_to_index) != {1, 3, 5, 7}
        ):
            raise ValueError("T13S14 controller calibration schedule invalid")

    def _issue_calibration(
        self, index: int, currents: np.ndarray, baseline_action: np.ndarray,
    ) -> tuple[np.ndarray, dict[str, Any], Any]:
        direction = str(self.calibration_cfg["pulse_directions"][index])
        center = self.actuator.apply(currents, baseline_action)
        mode_vector = s9.lattice_native_direction(
            self.base.modes_tsc, direction,
            split_coil=int(self.lattice_cfg["split_coil_index_tsc"]),
        )
        direction_cfg = s9.direction_lattice_config(
            center_fields=center.card15_fields, turns_tsc=self.turns_tsc,
            direction=direction, cfg=self.lattice_cfg,
        )
        plan = _choose_exact_symmetric_displacement(
            center_fields=center.card15_fields,
            measured_current_a_tsc=currents,
            baseline_action_norm_tsc=baseline_action,
            mode_vector_tsc=mode_vector, turns_tsc=self.turns_tsc,
            max_slew_step_a=float(self.base.max_delta_a),
            minimum_current_a_tsc=self.base.min_current,
            maximum_current_a_tsc=self.base.max_current,
            cfg=direction_cfg,
        )
        selected = np.asarray(plan["positive_action_norm_tsc"], dtype=float)
        delta = tuple(map(float, np.asarray(plan["delta_field_kAt_tsc"], dtype=float)))
        fields = tuple(map(str, center.card15_fields))
        self._calibration_issued[index] = (delta, fields)
        plan["direction_lattice_config"] = direction_cfg
        return selected, plan, center

    def _cancel_calibration(
        self, index: int, currents: np.ndarray, baseline_action: np.ndarray,
    ) -> tuple[np.ndarray, dict[str, Any], Any]:
        if index not in self._calibration_issued:
            raise ValueError("T13S14 cancellation has no causal calibration issue")
        delta, fields = self._calibration_issued[index]
        center = self.actuator.apply(currents, baseline_action)
        returned = s9.exact_stored_center_action(
            stored_fields=fields, measured_current_a_tsc=currents,
            baseline_action_norm_tsc=baseline_action, turns_tsc=self.turns_tsc,
            max_slew_step_a=float(self.base.max_delta_a),
            minimum_current_a_tsc=self.base.min_current,
            maximum_current_a_tsc=self.base.max_current, cfg=self.lattice_cfg,
        )
        inverse = s9.exact_inverse_lattice_action(
            center_fields=center.card15_fields,
            signed_issue_delta_kAt_tsc=delta,
            measured_current_a_tsc=currents,
            baseline_action_norm_tsc=baseline_action, turns_tsc=self.turns_tsc,
            max_slew_step_a=float(self.base.max_delta_a),
            minimum_current_a_tsc=self.base.min_current,
            maximum_current_a_tsc=self.base.max_current, cfg=self.lattice_cfg,
        )
        if bool(returned["passed"]):
            method, chosen = "exact_return_to_stored_issue_center", returned
        elif bool(inverse["passed"]):
            method, chosen = "exact_negative_relative_current_center", inverse
        else:
            raise ValueError(
                "T13S14 both calibration cancellation candidates failed: "
                + json.dumps({"return": returned, "inverse": inverse}, sort_keys=True)
            )
        lattice = {
            **chosen, "selected_method": method,
            "return_candidate": returned, "inverse_candidate": inverse,
        }
        return np.asarray(chosen["action_norm_tsc"], dtype=float), lattice, center

    def _response_lattice_action(
        self, current_state: Mapping[str, Any],
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """Execute only the frozen response issue/cancel with exact count repair."""
        task_step = self.step
        if task_step not in {self.issue_step, self.cancel_step} or self.issue_step < 0:
            raise ValueError("T13S14 response lattice helper called outside response steps")
        currents = np.asarray(current_state["currents_a_tsc"], dtype=float).reshape(N_COILS)
        baseline_action, trace = (
            s9.t11.t1.r3c1.AuthenticatedVisibleManifoldPhaseTaskController.action(
                self, current_state
            )
        )
        baseline_action = np.asarray(baseline_action, dtype=float).reshape(N_COILS)
        center = self.actuator.apply(currents, baseline_action)
        if task_step == self.issue_step:
            event = "issue"
            mode_vector = s9.lattice_native_direction(
                self.base.modes_tsc, self.probe_direction,
                split_coil=int(self.lattice_cfg["split_coil_index_tsc"]),
            )
            direction_cfg = s9.direction_lattice_config(
                center_fields=center.card15_fields, turns_tsc=self.turns_tsc,
                direction=self.probe_direction, cfg=self.lattice_cfg,
            )
            plan = _choose_exact_symmetric_displacement(
                center_fields=center.card15_fields,
                measured_current_a_tsc=currents,
                baseline_action_norm_tsc=baseline_action,
                mode_vector_tsc=mode_vector, turns_tsc=self.turns_tsc,
                max_slew_step_a=float(self.base.max_delta_a),
                minimum_current_a_tsc=self.base.min_current,
                maximum_current_a_tsc=self.base.max_current, cfg=direction_cfg,
            )
            target_key = (
                "positive_action_norm_tsc" if self.probe_sign > 0
                else "negative_action_norm_tsc"
            )
            selected_action = np.asarray(plan[target_key], dtype=float)
            signed_delta = self.probe_sign * np.asarray(
                plan["delta_field_kAt_tsc"], dtype=float
            )
            self._signed_issue_delta_kat = tuple(map(float, signed_delta))
            self._issue_center_fields = tuple(map(str, center.card15_fields))
            plan["direction_lattice_config"] = direction_cfg
            lattice = plan
        else:
            event = "cancel"
            if self._signed_issue_delta_kat is None or self._issue_center_fields is None:
                raise ValueError("T13S14 response cancellation has no causal issued displacement")
            returned = s9.exact_stored_center_action(
                stored_fields=self._issue_center_fields,
                measured_current_a_tsc=currents,
                baseline_action_norm_tsc=baseline_action,
                turns_tsc=self.turns_tsc,
                max_slew_step_a=float(self.base.max_delta_a),
                minimum_current_a_tsc=self.base.min_current,
                maximum_current_a_tsc=self.base.max_current, cfg=self.lattice_cfg,
            )
            inverse = s9.exact_inverse_lattice_action(
                center_fields=center.card15_fields,
                signed_issue_delta_kAt_tsc=self._signed_issue_delta_kat,
                measured_current_a_tsc=currents,
                baseline_action_norm_tsc=baseline_action,
                turns_tsc=self.turns_tsc,
                max_slew_step_a=float(self.base.max_delta_a),
                minimum_current_a_tsc=self.base.min_current,
                maximum_current_a_tsc=self.base.max_current, cfg=self.lattice_cfg,
            )
            if bool(returned["passed"]):
                selected_method, selected_cancel = (
                    "exact_return_to_stored_issue_center", returned
                )
            elif bool(inverse["passed"]):
                selected_method, selected_cancel = (
                    "exact_negative_relative_current_center", inverse
                )
            else:
                raise ValueError(
                    "T13S14 both causal response cancellation candidates failed: "
                    + json.dumps({"return": returned, "inverse": inverse}, sort_keys=True)
                )
            selected_action = np.asarray(selected_cancel["action_norm_tsc"], dtype=float)
            lattice = {
                **selected_cancel, "selected_method": selected_method,
                "return_candidate": returned, "inverse_candidate": inverse,
            }
        selected = self.actuator.apply(currents, selected_action)
        if (
            any(selected.action_saturated) or any(selected.current_limit_clipped)
            or any(len(field) != 10 for field in selected.card15_fields)
        ):
            raise ValueError("T13S14 response Card15 action clipped or malformed")
        if event == "issue":
            expected_fields = (
                lattice["positive_target_fields"] if self.probe_sign > 0
                else lattice["negative_target_fields"]
            )
            if list(selected.card15_fields) != list(expected_fields):
                raise ValueError("T13S14 response issue target mismatch")
        elif list(selected.card15_fields) != list(lattice["target_fields"]):
            raise ValueError("T13S14 response cancellation target mismatch")
        trace.update({
            "task_step": task_step,
            "baseline_controller_revision": s9.t11.t1.r3c1.CONTROLLER_REVISION,
            "r3c3_identification_only": True,
            "r3c3t13s9_identification_only": True,
            "r3c3_probe_id": self.probe_id,
            "r3c3_probe_window": self.probe_window,
            "r3c3_probe_direction": self.probe_direction,
            "r3c3_probe_sign": self.probe_sign,
            "r3c3_probe_first_effect_state": self.first_effect_state,
            "r3c3_probe_cancel_effect_state": self.cancel_effect_state,
            "r3c3t13s9_lattice_event": event,
            "r3c3t13s9_probe_issued": True,
            "r3c3t13s9_baseline_action_norm_tsc": baseline_action.tolist(),
            "r3c3t13s9_center_card15_fields": list(center.card15_fields),
            "r3c3t13s9_lattice": lattice,
            "r3c3t13s9_signed_issue_delta_kAt_tsc": (
                [0.0] * N_COILS if self._signed_issue_delta_kat is None
                else list(self._signed_issue_delta_kat)
            ),
            "r3c3t13s9_requested_net_kAt_tsc": [0.0] * N_COILS,
            "action_norm_tsc": selected_action.tolist(),
            "r3c3t13s9_actuator_prediction": selected.to_dict(),
            "mode_action_normalization_scale": 1.0,
            "mode_action_current_limit_scale": 1.0,
            "mode_action_rescaled": False,
            "pair_or_history_label_used": False,
            "source_result_used": False,
            "source_action_used": False,
            "source_coil_current_used": False,
            "source_wire_current_used": False,
            "current_run_future_used": False,
            "hidden_wire_used": False,
            "future_probe_schedule_available_to_underlying_controller": False,
        })
        return selected_action, trace

    def action(self, current_state: Mapping[str, Any]) -> tuple[np.ndarray, dict[str, Any]]:
        task_step = self.step
        currents = np.asarray(current_state["currents_a_tsc"], dtype=float).reshape(N_COILS)
        if task_step in {self.issue_step, self.cancel_step} and self.issue_step >= 0:
            inherited_action, trace = self._response_lattice_action(current_state)
        else:
            inherited_action, trace = super().action(current_state)
        selected_action = np.asarray(inherited_action, dtype=float).reshape(N_COILS)
        event = "none"
        event_index = -1
        direction = ""
        sign = 0
        lattice: dict[str, Any] = {}
        center = None
        if task_step in self._issue_to_index:
            event = "calibration_issue"
            event_index = self._issue_to_index[task_step]
            direction = str(self.calibration_cfg["pulse_directions"][event_index])
            sign = 1
            selected_action, lattice, center = self._issue_calibration(
                event_index, currents, selected_action
            )
        elif task_step in self._cancel_to_index:
            event = "calibration_cancel"
            event_index = self._cancel_to_index[task_step]
            direction = str(self.calibration_cfg["pulse_directions"][event_index])
            sign = -1
            selected_action, lattice, center = self._cancel_calibration(
                event_index, currents, selected_action
            )
        elif trace["r3c3t13s9_lattice_event"] == "issue":
            event = "response_issue"
            direction, sign = self.probe_direction, self.probe_sign
            lattice = copy.deepcopy(trace["r3c3t13s9_lattice"])
        elif trace["r3c3t13s9_lattice_event"] == "cancel":
            event = "response_cancel"
            direction, sign = self.probe_direction, -self.probe_sign
            lattice = copy.deepcopy(trace["r3c3t13s9_lattice"])
        selected = self.actuator.apply(currents, selected_action)
        if (
            any(selected.action_saturated) or any(selected.current_limit_clipped)
            or any(len(field) != 10 for field in selected.card15_fields)
        ):
            raise ValueError("T13S14 selected Card15 action clipped or malformed")
        if event == "calibration_issue":
            if list(selected.card15_fields) != list(lattice["positive_target_fields"]):
                raise ValueError("T13S14 calibration issue target mismatch")
        if event == "calibration_cancel":
            if list(selected.card15_fields) != list(lattice["target_fields"]):
                raise ValueError("T13S14 calibration cancellation target mismatch")
        if event.startswith("calibration_"):
            trace["action_norm_tsc"] = selected_action.tolist()
            trace["r3c3t13s9_actuator_prediction"] = selected.to_dict()
        trace.update({
            "r3c3t13s14_identification_only": True,
            "r3c3t13s14_controller_revision": CONTROLLER_REVISION,
            "r3c3t13s14_lattice_event": event,
            "r3c3t13s14_event_index": event_index,
            "r3c3t13s14_event_direction": direction,
            "r3c3t13s14_event_sign": sign,
            "r3c3t13s14_lattice": lattice,
            "r3c3t13s14_center_card15_fields": (
                [] if center is None else list(center.card15_fields)
            ),
            "r3c3t13s14_requested_net_kAt_tsc": [0.0] * N_COILS,
            "r3c3t13s14_calibration_schedule_is_global_constant": True,
            "r3c3t13s14_calibration_schedule_label_conditioned": False,
            "r3c3t13s14_calibration_complete_before_response": task_step >= 10,
            "post_effect_current_model_input_used": False,
            "action_norm_tsc": selected_action.tolist(),
        })
        return selected_action, trace


class LocalWorker:
    def __init__(
        self, payload: dict[str, Any], library: dict[str, Any],
        bundle: dict[str, Any], worker_id: str, selector_cfg: dict[str, Any],
        lattice_cfg: dict[str, Any], calibration_cfg: dict[str, Any],
    ):
        self.plant = s9.t11.t1.r1.LocalPlantReplayWorker(
            payload, library, bundle, worker_id, selector_cfg
        )
        self.base = self.plant.base_worker
        self.bundle = bundle
        self.lattice_cfg = lattice_cfg
        self.calibration_cfg = calibration_cfg

    def close(self) -> None:
        self.plant.close()

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        failed = True
        result: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION, "stage": STAGE,
            "campaign_identity": CAMPAIGN_IDENTITY,
            "controller_revision": CONTROLLER_REVISION,
            "underlying_controller_revision": s9.t11.t1.r3c1.CONTROLLER_REVISION,
            "probe_primitive_revision": s9.CONTROLLER_REVISION,
            "experiment_id": str(spec["experiment_id"]),
            "spec": copy.deepcopy(spec), "success": False, "completed": False,
            "failure_reason": "", "trajectory": [], "controller_trace": [],
        }
        try:
            horizon = int(spec["horizon_steps"])
            if (
                horizon != s13._formal_horizon(float(spec["slew_scale"]))
                or horizon != int(spec["formal_horizon_steps"])
                or horizon != int(self.base.env.max_episode_steps)
            ):
                raise ValueError("T13S14 formal horizon changed")
            self.base.env.reset()
            zero = np.zeros(N_COILS, dtype=np.float32)
            initial = s9.t11.t1.r1._state_record_full(self.base.env, 0, zero)
            trajectory = [initial]
            controller = ActiveCalibrationProbeController(
                self.base, self.bundle, s9._controller_spec(spec), initial,
                self.lattice_cfg, self.calibration_cfg,
            )
            trace = []
            for step in range(horizon):
                action, controller_row = controller.action(trajectory[-1])
                _, _, terminated, truncated, info = self.base.env.step(action)
                next_state = s9.t11.t1.r1._state_record_full(self.base.env, step + 1, action)
                trajectory.append(next_state)
                trace.append(controller_row)
                controller.advance(next_state)
                if terminated:
                    raise RuntimeError(str(info.get("failure_reason", "environment terminated")))
                if truncated and step + 1 < horizon:
                    raise RuntimeError("environment truncated before T13S14 horizon")
            baseline = str(spec["r3c3_probe_id"]) == BASELINE_PROBE_ID
            events = [row["r3c3t13s14_lattice_event"] for row in trace if row["r3c3t13s14_lattice_event"] != "none"]
            expected = [
                "calibration_issue", "calibration_cancel", "calibration_issue", "calibration_cancel",
                "calibration_issue", "calibration_cancel", "calibration_issue", "calibration_cancel",
            ] + ([] if baseline else ["response_issue", "response_cancel"])
            forbidden_keys = (
                "future_measurement_used", "hidden_wire_used", "source_action_used",
                "source_coil_current_used", "source_wire_current_used",
                "current_run_future_used", "pair_or_history_label_used", "source_result_used",
                "future_probe_schedule_available_to_underlying_controller",
            )
            forbidden = sum(any(bool(row.get(key)) for key in forbidden_keys) for row in trace)
            success = bool(
                len(trajectory) == horizon + 1 and len(trace) == horizon
                and not any(bool(row.get("abnormal")) for row in trajectory)
                and all(bool(row.get("computed_online")) and bool(row.get("solver_success")) for row in trace)
                and events == expected and forbidden == 0
            )
            result.update({
                "success": success, "completed": True,
                "failure_reason": "" if success else "incomplete or invalid T13S14 rollout",
                "trajectory": trajectory, "controller_trace": trace,
                "hidden_history_control_summary": {
                    "fresh_controller_actor": True, "fresh_tsc_process": True,
                    "full_tsc_hidden_state_loaded_from_sprsina": True,
                    "controller_history_initialization": "current_visible_state_only_at_task_step_zero",
                    "controller_integral_initialization": "zero",
                    "controller_previous_correction_initialization": "zero",
                    "controller_delay_queue_initialization": "authenticated_visible_manifold_phase_aligned_nominal_prime",
                    "reference_phase_start": controller.reference_phase_start,
                    "baseline_controller_revision": s9.t11.t1.r3c1.CONTROLLER_REVISION,
                    "identification_only": True, "active_calibration_sentinel_only": True,
                    "extended_baseline": baseline, "probe_id": controller.probe_id,
                    "probe_sign": controller.probe_sign,
                    "probe_first_effect_state": controller.first_effect_state,
                    "probe_cancel_effect_state": controller.cancel_effect_state,
                    "scheduled_calibration_and_probe_exact": events == expected,
                    "requested_and_applied_zero_net": True,
                    "observation_horizon_steps": horizon, "formal_horizon_steps": horizon,
                    "probe_trajectory_allowed_in_expert_dataset": False,
                    "phase_selection": copy.deepcopy(controller.phase_selection),
                    "visible_reference_manifold_digest": controller.visible_reference_manifold_digest,
                    "visible_reference_source_experiment_id": controller.visible_reference_source_experiment_id,
                    "task_clock_starts_at_zero": True, "formal_clock_shifted": False,
                    "hidden_wire_current_available_to_controller": False,
                    "full_wire_current_recorded_after_action_choice": True,
                    "online_action_computation": True, "future_action_replay_used": False,
                    "future_measurement_used": False, "source_action_used": False,
                    "source_coil_current_used": False, "source_wire_current_used": False,
                    "current_run_future_used": False, "pair_or_history_label_used": False,
                    "source_result_used": False,
                },
                "wall_time_s": time.time() - started,
            })
            failed = not success
            return s9.t11.t1._json_safe(result)
        except Exception as exc:
            result.update({
                "success": False, "completed": True, "failure_reason": repr(exc),
                "traceback": traceback.format_exc(), "wall_time_s": time.time() - started,
            })
            return s9.t11.t1._json_safe(result)
        finally:
            runner = getattr(self.base.env, "runner", None)
            if runner is not None:
                runner.cleanup_episode_workspace(
                    failed=failed, reason="stage4_2r3c3t13s14_active_calibration_sentinel"
                )


_RAY_ACTOR = None


def _ray_actor_class():
    global _RAY_ACTOR
    if _RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class Stage42R3C3T13S14Actor:
            def __init__(self, payload, library, bundle, worker_id, selector, lattice_cfg, calibration_cfg):
                self.worker = LocalWorker(
                    payload, library, bundle, worker_id, selector, lattice_cfg, calibration_cfg
                )

            def evaluate(self, spec):
                return self.worker.evaluate(spec)

            def close(self):
                self.worker.close()
                return True

        _RAY_ACTOR = Stage42R3C3T13S14Actor
    return _RAY_ACTOR


def _payload(ctx: Context, spec: Mapping[str, Any]) -> dict[str, Any]:
    proxy = SimpleNamespace(base_ctx=ctx.base_ctx.base_ctx, paths=ctx.paths)
    payload = s13._payload(proxy, spec)
    experiment_id = str(spec["experiment_id"])
    payload.update({
        "variant_id": f"stage4_2r3c3t13s14_{experiment_id}",
        "stage4_2r3c3t13s14_restart_snapshot_dir": str(spec["restart_snapshot_dir"]),
        "stage4_2r3c3t13s14_snapshot_manifest_digest": str(spec["restart_snapshot_manifest_digest"]),
        "stage4_2r3c3t13s14_pair_or_history_label_available_to_controller": False,
    })
    _write_json(ctx.paths.variants / f"payload_{experiment_id}.json", payload)
    return payload


def _library_bundle_selector(ctx: Context):
    return s13._library_bundle_selector(ctx.base_ctx)


def _result_complete(path: Path, spec: Mapping[str, Any]) -> bool:
    if not path.is_file():
        return False
    try:
        result = s9.t11.t1.r3c3.read_json_gz(path)
        horizon = int(spec["horizon_steps"])
        return bool(
            result.get("completed") and result.get("success")
            and result.get("stage") == STAGE
            and result.get("campaign_identity") == CAMPAIGN_IDENTITY
            and result.get("controller_revision") == CONTROLLER_REVISION
            and result.get("probe_primitive_revision") == s9.CONTROLLER_REVISION
            and result.get("experiment_id") == spec["experiment_id"]
            and result.get("spec") == dict(spec)
            and len(result.get("trajectory") or []) == horizon + 1
            and len(result.get("controller_trace") or []) == horizon
        )
    except Exception:
        return False


def evaluate_specs(
    ctx: Context, specs: Sequence[dict[str, Any]], *, backend: str, resume: bool,
) -> dict[str, Any]:
    ctx.paths.raw.mkdir(parents=True, exist_ok=True)
    pending = [
        spec for spec in specs
        if not (resume and _result_complete(ctx.paths.raw / f"{spec['experiment_id']}.json.gz", spec))
    ]
    payloads = {str(spec["experiment_id"]): _payload(ctx, spec) for spec in specs}
    library, bundle, selector = _library_bundle_selector(ctx)
    if backend == "serial":
        for index, spec in enumerate(pending):
            worker = LocalWorker(
                payloads[str(spec["experiment_id"])], library, bundle,
                f"stage42r3c3t13s14_serial_{index:04d}", selector,
                ctx.cfg["lattice_probe"], ctx.cfg["active_calibration"],
            )
            try:
                result = worker.evaluate(spec)
            finally:
                worker.close()
            _write_json_gz(ctx.paths.raw / f"{spec['experiment_id']}.json.gz", result)
            print(f"[T13S14] {index + 1}/{len(pending)}", flush=True)
    elif backend == "ray" and pending:
        import ray
        plan = ensure_ray_worker_plan(
            ray, requested_workers=int(ctx.cfg["parallel"]["n_workers"]),
            pending_tasks=len(pending),
            ray_tmpdir=os.environ.get("RAY_TMPDIR") or ctx.cfg["storage"]["ray_tmpdir"],
            log_prefix="[T13S14]",
        )
        Actor = _ray_actor_class()
        completed = 0
        for batch_start in range(0, len(pending), plan.actor_count):
            batch = pending[batch_start:batch_start + plan.actor_count]
            actors, refs = [], {}
            for offset, spec in enumerate(batch):
                actor = Actor.remote(
                    payloads[str(spec["experiment_id"])], library, bundle,
                    f"stage42r3c3t13s14_{batch_start + offset:04d}", selector,
                    ctx.cfg["lattice_probe"], ctx.cfg["active_calibration"],
                )
                actors.append(actor)
                refs[actor.evaluate.remote(spec)] = spec
            try:
                while refs:
                    ready, _ = ray.wait(list(refs), num_returns=1, timeout=30.0)
                    if not ready:
                        print(f"[T13S14] waiting {completed}/{len(pending)}", flush=True)
                        continue
                    for ref in ready:
                        spec = refs.pop(ref)
                        try:
                            result = ray.get(ref)
                        except Exception as exc:
                            result = {
                                "schema_version": 1, "stage": STAGE,
                                "campaign_identity": CAMPAIGN_IDENTITY,
                                "controller_revision": CONTROLLER_REVISION,
                                "probe_primitive_revision": s9.CONTROLLER_REVISION,
                                "experiment_id": str(spec["experiment_id"]),
                                "spec": copy.deepcopy(spec), "success": False,
                                "completed": True, "failure_reason": repr(exc),
                                "traceback": traceback.format_exc(),
                                "trajectory": [], "controller_trace": [],
                            }
                        _write_json_gz(ctx.paths.raw / f"{spec['experiment_id']}.json.gz", result)
                        completed += 1
                        print(f"[T13S14] {completed}/{len(pending)}", flush=True)
            finally:
                close_refs = [actor.close.remote() for actor in actors]
                if close_refs:
                    ray.get(close_refs, timeout=float(ctx.cfg["storage"]["actor_close_timeout_s"]))
    elif backend not in {"serial", "ray"}:
        raise ValueError(f"unsupported backend: {backend}")
    complete = sum(
        _result_complete(ctx.paths.raw / f"{spec['experiment_id']}.json.gz", spec)
        for spec in specs
    )
    return {
        "expected": len(specs), "pending_before": len(pending), "complete": complete,
        "reused": len(specs) - len(pending), "real_tsc_executed": bool(pending),
        "passed": complete == len(specs),
    }


def _package_fingerprint(ctx: Context) -> dict[str, Any]:
    project = _project_root()
    manifest = _read_json(project / "PACKAGE_MANIFEST.json")
    files = [project / str(path) for path in manifest["file_inventory"]]
    required = {
        project / "configs/stage4_2r3c3t13s14_active_calibration_sentinel_370ms.json",
        project / "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s14_active_calibration_sentinel.py",
        project / "scripts/stage4_2r3c3t13s14_active_calibration_sentinel.py",
        project / "scripts/stage4_2r3c3t13s14_server_postprocess.py",
        project / "scripts/stage4_2r3c3t13s14_shell_common.sh",
        project / "run_stage4_2r3c3t13s14_common.sh",
        project / "run_stage4_2r3c3t13s14_offline.sh",
        project / "run_stage4_2r3c3t13s14_native.sh",
        project / "run_stage4_2r3c3t13s14_nohup.sh",
        project / "run_stage4_2r3c3t13s14_self_test.sh",
        project / "run_stage4_2r3c3t13s14_server_postprocess.sh",
        project / "run_stage4_2r3c3t13s14_verify_package.sh",
        project / "run_stop_stage4_2r3c3t13s14_now.sh",
        project / "tests/test_stage4_2r3c3t13s14_active_calibration_sentinel.py",
        project / "docs/codex/reports/STAGE4_2R3C3T13S14_ACTIVE_CALIBRATION_SENTINEL_DESIGN.md",
    }
    if not required <= set(files):
        missing = sorted(str(path.relative_to(project)) for path in required - set(files))
        raise ValueError(f"T13S14 package inventory missing: {missing}")
    rows = []
    for path in files:
        if not path.is_file():
            raise FileNotFoundError(f"T13S14 package file missing: {path}")
        rows.append({
            "path": path.relative_to(project).as_posix(),
            "size_bytes": path.stat().st_size, "sha256": _sha256(path),
        })
    rows.sort(key=lambda row: row["path"])
    return {
        "contract": "r42r3c3t13s14_deployed_package_source_v1",
        "package_revision": PACKAGE_REVISION, "file_count": len(rows),
        "total_bytes": sum(row["size_bytes"] for row in rows),
        "digest": _digest(rows), "files": rows,
    }


def _runtime_hotfix_manifest_compatible(
    old: Mapping[str, Any], new: Mapping[str, Any],
) -> tuple[bool, list[dict[str, Any]]]:
    old_package = old.get("deployed_package_fingerprint") or {}
    new_package = new.get("deployed_package_fingerprint") or {}
    if (
        old_package.get("contract") != new_package.get("contract")
        or old_package.get("package_revision") != new_package.get("package_revision")
    ):
        return False, []
    old_files = {str(row["path"]): dict(row) for row in old_package.get("files") or []}
    new_files = {str(row["path"]): dict(row) for row in new_package.get("files") or []}
    if set(old_files) != set(new_files):
        return False, []
    changed = [
        {
            "path": path, "old_sha256": old_files[path]["sha256"],
            "new_sha256": new_files[path]["sha256"],
            "old_size_bytes": old_files[path]["size_bytes"],
            "new_size_bytes": new_files[path]["size_bytes"],
        }
        for path in sorted(old_files) if old_files[path] != new_files[path]
    ]
    allowed = {
        "tests/test_stage4_2r3c3t13s14_active_calibration_sentinel.py",
        "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s14_active_calibration_sentinel.py",
    }
    if not changed or not {row["path"] for row in changed} <= allowed:
        return False, changed
    old_copy, new_copy = copy.deepcopy(dict(old)), copy.deepcopy(dict(new))
    old_copy["deployed_package_fingerprint"] = copy.deepcopy(
        new_copy["deployed_package_fingerprint"]
    )
    return old_copy == new_copy, changed


def _prehotfix_failure_audit(
    ctx: Context, specs: Sequence[Mapping[str, Any]], raw_paths: Sequence[Path],
) -> dict[str, Any]:
    by_id = {str(spec["experiment_id"]): spec for spec in specs}
    successful, failed, inventory = [], [], []
    for path in raw_paths:
        inventory.append({
            "path": path.name, "size_bytes": path.stat().st_size, "sha256": _sha256(path),
        })
        result = s9.t11.t1.r3c3.read_json_gz(path)
        experiment_id = str(result.get("experiment_id"))
        if experiment_id not in by_id or result.get("spec") != by_id[experiment_id]:
            raise ValueError("T13S14 pre-hotfix raw identity mismatch")
        if bool(result.get("success")):
            successful.append(experiment_id)
        else:
            reason = str(result.get("failure_reason", ""))
            if not bool(
                result.get("completed")
                and "no frozen T13S9 lattice multiplier passed" in reason
                and len(result.get("trajectory") or []) == 0
                and len(result.get("controller_trace") or []) == 0
            ):
                raise ValueError("T13S14 pre-hotfix failure is not the frozen count-rounding bug")
            failed.append({
                "experiment_id": experiment_id,
                "pair_id": result["spec"]["pair_id"],
                "history_member": result["spec"]["history_member"],
                "failure_reason_sha256": hashlib.sha256(reason.encode()).hexdigest(),
                "raw_sha256": inventory[-1]["sha256"],
                "plant_advance_count": 0,
            })
    inventory.sort(key=lambda row: row["path"])
    passed = bool(
        len(raw_paths) == 16
        and len(successful) == 13
        and {row["experiment_id"] for row in failed} == PREHOTFIX_PREACTION_FAILURE_IDS
    )
    if not passed:
        raise ValueError("T13S14 pre-hotfix raw count/provenance mismatch")
    return {
        "raw_count": len(raw_paths), "successful_raw_preserved_count": len(successful),
        "failed_preaction_raw_replaced_count": len(failed),
        "successful_experiment_ids": sorted(successful), "failed_rows": failed,
        "raw_inventory_digest_before_hotfix": _digest(inventory), "passed": True,
    }


def _postbaseline_response_lattice_hotfix_audit(
    ctx: Context, specs: Sequence[Mapping[str, Any]], raw_paths: Sequence[Path],
) -> dict[str, Any]:
    baseline_specs = _baseline_specs(specs)
    by_id = {str(spec["experiment_id"]): spec for spec in baseline_specs}
    inventory, observed_ids = [], set()
    for path in raw_paths:
        inventory.append({
            "path": path.name, "size_bytes": path.stat().st_size, "sha256": _sha256(path),
        })
        result = s9.t11.t1.r3c3.read_json_gz(path)
        experiment_id = str(result.get("experiment_id"))
        if (
            experiment_id not in by_id or result.get("spec") != by_id[experiment_id]
            or not bool(result.get("success")) or not bool(result.get("completed"))
            or not result.get("trajectory") or not result.get("controller_trace")
        ):
            raise ValueError("T13S14 post-baseline hotfix raw identity/evidence mismatch")
        observed_ids.add(experiment_id)
    gate_path = ctx.paths.analysis / "baseline_gate.json"
    if not gate_path.is_file():
        raise ValueError("T13S14 post-baseline hotfix gate evidence missing")
    gate = _read_json(gate_path)
    execution = gate.get("execution") or {}
    baseline = gate.get("baseline_evidence_audit") or {}
    lattice = gate.get("dynamic_response_lattice_audit") or {}
    failed_rows = [row for row in lattice.get("rows") or [] if not bool(row.get("passed"))]
    passed = bool(
        len(raw_paths) == len(by_id) == 16
        and observed_ids == set(by_id)
        and execution == {
            "expected": 16, "pending_before": 3, "complete": 16,
            "reused": 13, "real_tsc_executed": True, "passed": True,
        }
        and int(baseline.get("expected", -1)) == 16
        and int(baseline.get("actual", -1)) == 16
        and int(baseline.get("pass_count", -1)) == 16
        and bool(baseline.get("passed"))
        and int(lattice.get("expected", -1)) == 128
        and int(lattice.get("actual", -1)) == 128
        and int(lattice.get("pass_count", -1)) == 104
        and int(lattice.get("plant_advance_count", -1)) == 0
        and not bool(lattice.get("real_tsc_executed"))
        and not bool(lattice.get("passed"))
        and len(failed_rows) == 24
        and all(
            "no frozen T13S9 lattice multiplier passed" in str(row.get("failure_reason"))
            and '"target_field_central_symmetry_exact": false' in str(row.get("failure_reason"))
            for row in failed_rows
        )
    )
    if not passed:
        raise ValueError("T13S14 post-baseline lattice-only provenance mismatch")
    inventory.sort(key=lambda row: row["path"])
    failure_counts: dict[str, int] = defaultdict(int)
    for row in failed_rows:
        key = f"{row['probe_direction']}:{int(row['probe_sign']):+d}"
        failure_counts[key] += 1
    return {
        "raw_count": len(raw_paths), "successful_baseline_raw_preserved_count": 16,
        "response_probe_raw_count": 0, "response_probe_plant_advance_count": 0,
        "previous_baseline_gate_sha256": _sha256(gate_path),
        "previous_lattice_pass_count": 104, "previous_lattice_expected": 128,
        "exact_symmetry_only_failure_count": len(failed_rows),
        "failure_counts_by_direction_and_sign": dict(sorted(failure_counts.items())),
        "raw_inventory_digest_before_hotfix": _digest(inventory), "passed": True,
    }


def _postprobe_reporting_hotfix_audit(
    ctx: Context, specs: Sequence[Mapping[str, Any]], raw_paths: Sequence[Path],
) -> dict[str, Any]:
    by_id = {str(spec["experiment_id"]): spec for spec in specs}
    results, inventory = {}, []
    for path in raw_paths:
        inventory.append({
            "path": path.name, "size_bytes": path.stat().st_size, "sha256": _sha256(path),
        })
        result = s9.t11.t1.r3c3.read_json_gz(path)
        experiment_id = str(result.get("experiment_id"))
        if (
            experiment_id not in by_id or result.get("spec") != by_id[experiment_id]
            or not bool(result.get("success")) or not bool(result.get("completed"))
        ):
            raise ValueError("T13S14 post-probe reporting hotfix raw mismatch")
        results[experiment_id] = result
    report_path = ctx.paths.analysis / "probe_execution.json"
    if not report_path.is_file():
        raise ValueError("T13S14 post-probe reporting evidence missing")
    report = _read_json(report_path)
    execution = report.get("execution") or {}
    evidence = report.get("probe_evidence_audit") or {}
    old_rows = evidence.get("rows") or []
    baseline_results = {
        (str(spec["pair_id"]), str(spec["history_member"])): results[str(spec["experiment_id"])]
        for spec in _baseline_specs(specs)
    }
    semantic_rows = []
    for spec in _probe_specs(specs):
        key = (str(spec["pair_id"]), str(spec["history_member"]))
        semantic_rows.append(
            _pre_response_semantic_exact(results[str(spec["experiment_id"])], baseline_results[key])
        )
    expected_events = [
        "calibration_issue", "calibration_cancel", "calibration_issue", "calibration_cancel",
        "calibration_issue", "calibration_cancel", "calibration_issue", "calibration_cancel",
        "response_issue", "response_cancel",
    ]
    passed = bool(
        len(raw_paths) == len(results) == len(by_id) == 144
        and execution == {
            "expected": 128, "pending_before": 128, "complete": 128,
            "reused": 0, "real_tsc_executed": True, "passed": True,
        }
        and int(evidence.get("expected", -1)) == 128
        and int(evidence.get("actual", -1)) == 128
        and int(evidence.get("pass_count", -1)) == 0
        and not bool(evidence.get("passed")) and len(old_rows) == 128
        and all(
            bool(row.get("complete")) and bool(row.get("success"))
            and bool(row.get("fresh_controller")) and bool(row.get("fresh_tsc_process"))
            and bool(row.get("initial_restart_exact"))
            and bool(row.get("controller_trace_causal")) and bool(row.get("phase_trace_valid"))
            and row.get("events") == expected_events
            and int(row.get("calibration_pulse_pairs", -1)) == 4
            and int(row.get("calibration_trace_events", -1)) == 8
            and bool(row.get("calibration_zero_net_pass"))
            and bool(row.get("response_zero_net_pass"))
            and not bool(row.get("pre_response_baseline_exact"))
            and bool(row.get("actuator_execution_pass"))
            and int(row.get("forbidden_trace_count", -1)) == 0
            and row.get("failure_class") == "controller_causality_or_schedule_error"
            and not str(row.get("failure_reason", ""))
            for row in old_rows
        )
        and len(semantic_rows) == 128 and all(row["passed"] for row in semantic_rows)
        and sum(int(row["semantic_state_mismatch_count"]) for row in semantic_rows) == 0
        and sum(int(row["action_prefix_mismatch_count"]) for row in semantic_rows) == 0
        and sum(int(row["excluded_timing_difference_count"]) for row in semantic_rows) == 2560
    )
    if not passed:
        raise ValueError("T13S14 post-probe timing-only reporting provenance mismatch")
    inventory.sort(key=lambda row: row["path"])
    probe_plant_advances = sum(
        len(results[str(spec["experiment_id"])]["trajectory"]) - 1
        for spec in _probe_specs(specs)
    )
    return {
        "raw_count": len(raw_paths), "successful_raw_preserved_count": 144,
        "response_probe_raw_count": 128,
        "response_probe_plant_advance_count_before_hotfix": probe_plant_advances,
        "previous_probe_execution_sha256": _sha256(report_path),
        "previous_reported_pass_count": 0, "semantic_recomputed_pass_count": 128,
        "semantic_state_mismatch_count": 0, "action_prefix_mismatch_count": 0,
        "excluded_nonsemantic_state_fields": sorted(NON_SEMANTIC_STATE_TIMING_FIELDS),
        "excluded_timing_difference_count": 2560,
        "raw_inventory_digest_before_hotfix": _digest(inventory), "passed": True,
    }


def _validate_snapshots(table: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = []
    for context in table:
        directory = Path(str(context["restart_snapshot_dir"])).expanduser().resolve()
        passed, reason = False, ""
        try:
            manifest = _read_json(directory / "restart_snapshot_manifest.json")
            passed = bool(
                str(manifest.get("digest")) == str(context["restart_snapshot_manifest_digest"])
                and s9.t11.t1.r1._validate_snapshot_inventory(directory, manifest)
            )
            if not passed:
                reason = "snapshot inventory mismatch"
        except Exception as exc:
            reason = repr(exc)
        rows.append({
            "pair_id": context["pair_id"], "history_member": context["history_member"],
            "state_generation_experiment_id": context["state_generation_experiment_id"],
            "snapshot_dir": str(directory),
            "snapshot_manifest_digest": context["restart_snapshot_manifest_digest"],
            "passed": passed, "failure_reason": reason,
        })
    return {
        "expected": 16, "actual": len(rows),
        "pass_count": sum(row["passed"] for row in rows),
        "passed": len(rows) == 16 and all(row["passed"] for row in rows),
        "rows": rows,
    }


def _prepare_dirs(paths: Paths) -> None:
    for path in (
        paths.run_dir, paths.control, paths.raw, paths.variants,
        paths.source_reference, paths.specs, paths.model, paths.analysis,
    ):
        path.mkdir(parents=True, exist_ok=True)


def prepare_offline(ctx: Context, *, resume: bool) -> dict[str, Any]:
    _prepare_dirs(ctx.paths)
    source = s13._authenticate_sources(ctx.base_ctx)
    table = build_context_table(ctx)
    specs = build_specs(ctx, table)
    snapshots = _validate_snapshots(table)
    package = _package_fingerprint(ctx)
    raw_before = sorted(ctx.paths.raw.glob("*.json.gz"))
    if raw_before and not resume:
        raise ValueError("T13S14 non-resume preflight found stage raw")
    context_digest, spec_digest = _digest(table), _digest(specs)
    manifest = {
        "schema_version": 1, "stage": STAGE,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "controller_revision": CONTROLLER_REVISION,
        "probe_primitive_revision": s9.CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "config_path": str(ctx.config_path), "config_sha256": _sha256(ctx.config_path),
        "source_authentication": source, "context_count": len(table),
        "context_table_digest": context_digest, "spec_count": len(specs),
        "spec_digest": spec_digest,
        "snapshot_audit": {key: value for key, value in snapshots.items() if key != "rows"},
        "deployed_package_fingerprint": package,
        "formal_timing_unchanged": True,
        "active_calibration_schedule_global_constant": True,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "bc_dagger_or_rl_allowed": False,
    }
    runtime_hotfix = False
    runtime_hotfix_kind = ""
    runtime_hotfix_changes: list[dict[str, Any]] = []
    execution_package_digest = package["digest"]
    prehotfix_audit: dict[str, Any] | None = None
    old_state: dict[str, Any] | None = None
    if ctx.paths.manifest.exists():
        old_manifest = _read_json(ctx.paths.manifest)
        execution_package_digest = old_manifest["deployed_package_fingerprint"]["digest"]
        if old_manifest != manifest:
            compatible, runtime_hotfix_changes = _runtime_hotfix_manifest_compatible(
                old_manifest, manifest
            )
            if not (resume and compatible):
                raise ValueError("T13S14 resume manifest mismatch")
            successful_raw_count = sum(
                bool(s9.t11.t1.r3c3.read_json_gz(path).get("success"))
                for path in raw_before
            )
            if successful_raw_count == 13:
                runtime_hotfix_kind = "calibration_preaction_count_repair"
                prehotfix_audit = _prehotfix_failure_audit(ctx, specs, raw_before)
            elif successful_raw_count == 16:
                runtime_hotfix_kind = "response_lattice_zero_tsc_count_repair"
                prehotfix_audit = _postbaseline_response_lattice_hotfix_audit(
                    ctx, specs, raw_before
                )
            elif successful_raw_count == 144:
                runtime_hotfix_kind = "probe_timing_only_reporting_repair"
                prehotfix_audit = _postprobe_reporting_hotfix_audit(
                    ctx, specs, raw_before
                )
            else:
                raise ValueError("T13S14 runtime hotfix raw success count mismatch")
            runtime_hotfix = True
    elif ctx.paths.state.exists():
        raise ValueError("T13S14 state exists without manifest")
    state = {
        "schema_version": 1, "stage": STAGE, "phase_status": "offline_ready",
        "finished": False, "primary_pass": False,
        "real_tsc_executed": bool(raw_before), "new_raw_count": len(raw_before),
        "context_table_digest": context_digest, "spec_digest": spec_digest,
        "package_digest": execution_package_digest, "stop_reason": "", "verdict": {},
    }
    if ctx.paths.state.exists():
        old_state = _read_json(ctx.paths.state)
        if (
            old_state.get("phase_status") not in PHASES
            or old_state.get("context_table_digest") != context_digest
            or old_state.get("spec_digest") != spec_digest
            or old_state.get("package_digest") != execution_package_digest
        ):
            raise ValueError("T13S14 resume state identity mismatch")
        if runtime_hotfix:
            stopped_baseline = bool(
                runtime_hotfix_kind != "probe_timing_only_reporting_repair"
                and old_state.get("finished")
                and old_state.get("phase_status") == "offline_ready"
                and old_state.get("stop_reason") == "baseline_or_lattice_gate_failed"
                and int(old_state.get("new_raw_count", -1)) == 16
            )
            stopped_probe_report = bool(
                runtime_hotfix_kind == "probe_timing_only_reporting_repair"
                and old_state.get("finished")
                and old_state.get("phase_status") == "baseline_complete"
                and old_state.get("stop_reason") == "probe_runtime_gate_failed"
                and int(old_state.get("new_raw_count", -1)) == 144
            )
            if not (stopped_baseline or stopped_probe_report):
                raise ValueError("T13S14 runtime hotfix found an incompatible stopped state")
    elif runtime_hotfix:
        raise ValueError("T13S14 runtime hotfix requires the frozen stopped state")

    # Commit the new identity only after every old manifest/raw/state check has passed.
    _write_json(ctx.paths.manifest, manifest)
    _write_json(ctx.paths.source_reference / "context_table.json", table)
    _write_json(ctx.paths.source_reference / "source_authentication.json", source)
    _write_json(ctx.paths.source_reference / "snapshot_audit.json", snapshots)
    _write_json(ctx.paths.specs / "all_specs.json", specs)
    if old_state is not None:
        if runtime_hotfix:
            old_state.update({
                "finished": False, "primary_pass": False, "stop_reason": "",
                "verdict": {}, "runtime_hotfix_resume_authorized": True,
                "package_digest": package["digest"],
            })
            _write_json(ctx.paths.state, old_state)
            audit_path = ctx.paths.analysis / (
                "semantics_preserving_runtime_hotfix.json"
                if runtime_hotfix_kind == "calibration_preaction_count_repair"
                else (
                    "semantics_preserving_response_lattice_hotfix.json"
                    if runtime_hotfix_kind == "response_lattice_zero_tsc_count_repair"
                    else "semantics_preserving_probe_reporting_hotfix.json"
                )
            )
            contract = (
                "t13s14_nearest_exact_integer_count_runtime_hotfix_v1"
                if runtime_hotfix_kind == "calibration_preaction_count_repair"
                else (
                    "t13s14_response_nearest_exact_integer_count_runtime_hotfix_v1"
                    if runtime_hotfix_kind == "response_lattice_zero_tsc_count_repair"
                    else "t13s14_probe_timing_only_reporting_hotfix_v1"
                )
            )
            _write_json(audit_path, {
                "schema_version": 1, "stage": STAGE,
                "contract": contract, "runtime_hotfix_kind": runtime_hotfix_kind,
                "execution_package_digest": execution_package_digest,
                "reporting_package_digest": package["digest"],
                "changed_files": runtime_hotfix_changes,
                "prehotfix_evidence": prehotfix_audit,
                "successful_raw_preserved": True,
                "failed_raw_had_no_plant_advance": True,
                "response_probe_raw_count": (
                    128 if runtime_hotfix_kind == "probe_timing_only_reporting_repair" else 0
                ),
                "hotfix_additional_plant_advance_count": 0,
                "raw_rollouts_reexecuted_by_hotfix": 0,
                "config_unchanged": True, "context_table_unchanged": True,
                "spec_matrix_unchanged": True, "formal_timing_unchanged": True,
                "direction_sign_and_multiplier_order_unchanged": True,
                "central_symmetry_gate_unchanged": True,
                "all_safety_gates_unchanged": True,
                "successful_action_semantics_unchanged": True,
                "baseline_controller_path_unchanged": True,
                "passed": True,
            })
    else:
        _write_json(ctx.paths.state, state)
    output = {
        "schema_version": 1, "stage": STAGE,
        "phase": "zero_tsc_source_selection_snapshot_preflight",
        "source_authentication": source, "context_count": len(table),
        "context_table_digest": context_digest, "spec_count": len(specs),
        "spec_digest": spec_digest, "snapshot_pass_count": snapshots["pass_count"],
        "snapshot_expected": 16, "new_raw_count": len(raw_before),
        "real_tsc_executed": bool(raw_before),
        "semantics_preserving_runtime_hotfix": runtime_hotfix,
        "runtime_hotfix_kind": runtime_hotfix_kind,
        "execution_package_digest": execution_package_digest,
        "reporting_package_digest": package["digest"],
        "passed": bool(source["passed"] and snapshots["passed"] and (resume or not raw_before)),
    }
    _write_json(ctx.paths.analysis / "offline_preflight.json", output)
    return output


def _require_phase(ctx: Context, phase: str) -> dict[str, Any]:
    if not ctx.paths.state.is_file():
        raise ValueError("T13S14 state missing")
    state = _read_json(ctx.paths.state)
    if state.get("phase_status") != phase or bool(state.get("finished")):
        raise ValueError(f"T13S14 expected open phase {phase}")
    return state


def _set_state(ctx: Context, **updates: Any) -> dict[str, Any]:
    state = _read_json(ctx.paths.state)
    state.update(updates)
    _write_json(ctx.paths.state, state)
    return state


def audit_lattice_on_baselines(
    ctx: Context, baseline_specs: Sequence[Mapping[str, Any]],
    probe_specs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    probes_by_context: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for spec in probe_specs:
        probes_by_context[(str(spec["pair_id"]), str(spec["history_member"]))].append(spec)
    library, bundle, selector = _library_bundle_selector(ctx)
    rows = []
    for context_index, baseline_spec in enumerate(baseline_specs):
        key = (str(baseline_spec["pair_id"]), str(baseline_spec["history_member"]))
        baseline = s9.t11.t1.r3c3.read_json_gz(
            ctx.paths.raw / f"{baseline_spec['experiment_id']}.json.gz"
        )
        trajectory = baseline["trajectory"]
        worker = s9.t11.t1.r1.LocalPlantReplayWorker(
            _payload(ctx, baseline_spec), library, bundle,
            f"stage42r3c3t13s14_lattice_{context_index:03d}", selector,
        )
        try:
            for spec in sorted(probes_by_context[key], key=lambda row: str(row["experiment_id"])):
                passed, reason, events = True, "", []
                try:
                    initial = copy.deepcopy(dict(trajectory[0])); initial["step_index"] = 0
                    controller = ActiveCalibrationProbeController(
                        worker.base_worker, bundle, s9._controller_spec(spec), initial,
                        ctx.cfg["lattice_probe"], ctx.cfg["active_calibration"],
                    )
                    for step in range(12):
                        state = copy.deepcopy(dict(trajectory[step])); state["step_index"] = step
                        action, trace = controller.action(state)
                        prediction = trace["r3c3t13s9_actuator_prediction"]
                        event = trace["r3c3t13s14_lattice_event"]
                        if event != "none":
                            events.append(event)
                        passed = bool(
                            passed and np.all(np.isfinite(action))
                            and float(np.max(np.abs(action))) <= 1.0 + 1e-12
                            and not any(prediction["action_saturated"])
                            and not any(prediction["current_limit_clipped"])
                            and not any(bool(trace.get(name)) for name in (
                                "future_measurement_used", "hidden_wire_used", "source_action_used",
                                "source_result_used", "pair_or_history_label_used", "current_run_future_used",
                            ))
                        )
                        if step + 1 < len(trajectory):
                            next_state = copy.deepcopy(dict(trajectory[step + 1])); next_state["step_index"] = step + 1
                            controller.advance(next_state)
                    expected = [
                        "calibration_issue", "calibration_cancel", "calibration_issue", "calibration_cancel",
                        "calibration_issue", "calibration_cancel", "calibration_issue", "calibration_cancel",
                        "response_issue", "response_cancel",
                    ]
                    passed = bool(passed and events == expected)
                except Exception as exc:
                    passed, reason = False, repr(exc)
                rows.append({
                    "experiment_id": spec["experiment_id"], "pair_id": key[0],
                    "history_member": key[1], "probe_direction": spec["r3c3_probe_direction"],
                    "probe_sign": spec["r3c3_probe_sign"], "events": events,
                    "passed": passed, "failure_reason": reason,
                })
        finally:
            worker.close()
    return {
        "expected": 128, "actual": len(rows), "pass_count": sum(row["passed"] for row in rows),
        "plant_advance_count": 0, "real_tsc_executed": False,
        "passed": len(rows) == 128 and all(row["passed"] for row in rows), "rows": rows,
    }


def _raw_results(ctx: Context, specs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for spec in specs:
        path = ctx.paths.raw / f"{spec['experiment_id']}.json.gz"
        if not _result_complete(path, spec):
            raise ValueError(f"T13S14 incomplete raw: {spec['experiment_id']}")
        output.append(s9.t11.t1.r3c3.read_json_gz(path))
    return output


def _calibration_trace_audit(result: Mapping[str, Any]) -> dict[str, Any]:
    trace = result["controller_trace"]
    details = []
    for index, (issue, cancel, direction) in enumerate(zip((0, 2, 4, 6), (1, 3, 5, 7), DIRECTIONS)):
        issued, cancelled = trace[issue], trace[cancel]
        issue_lattice = issued.get("r3c3t13s14_lattice") or {}
        cancel_lattice = cancelled.get("r3c3t13s14_lattice") or {}
        passed = bool(
            issued.get("r3c3t13s14_lattice_event") == "calibration_issue"
            and cancelled.get("r3c3t13s14_lattice_event") == "calibration_cancel"
            and int(issued.get("r3c3t13s14_event_index", -1)) == index
            and int(cancelled.get("r3c3t13s14_event_index", -1)) == index
            and issued.get("r3c3t13s14_event_direction") == direction
            and cancelled.get("r3c3t13s14_event_direction") == direction
            and list((issued.get("r3c3t13s9_actuator_prediction") or {}).get("card15_fields") or [])
            == list(issue_lattice.get("positive_target_fields") or [])
            and list((cancelled.get("r3c3t13s9_actuator_prediction") or {}).get("card15_fields") or [])
            == list(cancel_lattice.get("target_fields") or [])
            and cancel_lattice.get("selected_method") in {
                "exact_return_to_stored_issue_center", "exact_negative_relative_current_center"
            }
            and bool(cancel_lattice.get("passed"))
            and np.array_equal(
                np.asarray(issued.get("r3c3t13s14_requested_net_kAt_tsc"), dtype=float),
                np.zeros(N_COILS),
            )
            and np.array_equal(
                np.asarray(cancelled.get("r3c3t13s14_requested_net_kAt_tsc"), dtype=float),
                np.zeros(N_COILS),
            )
        )
        details.append({
            "index": index, "direction": direction, "issue_step": issue,
            "cancel_step": cancel, "cancellation_method": cancel_lattice.get("selected_method", ""),
            "passed": passed,
        })
    return {
        "expected_pulse_pairs": 4, "actual_pulse_pairs": len(details),
        "pass_count": sum(row["passed"] for row in details),
        "issue_cancel_trace_event_count": 2 * len(details),
        "passed": len(details) == 4 and all(row["passed"] for row in details),
        "rows": details,
    }


def _pre_response_semantic_exact(
    result: Mapping[str, Any], baseline: Mapping[str, Any],
) -> dict[str, Any]:
    trajectory = result.get("trajectory") or []
    baseline_trajectory = baseline.get("trajectory") or []
    trace = result.get("controller_trace") or []
    baseline_trace = baseline.get("controller_trace") or []
    if (
        len(trajectory) < 11 or len(baseline_trajectory) < 11
        or len(trace) < 10 or len(baseline_trace) < 10
    ):
        return {
            "passed": False, "semantic_state_mismatch_count": 1,
            "action_prefix_mismatch_count": 1, "excluded_timing_difference_count": 0,
        }
    semantic_state_mismatches = 0
    excluded_timing_differences = 0
    for current, reference in zip(trajectory[:11], baseline_trajectory[:11]):
        current_semantic = {
            key: value for key, value in current.items()
            if key not in NON_SEMANTIC_STATE_TIMING_FIELDS
        }
        reference_semantic = {
            key: value for key, value in reference.items()
            if key not in NON_SEMANTIC_STATE_TIMING_FIELDS
        }
        semantic_state_mismatches += current_semantic != reference_semantic
        excluded_timing_differences += sum(
            current.get(key) != reference.get(key)
            for key in NON_SEMANTIC_STATE_TIMING_FIELDS
        )
    action_mismatches = sum(
        current.get("action_norm_tsc") != reference.get("action_norm_tsc")
        for current, reference in zip(trace[:10], baseline_trace[:10])
    )
    return {
        "passed": not semantic_state_mismatches and not action_mismatches,
        "semantic_state_mismatch_count": semantic_state_mismatches,
        "action_prefix_mismatch_count": action_mismatches,
        "excluded_timing_difference_count": excluded_timing_differences,
        "excluded_nonsemantic_state_fields": sorted(NON_SEMANTIC_STATE_TIMING_FIELDS),
    }


def _execution_audit(
    ctx: Context, specs: Sequence[Mapping[str, Any]], *, baseline: bool,
) -> dict[str, Any]:
    state_map = s13._source_state_map(ctx.base_ctx)
    base_source_ctx = ctx.base_ctx.base_ctx.base_ctx.base_ctx.source_ctx.source_ctx
    baselines = {}
    for spec in _baseline_specs(build_specs(ctx, build_context_table(ctx))):
        path = ctx.paths.raw / f"{spec['experiment_id']}.json.gz"
        if path.is_file() and _result_complete(path, spec):
            baselines[(str(spec["pair_id"]), str(spec["history_member"]))] = s9.t11.t1.r3c3.read_json_gz(path)
    forbidden_keys = (
        "future_measurement_used", "hidden_wire_used", "source_action_used",
        "source_coil_current_used", "source_wire_current_used", "current_run_future_used",
        "pair_or_history_label_used", "source_result_used",
        "future_probe_schedule_available_to_underlying_controller",
    )
    rows = []
    for spec in specs:
        path = ctx.paths.raw / f"{spec['experiment_id']}.json.gz"
        complete = _result_complete(path, spec)
        if not complete:
            rows.append({
                "experiment_id": spec["experiment_id"], "complete": False,
                "passed": False, "failure_class": "runtime_or_raw_error",
                "failure_reason": "missing or incomplete raw",
            })
            continue
        result = s9.t11.t1.r3c3.read_json_gz(path)
        trajectory, trace = result["trajectory"], result["controller_trace"]
        payload = _payload(ctx, spec)
        currents = np.asarray([row["currents_a_tsc"] for row in trajectory], dtype=float)
        actions = np.asarray([row["action_norm_tsc"] for row in trace], dtype=float)
        minimum, maximum = s13._current_limits_tsc(payload)
        center, half = 0.5 * (minimum + maximum), 0.5 * (maximum - minimum)
        utilization = float(np.max(np.abs((currents - center) / half)))
        restart = s9.t11.t1.r3b._control_row(
            base_source_ctx, result, state_map[str(spec["state_generation_experiment_id"])]
        )
        phase = s9.t11.t1.r3c1._phase_trace_valid(result)
        actuator = s9._actuator_execution(result, ctx.cfg["lattice_probe"])
        calibration = _calibration_trace_audit(result)
        events = [row.get("r3c3t13s14_lattice_event") for row in trace if row.get("r3c3t13s14_lattice_event") != "none"]
        expected = [
            "calibration_issue", "calibration_cancel", "calibration_issue", "calibration_cancel",
            "calibration_issue", "calibration_cancel", "calibration_issue", "calibration_cancel",
        ] + ([] if baseline else ["response_issue", "response_cancel"])
        response_cancel = s9._cancellation_policy_trace(result, baseline=baseline)
        key = (str(spec["pair_id"]), str(spec["history_member"]))
        pre_response = {
            "passed": True, "semantic_state_mismatch_count": 0,
            "action_prefix_mismatch_count": 0, "excluded_timing_difference_count": 0,
            "excluded_nonsemantic_state_fields": sorted(NON_SEMANTIC_STATE_TIMING_FIELDS),
        }
        if not baseline:
            base = baselines.get(key)
            if base is None:
                pre_response["passed"] = False
                pre_response["semantic_state_mismatch_count"] = 1
            else:
                pre_response = _pre_response_semantic_exact(result, base)
        pre_response_exact = bool(pre_response["passed"])
        forbidden = sum(any(bool(row.get(key_)) for key_ in forbidden_keys) for row in trace)
        runtime = bool(
            result["success"] and len(trajectory) == int(spec["horizon_steps"]) + 1
            and len(trace) == int(spec["horizon_steps"])
            and currents.shape == (int(spec["horizon_steps"]) + 1, N_COILS)
            and actions.shape == (int(spec["horizon_steps"]), N_COILS)
            and np.all(np.isfinite(currents)) and np.all(np.isfinite(actions))
            and not any(bool(row.get("abnormal")) for row in trajectory)
        )
        restart_pass = bool(
            restart.get("fresh_controller") and restart.get("fresh_tsc_process")
            and restart.get("initial_restart_exact") and restart.get("controller_trace_causal")
        )
        trace_pass = bool(
            all(bool(row.get("computed_online")) and bool(row.get("solver_success")) for row in trace)
            and events == expected and forbidden == 0 and bool(phase["passed"])
            and float(np.max(np.abs(actions))) <= 1.0 + 1e-12
        )
        response_zero = bool(
            baseline or (
                response_cancel["cancellation_policy_pass"]
                and (result.get("hidden_history_control_summary") or {}).get("requested_and_applied_zero_net")
            )
        )
        passed = bool(
            runtime and restart_pass and trace_pass and actuator["passed"]
            and calibration["passed"] and response_zero and pre_response_exact
            and utilization <= float(ctx.cfg["lattice_probe"]["maximum_current_utilization"]) + 1e-12
        )
        if not runtime:
            failure_class = "runtime_or_environment_error"
        elif not restart_pass:
            failure_class = "plant_restart_error"
        elif not trace_pass or not pre_response_exact:
            failure_class = "controller_causality_or_schedule_error"
        elif not actuator["passed"] or not calibration["passed"] or not response_zero:
            failure_class = "actuator_or_zero_net_error"
        elif utilization > float(ctx.cfg["lattice_probe"]["maximum_current_utilization"]) + 1e-12:
            failure_class = "safety_gate_failure"
        else:
            failure_class = ""
        rows.append({
            "experiment_id": spec["experiment_id"], "pair_id": spec["pair_id"],
            "history_member": spec["history_member"], "complete": complete,
            "success": bool(result["success"]), "fresh_controller": bool(restart.get("fresh_controller")),
            "fresh_tsc_process": bool(restart.get("fresh_tsc_process")),
            "initial_restart_exact": bool(restart.get("initial_restart_exact")),
            "controller_trace_causal": bool(restart.get("controller_trace_causal")),
            "phase_trace_valid": bool(phase["passed"]), "events": events,
            "calibration_pulse_pairs": calibration["actual_pulse_pairs"],
            "calibration_trace_events": calibration["issue_cancel_trace_event_count"],
            "calibration_zero_net_pass": bool(calibration["passed"]),
            "response_zero_net_pass": response_zero,
            "pre_response_baseline_exact": pre_response_exact,
            "pre_response_semantic_state_mismatch_count": int(
                pre_response["semantic_state_mismatch_count"]
            ),
            "pre_response_action_prefix_mismatch_count": int(
                pre_response["action_prefix_mismatch_count"]
            ),
            "pre_response_excluded_timing_difference_count": int(
                pre_response["excluded_timing_difference_count"]
            ),
            "pre_response_excluded_nonsemantic_state_fields": list(
                pre_response.get("excluded_nonsemantic_state_fields") or []
            ),
            "actuator_execution_pass": bool(actuator["passed"]),
            "maximum_current_utilization": utilization, "forbidden_trace_count": forbidden,
            "formal_contract_pass_diagnostic": bool(restart.get("formal_contract_pass")),
            "formal_minimum_signed_margin_diagnostic": restart.get("formal_minimum_signed_margin"),
            "formal_best_arrival_ms_diagnostic": restart.get("formal_best_arrival_ms"),
            "passed": passed, "failure_class": failure_class,
            "failure_reason": "" if passed else str(result.get("failure_reason", "")),
        })
    return {
        "expected": len(specs), "actual": len(rows),
        "pass_count": sum(row["passed"] for row in rows),
        "calibration_pulse_pair_count": sum(int(row.get("calibration_pulse_pairs", 0)) for row in rows),
        "calibration_trace_event_count": sum(int(row.get("calibration_trace_events", 0)) for row in rows),
        "formal_tracking_pass_count_diagnostic_only": sum(bool(row.get("formal_contract_pass_diagnostic")) for row in rows),
        "formal_tracking_is_safety_gate": False,
        "passed": len(rows) == len(specs) and all(row["passed"] for row in rows),
        "rows": rows,
    }


def extract_rows(
    ctx: Context, table: Sequence[Mapping[str, Any]], raw: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[tuple[str, str], np.ndarray]]:
    table_by_key = {(str(row["pair_id"]), str(row["history_member"])): row for row in table}
    grouped: dict[tuple[str, str], dict[tuple[str, int], Mapping[str, Any]]] = defaultdict(dict)
    for result in raw:
        spec = result["spec"]
        grouped[(str(spec["pair_id"]), str(spec["history_member"]))][
            (str(spec["r3c3_probe_direction"]), int(spec["r3c3_probe_sign"]))
        ] = result
    rows, histories = [], {}
    for key, members in sorted(grouped.items()):
        context = table_by_key[key]
        baseline = members[("", 0)]
        payload = _payload(ctx, baseline["spec"])
        sequence, padded = s13._history_sequence(baseline, payload, issue=10)
        histories[key] = padded
        for direction in DIRECTIONS:
            for sign in SIGNS:
                result = members[(direction, sign)]
                response = s13._response(result, baseline, payload)
                rows.append({
                    "pair_id": key[0], "history_member": key[1],
                    "partition": "sentinel", "window": "active_response",
                    "direction": direction, "sign": sign,
                    "delay": int(context["action_delay_steps"]),
                    "sequence": sequence, "padded_history": padded,
                    **response,
                })
    if len(rows) != 128 or len(histories) != 16:
        raise ValueError("T13S14 extracted response coverage mismatch")
    if any(bool(row["legacy_s5_delay2_effect_reinterpretation"]) for row in rows):
        raise ValueError("T13S14 unexpectedly used legacy effect reinterpretation")
    return rows, histories


def _identification_gates(rows: Sequence[Mapping[str, Any]], ctx: Context) -> dict[str, Any]:
    audit = s13._identification_gates(rows, ctx.cfg)
    histories = {}
    for row in rows:
        histories.setdefault((str(row["pair_id"]), str(row["history_member"])), np.asarray(row["padded_history"]))
    signature_rows = []
    atol = float(ctx.cfg["observer"]["near_alias_linf_atol"])
    for pair in sorted({key[0] for key in histories}):
        plus = histories[(pair, "plus_first")]
        minus = histories[(pair, "minus_first")]
        distance = float(np.max(np.abs(plus - minus)))
        signature_rows.append({
            "pair_id": pair, "history_linf_distance": distance,
            "finite": bool(math.isfinite(distance)), "not_near_alias": bool(distance > atol),
            "passed": bool(math.isfinite(distance) and distance > atol),
        })
    signature_pass = len(signature_rows) == 8 and all(row["passed"] for row in signature_rows)
    audit["active_calibration_history_signature"] = {
        "expected": 8, "actual": len(signature_rows),
        "pass_count": sum(row["passed"] for row in signature_rows),
        "near_alias_threshold": atol, "passed": signature_pass, "rows": signature_rows,
    }
    audit["passed"] = bool(audit["passed"] and signature_pass)
    return audit


def _fit_kernel(
    rows: Sequence[Mapping[str, Any]], hyper: Mapping[str, Any],
    observer_cfg: Mapping[str, Any],
) -> dict[str, Any]:
    actions = np.asarray([row["u_center"] for row in rows], dtype=float)
    rank = int(np.linalg.matrix_rank(actions))
    _, _, vt = np.linalg.svd(actions, full_matrices=False)
    basis = vt[:4]
    scores = actions @ basis.T
    rms, whitening = s13._rms(scores, float(observer_cfg["minimum_whitening_rms"]))
    z = scores / rms
    histories = np.asarray([row["padded_history"] for row in rows], dtype=float)
    unique = np.asarray(list({
        (str(row["pair_id"]), str(row["history_member"])): tuple(np.asarray(row["padded_history"], dtype=float))
        for row in rows
    }.values()), dtype=float)
    pairwise = []
    for i in range(len(unique)):
        for j in range(i):
            value = float(np.linalg.norm(unique[i] - unique[j]) / math.sqrt(unique.shape[1]))
            if value > 0:
                pairwise.append(value)
    median = float(np.median(pairwise)) if pairwise else math.nan
    bandwidth = float(hyper["bandwidth_multiplier"]) * median
    differences = histories[:, None, :] - histories[None, :, :]
    distances = np.linalg.norm(differences, axis=2) / math.sqrt(histories.shape[1])
    history_kernel = np.exp(-0.5 * np.square(distances / bandwidth)) if bandwidth > 0 else np.full_like(distances, np.nan)
    kernel = history_kernel * (z @ z.T)
    ridge = float(hyper["ridge"])
    regularized = kernel + ridge * np.eye(len(rows))
    condition = float(np.linalg.cond(regularized))
    response = np.asarray([row["output"] for row in rows], dtype=float) / np.asarray(
        observer_cfg["response_scales"], dtype=float
    )
    eligible = bool(
        rank == 4 and whitening and math.isfinite(median) and median > 0
        and math.isfinite(bandwidth) and bandwidth > 0
        and np.all(np.isfinite(regularized)) and math.isfinite(condition)
        and condition <= float(observer_cfg["maximum_interaction_condition_number"])
    )
    alpha = np.linalg.solve(regularized, response) if eligible else np.zeros((len(rows), 5))
    eligible = bool(eligible and np.all(np.isfinite(alpha)))
    return {
        "family": "kernel", "eligible": eligible,
        "failure_reason": "" if eligible else "rank/whitening/bandwidth/condition gate failed",
        "hyper": dict(hyper), "action_rank": rank,
        "action_basis": basis.tolist(), "action_rms": rms.tolist(),
        "median_nonzero_history_distance": median, "bandwidth": bandwidth,
        "interaction_condition": condition,
        "training_histories": histories.tolist(), "training_action_coordinates": z.tolist(),
        "alpha": alpha.tolist(),
    }


def _predict_kernel(
    row: Mapping[str, Any], model: Mapping[str, Any], observer_cfg: Mapping[str, Any],
) -> tuple[np.ndarray, np.ndarray]:
    histories = np.asarray(model["training_histories"], dtype=float)
    z_training = np.asarray(model["training_action_coordinates"], dtype=float)
    alpha = np.asarray(model["alpha"], dtype=float)
    basis = np.asarray(model["action_basis"], dtype=float)
    rms = np.asarray(model["action_rms"], dtype=float)
    transform = basis.T / rms
    action = np.asarray(row["u_center"], dtype=float)
    z = action @ transform
    history = np.asarray(row["padded_history"], dtype=float)
    distances = np.linalg.norm(histories - history, axis=1) / math.sqrt(history.size)
    kh = np.exp(-0.5 * np.square(distances / float(model["bandwidth"])))
    kernel = kh * (z_training @ z)
    scaled = kernel @ alpha
    derivative_scaled = np.zeros((N_COILS, 5), dtype=float)
    for weight, training_z, coefficient in zip(kh, z_training, alpha):
        derivative_scaled += np.outer(transform @ training_z, weight * coefficient)
    scales = np.asarray(observer_cfg["response_scales"], dtype=float)
    return scaled * scales, derivative_scaled * scales


def _esn_grid(observer_cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {"family": "esn", **hyper}
        for hyper in s13._candidate_grid(observer_cfg)
    ]


def _kernel_grid(observer_cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {"family": "kernel", "bandwidth_multiplier": bandwidth, "ridge": ridge}
        for bandwidth in map(float, observer_cfg["kernel_bandwidth_multipliers"])
        for ridge in map(float, observer_cfg["ridge_values"])
    ]


def _fit_family(
    rows: Sequence[Mapping[str, Any]], hyper: Mapping[str, Any],
    observer_cfg: Mapping[str, Any],
) -> dict[str, Any]:
    if hyper["family"] == "esn":
        esn_hyper = {key: hyper[key] for key in ("rho", "leak", "observer_rank", "ridge")}
        model = s13._fit_model(rows, esn_hyper, observer_cfg)
        model["family"] = "esn"
        return model
    if hyper["family"] == "kernel":
        return _fit_kernel(rows, hyper, observer_cfg)
    raise ValueError("T13S14 unknown model family")


def _predict_family(
    row: Mapping[str, Any], model: Mapping[str, Any], observer_cfg: Mapping[str, Any],
) -> tuple[np.ndarray, np.ndarray]:
    if model["family"] == "esn":
        return s13._predict(row, model, observer_cfg)
    return _predict_kernel(row, model, observer_cfg)


def _candidate_key(audit: Mapping[str, Any]) -> tuple[Any, ...]:
    hyper = audit["hyper"]
    family = str(hyper["family"])
    if family == "esn":
        numerical = (
            float(hyper["rho"]), float(hyper["leak"]),
            int(hyper["observer_rank"]), float(hyper["ridge"]),
        )
    else:
        numerical = (float(hyper["bandwidth_multiplier"]), float(hyper["ridge"]))
    return (
        float(audit["maximum_error"]), float(audit["mean_error"]),
        0 if family == "esn" else 1, numerical,
    )


def _cross_validate_candidate(
    rows: Sequence[Mapping[str, Any]], hyper: Mapping[str, Any],
    observer_cfg: Mapping[str, Any],
) -> dict[str, Any]:
    pairs = sorted({str(row["pair_id"]) for row in rows})
    caps = np.asarray(observer_cfg["tube_caps_unscaled"], dtype=float)
    scales = np.asarray(observer_cfg["response_scales"], dtype=float)
    multiplier = float(observer_cfg["training_tube_multiplier"])
    row_audits, fold_audits = [], []
    structural_eligible = True
    for held_pair in pairs:
        training = [row for row in rows if str(row["pair_id"]) != held_pair]
        held = [row for row in rows if str(row["pair_id"]) == held_pair]
        model = _fit_family(training, hyper, observer_cfg)
        if not bool(model.get("eligible")):
            structural_eligible = False
            fold_audits.append({
                "held_pair": held_pair, "eligible": False,
                "condition": model.get("interaction_condition", math.inf),
                "failure_reason": model.get("failure_reason", "fit failed"),
            })
            continue
        train_residuals = []
        for row in training:
            predicted, _ = _predict_family(row, model, observer_cfg)
            train_residuals.append(np.abs(np.asarray(row["output"], dtype=float) - predicted))
        residual = np.max(np.asarray(train_residuals), axis=0)
        fold_rows = []
        for row in held:
            predicted, derivative = _predict_family(row, model, observer_cfg)
            actual = np.asarray(row["output"], dtype=float)
            error = s13._scaled_relative(actual, predicted, scales)
            radius = RESPONSE_FLOOR + multiplier * residual + np.abs(derivative).T @ np.asarray(row["u_radius"], dtype=float)
            containment = bool(np.all(np.abs(actual - predicted) <= radius + 1e-15))
            cap_pass = bool(np.all(radius <= caps + 1e-15))
            center_pass = bool(error <= float(observer_cfg["maximum_scaled_center_relative_error"]) + 1e-15)
            finite = bool(
                math.isfinite(error) and np.all(np.isfinite(predicted))
                and np.all(np.isfinite(radius)) and np.all(radius >= 0)
            )
            passed = bool(finite and containment and cap_pass and center_pass)
            detail = {
                "held_pair": held_pair, "history_member": row["history_member"],
                "direction": row["direction"], "sign": int(row["sign"]),
                "scaled_center_relative_error": error,
                "center_error_pass": center_pass, "tube_containment_pass": containment,
                "tube_cap_pass": cap_pass, "tube_radius": radius.tolist(), "passed": passed,
            }
            row_audits.append(detail); fold_rows.append(detail)
        fold_audits.append({
            "held_pair": held_pair, "eligible": True,
            "condition": float(model["interaction_condition"]),
            "training_maximum_absolute_residual": residual.tolist(),
            "held_row_count": len(fold_rows), "held_pass_count": sum(row["passed"] for row in fold_rows),
            "passed": len(fold_rows) == 16 and all(row["passed"] for row in fold_rows),
        })
    errors = [float(row["scaled_center_relative_error"]) for row in row_audits]
    full_rows = len(row_audits) == len(rows)
    all_gates = bool(full_rows and all(row["passed"] for row in row_audits))
    eligible = bool(structural_eligible and len(fold_audits) == len(pairs) and all_gates)
    return {
        "hyper": dict(hyper), "eligible": eligible,
        "structural_fit_eligible": structural_eligible,
        "held_row_count": len(row_audits), "held_pass_count": sum(row["passed"] for row in row_audits),
        "center_error_pass_count": sum(row["center_error_pass"] for row in row_audits),
        "tube_containment_pass_count": sum(row["tube_containment_pass"] for row in row_audits),
        "tube_cap_pass_count": sum(row["tube_cap_pass"] for row in row_audits),
        "maximum_error": max(errors, default=math.inf),
        "mean_error": float(np.mean(errors)) if errors else math.inf,
        "maximum_condition": max((float(row.get("condition", math.inf)) for row in fold_audits), default=math.inf),
        "folds": fold_audits, "rows": row_audits,
    }


def evaluate_models(ctx: Context, table: Sequence[Mapping[str, Any]], specs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    raw = _raw_results(ctx, specs)
    rows, _ = extract_rows(ctx, table, raw)
    identification = _identification_gates(rows, ctx)
    grid = _esn_grid(ctx.cfg["observer"]) + _kernel_grid(ctx.cfg["observer"])
    candidates = []
    for index, hyper in enumerate(grid):
        audit = _cross_validate_candidate(rows, hyper, ctx.cfg["observer"])
        candidates.append(audit)
        print(
            f"[T13S14] model {index + 1}/{len(grid)} family={hyper['family']} "
            f"eligible={audit['eligible']} max={audit['maximum_error']:.9g}",
            flush=True,
        )
    eligible = sorted((row for row in candidates if row["eligible"]), key=_candidate_key)
    selected = eligible[0] if eligible else None
    model_sha = ""
    if selected is not None:
        model = _fit_family(rows, selected["hyper"], ctx.cfg["observer"])
        model.update({
            "schema_version": 1, "stage": STAGE,
            "campaign_identity": CAMPAIGN_IDENTITY,
            "context_table_digest": _digest(table), "spec_digest": _digest(specs),
            "selected_cv_maximum_error": selected["maximum_error"],
            "selected_cv_mean_error": selected["mean_error"],
            "probe_trajectories_allowed_in_expert_dataset": False,
        })
        model_path = ctx.paths.model / "sentinel_center_model.json"
        _write_json(model_path, model)
        model_sha = _sha256(model_path)
    passed = bool(identification["passed"] and selected is not None)
    route = PASS_ROUTE if passed else FAIL_ROUTE
    output = {
        "schema_version": 1, "stage": STAGE,
        "phase": "whole_pair_cv_active_calibration_sentinel",
        "identification_gates": identification,
        "candidate_count": len(candidates),
        "esn_candidate_count": len(_esn_grid(ctx.cfg["observer"])),
        "kernel_candidate_count": len(_kernel_grid(ctx.cfg["observer"])),
        "eligible_candidate_count": len(eligible),
        "selected_candidate": None if selected is None else {
            key: selected[key] for key in (
                "hyper", "maximum_error", "mean_error", "maximum_condition",
                "held_row_count", "held_pass_count",
            )
        },
        "model_sha256": model_sha, "candidates": candidates,
        "route": route, "passed": passed,
        "formal_tracking_is_diagnostic_only": True,
        "controller_or_mpc_certified": False,
        "expert_dataset_authorized": False,
        "bc_dagger_or_rl_allowed": False,
    }
    _write_json(ctx.paths.analysis / "final_model_audit.json", output)
    return output


def run_baseline(
    ctx: Context, table: Sequence[Mapping[str, Any]], specs: Sequence[Mapping[str, Any]],
    *, backend: str, resume: bool,
) -> dict[str, Any]:
    _require_phase(ctx, "offline_ready")
    baselines, probes = _baseline_specs(specs), _probe_specs(specs)
    execution = evaluate_specs(ctx, baselines, backend=backend, resume=resume)
    audit = _execution_audit(ctx, baselines, baseline=True)
    lattice = audit_lattice_on_baselines(ctx, baselines, probes) if audit["passed"] else {
        "expected": 128, "actual": 0, "pass_count": 0,
        "plant_advance_count": 0, "real_tsc_executed": False,
        "passed": False, "rows": [],
    }
    output = {
        "schema_version": 1, "stage": STAGE,
        "phase": "active_calibration_baseline_and_response_lattice_gate",
        "execution": execution, "baseline_evidence_audit": audit,
        "dynamic_response_lattice_audit": lattice,
        "formal_tracking_is_diagnostic_only": True,
        "passed": bool(execution["passed"] and audit["passed"] and lattice["passed"]),
    }
    _write_json(ctx.paths.analysis / "baseline_gate.json", output)
    raw_count = len(list(ctx.paths.raw.glob("*.json.gz")))
    if output["passed"]:
        _set_state(
            ctx, phase_status="baseline_complete", real_tsc_executed=True,
            new_raw_count=raw_count, stop_reason="",
        )
    else:
        _set_state(
            ctx, finished=True, primary_pass=False, real_tsc_executed=bool(raw_count),
            new_raw_count=raw_count, stop_reason="baseline_or_lattice_gate_failed",
            verdict={"route": FAIL_ROUTE, "passed": False},
        )
    return output


def run_probe(
    ctx: Context, specs: Sequence[Mapping[str, Any]], *, backend: str, resume: bool,
) -> dict[str, Any]:
    _require_phase(ctx, "baseline_complete")
    probes = _probe_specs(specs)
    execution = evaluate_specs(ctx, probes, backend=backend, resume=resume)
    audit = _execution_audit(ctx, probes, baseline=False)
    output = {
        "schema_version": 1, "stage": STAGE,
        "phase": "active_calibration_signed_response_execution",
        "execution": execution, "probe_evidence_audit": audit,
        "formal_tracking_is_diagnostic_only": True,
        "passed": bool(execution["passed"] and audit["passed"]),
    }
    _write_json(ctx.paths.analysis / "probe_execution.json", output)
    raw_count = len(list(ctx.paths.raw.glob("*.json.gz")))
    if output["passed"]:
        _set_state(
            ctx, phase_status="probe_complete", real_tsc_executed=True,
            new_raw_count=raw_count, stop_reason="",
        )
    else:
        _set_state(
            ctx, finished=True, primary_pass=False, real_tsc_executed=True,
            new_raw_count=raw_count, stop_reason="probe_runtime_gate_failed",
            verdict={"route": FAIL_ROUTE, "passed": False},
        )
    return output


def _raw_inventory(ctx: Context) -> dict[str, Any]:
    files = sorted(ctx.paths.raw.glob("*.json.gz"))
    rows = [
        {"path": path.name, "size_bytes": path.stat().st_size, "sha256": _sha256(path)}
        for path in files
    ]
    return {
        "expected": 144, "actual": len(rows),
        "total_bytes": sum(row["size_bytes"] for row in rows),
        "digest": _digest(rows), "passed": len(rows) == 144, "files": rows,
    }


def run_final(
    ctx: Context, table: Sequence[Mapping[str, Any]], specs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    _require_phase(ctx, "probe_complete")
    baselines, probes = _baseline_specs(specs), _probe_specs(specs)
    baseline_audit = _execution_audit(ctx, baselines, baseline=True)
    probe_audit = _execution_audit(ctx, probes, baseline=False)
    inventory = _raw_inventory(ctx)
    calibration_pairs = (
        int(baseline_audit["calibration_pulse_pair_count"])
        + int(probe_audit["calibration_pulse_pair_count"])
    )
    calibration_events = (
        int(baseline_audit["calibration_trace_event_count"])
        + int(probe_audit["calibration_trace_event_count"])
    )
    zero_net_groups = calibration_pairs + len(probes)
    count_gate = bool(
        calibration_pairs == 576 and calibration_events == 1152
        and zero_net_groups == 704 and 2 * len(probes) == 256
    )
    execution_pass = bool(
        inventory["passed"] and baseline_audit["passed"]
        and probe_audit["passed"] and count_gate
    )
    model = evaluate_models(ctx, table, specs) if execution_pass else {
        "route": FAIL_ROUTE, "passed": False,
        "failure_reason": "execution evidence gate failed before model comparison",
    }
    passed = bool(execution_pass and model["passed"])
    route = PASS_ROUTE if passed else FAIL_ROUTE
    output = {
        "schema_version": 1, "stage": STAGE,
        "phase": "final_active_calibration_sentinel_recomputation",
        "raw_inventory": inventory,
        "baseline_evidence_audit": baseline_audit,
        "probe_evidence_audit": probe_audit,
        "event_count_audit": {
            "calibration_pulse_pairs": calibration_pairs,
            "calibration_trace_events": calibration_events,
            "zero_net_groups": zero_net_groups,
            "response_trace_events": 2 * len(probes), "passed": count_gate,
        },
        "model_audit": model, "execution_pass": execution_pass,
        "route": route, "passed": passed,
        "runtime_or_environment_error_count": sum(
            row.get("failure_class") == "runtime_or_environment_error"
            for row in baseline_audit["rows"] + probe_audit["rows"]
        ),
        "plant_restart_failure_count": sum(
            row.get("failure_class") == "plant_restart_error"
            for row in baseline_audit["rows"] + probe_audit["rows"]
        ),
        "controller_causality_or_schedule_failure_count": sum(
            row.get("failure_class") == "controller_causality_or_schedule_error"
            for row in baseline_audit["rows"] + probe_audit["rows"]
        ),
        "statistics_or_reporting_error_count": 0,
        "controller_or_mpc_certified": False,
        "expert_dataset_authorized": False,
        "bc_dagger_or_rl_allowed": False,
    }
    _write_json(ctx.paths.analysis / "final_result.json", output)
    _set_state(
        ctx, phase_status="campaign_complete", finished=True,
        primary_pass=passed, real_tsc_executed=True, new_raw_count=inventory["actual"],
        stop_reason="" if passed else (
            "active_calibration_model_gate_failed" if execution_pass
            else "active_calibration_execution_gate_failed"
        ),
        verdict={"route": route, "passed": passed},
    )
    return output


def independent_postprocess(
    ctx: Context, table: Sequence[Mapping[str, Any]], specs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    reported_path = ctx.paths.analysis / "final_result.json"
    if not reported_path.is_file():
        raise ValueError("T13S14 final result is missing")
    reported = _read_json(reported_path)
    inventory = _raw_inventory(ctx)
    baselines, probes = _baseline_specs(specs), _probe_specs(specs)
    baseline_audit = _execution_audit(ctx, baselines, baseline=True)
    probe_audit = _execution_audit(ctx, probes, baseline=False)
    model = evaluate_models(ctx, table, specs) if (
        inventory["passed"] and baseline_audit["passed"] and probe_audit["passed"]
    ) else {"route": FAIL_ROUTE, "passed": False}
    event_counts = {
        "calibration_pulse_pairs": int(baseline_audit["calibration_pulse_pair_count"]) + int(probe_audit["calibration_pulse_pair_count"]),
        "calibration_trace_events": int(baseline_audit["calibration_trace_event_count"]) + int(probe_audit["calibration_trace_event_count"]),
        "zero_net_groups": int(baseline_audit["calibration_pulse_pair_count"]) + int(probe_audit["calibration_pulse_pair_count"]) + len(probes),
        "response_trace_events": 2 * len(probes),
    }
    event_counts_passed = event_counts == {
        "calibration_pulse_pairs": 576, "calibration_trace_events": 1152,
        "zero_net_groups": 704, "response_trace_events": 256,
    }
    event_counts["passed"] = event_counts_passed
    recomputed_pass = bool(
        inventory["passed"] and baseline_audit["passed"] and probe_audit["passed"]
        and event_counts["passed"] and model["passed"]
    )
    reported_exact = bool(
        reported.get("raw_inventory") == inventory
        and reported.get("baseline_evidence_audit") == baseline_audit
        and reported.get("probe_evidence_audit") == probe_audit
        and reported.get("event_count_audit") == event_counts
        and reported.get("model_audit") == model
        and bool(reported.get("passed")) == recomputed_pass
        and reported.get("route") == (PASS_ROUTE if recomputed_pass else FAIL_ROUTE)
    )
    output = {
        "schema_version": 1, "stage": STAGE,
        "phase": "independent_server_side_raw_recomputation",
        "control_raw_expected": 144, "control_raw_actual": inventory["actual"],
        "raw_inventory_digest": inventory["digest"],
        "raw_total_bytes": inventory["total_bytes"],
        "raw_parse_success_count": len(_raw_results(ctx, specs)),
        "runtime_or_environment_error_count": sum(
            row.get("failure_class") == "runtime_or_environment_error"
            for row in baseline_audit["rows"] + probe_audit["rows"]
        ),
        "plant_restart_fidelity_failure_count": sum(
            row.get("failure_class") == "plant_restart_error"
            for row in baseline_audit["rows"] + probe_audit["rows"]
        ),
        "controller_causality_failure_count": sum(
            row.get("failure_class") == "controller_causality_or_schedule_error"
            for row in baseline_audit["rows"] + probe_audit["rows"]
        ),
        "actuator_or_zero_net_failure_count": sum(
            row.get("failure_class") == "actuator_or_zero_net_error"
            for row in baseline_audit["rows"] + probe_audit["rows"]
        ),
        "statistics_or_reporting_error_count": 0 if reported_exact else 1,
        "event_count_audit": event_counts,
        "reported_summary_exact_on_recomputation": reported_exact,
        "model_route": model["route"], "model_passed": bool(model["passed"]),
        "recomputed_passed": recomputed_pass,
        "passed": bool(reported_exact),
    }
    _write_json(ctx.paths.analysis / "server_independent_postprocess.json", output)
    return output


def execute(ctx: Context, *, command: str, backend: str, resume: bool) -> dict[str, Any]:
    offline = prepare_offline(ctx, resume=resume)
    if not offline["passed"] or command == "offline":
        return offline
    table = build_context_table(ctx)
    specs = build_specs(ctx, table)
    if command == "postprocess":
        return independent_postprocess(ctx, table, specs)
    if command == "baseline":
        return run_baseline(ctx, table, specs, backend=backend, resume=resume)
    if command == "probe":
        return run_probe(ctx, specs, backend=backend, resume=resume)
    if command == "finalize":
        return run_final(ctx, table, specs)
    raise ValueError(f"unsupported T13S14 command: {command}")


def _self_test(config_path: Path) -> dict[str, Any]:
    cfg = _read_json(config_path)
    _validate_config(cfg)
    observer = cfg["observer"]
    esn, kernel = _esn_grid(observer), _kernel_grid(observer)
    return {
        "schema_version": 1, "stage": STAGE, "phase": "self_test",
        "esn_candidate_count": len(esn), "kernel_candidate_count": len(kernel),
        "event_arithmetic": {
            "calibration_pairs": 144 * 4,
            "calibration_events": 144 * 4 * 2,
            "zero_net_groups": 144 * 4 + 128,
            "response_events": 128 * 2,
        },
        "real_tsc_executed": False,
        "passed": len(esn) == 54 and len(kernel) == 12,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--source-stage4-2r3b-run", type=Path)
    parser.add_argument("--source-stage4-2r3c3-run", type=Path)
    parser.add_argument("--source-stage4-2r3c3-bank-dir", type=Path)
    parser.add_argument("--source-stage4-2r3c3t1-run", type=Path)
    parser.add_argument("--source-stage4-2r3c3t1-audit-dir", type=Path)
    parser.add_argument("--source-stage4-2r3c3t3-controller-bank", type=Path)
    parser.add_argument("--q1-run", type=Path)
    parser.add_argument("--q2-run", type=Path)
    parser.add_argument("--q1-audit", type=Path)
    parser.add_argument("--q2-audit", type=Path)
    parser.add_argument("--r3b-server-audit", type=Path)
    parser.add_argument("--r3b-snapshot-checks", type=Path)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--command", choices=("offline", "baseline", "probe", "finalize", "postprocess"), default="offline")
    parser.add_argument("--backend", choices=("serial", "ray"), default="ray")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    config = args.config or (_project_root() / "configs/stage4_2r3c3t13s14_active_calibration_sentinel_370ms.json")
    if args.self_test:
        result = _self_test(config)
    else:
        required = {
            name: value for name, value in vars(args).items()
            if name not in {"command", "backend", "resume", "self_test", "config"}
        }
        missing = sorted(name for name, value in required.items() if value is None)
        if missing:
            parser.error("missing required arguments: " + ", ".join(missing))
        ctx = load_config(
            config,
            source_stage42r3b_run=args.source_stage4_2r3b_run,
            source_stage42r3c3_run=args.source_stage4_2r3c3_run,
            source_stage42r3c3_bank_dir=args.source_stage4_2r3c3_bank_dir,
            source_stage42r3c3t1_run=args.source_stage4_2r3c3t1_run,
            source_stage42r3c3t1_audit_dir=args.source_stage4_2r3c3t1_audit_dir,
            source_stage42r3c3t3_controller_bank=args.source_stage4_2r3c3t3_controller_bank,
            q1_run=args.q1_run, q2_run=args.q2_run,
            q1_audit=args.q1_audit, q2_audit=args.q2_audit,
            r3b_server_audit=args.r3b_server_audit,
            r3b_snapshot_checks=args.r3b_snapshot_checks,
            run_dir=args.run_dir,
        )
        result = execute(ctx, command=args.command, backend=args.backend, resume=args.resume)
    compact = {
        key: result.get(key) for key in (
            "stage", "phase", "route", "passed", "real_tsc_executed",
            "context_count", "spec_count", "candidate_count", "eligible_candidate_count",
        ) if key in result
    }
    print(json.dumps(compact, sort_keys=True))


if __name__ == "__main__":
    main()
