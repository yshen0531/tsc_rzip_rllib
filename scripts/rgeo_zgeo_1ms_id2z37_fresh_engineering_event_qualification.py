#!/usr/bin/env python3
"""Run the staged fresh ID2Z37 engineering-event qualification."""

from __future__ import annotations

import argparse
import copy
from decimal import Decimal
import json
from pathlib import Path
import sys
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_id2z33_corrected_moving_center_d0 as z33  # noqa: E402


CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z37_fresh_engineering_event_qualification.json"
CONFIG_SHA256 = "76d3f141ee69657dc14d458cc7305a9261ed02284648dabb4d8ca16ca7c7a5a8"
SCHEMA = "rgeo-zgeo-1ms-id2z37-fresh-engineering-event-qualification-result-v1"
ROW_SCHEMA = "rgeo-zgeo-1ms-id2z37-fresh-engineering-event-qualification-row-v1"
OFFLINE_SCHEMA = "rgeo-zgeo-1ms-id2z37-fresh-engineering-event-qualification-offline-v1"
KEYS = ("r_geo_m", "z_geo_m", "ip_a")
io = z33.z32.z31.z30.z27.io


def _read(path: Path) -> dict[str, Any]:
    return z33.z32._read(path)


def _inside(path: Path, label: str) -> Path:
    return z33.z32._inside(path, label)


def _sha(path: Path) -> str:
    return z33.z32._sha(path)


def _require(stage: dict[str, Any]) -> None:
    if _sha(CONFIG) != CONFIG_SHA256 or stage != _read(CONFIG):
        raise ValueError("ID2Z37 frozen config changed")
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2z37-fresh-engineering-event-qualification-v1",
        "identity": "rgeo-zgeo-1ms-id2z37-fresh-engineering-event-qualification-v1",
        "stage": "ID-2Z37", "common_horizon_steps": 71,
        "calibration_phase_issue": 48, "blind_phase_issue": 54,
        "maximum_rollouts": 10, "maximum_reset_calls": 10,
        "maximum_advance_attempts": 710, "maximum_gotsc_calls": 710,
        "maximum_verified_plant_advances": 710,
        "required_artifact_files_if_all_complete": 3600,
        "models_fit_or_updated": 0,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise ValueError(f"ID2Z37 frozen field changed: {key}")
    roles = stage["data_contract"]
    qualification = stage["qualification"]
    if (roles.get("calibration_family_count") != 4
            or roles.get("blind_family_count") != 4
            or roles.get("id2z35_rows_fit_weight") != 0
            or roles.get("qualification_rows_may_refit_model") is not False
            or qualification.get("model_refit_after_calibration") is not False
            or qualification.get("blind_open_only_after_calibration_pass") is not True):
        raise ValueError("ID2Z37 data/qualification contract changed")


def load(config: Path = CONFIG):
    if config.resolve() != CONFIG.resolve():
        raise ValueError("ID2Z37 alternate config forbidden")
    stage = _read(config)
    _require(stage)
    for name, spec in stage["evidence"].items():
        path = ROOT / spec["path"]
        if _sha(path) != spec["sha256"]:
            raise ValueError(f"ID2Z37 evidence hash mismatch: {name}")
    model_result = _read(ROOT / stage["evidence"]["id2z36_result"]["path"])
    model_audit = _read(ROOT / stage["evidence"]["id2z36_independent"]["path"])
    if (model_result.get("passed") is not True
            or model_result.get("route") != stage["evidence"]["id2z36_result"]["required_route"]
            or model_result.get("model_payload", {}).get("payload_sha256")
            != stage["evidence"]["id2z36_result"]["required_payload_sha256"]
            or model_audit.get("audit_passed") is not True
            or model_audit.get("primary_sha256") != stage["evidence"]["id2z36_result"]["sha256"]
            or model_audit.get("recomputed_payload_sha256")
            != stage["evidence"]["id2z36_result"]["required_payload_sha256"]):
        raise ValueError("ID2Z36 frozen model identity mismatch")
    event = model_result.get("model_payload", {}).get("event_sets", [{}])[0]
    if event.get("half_width") != [0.000375, 0.000075, 30.0]:
        raise ValueError("ID2Z36 frozen engineering event width mismatch")
    _, base, cfg, preflight, tracked = z33.load(z33.CONFIG)
    return stage, base, cfg, preflight, tracked, model_result["model_payload"]


def build_streams(stage: dict[str, Any], cfg: Any, preflight: dict[str, Any],
                  tracked: dict[str, Any]) -> list[dict[str, Any]]:
    center = next(row for row in preflight["prospective_static_streams"]
                  if row["rollout_id"] == "baseline_transition_center")
    center_fields = [tuple(value) for value in center["card15_targets"]][
        :int(stage["common_horizon_steps"])]
    axes = {name: tuple(Decimal(value) for value in values) for name, values in
            preflight["output_aligned_field_increments"].items()}
    rows: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    for spec in stage["rollout_specs"]:
        family = spec["family_id"]
        if spec["kind"] == "replay":
            row = copy.deepcopy(by_id[spec["source_family_id"]])
            row.update({"rollout_id": family, "candidate_id": family,
                        "family_id": family, "kind": "replay",
                        "phase_role": spec["phase_role"],
                        "source_family_id": spec["source_family_id"],
                        "fit_weight": 0, "data_role": "zero_fit_calibration_replay",
                        "cell_id": family})
        else:
            phase = spec.get("phase_issue")
            fields = center_fields if phase is None else z33._corrected_branch(
                center_fields, axes[spec["axis_id"]], int(phase),
                1 if spec["initial_sign"] == "plus" else -1)
            targets = z33.z32.z31.z30.z27._targets(fields, cfg, family)
            actions = z33.z32.z31.z30.z27._actions(targets, cfg, family, tracked)
            checkpoint = 32 if phase is None else int(phase)
            row = {
                "rollout_id": family, "candidate_id": family, "family_id": family,
                "kind": spec["kind"], "phase_role": spec["phase_role"],
                "data_role": "fresh_qualification" if phase is not None else "zero_fit_baseline",
                "phase_issue": phase, "axis_id": spec.get("axis_id"),
                "initial_sign": spec.get("initial_sign"), "fit_weight": 0,
                "round_index": 0, "round_id": "fresh_engineering_event_qualification",
                "cell_id": family, "cell_kind": "frozen_event_set_qualification",
                "context_id": f"canonical_dynamic_state{checkpoint}",
                "coordinate": "general_center_delta_plus_signed_q_return",
                "probe_issue_step": phase,
                "probe_duration_issues": 0 if phase is None else 8,
                "prefix_checkpoint_last_state": checkpoint,
                "non_nominal_issue_steps": [] if phase is None else list(
                    range(int(phase), int(phase) + 16)),
                "targets": targets, "actions": actions,
            }
        rows.append(row)
        by_id[family] = row
    return rows


def action_separation(streams: Sequence[dict[str, Any]]) -> dict[str, Any]:
    by_id = {row["rollout_id"]: row for row in streams}
    baseline = by_id["baseline_transition_center"]
    failures: list[str] = []
    rows: list[dict[str, Any]] = []
    branches = [row for row in streams if row["kind"] == "output_aligned_branch"]
    for stream in branches:
        phase = int(stream["phase_issue"])
        differing = [i for i, (left, right) in enumerate(zip(stream["actions"], baseline["actions"]))
                     if left["expected_card15_fields"] != right["expected_card15_fields"]]
        outside = [i for i in differing if not phase <= i < phase + 16]
        first_nonzero = stream["actions"][phase]["maximum_issued_delta_a"] > 0
        terminal_equal = (stream["actions"][phase + 15]["expected_card15_fields"]
                          == baseline["actions"][phase + 15]["expected_card15_fields"])
        passed = bool(differing and not outside and first_nonzero and terminal_equal)
        if not passed:
            failures.append(stream["family_id"])
        rows.append({"family_id": stream["family_id"], "differing_issue_indices": differing,
                     "outside_window": outside, "first_branch_issue_nonzero": first_nonzero,
                     "terminal_target_equals_center": terminal_equal, "passed": passed})
    for role, phase in (("calibration", 48), ("blind", 54)):
        for axis in ("q_r", "q_z"):
            plus = by_id[f"{'cal48' if role == 'calibration' else 'blind54'}__{axis}__plus_then_return"]
            minus = by_id[f"{'cal48' if role == 'calibration' else 'blind54'}__{axis}__minus_then_return"]
            if all(a["expected_card15_fields"] == b["expected_card15_fields"]
                   for a, b in zip(plus["actions"], minus["actions"])):
                failures.append(f"PLUS_MINUS_IDENTICAL:{phase}:{axis}")
    return {"passed": not failures and len(rows) == 8, "failures": failures, "rows": rows}


def offline(config: Path, revision: str) -> dict[str, Any]:
    failures: list[str] = []
    try:
        stage, _, cfg, preflight, tracked, _ = load(config)
        streams = build_streams(stage, cfg, preflight, tracked)
        checks = [z33.z32.z31.z30.validate_stream(row, cfg) for row in streams]
        separation = action_separation(streams)
        if len(streams) != 10 or not all(row["passed"] for row in checks):
            failures.append("STATIC_STREAMS")
        if not separation["passed"]:
            failures.append("ACTION_STREAM_SEPARATION")
    except Exception as exc:
        checks = []
        separation = {"passed": False, "failures": [str(exc)], "rows": []}
        failures.append(f"{type(exc).__name__}:{exc}")
    return {"schema_version": OFFLINE_SCHEMA, "source_revision": revision,
            "stage_config_sha256": CONFIG_SHA256, "passed": not failures,
            "failures": failures, "stream_checks": checks,
            "action_stream_separation": separation, "reset_calls": 0,
            "plant_advance_gotsc_calls": 0, "models_fit_or_updated": 0}


def _response(row: dict[str, Any], baseline: dict[str, Any], phase: int) -> np.ndarray:
    return np.asarray([[float(row["states"][phase + age][key])
                        - float(baseline["states"][phase + age][key]) for key in KEYS]
                       for age in range(1, 18)], dtype=float)


def qualification_metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any],
                          model: dict[str, Any], role: str,
                          calibrated_half_width: dict[str, float] | None = None) -> dict[str, Any]:
    phase = int(stage[f"{role}_phase_issue"])
    prefix = "cal48" if role == "calibration" else "blind54"
    by_id = {row["family_id"]: row for row in rows}
    baseline = by_id.get("baseline_transition_center")
    complete = bool(baseline and baseline.get("passed") and len(baseline.get("states", [])) == 72)
    q = stage["qualification"]
    event_key = (q["event_axis_sign"], int(q["event_effect_age"]))
    event = next(row for row in model["event_sets"]
                 if (row["axis_sign"], int(row["effect_age"])) == event_key)
    event_center = np.asarray(event["center"], dtype=float)
    event_half = np.asarray(event["half_width"], dtype=float)
    maximum = np.zeros(3, dtype=float)
    event_total = 0
    event_contained = 0
    all_total = 0
    all_contained = 0
    branch_rows: list[dict[str, Any]] = []
    for axis in stage["output_aligned_axis_ids"]:
        for sign in stage["initial_signs"]:
            family = f"{prefix}__{axis}__{sign}_then_return"
            row = by_id.get(family)
            row_complete = bool(row and row.get("passed") and len(row.get("states", [])) == 72)
            complete = complete and row_complete
            if not row_complete:
                branch_rows.append({"family_id": family, "complete": False})
                continue
            truth = _response(row, baseline, phase)
            key = f"{axis}:{sign}"
            center = np.asarray(model["point_centers"][key], dtype=float)
            local_event = 0
            local_non_event_max = np.zeros(3, dtype=float)
            for offset, observed in enumerate(truth, start=1):
                all_total += 1
                if (key, offset) == event_key:
                    event_total += 1
                    inside = bool(np.all(np.abs(observed - event_center) <= event_half + 1e-15))
                    event_contained += int(inside)
                    all_contained += int(inside)
                    local_event += int(inside)
                else:
                    error = np.abs(observed - center[offset - 1])
                    maximum = np.maximum(maximum, error)
                    local_non_event_max = np.maximum(local_non_event_max, error)
                    if calibrated_half_width is not None:
                        half = np.asarray([calibrated_half_width[name] for name in KEYS])
                        all_contained += int(bool(np.all(error <= half + 1e-15)))
            branch_rows.append({"family_id": family, "complete": True,
                                "event_cells_contained": local_event,
                                "maximum_non_event_absolute_error":
                                    dict(zip(KEYS, local_non_event_max.tolist()))})
    event_fraction = event_contained / event_total if event_total else 0.0
    result: dict[str, Any] = {
        "role": role, "phase_issue": phase, "complete": complete,
        "branch_metrics": branch_rows,
        "maximum_non_event_absolute_error": dict(zip(KEYS, maximum.tolist())),
        "event_cell_observations": event_total,
        "event_containment_fraction": event_fraction,
    }
    if role == "calibration":
        cap = q["calibration_maximum_non_event_error"]
        development = model["candidate_b"]["metrics"]["maximum_non_event_absolute_error"]
        floor = q["calibrated_half_width_floor"]
        multiplier = float(q["calibrated_non_event_multiplier"])
        half = {name: multiplier * max(float(development[name]), float(maximum[index]))
                + float(floor[name]) for index, name in enumerate(KEYS)}
        width_cap = q["calibrated_half_width_cap"]
        passed = bool(complete
                      and event_fraction >= q["required_event_containment_fraction"]
                      and all(maximum[index] <= float(cap[name]) for index, name in enumerate(KEYS))
                      and all(half[name] <= float(width_cap[name]) for name in KEYS))
        result.update({"calibrated_non_event_half_width": half, "passed": passed})
    else:
        containment = all_contained / all_total if all_total else 0.0
        result.update({"all_cell_observations": all_total,
                       "all_cell_containment_fraction": containment,
                       "calibrated_non_event_half_width": calibrated_half_width,
                       "passed": bool(complete and containment
                                      >= q["required_blind_all_cell_containment_fraction"]
                                      and event_fraction >= q["required_event_containment_fraction"])})
    return result


def _run_one(stage: dict[str, Any], base: dict[str, Any], cfg: Any,
             tracked: dict[str, Any], stream: dict[str, Any], centered: dict[str, Any] | None,
             revision: str, output: Path, runner_cls: type | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    source = tracked if stream["kind"] == "center_baseline" else (centered or {})
    count = 33 if stream["kind"] == "center_baseline" else int(
        stream["prefix_checkpoint_last_state"]) + 1
    reference = z33.z32.z31.z30.z27.z6._reference(source, count)
    row = z33.z32.z31.z30.z27.z6.one_rollout(
        cfg, z33.z32.z31.z30._runtime(stage, base, stream), stream, reference,
        runner_cls=runner_cls)
    row.update({"schema_version": ROW_SCHEMA, "source_revision": revision,
                "family_id": stream["family_id"], "kind": stream["kind"],
                "phase_role": stream["phase_role"], "phase_issue": stream["phase_issue"],
                "axis_id": stream["axis_id"], "initial_sign": stream["initial_sign"],
                "fit_weight": 0, "data_role": stream["data_role"]})
    io.write_new(output / f"{stream['rollout_id']}.json", row)
    prefix = z33.z32.z31.z30.z27.z6.prefix_check(
        row, source, count, count - 1, stage["semantic_artifacts"])
    return row, prefix


def execute(stage: dict[str, Any], base: dict[str, Any], cfg: Any,
            preflight: dict[str, Any], tracked: dict[str, Any], model: dict[str, Any],
            revision: str, output: Path, storage: dict[str, Any],
            runner_cls: type | None = None) -> dict[str, Any]:
    isolation = z33.z32.z31.z30.z27.z7.configure_run_root(cfg, output)
    streams = build_streams(stage, cfg, preflight, tracked)
    rows: list[dict[str, Any]] = []
    prefixes: list[dict[str, Any]] = []
    centered: dict[str, Any] | None = None
    execution = True
    for stream in streams[:6]:
        row, prefix = _run_one(stage, base, cfg, tracked, stream, centered, revision,
                               output, runner_cls)
        rows.append(row); prefixes.append(prefix)
        if stream["kind"] == "center_baseline" and row.get("passed") and len(row.get("states", [])) == 72:
            centered = row
        if not row.get("passed"):
            execution = False
            break
    calibration = qualification_metrics(rows, stage, model, "calibration")
    by_id = {row["family_id"]: row for row in rows}
    replay = z33.z32.z31.z30.z27.z6.replay_check(
        by_id.get(stage["replay_source_family_id"]), by_id.get(stage["replay_family_id"]),
        stage["semantic_artifacts"])
    provisional_inventory = io.raw_inventory(output, rows, stage)
    provisional_raw = (not provisional_inventory["missing_required_artifacts"]
                       and provisional_inventory["required_artifact_files"]
                       == 5 * sum(len(row.get("states", [])) for row in rows))
    provisional_prefix = len(prefixes) == len(rows) and all(row["passed"] for row in prefixes)
    blind_opened = bool(execution and provisional_raw and provisional_prefix
                        and replay["passed"] and calibration["passed"] and len(rows) == 6)
    if blind_opened:
        for stream in streams[6:]:
            row, prefix = _run_one(stage, base, cfg, tracked, stream, centered, revision,
                                   output, runner_cls)
            rows.append(row); prefixes.append(prefix)
            if not row.get("passed"):
                execution = False
                break
    blind = (qualification_metrics(
        rows, stage, model, "blind", calibration.get("calibrated_non_event_half_width"))
        if blind_opened else {"role": "blind", "opened": False, "passed": False})
    inventory = io.raw_inventory(output, rows, stage)
    raw_ok = (not inventory["missing_required_artifacts"]
              and inventory["required_artifact_files"]
              == 5 * sum(len(row.get("states", [])) for row in rows))
    prefix_ok = len(prefixes) == len(rows) and all(row["passed"] for row in prefixes)
    if not execution:
        route = stage["routes"]["execution_or_interface_fail"]
    elif not raw_ok:
        route = stage["routes"]["raw_integrity_fail"]
    elif not prefix_ok:
        route = stage["routes"]["prefix_mismatch"]
    elif not replay["passed"]:
        route = stage["routes"]["replay_fail"]
    elif not calibration["passed"]:
        route = stage["routes"]["calibration_fail"]
    elif not blind_opened or len(rows) != 10 or not blind["passed"]:
        route = stage["routes"]["blind_fail"]
    else:
        route = stage["routes"]["pass"]
    counters = {key: sum(int(row.get(key, 0)) for row in rows) for key in
                ("reset_calls", "advance_attempts", "plant_advance_gotsc_calls",
                 "verified_plant_advances")}
    result = {
        "schema_version": SCHEMA, "source_revision": revision,
        "stage_config_sha256": CONFIG_SHA256, "passed": route == stage["routes"]["pass"],
        "route": route, "storage_gate": storage, "run_root_isolation": isolation,
        "execution_integrity_passed": execution, "raw_integrity_passed": raw_ok,
        "prefix_checks": prefixes, "calibration_replay_metrics": replay,
        "calibration_metrics": calibration, "blind_opened": blind_opened,
        "blind_metrics": blind, "rollouts_started": len(rows),
        "complete_rollouts": sum(bool(row.get("passed") and len(row.get("states", [])) == 72)
                                 for row in rows),
        **counters, **inventory, "models_fit_or_updated": 0,
        "fresh_calibration_records_read": 4 if len(rows) >= 5 else 0,
        "fresh_blind_records_read": 4 if len(rows) == 10 else 0,
        "model_payload_sha256": model["payload_sha256"],
        "id2z35_fit_rows": 0,
        "claim_boundary": stage["claim_boundary"],
    }
    io.write_new(output / "result.json", result)
    return result


def run(config: Path, revision: str, output: Path) -> dict[str, Any]:
    output = _inside(output, "output")
    if output.exists():
        raise FileExistsError(str(output))
    stage, base, cfg, preflight, tracked, model = load(config)
    output.parent.mkdir(parents=True, exist_ok=True)
    storage = io.storage(stage, output)
    output.mkdir()
    pre = offline(config, revision)
    io.write_new(output / "offline_preflight.json", pre)
    if not storage["passed"] or not pre["passed"]:
        route = stage["routes"]["storage_fail" if not storage["passed"] else "offline_or_input_fail"]
        result = {"schema_version": SCHEMA, "source_revision": revision,
                  "stage_config_sha256": CONFIG_SHA256, "passed": False,
                  "route": route, "storage_gate": storage, "reasons": pre["failures"],
                  "rollouts_started": 0, "reset_calls": 0, "advance_attempts": 0,
                  "plant_advance_gotsc_calls": 0, "verified_plant_advances": 0,
                  "models_fit_or_updated": 0, "fresh_calibration_records_read": 0,
                  "fresh_blind_records_read": 0}
        io.write_new(output / "result.json", result)
        return result
    try:
        return execute(stage, base, cfg, preflight, tracked, model, revision, output, storage)
    except Exception as exc:
        rows = []
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
            inventory = io.raw_inventory(output, rows, stage)
        except Exception as inv:
            inventory = {"required_artifact_files": 0, "required_artifact_bytes": 0,
                         "required_artifact_inventory_sha256": None,
                         "missing_required_artifacts": [f"FINALIZER:{type(inv).__name__}:{inv}"]}
        result = {"schema_version": SCHEMA, "source_revision": revision,
                  "stage_config_sha256": CONFIG_SHA256, "passed": False,
                  "route": stage["routes"]["execution_or_interface_fail"],
                  "failure": f"{type(exc).__name__}:{exc}", "storage_gate": storage,
                  "rollouts_started": len(rows), **counters, **inventory,
                  "models_fit_or_updated": 0, "fresh_calibration_records_read": 0,
                  "fresh_blind_records_read": 0,
                  "claim_boundary": "Best-effort execution failure; no scientific verdict."}
        if not (output / "result.json").exists():
            io.write_new(output / "result.json", result)
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
        io.write_new(args.output, value)
    print(json.dumps(value, sort_keys=True, allow_nan=False))
    return 0 if value["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
