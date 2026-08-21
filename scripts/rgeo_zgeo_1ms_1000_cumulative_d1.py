#!/usr/bin/env python3
"""Fixed-1000 cumulative signed temporal-response campaign."""

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


SCHEMA = "rgeo-zgeo-1ms-1000-cumulative-d1-v1"
CONFIG_SHA256 = "de1ab1d61559d451e44a08e36887f163c8266bc396d3de8b684beb979048ba96"
DEFAULT_CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_cumulative_d1.json"
SEMANTIC_ARTIFACTS = b0.SEMANTIC_ARTIFACTS


class InputIntegrityError(ValueError):
    """Frozen D1 stage or evidence identity changed."""


def load(config_path: Path) -> tuple[dict[str, Any], TSCConfig, dict[str, Any]]:
    config_path = b0.inside_root(config_path, "D1 config")
    if b0.sha256(config_path) != CONFIG_SHA256:
        raise InputIntegrityError("D1 config SHA-256 mismatch")
    stage = json.loads(config_path.read_text(encoding="utf-8"))
    exact = {
        "schema_version": SCHEMA,
        "campaign_id": "rgeo_zgeo_1ms_1000_cumulative_d1_v1",
        "takeover_time_ms": 1000,
        "control_period_ms": 1,
        "horizon_steps": 48,
        "issue_phases": [8, 24],
        "ramp_up_issues": 4,
        "plateau_issues": 4,
        "ramp_down_issues": 4,
        "tail_states_after_return": 12,
        "axes": ["even", "odd"],
        "signs": ["plus", "minus"],
        "primary_rollouts": 8,
        "critical_replays": ["p24_even_minus", "p24_odd_plus"],
        "rollouts": 10,
        "maximum_reset_calls": 10,
        "maximum_advance_attempts": 480,
        "maximum_gotsc_calls": 480,
        "maximum_verified_plant_advances": 480,
        "retry_after_any_advance_attempt": "forbidden",
        "requested_single_turn_increment_a": 0.14,
        "maximum_quantized_adjacent_increment_a": 0.21,
        "maximum_cumulative_level": 4,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise InputIntegrityError(f"frozen field mismatch: {key}")
    expected_axes = {
        "even": [1] * 14,
        "odd": [1, 1, 1, -1, -1, -1, 1, -1, 1, -1, 1, -1, 1, -1],
    }
    if stage.get("axis_signs_tsc_order") != expected_axes:
        raise InputIntegrityError("D1 axis signs changed")
    roles = stage.get("data_roles", {})
    if roles.get("critical_replays") != "integrity_only_zero_fit_weight" or any(
        roles.get(key) != "unopened" for key in ("calibration", "holdout")
    ) or roles.get("controller_or_recourse") != "forbidden":
        raise InputIntegrityError("D1 data roles changed")
    base = b0.inside_root(ROOT / stage["base_tsc_config"], "base TSC config")
    if b0.sha256(base) != stage["base_tsc_config_sha256"]:
        raise InputIntegrityError("base TSC config hash mismatch")
    payloads: dict[str, Any] = {}
    for section in ("baseline_evidence", "d0r1_evidence"):
        for label, row in stage[section].items():
            path = b0.inside_root(ROOT / row["path"], f"{section} {label}")
            if not path.is_file() or b0.sha256(path) != row["sha256"]:
                raise InputIntegrityError(f"evidence hash mismatch: {section}:{label}")
            payload = json.loads(path.read_text(encoding="utf-8"))
            if "route" in row and (payload.get("passed") is not True or payload.get("route") != row["route"]):
                raise InputIntegrityError(f"evidence route mismatch: {section}:{label}")
            payloads[f"{section}:{label}"] = payload
    baseline = payloads["baseline_evidence:primary"]
    if not baseline.get("passed") or len(baseline.get("states", ())) != 65:
        raise InputIntegrityError("B0 primary is incomplete")
    cfg = TSCConfig.from_json(base)
    validate_one_ms_config(
        start_folder=cfg.start_folder, dt_ms=cfg.dt_ms,
        slew_a_per_ms=cfg.current_slew_a_per_ms, expected_start_folder="1000ms",
    )
    return stage, cfg, baseline


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
    q0_decimal = card15_target_decimal_a(q0, cfg.turns_tsc, name="d1.q0")
    if tuple(q0_decimal) != tuple(source["active_command_decimal_a_tsc"]):
        raise ContractError("D1 q0 is not the semantic source command")
    increment = Decimal(str(stage["requested_single_turn_increment_a"]))
    adjacent_limit = Decimal(str(stage["maximum_quantized_adjacent_increment_a"]))
    result: dict[str, Any] = {"q0": q0}
    level1_deltas: list[list[float]] = []
    maximum_adjacent = Decimal("0")
    for axis in stage["axes"]:
        axis_signs = stage["axis_signs_tsc_order"][axis]
        for sign_name, polarity in (("plus", 1), ("minus", -1)):
            previous = q0_decimal
            for level in range(1, stage["maximum_cumulative_level"] + 1):
                desired = [
                    float(base + increment * level * axis_sign * polarity)
                    for base, axis_sign in zip(q0_decimal, axis_signs)
                ]
                target = quantize_target(desired, cfg.turns_tsc)
                exact = card15_target_decimal_a(
                    target, cfg.turns_tsc, name=f"d1.{axis}.{sign_name}.level{level}"
                )
                adjacent = Decimal(str(assert_exact_slew(
                    previous, exact, name=f"d1.{axis}.{sign_name}.adjacent{level}"
                )))
                maximum_adjacent = max(maximum_adjacent, adjacent)
                if adjacent > adjacent_limit:
                    raise ContractError(f"{axis}:{sign_name}:level{level} exceeds adjacent construction cap")
                if any(value < Decimal(str(low)) or value > Decimal(str(high))
                       for value, low, high in zip(exact, cfg.min_current_a_tsc, cfg.max_current_a_tsc)):
                    raise ContractError(f"{axis}:{sign_name}:level{level} exceeds absolute current limits")
                delta = [value - base for value, base in zip(exact, q0_decimal)]
                if any(value == 0 or (value > 0) != (axis_sign * polarity > 0)
                       for value, axis_sign in zip(delta, axis_signs)):
                    raise ContractError(f"{axis}:{sign_name}:level{level} lost a signed component")
                result[f"{axis}_{sign_name}_level{level}"] = target
                if level == 1:
                    level1_deltas.append([float(value) for value in delta])
                previous = exact
            assert_exact_slew(previous, card15_target_decimal_a(
                result[f"{axis}_{sign_name}_level3"], cfg.turns_tsc, name="d1.return.level3"
            ), name=f"d1.{axis}.{sign_name}.return_start")
    matrix = np.asarray(level1_deltas, dtype=float).T
    if np.linalg.matrix_rank(matrix) != 2:
        raise ContractError("D1 level-one action matrix is not rank two")
    result["action_geometry"] = {
        "rank": 2,
        "singular_values_a": np.linalg.svd(matrix, compute_uv=False).tolist(),
        "maximum_quantized_adjacent_increment_a": float(maximum_adjacent),
    }
    return result


def rollout_specs(stage: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for phase in stage["issue_phases"]:
        for axis in stage["axes"]:
            for sign in stage["signs"]:
                base = f"p{phase:02d}_{axis}_{sign}"
                rows.append({
                    "rollout_id": base, "family_id": base, "issue_phase": phase,
                    "axis": axis, "sign": sign, "repeat_index": 0,
                    "data_role": "development_fit_eligible_weight_1",
                })
    for base in stage["critical_replays"]:
        phase_text, axis, sign = base.split("_")
        rows.append({
            "rollout_id": f"{base}_replay", "family_id": base,
            "issue_phase": int(phase_text[1:]), "axis": axis, "sign": sign,
            "repeat_index": 1, "data_role": "integrity_only_zero_fit_weight",
        })
    if len(rows) != stage["rollouts"] or len({row["rollout_id"] for row in rows}) != len(rows):
        raise InputIntegrityError("D1 rollout matrix changed")
    return rows


def sequence_for(spec: dict[str, Any], stage: dict[str, Any], target_map: dict[str, Any]) -> list[Any]:
    sequence = [target_map["q0"]] * stage["horizon_steps"]
    phase = spec["issue_phase"]
    prefix = f"{spec['axis']}_{spec['sign']}_level"
    for offset, level in enumerate((1, 2, 3, 4, 4, 4, 4, 4, 3, 2, 1)):
        sequence[phase + offset] = target_map[f"{prefix}{level}"]
    sequence[phase + 11] = target_map["q0"]
    return sequence


def action_stream(
    spec: dict[str, Any], stage: dict[str, Any], cfg: TSCConfig,
    source: dict[str, Any], target_map: dict[str, Any],
) -> list[dict[str, Any]]:
    previous = tuple(source["active_command_decimal_a_tsc"])
    rows = []
    for issue, target in enumerate(sequence_for(spec, stage, target_map)):
        exact = card15_target_decimal_a(target, cfg.turns_tsc, name=f"d1.{spec['rollout_id']}.{issue}")
        maximum = assert_exact_slew(previous, exact, name=f"d1.{spec['rollout_id']}.{issue}")
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
    try:
        stage, cfg, _ = load(config_path)
        source = _source(cfg)
        envelope = OneMsNR1SafetyEnvelope.from_signal(RGeoZGeoSignal.from_tsc_state(source))
        failures.extend(envelope.state_reasons(
            RGeoZGeoSignal.from_tsc_state(source), source["currents_a_tsc"],
            cfg.min_current_a_tsc, cfg.max_current_a_tsc,
        ))
        target_map = targets(stage, cfg, source)
        geometry = target_map["action_geometry"]
        streams = [
            {**spec, "actions": action_stream(spec, stage, cfg, source, target_map)}
            for spec in rollout_specs(stage)
        ]
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
        stage = None
    failures = list(dict.fromkeys(failures))
    routes = (stage or {}).get("routes", {})
    return {
        "schema_version": SCHEMA, "kind": "offline_preflight",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_revision": source_revision, "passed": not failures,
        "route": routes.get("offline_pass") if not failures else routes.get(
            "offline_fail", "ONE_MS_NR1000D1_OFFLINE_FAIL_NO_TSC"
        ),
        "failures": failures, "authorized_reset_calls": 10,
        "authorized_plant_advances": 480, "action_geometry": geometry,
        "rollout_action_streams": streams,
    }


def _response(row: dict[str, Any], baseline: Sequence[dict[str, Any]]) -> np.ndarray:
    return np.asarray([
        [(state["r_geo_m"] - base["r_geo_m"]) * 1000.0,
         (state["z_geo_m"] - base["z_geo_m"]) * 1000.0,
         state["ip_a"] - base["ip_a"]]
        for state, base in zip(row["states"], baseline)
    ], dtype=float)


def scientific_metrics(
    primary_rows: Sequence[dict[str, Any]], baseline: Sequence[dict[str, Any]],
    stage: dict[str, Any],
) -> dict[str, Any]:
    indexed = {(row["issue_phase"], row["axis"], row["sign"]): row for row in primary_rows}
    responses = {key: _response(row, baseline) for key, row in indexed.items()}
    gates = stage["scientific_gates"]
    signal_pass = pair_pass = geometry_pass = ip_pass = tail_pass = True
    arms = []
    for key, response in responses.items():
        phase, axis, sign = key
        values = {h: response[phase + h] for h in (4, 8, 12, 16)}
        norms = {h: float(np.linalg.norm(values[h][:2])) for h in values}
        signal_pass &= max(norms[4], norms[8]) >= gates["minimum_axis_max_h4_h8_rz_norm_mm"]
        ip_pass &= max(abs(float(values[h][2])) for h in (4, 8)) <= gates[
            "maximum_h4_h8_absolute_ip_response_a"
        ]
        tail_pass &= max(norms[12], norms[16]) <= gates["maximum_h12_h16_absolute_rz_response_mm"]
        tail_pass &= max(abs(float(values[h][2])) for h in (12, 16)) <= gates[
            "maximum_h12_h16_absolute_ip_response_a"
        ]
        arms.append({
            "rollout_id": indexed[key]["rollout_id"], "issue_phase": phase,
            "axis": axis, "sign": sign,
            **{f"h{h}_response_rz_mm": values[h][:2].tolist() for h in values},
            **{f"h{h}_rz_norm_mm": norms[h] for h in norms},
            **{f"h{h}_ip_response_a": float(values[h][2]) for h in values},
        })
    pairs = []
    phases = []
    for phase in stage["issue_phases"]:
        odd_vectors: dict[int, list[np.ndarray]] = {4: [], 8: []}
        for axis in stage["axes"]:
            plus = responses[(phase, axis, "plus")]
            minus = responses[(phase, axis, "minus")]
            separation = {
                h: float(np.linalg.norm(plus[phase + h, :2] - minus[phase + h, :2]))
                for h in (4, 8)
            }
            local_pass = max(separation.values()) >= gates["minimum_signed_pair_max_h4_h8_separation_mm"]
            pair_pass &= local_pass
            pairs.append({
                "issue_phase": phase, "axis": axis,
                "h4_separation_mm": separation[4], "h8_separation_mm": separation[8],
                "passed": local_pass,
            })
            for horizon in (4, 8):
                odd_vectors[horizon].append(
                    0.5 * (plus[phase + horizon, :2] - minus[phase + horizon, :2])
                )
        horizon_rows = []
        for horizon in (4, 8):
            matrix = np.column_stack(odd_vectors[horizon])
            singular = np.linalg.svd(matrix, compute_uv=False)
            condition = float(singular[0] / singular[-1]) if singular[-1] > 0 else math.inf
            horizon_rows.append({
                "horizon": horizon, "matrix_columns_even_odd_mm": matrix.tolist(),
                "singular_values_mm": singular.tolist(), "condition": condition,
                "sigma_min_mm": float(singular[-1]),
            })
        best = min(horizon_rows, key=lambda row: row["condition"])
        local_pass = (
            best["condition"] <= gates["maximum_phase_best_h4_h8_condition"]
            and best["sigma_min_mm"] >= gates["minimum_phase_best_h4_h8_sigma_min_mm"]
        )
        geometry_pass &= local_pass
        phases.append({"issue_phase": phase, "horizons": horizon_rows, "best": best, "passed": local_pass})
    passed = signal_pass and pair_pass and geometry_pass and ip_pass and tail_pass
    return {
        "passed": passed, "signal_pass": signal_pass, "signed_pair_pass": pair_pass,
        "phase_geometry_pass": geometry_pass, "ip_pass": ip_pass,
        "return_tail_pass": tail_pass, "arms": arms, "signed_pairs": pairs,
        "phases": phases,
    }


def run(config_path: Path, source_revision: str, output_dir: Path) -> dict[str, Any]:
    preflight = offline(config_path, source_revision)
    if not preflight["passed"]:
        raise RuntimeError("D1 offline gate failed; TSC forbidden")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {output_dir}")
    output_dir.mkdir(parents=True)
    b0.write_new(output_dir / "offline_preflight.json", preflight)
    stage, cfg, baseline = load(config_path)
    cfg.run_root = output_dir / "rollouts"
    source = _source(cfg)
    target_map = targets(stage, cfg, source)
    envelope = OneMsNR1SafetyEnvelope.from_signal(RGeoZGeoSignal.from_tsc_state(source))
    rows: dict[str, dict[str, Any]] = {}
    for spec in rollout_specs(stage):
        row = d0._run_one(
            cfg, stage, spec, sequence_for(spec, stage, target_map), envelope,
            baseline["states"][0],
        )
        rows[spec["rollout_id"]] = row
        b0.write_new(output_dir / f"{spec['rollout_id']}.json", row)
        if not row["passed"]:
            break
    execution_pass = len(rows) == stage["rollouts"] and all(row["passed"] for row in rows.values())
    replay_rows = []
    if execution_pass:
        for family in stage["critical_replays"]:
            replay_rows.append({
                "family_id": family, **d0.compare_rows(rows[family], rows[f"{family}_replay"])
            })
    replay_pass = len(replay_rows) == 2 and all(row["passed"] for row in replay_rows)
    metrics = None
    if execution_pass:
        metrics = scientific_metrics(
            [row for row in rows.values() if row["repeat_index"] == 0],
            baseline["states"][:49], stage,
        )
    scientific_pass = metrics is not None and metrics["passed"]
    passed = execution_pass and replay_pass and scientific_pass
    route = stage["routes"]["pass"] if passed else (
        stage["routes"]["execution_fail"] if not execution_pass
        else stage["routes"]["replay_fail"] if not replay_pass
        else stage["routes"]["scientific_fail"]
    )
    result = {
        "schema_version": SCHEMA,
        "kind": "authentic_fixed_1000_cumulative_temporal_development",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_revision": source_revision, "passed": passed, "route": route,
        "rollout_count": len(rows),
        "reset_calls": sum(row["reset_calls"] for row in rows.values()),
        "advance_attempts": sum(row["advance_attempts"] for row in rows.values()),
        "gotsc_calls": sum(row["gotsc_calls"] for row in rows.values()),
        "verified_plant_advances": sum(row["verified_plant_advances"] for row in rows.values()),
        "action_geometry": target_map["action_geometry"],
        "critical_replays": replay_rows, "scientific_metrics": metrics,
        "claim_boundary": "fixed-1000 cumulative temporal development only; no hold/recovery/control",
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
