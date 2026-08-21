#!/usr/bin/env python3
"""Unopened mixed-history blind evaluation of fixed-1000 V0."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_1000_baseline_b0 as b0  # noqa: E402
from scripts import rgeo_zgeo_1ms_1000_signed_temporal_d0 as d0  # noqa: E402
from scripts import rgeo_zgeo_1ms_1000_value_c0 as c0  # noqa: E402
from scripts.rgeo_zgeo_1ms_nr1_qualification import _source  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    OneMsNR1SafetyEnvelope, assert_exact_slew, card15_target_decimal_a,
)
from tsc_rzip_rllib.control.rgeo_zgeo_contract import RGeoZGeoSignal  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-1000-value-b1-v1"
CONFIG_SHA256 = "ef91fc5d9a01107c1263bbb75f9a77330255ffbd3aacf9ed96e369feb9dd8313"
DEFAULT_CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_value_b1.json"


class InputIntegrityError(ValueError):
    """Frozen blind identity, history, evidence or model changed."""


def load(config_path: Path) -> tuple[dict[str, Any], Any, dict[str, Any], dict[str, Any], dict[str, Any]]:
    config_path = b0.inside_root(config_path, "B1 config")
    if b0.sha256(config_path) != CONFIG_SHA256:
        raise InputIntegrityError("B1 config SHA-256 mismatch")
    stage = json.loads(config_path.read_text(encoding="utf-8"))
    exact = {
        "schema_version": SCHEMA,
        "campaign_id": "rgeo_zgeo_1ms_1000_value_b1_v1",
        "takeover_time_ms": 1000,
        "control_period_ms": 1,
        "horizon_steps": 48,
        "conditioner_phases": [0, 12],
        "candidate_issue_phase": 24,
        "histories": {
            "even_plus_then_odd_minus": ["even_plus", "odd_minus"],
            "even_minus_then_odd_plus": ["even_minus", "odd_plus"],
        },
        "candidates": ["baseline", "even_plus", "even_minus", "odd_plus", "odd_minus"],
        "primary_rollouts": 10,
        "critical_replays": [
            "h_even_plus_then_odd_minus__even_minus",
            "h_even_minus_then_odd_plus__odd_plus",
        ],
        "rollouts": 12,
        "maximum_reset_calls": 12,
        "maximum_advance_attempts": 576,
        "maximum_gotsc_calls": 576,
        "maximum_verified_plant_advances": 576,
        "retry_after_any_advance_attempt": "forbidden",
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise InputIntegrityError(f"frozen B1 field mismatch: {key}")
    roles = {
        "ten_primary_history_candidate_rows": "unopened_blind_evaluation_only_zero_fit_weight",
        "critical_replays": "integrity_only_zero_fit_weight",
        "v0_artifact": "frozen_read_only_no_refit_or_widening",
        "d2_and_c0_evidence": "development_calibration_and_action_support_only",
        "controller_or_recourse": "forbidden",
        "fixed_1100_data": "forbidden",
    }
    if stage.get("data_roles") != roles:
        raise InputIntegrityError("B1 data roles changed")
    for stem in ("c0_config", "c0_result", "c0_independent", "v0_artifact"):
        path = b0.inside_root(ROOT / stage[f"{stem}_path"], f"B1 {stem}")
        if b0.sha256(path) != stage[f"{stem}_sha256"]:
            raise InputIntegrityError(f"B1 {stem} SHA-256 mismatch")
    for stem in ("c0_result", "c0_independent"):
        payload = json.loads((ROOT / stage[f"{stem}_path"]).read_text(encoding="utf-8"))
        if payload.get("passed") is not True:
            raise InputIntegrityError(f"B1 {stem} is not PASS")
    _, cfg, baseline, d1_stage, inherited_artifact = c0.load(ROOT / stage["c0_config_path"])
    artifact = json.loads((ROOT / stage["v0_artifact_path"]).read_text(encoding="utf-8"))
    if artifact != inherited_artifact:
        raise InputIntegrityError("B1 V0 artifact differs from calibrated artifact")
    return stage, cfg, baseline, d1_stage, artifact


def rollout_specs(stage: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for history in stage["histories"]:
        for candidate in stage["candidates"]:
            family = f"h_{history}__{candidate}"
            rows.append({
                "rollout_id": family, "family_id": family, "conditioner": history,
                "history": history, "candidate": candidate, "repeat_index": 0,
                "data_role": "unopened_blind_evaluation_only_zero_fit_weight",
            })
    for family in stage["critical_replays"]:
        history, candidate = family[2:].split("__")
        rows.append({
            "rollout_id": f"{family}_replay", "family_id": family,
            "conditioner": history, "history": history, "candidate": candidate,
            "repeat_index": 1, "data_role": "integrity_only_zero_fit_weight",
        })
    if len(rows) != 12 or len({row["rollout_id"] for row in rows}) != 12:
        raise InputIntegrityError("B1 rollout matrix changed")
    return rows


def sequence_for(spec: Mapping[str, Any], stage: Mapping[str, Any], target_map: Mapping[str, Any]) -> list[Any]:
    sequence = [target_map["q0"]] * stage["horizon_steps"]
    for phase, macro in zip(stage["conditioner_phases"], stage["histories"][spec["history"]]):
        c0.d2._apply_macro(sequence, phase, macro, target_map)
    if spec["candidate"] != "baseline":
        c0.d2._apply_macro(sequence, stage["candidate_issue_phase"], spec["candidate"], target_map)
    return sequence


def action_stream(spec: Mapping[str, Any], stage: Mapping[str, Any], cfg: Any,
                  source: Mapping[str, Any], target_map: Mapping[str, Any]) -> list[dict[str, Any]]:
    active = tuple(source["active_command_decimal_a_tsc"])
    result = []
    for issue, target in enumerate(sequence_for(spec, stage, target_map)):
        exact = card15_target_decimal_a(target, cfg.turns_tsc,
                                         name=f"b1.{spec['rollout_id']}.{issue}")
        maximum = assert_exact_slew(active, exact, name=f"b1.{spec['rollout_id']}.{issue}")
        result.append({
            "issue_step": issue, "issue_time_ms": 1000 + issue,
            "effect_state_index": issue + 1, "effect_time_ms": 1001 + issue,
            "expected_card15_fields": list(target.card15_fields),
            "maximum_issued_delta_a": maximum,
        })
        active = exact
    return result


def evaluation_stage(stage: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(stage)
    result["conditioners"] = list(stage["histories"])
    result["model_calibration_gates"] = stage["model_blind_gates"]
    return result


def offline(config_path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    streams = geometry = None
    try:
        stage, cfg, _, d1_stage, _ = load(config_path)
        source = _source(cfg)
        envelope = OneMsNR1SafetyEnvelope.from_signal(RGeoZGeoSignal.from_tsc_state(source))
        failures.extend(envelope.state_reasons(
            RGeoZGeoSignal.from_tsc_state(source), source["currents_a_tsc"],
            cfg.min_current_a_tsc, cfg.max_current_a_tsc))
        target_map = c0.d2.d1.targets(d1_stage, cfg, source)
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
            "offline_fail", "ONE_MS_NR1000B1_OFFLINE_FAIL_NO_TSC"),
        "failures": failures, "authorized_reset_calls": 12,
        "authorized_plant_advances": 576, "action_geometry": geometry,
        "rollout_action_streams": streams,
        "v0_artifact_sha256": (stage or {}).get("v0_artifact_sha256"),
    }


def run(config_path: Path, source_revision: str, output_dir: Path) -> dict[str, Any]:
    preflight = offline(config_path, source_revision)
    if not preflight["passed"]:
        raise RuntimeError("B1 offline gate failed; TSC forbidden")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {output_dir}")
    output_dir.mkdir(parents=True)
    b0.write_new(output_dir / "offline_preflight.json", preflight)
    stage, cfg, baseline, d1_stage, artifact = load(config_path)
    cfg.run_root = output_dir / "rollouts"
    source = _source(cfg)
    target_map = c0.d2.d1.targets(d1_stage, cfg, source)
    envelope = OneMsNR1SafetyEnvelope.from_signal(RGeoZGeoSignal.from_tsc_state(source))
    rows: dict[str, dict[str, Any]] = {}
    for spec in rollout_specs(stage):
        row = d0._run_one(cfg, stage, spec, sequence_for(spec, stage, target_map),
                          envelope, baseline["states"][0])
        rows[spec["rollout_id"]] = row
        b0.write_new(output_dir / f"{spec['rollout_id']}.json", row)
        if not row["passed"]:
            break
    execution_pass = len(rows) == 12 and all(row["passed"] for row in rows.values())
    replay_rows = []
    if execution_pass:
        replay_rows = [{"family_id": family, **c0.d2.compare_rows(rows[family], rows[f"{family}_replay"])}
                       for family in stage["critical_replays"]]
    replay_pass = len(replay_rows) == 2 and all(row["passed"] for row in replay_rows)
    primaries = [row for row in rows.values() if row["repeat_index"] == 0]
    eval_stage = evaluation_stage(stage)
    scientific = c0.d2.scientific_metrics(primaries, eval_stage) if execution_pass else None
    blind = c0.calibration_metrics(primaries, eval_stage, artifact) if execution_pass else None
    scientific_pass = scientific is not None and scientific["passed"]
    model_pass = blind is not None and blind["passed"]
    passed = execution_pass and replay_pass and scientific_pass and model_pass
    route = stage["routes"]["pass"] if passed else (
        stage["routes"]["execution_fail"] if not execution_pass else
        stage["routes"]["replay_fail"] if not replay_pass else
        stage["routes"]["scientific_fail"] if not scientific_pass else stage["routes"]["model_fail"])
    result = {
        "schema_version": SCHEMA, "kind": "authentic_fixed_1000_mixed_history_blind",
        "created_utc": datetime.now(timezone.utc).isoformat(), "source_revision": source_revision,
        "passed": passed, "route": route, "rollout_count": len(rows),
        "reset_calls": sum(row["reset_calls"] for row in rows.values()),
        "advance_attempts": sum(row["advance_attempts"] for row in rows.values()),
        "gotsc_calls": sum(row["gotsc_calls"] for row in rows.values()),
        "verified_plant_advances": sum(row["verified_plant_advances"] for row in rows.values()),
        "v0_artifact_sha256": stage["v0_artifact_sha256"],
        "action_geometry": target_map["action_geometry"], "critical_replays": replay_rows,
        "scientific_metrics": scientific, "model_blind_metrics": blind,
        "claim_boundary": "fixed-1000 finite mixed-history blind only; no fit/authority/recourse/control",
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
