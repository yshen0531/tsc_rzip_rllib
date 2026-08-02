#!/usr/bin/env python3
"""Stage4.2R3c3T13S5 exact-Card15 lattice transition holdout."""

from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN
import hashlib
import json
import math
import os
from pathlib import Path
import time
import traceback
from types import SimpleNamespace
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.control.quantized_actuator import (
    DEVELOPMENT_READBACK_BIAS_GRID_UNITS_TSC,
    OUTPUT_GRID_KAT,
    QuantizedActuatorModel,
)
from tsc_rzip_rllib.core.inputa import format_number
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s1_minimal_transition_sentinel as s1,
)
from tsc_rzip_rllib.utils.ray_runtime import ensure_ray_worker_plan


t11 = s1.t11
SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S5"
RUN_NAME = "stage4_2r3c3t13s5_lattice_native_split_holdout"
CAMPAIGN_IDENTITY = "quantized_lattice_native_split_two_step_blind_holdout_v1"
CONTROLLER_REVISION = "quantized_lattice_native_split_probe_v42r3c3t13s5_v1"
EXECUTION_PACKAGE_REVISION = "r42r3c3t13s5_lattice_native_split_holdout_v1"
PACKAGE_REVISION = "r42r3c3t13s5_lattice_native_split_holdout_v1h1"
BASELINE_PROBE_ID = "lattice_baseline"
WINDOWS = ("transport", "braking")
DIRECTIONS = (
    "mode0_without_coil8",
    "mode0_coil8_component",
    "mode1",
    "mode2",
)
SIGNS = (-1, 1)
N_MODES = 3
N_DIRECTIONS = 4
N_COILS = 14
EXPECTED_CURRENT_COMPONENTS = 34_272
REPORTING_HOTFIX_PATHS = frozenset({
    "PACKAGE_MANIFEST.json",
    "configs/stage4_2r3c3t13s5_lattice_native_split_holdout_370ms.json",
    "run_stage4_2r3c3t13s5_verify_package.sh",
    "scripts/stage4_2r3c3t13s5_server_postprocess.py",
    "tests/test_stage4_2r3c3t13s5_lattice_native_split_holdout.py",
    "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s5_lattice_native_split_holdout.py",
})


@dataclass
class BlindOpenOrderGuard:
    """Fail closed if a holdout raw is opened before a model hash exists."""

    expected_development_count: int = 34
    development_open_count: int = 0
    holdout_open_count: int = 0
    model_sha256: str = ""

    def before_open(self, role: str) -> None:
        if role == "development":
            if self.model_sha256 or self.holdout_open_count:
                raise ValueError("development raw opened after T13S5 model freeze")
            self.development_open_count += 1
            return
        if role != "blind_holdout":
            raise ValueError(f"unknown T13S5 raw role: {role}")
        if (
            self.development_open_count != self.expected_development_count
            or len(self.model_sha256) != 64
        ):
            raise ValueError("holdout raw opened before development model hash")
        self.holdout_open_count += 1

    def freeze(self, model_sha256: str) -> None:
        if self.development_open_count != self.expected_development_count:
            raise ValueError("cannot freeze T13S5 model before all development raw")
        if self.holdout_open_count:
            raise ValueError("cannot freeze T13S5 model after holdout access")
        if len(model_sha256) != 64:
            raise ValueError("T13S5 model SHA-256 must contain 64 hexadecimal digits")
        int(model_sha256, 16)
        self.model_sha256 = model_sha256.lower()


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
class Stage42R3C3T13S5Paths:
    run_dir: Path
    control: Path
    raw: Path
    variants: Path
    source_reference: Path
    model: Path
    analysis: Path
    manifest: Path
    state: Path


@dataclass(frozen=True)
class Stage42R3C3T13S5Context:
    cfg: dict[str, Any]
    base_config_path: Path
    base_ctx: t11.Stage42R3C3T11Context
    paths: Stage42R3C3T13S5Paths


def _paths(run_dir: Path) -> Stage42R3C3T13S5Paths:
    root = run_dir.expanduser().resolve()
    control = root / RUN_NAME
    return Stage42R3C3T13S5Paths(
        run_dir=root,
        control=control,
        raw=control / "raw",
        variants=root / "stage4_2r3c3t13s5_environment_variants",
        source_reference=root / "stage4_2r3c3t13s5_source_reference",
        model=root / "stage4_2r3c3t13s5_frozen_model",
        analysis=root / "stage4_2r3c3t13s5_analysis",
        manifest=root / "stage4_2r3c3t13s5_manifest.json",
        state=root / "stage4_2r3c3t13s5_state.json",
    )


def _frozen_context_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        str(row["pair_id"]),
        str(row["history_member"]),
        str(row["target_id"]),
        int(row["action_delay_steps"]),
        float(row["slew_scale"]),
    )


def _context_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return t11._context_key(row)


def _validate_config(cfg: Mapping[str, Any]) -> None:
    if (
        cfg.get("stage") != STAGE
        or int(cfg.get("schema_version", -1)) != 1
        or int(cfg.get("design_revision", -1)) != 1
        or cfg.get("run_name") != RUN_NAME
        or cfg.get("campaign_identity") != CAMPAIGN_IDENTITY
        or cfg.get("controller_revision") != CONTROLLER_REVISION
        or cfg.get("package_revision") != PACKAGE_REVISION
        or cfg.get("underlying_controller_revision")
        != t11.t1.r3c1.CONTROLLER_REVISION
    ):
        raise ValueError("T13S5 campaign identity changed")
    expected_contexts = [
        (
            "hard", "development", "p5_q2_a0p900_gap2_settle4",
            "plus_first", "RZ_p10_m10", 2, 0.9,
            "s42r3c1_93d020858e4b4355c19d",
            "e40bc1f02a6559eef6f677683d5e0011e013f67ed5c4c6649f08824b02d030da",
            False, -0.3605615999999987,
        ),
        (
            "hard", "blind_holdout", "p5_q2_a0p900_gap2_settle4",
            "minus_first", "RZ_p10_m10", 2, 0.9,
            "s42r3c1_3f285839dc63859020d5",
            "11ba0651e04c5cc3cb16482f0f5bb7e6430425ff5a9886fd5bdca349727b8735",
            False, -0.3612697000000007,
        ),
        (
            "easy", "development", "p9_q2_a0p750_gap2_settle4",
            "plus_first", "nominal", 0, 1.0,
            "s42r3c1_1be965d393046a0768a8",
            "b931836adcc4486454a470ee75981d76ca79664da72487a8151110a84bbec05d",
            True, 0.10281705403080599,
        ),
        (
            "easy", "blind_holdout", "p9_q2_a0p750_gap2_settle4",
            "minus_first", "nominal", 0, 1.0,
            "s42r3c1_965d1418e70a2444e627",
            "96554811c713b35cc42aa12914e2b4af41cf7ff1e58ae7ae015873855ee1edb8",
            True, 0.10544524405844569,
        ),
    ]
    actual_contexts = [
        (
            str(row["stratum"]), str(row["offline_role"]),
            str(row["pair_id"]), str(row["history_member"]),
            str(row["target_id"]), int(row["action_delay_steps"]),
            float(row["slew_scale"]), str(row["source_r3c1_experiment_id"]),
            str(row["snapshot_manifest_sha256"]),
            bool(row["expected_formal_pass"]),
            float(row["expected_formal_minimum_signed_margin"]),
        )
        for row in cfg["holdout_contexts"]
    ]
    if actual_contexts != expected_contexts:
        raise ValueError("T13S5 evidence split changed")
    probe = cfg["lattice_probe"]
    expected_schedule = {
        "0": {"transport": (2, 3, 3, 4), "braking": (16, 17, 17, 18)},
        "2": {"transport": (0, 1, 3, 4), "braking": (14, 15, 17, 18)},
    }
    actual_schedule = {
        delay: {
            window: tuple(
                int(probe["schedule_by_delay"][delay][window][name])
                for name in (
                    "issue_step", "cancel_step", "first_effect_state",
                    "cancel_effect_state",
                )
            )
            for window in WINDOWS
        }
        for delay in ("0", "2")
    }
    if actual_schedule != expected_schedule:
        raise ValueError("T13S5 causal issue schedule changed")
    if (
        tuple(map(str, probe["probe_directions"])) != DIRECTIONS
        or tuple(map(int, probe["probe_signs"])) != SIGNS
        or tuple(probe["effect_windows"]) != WINDOWS
        or float(probe["significant_mode_fraction"]) != 0.10
        or int(probe["minimum_significant_grid_steps"]) != 1
        or int(probe["split_coil_index_tsc"]) != 8
        or float(probe["split_coil_target_current_delta_A"]) != 0.08
        or probe["cancellation_policy"]
        != "exact_return_to_stored_issue_center_then_exact_negative_current_center"
        or list(map(int, probe["lambda_multipliers"])) != [1, 2, 4, 8]
        or float(probe["minimum_coil_space_cosine"]) != 0.98
        or float(probe["maximum_relative_off_mode_residual"]) != 0.15
        or float(probe["maximum_incremental_normalized_action_linf"]) != 0.25
        or float(probe["maximum_total_normalized_action_abs"]) != 1.0
        or float(probe["maximum_current_utilization"]) != 0.55
        or float(probe["output_grid_kAt"]) != OUTPUT_GRID_KAT
        or tuple(map(float, probe["readback_bias_grid_units_tsc"]))
        != DEVELOPMENT_READBACK_BIAS_GRID_UNITS_TSC
        or tuple(map(float, probe["readback_radius_grid_units_tsc"]))
        != (1.0,) * N_COILS
        or int(probe["expected_current_components"])
        != EXPECTED_CURRENT_COMPONENTS
        or bool(probe["probe_trajectories_allowed_in_expert_dataset"])
        or bool(probe["pair_or_history_label_input_allowed"])
        or bool(probe["source_result_input_allowed"])
        or bool(probe["source_action_input_allowed"])
        or bool(probe["source_or_current_wire_input_allowed"])
    ):
        raise ValueError("T13S5 lattice/actuator contract changed")
    matrix = cfg["control_matrix"]
    if (
        int(matrix["expected_contexts"]) != 4
        or int(matrix["expected_development_contexts"]) != 2
        or int(matrix["expected_blind_holdout_contexts"]) != 2
        or int(matrix["expected_baseline_rollouts"]) != 4
        or int(matrix["expected_signed_probe_rollouts"]) != 64
        or int(matrix["expected_rollouts_per_context"]) != 17
        or int(matrix["expected_rollouts"]) != 68
        or int(matrix["expected_signed_groups"]) != 32
        or int(matrix["expected_model_stratum_windows"]) != 4
        or not all(bool(matrix[key]) for key in (
            "require_fresh_controller", "require_fresh_tsc_process",
            "forbid_future_actions", "forbid_future_measurements",
            "require_online_action_computation",
        ))
    ):
        raise ValueError("T13S5 matrix changed")
    timing = cfg["formal_timing_contract"]
    if (
        (int(timing["normal"]["arrival_deadline_step"]),
         int(timing["normal"]["hold_through_step"])) != (25, 35)
        or (int(timing["weak"]["arrival_deadline_step"]),
            int(timing["weak"]["hold_through_step"])) != (27, 37)
        or float(timing["position_tolerance_m"]) != 0.03
        or float(timing["speed_tolerance_m_per_s"]) != 0.1
        or float(timing["ip_tolerance_A"]) != 10000.0
        or int(timing["arrival_streak_steps"]) != 3
        or bool(timing["arrival_deadline_expansion_allowed"])
    ):
        raise ValueError("T13S5 formal timing changed")
    if (
        int(cfg["parallel"]["n_workers"]) != 68
        or not bool(cfg["storage"]["large_result_postprocess_on_server"])
        or not bool(cfg["storage"]["download_compact_audits_only"])
        or not bool(cfg["identification_only"])
        or not bool(cfg["blind_holdout_required"])
        or bool(cfg["independent_new_history_confirmation"])
        or bool(cfg["independent_long_hold_validated"])
        or bool(cfg["bc_dagger_or_rl_allowed"])
    ):
        raise ValueError("T13S5 scope changed")


def load_stage42r3c3t13s5_config(
    config_path: Path,
    *,
    source_stage42r3b_run: Path,
    source_stage42r3c3_run: Path,
    source_stage42r3c3_bank_dir: Path,
    source_stage42r3c3t1_run: Path,
    source_stage42r3c3t1_audit_dir: Path,
    source_stage42r3c3t3_controller_bank: Path,
    run_dir_override: Path,
) -> Stage42R3C3T13S5Context:
    config_path = config_path.expanduser().resolve()
    cfg = t11.t1.r3c3.read_json(config_path)
    _validate_config(cfg)
    base_path = (_project_root() / str(cfg["base_stage_config"])).resolve()
    if (
        not base_path.is_file()
        or _sha256(base_path) != str(cfg["base_stage_config_sha256"])
    ):
        raise ValueError("T13S5 frozen T11 base config mismatch")
    base_ctx = t11.load_stage42r3c3t11_config(
        base_path,
        source_stage42r3b_run=source_stage42r3b_run,
        source_stage42r3c3_run=source_stage42r3c3_run,
        source_stage42r3c3_bank_dir=source_stage42r3c3_bank_dir,
        source_stage42r3c3t1_run=source_stage42r3c3t1_run,
        source_stage42r3c3t1_audit_dir=source_stage42r3c3t1_audit_dir,
        source_stage42r3c3t3_controller_bank=source_stage42r3c3t3_controller_bank,
        run_dir_override=run_dir_override,
    )
    return Stage42R3C3T13S5Context(
        cfg=cfg,
        base_config_path=base_path,
        base_ctx=base_ctx,
        paths=_paths(run_dir_override),
    )


def _selected_pairs(ctx: Stage42R3C3T13S5Context) -> list[dict[str, Any]]:
    pairs, _ = t11.t1.r3c3._recompute_selected_pairs(
        ctx.base_ctx.base_ctx.source_ctx.base_ctx
    )
    return list(pairs)


def build_control_specs(
    ctx: Stage42R3C3T13S5Context,
    selected_pairs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    source = t11.build_control_specs(ctx.base_ctx, selected_pairs)
    source_baselines = {
        _context_key(spec): spec
        for spec in source
        if str(spec["r3c3_probe_id"]) == t11.BASELINE_PROBE_ID
    }
    frozen = {
        _frozen_context_key(row): row for row in ctx.cfg["holdout_contexts"]
    }
    if len(source_baselines) != 32 or len(frozen) != 4 or not set(frozen) <= set(source_baselines):
        raise ValueError("T13S5 source context coverage mismatch")
    specs: list[dict[str, Any]] = []
    schedule_cfg = ctx.cfg["lattice_probe"]["schedule_by_delay"]
    for key, row in sorted(frozen.items()):
        template = copy.deepcopy(dict(source_baselines[key]))
        if (
            str(template["baseline_experiment_id"])
            != str(row["source_r3c1_experiment_id"])
            or str(template["restart_snapshot_manifest_digest"])
            != str(row["snapshot_manifest_sha256"])
        ):
            raise ValueError("T13S5 source raw/snapshot identity mismatch")
        delay = int(template["action_delay_steps"])
        horizon = _formal_horizon(float(template["slew_scale"]))
        members = [(BASELINE_PROBE_ID, "baseline", "", 0)]
        members.extend(
            (f"lattice_{window}_{direction}", window, direction, sign)
            for window in WINDOWS for direction in DIRECTIONS for sign in SIGNS
        )
        for probe_id, window, direction, sign in members:
            schedule = None if window == "baseline" else schedule_cfg[str(delay)][window]
            identity = {
                "stage": STAGE,
                "campaign_identity": CAMPAIGN_IDENTITY,
                "source_context": list(key),
                "offline_role": str(row["offline_role"]),
                "probe_id": probe_id,
                "probe_sign": sign,
                "formal_horizon_steps": horizon,
                "controller_revision": CONTROLLER_REVISION,
                "source_t1_raw_inventory_digest": (
                    ctx.base_ctx.base_ctx.source_t1_fingerprint["raw_inventory_digest"]
                ),
            }
            experiment_id = t11.t1.r3c3._scenario_digest(identity)
            spec = copy.deepcopy(template)
            spec.update({
                "kind": "stage4_2r3c3t13s5_lattice_native_split_holdout",
                "stage": STAGE,
                "campaign_identity": CAMPAIGN_IDENTITY,
                "controller_revision": CONTROLLER_REVISION,
                "underlying_controller_revision": t11.t1.r3c1.CONTROLLER_REVISION,
                "experiment_id": experiment_id,
                "phase": "lattice_transition_holdout",
                "category": "identification_only_blind_holdout",
                "environment_variant": f"stage4_2r3c3t13s5_{experiment_id}",
                "horizon_steps": horizon,
                "formal_horizon_steps": horizon,
                "identification_only": True,
                "r3c3_probe_id": probe_id,
                "r3c3_probe_window": window,
                "r3c3_probe_direction": direction,
                "r3c3_probe_sign": sign,
                "r3c3_probe_issue_step": -1 if schedule is None else int(schedule["issue_step"]),
                "r3c3_probe_cancel_step": -1 if schedule is None else int(schedule["cancel_step"]),
                "r3c3_probe_first_effect_state": -1 if schedule is None else int(schedule["first_effect_state"]),
                "r3c3_probe_cancel_effect_state": -1 if schedule is None else int(schedule["cancel_effect_state"]),
                "r3c3t13s5_schedule_contract": "lattice_native_split_return_first_hybrid_cancel_v1",
                "r3c3t13s5_offline_role": str(row["offline_role"]),
                "r3c3t13s5_stratum": str(row["stratum"]),
                "r3c3t13s5_source_r3c1_experiment_id": str(row["source_r3c1_experiment_id"]),
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
            })
            specs.append(spec)
    expected = int(ctx.cfg["control_matrix"]["expected_rollouts"])
    if len(specs) != expected or len({str(row["experiment_id"]) for row in specs}) != expected:
        raise ValueError("T13S5 control identity coverage mismatch")
    return specs


def _decimal_field(field: str) -> Decimal:
    if len(field) != 10:
        raise ValueError("Card15 field must contain exactly ten characters")
    value = Decimal(field.strip())
    if not value.is_finite():
        raise ValueError("Card15 field must be finite")
    return value


def local_symmetric_card15_step(field: str) -> Decimal:
    """Return the smallest source-grid-bounded exact symmetric local step."""
    center = _decimal_field(field)
    if center == 0:
        quantum = Decimal(str(OUTPUT_GRID_KAT))
    else:
        quantum = Decimal(1).scaleb(center.copy_abs().adjusted() - 3)
        quantum = max(quantum, Decimal(str(OUTPUT_GRID_KAT)))
    for multiplier in range(1, 10_001):
        step = quantum * multiplier
        plus = center + step
        minus = center - step
        plus_field = format_number(float(plus))
        minus_field = format_number(float(minus))
        if (
            len(plus_field) == len(minus_field) == 10
            and _decimal_field(plus_field) == plus
            and _decimal_field(minus_field) == minus
            and plus - center == center - minus
        ):
            return step
    raise ValueError(f"no exact symmetric Card15 neighbor for {field!r}")


def _current_utilization(
    current: np.ndarray, minimum: np.ndarray, maximum: np.ndarray
) -> float:
    limits = np.maximum(np.abs(minimum), np.abs(maximum))
    if np.any(limits <= 0):
        raise ValueError("invalid current limits")
    return float(np.max(np.abs(current) / limits))


def choose_lattice_displacement(
    *,
    center_fields: Sequence[str],
    measured_current_a_tsc: Sequence[float],
    baseline_action_norm_tsc: Sequence[float],
    mode_vector_tsc: Sequence[float],
    turns_tsc: Sequence[float],
    max_slew_step_a: float,
    minimum_current_a_tsc: Sequence[float],
    maximum_current_a_tsc: Sequence[float],
    cfg: Mapping[str, Any],
) -> dict[str, Any]:
    center_decimal = tuple(_decimal_field(field) for field in center_fields)
    steps_kat = tuple(local_symmetric_card15_step(field) for field in center_fields)
    current = np.asarray(measured_current_a_tsc, dtype=float).reshape(N_COILS)
    baseline_action = np.asarray(baseline_action_norm_tsc, dtype=float).reshape(N_COILS)
    mode = np.asarray(mode_vector_tsc, dtype=float).reshape(N_COILS)
    turns = np.asarray(turns_tsc, dtype=float).reshape(N_COILS)
    minimum = np.asarray(minimum_current_a_tsc, dtype=float).reshape(N_COILS)
    maximum = np.asarray(maximum_current_a_tsc, dtype=float).reshape(N_COILS)
    step_a = np.asarray([float(value) for value in steps_kat]) * 1000.0 / turns
    significant = np.abs(mode) >= float(cfg["significant_mode_fraction"]) * float(np.max(np.abs(mode)))
    if not np.any(significant):
        raise ValueError("mode has no significant coil")
    lambda_min = float(np.max(
        int(cfg["minimum_significant_grid_steps"]) * step_a[significant]
        / np.abs(mode[significant])
    ))
    mode_norm = float(np.linalg.norm(mode))
    if not math.isclose(mode_norm, 1.0, rel_tol=0.0, abs_tol=1e-10):
        raise ValueError("authenticated mode vector is not unit length")
    candidate_rows = []
    for multiplier in map(int, cfg["lambda_multipliers"]):
        lam = lambda_min * multiplier
        counts = np.rint(lam * mode / step_a).astype(np.int64)
        delta_a = counts.astype(float) * step_a
        plus_fields = []
        minus_fields = []
        exact = True
        for center, step, count in zip(center_decimal, steps_kat, counts):
            delta = step * int(count)
            plus = center + delta
            minus = center - delta
            plus_field = format_number(float(plus))
            minus_field = format_number(float(minus))
            plus_fields.append(plus_field)
            minus_fields.append(minus_field)
            exact = bool(
                exact
                and len(plus_field) == len(minus_field) == 10
                and _decimal_field(plus_field) == plus
                and _decimal_field(minus_field) == minus
                and _decimal_field(plus_field) - center
                == center - _decimal_field(minus_field)
            )
        plus_target = np.asarray([
            float(_decimal_field(field)) * 1000.0 / turn
            for field, turn in zip(plus_fields, turns)
        ])
        minus_target = np.asarray([
            float(_decimal_field(field)) * 1000.0 / turn
            for field, turn in zip(minus_fields, turns)
        ])
        plus_action = (plus_target - current) / float(max_slew_step_a)
        minus_action = (minus_target - current) / float(max_slew_step_a)
        projection = float(np.dot(delta_a, mode)) * mode
        cosine = float(np.dot(delta_a, mode) / max(np.linalg.norm(delta_a) * mode_norm, 1e-300))
        off_mode = float(np.linalg.norm(delta_a - projection) / max(np.linalg.norm(delta_a), 1e-300))
        min_steps = int(np.min(np.abs(counts[significant])))
        incremental_linf = float(max(
            np.max(np.abs(plus_action - baseline_action)),
            np.max(np.abs(minus_action - baseline_action)),
        ))
        total_abs = float(max(np.max(np.abs(plus_action)), np.max(np.abs(minus_action))))
        bounds = bool(
            np.all(plus_target >= minimum) and np.all(plus_target <= maximum)
            and np.all(minus_target >= minimum) and np.all(minus_target <= maximum)
        )
        utilization = max(
            _current_utilization(plus_target, minimum, maximum),
            _current_utilization(minus_target, minimum, maximum),
        )
        passed = bool(
            min_steps >= int(cfg["minimum_significant_grid_steps"])
            and exact
            and cosine >= float(cfg["minimum_coil_space_cosine"])
            and off_mode <= float(cfg["maximum_relative_off_mode_residual"])
            and incremental_linf <= float(cfg["maximum_incremental_normalized_action_linf"])
            and total_abs <= float(cfg["maximum_total_normalized_action_abs"])
            and bounds
            and utilization <= float(cfg["maximum_current_utilization"])
        )
        row = {
            "lambda_multiplier": multiplier,
            "lambda_A": lam,
            "local_steps_kAt_tsc": [float(value) for value in steps_kat],
            "integer_grid_steps_tsc": counts.tolist(),
            "delta_current_a_tsc": delta_a.tolist(),
            "delta_field_kAt_tsc": [float(step * int(count)) for step, count in zip(steps_kat, counts)],
            "positive_target_fields": plus_fields,
            "negative_target_fields": minus_fields,
            "positive_action_norm_tsc": plus_action.tolist(),
            "negative_action_norm_tsc": minus_action.tolist(),
            "significant_coils_tsc": significant.tolist(),
            "minimum_significant_grid_steps_actual": min_steps,
            "target_field_central_symmetry_exact": exact,
            "coil_space_cosine": cosine,
            "relative_off_mode_residual": off_mode,
            "incremental_normalized_action_linf": incremental_linf,
            "total_normalized_action_abs": total_abs,
            "current_bounds_pass": bounds,
            "predicted_maximum_current_utilization": utilization,
            "passed": passed,
        }
        candidate_rows.append(row)
        if passed:
            row["candidate_rows_evaluated"] = [
                dict(candidate) for candidate in candidate_rows
            ]
            return row
    raise ValueError(
        "no frozen T13S5 lattice multiplier passed: "
        + json.dumps(candidate_rows, sort_keys=True)
    )


def exact_inverse_lattice_action(
    *,
    center_fields: Sequence[str],
    signed_issue_delta_kAt_tsc: Sequence[float],
    measured_current_a_tsc: Sequence[float],
    baseline_action_norm_tsc: Sequence[float],
    turns_tsc: Sequence[float],
    max_slew_step_a: float,
    minimum_current_a_tsc: Sequence[float],
    maximum_current_a_tsc: Sequence[float],
    cfg: Mapping[str, Any],
) -> dict[str, Any]:
    centers = tuple(_decimal_field(field) for field in center_fields)
    deltas = tuple(Decimal(str(value)) for value in signed_issue_delta_kAt_tsc)
    fields = tuple(
        format_number(float(center - delta))
        for center, delta in zip(centers, deltas)
    )
    exact = all(
        len(field) == 10 and _decimal_field(field) == center - delta
        for field, center, delta in zip(fields, centers, deltas)
    )
    turns = np.asarray(turns_tsc, dtype=float).reshape(N_COILS)
    current = np.asarray(measured_current_a_tsc, dtype=float).reshape(N_COILS)
    baseline = np.asarray(baseline_action_norm_tsc, dtype=float).reshape(N_COILS)
    minimum = np.asarray(minimum_current_a_tsc, dtype=float).reshape(N_COILS)
    maximum = np.asarray(maximum_current_a_tsc, dtype=float).reshape(N_COILS)
    target = np.asarray([
        float(_decimal_field(field)) * 1000.0 / turn
        for field, turn in zip(fields, turns)
    ])
    action = (target - current) / float(max_slew_step_a)
    incremental = float(np.max(np.abs(action - baseline)))
    total_abs = float(np.max(np.abs(action)))
    bounds = bool(np.all(target >= minimum) and np.all(target <= maximum))
    utilization = _current_utilization(target, minimum, maximum)
    passed = bool(
        exact
        and incremental <= float(cfg["maximum_incremental_normalized_action_linf"])
        and total_abs <= float(cfg["maximum_total_normalized_action_abs"])
        and bounds
        and utilization <= float(cfg["maximum_current_utilization"])
    )
    return {
        "target_fields": list(fields),
        "action_norm_tsc": action.tolist(),
        "incremental_normalized_action_linf": incremental,
        "total_normalized_action_abs": total_abs,
        "current_bounds_pass": bounds,
        "predicted_maximum_current_utilization": utilization,
        "exact_negative_of_issued_displacement": exact,
        "passed": passed,
    }


def lattice_native_direction(
    modes_tsc: Sequence[Sequence[float]], direction: str, *, split_coil: int
) -> np.ndarray:
    modes = np.asarray(modes_tsc, dtype=float).reshape(N_COILS, N_MODES)
    if direction == "mode0_without_coil8":
        vector = modes[:, 0].copy()
        vector[split_coil] = 0.0
    elif direction == "mode0_coil8_component":
        vector = np.zeros(N_COILS, dtype=float)
        vector[split_coil] = float(np.sign(modes[split_coil, 0]) or 1.0)
    elif direction == "mode1":
        vector = modes[:, 1].copy()
    elif direction == "mode2":
        vector = modes[:, 2].copy()
    else:
        raise ValueError(f"unknown T13S5 lattice direction: {direction}")
    norm = float(np.linalg.norm(vector))
    if not math.isfinite(norm) or norm <= 0.0:
        raise ValueError("T13S5 lattice direction is degenerate")
    return vector / norm


def direction_lattice_config(
    *,
    center_fields: Sequence[str],
    turns_tsc: Sequence[float],
    direction: str,
    cfg: Mapping[str, Any],
) -> dict[str, Any]:
    output = copy.deepcopy(dict(cfg))
    if direction == "mode0_coil8_component":
        coil = int(cfg["split_coil_index_tsc"])
        local_step_a = (
            float(local_symmetric_card15_step(center_fields[coil]))
            * 1000.0 / float(turns_tsc[coil])
        )
        target = float(cfg["split_coil_target_current_delta_A"])
        output["minimum_significant_grid_steps"] = max(
            1, int(math.ceil(target / local_step_a - 1e-12))
        )
    return output


def exact_stored_center_action(
    *,
    stored_fields: Sequence[str],
    measured_current_a_tsc: Sequence[float],
    baseline_action_norm_tsc: Sequence[float],
    turns_tsc: Sequence[float],
    max_slew_step_a: float,
    minimum_current_a_tsc: Sequence[float],
    maximum_current_a_tsc: Sequence[float],
    cfg: Mapping[str, Any],
) -> dict[str, Any]:
    fields = tuple(map(str, stored_fields))
    exact = all(
        len(field) == 10 and format_number(float(_decimal_field(field))) == field
        for field in fields
    )
    turns = np.asarray(turns_tsc, dtype=float).reshape(N_COILS)
    current = np.asarray(measured_current_a_tsc, dtype=float).reshape(N_COILS)
    baseline = np.asarray(baseline_action_norm_tsc, dtype=float).reshape(N_COILS)
    minimum = np.asarray(minimum_current_a_tsc, dtype=float).reshape(N_COILS)
    maximum = np.asarray(maximum_current_a_tsc, dtype=float).reshape(N_COILS)
    target = np.asarray([
        float(_decimal_field(field)) * 1000.0 / turn
        for field, turn in zip(fields, turns)
    ])
    action = (target - current) / float(max_slew_step_a)
    incremental = float(np.max(np.abs(action - baseline)))
    total_abs = float(np.max(np.abs(action)))
    bounds = bool(np.all(target >= minimum) and np.all(target <= maximum))
    utilization = _current_utilization(target, minimum, maximum)
    passed = bool(
        exact
        and incremental <= float(cfg["maximum_incremental_normalized_action_linf"])
        and total_abs <= float(cfg["maximum_total_normalized_action_abs"])
        and bounds
        and utilization <= float(cfg["maximum_current_utilization"])
    )
    return {
        "target_fields": list(fields),
        "action_norm_tsc": action.tolist(),
        "incremental_normalized_action_linf": incremental,
        "total_normalized_action_abs": total_abs,
        "current_bounds_pass": bounds,
        "predicted_maximum_current_utilization": utilization,
        "exact_stored_issue_center": exact,
        "passed": passed,
    }


_WRAPPER_SPEC_KEYS = frozenset({
    "campaign_identity",
    "r3c3_probe_id",
    "r3c3_probe_window",
    "r3c3_probe_direction",
    "r3c3_probe_sign",
    "r3c3_probe_issue_step",
    "r3c3_probe_cancel_step",
    "r3c3_probe_first_effect_state",
    "r3c3_probe_cancel_effect_state",
    "r3c3t13s5_schedule_contract",
    "r3c3t13s5_offline_role",
    "r3c3t13s5_stratum",
    "r3c3t13s5_source_r3c1_experiment_id",
})


def _controller_spec(spec: Mapping[str, Any]) -> dict[str, Any]:
    output = t11._controller_spec(spec)
    forbidden = {
        "pair_id", "history_member", "common_prefix_steps", "history_order",
        "state_generation_experiment_id", "baseline_experiment_id",
        "restart_snapshot_dir", "restart_snapshot_manifest_digest",
        "r3c3t13s5_offline_role", "r3c3t13s5_stratum",
        "r3c3t13s5_source_r3c1_experiment_id",
    }
    for key in forbidden:
        output.pop(key, None)
    if forbidden.intersection(output):
        raise ValueError("T13S5 forbidden experiment label reached controller")
    return output


class LatticeTransitionProbeController(
    t11.t1.r3c1.AuthenticatedVisibleManifoldPhaseTaskController
):
    """Causal R3c1 controller followed by an exact current-step Card15 move."""

    def __init__(
        self,
        base_worker: Any,
        bundle: Mapping[str, Any],
        source_spec: Mapping[str, Any],
        initial_state: Mapping[str, Any],
        lattice_cfg: Mapping[str, Any],
    ):
        baseline_spec = copy.deepcopy(dict(source_spec))
        wrapper = {key: baseline_spec.pop(key, None) for key in _WRAPPER_SPEC_KEYS}
        super().__init__(base_worker, bundle, baseline_spec, initial_state)
        self.lattice_cfg = copy.deepcopy(dict(lattice_cfg))
        self.probe_id = str(wrapper["r3c3_probe_id"])
        self.probe_window = str(wrapper["r3c3_probe_window"])
        self.probe_direction = str(wrapper["r3c3_probe_direction"])
        self.probe_sign = int(wrapper["r3c3_probe_sign"])
        self.issue_step = int(wrapper["r3c3_probe_issue_step"])
        self.cancel_step = int(wrapper["r3c3_probe_cancel_step"])
        self.first_effect_state = int(wrapper["r3c3_probe_first_effect_state"])
        self.cancel_effect_state = int(wrapper["r3c3_probe_cancel_effect_state"])
        self._signed_issue_delta_kat: tuple[float, ...] | None = None
        self._issue_center_fields: tuple[str, ...] | None = None
        runner = self.base.env.runner
        if runner is None:
            runner = self.base.env._ensure_runner()
        self.turns_tsc = np.asarray(runner.turns_tsc, dtype=float).reshape(N_COILS)
        self.actuator = QuantizedActuatorModel(
            minimum_current_a_tsc=tuple(map(float, self.base.min_current)),
            maximum_current_a_tsc=tuple(map(float, self.base.max_current)),
            max_slew_step_a=float(self.base.max_delta_a),
            turns_tsc=tuple(map(float, self.turns_tsc)),
            bias_grid_units_tsc=tuple(
                map(float, self.lattice_cfg["readback_bias_grid_units_tsc"])
            ),
            uncertainty_radius_grid_units_tsc=tuple(
                map(float, self.lattice_cfg["readback_radius_grid_units_tsc"])
            ),
        )
        baseline = self.probe_id == BASELINE_PROBE_ID
        if baseline:
            valid = bool(
                self.probe_window == "baseline"
                and self.probe_direction == ""
                and self.probe_sign == 0
                and self.issue_step == self.cancel_step == -1
                and self.first_effect_state == self.cancel_effect_state == -1
            )
        else:
            valid = bool(
                self.probe_id == f"lattice_{self.probe_window}_{self.probe_direction}"
                and self.probe_window in WINDOWS
                and self.probe_direction in DIRECTIONS
                and self.probe_sign in SIGNS
                and self.cancel_step == self.issue_step + 1
                and self.first_effect_state == self.issue_step + self.actual_delay + 1
                and self.cancel_effect_state == self.cancel_step + self.actual_delay + 1
                and self.cancel_effect_state == self.first_effect_state + 1
            )
        if not valid:
            raise ValueError("T13S5 controller schedule contract invalid")

    def action(
        self, current_state: Mapping[str, Any]
    ) -> tuple[np.ndarray, dict[str, Any]]:
        task_step = self.step
        currents = np.asarray(
            current_state["currents_a_tsc"], dtype=float
        ).reshape(N_COILS)
        baseline_action, trace = super().action(current_state)
        baseline_action = np.asarray(baseline_action, dtype=float).reshape(N_COILS)
        center = self.actuator.apply(currents, baseline_action)
        selected_action = baseline_action.copy()
        event = "none"
        lattice: dict[str, Any] = {}
        if task_step == self.issue_step:
            event = "issue"
            mode_vector = lattice_native_direction(
                self.base.modes_tsc,
                self.probe_direction,
                split_coil=int(self.lattice_cfg["split_coil_index_tsc"]),
            )
            direction_cfg = direction_lattice_config(
                center_fields=center.card15_fields,
                turns_tsc=self.turns_tsc,
                direction=self.probe_direction,
                cfg=self.lattice_cfg,
            )
            plan = choose_lattice_displacement(
                center_fields=center.card15_fields,
                measured_current_a_tsc=currents,
                baseline_action_norm_tsc=baseline_action,
                mode_vector_tsc=mode_vector,
                turns_tsc=self.turns_tsc,
                max_slew_step_a=float(self.base.max_delta_a),
                minimum_current_a_tsc=self.base.min_current,
                maximum_current_a_tsc=self.base.max_current,
                cfg=direction_cfg,
            )
            target_key = (
                "positive_action_norm_tsc" if self.probe_sign > 0
                else "negative_action_norm_tsc"
            )
            selected_action = np.asarray(plan[target_key], dtype=float)
            base_delta = np.asarray(plan["delta_field_kAt_tsc"], dtype=float)
            signed_delta = self.probe_sign * base_delta
            self._signed_issue_delta_kat = tuple(map(float, signed_delta))
            self._issue_center_fields = tuple(map(str, center.card15_fields))
            plan["direction_lattice_config"] = direction_cfg
            lattice = plan
        elif task_step == self.cancel_step:
            event = "cancel"
            if self._signed_issue_delta_kat is None or self._issue_center_fields is None:
                raise ValueError("T13S5 cancellation has no causal issued displacement")
            returned = exact_stored_center_action(
                stored_fields=self._issue_center_fields,
                measured_current_a_tsc=currents,
                baseline_action_norm_tsc=baseline_action,
                turns_tsc=self.turns_tsc,
                max_slew_step_a=float(self.base.max_delta_a),
                minimum_current_a_tsc=self.base.min_current,
                maximum_current_a_tsc=self.base.max_current,
                cfg=self.lattice_cfg,
            )
            inverse = exact_inverse_lattice_action(
                center_fields=center.card15_fields,
                signed_issue_delta_kAt_tsc=self._signed_issue_delta_kat,
                measured_current_a_tsc=currents,
                baseline_action_norm_tsc=baseline_action,
                turns_tsc=self.turns_tsc,
                max_slew_step_a=float(self.base.max_delta_a),
                minimum_current_a_tsc=self.base.min_current,
                maximum_current_a_tsc=self.base.max_current,
                cfg=self.lattice_cfg,
            )
            if bool(returned["passed"]):
                selected_method = "exact_return_to_stored_issue_center"
                selected_cancel = returned
            elif bool(inverse["passed"]):
                selected_method = "exact_negative_relative_current_center"
                selected_cancel = inverse
            else:
                raise ValueError(
                    "T13S5 both causal cancellation candidates failed: "
                    + json.dumps({"return": returned, "inverse": inverse}, sort_keys=True)
                )
            selected_action = np.asarray(
                selected_cancel["action_norm_tsc"], dtype=float
            )
            lattice = {
                **selected_cancel,
                "selected_method": selected_method,
                "return_candidate": returned,
                "inverse_candidate": inverse,
            }
        selected = self.actuator.apply(currents, selected_action)
        if (
            any(selected.action_saturated)
            or any(selected.current_limit_clipped)
            or any(len(field) != 10 for field in selected.card15_fields)
        ):
            raise ValueError("T13S5 selected Card15 action clipped or malformed")
        if event == "issue":
            expected_fields = (
                lattice["positive_target_fields"]
                if self.probe_sign > 0 else lattice["negative_target_fields"]
            )
            if list(selected.card15_fields) != list(expected_fields):
                raise ValueError("T13S5 issued action did not reproduce target fields")
        if event == "cancel" and list(selected.card15_fields) != list(lattice["target_fields"]):
            raise ValueError("T13S5 cancellation did not reproduce target fields")
        forbidden = {
            "pair_or_history_label_used": False,
            "source_result_used": False,
            "source_action_used": False,
            "source_coil_current_used": False,
            "source_wire_current_used": False,
            "current_run_future_used": False,
            "hidden_wire_used": False,
            "future_probe_schedule_available_to_underlying_controller": False,
        }
        trace.update({
            "task_step": task_step,
            "baseline_controller_revision": t11.t1.r3c1.CONTROLLER_REVISION,
            "r3c3_identification_only": True,
            "r3c3t13s5_identification_only": True,
            "r3c3_probe_id": self.probe_id,
            "r3c3_probe_window": self.probe_window,
            "r3c3_probe_direction": self.probe_direction,
            "r3c3_probe_sign": self.probe_sign,
            "r3c3_probe_first_effect_state": self.first_effect_state,
            "r3c3_probe_cancel_effect_state": self.cancel_effect_state,
            "r3c3t13s5_lattice_event": event,
            "r3c3t13s5_probe_issued": event in {"issue", "cancel"},
            "r3c3t13s5_baseline_action_norm_tsc": baseline_action.tolist(),
            "r3c3t13s5_center_card15_fields": list(center.card15_fields),
            "r3c3t13s5_lattice": lattice,
            "r3c3t13s5_signed_issue_delta_kAt_tsc": (
                [0.0] * N_COILS
                if self._signed_issue_delta_kat is None
                else list(self._signed_issue_delta_kat)
            ),
            "r3c3t13s5_requested_net_kAt_tsc": [0.0] * N_COILS,
            "action_norm_tsc": selected_action.tolist(),
            "r3c3t13s5_actuator_prediction": selected.to_dict(),
            "mode_action_normalization_scale": 1.0,
            "mode_action_current_limit_scale": 1.0,
            "mode_action_rescaled": False,
            **forbidden,
        })
        return selected_action, trace


def _control_payload(
    ctx: Stage42R3C3T13S5Context, *, spec: Mapping[str, Any]
) -> dict[str, Any]:
    proxy = SimpleNamespace(
        source_ctx=ctx.base_ctx.base_ctx.source_ctx.source_ctx,
        cfg=ctx.base_ctx.base_ctx.cfg,
        paths=ctx.paths,
    )
    payload = t11.t1.r3c3._control_payload(proxy, spec=spec)
    horizon = int(spec["formal_horizon_steps"])
    train_cfg = copy.deepcopy(payload["train_cfg"])
    train_cfg.setdefault("episode", {})["max_episode_steps"] = horizon
    experiment_id = str(spec["experiment_id"])
    t11.t1.r3c3.atomic_write_json(
        ctx.paths.variants / f"train_{experiment_id}.json", train_cfg
    )
    payload["train_cfg"] = train_cfg
    payload["stage4_1r4_horizon_steps"] = horizon
    payload["variant_id"] = f"stage4_2r3c3t13s5_{experiment_id}"
    payload["stage4_2r3c3t13s5_restart_snapshot_dir"] = str(
        spec["restart_snapshot_dir"]
    )
    payload["stage4_2r3c3t13s5_snapshot_manifest_digest"] = str(
        spec["restart_snapshot_manifest_digest"]
    )
    t11.t1.r3c3.atomic_write_json(
        ctx.paths.variants / f"payload_{experiment_id}.json", payload
    )
    return payload


class LocalLatticeTransitionProbeWorker:
    def __init__(
        self,
        payload: dict[str, Any],
        library: dict[str, Any],
        bundle: dict[str, Any],
        worker_id: str,
        selector_cfg: dict[str, Any],
        lattice_cfg: dict[str, Any],
    ):
        self.plant = t11.t1.r1.LocalPlantReplayWorker(
            payload, library, bundle, worker_id, selector_cfg
        )
        self.base = self.plant.base_worker
        self.bundle = bundle
        self.lattice_cfg = lattice_cfg

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
                horizon != _formal_horizon(float(spec["slew_scale"]))
                or horizon != int(spec["formal_horizon_steps"])
                or horizon != int(self.base.env.max_episode_steps)
            ):
                raise ValueError("T13S5 formal horizon changed")
            self.base.env.reset()
            zero_action = np.zeros(N_COILS, dtype=np.float32)
            initial = t11.t1.r1._state_record_full(self.base.env, 0, zero_action)
            trajectory = [initial]
            controller = LatticeTransitionProbeController(
                self.base,
                self.bundle,
                _controller_spec(spec),
                initial,
                self.lattice_cfg,
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
                    raise RuntimeError("environment truncated before T13S5 horizon")
            baseline = str(spec["r3c3_probe_id"]) == BASELINE_PROBE_ID
            events = [row["r3c3t13s5_lattice_event"] for row in trace]
            expected_events = [] if baseline else ["issue", "cancel"]
            actual_events = [event for event in events if event != "none"]
            forbidden_count = sum(
                any(bool(row.get(key)) for key in (
                    "future_measurement_used", "hidden_wire_used",
                    "source_action_used", "source_coil_current_used",
                    "source_wire_current_used", "current_run_future_used",
                    "pair_or_history_label_used", "source_result_used",
                    "future_probe_schedule_available_to_underlying_controller",
                ))
                for row in trace
            )
            success = bool(
                len(trajectory) == horizon + 1
                and len(trace) == horizon
                and not any(bool(row.get("abnormal")) for row in trajectory)
                and all(bool(row.get("computed_online")) for row in trace)
                and all(bool(row.get("solver_success")) for row in trace)
                and actual_events == expected_events
                and forbidden_count == 0
            )
            result.update({
                "success": success,
                "completed": True,
                "failure_reason": "" if success else "incomplete or invalid T13S5 rollout",
                "trajectory": trajectory,
                "controller_trace": trace,
                "hidden_history_control_summary": {
                    "fresh_controller_actor": True,
                    "fresh_tsc_process": True,
                    "full_tsc_hidden_state_loaded_from_sprsina": True,
                    "controller_history_initialization": "current_visible_state_only_at_task_step_zero",
                    "controller_integral_initialization": "zero",
                    "controller_previous_correction_initialization": "zero",
                    "controller_delay_queue_initialization": "authenticated_visible_manifold_phase_aligned_nominal_prime",
                    "reference_phase_start": controller.reference_phase_start,
                    "baseline_controller_revision": t11.t1.r3c1.CONTROLLER_REVISION,
                    "identification_only": True,
                    "extended_baseline": baseline,
                    "probe_id": controller.probe_id,
                    "probe_window": controller.probe_window,
                    "probe_sign": controller.probe_sign,
                    "probe_first_effect_state": controller.first_effect_state,
                    "probe_cancel_effect_state": controller.cancel_effect_state,
                    "scheduled_probe_exact": actual_events == expected_events,
                    "requested_and_applied_zero_net": True,
                    "observation_horizon_steps": horizon,
                    "formal_horizon_steps": horizon,
                    "probe_trajectory_allowed_in_expert_dataset": False,
                    "phase_selection": copy.deepcopy(controller.phase_selection),
                    "visible_reference_manifold_digest": controller.visible_reference_manifold_digest,
                    "visible_reference_source_experiment_id": controller.visible_reference_source_experiment_id,
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
            })
            failed = not success
            return t11.t1._json_safe(result)
        except Exception as exc:
            result.update({
                "success": False,
                "completed": True,
                "failure_reason": repr(exc),
                "traceback": traceback.format_exc(),
                "wall_time_s": time.time() - started,
            })
            return t11.t1._json_safe(result)
        finally:
            runner = getattr(self.base.env, "runner", None)
            if runner is not None:
                runner.cleanup_episode_workspace(
                    failed=failed,
                    reason="stage4_2r3c3t13s5_lattice_native_split_holdout",
                )


_CONTROL_RAY_ACTOR = None


def _control_ray_actor_class():
    global _CONTROL_RAY_ACTOR
    if _CONTROL_RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class Stage42R3C3T13S5ControlActor:
            def __init__(
                self, payload, library, bundle, worker_id, selector_cfg, lattice_cfg
            ):
                self.worker = LocalLatticeTransitionProbeWorker(
                    payload, library, bundle, worker_id, selector_cfg, lattice_cfg
                )

            def evaluate(self, spec):
                return self.worker.evaluate(spec)

            def close(self):
                self.worker.close()
                return True

        _CONTROL_RAY_ACTOR = Stage42R3C3T13S5ControlActor
    return _CONTROL_RAY_ACTOR


def _package_files(ctx: Stage42R3C3T13S5Context) -> list[Path]:
    project = _project_root()
    manifest = t11.t1.r3c3.read_json(project / "PACKAGE_MANIFEST.json")
    paths = [project / str(relative) for relative in manifest["file_inventory"]]
    required = {
        project / "configs/stage4_2r3c3t13s5_lattice_native_split_holdout_370ms.json",
        project / "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s5_lattice_native_split_holdout.py",
        project / "scripts/stage4_2r3c3t13s5_lattice_native_split_holdout.py",
        project / "scripts/stage4_2r3c3t13s5_server_postprocess.py",
        project / "scripts/stage4_2r3c3t13s5_shell_common.sh",
        project / "run_stage4_2r3c3t13s5_common.sh",
        project / "run_stage4_2r3c3t13s5_offline.sh",
        project / "run_stage4_2r3c3t13s5_native.sh",
        project / "run_stage4_2r3c3t13s5_nohup.sh",
        project / "run_stage4_2r3c3t13s5_self_test.sh",
        project / "run_stage4_2r3c3t13s5_server_postprocess.sh",
        project / "run_stage4_2r3c3t13s5_verify_package.sh",
        project / "run_stop_stage4_2r3c3t13s5_now.sh",
    }
    if not required <= set(paths):
        missing = sorted(str(path.relative_to(project)) for path in required - set(paths))
        raise ValueError(f"T13S5 package inventory missing files: {missing}")
    return paths


def _deployed_package_fingerprint(
    ctx: Stage42R3C3T13S5Context,
) -> dict[str, Any]:
    project = _project_root()
    rows = []
    for path in _package_files(ctx):
        if not path.is_file():
            raise FileNotFoundError(f"package file missing: {path}")
        rows.append({
            "path": path.relative_to(project).as_posix(),
            "size_bytes": int(path.stat().st_size),
            "sha256": _sha256(path),
        })
    rows.sort(key=lambda row: row["path"])
    return {
        "contract": "r42r3c3t13s5_deployed_package_source_v1",
        "package_revision": PACKAGE_REVISION,
        "file_count": len(rows),
        "total_bytes": sum(int(row["size_bytes"]) for row in rows),
        "digest": _canonical_digest(rows),
        "files": rows,
    }


def _prepare_dirs(paths: Stage42R3C3T13S5Paths) -> None:
    for path in (
        paths.run_dir, paths.control, paths.raw, paths.variants,
        paths.source_reference, paths.model, paths.analysis,
    ):
        path.mkdir(parents=True, exist_ok=True)


def _resume_compatible(
    old: Mapping[str, Any],
    new: Mapping[str, Any],
    *,
    allow_reporting_hotfix: bool = False,
) -> None:
    if old == new:
        return
    old_by_path = {row["path"]: row for row in old.get("files", [])}
    new_by_path = {row["path"]: row for row in new.get("files", [])}
    changed = sorted(
        path for path in set(old_by_path) | set(new_by_path)
        if old_by_path.get(path) != new_by_path.get(path)
    )
    if (
        allow_reporting_hotfix
        and old.get("package_revision") == EXECUTION_PACKAGE_REVISION
        and new.get("package_revision") == PACKAGE_REVISION
        and changed
        and set(changed) <= REPORTING_HOTFIX_PATHS
    ):
        return
    raise ValueError(
        "T13S5 automatic resume requires exact package identity; changed="
        + repr(changed)
    )


def _reporting_hotfix_config_compatible(
    old: Mapping[str, Any], new: Mapping[str, Any]
) -> bool:
    old_copy = copy.deepcopy(dict(old))
    new_copy = copy.deepcopy(dict(new))
    if (
        old_copy.get("package_revision") != EXECUTION_PACKAGE_REVISION
        or new_copy.get("package_revision") != PACKAGE_REVISION
    ):
        return False
    old_copy["package_revision"] = PACKAGE_REVISION
    return old_copy == new_copy


def prepare(
    ctx: Stage42R3C3T13S5Context, *, resume: bool
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    _prepare_dirs(ctx.paths)
    selected_pairs = _selected_pairs(ctx)
    specs = build_control_specs(ctx, selected_pairs)
    package = _deployed_package_fingerprint(ctx)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "controller_revision": CONTROLLER_REVISION,
        "underlying_controller_revision": t11.t1.r3c1.CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "source_stage4_2r3c3t11_config": str(ctx.base_config_path),
        "source_stage4_2r3c3t11_config_sha256": _sha256(ctx.base_config_path),
        "source_stage4_2r3c3t1_run": str(ctx.base_ctx.base_ctx.source_t1_run),
        "source_stage4_2r3c3t1_audit_dir": str(ctx.base_ctx.base_ctx.source_t1_audit_dir),
        "source_stage4_2r3c3t1_fingerprint": ctx.base_ctx.base_ctx.source_t1_fingerprint,
        "source_stage4_2r3c3_run": str(ctx.base_ctx.base_ctx.source_ctx.source_r3c3_run),
        "source_stage4_2r3c3_bank_dir": str(ctx.base_ctx.base_ctx.source_ctx.source_bank_dir),
        "source_stage4_2r3b_run": str(ctx.base_ctx.base_ctx.source_ctx.source_r3b_run),
        "source_stage4_2r3c1_run": str(ctx.base_ctx.base_ctx.source_ctx.source_r3c1_run),
        "source_stage4_2r3c3t3_controller_bank": str(ctx.base_ctx.t3_controller_bank_path),
        "source_stage4_2r3c3t3_controller_bank_sha256": _sha256(ctx.base_ctx.t3_controller_bank_path),
        "deployed_package_fingerprint": package,
        "config_digest": _canonical_digest(ctx.cfg),
        "control_spec_digest": _canonical_digest(specs),
        "lattice_probe": copy.deepcopy(ctx.cfg["lattice_probe"]),
        "formal_timing_contract": copy.deepcopy(ctx.cfg["formal_timing_contract"]),
        "control_matrix": copy.deepcopy(ctx.cfg["control_matrix"]),
        "identification_only": True,
        "blind_holdout_required": True,
        "independent_new_history_confirmation": False,
        "independent_long_hold_validated": False,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "bc_dagger_or_rl_allowed": False,
    }
    if ctx.paths.manifest.is_file():
        if not resume:
            raise FileExistsError("T13S5 run exists; use resume or a fresh run")
        old = t11.t1.r3c3.read_json(ctx.paths.manifest)
        old_resolved_path = (
            ctx.paths.run_dir / "stage4_2r3c3t13s5_config.resolved.json"
        )
        reporting_hotfix = bool(
            old.get("package_revision") == EXECUTION_PACKAGE_REVISION
            and old_resolved_path.is_file()
            and _reporting_hotfix_config_compatible(
                t11.t1.r3c3.read_json(old_resolved_path), ctx.cfg
            )
        )
        for key, value in manifest.items():
            if key == "deployed_package_fingerprint":
                continue
            if reporting_hotfix and key in {"package_revision", "config_digest"}:
                continue
            if old.get(key) != value:
                raise ValueError(f"T13S5 resume incompatibility in {key}")
        _resume_compatible(
            dict(old.get("deployed_package_fingerprint") or {}),
            package,
            allow_reporting_hotfix=reporting_hotfix,
        )
    else:
        reporting_hotfix = False
        t11.t1.r3c3.atomic_write_json(ctx.paths.manifest, manifest)
    resolved_name = (
        "stage4_2r3c3t13s5_config.resolved.v1h1.json"
        if reporting_hotfix
        else "stage4_2r3c3t13s5_config.resolved.json"
    )
    t11.t1.r3c3.atomic_write_json(ctx.paths.run_dir / resolved_name, ctx.cfg)
    t11.t1.r3c3.atomic_write_json(
        ctx.paths.source_reference / "control_specs.json", specs
    )
    fingerprint_name = (
        "deployed_package_fingerprint.v1h1.json"
        if reporting_hotfix else "deployed_package_fingerprint.json"
    )
    t11.t1.r3c3.atomic_write_json(
        ctx.paths.source_reference / fingerprint_name, package
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
    if reporting_hotfix:
        state["execution_package_revision"] = EXECUTION_PACKAGE_REVISION
        state["reporting_package_revision"] = PACKAGE_REVISION
        state["semantics_preserving_reporting_resume"] = True
    state["updated_utc"] = t11.t1.r3c3.utc_timestamp()
    t11.t1.r3c3.atomic_write_json(ctx.paths.state, state)
    return selected_pairs, specs


def run_offline_lattice_audit(
    ctx: Stage42R3C3T13S5Context,
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
        / "stage4_2r3c1_authenticated_visible_manifold_control" / "raw"
    )
    pass_count = 0
    event_count = 0
    hidden_invariant_count = 0
    lattice_design_failures: list[dict[str, Any]] = []
    context_source: dict[tuple[Any, ...], Mapping[str, Any]] = {}
    for spec in specs:
        key = _context_key(spec)
        if key not in context_source:
            context_source[key] = t11.t1.r3c3.read_json_gz(
                baseline_dir / f"{spec['baseline_experiment_id']}.json.gz"
            )
        source = context_source[key]
        trajectory = list(source["trajectory"])
        initial = copy.deepcopy(dict(trajectory[0]))
        initial["step_index"] = 0
        payload = _control_payload(ctx, spec=spec)
        worker = t11.t1.r1.LocalPlantReplayWorker(
            payload, library, bundle,
            f"stage42r3c3t13s5_offline_{len(context_source):03d}", selector,
        )
        try:
            controller = LatticeTransitionProbeController(
                worker.base_worker, bundle, _controller_spec(spec), initial,
                ctx.cfg["lattice_probe"],
            )
            finite = True
            events = []
            for step in range(int(spec["horizon_steps"])):
                state = copy.deepcopy(dict(trajectory[step]))
                state["step_index"] = step
                action, trace = controller.action(state)
                finite = bool(
                    finite
                    and np.all(np.isfinite(action))
                    and len(trace["r3c3t13s5_actuator_prediction"]["card15_fields"])
                    == N_COILS
                    and all(
                        len(field) == 10
                        for field in trace["r3c3t13s5_actuator_prediction"]["card15_fields"]
                    )
                    and int(trace["measurement_max_state_index_used"]) == step
                    and not any(bool(trace.get(key)) for key in (
                        "future_measurement_used", "hidden_wire_used",
                        "source_action_used", "source_result_used",
                        "pair_or_history_label_used", "current_run_future_used",
                    ))
                )
                if trace["r3c3t13s5_lattice_event"] != "none":
                    events.append(trace["r3c3t13s5_lattice_event"])
                if step + 1 < len(trajectory):
                    next_state = copy.deepcopy(dict(trajectory[step + 1]))
                    next_state["step_index"] = step + 1
                    controller.advance(next_state)
            baseline = str(spec["r3c3_probe_id"]) == BASELINE_PROBE_ID
            exact_events = events == ([] if baseline else ["issue", "cancel"])
            passed = bool(finite and exact_events)
            pass_count += passed
            event_count += len(events)
            hidden = copy.deepcopy(initial)
            hidden["wire_currents_a"] = [float(i + 1) * 1e9 for i in range(s1.N_WIRES)]
            a = LatticeTransitionProbeController(
                worker.base_worker, bundle, _controller_spec(spec), initial,
                ctx.cfg["lattice_probe"],
            ).action(initial)[0]
            b = LatticeTransitionProbeController(
                worker.base_worker, bundle, _controller_spec(spec), hidden,
                ctx.cfg["lattice_probe"],
            ).action(hidden)[0]
            hidden_invariant_count += np.array_equal(a, b)
        except ValueError as exc:
            message = str(exc)
            issue_prefix = "no frozen T13S5 lattice multiplier passed: "
            cancel_prefix = "T13S5 both causal cancellation candidates failed: "
            if message.startswith(issue_prefix):
                failure_phase = "issue"
                candidates = json.loads(message[len(issue_prefix):])
                metrics = [
                    {
                        key: candidate[key]
                        for key in (
                            "lambda_multiplier",
                            "lambda_A",
                            "minimum_significant_grid_steps_actual",
                            "target_field_central_symmetry_exact",
                            "coil_space_cosine",
                            "relative_off_mode_residual",
                            "incremental_normalized_action_linf",
                            "total_normalized_action_abs",
                            "current_bounds_pass",
                            "predicted_maximum_current_utilization",
                            "passed",
                        )
                    }
                    for candidate in candidates
                ]
            elif message.startswith(cancel_prefix):
                failure_phase = "cancel"
                candidates = json.loads(message[len(cancel_prefix):])
                metrics = candidates
            else:
                raise
            lattice_design_failures.append({
                "experiment_id": str(spec["experiment_id"]),
                "offline_role": str(spec["r3c3t13s5_offline_role"]),
                "stratum": str(spec["r3c3t13s5_stratum"]),
                "pair_id": str(spec["pair_id"]),
                "history_member": str(spec["history_member"]),
                "target_id": str(spec["target_id"]),
                "action_delay_steps": int(spec["action_delay_steps"]),
                "slew_scale": float(spec["slew_scale"]),
                "probe_window": str(spec["r3c3_probe_window"]),
                "probe_direction": str(spec["r3c3_probe_direction"]),
                "probe_sign": int(spec["r3c3_probe_sign"]),
                "failure_phase": failure_phase,
                "candidate_metrics": metrics,
            })
        finally:
            worker.close()
    expected = int(ctx.cfg["control_matrix"]["expected_rollouts"])
    raw_count = len(list(ctx.paths.raw.glob("*.json.gz")))
    raw_gate = 0 <= raw_count <= expected if allow_existing_raw else raw_count == 0
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "phase": "offline_dynamic_lattice_preflight",
        "expected_specs": expected,
        "spec_count": len(specs),
        "development_spec_count": sum(
            spec["r3c3t13s5_offline_role"] == "development" for spec in specs
        ),
        "blind_holdout_spec_count": sum(
            spec["r3c3t13s5_offline_role"] == "blind_holdout" for spec in specs
        ),
        "dynamic_lattice_preflight_pass_count": pass_count,
        "expected_lattice_event_count": 128,
        "lattice_event_count": event_count,
        "hidden_wire_invariant_action_count": hidden_invariant_count,
        "lattice_design_failure_count": len(lattice_design_failures),
        "lattice_design_failures": lattice_design_failures,
        "expected_current_components": EXPECTED_CURRENT_COMPONENTS,
        "raw_count": raw_count,
        "allow_existing_raw": allow_existing_raw,
        "raw_directory_gate_passed": raw_gate,
        "plant_advance_count": 0,
        "real_tsc_executed": False,
    }
    summary["passed"] = bool(
        len(specs) == expected == pass_count == hidden_invariant_count
        and summary["development_spec_count"] == 34
        and summary["blind_holdout_spec_count"] == 34
        and event_count == 128
        and raw_gate
    )
    summary["route"] = (
        "LATTICE_PREFLIGHT_PASS_REAL_TSC_NOT_STARTED"
        if summary["passed"]
        else "LATTICE_PREFLIGHT_FAIL_NO_REAL_TSC"
    )
    t11.t1.r3c3.atomic_write_json(
        ctx.paths.source_reference / "offline_dynamic_lattice_audit.json", summary
    )
    return summary


def _result_complete(path: Path, expected_spec: Mapping[str, Any]) -> bool:
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
    ctx: Stage42R3C3T13S5Context,
    specs: Sequence[dict[str, Any]],
    *,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    ctx.paths.raw.mkdir(parents=True, exist_ok=True)
    library, bundle, selector = t11.t1.r1._library_bundle_selector(
        ctx.base_ctx.base_ctx.source_ctx.source_ctx.r1_ctx
    )
    pending = [
        spec for spec in specs
        if not (resume and _result_complete(
            ctx.paths.raw / f"{spec['experiment_id']}.json.gz", spec
        ))
    ]
    payloads = {
        str(spec["experiment_id"]): _control_payload(ctx, spec=spec)
        for spec in specs
    }
    if backend == "serial":
        for index, spec in enumerate(pending):
            worker = LocalLatticeTransitionProbeWorker(
                payloads[str(spec["experiment_id"])], library, bundle,
                f"stage42r3c3t13s5_serial_{index:03d}", selector,
                ctx.cfg["lattice_probe"],
            )
            try:
                result = worker.evaluate(spec)
            finally:
                worker.close()
            t11.t1.r3c3.atomic_write_json_gz(
                ctx.paths.raw / f"{spec['experiment_id']}.json.gz", result
            )
            print(f"[T13S5] {index + 1}/{len(pending)}", flush=True)
    elif backend == "ray" and pending:
        import ray

        plan = ensure_ray_worker_plan(
            ray,
            requested_workers=int(ctx.cfg["parallel"]["n_workers"]),
            pending_tasks=len(pending),
            ray_tmpdir=os.environ.get("RAY_TMPDIR") or ctx.cfg["storage"].get("ray_tmpdir"),
            log_prefix="[T13S5]",
        )
        Actor = _control_ray_actor_class()
        completed = 0
        print(
            f"[T13S5] maximum_actor_count={plan.actor_count} pending={len(pending)}",
            flush=True,
        )
        for batch_start in range(0, len(pending), plan.actor_count):
            batch = pending[batch_start: batch_start + plan.actor_count]
            actors = []
            refs = {}
            for offset, spec in enumerate(batch):
                index = batch_start + offset
                actor = Actor.remote(
                    payloads[str(spec["experiment_id"])], library, bundle,
                    f"stage42r3c3t13s5_{index:03d}", selector,
                    ctx.cfg["lattice_probe"],
                )
                actors.append(actor)
                refs[actor.evaluate.remote(spec)] = spec
            try:
                while refs:
                    ready, _ = ray.wait(list(refs), num_returns=1, timeout=30.0)
                    if not ready:
                        print(f"[T13S5] waiting {completed}/{len(pending)}", flush=True)
                        continue
                    for ref in ready:
                        spec = refs.pop(ref)
                        try:
                            result = ray.get(ref)
                        except Exception as exc:
                            result = _structured_actor_failure(spec, exc)
                        t11.t1.r3c3.atomic_write_json_gz(
                            ctx.paths.raw / f"{spec['experiment_id']}.json.gz", result
                        )
                        completed += 1
                        if completed % 4 == 0 or not refs:
                            print(f"[T13S5] {completed}/{len(pending)}", flush=True)
            finally:
                t11.t1.r3b.s2._close_ray_actors(
                    actors,
                    timeout_s=float(ctx.cfg["storage"].get("actor_close_timeout_s", 1800.0)),
                )
    elif backend not in {"serial", "ray"}:
        raise ValueError("backend must be serial or ray")
    completed_count = sum(
        _result_complete(ctx.paths.raw / f"{spec['experiment_id']}.json.gz", spec)
        for spec in specs
    )
    return {
        "expected": len(specs),
        "pending_before_run": len(pending),
        "complete_after_run": completed_count,
        "raw_paths": [
            str(ctx.paths.raw / f"{spec['experiment_id']}.json.gz")
            for spec in specs
        ],
    }


def _feature_arrays(result: Mapping[str, Any], dt_s: float) -> np.ndarray:
    return s1._feature_arrays(result, dt_s)


def _effect_response(
    result: Mapping[str, Any],
    baseline: Mapping[str, Any],
    modes: np.ndarray,
    dt_s: float,
    radius_a: np.ndarray,
) -> dict[str, Any]:
    spec = result["spec"]
    first = int(spec["r3c3_probe_first_effect_state"])
    cancel = int(spec["r3c3_probe_cancel_effect_state"])
    if cancel != first + 1:
        raise ValueError("T13S5 effect states are not adjacent")
    feature = _feature_arrays(result, dt_s)
    base_feature = _feature_arrays(baseline, dt_s)
    response = np.concatenate(
        (feature[first] - base_feature[first], feature[cancel] - base_feature[cancel])
    )
    current = np.asarray(
        [row["currents_a_tsc"] for row in result["trajectory"]], dtype=float
    )
    base_current = np.asarray(
        [row["currents_a_tsc"] for row in baseline["trajectory"]], dtype=float
    )
    displacement = current[[first, cancel]] - base_current[[first, cancel]]
    modal = displacement @ modes
    pre = feature[:first] - base_feature[:first]
    pre_current = current[:first] - base_current[:first]
    if len(pre):
        pre_position = float(np.max(np.abs(pre[:, :2])))
        pre_velocity = float(np.max(np.abs(pre[:, 2:4])))
        pre_ip = float(np.max(np.abs(pre[:, 4])))
        pre_coil = float(np.max(np.abs(pre_current) / radius_a[None, :]))
    else:
        pre_position = pre_velocity = pre_ip = pre_coil = 0.0
    return {
        "first_effect_state": first,
        "cancel_effect_state": cancel,
        "response_unscaled": response,
        "input_measured_current_A": displacement.reshape(-1),
        "off_mode_current_A": (
            displacement - (displacement @ modes) @ modes.T
        ).reshape(-1),
        "first_effect_current_displacement_A": displacement[0],
        "maximum_pre_effect_position_m": pre_position,
        "maximum_pre_effect_velocity_m_per_s": pre_velocity,
        "maximum_pre_effect_ip_A": pre_ip,
        "maximum_pre_effect_coil_radius_units": pre_coil,
    }


def _issue_trace(result: Mapping[str, Any]) -> Mapping[str, Any]:
    rows = [
        row for row in result["controller_trace"]
        if row.get("r3c3t13s5_lattice_event") == "issue"
    ]
    if len(rows) != 1:
        raise ValueError("T13S5 signed result must contain one issue trace")
    return rows[0]


def _cancellation_policy_trace(
    result: Mapping[str, Any], *, baseline: bool
) -> dict[str, Any]:
    rows = [
        row for row in result.get("controller_trace", [])
        if row.get("r3c3t13s5_lattice_event") == "cancel"
    ]
    if baseline:
        return {
            "cancellation_method": "",
            "cancellation_policy_pass": len(rows) == 0,
        }
    if len(rows) != 1:
        return {
            "cancellation_method": "",
            "cancellation_policy_pass": False,
        }
    row = rows[0]
    lattice = row.get("r3c3t13s5_lattice") or {}
    returned = lattice.get("return_candidate") or {}
    inverse = lattice.get("inverse_candidate") or {}
    method = str(lattice.get("selected_method") or "")
    if bool(returned.get("passed")):
        expected = "exact_return_to_stored_issue_center"
        selected = returned
    elif bool(inverse.get("passed")):
        expected = "exact_negative_relative_current_center"
        selected = inverse
    else:
        expected = ""
        selected = {}
    actuator = row.get("r3c3t13s5_actuator_prediction") or {}
    return {
        "cancellation_method": method,
        "cancellation_policy_pass": bool(
            expected
            and method == expected
            and list(selected.get("target_fields") or [])
            == list(actuator.get("card15_fields") or [])
        ),
    }


def _actuator_execution(
    result: Mapping[str, Any], cfg: Mapping[str, Any]
) -> dict[str, Any]:
    if not bool(result.get("success")):
        return {
            "component_count": 0,
            "inside_interval_count": 0,
            "card15_field_count": 0,
            "card15_length_exact_count": 0,
            "clip_or_rescale_count": 0,
            "passed": False,
        }
    trace = list(result["controller_trace"])
    trajectory = list(result["trajectory"])
    inside = 0
    fields = 0
    length_exact = 0
    clip_count = 0
    maximum_interval_excess = 0.0
    for step, row in enumerate(trace):
        actuator = row["r3c3t13s5_actuator_prediction"]
        observed = np.asarray(trajectory[step + 1]["currents_a_tsc"], dtype=float)
        lower = np.asarray(actuator["readback_lower_a_tsc"], dtype=float)
        upper = np.asarray(actuator["readback_upper_a_tsc"], dtype=float)
        inside_mask = (observed >= lower - 1e-12) & (observed <= upper + 1e-12)
        inside += int(np.sum(inside_mask))
        maximum_interval_excess = max(
            maximum_interval_excess,
            float(np.max(np.maximum(lower - observed, observed - upper))),
        )
        card = list(actuator["card15_fields"])
        fields += len(card)
        length_exact += sum(len(field) == 10 for field in card)
        clip_count += sum(bool(value) for value in actuator["action_saturated"])
        clip_count += sum(bool(value) for value in actuator["current_limit_clipped"])
        clip_count += bool(row.get("mode_action_rescaled"))
    components = len(trace) * N_COILS
    return {
        "component_count": components,
        "inside_interval_count": inside,
        "card15_field_count": fields,
        "card15_length_exact_count": length_exact,
        "clip_or_rescale_count": clip_count,
        "maximum_interval_excess_A": max(0.0, maximum_interval_excess),
        "passed": bool(
            inside == fields == length_exact == components and clip_count == 0
        ),
    }


def _expected_context_row(
    cfg: Mapping[str, Any], key: tuple[Any, ...]
) -> Mapping[str, Any]:
    rows = [
        row for row in cfg["holdout_contexts"]
        if _frozen_context_key(row) == key
    ]
    if len(rows) != 1:
        raise ValueError("T13S5 frozen context lookup mismatch")
    return rows[0]


def _execution_rows(
    ctx: Stage42R3C3T13S5Context,
    results: Sequence[Mapping[str, Any]],
    selected_pairs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    state_map = t11.t1.r3b._selected_state_map(selected_pairs)
    base_source_ctx = ctx.base_ctx.base_ctx.source_ctx.source_ctx
    rows = []
    for result in results:
        spec = result["spec"]
        baseline = str(spec["r3c3_probe_id"]) == BASELINE_PROBE_ID
        state_id = str(spec["state_generation_experiment_id"])
        base = t11.t1.r3b._control_row(
            base_source_ctx, result, state_map[state_id]
        )
        phase = t11.t1.r3c1._phase_trace_valid(result)
        formal = (
            t11._formal_prefix_metrics(ctx.base_ctx, result)
            if bool(result.get("success")) else {}
        )
        prefix_exact = bool(
            baseline and result.get("success")
            and t11._source_prefix_exact(ctx.base_ctx, result)
        )
        expected = _expected_context_row(ctx.cfg, _context_key(spec))
        margin = (
            float(formal["stage3_4_tracking_minimum_signed_margin"])
            if formal else None
        )
        baseline_formal = bool(
            baseline and formal
            and bool(formal["stage3_4_target_tracking_pass"])
            == bool(expected["expected_formal_pass"])
            and margin is not None
            and abs(margin - float(expected["expected_formal_minimum_signed_margin"]))
            <= float(ctx.cfg["lattice_probe"]["baseline_margin_reproduction_atol"])
        )
        actuator = _actuator_execution(result, ctx.cfg["lattice_probe"])
        trace = list(result.get("controller_trace") or [])
        forbidden_count = sum(
            any(bool(row.get(key)) for key in (
                "pair_or_history_label_used", "source_result_used",
                "source_action_used", "source_coil_current_used",
                "source_wire_current_used", "current_run_future_used",
                "future_measurement_used", "hidden_wire_used",
                "future_probe_schedule_available_to_underlying_controller",
            )) for row in trace
        )
        expected_events = [] if baseline else ["issue", "cancel"]
        actual_events = [
            row.get("r3c3t13s5_lattice_event") for row in trace
            if row.get("r3c3t13s5_lattice_event") != "none"
        ]
        cancellation = _cancellation_policy_trace(result, baseline=baseline)
        trace_pass = bool(
            len(trace) == int(spec["formal_horizon_steps"])
            and actual_events == expected_events
            and forbidden_count == 0
            and all(bool(row.get("solver_success")) for row in trace)
            and bool(cancellation["cancellation_policy_pass"])
        )
        execution = bool(
            result.get("success") and base["fresh_controller"]
            and base["fresh_tsc_process"] and base["initial_restart_exact"]
            and base["controller_trace_causal"] and phase["passed"]
            and trace_pass and actuator["passed"]
            and (not baseline or (prefix_exact and baseline_formal))
        )
        if not bool(result.get("success")):
            failure_class = "runtime_or_environment_error"
        elif not bool(base["initial_restart_exact"]):
            failure_class = "plant_restart_fidelity_failure"
        elif not bool(base["controller_trace_causal"]):
            failure_class = "controller_causality_failure"
        elif not trace_pass or not bool(phase["passed"]):
            failure_class = "lattice_probe_execution_failure"
        elif not actuator["passed"]:
            failure_class = "actuator_interval_or_serialization_failure"
        elif baseline and not prefix_exact:
            failure_class = "baseline_prefix_mismatch"
        elif baseline and not baseline_formal:
            failure_class = "baseline_formal_reproduction_mismatch"
        else:
            failure_class = ""
        rows.append({
            **base,
            "probe_id": str(spec["r3c3_probe_id"]),
            "probe_window": str(spec["r3c3_probe_window"]),
            "probe_direction": str(spec["r3c3_probe_direction"]),
            "probe_sign": int(spec["r3c3_probe_sign"]),
            "offline_role": str(spec["r3c3t13s5_offline_role"]),
            "stratum": str(spec["r3c3t13s5_stratum"]),
            "extended_baseline": baseline,
            "extended_baseline_prefix_exact": prefix_exact,
            "baseline_formal_reproduced": baseline_formal,
            "formal_contract_pass": bool(formal.get("stage3_4_target_tracking_pass", False)),
            "formal_minimum_signed_margin": margin,
            "phase_trace_valid": bool(phase["passed"]),
            "lattice_trace_valid": trace_pass,
            "cancellation_method": cancellation["cancellation_method"],
            "cancellation_policy_pass": cancellation["cancellation_policy_pass"],
            "forbidden_trace_count": forbidden_count,
            "actuator_component_count": actuator["component_count"],
            "actuator_inside_interval_count": actuator["inside_interval_count"],
            "card15_field_count": actuator["card15_field_count"],
            "card15_length_exact_count": actuator["card15_length_exact_count"],
            "clip_or_rescale_count": actuator["clip_or_rescale_count"],
            "maximum_actuator_interval_excess_A": actuator.get("maximum_interval_excess_A"),
            "actuator_execution_pass": actuator["passed"],
            "max_current_utilization": (
                t11._full_current_utilization(ctx.base_ctx, result)
                if bool(result.get("success")) else None
            ),
            "execution_pass": execution,
            "failure_class": failure_class,
            "passed": execution,
            "identification_only": True,
            "probe_trajectory_allowed_in_expert_dataset": False,
        })
    return rows


def _group_results(
    results: Sequence[Mapping[str, Any]],
) -> dict[tuple[Any, ...], dict[str, Mapping[str, Any]]]:
    grouped: dict[tuple[Any, ...], dict[str, Mapping[str, Any]]] = {}
    for result in results:
        spec = result["spec"]
        name = (
            BASELINE_PROBE_ID
            if str(spec["r3c3_probe_id"]) == BASELINE_PROBE_ID
            else f"{spec['r3c3_probe_window']}:{spec['r3c3_probe_direction']}:{spec['r3c3_probe_sign']}"
        )
        members = grouped.setdefault(_context_key(spec), {})
        if name in members:
            raise ValueError("duplicate T13S5 context member")
        members[name] = result
    return grouped


def _signed_group_rows(
    ctx: Stage42R3C3T13S5Context,
    results: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    grouped = _group_results(results)
    modes, _, dt_s = s1._stage34_identity(ctx)
    turns = None
    probe_cfg = ctx.cfg["lattice_probe"]
    scales = np.asarray(probe_cfg["response_scales"], dtype=float)
    floor_one = np.asarray([1e-9, 1e-9, 1e-7, 1e-7, 1e-4], dtype=float)
    floor_scaled = float(np.linalg.norm(np.tile(floor_one / scales, 2)))
    rows = []
    for context_key, members in sorted(grouped.items()):
        if BASELINE_PROBE_ID not in members:
            raise ValueError("T13S5 context baseline missing")
        baseline = members[BASELINE_PROBE_ID]
        if turns is None:
            payload = t11.t1.r3c3.read_json(
                ctx.paths.variants / f"payload_{baseline['experiment_id']}.json"
            )
            from tsc_rzip_rllib.core.coil_order import display_to_tsc
            turns = np.asarray(
                display_to_tsc(payload["env_cfg"]["turns_display_order"]), dtype=float
            )
        radius_a = OUTPUT_GRID_KAT * 1000.0 / turns
        for window in WINDOWS:
            for direction in DIRECTIONS:
                signed = {
                    sign: members.get(f"{window}:{direction}:{sign}") for sign in SIGNS
                }
                row: dict[str, Any] = {
                    "pair_id": context_key[0],
                    "history_member": context_key[1],
                    "target_id": context_key[2],
                    "actual_delay_steps": context_key[3],
                    "actual_slew_scale": context_key[4],
                    "offline_role": str(baseline["spec"]["r3c3t13s5_offline_role"]),
                    "stratum": str(baseline["spec"]["r3c3t13s5_stratum"]),
                    "probe_window": window,
                    "probe_direction": direction,
                    "signed_member_count": sum(value is not None for value in signed.values()),
                    "response_available": False,
                    "target_field_central_symmetry_exact": False,
                    "observed_current_signal_pass": False,
                    "observed_current_symmetry_pass": False,
                    "pre_effect_causality_pass": False,
                    "development_signal_pass": False,
                }
                if (
                    all(value is not None and bool(value.get("success")) for value in signed.values())
                    and bool(baseline.get("success"))
                ):
                    response = {
                        sign: _effect_response(value, baseline, modes, dt_s, radius_a)
                        for sign, value in signed.items()
                    }
                    plus_issue = _issue_trace(signed[1])
                    minus_issue = _issue_trace(signed[-1])
                    plus_fields = plus_issue["r3c3t13s5_actuator_prediction"]["card15_fields"]
                    minus_fields = minus_issue["r3c3t13s5_actuator_prediction"]["card15_fields"]
                    plus_center = plus_issue["r3c3t13s5_center_card15_fields"]
                    minus_center = minus_issue["r3c3t13s5_center_card15_fields"]
                    target_symmetry = bool(
                        plus_center == minus_center
                        and all(
                            _decimal_field(p) - _decimal_field(c)
                            == _decimal_field(c) - _decimal_field(m)
                            for p, c, m in zip(plus_fields, plus_center, minus_fields)
                        )
                    )
                    first_plus = response[1]["first_effect_current_displacement_A"]
                    first_minus = response[-1]["first_effect_current_displacement_A"]
                    odd_current = (first_plus - first_minus) / 2.0
                    even_current = (first_plus + first_minus) / 2.0
                    odd_norm = float(np.linalg.norm(odd_current))
                    even_norm = float(np.linalg.norm(even_current))
                    signal = bool(
                        odd_norm >= float(probe_cfg["required_observed_odd_signal_radius_l2"])
                        * float(np.linalg.norm(radius_a))
                    )
                    ratio = even_norm / max(odd_norm, 1e-300)
                    current_symmetry = bool(
                        target_symmetry and signal
                        and ratio <= float(probe_cfg["maximum_observed_even_to_odd_l2"])
                    )
                    pre_position = max(
                        response[sign]["maximum_pre_effect_position_m"] for sign in SIGNS
                    )
                    pre_velocity = max(
                        response[sign]["maximum_pre_effect_velocity_m_per_s"] for sign in SIGNS
                    )
                    pre_ip = max(
                        response[sign]["maximum_pre_effect_ip_A"] for sign in SIGNS
                    )
                    pre_coil = max(
                        response[sign]["maximum_pre_effect_coil_radius_units"] for sign in SIGNS
                    )
                    pre_pass = bool(
                        pre_position <= float(probe_cfg["pre_effect_position_max_m"])
                        and pre_velocity <= float(probe_cfg["pre_effect_velocity_max_m_per_s"])
                        and pre_ip <= float(probe_cfg["pre_effect_ip_max_A"])
                        and pre_coil <= 1.0 + 1e-12
                    )
                    odd_input = (
                        response[1]["input_measured_current_A"]
                        - response[-1]["input_measured_current_A"]
                    ) / 2.0
                    odd_output = (
                        response[1]["response_unscaled"]
                        - response[-1]["response_unscaled"]
                    ) / 2.0
                    odd_scaled_norm = float(
                        np.linalg.norm(odd_output / np.tile(scales, 2))
                    )
                    development_signal = bool(
                        odd_scaled_norm
                        >= float(probe_cfg["signal_floor_multiplier"]) * floor_scaled
                    )
                    row.update({
                        "response_available": True,
                        "target_field_central_symmetry_exact": target_symmetry,
                        "observed_current_odd_l2_A": odd_norm,
                        "observed_current_required_l2_A": float(probe_cfg["required_observed_odd_signal_radius_l2"] * np.linalg.norm(radius_a)),
                        "observed_current_even_l2_A": even_norm,
                        "observed_current_even_to_odd_l2": ratio,
                        "observed_current_signal_pass": signal,
                        "observed_current_symmetry_pass": current_symmetry,
                        "maximum_pre_effect_position_m": pre_position,
                        "maximum_pre_effect_velocity_m_per_s": pre_velocity,
                        "maximum_pre_effect_ip_A": pre_ip,
                        "maximum_pre_effect_coil_radius_units": pre_coil,
                        "pre_effect_causality_pass": pre_pass,
                        "scaled_numerical_floor": floor_scaled,
                        "scaled_odd_response_l2": odd_scaled_norm,
                        "development_signal_pass": development_signal,
                        "odd_input_measured_current_A": odd_input.tolist(),
                        "odd_response_unscaled": odd_output.tolist(),
                        "signed_inputs_measured_current_A": {
                            str(sign): response[sign]["input_measured_current_A"].tolist()
                            for sign in SIGNS
                        },
                        "signed_responses_unscaled": {
                            str(sign): response[sign]["response_unscaled"].tolist()
                            for sign in SIGNS
                        },
                        "signed_off_mode_current_A": {
                            str(sign): response[sign]["off_mode_current_A"].tolist()
                            for sign in SIGNS
                        },
                        "raw_sha256_by_sign": {
                            str(sign): _sha256(
                                ctx.paths.raw / f"{signed[sign]['experiment_id']}.json.gz"
                            ) for sign in SIGNS
                        },
                    })
                rows.append(row)
    return rows


def _build_model_artifact(
    ctx: Stage42R3C3T13S5Context,
    development_results: Sequence[Mapping[str, Any]],
    signed_rows: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cfg = ctx.cfg["lattice_probe"]
    floor_one = np.asarray([1e-9, 1e-9, 1e-7, 1e-7, 1e-4], dtype=float)
    numerical_floor = np.tile(floor_one, 2)
    caps = np.asarray(cfg["tube_caps_unscaled"], dtype=float)
    entries = []
    fit_rows = []
    by_key: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for row in signed_rows:
        if row["offline_role"] != "development":
            raise ValueError("holdout row reached T13S5 model builder")
        by_key.setdefault((str(row["stratum"]), str(row["probe_window"])), []).append(row)
    for key, rows in sorted(by_key.items()):
        rows = sorted(rows, key=lambda row: DIRECTIONS.index(str(row["probe_direction"])))
        if len(rows) != N_DIRECTIONS or [
            str(row["probe_direction"]) for row in rows
        ] != list(DIRECTIONS):
            raise ValueError("T13S5 development direction coverage mismatch")
        x = np.asarray([row["odd_input_measured_current_A"] for row in rows], dtype=float)
        y = np.asarray([row["odd_response_unscaled"] for row in rows], dtype=float)
        rank, condition_json, condition_finite, rank_pass = (
            _development_matrix_diagnostics(
                x,
                required_rank=int(cfg["required_development_rank"]),
                maximum_condition=float(
                    cfg["maximum_development_condition_number"]
                ),
            )
        )
        jacobian = np.linalg.lstsq(x, y, rcond=None)[0]
        signed_residuals = []
        for row in rows:
            for sign in SIGNS:
                xi = np.asarray(row["signed_inputs_measured_current_A"][str(sign)], dtype=float)
                yi = np.asarray(row["signed_responses_unscaled"][str(sign)], dtype=float)
                signed_residuals.append(yi - xi @ jacobian)
        residuals = np.asarray(signed_residuals)
        radius = numerical_floor + float(cfg["tube_residual_multiplier"]) * np.max(
            np.abs(residuals), axis=0
        )
        tube_pass = bool(np.all(radius <= caps))
        signal_pass = all(bool(row["development_signal_pass"]) for row in rows)
        entry = {
            "stratum": key[0],
            "probe_window": key[1],
            "target_id": str(rows[0]["target_id"]),
            "action_delay_steps": int(rows[0]["actual_delay_steps"]),
            "slew_scale": float(rows[0]["actual_slew_scale"]),
            "input_definition": "two_effect_states_x_four_lattice_directions_full_14_coil_current_A",
            "output_definition": "two_effect_states_x_R_Z_vR_vZ_Ip_unscaled",
            "jacobian": jacobian.tolist(),
            "tube_radius_unscaled": radius.tolist(),
            "tube_caps_unscaled": caps.tolist(),
            "input_support_min": np.min(x, axis=0).tolist(),
            "input_support_max": np.max(x, axis=0).tolist(),
            "development_rank": rank,
            "development_condition_number": condition_json,
            "development_condition_number_finite": condition_finite,
            "development_signal_pass": signal_pass,
            "development_rank_condition_pass": rank_pass,
            "tube_non_vacuous_pass": tube_pass,
            "training_raw_sha256": sorted({
                value for row in rows for value in row["raw_sha256_by_sign"].values()
            }),
        }
        entries.append(entry)
        fit_rows.append({
            "stratum": key[0],
            "probe_window": key[1],
            "development_rank": rank,
            "development_condition_number": condition_json,
            "development_condition_number_finite": condition_finite,
            "development_signal_pass": signal_pass,
            "development_rank_condition_pass": rank_pass,
            "maximum_tube_to_cap_ratio": float(np.max(radius / caps)),
            "tube_non_vacuous_pass": tube_pass,
            "passed": bool(signal_pass and rank_pass and tube_pass),
        })
    if len(entries) != 4:
        raise ValueError("T13S5 model stratum/window coverage mismatch")
    development_raw = sorted(
        ctx.paths.raw / f"{result['experiment_id']}.json.gz"
        for result in development_results
    )
    core = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "model_contract": "causal_two_effect_lattice_local_map_v1",
        "training_role": "plus_first_development_only",
        "holdout_role_opened_during_fit": False,
        "pair_history_or_prefix_model_input": False,
        "source_action_result_or_wire_input": False,
        "entries": entries,
        "training_raw_files": [
            {
                "experiment_id": path.name.removesuffix(".json.gz"),
                "size_bytes": int(path.stat().st_size),
                "sha256": _sha256(path),
            }
            for path in development_raw
        ],
        "source_hashes": {
            "config_sha256": _sha256(
                _project_root() / "configs/stage4_2r3c3t13s5_lattice_native_split_holdout_370ms.json"
            ),
            "implementation_sha256": _sha256(Path(__file__).resolve()),
            "quantized_actuator_sha256": _sha256(
                _project_root() / "tsc_rzip_rllib/control/quantized_actuator.py"
            ),
        },
    }
    artifact = {
        **core,
        "self_digest_contract": "sha256_of_canonical_core_without_digest_fields",
        "canonical_core_sha256": _canonical_digest(core),
    }
    return artifact, fit_rows


def _json_condition_number(matrix: np.ndarray) -> tuple[float | None, bool]:
    """Return a strict-JSON condition number without changing rank semantics."""
    condition = float(np.linalg.cond(np.asarray(matrix, dtype=float)))
    finite = math.isfinite(condition)
    return (condition if finite else None), finite


def _development_matrix_diagnostics(
    matrix: np.ndarray,
    *,
    required_rank: int,
    maximum_condition: float,
) -> tuple[int, float | None, bool, bool]:
    values = np.asarray(matrix, dtype=float)
    rank = int(np.linalg.matrix_rank(values))
    condition, finite = _json_condition_number(values)
    passed = bool(
        rank == required_rank
        and finite
        and condition is not None
        and condition <= maximum_condition
    )
    return rank, condition, finite, passed


def _freeze_model(
    ctx: Stage42R3C3T13S5Context, artifact: Mapping[str, Any]
) -> dict[str, Any]:
    path = ctx.paths.model / "stage4_2r3c3t13s5_local_model_tube.json"
    if path.is_file():
        existing = t11.t1.r3c3.read_json(path)
        if existing != dict(artifact):
            raise ValueError("existing frozen T13S5 model differs from development fit")
    else:
        t11.t1.r3c3.atomic_write_json(path, artifact)
    record_path = ctx.paths.model / "stage4_2r3c3t13s5_model_freeze.json"
    record = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "model_path": str(path),
        "model_size_bytes": int(path.stat().st_size),
        "model_file_sha256": _sha256(path),
        "model_canonical_core_sha256": artifact["canonical_core_sha256"],
        "holdout_opened_before_model_hash": False,
        "frozen_utc": t11.t1.r3c3.utc_timestamp(),
    }
    if record_path.is_file():
        old = t11.t1.r3c3.read_json(record_path)
        comparable = {key: value for key, value in record.items() if key != "frozen_utc"}
        old_comparable = {key: value for key, value in old.items() if key != "frozen_utc"}
        if comparable != old_comparable:
            raise ValueError("existing T13S5 model freeze record mismatch")
        record = old
    else:
        t11.t1.r3c3.atomic_write_json(record_path, record)
    return record


def _evaluate_holdout(
    ctx: Stage42R3C3T13S5Context,
    holdout_signed_rows: Sequence[Mapping[str, Any]],
    artifact: Mapping[str, Any],
) -> list[dict[str, Any]]:
    scales = np.tile(np.asarray(ctx.cfg["lattice_probe"]["response_scales"], dtype=float), 2)
    floor = float(np.linalg.norm(
        np.tile(np.asarray([1e-9, 1e-9, 1e-7, 1e-7, 1e-4])
                / np.asarray(ctx.cfg["lattice_probe"]["response_scales"]), 2)
    ))
    models = {
        (str(row["stratum"]), str(row["probe_window"])): row
        for row in artifact["entries"]
    }
    outputs = []
    for group in holdout_signed_rows:
        key = (str(group["stratum"]), str(group["probe_window"]))
        model = models[key]
        jacobian = np.asarray(model["jacobian"], dtype=float)
        radius = np.asarray(model["tube_radius_unscaled"], dtype=float)
        for sign in SIGNS:
            actual = np.asarray(
                group["signed_responses_unscaled"][str(sign)], dtype=float
            )
            model_input = np.asarray(
                group["signed_inputs_measured_current_A"][str(sign)], dtype=float
            )
            predicted = model_input @ jacobian
            residual = actual - predicted
            contained = bool(np.all(np.abs(residual) <= radius + 1e-15))
            relative = float(
                np.linalg.norm(residual / scales)
                / max(np.linalg.norm(actual / scales), floor)
            )
            relative_pass = bool(
                relative <= float(
                    ctx.cfg["lattice_probe"]["maximum_holdout_scaled_center_relative_error"]
                )
            )
            outputs.append({
                "stratum": group["stratum"],
                "target_id": group["target_id"],
                "actual_delay_steps": group["actual_delay_steps"],
                "actual_slew_scale": group["actual_slew_scale"],
                "probe_window": group["probe_window"],
                "probe_direction": group["probe_direction"],
                "probe_sign": sign,
                "support_class": "finite_clean_extrapolation",
                "componentwise_contained": contained,
                "scaled_center_relative_error": relative,
                "scaled_center_relative_error_pass": relative_pass,
                "pre_effect_causality_pass": bool(group["pre_effect_causality_pass"]),
                "forbidden_model_input_count": 0,
                "passed": bool(
                    contained and relative_pass
                    and group["pre_effect_causality_pass"]
                ),
            })
    return outputs


def summarize_from_raw(
    ctx: Stage42R3C3T13S5Context,
    specs: Sequence[Mapping[str, Any]],
    selected_pairs: Sequence[Mapping[str, Any]],
    *,
    write_outputs: bool = True,
    open_hook: Callable[[str, Path], None] | None = None,
) -> dict[str, Any]:
    development_specs = [
        spec for spec in specs
        if spec["r3c3t13s5_offline_role"] == "development"
    ]
    holdout_specs = [
        spec for spec in specs
        if spec["r3c3t13s5_offline_role"] == "blind_holdout"
    ]
    if len(development_specs) != 34 or len(holdout_specs) != 34:
        raise ValueError("T13S5 development/holdout split mismatch")
    open_events: list[dict[str, Any]] = []
    guard = BlindOpenOrderGuard(expected_development_count=34)

    def open_one(role: str, spec: Mapping[str, Any]) -> dict[str, Any]:
        path = ctx.paths.raw / f"{spec['experiment_id']}.json.gz"
        guard.before_open(role)
        if open_hook is not None:
            open_hook(role, path)
        result = t11.t1.r3c3.read_json_gz(path)
        if not _result_complete(path, spec):
            raise ValueError(f"incomplete or incompatible T13S5 raw: {path}")
        open_events.append({
            "ordinal": len(open_events) + 1,
            "offline_role": role,
            "experiment_id": str(spec["experiment_id"]),
            "path": str(path),
            "size_bytes": int(path.stat().st_size),
            "sha256": _sha256(path),
            "opened_utc": t11.t1.r3c3.utc_timestamp(),
        })
        return result

    development = [open_one("development", spec) for spec in development_specs]
    development_signed = _signed_group_rows(ctx, development)
    artifact, fit_rows = _build_model_artifact(
        ctx, development, development_signed
    )
    freeze = _freeze_model(ctx, artifact)
    guard.freeze(str(freeze["model_file_sha256"]))
    pre_holdout_order = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "development_open_count_before_model_hash": len(open_events),
        "holdout_open_count_before_model_hash": 0,
        "model_file_sha256_before_holdout_open": freeze["model_file_sha256"],
        "model_frozen_utc": freeze["frozen_utc"],
        "events": copy.deepcopy(open_events),
        "holdout_open_started": False,
        "passed": len(open_events) == 34,
    }
    order_path = ctx.paths.model / "stage4_2r3c3t13s5_input_open_order.json"
    t11.t1.r3c3.atomic_write_json(order_path, pre_holdout_order)
    holdout = [open_one("blind_holdout", spec) for spec in holdout_specs]
    order = {
        **pre_holdout_order,
        "events": open_events,
        "holdout_open_started": True,
        "total_open_count": len(open_events),
        "development_first_exact": all(
            row["offline_role"] == "development" for row in open_events[:34]
        ) and all(
            row["offline_role"] == "blind_holdout" for row in open_events[34:]
        ),
        "holdout_first_open_ordinal": 35,
        "model_hash_still_exact_after_holdout": (
            _sha256(Path(freeze["model_path"])) == freeze["model_file_sha256"]
        ),
    }
    order["passed"] = bool(
        order["development_first_exact"]
        and order["model_hash_still_exact_after_holdout"]
        and len(open_events) == 68
    )
    t11.t1.r3c3.atomic_write_json(order_path, order)

    results = development + holdout
    execution_rows = _execution_rows(ctx, results, selected_pairs)
    all_signed = _signed_group_rows(ctx, results)
    holdout_signed = [
        row for row in all_signed if row["offline_role"] == "blind_holdout"
    ]
    holdout_rows = _evaluate_holdout(ctx, holdout_signed, artifact)

    def count(rows: Sequence[Mapping[str, Any]], field: str) -> int:
        return sum(bool(row.get(field)) for row in rows)

    current_values = [
        float(row["max_current_utilization"])
        for row in execution_rows if row["max_current_utilization"] is not None
    ]
    maximum_current = max(current_values) if current_values else None
    component_count = sum(int(row["actuator_component_count"]) for row in execution_rows)
    interval_count = sum(int(row["actuator_inside_interval_count"]) for row in execution_rows)
    field_count = sum(int(row["card15_field_count"]) for row in execution_rows)
    field_length_count = sum(
        int(row["card15_length_exact_count"]) for row in execution_rows
    )
    development_group_rows = [
        row for row in all_signed if row["offline_role"] == "development"
    ]
    raw_paths = [
        ctx.paths.raw / f"{spec['experiment_id']}.json.gz" for spec in specs
    ]
    raw_rows = [
        {
            "path": path.name,
            "size_bytes": int(path.stat().st_size),
            "sha256": _sha256(path),
        }
        for path in sorted(raw_paths)
    ]
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "phase": "lattice_transition_blind_holdout",
        "identification_only": True,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "independent_new_history_confirmation": False,
        "independent_long_hold_validated": False,
        "formal_timing_unchanged": True,
        "expected_rollouts": 68,
        "n_rollouts": len(execution_rows),
        "raw_file_count": len(raw_rows),
        "raw_total_bytes": sum(row["size_bytes"] for row in raw_rows),
        "raw_inventory_digest": _canonical_digest(raw_rows),
        "execution_pass_count": count(execution_rows, "execution_pass"),
        "extended_baseline_prefix_exact_count": count(
            execution_rows, "extended_baseline_prefix_exact"
        ),
        "baseline_formal_reproduction_count": count(
            execution_rows, "baseline_formal_reproduced"
        ),
        "runtime_or_environment_error_count": sum(
            row["failure_class"] == "runtime_or_environment_error"
            for row in execution_rows
        ),
        "plant_restart_fidelity_failure_count": sum(
            row["failure_class"] == "plant_restart_fidelity_failure"
            for row in execution_rows
        ),
        "controller_causality_failure_count": sum(
            row["failure_class"] == "controller_causality_failure"
            for row in execution_rows
        ),
        "lattice_probe_execution_failure_count": sum(
            row["failure_class"] == "lattice_probe_execution_failure"
            for row in execution_rows
        ),
        "actuator_interval_or_serialization_failure_count": sum(
            row["failure_class"] == "actuator_interval_or_serialization_failure"
            for row in execution_rows
        ),
        "baseline_prefix_mismatch_count": sum(
            row["failure_class"] == "baseline_prefix_mismatch"
            for row in execution_rows
        ),
        "baseline_formal_reproduction_mismatch_count": sum(
            row["failure_class"] == "baseline_formal_reproduction_mismatch"
            for row in execution_rows
        ),
        "forbidden_controller_input_count": sum(
            int(row["forbidden_trace_count"]) for row in execution_rows
        ),
        "cancellation_policy_pass_count": count(
            execution_rows, "cancellation_policy_pass"
        ),
        "return_to_stored_center_count": sum(
            row["cancellation_method"]
            == "exact_return_to_stored_issue_center"
            for row in execution_rows
        ),
        "negative_current_center_count": sum(
            row["cancellation_method"]
            == "exact_negative_relative_current_center"
            for row in execution_rows
        ),
        "actuator_component_expected": EXPECTED_CURRENT_COMPONENTS,
        "actuator_component_count": component_count,
        "actuator_inside_interval_count": interval_count,
        "card15_field_count": field_count,
        "card15_length_exact_count": field_length_count,
        "clip_or_rescale_count": sum(
            int(row["clip_or_rescale_count"]) for row in execution_rows
        ),
        "maximum_actuator_interval_excess_A": max(
            (
                float(row["maximum_actuator_interval_excess_A"])
                for row in execution_rows
                if row["maximum_actuator_interval_excess_A"] is not None
            ), default=None,
        ),
        "signed_group_count": len(all_signed),
        "target_field_central_symmetry_exact_count": count(
            all_signed, "target_field_central_symmetry_exact"
        ),
        "observed_current_signal_pass_count": count(
            all_signed, "observed_current_signal_pass"
        ),
        "observed_current_symmetry_pass_count": count(
            all_signed, "observed_current_symmetry_pass"
        ),
        "pre_effect_causality_pass_count": count(
            all_signed, "pre_effect_causality_pass"
        ),
        "development_signed_group_count": len(development_group_rows),
        "development_signal_pass_count": count(
            development_group_rows, "development_signal_pass"
        ),
        "model_fit_count": len(fit_rows),
        "model_rank_condition_pass_count": count(
            fit_rows, "development_rank_condition_pass"
        ),
        "model_non_vacuous_tube_pass_count": count(
            fit_rows, "tube_non_vacuous_pass"
        ),
        "maximum_development_condition_number": max(
            (
                float(row["development_condition_number"])
                for row in fit_rows
                if row["development_condition_number"] is not None
            ),
            default=None,
        ),
        "nonfinite_development_condition_count": sum(
            not bool(row["development_condition_number_finite"])
            for row in fit_rows
        ),
        "maximum_tube_to_cap_ratio": max(
            (float(row["maximum_tube_to_cap_ratio"]) for row in fit_rows),
            default=None,
        ),
        "holdout_signed_response_count": len(holdout_rows),
        "holdout_componentwise_containment_pass_count": count(
            holdout_rows, "componentwise_contained"
        ),
        "holdout_scaled_center_error_pass_count": count(
            holdout_rows, "scaled_center_relative_error_pass"
        ),
        "holdout_pre_effect_causality_pass_count": count(
            holdout_rows, "pre_effect_causality_pass"
        ),
        "maximum_holdout_scaled_center_relative_error": max(
            (float(row["scaled_center_relative_error"]) for row in holdout_rows),
            default=None,
        ),
        "forbidden_model_input_count": sum(
            int(row["forbidden_model_input_count"]) for row in holdout_rows
        ),
        "development_before_holdout_open_order_pass": bool(order["passed"]),
        "model_file_sha256": freeze["model_file_sha256"],
        "model_canonical_core_sha256": freeze["model_canonical_core_sha256"],
        "maximum_current_utilization": maximum_current,
        "maximum_current_utilization_allowed": float(
            ctx.cfg["lattice_probe"]["maximum_current_utilization"]
        ),
    }
    summary["execution_gate_passed"] = bool(
        len(execution_rows) == summary["execution_pass_count"] == 68
        and summary["extended_baseline_prefix_exact_count"] == 4
        and summary["baseline_formal_reproduction_count"] == 4
        and summary["forbidden_controller_input_count"] == 0
        and summary["cancellation_policy_pass_count"] == 68
        and summary["return_to_stored_center_count"]
        + summary["negative_current_center_count"] == 64
    )
    summary["actuator_interval_gate_passed"] = bool(
        component_count == interval_count == field_count == field_length_count
        == EXPECTED_CURRENT_COMPONENTS
        and summary["clip_or_rescale_count"] == 0
    )
    summary["actuator_signed_group_gate_passed"] = bool(
        len(all_signed) == 32
        and summary["target_field_central_symmetry_exact_count"] == 32
        and summary["observed_current_signal_pass_count"] == 32
        and summary["observed_current_symmetry_pass_count"] == 32
    )
    summary["pre_effect_causality_gate_passed"] = bool(
        len(all_signed) == summary["pre_effect_causality_pass_count"] == 32
    )
    summary["development_model_gate_passed"] = bool(
        len(development_group_rows) == summary["development_signal_pass_count"] == 16
        and len(fit_rows) == summary["model_rank_condition_pass_count"]
        == summary["model_non_vacuous_tube_pass_count"] == 4
    )
    summary["blind_holdout_gate_passed"] = bool(
        len(holdout_rows)
        == summary["holdout_componentwise_containment_pass_count"]
        == summary["holdout_scaled_center_error_pass_count"]
        == summary["holdout_pre_effect_causality_pass_count"]
        == 32
        and summary["forbidden_model_input_count"] == 0
        and summary["development_before_holdout_open_order_pass"]
    )
    summary["current_utilization_pass"] = bool(
        maximum_current is not None
        and maximum_current <= float(
            ctx.cfg["lattice_probe"]["maximum_current_utilization"]
        )
    )
    summary["passed"] = bool(
        summary["execution_gate_passed"]
        and summary["actuator_interval_gate_passed"]
        and summary["actuator_signed_group_gate_passed"]
        and summary["pre_effect_causality_gate_passed"]
        and summary["development_model_gate_passed"]
        and summary["blind_holdout_gate_passed"]
        and summary["current_utilization_pass"]
    )
    if write_outputs:
        for name, values in (
            ("results", execution_rows),
            ("signed_transition_results", all_signed),
            ("development_model_results", fit_rows),
            ("blind_holdout_results", holdout_rows),
        ):
            t11.t1.r3c3.atomic_write_json(ctx.paths.control / f"{name}.json", values)
            t11.t1.r3c3.write_csv(ctx.paths.control / f"{name}.csv", values)
        t11.t1.r3c3.atomic_write_json(ctx.paths.control / "summary.json", summary)
        t11.t1.r3c3.atomic_write_json(
            ctx.paths.source_reference / "raw_inventory.json", {
                "n_files": len(raw_rows),
                "total_bytes": summary["raw_total_bytes"],
                "digest": summary["raw_inventory_digest"],
                "files": raw_rows,
            }
        )
    return summary


def analyze(
    ctx: Stage42R3C3T13S5Context, summary: Mapping[str, Any]
) -> dict[str, Any]:
    primary_pass = bool(summary.get("passed"))
    verdict = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "verdict": (
            "LATTICE_HOLDOUT_PASS_LOCAL_MODEL_ONLY"
            if primary_pass else "LATTICE_HOLDOUT_FAIL_REDESIGN"
        ),
        "primary_pass": primary_pass,
        "identification_only": True,
        "real_mpc_executed": False,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "independent_new_history_confirmation": False,
        "independent_long_hold_validated": False,
        "bc_dagger_or_rl_allowed": False,
        "next_if_pass": (
            "Implement and validate an offline robust finite-horizon MPC prototype, "
            "then preregister a separate minimal real-MPC sentinel."
        ),
        "next_if_fail": (
            "Preserve raw and distinguish actuator uncertainty, signal, off-mode "
            "quantization, latent-history dependence, and local-model error."
        ),
    }
    t11.t1.r3c3.atomic_write_json(
        ctx.paths.analysis / "stage4_2r3c3t13s5_summary.json", dict(summary)
    )
    t11.t1.r3c3.atomic_write_json(
        ctx.paths.analysis / "stage4_2r3c3t13s5_verdict.json", verdict
    )
    state = t11.t1.r3c3.read_json(ctx.paths.state)
    state.update({
        "finished": True,
        "primary_pass": primary_pass,
        "phase_status": "campaign_complete",
        "stop_reason": "" if primary_pass else "lattice_holdout_scientific_gate_failed",
        "verdict": verdict,
        "updated_utc": t11.t1.r3c3.utc_timestamp(),
    })
    t11.t1.r3c3.atomic_write_json(ctx.paths.state, state)
    return {"control_summary": dict(summary), "verdict": verdict}


def execute(
    ctx: Stage42R3C3T13S5Context,
    *,
    command: str,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    selected_pairs, specs = prepare(ctx, resume=resume)
    offline = run_offline_lattice_audit(
        ctx, selected_pairs, allow_existing_raw=resume
    )
    if not bool(offline.get("passed")):
        state = t11.t1.r3c3.read_json(ctx.paths.state)
        state.update({
            "finished": True,
            "primary_pass": False,
            "phase_status": "offline_gate_failed",
            "stop_reason": "frozen_dynamic_lattice_infeasible",
            "offline_lattice_audit": offline,
            "real_tsc_executed": False,
            "updated_utc": t11.t1.r3c3.utc_timestamp(),
        })
        t11.t1.r3c3.atomic_write_json(ctx.paths.state, state)
        if command == "offline":
            return {
                "schema_version": SCHEMA_VERSION,
                "stage": STAGE,
                "phase": "offline_dynamic_lattice_preflight",
                "offline_lattice_audit": offline,
                "real_tsc_executed": False,
                "finished": True,
                "primary_pass": False,
            }
        raise RuntimeError("T13S5 offline lattice gate failed; no real TSC started")
    if command == "offline":
        state = t11.t1.r3c3.read_json(ctx.paths.state)
        state.update({
            "finished": False,
            "primary_pass": False,
            "phase_status": "offline_gate_complete",
            "stop_reason": "",
            "offline_lattice_audit": offline,
            "updated_utc": t11.t1.r3c3.utc_timestamp(),
        })
        t11.t1.r3c3.atomic_write_json(ctx.paths.state, state)
        return {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "phase": "offline_dynamic_lattice_preflight",
            "offline_lattice_audit": offline,
            "real_tsc_executed": False,
            "finished": False,
            "primary_pass": False,
        }
    execution = _evaluate_control(ctx, specs, backend=backend, resume=resume)
    if int(execution["complete_after_run"]) != len(specs):
        raise RuntimeError("T13S5 raw set incomplete; resume safely after runtime repair")
    summary = summarize_from_raw(ctx, specs, selected_pairs)
    return analyze(ctx, summary)


def self_test() -> dict[str, Any]:
    cfg = t11.t1.r3c3.read_json(
        _project_root()
        / "configs/stage4_2r3c3t13s5_lattice_native_split_holdout_370ms.json"
    )
    _validate_config(cfg)
    fields = [format_number(0.0)] * N_COILS
    mode0 = np.ones(N_COILS, dtype=float) / math.sqrt(N_COILS)
    mode1 = np.asarray([1.0 if index % 2 == 0 else -1.0 for index in range(N_COILS)])
    mode1 /= np.linalg.norm(mode1)
    mode2 = np.asarray([1.0] * (N_COILS // 2) + [-1.0] * (N_COILS // 2))
    mode2 /= np.linalg.norm(mode2)
    modes = np.column_stack((mode0, mode1, mode2))
    plans: dict[str, dict[str, Any]] = {}
    for direction in DIRECTIONS:
        direction_cfg = direction_lattice_config(
            center_fields=fields,
            turns_tsc=[100.0] * N_COILS,
            direction=direction,
            cfg=cfg["lattice_probe"],
        )
        plans[direction] = choose_lattice_displacement(
            center_fields=fields,
            measured_current_a_tsc=[0.0] * N_COILS,
            baseline_action_norm_tsc=[0.0] * N_COILS,
            mode_vector_tsc=lattice_native_direction(
                modes,
                direction,
                split_coil=int(cfg["lattice_probe"]["split_coil_index_tsc"]),
            ),
            turns_tsc=[100.0] * N_COILS,
            max_slew_step_a=1000.0,
            minimum_current_a_tsc=[-1000.0] * N_COILS,
            maximum_current_a_tsc=[1000.0] * N_COILS,
            cfg=direction_cfg,
        )
    plan = plans["mode0_coil8_component"]
    inverse = exact_inverse_lattice_action(
        center_fields=fields,
        signed_issue_delta_kAt_tsc=plan["delta_field_kAt_tsc"],
        measured_current_a_tsc=[0.0] * N_COILS,
        baseline_action_norm_tsc=[0.0] * N_COILS,
        turns_tsc=[100.0] * N_COILS,
        max_slew_step_a=1000.0,
        minimum_current_a_tsc=[-1000.0] * N_COILS,
        maximum_current_a_tsc=[1000.0] * N_COILS,
        cfg=cfg["lattice_probe"],
    )
    step_cases = {
        "positive": local_symmetric_card15_step(format_number(1.234)),
        "negative": local_symmetric_card15_step(format_number(-1.234)),
        "exponent_boundary": local_symmetric_card15_step(format_number(1000.0)),
        "zero": local_symmetric_card15_step(format_number(0.0)),
    }
    passed = bool(
        all(item["passed"] for item in plans.values())
        and inverse["passed"]
        and all(item["target_field_central_symmetry_exact"] for item in plans.values())
        and plan["minimum_significant_grid_steps_actual"] >= 8_000
        and all(value > 0 for value in step_cases.values())
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "design_revision": 1,
        "expected_rollouts": 68,
        "expected_current_components": EXPECTED_CURRENT_COMPONENTS,
        "local_step_cases_kAt": {
            key: float(value) for key, value in step_cases.items()
        },
        "lattice_plans": plans,
        "inverse_plan": inverse,
        "real_tsc_executed": False,
        "formal_timing_unchanged": True,
        "bc_dagger_or_rl_allowed": False,
        "passed": passed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage4.2R3c3T13S5 lattice transition holdout"
    )
    parser.add_argument("--config", type=Path)
    parser.add_argument("--source-stage4-2r3b-run", type=Path)
    parser.add_argument("--source-stage4-2r3c3-run", type=Path)
    parser.add_argument("--source-stage4-2r3c3-bank-dir", type=Path)
    parser.add_argument("--source-stage4-2r3c3t1-run", type=Path)
    parser.add_argument("--source-stage4-2r3c3t1-audit-dir", type=Path)
    parser.add_argument("--source-stage4-2r3c3t3-controller-bank", type=Path)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--command", choices=("all", "offline"), default="all")
    parser.add_argument("--backend", choices=("serial", "ray"), default="ray")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), indent=2, sort_keys=True))
        return
    required = (
        ("--config", args.config),
        ("--source-stage4-2r3b-run", args.source_stage4_2r3b_run),
        ("--source-stage4-2r3c3-run", args.source_stage4_2r3c3_run),
        ("--source-stage4-2r3c3-bank-dir", args.source_stage4_2r3c3_bank_dir),
        ("--source-stage4-2r3c3t1-run", args.source_stage4_2r3c3t1_run),
        ("--source-stage4-2r3c3t1-audit-dir", args.source_stage4_2r3c3t1_audit_dir),
        ("--source-stage4-2r3c3t3-controller-bank", args.source_stage4_2r3c3t3_controller_bank),
        ("--run-dir", args.run_dir),
    )
    missing = [name for name, value in required if value is None]
    if missing:
        parser.error("missing required arguments: " + ", ".join(missing))
    ctx = load_stage42r3c3t13s5_config(
        args.config,
        source_stage42r3b_run=args.source_stage4_2r3b_run,
        source_stage42r3c3_run=args.source_stage4_2r3c3_run,
        source_stage42r3c3_bank_dir=args.source_stage4_2r3c3_bank_dir,
        source_stage42r3c3t1_run=args.source_stage4_2r3c3t1_run,
        source_stage42r3c3t1_audit_dir=args.source_stage4_2r3c3t1_audit_dir,
        source_stage42r3c3t3_controller_bank=args.source_stage4_2r3c3t3_controller_bank,
        run_dir_override=args.run_dir,
    )
    output = execute(
        ctx, command=args.command, backend=args.backend, resume=args.resume
    )
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
