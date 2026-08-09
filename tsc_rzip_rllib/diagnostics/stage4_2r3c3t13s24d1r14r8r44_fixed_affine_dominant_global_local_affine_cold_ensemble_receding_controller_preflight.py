"""R8R44 affine-dominant cold-ensemble receding-controller preflight."""

from __future__ import annotations

import argparse
import copy
import json
import math
import traceback
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r31_aligned_explicit_four_coordinate_feedback_sentinel
    as r8r31,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r43_fixed_affine_dominant_global_ridge_local_affine_cold_ensemble_preflight
    as source_r8r43,
)


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S24D1R14R8R44"
IDENTITY = "fixed_affine_dominant_global_local_affine_cold_ensemble_receding_controller_preflight_v1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r44_fixed_affine_dominant_global_local_affine_cold_ensemble_receding_controller_preflight"
FACTORS = r8r31.OUTPUT_FACTORS

_read = source_r8r43._read
_write = source_r8r43._write
_sha = source_r8r43._sha
_digest = source_r8r43._digest
_jsonable = source_r8r43._jsonable


class SourceBlockedError(RuntimeError):
    """The prospectively required final R8R43 PASS is not present."""


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Paths:
    stage: Path
    analysis: Path
    model: Path
    state: Path
    manifest: Path


@dataclass(frozen=True)
class Context:
    cfg: Mapping[str, Any]
    config_path: Path
    paths: Paths
    r8r43_ctx: Any
    r8r43_stage: Path
    source_ctx: Any


def _paths(run_dir: Path) -> Paths:
    stage = run_dir.expanduser().resolve() / RUN_NAME
    return Paths(
        stage=stage,
        analysis=stage / "analysis",
        model=stage / "model",
        state=stage / "stage_state.json",
        manifest=stage / "stage_manifest.json",
    )


def validate_config(cfg: Mapping[str, Any], *, project_root: Path) -> None:
    root = project_root.resolve()
    design = (root / str(cfg["design_document"])).resolve()
    source_config = (root / str(cfg["source_r8r43_config"])).resolve()
    bank = cfg["bank_contract"]
    model = cfg["model_contract"]
    gates = cfg["model_gates"]
    planner = cfg["planner_contract"]
    action = cfg["action_contract"]
    support = cfg["support_contract"]
    formal = cfg["formal_contract"]
    offline = cfg["offline_gate"]
    scope = cfg["scientific_scope"]
    routes = {
        "source_blocked": "FIXED_AFFINE_DOMINANT_COLD_ENSEMBLE_CONTROLLER_PREFLIGHT_BLOCKED_BY_SOURCE",
        "execution_fail": "FIXED_AFFINE_DOMINANT_COLD_ENSEMBLE_CONTROLLER_PREFLIGHT_EXECUTION_FAIL_STOP",
        "safety_fail": "FIXED_AFFINE_DOMINANT_COLD_ENSEMBLE_CONTROLLER_PREFLIGHT_SAFETY_FAIL_NO_TSC",
        "authority_fail": "FIXED_AFFINE_DOMINANT_COLD_ENSEMBLE_CONTROLLER_PREFLIGHT_AUTHORITY_INSUFFICIENT_NO_TSC",
        "pass": "FIXED_AFFINE_DOMINANT_COLD_ENSEMBLE_CONTROLLER_PREFLIGHT_PASS_REAL_SENTINEL_DESIGN_REQUIRED",
    }
    invalid = (
        int(cfg.get("schema_version", -1)) != SCHEMA_VERSION
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("run_name") != RUN_NAME
        or not design.is_file()
        or _sha(design) != cfg.get("design_document_sha256")
        or not source_config.is_file()
        or _sha(source_config) != cfg.get("source_r8r43_config_sha256")
        or cfg["source_r8r43"].get("required_route")
        != "FIXED_AFFINE_DOMINANT_COLD_ENSEMBLE_PASS_CONTROLLER_PREFLIGHT_DESIGN_REQUIRED"
        or any(
            len(str(value)) != 64
            for key, value in cfg["source_r8r43"].items()
            if key.endswith("_sha256")
        )
        or tuple(
            int(bank[name])
            for name in (
                "trajectory_count",
                "physical_pair_count",
                "history_context_count",
                "schedule_count",
                "interval_record_count",
                "five_component_time_row_count",
            )
        )
        != (560, 8, 16, 35, 3360, 14560)
        or tuple(map(int, bank["decision_task_steps"])) != (10, 12, 14, 16, 18, 22)
        or tuple(
            bank[name]
            for name in ("bank_digest", "feature_digest", "target_digest")
        )
        != (
            "a84995970a5c1f0f2d2e964c6b97cbaf213ac8f86d70a3666279ae144ba2de2e",
            "80ed0b20b99f6f277ac1e09f85ad33c6fb8a1e611824901509eaf6a3c7b830db",
            "0f445fca5bb2dbb1da7fb1fc5e1951161322caccc4219371653ffdb55eaa8539",
        )
        or tuple(
            int(model[name])
            for name in (
                "global_expanded_dimension",
                "local_coordinate_dimension",
                "local_neighbor_count",
                "local_slope_dimension",
            )
        )
        != (238, 62, 64, 62)
        or tuple(
            float(model[name])
            for name in (
                "global_ridge_penalty",
                "local_coordinate_scale_floor",
                "local_uniform_neighbor_weight",
                "local_slope_ridge_penalty",
                "local_intercept_penalty",
                "global_weight",
                "local_weight",
                "reserve_multiplier",
            )
        )
        != (1e-4, 1e-12, 1.0, 1.0, 0.0, 0.25, 0.75, 1.25)
        or model.get("global_unpenalized_centered_intercept") is not True
        or model.get("local_inactive_centered_columns_zero_slope") is not True
        or model.get("local_solver") != "augmented_lstsq"
        or list(model.get("physical_point_error_floors", []))
        != [0.015, 0.015, 3000.0, 0.05, 0.05]
        or list(model.get("primary_independent_component_scales", []))
        != [0.015, 0.015, 3000.0, 0.05, 0.05]
        or float(model.get("primary_independent_scaled_tolerance", -1.0)) != 1e-9
        or any(
            model.get(name) is not False
            for name in (
                "weight_search_allowed",
                "gating_allowed",
                "innovation_enabled",
                "feature_search_allowed",
                "ridge_search_allowed",
                "neighbor_search_allowed",
                "response_weighting_allowed",
                "outlier_deletion_allowed",
                "tube_clipping_allowed",
            )
        )
        or list(gates.get("maximum_point_error", []))
        != [0.015, 0.015, 3000.0, 0.05, 0.05]
        or list(gates.get("maximum_tube_half_width", []))
        != [0.025, 0.025, 5000.0, 0.08, 0.08]
        or float(gates.get("required_reserved_tube_containment_rate", -1.0)) != 1.0
        or float(gates.get("required_whole_pair_state_support_rate", -1.0)) != 1.0
        or float(gates.get("required_finite_prediction_rate", -1.0)) != 1.0
        or int(gates.get("required_forbidden_input_count", -1)) != 0
        or tuple(
            int(planner[name])
            for name in ("candidate_count", "beam_width", "dynamic_exact_search_radius")
        )
        != (17, 512, 16)
        or tuple(map(int, planner["decision_task_steps"])) != (10, 12, 14, 16, 18, 22)
        or planner.get("measurement_recentered") is not True
        or planner.get("execute_first_action_only") is not True
        or planner.get("failed_plan_deployment_allowed") is not False
        or planner.get("fallback") != "exact_current_target_hold"
        or planner.get("canonical_matrix_float64_le_c_sha256")
        != "c8cd62c00c1f60b46312927789659657dc8cc35717533193433b0e398c1ec94c"
        or tuple(
            float(action[name])
            for name in (
                "maximum_incremental_normalized_action_linf",
                "maximum_total_normalized_action_abs",
                "maximum_current_utilization",
                "minimum_desired_applied_current_cosine",
                "maximum_relative_off_basis_residual",
            )
        )
        != (0.25, 1.0, 0.55, 0.98, 0.1)
        or not all(
            action.get(name) is True
            for name in (
                "require_exact_card15_issue",
                "require_exact_card15_refresh",
                "safe_stop_before_failed_advance",
            )
        )
        or tuple(
            float(support[name])
            for name in (
                "required_observed_transition_support_rate",
                "coordinate_scale",
                "affine_singular_value_tolerance",
                "affine_residual_tolerance",
                "convex_hull_inequality_tolerance",
            )
        )
        != (1.0, 1.5, 1e-12, 1e-12, 1e-10)
        or tuple(int(support[name]) for name in ("coordinate_dimension", "transition_dimension"))
        != (4, 8)
        or support.get("qhull_joggle_allowed") is not False
        or tuple(
            int(formal[name])
            for name in (
                "normal_arrival_deadline_step",
                "normal_hold_through_step",
                "weak_arrival_deadline_step",
                "weak_hold_through_step",
                "arrival_streak_steps",
            )
        )
        != (25, 35, 27, 37, 3)
        or tuple(
            float(formal[name])
            for name in ("position_tolerance_m", "speed_tolerance_m_per_s", "ip_tolerance_A")
        )
        != (0.03, 0.1, 10000.0)
        or formal.get("arrival_deadline_expansion_allowed") is not False
        or tuple(
            int(offline[name])
            for name in (
                "required_safe_search_context_count",
                "minimum_predicted_repaired_failed_baseline_count",
                "maximum_predicted_regressed_baseline_pass_count",
                "minimum_predicted_oracle_count",
                "minimum_nonzero_first_action_count",
                "required_fault_injection_count",
            )
        )
        != (16, 1, 0, 7, 1, 6)
        or cfg.get("routes") != routes
        or scope.get("zero_new_tsc") is not True
        or scope.get("controller_execution_authorized") is not False
        or scope.get("gate_a_qualified") is not False
        or scope.get("expert_data_allowed") is not False
        or scope.get("bc_dagger_or_rl_allowed") is not False
        or scope.get("all_stage_trajectories_allowed_in_expert_dataset") is not False
        or scope.get("global_plant_reachability_claimed") is not False
    )
    if invalid:
        raise ValueError("R8R44 frozen config changed")


def _validate_planner_source(ctx: Context) -> None:
    source = ctx.source_ctx
    cfg = source.cfg
    planner = ctx.cfg["planner_contract"]
    action = ctx.cfg["action_contract"]
    support = ctx.cfg["support_contract"]
    formal = ctx.cfg["formal_contract"]
    if (
        _sha(source.config_path) != ctx.cfg["source_r8r31_config_sha256"]
        or int(cfg["candidate_contract"]["candidate_count"]) != planner["candidate_count"]
        or list(cfg["candidate_contract"]["decision_task_steps"])
        != list(planner["decision_task_steps"])
        or cfg["candidate_contract"]["canonical_matrix_float64_le_c_sha256"]
        != planner["canonical_matrix_float64_le_c_sha256"]
        or int(cfg["candidate_contract"]["dynamic_exact_search_radius"])
        != planner["dynamic_exact_search_radius"]
        or int(cfg["search_contract"]["beam_width"]) != planner["beam_width"]
        or cfg["search_contract"]["execute_first_action_only"] is not True
        or cfg["search_contract"]["failed_plan_deployment_allowed"] is not False
        or any(cfg["action_contract"][key] != value for key, value in action.items())
        or any(
            cfg["support_contract"][key] != value
            for key, value in support.items()
            if key != "required_observed_transition_support_rate"
        )
        or any(cfg["formal_contract"][key] != value for key, value in formal.items())
    ):
        raise ValueError("R8R44 frozen R8R31 planner source changed")


def load_context(args: argparse.Namespace) -> Context:
    root = _root()
    config_path = args.config.expanduser().resolve()
    cfg = _read(config_path)
    validate_config(cfg, project_root=root)
    source_args = SimpleNamespace(**vars(args))
    source_args.config = (root / str(cfg["source_r8r43_config"])).resolve()
    source_args.run_dir = args.r8r43_run.expanduser().resolve()
    r8r43_ctx = source_r8r43.load_context(source_args)
    ctx = Context(
        cfg=cfg,
        config_path=config_path,
        paths=_paths(args.run_dir),
        r8r43_ctx=r8r43_ctx,
        r8r43_stage=r8r43_ctx.paths.stage,
        source_ctx=r8r43_ctx.source_ctx,
    )
    _validate_planner_source(ctx)
    return ctx


def authenticate_sources(ctx: Context) -> dict[str, Any]:
    paths = source_r8r43._source_paths(ctx.r8r43_stage)
    contract = ctx.cfg["source_r8r43"]
    if any(not path.is_file() for path in paths.values()):
        raise ValueError("R8R44 R8R43 source evidence incomplete")
    hashes = {name: _sha(path) for name, path in paths.items()}
    if any(hashes[name] != contract[f"{name}_sha256"] for name in hashes):
        raise ValueError("R8R44 R8R43 source hash changed")
    final = _read(paths["final_report"])
    independent = _read(paths["independent"])
    if (
        final.get("route") != contract["required_route"]
        or final.get("integrity_gate_passed") is not True
        or final.get("scientific_gate_passed") is not True
        or independent.get("passed") is not True
        or independent.get("primary_route_agreement") is not True
        or independent.get("primary_outcome_agreement") is not True
    ):
        raise SourceBlockedError("R8R44 requires exact independently reproduced final R8R43 PASS")
    r8r43 = source_r8r43._authenticate_final_source(
        ctx.r8r43_stage, contract, label="R8R43"
    )
    transitive = source_r8r43.authenticate_sources(ctx.r8r43_ctx)
    return {"r8r43_final": r8r43, "transitive": transitive, "passed": True}


def _verify_bank(trajectories: Sequence[Mapping[str, Any]], bank: Mapping[str, Any], cfg: Mapping[str, Any]) -> None:
    source_r8r43._verify_bank(trajectories, bank, cfg)


def _baseline_classification(ctx: Context) -> dict[tuple[str, str], bool]:
    source = _read(ctx.source_ctx.r8r28_stage / "analysis/primary_detailed.json")
    result = {
        (str(row["pair_id"]), str(row["history_member"])): bool(
            row["baseline"]["formal_contract_pass"]
        )
        for row in source["formal_authority"]["context_rows"]
    }
    if len(result) != 16 or sum(result.values()) != 6:
        raise ValueError("R8R44 frozen six-pass ten-fail baseline changed")
    return result


def evaluate_planning(
    ctx: Context,
    trajectories: Sequence[Mapping[str, Any]],
    context_meta: Mapping[tuple[str, str], Mapping[str, Any]],
    combined_tube: Sequence[np.ndarray],
    *,
    fit_model_fn: Callable[[Sequence[Mapping[str, Any]], Callable[[Mapping[str, Any]], bool], Mapping[str, Any]], Mapping[str, Any]],
    predict_ensemble_fn: Callable[[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]], np.ndarray],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    model = fit_model_fn(trajectories, lambda _row: True, ctx.r8r43_ctx.cfg)
    hulls = r8r31.transition_hulls(trajectories, ctx.source_ctx.cfg)
    support = r8r31.planning_support(trajectories, ctx.source_ctx.cfg)

    def predictor(current_model: Mapping[str, Any], row: Mapping[str, Any]) -> np.ndarray:
        value = np.asarray(
            predict_ensemble_fn(current_model, row, ctx.r8r43_ctx.cfg), dtype=float
        )
        if value.shape != (len(row["targets"]), 5) or not np.all(np.isfinite(value)):
            raise ValueError("R8R44 planner ensemble prediction invalid")
        return value

    plans = [
        r8r31.plan_context(
            ctx.source_ctx,
            context_meta[key],
            model,
            combined_tube,
            support,
            hulls,
            predict_fn=predictor,
        )
        for key in sorted(context_meta)
    ]
    baseline = _baseline_classification(ctx)
    repairs = regressions = oracle = nonzero = 0
    for plan in plans:
        key = (str(plan["pair_id"]), str(plan["history_member"]))
        robust = bool(plan["robust_formal_plan_found"])
        policy = bool(robust or baseline[key])
        repairs += int(not baseline[key] and robust)
        regressions += int(baseline[key] and not policy)
        oracle += int(policy)
        selected = plan.get("selected_plan") or {}
        tokens = selected.get("candidate_indices") or []
        nonzero += int(robust and bool(tokens) and int(tokens[0]) != 0)
        plan["baseline_formal_pass"] = baseline[key]
        plan["fallback_or_plan_predicted_pass"] = policy
        plan["selected_first_action_index"] = int(tokens[0]) if robust and tokens else 0
        plan["selected_first_action_mode"] = (
            "safe_nonzero_first_action" if robust and tokens and int(tokens[0]) != 0
            else "safe_hold_first_action" if robust
            else "exact_current_target_hold_fallback"
        )
    faults = r8r31.fault_injections()
    gate = ctx.cfg["offline_gate"]
    safe_count = sum(bool(plan["safe_search_complete"]) for plan in plans)
    safety_passed = bool(
        len(plans) == int(gate["required_safe_search_context_count"])
        and safe_count == len(plans)
        and faults["pass_count"] == int(gate["required_fault_injection_count"])
        and faults["passed"]
    )
    authority_passed = bool(
        safety_passed
        and repairs >= int(gate["minimum_predicted_repaired_failed_baseline_count"])
        and regressions <= int(gate["maximum_predicted_regressed_baseline_pass_count"])
        and oracle >= int(gate["minimum_predicted_oracle_count"])
        and nonzero >= int(gate["minimum_nonzero_first_action_count"])
    )
    planning = {
        "ran": True,
        "measurement_recentered": True,
        "execute_first_action_only": True,
        "fallback": "exact_current_target_hold",
        "safe_search_context_count": safe_count,
        "predicted_repaired_failed_baseline_count": repairs,
        "predicted_regressed_baseline_pass_count": regressions,
        "predicted_fallback_plus_plan_oracle_count": oracle,
        "nonzero_first_action_count": nonzero,
        "plans": plans,
        "safety_passed": safety_passed,
        "authority_passed": authority_passed,
        "passed": authority_passed,
    }
    support_artifact = {
        "thresholds": support["thresholds"],
        "training_maxima": support["training_maxima"],
        "features": support["features"],
    }
    hull_summary = [
        {
            "interval": row["interval"],
            "affine_rank": row["affine_rank"],
            "observed_transition_count": row["observed_transition_count"],
            "singular_values": row["singular_values"],
            "digest": row["digest"],
        }
        for row in hulls
    ]
    return _jsonable(planning), _jsonable(faults), _jsonable(support_artifact), _jsonable(hull_summary)


def assemble_result(
    ctx: Context,
    authentication: Mapping[str, Any],
    bank: Mapping[str, Any],
    base_detailed: Mapping[str, Any],
    planning: Mapping[str, Any],
    faults: Mapping[str, Any],
    model_binding: Mapping[str, Any],
) -> dict[str, Any]:
    model_gate = bool(
        model_binding["passed"]
        and base_detailed["integrity_gate_passed"]
        and base_detailed["scientific_gate_passed"]
        and base_detailed["model_gate_passed"]
        and base_detailed["route"] == ctx.cfg["source_r8r43"]["required_route"]
    )
    safety = bool(model_gate and planning["safety_passed"] and faults["passed"])
    authority = bool(safety and planning["authority_passed"])
    route = (
        ctx.cfg["routes"]["safety_fail"]
        if not model_gate or not safety
        else ctx.cfg["routes"]["pass"]
        if authority
        else ctx.cfg["routes"]["authority_fail"]
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "identity": IDENTITY,
        "source_authentication": authentication,
        "bank_evidence": bank,
        "source_model_binding": model_binding,
        "source_model_evaluation": {
            "local_cardinality_audit": base_detailed["local_cardinality_audit"],
            "outer_model_evaluation": base_detailed["outer_model_evaluation"],
            "schedule_jackknife": base_detailed["schedule_jackknife"],
            "combined_tube_maximum_physical_half_width": base_detailed[
                "combined_tube_maximum_physical_half_width"
            ],
            "combined_tube_cap_passed": base_detailed["combined_tube_cap_passed"],
        },
        "model_gate_passed": model_gate,
        "planning_evaluation": planning,
        "fault_injection": faults,
        "safety_gate_passed": safety,
        "authority_gate_passed": authority,
        "integrity_gate_passed": True,
        "scientific_gate_passed": authority,
        "passed": True,
        "route": route,
        "real_tsc_executed": False,
        "plant_step_count": 0,
        "new_raw_count": 0,
        "controller_execution_authorized": False,
        "gate_a_qualified": False,
        "expert_data_allowed": False,
    }


def compute_from_bank(
    ctx: Context,
    authentication: Mapping[str, Any],
    trajectories: Sequence[Mapping[str, Any]],
    context_meta: Mapping[tuple[str, str], Mapping[str, Any]],
    bank: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    _verify_bank(trajectories, bank, ctx.r8r43_ctx.cfg)
    transitive = source_r8r43.authenticate_sources(ctx.r8r43_ctx)
    base_detailed, base_model = source_r8r43.compute_from_bank(
        ctx.r8r43_ctx, transitive, trajectories, bank
    )
    source_detailed = _read(ctx.r8r43_stage / "analysis/primary_detailed.json")
    source_model = _read(ctx.r8r43_stage / "model/preflight_model.json")
    detailed_exact = base_detailed == source_detailed
    model_exact = base_model == source_model
    model_binding = {
        "recomputed_primary_detailed_digest": _digest(base_detailed),
        "source_primary_detailed_digest": _digest(source_detailed),
        "recomputed_model_digest": _digest(base_model),
        "source_model_digest": _digest(source_model),
        "primary_detailed_exact": detailed_exact,
        "model_artifact_exact": model_exact,
        "passed": bool(detailed_exact and model_exact),
    }
    combined_tube = [np.asarray(row, dtype=float) for row in base_model["combined_tube"]]
    planning, faults, support, hulls = evaluate_planning(
        ctx,
        trajectories,
        context_meta,
        combined_tube,
        fit_model_fn=source_r8r43.fit_model,
        predict_ensemble_fn=lambda model, row, cfg: source_r8r43.predict(model, row, cfg)[2],
    )
    detailed = assemble_result(
        ctx, authentication, bank, base_detailed, planning, faults, model_binding
    )
    artifact = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "identity": IDENTITY,
        "model_kind": "fixed_affine_dominant_cold_ensemble_receding_controller_preflight",
        "base_model": base_model,
        "planning_model_evidence": source_r8r43.model_evidence(
            source_r8r43.fit_model(trajectories, lambda _row: True, ctx.r8r43_ctx.cfg)
        ),
        "combined_tube": base_model["combined_tube"],
        "support": support,
        "transition_hulls": hulls,
        "planning_evaluation": planning,
    }
    return _jsonable(detailed), _jsonable(artifact)


def _summary(detailed: Mapping[str, Any], model_sha: str) -> dict[str, Any]:
    planning = detailed["planning_evaluation"]
    model = detailed["source_model_evaluation"]
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "identity": IDENTITY,
        "phase": "offline_primary",
        "passed": True,
        "integrity_gate_passed": True,
        "scientific_gate_passed": bool(detailed["scientific_gate_passed"]),
        "route": detailed["route"],
        "model_artifact_sha256": model_sha,
        "trajectory_count": int(detailed["bank_evidence"]["trajectory_count"]),
        "schedule_count": int(detailed["bank_evidence"]["schedule_count"]),
        "interval_record_count": int(detailed["bank_evidence"]["interval_record_count"]),
        "bank_digest": detailed["bank_evidence"]["bank_digest"],
        "source_model_binding_passed": bool(detailed["source_model_binding"]["passed"]),
        "combined_tube_maximum_physical_half_width": model[
            "combined_tube_maximum_physical_half_width"
        ],
        "safe_search_context_count": int(planning["safe_search_context_count"]),
        "predicted_repaired_failed_baseline_count": int(
            planning["predicted_repaired_failed_baseline_count"]
        ),
        "predicted_regressed_baseline_pass_count": int(
            planning["predicted_regressed_baseline_pass_count"]
        ),
        "predicted_fallback_plus_plan_oracle_count": int(
            planning["predicted_fallback_plus_plan_oracle_count"]
        ),
        "nonzero_first_action_count": int(planning["nonzero_first_action_count"]),
        "fault_injection_hold_count": int(detailed["fault_injection"]["pass_count"]),
        "safety_gate_passed": bool(detailed["safety_gate_passed"]),
        "authority_gate_passed": bool(detailed["authority_gate_passed"]),
        "real_tsc_executed": False,
        "plant_step_count": 0,
        "new_raw_count": 0,
        "controller_execution_authorized": False,
        "gate_a_qualified": False,
        "expert_data_allowed": False,
    }


def run_primary(ctx: Context) -> dict[str, Any]:
    if ctx.paths.stage.exists():
        raise ValueError("R8R44 primary requires a fresh stage directory")
    ctx.paths.stage.mkdir(parents=True)
    ctx.paths.analysis.mkdir()
    ctx.paths.model.mkdir()
    try:
        authentication = authenticate_sources(ctx)
        trajectories, context_meta, bank = r8r31.build_bank(ctx.source_ctx)
        detailed, artifact = compute_from_bank(
            ctx, authentication, trajectories, context_meta, bank
        )
        model_path = ctx.paths.model / "preflight_model.json"
        _write(model_path, artifact)
        _write(ctx.paths.analysis / "primary_detailed.json", detailed)
        summary = _summary(detailed, _sha(model_path))
        _write(ctx.paths.analysis / "primary_summary.json", summary)
        _write(
            ctx.paths.manifest,
            {
                "schema_version": SCHEMA_VERSION,
                "stage": STAGE,
                "identity": IDENTITY,
                "config_sha256": _sha(ctx.config_path),
                "design_sha256": str(ctx.cfg["design_document_sha256"]),
                "primary_summary_sha256": _sha(ctx.paths.analysis / "primary_summary.json"),
                "primary_detailed_sha256": _sha(ctx.paths.analysis / "primary_detailed.json"),
                "model_sha256": _sha(model_path),
                "zero_tsc_preflight": True,
            },
        )
        _write(
            ctx.paths.state,
            {
                "schema_version": SCHEMA_VERSION,
                "stage": STAGE,
                "phase_status": "offline_primary_ready_for_independent",
                "finished": False,
                "primary_completed": True,
                "independent_completed": False,
                "scientific_gate_passed": bool(summary["scientific_gate_passed"]),
                "route": summary["route"],
                "real_tsc_executed": False,
                "plant_step_count": 0,
                "new_raw_count": 0,
                "controller_execution_authorized": False,
            },
        )
        return summary
    except Exception as exc:
        route = (
            ctx.cfg["routes"]["source_blocked"]
            if isinstance(exc, SourceBlockedError)
            else ctx.cfg["routes"]["execution_fail"]
        )
        failure = {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "identity": IDENTITY,
            "phase": "offline_primary",
            "passed": False,
            "integrity_gate_passed": False,
            "scientific_gate_passed": False,
            "route": route,
            "failure_reason": repr(exc),
            "traceback": traceback.format_exc(),
            "real_tsc_executed": False,
            "plant_step_count": 0,
            "new_raw_count": 0,
        }
        _write(ctx.paths.analysis / "primary_failure.json", failure)
        _write(ctx.paths.state, {**failure, "phase_status": "offline_primary_execution_failed"})
        raise


AGREEMENT_FIELDS = (
    "primary_source_agreement",
    "primary_bank_agreement",
    "primary_model_agreement",
    "primary_prediction_agreement",
    "primary_tube_agreement",
    "primary_metric_agreement",
    "primary_planning_agreement",
    "primary_discrete_selection_agreement",
    "primary_route_agreement",
    "primary_outcome_agreement",
)
DIFFERENCE_FIELDS = (
    "maximum_bank_absolute_difference",
    "maximum_scaled_model_difference",
    "maximum_scaled_prediction_difference",
    "maximum_scaled_tube_difference",
    "maximum_scaled_metric_difference",
    "maximum_scaled_planning_difference",
)


def run_finalize(ctx: Context) -> dict[str, Any]:
    paths: dict[str, Path] = {
        "primary_summary": ctx.paths.analysis / "primary_summary.json",
        "primary_detailed": ctx.paths.analysis / "primary_detailed.json",
        "model": ctx.paths.model / "preflight_model.json",
    }
    independent_path = ctx.paths.analysis / "independent.json"
    failure_path = ctx.paths.analysis / "independent_failure.json"
    if any(not path.is_file() for path in (*paths.values(), ctx.paths.manifest, ctx.paths.state)):
        raise ValueError("R8R44 finalization evidence incomplete")
    if independent_path.is_file() == failure_path.is_file():
        raise ValueError("R8R44 finalization evidence ambiguous")
    summary = _read(paths["primary_summary"])
    detailed = _read(paths["primary_detailed"])
    selected_path = independent_path if independent_path.is_file() else failure_path
    selected_name = "independent" if independent_path.is_file() else "independent_failure"
    paths[selected_name] = selected_path
    independent = _read(selected_path)
    hashes = {name: _sha(path) for name, path in paths.items()}
    tolerance = float(ctx.cfg["model_contract"]["primary_independent_scaled_tolerance"])
    agreement = bool(
        independent.get("passed") is True
        and all(independent.get(field) is True for field in AGREEMENT_FIELDS)
        and all(float(independent.get(field, math.inf)) <= tolerance for field in DIFFERENCE_FIELDS)
        and independent.get("primary_summary_sha256") == hashes["primary_summary"]
        and independent.get("primary_detailed_sha256") == hashes["primary_detailed"]
        and independent.get("primary_model_sha256") == hashes["model"]
        and independent.get("route") == summary.get("route")
        and not bool(independent.get("real_tsc_executed"))
        and int(independent.get("plant_step_count", -1)) == 0
        and int(independent.get("new_raw_count", -1)) == 0
    )
    if independent_path.is_file() and not agreement:
        raise ValueError("R8R44 finalization independent disagreement")
    final_route = summary["route"] if agreement else ctx.cfg["routes"]["execution_fail"]
    compact = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "identity": IDENTITY,
        "audit_kind": "r8r44_compact_primary_independent_finalization" if agreement else "r8r44_compact_independent_failure_finalization",
        "passed": agreement,
        "integrity_gate_passed": agreement,
        "scientific_gate_passed": bool(summary["scientific_gate_passed"]) if agreement else False,
        "route": final_route,
        "primary_route": summary["route"],
        "source_file_sha256": hashes,
        "summary": summary,
        "source_model_binding": detailed["source_model_binding"],
        "source_model_evaluation": detailed["source_model_evaluation"],
        "planning_evaluation": detailed["planning_evaluation"],
        "fault_injection": detailed["fault_injection"],
        "independent_agreement": {field: independent.get(field) for field in AGREEMENT_FIELDS},
        "independent_maximum_scaled_difference": {
            field: independent.get(field) for field in DIFFERENCE_FIELDS
        },
        "real_tsc_executed": False,
        "plant_step_count": 0,
        "new_raw_count": 0,
        "controller_execution_authorized": False,
        "gate_a_qualified": False,
        "expert_data_allowed": False,
    }
    compact_path = ctx.paths.analysis / "compact_audit.json"
    _write(compact_path, compact)
    final = copy.deepcopy(compact)
    final["audit_kind"] = "r8r44_final_report"
    final["compact_audit_sha256"] = _sha(compact_path)
    final_path = ctx.paths.analysis / "final_report.json"
    _write(final_path, final)
    manifest = _read(ctx.paths.manifest)
    manifest.update(
        {
            f"{selected_name}_sha256": hashes[selected_name],
            "compact_audit_sha256": _sha(compact_path),
            "final_report_sha256": _sha(final_path),
            "final_route": final_route,
            "independent_completed": True,
            "independent_validation_passed": agreement,
        }
    )
    _write(ctx.paths.manifest, manifest)
    state = _read(ctx.paths.state)
    state.update(
        {
            "phase_status": "offline_preflight_final" if agreement else "offline_preflight_independent_validation_failed",
            "finished": True,
            "independent_completed": True,
            "independent_validation_passed": agreement,
            "scientific_gate_passed": bool(summary["scientific_gate_passed"]) if agreement else False,
            "primary_route": summary["route"],
            "route": final_route,
        }
    )
    _write(ctx.paths.state, state)
    return final


ARGUMENT_NAMES = (
    "config",
    "run-dir",
    "r8r43-run",
) + tuple(
    name for name in source_r8r43.ARGUMENT_NAMES if name not in {"config", "run-dir"}
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ARGUMENT_NAMES:
        parser.add_argument(f"--{name}", dest=name.replace("-", "_"), type=Path, required=True)
    parser.add_argument("--command", choices=("primary", "finalize"), default="primary")
    return parser


def main() -> None:
    args = _parser().parse_args()
    ctx = load_context(args)
    result = run_primary(ctx) if args.command == "primary" else run_finalize(ctx)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
