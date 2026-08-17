#!/usr/bin/env python3
"""Run the prospectively frozen ID-2K1 factorized development campaign."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import shutil
import sys
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_id0_vector_tail import (  # noqa: E402
    InputIntegrityError, compare_rows, inside_root, raw_inventory, sha256, write_new,
)
from scripts.rgeo_zgeo_1ms_id2c1_active_nominal_vector_search import (  # noqa: E402
    _actions, _translated_target, phase_a_streams,
)
from scripts.rgeo_zgeo_1ms_id2f1_repeated_context_development import (  # noqa: E402
    load as load_id2f1, one_rollout,
)


CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2k1_factorized_history_sign_development.json"
CONFIG_SHA256 = "7ea0e1851104eb1c58a74fb50c8338aa16777c7c48dbfd24927b24184d78332e"
SCHEMA = "rgeo-zgeo-1ms-id2k1-factorized-history-sign-development-result-v1"


def _json(path: Path) -> dict[str, Any]:
    path = inside_root(path, "JSON evidence")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise InputIntegrityError(f"object required: {path.relative_to(ROOT)}")
    return value


def _require_stage(stage: dict[str, Any]) -> None:
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2k1-factorized-history-sign-development-v1",
        "identity": "rgeo-zgeo-1ms-id2k1-factorized-history-sign-development-v1",
        "stage": "ID-2K1", "takeover_time_ms": 1100, "control_period_ms": 1,
        "horizon_steps": 34, "whole_history_groups": 8,
        "unique_cells_per_group": 5, "unique_whole_history_cells": 40,
        "maximum_rollouts": 43, "maximum_reset_calls": 43,
        "maximum_advance_attempts": 1462, "maximum_gotsc_calls": 1462,
        "maximum_verified_plant_advances": 1462, "maximum_retained_states": 1505,
        "retry_after_any_advance_attempt": "forbidden",
        "experiment_contract": "tsc_only_factorized_history_sign_development",
        "data_use": "development_fit_only_after_all_gates_pass",
        "calibration_holdout_controller_expert_or_rl_use": "forbidden",
        "id2c2_records_read": 0, "id2i1_or_id2j0_records_used_for_fit": 0,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise InputIntegrityError(f"frozen field mismatch: {key}")
    if stage.get("critical_replay_cells") != [
        "h00__p07_minus_i25_d3", "h02__p04_minus_i25_d3", "h06__p07_minus_i25_d3"
    ]:
        raise InputIntegrityError("critical replay cells changed")
    matrix = stage.get("probe_matrix", {})
    if matrix != {
        "directions": ["p04", "p07"], "signs": ["plus", "minus"],
        "issue_step": 25, "duration_issues": 3, "first_effect_state": 26,
        "paired_response_state_range_inclusive": [26, 34],
    }:
        raise InputIntegrityError("probe matrix changed")
    groups = stage.get("groups", [])
    if [row.get("group_id") for row in groups] != [f"h{i:02d}" for i in range(8)]:
        raise InputIntegrityError("history group order changed")
    for group in groups:
        for event in group.get("conditioners", []):
            if event.get("direction") not in ("p04", "p07") or event.get("sign") not in ("plus", "minus"):
                raise InputIntegrityError("conditioner grammar changed")
            if event.get("issue_step") not in (18, 21) or event.get("duration_issues") not in (1, 2):
                raise InputIntegrityError("conditioner timing changed")
    if stage.get("data_gates") != {
        "minimum_peak_paired_rz_norm_m": 0.00002,
        "maximum_peak_paired_abs_ip_a": 100.0,
        "all_32_probe_cells_required": True,
        "all_8_by_4_factor_cells_required": True,
        "three_critical_replay_pairs_required": True,
        "rank_condition_and_sign_asymmetry_are_descriptive_only": True,
    }:
        raise InputIntegrityError("data gates changed")
    if stage.get("semantic_artifacts") != ["inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv"]:
        raise InputIntegrityError("semantic artifacts changed")
    if stage.get("diagnostic_artifacts") != ["sprsina"]:
        raise InputIntegrityError("diagnostic artifacts changed")


def load(path: Path = CONFIG) -> tuple[dict[str, Any], Any, dict[str, Any], dict[str, Any]]:
    path = inside_root(path, "ID2K1 config")
    if sha256(path) != CONFIG_SHA256:
        raise InputIntegrityError("ID2K1 config hash mismatch")
    stage = _json(path)
    _require_stage(stage)
    base = inside_root(ROOT / stage["base_tsc_config"], "base TSC config")
    if sha256(base) != stage["evidence"]["base_tsc_config_sha256"]:
        raise InputIntegrityError("base TSC config hash mismatch")
    for name, item in stage["evidence"].items():
        if name == "base_tsc_config_sha256":
            continue
        evidence = inside_root(ROOT / item["path"], name)
        if not evidence.is_file() or sha256(evidence) != item["sha256"]:
            raise InputIntegrityError(f"evidence mismatch: {name}")
    j0 = _json(ROOT / stage["evidence"]["id2j0_result"]["path"])
    j0a = _json(ROOT / stage["evidence"]["id2j0_attribution"]["path"])
    raw = _json(ROOT / stage["evidence"]["id2j0_independent_raw"]["path"])
    attr = _json(ROOT / stage["evidence"]["id2j0_independent_attribution"]["path"])
    if (j0.get("route") != stage["evidence"]["id2j0_result"]["required_route"]
            or not j0.get("passed") or not raw.get("audit_passed")):
        raise InputIntegrityError("ID2J0 data identity changed")
    if (j0a.get("route") != stage["evidence"]["id2j0_attribution"]["required_route"]
            or not attr.get("audit_passed")):
        raise InputIntegrityError("ID2J0 attribution identity changed")
    _, cfg, targets, id2c1_stage = load_id2f1(ROOT / stage["evidence"]["id2f1r1_config"]["path"])
    return stage, cfg, targets, id2c1_stage


def campaign_streams(stage: dict[str, Any], cfg: Any, targets: dict[str, Any],
                     id2c1_stage: dict[str, Any]) -> list[dict[str, Any]]:
    selected = next(row for row in phase_a_streams(id2c1_stage, cfg, targets)
                    if row["candidate_id"] == "p03_minus_stride1")
    held = selected["targets"][15]
    nominal = list(selected["targets"][:16]) + [held] * (stage["horizon_steps"] - 16)
    matrix = stage["probe_matrix"]
    translated = {
        f"{direction}:{sign}": _translated_target(
            held, targets["q0"], targets[f"{direction}:{sign}"], cfg,
            f"id2k1.{direction}.{sign}",
        )
        for direction in matrix["directions"] for sign in matrix["signs"]
    }
    coordinate = {"p04": 0, "p07": 1}
    streams: list[dict[str, Any]] = []
    for group in stage["groups"]:
        cells: list[tuple[str | None, str | None]] = [(None, None)]
        cells += [(direction, sign) for direction in matrix["directions"] for sign in matrix["signs"]]
        for direction, sign in cells:
            cell_id = (f"{group['group_id']}__baseline" if direction is None else
                       f"{group['group_id']}__{direction}_{sign}_i25_d3")
            replay_count = 2 if cell_id in stage["critical_replay_cells"] else 1
            for replay in range(replay_count):
                sequence = list(nominal)
                virtual = [[0.0, 0.0] for _ in sequence]
                non_nominal: list[int] = []
                events = list(group["conditioners"])
                if direction is not None:
                    events.append({"direction": direction, "sign": sign,
                                   "issue_step": matrix["issue_step"],
                                   "duration_issues": matrix["duration_issues"]})
                for event in events:
                    issue, duration = int(event["issue_step"]), int(event["duration_issues"])
                    signed = 1.0 if event["sign"] == "plus" else -1.0
                    for step in range(issue, issue + duration):
                        if sequence[step] != held:
                            raise InputIntegrityError(f"overlapping events: {cell_id}:{step}")
                        sequence[step] = translated[f"{event['direction']}:{event['sign']}"]
                        virtual[step][coordinate[event["direction"]]] = signed
                    non_nominal.append(issue)
                rollout_id = f"{cell_id}__r{replay}"
                streams.append({
                    "rollout_id": rollout_id, "cell_id": cell_id,
                    "group_id": group["group_id"], "context_id": group["group_id"],
                    "replay_index": replay, "cell_kind": "baseline" if direction is None else "probe",
                    "conditioners": group["conditioners"], "direction_id": direction, "sign": sign,
                    "probe_issue_step": None if direction is None else matrix["issue_step"],
                    "probe_duration_issues": 0 if direction is None else matrix["duration_issues"],
                    "non_nominal_issue_steps": sorted(set(non_nominal)),
                    "targets": sequence, "actions": _actions(sequence, cfg, rollout_id, virtual),
                })
    if len(streams) != 43 or len({row["rollout_id"] for row in streams}) != 43:
        raise InputIntegrityError("campaign cardinality changed")
    if len({row["cell_id"] for row in streams}) != 40:
        raise InputIntegrityError("unique cell count changed")
    return streams


def offline(path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    action_rows: list[dict[str, Any]] = []
    try:
        stage, cfg, targets, source = load(path)
        rows = campaign_streams(stage, cfg, targets, source)
        for row in rows:
            if len(row["targets"]) != 34 or len(row["actions"]) != 34:
                raise InputIntegrityError("stream length changed")
            if any(float(action["maximum_issued_delta_a"]) > 0.3 for action in row["actions"]):
                raise InputIntegrityError("issued slew exceeds 0.3 A")
        action_rows = [{key: value for key, value in row.items() if key != "targets"} for row in rows]
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {"schema_version": SCHEMA, "kind": "offline_preflight",
            "source_revision": source_revision, "stage_config_sha256": sha256(path),
            "passed": not failures, "failures": failures, "action_streams": action_rows,
            "reset_calls": 0, "advance_attempts": 0, "plant_advance_gotsc_calls": 0,
            "verified_plant_advances": 0, "models_fit_or_updated": 0,
            "id2c2_records_read": 0, "id2i1_or_id2j0_records_used_for_fit": 0}


def _storage(stage: dict[str, Any], output: Path) -> dict[str, Any]:
    free = shutil.disk_usage(output.parent).free
    gate = stage["storage_gate"]
    estimate = int(gate["maximum_estimated_raw_bytes"])
    return {"free_bytes_before_run": free, "estimated_raw_bytes": estimate,
            "estimated_free_bytes_after_run": free - estimate,
            "passed": free >= int(gate["minimum_free_bytes_before_run"])
            and free - estimate >= int(gate["minimum_free_bytes_after_estimate"])}


def _primary_rows(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if int(row["replay_index"]) == 0]


def matched_prefix_checks(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    by_group: dict[str, list[dict[str, Any]]] = {}
    for row in _primary_rows(rows):
        by_group.setdefault(row["group_id"], []).append(row)
    checks = []
    for group in sorted(by_group):
        members = by_group[group]
        baseline = next((row for row in members if row["cell_kind"] == "baseline"), None)
        failures: list[str] = []
        if baseline is None or len(members) != 5:
            failures.append("CELL_SET")
        else:
            for probe in [row for row in members if row["cell_kind"] == "probe"]:
                for index in range(26):
                    left, right = baseline["states"][index], probe["states"][index]
                    for key in ("r_geo_m", "z_geo_m", "r_mid_m", "ip_a",
                                "actual_current_decimal_a_tsc", "wire_current_a"):
                        if left[key] != right[key]:
                            failures.append(f"{probe['cell_id']}:STATE:{index}:{key}")
                    if index < 25:
                        for name in ("inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv"):
                            if left["artifact_sha256"].get(name) != right["artifact_sha256"].get(name):
                                failures.append(f"{probe['cell_id']}:ARTIFACT:{index}:{name}")
                for issue in range(25):
                    if (baseline["actions"][issue]["expected_card15_fields"]
                            != probe["actions"][issue]["expected_card15_fields"]):
                        failures.append(f"{probe['cell_id']}:ACTION:{issue}")
        checks.append({"group_id": group, "passed": not failures,
                       "failures": list(dict.fromkeys(failures))})
    return checks


def critical_replay_checks(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> list[dict[str, Any]]:
    by_cell: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if row["cell_id"] in stage["critical_replay_cells"]:
            by_cell.setdefault(row["cell_id"], []).append(row)
    shim = {"repeatability": stage["repeatability"], "semantic_artifacts": stage["semantic_artifacts"]}
    checks = []
    for cell_id in stage["critical_replay_cells"]:
        members = by_cell.get(cell_id, [])
        check = ({"passed": False, "failures": ["REPLAY_COUNT"]} if len(members) != 2
                 else compare_rows(members[0], members[1], shim))
        checks.append({"cell_id": cell_id, **check})
    return checks


def response_metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    by_group: dict[str, list[dict[str, Any]]] = {}
    for row in _primary_rows(rows):
        by_group.setdefault(row["group_id"], []).append(row)
    probes, groups = [], []
    for group_id in [f"h{i:02d}" for i in range(8)]:
        members = by_group.get(group_id, [])
        baseline = next((row for row in members if row["cell_kind"] == "baseline"), None)
        vectors = []
        for probe in sorted((row for row in members if row["cell_kind"] == "probe"),
                            key=lambda row: (row["direction_id"], row["sign"])):
            truth = np.asarray([[state[key] for key in ("r_geo_m", "z_geo_m", "ip_a")]
                                for state in probe["states"][26:35]], dtype=float)
            base = np.asarray([[state[key] for key in ("r_geo_m", "z_geo_m", "ip_a")]
                               for state in baseline["states"][26:35]], dtype=float)
            response = truth - base
            norms = np.linalg.norm(response[:, :2], axis=1)
            peak = int(np.argmax(norms))
            vectors.append(response[:, :2].reshape(-1))
            probes.append({"cell_id": probe["cell_id"], "group_id": group_id,
                           "direction": probe["direction_id"], "sign": probe["sign"],
                           "peak_state": 26 + peak, "peak_rz_norm_m": float(norms[peak]),
                           "maximum_abs_ip_response_a": float(np.max(np.abs(response[:, 2]))),
                           "response_by_state": response.tolist()})
        matrix = np.column_stack(vectors) if vectors else np.empty((18, 0))
        rank = int(np.linalg.matrix_rank(matrix)) if matrix.size else 0
        condition = float(np.linalg.cond(matrix)) if rank == min(matrix.shape) and matrix.size else None
        groups.append({"group_id": group_id, "trajectory_response_rank": rank,
                       "trajectory_response_condition": condition})
    gate = stage["data_gates"]
    signal_ok = len(probes) == 32 and all(
        row["peak_rz_norm_m"] >= gate["minimum_peak_paired_rz_norm_m"] for row in probes
    )
    ip_ok = len(probes) == 32 and all(
        row["maximum_abs_ip_response_a"] <= gate["maximum_peak_paired_abs_ip_a"] for row in probes
    )
    return {"probe_count": len(probes), "all_probe_signal_passed": signal_ok,
            "all_probe_ip_passed": ip_ok, "probe_metrics": probes,
            "group_geometry_descriptive": groups,
            "rank_condition_and_sign_asymmetry_are_descriptive_only": True,
            "passed": signal_ok and ip_ok}


def run(path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = inside_root(output, "ID2K1 output")
    if output.exists():
        raise FileExistsError(str(output))
    stage, cfg, targets, source = load(path)
    storage = _storage(stage, output)
    output.mkdir(parents=True)
    preflight = offline(path, source_revision)
    write_new(output / "offline_preflight.json", preflight)
    if not storage["passed"] or not preflight["passed"]:
        route = stage["routes"]["storage_fail" if not storage["passed"] else "offline_or_input_fail"]
        result = {"schema_version": SCHEMA, "source_revision": source_revision,
                  "stage_config_sha256": CONFIG_SHA256, "passed": False, "route": route,
                  "storage_gate": storage, "reasons": preflight["failures"],
                  "rollouts_completed": 0, "reset_calls": 0, "advance_attempts": 0,
                  "plant_advance_gotsc_calls": 0, "verified_plant_advances": 0,
                  "development_fit_data_eligible": False, "models_fit_or_updated": 0}
        write_new(output / "result.json", result)
        return result
    cfg.run_root = output / "rollouts"
    runtime = dict(stage)
    runtime["empirical_exploration"] = dict(stage["empirical_exploration"])
    runtime["empirical_exploration"]["inner_pulse_issue_clearance"] = stage["empirical_exploration"]["inner_probe_issue_clearance"]
    rows = []
    for stream in campaign_streams(stage, cfg, targets, source):
        row = one_rollout(cfg, runtime, stream)
        row.update({"schema_version": SCHEMA, "source_revision": source_revision})
        rows.append(row)
        write_new(output / f"{row['rollout_id']}.json", row)
        if not row["passed"]:
            break
    inventory = raw_inventory(output, rows, stage)
    execution = len(rows) == 43 and all(row["passed"] for row in rows)
    raw_ok = not inventory["missing_required_artifacts"]
    prefixes = matched_prefix_checks(rows) if execution else []
    replays = critical_replay_checks(rows, stage) if execution else []
    metrics = response_metrics(rows, stage) if execution else {"passed": False}
    prefix_replay_ok = (len(prefixes) == 8 and all(row["passed"] for row in prefixes)
                        and len(replays) == 3 and all(row["passed"] for row in replays))
    if not execution:
        route = stage["routes"]["execution_or_interface_fail"]
    elif not raw_ok:
        route = stage["routes"]["raw_integrity_fail"]
    elif not prefix_replay_ok:
        route = stage["routes"]["prefix_or_replay_fail"]
    elif not metrics["passed"]:
        route = stage["routes"]["signal_or_ip_fail"]
    else:
        route = stage["routes"]["pass"]
    passed = route == stage["routes"]["pass"]
    result = {"schema_version": SCHEMA, "source_revision": source_revision,
              "stage_config_sha256": CONFIG_SHA256, "passed": passed, "route": route,
              "storage_gate": storage, "matched_prefix_checks": prefixes,
              "critical_replay_checks": replays, "response_metrics": metrics,
              "rollouts_completed": len(rows), "unique_cells_completed": len({x["cell_id"] for x in rows}),
              "whole_history_groups_completed": len({x["group_id"] for x in rows}),
              "reset_calls": sum(x["reset_calls"] for x in rows),
              "advance_attempts": sum(x["advance_attempts"] for x in rows),
              "plant_advance_gotsc_calls": sum(x["plant_advance_gotsc_calls"] for x in rows),
              "verified_plant_advances": sum(x["verified_plant_advances"] for x in rows),
              **inventory, "development_fit_data_eligible": passed,
              "critical_replays_have_zero_extra_fit_weight": True,
              "calibration_holdout_controller_expert_or_rl_use": "forbidden",
              "models_fit_or_updated": 0, "id2c2_records_read": 0,
              "id2i1_or_id2j0_records_used_for_fit": 0,
              "claim_boundary": stage["claim_boundary"]}
    write_new(output / "result.json", result)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("offline", "run"))
    parser.add_argument("--stage-config", type=Path, default=CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = (offline(args.stage_config, args.source_revision) if args.mode == "offline"
              else run(args.stage_config, args.source_revision,
                       args.output or ROOT / f"rgeo_zgeo_1ms_id2k1_runs_{args.source_revision[:8]}"))
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
