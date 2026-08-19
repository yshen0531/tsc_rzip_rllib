#!/usr/bin/env python3
"""Run the frozen ID-2Z15 takeover headroom-nominal frontier."""

from __future__ import annotations

import argparse
from decimal import Decimal
import json
from pathlib import Path
import sys
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_id2z14_early_remaining_basis_capture as z14  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2z12_convex_allocation_capture as z12  # noqa: E402


z6, z7, io = z14.z6, z14.z7, z14.io
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z15_headroom_nominal_frontier.json"
CONFIG_SHA256 = "ca04d4060bdb6fa1552ecf67044857d22b67e5f965ed6fa2de14fe5987ff73ea"
SCHEMA = "rgeo-zgeo-1ms-id2z15-headroom-nominal-frontier-result-v1"
ARM_IDS = ("q0", "f25", "f50", "f75", "f100", "duty50")


def inside(path: Path, label: str) -> Path:
    return z14.inside(path, label)


def load_json(path: Path) -> dict[str, Any]:
    return z14.load_json(path)


def _require(stage: dict[str, Any]) -> None:
    if io.sha256(CONFIG) != CONFIG_SHA256:
        raise z6._error("ID2Z15 config hash mismatch")
    if stage != load_json(CONFIG):
        raise z6._error("frozen ID2Z15 config changed")
    if [row.get("arm_id") for row in stage.get("candidate_specs", [])] != list(ARM_IDS):
        raise z6._error("candidate order changed")
    if [row.get("alpha_f") for row in stage["candidate_specs"]] != [0.0, .25, .5, .75, 1.0, .5]:
        raise z6._error("fraction frontier changed")
    if [row.get("mode") for row in stage["candidate_specs"]] != [
            "constant_fraction"] * 5 + ["odd_full_f_even_hold"]:
        raise z6._error("nominal modes changed")
    exact = {
        "takeover_time_ms": 1100, "control_period_ms": 1,
        "first_increment_issue_step": 1, "last_increment_issue_step": 31,
        "common_horizon_steps": 48, "common_terminal_state_index": 48,
        "maximum_branches": 6, "maximum_replay_rollouts": 1,
        "maximum_rollouts": 7, "maximum_reset_calls": 7,
        "maximum_advance_attempts": 336, "maximum_gotsc_calls": 336,
        "maximum_verified_plant_advances": 336,
        "maximum_retained_states": 343,
        "required_artifact_files_if_all_complete": 1715,
        "models_fit_or_updated": 0,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise z6._error(f"frozen field changed: {key}")


def _verify_evidence(stage: dict[str, Any]) -> dict[str, dict[str, Any]]:
    values: dict[str, dict[str, Any]] = {}
    for name, spec in stage["evidence"].items():
        path = inside(ROOT / spec["path"], name)
        if io.sha256(path) != spec["sha256"]:
            raise z6._error(f"evidence hash mismatch: {name}")
        values[name] = load_json(path) if path.suffix == ".json" else {}
    return values


def runtime_stage(stage: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    value = dict(source)
    value.update({
        "common_horizon_steps": 48,
        "common_terminal_state_index": 48,
        "maximum_rounds": 1,
        "rounds": [{"round_index": 0, "round_id": "canonical_source",
                    "decision_state_index": 0, "macro_last_issue": 47}],
        "candidate_specs": list(stage["candidate_specs"]),
        "empirical_exploration": dict(stage["empirical_exploration"]),
        "measurement_gates": dict(stage["measurement_gates"]),
        "semantic_artifacts": list(stage["semantic_artifacts"]),
    })
    return value


def load(path: Path = CONFIG) -> tuple[dict[str, Any], dict[str, Any], Any,
                                       dict[str, Any], dict[str, Any]]:
    path = inside(path, "ID2Z15 config")
    if path != CONFIG.resolve():
        raise z6._error("alternate ID2Z15 config forbidden")
    stage = load_json(path)
    _require(stage)
    evidence = _verify_evidence(stage)
    result = evidence["id2z14_result"]
    audit = evidence["id2z14_independent"]
    if (result.get("route") != stage["evidence"]["id2z14_result"]["required_route"]
            or result.get("passed") is not False
            or audit.get("audit_passed") is not True
            or audit.get("recomputed_route") != result.get("route")):
        raise z6._error("ID2Z14 closing evidence mismatch")
    _, base_runtime, cfg, targets, _, source_reference = z14.load(
        ROOT / stage["evidence"]["id2z14_config"]["path"])
    if (len(source_reference.get("states", [])) < 1
            or source_reference.get("passed") is not True):
        raise z6._error("canonical source reference missing")
    return stage, runtime_stage(stage, base_runtime), cfg, targets, source_reference


def _increment(q0: Any, targets: dict[str, Any], cfg: Any,
               alpha_f: Decimal, name: str) -> Any:
    return z12._allocation_delta(q0, targets, cfg, Decimal("0"), alpha_f, name)


def build_stream(stage: dict[str, Any], cfg: Any, targets: dict[str, Any],
                 spec: dict[str, Any]) -> dict[str, Any]:
    arm_id = str(spec["arm_id"])
    rollout_id = f"branch__{arm_id}"
    mode = str(spec["mode"])
    alpha = Decimal(str(spec["alpha_f"]))
    horizon = int(stage["common_horizon_steps"])
    q0 = targets["q0"]
    current = q0
    level = Decimal("0")
    sequence: list[Any] = []
    virtual_rows: list[list[float]] = []
    for issue in range(horizon):
        applied = Decimal("0")
        if 1 <= issue <= 31:
            if mode == "constant_fraction":
                applied = alpha
            elif mode == "odd_full_f_even_hold":
                applied = Decimal("1") if issue % 2 == 1 else Decimal("0")
            else:
                raise z6._error(f"unknown mode: {mode}")
        if applied:
            delta = _increment(q0, targets, cfg, applied,
                               f"id2z15.{rollout_id}.issue{issue}.delta")
            current = z6.z5.z3.z1.c1._translated_target(
                current, q0, delta, cfg, f"id2z15.{rollout_id}.issue{issue}.target")
            level += applied
        sequence.append(current)
        virtual_rows.append([float(level), 0.0, 0.0, 0.0, 0.0])
    actions = z6.z5.z3.z1.c1._actions(sequence, cfg, rollout_id, virtual_rows)
    return {
        "rollout_id": rollout_id, "candidate_id": rollout_id,
        "arm_id": arm_id, "mode": mode, "alpha_f": str(spec["alpha_f"]),
        "attained_f_level": str(level), "fit_weight": 0,
        "round_index": 0, "round_id": "canonical_source",
        "cell_id": rollout_id, "cell_kind": "headroom_nominal_frontier_branch",
        "context_id": "canonical_1100ms_source",
        "direction_id": "fractional_p03_forward_nominal",
        "coordinate": "p03_forward_fraction_or_duty", "sign": None,
        "probe_issue_step": 1, "probe_duration_issues": 31,
        "non_nominal_issue_steps": list(range(1, 32)),
        "targets": sequence, "actions": actions,
    }


def build_matrix(stage: dict[str, Any], cfg: Any,
                 targets: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [build_stream(stage, cfg, targets, spec)
            for spec in stage["candidate_specs"]]
    if [row["arm_id"] for row in rows] != list(ARM_IDS):
        raise z6._error("candidate matrix order changed")
    return rows


def validate_stream(stream: dict[str, Any], stage: dict[str, Any], cfg: Any) -> dict[str, Any]:
    failures: list[str] = []
    actions = stream["actions"]
    horizon = int(stage["common_horizon_steps"])
    if len(actions) != horizon or len(stream["targets"]) != horizon:
        failures.append("STREAM_DIMENSIONS")
    for issue, action in enumerate(actions):
        if (int(action["issue_step"]) != issue
                or int(action["effect_state_index"]) != issue + 1
                or float(action["maximum_issued_delta_a"]) > .3000000001):
            failures.append(f"ACTION_CONTRACT:{issue}")
    for issue in range(32, horizon):
        if (actions[issue]["expected_card15_fields"]
                != actions[31]["expected_card15_fields"]
                or float(actions[issue]["maximum_issued_delta_a"]) != 0.0):
            failures.append(f"TAIL_HOLD:{issue}")
    if stream["arm_id"] == "duty50":
        for issue in range(1, 32):
            delta = float(actions[issue]["maximum_issued_delta_a"])
            if (issue % 2 == 1 and delta <= 0.0) or (issue % 2 == 0 and delta != 0.0):
                failures.append(f"DUTY_PARITY:{issue}")
    if stream["arm_id"] == "q0" and any(
            float(action["maximum_issued_delta_a"]) != 0.0 for action in actions):
        failures.append("Q0_NOT_CONSTANT")
    headroom = z6._headroom(stream["targets"], cfg)
    if headroom < -1e-9:
        failures.append("ABSOLUTE_CURRENT_LIMIT")
    return {"rollout_id": stream["rollout_id"], "arm_id": stream["arm_id"],
            "attained_f_level": stream["attained_f_level"],
            "minimum_absolute_current_headroom_a": headroom,
            "passed": not failures, "failures": list(dict.fromkeys(failures))}


def _metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    gates = stage["measurement_gates"]
    by_arm = {str(row.get("arm_id")): row for row in rows}
    expected_states = int(stage["common_horizon_steps"]) + 1
    terminal = [int(value) for value in gates["terminal_state_indices"]]
    source_row = next((row for row in rows if row.get("states")), None)
    if source_row is None:
        return {"frontier_complete": False, "branch_metrics": [],
                "selected_arm_id": None, "passed": False}
    source = source_row["states"][0]
    source_ip = abs(float(source["ip_a"]))
    dcap = float(gates["maximum_capture_source_rz_distance_m"])
    vcap = float(gates["maximum_capture_rz_step_speed_m_per_s"])
    icap = float(gates["maximum_capture_absolute_source_ip_fraction"])
    values: list[dict[str, Any]] = []
    for arm in ARM_IDS:
        row = by_arm.get(arm)
        complete = bool(row and row.get("passed")
                        and len(row.get("states", [])) == expected_states)
        if not complete:
            values.append({"arm_id": arm, "execution_status": "incomplete",
                           "capture_passed": False, "headroom_development_passed": False})
            continue
        states = row["states"]
        distances = [z6._distance(states[index], source) for index in terminal]
        speeds = [z6._speed(states, index) for index in terminal]
        ipf = [abs(float(states[index]["ip_a"]) - float(source["ip_a"])) / source_ip
               for index in terminal]
        score = max(max(distances) / dcap, max(speeds) / vcap, max(ipf) / icap)
        capture = bool(max(distances) <= dcap and max(speeds) <= vcap and max(ipf) <= icap)
        development = bool(
            max(distances) <= float(gates["maximum_headroom_development_source_rz_distance_m"])
            and max(speeds) <= float(gates["maximum_headroom_development_rz_step_speed_m_per_s"])
            and max(ipf) <= float(gates["maximum_headroom_development_absolute_source_ip_fraction"]))
        values.append({
            "arm_id": arm, "execution_status": "complete",
            "terminal_state_indices": terminal,
            "terminal_source_rz_distance_m": distances,
            "terminal_rz_step_speed_m_per_s": speeds,
            "terminal_absolute_source_ip_fraction": ipf,
            "terminal_max_source_rz_distance_m": max(distances),
            "terminal_max_rz_step_speed_m_per_s": max(speeds),
            "terminal_max_absolute_source_ip_fraction": max(ipf),
            "terminal_worst_normalized_score": score,
            "capture_passed": capture,
            "headroom_development_passed": development,
        })
    complete = all(value["execution_status"] == "complete" for value in values)
    ranked = [value for value in values if value["execution_status"] == "complete"]
    ranked.sort(key=lambda value: (
        not bool(value["capture_passed"]),
        float(value["terminal_worst_normalized_score"]), str(value["arm_id"])))
    selected = ranked[0] if complete and ranked else None
    by_metric = {value["arm_id"]: value for value in values}
    q0_score = by_metric.get("q0", {}).get("terminal_worst_normalized_score")
    f100_score = by_metric.get("f100", {}).get("terminal_worst_normalized_score")
    improvement_q0 = (float(q0_score) - float(selected["terminal_worst_normalized_score"])
                      if selected and q0_score is not None else None)
    improvement_f100 = (float(f100_score) - float(selected["terminal_worst_normalized_score"])
                        if selected and f100_score is not None else None)
    threshold = float(gates["minimum_headroom_score_improvement_against_both_endpoints"])
    headroom = bool(
        selected and selected["arm_id"] in gates["headroom_arm_ids"]
        and selected["headroom_development_passed"]
        and improvement_q0 is not None and improvement_q0 >= threshold
        and improvement_f100 is not None and improvement_f100 >= threshold)
    return {
        "frontier_complete": complete, "branch_metrics": values,
        "selected_arm_id": selected["arm_id"] if selected else None,
        "selected_capture_passed": bool(selected and selected["capture_passed"]),
        "selected_headroom_development_passed": headroom,
        "selected_score_improvement_over_q0": improvement_q0,
        "selected_score_improvement_over_f100": improvement_f100,
        "passed": bool(complete and selected),
    }


def execute_row(cfg: Any, runtime: dict[str, Any], stream: dict[str, Any],
                reference: dict[str, Any], source_revision: str,
                output: Path, *, runner_cls: type | None = None) -> dict[str, Any]:
    if Path(cfg.run_root).resolve() != (output / "rollouts").resolve():
        raise z6._error("run root isolation failed")
    row = z6.one_rollout(cfg, runtime, stream,
                         z6._reference(reference, len(reference.get("states", []))),
                         runner_cls=runner_cls)
    row.update({"schema_version": SCHEMA, "source_revision": source_revision})
    io.write_new(output / f"{stream['rollout_id']}.json", row)
    return row


def replay_stream(selected: dict[str, Any]) -> dict[str, Any]:
    value = dict(selected)
    value.update({"rollout_id": "critical_replay", "candidate_id": "critical_replay",
                  "arm_id": "critical_replay", "fit_weight": 0,
                  "round_id": "critical_replay", "cell_id": "critical_replay",
                  "cell_kind": "nominal_frontier_replay"})
    return value


def offline(path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    checks: list[dict[str, Any]] = []
    try:
        stage, _, cfg, targets, _ = load(path)
        for stream in build_matrix(stage, cfg, targets):
            checks.append(validate_stream(stream, stage, cfg))
        if len(checks) != 6 or not all(value["passed"] for value in checks):
            failures.append("FULL_ACTION_MATRIX_NOT_ADMISSIBLE")
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {"schema_version": "rgeo-zgeo-1ms-id2z15-offline-v1",
            "source_revision": source_revision, "stage_config_sha256": CONFIG_SHA256,
            "passed": not failures, "failures": failures,
            "static_sequence_count": len(checks),
            "static_sequences_passed": sum(value["passed"] for value in checks),
            "sequence_checks": checks, "reset_calls": 0, "advance_attempts": 0,
            "plant_advance_gotsc_calls": 0, "models_fit_or_updated": 0}


def route_for(stage: dict[str, Any], execution: bool, raw_ok: bool,
              prefixes_ok: bool, metrics: dict[str, Any], replay_ok: bool) -> str:
    if not execution:
        return stage["routes"]["execution_or_interface_fail"]
    if not raw_ok:
        return stage["routes"]["raw_integrity_fail"]
    if not prefixes_ok:
        return stage["routes"]["prefix_mismatch"]
    if not metrics.get("frontier_complete"):
        return stage["routes"]["frontier_incomplete"]
    if not replay_ok:
        return stage["routes"]["replay_fail"]
    if metrics.get("selected_capture_passed"):
        return stage["routes"]["capture_pass"]
    if metrics.get("selected_headroom_development_passed"):
        return stage["routes"]["headroom_pass"]
    return stage["routes"]["no_useful_nominal"]


def execute(stage: dict[str, Any], runtime: dict[str, Any], cfg: Any,
            targets: dict[str, Any], reference: dict[str, Any],
            source_revision: str, output: Path, storage_gate: dict[str, Any]) -> dict[str, Any]:
    isolation = z7.configure_run_root(cfg, output)
    streams = build_matrix(stage, cfg, targets)
    rows: list[dict[str, Any]] = []
    branches: list[dict[str, Any]] = []
    prefixes: list[dict[str, Any]] = []
    execution = True
    for stream in streams:
        if not validate_stream(stream, stage, cfg)["passed"]:
            execution = False
            break
        row = execute_row(cfg, runtime, stream, reference, source_revision, output)
        rows.append(row)
        branches.append(row)
        prefixes.append(z6.prefix_check(row, reference, 1, 0,
                                        stage["semantic_artifacts"]))
        if not row.get("passed") and not z6.safe_stop(row, runtime):
            execution = False
            break
    metrics = _metrics(branches, stage)
    selected_arm = metrics.get("selected_arm_id")
    selected_stream = next((row for row in streams if row["arm_id"] == selected_arm), None)
    selected_row = next((row for row in branches if row.get("arm_id") == selected_arm), None)
    replay_ok = False
    if execution and metrics.get("frontier_complete") and selected_stream and selected_row:
        replay = execute_row(cfg, runtime, replay_stream(selected_stream), selected_row,
                             source_revision, output)
        rows.append(replay)
        prefixes.append(z6.prefix_check(replay, selected_row, 49, 48,
                                        stage["semantic_artifacts"]))
        replay_ok = z6.replay_check(selected_row, replay,
                                    stage["semantic_artifacts"])["passed"]
        if not replay.get("passed"):
            execution = False
    counters = {key: sum(int(row.get(key, 0)) for row in rows) for key in
                ("reset_calls", "advance_attempts", "plant_advance_gotsc_calls",
                 "verified_plant_advances")}
    if len(rows) > 7 or any(counters[key] > 336 for key in counters):
        execution = False
    prefixes_ok = bool(prefixes and all(value.get("passed") for value in prefixes))
    inventory = io.raw_inventory(output, rows, stage)
    expected_files = 5 * sum(len(row.get("states", [])) for row in rows)
    raw_ok = bool(execution and not inventory["missing_required_artifacts"]
                  and inventory["required_artifact_files"] == expected_files)
    route = route_for(stage, execution, raw_ok, prefixes_ok, metrics, replay_ok)
    positive = {stage["routes"]["capture_pass"], stage["routes"]["headroom_pass"]}
    scientific = {"frontier_metrics": metrics,
                  "selected_arm_id": selected_arm,
                  "selected_capture_passed": metrics.get("selected_capture_passed", False),
                  "selected_headroom_development_passed": metrics.get(
                      "selected_headroom_development_passed", False),
                  "selected_replay_exact_passed": replay_ok}
    result = {"schema_version": SCHEMA, "source_revision": source_revision,
              "stage_config_sha256": CONFIG_SHA256, "passed": route in positive,
              "route": route, "storage_gate": storage_gate,
              "run_root_isolation": isolation, "execution_integrity_passed": execution,
              "raw_integrity_passed": raw_ok, "prefix_checks": prefixes,
              "scientific_metrics": scientific, "rollouts_completed": len(rows),
              "complete_rollouts": sum(bool(row.get("passed")) for row in rows),
              "guarded_safe_stops": sum(z6.safe_stop(row, runtime) for row in rows),
              **counters, **inventory, "models_fit_or_updated": 0,
              "calibration_or_holdout_records_read": 0,
              "claim_boundary": stage["claim_boundary"]}
    io.write_new(output / "result.json", result)
    return result


def _failure_result(stage: dict[str, Any], source_revision: str, output: Path,
                    storage_gate: dict[str, Any], exc: Exception) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for item in sorted(output.glob("*.json")):
        if item.name in {"offline_preflight.json", "result.json", "independent_raw_audit.json"}:
            continue
        try:
            row = load_json(item)
        except Exception:
            continue
        if "rollout_id" in row:
            rows.append(row)
    counters = {key: sum(int(row.get(key, 0)) for row in rows) for key in
                ("reset_calls", "advance_attempts", "plant_advance_gotsc_calls",
                 "verified_plant_advances")}
    try:
        inventory = io.raw_inventory(output, rows, stage)
    except Exception as inv_exc:
        inventory = {"required_artifact_files": 0, "required_artifact_bytes": 0,
                     "required_artifact_inventory_sha256": None,
                     "missing_required_artifacts": [
                         f"FINALIZER:{type(inv_exc).__name__}:{inv_exc}"]}
    return {"schema_version": SCHEMA, "source_revision": source_revision,
            "stage_config_sha256": CONFIG_SHA256, "passed": False,
            "route": stage["routes"]["execution_or_interface_fail"],
            "failure": f"{type(exc).__name__}:{exc}", "storage_gate": storage_gate,
            "rollouts_completed": len(rows), **counters, **inventory,
            "models_fit_or_updated": 0, "calibration_or_holdout_records_read": 0,
            "claim_boundary": "Best-effort classified execution failure; no plant verdict."}


def run(path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = inside(output, "ID2Z15 output")
    if output.exists():
        raise FileExistsError(str(output))
    stage, runtime, cfg, targets, reference = load(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    storage_gate = io.storage(stage, output)
    output.mkdir()
    preflight = offline(path, source_revision)
    io.write_new(output / "offline_preflight.json", preflight)
    if not storage_gate["passed"] or not preflight["passed"]:
        route = stage["routes"]["storage_fail" if not storage_gate["passed"]
                                else "offline_or_input_fail"]
        result = {"schema_version": SCHEMA, "source_revision": source_revision,
                  "stage_config_sha256": CONFIG_SHA256, "passed": False,
                  "route": route, "storage_gate": storage_gate,
                  "reasons": preflight["failures"], "rollouts_completed": 0,
                  "reset_calls": 0, "advance_attempts": 0,
                  "plant_advance_gotsc_calls": 0, "verified_plant_advances": 0,
                  "models_fit_or_updated": 0, "calibration_or_holdout_records_read": 0}
        io.write_new(output / "result.json", result)
        return result
    try:
        return execute(stage, runtime, cfg, targets, reference,
                       source_revision, output, storage_gate)
    except Exception as exc:
        result = _failure_result(stage, source_revision, output, storage_gate, exc)
        if not (output / "result.json").exists():
            io.write_new(output / "result.json", result)
        return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-config", type=Path, default=CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--offline-only", action="store_true")
    args = parser.parse_args(argv)
    if args.offline_only:
        value = offline(args.stage_config, args.source_revision)
        print(json.dumps(value, indent=2, sort_keys=True, allow_nan=False))
        return 0 if value["passed"] else 2
    if args.output is None:
        parser.error("--output is required unless --offline-only")
    value = run(args.stage_config, args.source_revision, args.output)
    print(json.dumps(value, indent=2, sort_keys=True, allow_nan=False))
    return 0 if value["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
