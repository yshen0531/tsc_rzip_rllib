#!/usr/bin/env python3
"""Fresh fixed-1000 q0 natural-drift baseline and exact replay."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import sys
import time
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_nr1_qualification import _record, _source  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    OneMsNR1SafetyEnvelope,
    assert_exact_slew,
    build_frozen_one_ms_prefixes,
    card15_target_decimal_a,
    validate_one_ms_config,
)
from tsc_rzip_rllib.control.rgeo_zgeo_contract import ContractError, RGeoZGeoSignal  # noqa: E402
from tsc_rzip_rllib.core.runner import TSCConfig, TSCStepRunner  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-1000-baseline-b0-v1"
CONFIG_SHA256 = "4f03648900e4793ba8b136993be01c2a77179ea6f94377de29fa15a8b3dc45d5"
DEFAULT_CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_baseline_b0.json"
SEMANTIC_ARTIFACTS = ("inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv")


class InputIntegrityError(ValueError):
    """Frozen stage or evidence identity is not exact."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inside_root(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT.resolve()):
        raise InputIntegrityError(f"{label} leaves repository")
    return resolved


def write_new(path: Path, value: Any) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def load(config_path: Path) -> tuple[dict[str, Any], TSCConfig]:
    config_path = inside_root(config_path, "stage config")
    if sha256(config_path) != CONFIG_SHA256:
        raise InputIntegrityError("stage config SHA-256 mismatch")
    stage = json.loads(config_path.read_text(encoding="utf-8"))
    exact = {
        "schema_version": SCHEMA,
        "campaign_id": "rgeo_zgeo_1ms_1000_baseline_b0_v1",
        "takeover_time_ms": 1000,
        "control_period_ms": 1,
        "horizon_steps": 64,
        "rollouts": 2,
        "maximum_reset_calls": 2,
        "maximum_advance_attempts": 128,
        "maximum_gotsc_calls": 128,
        "maximum_verified_plant_advances": 128,
        "retry_after_any_advance_attempt": "forbidden",
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise InputIntegrityError(f"frozen field mismatch: {key}")
    expected_roles = {
        "baseline_primary": "development_fit_eligible_baseline_weight_1",
        "baseline_replay": "integrity_replay_zero_fit_weight",
        "calibration": "unopened",
        "holdout": "unopened",
        "controller_or_recourse": "forbidden",
    }
    if stage.get("data_roles") != expected_roles:
        raise InputIntegrityError("data-role contract mismatch")
    for label, row in stage["prerequisites"].items():
        path = inside_root(ROOT / row["path"], f"prerequisite {label}")
        if not path.is_file() or sha256(path) != row["sha256"]:
            raise InputIntegrityError(f"prerequisite hash mismatch: {label}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("passed") is not True or payload.get("route") != row["route"]:
            raise InputIntegrityError(f"prerequisite route mismatch: {label}")
    base = inside_root(ROOT / stage["base_tsc_config"], "base TSC config")
    if sha256(base) != stage["base_tsc_config_sha256"]:
        raise InputIntegrityError("base TSC config SHA-256 mismatch")
    cfg = TSCConfig.from_json(base)
    validate_one_ms_config(
        start_folder=cfg.start_folder,
        dt_ms=cfg.dt_ms,
        slew_a_per_ms=cfg.current_slew_a_per_ms,
        expected_start_folder="1000ms",
    )
    return stage, cfg


def target_and_source(stage: dict[str, Any], cfg: TSCConfig) -> tuple[Any, dict[str, Any]]:
    source = _source(cfg)
    frozen = build_frozen_one_ms_prefixes(
        source_current_a_tsc=source["currents_a_tsc"],
        source_command_a_tsc=source["active_command_decimal_a_tsc"],
        turns_tsc=cfg.turns_tsc,
        min_current_a_tsc=cfg.min_current_a_tsc,
        max_current_a_tsc=cfg.max_current_a_tsc,
        maximum_command_delta_a=Decimal("0.299"),
    )
    q0 = frozen.q0
    exact = card15_target_decimal_a(q0, cfg.turns_tsc, name="baseline.q0")
    maximum = assert_exact_slew(
        source["active_command_decimal_a_tsc"], exact, name="baseline.source_to_q0"
    )
    if maximum != 0.0 or tuple(exact) != tuple(source["active_command_decimal_a_tsc"]):
        raise ContractError("baseline q0 is not the exact semantic active source command")
    if stage["action_contract"]["target"] != "exact_source_active_card15_q0":
        raise InputIntegrityError("action target contract changed")
    return q0, source


def offline(config_path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    source_signal = None
    try:
        stage, cfg = load(config_path)
        q0, source = target_and_source(stage, cfg)
        source_signal = RGeoZGeoSignal.from_tsc_state(source)
        envelope = OneMsNR1SafetyEnvelope.from_signal(source_signal)
        failures.extend(envelope.state_reasons(
            source_signal, source["currents_a_tsc"],
            cfg.min_current_a_tsc, cfg.max_current_a_tsc,
        ))
        exact = card15_target_decimal_a(q0, cfg.turns_tsc, name="baseline.q0")
        if any(assert_exact_slew(exact, exact, name=f"baseline.issue.{index}") != 0.0
               for index in range(stage["horizon_steps"])):
            failures.append("NONZERO_Q0_STREAM")
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
        stage = None
    failures = list(dict.fromkeys(failures))
    routes = (stage or {}).get("routes", {})
    return {
        "schema_version": SCHEMA,
        "kind": "offline_preflight",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_revision": source_revision,
        "passed": not failures,
        "route": routes.get("offline_pass") if not failures else routes.get(
            "offline_fail", "ONE_MS_NR1000B0_OFFLINE_FAIL_NO_TSC"
        ),
        "failures": failures,
        "authorized_reset_calls": 2,
        "authorized_plant_advances": 128,
        "source_signal": None if source_signal is None else source_signal.to_dict(),
    }


def _run_one(
    cfg: TSCConfig, stage: dict[str, Any], q0: Any,
    envelope: OneMsNR1SafetyEnvelope, rollout_id: str,
) -> dict[str, Any]:
    runner = TSCStepRunner(cfg, worker_id=f"nr1000_b0_{rollout_id}", keep_workspace=False)
    reasons: list[str] = []
    states: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    attempts = gotsc_calls = verified = 0
    reset_calls = 0
    started = time.perf_counter()
    try:
        reset_calls += 1
        live = runner.reset(episode_name=rollout_id)
        states.append(_record(cfg, live))
        origin_time = states[0]["time_ms"]
        for issue in range(stage["horizon_steps"]):
            reasons.extend(envelope.state_reasons(
                RGeoZGeoSignal.from_tsc_state(live), live["currents_a_tsc"],
                cfg.min_current_a_tsc, cfg.max_current_a_tsc,
            ))
            target_decimal = card15_target_decimal_a(
                q0, cfg.turns_tsc, name=f"{rollout_id}.target.{issue}"
            )
            maximum = assert_exact_slew(
                states[-1]["active_command_decimal_a_tsc"], target_decimal,
                name=f"{rollout_id}.issued.{issue}",
            )
            if reasons:
                break
            actions.append({
                "issue_step": issue,
                "issue_time_ms": int(live["time_ms"]),
                "effect_state_index": issue + 1,
                "effect_time_ms": origin_time + issue + 1,
                "expected_card15_fields": list(q0.card15_fields),
                "maximum_issued_delta_a": maximum,
            })
            attempts += 1
            live = runner.step_current_a(np.asarray(q0.current_a_tsc, dtype=float))
            gotsc_calls += 1
            record = _record(cfg, live)
            states.append(record)
            if int(live.get("returncode", 0)) != 0:
                reasons.append(f"TSC_RETURNCODE:{issue}:{live.get('returncode')}")
            if bool(live.get("abnormal", False)):
                reasons.append(f"TSC_ABNORMAL:{issue}:{live.get('done_reason', '')}")
            if record["time_ms"] != origin_time + issue + 1:
                reasons.append(f"TIME:{issue}")
            else:
                verified += 1
            if tuple(record["active_command_card15_fields"]) != tuple(q0.card15_fields):
                reasons.append(f"CARD15:{issue}")
            if issue == 0:
                record["observed_delta_role"] = "source_bias_descriptive_matched_hold_reference"
                record["maximum_observed_delta_a"] = float(max(
                    abs(Decimal(after) - Decimal(before))
                    for before, after in zip(
                        states[-2]["actual_current_decimal_a_tsc"],
                        record["actual_current_decimal_a_tsc"],
                    )
                ))
            else:
                record["maximum_observed_delta_a"] = assert_exact_slew(
                    states[-2]["actual_current_decimal_a_tsc"],
                    record["actual_current_decimal_a_tsc"],
                    name=f"{rollout_id}.observed.{issue}",
                )
            reasons.extend(envelope.state_reasons(
                RGeoZGeoSignal.from_tsc_state(live), live["currents_a_tsc"],
                cfg.min_current_a_tsc, cfg.max_current_a_tsc,
            ))
            if reasons:
                break
    except Exception as exc:
        reasons.append(f"EXECUTION:{type(exc).__name__}:{exc}")
    finally:
        try:
            runner.cleanup_runtime_workspace()
        except Exception as exc:
            reasons.append(f"CLEANUP:{type(exc).__name__}:{exc}")
    reasons = list(dict.fromkeys(reasons))
    complete = (
        not reasons and reset_calls == 1
        and attempts == gotsc_calls == verified == stage["horizon_steps"]
        and len(actions) == stage["horizon_steps"]
        and len(states) == stage["horizon_steps"] + 1
    )
    return {
        "rollout_id": rollout_id,
        "data_role": stage["data_roles"][rollout_id],
        "passed": complete,
        "reasons": reasons,
        "reset_calls": reset_calls,
        "advance_attempts": attempts,
        "gotsc_calls": gotsc_calls,
        "verified_plant_advances": verified,
        "states": states,
        "actions": actions,
        "wall_time_s": time.perf_counter() - started,
    }


def compare_replay(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    maxima = {"geometry_m": 0.0, "ip_a": 0.0, "coil_a": 0.0, "wire_a": 0.0}
    if len(left["states"]) != 65 or len(right["states"]) != 65:
        failures.append("STATE_COUNT")
    for index, (a, b) in enumerate(zip(left["states"], right["states"])):
        if a["time_ms"] != b["time_ms"]:
            failures.append(f"TIME:{index}")
        maxima["geometry_m"] = max(
            maxima["geometry_m"], *(abs(a[key] - b[key]) for key in ("r_geo_m", "z_geo_m", "r_mid_m"))
        )
        maxima["ip_a"] = max(maxima["ip_a"], abs(a["ip_a"] - b["ip_a"]))
        maxima["coil_a"] = max(maxima["coil_a"], max(
            abs(x - y) for x, y in zip(a["actual_current_a_tsc"], b["actual_current_a_tsc"])
        ))
        maxima["wire_a"] = max(maxima["wire_a"], max(
            abs(x - y) for x, y in zip(a["wire_current_a"], b["wire_current_a"])
        ))
        for name in SEMANTIC_ARTIFACTS:
            if a["artifact_sha256"][name] != b["artifact_sha256"][name]:
                failures.append(f"SEMANTIC_ARTIFACT:{name}:{index}")
    if maxima["geometry_m"] > 1e-12:
        failures.append("GEOMETRY")
    if maxima["ip_a"] > 1e-9:
        failures.append("IP")
    if maxima["coil_a"] > 1e-9:
        failures.append("COIL")
    if maxima["wire_a"] > 1e-9:
        failures.append("WIRE")
    return {"passed": not failures, "failures": list(dict.fromkeys(failures)), "maximum_absolute_difference": maxima}


def drift_metrics(states: Sequence[dict[str, Any]]) -> dict[str, Any]:
    source = states[0]
    increments = [
        ((b["r_geo_m"] - a["r_geo_m"]) * 1000.0,
         (b["z_geo_m"] - a["z_geo_m"]) * 1000.0,
         b["ip_a"] - a["ip_a"])
        for a, b in zip(states, states[1:])
    ]
    speeds = [math.hypot(row[0], row[1]) for row in increments]
    terminal = states[-1]
    tail_start = states[-9]
    return {
        "terminal_state_index": len(states) - 1,
        "terminal_time_ms": terminal["time_ms"],
        "terminal_source_delta": {
            "r_mm": (terminal["r_geo_m"] - source["r_geo_m"]) * 1000.0,
            "z_mm": (terminal["z_geo_m"] - source["z_geo_m"]) * 1000.0,
            "ip_a": terminal["ip_a"] - source["ip_a"],
        },
        "last_8ms_net_delta": {
            "r_mm": (terminal["r_geo_m"] - tail_start["r_geo_m"]) * 1000.0,
            "z_mm": (terminal["z_geo_m"] - tail_start["z_geo_m"]) * 1000.0,
            "ip_a": terminal["ip_a"] - tail_start["ip_a"],
        },
        "maximum_absolute_one_step": {
            "r_mm": max(abs(row[0]) for row in increments),
            "z_mm": max(abs(row[1]) for row in increments),
            "ip_a": max(abs(row[2]) for row in increments),
            "rz_speed_m_s": max(speeds),
        },
        "terminal_8state_maximum_rz_speed_m_s": max(speeds[-8:]),
    }


def run(config_path: Path, source_revision: str, output_dir: Path) -> dict[str, Any]:
    preflight = offline(config_path, source_revision)
    if not preflight["passed"]:
        raise RuntimeError("offline gate failed; TSC forbidden")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {output_dir}")
    output_dir.mkdir(parents=True)
    write_new(output_dir / "offline_preflight.json", preflight)
    stage, cfg = load(config_path)
    cfg.run_root = output_dir / "rollouts"
    q0, source = target_and_source(stage, cfg)
    envelope = OneMsNR1SafetyEnvelope.from_signal(RGeoZGeoSignal.from_tsc_state(source))
    rows: dict[str, dict[str, Any]] = {}
    for rollout_id in ("baseline_primary", "baseline_replay"):
        row = _run_one(cfg, stage, q0, envelope, rollout_id)
        rows[rollout_id] = row
        write_new(output_dir / f"{rollout_id}.json", row)
        if not row["passed"]:
            break
    comparison = None
    if len(rows) == 2:
        comparison = compare_replay(rows["baseline_primary"], rows["baseline_replay"])
    execution_pass = len(rows) == 2 and all(row["passed"] for row in rows.values())
    replay_pass = comparison is not None and comparison["passed"]
    passed = execution_pass and replay_pass
    route = stage["routes"]["pass"] if passed else (
        stage["routes"]["execution_fail"] if not execution_pass else stage["routes"]["replay_fail"]
    )
    result = {
        "schema_version": SCHEMA,
        "kind": "authentic_fixed_1000_baseline",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_revision": source_revision,
        "passed": passed,
        "route": route,
        "rollout_count": len(rows),
        "reset_calls": sum(row["reset_calls"] for row in rows.values()),
        "advance_attempts": sum(row["advance_attempts"] for row in rows.values()),
        "gotsc_calls": sum(row["gotsc_calls"] for row in rows.values()),
        "verified_plant_advances": sum(row["verified_plant_advances"] for row in rows.values()),
        "replay": comparison,
        "drift_metrics": drift_metrics(rows["baseline_primary"]["states"]) if execution_pass else None,
        "claim_boundary": "fixed-1000 q0 natural drift and replay only; no hold/model/authority/control",
    }
    write_new(output_dir / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("offline", "run"))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = offline(args.config.resolve(), args.source_revision) if args.mode == "offline" else run(
        args.config.resolve(), args.source_revision, args.output.resolve()
    )
    if args.mode == "offline":
        write_new(args.output.resolve(), result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
