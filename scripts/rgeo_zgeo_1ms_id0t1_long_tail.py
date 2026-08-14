#!/usr/bin/env python3
"""Prospectively frozen 1 ms ID-0T1 state32 tail discriminator."""

from __future__ import annotations

import argparse
import json
import math
from decimal import Decimal
from pathlib import Path
import sys
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_id0_vector_tail as id0  # noqa: E402
from scripts.rgeo_zgeo_1ms_nr1_qualification import _source  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    Card15Target,
    OneMsNR1SafetyEnvelope,
    assert_exact_slew,
    build_frozen_one_ms_prefixes,
    card15_target_decimal_a,
    validate_one_ms_config,
)
from tsc_rzip_rllib.control.rgeo_zgeo_contract import ContractError, RGeoZGeoSignal  # noqa: E402
from tsc_rzip_rllib.core.runner import TSCConfig  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-id0t1-long-tail-v1"
CONFIG_SHA256 = "2b5137284435845587e6d93ed9f1cc9736e4bef43ded17da26c6e02cf5356df3"
DEFAULT_STAGE = ROOT / "configs/rgeo_zgeo_1ms_id0t1_long_tail.json"
OFFLINE_PASS = "ONE_MS_ID0T1_OFFLINE_PASS_RUN_ONLY"


class InputIntegrityError(ValueError):
    """Frozen input/config/evidence identity is not exact."""


def inside_root(path: Path, label: str) -> Path:
    result = path.resolve()
    if not result.is_relative_to(ROOT.resolve()):
        raise InputIntegrityError(f"{label} leaves repository: {path}")
    return result


def sha256(path: Path) -> str:
    return id0.sha256(path)


def write_new(path: Path, value: Any) -> None:
    id0.write_new(path, value)


def _exact_stage(stage: dict[str, Any]) -> None:
    exact = {
        "schema_version": SCHEMA,
        "campaign_id": "rgeo_zgeo_1ms_id0t1_long_tail_v1",
        "takeover_time_ms": 1100,
        "control_period_ms": 1,
        "horizon_steps": 32,
        "rollouts": 8,
        "maximum_reset_calls": 8,
        "maximum_advance_attempts": 256,
        "maximum_gotsc_calls": 256,
        "maximum_verified_plant_advances": 256,
        "retry_after_any_advance_attempt": "forbidden",
        "completed_state_count": 264,
        "completed_required_artifact_files": 1320,
        "model_development_use": "forbidden_this_stage_is_design_evidence_only",
        "holdout_records_read": 0,
    }
    for key, value in exact.items():
        if stage.get(key) != value:
            raise InputIntegrityError(f"frozen field mismatch: {key}")
    if stage.get("context") != {
        "context_id": "early_long_tail", "pulse_issue_step": 2,
        "return_issue_step": 3, "repetitions_per_signed_direction": 1,
        "effect_window_states": [3, 32], "reference_prefix_terminal_state": 20,
    }:
        raise InputIntegrityError("context mismatch")
    if stage.get("scientific_gates") != {
        "tail_terminal_state_index": 32, "peak_response_states": [3, 32],
        "tail_terminal_maximum_rz_norm_m": 0.00005,
        "tail_terminal_maximum_peak_fraction": 0.20,
        "tail_terminal_maximum_abs_ip_a": 10.0,
        "no_automatic_longer_horizon_after_fail": True,
    }:
        raise InputIntegrityError("scientific gate mismatch")
    if len(stage.get("directions", ())) != 3 or [row.get("direction_id") for row in stage["directions"]] != ["p03", "p04", "p07"]:
        raise InputIntegrityError("direction identity mismatch")
    if len(stage.get("evidence", {}).get("reference_records", ())) != 14:
        raise InputIntegrityError("reference record count mismatch")
    forbidden = (
        stage.get("calibration_use"), stage.get("holdout_use"),
        stage.get("expert_oracle_fixture_bc_dagger_rl_use"),
        stage.get("controller_safety_or_recourse_qualification_use"),
    )
    if any(value != "forbidden" for value in forbidden):
        raise InputIntegrityError("forbidden-use contract mismatch")


def load(stage_path: Path) -> tuple[dict[str, Any], TSCConfig]:
    stage_path = inside_root(stage_path, "stage config")
    if sha256(stage_path) != CONFIG_SHA256:
        raise InputIntegrityError("ID-0T1 config SHA-256 mismatch")
    stage = json.loads(stage_path.read_text(encoding="utf-8"))
    _exact_stage(stage)
    evidence = stage["evidence"]
    for label in ("id0_result_report", "id0_result", "id0_independent"):
        row = evidence[label]
        path = inside_root(ROOT / row["path"], label)
        if not path.is_file() or sha256(path) != row["sha256"]:
            raise InputIntegrityError(f"{label} hash mismatch")
    for index, row in enumerate(evidence["reference_records"]):
        path = inside_root(ROOT / row["path"], f"reference record {index}")
        if not path.is_file() or sha256(path) != row["sha256"]:
            raise InputIntegrityError(f"reference record {index} hash mismatch")
    result = json.loads((ROOT / evidence["id0_result"]["path"]).read_text(encoding="utf-8"))
    audit = json.loads((ROOT / evidence["id0_independent"]["path"]).read_text(encoding="utf-8"))
    if result.get("route") != "ONE_MS_ID0_TAIL_HORIZON_INSUFFICIENT_REDESIGN":
        raise InputIntegrityError("ID-0 result route mismatch")
    if not audit.get("audit_passed") or audit.get("failures"):
        raise InputIntegrityError("ID-0 independent audit mismatch")
    base = inside_root(ROOT / stage["base_tsc_config"], "base config")
    if sha256(base) != evidence["base_tsc_config_sha256"]:
        raise InputIntegrityError("base config hash mismatch")
    cfg = TSCConfig.from_json(base)
    validate_one_ms_config(start_folder=cfg.start_folder, dt_ms=cfg.dt_ms, slew_a_per_ms=cfg.current_slew_a_per_ms)
    return stage, cfg


def rollout_specs(stage: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        {"rollout_id": f"baseline_q0_r{repeat}", "context_id": "baseline",
         "direction_id": None, "sign": None, "repeat_index": repeat,
         "pulse_issue_step": None, "return_issue_step": None}
        for repeat in range(2)
    ]
    context = stage["context"]
    for direction in stage["directions"]:
        for sign in ("plus", "minus"):
            rows.append({
                "rollout_id": f"early_{direction['direction_id']}_{sign}_r0",
                "context_id": context["context_id"],
                "direction_id": direction["direction_id"], "sign": sign,
                "repeat_index": 0, "pulse_issue_step": context["pulse_issue_step"],
                "return_issue_step": context["return_issue_step"],
            })
    if len(rows) != stage["rollouts"] or len({row["rollout_id"] for row in rows}) != len(rows):
        raise InputIntegrityError("rollout matrix count/identity mismatch")
    return rows


def targets_and_stream(stage: dict[str, Any], cfg: TSCConfig, source: dict[str, Any]) -> tuple[dict[str, Card15Target], list[dict[str, Any]]]:
    frozen = build_frozen_one_ms_prefixes(
        source_current_a_tsc=source["currents_a_tsc"], turns_tsc=cfg.turns_tsc,
        min_current_a_tsc=cfg.min_current_a_tsc, max_current_a_tsc=cfg.max_current_a_tsc,
    )
    targets: dict[str, Card15Target] = {"q0": frozen.q0}
    for row in stage["directions"]:
        for sign in ("plus", "minus"):
            targets[f"{row['direction_id']}:{sign}"] = id0.target_from_fields(
                row[f"{sign}_card15_fields"], cfg, f"id0t1.{row['direction_id']}.{sign}"
            )
    streams = []
    for spec in rollout_specs(stage):
        sequence = [targets["q0"]] * stage["horizon_steps"]
        if spec["pulse_issue_step"] is not None:
            sequence[spec["pulse_issue_step"]] = targets[f"{spec['direction_id']}:{spec['sign']}"]
        previous = tuple(source["active_command_decimal_a_tsc"])
        actions = []
        for issue, target in enumerate(sequence):
            exact = card15_target_decimal_a(target, cfg.turns_tsc, name=f"id0t1.{spec['rollout_id']}.{issue}")
            maximum = assert_exact_slew(previous, exact, name=f"id0t1.{spec['rollout_id']}.{issue}")
            if any(value < low or value > high for value, low, high in zip(
                exact, map(lambda x: Decimal(str(x)), cfg.min_current_a_tsc),
                map(lambda x: Decimal(str(x)), cfg.max_current_a_tsc)
            )):
                raise ContractError("target leaves absolute current limits")
            actions.append({
                "issue_step": issue, "issue_time_ms": 1100 + issue,
                "effect_state_index": issue + 1, "effect_time_ms": 1101 + issue,
                "expected_card15_fields": list(target.card15_fields),
                "target_current_a_tsc": list(target.current_a_tsc),
                "maximum_issued_delta_a": maximum,
            })
            previous = exact
        streams.append({**spec, "targets": sequence, "actions": actions})
    return targets, streams


def _reference_records(stage: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result = {}
    for row in stage["evidence"]["reference_records"]:
        path = inside_root(ROOT / row["path"], "reference record")
        result[path.stem] = json.loads(path.read_text(encoding="utf-8"))
    return result


def prefix_comparisons(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> list[dict[str, Any]]:
    references = _reference_records(stage)
    proxy = {
        "semantic_artifacts": stage["semantic_artifacts"],
        "repeatability": {key: stage["prefix_match"][key] for key in ("geometry_m", "ip_a", "coil_a", "wire_a")},
    }
    comparisons = []
    terminal = stage["prefix_match"]["terminal_state_index"]
    for row in rows:
        prefix = {**row, "states": row["states"][:terminal + 1], "actions": row["actions"][:terminal]}
        if row["context_id"] == "baseline":
            keys = ("baseline_q0_r0", "baseline_q0_r1")
        else:
            keys = tuple(f"early_{row['direction_id']}_{row['sign']}_r{repeat}" for repeat in range(2))
        for key in keys:
            comparisons.append({
                "new_rollout_id": row["rollout_id"], "reference_rollout_id": key,
                **id0.compare_rows(prefix, references[key], proxy),
            })
    return comparisons


def scientific_metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    baseline = id0._matched_baseline(rows)
    gates = stage["scientific_gates"]
    first, last = gates["peak_response_states"]
    arm_metrics = []
    for row in rows:
        if row["context_id"] == "baseline":
            continue
        response = np.asarray(id0._response(row, baseline), dtype=float)
        rz = np.linalg.norm(response[:, :2], axis=1)
        peak = float(np.max(rz[first:last + 1]))
        terminal = gates["tail_terminal_state_index"]
        arm_metrics.append({
            "rollout_id": row["rollout_id"], "direction_id": row["direction_id"], "sign": row["sign"],
            "peak_rz_norm_m_states_3_32": peak,
            "terminal_state_index": terminal,
            "terminal_rz_norm_m": float(rz[terminal]),
            "terminal_peak_fraction": float(rz[terminal] / peak) if peak else math.inf,
            "terminal_absolute_ip_response_a": float(abs(response[terminal, 2])),
        })
    tail_passed = all(
        row["terminal_rz_norm_m"] <= gates["tail_terminal_maximum_rz_norm_m"]
        and row["terminal_peak_fraction"] <= gates["tail_terminal_maximum_peak_fraction"]
        and row["terminal_absolute_ip_response_a"] <= gates["tail_terminal_maximum_abs_ip_a"]
        for row in arm_metrics
    )
    return {"arm_metrics": arm_metrics, "tail_passed": tail_passed}


def offline(stage_path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    stage = source_signal = streams = None
    try:
        stage, cfg = load(stage_path)
        source = _source(cfg)
        source_signal = RGeoZGeoSignal.from_tsc_state(source)
        envelope = OneMsNR1SafetyEnvelope.from_signal(source_signal)
        failures.extend(envelope.state_reasons(source_signal, source["currents_a_tsc"], cfg.min_current_a_tsc, cfg.max_current_a_tsc))
        _, raw_streams = targets_and_stream(stage, cfg, source)
        streams = [{key: value for key, value in row.items() if key != "targets"} for row in raw_streams]
        references = _reference_records(stage)
        if any(not row.get("passed") or len(row.get("states", ())) != 21 or len(row.get("actions", ())) != 20 for row in references.values()):
            failures.append("REFERENCE_RECORD_STRUCTURE")
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    failures = list(dict.fromkeys(failures))
    return {
        "schema_version": SCHEMA, "kind": "offline_preflight", "source_revision": source_revision,
        "stage_config_sha256": sha256(inside_root(stage_path, "stage config")),
        "passed": not failures, "route": OFFLINE_PASS if not failures else (
            stage["routes"]["offline_fail"] if stage else "ONE_MS_ID0T1_OFFLINE_FAIL_NO_TSC"
        ), "failures": failures, "source_signal": None if source_signal is None else source_signal.to_dict(),
        "rollout_action_streams": streams, "reset_calls": 0, "advance_attempts": 0,
        "plant_advance_gotsc_calls": 0, "verified_plant_advances": 0,
    }


def route_for(stage: dict[str, Any], execution: bool, raw_ok: bool, prefix_ok: bool, metrics: dict[str, Any] | None) -> str:
    if not execution:
        return stage["routes"]["execution_or_interface_fail"]
    if not raw_ok:
        return stage["routes"]["raw_integrity_fail"]
    if not prefix_ok:
        return stage["routes"]["prefix_match_fail"]
    assert metrics is not None
    return stage["routes"]["pass"] if metrics["tail_passed"] else stage["routes"]["tail_horizon_fail"]


def run(stage_path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = inside_root(output, "run output")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    output.mkdir(parents=True)
    gate = offline(stage_path, source_revision)
    write_new(output / "offline_preflight.json", gate)
    if not gate["passed"]:
        result = {"schema_version": SCHEMA, "source_revision": source_revision, "passed": False,
                  "route": gate["route"], "reasons": gate["failures"], "rollouts_completed": 0,
                  "reset_calls": 0, "advance_attempts": 0, "plant_advance_gotsc_calls": 0,
                  "verified_plant_advances": 0}
        write_new(output / "result.json", result)
        return result
    stage, cfg = load(stage_path)
    if gate["stage_config_sha256"] != sha256(inside_root(stage_path, "stage config")):
        raise InputIntegrityError("stage changed after offline preflight")
    cfg.run_root = output / "rollouts"
    source = _source(cfg)
    _, streams = targets_and_stream(stage, cfg, source)
    rows = []
    for stream in streams:
        row = id0.one_rollout(cfg, stage, stream)
        row["schema_version"] = SCHEMA
        row["source_revision"] = source_revision
        rows.append(row)
        write_new(output / f"{row['rollout_id']}.json", row)
        if not row["passed"]:
            break
    execution = len(rows) == stage["rollouts"] and all(row["passed"] for row in rows)
    inventory = id0.raw_inventory(output, rows, stage)
    raw_ok = execution and not inventory["missing_required_artifacts"] and inventory["required_artifact_files"] == stage["completed_required_artifact_files"]
    comparisons = prefix_comparisons(rows, stage) if execution else []
    prefix_ok = execution and len(comparisons) == 16 and all(row["passed"] for row in comparisons)
    metrics = scientific_metrics(rows, stage) if prefix_ok else None
    route = route_for(stage, execution, raw_ok, prefix_ok, metrics)
    result = {
        "schema_version": SCHEMA, "source_revision": source_revision,
        "passed": route == stage["routes"]["pass"], "route": route,
        "execution_passed": execution, "raw_integrity_passed": raw_ok,
        "id0_prefix_match_passed": prefix_ok, "prefix_comparisons": comparisons,
        "scientific_metrics": metrics, "rollouts_completed": len(rows),
        "reset_calls": sum(row["reset_calls"] for row in rows),
        "advance_attempts": sum(row["advance_attempts"] for row in rows),
        "plant_advance_gotsc_calls": sum(row["plant_advance_gotsc_calls"] for row in rows),
        "verified_plant_advances": sum(row["verified_plant_advances"] for row in rows),
        **inventory,
        "claim_boundary": "state32_tail_design_evidence_only_not_model_controller_safety_or_recourse",
    }
    write_new(output / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("offline", "run"))
    parser.add_argument("--stage-config", type=Path, default=DEFAULT_STAGE)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "offline":
        result = offline(args.stage_config.resolve(), args.source_revision)
        write_new(args.output.resolve(), result)
    else:
        result = run(args.stage_config.resolve(), args.source_revision, args.output.resolve())
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if (result["passed"] or (args.mode == "run" and result.get("execution_passed") and result.get("raw_integrity_passed") and result.get("id0_prefix_match_passed"))) else 2


if __name__ == "__main__":
    raise SystemExit(main())
