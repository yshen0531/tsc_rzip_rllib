"""Frozen zero-TSC R8R26 action-supported multiresolution MPC preflight."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
from scipy.spatial import ConvexHull

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r25_training_cardinality_matched_outer_jackknife_tube_preflight
    as r8r25,
)


r8r24 = r8r25.r8r24
r8r23 = r8r25.r8r23
SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S24D1R14R8R26"
IDENTITY = "action_transition_supported_multiresolution_mpc_preflight_v1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r26_action_transition_supported_multiresolution_mpc_preflight"
DECISIONS = (10, 14, 18, 22)
FACTORS = np.asarray([0.03, 0.03, 10000.0, 1.0, 1.0], dtype=float)


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
    source = (root / str(cfg["source_r8r25_config"])).resolve()
    model = cfg["model_contract"]
    schedule = cfg["schedule_jackknife_contract"]
    transition = cfg["transition_support_contract"]
    search = cfg["search_contract"]
    action = cfg["action_contract"]
    gates = cfg["model_gates"]
    formal = cfg["formal_contract"]
    fallback = cfg["fallback_contract"]
    planning = cfg["planning_gate"]
    if (
        int(cfg.get("schema_version", -1)) != SCHEMA_VERSION
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("run_name") != RUN_NAME
        or not design.is_relative_to(root)
        or not source.is_relative_to(root)
        or _sha(design) != str(cfg["design_document_sha256"])
        or _sha(source) != str(cfg["source_r8r25_config_sha256"])
        or tuple(map(int, (model["causal_feature_dimension"], model["expanded_feature_dimension"])))
        != (42, 133)
        or float(model["ridge_penalty"]) != 1e-4
        or model.get("masked_final_horizon_outputs") is not True
        or model.get("innovation_enabled") is not False
        or model.get("feature_selection_allowed") is not False
        or model.get("hyperparameter_search_allowed") is not False
        or tuple(map(int, (schedule["schedule_count"], schedule["training_schedule_count"], schedule["held_trajectory_count_per_schedule"])))
        != (27, 26, 16)
        or schedule.get("whole_schedule_exclusion") is not True
        or schedule.get("same_interval_required") is not True
        or schedule.get("same_lead_sample_required") is not True
        or schedule.get("residual_aggregation") != "componentwise_maximum"
        or float(schedule["reserve_multiplier"]) != 1.25
        or tuple(map(float, schedule["physical_point_error_floors"]))
        != (0.015, 0.015, 3000.0, 0.05, 0.05)
        or schedule.get("combine_with_r8r25_pair_tube") != "componentwise_maximum"
        or schedule.get("tube_clipping_allowed") is not False
        or tuple(map(int, (transition["lattice_denominator"], transition["maximum_coordinate_sum_units"])))
        != (16, 24)
        or tuple(
            map(
                float,
                (
                    transition["normalized_transition_scale"],
                    transition["affine_singular_value_tolerance"],
                    transition["affine_residual_tolerance"],
                    transition["convex_hull_inequality_tolerance"],
                ),
            )
        )
        != (1.5, 1e-12, 1e-12, 1e-10)
        or transition.get("qhull_joggle_allowed") is not False
        or transition.get("outcome_or_residual_selection_allowed") is not False
        or tuple(map(int, search["decision_task_steps"])) != DECISIONS
        or tuple(
            map(
                int,
                (
                    search["coarse_grid_unit_stride"],
                    search["coarse_level_count"],
                    search["beam_width"],
                    search["terminal_seed_count"],
                    search["maximum_sweeps_per_step"],
                ),
            )
        )
        != (4, 33, 256, 32, 16)
        or tuple(map(int, search["refinement_step_units"])) != (2, 1)
        or tuple(tuple(map(int, row)) for row in search["refinement_directions"])
        != ((1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1))
        or search.get("global_optimality_claimed") is not False
        or search.get("failed_plan_deployment_allowed") is not False
        or tuple(
            map(
                float,
                (
                    action["maximum_incremental_normalized_action_linf"],
                    action["maximum_total_normalized_action_abs"],
                    action["maximum_current_utilization"],
                    action["minimum_desired_applied_current_cosine"],
                    action["maximum_relative_off_basis_residual"],
                ),
            )
        )
        != (0.25, 1.0, 0.55, 0.98, 0.10)
        or action.get("require_exact_card15_issue") is not True
        or action.get("require_exact_card15_refresh") is not True
        or action.get("safe_stop_before_failed_advance") is not True
        or tuple(
            map(
                float,
                (
                    gates["maximum_R_point_error_m"],
                    gates["maximum_Z_point_error_m"],
                    gates["maximum_Ip_point_error_A"],
                    gates["maximum_vR_point_error_m_per_s"],
                    gates["maximum_vZ_point_error_m_per_s"],
                ),
            )
        )
        != (0.015, 0.015, 3000.0, 0.05, 0.05)
        or tuple(
            map(
                float,
                (
                    gates["maximum_reserved_R_tube_half_width_m"],
                    gates["maximum_reserved_Z_tube_half_width_m"],
                    gates["maximum_reserved_Ip_tube_half_width_A"],
                    gates["maximum_reserved_vR_tube_half_width_m_per_s"],
                    gates["maximum_reserved_vZ_tube_half_width_m_per_s"],
                ),
            )
        )
        != (0.025, 0.025, 5000.0, 0.08, 0.08)
        or tuple(map(float, (gates["required_reserved_tube_containment_rate"], gates["required_state_support_rate"])))
        != (1.0, 1.0)
        or tuple(map(int, (gates["maximum_finite_exclusion_count"], gates["maximum_forbidden_input_count"])))
        != (0, 0)
        or tuple(
            map(
                int,
                (
                    formal["normal_arrival_deadline_step"],
                    formal["normal_hold_through_step"],
                    formal["weak_arrival_deadline_step"],
                    formal["weak_hold_through_step"],
                    formal["arrival_streak_steps"],
                ),
            )
        )
        != (25, 35, 27, 37, 3)
        or tuple(map(float, (formal["position_tolerance_m"], formal["speed_tolerance_m_per_s"], formal["ip_tolerance_A"])))
        != (0.03, 0.1, 10000.0)
        or formal.get("arrival_deadline_expansion_allowed") is not False
        or fallback.get("fallback_controller") != "unchanged_causal_baseline_continuation"
        or fallback.get("plan_selected_only_if_robust_formal_pass") is not True
        or fallback.get("pair_or_history_label_allowed") is not False
        or fallback.get("source_outcome_label_allowed") is not False
        or fallback.get("future_state_allowed") is not False
        or tuple(
            map(
                int,
                (
                    planning["required_safe_search_context_count"],
                    planning["minimum_predicted_repaired_failed_baseline_count"],
                    planning["maximum_predicted_regressed_baseline_pass_count"],
                    planning["minimum_predicted_oracle_count"],
                ),
            )
        )
        != (16, 1, 0, 7)
        or float(planning["primary_independent_absolute_tolerance"]) != 1e-12
        or cfg.get("routes")
        != {
            "evidence_fail": "R8R26_INTEGRITY_FAIL_STOP",
            "model_fail": "ACTION_TRANSITION_SUPPORTED_TUBE_PREFLIGHT_INSUFFICIENT_REDESIGN_REQUIRED",
            "planning_fail": "ACTION_TRANSITION_SUPPORTED_MULTIRESOLUTION_AUTHORITY_INSUFFICIENT_CONTROLLER_SENTINEL_NOT_AUTHORIZED",
            "pass": "ACTION_TRANSITION_SUPPORTED_MULTIRESOLUTION_PREFLIGHT_PASS_FRESH_CONTROLLER_SENTINEL_DESIGN_REQUIRED",
        }
        or cfg.get("zero_new_tsc") is not True
        or cfg.get("expert_data_allowed") is not False
        or cfg.get("gate_a_qualified") is not False
    ):
        raise ValueError("R8R26 frozen contract changed")


def load_context(args: argparse.Namespace) -> Context:
    config_path = args.config.expanduser().resolve()
    cfg = _read(config_path)
    validate_config(cfg, project_root=_root())
    source_args = copy.copy(args)
    source_args.config = (_root() / str(cfg["source_r8r25_config"])).resolve()
    source_args.run_dir = args.r8r25_run
    source_ctx = r8r25.load_context(source_args)
    source_stage = args.r8r25_run.expanduser().resolve() / str(
        cfg["source_r8r25"]["stage_directory"]
    )
    return Context(cfg, config_path, _paths(args.run_dir), source_ctx, source_stage)


def _authenticate_source(ctx: Context) -> dict[str, Any]:
    expected = ctx.cfg["source_r8r25"]
    paths = {
        "primary_detailed": ctx.source_stage / "analysis/primary_detailed.json",
        "primary_summary": ctx.source_stage / "analysis/primary_summary.json",
        "independent": ctx.source_stage / "analysis/independent.json",
        "final_report": ctx.source_stage / "analysis/final_report.json",
        "model_evidence": ctx.source_stage / "model/outer_fold_models.json",
        "stage_manifest": ctx.source_stage / "stage_manifest.json",
        "stage_state": ctx.source_stage / "stage_state.json",
        "compact_audit": ctx.source_stage / "analysis/compact_audit.json",
    }
    hashes = {name: _sha(path) for name, path in paths.items()}
    if any(hashes[name] != str(expected[f"{name}_sha256"]) for name in paths):
        raise ValueError("R8R26 R8R25 source hash changed")
    primary = _read(paths["primary_detailed"])
    summary = _read(paths["primary_summary"])
    independent = _read(paths["independent"])
    final = _read(paths["final_report"])
    model = _read(paths["model_evidence"])
    state = _read(paths["stage_state"])
    compact = _read(paths["compact_audit"])
    if (
        ctx.source_stage.parent.name != str(expected["run_name"])
        or primary.get("route") != str(expected["required_route"])
        or summary.get("route") != str(expected["required_route"])
        or independent.get("route") != str(expected["required_route"])
        or final.get("route") != str(expected["required_route"])
        or final.get("primary_independent_agreement") is not True
        or independent.get("passed") is not True
        or primary.get("model_gate_passed") is not True
        or primary.get("predicted_feasibility_gate_passed") is not False
        or state.get("finished") is not True
        or compact.get("passed") is not True
        or compact.get("fresh_controller_sentinel_authorized") is not False
        or model["planning_evidence"]["tube_evidence"]["tube_digest"]
        != str(expected["planning_tube_digest"])
        or primary["planning_evaluation"]["planning_model_digest"]
        != str(expected["planning_model_digest"])
    ):
        raise ValueError("R8R26 R8R25 source outcome changed")
    transitive = r8r25._authenticate_source(ctx.source_ctx)
    if transitive.get("passed") is not True:
        raise ValueError("R8R26 transitive source authentication failed")
    return {"hashes": hashes, "route": str(final["route"]), "transitive": transitive, "passed": True}


def _fit_selected(
    trajectories: Sequence[Mapping[str, Any]],
    selected: Callable[[Mapping[str, Any]], bool],
    ridge: float,
) -> dict[str, Any]:
    intervals = []
    for interval in range(4):
        current = [row["intervals"][interval] for row in trajectories if selected(row)]
        maximum = max(len(row["targets"]) for row in current)
        offsets = []
        for offset in range(maximum):
            rows = [row for row in current if len(row["targets"]) > offset]
            x = np.asarray([row["expanded"] for row in rows], dtype=float)
            y = np.asarray([row["targets"][offset] for row in rows], dtype=float)
            x_mean, y_mean = np.mean(x, axis=0), np.mean(y, axis=0)
            centered_x, centered_y = x - x_mean, y - y_mean
            gram = centered_x.T @ centered_x
            coefficients = np.linalg.solve(
                gram + float(ridge) * np.eye(gram.shape[0]),
                centered_x.T @ centered_y,
            )
            intercept = y_mean - x_mean @ coefficients
            if (
                coefficients.shape != (133, 5)
                or intercept.shape != (5,)
                or not np.all(np.isfinite(coefficients))
                or not np.all(np.isfinite(intercept))
            ):
                raise ValueError("R8R26 schedule-held-out fit invalid")
            offsets.append(
                {
                    "sample_offset": offset,
                    "training_row_count": len(rows),
                    "intercept": intercept,
                    "coefficients": coefficients,
                }
            )
        intervals.append({"interval": interval, "offsets": offsets})
    return {"intervals": intervals}


def _schedule_jackknife(
    trajectories: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> tuple[list[np.ndarray], dict[str, Any]]:
    schedules = tuple(sorted({str(row["schedule_id"]) for row in trajectories}))
    if len(schedules) != 27:
        raise ValueError("R8R26 schedule inventory changed")
    groups: list[list[list[np.ndarray]]] = [[[] for _ in range(count)] for count in (4, 4, 4, 15)]
    folds = []
    all_residuals = []
    ridge = float(cfg["model_contract"]["ridge_penalty"])
    for held_schedule in schedules:
        model = _fit_selected(
            trajectories,
            lambda row, held=held_schedule: str(row["schedule_id"]) != held,
            ridge,
        )
        held = [row for row in trajectories if str(row["schedule_id"]) == held_schedule]
        if len(held) != 16:
            raise ValueError("R8R26 held schedule cardinality changed")
        predictions = r8r23._cold_predictions(model, held)
        serial = []
        for trajectory in held:
            identifier = str(trajectory["trajectory_id"])
            interval_rows = []
            for interval, row in enumerate(trajectory["intervals"]):
                residual = np.abs(
                    np.asarray(row["targets"], dtype=float)
                    - np.asarray(predictions[identifier][interval], dtype=float)
                )
                interval_rows.append(residual.tolist())
                all_residuals.append(residual)
                for offset, value in enumerate(residual):
                    groups[interval][offset].append(value)
            serial.append({"trajectory_id": identifier, "absolute_residuals": interval_rows})
        folds.append(
            {
                "held_schedule": held_schedule,
                "training_schedule_count": 26,
                "held_trajectory_count": len(held),
                "model_digest": _digest(r8r23._model_serializable(model)),
                "residual_digest": _digest(serial),
            }
        )
    floor = np.asarray(
        cfg["schedule_jackknife_contract"]["physical_point_error_floors"], dtype=float
    ) / FACTORS
    reserve = float(cfg["schedule_jackknife_contract"]["reserve_multiplier"])
    tube, counts = [], []
    for interval in groups:
        rows = []
        for values in interval:
            residuals = np.asarray(values, dtype=float).reshape((-1, 5))
            if len(residuals) == 0 or not np.all(np.isfinite(residuals)):
                raise ValueError("R8R26 schedule residual group invalid")
            rows.append(np.maximum(reserve * np.max(residuals, axis=0), floor))
            counts.append(len(residuals))
        tube.append(np.asarray(rows, dtype=float))
    maximum_error = np.max(np.concatenate(all_residuals, axis=0), axis=0) * FACTORS
    maximum_tube = np.max(np.concatenate(tube, axis=0), axis=0) * FACTORS
    contained = total = 0
    for interval, offsets in enumerate(groups):
        for offset, values in enumerate(offsets):
            residuals = np.asarray(values, dtype=float).reshape((-1, 5))
            contained += int(np.count_nonzero(residuals <= tube[interval][offset] + 1e-15))
            total += int(residuals.size)
    gates = cfg["model_gates"]
    point_caps = np.asarray(
        [
            gates["maximum_R_point_error_m"],
            gates["maximum_Z_point_error_m"],
            gates["maximum_Ip_point_error_A"],
            gates["maximum_vR_point_error_m_per_s"],
            gates["maximum_vZ_point_error_m_per_s"],
        ],
        dtype=float,
    )
    tube_caps = np.asarray(
        [
            gates["maximum_reserved_R_tube_half_width_m"],
            gates["maximum_reserved_Z_tube_half_width_m"],
            gates["maximum_reserved_Ip_tube_half_width_A"],
            gates["maximum_reserved_vR_tube_half_width_m_per_s"],
            gates["maximum_reserved_vZ_tube_half_width_m_per_s"],
        ],
        dtype=float,
    )
    point_pass = bool(np.all(maximum_error <= point_caps + 1e-15))
    containment_rate = contained / total
    containment_pass = bool(containment_rate >= float(gates["required_reserved_tube_containment_rate"]) - 1e-15)
    tube_pass = bool(np.all(maximum_tube <= tube_caps + 1e-15))
    evidence = {
        "schedule_ids": list(schedules),
        "schedule_count": len(schedules),
        "folds": folds,
        "minimum_residual_record_count": min(counts),
        "maximum_residual_record_count": max(counts),
        "maximum_absolute_physical_error": maximum_error.tolist(),
        "maximum_reserved_physical_tube_half_width": maximum_tube.tolist(),
        "reserved_tube_contained_component_count": contained,
        "reserved_tube_component_count": total,
        "reserved_tube_containment_rate": containment_rate,
        "point_error_gate_passed": point_pass,
        "reserved_tube_containment_gate_passed": containment_pass,
        "tube_cap_gate_passed": tube_pass,
        "tube_digest": _digest([value.tolist() for value in tube]),
        "finite_exclusion_count": 0,
        "forbidden_input_count": 0,
        "passed": bool(point_pass and containment_pass and tube_pass and contained == total == 56160),
    }
    return tube, evidence


def _deserialize_model(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "intervals": [
            {
                "interval": int(interval["interval"]),
                "offsets": [
                    {
                        "sample_offset": int(offset["sample_offset"]),
                        "training_row_count": int(offset["training_row_count"]),
                        "intercept": np.asarray(offset["intercept"], dtype=float),
                        "coefficients": np.asarray(offset["coefficients"], dtype=float),
                    }
                    for offset in interval["offsets"]
                ],
            }
            for interval in value["intervals"]
        ]
    }


def _source_reproduction(
    ctx: Context,
    trajectories: Sequence[Mapping[str, Any]],
    context_meta: Mapping[tuple[str, str], Mapping[str, Any]],
    model: Mapping[str, Any],
    pair_tube: Sequence[np.ndarray],
    support: Mapping[str, Any],
) -> dict[str, Any]:
    source = _read(ctx.source_stage / "analysis/primary_detailed.json")
    current_plans = [
        r8r25._plan_context(ctx.source_ctx, context_meta[key], model, pair_tube, support)
        for key in sorted(context_meta)
    ]
    source_plans = source["planning_evaluation"]["plans"]
    result = {
        "planning_model_digest": _digest(r8r23._model_serializable(model)),
        "pair_tube_digest": _digest([np.asarray(value).tolist() for value in pair_tube]),
        "maximum_original_plan_absolute_difference": r8r24._maximum_difference(source_plans, current_plans),
        "original_plan_count": len(current_plans),
    }
    expected = ctx.cfg["source_r8r25"]
    result["passed"] = bool(
        result["planning_model_digest"] == str(expected["planning_model_digest"])
        and result["pair_tube_digest"] == str(expected["planning_tube_digest"])
        and result["maximum_original_plan_absolute_difference"] <= 1e-12
        and result["original_plan_count"] == 16
    )
    if not result["passed"]:
        raise ValueError("R8R26 did not reproduce R8R25 planning evidence")
    return result


def _transition_hulls(
    trajectories: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> list[dict[str, Any]]:
    contract = cfg["transition_support_contract"]
    scale = float(contract["normalized_transition_scale"])
    singular_tolerance = float(contract["affine_singular_value_tolerance"])
    hulls = []
    for interval in range(4):
        rows = sorted(
            {
                tuple(
                    np.concatenate(
                        (
                            np.asarray(trajectory["intervals"][interval]["previous_q"], dtype=float),
                            np.asarray(trajectory["intervals"][interval]["q"], dtype=float),
                        )
                    )
                    / scale
                )
                for trajectory in trajectories
            }
        )
        points = np.asarray(rows, dtype=float)
        origin = np.mean(points, axis=0)
        centered = points - origin
        _, singular, vh = np.linalg.svd(centered, full_matrices=False)
        rank = int(np.count_nonzero(singular > singular_tolerance))
        basis = vh[:rank].T
        projected = centered @ basis
        if rank == 1:
            equations = np.asarray(
                [[1.0, -float(np.max(projected[:, 0]))], [-1.0, float(np.min(projected[:, 0]))]],
                dtype=float,
            )
        elif rank >= 2:
            equations = np.asarray(ConvexHull(projected).equations, dtype=float)
        else:
            equations = np.empty((0, 1), dtype=float)
        hulls.append(
            {
                "interval": interval,
                "points": points,
                "origin": origin,
                "basis": basis,
                "equations": equations,
                "affine_rank": rank,
                "observed_transition_count": len(points),
                "singular_values": singular,
                "digest": _digest(rows),
            }
        )
    return hulls


def _transition_supported(
    hull: Mapping[str, Any], previous_q: np.ndarray, q: np.ndarray, cfg: Mapping[str, Any]
) -> bool:
    contract = cfg["transition_support_contract"]
    scale = float(contract["normalized_transition_scale"])
    value = np.concatenate((previous_q, q)) / scale
    delta = value - np.asarray(hull["origin"], dtype=float)
    basis = np.asarray(hull["basis"], dtype=float)
    projected = delta @ basis
    reconstructed = projected @ basis.T
    if np.linalg.norm(delta - reconstructed) > float(contract["affine_residual_tolerance"]) + 1e-15:
        return False
    equations = np.asarray(hull["equations"], dtype=float)
    if len(equations) == 0:
        return bool(np.linalg.norm(delta) <= float(contract["affine_residual_tolerance"]) + 1e-15)
    maximum = float(np.max(equations[:, :-1] @ projected + equations[:, -1]))
    return maximum <= float(contract["convex_hull_inequality_tolerance"]) + 1e-15


def _all_lattice_units(cfg: Mapping[str, Any]) -> list[tuple[int, int]]:
    maximum = int(cfg["transition_support_contract"]["maximum_coordinate_sum_units"])
    return [(u, v) for u in range(maximum + 1) for v in range(maximum + 1 - u)]


def _coarse_units(ctx: Context) -> list[tuple[int, int]]:
    stride = int(ctx.cfg["search_contract"]["coarse_grid_unit_stride"])
    maximum = int(ctx.cfg["transition_support_contract"]["maximum_coordinate_sum_units"])
    output = {(u, v) for u in range(0, maximum + 1, stride) for v in range(0, maximum + 1 - u, stride)}
    source_r23_ctx = ctx.source_ctx.source_ctx.source_ctx
    for level in r8r23._action_levels(source_r23_ctx):
        q = np.asarray(level["q"], dtype=float)
        units = tuple(map(int, np.rint(q * 16.0)))
        if not np.allclose(q, np.asarray(units) / 16.0, rtol=0.0, atol=1e-15):
            raise ValueError("R8R26 source level is off the frozen lattice")
        output.add(units)
    result = sorted(output)
    if len(result) != int(ctx.cfg["search_contract"]["coarse_level_count"]):
        raise ValueError("R8R26 coarse level count changed")
    return result


def _level(units: tuple[int, int]) -> dict[str, Any]:
    return {
        "index": -1,
        "level_id": f"q_u{units[0]:02d}_v{units[1]:02d}",
        "q": [units[0] / 16.0, units[1] / 16.0],
        "units": units,
    }


@dataclass
class SearchCounter:
    evaluated_sequences: int = 0
    safe_expansions: int = 0
    state_unsupported_nodes: int = 0
    transition_unsupported_expansions: int = 0
    hard_action_rejections: int = 0
    digest: Any = None

    def __post_init__(self) -> None:
        self.digest = hashlib.sha256()

    def record(self, tokens: Sequence[tuple[int, int]], status: str) -> None:
        self.evaluated_sequences += 1
        self.digest.update(
            (json.dumps([list(value) for value in tokens], separators=(",", ":")) + "|" + status + "\n").encode("ascii")
        )


def _deadline_endpoint(meta: Mapping[str, Any], cfg: Mapping[str, Any]) -> tuple[int, int]:
    weak = math.isclose(float(meta["slew_scale"]), 0.9, abs_tol=1e-15)
    return (
        int(cfg["formal_contract"]["weak_arrival_deadline_step" if weak else "normal_arrival_deadline_step"]),
        int(cfg["formal_contract"]["weak_hold_through_step" if weak else "normal_hold_through_step"]),
    )


def _node_rank(node: Mapping[str, Any], *, terminal: bool, deadline: int, endpoint: int, cfg: Mapping[str, Any]) -> tuple[Any, ...]:
    states = np.asarray(node["states"], dtype=float)
    if terminal:
        passed, violation, integrated = r8r23._robust_formal(
            states,
            np.asarray(node["tubes"], dtype=float),
            deadline=deadline,
            endpoint=endpoint,
            cfg=cfg,
        )
        return (
            not passed,
            violation,
            integrated,
            float(node["movement"]),
            float(node["maximum_current"]),
            tuple(node["tokens"]),
        )
    integrated = float(np.sum(states[10:, :3] ** 2))
    return (
        integrated,
        float(node["maximum_current"]),
        float(node["movement"]),
        tuple(node["tokens"]),
    )


def _initial_node(meta: Mapping[str, Any]) -> dict[str, Any]:
    states = r8r23._state_matrix(meta["baseline_result"], meta["target"])
    prefix = states[: DECISIONS[0] + 1]
    current = np.asarray(meta["baseline_result"]["trajectory"][DECISIONS[0]]["currents_a_tsc"], dtype=float)
    return {
        "states": prefix,
        "tubes": np.zeros_like(prefix),
        "current": current,
        "previous_current": current,
        "previous_q": np.zeros(2, dtype=float),
        "tokens": tuple(),
        "movement": 0.0,
        "maximum_current": 0.0,
    }


def _expand_node(
    ctx: Context,
    meta: Mapping[str, Any],
    model: Mapping[str, Any],
    tube: Sequence[np.ndarray],
    support: Mapping[str, Any],
    hulls: Sequence[Mapping[str, Any]],
    node: Mapping[str, Any],
    interval: int,
    units: tuple[int, int],
    counter: SearchCounter,
) -> dict[str, Any] | None:
    feature = r8r23._planning_feature(
        np.asarray(node["states"]),
        np.asarray(node["current"]),
        np.asarray(node["previous_current"]),
        np.asarray(node["previous_q"]),
        np.asarray(meta["coil_limits"], dtype=float),
    )
    tokens = tuple(node["tokens"]) + (units,)
    if not r8r25._planning_supported(support, feature, interval):
        counter.state_unsupported_nodes += 1
        counter.record(tokens, "state_unsupported")
        return None
    level = _level(units)
    q = np.asarray(level["q"], dtype=float)
    if not _transition_supported(hulls[interval], np.asarray(node["previous_q"]), q, ctx.cfg):
        counter.transition_unsupported_expansions += 1
        counter.record(tokens, "transition_unsupported")
        return None
    source_r23_ctx = ctx.source_ctx.source_ctx.source_ctx
    issue = r8r23._safe_issue(source_r23_ctx, meta, np.asarray(node["current"]), level, DECISIONS[interval])
    if not bool(issue["passed"]):
        counter.hard_action_rejections += 1
        counter.record(tokens, "hard_action_rejected")
        return None
    count = 4 if interval < 3 else _deadline_endpoint(meta, ctx.cfg)[1] - DECISIONS[3]
    row = {
        "interval": interval,
        "feature": feature,
        "q": q,
        "previous_q": np.asarray(node["previous_q"]),
        "targets": np.zeros((count, 5), dtype=float),
    }
    row["expanded"] = r8r23._expanded_row(row)
    prediction = r8r23.predict_row(model, row)
    next_current = np.asarray(issue["nominal_issue_readback_current_a_tsc"], dtype=float)
    counter.safe_expansions += 1
    counter.record(tokens, "safe")
    return {
        "states": np.concatenate((np.asarray(node["states"]), prediction), axis=0),
        "tubes": np.concatenate((np.asarray(node["tubes"]), np.asarray(tube[interval][:count])), axis=0),
        "current": next_current,
        "previous_current": np.asarray(node["current"]),
        "previous_q": q,
        "tokens": tokens,
        "movement": float(node["movement"]) + float(np.sum(np.abs(q - np.asarray(node["previous_q"])) )),
        "maximum_current": max(float(node["maximum_current"]), float(issue["predicted_current_utilization"])),
    }


def _evaluate_tokens(
    ctx: Context,
    meta: Mapping[str, Any],
    model: Mapping[str, Any],
    tube: Sequence[np.ndarray],
    support: Mapping[str, Any],
    hulls: Sequence[Mapping[str, Any]],
    tokens: Sequence[tuple[int, int]],
    counter: SearchCounter,
) -> dict[str, Any] | None:
    node = _initial_node(meta)
    for interval, units in enumerate(tokens):
        node = _expand_node(ctx, meta, model, tube, support, hulls, node, interval, units, counter)
        if node is None:
            return None
    return node


def _plan_context(
    ctx: Context,
    meta: Mapping[str, Any],
    model: Mapping[str, Any],
    tube: Sequence[np.ndarray],
    support: Mapping[str, Any],
    hulls: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    counter = SearchCounter()
    deadline, endpoint = _deadline_endpoint(meta, ctx.cfg)
    beam = [_initial_node(meta)]
    coarse = _coarse_units(ctx)
    beam_width = int(ctx.cfg["search_contract"]["beam_width"])
    seed_count = int(ctx.cfg["search_contract"]["terminal_seed_count"])
    beam_counts = []
    for interval in range(4):
        expanded = []
        for node in beam:
            for units in coarse:
                next_node = _expand_node(ctx, meta, model, tube, support, hulls, node, interval, units, counter)
                if next_node is not None:
                    expanded.append(next_node)
        terminal = interval == 3
        expanded.sort(key=lambda node: _node_rank(node, terminal=terminal, deadline=deadline, endpoint=endpoint, cfg=ctx.cfg))
        beam = expanded[: (seed_count if terminal else beam_width)]
        beam_counts.append(len(beam))
        if not beam:
            break
    seeds = list(beam)
    refined = []
    directions = tuple(tuple(map(int, row)) for row in ctx.cfg["search_contract"]["refinement_directions"])
    maximum_units = int(ctx.cfg["transition_support_contract"]["maximum_coordinate_sum_units"])
    maximum_sweeps = int(ctx.cfg["search_contract"]["maximum_sweeps_per_step"])
    refinement_records = []
    for seed_index, seed in enumerate(seeds):
        current = seed
        scale_records = []
        for step_units in map(int, ctx.cfg["search_contract"]["refinement_step_units"]):
            sweeps = accepted = 0
            for _ in range(maximum_sweeps):
                sweeps += 1
                current_rank = _node_rank(current, terminal=True, deadline=deadline, endpoint=endpoint, cfg=ctx.cfg)
                candidates = []
                current_tokens = tuple(current["tokens"])
                for decision_index in range(4):
                    for direction_index, direction in enumerate(directions):
                        old = current_tokens[decision_index]
                        candidate_units = (
                            old[0] + step_units * direction[0],
                            old[1] + step_units * direction[1],
                        )
                        if (
                            candidate_units[0] < 0
                            or candidate_units[1] < 0
                            or sum(candidate_units) > maximum_units
                        ):
                            continue
                        tokens = list(current_tokens)
                        tokens[decision_index] = candidate_units
                        node = _evaluate_tokens(ctx, meta, model, tube, support, hulls, tokens, counter)
                        if node is None:
                            continue
                        rank = _node_rank(node, terminal=True, deadline=deadline, endpoint=endpoint, cfg=ctx.cfg)
                        candidates.append((rank, decision_index, direction_index, node))
                if not candidates:
                    break
                candidates.sort(key=lambda row: (row[0], row[1], row[2]))
                if candidates[0][0] < current_rank:
                    current = candidates[0][3]
                    accepted += 1
                else:
                    break
            scale_records.append({"step_units": step_units, "sweeps": sweeps, "accepted_moves": accepted})
        refined.append(current)
        refinement_records.append({"seed_index": seed_index, "scales": scale_records})
    candidates = seeds + refined
    candidates.sort(key=lambda node: _node_rank(node, terminal=True, deadline=deadline, endpoint=endpoint, cfg=ctx.cfg))
    best = candidates[0] if candidates else None
    selected = None
    if best is not None:
        rank = _node_rank(best, terminal=True, deadline=deadline, endpoint=endpoint, cfg=ctx.cfg)
        selected = {
            "q_units": [list(value) for value in best["tokens"]],
            "q_values": [[value[0] / 16.0, value[1] / 16.0] for value in best["tokens"]],
            "robust_formal_pass": not bool(rank[0]),
            "worst_formal_margin_violation": float(rank[1]),
            "integrated_normalized_error": float(rank[2]),
            "cumulative_normalized_action_movement": float(rank[3]),
            "maximum_predicted_current_utilization": float(rank[4]),
            "predicted_states": np.asarray(best["states"]).tolist(),
            "reserved_tubes": np.asarray(best["tubes"]).tolist(),
        }
    robust = bool(selected and selected["robust_formal_pass"])
    return {
        "pair_id": str(meta["pair_id"]),
        "history_member": str(meta["history_member"]),
        "coarse_level_count": len(coarse),
        "beam_counts": beam_counts,
        "terminal_seed_count": len(seeds),
        "refinement_records": refinement_records,
        "safe_search_complete": best is not None,
        "selected_plan": selected,
        "robust_formal_plan_found": robust,
        "causal_selected_mode": "refined_plan" if robust else "baseline_fallback",
        "search_counts": {
            "evaluated_sequences": counter.evaluated_sequences,
            "safe_expansions": counter.safe_expansions,
            "state_unsupported_nodes": counter.state_unsupported_nodes,
            "transition_unsupported_expansions": counter.transition_unsupported_expansions,
            "hard_action_rejections": counter.hard_action_rejections,
        },
        "evaluated_sequence_digest": counter.digest.hexdigest(),
    }


def _planning_evaluation(
    ctx: Context,
    model: Mapping[str, Any],
    combined_tube: Sequence[np.ndarray],
    support: Mapping[str, Any],
    hulls: Sequence[Mapping[str, Any]],
    context_meta: Mapping[tuple[str, str], Mapping[str, Any]],
) -> dict[str, Any]:
    plans = [
        _plan_context(ctx, context_meta[key], model, combined_tube, support, hulls)
        for key in sorted(context_meta)
    ]
    source_r23_ctx = ctx.source_ctx.source_ctx.source_ctx
    source = _read(source_r23_ctx.r8r22_ctx.paths.analysis / "primary_detailed.json")
    baseline = {
        (str(row["pair_id"]), str(row["history_member"])): bool(row["baseline"]["formal_contract_pass"])
        for row in source["formal_authority"]["context_rows"]
    }
    repairs = regressions = oracle = 0
    for plan in plans:
        key = (str(plan["pair_id"]), str(plan["history_member"]))
        plan_pass = bool(plan["robust_formal_plan_found"])
        policy_pass = plan_pass if plan_pass else baseline[key]
        repairs += int(not baseline[key] and policy_pass)
        regressions += int(baseline[key] and not policy_pass)
        oracle += int(policy_pass)
        plan["baseline_formal_pass_for_postselection_scoring"] = baseline[key]
        plan["hybrid_predicted_formal_pass"] = policy_pass
    complete = sum(bool(plan["safe_search_complete"]) for plan in plans)
    gate = ctx.cfg["planning_gate"]
    passed = bool(
        complete == int(gate["required_safe_search_context_count"])
        and repairs >= int(gate["minimum_predicted_repaired_failed_baseline_count"])
        and regressions <= int(gate["maximum_predicted_regressed_baseline_pass_count"])
        and oracle >= int(gate["minimum_predicted_oracle_count"])
    )
    return {
        "safe_search_context_count": complete,
        "predicted_repaired_failed_baseline_count": repairs,
        "predicted_regressed_baseline_pass_count": regressions,
        "predicted_baseline_fallback_plus_plan_oracle_count": oracle,
        "robust_formal_plan_context_count": sum(bool(plan["robust_formal_plan_found"]) for plan in plans),
        "plans": plans,
        "passed": passed,
    }


def compute(ctx: Context) -> tuple[dict[str, Any], dict[str, Any]]:
    authentication = _authenticate_source(ctx)
    source_r23_ctx = ctx.source_ctx.source_ctx.source_ctx
    trajectories, context_meta = r8r23.build_bank(source_r23_ctx)
    bank = r8r23._bank_evidence(trajectories)
    expected = ctx.cfg["source_r8r25"]
    schedules = sorted({str(row["schedule_id"]) for row in trajectories})
    if (
        bank["feature_digest"] != str(expected["feature_digest"])
        or bank["target_digest"] != str(expected["target_digest"])
        or len(schedules) != int(expected["schedule_count"])
    ):
        raise ValueError("R8R26 recomputed bank differs from R8R25")
    source_model_evidence = _read(ctx.source_stage / "model/outer_fold_models.json")
    planning_evidence = source_model_evidence["planning_evidence"]
    model = _deserialize_model(planning_evidence["model"])
    pair_tube = [np.asarray(value, dtype=float) for value in planning_evidence["tube_template"]]
    support = r8r25._planning_support(trajectories, ctx.source_ctx.cfg)
    reproduction = _source_reproduction(ctx, trajectories, context_meta, model, pair_tube, support)
    schedule_tube, schedule_evidence = _schedule_jackknife(trajectories, ctx.cfg)
    combined_tube = [np.maximum(pair, schedule) for pair, schedule in zip(pair_tube, schedule_tube)]
    combined_physical = np.max(np.concatenate(combined_tube, axis=0), axis=0) * FACTORS
    gates = ctx.cfg["model_gates"]
    caps = np.asarray(
        [
            gates["maximum_reserved_R_tube_half_width_m"],
            gates["maximum_reserved_Z_tube_half_width_m"],
            gates["maximum_reserved_Ip_tube_half_width_A"],
            gates["maximum_reserved_vR_tube_half_width_m_per_s"],
            gates["maximum_reserved_vZ_tube_half_width_m_per_s"],
        ],
        dtype=float,
    )
    combined_cap_pass = bool(np.all(combined_physical <= caps + 1e-15))
    model_gate = bool(schedule_evidence["passed"] and combined_cap_pass)
    hulls = _transition_hulls(trajectories, ctx.cfg)
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
    if model_gate:
        planning = _planning_evaluation(ctx, model, combined_tube, support, hulls, context_meta)
    else:
        planning = {
            "safe_search_context_count": 0,
            "predicted_repaired_failed_baseline_count": 0,
            "predicted_regressed_baseline_pass_count": 0,
            "predicted_baseline_fallback_plus_plan_oracle_count": 6,
            "robust_formal_plan_context_count": 0,
            "plans": [],
            "skipped_reason": "frozen_schedule_jackknife_or_combined_tube_gate_failed",
            "passed": False,
        }
    scientific = bool(model_gate and planning["passed"])
    route = str(ctx.cfg["routes"]["pass" if scientific else ("planning_fail" if model_gate else "model_fail")])
    detailed = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "source_authentication": authentication,
        "bank_evidence": {**bank, "schedule_count": len(schedules), "schedule_ids": schedules},
        "source_reproduction": reproduction,
        "schedule_jackknife_evaluation": schedule_evidence,
        "pair_tube_digest": _digest([value.tolist() for value in pair_tube]),
        "combined_tube_digest": _digest([value.tolist() for value in combined_tube]),
        "maximum_combined_physical_tube_half_width": combined_physical.tolist(),
        "combined_tube_cap_gate_passed": combined_cap_pass,
        "transition_hull_evidence": hull_evidence,
        "coarse_level_units": [list(value) for value in _coarse_units(ctx)],
        "model_gate_passed": model_gate,
        "planning_evaluation": planning,
        "predicted_feasibility_gate_passed": bool(planning["passed"]),
        "scientific_gate_passed": scientific,
        "route": route,
        "fresh_controller_sentinel_authorized": scientific,
        "real_tsc_executed": False,
        "plant_step_count": 0,
        "new_raw_count": 0,
        "allowed_in_expert_dataset": False,
    }
    model_evidence = {
        "schema_version": 1,
        "stage": STAGE,
        "planning_model_digest": reproduction["planning_model_digest"],
        "pair_tube": [value.tolist() for value in pair_tube],
        "schedule_tube": [value.tolist() for value in schedule_tube],
        "combined_tube": [value.tolist() for value in combined_tube],
        "schedule_fold_digests": schedule_evidence["folds"],
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
            for key in ("training_nearest_neighbor_maxima", "thresholds", "training_origin_count_by_interval")
        },
    }
    return detailed, model_evidence


def _summary(detailed: Mapping[str, Any], model_sha: str) -> dict[str, Any]:
    schedule = detailed["schedule_jackknife_evaluation"]
    planning = detailed["planning_evaluation"]
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
        "model_evidence_sha256": model_sha,
        "maximum_schedule_heldout_physical_error": schedule["maximum_absolute_physical_error"],
        "maximum_schedule_reserved_physical_tube_half_width": schedule["maximum_reserved_physical_tube_half_width"],
        "maximum_combined_physical_tube_half_width": detailed["maximum_combined_physical_tube_half_width"],
        "schedule_reserved_tube_containment_rate": schedule["reserved_tube_containment_rate"],
        "model_gate_passed": detailed["model_gate_passed"],
        "safe_search_context_count": planning["safe_search_context_count"],
        "robust_formal_plan_context_count": planning["robust_formal_plan_context_count"],
        "predicted_repaired_failed_baseline_count": planning["predicted_repaired_failed_baseline_count"],
        "predicted_regressed_baseline_pass_count": planning["predicted_regressed_baseline_pass_count"],
        "predicted_baseline_fallback_plus_plan_oracle_count": planning["predicted_baseline_fallback_plus_plan_oracle_count"],
        "predicted_feasibility_gate_passed": detailed["predicted_feasibility_gate_passed"],
        "scientific_gate_passed": detailed["scientific_gate_passed"],
        "route": detailed["route"],
        "fresh_controller_sentinel_authorized": detailed["fresh_controller_sentinel_authorized"],
        "real_tsc_executed": False,
        "plant_step_count": 0,
        "new_raw_count": 0,
        "gate_a_qualified": False,
    }


def run_primary(ctx: Context) -> dict[str, Any]:
    if ctx.paths.stage.exists() and any(ctx.paths.stage.iterdir()):
        raise ValueError("R8R26 primary requires an empty stage directory")
    ctx.paths.analysis.mkdir(parents=True, exist_ok=True)
    ctx.paths.model.mkdir(parents=True, exist_ok=True)
    detailed, model_evidence = compute(ctx)
    model_path = ctx.paths.model / "preflight_evidence.json"
    _write(model_path, model_evidence)
    model_sha = _sha(model_path)
    detailed["model_evidence_sha256"] = model_sha
    detailed_path = ctx.paths.analysis / "primary_detailed.json"
    summary_path = ctx.paths.analysis / "primary_summary.json"
    _write(detailed_path, detailed)
    _write(summary_path, _summary(detailed, model_sha))
    _write(
        ctx.paths.manifest,
        {
            "schema_version": 1,
            "stage": STAGE,
            "identity": IDENTITY,
            "config_path": str(ctx.config_path),
            "config_sha256": _sha(ctx.config_path),
            "design_document_sha256": ctx.cfg["design_document_sha256"],
            "source_r8r25_run": str(ctx.source_stage.parent),
            "source_r8r25_stage_state_sha256": ctx.cfg["source_r8r25"]["stage_state_sha256"],
            "primary_detailed_sha256": _sha(detailed_path),
            "primary_summary_sha256": _sha(summary_path),
            "model_evidence_sha256": model_sha,
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
        "primary_bank_agreement",
        "primary_source_reproduction_agreement",
        "primary_schedule_agreement",
        "primary_hull_agreement",
        "primary_plan_agreement",
        "primary_route_agreement",
        "primary_outcome_agreement",
    )
    if independent.get("passed") is not True or any(independent.get(key) is not True for key in required):
        raise ValueError("R8R26 independent agreement incomplete")
    final = {
        **summary,
        "primary_detailed_sha256": _sha(primary_path),
        "primary_summary_sha256": _sha(summary_path),
        "independent_sha256": _sha(independent_path),
        "primary_independent_agreement": True,
        "passed": bool(primary["scientific_gate_passed"]),
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
            "verdict": {"passed": bool(final["passed"]), "route": str(final["route"])},
            "stop_reason": (
                "all_preflight_gates_passed"
                if final["passed"]
                else ("planning_gate_failed" if primary["model_gate_passed"] else "schedule_or_combined_tube_gate_failed")
            ),
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
    parser.add_argument("--r8r26-command", choices=("primary", "postprocess"), required=True)
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
    result = run_primary(ctx) if args.r8r26_command == "primary" else postprocess(ctx)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
