#!/usr/bin/env python3
"""Sequential exact-observation Authority-L0 sentinel at fixed 1000 ms."""

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

from scripts import rgeo_zgeo_1ms_1000_baseline_b0 as b0  # noqa: E402
from scripts import rgeo_zgeo_1ms_1000_signed_temporal_d0 as d0  # noqa: E402
from scripts import rgeo_zgeo_1ms_1000_value_b1 as b1  # noqa: E402
from scripts.rgeo_zgeo_1ms_nr1_qualification import _record, _source  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    OneMsNR1SafetyEnvelope, assert_exact_slew, card15_target_decimal_a,
)
from tsc_rzip_rllib.control.rgeo_zgeo_contract import RGeoZGeoSignal  # noqa: E402
from tsc_rzip_rllib.core.runner import TSCStepRunner  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-1000-authority-a0-v1"
CONFIG_SHA256 = "2f0215fd210edec333df5f695115e22785e619240a3c3b9bc969f4cbc48f5286"
DEFAULT_CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_authority_a0.json"


class InputIntegrityError(ValueError):
    """Frozen Authority identity or prerequisite changed."""


def load(config_path: Path) -> tuple[dict[str, Any], Any, dict[str, Any], dict[str, Any], dict[str, Any]]:
    config_path = b0.inside_root(config_path, "A0 config")
    if b0.sha256(config_path) != CONFIG_SHA256:
        raise InputIntegrityError("A0 config SHA-256 mismatch")
    stage = json.loads(config_path.read_text(encoding="utf-8"))
    exact = {
        "schema_version": SCHEMA,
        "campaign_id": "rgeo_zgeo_1ms_1000_authority_a0_v1",
        "takeover_time_ms": 1000,
        "control_period_ms": 1,
        "horizon_steps": 60,
        "decision_issues": [24, 36],
        "candidate_horizon": 8,
        "candidates": ["even_minus", "even_plus", "odd_minus", "odd_plus"],
        "waypoints_mm": {"positive": [0.8, 0.2], "negative": [-0.9, -1.0]},
        "rollout_ids": ["q0_baseline", "positive_first_only", "positive_full",
                        "negative_first_only", "negative_full", "positive_full_replay"],
        "maximum_reset_calls": 6,
        "maximum_advance_attempts": 360,
        "maximum_gotsc_calls": 360,
        "maximum_verified_plant_advances": 360,
        "retry_after_any_advance_attempt": "forbidden",
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise InputIntegrityError(f"frozen A0 field mismatch: {key}")
    for stem in ("design", "b0_config", "b0_result", "b1_config", "b1_result",
                 "b1_independent", "v0_artifact"):
        path = b0.inside_root(ROOT / stage[f"{stem}_path"], f"A0 {stem}")
        if b0.sha256(path) != stage[f"{stem}_sha256"]:
            raise InputIntegrityError(f"A0 {stem} SHA-256 mismatch")
    for stem in ("b0_result", "b1_result", "b1_independent"):
        if json.loads((ROOT / stage[f"{stem}_path"]).read_text(encoding="utf-8")).get("passed") is not True:
            raise InputIntegrityError(f"A0 prerequisite {stem} is not PASS")
    _, cfg, baseline, d1_stage, artifact = b1.load(ROOT / stage["b1_config_path"])
    if artifact != json.loads((ROOT / stage["v0_artifact_path"]).read_text(encoding="utf-8")):
        raise InputIntegrityError("A0 artifact differs from B1 artifact")
    return stage, cfg, baseline, d1_stage, artifact


def rollout_specs(stage: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for rollout_id in stage["rollout_ids"]:
        if rollout_id == "q0_baseline":
            path, decisions, replay = None, 0, False
        elif rollout_id.endswith("_replay"):
            path, decisions, replay = "positive", 2, True
        else:
            path = "positive" if rollout_id.startswith("positive") else "negative"
            decisions = 1 if rollout_id.endswith("first_only") else 2
            replay = False
        rows.append({
            "rollout_id": rollout_id, "family_id": "positive_full" if replay else rollout_id,
            "path": path, "decision_count": decisions, "repeat_index": 1 if replay else 0,
            "data_role": "integrity_only_zero_fit_weight" if replay else
                         "authority_qualification_only_zero_fit_weight",
        })
    return rows


def candidate_center(artifact: Mapping[str, Any], candidate: str, horizon: int = 8) -> np.ndarray:
    return np.asarray(artifact["model"]["candidates"][candidate][str(horizon)]["center_rz_ip"][:2], dtype=float)


def select_candidate(stage: Mapping[str, Any], artifact: Mapping[str, Any], remaining_rz_mm: np.ndarray) -> str:
    norm = float(np.linalg.norm(remaining_rz_mm))
    if not np.isfinite(norm) or norm <= 0:
        raise ValueError("remaining waypoint error is not a finite nonzero vector")
    direction = remaining_rz_mm / norm
    scored = [(float(candidate_center(artifact, name) @ direction), name)
              for name in stage["candidates"]]
    return max(scored, key=lambda item: (item[0], tuple(-ord(c) for c in item[1])))[1]


def _rz_mm(state: Mapping[str, Any]) -> np.ndarray:
    return 1000.0 * np.asarray([state["r_geo_m"], state["z_geo_m"]], dtype=float)


def _run_one(cfg: Any, stage: dict[str, Any], spec: dict[str, Any], envelope: Any,
             source_reference: dict[str, Any], target_map: Mapping[str, Any],
             artifact: Mapping[str, Any]) -> dict[str, Any]:
    runner = TSCStepRunner(cfg, worker_id=f"nr1000_a0_{spec['rollout_id']}", keep_workspace=False)
    reasons: list[str] = []
    states: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    attempts = gotsc_calls = verified = reset_calls = 0
    started = time.perf_counter()
    sequence = [target_map["q0"]] * stage["horizon_steps"]
    waypoint = None
    try:
        reset_calls = 1
        live = runner.reset(episode_name=spec["rollout_id"])
        states.append(_record(cfg, live))
        reasons.extend(d0.source_mismatch_reasons(states[0], source_reference))
        origin_time = states[0]["time_ms"]
        for issue in range(stage["horizon_steps"]):
            reasons.extend(envelope.state_reasons(
                RGeoZGeoSignal.from_tsc_state(live), live["currents_a_tsc"],
                cfg.min_current_a_tsc, cfg.max_current_a_tsc))
            decision_ordinal = stage["decision_issues"].index(issue) if issue in stage["decision_issues"] else None
            if decision_ordinal is not None and decision_ordinal < spec["decision_count"]:
                current = _rz_mm(states[-1])
                if waypoint is None:
                    waypoint = current + np.asarray(stage["waypoints_mm"][spec["path"]], dtype=float)
                remaining = waypoint - current
                candidate = select_candidate(stage, artifact, remaining)
                b1.c0.d2._apply_macro(sequence, issue, candidate, target_map)
                direction = remaining / np.linalg.norm(remaining)
                decisions.append({
                    "ordinal": decision_ordinal, "issue_step": issue,
                    "state_index": issue, "candidate": candidate,
                    "current_rz_mm": current.tolist(), "waypoint_rz_mm": waypoint.tolist(),
                    "remaining_rz_mm": remaining.tolist(), "remaining_direction_rz": direction.tolist(),
                    "predicted_h8_center_rz_mm": candidate_center(artifact, candidate).tolist(),
                    "predicted_projection_mm": float(candidate_center(artifact, candidate) @ direction),
                })
            target = sequence[issue]
            exact = card15_target_decimal_a(target, cfg.turns_tsc, name=f"a0.{spec['rollout_id']}.{issue}")
            maximum = assert_exact_slew(states[-1]["active_command_decimal_a_tsc"], exact,
                                        name=f"a0.{spec['rollout_id']}.issued.{issue}")
            if reasons:
                break
            actions.append({
                "issue_step": issue, "issue_time_ms": int(live["time_ms"]),
                "effect_state_index": issue + 1, "effect_time_ms": origin_time + issue + 1,
                "expected_card15_fields": list(target.card15_fields),
                "maximum_issued_delta_a": maximum,
            })
            attempts += 1
            live = runner.step_current_a(np.asarray(target.current_a_tsc, dtype=float))
            gotsc_calls += 1
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
                    name=f"a0.{spec['rollout_id']}.observed.{issue}")
            reasons.extend(envelope.state_reasons(
                RGeoZGeoSignal.from_tsc_state(live), live["currents_a_tsc"],
                cfg.min_current_a_tsc, cfg.max_current_a_tsc))
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
    complete = (not reasons and reset_calls == 1 and
                attempts == gotsc_calls == verified == stage["horizon_steps"] and
                len(actions) == stage["horizon_steps"] and len(states) == stage["horizon_steps"] + 1 and
                len(decisions) == spec["decision_count"] and
                tuple(states[-1]["active_command_card15_fields"]) == tuple(target_map["q0"].card15_fields))
    return {**spec, "passed": complete, "reasons": reasons, "reset_calls": reset_calls,
            "advance_attempts": attempts, "gotsc_calls": gotsc_calls,
            "verified_plant_advances": verified, "states": states, "actions": actions,
            "decisions": decisions, "wall_time_s": time.perf_counter() - started}


def response(full: Mapping[str, Any], matched: Mapping[str, Any], origin: int, horizon: int) -> np.ndarray:
    a, b = full["states"][origin + horizon], matched["states"][origin + horizon]
    return np.asarray([1000.0 * (a["r_geo_m"] - b["r_geo_m"]),
                       1000.0 * (a["z_geo_m"] - b["z_geo_m"]),
                       a["ip_a"] - b["ip_a"]], dtype=float)


def compare_prefix(left: Mapping[str, Any], right: Mapping[str, Any],
                   state_count: int, action_count: int) -> dict[str, Any]:
    failures = []
    if len(left["states"]) < state_count or len(right["states"]) < state_count:
        failures.append("STATE_COUNT")
    if len(left.get("actions", [])) < action_count or len(right.get("actions", [])) < action_count:
        failures.append("ACTION_COUNT")
    for index, (a, b) in enumerate(zip(left["states"][:state_count], right["states"][:state_count])):
        for key, tolerance in (("r_geo_m", 1e-12), ("z_geo_m", 1e-12), ("ip_a", 1e-9)):
            if abs(float(a[key]) - float(b[key])) > tolerance:
                failures.append(f"{key.upper()}:{index}")
        for key in ("actual_current_a_tsc", "wire_current_a"):
            if key in a or key in b:
                if len(a.get(key, [])) != len(b.get(key, [])) or any(
                        abs(float(x) - float(y)) > 1e-9 for x, y in zip(a.get(key, []), b.get(key, []))):
                    failures.append(f"{key.upper()}:{index}")
        if "artifact_sha256" in a or "artifact_sha256" in b:
            for name in b0.SEMANTIC_ARTIFACTS:
                if a.get("artifact_sha256", {}).get(name) != b.get("artifact_sha256", {}).get(name):
                    failures.append(f"SEMANTIC_ARTIFACT:{name}:{index}")
    if left.get("actions", [])[:action_count] != right.get("actions", [])[:action_count]:
        failures.append("ACTIONS")
    return {"passed": not failures, "failures": list(dict.fromkeys(failures))}


def scientific_metrics(rows: Mapping[str, dict[str, Any]], stage: Mapping[str, Any],
                       artifact: Mapping[str, Any]) -> dict[str, Any]:
    prefix_checks = []
    for left_id, right_id, state_count, action_count in (
        ("positive_first_only", "q0_baseline", 25, 24),
        ("negative_first_only", "q0_baseline", 25, 24),
        ("positive_full", "positive_first_only", 37, 36),
        ("negative_full", "negative_first_only", 37, 36),
    ):
        comparison = compare_prefix(rows[left_id], rows[right_id], state_count, action_count)
        failures = comparison["failures"]
        prefix_checks.append({"left": left_id, "right": right_id,
                              "state_count": state_count, "action_count": action_count,
                              "passed": not failures, "failures": failures})
    checks = []
    definitions = [
        ("positive_first", rows["positive_first_only"], rows["q0_baseline"], 24, 0),
        ("positive_second", rows["positive_full"], rows["positive_first_only"], 36, 1),
        ("negative_first", rows["negative_first_only"], rows["q0_baseline"], 24, 0),
        ("negative_second", rows["negative_full"], rows["negative_first_only"], 36, 1),
    ]
    for name, full, matched, origin, ordinal in definitions:
        decision = full["decisions"][ordinal]
        candidate = decision["candidate"]
        horizons = []
        for horizon in (4, 8):
            actual = response(full, matched, origin, horizon)
            model = artifact["model"]["candidates"][candidate][str(horizon)]
            center = np.asarray(model["center_rz_ip"], dtype=float)
            halfwidth = np.asarray(model["halfwidth_rz_ip"], dtype=float)
            contained = bool(np.all(np.abs(actual - center) <= halfwidth + 1e-12))
            horizons.append({"horizon": horizon, "actual_rz_ip": actual.tolist(),
                             "center_rz_ip": center.tolist(), "halfwidth_rz_ip": halfwidth.tolist(),
                             "contained": contained})
        h8 = np.asarray(horizons[1]["actual_rz_ip"][:2], dtype=float)
        projection = float(h8 @ np.asarray(decision["remaining_direction_rz"], dtype=float))
        passed = (all(item["contained"] for item in horizons) and projection >= 0.10 and
                  abs(horizons[1]["actual_rz_ip"][2]) <= 400.0)
        checks.append({"name": name, "origin_issue": origin, "candidate": candidate,
                       "horizons": horizons, "h8_waypoint_projection_mm": projection,
                       "passed": passed})
    return {"passed": all(item["passed"] for item in prefix_checks + checks),
            "matched_prefix_checks": prefix_checks, "decision_checks": checks}


def compare_replay(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    comparison = d0.compare_rows(left, right)
    failures = [reason for reason in comparison["failures"] if reason not in ("STATE_COUNT", "ACTION_COUNT")]
    if len(left["states"]) != 61 or len(right["states"]) != 61:
        failures.append("STATE_COUNT")
    if len(left["actions"]) != 60 or len(right["actions"]) != 60:
        failures.append("ACTION_COUNT")
    if left["decisions"] != right["decisions"]:
        failures.append("DECISIONS")
    comparison["failures"] = list(dict.fromkeys(failures))
    comparison["passed"] = not comparison["failures"]
    return comparison


def offline(config_path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    geometry = None
    try:
        stage, cfg, _, d1_stage, artifact = load(config_path)
        source = _source(cfg)
        envelope = OneMsNR1SafetyEnvelope.from_signal(RGeoZGeoSignal.from_tsc_state(source))
        failures.extend(envelope.state_reasons(RGeoZGeoSignal.from_tsc_state(source), source["currents_a_tsc"],
                                               cfg.min_current_a_tsc, cfg.max_current_a_tsc))
        target_map = b1.c0.d2.d1.targets(d1_stage, cfg, source)
        geometry = target_map["action_geometry"]
        for candidate in stage["candidates"]:
            for horizon in (4, 8):
                center = candidate_center(artifact, candidate, horizon)
                if not np.all(np.isfinite(center)):
                    failures.append(f"MODEL_CENTER:{candidate}:{horizon}")
        for phase in stage["decision_issues"]:
            for candidate in stage["candidates"]:
                sequence = [target_map["q0"]] * stage["horizon_steps"]
                b1.c0.d2._apply_macro(sequence, phase, candidate, target_map)
                active = tuple(source["active_command_decimal_a_tsc"])
                for issue, target in enumerate(sequence):
                    exact = card15_target_decimal_a(
                        target, cfg.turns_tsc, name=f"a0.offline.{phase}.{candidate}.{issue}")
                    assert_exact_slew(active, exact,
                                      name=f"a0.offline.{phase}.{candidate}.{issue}")
                    active = exact
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
        stage = None
    failures = list(dict.fromkeys(failures))
    routes = (stage or {}).get("routes", {})
    return {"schema_version": SCHEMA, "kind": "offline_preflight",
            "created_utc": datetime.now(timezone.utc).isoformat(), "source_revision": source_revision,
            "passed": not failures, "route": routes.get("offline_pass") if not failures else
            routes.get("offline_fail", "ONE_MS_NR1000A0_OFFLINE_FAIL_NO_TSC"),
            "failures": failures, "authorized_reset_calls": 6,
            "authorized_plant_advances": 360, "action_geometry": geometry,
            "v0_artifact_sha256": (stage or {}).get("v0_artifact_sha256")}


def run(config_path: Path, source_revision: str, output_dir: Path) -> dict[str, Any]:
    preflight = offline(config_path, source_revision)
    if not preflight["passed"]:
        raise RuntimeError("A0 offline gate failed; TSC forbidden")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {output_dir}")
    output_dir.mkdir(parents=True)
    b0.write_new(output_dir / "offline_preflight.json", preflight)
    stage, cfg, baseline, d1_stage, artifact = load(config_path)
    cfg.run_root = output_dir / "rollouts"
    source = _source(cfg)
    target_map = b1.c0.d2.d1.targets(d1_stage, cfg, source)
    envelope = OneMsNR1SafetyEnvelope.from_signal(RGeoZGeoSignal.from_tsc_state(source))
    rows: dict[str, dict[str, Any]] = {}
    for spec in rollout_specs(stage):
        row = _run_one(cfg, stage, spec, envelope, baseline["states"][0], target_map, artifact)
        rows[spec["rollout_id"]] = row
        b0.write_new(output_dir / f"{spec['rollout_id']}.json", row)
        if not row["passed"]:
            break
    execution_pass = len(rows) == 6 and all(row["passed"] for row in rows.values())
    replay = compare_replay(rows["positive_full"], rows["positive_full_replay"]) if execution_pass else None
    replay_pass = replay is not None and replay["passed"]
    metrics = scientific_metrics(rows, stage, artifact) if execution_pass else None
    authority_pass = metrics is not None and metrics["passed"]
    passed = execution_pass and replay_pass and authority_pass
    route = stage["routes"]["pass"] if passed else (stage["routes"]["execution_fail"] if not execution_pass
            else stage["routes"]["replay_fail"] if not replay_pass else stage["routes"]["authority_fail"])
    result = {"schema_version": SCHEMA, "kind": "authentic_fixed_1000_sequential_authority_l0",
              "created_utc": datetime.now(timezone.utc).isoformat(), "source_revision": source_revision,
              "passed": passed, "route": route, "rollout_count": len(rows),
              "reset_calls": sum(r["reset_calls"] for r in rows.values()),
              "advance_attempts": sum(r["advance_attempts"] for r in rows.values()),
              "gotsc_calls": sum(r["gotsc_calls"] for r in rows.values()),
              "verified_plant_advances": sum(r["verified_plant_advances"] for r in rows.values()),
              "v0_artifact_sha256": stage["v0_artifact_sha256"],
              "action_geometry": target_map["action_geometry"], "replay": replay,
              "scientific_metrics": metrics,
              "claim_boundary": "fixed-1000 finite two-decision Authority-L0 only; no capture/recourse/path tracking"}
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
