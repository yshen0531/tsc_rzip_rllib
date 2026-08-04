"""Stage4.2R3c3T13S24D1R11 full replacement transition identification."""

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
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.control import sequential_transition as transition
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s21_cumulative_exact_card15_pooled_observer_campaign as s21,
)


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S24D1R11"
RUN_NAME = "stage4_2r3c3t13s24d1r11_full_replacement_sequential_transition_identification"
CAMPAIGN_IDENTITY = "full_replacement_sequential_transition_identification_v1"
CONTROLLER_REVISION = "sequential_replacement_card15_probe_v42r3c3t13s24d1r11_v1"
BASELINE_ID = "sequential_baseline"
N_COILS = 14
DT_S = 0.01


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _write_json_gz(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True)
class Paths:
    run_dir: Path
    stage_dir: Path
    variants: Path
    specs: Path
    source_reference: Path
    raw: Path
    analysis: Path
    model: Path
    state: Path
    manifest: Path


def _paths(run_dir: Path) -> Paths:
    root = run_dir.expanduser().resolve()
    stage = root / RUN_NAME
    return Paths(
        run_dir=root,
        stage_dir=stage,
        variants=stage / "variants",
        specs=stage / "specs",
        source_reference=stage / "source_reference",
        raw=stage / "raw",
        analysis=stage / "analysis",
        model=stage / "model",
        state=stage / "stage_state.json",
        manifest=stage / "stage_manifest.json",
    )


@dataclass(frozen=True)
class Context:
    cfg: dict[str, Any]
    config_path: Path
    base_ctx: Any
    source_s21_ctx: Any
    source_s23r1_output: Path
    source_s24_run: Path
    source_d1r9_v1: Path
    source_d1r9_v2: Path
    source_d1r10_run: Path
    source_d1r10_audit: Path
    paths: Paths


def _requested_matrix(cfg: Mapping[str, Any]) -> np.ndarray:
    matrix = np.asarray(cfg["schedule_contract"]["requested_matrix"], dtype=float)
    if matrix.shape != (24, 16) or not np.all(np.isfinite(matrix)):
        raise ValueError("D1R11 requested matrix shape or values changed")
    if _digest(matrix.tolist()) != str(
        cfg["schedule_contract"]["requested_matrix_digest"]
    ):
        raise ValueError("D1R11 requested matrix digest changed")
    return matrix


def _validate_config(cfg: Mapping[str, Any], config_path: Path) -> None:
    root = _project_root()
    exact = {
        "schema_version": 1,
        "stage": STAGE,
        "run_name": RUN_NAME,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": "r42r3c3t13s24d1r11_full_replacement_sequential_transition_identification_v1",
    }
    for key, value in exact.items():
        if cfg.get(key) != value:
            raise ValueError(f"S24 frozen {key} changed")
    for key in ("design_document", "base_s21_config"):
        path = (root / str(cfg[key])).resolve()
        if root not in path.parents or not path.is_file():
            raise ValueError(f"S24 {key} is outside the package")
        expected = str(cfg[f"{key}_sha256"])
        if _sha256(path) != expected:
            raise ValueError(f"S24 {key} hash changed")
    source = cfg["source_contract"]
    if (
        str(source["s24_run_name"])
        != "stage4_2r3c3t13s24_sequential_transition_identification_20260803_111226_0c71836"
        or int(source["s24_raw_count"]) != 600
        or int(source["s24_raw_total_bytes"]) != 34003877
        or str(source["s24_raw_inventory_digest"])
        != "fae5f62671296c837e00158fe204a1630fc70aace87be650ad13d75928f20c70"
        or str(source["s24_implementation_sha256"])
        != "29283348f004f90eeea5e563ae2e5397397e324bfb6b51ecff3436398938c6e9"
        or str(source["d1r9_route"])
        != "CENTRAL_ROW_REPLACEMENT_PREFLIGHT_PASS_EXACT_ROW_SENTINEL_DESIGN_REQUIRED"
        or str(source["d1r9_requested_matrix_digest"])
        != "106dfed384febb16019e4d39ce1da03762ad9dbb5e8e69120a4a9d9acdebc30b"
        or str(source["d1r10_route"])
        != "EXACT_ROW_COMPLETION_SENTINEL_PASS_FULL_REPLACEMENT_IDENTIFICATION_DESIGN_REQUIRED"
        or int(source["d1r10_raw_count"]) != 126
        or int(source["d1r10_raw_total_bytes"]) != 7617161
        or str(source["ordered_spec_digest"])
        != "e370269558ab079fe6d1f2293b2920b7774e3239942c7dd60ae4b638138f8c7a"
        or str(source["s21_run_name"])
        != "stage4_2r3c3t13s21_cumulative_exact_card15_pooled_observer_campaign_20260803_024821_98dc353"
        or str(source["s21_package_commit"]) != "98dc353"
        or int(source["s21_raw_count"]) != 360
        or int(source["s21_raw_total_bytes"]) != 21083271
        or str(source["s21_raw_inventory_digest"])
        != "8d5a67944e344b06da89c64625d1e94adc60432db230655ec9250c339e3e50f4"
        or str(source["s22_route"])
        != "AFFINE_STATE10_AUTHORITY_FAIL_SEQUENTIAL_MODEL_REQUIRED"
        or str(source["s23_route"])
        != "SEQUENTIAL_HADAMARD_LATTICE_PREFLIGHT_FAIL_SCHEDULE_REDESIGN"
        or str(source["s23d1_route"])
        != "BOUNDED_TERNARY_SCHEDULE_SEARCH_FAIL_NEW_EXCITATION_ARCHITECTURE_REQUIRED"
        or str(source["s23r1_route"])
        != "AMPLITUDE_CODED_HADAMARD_PREFLIGHT_PASS_FREEZE_S24_REQUIRED"
        or str(source["s23r1_detailed_sha256"])
        != "2fe49067ea49551eda1341f6aff74ad6d9c3a5abc2b05e26453aae12bddc0e79"
        or any(
            len(str(value)) != 64
            for key, value in source.items()
            if key.endswith("_sha256") or key.endswith("_digest")
        )
    ):
        raise ValueError("S24 immutable source contract changed")
    matrix = cfg["control_matrix"]
    required_counts = {
        "training_pairs": 12,
        "training_contexts": 24,
        "training_baselines": 24,
        "training_sequences": 576,
        "training_rollouts": 600,
        "calibration_pairs": 4,
        "calibration_contexts": 8,
        "calibration_baselines": 8,
        "calibration_sequences": 192,
        "calibration_rollouts": 200,
        "holdout_pairs": 4,
        "holdout_contexts": 8,
        "holdout_baselines": 8,
        "holdout_sequences": 192,
        "holdout_rollouts": 200,
        "history_members_per_pair": 2,
        "sequences_per_context": 24,
        "total_contexts": 40,
        "total_real_rollouts": 1000,
    }
    if any(int(matrix.get(key, -1)) != value for key, value in required_counts.items()):
        raise ValueError("S24 1,000-rollout matrix changed")
    if not all(bool(matrix.get(key)) for key in (
        "require_fresh_controller", "require_fresh_tsc_process",
        "require_online_action_computation", "forbid_future_actions",
        "forbid_future_measurements",
    )):
        raise ValueError("S24 execution blindness changed")
    schedule = cfg["schedule_contract"]
    if (
        list(map(int, schedule["issue_task_steps"])) != [10, 13, 15, 17]
        or list(map(int, schedule["cancel_task_steps"])) != [11, 14, 16, 18]
        or list(map(int, schedule["issue_effect_states"])) != [11, 14, 16, 18]
        or list(map(int, schedule["cancel_effect_states"])) != [12, 15, 17, 19]
        or int(schedule["dynamic_exact_search_radius"]) != 16
        or float(schedule["maximum_absolute_coordinate_error"]) != 0.07
        or float(schedule["minimum_active_absolute_coordinate"]) != 0.18
        or float(schedule["minimum_desired_applied_current_cosine"]) != 0.98
        or float(schedule["maximum_relative_off_basis_residual"]) != 0.1
        or float(schedule["maximum_incremental_normalized_action_linf"]) != 0.25
        or float(schedule["maximum_online_cancel_incremental_linf"]) != 0.24
        or float(schedule["maximum_total_normalized_action_abs"]) != 1.0
        or float(schedule["maximum_current_utilization"]) != 0.55
        or not bool(schedule["require_exact_stored_center_cancellation"])
        or not bool(schedule["require_exact_zero_target_jump_net"])
    ):
        raise ValueError("S24 action schedule or gate changed")
    requested = _requested_matrix(cfg)
    normalized = requested / np.linalg.norm(requested, axis=0, keepdims=True)
    if (
        requested.shape != (24, 16)
        or int(np.linalg.matrix_rank(requested)) != 16
        or not math.isclose(float(np.linalg.cond(normalized)), 2.036467529817257, abs_tol=1e-12)
    ):
        raise ValueError("S24 requested matrix changed")
    model = cfg["transition_model"]
    if (
        int(model["causal_prefix_start_state"]) != 1
        or int(model["causal_prefix_end_state"]) != 10
        or int(model["recursive_start_state"]) != 10
        or int(model["history_length"]) != 10
        or int(model["action_history_length"]) != 3
        or int(model["task_clock_legendre_degree"]) != 3
        or list(model["feature_candidates"]) != ["L", "SA", "Q"]
        or list(map(float, model["ridge_grid"]))
        != [0.0, 1e-10, 1e-8, 1e-6, 1e-4, 1e-2, 1.0, 100.0]
        or list(map(float, model["visible_state_scales"]))
        != [0.03, 0.03, 0.1, 0.1, 2000.0]
        or float(model["maximum_absolute_recursive_scaled_error"]) != 0.1
        or float(model["tube_multiplier"]) != 2.0
        or list(map(float, model["belief_halfwidth_caps"]))
        != [0.003, 0.003, 0.01, 0.01, 1000.0]
        or str(model["outer_group_key"]) != "pair_id"
    ):
        raise ValueError("S24 recursive model family changed")
    formal = cfg["formal_timing_contract"]
    if (
        formal["normal"] != {"arrival_deadline_step": 25, "hold_through_step": 35}
        or formal["weak"] != {"arrival_deadline_step": 27, "hold_through_step": 37}
        or float(formal["position_tolerance_m"]) != 0.03
        or float(formal["speed_tolerance_m_per_s"]) != 0.1
        or float(formal["ip_tolerance_A"]) != 10000.0
        or int(formal["arrival_streak_steps"]) != 3
        or bool(formal["arrival_deadline_expansion_allowed"])
    ):
        raise ValueError("S24 formal timing changed")
    routes = cfg["routes"]
    if routes != {
        "offline_fail": "FULL_REPLACEMENT_IDENTIFICATION_PREFLIGHT_FAIL_NO_TSC",
        "runtime_fail": "FULL_REPLACEMENT_IDENTIFICATION_RUNTIME_OR_ACTION_FAIL_STOP",
        "training_fail": "FULL_REPLACEMENT_TRANSITION_TRAINING_MODEL_FAIL",
        "calibration_fail": "FULL_REPLACEMENT_TRANSITION_CALIBRATION_TUBE_FAIL",
        "holdout_fail": "FULL_REPLACEMENT_TRANSITION_FRESH_HOLDOUT_FAIL_REDESIGN",
        "pass": "FULL_REPLACEMENT_CAUSAL_TRANSITION_HOLDOUT_PASS_MODEL_ONLY_ZERO_TSC_MPC_DESIGN_REQUIRED",
    }:
        raise ValueError("S24 routes changed")
    if (
        not bool(cfg["identification_only"])
        or not bool(cfg["fresh_holdout_required"])
        or bool(cfg["probe_trajectories_allowed_in_expert_dataset"])
        or bool(cfg["independent_long_hold_validated"])
        or bool(cfg["bc_dagger_or_rl_allowed"])
    ):
        raise ValueError("S24 scientific scope changed")
    if config_path.resolve() != (
        root
        / "configs/stage4_2r3c3t13s24d1r11_full_replacement_sequential_transition_identification_370ms.json"
    ).resolve():
        raise ValueError("D1R11 config path changed")


def load_config(
    config_path: Path,
    *,
    source_s21_run: Path,
    source_s23r1_output: Path,
    source_s24_run: Path,
    source_d1r9_v1: Path,
    source_d1r9_v2: Path,
    source_d1r10_run: Path,
    source_d1r10_audit: Path,
    run_dir: Path,
    source_stage42r3b_run: Path,
    source_stage42r3c3_run: Path,
    source_stage42r3c3_bank_dir: Path,
    source_stage42r3c3t1_run: Path,
    source_stage42r3c3t1_audit_dir: Path,
    source_stage42r3c3t3_controller_bank: Path,
    q1_run: Path,
    q2_run: Path,
    q1_audit: Path,
    q2_audit: Path,
    r3b_server_audit: Path,
    r3b_snapshot_checks: Path,
) -> Context:
    config_path = config_path.expanduser().resolve()
    cfg = _read_json(config_path)
    _validate_config(cfg, config_path)
    base_config = (_project_root() / str(cfg["base_s21_config"])).resolve()
    source_kwargs = {
        "source_stage42r3b_run": source_stage42r3b_run,
        "source_stage42r3c3_run": source_stage42r3c3_run,
        "source_stage42r3c3_bank_dir": source_stage42r3c3_bank_dir,
        "source_stage42r3c3t1_run": source_stage42r3c3t1_run,
        "source_stage42r3c3t1_audit_dir": source_stage42r3c3t1_audit_dir,
        "source_stage42r3c3t3_controller_bank": source_stage42r3c3t3_controller_bank,
        "q1_run": q1_run,
        "q2_run": q2_run,
        "q1_audit": q1_audit,
        "q2_audit": q2_audit,
        "r3b_server_audit": r3b_server_audit,
        "r3b_snapshot_checks": r3b_snapshot_checks,
    }
    base_ctx = s21.load_config(base_config, run_dir=run_dir, **source_kwargs)
    source_ctx = s21.load_config(base_config, run_dir=source_s21_run, **source_kwargs)
    return Context(
        cfg=cfg,
        config_path=config_path,
        base_ctx=base_ctx,
        source_s21_ctx=source_ctx,
        source_s23r1_output=source_s23r1_output.expanduser().resolve(),
        source_s24_run=source_s24_run.expanduser().resolve(),
        source_d1r9_v1=source_d1r9_v1.expanduser().resolve(),
        source_d1r9_v2=source_d1r9_v2.expanduser().resolve(),
        source_d1r10_run=source_d1r10_run.expanduser().resolve(),
        source_d1r10_audit=source_d1r10_audit.expanduser().resolve(),
        paths=_paths(run_dir),
    )


def build_context_table(ctx: Context) -> list[dict[str, Any]]:
    table = copy.deepcopy(s21.build_context_table(ctx.base_ctx))
    counts = Counter(str(row["partition"]) for row in table)
    if len(table) != 40 or counts != {"training": 24, "calibration": 8, "holdout": 8}:
        raise ValueError("S24 source context table changed")
    return table


def build_specs(ctx: Context, table: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    source_specs = s21.build_specs(ctx.base_ctx, table)
    source_baselines = {
        (str(row["pair_id"]), str(row["history_member"])): row
        for row in source_specs
        if str(row["r3c3_probe_id"]) == s21.BASELINE_PROBE_ID
    }
    requested = _requested_matrix(ctx.cfg)
    output: list[dict[str, Any]] = []
    for context in table:
        key = (str(context["pair_id"]), str(context["history_member"]))
        source = source_baselines[key]
        staged: list[dict[str, Any]] = []
        for sequence_index in [-1, *range(24)]:
            baseline = sequence_index < 0
            row = np.zeros(16) if baseline else requested[sequence_index]
            identity = {
                "stage": STAGE,
                "campaign_identity": CAMPAIGN_IDENTITY,
                "partition": context["partition"],
                "pair_id": context["pair_id"],
                "history_member": context["history_member"],
                "state_generation_experiment_id": context["state_generation_experiment_id"],
                "snapshot_manifest_digest": context["restart_snapshot_manifest_digest"],
                "target_id": context["target_id"],
                "delay": context["action_delay_steps"],
                "slew": context["slew_scale"],
                "sequence_index": sequence_index,
                "controller_revision": CONTROLLER_REVISION,
            }
            experiment_id = s21.s16.s9.t11.t1.r3c3._scenario_digest(identity)
            spec = copy.deepcopy(source)
            action_by_step = transition.requested_action_by_step(row, ctx.cfg["schedule_contract"])
            spec.update(
                {
                    "kind": "stage4_2r3c3t13s24d1r11_full_replacement_sequential_transition_identification",
                    "stage": STAGE,
                    "campaign_identity": CAMPAIGN_IDENTITY,
                    "controller_revision": CONTROLLER_REVISION,
                    "experiment_id": experiment_id,
                    "phase": "prospective_partitioned_full_replacement_sequential_transition_identification",
                    "category": "identification_only_causal_recursive_transition_full_replacement",
                    "environment_variant": f"stage4_2r3c3t13s24d1r11_{experiment_id}",
                    "baseline_experiment_id": "",
                    "r3c3_probe_id": s21.BASELINE_PROBE_ID,
                    "r3c3_probe_window": "baseline",
                    "r3c3_probe_direction": "",
                    "r3c3_probe_sign": 0,
                    "r3c3_probe_issue_step": -1,
                    "r3c3_probe_cancel_step": -1,
                    "r3c3_probe_first_effect_state": -1,
                    "r3c3_probe_cancel_effect_state": -1,
                    "s24_role": "baseline" if baseline else "sequential_response",
                    "s24_sequence_index": sequence_index,
                    "s24_requested_matrix_row": row.tolist(),
                    "s24_requested_action_by_task_step": {
                        str(step): value.tolist() for step, value in sorted(action_by_step.items())
                    },
                    "s24_schedule_digest": _digest(requested.tolist()),
                    "s24_model_predictor_label_access": False,
                    "probe_trajectory_allowed_in_expert_dataset": False,
                    "pair_or_history_label_available_to_controller": False,
                    "partition_label_available_to_controller": False,
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
                }
            )
            staged.append(spec)
        baseline_id = str(staged[0]["experiment_id"])
        for spec in staged:
            spec["baseline_experiment_id"] = "" if spec["s24_role"] == "baseline" else baseline_id
            output.append(spec)
    if len(output) != 1000 or len({str(row["experiment_id"]) for row in output}) != 1000:
        raise ValueError("S24 spec identity coverage changed")
    counts = Counter(str(row["partition"]) for row in output)
    if counts != {"training": 600, "calibration": 200, "holdout": 200}:
        raise ValueError("S24 partition rollout coverage changed")
    return output


def _partition_specs(
    specs: Sequence[Mapping[str, Any]], partition: str, *, baseline: bool
) -> list[dict[str, Any]]:
    output = [
        copy.deepcopy(dict(spec))
        for spec in specs
        if str(spec["partition"]) == partition
        and (str(spec["s24_role"]) == "baseline") == baseline
    ]
    expected = {
        ("training", True): 24,
        ("training", False): 576,
        ("calibration", True): 8,
        ("calibration", False): 192,
        ("holdout", True): 8,
        ("holdout", False): 192,
    }[(partition, baseline)]
    if len(output) != expected:
        raise ValueError("S24 phase spec coverage changed")
    return output


def _payload(ctx: Context, spec: Mapping[str, Any]) -> dict[str, Any]:
    proxy = SimpleNamespace(
        base_ctx=ctx.base_ctx.base_ctx,
        paths=ctx.paths,
        cfg=ctx.base_ctx.cfg,
    )
    payload = s21._payload(proxy, spec)
    experiment_id = str(spec["experiment_id"])
    payload.update(
        {
            "variant_id": f"stage4_2r3c3t13s24d1r11_{experiment_id}",
            "stage4_2r3c3t13s24_restart_snapshot_dir": str(spec["restart_snapshot_dir"]),
            "stage4_2r3c3t13s24_snapshot_manifest_digest": str(
                spec["restart_snapshot_manifest_digest"]
            ),
            "stage4_2r3c3t13s24_pair_history_partition_label_available_to_controller": False,
        }
    )
    _write_json(ctx.paths.variants / f"payload_{experiment_id}.json", payload)
    return payload


def _library_bundle_selector(ctx: Context):
    return s21._library_bundle_selector(ctx.base_ctx)


class SequentialAmplitudeCodedProbeController(s21.CumulativeExactCard15ProbeController):
    """S21 causal prefix followed by four exact issue/cancel action pairs."""

    def __init__(
        self,
        base_worker: Any,
        bundle: Mapping[str, Any],
        source_spec: Mapping[str, Any],
        initial_state: Mapping[str, Any],
        lattice_cfg: Mapping[str, Any],
        calibration_cfg: Mapping[str, Any],
        dynamic_cfg: Mapping[str, Any],
        schedule_cfg: Mapping[str, Any],
    ):
        super().__init__(
            base_worker,
            bundle,
            source_spec,
            initial_state,
            lattice_cfg,
            calibration_cfg,
            dynamic_cfg,
        )
        self.schedule_cfg = copy.deepcopy(dict(schedule_cfg))
        self.sequence_index = int(source_spec["s24_sequence_index"])
        self.requested_row = np.asarray(source_spec["s24_requested_matrix_row"], dtype=float)
        self.requested_by_step = {
            int(step): np.asarray(value, dtype=float)
            for step, value in source_spec["s24_requested_action_by_task_step"].items()
        }
        self.issue_steps = tuple(map(int, schedule_cfg["issue_task_steps"]))
        self.cancel_steps = tuple(map(int, schedule_cfg["cancel_task_steps"]))
        self._active_issue: dict[str, Any] | None = None

    def _basis_current(self) -> tuple[np.ndarray, np.ndarray]:
        if set(self._fixed_basis_delta) != {0, 1, 2, 3}:
            raise ValueError("S24 fixed physical basis columns changed")
        fields = np.column_stack(
            [
                np.asarray(
                    [float(value) for value in self._fixed_basis_delta[column]],
                    dtype=float,
                )
                for column in range(4)
            ]
        )
        turns = np.asarray(self.turns_tsc, dtype=float)
        if fields.shape != (N_COILS, 4) or turns.shape != (N_COILS,):
            raise ValueError("S24 fixed physical basis shape changed")
        return fields, fields * 1000.0 / turns[:, None]

    def _issue(
        self, slot: int, currents: np.ndarray, baseline_action: np.ndarray
    ) -> tuple[np.ndarray, dict[str, Any]]:
        self._freeze_fixed_basis(currents, baseline_action)
        center = self.actuator.apply(currents, baseline_action)
        desired_coordinate = self.requested_by_step[self.issue_steps[slot]]
        field_basis, current_basis = self._basis_current()
        desired_field = field_basis @ desired_coordinate
        target_fields, actual_decimal, integer_counts = s21._dynamic_exact_target(
            center.card15_fields,
            tuple(Decimal(str(value)) for value in desired_field),
            search_radius=int(self.schedule_cfg["dynamic_exact_search_radius"]),
        )
        chosen = s21.s16.s9.exact_stored_center_action(
            stored_fields=target_fields,
            measured_current_a_tsc=currents,
            baseline_action_norm_tsc=baseline_action,
            turns_tsc=self.turns_tsc,
            max_slew_step_a=float(self.base.max_delta_a),
            minimum_current_a_tsc=self.base.min_current,
            maximum_current_a_tsc=self.base.max_current,
            cfg=self.lattice_cfg,
        )
        issued = self.actuator.apply(currents, chosen["action_norm_tsc"])
        actual_field = np.asarray([float(value) for value in actual_decimal], dtype=float)
        actual_current = actual_field * 1000.0 / np.asarray(self.turns_tsc, dtype=float)
        desired_current = current_basis @ desired_coordinate
        coordinate = np.linalg.lstsq(current_basis, actual_current, rcond=None)[0]
        reconstructed = current_basis @ coordinate
        desired_norm = float(np.linalg.norm(desired_current))
        actual_norm = float(np.linalg.norm(actual_current))
        cosine = float(
            np.dot(desired_current, actual_current)
            / max(desired_norm * actual_norm, 1e-300)
        )
        off_basis = float(
            np.linalg.norm(actual_current - reconstructed) / max(actual_norm, 1e-300)
        )
        coordinate_error = float(np.max(np.abs(coordinate - desired_coordinate)))
        minimum_active = float(np.min(np.abs(coordinate)))
        criteria = {
            "finite": bool(
                np.all(np.isfinite(coordinate))
                and np.all(np.isfinite(actual_field))
                and math.isfinite(cosine)
                and math.isfinite(off_basis)
            ),
            "center_exact": all(len(field) == 10 for field in center.card15_fields),
            "target_exact": all(len(field) == 10 for field in target_fields),
            "target_reproduction": list(issued.card15_fields) == list(target_fields),
            "no_saturation": not any(issued.action_saturated),
            "no_current_clip": not any(issued.current_limit_clipped),
            "active_sign": bool(np.all(np.sign(coordinate) == np.sign(desired_coordinate))),
            "minimum_active": minimum_active
            >= float(self.schedule_cfg["minimum_active_absolute_coordinate"]) - 1e-12,
            "coordinate_error": coordinate_error
            <= float(self.schedule_cfg["maximum_absolute_coordinate_error"]) + 1e-12,
            "cosine": cosine
            >= float(self.schedule_cfg["minimum_desired_applied_current_cosine"]) - 1e-12,
            "off_basis": off_basis
            <= float(self.schedule_cfg["maximum_relative_off_basis_residual"]) + 1e-12,
            "incremental_action": float(chosen["incremental_normalized_action_linf"])
            <= float(self.schedule_cfg["maximum_incremental_normalized_action_linf"])
            + 1e-12,
            "total_action": float(chosen["total_normalized_action_abs"])
            <= float(self.schedule_cfg["maximum_total_normalized_action_abs"]) + 1e-12,
            "current_utilization": float(chosen["predicted_maximum_current_utilization"])
            <= float(self.schedule_cfg["maximum_current_utilization"]) + 1e-12,
            "actuator_gate": bool(chosen["passed"]),
        }
        event = {
            "event": "sequential_issue",
            "slot": slot,
            "task_step": self.step,
            "requested_coordinate": desired_coordinate.tolist(),
            "actual_coordinate": coordinate.tolist(),
            "center_card15_fields": list(center.card15_fields),
            "target_card15_fields": list(target_fields),
            "integer_grid_steps_tsc": list(map(int, integer_counts)),
            "actual_signed_delta_field_kAt_tsc": actual_field.tolist(),
            "maximum_absolute_coordinate_error": coordinate_error,
            "minimum_active_absolute_coordinate": minimum_active,
            "desired_applied_current_cosine": cosine,
            "relative_off_basis_residual": off_basis,
            "incremental_normalized_action_linf": float(
                chosen["incremental_normalized_action_linf"]
            ),
            "total_normalized_action_abs": float(chosen["total_normalized_action_abs"]),
            "predicted_current_utilization": float(
                chosen["predicted_maximum_current_utilization"]
            ),
            "criteria": criteria,
            "passed": bool(all(criteria.values())),
            "actuator_prediction": copy.deepcopy(chosen),
        }
        if not event["passed"]:
            raise ValueError("S24 sequential issue action failed: " + json.dumps(event, sort_keys=True))
        self._active_issue = copy.deepcopy(event)
        return np.asarray(chosen["action_norm_tsc"], dtype=float), event

    def _cancel(
        self, slot: int, currents: np.ndarray, baseline_action: np.ndarray
    ) -> tuple[np.ndarray, dict[str, Any]]:
        if self._active_issue is None or int(self._active_issue["slot"]) != slot:
            raise ValueError("S24 cancellation has no matching causal issue")
        stored_fields = tuple(map(str, self._active_issue["center_card15_fields"]))
        issue_target = tuple(map(str, self._active_issue["target_card15_fields"]))
        chosen = s21.s16.s9.exact_stored_center_action(
            stored_fields=stored_fields,
            measured_current_a_tsc=currents,
            baseline_action_norm_tsc=baseline_action,
            turns_tsc=self.turns_tsc,
            max_slew_step_a=float(self.base.max_delta_a),
            minimum_current_a_tsc=self.base.min_current,
            maximum_current_a_tsc=self.base.max_current,
            cfg=self.lattice_cfg,
        )
        cancelled = self.actuator.apply(currents, chosen["action_norm_tsc"])
        exact_zero = all(
            (s21.s16.s9._decimal_field(target) - s21.s16.s9._decimal_field(center))
            + (s21.s16.s9._decimal_field(center) - s21.s16.s9._decimal_field(target))
            == 0
            for center, target in zip(stored_fields, issue_target)
        )
        criteria = {
            "target_exact": list(cancelled.card15_fields) == list(stored_fields),
            "exact_fields": all(len(field) == 10 for field in stored_fields),
            "exact_zero_target_jump_net": exact_zero,
            "no_saturation": not any(cancelled.action_saturated),
            "no_current_clip": not any(cancelled.current_limit_clipped),
            "incremental_action": float(chosen["incremental_normalized_action_linf"])
            <= float(self.schedule_cfg["maximum_incremental_normalized_action_linf"])
            + 1e-12,
            "online_cancel_margin": float(
                chosen["incremental_normalized_action_linf"]
            )
            <= float(self.schedule_cfg["maximum_online_cancel_incremental_linf"])
            + 1e-12,
            "total_action": float(chosen["total_normalized_action_abs"])
            <= float(self.schedule_cfg["maximum_total_normalized_action_abs"]) + 1e-12,
            "current_utilization": float(chosen["predicted_maximum_current_utilization"])
            <= float(self.schedule_cfg["maximum_current_utilization"]) + 1e-12,
            "actuator_gate": bool(chosen["passed"]),
        }
        event = {
            "event": "sequential_cancel",
            "slot": slot,
            "task_step": self.step,
            "requested_coordinate": self.requested_by_step[self.cancel_steps[slot]].tolist(),
            "stored_center_card15_fields": list(stored_fields),
            "issue_target_card15_fields": list(issue_target),
            "incremental_normalized_action_linf": float(
                chosen["incremental_normalized_action_linf"]
            ),
            "total_normalized_action_abs": float(chosen["total_normalized_action_abs"]),
            "predicted_current_utilization": float(
                chosen["predicted_maximum_current_utilization"]
            ),
            "criteria": criteria,
            "passed": bool(all(criteria.values())),
            "actuator_prediction": copy.deepcopy(chosen),
        }
        if not event["passed"]:
            raise ValueError("S24 sequential cancel action failed: " + json.dumps(event, sort_keys=True))
        self._active_issue = None
        return np.asarray(chosen["action_norm_tsc"], dtype=float), event

    def action(self, current_state: Mapping[str, Any]) -> tuple[np.ndarray, dict[str, Any]]:
        action, trace = super().action(current_state)
        action = np.asarray(action, dtype=float)
        currents = np.asarray(current_state["currents_a_tsc"], dtype=float)
        event: dict[str, Any] = {}
        event_name = "none"
        if self.sequence_index >= 0 and self.step in self.issue_steps:
            slot = self.issue_steps.index(self.step)
            action, event = self._issue(slot, currents, action)
            event_name = "sequential_issue"
        elif self.sequence_index >= 0 and self.step in self.cancel_steps:
            slot = self.cancel_steps.index(self.step)
            action, event = self._cancel(slot, currents, action)
            event_name = "sequential_cancel"
        requested_now = np.asarray(self.requested_by_step.get(self.step, np.zeros(4)), dtype=float)
        trace.update(
            {
                "action_norm_tsc": action.tolist(),
                "r3c3t13s24_identification_only": True,
                "r3c3t13s24_controller_revision": CONTROLLER_REVISION,
                "r3c3t13s24_sequence_index": self.sequence_index,
                "r3c3t13s24_event": event_name,
                "r3c3t13s24_event_detail": event,
                "r3c3t13s24_requested_coordinate_current_step": requested_now.tolist(),
                "r3c3t13s24_pair_history_partition_label_used": False,
                "r3c3t13s24_delay_slew_target_id_label_used": False,
                "r3c3t13s24_source_or_matched_baseline_used": False,
                "r3c3t13s24_future_measurement_used": False,
                "r3c3t13s24_future_executed_action_used": False,
                "r3c3t13s24_hidden_wire_current_used": False,
                "r3c3t13s24_model_predictor_executed": False,
                "r3c3t13s24_schedule_available_to_underlying_controller": False,
            }
        )
        return action, trace


class LocalWorker:
    """One fresh authentic TSC process and S24 controller per rollout."""

    def __init__(
        self,
        payload: dict[str, Any],
        library: dict[str, Any],
        bundle: dict[str, Any],
        worker_id: str,
        selector: dict[str, Any],
        lattice_cfg: dict[str, Any],
        calibration_cfg: dict[str, Any],
        dynamic_cfg: dict[str, Any],
        schedule_cfg: dict[str, Any],
    ):
        self.plant = s21.s16.s9.t11.t1.r1.LocalPlantReplayWorker(
            payload, library, bundle, worker_id, selector
        )
        self.base = self.plant.base_worker
        self.bundle = bundle
        self.lattice_cfg = lattice_cfg
        self.calibration_cfg = calibration_cfg
        self.dynamic_cfg = dynamic_cfg
        self.schedule_cfg = schedule_cfg

    def close(self) -> None:
        self.plant.close()

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        failed = True
        trajectory: list[dict[str, Any]] = []
        trace: list[dict[str, Any]] = []
        result: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "campaign_identity": CAMPAIGN_IDENTITY,
            "controller_revision": CONTROLLER_REVISION,
            "underlying_controller_revision": s21.s16.s9.t11.t1.r3c1.CONTROLLER_REVISION,
            "probe_primitive_revision": CONTROLLER_REVISION,
            "experiment_id": str(spec["experiment_id"]),
            "spec": copy.deepcopy(spec),
            "success": False,
            "completed": False,
            "failure_reason": "",
            "trajectory": trajectory,
            "controller_trace": trace,
        }
        try:
            horizon = int(spec["horizon_steps"])
            if (
                horizon != s21.s13._formal_horizon(float(spec["slew_scale"]))
                or horizon != int(spec["formal_horizon_steps"])
                or horizon != int(self.base.env.max_episode_steps)
            ):
                raise ValueError("S24 formal horizon changed")
            self.base.env.reset()
            zero = np.zeros(N_COILS, dtype=np.float32)
            trajectory.append(
                s21.s16.s9.t11.t1.r1._state_record_full(self.base.env, 0, zero)
            )
            controller = SequentialAmplitudeCodedProbeController(
                self.base,
                self.bundle,
                s21.s16.s9._controller_spec(spec),
                trajectory[0],
                self.lattice_cfg,
                self.calibration_cfg,
                self.dynamic_cfg,
                self.schedule_cfg,
            )
            for step in range(horizon):
                action, controller_row = controller.action(trajectory[-1])
                _, _, terminated, truncated, info = self.base.env.step(action)
                next_state = s21.s16.s9.t11.t1.r1._state_record_full(
                    self.base.env, step + 1, action
                )
                trajectory.append(next_state)
                trace.append(controller_row)
                controller.advance(next_state)
                if terminated:
                    raise RuntimeError(str(info.get("failure_reason", "environment terminated")))
                if truncated and step + 1 < horizon:
                    raise RuntimeError("environment truncated before S24 formal horizon")
            baseline = str(spec["s24_role"]) == "baseline"
            calibration_events = [
                row["r3c3t13s16_lattice_event"]
                for row in trace
                if row["r3c3t13s16_lattice_event"] != "none"
            ]
            expected_calibration = [
                "calibration_issue",
                "calibration_cancel",
                "calibration_issue",
                "calibration_cancel",
                "calibration_issue",
                "calibration_cancel",
                "calibration_issue",
                "calibration_cancel",
            ]
            sequence_events = [
                row["r3c3t13s24_event"]
                for row in trace
                if row["r3c3t13s24_event"] != "none"
            ]
            expected_sequence = [] if baseline else [
                "sequential_issue",
                "sequential_cancel",
                "sequential_issue",
                "sequential_cancel",
                "sequential_issue",
                "sequential_cancel",
                "sequential_issue",
                "sequential_cancel",
            ]
            forbidden_keys = (
                "future_measurement_used",
                "hidden_wire_used",
                "source_action_used",
                "source_coil_current_used",
                "source_wire_current_used",
                "current_run_future_used",
                "pair_or_history_label_used",
                "source_result_used",
                "future_probe_schedule_available_to_underlying_controller",
                "r3c3t13s21_partition_label_used",
                "r3c3t13s24_pair_history_partition_label_used",
                "r3c3t13s24_delay_slew_target_id_label_used",
                "r3c3t13s24_source_or_matched_baseline_used",
                "r3c3t13s24_future_measurement_used",
                "r3c3t13s24_future_executed_action_used",
                "r3c3t13s24_hidden_wire_current_used",
                "r3c3t13s24_schedule_available_to_underlying_controller",
            )
            forbidden = sum(any(bool(row.get(key)) for key in forbidden_keys) for row in trace)
            event_pass = all(
                bool((row.get("r3c3t13s24_event_detail") or {}).get("passed"))
                for row in trace
                if row.get("r3c3t13s24_event") != "none"
            )
            success = bool(
                len(trajectory) == horizon + 1
                and len(trace) == horizon
                and not any(bool(row.get("abnormal")) for row in trajectory)
                and all(
                    bool(row.get("computed_online")) and bool(row.get("solver_success"))
                    for row in trace
                )
                and calibration_events == expected_calibration
                and sequence_events == expected_sequence
                and event_pass
                and forbidden == 0
                and bool(trace[7]["r3c3t13s21_exact_calibration_net_zero"])
                and controller._active_issue is None
            )
            result.update(
                {
                    "success": success,
                    "completed": True,
                    "failure_reason": "" if success else "incomplete or invalid S24 rollout",
                    "hidden_history_control_summary": {
                        "fresh_controller_actor": True,
                        "fresh_tsc_process": True,
                        "full_tsc_hidden_state_loaded_from_sprsina": True,
                        "controller_history_initialization": "current_visible_state_only_at_task_step_zero",
                        "controller_integral_initialization": "zero",
                        "controller_previous_correction_initialization": "zero",
                        "controller_delay_queue_initialization": "authenticated_visible_manifold_phase_aligned_nominal_prime",
                        "reference_phase_start": controller.reference_phase_start,
                        "baseline_controller_revision": s21.s16.s9.t11.t1.r3c1.CONTROLLER_REVISION,
                        "identification_only": True,
                        "sequential_amplitude_coded_identification_only": True,
                        "baseline": baseline,
                        "sequence_index": controller.sequence_index,
                        "calibration_schedule_exact": calibration_events == expected_calibration,
                        "sequential_schedule_exact": sequence_events == expected_sequence,
                        "sequential_action_gates_passed": event_pass,
                        "requested_target_jump_net_zero": True,
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
                        "partition_label_available_to_controller": False,
                        "source_result_used": False,
                    },
                    "wall_time_s": time.time() - started,
                }
            )
            failed = not success
            return s21.s16.s9.t11.t1._json_safe(result)
        except Exception as exc:
            result.update(
                {
                    "success": False,
                    "completed": True,
                    "failure_reason": repr(exc),
                    "trajectory": trajectory,
                    "controller_trace": trace,
                    "traceback": traceback.format_exc(),
                    "wall_time_s": time.time() - started,
                }
            )
            return s21.s16.s9.t11.t1._json_safe(result)
        finally:
            runner = getattr(self.base.env, "runner", None)
            if runner is not None:
                runner.cleanup_episode_workspace(
                    failed=failed,
                    reason="stage4_2r3c3t13s24_sequential_transition_identification",
                )


_RAY_ACTOR = None


def _ray_actor_class():
    global _RAY_ACTOR
    if _RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class Stage42R3C3T13S24Actor:
            def __init__(
                self,
                payload,
                library,
                bundle,
                worker_id,
                selector,
                lattice,
                calibration,
                dynamic,
                schedule,
            ):
                self.worker = LocalWorker(
                    payload,
                    library,
                    bundle,
                    worker_id,
                    selector,
                    lattice,
                    calibration,
                    dynamic,
                    schedule,
                )

            def evaluate(self, spec):
                return self.worker.evaluate(spec)

            def close(self):
                self.worker.close()
                return True

        _RAY_ACTOR = Stage42R3C3T13S24Actor
    return _RAY_ACTOR


def _result_complete(path: Path, spec: Mapping[str, Any]) -> bool:
    if not path.is_file():
        return False
    try:
        result = s21.s16.s9.t11.t1.r3c3.read_json_gz(path)
        horizon = int(spec["horizon_steps"])
        return bool(
            result.get("completed")
            and result.get("success")
            and result.get("stage") == STAGE
            and result.get("campaign_identity") == CAMPAIGN_IDENTITY
            and result.get("controller_revision") == CONTROLLER_REVISION
            and result.get("probe_primitive_revision") == CONTROLLER_REVISION
            and result.get("experiment_id") == spec["experiment_id"]
            and result.get("spec") == dict(spec)
            and len(result.get("trajectory") or []) == horizon + 1
            and len(result.get("controller_trace") or []) == horizon
        )
    except Exception:
        return False


def evaluate_specs(
    ctx: Context, specs: Sequence[dict[str, Any]], *, backend: str, resume: bool
) -> dict[str, Any]:
    ctx.paths.raw.mkdir(parents=True, exist_ok=True)
    pending = [
        spec
        for spec in specs
        if not (
            resume
            and _result_complete(ctx.paths.raw / f"{spec['experiment_id']}.json.gz", spec)
        )
    ]
    payloads = {str(spec["experiment_id"]): _payload(ctx, spec) for spec in specs}
    library, bundle, selector = _library_bundle_selector(ctx)
    lattice = ctx.base_ctx.base_ctx.cfg["lattice_probe"]
    calibration = ctx.base_ctx.base_ctx.cfg["active_calibration"]
    dynamic = ctx.base_ctx.cfg["causal_model"]
    schedule = ctx.cfg["schedule_contract"]
    if backend == "serial":
        for index, spec in enumerate(pending):
            worker = LocalWorker(
                payloads[str(spec["experiment_id"])],
                library,
                bundle,
                f"stage42r3c3t13s24_serial_{index:04d}",
                selector,
                lattice,
                calibration,
                dynamic,
                schedule,
            )
            try:
                result = worker.evaluate(spec)
            finally:
                worker.close()
            _write_json_gz(ctx.paths.raw / f"{spec['experiment_id']}.json.gz", result)
            print(f"[T13S24] {index + 1}/{len(pending)}", flush=True)
    elif backend == "ray" and pending:
        import ray

        plan = s21.s16.ensure_ray_worker_plan(
            ray,
            requested_workers=int(ctx.cfg["parallel"]["n_workers"]),
            pending_tasks=len(pending),
            ray_tmpdir=os.environ.get("RAY_TMPDIR") or ctx.cfg["storage"]["ray_tmpdir"],
            log_prefix="[T13S24]",
        )
        Actor = _ray_actor_class()
        completed = 0
        for batch_start in range(0, len(pending), plan.actor_count):
            batch = pending[batch_start : batch_start + plan.actor_count]
            actors, refs = [], {}
            for offset, spec in enumerate(batch):
                actor = Actor.remote(
                    payloads[str(spec["experiment_id"])],
                    library,
                    bundle,
                    f"stage42r3c3t13s24_{batch_start + offset:04d}",
                    selector,
                    lattice,
                    calibration,
                    dynamic,
                    schedule,
                )
                actors.append(actor)
                refs[actor.evaluate.remote(spec)] = spec
            try:
                while refs:
                    ready, _ = ray.wait(list(refs), num_returns=1, timeout=30.0)
                    if not ready:
                        print(f"[T13S24] waiting {completed}/{len(pending)}", flush=True)
                        continue
                    for ref in ready:
                        spec = refs.pop(ref)
                        try:
                            result = ray.get(ref)
                        except Exception as exc:
                            result = {
                                "schema_version": 1,
                                "stage": STAGE,
                                "campaign_identity": CAMPAIGN_IDENTITY,
                                "controller_revision": CONTROLLER_REVISION,
                                "probe_primitive_revision": CONTROLLER_REVISION,
                                "experiment_id": str(spec["experiment_id"]),
                                "spec": copy.deepcopy(spec),
                                "success": False,
                                "completed": True,
                                "failure_reason": repr(exc),
                                "traceback": traceback.format_exc(),
                                "trajectory": [],
                                "controller_trace": [],
                            }
                        _write_json_gz(
                            ctx.paths.raw / f"{spec['experiment_id']}.json.gz", result
                        )
                        completed += 1
                        print(f"[T13S24] {completed}/{len(pending)}", flush=True)
            finally:
                close_refs = [actor.close.remote() for actor in actors]
                if close_refs:
                    ray.get(close_refs, timeout=float(ctx.cfg["storage"]["actor_close_timeout_s"]))
                for actor in actors:
                    ray.kill(actor, no_restart=True)
    elif backend not in {"serial", "ray"}:
        raise ValueError(f"unsupported S24 backend: {backend}")
    complete = sum(
        _result_complete(ctx.paths.raw / f"{spec['experiment_id']}.json.gz", spec)
        for spec in specs
    )
    return {
        "expected": len(specs),
        "pending_at_start": len(pending),
        "complete_successful": complete,
        "passed": complete == len(specs),
    }


def _authenticate_s21_source(ctx: Context) -> dict[str, Any]:
    source = ctx.cfg["source_contract"]
    paths = ctx.source_s21_ctx.paths
    required = {
        "state": (paths.state, "s21_final_state_sha256"),
        "manifest": (paths.manifest, "s21_manifest_sha256"),
        "final_result": (paths.run_dir / "final_result.json", "s21_final_result_sha256"),
        "independent_postprocess": (
            paths.run_dir / "server_independent_postprocess.json",
            "s21_independent_postprocess_sha256",
        ),
        "final_audit": (paths.run_dir / "server_final_audit.json", "s21_final_audit_sha256"),
        "training_model": (
            paths.model / "training_pooled_observer.json",
            "s21_training_model_sha256",
        ),
        "calibrated_tube": (
            paths.model / "calibrated_response_tube.json",
            "s21_calibrated_tube_sha256",
        ),
    }
    hashes = {}
    for name, (path, key) in required.items():
        if not path.is_file():
            raise ValueError(f"S24 immutable S21 {name} missing")
        hashes[name] = _sha256(path)
        if hashes[name] != str(source[key]):
            raise ValueError(f"S24 immutable S21 {name} hash changed")
    state = _read_json(paths.state)
    final = _read_json(paths.run_dir / "final_result.json")
    independent = _read_json(paths.run_dir / "server_independent_postprocess.json")
    audit = _read_json(paths.run_dir / "server_final_audit.json")
    inventory = s21._raw_inventory(ctx.source_s21_ctx)
    parse_count = success_count = 0
    for path in sorted(paths.raw.glob("*.json.gz")):
        result = s21.s16.s9.t11.t1.r3c3.read_json_gz(path)
        parse_count += 1
        success_count += int(bool(result.get("success") and result.get("completed")))
    passed = bool(
        state.get("finished")
        and state.get("phase_status") == "campaign_complete"
        and state.get("primary_pass")
        and final.get("passed")
        and independent.get("passed")
        and audit.get("passed")
        and int(inventory["count"]) == int(source["s21_raw_count"]) == 360
        and int(inventory["total_bytes"]) == int(source["s21_raw_total_bytes"])
        and str(inventory["digest"]) == str(source["s21_raw_inventory_digest"])
        and parse_count == success_count == 360
        and int(final.get("forbidden_predictor_input_count", -1))
        == int(source["s21_forbidden_predictor_input_count"])
    )
    if not passed:
        raise ValueError("S24 immutable S21 source authentication failed")
    return {
        "run_dir": str(paths.run_dir),
        "hashes": hashes,
        "raw_count": int(inventory["count"]),
        "raw_total_bytes": int(inventory["total_bytes"]),
        "raw_inventory_digest": str(inventory["digest"]),
        "raw_strict_parse_count": parse_count,
        "raw_complete_success_count": success_count,
        "passed": True,
    }


def _authenticate_s23r1(ctx: Context) -> dict[str, Any]:
    source = ctx.cfg["source_contract"]
    root = ctx.source_s23r1_output
    paths = {
        "detailed": root / "stage4_2r3c3t13s23r1_amplitude_coded_preflight_v1.json",
        "summary": root / "stage4_2r3c3t13s23r1_summary_v1.json",
        "manifest": root / "stage4_2r3c3t13s23r1_manifest_v1.json",
    }
    expected = {
        "detailed": str(source["s23r1_detailed_sha256"]),
        "summary": str(source["s23r1_summary_sha256"]),
        "manifest": str(source["s23r1_manifest_sha256"]),
    }
    hashes = {}
    for key, path in paths.items():
        if not path.is_file():
            raise ValueError(f"S24 immutable S23R1 {key} missing")
        hashes[key] = _sha256(path)
        if hashes[key] != expected[key]:
            raise ValueError(f"S24 immutable S23R1 {key} hash changed")
    detailed, summary, manifest = (_read_json(paths[key]) for key in ("detailed", "summary", "manifest"))
    chain = detailed.get("source_authentication") or {}
    s22_auth = chain.get("s22") or {}
    s23_auth = chain.get("s23") or {}
    d1_auth = chain.get("s23d1") or {}
    passed = bool(
        detailed.get("primary_pass")
        and summary.get("primary_pass")
        and detailed.get("route") == source["s23r1_route"]
        and summary.get("route") == source["s23r1_route"]
        and int(summary.get("source_raw_authentication_count", -1)) == 360
        and int(summary.get("issue_gate_pass", -1)) == 3840
        and int(summary.get("cancellation_gate_pass", -1)) == 3840
        and int(summary.get("finite_constructions", -1)) == 7680
        and int(summary.get("central_sign_gate_pass", -1)) == 1280
        and bool(manifest.get("pass_authorizes_s24_design_only"))
        and not bool(manifest.get("ray_gotsc_tsc_plant_or_controller_executed"))
        and str((s22_auth.get("hashes") or {}).get("summary"))
        == str(source["s22_summary_sha256"])
        and str(s23_auth.get("route")) == str(source["s23_route"])
        and str((s23_auth.get("hashes") or {}).get("summary"))
        == str(source["s23_summary_sha256"])
        and str(d1_auth.get("route")) == str(source["s23d1_route"])
        and str((d1_auth.get("hashes") or {}).get("summary"))
        == str(source["s23d1_summary_sha256"])
    )
    if not passed:
        raise ValueError("S24 immutable S23R1 authentication failed")
    return {
        "output_dir": str(root),
        "hashes": hashes,
        "provenance_digest": str(detailed["provenance_digest"]),
        "route": str(detailed["route"]),
        "passed": True,
    }


def _raw_inventory_dir(raw_dir: Path, *, strict_parse: bool) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    digest = hashlib.sha256()
    parse_count = 0
    for path in sorted(raw_dir.glob("*.json.gz")):
        sha = _sha256(path)
        size = path.stat().st_size
        digest.update(f"{path.name}\0{size}\0{sha}\n".encode())
        if strict_parse:
            with gzip.open(path, "rt", encoding="utf-8") as stream:
                json.load(
                    stream,
                    parse_constant=lambda value: (_ for _ in ()).throw(
                        ValueError(value)
                    ),
                )
            parse_count += 1
        rows.append({"path": path.name, "bytes": size, "sha256": sha})
    return {
        "count": len(rows),
        "total_bytes": sum(int(row["bytes"]) for row in rows),
        "digest": digest.hexdigest(),
        "strict_parse_count": parse_count,
    }


def _authenticate_s24_source(ctx: Context) -> dict[str, Any]:
    source = ctx.cfg["source_contract"]
    stage = ctx.source_s24_run / "stage4_2r3c3t13s24_sequential_transition_identification"
    files = {
        "state": stage / "stage_state.json",
        "manifest": stage / "stage_manifest.json",
        "training_gate": stage / "analysis/training_sequence_gate.json",
        "all_specs": stage / "specs/all_specs.json",
        "implementation": _project_root()
        / "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24_sequential_transition_identification.py",
    }
    expected = {
        "state": source["s24_state_sha256"],
        "manifest": source["s24_manifest_sha256"],
        "training_gate": source["s24_training_gate_sha256"],
        "implementation": source["s24_implementation_sha256"],
    }
    hashes: dict[str, str] = {}
    for key, path in files.items():
        if not path.is_file():
            raise ValueError(f"D1R11 immutable S24 {key} missing")
        hashes[key] = _sha256(path)
        if key in expected and hashes[key] != str(expected[key]):
            raise ValueError(f"D1R11 immutable S24 {key} hash changed")
    inventory = _raw_inventory_dir(stage / "raw", strict_parse=True)
    if (
        inventory["count"] != int(source["s24_raw_count"])
        or inventory["total_bytes"] != int(source["s24_raw_total_bytes"])
        or inventory["digest"] != str(source["s24_raw_inventory_digest"])
    ):
        raise ValueError("D1R11 immutable S24 raw inventory changed")
    state = _read_json(files["state"])
    gate = _read_json(files["training_gate"])
    specs = _read_json(files["all_specs"])
    if (
        state.get("stage") != "Stage4.2R3c3T13S24"
        or not bool(state.get("finished"))
        or int(state.get("new_raw_count", -1)) != 600
        or gate.get("stage") != "Stage4.2R3c3T13S24"
        or bool(gate.get("passed"))
        or len(specs) != 1000
        or len({str(row["experiment_id"]) for row in specs}) != 1000
    ):
        raise ValueError("D1R11 immutable S24 identity or terminal boundary changed")
    return {
        "run": str(ctx.source_s24_run),
        "hashes": hashes,
        "raw_inventory": inventory,
        "spec_count": len(specs),
        "passed": True,
    }


def _authenticate_d1r9(ctx: Context) -> dict[str, Any]:
    source = ctx.cfg["source_contract"]
    names = (
        "stage4_2r3c3t13s24d1r9_central_row_replacement_preflight_v1.json",
        "stage4_2r3c3t13s24d1r9_d1r10_candidate_specs_v1.json",
        "stage4_2r3c3t13s24d1r9_independent_forensics_v1.json",
        "stage4_2r3c3t13s24d1r9_manifest_v1.json",
        "stage4_2r3c3t13s24d1r9_summary_v1.json",
    )
    hashes: dict[str, str] = {}
    for name in names:
        left = ctx.source_d1r9_v1 / name
        right = ctx.source_d1r9_v2 / name
        if not left.is_file() or not right.is_file():
            raise ValueError(f"D1R11 immutable D1R9 output missing: {name}")
        left_sha, right_sha = _sha256(left), _sha256(right)
        if left_sha != right_sha or left.read_bytes() != right.read_bytes():
            raise ValueError(f"D1R11 D1R9 official outputs differ: {name}")
        hashes[name] = left_sha
    detailed_path = ctx.source_d1r9_v1 / names[0]
    independent_path = ctx.source_d1r9_v1 / names[2]
    if (
        hashes[names[0]] != str(source["d1r9_detailed_sha256"])
        or hashes[names[2]] != str(source["d1r9_independent_sha256"])
    ):
        raise ValueError("D1R11 immutable D1R9 hashes changed")
    detailed = _read_json(detailed_path)
    independent = _read_json(independent_path)
    selection = detailed.get("selection") or {}
    matrix = _requested_matrix(ctx.cfg)
    if (
        detailed.get("route") != source["d1r9_route"]
        or not bool(detailed.get("passed"))
        or not bool(independent.get("passed"))
        or str(selection.get("requested_matrix_digest"))
        != str(source["d1r9_requested_matrix_digest"])
        or str(selection.get("source_matrix_digest"))
        != str(source["s24_source_matrix_digest"])
        or selection.get("changed_matrix_row_indices") != [22]
        or selection.get("contradicted_matrix_row_indices") != []
        or selection.get("unknown_matrix_row_indices") != [3, 7, 11, 15, 20, 21, 22]
        or _digest(selection.get("requested_matrix")) != _digest(matrix.tolist())
    ):
        raise ValueError("D1R11 immutable D1R9 selection authentication failed")
    return {
        "v1": str(ctx.source_d1r9_v1),
        "v2": str(ctx.source_d1r9_v2),
        "file_hashes": hashes,
        "requested_matrix_digest": _digest(matrix.tolist()),
        "byte_identical_file_count": len(names),
        "passed": True,
    }


def _authenticate_d1r10(ctx: Context) -> dict[str, Any]:
    source = ctx.cfg["source_contract"]
    stage = (
        ctx.source_d1r10_run
        / "stage4_2r3c3t13s24d1r10_exact_row_completion_safety_sentinel"
    )
    final_path = stage / "final_result.json"
    if not final_path.is_file() or not ctx.source_d1r10_audit.is_file():
        raise ValueError("D1R11 immutable D1R10 result or audit missing")
    if (
        _sha256(final_path) != str(source["d1r10_final_result_sha256"])
        or _sha256(ctx.source_d1r10_audit)
        != str(source["d1r10_independent_audit_sha256"])
    ):
        raise ValueError("D1R11 immutable D1R10 result or audit hash changed")
    inventory = _raw_inventory_dir(stage / "raw", strict_parse=True)
    final = _read_json(final_path)
    audit = _read_json(ctx.source_d1r10_audit)
    if (
        inventory["count"] != int(source["d1r10_raw_count"])
        or inventory["total_bytes"] != int(source["d1r10_raw_total_bytes"])
        or inventory["digest"] != str(source["d1r10_raw_inventory_digest"])
        or final.get("route") != source["d1r10_route"]
        or not bool(final.get("passed"))
        or not bool(audit.get("passed"))
        or audit.get("route") != source["d1r10_route"]
        or int(audit.get("strict_parse_count", -1)) != 126
        or int(audit.get("full_pass_count", -1)) != 126
        or int(audit.get("runtime_or_audit_failure_count", -1)) != 0
    ):
        raise ValueError("D1R11 immutable D1R10 raw acceptance changed")
    return {
        "run": str(ctx.source_d1r10_run),
        "audit": str(ctx.source_d1r10_audit),
        "final_result_sha256": _sha256(final_path),
        "independent_audit_sha256": _sha256(ctx.source_d1r10_audit),
        "raw_inventory": inventory,
        "passed": True,
    }


def _prior_identity_audit(specs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    requested = {f"{row['experiment_id']}.json.gz" for row in specs}
    prior_names: set[str] = set()
    scanned = 0
    for path in _project_root().glob("*_runs/**/raw/*.json.gz"):
        scanned += 1
        prior_names.add(path.name)
    overlap = sorted(requested & prior_names)
    if overlap:
        raise ValueError("D1R11 new identities overlap prior raw: " + ",".join(overlap[:5]))
    return {
        "new_identity_count": len(requested),
        "prior_raw_file_count_scanned": scanned,
        "overlap_count": 0,
        "passed": True,
    }


def _prepare_dirs(paths: Paths) -> None:
    for path in (
        paths.run_dir,
        paths.stage_dir,
        paths.variants,
        paths.specs,
        paths.source_reference,
        paths.raw,
        paths.analysis,
        paths.model,
    ):
        path.mkdir(parents=True, exist_ok=True)


def prepare_offline(ctx: Context) -> dict[str, Any]:
    if (
        ctx.paths.state.exists()
        or ctx.paths.manifest.exists()
        or ctx.paths.stage_dir.exists()
    ):
        raise ValueError("S24 offline requires a fresh run identity")
    s21_auth = _authenticate_s21_source(ctx)
    s23r1_auth = _authenticate_s23r1(ctx)
    s24_auth = _authenticate_s24_source(ctx)
    d1r9_auth = _authenticate_d1r9(ctx)
    d1r10_auth = _authenticate_d1r10(ctx)
    table = build_context_table(ctx)
    specs = build_specs(ctx, table)
    prior_identity = _prior_identity_audit(specs)
    snapshots = s21._snapshot_audit(table)
    package = s21._package_fingerprint()
    requested = _requested_matrix(ctx.cfg)
    if not snapshots["passed"] or int(snapshots["pass_count"]) != 40:
        raise ValueError("S24 source snapshot authentication failed")
    _prepare_dirs(ctx.paths)
    context_digest, spec_digest = _digest(table), _digest(specs)
    if spec_digest != str(ctx.cfg["source_contract"]["ordered_spec_digest"]):
        raise ValueError("D1R11 prospective ordered spec digest changed")
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": str(ctx.cfg["package_revision"]),
        "config_path": str(ctx.config_path),
        "config_sha256": _sha256(ctx.config_path),
        "design_document_sha256": str(ctx.cfg["design_document_sha256"]),
        "s21_source_authentication": s21_auth,
        "s23r1_source_authentication": s23r1_auth,
        "s24_source_authentication": s24_auth,
        "d1r9_source_authentication": d1r9_auth,
        "d1r10_source_authentication": d1r10_auth,
        "prior_raw_identity_audit": prior_identity,
        "context_count": 40,
        "context_table_digest": context_digest,
        "spec_count": 1000,
        "spec_digest": spec_digest,
        "requested_matrix_digest": _digest(requested.tolist()),
        "snapshot_pass_count": int(snapshots["pass_count"]),
        "package_fingerprint": package,
        "training_model_hashed_before_calibration": True,
        "calibrated_tube_hashed_before_holdout": True,
        "formal_timing_unchanged": True,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "bc_dagger_or_rl_allowed": False,
    }
    state = {
        "schema_version": 1,
        "stage": STAGE,
        "phase_status": "offline_ready",
        "finished": False,
        "primary_pass": False,
        "real_tsc_executed": False,
        "new_raw_count": 0,
        "context_table_digest": context_digest,
        "spec_digest": spec_digest,
        "package_digest": package["digest"],
        "training_model_sha256": "",
        "calibrated_tube_sha256": "",
        "heldout_outcomes_opened": False,
        "stop_reason": "",
        "verdict": {},
    }
    _write_json(ctx.paths.manifest, manifest)
    _write_json(ctx.paths.state, state)
    _write_json(ctx.paths.source_reference / "context_table.json", table)
    _write_json(ctx.paths.source_reference / "s21_authentication.json", s21_auth)
    _write_json(ctx.paths.source_reference / "s23r1_authentication.json", s23r1_auth)
    _write_json(ctx.paths.source_reference / "s24_authentication.json", s24_auth)
    _write_json(ctx.paths.source_reference / "d1r9_authentication.json", d1r9_auth)
    _write_json(ctx.paths.source_reference / "d1r10_authentication.json", d1r10_auth)
    _write_json(ctx.paths.source_reference / "prior_raw_identity_audit.json", prior_identity)
    _write_json(ctx.paths.source_reference / "snapshot_audit.json", snapshots)
    _write_json(ctx.paths.specs / "all_specs.json", specs)
    for partition in ("training", "calibration", "holdout"):
        for baseline in (True, False):
            name = "baseline" if baseline else "sequence"
            _write_json(
                ctx.paths.specs / f"{partition}_{name}_specs.json",
                _partition_specs(specs, partition, baseline=baseline),
            )
    output = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "zero_plant_offline_preflight",
        "context_count": 40,
        "spec_count": 1000,
        "training_rollouts": 600,
        "calibration_rollouts": 200,
        "holdout_rollouts": 200,
        "snapshot_pass_count": int(snapshots["pass_count"]),
        "requested_matrix_rank": int(np.linalg.matrix_rank(requested)),
        "new_raw_count": 0,
        "real_tsc_executed": False,
        "passed": True,
    }
    _write_json(ctx.paths.analysis / "offline_preflight.json", output)
    return output


def _require_phase(ctx: Context, phase: str) -> dict[str, Any]:
    state = _read_json(ctx.paths.state)
    if state.get("phase_status") != phase or bool(state.get("finished")):
        raise ValueError(f"S24 expected open phase {phase}")
    return state


def _set_state(ctx: Context, **updates: Any) -> dict[str, Any]:
    state = _read_json(ctx.paths.state)
    state.update(updates)
    _write_json(ctx.paths.state, state)
    return state


def _all_specs(ctx: Context) -> list[dict[str, Any]]:
    saved = _read_json(ctx.paths.specs / "all_specs.json")
    rebuilt = build_specs(ctx, build_context_table(ctx))
    if _digest(saved) != _digest(rebuilt):
        raise ValueError("S24 frozen spec matrix changed")
    return saved


def _execution_audit(
    ctx: Context, specs: Sequence[Mapping[str, Any]], *, baseline: bool
) -> dict[str, Any]:
    state_map = s21.s13._source_state_map(ctx.base_ctx.base_ctx.base_ctx)
    base_source_ctx = (
        ctx.base_ctx.base_ctx.base_ctx.base_ctx.base_ctx.base_ctx.source_ctx.source_ctx
    )
    forbidden_keys = (
        "future_measurement_used",
        "hidden_wire_used",
        "source_action_used",
        "source_coil_current_used",
        "source_wire_current_used",
        "current_run_future_used",
        "pair_or_history_label_used",
        "source_result_used",
        "future_probe_schedule_available_to_underlying_controller",
        "r3c3t13s21_partition_label_used",
        "r3c3t13s24_pair_history_partition_label_used",
        "r3c3t13s24_delay_slew_target_id_label_used",
        "r3c3t13s24_source_or_matched_baseline_used",
        "r3c3t13s24_future_measurement_used",
        "r3c3t13s24_future_executed_action_used",
        "r3c3t13s24_hidden_wire_current_used",
        "r3c3t13s24_schedule_available_to_underlying_controller",
    )
    rows = []
    for spec in specs:
        path = ctx.paths.raw / f"{spec['experiment_id']}.json.gz"
        if not _result_complete(path, spec):
            rows.append(
                {
                    "experiment_id": spec["experiment_id"],
                    "passed": False,
                    "failure_class": "runtime_or_raw_error",
                    "failure_reason": "missing or incomplete successful raw",
                }
            )
            continue
        result = s21.s16.s9.t11.t1.r3c3.read_json_gz(path)
        trajectory, trace = result["trajectory"], result["controller_trace"]
        payload = _payload(ctx, spec)
        currents = np.asarray([row["currents_a_tsc"] for row in trajectory], dtype=float)
        actions = np.asarray([row["action_norm_tsc"] for row in trace], dtype=float)
        recorded_actions = np.asarray(
            [row["action_norm_tsc"] for row in trajectory[1:]], dtype=float
        )
        minimum, maximum = s21.s13._current_limits_tsc(payload)
        center, half = 0.5 * (minimum + maximum), 0.5 * (maximum - minimum)
        utilization = float(np.max(np.abs((currents - center) / half)))
        restart = s21.s16.s9.t11.t1.r3b._control_row(
            base_source_ctx,
            result,
            state_map[str(spec["state_generation_experiment_id"])],
        )
        phase = s21.s16.s9.t11.t1.r3c1._phase_trace_valid(result)
        calibration = s21._dynamic_calibration_trace_audit(result, ctx.base_ctx.cfg)
        calibration_events = [
            row.get("r3c3t13s16_lattice_event")
            for row in trace
            if row.get("r3c3t13s16_lattice_event") != "none"
        ]
        sequence_events = [
            row.get("r3c3t13s24_event")
            for row in trace
            if row.get("r3c3t13s24_event") != "none"
        ]
        expected_calibration = [
            "calibration_issue",
            "calibration_cancel",
            "calibration_issue",
            "calibration_cancel",
            "calibration_issue",
            "calibration_cancel",
            "calibration_issue",
            "calibration_cancel",
        ]
        expected_sequence = [] if baseline else [
            "sequential_issue",
            "sequential_cancel",
            "sequential_issue",
            "sequential_cancel",
            "sequential_issue",
            "sequential_cancel",
            "sequential_issue",
            "sequential_cancel",
        ]
        event_details = [
            row["r3c3t13s24_event_detail"]
            for row in trace
            if row.get("r3c3t13s24_event") != "none"
        ]
        forbidden = sum(any(bool(row.get(key)) for key in forbidden_keys) for row in trace)
        runtime = bool(
            result["success"]
            and len(trajectory) == int(spec["horizon_steps"]) + 1
            and len(trace) == int(spec["horizon_steps"])
            and np.all(np.isfinite(currents))
            and np.all(np.isfinite(actions))
            and not any(bool(row.get("abnormal")) for row in trajectory)
        )
        restart_pass = bool(
            restart.get("fresh_controller")
            and restart.get("fresh_tsc_process")
            and restart.get("initial_restart_exact")
            and restart.get("controller_trace_causal")
        )
        trace_pass = bool(
            all(
                bool(row.get("computed_online")) and bool(row.get("solver_success"))
                for row in trace
            )
            and calibration_events == expected_calibration
            and sequence_events == expected_sequence
            and all(bool(row.get("passed")) for row in event_details)
            and forbidden == 0
            and bool(phase["passed"])
            and np.array_equal(actions, recorded_actions)
            and float(np.max(np.abs(actions))) <= 1.0 + 1e-12
        )
        passed = bool(
            runtime
            and restart_pass
            and trace_pass
            and calibration["passed"]
            and utilization
            <= float(ctx.cfg["schedule_contract"]["maximum_current_utilization"])
            + 1e-12
        )
        rows.append(
            {
                "experiment_id": spec["experiment_id"],
                "pair_id": spec["pair_id"],
                "history_member": spec["history_member"],
                "partition": spec["partition"],
                "role": spec["s24_role"],
                "sequence_index": int(spec["s24_sequence_index"]),
                "runtime_pass": runtime,
                "restart_pass": restart_pass,
                "causality_schedule_action_pass": trace_pass,
                "calibration_pass": bool(calibration["passed"]),
                "sequential_event_pass_count": sum(
                    bool(row.get("passed")) for row in event_details
                ),
                "sequential_event_count": len(event_details),
                "maximum_current_utilization": utilization,
                "forbidden_trace_count": forbidden,
                "formal_contract_pass_diagnostic": bool(
                    restart.get("formal_contract_pass")
                ),
                "passed": passed,
            }
        )
    return {
        "expected": len(specs),
        "actual": len(rows),
        "pass_count": sum(bool(row["passed"]) for row in rows),
        "formal_tracking_pass_count_diagnostic_only": sum(
            bool(row.get("formal_contract_pass_diagnostic")) for row in rows
        ),
        "maximum_current_utilization": max(
            (float(row.get("maximum_current_utilization", 0.0)) for row in rows),
            default=0.0,
        ),
        "passed": len(rows) == len(specs) and all(bool(row["passed"]) for row in rows),
        "rows": rows,
    }


def run_rollout_phase(
    ctx: Context,
    partition: str,
    *,
    baseline: bool,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    previous = {
        ("training", True): "offline_ready",
        ("training", False): "training_baseline_complete",
        ("calibration", True): "training_model_frozen",
        ("calibration", False): "calibration_baseline_complete",
        ("holdout", True): "calibration_tube_frozen",
        ("holdout", False): "holdout_baseline_complete",
    }[(partition, baseline)]
    _require_phase(ctx, previous)
    specs = _partition_specs(_all_specs(ctx), partition, baseline=baseline)
    execution = evaluate_specs(ctx, specs, backend=backend, resume=resume)
    audit = _execution_audit(ctx, specs, baseline=baseline)
    role = "baseline" if baseline else "sequence"
    output = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": f"{partition}_{role}_execution_gate",
        "execution": execution,
        "execution_audit": audit,
        "passed": bool(execution["passed"] and audit["passed"]),
    }
    _write_json(ctx.paths.analysis / f"{partition}_{role}_gate.json", output)
    raw_count = len(list(ctx.paths.raw.glob("*.json.gz")))
    if output["passed"]:
        phase = f"{partition}_{role}_complete"
        _set_state(
            ctx,
            phase_status=phase,
            real_tsc_executed=True,
            new_raw_count=raw_count,
            heldout_outcomes_opened=partition == "holdout",
            stop_reason="",
        )
    else:
        _set_state(
            ctx,
            phase_status=f"{partition}_{role}_failed",
            finished=True,
            primary_pass=False,
            real_tsc_executed=True,
            new_raw_count=raw_count,
            stop_reason=f"{partition}_{role}_runtime_or_action_gate_failed",
            verdict={"route": ctx.cfg["routes"]["runtime_fail"], "passed": False},
        )
    return output


def _partition_raw(
    ctx: Context, specs: Sequence[Mapping[str, Any]], partition: str
) -> list[dict[str, Any]]:
    selected = [spec for spec in specs if str(spec["partition"]) == partition]
    output = []
    for spec in selected:
        path = ctx.paths.raw / f"{spec['experiment_id']}.json.gz"
        if not _result_complete(path, spec):
            raise ValueError(f"S24 incomplete {partition} raw: {spec['experiment_id']}")
        output.append(s21.s16.s9.t11.t1.r3c3.read_json_gz(path))
    expected = {"training": 600, "calibration": 200, "holdout": 200}[partition]
    if len(output) != expected:
        raise ValueError("S24 partition raw coverage changed")
    return output


def _formal_callback(ctx: Context, specs: Sequence[Mapping[str, Any]]):
    from docs.codex.audit_tools import (
        stage4_2r3c3t13s22_full_horizon_affine_authority as s22,
    )

    s22._load_s21_module()
    evaluators = {
        str(spec["experiment_id"]): s22.FormalEvaluator.from_context(ctx.base_ctx, spec)
        for spec in specs
    }
    scales = np.asarray(ctx.cfg["transition_model"]["visible_state_scales"], dtype=float)

    def evaluate(item: Mapping[str, Any], states: np.ndarray) -> bool:
        evaluator = evaluators[str(item["experiment_id"])]
        values = np.asarray(states, dtype=float)
        target = np.asarray(evaluator.target, dtype=float)
        rzi = np.column_stack(
            (
                target[0] + values[:, 0] * scales[0],
                target[1] + values[:, 1] * scales[1],
                target[2] + values[:, 4] * scales[4],
            )
        )
        return bool(evaluator.evaluate(rzi)["formal_contract_pass"])

    return evaluators, evaluate


def _transition_item(
    result: Mapping[str, Any], evaluator: Any, model_cfg: Mapping[str, Any]
) -> dict[str, Any]:
    spec = result["spec"]
    trajectory = result["trajectory"]
    horizon = int(spec["horizon_steps"])
    if len(trajectory) != horizon + 1:
        raise ValueError("S24 transition source horizon changed")
    target = np.asarray(evaluator.target, dtype=float)
    scales = np.asarray(model_cfg["visible_state_scales"], dtype=float)
    rows = []
    for index, state in enumerate(trajectory):
        if index == 0:
            following = trajectory[1]
            v_r = (float(following["R"]) - float(state["R"])) / DT_S
            v_z = (float(following["Z"]) - float(state["Z"])) / DT_S
        else:
            previous = trajectory[index - 1]
            v_r = (float(state["R"]) - float(previous["R"])) / DT_S
            v_z = (float(state["Z"]) - float(previous["Z"])) / DT_S
        rows.append(
            [
                (float(state["R"]) - target[0]) / scales[0],
                (float(state["Z"]) - target[1]) / scales[1],
                v_r / scales[2],
                v_z / scales[3],
                (float(state["Ip"]) - target[2]) / scales[4],
            ]
        )
    states = np.asarray(rows, dtype=float)
    requested = {
        int(step): np.asarray(value, dtype=float)
        for step, value in spec["s24_requested_action_by_task_step"].items()
    }
    if states.shape != (horizon + 1, 5) or not np.all(np.isfinite(states)):
        raise ValueError("S24 transition item is invalid")
    return {
        "experiment_id": str(result["experiment_id"]),
        "pair_id": str(spec["pair_id"]),
        "history_member": str(spec["history_member"]),
        "partition": str(spec["partition"]),
        "role": str(spec["s24_role"]),
        "sequence_index": int(spec["s24_sequence_index"]),
        "states": states,
        "horizon": horizon,
        "target_offsets": np.asarray(
            [
                float(spec["target_R_offset_m"]),
                float(spec["target_Z_offset_m"]),
                float(spec["target_Ip_offset_A"]),
            ],
            dtype=float,
        ),
        "target_absolute": target,
        "requested_action_by_step": requested,
        "forbidden_predictor_input_count": 0,
    }


def _partition_items(
    ctx: Context,
    specs: Sequence[Mapping[str, Any]],
    partition: str,
    evaluators: Mapping[str, Any],
) -> list[dict[str, Any]]:
    raw = _partition_raw(ctx, specs, partition)
    items = [
        _transition_item(
            result,
            evaluators[str(result["experiment_id"])],
            ctx.cfg["transition_model"],
        )
        for result in sorted(raw, key=lambda row: str(row["experiment_id"]))
    ]
    pairs = {str(item["pair_id"]) for item in items}
    expected_pairs = {"training": 12, "calibration": 4, "holdout": 4}[partition]
    expected_items = {"training": 600, "calibration": 200, "holdout": 200}[partition]
    if (
        len(items) != expected_items
        or len(pairs) != expected_pairs
        or sum(int(item["forbidden_predictor_input_count"]) for item in items)
    ):
        raise ValueError("S24 causal transition item coverage changed")
    return items


def _json_model_artifact(value: Mapping[str, Any]) -> dict[str, Any]:
    return s21.s16.s9.t11.t1._json_safe(copy.deepcopy(dict(value)))


def run_fit_training(ctx: Context) -> dict[str, Any]:
    _require_phase(ctx, "training_sequence_complete")
    specs = _all_specs(ctx)
    calibration_specs = _partition_specs(specs, "calibration", baseline=True) + _partition_specs(
        specs, "calibration", baseline=False
    )
    if any((ctx.paths.raw / f"{spec['experiment_id']}.json.gz").exists() for spec in calibration_specs):
        raise ValueError("S24 calibration outcomes opened before training model hash")
    evaluators, formal = _formal_callback(ctx, specs)
    items = _partition_items(ctx, specs, "training", evaluators)
    artifact = transition.select_training_model(items, ctx.cfg["transition_model"], formal)
    artifact = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "training_model_frozen_before_calibration",
        "spec_digest": _digest(specs),
        **artifact,
    }
    artifact = _json_model_artifact(artifact)
    audit = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "training_whole_pair_recursive_oof",
        "training_trajectory_count": int(artifact["training_item_count"]),
        "training_pair_count": int(artifact["training_pair_count"]),
        "teacher_row_count": int(artifact["teacher_row_count"]),
        "selected": artifact["selected"],
        "training_recursive_formal_reproduction_count": sum(
            bool(row["formal_verdict_reproduced"]) for row in artifact["training_oof_rows"]
        ),
        "forbidden_predictor_input_count": int(artifact["forbidden_predictor_input_count"]),
        "passed": bool(artifact["passed"]),
    }
    _write_json(ctx.paths.analysis / "training_model_audit.json", audit)
    if not artifact["passed"]:
        _write_json(ctx.paths.analysis / "failed_training_model_artifact.json", artifact)
        _set_state(
            ctx,
            phase_status="training_model_failed",
            finished=True,
            primary_pass=False,
            stop_reason="training_recursive_model_gate_failed",
            verdict={"route": ctx.cfg["routes"]["training_fail"], "passed": False},
        )
        return audit
    path = ctx.paths.model / "training_sequential_transition_model.json"
    _write_json(path, artifact)
    sha = _sha256(path)
    _set_state(ctx, phase_status="training_model_frozen", training_model_sha256=sha)
    audit["training_model_sha256"] = sha
    _write_json(ctx.paths.analysis / "training_model_audit.json", audit)
    return audit


def run_calibrate(ctx: Context) -> dict[str, Any]:
    state = _require_phase(ctx, "calibration_sequence_complete")
    model_path = ctx.paths.model / "training_sequential_transition_model.json"
    if _sha256(model_path) != state["training_model_sha256"]:
        raise ValueError("S24 training model changed before calibration")
    specs = _all_specs(ctx)
    holdout_specs = _partition_specs(specs, "holdout", baseline=True) + _partition_specs(
        specs, "holdout", baseline=False
    )
    if any((ctx.paths.raw / f"{spec['experiment_id']}.json.gz").exists() for spec in holdout_specs):
        raise ValueError("S24 holdout outcomes opened before tube hash")
    evaluators, formal = _formal_callback(ctx, specs)
    items = _partition_items(ctx, specs, "calibration", evaluators)
    training = _read_json(model_path)
    artifact = transition.calibration_artifact(
        training, items, ctx.cfg["transition_model"], formal
    )
    artifact = _json_model_artifact(
        {
            "schema_version": 1,
            "stage": STAGE,
            "phase": "calibrated_recursive_tube_frozen_before_holdout",
            "training_model_sha256": state["training_model_sha256"],
            **artifact,
        }
    )
    summary = artifact["calibration_summary"]
    audit = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "calibration_recursive_tube_gate",
        **summary,
    }
    _write_json(ctx.paths.analysis / "calibration_tube_audit.json", audit)
    if not artifact["passed"]:
        _write_json(ctx.paths.analysis / "failed_calibration_tube_artifact.json", artifact)
        _set_state(
            ctx,
            phase_status="calibration_tube_failed",
            finished=True,
            primary_pass=False,
            stop_reason="calibration_recursive_tube_gate_failed",
            verdict={"route": ctx.cfg["routes"]["calibration_fail"], "passed": False},
        )
        return audit
    path = ctx.paths.model / "calibrated_recursive_transition_tube.json"
    _write_json(path, artifact)
    sha = _sha256(path)
    _set_state(ctx, phase_status="calibration_tube_frozen", calibrated_tube_sha256=sha)
    audit["calibrated_tube_sha256"] = sha
    _write_json(ctx.paths.analysis / "calibration_tube_audit.json", audit)
    return audit


def _build_holdout_result(
    ctx: Context,
    specs: Sequence[Mapping[str, Any]],
    training: Mapping[str, Any],
    tube: Mapping[str, Any],
) -> dict[str, Any]:
    evaluators, formal = _formal_callback(ctx, specs)
    items = _partition_items(ctx, specs, "holdout", evaluators)
    rows, summary = transition.evaluate_recursive_set(
        training["model"],
        items,
        ctx.cfg["transition_model"],
        formal,
        tube["calibrated_componentwise_scaled_residual"],
    )
    return _json_model_artifact(
        {
            "schema_version": 1,
            "stage": STAGE,
            "phase": "fresh_whole_pair_recursive_holdout_final",
            "route": ctx.cfg["routes"]["pass"]
            if summary["passed"]
            else ctx.cfg["routes"]["holdout_fail"],
            "training_model_sha256": _sha256(
                ctx.paths.model / "training_sequential_transition_model.json"
            ),
            "calibrated_tube_sha256": _sha256(
                ctx.paths.model / "calibrated_recursive_transition_tube.json"
            ),
            "training_real_rollouts": 600,
            "calibration_real_rollouts": 200,
            "holdout_real_rollouts": 200,
            "total_real_rollouts": 1000,
            "holdout_outcome_access_after_tube_hash_count": 200,
            "forbidden_predictor_input_count": 0,
            "runtime_or_environment_error_count": 0,
            "raw_or_restart_error_count": 0,
            "statistics_or_reporting_error_count": 0,
            "probe_trajectories_allowed_in_expert_dataset": False,
            "real_tsc_executed": True,
            "rows": rows,
            **summary,
        }
    )


def independent_postprocess(ctx: Context, final: Mapping[str, Any]) -> dict[str, Any]:
    specs = _all_specs(ctx)
    evaluators, formal = _formal_callback(ctx, specs)
    training_items = _partition_items(ctx, specs, "training", evaluators)
    rebuilt_training = transition.select_training_model(
        training_items, ctx.cfg["transition_model"], formal
    )
    rebuilt_training = _json_model_artifact(
        {
            "schema_version": 1,
            "stage": STAGE,
            "phase": "training_model_frozen_before_calibration",
            "spec_digest": _digest(specs),
            **rebuilt_training,
        }
    )
    calibration_items = _partition_items(ctx, specs, "calibration", evaluators)
    rebuilt_tube = transition.calibration_artifact(
        rebuilt_training,
        calibration_items,
        ctx.cfg["transition_model"],
        formal,
    )
    rebuilt_tube = _json_model_artifact(
        {
            "schema_version": 1,
            "stage": STAGE,
            "phase": "calibrated_recursive_tube_frozen_before_holdout",
            "training_model_sha256": _sha256(
                ctx.paths.model / "training_sequential_transition_model.json"
            ),
            **rebuilt_tube,
        }
    )
    rebuilt_final = _build_holdout_result(ctx, specs, rebuilt_training, rebuilt_tube)
    saved_training = _read_json(
        ctx.paths.model / "training_sequential_transition_model.json"
    )
    saved_tube = _read_json(
        ctx.paths.model / "calibrated_recursive_transition_tube.json"
    )
    report = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "independent_server_side_recursive_raw_recomputation",
        "raw_count": len(list(ctx.paths.raw.glob("*.json.gz"))),
        "training_artifact_exact": _digest(saved_training) == _digest(rebuilt_training),
        "calibrated_tube_exact": _digest(saved_tube) == _digest(rebuilt_tube),
        "final_result_exact": _digest(final) == _digest(rebuilt_final),
        "runtime_or_environment_error_count": 0,
        "raw_or_restart_error_count": 0,
        "statistics_or_reporting_error_count": 0,
    }
    report["passed"] = bool(
        report["raw_count"] == 1000
        and report["training_artifact_exact"]
        and report["calibrated_tube_exact"]
        and report["final_result_exact"]
    )
    return report


def run_finalize(ctx: Context) -> dict[str, Any]:
    state = _require_phase(ctx, "holdout_sequence_complete")
    training_path = ctx.paths.model / "training_sequential_transition_model.json"
    tube_path = ctx.paths.model / "calibrated_recursive_transition_tube.json"
    if (
        _sha256(training_path) != state["training_model_sha256"]
        or _sha256(tube_path) != state["calibrated_tube_sha256"]
        or not bool(state["heldout_outcomes_opened"])
    ):
        raise ValueError("S24 frozen model/tube or holdout ordering changed")
    final = _build_holdout_result(
        ctx,
        _all_specs(ctx),
        _read_json(training_path),
        _read_json(tube_path),
    )
    final_path = ctx.paths.run_dir / "final_result.json"
    _write_json(final_path, final)
    independent = independent_postprocess(ctx, final)
    independent_path = ctx.paths.run_dir / "server_independent_postprocess.json"
    _write_json(independent_path, independent)
    final_pass = bool(final["passed"] and independent["passed"])
    _set_state(
        ctx,
        phase_status="campaign_complete",
        finished=True,
        primary_pass=final_pass,
        real_tsc_executed=True,
        new_raw_count=1000,
        final_result_sha256=_sha256(final_path),
        independent_postprocess_sha256=_sha256(independent_path),
        stop_reason="" if final_pass else "fresh_recursive_holdout_gate_failed",
        verdict={"route": final["route"], "passed": final_pass},
    )
    return {
        key: final[key]
        for key in (
            "stage",
            "phase",
            "route",
            "trajectory_count",
            "recursive_state_count",
            "point_pass_count",
            "containment_pass_count",
            "tube_cap_pass",
            "formal_verdict_reproduction_count",
            "maximum_absolute_recursive_scaled_error",
            "tube_halfwidth_physical",
            "passed",
        )
    } | {"independent_postprocess_passed": independent["passed"]}


def _raw_inventory(ctx: Context) -> dict[str, Any]:
    rows = []
    digest = hashlib.sha256()
    for path in sorted(ctx.paths.raw.glob("*.json.gz")):
        sha = _sha256(path)
        size = path.stat().st_size
        digest.update(f"{path.name}\0{size}\0{sha}\n".encode())
        rows.append({"path": path.name, "bytes": size, "sha256": sha})
    return {
        "count": len(rows),
        "total_bytes": sum(row["bytes"] for row in rows),
        "digest": digest.hexdigest(),
        "files": rows,
    }


def run_postprocess(ctx: Context) -> dict[str, Any]:
    state = _read_json(ctx.paths.state)
    if not state.get("finished") or state.get("phase_status") != "campaign_complete":
        raise ValueError("S24 postprocess requires a completed campaign")
    final = _read_json(ctx.paths.run_dir / "final_result.json")
    independent = independent_postprocess(ctx, final)
    inventory = _raw_inventory(ctx)
    report = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "final_server_raw_inventory_audit",
        "raw_inventory": inventory,
        "expected_raw_count": 1000,
        "actual_raw_count": inventory["count"],
        "independent_recomputation": independent,
        "passed": bool(inventory["count"] == 1000 and independent["passed"]),
    }
    _write_json(ctx.paths.run_dir / "server_final_audit.json", report)
    return report


def execute(ctx: Context, *, command: str, backend: str, resume: bool) -> dict[str, Any]:
    if command == "offline":
        return prepare_offline(ctx)
    if command == "postprocess":
        return run_postprocess(ctx)
    if not ctx.paths.state.is_file():
        raise ValueError("S24 command requires frozen offline state")
    if command.endswith("-baseline"):
        return run_rollout_phase(
            ctx, command.split("-", 1)[0], baseline=True, backend=backend, resume=resume
        )
    if command.endswith("-sequence"):
        return run_rollout_phase(
            ctx, command.split("-", 1)[0], baseline=False, backend=backend, resume=resume
        )
    if command == "fit-training":
        return run_fit_training(ctx)
    if command == "calibrate":
        return run_calibrate(ctx)
    if command == "finalize":
        return run_finalize(ctx)
    raise ValueError(f"unsupported S24 command: {command}")


def self_test(config_path: Path) -> dict[str, Any]:
    config_path = config_path.expanduser().resolve()
    cfg = _read_json(config_path)
    _validate_config(cfg, config_path)
    matrix = _requested_matrix(cfg)
    normalized = matrix / np.linalg.norm(matrix, axis=0, keepdims=True)
    history = np.zeros((10, 5), dtype=float)
    requested = transition.requested_action_by_step(matrix[0], cfg["schedule_contract"])
    dimensions = {
        candidate: len(
            transition.feature_vector(
                history,
                requested,
                np.zeros(3),
                step=10,
                horizon=35,
                candidate=candidate,
                model_cfg=cfg["transition_model"],
            )
        )
        for candidate in cfg["transition_model"]["feature_candidates"]
    }
    return {
        "stage": STAGE,
        "requested_matrix_shape": list(matrix.shape),
        "requested_matrix_rank": int(np.linalg.matrix_rank(matrix)),
        "requested_matrix_normalized_condition": float(np.linalg.cond(normalized)),
        "feature_dimensions": dimensions,
        "total_real_rollouts": int(cfg["control_matrix"]["total_real_rollouts"]),
        "real_tsc_executed": False,
        "passed": True,
    }


def _source_kwargs(args: argparse.Namespace) -> dict[str, Path]:
    return {
        "source_stage42r3b_run": args.source_stage42r3b_run,
        "source_stage42r3c3_run": args.source_stage42r3c3_run,
        "source_stage42r3c3_bank_dir": args.source_stage42r3c3_bank_dir,
        "source_stage42r3c3t1_run": args.source_stage42r3c3t1_run,
        "source_stage42r3c3t1_audit_dir": args.source_stage42r3c3t1_audit_dir,
        "source_stage42r3c3t3_controller_bank": args.source_stage42r3c3t3_controller_bank,
        "q1_run": args.q1_run,
        "q2_run": args.q2_run,
        "q1_audit": args.q1_audit,
        "q2_audit": args.q2_audit,
        "r3b_server_audit": args.r3b_server_audit,
        "r3b_snapshot_checks": args.r3b_snapshot_checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source-s21-run", type=Path, required=True)
    parser.add_argument("--source-s23r1-output", type=Path, required=True)
    parser.add_argument("--source-s24-run", type=Path, required=True)
    parser.add_argument("--source-d1r9-v1", type=Path, required=True)
    parser.add_argument("--source-d1r9-v2", type=Path, required=True)
    parser.add_argument("--source-d1r10-run", type=Path, required=True)
    parser.add_argument("--source-d1r10-audit", type=Path, required=True)
    parser.add_argument("--source-stage42r3b-run", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3-run", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3-bank-dir", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3t1-run", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3t1-audit-dir", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3t3-controller-bank", type=Path, required=True)
    parser.add_argument("--q1-run", type=Path, required=True)
    parser.add_argument("--q2-run", type=Path, required=True)
    parser.add_argument("--q1-audit", type=Path, required=True)
    parser.add_argument("--q2-audit", type=Path, required=True)
    parser.add_argument("--r3b-server-audit", type=Path, required=True)
    parser.add_argument("--r3b-snapshot-checks", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument(
        "--command",
        choices=(
            "offline",
            "training-baseline",
            "training-sequence",
            "fit-training",
            "calibration-baseline",
            "calibration-sequence",
            "calibrate",
            "holdout-baseline",
            "holdout-sequence",
            "finalize",
            "postprocess",
        ),
        required=True,
    )
    parser.add_argument("--backend", choices=("serial", "ray"), default="ray")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(args.config), sort_keys=True, indent=2))
        return
    ctx = load_config(
        args.config,
        source_s21_run=args.source_s21_run,
        source_s23r1_output=args.source_s23r1_output,
        source_s24_run=args.source_s24_run,
        source_d1r9_v1=args.source_d1r9_v1,
        source_d1r9_v2=args.source_d1r9_v2,
        source_d1r10_run=args.source_d1r10_run,
        source_d1r10_audit=args.source_d1r10_audit,
        run_dir=args.run_dir,
        **_source_kwargs(args),
    )
    result = execute(ctx, command=args.command, backend=args.backend, resume=args.resume)
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
