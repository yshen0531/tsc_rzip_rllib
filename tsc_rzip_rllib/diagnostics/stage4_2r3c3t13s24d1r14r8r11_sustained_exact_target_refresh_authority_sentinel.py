#!/usr/bin/env python3
"""Execute the frozen R8R11 sustained exact-target-refresh authority sentinel."""

from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import time
import traceback
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.control.quantized_actuator import QuantizedActuatorModel
from tsc_rzip_rllib.core.coil_order import display_to_tsc
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r6_direction0_replacement_sentinel as r6,
    stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_campaign as r8r7,
    stage4_2r3c3t13s24d1r14r8r9_measured_multipulse_authority_audit as r8r9,
)


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S24D1R14R8R11"
IDENTITY = "sustained_exact_target_refresh_authority_sentinel_v1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r11_sustained_exact_target_refresh_authority_sentinel"
CONTROLLER_REVISION = "sustained_exact_target_refresh_v42r3c3t13s24d1r14r8r11_v1"
N_COILS = 14
PREFIX_END = 10
PHASES = ("safety", "qualification")


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _matrix_digest(value: Sequence[Sequence[float]]) -> str:
    return hashlib.sha256(
        np.ascontiguousarray(np.asarray(value, dtype="<f8")).tobytes(order="C")
    ).hexdigest()


@dataclass(frozen=True)
class Paths:
    run_dir: Path
    stage: Path
    variants: Path
    specs: Path
    source_reference: Path
    raw: Path
    analysis: Path
    state: Path
    manifest: Path

    def phase_raw(self, phase: str) -> Path:
        if phase not in PHASES:
            raise ValueError(f"invalid R8R11 phase: {phase}")
        return self.raw / phase


def _paths(run_dir: Path) -> Paths:
    root = run_dir.expanduser().resolve()
    stage = root / RUN_NAME
    return Paths(
        run_dir=root,
        stage=stage,
        variants=stage / "variants",
        specs=stage / "specs",
        source_reference=stage / "source_reference",
        raw=stage / "raw",
        analysis=stage / "analysis",
        state=stage / "stage_state.json",
        manifest=stage / "stage_manifest.json",
    )


@dataclass(frozen=True)
class Context:
    cfg: dict[str, Any]
    config_path: Path
    paths: Paths
    r8r7_run: Path
    source_ctx: r8r7.Context


def validate_config(cfg: Mapping[str, Any], *, project_root: Path) -> None:
    design = project_root / str(cfg["design_document"])
    contexts = cfg["context_contract"]
    schedule = cfg["schedule_contract"]
    controller = cfg["controller_contract"]
    formal = cfg["formal_contract"]
    gate = cfg["scientific_gate"]
    scope = cfg["scientific_scope"]
    matrix = schedule["replacement_matrix_columns"]
    if (
        int(cfg.get("schema_version", -1)) != SCHEMA_VERSION
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("run_name") != RUN_NAME
        or cfg.get("controller_revision") != CONTROLLER_REVISION
        or not design.is_file()
        or _sha(design) != str(cfg["design_document_sha256"])
        or tuple(contexts["histories"]) != ("minus_first", "plus_first")
        or len(contexts["ordered_pairs"]) != 8
        or tuple(contexts["safety_pairs"]) != tuple(contexts["ordered_pairs"][:2])
        or (int(contexts["context_count"]), int(contexts["safety_context_count"]), int(contexts["qualification_context_count"]))
        != (16, 4, 12)
        or tuple(map(int, schedule["issue_task_steps"])) != (14, 18, 22)
        or tuple(map(int, schedule["signs"])) != (-1, 1)
        or int(schedule["direction_index"]) != 0
        or (int(schedule["refresh_step_offset"]), int(schedule["cancel_step_offset"]), int(schedule["zero_after_step_offset"]))
        != (1, 2, 3)
        or np.asarray(matrix, dtype=float).shape != (4, 4)
        or _matrix_digest(matrix) != str(schedule["replacement_matrix_float64_le_c_sha256"])
        or (int(schedule["safety_spec_count"]), int(schedule["qualification_spec_count"]), int(schedule["total_spec_count"]))
        != (24, 72, 96)
        or float(controller["maximum_incremental_normalized_action_linf"]) != 0.25
        or float(controller["maximum_online_cancel_incremental_linf"]) != 0.24
        or float(controller["maximum_total_normalized_action_abs"]) != 1.0
        or float(controller["maximum_current_utilization"]) != 0.55
        or float(controller["minimum_desired_applied_current_cosine"]) != 0.98
        or float(controller["maximum_relative_off_basis_residual"]) != 0.10
        or not all(bool(controller[key]) for key in (
            "require_exact_card15_issue", "require_exact_card15_refresh",
            "require_exact_stored_center_cancellation", "require_exact_zero_target_jump_net",
            "require_exact_source_prefix", "forbid_future_r17_controller_execution",
        ))
        or (int(formal["normal_arrival_deadline_step"]), int(formal["normal_hold_through_step"]), int(formal["weak_arrival_deadline_step"]), int(formal["weak_hold_through_step"]))
        != (25, 35, 27, 37)
        or (float(formal["position_tolerance_m"]), float(formal["speed_tolerance_m_per_s"]), float(formal["ip_tolerance_A"]), int(formal["arrival_streak_steps"]))
        != (0.03, 0.1, 10000.0, 3)
        or float(formal["metric_equivalence_absolute_tolerance"]) != 1e-12
        or bool(formal["arrival_deadline_expansion_allowed"])
        or (int(gate["required_baseline_formal_pass_count"]), int(gate["required_failed_baseline_count"]), int(gate["minimum_repaired_failed_baseline_count"]), int(gate["minimum_held_oracle_formal_pass_count"]))
        != (6, 10, 1, 7)
        or not bool(gate["require_held_oracle_strictly_improves_baseline"])
        or bool(scope["measured_oracle_is_causal_selector"])
        or bool(scope["real_mpc_executed"])
        or bool(scope["gate_a_qualified"])
        or bool(scope["all_stage_trajectories_allowed_in_expert_dataset"])
        or bool(scope["expert_data_allowed"])
        or bool(scope["bc_dagger_or_rl_allowed"])
        or bool(scope["global_plant_reachability_claimed"])
    ):
        raise ValueError("R8R11 frozen design changed")


def load_context(args: argparse.Namespace) -> Context:
    config_path = args.config.expanduser().resolve()
    cfg = _read(config_path)
    validate_config(cfg, project_root=_root())
    source_args = argparse.Namespace(**vars(args))
    source_args.config = (_root() / str(cfg["source_r8r7_config"])).resolve()
    source_args.run_dir = args.r8r7_run.expanduser().resolve()
    source_ctx = r8r7.load_context(source_args)
    return Context(
        cfg=cfg,
        config_path=config_path,
        paths=_paths(args.run_dir),
        r8r7_run=args.r8r7_run.expanduser().resolve(),
        source_ctx=source_ctx,
    )


def _execution_context(ctx: Context) -> Any:
    return r8r7.r8.Context(
        cfg=ctx.source_ctx.r8_cfg,
        config_path=ctx.source_ctx.r8_config_path,
        d1r11_ctx=ctx.source_ctx.r8_ctx.d1r11_ctx,
        source_d1r11_run=ctx.source_ctx.r8_ctx.source_d1r11_run,
        source_response_runs=ctx.source_ctx.r8_ctx.source_response_runs,
        paths=ctx.paths,  # compatible variants path; source evidence remains read-only
    )


def _source_stage(ctx: Context) -> Path:
    return ctx.r8r7_run / str(ctx.cfg["source_r8r7"]["stage_directory"])


def _source_baselines(ctx: Context) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    specs = [copy.deepcopy(row) for row in r8r7._phase_specs(ctx.source_ctx, "baseline")]
    ordered = list(map(str, ctx.cfg["context_contract"]["ordered_pairs"]))
    histories = list(map(str, ctx.cfg["context_contract"]["histories"]))
    order = {(pair, history): (pi, hi) for pi, pair in enumerate(ordered) for hi, history in enumerate(histories)}
    specs.sort(key=lambda row: order[(str(row["pair_id"]), str(row["history_member"]))])
    if len(specs) != 16 or {(str(row["pair_id"]), str(row["history_member"])) for row in specs} != set(order):
        raise ValueError("R8R11 source baseline context coverage changed")
    results = {
        str(row["experiment_id"]): r8r7.r8._read_gz(
            _source_stage(ctx) / "raw" / "baseline" / f"{row['experiment_id']}.json.gz"
        )
        for row in specs
    }
    return specs, results


def build_specs(ctx: Context) -> list[dict[str, Any]]:
    baselines, _ = _source_baselines(ctx)
    safety_pairs = set(map(str, ctx.cfg["context_contract"]["safety_pairs"]))
    schedule = ctx.cfg["schedule_contract"]
    matrix = np.asarray(schedule["replacement_matrix_columns"], dtype=float)
    output: list[dict[str, Any]] = []
    for context_index, source in enumerate(baselines):
        pair = str(source["pair_id"])
        phase = "safety" if pair in safety_pairs else "qualification"
        for issue in map(int, schedule["issue_task_steps"]):
            for sign in map(int, schedule["signs"]):
                spec = copy.deepcopy(source)
                experiment_id = f"r8r11_{phase}_{context_index:02d}_s{issue}_{'p' if sign > 0 else 'm'}"
                requested = matrix[:, 0] * sign
                spec.update(
                    {
                        "kind": "stage4_2r3c3t13s24d1r14r8r11_sustained_exact_target_refresh",
                        "stage": STAGE,
                        "campaign_identity": IDENTITY,
                        "controller_revision": CONTROLLER_REVISION,
                        "partition": phase,
                        "experiment_id": experiment_id,
                        "source_r8r7_baseline_experiment_id": str(source["experiment_id"]),
                        "r8r11_role": "sustained_exact_target_refresh",
                        "r8r11_direction_index": 0,
                        "r8r11_sign": sign,
                        "r8r11_requested_coordinate": requested.tolist(),
                        "r8r11_matrix_digest": str(schedule["replacement_matrix_float64_le_c_sha256"]),
                        "r8r11_issue_task_step": issue,
                        "r8r11_refresh_task_step": issue + int(schedule["refresh_step_offset"]),
                        "r8r11_cancel_task_step": issue + int(schedule["cancel_step_offset"]),
                        "r8r11_zero_after_task_step": issue + int(schedule["zero_after_step_offset"]),
                        "r8r11_allowed_in_expert_dataset": False,
                        "pair_or_history_label_available_to_controller": False,
                        "source_result_available_to_controller": False,
                        "future_measurement_count": 0,
                        "future_action_count": 0,
                        "formal_timing_unchanged": True,
                    }
                )
                output.append(spec)
    counts = {phase: sum(str(row["partition"]) == phase for row in output) for phase in PHASES}
    if counts != {"safety": 24, "qualification": 72} or len(output) != 96 or len({row["experiment_id"] for row in output}) != 96:
        raise ValueError("R8R11 frozen specification matrix changed")
    return output


def _payload(ctx: Context, spec: Mapping[str, Any]) -> dict[str, Any]:
    payload = r8r7.r8._payload(_execution_context(ctx), spec)
    experiment_id = str(spec["experiment_id"])
    payload.update(
        {
            "variant_id": f"stage4_2r3c3t13s24d1r14r8r11_{experiment_id}",
            "stage4_2r3c3t13s24d1r14r8r11_issue_task_step": int(spec["r8r11_issue_task_step"]),
            "stage4_2r3c3t13s24d1r14r8r11_refresh_task_step": int(spec["r8r11_refresh_task_step"]),
            "stage4_2r3c3t13s24d1r14r8r11_cancel_task_step": int(spec["r8r11_cancel_task_step"]),
            "stage4_2r3c3t13s24d1r14r8r11_pair_history_label_available_to_controller": False,
        }
    )
    _write(ctx.paths.variants / f"payload_{experiment_id}.json", payload)
    return payload


def _fixed_basis(result: Mapping[str, Any]) -> np.ndarray:
    values = [
        row.get("r3c3t13s16_fixed_basis_delta_field_kAt_tsc")
        for row in result["controller_trace"][:11]
        if row.get("r3c3t13s16_fixed_basis_delta_field_kAt_tsc")
    ]
    if not values or any(value != values[0] for value in values[1:]):
        raise ValueError("R8R11 source fixed field basis is not unique")
    matrix = np.asarray(values[0], dtype=float).T
    if matrix.shape != (N_COILS, 4) or not np.all(np.isfinite(matrix)):
        raise ValueError("R8R11 source fixed field basis is invalid")
    return matrix


def _offline_issue_preflight(ctx: Context, specs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    _, source_results = _source_baselines(ctx)
    execution = _execution_context(ctx)
    lattice = execution.d1r11_ctx.base_ctx.base_ctx.cfg["lattice_probe"]
    schedule_cfg = execution.d1r11_ctx.cfg["schedule_contract"]
    rows = []
    for spec in specs:
        source = source_results[str(spec["source_r8r7_baseline_experiment_id"])]
        issue = int(spec["r8r11_issue_task_step"])
        currents = np.asarray(source["trajectory"][issue]["currents_a_tsc"], dtype=float)
        payload = _read(ctx.paths.variants / f"payload_{spec['experiment_id']}.json")
        turns = np.asarray(display_to_tsc(payload["env_cfg"]["turns_display_order"]), dtype=float)
        minimum = np.asarray(payload["min_current_tsc"], dtype=float)
        maximum = np.asarray(payload["max_current_tsc"], dtype=float)
        actuator = QuantizedActuatorModel(
            minimum_current_a_tsc=tuple(minimum), maximum_current_a_tsc=tuple(maximum),
            max_slew_step_a=float(payload["max_delta_a"]), turns_tsc=tuple(turns),
        )
        field_basis = _fixed_basis(source)
        current_basis = field_basis * 1000.0 / turns[:, None]
        requested = np.asarray(spec["r8r11_requested_coordinate"], dtype=float)
        center = actuator.apply(currents, np.zeros(N_COILS, dtype=float))
        target_fields, actual_decimal, _ = r8r7.r8.d1r11.s21._dynamic_exact_target(
            center.card15_fields,
            tuple(Decimal(str(value)) for value in field_basis @ requested),
            search_radius=int(schedule_cfg["dynamic_exact_search_radius"]),
        )
        chosen = r8r7.r8.d1r11.s21.s16.s9.exact_stored_center_action(
            stored_fields=target_fields, measured_current_a_tsc=currents,
            baseline_action_norm_tsc=np.zeros(N_COILS), turns_tsc=turns,
            max_slew_step_a=float(payload["max_delta_a"]), minimum_current_a_tsc=minimum,
            maximum_current_a_tsc=maximum, cfg=lattice,
        )
        issued = actuator.apply(currents, chosen["action_norm_tsc"])
        actual_current = np.asarray([float(value) for value in actual_decimal]) * 1000.0 / turns
        desired_current = current_basis @ requested
        coordinate = np.linalg.lstsq(current_basis, actual_current, rcond=None)[0]
        reconstructed = current_basis @ coordinate
        cosine = float(np.dot(desired_current, actual_current) / max(np.linalg.norm(desired_current) * np.linalg.norm(actual_current), 1e-300))
        residual = float(np.linalg.norm(actual_current - reconstructed) / max(np.linalg.norm(actual_current), 1e-300))
        contract = ctx.cfg["controller_contract"]
        criteria = {
            "finite": bool(np.all(np.isfinite(coordinate)) and math.isfinite(cosine) and math.isfinite(residual)),
            "requested_exact": bool(np.array_equal(requested, np.asarray(ctx.cfg["schedule_contract"]["replacement_matrix_columns"], dtype=float)[:, 0] * int(spec["r8r11_sign"]))),
            "target_reproduction": list(issued.card15_fields) == list(target_fields),
            "no_saturation": not any(issued.action_saturated),
            "no_current_clip": not any(issued.current_limit_clipped),
            "incremental_action": float(chosen["incremental_normalized_action_linf"]) <= float(contract["maximum_incremental_normalized_action_linf"]) + 1e-12,
            "total_action": float(chosen["total_normalized_action_abs"]) <= float(contract["maximum_total_normalized_action_abs"]) + 1e-12,
            "current_utilization": float(chosen["predicted_maximum_current_utilization"]) <= float(contract["maximum_current_utilization"]) + 1e-12,
            "cosine": cosine >= float(contract["minimum_desired_applied_current_cosine"]) - 1e-12,
            "off_basis": residual <= float(contract["maximum_relative_off_basis_residual"]) + 1e-12,
            "actuator_gate": bool(chosen["passed"]),
        }
        rows.append(
            {
                "experiment_id": spec["experiment_id"], "pair_id": spec["pair_id"],
                "history_member": spec["history_member"], "issue_task_step": issue,
                "sign": int(spec["r8r11_sign"]),
                "incremental_normalized_action_linf": float(chosen["incremental_normalized_action_linf"]),
                "predicted_current_utilization": float(chosen["predicted_maximum_current_utilization"]),
                "desired_applied_current_cosine": cosine,
                "relative_off_basis_residual": residual,
                "criteria": criteria, "passed": bool(all(criteria.values())),
            }
        )
    return {
        "construction_count": len(rows),
        "construction_pass_count": sum(bool(row["passed"]) for row in rows),
        "maximum_incremental_normalized_action_linf": max(float(row["incremental_normalized_action_linf"]) for row in rows),
        "maximum_predicted_current_utilization": max(float(row["predicted_current_utilization"]) for row in rows),
        "rows": rows,
        "passed": len(rows) == 96 and all(bool(row["passed"]) for row in rows),
    }


def prepare_offline(ctx: Context) -> dict[str, Any]:
    if ctx.paths.stage.exists():
        raise ValueError("R8R11 offline requires a fresh run identity")
    source = r8r9._authenticate_r8r7(_source_stage(ctx), ctx.cfg)
    lineage = {
        "r8": r8r7._authenticate_r8(ctx.source_ctx),
        "r8r1": r8r7._authenticate_r8r1(ctx.source_ctx),
        "r8r6": r8r7._authenticate_r8r6(ctx.source_ctx),
    }
    specs = build_specs(ctx)
    for path in (ctx.paths.stage, ctx.paths.variants, ctx.paths.specs, ctx.paths.source_reference, ctx.paths.analysis):
        path.mkdir(parents=True, exist_ok=True)
    for phase in PHASES:
        ctx.paths.phase_raw(phase).mkdir(parents=True, exist_ok=True)
    for spec in specs:
        _payload(ctx, spec)
    preflight = _offline_issue_preflight(ctx, specs)
    if not preflight["passed"]:
        raise ValueError("R8R11 frozen offline issue preflight failed")
    _write(ctx.paths.specs / "all_specs.json", specs)
    for phase in PHASES:
        _write(ctx.paths.specs / f"{phase}_specs.json", [row for row in specs if row["partition"] == phase])
    _write(ctx.paths.source_reference / "r8r7_authentication.json", source)
    _write(ctx.paths.source_reference / "lineage_authentication.json", lineage)
    _write(ctx.paths.analysis / "offline_issue_preflight.json", preflight)
    package = r8r7._package_fingerprint()
    manifest = {
        "schema_version": 1, "stage": STAGE, "identity": IDENTITY,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": ctx.cfg["package_revision"],
        "config_path": str(ctx.config_path), "config_sha256": _sha(ctx.config_path),
        "design_document_sha256": ctx.cfg["design_document_sha256"],
        "source_r8r7_run": str(ctx.r8r7_run),
        "source_authentication": source, "lineage_authenticated": True,
        "spec_count": len(specs), "spec_digest": _digest(specs),
        "offline_preflight_digest": _digest(preflight), "package_fingerprint": package,
        "formal_timing_unchanged": True,
        "all_stage_trajectories_allowed_in_expert_dataset": False,
    }
    _write(ctx.paths.manifest, manifest)
    state = {
        "schema_version": 1, "stage": STAGE, "phase_status": "offline_primary_ready",
        "finished": False, "real_tsc_executed": False, "new_raw_count": 0,
        "qualification_outcomes_opened": False, "formal_outcomes_opened": False,
        "spec_digest": manifest["spec_digest"], "package_digest": package["digest"],
        "verdict": {}, "stop_reason": "",
    }
    _write(ctx.paths.state, state)
    report = {
        "schema_version": 1, "stage": STAGE, "phase": "offline_primary",
        "source_authenticated": True, "lineage_authenticated": True,
        "spec_count": 96, "safety_spec_count": 24, "qualification_spec_count": 72,
        "offline_issue_construction_count": preflight["construction_count"],
        "offline_issue_construction_pass_count": preflight["construction_pass_count"],
        "new_raw_count": 0, "real_tsc_executed": False, "passed": True,
    }
    _write(ctx.paths.analysis / "offline_primary.json", report)
    return report


def _saved_specs(ctx: Context) -> list[dict[str, Any]]:
    specs = _read(ctx.paths.specs / "all_specs.json")
    manifest = _read(ctx.paths.manifest)
    if len(specs) != 96 or _digest(specs) != manifest.get("spec_digest") or _sha(ctx.config_path) != manifest.get("config_sha256"):
        raise ValueError("R8R11 saved specifications changed")
    return specs


def _phase_specs(ctx: Context, phase: str) -> list[dict[str, Any]]:
    rows = [row for row in _saved_specs(ctx) if row["partition"] == phase]
    if len(rows) != {"safety": 24, "qualification": 72}[phase]:
        raise ValueError("R8R11 saved phase coverage changed")
    return rows


def _set_state(ctx: Context, **updates: Any) -> dict[str, Any]:
    state = _read(ctx.paths.state)
    state.update(updates)
    _write(ctx.paths.state, state)
    return state


class SustainedRefreshController(r6.MixedBasisSignedExcitationController):
    """One exact issue, one causal target refresh, then exact center return."""

    def __init__(
        self,
        base: Any,
        bundle: Mapping[str, Any],
        source_spec: Mapping[str, Any],
        initial_state: Mapping[str, Any],
        lattice_cfg: Mapping[str, Any],
        calibration_cfg: Mapping[str, Any],
        dynamic_cfg: Mapping[str, Any],
        schedule_cfg: Mapping[str, Any],
        controller_contract: Mapping[str, Any],
        *,
        spec: Mapping[str, Any],
    ):
        issue = int(spec["r8r11_issue_task_step"])
        super().__init__(
            base,
            bundle,
            source_spec,
            initial_state,
            lattice_cfg,
            calibration_cfg,
            dynamic_cfg,
            schedule_cfg,
            controller_contract,
            role="signed_probe", direction_index=0, sign=int(spec["r8r11_sign"]),
            requested_coordinate=spec["r8r11_requested_coordinate"], issue_step=issue,
            cancel_step=issue + 1, zero_after_step=issue + 2,
        )
        self.r8r11_issue_step = issue
        self.r8r11_refresh_step = int(spec["r8r11_refresh_task_step"])
        self.r8r11_cancel_step = int(spec["r8r11_cancel_task_step"])
        self.r8r11_contract = copy.deepcopy(dict(controller_contract))

    def _refresh(self, currents: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
        if self._active_issue is None:
            raise ValueError("R8R11 refresh has no matching causal issue")
        target_fields = tuple(map(str, self._active_issue["target_card15_fields"]))
        chosen = r8r7.r8.d1r11.s21.s16.s9.exact_stored_center_action(
            stored_fields=target_fields, measured_current_a_tsc=currents,
            baseline_action_norm_tsc=np.zeros(N_COILS), turns_tsc=self.turns_tsc,
            max_slew_step_a=float(self.base.max_delta_a), minimum_current_a_tsc=self.base.min_current,
            maximum_current_a_tsc=self.base.max_current, cfg=self.lattice_cfg,
        )
        refreshed = self.actuator.apply(currents, chosen["action_norm_tsc"])
        contract = self.r8r11_contract
        criteria = {
            "target_exact": list(refreshed.card15_fields) == list(target_fields),
            "exact_fields": all(len(field) == 10 for field in target_fields),
            "no_saturation": not any(refreshed.action_saturated),
            "no_current_clip": not any(refreshed.current_limit_clipped),
            "incremental_action": float(chosen["incremental_normalized_action_linf"]) <= float(contract["maximum_incremental_normalized_action_linf"]) + 1e-12,
            "total_action": float(chosen["total_normalized_action_abs"]) <= float(contract["maximum_total_normalized_action_abs"]) + 1e-12,
            "current_utilization": float(chosen["predicted_maximum_current_utilization"]) <= float(contract["maximum_current_utilization"]) + 1e-12,
            "actuator_gate": bool(chosen["passed"]),
        }
        event = {
            "event": "exact_target_refresh", "task_step": self.step, "slot": 0,
            "stored_target_card15_fields": list(target_fields),
            "incremental_normalized_action_linf": float(chosen["incremental_normalized_action_linf"]),
            "total_normalized_action_abs": float(chosen["total_normalized_action_abs"]),
            "predicted_current_utilization": float(chosen["predicted_maximum_current_utilization"]),
            "criteria": criteria, "passed": bool(all(criteria.values())),
            "actuator_prediction": copy.deepcopy(chosen),
        }
        if not event["passed"]:
            raise ValueError("R8R11 exact target refresh action failed: " + json.dumps(event, sort_keys=True))
        return np.asarray(chosen["action_norm_tsc"], dtype=float), event

    def action(self, current_state: Mapping[str, Any]) -> tuple[np.ndarray, dict[str, Any]]:
        if int(current_state["step_index"]) != self.step:
            raise ValueError("R8R11 controller/current state index mismatch")
        if self.step < PREFIX_END:
            action, trace = super().action(current_state)
            trace.update(
                {
                    "r3c3t13s24d1r14r8r11_controller_revision": CONTROLLER_REVISION,
                    "r3c3t13s24d1r14r8r11_delegated_prefix": True,
                    "r3c3t13s24d1r14r8r11_event": "none",
                    "r3c3t13s24d1r14r8r11_event_detail": {},
                    "r3c3t13s24d1r14r8r11_forbidden_input_used": False,
                }
            )
            return np.asarray(action, dtype=float), trace
        action = r6.zero_action(self.step)
        trace = r6._trace_template(self.step, action)
        currents = np.asarray(current_state["currents_a_tsc"], dtype=float)
        event_name = "none"
        event: dict[str, Any] = {}
        if self.step == self.r8r11_issue_step:
            action, event = self._issue(0, currents, np.zeros(N_COILS))
            event_name = "sustained_issue"
        elif self.step == self.r8r11_refresh_step:
            action, event = self._refresh(currents)
            event_name = "sustained_refresh"
        elif self.step == self.r8r11_cancel_step:
            action, event = self._cancel(0, currents, np.zeros(N_COILS))
            event_name = "stored_center_cancel"
        trace.update(
            {
                "action_norm_tsc": np.asarray(action, dtype=float).tolist(),
                "r3c3t13s24d1r14r8r11_controller_revision": CONTROLLER_REVISION,
                "r3c3t13s24d1r14r8r11_delegated_prefix": False,
                "r3c3t13s24d1r14r8r11_event": event_name,
                "r3c3t13s24d1r14r8r11_event_detail": event,
                "r3c3t13s24d1r14r8r11_forbidden_input_used": False,
                "r3c3t13s24d1r14r8r11_pair_or_history_label_used": False,
                "r3c3t13s24d1r14r8r11_future_measurement_used": False,
                "r3c3t13s24d1r14r8r11_future_action_used": False,
                "r3c3t13s24d1r14r8r11_source_result_used": False,
                "r3c3t13s24d1r14r8r11_hidden_wire_used": False,
            }
        )
        return np.asarray(action, dtype=float), trace


class LocalWorker:
    def __init__(self, payload: dict[str, Any], library: dict[str, Any], bundle: dict[str, Any], worker_id: str, selector: dict[str, Any], lattice_cfg: dict[str, Any], calibration_cfg: dict[str, Any], dynamic_cfg: dict[str, Any], schedule_cfg: dict[str, Any], controller_cfg: dict[str, Any]):
        self.plant = r8r7.r8.d1r11.s21.s16.s9.t11.t1.r1.LocalPlantReplayWorker(payload, library, bundle, worker_id, selector)
        self.base = self.plant.base_worker
        self.bundle = bundle
        self.lattice_cfg = lattice_cfg
        self.calibration_cfg = calibration_cfg
        self.dynamic_cfg = dynamic_cfg
        self.schedule_cfg = schedule_cfg
        self.controller_cfg = controller_cfg

    def close(self) -> None:
        self.plant.close()

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        failed = True
        trajectory: list[dict[str, Any]] = []
        trace: list[dict[str, Any]] = []
        result: dict[str, Any] = {
            "schema_version": 1, "stage": STAGE, "campaign_identity": IDENTITY,
            "controller_revision": CONTROLLER_REVISION, "experiment_id": spec["experiment_id"],
            "spec": copy.deepcopy(spec), "success": False, "completed": False,
            "failure_reason": "", "execution_failure_class": "",
            "trajectory": trajectory, "controller_trace": trace,
        }
        try:
            horizon = int(spec["horizon_steps"])
            if horizon != int(spec["formal_horizon_steps"]) or horizon != int(self.base.env.max_episode_steps):
                raise ValueError("R8R11 formal horizon changed")
            self.base.env.reset()
            zero = np.zeros(N_COILS, dtype=np.float32)
            trajectory.append(r8r7.r8.d1r11.s21.s16.s9.t11.t1.r1._state_record_full(self.base.env, 0, zero))
            controller = SustainedRefreshController(
                self.base, self.bundle, spec, trajectory[0], self.lattice_cfg,
                self.calibration_cfg, self.dynamic_cfg, self.schedule_cfg,
                self.controller_cfg, spec=spec,
            )
            for step in range(horizon):
                current = trajectory[-1]
                finite = all(math.isfinite(float(current[key])) for key in ("R", "Z", "Ip")) and np.all(np.isfinite(np.asarray(current["currents_a_tsc"], dtype=float)))
                if not finite or bool(current.get("abnormal")):
                    result["execution_failure_class"] = "pre_action_visible_state_safety_failure"
                    raise ValueError("R8R11 pre-action visible state safety gate failed")
                try:
                    action, row = controller.action(current)
                except ValueError as exc:
                    if "action failed" in str(exc):
                        result["execution_failure_class"] = "controller_action_safety_gate_failure"
                    raise
                _, _, terminated, truncated, info = self.base.env.step(action)
                next_state = r8r7.r8.d1r11.s21.s16.s9.t11.t1.r1._state_record_full(self.base.env, step + 1, action)
                trajectory.append(next_state)
                trace.append(row)
                controller.advance(next_state)
                if terminated:
                    result["execution_failure_class"] = "plant_abnormal_termination"
                    raise RuntimeError(str(info.get("failure_reason", "environment terminated")))
                if truncated and step + 1 < horizon:
                    result["execution_failure_class"] = "plant_early_truncation"
                    raise RuntimeError("environment truncated before R8R11 horizon")
            events = [row.get("r3c3t13s24d1r14r8r11_event") for row in trace if row.get("r3c3t13s24d1r14r8r11_event") != "none"]
            event_steps = {int(spec["r8r11_issue_task_step"]), int(spec["r8r11_refresh_task_step"]), int(spec["r8r11_cancel_task_step"])}
            actions = np.asarray([row["action_norm_tsc"] for row in trace], dtype=float)
            currents = np.asarray([row["currents_a_tsc"] for row in trajectory], dtype=float)
            zero_steps = [step for step in range(PREFIX_END, horizon) if step not in event_steps]
            zero_exact = bool(np.array_equal(actions[zero_steps], np.zeros((len(zero_steps), N_COILS))) and np.array_equal(currents[np.asarray(zero_steps) + 1] - currents[zero_steps], np.zeros((len(zero_steps), N_COILS))))
            calibration_events = [row.get("r3c3t13s16_lattice_event") for row in trace[:PREFIX_END] if row.get("r3c3t13s16_lattice_event") != "none"]
            success = bool(
                len(trajectory) == horizon + 1 and len(trace) == horizon
                and calibration_events == r8r7.r4.EXPECTED_CALIBRATION
                and bool(trace[7].get("r3c3t13s21_exact_calibration_net_zero"))
                and all(bool(row.get("r3c3t13s24d1r14r8r11_delegated_prefix")) for row in trace[:PREFIX_END])
                and events == ["sustained_issue", "sustained_refresh", "stored_center_cancel"]
                and all(bool((trace[step].get("r3c3t13s24d1r14r8r11_event_detail") or {}).get("passed")) for step in event_steps)
                and controller._active_issue is None and zero_exact
                and not any(bool(row.get("abnormal")) for row in trajectory)
                and np.all(np.isfinite(currents))
            )
            result.update(
                {
                    "success": success, "completed": True,
                    "failure_reason": "" if success else "incomplete or invalid R8R11 rollout",
                    "execution_failure_class": "" if success else "controller_or_action_semantics_error",
                    "hidden_history_control_summary": {
                        "fresh_controller_actor": True, "fresh_tsc_process": True,
                        "full_tsc_hidden_state_loaded_from_sprsina": True,
                        "future_r17_controller_executed": False,
                        "formal_tracking_diagnostic_only": False,
                        "stage_trajectory_allowed_in_expert_dataset": False,
                        "future_action_replay_used": False, "future_measurement_used": False,
                        "pair_or_history_label_used": False, "source_result_used": False,
                    },
                    "wall_time_s": time.time() - started,
                }
            )
            failed = not success
            return r8r7.r8.d1r11.s21.s16.s9.t11.t1._json_safe(result)
        except Exception as exc:
            result.update(
                {
                    "success": False, "completed": True, "failure_reason": repr(exc),
                    "execution_failure_class": str(result.get("execution_failure_class") or "runtime_or_controller_error"),
                    "trajectory": trajectory, "controller_trace": trace,
                    "traceback": traceback.format_exc(), "wall_time_s": time.time() - started,
                }
            )
            return r8r7.r8.d1r11.s21.s16.s9.t11.t1._json_safe(result)
        finally:
            runner = getattr(self.base.env, "runner", None)
            if runner is not None:
                runner.cleanup_episode_workspace(failed=failed, reason="stage4_2r3c3t13s24d1r14r8r11")


_RAY_ACTOR = None


def _ray_actor_class():
    global _RAY_ACTOR
    if _RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class R8R11Actor:
            def __init__(self, *args: Any):
                self.worker = LocalWorker(*args)
            def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
                return self.worker.evaluate(spec)
            def close(self) -> bool:
                self.worker.close()
                return True

        _RAY_ACTOR = R8R11Actor
    return _RAY_ACTOR


def _result_complete(path: Path, spec: Mapping[str, Any], *, require_success: bool = True) -> bool:
    if not path.is_file():
        return False
    try:
        result = r8r7.r8._read_gz(path)
        horizon = int(spec["horizon_steps"])
        return bool(
            result.get("completed") and (result.get("success") or not require_success)
            and result.get("stage") == STAGE and result.get("campaign_identity") == IDENTITY
            and result.get("controller_revision") == CONTROLLER_REVISION
            and result.get("experiment_id") == spec["experiment_id"] and result.get("spec") == dict(spec)
            and (not require_success or (len(result.get("trajectory") or []) == horizon + 1 and len(result.get("controller_trace") or []) == horizon))
        )
    except Exception:
        return False


def evaluate_specs(ctx: Context, specs: Sequence[dict[str, Any]], *, phase: str, backend: str, resume: bool) -> dict[str, Any]:
    raw_dir = ctx.paths.phase_raw(phase)
    pending = [spec for spec in specs if not (resume and _result_complete(raw_dir / f"{spec['experiment_id']}.json.gz", spec))]
    payloads = {str(spec["experiment_id"]): _payload(ctx, spec) for spec in specs}
    execution = _execution_context(ctx)
    library, bundle, selector = r8r7.r8.d1r11._library_bundle_selector(execution.d1r11_ctx)
    lattice = execution.d1r11_ctx.base_ctx.base_ctx.cfg["lattice_probe"]
    calibration = execution.d1r11_ctx.base_ctx.base_ctx.cfg["active_calibration"]
    dynamic = execution.d1r11_ctx.base_ctx.cfg["causal_model"]
    schedule_cfg = execution.d1r11_ctx.cfg["schedule_contract"]
    controller_cfg = copy.deepcopy(ctx.cfg["controller_contract"])
    controller_cfg.update(
        {
            "requested_coordinate_matrix_columns": copy.deepcopy(ctx.cfg["schedule_contract"]["replacement_matrix_columns"]),
            "requested_matrix_float64_le_c_sha256": str(ctx.cfg["schedule_contract"]["replacement_matrix_float64_le_c_sha256"]),
        }
    )
    def args_for(spec: Mapping[str, Any], index: int) -> tuple[Any, ...]:
        return (payloads[str(spec["experiment_id"])], library, bundle, f"stage42r8r11_{phase}_{index:03d}", selector, lattice, calibration, dynamic, schedule_cfg, controller_cfg)
    if backend == "serial":
        for index, spec in enumerate(pending):
            worker = LocalWorker(*args_for(spec, index))
            try:
                result = worker.evaluate(spec)
            finally:
                worker.close()
            r8r7.r8._write_gz(raw_dir / f"{spec['experiment_id']}.json.gz", result)
            print(f"[R8R11 {phase}] {index + 1}/{len(pending)}", flush=True)
    elif backend == "ray" and pending:
        import ray
        plan = r8r7.r8.d1r11.s21.s16.ensure_ray_worker_plan(
            ray, requested_workers=int(ctx.cfg["parallel"]["n_workers"]), pending_tasks=len(pending),
            ray_tmpdir=os.environ.get("RAY_TMPDIR") or ctx.cfg["storage"]["ray_tmpdir"], log_prefix=f"[R8R11 {phase}]",
        )
        Actor = _ray_actor_class()
        completed = 0
        for start in range(0, len(pending), plan.actor_count):
            batch = pending[start : start + plan.actor_count]
            actors, refs = [], {}
            for offset, spec in enumerate(batch):
                actor = Actor.remote(*args_for(spec, start + offset))
                actors.append(actor)
                refs[actor.evaluate.remote(spec)] = spec
            try:
                while refs:
                    ready, _ = ray.wait(list(refs), num_returns=1, timeout=30.0)
                    if not ready:
                        print(f"[R8R11 {phase}] waiting {completed}/{len(pending)}", flush=True)
                        continue
                    ref = ready[0]
                    spec = refs.pop(ref)
                    try:
                        result = ray.get(ref)
                    except Exception as exc:
                        result = {
                            "schema_version": 1, "stage": STAGE, "campaign_identity": IDENTITY,
                            "controller_revision": CONTROLLER_REVISION, "experiment_id": spec["experiment_id"],
                            "spec": copy.deepcopy(spec), "success": False, "completed": True,
                            "failure_reason": repr(exc), "execution_failure_class": "ray_actor_runtime_error",
                            "trajectory": [], "controller_trace": [], "traceback": traceback.format_exc(),
                        }
                    r8r7.r8._write_gz(raw_dir / f"{spec['experiment_id']}.json.gz", result)
                    completed += 1
                    print(f"[R8R11 {phase}] {completed}/{len(pending)}", flush=True)
            finally:
                close_refs = [actor.close.remote() for actor in actors]
                if close_refs:
                    ray.get(close_refs, timeout=float(ctx.cfg["storage"]["actor_close_timeout_s"]))
                for actor in actors:
                    ray.kill(actor, no_restart=True)
    elif backend not in {"serial", "ray"}:
        raise ValueError(f"unsupported R8R11 backend: {backend}")
    successful = sum(_result_complete(raw_dir / f"{spec['experiment_id']}.json.gz", spec) for spec in specs)
    return {"phase": phase, "expected": len(specs), "pending_at_start": len(pending), "successful": successful, "passed": successful == len(specs)}


def _source_baseline_maps(ctx: Context) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    specs, results = _source_baselines(ctx)
    return {str(row["experiment_id"]): row for row in specs}, results


def audit_raw_phase(ctx: Context, phase: str) -> dict[str, Any]:
    specs = _phase_specs(ctx, phase)
    _, source_results = _source_baseline_maps(ctx)
    rows = []
    contract = ctx.cfg["controller_contract"]
    for spec in specs:
        path = ctx.paths.phase_raw(phase) / f"{spec['experiment_id']}.json.gz"
        result = r8r7.r8._read_gz(path) if _result_complete(path, spec, require_success=False) else {}
        trajectory = result.get("trajectory") or []
        trace = result.get("controller_trace") or []
        horizon = int(spec["horizon_steps"])
        full = len(trajectory) == horizon + 1 and len(trace) == horizon
        source = source_results[str(spec["source_r8r7_baseline_experiment_id"])]
        prefix_state = bool(full and all(r8r7.r8.r4._semantic_state(current) == r8r7.r8.r4._semantic_state(reference) for current, reference in zip(trajectory[: PREFIX_END + 1], source["trajectory"][: PREFIX_END + 1])))
        prefix_trace = bool(full and all(r8r7.r8.r4._source_trace_projection(reference, current) for current, reference in zip(trace[:PREFIX_END], source["controller_trace"][:PREFIX_END])))
        calibration = bool(full and r8r7.r8.r4._calibration_exact(trace))
        actions = np.asarray([row.get("action_norm_tsc", []) for row in trace], dtype=float)
        currents = np.asarray([row.get("currents_a_tsc", []) for row in trajectory], dtype=float)
        event_steps = [int(spec[key]) for key in ("r8r11_issue_task_step", "r8r11_refresh_task_step", "r8r11_cancel_task_step")]
        event_names = ["sustained_issue", "sustained_refresh", "stored_center_cancel"]
        events = [(trace[step].get("r3c3t13s24d1r14r8r11_event_detail") or {}) if full else {} for step in event_steps]
        event_exact = bool(full and all(trace[step].get("r3c3t13s24d1r14r8r11_event") == name and event.get("passed") is True and all(bool(value) for value in (event.get("criteria") or {}).values()) for step, name, event in zip(event_steps, event_names, events)))
        center_target_exact = bool(event_exact and events[1].get("stored_target_card15_fields") == events[0].get("target_card15_fields") and events[2].get("stored_center_card15_fields") == events[0].get("center_card15_fields") and events[2].get("issue_target_card15_fields") == events[0].get("target_card15_fields"))
        zero_steps = [step for step in range(PREFIX_END, horizon) if step not in set(event_steps)]
        zero_exact = bool(full and actions.shape == (horizon, N_COILS) and currents.shape == (horizon + 1, N_COILS) and np.array_equal(actions[zero_steps], np.zeros((len(zero_steps), N_COILS))) and np.array_equal(currents[np.asarray(zero_steps) + 1] - currents[zero_steps], np.zeros((len(zero_steps), N_COILS))))
        finite = bool(full and np.all(np.isfinite(actions)) and np.all(np.isfinite(currents)) and all(math.isfinite(float(row[key])) for row in trajectory for key in ("R", "Z", "Ip")) and all(np.all(np.isfinite(np.asarray(row.get("wire_currents_a", []), dtype=float))) for row in trajectory) and not any(bool(row.get("abnormal")) for row in trajectory))
        forbidden = sum(any(bool(row.get(key)) for key in (
            "r3c3t13s24d1r14r8r11_forbidden_input_used", "r3c3t13s24d1r14r8r11_pair_or_history_label_used",
            "r3c3t13s24d1r14r8r11_future_measurement_used", "r3c3t13s24d1r14r8r11_future_action_used",
            "r3c3t13s24d1r14r8r11_source_result_used", "r3c3t13s24d1r14r8r11_hidden_wire_used",
        )) for row in trace)
        payload = _read(ctx.paths.variants / f"payload_{spec['experiment_id']}.json")
        minimum, maximum = r8r7.r8.d1r11.s21.s13._current_limits_tsc(payload)
        center, half = 0.5 * (minimum + maximum), 0.5 * (maximum - minimum)
        utilization = float(np.max(np.abs((currents - center) / half))) if currents.shape == (horizon + 1, N_COILS) else None
        increments = [event.get("incremental_normalized_action_linf") for event in events]
        passed = bool(
            result.get("success") and full and prefix_state and prefix_trace and calibration
            and event_exact and center_target_exact and zero_exact and finite and forbidden == 0
            and all(value is not None and math.isfinite(float(value)) for value in increments)
            and float(increments[0]) <= float(contract["maximum_incremental_normalized_action_linf"]) + 1e-12
            and float(increments[1]) <= float(contract["maximum_incremental_normalized_action_linf"]) + 1e-12
            and float(increments[2]) <= float(contract["maximum_online_cancel_incremental_linf"]) + 1e-12
            and utilization is not None and utilization <= float(contract["maximum_current_utilization"]) + 1e-12
        )
        rows.append(
            {
                "experiment_id": spec["experiment_id"], "pair_id": spec["pair_id"], "history_member": spec["history_member"],
                "issue_task_step": int(spec["r8r11_issue_task_step"]), "sign": int(spec["r8r11_sign"]),
                "runtime_success": bool(result.get("success")), "full_horizon": full,
                "source_prefix_state_exact": prefix_state, "source_prefix_trace_exact": prefix_trace,
                "calibration_exact": calibration, "event_exact": event_exact,
                "center_target_exact": center_target_exact, "zero_non_event_exact": zero_exact,
                "finite": finite, "forbidden_trace_count": forbidden,
                "issue_increment": increments[0] if len(increments) > 0 else None,
                "refresh_increment": increments[1] if len(increments) > 1 else None,
                "cancel_increment": increments[2] if len(increments) > 2 else None,
                "maximum_current_utilization": utilization,
                "failure_reason": str(result.get("failure_reason") or ""), "passed": passed,
            }
        )
    inventory = r8r7.r8._inventory(ctx.paths.phase_raw(phase))
    expected = {"safety": 24, "qualification": 72}[phase]
    def maximum(key: str) -> float | None:
        values = [row.get(key) for row in rows]
        return max(map(float, values)) if values and all(value is not None and math.isfinite(float(value)) for value in values) else None
    report = {
        "schema_version": 1, "stage": STAGE, "phase": phase,
        "expected_raw_count": expected, "raw_inventory": inventory,
        "runtime_success_count": sum(bool(row["runtime_success"]) for row in rows),
        "full_horizon_count": sum(bool(row["full_horizon"]) for row in rows),
        "source_prefix_state_exact_count": sum(bool(row["source_prefix_state_exact"]) for row in rows),
        "source_prefix_trace_exact_count": sum(bool(row["source_prefix_trace_exact"]) for row in rows),
        "calibration_exact_count": sum(bool(row["calibration_exact"]) for row in rows),
        "event_exact_count": sum(bool(row["event_exact"]) for row in rows),
        "center_target_exact_count": sum(bool(row["center_target_exact"]) for row in rows),
        "zero_non_event_exact_count": sum(bool(row["zero_non_event_exact"]) for row in rows),
        "finite_count": sum(bool(row["finite"]) for row in rows),
        "forbidden_trace_count": sum(int(row["forbidden_trace_count"]) for row in rows),
        "maximum_issue_increment": maximum("issue_increment"),
        "maximum_refresh_increment": maximum("refresh_increment"),
        "maximum_cancel_increment": maximum("cancel_increment"),
        "maximum_current_utilization": maximum("maximum_current_utilization"),
        "passed_count": sum(bool(row["passed"]) for row in rows), "rows": rows,
    }
    report["passed"] = bool(inventory["count"] == expected and len(rows) == expected and report["passed_count"] == expected)
    report["route"] = ctx.cfg["routes"]["pass" if report["passed"] else "execution_fail"]
    _write(ctx.paths.analysis / f"{phase}_raw_primary.json", report)
    return report


def authorize_safety(ctx: Context) -> dict[str, Any]:
    state = _read(ctx.paths.state)
    independent = _read(ctx.paths.analysis / "offline_independent.json")
    if state.get("phase_status") != "offline_primary_ready" or independent.get("passed") is not True:
        raise ValueError("R8R11 offline independent gate failed")
    _set_state(ctx, phase_status="safety_authorized", offline_independent_sha256=_sha(ctx.paths.analysis / "offline_independent.json"))
    return {"stage": STAGE, "phase": "safety_authorized", "passed": True}


def run_phase(ctx: Context, phase: str, *, backend: str, resume: bool) -> dict[str, Any]:
    required = {"safety": "safety_authorized", "qualification": "qualification_authorized"}[phase]
    state = _read(ctx.paths.state)
    if state.get("phase_status") != required:
        raise ValueError(f"R8R11 {phase} is not authorized")
    if phase == "safety" and any(ctx.paths.phase_raw("qualification").glob("*.json.gz")):
        raise ValueError("R8R11 qualification raw opened before safety authorization")
    specs = _phase_specs(ctx, phase)
    execution = evaluate_specs(ctx, specs, phase=phase, backend=backend, resume=resume)
    primary = audit_raw_phase(ctx, phase)
    total = sum(r8r7.r8._inventory(ctx.paths.phase_raw(name))["count"] for name in PHASES)
    if not execution["passed"] or not primary["passed"]:
        _set_state(
            ctx, phase_status=f"{phase}_execution_failed", finished=True,
            real_tsc_executed=total > 0, new_raw_count=total,
            qualification_outcomes_opened=phase == "qualification", formal_outcomes_opened=False,
            stop_reason="runtime_restart_action_current_or_raw_gate_failed",
            verdict={"route": ctx.cfg["routes"]["execution_fail"], "passed": False},
        )
    else:
        _set_state(
            ctx, phase_status=f"{phase}_primary_ready", real_tsc_executed=True,
            new_raw_count=total, qualification_outcomes_opened=phase == "qualification",
            formal_outcomes_opened=False,
        )
    return {"stage": STAGE, "phase": phase, "execution": execution, "primary_raw_audit_passed": primary["passed"], "route": primary["route"]}


def authorize_qualification(ctx: Context) -> dict[str, Any]:
    state = _read(ctx.paths.state)
    independent = _read(ctx.paths.analysis / "safety_raw_independent.json")
    primary = _read(ctx.paths.analysis / "safety_raw_primary.json")
    if state.get("phase_status") != "safety_primary_ready" or primary.get("passed") is not True or independent.get("passed") is not True or independent.get("primary_agreement") is not True:
        raise ValueError("R8R11 safety independent gate failed")
    _set_state(ctx, phase_status="qualification_authorized", safety_independent_sha256=_sha(ctx.paths.analysis / "safety_raw_independent.json"))
    return {"stage": STAGE, "phase": "qualification_authorized", "passed": True}


def _formal_row(evaluator: Any, result: Mapping[str, Any], meta: Mapping[str, Any]) -> dict[str, Any]:
    values = np.asarray([[row["R"], row["Z"], row["Ip"]] for row in result["trajectory"]], dtype=float)
    compact = evaluator.evaluate(values)
    existing = evaluator.exact_existing_metric(result, values)
    differences = [abs(float(compact[key]) - float(existing[key])) for key in ("formal_minimum_signed_margin", "formal_mean_signed_margin")]
    return {
        **dict(meta),
        "formal_contract_pass": bool(compact["formal_contract_pass"]),
        "formal_best_arrival_ms": int(compact["formal_best_arrival_ms"]),
        "formal_minimum_signed_margin": float(compact["formal_minimum_signed_margin"]),
        "formal_mean_signed_margin": float(compact["formal_mean_signed_margin"]),
        "existing_pass": bool(existing["formal_contract_pass"]),
        "existing_arrival_ms": int(existing["formal_best_arrival_ms"]),
        "maximum_margin_abs_difference": max(differences),
    }


def compute_formal_authority(ctx: Context) -> dict[str, Any]:
    specs = _saved_specs(ctx)
    baseline_specs, baseline_results = _source_baselines(ctx)
    all_specs = [*baseline_specs, *specs]
    evaluators, _ = r8r7.r8.d1r11._formal_callback(ctx.source_ctx.r8_ctx.d1r11_ctx, all_specs)
    rows = []
    for spec in baseline_specs:
        rows.append(_formal_row(evaluators[str(spec["experiment_id"])], baseline_results[str(spec["experiment_id"])], {"kind": "baseline", "experiment_id": spec["experiment_id"], "pair_id": spec["pair_id"], "history_member": spec["history_member"], "issue_task_step": -1, "sign": 0}))
    for spec in specs:
        result = r8r7.r8._read_gz(ctx.paths.phase_raw(str(spec["partition"])) / f"{spec['experiment_id']}.json.gz")
        rows.append(_formal_row(evaluators[str(spec["experiment_id"])], result, {"kind": "candidate", "experiment_id": spec["experiment_id"], "pair_id": spec["pair_id"], "history_member": spec["history_member"], "issue_task_step": int(spec["r8r11_issue_task_step"]), "sign": int(spec["r8r11_sign"])}))
    tolerance = float(ctx.cfg["formal_contract"]["metric_equivalence_absolute_tolerance"])
    equivalence = bool(all(row["formal_contract_pass"] == row["existing_pass"] and row["formal_best_arrival_ms"] == row["existing_arrival_ms"] and float(row["maximum_margin_abs_difference"]) <= tolerance for row in rows))
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault((str(row["pair_id"]), str(row["history_member"])), []).append(row)
    contexts = []
    for key, group in sorted(groups.items()):
        baseline = [row for row in group if row["kind"] == "baseline"]
        candidates = [row for row in group if row["kind"] == "candidate"]
        if len(baseline) != 1 or len(candidates) != 6:
            raise ValueError("R8R11 formal context coverage changed")
        base = baseline[0]
        best = max(candidates, key=lambda row: (float(row["formal_minimum_signed_margin"]), float(row["formal_mean_signed_margin"]), -int(row["issue_task_step"]), -int(row["sign"])))
        oracle = max([base, *candidates], key=lambda row: (float(row["formal_minimum_signed_margin"]), float(row["formal_mean_signed_margin"]), row["kind"] == "baseline", -int(row["issue_task_step"]), -int(row["sign"])))
        contexts.append(
            {
                "pair_id": key[0], "history_member": key[1], "baseline": base,
                "candidates": candidates, "best_candidate_experiment_id": best["experiment_id"],
                "best_candidate_minimum_margin_gain": float(best["formal_minimum_signed_margin"]) - float(base["formal_minimum_signed_margin"]),
                "failed_baseline_repaired": bool(not base["formal_contract_pass"] and any(row["formal_contract_pass"] for row in candidates)),
                "held_oracle_formal_pass": bool(oracle["formal_contract_pass"]),
                "held_oracle_experiment_id": oracle["experiment_id"],
            }
        )
    baseline_pass = sum(bool(row["baseline"]["formal_contract_pass"]) for row in contexts)
    repairs = sum(bool(row["failed_baseline_repaired"]) for row in contexts)
    oracle_pass = sum(bool(row["held_oracle_formal_pass"]) for row in contexts)
    gains = [float(row["best_candidate_minimum_margin_gain"]) for row in contexts if not row["baseline"]["formal_contract_pass"]]
    gate = ctx.cfg["scientific_gate"]
    scientific = bool(
        baseline_pass == int(gate["required_baseline_formal_pass_count"])
        and len(contexts) - baseline_pass == int(gate["required_failed_baseline_count"])
        and repairs >= int(gate["minimum_repaired_failed_baseline_count"])
        and oracle_pass >= int(gate["minimum_held_oracle_formal_pass_count"])
        and oracle_pass > baseline_pass
    )
    return {
        "row_count": len(rows), "formal_metric_equivalence_passed": equivalence,
        "maximum_margin_abs_difference": max(float(row["maximum_margin_abs_difference"]) for row in rows),
        "context_count": len(contexts), "baseline_formal_pass_count": baseline_pass,
        "failed_baseline_count": len(contexts) - baseline_pass,
        "candidate_formal_pass_trajectory_count": sum(bool(row["formal_contract_pass"]) for row in rows if row["kind"] == "candidate"),
        "repaired_failed_baseline_count": repairs, "held_oracle_formal_pass_count": oracle_pass,
        "failed_baseline_best_margin_gain": {"minimum": min(gains), "median": statistics.median(gains), "maximum": max(gains)},
        "context_rows": contexts, "rows": rows,
        "scientific_gate_passed": scientific,
    }


def finalize_primary(ctx: Context) -> dict[str, Any]:
    state = _read(ctx.paths.state)
    safety_primary = _read(ctx.paths.analysis / "safety_raw_primary.json")
    qualification_primary = _read(ctx.paths.analysis / "qualification_raw_primary.json")
    safety_independent = _read(ctx.paths.analysis / "safety_raw_independent.json")
    qualification_independent = _read(ctx.paths.analysis / "qualification_raw_independent.json")
    if state.get("phase_status") != "qualification_primary_ready" or not all(value.get("passed") is True for value in (safety_primary, qualification_primary, safety_independent, qualification_independent)) or not all(value.get("primary_agreement") is True for value in (safety_independent, qualification_independent)):
        raise ValueError("R8R11 raw independent gates incomplete")
    formal = compute_formal_authority(ctx)
    integrity = bool(formal["formal_metric_equivalence_passed"])
    scientific = bool(integrity and formal["scientific_gate_passed"])
    route = ctx.cfg["routes"]["pass" if scientific else "authority_fail"]
    detailed = {
        "schema_version": 1, "stage": STAGE, "identity": IDENTITY,
        "source_authenticated": True, "integrity_gate_passed": integrity,
        "scientific_gate_passed": scientific, "formal_authority": formal,
        "safety_raw_inventory": safety_primary["raw_inventory"],
        "qualification_raw_inventory": qualification_primary["raw_inventory"],
        "new_raw_count": 96, "real_tsc_executed": True, "route": route,
        "passed": scientific,
    }
    _write(ctx.paths.analysis / "primary_detailed.json", detailed)
    summary = {
        "schema_version": 1, "stage": STAGE, "identity": IDENTITY,
        "source_authenticated": True, "integrity_gate_passed": integrity,
        "scientific_gate_passed": scientific,
        "formal_metric_equivalence_passed": formal["formal_metric_equivalence_passed"],
        "maximum_margin_abs_difference": formal["maximum_margin_abs_difference"],
        "context_count": formal["context_count"],
        "baseline_formal_pass_count": formal["baseline_formal_pass_count"],
        "failed_baseline_count": formal["failed_baseline_count"],
        "candidate_formal_pass_trajectory_count": formal["candidate_formal_pass_trajectory_count"],
        "repaired_failed_baseline_count": formal["repaired_failed_baseline_count"],
        "held_oracle_formal_pass_count": formal["held_oracle_formal_pass_count"],
        "failed_baseline_best_margin_gain": formal["failed_baseline_best_margin_gain"],
        "new_raw_count": 96, "real_tsc_executed": True, "route": route, "passed": scientific,
    }
    _write(ctx.paths.analysis / "primary_summary.json", summary)
    _set_state(ctx, phase_status="final_primary_ready", formal_outcomes_opened=True, primary_route=route, primary_summary_sha256=_sha(ctx.paths.analysis / "primary_summary.json"))
    return summary


def postprocess(ctx: Context) -> dict[str, Any]:
    state = _read(ctx.paths.state)
    primary = _read(ctx.paths.analysis / "primary_summary.json")
    independent = _read(ctx.paths.analysis / "final_independent.json")
    if state.get("phase_status") != "final_primary_ready" or independent.get("passed") is not True or independent.get("primary_route_agreement") is not True or independent.get("primary_outcome_agreement") is not True or independent.get("primary_numerical_agreement") is not True:
        raise ValueError("R8R11 final independent agreement failed")
    final = copy.deepcopy(primary)
    final.update(
        {
            "phase": "final", "primary_detailed_sha256": _sha(ctx.paths.analysis / "primary_detailed.json"),
            "primary_summary_sha256": _sha(ctx.paths.analysis / "primary_summary.json"),
            "independent_sha256": _sha(ctx.paths.analysis / "final_independent.json"),
            "stage_manifest_sha256": _sha(ctx.paths.manifest),
        }
    )
    _write(ctx.paths.analysis / "final_report.json", final)
    _set_state(
        ctx, phase_status="complete", finished=True, real_tsc_executed=True,
        new_raw_count=96, qualification_outcomes_opened=True, formal_outcomes_opened=True,
        final_report_sha256=_sha(ctx.paths.analysis / "final_report.json"),
        final_independent_sha256=_sha(ctx.paths.analysis / "final_independent.json"),
        stop_reason="" if final["passed"] else "formal_authority_gate_failed",
        verdict={"route": final["route"], "passed": bool(final["passed"])},
    )
    return final


def execute(ctx: Context, *, command: str, backend: str, resume: bool) -> dict[str, Any]:
    if command == "offline":
        return prepare_offline(ctx)
    if command == "authorize-safety":
        return authorize_safety(ctx)
    if command in PHASES:
        return run_phase(ctx, command, backend=backend, resume=resume)
    if command == "authorize-qualification":
        return authorize_qualification(ctx)
    if command == "finalize-primary":
        return finalize_primary(ctx)
    if command == "postprocess":
        return postprocess(ctx)
    raise ValueError(f"unsupported R8R11 command: {command}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--r8r7-run", type=Path, required=True)
    parser.add_argument("--r8-run", type=Path, required=True)
    parser.add_argument("--r8r1-output", type=Path, required=True)
    parser.add_argument("--r8r6-run", type=Path, required=True)
    for name in (
        "source-d1r11-run", "source-r2-run", "source-r4-run", "source-r6-run",
        "source-s21-run", "source-s23r1-output", "source-s24-run", "source-d1r9-v1",
        "source-d1r9-v2", "source-d1r10-run", "source-d1r10-audit", "source-stage42r3b-run",
        "source-stage42r3c3-run", "source-stage42r3c3-bank-dir", "source-stage42r3c3t1-run",
        "source-stage42r3c3t1-audit-dir", "source-stage42r3c3t3-controller-bank",
        "q1-run", "q2-run", "q1-audit", "q2-audit", "r3b-server-audit", "r3b-snapshot-checks",
    ):
        parser.add_argument(f"--{name}", dest=name.replace("-", "_"), type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--command", choices=("offline", "authorize-safety", "safety", "authorize-qualification", "qualification", "finalize-primary", "postprocess"), required=True)
    parser.add_argument("--backend", choices=("serial", "ray"), default="ray")
    parser.add_argument("--resume", action="store_true")
    return parser


def main() -> None:
    args = _parser().parse_args()
    ctx = load_context(args)
    result = execute(ctx, command=args.command, backend=args.backend, resume=args.resume)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
