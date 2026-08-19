#!/usr/bin/env python3
"""Run frozen ID-2Z18 full-horizon token development campaign."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_id2z17_full_f_transient_remaining_basis_beam as z17  # noqa: E402


z6, z7, io = z17.z6, z17.z7, z17.io
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z18_full_horizon_token_development.json"
CONFIG_SHA256 = "93d17647efda97cfc97813f30a85b8639ccac4cae9575be4206597999137a0a6"
SCHEMA = "rgeo-zgeo-1ms-id2z18-full-horizon-token-development-result-v1"
OFFLINE_SCHEMA = "rgeo-zgeo-1ms-id2z18-full-horizon-token-development-offline-v1"
TOKENS = frozenset("FAaEeH")


def inside(path: Path, label: str) -> Path:
    return z17.inside(path, label)


def load_json(path: Path) -> dict[str, Any]:
    return z17.load_json(path)


def _error(message: str) -> Exception:
    return z6._error(message)


def _require(stage: dict[str, Any]) -> None:
    if io.sha256(CONFIG) != CONFIG_SHA256:
        raise _error("ID2Z18 config hash mismatch")
    if stage != load_json(CONFIG):
        raise _error("frozen ID2Z18 config changed")
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2z18-full-horizon-token-development-v1",
        "identity": "rgeo-zgeo-1ms-id2z18-full-horizon-token-development-v1",
        "stage": "ID-2Z18", "takeover_time_ms": 1100,
        "control_period_ms": 1, "common_horizon_steps": 65,
        "common_terminal_state_index": 65, "exact_prefix_last_issue": 15,
        "exact_prefix_last_state": 16, "development_first_issue": 16,
        "development_last_issue": 47, "held_tail_first_issue": 48,
        "held_tail_last_issue": 64, "maximum_unique_fit_families": 14,
        "maximum_replay_rollouts": 2, "maximum_rollouts": 16,
        "maximum_reset_calls": 16, "maximum_advance_attempts": 1040,
        "maximum_gotsc_calls": 1040, "maximum_verified_plant_advances": 1040,
        "maximum_retained_states": 1056,
        "required_artifact_files_if_all_complete": 5280,
        "retry_after_any_advance_attempt": "forbidden",
        "models_fit_or_updated": 0,
        "data_use": "prospective_full_horizon_history_conditioned_model_development",
        "replay_fit_weight": 0,
        "calibration_and_holdout_execution": "forbidden_in_this_identity",
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise _error(f"frozen field changed: {key}")
    exploration = stage.get("empirical_exploration", {})
    if (exploration.get("abort_campaign_after_any_rollout_failure") is not True
            or exploration.get("all_sixteen_rollouts_complete_required_for_data_pass") is not True
            or exploration.get("stop_before_next_issue_after_any_failure") is not True):
        raise _error("campaign fail-fast contract changed")
    unique = stage.get("development_unique_specs", [])
    replay = stage.get("replay_specs", [])
    future = [*stage.get("future_calibration_specs_unexecuted", []),
              *stage.get("future_blind_holdout_specs_unexecuted", [])]
    if len(unique) != 14 or len(replay) != 2 or len(future) != 8:
        raise _error("schedule population changed")
    ids = [row.get("family_id") for row in [*unique, *replay, *future]]
    if len(ids) != len(set(ids)):
        raise _error("schedule identities are not unique")
    for row in [*unique, *future]:
        tokens = str(row.get("tokens", ""))
        if len(tokens) != 32 or any(token not in TOKENS for token in tokens):
            raise _error(f"invalid token schedule: {row.get('family_id')}")
    if any(int(row.get("fit_weight", -1)) != 1 for row in unique):
        raise _error("development fit weights changed")
    if any(int(row.get("fit_weight", -1)) != 0 for row in replay):
        raise _error("replay fit weights changed")


def _verify_evidence(stage: dict[str, Any]) -> dict[str, dict[str, Any]]:
    values: dict[str, dict[str, Any]] = {}
    for name, spec in stage["evidence"].items():
        path = inside(ROOT / spec["path"], name)
        if io.sha256(path) != spec["sha256"]:
            raise _error(f"evidence hash mismatch: {name}")
        values[name] = load_json(path) if path.suffix == ".json" else {}
    return values


def runtime_stage(stage: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    value = dict(base)
    value.update(stage)
    value["horizon_steps"] = int(stage["common_horizon_steps"])
    value["decision_state_index"] = int(stage["development_first_issue"])
    value["rounds"] = [{"round_index": 0, "decision_state_index": 16}]
    value["prefix_gates"] = {"checkpoint_indices": list(range(17))}
    value["empirical_exploration"] = dict(stage["empirical_exploration"])
    value["empirical_exploration"]["inner_novel_issue_clearance"] = dict(
        stage["empirical_exploration"]["simulator_development_preissue_clearance"])
    return value


def load(path: Path = CONFIG) -> tuple[dict[str, Any], dict[str, Any], Any,
                                       dict[str, Any], dict[str, Any], dict[str, Any]]:
    path = inside(path, "ID2Z18 config")
    if path != CONFIG.resolve():
        raise _error("alternate ID2Z18 config forbidden")
    stage = load_json(path)
    _require(stage)
    evidence = _verify_evidence(stage)
    result, audit, reference = (evidence["id2z17_result"],
                                evidence["id2z17_independent"],
                                evidence["id2z17_reference"])
    if (result.get("route") != stage["evidence"]["id2z17_result"]["required_route"]
            or result.get("passed") is not False
            or audit.get("audit_passed") is not True
            or audit.get("recomputed_route") != result.get("route")
            or reference.get("passed") is not True
            or len(reference.get("states", [])) != 66
            or len(reference.get("actions", [])) != 65):
        raise _error("ID2Z17 source evidence mismatch")
    _, base_runtime, cfg, targets, parent, _ = z17.load(z17.CONFIG)
    planned = [row["expected_card15_fields"] for row in parent["actions"][:16]]
    observed = [row["expected_card15_fields"] for row in reference["actions"][:16]]
    if planned != observed:
        raise _error("ID2Z17 full-F prefix changed")
    return stage, runtime_stage(stage, base_runtime), cfg, targets, parent, reference


def _apply_token(current: Any, virtual: Sequence[float], token: str,
                 q0: Any, targets: dict[str, Any], cfg: Any,
                 name: str) -> tuple[Any, list[float]]:
    if token in "FH":
        return z17.z14._apply_token(current, virtual, token, q0, targets, cfg, name)
    mapping = {"A": "p06_plus4", "a": "p06_minus4",
               "E": "p08_plus4", "e": "p08_minus4"}
    if token not in mapping:
        raise _error(f"unknown token: {token}")
    return z17._apply_arm(current, virtual, mapping[token], q0, targets, cfg, name)


def build_stream(stage: dict[str, Any], cfg: Any, targets: dict[str, Any],
                 parent: dict[str, Any], spec: dict[str, Any], role: str) -> dict[str, Any]:
    family_id, tokens = str(spec["family_id"]), str(spec["tokens"])
    decision, horizon = int(stage["development_first_issue"]), int(stage["common_horizon_steps"])
    sequence = list(parent["targets"][:decision])
    virtual_rows = [z17._extended(row["probe_virtual_action"])
                    for row in parent["actions"][:decision]]
    current, virtual, q0 = sequence[-1], list(virtual_rows[-1]), targets["q0"]
    for offset, token in enumerate(tokens):
        current, virtual = _apply_token(
            current, virtual, token, q0, targets, cfg,
            f"id2z18.{family_id}.{decision + offset}.{token}")
        sequence.append(current); virtual_rows.append(list(virtual))
    while len(sequence) < horizon:
        sequence.append(current); virtual_rows.append(list(virtual))
    actions = z6.z5.z3.z1.c1._actions(sequence, cfg, family_id, virtual_rows)
    return {
        "rollout_id": family_id, "candidate_id": family_id,
        "family_id": family_id, "pair_id": spec.get("pair_id"),
        "sign": spec.get("sign"), "tokens": tokens,
        "fit_weight": int(spec.get("fit_weight", 0)), "data_role": role,
        "round_index": 0, "round_id": "full_horizon_token_development",
        "cell_id": family_id, "cell_kind": "full_horizon_causal_token_history",
        "context_id": "canonical_source_full_f_state16",
        "coordinate": "exact_card15_f_p06_p08_token_history",
        "probe_issue_step": decision, "probe_duration_issues": len(tokens),
        "non_nominal_issue_steps": [decision + index for index, token in enumerate(tokens)
                                     if token != "H"],
        "targets": sequence, "actions": actions,
    }


def build_unique_streams(stage: dict[str, Any], cfg: Any, targets: dict[str, Any],
                         parent: dict[str, Any]) -> list[dict[str, Any]]:
    return [build_stream(stage, cfg, targets, parent, spec, "development")
            for spec in stage["development_unique_specs"]]


def replay_stream(source: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    value = dict(source)
    family_id = str(spec["family_id"])
    value.update({"rollout_id": family_id, "candidate_id": family_id,
                  "family_id": family_id, "source_family_id": spec["source_family_id"],
                  "fit_weight": 0, "data_role": "replay", "cell_id": family_id,
                  "cell_kind": "full_horizon_exact_replay"})
    return value


def build_execution_streams(stage: dict[str, Any], cfg: Any,
                            targets: dict[str, Any], parent: dict[str, Any]) -> list[dict[str, Any]]:
    unique = build_unique_streams(stage, cfg, targets, parent)
    by_id = {row["family_id"]: row for row in unique}
    return [*unique, *(replay_stream(by_id[spec["source_family_id"]], spec)
                       for spec in stage["replay_specs"])]


def build_all_static_streams(stage: dict[str, Any], cfg: Any,
                             targets: dict[str, Any], parent: dict[str, Any]) -> list[dict[str, Any]]:
    rows = build_execution_streams(stage, cfg, targets, parent)
    rows.extend(build_stream(stage, cfg, targets, parent, spec, "future_calibration_unexecuted")
                for spec in stage["future_calibration_specs_unexecuted"])
    rows.extend(build_stream(stage, cfg, targets, parent, spec, "future_blind_holdout_unexecuted")
                for spec in stage["future_blind_holdout_specs_unexecuted"])
    return rows


def validate_stream(stream: dict[str, Any], stage: dict[str, Any], cfg: Any,
                    reference: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    actions, horizon = stream["actions"], int(stage["common_horizon_steps"])
    if len(actions) != horizon or len(stream["targets"]) != horizon:
        failures.append("STREAM_DIMENSIONS")
    if len(stream.get("tokens", "")) != 32:
        failures.append("TOKEN_COUNT")
    expected_prefix = [row["expected_card15_fields"] for row in reference["actions"][:16]]
    if [row["expected_card15_fields"] for row in actions[:16]] != expected_prefix:
        failures.append("PREFIX_ACTIONS")
    for issue, action in enumerate(actions):
        if (int(action["issue_step"]) != issue
                or int(action["effect_state_index"]) != issue + 1
                or float(action["maximum_issued_delta_a"]) > .3000000001):
            failures.append(f"ACTION_CONTRACT:{issue}")
    for issue in range(48, 65):
        if (actions[issue]["expected_card15_fields"] != actions[47]["expected_card15_fields"]
                or float(actions[issue]["maximum_issued_delta_a"]) != 0.0):
            failures.append(f"TAIL_HOLD:{issue}")
    headroom = z6._headroom(stream["targets"], cfg)
    if headroom < -1e-9:
        failures.append("ABSOLUTE_CURRENT_LIMIT")
    return {"rollout_id": stream["rollout_id"], "data_role": stream["data_role"],
            "minimum_absolute_current_headroom_a": headroom,
            "maximum_issued_delta_a": max(float(row["maximum_issued_delta_a"])
                                            for row in actions),
            "passed": not failures, "failures": list(dict.fromkeys(failures))}


def increment_geometry(stage: dict[str, Any], cfg: Any, targets: dict[str, Any],
                       parent: dict[str, Any]) -> dict[str, Any]:
    current = parent["targets"][15]
    virtual = z17._extended(parent["actions"][15]["probe_virtual_action"])
    columns = []
    for token in "FAE":
        target, _ = _apply_token(current, virtual, token, targets["q0"], targets, cfg,
                                 f"id2z18.geometry.{token}")
        columns.append(np.asarray(target.current_a_tsc, dtype=float)
                       - np.asarray(current.current_a_tsc, dtype=float))
    matrix = np.stack(columns, axis=1)
    rank = int(np.linalg.matrix_rank(matrix, tol=1e-12))
    condition = float(np.linalg.cond(matrix))
    return {"token_order": ["F", "A", "E"], "rank": rank, "condition": condition,
            "columns_a_tsc": [column.tolist() for column in columns],
            "passed": bool(rank == int(stage["measurement_gates"]["required_increment_rank"])
                           and condition <= float(stage["measurement_gates"]["maximum_increment_condition"]))}


def pair_metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> list[dict[str, Any]]:
    by_id = {str(row.get("family_id")): row for row in rows}
    values: list[dict[str, Any]] = []
    for pair_id in [f"d{index:02d}" for index in range(6)]:
        plus, minus = by_id.get(f"{pair_id}_plus"), by_id.get(f"{pair_id}_minus")
        complete = bool(plus and minus and plus.get("passed") and minus.get("passed")
                        and len(plus.get("states", [])) == 66
                        and len(minus.get("states", [])) == 66)
        separations = []
        if complete:
            for index in range(17, 66):
                separations.append(math.hypot(
                    float(plus["states"][index]["r_geo_m"]) - float(minus["states"][index]["r_geo_m"]),
                    float(plus["states"][index]["z_geo_m"]) - float(minus["states"][index]["z_geo_m"])))
        maximum = max(separations, default=0.0)
        values.append({"pair_id": pair_id, "complete": complete,
                       "maximum_rz_separation_m": maximum,
                       "passed": bool(complete and maximum >= float(
                           stage["measurement_gates"]["minimum_each_pair_max_rz_separation_m"]))})
    return values


def replay_metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> list[dict[str, Any]]:
    by_id = {str(row.get("family_id")): row for row in rows}
    values = []
    for spec in stage["replay_specs"]:
        check = z6.replay_check(by_id.get(spec["source_family_id"]),
                                by_id.get(spec["family_id"]), stage["semantic_artifacts"])
        values.append({"replay_family_id": spec["family_id"],
                       "source_family_id": spec["source_family_id"], **check})
    return values


def route_for(stage: dict[str, Any], execution: bool, raw_ok: bool,
              prefixes_ok: bool, complete_count: int,
              replays_ok: bool, signal_ok: bool) -> str:
    routes = stage["routes"]
    if not execution:
        return routes["execution_or_interface_fail"]
    if not raw_ok:
        return routes["raw_integrity_fail"]
    if not prefixes_ok:
        return routes["prefix_mismatch"]
    if complete_count != int(stage["maximum_rollouts"]):
        return routes["campaign_incomplete"]
    if not replays_ok:
        return routes["replay_fail"]
    return routes["data_pass" if signal_ok else "signal_or_support_fail"]


def execute_row(cfg: Any, runtime: dict[str, Any], stream: dict[str, Any],
                reference: dict[str, Any], source_revision: str,
                output: Path, *, runner_cls: type | None = None) -> dict[str, Any]:
    if Path(cfg.run_root).resolve() != (output / "rollouts").resolve():
        raise _error("run root isolation failed")
    row = z6.one_rollout(cfg, runtime, stream, z6._reference(reference, 17),
                         runner_cls=runner_cls)
    row.update({"schema_version": SCHEMA, "source_revision": source_revision,
                "family_id": stream["family_id"], "pair_id": stream.get("pair_id"),
                "sign": stream.get("sign"), "tokens": stream["tokens"],
                "fit_weight": stream["fit_weight"], "data_role": stream["data_role"]})
    io.write_new(output / f"{stream['rollout_id']}.json", row)
    return row


def offline(path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    checks: list[dict[str, Any]] = []
    geometry: dict[str, Any] = {}
    try:
        stage, _, cfg, targets, parent, reference = load(path)
        streams = build_all_static_streams(stage, cfg, targets, parent)
        checks = [validate_stream(row, stage, cfg, reference) for row in streams]
        geometry = increment_geometry(stage, cfg, targets, parent)
        roles = [row["data_role"] for row in streams]
        if len(streams) != 24 or len({row["rollout_id"] for row in streams}) != 24:
            failures.append("STATIC_STREAM_POPULATION")
        if roles.count("development") != 14 or roles.count("replay") != 2:
            failures.append("EXECUTION_ROLE_POPULATION")
        if roles.count("future_calibration_unexecuted") != 4 or roles.count(
                "future_blind_holdout_unexecuted") != 4:
            failures.append("FUTURE_ROLE_POPULATION")
        if not all(row["passed"] for row in checks):
            failures.append("STATIC_STREAM_INADMISSIBLE")
        if not geometry.get("passed"):
            failures.append("INCREMENT_GEOMETRY")
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {"schema_version": OFFLINE_SCHEMA, "source_revision": source_revision,
            "stage_config_sha256": CONFIG_SHA256, "passed": not failures,
            "failures": failures, "static_stream_count": len(checks),
            "static_streams_passed": sum(bool(row.get("passed")) for row in checks),
            "stream_checks": checks, "increment_geometry": geometry,
            "execution_rollouts_planned": 16,
            "future_calibration_rollouts_planned_but_unexecuted": 4,
            "future_blind_holdout_rollouts_planned_but_unexecuted": 4,
            "reset_calls": 0, "advance_attempts": 0,
            "plant_advance_gotsc_calls": 0, "models_fit_or_updated": 0,
            "calibration_or_holdout_records_read": 0}


def execute(stage: dict[str, Any], runtime: dict[str, Any], cfg: Any,
            targets: dict[str, Any], parent: dict[str, Any], reference: dict[str, Any],
            source_revision: str, output: Path, storage_gate: dict[str, Any]) -> dict[str, Any]:
    isolation = z7.configure_run_root(cfg, output)
    streams = build_execution_streams(stage, cfg, targets, parent)
    rows: list[dict[str, Any]] = []
    prefixes: list[dict[str, Any]] = []
    execution = True
    for stream in streams:
        row = execute_row(cfg, runtime, stream, reference, source_revision, output)
        rows.append(row)
        prefixes.append(z6.prefix_check(row, reference, 17, 16,
                                        stage["semantic_artifacts"]))
        if not row.get("passed"):
            if not z6.safe_stop(row, runtime):
                execution = False
            break
    counters = {key: sum(int(row.get(key, 0)) for row in rows) for key in
                ("reset_calls", "advance_attempts", "plant_advance_gotsc_calls",
                 "verified_plant_advances")}
    if len(rows) > 16 or any(counters[key] > 1040 for key in counters):
        execution = False
    inventory = io.raw_inventory(output, rows, stage)
    expected_files = 5 * sum(len(row.get("states", [])) for row in rows)
    raw_ok = bool(not inventory["missing_required_artifacts"]
                  and inventory["required_artifact_files"] == expected_files)
    prefixes_ok = bool(prefixes and all(value.get("passed") for value in prefixes))
    complete_count = sum(bool(row.get("passed") and len(row.get("states", [])) == 66)
                         for row in rows)
    replay_values = replay_metrics(rows, stage)
    replay_ok = bool(len(replay_values) == 2 and all(row["passed"] for row in replay_values))
    pair_values = pair_metrics(rows, stage)
    geometry = increment_geometry(stage, cfg, targets, parent)
    unique_fit_count = len({row.get("family_id") for row in rows
                            if row.get("fit_weight") == 1 and row.get("passed")})
    signal_ok = bool(unique_fit_count == 14 and geometry.get("passed")
                     and len(pair_values) == 6 and all(row["passed"] for row in pair_values))
    route = route_for(stage, execution, raw_ok, prefixes_ok, complete_count,
                      replay_ok, signal_ok)
    scientific = {"fit_weight_one_unique_history_count": unique_fit_count,
                  "replay_metrics": replay_values, "paired_family_metrics": pair_values,
                  "increment_geometry": geometry,
                  "calibration_rollouts_executed": 0,
                  "blind_holdout_rollouts_executed": 0,
                  "signal_and_support_passed": signal_ok}
    result = {"schema_version": SCHEMA, "source_revision": source_revision,
              "stage_config_sha256": CONFIG_SHA256,
              "passed": route == stage["routes"]["data_pass"], "route": route,
              "storage_gate": storage_gate, "run_root_isolation": isolation,
              "execution_integrity_passed": execution,
              "raw_integrity_passed": raw_ok, "prefix_checks": prefixes,
              "scientific_metrics": scientific, "rollouts_started": len(rows),
              "complete_rollouts": complete_count,
              "campaign_aborted_after_rollout_failure": bool(len(rows) < 16),
              **counters, **inventory, "models_fit_or_updated": 0,
              "calibration_or_holdout_records_read": 0,
              "claim_boundary": stage["claim_boundary"]}
    io.write_new(output / "result.json", result)
    return result


def _failure_result(stage: dict[str, Any], source_revision: str, output: Path,
                    storage_gate: dict[str, Any], exc: Exception) -> dict[str, Any]:
    rows = []
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
                     "missing_required_artifacts": [f"FINALIZER:{type(inv_exc).__name__}:{inv_exc}"]}
    return {"schema_version": SCHEMA, "source_revision": source_revision,
            "stage_config_sha256": CONFIG_SHA256, "passed": False,
            "route": stage["routes"]["execution_or_interface_fail"],
            "failure": f"{type(exc).__name__}:{exc}", "storage_gate": storage_gate,
            "rollouts_started": len(rows), "campaign_aborted_after_rollout_failure": True,
            **counters, **inventory, "models_fit_or_updated": 0,
            "calibration_or_holdout_records_read": 0,
            "claim_boundary": "Best-effort classified execution failure; no scientific verdict."}


def run(path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = inside(output, "ID2Z18 output")
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
                  "reasons": preflight["failures"], "rollouts_started": 0,
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
