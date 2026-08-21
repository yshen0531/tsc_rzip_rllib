#!/usr/bin/env python3
"""Deadband-abstention repair of fixed-1000 finite feedback F0."""

from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Mapping
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_1000_feedback_f0 as f0  # noqa: E402
from scripts.rgeo_zgeo_1ms_nr1_qualification import _source  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    OneMsNR1SafetyEnvelope, assert_exact_slew, card15_target_decimal_a,
)
from tsc_rzip_rllib.control.rgeo_zgeo_contract import RGeoZGeoSignal  # noqa: E402

SCHEMA = "rgeo-zgeo-1ms-1000-feedback-f1-v1"
CONFIG_SHA256 = "2a68f28935961dfff6f7811719f391cfa8c89c5fdec977cc0b3b72f875ba068c"
DEFAULT_CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_feedback_f1.json"


class InputIntegrityError(ValueError):
    pass


def load(path: Path) -> tuple[dict[str, Any], Any, dict[str, Any], dict[str, Any], dict[str, Any]]:
    path = f0.b0.inside_root(path, "F1 config")
    if f0.b0.sha256(path) != CONFIG_SHA256:
        raise InputIntegrityError("F1 config SHA-256 mismatch")
    stage = json.loads(path.read_text(encoding="utf-8"))
    exact = {
        "schema_version": SCHEMA, "campaign_id": "rgeo_zgeo_1ms_1000_feedback_f1_v1",
        "takeover_time_ms": 1000, "control_period_ms": 1, "horizon_steps": 64,
        "decision_issues": [24, 36, 48], "endpoint_states": [32, 44, 56],
        "terminal_state": 64, "candidate_horizon": 8,
        "active_candidates": ["even_minus", "even_plus", "odd_minus", "odd_plus"],
        "noop_candidate": "q0_noop",
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
            raise InputIntegrityError(f"frozen F1 field mismatch: {key}")
    for stem in ("design", "f0_config", "f0_result", "f0_independent"):
        dep = f0.b0.inside_root(ROOT / stage[f"{stem}_path"], f"F1 {stem}")
        if f0.b0.sha256(dep) != stage[f"{stem}_sha256"]:
            raise InputIntegrityError(f"F1 {stem} SHA-256 mismatch")
    result = json.loads((ROOT / stage["f0_result_path"]).read_text(encoding="utf-8"))
    audit = json.loads((ROOT / stage["f0_independent_path"]).read_text(encoding="utf-8"))
    if result.get("route") != "ONE_MS_NR1000F0_FINITE_Q0_RELATIVE_TRACKING_FAIL_REDESIGN":
        raise InputIntegrityError("F0 is not the frozen scientific FAIL")
    if audit.get("passed") is not True or audit.get("primary_scientific_route") != result.get("route"):
        raise InputIntegrityError("F0 independent audit is not the frozen integrity PASS")
    _, cfg, baseline, d1_stage, artifact = f0.load(ROOT / stage["f0_config_path"])
    return stage, cfg, baseline, d1_stage, artifact


def specs(stage: Mapping[str, Any]) -> list[dict[str, Any]]:
    return f0.specs({**stage, "candidates": stage["active_candidates"]})


def select(stage: Mapping[str, Any], artifact: Mapping[str, Any], current_deviation: np.ndarray,
           command: np.ndarray) -> tuple[str | None, float, float]:
    before = float(np.linalg.norm(command - current_deviation))
    if before <= float(stage["scientific_gates"]["deadband_error_norm_mm"]):
        return stage["noop_candidate"], before, before
    proxy = {**stage, "candidates": stage["active_candidates"]}
    candidate, _, after = f0.select(proxy, artifact, current_deviation, command)
    return (candidate if after < before else None), before, after


def metrics(rows: Mapping[str, dict[str, Any]], stage: Mapping[str, Any],
            reference: dict[str, Any], artifact: Mapping[str, Any]) -> dict[str, Any]:
    q0_replay = f0.a0.compare_prefix(rows["q0_baseline"], reference, 65, 64)
    path_replay = f0.a0.compare_prefix(rows["path_a"], rows["path_a_replay"], 65, 64)
    if rows["path_a"].get("decisions") != rows["path_a_replay"].get("decisions"):
        path_replay["failures"].append("DECISIONS")
        path_replay["failures"] = list(dict.fromkeys(path_replay["failures"]))
        path_replay["passed"] = False
    gates = stage["scientific_gates"]
    paths = []
    for path_id in ("path_a", "path_b"):
        checkpoints = []
        for ordinal, state_index in enumerate(stage["endpoint_states"]):
            actual = f0._rz_mm(rows[path_id]["states"][state_index]) - f0._rz_mm(
                rows["q0_baseline"]["states"][state_index])
            command = np.asarray(stage["paths_mm_relative_q0"][path_id][ordinal], dtype=float)
            error = actual - command
            decision = rows[path_id]["decisions"][ordinal]
            candidate = decision["candidate"]
            progress = decision["predicted_error_before_mm"] - decision["predicted_error_after_mm"]
            if candidate == stage["noop_candidate"]:
                decision_gate = decision["predicted_error_before_mm"] <= gates["deadband_error_norm_mm"]
                predicted_ip = 0.0
            else:
                decision_gate = progress > 0
                predicted_ip = abs(float(artifact["model"]["candidates"][candidate]["8"]
                                         ["center_rz_ip"][2]))
            passed = (float(np.linalg.norm(error)) <= gates["maximum_each_checkpoint_rz_error_norm_mm"] and
                      float(np.max(np.abs(error))) <= gates["maximum_each_checkpoint_axis_error_mm"] and
                      decision_gate and predicted_ip <= gates["maximum_selected_predicted_absolute_ip_response_a"])
            checkpoints.append({"ordinal": ordinal, "state_index": state_index,
                "candidate": candidate, "command_rz_mm": command.tolist(),
                "actual_rz_mm": actual.tolist(), "error_rz_mm": error.tolist(),
                "error_norm_mm": float(np.linalg.norm(error)), "predicted_progress_mm": progress,
                "decision_gate_passed": decision_gate, "passed": passed})
        terminal_index = stage["terminal_state"]
        terminal_command = np.asarray(stage["paths_mm_relative_q0"][path_id][-1], dtype=float)
        terminal_actual = f0._rz_mm(rows[path_id]["states"][terminal_index]) - f0._rz_mm(
            rows["q0_baseline"]["states"][terminal_index])
        terminal_error = terminal_actual - terminal_command
        terminal_passed = (float(np.linalg.norm(terminal_error)) <=
                           gates["maximum_each_checkpoint_rz_error_norm_mm"] and
                           float(np.max(np.abs(terminal_error))) <= gates["maximum_each_checkpoint_axis_error_mm"])
        paths.append({"path": path_id, "passed": all(row["passed"] for row in checkpoints) and terminal_passed,
                      "checkpoints": checkpoints,
                      "terminal": {"state_index": terminal_index,
                          "command_rz_mm": terminal_command.tolist(),
                          "actual_rz_mm": terminal_actual.tolist(),
                          "error_rz_mm": terminal_error.tolist(),
                          "error_norm_mm": float(np.linalg.norm(terminal_error)),
                          "passed": terminal_passed}})
    return {"passed": q0_replay["passed"] and path_replay["passed"] and all(p["passed"] for p in paths),
            "q0_reference_replay": q0_replay, "path_a_replay": path_replay, "paths": paths}


def offline(config_path: Path, source_revision: str) -> dict[str, Any]:
    failures = []
    try:
        stage, cfg, _, d1_stage, _ = load(config_path)
        source = _source(cfg)
        envelope = OneMsNR1SafetyEnvelope.from_signal(RGeoZGeoSignal.from_tsc_state(source))
        failures.extend(envelope.state_reasons(RGeoZGeoSignal.from_tsc_state(source),
            source["currents_a_tsc"], cfg.min_current_a_tsc, cfg.max_current_a_tsc))
        target_map = f0.a0.b1.c0.d2.d1.targets(d1_stage, cfg, source)
        for phase in stage["decision_issues"]:
            for candidate in stage["active_candidates"]:
                sequence = [target_map["q0"]] * 64
                f0.a0.b1.c0.d2._apply_macro(sequence, phase, candidate, target_map)
                active = tuple(source["active_command_decimal_a_tsc"])
                for issue, target in enumerate(sequence):
                    exact = card15_target_decimal_a(target, cfg.turns_tsc,
                                                     name=f"f1.offline.{phase}.{candidate}.{issue}")
                    assert_exact_slew(active, exact, name=f"f1.offline.{phase}.{candidate}.{issue}")
                    active = exact
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
        stage = None
    failures = list(dict.fromkeys(failures))
    routes = (stage or {}).get("routes", {})
    return {"schema_version": SCHEMA, "kind": "offline_preflight",
        "created_utc": datetime.now(timezone.utc).isoformat(), "source_revision": source_revision,
        "passed": not failures, "route": routes.get("offline_pass") if not failures else
        routes.get("offline_fail", "ONE_MS_NR1000F1_OFFLINE_FAIL_NO_TSC"), "failures": failures,
        "authorized_reset_calls": 4, "authorized_plant_advances": 256}


def run(config_path: Path, source_revision: str, output_dir: Path) -> dict[str, Any]:
    preflight = offline(config_path, source_revision)
    if not preflight["passed"]:
        raise RuntimeError("F1 offline gate failed; TSC forbidden")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {output_dir}")
    output_dir.mkdir(parents=True)
    f0.b0.write_new(output_dir / "offline_preflight.json", preflight)
    stage, cfg, baseline, d1_stage, artifact = load(config_path)
    cfg.run_root = output_dir / "rollouts"
    source = _source(cfg)
    target_map = f0.a0.b1.c0.d2.d1.targets(d1_stage, cfg, source)
    envelope = OneMsNR1SafetyEnvelope.from_signal(RGeoZGeoSignal.from_tsc_state(source))
    rows = {}
    for spec in specs(stage):
        row = f0.run_one(cfg, stage, spec, envelope, baseline["states"][0], target_map,
                         artifact, baseline["states"][:65], decision_selector=select)
        rows[spec["rollout_id"]] = row
        f0.b0.write_new(output_dir / f"{spec['rollout_id']}.json", row)
        if not row["passed"]:
            break
    execution = len(rows) == 4 and all(row["passed"] for row in rows.values())
    measured = metrics(rows, stage, baseline, artifact) if execution else None
    passed = execution and measured is not None and measured["passed"]
    refused = any(any(str(reason).startswith("DECISION_REFUSAL") for reason in row.get("reasons", []))
                  for row in rows.values())
    if passed:
        route = stage["routes"]["pass"]
    elif refused:
        route = stage["routes"]["decision_refusal"]
    elif not execution:
        route = stage["routes"]["execution_fail"]
    elif not measured["q0_reference_replay"]["passed"]:
        route = stage["routes"]["reference_fail"]
    elif not measured["path_a_replay"]["passed"]:
        route = stage["routes"]["replay_fail"]
    else:
        route = stage["routes"]["tracking_fail"]
    result = {"schema_version": SCHEMA, "kind": "authentic_fixed_1000_deadband_feedback",
        "created_utc": datetime.now(timezone.utc).isoformat(), "source_revision": source_revision,
        "passed": passed, "route": route, "rollout_count": len(rows),
        "reset_calls": sum(row["reset_calls"] for row in rows.values()),
        "advance_attempts": sum(row["advance_attempts"] for row in rows.values()),
        "gotsc_calls": sum(row["gotsc_calls"] for row in rows.values()),
        "verified_plant_advances": sum(row["verified_plant_advances"] for row in rows.values()),
        "metrics": measured,
        "claim_boundary": "fixed-1000 finite q0-relative deadband feedback only; no absolute hold/recourse"}
    f0.b0.write_new(output_dir / "result.json", result)
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
        f0.b0.write_new(args.output.resolve(), result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
