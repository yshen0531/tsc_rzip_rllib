#!/usr/bin/env python3
"""Independent raw audit for fixed-1000 radial nominal N0."""

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

from scripts import rgeo_zgeo_1ms_1000_radial_nominal_n0 as primary  # noqa: E402
from scripts import rgeo_zgeo_1ms_1000_signed_temporal_d0_independent as d0audit  # noqa: E402
from scripts.rgeo_zgeo_1ms_nr1_independent import _fields, _state  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    assert_exact_slew,
    card15_target_decimal_a,
    decimal_single_turn_currents_a,
)


def semantic_replay(
    run_dir: Path, left_id: str, right_id: str,
    left: list[dict[str, Any]], right: list[dict[str, Any]],
) -> dict[str, Any]:
    failures: list[str] = []
    maxima = {"geometry_m": 0.0, "ip_a": 0.0, "coil_a": 0.0, "wire_a": 0.0}
    if len(left) != 65 or len(right) != 65:
        failures.append("STATE_COUNT")
    for index, (a, b) in enumerate(zip(left, right)):
        maxima["geometry_m"] = max(
            maxima["geometry_m"],
            *(abs(a[key] - b[key]) for key in ("r_geo_m", "z_geo_m", "r_mid_m")),
        )
        maxima["ip_a"] = max(maxima["ip_a"], abs(a["ip_a"] - b["ip_a"]))
        maxima["coil_a"] = max(maxima["coil_a"], d0audit._maxdiff(a["current_a_tsc"], b["current_a_tsc"]))
        maxima["wire_a"] = max(maxima["wire_a"], d0audit._maxdiff(a["wire_a"], b["wire_a"]))
        for name in primary.SEMANTIC_ARTIFACTS:
            left_path = run_dir / "rollouts" / left_id / f"{1000 + index}ms" / name
            right_path = run_dir / "rollouts" / right_id / f"{1000 + index}ms" / name
            if primary.b0.sha256(left_path) != primary.b0.sha256(right_path):
                failures.append(f"SEMANTIC_ARTIFACT:{name}:{index}")
    for key, tolerance in (("geometry_m", 1e-12), ("ip_a", 1e-9), ("coil_a", 1e-9), ("wire_a", 1e-9)):
        if maxima[key] > tolerance:
            failures.append(key.upper())
    return {
        "passed": not failures, "failures": list(dict.fromkeys(failures)),
        "maximum_absolute_difference": maxima,
    }


def audit(config_path: Path, run_dir: Path, source_revision: str) -> dict[str, Any]:
    stage, cfg, baseline = primary.load(config_path)
    run_dir = primary.b0.inside_root(run_dir, "N0 run directory")
    failures: list[str] = []
    expected_times = list(range(1000, 1065))
    specs = primary.rollout_specs(stage)
    source_fields = _fields(cfg.simulation_root / cfg.start_folder / "inputa")
    source_command = decimal_single_turn_currents_a(
        tuple(value.strip() for value in source_fields), cfg.turns_tsc,
        name="n0.independent.source_command",
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
                for reason in d0audit._source_reasons(run_dir, rollout_id, states[0], baseline["states"][0])
            )
            if target_map is None:
                source = {
                    "currents_a_tsc": states[0]["current_a_tsc"],
                    "active_command_decimal_a_tsc": source_command,
                }
                target_map = primary.targets(stage, cfg, source)
            sequence = primary.sequence_for(spec, stage, target_map)
            active = source_command
            for issue, target in enumerate(sequence):
                action_checks += 1
                if _fields(root / f"{1000 + issue}ms" / "inputa") != target.card15_fields:
                    failures.append(f"CARD15:{rollout_id}:{issue}")
                exact = card15_target_decimal_a(target, cfg.turns_tsc, name=f"n0.independent.{rollout_id}.{issue}")
                assert_exact_slew(active, exact, name=f"n0.independent.issue.{rollout_id}.{issue}")
                active = exact
                if issue > 0:
                    assert_exact_slew(
                        states[issue]["current_decimal_a_tsc"], states[issue + 1]["current_decimal_a_tsc"],
                        name=f"n0.independent.observed.{rollout_id}.{issue}",
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
    replay = semantic_replay(
        run_dir, base, f"{base}_replay", rows.get(base, []), rows.get(f"{base}_replay", []),
    )
    failures.extend(f"REPLAY:{reason}" for reason in replay["failures"])
    metrics = None
    if all(len(rows.get(spec["rollout_id"], [])) == 65 for spec in specs):
        metrics = primary.scientific_metrics(
            [{**spec, "states": rows[spec["rollout_id"]]} for spec in specs if spec["repeat_index"] == 0],
            baseline["states"], stage,
        )
    try:
        primary_result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    except Exception as exc:
        failures.append(f"PRIMARY_RESULT:{type(exc).__name__}:{exc}")
        primary_result = {}
    execution_pass = len(rows) == 5 and all(len(value) == 65 for value in rows.values())
    replay_pass = replay["passed"]
    scientific_pass = metrics is not None and metrics["passed"]
    expected_passed = execution_pass and replay_pass and scientific_pass
    expected_route = stage["routes"]["pass"] if expected_passed else (
        stage["routes"]["execution_fail"] if not execution_pass
        else stage["routes"]["replay_fail"] if not replay_pass
        else stage["routes"]["scientific_fail"]
    )
    for key, expected in {
        "rollout_count": 5, "reset_calls": 5, "advance_attempts": 320,
        "gotsc_calls": 320, "verified_plant_advances": 320,
    }.items():
        if primary_result.get(key) != expected:
            failures.append(f"PRIMARY_COUNTER:{key}")
    if primary_result.get("source_revision") != source_revision:
        failures.append("PRIMARY_SOURCE_REVISION")
    if primary_result.get("passed") is not expected_passed or primary_result.get("route") != expected_route:
        failures.append("PRIMARY_VERDICT")
    if metrics is None or not d0audit._close(metrics, primary_result.get("scientific_metrics")):
        failures.append("PRIMARY_SCIENTIFIC_METRICS")
    if target_map is None or not d0audit._close(target_map["action_geometry"], primary_result.get("action_geometry")):
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
