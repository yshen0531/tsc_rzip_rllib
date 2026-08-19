#!/usr/bin/env python3
"""Run frozen ID-2Z17 full-F-transient remaining-basis beam."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_id2z16_full_f_prefix_beam_reachability as z16  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr2_spec import (  # noqa: E402
    build_one_ms_nr2_specs,
    build_one_ms_nr2_targets,
)


z14, z6, z7, io = z16.z14, z16.z6, z16.z7, z16.io
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z17_full_f_transient_remaining_basis_beam.json"
CONFIG_SHA256 = "4308452e9480574a13703b41816c6fc7145a4b559992aac86e2ced58a612486a"
SCHEMA = "rgeo-zgeo-1ms-id2z17-full-f-transient-remaining-basis-beam-result-v1"
BASE_DIRECTIONS = ("p00", "p02", "p05", "p06", "p08")
ROUND0_ARM_IDS = (
    "h4", "p00_plus4", "p00_minus4", "p02_plus4", "p02_minus4",
    "p05_plus4", "p05_minus4", "p06_plus4", "p06_minus4",
    "p08_plus4", "p08_minus4",
)


def inside(path: Path, label: str) -> Path:
    return z16.inside(path, label)


def load_json(path: Path) -> dict[str, Any]:
    return z16.load_json(path)


def _require(stage: dict[str, Any]) -> None:
    if io.sha256(CONFIG) != CONFIG_SHA256:
        raise z6._error("ID2Z17 config hash mismatch")
    if stage != load_json(CONFIG):
        raise z6._error("frozen ID2Z17 config changed")
    if tuple(stage.get("base_direction_ids", ())) != BASE_DIRECTIONS:
        raise z6._error("base direction order changed")
    if tuple(row.get("arm_id") for row in stage.get("round0_candidate_specs", ())) != ROUND0_ARM_IDS:
        raise z6._error("round0 arm order changed")
    exact = {
        "takeover_time_ms": 1100, "control_period_ms": 1,
        "common_horizon_steps": 65, "common_terminal_state_index": 65,
        "source_prefix_last_issue": 47, "source_prefix_last_state": 48,
        "beam_width": 2, "macro_issues": 4,
        "maximum_static_sequences": 121, "maximum_search_branches": 17,
        "maximum_replay_rollouts": 1, "maximum_rollouts": 18,
        "maximum_reset_calls": 18, "maximum_advance_attempts": 1170,
        "maximum_gotsc_calls": 1170, "maximum_verified_plant_advances": 1170,
        "maximum_retained_states": 1188,
        "required_artifact_files_if_all_complete": 5940,
        "models_fit_or_updated": 0,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise z6._error(f"frozen field changed: {key}")
    if [(row.get("round_index"), row.get("decision_state_index"),
         row.get("macro_last_issue")) for row in stage.get("rounds", [])] != [
            (0, 48, 51), (1, 52, 55)]:
        raise z6._error("round clocks changed")
    if (stage.get("data_use") !=
            "physical_basis_reachability_route_evidence_only_zero_fit_weight"
            or stage.get("fit_calibration_holdout_controller_expert_bc_dagger_rl_fixture_use")
            != "forbidden"):
        raise z6._error("data-use boundary changed")


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
        "candidate_specs": list(stage["round0_candidate_specs"]),
        "empirical_exploration": dict(stage["empirical_exploration"]),
        "measurement_gates": dict(stage["measurement_gates"]),
        "semantic_artifacts": list(stage["semantic_artifacts"]),
    })
    return value


def _nr2_residual_targets(cfg: Any, reference: dict[str, Any]) -> dict[str, Any]:
    source = reference["states"][0]["actual_current_a_tsc"]
    values: dict[str, Any] = {}
    for pair in (0, 2, 5, 6, 8):
        for sign_value, sign_name in ((1, "plus"), (-1, "minus")):
            spec = next(row for row in build_one_ms_nr2_specs()
                        if row.split == "development" and row.pair_index == pair
                        and row.sign == sign_value)
            built = build_one_ms_nr2_targets(
                spec, source_current_a_tsc=source, turns_tsc=cfg.turns_tsc)
            issue = next(index for index, (amplitude, _) in enumerate(spec.schedule)
                         if amplitude != "zero")
            values[f"p{pair:02d}_{sign_name}4"] = built[issue]
    return values


def _selected_z16_parent(stage: dict[str, Any], cfg: Any,
                         targets: dict[str, Any]) -> dict[str, Any]:
    z16_stage = load_json(z16.CONFIG)
    _, _, _, _, full_f, _ = z16.load(z16.CONFIG)
    roots = z16.build_round(z16_stage, cfg, targets, full_f, 32, 0, "round0")
    f8 = next(row for row in roots if row["arm_id"] == "f8")
    children = z16.build_round(z16_stage, cfg, targets, f8, 40, 1, "round1__f8")
    return next(row for row in children if row["arm_id"] == "f8")


def load(path: Path = CONFIG) -> tuple[dict[str, Any], dict[str, Any], Any,
                                       dict[str, Any], dict[str, Any], dict[str, Any]]:
    path = inside(path, "ID2Z17 config")
    if path != CONFIG.resolve():
        raise z6._error("alternate ID2Z17 config forbidden")
    stage = load_json(path)
    _require(stage)
    evidence = _verify_evidence(stage)
    result = evidence["id2z16_result"]
    audit = evidence["id2z16_independent"]
    reference = evidence["id2z16_critical_replay"]
    selected = evidence["id2z16_selected_path"]
    if (result.get("route") != stage["evidence"]["id2z16_result"]["required_route"]
            or result.get("passed") is not False
            or result.get("scientific_metrics", {}).get("selected_path_id") != "f100__f8__f8"
            or result.get("scientific_metrics", {}).get("selected_replay_exact_passed") is not True
            or audit.get("audit_passed") is not True
            or audit.get("recomputed_route") != result.get("route")
            or reference.get("passed") is not True
            or selected.get("passed") is not True
            or len(reference.get("states", [])) != 66
            or len(reference.get("actions", [])) != 65):
        raise z6._error("ID2Z16 source evidence mismatch")
    if evidence["id1c0_result"].get("passed") is not True:
        raise z6._error("ID1C0 direction evidence mismatch")
    _, base_runtime, cfg, targets, _, _ = z16.load(
        ROOT / stage["evidence"]["id2z16_config"]["path"])
    parent = _selected_z16_parent(stage, cfg, targets)
    planned = [row["expected_card15_fields"] for row in parent["actions"]]
    if (planned != [row["expected_card15_fields"] for row in selected["actions"]]
            or planned != [row["expected_card15_fields"] for row in reference["actions"]]):
        raise z6._error("planned selected parent differs from ID2Z16 evidence")
    prefix = z6.prefix_check(reference, selected, 66, 65, stage["semantic_artifacts"])
    if not prefix.get("passed"):
        raise z6._error("ID2Z16 selected replay mismatch")
    values = dict(targets)
    values.update(_nr2_residual_targets(cfg, reference))
    base = parent["targets"][47]
    q0 = targets["q0"]
    frozen = stage["zero_tsc_action_audit"]["translated_first_target_card15_fields"]
    for arm_id, expected in frozen.items():
        translated = z6.z5.z3.z1.c1._translated_target(
            base, q0, values[arm_id], cfg, f"id2z17.audit.{arm_id}")
        if list(translated.card15_fields) != expected:
            raise z6._error(f"translated target changed: {arm_id}")
    return stage, runtime_stage(stage, base_runtime), cfg, values, parent, reference


def _extended(virtual: Sequence[float]) -> list[float]:
    values = [float(value) for value in virtual]
    return values + [0.0] * (10 - len(values))


def _apply_arm(current: Any, virtual: Sequence[float], arm_id: str,
               q0: Any, targets: dict[str, Any], cfg: Any,
               name: str) -> tuple[Any, list[float]]:
    values = _extended(virtual)
    if arm_id == "h4":
        return current, values
    if arm_id not in targets:
        raise z6._error(f"unknown action arm: {arm_id}")
    target = z6.z5.z3.z1.c1._translated_target(
        current, q0, targets[arm_id], cfg, f"{name}.target")
    direction = arm_id[:3]
    index = 5 + BASE_DIRECTIONS.index(direction)
    values[index] += 1.0 if "_plus" in arm_id else -1.0
    return target, values


def build_stream(stage: dict[str, Any], cfg: Any, targets: dict[str, Any],
                 parent: dict[str, Any], decision: int, round_index: int,
                 namespace: str, spec: dict[str, Any]) -> dict[str, Any]:
    if len(parent.get("targets", [])) < decision:
        raise z6._error("parent prefix too short")
    arm_id = str(spec["arm_id"])
    rollout_id = f"{namespace}__{arm_id}"
    sequence = list(parent["targets"][:decision])
    virtual_rows = [_extended(row["probe_virtual_action"])
                    for row in parent["actions"][:decision]]
    current, virtual, q0 = sequence[-1], list(virtual_rows[-1]), targets["q0"]
    for offset in range(int(stage["macro_issues"])):
        current, virtual = _apply_arm(
            current, virtual, arm_id, q0, targets, cfg,
            f"id2z17.{rollout_id}.{decision + offset}")
        sequence.append(current)
        virtual_rows.append(list(virtual))
    while len(sequence) < int(stage["common_horizon_steps"]):
        sequence.append(current)
        virtual_rows.append(list(virtual))
    actions = z6.z5.z3.z1.c1._actions(sequence, cfg, rollout_id, virtual_rows)
    parent_path = str(parent.get("path_id") or "f100__f8__f8")
    path_id = f"{parent_path}__{arm_id}"
    return {
        "rollout_id": rollout_id, "candidate_id": rollout_id,
        "arm_id": arm_id, "base_direction_id": spec["base_direction_id"],
        "sign": spec.get("sign"), "parent_path_id": parent_path,
        "path_id": path_id, "fit_weight": 0, "round_index": round_index,
        "round_id": "full_f_transient_state48" if round_index == 0 else "selected_state52",
        "cell_id": rollout_id, "cell_kind": "full_f_transient_remaining_basis_branch",
        "context_id": f"round{round_index}_state{decision}_causal_prefix",
        "direction_id": "hold" if arm_id == "h4" else arm_id[:-1],
        "coordinate": "exact_card15_first_event_cumulative4",
        "probe_issue_step": decision,
        "probe_duration_issues": int(stage["macro_issues"]),
        "non_nominal_issue_steps": ([] if arm_id == "h4" else
                                     list(range(decision, decision + int(stage["macro_issues"])))),
        "targets": sequence, "actions": actions,
    }


def build_round(stage: dict[str, Any], cfg: Any, targets: dict[str, Any],
                parent: dict[str, Any], decision: int, round_index: int,
                namespace: str, specs: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    return [build_stream(stage, cfg, targets, parent, decision, round_index,
                         namespace, spec) for spec in specs]


def validate_stream(stream: dict[str, Any], stage: dict[str, Any], cfg: Any) -> dict[str, Any]:
    failures: list[str] = []
    actions = stream["actions"]
    horizon, decision = int(stage["common_horizon_steps"]), int(stream["probe_issue_step"])
    last = decision + int(stage["macro_issues"]) - 1
    if len(actions) != horizon or len(stream["targets"]) != horizon:
        failures.append("STREAM_DIMENSIONS")
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
            "arm_id": stream["arm_id"], "base_direction_id": stream["base_direction_id"],
            "minimum_absolute_current_headroom_a": headroom,
            "passed": not failures, "failures": list(dict.fromkeys(failures))}


def _metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    return z16._metrics(rows, stage)


def _distinct_parents(root_metrics: dict[str, Any],
                      root_streams: Sequence[dict[str, Any]],
                      limit: int = 2) -> list[str]:
    by_path = {row["path_id"]: row for row in root_streams}
    selected: list[str] = []
    used: set[str] = set()
    for path in root_metrics.get("ranked_path_ids", []):
        stream = by_path.get(path)
        if stream is None or stream["arm_id"] == "h4":
            continue
        direction = str(stream["base_direction_id"])
        if direction in used:
            continue
        selected.append(path); used.add(direction)
        if len(selected) == limit:
            break
    return selected


def replay_stream(selected: dict[str, Any]) -> dict[str, Any]:
    value = dict(selected)
    value.update({"rollout_id": "critical_replay", "candidate_id": "critical_replay",
                  "arm_id": "critical_replay", "fit_weight": 0,
                  "round_id": "critical_replay", "cell_id": "critical_replay",
                  "cell_kind": "new_basis_selected_path_replay"})
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
        specs = list(stage["round0_candidate_specs"])
        roots = build_round(stage, cfg, targets, parent, 48, 0, "round0", specs)
        checks.extend(validate_stream(stream, stage, cfg) for stream in roots)
        for root in roots:
            if root["arm_id"] == "h4":
                continue
            for child in build_round(stage, cfg, targets, root, 52, 1,
                                     f"static__{root['arm_id']}", specs):
                checks.append(validate_stream(child, stage, cfg))
        if len(checks) != 121 or not all(value["passed"] for value in checks):
            failures.append("FULL_STATIC_TREE_NOT_ADMISSIBLE")
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {"schema_version": "rgeo-zgeo-1ms-id2z17-offline-v1",
            "source_revision": source_revision, "stage_config_sha256": CONFIG_SHA256,
            "passed": not failures, "failures": failures,
            "static_sequence_count": len(checks),
            "static_sequences_passed": sum(value["passed"] for value in checks),
            "sequence_checks": checks, "reset_calls": 0, "advance_attempts": 0,
            "plant_advance_gotsc_calls": 0, "models_fit_or_updated": 0}


def route_for(stage: dict[str, Any], execution: bool, raw_ok: bool,
              prefixes_ok: bool, round0: dict[str, Any], round1: dict[str, Any],
              early_capture: bool, parent_count: int, replay_ok: bool) -> str:
    if not execution:
        return stage["routes"]["execution_or_interface_fail"]
    if not raw_ok:
        return stage["routes"]["raw_integrity_fail"]
    if not prefixes_ok:
        return stage["routes"]["prefix_mismatch"]
    if not round0.get("complete"):
        return stage["routes"]["beam_incomplete"]
    if not early_capture and (parent_count != 2 or not round1.get("complete")):
        return stage["routes"]["beam_incomplete"]
    if not replay_ok:
        return stage["routes"]["replay_fail"]
    captured = early_capture or bool(round1.get("selected_capture_passed"))
    return stage["routes"]["capture_pass" if captured else "no_capture"]


def execute(stage: dict[str, Any], runtime: dict[str, Any], cfg: Any,
            targets: dict[str, Any], parent: dict[str, Any], reference: dict[str, Any],
            source_revision: str, output: Path, storage_gate: dict[str, Any]) -> dict[str, Any]:
    isolation = z7.configure_run_root(cfg, output)
    rows: list[dict[str, Any]] = []
    prefixes: list[dict[str, Any]] = []
    execution = True
    specs = list(stage["round0_candidate_specs"])
    root_streams = build_round(stage, cfg, targets, parent, 48, 0, "round0", specs)
    root_rows: list[dict[str, Any]] = []
    for stream in root_streams:
        row = execute_row(cfg, runtime, stream, reference, source_revision, output)
        rows.append(row); root_rows.append(row)
        prefixes.append(z6.prefix_check(row, reference, 49, 48,
                                        stage["semantic_artifacts"]))
        if not row.get("passed") and not z6.safe_stop(row, runtime):
            execution = False
            break
    root_metrics = _metrics(root_rows, stage)
    early_capture = bool(root_metrics.get("selected_capture_passed"))
    parent_ids = _distinct_parents(root_metrics, root_streams)
    root_stream_by_path = {row["path_id"]: row for row in root_streams}
    root_row_by_path = {row.get("path_id"): row for row in root_rows}
    child_streams: list[dict[str, Any]] = []
    child_rows: list[dict[str, Any]] = []
    if execution and not early_capture and len(parent_ids) == 2:
        chosen_specs = [specs[0]] + [next(spec for spec in specs
                                         if spec["arm_id"] == root_stream_by_path[path]["arm_id"])
                                       for path in parent_ids]
        for path in parent_ids:
            parent_stream, parent_row = root_stream_by_path[path], root_row_by_path[path]
            children = build_round(stage, cfg, targets, parent_stream, 52, 1,
                                   f"round1__{parent_stream['arm_id']}", chosen_specs)
            child_streams.extend(children)
            for stream in children:
                row = execute_row(cfg, runtime, stream, parent_row,
                                  source_revision, output)
                rows.append(row); child_rows.append(row)
                prefixes.append(z6.prefix_check(row, parent_row, 53, 52,
                                                stage["semantic_artifacts"]))
                if not row.get("passed") and not z6.safe_stop(row, runtime):
                    execution = False
                    break
            if not execution:
                break
    child_metrics = _metrics(child_rows, stage)
    if early_capture:
        selected_path = root_metrics.get("selected_path_id")
        selected_stream = next((row for row in root_streams if row["path_id"] == selected_path), None)
        selected_row = next((row for row in root_rows if row.get("path_id") == selected_path), None)
    else:
        selected_path = child_metrics.get("selected_path_id")
        selected_stream = next((row for row in child_streams if row["path_id"] == selected_path), None)
        selected_row = next((row for row in child_rows if row.get("path_id") == selected_path), None)
    replay_ok = False
    if execution and selected_stream is not None and selected_row is not None:
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
    if len(rows) > 18 or any(counters[key] > 1170 for key in counters):
        execution = False
    prefixes_ok = bool(prefixes and all(value.get("passed") for value in prefixes))
    inventory = io.raw_inventory(output, rows, stage)
    expected_files = 5 * sum(len(row.get("states", [])) for row in rows)
    raw_ok = bool(execution and not inventory["missing_required_artifacts"]
                  and inventory["required_artifact_files"] == expected_files)
    route = route_for(stage, execution, raw_ok, prefixes_ok, root_metrics,
                      child_metrics, early_capture, len(parent_ids), replay_ok)
    scientific = {"round0_metrics": root_metrics,
                  "round0_selected_parent_path_ids": parent_ids,
                  "round0_early_capture": early_capture,
                  "round1_metrics": child_metrics,
                  "selected_path_id": selected_path,
                  "selected_capture_passed": bool(early_capture or child_metrics.get(
                      "selected_capture_passed", False)),
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
    output = inside(output, "ID2Z17 output")
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
