#!/usr/bin/env python3
"""Independent raw audit for fixed-1000 finite feedback F0."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import rgeo_zgeo_1ms_1000_authority_a0_independent as a0audit  # noqa: E402
from scripts import rgeo_zgeo_1ms_1000_feedback_f0 as primary  # noqa: E402
from scripts.rgeo_zgeo_1ms_nr1_independent import _fields, _state  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    assert_exact_slew, card15_target_decimal_a, decimal_single_turn_currents_a,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _reference_failures(run_dir: Path, rollout_id: str, states: list[dict[str, Any]],
                        reference: dict[str, Any]) -> list[str]:
    failures = []
    if len(states) != 65 or len(reference.get("states", [])) < 65:
        return ["STATE_COUNT"]
    for index, (state, expected) in enumerate(zip(states, reference["states"][:65])):
        for key, tolerance in (("r_geo_m", 1e-12), ("z_geo_m", 1e-12),
                               ("r_mid_m", 1e-12), ("ip_a", 1e-9)):
            if abs(float(state[key]) - float(expected[key])) > tolerance:
                failures.append(f"{key.upper()}:{index}")
        for raw_key, compact_key, count in (("current_a_tsc", "actual_current_a_tsc", 14),
                                             ("wire_a", "wire_current_a", 48)):
            actual = state[raw_key]
            frozen = expected[compact_key]
            if len(actual) != count or len(frozen) != count:
                failures.append(f"{raw_key.upper()}_LENGTH:{index}")
            elif max(abs(float(a) - float(b)) for a, b in zip(actual, frozen)) > 1e-9:
                failures.append(f"{raw_key.upper()}:{index}")
        # Raw state folders 0..63 contain the outgoing issue inputa after the
        # runner rewrite, whereas the compact state captured the preissue
        # inputa.  The outgoing Card15 fields are checked independently below;
        # compare only the three immutable state artifacts to the frozen
        # preissue reference here.
        for name in tuple(name for name in primary.b0.SEMANTIC_ARTIFACTS if name != "inputa"):
            path = run_dir / "rollouts" / rollout_id / f"{1000 + index}ms" / name
            if _sha256(path) != expected["artifact_sha256"][name]:
                failures.append(f"SEMANTIC_ARTIFACT:{name}:{index}")
    return list(dict.fromkeys(failures))


def audit(config_path: Path, run_dir: Path, source_revision: str) -> dict[str, Any]:
    stage, cfg, baseline, d1_stage, artifact = primary.load(config_path)
    run_dir = primary.b0.inside_root(run_dir, "F0 run directory")
    failures = []
    expected_times = list(range(1000, 1065))
    source_command = decimal_single_turn_currents_a(
        tuple(v.strip() for v in _fields(cfg.simulation_root / cfg.start_folder / "inputa")),
        cfg.turns_tsc, name="f0.audit.source")
    rows = {}
    raw_states = action_checks = observed_checks = 0
    target_map = None
    for spec in primary.specs(stage):
        rollout_id = spec["rollout_id"]
        root = run_dir / "rollouts" / rollout_id
        times = sorted(int(p.name[:-2]) for p in root.iterdir()
                       if p.is_dir() and p.name.endswith("ms") and p.name[:-2].isdigit()) \
            if root.is_dir() else []
        if times != expected_times:
            failures.append(f"TIME_DIRECTORY_SET:{rollout_id}")
        try:
            states = [_state(root / f"{t}ms", cfg) for t in expected_times]
            raw_states += len(states)
            compact = json.loads((run_dir / f"{rollout_id}.json").read_text(encoding="utf-8"))
            for index, state in enumerate(states):
                state["actual_current_a_tsc"] = list(state["current_a_tsc"])
                state["wire_current_a"] = list(state["wire_a"])
                state["artifact_sha256"] = {
                    name: (_sha256(root / f"{1000 + index}ms" / name)
                           if name != "inputa" else
                           compact["states"][index]["artifact_sha256"][name])
                    for name in primary.b0.SEMANTIC_ARTIFACTS
                }
            compact["states"] = states
            rows[rollout_id] = compact
            failures.extend(
                f"SOURCE:{rollout_id}:{reason}" for reason in
                a0audit.d0audit._source_reasons(run_dir, rollout_id, states[0], baseline["states"][0])
            )
            if target_map is None:
                source = {"currents_a_tsc": states[0]["current_a_tsc"],
                          "active_command_decimal_a_tsc": source_command}
                target_map = primary.a0.b1.c0.d2.d1.targets(d1_stage, cfg, source)
            sequence = [target_map["q0"]] * 64
            expected_decisions = []
            for ordinal, issue in enumerate(stage["decision_issues"] if spec["path"] else []):
                current = primary._rz_mm(states[issue])
                reference = primary._rz_mm(baseline["states"][issue])
                command = np.asarray(stage["paths_mm_relative_q0"][spec["path"]][ordinal])
                candidate, before, after = primary.select(stage, artifact, current - reference, command)
                primary.a0.b1.c0.d2._apply_macro(sequence, issue, candidate, target_map)
                expected_decisions.append((issue, candidate, before, after))
            if len(compact["decisions"]) != len(expected_decisions):
                failures.append(f"DECISION_COUNT:{rollout_id}")
            for got, expected in zip(compact["decisions"], expected_decisions):
                issue, candidate, before, after = expected
                if got.get("issue_step") != issue or got.get("candidate") != candidate:
                    failures.append(f"DECISION:{rollout_id}:{issue}")
                if abs(got.get("predicted_error_before_mm", -1) - before) > 1e-12 or abs(
                        got.get("predicted_error_after_mm", -1) - after) > 1e-12:
                    failures.append(f"DECISION_SCORE:{rollout_id}:{issue}")
            active = source_command
            for issue, target in enumerate(sequence):
                action_checks += 1
                if _fields(root / f"{1000 + issue}ms" / "inputa") != target.card15_fields:
                    failures.append(f"CARD15:{rollout_id}:{issue}")
                exact = card15_target_decimal_a(target, cfg.turns_tsc, name=f"f0.audit.{rollout_id}.{issue}")
                assert_exact_slew(active, exact, name=f"f0.audit.issue.{rollout_id}.{issue}")
                active = exact
                if issue > 0:
                    assert_exact_slew(states[issue]["current_decimal_a_tsc"],
                                      states[issue + 1]["current_decimal_a_tsc"],
                                      name=f"f0.audit.observed.{rollout_id}.{issue}")
                    observed_checks += 1
            for index, state in enumerate(states):
                if state["time_ms"] != 1000 + index or state["abnormal"]:
                    failures.append(f"STATE:{rollout_id}:{index}")
                if not state["r_inner_m"] <= state["r_geo_m"] <= state["r_outer_m"]:
                    failures.append(f"LIMITER:{rollout_id}:{index}")
                if abs(state["r_geo_m"] - states[0]["r_geo_m"]) > .05:
                    failures.append(f"R_ENVELOPE:{rollout_id}:{index}")
                if abs(state["z_geo_m"] - states[0]["z_geo_m"]) > .05:
                    failures.append(f"Z_ENVELOPE:{rollout_id}:{index}")
                if abs(state["ip_a"] - states[0]["ip_a"]) > .10 * abs(states[0]["ip_a"]):
                    failures.append(f"IP_ENVELOPE:{rollout_id}:{index}")
                if len(state["current_a_tsc"]) != 14 or any(
                        value < lower or value > upper for value, lower, upper in zip(
                            state["current_a_tsc"], cfg.min_current_a_tsc, cfg.max_current_a_tsc)):
                    failures.append(f"ABSOLUTE_CURRENT:{rollout_id}:{index}")
        except Exception as exc:
            failures.append(f"RAW:{rollout_id}:{type(exc).__name__}:{exc}")
            rows.setdefault(rollout_id, {})
    complete = len(rows) == 4 and all(len(row.get("states", [])) == 65 for row in rows.values())
    measured = primary.metrics(rows, stage, baseline, artifact) if complete else None
    if complete:
        failures.extend(
            f"Q0_REFERENCE:{reason}" for reason in
            _reference_failures(run_dir, "q0_baseline", rows["q0_baseline"]["states"], baseline)
        )
    replay = a0audit._semantic_compare(run_dir, "path_a", "path_a_replay",
                                       rows.get("path_a", {}).get("states", []),
                                       rows.get("path_a_replay", {}).get("states", []), 65)
    failures.extend(f"REPLAY:{r}" for r in replay["failures"])
    try:
        reported = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    except Exception as exc:
        failures.append(f"PRIMARY_RESULT:{type(exc).__name__}:{exc}")
        reported = {}
    expected_pass = complete and measured is not None and measured["passed"] and replay["passed"]
    expected_route = stage["routes"]["pass"] if expected_pass else (
        stage["routes"]["execution_fail"] if not complete else stage["routes"]["reference_fail"]
        if not measured["q0_reference_replay"]["passed"] else stage["routes"]["replay_fail"]
        if not measured["path_a_replay"]["passed"] else stage["routes"]["tracking_fail"])
    for key, value in {"rollout_count": 4, "reset_calls": 4, "advance_attempts": 256,
                       "gotsc_calls": 256, "verified_plant_advances": 256}.items():
        if reported.get(key) != value:
            failures.append(f"PRIMARY_COUNTER:{key}")
    if reported.get("source_revision") != source_revision:
        failures.append("PRIMARY_SOURCE_REVISION")
    if reported.get("passed") is not expected_pass or reported.get("route") != expected_route:
        failures.append("PRIMARY_VERDICT")
    if measured is None or not a0audit.d0audit._close(measured, reported.get("metrics")):
        failures.append("PRIMARY_METRICS")
    failures = list(dict.fromkeys(failures))
    result = {"schema_version": f"{primary.SCHEMA}-independent", "kind": "independent_raw_audit",
        "created_utc": datetime.now(timezone.utc).isoformat(), "source_revision": source_revision,
        "passed": not failures, "route": "ONE_MS_NR1000F0_INDEPENDENT_PASS" if not failures else
        "ONE_MS_NR1000F0_INDEPENDENT_FAIL", "failures": failures,
        "primary_scientific_passed": expected_pass, "primary_scientific_route": expected_route,
        "raw_states": raw_states, "action_checks": action_checks,
        "observed_slew_checks": observed_checks, "metrics": measured}
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
