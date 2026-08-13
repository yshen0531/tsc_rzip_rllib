#!/usr/bin/env python3
"""Offline gate and phased authentic collection for the frozen 1 ms NR2."""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import shutil
import sys
import time
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_nr1_qualification import _record, _source  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    OneMsNR1SafetyEnvelope,
    assert_exact_slew,
    card15_target_decimal_a,
    validate_one_ms_config,
)
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr2_spec import (  # noqa: E402
    NR2_1MS_CAMPAIGN_ID,
    NR2_1MS_CONTRACT_VERSION,
    NR2_1MS_HORIZON_STEPS,
    build_one_ms_nr2_specs,
    build_one_ms_nr2_targets,
    validate_one_ms_nr2_specs,
)
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr2_models import q0_readback_bias  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_contract import ContractError, DataIdentity, RGeoZGeoSignal  # noqa: E402
from tsc_rzip_rllib.core.runner import TSCConfig, TSCStepRunner  # noqa: E402

DEFAULT_CONFIG = ROOT / "configs/rgeo_zgeo_1ms_nr1_safety_effect.json"
STRUCTURAL_CURRENT_ERROR_A = Decimal("1e-9")


def _write_new(path: Path, payload: Any) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def offline(config_path: Path, source_revision: str) -> dict[str, Any]:
    cfg = TSCConfig.from_json(config_path)
    failures: list[str] = []
    gate: dict[str, Any] | None = None
    signal = None
    disk_free_bytes = None
    try:
        validate_one_ms_config(start_folder=cfg.start_folder, dt_ms=cfg.dt_ms,
                               slew_a_per_ms=cfg.current_slew_a_per_ms)
        source = _source(cfg)
        signal = RGeoZGeoSignal.from_tsc_state(source)
        gate = validate_one_ms_nr2_specs(
            build_one_ms_nr2_specs(), source_current_a_tsc=source["currents_a_tsc"],
            turns_tsc=cfg.turns_tsc,
        )
        disk_free_bytes = shutil.disk_usage(cfg.resolved_run_root().parent).free
        if disk_free_bytes < 80 * 1024**3:
            failures.append("DISK_FREE_BELOW_80_GIB")
        envelope = OneMsNR1SafetyEnvelope.from_signal(signal)
        failures.extend(envelope.state_reasons(signal, source["currents_a_tsc"],
                                                cfg.min_current_a_tsc, cfg.max_current_a_tsc))
        for spec in build_one_ms_nr2_specs():
            targets = build_one_ms_nr2_targets(
                spec, source_current_a_tsc=source["currents_a_tsc"], turns_tsc=cfg.turns_tsc)
            previous = source["active_command_decimal_a_tsc"]
            for step, target in enumerate(targets):
                current = card15_target_decimal_a(target, cfg.turns_tsc,
                                                  name=f"offline.{spec.trajectory_id}.{step}")
                assert_exact_slew(previous, current, name=f"offline.{spec.trajectory_id}.{step}")
                if any(not Decimal(str(low)) <= value <= Decimal(str(high)) for value, low, high in
                       zip(current, cfg.min_current_a_tsc, cfg.max_current_a_tsc)):
                    failures.append(f"TARGET_CURRENT:{spec.trajectory_id}:{step}")
                previous = current
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    identity = DataIdentity(NR2_1MS_CAMPAIGN_ID, "identification", True, source_revision)
    passed = not failures
    return {
        "schema_version": NR2_1MS_CONTRACT_VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "identity": identity.to_dict(),
        "passed": passed,
        "route": "ONE_MS_NR2R1_OFFLINE_PASS" if passed else "ONE_MS_NR2R1_OFFLINE_FAIL_NO_TSC",
        "failures": list(dict.fromkeys(failures)),
        "config_path": str(config_path),
        "disk_free_bytes": disk_free_bytes,
        "source_signal": None if signal is None else signal.to_dict(),
        "spec_gate": gate,
        "structural_current_error_cap_a": str(STRUCTURAL_CURRENT_ERROR_A),
    }


def _run_spec(cfg: TSCConfig, spec: Any, envelope: OneMsNR1SafetyEnvelope,
              source: dict[str, Any]) -> dict[str, Any]:
    runner = TSCStepRunner(cfg, worker_id=f"one_ms_nr2_{spec.trajectory_id}", keep_workspace=False)
    targets = build_one_ms_nr2_targets(
        spec, source_current_a_tsc=source["currents_a_tsc"], turns_tsc=cfg.turns_tsc)
    source_readback = tuple(Decimal(value) for value in source["currents_decimal_a_tsc"])
    q0_command = card15_target_decimal_a(
        targets[0], cfg.turns_tsc, name=f"{spec.trajectory_id}.q0"
    )
    bias = q0_readback_bias(source_readback, q0_command)
    states: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    failures: list[str] = []
    started = time.perf_counter()
    try:
        state = runner.reset(episode_name=spec.trajectory_id)
        states.append(_record(cfg, state))
        for step, target in enumerate(targets):
            before = states[-1]
            signal = RGeoZGeoSignal.from_tsc_state(state)
            failures.extend(envelope.state_reasons(signal, state["currents_a_tsc"],
                                                   cfg.min_current_a_tsc, cfg.max_current_a_tsc))
            target_decimal = card15_target_decimal_a(
                target, cfg.turns_tsc, name=f"{spec.trajectory_id}.target.{step}")
            try:
                issued_max = assert_exact_slew(
                    before["active_command_decimal_a_tsc"], target_decimal,
                    name=f"{spec.trajectory_id}.issued.{step}")
            except ContractError as exc:
                failures.append(f"ISSUED_SLEW:{exc}")
                break
            if failures:
                break
            command_before = tuple(Decimal(value) for value in before["active_command_decimal_a_tsc"])
            actions.append({
                "issue_step": step,
                "issue_time_ms": int(state["time_ms"]),
                "target": target.to_dict(),
                "command_delta_decimal_a_tsc": [str(a-b) for a,b in zip(target_decimal, command_before)],
                "maximum_issued_delta_a": issued_max,
            })
            state = runner.step_current_a(np.asarray(target.current_a_tsc, dtype=float))
            if int(state.get("returncode", 0)) != 0 or bool(state.get("abnormal", False)):
                failures.append(f"TSC:{state.get('returncode')}:{state.get('done_reason', '')}")
            record = _record(cfg, state)
            states.append(record)
            if record["time_ms"] != 1100 + step + 1:
                failures.append(f"TIME:{step}")
            if tuple(record["active_command_card15_fields"]) != target.card15_fields:
                failures.append(f"CARD15:{step}")
            try:
                record["maximum_observed_delta_a"] = assert_exact_slew(
                    before["actual_current_decimal_a_tsc"], record["actual_current_decimal_a_tsc"],
                    name=f"{spec.trajectory_id}.observed.{step}")
            except ContractError as exc:
                failures.append(f"OBSERVED_SLEW:{exc}")
            actual = tuple(Decimal(value) for value in record["actual_current_decimal_a_tsc"])
            predicted = tuple(command + offset for command, offset in zip(target_decimal, bias))
            structural_error = max(abs(value-wanted) for value,wanted in zip(actual,predicted))
            record["structural_current_prediction_decimal_a_tsc"] = [str(value) for value in predicted]
            record["maximum_structural_current_error_a"] = str(structural_error)
            if structural_error > STRUCTURAL_CURRENT_ERROR_A:
                failures.append(f"STRUCTURAL_CURRENT:{step}")
            failures.extend(envelope.state_reasons(RGeoZGeoSignal.from_tsc_state(state),
                                                   state["currents_a_tsc"], cfg.min_current_a_tsc,
                                                   cfg.max_current_a_tsc))
            if failures:
                break
    except Exception as exc:
        failures.append(f"EXECUTION:{type(exc).__name__}:{exc}")
    finally:
        runner.cleanup_runtime_workspace()
    failures = list(dict.fromkeys(failures))
    return {
        "schema_version": NR2_1MS_CONTRACT_VERSION,
        "spec": spec.to_dict(),
        "passed": not failures and len(actions) == NR2_1MS_HORIZON_STEPS and len(states) == NR2_1MS_HORIZON_STEPS + 1,
        "failures": failures,
        "plant_advances": len(actions),
        "source_readback_bias_decimal_a_tsc": [str(value) for value in bias],
        "wall_time_s": time.perf_counter() - started,
        "actions": actions,
        "states": states,
    }


def collect(config_path: Path, source_revision: str, output_dir: Path, phase: str,
            authorization: Path | None) -> dict[str, Any]:
    gate = offline(config_path, source_revision)
    if not gate["passed"]:
        raise RuntimeError("1 ms NR2 offline gate failed; TSC forbidden")
    if phase == "development_calibration":
        if output_dir.exists():
            raise FileExistsError(f"refusing to overwrite {output_dir}")
        output_dir.mkdir(parents=True)
        _write_new(output_dir / "offline_preflight.json", gate)
        allowed = {"development", "calibration"}
    else:
        if not output_dir.is_dir() or authorization is None or not authorization.is_file():
            raise RuntimeError("holdout requires an existing campaign and authorization")
        auth = json.loads(authorization.read_text(encoding="utf-8"))
        bundle = output_dir / "frozen_models.pt"
        if (auth.get("campaign_id") != NR2_1MS_CAMPAIGN_ID or auth.get("holdout_authorized") is not True
                or auth.get("source_revision") != source_revision or not bundle.is_file()):
            raise RuntimeError("invalid 1 ms NR2 holdout authorization")
        import hashlib
        if auth.get("frozen_model_sha256") != hashlib.sha256(bundle.read_bytes()).hexdigest():
            raise RuntimeError("frozen model hash mismatch")
        allowed = {"holdout"}
    cfg = TSCConfig.from_json(config_path)
    cfg = replace(cfg, run_root=output_dir / "rollouts", runtime_only_fast_mode=False,
                  save_step_artifacts=False, keep_episode_restart_files=True,
                  cleanup_episode_dir=False, keep_failed_episode_dir=True)
    source = _source(cfg)
    envelope = OneMsNR1SafetyEnvelope.from_signal(RGeoZGeoSignal.from_tsc_state(source))
    selected = [value for value in build_one_ms_nr2_specs() if value.split in allowed]
    completed: list[str] = []
    failures: list[str] = []
    advances = 0
    for spec in selected:
        result = _run_spec(cfg, spec, envelope, source)
        _write_new(output_dir / "records" / f"{spec.trajectory_id}.json", result)
        completed.append(spec.trajectory_id)
        advances += result["plant_advances"]
        if not result["passed"]:
            failures.extend(f"{spec.trajectory_id}:{value}" for value in result["failures"])
            break
    passed = not failures and len(completed) == len(selected)
    result = {
        "schema_version": NR2_1MS_CONTRACT_VERSION,
        "campaign_id": NR2_1MS_CAMPAIGN_ID,
        "phase": phase,
        "source_revision": source_revision,
        "passed": passed,
        "route": f"ONE_MS_NR2R1_{phase.upper()}_COLLECTION_PASS" if passed else "ONE_MS_NR2R1_SAFETY_FAIL_STOP",
        "expected_trajectories": len(selected),
        "completed_trajectories": len(completed),
        "plant_advances": advances,
        "failures": failures,
        "trajectory_ids": completed,
    }
    _write_new(output_dir / f"{phase}_collection.json", result)
    return result


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("mode",choices=("offline","collect")); parser.add_argument("--config",type=Path,default=DEFAULT_CONFIG); parser.add_argument("--source-revision",required=True); parser.add_argument("--output",type=Path,required=True); parser.add_argument("--phase",choices=("development_calibration","holdout"),default="development_calibration"); parser.add_argument("--authorization",type=Path)
    args=parser.parse_args(); result=offline(args.config.resolve(),args.source_revision) if args.mode=="offline" else collect(args.config.resolve(),args.source_revision,args.output.resolve(),args.phase,None if args.authorization is None else args.authorization.resolve())
    if args.mode=="offline": _write_new(args.output.resolve(),result)
    print(json.dumps(result,indent=2,sort_keys=True)); return 0 if result["passed"] else 2


if __name__ == "__main__": raise SystemExit(main())
