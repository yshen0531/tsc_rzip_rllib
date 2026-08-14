#!/usr/bin/env python3
"""Recompute the frozen zero-TSC A4 late-state causal-support condition."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "rgeo-zgeo-1ms-nr2r2c2aa4-late-state-support-audit-v1"
A4_SCHEMA = "rgeo-zgeo-1ms-nr2r2c2aa4-p03-level2-dwell-hold-v1"
INPUT_FAIL_ROUTE = "ONE_MS_NR2R2C2AA4_SUPPORT_AUDIT_INPUT_INTEGRITY_FAIL_NO_TSC"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_hashed_json(row: dict[str, Any]) -> dict[str, Any]:
    path = (ROOT / row["path"]).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError(f"input leaves repository: {row['path']}")
    if not path.is_file() or sha256(path) != row["sha256"]:
        raise ValueError(f"input hash mismatch: {row['path']}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_new(path: Path, payload: dict[str, Any]) -> None:
    path = path.resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError("output path must remain inside the repository")
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def expected_a4_fields(stage: dict[str, Any], q0_fields: Sequence[str]) -> list[list[str]]:
    by_level = {
        "q0": list(q0_fields),
        "level1": list(stage["level1_card15_fields"]),
        "level2": list(stage["level2_card15_fields"]),
    }
    rows: list[list[str] | None] = [None] * int(stage["horizon_steps"])
    for segment in stage["schedule"]:
        for issue in range(int(segment["first_step"]), int(segment["last_step"]) + 1):
            if rows[issue] is not None:
                raise ValueError("A4 schedule overlaps")
            rows[issue] = by_level[segment["level"]]
    if any(row is None for row in rows):
        raise ValueError("A4 schedule does not cover the horizon")
    return [list(row) for row in rows if row is not None]


def expected_a4_levels(stage: dict[str, Any]) -> list[str]:
    rows: list[str | None] = [None] * int(stage["horizon_steps"])
    for segment in stage["schedule"]:
        for issue in range(int(segment["first_step"]), int(segment["last_step"]) + 1):
            if rows[issue] is not None:
                raise ValueError("A4 schedule overlaps")
            rows[issue] = str(segment["level"])
    if any(row is None for row in rows):
        raise ValueError("A4 schedule does not cover the horizon")
    return [str(row) for row in rows]


def checked_replay_prefix_equal(
    left: dict[str, Any], right: dict[str, Any], last_state: int
) -> bool:
    state_keys = (
        "time_ms",
        "r_geo_m",
        "z_geo_m",
        "r_mid_m",
        "ip_a",
        "actual_current_decimal_a_tsc",
        "wire_current_a",
    )
    if len(left["states"]) <= last_state or len(right["states"]) <= last_state:
        return False
    for index in range(last_state + 1):
        if any(left["states"][index][key] != right["states"][index][key] for key in state_keys):
            return False
    return True


def build_support_table(
    expected: Sequence[Sequence[str]],
    levels: Sequence[str],
    replay0: dict[str, Any],
    replay1: dict[str, Any],
    *,
    effect_state_offset: int,
) -> list[dict[str, Any]]:
    if len(expected) != len(levels):
        raise ValueError("A4 action/level stream length mismatch")
    table: list[dict[str, Any]] = []
    prefix_matches = True
    level2_first_issue = list(levels).index("level2")
    for issue, fields in enumerate(expected):
        effect = issue + effect_state_offset
        prefix_before_issue_matches = prefix_matches
        preissue_state_present = issue < len(replay0["states"]) and issue < len(replay1["states"])
        replay_pair_preissue_equal = (
            preissue_state_present and checked_replay_prefix_equal(replay0, replay1, issue)
        )
        same_prefix_preissue_state = bool(
            prefix_before_issue_matches and replay_pair_preissue_equal
        )
        action_present = issue < len(replay0["actions"]) and issue < len(replay1["actions"])
        if action_present:
            action_match = (
                replay0["actions"][issue]["expected_card15_fields"] == list(fields)
                and replay1["actions"][issue]["expected_card15_fields"] == list(fields)
            )
        else:
            action_match = False
        prefix_matches = prefix_matches and action_match
        successor_present = effect < len(replay0["states"]) and effect < len(replay1["states"])
        replay_pair_successor_equal = (
            successor_present and checked_replay_prefix_equal(replay0, replay1, effect)
        )
        same_prefix_successor = bool(
            prefix_matches and successor_present and replay_pair_successor_equal
        )
        direct = same_prefix_successor
        supported = direct
        dwell_age = issue - level2_first_issue + 1 if issue >= level2_first_issue else None
        table.append(
            {
                "issue_step": issue,
                "effect_state_index": effect,
                "command_level": levels[issue],
                "level2_dwell_effect_age": dwell_age,
                "current_state_observation_contract_exact": True,
                "same_prefix_preissue_state": same_prefix_preissue_state,
                "same_card15_target": action_match,
                "complete_same_issue_prefix": prefix_matches,
                "recorded_replay_pair_successor_equal": replay_pair_successor_equal,
                "same_prefix_successor": same_prefix_successor,
                "direct_same_prefix_support": direct,
                "qualified_state_history_tube_support": False,
                "supported_before_advance": supported,
                "support_kind": "direct_same_prefix_successor" if direct else "unsupported",
                "reason": (
                    "DIRECT_SAME_PREFIX_SUCCESSOR" if direct
                    else "MISSING_SAME_PREFIX_SUCCESSOR_OR_QUALIFIED_TUBE"
                ),
            }
        )
    return table


def maximum_successor(records: Sequence[dict[str, Any]]) -> dict[str, Any]:
    maximum = {"r_geo_m": 0.0, "z_geo_m": 0.0, "ip_a": 0.0}
    provenance: dict[str, dict[str, Any] | None] = {key: None for key in maximum}
    for record in records:
        for index, (before, after) in enumerate(zip(record["states"], record["states"][1:])):
            for key in maximum:
                value = abs(float(after[key]) - float(before[key]))
                if not math.isfinite(value):
                    raise ValueError("nonfinite compact successor")
                if value > maximum[key]:
                    maximum[key] = value
                    provenance[key] = {"role": record["_audit_role"], "issue_step": index}
    return {"maximum_absolute": maximum, "provenance": provenance}


def state_margin(stage: dict[str, Any], replay: dict[str, Any], state_index: int) -> dict[str, Any]:
    source = replay["states"][0]
    state = replay["states"][state_index]
    dr = abs(float(state["r_geo_m"]) - float(source["r_geo_m"]))
    dz = abs(float(state["z_geo_m"]) - float(source["z_geo_m"]))
    dip = abs(float(state["ip_a"]) - float(source["ip_a"]))
    ip0 = abs(float(source["ip_a"]))
    return {
        "state_index": state_index,
        "source_offset": {"r_geo_m": dr, "z_geo_m": dz, "ip_a": dip},
        "remaining_to_inner": {
            "r_geo_m": float(stage["inner_r_radius_m"]) - dr,
            "z_geo_m": float(stage["inner_z_radius_m"]) - dz,
            "ip_a": float(stage["inner_ip_fraction"]) * ip0 - dip,
        },
        "remaining_to_outer": {
            "r_geo_m": float(stage["outer_r_radius_m"]) - dr,
            "z_geo_m": float(stage["outer_z_radius_m"]) - dz,
            "ip_a": float(stage["outer_ip_fraction"]) * ip0 - dip,
        },
    }


def audit(config_path: Path, source_revision: str) -> dict[str, Any]:
    config_path = config_path.resolve()
    if not config_path.is_relative_to(ROOT.resolve()):
        raise ValueError("audit config must remain inside the repository")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != SCHEMA:
        raise ValueError("unexpected A4 support-audit schema")
    a4 = load_hashed_json(config["a4_config"])
    if a4.get("schema_version") != A4_SCHEMA:
        raise ValueError("unexpected A4 campaign schema")
    if (
        a4.get("takeover_time_ms") != 1100
        or a4.get("control_period_ms") != 1
        or a4.get("horizon_steps") != 32
        or a4.get("rollouts") != 2
        or a4.get("maximum_plant_advances") != 64
    ):
        raise ValueError("A4 timing or plant budget mismatch")
    if (
        config.get("required_issue_first") != 0
        or config.get("required_issue_last") != 31
        or config.get("effect_state_offset") != 1
    ):
        raise ValueError("support audit issue/effect contract mismatch")
    observation = config.get("decision_observation_contract", {})
    if observation != {
        "available_before_issue": True,
        "r_geo_z_geo_ip_are_exact_noiseless_observables": True,
        "same_step_paired_boundary_required": True,
        "invalid_or_missing_boundary_fails_closed": True,
        "complete_causal_observation_and_own_action_history_through_current_step_is_available": True,
        "future_successor_is_observed_before_issue": False,
    }:
        raise ValueError("decision observation contract mismatch")
    rule = config.get("support_rule", {})
    if (
        rule.get("empirical_stop_threshold_is_qualified_tube") is not False
        or rule.get("current_state_margin_alone_is_causal_successor_support") is not False
        or rule.get("wrong_action_or_history_substitution_allowed") is not False
    ):
        raise ValueError("support rule would permit an unsafe shortcut")
    design_path = (ROOT / config["a4_design"]["path"]).resolve()
    if not design_path.is_relative_to(ROOT.resolve()):
        raise ValueError("A4 design path leaves repository")
    if not design_path.is_file() or sha256(design_path) != config["a4_design"]["sha256"]:
        raise ValueError("A4 design hash mismatch")
    primary = load_hashed_json(config["a3_primary_result"])
    independent = load_hashed_json(config["a3_independent_audit"])
    if primary.get("route") != config["a3_primary_result"]["required_route"]:
        raise ValueError("A3 primary route mismatch")
    if independent.get("route") != config["a3_independent_audit"]["required_route"]:
        raise ValueError("A3 independent route mismatch")
    if not primary.get("execution_passed") or not primary.get("repeatability_passed"):
        raise ValueError("A3 execution/repeatability premise failed")
    if independent.get("audit_passed") is not True:
        raise ValueError("A3 independent audit premise failed")
    if independent.get("primary_result_sha256") != config["a3_primary_result"]["sha256"]:
        raise ValueError("A3 independent/primary binding mismatch")
    if primary.get("plant_advances") != 64 or independent.get("plant_advances") != 64:
        raise ValueError("A3 plant budget evidence mismatch")
    if primary.get("required_artifact_files") != 330:
        raise ValueError("A3 required artifact count mismatch")
    for key in (
        "required_artifact_files",
        "required_artifact_bytes",
        "required_artifact_inventory_sha256",
    ):
        if independent.get(key) != primary.get(key):
            raise ValueError(f"A3 independent inventory binding mismatch: {key}")
    if a4["support_evidence"].get("holdout_records_read") != 0:
        raise ValueError("A4 support premise may not read holdout records")

    records: dict[str, dict[str, Any]] = {}
    for row in config["compact_trajectories"]:
        record = load_hashed_json(row)
        if record.get("passed") is not True or record.get("plant_advances") != 32:
            raise ValueError(f"compact trajectory incomplete: {row['role']}")
        if len(record.get("states", [])) != 33 or len(record.get("actions", [])) != 32:
            raise ValueError(f"compact trajectory shape mismatch: {row['role']}")
        for state_index, state in enumerate(record["states"]):
            if state.get("time_ms") != 1100 + state_index:
                raise ValueError(f"compact state clock mismatch: {row['role']}:{state_index}")
        for issue, action in enumerate(record["actions"]):
            if (
                action.get("issue_step") != issue
                or action.get("issue_time_ms") != 1100 + issue
                or action.get("effect_state_index") != issue + 1
                or action.get("effect_age_steps") != 1
            ):
                raise ValueError(f"compact issue/effect contract mismatch: {row['role']}:{issue}")
        record["_audit_role"] = row["role"]
        records[row["role"]] = record

    replay0 = records["a3_level2_replay_0"]
    replay1 = records["a3_level2_replay_1"]
    q0_fields = records["q0_h32"]["actions"][0]["expected_card15_fields"]
    expected = expected_a4_fields(a4, q0_fields)
    levels = expected_a4_levels(a4)
    if len(expected) != int(a4["horizon_steps"]):
        raise ValueError("A4 expected action stream length mismatch")

    table = build_support_table(
        expected,
        levels,
        replay0,
        replay1,
        effect_state_offset=int(config["effect_state_offset"]),
    )
    required = [
        row for row in table
        if int(config["required_issue_first"]) <= row["issue_step"] <= int(config["required_issue_last"])
    ]
    unsupported = [row for row in required if not row["supported_before_advance"]]
    support_passed = not unsupported
    observed = maximum_successor(list(records.values()))
    a3_only = maximum_successor([replay0, replay1])
    threshold = a4["support_evidence"]["prospective_successor_bound"]
    threshold_multiple = {
        key: float(threshold[key]) / float(a3_only["maximum_absolute"][key])
        for key in ("r_geo_m", "z_geo_m", "ip_a")
    }
    route = config["routes"]["pass"] if support_passed else config["routes"]["blocked"]
    return {
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "audit_completed": True,
        "input_integrity_passed": True,
        "support_passed": support_passed,
        "passed": support_passed,
        "route": route,
        "required_issue_steps": [int(config["required_issue_first"]), int(config["required_issue_last"])],
        "required_transitions": len(required),
        "supported_transitions": sum(row["supported_before_advance"] for row in required),
        "directly_supported_issue_steps": [
            row["issue_step"] for row in required if row["direct_same_prefix_support"]
        ],
        "unsupported_issue_steps": [row["issue_step"] for row in unsupported],
        "first_unsupported": None if not unsupported else unsupported[0],
        "support_table": table,
        "support_rule": rule,
        "decision_observation_contract": config["decision_observation_contract"],
        "qualified_state_history_tube_certificate_present": False,
        "state16_margin_is_descriptive_not_support": state_margin(a4, replay0, 16),
        "a3_maximum_observed_successor": a3_only,
        "all_compact_maximum_observed_successor": observed,
        "a3_threshold_multiple": threshold_multiple,
        "empirical_threshold": threshold,
        "claim_boundary": (
            "zero_tsc_causal_support_audit_only; margin_and_empirical_threshold_do_not_qualify_"
            "unseen_level2_action_age_15_through_30"
        ),
        "stop_semantics_audit": "not_run_because_causal_support_failed_before_a4_implementation",
        "input_identity": {
            "audit_config_path": str(config_path.relative_to(ROOT.resolve())).replace("\\", "/"),
            "audit_config_sha256": sha256(config_path),
            "hashed_inputs": {
                row["path"]: row["sha256"]
                for row in (
                    config["a4_config"],
                    config["a4_design"],
                    config["a3_primary_result"],
                    config["a3_independent_audit"],
                    *config["compact_trajectories"],
                )
            },
        },
        "counters": {
            "server_accesses": 0,
            "server_raw_reads": 0,
            "holdout_records_read": 0,
            "new_tsc_or_plant_advances": 0,
            "model_fits_or_training_runs": 0,
            "controller_or_optimizer_executions": 0,
            "compact_trajectory_records_read": len(records),
            "raw_records_read": 0,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs/rgeo_zgeo_1ms_nr2r2c2aa4_late_state_support_audit.json",
    )
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit(args.config.resolve(), args.source_revision)
        write_new(args.output.resolve(), result)
    except Exception as exc:
        failure = {
            "schema_version": SCHEMA,
            "audit_completed": False,
            "input_integrity_passed": False,
            "passed": False,
            "route": INPUT_FAIL_ROUTE,
            "error": f"{type(exc).__name__}:{exc}",
            "new_tsc_or_plant_advances": 0,
        }
        print(json.dumps(failure, indent=2, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
