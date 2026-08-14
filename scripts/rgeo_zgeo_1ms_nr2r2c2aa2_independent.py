#!/usr/bin/env python3
"""Structurally separate final-raw audit for NR2R2C2aA2."""

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
from scripts.rgeo_zgeo_1ms_nr2r2c2a_search import sha256, write_new  # noqa: E402
from scripts.rgeo_zgeo_1ms_nr2r2c2aa1_independent import (  # noqa: E402
    independent_authority_metrics, metric_difference,
)
from scripts.rgeo_zgeo_1ms_nr2r2c2aa2_directions import (  # noqa: E402
    FAIL_ROUTE, PASS_ROUTE, SCHEMA, candidate_targets, load,
)
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    assert_exact_slew, build_frozen_one_ms_prefixes, card15_target_decimal_a,
    decimal_single_turn_currents_a,
)


def inventory_digest(lines: list[str]) -> str:
    payload = "".join(f"{line}\n" for line in sorted(lines)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def audit(stage_path: Path, run_dir: Path, source_revision: str) -> dict[str, Any]:
    stage, cfg = load(stage_path)
    primary = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    q0_record = json.loads((ROOT / stage["q0_comparator"]["path"]).read_text(encoding="utf-8"))
    failures: list[str] = []
    for key in ("selection_audit", "q0_comparator"):
        if sha256(ROOT / stage[key]["path"]) != stage[key]["sha256"]:
            failures.append(f"{key.upper()}_HASH")
    rows: list[dict[str, Any]] = []
    inventory: list[str] = []
    artifact_bytes = 0
    source_fields = tuple(_fields(cfg.simulation_root / cfg.start_folder / "inputa"))
    source_command = decimal_single_turn_currents_a(
        tuple(value.strip() for value in source_fields), cfg.turns_tsc,
        name="c2aa2.independent.source_command")
    for spec in stage["candidates"][:primary["rollouts_completed"]]:
        rollout_id = spec["candidate_id"]
        compact = json.loads((run_dir / f"{rollout_id}.json").read_text(encoding="utf-8"))
        states: list[dict[str, Any]] = []
        actions: list[dict[str, Any]] = []
        try:
            for state_index in range(len(compact["states"])):
                folder = run_dir / "rollouts" / rollout_id / f"{1100 + state_index}ms"
                state = _state(folder, cfg)
                state["outgoing_command_card15_fields"] = list(_fields(folder / "inputa"))
                state["actual_current_decimal_a_tsc"] = state["current_decimal_a_tsc"]
                state["wire_current_a"] = tuple(state["wire_a"])
                state["artifact_sha256"] = {}
                if state["abnormal"]:
                    failures.append(f"ABNORMAL:{rollout_id}:{state_index}")
                for name in tuple(stage["semantic_artifacts"]) + tuple(stage["diagnostic_artifacts"]):
                    path = folder / name
                    size = path.stat().st_size
                    digest = sha256(path)
                    state["artifact_sha256"][name] = digest
                    artifact_bytes += size
                    inventory.append(f"{path.relative_to(run_dir).as_posix()}\t{size}\t{digest}")
                recorded = compact["states"][state_index]
                if any(state[key] != recorded[key]
                       for key in ("time_ms", "r_geo_m", "z_geo_m", "r_mid_m", "ip_a")):
                    failures.append(f"PRIMARY_STATE:{rollout_id}:{state_index}")
                if tuple(state["current_decimal_a_tsc"]) != tuple(
                    Decimal(str(value)) for value in recorded["actual_current_decimal_a_tsc"]
                ):
                    failures.append(f"PRIMARY_COIL:{rollout_id}:{state_index}")
                if tuple(state["wire_current_a"]) != tuple(recorded["wire_current_a"]):
                    failures.append(f"PRIMARY_WIRE:{rollout_id}:{state_index}")
                if any(not low <= value <= high for value, low, high in zip(
                    state["current_a_tsc"], cfg.min_current_a_tsc, cfg.max_current_a_tsc
                )):
                    failures.append(f"CURRENT:{rollout_id}:{state_index}")
                if not state["r_inner_m"] <= state["r_geo_m"] <= state["r_outer_m"]:
                    failures.append(f"LIMITER:{rollout_id}:{state_index}")
                states.append(state)

            frozen = build_frozen_one_ms_prefixes(
                source_current_a_tsc=states[0]["current_a_tsc"], turns_tsc=cfg.turns_tsc,
                min_current_a_tsc=cfg.min_current_a_tsc, max_current_a_tsc=cfg.max_current_a_tsc)
            _, _, targets = candidate_targets(stage, spec, frozen.q0, cfg)
            previous_command = source_command
            bound = stage["support_evidence"]["prospective_successor_bound"]
            source_state = states[0]
            for step in range(len(states) - 1):
                expected = targets[step]
                if states[step]["outgoing_command_card15_fields"] != list(expected.card15_fields):
                    failures.append(f"CARD15:{rollout_id}:{step}")
                exact = card15_target_decimal_a(
                    expected, cfg.turns_tsc, name=f"c2aa2.independent.{rollout_id}.{step}")
                issued = assert_exact_slew(
                    previous_command, exact, name=f"c2aa2.independent.issue.{rollout_id}.{step}")
                assert_exact_slew(
                    states[step]["current_decimal_a_tsc"], states[step + 1]["current_decimal_a_tsc"],
                    name=f"c2aa2.independent.readback.{rollout_id}.{step}")
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
                    failures.append(f"SUPPORT_BOUND_R:{rollout_id}:{step}")
                if dz > bound["z_geo_m"]:
                    failures.append(f"SUPPORT_BOUND_Z:{rollout_id}:{step}")
                if dip > bound["ip_a"]:
                    failures.append(f"SUPPORT_BOUND_IP:{rollout_id}:{step}")
                source_dr = abs(states[step]["r_geo_m"] - source_state["r_geo_m"])
                source_dz = abs(states[step]["z_geo_m"] - source_state["z_geo_m"])
                source_dip = abs(states[step]["ip_a"] - source_state["ip_a"])
                if (source_dr > stage["inner_r_radius_m"]
                        or stage["outer_r_radius_m"] - source_dr < bound["r_geo_m"]):
                    failures.append(f"PREISSUE_R_MARGIN:{rollout_id}:{step}")
                if (source_dz > stage["inner_z_radius_m"]
                        or stage["outer_z_radius_m"] - source_dz < bound["z_geo_m"]):
                    failures.append(f"PREISSUE_Z_MARGIN:{rollout_id}:{step}")
                inner_ip = stage["inner_ip_fraction"] * abs(source_state["ip_a"])
                outer_ip = stage["outer_ip_fraction"] * abs(source_state["ip_a"])
                if (source_state["ip_a"] * states[step]["ip_a"] <= 0
                        or source_dip > inner_ip or outer_ip - source_dip < bound["ip_a"]):
                    failures.append(f"PREISSUE_IP_MARGIN:{rollout_id}:{step}")
                successor_dr = abs(states[step + 1]["r_geo_m"] - source_state["r_geo_m"])
                successor_dz = abs(states[step + 1]["z_geo_m"] - source_state["z_geo_m"])
                successor_dip = abs(states[step + 1]["ip_a"] - source_state["ip_a"])
                if successor_dr > stage["outer_r_radius_m"]:
                    failures.append(f"OUTER_R:{rollout_id}:{step + 1}")
                if successor_dz > stage["outer_z_radius_m"]:
                    failures.append(f"OUTER_Z:{rollout_id}:{step + 1}")
                if (source_state["ip_a"] * states[step + 1]["ip_a"] <= 0
                        or successor_dip > outer_ip):
                    failures.append(f"OUTER_IP:{rollout_id}:{step + 1}")
            if actions != compact["actions"]:
                failures.append(f"PRIMARY_ACTION:{rollout_id}")
            metrics = (independent_authority_metrics(states, q0_record["states"], stage)
                       if len(states) == 33 else None)
            if metrics is not None and (
                metric_difference(metrics, compact["authority_metrics"]) > 1e-15
                or metrics["passed"] != compact["authority_metrics"]["passed"]
            ):
                failures.append(f"PRIMARY_METRICS:{rollout_id}")
            rows.append({"candidate_id": rollout_id, "passed": compact["passed"],
                         "states": states, "actions": actions, "authority_metrics": metrics,
                         "reasons": compact["reasons"]})
        except Exception as exc:
            failures.append(f"RAW:{rollout_id}:{type(exc).__name__}:{exc}")
            break

    execution = (len(rows) == len(stage["candidates"])
                 and all(row["passed"] and len(row["states"]) == 33
                         and len(row["actions"]) == 32 for row in rows))
    support_failure = any(reason.startswith("SUPPORT_BOUND_")
                          for row in rows for reason in row["reasons"])
    passing = [row["candidate_id"] for row in rows
               if row["passed"] and row["authority_metrics"] is not None
               and row["authority_metrics"]["passed"]]
    scientific_pass = execution and bool(passing)
    expected_route = ("ONE_MS_NR2R2C2AA2_SUPPORT_BOUND_FAIL_STOP" if support_failure else
                      "ONE_MS_NR2R2C2AA2_EXECUTION_FAIL_STOP" if not execution else
                      PASS_ROUTE if scientific_pass else FAIL_ROUTE)
    if expected_route != primary["route"]:
        failures.append("PRIMARY_ROUTE")
    if primary["passed"] != scientific_pass or primary["passing_candidates"] != passing:
        failures.append("PRIMARY_SCIENTIFIC_VERDICT")
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
    result = {"schema_version": SCHEMA + "-independent-v1",
              "source_revision": source_revision, "audit_passed": audit_passed,
              "route": ("ONE_MS_NR2R2C2AA2_INDEPENDENT_AUDIT_PASS" if audit_passed
                        else "ONE_MS_NR2R2C2AA2_INDEPENDENT_AUDIT_FAIL_STOP"),
              "failures": failures, "primary_route": primary["route"],
              "primary_scientific_passed": primary["passed"],
              "passing_candidates": passing, "raw_rollouts": len(rows),
              "raw_states": sum(len(row["states"]) for row in rows),
              "plant_advances": sum(len(row["actions"]) for row in rows),
              "required_artifact_files": len(inventory),
              "required_artifact_bytes": artifact_bytes,
              "required_artifact_inventory_sha256": digest,
              "authority_metrics": [{"candidate_id": row["candidate_id"],
                                      **row["authority_metrics"]}
                                     for row in rows if row["authority_metrics"]],
              "maximum_primary_metric_difference": max((
                  metric_difference(row["authority_metrics"], primary_metric)
                  for row, primary_metric in zip(rows, primary.get("authority_metrics", []))
                  if row["authority_metrics"] is not None
              ), default=None),
              "primary_result_sha256": sha256(run_dir / "result.json")}
    write_new(run_dir / "independent_audit.json", result)
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
