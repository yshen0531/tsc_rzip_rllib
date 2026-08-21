#!/usr/bin/env python3
"""Fresh fixed-1000 multi-phase signed temporal-response campaign."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
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

from scripts import rgeo_zgeo_1ms_1000_baseline_b0 as b0  # noqa: E402
from scripts.rgeo_zgeo_1ms_nr1_qualification import _record, _source  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    OneMsNR1SafetyEnvelope,
    assert_exact_slew,
    build_frozen_one_ms_prefixes,
    card15_target_decimal_a,
    quantize_target,
    validate_one_ms_config,
)
from tsc_rzip_rllib.control.rgeo_zgeo_contract import ContractError, RGeoZGeoSignal  # noqa: E402
from tsc_rzip_rllib.core.runner import TSCConfig, TSCStepRunner  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-1000-signed-temporal-d0-v1"
CONFIG_SHA256 = "09b10b0a9db37decc02d71a4327ad4190405843674c3697d4c460a68b2780972"
DEFAULT_CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_signed_temporal_d0.json"
SEMANTIC_ARTIFACTS = b0.SEMANTIC_ARTIFACTS


class InputIntegrityError(ValueError):
    """Frozen stage, baseline or action identity changed."""


def load(config_path: Path) -> tuple[dict[str, Any], TSCConfig, dict[str, Any]]:
    config_path = b0.inside_root(config_path, "D0 config")
    if b0.sha256(config_path) != CONFIG_SHA256:
        raise InputIntegrityError("D0 config SHA-256 mismatch")
    stage = json.loads(config_path.read_text(encoding="utf-8"))
    exact = {
        "schema_version": SCHEMA,
        "campaign_id": "rgeo_zgeo_1ms_1000_signed_temporal_d0_v1",
        "takeover_time_ms": 1000,
        "control_period_ms": 1,
        "horizon_steps": 40,
        "issue_phases": [8, 10, 24],
        "pulse_duration_issues": 4,
        "tail_states_after_return": 12,
        "axes": ["even", "odd"],
        "signs": ["plus", "minus"],
        "primary_rollouts": 12,
        "critical_replays": ["p24_even_plus", "p24_odd_plus"],
        "rollouts": 14,
        "maximum_reset_calls": 14,
        "maximum_advance_attempts": 560,
        "maximum_gotsc_calls": 560,
        "maximum_verified_plant_advances": 560,
        "retry_after_any_advance_attempt": "forbidden",
        "requested_single_turn_amplitude_a": 0.15,
        "maximum_quantized_single_turn_amplitude_a": 0.151,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise InputIntegrityError(f"frozen field mismatch: {key}")
    expected_axis_signs = {
        "even": [1] * 14,
        "odd": [1, 1, 1, -1, -1, -1, 1, -1, 1, -1, 1, -1, 1, -1],
    }
    if stage.get("axis_signs_tsc_order") != expected_axis_signs:
        raise InputIntegrityError("axis signs changed")
    roles = stage.get("data_roles", {})
    if roles.get("critical_replays") != "integrity_only_zero_fit_weight" or any(
        roles.get(key) != "unopened" for key in ("calibration", "holdout")
    ) or roles.get("controller_or_recourse") != "forbidden":
        raise InputIntegrityError("data roles changed")
    base = b0.inside_root(ROOT / stage["base_tsc_config"], "base TSC config")
    if b0.sha256(base) != stage["base_tsc_config_sha256"]:
        raise InputIntegrityError("base TSC config hash mismatch")
    baseline_payloads: dict[str, Any] = {}
    for label, row in stage["baseline_evidence"].items():
        path = b0.inside_root(ROOT / row["path"], f"baseline {label}")
        if not path.is_file() or b0.sha256(path) != row["sha256"]:
            raise InputIntegrityError(f"baseline hash mismatch: {label}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if "route" in row and (payload.get("passed") is not True or payload.get("route") != row["route"]):
            raise InputIntegrityError(f"baseline route mismatch: {label}")
        baseline_payloads[label] = payload
    baseline = baseline_payloads["primary"]
    if not baseline.get("passed") or len(baseline.get("states", ())) != 65:
        raise InputIntegrityError("baseline primary is incomplete")
    if baseline.get("data_role") != "development_fit_eligible_baseline_weight_1":
        raise InputIntegrityError("baseline fit role changed")
    cfg = TSCConfig.from_json(base)
    validate_one_ms_config(
        start_folder=cfg.start_folder, dt_ms=cfg.dt_ms,
        slew_a_per_ms=cfg.current_slew_a_per_ms, expected_start_folder="1000ms",
    )
    return stage, cfg, baseline


def targets(stage: dict[str, Any], cfg: TSCConfig, source: dict[str, Any]) -> dict[str, Any]:
    frozen = build_frozen_one_ms_prefixes(
        source_current_a_tsc=source["currents_a_tsc"],
        source_command_a_tsc=source["active_command_decimal_a_tsc"],
        turns_tsc=cfg.turns_tsc,
        min_current_a_tsc=cfg.min_current_a_tsc,
        max_current_a_tsc=cfg.max_current_a_tsc,
        maximum_command_delta_a=Decimal("0.299"),
    )
    q0 = frozen.q0
    q0_decimal = card15_target_decimal_a(q0, cfg.turns_tsc, name="d0.q0")
    if tuple(q0_decimal) != tuple(source["active_command_decimal_a_tsc"]):
        raise ContractError("D0 q0 is not the semantic source command")
    amplitude = Decimal(str(stage["requested_single_turn_amplitude_a"]))
    limit = Decimal(str(stage["maximum_quantized_single_turn_amplitude_a"]))
    result: dict[str, Any] = {"q0": q0}
    deltas: list[list[float]] = []
    for axis in stage["axes"]:
        axis_signs = stage["axis_signs_tsc_order"][axis]
        for sign_name, polarity in (("plus", 1), ("minus", -1)):
            desired = [
                float(base + amplitude * axis_sign * polarity)
                for base, axis_sign in zip(q0_decimal, axis_signs)
            ]
            target = quantize_target(desired, cfg.turns_tsc)
            exact = card15_target_decimal_a(target, cfg.turns_tsc, name=f"d0.{axis}.{sign_name}")
            delta = [value - base for value, base in zip(exact, q0_decimal)]
            if any(value == 0 or (value > 0) != (axis_sign * polarity > 0)
                   for value, axis_sign in zip(delta, axis_signs)):
                raise ContractError(f"{axis}:{sign_name} lost a signed component")
            if max(abs(value) for value in delta) > limit:
                raise ContractError(f"{axis}:{sign_name} exceeds quantized amplitude")
            assert_exact_slew(q0_decimal, exact, name=f"d0.q0_to_{axis}_{sign_name}")
            if any(value < Decimal(str(low)) or value > Decimal(str(high))
                   for value, low, high in zip(exact, cfg.min_current_a_tsc, cfg.max_current_a_tsc)):
                raise ContractError(f"{axis}:{sign_name} exceeds absolute current limits")
            result[f"{axis}_{sign_name}"] = target
            deltas.append([float(value) for value in delta])
    matrix = np.asarray(deltas, dtype=float).T
    if np.linalg.matrix_rank(matrix) != 2:
        raise ContractError("D0 executed action matrix is not rank two")
    result["action_geometry"] = {
        "rank": 2,
        "singular_values_a": np.linalg.svd(matrix, compute_uv=False).tolist(),
        "maximum_absolute_delta_a": float(np.max(np.abs(matrix))),
    }
    return result


def rollout_specs(stage: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for phase in stage["issue_phases"]:
        for axis in stage["axes"]:
            for sign in stage["signs"]:
                base = f"p{phase:02d}_{axis}_{sign}"
                rows.append({
                    "rollout_id": base,
                    "family_id": base,
                    "issue_phase": phase,
                    "axis": axis,
                    "sign": sign,
                    "repeat_index": 0,
                    "data_role": "development_fit_eligible_weight_1",
                })
    for base in stage["critical_replays"]:
        phase_text, axis, sign = base.split("_")
        rows.append({
            "rollout_id": f"{base}_replay",
            "family_id": base,
            "issue_phase": int(phase_text[1:]),
            "axis": axis,
            "sign": sign,
            "repeat_index": 1,
            "data_role": "integrity_only_zero_fit_weight",
        })
    if len(rows) != stage["rollouts"] or len({row["rollout_id"] for row in rows}) != len(rows):
        raise InputIntegrityError("rollout matrix changed")
    return rows


def sequence_for(spec: dict[str, Any], stage: dict[str, Any], target_map: dict[str, Any]) -> list[Any]:
    sequence = [target_map["q0"]] * stage["horizon_steps"]
    start = spec["issue_phase"]
    end = start + stage["pulse_duration_issues"]
    for issue in range(start, end):
        sequence[issue] = target_map[f"{spec['axis']}_{spec['sign']}"]
    return sequence


def action_stream(
    spec: dict[str, Any], stage: dict[str, Any], cfg: TSCConfig,
    source: dict[str, Any], target_map: dict[str, Any],
) -> list[dict[str, Any]]:
    previous = tuple(source["active_command_decimal_a_tsc"])
    rows = []
    for issue, target in enumerate(sequence_for(spec, stage, target_map)):
        exact = card15_target_decimal_a(target, cfg.turns_tsc, name=f"d0.{spec['rollout_id']}.{issue}")
        maximum = assert_exact_slew(previous, exact, name=f"d0.{spec['rollout_id']}.{issue}")
        rows.append({
            "issue_step": issue,
            "issue_time_ms": 1000 + issue,
            "effect_state_index": issue + 1,
            "effect_time_ms": 1001 + issue,
            "expected_card15_fields": list(target.card15_fields),
            "maximum_issued_delta_a": maximum,
        })
        previous = exact
    return rows


def offline(config_path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    streams = None
    geometry = None
    try:
        stage, cfg, _ = load(config_path)
        source = _source(cfg)
        envelope = OneMsNR1SafetyEnvelope.from_signal(RGeoZGeoSignal.from_tsc_state(source))
        failures.extend(envelope.state_reasons(
            RGeoZGeoSignal.from_tsc_state(source), source["currents_a_tsc"],
            cfg.min_current_a_tsc, cfg.max_current_a_tsc,
        ))
        target_map = targets(stage, cfg, source)
        geometry = target_map["action_geometry"]
        streams = [
            {**spec, "actions": action_stream(spec, stage, cfg, source, target_map)}
            for spec in rollout_specs(stage)
        ]
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
            "offline_fail", "ONE_MS_NR1000D0_OFFLINE_FAIL_NO_TSC"
        ),
        "failures": failures,
        "authorized_reset_calls": 14,
        "authorized_plant_advances": 560,
        "action_geometry": geometry,
        "rollout_action_streams": streams,
    }


def _run_one(
    cfg: TSCConfig, stage: dict[str, Any], spec: dict[str, Any],
    targets_for_rollout: Sequence[Any], envelope: OneMsNR1SafetyEnvelope,
    source_reference: dict[str, Any],
) -> dict[str, Any]:
    runner = TSCStepRunner(cfg, worker_id=f"nr1000_d0_{spec['rollout_id']}", keep_workspace=False)
    reasons: list[str] = []
    states: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    attempts = gotsc_calls = verified = reset_calls = 0
    started = time.perf_counter()
    try:
        reset_calls = 1
        live = runner.reset(episode_name=spec["rollout_id"])
        states.append(_record(cfg, live))
        reasons.extend(source_mismatch_reasons(states[0], source_reference))
        origin_time = states[0]["time_ms"]
        for issue, target in enumerate(targets_for_rollout):
            reasons.extend(envelope.state_reasons(
                RGeoZGeoSignal.from_tsc_state(live), live["currents_a_tsc"],
                cfg.min_current_a_tsc, cfg.max_current_a_tsc,
            ))
            exact = card15_target_decimal_a(target, cfg.turns_tsc, name=f"{spec['rollout_id']}.{issue}")
            maximum = assert_exact_slew(
                states[-1]["active_command_decimal_a_tsc"], exact,
                name=f"{spec['rollout_id']}.issued.{issue}",
            )
            if reasons:
                break
            actions.append({
                "issue_step": issue,
                "issue_time_ms": int(live["time_ms"]),
                "effect_state_index": issue + 1,
                "effect_time_ms": origin_time + issue + 1,
                "expected_card15_fields": list(target.card15_fields),
                "maximum_issued_delta_a": maximum,
            })
            attempts += 1
            live = runner.step_current_a(np.asarray(target.current_a_tsc, dtype=float))
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
            if tuple(record["active_command_card15_fields"]) != tuple(target.card15_fields):
                reasons.append(f"CARD15:{issue}")
            if issue == 0:
                record["observed_delta_role"] = "source_bias_descriptive_matched_hold_reference"
            else:
                record["maximum_observed_delta_a"] = assert_exact_slew(
                    states[-2]["actual_current_decimal_a_tsc"],
                    record["actual_current_decimal_a_tsc"],
                    name=f"{spec['rollout_id']}.observed.{issue}",
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
        **spec,
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


def source_mismatch_reasons(
    actual: dict[str, Any], expected: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    for key, tolerance in (
        ("r_geo_m", 1e-12), ("z_geo_m", 1e-12), ("r_mid_m", 1e-12), ("ip_a", 1e-9),
    ):
        if abs(float(actual[key]) - float(expected[key])) > tolerance:
            reasons.append(f"SOURCE_{key.upper()}")
    for key, expected_length in (("actual_current_a_tsc", 14), ("wire_current_a", 48)):
        left, right = actual[key], expected[key]
        if len(left) != expected_length or len(right) != expected_length:
            reasons.append(f"SOURCE_{key.upper()}_LENGTH")
        elif max(abs(float(a) - float(b)) for a, b in zip(left, right)) > 1e-9:
            reasons.append(f"SOURCE_{key.upper()}")
    for name in SEMANTIC_ARTIFACTS:
        if actual["artifact_sha256"].get(name) != expected["artifact_sha256"].get(name):
            reasons.append(f"SOURCE_SEMANTIC_ARTIFACT:{name}")
    return reasons


def compare_rows(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    maxima = {"geometry_m": 0.0, "ip_a": 0.0, "coil_a": 0.0, "wire_a": 0.0}
    if len(left["states"]) != 41 or len(right["states"]) != 41:
        failures.append("STATE_COUNT")
    if len(left["actions"]) != 40 or len(right["actions"]) != 40:
        failures.append("ACTION_COUNT")
    for index, (a, b) in enumerate(zip(left["states"], right["states"])):
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
    if left["actions"] != right["actions"]:
        failures.append("ACTIONS")
    for key, tolerance in (("geometry_m", 1e-12), ("ip_a", 1e-9), ("coil_a", 1e-9), ("wire_a", 1e-9)):
        if maxima[key] > tolerance:
            failures.append(key.upper())
    return {"passed": not failures, "failures": list(dict.fromkeys(failures)), "maximum_absolute_difference": maxima}


def _response(row: dict[str, Any], baseline: Sequence[dict[str, Any]]) -> np.ndarray:
    return np.asarray([
        [(state["r_geo_m"] - base["r_geo_m"]) * 1000.0,
         (state["z_geo_m"] - base["z_geo_m"]) * 1000.0,
         state["ip_a"] - base["ip_a"]]
        for state, base in zip(row["states"], baseline)
    ], dtype=float)


def scientific_metrics(
    primary_rows: Sequence[dict[str, Any]], baseline: Sequence[dict[str, Any]],
    stage: dict[str, Any],
) -> dict[str, Any]:
    indexed = {(row["issue_phase"], row["axis"], row["sign"]): row for row in primary_rows}
    responses = {key: _response(row, baseline) for key, row in indexed.items()}
    arm_rows = []
    signal_pass = ip_pass = True
    gates = stage["scientific_gates"]
    for key, response in responses.items():
        phase, axis, sign = key
        h4, h8 = response[phase + 4], response[phase + 8]
        norm4, norm8 = float(np.linalg.norm(h4[:2])), float(np.linalg.norm(h8[:2]))
        signal_pass &= max(norm4, norm8) >= gates["minimum_axis_max_h4_h8_rz_norm_mm"]
        ip_pass &= max(abs(float(h4[2])), abs(float(h8[2]))) <= gates["maximum_h4_h8_absolute_ip_response_a"]
        arm_rows.append({
            "rollout_id": indexed[key]["rollout_id"], "issue_phase": phase,
            "axis": axis, "sign": sign,
            "h4_response_rz_mm": h4[:2].tolist(), "h8_response_rz_mm": h8[:2].tolist(),
            "h4_rz_norm_mm": norm4, "h8_rz_norm_mm": norm8,
            "h4_ip_response_a": float(h4[2]), "h8_ip_response_a": float(h8[2]),
            "peak_rz_norm_mm_states_phase1_phase12": float(np.max(np.linalg.norm(
                response[phase + 1:phase + 13, :2], axis=1
            ))),
        })
    pair_rows = []
    pair_pass = True
    phase_rows = []
    geometry_pass = True
    for phase in stage["issue_phases"]:
        odd_vectors: dict[int, list[np.ndarray]] = {4: [], 8: []}
        for axis in stage["axes"]:
            plus, minus = responses[(phase, axis, "plus")], responses[(phase, axis, "minus")]
            separation4 = float(np.linalg.norm(plus[phase + 4, :2] - minus[phase + 4, :2]))
            separation8 = float(np.linalg.norm(plus[phase + 8, :2] - minus[phase + 8, :2]))
            local_pass = max(separation4, separation8) >= gates["minimum_signed_pair_max_h4_h8_separation_mm"]
            pair_pass &= local_pass
            pair_rows.append({
                "issue_phase": phase, "axis": axis,
                "h4_separation_mm": separation4, "h8_separation_mm": separation8,
                "passed": local_pass,
            })
            for horizon in (4, 8):
                odd_vectors[horizon].append(
                    0.5 * (plus[phase + horizon, :2] - minus[phase + horizon, :2])
                )
        horizon_rows = []
        for horizon in (4, 8):
            matrix = np.column_stack(odd_vectors[horizon])
            singular = np.linalg.svd(matrix, compute_uv=False)
            condition = float(singular[0] / singular[-1]) if singular[-1] > 0 else math.inf
            horizon_rows.append({
                "horizon": horizon, "matrix_columns_even_odd_mm": matrix.tolist(),
                "singular_values_mm": singular.tolist(), "condition": condition,
                "sigma_min_mm": float(singular[-1]),
            })
        best = min(horizon_rows, key=lambda row: row["condition"])
        local_pass = (
            best["condition"] <= gates["maximum_phase_best_h4_h8_condition"]
            and best["sigma_min_mm"] >= gates["minimum_phase_best_h4_h8_sigma_min_mm"]
        )
        geometry_pass &= local_pass
        phase_rows.append({"issue_phase": phase, "horizons": horizon_rows, "best": best, "passed": local_pass})
    passed = signal_pass and pair_pass and geometry_pass and ip_pass
    return {
        "passed": passed,
        "signal_pass": signal_pass,
        "signed_pair_pass": pair_pass,
        "phase_geometry_pass": geometry_pass,
        "ip_pass": ip_pass,
        "arms": arm_rows,
        "signed_pairs": pair_rows,
        "phases": phase_rows,
    }


def run(config_path: Path, source_revision: str, output_dir: Path) -> dict[str, Any]:
    preflight = offline(config_path, source_revision)
    if not preflight["passed"]:
        raise RuntimeError("offline gate failed; TSC forbidden")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {output_dir}")
    output_dir.mkdir(parents=True)
    b0.write_new(output_dir / "offline_preflight.json", preflight)
    stage, cfg, baseline = load(config_path)
    cfg.run_root = output_dir / "rollouts"
    source = _source(cfg)
    target_map = targets(stage, cfg, source)
    envelope = OneMsNR1SafetyEnvelope.from_signal(RGeoZGeoSignal.from_tsc_state(source))
    rows: dict[str, dict[str, Any]] = {}
    for spec in rollout_specs(stage):
        row = _run_one(
            cfg, stage, spec, sequence_for(spec, stage, target_map), envelope,
            baseline["states"][0],
        )
        rows[spec["rollout_id"]] = row
        b0.write_new(output_dir / f"{spec['rollout_id']}.json", row)
        if not row["passed"]:
            break
    execution_pass = len(rows) == stage["rollouts"] and all(row["passed"] for row in rows.values())
    replay_rows = []
    if execution_pass:
        for base in stage["critical_replays"]:
            replay_rows.append({"family_id": base, **compare_rows(rows[base], rows[f"{base}_replay"])})
    replay_pass = len(replay_rows) == 2 and all(row["passed"] for row in replay_rows)
    metrics = None
    if execution_pass:
        primary_rows = [row for row in rows.values() if row["repeat_index"] == 0]
        metrics = scientific_metrics(primary_rows, baseline["states"][:41], stage)
    scientific_pass = metrics is not None and metrics["passed"]
    passed = execution_pass and replay_pass and scientific_pass
    route = stage["routes"]["pass"] if passed else (
        stage["routes"]["execution_fail"] if not execution_pass
        else stage["routes"]["replay_fail"] if not replay_pass
        else stage["routes"]["scientific_fail"]
    )
    result = {
        "schema_version": SCHEMA,
        "kind": "authentic_fixed_1000_signed_temporal_development",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_revision": source_revision,
        "passed": passed,
        "route": route,
        "rollout_count": len(rows),
        "reset_calls": sum(row["reset_calls"] for row in rows.values()),
        "advance_attempts": sum(row["advance_attempts"] for row in rows.values()),
        "gotsc_calls": sum(row["gotsc_calls"] for row in rows.values()),
        "verified_plant_advances": sum(row["verified_plant_advances"] for row in rows.values()),
        "action_geometry": target_map["action_geometry"],
        "critical_replays": replay_rows,
        "scientific_metrics": metrics,
        "claim_boundary": "fixed-1000 signed temporal development only; no model/hold/recovery/control",
    }
    b0.write_new(output_dir / "result.json", result)
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
        b0.write_new(args.output.resolve(), result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
