#!/usr/bin/env python3
"""Offline gate and six-rollout authentic 1 ms NR1 qualification."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    NR1_1MS_CAMPAIGN_ID,
    NR1_1MS_CONTRACT_VERSION,
    NR1_1MS_HORIZON_STEPS,
    NR1_1MS_INTENDED_USE,
    NR1_1MS_ROLLOUTS,
    OneMsNR1SafetyEnvelope,
    RETURN_EQUIVALENCE_A,
    assert_exact_slew,
    build_frozen_one_ms_prefixes,
    card15_target_decimal_a,
    decimal_single_turn_currents_a,
    validate_one_ms_config,
)
from tsc_rzip_rllib.control.rgeo_zgeo_contract import ContractError, DataIdentity, RGeoZGeoSignal  # noqa: E402
from tsc_rzip_rllib.core.gfile import parse_gfile, read_coil_currents_csv  # noqa: E402
from tsc_rzip_rllib.core.runner import TSCConfig, TSCStepRunner  # noqa: E402

DEFAULT_CONFIG = ROOT / "configs" / "rgeo_zgeo_1ms_nr1_safety_effect.json"
ARTIFACTS = ("inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv", "sprsina")


def _profile(config_path: Path) -> dict[str, Any]:
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    row = payload.get("qualification_identity")
    if row is None:
        return {
            "takeover_time_ms": 1100,
            "contract_version": NR1_1MS_CONTRACT_VERSION,
            "campaign_id": NR1_1MS_CAMPAIGN_ID,
            "intended_use": NR1_1MS_INTENDED_USE,
            "route_prefix": "ONE_MS_NR1R2",
            "matched_hold_effect": False,
        }
    expected = {
        "takeover_time_ms", "contract_version", "campaign_id",
        "intended_use", "route_prefix",
    }
    if set(row) != expected:
        raise ContractError("qualification_identity fields changed")
    takeover = int(row["takeover_time_ms"])
    if takeover < 0 or payload.get("start_folder") != f"{takeover}ms":
        raise ContractError("qualification identity/start_folder mismatch")
    contract = payload.get("source_command_contract")
    expected_contract = {
        "command_center": "active_source_card15",
        "effect_evaluation": "matched_hold_state1_differential",
        "return_evaluation": "exact_card15_command_center",
    }
    if contract != expected_contract:
        raise ContractError("source command contract changed")
    return {**row, "matched_hold_effect": True}


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source(cfg: TSCConfig) -> dict[str, Any]:
    folder = cfg.simulation_root / cfg.start_folder
    missing = [name for name in ARTIFACTS if not (folder / name).is_file()]
    if missing:
        raise ContractError(f"source is missing required artifacts: {missing}")
    gfile = parse_gfile(folder / "geqdsk")
    kat = read_coil_currents_csv(folder / "coil_currents.csv")
    current = TSCStepRunner.current_kat_to_a(kat, cfg.turns_tsc)
    exact = _exact_coil_currents_a(folder / "coil_currents.csv", cfg)
    command_fields = _card15_fields(folder / "inputa")
    command_exact = decimal_single_turn_currents_a(
        tuple(value.strip() for value in command_fields), cfg.turns_tsc,
        name=f"{folder / 'inputa'}.active_command",
    )
    time_ms = int(cfg.start_folder.removesuffix("ms"))
    return {"folder": folder, "time_ms": time_ms, "Ip": float(gfile["ip"]), "gfile": gfile,
            "currents_a_tsc": current, "currents_decimal_a_tsc": exact,
            "currents_kat_tsc": kat, "active_command_card15_fields": command_fields,
            "active_command_decimal_a_tsc": command_exact, "abnormal": False}


def _card15_fields(path: Path) -> tuple[str, ...]:
    values = tuple(
        line[30:40]
        for line in path.read_text(encoding="utf-8").splitlines()
        if line[:10].strip() == "15"
    )
    if len(values) != 14:
        raise ContractError(f"expected fourteen Card15 rows in {path}, got {len(values)}")
    return values


def _exact_coil_currents_a(path: Path, cfg: TSCConfig) -> tuple[Any, ...]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, skipinitialspace=True)
        field = next((value for value in (reader.fieldnames or []) if "ccoil" in value.lower()), None)
        if field is None:
            raise ContractError("ccoil column is missing")
        values = tuple(row[field].strip() for row in reader)
    return decimal_single_turn_currents_a(values, cfg.turns_tsc, name=str(path))


def offline_preflight(config_path: Path, source_revision: str) -> dict[str, Any]:
    cfg = TSCConfig.from_json(config_path)
    profile = _profile(config_path)
    config_payload = json.loads(config_path.read_text(encoding="utf-8"))
    source_identity = config_payload.get("source_identity")
    failures: list[str] = []
    source_evidence: dict[str, Any] = {}
    try:
        validate_one_ms_config(start_folder=cfg.start_folder, dt_ms=cfg.dt_ms,
                               slew_a_per_ms=cfg.current_slew_a_per_ms,
                               expected_start_folder=f"{profile['takeover_time_ms']}ms")
        source = _source(cfg)
        signal = RGeoZGeoSignal.from_tsc_state(source)
        if source_identity is not None:
            files = source_identity.get("files", {})
            if set(files) != {"inputa", "geqdsk", "coil_currents.csv",
                              "wire_currents.csv", "sprsina", "outputa"}:
                raise ContractError("source identity file set changed")
            source_evidence["files"] = {}
            for name, expected in files.items():
                item = source["folder"] / name
                actual = {"sha256": _sha(item), "bytes": item.stat().st_size}
                source_evidence["files"][name] = actual
                if actual != expected:
                    raise ContractError(f"source identity mismatch: {name}")
            expected_state = source_identity.get("expected_state", {})
            actual_state = {
                "time_ms": signal.boundary.time_ms,
                "point_count": signal.boundary.point_count,
                "r_geo_m": signal.boundary.r_geo_m,
                "z_geo_m": signal.boundary.z_geo_m,
                "r_boundary_min_m": signal.boundary.r_boundary_min_m,
                "r_boundary_max_m": signal.boundary.r_boundary_max_m,
                "z_boundary_min_m": signal.boundary.z_boundary_min_m,
                "z_boundary_max_m": signal.boundary.z_boundary_max_m,
                "ip_a": signal.ip_a,
                "wire_count": len(_wire(source["folder"] / "wire_currents.csv", cfg)),
            }
            source_evidence["state"] = actual_state
            for key, expected in expected_state.items():
                actual = actual_state.get(key)
                if actual is None or abs(float(actual) - float(expected)) > 1e-12:
                    raise ContractError(f"source state mismatch: {key}")
        frozen = build_frozen_one_ms_prefixes(
            source_current_a_tsc=source["currents_a_tsc"], turns_tsc=cfg.turns_tsc,
            source_command_a_tsc=(source["active_command_decimal_a_tsc"]
                                  if profile["matched_hold_effect"] else None),
            min_current_a_tsc=cfg.min_current_a_tsc, max_current_a_tsc=cfg.max_current_a_tsc,
        )
        envelope = OneMsNR1SafetyEnvelope.from_signal(signal)
        failures.extend(envelope.state_reasons(signal, source["currents_a_tsc"],
                                                cfg.min_current_a_tsc, cfg.max_current_a_tsc))
        maxima = {}
        for prefix_name, targets in frozen.prefixes.items():
            current = source["active_command_decimal_a_tsc"]
            local = []
            for target in targets:
                target_decimal = card15_target_decimal_a(target, cfg.turns_tsc, name=prefix_name)
                local.append(assert_exact_slew(current, target_decimal, name=prefix_name))
                current = target_decimal
            maxima[prefix_name] = max(local)
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
        source = None
        signal = None
        frozen = None
        maxima = {}
    identity = DataIdentity(campaign_id=profile["campaign_id"], intended_use=profile["intended_use"],
                            declared_before_collection=True, source_revision=source_revision)
    passed = not failures
    return {
        "schema_version": profile["contract_version"], "kind": "offline_preflight",
        "created_utc": datetime.now(timezone.utc).isoformat(), "identity": identity.to_dict(),
        "passed": passed, "route": f"{profile['route_prefix']}_OFFLINE_PASS" if passed else f"{profile['route_prefix']}_OFFLINE_FAIL_NO_TSC",
        "failures": list(dict.fromkeys(failures)), "config_path": str(config_path),
        "fixed_contract": {"start_folder": cfg.start_folder, "dt_ms": cfg.dt_ms,
                           "takeover_time_ms": profile["takeover_time_ms"],
                           "current_slew_a_per_ms": cfg.current_slew_a_per_ms,
                           "max_delta_current_a_per_step": cfg.max_delta_current_a_per_step,
                           "rollouts": len(NR1_1MS_ROLLOUTS), "steps_per_rollout": NR1_1MS_HORIZON_STEPS,
                           "authorized_plant_advances": len(NR1_1MS_ROLLOUTS) * NR1_1MS_HORIZON_STEPS},
        "source_signal": None if signal is None else signal.to_dict(),
        "source_evidence": source_evidence,
        "maximum_target_step_a": maxima,
        "frozen_prefixes": None if frozen is None else frozen.to_dict(),
    }


def _wire(path: Path, cfg: TSCConfig) -> list[float]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, skipinitialspace=True)
        fields = {str(name).strip(): name for name in (reader.fieldnames or [])}
        original = fields.get(cfg.vessel_current_column)
        if original is None:
            raise ContractError("wire current column is missing")
        values = [float(row[original]) * cfg.vessel_current_raw_to_a for row in reader if str(row[original]).strip()]
    if not values or not np.all(np.isfinite(values)):
        raise ContractError("wire current vector is invalid")
    return values


def _record(cfg: TSCConfig, state: dict[str, Any]) -> dict[str, Any]:
    signal = RGeoZGeoSignal.from_tsc_state(state)
    folder = Path(state["folder"])
    missing = [name for name in ARTIFACTS if not (folder / name).is_file()]
    if missing:
        raise ContractError(f"state artifacts missing: {missing}")
    exact_current = _exact_coil_currents_a(folder / "coil_currents.csv", cfg)
    active_fields = _card15_fields(folder / "inputa")
    active_command = decimal_single_turn_currents_a(
        tuple(value.strip() for value in active_fields), cfg.turns_tsc,
        name=f"{folder / 'inputa'}.active_command",
    )
    return {"time_ms": int(state["time_ms"]), "r_geo_m": signal.boundary.r_geo_m,
            "z_geo_m": signal.boundary.z_geo_m, "r_mid_m": signal.limiter.r_mid_m,
            "r_inner_m": signal.limiter.r_inner_m, "r_outer_m": signal.limiter.r_outer_m,
            "side": signal.side, "ip_a": signal.ip_a,
            "actual_current_a_tsc": [float(v) for v in state["currents_a_tsc"]],
            "actual_current_decimal_a_tsc": [str(v) for v in exact_current],
            "active_command_card15_fields": list(active_fields),
            "active_command_decimal_a_tsc": [str(v) for v in active_command],
            "wire_current_a": _wire(folder / "wire_currents.csv", cfg),
            "artifact_sha256": {name: _sha(folder / name) for name in ARTIFACTS}}


def _run_one(cfg: TSCConfig, name: str, prefix_name: str, targets: Sequence[Any],
             envelope: OneMsNR1SafetyEnvelope, *, matched_hold_effect: bool = False) -> dict[str, Any]:
    runner = TSCStepRunner(cfg, worker_id=f"one_ms_nr1_{name}", keep_workspace=False)
    reasons: list[str] = []
    records: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    started = time.perf_counter()
    try:
        state = runner.reset(episode_name=name)
        records.append(_record(cfg, state))
        takeover_time_ms = records[0]["time_ms"]
        source_current = tuple(records[0]["actual_current_decimal_a_tsc"])
        source_command = tuple(Decimal(value) for value in records[0]["active_command_decimal_a_tsc"])
        for step, target in enumerate(targets):
            signal = RGeoZGeoSignal.from_tsc_state(state)
            reasons.extend(envelope.state_reasons(signal, state["currents_a_tsc"],
                                                   cfg.min_current_a_tsc, cfg.max_current_a_tsc))
            try:
                target_decimal = card15_target_decimal_a(
                    target, cfg.turns_tsc, name=f"{name}.target.{step}"
                )
                maximum = assert_exact_slew(records[-1]["active_command_decimal_a_tsc"], target_decimal,
                                            name=f"{name}.issued.{step}")
            except ContractError as exc:
                reasons.append(f"ISSUED_SLEW:{exc}")
                break
            if reasons:
                break
            actions.append({"issue_step": step, "issue_time_ms": int(state["time_ms"]),
                            "expected_card15_fields": list(target.card15_fields),
                            "target_current_a_tsc": list(target.current_a_tsc),
                            "maximum_issued_delta_a": maximum})
            state = runner.step_current_a(np.asarray(target.current_a_tsc, dtype=float))
            if int(state.get("returncode", 0)) != 0:
                reasons.append(f"TSC_RETURNCODE:{state.get('returncode')}")
            if bool(state.get("abnormal", False)):
                reasons.append(f"TSC_ABNORMAL:{state.get('done_reason', '')}")
            record = _record(cfg, state)
            records.append(record)
            if tuple(record["active_command_card15_fields"]) != target.card15_fields:
                reasons.append(f"CARD15:{step}")
            if record["time_ms"] != takeover_time_ms + step + 1:
                reasons.append(f"TIME:{step}")
            try:
                record["maximum_observed_delta_a"] = assert_exact_slew(
                    records[-2]["actual_current_decimal_a_tsc"],
                    record["actual_current_decimal_a_tsc"],
                    name=f"{name}.observed.{step}")
            except ContractError as exc:
                reasons.append(f"OBSERVED_SLEW:{exc}")
            reasons.extend(envelope.state_reasons(RGeoZGeoSignal.from_tsc_state(state),
                                                   state["currents_a_tsc"], cfg.min_current_a_tsc,
                                                   cfg.max_current_a_tsc))
            if step == 0 and prefix_name != "hold" and not matched_hold_effect:
                effect = tuple(Decimal(value) - Decimal(base) for value, base in zip(
                    record["actual_current_decimal_a_tsc"], source_current
                ))
                requested = tuple(value - Decimal(base) for value, base in zip(
                    target_decimal, source_command
                ))
                if any(value == 0 for value in effect) or any(
                    (value > 0) != (wanted > 0) for value, wanted in zip(effect, requested)
                ):
                    reasons.append("FIRST_EFFECT_SIGN")
            if step >= 1 and prefix_name != "hold" and not matched_hold_effect:
                if max(abs(Decimal(a) - Decimal(b)) for a, b in zip(
                    record["actual_current_decimal_a_tsc"], source_current
                )) > RETURN_EQUIVALENCE_A:
                    reasons.append(f"CENTER_RETURN:{step}")
            if reasons:
                break
    except Exception as exc:
        reasons.append(f"EXECUTION:{type(exc).__name__}:{exc}")
    finally:
        runner.cleanup_runtime_workspace()
    reasons = list(dict.fromkeys(reasons))
    return {"rollout_name": name, "prefix_name": prefix_name, "passed": not reasons and len(actions) == 4 and len(records) == 5,
            "reasons": reasons, "plant_advances": len(actions), "states": records, "actions": actions,
            "wall_time_s": time.perf_counter() - started}


def _replay(left: Sequence[dict[str, Any]], right: Sequence[dict[str, Any]]) -> dict[str, Any]:
    maxima = {"geometry_m": 0.0, "ip_a": 0.0, "coil_a": 0.0, "wire_a": 0.0}
    failures = []
    if len(left) != 5 or len(right) != 5:
        failures.append("STATE_COUNT")
    for index, (a, b) in enumerate(zip(left, right)):
        if a["time_ms"] != b["time_ms"]:
            failures.append(f"TIME:{index}")
        maxima["geometry_m"] = max(maxima["geometry_m"], *(abs(a[k] - b[k]) for k in ("r_geo_m", "z_geo_m", "r_mid_m")))
        maxima["ip_a"] = max(maxima["ip_a"], abs(a["ip_a"] - b["ip_a"]))
        maxima["coil_a"] = max(maxima["coil_a"], max(abs(x-y) for x,y in zip(a["actual_current_a_tsc"], b["actual_current_a_tsc"])))
        maxima["wire_a"] = max(maxima["wire_a"], max(abs(x-y) for x,y in zip(a["wire_current_a"], b["wire_current_a"])))
    if maxima["geometry_m"] > 1e-12: failures.append("GEOMETRY")
    if maxima["ip_a"] > 1e-9: failures.append("IP")
    if maxima["coil_a"] > 1e-9: failures.append("COIL")
    if maxima["wire_a"] > 1e-9: failures.append("WIRE")
    return {"passed": not failures, "failures": failures, "maximum_absolute_difference": maxima}


def _matched_hold_effect(
    probe: Sequence[dict[str, Any]], hold: Sequence[dict[str, Any]],
    target: Any, source_command: Sequence[Decimal], turns_tsc: Sequence[float],
) -> dict[str, Any]:
    failures: list[str] = []
    if len(probe) != 5 or len(hold) != 5:
        return {"passed": False, "failures": ["STATE_COUNT"], "component_checks": 0}
    target_decimal = card15_target_decimal_a(target, turns_tsc, name="matched_effect.target")
    requested = tuple(value - base for value, base in zip(target_decimal, source_command))
    observed = tuple(
        Decimal(value) - Decimal(base)
        for value, base in zip(
            probe[1]["actual_current_decimal_a_tsc"],
            hold[1]["actual_current_decimal_a_tsc"],
        )
    )
    for index, (effect, wanted) in enumerate(zip(observed, requested)):
        if effect == 0 or wanted == 0 or (effect > 0) != (wanted > 0):
            failures.append(f"COMPONENT_SIGN:{index}")
    return {
        "passed": not failures,
        "failures": failures,
        "component_checks": len(observed),
        "requested_delta_a": [str(value) for value in requested],
        "matched_observed_delta_a": [str(value) for value in observed],
    }


def run(config_path: Path, source_revision: str, output_dir: Path) -> dict[str, Any]:
    profile = _profile(config_path)
    preflight = offline_preflight(config_path, source_revision)
    if not preflight["passed"]:
        raise RuntimeError("offline gate failed; TSC forbidden")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {output_dir}")
    output_dir.mkdir(parents=True)
    _dump(output_dir / "offline_preflight.json", preflight)
    cfg = TSCConfig.from_json(config_path)
    cfg.run_root = output_dir / "rollouts"
    source = _source(cfg)
    signal = RGeoZGeoSignal.from_tsc_state(source)
    envelope = OneMsNR1SafetyEnvelope.from_signal(signal)
    frozen = build_frozen_one_ms_prefixes(source_current_a_tsc=source["currents_a_tsc"], turns_tsc=cfg.turns_tsc,
                                          source_command_a_tsc=(source["active_command_decimal_a_tsc"]
                                                                if profile["matched_hold_effect"] else None),
                                          min_current_a_tsc=cfg.min_current_a_tsc, max_current_a_tsc=cfg.max_current_a_tsc)
    results = {}
    for name, prefix_name in NR1_1MS_ROLLOUTS:
        result = _run_one(cfg, name, prefix_name, frozen.prefixes[prefix_name], envelope,
                          matched_hold_effect=profile["matched_hold_effect"])
        results[name] = result
        _dump(output_dir / f"{name}.json", result)
        if not result["passed"]:
            break
    comparisons = {}
    for prefix in ("hold", "pattern_a", "pattern_b"):
        a, b = results.get(f"{prefix}_primary"), results.get(f"{prefix}_replay")
        if a and b:
            comparisons[prefix] = _replay(a["states"], b["states"])
    effect_comparisons = {}
    if profile["matched_hold_effect"]:
        source_command = tuple(Decimal(value) for value in source["active_command_decimal_a_tsc"])
        for prefix in ("pattern_a", "pattern_b"):
            for role in ("primary", "replay"):
                probe = results.get(f"{prefix}_{role}")
                hold = results.get(f"hold_{role}")
                if probe and hold:
                    effect_comparisons[f"{prefix}_{role}"] = _matched_hold_effect(
                        probe["states"], hold["states"], frozen.prefixes[prefix][0],
                        source_command, cfg.turns_tsc,
                    )
    all_pass = len(results) == 6 and all(row["passed"] for row in results.values())
    replay_pass = len(comparisons) == 3 and all(row["passed"] for row in comparisons.values())
    effect_pass = (not profile["matched_hold_effect"] or
                   len(effect_comparisons) == 4 and
                   all(row["passed"] for row in effect_comparisons.values()))
    passed = all_pass and replay_pass and effect_pass
    route = f"{profile['route_prefix']}_INTERFACE_QUALIFIED" if passed else (
        f"{profile['route_prefix']}_EFFECT_CONTRACT_FAIL_STOP" if (not effect_pass or any("EFFECT" in reason or "CENTER_RETURN" in reason for row in results.values() for reason in row["reasons"]))
        else f"{profile['route_prefix']}_SAFETY_FAIL_STOP" if not all_pass else f"{profile['route_prefix']}_REPLAY_NOT_QUALIFIED")
    final = {"schema_version": profile["contract_version"], "kind": "authentic_qualification",
             "source_revision": source_revision, "passed": passed, "route": route,
             "takeover_time_ms": profile["takeover_time_ms"],
             "output_dir": str(output_dir), "rollout_count": len(results),
             "plant_advances": sum(row["plant_advances"] for row in results.values()),
             "comparisons": comparisons, "effect_comparisons": effect_comparisons,
             "claim_boundary": "1 ms fixed-source interface only; no model or control"}
    _dump(output_dir / "qualification.json", final)
    return final


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("offline", "run"))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = offline_preflight(args.config.resolve(), args.source_revision) if args.mode == "offline" else run(args.config.resolve(), args.source_revision, args.output.resolve())
    if args.mode == "offline": _dump(args.output.resolve(), result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
