#!/usr/bin/env python3
"""Stage4.2R3c3T6 target-residual new-direction identification."""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
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
    stage4_2r3c3t1_long_separation_zero_net_transport_identification as t1,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t2_post_contract_neutralized_held_transport_identification as t2,
)
from tsc_rzip_rllib.utils.ray_runtime import ensure_ray_worker_plan

try:
    import resource
except ImportError:  # pragma: no cover - Windows validation
    resource = None


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T6"
CONTROLLER_REVISION = "target_residual_new_direction_probe_v42r3c3t6_v1"
PACKAGE_REVISION = "r42r3c3t6_target_residual_identification_v1h1"
RUN_NAME = "stage4_2r3c3t6_target_residual_new_direction_identification"
OBSERVATION_HORIZON = 50
BASELINE_PROBE_ID = "target_residual_baseline"
PROBE_IDS = (
    "r17_target_action_residual",
    "matched_visible_target_equal_pc1",
    "matched_visible_target_equal_pc2",
)
N_MODES = t1.N_MODES
N_COILS = t1.N_COILS
N_WIRES = t1.N_WIRES


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_digest(value: Any) -> str:
    return t1._canonical_digest(value)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _formal_horizon(slew: float) -> int:
    return t2._formal_horizon(slew)


@dataclass(frozen=True)
class Stage42R3C3T6Paths:
    run_dir: Path
    control: Path
    raw: Path
    variants: Path
    source_reference: Path
    analysis: Path
    manifest: Path
    state: Path


@dataclass(frozen=True)
class Stage42R3C3T6Context:
    cfg: dict[str, Any]
    base_config_path: Path
    base_ctx: t2.Stage42R3C3T2Context
    preflight_path: Path
    preflight: dict[str, Any]
    t3_controller_bank_path: Path
    paths: Stage42R3C3T6Paths


def _paths(run_dir: Path) -> Stage42R3C3T6Paths:
    root = run_dir.expanduser().resolve()
    control = root / "stage4_2r3c3t6_target_residual_identification"
    return Stage42R3C3T6Paths(
        run_dir=root,
        control=control,
        raw=control / "raw",
        variants=root / "stage4_2r3c3t6_environment_variants",
        source_reference=root / "stage4_2r3c3t6_source_reference",
        analysis=root / "stage4_2r3c3t6_analysis",
        manifest=root / "stage4_2r3c3t6_manifest.json",
        state=root / "stage4_2r3c3t6_state.json",
    )


def _validate_config(cfg: Mapping[str, Any]) -> None:
    if (
        cfg.get("stage") != STAGE
        or int(cfg.get("design_revision", -1)) != 1
        or cfg.get("run_name") != RUN_NAME
        or cfg.get("controller_revision") != CONTROLLER_REVISION
        or cfg.get("package_revision") != PACKAGE_REVISION
    ):
        raise ValueError("Stage4.2R3c3T6 identity changed")
    probe = cfg["identification_probe"]
    matrix = cfg["control_matrix"]
    if (
        int(probe["observation_horizon_steps"]) != OBSERVATION_HORIZON
        or tuple(probe["probe_ids"]) != PROBE_IDS
        or probe["extended_baseline_probe_id"] != BASELINE_PROBE_ID
        or list(map(int, probe["probe_signs"])) != [-1, 1]
        or int(probe["required_issue_count_per_signed_probe"]) != 41
        or list(map(int, probe["cancellation_effect_states"]))
        != [39, 40, 41, 42, 43, 44]
        or float(probe["maximum_formal_schedule_l2"]) != 0.015
        or float(probe["maximum_schedule_component_abs"]) != 0.0075
        or float(probe["maximum_current_utilization"]) != 0.55
        or float(probe["maximum_selected_velocity_condition_number"])
        != 25.0
        or float(probe["maximum_combined_velocity_condition_number"])
        != 25.0
    ):
        raise ValueError("Stage4.2R3c3T6 probe contract changed")
    if (
        int(matrix["expected_rollouts"]) != 224
        or int(matrix["expected_signed_probe_rollouts"]) != 192
        or int(matrix["expected_extended_baseline_rollouts"]) != 32
        or int(matrix["expected_rollouts_per_baseline_context"]) != 7
        or int(matrix["expected_response_groups"]) != 96
        or int(matrix["expected_matched_hidden_history_groups"]) != 48
    ):
        raise ValueError("Stage4.2R3c3T6 task matrix changed")
    contract = cfg["formal_timing_contract"]
    if (
        int(contract["normal"]["arrival_deadline_step"]) != 25
        or int(contract["normal"]["hold_through_step"]) != 35
        or int(contract["weak"]["arrival_deadline_step"]) != 27
        or int(contract["weak"]["hold_through_step"]) != 37
        or float(contract["position_tolerance_m"]) != 0.03
        or float(contract["speed_tolerance_m_per_s"]) != 0.1
        or bool(contract["arrival_deadline_expansion_allowed"])
    ):
        raise ValueError("Stage4.2R3c3T6 formal timing changed")
    if (
        not bool(cfg["development_set_only"])
        or bool(cfg["independent_hidden_history_confirmation"])
        or bool(cfg["independent_long_hold_validated"])
        or bool(cfg["bc_dagger_or_rl_allowed"])
    ):
        raise ValueError("Stage4.2R3c3T6 scope changed")


def _authenticate_preflight(
    cfg: Mapping[str, Any],
) -> tuple[Path, dict[str, Any]]:
    required = cfg["candidate_preflight"]
    path = (_project_root() / str(required["path"])).resolve()
    if not path.is_file() or _sha256(path) != str(required["sha256"]):
        raise ValueError("T6 candidate preflight fingerprint mismatch")
    payload = t1.r3c3.read_json(path)
    if (
        not bool(payload["all_preflight_gates_pass"])
        or bool(payload["real_tsc_executed"])
        or int(payload["candidate_count_per_actuator"]) != 3
        or int(payload["prospective_task_count"]) != 224
        or len(payload["actuator_cases"]) != 2
        or int(
            payload["inputs"]["r17"]["authenticated_file_count"]
        )
        != int(required["required_r17_authenticated_count"])
        or int(payload["inputs"]["r3c1"]["authenticated_raw_count"])
        != int(required["required_r3c1_authenticated_count"])
    ):
        raise ValueError("T6 candidate preflight content mismatch")
    for case in payload["actuator_cases"]:
        if (
            int(case["augmented_schedule_rank"])
            != int(required["required_augmented_schedule_rank"])
            or float(case["augmented_schedule_normalized_condition"])
            > float(
                required[
                    "maximum_augmented_schedule_normalized_condition"
                ]
            )
            or len(case["probe_schedules"]) != 3
        ):
            raise ValueError("T6 preflight actuator gate mismatch")
        for probe in case["probe_schedules"]:
            if (
                probe["probe_id"] not in PROBE_IDS
                or len(probe["positive_schedule_by_task_issue_step"])
                != int(required["required_issue_count_per_signed_probe"])
                or int(probe["first_cancellation_effect_state"])
                != int(required["required_first_cancellation_effect_state"])
                or int(probe["last_cancellation_effect_state"])
                != int(required["required_last_cancellation_effect_state"])
                or max(abs(float(x)) for x in probe["requested_full_net"])
                > 1.0e-12
            ):
                raise ValueError("T6 frozen candidate schedule mismatch")
    return path, payload


def load_stage42r3c3t6_config(
    config_path: Path,
    *,
    source_stage42r3b_run: Path,
    source_stage42r3c3_run: Path,
    source_stage42r3c3_bank_dir: Path,
    source_stage42r3c3t1_run: Path,
    source_stage42r3c3t1_audit_dir: Path,
    source_stage42r3c3t3_controller_bank: Path,
    run_dir_override: Path,
) -> Stage42R3C3T6Context:
    config_path = config_path.expanduser().resolve()
    cfg = t1.r3c3.read_json(config_path)
    _validate_config(cfg)
    base_path = (
        _project_root() / str(cfg["base_stage_config"])
    ).resolve()
    if (
        not base_path.is_file()
        or _sha256(base_path) != str(cfg["base_stage_config_sha256"])
    ):
        raise ValueError("T6 frozen T2 base config mismatch")
    base_ctx = t2.load_stage42r3c3t2_config(
        base_path,
        source_stage42r3b_run=source_stage42r3b_run,
        source_stage42r3c3_run=source_stage42r3c3_run,
        source_stage42r3c3_bank_dir=source_stage42r3c3_bank_dir,
        source_stage42r3c3t1_run=source_stage42r3c3t1_run,
        source_stage42r3c3t1_audit_dir=source_stage42r3c3t1_audit_dir,
        run_dir_override=run_dir_override,
    )
    preflight_path, preflight = _authenticate_preflight(cfg)
    bank = source_stage42r3c3t3_controller_bank.expanduser().resolve()
    expected_bank_sha = str(
        preflight["inputs"]["eight_basis_bank"]["sha256"]
    )
    if not bank.is_file() or _sha256(bank) != expected_bank_sha:
        raise ValueError("T6 source T3 controller bank mismatch")
    return Stage42R3C3T6Context(
        cfg=cfg,
        base_config_path=base_path,
        base_ctx=base_ctx,
        preflight_path=preflight_path,
        preflight=preflight,
        t3_controller_bank_path=bank,
        paths=_paths(run_dir_override),
    )


def _context_key(spec: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        str(spec["pair_id"]),
        str(spec["history_member"]),
        str(spec["target_id"]),
        int(spec["action_delay_steps"]),
        float(spec["slew_scale"]),
    )


def _preflight_case(
    ctx: Stage42R3C3T6Context, *, delay: int, slew: float
) -> Mapping[str, Any]:
    matches = [
        case
        for case in ctx.preflight["actuator_cases"]
        if int(case["delay_steps"]) == delay
        and math.isclose(
            float(case["slew_scale"]),
            slew,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        )
    ]
    if len(matches) != 1:
        raise ValueError("T6 preflight actuator selection mismatch")
    return matches[0]


def _signed_schedule(
    probe: Mapping[str, Any], *, sign: int
) -> dict[int, np.ndarray]:
    if int(sign) not in {-1, 1}:
        raise ValueError("T6 signed schedule sign changed")
    schedule: dict[int, np.ndarray] = {}
    for issue_step, values in probe[
        "positive_schedule_by_task_issue_step"
    ]:
        issue_step = int(issue_step)
        value = np.asarray(values, dtype=float).reshape(N_MODES) * int(sign)
        if (
            issue_step in schedule
            or issue_step < 0
            or issue_step >= OBSERVATION_HORIZON
        ):
            raise ValueError("T6 issue schedule invalid")
        schedule[issue_step] = value
    if len(schedule) != 41:
        raise ValueError("T6 issue count changed")
    net = np.sum(np.stack(list(schedule.values())), axis=0)
    if not np.allclose(net, np.zeros(N_MODES), rtol=0.0, atol=1e-12):
        raise ValueError("T6 signed schedule is not zero net")
    return schedule


def build_control_specs(
    ctx: Stage42R3C3T6Context,
    selected_pairs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    source_specs = t1.build_control_specs(
        ctx.base_ctx.source_ctx, selected_pairs
    )
    templates: dict[tuple[Any, ...], Mapping[str, Any]] = {}
    for spec in source_specs:
        templates.setdefault(_context_key(spec), spec)
    if len(templates) != 32:
        raise ValueError("T6 source context coverage mismatch")
    specs: list[dict[str, Any]] = []
    for key in sorted(templates):
        template = copy.deepcopy(dict(templates[key]))
        delay = int(template["action_delay_steps"])
        slew = float(template["slew_scale"])
        case = _preflight_case(ctx, delay=delay, slew=slew)
        probes = {
            str(probe["probe_id"]): probe
            for probe in case["probe_schedules"]
        }
        if set(probes) != set(PROBE_IDS):
            raise ValueError("T6 probe ID set changed")
        members: list[tuple[str, int, dict[int, np.ndarray], Mapping[str, Any] | None]] = [
            (BASELINE_PROBE_ID, 0, {}, None)
        ]
        for probe_id in PROBE_IDS:
            for sign in (-1, 1):
                members.append(
                    (
                        probe_id,
                        sign,
                        _signed_schedule(probes[probe_id], sign=sign),
                        probes[probe_id],
                    )
                )
        for probe_id, sign, schedule, frozen in members:
            schedule_json = {
                str(step): value.tolist()
                for step, value in sorted(schedule.items())
            }
            identity = {
                "stage": STAGE,
                "source_context": list(key),
                "probe_id": probe_id,
                "probe_sign": sign,
                "schedule": schedule_json,
                "candidate_preflight_sha256": _sha256(
                    ctx.preflight_path
                ),
                "observation_horizon_steps": OBSERVATION_HORIZON,
                "controller_revision": CONTROLLER_REVISION,
                "source_t1_raw_inventory_digest": (
                    ctx.base_ctx.source_t1_fingerprint[
                        "raw_inventory_digest"
                    ]
                ),
            }
            experiment_id = t1.r3c3._scenario_digest(identity)
            spec = copy.deepcopy(template)
            spec.update(
                {
                    "kind": (
                        "stage4_2r3c3t6_target_residual_new_direction_"
                        "identification"
                    ),
                    "stage": STAGE,
                    "controller_revision": CONTROLLER_REVISION,
                    "underlying_controller_revision": (
                        t1.r3c1.CONTROLLER_REVISION
                    ),
                    "experiment_id": experiment_id,
                    "phase": "target_residual_new_direction_identification",
                    "category": "target_residual_new_direction_identification",
                    "environment_variant": f"stage4_2r3c3t6_{experiment_id}",
                    "horizon_steps": OBSERVATION_HORIZON,
                    "formal_horizon_steps": _formal_horizon(slew),
                    "identification_only": True,
                    "r3c3_probe_id": probe_id,
                    "r3c3_probe_mode": -1 if not schedule else -2,
                    "r3c3_probe_sign": sign,
                    "r3c3_probe_first_effect_state": (
                        -1
                        if frozen is None
                        else int(frozen["first_formal_effect_state"])
                    ),
                    "r3c3_probe_delta_by_task_issue_step": schedule_json,
                    "r3c3_requested_probe_net": (
                        [0.0] * N_MODES
                        if not schedule
                        else np.sum(
                            np.stack(list(schedule.values())), axis=0
                        ).tolist()
                    ),
                    "r3c3_probe_amplitude": (
                        0.0
                        if frozen is None
                        else float(frozen["formal_max_abs_component"])
                    ),
                    "r3c3_probe_expected_issue_count": len(schedule),
                    "r3c3t6_schedule_contract": (
                        "authenticated_target_residual_three_mode_dense_"
                        "formal_then_effect_states_39_to_44_zero_net_v1"
                    ),
                    "candidate_preflight_sha256": _sha256(
                        ctx.preflight_path
                    ),
                    "source_stage4_2r3c3t1_raw_inventory_digest": (
                        ctx.base_ctx.source_t1_fingerprint[
                            "raw_inventory_digest"
                        ]
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
    if (
        len(specs) != expected
        or len({str(spec["experiment_id"]) for spec in specs}) != expected
    ):
        raise ValueError("T6 control identity coverage mismatch")
    return specs


def _controller_spec(spec: Mapping[str, Any]) -> dict[str, Any]:
    return t1._controller_spec(spec)


class TargetResidualNewDirectionProbeController(
    t1.LongSeparationTransportProbeController
):
    """Exact R3c1 controller plus one frozen T6 three-mode schedule."""

    def __init__(
        self,
        base_worker: Any,
        bundle: Mapping[str, Any],
        source_spec: Mapping[str, Any],
        initial_state: Mapping[str, Any],
    ):
        t1.r3c1.AuthenticatedVisibleManifoldPhaseTaskController.__init__(
            self, base_worker, bundle, source_spec, initial_state
        )
        self.probe_schedule = {
            int(step): np.asarray(value, dtype=float).reshape(N_MODES)
            for step, value in (
                source_spec.get("r3c3_probe_delta_by_task_issue_step")
                or {}
            ).items()
        }
        self.probe_id = str(source_spec["r3c3_probe_id"])
        self.probe_mode = int(source_spec["r3c3_probe_mode"])
        self.probe_sign = int(source_spec["r3c3_probe_sign"])
        self.probe_first_effect_state = int(
            source_spec["r3c3_probe_first_effect_state"]
        )
        self.probe_amplitude = float(source_spec["r3c3_probe_amplitude"])
        baseline = self.probe_id == BASELINE_PROBE_ID
        if baseline:
            valid = bool(
                self.probe_mode == -1
                and self.probe_sign == 0
                and self.probe_first_effect_state == -1
                and self.probe_amplitude == 0.0
                and not self.probe_schedule
            )
        else:
            delay = int(source_spec["action_delay_steps"])
            valid = bool(
                self.probe_id in PROBE_IDS
                and self.probe_mode == -2
                and self.probe_sign in {-1, 1}
                and self.probe_first_effect_state == delay + 1
                and len(self.probe_schedule) == 41
                and max(
                    float(np.max(np.abs(value)))
                    for value in self.probe_schedule.values()
                )
                <= 0.0075
            )
        if not valid:
            raise ValueError("Stage4.2R3c3T6 controller contract invalid")
        if self.probe_schedule:
            requested = np.sum(
                np.stack(list(self.probe_schedule.values())), axis=0
            )
            if not np.allclose(
                requested, np.zeros(N_MODES), rtol=0.0, atol=1e-12
            ):
                raise ValueError("Stage4.2R3c3T6 probe is not zero net")

    def action(
        self, current_state: Mapping[str, Any]
    ) -> tuple[np.ndarray, dict[str, Any]]:
        action, trace = super().action(current_state)
        trace.pop("r3c3t1_identification_only", None)
        trace.update(
            {
                "r3c3t6_identification_only": True,
                "r3c3t6_observation_horizon_steps": OBSERVATION_HORIZON,
                "r3c3t6_post_contract_neutralization": True,
            }
        )
        return action, trace


def _control_payload(
    ctx: Stage42R3C3T6Context, *, spec: Mapping[str, Any]
) -> dict[str, Any]:
    proxy = SimpleNamespace(
        source_ctx=ctx.base_ctx.source_ctx.source_ctx,
        cfg=ctx.base_ctx.cfg,
        paths=ctx.paths,
    )
    payload = t1.r3c3._control_payload(proxy, spec=spec)
    train_cfg = copy.deepcopy(payload["train_cfg"])
    train_cfg.setdefault("episode", {})[
        "max_episode_steps"
    ] = OBSERVATION_HORIZON
    experiment_id = str(spec["experiment_id"])
    t1.r3c3.atomic_write_json(
        ctx.paths.variants / f"train_{experiment_id}.json", train_cfg
    )
    payload["train_cfg"] = train_cfg
    payload["stage4_1r4_horizon_steps"] = OBSERVATION_HORIZON
    payload["variant_id"] = f"stage4_2r3c3t6_{experiment_id}"
    payload["stage4_2r3c3t6_restart_snapshot_dir"] = str(
        spec["restart_snapshot_dir"]
    )
    payload["stage4_2r3c3t6_snapshot_manifest_digest"] = str(
        spec["restart_snapshot_manifest_digest"]
    )
    t1.r3c3.atomic_write_json(
        ctx.paths.variants / f"payload_{experiment_id}.json", payload
    )
    return payload


class LocalTargetResidualProbeWorker:
    def __init__(
        self,
        payload: dict[str, Any],
        library: dict[str, Any],
        bundle: dict[str, Any],
        worker_id: str,
        selector_cfg: dict[str, Any],
    ):
        self.plant = t1.r1.LocalPlantReplayWorker(
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
            "controller_revision": CONTROLLER_REVISION,
            "underlying_controller_revision": t1.r3c1.CONTROLLER_REVISION,
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
                raise ValueError("T6 observation/formal horizon changed")
            self.base.env.reset()
            zero_action = np.zeros(N_COILS, dtype=np.float32)
            initial = t1.r1._state_record_full(
                self.base.env, 0, zero_action
            )
            trajectory = [initial]
            controller = TargetResidualNewDirectionProbeController(
                self.base, self.bundle, _controller_spec(spec), initial
            )
            trace = []
            for step in range(horizon):
                action, controller_row = controller.action(trajectory[-1])
                _, _, terminated, truncated, info = self.base.env.step(action)
                next_state = t1.r1._state_record_full(
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
                        "environment truncated before T6 horizon"
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
            expected_count = 0 if baseline else 41
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
            if baseline:
                requested = applied = np.empty((0, N_MODES))
            else:
                requested = np.asarray(
                    [
                        issued[step]["r3c3_probe_requested_delta"]
                        for step in sorted(issued)
                    ],
                    dtype=float,
                )
                applied = np.asarray(
                    [
                        issued[step]["r3c3_probe_applied_desired_delta"]
                        for step in sorted(issued)
                    ],
                    dtype=float,
                )
            shape = (expected_count, N_MODES)
            applied_exact = bool(
                requested.shape == applied.shape == shape
                and np.allclose(
                    requested, applied, rtol=0.0, atol=1e-12
                )
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
                np.allclose(
                    requested_net, np.zeros(N_MODES), rtol=0.0, atol=1e-12
                )
                and np.allclose(
                    applied_net, np.zeros(N_MODES), rtol=0.0, atol=1e-12
                )
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
                )
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
            )
            result.update(
                {
                    "success": success,
                    "completed": True,
                    "failure_reason": (
                        "" if success else "incomplete or invalid T6 rollout"
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
                            "authenticated_visible_manifold_phase_aligned_"
                            "nominal_prime"
                        ),
                        "reference_phase_start": controller.reference_phase_start,
                        "baseline_controller_revision": (
                            t1.r3c1.CONTROLLER_REVISION
                        ),
                        "identification_only": True,
                        "extended_baseline": baseline,
                        "probe_id": controller.probe_id,
                        "probe_sign": controller.probe_sign,
                        "probe_first_effect_state": (
                            controller.probe_first_effect_state
                        ),
                        "probe_issue_steps": sorted(schedule),
                        "scheduled_probe_exact": schedule_exact,
                        "applied_probe_exact": applied_exact,
                        "requested_probe_net": requested_net.tolist(),
                        "applied_probe_net": applied_net.tolist(),
                        "requested_and_applied_zero_net": zero_net,
                        "observation_horizon_steps": horizon,
                        "formal_horizon_steps": int(
                            spec["formal_horizon_steps"]
                        ),
                        "first_cancellation_effect_state": (
                            39 if not baseline else None
                        ),
                        "probe_trajectory_allowed_in_expert_dataset": False,
                        "phase_selection": copy.deepcopy(
                            controller.phase_selection
                        ),
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
            return t1._json_safe(result)
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
            return t1._json_safe(result)
        finally:
            runner = getattr(self.base.env, "runner", None)
            if runner is not None:
                runner.cleanup_episode_workspace(
                    failed=failed,
                    reason="stage4_2r3c3t6_target_residual_identification",
                )


_CONTROL_RAY_ACTOR = None


def _control_ray_actor_class():
    global _CONTROL_RAY_ACTOR
    if _CONTROL_RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class Stage42R3C3T6ControlActor:
            def __init__(
                self, payload, library, bundle, worker_id, selector_cfg
            ):
                self.worker = LocalTargetResidualProbeWorker(
                    payload, library, bundle, worker_id, selector_cfg
                )

            def evaluate(self, spec):
                return self.worker.evaluate(spec)

            def close(self):
                self.worker.close()
                return True

        _CONTROL_RAY_ACTOR = Stage42R3C3T6ControlActor
    return _CONTROL_RAY_ACTOR


def _result_complete(
    path: Path, expected_spec: Mapping[str, Any]
) -> bool:
    if not path.is_file():
        return False
    try:
        result = t1.r3c3.read_json_gz(path)
        return bool(
            result.get("completed")
            and result.get("stage") == STAGE
            and result.get("controller_revision") == CONTROLLER_REVISION
            and result.get("experiment_id")
            == expected_spec["experiment_id"]
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
    ctx: Stage42R3C3T6Context,
    specs: Sequence[dict[str, Any]],
    *,
    backend: str,
    resume: bool,
) -> list[dict[str, Any]]:
    ctx.paths.raw.mkdir(parents=True, exist_ok=True)
    library, bundle, selector = t1.r1._library_bundle_selector(
        ctx.base_ctx.source_ctx.source_ctx.r1_ctx
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
            worker = LocalTargetResidualProbeWorker(
                payloads[str(spec["experiment_id"])],
                library,
                bundle,
                f"stage42r3c3t6_serial_{index:03d}",
                selector,
            )
            try:
                result = worker.evaluate(spec)
            finally:
                worker.close()
            t1.r3c3.atomic_write_json_gz(
                ctx.paths.raw / f"{spec['experiment_id']}.json.gz",
                result,
            )
            print(f"[Stage4.2R3c3T6] {index + 1}/{len(pending)}", flush=True)
    elif backend == "ray" and pending:
        import ray

        plan = ensure_ray_worker_plan(
            ray,
            requested_workers=int(ctx.cfg["parallel"]["n_workers"]),
            pending_tasks=len(pending),
            ray_tmpdir=(
                os.environ.get("RAY_TMPDIR")
                or ctx.cfg["parallel"].get("ray_tmpdir")
            ),
            log_prefix="[Stage4.2R3c3T6]",
        )
        Actor = _control_ray_actor_class()
        completed = 0
        print(
            "[Stage4.2R3c3T6] "
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
                    f"stage42r3c3t6_{index:03d}",
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
                            f"[Stage4.2R3c3T6] waiting "
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
                        t1.r3c3.atomic_write_json_gz(
                            ctx.paths.raw
                            / f"{spec['experiment_id']}.json.gz",
                            result,
                        )
                        completed += 1
                        if completed % 8 == 0 or not refs:
                            print(
                                f"[Stage4.2R3c3T6] "
                                f"{completed}/{len(pending)}",
                                flush=True,
                            )
            finally:
                t1.r3b.s2._close_ray_actors(
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
        t1.r3c3.read_json_gz(
            ctx.paths.raw / f"{spec['experiment_id']}.json.gz"
        )
        for spec in specs
    ]


def _formal_prefix_result(
    result: Mapping[str, Any],
) -> dict[str, Any]:
    horizon = int(result["spec"]["formal_horizon_steps"])
    truncated = copy.deepcopy(dict(result))
    truncated["trajectory"] = list(result["trajectory"])[: horizon + 1]
    truncated["controller_trace"] = list(
        result["controller_trace"]
    )[:horizon]
    truncated["spec"] = copy.deepcopy(dict(result["spec"]))
    truncated["spec"]["horizon_steps"] = horizon
    return truncated


def _phase_trace_valid(result: Mapping[str, Any]) -> dict[str, Any]:
    base = t1.r3c1._phase_trace_valid(result)
    trace = list(result.get("controller_trace") or [])
    spec = dict(result.get("spec") or {})
    schedule = {
        int(step): np.asarray(value, dtype=float).reshape(N_MODES)
        for step, value in (
            spec.get("r3c3_probe_delta_by_task_issue_step") or {}
        ).items()
    }
    baseline = str(spec.get("r3c3_probe_id")) == BASELINE_PROBE_ID
    expected_count = 0 if baseline else 41
    requested_rows = []
    applied_rows = []
    exact = bool(
        len(trace) == OBSERVATION_HORIZON
        and len(schedule) == expected_count
    )
    solver_failures = 0
    forbidden_count = 0
    issued_count = 0
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
            and bool(row.get("r3c3t6_identification_only"))
        )
        if issued:
            issued_count += 1
            requested_rows.append(requested)
            applied_rows.append(applied)
        solver_failures += not bool(row.get("solver_success"))
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
            )
        )
    requested_array = np.asarray(requested_rows, dtype=float).reshape(
        expected_count, N_MODES
    )
    applied_array = np.asarray(applied_rows, dtype=float).reshape(
        expected_count, N_MODES
    )
    applied_exact = bool(
        np.allclose(
            requested_array, applied_array, rtol=0.0, atol=1e-12
        )
    )
    requested_net = np.sum(requested_array, axis=0)
    applied_net = np.sum(applied_array, axis=0)
    zero_net = bool(
        np.allclose(
            requested_net, np.zeros(N_MODES), rtol=0.0, atol=1e-12
        )
        and np.allclose(
            applied_net, np.zeros(N_MODES), rtol=0.0, atol=1e-12
        )
    )
    passed = bool(
        base["passed"]
        and exact
        and issued_count == expected_count
        and applied_exact
        and zero_net
        and forbidden_count == 0
        and solver_failures == 0
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
        "extended_baseline": baseline,
    }


def _source_prefix_exact(
    ctx: Stage42R3C3T6Context, result: Mapping[str, Any]
) -> bool:
    return t2._source_prefix_exact(ctx.base_ctx, result)


def _formal_prefix_metrics(
    ctx: Stage42R3C3T6Context, result: Mapping[str, Any]
) -> dict[str, Any]:
    return t2._formal_prefix_metrics(ctx.base_ctx, result)


def _full_current_utilization(
    ctx: Stage42R3C3T6Context, result: Mapping[str, Any]
) -> float:
    return t2._full_current_utilization(ctx.base_ctx, result)


def _arrays(
    result: Mapping[str, Any], dt_s: float
) -> tuple[np.ndarray, np.ndarray]:
    return t2._arrays(result, dt_s)


def _rmse(array: np.ndarray) -> float:
    return t2._rmse(array)


def _initial_arrays(
    result: Mapping[str, Any],
) -> tuple[np.ndarray, np.ndarray]:
    return t2._initial_arrays(result)


def _t3_sample_key(sample: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        float(sample["initial_R_m"]),
        float(sample["initial_Z_m"]),
        float(sample["initial_Ip_A"]),
        tuple(float(x) for x in sample["initial_coil_currents_A"]),
        float(sample["target_R_offset_m"]),
        float(sample["target_Z_offset_m"]),
        float(sample["target_Ip_offset_A"]),
        int(sample["actuator_delay_steps"]),
        float(sample["actuator_slew_scale"]),
    )


def _result_sample_key(result: Mapping[str, Any]) -> tuple[Any, ...]:
    initial = result["trajectory"][0]
    spec = result["spec"]
    return (
        float(initial["R"]),
        float(initial["Z"]),
        float(initial["Ip"]),
        tuple(float(x) for x in initial["currents_a_display"]),
        float(spec["target_R_offset_m"]),
        float(spec["target_Z_offset_m"]),
        float(spec["target_Ip_offset_A"]),
        int(spec["action_delay_steps"]),
        float(spec["slew_scale"]),
    )


def _condition_row(
    arrays: Sequence[np.ndarray],
    *,
    expected_rank: int,
    maximum: float,
) -> tuple[int | None, float | None, bool]:
    if len(arrays) != expected_rank or len({a.shape for a in arrays}) != 1:
        return None, None, False
    matrix = np.stack(
        [array[3:, :2].reshape(-1) for array in arrays], axis=1
    )
    rank = int(np.linalg.matrix_rank(matrix))
    condition = float(np.linalg.cond(matrix))
    return (
        rank,
        condition,
        bool(
            rank == expected_rank
            and math.isfinite(condition)
            and condition <= maximum
        ),
    )


def summarize_control(
    ctx: Stage42R3C3T6Context,
    results: Sequence[Mapping[str, Any]],
    selected_pairs: Sequence[Mapping[str, Any]],
    *,
    write_outputs: bool = True,
) -> dict[str, Any]:
    expected = int(ctx.cfg["control_matrix"]["expected_rollouts"])
    probe_cfg = ctx.cfg["identification_probe"]
    central_cfg = probe_cfg["central_symmetry"]
    history_cfg = probe_cfg["matched_hidden_history"]
    dt_ms = int(
        t1.r1._r13_ctx(ctx.base_ctx.source_ctx.source_ctx.r1_ctx)
        .r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34.env_cfg[
            "dt_ms"
        ]
    )
    dt_s = dt_ms / 1000.0
    state_map = t1.r3b._selected_state_map(selected_pairs)
    base_source_ctx = ctx.base_ctx.source_ctx.source_ctx
    rows = []
    by_context: dict[tuple[Any, ...], dict[str, Mapping[str, Any]]] = (
        defaultdict(dict)
    )
    for result in results:
        spec = result["spec"]
        name = (
            BASELINE_PROBE_ID
            if spec["r3c3_probe_id"] == BASELINE_PROBE_ID
            else f"{spec['r3c3_probe_id']}:{spec['r3c3_probe_sign']}"
        )
        by_context[_context_key(spec)][name] = result
        state_id = str(spec["state_generation_experiment_id"])
        base = t1.r3b._control_row(
            base_source_ctx,
            _formal_prefix_result(result),
            state_map[state_id],
        )
        phase = _phase_trace_valid(result)
        formal = (
            _formal_prefix_metrics(ctx, result)
            if bool(result.get("success"))
            else {}
        )
        baseline = str(spec["r3c3_probe_id"]) == BASELINE_PROBE_ID
        prefix_exact = bool(
            baseline
            and result.get("success")
            and _source_prefix_exact(ctx, result)
        )
        execution_pass = bool(
            result.get("success")
            and base["fresh_controller"]
            and base["fresh_tsc_process"]
            and base["initial_restart_exact"]
            and base["controller_trace_causal"]
            and phase["passed"]
            and (not baseline or prefix_exact)
        )
        if not bool(result.get("success")):
            failure_class = "runtime_or_environment_error"
        elif not bool(base["initial_restart_exact"]):
            failure_class = "plant_restart_fidelity_failure"
        elif not bool(base["controller_trace_causal"]):
            failure_class = "controller_causality_failure"
        elif not bool(phase["passed"]):
            failure_class = "identification_probe_execution_failure"
        elif baseline and not prefix_exact:
            failure_class = "extended_baseline_prefix_mismatch"
        else:
            failure_class = ""
        rows.append(
            {
                **base,
                "probe_id": str(spec["r3c3_probe_id"]),
                "probe_sign": int(spec["r3c3_probe_sign"]),
                "extended_baseline": baseline,
                "extended_baseline_prefix_exact": prefix_exact,
                "formal_horizon_steps": int(spec["formal_horizon_steps"]),
                "observation_horizon_steps": int(spec["horizon_steps"]),
                "phase_trace_valid": bool(phase["passed"]),
                "probe_trace_exact": bool(phase["probe_trace_exact"]),
                "probe_issued_count": int(phase["probe_issued_count"]),
                "probe_applied_exact": bool(phase["probe_applied_exact"]),
                "probe_zero_net": bool(phase["probe_zero_net"]),
                "solver_failure_count": int(phase["solver_failure_count"]),
                "forbidden_trace_count": int(
                    phase["forbidden_trace_count"]
                ),
                "max_current_utilization": (
                    _full_current_utilization(ctx, result)
                    if bool(result.get("success"))
                    else None
                ),
                "formal_contract_pass": bool(
                    formal.get("stage3_4_target_tracking_pass", False)
                ),
                "formal_minimum_signed_margin": (
                    float(
                        formal["stage3_4_tracking_minimum_signed_margin"]
                    )
                    if formal
                    else None
                ),
                "execution_pass": execution_pass,
                "failure_class": failure_class,
                "passed": execution_pass,
                "identification_only": True,
                "probe_trajectory_allowed_in_expert_dataset": False,
            }
        )

    baselines = {}
    signed_groups: dict[
        tuple[Any, ...], dict[str, dict[int, Mapping[str, Any]]]
    ] = defaultdict(lambda: defaultdict(dict))
    for key, members in by_context.items():
        if BASELINE_PROBE_ID in members:
            baselines[key] = members[BASELINE_PROBE_ID]
        for name, result in members.items():
            if name != BASELINE_PROBE_ID:
                probe_id, sign = name.rsplit(":", 1)
                signed_groups[key][probe_id][int(sign)] = result
    if len(baselines) != 32:
        raise ValueError("T6 baseline coverage mismatch")

    response_rows = []
    odd_by_key: dict[
        tuple[Any, ...], tuple[np.ndarray, np.ndarray, int]
    ] = {}
    for context_key in sorted(signed_groups):
        baseline = baselines[context_key]
        base_y, base_v = _arrays(baseline, dt_s)
        for probe_id in PROBE_IDS:
            signed = signed_groups[context_key].get(probe_id, {})
            row: dict[str, Any] = {
                "pair_id": context_key[0],
                "history_member": context_key[1],
                "target_id": context_key[2],
                "actual_delay_steps": context_key[3],
                "actual_slew_scale": context_key[4],
                "probe_id": probe_id,
                "signed_member_count": len(signed),
                "response_available": False,
                "baseline_initial_state_exact": False,
                "even_velocity_rmse_m_per_s": None,
                "even_position_rmse_m": None,
                "even_ip_rmse_A": None,
                "central_symmetry_pass": False,
            }
            if (
                set(signed) == {-1, 1}
                and bool(baseline.get("success"))
                and all(bool(item.get("success")) for item in signed.values())
            ):
                plus_y, plus_v = _arrays(signed[1], dt_s)
                minus_y, minus_v = _arrays(signed[-1], dt_s)
                initial = (
                    _initial_arrays(signed[1]),
                    _initial_arrays(signed[-1]),
                    _initial_arrays(baseline),
                )
                initial_exact = bool(
                    np.array_equal(initial[0][0], initial[1][0])
                    and np.array_equal(initial[0][0], initial[2][0])
                    and np.array_equal(initial[0][1], initial[1][1])
                    and np.array_equal(initial[0][1], initial[2][1])
                )
                if (
                    plus_y.shape == minus_y.shape == base_y.shape
                    and plus_v.shape == minus_v.shape == base_v.shape
                ):
                    first = int(
                        signed[1]["spec"][
                            "r3c3_probe_first_effect_state"
                        ]
                    )
                    section = slice(first, OBSERVATION_HORIZON + 1)
                    odd_y = (plus_y - minus_y) / 2.0
                    odd_v = (plus_v - minus_v) / 2.0
                    even_y = (plus_y + minus_y) / 2.0 - base_y
                    even_v = (plus_v + minus_v) / 2.0 - base_v
                    velocity_rmse = _rmse(even_v[section, :2])
                    position_rmse = _rmse(even_y[section, :2])
                    ip_rmse = _rmse(even_y[section, 2])
                    central_pass = bool(
                        initial_exact
                        and velocity_rmse
                        <= float(
                            central_cfg[
                                "maximum_even_velocity_rmse_m_per_s"
                            ]
                        )
                        and position_rmse
                        <= float(
                            central_cfg["maximum_even_position_rmse_m"]
                        )
                        and ip_rmse
                        <= float(central_cfg["maximum_even_ip_rmse_A"])
                    )
                    row.update(
                        {
                            "response_available": True,
                            "baseline_initial_state_exact": initial_exact,
                            "first_effect_state": first,
                            "even_velocity_rmse_m_per_s": velocity_rmse,
                            "even_position_rmse_m": position_rmse,
                            "even_ip_rmse_A": ip_rmse,
                            "central_symmetry_pass": central_pass,
                        }
                    )
                    odd_by_key[(*context_key, probe_id)] = (
                        odd_y,
                        odd_v,
                        first,
                    )
            response_rows.append(row)

    history_groups: dict[
        tuple[Any, ...], dict[str, tuple[np.ndarray, np.ndarray, int]]
    ] = defaultdict(dict)
    for key, response in odd_by_key.items():
        history_groups[(key[0], key[2], key[3], key[4], key[5])][
            key[1]
        ] = response
    history_rows = []
    for key in sorted(history_groups):
        members = history_groups[key]
        row = {
            "pair_id": key[0],
            "target_id": key[1],
            "actual_delay_steps": key[2],
            "actual_slew_scale": key[3],
            "probe_id": key[4],
            "history_member_count": len(members),
            "odd_velocity_rmse_m_per_s": None,
            "odd_position_rmse_m": None,
            "odd_ip_rmse_A": None,
            "matched_hidden_history_pass": False,
        }
        if set(members) == {"plus_first", "minus_first"}:
            plus = members["plus_first"]
            minus = members["minus_first"]
            if plus[0].shape == minus[0].shape:
                first = min(plus[2], minus[2])
                section = slice(first, OBSERVATION_HORIZON + 1)
                velocity_rmse = _rmse(
                    plus[1][section, :2] - minus[1][section, :2]
                )
                position_rmse = _rmse(
                    plus[0][section, :2] - minus[0][section, :2]
                )
                ip_rmse = _rmse(
                    plus[0][section, 2] - minus[0][section, 2]
                )
                matched = bool(
                    velocity_rmse
                    <= float(
                        history_cfg[
                            "maximum_odd_velocity_rmse_m_per_s"
                        ]
                    )
                    and position_rmse
                    <= float(
                        history_cfg["maximum_odd_position_rmse_m"]
                    )
                    and ip_rmse
                    <= float(history_cfg["maximum_odd_ip_rmse_A"])
                )
                row.update(
                    {
                        "odd_velocity_rmse_m_per_s": velocity_rmse,
                        "odd_position_rmse_m": position_rmse,
                        "odd_ip_rmse_A": ip_rmse,
                        "matched_hidden_history_pass": matched,
                    }
                )
        history_rows.append(row)

    new_by_context: dict[tuple[Any, ...], dict[str, np.ndarray]] = (
        defaultdict(dict)
    )
    for key, response in odd_by_key.items():
        new_by_context[key[:5]][key[5]] = response[1]
    selected_condition_rows = []
    selected_max = float(
        probe_cfg["maximum_selected_velocity_condition_number"]
    )
    for key in sorted(new_by_context):
        horizon = _formal_horizon(float(key[4]))
        new = new_by_context[key]
        arrays = [
            new[probe_id][: horizon + 1]
            for probe_id in PROBE_IDS
            if probe_id in new
        ]
        rank, condition, passed = _condition_row(
            arrays, expected_rank=3, maximum=selected_max
        )
        selected_condition_rows.append(
            {
                "pair_id": key[0],
                "history_member": key[1],
                "target_id": key[2],
                "actual_delay_steps": key[3],
                "actual_slew_scale": key[4],
                "controller_use_start_state": 3,
                "controller_use_end_state": horizon,
                "basis_count": 3,
                "velocity_response_matrix_rank": rank,
                "selected_velocity_condition_number": condition,
                "condition_number_pass": passed,
            }
        )

    t3_bank = t1.r3c3.read_json(ctx.t3_controller_bank_path)
    old_by_sample = {
        _t3_sample_key(sample): [
            np.asarray(
                response["delta_velocity_RZ_by_state"], dtype=float
            )
            for response in sorted(
                sample["basis_responses"],
                key=lambda item: int(item["basis_index"]),
            )
        ]
        for sample in t3_bank["samples"]
    }
    combined_rows = []
    combined_max = float(
        probe_cfg["maximum_combined_velocity_condition_number"]
    )
    for key in sorted(new_by_context):
        baseline = baselines[key]
        sample_key = _result_sample_key(baseline)
        old = old_by_sample.get(sample_key, [])
        horizon = _formal_horizon(float(key[4]))
        new = new_by_context[key]
        arrays = [
            *old,
            *[
                new[probe_id][: horizon + 1]
                for probe_id in PROBE_IDS
                if probe_id in new
            ],
        ]
        rank, condition, passed = _condition_row(
            arrays, expected_rank=11, maximum=combined_max
        )
        combined_rows.append(
            {
                "pair_id": key[0],
                "history_member": key[1],
                "target_id": key[2],
                "actual_delay_steps": key[3],
                "actual_slew_scale": key[4],
                "controller_use_start_state": 3,
                "controller_use_end_state": horizon,
                "basis_count": 11,
                "velocity_response_matrix_rank": rank,
                "selected_velocity_condition_number": condition,
                "condition_number_pass": passed,
                "t3_sample_match": len(old) == 8,
            }
        )

    def count(rows_: Sequence[Mapping[str, Any]], field: str) -> int:
        return sum(bool(row[field]) for row in rows_)

    current_values = [
        float(row["max_current_utilization"])
        for row in rows
        if row["max_current_utilization"] is not None
    ]
    maximum_current = max(current_values) if current_values else None
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "target_residual_new_direction_identification",
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
        "expected_extended_baseline_count": 32,
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
            row["failure_class"]
            == "identification_probe_execution_failure"
            for row in rows
        ),
        "extended_baseline_prefix_mismatch_count": sum(
            row["failure_class"] == "extended_baseline_prefix_mismatch"
            for row in rows
        ),
        "forbidden_controller_input_count": sum(
            int(row["forbidden_trace_count"]) for row in rows
        ),
        "solver_failure_count": sum(
            int(row["solver_failure_count"]) for row in rows
        ),
        "formal_contract_pass_count": count(rows, "formal_contract_pass"),
        "formal_contract_failure_count": len(rows)
        - count(rows, "formal_contract_pass"),
        "formal_tracking_is_acceptance_gate": False,
        "response_group_count": len(response_rows),
        "expected_response_group_count": 96,
        "central_symmetry_pass_count": count(
            response_rows, "central_symmetry_pass"
        ),
        "matched_hidden_history_group_count": len(history_rows),
        "expected_matched_hidden_history_group_count": 48,
        "matched_hidden_history_pass_count": count(
            history_rows, "matched_hidden_history_pass"
        ),
        "condition_number_group_count": len(selected_condition_rows),
        "expected_condition_number_group_count": 32,
        "condition_number_pass_count": count(
            selected_condition_rows, "condition_number_pass"
        ),
        "maximum_selected_velocity_condition_number": max(
            (
                float(row["selected_velocity_condition_number"])
                for row in selected_condition_rows
                if row["selected_velocity_condition_number"] is not None
            ),
            default=None,
        ),
        "combined_condition_group_count": len(combined_rows),
        "expected_combined_condition_group_count": 32,
        "combined_condition_pass_count": count(
            combined_rows, "condition_number_pass"
        ),
        "maximum_combined_velocity_condition_number": max(
            (
                float(row["selected_velocity_condition_number"])
                for row in combined_rows
                if row["selected_velocity_condition_number"] is not None
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
        and summary["extended_baseline_prefix_exact_count"] == 32
        and summary["forbidden_controller_input_count"] == 0
        and summary["solver_failure_count"] == 0
    )
    summary["central_symmetry_gate_passed"] = bool(
        len(response_rows) == summary["central_symmetry_pass_count"] == 96
    )
    summary["matched_hidden_history_gate_passed"] = bool(
        len(history_rows)
        == summary["matched_hidden_history_pass_count"]
        == 48
    )
    summary["condition_number_gate_passed"] = bool(
        len(selected_condition_rows)
        == summary["condition_number_pass_count"]
        == 32
    )
    summary["combined_condition_number_gate_passed"] = bool(
        len(combined_rows) == summary["combined_condition_pass_count"] == 32
    )
    summary["current_utilization_pass"] = bool(
        maximum_current is not None
        and maximum_current
        <= float(probe_cfg["maximum_current_utilization"])
    )
    summary["passed"] = bool(
        summary["execution_gate_passed"]
        and summary["central_symmetry_gate_passed"]
        and summary["matched_hidden_history_gate_passed"]
        and summary["condition_number_gate_passed"]
        and summary["combined_condition_number_gate_passed"]
        and summary["current_utilization_pass"]
    )
    if write_outputs:
        outputs = (
            ("results", rows),
            ("central_response_results", response_rows),
            ("matched_hidden_history_results", history_rows),
            ("condition_number_results", selected_condition_rows),
            ("combined_condition_number_results", combined_rows),
        )
        ctx.paths.control.mkdir(parents=True, exist_ok=True)
        for name, values in outputs:
            t1.r3c3.atomic_write_json(
                ctx.paths.control / f"{name}.json", values
            )
            t1.r3c3.write_csv(
                ctx.paths.control / f"{name}.csv", values
            )
        t1.r3c3.atomic_write_json(
            ctx.paths.control / "summary.json", summary
        )
    return summary


def _package_files(ctx: Stage42R3C3T6Context) -> list[Path]:
    project = _project_root()
    names = [
        "AGENTS.md",
        "PACKAGE_MANIFEST.json",
        "SHA256SUMS",
        str(ctx.cfg["base_stage_config"]),
        (
            "configs/stage4_2r3c3t6_target_residual_new_direction_"
            "identification_500ms.json"
        ),
        str(ctx.cfg["candidate_preflight"]["path"]),
        (
            "tsc_rzip_rllib/diagnostics/stage4_2r3c3t6_target_"
            "residual_new_direction_identification.py"
        ),
        (
            "scripts/stage4_2r3c3t6_target_residual_new_direction_"
            "identification.py"
        ),
        "scripts/stage4_2r3c3t6_server_postprocess.py",
        "scripts/stage4_2r3c3t6_shell_common.sh",
        "run_stage4_2r3c3t6_common.sh",
        "run_stage4_2r3c3t6_offline.sh",
        "run_stage4_2r3c3t6_server_postprocess.sh",
        (
            "run_stage4_2r3c3t6_target_residual_new_direction_"
            "identification_native.sh"
        ),
        (
            "run_stage4_2r3c3t6_target_residual_new_direction_"
            "identification_nohup.sh"
        ),
        "run_stage4_2r3c3t6_self_test.sh",
        "run_stage4_2r3c3t6_verify_package.sh",
        "run_stop_stage4_2r3c3t6_now.sh",
    ]
    paths = [project / name for name in names]
    manifest = t1.r3c3.read_json(project / "PACKAGE_MANIFEST.json")
    for relative in manifest["file_inventory"]:
        path = project / str(relative)
        if path not in paths:
            paths.append(path)
    return paths


def _deployed_package_fingerprint(
    ctx: Stage42R3C3T6Context,
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
    return {
        "schema_version": 1,
        "contract": "r42r3c3t6_deployed_package_source_v1",
        "n_files": len(rows),
        "digest": _canonical_digest(rows),
        "files": rows,
    }


def _prepare_dirs(paths: Stage42R3C3T6Paths) -> None:
    for path in (
        paths.run_dir,
        paths.control,
        paths.raw,
        paths.variants,
        paths.source_reference,
        paths.analysis,
    ):
        path.mkdir(parents=True, exist_ok=True)


def prepare(
    ctx: Stage42R3C3T6Context, *, resume: bool
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    _prepare_dirs(ctx.paths)
    selected_pairs, _ = t1.r3c3._recompute_selected_pairs(
        ctx.base_ctx.source_ctx.base_ctx
    )
    specs = build_control_specs(ctx, selected_pairs)
    package_fingerprint = _deployed_package_fingerprint(ctx)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "source_stage4_2r3c3t1_run": str(ctx.base_ctx.source_t1_run),
        "source_stage4_2r3c3t1_audit_dir": str(
            ctx.base_ctx.source_t1_audit_dir
        ),
        "source_stage4_2r3c3t1_fingerprint": (
            ctx.base_ctx.source_t1_fingerprint
        ),
        "source_stage4_2r3c3_run": str(
            ctx.base_ctx.source_ctx.source_r3c3_run
        ),
        "source_stage4_2r3c3_bank_dir": str(
            ctx.base_ctx.source_ctx.source_bank_dir
        ),
        "source_stage4_2r3b_run": str(
            ctx.base_ctx.source_ctx.source_r3b_run
        ),
        "source_stage4_2r3c1_run": str(
            ctx.base_ctx.source_ctx.source_r3c1_run
        ),
        "source_stage4_2r3c3t3_controller_bank": str(
            ctx.t3_controller_bank_path
        ),
        "source_stage4_2r3c3t3_controller_bank_sha256": _sha256(
            ctx.t3_controller_bank_path
        ),
        "candidate_preflight_path": str(ctx.preflight_path),
        "candidate_preflight_sha256": _sha256(ctx.preflight_path),
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
        "independent_hidden_history_confirmation": False,
        "independent_long_hold_validated": False,
    }
    if ctx.paths.manifest.is_file():
        if not resume:
            raise FileExistsError(
                "Stage4.2R3c3T6 run exists; use resume or a fresh run"
            )
        old = t1.r3c3.read_json(ctx.paths.manifest)
        for key, value in manifest.items():
            if old.get(key) != value:
                raise ValueError(
                    f"T6 resume incompatibility in manifest field {key}"
                )
    else:
        t1.r3c3.atomic_write_json(ctx.paths.manifest, manifest)
    t1.r3c3.atomic_write_json(
        ctx.paths.run_dir / "stage4_2r3c3t6_config.resolved.json", ctx.cfg
    )
    t1.r3c3.atomic_write_json(
        ctx.paths.source_reference / "control_specs.json", specs
    )
    t1.r3c3.atomic_write_json(
        ctx.paths.source_reference
        / "source_stage4_2r3c3t1_fingerprint.json",
        ctx.base_ctx.source_t1_fingerprint,
    )
    t1.r3c3.atomic_write_json(
        ctx.paths.source_reference / "candidate_preflight.json",
        ctx.preflight,
    )
    t1.r3c3.atomic_write_json(
        ctx.paths.source_reference / "deployed_package_fingerprint.json",
        package_fingerprint,
    )
    state = (
        t1.r3c3.read_json(ctx.paths.state)
        if ctx.paths.state.is_file()
        else {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "controller_revision": CONTROLLER_REVISION,
            "package_revision": PACKAGE_REVISION,
            "prepared": True,
            "finished": False,
            "primary_pass": False,
            "phase_status": "prepared",
            "stop_reason": "",
        }
    )
    state["updated_utc"] = t1.r3c3.utc_timestamp()
    t1.r3c3.atomic_write_json(ctx.paths.state, state)
    return list(selected_pairs), specs


def run_offline_probe_audit(
    ctx: Stage42R3C3T6Context,
    selected_pairs: Sequence[Mapping[str, Any]],
    *,
    allow_existing_raw: bool = False,
) -> dict[str, Any]:
    specs = build_control_specs(ctx, selected_pairs)
    library, bundle, selector = t1.r1._library_bundle_selector(
        ctx.base_ctx.source_ctx.source_ctx.r1_ctx
    )
    baseline_dir = (
        ctx.base_ctx.source_ctx.source_r3c1_run
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
        delay = int(spec["action_delay_steps"])
        effects = sorted(step + delay + 1 for step in schedule)
        exact = bool(
            (baseline and not schedule)
            or (
                not baseline
                and len(schedule) == 41
                and effects[:35]
                == list(range(delay + 1, _formal_horizon(float(spec["slew_scale"])) + 1))
                and effects[35:] == [39, 40, 41, 42, 43, 44]
                and np.allclose(
                    np.sum(np.stack(list(schedule.values())), axis=0),
                    np.zeros(N_MODES),
                    rtol=0.0,
                    atol=1e-12,
                )
            )
        )
        schedule_exact_count += exact
    action_count = 0
    hidden_invariant_count = 0
    horizon_exact_count = 0
    for index, key in enumerate(sorted(grouped)):
        context_specs = grouped[key]
        baseline_id = str(context_specs[0]["baseline_experiment_id"])
        source = t1.r3c3.read_json_gz(
            baseline_dir / f"{baseline_id}.json.gz"
        )
        initial = copy.deepcopy(dict(source["trajectory"][0]))
        initial["step_index"] = 0
        payload = _control_payload(ctx, spec=context_specs[0])
        plant = t1.r1.LocalPlantReplayWorker(
            payload,
            library,
            bundle,
            f"stage42r3c3t6_offline_{index:03d}",
            selector,
        )
        try:
            for spec in context_specs:
                sanitized = _controller_spec(spec)
                controller = TargetResidualNewDirectionProbeController(
                    plant.base_worker, bundle, sanitized, initial
                )
                action, trace = controller.action(initial)
                hidden = copy.deepcopy(initial)
                hidden["wire_currents_a"] = [
                    float(wire + 1) * 1.0e9 for wire in range(N_WIRES)
                ]
                hidden_controller = TargetResidualNewDirectionProbeController(
                    plant.base_worker, bundle, sanitized, hidden
                )
                hidden_action, hidden_trace = hidden_controller.action(hidden)
                baseline = (
                    str(spec["r3c3_probe_id"]) == BASELINE_PROBE_ID
                )
                passed = bool(
                    np.all(np.isfinite(action))
                    and np.array_equal(action, hidden_action)
                    and bool(trace["r3c3_probe_issued"]) == (not baseline)
                    and bool(hidden_trace["r3c3_probe_issued"])
                    == (not baseline)
                    and int(trace["measurement_max_state_index_used"]) == 0
                    and not bool(trace["future_measurement_used"])
                    and not bool(trace["hidden_wire_used"])
                    and not bool(trace["source_action_used"])
                    and not bool(trace["source_result_used"])
                    and not bool(trace["pair_or_history_label_used"])
                )
                action_count += passed
                hidden_invariant_count += np.array_equal(
                    action, hidden_action
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
        "phase": "offline_target_residual_probe_audit",
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
        "finite_causal_action_count": action_count,
        "baseline_context_count": len(grouped),
        "hidden_wire_invariant_action_count": hidden_invariant_count,
        "payload_and_environment_horizon_exact_count": horizon_exact_count,
        "raw_count": raw_count,
        "allow_existing_raw": allow_existing_raw,
        "raw_directory_gate_passed": raw_gate,
        "plant_advance_count": 0,
        "real_tsc_executed": False,
    }
    summary["passed"] = bool(
        len(specs) == expected
        and summary["extended_baseline_spec_count"] == 32
        and summary["signed_probe_spec_count"] == 192
        and schedule_exact_count == expected
        and action_count == expected
        and len(grouped) == 32
        and hidden_invariant_count == expected
        and horizon_exact_count == expected
        and raw_gate
    )
    t1.r3c3.atomic_write_json(
        ctx.paths.source_reference / "offline_target_residual_audit.json",
        summary,
    )
    return summary


def analyze(
    ctx: Stage42R3C3T6Context,
    control_summary: Mapping[str, Any],
) -> dict[str, Any]:
    primary_pass = bool(control_summary.get("passed"))
    verdict = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "verdict": (
            "STAGE4_2R3C3T6_NEW_DIRECTION_IDENTIFICATION_PASS"
            if primary_pass
            else "STAGE4_2R3C3T6_NEW_DIRECTION_IDENTIFICATION_FAIL"
        ),
        "primary_pass": primary_pass,
        "identification_only": True,
        "formal_tracking_is_acceptance_gate": False,
        "observation_horizon_is_long_hold_validation": False,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "development_set_only": True,
        "independent_hidden_history_confirmation": False,
        "bc_dagger_or_rl_allowed": False,
        "next_if_pass": (
            "Build an authenticated eleven-basis bank and run a new "
            "unchanged-contract optimistic feasibility audit; do not "
            "execute R3c4 directly."
        ),
        "next_if_fail": (
            "Preserve raw and redesign target-relevant identification "
            "without weakening timing or response gates."
        ),
    }
    t1.r3c3.atomic_write_json(
        ctx.paths.analysis / "stage4_2r3c3t6_summary.json",
        dict(control_summary),
    )
    t1.r3c3.atomic_write_json(
        ctx.paths.analysis / "stage4_2r3c3t6_verdict.json", verdict
    )
    state = t1.r3c3.read_json(ctx.paths.state)
    state.update(
        {
            "finished": True,
            "primary_pass": primary_pass,
            "phase_status": "campaign_complete",
            "stop_reason": (
                "" if primary_pass else "identification_gate_failed"
            ),
            "verdict": verdict,
            "updated_utc": t1.r3c3.utc_timestamp(),
        }
    )
    t1.r3c3.atomic_write_json(ctx.paths.state, state)
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "control_summary": dict(control_summary),
        "verdict": verdict,
    }


def execute(
    ctx: Stage42R3C3T6Context,
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
            "Stage4.2R3c3T6 offline gate failed; no real TSC started"
        )
    if command == "offline":
        state = t1.r3c3.read_json(ctx.paths.state)
        state.update(
            {
                "finished": False,
                "primary_pass": False,
                "phase_status": "offline_gate_complete",
                "stop_reason": "",
                "offline_probe_audit": dict(offline),
                "updated_utc": t1.r3c3.utc_timestamp(),
            }
        )
        t1.r3c3.atomic_write_json(ctx.paths.state, state)
        return {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "phase": "offline_target_residual_probe_audit",
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
    cfg = t1.r3c3.read_json(
        _project_root()
        / "configs/stage4_2r3c3t6_target_residual_new_direction_"
        "identification_500ms.json"
    )
    _validate_config(cfg)
    path, preflight = _authenticate_preflight(cfg)
    cases = []
    for case in preflight["actuator_cases"]:
        delay = int(case["delay_steps"])
        probes = []
        for probe in case["probe_schedules"]:
            schedule = _signed_schedule(probe, sign=1)
            effects = sorted(step + delay + 1 for step in schedule)
            probes.append(
                {
                    "probe_id": probe["probe_id"],
                    "issue_count": len(schedule),
                    "first_effect_state": effects[0],
                    "last_formal_effect_state": int(
                        probe["last_formal_effect_state"]
                    ),
                    "cancellation_effect_states": effects[35:],
                    "requested_net": np.sum(
                        np.stack(list(schedule.values())), axis=0
                    ).tolist(),
                }
            )
        cases.append(
            {
                "delay_steps": delay,
                "slew_scale": float(case["slew_scale"]),
                "probes": probes,
            }
        )
    passed = bool(
        len(cases) == 2
        and all(
            len(case["probes"]) == 3
            and all(
                probe["issue_count"] == 41
                and probe["cancellation_effect_states"]
                == [39, 40, 41, 42, 43, 44]
                and max(abs(x) for x in probe["requested_net"]) <= 1e-12
                for probe in case["probes"]
            )
            for case in cases
        )
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "design_revision": 1,
        "candidate_preflight_path": str(path),
        "candidate_preflight_sha256": _sha256(path),
        "expected_rollouts": 224,
        "cases": cases,
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
        description="Stage4.2R3c3T6 new-direction identification"
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
        (
            "--source-stage4-2r3c3t1-run",
            args.source_stage4_2r3c3t1_run,
        ),
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
    ctx = load_stage42r3c3t6_config(
        args.config,
        source_stage42r3b_run=args.source_stage4_2r3b_run,
        source_stage42r3c3_run=args.source_stage4_2r3c3_run,
        source_stage42r3c3_bank_dir=args.source_stage4_2r3c3_bank_dir,
        source_stage42r3c3t1_run=args.source_stage4_2r3c3t1_run,
        source_stage42r3c3t1_audit_dir=(
            args.source_stage4_2r3c3t1_audit_dir
        ),
        source_stage42r3c3t3_controller_bank=(
            args.source_stage4_2r3c3t3_controller_bank
        ),
        run_dir_override=args.run_dir,
    )
    result = execute(
        ctx,
        command=args.command,
        backend=args.backend,
        resume=args.resume,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
