#!/usr/bin/env python3
"""Independent reporting-only audit of the immutable partial G1 run.

This does not repair, resume, or reinterpret G1.  It verifies that the first
novel rollout stopped immediately after the first observed-current slew above
the frozen 0.3 A contract and that no later action/state was produced.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import sys
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_1000_hybrid_radial_authority_g1 as primary  # noqa: E402
from scripts import rgeo_zgeo_1ms_1000_signed_temporal_d0_independent as d0audit  # noqa: E402
from scripts.rgeo_zgeo_1ms_nr1_independent import _fields, _state  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    assert_exact_slew,
    card15_target_decimal_a,
    decimal_single_turn_currents_a,
)


SCHEMA = f"{primary.SCHEMA}-partial-failure-forensic-v1"
PRIMARY_FAILURE_ROUTE = "ONE_MS_NR1000G1_EXECUTION_OR_HARD_SAFETY_FAIL_STOP"
PASS_ROUTE = "ONE_MS_NR1000G1_PARTIAL_RAW_FORENSIC_PASS_ACTION_ALLOCATION_MARGIN_REDESIGN"
FAIL_ROUTE = "ONE_MS_NR1000G1_PARTIAL_RAW_FORENSIC_FAIL"
EXPECTED_ROLLOUTS = ("m04_cross_p32", "matched_q0")
EXPECTED_CANDIDATE_TIMES = tuple(range(1000, 1007))
OBSERVED_CAP = Decimal("0.3")
EXPECTED_EXCESS = Decimal("0.30001")


def _time_directories(root: Path) -> tuple[int, ...]:
    if not root.is_dir():
        return ()
    return tuple(sorted(
        int(path.name[:-2])
        for path in root.iterdir()
        if path.is_dir() and path.name.endswith("ms") and path.name[:-2].isdigit()
    ))


def observed_slew_rows(states: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    # state0->state1 contains the authentic-source current/command offset and
    # remains descriptive, matching the original G1/D0 execution contract.
    for effect_index in range(2, len(states)):
        before = states[effect_index - 1]["current_decimal_a_tsc"]
        after = states[effect_index]["current_decimal_a_tsc"]
        deltas = tuple(abs(right - left) for left, right in zip(before, after))
        maximum = max(deltas)
        rows.append({
            "issue_step": effect_index - 1,
            "effect_state_index": effect_index,
            "effect_time_ms": 1000 + effect_index,
            "maximum_observed_delta_a": str(maximum),
            "maximum_component_indices": [i for i, value in enumerate(deltas) if value == maximum],
            "exceeds_frozen_cap": maximum > OBSERVED_CAP,
        })
    return rows


def _compact_match_reasons(
    raw: Sequence[dict[str, Any]], compact: Sequence[dict[str, Any]],
) -> list[str]:
    failures: list[str] = []
    if len(raw) != len(compact):
        return ["COMPACT_STATE_COUNT"]
    for index, (left, right) in enumerate(zip(raw, compact)):
        for raw_key, compact_key, tolerance in (
            ("r_geo_m", "r_geo_m", 1e-12),
            ("z_geo_m", "z_geo_m", 1e-12),
            ("r_mid_m", "r_mid_m", 1e-12),
            ("ip_a", "ip_a", 1e-9),
        ):
            if abs(float(left[raw_key]) - float(right[compact_key])) > tolerance:
                failures.append(f"COMPACT_{compact_key.upper()}:{index}")
        for raw_key, compact_key, expected_length in (
            ("current_a_tsc", "actual_current_a_tsc", 14),
            ("wire_a", "wire_current_a", 48),
        ):
            a, b = left[raw_key], right[compact_key]
            if len(a) != expected_length or len(b) != expected_length:
                failures.append(f"COMPACT_{compact_key.upper()}_LENGTH:{index}")
            elif max(abs(float(x) - float(y)) for x, y in zip(a, b)) > 1e-9:
                failures.append(f"COMPACT_{compact_key.upper()}:{index}")
    return failures


def audit(config_path: Path, run_dir: Path, source_revision: str) -> dict[str, Any]:
    stage, cfg, prior = primary.load(config_path)
    run_dir = primary.b0.inside_root(run_dir, "G1 partial run directory")
    failures: list[str] = []

    rollout_root = run_dir / "rollouts"
    actual_rollouts = tuple(sorted(path.name for path in rollout_root.iterdir() if path.is_dir()))
    if actual_rollouts != EXPECTED_ROLLOUTS:
        failures.append("ROLLOUT_DIRECTORY_SET")
    matched_times = _time_directories(rollout_root / "matched_q0")
    candidate_times = _time_directories(rollout_root / "m04_cross_p32")
    if matched_times != tuple(range(1000, 1065)):
        failures.append("MATCHED_Q0_TIME_SET")
    if candidate_times != EXPECTED_CANDIDATE_TIMES:
        failures.append("CANDIDATE_TIME_SET")
    if (rollout_root / "m04_cross_p32" / "1007ms").exists():
        failures.append("FORBIDDEN_STATE1007")

    matched_states: list[dict[str, Any]] = []
    candidate_states: list[dict[str, Any]] = []
    try:
        matched_states = [_state(rollout_root / "matched_q0" / f"{time_ms}ms", cfg)
                          for time_ms in matched_times]
        candidate_states = [_state(rollout_root / "m04_cross_p32" / f"{time_ms}ms", cfg)
                            for time_ms in candidate_times]
    except Exception as exc:
        failures.append(f"RAW_PARSE:{type(exc).__name__}:{exc}")

    try:
        primary_result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        matched_compact = json.loads((run_dir / "matched_q0.json").read_text(encoding="utf-8"))
        candidate_compact = json.loads((run_dir / "m04_cross_p32.json").read_text(encoding="utf-8"))
    except Exception as exc:
        failures.append(f"PRIMARY_COMPACT:{type(exc).__name__}:{exc}")
        primary_result = {}
        matched_compact = {}
        candidate_compact = {}

    expected_primary = {
        "source_revision": source_revision,
        "route": PRIMARY_FAILURE_ROUTE,
        "passed": False,
        "rollout_count": 2,
        "reset_calls": 2,
        "advance_attempts": 70,
        "gotsc_calls": 70,
        "verified_plant_advances": 70,
        "matched_q0_complete": True,
    }
    for key, expected in expected_primary.items():
        if primary_result.get(key) != expected:
            failures.append(f"PRIMARY_{key.upper()}")
    expected_candidate = {
        "passed": False,
        "reset_calls": 1,
        "advance_attempts": 6,
        "gotsc_calls": 6,
        "verified_plant_advances": 6,
    }
    for key, expected in expected_candidate.items():
        if candidate_compact.get(key) != expected:
            failures.append(f"CANDIDATE_{key.upper()}")
    expected_reason = (
        "EXECUTION:ContractError:m04_cross_p32.observed.5[10] "
        "exceeds the exact 0.3 A step limit"
    )
    if candidate_compact.get("reasons") != [expected_reason]:
        failures.append("CANDIDATE_STOP_REASON")
    if len(candidate_compact.get("actions", ())) != 6:
        failures.append("CANDIDATE_ACTION_COUNT")
    if matched_compact.get("passed") is not True or len(matched_compact.get("actions", ())) != 64:
        failures.append("MATCHED_Q0_COMPACT")

    failures.extend(_compact_match_reasons(matched_states, matched_compact.get("states", ())))
    for rollout_id, states in (("matched_q0", matched_states), ("m04_cross_p32", candidate_states)):
        if not states:
            continue
        source = states[0]
        for index, state in enumerate(states):
            if state["time_ms"] != 1000 + index:
                failures.append(f"TIME:{rollout_id}:{index}")
            if state["abnormal"]:
                failures.append(f"ABNORMAL:{rollout_id}:{index}")
            if not state["r_inner_m"] <= state["r_geo_m"] <= state["r_outer_m"]:
                failures.append(f"LIMITER:{rollout_id}:{index}")
            if abs(state["r_geo_m"] - source["r_geo_m"]) > 0.05:
                failures.append(f"R_ENVELOPE:{rollout_id}:{index}")
            if abs(state["z_geo_m"] - source["z_geo_m"]) > 0.05:
                failures.append(f"Z_ENVELOPE:{rollout_id}:{index}")
            if state["ip_a"] * source["ip_a"] <= 0 or abs(state["ip_a"] - source["ip_a"]) > 0.10 * abs(source["ip_a"]):
                failures.append(f"IP_ENVELOPE:{rollout_id}:{index}")
            if any(value < low or value > high for value, low, high in zip(
                state["current_a_tsc"], cfg.min_current_a_tsc, cfg.max_current_a_tsc
            )):
                failures.append(f"CURRENT_LIMIT:{rollout_id}:{index}")

    if candidate_states:
        failures.extend(d0audit._source_reasons(
            run_dir, "m04_cross_p32", candidate_states[0], prior["states"][0]
        ))
        source_fields = _fields(cfg.simulation_root / cfg.start_folder / "inputa")
        source_command = decimal_single_turn_currents_a(
            tuple(value.strip() for value in source_fields), cfg.turns_tsc,
            name="g1.failure_forensic.source_command",
        )
        target_map = primary.targets(stage, cfg, {
            "currents_a_tsc": candidate_states[0]["current_a_tsc"],
            "active_command_decimal_a_tsc": source_command,
        })
        spec = next(row for row in primary.rollout_specs(stage) if row["rollout_id"] == "m04_cross_p32")
        expected_targets = primary.sequence_for(spec, stage, target_map)
        previous = source_command
        for issue in range(6):
            target = expected_targets[issue]
            if _fields(rollout_root / "m04_cross_p32" / f"{1000 + issue}ms" / "inputa") != target.card15_fields:
                failures.append(f"CARD15:{issue}")
            exact = card15_target_decimal_a(target, cfg.turns_tsc, name=f"g1.forensic.{issue}")
            try:
                assert_exact_slew(previous, exact, name=f"g1.forensic.issued.{issue}")
            except Exception as exc:
                failures.append(f"ISSUED_SLEW:{issue}:{exc}")
            previous = exact
        # The final state contains the active issue-5 target.  No state1007
        # and no seventh action are the independent stop-before-next evidence.
        if _fields(rollout_root / "m04_cross_p32" / "1006ms" / "inputa") != expected_targets[5].card15_fields:
            failures.append("FINAL_ACTIVE_CARD15")
        failures.extend(_compact_match_reasons(candidate_states, candidate_compact.get("states", ())))

    slew_rows = observed_slew_rows(candidate_states) if candidate_states else []
    exceed_rows = [row for row in slew_rows if row["exceeds_frozen_cap"]]
    if len(exceed_rows) != 1:
        failures.append("OBSERVED_EXCEED_COUNT")
    elif (
        exceed_rows[0]["issue_step"] != 5
        or Decimal(exceed_rows[0]["maximum_observed_delta_a"]) != EXPECTED_EXCESS
        or exceed_rows[0]["maximum_component_indices"] != [10, 11]
    ):
        failures.append("OBSERVED_EXCEED_IDENTITY")
    if any(Decimal(row["maximum_observed_delta_a"]) > OBSERVED_CAP for row in slew_rows[:-1]):
        failures.append("EARLIER_OBSERVED_EXCEED")

    failures = list(dict.fromkeys(failures))
    result = {
        "schema_version": SCHEMA,
        "kind": "reporting_only_partial_raw_forensic",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_revision": source_revision,
        "passed": not failures,
        "route": PASS_ROUTE if not failures else FAIL_ROUTE,
        "failures": failures,
        "primary_route_unchanged": PRIMARY_FAILURE_ROUTE,
        "classification": "action_allocation_and_observed_readback_margin_design_failure",
        "scientific_control_result_available": False,
        "matched_q0_raw_states": len(matched_states),
        "candidate_raw_states": len(candidate_states),
        "candidate_issued_actions": 6,
        "candidate_verified_plant_advances": 6,
        "forbidden_next_state_present": (rollout_root / "m04_cross_p32" / "1007ms").exists(),
        "observed_slew_rows": slew_rows,
        "first_excess": exceed_rows[0] if len(exceed_rows) == 1 else None,
        "claim_boundary": (
            "authenticates the immutable G1 partial stop only; it does not repair G1, "
            "measure hybrid radial utility, authorize a rerun, or qualify Authority/control"
        ),
    }
    destination = run_dir / "failure_forensic.json"
    primary.b0.write_new(destination, result)
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
