#!/usr/bin/env python3
"""Prospectively frozen NR2R2C2a canonical-source nominal-hold search."""

from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
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
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    Card15Target, OneMsNR1SafetyEnvelope, assert_exact_slew,
    build_frozen_one_ms_prefixes, card15_target_decimal_a,
    decimal_single_turn_currents_a, validate_one_ms_config,
)
from tsc_rzip_rllib.control.rgeo_zgeo_contract import ContractError, RGeoZGeoSignal  # noqa: E402
from tsc_rzip_rllib.core.runner import TSCConfig, TSCStepRunner  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-nr2r2c2a-nominal-hold-search-v1"
PASS_ROUTE = "ONE_MS_NR2R2C2A_SEARCH_CANDIDATE_FOUND_VALIDATION_DESIGN_ONLY"
NO_CANDIDATE_ROUTE = "ONE_MS_NR2R2C2A_SEARCH_NO_NOMINAL_HOLD_CANDIDATE_REDESIGN"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path: Path, value: Any) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def load(stage_path: Path) -> tuple[dict[str, Any], TSCConfig]:
    stage = json.loads(stage_path.read_text(encoding="utf-8"))
    if stage.get("schema_version") != SCHEMA:
        raise ValueError("unexpected C2a search schema")
    if len(stage.get("candidates", ())) != 2:
        raise ValueError("C2a search requires exactly two frozen candidates")
    if (stage["maximum_plant_advances"] != len(stage["candidates"]) * stage["horizon_steps"]
            or stage["maximum_plant_advances"] != 64):
        raise ValueError("C2a search plant budget mismatch")
    if stage["support_evidence"]["holdout_records_read"] != 0:
        raise ValueError("C2a search may not read the invalid NR2R1 holdout")
    cfg = TSCConfig.from_json(ROOT / stage["base_tsc_config"])
    validate_one_ms_config(start_folder=cfg.start_folder, dt_ms=cfg.dt_ms,
                           slew_a_per_ms=cfg.current_slew_a_per_ms)
    return stage, cfg


def candidate_target(spec: dict[str, Any], cfg: TSCConfig) -> Card15Target:
    fields = tuple(spec["card15_fields"])
    exact = decimal_single_turn_currents_a(
        tuple(value.strip() for value in fields), cfg.turns_tsc,
        name=f"c2a.{spec['candidate_id']}",
    )
    return Card15Target(fields, tuple(float(value) for value in exact))


def action_stream(stage: dict[str, Any], q0: Card15Target, target: Card15Target) -> tuple[Card15Target, ...]:
    return (q0,) + (target,) * (stage["horizon_steps"] - 1)


def hold_metrics(states: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    source = states[0]
    first, last = stage["terminal_window_start_state"], stage["terminal_window_end_state"]
    terminal = states[first:last + 1]
    r = np.asarray([state["r_geo_m"] for state in terminal], dtype=float)
    z = np.asarray([state["z_geo_m"] for state in terminal], dtype=float)
    all_r = np.asarray([state["r_geo_m"] - source["r_geo_m"] for state in states], dtype=float)
    all_z = np.asarray([state["z_geo_m"] - source["z_geo_m"] for state in states], dtype=float)
    all_ip = np.asarray([state["ip_a"] - source["ip_a"] for state in states], dtype=float)
    values = {
        "maximum_absolute_r_from_source_m": float(np.max(np.abs(all_r))),
        "maximum_absolute_z_from_source_m": float(np.max(np.abs(all_z))),
        "maximum_absolute_ip_from_source_a": float(np.max(np.abs(all_ip))),
        "terminal_maximum_source_axis_displacement_m": float(max(
            np.max(np.abs(r - source["r_geo_m"])), np.max(np.abs(z - source["z_geo_m"]))
        )),
        "terminal_maximum_absolute_axis_step_m": float(max(
            np.max(np.abs(np.diff(r))), np.max(np.abs(np.diff(z)))
        )),
        "terminal_maximum_absolute_axis_net_drift_m": float(max(
            abs(r[-1] - r[0]), abs(z[-1] - z[0])
        )),
        "endpoint_r_from_source_m": float(all_r[-1]),
        "endpoint_z_from_source_m": float(all_z[-1]),
        "endpoint_ip_from_source_a": float(all_ip[-1]),
    }
    values["eligible"] = (
        values["maximum_absolute_r_from_source_m"] <= stage["inner_r_radius_m"]
        and values["maximum_absolute_z_from_source_m"] <= stage["inner_z_radius_m"]
        and values["maximum_absolute_ip_from_source_a"] <= stage["inner_ip_fraction"] * abs(source["ip_a"])
        and values["terminal_maximum_source_axis_displacement_m"] <= stage["terminal_max_source_axis_displacement_m"]
        and values["terminal_maximum_absolute_axis_step_m"] <= stage["terminal_max_axis_step_m"]
        and values["terminal_maximum_absolute_axis_net_drift_m"] <= stage["terminal_max_axis_net_drift_m"]
    )
    return values


def selection_key(row: dict[str, Any]) -> tuple[float, float, float, str]:
    metrics = row["hold_metrics"]
    return (metrics["terminal_maximum_source_axis_displacement_m"],
            metrics["terminal_maximum_absolute_axis_step_m"],
            metrics["terminal_maximum_absolute_axis_net_drift_m"], row["candidate_id"])


def _outer_reasons(stage: dict[str, Any], source: RGeoZGeoSignal, current: RGeoZGeoSignal) -> list[str]:
    reasons = []
    if abs(current.boundary.r_geo_m - source.boundary.r_geo_m) > stage["outer_r_radius_m"]:
        reasons.append("OUTER_R")
    if abs(current.boundary.z_geo_m - source.boundary.z_geo_m) > stage["outer_z_radius_m"]:
        reasons.append("OUTER_Z")
    if source.ip_a * current.ip_a <= 0 or abs(current.ip_a - source.ip_a) > stage["outer_ip_fraction"] * abs(source.ip_a):
        reasons.append("OUTER_IP")
    return reasons


def _preissue_reasons(stage: dict[str, Any], source: RGeoZGeoSignal, current: RGeoZGeoSignal) -> list[str]:
    dr = abs(current.boundary.r_geo_m - source.boundary.r_geo_m)
    dz = abs(current.boundary.z_geo_m - source.boundary.z_geo_m)
    dip = abs(current.ip_a - source.ip_a)
    bound = stage["support_evidence"]["prospective_successor_bound"]
    reasons = []
    if dr > stage["inner_r_radius_m"] or stage["outer_r_radius_m"] - dr < bound["r_geo_m"]:
        reasons.append("PREISSUE_R_MARGIN")
    if dz > stage["inner_z_radius_m"] or stage["outer_z_radius_m"] - dz < bound["z_geo_m"]:
        reasons.append("PREISSUE_Z_MARGIN")
    inner_ip = stage["inner_ip_fraction"] * abs(source.ip_a)
    outer_ip = stage["outer_ip_fraction"] * abs(source.ip_a)
    if dip > inner_ip or outer_ip - dip < bound["ip_a"]:
        reasons.append("PREISSUE_IP_MARGIN")
    return reasons


def offline(stage_path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    streams = []
    stage = signal = frozen = None
    try:
        stage, cfg = load(stage_path)
        comparator = ROOT / stage["q0_comparator"]["path"]
        if sha256(comparator) != stage["q0_comparator"]["sha256"]:
            raise ValueError("q0 comparator hash mismatch")
        source = _source(cfg)
        signal = RGeoZGeoSignal.from_tsc_state(source)
        envelope = OneMsNR1SafetyEnvelope.from_signal(signal)
        failures.extend(envelope.state_reasons(signal, source["currents_a_tsc"],
                                                cfg.min_current_a_tsc, cfg.max_current_a_tsc))
        frozen = build_frozen_one_ms_prefixes(
            source_current_a_tsc=source["currents_a_tsc"], turns_tsc=cfg.turns_tsc,
            min_current_a_tsc=cfg.min_current_a_tsc, max_current_a_tsc=cfg.max_current_a_tsc)
        observed = stage["support_evidence"]["maximum_observed_axis_step_m"]
        bound = stage["support_evidence"]["prospective_successor_bound"]
        if not (bound["r_geo_m"] > observed["r_geo"] and bound["z_geo_m"] > observed["z_geo"]
                and bound["ip_a"] > stage["support_evidence"]["maximum_observed_ip_step_a"]):
            raise ValueError("prospective successor bound does not exceed prior evidence")
        for spec in stage["candidates"]:
            target = candidate_target(spec, cfg)
            previous = source["active_command_decimal_a_tsc"]
            fields = []
            for step, item in enumerate(action_stream(stage, frozen.q0, target)):
                exact = card15_target_decimal_a(item, cfg.turns_tsc,
                                                name=f"offline.{spec['candidate_id']}.{step}")
                assert_exact_slew(previous, exact, name=f"offline.{spec['candidate_id']}.{step}")
                previous = exact
                fields.append(list(item.card15_fields))
            streams.append({"candidate_id": spec["candidate_id"], "card15_stream": fields})
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {"schema_version": SCHEMA, "kind": "offline_preflight", "source_revision": source_revision,
            "passed": not failures,
            "route": "ONE_MS_NR2R2C2A_SEARCH_OFFLINE_PASS" if not failures else "ONE_MS_NR2R2C2A_SEARCH_OFFLINE_FAIL_NO_TSC",
            "failures": failures, "stage": stage,
            "source_signal": None if signal is None else signal.to_dict(),
            "frozen_prefixes": None if frozen is None else frozen.to_dict(),
            "action_streams": streams, "new_tsc_or_plant_advances": 0}


def one_rollout(cfg: TSCConfig, stage: dict[str, Any], spec: dict[str, Any], targets: Sequence[Card15Target]) -> dict[str, Any]:
    runner = TSCStepRunner(cfg, worker_id=f"c2a_{spec['candidate_id']}", keep_workspace=False)
    reasons: list[str] = []
    states: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    advance_times: list[float] = []
    started = time.perf_counter()
    try:
        state = runner.reset(episode_name=spec["candidate_id"])
        source_signal = RGeoZGeoSignal.from_tsc_state(state)
        envelope = OneMsNR1SafetyEnvelope.from_signal(source_signal)
        states.append(_record(cfg, state))
        for step, target in enumerate(targets):
            current_signal = RGeoZGeoSignal.from_tsc_state(state)
            reasons.extend(envelope.state_reasons(current_signal, state["currents_a_tsc"],
                                                   cfg.min_current_a_tsc, cfg.max_current_a_tsc))
            reasons.extend(_preissue_reasons(stage, source_signal, current_signal))
            try:
                target_exact = card15_target_decimal_a(target, cfg.turns_tsc,
                                                       name=f"{spec['candidate_id']}.target.{step}")
                maximum = assert_exact_slew(states[-1]["active_command_decimal_a_tsc"], target_exact,
                                            name=f"{spec['candidate_id']}.issue.{step}")
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
                    name=f"{spec['candidate_id']}.observed.{step}")
            except ContractError as exc:
                reasons.append(f"OBSERVED_SLEW:{exc}")
            successor_signal = RGeoZGeoSignal.from_tsc_state(state)
            reasons.extend(envelope.state_reasons(successor_signal, state["currents_a_tsc"],
                                                   cfg.min_current_a_tsc, cfg.max_current_a_tsc))
            reasons.extend(_outer_reasons(stage, source_signal, successor_signal))
            bound = stage["support_evidence"]["prospective_successor_bound"]
            dr = abs(states[-1]["r_geo_m"] - states[-2]["r_geo_m"])
            dz = abs(states[-1]["z_geo_m"] - states[-2]["z_geo_m"])
            dip = abs(states[-1]["ip_a"] - states[-2]["ip_a"])
            if dr > bound["r_geo_m"]:
                reasons.append(f"SUPPORT_BOUND_R:{step}")
            if dz > bound["z_geo_m"]:
                reasons.append(f"SUPPORT_BOUND_Z:{step}")
            if dip > bound["ip_a"]:
                reasons.append(f"SUPPORT_BOUND_IP:{step}")
            if reasons:
                break
    except Exception as exc:
        reasons.append(f"EXECUTION:{type(exc).__name__}:{exc}")
    finally:
        runner.cleanup_runtime_workspace()
    reasons = list(dict.fromkeys(reasons))
    complete = not reasons and len(actions) == stage["horizon_steps"] and len(states) == stage["horizon_steps"] + 1
    return {"candidate_id": spec["candidate_id"], "passed": complete, "reasons": reasons,
            "plant_advances": len(actions), "states": states, "actions": actions,
            "hold_metrics": hold_metrics(states, stage) if complete else None,
            "advance_wall_time_s": advance_times, "wall_time_s": time.perf_counter() - started}


def final_inventory(output: Path, rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    lines = []
    total_bytes = 0
    names = tuple(stage["semantic_artifacts"]) + tuple(stage["diagnostic_artifacts"])
    for row in rows:
        for state_index in range(len(row["states"])):
            folder = output / "rollouts" / row["candidate_id"] / f"{1100 + state_index}ms"
            for name in names:
                path = folder / name
                size = path.stat().st_size
                digest = sha256(path)
                total_bytes += size
                lines.append(f"{path.relative_to(output).as_posix()}\t{size}\t{digest}")
    payload = "".join(f"{line}\n" for line in sorted(lines)).encode("utf-8")
    return {"required_artifact_files": len(lines), "required_artifact_bytes": total_bytes,
            "required_artifact_inventory_sha256": hashlib.sha256(payload).hexdigest()}


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
    source = _source(cfg)
    frozen = build_frozen_one_ms_prefixes(
        source_current_a_tsc=source["currents_a_tsc"], turns_tsc=cfg.turns_tsc,
        min_current_a_tsc=cfg.min_current_a_tsc, max_current_a_tsc=cfg.max_current_a_tsc)
    rows = []
    for spec in stage["candidates"]:
        target = candidate_target(spec, cfg)
        row = one_rollout(cfg, stage, spec, action_stream(stage, frozen.q0, target))
        rows.append(row)
        write_new(output / f"{spec['candidate_id']}.json", row)
        if not row["passed"]:
            break
    execution = len(rows) == len(stage["candidates"]) and all(row["passed"] for row in rows)
    support_failure = any(reason.startswith("SUPPORT_BOUND_") for row in rows for reason in row["reasons"])
    eligible = [row for row in rows if row["passed"] and row["hold_metrics"]["eligible"]]
    selected = min(eligible, key=selection_key) if execution and eligible else None
    route = ("ONE_MS_NR2R2C2A_SEARCH_SUPPORT_BOUND_FAIL_STOP" if support_failure else
             "ONE_MS_NR2R2C2A_SEARCH_EXECUTION_FAIL_STOP" if not execution else
             PASS_ROUTE if selected is not None else NO_CANDIDATE_ROUTE)
    inventory = final_inventory(output, rows, stage)
    result = {"schema_version": SCHEMA, "source_revision": source_revision,
              "passed": selected is not None, "search_execution_passed": execution,
              "route": route, "rollouts_completed": len(rows),
              "plant_advances": sum(row["plant_advances"] for row in rows),
              "candidate_metrics": [{"candidate_id": row["candidate_id"],
                                     "passed": row["passed"], "reasons": row["reasons"],
                                     "hold_metrics": row["hold_metrics"]} for row in rows],
              "selected_candidate": None if selected is None else {
                  "candidate_id": selected["candidate_id"],
                  "action_sha256": hashlib.sha256(json.dumps(selected["actions"], sort_keys=True).encode()).hexdigest(),
                  "selection_key": list(selection_key(selected)),
              },
              "worst_rollout_wall_time_s": max((row["wall_time_s"] for row in rows), default=None),
              "total_rollout_wall_time_s": sum(row["wall_time_s"] for row in rows),
              **inventory,
              "claim_boundary": "development_search_only_candidate_requires_separate_fresh_validation"}
    write_new(output / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("offline", "run"))
    parser.add_argument("--stage-config", type=Path, default=ROOT / "configs/rgeo_zgeo_1ms_nr2r2c2a_search.json")
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
