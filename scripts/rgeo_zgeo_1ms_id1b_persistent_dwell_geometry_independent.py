#!/usr/bin/env python3
"""Independent raw reparse for the frozen 1 ms ID-1B discriminator."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_id0_vector_tail_independent import (  # noqa: E402
    ARTIFACTS,
    _compare,
    _fields,
    _sha,
    _state,
)
from scripts.rgeo_zgeo_1ms_id1a_context_anchor_pilot_independent import (  # noqa: E402
    _compare_compact,
    _numeric_max_difference,
)
from scripts.rgeo_zgeo_1ms_id1b_persistent_dwell_geometry import (  # noqa: E402
    CONFIG_SHA256,
    SCHEMA as PRIMARY_SCHEMA,
    load,
    rollout_specs,
    targets_and_streams,
)
from scripts.rgeo_zgeo_1ms_nr1_qualification import _source  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    assert_exact_slew,
    decimal_single_turn_currents_a,
)


SCHEMA = "rgeo-zgeo-1ms-id1b-persistent-dwell-geometry-v1-independent"


def _inside(path: Path, label: str) -> Path:
    result = path.resolve()
    try:
        result.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} leaves repository root") from exc
    return result


def _baseline(rows: Sequence[dict[str, Any]]) -> np.ndarray:
    selected = [row for row in rows if row["context_id"] == "baseline"]
    if len(selected) != 2:
        raise ValueError("two independent q0 baselines required")
    return np.asarray([
        [
            sum(row["states"][index]["r_geo_m"] for row in selected) / 2.0,
            sum(row["states"][index]["z_geo_m"] for row in selected) / 2.0,
            sum(row["states"][index]["ip_a"] for row in selected) / 2.0,
        ]
        for index in range(len(selected[0]["states"]))
    ], dtype=float)


def _gap(vectors: np.ndarray) -> float:
    angles = sorted(math.degrees(math.atan2(float(row[1]), float(row[0]))) % 360.0 for row in vectors)
    return max(right - left for left, right in zip(angles, angles[1:] + [angles[0] + 360.0]))


def _metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    baseline = _baseline(rows)
    arms = []
    indices = stage["scientific_gates"]["response_state_indices"]
    for row in rows:
        if row["context_id"] == "baseline":
            continue
        values = np.asarray([
            [state["r_geo_m"], state["z_geo_m"], state["ip_a"]]
            for state in row["states"]
        ], dtype=float) - baseline
        mean = np.sum(values[indices], axis=0) / len(indices)
        tail = values[stage["dwell"]["return_effect_state_index"]:]
        arms.append({
            "rollout_id": row["rollout_id"], "direction_id": row["direction_id"],
            "sign": row["sign"], "repeat_index": row["repeat_index"],
            "response_state_indices": indices,
            "mean_persistent_effect_1_4": mean.tolist(),
            "peak_persistent_rz_norm_m": float(max(math.hypot(v[0], v[1]) for v in values[indices])),
            "maximum_absolute_ip_response_a": float(max(abs(v[2]) for v in values[indices])),
            "tail_peak_rz_norm_m_reported_only": float(max(math.hypot(v[0], v[1]) for v in tail)),
            "terminal_rz_norm_m_reported_only": float(math.hypot(values[-1, 0], values[-1, 1])),
            "terminal_absolute_ip_response_a_reported_only": float(abs(values[-1, 2])),
        })
    keys = [f"{direction}:{sign}" for direction in stage["directions"] for sign in stage["signs"]]
    vectors = []
    for key in keys:
        direction, sign = key.split(":")
        selected = [
            row["mean_persistent_effect_1_4"] for row in arms
            if row["direction_id"] == direction and row["sign"] == sign
        ]
        vectors.append(np.sum(np.asarray(selected, dtype=float), axis=0)[:2] / len(selected))
    matrix = np.asarray(vectors, dtype=float).T
    rank = int(np.linalg.matrix_rank(matrix))
    pairs = []
    for left in range(len(keys)):
        for right in range(left + 1, len(keys)):
            pair = matrix[:, [left, right]]
            pairs.append({
                "columns": [keys[left], keys[right]],
                "condition": float(np.linalg.cond(pair)) if np.linalg.matrix_rank(pair) == 2 else math.inf,
            })
    best = min(pairs, key=lambda row: row["condition"])
    vector_array = np.asarray(vectors, dtype=float)
    gap = _gap(vector_array)
    samples = stage["scientific_gates"]["directional_support_angle_samples"]
    supports = []
    for index in range(samples):
        angle = 2.0 * math.pi * index / samples
        direction = np.asarray([math.cos(angle), math.sin(angle)])
        supports.append(max(float(np.dot(direction, vector)) for vector in vector_array))
    support = min(supports)
    gates = stage["scientific_gates"]
    signal = all(
        row["peak_persistent_rz_norm_m"] >= gates["minimum_peak_rz_response_norm_m_per_signed_arm"]
        for row in arms
    )
    ip_ok = all(row["maximum_absolute_ip_response_a"] <= gates["maximum_absolute_ip_response_a"] for row in arms)
    positive = (
        rank >= gates["minimum_rz_response_rank"]
        and best["condition"] <= gates["maximum_best_pair_condition"]
        and gap <= gates["maximum_angular_gap_deg"]
        and support >= gates["minimum_directional_support_m"]
    )
    return {
        "arm_metrics": arms, "vector_keys": keys,
        "mean_persistent_rz_response_matrix_m": matrix.tolist(),
        "rz_response_rank": rank, "pair_conditions": pairs,
        "best_pair": best, "maximum_angular_gap_deg": gap,
        "minimum_directional_support_m": support,
        "directional_support_samples": samples,
        "signal_passed": signal, "ip_passed": ip_ok,
        "positive_span_passed": positive,
    }


def _route(stage: dict[str, Any], repeatable: bool, metrics: dict[str, Any]) -> str:
    if not repeatable:
        return stage["routes"]["repeatability_fail"]
    if not (metrics["signal_passed"] and metrics["ip_passed"]):
        return stage["routes"]["signal_or_ip_fail"]
    if not metrics["positive_span_passed"]:
        return stage["routes"]["positive_span_fail"]
    return stage["routes"]["pass"]


def audit(stage_path: Path, run_dir: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    stage_path = _inside(stage_path, "stage config")
    run_dir = _inside(run_dir, "run directory")
    if _sha(stage_path) != CONFIG_SHA256:
        failures.append("STAGE_SHA256")
    try:
        stage, cfg, evidence = load(stage_path)
    except Exception as exc:
        failures.append(f"STAGE_LOAD:{type(exc).__name__}:{exc}")
        stage = json.loads(stage_path.read_text(encoding="utf-8"))
        cfg = None
        evidence = None
    primary_path = run_dir / "result.json"
    primary = json.loads(primary_path.read_text(encoding="utf-8")) if primary_path.is_file() else {}
    if not primary:
        failures.append("PRIMARY_RESULT_MISSING")
    specs = rollout_specs(stage)
    expected_ids = [row["rollout_id"] for row in specs]
    rollout_root = run_dir / "rollouts"
    actual_ids = sorted(path.name for path in rollout_root.iterdir() if path.is_dir()) if rollout_root.is_dir() else []
    if actual_ids != sorted(expected_ids):
        failures.append("ROLLOUT_DIRECTORY_SET")
    rows: list[dict[str, Any]] = []
    lines: list[str] = []
    total_bytes = 0
    try:
        if cfg is None or evidence is None:
            raise ValueError("stage dependencies unavailable")
        source = _source(cfg)
        streams = targets_and_streams(stage, cfg, evidence, source)
        stream_by_id = {row["rollout_id"]: row for row in streams}
        source_signal = None
        for spec in specs:
            folder = rollout_root / spec["rollout_id"]
            state_dirs = sorted(path.name for path in folder.iterdir() if path.is_dir() and path.name.endswith("ms"))
            expected_dirs = [f"{time}ms" for time in range(1100, 1125)]
            if state_dirs != expected_dirs:
                raise ValueError(f"state directory set:{spec['rollout_id']}")
            states = [_state(folder / f"{time}ms", cfg) for time in range(1100, 1125)]
            if source_signal is None:
                source_signal = states[0]
            stream = stream_by_id[spec["rollout_id"]]
            actions = []
            previous_command = states[0]["active_command_decimal_a_tsc"]
            outer = stage["empirical_exploration"]["outer_hard_envelope"]
            inner = stage["empirical_exploration"]["inner_probe_issue_clearance"]
            caps = stage["empirical_exploration"]["post_successor_step_caps"]
            for state_index, state in enumerate(states):
                if not state["r_inner_m"] <= state["r_geo_m"] <= state["r_outer_m"]:
                    failures.append(f"LIMITER:{spec['rollout_id']}:{state_index}")
                if abs(state["r_geo_m"] - states[0]["r_geo_m"]) > outer["r_geo_m"]:
                    failures.append(f"OUTER_R:{spec['rollout_id']}:{state_index}")
                if abs(state["z_geo_m"] - states[0]["z_geo_m"]) > outer["z_geo_m"]:
                    failures.append(f"OUTER_Z:{spec['rollout_id']}:{state_index}")
                if states[0]["ip_a"] * state["ip_a"] <= 0 or abs(state["ip_a"] - states[0]["ip_a"]) > outer["ip_fraction"] * abs(states[0]["ip_a"]):
                    failures.append(f"OUTER_IP:{spec['rollout_id']}:{state_index}")
                if len(state["actual_current_decimal_a_tsc"]) != 14 or len(state["wire_current_a"]) != 48:
                    failures.append(f"STATE_VECTOR_LENGTH:{spec['rollout_id']}:{state_index}")
            if spec["pulse_issue_step"] is not None:
                state = states[spec["pulse_issue_step"]]
                if abs(state["r_geo_m"] - states[0]["r_geo_m"]) > inner["r_geo_m"]:
                    failures.append(f"PULSE_CLEARANCE_R:{spec['rollout_id']}")
                if abs(state["z_geo_m"] - states[0]["z_geo_m"]) > inner["z_geo_m"]:
                    failures.append(f"PULSE_CLEARANCE_Z:{spec['rollout_id']}")
                if abs(state["ip_a"] - states[0]["ip_a"]) > inner["ip_fraction"] * abs(states[0]["ip_a"]):
                    failures.append(f"PULSE_CLEARANCE_IP:{spec['rollout_id']}")
            for issue, target in enumerate(stream["targets"]):
                fields = _fields(folder / f"{1100 + issue}ms" / "inputa")
                if fields != target.card15_fields:
                    failures.append(f"CARD15:{spec['rollout_id']}:{issue}")
                exact = decimal_single_turn_currents_a(
                    tuple(value.strip() for value in target.card15_fields), cfg.turns_tsc,
                    name=f"id1b.audit.{spec['rollout_id']}.{issue}",
                )
                maximum = assert_exact_slew(previous_command, exact, name=f"id1b.audit.issue.{issue}")
                observed = assert_exact_slew(
                    states[issue]["actual_current_decimal_a_tsc"],
                    states[issue + 1]["actual_current_decimal_a_tsc"],
                    name=f"id1b.audit.observed.{issue}",
                )
                if abs(states[issue + 1]["r_geo_m"] - states[issue]["r_geo_m"]) > caps["r_geo_m"]:
                    failures.append(f"EMPIRICAL_STEP_R:{spec['rollout_id']}:{issue}")
                if abs(states[issue + 1]["z_geo_m"] - states[issue]["z_geo_m"]) > caps["z_geo_m"]:
                    failures.append(f"EMPIRICAL_STEP_Z:{spec['rollout_id']}:{issue}")
                if abs(states[issue + 1]["ip_a"] - states[issue]["ip_a"]) > caps["ip_a"]:
                    failures.append(f"EMPIRICAL_STEP_IP:{spec['rollout_id']}:{issue}")
                action = dict(stream["actions"][issue])
                action["maximum_issued_delta_a"] = maximum
                actions.append(action)
                states[issue + 1]["maximum_observed_delta_a"] = observed
                previous_command = exact
            compact_path = run_dir / f"{spec['rollout_id']}.json"
            compact = json.loads(compact_path.read_text(encoding="utf-8"))
            raw = {**spec, "states": states, "actions": actions}
            failures.extend(f"{spec['rollout_id']}:{value}" for value in _compare_compact(raw, compact, stage))
            rows.append(raw)
            for state in states:
                for name in ARTIFACTS:
                    path = folder / f"{state['time_ms']}ms" / name
                    if not path.is_file():
                        failures.append(f"MISSING:{path.relative_to(run_dir).as_posix()}")
                        continue
                    size = path.stat().st_size
                    total_bytes += size
                    lines.append(f"{path.relative_to(run_dir).as_posix()}\t{size}\t{_sha(path)}")
    except Exception as exc:
        failures.append(f"RAW:{type(exc).__name__}:{exc}")

    metrics = comparisons = expected_route = None
    if len(rows) == stage["rollouts"] and not any(item.startswith("RAW:") for item in failures):
        comparisons = []
        baseline = [row for row in rows if row["context_id"] == "baseline"]
        comparisons.append({"pair_id": "q0_baseline", **_compare(baseline[0], baseline[1], stage)})
        for direction in stage["directions"]:
            for sign in stage["signs"]:
                selected = [row for row in rows if row["direction_id"] == direction and row["sign"] == sign]
                comparisons.append({"pair_id": f"late_{direction}_{sign}", **_compare(selected[0], selected[1], stage)})
        repeatable = all(row["passed"] for row in comparisons)
        metrics = _metrics(rows, stage)
        expected_route = _route(stage, repeatable, metrics)
        inventory = hashlib.sha256("".join(f"{line}\n" for line in sorted(lines)).encode()).hexdigest()
        if len(lines) != stage["completed_required_artifact_files"]:
            failures.append("INVENTORY_COUNT")
        if primary.get("required_artifact_files") != len(lines) or primary.get("required_artifact_bytes") != total_bytes or primary.get("required_artifact_inventory_sha256") != inventory:
            failures.append("INVENTORY_IDENTITY")
        if primary.get("route") != expected_route:
            failures.append("PRIMARY_ROUTE")
        if primary.get("schema_version") != PRIMARY_SCHEMA or primary.get("source_revision") != source_revision:
            failures.append("PRIMARY_IDENTITY")
        if primary.get("reset_calls") != 14 or primary.get("advance_attempts") != 336 or primary.get("plant_advance_gotsc_calls") != 336 or primary.get("verified_plant_advances") != 336:
            failures.append("PRIMARY_COUNTERS")
        difference = _numeric_max_difference(metrics, primary.get("scientific_metrics"))
        if difference > 1e-12:
            failures.append(f"PRIMARY_METRICS:{difference}")
        if primary.get("repeatability_comparisons") != comparisons:
            failures.append("PRIMARY_REPEATABILITY")
    failures = list(dict.fromkeys(failures))
    result = {
        "schema_version": SCHEMA, "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "audit_passed": not failures,
        "route": "ONE_MS_ID1B_INDEPENDENT_AUDIT_PASS" if not failures else "ONE_MS_ID1B_INDEPENDENT_AUDIT_FAIL",
        "failures": failures, "raw_rollouts": len(rows),
        "raw_states": sum(len(row["states"]) for row in rows),
        "required_artifact_files": len(lines),
        "required_artifact_bytes": total_bytes,
        "required_artifact_inventory_sha256": hashlib.sha256(
            "".join(f"{line}\n" for line in sorted(lines)).encode()
        ).hexdigest(),
        "recomputed_scientific_route": expected_route,
        "recomputed_scientific_metrics": metrics,
        "repeatability_comparisons": comparisons,
        "primary_scientific_passed": primary.get("passed"),
        "maximum_primary_metric_difference": (
            None if metrics is None else _numeric_max_difference(metrics, primary.get("scientific_metrics"))
        ),
        "claim_boundary": "independent_raw_recomputation_not_model_controller_or_safety_qualification",
    }
    destination = run_dir / "independent_audit.json"
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite {destination}")
    destination.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-config", type=Path, default=ROOT / "configs/rgeo_zgeo_1ms_id1b_persistent_dwell_geometry.json")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    result = audit(args.stage_config, args.run_dir, args.source_revision)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
