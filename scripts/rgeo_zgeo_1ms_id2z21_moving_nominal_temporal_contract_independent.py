#!/usr/bin/env python3
"""Structurally separate recomputation of the ID-2Z21 compact result."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

import numpy as np


SCHEMA = "rgeo-zgeo-1ms-id2z21-moving-nominal-temporal-contract-independent-v1"
HEX40 = re.compile(r"[0-9a-f]{40}\Z")


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                return value.hexdigest()
            value.update(block)


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def regular_below(root: Path, relative: str) -> Path:
    path = (root / relative).resolve(strict=True)
    path.relative_to(root)
    if not path.is_file() or path.is_symlink():
        raise ValueError(relative)
    return path


def rz(row: Mapping[str, Any]) -> np.ndarray:
    result = np.asarray([float(row["r_geo_m"]), float(row["z_geo_m"])], dtype=float)
    if not np.all(np.isfinite(result)):
        raise ValueError("non-finite R/Z")
    return result


def speed(states: Sequence[Mapping[str, Any]], index: int) -> float:
    return float(np.linalg.norm(rz(states[index]) - rz(states[index - 1])) / 0.001)


def state_metrics(states: Sequence[Mapping[str, Any]], index: int) -> dict[str, float]:
    source = states[0]
    return {
        "distance_m": float(np.linalg.norm(rz(states[index]) - rz(source))),
        "speed_m_per_s": speed(states, index),
        "ip_fraction": abs(float(states[index]["ip_a"]) - float(source["ip_a"]))
        / abs(float(source["ip_a"])),
    }


def action_target(row: Mapping[str, Any]) -> np.ndarray:
    target = np.asarray(row["target_current_a_tsc"], dtype=float)
    if target.shape != (14,) or not np.all(np.isfinite(target)):
        raise ValueError("invalid target")
    return target


def recompute_token_vectors(trajectories: Mapping[str, Mapping[str, Any]]) -> dict[str, np.ndarray]:
    groups: dict[str, list[np.ndarray]] = {name: [] for name in "FAaEeH"}
    for row in trajectories.values():
        actions = row["actions"]
        for offset, token in enumerate(row["tokens"]):
            issue = 16 + offset
            groups[token].append(action_target(actions[issue]) - action_target(actions[issue - 1]))
    result: dict[str, np.ndarray] = {}
    for name, values in groups.items():
        if not values:
            raise ValueError(f"missing token {name}")
        array = np.stack(values)
        if float(np.max(np.abs(array - array[0]))) > 1e-9:
            raise ValueError(f"token mismatch {name}")
        result[name] = array[0]
    return result


def common_origin(plus: Mapping[str, Any], minus: Mapping[str, Any]) -> int:
    for offset, values in enumerate(zip(plus["tokens"], minus["tokens"])):
        if values[0] != values[1]:
            issue = 16 + offset
            if float(np.max(np.abs(rz(plus["states"][issue]) - rz(minus["states"][issue])))) > 1e-12:
                raise ValueError("unmatched first divergence")
            return issue
    raise ValueError("no divergence")


def response_rows(pair_id: str, plus: Mapping[str, Any], minus: Mapping[str, Any]) -> list[dict[str, Any]]:
    origin = common_origin(plus, minus)
    output: list[dict[str, Any]] = []
    for horizon in (2, 4, 8):
        endpoint = origin + horizon
        vector = rz(plus["states"][endpoint]) - rz(minus["states"][endpoint])
        velocity = (
            rz(plus["states"][endpoint])
            - rz(plus["states"][endpoint - 1])
            - rz(minus["states"][endpoint])
            + rz(minus["states"][endpoint - 1])
        ) / 0.001
        norms = [
            float(np.linalg.norm(rz(plus["states"][index]) - rz(minus["states"][index])))
            for index in range(max(origin + 1, endpoint - 2), endpoint + 1)
        ]
        median = float(np.median(norms))
        output.append(
            {
                "pair_id": pair_id,
                "first_divergence_issue": origin,
                "horizon_ms": horizon,
                "rz_vector_m": [float(value) for value in vector],
                "rz_separation_m": float(np.linalg.norm(vector)),
                "terminal_velocity_separation_m_per_s": float(np.linalg.norm(velocity)),
                "three_state_median_rz_separation_m": median,
                "peak_to_three_state_median_ratio": math.inf if median <= 0 else max(norms) / median,
            }
        )
    return output


def useful(rows: Sequence[Mapping[str, Any]], gate: Mapping[str, Any]) -> Mapping[str, Any] | None:
    for horizon, threshold in (
        (4, float(gate["minimum_four_ms_rz_separation_m"])),
        (8, float(gate["minimum_eight_ms_rz_separation_m"])),
    ):
        row = next(item for item in rows if item["horizon_ms"] == horizon)
        if (
            row["rz_separation_m"] >= threshold
            and row["terminal_velocity_separation_m_per_s"]
            >= float(gate["minimum_terminal_velocity_separation_m_per_s"])
            and row["three_state_median_rz_separation_m"]
            >= float(gate["minimum_three_state_median_rz_separation_m"])
            and row["peak_to_three_state_median_ratio"]
            <= float(gate["maximum_peak_to_three_state_median_ratio"])
        ):
            return row
    return None


def geometry(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    choices: list[dict[str, Any]] = []
    for left_index, left in enumerate(rows):
        for right in rows[left_index + 1 :]:
            if left["pair_id"] == right["pair_id"]:
                continue
            left_vector = np.asarray(left["rz_vector_m"], dtype=float)
            right_vector = np.asarray(right["rz_vector_m"], dtype=float)
            singular = np.linalg.svd(np.column_stack([left_vector, right_vector]), compute_uv=False)
            condition = math.inf if singular[-1] <= 0 else float(singular[0] / singular[-1])
            cosine = abs(float(np.dot(left_vector, right_vector))) / (
                float(np.linalg.norm(left_vector)) * float(np.linalg.norm(right_vector))
            )
            choices.append(
                {
                    "pair_ids": [left["pair_id"], right["pair_id"]],
                    "horizons_ms": [left["horizon_ms"], right["horizon_ms"]],
                    "condition": condition,
                    "acute_line_angle_deg": math.degrees(math.acos(max(-1.0, min(1.0, cosine)))),
                }
            )
    return min(choices, key=lambda row: (row["condition"], -row["acute_line_angle_deg"], row["pair_ids"]))


def close(actual: Any, expected: Any, tolerance: float, failures: list[str], label: str) -> None:
    if not math.isfinite(float(actual)) or abs(float(actual) - float(expected)) > tolerance:
        failures.append(label)


def execute(root: Path, server_root: Path, config: Mapping[str, Any], primary: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    directory = root / "docs/codex/audits/rgeo_zgeo_1ms_id2z18_20260820_dc577537_v1"
    trajectories: dict[str, Mapping[str, Any]] = {}
    for family_id in config["development_family_ids"]:
        path = regular_below(root, f"{directory.relative_to(root).as_posix()}/{family_id}.json")
        if digest(path) != config["development_trajectory_sha256"][family_id]:
            failures.append(f"HASH_{family_id}")
        trajectories[family_id] = read(path)

    full_states = trajectories["baseline_full_f"]["states"]
    full48 = state_metrics(full_states, 48)
    hold_spec = config["id2z20_dev_hold_expected_metrics"]
    hold_path = regular_below(server_root, hold_spec["server_relative_path"])
    hold_result_path = regular_below(server_root, hold_spec["primary_result_relative_path"])
    if digest(hold_path) != hold_spec["sha256"]:
        failures.append("HOLD_HASH")
    if digest(hold_result_path) != hold_spec["primary_result_sha256"]:
        failures.append("HOLD_RESULT_HASH")
    hold = read(hold_path)
    hold48 = state_metrics(hold["states"], 48)
    lineage_distance = hold48["distance_m"] - full48["distance_m"]
    lineage_speed = hold48["speed_m_per_s"] - full48["speed_m_per_s"]

    vectors = recompute_token_vectors(trajectories)
    matrix = np.column_stack([vectors[name] for name in ("F", "A", "a", "E", "e")])
    singular = np.linalg.svd(matrix, compute_uv=False)
    rank = int(np.sum(singular > singular[0] * float(config["action_gates"]["rank_relative_tolerance"])))
    condition = float(singular[0] / singular[rank - 1])
    additive = {
        name: float(np.max(np.abs(vectors["F"] + vectors[name])))
        for name in ("A", "a", "E", "e")
    }

    useful_rows: list[dict[str, Any]] = []
    segments: dict[str, list[dict[str, Any]]] = {}
    for pair_id in config["signed_pair_ids"]:
        rows = response_rows(pair_id, trajectories[f"{pair_id}_plus"], trajectories[f"{pair_id}_minus"])
        segments[pair_id] = rows
        selected = useful(rows, config["sustained_response_gates"])
        if selected is not None:
            useful_rows.append(dict(selected))
    best = geometry(useful_rows)

    close(rank, primary["action_allocation"]["executed_nonzero_token_rank"], 0, failures, "PRIMARY_RANK")
    close(condition, primary["action_allocation"]["executed_nonzero_token_condition"], 1e-12, failures, "PRIMARY_CONDITION")
    close(lineage_distance, primary["lineage"]["held_minus_full_f_distance_m"], 1e-12, failures, "PRIMARY_LINEAGE_DISTANCE")
    close(lineage_speed, primary["lineage"]["held_minus_full_f_speed_m_per_s"], 1e-12, failures, "PRIMARY_LINEAGE_SPEED")
    close(best["condition"], primary["best_two_vector_geometry"]["condition"], 1e-12, failures, "PRIMARY_GEOMETRY_CONDITION")
    close(best["acute_line_angle_deg"], primary["best_two_vector_geometry"]["acute_line_angle_deg"], 1e-12, failures, "PRIMARY_GEOMETRY_ANGLE")
    if best["pair_ids"] != primary["best_two_vector_geometry"]["pair_ids"]:
        failures.append("PRIMARY_GEOMETRY_PAIR_IDS")
    if sorted(row["pair_id"] for row in useful_rows) != primary["useful_distinct_pair_ids"]:
        failures.append("PRIMARY_USEFUL_PAIR_IDS")
    expected_reasons = []
    if condition > float(config["action_gates"]["maximum_executed_nonzero_token_condition"]):
        expected_reasons.append("EXECUTED_TOKEN_CONDITION")
    if expected_reasons != primary["readiness_reasons"]:
        failures.append("PRIMARY_READINESS_REASONS")
    expected_route = config["routes"]["ready"] if not expected_reasons else config["routes"]["not_ready"]
    if primary["route"] != expected_route or bool(primary["passed"]) != (not expected_reasons):
        failures.append("PRIMARY_ROUTE")

    duplicate_signatures: dict[str, list[str]] = {}
    for row in useful_rows:
        signature = json.dumps(
            {
                "horizon_ms": row["horizon_ms"],
                "rz_vector_m": [round(value, 15) for value in row["rz_vector_m"]],
                "terminal_velocity_separation_m_per_s": round(row["terminal_velocity_separation_m_per_s"], 15),
            },
            sort_keys=True,
        )
        duplicate_signatures.setdefault(signature, []).append(row["pair_id"])

    return {
        "schema_version": SCHEMA,
        "stage": "ID-2Z21",
        "primary_source_revision": primary["source_revision"],
        "primary_result_sha256": None,
        "audit_passed": not failures,
        "failures": failures,
        "models_fit_or_updated": 0,
        "tsc_calls_or_plant_advances": 0,
        "calibration_and_blind_holdout_records_read": 0,
        "recomputed": {
            "executed_nonzero_token_rank": rank,
            "executed_nonzero_token_condition": condition,
            "executed_nonzero_token_singular_values": [float(value) for value in singular],
            "unconditional_f_plus_residual_maximum_component_a": additive,
            "held_minus_full_f_distance_m": lineage_distance,
            "held_minus_full_f_speed_m_per_s": lineage_speed,
            "useful_pair_ids": sorted(row["pair_id"] for row in useful_rows),
            "best_two_vector_geometry": best,
            "expected_readiness_reasons": expected_reasons,
            "expected_route": expected_route,
        },
        "exact_duplicate_useful_response_groups": sorted(
            [sorted(values) for values in duplicate_signatures.values() if len(values) > 1]
        ),
        "duplicate_group_interpretation": "pair IDs with identical admitted early response are not independent task-plane segments",
        "claim_boundary": "Independent zero-TSC zero-fit metric/route recomputation; duplicate groups are a conservative reporting diagnostic, not a new scientific gate or changed ID2Z21 verdict.",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--server-run-root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    root = args.repo_root.resolve()
    output = args.output.resolve()
    output.relative_to(root)
    config_path = args.config.resolve()
    primary_path = args.primary.resolve()
    config_path.relative_to(root)
    primary_path.relative_to(root)
    config = read(config_path)
    primary = read(primary_path)
    result = execute(root, args.server_run_root.resolve(), config, primary)
    result["primary_result_sha256"] = digest(primary_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
