#!/usr/bin/env python3
"""Run frozen ID-2Z11 bounded exact-TSC capture teacher."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_id2z9_late_root_branch_utility_support as z9  # noqa: E402


z7 = z9.z7
z6 = z9.z6
io = z6.z5.z3.z1.y1r1.y1.x1
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z11_bounded_capture_teacher.json"
CONFIG_SHA256 = "bbd9075f1ca47740a04779e3407856125bf235b5f0a80fc909a409465b13aafe"
SCHEMA = "rgeo-zgeo-1ms-id2z11-bounded-capture-teacher-result-v1"
ARM_IDS = ("h8", "b8", "f8", "u4h4", "p4h4", "b4f4", "f4b4")


def inside(path: Path, label: str) -> Path:
    return z9.inside(path, label)


def load_json(path: Path) -> dict[str, Any]:
    return z9.load_json(path)


def _require(stage: dict[str, Any]) -> None:
    if z6.z5.base.sha256(CONFIG) != CONFIG_SHA256:
        raise z6._error("ID2Z11 config hash mismatch")
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2z11-bounded-capture-teacher-v1",
        "identity": "rgeo-zgeo-1ms-id2z11-bounded-capture-teacher-v1",
        "stage": "ID-2Z11", "takeover_time_ms": 1100,
        "control_period_ms": 1, "root_decision_state_index": 49,
        "second_decision_state_index": 53, "root_commit_issues": 4,
        "second_commit_issues": 8, "common_horizon_steps": 77,
        "common_terminal_state_index": 77, "maximum_root_branches": 7,
        "maximum_main_second_branches": 7,
        "maximum_alternate_support_branches": 2,
        "maximum_replay_rollouts": 1, "maximum_rollouts": 17,
        "maximum_reset_calls": 17, "maximum_advance_attempts": 1309,
        "maximum_gotsc_calls": 1309,
        "maximum_verified_plant_advances": 1309,
        "maximum_retained_states": 1326,
        "required_artifact_files_if_all_complete": 6630,
        "retry_after_any_advance_attempt": "forbidden",
        "models_fit_or_updated": 0,
    }
    for key, value in exact.items():
        if stage.get(key) != value:
            raise z6._error(f"frozen field changed: {key}")
    expected = [
        {"arm_id": "h8", "tokens": "HHHHHHHH"},
        {"arm_id": "b8", "tokens": "BBBBBBBB"},
        {"arm_id": "f8", "tokens": "FFFFFFFF"},
        {"arm_id": "u4h4", "tokens": "UUUUHHHH"},
        {"arm_id": "p4h4", "tokens": "PPPPHHHH"},
        {"arm_id": "b4f4", "tokens": "BBBBFFFF"},
        {"arm_id": "f4b4", "tokens": "FFFFBBBB"},
    ]
    if stage.get("candidate_specs") != expected:
        raise z6._error("candidate matrix changed")
    if stage.get("alternate_history_rule") != {
            "if_main_root_committed_tokens_equal": "BBBB",
            "alternate_committed_tokens": "FFFF",
            "otherwise_alternate_committed_tokens": "BBBB",
            "support_arms": ["h8", "selected_main_second_arm"]}:
        raise z6._error("alternate history rule changed")
    if stage.get("semantic_artifacts") != [
            "inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv"]:
        raise z6._error("semantic artifacts changed")
    if stage.get("diagnostic_artifacts") != ["sprsina"]:
        raise z6._error("diagnostic artifacts changed")


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
        "maximum_rounds": 3,
        "rounds": [
            {"round_index": 0, "round_id": "root_state49",
             "decision_state_index": 49, "macro_last_issue": 56},
            {"round_index": 1, "round_id": "main_state53",
             "decision_state_index": 53, "macro_last_issue": 60},
            {"round_index": 2, "round_id": "alternate_state53",
             "decision_state_index": 53, "macro_last_issue": 60},
        ],
        "candidate_specs": list(stage["candidate_specs"]),
        "empirical_exploration": dict(stage["empirical_exploration"]),
        "measurement_gates": dict(stage["measurement_gates"]),
        "semantic_artifacts": list(stage["semantic_artifacts"]),
    })
    return value


def load(path: Path = CONFIG) -> tuple[dict[str, Any], dict[str, Any], Any,
                                       dict[str, Any], dict[str, Any], dict[str, Any]]:
    path = inside(path, "ID2Z11 config")
    if path != CONFIG.resolve():
        raise z6._error("alternate ID2Z11 config forbidden")
    stage = load_json(path)
    _require(stage)
    evidence = _verify_evidence(stage)
    if (evidence["id2z9_result"].get("route")
            != stage["evidence"]["id2z9_result"]["required_route"]
            or evidence["id2z9_result"].get("passed") is not True
            or evidence["id2z9_independent"].get("audit_passed") is not True
            or evidence["id2z10_result"].get("route")
            != stage["evidence"]["id2z10_result"]["required_route"]
            or evidence["id2z10_result"].get("passed") is not False
            or evidence["id2z10_audit"].get("audit_passed") is not True):
        raise z6._error("source route mismatch")
    z7_stage, z6_stage, cfg, targets, _, _, _, _, _ = z7.load(
        ROOT / stage["evidence"]["id2z7_config"]["path"])
    _, cfg2, targets2, root_reference, root_parent = z6.load(
        ROOT / z7_stage["evidence"]["id2z6_config"]["path"])
    if cfg is not cfg2 and cfg.__dict__ != cfg2.__dict__:
        raise z6._error("source config reconstruction mismatch")
    if set(targets) != set(targets2):
        raise z6._error("target reconstruction mismatch")
    replay = evidence["id2z9_critical_replay"]
    if (replay.get("passed") is not True or len(replay.get("states", [])) != 78
            or len(replay.get("actions", [])) != 77):
        raise z6._error("ID2Z9 replay shape changed")
    prefix = z6.prefix_check(replay, root_reference, 50, 49,
                             stage["semantic_artifacts"])
    if not prefix.get("passed"):
        raise z6._error("state49 source prefix mismatch")
    return stage, runtime_stage(stage, z6_stage), cfg, targets, root_parent, replay


def _apply_token(current: Any, virtual: Sequence[float], token: str,
                 q0: Any, targets: dict[str, Any], cfg: Any,
                 name: str) -> tuple[Any, list[float]]:
    if token in "HBF":
        return z6._apply_token(current, virtual, token, q0, targets, cfg, name)
    if token == "U":
        spec = {"coordinate": "p03", "level_delta": -1}
    elif token == "P":
        spec = {"coordinate": "p07:plus", "level_delta": 1}
    else:
        raise z6._error(f"unknown token: {token}")
    delta = z6.z5.z3.z2._increment_target(q0, targets, spec, cfg, name)
    target = z6.z5.z3.z1.c1._translated_target(
        current, q0, delta, cfg, f"{name}.target")
    return target, z6.z5.z3.z2._virtual_step(virtual, spec)


def build_stream(stage: dict[str, Any], cfg: Any, targets: dict[str, Any],
                 parent: dict[str, Any], decision: int, round_index: int,
                 rollout_id: str, arm_id: str, tokens: str,
                 *, fit_weight: int = 0) -> dict[str, Any]:
    if len(parent.get("targets", [])) < decision:
        raise z6._error("parent prefix too short")
    sequence = list(parent["targets"][:decision])
    virtual_rows = [list(row["probe_virtual_action"])
                    for row in parent["actions"][:decision]]
    current = sequence[-1]
    virtual = list(virtual_rows[-1])
    q0 = targets["q0"]
    for offset, token in enumerate(tokens):
        current, virtual = _apply_token(
            current, virtual, token, q0, targets, cfg,
            f"id2z11.{rollout_id}.{decision + offset}.{token}")
        sequence.append(current)
        virtual_rows.append(list(virtual))
    while len(sequence) < int(stage["common_horizon_steps"]):
        sequence.append(current)
        virtual_rows.append(list(virtual))
    actions = z6.z5.z3.z1.c1._actions(sequence, cfg, rollout_id, virtual_rows)
    return {
        "rollout_id": rollout_id, "candidate_id": rollout_id,
        "arm_id": arm_id, "tokens": tokens, "fit_weight": fit_weight,
        "round_index": round_index,
        "round_id": ("root_state49" if round_index == 0 else
                     "main_state53" if round_index == 1 else "alternate_state53"),
        "cell_id": rollout_id, "cell_kind": "bounded_capture_teacher_branch",
        "context_id": f"round{round_index}_state{decision}_causal_prefix",
        "direction_id": "signed_p03_p07_capture_sequence",
        "coordinate": "h_b_f_u_p_capture_grammar", "sign": None,
        "probe_issue_step": decision, "probe_duration_issues": len(tokens),
        "non_nominal_issue_steps": list(range(decision, decision + len(tokens))),
        "targets": sequence, "actions": actions,
    }


def build_matrix(stage: dict[str, Any], cfg: Any, targets: dict[str, Any],
                 parent: dict[str, Any], decision: int, round_index: int,
                 namespace: str) -> list[dict[str, Any]]:
    return [build_stream(stage, cfg, targets, parent, decision, round_index,
                         f"{namespace}__{spec['arm_id']}", spec["arm_id"],
                         spec["tokens"])
            for spec in stage["candidate_specs"]]


def validate_stream(stream: dict[str, Any], stage: dict[str, Any], cfg: Any) -> dict[str, Any]:
    failures: list[str] = []
    horizon = int(stage["common_horizon_steps"])
    actions = stream["actions"]
    decision = int(stream["probe_issue_step"])
    last = decision + len(stream["tokens"]) - 1
    if len(actions) != horizon or len(stream["targets"]) != horizon:
        failures.append("STREAM_DIMENSIONS")
    if any(token not in "HBFUP" for token in stream["tokens"]):
        failures.append("TOKEN_SET")
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


def _metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any],
             arm_ids: Sequence[str]) -> dict[str, Any]:
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
    for arm in arm_ids:
        row = by_arm.get(arm)
        complete = bool(row and row.get("passed") and
                        len(row.get("states", [])) == 78)
        if not complete:
            values.append({"arm_id": arm, "execution_status": "incomplete",
                           "capture_passed": False, "eligible": False})
            continue
        states = row["states"]
        distances = [z6._distance(states[i], source) for i in terminal]
        speeds = [z6._speed(states, i) for i in terminal]
        ipf = [abs(float(states[i]["ip_a"]) - float(source["ip_a"])) / source_ip
               for i in terminal]
        score = max(max(distances) / 0.025, max(speeds) / 0.1,
                    max(ipf) / 0.05)
        capture = bool(max(distances) <= 0.025 and max(speeds) <= 0.1
                       and max(ipf) <= 0.05)
        values.append({"arm_id": arm, "tokens": row["tokens"],
                       "execution_status": "complete",
                       "terminal_state_indices": terminal,
                       "terminal_source_rz_distance_m": distances,
                       "terminal_rz_step_speed_m_per_s": speeds,
                       "terminal_absolute_source_ip_fraction": ipf,
                       "terminal_max_source_rz_distance_m": max(distances),
                       "terminal_max_rz_step_speed_m_per_s": max(speeds),
                       "terminal_max_absolute_source_ip_fraction": max(ipf),
                       "terminal_worst_normalized_score": score,
                       "capture_passed": capture, "eligible": False})
    baseline = next((v for v in values if v["arm_id"] == "h8"), None)
    baseline_complete = bool(baseline and baseline.get("execution_status") == "complete")
    nominated: list[dict[str, Any]] = []
    if baseline_complete:
        base_score = float(baseline["terminal_worst_normalized_score"])
        for value in values:
            if value["arm_id"] == "h8" or value.get("execution_status") != "complete":
                continue
            improvement = base_score - float(value["terminal_worst_normalized_score"])
            value["score_improvement_over_hold"] = improvement
            value["eligible"] = bool(value["capture_passed"] or improvement >= 0.02)
            if value["eligible"]:
                nominated.append(value)
    nominated.sort(key=lambda v: (
        not bool(v["capture_passed"]), float(v["terminal_worst_normalized_score"]),
        float(v["terminal_max_source_rz_distance_m"]),
        float(v["terminal_max_rz_step_speed_m_per_s"]),
        float(v["terminal_max_absolute_source_ip_fraction"]), str(v["arm_id"])))
    return {"baseline_complete": baseline_complete,
            "baseline_terminal_worst_normalized_score": (
                baseline.get("terminal_worst_normalized_score") if baseline else None),
            "branch_metrics": values,
            "nominated_arm_ids": [v["arm_id"] for v in nominated],
            "selected_arm_id": nominated[0]["arm_id"] if nominated else None,
            "selected_capture_passed": bool(nominated and nominated[0]["capture_passed"]),
            "passed": bool(baseline_complete and nominated and
                           all(v.get("execution_status") == "complete" for v in values))}


def alternate_parent_arm(selected_root_tokens: str) -> str:
    return "f8" if selected_root_tokens[:4] == "BBBB" else "b8"


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
        roots = build_matrix(stage, cfg, targets, parent, 49, 0, "root")
        for root in roots:
            a = validate_stream(root, stage, cfg)
            for main in build_matrix(stage, cfg, targets, root, 53, 1, "main"):
                b = validate_stream(main, stage, cfg)
                checks.append({"sequence": [root["arm_id"], main["arm_id"]],
                               "passed": bool(a["passed"] and b["passed"]),
                               "failures": list(dict.fromkeys(a["failures"] + b["failures"]))})
        if len(checks) != 49 or not all(v["passed"] for v in checks):
            failures.append("FULL_ROOT_MAIN_ACTION_MATRIX_NOT_ADMISSIBLE")
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {"schema_version": "rgeo-zgeo-1ms-id2z11-offline-v1",
            "source_revision": source_revision, "stage_config_sha256": CONFIG_SHA256,
            "passed": not failures, "failures": failures,
            "static_root_main_sequence_count": len(checks),
            "static_root_main_sequences_passed": sum(v["passed"] for v in checks),
            "sequence_checks": checks, "reset_calls": 0, "advance_attempts": 0,
            "plant_advance_gotsc_calls": 0, "models_fit_or_updated": 0}


def route_for(stage: dict[str, Any], execution: bool, raw_ok: bool,
              prefixes_ok: bool, root: dict[str, Any], main: dict[str, Any],
              alt_ok: bool, replay_ok: bool, capture: bool) -> str:
    if not execution:
        return stage["routes"]["execution_or_interface_fail"]
    if not raw_ok:
        return stage["routes"]["raw_integrity_fail"]
    if not prefixes_ok:
        return stage["routes"]["prefix_mismatch"]
    if not root.get("passed"):
        return stage["routes"]["root_no_eligible_arm"]
    if not main.get("passed"):
        return stage["routes"]["main_no_eligible_arm"]
    if not alt_ok:
        return stage["routes"]["alternate_support_fail"]
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

    root_streams = build_matrix(stage, cfg, targets, parent, 49, 0, "root")
    root_rows: list[dict[str, Any]] = []
    for stream in root_streams:
        if not validate_stream(stream, stage, cfg)["passed"]:
            execution = False; break
        row = execute_row(cfg, runtime, stream, reference, source_revision, output)
        rows.append(row); root_rows.append(row)
        prefixes.append(z6.prefix_check(row, reference, 50, 49,
                                        stage["semantic_artifacts"]))
        if not row.get("passed") and not z6.safe_stop(row, runtime):
            execution = False; break
    root_metrics = _metrics(root_rows, stage, ARM_IDS)
    selected_root_arm = root_metrics.get("selected_arm_id")
    selected_root_stream = next((v for v in root_streams
                                 if v["arm_id"] == selected_root_arm), None)
    selected_root_row = next((v for v in root_rows
                              if v.get("arm_id") == selected_root_arm), None)

    main_streams: list[dict[str, Any]] = []
    main_rows: list[dict[str, Any]] = []
    main_metrics: dict[str, Any] = {"passed": False}
    if execution and root_metrics.get("passed") and selected_root_stream and selected_root_row:
        main_streams = build_matrix(stage, cfg, targets, selected_root_stream,
                                    53, 1, "main")
        for stream in main_streams:
            if not validate_stream(stream, stage, cfg)["passed"]:
                execution = False; break
            row = execute_row(cfg, runtime, stream, selected_root_row,
                              source_revision, output)
            rows.append(row); main_rows.append(row)
            prefixes.append(z6.prefix_check(row, selected_root_row, 54, 53,
                                            stage["semantic_artifacts"]))
            if not row.get("passed") and not z6.safe_stop(row, runtime):
                execution = False; break
        main_metrics = _metrics(main_rows, stage, ARM_IDS)

    selected_main_arm = main_metrics.get("selected_arm_id")
    selected_main_stream = next((v for v in main_streams
                                 if v["arm_id"] == selected_main_arm), None)
    selected_main_row = next((v for v in main_rows
                              if v.get("arm_id") == selected_main_arm), None)

    alt_rows: list[dict[str, Any]] = []
    alt_metrics: dict[str, Any] = {"passed": False}
    alt_parent_id = None
    if (execution and main_metrics.get("passed") and selected_main_stream
            and selected_main_row and selected_main_arm != "h8"):
        alt_parent_id = alternate_parent_arm(str(selected_root_stream["tokens"]))
        alt_parent_stream = next(v for v in root_streams if v["arm_id"] == alt_parent_id)
        alt_parent_row = next(v for v in root_rows if v.get("arm_id") == alt_parent_id)
        selected_tokens = next(v["tokens"] for v in stage["candidate_specs"]
                               if v["arm_id"] == selected_main_arm)
        alt_streams = [
            build_stream(stage, cfg, targets, alt_parent_stream, 53, 2,
                         "alternate__h8", "h8", "HHHHHHHH"),
            build_stream(stage, cfg, targets, alt_parent_stream, 53, 2,
                         f"alternate__{selected_main_arm}", selected_main_arm,
                         selected_tokens),
        ]
        for stream in alt_streams:
            if not validate_stream(stream, stage, cfg)["passed"]:
                execution = False; break
            row = execute_row(cfg, runtime, stream, alt_parent_row,
                              source_revision, output)
            rows.append(row); alt_rows.append(row)
            prefixes.append(z6.prefix_check(row, alt_parent_row, 54, 53,
                                            stage["semantic_artifacts"]))
            if not row.get("passed") and not z6.safe_stop(row, runtime):
                execution = False; break
        alt_metrics = _metrics(alt_rows, stage, ("h8", selected_main_arm))

    alt_selected = next((v for v in alt_metrics.get("branch_metrics", [])
                         if v.get("arm_id") == selected_main_arm), None)
    alt_hold = next((v for v in alt_metrics.get("branch_metrics", [])
                     if v.get("arm_id") == "h8"), None)
    alt_improvement = None
    if (alt_selected and alt_hold and alt_selected.get("execution_status") == "complete"
            and alt_hold.get("execution_status") == "complete"):
        alt_improvement = (float(alt_hold["terminal_worst_normalized_score"])
                           - float(alt_selected["terminal_worst_normalized_score"]))
    alt_ok = bool(alt_metrics.get("baseline_complete") and alt_selected
                  and (alt_selected.get("capture_passed")
                       or (alt_improvement is not None and alt_improvement >= 0.02)))

    replay_row = None
    replay_ok = False
    if execution and selected_main_stream and selected_main_row:
        replay = replay_stream(selected_main_stream)
        replay_row = execute_row(cfg, runtime, replay, selected_main_row,
                                 source_revision, output)
        rows.append(replay_row)
        prefixes.append(z6.prefix_check(replay_row, selected_main_row, 78, 77,
                                        stage["semantic_artifacts"]))
        replay_ok = z6.replay_check(selected_main_row, replay_row,
                                    stage["semantic_artifacts"])["passed"]
        if not replay_row.get("passed") and not z6.safe_stop(replay_row, runtime):
            execution = False

    counters = {key: sum(int(row.get(key, 0)) for row in rows) for key in
                ("reset_calls", "advance_attempts", "plant_advance_gotsc_calls",
                 "verified_plant_advances")}
    if (len(rows) > 17 or any(counters[key] > 1309 for key in counters)):
        execution = False
    prefixes_ok = bool(prefixes and all(v.get("passed") for v in prefixes))
    inventory = io.raw_inventory(output, rows, stage)
    expected_files = 5 * sum(len(row.get("states", [])) for row in rows)
    raw_ok = bool(execution and not inventory["missing_required_artifacts"]
                  and inventory["required_artifact_files"] == expected_files)
    selected_metric = next((v for v in main_metrics.get("branch_metrics", [])
                            if v.get("arm_id") == selected_main_arm), None)
    capture = bool(selected_metric and selected_metric.get("capture_passed"))
    route = route_for(stage, execution, raw_ok, prefixes_ok, root_metrics,
                      main_metrics, alt_ok, replay_ok, capture)
    scientific = {
        "root_metrics": root_metrics, "main_metrics": main_metrics,
        "alternate_metrics": alt_metrics,
        "alternate_parent_arm_id": alt_parent_id,
        "alternate_selected_arm_score_improvement_over_hold": alt_improvement,
        "alternate_support_passed": alt_ok,
        "selected_root_arm_id": selected_root_arm,
        "selected_root_committed_tokens": (
            selected_root_stream["tokens"][:4] if selected_root_stream else None),
        "selected_main_arm_id": selected_main_arm,
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
              "claim_boundary": "Finite source-local capture-teacher evidence only."}
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
    output = inside(output, "ID2Z11 output")
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
