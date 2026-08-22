#!/usr/bin/env python3
"""Independent raw audit for fixed-1000 joint allocator Authority G2R1."""

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

from scripts import rgeo_zgeo_1ms_1000_joint_allocator_authority_g2r1 as primary  # noqa: E402
from scripts import rgeo_zgeo_1ms_1000_radial_nominal_n0_independent as n0audit  # noqa: E402
from scripts import rgeo_zgeo_1ms_1000_signed_temporal_d0_independent as d0audit  # noqa: E402
from scripts.rgeo_zgeo_1ms_nr1_independent import _fields, _state  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    assert_exact_slew,
    decimal_single_turn_currents_a,
)


def _compact_state_reasons(raw: list[dict[str, Any]], compact: list[dict[str, Any]], name: str) -> list[str]:
    failures: list[str] = []
    if len(raw) != 65 or len(compact) != 65:
        return [f"COMPACT_STATE_COUNT:{name}"]
    for index, (left, right) in enumerate(zip(raw, compact)):
        for key, tolerance in (("r_geo_m", 1e-12), ("z_geo_m", 1e-12), ("r_mid_m", 1e-12), ("ip_a", 1e-9)):
            if abs(float(left[key]) - float(right[key])) > tolerance:
                failures.append(f"COMPACT_{key.upper()}:{name}:{index}")
        for raw_key, compact_key, length in (
            ("current_a_tsc", "actual_current_a_tsc", 14),
            ("wire_a", "wire_current_a", 48),
        ):
            a, b = left[raw_key], right[compact_key]
            if len(a) != length or len(b) != length:
                failures.append(f"COMPACT_{compact_key.upper()}_LENGTH:{name}:{index}")
            elif max(abs(float(x) - float(y)) for x, y in zip(a, b)) > 1e-9:
                failures.append(f"COMPACT_{compact_key.upper()}:{name}:{index}")
    return failures


def audit(config_path: Path, run_dir: Path, source_revision: str) -> dict[str, Any]:
    stage, cfg, evidence = primary.load(config_path)
    run_dir = primary.b0.inside_root(run_dir, "G2R1 run directory")
    failures: list[str] = []
    specs = primary.rollout_specs(stage)
    expected_times = tuple(range(1000, 1065))
    source_command = decimal_single_turn_currents_a(
        tuple(value.strip() for value in _fields(cfg.simulation_root / cfg.start_folder / "inputa")),
        cfg.turns_tsc,
        name="g2r1.independent.source_command",
    )
    rows: dict[str, list[dict[str, Any]]] = {}
    compact_rows: dict[str, dict[str, Any]] = {}
    reconstructed: list[dict[str, Any]] = []
    target_map = None
    action_checks = observed_checks = raw_states = 0

    actual_rollouts = tuple(sorted(path.name for path in (run_dir / "rollouts").iterdir() if path.is_dir()))
    if actual_rollouts != tuple(sorted(stage["rollout_ids"])):
        failures.append("ROLLOUT_DIRECTORY_SET")

    for spec in specs:
        rollout_id = spec["rollout_id"]
        root = run_dir / "rollouts" / rollout_id
        actual_times = tuple(sorted(
            int(path.name[:-2]) for path in root.iterdir()
            if path.is_dir() and path.name.endswith("ms") and path.name[:-2].isdigit()
        )) if root.is_dir() else ()
        if actual_times != expected_times:
            failures.append(f"TIME_DIRECTORY_SET:{rollout_id}")
        try:
            states = [_state(root / f"{time_ms}ms", cfg) for time_ms in expected_times]
            rows[rollout_id] = states
            raw_states += len(states)
            failures.extend(f"SOURCE:{rollout_id}:{reason}" for reason in d0audit._source_reasons(
                run_dir, rollout_id, states[0], evidence["b0_primary"]["states"][0]
            ))
            if target_map is None:
                target_map = primary.targets(stage, cfg, {
                    "currents_a_tsc": states[0]["current_a_tsc"],
                    "active_command_decimal_a_tsc": source_command,
                })
            compact = json.loads((run_dir / f"{rollout_id}.json").read_text(encoding="utf-8"))
            compact_rows[rollout_id] = compact
            failures.extend(_compact_state_reasons(states, compact.get("states", []), rollout_id))

            radial_level = vertical_level = 0
            radial_phase = "initial_minus"
            radial_switch_issue = None
            vertical_signs: dict[int, int] = {}
            decisions = []
            action_rows = []
            for issue in range(stage["horizon_steps"]):
                inward_mm = (states[0]["r_geo_m"] - states[issue]["r_geo_m"]) * 1000.0
                if spec["kind"] == "matched_q0":
                    next_radial, next_vertical = 0, 0
                else:
                    policy = stage["radial_policy"]
                    switched = False
                    if issue < policy["initial_minus_depth"]:
                        next_radial = radial_level - 1
                        radial_phase = "initial_minus"
                    else:
                        next_radial = radial_level
                        if radial_phase in ("initial_minus", "await_switch"):
                            radial_phase = "await_switch"
                            if (issue >= policy["earliest_switch_issue"] and
                                    (inward_mm >= policy["switch_inward_source_displacement_mm"]
                                     or issue >= policy["latest_switch_issue"])):
                                radial_phase = "brake"
                                switched = True
                        if radial_phase == "brake" and next_radial < policy["final_plus_level"]:
                            next_radial += policy["brake_increment_levels_per_issue"]
                            if next_radial == policy["final_plus_level"]:
                                radial_phase = "hold_final"
                        if switched:
                            radial_switch_issue = issue
                    next_vertical = 0
                    if spec["path"] is not None:
                        for ordinal, decision_issue in enumerate(stage["vertical_policy"]["decision_issues"]):
                            if issue == decision_issue:
                                target_z = stage["vertical_policy"]["waypoints_z_source_mm"][spec["path"]][ordinal]
                                current_z = (states[issue]["z_geo_m"] - states[0]["z_geo_m"]) * 1000.0
                                sign = 1 if target_z - current_z >= 0 else -1
                                vertical_signs[decision_issue] = sign
                                decisions.append({
                                    "ordinal": ordinal,
                                    "issue_step": issue,
                                    "endpoint_state": stage["vertical_policy"]["endpoint_states"][ordinal],
                                    "target_z_source_mm": target_z,
                                    "current_z_source_mm": current_z,
                                    "selected_vertical_sign": sign,
                                })
                        for decision_issue, sign in vertical_signs.items():
                            offset = issue - decision_issue
                            profile = stage["vertical_policy"]["macro_absolute_levels"]
                            if 0 <= offset < len(profile):
                                next_vertical = sign * profile[offset]
                target = target_map["cells"][(next_radial, next_vertical)]
                exact = target_map["exact_cells"][(next_radial, next_vertical)]
                action_checks += 1
                if _fields(root / f"{1000 + issue}ms" / "inputa") != target.card15_fields:
                    failures.append(f"CARD15:{rollout_id}:{issue}")
                maximum = assert_exact_slew(
                    source_command if issue == 0 else target_map["exact_cells"][(radial_level, vertical_level)],
                    exact,
                    name=f"g2r1.independent.issued.{rollout_id}.{issue}",
                )
                if maximum > stage["lattice"]["maximum_exact_issued_slew_a"]:
                    failures.append(f"ISSUED_RESERVE:{rollout_id}:{issue}")
                if issue > 0:
                    try:
                        assert_exact_slew(
                            states[issue]["current_decimal_a_tsc"],
                            states[issue + 1]["current_decimal_a_tsc"],
                            name=f"g2r1.independent.observed.{rollout_id}.{issue}",
                        )
                        observed_checks += 1
                    except Exception as exc:
                        failures.append(f"OBSERVED_SLEW:{rollout_id}:{issue}:{exc}")
                action_rows.append({
                    "issue_step": issue,
                    "issue_time_ms": 1000 + issue,
                    "effect_state_index": issue + 1,
                    "effect_time_ms": 1001 + issue,
                    "radial_level": next_radial,
                    "vertical_level": next_vertical,
                    "radial_phase": radial_phase,
                    "inward_source_displacement_mm": inward_mm,
                    "maximum_issued_delta_a": maximum,
                    "expected_card15_fields": list(target.card15_fields),
                })
                radial_level, vertical_level = next_radial, next_vertical

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
                if state["ip_a"] * states[0]["ip_a"] <= 0 or abs(state["ip_a"] - states[0]["ip_a"]) > 0.10 * abs(states[0]["ip_a"]):
                    failures.append(f"IP_ENVELOPE:{rollout_id}:{index}")
                if any(value < low or value > high for value, low, high in zip(
                    state["current_a_tsc"], cfg.min_current_a_tsc, cfg.max_current_a_tsc
                )):
                    failures.append(f"CURRENT_LIMIT:{rollout_id}:{index}")
            final_levels = [radial_level, vertical_level]
            if spec["kind"] != "matched_q0" and final_levels != stage["scientific_gates"]["final_active_levels"]:
                failures.append(f"FINAL_LEVELS:{rollout_id}")
            if _fields(root / "1064ms" / "inputa") != target_map["cells"][(radial_level, vertical_level)].card15_fields:
                failures.append(f"FINAL_ACTIVE_CARD15:{rollout_id}")
            for key, expected in {
                "passed": True,
                "reset_calls": 1,
                "advance_attempts": 64,
                "gotsc_calls": 64,
                "verified_plant_advances": 64,
                "radial_switch_issue": radial_switch_issue,
                "final_levels": final_levels,
                "decisions": decisions,
                "actions": action_rows,
            }.items():
                if compact.get(key) != expected:
                    failures.append(f"COMPACT_{key.upper()}:{rollout_id}")
            reconstructed.append({**spec, "states": states, "decisions": decisions})
        except Exception as exc:
            failures.append(f"RAW:{rollout_id}:{type(exc).__name__}:{exc}")
            rows.setdefault(rollout_id, [])

    replay = n0audit.semantic_replay(
        run_dir, "path_pos_neg", "path_pos_neg_replay",
        rows.get("path_pos_neg", []), rows.get("path_pos_neg_replay", []),
    )
    failures.extend(f"REPLAY:{reason}" for reason in replay["failures"])
    complete = all(len(rows.get(spec["rollout_id"], [])) == 65 for spec in specs)
    metrics = primary.scientific_metrics(reconstructed, stage) if complete else None
    try:
        result0 = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    except Exception as exc:
        failures.append(f"PRIMARY_RESULT:{type(exc).__name__}:{exc}")
        result0 = {}
    expected_science = metrics is not None and metrics["passed"]
    expected_pass = complete and replay["passed"] and expected_science
    expected_route = stage["routes"]["pass"] if expected_pass else (
        stage["routes"]["execution_fail"] if not complete
        else stage["routes"]["replay_fail"] if not replay["passed"]
        else stage["routes"]["scientific_fail"]
    )
    for key, expected in {
        "source_revision": source_revision,
        "passed": expected_pass,
        "route": expected_route,
        "rollout_count": 5,
        "reset_calls": 5,
        "advance_attempts": 320,
        "gotsc_calls": 320,
        "verified_plant_advances": 320,
        "matched_q0_complete": True,
    }.items():
        if result0.get(key) != expected:
            failures.append(f"PRIMARY_{key.upper()}")
    if target_map is None or not d0audit._close(target_map["action_geometry"], result0.get("action_geometry")):
        failures.append("PRIMARY_ACTION_GEOMETRY")
    if metrics is None or not d0audit._close(metrics, result0.get("scientific_metrics")):
        failures.append("PRIMARY_SCIENTIFIC_METRICS")
    if result0.get("critical_replay", {}).get("passed") is not True:
        failures.append("PRIMARY_REPLAY")

    failures = list(dict.fromkeys(failures))
    result = {
        "schema_version": f"{primary.SCHEMA}-independent",
        "kind": "independent_raw_audit",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_revision": source_revision,
        "passed": not failures,
        "route": stage["routes"]["independent_pass"] if not failures else stage["routes"]["independent_fail"],
        "failures": failures,
        "primary_scientific_passed": expected_pass,
        "primary_scientific_route": expected_route,
        "raw_rollouts": sum(len(value) == 65 for value in rows.values()),
        "raw_states": raw_states,
        "action_checks": action_checks,
        "observed_slew_checks": observed_checks,
        "critical_replay": replay,
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
