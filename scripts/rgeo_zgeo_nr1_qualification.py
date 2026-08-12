#!/usr/bin/env python3
"""Run the prospectively frozen NR1 offline gate or four-rollout campaign."""

from __future__ import annotations

import argparse
import csv
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from typing import Any, Sequence

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tsc_rzip_rllib.control.rgeo_zgeo_contract import (  # noqa: E402
    ContractError,
    DataIdentity,
    RGeoZGeoSignal,
)
from tsc_rzip_rllib.control.rgeo_zgeo_nr1 import (  # noqa: E402
    NR1_CONTRACT_VERSION,
    NR1_HORIZON_STEPS,
    NR1_INTENDED_USE,
    NR1SafetyEnvelope,
    artifact_sha256,
    build_frozen_prefixes,
    compare_replay_records,
)
from tsc_rzip_rllib.core.gfile import parse_gfile, read_coil_currents_csv  # noqa: E402
from tsc_rzip_rllib.core.runner import TSCConfig, TSCStepRunner  # noqa: E402


DEFAULT_CONFIG = REPO_ROOT / "stage1_1_runs" / "stage1_1_svd234_strict_validation_100ms_20260718_025916" / "env_config.resolved.json"
ARTIFACT_NAMES = ("geqdsk", "coil_currents.csv", "wire_currents.csv", "sprsina")
ROLLOUT_ORDER = (
    ("hold_primary", "hold"),
    ("hold_replay", "hold"),
    ("pulse_primary", "pulse"),
    ("pulse_replay", "pulse"),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dump(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_source_state(cfg: TSCConfig) -> dict[str, Any]:
    folder = cfg.simulation_root / cfg.start_folder
    gfile = parse_gfile(folder / "geqdsk")
    currents_kat = read_coil_currents_csv(folder / "coil_currents.csv")
    currents_a = TSCStepRunner.current_kat_to_a(currents_kat, cfg.turns_tsc)
    return {
        "folder": folder,
        "time_ms": int(cfg.start_folder.rstrip("ms")),
        "Ip": float(gfile["ip"]),
        "gfile": gfile,
        "currents_kat_tsc": currents_kat,
        "currents_a_tsc": currents_a,
        "abnormal": False,
    }


def _validate_prefix_targets(cfg: TSCConfig, prefixes: dict[str, Any], initial: Sequence[float]) -> dict[str, Any]:
    current = np.asarray(initial, dtype=float)
    rows: list[dict[str, Any]] = []
    accepted = True
    for prefix_name in ("hold", "pulse"):
        current = np.asarray(initial, dtype=float)
        for index, target in enumerate(prefixes[prefix_name].targets):
            target_a = np.asarray(target.quantized_current_a_tsc, dtype=float)
            reasons: list[str] = []
            if np.any(target_a < cfg.min_current_a_tsc - 1e-9) or np.any(target_a > cfg.max_current_a_tsc + 1e-9):
                reasons.append("TARGET_CURRENT_LIMIT")
            maximum_delta = float(np.max(np.abs(target_a - current)))
            if maximum_delta > cfg.max_delta_current_a_per_step + 1e-9:
                reasons.append("TARGET_SLEW_LIMIT")
            rows.append(
                {
                    "prefix": prefix_name,
                    "step_index": index,
                    "maximum_increment_a": maximum_delta,
                    "reasons": reasons,
                    "serialized_card15_fields": list(target.serialized_card15_fields),
                    "quantized_target_current_a_tsc": list(target.quantized_current_a_tsc),
                }
            )
            accepted = accepted and not reasons
            current = target_a
    return {"passed": bool(accepted), "rows": rows}


def offline_preflight(config_path: Path, source_revision: str) -> dict[str, Any]:
    cfg = TSCConfig.from_json(config_path)
    source = _read_source_state(cfg)
    signal = RGeoZGeoSignal.from_tsc_state(source)
    envelope = NR1SafetyEnvelope.from_source_signal(signal)
    prefixes = build_frozen_prefixes(
        initial_current_a_tsc=source["currents_a_tsc"],
        turns_tsc=cfg.turns_tsc,
        max_delta_current_a_per_step=cfg.max_delta_current_a_per_step,
    )
    source_reasons = envelope.state_reasons(
        signal=signal,
        actual_current_a_tsc=source["currents_a_tsc"],
        min_current_a_tsc=cfg.min_current_a_tsc,
        max_current_a_tsc=cfg.max_current_a_tsc,
    )
    target_gate = _validate_prefix_targets(cfg, prefixes, source["currents_a_tsc"])
    identity = DataIdentity(
        campaign_id="rgeo_zgeo_nr1_fixed_prefix_replay_v1",
        intended_use=NR1_INTENDED_USE,
        declared_before_collection=True,
        source_revision=source_revision,
    )
    passed = not source_reasons and target_gate["passed"] and cfg.start_folder == "1100ms" and cfg.dt_ms == 10
    return {
        "schema_version": NR1_CONTRACT_VERSION,
        "kind": "offline_preflight",
        "created_utc": _utc_now(),
        "identity": identity.to_dict(),
        "passed": bool(passed),
        "route": "NR1_OFFLINE_GATE_PASS" if passed else "NR1_OFFLINE_GATE_FAIL_NO_TSC",
        "config_path": str(config_path),
        "fixed_contract": {
            "start_folder": cfg.start_folder,
            "dt_ms": cfg.dt_ms,
            "horizon_steps": NR1_HORIZON_STEPS,
            "rollout_count": len(ROLLOUT_ORDER),
            "authorized_plant_advances": len(ROLLOUT_ORDER) * NR1_HORIZON_STEPS,
            "max_delta_current_a_per_step": cfg.max_delta_current_a_per_step,
        },
        "source_signal": signal.to_dict(),
        "source_state_reasons": list(source_reasons),
        "safety_envelope": envelope.to_dict(),
        "target_gate": target_gate,
        "prefixes": {key: value.to_dict() for key, value in prefixes.items()},
    }


def _read_wire_current_a(path: Path, column_name: str, raw_to_a: float) -> list[float]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, skipinitialspace=True)
        if reader.fieldnames is None:
            raise ContractError("wire current CSV has no header")
        normalized = {str(name).strip(): name for name in reader.fieldnames}
        if column_name not in normalized:
            raise ContractError(f"wire current CSV is missing {column_name!r}")
        original = normalized[column_name]
        values = [float(row[original]) * raw_to_a for row in reader if str(row.get(original, "")).strip()]
    if not values or not np.all(np.isfinite(values)):
        raise ContractError("wire current vector must be nonempty and finite")
    return [float(value) for value in values]


def _state_record(
    cfg: TSCConfig,
    state: dict[str, Any],
    target_fields: Sequence[str],
) -> dict[str, Any]:
    signal = RGeoZGeoSignal.from_tsc_state(state)
    folder = Path(state["folder"])
    hashes: dict[str, str] = {}
    for name in ARTIFACT_NAMES:
        path = folder / name
        if not path.is_file():
            raise ContractError(f"required NR1 state artifact is missing: {path}")
        hashes[name] = artifact_sha256(path)
    return {
        "time_ms": int(state["time_ms"]),
        "r_geo_m": signal.boundary.r_geo_m,
        "z_geo_m": signal.boundary.z_geo_m,
        "r_mid_m": signal.limiter.r_mid_m,
        "side": signal.side,
        "ip_a": signal.ip_a,
        "boundary": signal.boundary.to_dict(),
        "limiter": signal.limiter.to_dict(),
        "actual_current_a_tsc": [float(value) for value in state["currents_a_tsc"]],
        "wire_current_a": _read_wire_current_a(
            folder / "wire_currents.csv", cfg.vessel_current_column, cfg.vessel_current_raw_to_a
        ),
        "target_card15_fields": list(target_fields),
        "artifact_sha256": hashes,
        "runner_timing": {key: float(value) for key, value in state.get("runner_timing", {}).items()},
    }


def _run_one(
    *,
    cfg: TSCConfig,
    rollout_name: str,
    prefix: Any,
    envelope: NR1SafetyEnvelope,
) -> dict[str, Any]:
    runner = TSCStepRunner(cfg, worker_id=f"nr1_{rollout_name}", keep_workspace=False)
    started = time.perf_counter()
    states: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    reasons: list[str] = []
    try:
        state = runner.reset(episode_name=rollout_name)
        for step_index, target in enumerate(prefix.targets):
            target_fields = target.serialized_card15_fields
            try:
                signal = RGeoZGeoSignal.from_tsc_state(state)
                reasons.extend(
                    envelope.state_reasons(
                        signal=signal,
                        actual_current_a_tsc=state["currents_a_tsc"],
                        min_current_a_tsc=cfg.min_current_a_tsc,
                        max_current_a_tsc=cfg.max_current_a_tsc,
                    )
                )
                reasons.extend(
                    envelope.target_reasons(
                        actual_current_a_tsc=state["currents_a_tsc"],
                        target_current_a_tsc=target.quantized_current_a_tsc,
                        min_current_a_tsc=cfg.min_current_a_tsc,
                        max_current_a_tsc=cfg.max_current_a_tsc,
                        max_delta_current_a_per_step=cfg.max_delta_current_a_per_step,
                    )
                )
                states.append(_state_record(cfg, state, target_fields))
            except (ContractError, OSError, ValueError) as exc:
                reasons.append(f"PRESTEP_CONTRACT:{type(exc).__name__}:{exc}")
            if reasons:
                break
            actions.append(
                {
                    "issue_step": step_index,
                    "issue_time_ms": int(state["time_ms"]),
                    "target": target.to_dict(),
                }
            )
            state = runner.step_current_a(np.asarray(target.quantized_current_a_tsc, dtype=float))
            if state.get("returncode", 0) != 0:
                reasons.append(f"TSC_RETURNCODE:{state.get('returncode')}")
            if bool(state.get("abnormal", False)):
                reasons.append(f"TSC_ABNORMAL:{state.get('done_reason', '')}")
            try:
                successor_signal = RGeoZGeoSignal.from_tsc_state(state)
                reasons.extend(
                    envelope.state_reasons(
                        signal=successor_signal,
                        actual_current_a_tsc=state["currents_a_tsc"],
                        min_current_a_tsc=cfg.min_current_a_tsc,
                        max_current_a_tsc=cfg.max_current_a_tsc,
                    )
                )
            except (ContractError, ValueError) as exc:
                reasons.append(f"POSTSTEP_CONTRACT:{type(exc).__name__}:{exc}")
            if reasons:
                try:
                    states.append(_state_record(cfg, state, ()))
                except (ContractError, OSError, ValueError) as exc:
                    reasons.append(f"FAILED_STATE_RECORD:{type(exc).__name__}:{exc}")
                break
        else:
            states.append(_state_record(cfg, state, ()))
    except Exception as exc:
        reasons.append(f"EXECUTION_EXCEPTION:{type(exc).__name__}:{exc}")
    finally:
        runner.cleanup_runtime_workspace()
    unique_reasons = list(dict.fromkeys(reasons))
    return {
        "rollout_name": rollout_name,
        "prefix_name": prefix.name,
        "passed": not unique_reasons and len(actions) == NR1_HORIZON_STEPS and len(states) == NR1_HORIZON_STEPS + 1,
        "reasons": unique_reasons,
        "plant_advances": len(actions),
        "wall_time_s": time.perf_counter() - started,
        "actions": actions,
        "states": states,
    }


def run_campaign(config_path: Path, source_revision: str, output_dir: Path) -> dict[str, Any]:
    preflight = offline_preflight(config_path, source_revision)
    if not preflight["passed"]:
        raise RuntimeError("NR1 offline gate did not pass; real TSC is forbidden")
    cfg = TSCConfig.from_json(config_path)
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"NR1 output directory already exists: {output_dir}")
    output_dir.mkdir(parents=True)
    _json_dump(output_dir / "offline_preflight.json", preflight)
    cfg = replace(
        cfg,
        run_root=output_dir / "rollouts",
        runtime_only_fast_mode=False,
        save_step_artifacts=False,
        save_artifacts_every_n_steps=0,
        keep_episode_restart_files=True,
        cleanup_episode_dir=False,
        keep_failed_episode_dir=True,
        keep_last_n_failed_episode_dirs=4,
    )
    source = _read_source_state(cfg)
    signal = RGeoZGeoSignal.from_tsc_state(source)
    envelope = NR1SafetyEnvelope.from_source_signal(signal)
    prefixes = build_frozen_prefixes(
        initial_current_a_tsc=source["currents_a_tsc"],
        turns_tsc=cfg.turns_tsc,
        max_delta_current_a_per_step=cfg.max_delta_current_a_per_step,
    )
    rollouts: dict[str, Any] = {}
    safety_stop = False
    for rollout_name, prefix_name in ROLLOUT_ORDER:
        if safety_stop:
            break
        result = _run_one(
            cfg=cfg,
            rollout_name=rollout_name,
            prefix=prefixes[prefix_name],
            envelope=envelope,
        )
        rollouts[rollout_name] = result
        _json_dump(output_dir / f"{rollout_name}.json", result)
        if not result["passed"]:
            safety_stop = True
    comparisons: dict[str, Any] = {}
    for prefix_name in ("hold", "pulse"):
        primary = rollouts.get(f"{prefix_name}_primary")
        replay = rollouts.get(f"{prefix_name}_replay")
        if primary is not None and replay is not None and primary["passed"] and replay["passed"]:
            comparisons[prefix_name] = compare_replay_records(primary["states"], replay["states"])
    expected = {name for name, _ in ROLLOUT_ORDER}
    all_rollouts_pass = set(rollouts) == expected and all(value["passed"] for value in rollouts.values())
    all_replays_pass = set(comparisons) == {"hold", "pulse"} and all(
        value["passed"] for value in comparisons.values()
    )
    passed = all_rollouts_pass and all_replays_pass
    final = {
        "schema_version": NR1_CONTRACT_VERSION,
        "kind": "real_tsc_qualification",
        "created_utc": _utc_now(),
        "identity": preflight["identity"],
        "passed": bool(passed),
        "route": "FIXED_1100MS_PREFIX_REPLAY_QUALIFIED" if passed else (
            "NR1_SAFETY_FAIL_STOP" if safety_stop else "PREFIX_REPLAY_NOT_QUALIFIED"
        ),
        "output_dir": str(output_dir),
        "rollout_names": list(rollouts),
        "plant_advances": sum(int(value["plant_advances"]) for value in rollouts.values()),
        "rollout_pass_count": sum(bool(value["passed"]) for value in rollouts.values()),
        "replay_comparisons": comparisons,
        "wall_time_s": sum(float(value["wall_time_s"]) for value in rollouts.values()),
        "claim_boundary": "fixed 1100ms exact-prefix replay only; not arbitrary-state Oracle or control",
    }
    _json_dump(output_dir / "qualification.json", final)
    return final


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("offline", "run"))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.mode == "offline":
        result = offline_preflight(args.config.resolve(), args.source_revision)
        if args.output is not None:
            _json_dump(args.output.resolve(), result)
    else:
        if args.output is None:
            parser.error("run mode requires --output")
        result = run_campaign(args.config.resolve(), args.source_revision, args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
