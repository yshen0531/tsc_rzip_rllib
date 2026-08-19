#!/usr/bin/env python3
"""Run frozen ID-2Z12 signed B/F convex-allocation capture discriminator."""

from __future__ import annotations

import argparse
from decimal import Decimal
import json
import math
import sys
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_id2z11_bounded_capture_teacher as z11  # noqa: E402


z6 = z11.z6
z7 = z11.z7
io = z11.io
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z12_convex_allocation_capture.json"
CONFIG_SHA256 = "40c31d9ce3cc5924ed8c2a5cab8301437104900075a76e3df9e9687e66fa4ad2"
SCHEMA = "rgeo-zgeo-1ms-id2z12-convex-allocation-capture-result-v1"
ARM_IDS = ("hold4", "b4", "bf4", "f4", "pf4", "p4", "pu4", "u4", "bu4")


def inside(path: Path, label: str) -> Path:
    return z11.inside(path, label)


def load_json(path: Path) -> dict[str, Any]:
    return z11.load_json(path)


def _require(stage: dict[str, Any]) -> None:
    if z6.z5.base.sha256(CONFIG) != CONFIG_SHA256:
        raise z6._error("ID2Z12 config hash mismatch")
    canonical = load_json(CONFIG)
    if stage != canonical:
        raise z6._error("frozen ID2Z12 config changed")
    if [row["arm_id"] for row in stage["candidate_specs"]] != list(ARM_IDS):
        raise z6._error("candidate order changed")
    if stage["action_semantics"]["coefficient_hull"] != "abs(alpha_b)+abs(alpha_f)<=1":
        raise z6._error("allocation hull changed")


def _verify_evidence(stage: dict[str, Any]) -> dict[str, dict[str, Any]]:
    values: dict[str, dict[str, Any]] = {}
    for name, spec in stage["evidence"].items():
        path = inside(ROOT / spec["path"], name)
        if z6.z5.base.sha256(path) != spec["sha256"]:
            raise z6._error(f"evidence hash mismatch: {name}")
        values[name] = load_json(path) if path.suffix == ".json" else {}
    return values


def runtime_stage(stage: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    value = dict(source)
    value.update({
        "common_horizon_steps": 77,
        "common_terminal_state_index": 77,
        "maximum_rounds": 2,
        "rounds": [
            {"round_index": 0, "round_id": "root_state61",
             "decision_state_index": 61, "macro_last_issue": 64},
            {"round_index": 1, "round_id": "selected_state65",
             "decision_state_index": 65, "macro_last_issue": 68},
        ],
        "candidate_specs": list(stage["candidate_specs"]),
        "empirical_exploration": dict(stage["empirical_exploration"]),
        "measurement_gates": dict(stage["measurement_gates"]),
        "semantic_artifacts": list(stage["semantic_artifacts"]),
    })
    return value


def _planned_parent(z11_stage: dict[str, Any], cfg: Any,
                    targets: dict[str, Any], parent: dict[str, Any]) -> dict[str, Any]:
    roots = z11.build_matrix(z11_stage, cfg, targets, parent, 49, 0, "root")
    selected_root = next(row for row in roots if row["arm_id"] == "b8")
    mains = z11.build_matrix(z11_stage, cfg, targets, selected_root, 53, 1, "main")
    return next(row for row in mains if row["arm_id"] == "b4f4")


def _planned_matches_replay(planned: dict[str, Any], replay: dict[str, Any]) -> bool:
    return bool(
        replay.get("passed") is True
        and len(replay.get("states", [])) == 78
        and len(replay.get("actions", [])) == 77
        and [row.get("expected_card15_fields") for row in replay["actions"]]
        == [row.get("expected_card15_fields") for row in planned["actions"]]
        and [row.get("probe_virtual_action") for row in replay["actions"]]
        == [row.get("probe_virtual_action") for row in planned["actions"]]
    )


def load(path: Path = CONFIG) -> tuple[dict[str, Any], dict[str, Any], Any,
                                       dict[str, Any], dict[str, Any], dict[str, Any]]:
    path = inside(path, "ID2Z12 config")
    if path != CONFIG.resolve():
        raise z6._error("alternate ID2Z12 config forbidden")
    stage = load_json(path)
    _require(stage)
    evidence = _verify_evidence(stage)
    result = evidence["id2z11_result"]
    audit = evidence["id2z11_independent"]
    if (result.get("route") != stage["evidence"]["id2z11_result"]["required_route"]
            or result.get("passed") is not False
            or audit.get("audit_passed") is not True):
        raise z6._error("ID2Z11 source route mismatch")
    scientific = result.get("scientific_metrics", {})
    if (scientific.get("selected_root_arm_id") != "b8"
            or scientific.get("selected_main_arm_id") != "b4f4"
            or scientific.get("selected_path_replay_exact_passed") is not True):
        raise z6._error("ID2Z11 selected path changed")
    z11_stage, z11_runtime, cfg, targets, parent, _ = z11.load(
        ROOT / stage["evidence"]["id2z11_config"]["path"])
    planned = _planned_parent(z11_stage, cfg, targets, parent)
    replay = evidence["id2z11_critical_replay"]
    if not _planned_matches_replay(planned, replay):
        raise z6._error("ID2Z11 planned parent/replay mismatch")
    return stage, runtime_stage(stage, z11_runtime), cfg, targets, planned, replay


def _allocation_delta(q0: Any, targets: dict[str, Any], cfg: Any,
                      alpha_b: Decimal, alpha_f: Decimal, name: str) -> Any:
    if abs(alpha_b) + abs(alpha_f) > Decimal("1"):
        raise z6._error("allocation leaves exact coefficient hull")
    b = z6.z5.z3.z2._increment_target(
        q0, targets, {"coordinate": "p07:minus", "level_delta": 1}, cfg,
        f"{name}.b")
    f = z6.z5.z3.z2._increment_target(
        q0, targets, {"coordinate": "p03", "level_delta": 1}, cfg,
        f"{name}.f")
    fields: list[str] = []
    for q, bv, fv in zip(q0.card15_fields, b.card15_fields, f.card15_fields):
        qd = Decimal(q.strip())
        value = qd + alpha_b * (Decimal(bv.strip()) - qd) \
            + alpha_f * (Decimal(fv.strip()) - qd)
        fields.append(z6.z5.z3.z1.c1.format_number(float(value)))
    return z6.z5.z3.z1.c1.target_from_fields(fields, cfg, name)


def _virtual_step(current: Sequence[float], alpha_b: Decimal,
                  alpha_f: Decimal) -> list[float]:
    value = [float(v) for v in current]
    value[2] -= float(alpha_b)
    value[0] += float(alpha_f)
    return value


def build_stream(stage: dict[str, Any], cfg: Any, targets: dict[str, Any],
                 parent: dict[str, Any], decision: int, round_index: int,
                 namespace: str, spec: dict[str, Any]) -> dict[str, Any]:
    if len(parent.get("targets", [])) < decision:
        raise z6._error("parent prefix too short")
    arm_id = str(spec["arm_id"])
    rollout_id = f"{namespace}__{arm_id}"
    alpha_b = Decimal(str(spec["alpha_b"]))
    alpha_f = Decimal(str(spec["alpha_f"]))
    sequence = list(parent["targets"][:decision])
    virtual_rows = [list(row["probe_virtual_action"])
                    for row in parent["actions"][:decision]]
    current = sequence[-1]
    virtual = list(virtual_rows[-1])
    q0 = targets["q0"]
    delta = _allocation_delta(q0, targets, cfg, alpha_b, alpha_f,
                              f"id2z12.{rollout_id}.delta")
    for offset in range(int(stage["macro_issues"])):
        current = z6.z5.z3.z1.c1._translated_target(
            current, q0, delta, cfg, f"id2z12.{rollout_id}.{decision + offset}")
        virtual = _virtual_step(virtual, alpha_b, alpha_f)
        sequence.append(current)
        virtual_rows.append(list(virtual))
    while len(sequence) < int(stage["common_horizon_steps"]):
        sequence.append(current)
        virtual_rows.append(list(virtual))
    actions = z6.z5.z3.z1.c1._actions(sequence, cfg, rollout_id, virtual_rows)
    return {
        "rollout_id": rollout_id, "candidate_id": rollout_id,
        "arm_id": arm_id, "alpha_b": str(spec["alpha_b"]),
        "alpha_f": str(spec["alpha_f"]), "fit_weight": 0,
        "round_index": round_index,
        "round_id": "root_state61" if round_index == 0 else "selected_state65",
        "cell_id": rollout_id, "cell_kind": "convex_allocation_capture_branch",
        "context_id": f"round{round_index}_state{decision}_causal_prefix",
        "direction_id": "signed_bf_convex_allocation", "coordinate": "bf_diamond",
        "sign": None, "probe_issue_step": decision,
        "probe_duration_issues": int(stage["macro_issues"]),
        "non_nominal_issue_steps": list(range(decision, decision + 4)),
        "targets": sequence, "actions": actions,
    }


def build_matrix(stage: dict[str, Any], cfg: Any, targets: dict[str, Any],
                 parent: dict[str, Any], decision: int, round_index: int,
                 namespace: str) -> list[dict[str, Any]]:
    rows = [build_stream(stage, cfg, targets, parent, decision, round_index,
                         namespace, spec) for spec in stage["candidate_specs"]]
    if [row["arm_id"] for row in rows] != list(ARM_IDS):
        raise z6._error("allocation matrix order changed")
    return rows


def validate_stream(stream: dict[str, Any], stage: dict[str, Any], cfg: Any) -> dict[str, Any]:
    failures: list[str] = []
    actions = stream["actions"]
    decision = int(stream["probe_issue_step"])
    last = decision + int(stage["macro_issues"]) - 1
    horizon = int(stage["common_horizon_steps"])
    alpha_b = Decimal(str(stream["alpha_b"]))
    alpha_f = Decimal(str(stream["alpha_f"]))
    if abs(alpha_b) + abs(alpha_f) > Decimal("1"):
        failures.append("COEFFICIENT_HULL")
    if len(actions) != horizon or len(stream["targets"]) != horizon:
        failures.append("STREAM_DIMENSIONS")
    for issue, action in enumerate(actions):
        if (int(action["issue_step"]) != issue
                or int(action["effect_state_index"]) != issue + 1
                or float(action["maximum_issued_delta_a"]) > 0.3000000001):
            failures.append(f"ACTION_CONTRACT:{issue}")
    for issue in range(last + 1, horizon):
        if (actions[issue]["expected_card15_fields"]
                != actions[last]["expected_card15_fields"]
                or float(actions[issue]["maximum_issued_delta_a"]) != 0.0):
            failures.append(f"TAIL_HOLD:{issue}")
    headroom = z6._headroom(stream["targets"], cfg)
    if headroom < -1e-9:
        failures.append("ABSOLUTE_CURRENT_LIMIT")
    return {"rollout_id": stream["rollout_id"], "arm_id": stream["arm_id"],
            "minimum_absolute_current_headroom_a": headroom,
            "passed": not failures, "failures": list(dict.fromkeys(failures))}


def _metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    gates = stage["measurement_gates"]
    by_arm = {str(row.get("arm_id")): row for row in rows}
    source_row = next((row for row in rows if row.get("states")), None)
    terminal = [int(v) for v in gates["terminal_state_indices"]]
    values: list[dict[str, Any]] = []
    if source_row is None:
        return {"baseline_complete": False, "branch_metrics": values,
                "selected_arm_id": None, "passed": False}
    source = source_row["states"][0]
    source_ip = abs(float(source["ip_a"]))
    for arm in ARM_IDS:
        row = by_arm.get(arm)
        complete = bool(row and row.get("passed") and len(row.get("states", [])) == 78)
        if not complete:
            values.append({"arm_id": arm, "execution_status": "incomplete_or_safe_stop",
                           "observed_state_count": len(row.get("states", [])) if row else 0,
                           "safe_stop": bool(row and z6.safe_stop(row, stage)),
                           "capture_passed": False, "eligible": False})
            continue
        states = row["states"]
        distances = [z6._distance(states[i], source) for i in terminal]
        speeds = [z6._speed(states, i) for i in terminal]
        ipf = [abs(float(states[i]["ip_a"]) - float(source["ip_a"])) / source_ip
               for i in terminal]
        score = max(max(distances) / float(gates["maximum_capture_source_rz_distance_m"]),
                    max(speeds) / float(gates["maximum_capture_rz_step_speed_m_per_s"]),
                    max(ipf) / float(gates["maximum_capture_absolute_source_ip_fraction"]))
        capture = bool(max(distances) <= float(gates["maximum_capture_source_rz_distance_m"])
                       and max(speeds) <= float(gates["maximum_capture_rz_step_speed_m_per_s"])
                       and max(ipf) <= float(gates["maximum_capture_absolute_source_ip_fraction"]))
        values.append({
            "arm_id": arm, "alpha_b": row["alpha_b"], "alpha_f": row["alpha_f"],
            "execution_status": "complete", "terminal_state_indices": terminal,
            "terminal_source_rz_distance_m": distances,
            "terminal_rz_step_speed_m_per_s": speeds,
            "terminal_absolute_source_ip_fraction": ipf,
            "terminal_max_source_rz_distance_m": max(distances),
            "terminal_max_rz_step_speed_m_per_s": max(speeds),
            "terminal_max_absolute_source_ip_fraction": max(ipf),
            "terminal_worst_normalized_score": score,
            "capture_passed": capture, "eligible": False,
        })
    baseline = next((v for v in values if v["arm_id"] == "hold4"), None)
    baseline_complete = bool(baseline and baseline.get("execution_status") == "complete")
    nominated: list[dict[str, Any]] = []
    if baseline_complete:
        base_score = float(baseline["terminal_worst_normalized_score"])
        for value in values:
            if value["arm_id"] == "hold4" or value.get("execution_status") != "complete":
                continue
            improvement = base_score - float(value["terminal_worst_normalized_score"])
            value["score_improvement_over_hold"] = improvement
            value["eligible"] = bool(value["capture_passed"] or improvement >= float(
                gates["minimum_round_score_improvement_over_hold"]))
            if value["eligible"]:
                nominated.append(value)
    nominated.sort(key=lambda v: (
        not bool(v["capture_passed"]), float(v["terminal_worst_normalized_score"]),
        float(v["terminal_max_source_rz_distance_m"]),
        float(v["terminal_max_rz_step_speed_m_per_s"]),
        float(v["terminal_max_absolute_source_ip_fraction"]), str(v["arm_id"])))
    all_complete = all(v.get("execution_status") == "complete" for v in values)
    return {"baseline_complete": baseline_complete,
            "baseline_terminal_worst_normalized_score": (
                baseline.get("terminal_worst_normalized_score") if baseline else None),
            "branch_metrics": values,
            "nominated_arm_ids": [v["arm_id"] for v in nominated],
            "selected_arm_id": nominated[0]["arm_id"] if nominated else None,
            "selected_capture_passed": bool(nominated and nominated[0]["capture_passed"]),
            "all_branches_complete": all_complete,
            "passed": bool(baseline_complete and nominated and all_complete)}


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
                  "round_index": 1, "round_id": "critical_replay",
                  "cell_id": "critical_replay", "cell_kind": "capture_replay"})
    return value


def offline(path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    checks: list[dict[str, Any]] = []
    try:
        stage, _, cfg, targets, parent, _ = load(path)
        roots = build_matrix(stage, cfg, targets, parent, 61, 0, "root")
        for root in roots:
            a = validate_stream(root, stage, cfg)
            for main in build_matrix(stage, cfg, targets, root, 65, 1, "main"):
                b = validate_stream(main, stage, cfg)
                checks.append({"sequence": [root["arm_id"], main["arm_id"]],
                               "passed": bool(a["passed"] and b["passed"]),
                               "failures": list(dict.fromkeys(a["failures"] + b["failures"]))})
        if len(checks) != 81 or not all(v["passed"] for v in checks):
            failures.append("FULL_CONVEX_ALLOCATION_MATRIX_NOT_ADMISSIBLE")
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {"schema_version": "rgeo-zgeo-1ms-id2z12-offline-v1",
            "source_revision": source_revision, "stage_config_sha256": CONFIG_SHA256,
            "passed": not failures, "failures": failures,
            "static_root_main_sequence_count": len(checks),
            "static_root_main_sequences_passed": sum(v["passed"] for v in checks),
            "sequence_checks": checks, "reset_calls": 0, "advance_attempts": 0,
            "plant_advance_gotsc_calls": 0, "models_fit_or_updated": 0}


def route_for(stage: dict[str, Any], execution: bool, raw_ok: bool,
              prefixes_ok: bool, root: dict[str, Any], main: dict[str, Any],
              replay_ok: bool, capture: bool) -> str:
    if not execution:
        return stage["routes"]["execution_or_interface_fail"]
    if not raw_ok:
        return stage["routes"]["raw_integrity_fail"]
    if not prefixes_ok:
        return stage["routes"]["prefix_mismatch"]
    if not root.get("passed") or not main.get("passed"):
        return stage["routes"]["round_no_eligible_arm"]
    if not replay_ok:
        return stage["routes"]["replay_fail"]
    if not capture:
        return stage["routes"]["no_capture"]
    return stage["routes"]["pass"]


def execute(stage: dict[str, Any], runtime: dict[str, Any], cfg: Any,
            targets: dict[str, Any], parent: dict[str, Any], reference: dict[str, Any],
            source_revision: str, output: Path, storage_gate: dict[str, Any]) -> dict[str, Any]:
    isolation = z7.configure_run_root(cfg, output)
    rows: list[dict[str, Any]] = []
    prefixes: list[dict[str, Any]] = []
    execution = True
    root_streams = build_matrix(stage, cfg, targets, parent, 61, 0, "root")
    root_rows: list[dict[str, Any]] = []
    for stream in root_streams:
        if not validate_stream(stream, stage, cfg)["passed"]:
            execution = False
            break
        row = execute_row(cfg, runtime, stream, reference, source_revision, output)
        rows.append(row)
        root_rows.append(row)
        prefixes.append(z6.prefix_check(row, reference, 62, 61,
                                        stage["semantic_artifacts"]))
        if not row.get("passed") and not z6.safe_stop(row, runtime):
            execution = False
            break
    root_metrics = _metrics(root_rows, stage)
    root_arm = root_metrics.get("selected_arm_id")
    root_stream = next((v for v in root_streams if v["arm_id"] == root_arm), None)
    root_row = next((v for v in root_rows if v.get("arm_id") == root_arm), None)

    main_streams: list[dict[str, Any]] = []
    main_rows: list[dict[str, Any]] = []
    main_metrics: dict[str, Any] = {"passed": False}
    if execution and root_metrics.get("passed") and root_stream and root_row:
        main_streams = build_matrix(stage, cfg, targets, root_stream, 65, 1, "main")
        for stream in main_streams:
            if not validate_stream(stream, stage, cfg)["passed"]:
                execution = False
                break
            row = execute_row(cfg, runtime, stream, root_row,
                              source_revision, output)
            rows.append(row)
            main_rows.append(row)
            prefixes.append(z6.prefix_check(row, root_row, 66, 65,
                                            stage["semantic_artifacts"]))
            if not row.get("passed") and not z6.safe_stop(row, runtime):
                execution = False
                break
        main_metrics = _metrics(main_rows, stage)
    main_arm = main_metrics.get("selected_arm_id")
    main_stream = next((v for v in main_streams if v["arm_id"] == main_arm), None)
    main_row = next((v for v in main_rows if v.get("arm_id") == main_arm), None)

    replay_ok = False
    if execution and main_stream and main_row:
        replay = replay_stream(main_stream)
        replay_row = execute_row(cfg, runtime, replay, main_row,
                                 source_revision, output)
        rows.append(replay_row)
        prefixes.append(z6.prefix_check(replay_row, main_row, 78, 77,
                                        stage["semantic_artifacts"]))
        replay_ok = z6.replay_check(main_row, replay_row,
                                    stage["semantic_artifacts"])["passed"]
        if not replay_row.get("passed") and not z6.safe_stop(replay_row, runtime):
            execution = False

    counters = {key: sum(int(row.get(key, 0)) for row in rows) for key in
                ("reset_calls", "advance_attempts", "plant_advance_gotsc_calls",
                 "verified_plant_advances")}
    if (len(rows) > int(stage["maximum_rollouts"])
            or any(counters[key] > int(stage["maximum_advance_attempts"])
                   for key in counters)):
        execution = False
    prefixes_ok = bool(prefixes and all(v.get("passed") for v in prefixes))
    inventory = io.raw_inventory(output, rows, stage)
    expected_files = 5 * sum(len(row.get("states", [])) for row in rows)
    raw_ok = bool(execution and not inventory["missing_required_artifacts"]
                  and inventory["required_artifact_files"] == expected_files)
    selected_metric = next((v for v in main_metrics.get("branch_metrics", [])
                            if v.get("arm_id") == main_arm), None)
    capture = bool(selected_metric and selected_metric.get("capture_passed"))
    route = route_for(stage, execution, raw_ok, prefixes_ok, root_metrics,
                      main_metrics, replay_ok, capture)
    scientific = {
        "root_metrics": root_metrics, "main_metrics": main_metrics,
        "selected_root_arm_id": root_arm, "selected_main_arm_id": main_arm,
        "selected_path_capture_passed": capture,
        "selected_path_replay_exact_passed": replay_ok,
    }
    result = {"schema_version": SCHEMA, "source_revision": source_revision,
              "stage_config_sha256": CONFIG_SHA256,
              "passed": route == stage["routes"]["pass"], "route": route,
              "storage_gate": storage_gate, "run_root_isolation": isolation,
              "execution_integrity_passed": execution,
              "raw_integrity_passed": raw_ok, "prefix_checks": prefixes,
              "scientific_metrics": scientific,
              "rollouts_completed": len(rows),
              "complete_rollouts": sum(bool(v.get("passed")) for v in rows),
              "guarded_safe_stops": sum(z6.safe_stop(v, runtime) for v in rows),
              **counters, **inventory, "models_fit_or_updated": 0,
              "calibration_or_holdout_records_read": 0,
              "claim_boundary": "Finite signed B/F convex-allocation authority evidence only."}
    io.write_new(output / "result.json", result)
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
    output = inside(output, "ID2Z12 output")
    if output.exists():
        raise FileExistsError(str(output))
    stage, runtime, cfg, targets, parent, reference = load(path)
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
        return execute(stage, runtime, cfg, targets, parent, reference,
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
        result = offline(args.stage_config, args.source_revision)
    else:
        if args.output is None:
            parser.error("--output is required unless --offline-only")
        result = run(args.stage_config, args.source_revision, args.output)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
