#!/usr/bin/env python3
"""Run the prospectively frozen NR2R2B0 all-q0 source baseline."""

from __future__ import annotations

import argparse
from decimal import Decimal
import json
from pathlib import Path
import sys
import time
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_nr1_qualification import _record, _source  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    OneMsNR1SafetyEnvelope, assert_exact_slew, card15_target_decimal_a,
    quantize_target, validate_one_ms_config,
)
from tsc_rzip_rllib.control.rgeo_zgeo_contract import RGeoZGeoSignal  # noqa: E402
from tsc_rzip_rllib.core.runner import TSCConfig, TSCStepRunner  # noqa: E402


def write_new(path: Path, value: Any) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def load(stage_path: Path) -> tuple[dict[str, Any], TSCConfig]:
    stage = json.loads(stage_path.read_text(encoding="utf-8"))
    if stage["schema_version"] != "rgeo-zgeo-1ms-nr2r2b0-source-q0-baseline-v1":
        raise ValueError("unexpected NR2R2B0 schema")
    if stage["rollouts"] * stage["steps_per_rollout"] != stage["maximum_plant_advances"]:
        raise ValueError("NR2R2B0 plant budget mismatch")
    base_path = ROOT / stage["base_tsc_config"]
    cfg = TSCConfig.from_json(base_path)
    validate_one_ms_config(start_folder=cfg.start_folder, dt_ms=cfg.dt_ms,
                           slew_a_per_ms=cfg.current_slew_a_per_ms)
    return stage, cfg


def hold_metrics(states: list[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    source = states[0]
    dr = np.asarray([x["r_geo_m"] - source["r_geo_m"] for x in states])
    dz = np.asarray([x["z_geo_m"] - source["z_geo_m"] for x in states])
    dip = np.asarray([x["ip_a"] - source["ip_a"] for x in states])
    first, last = stage["terminal_window_start_state"], stage["terminal_window_end_state"]
    terminal_r = np.asarray([x["r_geo_m"] for x in states[first:last + 1]])
    terminal_z = np.asarray([x["z_geo_m"] for x in states[first:last + 1]])
    values = {
        "maximum_absolute_r_from_source_m": float(np.max(np.abs(dr))),
        "maximum_absolute_z_from_source_m": float(np.max(np.abs(dz))),
        "maximum_absolute_ip_from_source_a": float(np.max(np.abs(dip))),
        "terminal_maximum_absolute_r_step_m": float(np.max(np.abs(np.diff(terminal_r)))),
        "terminal_maximum_absolute_z_step_m": float(np.max(np.abs(np.diff(terminal_z)))),
        "terminal_absolute_r_net_drift_m": float(abs(terminal_r[-1] - terminal_r[0])),
        "terminal_absolute_z_net_drift_m": float(abs(terminal_z[-1] - terminal_z[0])),
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
    exact_card15 = True
    exact_artifacts = True
    if len(reference) != len(candidate):
        return {"passed": False, "reason": "STATE_COUNT", "maximum_absolute_difference": maxima,
                "exact_card15": False, "exact_artifact_sha256": False}
    for left, right in zip(reference, candidate):
        maxima["geometry_m"] = max(maxima["geometry_m"], *(abs(left[k] - right[k]) for k in ("r_geo_m", "z_geo_m", "r_mid_m")))
        maxima["ip_a"] = max(maxima["ip_a"], abs(left["ip_a"] - right["ip_a"]))
        maxima["coil_a"] = max(maxima["coil_a"], max(abs(float(a) - float(b)) for a, b in zip(left["actual_current_decimal_a_tsc"], right["actual_current_decimal_a_tsc"])))
        maxima["wire_a"] = max(maxima["wire_a"], max(abs(a - b) for a, b in zip(left["wire_current_a"], right["wire_current_a"])))
        exact_card15 = exact_card15 and left["active_command_card15_fields"] == right["active_command_card15_fields"]
        exact_artifacts = exact_artifacts and left["artifact_sha256"] == right["artifact_sha256"]
    limits = stage["repeatability"]
    passed = (maxima["geometry_m"] <= limits["geometry_m"] and maxima["ip_a"] <= limits["ip_a"]
              and maxima["coil_a"] <= limits["coil_a"] and maxima["wire_a"] <= limits["wire_a"]
              and exact_card15 and exact_artifacts)
    return {"passed": passed, "maximum_absolute_difference": maxima,
            "exact_card15": exact_card15, "exact_artifact_sha256": exact_artifacts}


def offline(stage_path: Path, source_revision: str) -> dict[str, Any]:
    failures = []
    try:
        stage, cfg = load(stage_path)
        source = _source(cfg)
        signal = RGeoZGeoSignal.from_tsc_state(source)
        envelope = OneMsNR1SafetyEnvelope.from_signal(signal)
        failures.extend(envelope.state_reasons(signal, source["currents_a_tsc"], cfg.min_current_a_tsc, cfg.max_current_a_tsc))
        q0 = quantize_target(source["currents_a_tsc"], cfg.turns_tsc)
        q0_decimal = card15_target_decimal_a(q0, cfg.turns_tsc, name="nr2r2b0.q0")
        source_command = source["active_command_decimal_a_tsc"]
        first_step = assert_exact_slew(source_command, q0_decimal, name="nr2r2b0.source_to_q0")
        repeated_step = assert_exact_slew(q0_decimal, q0_decimal, name="nr2r2b0.q0_to_q0")
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
        stage = None; signal = None; q0 = None; first_step = None; repeated_step = None
    return {"schema_version": "rgeo-zgeo-1ms-nr2r2b0-source-q0-baseline-v1",
            "source_revision": source_revision, "passed": not failures,
            "route": "ONE_MS_NR2R2B0_OFFLINE_PASS" if not failures else "ONE_MS_NR2R2B0_OFFLINE_FAIL_NO_TSC",
            "failures": failures, "stage": stage, "source_signal": None if signal is None else signal.to_dict(),
            "q0": None if q0 is None else {"card15_fields": list(q0.card15_fields), "current_a_tsc": list(q0.current_a_tsc)},
            "maximum_source_to_q0_step_a": first_step, "maximum_q0_to_q0_step_a": repeated_step,
            "new_tsc_or_plant_advances": 0}


def one_rollout(cfg: TSCConfig, stage: dict[str, Any], q0: Any, name: str) -> dict[str, Any]:
    runner = TSCStepRunner(cfg, worker_id=f"nr2r2b0_{name}", keep_workspace=False)
    reasons: list[str] = []
    states: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    started = time.perf_counter()
    try:
        state = runner.reset(episode_name=name)
        states.append(_record(cfg, state))
        envelope = OneMsNR1SafetyEnvelope.from_signal(RGeoZGeoSignal.from_tsc_state(state))
        q0_decimal = card15_target_decimal_a(q0, cfg.turns_tsc, name=f"{name}.q0")
        for step in range(stage["steps_per_rollout"]):
            reasons.extend(envelope.state_reasons(RGeoZGeoSignal.from_tsc_state(state), state["currents_a_tsc"], cfg.min_current_a_tsc, cfg.max_current_a_tsc))
            try:
                maximum = assert_exact_slew(states[-1]["active_command_decimal_a_tsc"], q0_decimal, name=f"{name}.issue.{step}")
            except Exception as exc:
                reasons.append(f"ISSUED_SLEW:{exc}")
                break
            if reasons:
                break
            actions.append({"issue_step": step, "issue_time_ms": 1100 + step,
                            "card15_fields": list(q0.card15_fields), "target_current_a_tsc": list(q0.current_a_tsc),
                            "maximum_issued_delta_a": maximum})
            state = runner.step_current_a(np.asarray(q0.current_a_tsc, dtype=float))
            if int(state.get("returncode", 0)) != 0:
                reasons.append(f"TSC_RETURNCODE:{state.get('returncode')}")
            if state.get("abnormal", False):
                reasons.append(f"TSC_ABNORMAL:{state.get('done_reason', '')}")
            record = _record(cfg, state)
            states.append(record)
            if record["time_ms"] != 1101 + step:
                reasons.append(f"TIME:{step}")
            if tuple(record["active_command_card15_fields"]) != q0.card15_fields:
                reasons.append(f"CARD15:{step}")
            try:
                record["maximum_observed_delta_a"] = assert_exact_slew(states[-2]["actual_current_decimal_a_tsc"], record["actual_current_decimal_a_tsc"], name=f"{name}.observed.{step}")
            except Exception as exc:
                reasons.append(f"OBSERVED_SLEW:{exc}")
            reasons.extend(envelope.state_reasons(RGeoZGeoSignal.from_tsc_state(state), state["currents_a_tsc"], cfg.min_current_a_tsc, cfg.max_current_a_tsc))
            if reasons:
                break
    except Exception as exc:
        reasons.append(f"EXECUTION:{type(exc).__name__}:{exc}")
    finally:
        runner.cleanup_runtime_workspace()
    reasons = list(dict.fromkeys(reasons))
    complete = not reasons and len(actions) == 32 and len(states) == 33
    return {"rollout_id": name, "passed": complete, "reasons": reasons,
            "plant_advances": len(actions), "states": states, "actions": actions,
            "hold_metrics": hold_metrics(states, stage) if complete else None,
            "wall_time_s": time.perf_counter() - started}


def run(stage_path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    gate = offline(stage_path, source_revision)
    if not gate["passed"]:
        raise RuntimeError("offline gate failed; TSC forbidden")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    output.mkdir(parents=True)
    write_new(output / "offline_preflight.json", gate)
    stage, cfg = load(stage_path)
    cfg.run_root = output / "rollouts"
    q0 = quantize_target(_source(cfg)["currents_a_tsc"], cfg.turns_tsc)
    rows = []
    for index in range(stage["rollouts"]):
        row = one_rollout(cfg, stage, q0, f"baseline_{index:02d}")
        rows.append(row)
        write_new(output / f"baseline_{index:02d}.json", row)
        if not row["passed"]:
            break
    safety = len(rows) == stage["rollouts"] and all(row["passed"] for row in rows)
    comparisons = [] if not safety else [compare(rows[0]["states"], row["states"], stage) for row in rows[1:]]
    repeatable = safety and len(comparisons) == 5 and all(x["passed"] for x in comparisons)
    q0_hold = repeatable and all(row["hold_metrics"]["passed"] for row in rows)
    route = ("ONE_MS_NR2R2B0_SAFETY_OR_INTERFACE_FAIL_STOP" if not safety else
             "ONE_MS_NR2R2B0_BASELINE_REPEATABILITY_FAIL_STOP" if not repeatable else
             "ONE_MS_NR2R2B0_Q0_SHORT_HOLD_CANDIDATE_PERTURBATION_RECOVERY_DESIGN_REQUIRED" if q0_hold else
             "ONE_MS_NR2R2B0_BASELINE_REPEATABLE_Q0_NOT_HOLD_ACTIVE_RECOVERY_REQUIRED")
    final = {"schema_version": stage["schema_version"], "source_revision": source_revision,
             "passed": safety and repeatable, "q0_short_hold_candidate": q0_hold, "route": route,
             "rollouts_completed": len(rows), "plant_advances": sum(x["plant_advances"] for x in rows),
             "repeatability": comparisons, "hold_metrics": [x["hold_metrics"] for x in rows if x["hold_metrics"]],
             "claim_boundary": "same-source_q0_baseline_only_not_perturbation_recovery_or_control"}
    write_new(output / "result.json", final)
    return final


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("offline", "run"))
    parser.add_argument("--stage-config", type=Path, default=ROOT / "configs/rgeo_zgeo_1ms_nr2r2b0_source_baseline.json")
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = offline(args.stage_config.resolve(), args.source_revision) if args.mode == "offline" else run(args.stage_config.resolve(), args.source_revision, args.output.resolve())
    if args.mode == "offline":
        write_new(args.output.resolve(), result)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
