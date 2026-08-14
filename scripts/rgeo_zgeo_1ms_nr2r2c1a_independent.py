#!/usr/bin/env python3
"""Independent raw-directory audit for NR2R2C1a."""

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
from scripts.rgeo_zgeo_1ms_nr2r2c1a_source_replay import (  # noqa: E402
    PASS_ROUTE, SCHEMA, compare_pair, load, matrix, targets_for, write_new,
)
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    RETURN_EQUIVALENCE_A, assert_exact_slew, build_frozen_one_ms_prefixes,
    card15_target_decimal_a, decimal_single_turn_currents_a,
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory_digest(lines: list[str]) -> str:
    payload = "".join(f"{line}\n" for line in sorted(lines)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def audit(stage_path: Path, run_dir: Path, source_revision: str) -> dict[str, Any]:
    stage, cfg = load(stage_path)
    failures: list[str] = []
    rows = []
    inventory: list[str] = []
    required_artifact_bytes = 0
    frozen = None
    for spec in matrix(stage):
        states = []
        actions = []
        try:
            for state_index in range(spec["horizon_steps"] + 1):
                folder = run_dir / "rollouts" / spec["rollout_id"] / f"{1100 + state_index}ms"
                state = _state(folder, cfg)
                state["actual_current_decimal_a_tsc"] = state["current_decimal_a_tsc"]
                state["wire_current_a"] = state["wire_a"]
                state["active_command_card15_fields"] = list(_fields(folder / "inputa"))
                state["active_command_decimal_a_tsc"] = list(decimal_single_turn_currents_a(
                    state["active_command_card15_fields"], cfg.turns_tsc,
                    name=f"independent.command.{spec['rollout_id']}.{state_index}"))
                state["artifact_sha256"] = {}
                for name in tuple(stage["semantic_artifacts"]) + tuple(stage["diagnostic_artifacts"]):
                    path = folder / name
                    size = path.stat().st_size
                    digest = sha(path)
                    state["artifact_sha256"][name] = digest
                    required_artifact_bytes += size
                    relative = path.relative_to(run_dir).as_posix()
                    inventory.append(f"{relative}\t{size}\t{digest}")
                if state["abnormal"]:
                    failures.append(f"ABNORMAL:{spec['rollout_id']}:{state_index}")
                states.append(state)
            if frozen is None:
                frozen = build_frozen_one_ms_prefixes(
                    source_current_a_tsc=states[0]["current_a_tsc"], turns_tsc=cfg.turns_tsc,
                    min_current_a_tsc=cfg.min_current_a_tsc, max_current_a_tsc=cfg.max_current_a_tsc)
            targets = targets_for(spec, frozen)
            source_r = states[0]["r_geo_m"]
            source_z = states[0]["z_geo_m"]
            source_ip = states[0]["ip_a"]
            source_current = tuple(states[0]["current_decimal_a_tsc"])
            source_command = tuple(Decimal(value) for value in states[0]["active_command_decimal_a_tsc"])
            for step, target in enumerate(targets):
                expected = list(target.card15_fields)
                if states[step + 1]["active_command_card15_fields"] != expected:
                    failures.append(f"CARD15:{spec['rollout_id']}:{step}")
                exact = card15_target_decimal_a(target, cfg.turns_tsc,
                                                name=f"independent.{spec['rollout_id']}.{step}")
                assert_exact_slew(states[step]["current_decimal_a_tsc"], states[step + 1]["current_decimal_a_tsc"],
                                  name=f"independent.readback.{spec['rollout_id']}.{step}")
                actions.append({"issue_step": step, "issue_time_ms": 1100 + step,
                    "expected_card15_fields": expected, "target_current_a_tsc": list(target.current_a_tsc),
                    "maximum_issued_delta_a": assert_exact_slew(
                        card15_target_decimal_a(targets[step - 1], cfg.turns_tsc, name="previous") if step else
                        states[0]["active_command_decimal_a_tsc"], exact, name="issued"),
                    "effect_state_index": step + 1, "effect_age_steps": 1})
                if states[step + 1]["time_ms"] != 1101 + step:
                    failures.append(f"TIME:{spec['rollout_id']}:{step}")
                current = states[step + 1]
                if any(not low <= value <= high for value, low, high in zip(
                    current["current_a_tsc"], cfg.min_current_a_tsc, cfg.max_current_a_tsc
                )):
                    failures.append(f"CURRENT:{spec['rollout_id']}:{step}")
                if not current["r_inner_m"] <= current["r_geo_m"] <= current["r_outer_m"]:
                    failures.append(f"LIMITER:{spec['rollout_id']}:{step}")
                if abs(current["r_geo_m"] - source_r) > stage["outer_r_radius_m"]:
                    failures.append(f"R:{spec['rollout_id']}:{step}")
                if abs(current["z_geo_m"] - source_z) > stage["outer_z_radius_m"]:
                    failures.append(f"Z:{spec['rollout_id']}:{step}")
                if source_ip * current["ip_a"] <= 0 or abs(current["ip_a"] - source_ip) > stage["outer_ip_fraction"] * abs(source_ip):
                    failures.append(f"IP:{spec['rollout_id']}:{step}")
                if step == 0 and spec["family"] != "q0":
                    effect = tuple(x - y for x, y in zip(current["current_decimal_a_tsc"], source_current))
                    requested = tuple(x - y for x, y in zip(exact, source_command))
                    if any(x == 0 or ((x > 0) != (y > 0)) for x, y in zip(effect, requested)):
                        failures.append(f"FIRST_EFFECT_SIGN:{spec['rollout_id']}")
                if step >= 1 and spec["family"] != "q0" and max(
                    abs(x - y) for x, y in zip(current["current_decimal_a_tsc"], source_current)
                ) > RETURN_EQUIVALENCE_A:
                    failures.append(f"CENTER_RETURN:{spec['rollout_id']}:{step}")
            rows.append({**spec, "passed": True, "states": states, "actions": actions})
        except Exception as exc:
            failures.append(f"RAW:{spec['rollout_id']}:{type(exc).__name__}:{exc}")
            break
    pairs = []
    if len(rows) == 12 and not failures:
        for pair_id in dict.fromkeys(row["pair_id"] for row in rows):
            pair = [row for row in rows if row["pair_id"] == pair_id]
            pairs.append(compare_pair(pair[0], pair[1], stage))
    primary = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    expected_files = len(inventory)
    if primary.get("rollouts_completed") != 12:
        failures.append("PRIMARY_ROLLOUT_COUNT")
    if primary.get("plant_advances") != 136:
        failures.append("PRIMARY_ADVANCE_COUNT")
    if primary.get("required_artifact_files") != expected_files:
        failures.append("PRIMARY_ARTIFACT_FILE_COUNT")
    if primary.get("required_artifact_bytes") != required_artifact_bytes:
        failures.append("PRIMARY_ARTIFACT_BYTE_COUNT")
    passed = not failures and len(rows) == 12 and len(pairs) == 6 and all(x["passed"] for x in pairs)
    result = {"schema_version": SCHEMA + "-independent", "source_revision": source_revision,
              "passed": passed, "route": PASS_ROUTE if passed else "ONE_MS_NR2R2C1A_INDEPENDENT_FAIL_STOP",
              "failures": failures, "raw_rollouts": len(rows),
              "raw_states": sum(len(row["states"]) for row in rows),
              "plant_advances": sum(row["horizon_steps"] for row in rows),
              "required_artifact_files": expected_files,
              "required_artifact_bytes": required_artifact_bytes,
              "required_artifact_inventory_sha256": inventory_digest(inventory),
              "pair_comparisons": pairs, "primary_result_sha256": sha(run_dir / "result.json"),
              "primary_route": primary.get("route")}
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
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
