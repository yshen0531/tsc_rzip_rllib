#!/usr/bin/env python3
"""Independent raw reparse for the frozen 1 ms ID-1A pilot."""

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
    _sha,
    _state,
)
from scripts.rgeo_zgeo_1ms_id1a_context_anchor_pilot import (  # noqa: E402
    CONFIG_SHA256,
    SCHEMA as PRIMARY_SCHEMA,
    load,
    rollout_specs,
    targets_and_streams,
)
from scripts.rgeo_zgeo_1ms_nr1_qualification import _source  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-id1a-context-anchor-pilot-v1-independent"


def _inside(path: Path, label: str) -> Path:
    result = path.resolve()
    result.relative_to(ROOT.resolve())
    return result


def _maxdiff(left: Sequence[Any], right: Sequence[Any]) -> float:
    if len(left) != len(right):
        return math.inf
    return max((abs(float(a) - float(b)) for a, b in zip(left, right)), default=0.0)


def _compare_compact(raw: dict[str, Any], compact: dict[str, Any], stage: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if raw["actions"] != compact.get("actions"):
        failures.append("COMPACT_ACTIONS")
    if len(raw["states"]) != len(compact.get("states", [])):
        failures.append("COMPACT_STATE_COUNT")
    for index, (a, b) in enumerate(zip(raw["states"], compact.get("states", []))):
        if a["time_ms"] != b.get("time_ms"):
            failures.append(f"COMPACT_TIME:{index}")
        if max(abs(a[key] - b.get(key, math.inf)) for key in ("r_geo_m", "z_geo_m", "r_mid_m")) > 1e-12:
            failures.append(f"COMPACT_GEOMETRY:{index}")
        if abs(a["ip_a"] - b.get("ip_a", math.inf)) > 1e-9:
            failures.append(f"COMPACT_IP:{index}")
        if _maxdiff(a["actual_current_decimal_a_tsc"], b.get("actual_current_decimal_a_tsc", [])) > 1e-9:
            failures.append(f"COMPACT_COIL:{index}")
        if _maxdiff(a["wire_current_a"], b.get("wire_current_a", [])) > 1e-9:
            failures.append(f"COMPACT_WIRE:{index}")
        for name in ("geqdsk", "coil_currents.csv", "wire_currents.csv"):
            if a["artifact_sha256"].get(name) != b.get("artifact_sha256", {}).get(name):
                failures.append(f"COMPACT_SEMANTIC:{index}:{name}")
    return failures


def _mean_baseline(rows: Sequence[dict[str, Any]]) -> np.ndarray:
    if not rows:
        raise ValueError("missing independent matched baseline")
    return np.asarray(
        [
            [
                np.mean([row["states"][index]["r_geo_m"] for row in rows]),
                np.mean([row["states"][index]["z_geo_m"] for row in rows]),
                np.mean([row["states"][index]["ip_a"] for row in rows]),
            ]
            for index in range(len(rows[0]["states"]))
        ],
        dtype=float,
    )


def _metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    q0 = _mean_baseline([row for row in rows if row["context_id"] == "q0_baseline"])
    baselines: dict[str, np.ndarray] = {}
    for context in stage["contexts"]:
        context_id = context["context_id"]
        if context["prefix_id"] == "q0":
            baselines[context_id] = q0
        else:
            baselines[context_id] = _mean_baseline(
                [row for row in rows if row["context_id"] == context_id and row["is_context_baseline"]]
            )
    arms = []
    for row in rows:
        if row["is_context_baseline"]:
            continue
        values = np.asarray(
            [[s["r_geo_m"], s["z_geo_m"], s["ip_a"]] for s in row["states"]], dtype=float
        ) - baselines[row["context_id"]]
        effect = row["pulse_issue_step"] + 1
        mean = np.sum(values[effect : effect + 4], axis=0) / 4.0
        arms.append(
            {
                "rollout_id": row["rollout_id"],
                "context_id": row["context_id"],
                "direction_id": row["direction_id"],
                "sign": row["sign"],
                "repeat_index": row["repeat_index"],
                "effect_state_index": effect,
                "mean_effect_age_1_4": mean.tolist(),
                "peak_rz_norm_m": float(max(math.hypot(v[0], v[1]) for v in values[effect:])),
                "maximum_absolute_ip_response_a": float(max(abs(v[2]) for v in values[effect:])),
            }
        )

    def mean_arm(context: str, direction: str, sign: str) -> np.ndarray:
        selected = [
            row["mean_effect_age_1_4"]
            for row in arms
            if row["context_id"] == context and row["direction_id"] == direction and row["sign"] == sign
        ]
        return np.sum(np.asarray(selected, dtype=float), axis=0) / len(selected)

    geometry = {}
    geometry_passed = True
    for context in stage["contexts"]:
        keys = [f"{direction}:{sign}" for direction in stage["probe_directions"] for sign in stage["probe_signs"]]
        columns = [mean_arm(context["context_id"], *key.split(":"))[:2] for key in keys]
        matrix = np.asarray(columns, dtype=float).T
        rank = int(np.linalg.matrix_rank(matrix))
        pairs = []
        for left in range(4):
            for right in range(left + 1, 4):
                pair = matrix[:, [left, right]]
                condition = float(np.linalg.cond(pair)) if np.linalg.matrix_rank(pair) == 2 else math.inf
                pairs.append({"columns": [keys[left], keys[right]], "condition": condition})
        best = min(pairs, key=lambda item: item["condition"])
        passed = (
            rank >= stage["scientific_gates"]["minimum_rz_response_rank_per_context"]
            and best["condition"] <= stage["scientific_gates"]["maximum_best_pair_condition_per_context"]
        )
        geometry_passed = geometry_passed and passed
        geometry[context["context_id"]] = {
            "keys": keys,
            "mean_rz_response_matrix_m": matrix.tolist(),
            "rank": rank,
            "best_pair": best,
            "passed": passed,
        }

    contrasts = {}
    history_passed = anchor_passed = True
    for context in stage["contexts"]:
        context_id = context["context_id"]
        if context_id in ("early_q0", "late_q0"):
            continue
        delta_state = baselines[context_id][10] - q0[10]
        differences = {}
        for direction in stage["probe_directions"]:
            for sign in stage["probe_signs"]:
                delta = mean_arm(context_id, direction, sign) - mean_arm("late_q0", direction, sign)
                differences[f"{direction}:{sign}"] = {
                    "rz_norm_m": float(math.hypot(delta[0], delta[1])),
                    "ip_a": float(delta[2]),
                }
        maximum = max(item["rz_norm_m"] for item in differences.values())
        rz = float(math.hypot(delta_state[0], delta_state[1]))
        ip = float(abs(delta_state[2]))
        if context_id.startswith("history_"):
            passed = (
                rz <= stage["scientific_gates"]["history_preprobe_maximum_rz_distance_from_late_q0_m"]
                and ip <= stage["scientific_gates"]["history_preprobe_maximum_ip_distance_from_late_q0_a"]
                and maximum >= stage["scientific_gates"]["minimum_history_conditioned_response_difference_m"]
            )
            history_passed = history_passed and passed
        else:
            passed = (
                rz >= stage["scientific_gates"]["minimum_anchor_preprobe_rz_distance_from_late_q0_m"]
                and maximum >= stage["scientific_gates"]["minimum_anchor_conditioned_response_difference_m"]
            )
            anchor_passed = anchor_passed and passed
        contrasts[context_id] = {
            "preprobe_rz_distance_from_late_q0_m": rz,
            "preprobe_ip_distance_from_late_q0_a": ip,
            "response_differences_from_late_q0": differences,
            "maximum_rz_response_difference_m": maximum,
            "passed": passed,
        }
    time = {}
    for direction in stage["probe_directions"]:
        for sign in stage["probe_signs"]:
            delta = mean_arm("late_q0", direction, sign) - mean_arm("early_q0", direction, sign)
            time[f"{direction}:{sign}"] = {
                "rz_norm_m": float(math.hypot(delta[0], delta[1])),
                "ip_a": float(delta[2]),
            }
    gates = stage["scientific_gates"]
    return {
        "arm_metrics": arms,
        "context_vector_geometry": geometry,
        "context_contrasts": contrasts,
        "time_contrasts_reported_only": time,
        "signal_passed": all(row["peak_rz_norm_m"] >= gates["minimum_peak_rz_response_norm_m_per_arm"] for row in arms),
        "ip_passed": all(row["maximum_absolute_ip_response_a"] <= gates["maximum_absolute_ip_response_a"] for row in arms),
        "vector_geometry_passed": geometry_passed,
        "history_contrast_passed": history_passed,
        "anchor_contrast_passed": anchor_passed,
    }


def _route(stage: dict[str, Any], repeatable: bool, metrics: dict[str, Any]) -> str:
    if not repeatable:
        return stage["routes"]["repeatability_fail"]
    if not (metrics["signal_passed"] and metrics["ip_passed"] and metrics["vector_geometry_passed"]):
        return stage["routes"]["signal_or_vector_fail"]
    if not metrics["history_contrast_passed"]:
        return stage["routes"]["history_contrast_fail"]
    if not metrics["anchor_contrast_passed"]:
        return stage["routes"]["anchor_contrast_fail"]
    return stage["routes"]["pass"]


def _numeric_max_difference(left: Any, right: Any) -> float:
    if isinstance(left, dict) and isinstance(right, dict):
        if set(left) != set(right):
            return math.inf
        return max((_numeric_max_difference(left[key], right[key]) for key in left), default=0.0)
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return math.inf
        return max((_numeric_max_difference(a, b) for a, b in zip(left, right)), default=0.0)
    if isinstance(left, (int, float)) and isinstance(right, (int, float)) and not isinstance(left, bool) and not isinstance(right, bool):
        return abs(float(left) - float(right))
    return 0.0 if left == right else math.inf


def audit(stage_path: Path, run_dir: Path, source_revision: str) -> dict[str, Any]:
    stage_path = _inside(stage_path, "stage")
    run_dir = _inside(run_dir, "run")
    failures: list[str] = []
    if _sha(stage_path) != CONFIG_SHA256:
        failures.append("STAGE_SHA")
    stage, cfg, evidence = load(stage_path)
    primary = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    offline = json.loads((run_dir / "offline_preflight.json").read_text(encoding="utf-8"))
    if primary.get("schema_version") != PRIMARY_SCHEMA or primary.get("source_revision") != source_revision:
        failures.append("PRIMARY_IDENTITY")
    if not offline.get("passed") or offline.get("source_revision") != source_revision:
        failures.append("OFFLINE_IDENTITY")
    source = _source(cfg)
    streams = targets_and_streams(stage, cfg, evidence, source)
    raw_rows = []
    inventory = []
    total_bytes = 0
    for spec, stream in zip(rollout_specs(stage), streams):
        folder = run_dir / "rollouts" / spec["rollout_id"]
        state_dirs = sorted(
            [path for path in folder.iterdir() if path.is_dir() and path.name.endswith("ms")],
            key=lambda path: int(path.name[:-2]),
        )
        expected_names = [f"{1100 + index}ms" for index in range(25)]
        if [path.name for path in state_dirs] != expected_names:
            failures.append(f"STATE_DIRECTORIES:{spec['rollout_id']}")
        states = []
        for index, state_dir in enumerate(state_dirs):
            try:
                state = _state(state_dir, cfg)
            except Exception as exc:
                failures.append(f"RAW_STATE:{spec['rollout_id']}:{state_dir.name}:{type(exc).__name__}:{exc}")
                continue
            expected_fields = stream["actions"][min(index, 23)]["expected_card15_fields"]
            if state["active_command_card15_fields"] != expected_fields:
                failures.append(f"RAW_OUTGOING_CARD15:{spec['rollout_id']}:{index}")
            states.append(state)
            for name in ARTIFACTS:
                path = state_dir / name
                if path.is_file():
                    size = path.stat().st_size
                    total_bytes += size
                    inventory.append(f"{path.relative_to(run_dir).as_posix()}\t{size}\t{_sha(path)}")
        row = {**spec, "states": states, "actions": stream["actions"]}
        raw_rows.append(row)
        compact_path = run_dir / f"{spec['rollout_id']}.json"
        if not compact_path.is_file():
            failures.append(f"COMPACT_MISSING:{spec['rollout_id']}")
        else:
            compact = json.loads(compact_path.read_text(encoding="utf-8"))
            failures.extend(f"{spec['rollout_id']}:{item}" for item in _compare_compact(row, compact, stage))
    digest = hashlib.sha256("".join(f"{line}\n" for line in sorted(inventory)).encode()).hexdigest()
    if len(inventory) != stage["completed_required_artifact_files"]:
        failures.append("RAW_FILE_COUNT")
    if primary.get("required_artifact_files") != len(inventory):
        failures.append("PRIMARY_RAW_FILE_COUNT")
    if primary.get("required_artifact_bytes") != total_bytes:
        failures.append("PRIMARY_RAW_BYTES")
    if primary.get("required_artifact_inventory_sha256") != digest:
        failures.append("PRIMARY_RAW_DIGEST")

    comparisons = []
    q0 = [row for row in raw_rows if row["context_id"] == "q0_baseline"]
    comparisons.append({"pair_id": "q0_baseline", **_compare(q0[0], q0[1], stage)})
    for direction, sign in (("p03", "plus"), ("p07", "minus")):
        selected = [
            row for row in raw_rows
            if row["context_id"] == "late_q0" and row["direction_id"] == direction and row["sign"] == sign
        ]
        comparisons.append({"pair_id": f"late_q0_{direction}_{sign}", **_compare(selected[0], selected[1], stage)})
    repeatable = all(row["passed"] for row in comparisons)
    metrics = _metrics(raw_rows, stage)
    route = _route(stage, repeatable, metrics)
    difference = _numeric_max_difference(metrics, primary.get("scientific_metrics"))
    if not math.isfinite(difference) or difference > 1e-12:
        failures.append(f"PRIMARY_METRICS:{difference}")
    if route != primary.get("route"):
        failures.append(f"PRIMARY_ROUTE:{route}:{primary.get('route')}")
    if bool(primary.get("passed")) != (route == stage["routes"]["pass"]):
        failures.append("PRIMARY_VERDICT")
    failures = list(dict.fromkeys(failures))
    return {
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "audit_passed": not failures,
        "failures": failures,
        "recomputed_route": route,
        "recomputed_scientific_metrics": metrics,
        "maximum_primary_metric_difference": difference,
        "repeatability_comparisons": comparisons,
        "raw_states_reparsed": sum(len(row["states"]) for row in raw_rows),
        "required_artifact_files": len(inventory),
        "required_artifact_bytes": total_bytes,
        "required_artifact_inventory_sha256": digest,
        "plant_advances": 0,
        "claim_boundary": "independent_raw_reparse_only_no_tsc_or_model",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-config", type=Path, default=ROOT / "configs/rgeo_zgeo_1ms_id1a_context_anchor_pilot.json")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.stage_config.resolve(), args.run_dir.resolve(), args.source_revision)
    output = _inside(args.output, "output")
    if output.exists():
        raise FileExistsError(output)
    output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
