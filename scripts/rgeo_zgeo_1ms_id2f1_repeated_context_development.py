#!/usr/bin/env python3
"""Run the prospectively frozen ID-2F1 repeated-context TSC campaign."""

from __future__ import annotations

import argparse
from decimal import Decimal
import json
import math
from pathlib import Path
import shutil
import sys
import time
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_id0_vector_tail import (  # noqa: E402
    CountingRunner,
    InputIntegrityError,
    _outer_reasons,
    _pulse_clearance,
    _step_cap_reasons,
    _validate_record,
    compare_rows,
    inside_root,
    raw_inventory,
    sha256,
    write_new,
)
from scripts.rgeo_zgeo_1ms_nr1_qualification import _record  # noqa: E402
from scripts.rgeo_zgeo_1ms_id2c1_active_nominal_vector_search import (  # noqa: E402
    _actions,
    _translated_target,
    load as load_id2c1,
    phase_a_streams,
)
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    OneMsNR1SafetyEnvelope,
    assert_exact_slew,
    card15_target_decimal_a,
)
from tsc_rzip_rllib.control.rgeo_zgeo_contract import ContractError, RGeoZGeoSignal  # noqa: E402
from tsc_rzip_rllib.core.runner import TSCStepRunner  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-id2f1r1-repeated-context-development-result-v1"
CONFIG_SHA256 = "2c97be4f3adbc684bcb7ed7782d76822e8071c919f92882e3141b3bf934e1831"
DEFAULT_CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2f1r1_repeated_context_development.json"
ID2C1_CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2c1_active_nominal_vector_search.json"
DESIGN = ROOT / "docs/codex/reports/RGEO_ZGEO_1MS_ID2F1R1_REPEATED_CONTEXT_DEVELOPMENT_DESIGN.md"


def _require_stage(stage: dict[str, Any]) -> None:
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2f1r1-repeated-context-development-v1",
        "stage_id": "rgeo_zgeo_1ms_id2f1r1_repeated_context_development_v1",
        "supersedes": "rgeo_zgeo_1ms_id2f1_repeated_context_development_v1",
        "takeover_time_ms": 1100,
        "control_period_ms": 1,
        "horizon_steps": 34,
        "unique_whole_history_cells": 39,
        "replays_per_cell": 2,
        "maximum_rollouts": 78,
        "maximum_reset_calls": 78,
        "maximum_advance_attempts": 2652,
        "maximum_gotsc_calls": 2652,
        "maximum_verified_plant_advances": 2652,
        "maximum_retained_states": 2730,
        "retry_after_any_advance_attempt": "forbidden",
        "id2c2_records_read": 0,
        "probe_issue_step": 22,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise InputIntegrityError(f"frozen field mismatch: {key}")
    if stage.get("probe_directions") != ["p04", "p07"]:
        raise InputIntegrityError("probe directions changed")
    if stage.get("probe_signs") != ["plus", "minus"]:
        raise InputIntegrityError("probe signs changed")
    if stage.get("probe_duration_issues") != [1, 2, 4]:
        raise InputIntegrityError("probe durations changed")
    contexts = stage.get("contexts")
    expected_contexts = [
        {"context_id": "none", "conditioner_direction": None, "conditioner_sign": None,
         "conditioner_issue_step": None, "conditioner_duration_issues": 0},
        {"context_id": "p04_plus_i18_d1", "conditioner_direction": "p04", "conditioner_sign": "plus",
         "conditioner_issue_step": 18, "conditioner_duration_issues": 1},
        {"context_id": "p07_plus_i18_d1", "conditioner_direction": "p07", "conditioner_sign": "plus",
         "conditioner_issue_step": 18, "conditioner_duration_issues": 1},
    ]
    if contexts != expected_contexts:
        raise InputIntegrityError("context matrix changed")
    if stage.get("semantic_artifacts") != ["inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv"]:
        raise InputIntegrityError("semantic artifacts changed")
    if stage.get("diagnostic_artifacts") != ["sprsina"]:
        raise InputIntegrityError("diagnostic artifacts changed")
    routes = stage.get("routes", {})
    if set(routes) != {"offline_or_input_fail", "storage_fail", "execution_or_interface_fail",
                       "raw_integrity_fail", "repeatability_fail", "action_support_fail",
                       "signal_or_ip_fail", "pass"}:
        raise InputIntegrityError("route table changed")


def load(stage_path: Path) -> tuple[dict[str, Any], Any, dict[str, Any], dict[str, Any]]:
    stage_path = inside_root(stage_path, "ID2F1 config")
    if sha256(stage_path) != CONFIG_SHA256:
        raise InputIntegrityError("ID2F1 config hash mismatch")
    stage = json.loads(stage_path.read_text(encoding="utf-8"))
    _require_stage(stage)
    if sha256(inside_root(DESIGN, "ID2F1 design")) != stage["evidence"]["design_sha256"]:
        raise InputIntegrityError("ID2F1 design hash mismatch")
    base = inside_root(ROOT / stage["base_tsc_config"], "base config")
    if sha256(base) != stage["evidence"]["base_tsc_config_sha256"]:
        raise InputIntegrityError("base config hash mismatch")
    for key in ("id2f1_v1_config", "id2f1_v1_design", "id2f1_v1_offline_audit",
                "id2c1_config", "id2c1_compact", "id2d1r1_config", "id2d1r1_compact",
                "id2e1_compact", "id2c2_config", "route_review"):
        item = stage["evidence"][key]
        path = inside_root(ROOT / item["path"], key)
        if sha256(path) != item["sha256"]:
            raise InputIntegrityError(f"{key} hash mismatch")
    id2d1 = json.loads((ROOT / stage["evidence"]["id2d1r1_compact"]["path"]).read_text(encoding="utf-8"))
    if id2d1.get("primary_route") != stage["evidence"]["id2d1r1_required_route"]:
        raise InputIntegrityError("ID2D1R1 route mismatch")
    id2e1 = json.loads((ROOT / stage["evidence"]["id2e1_compact"]["path"]).read_text(encoding="utf-8"))
    if id2e1.get("route") != stage["evidence"]["id2e1_required_route"]:
        raise InputIntegrityError("ID2E1 route mismatch")
    if bool(id2e1.get("evaluator_opened")) is not stage["evidence"]["id2e1_evaluator_opened_required"]:
        raise InputIntegrityError("ID2E1 evaluator-use mismatch")
    id2c1_stage, cfg, _, targets = load_id2c1(ID2C1_CONFIG)
    return stage, cfg, targets, id2c1_stage


def campaign_streams(stage: dict[str, Any], cfg: Any, targets: dict[str, Any],
                     id2c1_stage: dict[str, Any]) -> list[dict[str, Any]]:
    selected = next(row for row in phase_a_streams(id2c1_stage, cfg, targets)
                    if row["candidate_id"] == "p03_minus_stride1")
    held = selected["targets"][15]
    nominal = list(selected["targets"][:16]) + [held] * (stage["horizon_steps"] - 16)
    translated = {
        f"{direction}:{sign}": _translated_target(
            held, targets["q0"], targets[f"{direction}:{sign}"], cfg,
            f"id2f1.{direction}.{sign}",
        )
        for direction in stage["probe_directions"] for sign in stage["probe_signs"]
    }
    cells: list[dict[str, Any]] = []
    for context in stage["contexts"]:
        cells.append({"context": context, "direction": None, "sign": None, "duration": 0})
        for direction in stage["probe_directions"]:
            for sign in stage["probe_signs"]:
                for duration in stage["probe_duration_issues"]:
                    cells.append({"context": context, "direction": direction,
                                  "sign": sign, "duration": duration})
    if len(cells) != stage["unique_whole_history_cells"]:
        raise InputIntegrityError("whole-history cell count changed")
    streams: list[dict[str, Any]] = []
    coordinate = {"p04": 0, "p07": 1}
    for cell in cells:
        context = cell["context"]
        context_id = context["context_id"]
        direction = cell["direction"]
        sign = cell["sign"]
        duration = int(cell["duration"])
        cell_id = f"{context_id}__baseline" if direction is None else f"{context_id}__{direction}_{sign}_i22_d{duration}"
        for replay in range(stage["replays_per_cell"]):
            rollout_id = f"{cell_id}__r{replay}"
            sequence = list(nominal)
            virtual = [[0.0, 0.0] for _ in sequence]
            non_nominal: list[int] = []
            conditioner_direction = context["conditioner_direction"]
            conditioner_issue = context["conditioner_issue_step"]
            if conditioner_direction is not None:
                conditioner_sign = str(context["conditioner_sign"])
                issue = int(conditioner_issue)
                duration_context = int(context["conditioner_duration_issues"])
                for step in range(issue, issue + duration_context):
                    sequence[step] = translated[f"{conditioner_direction}:{conditioner_sign}"]
                    virtual[step][coordinate[conditioner_direction]] = 1.0
                non_nominal.append(issue)
            if direction is not None:
                issue = int(stage["probe_issue_step"])
                signed = 1.0 if sign == "plus" else -1.0
                for step in range(issue, issue + duration):
                    sequence[step] = translated[f"{direction}:{sign}"]
                    virtual[step][coordinate[direction]] = signed
                non_nominal.append(issue)
            streams.append({
                "rollout_id": rollout_id,
                "cell_id": cell_id,
                "replay_index": replay,
                "cell_kind": "baseline" if direction is None else "probe",
                "context_id": context_id,
                "conditioner_direction": conditioner_direction,
                "conditioner_sign": context["conditioner_sign"],
                "conditioner_issue_step": conditioner_issue,
                "conditioner_duration_issues": context["conditioner_duration_issues"],
                "direction_id": direction,
                "sign": sign,
                "probe_issue_step": None if direction is None else stage["probe_issue_step"],
                "probe_duration_issues": duration,
                "non_nominal_issue_steps": sorted(non_nominal),
                "targets": sequence,
                "actions": _actions(sequence, cfg, rollout_id, virtual),
            })
    if len(streams) != stage["maximum_rollouts"]:
        raise InputIntegrityError("rollout count changed")
    if any(row["probe_issue_step"] == 16 and row["probe_duration_issues"] == 1 for row in streams):
        raise InputIntegrityError("ID2C2 evaluator cell leaked into ID2F1")
    return streams


def lag_support(streams: Sequence[dict[str, Any]], lag_steps: int) -> dict[str, Any]:
    rows: list[list[float]] = []
    for stream in streams:
        u = np.asarray([action["probe_virtual_action"] for action in stream["actions"]], dtype=float)
        for issue in range(len(u)):
            feature: list[float] = []
            for lag in range(lag_steps):
                feature.extend(u[issue - lag].tolist() if issue >= lag else [0.0, 0.0])
            rows.append(feature)
    matrix = np.asarray(rows, dtype=float)
    singular = np.linalg.svd(matrix, compute_uv=False)
    return {
        "rows": int(matrix.shape[0]), "columns": int(matrix.shape[1]),
        "rank": int(np.linalg.matrix_rank(matrix)),
        "condition": float(singular[0] / singular[-1]) if singular.size and singular[-1] > 0 else math.inf,
        "minimum_singular_value": float(singular[-1]) if singular.size else 0.0,
    }


def clearance_required(issue: int, stream: dict[str, Any]) -> bool:
    return issue in set(int(value) for value in stream["non_nominal_issue_steps"])


def one_rollout(cfg: Any, stage: dict[str, Any], stream: dict[str, Any],
                *, runner_cls: type[TSCStepRunner] = CountingRunner) -> dict[str, Any]:
    """Execute one stream, checking clearance at every declared novel event."""
    runner: TSCStepRunner | None = None
    states: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    attempted: list[dict[str, Any]] = []
    reasons: list[str] = []
    reset_calls = attempts = successes = 0
    started = time.perf_counter()
    try:
        runner = runner_cls(cfg, worker_id=f"id2f1_{stream['rollout_id']}", keep_workspace=False)
        reset_calls += 1
        state = runner.reset(episode_name=stream["rollout_id"])
        states.append(_record(cfg, state))
        _validate_record(states[-1], f"{stream['rollout_id']}.state0")
        if states[0]["time_ms"] != 1100 or int(state.get("returncode", 0)) != 0 or bool(state.get("abnormal", False)):
            reasons.append("SOURCE_RESET_INVALID")
        source_signal = RGeoZGeoSignal.from_tsc_state(state)
        envelope = OneMsNR1SafetyEnvelope.from_signal(source_signal)
        for issue, (target, frozen_action) in enumerate(zip(stream["targets"], stream["actions"])):
            if reasons:
                break
            signal = RGeoZGeoSignal.from_tsc_state(state)
            reasons.extend(envelope.state_reasons(signal, state["currents_a_tsc"],
                                                   cfg.min_current_a_tsc, cfg.max_current_a_tsc))
            reasons.extend(_outer_reasons(stage, source_signal, signal))
            if clearance_required(issue, stream):
                reasons.extend(_pulse_clearance(stage, source_signal, signal))
            exact = card15_target_decimal_a(target, cfg.turns_tsc,
                                             name=f"id2f1.{stream['rollout_id']}.{issue}")
            try:
                maximum = assert_exact_slew(states[-1]["active_command_decimal_a_tsc"], exact,
                                            name=f"id2f1.issue.{stream['rollout_id']}.{issue}")
                if any(value < Decimal(str(low)) or value > Decimal(str(high))
                       for value, low, high in zip(exact, cfg.min_current_a_tsc, cfg.max_current_a_tsc)):
                    raise ContractError("target leaves absolute current limits")
            except Exception as exc:
                reasons.append(f"ISSUED_ACTION:{issue}:{type(exc).__name__}:{exc}")
                break
            if reasons:
                break
            action = dict(frozen_action)
            action["maximum_issued_delta_a"] = maximum
            attempted.append(action)
            attempts += 1
            try:
                successor = runner.step_current_a(np.asarray(target.current_a_tsc, dtype=float))
            except Exception as exc:
                reasons.append(f"STEP_EXECUTION:{issue}:{type(exc).__name__}:{exc}")
                break
            try:
                record = _record(cfg, successor)
                _validate_record(record, f"{stream['rollout_id']}.state{issue + 1}")
            except Exception as exc:
                reasons.append(f"SUCCESSOR_RECORD:{issue}:{type(exc).__name__}:{exc}")
                break
            if record["time_ms"] != 1101 + issue:
                reasons.append(f"TIME:{issue}:{record['time_ms']}")
                break
            states.append(record)
            if int(successor.get("returncode", 0)) != 0 or bool(successor.get("abnormal", False)):
                reasons.append(f"TSC_STATUS:{issue}:{successor.get('returncode', 0)}:{successor.get('done_reason', '')}")
                break
            actions.append(action)
            successes += 1
            if tuple(record["active_command_card15_fields"]) != target.card15_fields:
                reasons.append(f"CARD15:{issue}")
            try:
                record["maximum_observed_delta_a"] = assert_exact_slew(
                    states[-2]["actual_current_decimal_a_tsc"], record["actual_current_decimal_a_tsc"],
                    name=f"id2f1.observed.{stream['rollout_id']}.{issue}")
            except Exception as exc:
                reasons.append(f"OBSERVED_SLEW:{issue}:{type(exc).__name__}:{exc}")
            successor_signal = RGeoZGeoSignal.from_tsc_state(successor)
            reasons.extend(envelope.state_reasons(successor_signal, successor["currents_a_tsc"],
                                                   cfg.min_current_a_tsc, cfg.max_current_a_tsc))
            reasons.extend(_outer_reasons(stage, source_signal, successor_signal))
            reasons.extend(_step_cap_reasons(stage, states[-2], states[-1]))
            state = successor
            if reasons:
                break
    except Exception as exc:
        reasons.append(f"ROLLOUT_EXECUTION:{type(exc).__name__}:{exc}")
    finally:
        if runner is not None:
            try:
                runner.cleanup_runtime_workspace()
            except Exception as exc:
                reasons.append(f"CLEANUP:{type(exc).__name__}:{exc}")
    reasons = list(dict.fromkeys(reasons))
    gotsc = 0 if runner is None else int(getattr(runner, "plant_advance_gotsc_calls", attempts))
    complete = (not reasons and reset_calls == 1 and attempts == successes == stage["horizon_steps"]
                and len(actions) == stage["horizon_steps"] and len(states) == stage["horizon_steps"] + 1)
    return {
        **{key: value for key, value in stream.items() if key not in ("targets", "actions")},
        "schema_version": SCHEMA, "passed": complete, "reasons": reasons,
        "reset_calls": reset_calls, "advance_attempts": attempts,
        "plant_advance_gotsc_calls": gotsc, "verified_plant_advances": successes,
        "states": states, "actions": actions, "attempted_actions": attempted,
        "retry_attempted": False, "wall_time_s": time.perf_counter() - started,
    }


def development_metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any],
                        streams: Sequence[dict[str, Any]]) -> dict[str, Any] | None:
    if len(rows) != stage["maximum_rollouts"] or not all(row["passed"] for row in rows):
        return None
    by_cell: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_cell.setdefault(row["cell_id"], []).append(row)
    shim = {"repeatability": stage["repeatability"], "semantic_artifacts": stage["semantic_artifacts"]}
    pair_checks = []
    for cell_id, members in sorted(by_cell.items()):
        if len(members) != stage["replays_per_cell"]:
            return None
        check = compare_rows(members[0], members[1], shim)
        pair_checks.append({"cell_id": cell_id, **check})
    baselines: dict[str, np.ndarray] = {}
    for context in (row["context_id"] for row in stage["contexts"]):
        members = [row for row in rows if row["context_id"] == context and row["cell_kind"] == "baseline"]
        values = np.asarray([[[state[key] for key in ("r_geo_m", "z_geo_m", "ip_a")]
                              for state in row["states"]] for row in members], dtype=float)
        baselines[context] = np.mean(values, axis=0)
    arm_metrics = []
    for cell_id, members in sorted(by_cell.items()):
        if members[0]["cell_kind"] == "baseline":
            continue
        context = members[0]["context_id"]
        values = np.mean(np.asarray([[[state[key] for key in ("r_geo_m", "z_geo_m", "ip_a")]
                                      for state in row["states"]] for row in members], dtype=float), axis=0)
        response = values - baselines[context]
        effect = int(members[0]["probe_issue_step"]) + 1
        window = response[effect:stage["horizon_steps"] + 1]
        norms = np.linalg.norm(window[:, :2], axis=1)
        peak_offset = int(np.argmax(norms))
        event_indices = [effect + index for index, value in enumerate(norms) if value >= 0.0003]
        arm_metrics.append({
            "cell_id": cell_id, "context_id": context,
            "direction_id": members[0]["direction_id"], "sign": members[0]["sign"],
            "probe_issue_step": members[0]["probe_issue_step"],
            "probe_duration_issues": members[0]["probe_duration_issues"],
            "effect_state_index": effect, "peak_state_index": effect + peak_offset,
            "peak_rz_response_m": window[peak_offset, :2].tolist(),
            "peak_rz_response_norm_m": float(norms[peak_offset]),
            "maximum_absolute_ip_response_a": float(np.max(np.abs(window[:, 2]))),
            "terminal_rzi_response": response[-1].tolist(),
            "response_event_state_indices_ge_0p3mm": event_indices,
            "complete_response": window.tolist(),
        })
    support = lag_support(streams, int(stage["fit_eligibility_gates"]["lag_steps"]))
    gates = stage["fit_eligibility_gates"]
    families = []
    for direction in stage["probe_directions"]:
        for sign in stage["probe_signs"]:
            members = [row for row in arm_metrics if row["direction_id"] == direction and row["sign"] == sign]
            families.append({"direction_id": direction, "sign": sign,
                             "maximum_peak_rz_response_norm_m": max(row["peak_rz_response_norm_m"] for row in members),
                             "supported": any(row["peak_rz_response_norm_m"] >= gates["minimum_peak_rz_response_m_for_family_support"] for row in members)})
    gate_passes = {
        "repeatability": all(row["passed"] for row in pair_checks),
        "action_history_support": (support["rank"] == gates["required_lag_block_rank"]
                                   and support["condition"] <= gates["maximum_lag_block_condition"]),
        "signal_and_ip": (all(row["supported"] for row in families)
                          and all(row["maximum_absolute_ip_response_a"] <= gates["maximum_each_arm_absolute_ip_response_a"] for row in arm_metrics)),
    }
    return {"replay_pair_checks": pair_checks, "lag_support": support,
            "family_support": families, "arm_metrics": arm_metrics, "gate_passes": gate_passes}


def route_for(stage: dict[str, Any], rows: Sequence[dict[str, Any]], raw_ok: bool,
              metrics: dict[str, Any] | None) -> str:
    if len(rows) != stage["maximum_rollouts"] or not all(row["passed"] for row in rows):
        return stage["routes"]["execution_or_interface_fail"]
    if not raw_ok:
        return stage["routes"]["raw_integrity_fail"]
    if metrics is None:
        return stage["routes"]["execution_or_interface_fail"]
    gates = metrics["gate_passes"]
    if not gates["repeatability"]:
        return stage["routes"]["repeatability_fail"]
    if not gates["action_history_support"]:
        return stage["routes"]["action_support_fail"]
    if not gates["signal_and_ip"]:
        return stage["routes"]["signal_or_ip_fail"]
    return stage["routes"]["pass"]


def offline(stage_path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    streams: list[dict[str, Any]] = []
    support = None
    try:
        stage, cfg, targets, id2c1_stage = load(stage_path)
        streams = campaign_streams(stage, cfg, targets, id2c1_stage)
        support = lag_support(streams, int(stage["fit_eligibility_gates"]["lag_steps"]))
        if support["rank"] != stage["fit_eligibility_gates"]["required_lag_block_rank"]:
            raise InputIntegrityError(f"lag support rank {support['rank']}")
        if support["condition"] > stage["fit_eligibility_gates"]["maximum_lag_block_condition"]:
            raise InputIntegrityError(f"lag support condition {support['condition']}")
        if any(len(row["targets"]) != stage["horizon_steps"] or len(row["actions"]) != stage["horizon_steps"] for row in streams):
            raise InputIntegrityError("stream dimensions changed")
        if sum(row["reset_calls"] if "reset_calls" in row else 1 for row in streams) != 78:
            raise InputIntegrityError("reset budget changed")
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {
        "schema_version": SCHEMA, "kind": "offline_preflight",
        "source_revision": source_revision,
        "stage_config_sha256": sha256(inside_root(stage_path, "stage config")),
        "passed": not failures, "failures": failures, "lag_support": support,
        "action_streams": [{key: value for key, value in row.items() if key != "targets"} for row in streams],
        "reset_calls": 0, "advance_attempts": 0, "plant_advance_gotsc_calls": 0,
        "verified_plant_advances": 0, "id2c2_records_read": 0,
    }


def _storage(stage: dict[str, Any], output: Path) -> dict[str, Any]:
    usage = shutil.disk_usage(output.parent)
    gate = stage["storage_gate"]
    return {"free_bytes_before_run": usage.free,
            "estimated_raw_bytes": gate["maximum_estimated_raw_bytes"],
            "estimated_free_bytes_after_run": usage.free - gate["maximum_estimated_raw_bytes"],
            "passed": (usage.free >= gate["minimum_free_bytes_before_run"]
                       and usage.free - gate["maximum_estimated_raw_bytes"] >= gate["minimum_free_bytes_after_estimate"])}


def run(stage_path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = inside_root(output, "ID2F1 output")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    stage, cfg, targets, id2c1_stage = load(stage_path)
    storage = _storage(stage, output)
    output.mkdir(parents=True)
    preflight = offline(stage_path, source_revision)
    write_new(output / "offline_preflight.json", preflight)
    if not storage["passed"] or not preflight["passed"]:
        route = stage["routes"]["storage_fail"] if not storage["passed"] else stage["routes"]["offline_or_input_fail"]
        result = {"schema_version": SCHEMA, "source_revision": source_revision,
                  "stage_config_sha256": CONFIG_SHA256, "passed": False, "route": route,
                  "reasons": preflight["failures"], "storage_gate": storage,
                  "rollouts_completed": 0, "reset_calls": 0, "advance_attempts": 0,
                  "plant_advance_gotsc_calls": 0, "verified_plant_advances": 0,
                  "model_fit_data_eligible": False, "id2c2_records_read": 0}
        write_new(output / "result.json", result)
        return result
    cfg.run_root = output / "rollouts"
    runtime_stage = dict(stage)
    runtime_stage["empirical_exploration"] = dict(stage["empirical_exploration"])
    runtime_stage["empirical_exploration"]["inner_pulse_issue_clearance"] = stage["empirical_exploration"]["inner_probe_issue_clearance"]
    streams = campaign_streams(stage, cfg, targets, id2c1_stage)
    rows: list[dict[str, Any]] = []
    for stream in streams:
        row = one_rollout(cfg, runtime_stage, stream)
        row["schema_version"] = SCHEMA
        row["source_revision"] = source_revision
        rows.append(row)
        write_new(output / f"{row['rollout_id']}.json", row)
        if not row["passed"]:
            break
    inventory = raw_inventory(output, rows, stage)
    raw_ok = not inventory["missing_required_artifacts"]
    metrics = development_metrics(rows, stage, streams)
    route = route_for(stage, rows, raw_ok, metrics)
    passed = route == stage["routes"]["pass"]
    result = {
        "schema_version": SCHEMA, "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256, "passed": passed, "route": route,
        "storage_gate": storage, "development_metrics": metrics,
        "rollouts_completed": len(rows), "unique_cells_completed": len({row["cell_id"] for row in rows}),
        "reset_calls": sum(row["reset_calls"] for row in rows),
        "advance_attempts": sum(row["advance_attempts"] for row in rows),
        "plant_advance_gotsc_calls": sum(row["plant_advance_gotsc_calls"] for row in rows),
        "verified_plant_advances": sum(row["verified_plant_advances"] for row in rows),
        **inventory, "model_fit_data_eligible": passed,
        "calibration_data_eligible": False, "blind_holdout_data_eligible": False,
        "controller_safety_data_eligible": False, "id2c2_records_read": 0,
        "claim_boundary": stage["claim_boundary"],
    }
    write_new(output / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("offline", "run"))
    parser.add_argument("--stage-config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "offline":
        result = offline(args.stage_config.resolve(), args.source_revision)
        write_new(args.output.resolve(), result)
    else:
        result = run(args.stage_config.resolve(), args.source_revision, args.output.resolve())
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
