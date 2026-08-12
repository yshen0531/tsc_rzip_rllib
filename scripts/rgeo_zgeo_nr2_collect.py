#!/usr/bin/env python3
"""Offline-check and collect the frozen NR2 identification trajectories."""

from __future__ import annotations

import argparse
import hashlib
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.rgeo_zgeo_nr1_qualification import _read_source_state, _state_record  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_contract import DataIdentity, RGeoZGeoSignal  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_nr1 import (  # noqa: E402
    NR1SafetyEnvelope,
    quantize_card15_target,
)
from tsc_rzip_rllib.control.rgeo_zgeo_nr2_spec import (  # noqa: E402
    NR2_CAMPAIGN_ID,
    NR2_CONTRACT_VERSION,
    build_nr2_specs,
    validate_nr2_specs,
)
from tsc_rzip_rllib.core.runner import TSCConfig, TSCStepRunner  # noqa: E402


DEFAULT_CONFIG = REPO_ROOT / "stage1_1_runs" / "stage1_1_svd234_strict_validation_100ms_20260718_025916" / "env_config.resolved.json"


def _write_new(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _targets(cfg: TSCConfig, source_current: np.ndarray, actions: tuple[tuple[float, ...], ...]) -> list[Any]:
    q0 = np.asarray(quantize_card15_target(source_current, cfg.turns_tsc).quantized_current_a_tsc)
    return [
        quantize_card15_target(
            q0 + np.asarray(action, dtype=float) * cfg.max_delta_current_a_per_step,
            cfg.turns_tsc,
        )
        for action in actions
    ]


def offline(config_path: Path, source_revision: str) -> dict[str, Any]:
    cfg = TSCConfig.from_json(config_path)
    source = _read_source_state(cfg)
    signal = RGeoZGeoSignal.from_tsc_state(source)
    envelope = NR1SafetyEnvelope.from_source_signal(signal)
    specs = build_nr2_specs()
    spec_gate = validate_nr2_specs(specs)
    maximum_increment = 0.0
    quantized_rows: list[list[float]] = []
    failures: list[str] = []
    for spec in specs:
        current = np.asarray(source["currents_a_tsc"], dtype=float)
        for step, target in enumerate(_targets(cfg, current * 0.0 + source["currents_a_tsc"], spec.normalized_actions_tsc)):
            target_a = np.asarray(target.quantized_current_a_tsc)
            reasons = envelope.target_reasons(
                actual_current_a_tsc=current,
                target_current_a_tsc=target_a,
                min_current_a_tsc=cfg.min_current_a_tsc,
                max_current_a_tsc=cfg.max_current_a_tsc,
                max_delta_current_a_per_step=cfg.max_delta_current_a_per_step,
            )
            if reasons:
                failures.append(f"{spec.trajectory_id}:{step}:{','.join(reasons)}")
            maximum_increment = max(maximum_increment, float(np.max(np.abs(target_a - current))))
            q0 = np.asarray(quantize_card15_target(source["currents_a_tsc"], cfg.turns_tsc).quantized_current_a_tsc)
            quantized_rows.append(target_a - q0)
            current = target_a
    split_ranks = {}
    offset = 0
    for split in ("development", "calibration", "holdout"):
        count = sum(1 for spec in specs if spec.split == split) * 8
        rows = np.asarray(quantized_rows[offset : offset + count])
        split_ranks[split] = int(np.linalg.matrix_rank(rows))
        offset += count
        if split_ranks[split] != 14:
            failures.append(f"{split}:QUANTIZED_RANK:{split_ranks[split]}")
    identity = DataIdentity(NR2_CAMPAIGN_ID, "identification", True, source_revision)
    passed = not failures and cfg.start_folder == "1100ms" and cfg.dt_ms == 10
    return {
        "schema_version": NR2_CONTRACT_VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "identity": identity.to_dict(),
        "passed": passed,
        "route": "NR2_OFFLINE_GATE_PASS" if passed else "NR2_OFFLINE_GATE_FAIL_NO_TSC",
        "failures": failures,
        "source_signal": signal.to_dict(),
        "safety_envelope": envelope.to_dict(),
        "spec_gate": spec_gate,
        "quantized_action_ranks": split_ranks,
        "maximum_sequential_target_increment_a": maximum_increment,
    }


def _run_spec(cfg: TSCConfig, spec: Any, envelope: NR1SafetyEnvelope, source_current: np.ndarray) -> dict[str, Any]:
    runner = TSCStepRunner(cfg, worker_id=f"nr2_{spec.trajectory_id}", keep_workspace=False)
    actions: list[dict[str, Any]] = []
    states: list[dict[str, Any]] = []
    failures: list[str] = []
    started = time.perf_counter()
    targets = _targets(cfg, source_current, spec.normalized_actions_tsc)
    try:
        state = runner.reset(episode_name=spec.trajectory_id)
        for step, target in enumerate(targets):
            try:
                signal = RGeoZGeoSignal.from_tsc_state(state)
                failures.extend(envelope.state_reasons(
                    signal=signal,
                    actual_current_a_tsc=state["currents_a_tsc"],
                    min_current_a_tsc=cfg.min_current_a_tsc,
                    max_current_a_tsc=cfg.max_current_a_tsc,
                ))
                failures.extend(envelope.target_reasons(
                    actual_current_a_tsc=state["currents_a_tsc"],
                    target_current_a_tsc=target.quantized_current_a_tsc,
                    min_current_a_tsc=cfg.min_current_a_tsc,
                    max_current_a_tsc=cfg.max_current_a_tsc,
                    max_delta_current_a_per_step=cfg.max_delta_current_a_per_step,
                ))
                states.append(_state_record(cfg, state, target.serialized_card15_fields))
            except Exception as exc:
                failures.append(f"PRESTEP:{type(exc).__name__}:{exc}")
            if failures:
                break
            actions.append({
                "issue_step": step,
                "issue_time_ms": int(state["time_ms"]),
                "normalized_action_tsc": list(spec.normalized_actions_tsc[step]),
                "target": target.to_dict(),
            })
            state = runner.step_current_a(np.asarray(target.quantized_current_a_tsc))
            if state.get("returncode", 0) != 0 or state.get("abnormal", False):
                failures.append(f"TSC:{state.get('returncode')}:{state.get('done_reason', '')}")
            try:
                signal = RGeoZGeoSignal.from_tsc_state(state)
                failures.extend(envelope.state_reasons(
                    signal=signal,
                    actual_current_a_tsc=state["currents_a_tsc"],
                    min_current_a_tsc=cfg.min_current_a_tsc,
                    max_current_a_tsc=cfg.max_current_a_tsc,
                ))
            except Exception as exc:
                failures.append(f"POSTSTEP:{type(exc).__name__}:{exc}")
            if failures:
                try:
                    states.append(_state_record(cfg, state, ()))
                except Exception as exc:
                    failures.append(f"FAILED_RECORD:{type(exc).__name__}:{exc}")
                break
        else:
            states.append(_state_record(cfg, state, ()))
    except Exception as exc:
        failures.append(f"EXECUTION:{type(exc).__name__}:{exc}")
    finally:
        runner.cleanup_runtime_workspace()
    failures = list(dict.fromkeys(failures))
    return {
        "schema_version": NR2_CONTRACT_VERSION,
        "spec": spec.to_dict(),
        "passed": not failures and len(actions) == 8 and len(states) == 9,
        "failures": failures,
        "plant_advances": len(actions),
        "wall_time_s": time.perf_counter() - started,
        "actions": actions,
        "states": states,
    }


def collect(config_path: Path, source_revision: str, output_dir: Path, phase: str, authorization: Path | None) -> dict[str, Any]:
    gate = offline(config_path, source_revision)
    if not gate["passed"]:
        raise RuntimeError("NR2 offline gate failed; TSC forbidden")
    if phase == "development_calibration":
        if output_dir.exists():
            raise FileExistsError(f"refusing to overwrite {output_dir}")
        output_dir.mkdir(parents=True)
        _write_new(output_dir / "offline_preflight.json", gate)
        allowed_splits = {"development", "calibration"}
    else:
        if not output_dir.is_dir() or authorization is None or not authorization.is_file():
            raise RuntimeError("holdout requires existing campaign and authorization file")
        auth = json.loads(authorization.read_text(encoding="utf-8"))
        if (
            auth.get("campaign_id") != NR2_CAMPAIGN_ID
            or auth.get("holdout_authorized") is not True
            or auth.get("source_revision") != source_revision
        ):
            raise RuntimeError("invalid NR2 holdout authorization")
        bundle = output_dir / "frozen_models.pt"
        if not bundle.is_file() or auth.get("frozen_model_sha256") != [_sha256(bundle)]:
            raise RuntimeError("holdout authorization frozen model hash mismatch")
        allowed_splits = {"holdout"}
    cfg = TSCConfig.from_json(config_path)
    cfg = replace(cfg, run_root=output_dir / "rollouts", runtime_only_fast_mode=False,
                  save_step_artifacts=False, keep_episode_restart_files=True,
                  cleanup_episode_dir=False, keep_failed_episode_dir=True)
    source = _read_source_state(cfg)
    envelope = NR1SafetyEnvelope.from_source_signal(RGeoZGeoSignal.from_tsc_state(source))
    selected = [spec for spec in build_nr2_specs() if spec.split in allowed_splits]
    completed: list[str] = []
    advances = 0
    failures: list[str] = []
    for spec in selected:
        result = _run_spec(cfg, spec, envelope, np.asarray(source["currents_a_tsc"]))
        _write_new(output_dir / "records" / f"{spec.trajectory_id}.json", result)
        completed.append(spec.trajectory_id)
        advances += result["plant_advances"]
        if not result["passed"]:
            failures.extend(f"{spec.trajectory_id}:{value}" for value in result["failures"])
            break
    summary = {
        "schema_version": NR2_CONTRACT_VERSION,
        "campaign_id": NR2_CAMPAIGN_ID,
        "phase": phase,
        "source_revision": source_revision,
        "passed": not failures and len(completed) == len(selected),
        "route": f"NR2_{phase.upper()}_COLLECTION_PASS" if not failures and len(completed) == len(selected) else "NR2_SAFETY_FAIL_STOP",
        "expected_trajectories": len(selected),
        "completed_trajectories": len(completed),
        "plant_advances": advances,
        "failures": failures,
        "trajectory_ids": completed,
    }
    _write_new(output_dir / f"{phase}_collection.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("offline", "collect"))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phase", choices=("development_calibration", "holdout"), default="development_calibration")
    parser.add_argument("--authorization", type=Path)
    args = parser.parse_args()
    if args.mode == "offline":
        result = offline(args.config.resolve(), args.source_revision)
        _write_new(args.output.resolve(), result)
    else:
        result = collect(args.config.resolve(), args.source_revision, args.output.resolve(), args.phase,
                         None if args.authorization is None else args.authorization.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
