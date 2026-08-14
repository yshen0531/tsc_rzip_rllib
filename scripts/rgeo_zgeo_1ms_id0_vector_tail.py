#!/usr/bin/env python3
"""Prospectively frozen 1 ms ID-0 source-local vector/tail campaign."""

from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import sys
import time
from typing import Any, Iterable, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_nr1_qualification import ARTIFACTS, _record, _source  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    Card15Target,
    OneMsNR1SafetyEnvelope,
    assert_exact_slew,
    build_frozen_one_ms_prefixes,
    card15_target_decimal_a,
    validate_one_ms_config,
)
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr2_spec import (  # noqa: E402
    OneMsNR2TrajectorySpec,
    build_one_ms_nr2_specs,
    build_one_ms_nr2_targets,
)
from tsc_rzip_rllib.control.rgeo_zgeo_contract import ContractError, RGeoZGeoSignal  # noqa: E402
from tsc_rzip_rllib.core.runner import TSCConfig, TSCStepRunner  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-id0-vector-tail-v1"
CONFIG_SHA256 = "668b0e4bb21166dc4d92fe4381c4177b4789b5a3139a176f7ab1b109393c31eb"
DEFAULT_STAGE = ROOT / "configs/rgeo_zgeo_1ms_id0_vector_tail.json"
OFFLINE_PASS = "ONE_MS_ID0_OFFLINE_PASS_RUN_ONLY"


class InputIntegrityError(ValueError):
    """Frozen input/config/package identity is not exact."""


class CountingRunner(TSCStepRunner):
    """Count calls entering gotsc, including a call which raises."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.plant_advance_gotsc_calls = 0

    def _run_tsc(self) -> tuple[int, str, str]:
        self.plant_advance_gotsc_calls += 1
        return super()._run_tsc()


def inside_root(path: Path, label: str) -> Path:
    result = path.resolve()
    if not result.is_relative_to(ROOT.resolve()):
        raise InputIntegrityError(f"{label} leaves repository: {path}")
    return result


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_new(path: Path, value: Any) -> None:
    path = inside_root(path, "output")
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _exact_stage(stage: dict[str, Any]) -> None:
    if stage.get("schema_version") != SCHEMA:
        raise InputIntegrityError("unexpected ID-0 schema")
    exact = {
        "takeover_time_ms": 1100,
        "control_period_ms": 1,
        "horizon_steps": 20,
        "rollouts": 20,
        "maximum_reset_calls": 20,
        "maximum_advance_attempts": 400,
        "maximum_gotsc_calls": 400,
        "maximum_verified_plant_advances": 400,
        "completed_state_count": 420,
        "completed_required_artifact_files": 2100,
        "retry_after_any_advance_attempt": "forbidden",
        "experiment_contract": "tsc_only_prospective_empirical_identification",
        "holdout_records_read": 0,
    }
    for key, value in exact.items():
        if stage.get(key) != value:
            raise InputIntegrityError(f"frozen field mismatch: {key}")
    if stage.get("semantic_artifacts") != [
        "inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv"
    ] or stage.get("diagnostic_artifacts") != ["sprsina"]:
        raise InputIntegrityError("artifact contract mismatch")
    if stage.get("calibration_use") != "forbidden" or stage.get("holdout_use") != "forbidden":
        raise InputIntegrityError("data-use contract mismatch")
    if stage.get("expert_oracle_fixture_bc_dagger_rl_use") != "forbidden":
        raise InputIntegrityError("expert-data prohibition mismatch")
    contexts = stage.get("contexts")
    if contexts != [
        {"context_id": "early", "pulse_issue_step": 2, "return_issue_step": 3,
         "repetitions_per_signed_direction": 2, "effect_window_states": [3, 20]},
        {"context_id": "late", "pulse_issue_step": 10, "return_issue_step": 11,
         "repetitions_per_signed_direction": 1, "effect_window_states": [11, 20]},
    ]:
        raise InputIntegrityError("context matrix mismatch")
    directions = stage.get("directions", [])
    if [(row.get("direction_id"), row.get("development_pair_index")) for row in directions] != [
        ("p03", 3), ("p04", 4), ("p07", 7)
    ]:
        raise InputIntegrityError("direction matrix mismatch")
    if stage.get("baseline") != {
        "candidate_id": "q0", "repetitions": 2, "target": "frozen_q0_for_all_20_issues"
    }:
        raise InputIntegrityError("baseline matrix mismatch")
    exploration = stage.get("empirical_exploration", {})
    if exploration.get("pre_action_transition_tube_claimed") is not False:
        raise InputIntegrityError("ID-0 may not claim a pre-action tube")
    if exploration.get("post_successor_step_caps") != {
        "r_geo_m": 0.002, "z_geo_m": 0.002, "ip_a": 100.0
    }:
        raise InputIntegrityError("successor cap mismatch")
    if exploration.get("inner_pulse_issue_clearance") != {
        "r_geo_m": 0.025, "z_geo_m": 0.025, "ip_fraction": 0.05
    } or exploration.get("outer_hard_envelope") != {
        "r_geo_m": 0.05, "z_geo_m": 0.05, "ip_fraction": 0.10
    }:
        raise InputIntegrityError("exploration envelope mismatch")
    gates = stage.get("scientific_gates", {})
    expected_gates = {
        "response_mean_effect_age_states": [1, 4],
        "minimum_peak_rz_response_norm_m_per_signed_arm": 0.00002,
        "minimum_rz_response_rank": 2,
        "maximum_best_pair_condition": 10.0,
        "maximum_normalized_angular_gap_deg": 170.0,
        "maximum_absolute_ip_response_a": 150.0,
        "tail_terminal_maximum_rz_norm_m": 0.00005,
        "tail_terminal_maximum_peak_fraction": 0.20,
        "tail_terminal_maximum_abs_ip_a": 10.0,
        "tail_closure_context": "early",
        "context_difference_is_reported_not_posthoc_failed": True,
    }
    if gates != expected_gates:
        raise InputIntegrityError("scientific gate mismatch")
    expected_routes = {
        "offline_fail": "ONE_MS_ID0_OFFLINE_FAIL_NO_TSC",
        "package_or_deployment_fail": "ONE_MS_ID0_PACKAGE_OR_DEPLOYMENT_FAIL_NO_TSC",
        "execution_or_interface_fail": "ONE_MS_ID0_EXECUTION_OR_INTERFACE_FAIL_STOP",
        "raw_integrity_fail": "ONE_MS_ID0_RAW_INTEGRITY_FAIL_STOP",
        "repeatability_fail": "ONE_MS_ID0_REPEATABILITY_FAIL_REDESIGN",
        "signal_or_vector_fail": "ONE_MS_ID0_SIGNAL_OR_VECTOR_GEOMETRY_FAIL_REDESIGN",
        "tail_horizon_fail": "ONE_MS_ID0_TAIL_HORIZON_INSUFFICIENT_REDESIGN",
        "pass": "ONE_MS_ID0_VECTOR_TAIL_DEVELOPMENT_PASS_NEXT_DESIGN_ONLY",
    }
    if stage.get("routes") != expected_routes:
        raise InputIntegrityError("route contract mismatch")


def load(stage_path: Path) -> tuple[dict[str, Any], TSCConfig]:
    stage_path = inside_root(stage_path, "stage config")
    if sha256(stage_path) != CONFIG_SHA256:
        raise InputIntegrityError("ID-0 config SHA-256 mismatch")
    stage = json.loads(stage_path.read_text(encoding="utf-8"))
    _exact_stage(stage)
    for label, row in stage["evidence"].items():
        if label == "base_tsc_config_sha256":
            continue
        path = inside_root(ROOT / row["path"], label)
        if not path.is_file() or sha256(path) != row["sha256"]:
            raise InputIntegrityError(f"{label} hash mismatch")
    base = inside_root(ROOT / stage["base_tsc_config"], "base config")
    if sha256(base) != stage["evidence"]["base_tsc_config_sha256"]:
        raise InputIntegrityError("base config hash mismatch")
    cfg = TSCConfig.from_json(base)
    validate_one_ms_config(
        start_folder=cfg.start_folder, dt_ms=cfg.dt_ms, slew_a_per_ms=cfg.current_slew_a_per_ms
    )
    return stage, cfg


def rollout_specs(stage: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
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
                        "context_id": context["context_id"],
                        "direction_id": direction["direction_id"], "sign": sign,
                        "repeat_index": repeat,
                        "pulse_issue_step": context["pulse_issue_step"],
                        "return_issue_step": context["return_issue_step"],
                    })
    if len(rows) != stage["rollouts"] or len({row["rollout_id"] for row in rows}) != len(rows):
        raise InputIntegrityError("rollout matrix count/identity mismatch")
    return rows


def target_from_fields(fields: Sequence[str], cfg: TSCConfig, name: str) -> Card15Target:
    exact = tuple(
        Decimal(value.strip()) * Decimal("1000") / Decimal(str(turn))
        for value, turn in zip(fields, cfg.turns_tsc)
    )
    target = Card15Target(tuple(fields), tuple(float(value) for value in exact))
    card15_target_decimal_a(target, cfg.turns_tsc, name=name)
    return target


def _reconstruct_direction_target(
    stage_row: dict[str, Any], sign_name: str, cfg: TSCConfig, source: dict[str, Any]
) -> Card15Target:
    sign = 1 if sign_name == "plus" else -1
    original = next(
        spec for spec in build_one_ms_nr2_specs()
        if spec.split == "development" and spec.pair_index == stage_row["development_pair_index"]
        and spec.sign == sign
    )
    schedule = tuple([("zero", None), ("full", 0)] + [("zero", None)] * 14)
    proxy = OneMsNR2TrajectorySpec(
        trajectory_id=f"id0_{stage_row['direction_id']}_{sign_name}",
        split="development", pair_index=stage_row["development_pair_index"], sign=sign,
        schedule_type="impulse", signed_events_tsc=original.signed_events_tsc,
        schedule=schedule,
    )
    return build_one_ms_nr2_targets(
        proxy, source_current_a_tsc=source["currents_a_tsc"], turns_tsc=cfg.turns_tsc
    )[1]


def targets_and_stream(
    stage: dict[str, Any], cfg: TSCConfig, source: dict[str, Any]
) -> tuple[dict[str, Card15Target], list[dict[str, Any]]]:
    frozen = build_frozen_one_ms_prefixes(
        source_current_a_tsc=source["currents_a_tsc"], turns_tsc=cfg.turns_tsc,
        min_current_a_tsc=cfg.min_current_a_tsc, max_current_a_tsc=cfg.max_current_a_tsc,
    )
    targets: dict[str, Card15Target] = {"q0": frozen.q0}
    for row in stage["directions"]:
        for sign in ("plus", "minus"):
            target = target_from_fields(row[f"{sign}_card15_fields"], cfg, f"id0.{row['direction_id']}.{sign}")
            rebuilt = _reconstruct_direction_target(row, sign, cfg, source)
            if target.card15_fields != rebuilt.card15_fields:
                raise InputIntegrityError(f"NR2 reconstruction mismatch: {row['direction_id']}:{sign}")
            targets[f"{row['direction_id']}:{sign}"] = target
    streams: list[dict[str, Any]] = []
    for spec in rollout_specs(stage):
        sequence = [targets["q0"]] * stage["horizon_steps"]
        if spec["pulse_issue_step"] is not None:
            sequence[spec["pulse_issue_step"]] = targets[f"{spec['direction_id']}:{spec['sign']}"]
        previous = tuple(source["active_command_decimal_a_tsc"])
        actions = []
        for issue, target in enumerate(sequence):
            exact = card15_target_decimal_a(target, cfg.turns_tsc, name=f"id0.{spec['rollout_id']}.{issue}")
            maximum = assert_exact_slew(previous, exact, name=f"id0.{spec['rollout_id']}.{issue}")
            if any(value < Decimal(str(low)) or value > Decimal(str(high))
                   for value, low, high in zip(exact, cfg.min_current_a_tsc, cfg.max_current_a_tsc)):
                raise ContractError("target leaves absolute current limits")
            actions.append({
                "issue_step": issue, "issue_time_ms": 1100 + issue,
                "effect_state_index": issue + 1, "effect_time_ms": 1101 + issue,
                "expected_card15_fields": list(target.card15_fields),
                "target_current_a_tsc": list(target.current_a_tsc),
                "maximum_issued_delta_a": maximum,
            })
            previous = exact
        streams.append({**spec, "targets": sequence, "actions": actions})
    return targets, streams


def _outer_reasons(stage: dict[str, Any], source: RGeoZGeoSignal, current: RGeoZGeoSignal) -> list[str]:
    gate = stage["empirical_exploration"]["outer_hard_envelope"]
    reasons = []
    if abs(current.boundary.r_geo_m - source.boundary.r_geo_m) > gate["r_geo_m"]:
        reasons.append("OUTER_R")
    if abs(current.boundary.z_geo_m - source.boundary.z_geo_m) > gate["z_geo_m"]:
        reasons.append("OUTER_Z")
    if source.ip_a * current.ip_a <= 0 or abs(current.ip_a - source.ip_a) > gate["ip_fraction"] * abs(source.ip_a):
        reasons.append("OUTER_IP")
    return reasons


def _pulse_clearance(stage: dict[str, Any], source: RGeoZGeoSignal, current: RGeoZGeoSignal) -> list[str]:
    gate = stage["empirical_exploration"]["inner_pulse_issue_clearance"]
    reasons = []
    if abs(current.boundary.r_geo_m - source.boundary.r_geo_m) > gate["r_geo_m"]:
        reasons.append("PULSE_CLEARANCE_R")
    if abs(current.boundary.z_geo_m - source.boundary.z_geo_m) > gate["z_geo_m"]:
        reasons.append("PULSE_CLEARANCE_Z")
    if abs(current.ip_a - source.ip_a) > gate["ip_fraction"] * abs(source.ip_a):
        reasons.append("PULSE_CLEARANCE_IP")
    return reasons


def _step_cap_reasons(stage: dict[str, Any], before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    cap = stage["empirical_exploration"]["post_successor_step_caps"]
    reasons = []
    if abs(after["r_geo_m"] - before["r_geo_m"]) > cap["r_geo_m"]:
        reasons.append("EMPIRICAL_STEP_R")
    if abs(after["z_geo_m"] - before["z_geo_m"]) > cap["z_geo_m"]:
        reasons.append("EMPIRICAL_STEP_Z")
    if abs(after["ip_a"] - before["ip_a"]) > cap["ip_a"]:
        reasons.append("EMPIRICAL_STEP_IP")
    return reasons


def offline(stage_path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    stage = source_signal = streams = None
    try:
        stage, cfg = load(stage_path)
        source = _source(cfg)
        source_signal = RGeoZGeoSignal.from_tsc_state(source)
        envelope = OneMsNR1SafetyEnvelope.from_signal(source_signal)
        failures.extend(envelope.state_reasons(
            source_signal, source["currents_a_tsc"], cfg.min_current_a_tsc, cfg.max_current_a_tsc
        ))
        _, raw_streams = targets_and_stream(stage, cfg, source)
        streams = [{k: v for k, v in row.items() if k != "targets"} for row in raw_streams]
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    failures = list(dict.fromkeys(failures))
    return {
        "schema_version": SCHEMA, "kind": "offline_preflight", "source_revision": source_revision,
        "stage_config_sha256": sha256(inside_root(stage_path, "stage config")),
        "passed": not failures, "route": OFFLINE_PASS if not failures else (
            stage["routes"]["offline_fail"] if stage else "ONE_MS_ID0_OFFLINE_FAIL_NO_TSC"
        ), "failures": failures, "source_signal": None if source_signal is None else source_signal.to_dict(),
        "rollout_action_streams": streams, "reset_calls": 0, "advance_attempts": 0,
        "plant_advance_gotsc_calls": 0, "verified_plant_advances": 0,
    }


def _action(action: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in action.items()}


def _validate_record(record: dict[str, Any], label: str) -> None:
    if len(record.get("actual_current_decimal_a_tsc", ())) != 14:
        raise ContractError(f"{label} coil-current vector is not length 14")
    if len(record.get("active_command_card15_fields", ())) != 14:
        raise ContractError(f"{label} active command is not length 14")
    if len(record.get("wire_current_a", ())) != 48:
        raise ContractError(f"{label} wire-current vector is not length 48")
    if set(record.get("artifact_sha256", ())) != set(ARTIFACTS):
        raise ContractError(f"{label} artifact hash set is incomplete")


def one_rollout(
    cfg: TSCConfig, stage: dict[str, Any], stream: dict[str, Any], *, runner_cls: type[TSCStepRunner] = CountingRunner
) -> dict[str, Any]:
    runner: TSCStepRunner | None = None
    states: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    attempted: list[dict[str, Any]] = []
    reasons: list[str] = []
    reset_calls = attempts = successes = 0
    started = time.perf_counter()
    try:
        runner = runner_cls(cfg, worker_id=f"id0_{stream['rollout_id']}", keep_workspace=False)
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
            reasons.extend(envelope.state_reasons(
                signal, state["currents_a_tsc"], cfg.min_current_a_tsc, cfg.max_current_a_tsc
            ))
            reasons.extend(_outer_reasons(stage, source_signal, signal))
            if issue == stream["pulse_issue_step"]:
                reasons.extend(_pulse_clearance(stage, source_signal, signal))
            target_exact = card15_target_decimal_a(target, cfg.turns_tsc, name=f"id0.run.{stream['rollout_id']}.{issue}")
            try:
                maximum = assert_exact_slew(
                    states[-1]["active_command_decimal_a_tsc"], target_exact,
                    name=f"id0.issue.{stream['rollout_id']}.{issue}",
                )
                if any(value < Decimal(str(low)) or value > Decimal(str(high))
                       for value, low, high in zip(target_exact, cfg.min_current_a_tsc, cfg.max_current_a_tsc)):
                    raise ContractError("target leaves absolute current limits")
            except Exception as exc:
                reasons.append(f"ISSUED_ACTION:{issue}:{type(exc).__name__}:{exc}")
                break
            if reasons:
                break
            action = _action(frozen_action)
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
            if record["time_ms"] == 1101 + issue:
                states.append(record)
            else:
                reasons.append(f"TIME:{issue}:{record['time_ms']}")
                break
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
                    name=f"id0.observed.{stream['rollout_id']}.{issue}",
                )
            except Exception as exc:
                reasons.append(f"OBSERVED_SLEW:{issue}:{type(exc).__name__}:{exc}")
            successor_signal = RGeoZGeoSignal.from_tsc_state(successor)
            reasons.extend(envelope.state_reasons(
                successor_signal, successor["currents_a_tsc"], cfg.min_current_a_tsc, cfg.max_current_a_tsc
            ))
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
    complete = (
        not reasons and reset_calls == 1 and attempts == successes == stage["horizon_steps"]
        and len(actions) == stage["horizon_steps"] and len(states) == stage["horizon_steps"] + 1
    )
    return {
        **{k: v for k, v in stream.items() if k not in ("targets", "actions")},
        "schema_version": SCHEMA, "passed": complete, "reasons": reasons,
        "reset_calls": reset_calls, "advance_attempts": attempts,
        "plant_advance_gotsc_calls": gotsc, "verified_plant_advances": successes,
        "states": states, "actions": actions, "attempted_actions": attempted,
        "retry_attempted": False, "wall_time_s": time.perf_counter() - started,
    }


def compare_rows(left: dict[str, Any], right: dict[str, Any], stage: dict[str, Any]) -> dict[str, Any]:
    maxima = {"geometry_m": 0.0, "ip_a": 0.0, "coil_a": 0.0, "wire_a": 0.0}
    failures: list[str] = []
    if left["actions"] != right["actions"]:
        failures.append("ACTION_STREAM")
    if len(left["states"]) != len(right["states"]):
        failures.append("STATE_COUNT")
    for index, (a, b) in enumerate(zip(left["states"], right["states"])):
        if a["time_ms"] != b["time_ms"]:
            failures.append(f"TIME:{index}")
        maxima["geometry_m"] = max(maxima["geometry_m"], *(abs(a[k] - b[k]) for k in ("r_geo_m", "z_geo_m", "r_mid_m")))
        maxima["ip_a"] = max(maxima["ip_a"], abs(a["ip_a"] - b["ip_a"]))
        if len(a["actual_current_decimal_a_tsc"]) != 14 or len(b["actual_current_decimal_a_tsc"]) != 14:
            failures.append(f"COIL_COUNT:{index}")
        else:
            maxima["coil_a"] = max(maxima["coil_a"], max(abs(float(x) - float(y)) for x, y in zip(a["actual_current_decimal_a_tsc"], b["actual_current_decimal_a_tsc"])))
        if len(a["wire_current_a"]) != 48 or len(b["wire_current_a"]) != 48:
            failures.append(f"WIRE_COUNT:{index}")
        else:
            maxima["wire_a"] = max(maxima["wire_a"], max(abs(x - y) for x, y in zip(a["wire_current_a"], b["wire_current_a"])))
        for name in stage["semantic_artifacts"]:
            if a["artifact_sha256"].get(name) != b["artifact_sha256"].get(name):
                failures.append(f"SEMANTIC_ARTIFACT:{index}:{name}")
    for key, value in maxima.items():
        if value > stage["repeatability"][key]:
            failures.append(key.upper())
    return {"passed": not failures, "failures": list(dict.fromkeys(failures)), "maximum_absolute_difference": maxima}


def _matched_baseline(rows: Sequence[dict[str, Any]]) -> list[dict[str, float]]:
    baselines = [row for row in rows if row["context_id"] == "baseline"]
    if len(baselines) != 2:
        raise ValueError("two complete baselines required")
    return [{key: float(np.mean([row["states"][index][key] for row in baselines]))
             for key in ("r_geo_m", "z_geo_m", "ip_a")}
            for index in range(len(baselines[0]["states"]))]


def _response(row: dict[str, Any], baseline: Sequence[dict[str, float]]) -> list[list[float]]:
    return [[state["r_geo_m"] - base["r_geo_m"], state["z_geo_m"] - base["z_geo_m"],
             state["ip_a"] - base["ip_a"]] for state, base in zip(row["states"], baseline)]


def _angular_gap(vectors: np.ndarray) -> float:
    angles = sorted((math.degrees(math.atan2(float(v[1]), float(v[0]))) % 360.0) for v in vectors)
    return max(b - a for a, b in zip(angles, angles[1:] + [angles[0] + 360.0]))


def scientific_metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    baseline = _matched_baseline(rows)
    arms = [row for row in rows if row["context_id"] != "baseline"]
    arm_metrics: list[dict[str, Any]] = []
    for row in arms:
        response = np.asarray(_response(row, baseline), dtype=float)
        effect = int(row["pulse_issue_step"]) + 1
        window = response[effect:]
        rz_norm = np.linalg.norm(window[:, :2], axis=1)
        mean = np.mean(response[effect:effect + 4], axis=0)
        arm_metrics.append({
            "rollout_id": row["rollout_id"], "context_id": row["context_id"],
            "direction_id": row["direction_id"], "sign": row["sign"],
            "repeat_index": row["repeat_index"], "effect_state_index": effect,
            "mean_effect_age_1_4": mean.tolist(), "peak_rz_norm_m": float(np.max(rz_norm)),
            "maximum_absolute_ip_response_a": float(np.max(np.abs(window[:, 2]))),
            "terminal_rz_norm_m": float(rz_norm[-1]),
            "terminal_absolute_ip_response_a": float(abs(window[-1, 2])),
            "terminal_peak_fraction": float(rz_norm[-1] / np.max(rz_norm)) if np.max(rz_norm) else math.inf,
        })
    early_vectors = []
    early_keys = []
    for direction in ("p03", "p04", "p07"):
        for sign in ("plus", "minus"):
            selected = [row for row in arm_metrics if row["context_id"] == "early" and row["direction_id"] == direction and row["sign"] == sign]
            early_vectors.append(np.mean([row["mean_effect_age_1_4"][:2] for row in selected], axis=0))
            early_keys.append(f"{direction}:{sign}")
    matrix = np.asarray(early_vectors, dtype=float).T
    rank = int(np.linalg.matrix_rank(matrix))
    pair_conditions = []
    for left in range(6):
        for right in range(left + 1, 6):
            pair = matrix[:, [left, right]]
            condition = float(np.linalg.cond(pair)) if np.linalg.matrix_rank(pair) == 2 else math.inf
            pair_conditions.append({"columns": [early_keys[left], early_keys[right]], "condition": condition})
    best = min(pair_conditions, key=lambda row: row["condition"])
    gap = _angular_gap(np.asarray(early_vectors))
    context_difference = []
    for direction in ("p03", "p04", "p07"):
        for sign in ("plus", "minus"):
            early = np.mean([row["mean_effect_age_1_4"] for row in arm_metrics if row["context_id"] == "early" and row["direction_id"] == direction and row["sign"] == sign], axis=0)
            late = np.mean([row["mean_effect_age_1_4"] for row in arm_metrics if row["context_id"] == "late" and row["direction_id"] == direction and row["sign"] == sign], axis=0)
            context_difference.append({"arm": f"{direction}:{sign}", "early": early.tolist(), "late": late.tolist(), "late_minus_early": (late - early).tolist()})
    gates = stage["scientific_gates"]
    signal_passed = all(row["peak_rz_norm_m"] >= gates["minimum_peak_rz_response_norm_m_per_signed_arm"] for row in arm_metrics)
    ip_passed = all(row["maximum_absolute_ip_response_a"] <= gates["maximum_absolute_ip_response_a"] for row in arm_metrics)
    vector_passed = rank >= gates["minimum_rz_response_rank"] and best["condition"] <= gates["maximum_best_pair_condition"] and gap <= gates["maximum_normalized_angular_gap_deg"]
    early = [row for row in arm_metrics if row["context_id"] == "early"]
    tail_passed = all(
        row["terminal_rz_norm_m"] <= gates["tail_terminal_maximum_rz_norm_m"]
        and row["terminal_peak_fraction"] <= gates["tail_terminal_maximum_peak_fraction"]
        and row["terminal_absolute_ip_response_a"] <= gates["tail_terminal_maximum_abs_ip_a"]
        for row in early
    )
    return {
        "arm_metrics": arm_metrics, "early_vector_keys": early_keys,
        "early_mean_rz_response_matrix_m": matrix.tolist(), "rz_response_rank": rank,
        "pair_conditions": pair_conditions, "best_pair": best,
        "maximum_normalized_angular_gap_deg": gap, "context_differences": context_difference,
        "signal_passed": signal_passed, "ip_passed": ip_passed,
        "vector_geometry_passed": vector_passed, "tail_passed": tail_passed,
    }


def raw_inventory(output: Path, rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    names = tuple(stage["semantic_artifacts"]) + tuple(stage["diagnostic_artifacts"])
    lines: list[str] = []
    missing: list[str] = []
    total = 0
    for row in rows:
        for state in row["states"]:
            folder = output / "rollouts" / row["rollout_id"] / f"{state['time_ms']}ms"
            for name in names:
                path = folder / name
                label = path.relative_to(output).as_posix()
                if not path.is_file():
                    missing.append(label)
                    continue
                size = path.stat().st_size
                total += size
                lines.append(f"{label}\t{size}\t{sha256(path)}")
    payload = "".join(f"{line}\n" for line in sorted(lines)).encode()
    return {"required_artifact_files": len(lines), "required_artifact_bytes": total,
            "required_artifact_inventory_sha256": hashlib.sha256(payload).hexdigest(),
            "missing_required_artifacts": missing}


def route_for(stage: dict[str, Any], execution: bool, raw_ok: bool, repeatable: bool,
              metrics: dict[str, Any] | None) -> str:
    if not execution:
        return stage["routes"]["execution_or_interface_fail"]
    if not raw_ok:
        return stage["routes"]["raw_integrity_fail"]
    if not repeatable:
        return stage["routes"]["repeatability_fail"]
    assert metrics is not None
    if not (metrics["signal_passed"] and metrics["ip_passed"] and metrics["vector_geometry_passed"]):
        return stage["routes"]["signal_or_vector_fail"]
    if not metrics["tail_passed"]:
        return stage["routes"]["tail_horizon_fail"]
    return stage["routes"]["pass"]


def run(stage_path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = inside_root(output, "run output")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    output.mkdir(parents=True)
    gate = offline(stage_path, source_revision)
    write_new(output / "offline_preflight.json", gate)
    if not gate["passed"]:
        result = {"schema_version": SCHEMA, "source_revision": source_revision, "passed": False,
                  "route": gate["route"], "reasons": gate["failures"], "rollouts_completed": 0,
                  "reset_calls": 0, "advance_attempts": 0, "plant_advance_gotsc_calls": 0,
                  "verified_plant_advances": 0}
        write_new(output / "result.json", result)
        return result
    stage, cfg = load(stage_path)
    if gate["stage_config_sha256"] != sha256(inside_root(stage_path, "stage config")):
        raise InputIntegrityError("stage changed after offline preflight")
    cfg.run_root = output / "rollouts"
    source = _source(cfg)
    _, streams = targets_and_stream(stage, cfg, source)
    rows = []
    for stream in streams:
        row = one_rollout(cfg, stage, stream)
        row["source_revision"] = source_revision
        rows.append(row)
        write_new(output / f"{row['rollout_id']}.json", row)
        if not row["passed"]:
            break
    execution = len(rows) == stage["rollouts"] and all(row["passed"] for row in rows)
    inventory = raw_inventory(output, rows, stage)
    raw_ok = execution and not inventory["missing_required_artifacts"] and inventory["required_artifact_files"] == stage["completed_required_artifact_files"]
    comparisons = []
    if execution:
        comparisons.append({"pair_id": "baseline_q0", **compare_rows(rows[0], rows[1], stage)})
        for direction in ("p03", "p04", "p07"):
            for sign in ("plus", "minus"):
                selected = [row for row in rows if row["context_id"] == "early" and row["direction_id"] == direction and row["sign"] == sign]
                comparisons.append({"pair_id": f"early_{direction}_{sign}", **compare_rows(selected[0], selected[1], stage)})
    repeatable = execution and all(row["passed"] for row in comparisons)
    metrics = scientific_metrics(rows, stage) if repeatable else None
    route = route_for(stage, execution, raw_ok, repeatable, metrics)
    passed = route == stage["routes"]["pass"]
    result = {
        "schema_version": SCHEMA, "source_revision": source_revision, "passed": passed,
        "route": route, "execution_passed": execution, "raw_integrity_passed": raw_ok,
        "repeatability_passed": repeatable, "scientific_metrics": metrics,
        "repeatability_comparisons": comparisons, "rollouts_completed": len(rows),
        "reset_calls": sum(row["reset_calls"] for row in rows),
        "advance_attempts": sum(row["advance_attempts"] for row in rows),
        "plant_advance_gotsc_calls": sum(row["plant_advance_gotsc_calls"] for row in rows),
        "verified_plant_advances": sum(row["verified_plant_advances"] for row in rows),
        **inventory,
        "claim_boundary": "source_local_tsc_identification_development_only_not_controller_safety_or_recourse",
    }
    write_new(output / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("offline", "run"))
    parser.add_argument("--stage-config", type=Path, default=DEFAULT_STAGE)
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
