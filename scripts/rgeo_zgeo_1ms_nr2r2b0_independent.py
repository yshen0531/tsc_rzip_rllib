#!/usr/bin/env python3
"""Independent raw-state audit for NR2R2B0."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_nr1_independent import _fields, _state, _maxdiff  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import assert_exact_slew  # noqa: E402
from tsc_rzip_rllib.core.runner import TSCConfig  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hold(states: list[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    source = states[0]
    r = [x["r_geo_m"] for x in states]
    z = [x["z_geo_m"] for x in states]
    ip = [x["ip_a"] for x in states]
    first, last = stage["terminal_window_start_state"], stage["terminal_window_end_state"]
    values = {
        "maximum_absolute_r_from_source_m": max(abs(x - r[0]) for x in r),
        "maximum_absolute_z_from_source_m": max(abs(x - z[0]) for x in z),
        "maximum_absolute_ip_from_source_a": max(abs(x - ip[0]) for x in ip),
        "terminal_maximum_absolute_r_step_m": max(abs(r[k + 1] - r[k]) for k in range(first, last)),
        "terminal_maximum_absolute_z_step_m": max(abs(z[k + 1] - z[k]) for k in range(first, last)),
        "terminal_absolute_r_net_drift_m": abs(r[last] - r[first]),
        "terminal_absolute_z_net_drift_m": abs(z[last] - z[first]),
    }
    values["passed"] = (
        values["maximum_absolute_r_from_source_m"] <= stage["inner_r_radius_m"]
        and values["maximum_absolute_z_from_source_m"] <= stage["inner_z_radius_m"]
        and values["maximum_absolute_ip_from_source_a"] <= stage["inner_ip_fraction"] * abs(source["ip_a"])
        and values["terminal_maximum_absolute_r_step_m"] <= stage["terminal_max_axis_step_m"]
        and values["terminal_maximum_absolute_z_step_m"] <= stage["terminal_max_axis_step_m"]
        and values["terminal_absolute_r_net_drift_m"] <= stage["terminal_max_axis_net_drift_m"]
        and values["terminal_absolute_z_net_drift_m"] <= stage["terminal_max_axis_net_drift_m"]
    )
    return values


def compare(reference: list[dict[str, Any]], candidate: list[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    maxima = {"geometry_m": 0.0, "ip_a": 0.0, "coil_a": 0.0, "wire_a": 0.0}
    exact_card15 = exact_artifacts = len(reference) == len(candidate)
    for left, right in zip(reference, candidate):
        maxima["geometry_m"] = max(maxima["geometry_m"], *(abs(left[k] - right[k]) for k in ("r_geo_m", "z_geo_m", "r_mid_m")))
        maxima["ip_a"] = max(maxima["ip_a"], abs(left["ip_a"] - right["ip_a"]))
        maxima["coil_a"] = max(maxima["coil_a"], _maxdiff(left["current_a_tsc"], right["current_a_tsc"]))
        maxima["wire_a"] = max(maxima["wire_a"], _maxdiff(left["wire_a"], right["wire_a"]))
        exact_card15 = exact_card15 and left["card15_fields"] == right["card15_fields"]
        exact_artifacts = exact_artifacts and left["artifact_sha256"] == right["artifact_sha256"]
    limits = stage["repeatability"]
    passed = len(reference) == len(candidate) and all(maxima[key] <= limits[key] for key in maxima) and exact_card15 and exact_artifacts
    return {"passed": passed, "maximum_absolute_difference": maxima,
            "exact_card15": exact_card15, "exact_artifact_sha256": exact_artifacts}


def audit(stage_path: Path, run_dir: Path, source_revision: str) -> dict[str, Any]:
    stage = json.loads(stage_path.read_text(encoding="utf-8"))
    cfg = TSCConfig.from_json(ROOT / stage["base_tsc_config"])
    required = tuple(stage["required_artifacts"])
    failures = []
    rollouts = []
    for index in range(stage["rollouts"]):
        name = f"baseline_{index:02d}"
        states = []
        try:
            for time_ms in range(1100, 1133):
                folder = run_dir / "rollouts" / name / f"{time_ms}ms"
                state = _state(folder, cfg)
                state["card15_fields"] = list(_fields(folder / "inputa"))
                state["artifact_sha256"] = {artifact: sha(folder / artifact) for artifact in required}
                states.append(state)
            source = states[0]
            for step, state in enumerate(states):
                if state["time_ms"] != 1100 + step or state["abnormal"]:
                    failures.append(f"TIME_OR_ABNORMAL:{name}:{step}")
                if not source["r_inner_m"] <= state["r_geo_m"] <= source["r_outer_m"]:
                    failures.append(f"LIMITER:{name}:{step}")
                if abs(state["r_geo_m"] - source["r_geo_m"]) > stage["outer_r_radius_m"] or abs(state["z_geo_m"] - source["z_geo_m"]) > stage["outer_z_radius_m"]:
                    failures.append(f"OUTER_GEOMETRY:{name}:{step}")
                if math.copysign(1, state["ip_a"]) != math.copysign(1, source["ip_a"]) or abs(state["ip_a"] - source["ip_a"]) > stage["outer_ip_fraction"] * abs(source["ip_a"]):
                    failures.append(f"OUTER_IP:{name}:{step}")
                if step:
                    try:
                        assert_exact_slew(states[step - 1]["current_decimal_a_tsc"], state["current_decimal_a_tsc"], name=f"independent.{name}.{step}")
                    except Exception as exc:
                        failures.append(f"SLEW:{name}:{step}:{exc}")
            if len({tuple(x["card15_fields"]) for x in states[1:]}) != 1:
                failures.append(f"CARD15_NOT_CONSTANT:{name}")
            rollouts.append(states)
        except Exception as exc:
            failures.append(f"RAW:{name}:{type(exc).__name__}:{exc}")
            break
    safety = len(rollouts) == 6 and not failures
    comparisons = [] if not safety else [compare(rollouts[0], row, stage) for row in rollouts[1:]]
    repeatable = safety and all(x["passed"] for x in comparisons)
    holds = [] if not safety else [hold(row, stage) for row in rollouts]
    q0_hold = repeatable and all(x["passed"] for x in holds)
    route = ("ONE_MS_NR2R2B0_SAFETY_OR_INTERFACE_FAIL_STOP" if not safety else
             "ONE_MS_NR2R2B0_BASELINE_REPEATABILITY_FAIL_STOP" if not repeatable else
             "ONE_MS_NR2R2B0_Q0_SHORT_HOLD_CANDIDATE_PERTURBATION_RECOVERY_DESIGN_REQUIRED" if q0_hold else
             "ONE_MS_NR2R2B0_BASELINE_REPEATABLE_Q0_NOT_HOLD_ACTIVE_RECOVERY_REQUIRED")
    primary = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    if (primary["route"], primary["plant_advances"], primary["q0_short_hold_candidate"]) != (route, 192 if safety else primary["plant_advances"], q0_hold):
        failures.append("PRIMARY_RESULT_MISMATCH")
    result = {"schema_version": stage["schema_version"] + "-independent", "source_revision": source_revision,
              "passed": safety and repeatable and not failures, "route": route if not failures else "ONE_MS_NR2R2B0_INDEPENDENT_AUDIT_FAIL_STOP",
              "failures": failures, "raw_rollouts": len(rollouts), "raw_states": sum(map(len, rollouts)),
              "repeatability": comparisons, "hold_metrics": holds, "q0_short_hold_candidate": q0_hold,
              "primary_result_sha256": sha(run_dir / "result.json")}
    destination = run_dir / "independent_audit.json"
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite {destination}")
    destination.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
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
