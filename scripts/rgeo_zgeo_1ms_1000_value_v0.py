#!/usr/bin/env python3
"""Conservative direct candidate-response set and ranking model."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_1000_baseline_b0 as b0  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-1000-value-v0-v1"
CONFIG_SHA256 = "137a39fc6d94a46539191433ea193f551597e44040e01455430b1e77f485cd8e"
DEFAULT_CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_value_v0.json"


class InputIntegrityError(ValueError):
    """Frozen V0 dataset, role or evaluation contract changed."""


def _exact_stage(stage: dict[str, Any]) -> None:
    exact = {
        "schema_version": SCHEMA,
        "model_id": "rgeo_zgeo_1ms_1000_value_v0_v1",
        "takeover_time_ms": 1000,
        "candidate_issue_phase": 24,
        "horizons": [4, 8],
        "contexts": ["q0", "even_plus", "odd_plus"],
        "candidates": ["even_plus", "even_minus", "odd_plus", "odd_minus"],
        "direction_grid_count": 64,
        "component_floor_rz_ip": [0.03, 0.03, 10.0],
        "model_form": "componentwise_median_plus_max_deviation_and_fixed_floor",
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise InputIntegrityError(f"frozen V0 field mismatch: {key}")
    roles = {
        "listed_rows": "development_fit_eligible_weight_1",
        "d1_and_d2_replays": "excluded_zero_fit_weight",
        "calibration_histories": "unopened",
        "blind_histories": "unopened",
        "controller_or_recourse": "forbidden",
        "fixed_1100_data": "forbidden",
    }
    if stage.get("data_roles") != roles:
        raise InputIntegrityError("V0 data roles changed")


def _load_files(stage: dict[str, Any]) -> dict[str, dict[str, Any]]:
    payloads: dict[str, dict[str, Any]] = {}
    if len(stage.get("dataset_files", ())) != 15:
        raise InputIntegrityError("V0 dataset file count changed")
    for row in stage["dataset_files"]:
        path = b0.inside_root(ROOT / row["path"], "V0 dataset file")
        if b0.sha256(path) != row["sha256"]:
            raise InputIntegrityError(f"V0 dataset hash mismatch: {row['path']}")
        if "1100" in path.as_posix() or "replay" in path.name:
            raise InputIntegrityError(f"forbidden V0 dataset row: {row['path']}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("passed") is not True:
            raise InputIntegrityError(f"failed V0 dataset row: {row['path']}")
        payloads[path.name] = payload
    return payloads


def _response(candidate: dict[str, Any], baseline: dict[str, Any], state_index: int) -> np.ndarray:
    a, z = candidate["states"][state_index], baseline["states"][state_index]
    return np.asarray([
        (a["r_geo_m"] - z["r_geo_m"]) * 1000.0,
        (a["z_geo_m"] - z["z_geo_m"]) * 1000.0,
        a["ip_a"] - z["ip_a"],
    ])


def load(config_path: Path) -> tuple[dict[str, Any], dict[str, dict[str, dict[int, np.ndarray]]]]:
    config_path = b0.inside_root(config_path, "V0 config")
    if b0.sha256(config_path) != CONFIG_SHA256:
        raise InputIntegrityError("V0 config SHA-256 mismatch")
    stage = json.loads(config_path.read_text(encoding="utf-8"))
    _exact_stage(stage)
    payloads = _load_files(stage)
    phase = stage["candidate_issue_phase"]
    contexts: dict[str, dict[str, dict[int, np.ndarray]]] = {}
    q0_baseline = payloads["rgeo_zgeo_1ms_1000_b0_20260821_d3ecd3cd_baseline_primary.json"]
    contexts["q0"] = {}
    for candidate in stage["candidates"]:
        row = payloads[f"p24_{candidate}.json"]
        contexts["q0"][candidate] = {
            horizon: _response(row, q0_baseline, phase + horizon) for horizon in stage["horizons"]
        }
    for context in ("even_plus", "odd_plus"):
        baseline = payloads[f"c_{context}__baseline.json"]
        contexts[context] = {}
        for candidate in stage["candidates"]:
            row = payloads[f"c_{context}__{candidate}.json"]
            contexts[context][candidate] = {
                horizon: _response(row, baseline, phase + horizon) for horizon in stage["horizons"]
            }
    if set(contexts) != set(stage["contexts"]):
        raise InputIntegrityError("V0 context construction changed")
    return stage, contexts


def fit_set(
    contexts: Mapping[str, Mapping[str, Mapping[int, np.ndarray]]],
    candidates: Sequence[str], horizons: Sequence[int], floor: np.ndarray,
) -> dict[str, Any]:
    center: dict[str, dict[int, np.ndarray]] = {}
    halfwidth: dict[str, dict[int, np.ndarray]] = {}
    for candidate in candidates:
        center[candidate], halfwidth[candidate] = {}, {}
        for horizon in horizons:
            values = np.asarray([row[candidate][horizon] for row in contexts.values()])
            median = np.median(values, axis=0)
            center[candidate][horizon] = median
            halfwidth[candidate][horizon] = np.max(np.abs(values - median), axis=0) + floor
    return {"center": center, "halfwidth": halfwidth, "train_contexts": sorted(contexts)}


def evaluate_fold(
    model: dict[str, Any], truth: Mapping[str, Mapping[int, np.ndarray]],
    candidates: Sequence[str], horizons: Sequence[int], direction_count: int,
) -> dict[str, Any]:
    containment = []
    maximum_excess = 0.0
    for candidate in candidates:
        for horizon in horizons:
            error = np.abs(truth[candidate][horizon] - model["center"][candidate][horizon])
            width = model["halfwidth"][candidate][horizon]
            inside = error <= width + 1e-12
            containment.extend(bool(value) for value in inside)
            maximum_excess = max(maximum_excess, float(np.max(error - width)))
    directions = np.asarray([
        [math.cos(2.0 * math.pi * index / direction_count), math.sin(2.0 * math.pi * index / direction_count)]
        for index in range(direction_count)
    ])
    regrets = []
    weakest_progress: dict[int, float] = {}
    for horizon in horizons:
        predicted = np.asarray([model["center"][candidate][horizon][:2] for candidate in candidates])
        actual = np.asarray([truth[candidate][horizon][:2] for candidate in candidates])
        local_progress = []
        for direction in directions:
            predicted_best = int(np.argmax(predicted @ direction))
            true_scores = actual @ direction
            regrets.append(float(np.max(true_scores) - true_scores[predicted_best]))
            local_progress.append(float(np.max(true_scores)))
        weakest_progress[horizon] = min(local_progress)
    return {
        "components": len(containment), "contained_components": sum(containment),
        "all_components_contained": all(containment),
        "maximum_component_excess": max(0.0, maximum_excess),
        "maximum_directional_ranking_regret_mm": max(regrets),
        "weakest_best_progress_mm": {str(key): value for key, value in weakest_progress.items()},
    }


def _serial_model(model: dict[str, Any], candidates: Sequence[str], horizons: Sequence[int]) -> dict[str, Any]:
    return {
        "train_contexts": model["train_contexts"],
        "candidates": {
            candidate: {str(horizon): {
                "center_rz_ip": model["center"][candidate][horizon].tolist(),
                "halfwidth_rz_ip": model["halfwidth"][candidate][horizon].tolist(),
            } for horizon in horizons}
            for candidate in candidates
        },
    }


def execute(config_path: Path, source_revision: str, output_dir: Path) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {output_dir}")
    output_dir.mkdir(parents=True)
    try:
        stage, contexts = load(config_path)
    except Exception as exc:
        result = {
            "schema_version": SCHEMA, "kind": "fixed_1000_direct_value_risk_development",
            "created_utc": datetime.now(timezone.utc).isoformat(), "source_revision": source_revision,
            "passed": False, "route": "ONE_MS_NR1000V0_INPUT_INTEGRITY_FAIL_ZERO_TSC",
            "failures": [f"{type(exc).__name__}:{exc}"], "plant_advances": 0,
        }
        b0.write_new(output_dir / "result.json", result)
        return result
    candidates, horizons = stage["candidates"], stage["horizons"]
    floor = np.asarray(stage["component_floor_rz_ip"], dtype=float)
    folds = []
    for held in stage["contexts"]:
        train = {key: value for key, value in contexts.items() if key != held}
        model = fit_set(train, candidates, horizons, floor)
        folds.append({"held_context": held, **evaluate_fold(
            model, contexts[held], candidates, horizons, stage["direction_grid_count"]
        )})
    final = fit_set(contexts, candidates, horizons, floor)
    final_rz_halfwidth = max(
        float(np.max(final["halfwidth"][candidate][horizon][:2]))
        for candidate in candidates for horizon in horizons
    )
    final_ip_halfwidth = max(
        float(final["halfwidth"][candidate][horizon][2])
        for candidate in candidates for horizon in horizons
    )
    maximum_ip = max(
        abs(float(contexts[context][candidate][horizon][2]))
        for context in contexts for candidate in candidates for horizon in horizons
    )
    gates = stage["gates"]
    containment_pass = all(fold["all_components_contained"] for fold in folds)
    width_pass = (
        final_rz_halfwidth <= gates["maximum_final_rz_halfwidth_mm"]
        and final_ip_halfwidth <= gates["maximum_final_ip_halfwidth_a"]
    )
    ranking_pass = all(
        fold["maximum_directional_ranking_regret_mm"]
        <= gates["maximum_each_fold_directional_ranking_regret_mm"]
        for fold in folds
    )
    progress_pass = all(
        fold["weakest_best_progress_mm"]["8"]
        >= gates["minimum_each_context_h8_weakest_best_progress_mm"]
        for fold in folds
    )
    ip_pass = maximum_ip <= gates["maximum_observed_absolute_ip_response_a"]
    passed = containment_pass and width_pass and ranking_pass and progress_pass and ip_pass
    result = {
        "schema_version": SCHEMA, "kind": "fixed_1000_direct_value_risk_development",
        "created_utc": datetime.now(timezone.utc).isoformat(), "source_revision": source_revision,
        "passed": passed, "route": stage["routes"]["pass"] if passed else stage["routes"]["model_fail"],
        "plant_advances": 0, "context_count": len(contexts), "candidate_count": len(candidates),
        "folds": folds, "final_maximum_rz_halfwidth_mm": final_rz_halfwidth,
        "final_maximum_ip_halfwidth_a": final_ip_halfwidth,
        "maximum_observed_absolute_ip_response_a": maximum_ip,
        "containment_gate_pass": containment_pass, "width_gate_pass": width_pass,
        "ranking_gate_pass": ranking_pass, "progress_gate_pass": progress_pass,
        "ip_gate_pass": ip_pass,
        "claim_boundary": "finite fixed-1000 development response set only; fresh calibration required",
    }
    if passed:
        artifact = {
            "schema_version": f"{SCHEMA}-artifact", "source_revision": source_revision,
            "model": _serial_model(final, candidates, horizons),
            "component_floor_rz_ip": stage["component_floor_rz_ip"],
            "direction_grid_count": stage["direction_grid_count"],
            "qualification": "development_only_fresh_calibration_and_blind_history_required",
        }
        b0.write_new(output_dir / "model_artifact.json", artifact)
        result["model_artifact_sha256"] = b0.sha256(output_dir / "model_artifact.json")
    b0.write_new(output_dir / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = execute(args.config.resolve(), args.source_revision, args.output.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
