#!/usr/bin/env python3
"""Fixed-1000 early-minus/late-plus radial Authority G1 campaign."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_1000_absolute_radial_authority_g0 as g0  # noqa: E402
from scripts import rgeo_zgeo_1ms_1000_baseline_b0 as b0  # noqa: E402
from scripts import rgeo_zgeo_1ms_1000_signed_temporal_d0 as d0  # noqa: E402
from scripts.rgeo_zgeo_1ms_nr1_qualification import _source  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    OneMsNR1SafetyEnvelope, assert_exact_slew, build_frozen_one_ms_prefixes,
    card15_target_decimal_a, quantize_target, validate_one_ms_config,
)
from tsc_rzip_rllib.control.rgeo_zgeo_contract import ContractError, RGeoZGeoSignal  # noqa: E402
from tsc_rzip_rllib.core.runner import TSCConfig  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-1000-hybrid-radial-authority-g1-v1"
CONFIG_SHA256 = "651796274b77fd690d941d51fe43c8ff13e2e40bae2346683057dcf29715ae9e"
DEFAULT_CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_hybrid_radial_authority_g1.json"
SEMANTIC_ARTIFACTS = b0.SEMANTIC_ARTIFACTS
InputIntegrityError = g0.InputIntegrityError


def load(config_path: Path) -> tuple[dict[str, Any], TSCConfig, dict[str, Any]]:
    config_path = b0.inside_root(config_path, "G1 config")
    if b0.sha256(config_path) != CONFIG_SHA256:
        raise InputIntegrityError("G1 config SHA-256 mismatch")
    stage = json.loads(config_path.read_text(encoding="utf-8"))
    exact = {
        "schema_version": SCHEMA,
        "campaign_id": "rgeo_zgeo_1ms_1000_hybrid_radial_authority_g1_v1",
        "takeover_time_ms": 1000, "control_period_ms": 1, "horizon_steps": 64,
        "initial_minus_depths": [4, 8, 12, 16],
        "transition_level_increment_per_issue": 2, "final_plus_level": 32,
        "critical_replay_minus_depth": 12, "rollouts": 6,
        "maximum_reset_calls": 6, "maximum_advance_attempts": 384,
        "maximum_gotsc_calls": 384, "maximum_verified_plant_advances": 384,
        "retry_after_any_advance_attempt": "forbidden",
        "requested_single_turn_increment_a": 0.14,
        "maximum_quantized_adjacent_increment_a": 0.3,
        "minimum_cumulative_level": -16, "maximum_cumulative_level": 32,
        "terminal_state_start": 56, "terminal_state_end": 64,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise InputIntegrityError(f"G1 frozen field mismatch: {key}")
    roles = stage.get("data_roles", {})
    if roles.get("matched_q0") != "development_fit_eligible_weight_1" or roles.get(
        "primary_candidates"
    ) != "development_fit_eligible_weight_1" or roles.get(
        "critical_replay"
    ) != "integrity_only_zero_fit_weight":
        raise InputIntegrityError("G1 development roles changed")
    if any(roles.get(key) != "unopened" for key in ("calibration", "holdout")) or roles.get(
        "controller_or_recourse"
    ) != "forbidden":
        raise InputIntegrityError("G1 qualification roles changed")
    base = b0.inside_root(ROOT / stage["base_tsc_config"], "G1 base config")
    if b0.sha256(base) != stage["base_tsc_config_sha256"]:
        raise InputIntegrityError("G1 base config hash mismatch")
    evidence: dict[str, dict[str, Any]] = {}
    for label, row in stage["prior_evidence"].items():
        path = b0.inside_root(ROOT / row["path"], f"G1 evidence {label}")
        if not path.is_file() or b0.sha256(path) != row["sha256"]:
            raise InputIntegrityError(f"G1 evidence hash mismatch: {label}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if "route" in row and payload.get("route") != row["route"]:
            raise InputIntegrityError(f"G1 evidence route mismatch: {label}")
        evidence[label] = payload
    if evidence["b0_primary"].get("passed") is not True or len(evidence["b0_primary"].get("states", ())) != 65:
        raise InputIntegrityError("G1 B0 evidence incomplete")
    if evidence["g0_result"].get("passed") is not False or evidence["g0_independent"].get("passed") is not True:
        raise InputIntegrityError("G1 G0 evidence identity changed")
    if evidence["n0_result"].get("passed") is not False or evidence["n0_independent"].get("passed") is not True:
        raise InputIntegrityError("G1 N0 evidence identity changed")
    cfg = TSCConfig.from_json(base)
    validate_one_ms_config(
        start_folder=cfg.start_folder, dt_ms=cfg.dt_ms,
        slew_a_per_ms=cfg.current_slew_a_per_ms, expected_start_folder="1000ms",
    )
    return stage, cfg, evidence["b0_primary"]


def targets(stage: dict[str, Any], cfg: TSCConfig, source: dict[str, Any]) -> dict[str, Any]:
    frozen = build_frozen_one_ms_prefixes(
        source_current_a_tsc=source["currents_a_tsc"],
        source_command_a_tsc=source["active_command_decimal_a_tsc"],
        turns_tsc=cfg.turns_tsc, min_current_a_tsc=cfg.min_current_a_tsc,
        max_current_a_tsc=cfg.max_current_a_tsc, maximum_command_delta_a=Decimal("0.299"),
    )
    q0 = frozen.q0
    center = card15_target_decimal_a(q0, cfg.turns_tsc, name="g1.q0")
    if tuple(center) != tuple(source["active_command_decimal_a_tsc"]):
        raise ContractError("G1 q0 is not the semantic source command")
    increment = Decimal(str(stage["requested_single_turn_increment_a"]))
    result: dict[str, Any] = {"level0": q0}
    for level in range(stage["minimum_cumulative_level"], stage["maximum_cumulative_level"] + 1):
        if level == 0:
            continue
        desired = [float(base + increment * level) for base in center]
        target = quantize_target(desired, cfg.turns_tsc)
        exact = card15_target_decimal_a(target, cfg.turns_tsc, name=f"g1.level{level}")
        delta = [value - base for value, base in zip(exact, center)]
        if any(value == 0 or (value > 0) != (level > 0) for value in delta):
            raise ContractError(f"G1 level {level} lost sign")
        if any(value < Decimal(str(low)) or value > Decimal(str(high))
               for value, low, high in zip(exact, cfg.min_current_a_tsc, cfg.max_current_a_tsc)):
            raise ContractError(f"G1 level {level} exceeds absolute current")
        result[f"level{level}"] = target
    maximum_adjacent = 0.0
    for depth in stage["initial_minus_depths"]:
        spec = {"kind": "hybrid", "initial_minus_depth": depth, "rollout_id": f"m{depth:02d}"}
        previous = center
        for issue, target in enumerate(sequence_for(spec, stage, result)):
            exact = card15_target_decimal_a(target, cfg.turns_tsc, name=f"g1.static.{depth}.{issue}")
            maximum_adjacent = max(maximum_adjacent, assert_exact_slew(previous, exact, name="g1.static"))
            previous = exact
    if maximum_adjacent > stage["maximum_quantized_adjacent_increment_a"]:
        raise ContractError("G1 transition exceeds frozen adjacent cap")
    columns = []
    for level in (-1, 1):
        exact = card15_target_decimal_a(result[f"level{level}"], cfg.turns_tsc, name="g1.geometry")
        columns.append([float(value - base) for value, base in zip(exact, center)])
    matrix = np.asarray(columns).T
    result["action_geometry"] = {
        "rank": int(np.linalg.matrix_rank(matrix)),
        "maximum_quantized_adjacent_increment_a": maximum_adjacent,
        "minimum_level": stage["minimum_cumulative_level"],
        "maximum_level": stage["maximum_cumulative_level"],
    }
    return result


def rollout_specs(stage: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [{"rollout_id": "matched_q0", "family_id": "matched_q0", "kind": "matched_q0",
             "depth": 0, "initial_minus_depth": 0, "repeat_index": 0,
             "data_role": "development_fit_eligible_weight_1"}]
    rows.extend({
        "rollout_id": f"m{depth:02d}_cross_p32", "family_id": f"m{depth:02d}_cross_p32",
        "kind": "even_plus", "depth": depth, "initial_minus_depth": depth,
        "repeat_index": 0, "data_role": "development_fit_eligible_weight_1",
    } for depth in stage["initial_minus_depths"])
    depth = stage["critical_replay_minus_depth"]
    rows.append({
        "rollout_id": f"m{depth:02d}_cross_p32_replay", "family_id": f"m{depth:02d}_cross_p32",
        "kind": "even_plus", "depth": depth, "initial_minus_depth": depth,
        "repeat_index": 1, "data_role": "integrity_only_zero_fit_weight",
    })
    if len(rows) != stage["rollouts"]:
        raise InputIntegrityError("G1 rollout matrix changed")
    return rows


def level_sequence(spec: dict[str, Any], stage: dict[str, Any]) -> list[int]:
    if spec["kind"] == "matched_q0":
        return [0] * stage["horizon_steps"]
    depth = spec["initial_minus_depth"]
    levels = list(range(-1, -depth - 1, -1))
    current = -depth
    while len(levels) < stage["horizon_steps"] and current < stage["final_plus_level"]:
        current = min(stage["final_plus_level"], current + stage["transition_level_increment_per_issue"])
        levels.append(current)
    levels.extend([stage["final_plus_level"]] * (stage["horizon_steps"] - len(levels)))
    return levels


def sequence_for(spec: dict[str, Any], stage: dict[str, Any], target_map: dict[str, Any]) -> list[Any]:
    return [target_map[f"level{level}"] for level in level_sequence(spec, stage)]


def action_stream(spec: dict[str, Any], stage: dict[str, Any], cfg: TSCConfig,
                  source: dict[str, Any], target_map: dict[str, Any]) -> list[dict[str, Any]]:
    previous = tuple(source["active_command_decimal_a_tsc"])
    rows = []
    for issue, target in enumerate(sequence_for(spec, stage, target_map)):
        exact = card15_target_decimal_a(target, cfg.turns_tsc, name=f"g1.{spec['rollout_id']}.{issue}")
        maximum = assert_exact_slew(previous, exact, name=f"g1.{spec['rollout_id']}.{issue}")
        rows.append({"issue_step": issue, "issue_time_ms": 1000 + issue,
                     "effect_state_index": issue + 1, "effect_time_ms": 1001 + issue,
                     "expected_card15_fields": list(target.card15_fields),
                     "maximum_issued_delta_a": maximum,
                     "scalar_level": level_sequence(spec, stage)[issue]})
        previous = exact
    return rows


def offline(config_path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []; stage = None; streams = geometry = None
    try:
        stage, cfg, _ = load(config_path); source = _source(cfg)
        signal = RGeoZGeoSignal.from_tsc_state(source)
        envelope = OneMsNR1SafetyEnvelope.from_signal(signal)
        failures.extend(envelope.state_reasons(signal, source["currents_a_tsc"],
                                                cfg.min_current_a_tsc, cfg.max_current_a_tsc))
        target_map = targets(stage, cfg, source); geometry = target_map["action_geometry"]
        streams = [{**spec, "levels": level_sequence(spec, stage),
                    "actions": action_stream(spec, stage, cfg, source, target_map)}
                   for spec in rollout_specs(stage)]
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    failures = list(dict.fromkeys(failures)); routes = (stage or {}).get("routes", {})
    return {"schema_version": SCHEMA, "kind": "offline_preflight",
            "created_utc": datetime.now(timezone.utc).isoformat(), "source_revision": source_revision,
            "passed": not failures, "route": routes.get("offline_pass") if not failures else routes.get(
                "offline_fail", "ONE_MS_NR1000G1_OFFLINE_FAIL_NO_TSC"),
            "failures": failures, "authorized_reset_calls": 6,
            "authorized_plant_advances": 384, "action_geometry": geometry,
            "rollout_action_streams": streams}


scientific_metrics = g0.scientific_metrics
compare_rows = g0.compare_rows


def run(config_path: Path, source_revision: str, output_dir: Path) -> dict[str, Any]:
    preflight = offline(config_path, source_revision)
    if not preflight["passed"]:
        raise RuntimeError("G1 offline gate failed; TSC forbidden")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {output_dir}")
    output_dir.mkdir(parents=True); b0.write_new(output_dir / "offline_preflight.json", preflight)
    stage, cfg, prior = load(config_path); cfg.run_root = output_dir / "rollouts"
    source = _source(cfg); target_map = targets(stage, cfg, source)
    envelope = OneMsNR1SafetyEnvelope.from_signal(RGeoZGeoSignal.from_tsc_state(source))
    rows: dict[str, dict[str, Any]] = {}
    for spec in rollout_specs(stage):
        row = d0._run_one(cfg, stage, spec, sequence_for(spec, stage, target_map),
                          envelope, prior["states"][0])
        rows[spec["rollout_id"]] = row; b0.write_new(output_dir / f"{spec['rollout_id']}.json", row)
        if not row["passed"]:
            break
    matched = rows.get("matched_q0", {}).get("passed") is True
    execution = len(rows) == stage["rollouts"] and all(row["passed"] for row in rows.values())
    base = f"m{stage['critical_replay_minus_depth']:02d}_cross_p32"
    replay = {"family_id": base, **compare_rows(rows[base], rows[f"{base}_replay"])} if execution else None
    replay_pass = replay is not None and replay["passed"]
    metrics = scientific_metrics(list(rows.values()), stage) if execution else None
    science = metrics is not None and metrics["passed"]
    passed = execution and matched and replay_pass and science
    route = stage["routes"]["pass"] if passed else (stage["routes"]["matched_q0_fail"] if not matched
        else stage["routes"]["execution_fail"] if not execution else stage["routes"]["replay_fail"]
        if not replay_pass else stage["routes"]["scientific_fail"])
    result = {"schema_version": SCHEMA, "kind": "authentic_fixed_1000_hybrid_radial_authority",
              "created_utc": datetime.now(timezone.utc).isoformat(), "source_revision": source_revision,
              "passed": passed, "route": route, "rollout_count": len(rows),
              "reset_calls": sum(row["reset_calls"] for row in rows.values()),
              "advance_attempts": sum(row["advance_attempts"] for row in rows.values()),
              "gotsc_calls": sum(row["gotsc_calls"] for row in rows.values()),
              "verified_plant_advances": sum(row["verified_plant_advances"] for row in rows.values()),
              "matched_q0_complete": matched, "action_geometry": target_map["action_geometry"],
              "critical_replay": replay, "scientific_metrics": metrics,
              "claim_boundary": "fixed-1000 hybrid radial Authority development only; no 2D authority, hold, recovery, model, or controller"}
    b0.write_new(output_dir / "result.json", result); return result


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("mode", choices=("offline", "run"))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--source-revision", required=True); parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(); result = offline(args.config.resolve(), args.source_revision) if args.mode == "offline" else run(
        args.config.resolve(), args.source_revision, args.output.resolve())
    if args.mode == "offline": b0.write_new(args.output.resolve(), result)
    print(json.dumps(result, indent=2, sort_keys=True)); return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
