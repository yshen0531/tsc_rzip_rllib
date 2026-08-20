#!/usr/bin/env python3
"""Recover the completed ID2Z20 dev-hold compact after JSON finalization failed."""

from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_id2z20_authority_l0_feedback as primary  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2z9_late_root_branch_utility_support_independent as z9i  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import assert_exact_slew  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-id2z20-reporting-recovery-v1"


def inside(path: Path, label: str) -> Path:
    value = path.resolve()
    try:
        value.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(f"{label} leaves repository") from exc
    return value


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("object required")
    return value


def frozen_actions(stage: dict[str, Any], cfg: Any,
                   dev: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    spec = primary.static_spec(stage, dev, cfg, "dev_hold", None, "hold", "development", 1)
    previous = tuple(Decimal(value) for value in dev["states"][0]["active_command_decimal_a_tsc"])
    actions = []
    for issue, target in enumerate(spec["targets"]):
        arm = "root" if issue < 32 else "hold"
        action = primary.action_row(target, issue, cfg, previous, arm)
        actions.append(action)
        previous = tuple(Decimal(value) for value in
                         primary.card15_target_decimal_a(target, cfg.turns_tsc,
                                                         name=f"recovery.{issue}"))
    metadata = {key: value for key, value in spec.items() if key != "targets"}
    return metadata, actions


def recover(stage_path: Path, run_dir: Path, source_revision: str,
            recovery_revision: str, *, write: bool = True) -> dict[str, Any]:
    stage_path, run_dir = inside(stage_path, "config"), inside(run_dir, "run")
    failures: list[str] = []
    initial = load_json(run_dir / "result.json")
    if (initial.get("route") != "ONE_MS_ID2Z20_EXECUTION_OR_INTERFACE_FAIL_STOP_PRESERVE_RAW"
            or initial.get("failure") != "TypeError:Object of type Card15Target is not JSON serializable"
            or initial.get("source_revision") != source_revision
            or any(int(initial.get(key, -1)) != 0 for key in
                   ("reset_calls", "advance_attempts", "plant_advance_gotsc_calls",
                    "verified_plant_advances"))):
        failures.append("INITIAL_FAILURE_IDENTITY")
    try:
        stage, _, cfg, _, dev, _ = primary.load(stage_path)
        metadata, actions = frozen_actions(stage, cfg, dev)
    except Exception as exc:
        failures.append(f"STAGE_LOAD:{type(exc).__name__}:{exc}")
        stage, cfg, dev, metadata, actions = load_json(stage_path), None, {}, {}, []
    provisional = {**metadata, "schema_version": primary.SCHEMA,
                   "source_revision": source_revision, "passed": True, "reasons": [],
                   "reset_calls": 1, "advance_attempts": 65,
                   "plant_advance_gotsc_calls": 65, "verified_plant_advances": 65,
                   "states": [], "actions": actions, "attempted_actions": actions,
                   "retry_attempted": False, "wall_time_s": None}
    raw_rows: list[dict[str, Any]] = []
    lines: list[str] = []
    byte_count = 0
    if cfg is not None:
        expected = [{"rollout_id": "dev_hold", "actions": actions}]
        raw_rows, lines, byte_count = z9i._raw_rows(
            run_dir, cfg, expected, [provisional], failures)
    row = raw_rows[0] if len(raw_rows) == 1 else provisional
    states = row.get("states", [])
    if len(states) != 66 or [state.get("time_ms") for state in states] != list(range(1100, 1166)):
        failures.append("STATE_CLOCK_OR_COUNT")
    if len(lines) != 330:
        failures.append("ARTIFACT_COUNT")
    # The raw state directory inputa is the outgoing issue and cannot recreate
    # the preissue inputa hash.  Exact physical prefix, actions and the other
    # semantic state are checked directly instead of inventing byte equality.
    maxima = {"geometry_m": 0.0, "ip_a": 0.0, "coil_a": 0.0, "wire_a": 0.0}
    if len(states) >= 33:
        for index in range(33):
            left, right = states[index], dev["states"][index]
            maxima["geometry_m"] = max(maxima["geometry_m"],
                *(abs(float(left[key]) - float(right[key]))
                  for key in ("r_geo_m", "z_geo_m", "r_mid_m")))
            maxima["ip_a"] = max(maxima["ip_a"],
                                  abs(float(left["ip_a"]) - float(right["ip_a"])))
            if len(left.get("actual_current_decimal_a_tsc", [])) != 14:
                failures.append(f"COIL_COUNT:{index}")
            else:
                maxima["coil_a"] = max(maxima["coil_a"], max(
                    abs(float(a) - float(b)) for a, b in zip(
                        left["actual_current_decimal_a_tsc"],
                        right["actual_current_decimal_a_tsc"])))
            if len(left.get("wire_current_a", [])) != 48:
                failures.append(f"WIRE_COUNT:{index}")
            else:
                maxima["wire_a"] = max(maxima["wire_a"], max(
                    abs(float(a) - float(b)) for a, b in zip(
                        left["wire_current_a"], right["wire_current_a"])))
        if any(value != 0.0 for value in maxima.values()):
            failures.append("PHYSICAL_PREFIX_NOT_EXACT")
    if len(states) == 66 and cfg is not None:
        source = states[0]
        outer = stage["empirical_exploration"]["outer_hard_envelope"]
        caps = stage["empirical_exploration"]["post_successor_step_caps"]
        for index, state in enumerate(states):
            if (abs(float(state["r_geo_m"]) - float(source["r_geo_m"])) > outer["r_geo_m"]
                    or abs(float(state["z_geo_m"]) - float(source["z_geo_m"])) > outer["z_geo_m"]
                    or abs(float(state["ip_a"]) - float(source["ip_a"]))
                    > outer["ip_fraction"] * abs(float(source["ip_a"]))):
                failures.append(f"OUTER:{index}")
            current = [Decimal(value) for value in state["actual_current_decimal_a_tsc"]]
            if any(value < Decimal(str(low)) or value > Decimal(str(high))
                   for value, low, high in zip(current, cfg.min_current_a_tsc,
                                               cfg.max_current_a_tsc)):
                failures.append(f"CURRENT_LIMIT:{index}")
            if index:
                previous = [Decimal(value) for value in
                            states[index - 1]["actual_current_decimal_a_tsc"]]
                try:
                    states[index]["maximum_observed_delta_a"] = assert_exact_slew(
                        previous, current, name=f"recovery.observed.{index}")
                except Exception as exc:
                    failures.append(f"OBSERVED_SLEW:{index}:{type(exc).__name__}:{exc}")
                if abs(float(state["r_geo_m"]) - float(states[index - 1]["r_geo_m"])) > caps["r_geo_m"]:
                    failures.append(f"STEP_R:{index}")
                if abs(float(state["z_geo_m"]) - float(states[index - 1]["z_geo_m"])) > caps["z_geo_m"]:
                    failures.append(f"STEP_Z:{index}")
                if abs(float(state["ip_a"]) - float(states[index - 1]["ip_a"])) > caps["ip_a"]:
                    failures.append(f"STEP_IP:{index}")
    row.update({"states": states, "actions": actions, "attempted_actions": actions,
                "passed": not failures, "reasons": [], "reset_calls": 1,
                "advance_attempts": 65, "plant_advance_gotsc_calls": 65,
                "verified_plant_advances": 65, "retry_attempted": False,
                "reporting_recovered_from_raw": True,
                "reporting_recovery_revision": recovery_revision})
    digest = hashlib.sha256(
        "".join(f"{line}\n" for line in sorted(lines)).encode()).hexdigest()
    audit = {"schema_version": SCHEMA, "source_revision": source_revision,
             "reporting_recovery_revision": recovery_revision,
             "stage_config_sha256": primary.CONFIG_SHA256,
             "initial_failure_result_sha256": primary.io.sha256(run_dir / "result.json"),
             "passed": not failures, "failures": list(dict.fromkeys(failures)),
             "recovered_rollout_id": "dev_hold", "recovered_state_count": len(states),
             "recovered_action_count": len(actions),
             "recovered_physical_plant_advances": 65,
             "new_tsc_or_plant_advances": 0,
             "physical_prefix_maximum_absolute_difference": maxima,
             "preissue_inputa_hash_reconstructable": False,
             "outgoing_card15_actions_exact": not any("CARD15" in value or "FROZEN_ACTION" in value
                                                       for value in failures),
             "required_artifact_files": len(lines), "required_artifact_bytes": byte_count,
             "required_artifact_inventory_sha256": digest,
             "resume_authorized_only_if_passed_and_dev_hold_not_repeated": True,
             "claim_boundary": "Reporting-only raw recovery; no new plant or scientific verdict."}
    audit["dry_run_no_files_written"] = not write
    if write:
        if audit["passed"]:
            primary.io.write_new(run_dir / "dev_hold.json", row)
        primary.io.write_new(run_dir / "reporting_recovery_audit.json", audit)
    return audit


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-config", type=Path, default=primary.CONFIG)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--recovery-revision", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    value = recover(args.stage_config, args.run_dir, args.source_revision,
                    args.recovery_revision, write=not args.dry_run)
    print(json.dumps(value, indent=2, sort_keys=True, allow_nan=False))
    return 0 if value["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
