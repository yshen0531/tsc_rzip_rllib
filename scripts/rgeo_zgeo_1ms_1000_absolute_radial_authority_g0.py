#!/usr/bin/env python3
"""Fixed-1000 matched-q0 absolute radial Authority G0 campaign."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
import json
import math
from pathlib import Path
import sys
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_1000_baseline_b0 as b0  # noqa: E402
from scripts import rgeo_zgeo_1ms_1000_signed_temporal_d0 as d0  # noqa: E402
from scripts.rgeo_zgeo_1ms_nr1_qualification import _source  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    OneMsNR1SafetyEnvelope,
    assert_exact_slew,
    build_frozen_one_ms_prefixes,
    card15_target_decimal_a,
    quantize_target,
    validate_one_ms_config,
)
from tsc_rzip_rllib.control.rgeo_zgeo_contract import ContractError, RGeoZGeoSignal  # noqa: E402
from tsc_rzip_rllib.core.runner import TSCConfig  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-1000-absolute-radial-authority-g0-v1"
CONFIG_SHA256 = "ecdf6f18229d0ed79477f95c434bc5d1b96a4508b699f44b9a7eac9f27bb4438"
DEFAULT_CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_absolute_radial_authority_g0.json"
SEMANTIC_ARTIFACTS = b0.SEMANTIC_ARTIFACTS


class InputIntegrityError(ValueError):
    """Frozen G0 identity or its evidence changed."""


def load(config_path: Path) -> tuple[dict[str, Any], TSCConfig, dict[str, Any]]:
    config_path = b0.inside_root(config_path, "G0 config")
    if b0.sha256(config_path) != CONFIG_SHA256:
        raise InputIntegrityError("G0 config SHA-256 mismatch")
    stage = json.loads(config_path.read_text(encoding="utf-8"))
    exact = {
        "schema_version": SCHEMA,
        "campaign_id": "rgeo_zgeo_1ms_1000_absolute_radial_authority_g0_v1",
        "takeover_time_ms": 1000,
        "control_period_ms": 1,
        "horizon_steps": 64,
        "candidate_depths": [4, 8, 12, 16, 24, 32],
        "critical_replay_depth": 16,
        "rollouts": 8,
        "maximum_reset_calls": 8,
        "maximum_advance_attempts": 512,
        "maximum_gotsc_calls": 512,
        "maximum_verified_plant_advances": 512,
        "retry_after_any_advance_attempt": "forbidden",
        "requested_single_turn_increment_a": 0.14,
        "maximum_quantized_adjacent_increment_a": 0.21,
        "maximum_cumulative_level": 32,
        "terminal_state_start": 56,
        "terminal_state_end": 64,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise InputIntegrityError(f"frozen field mismatch: {key}")
    if stage.get("axis_signs_tsc_order") != {"even": [1] * 14}:
        raise InputIntegrityError("G0 even coordinate changed")
    roles = stage.get("data_roles", {})
    if roles.get("matched_q0") != "development_fit_eligible_weight_1":
        raise InputIntegrityError("G0 matched-q0 role changed")
    if roles.get("primary_candidates") != "development_fit_eligible_weight_1":
        raise InputIntegrityError("G0 candidate role changed")
    if roles.get("critical_replay") != "integrity_only_zero_fit_weight":
        raise InputIntegrityError("G0 replay role changed")
    if any(roles.get(key) != "unopened" for key in ("calibration", "holdout")):
        raise InputIntegrityError("G0 fresh data role changed")
    if roles.get("controller_or_recourse") != "forbidden":
        raise InputIntegrityError("G0 controller role changed")
    base = b0.inside_root(ROOT / stage["base_tsc_config"], "G0 base TSC config")
    if b0.sha256(base) != stage["base_tsc_config_sha256"]:
        raise InputIntegrityError("G0 base config hash mismatch")
    evidence: dict[str, dict[str, Any]] = {}
    for label, row in stage["prior_evidence"].items():
        path = b0.inside_root(ROOT / row["path"], f"G0 evidence {label}")
        if not path.is_file() or b0.sha256(path) != row["sha256"]:
            raise InputIntegrityError(f"G0 evidence hash mismatch: {label}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if "route" in row and payload.get("route") != row["route"]:
            raise InputIntegrityError(f"G0 evidence route mismatch: {label}")
        evidence[label] = payload
    if evidence["b0_primary"].get("passed") is not True or len(
        evidence["b0_primary"].get("states", ())
    ) != 65:
        raise InputIntegrityError("G0 B0 evidence incomplete")
    if evidence["b0_result"].get("passed") is not True:
        raise InputIntegrityError("G0 B0 result is not PASS")
    if evidence["d1_result"].get("passed") is not True or evidence["d1_independent"].get("passed") is not True:
        raise InputIntegrityError("G0 D1 prerequisite is not PASS")
    if evidence["n0_result"].get("passed") is not False or evidence["n0_independent"].get("passed") is not True:
        raise InputIntegrityError("G0 N0 evidence identity changed")
    cfg = TSCConfig.from_json(base)
    validate_one_ms_config(
        start_folder=cfg.start_folder,
        dt_ms=cfg.dt_ms,
        slew_a_per_ms=cfg.current_slew_a_per_ms,
        expected_start_folder="1000ms",
    )
    return stage, cfg, evidence["b0_primary"]


def targets(stage: dict[str, Any], cfg: TSCConfig, source: dict[str, Any]) -> dict[str, Any]:
    frozen = build_frozen_one_ms_prefixes(
        source_current_a_tsc=source["currents_a_tsc"],
        source_command_a_tsc=source["active_command_decimal_a_tsc"],
        turns_tsc=cfg.turns_tsc,
        min_current_a_tsc=cfg.min_current_a_tsc,
        max_current_a_tsc=cfg.max_current_a_tsc,
        maximum_command_delta_a=Decimal("0.299"),
    )
    q0 = frozen.q0
    q0_decimal = card15_target_decimal_a(q0, cfg.turns_tsc, name="g0.q0")
    if tuple(q0_decimal) != tuple(source["active_command_decimal_a_tsc"]):
        raise ContractError("G0 q0 is not the semantic source command")
    increment = Decimal(str(stage["requested_single_turn_increment_a"]))
    adjacent_cap = Decimal(str(stage["maximum_quantized_adjacent_increment_a"]))
    result: dict[str, Any] = {"q0": q0}
    previous = q0_decimal
    maximum_adjacent = Decimal("0")
    level_one_delta: list[float] | None = None
    for level in range(1, stage["maximum_cumulative_level"] + 1):
        desired = [float(base + increment * level) for base in q0_decimal]
        target = quantize_target(desired, cfg.turns_tsc)
        exact = card15_target_decimal_a(target, cfg.turns_tsc, name=f"g0.even_plus.level{level}")
        adjacent = Decimal(str(assert_exact_slew(previous, exact, name=f"g0.adjacent{level}")))
        maximum_adjacent = max(maximum_adjacent, adjacent)
        if adjacent > adjacent_cap:
            raise ContractError(f"G0 level {level} exceeds adjacent cap")
        if any(value < Decimal(str(low)) or value > Decimal(str(high))
               for value, low, high in zip(exact, cfg.min_current_a_tsc, cfg.max_current_a_tsc)):
            raise ContractError(f"G0 level {level} exceeds an absolute current limit")
        delta = [value - base for value, base in zip(exact, q0_decimal)]
        if any(value <= 0 for value in delta):
            raise ContractError(f"G0 level {level} lost even-plus sign")
        if level == 1:
            level_one_delta = [float(value) for value in delta]
        result[f"level{level}"] = target
        previous = exact
    if level_one_delta is None:
        raise ContractError("G0 level-one coordinate missing")
    result["action_geometry"] = {
        "rank": int(np.linalg.matrix_rank(np.asarray(level_one_delta)[:, None])),
        "maximum_level": stage["maximum_cumulative_level"],
        "maximum_quantized_adjacent_increment_a": float(maximum_adjacent),
        "level_one_l2_a": float(np.linalg.norm(np.asarray(level_one_delta))),
        "terminal_offset_l2_a": float(np.linalg.norm(np.asarray(
            [float(value - base) for value, base in zip(previous, q0_decimal)]
        ))),
        "terminal_offset_linf_a": float(max(
            abs(value - base) for value, base in zip(previous, q0_decimal)
        )),
    }
    return result


def rollout_specs(stage: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [{
        "rollout_id": "matched_q0", "family_id": "matched_q0", "kind": "matched_q0",
        "depth": 0, "repeat_index": 0, "data_role": "development_fit_eligible_weight_1",
    }]
    rows.extend({
        "rollout_id": f"depth{depth:02d}", "family_id": f"depth{depth:02d}",
        "kind": "even_plus", "depth": depth, "repeat_index": 0,
        "data_role": "development_fit_eligible_weight_1",
    } for depth in stage["candidate_depths"])
    depth = stage["critical_replay_depth"]
    rows.append({
        "rollout_id": f"depth{depth:02d}_replay", "family_id": f"depth{depth:02d}",
        "kind": "even_plus", "depth": depth, "repeat_index": 1,
        "data_role": "integrity_only_zero_fit_weight",
    })
    if len(rows) != stage["rollouts"] or len({row["rollout_id"] for row in rows}) != len(rows):
        raise InputIntegrityError("G0 rollout matrix changed")
    return rows


def sequence_for(spec: dict[str, Any], stage: dict[str, Any], target_map: dict[str, Any]) -> list[Any]:
    if spec["kind"] == "matched_q0":
        return [target_map["q0"]] * stage["horizon_steps"]
    depth = spec["depth"]
    return [target_map[f"level{min(issue + 1, depth)}"] for issue in range(stage["horizon_steps"])]


def action_stream(
    spec: dict[str, Any], stage: dict[str, Any], cfg: TSCConfig,
    source: dict[str, Any], target_map: dict[str, Any],
) -> list[dict[str, Any]]:
    previous = tuple(source["active_command_decimal_a_tsc"])
    rows = []
    for issue, target in enumerate(sequence_for(spec, stage, target_map)):
        exact = card15_target_decimal_a(target, cfg.turns_tsc, name=f"g0.{spec['rollout_id']}.{issue}")
        maximum = assert_exact_slew(previous, exact, name=f"g0.{spec['rollout_id']}.{issue}")
        rows.append({
            "issue_step": issue, "issue_time_ms": 1000 + issue,
            "effect_state_index": issue + 1, "effect_time_ms": 1001 + issue,
            "expected_card15_fields": list(target.card15_fields),
            "maximum_issued_delta_a": maximum,
        })
        previous = exact
    return rows


def offline(config_path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    streams = geometry = None
    stage = None
    try:
        stage, cfg, _ = load(config_path)
        source = _source(cfg)
        signal = RGeoZGeoSignal.from_tsc_state(source)
        envelope = OneMsNR1SafetyEnvelope.from_signal(signal)
        failures.extend(envelope.state_reasons(
            signal, source["currents_a_tsc"], cfg.min_current_a_tsc, cfg.max_current_a_tsc,
        ))
        target_map = targets(stage, cfg, source)
        geometry = target_map["action_geometry"]
        streams = [
            {**spec, "actions": action_stream(spec, stage, cfg, source, target_map)}
            for spec in rollout_specs(stage)
        ]
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    failures = list(dict.fromkeys(failures))
    routes = (stage or {}).get("routes", {})
    return {
        "schema_version": SCHEMA, "kind": "offline_preflight",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_revision": source_revision, "passed": not failures,
        "route": routes.get("offline_pass") if not failures else routes.get(
            "offline_fail", "ONE_MS_NR1000G0_OFFLINE_FAIL_NO_TSC"
        ),
        "failures": failures, "authorized_reset_calls": 8,
        "authorized_plant_advances": 512, "action_geometry": geometry,
        "rollout_action_streams": streams,
    }


def _window_metrics(states: Sequence[dict[str, Any]], start: int, end: int) -> dict[str, float]:
    source = states[0]
    window = states[start:end + 1]
    distances = [1000.0 * math.hypot(
        row["r_geo_m"] - source["r_geo_m"], row["z_geo_m"] - source["z_geo_m"]
    ) for row in window]
    speeds = [math.hypot(
        states[index]["r_geo_m"] - states[index - 1]["r_geo_m"],
        states[index]["z_geo_m"] - states[index - 1]["z_geo_m"],
    ) / 0.001 for index in range(start + 1, end + 1)]
    ip_fractions = [abs(row["ip_a"] - source["ip_a"]) / abs(source["ip_a"]) for row in window]
    return {
        "maximum_source_distance_mm": max(distances),
        "maximum_speed_m_per_s": max(speeds),
        "maximum_ip_source_fraction": max(ip_fractions),
    }


def scientific_metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    by_id = {row["rollout_id"]: row for row in rows}
    baseline = _window_metrics(
        by_id["matched_q0"]["states"], stage["terminal_state_start"], stage["terminal_state_end"],
    )
    gates = stage["scientific_gates"]
    candidates = []
    for row in rows:
        if row["kind"] != "even_plus" or row["repeat_index"] != 0:
            continue
        metrics = _window_metrics(row["states"], stage["terminal_state_start"], stage["terminal_state_end"])
        distance_gain = 1.0 - metrics["maximum_source_distance_mm"] / baseline["maximum_source_distance_mm"]
        speed_gain = baseline["maximum_speed_m_per_s"] - metrics["maximum_speed_m_per_s"]
        utility_pass = (
            distance_gain >= gates["minimum_terminal_worst_source_distance_improvement_fraction"]
            and speed_gain >= gates["minimum_terminal_max_speed_improvement_m_per_s"]
            and metrics["maximum_ip_source_fraction"] <= gates["maximum_terminal_ip_source_fraction"]
        )
        capture = (
            metrics["maximum_source_distance_mm"] <= gates["capture_source_distance_mm_diagnostic_only"]
            and metrics["maximum_speed_m_per_s"] <= gates["capture_speed_m_per_s_diagnostic_only"]
            and metrics["maximum_ip_source_fraction"] <= gates["maximum_terminal_ip_source_fraction"]
        )
        candidates.append({
            "rollout_id": row["rollout_id"], "depth": row["depth"], **metrics,
            "source_distance_improvement_fraction": distance_gain,
            "speed_improvement_m_per_s": speed_gain,
            "utility_pass": utility_pass, "capture_diagnostic_pass": capture,
        })
    best = min(candidates, key=lambda row: max(
        row["maximum_source_distance_mm"] / 5.0,
        row["maximum_speed_m_per_s"] / 0.1,
        row["maximum_ip_source_fraction"] / 0.05,
    ))
    eligible = [row for row in candidates if row["utility_pass"]]
    return {
        "passed": bool(eligible), "matched_q0_terminal": baseline,
        "candidates": candidates, "best_candidate": best,
        "selected_eligible_candidate": min(eligible, key=lambda row: max(
            row["maximum_source_distance_mm"] / 5.0,
            row["maximum_speed_m_per_s"] / 0.1,
            row["maximum_ip_source_fraction"] / 0.05,
        )) if eligible else None,
        "capture_diagnostic_any": any(row["capture_diagnostic_pass"] for row in candidates),
    }


def compare_rows(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    comparison = d0.compare_rows(left, right)
    failures = [reason for reason in comparison["failures"] if reason not in ("STATE_COUNT", "ACTION_COUNT")]
    if len(left["states"]) != 65 or len(right["states"]) != 65:
        failures.append("STATE_COUNT")
    if len(left["actions"]) != 64 or len(right["actions"]) != 64:
        failures.append("ACTION_COUNT")
    comparison["failures"] = list(dict.fromkeys(failures))
    comparison["passed"] = not comparison["failures"]
    return comparison


def run(config_path: Path, source_revision: str, output_dir: Path) -> dict[str, Any]:
    preflight = offline(config_path, source_revision)
    if not preflight["passed"]:
        raise RuntimeError("G0 offline gate failed; TSC forbidden")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {output_dir}")
    output_dir.mkdir(parents=True)
    b0.write_new(output_dir / "offline_preflight.json", preflight)
    stage, cfg, prior_baseline = load(config_path)
    cfg.run_root = output_dir / "rollouts"
    source = _source(cfg)
    target_map = targets(stage, cfg, source)
    envelope = OneMsNR1SafetyEnvelope.from_signal(RGeoZGeoSignal.from_tsc_state(source))
    rows: dict[str, dict[str, Any]] = {}
    for spec in rollout_specs(stage):
        row = d0._run_one(
            cfg, stage, spec, sequence_for(spec, stage, target_map), envelope, prior_baseline["states"][0],
        )
        rows[spec["rollout_id"]] = row
        b0.write_new(output_dir / f"{spec['rollout_id']}.json", row)
        if not row["passed"]:
            break
    matched_q0_complete = rows.get("matched_q0", {}).get("passed") is True
    execution_pass = len(rows) == stage["rollouts"] and all(row["passed"] for row in rows.values())
    base = f"depth{stage['critical_replay_depth']:02d}"
    replay = {"family_id": base, **compare_rows(rows[base], rows[f"{base}_replay"])} \
        if execution_pass else None
    replay_pass = replay is not None and replay["passed"]
    metrics = scientific_metrics(list(rows.values()), stage) if execution_pass else None
    scientific_pass = metrics is not None and metrics["passed"]
    passed = execution_pass and matched_q0_complete and replay_pass and scientific_pass
    route = stage["routes"]["pass"] if passed else (
        stage["routes"]["matched_q0_fail"] if not matched_q0_complete
        else stage["routes"]["execution_fail"] if not execution_pass
        else stage["routes"]["replay_fail"] if not replay_pass
        else stage["routes"]["scientific_fail"]
    )
    result = {
        "schema_version": SCHEMA,
        "kind": "authentic_fixed_1000_absolute_radial_authority_development",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_revision": source_revision, "passed": passed, "route": route,
        "rollout_count": len(rows),
        "reset_calls": sum(row["reset_calls"] for row in rows.values()),
        "advance_attempts": sum(row["advance_attempts"] for row in rows.values()),
        "gotsc_calls": sum(row["gotsc_calls"] for row in rows.values()),
        "verified_plant_advances": sum(row["verified_plant_advances"] for row in rows.values()),
        "matched_q0_complete": matched_q0_complete,
        "action_geometry": target_map["action_geometry"],
        "critical_replay": replay, "scientific_metrics": metrics,
        "claim_boundary": "fixed-1000 absolute radial Authority development only; no 2D authority, hold, recovery, model, or controller",
    }
    b0.write_new(output_dir / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("offline", "run"))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = offline(args.config.resolve(), args.source_revision) if args.mode == "offline" else run(
        args.config.resolve(), args.source_revision, args.output.resolve()
    )
    if args.mode == "offline":
        b0.write_new(args.output.resolve(), result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
