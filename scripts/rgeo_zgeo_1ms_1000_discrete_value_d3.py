#!/usr/bin/env python3
"""Fixed-1000 support-gated discrete candidate-value development campaign."""

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
from scripts import rgeo_zgeo_1ms_1000_cumulative_d1 as d1  # noqa: E402
from scripts import rgeo_zgeo_1ms_1000_signed_basis_g3 as g3  # noqa: E402
from scripts import rgeo_zgeo_1ms_1000_signed_temporal_d0 as d0  # noqa: E402
from scripts.rgeo_zgeo_1ms_nr1_qualification import _source  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    OneMsNR1SafetyEnvelope, assert_exact_slew, build_frozen_one_ms_prefixes,
    card15_target_decimal_a, quantize_target,
)
from tsc_rzip_rllib.control.rgeo_zgeo_contract import ContractError, RGeoZGeoSignal  # noqa: E402
from tsc_rzip_rllib.core.runner import TSCConfig  # noqa: E402

SCHEMA = "rgeo-zgeo-1ms-1000-discrete-value-d3-v1"
CONFIG_SHA256 = "86d9c4f8773013d58ad3cb168146af9ed5fda0d5a629694711c053615f4af037"
DEFAULT_CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_discrete_value_d3.json"
SEMANTIC_ARTIFACTS = b0.SEMANTIC_ARTIFACTS


class InputIntegrityError(ValueError):
    """Frozen D3 identity or evidence changed."""


def load(config_path: Path) -> tuple[dict[str, Any], TSCConfig, dict[str, Any]]:
    config_path = b0.inside_root(config_path, "D3 config")
    if b0.sha256(config_path) != CONFIG_SHA256:
        raise InputIntegrityError("D3 config SHA-256 mismatch")
    stage = json.loads(config_path.read_text(encoding="utf-8"))
    exact = {
        "schema_version": SCHEMA, "campaign_id": "rgeo_zgeo_1ms_1000_discrete_value_d3_v1",
        "takeover_time_ms": 1000, "control_period_ms": 1, "horizon_steps": 48,
        "conditioner_issue_phase": 8, "candidate_issue_phase": 24,
        "macro_levels": [1,2,3,4,4,4,4,4,3,2,1,0],
        "conditioners": ["block4_plus", "block4_minus"],
        "candidates": ["baseline", "even_plus", "even_minus", "odd_plus", "odd_minus", "block4_plus", "block4_minus"],
        "axes": ["even", "odd", "block4"], "primary_rollouts": 14,
        "critical_replays": ["c_block4_plus__block4_minus", "c_block4_minus__even_plus"],
        "rollouts": 16, "maximum_reset_calls": 16, "maximum_advance_attempts": 768,
        "maximum_gotsc_calls": 768, "maximum_verified_plant_advances": 768,
        "retry_after_any_advance_attempt": "forbidden", "requested_single_turn_increment_a": 0.14,
        "maximum_quantized_adjacent_increment_a": 0.21, "maximum_cumulative_level": 4,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise InputIntegrityError(f"frozen D3 field mismatch: {key}")
    expected_axes = {
        "even": [1]*14,
        "odd": [1,1,1,-1,-1,-1,1,-1,1,-1,1,-1,1,-1],
        "block4": [1,1,1,1,-1,-1,-1,-1,1,1,1,1,-1,-1],
    }
    if stage.get("axis_signs_tsc_order") != expected_axes:
        raise InputIntegrityError("D3 axis signs changed")
    expected_roles = {
        "primary_rows": "development_fit_eligible_weight_1",
        "critical_replays": "integrity_only_zero_fit_weight",
        "g3_block2": "retained_negative_development_label_not_rerun",
        "calibration": "unopened", "holdout": "unopened",
        "controller_or_recourse": "forbidden", "fixed_1100_data": "forbidden",
    }
    if stage.get("data_roles") != expected_roles:
        raise InputIntegrityError("D3 data roles changed")
    for path_key, sha_key in (
        ("design_path", "design_sha256"), ("base_tsc_config", "base_tsc_config_sha256"),
        ("baseline_primary_path", "baseline_primary_sha256"),
        ("g3_result_path", "g3_result_sha256"), ("g3_independent_path", "g3_independent_sha256"),
    ):
        path = b0.inside_root(ROOT / stage[path_key], f"D3 {path_key}")
        if b0.sha256(path) != stage[sha_key]:
            raise InputIntegrityError(f"D3 evidence hash mismatch: {path_key}")
    g3_result = json.loads((ROOT / stage["g3_result_path"]).read_text(encoding="utf-8"))
    g3_audit = json.loads((ROOT / stage["g3_independent_path"]).read_text(encoding="utf-8"))
    if g3_result.get("route") != "ONE_MS_NR1000G3_SIGNED_ACTION_BASIS_INSUFFICIENT_ARCHITECTURE_REDESIGN":
        raise InputIntegrityError("G3 final FAIL route changed")
    if g3_audit.get("passed") is not True or g3_audit.get("primary_scientific_passed") is not False:
        raise InputIntegrityError("G3 independent boundary changed")
    _, cfg, baseline = d1.load(ROOT / "configs/rgeo_zgeo_1ms_1000_cumulative_d1.json")
    if b0.sha256(ROOT / stage["base_tsc_config"]) != stage["base_tsc_config_sha256"]:
        raise InputIntegrityError("D3 base config changed")
    return stage, cfg, baseline


def targets(stage: dict[str, Any], cfg: TSCConfig, source: dict[str, Any]) -> dict[str, Any]:
    frozen = build_frozen_one_ms_prefixes(
        source_current_a_tsc=source["currents_a_tsc"],
        source_command_a_tsc=source["active_command_decimal_a_tsc"], turns_tsc=cfg.turns_tsc,
        min_current_a_tsc=cfg.min_current_a_tsc, max_current_a_tsc=cfg.max_current_a_tsc,
        maximum_command_delta_a=Decimal("0.299"),
    )
    q0 = frozen.q0
    q0_decimal = card15_target_decimal_a(q0, cfg.turns_tsc, name="d3.q0")
    if tuple(q0_decimal) != tuple(source["active_command_decimal_a_tsc"]):
        raise ContractError("D3 q0 changed")
    increment = Decimal(str(stage["requested_single_turn_increment_a"]))
    adjacent_cap = Decimal(str(stage["maximum_quantized_adjacent_increment_a"]))
    result: dict[str, Any] = {"q0": q0}
    level1_columns: list[list[float]] = []
    maximum_adjacent = Decimal("0")
    for axis in stage["axes"]:
        code = stage["axis_signs_tsc_order"][axis]
        for sign, polarity in (("plus", 1), ("minus", -1)):
            previous = q0_decimal
            for level in range(1, stage["maximum_cumulative_level"] + 1):
                desired = [float(base + increment*level*c*polarity) for base, c in zip(q0_decimal, code)]
                target = quantize_target(desired, cfg.turns_tsc)
                exact = card15_target_decimal_a(target, cfg.turns_tsc, name=f"d3.{axis}.{sign}.l{level}")
                adjacent = Decimal(str(assert_exact_slew(previous, exact, name=f"d3.{axis}.{sign}.l{level}")))
                maximum_adjacent = max(maximum_adjacent, adjacent)
                if adjacent > adjacent_cap:
                    raise ContractError(f"D3 {axis}:{sign}:level{level} exceeds adjacent cap")
                if any(v < Decimal(str(lo)) or v > Decimal(str(hi))
                       for v, lo, hi in zip(exact, cfg.min_current_a_tsc, cfg.max_current_a_tsc)):
                    raise ContractError(f"D3 {axis}:{sign}:level{level} exceeds current limits")
                delta = [v-base for v, base in zip(exact, q0_decimal)]
                if any(v == 0 or (v > 0) != (c*polarity > 0) for v, c in zip(delta, code)):
                    raise ContractError(f"D3 {axis}:{sign}:level{level} lost signed component")
                result[f"{axis}_{sign}_level{level}"] = target
                if level == 1 and sign == "plus":
                    level1_columns.append([float(v) for v in delta])
                previous = exact
    matrix = np.asarray(level1_columns, dtype=float).T
    singular = np.linalg.svd(matrix, compute_uv=False)
    rank = int(np.linalg.matrix_rank(matrix))
    if rank != 3:
        raise ContractError("D3 candidate input span is not rank three")
    result["action_geometry"] = {
        "rank": rank, "singular_values_a": singular.tolist(),
        "condition": float(singular[0]/singular[-1]),
        "maximum_quantized_adjacent_increment_a": float(maximum_adjacent),
    }
    return result


def rollout_specs(stage: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for conditioner in stage["conditioners"]:
        for candidate in stage["candidates"]:
            base = f"c_{conditioner}__{candidate}"
            rows.append({"rollout_id": base, "family_id": base, "conditioner": conditioner,
                         "candidate": candidate, "repeat_index": 0,
                         "data_role": "development_fit_eligible_weight_1"})
    for base in stage["critical_replays"]:
        conditioner, candidate = base[2:].split("__")
        rows.append({"rollout_id": f"{base}_replay", "family_id": base,
                     "conditioner": conditioner, "candidate": candidate, "repeat_index": 1,
                     "data_role": "integrity_only_zero_fit_weight"})
    if len(rows) != stage["rollouts"] or len({r["rollout_id"] for r in rows}) != len(rows):
        raise InputIntegrityError("D3 rollout matrix changed")
    return rows


def _apply_macro(sequence: list[Any], phase: int, label: str, stage: dict[str, Any], target_map: dict[str, Any]) -> None:
    prefix = f"{label}_level"
    for offset, level in enumerate(stage["macro_levels"]):
        sequence[phase+offset] = target_map["q0"] if level == 0 else target_map[f"{prefix}{level}"]


def sequence_for(spec: dict[str, Any], stage: dict[str, Any], target_map: dict[str, Any]) -> list[Any]:
    sequence = [target_map["q0"]] * stage["horizon_steps"]
    _apply_macro(sequence, stage["conditioner_issue_phase"], spec["conditioner"], stage, target_map)
    if spec["candidate"] != "baseline":
        _apply_macro(sequence, stage["candidate_issue_phase"], spec["candidate"], stage, target_map)
    return sequence


def action_stream(spec: dict[str, Any], stage: dict[str, Any], cfg: TSCConfig,
                  source: dict[str, Any], target_map: dict[str, Any]) -> list[dict[str, Any]]:
    active = tuple(source["active_command_decimal_a_tsc"])
    rows = []
    for issue, target in enumerate(sequence_for(spec, stage, target_map)):
        exact = card15_target_decimal_a(target, cfg.turns_tsc, name=f"d3.{spec['rollout_id']}.{issue}")
        maximum = assert_exact_slew(active, exact, name=f"d3.{spec['rollout_id']}.{issue}")
        rows.append({"issue_step": issue, "issue_time_ms": 1000+issue,
                     "effect_state_index": issue+1, "effect_time_ms": 1001+issue,
                     "expected_card15_fields": list(target.card15_fields),
                     "maximum_issued_delta_a": maximum})
        active = exact
    return rows


def offline(config_path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    streams = geometry = None
    try:
        stage, cfg, _ = load(config_path)
        source = _source(cfg)
        envelope = OneMsNR1SafetyEnvelope.from_signal(RGeoZGeoSignal.from_tsc_state(source))
        failures.extend(envelope.state_reasons(RGeoZGeoSignal.from_tsc_state(source),
                                                source["currents_a_tsc"], cfg.min_current_a_tsc,
                                                cfg.max_current_a_tsc))
        target_map = targets(stage, cfg, source)
        geometry = target_map["action_geometry"]
        streams = [{**spec, "actions": action_stream(spec, stage, cfg, source, target_map)}
                   for spec in rollout_specs(stage)]
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
        stage = None
    failures = list(dict.fromkeys(failures))
    routes = (stage or {}).get("routes", {})
    return {"schema_version": SCHEMA, "kind": "offline_preflight",
            "created_utc": datetime.now(timezone.utc).isoformat(), "source_revision": source_revision,
            "passed": not failures,
            "route": routes.get("offline_pass") if not failures else routes.get("offline_fail", "ONE_MS_NR1000D3_OFFLINE_FAIL_NO_TSC"),
            "failures": failures, "authorized_reset_calls": 16,
            "authorized_plant_advances": 768, "action_geometry": geometry,
            "rollout_action_streams": streams}


def _response(row: dict[str, Any], matched: dict[str, Any]) -> np.ndarray:
    return np.asarray([[(s["r_geo_m"]-b["r_geo_m"])*1000.0,
                        (s["z_geo_m"]-b["z_geo_m"])*1000.0, s["ip_a"]-b["ip_a"]]
                       for s, b in zip(row["states"], matched["states"])], dtype=float)


def scientific_metrics(primary_rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    indexed = {(r["conditioner"], r["candidate"]): r for r in primary_rows}
    phase, gates = stage["candidate_issue_phase"], stage["scientific_gates"]
    histories = []
    all_pass = True
    for conditioner in stage["conditioners"]:
        baseline = indexed[(conditioner, "baseline")]
        responses = {candidate: _response(indexed[(conditioner, candidate)], baseline)
                     for candidate in stage["candidates"] if candidate != "baseline"}
        pair_rows, columns = [], {4: [], 8: []}
        supported_axes = 0
        ip_pass = tail_pass = True
        arms = []
        for candidate, response in responses.items():
            values = {h: response[phase+h] for h in (4,8,12,16)}
            norms = {h: float(np.linalg.norm(values[h][:2])) for h in values}
            ip_pass &= max(abs(float(values[h][2])) for h in (4,8)) <= gates["maximum_h4_h8_absolute_ip_response_a"]
            tail_pass &= max(norms[12], norms[16]) <= gates["maximum_h12_h16_absolute_rz_response_mm"]
            tail_pass &= max(abs(float(values[h][2])) for h in (12,16)) <= gates["maximum_h12_h16_absolute_ip_response_a"]
            arms.append({"candidate": candidate, **{f"h{h}_response_rz_mm": values[h][:2].tolist() for h in values},
                         **{f"h{h}_rz_norm_mm": norms[h] for h in norms},
                         **{f"h{h}_ip_response_a": float(values[h][2]) for h in values}})
        for axis in stage["axes"]:
            plus, minus = responses[f"{axis}_plus"], responses[f"{axis}_minus"]
            separation = {h: float(np.linalg.norm(plus[phase+h,:2]-minus[phase+h,:2])) for h in (4,8)}
            local = max(separation.values()) >= gates["minimum_signed_pair_max_h4_h8_separation_mm"]
            supported_axes += int(local)
            pair_rows.append({"axis": axis, "h4_separation_mm": separation[4],
                              "h8_separation_mm": separation[8], "passed": local})
            for horizon in (4,8):
                columns[horizon].append(0.5*(plus[phase+horizon,:2]-minus[phase+horizon,:2]))
        horizon_rows = []
        for horizon in (4,8):
            row = {"horizon": horizon, **g3._cone_metrics(columns[horizon])}
            row["passed"] = (row["rank"] == 2 and row["condition"] <= gates["maximum_history_best_h4_h8_condition"]
                             and row["maximum_angular_gap_deg"] <= gates["maximum_history_best_h4_h8_angular_gap_deg"]
                             and row["weakest_best_projection_mm"] >= gates["minimum_history_best_h4_h8_weakest_projection_mm"])
            horizon_rows.append(row)
        geometry_pass = any(r["passed"] for r in horizon_rows)
        local_pass = (supported_axes >= gates["minimum_supported_axes_per_history"] and geometry_pass and ip_pass and tail_pass)
        all_pass &= local_pass
        histories.append({"conditioner": conditioner, "arms": arms, "signed_pairs": pair_rows,
                          "supported_axes": supported_axes, "horizons": horizon_rows,
                          "geometry_pass": geometry_pass, "ip_pass": ip_pass,
                          "return_tail_pass": tail_pass, "passed": local_pass})
    return {"passed": all_pass, "histories": histories}


def compare_rows(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    return d1.compare_rows(left, right)


def run(config_path: Path, source_revision: str, output_dir: Path) -> dict[str, Any]:
    preflight = offline(config_path, source_revision)
    if not preflight["passed"]:
        raise RuntimeError("D3 offline gate failed; TSC forbidden")
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
        replays = [{"family_id": family, **compare_rows(rows[family], rows[f"{family}_replay"])}
                   for family in stage["critical_replays"]]
    replay_pass = len(replays) == 2 and all(r["passed"] for r in replays)
    metrics = scientific_metrics([r for r in rows.values() if r["repeat_index"] == 0], stage) if execution else None
    science = metrics is not None and metrics["passed"]
    passed = execution and replay_pass and science
    route = stage["routes"]["pass"] if passed else (stage["routes"]["execution_fail"] if not execution
            else stage["routes"]["replay_fail"] if not replay_pass else stage["routes"]["scientific_fail"])
    result = {"schema_version": SCHEMA, "kind": "authentic_fixed_1000_discrete_value_development",
              "created_utc": datetime.now(timezone.utc).isoformat(), "source_revision": source_revision,
              "passed": passed, "route": route, "rollout_count": len(rows),
              "reset_calls": sum(r["reset_calls"] for r in rows.values()),
              "advance_attempts": sum(r["advance_attempts"] for r in rows.values()),
              "gotsc_calls": sum(r["gotsc_calls"] for r in rows.values()),
              "verified_plant_advances": sum(r["verified_plant_advances"] for r in rows.values()),
              "action_geometry": target_map["action_geometry"], "critical_replays": replays,
              "scientific_metrics": metrics,
              "claim_boundary": "fixed-1000 discrete candidate-value development only; no Authority/Recourse/controller"}
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
