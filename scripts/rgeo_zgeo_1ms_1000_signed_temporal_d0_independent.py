#!/usr/bin/env python3
"""Independent raw audit for the fixed-1000 signed temporal D0 campaign."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
import json
import math
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_1000_signed_temporal_d0 as primary  # noqa: E402
from scripts.rgeo_zgeo_1ms_nr1_independent import _fields, _state  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    assert_exact_slew,
    build_frozen_one_ms_prefixes,
    card15_target_decimal_a,
    decimal_single_turn_currents_a,
)


def _maxdiff(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return max(abs(a - b) for a, b in zip(left, right)) if len(left) == len(right) else math.inf


def _close(left: Any, right: Any, tolerance: float = 1e-10) -> bool:
    if isinstance(left, dict) and isinstance(right, dict):
        return set(left) == set(right) and all(_close(left[key], right[key], tolerance) for key in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(_close(a, b, tolerance) for a, b in zip(left, right))
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        if math.isinf(float(left)) or math.isinf(float(right)):
            return float(left) == float(right)
        return abs(float(left) - float(right)) <= tolerance
    return left == right


def _semantic_replay(
    run_dir: Path, left_id: str, right_id: str,
    left: list[dict[str, Any]], right: list[dict[str, Any]],
) -> dict[str, Any]:
    failures: list[str] = []
    maxima = {"geometry_m": 0.0, "ip_a": 0.0, "coil_a": 0.0, "wire_a": 0.0}
    if len(left) != 41 or len(right) != 41:
        failures.append("STATE_COUNT")
    for index, (a, b) in enumerate(zip(left, right)):
        maxima["geometry_m"] = max(
            maxima["geometry_m"],
            *(abs(a[key] - b[key]) for key in ("r_geo_m", "z_geo_m", "r_mid_m")),
        )
        maxima["ip_a"] = max(maxima["ip_a"], abs(a["ip_a"] - b["ip_a"]))
        maxima["coil_a"] = max(maxima["coil_a"], _maxdiff(a["current_a_tsc"], b["current_a_tsc"]))
        maxima["wire_a"] = max(maxima["wire_a"], _maxdiff(a["wire_a"], b["wire_a"]))
        for name in primary.SEMANTIC_ARTIFACTS:
            left_path = run_dir / "rollouts" / left_id / f"{1000 + index}ms" / name
            right_path = run_dir / "rollouts" / right_id / f"{1000 + index}ms" / name
            if primary.b0.sha256(left_path) != primary.b0.sha256(right_path):
                failures.append(f"SEMANTIC_ARTIFACT:{name}:{index}")
    for key, tolerance in (("geometry_m", 1e-12), ("ip_a", 1e-9), ("coil_a", 1e-9), ("wire_a", 1e-9)):
        if maxima[key] > tolerance:
            failures.append(key.upper())
    return {
        "passed": not failures,
        "failures": list(dict.fromkeys(failures)),
        "maximum_absolute_difference": maxima,
    }


def _source_reasons(
    run_dir: Path, rollout_id: str, state: dict[str, Any], reference: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    for key, tolerance in (
        ("r_geo_m", 1e-12), ("z_geo_m", 1e-12), ("r_mid_m", 1e-12), ("ip_a", 1e-9),
    ):
        if abs(float(state[key]) - float(reference[key])) > tolerance:
            reasons.append(f"{key.upper()}")
    for raw_key, compact_key, expected_length in (
        ("current_a_tsc", "actual_current_a_tsc", 14),
        ("wire_a", "wire_current_a", 48),
    ):
        left, right = state[raw_key], reference[compact_key]
        if len(left) != expected_length or len(right) != expected_length:
            reasons.append(f"{raw_key.upper()}_LENGTH")
        elif _maxdiff(left, tuple(float(value) for value in right)) > 1e-9:
            reasons.append(raw_key.upper())
    # The runner rewrites state0/inputa with the outgoing issue0 command after
    # the primary captured its preissue source hash.  Its Card15 fields are
    # checked independently in the action loop below.  The other state0
    # semantic artifacts remain immutable and retain byte-hash identity.
    for name in tuple(name for name in primary.SEMANTIC_ARTIFACTS if name != "inputa"):
        if primary.b0.sha256(run_dir / "rollouts" / rollout_id / "1000ms" / name) != reference[
            "artifact_sha256"
        ][name]:
            reasons.append(f"SEMANTIC_ARTIFACT:{name}")
    return reasons


def audit(config_path: Path, run_dir: Path, source_revision: str) -> dict[str, Any]:
    stage, cfg, baseline = primary.load(config_path)
    run_dir = primary.b0.inside_root(run_dir, "D0 run directory")
    failures: list[str] = []
    expected_times = list(range(1000, 1041))
    specs = primary.rollout_specs(stage)
    source_fields = _fields(cfg.simulation_root / cfg.start_folder / "inputa")
    source_command = decimal_single_turn_currents_a(
        tuple(value.strip() for value in source_fields), cfg.turns_tsc,
        name="d0.independent.source_command",
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
                for reason in _source_reasons(run_dir, rollout_id, states[0], baseline["states"][0])
            )
            if target_map is None:
                frozen = build_frozen_one_ms_prefixes(
                    source_current_a_tsc=states[0]["current_a_tsc"],
                    source_command_a_tsc=source_command,
                    turns_tsc=cfg.turns_tsc,
                    min_current_a_tsc=cfg.min_current_a_tsc,
                    max_current_a_tsc=cfg.max_current_a_tsc,
                    maximum_command_delta_a=Decimal("0.299"),
                )
                source = {
                    "currents_a_tsc": states[0]["current_a_tsc"],
                    "active_command_decimal_a_tsc": source_command,
                }
                target_map = primary.targets(stage, cfg, source)
                if tuple(card15_target_decimal_a(
                    frozen.q0, cfg.turns_tsc, name="d0.independent.q0"
                )) != tuple(source_command):
                    failures.append("SOURCE_Q0")
            sequence = primary.sequence_for(spec, stage, target_map)
            active = source_command
            for issue, target in enumerate(sequence):
                action_checks += 1
                fields = _fields(root / f"{1000 + issue}ms" / "inputa")
                if fields != target.card15_fields:
                    failures.append(f"CARD15:{rollout_id}:{issue}")
                exact = card15_target_decimal_a(
                    target, cfg.turns_tsc, name=f"d0.independent.{rollout_id}.{issue}"
                )
                assert_exact_slew(active, exact, name=f"d0.independent.issue.{rollout_id}.{issue}")
                active = exact
                if issue > 0:
                    assert_exact_slew(
                        states[issue]["current_decimal_a_tsc"],
                        states[issue + 1]["current_decimal_a_tsc"],
                        name=f"d0.independent.observed.{rollout_id}.{issue}",
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

    replay_rows = []
    for family_id in stage["critical_replays"]:
        replay_id = f"{family_id}_replay"
        comparison = _semantic_replay(
            run_dir, family_id, replay_id,
            rows.get(family_id, []), rows.get(replay_id, []),
        )
        replay_rows.append({"family_id": family_id, **comparison})
        failures.extend(f"REPLAY:{family_id}:{reason}" for reason in comparison["failures"])

    metrics = None
    if all(len(rows.get(spec["rollout_id"], [])) == 41 for spec in specs):
        metric_rows = [
            {**spec, "states": rows[spec["rollout_id"]]}
            for spec in specs if spec["repeat_index"] == 0
        ]
        metrics = primary.scientific_metrics(metric_rows, baseline["states"][:41], stage)

    try:
        primary_result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    except Exception as exc:
        failures.append(f"PRIMARY_RESULT:{type(exc).__name__}:{exc}")
        primary_result = {}
    execution_pass = len(rows) == 14 and all(len(value) == 41 for value in rows.values())
    replay_pass = len(replay_rows) == 2 and all(row["passed"] for row in replay_rows)
    scientific_pass = metrics is not None and metrics["passed"]
    expected_passed = execution_pass and replay_pass and scientific_pass
    expected_route = stage["routes"]["pass"] if expected_passed else (
        stage["routes"]["execution_fail"] if not execution_pass
        else stage["routes"]["replay_fail"] if not replay_pass
        else stage["routes"]["scientific_fail"]
    )
    expected_counters = {
        "rollout_count": 14,
        "reset_calls": 14,
        "advance_attempts": 560,
        "gotsc_calls": 560,
        "verified_plant_advances": 560,
    }
    for key, expected in expected_counters.items():
        if primary_result.get(key) != expected:
            failures.append(f"PRIMARY_COUNTER:{key}")
    if primary_result.get("source_revision") != source_revision:
        failures.append("PRIMARY_SOURCE_REVISION")
    if primary_result.get("passed") is not expected_passed or primary_result.get("route") != expected_route:
        failures.append("PRIMARY_VERDICT")
    if metrics is None or not _close(metrics, primary_result.get("scientific_metrics")):
        failures.append("PRIMARY_SCIENTIFIC_METRICS")
    if target_map is None or not _close(target_map["action_geometry"], primary_result.get("action_geometry")):
        failures.append("PRIMARY_ACTION_GEOMETRY")
    failures = list(dict.fromkeys(failures))
    result = {
        "schema_version": f"{primary.SCHEMA}-independent",
        "kind": "independent_raw_audit",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_revision": source_revision,
        "passed": not failures,
        "route": stage["routes"]["independent_pass"] if not failures else stage["routes"]["independent_fail"],
        "failures": failures,
        "primary_scientific_passed": expected_passed,
        "primary_scientific_route": expected_route,
        "raw_rollouts": sum(len(value) == 41 for value in rows.values()),
        "raw_states": raw_states,
        "action_checks": action_checks,
        "observed_slew_checks": observed_checks,
        "critical_replays": replay_rows,
        "scientific_metrics": metrics,
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
