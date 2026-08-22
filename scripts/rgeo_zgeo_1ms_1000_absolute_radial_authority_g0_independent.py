#!/usr/bin/env python3
"""Structurally separate raw audit for fixed-1000 G0."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_1000_absolute_radial_authority_g0 as primary  # noqa: E402
from scripts import rgeo_zgeo_1ms_1000_radial_nominal_n0_independent as n0audit  # noqa: E402
from scripts import rgeo_zgeo_1ms_1000_signed_temporal_d0_independent as d0audit  # noqa: E402
from scripts.rgeo_zgeo_1ms_nr1_independent import _fields, _state  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    assert_exact_slew,
    card15_target_decimal_a,
    decimal_single_turn_currents_a,
)


def audit(config_path: Path, run_dir: Path, source_revision: str) -> dict[str, Any]:
    stage, cfg, prior_baseline = primary.load(config_path)
    run_dir = primary.b0.inside_root(run_dir, "G0 run directory")
    failures: list[str] = []
    expected_times = list(range(1000, 1065))
    specs = primary.rollout_specs(stage)
    source_fields = _fields(cfg.simulation_root / cfg.start_folder / "inputa")
    source_command = decimal_single_turn_currents_a(
        tuple(value.strip() for value in source_fields), cfg.turns_tsc,
        name="g0.independent.source_command",
    )
    rows: dict[str, list[dict[str, Any]]] = {}
    target_map = None
    action_checks = observed_checks = raw_states = 0
    for spec in specs:
        rollout_id = spec["rollout_id"]
        root = run_dir / "rollouts" / rollout_id
        actual_times = sorted(
            int(path.name[:-2]) for path in root.iterdir()
            if path.is_dir() and path.name.endswith("ms") and path.name[:-2].isdigit()
        ) if root.is_dir() else []
        if actual_times != expected_times:
            failures.append(f"TIME_DIRECTORY_SET:{rollout_id}")
        try:
            states = [_state(root / f"{time_ms}ms", cfg) for time_ms in expected_times]
            rows[rollout_id] = states
            raw_states += len(states)
            failures.extend(
                f"SOURCE:{rollout_id}:{reason}"
                for reason in d0audit._source_reasons(
                    run_dir, rollout_id, states[0], prior_baseline["states"][0]
                )
            )
            if target_map is None:
                target_map = primary.targets(stage, cfg, {
                    "currents_a_tsc": states[0]["current_a_tsc"],
                    "active_command_decimal_a_tsc": source_command,
                })
            sequence = primary.sequence_for(spec, stage, target_map)
            active = source_command
            for issue, target in enumerate(sequence):
                action_checks += 1
                if _fields(root / f"{1000 + issue}ms" / "inputa") != target.card15_fields:
                    failures.append(f"CARD15:{rollout_id}:{issue}")
                exact = card15_target_decimal_a(
                    target, cfg.turns_tsc, name=f"g0.independent.{rollout_id}.{issue}"
                )
                assert_exact_slew(active, exact, name=f"g0.independent.issue.{rollout_id}.{issue}")
                active = exact
                if issue > 0:
                    assert_exact_slew(
                        states[issue]["current_decimal_a_tsc"],
                        states[issue + 1]["current_decimal_a_tsc"],
                        name=f"g0.independent.observed.{rollout_id}.{issue}",
                    )
                    observed_checks += 1
            for index, state in enumerate(states):
                if state["time_ms"] != 1000 + index:
                    failures.append(f"TIME:{rollout_id}:{index}")
                if state["abnormal"]:
                    failures.append(f"ABNORMAL:{rollout_id}:{index}")
                if not state["r_inner_m"] <= state["r_geo_m"] <= state["r_outer_m"]:
                    failures.append(f"LIMITER:{rollout_id}:{index}")
                if abs(state["r_geo_m"] - states[0]["r_geo_m"]) > 0.05:
                    failures.append(f"R_ENVELOPE:{rollout_id}:{index}")
                if abs(state["z_geo_m"] - states[0]["z_geo_m"]) > 0.05:
                    failures.append(f"Z_ENVELOPE:{rollout_id}:{index}")
                if state["ip_a"] * states[0]["ip_a"] <= 0 or abs(
                    state["ip_a"] - states[0]["ip_a"]
                ) > 0.10 * abs(states[0]["ip_a"]):
                    failures.append(f"IP_ENVELOPE:{rollout_id}:{index}")
                if any(value < low or value > high for value, low, high in zip(
                    state["current_a_tsc"], cfg.min_current_a_tsc, cfg.max_current_a_tsc
                )):
                    failures.append(f"CURRENT_LIMIT:{rollout_id}:{index}")
        except Exception as exc:
            failures.append(f"RAW:{rollout_id}:{type(exc).__name__}:{exc}")
            rows.setdefault(rollout_id, [])

    base = f"depth{stage['critical_replay_depth']:02d}"
    replay = n0audit.semantic_replay(
        run_dir, base, f"{base}_replay", rows.get(base, []), rows.get(f"{base}_replay", []),
    )
    failures.extend(f"REPLAY:{reason}" for reason in replay["failures"])
    complete = all(len(rows.get(spec["rollout_id"], [])) == 65 for spec in specs)
    metrics = primary.scientific_metrics([
        {**spec, "states": rows[spec["rollout_id"]]} for spec in specs
    ], stage) if complete else None
    try:
        primary_result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    except Exception as exc:
        failures.append(f"PRIMARY_RESULT:{type(exc).__name__}:{exc}")
        primary_result = {}
    execution_pass = complete
    matched_q0_complete = len(rows.get("matched_q0", [])) == 65
    replay_pass = replay["passed"]
    scientific_pass = metrics is not None and metrics["passed"]
    expected_passed = execution_pass and matched_q0_complete and replay_pass and scientific_pass
    expected_route = stage["routes"]["pass"] if expected_passed else (
        stage["routes"]["matched_q0_fail"] if not matched_q0_complete
        else stage["routes"]["execution_fail"] if not execution_pass
        else stage["routes"]["replay_fail"] if not replay_pass
        else stage["routes"]["scientific_fail"]
    )
    expected_counters = {
        "rollout_count": 8, "reset_calls": 8, "advance_attempts": 512,
        "gotsc_calls": 512, "verified_plant_advances": 512,
    }
    for key, expected in expected_counters.items():
        if primary_result.get(key) != expected:
            failures.append(f"PRIMARY_COUNTER:{key}")
    if primary_result.get("source_revision") != source_revision:
        failures.append("PRIMARY_SOURCE_REVISION")
    if primary_result.get("passed") is not expected_passed or primary_result.get("route") != expected_route:
        failures.append("PRIMARY_VERDICT")
    if metrics is None or not d0audit._close(metrics, primary_result.get("scientific_metrics")):
        failures.append("PRIMARY_SCIENTIFIC_METRICS")
    if target_map is None or not d0audit._close(
        target_map["action_geometry"], primary_result.get("action_geometry")
    ):
        failures.append("PRIMARY_ACTION_GEOMETRY")
    failures = list(dict.fromkeys(failures))
    result = {
        "schema_version": f"{primary.SCHEMA}-independent",
        "kind": "independent_raw_audit",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_revision": source_revision, "passed": not failures,
        "route": stage["routes"]["independent_pass"] if not failures else stage["routes"]["independent_fail"],
        "failures": failures, "primary_scientific_passed": expected_passed,
        "primary_scientific_route": expected_route,
        "raw_rollouts": sum(len(value) == 65 for value in rows.values()),
        "raw_states": raw_states, "action_checks": action_checks,
        "observed_slew_checks": observed_checks,
        "critical_replay": replay, "scientific_metrics": metrics,
    }
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
