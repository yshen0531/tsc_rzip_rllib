#!/usr/bin/env python3
"""Frozen NR2R2C2aA1 level-2 cumulative authority discriminator."""

from __future__ import annotations

import argparse
from decimal import Decimal
import json
from pathlib import Path
import sys
import time
from typing import Any, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_nr1_qualification import _record, _source  # noqa: E402
from scripts.rgeo_zgeo_1ms_nr2r2c1a_source_replay import compare_pair  # noqa: E402
from scripts.rgeo_zgeo_1ms_nr2r2c2a_search import (  # noqa: E402
    _outer_reasons, _preissue_reasons, final_inventory, sha256, write_new,
)
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    Card15Target, OneMsNR1SafetyEnvelope, assert_exact_slew,
    build_frozen_one_ms_prefixes, card15_target_decimal_a,
    decimal_single_turn_currents_a, validate_one_ms_config,
)
from tsc_rzip_rllib.control.rgeo_zgeo_contract import ContractError, RGeoZGeoSignal  # noqa: E402
from tsc_rzip_rllib.core.runner import TSCConfig, TSCStepRunner  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-nr2r2c2aa1-level2-authority-v1"
PASS_ROUTE = "ONE_MS_NR2R2C2AA1_LEVEL2_AUTHORITY_PASS_TIME_VARYING_C2A_DESIGN_ONLY"
FAIL_ROUTE = "ONE_MS_NR2R2C2AA1_LEVEL2_AUTHORITY_FAIL_REDESIGN"


def load(stage_path: Path) -> tuple[dict[str, Any], TSCConfig]:
    stage = json.loads(stage_path.read_text(encoding="utf-8"))
    if stage.get("schema_version") != SCHEMA:
        raise ValueError("unexpected C2aA1 schema")
    if stage["rollouts"] * stage["horizon_steps"] != stage["maximum_plant_advances"] or stage["maximum_plant_advances"] != 64:
        raise ValueError("C2aA1 plant budget mismatch")
    if stage["support_evidence"]["holdout_records_read"] != 0:
        raise ValueError("C2aA1 may not read the invalid holdout")
    covered = [step for row in stage["schedule"] for step in range(row["first_step"], row["last_step"] + 1)]
    if covered != list(range(stage["horizon_steps"])):
        raise ValueError("C2aA1 schedule does not cover each step exactly once")
    cfg = TSCConfig.from_json(ROOT / stage["base_tsc_config"])
    validate_one_ms_config(start_folder=cfg.start_folder, dt_ms=cfg.dt_ms,
                           slew_a_per_ms=cfg.current_slew_a_per_ms)
    return stage, cfg


def target_from_fields(fields: Sequence[str], cfg: TSCConfig, name: str) -> Card15Target:
    values = tuple(fields)
    exact = decimal_single_turn_currents_a(tuple(value.strip() for value in values), cfg.turns_tsc, name=name)
    return Card15Target(values, tuple(float(value) for value in exact))


def targets_for(stage: dict[str, Any], q0: Card15Target, level1: Card15Target,
                level2: Card15Target) -> tuple[Card15Target, ...]:
    levels = {"q0": q0, "level1": level1, "level2": level2}
    targets: list[Card15Target | None] = [None] * stage["horizon_steps"]
    for row in stage["schedule"]:
        for step in range(row["first_step"], row["last_step"] + 1):
            targets[step] = levels[row["level"]]
    if any(target is None for target in targets):
        raise ContractError("C2aA1 target schedule is incomplete")
    return tuple(target for target in targets if target is not None)


def authority_metrics(states: Sequence[dict[str, Any]], q0_states: Sequence[dict[str, Any]],
                      stage: dict[str, Any]) -> dict[str, Any]:
    first, last = stage["authority_window_start_state"], stage["authority_window_end_state"]
    opposition = np.asarray([
        (states[index]["r_geo_m"] - q0_states[index]["r_geo_m"])
        - (states[index]["z_geo_m"] - q0_states[index]["z_geo_m"])
        for index in range(first, last + 1)
    ], dtype=float)
    ip = np.asarray([states[index]["ip_a"] - q0_states[index]["ip_a"]
                     for index in range(first, last + 1)], dtype=float)
    values = {
        "window_states": list(range(first, last + 1)),
        "opposition_m": opposition.tolist(),
        "mean_opposition_m": float(np.mean(opposition)),
        "positive_opposition_fraction": float(np.mean(opposition > 0.0)),
        "maximum_opposition_m": float(np.max(opposition)),
        "maximum_absolute_ip_deviation_from_q0_a": float(np.max(np.abs(ip))),
    }
    values["passed"] = (
        values["mean_opposition_m"] >= stage["minimum_mean_opposition_m"]
        and values["positive_opposition_fraction"] >= stage["minimum_positive_opposition_fraction"]
        and values["maximum_opposition_m"] >= stage["minimum_maximum_opposition_m"]
        and values["maximum_absolute_ip_deviation_from_q0_a"] <= stage["maximum_absolute_ip_deviation_from_q0_a"]
    )
    return values


def offline(stage_path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    stage = signal = frozen = None
    stream = []
    try:
        stage, cfg = load(stage_path)
        for key in ("q0_comparator", "level1_comparator"):
            if sha256(ROOT / stage[key]["path"]) != stage[key]["sha256"]:
                raise ValueError(f"{key} hash mismatch")
        level1_record = json.loads((ROOT / stage["level1_comparator"]["path"]).read_text(encoding="utf-8"))
        if level1_record["actions"][1]["expected_card15_fields"] != stage["level1_card15_fields"]:
            raise ValueError("level1 fields do not reproduce the tracked p07 action")
        source = _source(cfg)
        signal = RGeoZGeoSignal.from_tsc_state(source)
        envelope = OneMsNR1SafetyEnvelope.from_signal(signal)
        failures.extend(envelope.state_reasons(signal, source["currents_a_tsc"],
                                                cfg.min_current_a_tsc, cfg.max_current_a_tsc))
        frozen = build_frozen_one_ms_prefixes(
            source_current_a_tsc=source["currents_a_tsc"], turns_tsc=cfg.turns_tsc,
            min_current_a_tsc=cfg.min_current_a_tsc, max_current_a_tsc=cfg.max_current_a_tsc)
        level1 = target_from_fields(stage["level1_card15_fields"], cfg, "c2aa1.level1")
        level2 = target_from_fields(stage["level2_card15_fields"], cfg, "c2aa1.level2")
        targets = targets_for(stage, frozen.q0, level1, level2)
        q0_exact = card15_target_decimal_a(frozen.q0, cfg.turns_tsc, name="c2aa1.q0")
        level1_exact = card15_target_decimal_a(level1, cfg.turns_tsc, name="c2aa1.level1")
        level2_exact = card15_target_decimal_a(level2, cfg.turns_tsc, name="c2aa1.level2")
        if max(abs(left - right) for left, right in zip(q0_exact, level2_exact)) > Decimal("0.3"):
            raise ContractError("level2 leaves the componentwise q0 +/- 0.3 A domain")
        if any(level2_value - q0_value != Decimal(2) * (level1_value - q0_value)
               for q0_value, level1_value, level2_value
               in zip(q0_exact, level1_exact, level2_exact)):
            raise ContractError("level2 is not exactly twice the level1 q0-relative offset")
        observed = stage["support_evidence"]["maximum_observed_axis_step_m"]
        bound = stage["support_evidence"]["prospective_successor_bound"]
        if not (bound["r_geo_m"] > observed["r_geo"]
                and bound["z_geo_m"] > observed["z_geo"]
                and bound["ip_a"] > stage["support_evidence"]["maximum_observed_ip_step_a"]):
            raise ValueError("prospective successor bound does not exceed prior evidence")
        previous = source["active_command_decimal_a_tsc"]
        for step, target in enumerate(targets):
            exact = card15_target_decimal_a(target, cfg.turns_tsc, name=f"c2aa1.offline.{step}")
            maximum = assert_exact_slew(previous, exact, name=f"c2aa1.offline.{step}")
            stream.append({"step": step, "level": next(row["level"] for row in stage["schedule"]
                                                         if row["first_step"] <= step <= row["last_step"]),
                           "card15_fields": list(target.card15_fields), "maximum_issued_delta_a": maximum})
            previous = exact
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {"schema_version": SCHEMA, "kind": "offline_preflight", "source_revision": source_revision,
            "passed": not failures,
            "route": "ONE_MS_NR2R2C2AA1_OFFLINE_PASS" if not failures else "ONE_MS_NR2R2C2AA1_OFFLINE_FAIL_NO_TSC",
            "failures": failures, "stage": stage,
            "source_signal": None if signal is None else signal.to_dict(),
            "frozen_prefixes": None if frozen is None else frozen.to_dict(),
            "action_stream": stream, "new_tsc_or_plant_advances": 0}


def one_rollout(cfg: TSCConfig, stage: dict[str, Any], rollout_id: str,
                targets: Sequence[Card15Target], q0_states: Sequence[dict[str, Any]]) -> dict[str, Any]:
    runner = TSCStepRunner(cfg, worker_id=f"c2aa1_{rollout_id}", keep_workspace=False)
    reasons: list[str] = []
    states: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    advance_times: list[float] = []
    started = time.perf_counter()
    try:
        state = runner.reset(episode_name=rollout_id)
        source_signal = RGeoZGeoSignal.from_tsc_state(state)
        envelope = OneMsNR1SafetyEnvelope.from_signal(source_signal)
        states.append(_record(cfg, state))
        for step, target in enumerate(targets):
            current_signal = RGeoZGeoSignal.from_tsc_state(state)
            reasons.extend(envelope.state_reasons(current_signal, state["currents_a_tsc"],
                                                   cfg.min_current_a_tsc, cfg.max_current_a_tsc))
            reasons.extend(_preissue_reasons(stage, source_signal, current_signal))
            try:
                exact = card15_target_decimal_a(target, cfg.turns_tsc, name=f"{rollout_id}.{step}")
                maximum = assert_exact_slew(states[-1]["active_command_decimal_a_tsc"], exact,
                                            name=f"{rollout_id}.issue.{step}")
            except ContractError as exc:
                reasons.append(f"ISSUED_SLEW:{exc}")
                break
            if reasons:
                break
            action = {"issue_step": step, "issue_time_ms": int(state["time_ms"]),
                      "expected_card15_fields": list(target.card15_fields),
                      "target_current_a_tsc": list(target.current_a_tsc),
                      "maximum_issued_delta_a": maximum,
                      "effect_state_index": step + 1, "effect_age_steps": 1}
            advanced = time.perf_counter()
            state = runner.step_current_a(np.asarray(target.current_a_tsc, dtype=float))
            advance_times.append(time.perf_counter() - advanced)
            actions.append(action)
            if int(state.get("returncode", 0)) != 0:
                reasons.append(f"TSC_RETURNCODE:{state.get('returncode')}")
            if bool(state.get("abnormal", False)):
                reasons.append(f"TSC_ABNORMAL:{state.get('done_reason', '')}")
            record = _record(cfg, state)
            states.append(record)
            if record["time_ms"] != 1101 + step:
                reasons.append(f"TIME:{step}")
            if tuple(record["active_command_card15_fields"]) != target.card15_fields:
                reasons.append(f"CARD15:{step}")
            try:
                record["maximum_observed_delta_a"] = assert_exact_slew(
                    states[-2]["actual_current_decimal_a_tsc"], record["actual_current_decimal_a_tsc"],
                    name=f"{rollout_id}.observed.{step}")
            except ContractError as exc:
                reasons.append(f"OBSERVED_SLEW:{exc}")
            successor = RGeoZGeoSignal.from_tsc_state(state)
            reasons.extend(envelope.state_reasons(successor, state["currents_a_tsc"],
                                                   cfg.min_current_a_tsc, cfg.max_current_a_tsc))
            reasons.extend(_outer_reasons(stage, source_signal, successor))
            bound = stage["support_evidence"]["prospective_successor_bound"]
            if abs(states[-1]["r_geo_m"] - states[-2]["r_geo_m"]) > bound["r_geo_m"]:
                reasons.append(f"SUPPORT_BOUND_R:{step}")
            if abs(states[-1]["z_geo_m"] - states[-2]["z_geo_m"]) > bound["z_geo_m"]:
                reasons.append(f"SUPPORT_BOUND_Z:{step}")
            if abs(states[-1]["ip_a"] - states[-2]["ip_a"]) > bound["ip_a"]:
                reasons.append(f"SUPPORT_BOUND_IP:{step}")
            if reasons:
                break
    except Exception as exc:
        reasons.append(f"EXECUTION:{type(exc).__name__}:{exc}")
    finally:
        runner.cleanup_runtime_workspace()
    reasons = list(dict.fromkeys(reasons))
    complete = not reasons and len(actions) == 32 and len(states) == 33
    return {"rollout_id": rollout_id, "candidate_id": rollout_id,
            "pair_id": "level2_authority", "passed": complete,
            "reasons": reasons, "plant_advances": len(actions), "states": states, "actions": actions,
            "authority_metrics": authority_metrics(states, q0_states, stage) if complete else None,
            "advance_wall_time_s": advance_times, "wall_time_s": time.perf_counter() - started}


def run(stage_path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    gate = offline(stage_path, source_revision)
    if not gate["passed"]:
        raise RuntimeError("offline gate failed; TSC forbidden")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    output.mkdir(parents=True)
    write_new(output / "offline_preflight.json", gate)
    stage, cfg = load(stage_path)
    cfg.run_root = output / "rollouts"
    q0_record = json.loads((ROOT / stage["q0_comparator"]["path"]).read_text(encoding="utf-8"))
    source = _source(cfg)
    frozen = build_frozen_one_ms_prefixes(
        source_current_a_tsc=source["currents_a_tsc"], turns_tsc=cfg.turns_tsc,
        min_current_a_tsc=cfg.min_current_a_tsc, max_current_a_tsc=cfg.max_current_a_tsc)
    level1 = target_from_fields(stage["level1_card15_fields"], cfg, "c2aa1.level1")
    level2 = target_from_fields(stage["level2_card15_fields"], cfg, "c2aa1.level2")
    targets = targets_for(stage, frozen.q0, level1, level2)
    rows = []
    for index in range(stage["rollouts"]):
        row = one_rollout(cfg, stage, f"level2_authority_r{index}", targets, q0_record["states"])
        rows.append(row)
        write_new(output / f"level2_authority_r{index}.json", row)
        if not row["passed"]:
            break
    execution = len(rows) == 2 and all(row["passed"] for row in rows)
    pair = compare_pair(rows[0], rows[1], stage) if execution else None
    repeatable = execution and pair is not None and pair["passed"]
    authority = repeatable and all(row["authority_metrics"]["passed"] for row in rows)
    support_failure = any(reason.startswith("SUPPORT_BOUND_") for row in rows for reason in row["reasons"])
    route = ("ONE_MS_NR2R2C2AA1_EXECUTION_FAIL_STOP" if not execution or support_failure else
             "ONE_MS_NR2R2C2AA1_REPEATABILITY_FAIL_STOP" if not repeatable else
             PASS_ROUTE if authority else FAIL_ROUTE)
    inventory = final_inventory(output, rows, stage)
    result = {"schema_version": SCHEMA, "source_revision": source_revision,
              "passed": authority, "execution_passed": execution, "repeatability_passed": repeatable,
              "route": route, "rollouts_completed": len(rows),
              "plant_advances": sum(row["plant_advances"] for row in rows),
              "pair_comparison": pair,
              "authority_metrics": [row["authority_metrics"] for row in rows if row["authority_metrics"]],
              "worst_rollout_wall_time_s": max((row["wall_time_s"] for row in rows), default=None),
              "total_rollout_wall_time_s": sum(row["wall_time_s"] for row in rows),
              **inventory,
              "claim_boundary": "level2_development_authority_only_not_hold_recovery_model_or_control"}
    write_new(output / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("offline", "run"))
    parser.add_argument("--stage-config", type=Path, default=ROOT / "configs/rgeo_zgeo_1ms_nr2r2c2aa1_level2_authority.json")
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = (offline(args.stage_config.resolve(), args.source_revision) if args.mode == "offline"
              else run(args.stage_config.resolve(), args.source_revision, args.output.resolve()))
    if args.mode == "offline":
        write_new(args.output.resolve(), result)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
