#!/usr/bin/env python3
"""Run the frozen ID-2Z31 qZ event-phase discriminator."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_id2z30_fresh_q_model_qualification as z30  # noqa: E402


CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z31_event_phase_discriminator.json"
CONFIG_SHA256 = "f4bec9a86014ea8edbee89d8848e768ddb2f52bbf7116c8d87119df9101c86de"
SCHEMA = "rgeo-zgeo-1ms-id2z31-event-phase-discriminator-result-v1"
ROW_SCHEMA = "rgeo-zgeo-1ms-id2z31-event-phase-discriminator-row-v1"
OFFLINE_SCHEMA = "rgeo-zgeo-1ms-id2z31-event-phase-discriminator-offline-v1"


def _inside(path: Path, label: str) -> Path:
    value = path.resolve()
    try:
        value.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(f"ID2Z31 {label} leaves repository") from exc
    return value


def _sha(path: Path) -> str:
    return hashlib.sha256(_inside(path, "hash path").read_bytes()).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(_inside(path, "JSON path").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("ID2Z31 JSON object required")
    return value


def _require(stage: dict[str, Any]) -> None:
    if _sha(CONFIG) != CONFIG_SHA256 or stage != _read(CONFIG):
        raise ValueError("ID2Z31 frozen config changed")
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2z31-event-phase-discriminator-v1",
        "identity": "rgeo-zgeo-1ms-id2z31-event-phase-discriminator-v1",
        "stage": "ID-2Z31", "takeover_time_ms": 1100,
        "control_period_ms": 1, "common_horizon_steps": 73,
        "event_window_effect_states": [47, 48, 49, 50, 51, 52],
        "positive_r_event_threshold_m": .0002,
        "branch_phase_issues": [43, 44, 45],
        "maximum_rollouts": 6, "maximum_reset_calls": 6,
        "maximum_advance_attempts": 438, "maximum_gotsc_calls": 438,
        "maximum_verified_plant_advances": 438,
        "maximum_retained_states": 444,
        "required_artifact_files_if_all_complete": 2220,
        "retry_after_any_advance_attempt": "forbidden",
        "models_fit_or_updated": 0,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise ValueError(f"ID2Z31 frozen field changed: {key}")
    ids = [row.get("family_id") for row in stage.get("rollout_specs", [])]
    if len(ids) != 6 or len(ids) != len(set(ids)):
        raise ValueError("ID2Z31 rollout matrix changed")


def load(config: Path = CONFIG) -> tuple[dict[str, Any], dict[str, Any], Any,
                                          dict[str, Any], dict[str, Any]]:
    if config.resolve() != CONFIG.resolve():
        raise ValueError("ID2Z31 alternate config forbidden")
    stage = _read(config); _require(stage)
    evidence: dict[str, dict[str, Any]] = {}
    for name, spec in stage["evidence"].items():
        path = ROOT / spec["path"]
        if _sha(path) != spec["sha256"]:
            raise ValueError(f"ID2Z31 evidence hash mismatch: {name}")
        if path.suffix == ".json":
            evidence[name] = _read(path)
    if (evidence["id2z26r1_preflight"].get("passed") is not True
            or evidence["id2z26r1_independent"].get("audit_passed") is not True
            or evidence["id2z30_result"].get("route")
            != stage["evidence"]["id2z30_result"]["required_route"]
            or evidence["id2z30_independent"].get("audit_passed") is not True):
        raise ValueError("ID2Z31 prerequisite identity mismatch")
    _, base, cfg, preflight, tracked, _ = z30.load(z30.CONFIG)
    return stage, base, cfg, preflight, tracked


def build_streams(stage: dict[str, Any], cfg: Any, preflight: dict[str, Any],
                  tracked: dict[str, Any]) -> list[dict[str, Any]]:
    center = next(row for row in preflight["prospective_static_streams"]
                  if row["rollout_id"] == "baseline_transition_center")
    rows: list[dict[str, Any]] = []; by_id: dict[str, dict[str, Any]] = {}
    for spec in stage["rollout_specs"]:
        family = spec["family_id"]
        if spec["kind"] == "replay":
            row = copy.deepcopy(by_id[spec["source_family_id"]])
            row.update({"rollout_id": family, "candidate_id": family,
                        "family_id": family, "kind": "replay",
                        "data_role": spec["data_role"],
                        "source_family_id": spec["source_family_id"]})
        else:
            phase = spec.get("phase_issue")
            fields = ([tuple(value) for value in center["card15_targets"]]
                      if phase is None else z30._branch_fields(
                          preflight, int(phase), spec["axis_id"], spec["initial_sign"]))
            targets = z30.z27._targets(fields, cfg, family)
            actions = z30.z27._actions(targets, cfg, family, tracked)
            checkpoint = 32 if phase is None else int(phase)
            row = {"rollout_id": family, "candidate_id": family,
                   "family_id": family, "kind": spec["kind"],
                   "data_role": spec["data_role"], "phase_issue": phase,
                   "axis_id": spec.get("axis_id"),
                   "initial_sign": spec.get("initial_sign"), "fit_weight": 0,
                   "round_index": 0, "round_id": "event_phase_discriminator",
                   "cell_id": family, "cell_kind": "zero_fit_event_phase",
                   "context_id": f"canonical_dynamic_state{checkpoint}",
                   "coordinate": "qz_sustained8_return8_event_map",
                   "probe_issue_step": phase,
                   "probe_duration_issues": 0 if phase is None else 8,
                   "prefix_checkpoint_last_state": checkpoint,
                   "non_nominal_issue_steps": [] if phase is None else list(
                       range(int(phase), int(phase) + 16)),
                   "targets": targets, "actions": actions}
        rows.append(row); by_id[family] = row
    return rows


def event_map(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    window = [int(value) for value in stage["event_window_effect_states"]]
    threshold = float(stage["positive_r_event_threshold_m"])
    mapped: list[dict[str, Any]] = []
    for row in rows:
        states = row.get("states", [])
        events = []
        if row.get("passed") and len(states) == 74:
            for state_index in window:
                delta = float(states[state_index]["r_geo_m"]) - float(
                    states[state_index - 1]["r_geo_m"])
                if delta > threshold:
                    events.append({"effect_state_index": state_index,
                                   "delta_r_m": delta})
        mapped.append({"family_id": row.get("family_id"),
                       "complete": bool(row.get("passed") and len(states) == 74),
                       "events": events, "event_count": len(events),
                       "passed": bool(row.get("passed") and len(states) == 74
                                      and len(events) == 1)})
    return {"passed": len(mapped) == 6 and all(row["passed"] for row in mapped),
            "threshold_m": threshold, "window_effect_states": window,
            "families": mapped}


def offline(config: Path, revision: str) -> dict[str, Any]:
    failures: list[str] = []
    try:
        stage, _, cfg, preflight, tracked = load(config)
        streams = build_streams(stage, cfg, preflight, tracked)
        checks = [z30.validate_stream(row, cfg) for row in streams]
        if len(streams) != 6 or not all(row["passed"] for row in checks):
            failures.append("STATIC_STREAMS")
    except Exception as exc:
        checks = []; failures.append(f"{type(exc).__name__}:{exc}")
    return {"schema_version": OFFLINE_SCHEMA, "source_revision": revision,
            "stage_config_sha256": CONFIG_SHA256, "passed": not failures,
            "failures": failures, "stream_checks": checks,
            "reset_calls": 0, "plant_advance_gotsc_calls": 0,
            "models_fit_or_updated": 0}


def execute(stage: dict[str, Any], base: dict[str, Any], cfg: Any,
            preflight: dict[str, Any], tracked: dict[str, Any], revision: str,
            output: Path, storage: dict[str, Any], runner_cls: type | None = None) -> dict[str, Any]:
    isolation = z30.z27.z7.configure_run_root(cfg, output)
    streams = build_streams(stage, cfg, preflight, tracked)
    rows: list[dict[str, Any]] = []; prefixes: list[dict[str, Any]] = []
    centered: dict[str, Any] | None = None; execution = True
    for stream in streams:
        reference_source = tracked if stream["kind"] == "center_baseline" else centered
        reference = (z30.z27.z6._reference(tracked, 33)
                     if stream["kind"] == "center_baseline" else
                     z30.z27.z6._reference(centered or {},
                                           int(stream["prefix_checkpoint_last_state"]) + 1))
        row = z30.z27.z6.one_rollout(
            cfg, z30._runtime(stage, base, stream), stream, reference,
            runner_cls=runner_cls)
        row.update({"schema_version": ROW_SCHEMA, "source_revision": revision,
                    "family_id": stream["family_id"], "kind": stream["kind"],
                    "phase_issue": stream["phase_issue"],
                    "axis_id": stream["axis_id"],
                    "initial_sign": stream["initial_sign"],
                    "fit_weight": 0, "data_role": stream["data_role"]})
        z30.z27.io.write_new(output / f"{stream['rollout_id']}.json", row)
        rows.append(row)
        count = 33 if stream["kind"] == "center_baseline" else int(
            stream["prefix_checkpoint_last_state"]) + 1
        prefixes.append(z30.z27.z6.prefix_check(
            row, reference_source or {}, count, count - 1, stage["semantic_artifacts"]))
        if stream["kind"] == "center_baseline" and row.get("passed") and len(row.get("states", [])) == 74:
            centered = row
        if not row.get("passed"):
            execution = False; break
    replay = (z30.z27.z6.replay_check(rows[2], rows[3], stage["semantic_artifacts"])
              if len(rows) >= 4 else {"passed": False, "failures": ["NOT_RUN"]})
    mapping = event_map(rows, stage)
    counters = {key: sum(int(row.get(key, 0)) for row in rows) for key in
                ("reset_calls", "advance_attempts", "plant_advance_gotsc_calls",
                 "verified_plant_advances")}
    inventory = z30.z27.io.raw_inventory(output, rows, stage)
    raw_ok = (not inventory["missing_required_artifacts"]
              and inventory["required_artifact_files"] == 5 * sum(
                  len(row.get("states", [])) for row in rows))
    prefix_ok = len(prefixes) == len(rows) and all(row["passed"] for row in prefixes)
    if not execution:
        route = stage["routes"]["execution_or_interface_fail"]
    elif not raw_ok:
        route = stage["routes"]["raw_integrity_fail"]
    elif not prefix_ok:
        route = stage["routes"]["prefix_mismatch"]
    elif not replay["passed"]:
        route = stage["routes"]["replay_fail"]
    elif not mapping["passed"]:
        route = stage["routes"]["event_map_fail"]
    else:
        route = stage["routes"]["pass"]
    result = {"schema_version": SCHEMA, "source_revision": revision,
              "stage_config_sha256": CONFIG_SHA256,
              "passed": route == stage["routes"]["pass"], "route": route,
              "storage_gate": storage, "run_root_isolation": isolation,
              "execution_integrity_passed": execution,
              "raw_integrity_passed": raw_ok, "prefix_checks": prefixes,
              "replay_metrics": replay, "event_map": mapping,
              "rollouts_started": len(rows), "complete_rollouts": sum(
                  bool(row.get("passed") and len(row.get("states", [])) == 74)
                  for row in rows), **counters, **inventory,
              "models_fit_or_updated": 0, "future_feedback_records_read": 0,
              "claim_boundary": stage["claim_boundary"]}
    z30.z27.io.write_new(output / "result.json", result)
    return result


def run(config: Path, revision: str, output: Path) -> dict[str, Any]:
    output = _inside(output, "output")
    if output.exists():
        raise FileExistsError(str(output))
    stage, base, cfg, preflight, tracked = load(config)
    output.parent.mkdir(parents=True, exist_ok=True)
    storage = z30.z27.io.storage(stage, output); output.mkdir()
    pre = offline(config, revision); z30.z27.io.write_new(output / "offline_preflight.json", pre)
    if not storage["passed"] or not pre["passed"]:
        route = stage["routes"]["storage_fail" if not storage["passed"] else "offline_or_input_fail"]
        result = {"schema_version": SCHEMA, "source_revision": revision,
                  "stage_config_sha256": CONFIG_SHA256, "passed": False,
                  "route": route, "storage_gate": storage,
                  "reasons": pre["failures"], "rollouts_started": 0,
                  "reset_calls": 0, "advance_attempts": 0,
                  "plant_advance_gotsc_calls": 0,
                  "verified_plant_advances": 0, "models_fit_or_updated": 0}
        z30.z27.io.write_new(output / "result.json", result); return result
    try:
        return execute(stage, base, cfg, preflight, tracked, revision, output, storage)
    except Exception as exc:
        rows: list[dict[str, Any]] = []
        for path in sorted(output.glob("*.json")):
            if path.name in ("offline_preflight.json", "result.json", "independent_raw_audit.json"):
                continue
            try:
                value = _read(path)
                if "rollout_id" in value:
                    rows.append(value)
            except Exception:
                pass
        counters = {key: sum(int(row.get(key, 0)) for row in rows) for key in
                    ("reset_calls", "advance_attempts", "plant_advance_gotsc_calls",
                     "verified_plant_advances")}
        try:
            inventory = z30.z27.io.raw_inventory(output, rows, stage)
        except Exception as inventory_exc:
            inventory = {"required_artifact_files": 0, "required_artifact_bytes": 0,
                         "required_artifact_inventory_sha256": None,
                         "missing_required_artifacts": [
                             f"FINALIZER:{type(inventory_exc).__name__}:{inventory_exc}"]}
        result = {"schema_version": SCHEMA, "source_revision": revision,
                  "stage_config_sha256": CONFIG_SHA256, "passed": False,
                  "route": stage["routes"]["execution_or_interface_fail"],
                  "failure": f"{type(exc).__name__}:{exc}",
                  "storage_gate": storage, "rollouts_started": len(rows),
                  "complete_rollouts": sum(bool(row.get("passed") and len(
                      row.get("states", [])) == 74) for row in rows),
                  **counters, **inventory, "models_fit_or_updated": 0,
                  "claim_boundary": "Best-effort execution failure; no scientific event verdict."}
        if not (output / "result.json").exists():
            z30.z27.io.write_new(output / "result.json", result)
        return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)
    value = offline(args.config, args.source_revision) if args.offline else run(
        args.config, args.source_revision, args.output)
    if args.offline:
        z30.z27.io.write_new(args.output, value)
    print(json.dumps(value, sort_keys=True, allow_nan=False))
    return 0 if value["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
