#!/usr/bin/env python3
"""Independent raw-directory audit for the fixed-1000 B0 baseline."""

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

from scripts import rgeo_zgeo_1ms_1000_baseline_b0 as primary  # noqa: E402
from scripts.rgeo_zgeo_1ms_nr1_independent import _fields, _state  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    assert_exact_slew,
    build_frozen_one_ms_prefixes,
    card15_target_decimal_a,
    decimal_single_turn_currents_a,
)
from tsc_rzip_rllib.core.runner import TSCConfig  # noqa: E402


def _maxdiff(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return max(abs(a - b) for a, b in zip(left, right)) if len(left) == len(right) else math.inf


def _metrics(states: list[dict[str, Any]]) -> dict[str, Any]:
    source = states[0]
    increments = [
        ((b["r_geo_m"] - a["r_geo_m"]) * 1000.0,
         (b["z_geo_m"] - a["z_geo_m"]) * 1000.0,
         b["ip_a"] - a["ip_a"])
        for a, b in zip(states, states[1:])
    ]
    terminal = states[-1]
    tail = states[-9]
    return {
        "terminal_state_index": 64,
        "terminal_time_ms": terminal["time_ms"],
        "terminal_source_delta": {
            "r_mm": (terminal["r_geo_m"] - source["r_geo_m"]) * 1000.0,
            "z_mm": (terminal["z_geo_m"] - source["z_geo_m"]) * 1000.0,
            "ip_a": terminal["ip_a"] - source["ip_a"],
        },
        "last_8ms_net_delta": {
            "r_mm": (terminal["r_geo_m"] - tail["r_geo_m"]) * 1000.0,
            "z_mm": (terminal["z_geo_m"] - tail["z_geo_m"]) * 1000.0,
            "ip_a": terminal["ip_a"] - tail["ip_a"],
        },
        "maximum_absolute_one_step": {
            "r_mm": max(abs(row[0]) for row in increments),
            "z_mm": max(abs(row[1]) for row in increments),
            "ip_a": max(abs(row[2]) for row in increments),
            "rz_speed_m_s": max(math.hypot(row[0], row[1]) for row in increments),
        },
        "terminal_8state_maximum_rz_speed_m_s": max(
            math.hypot(row[0], row[1]) for row in increments[-8:]
        ),
    }


def _close(left: Any, right: Any, tolerance: float = 1e-12) -> bool:
    if isinstance(left, dict) and isinstance(right, dict):
        return set(left) == set(right) and all(_close(left[key], right[key], tolerance) for key in left)
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return abs(float(left) - float(right)) <= tolerance
    return left == right


def audit(config_path: Path, run_dir: Path, source_revision: str) -> dict[str, Any]:
    stage, cfg = primary.load(config_path)
    run_dir = primary.inside_root(run_dir, "run directory")
    failures: list[str] = []
    rows: dict[str, list[dict[str, Any]]] = {}
    action_checks = observed_checks = 0
    expected_times = list(range(1000, 1065))
    source_fields = _fields(cfg.simulation_root / cfg.start_folder / "inputa")
    source_command = decimal_single_turn_currents_a(
        tuple(value.strip() for value in source_fields), cfg.turns_tsc,
        name="b0.independent.source_command",
    )
    source_state = None
    for rollout_id in ("baseline_primary", "baseline_replay"):
        root = run_dir / "rollouts" / rollout_id
        actual_time_dirs = sorted(
            int(path.name[:-2]) for path in root.iterdir()
            if path.is_dir() and path.name.endswith("ms") and path.name[:-2].isdigit()
        ) if root.is_dir() else []
        if actual_time_dirs != expected_times:
            failures.append(f"TIME_DIRECTORY_SET:{rollout_id}")
        try:
            states = [_state(root / f"{time_ms}ms", cfg) for time_ms in expected_times]
            rows[rollout_id] = states
            source_state = states[0] if source_state is None else source_state
            frozen = build_frozen_one_ms_prefixes(
                source_current_a_tsc=states[0]["current_a_tsc"],
                source_command_a_tsc=source_command,
                turns_tsc=cfg.turns_tsc,
                min_current_a_tsc=cfg.min_current_a_tsc,
                max_current_a_tsc=cfg.max_current_a_tsc,
                maximum_command_delta_a=Decimal("0.299"),
            )
            q0 = frozen.q0
            q0_decimal = card15_target_decimal_a(q0, cfg.turns_tsc, name="b0.independent.q0")
            active = source_command
            for issue in range(64):
                action_checks += 1
                if _fields(root / f"{1000 + issue}ms" / "inputa") != q0.card15_fields:
                    failures.append(f"CARD15:{rollout_id}:{issue}")
                assert_exact_slew(active, q0_decimal, name=f"b0.independent.issue.{rollout_id}.{issue}")
                active = q0_decimal
                if issue > 0:
                    assert_exact_slew(
                        states[issue]["current_decimal_a_tsc"],
                        states[issue + 1]["current_decimal_a_tsc"],
                        name=f"b0.independent.observed.{rollout_id}.{issue}",
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
    maxima = {"geometry_m": 0.0, "ip_a": 0.0, "coil_a": 0.0, "wire_a": 0.0}
    left, right = rows.get("baseline_primary", []), rows.get("baseline_replay", [])
    if len(left) != 65 or len(right) != 65:
        failures.append("REPLAY_STATE_COUNT")
    for index, (a, b) in enumerate(zip(left, right)):
        maxima["geometry_m"] = max(
            maxima["geometry_m"], *(abs(a[key] - b[key]) for key in ("r_geo_m", "z_geo_m", "r_mid_m"))
        )
        maxima["ip_a"] = max(maxima["ip_a"], abs(a["ip_a"] - b["ip_a"]))
        maxima["coil_a"] = max(maxima["coil_a"], _maxdiff(a["current_a_tsc"], b["current_a_tsc"]))
        maxima["wire_a"] = max(maxima["wire_a"], _maxdiff(a["wire_a"], b["wire_a"]))
        for name in primary.SEMANTIC_ARTIFACTS:
            if primary.sha256(run_dir / "rollouts" / "baseline_primary" / f"{1000+index}ms" / name) != primary.sha256(
                run_dir / "rollouts" / "baseline_replay" / f"{1000+index}ms" / name
            ):
                failures.append(f"SEMANTIC_ARTIFACT:{name}:{index}")
    if maxima["geometry_m"] > 1e-12:
        failures.append("REPLAY_GEOMETRY")
    if maxima["ip_a"] > 1e-9:
        failures.append("REPLAY_IP")
    if maxima["coil_a"] > 1e-9:
        failures.append("REPLAY_COIL")
    if maxima["wire_a"] > 1e-9:
        failures.append("REPLAY_WIRE")
    primary_result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    recomputed_metrics = _metrics(left) if len(left) == 65 else None
    if primary_result.get("source_revision") != source_revision:
        failures.append("PRIMARY_SOURCE_REVISION")
    if primary_result.get("route") != stage["routes"]["pass"] or primary_result.get("passed") is not True:
        failures.append("PRIMARY_VERDICT")
    if primary_result.get("verified_plant_advances") != 128:
        failures.append("PRIMARY_ADVANCE_COUNT")
    if recomputed_metrics is None or not _close(recomputed_metrics, primary_result.get("drift_metrics")):
        failures.append("PRIMARY_DRIFT_METRICS")
    failures = list(dict.fromkeys(failures))
    result = {
        "schema_version": f"{primary.SCHEMA}-independent",
        "kind": "independent_raw_audit",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_revision": source_revision,
        "passed": not failures,
        "route": stage["routes"]["independent_pass"] if not failures else stage["routes"]["independent_fail"],
        "failures": failures,
        "raw_rollouts": sum(len(value) == 65 for value in rows.values()),
        "raw_states": sum(len(value) for value in rows.values()),
        "action_checks": action_checks,
        "observed_slew_checks": observed_checks,
        "maximum_absolute_difference": maxima,
        "drift_metrics": recomputed_metrics,
    }
    destination = run_dir / "independent_audit.json"
    primary.write_new(destination, result)
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
