#!/usr/bin/env python3
"""Run the frozen no-fit ID-2S0 sequence-utility selector."""

from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
from pathlib import Path
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_id0_vector_tail import (  # noqa: E402
    InputIntegrityError, inside_root, sha256, write_new,
)
from scripts import rgeo_zgeo_1ms_id2p1_matched_factorial_development as p1  # noqa: E402


CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2s0_sequence_utility_selector.json"
CONFIG_SHA256 = "aaed52b652c935bc6c8246a007af8b3be113b3489d418a236057a9f68086ecb2"
SCHEMA = "rgeo-zgeo-1ms-id2s0-sequence-utility-selector-result-v1"


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(inside_root(path, "JSON evidence").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise InputIntegrityError("JSON object required")
    return value


def _require(stage: dict[str, Any]) -> None:
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2s0-sequence-utility-selector-v1",
        "identity": "rgeo-zgeo-1ms-id2s0-sequence-utility-selector-v1",
        "stage": "ID-2S0", "takeover_time_ms": 1100, "control_period_ms": 1,
        "horizon_steps": 34, "family_id": "f03",
        "first_arm_issue_steps": [24, 25], "first_return_issue_step": 26,
        "second_arm_issue_steps": [27, 28], "second_return_issue_step": 29,
        "arms": ["p04_minus", "p04_plus", "p07_minus", "p07_plus"],
        "ordered_candidate_count": 16, "selected_candidate_count": 4,
        "target_direction_count": 16, "minimum_sample_norm_m": 0.00002,
        "minimum_each_direction_progress_m": 0.00002,
        "maximum_selected_angular_gap_deg": 180.0,
        "selector": "fixed_additive_shift3_exhaustive_four_subset_lexicographic",
        "selection_order": ["maximize_minimum_direction_progress",
                            "maximize_mean_direction_progress",
                            "minimize_maximum_angular_gap", "lexicographic_sequence_ids"],
        "new_tsc_calls": 0, "reset_calls": 0, "plant_advances": 0,
        "models_fit_or_updated": 0, "data_use": "no_fit_candidate_nomination_only",
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise InputIntegrityError(f"frozen field mismatch: {key}")
    if stage.get("action_semantics") != {
        "absolute_card15_targets": True, "maximum_per_coil_issue_delta_a": 0.3,
        "issue_to_effect_state_offset": 1, "software_queue_added": False,
        "legacy_runner_clipping_may_be_relied_on": False,
        "future_actual_current": "forbidden",
    }:
        raise InputIntegrityError("action semantics changed")


def load(path: Path = CONFIG) -> tuple[dict[str, Any], Any, dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    path = inside_root(path, "ID2S0 config")
    if sha256(path) != CONFIG_SHA256:
        raise InputIntegrityError("ID2S0 config hash mismatch")
    stage = _json(path)
    _require(stage)
    evidence = stage["evidence"]
    for name in ("design", "id2p1_config", "id2r0_result", "id2r1_result", "id2r1_independent"):
        item = evidence[name]
        source = inside_root(ROOT / item["path"], name)
        if sha256(source) != item["sha256"]:
            raise InputIntegrityError(f"evidence mismatch: {name}")
    r0 = _json(ROOT / evidence["id2r0_result"]["path"])
    r1 = _json(ROOT / evidence["id2r1_result"]["path"])
    r1a = _json(ROOT / evidence["id2r1_independent"]["path"])
    if r0.get("route") != evidence["id2r0_result"]["required_route"]:
        raise InputIntegrityError("ID2R0 route changed")
    if r1.get("route") != evidence["id2r1_result"]["required_route"] or not r1a.get("audit_passed"):
        raise InputIntegrityError("ID2R1 route changed")
    rows: dict[str, dict[str, Any]] = {}
    for item in evidence["fresh_compacts"]:
        source = inside_root(ROOT / item["path"], item["cell_id"])
        if sha256(source) != item["sha256"]:
            raise InputIntegrityError(f"fresh compact mismatch: {item['cell_id']}")
        row = _json(source)
        if row.get("cell_id") != item["cell_id"] or not row.get("passed"):
            raise InputIntegrityError(f"fresh compact identity: {item['cell_id']}")
        rows[item["cell_id"]] = row
    pstage, cfg, targets, source = p1.load(ROOT / evidence["id2p1_config"]["path"])
    return stage, cfg, targets, source, rows


def _arm_key(row: dict[str, Any]) -> str:
    return f"{row['direction_id']}_{row['sign']}"


def candidate_streams(stage: dict[str, Any], cfg: Any, targets: dict[str, Any],
                      source: dict[str, Any]) -> list[dict[str, Any]]:
    pstage = _json(ROOT / stage["evidence"]["id2p1_config"]["path"])
    f03 = [row for row in p1.campaign_streams(pstage, cfg, targets, source)
           if row["group_id"] == "f03" and int(row["replay_index"]) == 0]
    baseline = next(row for row in f03 if row["cell_kind"] == "baseline")
    arms = {_arm_key(row): row for row in f03 if row["cell_kind"] == "probe"}
    if sorted(arms) != sorted(stage["arms"]):
        raise InputIntegrityError("arm set changed")
    coordinate = {"p04": 0, "p07": 1}
    streams = []
    for first in stage["arms"]:
        for second in stage["arms"]:
            sequence = list(baseline["targets"])
            virtual = [[0.0, 0.0] for _ in sequence]
            for arm, issues in ((first, stage["first_arm_issue_steps"]),
                                (second, stage["second_arm_issue_steps"])):
                source_arm = arms[arm]
                target = source_arm["targets"][24]
                direction, sign = arm.split("_")
                for issue in issues:
                    sequence[issue] = target
                    virtual[issue][coordinate[direction]] = 1.0 if sign == "plus" else -1.0
            sequence_id = f"{first}__then__{second}"
            actions = p1._actions(sequence, cfg, f"id2s0.{sequence_id}", virtual)
            streams.append({"sequence_id": sequence_id, "first_arm": first,
                            "second_arm": second, "targets": sequence, "actions": actions})
    if len(streams) != 16 or len({row["sequence_id"] for row in streams}) != 16:
        raise InputIntegrityError("candidate count changed")
    return streams


def measured_arm_responses(rows: dict[str, dict[str, Any]]) -> dict[str, np.ndarray]:
    baseline = rows["f03__baseline"]
    responses = {}
    for cell_id, row in rows.items():
        if cell_id == "f03__baseline":
            continue
        arm = f"{row['direction_id']}_{row['sign']}"
        responses[arm] = np.asarray([
            [state["r_geo_m"] - base["r_geo_m"], state["z_geo_m"] - base["z_geo_m"]]
            for state, base in zip(row["states"][25:35], baseline["states"][25:35])
        ], dtype=float)
    return responses


def predicted_sequences(streams: Sequence[dict[str, Any]], responses: dict[str, np.ndarray]) -> list[dict[str, Any]]:
    predicted = []
    for stream in streams:
        value = np.array(responses[stream["first_arm"]], copy=True)
        value[3:] += responses[stream["second_arm"]][:-3]
        predicted.append({"sequence_id": stream["sequence_id"],
                          "first_arm": stream["first_arm"], "second_arm": stream["second_arm"],
                          "predicted_rz_response_m": value.tolist()})
    return predicted


def angular_gap(samples: np.ndarray, minimum_norm: float) -> float:
    keep = samples[np.linalg.norm(samples, axis=1) >= minimum_norm]
    if len(keep) < 2:
        return 360.0
    angles = sorted(math.degrees(math.atan2(float(row[1]), float(row[0]))) % 360.0 for row in keep)
    return max(b - a for a, b in zip(angles, angles[1:] + [angles[0] + 360.0]))


def select(stage: dict[str, Any], predicted: Sequence[dict[str, Any]]) -> dict[str, Any]:
    units = np.asarray([[math.cos(2 * math.pi * i / stage["target_direction_count"]),
                         math.sin(2 * math.pi * i / stage["target_direction_count"])]
                        for i in range(stage["target_direction_count"])], dtype=float)
    choices = []
    for subset in itertools.combinations(predicted, stage["selected_candidate_count"]):
        samples = np.concatenate([np.asarray(row["predicted_rz_response_m"], dtype=float) for row in subset])
        progress = np.max(samples @ units.T, axis=0)
        gap = angular_gap(samples, stage["minimum_sample_norm_m"])
        ids = tuple(row["sequence_id"] for row in subset)
        choices.append({"sequence_ids": ids, "minimum_direction_progress_m": float(np.min(progress)),
                        "mean_direction_progress_m": float(np.mean(progress)),
                        "maximum_angular_gap_deg": float(gap),
                        "direction_progress_m": progress.tolist()})
    choices.sort(key=lambda row: (-row["minimum_direction_progress_m"],
                                  -row["mean_direction_progress_m"],
                                  row["maximum_angular_gap_deg"], row["sequence_ids"]))
    return {**choices[0], "sequence_ids": list(choices[0]["sequence_ids"]),
            "subsets_evaluated": len(choices)}


def execute(path: Path, source_revision: str) -> dict[str, Any]:
    try:
        stage, cfg, targets, source, rows = load(path)
        streams = candidate_streams(stage, cfg, targets, source)
        action_ok = all(len(row["actions"]) == 34 and all(
            float(action["maximum_issued_delta_a"]) <= 0.3 for action in row["actions"])
                        for row in streams)
        responses = measured_arm_responses(rows)
        predicted = predicted_sequences(streams, responses)
        selection = select(stage, predicted)
        utility_ok = (selection["minimum_direction_progress_m"] >= stage["minimum_each_direction_progress_m"]
                      and selection["maximum_angular_gap_deg"] < stage["maximum_selected_angular_gap_deg"])
        route = stage["routes"]["pass" if action_ok and utility_ok else
                                ("action_stream_fail" if not action_ok else "utility_fail")]
        selected = set(selection["sequence_ids"])
        selected_streams = [{**{key: value for key, value in row.items() if key != "targets"},
                             "selected": row["sequence_id"] in selected} for row in streams]
        return {"schema_version": SCHEMA, "source_revision": source_revision,
                "stage_config_sha256": CONFIG_SHA256, "passed": route == stage["routes"]["pass"],
                "route": route, "action_stream_gate_passed": action_ok,
                "utility_gate_passed": utility_ok, "selection": selection,
                "candidate_streams": selected_streams, "predicted_candidates": predicted,
                "new_tsc_calls": 0, "reset_calls": 0, "plant_advances": 0,
                "models_fit_or_updated": 0, "claim_boundary": stage["claim_boundary"]}
    except Exception as exc:
        stage = _json(path)
        return {"schema_version": SCHEMA, "source_revision": source_revision,
                "stage_config_sha256": sha256(path), "passed": False,
                "route": stage["routes"]["input_or_reproduction_fail"],
                "failures": [f"{type(exc).__name__}:{exc}"], "new_tsc_calls": 0,
                "reset_calls": 0, "plant_advances": 0, "models_fit_or_updated": 0}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-config", type=Path, default=CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = execute(args.stage_config, args.source_revision)
    write_new(inside_root(args.output, "ID2S0 output"), result)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

