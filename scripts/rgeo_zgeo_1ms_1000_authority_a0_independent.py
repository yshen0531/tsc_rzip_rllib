#!/usr/bin/env python3
"""Independent raw reconstruction of fixed-1000 Authority A0."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_1000_authority_a0 as primary  # noqa: E402
from scripts import rgeo_zgeo_1ms_1000_signed_temporal_d0_independent as d0audit  # noqa: E402
from scripts.rgeo_zgeo_1ms_nr1_independent import _fields, _state  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    assert_exact_slew, card15_target_decimal_a, decimal_single_turn_currents_a,
)


def _select(stage: dict[str, Any], artifact: dict[str, Any], remaining: np.ndarray) -> str:
    direction = remaining / np.linalg.norm(remaining)
    scores = []
    for name in stage["candidates"]:
        center = np.asarray(artifact["model"]["candidates"][name]["8"]["center_rz_ip"][:2])
        scores.append((float(center @ direction), name))
    best = max(score for score, _ in scores)
    return sorted(name for score, name in scores if abs(score - best) <= 1e-15)[0]


def _semantic_compare(run_dir: Path, left_id: str, right_id: str,
                      left: list[dict[str, Any]], right: list[dict[str, Any]], count: int,
                      final_state_inputa_is_outgoing: bool = False) -> dict[str, Any]:
    failures = []
    maxima = {"geometry_m": 0.0, "ip_a": 0.0, "coil_a": 0.0, "wire_a": 0.0}
    if len(left) < count or len(right) < count:
        failures.append("STATE_COUNT")
    for index, (a, b) in enumerate(zip(left[:count], right[:count])):
        maxima["geometry_m"] = max(maxima["geometry_m"], *(
            abs(a[key] - b[key]) for key in ("r_geo_m", "z_geo_m", "r_mid_m")))
        maxima["ip_a"] = max(maxima["ip_a"], abs(a["ip_a"] - b["ip_a"]))
        maxima["coil_a"] = max(maxima["coil_a"], d0audit._maxdiff(a["current_a_tsc"], b["current_a_tsc"]))
        maxima["wire_a"] = max(maxima["wire_a"], d0audit._maxdiff(a["wire_a"], b["wire_a"]))
        for name in primary.b0.SEMANTIC_ARTIFACTS:
            if final_state_inputa_is_outgoing and index == count - 1 and name == "inputa":
                continue
            left_path = run_dir / "rollouts" / left_id / f"{1000 + index}ms" / name
            right_path = run_dir / "rollouts" / right_id / f"{1000 + index}ms" / name
            if primary.b0.sha256(left_path) != primary.b0.sha256(right_path):
                failures.append(f"SEMANTIC_ARTIFACT:{name}:{index}")
    for key, tolerance in (("geometry_m", 1e-12), ("ip_a", 1e-9),
                           ("coil_a", 1e-9), ("wire_a", 1e-9)):
        if maxima[key] > tolerance:
            failures.append(key.upper())
    return {"passed": not failures, "failures": list(dict.fromkeys(failures)),
            "maximum_absolute_difference": maxima}


def _responses(run_dir: Path, rows: dict[str, list[dict[str, Any]]],
               decisions: dict[str, list[dict[str, Any]]], artifact: dict[str, Any]) -> dict[str, Any]:
    prefix_checks = []
    for left_id, right_id, count in (
        ("positive_first_only", "q0_baseline", 25),
        ("negative_first_only", "q0_baseline", 25),
        ("positive_full", "positive_first_only", 37),
        ("negative_full", "negative_first_only", 37),
    ):
        comparison = _semantic_compare(run_dir, left_id, right_id, rows[left_id], rows[right_id], count,
                                       final_state_inputa_is_outgoing=True)
        prefix_checks.append({"left": left_id, "right": right_id, "state_count": count,
                              "action_count": count - 1, "passed": comparison["passed"],
                              "failures": comparison["failures"]})
    checks = []
    definitions = [
        ("positive_first", "positive_first_only", "q0_baseline", 24, 0),
        ("positive_second", "positive_full", "positive_first_only", 36, 1),
        ("negative_first", "negative_first_only", "q0_baseline", 24, 0),
        ("negative_second", "negative_full", "negative_first_only", 36, 1),
    ]
    for label, full_id, base_id, origin, ordinal in definitions:
        decision = decisions[full_id][ordinal]
        candidate = decision["candidate"]
        horizon_rows = []
        for horizon in (4, 8):
            full, base = rows[full_id][origin + horizon], rows[base_id][origin + horizon]
            actual = np.asarray([1000 * (full["r_geo_m"] - base["r_geo_m"]),
                                 1000 * (full["z_geo_m"] - base["z_geo_m"]),
                                 full["ip_a"] - base["ip_a"]])
            model = artifact["model"]["candidates"][candidate][str(horizon)]
            center, width = np.asarray(model["center_rz_ip"]), np.asarray(model["halfwidth_rz_ip"])
            horizon_rows.append({"horizon": horizon, "actual_rz_ip": actual.tolist(),
                                 "center_rz_ip": center.tolist(), "halfwidth_rz_ip": width.tolist(),
                                 "contained": bool(np.all(np.abs(actual - center) <= width + 1e-12))})
        projection = float(np.asarray(horizon_rows[1]["actual_rz_ip"][:2]) @
                           np.asarray(decision["remaining_direction_rz"]))
        passed = all(row["contained"] for row in horizon_rows) and projection >= 0.10 and abs(
            horizon_rows[1]["actual_rz_ip"][2]) <= 400
        checks.append({"name": label, "origin_issue": origin, "candidate": candidate,
                       "horizons": horizon_rows, "h8_waypoint_projection_mm": projection,
                       "passed": passed})
    return {"passed": all(row["passed"] for row in prefix_checks + checks),
            "matched_prefix_checks": prefix_checks, "decision_checks": checks}


def audit(config_path: Path, run_dir: Path, source_revision: str) -> dict[str, Any]:
    stage, cfg, baseline, d1_stage, artifact = primary.load(config_path)
    run_dir = primary.b0.inside_root(run_dir, "A0 run directory")
    failures: list[str] = []
    expected_times = list(range(1000, 1061))
    specs = primary.rollout_specs(stage)
    source_command = decimal_single_turn_currents_a(
        tuple(value.strip() for value in _fields(cfg.simulation_root / cfg.start_folder / "inputa")),
        cfg.turns_tsc, name="a0.audit.source_command")
    rows: dict[str, list[dict[str, Any]]] = {}
    decisions: dict[str, list[dict[str, Any]]] = {}
    raw_states = action_checks = observed_checks = 0
    target_map = None
    for spec in specs:
        rollout_id = spec["rollout_id"]
        root = run_dir / "rollouts" / rollout_id
        actual_times = sorted(int(p.name[:-2]) for p in root.iterdir()
                              if p.is_dir() and p.name.endswith("ms") and p.name[:-2].isdigit()) \
            if root.is_dir() else []
        if actual_times != expected_times:
            failures.append(f"TIME_DIRECTORY_SET:{rollout_id}")
        try:
            states = [_state(root / f"{time_ms}ms", cfg) for time_ms in expected_times]
            rows[rollout_id] = states
            raw_states += len(states)
            failures.extend(f"SOURCE:{rollout_id}:{reason}" for reason in d0audit._source_reasons(
                run_dir, rollout_id, states[0], baseline["states"][0]))
            if target_map is None:
                source = {"currents_a_tsc": states[0]["current_a_tsc"],
                          "active_command_decimal_a_tsc": source_command}
                target_map = primary.b1.c0.d2.d1.targets(d1_stage, cfg, source)
            compact = json.loads((run_dir / f"{rollout_id}.json").read_text(encoding="utf-8"))
            sequence = [target_map["q0"]] * stage["horizon_steps"]
            expected_decisions = []
            waypoint = None
            for ordinal, issue in enumerate(stage["decision_issues"][:spec["decision_count"]]):
                current = 1000 * np.asarray([states[issue]["r_geo_m"], states[issue]["z_geo_m"]])
                if waypoint is None:
                    waypoint = current + np.asarray(stage["waypoints_mm"][spec["path"]])
                remaining = waypoint - current
                candidate = _select(stage, artifact, remaining)
                primary.b1.c0.d2._apply_macro(sequence, issue, candidate, target_map)
                expected_decisions.append({"ordinal": ordinal, "issue_step": issue,
                                           "candidate": candidate,
                                           "remaining_direction_rz": (remaining / np.linalg.norm(remaining)).tolist()})
            decisions[rollout_id] = compact.get("decisions", [])
            if len(decisions[rollout_id]) != len(expected_decisions):
                failures.append(f"DECISION_COUNT:{rollout_id}")
            for got, expected in zip(decisions[rollout_id], expected_decisions):
                if any(got.get(key) != expected[key] for key in ("ordinal", "issue_step", "candidate")):
                    failures.append(f"DECISION_IDENTITY:{rollout_id}:{expected['ordinal']}")
                if not np.allclose(got.get("remaining_direction_rz"), expected["remaining_direction_rz"],
                                   rtol=0, atol=1e-12):
                    failures.append(f"DECISION_DIRECTION:{rollout_id}:{expected['ordinal']}")
            active = source_command
            for issue, target in enumerate(sequence):
                action_checks += 1
                if _fields(root / f"{1000 + issue}ms" / "inputa") != target.card15_fields:
                    failures.append(f"CARD15:{rollout_id}:{issue}")
                exact = card15_target_decimal_a(target, cfg.turns_tsc,
                                                 name=f"a0.audit.{rollout_id}.{issue}")
                assert_exact_slew(active, exact, name=f"a0.audit.issue.{rollout_id}.{issue}")
                active = exact
                if issue > 0:
                    assert_exact_slew(states[issue]["current_decimal_a_tsc"],
                                      states[issue + 1]["current_decimal_a_tsc"],
                                      name=f"a0.audit.observed.{rollout_id}.{issue}")
                    observed_checks += 1
            if _fields(root / "1060ms" / "inputa") != target_map["q0"].card15_fields:
                failures.append(f"FINAL_ACTIVE_NOT_Q0:{rollout_id}")
            for index, state in enumerate(states):
                if state["time_ms"] != 1000 + index or state["abnormal"]:
                    failures.append(f"STATE_OR_TIME:{rollout_id}:{index}")
                if not state["r_inner_m"] <= state["r_geo_m"] <= state["r_outer_m"]:
                    failures.append(f"LIMITER:{rollout_id}:{index}")
                if abs(state["r_geo_m"] - states[0]["r_geo_m"]) > 0.05:
                    failures.append(f"R_ENVELOPE:{rollout_id}:{index}")
                if abs(state["z_geo_m"] - states[0]["z_geo_m"]) > 0.05:
                    failures.append(f"Z_ENVELOPE:{rollout_id}:{index}")
                if (state["ip_a"] * states[0]["ip_a"] <= 0 or
                        abs(state["ip_a"] - states[0]["ip_a"]) > .10 * abs(states[0]["ip_a"])):
                    failures.append(f"IP_ENVELOPE:{rollout_id}:{index}")
        except Exception as exc:
            failures.append(f"RAW:{rollout_id}:{type(exc).__name__}:{exc}")
            rows.setdefault(rollout_id, [])
            decisions.setdefault(rollout_id, [])
    replay = _semantic_compare(run_dir, "positive_full", "positive_full_replay",
                               rows.get("positive_full", []), rows.get("positive_full_replay", []), 61)
    failures.extend(f"REPLAY:{reason}" for reason in replay["failures"])
    complete = len(rows) == 6 and all(len(rows.get(spec["rollout_id"], [])) == 61 for spec in specs)
    metrics = _responses(run_dir, rows, decisions, artifact) if complete else None
    try:
        reported = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    except Exception as exc:
        failures.append(f"PRIMARY_RESULT:{type(exc).__name__}:{exc}")
        reported = {}
    expected_pass = complete and replay["passed"] and metrics is not None and metrics["passed"]
    expected_route = stage["routes"]["pass"] if expected_pass else (
        stage["routes"]["execution_fail"] if not complete else stage["routes"]["replay_fail"]
        if not replay["passed"] else stage["routes"]["authority_fail"])
    for key, expected in {"rollout_count": 6, "reset_calls": 6, "advance_attempts": 360,
                          "gotsc_calls": 360, "verified_plant_advances": 360,
                          "v0_artifact_sha256": stage["v0_artifact_sha256"]}.items():
        if reported.get(key) != expected:
            failures.append(f"PRIMARY_COUNTER_OR_IDENTITY:{key}")
    if reported.get("source_revision") != source_revision:
        failures.append("PRIMARY_SOURCE_REVISION")
    if reported.get("passed") is not expected_pass or reported.get("route") != expected_route:
        failures.append("PRIMARY_VERDICT")
    if metrics is None or not d0audit._close(metrics, reported.get("scientific_metrics")):
        failures.append("PRIMARY_SCIENTIFIC_METRICS")
    failures = list(dict.fromkeys(failures))
    result = {"schema_version": f"{primary.SCHEMA}-independent", "kind": "independent_raw_audit",
              "created_utc": datetime.now(timezone.utc).isoformat(), "source_revision": source_revision,
              "passed": not failures,
              "route": "ONE_MS_NR1000A0_INDEPENDENT_PASS" if not failures else
                       "ONE_MS_NR1000A0_INDEPENDENT_FAIL",
              "failures": failures, "primary_scientific_passed": expected_pass,
              "primary_scientific_route": expected_route, "raw_rollouts": sum(len(v) == 61 for v in rows.values()),
              "raw_states": raw_states, "action_checks": action_checks,
              "observed_slew_checks": observed_checks, "replay": replay,
              "scientific_metrics": metrics}
    primary.b0.write_new(run_dir / "independent_audit.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    result = audit(args.config.resolve(), args.run_dir.resolve(), args.source_revision)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
