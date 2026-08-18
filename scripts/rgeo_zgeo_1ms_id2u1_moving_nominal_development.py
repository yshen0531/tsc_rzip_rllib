#!/usr/bin/env python3
"""Run the frozen ID-2U1 moving-nominal development campaign."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_id0_vector_tail import (  # noqa: E402
    InputIntegrityError, inside_root, raw_inventory, sha256, write_new,
)
from scripts.rgeo_zgeo_1ms_id2f1_repeated_context_development import one_rollout  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2u0_nominal_realign_preflight as u0  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import Card15Target  # noqa: E402


CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2u1_moving_nominal_development.json"
CONFIG_SHA256 = "21989e3502f0b8d283293af85c5442ae108bdf3333c2220bb03109c93c9b3cd5"
SCHEMA = "rgeo-zgeo-1ms-id2u1-moving-nominal-development-result-v1"


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(inside_root(path, "JSON evidence").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise InputIntegrityError("JSON object required")
    return value


def _require(stage: dict[str, Any]) -> None:
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2u1-moving-nominal-development-v1",
        "identity": "rgeo-zgeo-1ms-id2u1-moving-nominal-development-v1",
        "stage": "ID-2U1", "takeover_time_ms": 1100, "control_period_ms": 1,
        "horizon_steps": 40, "active_role": "development",
        "active_family_ids": ["u00", "u02", "u04", "u06"],
        "unopened_calibration_family_ids": ["u01", "u03"],
        "unopened_blind_holdout_family_ids": ["u05", "u07"],
        "unique_cells_per_family": 5, "maximum_rollouts": 20,
        "maximum_reset_calls": 20, "maximum_advance_attempts": 800,
        "maximum_gotsc_calls": 800, "maximum_verified_plant_advances": 800,
        "maximum_retained_states": 820, "retry_after_any_advance_attempt": "forbidden",
        "experiment_contract": "tsc_only_moving_nominal_fit_eligible_development",
        "data_use": "development_fit_only_after_all_execution_raw_prefix_signal_ip_and_independent_gates_pass",
        "calibration_holdout_controller_expert_or_rl_use": "forbidden",
        "source_model_or_response_labels_used": 0,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise InputIntegrityError(f"frozen field mismatch: {key}")
    if stage.get("action_semantics") != {
        "absolute_card15_targets": True,
        "maximum_per_coil_issue_delta_a": 0.3,
        "full_0p3_a_allowed": True,
        "issue_to_effect_state_offset": 1,
        "software_queue_added": False,
        "legacy_runner_clipping_may_be_relied_on": False,
        "future_actual_current": "forbidden",
        "grammar": "moving_p03_pause_probe_two_issues_exact_return_resume",
    }:
        raise InputIntegrityError("action semantics changed")
    if stage.get("observability") != {
        "current_same_step_paired_boundary_rgeo_zgeo_and_ip": "exact_noiseless_before_issue",
        "post_takeover_causal_history": "available",
        "future_successor": "unknown_before_issue",
        "invalid_boundary": "fail_closed",
    }:
        raise InputIntegrityError("observation contract changed")
    if stage.get("semantic_artifacts") != ["inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv"]:
        raise InputIntegrityError("semantic artifacts changed")
    if stage.get("diagnostic_artifacts") != ["sprsina"]:
        raise InputIntegrityError("diagnostic artifacts changed")
    gates = stage.get("data_gates", {})
    if (gates.get("minimum_peak_paired_rz_norm_m") != 0.00002
            or gates.get("maximum_peak_paired_abs_ip_a") != 100.0
            or gates.get("calibration_or_holdout_records_read") != 0):
        raise InputIntegrityError("data gates changed")
    storage = stage.get("storage_gate", {})
    if storage != {
        "minimum_free_bytes_before_run": 75000000000,
        "maximum_estimated_raw_bytes": 50000000000,
        "minimum_free_bytes_after_estimate": 25000000000,
        "output_must_not_exist": True,
        "raw_compression": "forbidden",
    }:
        raise InputIntegrityError("storage gate changed")


def load(path: Path = CONFIG) -> tuple[dict[str, Any], Any, list[dict[str, Any]]]:
    path = inside_root(path, "ID2U1 config")
    if sha256(path) != CONFIG_SHA256:
        raise InputIntegrityError("ID2U1 config hash mismatch")
    stage = _json(path)
    _require(stage)
    for name, spec in stage["evidence"].items():
        evidence = inside_root(ROOT / spec["path"], name)
        if sha256(evidence) != spec["sha256"]:
            raise InputIntegrityError(f"evidence mismatch: {name}")
    saved = _json(ROOT / stage["evidence"]["id2u0_result"]["path"])
    audit = _json(ROOT / stage["evidence"]["id2u0_independent"]["path"])
    if (saved.get("route") != stage["evidence"]["id2u0_result"]["required_route"]
            or saved.get("passed") is not True or audit.get("audit_passed") is not True):
        raise InputIntegrityError("ID2U0 evidence is not eligible")
    recomputed = u0.execute(ROOT / stage["evidence"]["id2u0_config"]["path"])
    if recomputed["prospective_campaign_streams"] != saved.get("prospective_campaign_streams"):
        raise InputIntegrityError("ID2U0 stream recomputation changed")
    _, cfg, _, _ = u0.load_stage(ROOT / stage["evidence"]["id2u0_config"]["path"])
    streams = campaign_streams(stage, recomputed["prospective_campaign_streams"])
    return stage, cfg, streams


def campaign_streams(stage: dict[str, Any], frozen: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    active = set(stage["active_family_ids"])
    rows: list[dict[str, Any]] = []
    for item in frozen:
        if item["family_id"] not in active:
            continue
        if item["role"] != "development" or item["arrival"] != "frontloaded":
            raise InputIntegrityError("active family role/arrival changed")
        direction = item.get("direction")
        probe_issue = int(item["probe_issue"])
        rows.append({
            "rollout_id": item["rollout_id"],
            "cell_id": item["rollout_id"],
            "group_id": item["family_id"],
            "context_id": item["family_id"],
            "role": item["role"],
            "arrival": item["arrival"],
            "nominal_level_at_probe": int(item["nominal_level_at_probe"]),
            "replay_index": 0,
            "cell_kind": "baseline" if direction is None else "probe",
            "direction_id": direction,
            "sign": item.get("sign"),
            "probe_issue_step": None if direction is None else probe_issue,
            "probe_duration_issues": int(item["probe_duration_issues"]),
            "non_nominal_issue_steps": [] if direction is None else [probe_issue],
            "targets": [Card15Target(tuple(action["expected_card15_fields"]),
                                     tuple(action["target_current_a_tsc"]))
                        for action in item["actions"]],
            "actions": item["actions"],
        })
    expected = [f"u{i:02d}" for i in (0, 2, 4, 6)]
    if len(rows) != 20 or [group for group in expected
                           if sum(row["group_id"] == group for row in rows) != 5]:
        raise InputIntegrityError("development campaign cardinality changed")
    if any(row["group_id"] in set(stage["unopened_calibration_family_ids"]
                                  + stage["unopened_blind_holdout_family_ids"]) for row in rows):
        raise InputIntegrityError("unopened family leaked")
    return rows


def offline(path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    action_rows: list[dict[str, Any]] = []
    try:
        stage, _, rows = load(path)
        for row in rows:
            if (len(row["actions"]) != 40
                    or any(float(action["maximum_issued_delta_a"]) > 0.3
                           for action in row["actions"])):
                raise InputIntegrityError("action stream invalid")
        action_rows = [{key: value for key, value in row.items() if key != "targets"}
                       for row in rows]
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {
        "schema_version": SCHEMA, "kind": "offline_preflight",
        "source_revision": source_revision, "stage_config_sha256": sha256(path),
        "passed": not failures, "failures": failures, "action_streams": action_rows,
        "reset_calls": 0, "advance_attempts": 0, "plant_advance_gotsc_calls": 0,
        "verified_plant_advances": 0, "models_fit_or_updated": 0,
        "calibration_or_holdout_records_read": 0,
    }


def matched_prefix_checks(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> list[dict[str, Any]]:
    checks = []
    for group_id in stage["active_family_ids"]:
        members = [row for row in rows if row["group_id"] == group_id]
        baseline = next((row for row in members if row["cell_kind"] == "baseline"), None)
        failures: list[str] = []
        if baseline is None or len(members) != 5:
            failures.append("CELL_SET")
        else:
            issue = next(int(row["probe_issue_step"]) for row in members if row["cell_kind"] == "probe")
            for probe in [row for row in members if row["cell_kind"] == "probe"]:
                for index in range(issue + 1):
                    for key in ("r_geo_m", "z_geo_m", "r_mid_m", "ip_a",
                                "actual_current_decimal_a_tsc", "wire_current_a"):
                        if baseline["states"][index][key] != probe["states"][index][key]:
                            failures.append(f"{probe['cell_id']}:STATE:{index}:{key}")
                for step in range(issue):
                    if (baseline["actions"][step]["expected_card15_fields"]
                            != probe["actions"][step]["expected_card15_fields"]):
                        failures.append(f"{probe['cell_id']}:ACTION:{step}")
        checks.append({"group_id": group_id, "passed": not failures,
                       "failures": list(dict.fromkeys(failures))})
    return checks


def response_metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    metrics = []
    for group_id in stage["active_family_ids"]:
        members = [row for row in rows if row["group_id"] == group_id]
        baseline = next(row for row in members if row["cell_kind"] == "baseline")
        for probe in [row for row in members if row["cell_kind"] == "probe"]:
            origin = int(probe["probe_issue_step"])
            truth = np.asarray([[state[key] for key in ("r_geo_m", "z_geo_m", "ip_a")]
                                for state in probe["states"][origin + 1:41]], dtype=float)
            base = np.asarray([[state[key] for key in ("r_geo_m", "z_geo_m", "ip_a")]
                               for state in baseline["states"][origin + 1:41]], dtype=float)
            response = truth - base
            norms = np.linalg.norm(response[:, :2], axis=1)
            peak = int(np.argmax(norms))
            metrics.append({
                "cell_id": probe["cell_id"], "group_id": group_id,
                "direction": probe["direction_id"], "sign": probe["sign"],
                "peak_state": origin + 1 + peak,
                "peak_rz_norm_m": float(norms[peak]),
                "maximum_abs_ip_response_a": float(np.max(np.abs(response[:, 2]))),
                "response_by_state": response.tolist(),
            })
    gates = stage["data_gates"]
    signal = len(metrics) == 16 and all(
        row["peak_rz_norm_m"] >= gates["minimum_peak_paired_rz_norm_m"] for row in metrics)
    ip_ok = len(metrics) == 16 and all(
        row["maximum_abs_ip_response_a"] <= gates["maximum_peak_paired_abs_ip_a"] for row in metrics)
    return {"probe_count": len(metrics), "all_probe_signal_passed": signal,
            "all_probe_ip_passed": ip_ok, "probe_metrics": metrics,
            "passed": signal and ip_ok}


def storage(stage: dict[str, Any], output: Path) -> dict[str, Any]:
    free = shutil.disk_usage(output.parent).free
    estimate = int(stage["storage_gate"]["maximum_estimated_raw_bytes"])
    return {"free_bytes_before_run": free, "estimated_raw_bytes": estimate,
            "estimated_free_bytes_after_run": free - estimate,
            "passed": free >= int(stage["storage_gate"]["minimum_free_bytes_before_run"])
            and free - estimate >= int(stage["storage_gate"]["minimum_free_bytes_after_estimate"])}


def run(path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = inside_root(output, "ID2U1 output")
    if output.exists():
        raise FileExistsError(str(output))
    stage, cfg, streams = load(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    storage_gate = storage(stage, output)
    output.mkdir()
    preflight = offline(path, source_revision)
    write_new(output / "offline_preflight.json", preflight)
    if not storage_gate["passed"] or not preflight["passed"]:
        route = stage["routes"]["storage_fail" if not storage_gate["passed"] else "offline_or_input_fail"]
        result = {"schema_version": SCHEMA, "source_revision": source_revision,
                  "stage_config_sha256": CONFIG_SHA256, "passed": False, "route": route,
                  "storage_gate": storage_gate, "reasons": preflight["failures"],
                  "rollouts_completed": 0, "reset_calls": 0, "advance_attempts": 0,
                  "plant_advance_gotsc_calls": 0, "verified_plant_advances": 0,
                  "development_fit_data_eligible": False, "models_fit_or_updated": 0,
                  "calibration_or_holdout_records_read": 0}
        write_new(output / "result.json", result)
        return result
    cfg.run_root = output / "rollouts"
    runtime = dict(stage)
    runtime["empirical_exploration"] = dict(stage["empirical_exploration"])
    runtime["empirical_exploration"]["inner_pulse_issue_clearance"] = (
        stage["empirical_exploration"]["inner_probe_issue_clearance"])
    rows = []
    for stream in streams:
        row = one_rollout(cfg, runtime, stream)
        row.update({"schema_version": SCHEMA, "source_revision": source_revision})
        rows.append(row)
        write_new(output / f"{row['rollout_id']}.json", row)
        if not row["passed"]:
            break
    inventory = raw_inventory(output, rows, stage)
    execution = len(rows) == 20 and all(row["passed"] for row in rows)
    prefixes = matched_prefix_checks(rows, stage) if execution else []
    metrics = response_metrics(rows, stage) if execution else {"passed": False}
    if not execution:
        route = stage["routes"]["execution_or_interface_fail"]
    elif inventory["missing_required_artifacts"]:
        route = stage["routes"]["raw_integrity_fail"]
    elif not all(row["passed"] for row in prefixes):
        route = stage["routes"]["prefix_fail"]
    elif not metrics["passed"]:
        route = stage["routes"]["signal_or_ip_fail"]
    else:
        route = stage["routes"]["pass"]
    passed = route == stage["routes"]["pass"]
    result = {
        "schema_version": SCHEMA, "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256, "passed": passed, "route": route,
        "storage_gate": storage_gate, "matched_prefix_checks": prefixes,
        "response_metrics": metrics, "rollouts_completed": len(rows),
        "unique_cells_completed": len({row["cell_id"] for row in rows}),
        "whole_history_groups_completed": len({row["group_id"] for row in rows}),
        "reset_calls": sum(row["reset_calls"] for row in rows),
        "advance_attempts": sum(row["advance_attempts"] for row in rows),
        "plant_advance_gotsc_calls": sum(row["plant_advance_gotsc_calls"] for row in rows),
        "verified_plant_advances": sum(row["verified_plant_advances"] for row in rows),
        **inventory, "development_fit_data_eligible": passed,
        "active_family_ids": stage["active_family_ids"],
        "unopened_calibration_family_ids": stage["unopened_calibration_family_ids"],
        "unopened_blind_holdout_family_ids": stage["unopened_blind_holdout_family_ids"],
        "calibration_or_holdout_records_read": 0,
        "calibration_holdout_controller_expert_or_rl_use": "forbidden",
        "models_fit_or_updated": 0, "claim_boundary": stage["claim_boundary"],
    }
    write_new(output / "result.json", result)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("offline", "run"))
    parser.add_argument("--stage-config", type=Path, default=CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = (offline(args.stage_config, args.source_revision) if args.mode == "offline"
              else run(args.stage_config, args.source_revision,
                       args.output or ROOT / f"rgeo_zgeo_1ms_id2u1_{args.source_revision[:8]}"))
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
