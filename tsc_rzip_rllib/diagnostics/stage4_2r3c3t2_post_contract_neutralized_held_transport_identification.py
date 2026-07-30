#!/usr/bin/env python3
"""Stage4.2R3c3T2 post-contract-neutralized held transport probes.

This is a new identification identity.  It keeps each signed response active
through the immutable 350/370 ms contract, neutralizes at physical states
39--44, and observes through 500 ms.  The longer observation never changes
the formal arrival or hold horizon.
"""

from __future__ import annotations

import argparse
import copy
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
from tsc_rzip_rllib.utils.ray_runtime import ensure_ray_worker_plan

try:
    import resource
except ImportError:  # pragma: no cover - Windows
    resource = None


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T2"
CONTROLLER_REVISION = (
    "post_contract_neutralized_held_transport_probe_v42r3c3t2_v2"
)
PACKAGE_REVISION = (
    "r42r3c3t2_post_contract_held_transport_identification_v2h1"
)
RUN_NAME = (
    "stage4_2r3c3t2_post_contract_neutralized_held_transport_"
    "identification"
)
OBSERVATION_HORIZON = 50
N_MODES = t1.N_MODES
N_COILS = t1.N_COILS
N_WIRES = t1.N_WIRES
BASELINE_PROBE_ID = "held_transport_baseline"
PROBE_IDS = {"held_transport_mode0", "held_transport_mode1"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_digest(value: Any) -> str:
    return t1._canonical_digest(value)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _formal_horizon(slew: float) -> int:
    if math.isclose(float(slew), 0.9, rel_tol=0.0, abs_tol=1.0e-12):
        return 37
    if math.isclose(float(slew), 1.0, rel_tol=0.0, abs_tol=1.0e-12):
        return 35
    raise ValueError(f"unsupported locked slew scale: {slew}")


def _validate_config(cfg: Mapping[str, Any]) -> None:
    if (
        cfg.get("stage") != STAGE
        or int(cfg.get("design_revision", -1)) != 2
        or cfg.get("run_name") != RUN_NAME
        or cfg.get("controller_revision") != CONTROLLER_REVISION
        or cfg.get("package_revision") != PACKAGE_REVISION
    ):
        raise ValueError("Stage4.2R3c3T2 identity changed")
    probe = cfg["identification_probe"]
    matrix = cfg["control_matrix"]
    if (
        int(probe["observation_horizon_steps"]) != OBSERVATION_HORIZON
        or [float(x) for x in probe["physical_mode_amplitude"]]
        != [0.006, 0.0075, 0.0]
        or probe["extended_baseline_probe_id"] != BASELINE_PROBE_ID
        or int(probe["required_nonzero_issue_count"]) != 12
        or float(probe["maximum_current_utilization"]) != 0.55
        or float(
            probe["maximum_selected_velocity_condition_number"]
        )
        != 25.0
        or float(
            probe["maximum_combined_velocity_condition_number"]
        )
        != 25.0
    ):
        raise ValueError("Stage4.2R3c3T2 probe gates changed")
    basis = probe["basis"]
    if len(basis) != 2:
        raise ValueError("Stage4.2R3c3T2 basis count changed")
    for index, row in enumerate(basis):
        if (
            int(row["mode"]) != index
            or str(row["probe_id"])
            != f"held_transport_mode{index}"
            or int(row["first_effect_state"]) != 3
            or list(map(int, row["positive_effect_states"]))
            != [3, 4, 5, 6, 7, 8]
            or list(map(int, row["negative_effect_states"]))
            != [39, 40, 41, 42, 43, 44]
        ):
            raise ValueError("Stage4.2R3c3T2 schedule changed")
    if (
        int(matrix["expected_rollouts"]) != 160
        or int(matrix["expected_signed_probe_rollouts"]) != 128
        or int(matrix["expected_extended_baseline_rollouts"]) != 32
        or int(matrix["expected_baseline_contexts"]) != 32
        or int(matrix["expected_rollouts_per_baseline_context"]) != 5
    ):
        raise ValueError("Stage4.2R3c3T2 matrix changed")
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
        raise ValueError("Stage4.2R3c3T2 formal contract changed")
    if (
        not bool(cfg["development_set_only"])
        or bool(cfg["independent_hidden_history_confirmation"])
        or bool(cfg["independent_long_hold_validated"])
        or bool(cfg["bc_dagger_or_rl_allowed"])
    ):
        raise ValueError("Stage4.2R3c3T2 scope changed")


def _resolved_config(config_path: Path) -> tuple[dict[str, Any], Path]:
    path = config_path.expanduser().resolve()
    overlay = t1.r3c3.read_json(path)
    base_path = (
        _project_root() / str(overlay["base_stage_config"])
    ).resolve()
    if (
        not base_path.is_file()
        or _sha256(base_path)
        != str(overlay["base_stage_config_sha256"])
    ):
        raise ValueError("frozen T1 base config mismatch")
    base = t1.r3c3.read_json(base_path)
    cfg = copy.deepcopy(base)
    for key, value in overlay.items():
        cfg[key] = copy.deepcopy(value)
    _validate_config(cfg)
    return cfg, base_path


@dataclass(frozen=True)
class Stage42R3C3T2Paths:
    run_dir: Path
    control: Path
    raw: Path
    variants: Path
    source_reference: Path
    analysis: Path
    manifest: Path
    state: Path


@dataclass(frozen=True)
class Stage42R3C3T2Context:
    cfg: dict[str, Any]
    base_config_path: Path
    source_ctx: t1.Stage42R3C3T1Context
    source_t1_run: Path
    source_t1_audit_dir: Path
    source_t1_fingerprint: dict[str, Any]
    paths: Stage42R3C3T2Paths


def _paths(run_dir: Path) -> Stage42R3C3T2Paths:
    root = run_dir.expanduser().resolve()
    return Stage42R3C3T2Paths(
        run_dir=root,
        control=root / "stage4_2r3c3t2_held_transport_identification",
        raw=(
            root
            / "stage4_2r3c3t2_held_transport_identification"
            / "raw"
        ),
        variants=root / "stage4_2r3c3t2_environment_variants",
        source_reference=root / "stage4_2r3c3t2_source_reference",
        analysis=root / "stage4_2r3c3t2_analysis",
        manifest=root / "stage4_2r3c3t2_manifest.json",
        state=root / "stage4_2r3c3t2_state.json",
    )


def _authenticate_t1_source(
    cfg: Mapping[str, Any],
    run_dir: Path,
    audit_dir: Path,
) -> dict[str, Any]:
    req = cfg["source_t1_requirements"]
    run = run_dir.expanduser().resolve()
    audit = audit_dir.expanduser().resolve()
    if run.name != str(req["required_run_name"]):
        raise ValueError("unexpected T1 source run")
    manifest_path = run / "stage4_2r3c3t1_manifest.json"
    state_path = run / "stage4_2r3c3t1_state.json"
    server_audit_path = audit / "stage4_2r3c3t1_server_audit.json"
    diagnostic_path = (
        audit / "stage4_2r3c3t1_six_basis_feasibility_diagnostic_v2.json"
    )
    manifest = t1.r3c3.read_json(manifest_path)
    state = t1.r3c3.read_json(state_path)
    server_audit = t1.r3c3.read_json(server_audit_path)
    diagnostic = t1.r3c3.read_json(diagnostic_path)
    if (
        manifest.get("stage") != req["required_stage"]
        or manifest.get("controller_revision")
        != req["required_controller_revision"]
        or manifest.get("package_revision")
        != req["required_package_revision"]
        or not bool(state.get("finished"))
        or bool(state.get("primary_pass"))
        or _sha256(server_audit_path)
        != req["required_server_audit_sha256"]
        or _sha256(diagnostic_path)
        != req["required_corrected_six_basis_diagnostic_sha256"]
        or not bool(server_audit["raw_and_manifest_integrity_passed"])
        or int(server_audit["control_raw_actual"])
        != int(req["required_raw_count"])
        or str(server_audit["raw_inventory"]["digest"])
        != req["required_raw_inventory_digest"]
        or int(
            server_audit["control_summary"][
                "combined_condition_pass_count"
            ]
        )
        != int(req["required_combined_condition_pass_count"])
        or int(
            server_audit["control_summary"][
                "combined_condition_group_count"
            ]
        )
        != int(req["required_combined_condition_context_count"])
        or int(
            diagnostic["scale_summaries"][0][
                "optimistic_formal_pass_count"
            ]
        )
        != int(req["required_optimistic_formal_pass_count"])
        or int(
            diagnostic["scale_summaries"][0][
                "failed_baseline_repair_count"
            ]
        )
        != int(req["required_failed_context_repair_count"])
    ):
        raise ValueError("T1 failed-source authentication mismatch")
    return {
        "run_dir": str(run),
        "manifest_sha256": _sha256(manifest_path),
        "state_sha256": _sha256(state_path),
        "server_audit_sha256": _sha256(server_audit_path),
        "corrected_diagnostic_sha256": _sha256(diagnostic_path),
        "raw_count": int(server_audit["control_raw_actual"]),
        "raw_inventory_digest": str(
            server_audit["raw_inventory"]["digest"]
        ),
        "runtime_package_fingerprint_digest": str(
            server_audit["runtime_package_fingerprint_digest"]
        ),
        "primary_pass": False,
        "failure_class": "identification_design_failure",
    }


def load_stage42r3c3t2_config(
    config_path: Path,
    *,
    source_stage42r3b_run: Path,
    source_stage42r3c3_run: Path,
    source_stage42r3c3_bank_dir: Path,
    source_stage42r3c3t1_run: Path,
    source_stage42r3c3t1_audit_dir: Path,
    run_dir_override: Path,
) -> Stage42R3C3T2Context:
    cfg, base_config = _resolved_config(config_path)
    source_t1_run = source_stage42r3c3t1_run.expanduser().resolve()
    source_ctx = t1.load_stage42r3c3t1_config(
        base_config,
        source_stage42r3b_run=source_stage42r3b_run,
        source_stage42r3c3_run=source_stage42r3c3_run,
        source_stage42r3c3_bank_dir=source_stage42r3c3_bank_dir,
        run_dir_override=source_t1_run,
    )
    source_t1_audit = source_stage42r3c3t1_audit_dir.expanduser().resolve()
    fingerprint = _authenticate_t1_source(
        cfg, source_t1_run, source_t1_audit
    )
    return Stage42R3C3T2Context(
        cfg=cfg,
        base_config_path=base_config,
        source_ctx=source_ctx,
        source_t1_run=source_t1_run,
        source_t1_audit_dir=source_t1_audit,
        source_t1_fingerprint=fingerprint,
        paths=_paths(run_dir_override),
    )


def _probe_schedule(
    *,
    basis: Mapping[str, Any],
    actual_delay: int,
    sign: int,
    amplitude_by_mode: Sequence[float],
) -> dict[int, np.ndarray]:
    mode = int(basis["mode"])
    amplitude = float(amplitude_by_mode[mode]) * int(sign)
    schedule: dict[int, np.ndarray] = {}
    for effect_state, polarity in [
        *[(state, 1) for state in basis["positive_effect_states"]],
        *[(state, -1) for state in basis["negative_effect_states"]],
    ]:
        issue_step = int(effect_state) - int(actual_delay) - 1
        if issue_step < 0 or issue_step >= OBSERVATION_HORIZON:
            raise ValueError("T2 issue step outside observation horizon")
        delta = np.zeros(N_MODES, dtype=float)
        delta[mode] = amplitude * polarity
        if issue_step in schedule:
            raise ValueError("duplicate T2 issue step")
        schedule[issue_step] = delta
    if len(schedule) != 12:
        raise ValueError("T2 schedule cardinality changed")
    return schedule


def _context_key(spec: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        str(spec["pair_id"]),
        str(spec["history_member"]),
        str(spec["target_id"]),
        int(spec["action_delay_steps"]),
        float(spec["slew_scale"]),
    )


def build_control_specs(
    ctx: Stage42R3C3T2Context,
    selected_pairs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    source_specs = t1.build_control_specs(ctx.source_ctx, selected_pairs)
    templates: dict[tuple[Any, ...], Mapping[str, Any]] = {}
    for spec in source_specs:
        templates.setdefault(_context_key(spec), spec)
    if len(templates) != 32:
        raise ValueError("T2 source context coverage mismatch")
    probe = ctx.cfg["identification_probe"]
    amplitudes = list(map(float, probe["physical_mode_amplitude"]))
    specs: list[dict[str, Any]] = []
    for key in sorted(templates):
        template = copy.deepcopy(dict(templates[key]))
        rows: list[tuple[str, int, int, dict[int, np.ndarray]]] = [
            (BASELINE_PROBE_ID, -1, 0, {})
        ]
        for basis in probe["basis"]:
            for sign in probe["probe_signs"]:
                rows.append(
                    (
                        str(basis["probe_id"]),
                        int(basis["mode"]),
                        int(sign),
                        _probe_schedule(
                            basis=basis,
                            actual_delay=int(
                                template["action_delay_steps"]
                            ),
                            sign=int(sign),
                            amplitude_by_mode=amplitudes,
                        ),
                    )
                )
        for probe_id, mode, sign, schedule in rows:
            identity = {
                "stage": STAGE,
                "source_context": list(key),
                "probe_id": probe_id,
                "probe_sign": sign,
                "schedule": {
                    str(step): value.tolist()
                    for step, value in schedule.items()
                },
                "observation_horizon_steps": OBSERVATION_HORIZON,
                "controller_revision": CONTROLLER_REVISION,
                "source_t1_raw_inventory_digest": (
                    ctx.source_t1_fingerprint["raw_inventory_digest"]
                ),
            }
            experiment_id = t1.r3c3._scenario_digest(identity)
            spec = copy.deepcopy(template)
            spec.update(
                {
                    "kind": (
                        "stage4_2r3c3t2_post_contract_neutralized_"
                        "held_transport_identification"
                    ),
                    "stage": STAGE,
                    "controller_revision": CONTROLLER_REVISION,
                    "underlying_controller_revision": (
                        t1.r3c1.CONTROLLER_REVISION
                    ),
                    "experiment_id": experiment_id,
                    "phase": "post_contract_held_transport_identification",
                    "category": (
                        "post_contract_held_transport_identification"
                    ),
                    "environment_variant": (
                        f"stage4_2r3c3t2_{experiment_id}"
                    ),
                    "horizon_steps": OBSERVATION_HORIZON,
                    "formal_horizon_steps": _formal_horizon(
                        float(template["slew_scale"])
                    ),
                    "identification_only": True,
                    "r3c3_probe_id": probe_id,
                    "r3c3_probe_mode": mode,
                    "r3c3_probe_sign": sign,
                    "r3c3_probe_first_effect_state": (
                        3 if schedule else -1
                    ),
                    "r3c3_probe_delta_by_task_issue_step": {
                        str(step): value.tolist()
                        for step, value in schedule.items()
                    },
                    "r3c3_requested_probe_net": [0.0] * N_MODES,
                    "r3c3_probe_amplitude": (
                        amplitudes[mode] if mode >= 0 else 0.0
                    ),
                    "r3c3t2_schedule_contract": (
                        "positive_states_3_to_8_negative_states_"
                        "39_to_44_observe_through_50_zero_net_v2"
                    ),
                    "source_stage4_2r3c3t1_raw_inventory_digest": (
                        ctx.source_t1_fingerprint[
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
        raise ValueError("T2 control identity coverage mismatch")
    return specs


def _controller_spec(spec: Mapping[str, Any]) -> dict[str, Any]:
    return t1._controller_spec(spec)


class PostContractHeldTransportProbeController(
    t1.LongSeparationTransportProbeController
):
    """Exact R3c1 controller plus a fixed T2 schedule or zero baseline."""

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
        self.probe_amplitude = float(
            source_spec["r3c3_probe_amplitude"]
        )
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
            expected_amplitude = 0.006 if self.probe_mode == 0 else 0.0075
            valid = bool(
                self.probe_id in PROBE_IDS
                and self.probe_mode in {0, 1}
                and self.probe_sign in {-1, 1}
                and self.probe_first_effect_state == 3
                and math.isclose(
                    self.probe_amplitude,
                    expected_amplitude,
                    rel_tol=0.0,
                    abs_tol=1.0e-15,
                )
                and len(self.probe_schedule) == 12
            )
        if not valid:
            raise ValueError("Stage4.2R3c3T2 controller contract invalid")
        if self.probe_schedule:
            requested = np.sum(
                np.stack(list(self.probe_schedule.values())), axis=0
            )
            if not np.allclose(
                requested,
                np.zeros(N_MODES, dtype=float),
                rtol=0.0,
                atol=1.0e-12,
            ):
                raise ValueError("Stage4.2R3c3T2 probe is not zero net")

    def action(
        self, current_state: Mapping[str, Any]
    ) -> tuple[np.ndarray, dict[str, Any]]:
        action, trace = super().action(current_state)
        trace.pop("r3c3t1_identification_only", None)
        trace.update(
            {
                "r3c3t2_identification_only": True,
                "r3c3t2_observation_horizon_steps": (
                    OBSERVATION_HORIZON
                ),
                "r3c3t2_post_contract_neutralization": True,
            }
        )
        return action, trace


def _control_payload(
    ctx: Stage42R3C3T2Context, *, spec: Mapping[str, Any]
) -> dict[str, Any]:
    proxy = SimpleNamespace(
        source_ctx=ctx.source_ctx.source_ctx,
        cfg=ctx.cfg,
        paths=ctx.paths,
    )
    payload = t1.r3c3._control_payload(proxy, spec=spec)
    train_cfg = copy.deepcopy(payload["train_cfg"])
    train_cfg.setdefault("episode", {})[
        "max_episode_steps"
    ] = OBSERVATION_HORIZON
    experiment_id = str(spec["experiment_id"])
    t1.r3c3.atomic_write_json(
        ctx.paths.variants / f"train_{experiment_id}.json",
        train_cfg,
    )
    payload["train_cfg"] = train_cfg
    payload["stage4_1r4_horizon_steps"] = OBSERVATION_HORIZON
    payload["variant_id"] = (
        f"stage4_2r3c3t2_{spec['experiment_id']}"
    )
    payload["stage4_2r3c3t2_restart_snapshot_dir"] = str(
        spec["restart_snapshot_dir"]
    )
    payload["stage4_2r3c3t2_snapshot_manifest_digest"] = str(
        spec["restart_snapshot_manifest_digest"]
    )
    t1.r3c3.atomic_write_json(
        ctx.paths.variants / f"payload_{experiment_id}.json",
        payload,
    )
    return payload


def _json_safe(value: Any) -> Any:
    return t1._json_safe(value)


class LocalHeldTransportResponseProbeWorker:
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
            "underlying_controller_revision": (
                t1.r3c1.CONTROLLER_REVISION
            ),
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
                raise ValueError("T2 observation/formal horizon changed")
            self.base.env.reset()
            zero_action = np.zeros(N_COILS, dtype=np.float32)
            initial = t1.r1._state_record_full(
                self.base.env, 0, zero_action
            )
            trajectory = [initial]
            controller = PostContractHeldTransportProbeController(
                self.base,
                self.bundle,
                _controller_spec(spec),
                initial,
            )
            trace = []
            for step in range(horizon):
                action, controller_row = controller.action(trajectory[-1])
                _, _, terminated, truncated, info = self.base.env.step(
                    action
                )
                next_state = t1.r1._state_record_full(
                    self.base.env, step + 1, action
                )
                trajectory.append(next_state)
                trace.append(controller_row)
                controller.advance(next_state)
                if terminated:
                    raise RuntimeError(
                        str(
                            info.get(
                                "failure_reason",
                                "environment terminated",
                            )
                        )
                    )
                if truncated and step + 1 < horizon:
                    raise RuntimeError(
                        "environment truncated before T2 horizon"
                    )
            schedule = {
                int(step): np.asarray(value, dtype=float)
                for step, value in spec[
                    "r3c3_probe_delta_by_task_issue_step"
                ].items()
            }
            issued_rows = {
                int(row["task_step"]): row
                for row in trace
                if row.get("r3c3_probe_issued")
            }
            requested = np.asarray(
                [
                    issued_rows[step]["r3c3_probe_requested_delta"]
                    for step in sorted(issued_rows)
                ],
                dtype=float,
            )
            applied = np.asarray(
                [
                    issued_rows[step][
                        "r3c3_probe_applied_desired_delta"
                    ]
                    for step in sorted(issued_rows)
                ],
                dtype=float,
            )
            baseline = str(spec["r3c3_probe_id"]) == BASELINE_PROBE_ID
            expected_count = 0 if baseline else 12
            scheduled_exact = bool(
                len(issued_rows) == len(schedule) == expected_count
                and set(issued_rows) == set(schedule)
                and all(
                    np.array_equal(
                        np.asarray(
                            issued_rows[step][
                                "r3c3_probe_requested_delta"
                            ],
                            dtype=float,
                        ),
                        value,
                    )
                    for step, value in schedule.items()
                )
            )
            if baseline:
                applied_exact = requested.size == applied.size == 0
                requested_net = np.zeros(N_MODES)
                applied_net = np.zeros(N_MODES)
            else:
                shape = (12, N_MODES)
                applied_exact = bool(
                    requested.shape == applied.shape == shape
                    and np.allclose(
                        requested, applied, rtol=0.0, atol=1.0e-12
                    )
                )
                requested_net = (
                    np.sum(requested, axis=0)
                    if requested.shape == shape
                    else np.full(N_MODES, np.nan)
                )
                applied_net = (
                    np.sum(applied, axis=0)
                    if applied.shape == shape
                    else np.full(N_MODES, np.nan)
                )
            zero_net = bool(
                np.allclose(
                    requested_net,
                    np.zeros(N_MODES),
                    rtol=0.0,
                    atol=1.0e-12,
                )
                and np.allclose(
                    applied_net,
                    np.zeros(N_MODES),
                    rtol=0.0,
                    atol=1.0e-12,
                )
            )
            causal = not any(
                bool(row.get("future_measurement_used"))
                or bool(row.get("hidden_wire_used"))
                or bool(row.get("source_action_used"))
                or bool(row.get("source_coil_current_used"))
                or bool(row.get("source_wire_current_used"))
                or bool(row.get("current_run_future_used"))
                or bool(row.get("pair_or_history_label_used"))
                or bool(row.get("source_result_used"))
                for row in trace
            )
            success = bool(
                len(trajectory) == horizon + 1
                and len(trace) == horizon
                and not any(
                    bool(row.get("abnormal")) for row in trajectory
                )
                and all(bool(row.get("computed_online")) for row in trace)
                and all(bool(row.get("solver_success")) for row in trace)
                and causal
                and scheduled_exact
                and applied_exact
                and zero_net
            )
            result.update(
                {
                    "success": success,
                    "completed": True,
                    "failure_reason": (
                        ""
                        if success
                        else "incomplete or invalid T2 rollout"
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
                        "controller_previous_correction_initialization": (
                            "zero"
                        ),
                        "controller_delay_queue_initialization": (
                            "authenticated_visible_manifold_phase_"
                            "aligned_nominal_prime"
                        ),
                        "reference_phase_start": (
                            controller.reference_phase_start
                        ),
                        "baseline_controller_revision": (
                            t1.r3c1.CONTROLLER_REVISION
                        ),
                        "identification_only": True,
                        "extended_baseline": baseline,
                        "probe_id": controller.probe_id,
                        "probe_mode": controller.probe_mode,
                        "probe_sign": controller.probe_sign,
                        "probe_first_effect_state": (
                            controller.probe_first_effect_state
                        ),
                        "probe_issue_steps": sorted(schedule),
                        "scheduled_probe_exact": scheduled_exact,
                        "applied_probe_exact": applied_exact,
                        "requested_probe_net": requested_net.tolist(),
                        "applied_probe_net": applied_net.tolist(),
                        "requested_and_applied_zero_net": zero_net,
                        "observation_horizon_steps": horizon,
                        "formal_horizon_steps": int(
                            spec["formal_horizon_steps"]
                        ),
                        "first_negative_effect_state": (
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
            return _json_safe(result)
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
            return _json_safe(result)
        finally:
            runner = getattr(self.base.env, "runner", None)
            if runner is not None:
                runner.cleanup_episode_workspace(
                    failed=failed,
                    reason="stage4_2r3c3t2_held_transport_identification",
                )


_CONTROL_RAY_ACTOR = None


def _control_ray_actor_class():
    global _CONTROL_RAY_ACTOR
    if _CONTROL_RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class Stage42R3C3T2ControlActor:
            def __init__(
                self, payload, library, bundle, worker_id, selector_cfg
            ):
                self.worker = LocalHeldTransportResponseProbeWorker(
                    payload, library, bundle, worker_id, selector_cfg
                )

            def evaluate(self, spec):
                return self.worker.evaluate(spec)

            def close(self):
                self.worker.close()
                return True

        _CONTROL_RAY_ACTOR = Stage42R3C3T2ControlActor
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
    ctx: Stage42R3C3T2Context,
    specs: Sequence[dict[str, Any]],
    *,
    backend: str,
    resume: bool,
) -> list[dict[str, Any]]:
    ctx.paths.raw.mkdir(parents=True, exist_ok=True)
    library, bundle, selector = t1.r1._library_bundle_selector(
        ctx.source_ctx.source_ctx.r1_ctx
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
            worker = LocalHeldTransportResponseProbeWorker(
                payloads[str(spec["experiment_id"])],
                library,
                bundle,
                f"stage42r3c3t2_serial_{index:03d}",
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
            print(
                f"[Stage4.2R3c3T2] {index + 1}/{len(pending)}",
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
                or ctx.cfg["parallel"].get("ray_tmpdir")
            ),
            log_prefix="[Stage4.2R3c3T2]",
        )
        Actor = _control_ray_actor_class()
        completed = 0
        print(
            "[Stage4.2R3c3T2] "
            f"maximum_actor_count={plan.actor_count} "
            f"pending={len(pending)}",
            flush=True,
        )
        for batch_start in range(0, len(pending), plan.actor_count):
            batch = pending[
                batch_start : batch_start + plan.actor_count
            ]
            actors = []
            refs = {}
            for offset, spec in enumerate(batch):
                index = batch_start + offset
                actor = Actor.remote(
                    payloads[str(spec["experiment_id"])],
                    library,
                    bundle,
                    f"stage42r3c3t2_{index:03d}",
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
                            "[Stage4.2R3c3T2] "
                            f"waiting {completed}/{len(pending)}",
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
                                "[Stage4.2R3c3T2] "
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


def _phase_trace_valid(
    result: Mapping[str, Any],
) -> dict[str, Any]:
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
    expected_count = 0 if baseline else 12
    requested_rows = []
    applied_rows = []
    trace_exact = bool(
        len(trace) == OBSERVATION_HORIZON
        and len(schedule) == expected_count
    )
    solver_failure_count = 0
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
        trace_exact = bool(
            trace_exact
            and requested.shape == applied.shape == (N_MODES,)
            and issued == (step in schedule)
            and np.array_equal(requested, expected)
            and bool(row.get("r3c3t2_identification_only"))
        )
        if issued:
            issued_count += 1
            requested_rows.append(requested)
            applied_rows.append(applied)
        solver_failure_count += not bool(row.get("solver_success"))
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
    if expected_count:
        requested_array = np.asarray(requested_rows, dtype=float)
        applied_array = np.asarray(applied_rows, dtype=float)
        applied_exact = bool(
            requested_array.shape
            == applied_array.shape
            == (expected_count, N_MODES)
            and np.allclose(
                requested_array,
                applied_array,
                rtol=0.0,
                atol=1.0e-12,
            )
        )
        requested_net = np.sum(requested_array, axis=0)
        applied_net = np.sum(applied_array, axis=0)
    else:
        applied_exact = not requested_rows and not applied_rows
        requested_net = np.zeros(N_MODES)
        applied_net = np.zeros(N_MODES)
    zero_net = bool(
        np.allclose(
            requested_net, np.zeros(N_MODES), rtol=0.0, atol=1.0e-12
        )
        and np.allclose(
            applied_net, np.zeros(N_MODES), rtol=0.0, atol=1.0e-12
        )
    )
    passed = bool(
        base["passed"]
        and trace_exact
        and issued_count == expected_count
        and applied_exact
        and zero_net
        and forbidden_count == 0
        and solver_failure_count == 0
    )
    return {
        **base,
        "passed": passed,
        "probe_trace_exact": trace_exact,
        "probe_issued_count": issued_count,
        "probe_applied_exact": applied_exact,
        "probe_requested_net": requested_net.tolist(),
        "probe_applied_net": applied_net.tolist(),
        "probe_zero_net": zero_net,
        "forbidden_trace_count": forbidden_count,
        "solver_failure_count": solver_failure_count,
        "extended_baseline": baseline,
    }


def _formal_prefix_metrics(
    ctx: Stage42R3C3T2Context,
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
    return t1.r3c3._formal_metrics(
        ctx.source_ctx.base_ctx, truncated
    )


def _full_current_utilization(
    ctx: Stage42R3C3T2Context,
    result: Mapping[str, Any],
) -> float:
    r13_ctx = t1.r1._r13_ctx(ctx.source_ctx.source_ctx.r1_ctx)
    env_cfg = (
        r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34.env_cfg
    )
    currents = np.asarray(
        [row["currents_a_display"] for row in result["trajectory"]],
        dtype=float,
    )
    minimum = np.asarray(
        env_cfg["min_current_a_display_order"], dtype=float
    )
    maximum = np.asarray(
        env_cfg["max_current_a_display_order"], dtype=float
    )
    center = 0.5 * (minimum + maximum)
    half = np.maximum(0.5 * (maximum - minimum), 1.0e-9)
    return float(
        np.max(np.abs((currents - center[None, :]) / half[None, :]))
    )


def _initial_arrays(
    result: Mapping[str, Any],
) -> tuple[np.ndarray, np.ndarray]:
    return t1.r3c3._initial_restart_arrays(result)


def _arrays(
    result: Mapping[str, Any], dt_s: float
) -> tuple[np.ndarray, np.ndarray]:
    return t1.r3c3._trajectory_arrays(result, dt_s)


def _rmse(array: np.ndarray) -> float:
    return t1.r3c3._rmse(array)


def _source_prefix_exact(
    ctx: Stage42R3C3T2Context,
    result: Mapping[str, Any],
) -> bool:
    source_id = str(result["spec"]["baseline_experiment_id"])
    source = t1.r3c3.read_json_gz(
        ctx.source_ctx.source_r3c1_run
        / "stage4_2r3c1_authenticated_visible_manifold_control"
        / "raw"
        / f"{source_id}.json.gz"
    )
    horizon = int(result["spec"]["formal_horizon_steps"])
    fields = (
        "R",
        "Z",
        "Ip",
        "currents_a_tsc",
        "wire_currents_a",
        "action_norm_tsc",
    )
    actual = list(result["trajectory"])[: horizon + 1]
    expected = list(source["trajectory"])
    return bool(
        len(actual) == len(expected) == horizon + 1
        and all(
            all(actual[index][field] == expected[index][field] for field in fields)
            for index in range(horizon + 1)
        )
    )


def _combined_condition_rows(
    ctx: Stage42R3C3T2Context,
    odd_by_key: Mapping[
        tuple[Any, ...], tuple[np.ndarray, np.ndarray, np.ndarray, int]
    ],
) -> list[dict[str, Any]]:
    audit_bank = t1.r3c3.read_json(
        ctx.source_ctx.source_bank_dir / t1.EXPECTED_AUDIT_BANK_NAME
    )
    old_by_key = {}
    for context in audit_bank["contexts"]:
        identity = context["audit_identity"]
        key = (
            str(identity["pair_id"]),
            str(identity["history_member"]),
            str(identity["target_id"]),
            int(context["actual_delay_steps"]),
            float(context["actual_slew_scale"]),
        )
        old_by_key[key] = [
            np.asarray(
                response["delta_velocity_RZ_by_state"], dtype=float
            )
            for response in sorted(
                context["responses"],
                key=lambda row: int(row["basis_index"]),
            )
        ]
    new_by_context: dict[tuple[Any, ...], dict[str, np.ndarray]] = (
        defaultdict(dict)
    )
    for key, response in odd_by_key.items():
        new_by_context[key[:5]][key[5]] = response[1]
    maximum = float(
        ctx.cfg["identification_probe"][
            "maximum_combined_velocity_condition_number"
        ]
    )
    rows = []
    for key in sorted(old_by_key):
        new = new_by_context.get(key, {})
        formal_horizon = _formal_horizon(float(key[4]))
        arrays = [
            *old_by_key[key],
            *[
                new[probe_id][: formal_horizon + 1]
                for probe_id in sorted(PROBE_IDS)
                if probe_id in new
            ],
        ]
        rank = None
        condition = None
        passed = False
        if (
            set(new) == PROBE_IDS
            and len(arrays) == 6
            and len({array.shape for array in arrays}) == 1
        ):
            matrix = np.stack(
                [array[3:, :2].reshape(-1) for array in arrays],
                axis=1,
            )
            rank = int(np.linalg.matrix_rank(matrix))
            condition = float(np.linalg.cond(matrix))
            passed = bool(
                rank == 6
                and math.isfinite(condition)
                and condition <= maximum
            )
        rows.append(
            {
                "pair_id": key[0],
                "history_member": key[1],
                "target_id": key[2],
                "actual_delay_steps": key[3],
                "actual_slew_scale": key[4],
                "controller_use_end_state": formal_horizon,
                "basis_count": 6,
                "velocity_response_matrix_rank": rank,
                "selected_velocity_condition_number": condition,
                "condition_number_pass": passed,
            }
        )
    return rows


def summarize_control(
    ctx: Stage42R3C3T2Context,
    results: Sequence[Mapping[str, Any]],
    selected_pairs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    expected = int(ctx.cfg["control_matrix"]["expected_rollouts"])
    probe_cfg = ctx.cfg["identification_probe"]
    central_cfg = probe_cfg["central_symmetry"]
    history_cfg = probe_cfg["matched_hidden_history"]
    dt_ms = int(
        t1.r1._r13_ctx(ctx.source_ctx.source_ctx.r1_ctx)
        .r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34.env_cfg[
            "dt_ms"
        ]
    )
    dt_s = dt_ms / 1000.0
    state_map = t1.r3b._selected_state_map(selected_pairs)
    base_source_ctx = ctx.source_ctx.source_ctx
    rows = []
    by_context: dict[tuple[Any, ...], dict[str, Mapping[str, Any]]] = (
        defaultdict(dict)
    )
    for result in results:
        spec = result["spec"]
        by_context[_context_key(spec)][
            (
                BASELINE_PROBE_ID
                if spec["r3c3_probe_id"] == BASELINE_PROBE_ID
                else f"{spec['r3c3_probe_id']}:{spec['r3c3_probe_sign']}"
            )
        ] = result
        state_id = str(spec["state_generation_experiment_id"])
        base = t1.r3b._control_row(
            base_source_ctx, result, state_map[state_id]
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
                "probe_mode": int(spec["r3c3_probe_mode"]),
                "probe_sign": int(spec["r3c3_probe_sign"]),
                "extended_baseline": baseline,
                "extended_baseline_prefix_exact": prefix_exact,
                "formal_horizon_steps": int(
                    spec["formal_horizon_steps"]
                ),
                "observation_horizon_steps": int(
                    spec["horizon_steps"]
                ),
                "phase_trace_valid": bool(phase["passed"]),
                "probe_trace_exact": bool(
                    phase["probe_trace_exact"]
                ),
                "probe_issued_count": int(
                    phase["probe_issued_count"]
                ),
                "probe_applied_exact": bool(
                    phase["probe_applied_exact"]
                ),
                "probe_zero_net": bool(phase["probe_zero_net"]),
                "solver_failure_count": int(
                    phase["solver_failure_count"]
                ),
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
                        formal[
                            "stage3_4_tracking_minimum_signed_margin"
                        ]
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

    baseline_results = {}
    signed_groups: dict[
        tuple[Any, ...], dict[str, dict[int, Mapping[str, Any]]]
    ] = defaultdict(lambda: defaultdict(dict))
    for key, members in by_context.items():
        if BASELINE_PROBE_ID in members:
            baseline_results[key] = members[BASELINE_PROBE_ID]
        for name, result in members.items():
            if name == BASELINE_PROBE_ID:
                continue
            probe_id, sign_text = name.rsplit(":", 1)
            signed_groups[key][probe_id][int(sign_text)] = result
    if len(baseline_results) != 32:
        raise ValueError("T2 extended baseline coverage mismatch")

    response_rows = []
    odd_by_key: dict[
        tuple[Any, ...], tuple[np.ndarray, np.ndarray, np.ndarray, int]
    ] = {}
    for context_key in sorted(signed_groups):
        baseline = baseline_results[context_key]
        base_y, base_v = _arrays(baseline, dt_s)
        for probe_id in sorted(PROBE_IDS):
            signed = signed_groups[context_key].get(probe_id, {})
            response_key = (*context_key, probe_id)
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
                and all(
                    bool(result.get("success"))
                    for result in signed.values()
                )
            ):
                plus_y, plus_v = _arrays(signed[1], dt_s)
                minus_y, minus_v = _arrays(signed[-1], dt_s)
                same_shape = (
                    plus_y.shape == minus_y.shape == base_y.shape
                    and plus_v.shape == minus_v.shape == base_v.shape
                )
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
                if same_shape:
                    first = 3
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
                            central_cfg[
                                "maximum_even_position_rmse_m"
                            ]
                        )
                        and ip_rmse
                        <= float(
                            central_cfg["maximum_even_ip_rmse_A"]
                        )
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
                    odd_by_key[response_key] = (
                        odd_y,
                        odd_v,
                        base_y,
                        first,
                    )
            response_rows.append(row)

    history_groups: dict[
        tuple[Any, ...],
        dict[str, tuple[np.ndarray, np.ndarray, np.ndarray, int]],
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
                section = slice(3, OBSERVATION_HORIZON + 1)
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
                        history_cfg[
                            "maximum_odd_position_rmse_m"
                        ]
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

    context_groups: dict[
        tuple[Any, ...],
        dict[str, tuple[np.ndarray, np.ndarray, np.ndarray, int]],
    ] = defaultdict(dict)
    for key, response in odd_by_key.items():
        context_groups[key[:5]][key[5]] = response
    condition_rows = []
    maximum_condition = float(
        probe_cfg["maximum_selected_velocity_condition_number"]
    )
    for key in sorted(context_groups):
        probes = context_groups[key]
        horizon = _formal_horizon(float(key[4]))
        rank = None
        condition = None
        passed = False
        if set(probes) == PROBE_IDS:
            columns = [
                probes[probe_id][1][3 : horizon + 1, :2].reshape(-1)
                for probe_id in sorted(PROBE_IDS)
            ]
            matrix = np.stack(columns, axis=1)
            rank = int(np.linalg.matrix_rank(matrix))
            condition = float(np.linalg.cond(matrix))
            passed = bool(
                rank == 2
                and math.isfinite(condition)
                and condition <= maximum_condition
            )
        condition_rows.append(
            {
                "pair_id": key[0],
                "history_member": key[1],
                "target_id": key[2],
                "actual_delay_steps": key[3],
                "actual_slew_scale": key[4],
                "controller_use_end_state": horizon,
                "velocity_response_matrix_rank": rank,
                "selected_velocity_condition_number": condition,
                "condition_number_pass": passed,
            }
        )
    combined_rows = _combined_condition_rows(ctx, odd_by_key)

    execution_count = sum(bool(row["execution_pass"]) for row in rows)
    baseline_exact_count = sum(
        bool(row["extended_baseline_prefix_exact"]) for row in rows
    )
    central_count = sum(
        bool(row["central_symmetry_pass"]) for row in response_rows
    )
    history_count = sum(
        bool(row["matched_hidden_history_pass"]) for row in history_rows
    )
    condition_count = sum(
        bool(row["condition_number_pass"]) for row in condition_rows
    )
    combined_count = sum(
        bool(row["condition_number_pass"]) for row in combined_rows
    )
    current_values = [
        float(row["max_current_utilization"])
        for row in rows
        if row["max_current_utilization"] is not None
    ]
    maximum_current = max(current_values) if current_values else None
    selected_condition_values = [
        float(row["selected_velocity_condition_number"])
        for row in condition_rows
        if row["selected_velocity_condition_number"] is not None
    ]
    combined_condition_values = [
        float(row["selected_velocity_condition_number"])
        for row in combined_rows
        if row["selected_velocity_condition_number"] is not None
    ]
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "post_contract_held_transport_identification",
        "identification_only": True,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "development_set_only": True,
        "independent_hidden_history_confirmation": False,
        "observation_horizon_steps": OBSERVATION_HORIZON,
        "formal_timing_unchanged": True,
        "expected_rollouts": expected,
        "n_rollouts": len(rows),
        "execution_pass_count": execution_count,
        "extended_baseline_prefix_exact_count": baseline_exact_count,
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
            row["failure_class"]
            == "extended_baseline_prefix_mismatch"
            for row in rows
        ),
        "forbidden_controller_input_count": sum(
            int(row["forbidden_trace_count"]) for row in rows
        ),
        "solver_failure_count": sum(
            int(row["solver_failure_count"]) for row in rows
        ),
        "formal_contract_pass_count": sum(
            bool(row["formal_contract_pass"]) for row in rows
        ),
        "formal_contract_failure_count": sum(
            not bool(row["formal_contract_pass"]) for row in rows
        ),
        "formal_tracking_is_acceptance_gate": False,
        "response_group_count": len(response_rows),
        "expected_response_group_count": 64,
        "central_symmetry_pass_count": central_count,
        "central_symmetry_failure_count": len(response_rows)
        - central_count,
        "matched_hidden_history_group_count": len(history_rows),
        "expected_matched_hidden_history_group_count": 32,
        "matched_hidden_history_pass_count": history_count,
        "matched_hidden_history_failure_count": len(history_rows)
        - history_count,
        "condition_number_group_count": len(condition_rows),
        "expected_condition_number_group_count": 32,
        "condition_number_pass_count": condition_count,
        "condition_number_failure_count": len(condition_rows)
        - condition_count,
        "maximum_selected_velocity_condition_number": (
            max(selected_condition_values)
            if selected_condition_values
            else None
        ),
        "combined_condition_group_count": len(combined_rows),
        "expected_combined_condition_group_count": 32,
        "combined_condition_pass_count": combined_count,
        "combined_condition_failure_count": len(combined_rows)
        - combined_count,
        "maximum_combined_velocity_condition_number": (
            max(combined_condition_values)
            if combined_condition_values
            else None
        ),
        "maximum_current_utilization": maximum_current,
        "maximum_current_utilization_allowed": float(
            probe_cfg["maximum_current_utilization"]
        ),
    }
    summary["execution_gate_passed"] = bool(
        len(rows) == expected
        and execution_count == expected
        and baseline_exact_count == 32
        and summary["forbidden_controller_input_count"] == 0
        and summary["solver_failure_count"] == 0
    )
    summary["central_symmetry_gate_passed"] = bool(
        len(response_rows) == central_count == 64
    )
    summary["matched_hidden_history_gate_passed"] = bool(
        len(history_rows) == history_count == 32
    )
    summary["condition_number_gate_passed"] = bool(
        len(condition_rows) == condition_count == 32
    )
    summary["combined_condition_number_gate_passed"] = bool(
        len(combined_rows) == combined_count == 32
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
    outputs = (
        ("results", rows),
        ("central_response_results", response_rows),
        ("matched_hidden_history_results", history_rows),
        ("condition_number_results", condition_rows),
        ("combined_condition_number_results", combined_rows),
    )
    ctx.paths.control.mkdir(parents=True, exist_ok=True)
    for name, values in outputs:
        t1.r3c3.atomic_write_json(
            ctx.paths.control / f"{name}.json", values
        )
        t1.r3c3.write_csv(ctx.paths.control / f"{name}.csv", values)
    t1.r3c3.atomic_write_json(
        ctx.paths.control / "summary.json", summary
    )
    return summary


def _package_files(ctx: Stage42R3C3T2Context) -> list[Path]:
    project = _project_root()
    names = [
        "AGENTS.md",
        "PACKAGE_MANIFEST.json",
        "SHA256SUMS",
        (
            "configs/stage4_2r3c3t1_long_separation_zero_net_"
            "transport_identification_370ms.json"
        ),
        (
            "configs/stage4_2r3c3t2_post_contract_neutralized_"
            "held_transport_identification_500ms.json"
        ),
        (
            "tsc_rzip_rllib/diagnostics/stage4_2r3c3t2_post_"
            "contract_neutralized_held_transport_identification.py"
        ),
        "scripts/stage4_2r3c3t2_server_postprocess.py",
        "run_stage4_2r3c3t2_common.sh",
        "run_stage4_2r3c3t2_offline.sh",
        "run_stage4_2r3c3t2_post_contract_neutralized_held_transport_identification_native.sh",
        "run_stage4_2r3c3t2_post_contract_neutralized_held_transport_identification_nohup.sh",
        "run_stage4_2r3c3t2_self_test.sh",
        "run_stage4_2r3c3t2_server_postprocess.sh",
        "run_stage4_2r3c3t2_verify_package.sh",
        "run_stop_stage4_2r3c3t2_now.sh",
    ]
    paths = [project / name for name in names]
    manifest = t1.r3c3.read_json(project / "PACKAGE_MANIFEST.json")
    for relative in manifest["file_inventory"]:
        path = project / str(relative)
        if path not in paths:
            paths.append(path)
    return paths


def _deployed_package_fingerprint(
    ctx: Stage42R3C3T2Context,
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
        "contract": "r42r3c3t2_deployed_package_source_v2",
        "n_files": len(rows),
        "digest": _canonical_digest(rows),
        "files": rows,
    }


def _prepare_dirs(paths: Stage42R3C3T2Paths) -> None:
    for path in (
        paths.run_dir,
        paths.control,
        paths.raw,
        paths.variants,
        paths.source_reference,
        paths.analysis,
    ):
        path.mkdir(parents=True, exist_ok=True)


def _validate_resume_manifest(
    existing: Mapping[str, Any],
    proposed: Mapping[str, Any],
) -> None:
    for key, value in proposed.items():
        if existing.get(key) != value:
            raise ValueError(
                "Stage4.2R3c3T2 resume incompatibility in "
                f"manifest field {key}"
            )


def prepare(
    ctx: Stage42R3C3T2Context, *, resume: bool
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    _prepare_dirs(ctx.paths)
    selected_pairs, _ = t1.r3c3._recompute_selected_pairs(
        ctx.source_ctx.base_ctx
    )
    specs = build_control_specs(ctx, selected_pairs)
    package_fingerprint = _deployed_package_fingerprint(ctx)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "source_stage4_2r3c3t1_run": str(ctx.source_t1_run),
        "source_stage4_2r3c3t1_audit_dir": str(
            ctx.source_t1_audit_dir
        ),
        "source_stage4_2r3c3t1_fingerprint": (
            ctx.source_t1_fingerprint
        ),
        "source_stage4_2r3c3_run": str(
            ctx.source_ctx.source_r3c3_run
        ),
        "source_stage4_2r3c3_bank_dir": str(
            ctx.source_ctx.source_bank_dir
        ),
        "source_stage4_2r3c3_bank_fingerprint": (
            ctx.source_ctx.source_bank_fingerprint
        ),
        "source_stage4_2r3b_run": str(ctx.source_ctx.source_r3b_run),
        "source_fingerprint": ctx.source_ctx.source_fingerprint,
        "source_stage4_2r3c1_run": str(
            ctx.source_ctx.source_r3c1_run
        ),
        "source_stage4_2r3c1_fingerprint": (
            ctx.source_ctx.source_r3c1_fingerprint
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
        "independent_hidden_history_confirmation": False,
        "independent_long_hold_validated": False,
    }
    if ctx.paths.manifest.is_file():
        if not resume:
            raise FileExistsError(
                "Stage4.2R3c3T2 run exists; use resume or a fresh run"
            )
        old = t1.r3c3.read_json(ctx.paths.manifest)
        _validate_resume_manifest(old, manifest)
    else:
        t1.r3c3.atomic_write_json(ctx.paths.manifest, manifest)
    t1.r3c3.atomic_write_json(
        ctx.paths.run_dir / "stage4_2r3c3t2_config.resolved.json",
        ctx.cfg,
    )
    t1.r3c3.atomic_write_json(
        ctx.paths.source_reference / "control_specs.json", specs
    )
    t1.r3c3.atomic_write_json(
        ctx.paths.source_reference
        / "source_stage4_2r3c3t1_fingerprint.json",
        ctx.source_t1_fingerprint,
    )
    t1.r3c3.atomic_write_json(
        ctx.paths.source_reference
        / "deployed_package_fingerprint.json",
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
    ctx: Stage42R3C3T2Context,
    selected_pairs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    specs = build_control_specs(ctx, selected_pairs)
    library, bundle, selector = t1.r1._library_bundle_selector(
        ctx.source_ctx.source_ctx.r1_ctx
    )
    baseline_dir = (
        ctx.source_ctx.source_r3c1_run
        / "stage4_2r3c1_authenticated_visible_manifold_control"
        / "raw"
    )
    grouped: dict[tuple[Any, ...], list[Mapping[str, Any]]] = (
        defaultdict(list)
    )
    schedule_rows = []
    for spec in specs:
        grouped[_context_key(spec)].append(spec)
        schedule = {
            int(step): np.asarray(value, dtype=float).reshape(N_MODES)
            for step, value in spec[
                "r3c3_probe_delta_by_task_issue_step"
            ].items()
        }
        baseline = str(spec["r3c3_probe_id"]) == BASELINE_PROBE_ID
        if schedule:
            net = np.sum(np.stack(list(schedule.values())), axis=0)
            delay = int(spec["action_delay_steps"])
            positive_effects = sorted(
                step + delay + 1
                for step, value in schedule.items()
                if float(value[int(spec["r3c3_probe_mode"])])
                * int(spec["r3c3_probe_sign"])
                > 0
            )
            negative_effects = sorted(
                step + delay + 1
                for step, value in schedule.items()
                if float(value[int(spec["r3c3_probe_mode"])])
                * int(spec["r3c3_probe_sign"])
                < 0
            )
        else:
            net = np.zeros(N_MODES)
            positive_effects = []
            negative_effects = []
        exact = bool(
            (
                baseline
                and not schedule
                and int(spec["r3c3_probe_sign"]) == 0
            )
            or (
                not baseline
                and len(schedule) == 12
                and positive_effects == [3, 4, 5, 6, 7, 8]
                and negative_effects == [39, 40, 41, 42, 43, 44]
                and np.allclose(
                    net,
                    np.zeros(N_MODES),
                    rtol=0.0,
                    atol=1.0e-12,
                )
            )
        )
        schedule_rows.append(
            {
                "experiment_id": str(spec["experiment_id"]),
                "probe_id": str(spec["r3c3_probe_id"]),
                "probe_sign": int(spec["r3c3_probe_sign"]),
                "extended_baseline": baseline,
                "issue_steps": sorted(schedule),
                "positive_effect_states": positive_effects,
                "negative_effect_states": negative_effects,
                "requested_net": net.tolist(),
                "schedule_exact": exact,
            }
        )
    action_rows = []
    for index, key in enumerate(sorted(grouped)):
        context_specs = grouped[key]
        baseline_id = str(context_specs[0]["baseline_experiment_id"])
        source_baseline = t1.r3c3.read_json_gz(
            baseline_dir / f"{baseline_id}.json.gz"
        )
        initial = copy.deepcopy(dict(source_baseline["trajectory"][0]))
        initial["step_index"] = 0
        payload = _control_payload(ctx, spec=context_specs[0])
        payload_horizon_exact = bool(
            int(payload["stage4_1r4_horizon_steps"])
            == OBSERVATION_HORIZON
            and int(
                payload["train_cfg"]["episode"]["max_episode_steps"]
            )
            == OBSERVATION_HORIZON
        )
        plant = t1.r1.LocalPlantReplayWorker(
            payload,
            library,
            bundle,
            f"stage42r3c3t2_offline_{index:03d}",
            selector,
        )
        try:
            for spec in context_specs:
                sanitized = _controller_spec(spec)
                controller = PostContractHeldTransportProbeController(
                    plant.base_worker, bundle, sanitized, initial
                )
                action, trace = controller.action(initial)
                hidden = copy.deepcopy(initial)
                hidden["wire_currents_a"] = [
                    float(wire + 1) * 1.0e9
                    for wire in range(N_WIRES)
                ]
                hidden_controller = (
                    PostContractHeldTransportProbeController(
                        plant.base_worker, bundle, sanitized, hidden
                    )
                )
                hidden_action, hidden_trace = hidden_controller.action(
                    hidden
                )
                baseline = (
                    str(spec["r3c3_probe_id"]) == BASELINE_PROBE_ID
                )
                expected_issued = bool(
                    not baseline
                    and int(spec["action_delay_steps"]) == 2
                )
                passed = bool(
                    np.all(np.isfinite(action))
                    and np.array_equal(action, hidden_action)
                    and bool(trace["r3c3_probe_issued"])
                    == expected_issued
                    and bool(hidden_trace["r3c3_probe_issued"])
                    == expected_issued
                    and int(trace["measurement_max_state_index_used"]) == 0
                    and not bool(trace["future_measurement_used"])
                    and not bool(trace["hidden_wire_used"])
                    and not bool(trace["source_action_used"])
                    and not bool(trace["source_result_used"])
                    and not bool(trace["pair_or_history_label_used"])
                    and payload_horizon_exact
                    and int(plant.base_worker.env.max_episode_steps)
                    == OBSERVATION_HORIZON
                )
                action_rows.append(
                    {
                        "experiment_id": str(spec["experiment_id"]),
                        "finite_first_action": bool(
                            np.all(np.isfinite(action))
                        ),
                        "hidden_wire_invariant": bool(
                            np.array_equal(action, hidden_action)
                        ),
                        "probe_issue_at_step_zero_expected": (
                            expected_issued
                        ),
                        "probe_issue_at_step_zero_actual": bool(
                            trace["r3c3_probe_issued"]
                        ),
                        "payload_horizon_exact": payload_horizon_exact,
                        "environment_horizon_steps": int(
                            plant.base_worker.env.max_episode_steps
                        ),
                        "passed": passed,
                    }
                )
        finally:
            plant.close()
    expected = int(ctx.cfg["control_matrix"]["expected_rollouts"])
    raw_count = len(list(ctx.paths.raw.glob("*.json.gz")))
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "offline_held_transport_probe_audit",
        "expected_probe_specs": expected,
        "probe_spec_count": len(schedule_rows),
        "extended_baseline_spec_count": sum(
            bool(row["extended_baseline"]) for row in schedule_rows
        ),
        "signed_probe_spec_count": sum(
            not bool(row["extended_baseline"]) for row in schedule_rows
        ),
        "probe_schedule_exact_count": sum(
            bool(row["schedule_exact"]) for row in schedule_rows
        ),
        "finite_causal_action_count": sum(
            bool(row["passed"]) for row in action_rows
        ),
        "baseline_context_count": len(grouped),
        "hidden_wire_invariant_action_count": sum(
            bool(row["hidden_wire_invariant"]) for row in action_rows
        ),
        "payload_and_environment_horizon_exact_count": sum(
            bool(row["payload_horizon_exact"])
            and int(row["environment_horizon_steps"])
            == OBSERVATION_HORIZON
            for row in action_rows
        ),
        "raw_count": raw_count,
        "plant_advance_count": 0,
        "real_tsc_executed": False,
    }
    summary["passed"] = bool(
        len(schedule_rows) == expected
        and summary["extended_baseline_spec_count"] == 32
        and summary["signed_probe_spec_count"] == 128
        and summary["probe_schedule_exact_count"] == expected
        and len(action_rows) == expected
        and summary["finite_causal_action_count"] == expected
        and len(grouped) == 32
        and summary["hidden_wire_invariant_action_count"] == expected
        and summary[
            "payload_and_environment_horizon_exact_count"
        ]
        == expected
        and raw_count == 0
    )
    t1.r3c3.atomic_write_json(
        ctx.paths.source_reference / "offline_held_transport_audit.json",
        {
            "summary": summary,
            "probe_schedules": schedule_rows,
            "first_actions": action_rows,
        },
    )
    return summary


def analyze(
    ctx: Stage42R3C3T2Context,
    control_summary: Mapping[str, Any],
) -> dict[str, Any]:
    primary_pass = bool(control_summary.get("passed"))
    verdict = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "verdict": (
            "STAGE4_2R3C3T2_HELD_TRANSPORT_IDENTIFICATION_PASS"
            if primary_pass
            else "STAGE4_2R3C3T2_HELD_TRANSPORT_IDENTIFICATION_FAIL"
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
            "Build an authenticated combined bank server-side and "
            "require 32/32 unchanged-contract optimistic formal "
            "feasibility before R3c4 implementation."
        ),
        "next_if_fail": (
            "Preserve all raw and redesign the dynamic response model "
            "without weakening timing or response gates."
        ),
    }
    t1.r3c3.atomic_write_json(
        ctx.paths.analysis / "stage4_2r3c3t2_summary.json",
        dict(control_summary),
    )
    t1.r3c3.atomic_write_json(
        ctx.paths.analysis / "stage4_2r3c3t2_verdict.json", verdict
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
    ctx: Stage42R3C3T2Context,
    *,
    command: str,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    selected_pairs, specs = prepare(ctx, resume=resume)
    offline = run_offline_probe_audit(ctx, selected_pairs)
    if not bool(offline.get("passed")):
        raise RuntimeError(
            "Stage4.2R3c3T2 offline gate failed; no real TSC started"
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
            "phase": "offline_held_transport_probe_audit",
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
    basis0 = {
        "mode": 0,
        "positive_effect_states": [3, 4, 5, 6, 7, 8],
        "negative_effect_states": [39, 40, 41, 42, 43, 44],
    }
    delay0 = _probe_schedule(
        basis=basis0,
        actual_delay=0,
        sign=1,
        amplitude_by_mode=[0.006, 0.0075, 0.0],
    )
    delay2 = _probe_schedule(
        basis=basis0,
        actual_delay=2,
        sign=1,
        amplitude_by_mode=[0.006, 0.0075, 0.0],
    )
    net0 = np.sum(np.stack(list(delay0.values())), axis=0)
    net2 = np.sum(np.stack(list(delay2.values())), axis=0)
    passed = bool(
        sorted(delay0)
        == [2, 3, 4, 5, 6, 7, 38, 39, 40, 41, 42, 43]
        and sorted(delay2)
        == [0, 1, 2, 3, 4, 5, 36, 37, 38, 39, 40, 41]
        and np.allclose(
            net0, np.zeros(N_MODES), rtol=0.0, atol=1.0e-12
        )
        and np.allclose(
            net2, np.zeros(N_MODES), rtol=0.0, atol=1.0e-12
        )
        and _formal_horizon(1.0) == 35
        and _formal_horizon(0.9) == 37
        and min(step + 1 for step in delay0 if step >= 38) == 39
        and min(step + 3 for step in delay2 if step >= 36) == 39
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "design_revision": 2,
        "delay0_issue_steps": sorted(delay0),
        "delay2_issue_steps": sorted(delay2),
        "delay0_requested_net": net0.tolist(),
        "delay2_requested_net": net2.tolist(),
        "first_negative_physical_effect_state": 39,
        "observation_horizon_steps": OBSERVATION_HORIZON,
        "formal_normal_hold_through_step": 35,
        "formal_weak_hold_through_step": 37,
        "identification_only": True,
        "observation_horizon_is_long_hold_validation": False,
        "probe_trajectories_allowed_in_expert_dataset": False,
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
        description=(
            "Stage4.2R3c3T2 post-contract-neutralized held "
            "transport identification"
        )
    )
    parser.add_argument("--config", type=Path)
    parser.add_argument("--source-stage4-2r3b-run", type=Path)
    parser.add_argument("--source-stage4-2r3c3-run", type=Path)
    parser.add_argument("--source-stage4-2r3c3-bank-dir", type=Path)
    parser.add_argument("--source-stage4-2r3c3t1-run", type=Path)
    parser.add_argument(
        "--source-stage4-2r3c3t1-audit-dir", type=Path
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
        ("--run-dir", args.run_dir),
    )
    missing = [name for name, value in required if value is None]
    if missing:
        parser.error(
            "missing required arguments: " + ", ".join(missing)
        )
    ctx = load_stage42r3c3t2_config(
        args.config,
        source_stage42r3b_run=args.source_stage4_2r3b_run,
        source_stage42r3c3_run=args.source_stage4_2r3c3_run,
        source_stage42r3c3_bank_dir=(
            args.source_stage4_2r3c3_bank_dir
        ),
        source_stage42r3c3t1_run=args.source_stage4_2r3c3t1_run,
        source_stage42r3c3t1_audit_dir=(
            args.source_stage4_2r3c3t1_audit_dir
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
