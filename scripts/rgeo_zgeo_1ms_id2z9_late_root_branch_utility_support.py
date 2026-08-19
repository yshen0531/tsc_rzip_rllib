#!/usr/bin/env python3
"""Run frozen ID-2Z9 late-root branch utility/support campaign."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_id2z7_branch_continuation as z7  # noqa: E402


z6 = z7.z6
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z9_late_root_branch_utility_support.json"
CONFIG_SHA256 = "9e520c1410a80d1a4ba79038a721bfce1e7148b033898ef534cb29914c4256b7"
SCHEMA = "rgeo-zgeo-1ms-id2z9-late-root-branch-utility-support-result-v1"
ARM_IDS = z6.ARM_IDS
FRESH_ROUNDS = (0, 1)


def inside(path: Path, label: str) -> Path:
    return z7._inside(path, label)


def load_json(path: Path) -> dict[str, Any]:
    return z7._json(path)


def _verify_evidence(stage: dict[str, Any]) -> dict[str, dict[str, Any]]:
    values: dict[str, dict[str, Any]] = {}
    for name, spec in stage["evidence"].items():
        path = inside(ROOT / spec["path"], name)
        if z6.z5.z3.z1.y1r1.y1.x1.sha256(path) != spec["sha256"]:
            raise z6._error(f"evidence hash mismatch: {name}")
        values[name] = load_json(path) if path.suffix == ".json" else {}
    return values


def _require(stage: dict[str, Any]) -> None:
    if z6.z5.z3.z1.y1r1.y1.x1.sha256(CONFIG) != CONFIG_SHA256:
        raise z6._error("config hash mismatch")
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2z9-late-root-branch-utility-support-v1",
        "identity": "rgeo-zgeo-1ms-id2z9-late-root-branch-utility-support-v1",
        "stage": "ID-2Z9", "takeover_time_ms": 1100,
        "control_period_ms": 1, "inherited_selected_macro_sequence":
        ["f4", "b2f2", "f2b2"], "common_horizon_steps": 77,
        "common_terminal_state_index": 77, "maximum_fresh_rounds": 2,
        "maximum_branches_per_round": 5, "maximum_branch_rollouts": 10,
        "maximum_replay_rollouts": 1, "maximum_rollouts": 11,
        "maximum_reset_calls": 11, "maximum_advance_attempts": 847,
        "maximum_gotsc_calls": 847, "maximum_verified_plant_advances": 847,
        "maximum_retained_states": 858,
        "required_artifact_files_if_all_complete": 4290,
        "retry_after_any_advance_attempt": "forbidden", "models_fit_or_updated": 0,
    }
    for key, value in exact.items():
        if stage.get(key) != value:
            raise z6._error(f"frozen field changed: {key}")
    if stage.get("fresh_rounds") != [
            {"round_index": 0, "round_id": "round_d_state61",
             "decision_state_index": 61, "macro_last_issue": 64},
            {"round_index": 1, "round_id": "round_e_state65",
             "decision_state_index": 65, "macro_last_issue": 68}]:
        raise z6._error("round schedule changed")
    if stage.get("candidate_specs") != [
            {"arm_id": "hold4", "tokens": "HHHH", "fit_weight": 1},
            {"arm_id": "b4", "tokens": "BBBB", "fit_weight": 1},
            {"arm_id": "f4", "tokens": "FFFF", "fit_weight": 1},
            {"arm_id": "b2f2", "tokens": "BBFF", "fit_weight": 1},
            {"arm_id": "f2b2", "tokens": "FFBB", "fit_weight": 1}]:
        raise z6._error("candidate matrix changed")
    if stage["measurement_gates"] != {
            "baseline_arm_id": "hold4",
            "terminal_state_indices": [72, 73, 74, 75, 76, 77],
            "maximum_capture_source_rz_distance_m": 0.025,
            "maximum_capture_rz_step_speed_m_per_s": 0.1,
            "maximum_capture_absolute_source_ip_fraction": 0.05,
            "minimum_round_score_improvement_over_hold": 0.02,
            "minimum_final_score_improvement_over_round_d_hold": 0.05,
            "new_complete_fit_weight_windows_required": 10,
            "critical_replay_exact_checked_trajectory_required": True,
            "selection_order": ["capture_first", "minimum_terminal_worst_normalized_score",
                                "minimum_terminal_max_source_rz_distance",
                                "minimum_terminal_max_rz_step_speed",
                                "minimum_terminal_max_absolute_source_ip_fraction",
                                "stable_arm_id"],
            "both_fresh_rounds_required": True,
            "pass_is_teacher_utility_and_development_data_only": True}:
        raise z6._error("measurement gates changed")


def _selected_id2z7_constructed(z6_stage: dict[str, Any], cfg: Any,
                                targets: dict[str, Any], parent: dict[str, Any]) -> dict[str, Any]:
    selected = parent
    for round_index, arm in ((1, "b2f2"), (2, "f2b2")):
        streams = z7.fresh_round_streams(z6_stage, cfg, targets, selected, round_index)
        selected = next(row for row in streams if row["arm_id"] == arm)
    return selected


def runtime_stage(stage: dict[str, Any], z6_stage: dict[str, Any]) -> dict[str, Any]:
    value = dict(z6_stage)
    value.update({
        "common_horizon_steps": 77, "common_terminal_state_index": 77,
        "maximum_rounds": 2, "rounds": list(stage["fresh_rounds"]),
        "candidate_specs": list(stage["candidate_specs"]),
        "empirical_exploration": dict(stage["empirical_exploration"]),
        "measurement_gates": dict(stage["measurement_gates"]),
        "semantic_artifacts": list(stage["semantic_artifacts"]),
    })
    return value


def load(path: Path = CONFIG) -> tuple[dict[str, Any], dict[str, Any], Any,
                                       dict[str, Any], dict[str, Any], dict[str, Any]]:
    path = inside(path, "ID2Z9 config")
    if path != CONFIG.resolve():
        raise z6._error("alternate config forbidden")
    stage = load_json(path)
    _require(stage)
    evidence = _verify_evidence(stage)
    if (evidence["id2z7_result"].get("route")
            != stage["evidence"]["id2z7_result"]["required_route"]
            or evidence["id2z7_result"].get("passed") is not True
            or evidence["id2z7_independent"].get("audit_passed") is not True
            or evidence["id2z8_result"].get("route")
            != stage["evidence"]["id2z8_result"]["required_route"]
            or evidence["id2z8_result"].get("passed") is not False
            or evidence["id2z8_audit"].get("audit_passed") is not True):
        raise z6._error("source result route mismatch")
    (z7_stage, z6_stage, cfg, targets, _, _, parent, _, _) = z7.load(
        ROOT / stage["evidence"]["id2z7_config"]["path"])
    del z7_stage
    selected = _selected_id2z7_constructed(z6_stage, cfg, targets, parent)
    compact = evidence["id2z7_critical_replay"]
    if (compact.get("passed") is not True or len(compact.get("states", [])) != 70
            or len(compact.get("actions", [])) != 69
            or [row.get("expected_card15_fields") for row in compact["actions"]]
            != [row.get("expected_card15_fields") for row in selected["actions"]]):
        raise z6._error("ID2Z7 selected replay mismatch")
    return stage, runtime_stage(stage, z6_stage), cfg, targets, selected, compact


def build_round_streams(stage: dict[str, Any], runtime: dict[str, Any], cfg: Any,
                        targets: dict[str, Any], parent: dict[str, Any],
                        round_index: int) -> list[dict[str, Any]]:
    spec = stage["fresh_rounds"][round_index]
    decision = int(spec["decision_state_index"])
    horizon = int(stage["common_horizon_steps"])
    if len(parent["targets"]) < decision or len(parent["actions"]) < decision:
        raise z6._error("parent prefix too short")
    rows = []
    for candidate in stage["candidate_specs"]:
        arm = candidate["arm_id"]
        rollout_id = f"r{round_index + 3}__{arm}"
        sequence = list(parent["targets"][:decision])
        virtual_rows = [list(row["probe_virtual_action"])
                        for row in parent["actions"][:decision]]
        current = sequence[-1]
        virtual = list(virtual_rows[-1])
        q0 = targets["q0"]
        for offset, token in enumerate(candidate["tokens"]):
            current, virtual = z6._apply_token(
                current, virtual, token, q0, targets, cfg,
                f"id2z9.{rollout_id}.{decision + offset}.{token}")
            sequence.append(current)
            virtual_rows.append(list(virtual))
        while len(sequence) < horizon:
            sequence.append(current)
            virtual_rows.append(list(virtual))
        actions = z6.z5.z3.z1.c1._actions(sequence, cfg, rollout_id, virtual_rows)
        rows.append({
            "rollout_id": rollout_id, "candidate_id": rollout_id,
            "arm_id": arm, "tokens": candidate["tokens"],
            "fit_weight": int(candidate["fit_weight"]),
            "round_index": round_index, "round_id": spec["round_id"],
            "parent_selected_arm_id": parent.get("arm_id"), "cell_id": rollout_id,
            "cell_kind": "late_root_branch_utility_support_window",
            "context_id": f"selected_state_{decision}_causal_prefix",
            "direction_id": "p07minus__p03forward__hold_time_shared",
            "coordinate": "late_root_b_f_h_macro", "sign": None,
            "probe_issue_step": decision, "probe_duration_issues": 4,
            "non_nominal_issue_steps": list(range(decision, decision + 4)),
            "targets": sequence, "actions": actions,
        })
    if [row["arm_id"] for row in rows] != list(ARM_IDS):
        raise z6._error("arm order changed")
    return rows


def validate_stream(stream: dict[str, Any], runtime: dict[str, Any], cfg: Any,
                    targets: dict[str, Any]) -> dict[str, Any]:
    return z6.validate_stream(stream, runtime, cfg, targets)


def offline(path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    checks: list[dict[str, Any]] = []
    try:
        stage, runtime, cfg, targets, parent, _ = load(path)
        for first in build_round_streams(stage, runtime, cfg, targets, parent, 0):
            a = validate_stream(first, runtime, cfg, targets)
            for second in build_round_streams(stage, runtime, cfg, targets, first, 1):
                b = validate_stream(second, runtime, cfg, targets)
                checks.append({"sequence": [first["arm_id"], second["arm_id"]],
                               "passed": bool(a["passed"] and b["passed"]),
                               "failures": list(dict.fromkeys(a["failures"] + b["failures"]))})
        if len(checks) != 25 or not all(row["passed"] for row in checks):
            failures.append("FULL_TWO_ROUND_ACTION_MATRIX_NOT_ADMISSIBLE")
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {"schema_version": "rgeo-zgeo-1ms-id2z9-offline-v1",
            "source_revision": source_revision, "stage_config_sha256": CONFIG_SHA256,
            "passed": not failures, "failures": failures,
            "static_two_round_sequence_count": len(checks),
            "static_two_round_sequences_passed": sum(row["passed"] for row in checks),
            "sequence_checks": checks, "reset_calls": 0, "advance_attempts": 0,
            "plant_advance_gotsc_calls": 0, "models_fit_or_updated": 0}


def final_metrics(rounds: Sequence[dict[str, Any]], rows: Sequence[dict[str, Any]],
                  stage: dict[str, Any], selected: dict[str, Any] | None,
                  replay: dict[str, Any] | None) -> dict[str, Any]:
    complete_fit = sum(bool(row.get("passed") and int(row.get("fit_weight", 0)) == 1)
                       for row in rows)
    replay_value = z6.replay_check(selected, replay, stage["semantic_artifacts"])
    first_hold = next((value for value in rounds[0]["branch_metrics"]
                       if value["arm_id"] == "hold4"), None) if rounds else None
    final_value = None
    if selected is not None:
        source = selected["states"][0]
        terminal = stage["measurement_gates"]["terminal_state_indices"]
        distances = [z6._distance(selected["states"][i], source) for i in terminal]
        speeds = [z6._speed(selected["states"], i) for i in terminal]
        ipf = [abs(float(selected["states"][i]["ip_a"]) - float(source["ip_a"]))
               / abs(float(source["ip_a"])) for i in terminal]
        final_value = max(max(distances) / 0.025, max(speeds) / 0.1,
                          max(ipf) / 0.05)
        capture = bool(max(distances) <= 0.025 and max(speeds) <= 0.1
                       and max(ipf) <= 0.05)
    else:
        capture = False
    first_score = first_hold.get("terminal_worst_normalized_score") if first_hold else None
    improvement = (float(first_score) - float(final_value)
                   if first_score is not None and final_value is not None else None)
    utility = bool(len(rounds) == 2 and all(row.get("passed") for row in rounds)
                   and (capture or (improvement is not None and improvement >= 0.05)))
    data_ready = complete_fit >= 10
    return {"rounds_passed": sum(bool(row.get("passed")) for row in rounds),
            "selected_late_macro_sequence": [row.get("selected_arm_id") for row in rounds],
            "selected_path_capture_passed": capture,
            "round_d_hold_terminal_worst_normalized_score": first_score,
            "selected_path_terminal_worst_normalized_score": final_value,
            "selected_path_score_improvement_over_round_d_hold": improvement,
            "teacher_utility_passed": utility,
            "new_complete_fit_weight_windows": complete_fit,
            "new_complete_fit_weight_windows_required": 10,
            "five_context_development_ready": data_ready,
            "critical_replay_check": replay_value,
            "passed": bool(utility and data_ready and replay_value["passed"])}


def route_for(stage: dict[str, Any], execution: bool, raw_ok: bool,
              prefixes_ok: bool, rounds: Sequence[dict[str, Any]],
              scientific: dict[str, Any]) -> str:
    if not execution:
        return stage["routes"]["execution_or_interface_fail"]
    if not raw_ok:
        return stage["routes"]["raw_integrity_fail"]
    if not prefixes_ok:
        return stage["routes"]["prefix_mismatch"]
    if len(rounds) != 2 or not all(row.get("passed") for row in rounds):
        return stage["routes"]["round_no_eligible_arm"]
    if not scientific.get("critical_replay_check", {}).get("passed"):
        return stage["routes"]["replay_fail"]
    if not scientific.get("teacher_utility_passed"):
        return stage["routes"]["round_no_eligible_arm"]
    if not scientific.get("five_context_development_ready"):
        return stage["routes"]["data_insufficient"]
    return stage["routes"]["pass"]


def execute(stage: dict[str, Any], runtime: dict[str, Any], cfg: Any,
            targets: dict[str, Any], parent: dict[str, Any], reference: dict[str, Any],
            source_revision: str, output: Path, storage_gate: dict[str, Any]) -> dict[str, Any]:
    isolation = z7.configure_run_root(cfg, output)
    rows: list[dict[str, Any]] = []
    round_values: list[dict[str, Any]] = []
    prefix_values: list[dict[str, Any]] = []
    selected_constructed = parent
    selected_row: dict[str, Any] | None = None
    reference_row = reference
    execution = True
    for round_index in FRESH_ROUNDS:
        streams = build_round_streams(stage, runtime, cfg, targets,
                                      selected_constructed, round_index)
        if not all(validate_stream(row, runtime, cfg, targets)["passed"] for row in streams):
            execution = False
            break
        decision = stage["fresh_rounds"][round_index]["decision_state_index"]
        round_rows = []
        for stream in streams:
            row = z7.execute_row(cfg, runtime, stream, reference_row,
                                 source_revision, output)
            rows.append(row); round_rows.append(row)
            prefix_values.append(z6.prefix_check(
                row, reference_row, decision + 1, decision, stage["semantic_artifacts"]))
            if not row.get("passed") and not z6.safe_stop(row, runtime):
                execution = False
                break
        if not execution:
            break
        value = z6.round_metrics(round_rows, runtime, round_index, cfg)
        round_values.append(value)
        if not value.get("passed"):
            break
        selected_arm = value["selected_arm_id"]
        selected_constructed = next(row for row in streams if row["arm_id"] == selected_arm)
        selected_row = next(row for row in round_rows if row["arm_id"] == selected_arm)
        reference_row = selected_row
    replay_row = None
    if len(round_values) == 2 and all(row.get("passed") for row in round_values):
        replay_stream = z6.critical_replay_stream(selected_constructed)
        replay_stream["round_index"] = 1
        replay_row = z7.execute_row(cfg, runtime, replay_stream, selected_row or {},
                                    source_revision, output)
        rows.append(replay_row)
        prefix_values.append(z6.prefix_check(
            replay_row, selected_row or {}, 78, 77, stage["semantic_artifacts"]))
        if not replay_row.get("passed") and not z6.safe_stop(replay_row, runtime):
            execution = False
    counters = {key: sum(int(row.get(key, 0)) for row in rows) for key in
                ("reset_calls", "advance_attempts", "plant_advance_gotsc_calls",
                 "verified_plant_advances")}
    if (len(rows) > 11 or counters["reset_calls"] > 11
            or counters["advance_attempts"] > 847
            or counters["plant_advance_gotsc_calls"] > 847
            or counters["verified_plant_advances"] > 847):
        execution = False
    prefixes_ok = bool(prefix_values and all(row.get("passed") for row in prefix_values))
    inventory = z6.z5.z3.z1.y1r1.y1.x1.raw_inventory(output, rows, stage)
    expected_files = 5 * sum(len(row.get("states", [])) for row in rows)
    raw_ok = bool(execution and not inventory["missing_required_artifacts"]
                  and inventory["required_artifact_files"] == expected_files)
    scientific = final_metrics(round_values, rows, stage, selected_row, replay_row)
    route = route_for(stage, execution, raw_ok, prefixes_ok, round_values, scientific)
    result = {"schema_version": SCHEMA, "source_revision": source_revision,
              "stage_config_sha256": CONFIG_SHA256,
              "passed": route == stage["routes"]["pass"], "route": route,
              "storage_gate": storage_gate, "run_root_isolation": isolation,
              "execution_integrity_passed": execution, "raw_integrity_passed": raw_ok,
              "fresh_prefix_checks": prefix_values, "fresh_round_metrics": round_values,
              "scientific_metrics": scientific,
              "selected_five_macro_sequence": ["f4", "b2f2", "f2b2",
                                               *scientific["selected_late_macro_sequence"]],
              "fresh_rollouts_completed": len(rows),
              "fresh_complete_rollouts": sum(bool(row.get("passed")) for row in rows),
              "fresh_guarded_safe_stops": sum(z6.safe_stop(row, runtime) for row in rows),
              **counters, **inventory, "models_fit_or_updated": 0,
              "calibration_or_holdout_records_read": 0,
              "compact_data_role": stage["data_use"],
              "claim_boundary": "Finite source-local late-root branch utility/support evidence only."}
    z6.z5.z3.z1.y1r1.y1.x1.write_new(output / "result.json", result)
    return result


def _failure_result(stage: dict[str, Any], source_revision: str, output: Path,
                    storage_gate: dict[str, Any], exc: Exception) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for item in sorted(output.glob("*.json")):
        if item.name in {"offline_preflight.json", "result.json",
                         "independent_raw_audit.json"}:
            continue
        try:
            row = load_json(item)
        except Exception:
            continue
        if "rollout_id" in row:
            rows.append(row)
    counters = {
        key: sum(int(row.get(key, 0)) for row in rows)
        for key in ("reset_calls", "advance_attempts",
                    "plant_advance_gotsc_calls", "verified_plant_advances")
    }
    try:
        inventory = z6.z5.z3.z1.y1r1.y1.x1.raw_inventory(output, rows, stage)
    except Exception as inventory_exc:
        inventory = {
            "required_artifact_files": 0,
            "required_artifact_bytes": 0,
            "required_artifact_inventory_sha256": None,
            "missing_required_artifacts": [
                f"FINALIZER:{type(inventory_exc).__name__}:{inventory_exc}"
            ],
        }
    return {
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "passed": False,
        "route": stage["routes"]["execution_or_interface_fail"],
        "failure": f"{type(exc).__name__}:{exc}",
        "storage_gate": storage_gate,
        "run_root_isolation": {
            "passed": True,
            "output": str(output.resolve()),
            "required_run_root": str((output / "rollouts").resolve()),
            "configured_run_root": str((output / "rollouts").resolve()),
            "historical_default_forbidden": True,
            "verified_before_runner_construction": True,
        },
        "fresh_rollouts_completed": len(rows),
        "fresh_complete_rollouts": sum(bool(row.get("passed")) for row in rows),
        **counters,
        **inventory,
        "models_fit_or_updated": 0,
        "calibration_or_holdout_records_read": 0,
        "claim_boundary": (
            "Best-effort classified ID2Z9 execution failure; "
            "no teacher-utility or action-basis verdict."
        ),
    }


def run(path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = inside(output, "ID2Z9 output")
    if output.exists():
        raise FileExistsError(str(output))
    stage, runtime, cfg, targets, parent, reference = load(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    storage_gate = z6.z5.z3.z1.y1r1.y1.x1.storage(stage, output)
    output.mkdir()
    preflight = offline(path, source_revision)
    z6.z5.z3.z1.y1r1.y1.x1.write_new(output / "offline_preflight.json", preflight)
    if not storage_gate["passed"] or not preflight["passed"]:
        route = stage["routes"]["storage_fail" if not storage_gate["passed"]
                                else "offline_or_input_fail"]
        result = {"schema_version": SCHEMA, "source_revision": source_revision,
                  "stage_config_sha256": CONFIG_SHA256, "passed": False,
                  "route": route, "storage_gate": storage_gate,
                  "reasons": preflight["failures"], "fresh_rollouts_completed": 0,
                  "reset_calls": 0, "advance_attempts": 0,
                  "plant_advance_gotsc_calls": 0, "verified_plant_advances": 0,
                  "models_fit_or_updated": 0, "calibration_or_holdout_records_read": 0}
        z6.z5.z3.z1.y1r1.y1.x1.write_new(output / "result.json", result)
        return result
    try:
        return execute(stage, runtime, cfg, targets, parent, reference,
                       source_revision, output, storage_gate)
    except Exception as exc:
        result = _failure_result(stage, source_revision, output, storage_gate, exc)
        if not (output / "result.json").exists():
            z6.z5.z3.z1.y1r1.y1.x1.write_new(output / "result.json", result)
        return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-config", type=Path, default=CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--offline-only", action="store_true")
    args = parser.parse_args(argv)
    if args.offline_only:
        result = offline(args.stage_config, args.source_revision)
    else:
        if args.output is None:
            parser.error("--output is required unless --offline-only")
        result = run(args.stage_config, args.source_revision, args.output)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
