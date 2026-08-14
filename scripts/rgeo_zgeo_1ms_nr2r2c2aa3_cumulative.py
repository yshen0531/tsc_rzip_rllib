#!/usr/bin/env python3
"""Frozen NR2R2C2aA3 p03 cumulative-level2 discriminator."""

from __future__ import annotations

import argparse
from decimal import Decimal
import json
from pathlib import Path
import sys
from typing import Any, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_nr1_qualification import _source  # noqa: E402
from scripts.rgeo_zgeo_1ms_nr2r2c1a_source_replay import compare_pair  # noqa: E402
from scripts.rgeo_zgeo_1ms_nr2r2c2a_search import final_inventory, sha256, write_new  # noqa: E402
from scripts.rgeo_zgeo_1ms_nr2r2c2aa1_authority import (  # noqa: E402
    assert_exact_doubled_card15_offset, one_rollout, target_from_fields, targets_for,
)
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    OneMsNR1SafetyEnvelope, assert_exact_slew, build_frozen_one_ms_prefixes,
    card15_target_decimal_a, validate_one_ms_config,
)
from tsc_rzip_rllib.control.rgeo_zgeo_contract import ContractError, RGeoZGeoSignal  # noqa: E402
from tsc_rzip_rllib.core.runner import TSCConfig  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-nr2r2c2aa3-p03-cumulative-level2-v1"
PASS_ROUTE = "ONE_MS_NR2R2C2AA3_P03_CUMULATIVE_LEVEL2_PASS_TIME_VARYING_C2A_DESIGN_ONLY"
FAIL_ROUTE = "ONE_MS_NR2R2C2AA3_P03_CUMULATIVE_LEVEL2_FAIL_REDESIGN"


def load(stage_path: Path) -> tuple[dict[str, Any], TSCConfig]:
    stage = json.loads(stage_path.read_text(encoding="utf-8"))
    if stage.get("schema_version") != SCHEMA:
        raise ValueError("unexpected C2aA3 schema")
    if (stage["rollouts"] * stage["horizon_steps"] != stage["maximum_plant_advances"]
            or stage["maximum_plant_advances"] != 64):
        raise ValueError("C2aA3 plant budget mismatch")
    if stage["support_evidence"]["holdout_records_read"] != 0:
        raise ValueError("C2aA3 may not read the invalid holdout")
    covered = [step for row in stage["schedule"]
               for step in range(row["first_step"], row["last_step"] + 1)]
    if covered != list(range(stage["horizon_steps"])):
        raise ValueError("C2aA3 schedule does not cover each step exactly once")
    cfg = TSCConfig.from_json(ROOT / stage["base_tsc_config"])
    validate_one_ms_config(start_folder=cfg.start_folder, dt_ms=cfg.dt_ms,
                           slew_a_per_ms=cfg.current_slew_a_per_ms)
    return stage, cfg


def incremental_metrics(states: Sequence[dict[str, Any]], q0_states: Sequence[dict[str, Any]],
                        level1_states: Sequence[dict[str, Any]],
                        stage: dict[str, Any]) -> dict[str, Any]:
    first, last = stage["authority_window_start_state"], stage["authority_window_end_state"]
    total = np.asarray([
        (states[index]["r_geo_m"] - q0_states[index]["r_geo_m"])
        - (states[index]["z_geo_m"] - q0_states[index]["z_geo_m"])
        for index in range(first, last + 1)
    ], dtype=float)
    level1 = np.asarray([
        (level1_states[index]["r_geo_m"] - q0_states[index]["r_geo_m"])
        - (level1_states[index]["z_geo_m"] - q0_states[index]["z_geo_m"])
        for index in range(first, last + 1)
    ], dtype=float)
    incremental = total - level1
    values = {"window_states": list(range(first, last + 1)),
              "incremental_opposition_m": incremental.tolist(),
              "mean_incremental_opposition_m": float(np.mean(incremental)),
              "positive_incremental_fraction": float(np.mean(incremental > 0.0))}
    values["passed"] = (
        values["mean_incremental_opposition_m"]
        >= stage["minimum_mean_incremental_opposition_m"]
        and values["positive_incremental_fraction"]
        >= stage["minimum_positive_incremental_fraction"])
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
        if level1_record["actions"][2]["expected_card15_fields"] != stage["level1_card15_fields"]:
            raise ValueError("level1 fields do not reproduce the tracked p03 action")
        source = _source(cfg)
        signal = RGeoZGeoSignal.from_tsc_state(source)
        envelope = OneMsNR1SafetyEnvelope.from_signal(signal)
        failures.extend(envelope.state_reasons(signal, source["currents_a_tsc"],
                                                cfg.min_current_a_tsc, cfg.max_current_a_tsc))
        frozen = build_frozen_one_ms_prefixes(
            source_current_a_tsc=source["currents_a_tsc"], turns_tsc=cfg.turns_tsc,
            min_current_a_tsc=cfg.min_current_a_tsc, max_current_a_tsc=cfg.max_current_a_tsc)
        q0_record = json.loads((ROOT / stage["q0_comparator"]["path"]).read_text(encoding="utf-8"))
        if list(frozen.q0.card15_fields) != q0_record["actions"][0]["expected_card15_fields"]:
            raise ValueError("q0 target does not reproduce the tracked comparator action")
        level1 = target_from_fields(stage["level1_card15_fields"], cfg, "c2aa3.level1")
        level2 = target_from_fields(stage["level2_card15_fields"], cfg, "c2aa3.level2")
        assert_exact_doubled_card15_offset(frozen.q0, level1, level2)
        targets = targets_for(stage, frozen.q0, level1, level2)
        q0_exact = card15_target_decimal_a(frozen.q0, cfg.turns_tsc, name="c2aa3.q0")
        level2_exact = card15_target_decimal_a(level2, cfg.turns_tsc, name="c2aa3.level2")
        if max(abs(left - right) for left, right in zip(q0_exact, level2_exact)) > Decimal("0.6"):
            raise ContractError("level2 leaves the componentwise q0 +/- 0.6 A domain")
        bound = stage["support_evidence"]["prospective_successor_bound"]
        for prior_key in ("p03_level1_maximum_observed_successor",
                          "all_prior_supported_cube_maximum_observed_successor"):
            prior = stage["support_evidence"][prior_key]
            if not (bound["r_geo_m"] > prior["r_geo_m"]
                    and bound["z_geo_m"] > prior["z_geo_m"] and bound["ip_a"] > prior["ip_a"]):
                raise ValueError(f"prospective successor bound does not exceed {prior_key}")
        previous = source["active_command_decimal_a_tsc"]
        for step, target in enumerate(targets):
            exact = card15_target_decimal_a(target, cfg.turns_tsc, name=f"c2aa3.offline.{step}")
            maximum = assert_exact_slew(previous, exact, name=f"c2aa3.offline.{step}")
            stream.append({"step": step,
                           "level": next(row["level"] for row in stage["schedule"]
                                         if row["first_step"] <= step <= row["last_step"]),
                           "card15_fields": list(target.card15_fields),
                           "maximum_issued_delta_a": maximum})
            previous = exact
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {"schema_version": SCHEMA, "kind": "offline_preflight",
            "source_revision": source_revision, "passed": not failures,
            "route": ("ONE_MS_NR2R2C2AA3_OFFLINE_PASS" if not failures
                      else "ONE_MS_NR2R2C2AA3_OFFLINE_FAIL_NO_TSC"),
            "failures": failures, "stage": stage,
            "source_signal": None if signal is None else signal.to_dict(),
            "frozen_prefixes": None if frozen is None else frozen.to_dict(),
            "action_stream": stream, "new_tsc_or_plant_advances": 0}


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
    level1_record = json.loads((ROOT / stage["level1_comparator"]["path"]).read_text(encoding="utf-8"))
    source = _source(cfg)
    frozen = build_frozen_one_ms_prefixes(
        source_current_a_tsc=source["currents_a_tsc"], turns_tsc=cfg.turns_tsc,
        min_current_a_tsc=cfg.min_current_a_tsc, max_current_a_tsc=cfg.max_current_a_tsc)
    level1 = target_from_fields(stage["level1_card15_fields"], cfg, "c2aa3.level1")
    level2 = target_from_fields(stage["level2_card15_fields"], cfg, "c2aa3.level2")
    targets = targets_for(stage, frozen.q0, level1, level2)
    rows = []
    for index in range(stage["rollouts"]):
        rollout_id = f"p03_cumulative_level2_r{index}"
        row = one_rollout(cfg, stage, rollout_id, targets, q0_record["states"])
        if row["passed"]:
            row["incremental_metrics"] = incremental_metrics(
                row["states"], q0_record["states"], level1_record["states"], stage)
        else:
            row["incremental_metrics"] = None
        rows.append(row)
        write_new(output / f"{rollout_id}.json", row)
        if not row["passed"]:
            break
    execution = len(rows) == 2 and all(row["passed"] for row in rows)
    pair = compare_pair(rows[0], rows[1], stage) if execution else None
    repeatable = execution and pair is not None and pair["passed"]
    authority = bool(repeatable and all(
        row["authority_metrics"]["passed"] and row["incremental_metrics"]["passed"]
        for row in rows))
    support_failure = any(reason.startswith("SUPPORT_BOUND_")
                          for row in rows for reason in row["reasons"])
    route = ("ONE_MS_NR2R2C2AA3_SUPPORT_BOUND_FAIL_STOP" if support_failure else
             "ONE_MS_NR2R2C2AA3_EXECUTION_FAIL_STOP" if not execution else
             "ONE_MS_NR2R2C2AA3_REPEATABILITY_FAIL_STOP" if not repeatable else
             PASS_ROUTE if authority else FAIL_ROUTE)
    inventory = final_inventory(output, rows, stage)
    result = {"schema_version": SCHEMA, "source_revision": source_revision,
              "passed": authority, "execution_passed": execution,
              "repeatability_passed": repeatable, "route": route,
              "rollouts_completed": len(rows),
              "plant_advances": sum(row["plant_advances"] for row in rows),
              "pair_comparison": pair,
              "authority_metrics": [row["authority_metrics"] for row in rows
                                    if row["authority_metrics"]],
              "incremental_metrics": [row["incremental_metrics"] for row in rows
                                      if row["incremental_metrics"]],
              "worst_rollout_wall_time_s": max((row["wall_time_s"] for row in rows), default=None),
              "total_rollout_wall_time_s": sum(row["wall_time_s"] for row in rows),
              **inventory,
              "claim_boundary": "p03_cumulative_level2_only_not_hold_recovery_model_or_control"}
    write_new(output / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("offline", "run"))
    parser.add_argument("--stage-config", type=Path,
                        default=ROOT / "configs/rgeo_zgeo_1ms_nr2r2c2aa3_p03_cumulative_level2.json")
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
