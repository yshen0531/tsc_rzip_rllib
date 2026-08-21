#!/usr/bin/env python3
"""Fixed-1000 matched-history candidate-value development campaign."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
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
from scripts import rgeo_zgeo_1ms_1000_signed_temporal_d0 as d0  # noqa: E402
from scripts.rgeo_zgeo_1ms_nr1_qualification import _source  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    OneMsNR1SafetyEnvelope,
    assert_exact_slew,
    card15_target_decimal_a,
)
from tsc_rzip_rllib.control.rgeo_zgeo_contract import RGeoZGeoSignal  # noqa: E402
from tsc_rzip_rllib.core.runner import TSCConfig  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-1000-value-d2-v1"
CONFIG_SHA256 = "20bc6f38136a7697549fe406bc45126c1cef83a05011c48f7afd0eeedf20b2c3"
DEFAULT_CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_value_d2.json"
SEMANTIC_ARTIFACTS = b0.SEMANTIC_ARTIFACTS
MACRO_LEVELS = (1, 2, 3, 4, 4, 4, 4, 4, 3, 2, 1, 0)


class InputIntegrityError(ValueError):
    """Frozen D2 evidence, campaign or data role changed."""


def load(config_path: Path) -> tuple[dict[str, Any], TSCConfig, dict[str, Any], dict[str, Any]]:
    config_path = b0.inside_root(config_path, "D2 config")
    if b0.sha256(config_path) != CONFIG_SHA256:
        raise InputIntegrityError("D2 config SHA-256 mismatch")
    stage = json.loads(config_path.read_text(encoding="utf-8"))
    exact = {
        "schema_version": SCHEMA,
        "campaign_id": "rgeo_zgeo_1ms_1000_value_d2_v1",
        "takeover_time_ms": 1000,
        "control_period_ms": 1,
        "horizon_steps": 48,
        "conditioner_issue_phase": 8,
        "candidate_issue_phase": 24,
        "ramp_up_issues": 4,
        "plateau_issues": 4,
        "ramp_down_issues": 4,
        "tail_states_after_candidate_return": 12,
        "conditioners": ["even_plus", "odd_plus"],
        "candidates": ["baseline", "even_plus", "even_minus", "odd_plus", "odd_minus"],
        "primary_rollouts": 10,
        "critical_replays": ["c_even_plus__even_minus", "c_odd_plus__odd_minus"],
        "rollouts": 12,
        "maximum_reset_calls": 12,
        "maximum_advance_attempts": 576,
        "maximum_gotsc_calls": 576,
        "maximum_verified_plant_advances": 576,
        "retry_after_any_advance_attempt": "forbidden",
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise InputIntegrityError(f"frozen D2 field mismatch: {key}")
    expected_roles = {
        "ten_primary_conditioner_candidate_rows": "development_fit_eligible_weight_1",
        "critical_replays": "integrity_only_zero_fit_weight",
        "d1_evidence": "design_and_action_support_only",
        "calibration_histories": "unopened",
        "blind_histories": "unopened",
        "controller_or_recourse": "forbidden",
        "fixed_1100_data": "forbidden",
    }
    if stage.get("data_roles") != expected_roles:
        raise InputIntegrityError("D2 data roles changed")
    d1_config = b0.inside_root(ROOT / stage["d1_config_path"], "D2 D1 config")
    if b0.sha256(d1_config) != stage["d1_config_sha256"]:
        raise InputIntegrityError("D2 D1 config hash mismatch")
    for prefix in ("d1_result", "d1_independent"):
        path = b0.inside_root(ROOT / stage[f"{prefix}_path"], f"D2 {prefix}")
        if b0.sha256(path) != stage[f"{prefix}_sha256"]:
            raise InputIntegrityError(f"D2 {prefix} hash mismatch")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("passed") is not True:
            raise InputIntegrityError(f"D2 {prefix} is not PASS")
    d1_stage, cfg, baseline = d1.load(d1_config)
    if b0.sha256(ROOT / stage["base_tsc_config"]) != stage["base_tsc_config_sha256"]:
        raise InputIntegrityError("D2 base TSC config hash mismatch")
    return stage, cfg, baseline, d1_stage


def rollout_specs(stage: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for conditioner in stage["conditioners"]:
        for candidate in stage["candidates"]:
            base = f"c_{conditioner}__{candidate}"
            rows.append({
                "rollout_id": base, "family_id": base, "conditioner": conditioner,
                "candidate": candidate, "repeat_index": 0,
                "data_role": "development_fit_eligible_weight_1",
            })
    for base in stage["critical_replays"]:
        conditioner, candidate = base[2:].split("__")
        rows.append({
            "rollout_id": f"{base}_replay", "family_id": base,
            "conditioner": conditioner, "candidate": candidate, "repeat_index": 1,
            "data_role": "integrity_only_zero_fit_weight",
        })
    if len(rows) != stage["rollouts"] or len({row["rollout_id"] for row in rows}) != len(rows):
        raise InputIntegrityError("D2 rollout matrix changed")
    return rows


def _apply_macro(sequence: list[Any], phase: int, label: str, target_map: dict[str, Any]) -> None:
    axis, sign = label.split("_")
    prefix = f"{axis}_{sign}_level"
    for offset, level in enumerate(MACRO_LEVELS):
        sequence[phase + offset] = target_map["q0"] if level == 0 else target_map[f"{prefix}{level}"]


def sequence_for(spec: dict[str, Any], stage: dict[str, Any], target_map: dict[str, Any]) -> list[Any]:
    sequence = [target_map["q0"]] * stage["horizon_steps"]
    _apply_macro(sequence, stage["conditioner_issue_phase"], spec["conditioner"], target_map)
    if spec["candidate"] != "baseline":
        _apply_macro(sequence, stage["candidate_issue_phase"], spec["candidate"], target_map)
    return sequence


def action_stream(
    spec: dict[str, Any], stage: dict[str, Any], cfg: TSCConfig,
    source: dict[str, Any], target_map: dict[str, Any],
) -> list[dict[str, Any]]:
    active = tuple(source["active_command_decimal_a_tsc"])
    result = []
    for issue, target in enumerate(sequence_for(spec, stage, target_map)):
        exact = card15_target_decimal_a(target, cfg.turns_tsc, name=f"d2.{spec['rollout_id']}.{issue}")
        maximum = assert_exact_slew(active, exact, name=f"d2.{spec['rollout_id']}.{issue}")
        result.append({
            "issue_step": issue, "issue_time_ms": 1000 + issue,
            "effect_state_index": issue + 1, "effect_time_ms": 1001 + issue,
            "expected_card15_fields": list(target.card15_fields),
            "maximum_issued_delta_a": maximum,
        })
        active = exact
    return result


def offline(config_path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    streams = geometry = None
    try:
        stage, cfg, _, d1_stage = load(config_path)
        source = _source(cfg)
        envelope = OneMsNR1SafetyEnvelope.from_signal(RGeoZGeoSignal.from_tsc_state(source))
        failures.extend(envelope.state_reasons(
            RGeoZGeoSignal.from_tsc_state(source), source["currents_a_tsc"],
            cfg.min_current_a_tsc, cfg.max_current_a_tsc,
        ))
        target_map = d1.targets(d1_stage, cfg, source)
        geometry = target_map["action_geometry"]
        streams = [{**spec, "actions": action_stream(spec, stage, cfg, source, target_map)}
                   for spec in rollout_specs(stage)]
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
        stage = None
    failures = list(dict.fromkeys(failures))
    routes = (stage or {}).get("routes", {})
    return {
        "schema_version": SCHEMA, "kind": "offline_preflight",
        "created_utc": datetime.now(timezone.utc).isoformat(), "source_revision": source_revision,
        "passed": not failures,
        "route": routes.get("offline_pass") if not failures else routes.get(
            "offline_fail", "ONE_MS_NR1000D2_OFFLINE_FAIL_NO_TSC"
        ),
        "failures": failures, "authorized_reset_calls": 12,
        "authorized_plant_advances": 576, "action_geometry": geometry,
        "rollout_action_streams": streams,
    }


def _response(row: dict[str, Any], matched: dict[str, Any]) -> np.ndarray:
    return np.asarray([
        [(state["r_geo_m"] - base["r_geo_m"]) * 1000.0,
         (state["z_geo_m"] - base["z_geo_m"]) * 1000.0,
         state["ip_a"] - base["ip_a"]]
        for state, base in zip(row["states"], matched["states"])
    ], dtype=float)


def scientific_metrics(primary_rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    indexed = {(row["conditioner"], row["candidate"]): row for row in primary_rows}
    phase = stage["candidate_issue_phase"]
    gates = stage["scientific_gates"]
    signal_pass = pair_pass = geometry_pass = ip_pass = tail_pass = True
    histories = []
    for conditioner in stage["conditioners"]:
        matched = indexed[(conditioner, "baseline")]
        responses = {
            candidate: _response(indexed[(conditioner, candidate)], matched)
            for candidate in stage["candidates"] if candidate != "baseline"
        }
        arms = []
        for candidate, response in responses.items():
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
                "candidate": candidate,
                **{f"h{h}_response_rz_mm": values[h][:2].tolist() for h in values},
                **{f"h{h}_rz_norm_mm": norms[h] for h in norms},
                **{f"h{h}_ip_response_a": float(values[h][2]) for h in values},
            })
        pair_rows = []
        columns: dict[int, list[np.ndarray]] = {4: [], 8: []}
        for axis in ("even", "odd"):
            plus, minus = responses[f"{axis}_plus"], responses[f"{axis}_minus"]
            separation = {h: float(np.linalg.norm(plus[phase + h, :2] - minus[phase + h, :2]))
                          for h in (4, 8)}
            local = max(separation.values()) >= gates["minimum_signed_pair_max_h4_h8_separation_mm"]
            pair_pass &= local
            pair_rows.append({"axis": axis, "h4_separation_mm": separation[4],
                              "h8_separation_mm": separation[8], "passed": local})
            for horizon in (4, 8):
                columns[horizon].append(0.5 * (
                    plus[phase + horizon, :2] - minus[phase + horizon, :2]
                ))
        horizon_rows = []
        for horizon in (4, 8):
            matrix = np.column_stack(columns[horizon])
            singular = np.linalg.svd(matrix, compute_uv=False)
            condition = float(singular[0] / singular[-1]) if singular[-1] > 0 else math.inf
            horizon_rows.append({
                "horizon": horizon, "matrix_columns_even_odd_mm": matrix.tolist(),
                "singular_values_mm": singular.tolist(), "condition": condition,
                "sigma_min_mm": float(singular[-1]),
            })
        best = min(horizon_rows, key=lambda row: row["condition"])
        local_geometry = (
            best["condition"] <= gates["maximum_history_best_h4_h8_condition"]
            and best["sigma_min_mm"] >= gates["minimum_history_best_h4_h8_sigma_min_mm"]
        )
        geometry_pass &= local_geometry
        histories.append({
            "conditioner": conditioner, "arms": arms, "signed_pairs": pair_rows,
            "horizons": horizon_rows, "best": best, "passed": local_geometry,
        })
    passed = signal_pass and pair_pass and geometry_pass and ip_pass and tail_pass
    return {
        "passed": passed, "signal_pass": signal_pass, "signed_pair_pass": pair_pass,
        "history_geometry_pass": geometry_pass, "ip_pass": ip_pass,
        "return_tail_pass": tail_pass, "histories": histories,
    }


def compare_rows(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    return d1.compare_rows(left, right)


def run(config_path: Path, source_revision: str, output_dir: Path) -> dict[str, Any]:
    preflight = offline(config_path, source_revision)
    if not preflight["passed"]:
        raise RuntimeError("D2 offline gate failed; TSC forbidden")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {output_dir}")
    output_dir.mkdir(parents=True)
    b0.write_new(output_dir / "offline_preflight.json", preflight)
    stage, cfg, baseline, d1_stage = load(config_path)
    cfg.run_root = output_dir / "rollouts"
    source = _source(cfg)
    target_map = d1.targets(d1_stage, cfg, source)
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
        replay_rows = [{"family_id": family, **compare_rows(rows[family], rows[f"{family}_replay"])}
                       for family in stage["critical_replays"]]
    replay_pass = len(replay_rows) == 2 and all(row["passed"] for row in replay_rows)
    metrics = scientific_metrics(
        [row for row in rows.values() if row["repeat_index"] == 0], stage
    ) if execution_pass else None
    scientific_pass = metrics is not None and metrics["passed"]
    passed = execution_pass and replay_pass and scientific_pass
    route = stage["routes"]["pass"] if passed else (
        stage["routes"]["execution_fail"] if not execution_pass
        else stage["routes"]["replay_fail"] if not replay_pass
        else stage["routes"]["scientific_fail"]
    )
    result = {
        "schema_version": SCHEMA, "kind": "authentic_fixed_1000_history_conditioned_value_development",
        "created_utc": datetime.now(timezone.utc).isoformat(), "source_revision": source_revision,
        "passed": passed, "route": route, "rollout_count": len(rows),
        "reset_calls": sum(row["reset_calls"] for row in rows.values()),
        "advance_attempts": sum(row["advance_attempts"] for row in rows.values()),
        "gotsc_calls": sum(row["gotsc_calls"] for row in rows.values()),
        "verified_plant_advances": sum(row["verified_plant_advances"] for row in rows.values()),
        "action_geometry": target_map["action_geometry"], "critical_replays": replay_rows,
        "scientific_metrics": metrics,
        "claim_boundary": "fixed-1000 matched-history value development only; no model/authority/recourse/control",
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
