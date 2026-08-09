"""R8R32 rank-regularized schedule-generalizing zero-TSC preflight."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r31_aligned_explicit_four_coordinate_feedback_sentinel
    as r8r31,
)


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S24D1R14R8R32"
IDENTITY = "rank_regularized_schedule_generalizing_feedback_preflight_v1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r32_rank_regularized_schedule_generalizing_feedback_preflight"
FACTORS = r8r31.OUTPUT_FACTORS
MAX_COUNTS = r8r31.MAX_COUNTS


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


def _jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            _jsonable(value),
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
    source_config = (root / str(cfg["source_r8r31_config"])).resolve()
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
        or _sha(source_config) != str(cfg["source_r8r31_config_sha256"])
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
        or tuple(map(int, bank["decision_task_steps"])) != r8r31.DECISIONS
        or tuple(map(int, bank["maximum_forecast_samples_by_interval"])) != MAX_COUNTS
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
        != (44, 32, 18, 178)
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
        raise ValueError("R8R32 frozen config changed")


def load_context(args: argparse.Namespace) -> Context:
    config_path = args.config.expanduser().resolve()
    cfg = _read(config_path)
    validate_config(cfg, project_root=_root())
    source_args = argparse.Namespace(**vars(args))
    source_args.config = (_root() / str(cfg["source_r8r31_config"])).resolve()
    source_args.run_dir = args.r8r31_run.expanduser().resolve()
    source_ctx = r8r31.load_context(source_args)
    source_stage = args.r8r31_run.expanduser().resolve() / str(
        cfg["source_r8r31"]["stage_directory"]
    )
    return Context(
        cfg=cfg,
        config_path=config_path,
        paths=_paths(args.run_dir),
        source_ctx=source_ctx,
        source_stage=source_stage,
    )


def authenticate_sources(ctx: Context) -> dict[str, Any]:
    transitive = r8r31.authenticate_sources(ctx.source_ctx)
    expected = ctx.cfg["source_r8r31"]
    paths = {
        "primary_summary": ctx.source_stage / "analysis/primary_summary.json",
        "primary_detailed": ctx.source_stage / "analysis/primary_detailed.json",
        "model": ctx.source_stage / "model/preflight_model.json",
        "independent": ctx.source_stage / "analysis/independent.json",
        "compact_audit": ctx.source_stage / "analysis/compact_audit.json",
        "final_report": ctx.source_stage / "analysis/final_report.json",
        "stage_state": ctx.source_stage / "stage_state.json",
        "stage_manifest": ctx.source_stage / "stage_manifest.json",
    }
    hashes = {name: _sha(path) for name, path in paths.items()}
    if any(hashes[name] != str(expected[f"{name}_sha256"]) for name in hashes):
        raise ValueError("R8R32 R8R31 source hash changed")
    final, state, independent = (
        _read(paths["final_report"]),
        _read(paths["stage_state"]),
        _read(paths["independent"]),
    )
    if (
        ctx.source_stage.parent.name != str(expected["run_name"])
        or final.get("route") != str(expected["required_route"])
        or final.get("scientific_gate_passed") is not False
        or independent.get("passed") is not True
        or state.get("finished") is not True
        or state.get("independent_completed") is not True
        or state.get("real_tsc_executed") is not False
        or int(state.get("plant_step_count", -1)) != 0
        or int(state.get("new_raw_count", -1)) != 0
    ):
        raise ValueError("R8R32 R8R31 source outcome changed")
    return {"r8r31": {"hashes": hashes, "transitive": transitive}, "passed": True}


def _action18(row: Mapping[str, Any]) -> np.ndarray:
    value = np.asarray(row["expanded"], dtype=float).reshape(238)[44:62]
    if value.shape != (18,) or not np.all(np.isfinite(value)):
        raise ValueError("R8R32 action18 invalid")
    return value


def _canonical_loadings(z: np.ndarray, cfg: Mapping[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    _, singular, vh = np.linalg.svd(z, full_matrices=False)
    tolerance = float(cfg["model_contract"]["rank_relative_tolerance"])
    rank = int(np.count_nonzero(singular > tolerance * singular[0])) if singular[0] > 0 else 0
    requested = int(cfg["model_contract"]["pca_rank"])
    if rank < requested:
        raise ValueError("R8R32 fold-local base rank below 32")
    loadings = vh[:requested].T.copy()
    for column in range(requested):
        pivot = int(np.argmax(np.abs(loadings[:, column])))
        if loadings[pivot, column] < 0:
            loadings[:, column] *= -1.0
    return loadings, singular


def _rank_head(
    rows: Sequence[Mapping[str, Any]],
    *,
    offset: int,
    cfg: Mapping[str, Any],
) -> dict[str, Any]:
    current = [row for row in rows if len(row["targets"]) > offset]
    base = np.asarray([row["feature"] for row in current], dtype=float).reshape((-1, 44))
    base_mean = np.mean(base, axis=0)
    base_scale = np.maximum(
        np.sqrt(np.mean((base - base_mean) ** 2, axis=0)),
        float(cfg["model_contract"]["base_scale_floor"]),
    )
    standardized = (base - base_mean) / base_scale
    singular = np.linalg.svd(standardized, compute_uv=False)
    tolerance = float(cfg["model_contract"]["rank_relative_tolerance"])
    numerical_rank = (
        int(np.count_nonzero(singular > tolerance * singular[0]))
        if singular[0] > 0.0
        else 0
    )
    requested = int(cfg["model_contract"]["pca_rank"])
    retained = float(singular[requested - 1]) if len(singular) >= requested else 0.0
    leading = float(singular[0]) if len(singular) else 0.0
    return {
        "sample_offset": offset,
        "training_row_count": len(current),
        "numerical_rank": numerical_rank,
        "leading_singular_value": leading,
        "retained_rank_singular_value": retained,
        "retained_rank_relative_singular_value": retained / leading if leading else 0.0,
        "passed": numerical_rank >= requested,
    }


def representation_rank_audit(
    trajectories: Sequence[Mapping[str, Any]],
    cfg: Mapping[str, Any],
    *,
    rank_head_fn: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    head_fn = _rank_head if rank_head_fn is None else rank_head_fn
    families = []
    definitions = (
        (
            "whole_physical_pair",
            sorted({str(row["pair_id"]) for row in trajectories}),
            lambda row, held: row["pair_id"] != held,
        ),
        (
            "whole_schedule",
            sorted({str(row["schedule_id"]) for row in trajectories}),
            lambda row, held: row["schedule_id"] != held,
        ),
    )
    for family, held_values, selected in definitions:
        rows = []
        for held in held_values:
            selected_trajectories = [
                row for row in trajectories if selected(row, held)
            ]
            for interval in range(6):
                interval_rows = [
                    row["intervals"][interval] for row in selected_trajectories
                ]
                if not interval_rows:
                    raise ValueError("R8R32 rank audit selection empty")
                for offset in range(max(len(row["targets"]) for row in interval_rows)):
                    result = head_fn(interval_rows, offset=offset, cfg=cfg)
                    rows.append(
                        {
                            "held_out": held,
                            "interval": interval,
                            **result,
                        }
                    )
        families.append(
            {
                "family": family,
                "fold_count": len(held_values),
                "head_count": len(rows),
                "pass_count": sum(bool(row["passed"]) for row in rows),
                "failed_head_count": sum(not bool(row["passed"]) for row in rows),
                "minimum_numerical_rank": min(int(row["numerical_rank"]) for row in rows),
                "rows": rows,
                "passed": all(bool(row["passed"]) for row in rows),
            }
        )
    failed = sum(int(row["failed_head_count"]) for row in families)
    return {
        "requested_rank": int(cfg["model_contract"]["pca_rank"]),
        "family_count": len(families),
        "head_count": sum(int(row["head_count"]) for row in families),
        "pass_count": sum(int(row["pass_count"]) for row in families),
        "failed_head_count": failed,
        "minimum_numerical_rank": min(
            int(row["minimum_numerical_rank"]) for row in families
        ),
        "families": families,
        "passed": failed == 0,
    }


def _expanded_to_transformed_map(
    base_mean: np.ndarray, base_scale: np.ndarray, loadings: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    rank = loadings.shape[1]
    matrix = np.zeros((238, rank * 5 + 18), dtype=float)
    constant = np.zeros(rank * 5 + 18, dtype=float)
    base_map = loadings / base_scale[:, None]
    score_constant = -(base_mean / base_scale) @ loadings
    matrix[:44, :rank] = base_map
    constant[:rank] = score_constant
    matrix[44:62, rank : rank + 18] = np.eye(18)
    for coordinate in range(4):
        start = rank + 18 + coordinate * rank
        matrix[62 + 44 * coordinate : 62 + 44 * (coordinate + 1), start : start + rank] = base_map
        matrix[44 + coordinate, start : start + rank] = score_constant
    return matrix, constant


def fit_head(
    rows: Sequence[Mapping[str, Any]],
    *,
    offset: int,
    cfg: Mapping[str, Any],
    solver: str = "normal",
) -> dict[str, Any]:
    current = [row for row in rows if len(row["targets"]) > offset]
    base = np.asarray([row["feature"] for row in current], dtype=float)
    action = np.asarray([_action18(row) for row in current], dtype=float)
    q = np.asarray([row["q"] for row in current], dtype=float)
    target = np.asarray([row["targets"][offset] for row in current], dtype=float)
    base_mean = np.mean(base, axis=0)
    base_scale = np.maximum(
        np.sqrt(np.mean((base - base_mean) ** 2, axis=0)),
        float(cfg["model_contract"]["base_scale_floor"]),
    )
    z = (base - base_mean) / base_scale
    loadings, singular = _canonical_loadings(z, cfg)
    scores = z @ loadings
    transformed = np.concatenate(
        (scores, action, *(scores * q[:, coordinate : coordinate + 1] for coordinate in range(4))),
        axis=1,
    )
    if transformed.shape[1] != int(cfg["model_contract"]["transformed_dimension"]):
        raise ValueError("R8R32 transformed feature dimension changed")
    transformed_mean = np.mean(transformed, axis=0)
    transformed_scale = np.maximum(
        np.sqrt(np.mean((transformed - transformed_mean) ** 2, axis=0)),
        float(cfg["model_contract"]["transformed_scale_floor"]),
    )
    x = (transformed - transformed_mean) / transformed_scale
    x_mean, y_mean = np.mean(x, axis=0), np.mean(target, axis=0)
    centered_x, centered_y = x - x_mean, target - y_mean
    ridge = float(cfg["model_contract"]["ridge_penalty"])
    dimension = x.shape[1]
    if solver == "normal":
        beta = np.linalg.solve(
            centered_x.T @ centered_x + ridge * np.eye(dimension),
            centered_x.T @ centered_y,
        )
    elif solver == "augmented_lstsq":
        design = np.vstack((centered_x, math.sqrt(ridge) * np.eye(dimension)))
        response = np.vstack((centered_y, np.zeros((dimension, 5))))
        beta = np.linalg.lstsq(design, response, rcond=None)[0]
    else:
        raise ValueError(f"unknown R8R32 solver {solver}")
    transformed_intercept = y_mean - x_mean @ beta
    affine_map, affine_constant = _expanded_to_transformed_map(
        base_mean, base_scale, loadings
    )
    scaled_beta = beta / transformed_scale[:, None]
    coefficients = affine_map @ scaled_beta
    intercept = transformed_intercept + (
        (affine_constant - transformed_mean) / transformed_scale
    ) @ beta
    if (
        coefficients.shape != (238, 5)
        or intercept.shape != (5,)
        or not np.all(np.isfinite(coefficients))
        or not np.all(np.isfinite(intercept))
    ):
        raise ValueError("R8R32 ridge head invalid")
    return {
        "sample_offset": offset,
        "training_row_count": len(current),
        "base_mean": base_mean,
        "base_scale": base_scale,
        "base_loadings": loadings,
        "base_singular_values": singular,
        "transformed_mean": transformed_mean,
        "transformed_scale": transformed_scale,
        "transformed_coefficients": beta,
        "intercept": intercept,
        "coefficients": coefficients,
    }


def fit_model(
    trajectories: Sequence[Mapping[str, Any]],
    selected: Callable[[Mapping[str, Any]], bool],
    cfg: Mapping[str, Any],
    *,
    solver: str = "normal",
    fit_head_fn: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    head_fn = fit_head if fit_head_fn is None else fit_head_fn
    intervals = []
    for interval in range(6):
        rows = [row["intervals"][interval] for row in trajectories if selected(row)]
        if not rows:
            raise ValueError("R8R32 fit selection empty")
        offsets = [
            head_fn(rows, offset=offset, cfg=cfg, solver=solver)
            for offset in range(max(len(row["targets"]) for row in rows))
        ]
        intervals.append({"interval": interval, "offsets": offsets})
    rank = int(cfg["model_contract"]["pca_rank"])
    return {
        "model_kind": f"rank_regularized_pca{rank}_ridge_0p01",
        "intervals": intervals,
    }


def predict(model: Mapping[str, Any], row: Mapping[str, Any]) -> np.ndarray:
    return r8r31.predict(model, row)


def _residuals(
    model: Mapping[str, Any], trajectories: Sequence[Mapping[str, Any]]
) -> tuple[list[list[list[np.ndarray]]], dict[str, Any]]:
    groups: list[list[list[np.ndarray]]] = [[[] for _ in range(count)] for count in MAX_COUNTS]
    serial = []
    for trajectory in trajectories:
        rows = []
        for interval, row in enumerate(trajectory["intervals"]):
            residual = np.abs(np.asarray(row["targets"]) - predict(model, row))
            rows.append(residual.tolist())
            for offset, value in enumerate(residual):
                groups[interval][offset].append(value)
        serial.append({"trajectory_id": trajectory["trajectory_id"], "absolute_residuals": rows})
    return groups, {"residual_digest": _digest(serial)}


def outer_model_evaluation(
    trajectories: Sequence[Mapping[str, Any]],
    cfg: Mapping[str, Any],
    source_cfg: Mapping[str, Any],
    *,
    solver: str = "normal",
    fit_head_fn: Callable[..., dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    pairs = sorted({str(row["pair_id"]) for row in trajectories})
    folds = []
    for held_pair in pairs:
        training = [pair for pair in pairs if pair != held_pair]
        model = fit_model(
            trajectories,
            lambda row, allowed=set(training): row["pair_id"] in allowed,
            cfg,
            solver=solver,
            fit_head_fn=fit_head_fn,
        )
        held = [row for row in trajectories if row["pair_id"] == held_pair]
        groups, evidence = _residuals(model, held)
        folds.append(
            {
                "held_pair": held_pair,
                "training_pairs": training,
                "model": model,
                "model_digest": _digest(model),
                "residual_groups": groups,
                "residual_digest": evidence["residual_digest"],
                "support": r8r31._support_fold(
                    trajectories,
                    training,
                    held_pair,
                    float(source_cfg["model_contract"]["support_threshold_multiplier"]),
                ),
            }
        )
    contained = total = 0
    maximum_error = np.zeros(5)
    maximum_tube = np.zeros(5)
    fold_rows = []
    for fold in folds:
        tube, tube_evidence = r8r31._tube_from_fold_groups(
            folds, lambda row, held=fold["held_pair"]: row["held_pair"] != held, cfg
        )
        fold_contained = fold_total = 0
        fold_error = np.zeros(5)
        for interval, offsets in enumerate(fold["residual_groups"]):
            for offset, values in enumerate(offsets):
                residual = np.asarray(values).reshape((-1, 5))
                fold_contained += int(np.count_nonzero(residual <= tube[interval][offset] + 1e-15))
                fold_total += residual.size
                if len(residual):
                    fold_error = np.maximum(fold_error, np.max(residual, axis=0))
        maximum_error = np.maximum(maximum_error, fold_error * FACTORS)
        maximum_tube = np.maximum(
            maximum_tube, np.max(np.concatenate(tube), axis=0) * FACTORS
        )
        contained += fold_contained
        total += fold_total
        fold["tube"] = tube
        fold_rows.append(
            {
                "held_pair": fold["held_pair"],
                "model_digest": fold["model_digest"],
                "residual_digest": fold["residual_digest"],
                "maximum_physical_error": (fold_error * FACTORS).tolist(),
                "contained_count": fold_contained,
                "component_count": fold_total,
                "support": fold["support"],
                "tube_evidence": tube_evidence,
            }
        )
    gates = cfg["model_gates"]
    rate = contained / total
    passed = bool(
        np.all(maximum_error <= np.asarray(gates["maximum_point_error"]) + 1e-15)
        and np.all(maximum_tube <= np.asarray(gates["maximum_tube_half_width"]) + 1e-15)
        and rate >= float(gates["required_reserved_tube_containment_rate"]) - 1e-15
        and all(fold["support"]["passed"] for fold in folds)
    )
    return folds, {
        "maximum_absolute_physical_error": maximum_error.tolist(),
        "maximum_reserved_physical_tube_half_width": maximum_tube.tolist(),
        "reserved_contained_count": contained,
        "reserved_component_count": total,
        "reserved_containment_rate": rate,
        "state_support_pass_count": sum(fold["support"]["passed"] for fold in folds),
        "fold_rows": fold_rows,
        "passed": passed,
    }


def schedule_jackknife(
    trajectories: Sequence[Mapping[str, Any]],
    cfg: Mapping[str, Any],
    *,
    solver: str = "normal",
    fit_head_fn: Callable[..., dict[str, Any]] | None = None,
) -> tuple[list[np.ndarray], dict[str, Any]]:
    schedules = sorted({str(row["schedule_id"]) for row in trajectories})
    folds = []
    for held_schedule in schedules:
        model = fit_model(
            trajectories,
            lambda row, held=held_schedule: row["schedule_id"] != held,
            cfg,
            solver=solver,
            fit_head_fn=fit_head_fn,
        )
        held = [row for row in trajectories if row["schedule_id"] == held_schedule]
        if len(held) != 16:
            raise ValueError("R8R32 schedule fold cardinality changed")
        groups, evidence = _residuals(model, held)
        folds.append(
            {
                "held_schedule": held_schedule,
                "model_digest": _digest(model),
                "residual_groups": groups,
                "residual_digest": evidence["residual_digest"],
            }
        )
    tube, tube_evidence = r8r31._tube_from_fold_groups(folds, lambda row: True, cfg)
    contained = total = 0
    maximum_error = np.zeros(5)
    for fold in folds:
        for interval, offsets in enumerate(fold["residual_groups"]):
            for offset, values in enumerate(offsets):
                residual = np.asarray(values).reshape((-1, 5))
                contained += int(np.count_nonzero(residual <= tube[interval][offset] + 1e-15))
                total += residual.size
                if len(residual):
                    maximum_error = np.maximum(maximum_error, np.max(residual, axis=0))
    maximum_tube = np.max(np.concatenate(tube), axis=0) * FACTORS
    gates = cfg["model_gates"]
    passed = bool(
        contained == total
        and np.all(maximum_error * FACTORS <= np.asarray(gates["maximum_point_error"]) + 1e-15)
        and np.all(maximum_tube <= np.asarray(gates["maximum_tube_half_width"]) + 1e-15)
    )
    return tube, {
        "schedule_count": len(schedules),
        "training_schedule_count": len(schedules) - 1,
        "folds": [
            {
                "held_schedule": fold["held_schedule"],
                "model_digest": fold["model_digest"],
                "residual_digest": fold["residual_digest"],
            }
            for fold in folds
        ],
        "maximum_absolute_physical_error": (maximum_error * FACTORS).tolist(),
        "maximum_reserved_physical_tube_half_width": maximum_tube.tolist(),
        "contained_count": contained,
        "component_count": total,
        "containment_rate": contained / total,
        "tube_evidence": tube_evidence,
        "passed": passed,
    }


def _verify_bank(evidence: Mapping[str, Any], cfg: Mapping[str, Any]) -> None:
    contract = cfg["bank_contract"]
    if (
        int(evidence["trajectory_count"]) != int(contract["trajectory_count"])
        or int(evidence["context_count"]) != int(contract["history_context_count"])
        or int(evidence["schedule_count"]) != int(contract["schedule_count"])
        or int(evidence["interval_record_count"]) != int(contract["interval_record_count"])
        or any(evidence[key] != contract[key] for key in ("bank_digest", "feature_digest", "target_digest"))
    ):
        raise ValueError("R8R32 bank reproduction changed")


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
    _verify_bank(bank, ctx.cfg)
    rank_audit = representation_rank_audit(
        trajectories, ctx.cfg, rank_head_fn=rank_head_fn
    )
    if not rank_audit["passed"]:
        closed_reason = "representation_rank_gate_failed_before_regression"
        outer = {
            "metrics_ran": False,
            "phase_closed_reason": closed_reason,
            "rank_gate_passed": False,
            "maximum_absolute_physical_error": [0.0] * 5,
            "maximum_reserved_physical_tube_half_width": [0.0] * 5,
            "reserved_contained_count": 0,
            "reserved_component_count": 0,
            "reserved_containment_rate": 0.0,
            "state_support_pass_count": 0,
            "fold_rows": [],
            "passed": False,
        }
        schedule = {
            "metrics_ran": False,
            "phase_closed_reason": closed_reason,
            "rank_gate_passed": False,
            "schedule_count": int(ctx.cfg["bank_contract"]["schedule_count"]),
            "training_schedule_count": int(ctx.cfg["bank_contract"]["schedule_count"]) - 1,
            "folds": [],
            "maximum_absolute_physical_error": [0.0] * 5,
            "maximum_reserved_physical_tube_half_width": [0.0] * 5,
            "contained_count": 0,
            "component_count": 0,
            "containment_rate": 0.0,
            "tube_evidence": {"ran": False, "phase_closed_reason": closed_reason},
            "passed": False,
        }
        planning = {
            "ran": False,
            "phase_closed_reason": closed_reason,
            "safe_search_context_count": 0,
            "predicted_repaired_failed_baseline_count": 0,
            "predicted_regressed_baseline_pass_count": 0,
            "predicted_fallback_plus_plan_oracle_count": 0,
            "nonzero_first_action_count": 0,
            "plans": [],
            "passed": False,
        }
        faults: Mapping[str, Any] = {
            "ran": False,
            "phase_closed_reason": closed_reason,
            "passed": False,
        }
        detailed = {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "identity": IDENTITY,
            "solver": solver,
            "source_authentication": authentication,
            "bank_evidence": bank,
            "representation_rank_audit": rank_audit,
            "outer_model_evaluation": outer,
            "schedule_jackknife": schedule,
            "pair_planning_tube_evidence": {
                "ran": False,
                "phase_closed_reason": closed_reason,
            },
            "combined_tube_maximum_physical_half_width": [0.0] * 5,
            "combined_tube_cap_passed": False,
            "model_gate_passed": False,
            "transition_hulls": [],
            "planning_evaluation": planning,
            "fault_injection": faults,
            "integrity_gate_passed": True,
            "scientific_gate_passed": False,
            "passed": True,
            "route": ctx.cfg["routes"]["model_fail"],
            "real_tsc_executed": False,
            "plant_step_count": 0,
            "new_raw_count": 0,
        }
        artifact = {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "identity": IDENTITY,
            "solver": solver,
            "bank_evidence": bank,
            "representation_rank_audit": rank_audit,
            "representation_rank_gate_passed": False,
            "outer_models": [],
            "planning_model": {"intervals": []},
            "pair_tube": [],
            "schedule_tube": [],
            "combined_tube": [],
            "support": {},
            "transition_hulls": [],
        }
        return _jsonable(detailed), _jsonable(artifact)
    folds, outer = outer_model_evaluation(
        trajectories,
        ctx.cfg,
        ctx.source_ctx.cfg,
        solver=solver,
        fit_head_fn=fit_head_fn,
    )
    schedule_tube, schedule = schedule_jackknife(
        trajectories, ctx.cfg, solver=solver, fit_head_fn=fit_head_fn
    )
    pair_tube, pair_evidence = r8r31._tube_from_fold_groups(
        folds, lambda row: True, ctx.cfg
    )
    combined_tube = [
        np.maximum(pair, schedule_value)
        for pair, schedule_value in zip(pair_tube, schedule_tube)
    ]
    combined_maximum = np.max(np.concatenate(combined_tube), axis=0) * FACTORS
    combined_passed = bool(
        np.all(
            combined_maximum
            <= np.asarray(ctx.cfg["model_gates"]["maximum_tube_half_width"]) + 1e-15
        )
    )
    model = fit_model(
        trajectories,
        lambda row: True,
        ctx.cfg,
        solver=solver,
        fit_head_fn=fit_head_fn,
    )
    model_gate = bool(outer["passed"] and schedule["passed"] and combined_passed)
    planning = {
        "ran": False,
        "safe_search_context_count": 0,
        "predicted_repaired_failed_baseline_count": 0,
        "predicted_regressed_baseline_pass_count": 0,
        "predicted_fallback_plus_plan_oracle_count": 0,
        "nonzero_first_action_count": 0,
        "plans": [],
        "passed": False,
    }
    faults: Mapping[str, Any] = {"ran": False, "passed": False}
    hull_summary: list[dict[str, Any]] = []
    support_artifact: Mapping[str, Any] = {}
    if model_gate:
        hulls = r8r31.transition_hulls(trajectories, ctx.source_ctx.cfg)
        support = r8r31.planning_support(trajectories, ctx.source_ctx.cfg)
        plans = [
            r8r31.plan_context(
                ctx.source_ctx,
                context_meta[key],
                model,
                combined_tube,
                support,
                hulls,
            )
            for key in sorted(context_meta)
        ]
        baseline_source = _read(ctx.source_ctx.r8r28_stage / "analysis/primary_detailed.json")
        baseline = {
            (str(row["pair_id"]), str(row["history_member"])): bool(
                row["baseline"]["formal_contract_pass"]
            )
            for row in baseline_source["formal_authority"]["context_rows"]
        }
        repairs = regressions = oracle = nonzero = 0
        for plan in plans:
            key = (plan["pair_id"], plan["history_member"])
            robust = bool(plan["robust_formal_plan_found"])
            policy = robust or baseline[key]
            repairs += int(not baseline[key] and robust)
            regressions += int(baseline[key] and not policy)
            oracle += int(policy)
            selected = plan.get("selected_plan") or {}
            tokens = selected.get("candidate_indices") or []
            nonzero += int(robust and bool(tokens) and int(tokens[0]) != 0)
            plan["baseline_formal_pass"] = baseline[key]
            plan["fallback_or_plan_predicted_pass"] = policy
        faults = r8r31.fault_injections()
        gate = ctx.cfg["offline_gate"]
        planning_passed = bool(
            len(plans) == int(gate["required_safe_search_context_count"])
            and all(plan["safe_search_complete"] for plan in plans)
            and repairs >= int(gate["minimum_predicted_repaired_failed_baseline_count"])
            and regressions <= int(gate["maximum_predicted_regressed_baseline_pass_count"])
            and oracle >= int(gate["minimum_predicted_oracle_count"])
            and nonzero >= int(gate["minimum_nonzero_first_action_count"])
            and faults["pass_count"] == int(gate["required_fault_injection_count"])
            and faults["passed"]
        )
        planning = {
            "ran": True,
            "safe_search_context_count": sum(plan["safe_search_complete"] for plan in plans),
            "predicted_repaired_failed_baseline_count": repairs,
            "predicted_regressed_baseline_pass_count": regressions,
            "predicted_fallback_plus_plan_oracle_count": oracle,
            "nonzero_first_action_count": nonzero,
            "plans": plans,
            "passed": planning_passed,
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
        support_artifact = {
            "thresholds": support["thresholds"],
            "training_maxima": support["training_maxima"],
            "features": support["features"],
        }
    scientific = bool(model_gate and planning["passed"])
    route = (
        ctx.cfg["routes"]["model_fail"]
        if not model_gate
        else ctx.cfg["routes"]["pass"]
        if scientific
        else ctx.cfg["routes"]["authority_fail"]
    )
    detailed = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "identity": IDENTITY,
        "solver": solver,
        "source_authentication": authentication,
        "bank_evidence": bank,
        "representation_rank_audit": rank_audit,
        "outer_model_evaluation": outer,
        "schedule_jackknife": schedule,
        "pair_planning_tube_evidence": pair_evidence,
        "combined_tube_maximum_physical_half_width": combined_maximum.tolist(),
        "combined_tube_cap_passed": combined_passed,
        "model_gate_passed": model_gate,
        "transition_hulls": hull_summary,
        "planning_evaluation": planning,
        "fault_injection": faults,
        "integrity_gate_passed": True,
        "scientific_gate_passed": scientific,
        "passed": True,
        "route": route,
        "real_tsc_executed": False,
        "plant_step_count": 0,
        "new_raw_count": 0,
    }
    artifact = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "identity": IDENTITY,
        "solver": solver,
        "bank_evidence": bank,
        "representation_rank_audit": rank_audit,
        "representation_rank_gate_passed": True,
        "outer_models": [
            {"held_pair": fold["held_pair"], "model": fold["model"]}
            for fold in folds
        ],
        "planning_model": model,
        "pair_tube": pair_tube,
        "schedule_tube": schedule_tube,
        "combined_tube": combined_tube,
        "support": support_artifact,
        "transition_hulls": hull_summary,
    }
    return _jsonable(detailed), _jsonable(artifact)


def _summary(detailed: Mapping[str, Any], model_sha: str) -> dict[str, Any]:
    outer, schedule, planning = (
        detailed["outer_model_evaluation"],
        detailed["schedule_jackknife"],
        detailed["planning_evaluation"],
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "identity": IDENTITY,
        "phase": "offline_primary",
        "passed": True,
        "integrity_gate_passed": True,
        "scientific_gate_passed": bool(detailed["scientific_gate_passed"]),
        "route": detailed["route"],
        "trajectory_count": int(detailed["bank_evidence"]["trajectory_count"]),
        "schedule_count": int(detailed["bank_evidence"]["schedule_count"]),
        "interval_record_count": int(detailed["bank_evidence"]["interval_record_count"]),
        "bank_digest": detailed["bank_evidence"]["bank_digest"],
        "feature_digest": detailed["bank_evidence"]["feature_digest"],
        "target_digest": detailed["bank_evidence"]["target_digest"],
        "representation_rank_gate_passed": bool(
            detailed["representation_rank_audit"]["passed"]
        ),
        "representation_head_count": int(
            detailed["representation_rank_audit"]["head_count"]
        ),
        "representation_failed_head_count": int(
            detailed["representation_rank_audit"]["failed_head_count"]
        ),
        "representation_minimum_numerical_rank": int(
            detailed["representation_rank_audit"]["minimum_numerical_rank"]
        ),
        "outer_model_gate_passed": bool(outer["passed"]),
        "outer_maximum_absolute_physical_error": outer["maximum_absolute_physical_error"],
        "outer_maximum_reserved_physical_tube_half_width": outer[
            "maximum_reserved_physical_tube_half_width"
        ],
        "schedule_jackknife_passed": bool(schedule["passed"]),
        "schedule_maximum_absolute_physical_error": schedule["maximum_absolute_physical_error"],
        "schedule_maximum_reserved_physical_tube_half_width": schedule[
            "maximum_reserved_physical_tube_half_width"
        ],
        "combined_tube_cap_passed": bool(detailed["combined_tube_cap_passed"]),
        "model_gate_passed": bool(detailed["model_gate_passed"]),
        "planning_ran": bool(planning["ran"]),
        "predicted_repaired_failed_baseline_count": int(
            planning["predicted_repaired_failed_baseline_count"]
        ),
        "predicted_fallback_plus_plan_oracle_count": int(
            planning["predicted_fallback_plus_plan_oracle_count"]
        ),
        "nonzero_first_action_count": int(planning["nonzero_first_action_count"]),
        "model_artifact_sha256": model_sha,
        "real_tsc_executed": False,
        "plant_step_count": 0,
        "new_raw_count": 0,
        "controller_execution_authorized": False,
        "gate_a_qualified": False,
        "expert_data_allowed": False,
    }


def run_primary(ctx: Context) -> dict[str, Any]:
    if ctx.paths.stage.exists():
        raise ValueError("R8R32 primary requires a fresh stage directory")
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
    if any(not path.is_file() for path in (*paths.values(), ctx.paths.manifest, ctx.paths.state)):
        raise ValueError("R8R32 finalization evidence incomplete")
    summary, detailed, independent, manifest = (
        _read(paths["primary_summary"]),
        _read(paths["primary_detailed"]),
        _read(paths["independent"]),
        _read(ctx.paths.manifest),
    )
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
        or any(float(independent.get(field, math.inf)) > tolerance for field in difference_fields)
        or independent.get("primary_summary_sha256") != hashes["primary_summary"]
        or independent.get("primary_detailed_sha256") != hashes["primary_detailed"]
        or independent.get("primary_model_sha256") != hashes["model"]
        or independent.get("route") != summary.get("route")
        or bool(independent.get("real_tsc_executed"))
        or int(independent.get("plant_step_count", -1)) != 0
        or int(independent.get("new_raw_count", -1)) != 0
    ):
        raise ValueError("R8R32 finalization independent disagreement")
    compact = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "identity": IDENTITY,
        "audit_kind": "r8r32_compact_primary_independent_finalization",
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
        "independent_agreement": {field: independent[field] for field in agreement_fields},
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
    final["audit_kind"] = "r8r32_final_report"
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
