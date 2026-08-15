#!/usr/bin/env python3
"""Zero-TSC, zero-fit readiness audit for the ID2A development records."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_id2a_duration_history_development import rollout_specs  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-id2b0-model-readiness-audit-result-v1"
CONFIG_SHA256 = "c0a8d05dab66412617d4f8a18e4ceb151a622f86f7fcfc944fad1b6e70e72f93"
ID2A_SOURCE_REVISION = "d25ee2a9e6112f9da25014b5349888298e1bd500"
INPUT_FAIL_ROUTE = "ONE_MS_ID2B0_INPUT_OR_RAW_INTEGRITY_FAIL_STOP"
SUPPORT_FAIL_ROUTE = "ONE_MS_ID2B0_CAUSAL_SUPPORT_FAIL_TARGETED_TSC_REQUIRED"
COMPLETE_ROUTE = "ONE_MS_ID2B0_READINESS_COMPLETE_ID2B1_REDESIGN_REQUIRED"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inside(root: Path, path: Path, label: str) -> Path:
    root = root.resolve()
    resolved = path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} leaves repository root") from exc
    return resolved


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def load_config(repo_root: Path, config_path: Path) -> dict[str, Any]:
    path = inside(repo_root, config_path, "config")
    if sha256_file(path) != CONFIG_SHA256:
        raise ValueError("ID2B0 config hash mismatch")
    config = read_json(path)
    if config.get("schema_version") != "rgeo-zgeo-1ms-id2b0-model-readiness-audit-v1":
        raise ValueError("ID2B0 schema mismatch")
    if config.get("plant_advances") != 0 or config.get("model_fit_or_training") is not False:
        raise ValueError("ID2B0 must remain zero-plant and zero-fit")
    if config.get("holdout_records_read") != 0 or config.get("server_raw_read_only") is not True:
        raise ValueError("ID2B0 data-role mismatch")
    if config.get("routes") != {
        "input_or_raw_fail": INPUT_FAIL_ROUTE,
        "causal_support_fail": SUPPORT_FAIL_ROUTE,
        "complete": COMPLETE_ROUTE,
    }:
        raise ValueError("ID2B0 route mismatch")
    history = config.get("available_takeover_history", {})
    if history.get("state_indices") != [0, 10] or history.get("issue_indices") != [0, 9]:
        raise ValueError("ID2B0 history contract mismatch")
    if history.get("maximum_true_explicit_action_lag_at_origin") != 10:
        raise ValueError("ID2B0 history length mismatch")
    return config


def _verify_bound_file(repo_root: Path, spec: dict[str, Any], label: str) -> Path:
    path = inside(repo_root, repo_root / spec["path"], label)
    if sha256_file(path) != spec["sha256"]:
        raise ValueError(f"{label} hash mismatch")
    return path


def _numeric_array(states: Sequence[dict[str, Any]]) -> np.ndarray:
    return np.asarray(
        [[float(row["r_geo_m"]), float(row["z_geo_m"]), float(row["ip_a"])] for row in states],
        dtype=float,
    )


def _turning_points(values: Sequence[float]) -> int:
    return sum(
        (values[index] - values[index - 1]) * (values[index + 1] - values[index]) < 0.0
        for index in range(1, len(values) - 1)
    )


def _finite_ratio(numerator: float, denominator: float) -> float | None:
    if denominator <= 0.0:
        return None
    return float(numerator / denominator)


def _compact_inventory(paths: Iterable[Path], root: Path) -> dict[str, Any]:
    lines: list[str] = []
    total = 0
    count = 0
    for path in sorted(paths):
        size = path.stat().st_size
        digest = sha256_file(path)
        total += size
        count += 1
        lines.append(f"{path.relative_to(root).as_posix()}\t{size}\t{digest}")
    payload = "".join(f"{line}\n" for line in lines).encode("utf-8")
    return {
        "compact_files": count,
        "compact_bytes": total,
        "compact_inventory_sha256": hashlib.sha256(payload).hexdigest(),
    }


def load_id2a_rows(
    repo_root: Path,
    config: dict[str, Any],
    run_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    run_dir = inside(repo_root, run_dir, "ID2A run directory")
    if run_dir.name != config["id2a_remote_run_directory"]:
        raise ValueError("ID2A run-directory identity mismatch")
    stage_path = _verify_bound_file(repo_root, config["id2a_stage_config"], "ID2A stage config")
    _verify_bound_file(repo_root, config["id2a_compact_evidence"], "ID2A compact evidence")
    old_path = inside(
        repo_root,
        repo_root / config["superseded_unexecuted_id2b_v1"]["path"],
        "superseded ID2B v1",
    )
    if sha256_file(old_path) != config["superseded_unexecuted_id2b_v1"]["sha256"]:
        raise ValueError("superseded ID2B v1 hash mismatch")

    primary_path = run_dir / "result.json"
    independent_path = run_dir / "independent_audit.json"
    if sha256_file(primary_path) != config["id2a_primary_result_sha256"]:
        raise ValueError("ID2A primary result hash mismatch")
    if sha256_file(independent_path) != config["id2a_independent_audit_sha256"]:
        raise ValueError("ID2A independent audit hash mismatch")
    primary = read_json(primary_path)
    independent = read_json(independent_path)
    required = config["required_id2a_identity"]
    checks = {
        "route": primary.get("route"),
        "rollouts": primary.get("rollouts_completed"),
        "verified_plant_advances": primary.get("verified_plant_advances"),
        "required_artifact_files": primary.get("required_artifact_files"),
        "required_artifact_bytes": primary.get("required_artifact_bytes"),
        "required_artifact_inventory_sha256": primary.get("required_artifact_inventory_sha256"),
    }
    if checks != {key: required[key] for key in checks}:
        raise ValueError("ID2A primary identity mismatch")
    if primary.get("passed") is not True or primary.get("model_fit_data_eligible") is not True:
        raise ValueError("ID2A data are not fit eligible")
    if independent.get("audit_passed") is not True or independent.get("recomputed_scientific_route") != required["route"]:
        raise ValueError("ID2A independent identity mismatch")
    if independent.get("raw_states_reparsed") != required["states"]:
        raise ValueError("ID2A raw-state count mismatch")

    stage = read_json(stage_path)
    specs = rollout_specs(stage)
    rows: list[dict[str, Any]] = []
    compact_paths: list[Path] = []
    for spec in specs:
        path = run_dir / f"{spec['rollout_id']}.json"
        if not path.is_file():
            raise ValueError(f"missing ID2A compact: {spec['rollout_id']}")
        row = read_json(path)
        compact_paths.append(path)
        for key in (
            "rollout_id",
            "context_id",
            "prefix_id",
            "is_context_baseline",
            "direction_id",
            "sign",
            "duration_issues",
            "repeat_index",
        ):
            if row.get(key) != spec.get(key):
                raise ValueError(f"ID2A compact identity mismatch: {spec['rollout_id']}:{key}")
        if row.get("schema_version") != "rgeo-zgeo-1ms-id2a-duration-history-development-v1":
            raise ValueError(f"ID2A compact schema mismatch: {spec['rollout_id']}")
        if row.get("source_revision") != ID2A_SOURCE_REVISION or row.get("passed") is not True:
            raise ValueError(f"ID2A compact revision/verdict mismatch: {spec['rollout_id']}")
        if len(row.get("states", [])) != 33 or len(row.get("actions", [])) != 32:
            raise ValueError(f"ID2A compact length mismatch: {spec['rollout_id']}")
        if any(state.get("time_ms") != 1100 + index for index, state in enumerate(row["states"])):
            raise ValueError(f"ID2A compact clock mismatch: {spec['rollout_id']}")
        rows.append(row)
    return stage, primary, rows, _compact_inventory(compact_paths, run_dir)


def _prefix_payload(row: dict[str, Any], origin: int) -> dict[str, Any]:
    return {
        "states": [
            {
                "time_ms": state["time_ms"],
                "r_geo_m": state["r_geo_m"],
                "z_geo_m": state["z_geo_m"],
                "ip_a": state["ip_a"],
                "actual_current_decimal_a_tsc": state["actual_current_decimal_a_tsc"],
            }
            for state in row["states"][: origin + 1]
        ],
        "actions": [
            {
                "issue_step": action["issue_step"],
                "expected_card15_fields": action["expected_card15_fields"],
                "target_current_a_tsc": action["target_current_a_tsc"],
            }
            for action in row["actions"][:origin]
        ],
    }


def _prefix_vector(
    row: dict[str, Any],
    origin: int,
    scales: dict[str, float],
) -> np.ndarray:
    state0 = row["states"][0]
    q0 = np.asarray([float(value) for value in state0["actual_current_decimal_a_tsc"]])
    values: list[float] = []
    for state in row["states"][: origin + 1]:
        values.extend(
            [
                (float(state["r_geo_m"]) - float(state0["r_geo_m"])) / scales["r_geo_m"],
                (float(state["z_geo_m"]) - float(state0["z_geo_m"])) / scales["z_geo_m"],
                (float(state["ip_a"]) - float(state0["ip_a"])) / scales["ip_a"],
            ]
        )
        current = np.asarray([float(value) for value in state["actual_current_decimal_a_tsc"]])
        values.extend(((current - q0) / scales["coil_current_a"]).tolist())
    for action in row["actions"][:origin]:
        target = np.asarray(action["target_current_a_tsc"], dtype=float)
        values.extend(((target - q0) / scales["coil_current_a"]).tolist())
    return np.asarray(values, dtype=float)


def _instant_vector(row: dict[str, Any], origin: int, scales: dict[str, float]) -> np.ndarray:
    state = row["states"][origin]
    state0 = row["states"][0]
    q0 = np.asarray([float(value) for value in state0["actual_current_decimal_a_tsc"]])
    current = np.asarray([float(value) for value in state["actual_current_decimal_a_tsc"]])
    return np.asarray(
        [
            (float(state["r_geo_m"]) - float(state0["r_geo_m"])) / scales["r_geo_m"],
            (float(state["z_geo_m"]) - float(state0["z_geo_m"])) / scales["z_geo_m"],
            (float(state["ip_a"]) - float(state0["ip_a"])) / scales["ip_a"],
            *((current - q0) / scales["coil_current_a"]).tolist(),
        ],
        dtype=float,
    )


def output_response_hankel(
    responses: Sequence[np.ndarray],
    scales: dict[str, float],
    block_rows: int,
    energy_fractions: Sequence[float],
) -> dict[str, Any]:
    output_scale = np.asarray([scales["r_geo_m"], scales["z_geo_m"], scales["ip_a"]])
    blocks: list[np.ndarray] = []
    for response in responses:
        scaled = np.asarray(response, dtype=float) / output_scale
        if scaled.shape[0] < block_rows:
            raise ValueError("response is shorter than Hankel block rows")
        columns = [scaled[start : start + block_rows].reshape(-1) for start in range(scaled.shape[0] - block_rows + 1)]
        blocks.append(np.stack(columns, axis=1))
    matrix = np.concatenate(blocks, axis=1)
    singular = np.linalg.svd(matrix, compute_uv=False)
    squared = singular * singular
    total = float(np.sum(squared))
    ranks: dict[str, int] = {}
    cumulative = np.cumsum(squared) / total if total > 0.0 else np.zeros_like(squared)
    for fraction in energy_fractions:
        ranks[str(fraction)] = int(np.searchsorted(cumulative, fraction, side="left") + 1) if total > 0.0 else 0
    return {
        "rows": int(matrix.shape[0]),
        "columns": int(matrix.shape[1]),
        "numerical_rank": int(np.linalg.matrix_rank(matrix)),
        "singular_values": singular.tolist(),
        "energy_ranks": ranks,
        "descriptive_only_not_plant_order": True,
    }


def analyze_rows(
    rows: Sequence[dict[str, Any]],
    config: dict[str, Any],
    stage: dict[str, Any],
) -> dict[str, Any]:
    origin = config["prediction_origin_state_index"]
    start, stop = config["response_state_range"]
    contexts = config["contexts"]
    scales = config["descriptive_scales"]
    baselines: dict[str, dict[str, Any]] = {}
    for context in contexts:
        selected = [row for row in rows if row["context_id"] == context and row["is_context_baseline"]]
        if len(selected) != 1:
            raise ValueError(f"expected one matched baseline: {context}")
        baselines[context] = selected[0]

    prefix_rows: dict[str, dict[str, Any]] = {}
    sibling_prefix_exact: dict[str, bool] = {}
    for context in contexts:
        siblings = [row for row in rows if row["context_id"] == context]
        reference = _prefix_payload(siblings[0], origin)
        sibling_prefix_exact[context] = all(_prefix_payload(row, origin) == reference for row in siblings[1:])
        if not sibling_prefix_exact[context]:
            raise ValueError(f"context siblings do not share a causal prefix: {context}")
        prefix_rows[context] = baselines[context]

    responses: dict[str, np.ndarray] = {}
    per_arm: list[dict[str, Any]] = []
    unique_response_arrays: list[np.ndarray] = []
    for row in rows:
        if row["is_context_baseline"]:
            continue
        baseline = _numeric_array(baselines[row["context_id"]]["states"])
        response = _numeric_array(row["states"]) - baseline
        responses[row["rollout_id"]] = response
        if row["repeat_index"] != 0:
            continue
        window = response[start : stop + 1]
        rz_norm_mm = np.linalg.norm(window[:, :2], axis=1) * 1000.0
        peak_offset = int(np.argmax(rz_norm_mm))
        peak = float(rz_norm_mm[peak_offset])
        unique_response_arrays.append(window)
        per_arm.append(
            {
                "rollout_id": row["rollout_id"],
                "context_id": row["context_id"],
                "direction_id": row["direction_id"],
                "sign": row["sign"],
                "duration_issues": row["duration_issues"],
                "peak_rz_norm_mm": peak,
                "peak_state_index": start + peak_offset,
                "terminal_rz_norm_mm": float(rz_norm_mm[-1]),
                "terminal_peak_fraction": _finite_ratio(float(rz_norm_mm[-1]), peak),
                "maximum_absolute_ip_response_a": float(np.max(np.abs(window[:, 2]))),
                "rz_norm_turning_points": _turning_points(rz_norm_mm.tolist()),
                "response_profile": [
                    {
                        "state_index": state_index,
                        "r_mm": float(value[0] * 1000.0),
                        "z_mm": float(value[1] * 1000.0),
                        "ip_a": float(value[2]),
                    }
                    for state_index, value in zip(range(start, stop + 1), window)
                ],
            }
        )
    if len(per_arm) != 36:
        raise ValueError(f"unexpected unique action-cell count: {len(per_arm)}")

    nominal = {}
    for context, row in baselines.items():
        states = _numeric_array(row["states"])
        delta = states[stop] - states[origin]
        nominal[context] = {
            "state10_to_state32_r_mm": float(delta[0] * 1000.0),
            "state10_to_state32_z_mm": float(delta[1] * 1000.0),
            "state10_to_state32_ip_a": float(delta[2]),
        }

    sign_pairs = []
    for context in contexts:
        for direction in stage["directions"]:
            for duration in stage["durations_issues"]:
                plus = next(
                    row for row in rows
                    if row["context_id"] == context and row["direction_id"] == direction
                    and row["sign"] == "plus" and row["duration_issues"] == duration
                    and row["repeat_index"] == 0
                )
                minus = next(
                    row for row in rows
                    if row["context_id"] == context and row["direction_id"] == direction
                    and row["sign"] == "minus" and row["duration_issues"] == duration
                    and row["repeat_index"] == 0
                )
                plus_response = responses[plus["rollout_id"]][start : stop + 1]
                minus_response = responses[minus["rollout_id"]][start : stop + 1]
                even = 0.5 * (plus_response + minus_response)
                odd = 0.5 * (plus_response - minus_response)
                even_peak = float(np.max(np.linalg.norm(even[:, :2], axis=1)) * 1000.0)
                odd_peak = float(np.max(np.linalg.norm(odd[:, :2], axis=1)) * 1000.0)
                sign_pairs.append(
                    {
                        "context_id": context,
                        "direction_id": direction,
                        "duration_issues": duration,
                        "maximum_even_rz_norm_mm": even_peak,
                        "maximum_odd_rz_norm_mm": odd_peak,
                        "even_to_odd_peak_ratio": _finite_ratio(even_peak, odd_peak),
                    }
                )

    context_pairs = []
    collisions = []
    material = float(stage["identifiability_gates"]["minimum_peak_rz_response_norm_m_per_context_direction_sign"])
    for left_index, left_context in enumerate(contexts):
        for right_context in contexts[left_index + 1 :]:
            left_row = prefix_rows[left_context]
            right_row = prefix_rows[right_context]
            left_payload = _prefix_payload(left_row, origin)
            right_payload = _prefix_payload(right_row, origin)
            instant_distance = float(np.linalg.norm(_instant_vector(left_row, origin, scales) - _instant_vector(right_row, origin, scales)))
            prefix_distance = float(np.linalg.norm(_prefix_vector(left_row, origin, scales) - _prefix_vector(right_row, origin, scales)))
            state_left = left_row["states"][origin]
            state_right = right_row["states"][origin]
            critical_left = next(
                row for row in rows
                if row["context_id"] == left_context and row["direction_id"] == "p09_half_exact_center"
                and row["sign"] == "minus" and row["duration_issues"] == 4 and row["repeat_index"] == 0
            )
            critical_right = next(
                row for row in rows
                if row["context_id"] == right_context and row["direction_id"] == "p09_half_exact_center"
                and row["sign"] == "minus" and row["duration_issues"] == 4 and row["repeat_index"] == 0
            )
            curve_difference = responses[critical_left["rollout_id"]][start : stop + 1, :2] - responses[critical_right["rollout_id"]][start : stop + 1, :2]
            max_difference = float(np.max(np.linalg.norm(curve_difference, axis=1)))
            prefix_exact = left_payload == right_payload
            collision = prefix_exact and max_difference >= material
            if collision:
                collisions.append(f"{left_context}:{right_context}:p09_minus_d4")
            left_current = np.asarray([float(value) for value in state_left["actual_current_decimal_a_tsc"]])
            right_current = np.asarray([float(value) for value in state_right["actual_current_decimal_a_tsc"]])
            context_pairs.append(
                {
                    "left_context": left_context,
                    "right_context": right_context,
                    "instantaneous_scaled_distance": instant_distance,
                    "complete_prefix_scaled_distance": prefix_distance,
                    "complete_prefix_exact": prefix_exact,
                    "state10_r_difference_mm": float((float(state_left["r_geo_m"]) - float(state_right["r_geo_m"])) * 1000.0),
                    "state10_z_difference_mm": float((float(state_left["z_geo_m"]) - float(state_right["z_geo_m"])) * 1000.0),
                    "state10_ip_difference_a": float(float(state_left["ip_a"]) - float(state_right["ip_a"])),
                    "state10_maximum_coil_difference_a": float(np.max(np.abs(left_current - right_current))),
                    "p09_minus_d4_maximum_curve_difference_mm": max_difference * 1000.0,
                    "material_exact_collision": collision,
                }
            )

    hankel_cfg = config["output_response_hankel"]
    hankel = output_response_hankel(
        unique_response_arrays,
        scales,
        int(hankel_cfg["block_rows"]),
        [float(value) for value in hankel_cfg["energy_fractions"]],
    )
    peaks = [row["peak_rz_norm_mm"] for row in per_arm]
    critical_peaks = {
        context: next(
            row["peak_rz_norm_mm"] for row in per_arm
            if row["context_id"] == context and row["direction_id"] == "p09_half_exact_center"
            and row["sign"] == "minus" and row["duration_issues"] == 4
        )
        for context in contexts
    }
    return {
        "counts": {
            "whole_trajectory_records": len(rows),
            "unique_whole_trajectory_cells": 39,
            "independent_context_groups": len(contexts),
            "matched_baselines": len(baselines),
            "unique_action_cells": len(per_arm),
            "exact_critical_replays": len(rows) - 39,
        },
        "sibling_prefix_exact": sibling_prefix_exact,
        "nominal_state10_to_state32": nominal,
        "per_arm": per_arm,
        "signed_even_odd": sign_pairs,
        "context_pairs": context_pairs,
        "exact_causal_collisions": collisions,
        "critical_p09_minus_d4_peak_rz_mm": critical_peaks,
        "critical_peak_maximum_to_minimum_ratio": max(critical_peaks.values()) / min(critical_peaks.values()),
        "minimum_action_peak_rz_mm": min(peaks),
        "maximum_action_peak_rz_mm": max(peaks),
        "output_response_hankel": hankel,
    }


def audit_old_id2b(repo_root: Path, config: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
    spec = config["superseded_unexecuted_id2b_v1"]
    path = inside(repo_root, repo_root / spec["path"], "ID2B v1")
    old = read_json(path)
    candidates = old.get("candidates", [])
    maximum_lag = max(int(row.get("history_lags", 0)) for row in candidates)
    stable_candidates = [row["model_id"] for row in candidates if row.get("kind") == "stable_state_space"]
    geometry_gate_mm = float(old["eligibility_gates"]["maximum_r_geo_point_error_m_each_fold"]) * 1000.0
    minimum_peak = float(analysis["minimum_action_peak_rz_mm"])
    return {
        "config_sha256": sha256_file(path),
        "prediction_start_state_index": old.get("prediction_start_state_index"),
        "declared_history_steps": old.get("history_steps"),
        "maximum_candidate_explicit_lag": maximum_lag,
        "maximum_true_lag_at_origin": config["available_takeover_history"]["maximum_true_explicit_action_lag_at_origin"],
        "lag_contract_valid": maximum_lag <= config["available_takeover_history"]["maximum_true_explicit_action_lag_at_origin"],
        "explicitly_stable_state_space_candidates": stable_candidates,
        "stable_state_space_candidate_present": bool(stable_candidates),
        "recursive_rollout_uses_actual_current_feature": bool(old.get("recursive_rollout")) and "actual_current_a_tsc" in old.get("features", []),
        "future_actual_current_propagation_frozen": False,
        "geometry_point_gate_mm": geometry_gate_mm,
        "minimum_measured_action_peak_mm": minimum_peak,
        "geometry_gate_to_minimum_action_peak_ratio": geometry_gate_mm / minimum_peak,
        "action_conditioned_differential_gate_present": False,
        "residual_backbone_and_seed_aggregation_frozen": False,
        "executable_as_frozen": False,
        "status": "unexecuted_superseded_before_model_fit",
        "defects": config["current_id2b_v1_known_defects"],
    }


def build_result(
    repo_root: Path,
    config_path: Path,
    run_dir: Path,
    source_revision: str,
) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{40}", source_revision):
        raise ValueError("source revision must be a full lowercase Git hash")
    config = load_config(repo_root, config_path)
    stage, primary, rows, compact_inventory = load_id2a_rows(repo_root, config, run_dir)
    analysis = analyze_rows(rows, config, stage)
    old_audit = audit_old_id2b(repo_root, config, analysis)
    support_passed = not analysis["exact_causal_collisions"]
    route = COMPLETE_ROUTE if support_passed else SUPPORT_FAIL_ROUTE
    return {
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "config_sha256": CONFIG_SHA256,
        "passed": support_passed,
        "route": route,
        "failures": [] if support_passed else ["EXACT_CAUSAL_PREFIX_RESPONSE_COLLISION"],
        "id2a_identity": {
            "source_revision": primary["source_revision"],
            "stage_config_sha256": primary["stage_config_sha256"],
            "route": primary["route"],
            "required_artifact_files": primary["required_artifact_files"],
            "required_artifact_bytes": primary["required_artifact_bytes"],
            "required_artifact_inventory_sha256": primary["required_artifact_inventory_sha256"],
            **compact_inventory,
        },
        "analysis": analysis,
        "superseded_id2b_v1_audit": old_audit,
        "prediction_contract": {
            "current_r_geo_z_geo_ip_and_actual_current": "exact_noiseless_observed_before_each_real_issue",
            "rolling_prediction": "recenter_on_new_truth_each_one_ms_cycle",
            "cold_recursive_origin_state_index": config["prediction_origin_state_index"],
            "true_burn_in_states": config["available_takeover_history"]["state_indices"],
            "true_burn_in_actions": config["available_takeover_history"]["issue_indices"],
            "future_candidate_issued_actions": "known_to_planner",
            "future_actual_current_readback": "unknown_and_must_be_propagated_without_future_truth",
            "matched_future_baseline": "evaluator_only",
        },
        "id2b1_requirements": {
            "baselines": ["persistence", "last_velocity", "time_indexed_nominal", "action_blind_history", "simple_action_fir"],
            "structured_center": "exact_actuator_queue_plus_stable_low_order_innovation_state_space",
            "signed_context_forcing": "prospectively_fixed_sign_split_and_causal_history_interaction",
            "residual": "optional_small_gru_or_tcn_without_seed_shopping",
            "evaluation": ["absolute_recursive_rzi", "paired_action_response", "rolling_origins", "worst_complete_context_fold"],
            "calibration_holdout_controller_use": "forbidden_until_fresh_later_stages",
        },
        "claim_boundary": {
            "limited_id2a_context_model_comparison_supported": support_passed,
            "context_robustness_claimed": False,
            "position_time_history_factorization_complete": False,
            "arbitrary_14_coil_action_supported": False,
            "uncertainty_calibrated": False,
            "controller_or_recovery_qualified": False,
        },
        "counters": {
            "server_raw_records_read": 42,
            "raw_states_reparsed_by_primary": 0,
            "plant_advances": 0,
            "tsc_calls": 0,
            "models_fit_or_trained": 0,
            "holdout_records_read": 0,
        },
        "data_role": config["data_role"],
    }


def execute(
    repo_root: Path,
    config_path: Path,
    run_dir: Path,
    output_dir: Path,
    source_revision: str,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    output_dir = inside(repo_root, output_dir, "output directory")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite output directory: {output_dir}")
    output_dir.mkdir(parents=True)
    try:
        result = build_result(repo_root, config_path, run_dir, source_revision)
    except Exception as exc:
        result = {
            "schema_version": SCHEMA,
            "source_revision": source_revision,
            "config_sha256": CONFIG_SHA256,
            "passed": False,
            "route": INPUT_FAIL_ROUTE,
            "failures": [f"{type(exc).__name__}:{exc}"],
            "counters": {
                "plant_advances": 0,
                "tsc_calls": 0,
                "models_fit_or_trained": 0,
                "holdout_records_read": 0,
            },
        }
    (output_dir / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path, default=Path("configs/rgeo_zgeo_1ms_id2b0_model_readiness_audit.json"))
    parser.add_argument("--id2a-run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    run_dir = args.id2a_run_dir if args.id2a_run_dir.is_absolute() else root / args.id2a_run_dir
    output_dir = args.output_dir if args.output_dir.is_absolute() else root / args.output_dir
    result = execute(root, config_path, run_dir, output_dir, args.source_revision)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
