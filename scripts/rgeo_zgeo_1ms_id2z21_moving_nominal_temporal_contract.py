#!/usr/bin/env python3
"""Read-only ID-2Z21 moving-nominal temporal-control contract audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


SCHEMA = "rgeo-zgeo-1ms-id2z21-moving-nominal-temporal-contract-result-v1"
CONFIG_SCHEMA = "rgeo-zgeo-1ms-id2z21-moving-nominal-temporal-contract-v1"
HEX40 = re.compile(r"[0-9a-f]{40}\Z")


class AuditInputError(RuntimeError):
    """The frozen audit contract or evidence identity is invalid."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuditInputError(f"cannot read JSON {path}: {exc}") from exc


def inside_root(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise AuditInputError(f"path escapes repository: {relative}") from exc
    if not candidate.is_file() or candidate.is_symlink():
        raise AuditInputError(f"required regular file missing: {relative}")
    return candidate


def require_close(actual: float, expected: float, tolerance: float, label: str) -> None:
    if not math.isfinite(actual) or abs(actual - expected) > tolerance:
        raise AuditInputError(
            f"{label}: actual={actual!r} expected={expected!r} tolerance={tolerance!r}"
        )


def state_rzi(state: Mapping[str, Any]) -> tuple[float, float, float]:
    values = (
        float(state["r_geo_m"]),
        float(state["z_geo_m"]),
        float(state["ip_a"]),
    )
    if not all(math.isfinite(value) for value in values):
        raise AuditInputError("non-finite R/Z/Ip state")
    return values


def causal_velocity(states: Sequence[Mapping[str, Any]], index: int, dt_s: float) -> np.ndarray:
    if index <= 0 or index >= len(states):
        raise AuditInputError(f"invalid causal velocity state index: {index}")
    current = np.asarray(state_rzi(states[index])[:2], dtype=float)
    previous = np.asarray(state_rzi(states[index - 1])[:2], dtype=float)
    return (current - previous) / dt_s


def source_metrics(
    states: Sequence[Mapping[str, Any]], index: int, dt_s: float
) -> dict[str, float]:
    source = state_rzi(states[0])
    current = state_rzi(states[index])
    velocity = causal_velocity(states, index, dt_s)
    return {
        "distance_m": math.hypot(current[0] - source[0], current[1] - source[1]),
        "speed_m_per_s": float(np.linalg.norm(velocity)),
        "ip_fraction": abs(current[2] - source[2]) / abs(source[2]),
    }


def terminal_metrics(
    states: Sequence[Mapping[str, Any]], indices: Sequence[int], dt_s: float
) -> dict[str, float]:
    rows = [source_metrics(states, index, dt_s) for index in indices]
    return {
        "maximum_distance_m": max(row["distance_m"] for row in rows),
        "maximum_speed_m_per_s": max(row["speed_m_per_s"] for row in rows),
        "maximum_ip_fraction": max(row["ip_fraction"] for row in rows),
    }


def capture_passed(
    states: Sequence[Mapping[str, Any]], indices: Sequence[int], gate: Mapping[str, Any], dt_s: float
) -> bool:
    return all(
        row["distance_m"] <= float(gate["maximum_source_rz_distance_m"])
        and row["speed_m_per_s"] <= float(gate["maximum_rz_step_speed_m_per_s"])
        and row["ip_fraction"] <= float(gate["maximum_absolute_source_ip_fraction"])
        for row in (source_metrics(states, index, dt_s) for index in indices)
    )


def target(action: Mapping[str, Any], coil_count: int) -> np.ndarray:
    values = np.asarray(action["target_current_a_tsc"], dtype=float)
    if values.shape != (coil_count,) or not np.all(np.isfinite(values)):
        raise AuditInputError("invalid target_current_a_tsc")
    return values


def token_vectors(
    trajectories: Mapping[str, Mapping[str, Any]],
    issue_first: int,
    issue_last: int,
    alphabet: Sequence[str],
    coil_count: int,
    tolerance_a: float,
) -> dict[str, np.ndarray]:
    occurrences: dict[str, list[np.ndarray]] = {token: [] for token in alphabet}
    expected_length = issue_last - issue_first + 1
    for family_id, row in trajectories.items():
        actions = row.get("actions")
        tokens = row.get("tokens")
        if not isinstance(actions, list) or len(actions) <= issue_last:
            raise AuditInputError(f"{family_id}: incomplete actions")
        if not isinstance(tokens, str) or len(tokens) != expected_length:
            raise AuditInputError(f"{family_id}: invalid token sequence")
        for offset, token_name in enumerate(tokens):
            if token_name not in occurrences:
                raise AuditInputError(f"{family_id}: unknown token {token_name!r}")
            issue = issue_first + offset
            increment = target(actions[issue], coil_count) - target(actions[issue - 1], coil_count)
            occurrences[token_name].append(increment)
    result: dict[str, np.ndarray] = {}
    for token_name, rows in occurrences.items():
        if not rows:
            raise AuditInputError(f"token never observed: {token_name}")
        reference = rows[0]
        maximum_error = max(float(np.max(np.abs(row - reference))) for row in rows)
        if maximum_error > tolerance_a:
            raise AuditInputError(
                f"token {token_name} not exact across occurrences: {maximum_error} A"
            )
        result[token_name] = reference
    return result


def numerical_rank_condition(matrix: np.ndarray, relative_tolerance: float) -> tuple[int, float, list[float]]:
    singular = np.linalg.svd(matrix, compute_uv=False)
    if singular.size == 0 or singular[0] <= 0:
        return 0, math.inf, [float(value) for value in singular]
    rank = int(np.sum(singular > singular[0] * relative_tolerance))
    condition = math.inf if rank == 0 else float(singular[0] / singular[rank - 1])
    return rank, condition, [float(value) for value in singular]


def first_divergence(plus_tokens: str, minus_tokens: str, issue_first: int) -> int:
    if len(plus_tokens) != len(minus_tokens):
        raise AuditInputError("signed token sequences have different lengths")
    for offset, (plus, minus) in enumerate(zip(plus_tokens, minus_tokens)):
        if plus != minus:
            return issue_first + offset
    raise AuditInputError("signed token pair never diverges")


def pair_segment_metrics(
    pair_id: str,
    plus: Mapping[str, Any],
    minus: Mapping[str, Any],
    issue_first: int,
    horizons_ms: Sequence[int],
    dt_s: float,
) -> dict[str, Any]:
    plus_states = plus["states"]
    minus_states = minus["states"]
    if len(plus_states) != len(minus_states):
        raise AuditInputError(f"{pair_id}: signed state counts differ")
    divergence_issue = first_divergence(plus["tokens"], minus["tokens"], issue_first)
    origin_plus = np.asarray(state_rzi(plus_states[divergence_issue])[:2], dtype=float)
    origin_minus = np.asarray(state_rzi(minus_states[divergence_issue])[:2], dtype=float)
    if float(np.max(np.abs(origin_plus - origin_minus))) > 1e-12:
        raise AuditInputError(f"{pair_id}: first-divergence preissue states are not matched")

    rows: list[dict[str, Any]] = []
    for horizon in horizons_ms:
        endpoint = divergence_issue + int(horizon)
        if endpoint >= len(plus_states):
            raise AuditInputError(f"{pair_id}: horizon exceeds trajectory")
        plus_rz = np.asarray(state_rzi(plus_states[endpoint])[:2], dtype=float)
        minus_rz = np.asarray(state_rzi(minus_states[endpoint])[:2], dtype=float)
        vector = plus_rz - minus_rz
        velocity_vector = causal_velocity(plus_states, endpoint, dt_s) - causal_velocity(
            minus_states, endpoint, dt_s
        )
        window_start = max(divergence_issue + 1, endpoint - 2)
        norms: list[float] = []
        for index in range(window_start, endpoint + 1):
            p = np.asarray(state_rzi(plus_states[index])[:2], dtype=float)
            m = np.asarray(state_rzi(minus_states[index])[:2], dtype=float)
            norms.append(float(np.linalg.norm(p - m)))
        median = float(np.median(np.asarray(norms, dtype=float)))
        peak = max(norms)
        ratio = math.inf if median <= 0 else peak / median
        rows.append(
            {
                "pair_id": pair_id,
                "first_divergence_issue": divergence_issue,
                "horizon_ms": int(horizon),
                "endpoint_state_index": endpoint,
                "rz_vector_m": [float(value) for value in vector],
                "rz_separation_m": float(np.linalg.norm(vector)),
                "terminal_velocity_vector_m_per_s": [float(value) for value in velocity_vector],
                "terminal_velocity_separation_m_per_s": float(np.linalg.norm(velocity_vector)),
                "three_state_median_rz_separation_m": median,
                "peak_to_three_state_median_ratio": ratio,
            }
        )
    return {"pair_id": pair_id, "first_divergence_issue": divergence_issue, "horizons": rows}


def useful_horizon(segment: Mapping[str, Any], gates: Mapping[str, Any]) -> Mapping[str, Any] | None:
    by_horizon = {int(row["horizon_ms"]): row for row in segment["horizons"]}
    for horizon in (4, 8):
        row = by_horizon.get(horizon)
        if row is None:
            continue
        signal_threshold = (
            float(gates["minimum_four_ms_rz_separation_m"])
            if horizon == 4
            else float(gates["minimum_eight_ms_rz_separation_m"])
        )
        if (
            float(row["rz_separation_m"]) >= signal_threshold
            and float(row["terminal_velocity_separation_m_per_s"])
            >= float(gates["minimum_terminal_velocity_separation_m_per_s"])
            and float(row["three_state_median_rz_separation_m"])
            >= float(gates["minimum_three_state_median_rz_separation_m"])
            and float(row["peak_to_three_state_median_ratio"])
            <= float(gates["maximum_peak_to_three_state_median_ratio"])
        ):
            return row
    return None


def best_two_vector_geometry(useful: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    best: dict[str, Any] | None = None
    for left_index in range(len(useful)):
        for right_index in range(left_index + 1, len(useful)):
            left = useful[left_index]
            right = useful[right_index]
            if left["pair_id"] == right["pair_id"]:
                continue
            v1 = np.asarray(left["rz_vector_m"], dtype=float)
            v2 = np.asarray(right["rz_vector_m"], dtype=float)
            n1 = float(np.linalg.norm(v1))
            n2 = float(np.linalg.norm(v2))
            if n1 <= 0 or n2 <= 0:
                continue
            cosine = max(-1.0, min(1.0, abs(float(np.dot(v1, v2))) / (n1 * n2)))
            angle = math.degrees(math.acos(cosine))
            matrix = np.column_stack((v1, v2))
            singular = np.linalg.svd(matrix, compute_uv=False)
            condition = math.inf if singular[-1] <= 0 else float(singular[0] / singular[-1])
            row = {
                "pair_ids": [left["pair_id"], right["pair_id"]],
                "horizons_ms": [left["horizon_ms"], right["horizon_ms"]],
                "acute_line_angle_deg": angle,
                "condition": condition,
                "vectors_m": [left["rz_vector_m"], right["rz_vector_m"]],
            }
            if best is None or (condition, -angle, row["pair_ids"]) < (
                best["condition"], -best["acute_line_angle_deg"], best["pair_ids"]
            ):
                best = row
    return best or {
        "pair_ids": [],
        "horizons_ms": [],
        "acute_line_angle_deg": 0.0,
        "condition": math.inf,
        "vectors_m": [],
    }


def validate_config(config: Mapping[str, Any]) -> None:
    if config.get("schema_version") != CONFIG_SCHEMA or config.get("stage") != "ID-2Z21":
        raise AuditInputError("wrong ID-2Z21 config identity")
    if config.get("execution_contract") != "server_only_read_only_zero_tsc_zero_fit":
        raise AuditInputError("execution contract changed")
    if config.get("models_fit_or_updated") != 0 or config.get("tsc_calls_or_plant_advances") != 0:
        raise AuditInputError("zero-fit/zero-TSC contract changed")
    if config.get("calibration_and_blind_holdout_reads") != 0:
        raise AuditInputError("calibration/holdout reads are forbidden")
    if config.get("token_alphabet") != ["F", "A", "a", "E", "e", "H"]:
        raise AuditInputError("token alphabet changed")
    if config.get("signed_pair_ids") != ["d00", "d01", "d02", "d03", "d04", "d05"]:
        raise AuditInputError("signed pair set changed")
    if config["sustained_response_gates"].get("segment_origin") != "first_common_prefix_divergence_only":
        raise AuditInputError("segment-origin rule changed")


def verify_tracked_evidence(root: Path, config: Mapping[str, Any]) -> dict[str, Any]:
    verified: dict[str, Any] = {}
    for label, spec in config["evidence"].items():
        path = inside_root(root, str(spec["path"]))
        actual_hash = sha256(path)
        if actual_hash != spec["sha256"]:
            raise AuditInputError(f"{label}: SHA-256 mismatch")
        row: dict[str, Any] = {"path": spec["path"], "sha256": actual_hash}
        if "required_route" in spec:
            payload = load_json(path)
            if payload.get("route") != spec["required_route"]:
                raise AuditInputError(f"{label}: route mismatch")
            row["route"] = payload["route"]
        verified[label] = row
    return verified


def load_development_trajectories(root: Path, config: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    directory = root / "docs/codex/audits/rgeo_zgeo_1ms_id2z18_20260820_dc577537_v1"
    result: dict[str, Mapping[str, Any]] = {}
    expected_hashes = config["development_trajectory_sha256"]
    expected_families = config["development_family_ids"]
    if set(expected_hashes) != set(expected_families):
        raise AuditInputError("development family/hash set mismatch")
    for family_id in expected_families:
        path = inside_root(root, f"{directory.relative_to(root).as_posix()}/{family_id}.json")
        if sha256(path) != expected_hashes[family_id]:
            raise AuditInputError(f"{family_id}: trajectory SHA-256 mismatch")
        row = load_json(path)
        if row.get("family_id") != family_id or row.get("fit_weight") != 1 or not row.get("passed"):
            raise AuditInputError(f"{family_id}: development identity mismatch")
        if len(row.get("states", [])) != 66 or len(row.get("actions", [])) != 65:
            raise AuditInputError(f"{family_id}: incomplete 65-step trajectory")
        result[family_id] = row
    for forbidden in config["forbidden_family_ids"]:
        if (directory / f"{forbidden}.json").exists():
            raise AuditInputError(f"forbidden calibration/holdout trajectory exists: {forbidden}")
    return result


def verify_server_hold(
    server_root: Path, config: Mapping[str, Any], full_f_states: Sequence[Mapping[str, Any]], dt_s: float
) -> tuple[Mapping[str, Any], Mapping[str, Any], dict[str, Any]]:
    spec = config["id2z20_dev_hold_expected_metrics"]
    hold_path = inside_root(server_root, spec["server_relative_path"])
    result_path = inside_root(server_root, spec["primary_result_relative_path"])
    if sha256(hold_path) != spec["sha256"] or sha256(result_path) != spec["primary_result_sha256"]:
        raise AuditInputError("ID2Z20 server compact hash mismatch")
    hold = load_json(hold_path)
    primary = load_json(result_path)
    if primary.get("route") != spec["required_route"]:
        raise AuditInputError("ID2Z20 primary route mismatch")
    states = hold.get("states", [])
    actions = hold.get("actions", [])
    if hold.get("rollout_id") != "dev_hold" or len(states) != 66 or len(actions) != 65:
        raise AuditInputError("ID2Z20 dev_hold structure mismatch")
    for index in range(33):
        for key, tolerance in (("r_geo_m", 1e-12), ("z_geo_m", 1e-12), ("ip_a", 1e-9)):
            require_close(float(states[index][key]), float(full_f_states[index][key]), tolerance, f"hold prefix {index} {key}")
    center = target(actions[31], 14)
    hold_delta = max(float(np.max(np.abs(target(actions[index], 14) - center))) for index in range(32, 65))
    if hold_delta > 1e-9:
        raise AuditInputError(f"ID2Z20 dev_hold is not exact after root: {hold_delta}")
    comparison_index = int(config["lineage_gates"]["comparison_state_index"])
    hold_at_comparison = source_metrics(states, comparison_index, dt_s)
    terminal = terminal_metrics(states, config["terminal_state_indices"], dt_s)
    return hold, primary, {
        "dev_hold_sha256": sha256(hold_path),
        "primary_result_sha256": sha256(result_path),
        "post_root_maximum_target_change_a": hold_delta,
        f"state_{comparison_index}": hold_at_comparison,
        "terminal": terminal,
    }


def execute(root: Path, server_root: Path, config: Mapping[str, Any], source_revision: str) -> dict[str, Any]:
    validate_config(config)
    if HEX40.fullmatch(source_revision) is None:
        raise AuditInputError("source revision must be a full lowercase Git revision")
    tracked = verify_tracked_evidence(root, config)
    trajectories = load_development_trajectories(root, config)
    dt_s = float(config["control_period_ms"]) / 1000.0
    full_f = trajectories["baseline_full_f"]
    full_states = full_f["states"]

    expected = config["full_f_expected_metrics"]
    tolerance = float(expected["absolute_tolerance"])
    full_metrics: dict[str, Any] = {}
    for state_index in (32, 40, 48, 60, 65):
        metrics = source_metrics(full_states, state_index, dt_s)
        frozen = expected[str(state_index)]
        for key in ("distance_m", "speed_m_per_s", "ip_fraction"):
            require_close(metrics[key], float(frozen[key]), tolerance, f"full-F state{state_index} {key}")
        full_metrics[str(state_index)] = metrics
    full_terminal = terminal_metrics(full_states, config["terminal_state_indices"], dt_s)
    require_close(full_terminal["maximum_distance_m"], float(expected["terminal_maximum_distance_m"]), tolerance, "full-F terminal distance")
    require_close(full_terminal["maximum_speed_m_per_s"], float(expected["terminal_maximum_speed_m_per_s"]), tolerance, "full-F terminal speed")
    require_close(full_terminal["maximum_ip_fraction"], float(expected["terminal_maximum_ip_fraction"]), tolerance, "full-F terminal Ip")

    _, _, hold_metrics = verify_server_hold(server_root, config, full_states, dt_s)
    comparison_key = f"state_{config['lineage_gates']['comparison_state_index']}"
    moving_comparison = full_metrics[str(config["lineage_gates"]["comparison_state_index"])]
    held_comparison = hold_metrics[comparison_key]
    lineage = {
        "comparison_state_index": config["lineage_gates"]["comparison_state_index"],
        "held_minus_full_f_distance_m": held_comparison["distance_m"] - moving_comparison["distance_m"],
        "held_minus_full_f_speed_m_per_s": held_comparison["speed_m_per_s"] - moving_comparison["speed_m_per_s"],
        "held_is_not_moving_nominal": False,
        "provenance": "ID2Z20 dev_hold server compact reparsed read-only; ID2Z18 full-F tracked compact reparsed",
    }
    lineage["held_is_not_moving_nominal"] = (
        lineage["held_minus_full_f_distance_m"] >= float(config["lineage_gates"]["minimum_held_minus_full_f_distance_m"])
        and lineage["held_minus_full_f_speed_m_per_s"] >= float(config["lineage_gates"]["minimum_held_minus_full_f_speed_m_per_s"])
    )

    action_gate = config["action_gates"]
    vectors = token_vectors(
        trajectories,
        int(config["development_issue_first"]),
        int(config["development_issue_last"]),
        config["token_alphabet"],
        int(action_gate["coil_count"]),
        float(action_gate["token_reproduction_tolerance_a"]),
    )
    if float(np.max(np.abs(vectors["H"]))) > float(action_gate["zero_hold_tolerance_a"]):
        raise AuditInputError("H token is not exact zero increment")
    nonzero_names = [name for name in config["token_alphabet"] if name != "H"]
    nonzero_matrix = np.column_stack([vectors[name] for name in nonzero_names])
    rank, condition, singular = numerical_rank_condition(
        nonzero_matrix, float(action_gate["rank_relative_tolerance"])
    )
    maximum_token_delta = {name: float(np.max(np.abs(vector))) for name, vector in vectors.items()}
    if any(value > float(action_gate["maximum_per_coil_issue_delta_a"]) + 1e-9 for value in maximum_token_delta.values()):
        raise AuditInputError("observed token exceeds maximum issue delta")
    require_close(
        maximum_token_delta["F"],
        float(action_gate["maximum_per_coil_issue_delta_a"]),
        float(action_gate["full_scale_tolerance_a"]),
        "full-F saturation",
    )
    additive = {
        name: {
            "maximum_absolute_component_a": float(np.max(np.abs(vectors["F"] + vectors[name]))),
            "violates_slew": bool(
                np.max(np.abs(vectors["F"] + vectors[name]))
                > float(action_gate["maximum_per_coil_issue_delta_a"]) + 1e-12
            ),
        }
        for name in ("A", "a", "E", "e")
    }
    additive_rejected = any(row["violates_slew"] for row in additive.values())

    segments: list[dict[str, Any]] = []
    useful_rows: list[dict[str, Any]] = []
    response_gate = config["sustained_response_gates"]
    for pair_id in config["signed_pair_ids"]:
        segment = pair_segment_metrics(
            pair_id,
            trajectories[f"{pair_id}_plus"],
            trajectories[f"{pair_id}_minus"],
            int(config["development_issue_first"]),
            response_gate["horizons_ms"],
            dt_s,
        )
        useful = useful_horizon(segment, response_gate)
        segment["useful_horizon_ms"] = None if useful is None else useful["horizon_ms"]
        segment["useful"] = useful is not None
        segments.append(segment)
        if useful is not None:
            useful_rows.append({"pair_id": pair_id, **dict(useful)})
    geometry = best_two_vector_geometry(useful_rows)

    capture_count = sum(
        capture_passed(row["states"], config["terminal_state_indices"], config["stationary_capture_gate"], dt_s)
        for row in trajectories.values()
    )
    if capture_count != int(config["stationary_capture_gate"]["expected_predecessor_capture_count"]):
        raise AuditInputError(f"predecessor capture count changed: {capture_count}")

    readiness_reasons: list[str] = []
    if not lineage["held_is_not_moving_nominal"]:
        readiness_reasons.append("HELD_MOVING_LINEAGE_NOT_SEPARATED")
    if rank < int(action_gate["minimum_executed_nonzero_token_rank"]):
        readiness_reasons.append("EXECUTED_TOKEN_RANK")
    if condition > float(action_gate["maximum_executed_nonzero_token_condition"]):
        readiness_reasons.append("EXECUTED_TOKEN_CONDITION")
    if not additive_rejected:
        readiness_reasons.append("UNCONDITIONAL_ADDITION_NOT_REJECTED")
    useful_pair_ids = sorted({row["pair_id"] for row in useful_rows})
    if len(useful_pair_ids) < int(response_gate["minimum_useful_distinct_pair_families"]):
        readiness_reasons.append("INSUFFICIENT_PERSISTENT_PAIR_FAMILIES")
    if geometry["condition"] > float(response_gate["maximum_best_two_vector_condition"]):
        readiness_reasons.append("TASK_PLANE_CONDITION")
    if geometry["acute_line_angle_deg"] < float(response_gate["minimum_task_plane_line_angle_deg"]):
        readiness_reasons.append("TASK_PLANE_LINE_ANGLE")

    ready = not readiness_reasons
    routes = config["routes"]
    return {
        "schema_version": SCHEMA,
        "stage": "ID-2Z21",
        "source_revision": source_revision,
        "route": routes["ready"] if ready else routes["not_ready"],
        "passed": ready,
        "audit_completed": True,
        "models_fit_or_updated": 0,
        "tsc_calls_or_plant_advances": 0,
        "calibration_and_blind_holdout_records_read": 0,
        "tracked_evidence": tracked,
        "development_trajectory_count": len(trajectories),
        "full_f_metrics": {**full_metrics, "terminal": full_terminal},
        "id2z20_dev_hold_metrics": hold_metrics,
        "lineage": lineage,
        "action_allocation": {
            "token_vectors_a": {name: [float(value) for value in vector] for name, vector in vectors.items()},
            "maximum_absolute_token_component_a": maximum_token_delta,
            "executed_nonzero_token_names": nonzero_names,
            "executed_nonzero_token_rank": rank,
            "executed_nonzero_token_condition": condition,
            "executed_nonzero_token_singular_values": singular,
            "unconditional_f_plus_residual": additive,
            "unconditional_nominal_plus_residual_rejected": additive_rejected,
            "allocation_semantics": "choose_replace_or_time_share_exact_increment_inside_slew_polytope",
        },
        "sustained_segments": segments,
        "useful_segment_rows": useful_rows,
        "useful_distinct_pair_ids": useful_pair_ids,
        "best_two_vector_geometry": geometry,
        "predecessor_stationary_capture_count": capture_count,
        "moving_terminal_required_fields": config["moving_terminal_required_fields"],
        "readiness_reasons": readiness_reasons,
        "pass_authorizes": config["pass_authorizes"] if ready else "action_basis_or_nominal_redesign_only",
        "claim_boundary": config["claim_boundary"],
    }


def failure_result(source_revision: str, route: str, reason: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA,
        "stage": "ID-2Z21",
        "source_revision": source_revision,
        "route": route,
        "passed": False,
        "audit_completed": False,
        "models_fit_or_updated": 0,
        "tsc_calls_or_plant_advances": 0,
        "calibration_and_blind_holdout_records_read": 0,
        "input_failure_reason": reason,
    }


def write_new(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--server-run-root", type=Path, required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/rgeo_zgeo_1ms_id2z21_moving_nominal_temporal_contract.json"),
    )
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    root = args.repo_root.resolve()
    source_revision = args.source_revision.strip().lower()
    output = args.output.resolve()
    try:
        output.relative_to(root)
    except ValueError:
        print("output must remain inside repository", file=sys.stderr)
        return 2
    try:
        config_path = args.config if args.config.is_absolute() else root / args.config
        config_path = config_path.resolve()
        config_path.relative_to(root)
        if not config_path.is_file() or config_path.is_symlink():
            raise AuditInputError("config is not a regular repository file")
        config = load_json(config_path)
        payload = execute(root, args.server_run_root.resolve(), config, source_revision)
        exit_code = 0
    except Exception as exc:  # preserve a classified zero-TSC result
        try:
            config = load_json((root / args.config).resolve())
            route = config.get("routes", {}).get(
                "input_or_evidence_fail", "ONE_MS_ID2Z21_INPUT_OR_EVIDENCE_FAIL_NO_TSC"
            )
        except Exception:
            route = "ONE_MS_ID2Z21_INPUT_OR_EVIDENCE_FAIL_NO_TSC"
        payload = failure_result(source_revision, route, f"{type(exc).__name__}: {exc}")
        exit_code = 2
    try:
        write_new(output, payload)
    except FileExistsError:
        print(f"refusing to overwrite output: {output}", file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
