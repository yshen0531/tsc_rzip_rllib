#!/usr/bin/env python3
"""Canonical-1100-ms full-prefix replay qualifier for NR2R2C1a."""

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
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    RETURN_EQUIVALENCE_A, OneMsNR1SafetyEnvelope, assert_exact_slew,
    build_frozen_one_ms_prefixes, card15_target_decimal_a, validate_one_ms_config,
)
from tsc_rzip_rllib.control.rgeo_zgeo_contract import ContractError, RGeoZGeoSignal  # noqa: E402
from tsc_rzip_rllib.core.runner import TSCConfig, TSCStepRunner  # noqa: E402

SCHEMA = "rgeo-zgeo-1ms-nr2r2c1a-canonical-source-replay-v1"
PASS_ROUTE = "ONE_MS_NR2R2C1A_CANONICAL_SOURCE_REPLAY_QUALIFIED_C2A_DESIGN_ONLY"


def write_new(path: Path, payload: Any) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def load(stage_path: Path) -> tuple[dict[str, Any], TSCConfig]:
    stage = json.loads(stage_path.read_text(encoding="utf-8"))
    if stage.get("schema_version") != SCHEMA:
        raise ValueError("unexpected C1a schema")
    expected = [("q0", 4, 2), ("q0", 8, 2), ("q0", 16, 2), ("q0", 32, 2),
                ("pattern_a", 4, 2), ("pattern_b", 4, 2)]
    actual = [(row["family"], row["horizon_steps"], row["repeats"]) for row in stage["families"]]
    if actual != expected or sum(horizon * repeats for _, horizon, repeats in expected) != stage["maximum_plant_advances"]:
        raise ValueError("C1a frozen matrix or plant budget mismatch")
    cfg = TSCConfig.from_json(ROOT / stage["base_tsc_config"])
    validate_one_ms_config(start_folder=cfg.start_folder, dt_ms=cfg.dt_ms,
                           slew_a_per_ms=cfg.current_slew_a_per_ms)
    return stage, cfg


def matrix(stage: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for spec in stage["families"]:
        pair_id = f"{spec['family']}_h{spec['horizon_steps']:02d}"
        for repeat in range(spec["repeats"]):
            rows.append({"rollout_id": f"{pair_id}_r{repeat}", "pair_id": pair_id,
                         "family": spec["family"], "horizon_steps": spec["horizon_steps"],
                         "repeat_index": repeat})
    return rows


def targets_for(spec: dict[str, Any], frozen: Any) -> tuple[Any, ...]:
    if spec["family"] == "q0":
        return (frozen.q0,) * spec["horizon_steps"]
    targets = frozen.prefixes[spec["family"]]
    if len(targets) != spec["horizon_steps"]:
        raise ContractError("non-q0 C1a schedule is not the exact NR1R2 four-step prefix")
    return targets


def offline(stage_path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    stage = signal = frozen = None
    streams = []
    try:
        stage, cfg = load(stage_path)
        source = _source(cfg)
        signal = RGeoZGeoSignal.from_tsc_state(source)
        envelope = OneMsNR1SafetyEnvelope.from_signal(signal)
        failures.extend(envelope.state_reasons(signal, source["currents_a_tsc"],
                                                cfg.min_current_a_tsc, cfg.max_current_a_tsc))
        frozen = build_frozen_one_ms_prefixes(
            source_current_a_tsc=source["currents_a_tsc"], turns_tsc=cfg.turns_tsc,
            min_current_a_tsc=cfg.min_current_a_tsc, max_current_a_tsc=cfg.max_current_a_tsc)
        for spec in matrix(stage):
            previous = source["active_command_decimal_a_tsc"]
            fields = []
            for step, target in enumerate(targets_for(spec, frozen)):
                exact = card15_target_decimal_a(target, cfg.turns_tsc,
                                                name=f"offline.{spec['rollout_id']}.{step}")
                assert_exact_slew(previous, exact, name=f"offline.{spec['rollout_id']}.{step}")
                previous = exact
                fields.append(list(target.card15_fields))
            streams.append({"rollout_id": spec["rollout_id"], "card15_stream": fields})
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {"schema_version": SCHEMA, "kind": "offline_preflight", "source_revision": source_revision,
            "passed": not failures,
            "route": "ONE_MS_NR2R2C1A_OFFLINE_PASS" if not failures else "ONE_MS_NR2R2C1A_OFFLINE_FAIL_NO_TSC",
            "failures": failures, "stage": stage,
            "source_signal": None if signal is None else signal.to_dict(),
            "frozen_prefixes": None if frozen is None else frozen.to_dict(),
            "action_streams": streams, "new_tsc_or_plant_advances": 0}


def _sizes(folder: Path, names: Sequence[str]) -> dict[str, int]:
    return {name: (folder / name).stat().st_size for name in names}


def one_rollout(cfg: TSCConfig, stage: dict[str, Any], spec: dict[str, Any], targets: Sequence[Any]) -> dict[str, Any]:
    runner = TSCStepRunner(cfg, worker_id=f"c1a_{spec['rollout_id']}", keep_workspace=False)
    reasons: list[str] = []
    states: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    advance_times: list[float] = []
    started = time.perf_counter()
    reset_started = started
    try:
        state = runner.reset(episode_name=spec["rollout_id"])
        reset_wall = time.perf_counter() - reset_started
        source_record = _record(cfg, state)
        source_record["artifact_size_bytes"] = _sizes(Path(state["folder"]),
            tuple(stage["semantic_artifacts"]) + tuple(stage["diagnostic_artifacts"]))
        states.append(source_record)
        source_current = tuple(source_record["actual_current_decimal_a_tsc"])
        source_command = tuple(Decimal(x) for x in source_record["active_command_decimal_a_tsc"])
        envelope = OneMsNR1SafetyEnvelope.from_signal(RGeoZGeoSignal.from_tsc_state(state))
        for step, target in enumerate(targets):
            reasons.extend(envelope.state_reasons(RGeoZGeoSignal.from_tsc_state(state), state["currents_a_tsc"],
                                                   cfg.min_current_a_tsc, cfg.max_current_a_tsc))
            try:
                target_decimal = card15_target_decimal_a(target, cfg.turns_tsc,
                                                        name=f"{spec['rollout_id']}.target.{step}")
                maximum = assert_exact_slew(states[-1]["active_command_decimal_a_tsc"], target_decimal,
                                            name=f"{spec['rollout_id']}.issued.{step}")
            except ContractError as exc:
                reasons.append(f"ISSUED_SLEW:{exc}")
                break
            if reasons:
                break
            action = {"issue_step": step, "issue_time_ms": int(state["time_ms"]),
                      "expected_card15_fields": list(target.card15_fields),
                      "target_current_a_tsc": list(target.current_a_tsc),
                      "maximum_issued_delta_a": maximum, "effect_state_index": step + 1,
                      "effect_age_steps": 1}
            advance_started = time.perf_counter()
            state = runner.step_current_a(np.asarray(target.current_a_tsc, dtype=float))
            advance_times.append(time.perf_counter() - advance_started)
            actions.append(action)
            if int(state.get("returncode", 0)) != 0:
                reasons.append(f"TSC_RETURNCODE:{state.get('returncode')}")
            if bool(state.get("abnormal", False)):
                reasons.append(f"TSC_ABNORMAL:{state.get('done_reason', '')}")
            record = _record(cfg, state)
            record["artifact_size_bytes"] = _sizes(Path(state["folder"]),
                tuple(stage["semantic_artifacts"]) + tuple(stage["diagnostic_artifacts"]))
            states.append(record)
            if record["time_ms"] != 1100 + step + 1:
                reasons.append(f"TIME:{step}")
            if tuple(record["active_command_card15_fields"]) != target.card15_fields:
                reasons.append(f"CARD15:{step}")
            try:
                record["maximum_observed_delta_a"] = assert_exact_slew(
                    states[-2]["actual_current_decimal_a_tsc"], record["actual_current_decimal_a_tsc"],
                    name=f"{spec['rollout_id']}.observed.{step}")
            except ContractError as exc:
                reasons.append(f"OBSERVED_SLEW:{exc}")
            reasons.extend(envelope.state_reasons(RGeoZGeoSignal.from_tsc_state(state), state["currents_a_tsc"],
                                                   cfg.min_current_a_tsc, cfg.max_current_a_tsc))
            if step == 0 and spec["family"] != "q0":
                effect = tuple(Decimal(x) - Decimal(y) for x, y in zip(record["actual_current_decimal_a_tsc"], source_current))
                requested = tuple(x - y for x, y in zip(target_decimal, source_command))
                if any(x == 0 or ((x > 0) != (y > 0)) for x, y in zip(effect, requested)):
                    reasons.append("FIRST_EFFECT_SIGN")
            if step >= 1 and spec["family"] != "q0" and max(
                abs(Decimal(x) - Decimal(y)) for x, y in zip(record["actual_current_decimal_a_tsc"], source_current)
            ) > RETURN_EQUIVALENCE_A:
                reasons.append(f"CENTER_RETURN:{step}")
            if reasons:
                break
    except Exception as exc:
        reset_wall = time.perf_counter() - reset_started
        reasons.append(f"EXECUTION:{type(exc).__name__}:{exc}")
    finally:
        runner.cleanup_runtime_workspace()
    reasons = list(dict.fromkeys(reasons))
    complete = not reasons and len(actions) == spec["horizon_steps"] and len(states) == spec["horizon_steps"] + 1
    return {**spec, "passed": complete, "reasons": reasons, "plant_advances": len(actions),
            "states": states, "actions": actions, "reset_wall_time_s": reset_wall,
            "advance_wall_time_s": advance_times, "wall_time_s": time.perf_counter() - started}


def compare_pair(left: dict[str, Any], right: dict[str, Any], stage: dict[str, Any]) -> dict[str, Any]:
    maxima = {"geometry_m": 0.0, "ip_a": 0.0, "coil_a": 0.0, "wire_a": 0.0}
    failures: list[str] = []
    sprsina_equal = True
    if left["actions"] != right["actions"]:
        failures.append("ACTION_STREAM")
    if len(left["states"]) != len(right["states"]):
        failures.append("STATE_COUNT")
    for index, (a, b) in enumerate(zip(left["states"], right["states"])):
        if a["time_ms"] != b["time_ms"]:
            failures.append(f"TIME:{index}")
        maxima["geometry_m"] = max(maxima["geometry_m"], *(abs(a[k] - b[k]) for k in ("r_geo_m", "z_geo_m", "r_mid_m")))
        maxima["ip_a"] = max(maxima["ip_a"], abs(a["ip_a"] - b["ip_a"]))
        maxima["coil_a"] = max(maxima["coil_a"], max(abs(float(x) - float(y)) for x, y in zip(a["actual_current_decimal_a_tsc"], b["actual_current_decimal_a_tsc"])))
        maxima["wire_a"] = max(maxima["wire_a"], max(abs(x - y) for x, y in zip(a["wire_current_a"], b["wire_current_a"])))
        if any(a["artifact_sha256"][name] != b["artifact_sha256"][name] for name in stage["semantic_artifacts"]):
            failures.append(f"SEMANTIC_ARTIFACT:{index}")
        sprsina_equal = sprsina_equal and a["artifact_sha256"]["sprsina"] == b["artifact_sha256"]["sprsina"]
    for key, maximum in maxima.items():
        if maximum > stage["repeatability"][key]:
            failures.append(key.upper())
    return {"pair_id": left["pair_id"], "passed": not failures, "failures": list(dict.fromkeys(failures)),
            "maximum_absolute_difference": maxima, "sprsina_hash_exact_all_states": sprsina_equal}


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
    frozen = build_frozen_one_ms_prefixes(source_current_a_tsc=source["currents_a_tsc"],
        turns_tsc=cfg.turns_tsc, min_current_a_tsc=cfg.min_current_a_tsc, max_current_a_tsc=cfg.max_current_a_tsc)
    rows = []
    for spec in matrix(stage):
        row = one_rollout(cfg, stage, spec, targets_for(spec, frozen))
        rows.append(row)
        write_new(output / f"{spec['rollout_id']}.json", row)
        if not row["passed"]:
            break
    execution = len(rows) == 12 and all(row["passed"] for row in rows)
    pairs = []
    if execution:
        for pair_id in dict.fromkeys(row["pair_id"] for row in rows):
            pair = [row for row in rows if row["pair_id"] == pair_id]
            pairs.append(compare_pair(pair[0], pair[1], stage))
    replay = execution and len(pairs) == 6 and all(pair["passed"] for pair in pairs)
    worst = max((row["wall_time_s"] for row in rows), default=float("inf"))
    route = PASS_ROUTE if replay else ("ONE_MS_NR2R2C1A_EXECUTION_OR_HISTORY_FAIL_STOP" if not execution
                                      else "ONE_MS_NR2R2C1A_SOURCE_REPLAY_MISMATCH_STOP")
    result = {"schema_version": SCHEMA, "source_revision": source_revision, "passed": replay,
              "route": route, "rollouts_completed": len(rows),
              "plant_advances": sum(row["plant_advances"] for row in rows), "pair_comparisons": pairs,
              "offline_source_shooting_usable": replay,
              "online_1ms_oracle_eligible": replay and worst <= stage["online_branch_deadline_s"],
              "worst_rollout_wall_time_s": worst,
              "total_rollout_wall_time_s": sum(row["wall_time_s"] for row in rows),
              "required_artifact_files": sum(len(state["artifact_size_bytes"]) for row in rows for state in row["states"]),
              "required_artifact_bytes": sum(sum(state["artifact_size_bytes"].values()) for row in rows for state in row["states"]),
              "claim_boundary": "canonical_source_full_replay_mechanics_only_c2a_design_not_action_authority"}
    write_new(output / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("offline", "run"))
    parser.add_argument("--stage-config", type=Path, default=ROOT / "configs/rgeo_zgeo_1ms_nr2r2c1a_source_replay.json")
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = offline(args.stage_config.resolve(), args.source_revision) if args.mode == "offline" else run(
        args.stage_config.resolve(), args.source_revision, args.output.resolve())
    if args.mode == "offline":
        write_new(args.output.resolve(), result)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
