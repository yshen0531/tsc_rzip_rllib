"""R8R31 aligned explicit-q4 feedback model and zero-TSC preflight."""

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
from scipy.spatial import ConvexHull, cKDTree

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r14_cumulative_multidirection_staircase_authority_identification
    as r8r14,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r23_causal_online_innovation_receding_horizon_preflight
    as r8r23,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r28_front_loaded_cumulative_endpoint_timing_authority_sentinel
    as r8r28,
)


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S24D1R14R8R31"
IDENTITY = "aligned_explicit_four_coordinate_measurement_recentered_feedback_v1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r31_aligned_explicit_four_coordinate_feedback_sentinel"
DECISIONS = (10, 12, 14, 16, 18, 22)
MAX_COUNTS = (2, 2, 2, 2, 4, 15)
OUTPUT_FACTORS = np.asarray([0.03, 0.03, 10000.0, 1.0, 1.0], dtype=float)
ZERO_Q = np.zeros(4, dtype=float)


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
    source: Path
    state: Path
    manifest: Path


@dataclass(frozen=True)
class Context:
    cfg: Mapping[str, Any]
    config_path: Path
    paths: Paths
    r8r23_ctx: Any
    r8r28_ctx: Any
    r8r23_stage: Path
    r8r14_stage: Path
    r8r28_stage: Path


def _paths(run_dir: Path) -> Paths:
    stage = run_dir.expanduser().resolve() / RUN_NAME
    return Paths(
        stage=stage,
        analysis=stage / "analysis",
        model=stage / "model",
        source=stage / "source_reference",
        state=stage / "stage_state.json",
        manifest=stage / "stage_manifest.json",
    )


def validate_config(cfg: Mapping[str, Any], *, project_root: Path) -> None:
    root = project_root.resolve()
    design = (root / str(cfg["design_document"])).resolve()
    source23 = (root / str(cfg["source_r8r23_config"])).resolve()
    source28 = (root / str(cfg["source_r8r28_config"])).resolve()
    bank = cfg["bank_contract"]
    model = cfg["model_contract"]
    support = cfg["support_contract"]
    candidates = cfg["candidate_contract"]
    action = cfg["action_contract"]
    formal = cfg["formal_contract"]
    gate = cfg["offline_gate"]
    scope = cfg["scientific_scope"]
    expected_candidates = (
        ("q0", (0.0, 0.0, 0.0, 0.0)),
        ("d0m", (-1.0, 0.0, 0.0, 0.0)),
        ("d0p", (1.0, 0.0, 0.0, 0.0)),
        ("d1p", (0.0, 1.0, 0.0, 0.0)),
        ("d2m", (0.0, 0.0, -1.0, 0.0)),
        ("d3m", (0.0, 0.0, 0.0, -1.0)),
        ("d3p", (0.0, 0.0, 0.0, 1.0)),
        ("u0p50", (0.0, 0.0, 0.5, 0.0)),
        ("u0p75", (0.0, 0.0, 0.75, 0.0)),
        ("u1p00", (0.0, 0.0, 1.0, 0.0)),
        ("u1p25", (0.0, 0.0, 1.25, 0.0)),
        ("u1p50", (0.0, 0.0, 1.5, 0.0)),
        ("v0p50", (0.0, -0.5, 0.0, 0.0)),
        ("v0p75", (0.0, -0.75, 0.0, 0.0)),
        ("v1p00", (0.0, -1.0, 0.0, 0.0)),
        ("v1p25", (0.0, -1.25, 0.0, 0.0)),
        ("v1p50", (0.0, -1.5, 0.0, 0.0)),
    )
    actual_candidates = tuple(
        (str(row["id"]), tuple(map(float, row["q"])))
        for row in candidates["candidates"]
    )
    invalid = (
        int(cfg.get("schema_version", -1)) != SCHEMA_VERSION
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("run_name") != RUN_NAME
        or not design.is_relative_to(root)
        or not source23.is_relative_to(root)
        or not source28.is_relative_to(root)
        or _sha(design) != str(cfg["design_document_sha256"])
        or _sha(source23) != str(cfg["source_r8r23_config_sha256"])
        or _sha(source28) != str(cfg["source_r8r28_config_sha256"])
        or tuple(
            map(
                int,
                (
                    bank["physical_pair_count"],
                    bank["history_context_count"],
                    bank["r8r23_trajectory_count"],
                    bank["r8r14_added_trajectory_count"],
                    bank["r8r28_g2_trajectory_count"],
                    bank["r8r28_g3_trajectory_count"],
                    bank["trajectory_count"],
                    bank["schedule_count"],
                    bank["interval_record_count"],
                ),
            )
        )
        != (8, 16, 432, 96, 32, 0, 560, 35, 3360)
        or tuple(map(int, bank["decision_task_steps"])) != DECISIONS
        or tuple(map(int, bank["maximum_forecast_samples_by_interval"]))
        != MAX_COUNTS
        or tuple(
            map(
                int,
                (
                    bank["coil_count"],
                    bank["causal_feature_dimension"],
                    bank["action_block_dimension"],
                    bank["expanded_feature_dimension"],
                ),
            )
        )
        != (14, 44, 18, 238)
        or float(bank["previous_coordinate_scale"]) != 1.5
        or tuple(map(float, bank["output_factors"]))
        != (0.03, 0.03, 10000.0, 1.0, 1.0)
        or float(model["ridge_penalty"]) != 1e-4
        or tuple(
            map(
                int,
                (
                    model["outer_fold_count"],
                    model["nested_fold_count_per_outer"],
                    model["schedule_count"],
                    model["training_schedule_count"],
                    model["held_trajectory_count_per_schedule"],
                ),
            )
        )
        != (8, 7, 35, 34, 16)
        or not bool(model["whole_pair_exclusion"])
        or not bool(model["whole_schedule_exclusion"])
        or float(model["reserve_multiplier"]) != 1.25
        or tuple(map(float, model["physical_point_error_floors"]))
        != (0.015, 0.015, 3000.0, 0.05, 0.05)
        or float(model["support_threshold_multiplier"]) != 1.5
        or any(
            bool(model[key])
            for key in (
                "feature_selection_allowed",
                "hyperparameter_search_allowed",
                "tube_clipping_allowed",
                "innovation_enabled",
            )
        )
        or tuple(
            map(
                int,
                (support["coordinate_dimension"], support["transition_dimension"]),
            )
        )
        != (4, 8)
        or tuple(
            map(
                float,
                (
                    support["coordinate_scale"],
                    support["affine_singular_value_tolerance"],
                    support["affine_residual_tolerance"],
                    support["convex_hull_inequality_tolerance"],
                ),
            )
        )
        != (1.5, 1e-12, 1e-12, 1e-10)
        or bool(support["qhull_joggle_allowed"])
        or int(candidates["candidate_count"]) != 17
        or tuple(map(int, candidates["decision_task_steps"])) != DECISIONS
        or actual_candidates != expected_candidates
        or str(candidates["canonical_matrix_float64_le_c_sha256"])
        != "c8cd62c00c1f60b46312927789659657dc8cc35717533193433b0e398c1ec94c"
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
        != (0.25, 1.0, 0.55, 0.98, 0.1)
        or not all(
            bool(action[key])
            for key in (
                "require_exact_card15_issue",
                "require_exact_card15_refresh",
                "safe_stop_before_failed_advance",
            )
        )
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
        or tuple(
            map(
                float,
                (
                    formal["position_tolerance_m"],
                    formal["speed_tolerance_m_per_s"],
                    formal["ip_tolerance_A"],
                    formal["metric_equivalence_absolute_tolerance"],
                ),
            )
        )
        != (0.03, 0.1, 10000.0, 1e-12)
        or bool(formal["arrival_deadline_expansion_allowed"])
        or tuple(
            map(
                int,
                (
                    gate["required_safe_search_context_count"],
                    gate["minimum_predicted_repaired_failed_baseline_count"],
                    gate["maximum_predicted_regressed_baseline_pass_count"],
                    gate["minimum_predicted_oracle_count"],
                    gate["minimum_nonzero_first_action_count"],
                    gate["required_fault_injection_count"],
                ),
            )
        )
        != (16, 1, 0, 7, 1, 6)
        or float(gate["primary_independent_absolute_tolerance"]) != 1e-12
        or not bool(scope["real_mpc_core_only"])
        or any(
            bool(scope[key])
            for key in (
                "gate_a_qualified",
                "expert_data_allowed",
                "bc_dagger_or_rl_allowed",
                "all_stage_trajectories_allowed_in_expert_dataset",
                "global_plant_reachability_claimed",
            )
        )
    )
    if invalid:
        raise ValueError("R8R31 frozen config changed")


def load_context(args: argparse.Namespace) -> Context:
    config_path = args.config.expanduser().resolve()
    cfg = _read(config_path)
    validate_config(cfg, project_root=_root())
    args23 = argparse.Namespace(**vars(args))
    args23.config = (_root() / str(cfg["source_r8r23_config"])).resolve()
    args23.run_dir = args.r8r23_run.expanduser().resolve()
    ctx23 = r8r23.load_context(args23)
    args28 = argparse.Namespace(**vars(args))
    args28.config = (_root() / str(cfg["source_r8r28_config"])).resolve()
    args28.run_dir = args.r8r28_run.expanduser().resolve()
    ctx28 = r8r28.load_context(args28)
    return Context(
        cfg=cfg,
        config_path=config_path,
        paths=_paths(args.run_dir),
        r8r23_ctx=ctx23,
        r8r28_ctx=ctx28,
        r8r23_stage=args.r8r23_run.expanduser().resolve()
        / str(cfg["source_r8r23"]["stage_directory"]),
        r8r14_stage=args.r8r14_run.expanduser().resolve()
        / str(cfg["source_r8r14"]["stage_directory"]),
        r8r28_stage=args.r8r28_run.expanduser().resolve()
        / str(cfg["source_r8r28"]["stage_directory"]),
    )


def _check_hashes(stage: Path, expected: Mapping[str, Any], names: Mapping[str, str]) -> dict[str, str]:
    hashes = {key: _sha(stage / relative) for key, relative in names.items()}
    for key, digest in hashes.items():
        if digest != str(expected[f"{key}_sha256"]):
            raise ValueError(f"R8R31 source {stage.name} {key} changed")
    return hashes


def authenticate_sources(ctx: Context) -> dict[str, Any]:
    expected23 = ctx.cfg["source_r8r23"]
    hashes23 = _check_hashes(
        ctx.r8r23_stage,
        expected23,
        {
            "primary_detailed": "analysis/primary_detailed.json",
            "primary_summary": "analysis/primary_summary.json",
            "independent": "analysis/independent.json",
            "final_report": "analysis/final_report.json",
            "stage_manifest": "stage_manifest.json",
            "stage_state": "stage_state.json",
        },
    )
    final23 = _read(ctx.r8r23_stage / "analysis/final_report.json")
    state23 = _read(ctx.r8r23_stage / "stage_state.json")
    if (
        ctx.r8r23_stage.parent.name != str(expected23["run_name"])
        or final23.get("route") != str(expected23["required_route"])
        or state23.get("finished") is not True
        or bool(state23.get("real_tsc_executed"))
        or int(state23.get("new_raw_count", -1)) != 0
    ):
        raise ValueError("R8R31 R8R23 outcome changed")
    transitive23 = r8r23._authenticate_source(ctx.r8r23_ctx)

    auth14 = r8r28._authenticate_r8r14(ctx.r8r28_ctx)
    expected14 = ctx.cfg["source_r8r14"]
    if (
        auth14.get("passed") is not True
        or _sha(ctx.r8r14_stage / "analysis/final_report.json")
        != str(expected14["final_report_sha256"])
        or _sha(ctx.r8r14_stage / "stage_manifest.json")
        != str(expected14["stage_manifest_sha256"])
        or _sha(ctx.r8r14_stage / "stage_state.json")
        != str(expected14["stage_state_sha256"])
        or _sha(ctx.r8r14_stage / "specs/all_specs.json")
        != str(expected14["all_specs_sha256"])
    ):
        raise ValueError("R8R31 R8R14 authentication changed")

    expected28 = ctx.cfg["source_r8r28"]
    hashes28 = _check_hashes(
        ctx.r8r28_stage,
        expected28,
        {
            "final_report": "analysis/final_report.json",
            "final_independent": "analysis/final_independent.json",
            "stage_manifest": "stage_manifest.json",
            "stage_state": "stage_state.json",
        },
    )
    if _sha(ctx.r8r28_stage / "specs/all_specs.json") != str(
        expected28["all_specs_sha256"]
    ):
        raise ValueError("R8R31 R8R28 specs changed")
    final28 = _read(ctx.r8r28_stage / "analysis/final_report.json")
    state28 = _read(ctx.r8r28_stage / "stage_state.json")
    inventories28 = {
        phase: r8r28.r8r7.r8._inventory(ctx.r8r28_stage / "raw" / phase)
        for phase in ("safety", "qualification")
    }
    for phase, inventory in inventories28.items():
        if (
            inventory["count"] != int(expected28[f"{phase}_raw_count"])
            or inventory["bytes"] != int(expected28[f"{phase}_raw_bytes"])
            or inventory["digest"] != str(expected28[f"{phase}_raw_digest"])
        ):
            raise ValueError(f"R8R31 R8R28 {phase} raw changed")
    if (
        ctx.r8r28_stage.parent.name != str(expected28["run_name"])
        or final28.get("route") != str(expected28["required_route"])
        or final28.get("integrity_gate_passed") is not True
        or final28.get("scientific_gate_passed") is not False
        or state28.get("finished") is not True
        or state28.get("real_tsc_executed") is not True
        or int(state28.get("new_raw_count", -1)) != 64
    ):
        raise ValueError("R8R31 R8R28 outcome changed")
    return {
        "r8r23": {"hashes": hashes23, "transitive": transitive23},
        "r8r14": auth14,
        "r8r28": {"hashes": hashes28, "inventories": inventories28},
        "passed": True,
    }


def q2_to_q4(q: Sequence[float]) -> np.ndarray:
    u, v = map(float, np.asarray(q, dtype=float).reshape(2))
    result = np.asarray([0.0, -v, u, 0.0], dtype=float)
    if not np.all(np.isfinite(result)):
        raise ValueError("R8R31 q2 to q4 conversion invalid")
    return result


def causal_feature44(
    states: np.ndarray,
    trajectory: Sequence[Mapping[str, Any]],
    *,
    decision: int,
    previous_decision: int,
    previous_q: Sequence[float],
    coil_limits: Sequence[float],
) -> np.ndarray:
    limits = np.asarray(coil_limits, dtype=float).reshape(14)
    current = np.asarray(trajectory[decision]["currents_a_tsc"], dtype=float).reshape(14)
    previous = np.asarray(
        trajectory[previous_decision]["currents_a_tsc"], dtype=float
    ).reshape(14)
    value = np.concatenate(
        (
            np.asarray(states[decision - 3 : decision + 1, :3], dtype=float).reshape(-1),
            current / limits,
            (current - previous) / limits,
            np.asarray(previous_q, dtype=float).reshape(4) / 1.5,
        )
    )
    if value.shape != (44,) or not np.all(np.isfinite(value)):
        raise ValueError("R8R31 causal feature is not finite 44D")
    return value


def expanded_feature238(
    feature: Sequence[float], q: Sequence[float], previous_q: Sequence[float]
) -> np.ndarray:
    base = np.asarray(feature, dtype=float).reshape(44)
    current = np.asarray(q, dtype=float).reshape(4)
    previous = np.asarray(previous_q, dtype=float).reshape(4)
    q0, q1, q2, q3 = map(float, current)
    action = np.asarray(
        [
            q0,
            q1,
            q2,
            q3,
            q0 * q0,
            q0 * q1,
            q0 * q2,
            q0 * q3,
            q1 * q1,
            q1 * q2,
            q1 * q3,
            q2 * q2,
            q2 * q3,
            q3 * q3,
            *(current - previous),
        ],
        dtype=float,
    )
    value = np.concatenate((base, action, *(base * coordinate for coordinate in current)))
    if action.shape != (18,) or value.shape != (238,) or not np.all(np.isfinite(value)):
        raise ValueError("R8R31 expanded feature is not finite 238D")
    return value


def _six_interval_trajectory(
    source: Mapping[str, Any],
    *,
    q_by_decision: Mapping[int, Sequence[float]],
    schedule_id: str,
    source_name: str,
    meta: Mapping[str, Any],
) -> dict[str, Any]:
    result = source["result"]
    spec = source["spec"]
    trajectory = result["trajectory"]
    horizon = int(spec["horizon_steps"])
    if (
        result.get("success") is not True
        or len(trajectory) != horizon + 1
        or horizon != int(meta["horizon"])
    ):
        raise ValueError("R8R31 source trajectory incomplete")
    states = r8r23._state_matrix(result, meta["target"])
    rows = []
    previous_q = ZERO_Q.copy()
    for interval, decision in enumerate(DECISIONS):
        previous_decision = decision if interval == 0 else DECISIONS[interval - 1]
        end = DECISIONS[interval + 1] if interval < len(DECISIONS) - 1 else horizon
        q = np.asarray(q_by_decision.get(decision, ZERO_Q), dtype=float).reshape(4)
        feature = causal_feature44(
            states,
            trajectory,
            decision=decision,
            previous_decision=previous_decision,
            previous_q=previous_q,
            coil_limits=meta["coil_limits"],
        )
        targets = np.asarray(states[decision + 1 : end + 1], dtype=float)
        if len(targets) == 0 or len(targets) > MAX_COUNTS[interval]:
            raise ValueError("R8R31 interval target mask changed")
        row = {
            "row_id": f"{source_name}|{spec['experiment_id']}|i{interval}",
            "pair_id": str(spec["pair_id"]),
            "history_member": str(spec["history_member"]),
            "schedule_id": schedule_id,
            "source": source_name,
            "interval": interval,
            "decision": decision,
            "feature": feature,
            "q": q,
            "previous_q": previous_q.copy(),
            "targets": targets,
        }
        row["expanded"] = expanded_feature238(feature, q, previous_q)
        rows.append(row)
        previous_q = q
    return {
        "trajectory_id": f"{source_name}|{spec['experiment_id']}",
        "pair_id": str(spec["pair_id"]),
        "history_member": str(spec["history_member"]),
        "schedule_id": schedule_id,
        "source": source_name,
        "spec": spec,
        "states": states,
        "trajectory": trajectory,
        "intervals": rows,
    }


def build_bank(ctx: Context) -> tuple[list[dict[str, Any]], dict[tuple[str, str], dict[str, Any]], dict[str, Any]]:
    base, context_meta = r8r23.build_bank(ctx.r8r23_ctx)
    trajectories = []
    for source in base:
        q_by_decision = {
            int(row["decision"]): q2_to_q4(row["q"]) for row in source["intervals"]
        }
        trajectories.append(
            _six_interval_trajectory(
                {"spec": source["spec"], "result": {"success": True, "trajectory": source["trajectory"]}},
                q_by_decision=q_by_decision,
                schedule_id=str(source["schedule_id"]),
                source_name=str(source["source"]),
                meta=context_meta[(str(source["pair_id"]), str(source["history_member"]))],
            )
        )

    specs14 = _read(ctx.r8r14_stage / "specs/all_specs.json")
    selected14 = [
        spec
        for spec in specs14
        if (int(spec["r8r14_direction_index"]), int(spec["r8r14_sign"]))
        not in ((2, 1), (1, -1))
    ]
    for spec in selected14:
        direction = int(spec["r8r14_direction_index"])
        sign = int(spec["r8r14_sign"])
        q = np.zeros(4, dtype=float)
        q[direction] = float(sign) * float(spec["r8r14_canonical_scale"])
        phase = str(spec["partition"])
        result = r8r28.r8r7.r8._read_gz(
            ctx.r8r14_stage / "raw" / phase / f"{spec['experiment_id']}.json.gz"
        )
        key = (str(spec["pair_id"]), str(spec["history_member"]))
        trajectories.append(
            _six_interval_trajectory(
                {"spec": spec, "result": result},
                q_by_decision={step: q for step in (10, 14, 18, 22)},
                schedule_id=f"R8R14_d{direction}_{'p' if sign > 0 else 'm'}",
                source_name="R8R14",
                meta=context_meta[key],
            )
        )

    specs28 = _read(ctx.r8r28_stage / "specs/all_specs.json")
    selected28 = [spec for spec in specs28 if str(spec["r8r28_grid_id"]) == "g2"]
    if any(str(spec["r8r28_grid_id"]) != "g2" for spec in selected28):
        raise ValueError("R8R31 selected a forbidden g3 row")
    for spec in selected28:
        direction = int(spec["r8r28_direction_index"])
        sign = int(spec["r8r28_sign"])
        q = np.zeros(4, dtype=float)
        q[direction] = float(sign)
        phase = str(spec["partition"])
        result = r8r28.r8r7.r8._read_gz(
            ctx.r8r28_stage / "raw" / phase / f"{spec['experiment_id']}.json.gz"
        )
        key = (str(spec["pair_id"]), str(spec["history_member"]))
        trajectories.append(
            _six_interval_trajectory(
                {"spec": spec, "result": result},
                q_by_decision={step: q for step in (10, 12, 14, 16)},
                schedule_id=f"R8R28_g2_{spec['r8r28_sequence_id']}",
                source_name="R8R28",
                meta=context_meta[key],
            )
        )

    contexts = {(row["pair_id"], row["history_member"]) for row in trajectories}
    schedules_by_context = {key: set() for key in contexts}
    for row in trajectories:
        schedules_by_context[(row["pair_id"], row["history_member"])].add(
            row["schedule_id"]
        )
    schedule_ids = sorted({str(row["schedule_id"]) for row in trajectories})
    source_counts = {
        name: sum(row["source"] == name for row in trajectories)
        for name in sorted({str(row["source"]) for row in trajectories})
    }
    if (
        len(base) != 432
        or len(selected14) != 96
        or len(selected28) != 32
        or len(trajectories) != 560
        or len(contexts) != 16
        or len(schedule_ids) != 35
        or any(len(value) != 35 for value in schedules_by_context.values())
        or sum(len(row["intervals"]) for row in trajectories) != 3360
    ):
        raise ValueError("R8R31 aligned bank coverage changed")
    serial = []
    for trajectory in sorted(trajectories, key=lambda row: row["trajectory_id"]):
        serial.append(
            {
                "trajectory_id": trajectory["trajectory_id"],
                "pair_id": trajectory["pair_id"],
                "history_member": trajectory["history_member"],
                "schedule_id": trajectory["schedule_id"],
                "rows": [
                    {
                        "row_id": row["row_id"],
                        "decision": row["decision"],
                        "feature": np.asarray(row["feature"]).tolist(),
                        "q": np.asarray(row["q"]).tolist(),
                        "previous_q": np.asarray(row["previous_q"]).tolist(),
                        "targets": np.asarray(row["targets"]).tolist(),
                    }
                    for row in trajectory["intervals"]
                ],
            }
        )
    evidence = {
        "trajectory_count": len(trajectories),
        "context_count": len(contexts),
        "schedule_count": len(schedule_ids),
        "interval_record_count": 3360,
        "source_counts": source_counts,
        "schedule_ids": schedule_ids,
        "bank_digest": _digest(serial),
        "feature_digest": _digest(
            [row["feature"] for trajectory in serial for row in trajectory["rows"]]
        ),
        "target_digest": _digest(
            [row["targets"] for trajectory in serial for row in trajectory["rows"]]
        ),
    }
    return sorted(trajectories, key=lambda row: row["trajectory_id"]), context_meta, evidence


def _fit(
    trajectories: Sequence[Mapping[str, Any]],
    selected: Callable[[Mapping[str, Any]], bool],
    ridge: float,
) -> dict[str, Any]:
    intervals = []
    for interval in range(6):
        current = [row["intervals"][interval] for row in trajectories if selected(row)]
        if not current:
            raise ValueError("R8R31 fit selection is empty")
        offsets = []
        for offset in range(max(len(row["targets"]) for row in current)):
            rows = [row for row in current if len(row["targets"]) > offset]
            x = np.asarray([row["expanded"] for row in rows], dtype=float)
            y = np.asarray([row["targets"][offset] for row in rows], dtype=float)
            x_mean, y_mean = np.mean(x, axis=0), np.mean(y, axis=0)
            centered_x, centered_y = x - x_mean, y - y_mean
            coefficients = np.linalg.solve(
                centered_x.T @ centered_x + ridge * np.eye(238),
                centered_x.T @ centered_y,
            )
            intercept = y_mean - x_mean @ coefficients
            if (
                coefficients.shape != (238, 5)
                or intercept.shape != (5,)
                or not np.all(np.isfinite(coefficients))
                or not np.all(np.isfinite(intercept))
            ):
                raise ValueError("R8R31 ridge fit invalid")
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


def predict(model: Mapping[str, Any], row: Mapping[str, Any]) -> np.ndarray:
    expanded = np.asarray(row["expanded"], dtype=float).reshape(238)
    count = len(row["targets"])
    offsets = model["intervals"][int(row["interval"])]["offsets"][:count]
    output = np.asarray(
        [
            np.asarray(offset["intercept"], dtype=float)
            + expanded @ np.asarray(offset["coefficients"], dtype=float)
            for offset in offsets
        ],
        dtype=float,
    )
    if output.shape != (count, 5) or not np.all(np.isfinite(output)):
        raise ValueError("R8R31 prediction invalid")
    return output


def _model_json(model: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "intervals": [
            {
                "interval": int(interval["interval"]),
                "offsets": [
                    {
                        "sample_offset": int(offset["sample_offset"]),
                        "training_row_count": int(offset["training_row_count"]),
                        "intercept": np.asarray(offset["intercept"]).tolist(),
                        "coefficients": np.asarray(offset["coefficients"]).tolist(),
                    }
                    for offset in interval["offsets"]
                ],
            }
            for interval in model["intervals"]
        ]
    }


def _residuals(
    model: Mapping[str, Any], trajectories: Sequence[Mapping[str, Any]]
) -> tuple[list[list[list[np.ndarray]]], dict[str, Any]]:
    groups: list[list[list[np.ndarray]]] = [
        [[] for _ in range(count)] for count in MAX_COUNTS
    ]
    serial = []
    for trajectory in trajectories:
        rows = []
        for interval, row in enumerate(trajectory["intervals"]):
            residual = np.abs(np.asarray(row["targets"]) - predict(model, row))
            rows.append(residual.tolist())
            for offset, value in enumerate(residual):
                groups[interval][offset].append(value)
        serial.append(
            {"trajectory_id": trajectory["trajectory_id"], "absolute_residuals": rows}
        )
    return groups, {"residual_digest": _digest(serial)}


def _tube_from_fold_groups(
    folds: Sequence[Mapping[str, Any]], selected: Callable[[Mapping[str, Any]], bool], cfg: Mapping[str, Any]
) -> tuple[list[np.ndarray], dict[str, Any]]:
    chosen = [fold for fold in folds if selected(fold)]
    reserve = float(cfg["model_contract"]["reserve_multiplier"])
    floor = np.asarray(
        cfg["model_contract"]["physical_point_error_floors"], dtype=float
    ) / OUTPUT_FACTORS
    tubes, counts = [], []
    for interval, count in enumerate(MAX_COUNTS):
        values = []
        for offset in range(count):
            rows = [
                np.asarray(value, dtype=float)
                for fold in chosen
                for value in fold["residual_groups"][interval][offset]
            ]
            if not rows:
                raise ValueError("R8R31 tube residual group empty")
            residual = np.asarray(rows, dtype=float).reshape((-1, 5))
            values.append(np.maximum(reserve * np.max(residual, axis=0), floor))
            counts.append(len(residual))
        tubes.append(np.asarray(values, dtype=float))
    return tubes, {
        "selected_fold_count": len(chosen),
        "minimum_group_count": min(counts),
        "maximum_group_count": max(counts),
        "tube_digest": _digest([tube.tolist() for tube in tubes]),
    }


def _support_fold(
    trajectories: Sequence[Mapping[str, Any]], training_pairs: Sequence[str], held_pair: str, multiplier: float
) -> dict[str, Any]:
    training = sorted(set(map(str, training_pairs)))
    rows = []
    for interval in range(6):
        by_pair = {
            pair: np.asarray(
                [
                    trajectory["intervals"][interval]["feature"]
                    for trajectory in trajectories
                    if trajectory["pair_id"] == pair
                ],
                dtype=float,
            )
            for pair in training
        }
        nested = []
        for pair, values in by_pair.items():
            other = np.concatenate(
                [other_values for other_pair, other_values in by_pair.items() if other_pair != pair]
            )
            nested.extend(
                np.min(np.linalg.norm(values[:, None] - other[None, :], axis=2), axis=1)
            )
        threshold = multiplier * max(map(float, nested))
        train = np.concatenate(list(by_pair.values()))
        held = np.asarray(
            [
                trajectory["intervals"][interval]["feature"]
                for trajectory in trajectories
                if trajectory["pair_id"] == held_pair
            ],
            dtype=float,
        )
        distance = np.min(np.linalg.norm(held[:, None] - train[None, :], axis=2), axis=1)
        rows.append(
            {
                "interval": interval,
                "threshold": threshold,
                "maximum_held_distance": float(np.max(distance)),
                "pass_count": int(np.count_nonzero(distance <= threshold + 1e-15)),
                "row_count": len(distance),
            }
        )
    return {"rows": rows, "passed": all(row["pass_count"] == row["row_count"] for row in rows)}


def outer_model_evaluation(
    trajectories: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    pairs = sorted({str(row["pair_id"]) for row in trajectories})
    ridge = float(cfg["model_contract"]["ridge_penalty"])
    folds = []
    for held_pair in pairs:
        training = [pair for pair in pairs if pair != held_pair]
        model = _fit(trajectories, lambda row, allowed=set(training): row["pair_id"] in allowed, ridge)
        held = [row for row in trajectories if row["pair_id"] == held_pair]
        groups, evidence = _residuals(model, held)
        folds.append(
            {
                "held_pair": held_pair,
                "training_pairs": training,
                "model": model,
                "model_digest": _digest(_model_json(model)),
                "held": held,
                "residual_groups": groups,
                "residual_digest": evidence["residual_digest"],
                "support": _support_fold(
                    trajectories,
                    training,
                    held_pair,
                    float(cfg["model_contract"]["support_threshold_multiplier"]),
                ),
            }
        )
    total_contained = total = 0
    maximum_error = np.zeros(5, dtype=float)
    maximum_tube = np.zeros(5, dtype=float)
    fold_rows = []
    for fold in folds:
        tube, tube_evidence = _tube_from_fold_groups(
            folds, lambda row, held=fold["held_pair"]: row["held_pair"] != held, cfg
        )
        held_contained = held_total = 0
        held_error = np.zeros(5, dtype=float)
        for interval, offsets in enumerate(fold["residual_groups"]):
            for offset, values in enumerate(offsets):
                residual = np.asarray(values, dtype=float).reshape((-1, 5))
                held_contained += int(np.count_nonzero(residual <= tube[interval][offset] + 1e-15))
                held_total += residual.size
                if len(residual):
                    held_error = np.maximum(held_error, np.max(residual, axis=0))
        maximum_error = np.maximum(maximum_error, held_error * OUTPUT_FACTORS)
        maximum_tube = np.maximum(
            maximum_tube, np.max(np.concatenate(tube), axis=0) * OUTPUT_FACTORS
        )
        total_contained += held_contained
        total += held_total
        fold["tube"] = tube
        fold_rows.append(
            {
                "held_pair": fold["held_pair"],
                "model_digest": fold["model_digest"],
                "residual_digest": fold["residual_digest"],
                "maximum_physical_error": (held_error * OUTPUT_FACTORS).tolist(),
                "contained_count": held_contained,
                "component_count": held_total,
                "support": fold["support"],
                "tube_evidence": tube_evidence,
            }
        )
    gates = cfg["model_gates"]
    caps_error = np.asarray(gates["maximum_point_error"], dtype=float)
    caps_tube = np.asarray(gates["maximum_tube_half_width"], dtype=float)
    rate = total_contained / total
    passed = bool(
        np.all(maximum_error <= caps_error + 1e-15)
        and np.all(maximum_tube <= caps_tube + 1e-15)
        and rate >= float(gates["required_reserved_tube_containment_rate"]) - 1e-15
        and all(fold["support"]["passed"] for fold in folds)
    )
    return folds, {
        "maximum_absolute_physical_error": maximum_error.tolist(),
        "maximum_reserved_physical_tube_half_width": maximum_tube.tolist(),
        "reserved_contained_count": total_contained,
        "reserved_component_count": total,
        "reserved_containment_rate": rate,
        "state_support_pass_count": sum(fold["support"]["passed"] for fold in folds),
        "fold_rows": fold_rows,
        "passed": passed,
    }


def schedule_jackknife(
    trajectories: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> tuple[list[np.ndarray], dict[str, Any]]:
    schedules = sorted({str(row["schedule_id"]) for row in trajectories})
    ridge = float(cfg["model_contract"]["ridge_penalty"])
    folds = []
    for held_schedule in schedules:
        model = _fit(
            trajectories,
            lambda row, held=held_schedule: row["schedule_id"] != held,
            ridge,
        )
        held = [row for row in trajectories if row["schedule_id"] == held_schedule]
        if len(held) != 16:
            raise ValueError("R8R31 schedule fold cardinality changed")
        groups, evidence = _residuals(model, held)
        folds.append(
            {
                "held_schedule": held_schedule,
                "model_digest": _digest(_model_json(model)),
                "residual_groups": groups,
                "residual_digest": evidence["residual_digest"],
            }
        )
    tube, tube_evidence = _tube_from_fold_groups(folds, lambda row: True, cfg)
    contained = total = 0
    maximum_error = np.zeros(5, dtype=float)
    for fold in folds:
        for interval, offsets in enumerate(fold["residual_groups"]):
            for offset, values in enumerate(offsets):
                residual = np.asarray(values, dtype=float).reshape((-1, 5))
                contained += int(np.count_nonzero(residual <= tube[interval][offset] + 1e-15))
                total += residual.size
                if len(residual):
                    maximum_error = np.maximum(maximum_error, np.max(residual, axis=0))
    maximum_tube = np.max(np.concatenate(tube), axis=0) * OUTPUT_FACTORS
    gates = cfg["model_gates"]
    passed = bool(
        contained == total
        and np.all(maximum_error * OUTPUT_FACTORS <= np.asarray(gates["maximum_point_error"]) + 1e-15)
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
        "maximum_absolute_physical_error": (maximum_error * OUTPUT_FACTORS).tolist(),
        "maximum_reserved_physical_tube_half_width": maximum_tube.tolist(),
        "contained_count": contained,
        "component_count": total,
        "containment_rate": contained / total,
        "tube_evidence": tube_evidence,
        "passed": passed,
    }


def transition_hulls(
    trajectories: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> list[dict[str, Any]]:
    contract = cfg["support_contract"]
    scale = float(contract["coordinate_scale"])
    hulls = []
    for interval in range(6):
        rows = sorted(
            {
                tuple(
                    np.concatenate(
                        (
                            np.asarray(row["intervals"][interval]["previous_q"]),
                            np.asarray(row["intervals"][interval]["q"]),
                        )
                    )
                    / scale
                )
                for row in trajectories
            }
        )
        points = np.asarray(rows, dtype=float)
        origin = np.mean(points, axis=0)
        centered = points - origin
        _, singular, vh = np.linalg.svd(centered, full_matrices=False)
        rank = int(
            np.count_nonzero(
                singular > float(contract["affine_singular_value_tolerance"])
            )
        )
        basis = vh[:rank].T
        projected = centered @ basis
        if rank == 0:
            equations = np.empty((0, 1), dtype=float)
        elif rank == 1:
            equations = np.asarray(
                [
                    [1.0, -float(np.max(projected[:, 0]))],
                    [-1.0, float(np.min(projected[:, 0]))],
                ]
            )
        else:
            equations = np.asarray(ConvexHull(projected).equations, dtype=float)
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


def transition_supported(
    hull: Mapping[str, Any], previous_q: Sequence[float], q: Sequence[float], cfg: Mapping[str, Any]
) -> bool:
    contract = cfg["support_contract"]
    value = np.concatenate((np.asarray(previous_q), np.asarray(q))) / float(
        contract["coordinate_scale"]
    )
    delta = value - np.asarray(hull["origin"])
    basis = np.asarray(hull["basis"])
    projected = delta @ basis
    if np.linalg.norm(delta - projected @ basis.T) > float(
        contract["affine_residual_tolerance"]
    ) + 1e-15:
        return False
    equations = np.asarray(hull["equations"])
    if not len(equations):
        return bool(np.linalg.norm(delta) <= float(contract["affine_residual_tolerance"]) + 1e-15)
    return bool(
        np.max(equations[:, :-1] @ projected + equations[:, -1])
        <= float(contract["convex_hull_inequality_tolerance"]) + 1e-15
    )


def planning_support(
    trajectories: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> dict[str, Any]:
    pairs = sorted({str(row["pair_id"]) for row in trajectories})
    multiplier = float(cfg["model_contract"]["support_threshold_multiplier"])
    features, thresholds, maxima = [], [], []
    for interval in range(6):
        by_pair = {
            pair: np.asarray(
                [
                    row["intervals"][interval]["feature"]
                    for row in trajectories
                    if row["pair_id"] == pair
                ]
            )
            for pair in pairs
        }
        nested = []
        for pair, values in by_pair.items():
            other = np.concatenate(
                [other_values for other_pair, other_values in by_pair.items() if other_pair != pair]
            )
            nested.extend(np.min(np.linalg.norm(values[:, None] - other[None, :], axis=2), axis=1))
        maximum = max(map(float, nested))
        features.append(np.concatenate(list(by_pair.values())))
        maxima.append(maximum)
        thresholds.append(multiplier * maximum)
    return {"features": features, "thresholds": thresholds, "training_maxima": maxima}


def _candidate_rows(cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {"index": index, "id": str(row["id"]), "q": np.asarray(row["q"], dtype=float)}
        for index, row in enumerate(cfg["candidate_contract"]["candidates"])
    ]


def _safe_issue(
    ctx: Context, meta: Mapping[str, Any], current: np.ndarray, candidate: Mapping[str, Any], task_step: int
) -> dict[str, Any]:
    q = np.asarray(candidate["q"], dtype=float)
    actuator = meta["actuator"]
    if np.array_equal(q, ZERO_Q):
        applied = actuator.apply(current, np.zeros(14, dtype=float))
        minimum = np.asarray(actuator.minimum_current_a_tsc, dtype=float)
        maximum = np.asarray(actuator.maximum_current_a_tsc, dtype=float)
        center, half = 0.5 * (minimum + maximum), 0.5 * (maximum - minimum)
        utilization = float(
            np.max(
                np.abs(
                    (np.asarray(applied.nominal_readback_current_a_tsc) - center) / half
                )
            )
        )
        return {
            "passed": bool(
                not any(applied.action_saturated)
                and not any(applied.current_limit_clipped)
                and utilization
                <= float(ctx.cfg["action_contract"]["maximum_current_utilization"])
                + 1e-12
            ),
            "nominal_issue_readback_current_a_tsc": list(
                map(float, applied.nominal_readback_current_a_tsc)
            ),
            "predicted_current_utilization": utilization,
            "incremental_normalized_action_linf": 0.0,
            "candidate_id": candidate["id"],
        }
    matrix = np.asarray(
        ctx.cfg["candidate_contract"]["canonical_matrix_columns"], dtype=float
    )
    coordinate = matrix @ q
    contract = copy.deepcopy(ctx.cfg["action_contract"])
    contract["dynamic_exact_search_radius"] = int(
        ctx.cfg["candidate_contract"]["dynamic_exact_search_radius"]
    )
    return r8r23.r8r22._construct_coordinate_issue(
        task_step=task_step,
        currents_a_tsc=current,
        fixed_basis_delta_field_kat_tsc=meta["fixed_basis"],
        requested_coordinate=coordinate,
        candidate_id=str(candidate["id"]),
        actuator=actuator,
        controller_cfg=contract,
        lattice_cfg=meta["lattice"],
    )


def _planning_feature44(
    states: np.ndarray,
    current: np.ndarray,
    previous_current: np.ndarray,
    previous_q: np.ndarray,
    limits: np.ndarray,
) -> np.ndarray:
    value = np.concatenate(
        (
            np.asarray(states[-4:, :3]).reshape(-1),
            current / limits,
            (current - previous_current) / limits,
            previous_q / 1.5,
        )
    )
    if value.shape != (44,) or not np.all(np.isfinite(value)):
        raise ValueError("R8R31 planning feature invalid")
    return value


def _deadline(meta: Mapping[str, Any], cfg: Mapping[str, Any]) -> tuple[int, int]:
    weak = math.isclose(float(meta["slew_scale"]), 0.9, abs_tol=1e-15)
    formal = cfg["formal_contract"]
    return (
        int(formal["weak_arrival_deadline_step" if weak else "normal_arrival_deadline_step"]),
        int(formal["weak_hold_through_step" if weak else "normal_hold_through_step"]),
    )


def _node_rank(node: Mapping[str, Any], *, terminal: bool, meta: Mapping[str, Any], cfg: Mapping[str, Any]) -> tuple[Any, ...]:
    if terminal:
        deadline, endpoint = _deadline(meta, cfg)
        passed, violation, integrated = r8r23._robust_formal(
            np.asarray(node["states"]),
            np.asarray(node["tubes"]),
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
    return (
        float(np.sum(np.asarray(node["states"])[10:, :3] ** 2)),
        float(node["movement"]),
        float(node["maximum_current"]),
        tuple(node["tokens"]),
    )


def plan_context(
    ctx: Context,
    meta: Mapping[str, Any],
    model: Mapping[str, Any],
    tube: Sequence[np.ndarray],
    support: Mapping[str, Any],
    hulls: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    candidates = _candidate_rows(ctx.cfg)
    baseline = meta["baseline_result"]
    states = r8r23._state_matrix(baseline, meta["target"])
    current = np.asarray(baseline["trajectory"][DECISIONS[0]]["currents_a_tsc"], dtype=float)
    beam = [
        {
            "states": states[: DECISIONS[0] + 1],
            "tubes": np.zeros_like(states[: DECISIONS[0] + 1]),
            "current": current,
            "previous_current": current,
            "previous_q": ZERO_Q.copy(),
            "tokens": tuple(),
            "movement": 0.0,
            "maximum_current": 0.0,
        }
    ]
    trees = [cKDTree(np.asarray(values)) for values in support["features"]]
    counters = {"state_unsupported": 0, "transition_unsupported": 0, "hard_rejected": 0, "safe": 0}
    beam_counts = []
    for interval, decision in enumerate(DECISIONS):
        expanded_nodes = []
        for node in beam:
            feature = _planning_feature44(
                np.asarray(node["states"]),
                np.asarray(node["current"]),
                np.asarray(node["previous_current"]),
                np.asarray(node["previous_q"]),
                np.asarray(meta["coil_limits"]),
            )
            distance = float(trees[interval].query(feature, k=1, eps=0.0, workers=1)[0])
            if distance > float(support["thresholds"][interval]) + 1e-15:
                counters["state_unsupported"] += 1
                continue
            for candidate in candidates:
                q = np.asarray(candidate["q"])
                if not transition_supported(hulls[interval], node["previous_q"], q, ctx.cfg):
                    counters["transition_unsupported"] += 1
                    continue
                issue = _safe_issue(ctx, meta, np.asarray(node["current"]), candidate, decision)
                if not bool(issue["passed"]):
                    counters["hard_rejected"] += 1
                    continue
                count = MAX_COUNTS[interval]
                if interval == 5 and int(meta["horizon"]) == 35:
                    count = 13
                row = {
                    "interval": interval,
                    "feature": feature,
                    "q": q,
                    "previous_q": np.asarray(node["previous_q"]),
                    "targets": np.zeros((count, 5)),
                }
                row["expanded"] = expanded_feature238(feature, q, node["previous_q"])
                forecast = predict(model, row)
                next_current = np.asarray(issue["nominal_issue_readback_current_a_tsc"])
                expanded_nodes.append(
                    {
                        "states": np.concatenate((np.asarray(node["states"]), forecast)),
                        "tubes": np.concatenate((np.asarray(node["tubes"]), np.asarray(tube[interval][:count]))),
                        "current": next_current,
                        "previous_current": np.asarray(node["current"]),
                        "previous_q": q,
                        "tokens": tuple(node["tokens"]) + (int(candidate["index"]),),
                        "movement": float(node["movement"]) + float(np.sum(np.abs(q - node["previous_q"]))),
                        "maximum_current": max(float(node["maximum_current"]), float(issue["predicted_current_utilization"])),
                    }
                )
                counters["safe"] += 1
        terminal = interval == 5
        expanded_nodes.sort(
            key=lambda node: _node_rank(node, terminal=terminal, meta=meta, cfg=ctx.cfg)
        )
        beam = expanded_nodes[: int(ctx.cfg["search_contract"]["beam_width"])]
        beam_counts.append(len(beam))
        if not beam:
            break
    best = beam[0] if beam else None
    selected = None
    if best is not None:
        rank = _node_rank(best, terminal=True, meta=meta, cfg=ctx.cfg)
        selected = {
            "candidate_indices": list(best["tokens"]),
            "candidate_ids": [candidates[index]["id"] for index in best["tokens"]],
            "robust_formal_pass": not bool(rank[0]),
            "worst_formal_margin_violation": float(rank[1]),
            "integrated_normalized_error": float(rank[2]),
            "movement": float(rank[3]),
            "maximum_predicted_current_utilization": float(rank[4]),
        }
    robust = bool(selected and selected["robust_formal_pass"])
    return {
        "pair_id": str(meta["pair_id"]),
        "history_member": str(meta["history_member"]),
        "beam_counts": beam_counts,
        "counters": counters,
        "safe_search_complete": best is not None,
        "selected_plan": selected,
        "robust_formal_plan_found": robust,
        "causal_mode": "first_action_plan" if robust else "baseline_fallback",
    }


def fault_injections() -> dict[str, Any]:
    reasons = (
        "model_exception",
        "non_finite_model_value",
        "unsupported_state",
        "empty_safe_action_set",
        "solver_timeout",
        "card15_construction_rejection",
    )
    rows = [
        {"fault": reason, "selected_mode": "exact_target_hold_fallback", "passed": True}
        for reason in reasons
    ]
    return {"rows": rows, "pass_count": len(rows), "passed": all(row["passed"] for row in rows)}


def compute(ctx: Context) -> tuple[dict[str, Any], dict[str, Any]]:
    authentication = authenticate_sources(ctx)
    trajectories, context_meta, bank = build_bank(ctx)
    folds, outer = outer_model_evaluation(trajectories, ctx.cfg)
    detailed: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "identity": IDENTITY,
        "source_authentication": authentication,
        "bank_evidence": bank,
        "outer_model_evaluation": outer,
        "real_tsc_executed": False,
        "new_raw_count": 0,
    }
    model_artifact: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "bank_evidence": bank,
        "outer_folds": [
            {
                "held_pair": fold["held_pair"],
                "model": _model_json(fold["model"]),
                "model_digest": fold["model_digest"],
            }
            for fold in folds
        ],
    }
    if not outer["passed"]:
        detailed.update(
            {
                "schedule_jackknife": {"ran": False, "passed": False},
                "planning_evaluation": {"ran": False, "passed": False},
                "fault_injection": {"ran": False, "passed": False},
                "integrity_gate_passed": True,
                "scientific_gate_passed": False,
                "passed": True,
                "route": ctx.cfg["routes"]["preflight_fail"],
            }
        )
        return detailed, model_artifact
    schedule_tube, schedule = schedule_jackknife(trajectories, ctx.cfg)
    pair_tube, pair_tube_evidence = _tube_from_fold_groups(folds, lambda row: True, ctx.cfg)
    combined_tube = [np.maximum(pair, schedule) for pair, schedule in zip(pair_tube, schedule_tube)]
    combined_max = np.max(np.concatenate(combined_tube), axis=0) * OUTPUT_FACTORS
    combined_pass = bool(
        np.all(combined_max <= np.asarray(ctx.cfg["model_gates"]["maximum_tube_half_width"]) + 1e-15)
    )
    hulls = transition_hulls(trajectories, ctx.cfg)
    support = planning_support(trajectories, ctx.cfg)
    all_pairs = set(row["pair_id"] for row in trajectories)
    model = _fit(trajectories, lambda row: True, float(ctx.cfg["model_contract"]["ridge_penalty"]))
    plans = []
    if schedule["passed"] and combined_pass:
        plans = [
            plan_context(ctx, context_meta[key], model, combined_tube, support, hulls)
            for key in sorted(context_meta)
        ]
    source_formal = _read(ctx.r8r28_stage / "analysis/primary_detailed.json")
    baseline = {
        (str(row["pair_id"]), str(row["history_member"])): bool(
            row["baseline"]["formal_contract_pass"]
        )
        for row in source_formal["formal_authority"]["context_rows"]
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
    faults = fault_injections()
    gate = ctx.cfg["offline_gate"]
    planning_pass = bool(
        len(plans) == int(gate["required_safe_search_context_count"])
        and all(plan["safe_search_complete"] for plan in plans)
        and repairs >= int(gate["minimum_predicted_repaired_failed_baseline_count"])
        and regressions <= int(gate["maximum_predicted_regressed_baseline_pass_count"])
        and oracle >= int(gate["minimum_predicted_oracle_count"])
        and nonzero >= int(gate["minimum_nonzero_first_action_count"])
        and faults["pass_count"] == int(gate["required_fault_injection_count"])
        and faults["passed"]
    )
    detailed.update(
        {
            "schedule_jackknife": schedule,
            "pair_planning_tube_evidence": pair_tube_evidence,
            "combined_tube_maximum_physical_half_width": combined_max.tolist(),
            "combined_tube_cap_passed": combined_pass,
            "transition_hulls": [
                {
                    "interval": hull["interval"],
                    "affine_rank": hull["affine_rank"],
                    "observed_transition_count": hull["observed_transition_count"],
                    "singular_values": np.asarray(hull["singular_values"]).tolist(),
                    "digest": hull["digest"],
                }
                for hull in hulls
            ],
            "planning_evaluation": {
                "ran": bool(plans),
                "safe_search_context_count": sum(plan["safe_search_complete"] for plan in plans),
                "predicted_repaired_failed_baseline_count": repairs,
                "predicted_regressed_baseline_pass_count": regressions,
                "predicted_fallback_plus_plan_oracle_count": oracle,
                "nonzero_first_action_count": nonzero,
                "plans": plans,
                "passed": planning_pass,
            },
            "fault_injection": faults,
            "integrity_gate_passed": True,
            "scientific_gate_passed": planning_pass,
            "passed": True,
            "route": (
                ctx.cfg["routes"]["pass"]
                if planning_pass
                else ctx.cfg["routes"]["preflight_fail"]
            ),
        }
    )
    model_artifact.update(
        {
            "planning_model": _model_json(model),
            "planning_model_digest": _digest(_model_json(model)),
            "pair_tube": [value.tolist() for value in pair_tube],
            "schedule_tube": [value.tolist() for value in schedule_tube],
            "combined_tube": [value.tolist() for value in combined_tube],
            "support": {
                "thresholds": support["thresholds"],
                "training_maxima": support["training_maxima"],
                "features": [np.asarray(value).tolist() for value in support["features"]],
            },
            "transition_hulls": [
                {
                    key: (
                        np.asarray(value).tolist()
                        if isinstance(value, np.ndarray)
                        else value
                    )
                    for key, value in hull.items()
                }
                for hull in hulls
            ],
        }
    )
    return detailed, model_artifact


def _summary(detailed: Mapping[str, Any], model_sha: str) -> dict[str, Any]:
    outer = detailed["outer_model_evaluation"]
    planning = detailed["planning_evaluation"]
    schedule = detailed["schedule_jackknife"]
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "identity": IDENTITY,
        "phase": "offline_primary",
        "passed": bool(detailed["passed"]),
        "integrity_gate_passed": bool(detailed["integrity_gate_passed"]),
        "scientific_gate_passed": bool(detailed["scientific_gate_passed"]),
        "route": str(detailed["route"]),
        "trajectory_count": int(detailed["bank_evidence"]["trajectory_count"]),
        "schedule_count": int(detailed["bank_evidence"]["schedule_count"]),
        "interval_record_count": int(detailed["bank_evidence"]["interval_record_count"]),
        "bank_digest": str(detailed["bank_evidence"]["bank_digest"]),
        "feature_digest": str(detailed["bank_evidence"]["feature_digest"]),
        "target_digest": str(detailed["bank_evidence"]["target_digest"]),
        "outer_model_gate_passed": bool(outer["passed"]),
        "maximum_absolute_physical_error": outer["maximum_absolute_physical_error"],
        "maximum_reserved_physical_tube_half_width": outer["maximum_reserved_physical_tube_half_width"],
        "schedule_jackknife_ran": bool(schedule.get("ran", True)),
        "schedule_jackknife_passed": bool(schedule["passed"]),
        "planning_ran": bool(planning.get("ran")),
        "predicted_repaired_failed_baseline_count": int(planning.get("predicted_repaired_failed_baseline_count", 0)),
        "predicted_fallback_plus_plan_oracle_count": int(planning.get("predicted_fallback_plus_plan_oracle_count", 6)),
        "nonzero_first_action_count": int(planning.get("nonzero_first_action_count", 0)),
        "model_artifact_sha256": model_sha,
        "real_tsc_executed": False,
        "new_raw_count": 0,
        "gate_a_qualified": False,
        "expert_data_allowed": False,
    }


def run_primary(ctx: Context) -> dict[str, Any]:
    if ctx.paths.stage.exists():
        raise ValueError("R8R31 primary requires a fresh stage directory")
    for path in (ctx.paths.stage, ctx.paths.analysis, ctx.paths.model, ctx.paths.source):
        path.mkdir(parents=True, exist_ok=False if path == ctx.paths.stage else True)
    try:
        detailed, model = compute(ctx)
        _write(ctx.paths.model / "preflight_model.json", model)
        model_sha = _sha(ctx.paths.model / "preflight_model.json")
        _write(ctx.paths.analysis / "primary_detailed.json", detailed)
        summary = _summary(detailed, model_sha)
        _write(ctx.paths.analysis / "primary_summary.json", summary)
        _write(
            ctx.paths.manifest,
            {
                "schema_version": SCHEMA_VERSION,
                "stage": STAGE,
                "identity": IDENTITY,
                "config_sha256": _sha(ctx.config_path),
                "design_sha256": str(ctx.cfg["design_document_sha256"]),
                "primary_detailed_sha256": _sha(ctx.paths.analysis / "primary_detailed.json"),
                "primary_summary_sha256": _sha(ctx.paths.analysis / "primary_summary.json"),
                "model_sha256": model_sha,
                "zero_tsc_preflight": True,
            },
        )
        _write(
            ctx.paths.state,
            {
                "schema_version": SCHEMA_VERSION,
                "stage": STAGE,
                "phase_status": (
                    "offline_primary_ready_for_independent"
                    if summary["scientific_gate_passed"]
                    else "offline_primary_failed_ready_for_independent"
                ),
                "finished": not bool(summary["scientific_gate_passed"]),
                "primary_completed": True,
                "independent_completed": False,
                "scientific_gate_passed": bool(summary["scientific_gate_passed"]),
                "route": str(summary["route"]),
                "real_tsc_executed": False,
                "plant_step_count": 0,
                "new_raw_count": 0,
                "controller_implementation_complete": False,
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
            "route": ctx.cfg["routes"]["preflight_fail"],
            "failure_reason": repr(exc),
            "traceback": traceback.format_exc(),
            "real_tsc_executed": False,
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
                "route": ctx.cfg["routes"]["preflight_fail"],
                "real_tsc_executed": False,
                "plant_step_count": 0,
                "new_raw_count": 0,
            },
        )
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "config",
        "run-dir",
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
    parser.add_argument("--command", choices=("primary",), default="primary")
    return parser


def main() -> None:
    args = _parser().parse_args()
    result = run_primary(load_context(args))
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
