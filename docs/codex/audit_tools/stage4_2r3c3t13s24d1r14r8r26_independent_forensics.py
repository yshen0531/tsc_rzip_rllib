#!/usr/bin/env python3
"""Structurally independent zero-TSC audit for frozen R8R26."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.spatial import ConvexHull, cKDTree

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r25_independent_forensics as ind25,
)


ind24 = ind25.ind24
ind23 = ind25.ind23
STAGE = "Stage4.2R3c3T13S24D1R14R8R26"
IDENTITY = "action_transition_supported_multiresolution_mpc_preflight_v1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r26_action_transition_supported_multiresolution_mpc_preflight"
DECISIONS = (10, 14, 18, 22)
FACTORS = np.asarray([0.03, 0.03, 10000.0, 1.0, 1.0], dtype=float)


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


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


def _validate_config(cfg: Mapping[str, Any]) -> None:
    root = _root().resolve()
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
        int(cfg.get("schema_version", -1)) != 1
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
        or tuple(map(int, (search["coarse_grid_unit_stride"], search["coarse_level_count"], search["beam_width"], search["terminal_seed_count"], search["maximum_sweeps_per_step"])))
        != (4, 33, 256, 32, 16)
        or tuple(map(int, search["refinement_step_units"])) != (2, 1)
        or tuple(tuple(map(int, row)) for row in search["refinement_directions"])
        != ((1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1))
        or search.get("global_optimality_claimed") is not False
        or search.get("failed_plan_deployment_allowed") is not False
        or tuple(map(float, (action["maximum_incremental_normalized_action_linf"], action["maximum_total_normalized_action_abs"], action["maximum_current_utilization"], action["minimum_desired_applied_current_cosine"], action["maximum_relative_off_basis_residual"])))
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
        or tuple(map(int, (formal["normal_arrival_deadline_step"], formal["normal_hold_through_step"], formal["weak_arrival_deadline_step"], formal["weak_hold_through_step"], formal["arrival_streak_steps"])))
        != (25, 35, 27, 37, 3)
        or tuple(map(float, (formal["position_tolerance_m"], formal["speed_tolerance_m_per_s"], formal["ip_tolerance_A"])))
        != (0.03, 0.1, 10000.0)
        or formal.get("arrival_deadline_expansion_allowed") is not False
        or fallback.get("fallback_controller") != "unchanged_causal_baseline_continuation"
        or fallback.get("plan_selected_only_if_robust_formal_pass") is not True
        or fallback.get("pair_or_history_label_allowed") is not False
        or fallback.get("source_outcome_label_allowed") is not False
        or fallback.get("future_state_allowed") is not False
        or tuple(map(int, (planning["required_safe_search_context_count"], planning["minimum_predicted_repaired_failed_baseline_count"], planning["maximum_predicted_regressed_baseline_pass_count"], planning["minimum_predicted_oracle_count"])))
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
        raise ValueError("independent R8R26 frozen contract changed")


def _source_cfg(cfg: Mapping[str, Any]) -> Mapping[str, Any]:
    return _read((_root() / str(cfg["source_r8r25_config"])).resolve())


def _source_stage(args: argparse.Namespace, cfg: Mapping[str, Any]) -> Path:
    return args.r8r25_run.expanduser().resolve() / str(cfg["source_r8r25"]["stage_directory"])


def _authenticate(args: argparse.Namespace, cfg: Mapping[str, Any]) -> dict[str, Any]:
    stage, expected = _source_stage(args, cfg), cfg["source_r8r25"]
    paths = {
        "primary_detailed": stage / "analysis/primary_detailed.json",
        "primary_summary": stage / "analysis/primary_summary.json",
        "independent": stage / "analysis/independent.json",
        "final_report": stage / "analysis/final_report.json",
        "model_evidence": stage / "model/outer_fold_models.json",
        "stage_manifest": stage / "stage_manifest.json",
        "stage_state": stage / "stage_state.json",
        "compact_audit": stage / "analysis/compact_audit.json",
    }
    hashes = {name: _sha(path) for name, path in paths.items()}
    if any(hashes[name] != str(expected[f"{name}_sha256"]) for name in paths):
        raise ValueError("independent R8R26 R8R25 source hash changed")
    primary = _read(paths["primary_detailed"])
    final = _read(paths["final_report"])
    independent = _read(paths["independent"])
    state = _read(paths["stage_state"])
    compact = _read(paths["compact_audit"])
    model = _read(paths["model_evidence"])
    if (
        stage.parent.name != str(expected["run_name"])
        or primary.get("route") != str(expected["required_route"])
        or final.get("route") != str(expected["required_route"])
        or final.get("primary_independent_agreement") is not True
        or independent.get("passed") is not True
        or primary.get("model_gate_passed") is not True
        or primary.get("predicted_feasibility_gate_passed") is not False
        or state.get("finished") is not True
        or compact.get("passed") is not True
        or compact.get("fresh_controller_sentinel_authorized") is not False
        or primary["planning_evaluation"]["planning_model_digest"] != str(expected["planning_model_digest"])
        or model["planning_evidence"]["tube_evidence"]["tube_digest"] != str(expected["planning_tube_digest"])
    ):
        raise ValueError("independent R8R26 R8R25 outcome changed")
    source_cfg = _source_cfg(cfg)
    transitive = ind25._authenticate(args, source_cfg)
    if transitive.get("passed") is not True:
        raise ValueError("independent R8R26 transitive authentication failed")
    return {"hashes": hashes, "route": str(final["route"]), "transitive": transitive, "passed": True}


def _fit_schedule(bank: Sequence[Mapping[str, Any]], held: str, ridge: float) -> dict[str, Any]:
    groups = []
    for interval in range(4):
        rows = [trajectory["intervals"][interval] for trajectory in bank if str(trajectory["schedule_id"]) != held]
        offsets = []
        for offset in range(max(len(row["targets"]) for row in rows)):
            selected = [row for row in rows if len(row["targets"]) > offset]
            x = np.asarray([row["expanded"] for row in selected], dtype=float)
            y = np.asarray([row["targets"][offset] for row in selected], dtype=float)
            xm, ym = np.mean(x, axis=0), np.mean(y, axis=0)
            dx, dy = x - xm, y - ym
            coefficient = np.linalg.solve(dx.T @ dx + ridge * np.eye(x.shape[1]), dx.T @ dy)
            intercept = ym - xm @ coefficient
            if coefficient.shape != (133, 5) or intercept.shape != (5,) or not np.all(np.isfinite(coefficient)) or not np.all(np.isfinite(intercept)):
                raise ValueError("independent R8R26 schedule fit invalid")
            offsets.append({"sample_offset": offset, "training_row_count": len(selected),
                            "intercept": intercept, "coefficients": coefficient})
        groups.append({"interval": interval, "offsets": offsets})
    return {"intervals": groups}


def _schedule_jackknife(bank: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> tuple[list[np.ndarray], dict[str, Any]]:
    schedules = tuple(sorted({str(row["schedule_id"]) for row in bank}))
    if len(schedules) != 27:
        raise ValueError("independent R8R26 schedule inventory changed")
    grouped: list[list[list[np.ndarray]]] = [[[] for _ in range(count)] for count in (4, 4, 4, 15)]
    folds, all_residuals = [], []
    for held_schedule in schedules:
        model = _fit_schedule(bank, held_schedule, float(cfg["model_contract"]["ridge_penalty"]))
        held = [row for row in bank if str(row["schedule_id"]) == held_schedule]
        predictions = ind23._predictions(model, held)
        if len(held) != 16:
            raise ValueError("independent R8R26 held schedule count changed")
        serial = []
        for trajectory in held:
            identifier = str(trajectory["trajectory_id"])
            interval_rows = []
            for interval, row in enumerate(trajectory["intervals"]):
                residual = np.abs(np.asarray(row["targets"]) - np.asarray(predictions[identifier][interval]))
                interval_rows.append(residual.tolist())
                all_residuals.append(residual)
                for offset, value in enumerate(residual):
                    grouped[interval][offset].append(value)
            serial.append({"trajectory_id": identifier, "absolute_residuals": interval_rows})
        folds.append({"held_schedule": held_schedule, "training_schedule_count": 26,
                      "held_trajectory_count": len(held),
                      "model_digest": _digest(ind23._serial(model)),
                      "residual_digest": _digest(serial)})
    floor = np.asarray(cfg["schedule_jackknife_contract"]["physical_point_error_floors"], dtype=float) / FACTORS
    reserve = float(cfg["schedule_jackknife_contract"]["reserve_multiplier"])
    tube, counts = [], []
    for interval in grouped:
        rows = []
        for values in interval:
            residuals = np.asarray(values, dtype=float).reshape((-1, 5))
            if len(residuals) == 0 or not np.all(np.isfinite(residuals)):
                raise ValueError("independent R8R26 residual group invalid")
            rows.append(np.maximum(reserve * np.max(residuals, axis=0), floor))
            counts.append(len(residuals))
        tube.append(np.asarray(rows))
    maximum_error = np.max(np.concatenate(all_residuals), axis=0) * FACTORS
    maximum_tube = np.max(np.concatenate(tube), axis=0) * FACTORS
    contained = total = 0
    for interval, offsets in enumerate(grouped):
        for offset, values in enumerate(offsets):
            residuals = np.asarray(values, dtype=float).reshape((-1, 5))
            contained += int(np.count_nonzero(residuals <= tube[interval][offset] + 1e-15))
            total += int(residuals.size)
    gates = cfg["model_gates"]
    point_caps = np.asarray([gates["maximum_R_point_error_m"], gates["maximum_Z_point_error_m"],
                             gates["maximum_Ip_point_error_A"], gates["maximum_vR_point_error_m_per_s"],
                             gates["maximum_vZ_point_error_m_per_s"]])
    tube_caps = np.asarray([gates["maximum_reserved_R_tube_half_width_m"], gates["maximum_reserved_Z_tube_half_width_m"],
                            gates["maximum_reserved_Ip_tube_half_width_A"], gates["maximum_reserved_vR_tube_half_width_m_per_s"],
                            gates["maximum_reserved_vZ_tube_half_width_m_per_s"]])
    point_pass = bool(np.all(maximum_error <= point_caps + 1e-15))
    containment_rate = contained / total
    containment_pass = bool(containment_rate >= float(gates["required_reserved_tube_containment_rate"]) - 1e-15)
    tube_pass = bool(np.all(maximum_tube <= tube_caps + 1e-15))
    evidence = {"schedule_ids": list(schedules), "schedule_count": len(schedules), "folds": folds,
                "minimum_residual_record_count": min(counts), "maximum_residual_record_count": max(counts),
                "maximum_absolute_physical_error": maximum_error.tolist(),
                "maximum_reserved_physical_tube_half_width": maximum_tube.tolist(),
                "reserved_tube_contained_component_count": contained,
                "reserved_tube_component_count": total,
                "reserved_tube_containment_rate": containment_rate,
                "point_error_gate_passed": point_pass,
                "reserved_tube_containment_gate_passed": containment_pass,
                "tube_cap_gate_passed": tube_pass,
                "tube_digest": _digest([value.tolist() for value in tube]),
                "finite_exclusion_count": 0, "forbidden_input_count": 0,
                "passed": bool(point_pass and containment_pass and tube_pass and contained == total == 56160)}
    return tube, evidence


def _transition_hulls(bank: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    contract = cfg["transition_support_contract"]
    hulls = []
    for interval in range(4):
        rows = sorted({tuple(np.r_[trajectory["intervals"][interval]["previous_q"],
                                      trajectory["intervals"][interval]["q"]] /
                             float(contract["normalized_transition_scale"])) for trajectory in bank})
        points = np.asarray(rows, dtype=float)
        origin = np.mean(points, axis=0)
        centered = points - origin
        _, singular, vh = np.linalg.svd(centered, full_matrices=False)
        rank = int(np.count_nonzero(singular > float(contract["affine_singular_value_tolerance"])))
        basis = vh[:rank].T
        projected = centered @ basis
        if rank == 1:
            equations = np.asarray([[1.0, -float(np.max(projected[:, 0]))],
                                    [-1.0, float(np.min(projected[:, 0]))]])
        elif rank >= 2:
            equations = np.asarray(ConvexHull(projected).equations)
        else:
            equations = np.empty((0, 1))
        hulls.append({"interval": interval, "points": points, "origin": origin,
                      "basis": basis, "equations": equations, "affine_rank": rank,
                      "observed_transition_count": len(points), "singular_values": singular,
                      "digest": _digest(rows)})
    return hulls


def _transition_supported(hull: Mapping[str, Any], previous_q: np.ndarray, q: np.ndarray,
                          cfg: Mapping[str, Any]) -> bool:
    contract = cfg["transition_support_contract"]
    value = np.r_[previous_q, q] / float(contract["normalized_transition_scale"])
    delta = value - np.asarray(hull["origin"])
    basis = np.asarray(hull["basis"])
    projected = delta @ basis
    if np.linalg.norm(delta - projected @ basis.T) > float(contract["affine_residual_tolerance"]) + 1e-15:
        return False
    equations = np.asarray(hull["equations"])
    if len(equations) == 0:
        return np.linalg.norm(delta) <= float(contract["affine_residual_tolerance"]) + 1e-15
    return float(np.max(equations[:, :-1] @ projected + equations[:, -1])) <= float(contract["convex_hull_inequality_tolerance"]) + 1e-15


def _planning_support(bank: Sequence[Mapping[str, Any]], cfg25: Mapping[str, Any]) -> dict[str, Any]:
    pairs = tuple(sorted({str(row["pair_id"]) for row in bank}))
    multiplier = float(cfg25["planning_support_contract"]["threshold_multiplier"])
    features, trees, maxima, thresholds = [], [], [], []
    for interval in range(4):
        by_pair = {pair: np.asarray([row["intervals"][interval]["feature"] for row in bank
                                    if str(row["pair_id"]) == pair]) for pair in pairs}
        distances = []
        for pair, values in by_pair.items():
            other = np.concatenate([other_values for other_pair, other_values in by_pair.items() if other_pair != pair])
            distances.extend(np.min(np.linalg.norm(values[:, None] - other[None], axis=2), axis=1))
        all_features = np.concatenate(list(by_pair.values()))
        maximum = max(map(float, distances))
        features.append(all_features); trees.append(cKDTree(all_features))
        maxima.append(maximum); thresholds.append(multiplier * maximum)
    return {"features": features, "trees": trees, "training_nearest_neighbor_maxima": maxima,
            "thresholds": thresholds, "training_origin_count_by_interval": [len(value) for value in features]}


def _state_supported(support: Mapping[str, Any], feature: np.ndarray, interval: int) -> bool:
    distance = float(support["trees"][interval].query(feature, k=1, eps=0.0, workers=1)[0])
    return distance <= float(support["thresholds"][interval]) + 1e-15


def _coarse_units(r22_cfg: Mapping[str, Any], cfg: Mapping[str, Any]) -> list[tuple[int, int]]:
    stride = int(cfg["search_contract"]["coarse_grid_unit_stride"])
    maximum = int(cfg["transition_support_contract"]["maximum_coordinate_sum_units"])
    output = {(u, v) for u in range(0, maximum + 1, stride) for v in range(0, maximum + 1 - u, stride)}
    for level in ind24._levels(r22_cfg):
        q = np.asarray(level["q"])
        units = tuple(map(int, np.rint(q * 16.0)))
        if not np.allclose(q, np.asarray(units) / 16.0, rtol=0.0, atol=1e-15):
            raise ValueError("independent R8R26 source level off lattice")
        output.add(units)
    result = sorted(output)
    if len(result) != int(cfg["search_contract"]["coarse_level_count"]):
        raise ValueError("independent R8R26 coarse level count changed")
    return result


def _level(units: tuple[int, int], r22_cfg: Mapping[str, Any]) -> dict[str, Any]:
    q = np.asarray(units, dtype=float) / 16.0
    schedule = r22_cfg["schedule_contract"]
    matrix = np.asarray(schedule["canonical_matrix_columns"], dtype=float)
    endpoint_u = matrix[:, int(schedule["endpoint_u"]["direction_index"])] * int(schedule["endpoint_u"]["sign"])
    endpoint_v = matrix[:, int(schedule["endpoint_v"]["direction_index"])] * int(schedule["endpoint_v"]["sign"])
    return {"index": 0 if units == (0, 0) else -1,
            "level_id": f"q_u{units[0]:02d}_v{units[1]:02d}",
            "q": q.tolist(), "coordinate": (q[0] * endpoint_u + q[1] * endpoint_v).tolist(),
            "units": units}


@dataclass
class Counter:
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
        self.digest.update((json.dumps([list(value) for value in tokens], separators=(",", ":")) +
                            "|" + status + "\n").encode("ascii"))


def _deadline_endpoint(meta: Mapping[str, Any], cfg: Mapping[str, Any]) -> tuple[int, int]:
    weak = math.isclose(float(meta["slew_scale"]), 0.9, abs_tol=1e-15)
    return (int(cfg["formal_contract"]["weak_arrival_deadline_step" if weak else "normal_arrival_deadline_step"]),
            int(cfg["formal_contract"]["weak_hold_through_step" if weak else "normal_hold_through_step"]))


def _initial(meta: Mapping[str, Any]) -> dict[str, Any]:
    states = ind23._states(meta["baseline_result"], meta["target"])
    prefix = states[:11]
    current = np.asarray(meta["baseline_result"]["trajectory"][10]["currents_a_tsc"])
    return {"states": prefix, "tubes": np.zeros_like(prefix), "current": current,
            "previous_current": current, "previous_q": np.zeros(2), "tokens": tuple(),
            "movement": 0.0, "maximum_current": 0.0}


def _rank(node: Mapping[str, Any], terminal: bool, deadline: int, endpoint: int,
          cfg: Mapping[str, Any]) -> tuple[Any, ...]:
    states = np.asarray(node["states"])
    if terminal:
        passed, violation, integrated = ind24._formal(states, np.asarray(node["tubes"]), deadline, endpoint, cfg)
        return (not passed, violation, integrated, float(node["movement"]),
                float(node["maximum_current"]), tuple(node["tokens"]))
    return (float(np.sum(states[10:, :3] ** 2)), float(node["maximum_current"]),
            float(node["movement"]), tuple(node["tokens"]))


def _expand(cfg: Mapping[str, Any], cfg25: Mapping[str, Any], r22_cfg: Mapping[str, Any],
            meta: Mapping[str, Any], model: Mapping[str, Any], tube: Sequence[np.ndarray],
            support: Mapping[str, Any], hulls: Sequence[Mapping[str, Any]],
            node: Mapping[str, Any], interval: int, units: tuple[int, int],
            counter: Counter) -> dict[str, Any] | None:
    feature = ind24._feature(np.asarray(node["states"]), np.asarray(node["current"]),
                             np.asarray(node["previous_current"]), np.asarray(node["previous_q"]),
                             np.asarray(meta["limits"]))
    tokens = tuple(node["tokens"]) + (units,)
    if not _state_supported(support, feature, interval):
        counter.state_unsupported_nodes += 1; counter.record(tokens, "state_unsupported"); return None
    level = _level(units, r22_cfg)
    q = np.asarray(level["q"])
    if not _transition_supported(hulls[interval], np.asarray(node["previous_q"]), q, cfg):
        counter.transition_unsupported_expansions += 1; counter.record(tokens, "transition_unsupported"); return None
    issue = ind24._safe_issue(cfg25, r22_cfg, meta, np.asarray(node["current"]), level, DECISIONS[interval])
    if not bool(issue["passed"]):
        counter.hard_action_rejections += 1; counter.record(tokens, "hard_action_rejected"); return None
    count = 4 if interval < 3 else _deadline_endpoint(meta, cfg)[1] - 22
    row = {"interval": interval, "feature": feature, "q": q,
           "previous_q": np.asarray(node["previous_q"]), "targets": np.zeros((count, 5))}
    row["expanded"] = ind23._expand(feature, q, np.asarray(node["previous_q"]))
    prediction = ind23._predict(model, row)
    next_current = np.asarray(issue["nominal_issue_readback_current_a_tsc"])
    counter.safe_expansions += 1; counter.record(tokens, "safe")
    return {"states": np.concatenate((np.asarray(node["states"]), prediction)),
            "tubes": np.concatenate((np.asarray(node["tubes"]), np.asarray(tube[interval][:count]))),
            "current": next_current, "previous_current": np.asarray(node["current"]),
            "previous_q": q, "tokens": tokens,
            "movement": float(node["movement"]) + float(np.sum(np.abs(q - np.asarray(node["previous_q"])))),
            "maximum_current": max(float(node["maximum_current"]), float(issue["predicted_current_utilization"]))}


def _evaluate_tokens(cfg: Mapping[str, Any], cfg25: Mapping[str, Any], r22_cfg: Mapping[str, Any],
                     meta: Mapping[str, Any], model: Mapping[str, Any], tube: Sequence[np.ndarray],
                     support: Mapping[str, Any], hulls: Sequence[Mapping[str, Any]],
                     tokens: Sequence[tuple[int, int]], counter: Counter) -> dict[str, Any] | None:
    node = _initial(meta)
    for interval, units in enumerate(tokens):
        node = _expand(cfg, cfg25, r22_cfg, meta, model, tube, support, hulls,
                       node, interval, units, counter)
        if node is None:
            return None
    return node


def _plan_one(cfg: Mapping[str, Any], cfg25: Mapping[str, Any], r22_cfg: Mapping[str, Any],
              meta: Mapping[str, Any], model: Mapping[str, Any], tube: Sequence[np.ndarray],
              support: Mapping[str, Any], hulls: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    counter = Counter()
    deadline, endpoint = _deadline_endpoint(meta, cfg)
    beam = [_initial(meta)]
    coarse = _coarse_units(r22_cfg, cfg)
    beam_counts = []
    for interval in range(4):
        expanded = []
        for node in beam:
            for units in coarse:
                candidate = _expand(cfg, cfg25, r22_cfg, meta, model, tube, support,
                                    hulls, node, interval, units, counter)
                if candidate is not None:
                    expanded.append(candidate)
        terminal = interval == 3
        expanded.sort(key=lambda node: _rank(node, terminal, deadline, endpoint, cfg))
        count = int(cfg["search_contract"]["terminal_seed_count"] if terminal else cfg["search_contract"]["beam_width"])
        beam = expanded[:count]
        beam_counts.append(len(beam))
        if not beam:
            break
    seeds = list(beam)
    refined, refinement_records = [], []
    directions = tuple(tuple(map(int, row)) for row in cfg["search_contract"]["refinement_directions"])
    maximum = int(cfg["transition_support_contract"]["maximum_coordinate_sum_units"])
    maximum_sweeps = int(cfg["search_contract"]["maximum_sweeps_per_step"])
    for seed_index, seed in enumerate(seeds):
        current = seed
        scale_records = []
        for step_units in map(int, cfg["search_contract"]["refinement_step_units"]):
            sweeps = accepted = 0
            for _ in range(maximum_sweeps):
                sweeps += 1
                current_rank = _rank(current, True, deadline, endpoint, cfg)
                candidates = []
                current_tokens = tuple(current["tokens"])
                for decision_index in range(4):
                    for direction_index, direction in enumerate(directions):
                        old = current_tokens[decision_index]
                        units = (old[0] + step_units * direction[0],
                                 old[1] + step_units * direction[1])
                        if units[0] < 0 or units[1] < 0 or sum(units) > maximum:
                            continue
                        tokens = list(current_tokens); tokens[decision_index] = units
                        node = _evaluate_tokens(cfg, cfg25, r22_cfg, meta, model, tube,
                                                support, hulls, tokens, counter)
                        if node is not None:
                            candidates.append((_rank(node, True, deadline, endpoint, cfg),
                                               decision_index, direction_index, node))
                if not candidates:
                    break
                candidates.sort(key=lambda row: (row[0], row[1], row[2]))
                if candidates[0][0] < current_rank:
                    current = candidates[0][3]; accepted += 1
                else:
                    break
            scale_records.append({"step_units": step_units, "sweeps": sweeps,
                                  "accepted_moves": accepted})
        refined.append(current)
        refinement_records.append({"seed_index": seed_index, "scales": scale_records})
    candidates = seeds + refined
    candidates.sort(key=lambda node: _rank(node, True, deadline, endpoint, cfg))
    best = candidates[0] if candidates else None
    selected = None
    if best is not None:
        rank = _rank(best, True, deadline, endpoint, cfg)
        selected = {"q_units": [list(value) for value in best["tokens"]],
                    "q_values": [[value[0] / 16.0, value[1] / 16.0] for value in best["tokens"]],
                    "robust_formal_pass": not bool(rank[0]),
                    "worst_formal_margin_violation": float(rank[1]),
                    "integrated_normalized_error": float(rank[2]),
                    "cumulative_normalized_action_movement": float(rank[3]),
                    "maximum_predicted_current_utilization": float(rank[4]),
                    "predicted_states": np.asarray(best["states"]).tolist(),
                    "reserved_tubes": np.asarray(best["tubes"]).tolist()}
    robust = bool(selected and selected["robust_formal_pass"])
    return {"pair_id": str(meta["pair_id"]), "history_member": str(meta["history_member"]),
            "coarse_level_count": len(coarse), "beam_counts": beam_counts,
            "terminal_seed_count": len(seeds), "refinement_records": refinement_records,
            "safe_search_complete": best is not None, "selected_plan": selected,
            "robust_formal_plan_found": robust,
            "causal_selected_mode": "refined_plan" if robust else "baseline_fallback",
            "search_counts": {"evaluated_sequences": counter.evaluated_sequences,
                              "safe_expansions": counter.safe_expansions,
                              "state_unsupported_nodes": counter.state_unsupported_nodes,
                              "transition_unsupported_expansions": counter.transition_unsupported_expansions,
                              "hard_action_rejections": counter.hard_action_rejections},
            "evaluated_sequence_digest": counter.digest.hexdigest()}


def _planning(args: argparse.Namespace, cfg: Mapping[str, Any], cfg25: Mapping[str, Any],
              r23_cfg: Mapping[str, Any], model: Mapping[str, Any], tube: Sequence[np.ndarray],
              support: Mapping[str, Any], hulls: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    metadata, r22_cfg, source_stage = ind24._planning_metadata(args, r23_cfg)
    plans = [_plan_one(cfg, cfg25, r22_cfg, metadata[key], model, tube, support, hulls)
             for key in sorted(metadata)]
    source = _read(source_stage / "analysis/primary_detailed.json")
    baseline = {(str(row["pair_id"]), str(row["history_member"])):
                bool(row["baseline"]["formal_contract_pass"])
                for row in source["formal_authority"]["context_rows"]}
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
    gate = cfg["planning_gate"]
    passed = bool(complete == int(gate["required_safe_search_context_count"])
                  and repairs >= int(gate["minimum_predicted_repaired_failed_baseline_count"])
                  and regressions <= int(gate["maximum_predicted_regressed_baseline_pass_count"])
                  and oracle >= int(gate["minimum_predicted_oracle_count"]))
    return {"safe_search_context_count": complete,
            "predicted_repaired_failed_baseline_count": repairs,
            "predicted_regressed_baseline_pass_count": regressions,
            "predicted_baseline_fallback_plus_plan_oracle_count": oracle,
            "robust_formal_plan_context_count": sum(bool(plan["robust_formal_plan_found"]) for plan in plans),
            "plans": plans, "passed": passed}


def audit(args: argparse.Namespace, cfg: Mapping[str, Any]) -> dict[str, Any]:
    _validate_config(cfg)
    authentication = _authenticate(args, cfg)
    cfg25 = _source_cfg(cfg)
    cfg24 = ind25._source_config(cfg25)
    r23_cfg = ind24._source_config(cfg24)
    stage = args.run_dir.expanduser().resolve() / RUN_NAME
    primary_path = stage / "analysis/primary_detailed.json"
    summary_path = stage / "analysis/primary_summary.json"
    model_path = stage / "model/preflight_evidence.json"
    primary, summary = _read(primary_path), _read(summary_path)
    bank = ind23._build_bank(args, r23_cfg)
    bank_evidence = ind23._bank_evidence(bank)
    schedules = sorted({str(row["schedule_id"]) for row in bank})
    pairs = tuple(sorted({str(row["pair_id"]) for row in bank}))
    folds25 = ind25._outer(bank, cfg25)
    ind25._attach(folds25, cfg25)
    source_planning, source_planning_evidence = ind25._planning(args, cfg25, r23_cfg, bank, folds25)
    source_primary = _read(_source_stage(args, cfg) / "analysis/primary_detailed.json")
    model = ind23._fit(bank, pairs, float(cfg["model_contract"]["ridge_penalty"]))
    pair_tube = [np.asarray(value) for value in source_planning_evidence["tube_template"]]
    support = _planning_support(bank, cfg25)
    reproduction = {"planning_model_digest": _digest(ind23._serial(model)),
                    "pair_tube_digest": _digest([value.tolist() for value in pair_tube]),
                    "maximum_original_plan_absolute_difference": ind23._maximum_difference(
                        source_primary["planning_evaluation"]["plans"], source_planning["plans"]),
                    "original_plan_count": len(source_planning["plans"])}
    expected = cfg["source_r8r25"]
    reproduction["passed"] = bool(reproduction["planning_model_digest"] == str(expected["planning_model_digest"])
                                  and reproduction["pair_tube_digest"] == str(expected["planning_tube_digest"])
                                  and reproduction["maximum_original_plan_absolute_difference"] <= 1e-12
                                  and reproduction["original_plan_count"] == 16)
    if not reproduction["passed"]:
        raise ValueError("independent R8R26 source reproduction failed")
    schedule_tube, schedule_evidence = _schedule_jackknife(bank, cfg)
    combined = [np.maximum(pair, schedule) for pair, schedule in zip(pair_tube, schedule_tube)]
    combined_physical = np.max(np.concatenate(combined), axis=0) * FACTORS
    gates = cfg["model_gates"]
    caps = np.asarray([gates["maximum_reserved_R_tube_half_width_m"], gates["maximum_reserved_Z_tube_half_width_m"],
                       gates["maximum_reserved_Ip_tube_half_width_A"], gates["maximum_reserved_vR_tube_half_width_m_per_s"],
                       gates["maximum_reserved_vZ_tube_half_width_m_per_s"]])
    combined_pass = bool(np.all(combined_physical <= caps + 1e-15))
    model_gate = bool(schedule_evidence["passed"] and combined_pass)
    hulls = _transition_hulls(bank, cfg)
    hull_evidence = [{"interval": int(hull["interval"]),
                      "observed_transition_count": int(hull["observed_transition_count"]),
                      "affine_rank": int(hull["affine_rank"]),
                      "singular_values": np.asarray(hull["singular_values"]).tolist(),
                      "transition_digest": str(hull["digest"]),
                      "hull_equation_digest": _digest(np.asarray(hull["equations"]).tolist())}
                     for hull in hulls]
    metadata, r22_cfg, _ = ind24._planning_metadata(args, r23_cfg)
    coarse = [list(value) for value in _coarse_units(r22_cfg, cfg)]
    if model_gate:
        planning = _planning(args, cfg, cfg25, r23_cfg, model, combined, support, hulls)
    else:
        planning = {"safe_search_context_count": 0, "predicted_repaired_failed_baseline_count": 0,
                    "predicted_regressed_baseline_pass_count": 0,
                    "predicted_baseline_fallback_plus_plan_oracle_count": 6,
                    "robust_formal_plan_context_count": 0, "plans": [],
                    "skipped_reason": "frozen_schedule_jackknife_or_combined_tube_gate_failed",
                    "passed": False}
    scientific = bool(model_gate and planning["passed"])
    route = str(cfg["routes"]["pass" if scientific else ("planning_fail" if model_gate else "model_fail")])
    tolerance = float(cfg["planning_gate"]["primary_independent_absolute_tolerance"])
    bank_agreement = bool(primary["bank_evidence"]["feature_digest"] == bank_evidence["feature_digest"]
                          and primary["bank_evidence"]["target_digest"] == bank_evidence["target_digest"]
                          and primary["bank_evidence"]["schedule_ids"] == schedules)
    reproduction_difference = ind23._maximum_difference(primary["source_reproduction"], reproduction)
    schedule_difference = ind23._maximum_difference(primary["schedule_jackknife_evaluation"], schedule_evidence)
    hull_difference = ind23._maximum_difference(primary["transition_hull_evidence"], hull_evidence)
    plan_difference = ind23._maximum_difference(primary["planning_evaluation"], planning)
    result = {"schema_version": 1, "stage": STAGE,
              "audit_kind": "action_transition_supported_multiresolution_mpc_preflight_independent",
              "source_authentication": authentication,
              "bank_evidence": {**bank_evidence, "schedule_count": len(schedules), "schedule_ids": schedules},
              "source_reproduction": reproduction,
              "schedule_jackknife_evaluation": schedule_evidence,
              "pair_tube_digest": _digest([value.tolist() for value in pair_tube]),
              "combined_tube_digest": _digest([value.tolist() for value in combined]),
              "maximum_combined_physical_tube_half_width": combined_physical.tolist(),
              "combined_tube_cap_gate_passed": combined_pass,
              "transition_hull_evidence": hull_evidence,
              "coarse_level_units": coarse,
              "model_gate_passed": model_gate,
              "planning_evaluation": planning,
              "route": route,
              "maximum_source_reproduction_absolute_difference": reproduction_difference,
              "maximum_schedule_absolute_difference": schedule_difference,
              "maximum_hull_absolute_difference": hull_difference,
              "maximum_plan_absolute_difference": plan_difference,
              "primary_bank_agreement": bank_agreement,
              "primary_source_reproduction_agreement": reproduction_difference <= tolerance,
              "primary_schedule_agreement": schedule_difference <= tolerance,
              "primary_hull_agreement": hull_difference <= tolerance,
              "primary_plan_agreement": plan_difference <= tolerance,
              "primary_route_agreement": primary.get("route") == route and summary.get("route") == route,
              "primary_outcome_agreement": bool(primary.get("model_gate_passed") is model_gate
                                                  and primary.get("predicted_feasibility_gate_passed") is planning["passed"]),
              "primary_detailed_sha256": _sha(primary_path),
              "primary_summary_sha256": _sha(summary_path),
              "primary_model_evidence_sha256": _sha(model_path),
              "real_tsc_executed": False, "plant_step_count": 0, "new_raw_count": 0}
    result["passed"] = all(bool(result[key]) for key in (
        "primary_bank_agreement", "primary_source_reproduction_agreement",
        "primary_schedule_agreement", "primary_hull_agreement", "primary_plan_agreement",
        "primary_route_agreement", "primary_outcome_agreement"))
    if not result["passed"]:
        raise ValueError("independent R8R26 audit disagrees with primary")
    _write(stage / "analysis/independent.json", result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--r8r25-run", type=Path, required=True)
    parser.add_argument("--r8r24-run", type=Path, required=True)
    parser.add_argument("--r8r23-run", type=Path, required=True)
    for name in (
        "r8r22-run", "r8r7-run", "r8r12-run", "r8r14-run", "r8r15-run",
        "r8r19-run", "r8r20-run", "r8-run", "r8r1-output", "r8r6-run",
        "source-d1r11-run", "source-r2-run", "source-r4-run", "source-r6-run",
        "source-s21-run", "source-s23r1-output", "source-s24-run",
        "source-d1r9-v1", "source-d1r9-v2", "source-d1r10-run",
        "source-d1r10-audit", "source-stage42r3b-run", "source-stage42r3c3-run",
        "source-stage42r3c3-bank-dir", "source-stage42r3c3t1-run",
        "source-stage42r3c3t1-audit-dir", "source-stage42r3c3t3-controller-bank",
        "q1-run", "q2-run", "q1-audit", "q2-audit", "r3b-server-audit",
        "r3b-snapshot-checks",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    cfg = _read(args.config.expanduser().resolve())
    result = audit(args, cfg)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
