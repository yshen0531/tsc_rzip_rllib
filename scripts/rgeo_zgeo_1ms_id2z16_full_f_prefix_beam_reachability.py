#!/usr/bin/env python3
"""Run the frozen ID-2Z16 full-F-prefix two-layer beam discriminator."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_id2z15_headroom_nominal_frontier as z15  # noqa: E402


z14, z6, z7, io = z15.z14, z15.z6, z15.z7, z15.io
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z16_full_f_prefix_beam_reachability.json"
CONFIG_SHA256 = "64da1123f1768d202c82f61480d207bc2ad049f1c308b2eafea942fff6e0b07d"
SCHEMA = "rgeo-zgeo-1ms-id2z16-full-f-prefix-beam-reachability-result-v1"
ARM_IDS = ("h8", "b8", "f8", "b4f4", "f4b4")


def inside(path: Path, label: str) -> Path:
    return z15.inside(path, label)


def load_json(path: Path) -> dict[str, Any]:
    return z15.load_json(path)


def _require(stage: dict[str, Any]) -> None:
    if io.sha256(CONFIG) != CONFIG_SHA256:
        raise z6._error("ID2Z16 config hash mismatch")
    if stage != load_json(CONFIG):
        raise z6._error("frozen ID2Z16 config changed")
    if [row.get("arm_id") for row in stage.get("candidate_specs", [])] != list(ARM_IDS):
        raise z6._error("candidate order changed")
    if [row.get("tokens") for row in stage["candidate_specs"]] != [
            "HHHHHHHH", "BBBBBBBB", "FFFFFFFF", "BBBBFFFF", "FFFFBBBB"]:
        raise z6._error("beam grammar changed")
    exact = {
        "takeover_time_ms": 1100, "control_period_ms": 1,
        "common_horizon_steps": 65, "common_terminal_state_index": 65,
        "source_prefix_last_issue": 31, "source_prefix_last_state": 32,
        "beam_width": 2, "maximum_static_sequences": 30,
        "maximum_search_branches": 15, "maximum_replay_rollouts": 1,
        "maximum_rollouts": 16, "maximum_reset_calls": 16,
        "maximum_advance_attempts": 1040, "maximum_gotsc_calls": 1040,
        "maximum_verified_plant_advances": 1040,
        "maximum_retained_states": 1056,
        "required_artifact_files_if_all_complete": 5280,
        "models_fit_or_updated": 0,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise z6._error(f"frozen field changed: {key}")
    if [(row.get("round_index"), row.get("decision_state_index"),
         row.get("macro_last_issue")) for row in stage.get("rounds", [])] != [
            (0, 32, 39), (1, 40, 47)]:
        raise z6._error("round clocks changed")


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
        "common_horizon_steps": 65,
        "common_terminal_state_index": 65,
        "maximum_rounds": 2,
        "rounds": list(stage["rounds"]),
        "candidate_specs": list(stage["candidate_specs"]),
        "empirical_exploration": dict(stage["empirical_exploration"]),
        "measurement_gates": dict(stage["measurement_gates"]),
        "semantic_artifacts": list(stage["semantic_artifacts"]),
    })
    return value


def load(path: Path = CONFIG) -> tuple[dict[str, Any], dict[str, Any], Any,
                                       dict[str, Any], dict[str, Any], dict[str, Any]]:
    path = inside(path, "ID2Z16 config")
    if path != CONFIG.resolve():
        raise z6._error("alternate ID2Z16 config forbidden")
    stage = load_json(path)
    _require(stage)
    evidence = _verify_evidence(stage)
    result, audit = evidence["id2z15_result"], evidence["id2z15_independent"]
    reference = evidence["id2z15_full_f_replay"]
    if (result.get("route") != stage["evidence"]["id2z15_result"]["required_route"]
            or result.get("passed") is not False
            or result.get("scientific_metrics", {}).get("selected_arm_id") != "f100"
            or result.get("scientific_metrics", {}).get(
                "selected_replay_exact_passed") is not True
            or audit.get("audit_passed") is not True
            or audit.get("recomputed_route") != result.get("route")
            or reference.get("passed") is not True
            or len(reference.get("states", [])) != 49
            or len(reference.get("actions", [])) != 48):
        raise z6._error("ID2Z15 source evidence mismatch")
    _, base_runtime, cfg, targets, _ = z15.load(
        ROOT / stage["evidence"]["id2z15_config"]["path"])
    parents = z15.build_matrix(load_json(z15.CONFIG), cfg, targets)
    parent = next(row for row in parents if row["arm_id"] == "f100")
    if [row["expected_card15_fields"] for row in parent["actions"]] != [
            row["expected_card15_fields"] for row in reference["actions"]]:
        raise z6._error("planned full-F parent differs from fresh replay")
    return stage, runtime_stage(stage, base_runtime), cfg, targets, parent, reference


def build_stream(stage: dict[str, Any], cfg: Any, targets: dict[str, Any],
                 parent: dict[str, Any], decision: int, round_index: int,
                 namespace: str, spec: dict[str, Any]) -> dict[str, Any]:
    if len(parent.get("targets", [])) < decision:
        raise z6._error("parent prefix too short")
    arm_id, tokens = str(spec["arm_id"]), str(spec["tokens"])
    rollout_id = f"{namespace}__{arm_id}"
    sequence = list(parent["targets"][:decision])
    virtual_rows = [list(row["probe_virtual_action"])
                    for row in parent["actions"][:decision]]
    current = sequence[-1]
    virtual = list(virtual_rows[-1])
    q0 = targets["q0"]
    for offset, token in enumerate(tokens):
        current, virtual = z14._apply_token(
            current, virtual, token, q0, targets, cfg,
            f"id2z16.{rollout_id}.{decision + offset}.{token}")
        sequence.append(current)
        virtual_rows.append(list(virtual))
    while len(sequence) < int(stage["common_horizon_steps"]):
        sequence.append(current)
        virtual_rows.append(list(virtual))
    actions = z6.z5.z3.z1.c1._actions(sequence, cfg, rollout_id, virtual_rows)
    parent_path = str(parent.get("path_id") or parent.get("arm_id") or "full_f")
    path_id = f"{parent_path}__{arm_id}"
    return {
        "rollout_id": rollout_id, "candidate_id": rollout_id,
        "arm_id": arm_id, "tokens": tokens, "parent_path_id": parent_path,
        "path_id": path_id, "fit_weight": 0, "round_index": round_index,
        "round_id": "full_f_state32" if round_index == 0 else "beam_state40",
        "cell_id": rollout_id, "cell_kind": "full_f_prefix_beam_branch",
        "context_id": f"round{round_index}_state{decision}_causal_prefix",
        "direction_id": "bfh_sequence_reachability", "coordinate": "h_b_f_macros",
        "sign": None, "probe_issue_step": decision,
        "probe_duration_issues": len(tokens),
        "non_nominal_issue_steps": list(range(decision, decision + len(tokens))),
        "targets": sequence, "actions": actions,
    }


def build_round(stage: dict[str, Any], cfg: Any, targets: dict[str, Any],
                parent: dict[str, Any], decision: int, round_index: int,
                namespace: str) -> list[dict[str, Any]]:
    rows = [build_stream(stage, cfg, targets, parent, decision, round_index,
                         namespace, spec) for spec in stage["candidate_specs"]]
    if [row["arm_id"] for row in rows] != list(ARM_IDS):
        raise z6._error("round matrix order changed")
    return rows


def validate_stream(stream: dict[str, Any], stage: dict[str, Any], cfg: Any) -> dict[str, Any]:
    failures: list[str] = []
    actions = stream["actions"]
    horizon, decision = int(stage["common_horizon_steps"]), int(stream["probe_issue_step"])
    last = decision + len(stream["tokens"]) - 1
    if len(actions) != horizon or len(stream["targets"]) != horizon:
        failures.append("STREAM_DIMENSIONS")
    if any(token not in "HBF" for token in stream["tokens"]):
        failures.append("TOKEN_SET")
    for issue, action in enumerate(actions):
        if (int(action["issue_step"]) != issue
                or int(action["effect_state_index"]) != issue + 1
                or float(action["maximum_issued_delta_a"]) > .3000000001):
            failures.append(f"ACTION_CONTRACT:{issue}")
    for issue in range(last + 1, horizon):
        if (actions[issue]["expected_card15_fields"] != actions[last]["expected_card15_fields"]
                or float(actions[issue]["maximum_issued_delta_a"]) != 0.0):
            failures.append(f"TAIL_HOLD:{issue}")
    headroom = z6._headroom(stream["targets"], cfg)
    if headroom < -1e-9:
        failures.append("ABSOLUTE_CURRENT_LIMIT")
    return {"rollout_id": stream["rollout_id"], "path_id": stream["path_id"],
            "minimum_absolute_current_headroom_a": headroom,
            "passed": not failures, "failures": list(dict.fromkeys(failures))}


def _metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    terminal = [int(value) for value in stage["measurement_gates"]["terminal_state_indices"]]
    expected_states = int(stage["common_horizon_steps"]) + 1
    source_row = next((row for row in rows if row.get("states")), None)
    if source_row is None:
        return {"complete": False, "branch_metrics": [], "ranked_path_ids": []}
    source = source_row["states"][0]
    source_ip = abs(float(source["ip_a"]))
    gates = stage["measurement_gates"]
    dcap = float(gates["maximum_capture_source_rz_distance_m"])
    vcap = float(gates["maximum_capture_rz_step_speed_m_per_s"])
    icap = float(gates["maximum_capture_absolute_source_ip_fraction"])
    values: list[dict[str, Any]] = []
    for row in rows:
        complete = bool(row.get("passed") and len(row.get("states", [])) == expected_states)
        if not complete:
            values.append({"rollout_id": row.get("rollout_id"),
                           "path_id": row.get("path_id"),
                           "execution_status": "incomplete", "capture_passed": False})
            continue
        states = row["states"]
        distances = [z6._distance(states[index], source) for index in terminal]
        speeds = [z6._speed(states, index) for index in terminal]
        ipf = [abs(float(states[index]["ip_a"]) - float(source["ip_a"])) / source_ip
               for index in terminal]
        score = max(max(distances) / dcap, max(speeds) / vcap, max(ipf) / icap)
        capture = bool(max(distances) <= dcap and max(speeds) <= vcap and max(ipf) <= icap)
        values.append({"rollout_id": row["rollout_id"], "path_id": row["path_id"],
                       "arm_id": row["arm_id"], "execution_status": "complete",
                       "terminal_state_indices": terminal,
                       "terminal_max_source_rz_distance_m": max(distances),
                       "terminal_max_rz_step_speed_m_per_s": max(speeds),
                       "terminal_max_absolute_source_ip_fraction": max(ipf),
                       "terminal_worst_normalized_score": score,
                       "capture_passed": capture})
    ranked = [value for value in values if value["execution_status"] == "complete"]
    ranked.sort(key=lambda value: (not bool(value["capture_passed"]),
                                   float(value["terminal_worst_normalized_score"]),
                                   str(value["path_id"])))
    return {"complete": bool(values and all(value["execution_status"] == "complete"
                                             for value in values)),
            "branch_metrics": values,
            "ranked_path_ids": [value["path_id"] for value in ranked],
            "selected_path_id": ranked[0]["path_id"] if ranked else None,
            "selected_capture_passed": bool(ranked and ranked[0]["capture_passed"])}


def replay_stream(selected: dict[str, Any]) -> dict[str, Any]:
    value = dict(selected)
    value.update({"rollout_id": "critical_replay", "candidate_id": "critical_replay",
                  "arm_id": "critical_replay", "fit_weight": 0,
                  "round_id": "critical_replay", "cell_id": "critical_replay",
                  "cell_kind": "beam_selected_path_replay"})
    return value


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


def offline(path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    checks: list[dict[str, Any]] = []
    try:
        stage, _, cfg, targets, parent, _ = load(path)
        roots = build_round(stage, cfg, targets, parent, 32, 0, "round0")
        for stream in roots:
            checks.append(validate_stream(stream, stage, cfg))
            for child in build_round(stage, cfg, targets, stream, 40, 1,
                                     f"static__{stream['arm_id']}"):
                checks.append(validate_stream(child, stage, cfg))
        if len(checks) != 30 or not all(value["passed"] for value in checks):
            failures.append("FULL_STATIC_TREE_NOT_ADMISSIBLE")
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {"schema_version": "rgeo-zgeo-1ms-id2z16-offline-v1",
            "source_revision": source_revision, "stage_config_sha256": CONFIG_SHA256,
            "passed": not failures, "failures": failures,
            "static_sequence_count": len(checks),
            "static_sequences_passed": sum(value["passed"] for value in checks),
            "sequence_checks": checks, "reset_calls": 0, "advance_attempts": 0,
            "plant_advance_gotsc_calls": 0, "models_fit_or_updated": 0}


def route_for(stage: dict[str, Any], execution: bool, raw_ok: bool,
              prefixes_ok: bool, round0: dict[str, Any], round1: dict[str, Any],
              replay_ok: bool) -> str:
    if not execution:
        return stage["routes"]["execution_or_interface_fail"]
    if not raw_ok:
        return stage["routes"]["raw_integrity_fail"]
    if not prefixes_ok:
        return stage["routes"]["prefix_mismatch"]
    if not round0.get("complete") or not round1.get("complete"):
        return stage["routes"]["beam_incomplete"]
    if not replay_ok:
        return stage["routes"]["replay_fail"]
    if round1.get("selected_capture_passed"):
        return stage["routes"]["capture_pass"]
    return stage["routes"]["no_capture"]


def execute(stage: dict[str, Any], runtime: dict[str, Any], cfg: Any,
            targets: dict[str, Any], parent: dict[str, Any], reference: dict[str, Any],
            source_revision: str, output: Path, storage_gate: dict[str, Any]) -> dict[str, Any]:
    isolation = z7.configure_run_root(cfg, output)
    rows: list[dict[str, Any]] = []
    prefixes: list[dict[str, Any]] = []
    execution = True
    root_streams = build_round(stage, cfg, targets, parent, 32, 0, "round0")
    root_rows: list[dict[str, Any]] = []
    for stream in root_streams:
        row = execute_row(cfg, runtime, stream, reference, source_revision, output)
        rows.append(row); root_rows.append(row)
        prefixes.append(z6.prefix_check(row, reference, 33, 32,
                                        stage["semantic_artifacts"]))
        if not row.get("passed") and not z6.safe_stop(row, runtime):
            execution = False
            break
    root_metrics = _metrics(root_rows, stage)
    beam_ids = root_metrics.get("ranked_path_ids", [])[:2] if root_metrics.get("complete") else []
    beam_streams = [stream for path in beam_ids for stream in root_streams
                    if stream["path_id"] == path]
    beam_rows = [row for path in beam_ids for row in root_rows if row["path_id"] == path]
    child_streams: list[dict[str, Any]] = []
    child_rows: list[dict[str, Any]] = []
    if execution and len(beam_streams) == 2:
        for parent_stream, parent_row in zip(beam_streams, beam_rows):
            children = build_round(stage, cfg, targets, parent_stream, 40, 1,
                                   f"round1__{parent_stream['arm_id']}")
            child_streams.extend(children)
            for stream in children:
                row = execute_row(cfg, runtime, stream, parent_row,
                                  source_revision, output)
                rows.append(row); child_rows.append(row)
                prefixes.append(z6.prefix_check(row, parent_row, 41, 40,
                                                stage["semantic_artifacts"]))
                if not row.get("passed") and not z6.safe_stop(row, runtime):
                    execution = False
                    break
            if not execution:
                break
    child_metrics = _metrics(child_rows, stage)
    selected_path = child_metrics.get("selected_path_id")
    selected_stream = next((row for row in child_streams
                            if row["path_id"] == selected_path), None)
    selected_row = next((row for row in child_rows if row.get("path_id") == selected_path), None)
    replay_ok = False
    if execution and child_metrics.get("complete") and selected_stream and selected_row:
        replay = execute_row(cfg, runtime, replay_stream(selected_stream), selected_row,
                             source_revision, output)
        rows.append(replay)
        prefixes.append(z6.prefix_check(replay, selected_row, 66, 65,
                                        stage["semantic_artifacts"]))
        replay_ok = z6.replay_check(selected_row, replay,
                                    stage["semantic_artifacts"])["passed"]
        if not replay.get("passed"):
            execution = False
    counters = {key: sum(int(row.get(key, 0)) for row in rows) for key in
                ("reset_calls", "advance_attempts", "plant_advance_gotsc_calls",
                 "verified_plant_advances")}
    if len(rows) > 16 or any(counters[key] > 1040 for key in counters):
        execution = False
    prefixes_ok = bool(prefixes and all(value.get("passed") for value in prefixes))
    inventory = io.raw_inventory(output, rows, stage)
    expected_files = 5 * sum(len(row.get("states", [])) for row in rows)
    raw_ok = bool(execution and not inventory["missing_required_artifacts"]
                  and inventory["required_artifact_files"] == expected_files)
    route = route_for(stage, execution, raw_ok, prefixes_ok,
                      root_metrics, child_metrics, replay_ok)
    scientific = {"round0_metrics": root_metrics,
                  "round0_selected_parent_path_ids": beam_ids,
                  "round1_metrics": child_metrics,
                  "selected_path_id": selected_path,
                  "selected_capture_passed": child_metrics.get(
                      "selected_capture_passed", False),
                  "selected_replay_exact_passed": replay_ok}
    result = {"schema_version": SCHEMA, "source_revision": source_revision,
              "stage_config_sha256": CONFIG_SHA256,
              "passed": route == stage["routes"]["capture_pass"], "route": route,
              "storage_gate": storage_gate, "run_root_isolation": isolation,
              "execution_integrity_passed": execution, "raw_integrity_passed": raw_ok,
              "prefix_checks": prefixes, "scientific_metrics": scientific,
              "rollouts_completed": len(rows),
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
    output = inside(output, "ID2Z16 output")
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
