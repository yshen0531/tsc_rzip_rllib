#!/usr/bin/env python3
"""Run the prospectively frozen ID-2P1 matched-factorial campaign."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
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
from scripts.rgeo_zgeo_1ms_id2f1_repeated_context_development import one_rollout  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2k1_factorized_history_sign_development as k1  # noqa: E402


CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2p1_matched_factorial_development.json"
CONFIG_SHA256 = "9572635bb62a9e81609289b53527d329bb5b09f08e46a2cbc886eafa3e93323f"
SCHEMA = "rgeo-zgeo-1ms-id2p1-matched-factorial-development-result-v1"


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(inside_root(path, "JSON evidence").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise InputIntegrityError("JSON object required")
    return value


def _require(stage: dict[str, Any]) -> None:
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2p1-matched-factorial-development-v1",
        "identity": "rgeo-zgeo-1ms-id2p1-matched-factorial-development-v1",
        "stage": "ID-2P1", "takeover_time_ms": 1100, "control_period_ms": 1,
        "horizon_steps": 34, "whole_history_groups": 8, "unique_cells_per_group": 5,
        "unique_whole_history_cells": 40, "maximum_rollouts": 42,
        "maximum_reset_calls": 42, "maximum_advance_attempts": 1428,
        "maximum_gotsc_calls": 1428, "maximum_verified_plant_advances": 1428,
        "maximum_retained_states": 1470, "retry_after_any_advance_attempt": "forbidden",
        "experiment_contract": "tsc_only_matched_factorial_fit_eligible_development",
        "data_use": "development_fit_only_after_all_execution_raw_prefix_replay_signal_and_ip_gates_pass",
        "calibration_holdout_controller_expert_or_rl_use": "forbidden",
        "source_model_or_response_labels_used": 0,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise InputIntegrityError(f"frozen field mismatch: {key}")
    if stage.get("critical_replay_cells") != ["f01__p07_minus_i26_d1", "f04__p04_plus_i25_d3"]:
        raise InputIntegrityError("critical replays changed")
    if stage.get("probe_directions") != ["p04", "p07"] or stage.get("probe_signs") != ["plus", "minus"]:
        raise InputIntegrityError("probe grammar changed")
    groups = stage.get("groups", [])
    if [row.get("group_id") for row in groups] != [f"f{i:02d}" for i in range(8)]:
        raise InputIntegrityError("group order changed")
    for group in groups:
        issue, duration = int(group["probe_issue_step"]), int(group["probe_duration_issues"])
        if issue not in (24, 25, 26) or duration not in (1, 2, 3) or issue + duration > 29:
            raise InputIntegrityError("probe timing changed")
        occupied: set[int] = set()
        for event in group["conditioners"]:
            if event["direction"] not in ("p04", "p07") or event["sign"] not in ("plus", "minus"):
                raise InputIntegrityError("conditioner grammar changed")
            for step in range(int(event["issue_step"]), int(event["issue_step"]) + int(event["duration_issues"])):
                if step in occupied or step >= issue:
                    raise InputIntegrityError("overlapping conditioner")
                occupied.add(step)
    if stage["action_semantics"] != {
        "absolute_card15_targets": True, "maximum_per_coil_issue_delta_a": 0.3,
        "issue_to_effect_state_offset": 1, "software_queue_added": False,
        "legacy_runner_clipping_may_be_relied_on": False, "future_actual_current": "forbidden",
    }:
        raise InputIntegrityError("action semantics changed")
    if stage["semantic_artifacts"] != ["inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv"]:
        raise InputIntegrityError("semantic artifacts changed")
    if stage["diagnostic_artifacts"] != ["sprsina"]:
        raise InputIntegrityError("diagnostic artifacts changed")


def load(path: Path = CONFIG) -> tuple[dict[str, Any], Any, dict[str, Any], dict[str, Any]]:
    path = inside_root(path, "ID2P1 config")
    if sha256(path) != CONFIG_SHA256:
        raise InputIntegrityError("ID2P1 config hash mismatch")
    stage = _json(path)
    _require(stage)
    for name, spec in stage["evidence"].items():
        evidence = inside_root(ROOT / spec["path"], name)
        if sha256(evidence) != spec["sha256"]:
            raise InputIntegrityError(f"evidence mismatch: {name}")
    if _json(ROOT / stage["evidence"]["id2k1_result"]["path"])["route"] != stage["evidence"]["id2k1_result"]["required_route"]:
        raise InputIntegrityError("K1 route changed")
    o0 = _json(ROOT / stage["evidence"]["id2o0_result"]["path"])
    o0a = _json(ROOT / stage["evidence"]["id2o0_independent"]["path"])
    if o0.get("route") != stage["evidence"]["id2o0_result"]["required_route"] or o0.get("support_ready_for_model_comparison"):
        raise InputIntegrityError("ID2O0 route changed")
    if not o0a.get("audit_passed"):
        raise InputIntegrityError("ID2O0 independent audit failed")
    _, cfg, targets, source = k1.load(ROOT / stage["evidence"]["id2k1_config"]["path"])
    return stage, cfg, targets, source


def campaign_streams(stage: dict[str, Any], cfg: Any, targets: dict[str, Any],
                     source: dict[str, Any]) -> list[dict[str, Any]]:
    selected = next(row for row in phase_a_streams(source, cfg, targets)
                    if row["candidate_id"] == "p03_minus_stride1")
    held = selected["targets"][15]
    nominal = list(selected["targets"][:16]) + [held] * (stage["horizon_steps"] - 16)
    translated = {f"{direction}:{sign}": _translated_target(
        held, targets["q0"], targets[f"{direction}:{sign}"], cfg,
        f"id2p1.{direction}.{sign}")
        for direction in stage["probe_directions"] for sign in stage["probe_signs"]}
    coordinate = {"p04": 0, "p07": 1}
    streams: list[dict[str, Any]] = []
    for group in stage["groups"]:
        cells = [(None, None), *[(direction, sign) for direction in stage["probe_directions"]
                                 for sign in stage["probe_signs"]]]
        for direction, sign in cells:
            issue, duration = int(group["probe_issue_step"]), int(group["probe_duration_issues"])
            cell_id = (f"{group['group_id']}__baseline" if direction is None else
                       f"{group['group_id']}__{direction}_{sign}_i{issue}_d{duration}")
            for replay in range(2 if cell_id in stage["critical_replay_cells"] else 1):
                sequence, virtual = list(nominal), [[0.0, 0.0] for _ in nominal]
                events = list(group["conditioners"])
                if direction is not None:
                    events.append({"direction": direction, "sign": sign,
                                   "issue_step": issue, "duration_issues": duration})
                non_nominal: list[int] = []
                for event in events:
                    for step in range(int(event["issue_step"]),
                                      int(event["issue_step"]) + int(event["duration_issues"])):
                        if sequence[step] != held:
                            raise InputIntegrityError(f"overlapping event: {cell_id}:{step}")
                        sequence[step] = translated[f"{event['direction']}:{event['sign']}"]
                        virtual[step][coordinate[event["direction"]]] = 1.0 if event["sign"] == "plus" else -1.0
                    non_nominal.append(int(event["issue_step"]))
                rollout_id = f"{cell_id}__r{replay}"
                streams.append({
                    "rollout_id": rollout_id, "cell_id": cell_id,
                    "group_id": group["group_id"], "context_id": group["group_id"],
                    "replay_index": replay, "cell_kind": "baseline" if direction is None else "probe",
                    "conditioners": group["conditioners"], "direction_id": direction, "sign": sign,
                    "probe_issue_step": None if direction is None else issue,
                    "probe_duration_issues": 0 if direction is None else duration,
                    "non_nominal_issue_steps": sorted(set(non_nominal)),
                    "targets": sequence, "actions": _actions(sequence, cfg, rollout_id, virtual),
                })
    if len(streams) != 42 or len({row["cell_id"] for row in streams}) != 40:
        raise InputIntegrityError("campaign cardinality changed")
    return streams


def offline(path: Path, source_revision: str) -> dict[str, Any]:
    failures, action_rows = [], []
    try:
        stage, cfg, targets, source = load(path)
        rows = campaign_streams(stage, cfg, targets, source)
        for row in rows:
            if len(row["actions"]) != 34 or any(float(action["maximum_issued_delta_a"]) > 0.3 for action in row["actions"]):
                raise InputIntegrityError("action stream invalid")
        action_rows = [{key: value for key, value in row.items() if key != "targets"} for row in rows]
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {"schema_version": SCHEMA, "kind": "offline_preflight",
            "source_revision": source_revision, "stage_config_sha256": sha256(path),
            "passed": not failures, "failures": failures, "action_streams": action_rows,
            "reset_calls": 0, "advance_attempts": 0, "plant_advance_gotsc_calls": 0,
            "verified_plant_advances": 0, "models_fit_or_updated": 0}


def _primary(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if int(row["replay_index"]) == 0]


def matched_prefix_checks(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> list[dict[str, Any]]:
    checks = []
    for group in stage["groups"]:
        members = [row for row in _primary(rows) if row["group_id"] == group["group_id"]]
        baseline = next((row for row in members if row["cell_kind"] == "baseline"), None)
        failures = []
        if baseline is None or len(members) != 5:
            failures.append("CELL_SET")
        else:
            issue = int(group["probe_issue_step"])
            for probe in [row for row in members if row["cell_kind"] == "probe"]:
                for index in range(issue + 1):
                    for key in ("r_geo_m", "z_geo_m", "r_mid_m", "ip_a",
                                "actual_current_decimal_a_tsc", "wire_current_a"):
                        if baseline["states"][index][key] != probe["states"][index][key]:
                            failures.append(f"{probe['cell_id']}:STATE:{index}:{key}")
                for step in range(issue):
                    if baseline["actions"][step]["expected_card15_fields"] != probe["actions"][step]["expected_card15_fields"]:
                        failures.append(f"{probe['cell_id']}:ACTION:{step}")
        checks.append({"group_id": group["group_id"], "passed": not failures,
                       "failures": list(dict.fromkeys(failures))})
    return checks


def replay_checks(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> list[dict[str, Any]]:
    shim = {"repeatability": stage["repeatability"], "semantic_artifacts": stage["semantic_artifacts"]}
    checks = []
    for cell_id in stage["critical_replay_cells"]:
        members = [row for row in rows if row["cell_id"] == cell_id]
        check = ({"passed": False, "failures": ["REPLAY_COUNT"]} if len(members) != 2
                 else compare_rows(members[0], members[1], shim))
        checks.append({"cell_id": cell_id, **check})
    return checks


def response_metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    metrics = []
    for group in stage["groups"]:
        members = [row for row in _primary(rows) if row["group_id"] == group["group_id"]]
        baseline = next(row for row in members if row["cell_kind"] == "baseline")
        origin = int(group["probe_issue_step"])
        for probe in [row for row in members if row["cell_kind"] == "probe"]:
            truth = np.asarray([[state[key] for key in ("r_geo_m", "z_geo_m", "ip_a")]
                                for state in probe["states"][origin + 1:35]], dtype=float)
            base = np.asarray([[state[key] for key in ("r_geo_m", "z_geo_m", "ip_a")]
                               for state in baseline["states"][origin + 1:35]], dtype=float)
            response = truth - base
            norms = np.linalg.norm(response[:, :2], axis=1)
            peak = int(np.argmax(norms))
            metrics.append({"cell_id": probe["cell_id"], "group_id": group["group_id"],
                            "direction": probe["direction_id"], "sign": probe["sign"],
                            "peak_state": origin + 1 + peak, "peak_rz_norm_m": float(norms[peak]),
                            "maximum_abs_ip_response_a": float(np.max(np.abs(response[:, 2]))),
                            "response_by_state": response.tolist()})
    gates = stage["data_gates"]
    signal = len(metrics) == 32 and all(row["peak_rz_norm_m"] >= gates["minimum_peak_paired_rz_norm_m"] for row in metrics)
    ip_ok = len(metrics) == 32 and all(row["maximum_abs_ip_response_a"] <= gates["maximum_peak_paired_abs_ip_a"] for row in metrics)
    return {"probe_count": len(metrics), "all_probe_signal_passed": signal,
            "all_probe_ip_passed": ip_ok, "probe_metrics": metrics, "passed": signal and ip_ok}


def storage(stage: dict[str, Any], output: Path) -> dict[str, Any]:
    free = shutil.disk_usage(output.parent).free
    gate, estimate = stage["storage_gate"], int(stage["storage_gate"]["maximum_estimated_raw_bytes"])
    return {"free_bytes_before_run": free, "estimated_raw_bytes": estimate,
            "estimated_free_bytes_after_run": free - estimate,
            "passed": free >= int(gate["minimum_free_bytes_before_run"])
            and free - estimate >= int(gate["minimum_free_bytes_after_estimate"])}


def run(path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = inside_root(output, "ID2P1 output")
    if output.exists():
        raise FileExistsError(str(output))
    stage, cfg, targets, source = load(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    storage_gate = storage(stage, output)
    output.mkdir()
    preflight = offline(path, source_revision)
    write_new(output / "offline_preflight.json", preflight)
    if not storage_gate["passed"] or not preflight["passed"]:
        route = stage["routes"]["storage_fail" if not storage_gate["passed"] else "offline_or_input_fail"]
        result = {"schema_version": SCHEMA, "source_revision": source_revision,
                  "stage_config_sha256": CONFIG_SHA256, "passed": False, "route": route,
                  "storage_gate": storage_gate, "reasons": preflight["failures"],
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
    execution = len(rows) == 42 and all(row["passed"] for row in rows)
    prefixes = matched_prefix_checks(rows, stage) if execution else []
    replays = replay_checks(rows, stage) if execution else []
    metrics = response_metrics(rows, stage) if execution else {"passed": False}
    if not execution:
        route = stage["routes"]["execution_or_interface_fail"]
    elif inventory["missing_required_artifacts"]:
        route = stage["routes"]["raw_integrity_fail"]
    elif not (all(row["passed"] for row in prefixes) and all(row["passed"] for row in replays)):
        route = stage["routes"]["prefix_or_replay_fail"]
    elif not metrics["passed"]:
        route = stage["routes"]["signal_or_ip_fail"]
    else:
        route = stage["routes"]["pass"]
    passed = route == stage["routes"]["pass"]
    result = {"schema_version": SCHEMA, "source_revision": source_revision,
              "stage_config_sha256": CONFIG_SHA256, "passed": passed, "route": route,
              "storage_gate": storage_gate, "matched_prefix_checks": prefixes,
              "critical_replay_checks": replays, "response_metrics": metrics,
              "rollouts_completed": len(rows), "unique_cells_completed": len({row["cell_id"] for row in rows}),
              "whole_history_groups_completed": len({row["group_id"] for row in rows}),
              "reset_calls": sum(row["reset_calls"] for row in rows),
              "advance_attempts": sum(row["advance_attempts"] for row in rows),
              "plant_advance_gotsc_calls": sum(row["plant_advance_gotsc_calls"] for row in rows),
              "verified_plant_advances": sum(row["verified_plant_advances"] for row in rows),
              **inventory, "development_fit_data_eligible": passed,
              "critical_replays_have_zero_extra_fit_weight": True,
              "calibration_holdout_controller_expert_or_rl_use": "forbidden",
              "models_fit_or_updated": 0, "claim_boundary": stage["claim_boundary"]}
    write_new(output / "result.json", result)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("offline", "run"))
    parser.add_argument("--stage-config", type=Path, default=CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = offline(args.stage_config, args.source_revision) if args.mode == "offline" else run(
        args.stage_config, args.source_revision, args.output or ROOT / f"rgeo_zgeo_1ms_id2p1_{args.source_revision[:8]}")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
