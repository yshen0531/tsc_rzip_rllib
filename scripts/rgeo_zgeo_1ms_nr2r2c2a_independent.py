#!/usr/bin/env python3
"""Structurally separate raw audit for the NR2R2C2a search."""

from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_nr1_independent import _fields, _state  # noqa: E402
from scripts.rgeo_zgeo_1ms_nr2r2c2a_search import (  # noqa: E402
    NO_CANDIDATE_ROUTE, PASS_ROUTE, SCHEMA, action_stream, candidate_target,
    load, selection_key, sha256, write_new,
)
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    assert_exact_slew, build_frozen_one_ms_prefixes, card15_target_decimal_a,
    decimal_single_turn_currents_a,
)


def independent_metrics(states: list[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    source = states[0]
    first, last = stage["terminal_window_start_state"], stage["terminal_window_end_state"]
    terminal = states[first:last + 1]
    all_r = [state["r_geo_m"] - source["r_geo_m"] for state in states]
    all_z = [state["z_geo_m"] - source["z_geo_m"] for state in states]
    all_ip = [state["ip_a"] - source["ip_a"] for state in states]
    r = [state["r_geo_m"] for state in terminal]
    z = [state["z_geo_m"] for state in terminal]
    values = {
        "maximum_absolute_r_from_source_m": max(abs(value) for value in all_r),
        "maximum_absolute_z_from_source_m": max(abs(value) for value in all_z),
        "maximum_absolute_ip_from_source_a": max(abs(value) for value in all_ip),
        "terminal_maximum_source_axis_displacement_m": max(
            *(abs(value - source["r_geo_m"]) for value in r),
            *(abs(value - source["z_geo_m"]) for value in z),
        ),
        "terminal_maximum_absolute_axis_step_m": max(
            *(abs(r[index + 1] - r[index]) for index in range(len(r) - 1)),
            *(abs(z[index + 1] - z[index]) for index in range(len(z) - 1)),
        ),
        "terminal_maximum_absolute_axis_net_drift_m": max(abs(r[-1] - r[0]), abs(z[-1] - z[0])),
        "endpoint_r_from_source_m": all_r[-1],
        "endpoint_z_from_source_m": all_z[-1],
        "endpoint_ip_from_source_a": all_ip[-1],
    }
    values["eligible"] = (
        values["maximum_absolute_r_from_source_m"] <= stage["inner_r_radius_m"]
        and values["maximum_absolute_z_from_source_m"] <= stage["inner_z_radius_m"]
        and values["maximum_absolute_ip_from_source_a"] <= stage["inner_ip_fraction"] * abs(source["ip_a"])
        and values["terminal_maximum_source_axis_displacement_m"] <= stage["terminal_max_source_axis_displacement_m"]
        and values["terminal_maximum_absolute_axis_step_m"] <= stage["terminal_max_axis_step_m"]
        and values["terminal_maximum_absolute_axis_net_drift_m"] <= stage["terminal_max_axis_net_drift_m"]
    )
    return values


def metric_difference(left: dict[str, Any], right: dict[str, Any]) -> float:
    keys = tuple(key for key, value in left.items() if isinstance(value, float))
    return max((abs(left[key] - right[key]) for key in keys), default=0.0)


def inventory_digest(lines: list[str]) -> str:
    payload = "".join(f"{line}\n" for line in sorted(lines)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def audit(stage_path: Path, run_dir: Path, source_revision: str) -> dict[str, Any]:
    stage, cfg = load(stage_path)
    primary = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    failures: list[str] = []
    rows: list[dict[str, Any]] = []
    inventory: list[str] = []
    artifact_bytes = 0
    source_fields = tuple(_fields(cfg.simulation_root / cfg.start_folder / "inputa"))
    source_command = decimal_single_turn_currents_a(
        tuple(value.strip() for value in source_fields), cfg.turns_tsc, name="c2a.independent.source_command"
    )
    for spec in stage["candidates"][:primary["rollouts_completed"]]:
        compact = json.loads((run_dir / f"{spec['candidate_id']}.json").read_text(encoding="utf-8"))
        states: list[dict[str, Any]] = []
        actions: list[dict[str, Any]] = []
        try:
            for state_index in range(len(compact["states"])):
                folder = run_dir / "rollouts" / spec["candidate_id"] / f"{1100 + state_index}ms"
                state = _state(folder, cfg)
                state["outgoing_command_card15_fields"] = list(_fields(folder / "inputa"))
                state["actual_current_decimal_a_tsc"] = state["current_decimal_a_tsc"]
                state["wire_current_a"] = state["wire_a"]
                if state["abnormal"]:
                    failures.append(f"ABNORMAL:{spec['candidate_id']}:{state_index}")
                for name in tuple(stage["semantic_artifacts"]) + tuple(stage["diagnostic_artifacts"]):
                    path = folder / name
                    size = path.stat().st_size
                    digest = sha256(path)
                    artifact_bytes += size
                    inventory.append(f"{path.relative_to(run_dir).as_posix()}\t{size}\t{digest}")
                recorded = compact["states"][state_index]
                if any(state[key] != recorded[key] for key in ("time_ms", "r_geo_m", "z_geo_m", "r_mid_m", "ip_a")):
                    failures.append(f"PRIMARY_STATE:{spec['candidate_id']}:{state_index}")
                if tuple(state["current_decimal_a_tsc"]) != tuple(
                    Decimal(str(value)) for value in recorded["actual_current_decimal_a_tsc"]
                ):
                    failures.append(f"PRIMARY_COIL:{spec['candidate_id']}:{state_index}")
                if tuple(state["wire_current_a"]) != tuple(recorded["wire_current_a"]):
                    failures.append(f"PRIMARY_WIRE:{spec['candidate_id']}:{state_index}")
                if any(not low <= value <= high for value, low, high in zip(
                    state["current_a_tsc"], cfg.min_current_a_tsc, cfg.max_current_a_tsc
                )):
                    failures.append(f"CURRENT:{spec['candidate_id']}:{state_index}")
                if not state["r_inner_m"] <= state["r_geo_m"] <= state["r_outer_m"]:
                    failures.append(f"LIMITER:{spec['candidate_id']}:{state_index}")
                states.append(state)
            source_state = states[0]
            for state_index, state in enumerate(states):
                if (state_index < len(states) - 1 and
                        abs(state["r_geo_m"] - source_state["r_geo_m"]) > stage["inner_r_radius_m"]):
                    failures.append(f"INNER_R:{spec['candidate_id']}:{state_index}")
                if (state_index < len(states) - 1 and
                        abs(state["z_geo_m"] - source_state["z_geo_m"]) > stage["inner_z_radius_m"]):
                    failures.append(f"INNER_Z:{spec['candidate_id']}:{state_index}")
                if (state_index < len(states) - 1 and (source_state["ip_a"] * state["ip_a"] <= 0 or
                        abs(state["ip_a"] - source_state["ip_a"]) >
                        stage["inner_ip_fraction"] * abs(source_state["ip_a"]))):
                    failures.append(f"INNER_IP:{spec['candidate_id']}:{state_index}")
            frozen = build_frozen_one_ms_prefixes(
                source_current_a_tsc=states[0]["current_a_tsc"], turns_tsc=cfg.turns_tsc,
                min_current_a_tsc=cfg.min_current_a_tsc, max_current_a_tsc=cfg.max_current_a_tsc)
            target = candidate_target(spec, cfg)
            targets = action_stream(stage, frozen.q0, target)
            previous_command = source_command
            bound = stage["support_evidence"]["prospective_successor_bound"]
            for step in range(len(states) - 1):
                expected = targets[step]
                if states[step]["outgoing_command_card15_fields"] != list(expected.card15_fields):
                    failures.append(f"CARD15:{spec['candidate_id']}:{step}")
                exact = card15_target_decimal_a(expected, cfg.turns_tsc,
                                                name=f"c2a.independent.{spec['candidate_id']}.{step}")
                issued = assert_exact_slew(previous_command, exact,
                                           name=f"c2a.independent.issue.{spec['candidate_id']}.{step}")
                assert_exact_slew(states[step]["current_decimal_a_tsc"], states[step + 1]["current_decimal_a_tsc"],
                                  name=f"c2a.independent.readback.{spec['candidate_id']}.{step}")
                actions.append({"issue_step": step, "issue_time_ms": 1100 + step,
                                "expected_card15_fields": list(expected.card15_fields),
                                "target_current_a_tsc": list(expected.current_a_tsc),
                                "maximum_issued_delta_a": issued,
                                "effect_state_index": step + 1, "effect_age_steps": 1})
                previous_command = exact
                dr = abs(states[step + 1]["r_geo_m"] - states[step]["r_geo_m"])
                dz = abs(states[step + 1]["z_geo_m"] - states[step]["z_geo_m"])
                dip = abs(states[step + 1]["ip_a"] - states[step]["ip_a"])
                if dr > bound["r_geo_m"]:
                    failures.append(f"SUPPORT_BOUND_R:{spec['candidate_id']}:{step}")
                if dz > bound["z_geo_m"]:
                    failures.append(f"SUPPORT_BOUND_Z:{spec['candidate_id']}:{step}")
                if dip > bound["ip_a"]:
                    failures.append(f"SUPPORT_BOUND_IP:{spec['candidate_id']}:{step}")
            if actions != compact["actions"]:
                failures.append(f"PRIMARY_ACTION:{spec['candidate_id']}")
            metrics = independent_metrics(states, stage) if len(states) == 33 else None
            if metrics is not None and (metric_difference(metrics, compact["hold_metrics"]) > 1e-15
                                        or metrics["eligible"] != compact["hold_metrics"]["eligible"]):
                failures.append(f"PRIMARY_METRICS:{spec['candidate_id']}")
            rows.append({"candidate_id": spec["candidate_id"], "states": states, "actions": actions,
                         "passed": compact["passed"], "hold_metrics": metrics})
        except Exception as exc:
            failures.append(f"RAW:{spec['candidate_id']}:{type(exc).__name__}:{exc}")
            break
    execution = len(rows) == 2 and all(row["passed"] and len(row["states"]) == 33 for row in rows)
    eligible = [row for row in rows if row["hold_metrics"] is not None and row["hold_metrics"]["eligible"]]
    selected = min(eligible, key=selection_key) if execution and eligible else None
    expected_route = (PASS_ROUTE if selected is not None else NO_CANDIDATE_ROUTE) if execution else primary["route"]
    if expected_route != primary["route"]:
        failures.append("PRIMARY_ROUTE")
    primary_selected = None if primary["selected_candidate"] is None else primary["selected_candidate"]["candidate_id"]
    if primary_selected != (None if selected is None else selected["candidate_id"]):
        failures.append("PRIMARY_SELECTION")
    if primary["plant_advances"] != sum(len(row["actions"]) for row in rows):
        failures.append("PRIMARY_ADVANCE_COUNT")
    if primary["required_artifact_files"] != len(inventory):
        failures.append("PRIMARY_ARTIFACT_FILE_COUNT")
    if primary["required_artifact_bytes"] != artifact_bytes:
        failures.append("PRIMARY_ARTIFACT_BYTE_COUNT")
    digest = inventory_digest(inventory)
    if primary["required_artifact_inventory_sha256"] != digest:
        failures.append("PRIMARY_ARTIFACT_DIGEST")
    audit_passed = not failures
    result = {"schema_version": SCHEMA + "-independent-v2", "source_revision": source_revision,
              "audit_passed": audit_passed,
              "route": "ONE_MS_NR2R2C2A_SEARCH_INDEPENDENT_AUDIT_PASS" if audit_passed else
                       "ONE_MS_NR2R2C2A_SEARCH_INDEPENDENT_AUDIT_FAIL_STOP",
              "failures": failures, "primary_route": primary["route"],
              "primary_scientific_passed": primary["passed"],
              "raw_rollouts": len(rows), "raw_states": sum(len(row["states"]) for row in rows),
              "plant_advances": sum(len(row["actions"]) for row in rows),
              "required_artifact_files": len(inventory), "required_artifact_bytes": artifact_bytes,
              "required_artifact_inventory_sha256": digest,
              "candidate_metrics": [{"candidate_id": row["candidate_id"],
                                     "hold_metrics": row["hold_metrics"]} for row in rows],
              "primary_result_sha256": sha256(run_dir / "result.json")}
    write_new(run_dir / "independent_audit_v2.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    result = audit(args.stage_config.resolve(), args.run_dir.resolve(), args.source_revision)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
