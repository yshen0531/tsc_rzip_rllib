"""Stage4.2R3c3T13S20 dynamic-exact Card15 observer campaign.

S20 keeps S16's causally frozen QR directions, but re-quantizes every signed
calibration increment around the current Card15 center.  The actual causal
input coordinates are recorded and used by the local response regression.
Training, calibration, and holdout outcomes open in that order, with a hashed
model and tube at the two phase boundaries.
"""

from __future__ import annotations

import argparse
import copy
from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
from types import SimpleNamespace
import time
import traceback
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s13_recurrent_sequence_tube_identification as s13,
    stage4_2r3c3t13s16_orthogonal_fixed_basis_identification as s16,
    stage4_2r3c3t13s18_pooled_causal_observer_preflight as s18,
)


STAGE = "Stage4.2R3c3T13S20"
SCHEMA_VERSION = 1
RUN_NAME = "stage4_2r3c3t13s20_dynamic_exact_card15_pooled_observer_campaign"
CAMPAIGN_IDENTITY = "dynamic_exact_card15_pooled_causal_observer_campaign_v1"
CONTROLLER_REVISION = "dynamic_exact_card15_calibration_probe_v42r3c3t13s20_v1"
PACKAGE_REVISION = "r42r3c3t13s20_dynamic_exact_card15_pooled_observer_campaign_v2"
BASELINE_PROBE_ID = s16.BASELINE_PROBE_ID
DIRECTIONS = s16.DIRECTIONS
SIGNS = s16.SIGNS
N_COILS = s16.N_COILS

PASS_ROUTE = "DYNAMIC_EXACT_CARD15_POOLED_OBSERVER_HOLDOUT_PASS_LOCAL_SET_MODEL_ONLY"
TRAINING_FAIL_ROUTE = "DYNAMIC_EXACT_CARD15_POOLED_OBSERVER_TRAINING_FAIL_STOP"
CALIBRATION_FAIL_ROUTE = "DYNAMIC_EXACT_CARD15_POOLED_OBSERVER_CALIBRATION_FAIL_STOP"
HOLDOUT_FAIL_ROUTE = "DYNAMIC_EXACT_CARD15_POOLED_OBSERVER_HOLDOUT_FAIL_REDESIGN"
EXECUTION_FAIL_ROUTE = "DYNAMIC_EXACT_CARD15_RUNTIME_OR_EXECUTION_FAIL_STOP"

PHASES = (
    "offline_ready",
    "training_baseline_complete",
    "training_probe_complete",
    "training_model_frozen",
    "calibration_baseline_complete",
    "calibration_probe_complete",
    "calibration_tube_frozen",
    "holdout_baseline_complete",
    "holdout_probe_complete",
    "campaign_complete",
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _write_json_gz(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(value, handle, sort_keys=True, allow_nan=False, separators=(",", ":"))


@dataclass(frozen=True)
class Paths:
    run_dir: Path
    raw: Path
    variants: Path
    specs: Path
    source_reference: Path
    analysis: Path
    model: Path
    manifest: Path
    state: Path


def _paths(run_dir: Path) -> Paths:
    root = run_dir.expanduser().resolve()
    return Paths(
        run_dir=root,
        raw=root / "stage4_2r3c3t13s20_dynamic_exact_card15_pooled_observer_campaign" / "raw",
        variants=root / "variants",
        specs=root / "specs",
        source_reference=root / "source_reference",
        analysis=root / "analysis",
        model=root / "model",
        manifest=root / "stage4_2r3c3t13s20_manifest.json",
        state=root / "stage4_2r3c3t13s20_state.json",
    )


@dataclass(frozen=True)
class Context:
    cfg: dict[str, Any]
    config_path: Path
    base_ctx: s16.Context
    paths: Paths


def _partition_rows(cfg: Mapping[str, Any], partition: str) -> tuple[tuple[str, str], ...]:
    return tuple((str(row["pair_id"]), str(row["regime"])) for row in cfg["split"][partition])


def _validate_config(cfg: Mapping[str, Any]) -> None:
    expected_training = (
        ("p5_q1_a0p750_gap2_settle4", "A"),
        ("p5_q1_a0p750_gap3_settle4", "B"),
        ("p5_q1_a0p900_gap4_settle4", "C"),
        ("p5_q2_a0p750_gap2_settle4", "D"),
        ("p5_q2_a0p750_gap4_settle4", "A"),
        ("p5_q2_a0p900_gap3_settle4", "B"),
        ("p9_q1_a0p750_gap3_settle4", "C"),
        ("p9_q1_a0p900_gap2_settle4", "D"),
        ("p9_q1_a0p900_gap4_settle4", "A"),
        ("p9_q2_a0p750_gap4_settle4", "B"),
        ("p9_q2_a0p900_gap2_settle4", "C"),
        ("p9_q2_a0p900_gap3_settle4", "D"),
    )
    expected_calibration = (
        ("p5_q1_a0p900_gap3_settle4", "A"),
        ("p5_q2_a0p750_gap3_settle4", "B"),
        ("p9_q1_a0p900_gap3_settle4", "C"),
        ("p9_q2_a0p750_gap3_settle4", "D"),
    )
    expected_holdout = (
        ("p5_q1_a0p750_gap4_settle4", "C"),
        ("p5_q2_a0p900_gap4_settle4", "D"),
        ("p9_q1_a0p750_gap4_settle4", "A"),
        ("p9_q2_a0p900_gap4_settle4", "B"),
    )
    if (
        cfg.get("schema_version") != 1
        or cfg.get("stage") != STAGE
        or cfg.get("design_revision") != 1
        or cfg.get("run_name") != RUN_NAME
        or cfg.get("campaign_identity") != CAMPAIGN_IDENTITY
        or cfg.get("controller_revision") != CONTROLLER_REVISION
        or cfg.get("package_revision") != PACKAGE_REVISION
        or cfg.get("base_stage_config")
        != "configs/stage4_2r3c3t13s16_orthogonal_fixed_basis_identification_370ms.json"
        or cfg.get("base_stage_config_sha256")
        != "5e9425977daebe7f667591f4ad1bdd5f7ebc8ae4e19d78be9624c547e4647e2a"
    ):
        raise ValueError("T13S20 identity changed")
    if (
        _partition_rows(cfg, "training") != expected_training
        or _partition_rows(cfg, "calibration") != expected_calibration
        or _partition_rows(cfg, "holdout") != expected_holdout
        or set(pair for pair, _ in (*expected_training, *expected_calibration, *expected_holdout))
        != {pair for part in (expected_training, expected_calibration, expected_holdout) for pair, _ in part}
        or tuple(cfg["split"]["history_members"]) != ("plus_first", "minus_first")
    ):
        raise ValueError("T13S20 prospective split changed")
    regimes = {
        row["id"]: (row["target_id"], int(row["action_delay_steps"]), float(row["slew_scale"]))
        for row in cfg["split"]["regimes"]
    }
    if regimes != {
        "A": ("nominal", 0, 1.0), "B": ("nominal", 2, 0.9),
        "C": ("RZ_p10_m10", 0, 1.0), "D": ("RZ_p10_m10", 2, 0.9),
    }:
        raise ValueError("T13S20 regimes changed")
    features = cfg["causal_model"]
    if (
        tuple(map(int, features["visible_state_indices"])) != tuple(range(1, 11))
        or tuple(map(int, features["input_steps"])) != tuple(range(10))
        or not bool(features["dynamic_input_coordinates_from_same_trace"])
        or tuple(map(int, features["calibration_input_steps"])) != tuple(range(8))
        or not np.array_equal(
            np.asarray(features["settling_input_coordinates"], dtype=float),
            np.zeros((2, 4), dtype=float),
        )
        or int(features["legendre_degree"]) != 3
        or int(features["feature_count"]) != 9
        or float(features["minimum_signed_primary_coordinate"]) != 0.85
        or float(features["maximum_signed_primary_coordinate"]) != 1.15
        or float(features["maximum_cross_coordinate_abs"]) != 0.15
        or float(features["minimum_dynamic_basis_cosine"]) != 0.98
        or float(features["maximum_dynamic_off_basis_residual"]) != 0.15
        or float(features["maximum_dynamic_design_condition"]) != 4.0
        or not bool(features["require_exact_calibration_net_zero"])
        or tuple(map(float, features["response_scales"])) != (0.03, 0.03, 0.1, 0.1, 2000.0)
        or tuple(map(float, features["response_floor"])) != (1e-9, 1e-9, 1e-7, 1e-7, 1e-4)
        or tuple(map(float, features["belief_halfwidth_caps"])) != (0.003, 0.003, 0.01, 0.01, 1000.0)
        or float(features["maximum_absolute_scaled_point_error"]) != 0.1
        or float(features["minimum_response_basis_cosine"]) != 0.98
        or float(features["maximum_response_off_basis_residual"]) != 0.15
        or float(features["feature_equivalence_tolerance"]) != 1e-12
    ):
        raise ValueError("T13S20 causal feature contract changed")
    model = cfg["pooled_model"]
    if (
        model["outer_group_key"] != "pair_id"
        or tuple(map(float, model["ridge_grid"])) != (0.0, 1e-8, 1e-6, 1e-4, 1e-2, 1.0, 100.0)
        or tuple(model["selection_order"]) != (
            "maximum_absolute_scaled_oof_error", "mean_squared_scaled_oof_error", "ridge"
        )
        or float(model["standard_deviation_floor"]) != 1e-12
        or float(model["tube_multiplier"]) != 4.0
        or model["calibrated_residual_rule"]
        != "componentwise_max_training_oof_and_calibration_absolute_residual"
    ):
        raise ValueError("T13S20 pooled model contract changed")
    counts = cfg["control_matrix"]
    expected_counts = {
        "training_pairs": 12, "calibration_pairs": 4, "holdout_pairs": 4,
        "history_members_per_pair": 2, "signed_probes_per_context": 8,
        "training_baselines": 24, "training_probes": 192,
        "calibration_baselines": 8, "calibration_probes": 64,
        "holdout_baselines": 8, "holdout_probes": 64, "total_real_rollouts": 360,
    }
    if any(int(counts[key]) != value for key, value in expected_counts.items()):
        raise ValueError("T13S20 rollout matrix changed")
    if (
        int(cfg["freshness"]["minimum_prior_identification_raw"]) != 900
        or int(cfg["freshness"]["required_candidate_pair_count"]) != 20
        or int(cfg["freshness"]["allowed_s19_training_baseline_raw_hits"]) != 24
        or int(cfg["freshness"]["allowed_prior_training_probe_raw_hits"]) != 0
        or int(cfg["freshness"]["allowed_prior_calibration_raw_hits"]) != 0
        or int(cfg["freshness"]["allowed_prior_holdout_raw_hits"]) != 0
        or not bool(cfg["freshness"]["forbid_outcome_based_selection"])
        or bool(cfg["formal_timing_contract"]["arrival_deadline_expansion_allowed"])
        or not bool(cfg["identification_only"])
        or not bool(cfg["fresh_holdout_required"])
        or bool(cfg["probe_trajectories_allowed_in_expert_dataset"])
        or bool(cfg["bc_dagger_or_rl_allowed"])
    ):
        raise ValueError("T13S20 scientific route changed")
    source = cfg["source_s19_development"]
    expected_source = {
        "run_relative_path": (
            "stage4_2r3c3t13s19_runs/"
            "stage4_2r3c3t13s19_prospective_pooled_observer_campaign_20260803_14f3646"
        ),
        "final_state_sha256": "4e4d4247be7478f4a2352d092b6b72dba2916df69deba0d15cee7eaad203bdc2",
        "raw_inventory_count": 24,
        "raw_inventory_digest": "3a2a468a92ea656b240280125ebac9b4e947d14bc3beb8e61a0fcdd82d1e01da",
        "successful_training_baselines": 23,
        "failed_training_baselines": 1,
        "failed_experiment_id": "s42r3c3_6bc94530a3ae407830ff",
        "failed_raw_sha256": "ebecebf89a465bfc9ddb66f7e089a9fdcb3803ab30d19c4ee121cd4a05a67ccc",
        "dynamic_card15_development_sha256": "e16cfd02d1d7f0af1789c9ece07de8d8116eee11780ad8bf0e7cd23d1de14d64",
        "failed_reproduction_v2_sha256": "cd3396e50f14cf3476709bb44423c5363b3cd56b551ad97380e1565e602fc7c1",
    }
    if dict(source) != expected_source:
        raise ValueError("T13S20 authenticated S19 development source changed")


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
    base_path = (_project_root() / cfg["base_stage_config"]).resolve()
    if not base_path.is_file() or _sha256(base_path) != cfg["base_stage_config_sha256"]:
        raise ValueError("T13S20 base S16 config mismatch")
    base = s16.load_config(
        base_path,
        source_stage42r3b_run=source_stage42r3b_run,
        source_stage42r3c3_run=source_stage42r3c3_run,
        source_stage42r3c3_bank_dir=source_stage42r3c3_bank_dir,
        source_stage42r3c3t1_run=source_stage42r3c3t1_run,
        source_stage42r3c3t1_audit_dir=source_stage42r3c3t1_audit_dir,
        source_stage42r3c3t3_controller_bank=source_stage42r3c3t3_controller_bank,
        q1_run=q1_run, q2_run=q2_run, q1_audit=q1_audit, q2_audit=q2_audit,
        r3b_server_audit=r3b_server_audit,
        r3b_snapshot_checks=r3b_snapshot_checks,
        run_dir=run_dir,
    )
    return Context(cfg=cfg, config_path=path, base_ctx=base, paths=_paths(run_dir))


def _pair_partition_map(cfg: Mapping[str, Any]) -> dict[str, tuple[str, str]]:
    output: dict[str, tuple[str, str]] = {}
    for partition in ("training", "calibration", "holdout"):
        for pair, regime in _partition_rows(cfg, partition):
            if pair in output:
                raise ValueError("T13S20 pair appears in more than one partition")
            output[pair] = (partition, regime)
    return output


def build_context_table(ctx: Context) -> list[dict[str, Any]]:
    source = s13.build_context_table(ctx.base_ctx.base_ctx)
    by_key = {(str(row["pair_id"]), str(row["history_member"])): row for row in source}
    assignment = _pair_partition_map(ctx.cfg)
    regimes = {row["id"]: row for row in ctx.cfg["split"]["regimes"]}
    output = []
    for pair, (partition, regime_id) in assignment.items():
        regime = regimes[regime_id]
        for member in ctx.cfg["split"]["history_members"]:
            key = (pair, str(member))
            if key not in by_key:
                raise ValueError(f"T13S20 source context missing: {key}")
            row = copy.deepcopy(by_key[key])
            row.update({
                "partition": partition, "consumed_training": False,
                "regime_id": regime_id, "target_id": regime["target_id"],
                "action_delay_steps": int(regime["action_delay_steps"]),
                "slew_scale": float(regime["slew_scale"]),
            })
            output.append(row)
    counts = Counter(row["partition"] for row in output)
    if counts != {"training": 24, "calibration": 8, "holdout": 8} or len(output) != 40:
        raise ValueError("T13S20 context coverage changed")
    return output


def build_specs(ctx: Context, table: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    templates = s13._source_templates(ctx.base_ctx.base_ctx)
    calibration = ctx.base_ctx.cfg["active_calibration"]
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
                "partition": row["partition"], "pair_id": row["pair_id"],
                "history_member": row["history_member"],
                "state_generation_experiment_id": row["state_generation_experiment_id"],
                "snapshot_manifest_digest": row["restart_snapshot_manifest_digest"],
                "target_id": row["target_id"], "delay": row["action_delay_steps"],
                "slew": row["slew_scale"], "probe_id": probe_id,
                "probe_sign": sign, "controller_revision": CONTROLLER_REVISION,
            }
            experiment_id = s16.s9.t11.t1.r3c3._scenario_digest(identity)
            spec = copy.deepcopy(templates[key])
            spec.update({
                "kind": "stage4_2r3c3t13s20_dynamic_exact_card15_pooled_observer_campaign",
                "stage": STAGE, "campaign_identity": CAMPAIGN_IDENTITY,
                "controller_revision": CONTROLLER_REVISION,
                "underlying_controller_revision": s16.s9.t11.t1.r3c1.CONTROLLER_REVISION,
                "probe_primitive_revision": s16.s9.CONTROLLER_REVISION,
                "experiment_id": experiment_id,
                "phase": "prospective_partitioned_pooled_observer_identification",
                "category": "identification_only_prospective_pooled_observer",
                "partition": str(row["partition"]), "regime_id": str(row["regime_id"]),
                "pair_id": str(row["pair_id"]), "history_member": str(row["history_member"]),
                "state_generation_experiment_id": str(row["state_generation_experiment_id"]),
                "restart_snapshot_dir": str(row["restart_snapshot_dir"]),
                "restart_snapshot_manifest_digest": str(row["restart_snapshot_manifest_digest"]),
                "baseline_experiment_id": "",
                "environment_variant": f"stage4_2r3c3t13s20_{experiment_id}",
                "horizon_steps": horizon, "formal_horizon_steps": horizon,
                "identification_only": True,
                "r3c3_probe_id": probe_id,
                "r3c3_probe_window": "baseline" if baseline else "transport",
                "r3c3_probe_direction": direction, "r3c3_probe_sign": sign,
                "r3c3_probe_issue_step": -1 if baseline else int(calibration["response_issue_step"]),
                "r3c3_probe_cancel_step": -1 if baseline else int(calibration["response_cancel_step"]),
                "r3c3_probe_first_effect_state": -1 if baseline else int(calibration["response_first_effect_state"]),
                "r3c3_probe_cancel_effect_state": -1 if baseline else int(calibration["response_cancel_effect_state"]),
                "r3c3t13s9_schedule_contract": "s20_prospective_orthogonal_postqueue_active_calibration_v1",
                "r3c3t13s9_offline_role": str(row["partition"]),
                "r3c3t13s9_stratum": "normal" if int(row["action_delay_steps"]) == 0 else "weak",
                "r3c3t13s9_source_r3c1_experiment_id": "",
                "s20_response_role": "baseline" if baseline else "active_response",
                "probe_trajectory_allowed_in_expert_dataset": False,
                "pair_or_history_label_available_to_controller": False,
                "partition_label_available_to_controller": False,
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
    if len(specs) != 360 or len({str(row["experiment_id"]) for row in specs}) != 360:
        raise ValueError("T13S20 spec coverage changed")
    return specs


def _partition_specs(
    specs: Sequence[Mapping[str, Any]], partition: str, *, baseline: bool,
) -> list[dict[str, Any]]:
    output = [
        copy.deepcopy(dict(spec)) for spec in specs
        if spec["partition"] == partition
        and (spec["r3c3_probe_id"] == BASELINE_PROBE_ID) == baseline
    ]
    expected = {
        ("training", True): 24, ("training", False): 192,
        ("calibration", True): 8, ("calibration", False): 64,
        ("holdout", True): 8, ("holdout", False): 64,
    }[(partition, baseline)]
    if len(output) != expected:
        raise ValueError("T13S20 partition spec coverage changed")
    return output


def _payload(ctx: Context, spec: Mapping[str, Any]) -> dict[str, Any]:
    proxy = SimpleNamespace(base_ctx=ctx.base_ctx.base_ctx, paths=ctx.paths)
    payload = s16._payload(proxy, spec)
    experiment_id = str(spec["experiment_id"])
    payload.update({
        "variant_id": f"stage4_2r3c3t13s20_{experiment_id}",
        "stage4_2r3c3t13s20_restart_snapshot_dir": str(spec["restart_snapshot_dir"]),
        "stage4_2r3c3t13s20_snapshot_manifest_digest": str(spec["restart_snapshot_manifest_digest"]),
        "stage4_2r3c3t13s20_pair_history_partition_label_available_to_controller": False,
    })
    _write_json(ctx.paths.variants / f"payload_{experiment_id}.json", payload)
    return payload


def _library_bundle_selector(ctx: Context):
    return s16._library_bundle_selector(ctx.base_ctx)


def _dynamic_exact_target(
    center_fields: Sequence[str], desired_delta: Sequence[Decimal], *, search_radius: int,
) -> tuple[tuple[str, ...], tuple[Decimal, ...], tuple[int, ...]]:
    """Find the nearest exactly representable signed displacement at one causal center."""
    centers = tuple(s16.s9._decimal_field(field) for field in center_fields)
    steps = tuple(s16.s9.local_symmetric_card15_step(field) for field in center_fields)
    targets: list[str] = []
    actual: list[Decimal] = []
    counts: list[int] = []
    for center, step, desired in zip(centers, steps, desired_delta):
        nominal = int(np.rint(float(desired / step)))
        count, target, _ = s16._nearest_exact_symmetric_count(
            center, step, nominal, search_radius=search_radius,
        )
        parsed = s16.s9._decimal_field(target)
        if len(target) != 10 or parsed != center + step * count:
            raise ValueError("T13S20 dynamic Card15 target lost exactness")
        targets.append(target)
        actual.append(parsed - center)
        counts.append(count)
    return tuple(targets), tuple(actual), tuple(counts)


class DynamicExactCard15ProbeController(s16.OrthogonalFixedBasisProbeController):
    """S16 QR directions with current-centered exact signed calibration pulses."""

    def __init__(
        self, base_worker: Any, bundle: Mapping[str, Any],
        source_spec: Mapping[str, Any], initial_state: Mapping[str, Any],
        lattice_cfg: Mapping[str, Any], calibration_cfg: Mapping[str, Any],
        dynamic_cfg: Mapping[str, Any],
    ):
        super().__init__(
            base_worker, bundle, source_spec, initial_state, lattice_cfg, calibration_cfg
        )
        self.dynamic_cfg = copy.deepcopy(dict(dynamic_cfg))
        self._s20_running_net = [Decimal(0) for _ in range(N_COILS)]

    def _fixed_signed_calibration(
        self, index: int, sign: int, currents: np.ndarray,
        baseline_action: np.ndarray,
    ) -> tuple[np.ndarray, dict[str, Any], Any]:
        if sign not in {-1, 1}:
            raise ValueError("T13S20 dynamic calibration sign must be plus or minus")
        self._freeze_fixed_basis(currents, baseline_action)
        center = self.actuator.apply(currents, baseline_action)
        desired = tuple(sign * value for value in self._fixed_basis_delta[index])
        target_fields, actual, counts = _dynamic_exact_target(
            center.card15_fields, desired,
            search_radius=int(self.calibration_cfg["exact_symmetric_search_radius"]),
        )
        chosen = s16.s9.exact_stored_center_action(
            stored_fields=target_fields, measured_current_a_tsc=currents,
            baseline_action_norm_tsc=baseline_action, turns_tsc=self.turns_tsc,
            max_slew_step_a=float(self.base.max_delta_a),
            minimum_current_a_tsc=self.base.min_current,
            maximum_current_a_tsc=self.base.max_current, cfg=self.lattice_cfg,
        )
        frozen_field = np.column_stack([
            np.asarray([float(value) for value in self._fixed_basis_delta[column]])
            for column in range(4)
        ])
        turns = np.asarray(self.turns_tsc, dtype=float)
        frozen_current = frozen_field * 1000.0 / turns[:, None]
        actual_field = np.asarray([float(value) for value in actual], dtype=float)
        actual_current = actual_field * 1000.0 / turns
        coordinate, _, _, _ = np.linalg.lstsq(frozen_current, actual_current, rcond=None)
        reconstructed = frozen_current @ coordinate
        actual_norm = float(np.linalg.norm(actual_current))
        desired_current = (
            np.asarray([float(value) for value in desired], dtype=float)
            * 1000.0 / turns
        )
        desired_norm = float(np.linalg.norm(desired_current))
        cosine = float(
            np.dot(desired_current, actual_current)
            / max(desired_norm * actual_norm, 1e-300)
        )
        off_basis = float(
            np.linalg.norm(actual_current - reconstructed) / max(actual_norm, 1e-300)
        )
        signed_primary = float(sign * coordinate[index])
        cross = float(np.max(np.abs(np.delete(coordinate, index))))
        geometry_pass = bool(
            float(self.dynamic_cfg["minimum_signed_primary_coordinate"])
            <= signed_primary
            <= float(self.dynamic_cfg["maximum_signed_primary_coordinate"])
            and cross <= float(self.dynamic_cfg["maximum_cross_coordinate_abs"])
            and cosine >= float(self.dynamic_cfg["minimum_dynamic_basis_cosine"])
            and off_basis <= float(self.dynamic_cfg["maximum_dynamic_off_basis_residual"])
        )
        if not bool(chosen["passed"]) or not geometry_pass:
            raise ValueError(
                "T13S20 dynamic exact calibration action failed: "
                + json.dumps({
                    "action": chosen, "coordinate": coordinate.tolist(),
                    "signed_primary": signed_primary, "cross": cross,
                    "cosine": cosine, "off_basis": off_basis,
                }, sort_keys=True)
            )
        lattice = {
            **chosen,
            "selected_method": "dynamic_nearest_exact_card15_relative_current_center",
            "fixed_sign": sign,
            "fixed_direction_index": index,
            "fixed_direction": str(self.calibration_cfg["pulse_directions"][index]),
            "fixed_delta_field_kAt_tsc": [
                float(value) for value in self._fixed_basis_delta[index]
            ],
            "desired_signed_delta_field_kAt_tsc": [float(value) for value in desired],
            "signed_delta_field_kAt_tsc": [float(value) for value in actual],
            "integer_grid_steps_tsc": list(counts),
            "positive_target_fields": list(target_fields) if sign > 0 else [],
            "negative_target_fields": list(target_fields) if sign < 0 else [],
            "dynamic_input_coordinate": coordinate.tolist(),
            "signed_primary_coordinate": signed_primary,
            "maximum_cross_coordinate_abs": cross,
            "desired_actual_current_cosine": cosine,
            "relative_off_basis_residual": off_basis,
            "fixed_basis_rank": self._fixed_basis_rank,
            "fixed_basis_normalized_condition": self._fixed_basis_condition,
            "initial_direction_plan": self._fixed_basis_plans[index],
            "dynamic_geometry_passed": geometry_pass,
            "passed": True,
        }
        return np.asarray(chosen["action_norm_tsc"], dtype=float), lattice, center

    def action(self, current_state: Mapping[str, Any]) -> tuple[np.ndarray, dict[str, Any]]:
        action, trace = super().action(current_state)
        event = str(trace["r3c3t13s16_lattice_event"])
        lattice = trace.get("r3c3t13s16_lattice") or {}
        coordinate: list[float] = []
        actual: list[float] = []
        exact_net = False
        if event.startswith("calibration_"):
            coordinate = list(map(float, lattice["dynamic_input_coordinate"]))
            actual = list(map(float, lattice["signed_delta_field_kAt_tsc"]))
            for coil, value in enumerate(lattice["signed_delta_field_kAt_tsc"]):
                self._s20_running_net[coil] += Decimal(str(value))
            exact_net = all(value == 0 for value in self._s20_running_net)
            if self.step == 7 and bool(
                self.dynamic_cfg["require_exact_calibration_net_zero"]
            ) and not exact_net:
                raise ValueError("T13S20 dynamic calibration sequence is not exact zero net")
        trace.update({
            "r3c3t13s20_identification_only": True,
            "r3c3t13s20_controller_revision": CONTROLLER_REVISION,
            "r3c3t13s20_partition_label_used": False,
            "r3c3t13s20_dynamic_exact_card15": event.startswith("calibration_"),
            "r3c3t13s20_dynamic_input_coordinate": coordinate,
            "r3c3t13s20_actual_signed_delta_field_kAt_tsc": actual,
            "r3c3t13s20_running_calibration_net_kAt_tsc": [
                float(value) for value in self._s20_running_net
            ],
            "r3c3t13s20_exact_calibration_net_zero": exact_net,
            "r3c3t13s20_dynamic_schedule_label_conditioned": False,
        })
        return action, trace


class LocalWorker:
    """Authentic TSC worker using the new S20 dynamic-exact controller."""

    def __init__(
        self, payload: dict[str, Any], library: dict[str, Any], bundle: dict[str, Any],
        worker_id: str, selector: dict[str, Any], lattice_cfg: dict[str, Any],
        calibration_cfg: dict[str, Any], dynamic_cfg: dict[str, Any],
    ):
        self.plant = s16.s9.t11.t1.r1.LocalPlantReplayWorker(
            payload, library, bundle, worker_id, selector
        )
        self.base = self.plant.base_worker
        self.bundle = bundle
        self.lattice_cfg = lattice_cfg
        self.calibration_cfg = calibration_cfg
        self.dynamic_cfg = dynamic_cfg

    def close(self) -> None:
        self.plant.close()

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        failed = True
        trajectory: list[dict[str, Any]] = []
        trace: list[dict[str, Any]] = []
        result: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION, "stage": STAGE,
            "campaign_identity": CAMPAIGN_IDENTITY,
            "controller_revision": CONTROLLER_REVISION,
            "underlying_controller_revision": s16.s9.t11.t1.r3c1.CONTROLLER_REVISION,
            "probe_primitive_revision": s16.s9.CONTROLLER_REVISION,
            "experiment_id": str(spec["experiment_id"]),
            "spec": copy.deepcopy(spec), "success": False, "completed": False,
            "failure_reason": "", "trajectory": trajectory, "controller_trace": trace,
        }
        try:
            horizon = int(spec["horizon_steps"])
            if (
                horizon != s13._formal_horizon(float(spec["slew_scale"]))
                or horizon != int(spec["formal_horizon_steps"])
                or horizon != int(self.base.env.max_episode_steps)
            ):
                raise ValueError("T13S20 formal horizon changed")
            self.base.env.reset()
            zero = np.zeros(N_COILS, dtype=np.float32)
            trajectory.append(s16.s9.t11.t1.r1._state_record_full(self.base.env, 0, zero))
            controller = DynamicExactCard15ProbeController(
                self.base, self.bundle, s16.s9._controller_spec(spec), trajectory[0],
                self.lattice_cfg, self.calibration_cfg, self.dynamic_cfg,
            )
            for step in range(horizon):
                action, controller_row = controller.action(trajectory[-1])
                _, _, terminated, truncated, info = self.base.env.step(action)
                next_state = s16.s9.t11.t1.r1._state_record_full(
                    self.base.env, step + 1, action
                )
                trajectory.append(next_state)
                trace.append(controller_row)
                controller.advance(next_state)
                if terminated:
                    raise RuntimeError(str(info.get("failure_reason", "environment terminated")))
                if truncated and step + 1 < horizon:
                    raise RuntimeError("environment truncated before T13S20 horizon")
            baseline = str(spec["r3c3_probe_id"]) == BASELINE_PROBE_ID
            events = [
                row["r3c3t13s16_lattice_event"] for row in trace
                if row["r3c3t13s16_lattice_event"] != "none"
            ]
            expected = [
                "calibration_issue", "calibration_cancel", "calibration_issue",
                "calibration_cancel", "calibration_issue", "calibration_cancel",
                "calibration_issue", "calibration_cancel",
            ] + ([] if baseline else ["response_issue", "response_cancel"])
            forbidden_keys = (
                "future_measurement_used", "hidden_wire_used", "source_action_used",
                "source_coil_current_used", "source_wire_current_used",
                "current_run_future_used", "pair_or_history_label_used", "source_result_used",
                "future_probe_schedule_available_to_underlying_controller",
                "r3c3t13s20_partition_label_used",
            )
            forbidden = sum(any(bool(row.get(key)) for key in forbidden_keys) for row in trace)
            success = bool(
                len(trajectory) == horizon + 1 and len(trace) == horizon
                and not any(bool(row.get("abnormal")) for row in trajectory)
                and all(bool(row.get("computed_online")) and bool(row.get("solver_success")) for row in trace)
                and events == expected and forbidden == 0
                and bool(trace[7]["r3c3t13s20_exact_calibration_net_zero"])
            )
            result.update({
                "success": success, "completed": True,
                "failure_reason": "" if success else "incomplete or invalid T13S20 rollout",
                "hidden_history_control_summary": {
                    "fresh_controller_actor": True, "fresh_tsc_process": True,
                    "full_tsc_hidden_state_loaded_from_sprsina": True,
                    "controller_history_initialization": "current_visible_state_only_at_task_step_zero",
                    "controller_integral_initialization": "zero",
                    "controller_previous_correction_initialization": "zero",
                    "controller_delay_queue_initialization": "authenticated_visible_manifold_phase_aligned_nominal_prime",
                    "reference_phase_start": controller.reference_phase_start,
                    "baseline_controller_revision": s16.s9.t11.t1.r3c1.CONTROLLER_REVISION,
                    "identification_only": True,
                    "dynamic_exact_card15_identification_only": True,
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
                    "partition_label_available_to_controller": False,
                    "source_result_used": False,
                },
                "wall_time_s": time.time() - started,
            })
            failed = not success
            return s16.s9.t11.t1._json_safe(result)
        except Exception as exc:
            result.update({
                "success": False, "completed": True, "failure_reason": repr(exc),
                "trajectory": trajectory, "controller_trace": trace,
                "traceback": traceback.format_exc(), "wall_time_s": time.time() - started,
            })
            return s16.s9.t11.t1._json_safe(result)
        finally:
            runner = getattr(self.base.env, "runner", None)
            if runner is not None:
                runner.cleanup_episode_workspace(
                    failed=failed,
                    reason="stage4_2r3c3t13s20_dynamic_exact_card15_pooled_observer_campaign",
                )


_RAY_ACTOR = None


def _ray_actor_class():
    global _RAY_ACTOR
    if _RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class Stage42R3C3T13S20Actor:
            def __init__(
                self, payload, library, bundle, worker_id, selector, lattice,
                calibration, dynamic,
            ):
                self.worker = LocalWorker(
                    payload, library, bundle, worker_id, selector, lattice,
                    calibration, dynamic,
                )

            def evaluate(self, spec):
                return self.worker.evaluate(spec)

            def close(self):
                self.worker.close()
                return True

        _RAY_ACTOR = Stage42R3C3T13S20Actor
    return _RAY_ACTOR


def _result_complete(path: Path, spec: Mapping[str, Any]) -> bool:
    if not path.is_file():
        return False
    try:
        result = s16.s9.t11.t1.r3c3.read_json_gz(path)
        horizon = int(spec["horizon_steps"])
        return bool(
            result.get("completed") and result.get("success")
            and result.get("stage") == STAGE
            and result.get("campaign_identity") == CAMPAIGN_IDENTITY
            and result.get("controller_revision") == CONTROLLER_REVISION
            and result.get("probe_primitive_revision") == s16.s9.CONTROLLER_REVISION
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
    lattice = ctx.base_ctx.cfg["lattice_probe"]
    calibration = ctx.base_ctx.cfg["active_calibration"]
    dynamic = ctx.cfg["causal_model"]
    if backend == "serial":
        for index, spec in enumerate(pending):
            worker = LocalWorker(
                payloads[str(spec["experiment_id"])], library, bundle,
                f"stage42r3c3t13s20_serial_{index:04d}", selector, lattice,
                calibration, dynamic,
            )
            try:
                result = worker.evaluate(spec)
            finally:
                worker.close()
            _write_json_gz(ctx.paths.raw / f"{spec['experiment_id']}.json.gz", result)
            print(f"[T13S20] {index + 1}/{len(pending)}", flush=True)
    elif backend == "ray" and pending:
        import ray

        plan = s16.ensure_ray_worker_plan(
            ray, requested_workers=int(ctx.cfg["parallel"]["n_workers"]),
            pending_tasks=len(pending),
            ray_tmpdir=os.environ.get("RAY_TMPDIR") or ctx.cfg["storage"]["ray_tmpdir"],
            log_prefix="[T13S20]",
        )
        Actor = _ray_actor_class()
        completed = 0
        for batch_start in range(0, len(pending), plan.actor_count):
            batch = pending[batch_start:batch_start + plan.actor_count]
            actors, refs = [], {}
            for offset, spec in enumerate(batch):
                actor = Actor.remote(
                    payloads[str(spec["experiment_id"])], library, bundle,
                    f"stage42r3c3t13s20_{batch_start + offset:04d}", selector,
                    lattice, calibration, dynamic,
                )
                actors.append(actor)
                refs[actor.evaluate.remote(spec)] = spec
            try:
                while refs:
                    ready, _ = ray.wait(list(refs), num_returns=1, timeout=30.0)
                    if not ready:
                        print(f"[T13S20] waiting {completed}/{len(pending)}", flush=True)
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
                                "probe_primitive_revision": s16.s9.CONTROLLER_REVISION,
                                "experiment_id": str(spec["experiment_id"]),
                                "spec": copy.deepcopy(spec), "success": False,
                                "completed": True, "failure_reason": repr(exc),
                                "traceback": traceback.format_exc(),
                                "trajectory": [], "controller_trace": [],
                            }
                        _write_json_gz(ctx.paths.raw / f"{spec['experiment_id']}.json.gz", result)
                        completed += 1
                        print(f"[T13S20] {completed}/{len(pending)}", flush=True)
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


def _authenticate_s19_development(project: Path, cfg: Mapping[str, Any]) -> dict[str, Any]:
    frozen = cfg["source_s19_development"]
    run = (project / str(frozen["run_relative_path"])).resolve()
    state_path = run / "stage4_2r3c3t13s19_state.json"
    development = run / "analysis" / "s20_dynamic_card15_development.json"
    reproduction = run / "analysis" / "card15_failed_baseline_one_step_reproduction_v2.json"
    raw_paths = sorted(run.glob("**/raw/*.json.gz"))
    inventory_digest = hashlib.sha256()
    success = 0
    failed: list[str] = []
    roles: Counter[str] = Counter()
    stages: Counter[str] = Counter()
    parse_failures = []
    failed_sha = ""
    for path in raw_paths:
        sha = _sha256(path)
        inventory_digest.update(
            f"{path.name}\0{path.stat().st_size}\0{sha}\n".encode("utf-8")
        )
        try:
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                result = json.load(handle)
        except Exception as exc:
            parse_failures.append({"path": str(path), "failure_reason": repr(exc)})
            continue
        spec = result.get("spec") or {}
        stages[str(result.get("stage"))] += 1
        role = (
            "training_baseline" if spec.get("partition") == "training"
            and spec.get("r3c3_probe_id") == BASELINE_PROBE_ID
            else f"{spec.get('partition', 'unknown')}_{spec.get('r3c3_probe_id', 'unknown')}"
        )
        roles[role] += 1
        if bool(result.get("success")):
            success += 1
        else:
            experiment_id = str(result.get("experiment_id"))
            failed.append(experiment_id)
            if experiment_id == frozen["failed_experiment_id"]:
                failed_sha = sha
    state = _read_json(state_path) if state_path.is_file() else {}
    passed = bool(
        run.is_dir()
        and state_path.is_file()
        and _sha256(state_path) == frozen["final_state_sha256"]
        and development.is_file()
        and _sha256(development) == frozen["dynamic_card15_development_sha256"]
        and reproduction.is_file()
        and _sha256(reproduction) == frozen["failed_reproduction_v2_sha256"]
        and len(raw_paths) == int(frozen["raw_inventory_count"])
        and inventory_digest.hexdigest() == frozen["raw_inventory_digest"]
        and not parse_failures
        and stages == {"Stage4.2R3c3T13S19": 24}
        and roles == {"training_baseline": 24}
        and success == int(frozen["successful_training_baselines"])
        and failed == [str(frozen["failed_experiment_id"])]
        and failed_sha == frozen["failed_raw_sha256"]
        and bool(state.get("finished")) and not bool(state.get("primary_pass"))
        and state.get("stop_reason") == "training_baseline_or_lattice_gate_failed"
    )
    return {
        "run": str(run), "state_sha256": _sha256(state_path) if state_path.is_file() else "",
        "raw_count": len(raw_paths), "raw_inventory_digest": inventory_digest.hexdigest(),
        "success_count": success, "failed_experiment_ids": failed,
        "role_counts": dict(roles), "stage_counts": dict(stages),
        "parse_failure_count": len(parse_failures),
        "dynamic_card15_development_sha256": _sha256(development) if development.is_file() else "",
        "failed_reproduction_v2_sha256": _sha256(reproduction) if reproduction.is_file() else "",
        "passed": passed,
    }


def _freshness_audit(
    project: Path, candidate_pairs: set[str], cfg: Mapping[str, Any],
) -> dict[str, Any]:
    source_run = (project / str(cfg["source_s19_development"]["run_relative_path"])).resolve()
    hits: Counter[str] = Counter()
    role_hits: Counter[str] = Counter()
    parsed = 0
    failures = []
    for path in sorted(project.glob("stage4_2r3c3t13s*_runs/**/raw/*.json.gz")):
        if source_run in path.resolve().parents:
            continue
        try:
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                result = json.load(handle)
        except Exception as exc:
            failures.append({"path": str(path), "failure_reason": repr(exc)})
            continue
        parsed += 1
        pair = str((result.get("spec") or {}).get("pair_id", result.get("pair_id", "")))
        if pair in candidate_pairs:
            hits[pair] += 1
            spec = result.get("spec") or {}
            partition = str(spec.get("partition", "unknown"))
            probe = str(spec.get("r3c3_probe_id", "unknown"))
            role_hits[
                f"{partition}_{'baseline' if probe == BASELINE_PROBE_ID else 'probe'}"
            ] += 1
    minimum = int(cfg["freshness"]["minimum_prior_identification_raw"])
    return {
        "candidate_pair_count": len(candidate_pairs),
        "prior_identification_raw_parsed": parsed,
        "parse_failure_count": len(failures),
        "candidate_raw_hit_count": sum(hits.values()),
        "candidate_pair_hit_counts": dict(sorted(hits.items())),
        "candidate_role_hit_counts": dict(sorted(role_hits.items())),
        "excluded_authenticated_s19_run": str(source_run),
        "passed": bool(parsed >= minimum and not failures and not hits and not role_hits),
    }


def _snapshot_audit(table: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = []
    for context in table:
        directory = Path(str(context["restart_snapshot_dir"])).expanduser().resolve()
        passed, reason = False, ""
        try:
            manifest = _read_json(directory / "restart_snapshot_manifest.json")
            passed = bool(
                str(manifest.get("digest")) == str(context["restart_snapshot_manifest_digest"])
                and s16.s9.t11.t1.r1._validate_snapshot_inventory(directory, manifest)
            )
            if not passed:
                reason = "snapshot inventory mismatch"
        except Exception as exc:
            reason = repr(exc)
        rows.append({
            "pair_id": context["pair_id"], "history_member": context["history_member"],
            "snapshot_dir": str(directory), "passed": passed, "failure_reason": reason,
        })
    return {
        "expected": 40, "actual": len(rows),
        "pass_count": sum(row["passed"] for row in rows),
        "passed": len(rows) == 40 and all(row["passed"] for row in rows), "rows": rows,
    }


def _package_fingerprint() -> dict[str, Any]:
    project = _project_root()
    manifest = _read_json(project / "PACKAGE_MANIFEST.json")
    files = [str(path) for path in manifest["file_inventory"]]
    hashes = {path: _sha256(project / path) for path in files}
    required = {
        "configs/stage4_2r3c3t13s20_dynamic_exact_card15_pooled_observer_campaign_370ms.json",
        "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s20_dynamic_exact_card15_pooled_observer_campaign.py",
        "scripts/stage4_2r3c3t13s20_dynamic_exact_card15_pooled_observer_campaign.py",
    }
    if not required.issubset(hashes):
        raise ValueError("T13S20 package import closure is incomplete")
    return {"declared_file_count": len(files), "hashes": hashes, "digest": _digest(hashes)}


def _preaction_basis_preflight(ctx: Context, specs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    baselines = [spec for spec in specs if spec["r3c3_probe_id"] == BASELINE_PROBE_ID]
    library, bundle, selector = _library_bundle_selector(ctx)
    rows = []
    for index, spec in enumerate(baselines):
        worker = s16.s9.t11.t1.r1.LocalPlantReplayWorker(
            _payload(ctx, spec), library, bundle, f"stage42r3c3t13s20_preaction_{index:03d}", selector,
        )
        try:
            worker.base_worker.env.reset()
            zero = np.zeros(N_COILS, dtype=np.float32)
            initial = s16.s9.t11.t1.r1._state_record_full(worker.base_worker.env, 0, zero)
            controller = DynamicExactCard15ProbeController(
                worker.base_worker, bundle, s16.s9._controller_spec(spec), initial,
                ctx.base_ctx.cfg["lattice_probe"], ctx.base_ctx.cfg["active_calibration"],
                ctx.cfg["causal_model"],
            )
            action, trace = controller.action(initial)
            passed = bool(
                trace["r3c3t13s16_lattice_event"] == "calibration_issue"
                and np.all(np.isfinite(action)) and float(np.max(np.abs(action))) <= 1.0 + 1e-12
                and int(controller._fixed_basis_rank) == 4
                and float(controller._fixed_basis_condition) <= 1.1
                and bool(trace["r3c3t13s20_dynamic_exact_card15"])
            )
            rows.append({
                "experiment_id": spec["experiment_id"], "pair_id": spec["pair_id"],
                "history_member": spec["history_member"],
                "fixed_basis_rank": int(controller._fixed_basis_rank),
                "fixed_basis_condition": float(controller._fixed_basis_condition),
                "passed": passed,
            })
        except Exception as exc:
            rows.append({"experiment_id": spec["experiment_id"], "passed": False, "failure_reason": repr(exc)})
        finally:
            worker.close()
    return {
        "expected": 40, "actual": len(rows), "pass_count": sum(row["passed"] for row in rows),
        "plant_advance_count": 0, "real_tsc_executed": False,
        "passed": len(rows) == 40 and all(row["passed"] for row in rows), "rows": rows,
    }


def _prepare_dirs(paths: Paths) -> None:
    for path in (
        paths.run_dir, paths.raw, paths.variants, paths.specs,
        paths.source_reference, paths.analysis, paths.model,
    ):
        path.mkdir(parents=True, exist_ok=True)


def prepare_offline(ctx: Context) -> dict[str, Any]:
    if ctx.paths.manifest.exists() or ctx.paths.state.exists() or list(ctx.paths.raw.glob("*.json.gz")):
        raise ValueError("T13S20 fresh offline identity is not empty")
    _prepare_dirs(ctx.paths)
    source = s13._authenticate_sources(ctx.base_ctx.base_ctx)
    table = build_context_table(ctx)
    specs = build_specs(ctx, table)
    candidate_pairs = {str(row["pair_id"]) for row in table}
    s19_development = _authenticate_s19_development(_project_root(), ctx.cfg)
    freshness = _freshness_audit(_project_root(), candidate_pairs, ctx.cfg)
    snapshots = _snapshot_audit(table)
    package = _package_fingerprint()
    preaction = _preaction_basis_preflight(ctx, specs)
    context_digest, spec_digest = _digest(table), _digest(specs)
    manifest = {
        "schema_version": 1, "stage": STAGE,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "config_path": str(ctx.config_path), "config_sha256": _sha256(ctx.config_path),
        "source_authentication": source, "s19_development_authentication": s19_development,
        "freshness_audit": freshness,
        "context_count": 40, "context_table_digest": context_digest,
        "spec_count": 360, "spec_digest": spec_digest,
        "snapshot_pass_count": snapshots["pass_count"],
        "package_fingerprint": package,
        "training_model_hashed_before_calibration": True,
        "calibrated_tube_hashed_before_holdout": True,
        "formal_timing_unchanged": True,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "bc_dagger_or_rl_allowed": False,
    }
    state = {
        "schema_version": 1, "stage": STAGE, "phase_status": "offline_ready",
        "finished": False, "primary_pass": False, "real_tsc_executed": False,
        "new_raw_count": 0, "context_table_digest": context_digest,
        "spec_digest": spec_digest, "package_digest": package["digest"],
        "training_model_sha256": "", "calibrated_tube_sha256": "",
        "heldout_outcomes_opened": False, "stop_reason": "", "verdict": {},
    }
    _write_json(ctx.paths.manifest, manifest)
    _write_json(ctx.paths.state, state)
    _write_json(ctx.paths.source_reference / "context_table.json", table)
    _write_json(ctx.paths.source_reference / "source_authentication.json", source)
    _write_json(
        ctx.paths.source_reference / "s19_development_authentication.json",
        s19_development,
    )
    _write_json(ctx.paths.source_reference / "freshness_audit.json", freshness)
    _write_json(ctx.paths.source_reference / "snapshot_audit.json", snapshots)
    _write_json(ctx.paths.specs / "all_specs.json", specs)
    for partition in ("training", "calibration", "holdout"):
        for baseline in (True, False):
            name = "baseline" if baseline else "probe"
            _write_json(
                ctx.paths.specs / f"{partition}_{name}_specs.json",
                _partition_specs(specs, partition, baseline=baseline),
            )
    output = {
        "schema_version": 1, "stage": STAGE, "phase": "zero_plant_advance_preflight",
        "context_count": 40, "spec_count": 360,
        "freshness": freshness, "s19_development": s19_development,
        "snapshot_pass_count": snapshots["pass_count"],
        "preaction_basis_pass_count": preaction["pass_count"],
        "new_raw_count": 0, "real_tsc_executed": False,
        "passed": bool(
            source["passed"] and s19_development["passed"] and freshness["passed"]
            and snapshots["passed"] and preaction["passed"]
        ),
    }
    _write_json(ctx.paths.analysis / "preaction_basis_preflight.json", preaction)
    _write_json(ctx.paths.analysis / "offline_preflight.json", output)
    if not output["passed"]:
        raise ValueError("T13S20 offline preflight failed")
    return output


def _require_phase(ctx: Context, phase: str) -> dict[str, Any]:
    state = _read_json(ctx.paths.state)
    if state.get("phase_status") != phase or bool(state.get("finished")):
        raise ValueError(f"T13S20 expected open phase {phase}")
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
        raise ValueError("T13S20 frozen spec matrix changed")
    return saved


def _lattice_gate(
    ctx: Context, baselines: Sequence[Mapping[str, Any]], probes: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    by_context: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for spec in probes:
        by_context[(str(spec["pair_id"]), str(spec["history_member"]))].append(spec)
    library, bundle, selector = _library_bundle_selector(ctx)
    rows = []
    for index, baseline_spec in enumerate(baselines):
        key = (str(baseline_spec["pair_id"]), str(baseline_spec["history_member"]))
        baseline = s16.s9.t11.t1.r3c3.read_json_gz(
            ctx.paths.raw / f"{baseline_spec['experiment_id']}.json.gz"
        )
        worker = s16.s9.t11.t1.r1.LocalPlantReplayWorker(
            _payload(ctx, baseline_spec), library, bundle,
            f"stage42r3c3t13s20_lattice_{index:03d}", selector,
        )
        try:
            for spec in sorted(by_context[key], key=lambda row: str(row["experiment_id"])):
                passed, reason, events = True, "", []
                try:
                    initial = copy.deepcopy(dict(baseline["trajectory"][0])); initial["step_index"] = 0
                    controller = DynamicExactCard15ProbeController(
                        worker.base_worker, bundle, s16.s9._controller_spec(spec), initial,
                        ctx.base_ctx.cfg["lattice_probe"], ctx.base_ctx.cfg["active_calibration"],
                        ctx.cfg["causal_model"],
                    )
                    for step in range(12):
                        state = copy.deepcopy(dict(baseline["trajectory"][step])); state["step_index"] = step
                        action, trace = controller.action(state)
                        prediction = trace["r3c3t13s9_actuator_prediction"]
                        event = trace["r3c3t13s16_lattice_event"]
                        if event != "none":
                            events.append(event)
                        passed = bool(
                            passed and np.all(np.isfinite(action))
                            and float(np.max(np.abs(action))) <= 1.0 + 1e-12
                            and not any(prediction["action_saturated"])
                            and not any(prediction["current_limit_clipped"])
                        )
                        if step + 1 < len(baseline["trajectory"]):
                            next_state = copy.deepcopy(dict(baseline["trajectory"][step + 1]))
                            next_state["step_index"] = step + 1
                            controller.advance(next_state)
                    expected = [
                        "calibration_issue", "calibration_cancel",
                        "calibration_issue", "calibration_cancel",
                        "calibration_issue", "calibration_cancel",
                        "calibration_issue", "calibration_cancel",
                        "response_issue", "response_cancel",
                    ]
                    passed = bool(passed and events == expected)
                    if len(controller._s20_running_net) != N_COILS or any(
                        value != 0 for value in controller._s20_running_net
                    ):
                        passed = False
                except Exception as exc:
                    passed, reason = False, repr(exc)
                rows.append({
                    "experiment_id": spec["experiment_id"], "pair_id": key[0],
                    "history_member": key[1], "events": events,
                    "passed": passed, "failure_reason": reason,
                })
        finally:
            worker.close()
    return {
        "expected": len(probes), "actual": len(rows),
        "pass_count": sum(row["passed"] for row in rows),
        "plant_advance_count": 0, "real_tsc_executed": False,
        "passed": len(rows) == len(probes) and all(row["passed"] for row in rows),
        "rows": rows,
    }


def _dynamic_design(
    trace: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any],
) -> tuple[np.ndarray, dict[str, Any]]:
    if len(trace) < 10:
        raise ValueError("T13S20 dynamic design trace is incomplete")
    inputs = np.asarray([
        trace[index].get("r3c3t13s20_dynamic_input_coordinate")
        for index in range(8)
    ] + list(cfg["causal_model"]["settling_input_coordinates"]), dtype=float)
    polynomial = np.polynomial.legendre.legvander(np.linspace(-1.0, 1.0, 10), 3)
    design = np.column_stack((polynomial, inputs))
    rank = int(np.linalg.matrix_rank(design))
    condition = float(np.linalg.cond(design))
    if (
        inputs.shape != (10, 4) or design.shape != (10, 8)
        or not np.all(np.isfinite(design)) or rank != 8
        or not math.isfinite(condition)
        or condition > float(cfg["causal_model"]["maximum_dynamic_design_condition"])
    ):
        raise ValueError("T13S20 dynamic causal design failed rank/condition gate")
    return design, {
        "dynamic_design_rank": rank,
        "dynamic_design_condition": condition,
        "dynamic_input_coordinates": inputs.tolist(),
        "passed": True,
    }


def _dynamic_calibration_trace_audit(
    result: Mapping[str, Any], cfg: Mapping[str, Any],
) -> dict[str, Any]:
    trace = result.get("controller_trace") or []
    if len(trace) < 10:
        return {"passed": False, "failure_reason": "incomplete trace"}
    try:
        design, design_audit = _dynamic_design(trace, cfg)
    except Exception as exc:
        return {"passed": False, "failure_reason": repr(exc)}
    rows = []
    total = [Decimal(0) for _ in range(N_COILS)]
    for step in range(8):
        row = trace[step]
        lattice = row.get("r3c3t13s16_lattice") or {}
        index = step // 2
        sign = 1 if step % 2 == 0 else -1
        event = "calibration_issue" if sign > 0 else "calibration_cancel"
        coordinate = np.asarray(
            row.get("r3c3t13s20_dynamic_input_coordinate") or [], dtype=float
        )
        actual = lattice.get("signed_delta_field_kAt_tsc") or []
        for coil, value in enumerate(actual if len(actual) == N_COILS else []):
            total[coil] += Decimal(str(value))
        prediction = row.get("r3c3t13s9_actuator_prediction") or {}
        target = (
            lattice.get("positive_target_fields") if sign > 0
            else lattice.get("target_fields")
        ) or []
        primary = float(sign * coordinate[index]) if coordinate.shape == (4,) else math.nan
        cross = (
            float(np.max(np.abs(np.delete(coordinate, index))))
            if coordinate.shape == (4,) else math.inf
        )
        passed = bool(
            row.get("r3c3t13s16_lattice_event") == event
            and int(row.get("r3c3t13s16_event_index", -1)) == index
            and int(row.get("r3c3t13s16_event_sign", 0)) == sign
            and lattice.get("selected_method")
            == "dynamic_nearest_exact_card15_relative_current_center"
            and bool(lattice.get("passed")) and bool(lattice.get("dynamic_geometry_passed"))
            and list(prediction.get("card15_fields") or []) == list(target)
            and coordinate.shape == (4,) and np.all(np.isfinite(coordinate))
            and float(cfg["causal_model"]["minimum_signed_primary_coordinate"])
            <= primary <= float(cfg["causal_model"]["maximum_signed_primary_coordinate"])
            and cross <= float(cfg["causal_model"]["maximum_cross_coordinate_abs"])
            and float(lattice.get("desired_actual_current_cosine", -math.inf))
            >= float(cfg["causal_model"]["minimum_dynamic_basis_cosine"])
            and float(lattice.get("relative_off_basis_residual", math.inf))
            <= float(cfg["causal_model"]["maximum_dynamic_off_basis_residual"])
            and row.get("r3c3t13s20_actual_signed_delta_field_kAt_tsc") == actual
            and bool(row.get("r3c3t13s20_dynamic_exact_card15"))
        )
        rows.append({
            "step": step, "direction_index": index, "sign": sign,
            "signed_primary_coordinate": primary,
            "maximum_cross_coordinate_abs": cross, "passed": passed,
        })
    exact_net = all(value == 0 for value in total)
    trace_exact = bool(trace[7].get("r3c3t13s20_exact_calibration_net_zero"))
    return {
        "expected_event_count": 8, "actual_event_count": len(rows),
        "pass_count": sum(row["passed"] for row in rows),
        "exact_calibration_net_zero": exact_net,
        "trace_exact_calibration_net_zero": trace_exact,
        **design_audit,
        "passed": bool(
            design.shape == (10, 8) and len(rows) == 8 and all(row["passed"] for row in rows)
            and exact_net and trace_exact
        ),
        "rows": rows,
    }


def _execution_audit(
    ctx: Context, specs: Sequence[Mapping[str, Any]], *, baseline: bool,
) -> dict[str, Any]:
    state_map = s13._source_state_map(ctx.base_ctx.base_ctx)
    base_source_ctx = ctx.base_ctx.base_ctx.base_ctx.base_ctx.base_ctx.source_ctx.source_ctx
    all_specs = _all_specs(ctx)
    baseline_map = {}
    for spec in (row for row in all_specs if row["r3c3_probe_id"] == BASELINE_PROBE_ID):
        path = ctx.paths.raw / f"{spec['experiment_id']}.json.gz"
        if _result_complete(path, spec):
            baseline_map[(str(spec["pair_id"]), str(spec["history_member"]))] = s16.s9.t11.t1.r3c3.read_json_gz(path)
    forbidden_keys = (
        "future_measurement_used", "hidden_wire_used", "source_action_used",
        "source_coil_current_used", "source_wire_current_used", "current_run_future_used",
        "pair_or_history_label_used", "source_result_used",
        "future_probe_schedule_available_to_underlying_controller",
        "r3c3t13s20_partition_label_used",
    )
    rows = []
    for spec in specs:
        path = ctx.paths.raw / f"{spec['experiment_id']}.json.gz"
        if not _result_complete(path, spec):
            rows.append({
                "experiment_id": spec["experiment_id"], "passed": False,
                "failure_class": "runtime_or_raw_error", "failure_reason": "missing or incomplete raw",
            })
            continue
        result = s16.s9.t11.t1.r3c3.read_json_gz(path)
        trajectory, trace = result["trajectory"], result["controller_trace"]
        payload = _payload(ctx, spec)
        currents = np.asarray([row["currents_a_tsc"] for row in trajectory], dtype=float)
        actions = np.asarray([row["action_norm_tsc"] for row in trace], dtype=float)
        minimum, maximum = s13._current_limits_tsc(payload)
        center, half = 0.5 * (minimum + maximum), 0.5 * (maximum - minimum)
        utilization = float(np.max(np.abs((currents - center) / half)))
        restart = s16.s9.t11.t1.r3b._control_row(
            base_source_ctx, result, state_map[str(spec["state_generation_experiment_id"])]
        )
        phase = s16.s9.t11.t1.r3c1._phase_trace_valid(result)
        actuator = s16.s9._actuator_execution(result, ctx.base_ctx.cfg["lattice_probe"])
        calibration = _dynamic_calibration_trace_audit(result, ctx.cfg)
        events = [
            row.get("r3c3t13s16_lattice_event") for row in trace
            if row.get("r3c3t13s16_lattice_event") != "none"
        ]
        expected = [
            "calibration_issue", "calibration_cancel", "calibration_issue", "calibration_cancel",
            "calibration_issue", "calibration_cancel", "calibration_issue", "calibration_cancel",
        ] + ([] if baseline else ["response_issue", "response_cancel"])
        response_cancel = s16.s9._cancellation_policy_trace(result, baseline=baseline)
        pre_response = {"passed": True}
        if not baseline:
            base = baseline_map.get((str(spec["pair_id"]), str(spec["history_member"])))
            pre_response = {"passed": False} if base is None else s16._pre_response_semantic_exact(result, base)
        forbidden = sum(any(bool(row.get(key)) for key in forbidden_keys) for row in trace)
        runtime = bool(
            result["success"] and len(trajectory) == int(spec["horizon_steps"]) + 1
            and len(trace) == int(spec["horizon_steps"])
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
            and calibration["passed"] and response_zero and pre_response["passed"]
            and utilization <= float(ctx.base_ctx.cfg["lattice_probe"]["maximum_current_utilization"]) + 1e-12
        )
        rows.append({
            "experiment_id": spec["experiment_id"], "pair_id": spec["pair_id"],
            "history_member": spec["history_member"], "partition": spec["partition"],
            "runtime_pass": runtime, "restart_pass": restart_pass,
            "causality_schedule_pass": trace_pass, "actuator_pass": bool(actuator["passed"]),
            "calibration_pass": bool(calibration["passed"]),
            "dynamic_design_rank": calibration.get("dynamic_design_rank", 0),
            "dynamic_design_condition": calibration.get("dynamic_design_condition", math.inf),
            "exact_calibration_net_zero": calibration.get("exact_calibration_net_zero", False),
            "response_zero_net_pass": response_zero,
            "pre_response_baseline_exact": bool(pre_response["passed"]),
            "maximum_current_utilization": utilization,
            "forbidden_trace_count": forbidden,
            "formal_contract_pass_diagnostic": bool(restart.get("formal_contract_pass")),
            "passed": passed,
        })
    return {
        "expected": len(specs), "actual": len(rows),
        "pass_count": sum(row["passed"] for row in rows),
        "formal_tracking_pass_count_diagnostic_only": sum(
            bool(row.get("formal_contract_pass_diagnostic")) for row in rows
        ),
        "passed": len(rows) == len(specs) and all(row["passed"] for row in rows),
        "rows": rows,
    }


def run_baseline(
    ctx: Context, partition: str, *, backend: str, resume: bool,
) -> dict[str, Any]:
    previous = {
        "training": "offline_ready", "calibration": "training_model_frozen",
        "holdout": "calibration_tube_frozen",
    }[partition]
    _require_phase(ctx, previous)
    specs = _all_specs(ctx)
    baselines = _partition_specs(specs, partition, baseline=True)
    probes = _partition_specs(specs, partition, baseline=False)
    execution = evaluate_specs(ctx, baselines, backend=backend, resume=resume)
    audit = _execution_audit(ctx, baselines, baseline=True) if execution["passed"] else {"passed": False}
    lattice = _lattice_gate(ctx, baselines, probes) if audit["passed"] else {"passed": False}
    output = {
        "schema_version": 1, "stage": STAGE,
        "phase": f"{partition}_baseline_execution_and_zero_plant_lattice_gate",
        "execution": execution, "execution_audit": audit, "lattice_gate": lattice,
        "passed": bool(execution["passed"] and audit["passed"] and lattice["passed"]),
    }
    _write_json(ctx.paths.analysis / f"{partition}_baseline_gate.json", output)
    raw_count = len(list(ctx.paths.raw.glob("*.json.gz")))
    if output["passed"]:
        _set_state(
            ctx, phase_status=f"{partition}_baseline_complete", real_tsc_executed=True,
            new_raw_count=raw_count, stop_reason="",
            heldout_outcomes_opened=partition == "holdout",
        )
    else:
        _set_state(
            ctx, finished=True, primary_pass=False, real_tsc_executed=bool(raw_count),
            new_raw_count=raw_count, stop_reason=f"{partition}_baseline_or_lattice_gate_failed",
            verdict={"route": EXECUTION_FAIL_ROUTE, "passed": False},
        )
    return output


def run_probe(
    ctx: Context, partition: str, *, backend: str, resume: bool,
) -> dict[str, Any]:
    _require_phase(ctx, f"{partition}_baseline_complete")
    specs = _partition_specs(_all_specs(ctx), partition, baseline=False)
    execution = evaluate_specs(ctx, specs, backend=backend, resume=resume)
    audit = _execution_audit(ctx, specs, baseline=False) if execution["passed"] else {"passed": False}
    output = {
        "schema_version": 1, "stage": STAGE,
        "phase": f"{partition}_signed_probe_execution",
        "execution": execution, "execution_audit": audit,
        "passed": bool(execution["passed"] and audit["passed"]),
    }
    _write_json(ctx.paths.analysis / f"{partition}_probe_execution.json", output)
    raw_count = len(list(ctx.paths.raw.glob("*.json.gz")))
    if output["passed"]:
        _set_state(
            ctx, phase_status=f"{partition}_probe_complete", real_tsc_executed=True,
            new_raw_count=raw_count, stop_reason="",
            heldout_outcomes_opened=partition == "holdout",
        )
    else:
        _set_state(
            ctx, finished=True, primary_pass=False, real_tsc_executed=True,
            new_raw_count=raw_count, stop_reason=f"{partition}_probe_runtime_gate_failed",
            verdict={"route": EXECUTION_FAIL_ROUTE, "passed": False},
        )
    return output


def _partition_raw(
    ctx: Context, specs: Sequence[Mapping[str, Any]], partition: str,
) -> list[dict[str, Any]]:
    selected = [spec for spec in specs if spec["partition"] == partition]
    output = []
    for spec in selected:
        path = ctx.paths.raw / f"{spec['experiment_id']}.json.gz"
        if not _result_complete(path, spec):
            raise ValueError(f"T13S20 incomplete {partition} raw: {spec['experiment_id']}")
        output.append(s16.s9.t11.t1.r3c3.read_json_gz(path))
    expected = {"training": 216, "calibration": 72, "holdout": 72}[partition]
    if len(output) != expected:
        raise ValueError("T13S20 partition raw coverage changed")
    return output


def _causal_row(
    result: Mapping[str, Any], baseline: Mapping[str, Any], payload: Mapping[str, Any],
    cfg: Mapping[str, Any],
) -> dict[str, Any]:
    trace = result["controller_trace"]
    forbidden_keys = (
        "pair_or_history_label_used", "source_action_used", "source_result_used",
        "source_wire_current_used", "source_coil_current_used", "hidden_wire_used",
        "future_measurement_used", "current_run_future_used", "r3c3t13s20_partition_label_used",
    )
    forbidden = sum(bool(trace[10].get(key, False)) for key in forbidden_keys)
    design, design_audit = _dynamic_design(trace, cfg)
    outputs = s18.s17._visible_outputs_prefix(result)
    coefficients = np.linalg.pinv(design) @ outputs
    _, coordinate, coordinate_radius, cosine, off_basis = s18._basis_and_coordinate(result, payload)
    query = np.concatenate((np.zeros(4), coordinate))
    prediction = query @ coefficients
    prediction_radius = np.abs(coefficients[-4:]).T @ coordinate_radius
    feature = np.concatenate((prediction, coordinate))
    feature_radius = np.concatenate((prediction_radius, coordinate_radius))
    actual = s18.s17._actual_response(result, baseline)
    if (
        feature.shape != (9,) or feature_radius.shape != (9,)
        or actual.shape != (5,) or not np.all(np.isfinite(feature))
        or not np.all(np.isfinite(feature_radius)) or not np.all(np.isfinite(actual))
        or cosine < float(cfg["causal_model"]["minimum_response_basis_cosine"])
        or off_basis > float(cfg["causal_model"]["maximum_response_off_basis_residual"])
        or forbidden
    ):
        raise ValueError("T13S20 causal row failed")
    spec = result["spec"]
    return {
        "experiment_id": str(result["experiment_id"]),
        "baseline_experiment_id": str(baseline["experiment_id"]),
        "pair_id": str(spec["pair_id"]), "history_member": str(spec["history_member"]),
        "partition": str(spec["partition"]), "feature": feature.tolist(),
        "feature_radius": feature_radius.tolist(), "actual_response": actual.tolist(),
        "response_basis_cosine": cosine, "response_off_basis_residual": off_basis,
        "dynamic_design_rank": design_audit["dynamic_design_rank"],
        "dynamic_design_condition": design_audit["dynamic_design_condition"],
        "same_trajectory_dynamic_input_coordinates": True,
        "forbidden_predictor_input_count": forbidden,
    }


def _extract_rows(
    ctx: Context, specs: Sequence[Mapping[str, Any]], partition: str,
) -> list[dict[str, Any]]:
    raw = _partition_raw(ctx, specs, partition)
    baselines = {
        (str(row["spec"]["pair_id"]), str(row["spec"]["history_member"])): row
        for row in raw if row["spec"]["r3c3_probe_id"] == BASELINE_PROBE_ID
    }
    rows = []
    for result in sorted(raw, key=lambda row: str(row["experiment_id"])):
        if result["spec"]["r3c3_probe_id"] == BASELINE_PROBE_ID:
            continue
        key = (str(result["spec"]["pair_id"]), str(result["spec"]["history_member"]))
        payload = _payload(ctx, result["spec"])
        rows.append(_causal_row(result, baselines[key], payload, ctx.cfg))
    expected = {"training": 192, "calibration": 64, "holdout": 64}[partition]
    pairs = {row["pair_id"] for row in rows}
    expected_pairs = {"training": 12, "calibration": 4, "holdout": 4}[partition]
    if len(rows) != expected or len(pairs) != expected_pairs:
        raise ValueError("T13S20 response row coverage changed")
    return rows


def _build_training_artifact(
    ctx: Context, specs: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    rows = _extract_rows(ctx, specs, "training")
    x = np.asarray([row["feature"] for row in rows], dtype=float)
    y = np.asarray([row["actual_response"] for row in rows], dtype=float)
    groups = np.asarray([row["pair_id"] for row in rows])
    scales = np.asarray(ctx.cfg["causal_model"]["response_scales"], dtype=float)
    grid = tuple(map(float, ctx.cfg["pooled_model"]["ridge_grid"]))
    std_floor = float(ctx.cfg["pooled_model"]["standard_deviation_floor"])
    candidates = []
    predictions: dict[float, np.ndarray] = {}
    for ridge in grid:
        prediction = s18._oof(x, y, groups, ridge, scales, std_floor)
        predictions[ridge] = prediction
        scaled_error = np.abs(prediction - y) / scales
        candidates.append({
            "ridge": ridge,
            "maximum_absolute_scaled_oof_error": float(np.max(scaled_error)),
            "mean_squared_scaled_oof_error": float(np.mean(scaled_error ** 2)),
        })
    selected = min(candidates, key=lambda row: (
        row["maximum_absolute_scaled_oof_error"], row["mean_squared_scaled_oof_error"], row["ridge"]
    ))
    ridge = float(selected["ridge"])
    oof = predictions[ridge]
    absolute = np.abs(oof - y)
    scaled = absolute / scales
    maximum_residual = np.max(absolute, axis=0)
    model = s18._fit_model(x, y, ridge, scales, std_floor)
    threshold = float(ctx.cfg["causal_model"]["maximum_absolute_scaled_point_error"])
    artifact = {
        "schema_version": 1, "stage": STAGE,
        "phase": "training_model_frozen_before_calibration",
        "training_response_row_count": 192, "training_pair_count": 12,
        "training_experiment_ids": [row["experiment_id"] for row in rows],
        "forbidden_predictor_input_count": sum(row["forbidden_predictor_input_count"] for row in rows),
        "candidate_scores": candidates, "selected_ridge": ridge,
        "model": s18._serialize_model(model),
        "training_oof_rows": [
            {
                "experiment_id": row["experiment_id"],
                "prediction": prediction.tolist(),
                "actual_response": actual.tolist(),
                "absolute_error": error.tolist(),
                "maximum_absolute_scaled_error": float(np.max(error / scales)),
            }
            for row, prediction, actual, error in zip(rows, oof, y, absolute)
        ],
        "training_maximum_oof_residual": maximum_residual.tolist(),
        "maximum_absolute_scaled_oof_error": float(np.max(scaled)),
        "calibration_outcome_access_count_before_model_hash": 0,
        "holdout_outcome_access_count_before_model_hash": 0,
        "passed": bool(
            len(set(groups)) == 12
            and float(np.max(scaled)) <= threshold
            and not sum(row["forbidden_predictor_input_count"] for row in rows)
        ),
    }
    audit = {
        "schema_version": 1, "stage": STAGE, "phase": "training_whole_pair_oof",
        "response_rows": 192, "pair_count": 12,
        "selected_ridge": ridge,
        "maximum_absolute_scaled_oof_error": float(np.max(scaled)),
        "point_pass_count": int(np.sum(np.max(scaled, axis=1) <= threshold)),
        "forbidden_predictor_input_count": artifact["forbidden_predictor_input_count"],
        "passed": artifact["passed"],
    }
    return audit, artifact


def run_fit_training(ctx: Context) -> dict[str, Any]:
    _require_phase(ctx, "training_probe_complete")
    specs = _all_specs(ctx)
    audit, artifact = _build_training_artifact(ctx, specs)
    _write_json(ctx.paths.analysis / "training_model_audit.json", audit)
    if not artifact["passed"]:
        _set_state(
            ctx, finished=True, primary_pass=False, stop_reason="training_model_gate_failed",
            verdict={"route": TRAINING_FAIL_ROUTE, "passed": False},
        )
        return audit
    path = ctx.paths.model / "training_pooled_observer.json"
    _write_json(path, artifact)
    sha = _sha256(path)
    _set_state(ctx, phase_status="training_model_frozen", training_model_sha256=sha)
    audit.update({"training_model_sha256": sha})
    _write_json(ctx.paths.analysis / "training_model_audit.json", audit)
    return audit


def _evaluate_rows(
    ctx: Context, rows: Sequence[Mapping[str, Any]], model: Mapping[str, np.ndarray],
    base_residual: np.ndarray,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    scales = np.asarray(ctx.cfg["causal_model"]["response_scales"], dtype=float)
    floor = np.asarray(ctx.cfg["causal_model"]["response_floor"], dtype=float)
    caps = np.asarray(ctx.cfg["causal_model"]["belief_halfwidth_caps"], dtype=float)
    multiplier = float(ctx.cfg["pooled_model"]["tube_multiplier"])
    threshold = float(ctx.cfg["causal_model"]["maximum_absolute_scaled_point_error"])
    x = np.asarray([row["feature"] for row in rows], dtype=float)
    actual = np.asarray([row["actual_response"] for row in rows], dtype=float)
    prediction = s18._predict(model, x, scales)
    error = np.abs(prediction - actual)
    radii = np.asarray([row["feature_radius"] for row in rows], dtype=float)
    propagation = radii @ np.abs(model["sensitivity"]).T
    halfwidth = floor + multiplier * base_residual + propagation
    output = []
    for row, pred, truth, err, width in zip(rows, prediction, actual, error, halfwidth):
        scaled_error = err / scales
        point = bool(np.max(scaled_error) <= threshold)
        containment = bool(np.all(err <= width + 1e-15))
        cap = bool(np.all(width <= caps + 1e-15))
        output.append({
            "experiment_id": row["experiment_id"], "pair_id": row["pair_id"],
            "history_member": row["history_member"], "prediction": pred.tolist(),
            "actual_response": truth.tolist(), "absolute_error": err.tolist(),
            "maximum_absolute_scaled_error": float(np.max(scaled_error)),
            "halfwidth": width.tolist(), "point_pass": point,
            "containment_pass": containment, "cap_pass": cap,
            "passed": bool(point and containment and cap),
        })
    summary = {
        "response_row_count": len(output),
        "point_pass_count": sum(row["point_pass"] for row in output),
        "containment_pass_count": sum(row["containment_pass"] for row in output),
        "cap_pass_count": sum(row["cap_pass"] for row in output),
        "joint_pass_count": sum(row["passed"] for row in output),
        "maximum_absolute_scaled_point_error": float(np.max(error / scales)),
        "maximum_absolute_error": np.max(error, axis=0).tolist(),
        "maximum_halfwidth": np.max(halfwidth, axis=0).tolist(),
        "passed": bool(all(row["passed"] for row in output)),
    }
    return output, summary


def _build_calibration_artifact(
    ctx: Context, specs: Sequence[Mapping[str, Any]], training: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    rows = _extract_rows(ctx, specs, "calibration")
    model = s18._deserialize_model(training["model"])
    scales = np.asarray(ctx.cfg["causal_model"]["response_scales"], dtype=float)
    x = np.asarray([row["feature"] for row in rows], dtype=float)
    actual = np.asarray([row["actual_response"] for row in rows], dtype=float)
    prediction = s18._predict(model, x, scales)
    calibration_residual = np.max(np.abs(prediction - actual), axis=0)
    training_residual = np.asarray(training["training_maximum_oof_residual"], dtype=float)
    calibrated = np.maximum(training_residual, calibration_residual)
    evaluated, summary = _evaluate_rows(ctx, rows, model, calibrated)
    artifact = {
        "schema_version": 1, "stage": STAGE,
        "phase": "calibrated_tube_frozen_before_holdout",
        "training_model_sha256": _sha256(ctx.paths.model / "training_pooled_observer.json"),
        "calibration_response_row_count": 64, "calibration_pair_count": 4,
        "training_maximum_oof_residual": training_residual.tolist(),
        "calibration_maximum_absolute_residual": calibration_residual.tolist(),
        "calibrated_componentwise_residual": calibrated.tolist(),
        "tube_multiplier": 4.0,
        "calibration_rows": evaluated, "calibration_summary": summary,
        "holdout_outcome_access_count_before_tube_hash": 0,
        "passed": bool(summary["passed"]),
    }
    audit = {"schema_version": 1, "stage": STAGE, "phase": "calibration_tube_gate", **summary}
    return audit, artifact


def run_calibrate(ctx: Context) -> dict[str, Any]:
    state = _require_phase(ctx, "calibration_probe_complete")
    model_path = ctx.paths.model / "training_pooled_observer.json"
    if _sha256(model_path) != state["training_model_sha256"]:
        raise ValueError("T13S20 training model changed before calibration")
    training = _read_json(model_path)
    audit, artifact = _build_calibration_artifact(ctx, _all_specs(ctx), training)
    _write_json(ctx.paths.analysis / "calibration_tube_audit.json", audit)
    if not artifact["passed"]:
        _set_state(
            ctx, finished=True, primary_pass=False, stop_reason="calibration_tube_gate_failed",
            verdict={"route": CALIBRATION_FAIL_ROUTE, "passed": False},
        )
        return audit
    path = ctx.paths.model / "calibrated_response_tube.json"
    _write_json(path, artifact)
    sha = _sha256(path)
    _set_state(ctx, phase_status="calibration_tube_frozen", calibrated_tube_sha256=sha)
    audit.update({"calibrated_tube_sha256": sha})
    _write_json(ctx.paths.analysis / "calibration_tube_audit.json", audit)
    return audit


def _build_holdout_result(
    ctx: Context, specs: Sequence[Mapping[str, Any]], training: Mapping[str, Any],
    tube: Mapping[str, Any],
) -> dict[str, Any]:
    rows = _extract_rows(ctx, specs, "holdout")
    model = s18._deserialize_model(training["model"])
    residual = np.asarray(tube["calibrated_componentwise_residual"], dtype=float)
    evaluated, summary = _evaluate_rows(ctx, rows, model, residual)
    return {
        "schema_version": 1, "stage": STAGE,
        "phase": "fresh_whole_pair_holdout_final",
        "route": PASS_ROUTE if summary["passed"] else HOLDOUT_FAIL_ROUTE,
        "training_model_sha256": _sha256(ctx.paths.model / "training_pooled_observer.json"),
        "calibrated_tube_sha256": _sha256(ctx.paths.model / "calibrated_response_tube.json"),
        "training_real_rollouts": 216, "calibration_real_rollouts": 72,
        "holdout_real_rollouts": 72, "total_real_rollouts": 360,
        "holdout_outcome_access_after_tube_hash_count": 64,
        "forbidden_predictor_input_count": 0,
        "runtime_or_environment_error_count": 0,
        "raw_or_restart_error_count": 0,
        "statistics_or_reporting_error_count": 0,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "real_tsc_executed": True, "rows": evaluated, **summary,
    }


def independent_postprocess(ctx: Context, final: Mapping[str, Any]) -> dict[str, Any]:
    specs = _all_specs(ctx)
    saved_training = _read_json(ctx.paths.model / "training_pooled_observer.json")
    saved_tube = _read_json(ctx.paths.model / "calibrated_response_tube.json")
    _, rebuilt_training = _build_training_artifact(ctx, specs)
    _, rebuilt_tube = _build_calibration_artifact(ctx, specs, rebuilt_training)
    rebuilt_final = _build_holdout_result(ctx, specs, rebuilt_training, rebuilt_tube)
    summary_keys = (
        "route", "response_row_count", "point_pass_count", "containment_pass_count",
        "cap_pass_count", "joint_pass_count", "maximum_absolute_scaled_point_error",
        "maximum_absolute_error", "maximum_halfwidth", "passed",
    )
    report = {
        "schema_version": 1, "stage": STAGE,
        "phase": "independent_server_side_raw_recomputation",
        "raw_count": len(list(ctx.paths.raw.glob("*.json.gz"))),
        "training_artifact_exact": _digest(saved_training) == _digest(rebuilt_training),
        "calibrated_tube_exact": _digest(saved_tube) == _digest(rebuilt_tube),
        "final_summary_exact": all(final[key] == rebuilt_final[key] for key in summary_keys),
        "runtime_or_environment_error_count": 0,
        "raw_or_restart_error_count": 0,
        "statistics_or_reporting_error_count": 0,
        "passed": bool(
            _digest(saved_training) == _digest(rebuilt_training)
            and _digest(saved_tube) == _digest(rebuilt_tube)
            and all(final[key] == rebuilt_final[key] for key in summary_keys)
        ),
    }
    return report


def run_finalize(ctx: Context) -> dict[str, Any]:
    state = _require_phase(ctx, "holdout_probe_complete")
    training_path = ctx.paths.model / "training_pooled_observer.json"
    tube_path = ctx.paths.model / "calibrated_response_tube.json"
    if (
        _sha256(training_path) != state["training_model_sha256"]
        or _sha256(tube_path) != state["calibrated_tube_sha256"]
        or not bool(state["heldout_outcomes_opened"])
    ):
        raise ValueError("T13S20 frozen model/tube or holdout ordering changed")
    final = _build_holdout_result(ctx, _all_specs(ctx), _read_json(training_path), _read_json(tube_path))
    final_path = ctx.paths.run_dir / "final_result.json"
    _write_json(final_path, final)
    independent = independent_postprocess(ctx, final)
    _write_json(ctx.paths.run_dir / "server_independent_postprocess.json", independent)
    final_pass = bool(final["passed"] and independent["passed"])
    _set_state(
        ctx, phase_status="campaign_complete", finished=True,
        primary_pass=final_pass, real_tsc_executed=True, new_raw_count=360,
        final_result_sha256=_sha256(final_path),
        independent_postprocess_sha256=_sha256(ctx.paths.run_dir / "server_independent_postprocess.json"),
        stop_reason="" if final_pass else "fresh_holdout_gate_failed",
        verdict={"route": final["route"], "passed": final_pass},
    )
    return {key: final[key] for key in (
        "stage", "phase", "route", "response_row_count", "point_pass_count",
        "containment_pass_count", "cap_pass_count", "joint_pass_count",
        "maximum_absolute_scaled_point_error", "maximum_halfwidth", "passed",
    )} | {"independent_postprocess_passed": independent["passed"]}


def _raw_inventory(ctx: Context) -> dict[str, Any]:
    rows = []
    digest = hashlib.sha256()
    for path in sorted(ctx.paths.raw.glob("*.json.gz")):
        sha = _sha256(path)
        size = path.stat().st_size
        row = f"{path.name}\0{size}\0{sha}\n".encode("utf-8")
        digest.update(row)
        rows.append({"path": path.name, "bytes": size, "sha256": sha})
    return {
        "count": len(rows), "total_bytes": sum(row["bytes"] for row in rows),
        "digest": digest.hexdigest(), "files": rows,
    }


def run_postprocess(ctx: Context) -> dict[str, Any]:
    state = _read_json(ctx.paths.state)
    if not state.get("finished") or state.get("phase_status") != "campaign_complete":
        raise ValueError("T13S20 postprocess requires a completed campaign")
    final = _read_json(ctx.paths.run_dir / "final_result.json")
    independent = independent_postprocess(ctx, final)
    inventory = _raw_inventory(ctx)
    report = {
        "schema_version": 1, "stage": STAGE, "phase": "final_server_raw_inventory_audit",
        "raw_inventory": inventory,
        "expected_raw_count": 360, "actual_raw_count": inventory["count"],
        "independent_recomputation": independent,
        "passed": bool(inventory["count"] == 360 and independent["passed"]),
    }
    _write_json(ctx.paths.run_dir / "server_final_audit.json", report)
    return report


def execute(ctx: Context, *, command: str, backend: str, resume: bool) -> dict[str, Any]:
    if command == "offline":
        return prepare_offline(ctx)
    if command == "postprocess":
        return run_postprocess(ctx)
    if not ctx.paths.state.is_file():
        raise ValueError("T13S20 command requires frozen offline state")
    if command.endswith("-baseline"):
        return run_baseline(ctx, command.split("-", 1)[0], backend=backend, resume=resume)
    if command.endswith("-probe"):
        return run_probe(ctx, command.split("-", 1)[0], backend=backend, resume=resume)
    if command == "fit-training":
        return run_fit_training(ctx)
    if command == "calibrate":
        return run_calibrate(ctx)
    if command == "finalize":
        return run_finalize(ctx)
    raise ValueError(f"unsupported T13S20 command: {command}")


def self_test(config_path: Path) -> dict[str, Any]:
    cfg = _read_json(config_path)
    _validate_config(cfg)
    nominal_inputs = (
        [[1.0, 0.0, 0.0, 0.0], [-1.0, 0.0, 0.0, 0.0],
         [0.0, 1.0, 0.0, 0.0], [0.0, -1.0, 0.0, 0.0],
         [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, -1.0, 0.0],
         [0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 0.0, -1.0]]
    )
    synthetic_trace = [
        {"r3c3t13s20_dynamic_input_coordinate": row}
        for row in nominal_inputs
    ] + [{}, {}]
    design, design_audit = _dynamic_design(synthetic_trace, cfg)
    rng = np.random.default_rng(20260803)
    x = rng.normal(size=(96, 9))
    scales = np.asarray(cfg["causal_model"]["response_scales"], dtype=float)
    y = rng.normal(size=(96, 5)) * scales * 1e-3
    groups = np.asarray([f"pair-{index:02d}" for index in range(12) for _ in range(8)])
    oof = s18._oof(x, y, groups, 1e-4, scales, 1e-12)
    passed = bool(
        design.shape == (10, 8) and np.linalg.matrix_rank(design) == 8
        and design_audit["dynamic_design_condition"] <= 4.0
        and oof.shape == y.shape and np.all(np.isfinite(oof))
        and len(_pair_partition_map(cfg)) == 20
    )
    return {
        "schema_version": 1, "stage": STAGE, "phase": "self_test",
        "context_pairs": 20, "expected_real_rollouts": 360,
        "new_tsc_or_plant_step_count": 0, "real_tsc_executed": False,
        "passed": passed,
    }


def _cli_source_kwargs(args: argparse.Namespace) -> dict[str, Path | None]:
    """Translate argparse destinations to the frozen internal source names."""
    return {
        "source_stage42r3b_run": args.source_stage4_2r3b_run,
        "source_stage42r3c3_run": args.source_stage4_2r3c3_run,
        "source_stage42r3c3_bank_dir": args.source_stage4_2r3c3_bank_dir,
        "source_stage42r3c3t1_run": args.source_stage4_2r3c3t1_run,
        "source_stage42r3c3t1_audit_dir": args.source_stage4_2r3c3t1_audit_dir,
        "source_stage42r3c3t3_controller_bank": args.source_stage4_2r3c3t3_controller_bank,
        "q1_run": args.q1_run,
        "q2_run": args.q2_run,
        "q1_audit": args.q1_audit,
        "q2_audit": args.q2_audit,
        "r3b_server_audit": args.r3b_server_audit,
        "r3b_snapshot_checks": args.r3b_snapshot_checks,
        "run_dir": args.run_dir,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path,
        default=_project_root() / "configs" / "stage4_2r3c3t13s20_dynamic_exact_card15_pooled_observer_campaign_370ms.json",
    )
    for name in (
        "source-stage4-2r3b-run", "source-stage4-2r3c3-run",
        "source-stage4-2r3c3-bank-dir", "source-stage4-2r3c3t1-run",
        "source-stage4-2r3c3t1-audit-dir", "source-stage4-2r3c3t3-controller-bank",
        "q1-run", "q2-run", "q1-audit", "q2-audit", "r3b-server-audit",
        "r3b-snapshot-checks", "run-dir",
    ):
        parser.add_argument(f"--{name}", type=Path)
    parser.add_argument(
        "--command", choices=(
            "offline", "training-baseline", "training-probe", "fit-training",
            "calibration-baseline", "calibration-probe", "calibrate",
            "holdout-baseline", "holdout-probe", "finalize", "postprocess",
        ), default="offline",
    )
    parser.add_argument("--backend", choices=("serial", "ray"), default="ray")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        result = self_test(args.config)
    else:
        required = _cli_source_kwargs(args)
        if any(value is None for value in required.values()) or len(required) != 13:
            parser.error("all source paths and --run-dir are required")
        ctx = load_config(args.config, **required)
        result = execute(ctx, command=args.command, backend=args.backend, resume=args.resume)
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
