#!/usr/bin/env python3
"""Frozen NR2R2C2aA2 supported-cube direction discriminator."""

from __future__ import annotations

import argparse
from decimal import Decimal
import json
from pathlib import Path
import sys
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_nr1_qualification import _source  # noqa: E402
from scripts.rgeo_zgeo_1ms_nr2r2c2a_search import (  # noqa: E402
    final_inventory, sha256, write_new,
)
from scripts.rgeo_zgeo_1ms_nr2r2c2aa1_authority import (  # noqa: E402
    authority_metrics, assert_exact_doubled_card15_offset, one_rollout,
    target_from_fields,
)
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    Card15Target, OneMsNR1SafetyEnvelope, assert_exact_slew,
    build_frozen_one_ms_prefixes, card15_target_decimal_a,
    validate_one_ms_config,
)
from tsc_rzip_rllib.control.rgeo_zgeo_contract import ContractError, RGeoZGeoSignal  # noqa: E402
from tsc_rzip_rllib.core.runner import TSCConfig  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-nr2r2c2aa2-supported-cube-directions-v1"
PASS_ROUTE = "ONE_MS_NR2R2C2AA2_SUPPORTED_CUBE_DIRECTION_FOUND_FRESH_VALIDATION_REQUIRED"
FAIL_ROUTE = "ONE_MS_NR2R2C2AA2_SUPPORTED_CUBE_DIRECTIONS_FAIL_REDESIGN"


def load(stage_path: Path) -> tuple[dict[str, Any], TSCConfig]:
    stage = json.loads(stage_path.read_text(encoding="utf-8"))
    if stage.get("schema_version") != SCHEMA:
        raise ValueError("unexpected C2aA2 schema")
    if (stage["rollouts"] != len(stage["candidates"])
            or stage["rollouts"] * stage["horizon_steps"] != stage["maximum_plant_advances"]
            or stage["maximum_plant_advances"] != 96):
        raise ValueError("C2aA2 plant budget mismatch")
    if [item["candidate_id"] for item in stage["candidates"]] != [
        "p03_minus", "p04_minus", "p07_minus"
    ]:
        raise ValueError("C2aA2 candidate identity mismatch")
    if stage["support_evidence"]["holdout_records_read"] != 0:
        raise ValueError("C2aA2 may not read the invalid holdout")
    covered = [step for row in stage["schedule"]
               for step in range(row["first_step"], row["last_step"] + 1)]
    if covered != list(range(stage["horizon_steps"])):
        raise ValueError("C2aA2 schedule does not cover each step exactly once")
    cfg = TSCConfig.from_json(ROOT / stage["base_tsc_config"])
    validate_one_ms_config(start_folder=cfg.start_folder, dt_ms=cfg.dt_ms,
                           slew_a_per_ms=cfg.current_slew_a_per_ms)
    return stage, cfg


def targets_for(stage: dict[str, Any], q0: Card15Target, entry: Card15Target,
                full: Card15Target) -> tuple[Card15Target, ...]:
    levels = {"q0": q0, "entry": entry, "full": full}
    targets: list[Card15Target | None] = [None] * stage["horizon_steps"]
    for row in stage["schedule"]:
        for step in range(row["first_step"], row["last_step"] + 1):
            targets[step] = levels[row["level"]]
    if any(target is None for target in targets):
        raise ContractError("C2aA2 target schedule is incomplete")
    return tuple(target for target in targets if target is not None)


def candidate_targets(stage: dict[str, Any], spec: dict[str, Any], q0: Card15Target,
                      cfg: TSCConfig) -> tuple[Card15Target, Card15Target,
                                               tuple[Card15Target, ...]]:
    full = target_from_fields(spec["full_card15_fields"], cfg,
                              f"c2aa2.{spec['candidate_id']}.full")
    entry = (q0 if spec["entry_level"] == "q0" else
             target_from_fields(spec["level1_card15_fields"], cfg,
                                f"c2aa2.{spec['candidate_id']}.entry"))
    if spec["entry_level"] == "level1":
        assert_exact_doubled_card15_offset(q0, entry, full)
    return entry, full, targets_for(stage, q0, entry, full)


def offline(stage_path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    stage = signal = frozen = None
    streams: list[dict[str, Any]] = []
    try:
        stage, cfg = load(stage_path)
        for key in ("selection_audit", "q0_comparator"):
            if sha256(ROOT / stage[key]["path"]) != stage[key]["sha256"]:
                raise ValueError(f"{key} hash mismatch")
        selection = json.loads((ROOT / stage["selection_audit"]["path"]).read_text(encoding="utf-8"))
        selected = {item["candidate_id"]: item for item in selection["candidates"]}
        if list(selected) != [item["candidate_id"] for item in stage["candidates"]]:
            raise ValueError("selection audit candidate order mismatch")
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
        observed = stage["support_evidence"]["maximum_observed_axis_step_m"]
        bound = stage["support_evidence"]["prospective_successor_bound"]
        if not (bound["r_geo_m"] > observed["r_geo"]
                and bound["z_geo_m"] > observed["z_geo"]
                and bound["ip_a"] > stage["support_evidence"]["maximum_observed_ip_step_a"]):
            raise ValueError("prospective successor bound does not exceed prior evidence")
        q0_exact = card15_target_decimal_a(frozen.q0, cfg.turns_tsc, name="c2aa2.q0")
        for spec in stage["candidates"]:
            selected_row = selected[spec["candidate_id"]]
            expected_source_fields = (spec["full_card15_fields"] if spec["entry_level"] == "q0"
                                      else spec["level1_card15_fields"])
            if selected_row["source_first_event_card15_fields"] != expected_source_fields:
                raise ValueError(f"{spec['candidate_id']} does not reproduce its selected development event")
            entry, full, targets = candidate_targets(stage, spec, frozen.q0, cfg)
            full_exact = card15_target_decimal_a(full, cfg.turns_tsc,
                                                 name=f"c2aa2.{spec['candidate_id']}.full")
            if max(abs(left - right) for left, right in zip(q0_exact, full_exact)) > Decimal("0.3"):
                raise ContractError(f"{spec['candidate_id']} leaves q0 +/- 0.3 A")
            previous = source["active_command_decimal_a_tsc"]
            actions = []
            for step, target in enumerate(targets):
                exact = card15_target_decimal_a(target, cfg.turns_tsc,
                                                name=f"c2aa2.{spec['candidate_id']}.{step}")
                maximum = assert_exact_slew(previous, exact,
                                            name=f"c2aa2.{spec['candidate_id']}.{step}")
                actions.append({"step": step,
                                "level": next(row["level"] for row in stage["schedule"]
                                              if row["first_step"] <= step <= row["last_step"]),
                                "card15_fields": list(target.card15_fields),
                                "maximum_issued_delta_a": maximum})
                previous = exact
            streams.append({"candidate_id": spec["candidate_id"],
                            "entry_card15_fields": list(entry.card15_fields),
                            "full_card15_fields": list(full.card15_fields),
                            "actions": actions})
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {"schema_version": SCHEMA, "kind": "offline_preflight",
            "source_revision": source_revision, "passed": not failures,
            "route": ("ONE_MS_NR2R2C2AA2_OFFLINE_PASS" if not failures
                      else "ONE_MS_NR2R2C2AA2_OFFLINE_FAIL_NO_TSC"),
            "failures": failures, "stage": stage,
            "source_signal": None if signal is None else signal.to_dict(),
            "frozen_prefixes": None if frozen is None else frozen.to_dict(),
            "candidate_streams": streams, "new_tsc_or_plant_advances": 0}


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
    rows = []
    for spec in stage["candidates"]:
        _, _, targets = candidate_targets(stage, spec, frozen.q0, cfg)
        row = one_rollout(cfg, stage, spec["candidate_id"], targets, q0_record["states"])
        rows.append(row)
        write_new(output / f"{spec['candidate_id']}.json", row)
        if not row["passed"]:
            break
    execution = (len(rows) == len(stage["candidates"])
                 and all(row["passed"] for row in rows))
    support_failure = any(reason.startswith("SUPPORT_BOUND_")
                          for row in rows for reason in row["reasons"])
    passing = [row["candidate_id"] for row in rows
               if row["passed"] and row["authority_metrics"]["passed"]]
    scientific_pass = execution and bool(passing)
    route = ("ONE_MS_NR2R2C2AA2_SUPPORT_BOUND_FAIL_STOP" if support_failure else
             "ONE_MS_NR2R2C2AA2_EXECUTION_FAIL_STOP" if not execution else
             PASS_ROUTE if scientific_pass else FAIL_ROUTE)
    inventory = final_inventory(output, rows, stage)
    result = {"schema_version": SCHEMA, "source_revision": source_revision,
              "passed": scientific_pass, "execution_passed": execution,
              "route": route, "rollouts_completed": len(rows),
              "plant_advances": sum(row["plant_advances"] for row in rows),
              "passing_candidates": passing,
              "authority_metrics": [{"candidate_id": row["candidate_id"],
                                      **row["authority_metrics"]}
                                     for row in rows if row["authority_metrics"]],
              "worst_rollout_wall_time_s": max((row["wall_time_s"] for row in rows), default=None),
              "total_rollout_wall_time_s": sum(row["wall_time_s"] for row in rows),
              **inventory,
              "claim_boundary": "supported_cube_direction_only_not_hold_recovery_model_or_control"}
    write_new(output / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("offline", "run"))
    parser.add_argument("--stage-config", type=Path,
                        default=ROOT / "configs/rgeo_zgeo_1ms_nr2r2c2aa2_supported_cube_directions.json")
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
