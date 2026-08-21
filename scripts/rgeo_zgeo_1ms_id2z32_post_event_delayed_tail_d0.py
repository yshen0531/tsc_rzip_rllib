#!/usr/bin/env python3
"""Run the frozen ID-2Z32 post-event delayed-tail D0 campaign."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_id2z31_event_phase_discriminator as z31  # noqa: E402


CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z32_post_event_delayed_tail_d0.json"
CONFIG_SHA256 = "699e6ed1a28ba0b8926b6789d287a352782aa1d64bdcc4eb4fe625e1500bbd1b"
SCHEMA = "rgeo-zgeo-1ms-id2z32-post-event-delayed-tail-d0-result-v1"
ROW_SCHEMA = "rgeo-zgeo-1ms-id2z32-post-event-delayed-tail-d0-row-v1"
OFFLINE_SCHEMA = "rgeo-zgeo-1ms-id2z32-post-event-delayed-tail-d0-offline-v1"


def _inside(path: Path, label: str) -> Path:
    value = path.resolve()
    try:
        value.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(f"ID2Z32 {label} leaves repository") from exc
    return value


def _sha(path: Path) -> str:
    return hashlib.sha256(_inside(path, "hash path").read_bytes()).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(_inside(path, "JSON path").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("ID2Z32 JSON object required")
    return value


def _require(stage: dict[str, Any]) -> None:
    if _sha(CONFIG) != CONFIG_SHA256 or stage != _read(CONFIG):
        raise ValueError("ID2Z32 frozen config changed")
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2z32-post-event-delayed-tail-d0-v1",
        "identity": "rgeo-zgeo-1ms-id2z32-post-event-delayed-tail-d0-v1",
        "stage": "ID-2Z32", "takeover_time_ms": 1100,
        "control_period_ms": 1, "common_horizon_steps": 73,
        "phase_issue_steps": [50, 56],
        "output_aligned_axis_ids": ["q_r", "q_z"],
        "initial_signs": ["plus", "minus"],
        "maximum_rollouts": 10, "maximum_reset_calls": 10,
        "maximum_advance_attempts": 730, "maximum_gotsc_calls": 730,
        "maximum_verified_plant_advances": 730,
        "maximum_retained_states": 740,
        "required_artifact_files_if_all_complete": 3700,
        "retry_after_any_advance_attempt": "forbidden",
        "models_fit_or_updated": 0,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise ValueError(f"ID2Z32 frozen field changed: {key}")
    ids = [row.get("family_id") for row in stage.get("rollout_specs", [])]
    expected_ids = ["baseline_transition_center",
                    *[f"issue{phase}__{axis}__{sign}_then_return"
                      for phase in (50, 56) for axis in ("q_r", "q_z")
                      for sign in ("plus", "minus")],
                    "replay_issue50__q_z__plus_then_return"]
    if ids != expected_ids or sum(int(row.get("fit_weight", 0)) for row in
                                  stage["rollout_specs"]) != 8:
        raise ValueError("ID2Z32 rollout/data matrix changed")


def load(config: Path = CONFIG) -> tuple[dict[str, Any], dict[str, Any], Any,
                                          dict[str, Any], dict[str, Any]]:
    if config.resolve() != CONFIG.resolve():
        raise ValueError("ID2Z32 alternate config forbidden")
    stage = _read(config); _require(stage)
    evidence: dict[str, dict[str, Any]] = {}
    for name, spec in stage["evidence"].items():
        path = ROOT / spec["path"]
        if _sha(path) != spec["sha256"]:
            raise ValueError(f"ID2Z32 evidence hash mismatch: {name}")
        if path.suffix == ".json":
            evidence[name] = _read(path)
    if (evidence["id2z26r1_preflight"].get("passed") is not True
            or evidence["id2z26r1_independent"].get("audit_passed") is not True
            or evidence["id2z31_result"].get("route")
            != stage["evidence"]["id2z31_result"]["required_route"]
            or evidence["id2z31_independent"].get("audit_passed") is not True):
        raise ValueError("ID2Z32 prerequisite identity mismatch")
    _, base, cfg, preflight, tracked, _ = z31.z30.load(z31.z30.CONFIG)
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
                        "source_family_id": spec["source_family_id"],
                        "fit_weight": 0, "data_role": "zero_fit_replay",
                        "cell_id": family})
        else:
            phase = spec.get("phase_issue")
            fields = ([tuple(value) for value in center["card15_targets"]]
                      if phase is None else z31.z30._branch_fields(
                          preflight, int(phase), spec["axis_id"], spec["initial_sign"]))
            targets = z31.z30.z27._targets(fields, cfg, family)
            actions = z31.z30.z27._actions(targets, cfg, family, tracked)
            checkpoint = 32 if phase is None else int(phase)
            weight = int(spec["fit_weight"])
            row = {"rollout_id": family, "candidate_id": family,
                   "family_id": family, "kind": spec["kind"],
                   "data_role": "development" if weight else "zero_fit_baseline",
                   "phase_issue": phase, "axis_id": spec.get("axis_id"),
                   "initial_sign": spec.get("initial_sign"), "fit_weight": weight,
                   "round_index": 0, "round_id": "post_event_delayed_tail_d0",
                   "cell_id": family, "cell_kind": "post_event_delayed_tail",
                   "context_id": f"canonical_dynamic_state{checkpoint}",
                   "coordinate": "qrz_sustained8_return8_whole_suffix",
                   "probe_issue_step": phase,
                   "probe_duration_issues": 0 if phase is None else 8,
                   "prefix_checkpoint_last_state": checkpoint,
                   "non_nominal_issue_steps": [] if phase is None else list(
                       range(int(phase), int(phase) + 16)),
                   "targets": targets, "actions": actions}
        rows.append(row); by_id[family] = row
    return rows


def _response(row: dict[str, Any], baseline: dict[str, Any], state: int) -> np.ndarray:
    return np.asarray([float(row["states"][state]["r_geo_m"])
                       - float(baseline["states"][state]["r_geo_m"]),
                       float(row["states"][state]["z_geo_m"])
                       - float(baseline["states"][state]["z_geo_m"])])


def scientific_metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    by_id = {str(row.get("family_id")): row for row in rows}
    baseline = by_id.get("baseline_transition_center")
    baseline_ok = bool(baseline and baseline.get("passed") and len(baseline.get("states", [])) == 74)
    gates = stage["measurement_gates"]
    branches = []; geometry = []; all_signal = baseline_ok
    if baseline_ok:
        for phase in stage["phase_issue_steps"]:
            vectors = {4: [], 8: []}
            for axis in stage["output_aligned_axis_ids"]:
                for sign in stage["initial_signs"]:
                    family = f"issue{phase}__{axis}__{sign}_then_return"
                    row = by_id.get(family)
                    complete = bool(row and row.get("passed") and len(row.get("states", [])) == 74)
                    if not complete:
                        branches.append({"family_id": family, "complete": False, "passed": False})
                        all_signal = False; continue
                    value = {h: _response(row, baseline, int(phase) + h) for h in (4, 8)}
                    norms = {h: float(np.linalg.norm(value[h])) for h in (4, 8)}
                    cosine = (float(np.dot(value[4], value[8]) / (norms[4] * norms[8]))
                              if norms[4] and norms[8] else -1.0)
                    max_ip = max(abs(float(row["states"][i]["ip_a"])
                                     - float(baseline["states"][i]["ip_a"]))
                                 for i in range(int(phase) + 1, 74))
                    passed = bool(norms[4] >= gates["minimum_each_h4_rz_response_m"]
                                  and norms[8] >= gates["minimum_each_h8_rz_response_m"]
                                  and cosine >= gates["minimum_each_h4_h8_cosine"]
                                  and max_ip <= gates["maximum_absolute_paired_ip_response_a"])
                    events = []
                    delayed = stage["delayed_tail_contract"]
                    for state_index in range(delayed["event_scan_first_state"],
                                             delayed["event_scan_last_state"] + 1):
                        delta = float(row["states"][state_index]["r_geo_m"]) - float(
                            row["states"][state_index - 1]["r_geo_m"])
                        if delta > delayed["positive_r_event_threshold_m"]:
                            events.append({"effect_state_index": state_index,
                                           "delta_r_m": delta})
                    branches.append({"family_id": family, "complete": True,
                                     "h4_response_m": value[4].tolist(),
                                     "h8_response_m": value[8].tolist(),
                                     "h4_norm_m": norms[4], "h8_norm_m": norms[8],
                                     "h4_h8_cosine": cosine,
                                     "maximum_absolute_paired_ip_response_a": max_ip,
                                     "delayed_positive_r_events": events, "passed": passed})
                    vectors[4].append(value[4]); vectors[8].append(value[8])
                    all_signal = all_signal and passed
            for horizon in (4, 8):
                value = z31.z30.z27.z23._geometry(vectors[horizon], gates["direction_grid_count"])
                value.update({"phase_issue": phase, "horizon": horizon,
                              "passed": bool(value["maximum_angular_gap_deg"]
                                             <= gates["maximum_each_phase_horizon_angular_gap_deg"]
                                             and value["weakest_best_projection_m"]
                                             >= gates["minimum_each_phase_horizon_weakest_best_projection_m"])})
                geometry.append(value); all_signal = all_signal and value["passed"]
    replay = z31.z30.z27.z6.replay_check(
        by_id.get(stage["replay_source_family_id"]),
        by_id.get(stage["replay_family_id"]), stage["semantic_artifacts"])
    return {"baseline_complete": baseline_ok, "branch_metrics": branches,
            "positive_span_metrics": geometry, "replay_metrics": replay,
            "passed": bool(all_signal and len(branches) == 8 and replay["passed"])}


def offline(config: Path, revision: str) -> dict[str, Any]:
    failures = []
    try:
        stage, _, cfg, preflight, tracked = load(config)
        streams = build_streams(stage, cfg, preflight, tracked)
        checks = [z31.z30.validate_stream(row, cfg) for row in streams]
        if len(streams) != 10 or not all(row["passed"] for row in checks):
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
    isolation = z31.z30.z27.z7.configure_run_root(cfg, output)
    streams = build_streams(stage, cfg, preflight, tracked)
    rows = []; prefixes = []; centered = None; execution = True
    for stream in streams:
        reference_source = tracked if stream["kind"] == "center_baseline" else centered
        reference = (z31.z30.z27.z6._reference(tracked, 33)
                     if stream["kind"] == "center_baseline" else
                     z31.z30.z27.z6._reference(centered or {},
                                               int(stream["prefix_checkpoint_last_state"]) + 1))
        row = z31.z30.z27.z6.one_rollout(
            cfg, z31.z30._runtime(stage, base, stream), stream, reference,
            runner_cls=runner_cls)
        row.update({"schema_version": ROW_SCHEMA, "source_revision": revision,
                    "family_id": stream["family_id"], "kind": stream["kind"],
                    "phase_issue": stream["phase_issue"], "axis_id": stream["axis_id"],
                    "initial_sign": stream["initial_sign"],
                    "fit_weight": stream["fit_weight"], "data_role": stream["data_role"]})
        z31.z30.z27.io.write_new(output / f"{stream['rollout_id']}.json", row)
        rows.append(row)
        count = 33 if stream["kind"] == "center_baseline" else int(
            stream["prefix_checkpoint_last_state"]) + 1
        prefixes.append(z31.z30.z27.z6.prefix_check(
            row, reference_source or {}, count, count - 1, stage["semantic_artifacts"]))
        if stream["kind"] == "center_baseline" and row.get("passed") and len(row.get("states", [])) == 74:
            centered = row
        if not row.get("passed"):
            execution = False; break
    counters = {key: sum(int(row.get(key, 0)) for row in rows) for key in
                ("reset_calls", "advance_attempts", "plant_advance_gotsc_calls",
                 "verified_plant_advances")}
    inventory = z31.z30.z27.io.raw_inventory(output, rows, stage)
    raw_ok = (not inventory["missing_required_artifacts"]
              and inventory["required_artifact_files"] == 5 * sum(
                  len(row.get("states", [])) for row in rows))
    prefix_ok = len(prefixes) == len(rows) and all(row["passed"] for row in prefixes)
    scientific = scientific_metrics(rows, stage)
    if not execution:
        route = stage["routes"]["execution_or_interface_fail"]
    elif not raw_ok:
        route = stage["routes"]["raw_integrity_fail"]
    elif not prefix_ok:
        route = stage["routes"]["prefix_mismatch"]
    elif not scientific["replay_metrics"]["passed"]:
        route = stage["routes"]["replay_fail"]
    elif len(rows) != 10 or not scientific["passed"]:
        route = stage["routes"]["signal_fail"]
    else:
        route = stage["routes"]["data_pass"]
    result = {"schema_version": SCHEMA, "source_revision": revision,
              "stage_config_sha256": CONFIG_SHA256,
              "passed": route == stage["routes"]["data_pass"], "route": route,
              "storage_gate": storage, "run_root_isolation": isolation,
              "execution_integrity_passed": execution, "raw_integrity_passed": raw_ok,
              "prefix_checks": prefixes, "scientific_metrics": scientific,
              "rollouts_started": len(rows), "complete_rollouts": sum(
                  bool(row.get("passed") and len(row.get("states", [])) == 74) for row in rows),
              **counters, **inventory, "models_fit_or_updated": 0,
              "fresh_calibration_or_holdout_records_read": 0,
              "claim_boundary": stage["claim_boundary"]}
    z31.z30.z27.io.write_new(output / "result.json", result)
    return result


def run(config: Path, revision: str, output: Path) -> dict[str, Any]:
    output = _inside(output, "output")
    if output.exists():
        raise FileExistsError(str(output))
    stage, base, cfg, preflight, tracked = load(config)
    output.parent.mkdir(parents=True, exist_ok=True)
    storage = z31.z30.z27.io.storage(stage, output); output.mkdir()
    pre = offline(config, revision); z31.z30.z27.io.write_new(output / "offline_preflight.json", pre)
    if not storage["passed"] or not pre["passed"]:
        route = stage["routes"]["storage_fail" if not storage["passed"] else "offline_or_input_fail"]
        result = {"schema_version": SCHEMA, "source_revision": revision,
                  "stage_config_sha256": CONFIG_SHA256, "passed": False,
                  "route": route, "storage_gate": storage, "reasons": pre["failures"],
                  "rollouts_started": 0, "reset_calls": 0, "advance_attempts": 0,
                  "plant_advance_gotsc_calls": 0, "verified_plant_advances": 0,
                  "models_fit_or_updated": 0}
        z31.z30.z27.io.write_new(output / "result.json", result); return result
    try:
        return execute(stage, base, cfg, preflight, tracked, revision, output, storage)
    except Exception as exc:
        rows = []
        for path in sorted(output.glob("*.json")):
            if path.name in ("offline_preflight.json", "result.json", "independent_raw_audit.json"):
                continue
            try:
                value = _read(path)
                if "rollout_id" in value: rows.append(value)
            except Exception: pass
        counters = {key: sum(int(row.get(key, 0)) for row in rows) for key in
                    ("reset_calls", "advance_attempts", "plant_advance_gotsc_calls",
                     "verified_plant_advances")}
        try: inventory = z31.z30.z27.io.raw_inventory(output, rows, stage)
        except Exception as inv:
            inventory = {"required_artifact_files": 0, "required_artifact_bytes": 0,
                         "required_artifact_inventory_sha256": None,
                         "missing_required_artifacts": [f"FINALIZER:{type(inv).__name__}:{inv}"]}
        result = {"schema_version": SCHEMA, "source_revision": revision,
                  "stage_config_sha256": CONFIG_SHA256, "passed": False,
                  "route": stage["routes"]["execution_or_interface_fail"],
                  "failure": f"{type(exc).__name__}:{exc}", "storage_gate": storage,
                  "rollouts_started": len(rows), **counters, **inventory,
                  "models_fit_or_updated": 0,
                  "claim_boundary": "Best-effort execution failure; no scientific D0 verdict."}
        if not (output / "result.json").exists():
            z31.z30.z27.io.write_new(output / "result.json", result)
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
    if args.offline: z31.z30.z27.io.write_new(args.output, value)
    print(json.dumps(value, sort_keys=True, allow_nan=False))
    return 0 if value["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
