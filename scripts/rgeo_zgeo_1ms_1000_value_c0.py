#!/usr/bin/env python3
"""Fresh fixed-model calibration for the fixed-1000 direct value model."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_1000_baseline_b0 as b0  # noqa: E402
from scripts import rgeo_zgeo_1ms_1000_signed_temporal_d0 as d0  # noqa: E402
from scripts import rgeo_zgeo_1ms_1000_value_d2 as d2  # noqa: E402
from scripts.rgeo_zgeo_1ms_nr1_qualification import _source  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import OneMsNR1SafetyEnvelope  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_contract import RGeoZGeoSignal  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-1000-value-c0-v1"
CONFIG_SHA256 = "3f140a2d834d6feead40e994c6c8979d8502de0ce0e5aa4c85c38163670c9c6c"
DEFAULT_CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_value_c0.json"


class InputIntegrityError(ValueError):
    """Frozen calibration identity, evidence or model changed."""


def load(config_path: Path) -> tuple[dict[str, Any], Any, dict[str, Any], dict[str, Any], dict[str, Any]]:
    config_path = b0.inside_root(config_path, "C0 config")
    if b0.sha256(config_path) != CONFIG_SHA256:
        raise InputIntegrityError("C0 config SHA-256 mismatch")
    stage = json.loads(config_path.read_text(encoding="utf-8"))
    exact = {
        "schema_version": SCHEMA,
        "campaign_id": "rgeo_zgeo_1ms_1000_value_c0_v1",
        "takeover_time_ms": 1000,
        "control_period_ms": 1,
        "horizon_steps": 48,
        "conditioner_issue_phase": 8,
        "candidate_issue_phase": 24,
        "conditioners": ["even_minus", "odd_minus"],
        "candidates": ["baseline", "even_plus", "even_minus", "odd_plus", "odd_minus"],
        "primary_rollouts": 10,
        "critical_replays": ["c_even_minus__even_plus", "c_odd_minus__odd_plus"],
        "rollouts": 12,
        "maximum_reset_calls": 12,
        "maximum_advance_attempts": 576,
        "maximum_gotsc_calls": 576,
        "maximum_verified_plant_advances": 576,
        "retry_after_any_advance_attempt": "forbidden",
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise InputIntegrityError(f"frozen C0 field mismatch: {key}")
    roles = {
        "ten_primary_conditioner_candidate_rows": "fresh_calibration_evaluation_only_zero_fit_weight",
        "critical_replays": "integrity_only_zero_fit_weight",
        "v0_artifact": "frozen_read_only_no_refit",
        "d2_evidence": "design_and_action_support_only",
        "blind_mixed_histories": "unopened",
        "controller_or_recourse": "forbidden",
        "fixed_1100_data": "forbidden",
    }
    if stage.get("data_roles") != roles:
        raise InputIntegrityError("C0 data roles changed")
    for stem in ("d2_config", "v0_result", "v0_artifact"):
        path = b0.inside_root(ROOT / stage[f"{stem}_path"], f"C0 {stem}")
        if b0.sha256(path) != stage[f"{stem}_sha256"]:
            raise InputIntegrityError(f"C0 {stem} SHA-256 mismatch")
    v0_result = json.loads((ROOT / stage["v0_result_path"]).read_text(encoding="utf-8"))
    artifact = json.loads((ROOT / stage["v0_artifact_path"]).read_text(encoding="utf-8"))
    if v0_result.get("route") != "ONE_MS_NR1000V0_DIRECT_VALUE_RISK_DEVELOPMENT_PASS_FRESH_CALIBRATION_ONLY":
        raise InputIntegrityError("V0 result is not the frozen development PASS")
    if artifact.get("qualification") != "development_only_fresh_calibration_and_blind_history_required":
        raise InputIntegrityError("V0 artifact qualification changed")
    if artifact.get("source_revision") != v0_result.get("source_revision"):
        raise InputIntegrityError("V0 artifact/result revision mismatch")
    _, cfg, baseline, d1_stage = d2.load(ROOT / stage["d2_config_path"])
    return stage, cfg, baseline, d1_stage, artifact


def rollout_specs(stage: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for conditioner in stage["conditioners"]:
        for candidate in stage["candidates"]:
            family = f"c_{conditioner}__{candidate}"
            rows.append({
                "rollout_id": family, "family_id": family, "conditioner": conditioner,
                "candidate": candidate, "repeat_index": 0,
                "data_role": "fresh_calibration_evaluation_only_zero_fit_weight",
            })
    for family in stage["critical_replays"]:
        conditioner, candidate = family[2:].split("__")
        rows.append({
            "rollout_id": f"{family}_replay", "family_id": family,
            "conditioner": conditioner, "candidate": candidate, "repeat_index": 1,
            "data_role": "integrity_only_zero_fit_weight",
        })
    if len(rows) != 12 or len({row["rollout_id"] for row in rows}) != 12:
        raise InputIntegrityError("C0 rollout matrix changed")
    return rows


def offline(config_path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    streams = geometry = None
    try:
        stage, cfg, _, d1_stage, artifact = load(config_path)
        source = _source(cfg)
        envelope = OneMsNR1SafetyEnvelope.from_signal(RGeoZGeoSignal.from_tsc_state(source))
        failures.extend(envelope.state_reasons(
            RGeoZGeoSignal.from_tsc_state(source), source["currents_a_tsc"],
            cfg.min_current_a_tsc, cfg.max_current_a_tsc,
        ))
        target_map = d2.d1.targets(d1_stage, cfg, source)
        geometry = target_map["action_geometry"]
        streams = [{**spec, "actions": d2.action_stream(spec, stage, cfg, source, target_map)}
                   for spec in rollout_specs(stage)]
        if set(artifact["model"]["candidates"]) != set(stage["candidates"]) - {"baseline"}:
            failures.append("V0_ARTIFACT_CANDIDATE_SET")
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
            "offline_fail", "ONE_MS_NR1000C0_OFFLINE_FAIL_NO_TSC"
        ),
        "failures": failures, "authorized_reset_calls": 12,
        "authorized_plant_advances": 576, "action_geometry": geometry,
        "rollout_action_streams": streams,
        "v0_artifact_sha256": (stage or {}).get("v0_artifact_sha256"),
    }


def _artifact_arrays(artifact: Mapping[str, Any], candidate: str, horizon: int) -> tuple[np.ndarray, np.ndarray]:
    row = artifact["model"]["candidates"][candidate][str(horizon)]
    return np.asarray(row["center_rz_ip"], dtype=float), np.asarray(row["halfwidth_rz_ip"], dtype=float)


def calibration_metrics(
    primary_rows: Sequence[dict[str, Any]], stage: Mapping[str, Any], artifact: Mapping[str, Any],
) -> dict[str, Any]:
    indexed = {(row["conditioner"], row["candidate"]): row for row in primary_rows}
    phase = stage["candidate_issue_phase"]
    candidates = [value for value in stage["candidates"] if value != "baseline"]
    horizons = (4, 8)
    count = stage["model_calibration_gates"]["direction_grid_count"]
    directions = np.asarray([[math.cos(2 * math.pi * i / count), math.sin(2 * math.pi * i / count)]
                             for i in range(count)])
    histories = []
    maximum_ip = 0.0
    for conditioner in stage["conditioners"]:
        baseline = indexed[(conditioner, "baseline")]
        truth = {candidate: {
            horizon: d2._response(indexed[(conditioner, candidate)], baseline)[phase + horizon]
            for horizon in horizons
        } for candidate in candidates}
        contained = []
        maximum_excess = 0.0
        regrets = []
        weakest = {}
        for candidate in candidates:
            for horizon in horizons:
                center, width = _artifact_arrays(artifact, candidate, horizon)
                error = np.abs(truth[candidate][horizon] - center)
                inside = error <= width + 1e-12
                contained.extend(bool(value) for value in inside)
                maximum_excess = max(maximum_excess, float(np.max(error - width)))
                maximum_ip = max(maximum_ip, abs(float(truth[candidate][horizon][2])))
        for horizon in horizons:
            predicted = np.asarray([_artifact_arrays(artifact, c, horizon)[0][:2] for c in candidates])
            actual = np.asarray([truth[c][horizon][:2] for c in candidates])
            progress = []
            for direction in directions:
                chosen = int(np.argmax(predicted @ direction))
                scores = actual @ direction
                regrets.append(float(np.max(scores) - scores[chosen]))
                progress.append(float(np.max(scores)))
            weakest[str(horizon)] = min(progress)
        histories.append({
            "conditioner": conditioner, "components": len(contained),
            "contained_components": sum(contained), "all_components_contained": all(contained),
            "maximum_component_excess": max(0.0, maximum_excess),
            "maximum_directional_ranking_regret_mm": max(regrets),
            "weakest_best_progress_mm": weakest,
        })
    gates = stage["model_calibration_gates"]
    containment_pass = all(row["all_components_contained"] for row in histories)
    ranking_pass = all(row["maximum_directional_ranking_regret_mm"] <=
                       gates["maximum_each_history_directional_ranking_regret_mm"] for row in histories)
    progress_pass = all(row["weakest_best_progress_mm"]["8"] >=
                        gates["minimum_each_history_h8_weakest_best_progress_mm"] for row in histories)
    ip_pass = maximum_ip <= gates["maximum_observed_absolute_ip_response_a"]
    return {
        "passed": containment_pass and ranking_pass and progress_pass and ip_pass,
        "containment_pass": containment_pass, "ranking_pass": ranking_pass,
        "progress_pass": progress_pass, "ip_pass": ip_pass,
        "maximum_observed_absolute_ip_response_a": maximum_ip, "histories": histories,
    }


def run(config_path: Path, source_revision: str, output_dir: Path) -> dict[str, Any]:
    preflight = offline(config_path, source_revision)
    if not preflight["passed"]:
        raise RuntimeError("C0 offline gate failed; TSC forbidden")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {output_dir}")
    output_dir.mkdir(parents=True)
    b0.write_new(output_dir / "offline_preflight.json", preflight)
    stage, cfg, baseline, d1_stage, artifact = load(config_path)
    cfg.run_root = output_dir / "rollouts"
    source = _source(cfg)
    target_map = d2.d1.targets(d1_stage, cfg, source)
    envelope = OneMsNR1SafetyEnvelope.from_signal(RGeoZGeoSignal.from_tsc_state(source))
    rows: dict[str, dict[str, Any]] = {}
    for spec in rollout_specs(stage):
        row = d0._run_one(cfg, stage, spec, d2.sequence_for(spec, stage, target_map),
                          envelope, baseline["states"][0])
        rows[spec["rollout_id"]] = row
        b0.write_new(output_dir / f"{spec['rollout_id']}.json", row)
        if not row["passed"]:
            break
    execution_pass = len(rows) == 12 and all(row["passed"] for row in rows.values())
    replay_rows = []
    if execution_pass:
        replay_rows = [{"family_id": family, **d2.compare_rows(rows[family], rows[f"{family}_replay"])}
                       for family in stage["critical_replays"]]
    replay_pass = len(replay_rows) == 2 and all(row["passed"] for row in replay_rows)
    primaries = [row for row in rows.values() if row["repeat_index"] == 0]
    scientific = d2.scientific_metrics(primaries, stage) if execution_pass else None
    calibration = calibration_metrics(primaries, stage, artifact) if execution_pass else None
    scientific_pass = scientific is not None and scientific["passed"]
    model_pass = calibration is not None and calibration["passed"]
    passed = execution_pass and replay_pass and scientific_pass and model_pass
    route = stage["routes"]["pass"] if passed else (
        stage["routes"]["execution_fail"] if not execution_pass else
        stage["routes"]["replay_fail"] if not replay_pass else
        stage["routes"]["scientific_fail"] if not scientific_pass else stage["routes"]["model_fail"]
    )
    result = {
        "schema_version": SCHEMA, "kind": "authentic_fixed_1000_fixed_model_fresh_calibration",
        "created_utc": datetime.now(timezone.utc).isoformat(), "source_revision": source_revision,
        "passed": passed, "route": route, "rollout_count": len(rows),
        "reset_calls": sum(row["reset_calls"] for row in rows.values()),
        "advance_attempts": sum(row["advance_attempts"] for row in rows.values()),
        "gotsc_calls": sum(row["gotsc_calls"] for row in rows.values()),
        "verified_plant_advances": sum(row["verified_plant_advances"] for row in rows.values()),
        "v0_artifact_sha256": stage["v0_artifact_sha256"],
        "action_geometry": target_map["action_geometry"], "critical_replays": replay_rows,
        "scientific_metrics": scientific, "model_calibration_metrics": calibration,
        "claim_boundary": "fresh negative-history fixed-model calibration only; no fit/blind/authority/recourse/control",
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
