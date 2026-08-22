#!/usr/bin/env python3
"""Fresh fixed-1000 rank-four signed Card15 action-basis campaign."""

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


SCHEMA = "rgeo-zgeo-1ms-1000-signed-basis-g3-v1"
CONFIG_SHA256 = "949677dce343770e32974283060bda1705efdbc3f56053ca540c07ad9f8b3a2e"
DEFAULT_CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_signed_basis_g3.json"
SEMANTIC_ARTIFACTS = b0.SEMANTIC_ARTIFACTS
InputIntegrityError = d0.InputIntegrityError
source_mismatch_reasons = d0.source_mismatch_reasons
compare_rows = d0.compare_rows


def load(config_path: Path) -> tuple[dict[str, Any], TSCConfig, dict[str, Any]]:
    config_path = b0.inside_root(config_path, "G3 config")
    if b0.sha256(config_path) != CONFIG_SHA256:
        raise InputIntegrityError("G3 config SHA-256 mismatch")
    stage = json.loads(config_path.read_text(encoding="utf-8"))
    exact = {
        "schema_version": SCHEMA,
        "campaign_id": "rgeo_zgeo_1ms_1000_signed_basis_g3_v1",
        "takeover_time_ms": 1000,
        "control_period_ms": 1,
        "horizon_steps": 40,
        "issue_phases": [8, 24],
        "pulse_duration_issues": 4,
        "tail_states_after_return": 12,
        "axes": ["even", "odd", "block2", "block4"],
        "signs": ["plus", "minus"],
        "primary_rollouts": 16,
        "critical_replays": ["p24_block2_plus", "p24_block4_minus"],
        "rollouts": 18,
        "maximum_reset_calls": 18,
        "maximum_advance_attempts": 720,
        "maximum_gotsc_calls": 720,
        "maximum_verified_plant_advances": 720,
        "retry_after_any_advance_attempt": "forbidden",
        "requested_single_turn_amplitude_a": 0.14,
        "maximum_quantized_single_turn_amplitude_a": 0.146,
        "design_path": "docs/codex/reports/RGEO_ZGEO_1MS_1000_SIGNED_BASIS_G3_DESIGN.md",
        "design_sha256": "d79c5ad4be9e15d5ffd309e298cce2897461638ec876eda64f5fed3b98e51483",
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise InputIntegrityError(f"G3 frozen field mismatch: {key}")
    expected_axes = {
        "even": [1] * 14,
        "odd": [1, 1, 1, -1, -1, -1, 1, -1, 1, -1, 1, -1, 1, -1],
        "block2": [1, 1, -1, -1, 1, 1, -1, -1, 1, 1, -1, -1, 1, 1],
        "block4": [1, 1, 1, 1, -1, -1, -1, -1, 1, 1, 1, 1, -1, -1],
    }
    if stage.get("axis_signs_tsc_order") != expected_axes:
        raise InputIntegrityError("G3 axis sign codes changed")
    design = b0.inside_root(ROOT / stage["design_path"], "G3 design")
    if b0.sha256(design) != stage["design_sha256"]:
        raise InputIntegrityError("G3 design hash mismatch")
    roles = stage.get("data_roles", {})
    if roles.get("primary_signed_rollouts") != "development_fit_eligible_weight_1":
        raise InputIntegrityError("G3 primary data role changed")
    if roles.get("critical_replays") != "integrity_only_zero_fit_weight":
        raise InputIntegrityError("G3 replay data role changed")
    if any(roles.get(key) != "unopened" for key in ("calibration", "holdout")):
        raise InputIntegrityError("G3 future data role changed")
    if roles.get("controller_or_recourse") != "forbidden":
        raise InputIntegrityError("G3 controller role changed")
    base = b0.inside_root(ROOT / stage["base_tsc_config"], "G3 base TSC config")
    if b0.sha256(base) != stage["base_tsc_config_sha256"]:
        raise InputIntegrityError("G3 base config hash mismatch")
    payloads: dict[str, Any] = {}
    for group in ("baseline_evidence", "prior_evidence"):
        for label, row in stage[group].items():
            path = b0.inside_root(ROOT / row["path"], f"G3 {group} {label}")
            if not path.is_file() or b0.sha256(path) != row["sha256"]:
                raise InputIntegrityError(f"G3 evidence hash mismatch: {label}")
            payload = json.loads(path.read_text(encoding="utf-8"))
            if "route" in row and payload.get("route") != row["route"]:
                raise InputIntegrityError(f"G3 evidence route mismatch: {label}")
            if "passed" in row and payload.get("passed") is not row["passed"]:
                raise InputIntegrityError(f"G3 evidence verdict mismatch: {label}")
            payloads[label] = payload
    baseline = payloads["primary"]
    if baseline.get("passed") is not True or len(baseline.get("states", ())) != 65:
        raise InputIntegrityError("G3 inherited baseline incomplete")
    if baseline.get("data_role") != "development_fit_eligible_baseline_weight_1":
        raise InputIntegrityError("G3 inherited baseline role changed")
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
    q0_decimal = card15_target_decimal_a(q0, cfg.turns_tsc, name="g3.q0")
    if tuple(q0_decimal) != tuple(source["active_command_decimal_a_tsc"]):
        raise ContractError("G3 q0 is not the semantic source command")
    amplitude = Decimal(str(stage["requested_single_turn_amplitude_a"]))
    limit = Decimal(str(stage["maximum_quantized_single_turn_amplitude_a"]))
    result: dict[str, Any] = {"q0": q0}
    positive_columns: list[list[float]] = []
    all_columns: list[list[float]] = []
    for axis in stage["axes"]:
        signs = stage["axis_signs_tsc_order"][axis]
        for sign_name, polarity in (("plus", 1), ("minus", -1)):
            desired = [float(base + amplitude * code * polarity) for base, code in zip(q0_decimal, signs)]
            target = quantize_target(desired, cfg.turns_tsc)
            exact = card15_target_decimal_a(target, cfg.turns_tsc, name=f"g3.{axis}.{sign_name}")
            delta = [value - base for value, base in zip(exact, q0_decimal)]
            if any(value == 0 or (value > 0) != (code * polarity > 0)
                   for value, code in zip(delta, signs)):
                raise ContractError(f"G3 {axis}:{sign_name} lost a signed component")
            if max(abs(value) for value in delta) > limit:
                raise ContractError(f"G3 {axis}:{sign_name} exceeds quantized amplitude")
            assert_exact_slew(q0_decimal, exact, name=f"g3.q0_to_{axis}_{sign_name}")
            if any(value < Decimal(str(low)) or value > Decimal(str(high))
                   for value, low, high in zip(exact, cfg.min_current_a_tsc, cfg.max_current_a_tsc)):
                raise ContractError(f"G3 {axis}:{sign_name} exceeds absolute current limits")
            result[f"{axis}_{sign_name}"] = target
            column = [float(value) for value in delta]
            all_columns.append(column)
            if sign_name == "plus":
                positive_columns.append(column)
    matrix = np.asarray(positive_columns, dtype=float).T
    singular = np.linalg.svd(matrix, compute_uv=False)
    rank = int(np.linalg.matrix_rank(matrix))
    if rank != 4:
        raise ContractError("G3 positive action basis is not rank four")
    condition = float(singular[0] / singular[-1])
    if condition > 1.45:
        raise ContractError("G3 positive action basis condition changed")
    result["action_geometry"] = {
        "rank": rank,
        "singular_values_a": singular.tolist(),
        "condition": condition,
        "maximum_absolute_delta_a": float(np.max(np.abs(np.asarray(all_columns)))),
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
        phase_text, axis, sign = base.split("_", 2)
        rows.append({
            "rollout_id": f"{base}_replay", "family_id": base,
            "issue_phase": int(phase_text[1:]), "axis": axis, "sign": sign,
            "repeat_index": 1, "data_role": "integrity_only_zero_fit_weight",
        })
    if len(rows) != stage["rollouts"] or len({row["rollout_id"] for row in rows}) != len(rows):
        raise InputIntegrityError("G3 rollout matrix changed")
    return rows


def sequence_for(spec: dict[str, Any], stage: dict[str, Any], target_map: dict[str, Any]) -> list[Any]:
    sequence = [target_map["q0"]] * stage["horizon_steps"]
    for issue in range(spec["issue_phase"], spec["issue_phase"] + stage["pulse_duration_issues"]):
        sequence[issue] = target_map[f"{spec['axis']}_{spec['sign']}"]
    return sequence


def action_stream(spec: dict[str, Any], stage: dict[str, Any], cfg: TSCConfig,
                  source: dict[str, Any], target_map: dict[str, Any]) -> list[dict[str, Any]]:
    previous = tuple(source["active_command_decimal_a_tsc"])
    rows = []
    for issue, target in enumerate(sequence_for(spec, stage, target_map)):
        exact = card15_target_decimal_a(target, cfg.turns_tsc, name=f"g3.{spec['rollout_id']}.{issue}")
        maximum = assert_exact_slew(previous, exact, name=f"g3.{spec['rollout_id']}.{issue}")
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
        envelope = OneMsNR1SafetyEnvelope.from_signal(RGeoZGeoSignal.from_tsc_state(source))
        failures.extend(envelope.state_reasons(
            RGeoZGeoSignal.from_tsc_state(source), source["currents_a_tsc"],
            cfg.min_current_a_tsc, cfg.max_current_a_tsc,
        ))
        target_map = targets(stage, cfg, source)
        geometry = target_map["action_geometry"]
        streams = [{**spec, "actions": action_stream(spec, stage, cfg, source, target_map)}
                   for spec in rollout_specs(stage)]
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    failures = list(dict.fromkeys(failures))
    routes = (stage or {}).get("routes", {})
    return {
        "schema_version": SCHEMA, "kind": "offline_preflight",
        "created_utc": datetime.now(timezone.utc).isoformat(), "source_revision": source_revision,
        "passed": not failures,
        "route": routes.get("offline_pass") if not failures else routes.get(
            "offline_fail", "ONE_MS_NR1000G3_OFFLINE_FAIL_NO_TSC"),
        "failures": failures, "authorized_reset_calls": 18,
        "authorized_plant_advances": 720, "action_geometry": geometry,
        "rollout_action_streams": streams,
    }


def _response(row: dict[str, Any], baseline: Sequence[dict[str, Any]]) -> np.ndarray:
    return np.asarray([
        [(state["r_geo_m"] - base["r_geo_m"]) * 1000.0,
         (state["z_geo_m"] - base["z_geo_m"]) * 1000.0,
         state["ip_a"] - base["ip_a"]]
        for state, base in zip(row["states"], baseline)
    ], dtype=float)


def _cone_metrics(columns: Sequence[np.ndarray]) -> dict[str, Any]:
    matrix = np.column_stack(columns)
    singular = np.linalg.svd(matrix, compute_uv=False)
    rank = int(np.linalg.matrix_rank(matrix))
    condition = float(singular[0] / singular[-1]) if rank == 2 and singular[-1] > 0 else math.inf
    signed = [vector for column in columns for vector in (column, -column)]
    angles = sorted((math.atan2(float(v[1]), float(v[0])) % (2 * math.pi)) for v in signed)
    gaps = [angles[(i + 1) % len(angles)] - angles[i] for i in range(len(angles) - 1)]
    gaps.append(angles[0] + 2 * math.pi - angles[-1])
    directions = [np.asarray([math.cos(2 * math.pi * i / 64), math.sin(2 * math.pi * i / 64)])
                  for i in range(64)]
    weakest = min(max(float(direction @ vector) for vector in signed) for direction in directions)
    return {
        "matrix_columns_mm": matrix.tolist(), "rank": rank,
        "singular_values_mm": singular.tolist(), "condition": condition,
        "column_norms_mm": [float(np.linalg.norm(column)) for column in columns],
        "maximum_angular_gap_deg": math.degrees(max(gaps)),
        "weakest_best_projection_mm": weakest,
    }


def scientific_metrics(primary_rows: Sequence[dict[str, Any]], baseline: Sequence[dict[str, Any]],
                       stage: dict[str, Any]) -> dict[str, Any]:
    indexed = {(row["issue_phase"], row["axis"], row["sign"]): row for row in primary_rows}
    responses = {key: _response(row, baseline) for key, row in indexed.items()}
    gates = stage["scientific_gates"]
    arms = []
    signal_pass = ip_pass = True
    for key, response in responses.items():
        phase, axis, sign = key
        h4, h8 = response[phase + 4], response[phase + 8]
        norm4, norm8 = float(np.linalg.norm(h4[:2])), float(np.linalg.norm(h8[:2]))
        arm_pass = max(norm4, norm8) >= gates["minimum_axis_max_h4_h8_rz_norm_mm"]
        arm_ip = max(abs(float(h4[2])), abs(float(h8[2]))) <= gates["maximum_h4_h8_absolute_ip_response_a"]
        signal_pass &= arm_pass
        ip_pass &= arm_ip
        arms.append({
            "rollout_id": indexed[key]["rollout_id"], "issue_phase": phase, "axis": axis, "sign": sign,
            "h4_response_rz_mm": h4[:2].tolist(), "h8_response_rz_mm": h8[:2].tolist(),
            "h4_rz_norm_mm": norm4, "h8_rz_norm_mm": norm8,
            "h4_ip_response_a": float(h4[2]), "h8_ip_response_a": float(h8[2]),
            "signal_pass": arm_pass, "ip_pass": arm_ip,
        })
    pairs = []
    pair_pass = True
    phases = []
    geometry_pass = True
    for phase in stage["issue_phases"]:
        odd_by_horizon: dict[int, list[np.ndarray]] = {4: [], 8: []}
        for axis in stage["axes"]:
            plus, minus = responses[(phase, axis, "plus")], responses[(phase, axis, "minus")]
            sep4 = float(np.linalg.norm(plus[phase + 4, :2] - minus[phase + 4, :2]))
            sep8 = float(np.linalg.norm(plus[phase + 8, :2] - minus[phase + 8, :2]))
            local = max(sep4, sep8) >= gates["minimum_signed_pair_max_h4_h8_separation_mm"]
            pair_pass &= local
            pairs.append({"issue_phase": phase, "axis": axis, "h4_separation_mm": sep4,
                          "h8_separation_mm": sep8, "passed": local})
            for horizon in (4, 8):
                odd_by_horizon[horizon].append(
                    0.5 * (plus[phase + horizon, :2] - minus[phase + horizon, :2]))
        horizons = []
        for horizon in (4, 8):
            row = {"horizon": horizon, **_cone_metrics(odd_by_horizon[horizon])}
            row["passed"] = (
                min(row["column_norms_mm"]) >= gates["minimum_each_odd_column_norm_mm"]
                and row["maximum_angular_gap_deg"] <= gates["maximum_phase_best_h4_h8_angular_gap_deg"]
                and row["weakest_best_projection_mm"] >= gates["minimum_phase_best_h4_h8_weakest_projection_mm"]
                and row["rank"] == 2
                and row["condition"] <= gates["maximum_phase_best_h4_h8_condition"]
            )
            horizons.append(row)
        local = any(row["passed"] for row in horizons)
        geometry_pass &= local
        best = max(horizons, key=lambda row: (row["passed"], row["weakest_best_projection_mm"]))
        phases.append({"issue_phase": phase, "horizons": horizons, "best": best, "passed": local})
    passed = signal_pass and pair_pass and geometry_pass and ip_pass
    return {
        "passed": passed, "signal_pass": signal_pass, "signed_pair_pass": pair_pass,
        "phase_geometry_pass": geometry_pass, "ip_pass": ip_pass,
        "arms": arms, "signed_pairs": pairs, "phases": phases,
    }


def run(config_path: Path, source_revision: str, output_dir: Path) -> dict[str, Any]:
    preflight = offline(config_path, source_revision)
    if not preflight["passed"]:
        raise RuntimeError("G3 offline gate failed; TSC forbidden")
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
        row = d0._run_one(cfg, stage, spec, sequence_for(spec, stage, target_map), envelope, baseline["states"][0])
        rows[spec["rollout_id"]] = row
        b0.write_new(output_dir / f"{spec['rollout_id']}.json", row)
        if not row["passed"]:
            break
    execution = len(rows) == stage["rollouts"] and all(row["passed"] for row in rows.values())
    replays = []
    if execution:
        for base in stage["critical_replays"]:
            replays.append({"family_id": base, **compare_rows(rows[base], rows[f"{base}_replay"])})
    replay_pass = len(replays) == len(stage["critical_replays"]) and all(row["passed"] for row in replays)
    metrics = scientific_metrics(
        [row for row in rows.values() if row["repeat_index"] == 0], baseline["states"][:41], stage
    ) if execution else None
    science = metrics is not None and metrics["passed"]
    passed = execution and replay_pass and science
    route = stage["routes"]["pass"] if passed else (
        stage["routes"]["execution_fail"] if not execution
        else stage["routes"]["replay_fail"] if not replay_pass
        else stage["routes"]["scientific_fail"]
    )
    result = {
        "schema_version": SCHEMA, "kind": "authentic_fixed_1000_rank_four_signed_basis",
        "created_utc": datetime.now(timezone.utc).isoformat(), "source_revision": source_revision,
        "passed": passed, "route": route, "rollout_count": len(rows),
        "reset_calls": sum(row["reset_calls"] for row in rows.values()),
        "advance_attempts": sum(row["advance_attempts"] for row in rows.values()),
        "gotsc_calls": sum(row["gotsc_calls"] for row in rows.values()),
        "verified_plant_advances": sum(row["verified_plant_advances"] for row in rows.values()),
        "action_geometry": target_map["action_geometry"], "critical_replays": replays,
        "scientific_metrics": metrics,
        "claim_boundary": "fixed-1000 signed action-basis development only; no model/Recourse/controller",
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
        args.config.resolve(), args.source_revision, args.output.resolve())
    if args.mode == "offline":
        b0.write_new(args.output.resolve(), result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
