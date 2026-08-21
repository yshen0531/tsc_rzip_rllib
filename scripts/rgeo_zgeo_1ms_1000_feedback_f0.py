#!/usr/bin/env python3
"""Finite q0-relative moving-reference feedback sentinel at fixed 1000 ms."""

from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from typing import Any, Mapping
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_1000_authority_a0 as a0  # noqa: E402
from scripts import rgeo_zgeo_1ms_1000_baseline_b0 as b0  # noqa: E402
from scripts import rgeo_zgeo_1ms_1000_signed_temporal_d0 as d0  # noqa: E402
from scripts.rgeo_zgeo_1ms_nr1_qualification import _record, _source  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    OneMsNR1SafetyEnvelope, assert_exact_slew, card15_target_decimal_a,
)
from tsc_rzip_rllib.control.rgeo_zgeo_contract import RGeoZGeoSignal  # noqa: E402
from tsc_rzip_rllib.core.runner import TSCStepRunner  # noqa: E402

SCHEMA = "rgeo-zgeo-1ms-1000-feedback-f0-v1"
CONFIG_SHA256 = "4774da444fb79cbd610a05aa0524cdbb5d76b0dfb12d6866b5cead1a9561a611"
DEFAULT_CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_feedback_f0.json"


class InputIntegrityError(ValueError):
    pass


def load(path: Path) -> tuple[dict[str, Any], Any, dict[str, Any], dict[str, Any], dict[str, Any]]:
    path = b0.inside_root(path, "F0 config")
    if b0.sha256(path) != CONFIG_SHA256:
        raise InputIntegrityError("F0 config SHA-256 mismatch")
    stage = json.loads(path.read_text(encoding="utf-8"))
    exact = {
        "schema_version": SCHEMA, "campaign_id": "rgeo_zgeo_1ms_1000_feedback_f0_v1",
        "takeover_time_ms": 1000, "control_period_ms": 1, "horizon_steps": 64,
        "decision_issues": [24, 36, 48], "endpoint_states": [32, 44, 56],
        "candidate_horizon": 8,
        "candidates": ["even_minus", "even_plus", "odd_minus", "odd_plus"],
        "paths_mm_relative_q0": {
            "path_a": [[0.28, 0.0], [-0.12, -0.90], [-0.30, -0.75]],
            "path_b": [[-0.30, 0.0], [0.12, 0.90], [0.30, 0.75]],
        },
        "rollout_ids": ["q0_baseline", "path_a", "path_b", "path_a_replay"],
        "maximum_reset_calls": 4, "maximum_advance_attempts": 256,
        "maximum_gotsc_calls": 256, "maximum_verified_plant_advances": 256,
        "retry_after_any_advance_attempt": "forbidden",
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise InputIntegrityError(f"frozen F0 field mismatch: {key}")
    for stem in ("design", "a0_config", "a0_result", "a0_independent"):
        dep = b0.inside_root(ROOT / stage[f"{stem}_path"], f"F0 {stem}")
        if b0.sha256(dep) != stage[f"{stem}_sha256"]:
            raise InputIntegrityError(f"F0 {stem} SHA-256 mismatch")
    for stem in ("a0_result", "a0_independent"):
        if json.loads((ROOT / stage[f"{stem}_path"]).read_text(encoding="utf-8")).get("passed") is not True:
            raise InputIntegrityError(f"F0 {stem} is not PASS")
    _, cfg, baseline, d1_stage, artifact = a0.load(ROOT / stage["a0_config_path"])
    if len(baseline["states"]) < 65:
        raise InputIntegrityError("B0 reference lacks state64")
    return stage, cfg, baseline, d1_stage, artifact


def specs(stage: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for rollout_id in stage["rollout_ids"]:
        replay = rollout_id.endswith("_replay")
        path = "path_a" if rollout_id.startswith("path_a") else "path_b" if rollout_id == "path_b" else None
        rows.append({"rollout_id": rollout_id, "family_id": "path_a" if replay else rollout_id,
                     "path": path, "repeat_index": int(replay),
                     "data_role": "integrity_only_zero_fit_weight" if replay else
                                  "finite_feedback_qualification_only_zero_fit_weight"})
    return rows


def _rz_mm(state: Mapping[str, Any]) -> np.ndarray:
    return 1000 * np.asarray([state["r_geo_m"], state["z_geo_m"]], dtype=float)


def select(stage: Mapping[str, Any], artifact: Mapping[str, Any], current_deviation: np.ndarray,
           command: np.ndarray) -> tuple[str, float, float]:
    before = float(np.linalg.norm(command - current_deviation))
    scored = []
    for candidate in stage["candidates"]:
        center = a0.candidate_center(artifact, candidate, 8)
        scored.append((float(np.linalg.norm(command - current_deviation - center)), candidate))
    after, candidate = min(scored, key=lambda item: (item[0], item[1]))
    return candidate, before, after


def run_one(cfg: Any, stage: dict[str, Any], spec: dict[str, Any], envelope: Any,
            source_reference: dict[str, Any], target_map: Mapping[str, Any], artifact: Mapping[str, Any],
            reference_states: list[dict[str, Any]], decision_selector: Any = select) -> dict[str, Any]:
    runner = TSCStepRunner(cfg, worker_id=f"nr1000_f0_{spec['rollout_id']}", keep_workspace=False)
    reasons, states, actions, decisions = [], [], [], []
    attempts = gotsc = verified = resets = 0
    started = time.perf_counter()
    sequence = [target_map["q0"]] * stage["horizon_steps"]
    try:
        resets = 1
        live = runner.reset(episode_name=spec["rollout_id"])
        states.append(_record(cfg, live))
        reasons.extend(d0.source_mismatch_reasons(states[0], source_reference))
        origin_time = states[0]["time_ms"]
        for issue in range(stage["horizon_steps"]):
            reasons.extend(envelope.state_reasons(RGeoZGeoSignal.from_tsc_state(live),
                live["currents_a_tsc"], cfg.min_current_a_tsc, cfg.max_current_a_tsc))
            if spec["path"] is not None and issue in stage["decision_issues"]:
                ordinal = stage["decision_issues"].index(issue)
                command = np.asarray(stage["paths_mm_relative_q0"][spec["path"]][ordinal], dtype=float)
                deviation = _rz_mm(states[-1]) - _rz_mm(reference_states[issue])
                candidate, before, after = decision_selector(stage, artifact, deviation, command)
                if candidate is None:
                    reasons.append(f"DECISION_REFUSAL:{issue}")
                    break
                center = np.zeros(2) if candidate == "q0_noop" else a0.candidate_center(
                    artifact, candidate, 8)
                if candidate != "q0_noop":
                    a0.b1.c0.d2._apply_macro(sequence, issue, candidate, target_map)
                decisions.append({"ordinal": ordinal, "issue_step": issue,
                    "endpoint_state": stage["endpoint_states"][ordinal], "candidate": candidate,
                    "current_deviation_rz_mm": deviation.tolist(), "command_rz_mm": command.tolist(),
                    "predicted_error_before_mm": before, "predicted_error_after_mm": after,
                    "predicted_h8_center_rz_mm": center.tolist()})
            target = sequence[issue]
            exact = card15_target_decimal_a(target, cfg.turns_tsc, name=f"f0.{spec['rollout_id']}.{issue}")
            maximum = assert_exact_slew(states[-1]["active_command_decimal_a_tsc"], exact,
                                        name=f"f0.{spec['rollout_id']}.issued.{issue}")
            if reasons:
                break
            actions.append({"issue_step": issue, "issue_time_ms": int(live["time_ms"]),
                "effect_state_index": issue + 1, "effect_time_ms": origin_time + issue + 1,
                "expected_card15_fields": list(target.card15_fields), "maximum_issued_delta_a": maximum})
            attempts += 1
            live = runner.step_current_a(np.asarray(target.current_a_tsc, dtype=float))
            gotsc += 1
            record = _record(cfg, live)
            states.append(record)
            if int(live.get("returncode", 0)) != 0:
                reasons.append(f"TSC_RETURNCODE:{issue}:{live.get('returncode')}")
            if bool(live.get("abnormal", False)):
                reasons.append(f"TSC_ABNORMAL:{issue}:{live.get('done_reason', '')}")
            if record["time_ms"] != origin_time + issue + 1:
                reasons.append(f"TIME:{issue}")
            else:
                verified += 1
            if tuple(record["active_command_card15_fields"]) != tuple(target.card15_fields):
                reasons.append(f"CARD15:{issue}")
            if issue > 0:
                record["maximum_observed_delta_a"] = assert_exact_slew(
                    states[-2]["actual_current_decimal_a_tsc"], record["actual_current_decimal_a_tsc"],
                    name=f"f0.{spec['rollout_id']}.observed.{issue}")
            reasons.extend(envelope.state_reasons(RGeoZGeoSignal.from_tsc_state(live),
                live["currents_a_tsc"], cfg.min_current_a_tsc, cfg.max_current_a_tsc))
            if reasons:
                break
    except Exception as exc:
        reasons.append(f"EXECUTION:{type(exc).__name__}:{exc}")
    finally:
        try:
            runner.cleanup_runtime_workspace()
        except Exception as exc:
            reasons.append(f"CLEANUP:{type(exc).__name__}:{exc}")
    reasons = list(dict.fromkeys(reasons))
    expected_decisions = 0 if spec["path"] is None else 3
    complete = (not reasons and resets == 1 and attempts == gotsc == verified == 64 and
                len(states) == 65 and len(actions) == 64 and len(decisions) == expected_decisions and
                tuple(states[-1]["active_command_card15_fields"]) == tuple(target_map["q0"].card15_fields))
    return {**spec, "passed": complete, "reasons": reasons, "reset_calls": resets,
            "advance_attempts": attempts, "gotsc_calls": gotsc,
            "verified_plant_advances": verified, "states": states, "actions": actions,
            "decisions": decisions, "wall_time_s": time.perf_counter() - started}


def metrics(rows: Mapping[str, dict[str, Any]], stage: Mapping[str, Any],
            frozen_reference: dict[str, Any], artifact: Mapping[str, Any]) -> dict[str, Any]:
    q0_replay = a0.compare_prefix(rows["q0_baseline"], frozen_reference, 65, 64)
    path_replay = a0.compare_prefix(rows["path_a"], rows["path_a_replay"], 65, 64)
    if rows["path_a"].get("decisions") != rows["path_a_replay"].get("decisions"):
        path_replay["failures"].append("DECISIONS")
        path_replay["failures"] = list(dict.fromkeys(path_replay["failures"]))
        path_replay["passed"] = False
    paths = []
    gates = stage["scientific_gates"]
    for path_id in ("path_a", "path_b"):
        checkpoints = []
        for ordinal, state_index in enumerate(stage["endpoint_states"]):
            actual = _rz_mm(rows[path_id]["states"][state_index]) - _rz_mm(rows["q0_baseline"]["states"][state_index])
            command = np.asarray(stage["paths_mm_relative_q0"][path_id][ordinal])
            error = actual - command
            decision = rows[path_id]["decisions"][ordinal]
            predicted_progress = decision["predicted_error_before_mm"] - decision["predicted_error_after_mm"]
            passed = (float(np.linalg.norm(error)) <= gates["maximum_each_checkpoint_rz_error_norm_mm"] and
                      float(np.max(np.abs(error))) <= gates["maximum_each_checkpoint_axis_error_mm"] and
                      predicted_progress > 0 and
                      abs(float(artifact["model"]["candidates"][decision["candidate"]]["8"]
                                ["center_rz_ip"][2])) <=
                      gates["maximum_selected_predicted_absolute_ip_response_a"])
            checkpoints.append({"ordinal": ordinal, "state_index": state_index,
                "candidate": decision["candidate"], "command_rz_mm": command.tolist(),
                "actual_rz_mm": actual.tolist(), "error_rz_mm": error.tolist(),
                "error_norm_mm": float(np.linalg.norm(error)),
                "predicted_progress_mm": predicted_progress, "passed": passed})
        paths.append({"path": path_id, "passed": all(c["passed"] for c in checkpoints),
                      "checkpoints": checkpoints})
    return {"passed": q0_replay["passed"] and path_replay["passed"] and all(p["passed"] for p in paths),
            "q0_reference_replay": q0_replay, "path_a_replay": path_replay, "paths": paths}


def offline(config_path: Path, source_revision: str) -> dict[str, Any]:
    failures = []
    try:
        stage, cfg, baseline, d1_stage, artifact = load(config_path)
        source = _source(cfg)
        envelope = OneMsNR1SafetyEnvelope.from_signal(RGeoZGeoSignal.from_tsc_state(source))
        failures.extend(envelope.state_reasons(RGeoZGeoSignal.from_tsc_state(source), source["currents_a_tsc"],
                                               cfg.min_current_a_tsc, cfg.max_current_a_tsc))
        target_map = a0.b1.c0.d2.d1.targets(d1_stage, cfg, source)
        for phase in stage["decision_issues"]:
            for candidate in stage["candidates"]:
                sequence = [target_map["q0"]] * 64
                a0.b1.c0.d2._apply_macro(sequence, phase, candidate, target_map)
                active = tuple(source["active_command_decimal_a_tsc"])
                for issue, target in enumerate(sequence):
                    exact = card15_target_decimal_a(target, cfg.turns_tsc, name=f"f0.offline.{phase}.{candidate}.{issue}")
                    assert_exact_slew(active, exact, name=f"f0.offline.{phase}.{candidate}.{issue}")
                    active = exact
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
        stage = None
    failures = list(dict.fromkeys(failures))
    routes = (stage or {}).get("routes", {})
    return {"schema_version": SCHEMA, "kind": "offline_preflight",
            "created_utc": datetime.now(timezone.utc).isoformat(), "source_revision": source_revision,
            "passed": not failures, "route": routes.get("offline_pass") if not failures else
            routes.get("offline_fail", "ONE_MS_NR1000F0_OFFLINE_FAIL_NO_TSC"), "failures": failures,
            "authorized_reset_calls": 4, "authorized_plant_advances": 256}


def run(config_path: Path, source_revision: str, output_dir: Path) -> dict[str, Any]:
    preflight = offline(config_path, source_revision)
    if not preflight["passed"]:
        raise RuntimeError("F0 offline gate failed; TSC forbidden")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {output_dir}")
    output_dir.mkdir(parents=True)
    b0.write_new(output_dir / "offline_preflight.json", preflight)
    stage, cfg, baseline, d1_stage, artifact = load(config_path)
    cfg.run_root = output_dir / "rollouts"
    source = _source(cfg)
    target_map = a0.b1.c0.d2.d1.targets(d1_stage, cfg, source)
    envelope = OneMsNR1SafetyEnvelope.from_signal(RGeoZGeoSignal.from_tsc_state(source))
    rows = {}
    for spec in specs(stage):
        row = run_one(cfg, stage, spec, envelope, baseline["states"][0], target_map, artifact,
                      baseline["states"][:65])
        rows[spec["rollout_id"]] = row
        b0.write_new(output_dir / f"{spec['rollout_id']}.json", row)
        if not row["passed"]:
            break
    execution = len(rows) == 4 and all(r["passed"] for r in rows.values())
    measured = metrics(rows, stage, baseline, artifact) if execution else None
    passed = execution and measured is not None and measured["passed"]
    if passed:
        route = stage["routes"]["pass"]
    elif not execution:
        route = stage["routes"]["execution_fail"]
    elif not measured["q0_reference_replay"]["passed"]:
        route = stage["routes"]["reference_fail"]
    elif not measured["path_a_replay"]["passed"]:
        route = stage["routes"]["replay_fail"]
    else:
        route = stage["routes"]["tracking_fail"]
    result = {"schema_version": SCHEMA, "kind": "authentic_fixed_1000_finite_q0_relative_feedback",
        "created_utc": datetime.now(timezone.utc).isoformat(), "source_revision": source_revision,
        "passed": passed, "route": route, "rollout_count": len(rows),
        "reset_calls": sum(r["reset_calls"] for r in rows.values()),
        "advance_attempts": sum(r["advance_attempts"] for r in rows.values()),
        "gotsc_calls": sum(r["gotsc_calls"] for r in rows.values()),
        "verified_plant_advances": sum(r["verified_plant_advances"] for r in rows.values()),
        "metrics": measured,
        "claim_boundary": "fixed-1000 finite q0-relative three-checkpoint feedback only; no absolute hold/recourse"}
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
