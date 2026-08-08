"""Frozen zero-TSC R8R27 point-versus-reserve authority discriminator."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r26_action_transition_supported_multiresolution_mpc_preflight
    as r8r26,
)


STAGE = "Stage4.2R3c3T13S24D1R14R8R27"
IDENTITY = "point_versus_reserve_authority_discriminator_v1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r27_point_versus_reserve_authority_discriminator"
LAYERS = ("point_only", "pair_tube", "combined_tube")


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
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


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
    source_ctx: Any
    source_stage: Path


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
    source = (root / str(cfg["source_r8r26_config"])).resolve()
    layer = cfg["layer_contract"]
    search = cfg["unchanged_search_contract"]
    formal = cfg["formal_contract"]
    gate = cfg["classification_gate"]
    if (
        int(cfg.get("schema_version", -1)) != 1
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("run_name") != RUN_NAME
        or not design.is_relative_to(root)
        or not source.is_relative_to(root)
        or _sha(design) != str(cfg["design_document_sha256"])
        or _sha(source) != str(cfg["source_r8r26_config_sha256"])
        or tuple(map(str, layer["ordered_layers"])) != LAYERS
        or layer.get("point_only_tube") != "exact_zero_with_source_interval_shapes"
        or layer.get("pair_tube_source") != "immutable_r8r25_all_eight_outer_jackknife_planning_tube"
        or layer.get("combined_tube_source") != "final_r8r26_componentwise_pair_schedule_maximum"
        or layer.get("pair_combined_elementwise_equality_required") is not True
        or layer.get("combined_r8r26_plan_reproduction_required") is not True
        or any(layer.get(key) is not False for key in (
            "tube_refit_allowed", "tube_rescale_allowed", "tube_clipping_allowed",
            "outcome_selected_tube_allowed",
        ))
        or tuple(map(int, search["decision_task_steps"])) != (10, 14, 18, 22)
        or tuple(map(int, (
            search["lattice_denominator"], search["maximum_coordinate_sum_units"],
            search["lattice_level_count"], search["coarse_level_count"],
            search["beam_width"], search["terminal_seed_count"],
            search["maximum_sweeps_per_step"],
        ))) != (16, 24, 325, 33, 256, 32, 16)
        or tuple(map(int, search["refinement_step_units"])) != (2, 1)
        or tuple(tuple(map(int, row)) for row in search["refinement_directions"])
        != ((1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1))
        or search.get("global_optimality_claimed") is not False
        or search.get("failed_plan_deployment_allowed") is not False
        or tuple(map(int, (
            formal["normal_arrival_deadline_step"], formal["normal_hold_through_step"],
            formal["weak_arrival_deadline_step"], formal["weak_hold_through_step"],
            formal["arrival_streak_steps"],
        ))) != (25, 35, 27, 37, 3)
        or tuple(map(float, (
            formal["position_tolerance_m"], formal["speed_tolerance_m_per_s"],
            formal["ip_tolerance_A"],
        ))) != (0.03, 0.1, 10000.0)
        or formal.get("arrival_deadline_expansion_allowed") is not False
        or tuple(map(int, (
            gate["required_safe_search_context_count_per_layer"],
            gate["minimum_point_only_repaired_failed_baseline_count_for_uncertainty_route"],
            gate["minimum_point_only_oracle_count_for_uncertainty_route"],
        ))) != (16, 1, 7)
        or float(gate["primary_independent_absolute_tolerance"]) != 1e-12
        or cfg.get("routes") != {
            "evidence_fail": "R8R27_INTEGRITY_FAIL_STOP",
            "uncertainty": "POINT_AUTHORITY_PRESENT_RESERVED_UNCERTAINTY_EXCITATION_REDESIGN_REQUIRED",
            "action_timing": "POINT_ACTION_TIMING_AUTHORITY_INSUFFICIENT_BROADER_CONTROLLER_REDESIGN_REQUIRED",
        }
        or cfg.get("zero_new_tsc") is not True
        or cfg.get("expert_data_allowed") is not False
        or cfg.get("gate_a_qualified") is not False
    ):
        raise ValueError("R8R27 frozen contract changed")


def load_context(args: argparse.Namespace) -> Context:
    config_path = args.config.expanduser().resolve()
    cfg = _read(config_path)
    validate_config(cfg, project_root=_root())
    source_args = copy.copy(args)
    source_args.config = (_root() / str(cfg["source_r8r26_config"])).resolve()
    source_args.run_dir = args.r8r26_run
    source_ctx = r8r26.load_context(source_args)
    source_stage = args.r8r26_run.expanduser().resolve() / str(
        cfg["source_r8r26"]["stage_directory"]
    )
    return Context(cfg, config_path, _paths(args.run_dir), source_ctx, source_stage)


def _plan_summaries(plans: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for plan in plans:
        selected = plan["selected_plan"]
        selected_summary = None
        if selected is not None:
            selected_summary = {
                key: selected[key]
                for key in (
                    "q_units", "q_values", "robust_formal_pass",
                    "worst_formal_margin_violation", "integrated_normalized_error",
                    "cumulative_normalized_action_movement",
                    "maximum_predicted_current_utilization",
                )
            }
            selected_summary["predicted_states_digest"] = _digest(selected["predicted_states"])
            selected_summary["reserved_tubes_digest"] = _digest(selected["reserved_tubes"])
        row = {
            key: plan[key]
            for key in (
                "pair_id", "history_member", "coarse_level_count", "beam_counts",
                "terminal_seed_count", "safe_search_complete", "robust_formal_plan_found",
                "causal_selected_mode", "search_counts", "evaluated_sequence_digest",
                "baseline_formal_pass_for_postselection_scoring",
                "hybrid_predicted_formal_pass",
            )
        }
        row["selected_plan"] = selected_summary
        output.append(row)
    return output


def _authenticate_source(ctx: Context) -> dict[str, Any]:
    expected = ctx.cfg["source_r8r26"]
    paths = {
        "primary_detailed": ctx.source_stage / "analysis/primary_detailed.json",
        "primary_summary": ctx.source_stage / "analysis/primary_summary.json",
        "independent": ctx.source_stage / "analysis/independent.json",
        "final_report": ctx.source_stage / "analysis/final_report.json",
        "model_evidence": ctx.source_stage / "model/preflight_evidence.json",
        "stage_manifest": ctx.source_stage / "stage_manifest.json",
        "stage_state": ctx.source_stage / "stage_state.json",
        "compact_audit": ctx.source_stage / "analysis/compact_audit.json",
    }
    hashes = {name: _sha(path) for name, path in paths.items()}
    if any(hashes[name] != str(expected[f"{name}_sha256"]) for name in paths):
        raise ValueError("R8R27 R8R26 source hash changed")
    primary = _read(paths["primary_detailed"])
    independent = _read(paths["independent"])
    final = _read(paths["final_report"])
    state = _read(paths["stage_state"])
    compact = _read(paths["compact_audit"])
    if (
        ctx.source_stage.parent.name != str(expected["run_name"])
        or primary.get("route") != str(expected["required_route"])
        or primary.get("model_gate_passed") is not True
        or primary.get("predicted_feasibility_gate_passed") is not False
        or primary.get("fresh_controller_sentinel_authorized") is not False
        or independent.get("passed") is not True
        or final.get("primary_independent_agreement") is not True
        or final.get("passed") is not False
        or state.get("finished") is not True
        or state.get("real_tsc_executed") is not False
        or int(state.get("plant_step_count", -1)) != 0
        or int(state.get("new_raw_count", -1)) != 0
        or compact.get("passed") is not True
        or compact.get("scientific_gate_passed") is not False
        or _digest(compact["plan_summaries"]) != str(expected["plan_summary_digest"])
        or _digest(compact["transition_hull_evidence"])
        != str(expected["transition_hull_evidence_digest"])
        or _digest(compact["coarse_level_units"]) != str(expected["coarse_level_digest"])
        or _digest([row["evaluated_sequence_digest"] for row in compact["plan_summaries"]])
        != str(expected["evaluated_token_digest_list_digest"])
    ):
        raise ValueError("R8R27 R8R26 source outcome changed")
    transitive = r8r26._authenticate_source(ctx.source_ctx)
    if transitive.get("passed") is not True:
        raise ValueError("R8R27 transitive source authentication failed")
    return {"hashes": hashes, "route": str(final["route"]), "transitive": transitive, "passed": True}


def _planning_inputs(ctx: Context) -> tuple[Any, ...]:
    source_r23_ctx = ctx.source_ctx.source_ctx.source_ctx.source_ctx
    trajectories, context_meta = r8r26.r8r23.build_bank(source_r23_ctx)
    bank = r8r26.r8r23._bank_evidence(trajectories)
    expected = ctx.cfg["source_r8r26"]
    schedules = sorted({str(row["schedule_id"]) for row in trajectories})
    if (
        bank["feature_digest"] != str(expected["feature_digest"])
        or bank["target_digest"] != str(expected["target_digest"])
        or len(schedules) != int(expected["schedule_count"])
    ):
        raise ValueError("R8R27 source bank changed")
    source_model = _read(ctx.source_ctx.source_stage / "model/outer_fold_models.json")
    model = r8r26._deserialize_model(source_model["planning_evidence"]["model"])
    source_evidence = _read(ctx.source_stage / "model/preflight_evidence.json")
    pair = [np.asarray(value, dtype=float) for value in source_evidence["pair_tube"]]
    combined = [np.asarray(value, dtype=float) for value in source_evidence["combined_tube"]]
    zero = [np.zeros_like(value) for value in combined]
    equality = max(
        float(np.max(np.abs(left - right))) for left, right in zip(pair, combined)
    )
    if (
        _digest(r8r26.r8r23._model_serializable(model))
        != str(expected["planning_model_digest"])
        or _digest([value.tolist() for value in pair]) != str(expected["pair_tube_digest"])
        or _digest([value.tolist() for value in combined]) != str(expected["combined_tube_digest"])
        or equality != 0.0
    ):
        raise ValueError("R8R27 source model/tube changed")
    support = r8r26.r8r25._planning_support(trajectories, ctx.source_ctx.source_ctx.cfg)
    hulls = r8r26._transition_hulls(trajectories, ctx.source_ctx.cfg)
    hull_evidence = [
        {
            "interval": int(hull["interval"]),
            "observed_transition_count": int(hull["observed_transition_count"]),
            "affine_rank": int(hull["affine_rank"]),
            "singular_values": np.asarray(hull["singular_values"]).tolist(),
            "transition_digest": str(hull["digest"]),
            "hull_equation_digest": _digest(np.asarray(hull["equations"]).tolist()),
        }
        for hull in hulls
    ]
    if (
        _digest(hull_evidence) != str(expected["transition_hull_evidence_digest"])
        or _digest([list(value) for value in r8r26._coarse_units(ctx.source_ctx)])
        != str(expected["coarse_level_digest"])
    ):
        raise ValueError("R8R27 source hull/coarse evidence changed")
    return trajectories, context_meta, bank, schedules, model, zero, pair, combined, support, hulls, hull_evidence


def _layer_result(
    ctx: Context,
    model: Mapping[str, Any],
    tube: Sequence[np.ndarray],
    support: Mapping[str, Any],
    hulls: Sequence[Mapping[str, Any]],
    context_meta: Mapping[tuple[str, str], Mapping[str, Any]],
) -> dict[str, Any]:
    return r8r26._planning_evaluation(
        ctx.source_ctx, model, tube, support, hulls, context_meta
    )


def _point_authority_present(point: Mapping[str, Any], cfg: Mapping[str, Any]) -> bool:
    gate = cfg["classification_gate"]
    return bool(
        int(point["predicted_repaired_failed_baseline_count"])
        >= int(gate["minimum_point_only_repaired_failed_baseline_count_for_uncertainty_route"])
        and int(point["predicted_baseline_fallback_plus_plan_oracle_count"])
        >= int(gate["minimum_point_only_oracle_count_for_uncertainty_route"])
    )


def compute(ctx: Context) -> tuple[dict[str, Any], dict[str, Any]]:
    authentication = _authenticate_source(ctx)
    (
        trajectories, context_meta, bank, schedules, model, zero, pair, combined,
        support, hulls, hull_evidence,
    ) = _planning_inputs(ctx)
    tubes = {"point_only": zero, "pair_tube": pair, "combined_tube": combined}
    results = {
        layer: _layer_result(ctx, model, tubes[layer], support, hulls, context_meta)
        for layer in LAYERS
    }
    source_primary = _read(ctx.source_stage / "analysis/primary_detailed.json")
    combined_difference = r8r26.r8r24._maximum_difference(
        source_primary["planning_evaluation"], results["combined_tube"]
    )
    pair_combined_difference = r8r26.r8r24._maximum_difference(
        results["pair_tube"], results["combined_tube"]
    )
    gate = ctx.cfg["classification_gate"]
    safe = all(
        int(results[layer]["safe_search_context_count"])
        == int(gate["required_safe_search_context_count_per_layer"])
        for layer in LAYERS
    )
    reproduction = bool(
        combined_difference <= 1e-12 and pair_combined_difference <= 1e-12
    )
    integrity = bool(safe and reproduction)
    if not integrity:
        raise ValueError("R8R27 source search reproduction failed")
    point = results["point_only"]
    uncertainty = _point_authority_present(point, ctx.cfg)
    route = str(ctx.cfg["routes"]["uncertainty" if uncertainty else "action_timing"])
    detailed = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "source_authentication": authentication,
        "bank_evidence": {**bank, "schedule_count": len(schedules), "schedule_ids": schedules},
        "planning_model_digest": _digest(r8r26.r8r23._model_serializable(model)),
        "layer_tube_digests": {
            layer: _digest([value.tolist() for value in tubes[layer]]) for layer in LAYERS
        },
        "pair_combined_elementwise_maximum_absolute_difference": max(
            float(np.max(np.abs(left - right))) for left, right in zip(pair, combined)
        ),
        "transition_hull_evidence": hull_evidence,
        "layer_results": results,
        "maximum_combined_source_plan_absolute_difference": combined_difference,
        "maximum_pair_combined_plan_absolute_difference": pair_combined_difference,
        "all_layer_safe_search_gate_passed": safe,
        "source_reproduction_gate_passed": reproduction,
        "classification_completed": True,
        "point_authority_present": uncertainty,
        "route": route,
        "fresh_controller_sentinel_authorized": False,
        "scientific_gate_passed": False,
        "real_tsc_executed": False,
        "plant_step_count": 0,
        "new_raw_count": 0,
        "allowed_in_expert_dataset": False,
        "gate_a_qualified": False,
    }
    evidence = {
        "schema_version": 1,
        "stage": STAGE,
        "planning_model_digest": detailed["planning_model_digest"],
        "layer_tubes": {layer: [value.tolist() for value in tubes[layer]] for layer in LAYERS},
        "transition_hulls": [
            {
                "interval": int(hull["interval"]),
                "points": np.asarray(hull["points"]).tolist(),
                "origin": np.asarray(hull["origin"]).tolist(),
                "basis": np.asarray(hull["basis"]).tolist(),
                "equations": np.asarray(hull["equations"]).tolist(),
            }
            for hull in hulls
        ],
        "planning_support": {
            key: support[key]
            for key in (
                "training_nearest_neighbor_maxima", "thresholds",
                "training_origin_count_by_interval",
            )
        },
        "layer_plan_summary_digests": {
            layer: _digest(_plan_summaries(results[layer]["plans"])) for layer in LAYERS
        },
    }
    return detailed, evidence


def _summary(detailed: Mapping[str, Any], evidence_sha: str) -> dict[str, Any]:
    layers = detailed["layer_results"]
    return {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "source_route": detailed["source_authentication"]["route"],
        "trajectory_count": detailed["bank_evidence"]["trajectory_count"],
        "schedule_count": detailed["bank_evidence"]["schedule_count"],
        "origin_row_count": detailed["bank_evidence"]["origin_row_count"],
        "forecast_point_count": detailed["bank_evidence"]["forecast_point_count"],
        "feature_digest": detailed["bank_evidence"]["feature_digest"],
        "target_digest": detailed["bank_evidence"]["target_digest"],
        "evidence_sha256": evidence_sha,
        "layer_results": {
            layer: {
                key: layers[layer][key]
                for key in (
                    "safe_search_context_count", "robust_formal_plan_context_count",
                    "predicted_repaired_failed_baseline_count",
                    "predicted_regressed_baseline_pass_count",
                    "predicted_baseline_fallback_plus_plan_oracle_count", "passed",
                )
            }
            for layer in LAYERS
        },
        "maximum_combined_source_plan_absolute_difference": detailed["maximum_combined_source_plan_absolute_difference"],
        "maximum_pair_combined_plan_absolute_difference": detailed["maximum_pair_combined_plan_absolute_difference"],
        "classification_completed": detailed["classification_completed"],
        "point_authority_present": detailed["point_authority_present"],
        "route": detailed["route"],
        "fresh_controller_sentinel_authorized": False,
        "scientific_gate_passed": False,
        "real_tsc_executed": False,
        "plant_step_count": 0,
        "new_raw_count": 0,
        "gate_a_qualified": False,
    }


def run_primary(ctx: Context) -> dict[str, Any]:
    if ctx.paths.stage.exists() and any(ctx.paths.stage.iterdir()):
        raise ValueError("R8R27 primary requires an empty stage directory")
    ctx.paths.analysis.mkdir(parents=True, exist_ok=True)
    ctx.paths.model.mkdir(parents=True, exist_ok=True)
    detailed, evidence = compute(ctx)
    evidence_path = ctx.paths.model / "discriminator_evidence.json"
    _write(evidence_path, evidence)
    detailed["evidence_sha256"] = _sha(evidence_path)
    detailed_path = ctx.paths.analysis / "primary_detailed.json"
    summary_path = ctx.paths.analysis / "primary_summary.json"
    _write(detailed_path, detailed)
    _write(summary_path, _summary(detailed, detailed["evidence_sha256"]))
    _write(
        ctx.paths.manifest,
        {
            "schema_version": 1,
            "stage": STAGE,
            "identity": IDENTITY,
            "config_path": str(ctx.config_path),
            "config_sha256": _sha(ctx.config_path),
            "design_document_sha256": ctx.cfg["design_document_sha256"],
            "source_r8r26_run": str(ctx.source_stage.parent),
            "source_r8r26_stage_state_sha256": ctx.cfg["source_r8r26"]["stage_state_sha256"],
            "primary_detailed_sha256": _sha(detailed_path),
            "primary_summary_sha256": _sha(summary_path),
            "evidence_sha256": detailed["evidence_sha256"],
            "zero_new_tsc": True,
            "all_source_trajectories_allowed_in_expert_dataset": False,
        },
    )
    _write(
        ctx.paths.state,
        {
            "schema_version": 1,
            "stage": STAGE,
            "phase_status": "primary_complete",
            "finished": False,
            "route": detailed["route"],
            "real_tsc_executed": False,
            "plant_step_count": 0,
            "new_raw_count": 0,
            "primary_detailed_sha256": _sha(detailed_path),
            "primary_summary_sha256": _sha(summary_path),
        },
    )
    return _read(summary_path)


def postprocess(ctx: Context) -> dict[str, Any]:
    primary_path = ctx.paths.analysis / "primary_detailed.json"
    summary_path = ctx.paths.analysis / "primary_summary.json"
    independent_path = ctx.paths.analysis / "independent.json"
    primary = _read(primary_path)
    summary = _read(summary_path)
    independent = _read(independent_path)
    required = (
        "primary_bank_agreement", "primary_model_tube_agreement",
        "primary_hull_agreement", "primary_layer_plan_agreement",
        "primary_reproduction_agreement", "primary_route_agreement",
        "primary_outcome_agreement",
    )
    if independent.get("passed") is not True or any(independent.get(key) is not True for key in required):
        raise ValueError("R8R27 independent agreement incomplete")
    final = {
        **summary,
        "primary_detailed_sha256": _sha(primary_path),
        "primary_summary_sha256": _sha(summary_path),
        "independent_sha256": _sha(independent_path),
        "primary_independent_agreement": True,
        "passed": True,
    }
    final_path = ctx.paths.analysis / "final_report.json"
    _write(final_path, final)
    _write(
        ctx.paths.state,
        {
            "schema_version": 1,
            "stage": STAGE,
            "phase_status": "complete",
            "finished": True,
            "verdict": {"passed": True, "route": str(final["route"])},
            "stop_reason": "point_versus_reserve_classification_complete",
            "real_tsc_executed": False,
            "plant_step_count": 0,
            "new_raw_count": 0,
            "primary_detailed_sha256": _sha(primary_path),
            "primary_summary_sha256": _sha(summary_path),
            "independent_sha256": _sha(independent_path),
            "final_report_sha256": _sha(final_path),
        },
    )
    return final


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--r8r27-command", choices=("primary", "postprocess"), required=True)
    parser.add_argument("--r8r26-run", type=Path, required=True)
    parser.add_argument("--r8r25-run", type=Path, required=True)
    for name in (
        "r8r24_run", "r8r23_run", "r8r22_run", "r8r7_run", "r8r12_run", "r8r14_run",
        "r8r15_run", "r8r19_run", "r8r20_run", "r8_run", "r8r1_output", "r8r6_run",
        "source_d1r11_run", "source_r2_run", "source_r4_run", "source_r6_run",
        "source_s21_run", "source_s23r1_output", "source_s24_run", "source_d1r9_v1",
        "source_d1r9_v2", "source_d1r10_run", "source_d1r10_audit", "source_stage42r3b_run",
        "source_stage42r3c3_run", "source_stage42r3c3_bank_dir", "source_stage42r3c3t1_run",
        "source_stage42r3c3t1_audit_dir", "source_stage42r3c3t3_controller_bank",
        "q1_run", "q2_run", "q1_audit", "q2_audit", "r3b_server_audit", "r3b_snapshot_checks",
    ):
        parser.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    ctx = load_context(args)
    result = run_primary(ctx) if args.r8r27_command == "primary" else postprocess(ctx)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
