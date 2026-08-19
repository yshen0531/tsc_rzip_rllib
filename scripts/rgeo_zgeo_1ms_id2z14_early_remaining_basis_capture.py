#!/usr/bin/env python3
"""Run frozen ID-2Z14 state33 remaining-basis capture discriminator."""

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

from scripts import rgeo_zgeo_1ms_id2z13_early_p04_augmented_capture as z13  # noqa: E402


z6 = z13.z6
z7 = z13.z7
io = z13.io
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z14_early_remaining_basis_capture.json"
CONFIG_SHA256 = "a7084ee9817eb3fb6e7567f812b3909cb84215a471ab10f44a4126e8af19ca31"
SCHEMA = "rgeo-zgeo-1ms-id2z14-early-remaining-basis-capture-result-v1"
ARM_IDS = ("h8", "b8", "f8", "b4f4", "f4b4", "i4h4", "j4h4", "k4r3", "l4r3")


def inside(path: Path, label: str) -> Path:
    return z13.inside(path, label)


def load_json(path: Path) -> dict[str, Any]:
    return z13.load_json(path)


def _require(stage: dict[str, Any]) -> None:
    if z6.z5.base.sha256(CONFIG) != CONFIG_SHA256:
        raise z6._error("ID2Z14 config hash mismatch")
    if stage != load_json(CONFIG):
        raise z6._error("frozen ID2Z14 config changed")
    if [row.get("arm_id") for row in stage.get("candidate_specs", [])] != list(ARM_IDS):
        raise z6._error("candidate order changed")
    if [row.get("tokens") for row in stage["candidate_specs"]] != [
            "HHHHHHHH", "BBBBBBBB", "FFFFFFFF", "BBBBFFFF", "FFFFBBBB",
            "IIIIHHHH", "JJJJHHHH", "KHHHLHHH", "LHHHKHHH"]:
        raise z6._error("candidate schedules changed")
    if (stage.get("decision_state_index") != 33
            or stage.get("common_horizon_steps") != 65
            or stage.get("maximum_rollouts") != 10
            or stage.get("maximum_advance_attempts") != 650
            or stage.get("required_artifact_files_if_all_complete") != 3300):
        raise z6._error("campaign budget changed")


def _verify_evidence(stage: dict[str, Any]) -> dict[str, dict[str, Any]]:
    values: dict[str, dict[str, Any]] = {}
    for name, spec in stage["evidence"].items():
        path = inside(ROOT / spec["path"], name)
        if z6.z5.base.sha256(path) != spec["sha256"]:
            raise z6._error(f"evidence hash mismatch: {name}")
        values[name] = load_json(path) if path.suffix == ".json" else {}
    return values


def _add_targets(stage: dict[str, Any], cfg: Any,
                 targets: dict[str, Any]) -> dict[str, Any]:
    values = dict(targets)
    maker = z6.z5.z3.z1.c1.target_from_fields
    for direction, spec in stage["directions"].items():
        for sign in ("plus", "minus"):
            values[f"{direction}:{sign}"] = maker(
                spec[f"{sign}_card15_fields"], cfg, f"id2z14.{direction}.{sign}")
    q0 = values["q0"]
    for direction in stage["directions"]:
        plus = values[f"{direction}:plus"]
        minus = values[f"{direction}:minus"]
        for index, (p, m, q) in enumerate(zip(
                plus.card15_fields, minus.card15_fields, q0.card15_fields)):
            if Decimal(p.strip()) + Decimal(m.strip()) != Decimal(q.strip()) * 2:
                raise z6._error(f"non-centred signed pair: {direction}:{index}")
    return values


def runtime_stage(stage: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    value = dict(source)
    value.update({
        "common_horizon_steps": 65,
        "common_terminal_state_index": 65,
        "maximum_rounds": 1,
        "rounds": [{"round_index": 0, "round_id": "state33",
                    "decision_state_index": 33, "macro_last_issue": 40}],
        "candidate_specs": list(stage["candidate_specs"]),
        "empirical_exploration": dict(stage["empirical_exploration"]),
        "measurement_gates": dict(stage["measurement_gates"]),
        "semantic_artifacts": list(stage["semantic_artifacts"]),
    })
    return value


def load(path: Path = CONFIG) -> tuple[dict[str, Any], dict[str, Any], Any,
                                       dict[str, Any], dict[str, Any], dict[str, Any]]:
    path = inside(path, "ID2Z14 config")
    if path != CONFIG.resolve():
        raise z6._error("alternate ID2Z14 config forbidden")
    stage = load_json(path)
    _require(stage)
    evidence = _verify_evidence(stage)
    result = evidence["id2z13_result"]
    audit = evidence["id2z13_independent"]
    if (result.get("route") != stage["evidence"]["id2z13_result"]["required_route"]
            or result.get("passed") is not False
            or audit.get("audit_passed") is not True
            or audit.get("recomputed_route") != result.get("route")):
        raise z6._error("ID2Z13 closing evidence mismatch")
    if (evidence["id1c0_result"].get("passed") is not True
            or evidence["id1c_result"].get("passed") is not False
            or evidence["id1c_independent"].get("audit_passed") is not True):
        raise z6._error("p01/p09 evidence mismatch")
    _, base_runtime, cfg, targets, parent, reference = z13.load(
        ROOT / stage["evidence"]["id2z13_config"]["path"])
    replay = evidence["id2z13_critical_replay"]
    if (replay.get("passed") is not True or len(replay.get("states", [])) != 78
            or len(replay.get("actions", [])) != 77):
        raise z6._error("ID2Z13 replay shape changed")
    prefix = z6.prefix_check(replay, reference, 34, 33, stage["semantic_artifacts"])
    if not prefix.get("passed"):
        raise z6._error("state33 prefix mismatch")
    return (stage, runtime_stage(stage, base_runtime), cfg,
            _add_targets(stage, cfg, targets), parent, replay)


def _extended(virtual: Sequence[float]) -> list[float]:
    values = [float(value) for value in virtual]
    return values + [0.0] * (5 - len(values))


def _apply_token(current: Any, virtual: Sequence[float], token: str,
                 q0: Any, targets: dict[str, Any], cfg: Any,
                 name: str) -> tuple[Any, list[float]]:
    values = _extended(virtual)
    if token in "HBF":
        target, updated = z13._apply_token(current, values, token, q0, targets, cfg, name)
        return target, _extended(updated)
    mapping = {
        "I": ("p01:plus", 3, 1.0), "J": ("p01:minus", 3, -1.0),
        "K": ("p09_half_exact_center:plus", 4, 1.0),
        "L": ("p09_half_exact_center:minus", 4, -1.0),
    }
    if token not in mapping:
        raise z6._error(f"unknown token: {token}")
    coordinate, index, direction = mapping[token]
    delta = targets[coordinate]
    target = z6.z5.z3.z1.c1._translated_target(
        current, q0, delta, cfg, f"{name}.target")
    values[index] += direction
    return target, values


def build_stream(stage: dict[str, Any], cfg: Any, targets: dict[str, Any],
                 parent: dict[str, Any], rollout_id: str,
                 arm_id: str, tokens: str) -> dict[str, Any]:
    decision = int(stage["decision_state_index"])
    horizon = int(stage["common_horizon_steps"])
    sequence = list(parent["targets"][:decision])
    virtual_rows = [_extended(row["probe_virtual_action"])
                    for row in parent["actions"][:decision]]
    current = sequence[-1]
    virtual = list(virtual_rows[-1])
    q0 = targets["q0"]
    for offset, token in enumerate(tokens):
        current, virtual = _apply_token(
            current, virtual, token, q0, targets, cfg,
            f"id2z14.{rollout_id}.{decision + offset}.{token}")
        sequence.append(current)
        virtual_rows.append(list(virtual))
    while len(sequence) < horizon:
        sequence.append(current)
        virtual_rows.append(list(virtual))
    actions = z6.z5.z3.z1.c1._actions(sequence, cfg, rollout_id, virtual_rows)
    return {
        "rollout_id": rollout_id, "candidate_id": rollout_id,
        "arm_id": arm_id, "tokens": tokens, "fit_weight": 0,
        "round_index": 0, "round_id": "state33",
        "cell_id": rollout_id, "cell_kind": "early_remaining_basis_capture_branch",
        "context_id": "state33_exact_causal_prefix",
        "direction_id": "signed_b_f_p01_p09_event",
        "coordinate": "h_b_f_i_j_k_l_capture_grammar", "sign": None,
        "probe_issue_step": decision, "probe_duration_issues": len(tokens),
        "non_nominal_issue_steps": list(range(decision, decision + len(tokens))),
        "targets": sequence, "actions": actions,
    }


def build_matrix(stage: dict[str, Any], cfg: Any, targets: dict[str, Any],
                 parent: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [build_stream(stage, cfg, targets, parent, f"branch__{spec['arm_id']}",
                         spec["arm_id"], spec["tokens"])
            for spec in stage["candidate_specs"]]
    if [row["arm_id"] for row in rows] != list(ARM_IDS):
        raise z6._error("candidate matrix order changed")
    return rows


def validate_stream(stream: dict[str, Any], stage: dict[str, Any], cfg: Any) -> dict[str, Any]:
    failures: list[str] = []
    horizon = int(stage["common_horizon_steps"])
    decision = int(stage["decision_state_index"])
    actions = stream["actions"]
    last = decision + len(stream["tokens"]) - 1
    if len(actions) != horizon or len(stream["targets"]) != horizon:
        failures.append("STREAM_DIMENSIONS")
    if any(token not in "HBFIJKL" for token in stream["tokens"]):
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
    if stream["arm_id"] in {"k4r3", "l4r3"}:
        if actions[decision + 4]["expected_card15_fields"] != actions[decision - 1]["expected_card15_fields"]:
            failures.append("P09_EXACT_RETURN")
    headroom = z6._headroom(stream["targets"], cfg)
    if headroom < -1e-9:
        failures.append("ABSOLUTE_CURRENT_LIMIT")
    return {"rollout_id": stream["rollout_id"], "arm_id": stream["arm_id"],
            "minimum_absolute_current_headroom_a": headroom,
            "passed": not failures, "failures": list(dict.fromkeys(failures))}


def _metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    """Evaluate the frozen ID2Z14 horizon without inheriting Z11's length.

    Z11 has a 77-step horizon and therefore hard-codes 78 retained states.
    ID2Z14 ends at issue 64/state 65, so reusing that implementation would
    classify every valid 66-state branch as incomplete.  Keep the same score
    and ordering semantics, but derive completeness and thresholds from the
    ID2Z14 stage contract.
    """
    gates = stage["measurement_gates"]
    by_arm = {str(row.get("arm_id")): row for row in rows}
    source_row = next((row for row in rows if row.get("states")), None)
    terminal = [int(value) for value in gates["terminal_state_indices"]]
    expected_state_count = int(stage["common_horizon_steps"]) + 1
    values: list[dict[str, Any]] = []
    if source_row is None:
        return {"baseline_complete": False, "branch_metrics": values,
                "selected_arm_id": None, "passed": False}
    source = source_row["states"][0]
    source_ip = abs(float(source["ip_a"]))
    distance_cap = float(gates["maximum_capture_source_rz_distance_m"])
    speed_cap = float(gates["maximum_capture_rz_step_speed_m_per_s"])
    ip_cap = float(gates["maximum_capture_absolute_source_ip_fraction"])
    minimum_improvement = float(gates["minimum_round_score_improvement_over_hold"])
    for arm in ARM_IDS:
        row = by_arm.get(arm)
        complete = bool(row and row.get("passed") and
                        len(row.get("states", [])) == expected_state_count)
        if not complete:
            values.append({"arm_id": arm, "execution_status": "incomplete",
                           "capture_passed": False, "eligible": False})
            continue
        states = row["states"]
        distances = [z6._distance(states[index], source) for index in terminal]
        speeds = [z6._speed(states, index) for index in terminal]
        ip_fractions = [
            abs(float(states[index]["ip_a"]) - float(source["ip_a"])) / source_ip
            for index in terminal
        ]
        score = max(max(distances) / distance_cap, max(speeds) / speed_cap,
                    max(ip_fractions) / ip_cap)
        capture = bool(max(distances) <= distance_cap and max(speeds) <= speed_cap
                       and max(ip_fractions) <= ip_cap)
        values.append({"arm_id": arm, "tokens": row["tokens"],
                       "execution_status": "complete",
                       "terminal_state_indices": terminal,
                       "terminal_source_rz_distance_m": distances,
                       "terminal_rz_step_speed_m_per_s": speeds,
                       "terminal_absolute_source_ip_fraction": ip_fractions,
                       "terminal_max_source_rz_distance_m": max(distances),
                       "terminal_max_rz_step_speed_m_per_s": max(speeds),
                       "terminal_max_absolute_source_ip_fraction": max(ip_fractions),
                       "terminal_worst_normalized_score": score,
                       "capture_passed": capture, "eligible": False})
    baseline = next((value for value in values if value["arm_id"] == "h8"), None)
    baseline_complete = bool(
        baseline and baseline.get("execution_status") == "complete")
    nominated: list[dict[str, Any]] = []
    if baseline_complete:
        baseline_score = float(baseline["terminal_worst_normalized_score"])
        for value in values:
            if value["arm_id"] == "h8" or value.get("execution_status") != "complete":
                continue
            improvement = baseline_score - float(value["terminal_worst_normalized_score"])
            value["score_improvement_over_hold"] = improvement
            value["eligible"] = bool(value["capture_passed"]
                                     or improvement >= minimum_improvement)
            if value["eligible"]:
                nominated.append(value)
    nominated.sort(key=lambda value: (
        not bool(value["capture_passed"]),
        float(value["terminal_worst_normalized_score"]),
        float(value["terminal_max_source_rz_distance_m"]),
        float(value["terminal_max_rz_step_speed_m_per_s"]),
        float(value["terminal_max_absolute_source_ip_fraction"]),
        str(value["arm_id"])))
    return {
        "baseline_complete": baseline_complete,
        "baseline_terminal_worst_normalized_score": (
            baseline.get("terminal_worst_normalized_score") if baseline else None),
        "branch_metrics": values,
        "nominated_arm_ids": [value["arm_id"] for value in nominated],
        "selected_arm_id": nominated[0]["arm_id"] if nominated else None,
        "selected_capture_passed": bool(nominated and nominated[0]["capture_passed"]),
        "passed": bool(baseline_complete and nominated and
                       all(value.get("execution_status") == "complete"
                           for value in values)),
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
                  "cell_kind": "capture_replay"})
    return value


def offline(path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    checks: list[dict[str, Any]] = []
    try:
        stage, _, cfg, targets, parent, _ = load(path)
        for stream in build_matrix(stage, cfg, targets, parent):
            checks.append(validate_stream(stream, stage, cfg))
        if len(checks) != 9 or not all(value["passed"] for value in checks):
            failures.append("FULL_ACTION_MATRIX_NOT_ADMISSIBLE")
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {"schema_version": "rgeo-zgeo-1ms-id2z14-offline-v1",
            "source_revision": source_revision, "stage_config_sha256": CONFIG_SHA256,
            "passed": not failures, "failures": failures,
            "static_sequence_count": len(checks),
            "static_sequences_passed": sum(value["passed"] for value in checks),
            "sequence_checks": checks, "reset_calls": 0, "advance_attempts": 0,
            "plant_advance_gotsc_calls": 0, "models_fit_or_updated": 0}


def route_for(stage: dict[str, Any], execution: bool, raw_ok: bool,
              prefixes_ok: bool, metrics: dict[str, Any], replay_ok: bool,
              capture: bool) -> str:
    if not execution:
        return stage["routes"]["execution_or_interface_fail"]
    if not raw_ok:
        return stage["routes"]["raw_integrity_fail"]
    if not prefixes_ok:
        return stage["routes"]["prefix_mismatch"]
    if not metrics.get("passed"):
        return stage["routes"]["no_eligible_arm"]
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
    streams = build_matrix(stage, cfg, targets, parent)
    branch_rows: list[dict[str, Any]] = []
    for stream in streams:
        if not validate_stream(stream, stage, cfg)["passed"]:
            execution = False
            break
        row = execute_row(cfg, runtime, stream, reference, source_revision, output)
        rows.append(row)
        branch_rows.append(row)
        prefixes.append(z6.prefix_check(row, reference, 34, 33,
                                        stage["semantic_artifacts"]))
        if not row.get("passed") and not z6.safe_stop(row, runtime):
            execution = False
            break
    metrics = _metrics(branch_rows, stage)
    selected_arm = metrics.get("selected_arm_id")
    selected_stream = next((value for value in streams
                            if value["arm_id"] == selected_arm), None)
    selected_row = next((value for value in branch_rows
                         if value.get("arm_id") == selected_arm), None)
    replay_row = None
    replay_ok = False
    if execution and metrics.get("passed") and selected_stream and selected_row:
        replay_row = execute_row(cfg, runtime, replay_stream(selected_stream),
                                 selected_row, source_revision, output)
        rows.append(replay_row)
        prefixes.append(z6.prefix_check(replay_row, selected_row, 66, 65,
                                        stage["semantic_artifacts"]))
        replay_ok = z6.replay_check(selected_row, replay_row,
                                    stage["semantic_artifacts"])["passed"]
        if not replay_row.get("passed") and not z6.safe_stop(replay_row, runtime):
            execution = False
    counters = {key: sum(int(row.get(key, 0)) for row in rows) for key in
                ("reset_calls", "advance_attempts", "plant_advance_gotsc_calls",
                 "verified_plant_advances")}
    if len(rows) > 10 or any(counters[key] > 650 for key in counters):
        execution = False
    prefixes_ok = bool(prefixes and all(value.get("passed") for value in prefixes))
    inventory = io.raw_inventory(output, rows, stage)
    expected_files = 5 * sum(len(row.get("states", [])) for row in rows)
    raw_ok = bool(execution and not inventory["missing_required_artifacts"]
                  and inventory["required_artifact_files"] == expected_files)
    selected_metric = next((value for value in metrics.get("branch_metrics", [])
                            if value.get("arm_id") == selected_arm), None)
    capture = bool(selected_metric and selected_metric.get("capture_passed"))
    route = route_for(stage, execution, raw_ok, prefixes_ok, metrics, replay_ok, capture)
    scientific = {"branch_metrics": metrics,
                  "selected_arm_id": selected_arm,
                  "selected_capture_passed": capture,
                  "selected_replay_exact_passed": replay_ok}
    result = {"schema_version": SCHEMA, "source_revision": source_revision,
              "stage_config_sha256": CONFIG_SHA256,
              "passed": route == stage["routes"]["pass"], "route": route,
              "storage_gate": storage_gate, "run_root_isolation": isolation,
              "execution_integrity_passed": execution,
              "raw_integrity_passed": raw_ok, "prefix_checks": prefixes,
              "scientific_metrics": scientific,
              "rollouts_completed": len(rows),
              "complete_rollouts": sum(bool(value.get("passed")) for value in rows),
              "guarded_safe_stops": sum(z6.safe_stop(value, runtime) for value in rows),
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
    output = inside(output, "ID2Z14 output")
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
