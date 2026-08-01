#!/usr/bin/env python3
"""Stage4.2R3c3T13S1 minimal issue-time transition sentinel."""

from __future__ import annotations

import argparse
import copy
import hashlib
import inspect
import json
import math
import os
import time
import traceback
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t11_persistent_step_response_identification as t11,
)
from tsc_rzip_rllib.utils.ray_runtime import ensure_ray_worker_plan

try:
    import resource
except ImportError:  # pragma: no cover - Windows validation
    resource = None


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S1"
RUN_NAME = "stage4_2r3c3t13s1_minimal_transition_sentinel"
CAMPAIGN_IDENTITY = "restart_issue_time_single_step_transition_sentinel_v1"
CONTROLLER_REVISION = "single_step_transition_probe_v42r3c3t13s1_v1"
PACKAGE_REVISION = "r42r3c3t13s1_minimal_transition_sentinel_v1"
OBSERVATION_HORIZON = 50
BASELINE_PROBE_ID = "single_step_baseline"
WINDOWS = ("transport", "braking")
MODES = (0, 1, 2)
SIGNS = (-1, 1)
N_MODES = t11.N_MODES
N_COILS = t11.N_COILS
N_WIRES = t11.N_WIRES


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_digest(value: Any) -> str:
    return t11._canonical_digest(value)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _formal_horizon(slew: float) -> int:
    return t11._formal_horizon(slew)


@dataclass(frozen=True)
class Stage42R3C3T13S1Paths:
    run_dir: Path
    control: Path
    raw: Path
    variants: Path
    source_reference: Path
    analysis: Path
    manifest: Path
    state: Path


@dataclass(frozen=True)
class Stage42R3C3T13S1Context:
    cfg: dict[str, Any]
    base_config_path: Path
    base_ctx: t11.Stage42R3C3T11Context
    paths: Stage42R3C3T13S1Paths


def _paths(run_dir: Path) -> Stage42R3C3T13S1Paths:
    root = run_dir.expanduser().resolve()
    control = root / RUN_NAME
    return Stage42R3C3T13S1Paths(
        run_dir=root,
        control=control,
        raw=control / "raw",
        variants=root / "stage4_2r3c3t13s1_environment_variants",
        source_reference=root / "stage4_2r3c3t13s1_source_reference",
        analysis=root / "stage4_2r3c3t13s1_analysis",
        manifest=root / "stage4_2r3c3t13s1_manifest.json",
        state=root / "stage4_2r3c3t13s1_state.json",
    )


def _validate_config(cfg: Mapping[str, Any]) -> None:
    if (
        cfg.get("stage") != STAGE
        or int(cfg.get("design_revision", -1)) != 1
        or cfg.get("run_name") != RUN_NAME
        or cfg.get("campaign_identity") != CAMPAIGN_IDENTITY
        or cfg.get("controller_revision") != CONTROLLER_REVISION
        or cfg.get("package_revision") != PACKAGE_REVISION
        or cfg.get("underlying_controller_revision")
        != t11.t1.r3c1.CONTROLLER_REVISION
    ):
        raise ValueError("Stage4.2R3c3T13S1 identity changed")
    contexts = list(cfg["bookend_contexts"])
    expected_contexts = [
        (
            "p5_q1_a0p900_gap2_settle4",
            "minus_first",
            "RZ_p10_m10",
            2,
            0.9,
            False,
            -0.361785367,
        ),
        (
            "p5_q1_a0p900_gap2_settle4",
            "plus_first",
            "RZ_p10_m10",
            2,
            0.9,
            False,
            -0.359605500,
        ),
        (
            "p9_q1_a0p750_gap2_settle4",
            "minus_first",
            "nominal",
            0,
            1.0,
            True,
            0.096970100,
        ),
        (
            "p9_q1_a0p750_gap2_settle4",
            "plus_first",
            "nominal",
            0,
            1.0,
            True,
            0.103787581,
        ),
    ]
    actual_contexts = [
        (
            str(row["pair_id"]),
            str(row["history_member"]),
            str(row["target_id"]),
            int(row["action_delay_steps"]),
            float(row["slew_scale"]),
            bool(row["expected_formal_pass"]),
            float(row["expected_formal_minimum_signed_margin"]),
        )
        for row in contexts
    ]
    if actual_contexts != expected_contexts:
        raise ValueError("Stage4.2R3c3T13S1 bookends changed")
    probe = cfg["identification_probe"]
    history = probe["matched_hidden_history"]
    schedule = probe["schedule_by_delay"]
    expected_schedule = {
        "0": {
            "transport": (2, 3, 3, 4),
            "braking": (16, 17, 17, 18),
        },
        "2": {
            "transport": (0, 1, 3, 4),
            "braking": (14, 15, 17, 18),
        },
    }
    actual_schedule = {
        delay: {
            window: (
                int(schedule[delay][window]["issue_step"]),
                int(schedule[delay][window]["cancel_step"]),
                int(schedule[delay][window]["first_effect_state"]),
                int(schedule[delay][window]["cancel_effect_state"]),
            )
            for window in WINDOWS
        }
        for delay in ("0", "2")
    }
    if actual_schedule != expected_schedule:
        raise ValueError("Stage4.2R3c3T13S1 issue/effect schedule changed")
    if (
        int(probe["observation_horizon_steps"]) != OBSERVATION_HORIZON
        or tuple(map(int, probe["probe_modes"])) != MODES
        or tuple(map(int, probe["probe_signs"])) != SIGNS
        or tuple(probe["effect_windows"]) != WINDOWS
        or list(map(float, probe["amplitude_by_mode"])) != [0.0075] * 3
        or int(probe["required_issue_count_per_signed_probe"]) != 2
        or float(probe["requested_and_applied_zero_net_atol"]) != 1e-12
        or float(probe["requested_and_applied_schedule_atol"]) != 1e-12
        or float(probe["command_mode_subspace_residual_max_A"]) != 1e-6
        or float(probe["scheduler_increment_residual_max_A"]) != 1e-6
        or float(probe["pre_effect_position_max_m"]) != 1e-9
        or float(probe["pre_effect_velocity_max_m_per_s"]) != 1e-7
        or float(probe["pre_effect_ip_max_A"]) != 1e-4
        or float(probe["maximum_current_utilization"]) != 0.55
        or int(probe["response_start_state"]) != 3
        or list(map(float, probe["response_scales"]))
        != [0.03, 0.03, 0.1, 0.1, 2000.0]
        or float(probe["signal_floor_multiplier"]) != 10.0
        or float(probe["maximum_even_to_odd_scaled_l2"]) != 0.1
        or float(probe["maximum_even_velocity_rmse_m_per_s"]) != 0.004
        or float(probe["maximum_even_position_rmse_m"]) != 0.0005
        or float(probe["maximum_even_ip_rmse_A"]) != 20.0
        or history["relative_reference_member"] != "minus_first"
        or float(history["maximum_scaled_relative_response_difference"]) != 0.1
        or float(history["maximum_velocity_component_rmse_m_per_s"]) != 0.008
        or float(history["maximum_endpoint_late_response_speed_error_m_per_s"])
        != 0.004
        or float(history["maximum_final_response_speed_error_m_per_s"]) != 0.01
        or float(history["maximum_position_rmse_m"]) != 0.001
        or float(history["maximum_ip_rmse_A"]) != 30.0
        or int(probe["required_local_response_rank"]) != 6
        or float(probe["maximum_normalized_condition_number"]) != 15.0
        or float(probe["baseline_margin_reproduction_atol"]) != 5e-10
        or bool(probe["formal_tracking_is_acceptance_gate_for_probes"])
        or bool(probe["probe_trajectories_allowed_in_expert_dataset"])
        or bool(probe["pair_or_history_label_input_allowed"])
        or bool(probe["source_result_input_allowed"])
        or bool(probe["source_action_input_allowed"])
        or bool(probe["source_or_current_wire_input_allowed"])
    ):
        raise ValueError("Stage4.2R3c3T13S1 probe contract changed")
    matrix = cfg["control_matrix"]
    if (
        int(matrix["expected_baseline_contexts"]) != 4
        or int(matrix["expected_extended_baseline_rollouts"]) != 4
        or int(matrix["expected_signed_probe_rollouts"]) != 48
        or int(matrix["expected_rollouts_per_context"]) != 13
        or int(matrix["expected_rollouts"]) != 52
        or int(matrix["expected_central_symmetry_groups"]) != 24
        or int(matrix["expected_matched_hidden_history_groups"]) != 12
        or int(matrix["expected_local_response_matrices"]) != 4
        or not bool(matrix["require_fresh_controller"])
        or not bool(matrix["require_fresh_tsc_process"])
        or not bool(matrix["forbid_future_actions"])
        or not bool(matrix["forbid_future_measurements"])
        or not bool(matrix["require_online_action_computation"])
    ):
        raise ValueError("Stage4.2R3c3T13S1 matrix changed")
    contract = cfg["formal_timing_contract"]
    if (
        int(contract["normal"]["arrival_deadline_step"]) != 25
        or int(contract["normal"]["hold_through_step"]) != 35
        or int(contract["weak"]["arrival_deadline_step"]) != 27
        or int(contract["weak"]["hold_through_step"]) != 37
        or float(contract["position_tolerance_m"]) != 0.03
        or float(contract["speed_tolerance_m_per_s"]) != 0.1
        or float(contract["ip_tolerance_A"]) != 10000.0
        or int(contract["arrival_streak_steps"]) != 3
        or bool(contract["arrival_deadline_expansion_allowed"])
    ):
        raise ValueError("Stage4.2R3c3T13S1 formal timing changed")
    if (
        int(cfg["parallel"]["n_workers"]) != 52
        or not bool(cfg["storage"]["large_result_postprocess_on_server"])
        or not bool(cfg["storage"]["download_compact_audits_only"])
        or not bool(cfg["development_set_only"])
        or not bool(cfg["identification_only"])
        or bool(cfg["independent_hidden_history_confirmation"])
        or bool(cfg["independent_long_hold_validated"])
        or bool(cfg["bc_dagger_or_rl_allowed"])
    ):
        raise ValueError("Stage4.2R3c3T13S1 scope changed")


def load_stage42r3c3t13s1_config(
    config_path: Path,
    *,
    source_stage42r3b_run: Path,
    source_stage42r3c3_run: Path,
    source_stage42r3c3_bank_dir: Path,
    source_stage42r3c3t1_run: Path,
    source_stage42r3c3t1_audit_dir: Path,
    source_stage42r3c3t3_controller_bank: Path,
    run_dir_override: Path,
) -> Stage42R3C3T13S1Context:
    config_path = config_path.expanduser().resolve()
    cfg = t11.t1.r3c3.read_json(config_path)
    _validate_config(cfg)
    base_path = (_project_root() / str(cfg["base_stage_config"])).resolve()
    if (
        not base_path.is_file()
        or _sha256(base_path) != str(cfg["base_stage_config_sha256"])
    ):
        raise ValueError("T13S1 frozen T11 base config mismatch")
    base_ctx = t11.load_stage42r3c3t11_config(
        base_path,
        source_stage42r3b_run=source_stage42r3b_run,
        source_stage42r3c3_run=source_stage42r3c3_run,
        source_stage42r3c3_bank_dir=source_stage42r3c3_bank_dir,
        source_stage42r3c3t1_run=source_stage42r3c3t1_run,
        source_stage42r3c3t1_audit_dir=source_stage42r3c3t1_audit_dir,
        source_stage42r3c3t3_controller_bank=(
            source_stage42r3c3t3_controller_bank
        ),
        run_dir_override=run_dir_override,
    )
    return Stage42R3C3T13S1Context(
        cfg=cfg,
        base_config_path=base_path,
        base_ctx=base_ctx,
        paths=_paths(run_dir_override),
    )


def _context_key(spec: Mapping[str, Any]) -> tuple[Any, ...]:
    return t11._context_key(spec)


def _frozen_context_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        str(row["pair_id"]),
        str(row["history_member"]),
        str(row["target_id"]),
        int(row["action_delay_steps"]),
        float(row["slew_scale"]),
    )


def _signed_schedule(
    cfg: Mapping[str, Any], *, delay: int, window: str, mode: int, sign: int
) -> dict[int, np.ndarray]:
    if window not in WINDOWS or mode not in MODES or sign not in SIGNS:
        raise ValueError("T13S1 signed schedule selector invalid")
    row = cfg["identification_probe"]["schedule_by_delay"][str(delay)][window]
    issue = int(row["issue_step"])
    cancel = int(row["cancel_step"])
    if cancel != issue + 1:
        raise ValueError("T13S1 cancellation is not adjacent")
    amplitude = float(cfg["identification_probe"]["amplitude_by_mode"][mode])
    value = np.zeros(N_MODES, dtype=float)
    value[mode] = int(sign) * amplitude
    schedule = {issue: value, cancel: -value}
    if not np.array_equal(
        np.sum(np.stack(list(schedule.values())), axis=0),
        np.zeros(N_MODES, dtype=float),
    ):
        raise ValueError("T13S1 schedule is not exactly zero net")
    effects = [step + delay + 1 for step in sorted(schedule)]
    if effects != [int(row["first_effect_state"]), int(row["cancel_effect_state"])]:
        raise ValueError("T13S1 physical effect schedule mismatch")
    return schedule


def build_control_specs(
    ctx: Stage42R3C3T13S1Context,
    selected_pairs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    source_specs = t11.build_control_specs(ctx.base_ctx, selected_pairs)
    source_baselines = {
        _context_key(spec): spec
        for spec in source_specs
        if str(spec["r3c3_probe_id"]) == t11.BASELINE_PROBE_ID
    }
    frozen = {
        _frozen_context_key(row): row for row in ctx.cfg["bookend_contexts"]
    }
    if len(source_baselines) != 32 or len(frozen) != 4 or not set(frozen) <= set(source_baselines):
        raise ValueError("T13S1 source bookend coverage mismatch")
    specs: list[dict[str, Any]] = []
    for key in sorted(frozen):
        template = copy.deepcopy(dict(source_baselines[key]))
        delay = int(template["action_delay_steps"])
        slew = float(template["slew_scale"])
        members: list[tuple[str, str, int, int, dict[int, np.ndarray]]] = [
            (BASELINE_PROBE_ID, "baseline", -1, 0, {})
        ]
        for window in WINDOWS:
            for mode in MODES:
                for sign in SIGNS:
                    members.append(
                        (
                            f"single_step_{window}_mode{mode}",
                            window,
                            mode,
                            sign,
                            _signed_schedule(
                                ctx.cfg,
                                delay=delay,
                                window=window,
                                mode=mode,
                                sign=sign,
                            ),
                        )
                    )
        for probe_id, window, mode, sign, schedule in members:
            schedule_json = {
                str(step): value.tolist()
                for step, value in sorted(schedule.items())
            }
            schedule_row = (
                None
                if not schedule
                else ctx.cfg["identification_probe"]["schedule_by_delay"]
                [str(delay)][window]
            )
            identity = {
                "stage": STAGE,
                "campaign_identity": CAMPAIGN_IDENTITY,
                "source_context": list(key),
                "probe_id": probe_id,
                "probe_sign": sign,
                "schedule": schedule_json,
                "observation_horizon_steps": OBSERVATION_HORIZON,
                "controller_revision": CONTROLLER_REVISION,
                "source_t1_raw_inventory_digest": (
                    ctx.base_ctx.base_ctx.source_t1_fingerprint[
                        "raw_inventory_digest"
                    ]
                ),
            }
            experiment_id = t11.t1.r3c3._scenario_digest(identity)
            spec = copy.deepcopy(template)
            spec.update(
                {
                    "kind": "stage4_2r3c3t13s1_minimal_transition_sentinel",
                    "stage": STAGE,
                    "campaign_identity": CAMPAIGN_IDENTITY,
                    "controller_revision": CONTROLLER_REVISION,
                    "underlying_controller_revision": (
                        t11.t1.r3c1.CONTROLLER_REVISION
                    ),
                    "experiment_id": experiment_id,
                    "phase": "minimal_transition_sentinel",
                    "category": "identification_only_transition_sentinel",
                    "environment_variant": f"stage4_2r3c3t13s1_{experiment_id}",
                    "horizon_steps": OBSERVATION_HORIZON,
                    "formal_horizon_steps": _formal_horizon(slew),
                    "identification_only": True,
                    "r3c3_probe_id": probe_id,
                    "r3c3_probe_window": window,
                    "r3c3_probe_mode": mode,
                    "r3c3_probe_sign": sign,
                    "r3c3_probe_first_effect_state": (
                        -1 if schedule_row is None else int(schedule_row["first_effect_state"])
                    ),
                    "r3c3_probe_cancel_effect_state": (
                        -1 if schedule_row is None else int(schedule_row["cancel_effect_state"])
                    ),
                    "r3c3_probe_delta_by_task_issue_step": schedule_json,
                    "r3c3_requested_probe_net": [0.0] * N_MODES,
                    "r3c3_probe_amplitude": (
                        0.0
                        if mode < 0
                        else float(
                            ctx.cfg["identification_probe"]["amplitude_by_mode"][mode]
                        )
                    ),
                    "r3c3_probe_expected_issue_count": len(schedule),
                    "r3c3t13s1_schedule_contract": (
                        "adjacent_inverse_issue_single_physical_step_v1"
                    ),
                    "command_mode_subspace_residual_max_A": float(
                        ctx.cfg["identification_probe"]
                        ["command_mode_subspace_residual_max_A"]
                    ),
                    "scheduler_increment_residual_max_A": float(
                        ctx.cfg["identification_probe"]
                        ["scheduler_increment_residual_max_A"]
                    ),
                    "probe_trajectory_allowed_in_expert_dataset": False,
                    "pair_or_history_label_available_to_controller": False,
                    "source_result_available_to_controller": False,
                    "source_action_available_to_controller": False,
                    "source_coil_current_available_to_controller": False,
                    "source_wire_current_available_to_controller": False,
                    "hidden_wire_current_available_to_controller": False,
                    "future_action_count": 0,
                    "future_measurement_count": 0,
                    "online_action_computation_required": True,
                    "task_clock_starts_at_zero": True,
                    "formal_timing_unchanged": True,
                    "development_set_only": True,
                }
            )
            specs.append(spec)
    expected = int(ctx.cfg["control_matrix"]["expected_rollouts"])
    if len(specs) != expected or len({str(spec["experiment_id"]) for spec in specs}) != expected:
        raise ValueError("T13S1 control identity coverage mismatch")
    return specs


def _controller_spec(spec: Mapping[str, Any]) -> dict[str, Any]:
    return t11._controller_spec(spec)


class SingleStepTransitionProbeController(
    t11.t1.LongSeparationTransportProbeController
):
    """Exact causal R3c1 controller plus one current-step-only intervention."""

    _WRAPPER_KEYS = frozenset(
        {
            "campaign_identity",
            "r3c3_probe_id",
            "r3c3_probe_window",
            "r3c3_probe_mode",
            "r3c3_probe_sign",
            "r3c3_probe_first_effect_state",
            "r3c3_probe_cancel_effect_state",
            "r3c3_probe_delta_by_task_issue_step",
            "r3c3_requested_probe_net",
            "r3c3_probe_amplitude",
            "r3c3_probe_expected_issue_count",
            "r3c3t13s1_schedule_contract",
            "command_mode_subspace_residual_max_A",
            "scheduler_increment_residual_max_A",
        }
    )

    def __init__(
        self,
        base_worker: Any,
        bundle: Mapping[str, Any],
        source_spec: Mapping[str, Any],
        initial_state: Mapping[str, Any],
    ):
        baseline_spec = copy.deepcopy(dict(source_spec))
        for key in self._WRAPPER_KEYS:
            baseline_spec.pop(key, None)
        t11.t1.r3c1.AuthenticatedVisibleManifoldPhaseTaskController.__init__(
            self, base_worker, bundle, baseline_spec, initial_state
        )
        self.probe_schedule = {
            int(step): np.asarray(value, dtype=float).reshape(N_MODES)
            for step, value in (
                source_spec.get("r3c3_probe_delta_by_task_issue_step") or {}
            ).items()
        }
        self.probe_id = str(source_spec["r3c3_probe_id"])
        self.probe_window = str(source_spec["r3c3_probe_window"])
        self.probe_mode = int(source_spec["r3c3_probe_mode"])
        self.probe_sign = int(source_spec["r3c3_probe_sign"])
        self.probe_first_effect_state = int(
            source_spec["r3c3_probe_first_effect_state"]
        )
        self.probe_cancel_effect_state = int(
            source_spec["r3c3_probe_cancel_effect_state"]
        )
        self.probe_amplitude = float(source_spec["r3c3_probe_amplitude"])
        self.scheduler_residual_max_a = float(
            source_spec["scheduler_increment_residual_max_A"]
        )
        baseline = self.probe_id == BASELINE_PROBE_ID
        if baseline:
            valid = bool(
                self.probe_window == "baseline"
                and self.probe_mode == -1
                and self.probe_sign == 0
                and self.probe_first_effect_state == -1
                and self.probe_cancel_effect_state == -1
                and self.probe_amplitude == 0.0
                and not self.probe_schedule
            )
        else:
            delay = int(source_spec["action_delay_steps"])
            effects = [step + delay + 1 for step in sorted(self.probe_schedule)]
            valid = bool(
                self.probe_window in WINDOWS
                and self.probe_id
                == f"single_step_{self.probe_window}_mode{self.probe_mode}"
                and self.probe_mode in MODES
                and self.probe_sign in SIGNS
                and self.probe_first_effect_state in {3, 17}
                and self.probe_cancel_effect_state
                == self.probe_first_effect_state + 1
                and effects
                == [self.probe_first_effect_state, self.probe_cancel_effect_state]
                and len(self.probe_schedule) == 2
                and math.isclose(
                    self.probe_amplitude, 0.0075, rel_tol=0.0, abs_tol=1e-15
                )
            )
        if not valid:
            raise ValueError("Stage4.2R3c3T13S1 controller contract invalid")
        if self.probe_schedule and not np.array_equal(
            np.sum(np.stack(list(self.probe_schedule.values())), axis=0),
            np.zeros(N_MODES, dtype=float),
        ):
            raise ValueError("Stage4.2R3c3T13S1 probe is not exactly zero net")

    def action(
        self, current_state: Mapping[str, Any]
    ) -> tuple[np.ndarray, dict[str, Any]]:
        task_step = self.step
        requested = self.probe_schedule.get(
            task_step, np.zeros(N_MODES, dtype=float)
        )
        original = t11.t1.r2.r3.solve_delay_aware_physical_correction
        probe_info: dict[str, Any] = {}
        currents = np.asarray(
            current_state["currents_a_tsc"], dtype=float
        ).reshape(N_COILS)

        def wrapped(*args: Any, **kwargs: Any) -> dict[str, Any]:
            out = original(*args, **kwargs)
            if not np.any(requested != 0.0):
                return out
            baseline = np.asarray(
                out["first_correction"], dtype=float
            ).reshape(N_MODES)
            nominal = np.asarray(
                kwargs["nominal_physical_coefficients"], dtype=float
            ).reshape(35, N_MODES)
            effect_step = min(
                int(out.get("effect_step", kwargs["current_step"])), 34
            )
            feedforward = nominal[effect_step]
            lower = np.asarray(
                self.base.stub.cfg["trajectory"]["coefficient_lower"],
                dtype=float,
            ).reshape(N_MODES)
            upper = np.asarray(
                self.base.stub.cfg["trajectory"]["coefficient_upper"],
                dtype=float,
            ).reshape(N_MODES)
            baseline_desired = np.clip(feedforward + baseline, lower, upper)
            modified_desired = np.clip(
                feedforward + baseline + requested, lower, upper
            )
            modified = modified_desired - feedforward
            baseline_scheduled = self.base.scheduler.solve_command(
                baseline_desired,
                currents,
                self.controller_gain,
                self.slew,
                enabled=True,
            )
            modified_scheduled = self.base.scheduler.solve_command(
                modified_desired,
                currents,
                self.controller_gain,
                self.slew,
                enabled=True,
            )
            target_increment = np.asarray(
                modified_scheduled["target_delta_a"], dtype=float
            ) - np.asarray(baseline_scheduled["target_delta_a"], dtype=float)
            predicted_increment = np.asarray(
                modified_scheduled["predicted_delta_a"], dtype=float
            ) - np.asarray(baseline_scheduled["predicted_delta_a"], dtype=float)
            scheduler_residual = float(
                np.max(np.abs(predicted_increment - target_increment))
            )
            updated = dict(out)
            updated["first_correction"] = modified
            sequence = np.asarray(
                updated.get(
                    "sequence_correction",
                    np.zeros((0, N_MODES), dtype=float),
                ),
                dtype=float,
            )
            if sequence.ndim == 2 and len(sequence):
                sequence = sequence.copy()
                sequence[0] = modified
                updated["sequence_correction"] = sequence
            probe_info.update(
                {
                    "requested_delta": requested.tolist(),
                    "applied_correction_delta": (modified - baseline).tolist(),
                    "applied_desired_delta": (
                        modified_desired - baseline_desired
                    ).tolist(),
                    "baseline_desired": baseline_desired.tolist(),
                    "modified_desired": modified_desired.tolist(),
                    "baseline_issued_mode_coefficients": np.asarray(
                        baseline_scheduled["command"], dtype=float
                    ).tolist(),
                    "modified_issued_mode_coefficients": np.asarray(
                        modified_scheduled["command"], dtype=float
                    ).tolist(),
                    "scheduler_increment_residual_A": scheduler_residual,
                    "scheduler_increment_exact": bool(
                        scheduler_residual <= self.scheduler_residual_max_a
                    ),
                    "solver_effect_step": effect_step,
                }
            )
            return updated

        t11.t1.r2.r3.solve_delay_aware_physical_correction = wrapped
        try:
            action, trace = (
                t11.t1.r3c1.AuthenticatedVisibleManifoldPhaseTaskController.action(
                    self, current_state
                )
            )
        finally:
            t11.t1.r2.r3.solve_delay_aware_physical_correction = original
        if np.any(requested != 0.0) and not probe_info:
            raise ValueError("scheduled T13S1 probe missed the online solver")
        applied_command = np.asarray(
            trace["applied_command_mode_coefficients"], dtype=float
        ).reshape(N_MODES)
        effective = self.actual_gain * applied_command + self.actuator_bias
        raw_mode_action = effective @ np.asarray(
            self.base.modes_tsc, dtype=float
        ).T
        mode_normalization_scale = 1.0
        max_abs = float(np.max(np.abs(raw_mode_action)))
        normalized = raw_mode_action.copy()
        if max_abs > 1.0:
            mode_normalization_scale = 1.0 / max_abs
            normalized *= mode_normalization_scale
        delta = normalized * float(self.base.max_delta_a)
        current_limit_scale = 1.0
        for coil in range(N_COILS):
            if delta[coil] > 0.0:
                current_limit_scale = min(
                    current_limit_scale,
                    max(
                        0.0,
                        (self.base.max_current[coil] - currents[coil])
                        / max(delta[coil], 1e-30),
                    ),
                )
            elif delta[coil] < 0.0:
                current_limit_scale = min(
                    current_limit_scale,
                    max(
                        0.0,
                        (self.base.min_current[coil] - currents[coil])
                        / min(delta[coil], -1e-30),
                    ),
                )
        current_limit_scale = float(np.clip(current_limit_scale, 0.0, 1.0))
        expected_action = normalized * current_limit_scale
        action_reconstruction_residual = float(
            np.max(np.abs(np.asarray(action, dtype=float) - expected_action))
        )
        zeros = np.zeros(N_MODES, dtype=float).tolist()
        trace.update(
            {
                "task_step": task_step,
                "baseline_controller_revision": t11.t1.r3c1.CONTROLLER_REVISION,
                "r3c3_identification_only": True,
                "r3c3t13s1_identification_only": True,
                "r3c3_probe_id": self.probe_id,
                "r3c3_probe_window": self.probe_window,
                "r3c3_probe_mode": self.probe_mode,
                "r3c3_probe_sign": self.probe_sign,
                "r3c3_probe_first_effect_state": self.probe_first_effect_state,
                "r3c3_probe_cancel_effect_state": self.probe_cancel_effect_state,
                "r3c3_probe_task_issue_step": task_step,
                "r3c3_probe_requested_delta": probe_info.get(
                    "requested_delta", zeros
                ),
                "r3c3_probe_applied_correction_delta": probe_info.get(
                    "applied_correction_delta", zeros
                ),
                "r3c3_probe_applied_desired_delta": probe_info.get(
                    "applied_desired_delta", zeros
                ),
                "r3c3_probe_issued": bool(probe_info),
                "r3c3_probe_scheduler_increment_residual_A": probe_info.get(
                    "scheduler_increment_residual_A", 0.0
                ),
                "r3c3_probe_scheduler_increment_exact": probe_info.get(
                    "scheduler_increment_exact", True
                ),
                "r3c3_probe_baseline_issued_mode_coefficients": probe_info.get(
                    "baseline_issued_mode_coefficients", zeros
                ),
                "r3c3_probe_modified_issued_mode_coefficients": probe_info.get(
                    "modified_issued_mode_coefficients", zeros
                ),
                "mode_action_normalization_scale": mode_normalization_scale,
                "mode_action_current_limit_scale": current_limit_scale,
                "mode_action_rescaled": bool(
                    mode_normalization_scale < 1.0 - 1e-12
                    or current_limit_scale < 1.0 - 1e-12
                ),
                "mode_action_reconstruction_residual": (
                    action_reconstruction_residual
                ),
                "future_probe_schedule_available_to_underlying_controller": False,
                "pair_or_history_label_used": False,
                "source_result_used": False,
                "source_action_used": False,
                "source_coil_current_used": False,
                "source_wire_current_used": False,
                "current_run_future_used": False,
                "hidden_wire_used": False,
            }
        )
        return action, trace


def _control_payload(
    ctx: Stage42R3C3T13S1Context, *, spec: Mapping[str, Any]
) -> dict[str, Any]:
    proxy = SimpleNamespace(
        source_ctx=ctx.base_ctx.base_ctx.source_ctx.source_ctx,
        cfg=ctx.base_ctx.base_ctx.cfg,
        paths=ctx.paths,
    )
    payload = t11.t1.r3c3._control_payload(proxy, spec=spec)
    train_cfg = copy.deepcopy(payload["train_cfg"])
    train_cfg.setdefault("episode", {})[
        "max_episode_steps"
    ] = OBSERVATION_HORIZON
    experiment_id = str(spec["experiment_id"])
    t11.t1.r3c3.atomic_write_json(
        ctx.paths.variants / f"train_{experiment_id}.json", train_cfg
    )
    payload["train_cfg"] = train_cfg
    payload["stage4_1r4_horizon_steps"] = OBSERVATION_HORIZON
    payload["variant_id"] = f"stage4_2r3c3t13s1_{experiment_id}"
    payload["stage4_2r3c3t13s1_restart_snapshot_dir"] = str(
        spec["restart_snapshot_dir"]
    )
    payload["stage4_2r3c3t13s1_snapshot_manifest_digest"] = str(
        spec["restart_snapshot_manifest_digest"]
    )
    t11.t1.r3c3.atomic_write_json(
        ctx.paths.variants / f"payload_{experiment_id}.json", payload
    )
    return payload


class LocalSingleStepTransitionProbeWorker:
    def __init__(
        self,
        payload: dict[str, Any],
        library: dict[str, Any],
        bundle: dict[str, Any],
        worker_id: str,
        selector_cfg: dict[str, Any],
    ):
        self.plant = t11.t1.r1.LocalPlantReplayWorker(
            payload, library, bundle, worker_id, selector_cfg
        )
        self.base = self.plant.base_worker
        self.bundle = bundle

    def close(self) -> None:
        self.plant.close()

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        failed = True
        result: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "campaign_identity": CAMPAIGN_IDENTITY,
            "controller_revision": CONTROLLER_REVISION,
            "underlying_controller_revision": t11.t1.r3c1.CONTROLLER_REVISION,
            "experiment_id": str(spec["experiment_id"]),
            "spec": copy.deepcopy(spec),
            "success": False,
            "completed": False,
            "failure_reason": "",
            "trajectory": [],
            "controller_trace": [],
        }
        try:
            horizon = int(spec["horizon_steps"])
            if (
                horizon != OBSERVATION_HORIZON
                or int(spec["formal_horizon_steps"])
                != _formal_horizon(float(spec["slew_scale"]))
                or int(self.base.env.max_episode_steps)
                != OBSERVATION_HORIZON
            ):
                raise ValueError("T13S1 observation/formal horizon changed")
            self.base.env.reset()
            zero_action = np.zeros(N_COILS, dtype=np.float32)
            initial = t11.t1.r1._state_record_full(
                self.base.env, 0, zero_action
            )
            trajectory = [initial]
            controller = SingleStepTransitionProbeController(
                self.base, self.bundle, _controller_spec(spec), initial
            )
            trace = []
            for step in range(horizon):
                action, controller_row = controller.action(trajectory[-1])
                _, _, terminated, truncated, info = self.base.env.step(action)
                next_state = t11.t1.r1._state_record_full(
                    self.base.env, step + 1, action
                )
                trajectory.append(next_state)
                trace.append(controller_row)
                controller.advance(next_state)
                if terminated:
                    raise RuntimeError(
                        str(info.get("failure_reason", "environment terminated"))
                    )
                if truncated and step + 1 < horizon:
                    raise RuntimeError(
                        "environment truncated before T13S1 horizon"
                    )
            schedule = {
                int(step): np.asarray(value, dtype=float)
                for step, value in spec[
                    "r3c3_probe_delta_by_task_issue_step"
                ].items()
            }
            issued = {
                int(row["task_step"]): row
                for row in trace
                if row.get("r3c3_probe_issued")
            }
            baseline = str(spec["r3c3_probe_id"]) == BASELINE_PROBE_ID
            expected_count = 0 if baseline else 2
            schedule_exact = bool(
                len(issued) == len(schedule) == expected_count
                and set(issued) == set(schedule)
                and all(
                    np.array_equal(
                        np.asarray(
                            issued[step]["r3c3_probe_requested_delta"],
                            dtype=float,
                        ),
                        value,
                    )
                    for step, value in schedule.items()
                )
            )
            requested = np.asarray(
                [
                    issued[step]["r3c3_probe_requested_delta"]
                    for step in sorted(issued)
                ],
                dtype=float,
            ).reshape(expected_count, N_MODES)
            applied = np.asarray(
                [
                    issued[step]["r3c3_probe_applied_desired_delta"]
                    for step in sorted(issued)
                ],
                dtype=float,
            ).reshape(expected_count, N_MODES)
            applied_exact = bool(
                np.allclose(requested, applied, rtol=0.0, atol=1e-12)
            )
            requested_net = (
                np.sum(requested, axis=0)
                if expected_count
                else np.zeros(N_MODES)
            )
            applied_net = (
                np.sum(applied, axis=0)
                if expected_count
                else np.zeros(N_MODES)
            )
            zero_net = bool(
                np.allclose(requested_net, np.zeros(N_MODES), rtol=0.0, atol=1e-12)
                and np.allclose(applied_net, np.zeros(N_MODES), rtol=0.0, atol=1e-12)
            )
            forbidden = any(
                bool(row.get(key))
                for row in trace
                for key in (
                    "future_measurement_used",
                    "hidden_wire_used",
                    "source_action_used",
                    "source_coil_current_used",
                    "source_wire_current_used",
                    "current_run_future_used",
                    "pair_or_history_label_used",
                    "source_result_used",
                    "future_probe_schedule_available_to_underlying_controller",
                )
            )
            scheduler_exact = all(
                bool(row.get("r3c3_probe_scheduler_increment_exact", True))
                for row in trace
            )
            mode_action_rescale_count = sum(
                bool(row.get("mode_action_rescaled")) for row in trace
            )
            success = bool(
                len(trajectory) == horizon + 1
                and len(trace) == horizon
                and not any(bool(row.get("abnormal")) for row in trajectory)
                and all(bool(row.get("computed_online")) for row in trace)
                and all(bool(row.get("solver_success")) for row in trace)
                and not forbidden
                and schedule_exact
                and applied_exact
                and zero_net
                and scheduler_exact
                and mode_action_rescale_count == 0
            )
            result.update(
                {
                    "success": success,
                    "completed": True,
                    "failure_reason": (
                        "" if success else "incomplete or invalid T13S1 rollout"
                    ),
                    "trajectory": trajectory,
                    "controller_trace": trace,
                    "hidden_history_control_summary": {
                        "fresh_controller_actor": True,
                        "fresh_tsc_process": True,
                        "full_tsc_hidden_state_loaded_from_sprsina": True,
                        "controller_history_initialization": (
                            "current_visible_state_only_at_task_step_zero"
                        ),
                        "controller_integral_initialization": "zero",
                        "controller_previous_correction_initialization": "zero",
                        "controller_delay_queue_initialization": (
                            "authenticated_visible_manifold_phase_aligned_nominal_prime"
                        ),
                        "reference_phase_start": controller.reference_phase_start,
                        "baseline_controller_revision": t11.t1.r3c1.CONTROLLER_REVISION,
                        "identification_only": True,
                        "extended_baseline": baseline,
                        "probe_id": controller.probe_id,
                        "probe_window": controller.probe_window,
                        "probe_sign": controller.probe_sign,
                        "probe_first_effect_state": controller.probe_first_effect_state,
                        "probe_cancel_effect_state": controller.probe_cancel_effect_state,
                        "probe_issue_steps": sorted(schedule),
                        "scheduled_probe_exact": schedule_exact,
                        "applied_probe_exact": applied_exact,
                        "requested_probe_net": requested_net.tolist(),
                        "applied_probe_net": applied_net.tolist(),
                        "requested_and_applied_zero_net": zero_net,
                        "scheduler_increment_exact": scheduler_exact,
                        "mode_action_rescale_count": mode_action_rescale_count,
                        "observation_horizon_steps": horizon,
                        "formal_horizon_steps": int(spec["formal_horizon_steps"]),
                        "probe_trajectory_allowed_in_expert_dataset": False,
                        "phase_selection": copy.deepcopy(controller.phase_selection),
                        "visible_reference_manifold_digest": (
                            controller.visible_reference_manifold_digest
                        ),
                        "visible_reference_source_experiment_id": (
                            controller.visible_reference_source_experiment_id
                        ),
                        "task_clock_starts_at_zero": True,
                        "formal_clock_shifted": False,
                        "hidden_wire_current_available_to_controller": False,
                        "full_wire_current_recorded_after_action_choice": True,
                        "online_action_computation": True,
                        "future_action_replay_used": False,
                        "future_measurement_used": False,
                        "source_action_used": False,
                        "source_coil_current_used": False,
                        "source_wire_current_used": False,
                        "current_run_future_used": False,
                        "pair_or_history_label_used": False,
                        "source_result_used": False,
                    },
                    "wall_time_s": time.time() - started,
                }
            )
            failed = not success
            return t11.t1._json_safe(result)
        except Exception as exc:
            result.update(
                {
                    "success": False,
                    "completed": True,
                    "failure_reason": repr(exc),
                    "traceback": traceback.format_exc(),
                    "wall_time_s": time.time() - started,
                }
            )
            return t11.t1._json_safe(result)
        finally:
            runner = getattr(self.base.env, "runner", None)
            if runner is not None:
                runner.cleanup_episode_workspace(
                    failed=failed,
                    reason="stage4_2r3c3t13s1_minimal_transition_sentinel",
                )


_CONTROL_RAY_ACTOR = None


def _control_ray_actor_class():
    global _CONTROL_RAY_ACTOR
    if _CONTROL_RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class Stage42R3C3T13S1ControlActor:
            def __init__(
                self, payload, library, bundle, worker_id, selector_cfg
            ):
                self.worker = LocalSingleStepTransitionProbeWorker(
                    payload, library, bundle, worker_id, selector_cfg
                )

            def evaluate(self, spec):
                return self.worker.evaluate(spec)

            def close(self):
                self.worker.close()
                return True

        _CONTROL_RAY_ACTOR = Stage42R3C3T13S1ControlActor
    return _CONTROL_RAY_ACTOR


def _result_complete(
    path: Path, expected_spec: Mapping[str, Any]
) -> bool:
    if not path.is_file():
        return False
    try:
        result = t11.t1.r3c3.read_json_gz(path)
        return bool(
            result.get("completed")
            and result.get("stage") == STAGE
            and result.get("campaign_identity") == CAMPAIGN_IDENTITY
            and result.get("controller_revision") == CONTROLLER_REVISION
            and result.get("experiment_id") == expected_spec["experiment_id"]
            and result.get("spec") == dict(expected_spec)
            and isinstance(result.get("success"), bool)
            and isinstance(result.get("trajectory"), list)
            and isinstance(result.get("controller_trace"), list)
        )
    except Exception:
        return False


def _structured_actor_failure(
    spec: Mapping[str, Any], exc: Exception
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "controller_revision": CONTROLLER_REVISION,
        "experiment_id": str(spec["experiment_id"]),
        "spec": copy.deepcopy(dict(spec)),
        "success": False,
        "completed": True,
        "failure_reason": repr(exc),
        "traceback": traceback.format_exc(),
        "trajectory": [],
        "controller_trace": [],
    }


def _evaluate_control(
    ctx: Stage42R3C3T13S1Context,
    specs: Sequence[dict[str, Any]],
    *,
    backend: str,
    resume: bool,
) -> list[dict[str, Any]]:
    ctx.paths.raw.mkdir(parents=True, exist_ok=True)
    library, bundle, selector = t11.t1.r1._library_bundle_selector(
        ctx.base_ctx.base_ctx.source_ctx.source_ctx.r1_ctx
    )
    pending = [
        spec
        for spec in specs
        if not (
            resume
            and _result_complete(
                ctx.paths.raw / f"{spec['experiment_id']}.json.gz", spec
            )
        )
    ]
    payloads = {
        str(spec["experiment_id"]): _control_payload(ctx, spec=spec)
        for spec in specs
    }
    if backend == "serial":
        for index, spec in enumerate(pending):
            worker = LocalSingleStepTransitionProbeWorker(
                payloads[str(spec["experiment_id"])],
                library,
                bundle,
                f"stage42r3c3t13s1_serial_{index:03d}",
                selector,
            )
            try:
                result = worker.evaluate(spec)
            finally:
                worker.close()
            t11.t1.r3c3.atomic_write_json_gz(
                ctx.paths.raw / f"{spec['experiment_id']}.json.gz", result
            )
            print(
                f"[Stage4.2R3c3T13S1] {index + 1}/{len(pending)}",
                flush=True,
            )
    elif backend == "ray" and pending:
        import ray

        plan = ensure_ray_worker_plan(
            ray,
            requested_workers=int(ctx.cfg["parallel"]["n_workers"]),
            pending_tasks=len(pending),
            ray_tmpdir=(
                os.environ.get("RAY_TMPDIR")
                or ctx.cfg["storage"].get("ray_tmpdir")
            ),
            log_prefix="[Stage4.2R3c3T13S1]",
        )
        Actor = _control_ray_actor_class()
        completed = 0
        print(
            "[Stage4.2R3c3T13S1] "
            f"maximum_actor_count={plan.actor_count} pending={len(pending)}",
            flush=True,
        )
        for batch_start in range(0, len(pending), plan.actor_count):
            batch = pending[batch_start : batch_start + plan.actor_count]
            actors = []
            refs = {}
            for offset, spec in enumerate(batch):
                index = batch_start + offset
                actor = Actor.remote(
                    payloads[str(spec["experiment_id"])],
                    library,
                    bundle,
                    f"stage42r3c3t13s1_{index:03d}",
                    selector,
                )
                actors.append(actor)
                refs[actor.evaluate.remote(spec)] = spec
            try:
                while refs:
                    ready, _ = ray.wait(
                        list(refs), num_returns=1, timeout=30.0
                    )
                    if not ready:
                        print(
                            f"[Stage4.2R3c3T13S1] waiting "
                            f"{completed}/{len(pending)}",
                            flush=True,
                        )
                        continue
                    for ref in ready:
                        spec = refs.pop(ref)
                        try:
                            result = ray.get(ref)
                        except Exception as exc:
                            result = _structured_actor_failure(spec, exc)
                        t11.t1.r3c3.atomic_write_json_gz(
                            ctx.paths.raw
                            / f"{spec['experiment_id']}.json.gz",
                            result,
                        )
                        completed += 1
                        if completed % 4 == 0 or not refs:
                            print(
                                f"[Stage4.2R3c3T13S1] "
                                f"{completed}/{len(pending)}",
                                flush=True,
                            )
            finally:
                t11.t1.r3b.s2._close_ray_actors(
                    actors,
                    timeout_s=float(
                        ctx.cfg["storage"].get(
                            "actor_close_timeout_s", 1800.0
                        )
                    ),
                )
    elif backend not in {"serial", "ray"}:
        raise ValueError("backend must be serial or ray")
    return [
        t11.t1.r3c3.read_json_gz(
            ctx.paths.raw / f"{spec['experiment_id']}.json.gz"
        )
        for spec in specs
    ]


def _formal_prefix_result(result: Mapping[str, Any]) -> dict[str, Any]:
    horizon = int(result["spec"]["formal_horizon_steps"])
    truncated = copy.deepcopy(dict(result))
    truncated["trajectory"] = list(result["trajectory"])[: horizon + 1]
    truncated["controller_trace"] = list(result["controller_trace"])[:horizon]
    truncated["spec"] = copy.deepcopy(dict(result["spec"]))
    truncated["spec"]["horizon_steps"] = horizon
    return truncated


def _phase_trace_valid(result: Mapping[str, Any]) -> dict[str, Any]:
    base = t11.t1.r3c1._phase_trace_valid(result)
    trace = list(result.get("controller_trace") or [])
    spec = dict(result.get("spec") or {})
    schedule = {
        int(step): np.asarray(value, dtype=float).reshape(N_MODES)
        for step, value in (
            spec.get("r3c3_probe_delta_by_task_issue_step") or {}
        ).items()
    }
    baseline = str(spec.get("r3c3_probe_id")) == BASELINE_PROBE_ID
    expected_count = 0 if baseline else 2
    requested_rows = []
    applied_rows = []
    exact = bool(
        len(trace) == OBSERVATION_HORIZON
        and len(schedule) == expected_count
    )
    solver_failures = 0
    forbidden_count = 0
    issued_count = 0
    scheduler_failure_count = 0
    rescale_count = 0
    max_scheduler_residual = 0.0
    for row in trace:
        step = int(row.get("task_step", -1))
        expected = schedule.get(step, np.zeros(N_MODES))
        requested = np.asarray(
            row.get("r3c3_probe_requested_delta", []), dtype=float
        ).reshape(-1)
        applied = np.asarray(
            row.get("r3c3_probe_applied_desired_delta", []), dtype=float
        ).reshape(-1)
        issued = bool(row.get("r3c3_probe_issued"))
        exact = bool(
            exact
            and requested.shape == applied.shape == (N_MODES,)
            and issued == (step in schedule)
            and np.array_equal(requested, expected)
            and bool(row.get("r3c3t13s1_identification_only"))
            and not bool(
                row.get(
                    "future_probe_schedule_available_to_underlying_controller"
                )
            )
        )
        if issued:
            issued_count += 1
            requested_rows.append(requested)
            applied_rows.append(applied)
            residual = float(
                row.get("r3c3_probe_scheduler_increment_residual_A", math.inf)
            )
            max_scheduler_residual = max(max_scheduler_residual, residual)
            scheduler_failure_count += not bool(
                row.get("r3c3_probe_scheduler_increment_exact")
            )
        solver_failures += not bool(row.get("solver_success"))
        rescale_count += bool(row.get("mode_action_rescaled"))
        forbidden_count += any(
            bool(row.get(key))
            for key in (
                "pair_or_history_label_used",
                "source_result_used",
                "hidden_wire_used",
                "source_action_used",
                "source_coil_current_used",
                "source_wire_current_used",
                "current_run_future_used",
                "future_measurement_used",
                "future_probe_schedule_available_to_underlying_controller",
            )
        )
    requested_array = np.asarray(requested_rows, dtype=float).reshape(
        expected_count, N_MODES
    )
    applied_array = np.asarray(applied_rows, dtype=float).reshape(
        expected_count, N_MODES
    )
    applied_exact = bool(
        np.allclose(requested_array, applied_array, rtol=0.0, atol=1e-12)
    )
    requested_net = np.sum(requested_array, axis=0)
    applied_net = np.sum(applied_array, axis=0)
    zero_net = bool(
        np.allclose(requested_net, np.zeros(N_MODES), rtol=0.0, atol=1e-12)
        and np.allclose(applied_net, np.zeros(N_MODES), rtol=0.0, atol=1e-12)
    )
    passed = bool(
        base["passed"]
        and exact
        and issued_count == expected_count
        and applied_exact
        and zero_net
        and forbidden_count == 0
        and solver_failures == 0
        and scheduler_failure_count == 0
        and rescale_count == 0
    )
    return {
        **base,
        "passed": passed,
        "probe_trace_exact": exact,
        "probe_issued_count": issued_count,
        "probe_applied_exact": applied_exact,
        "probe_requested_net": requested_net.tolist(),
        "probe_applied_net": applied_net.tolist(),
        "probe_zero_net": zero_net,
        "forbidden_trace_count": forbidden_count,
        "solver_failure_count": solver_failures,
        "scheduler_failure_count": scheduler_failure_count,
        "maximum_scheduler_increment_residual_A": max_scheduler_residual,
        "mode_action_rescale_count": rescale_count,
        "extended_baseline": baseline,
    }


def _stage34_identity(
    ctx: Stage42R3C3T13S1Context,
) -> tuple[np.ndarray, float, float]:
    r13_ctx = t11.t1.r1._r13_ctx(
        ctx.base_ctx.base_ctx.source_ctx.source_ctx.r1_ctx
    )
    base34 = (
        r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34
    )
    modes = np.asarray(base34.modes_tsc, dtype=float).reshape(N_COILS, N_MODES)
    max_delta = float(base34.max_delta_a)
    dt_s = float(base34.env_cfg["dt_ms"]) / 1000.0
    if float(np.max(np.abs(modes.T @ modes - np.eye(N_MODES)))) > 1e-12:
        raise ValueError("T13S1 authenticated mode basis is not orthonormal")
    return modes, max_delta, dt_s


def _command_modal_residual(
    result: Mapping[str, Any], modes: np.ndarray, max_delta_a: float
) -> float:
    trace = list(result.get("controller_trace") or [])
    if not trace:
        return math.inf
    actions = np.asarray(
        [row["action_norm_tsc"] for row in trace], dtype=float
    ).reshape(-1, N_COILS)
    slew = float(result["spec"]["slew_scale"])
    commands = actions * max_delta_a * slew
    modal = (commands / max_delta_a) @ modes
    reconstructed = max_delta_a * (modal @ modes.T)
    return float(np.max(np.abs(commands - reconstructed)))


def _feature_arrays(
    result: Mapping[str, Any], dt_s: float
) -> np.ndarray:
    y, velocity = t11._arrays(result, dt_s)
    return np.column_stack(
        [y[:, 0], y[:, 1], velocity[:, 0], velocity[:, 1], y[:, 2]]
    )


def _rmse(array: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.asarray(array, dtype=float) ** 2)))


def _signal_floor(n_states: int) -> float:
    return math.sqrt(
        2 * n_states * (1e-9 / 0.03) ** 2
        + 2 * n_states * (1e-7 / 0.1) ** 2
        + n_states * (1e-4 / 2000.0) ** 2
    )


def _expected_context_row(
    cfg: Mapping[str, Any], key: tuple[Any, ...]
) -> Mapping[str, Any]:
    rows = [
        row
        for row in cfg["bookend_contexts"]
        if _frozen_context_key(row) == key
    ]
    if len(rows) != 1:
        raise ValueError("T13S1 frozen context lookup mismatch")
    return rows[0]


def summarize_control(
    ctx: Stage42R3C3T13S1Context,
    results: Sequence[Mapping[str, Any]],
    selected_pairs: Sequence[Mapping[str, Any]],
    *,
    write_outputs: bool = True,
) -> dict[str, Any]:
    expected = int(ctx.cfg["control_matrix"]["expected_rollouts"])
    probe_cfg = ctx.cfg["identification_probe"]
    history_cfg = probe_cfg["matched_hidden_history"]
    modes, max_delta_a, dt_s = _stage34_identity(ctx)
    state_map = t11.t1.r3b._selected_state_map(selected_pairs)
    base_source_ctx = ctx.base_ctx.base_ctx.source_ctx.source_ctx
    rows = []
    by_context: dict[tuple[Any, ...], dict[str, Mapping[str, Any]]] = (
        defaultdict(dict)
    )
    for result in results:
        spec = result["spec"]
        baseline = str(spec["r3c3_probe_id"]) == BASELINE_PROBE_ID
        name = (
            BASELINE_PROBE_ID
            if baseline
            else (
                f"{spec['r3c3_probe_window']}:"
                f"{spec['r3c3_probe_mode']}:{spec['r3c3_probe_sign']}"
            )
        )
        by_context[_context_key(spec)][name] = result
        state_id = str(spec["state_generation_experiment_id"])
        base = t11.t1.r3b._control_row(
            base_source_ctx,
            _formal_prefix_result(result),
            state_map[state_id],
        )
        phase = _phase_trace_valid(result)
        formal = (
            t11._formal_prefix_metrics(ctx.base_ctx, result)
            if bool(result.get("success"))
            else {}
        )
        prefix_exact = bool(
            baseline
            and result.get("success")
            and t11._source_prefix_exact(ctx.base_ctx, result)
        )
        expected_row = _expected_context_row(ctx.cfg, _context_key(spec))
        expected_status = bool(expected_row["expected_formal_pass"])
        expected_margin = float(
            expected_row["expected_formal_minimum_signed_margin"]
        )
        margin = (
            float(formal["stage3_4_tracking_minimum_signed_margin"])
            if formal
            else None
        )
        baseline_formal_reproduced = bool(
            baseline
            and formal
            and bool(formal["stage3_4_target_tracking_pass"])
            == expected_status
            and margin is not None
            and abs(margin - expected_margin)
            <= float(probe_cfg["baseline_margin_reproduction_atol"])
        )
        modal_residual = (
            _command_modal_residual(result, modes, max_delta_a)
            if bool(result.get("success"))
            else None
        )
        modal_pass = bool(
            modal_residual is not None
            and modal_residual
            <= float(probe_cfg["command_mode_subspace_residual_max_A"])
        )
        execution_pass = bool(
            result.get("success")
            and base["fresh_controller"]
            and base["fresh_tsc_process"]
            and base["initial_restart_exact"]
            and base["controller_trace_causal"]
            and phase["passed"]
            and modal_pass
            and (
                not baseline
                or (prefix_exact and baseline_formal_reproduced)
            )
        )
        if not bool(result.get("success")):
            failure_class = "runtime_or_environment_error"
        elif not bool(base["initial_restart_exact"]):
            failure_class = "plant_restart_fidelity_failure"
        elif not bool(base["controller_trace_causal"]):
            failure_class = "controller_causality_failure"
        elif not bool(phase["passed"]):
            failure_class = "identification_probe_execution_failure"
        elif not modal_pass:
            failure_class = "command_subspace_execution_failure"
        elif baseline and not prefix_exact:
            failure_class = "extended_baseline_prefix_mismatch"
        elif baseline and not baseline_formal_reproduced:
            failure_class = "baseline_formal_reproduction_mismatch"
        else:
            failure_class = ""
        rows.append(
            {
                **base,
                "probe_id": str(spec["r3c3_probe_id"]),
                "probe_window": str(spec["r3c3_probe_window"]),
                "probe_mode": int(spec["r3c3_probe_mode"]),
                "probe_sign": int(spec["r3c3_probe_sign"]),
                "extended_baseline": baseline,
                "extended_baseline_prefix_exact": prefix_exact,
                "baseline_formal_reproduced": baseline_formal_reproduced,
                "expected_formal_contract_pass": expected_status,
                "expected_formal_minimum_signed_margin": expected_margin,
                "formal_contract_pass": bool(
                    formal.get("stage3_4_target_tracking_pass", False)
                ),
                "formal_minimum_signed_margin": margin,
                "phase_trace_valid": bool(phase["passed"]),
                "probe_trace_exact": bool(phase["probe_trace_exact"]),
                "probe_issued_count": int(phase["probe_issued_count"]),
                "probe_applied_exact": bool(phase["probe_applied_exact"]),
                "probe_zero_net": bool(phase["probe_zero_net"]),
                "solver_failure_count": int(phase["solver_failure_count"]),
                "forbidden_trace_count": int(phase["forbidden_trace_count"]),
                "scheduler_failure_count": int(
                    phase["scheduler_failure_count"]
                ),
                "maximum_scheduler_increment_residual_A": float(
                    phase["maximum_scheduler_increment_residual_A"]
                ),
                "mode_action_rescale_count": int(
                    phase["mode_action_rescale_count"]
                ),
                "command_mode_subspace_residual_A": modal_residual,
                "command_mode_subspace_pass": modal_pass,
                "max_current_utilization": (
                    t11._full_current_utilization(ctx.base_ctx, result)
                    if bool(result.get("success"))
                    else None
                ),
                "execution_pass": execution_pass,
                "failure_class": failure_class,
                "passed": execution_pass,
                "identification_only": True,
                "probe_trajectory_allowed_in_expert_dataset": False,
            }
        )

    baselines: dict[tuple[Any, ...], Mapping[str, Any]] = {}
    signed_groups: dict[
        tuple[Any, ...], dict[tuple[str, int], dict[int, Mapping[str, Any]]]
    ] = defaultdict(lambda: defaultdict(dict))
    for key, members in by_context.items():
        if BASELINE_PROBE_ID in members:
            baselines[key] = members[BASELINE_PROBE_ID]
        for name, result in members.items():
            if name == BASELINE_PROBE_ID:
                continue
            window, mode, sign = name.split(":")
            signed_groups[key][(window, int(mode))][int(sign)] = result
    if len(baselines) != 4:
        raise ValueError("T13S1 baseline coverage mismatch")

    response_rows = []
    odd_by_key: dict[tuple[Any, ...], dict[str, Any]] = {}
    scales = np.asarray(probe_cfg["response_scales"], dtype=float)
    for context_key in sorted(signed_groups):
        baseline_result = baselines[context_key]
        baseline_feature = _feature_arrays(baseline_result, dt_s)
        formal_end = _formal_horizon(float(context_key[4]))
        section = slice(int(probe_cfg["response_start_state"]), formal_end + 1)
        n_states = formal_end - int(probe_cfg["response_start_state"]) + 1
        epsilon = _signal_floor(n_states)
        for window in WINDOWS:
            for mode in MODES:
                signed = signed_groups[context_key].get((window, mode), {})
                row: dict[str, Any] = {
                    "pair_id": context_key[0],
                    "history_member": context_key[1],
                    "target_id": context_key[2],
                    "actual_delay_steps": context_key[3],
                    "actual_slew_scale": context_key[4],
                    "probe_window": window,
                    "probe_mode": mode,
                    "signed_member_count": len(signed),
                    "response_available": False,
                    "signal_pass": False,
                    "central_symmetry_pass": False,
                    "pre_effect_causality_pass": False,
                    "first_and_cancel_effect_schedule_pass": False,
                }
                if (
                    set(signed) == {-1, 1}
                    and bool(baseline_result.get("success"))
                    and all(bool(item.get("success")) for item in signed.values())
                ):
                    plus = _feature_arrays(signed[1], dt_s)
                    minus = _feature_arrays(signed[-1], dt_s)
                    initial_exact = bool(
                        np.array_equal(
                            np.asarray(signed[1]["trajectory"][0]["currents_a_tsc"]),
                            np.asarray(signed[-1]["trajectory"][0]["currents_a_tsc"]),
                        )
                        and np.array_equal(
                            np.asarray(signed[1]["trajectory"][0]["wire_currents_a"]),
                            np.asarray(signed[-1]["trajectory"][0]["wire_currents_a"]),
                        )
                    )
                    first = int(
                        signed[1]["spec"]["r3c3_probe_first_effect_state"]
                    )
                    cancel = int(
                        signed[1]["spec"]["r3c3_probe_cancel_effect_state"]
                    )
                    plus_pre = plus[:first] - baseline_feature[:first]
                    minus_pre = minus[:first] - baseline_feature[:first]
                    pre = np.concatenate([plus_pre, minus_pre], axis=0)
                    pre_position = float(np.max(np.abs(pre[:, :2])))
                    pre_velocity = float(np.max(np.abs(pre[:, 2:4])))
                    pre_ip = float(np.max(np.abs(pre[:, 4])))
                    pre_pass = bool(
                        pre_position
                        <= float(probe_cfg["pre_effect_position_max_m"])
                        and pre_velocity
                        <= float(probe_cfg["pre_effect_velocity_max_m_per_s"])
                        and pre_ip <= float(probe_cfg["pre_effect_ip_max_A"])
                    )
                    delay = int(signed[1]["spec"]["action_delay_steps"])
                    issue_steps = sorted(
                        int(step)
                        for step in signed[1]["spec"][
                            "r3c3_probe_delta_by_task_issue_step"
                        ]
                    )
                    effects = [step + delay + 1 for step in issue_steps]
                    effect_schedule_pass = bool(
                        effects == [first, cancel]
                        and cancel == first + 1
                        and first == (3 if window == "transport" else 17)
                    )
                    odd = (plus - minus) / 2.0
                    even = (plus + minus) / 2.0 - baseline_feature
                    odd_scaled = odd[section] / scales[None, :]
                    even_scaled = even[section] / scales[None, :]
                    odd_norm = float(np.linalg.norm(odd_scaled.reshape(-1)))
                    even_norm = float(np.linalg.norm(even_scaled.reshape(-1)))
                    signal_pass = bool(
                        odd_norm
                        >= float(probe_cfg["signal_floor_multiplier"]) * epsilon
                    )
                    relative_even = even_norm / max(odd_norm, epsilon)
                    velocity_rmse = _rmse(even[section, 2:4])
                    position_rmse = _rmse(even[section, :2])
                    ip_rmse = _rmse(even[section, 4])
                    central_pass = bool(
                        initial_exact
                        and pre_pass
                        and effect_schedule_pass
                        and signal_pass
                        and relative_even
                        <= float(probe_cfg["maximum_even_to_odd_scaled_l2"])
                        and velocity_rmse
                        <= float(
                            probe_cfg["maximum_even_velocity_rmse_m_per_s"]
                        )
                        and position_rmse
                        <= float(probe_cfg["maximum_even_position_rmse_m"])
                        and ip_rmse
                        <= float(probe_cfg["maximum_even_ip_rmse_A"])
                    )
                    row.update(
                        {
                            "response_available": True,
                            "baseline_initial_state_exact": initial_exact,
                            "first_effect_state": first,
                            "cancel_effect_state": cancel,
                            "first_and_cancel_effect_schedule_pass": effect_schedule_pass,
                            "maximum_pre_effect_position_m": pre_position,
                            "maximum_pre_effect_velocity_m_per_s": pre_velocity,
                            "maximum_pre_effect_ip_A": pre_ip,
                            "pre_effect_causality_pass": pre_pass,
                            "response_state_count": n_states,
                            "scaled_numerical_floor": epsilon,
                            "scaled_odd_l2_norm": odd_norm,
                            "scaled_even_l2_norm": even_norm,
                            "signal_pass": signal_pass,
                            "even_to_odd_scaled_l2": relative_even,
                            "even_velocity_rmse_m_per_s": velocity_rmse,
                            "even_position_rmse_m": position_rmse,
                            "even_ip_rmse_A": ip_rmse,
                            "central_symmetry_pass": central_pass,
                        }
                    )
                    odd_by_key[(*context_key, window, mode)] = {
                        "odd": odd,
                        "scaled_column": odd_scaled.reshape(-1),
                        "signal_pass": signal_pass,
                        "first_effect_state": first,
                        "formal_end_state": formal_end,
                    }
                response_rows.append(row)

    history_groups: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = (
        defaultdict(dict)
    )
    for key, response in odd_by_key.items():
        history_groups[(key[0], key[2], key[3], key[4], key[5], key[6])][
            key[1]
        ] = response
    history_rows = []
    for key in sorted(history_groups):
        members = history_groups[key]
        row: dict[str, Any] = {
            "pair_id": key[0],
            "target_id": key[1],
            "actual_delay_steps": key[2],
            "actual_slew_scale": key[3],
            "probe_window": key[4],
            "probe_mode": key[5],
            "history_member_count": len(members),
            "matched_hidden_history_pass": False,
        }
        if set(members) == {"plus_first", "minus_first"}:
            plus = np.asarray(members["plus_first"]["odd"], dtype=float)
            minus = np.asarray(members["minus_first"]["odd"], dtype=float)
            formal_end = int(members["minus_first"]["formal_end_state"])
            section = slice(int(probe_cfg["response_start_state"]), formal_end + 1)
            difference = plus[section] - minus[section]
            minus_scaled = minus[section] / scales[None, :]
            diff_scaled = difference / scales[None, :]
            relative = float(
                np.linalg.norm(diff_scaled.reshape(-1))
                / max(
                    np.linalg.norm(minus_scaled.reshape(-1)),
                    _signal_floor(len(minus_scaled)),
                )
            )
            velocity_rmse = _rmse(difference[:, 2:4])
            position_rmse = _rmse(difference[:, :2])
            ip_rmse = _rmse(difference[:, 4])
            plus_speed = np.linalg.norm(plus[section, 2:4], axis=1)
            minus_speed = np.linalg.norm(minus[section, 2:4], axis=1)
            endpoint = float(
                abs(
                    math.sqrt(float(np.mean(plus_speed[-4:] ** 2)))
                    - math.sqrt(float(np.mean(minus_speed[-4:] ** 2)))
                )
            )
            final = float(abs(plus_speed[-1] - minus_speed[-1]))
            passed = bool(
                members["plus_first"]["signal_pass"]
                and members["minus_first"]["signal_pass"]
                and relative
                <= float(
                    history_cfg["maximum_scaled_relative_response_difference"]
                )
                and velocity_rmse
                <= float(
                    history_cfg["maximum_velocity_component_rmse_m_per_s"]
                )
                and endpoint
                <= float(
                    history_cfg[
                        "maximum_endpoint_late_response_speed_error_m_per_s"
                    ]
                )
                and final
                <= float(
                    history_cfg["maximum_final_response_speed_error_m_per_s"]
                )
                and position_rmse
                <= float(history_cfg["maximum_position_rmse_m"])
                and ip_rmse <= float(history_cfg["maximum_ip_rmse_A"])
            )
            row.update(
                {
                    "scaled_relative_response_difference": relative,
                    "velocity_component_rmse_m_per_s": velocity_rmse,
                    "endpoint_late_response_speed_error_m_per_s": endpoint,
                    "final_response_speed_error_m_per_s": final,
                    "position_rmse_m": position_rmse,
                    "ip_rmse_A": ip_rmse,
                    "matched_hidden_history_pass": passed,
                }
            )
        history_rows.append(row)

    condition_rows = []
    for context_key in sorted(baselines):
        columns = []
        metadata = []
        all_signal = True
        for window in WINDOWS:
            for mode in MODES:
                response = odd_by_key.get((*context_key, window, mode))
                if response is None:
                    all_signal = False
                    continue
                column = np.asarray(response["scaled_column"], dtype=float)
                norm = float(np.linalg.norm(column))
                all_signal = bool(all_signal and response["signal_pass"] and norm > 0.0)
                columns.append(column / max(norm, 1e-300))
                metadata.append((window, mode, norm, column))
        rank = None
        condition = None
        passed = False
        if len(columns) == 6 and len({column.shape for column in columns}) == 1:
            matrix = np.stack(columns, axis=1)
            rank = int(np.linalg.matrix_rank(matrix))
            condition = float(np.linalg.cond(matrix))
            passed = bool(
                all_signal
                and rank == int(probe_cfg["required_local_response_rank"])
                and math.isfinite(condition)
                and condition
                <= float(probe_cfg["maximum_normalized_condition_number"])
            )
        geometry = []
        by_window_mode = {(w, m): (n, c) for w, m, n, c in metadata}
        for mode in MODES:
            if ("transport", mode) in by_window_mode and (
                "braking",
                mode,
            ) in by_window_mode:
                transport_norm, transport = by_window_mode[("transport", mode)]
                braking_norm, braking = by_window_mode[("braking", mode)]
                cosine = float(
                    np.dot(transport, braking)
                    / max(transport_norm * braking_norm, 1e-300)
                )
                geometry.append(
                    {
                        "mode": mode,
                        "transport_braking_cosine": cosine,
                        "transport_to_braking_norm_ratio": (
                            transport_norm / max(braking_norm, 1e-300)
                        ),
                    }
                )
        condition_rows.append(
            {
                "pair_id": context_key[0],
                "history_member": context_key[1],
                "target_id": context_key[2],
                "actual_delay_steps": context_key[3],
                "actual_slew_scale": context_key[4],
                "basis_count": len(columns),
                "all_columns_signal_pass": all_signal,
                "normalized_response_matrix_rank": rank,
                "normalized_response_condition_number": condition,
                "transport_braking_geometry": geometry,
                "condition_number_pass": passed,
            }
        )

    def count(values: Sequence[Mapping[str, Any]], field: str) -> int:
        return sum(bool(row.get(field)) for row in values)

    current_values = [
        float(row["max_current_utilization"])
        for row in rows
        if row["max_current_utilization"] is not None
    ]
    maximum_current = max(current_values) if current_values else None
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "phase": "minimal_transition_sentinel",
        "identification_only": True,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "development_set_only": True,
        "independent_hidden_history_confirmation": False,
        "observation_horizon_steps": OBSERVATION_HORIZON,
        "formal_timing_unchanged": True,
        "expected_rollouts": expected,
        "n_rollouts": len(rows),
        "execution_pass_count": count(rows, "execution_pass"),
        "extended_baseline_prefix_exact_count": count(
            rows, "extended_baseline_prefix_exact"
        ),
        "baseline_formal_reproduction_count": count(
            rows, "baseline_formal_reproduced"
        ),
        "runtime_or_environment_error_count": sum(
            row["failure_class"] == "runtime_or_environment_error"
            for row in rows
        ),
        "plant_restart_fidelity_failure_count": sum(
            row["failure_class"] == "plant_restart_fidelity_failure"
            for row in rows
        ),
        "controller_causality_failure_count": sum(
            row["failure_class"] == "controller_causality_failure"
            for row in rows
        ),
        "identification_probe_execution_failure_count": sum(
            row["failure_class"] == "identification_probe_execution_failure"
            for row in rows
        ),
        "command_subspace_execution_failure_count": sum(
            row["failure_class"] == "command_subspace_execution_failure"
            for row in rows
        ),
        "extended_baseline_prefix_mismatch_count": sum(
            row["failure_class"] == "extended_baseline_prefix_mismatch"
            for row in rows
        ),
        "baseline_formal_reproduction_mismatch_count": sum(
            row["failure_class"] == "baseline_formal_reproduction_mismatch"
            for row in rows
        ),
        "forbidden_controller_input_count": sum(
            int(row["forbidden_trace_count"]) for row in rows
        ),
        "solver_failure_count": sum(
            int(row["solver_failure_count"]) for row in rows
        ),
        "scheduler_failure_count": sum(
            int(row["scheduler_failure_count"]) for row in rows
        ),
        "mode_action_rescale_count": sum(
            int(row["mode_action_rescale_count"]) for row in rows
        ),
        "maximum_command_mode_subspace_residual_A": max(
            (
                float(row["command_mode_subspace_residual_A"])
                for row in rows
                if row["command_mode_subspace_residual_A"] is not None
            ),
            default=None,
        ),
        "formal_contract_pass_count": count(rows, "formal_contract_pass"),
        "formal_tracking_is_acceptance_gate_for_probes": False,
        "response_group_count": len(response_rows),
        "expected_response_group_count": 24,
        "signal_pass_count": count(response_rows, "signal_pass"),
        "pre_effect_causality_pass_count": count(
            response_rows, "pre_effect_causality_pass"
        ),
        "central_symmetry_pass_count": count(
            response_rows, "central_symmetry_pass"
        ),
        "matched_hidden_history_group_count": len(history_rows),
        "expected_matched_hidden_history_group_count": 12,
        "matched_hidden_history_pass_count": count(
            history_rows, "matched_hidden_history_pass"
        ),
        "local_response_matrix_count": len(condition_rows),
        "expected_local_response_matrix_count": 4,
        "local_response_matrix_pass_count": count(
            condition_rows, "condition_number_pass"
        ),
        "maximum_normalized_condition_number": max(
            (
                float(row["normalized_response_condition_number"])
                for row in condition_rows
                if row["normalized_response_condition_number"] is not None
            ),
            default=None,
        ),
        "maximum_current_utilization": maximum_current,
        "maximum_current_utilization_allowed": float(
            probe_cfg["maximum_current_utilization"]
        ),
    }
    summary["execution_gate_passed"] = bool(
        len(rows) == expected
        and summary["execution_pass_count"] == expected
        and summary["extended_baseline_prefix_exact_count"] == 4
        and summary["baseline_formal_reproduction_count"] == 4
        and summary["forbidden_controller_input_count"] == 0
        and summary["solver_failure_count"] == 0
        and summary["scheduler_failure_count"] == 0
        and summary["mode_action_rescale_count"] == 0
    )
    summary["signal_gate_passed"] = bool(
        len(response_rows) == summary["signal_pass_count"] == 24
    )
    summary["pre_effect_causality_gate_passed"] = bool(
        len(response_rows)
        == summary["pre_effect_causality_pass_count"]
        == 24
    )
    summary["central_symmetry_gate_passed"] = bool(
        len(response_rows) == summary["central_symmetry_pass_count"] == 24
    )
    summary["matched_hidden_history_gate_passed"] = bool(
        len(history_rows)
        == summary["matched_hidden_history_pass_count"]
        == 12
    )
    summary["local_identifiability_gate_passed"] = bool(
        len(condition_rows)
        == summary["local_response_matrix_pass_count"]
        == 4
    )
    summary["current_utilization_pass"] = bool(
        maximum_current is not None
        and maximum_current
        <= float(probe_cfg["maximum_current_utilization"])
    )
    summary["passed"] = bool(
        summary["execution_gate_passed"]
        and summary["signal_gate_passed"]
        and summary["pre_effect_causality_gate_passed"]
        and summary["central_symmetry_gate_passed"]
        and summary["matched_hidden_history_gate_passed"]
        and summary["local_identifiability_gate_passed"]
        and summary["current_utilization_pass"]
    )
    if write_outputs:
        outputs = (
            ("results", rows),
            ("central_response_results", response_rows),
            ("matched_hidden_history_results", history_rows),
            ("local_identifiability_results", condition_rows),
        )
        ctx.paths.control.mkdir(parents=True, exist_ok=True)
        for name, values in outputs:
            t11.t1.r3c3.atomic_write_json(
                ctx.paths.control / f"{name}.json", values
            )
            t11.t1.r3c3.write_csv(
                ctx.paths.control / f"{name}.csv", values
            )
        t11.t1.r3c3.atomic_write_json(
            ctx.paths.control / "summary.json", summary
        )
    return summary


def _package_files(ctx: Stage42R3C3T13S1Context) -> list[Path]:
    project = _project_root()
    manifest = t11.t1.r3c3.read_json(project / "PACKAGE_MANIFEST.json")
    paths = [project / str(relative) for relative in manifest["file_inventory"]]
    required = {
        project
        / "configs/stage4_2r3c3t13s1_minimal_transition_sentinel_500ms.json",
        project
        / "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s1_minimal_transition_sentinel.py",
        project
        / "scripts/stage4_2r3c3t13s1_minimal_transition_sentinel.py",
        project / "scripts/stage4_2r3c3t13s1_server_postprocess.py",
        project / "scripts/stage4_2r3c3t13s1_shell_common.sh",
        project / "run_stage4_2r3c3t13s1_common.sh",
        project / "run_stage4_2r3c3t13s1_offline.sh",
        project / "run_stage4_2r3c3t13s1_server_postprocess.sh",
        project / "run_stage4_2r3c3t13s1_native.sh",
        project / "run_stage4_2r3c3t13s1_nohup.sh",
        project / "run_stage4_2r3c3t13s1_self_test.sh",
        project / "run_stage4_2r3c3t13s1_verify_package.sh",
        project / "run_stop_stage4_2r3c3t13s1_now.sh",
    }
    if not required <= set(paths):
        missing = sorted(str(path.relative_to(project)) for path in required - set(paths))
        raise ValueError(f"T13S1 package inventory missing files: {missing}")
    return paths


def _deployed_package_fingerprint(
    ctx: Stage42R3C3T13S1Context,
) -> dict[str, Any]:
    project = _project_root()
    rows = []
    for path in _package_files(ctx):
        if not path.is_file():
            raise FileNotFoundError(f"package file missing: {path}")
        rows.append(
            {
                "path": path.relative_to(project).as_posix(),
                "size_bytes": int(path.stat().st_size),
                "sha256": _sha256(path),
            }
        )
    rows.sort(key=lambda row: row["path"])
    controller_source = inspect.getsource(SingleStepTransitionProbeController)
    rollout_semantics = {
        "campaign_identity": CAMPAIGN_IDENTITY,
        "controller_revision": CONTROLLER_REVISION,
        "config_digest": _canonical_digest(ctx.cfg),
        "controller_source_sha256": hashlib.sha256(
            controller_source.encode("utf-8")
        ).hexdigest(),
        "underlying_t11_source_sha256": _sha256(
            Path(t11.__file__).resolve()
        ),
        "underlying_t1_source_sha256": _sha256(
            Path(t11.t1.__file__).resolve()
        ),
        "underlying_r3c1_source_sha256": _sha256(
            Path(t11.t1.r3c1.__file__).resolve()
        ),
    }
    return {
        "schema_version": 1,
        "contract": "r42r3c3t13s1_deployed_package_source_v1",
        "n_files": len(rows),
        "digest": _canonical_digest(rows),
        "rollout_semantics": rollout_semantics,
        "rollout_semantics_digest": _canonical_digest(rollout_semantics),
        "files": rows,
    }


def _semantics_preserving_resume_compatibility(
    original: Mapping[str, Any], active: Mapping[str, Any]
) -> None:
    """Conservatively require exact package identity for automatic resume."""

    if dict(original) != dict(active):
        raise ValueError(
            "Stage4.2R3c3T13S1 automatic resume requires the exact deployed "
            "package fingerprint; a separately audited semantics-only hotfix "
            "must explicitly revise this compatibility contract"
        )


def _prepare_dirs(paths: Stage42R3C3T13S1Paths) -> None:
    for path in (
        paths.run_dir,
        paths.control,
        paths.raw,
        paths.variants,
        paths.source_reference,
        paths.analysis,
    ):
        path.mkdir(parents=True, exist_ok=True)


def _selected_pairs(
    ctx: Stage42R3C3T13S1Context,
) -> list[dict[str, Any]]:
    pairs, _ = t11.t1.r3c3._recompute_selected_pairs(
        ctx.base_ctx.base_ctx.source_ctx.base_ctx
    )
    return list(pairs)


def prepare(
    ctx: Stage42R3C3T13S1Context, *, resume: bool
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    _prepare_dirs(ctx.paths)
    selected_pairs = _selected_pairs(ctx)
    specs = build_control_specs(ctx, selected_pairs)
    package_fingerprint = _deployed_package_fingerprint(ctx)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "controller_revision": CONTROLLER_REVISION,
        "underlying_controller_revision": t11.t1.r3c1.CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "source_stage4_2r3c3t11_config": str(ctx.base_config_path),
        "source_stage4_2r3c3t11_config_sha256": _sha256(
            ctx.base_config_path
        ),
        "source_stage4_2r3c3t1_run": str(
            ctx.base_ctx.base_ctx.source_t1_run
        ),
        "source_stage4_2r3c3t1_audit_dir": str(
            ctx.base_ctx.base_ctx.source_t1_audit_dir
        ),
        "source_stage4_2r3c3t1_fingerprint": (
            ctx.base_ctx.base_ctx.source_t1_fingerprint
        ),
        "source_stage4_2r3c3_run": str(
            ctx.base_ctx.base_ctx.source_ctx.source_r3c3_run
        ),
        "source_stage4_2r3c3_bank_dir": str(
            ctx.base_ctx.base_ctx.source_ctx.source_bank_dir
        ),
        "source_stage4_2r3b_run": str(
            ctx.base_ctx.base_ctx.source_ctx.source_r3b_run
        ),
        "source_stage4_2r3c1_run": str(
            ctx.base_ctx.base_ctx.source_ctx.source_r3c1_run
        ),
        "source_stage4_2r3c3t3_controller_bank": str(
            ctx.base_ctx.t3_controller_bank_path
        ),
        "source_stage4_2r3c3t3_controller_bank_sha256": _sha256(
            ctx.base_ctx.t3_controller_bank_path
        ),
        "deployed_package_fingerprint": package_fingerprint,
        "config_digest": _canonical_digest(ctx.cfg),
        "control_spec_digest": _canonical_digest(specs),
        "identification_probe": copy.deepcopy(
            ctx.cfg["identification_probe"]
        ),
        "formal_timing_contract": copy.deepcopy(
            ctx.cfg["formal_timing_contract"]
        ),
        "control_matrix": copy.deepcopy(ctx.cfg["control_matrix"]),
        "development_set_only": True,
        "identification_only": True,
        "independent_hidden_history_confirmation": False,
        "independent_long_hold_validated": False,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "bc_dagger_or_rl_allowed": False,
    }
    if ctx.paths.manifest.is_file():
        if not resume:
            raise FileExistsError(
                "Stage4.2R3c3T13S1 run exists; use resume or a fresh run"
            )
        old = t11.t1.r3c3.read_json(ctx.paths.manifest)
        for key, value in manifest.items():
            if key == "deployed_package_fingerprint":
                continue
            if old.get(key) != value:
                raise ValueError(
                    f"T13S1 resume incompatibility in manifest field {key}"
                )
        _semantics_preserving_resume_compatibility(
            dict(old.get("deployed_package_fingerprint") or {}),
            package_fingerprint,
        )
    else:
        t11.t1.r3c3.atomic_write_json(ctx.paths.manifest, manifest)
    t11.t1.r3c3.atomic_write_json(
        ctx.paths.run_dir / "stage4_2r3c3t13s1_config.resolved.json",
        ctx.cfg,
    )
    t11.t1.r3c3.atomic_write_json(
        ctx.paths.source_reference / "control_specs.json", specs
    )
    t11.t1.r3c3.atomic_write_json(
        ctx.paths.source_reference
        / "source_stage4_2r3c3t1_fingerprint.json",
        ctx.base_ctx.base_ctx.source_t1_fingerprint,
    )
    t11.t1.r3c3.atomic_write_json(
        ctx.paths.source_reference / "deployed_package_fingerprint.json",
        package_fingerprint,
    )
    state = (
        t11.t1.r3c3.read_json(ctx.paths.state)
        if ctx.paths.state.is_file()
        else {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "campaign_identity": CAMPAIGN_IDENTITY,
            "controller_revision": CONTROLLER_REVISION,
            "package_revision": PACKAGE_REVISION,
            "prepared": True,
            "finished": False,
            "primary_pass": False,
            "phase_status": "prepared",
            "stop_reason": "",
        }
    )
    state["updated_utc"] = t11.t1.r3c3.utc_timestamp()
    t11.t1.r3c3.atomic_write_json(ctx.paths.state, state)
    return selected_pairs, specs


def run_offline_probe_audit(
    ctx: Stage42R3C3T13S1Context,
    selected_pairs: Sequence[Mapping[str, Any]],
    *,
    allow_existing_raw: bool = False,
) -> dict[str, Any]:
    specs = build_control_specs(ctx, selected_pairs)
    library, bundle, selector = t11.t1.r1._library_bundle_selector(
        ctx.base_ctx.base_ctx.source_ctx.source_ctx.r1_ctx
    )
    baseline_dir = (
        ctx.base_ctx.base_ctx.source_ctx.source_r3c1_run
        / "stage4_2r3c1_authenticated_visible_manifold_control"
        / "raw"
    )
    grouped: dict[tuple[Any, ...], list[Mapping[str, Any]]] = (
        defaultdict(list)
    )
    schedule_exact_count = 0
    for spec in specs:
        grouped[_context_key(spec)].append(spec)
        schedule = {
            int(step): np.asarray(value, dtype=float)
            for step, value in spec[
                "r3c3_probe_delta_by_task_issue_step"
            ].items()
        }
        baseline = str(spec["r3c3_probe_id"]) == BASELINE_PROBE_ID
        effects = sorted(
            step + int(spec["action_delay_steps"]) + 1
            for step in schedule
        )
        exact = bool(
            (baseline and not schedule)
            or (
                not baseline
                and len(schedule) == 2
                and effects
                == [
                    int(spec["r3c3_probe_first_effect_state"]),
                    int(spec["r3c3_probe_cancel_effect_state"]),
                ]
                and effects[1] == effects[0] + 1
                and np.array_equal(
                    np.sum(np.stack(list(schedule.values())), axis=0),
                    np.zeros(N_MODES),
                )
            )
        )
        schedule_exact_count += exact
    finite_causal_action_count = 0
    hidden_invariant_count = 0
    horizon_exact_count = 0
    conservative_intervention_count = 0
    for index, key in enumerate(sorted(grouped)):
        context_specs = grouped[key]
        baseline_id = str(context_specs[0]["baseline_experiment_id"])
        source = t11.t1.r3c3.read_json_gz(
            baseline_dir / f"{baseline_id}.json.gz"
        )
        source_trajectory = list(source["trajectory"])
        initial = copy.deepcopy(dict(source_trajectory[0]))
        initial["step_index"] = 0
        payload = _control_payload(ctx, spec=context_specs[0])
        plant = t11.t1.r1.LocalPlantReplayWorker(
            payload,
            library,
            bundle,
            f"stage42r3c3t13s1_offline_{index:03d}",
            selector,
        )
        try:
            for spec in context_specs:
                sanitized = _controller_spec(spec)
                controller = SingleStepTransitionProbeController(
                    plant.base_worker, bundle, sanitized, initial
                )
                schedule_steps = sorted(
                    int(step)
                    for step in spec[
                        "r3c3_probe_delta_by_task_issue_step"
                    ]
                )
                last_step = max(schedule_steps, default=0)
                traces = []
                actions = []
                coil_bound_pass = True
                for step in range(last_step + 1):
                    state = copy.deepcopy(dict(source_trajectory[step]))
                    state["step_index"] = step
                    action, trace = controller.action(state)
                    actions.append(np.asarray(action, dtype=float))
                    traces.append(trace)
                    currents = np.asarray(
                        state["currents_a_tsc"], dtype=float
                    )
                    next_currents = (
                        currents
                        + np.asarray(action, dtype=float)
                        * float(plant.base_worker.max_delta_a)
                        * float(spec["slew_scale"])
                    )
                    coil_bound_pass = bool(
                        coil_bound_pass
                        and np.all(
                            next_currents
                            <= np.asarray(plant.base_worker.max_current)
                            + 1e-9
                        )
                        and np.all(
                            next_currents
                            >= np.asarray(plant.base_worker.min_current)
                            - 1e-9
                        )
                    )
                    if step + 1 < len(source_trajectory):
                        next_state = copy.deepcopy(
                            dict(source_trajectory[step + 1])
                        )
                        next_state["step_index"] = step + 1
                        controller.advance(next_state)
                issued = [row for row in traces if row["r3c3_probe_issued"]]
                schedule_pass = bool(
                    len(issued) == len(schedule_steps)
                    and [int(row["task_step"]) for row in issued]
                    == schedule_steps
                    and all(
                        bool(row["r3c3_probe_scheduler_increment_exact"])
                        and not bool(row["mode_action_rescaled"])
                        for row in issued
                    )
                )
                causal_pass = bool(
                    all(np.all(np.isfinite(action)) for action in actions)
                    and all(
                        int(row["measurement_max_state_index_used"])
                        == int(row["task_step"])
                        and not bool(row["future_measurement_used"])
                        and not bool(row["hidden_wire_used"])
                        and not bool(row["source_action_used"])
                        and not bool(row["source_result_used"])
                        and not bool(row["pair_or_history_label_used"])
                        and not bool(
                            row[
                                "future_probe_schedule_available_to_underlying_controller"
                            ]
                        )
                        for row in traces
                    )
                    and schedule_pass
                    and coil_bound_pass
                )
                finite_causal_action_count += causal_pass
                if schedule_steps:
                    conservative_intervention_count += causal_pass
                hidden = copy.deepcopy(initial)
                hidden["wire_currents_a"] = [
                    float(wire + 1) * 1.0e9 for wire in range(N_WIRES)
                ]
                visible_controller = SingleStepTransitionProbeController(
                    plant.base_worker, bundle, sanitized, initial
                )
                hidden_controller = SingleStepTransitionProbeController(
                    plant.base_worker, bundle, sanitized, hidden
                )
                visible_action, _ = visible_controller.action(initial)
                hidden_action, _ = hidden_controller.action(hidden)
                hidden_invariant_count += np.array_equal(
                    visible_action, hidden_action
                )
                horizon_exact_count += bool(
                    int(payload["stage4_1r4_horizon_steps"])
                    == OBSERVATION_HORIZON
                    and int(
                        payload["train_cfg"]["episode"][
                            "max_episode_steps"
                        ]
                    )
                    == OBSERVATION_HORIZON
                    and int(plant.base_worker.env.max_episode_steps)
                    == OBSERVATION_HORIZON
                )
        finally:
            plant.close()
    expected = int(ctx.cfg["control_matrix"]["expected_rollouts"])
    raw_count = len(list(ctx.paths.raw.glob("*.json.gz")))
    raw_gate = (
        0 <= raw_count <= expected if allow_existing_raw else raw_count == 0
    )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "phase": "offline_minimal_transition_probe_audit",
        "expected_probe_specs": expected,
        "probe_spec_count": len(specs),
        "extended_baseline_spec_count": sum(
            str(spec["r3c3_probe_id"]) == BASELINE_PROBE_ID
            for spec in specs
        ),
        "signed_probe_spec_count": sum(
            str(spec["r3c3_probe_id"]) != BASELINE_PROBE_ID
            for spec in specs
        ),
        "probe_schedule_exact_count": schedule_exact_count,
        "finite_causal_action_count": finite_causal_action_count,
        "baseline_context_count": len(grouped),
        "hidden_wire_invariant_action_count": hidden_invariant_count,
        "payload_and_environment_horizon_exact_count": horizon_exact_count,
        "conservative_14_coil_current_and_slew_preflight_count": (
            conservative_intervention_count
        ),
        "raw_count": raw_count,
        "allow_existing_raw": allow_existing_raw,
        "raw_directory_gate_passed": raw_gate,
        "plant_advance_count": 0,
        "real_tsc_executed": False,
    }
    summary["passed"] = bool(
        len(specs) == expected
        and summary["extended_baseline_spec_count"] == 4
        and summary["signed_probe_spec_count"] == 48
        and schedule_exact_count == expected
        and finite_causal_action_count == expected
        and len(grouped) == 4
        and hidden_invariant_count == expected
        and horizon_exact_count == expected
        and conservative_intervention_count == 48
        and raw_gate
    )
    t11.t1.r3c3.atomic_write_json(
        ctx.paths.source_reference / "offline_transition_probe_audit.json",
        summary,
    )
    return summary


def analyze(
    ctx: Stage42R3C3T13S1Context,
    control_summary: Mapping[str, Any],
) -> dict[str, Any]:
    primary_pass = bool(control_summary.get("passed"))
    verdict = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "verdict": (
            "SENTINEL_PASS_OFFLINE_MODEL_ONLY"
            if primary_pass
            else "SENTINEL_FAIL_STOP_IDENTIFICATION"
        ),
        "primary_pass": primary_pass,
        "identification_only": True,
        "formal_tracking_is_acceptance_gate_for_probes": False,
        "observation_horizon_is_long_hold_validation": False,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "development_set_only": True,
        "independent_hidden_history_confirmation": False,
        "bc_dagger_or_rl_allowed": False,
        "next_if_pass": (
            "Build and unit-test one offline state/issue-time local "
            "transition interface and preregister its holdout validation."
        ),
        "next_if_fail": (
            "Preserve all raw, stop identification expansion, and redesign "
            "observer/model/action resolution without weakening gates."
        ),
    }
    t11.t1.r3c3.atomic_write_json(
        ctx.paths.analysis / "stage4_2r3c3t13s1_summary.json",
        dict(control_summary),
    )
    t11.t1.r3c3.atomic_write_json(
        ctx.paths.analysis / "stage4_2r3c3t13s1_verdict.json", verdict
    )
    state = t11.t1.r3c3.read_json(ctx.paths.state)
    state.update(
        {
            "finished": True,
            "primary_pass": primary_pass,
            "phase_status": "campaign_complete",
            "stop_reason": (
                "" if primary_pass else "sentinel_scientific_gate_failed"
            ),
            "verdict": verdict,
            "updated_utc": t11.t1.r3c3.utc_timestamp(),
        }
    )
    t11.t1.r3c3.atomic_write_json(ctx.paths.state, state)
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "control_summary": dict(control_summary),
        "verdict": verdict,
    }


def execute(
    ctx: Stage42R3C3T13S1Context,
    *,
    command: str,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    selected_pairs, specs = prepare(ctx, resume=resume)
    offline = run_offline_probe_audit(
        ctx, selected_pairs, allow_existing_raw=resume
    )
    if not bool(offline.get("passed")):
        raise RuntimeError(
            "Stage4.2R3c3T13S1 offline gate failed; no real TSC started"
        )
    if command == "offline":
        state = t11.t1.r3c3.read_json(ctx.paths.state)
        state.update(
            {
                "finished": False,
                "primary_pass": False,
                "phase_status": "offline_gate_complete",
                "stop_reason": "",
                "offline_probe_audit": dict(offline),
                "updated_utc": t11.t1.r3c3.utc_timestamp(),
            }
        )
        t11.t1.r3c3.atomic_write_json(ctx.paths.state, state)
        return {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "phase": "offline_minimal_transition_probe_audit",
            "offline_probe_audit": dict(offline),
            "real_tsc_executed": False,
            "finished": False,
            "primary_pass": False,
        }
    results = _evaluate_control(
        ctx, specs, backend=backend, resume=resume
    )
    summary = summarize_control(ctx, results, selected_pairs)
    return analyze(ctx, summary)


def self_test() -> dict[str, Any]:
    cfg = t11.t1.r3c3.read_json(
        _project_root()
        / "configs/stage4_2r3c3t13s1_minimal_transition_sentinel_500ms.json"
    )
    _validate_config(cfg)
    rows = []
    for delay in (0, 2):
        for window in WINDOWS:
            for mode in MODES:
                schedule = _signed_schedule(
                    cfg, delay=delay, window=window, mode=mode, sign=1
                )
                effects = [step + delay + 1 for step in sorted(schedule)]
                rows.append(
                    {
                        "delay_steps": delay,
                        "probe_window": window,
                        "probe_mode": mode,
                        "issue_steps": sorted(schedule),
                        "effect_states": effects,
                        "requested_net": np.sum(
                            np.stack(list(schedule.values())), axis=0
                        ).tolist(),
                    }
                )
    passed = bool(
        len(rows) == 12
        and all(
            len(row["issue_steps"]) == 2
            and row["issue_steps"][1] == row["issue_steps"][0] + 1
            and row["effect_states"][1] == row["effect_states"][0] + 1
            and max(abs(value) for value in row["requested_net"]) == 0.0
            for row in rows
        )
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "design_revision": 1,
        "expected_rollouts": 52,
        "schedule_rows": rows,
        "identification_only": True,
        "real_tsc_executed": False,
        "formal_timing_unchanged": True,
        "bc_dagger_or_rl_allowed": False,
        "passed": passed,
    }


def _set_resource_limits() -> None:
    if resource is None:
        return
    try:
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    except Exception:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage4.2R3c3T13S1 minimal transition sentinel"
    )
    parser.add_argument("--config", type=Path)
    parser.add_argument("--source-stage4-2r3b-run", type=Path)
    parser.add_argument("--source-stage4-2r3c3-run", type=Path)
    parser.add_argument("--source-stage4-2r3c3-bank-dir", type=Path)
    parser.add_argument("--source-stage4-2r3c3t1-run", type=Path)
    parser.add_argument("--source-stage4-2r3c3t1-audit-dir", type=Path)
    parser.add_argument(
        "--source-stage4-2r3c3t3-controller-bank", type=Path
    )
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument(
        "--command", choices=("all", "offline"), default="all"
    )
    parser.add_argument(
        "--backend", choices=("serial", "ray"), default="ray"
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    _set_resource_limits()
    if args.self_test:
        print(json.dumps(self_test(), indent=2, sort_keys=True))
        return
    required = (
        ("--config", args.config),
        ("--source-stage4-2r3b-run", args.source_stage4_2r3b_run),
        ("--source-stage4-2r3c3-run", args.source_stage4_2r3c3_run),
        (
            "--source-stage4-2r3c3-bank-dir",
            args.source_stage4_2r3c3_bank_dir,
        ),
        ("--source-stage4-2r3c3t1-run", args.source_stage4_2r3c3t1_run),
        (
            "--source-stage4-2r3c3t1-audit-dir",
            args.source_stage4_2r3c3t1_audit_dir,
        ),
        (
            "--source-stage4-2r3c3t3-controller-bank",
            args.source_stage4_2r3c3t3_controller_bank,
        ),
        ("--run-dir", args.run_dir),
    )
    missing = [name for name, value in required if value is None]
    if missing:
        parser.error("missing required arguments: " + ", ".join(missing))
    ctx = load_stage42r3c3t13s1_config(
        args.config,
        source_stage42r3b_run=args.source_stage4_2r3b_run,
        source_stage42r3c3_run=args.source_stage4_2r3c3_run,
        source_stage42r3c3_bank_dir=args.source_stage4_2r3c3_bank_dir,
        source_stage42r3c3t1_run=args.source_stage4_2r3c3t1_run,
        source_stage42r3c3t1_audit_dir=args.source_stage4_2r3c3t1_audit_dir,
        source_stage42r3c3t3_controller_bank=(
            args.source_stage4_2r3c3t3_controller_bank
        ),
        run_dir_override=args.run_dir,
    )
    result = execute(
        ctx, command=args.command, backend=args.backend, resume=args.resume
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
