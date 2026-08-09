"""R8R33 uniformly supported rank-12 schedule-generalization preflight."""

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

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r32_rank_regularized_schedule_generalizing_feedback_preflight
    as r8r32,
)


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S24D1R14R8R33"
IDENTITY = "uniformly_supported_rank12_schedule_generalizing_feedback_preflight_v1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r33_uniformly_supported_rank12_schedule_generalizing_feedback_preflight"


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


_read = r8r32._read
_write = r8r32._write
_sha = r8r32._sha
_jsonable = r8r32._jsonable


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
    r8r32_ctx: Any
    r8r32_stage: Path


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
    source_config = (root / str(cfg["source_r8r32_config"])).resolve()
    bank, model, gates, offline, scope = (
        cfg["bank_contract"],
        cfg["model_contract"],
        cfg["model_gates"],
        cfg["offline_gate"],
        cfg["scientific_scope"],
    )
    invalid = (
        int(cfg.get("schema_version", -1)) != SCHEMA_VERSION
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("run_name") != RUN_NAME
        or not design.is_relative_to(root)
        or not source_config.is_relative_to(root)
        or _sha(design) != str(cfg["design_document_sha256"])
        or _sha(source_config) != str(cfg["source_r8r32_config_sha256"])
        or tuple(
            map(
                int,
                (
                    bank["trajectory_count"],
                    bank["physical_pair_count"],
                    bank["history_context_count"],
                    bank["schedule_count"],
                    bank["interval_record_count"],
                ),
            )
        )
        != (560, 8, 16, 35, 3360)
        or tuple(map(int, bank["decision_task_steps"])) != r8r32.r8r31.DECISIONS
        or tuple(map(int, bank["maximum_forecast_samples_by_interval"]))
        != r8r32.MAX_COUNTS
        or tuple(
            map(
                int,
                (
                    model["causal_base_dimension"],
                    model["pca_rank"],
                    model["action_dimension"],
                    model["transformed_dimension"],
                ),
            )
        )
        != (44, 12, 18, 78)
        or tuple(
            map(
                float,
                (
                    model["base_scale_floor"],
                    model["transformed_scale_floor"],
                    model["rank_relative_tolerance"],
                    model["ridge_penalty"],
                    model["reserve_multiplier"],
                ),
            )
        )
        != (1e-12, 1e-12, 1e-12, 0.01, 1.25)
        or tuple(map(float, model["physical_point_error_floors"]))
        != (0.015, 0.015, 3000.0, 0.05, 0.05)
        or not bool(model["whole_pair_exclusion"])
        or not bool(model["whole_schedule_exclusion"])
        or any(
            bool(model[key])
            for key in (
                "feature_selection_allowed",
                "hyperparameter_search_allowed",
                "tube_clipping_allowed",
                "outlier_deletion_allowed",
            )
        )
        or tuple(map(float, gates["maximum_point_error"]))
        != (0.015, 0.015, 3000.0, 0.05, 0.05)
        or tuple(map(float, gates["maximum_tube_half_width"]))
        != (0.025, 0.025, 5000.0, 0.08, 0.08)
        or float(gates["required_reserved_tube_containment_rate"]) != 1.0
        or tuple(
            map(
                int,
                (
                    offline["required_safe_search_context_count"],
                    offline["minimum_predicted_repaired_failed_baseline_count"],
                    offline["maximum_predicted_regressed_baseline_pass_count"],
                    offline["minimum_predicted_oracle_count"],
                    offline["minimum_nonzero_first_action_count"],
                    offline["required_fault_injection_count"],
                ),
            )
        )
        != (16, 1, 0, 7, 1, 6)
        or float(offline["primary_independent_absolute_tolerance"]) != 1e-12
        or not bool(scope["zero_new_tsc"])
        or any(
            bool(scope[key])
            for key in (
                "controller_execution_authorized",
                "gate_a_qualified",
                "expert_data_allowed",
                "bc_dagger_or_rl_allowed",
                "all_stage_trajectories_allowed_in_expert_dataset",
                "global_plant_reachability_claimed",
            )
        )
    )
    if invalid:
        raise ValueError("R8R33 frozen config changed")


def load_context(args: argparse.Namespace) -> Context:
    config_path = args.config.expanduser().resolve()
    cfg = _read(config_path)
    validate_config(cfg, project_root=_root())
    source_args = argparse.Namespace(**vars(args))
    source_args.config = (_root() / str(cfg["source_r8r32_config"])).resolve()
    source_args.run_dir = args.r8r32_run.expanduser().resolve()
    r8r32_ctx = r8r32.load_context(source_args)
    r8r32_stage = args.r8r32_run.expanduser().resolve() / str(
        cfg["source_r8r32"]["stage_directory"]
    )
    return Context(
        cfg=cfg,
        config_path=config_path,
        paths=_paths(args.run_dir),
        r8r32_ctx=r8r32_ctx,
        r8r32_stage=r8r32_stage,
    )


def authenticate_sources(ctx: Context) -> dict[str, Any]:
    transitive = r8r32.authenticate_sources(ctx.r8r32_ctx)
    expected = ctx.cfg["source_r8r32"]
    paths = {
        "primary_summary": ctx.r8r32_stage / "analysis/primary_summary.json",
        "primary_detailed": ctx.r8r32_stage / "analysis/primary_detailed.json",
        "model": ctx.r8r32_stage / "model/preflight_model.json",
        "independent": ctx.r8r32_stage / "analysis/independent.json",
        "compact_audit": ctx.r8r32_stage / "analysis/compact_audit.json",
        "final_report": ctx.r8r32_stage / "analysis/final_report.json",
        "stage_state": ctx.r8r32_stage / "stage_state.json",
        "stage_manifest": ctx.r8r32_stage / "stage_manifest.json",
    }
    hashes = {name: _sha(path) for name, path in paths.items()}
    if any(hashes[name] != str(expected[f"{name}_sha256"]) for name in hashes):
        raise ValueError("R8R33 R8R32 source hash changed")
    final = _read(paths["final_report"])
    state = _read(paths["stage_state"])
    independent = _read(paths["independent"])
    if (
        ctx.r8r32_stage.parent.name != str(expected["run_name"])
        or final.get("route") != str(expected["required_route"])
        or final.get("scientific_gate_passed") is not False
        or independent.get("passed") is not True
        or state.get("finished") is not True
        or state.get("independent_completed") is not True
        or bool(state.get("real_tsc_executed"))
        or int(state.get("plant_step_count", -1)) != 0
        or int(state.get("new_raw_count", -1)) != 0
    ):
        raise ValueError("R8R33 R8R32 source outcome changed")
    return {"r8r32": {"hashes": hashes, "transitive": transitive}, "passed": True}


def compute_from_bank(
    ctx: Context,
    authentication: Mapping[str, Any],
    trajectories: Sequence[Mapping[str, Any]],
    context_meta: Mapping[tuple[str, str], Mapping[str, Any]],
    bank: Mapping[str, Any],
    *,
    solver: str = "normal",
    fit_head_fn: Callable[..., dict[str, Any]] | None = None,
    rank_head_fn: Callable[..., dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    bridge = SimpleNamespace(cfg=ctx.cfg, source_ctx=ctx.r8r32_ctx.source_ctx)
    detailed, artifact = r8r32.compute_from_bank(
        bridge,
        authentication,
        trajectories,
        context_meta,
        bank,
        solver=solver,
        fit_head_fn=fit_head_fn,
        rank_head_fn=rank_head_fn,
    )
    detailed["stage"] = STAGE
    detailed["identity"] = IDENTITY
    artifact["stage"] = STAGE
    artifact["identity"] = IDENTITY
    return detailed, artifact


def _summary(detailed: Mapping[str, Any], model_sha: str) -> dict[str, Any]:
    summary = r8r32._summary(detailed, model_sha)
    summary["stage"] = STAGE
    summary["identity"] = IDENTITY
    return summary


def run_primary(ctx: Context) -> dict[str, Any]:
    if ctx.paths.stage.exists():
        raise ValueError("R8R33 primary requires a fresh stage directory")
    ctx.paths.stage.mkdir(parents=True)
    ctx.paths.analysis.mkdir()
    ctx.paths.model.mkdir()
    try:
        authentication = authenticate_sources(ctx)
        trajectories, context_meta, bank = r8r32.r8r31.build_bank(
            ctx.r8r32_ctx.source_ctx
        )
        detailed, artifact = compute_from_bank(
            ctx, authentication, trajectories, context_meta, bank
        )
        model_path = ctx.paths.model / "preflight_model.json"
        detailed_path = ctx.paths.analysis / "primary_detailed.json"
        summary_path = ctx.paths.analysis / "primary_summary.json"
        _write(model_path, artifact)
        _write(detailed_path, detailed)
        summary = _summary(detailed, _sha(model_path))
        _write(summary_path, summary)
        _write(
            ctx.paths.manifest,
            {
                "schema_version": SCHEMA_VERSION,
                "stage": STAGE,
                "identity": IDENTITY,
                "config_sha256": _sha(ctx.config_path),
                "design_sha256": str(ctx.cfg["design_document_sha256"]),
                "primary_summary_sha256": _sha(summary_path),
                "primary_detailed_sha256": _sha(detailed_path),
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
                "finished": not bool(summary["scientific_gate_passed"]),
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
        failure = {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "identity": IDENTITY,
            "phase": "offline_primary",
            "passed": False,
            "integrity_gate_passed": False,
            "scientific_gate_passed": False,
            "route": ctx.cfg["routes"]["execution_fail"],
            "failure_reason": repr(exc),
            "traceback": traceback.format_exc(),
            "real_tsc_executed": False,
            "plant_step_count": 0,
            "new_raw_count": 0,
        }
        _write(ctx.paths.analysis / "primary_failure.json", failure)
        _write(
            ctx.paths.state,
            {
                "schema_version": SCHEMA_VERSION,
                "stage": STAGE,
                "phase_status": "offline_primary_execution_failed",
                "finished": True,
                "primary_completed": False,
                "independent_completed": False,
                "scientific_gate_passed": False,
                "route": ctx.cfg["routes"]["execution_fail"],
                "real_tsc_executed": False,
                "plant_step_count": 0,
                "new_raw_count": 0,
            },
        )
        raise


def run_finalize(ctx: Context) -> dict[str, Any]:
    paths = {
        "primary_summary": ctx.paths.analysis / "primary_summary.json",
        "primary_detailed": ctx.paths.analysis / "primary_detailed.json",
        "model": ctx.paths.model / "preflight_model.json",
        "independent": ctx.paths.analysis / "independent.json",
    }
    if any(
        not path.is_file()
        for path in (*paths.values(), ctx.paths.manifest, ctx.paths.state)
    ):
        raise ValueError("R8R33 finalization evidence incomplete")
    summary = _read(paths["primary_summary"])
    detailed = _read(paths["primary_detailed"])
    independent = _read(paths["independent"])
    manifest = _read(ctx.paths.manifest)
    hashes = {name: _sha(path) for name, path in paths.items()}
    agreement_fields = (
        "primary_bank_agreement",
        "primary_model_agreement",
        "primary_outer_agreement",
        "primary_schedule_agreement",
        "primary_planning_agreement",
        "primary_route_agreement",
        "primary_outcome_agreement",
    )
    difference_fields = (
        "maximum_bank_absolute_difference",
        "maximum_model_absolute_difference",
        "maximum_outer_absolute_difference",
        "maximum_schedule_absolute_difference",
        "maximum_planning_absolute_difference",
    )
    tolerance = float(ctx.cfg["offline_gate"]["primary_independent_absolute_tolerance"])
    if (
        independent.get("passed") is not True
        or any(independent.get(field) is not True for field in agreement_fields)
        or any(
            float(independent.get(field, math.inf)) > tolerance
            for field in difference_fields
        )
        or independent.get("primary_summary_sha256") != hashes["primary_summary"]
        or independent.get("primary_detailed_sha256") != hashes["primary_detailed"]
        or independent.get("primary_model_sha256") != hashes["model"]
        or independent.get("route") != summary.get("route")
        or bool(independent.get("real_tsc_executed"))
        or int(independent.get("plant_step_count", -1)) != 0
        or int(independent.get("new_raw_count", -1)) != 0
    ):
        raise ValueError("R8R33 finalization independent disagreement")
    compact = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "identity": IDENTITY,
        "audit_kind": "r8r33_compact_primary_independent_finalization",
        "passed": True,
        "integrity_gate_passed": True,
        "scientific_gate_passed": bool(summary["scientific_gate_passed"]),
        "route": summary["route"],
        "source_file_sha256": hashes,
        "summary": summary,
        "representation_rank_audit": detailed["representation_rank_audit"],
        "outer_model_evaluation": detailed["outer_model_evaluation"],
        "schedule_jackknife": detailed["schedule_jackknife"],
        "combined_tube_maximum_physical_half_width": detailed[
            "combined_tube_maximum_physical_half_width"
        ],
        "combined_tube_cap_passed": detailed["combined_tube_cap_passed"],
        "planning_evaluation": detailed["planning_evaluation"],
        "fault_injection": detailed["fault_injection"],
        "independent_agreement": {
            field: independent[field] for field in agreement_fields
        },
        "independent_maximum_absolute_difference": {
            field: independent[field] for field in difference_fields
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
    final["audit_kind"] = "r8r33_final_report"
    final["compact_audit_sha256"] = _sha(compact_path)
    final_path = ctx.paths.analysis / "final_report.json"
    _write(final_path, final)
    manifest.update(
        {
            "independent_sha256": hashes["independent"],
            "compact_audit_sha256": _sha(compact_path),
            "final_report_sha256": _sha(final_path),
            "final_route": summary["route"],
            "independent_completed": True,
        }
    )
    _write(ctx.paths.manifest, manifest)
    state = _read(ctx.paths.state)
    state.update(
        {
            "phase_status": "offline_preflight_final",
            "finished": True,
            "primary_completed": True,
            "independent_completed": True,
            "scientific_gate_passed": bool(summary["scientific_gate_passed"]),
            "route": summary["route"],
            "real_tsc_executed": False,
            "plant_step_count": 0,
            "new_raw_count": 0,
            "controller_execution_authorized": False,
        }
    )
    _write(ctx.paths.state, state)
    return final


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "config",
        "run-dir",
        "r8r32-run",
        "r8r31-run",
        "r8r23-run",
        "r8r28-run",
        "r8r22-run",
        "r8r7-run",
        "r8r12-run",
        "r8r14-run",
        "r8r15-run",
        "r8r19-run",
        "r8r20-run",
        "r8r27-run",
        "r8-run",
        "r8r1-output",
        "r8r6-run",
        "source-d1r11-run",
        "source-r2-run",
        "source-r4-run",
        "source-r6-run",
        "source-s21-run",
        "source-s23r1-output",
        "source-s24-run",
        "source-d1r9-v1",
        "source-d1r9-v2",
        "source-d1r10-run",
        "source-d1r10-audit",
        "source-stage42r3b-run",
        "source-stage42r3c3-run",
        "source-stage42r3c3-bank-dir",
        "source-stage42r3c3t1-run",
        "source-stage42r3c3t1-audit-dir",
        "source-stage42r3c3t3-controller-bank",
        "q1-run",
        "q2-run",
        "q1-audit",
        "q2-audit",
        "r3b-server-audit",
        "r3b-snapshot-checks",
    ):
        parser.add_argument(
            f"--{name}", dest=name.replace("-", "_"), type=Path, required=True
        )
    parser.add_argument("--command", choices=("primary", "finalize"), default="primary")
    return parser


def main() -> None:
    args = _parser().parse_args()
    ctx = load_context(args)
    result = run_primary(ctx) if args.command == "primary" else run_finalize(ctx)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
