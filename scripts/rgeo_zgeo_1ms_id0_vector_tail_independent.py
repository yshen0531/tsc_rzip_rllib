#!/usr/bin/env python3
"""Independent raw-directory audit for the frozen 1 ms ID-0 campaign."""

from __future__ import annotations

import argparse
import csv
from decimal import Decimal
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

from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    Card15Target, assert_exact_slew, decimal_single_turn_currents_a, quantize_target,
)
from tsc_rzip_rllib.control.rgeo_zgeo_contract import RGeoZGeoSignal  # noqa: E402
from tsc_rzip_rllib.core.gfile import parse_gfile  # noqa: E402
from tsc_rzip_rllib.core.runner import TSCConfig  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-id0-vector-tail-v1-independent"
PRIMARY_SCHEMA = "rgeo-zgeo-1ms-id0-vector-tail-v1"
CONFIG_SHA256 = "668b0e4bb21166dc4d92fe4381c4177b4789b5a3139a176f7ab1b109393c31eb"
ARTIFACTS = ("inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv", "sprsina")


def _inside_root(path: Path, label: str) -> Path:
    result = path.resolve()
    if not result.is_relative_to(ROOT.resolve()):
        raise ValueError(f"{label} leaves repository: {path}")
    return result


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fields(path: Path) -> tuple[str, ...]:
    values = tuple(
        line[30:40] for line in path.read_text(encoding="utf-8").splitlines()
        if line[:10].strip() == "15"
    )
    if len(values) != 14 or any(len(value) != 10 for value in values):
        raise ValueError(f"expected fourteen exact Card15 fields: {path}")
    return values


def _coil(path: Path, cfg: TSCConfig) -> tuple[Decimal, ...]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, skipinitialspace=True)
        key = next((name for name in (reader.fieldnames or []) if "ccoil" in name.lower()), None)
        if key is None:
            raise ValueError("ccoil column missing")
        values = tuple(row[key].strip() for row in reader)
    result = decimal_single_turn_currents_a(values, cfg.turns_tsc, name=str(path))
    if len(result) != 14:
        raise ValueError("coil vector is not length 14")
    return result


def _wire(path: Path, cfg: TSCConfig) -> tuple[float, ...]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, skipinitialspace=True)
        names = {str(name).strip(): name for name in (reader.fieldnames or [])}
        key = names.get(cfg.vessel_current_column)
        if key is None:
            raise ValueError("wire current column missing")
        values = tuple(float(row[key]) * cfg.vessel_current_raw_to_a for row in reader if str(row[key]).strip())
    if len(values) != 48 or not all(math.isfinite(value) for value in values):
        raise ValueError("wire current vector is not a finite length-48 vector")
    return values


def _state(folder: Path, cfg: TSCConfig) -> dict[str, Any]:
    for name in ARTIFACTS:
        if not (folder / name).is_file():
            raise FileNotFoundError(str(folder / name))
    time_ms = int(folder.name.removesuffix("ms"))
    gfile = parse_gfile(folder / "geqdsk")
    signal = RGeoZGeoSignal.from_tsc_state(
        {"time_ms": time_ms, "Ip": float(gfile["ip"]), "gfile": gfile, "abnormal": False}
    )
    current = _coil(folder / "coil_currents.csv", cfg)
    fields = _fields(folder / "inputa")
    command = decimal_single_turn_currents_a(
        tuple(value.strip() for value in fields), cfg.turns_tsc, name=str(folder / "inputa")
    )
    return {
        "time_ms": time_ms, "r_geo_m": signal.boundary.r_geo_m,
        "z_geo_m": signal.boundary.z_geo_m, "r_mid_m": signal.limiter.r_mid_m,
        "r_inner_m": signal.limiter.r_inner_m, "r_outer_m": signal.limiter.r_outer_m,
        "ip_a": signal.ip_a, "actual_current_decimal_a_tsc": [str(value) for value in current],
        "active_command_card15_fields": list(fields),
        "active_command_decimal_a_tsc": [str(value) for value in command],
        "wire_current_a": list(_wire(folder / "wire_currents.csv", cfg)),
        "artifact_sha256": {name: _sha(folder / name) for name in ARTIFACTS},
    }


def _specs(stage: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        {"rollout_id": f"baseline_q0_r{repeat}", "context_id": "baseline",
         "direction_id": None, "sign": None, "repeat_index": repeat,
         "pulse_issue_step": None, "return_issue_step": None}
        for repeat in range(2)
    ]
    for context in stage["contexts"]:
        for direction in stage["directions"]:
            for sign in ("plus", "minus"):
                for repeat in range(context["repetitions_per_signed_direction"]):
                    rows.append({
                        "rollout_id": f"{context['context_id']}_{direction['direction_id']}_{sign}_r{repeat}",
                        "context_id": context["context_id"], "direction_id": direction["direction_id"],
                        "sign": sign, "repeat_index": repeat,
                        "pulse_issue_step": context["pulse_issue_step"],
                        "return_issue_step": context["return_issue_step"],
                    })
    return rows


def _target(fields: Sequence[str], cfg: TSCConfig) -> Card15Target:
    exact = decimal_single_turn_currents_a(
        tuple(value.strip() for value in fields), cfg.turns_tsc, name="id0.independent.target"
    )
    return Card15Target(tuple(fields), tuple(float(value) for value in exact))


def _stream(stage: dict[str, Any], cfg: TSCConfig, spec: dict[str, Any], q0: Card15Target) -> list[Card15Target]:
    output = [q0] * stage["horizon_steps"]
    if spec["pulse_issue_step"] is not None:
        direction = next(row for row in stage["directions"] if row["direction_id"] == spec["direction_id"])
        output[spec["pulse_issue_step"]] = _target(direction[f"{spec['sign']}_card15_fields"], cfg)
    return output


def _maxdiff(left: Sequence[Any], right: Sequence[Any]) -> float:
    if len(left) != len(right):
        return math.inf
    return max((abs(float(a) - float(b)) for a, b in zip(left, right)), default=0.0)


def _compare(left: dict[str, Any], right: dict[str, Any], stage: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    maxima = {"geometry_m": 0.0, "ip_a": 0.0, "coil_a": 0.0, "wire_a": 0.0}
    if left["actions"] != right["actions"]:
        failures.append("ACTION_STREAM")
    for index, (a, b) in enumerate(zip(left["states"], right["states"])):
        maxima["geometry_m"] = max(maxima["geometry_m"], *(abs(a[key] - b[key]) for key in ("r_geo_m", "z_geo_m", "r_mid_m")))
        maxima["ip_a"] = max(maxima["ip_a"], abs(a["ip_a"] - b["ip_a"]))
        maxima["coil_a"] = max(maxima["coil_a"], _maxdiff(a["actual_current_decimal_a_tsc"], b["actual_current_decimal_a_tsc"]))
        maxima["wire_a"] = max(maxima["wire_a"], _maxdiff(a["wire_current_a"], b["wire_current_a"]))
        for name in stage["semantic_artifacts"]:
            if a["artifact_sha256"][name] != b["artifact_sha256"][name]:
                failures.append(f"SEMANTIC_ARTIFACT:{index}:{name}")
    for key, value in maxima.items():
        if value > stage["repeatability"][key]:
            failures.append(key.upper())
    return {"passed": not failures, "failures": list(dict.fromkeys(failures)), "maximum_absolute_difference": maxima}


def _baseline(rows: Sequence[dict[str, Any]]) -> list[dict[str, float]]:
    selected = [row for row in rows if row["context_id"] == "baseline"]
    return [{key: float(np.mean([row["states"][index][key] for row in selected]))
             for key in ("r_geo_m", "z_geo_m", "ip_a")} for index in range(21)]


def _gap(vectors: np.ndarray) -> float:
    angles = sorted(math.degrees(math.atan2(float(row[1]), float(row[0]))) % 360 for row in vectors)
    return max(right - left for left, right in zip(angles, angles[1:] + [angles[0] + 360]))


def _metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    baseline = _baseline(rows)
    arm_metrics = []
    for row in rows:
        if row["context_id"] == "baseline":
            continue
        response = np.asarray([[state["r_geo_m"] - base["r_geo_m"], state["z_geo_m"] - base["z_geo_m"], state["ip_a"] - base["ip_a"]] for state, base in zip(row["states"], baseline)])
        effect = row["pulse_issue_step"] + 1
        window = response[effect:]
        norms = np.linalg.norm(window[:, :2], axis=1)
        mean = np.mean(response[effect:effect + 4], axis=0)
        peak = float(np.max(norms))
        arm_metrics.append({
            "rollout_id": row["rollout_id"], "context_id": row["context_id"],
            "direction_id": row["direction_id"], "sign": row["sign"],
            "repeat_index": row["repeat_index"], "effect_state_index": effect,
            "mean_effect_age_1_4": mean.tolist(), "peak_rz_norm_m": peak,
            "maximum_absolute_ip_response_a": float(np.max(np.abs(window[:, 2]))),
            "terminal_rz_norm_m": float(norms[-1]),
            "terminal_absolute_ip_response_a": float(abs(window[-1, 2])),
            "terminal_peak_fraction": float(norms[-1] / peak) if peak else math.inf,
        })
    keys, vectors = [], []
    for direction in ("p03", "p04", "p07"):
        for sign in ("plus", "minus"):
            subset = [row for row in arm_metrics if row["context_id"] == "early" and row["direction_id"] == direction and row["sign"] == sign]
            keys.append(f"{direction}:{sign}")
            vectors.append(np.mean([row["mean_effect_age_1_4"][:2] for row in subset], axis=0))
    matrix = np.asarray(vectors).T
    conditions = []
    for i in range(6):
        for j in range(i + 1, 6):
            pair = matrix[:, [i, j]]
            conditions.append({"columns": [keys[i], keys[j]], "condition": float(np.linalg.cond(pair)) if np.linalg.matrix_rank(pair) == 2 else math.inf})
    best = min(conditions, key=lambda row: row["condition"])
    context = []
    for direction in ("p03", "p04", "p07"):
        for sign in ("plus", "minus"):
            early = np.mean([row["mean_effect_age_1_4"] for row in arm_metrics if row["context_id"] == "early" and row["direction_id"] == direction and row["sign"] == sign], axis=0)
            late = np.mean([row["mean_effect_age_1_4"] for row in arm_metrics if row["context_id"] == "late" and row["direction_id"] == direction and row["sign"] == sign], axis=0)
            context.append({"arm": f"{direction}:{sign}", "early": early.tolist(), "late": late.tolist(), "late_minus_early": (late - early).tolist()})
    gate = stage["scientific_gates"]
    early_rows = [row for row in arm_metrics if row["context_id"] == "early"]
    return {
        "arm_metrics": arm_metrics, "early_vector_keys": keys,
        "early_mean_rz_response_matrix_m": matrix.tolist(),
        "rz_response_rank": int(np.linalg.matrix_rank(matrix)), "pair_conditions": conditions,
        "best_pair": best, "maximum_normalized_angular_gap_deg": _gap(np.asarray(vectors)),
        "context_differences": context,
        "signal_passed": all(row["peak_rz_norm_m"] >= gate["minimum_peak_rz_response_norm_m_per_signed_arm"] for row in arm_metrics),
        "ip_passed": all(row["maximum_absolute_ip_response_a"] <= gate["maximum_absolute_ip_response_a"] for row in arm_metrics),
        "vector_geometry_passed": int(np.linalg.matrix_rank(matrix)) >= gate["minimum_rz_response_rank"] and best["condition"] <= gate["maximum_best_pair_condition"] and _gap(np.asarray(vectors)) <= gate["maximum_normalized_angular_gap_deg"],
        "tail_passed": all(row["terminal_rz_norm_m"] <= gate["tail_terminal_maximum_rz_norm_m"] and row["terminal_peak_fraction"] <= gate["tail_terminal_maximum_peak_fraction"] and row["terminal_absolute_ip_response_a"] <= gate["tail_terminal_maximum_abs_ip_a"] for row in early_rows),
    }


def _expected_route(stage: dict[str, Any], repeatable: bool, metrics: dict[str, Any]) -> str:
    if not repeatable:
        return stage["routes"]["repeatability_fail"]
    if not (metrics["signal_passed"] and metrics["ip_passed"] and metrics["vector_geometry_passed"]):
        return stage["routes"]["signal_or_vector_fail"]
    if not metrics["tail_passed"]:
        return stage["routes"]["tail_horizon_fail"]
    return stage["routes"]["pass"]


def audit(stage_path: Path, run_dir: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    stage_path = _inside_root(stage_path, "stage config")
    run_dir = _inside_root(run_dir, "run dir")
    stage = json.loads(stage_path.read_text(encoding="utf-8"))
    if _sha(stage_path) != CONFIG_SHA256 or stage.get("schema_version") != PRIMARY_SCHEMA:
        failures.append("STAGE_IDENTITY")
    cfg = TSCConfig.from_json(_inside_root(ROOT / stage["base_tsc_config"], "base config"))
    primary_path = run_dir / "result.json"
    if not primary_path.is_file():
        failures.append("PRIMARY_RESULT_MISSING")
        primary = {}
    else:
        primary = json.loads(primary_path.read_text(encoding="utf-8"))
    specs = _specs(stage)
    actual_rollout_dirs = sorted(path.name for path in (run_dir / "rollouts").iterdir() if path.is_dir()) if (run_dir / "rollouts").is_dir() else []
    expected_ids = [row["rollout_id"] for row in specs]
    if actual_rollout_dirs != sorted(expected_ids):
        failures.append("ROLLOUT_DIRECTORY_SET")
    rows = []
    inventory_lines = []
    try:
        for spec in specs:
            folder = run_dir / "rollouts" / spec["rollout_id"]
            state_dirs = sorted(path.name for path in folder.iterdir() if path.is_dir() and path.name.endswith("ms"))
            if state_dirs != [f"{time}ms" for time in range(1100, 1121)]:
                raise ValueError(f"state directory set:{spec['rollout_id']}")
            states = [_state(folder / f"{time}ms", cfg) for time in range(1100, 1121)]
            q0 = quantize_target(tuple(float(x) for x in states[0]["actual_current_decimal_a_tsc"]), cfg.turns_tsc)
            targets = _stream(stage, cfg, spec, q0)
            actions = []
            previous_command = states[0]["active_command_decimal_a_tsc"]
            source = states[0]
            outer = stage["empirical_exploration"]["outer_hard_envelope"]
            inner = stage["empirical_exploration"]["inner_pulse_issue_clearance"]
            caps = stage["empirical_exploration"]["post_successor_step_caps"]
            for state_index, state in enumerate(states):
                if not state["r_inner_m"] <= state["r_geo_m"] <= state["r_outer_m"]:
                    failures.append(f"LIMITER:{spec['rollout_id']}:{state_index}")
                if abs(state["r_geo_m"] - source["r_geo_m"]) > outer["r_geo_m"]:
                    failures.append(f"OUTER_R:{spec['rollout_id']}:{state_index}")
                if abs(state["z_geo_m"] - source["z_geo_m"]) > outer["z_geo_m"]:
                    failures.append(f"OUTER_Z:{spec['rollout_id']}:{state_index}")
                if source["ip_a"] * state["ip_a"] <= 0 or abs(state["ip_a"] - source["ip_a"]) > outer["ip_fraction"] * abs(source["ip_a"]):
                    failures.append(f"OUTER_IP:{spec['rollout_id']}:{state_index}")
                if any(float(value) < low or float(value) > high for value, low, high in zip(
                    state["actual_current_decimal_a_tsc"], cfg.min_current_a_tsc, cfg.max_current_a_tsc
                )):
                    failures.append(f"ACTUAL_CURRENT_LIMIT:{spec['rollout_id']}:{state_index}")
            if spec["pulse_issue_step"] is not None:
                pulse_state = states[spec["pulse_issue_step"]]
                if abs(pulse_state["r_geo_m"] - source["r_geo_m"]) > inner["r_geo_m"]:
                    failures.append(f"PULSE_CLEARANCE_R:{spec['rollout_id']}")
                if abs(pulse_state["z_geo_m"] - source["z_geo_m"]) > inner["z_geo_m"]:
                    failures.append(f"PULSE_CLEARANCE_Z:{spec['rollout_id']}")
                if abs(pulse_state["ip_a"] - source["ip_a"]) > inner["ip_fraction"] * abs(source["ip_a"]):
                    failures.append(f"PULSE_CLEARANCE_IP:{spec['rollout_id']}")
            for issue, target in enumerate(targets):
                observed_fields = _fields(folder / f"{1100 + issue}ms" / "inputa")
                if observed_fields != target.card15_fields:
                    failures.append(f"CARD15:{spec['rollout_id']}:{issue}")
                exact = decimal_single_turn_currents_a(tuple(value.strip() for value in target.card15_fields), cfg.turns_tsc, name="audit.target")
                maximum = assert_exact_slew(previous_command, exact, name=f"audit.issue.{spec['rollout_id']}.{issue}")
                observed = assert_exact_slew(states[issue]["actual_current_decimal_a_tsc"], states[issue + 1]["actual_current_decimal_a_tsc"], name=f"audit.observed.{spec['rollout_id']}.{issue}")
                if abs(states[issue + 1]["r_geo_m"] - states[issue]["r_geo_m"]) > caps["r_geo_m"]:
                    failures.append(f"EMPIRICAL_STEP_R:{spec['rollout_id']}:{issue}")
                if abs(states[issue + 1]["z_geo_m"] - states[issue]["z_geo_m"]) > caps["z_geo_m"]:
                    failures.append(f"EMPIRICAL_STEP_Z:{spec['rollout_id']}:{issue}")
                if abs(states[issue + 1]["ip_a"] - states[issue]["ip_a"]) > caps["ip_a"]:
                    failures.append(f"EMPIRICAL_STEP_IP:{spec['rollout_id']}:{issue}")
                actions.append({"issue_step": issue, "issue_time_ms": 1100 + issue, "effect_state_index": issue + 1, "effect_time_ms": 1101 + issue, "expected_card15_fields": list(target.card15_fields), "target_current_a_tsc": list(target.current_a_tsc), "maximum_issued_delta_a": maximum})
                states[issue + 1]["maximum_observed_delta_a"] = observed
                previous_command = exact
            if tuple(states[-1]["active_command_card15_fields"]) != q0.card15_fields:
                failures.append(f"FINAL_ACTIVE_CARD15:{spec['rollout_id']}")
            rows.append({**spec, "states": states, "actions": actions})
            for state in states:
                for name in ARTIFACTS:
                    path = folder / f"{state['time_ms']}ms" / name
                    label = path.relative_to(run_dir).as_posix()
                    inventory_lines.append(f"{label}\t{path.stat().st_size}\t{_sha(path)}")
    except Exception as exc:
        failures.append(f"RAW:{type(exc).__name__}:{exc}")
    metrics = comparisons = None
    expected_route = None
    if len(rows) == 20 and not any(item.startswith("RAW:") for item in failures):
        comparisons = [{"pair_id": "baseline_q0", **_compare(rows[0], rows[1], stage)}]
        for direction in ("p03", "p04", "p07"):
            for sign in ("plus", "minus"):
                selected = [row for row in rows if row["context_id"] == "early" and row["direction_id"] == direction and row["sign"] == sign]
                comparisons.append({"pair_id": f"early_{direction}_{sign}", **_compare(selected[0], selected[1], stage)})
        repeatable = all(row["passed"] for row in comparisons)
        metrics = _metrics(rows, stage)
        expected_route = _expected_route(stage, repeatable, metrics)
        payload = "".join(f"{line}\n" for line in sorted(inventory_lines)).encode()
        inventory_sha = hashlib.sha256(payload).hexdigest()
        total_bytes = sum(int(line.split("\t")[1]) for line in inventory_lines)
        if len(inventory_lines) != 2100 or primary.get("required_artifact_files") != 2100:
            failures.append("INVENTORY_COUNT")
        if primary.get("required_artifact_inventory_sha256") != inventory_sha or primary.get("required_artifact_bytes") != total_bytes:
            failures.append("INVENTORY_IDENTITY")
        if primary.get("route") != expected_route:
            failures.append("PRIMARY_ROUTE")
        if primary.get("source_revision") != source_revision or primary.get("schema_version") != PRIMARY_SCHEMA:
            failures.append("PRIMARY_IDENTITY")
        if primary.get("reset_calls") != 20 or primary.get("advance_attempts") != 400 or primary.get("verified_plant_advances") != 400:
            failures.append("PRIMARY_COUNTERS")
        primary_metrics = primary.get("scientific_metrics")
        if json.dumps(primary_metrics, sort_keys=True, allow_nan=False) != json.dumps(metrics, sort_keys=True, allow_nan=False):
            failures.append("PRIMARY_METRICS")
    failures = list(dict.fromkeys(failures))
    result = {
        "schema_version": SCHEMA, "source_revision": source_revision,
        "audit_passed": not failures, "passed": not failures,
        "route": "ONE_MS_ID0_INDEPENDENT_AUDIT_PASS" if not failures else "ONE_MS_ID0_INDEPENDENT_AUDIT_FAIL",
        "failures": failures, "raw_rollouts": len(rows), "raw_states": sum(len(row["states"]) for row in rows),
        "recomputed_scientific_route": expected_route, "repeatability_comparisons": comparisons,
        "scientific_metrics": metrics,
        "primary_scientific_passed": primary.get("passed"),
        "claim_boundary": "independent_raw_recomputation_not_controller_or_safety_qualification",
    }
    destination = run_dir / "independent_audit.json"
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite {destination}")
    destination.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    result = audit(args.stage_config.resolve(), args.run_dir.resolve(), args.source_revision)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
