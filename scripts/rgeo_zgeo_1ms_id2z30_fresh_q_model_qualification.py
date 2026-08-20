#!/usr/bin/env python3
"""Run the frozen fresh ID-2Z30 q-model qualification campaign."""

from __future__ import annotations

import argparse
import copy
from decimal import Decimal
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

from scripts import rgeo_zgeo_1ms_id2z27_dynamic_output_aligned_campaign as z27  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2z26_dynamic_output_aligned_preflight as z26  # noqa: E402


CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z30_fresh_q_model_qualification.json"
CONFIG_SHA256 = "37b0bdfeb56079cd6de9fe95805de96294848534d75cda620e5ba179049f1c95"
SCHEMA = "rgeo-zgeo-1ms-id2z30-fresh-q-model-qualification-result-v1"
ROW_SCHEMA = "rgeo-zgeo-1ms-id2z30-fresh-q-model-qualification-row-v1"
OFFLINE_SCHEMA = "rgeo-zgeo-1ms-id2z30-fresh-q-model-qualification-offline-v1"


def _inside(path: Path, label: str) -> Path:
    value = path.resolve()
    try:
        value.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(f"ID2Z30 {label} leaves repository") from exc
    return value


def _sha(path: Path) -> str:
    return hashlib.sha256(_inside(path, "hash path").read_bytes()).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(_inside(path, "JSON path").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("ID2Z30 JSON object required")
    return value


def _require(stage: dict[str, Any]) -> None:
    if _sha(CONFIG) != CONFIG_SHA256 or stage != _read(CONFIG):
        raise ValueError("ID2Z30 frozen config changed")
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2z30-fresh-q-model-qualification-v1",
        "identity": "rgeo-zgeo-1ms-id2z30-fresh-q-model-qualification-v1",
        "stage": "ID-2Z30", "takeover_time_ms": 1100,
        "control_period_ms": 1, "common_horizon_steps": 73,
        "calibration_phase_issue": 36, "blind_phase_issue": 44,
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
            raise ValueError(f"ID2Z30 frozen field changed: {key}")
    ids = [row.get("family_id") for row in stage.get("rollout_specs", [])]
    if len(ids) != 10 or len(ids) != len(set(ids)):
        raise ValueError("ID2Z30 rollout matrix changed")


def load(config: Path = CONFIG) -> tuple[dict[str, Any], dict[str, Any], Any,
                                          dict[str, Any], dict[str, Any], dict[str, Any]]:
    if config.resolve() != CONFIG.resolve():
        raise ValueError("ID2Z30 alternate config forbidden")
    stage = _read(config); _require(stage)
    evidence: dict[str, dict[str, Any]] = {}
    for name, spec in stage["evidence"].items():
        path = ROOT / spec["path"]
        if _sha(path) != spec["sha256"]:
            raise ValueError(f"ID2Z30 evidence hash mismatch: {name}")
        if path.suffix == ".json":
            evidence[name] = _read(path)
    if (evidence["id2z26r1_preflight"].get("passed") is not True
            or evidence["id2z26r1_independent"].get("audit_passed") is not True
            or evidence["id2z28_result"].get("model_validation_passed") is not True
            or evidence["id2z28_result"].get("model", {}).get("payload_sha256")
            != stage["data_contract"]["model_payload_sha256"]
            or evidence["id2z29_result"].get("route")
            != stage["evidence"]["id2z29_result"]["required_route"]
            or evidence["id2z29_independent"].get("audit_passed") is not True):
        raise ValueError("ID2Z30 prerequisite identity mismatch")
    _, base, cfg, _, _, tracked = z27.z23.load(z27.z23.CONFIG)
    return stage, base, cfg, evidence["id2z26r1_preflight"], tracked, evidence["id2z28_result"]


def _branch_fields(preflight: dict[str, Any], phase: int, axis: str,
                   sign: str) -> list[tuple[str, ...]]:
    center = next(row for row in preflight["prospective_static_streams"]
                  if row["rollout_id"] == "baseline_transition_center")
    center_fields = [tuple(row) for row in center["card15_targets"]]
    nominal = tuple(Decimal(value) for value in preflight["nominal_field_increment"])
    increment = tuple(Decimal(value) for value in
                      preflight["output_aligned_field_increments"][axis])
    return z26._build_branch(center_fields, nominal, increment, phase,
                             1 if sign == "plus" else -1)


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
                      if phase is None else _branch_fields(
                          preflight, int(phase), spec["axis_id"], spec["initial_sign"]))
            targets = z27._targets(fields, cfg, family)
            actions = z27._actions(targets, cfg, family, tracked)
            checkpoint = 32 if phase is None else int(phase)
            row = {"rollout_id": family, "candidate_id": family,
                   "family_id": family, "kind": spec["kind"],
                   "data_role": spec["data_role"], "phase_issue": phase,
                   "axis_id": spec.get("axis_id"),
                   "initial_sign": spec.get("initial_sign"),
                   "fit_weight": 0, "round_index": 0,
                   "round_id": "fresh_q_model_qualification",
                   "cell_id": family, "cell_kind": "fresh_q_qualification",
                   "context_id": f"canonical_dynamic_state{checkpoint}",
                   "coordinate": "full_f_to_slack_qrz_sustained8_return_bridge8",
                   "probe_issue_step": phase,
                   "probe_duration_issues": 0 if phase is None else 8,
                   "prefix_checkpoint_last_state": checkpoint,
                   "non_nominal_issue_steps": [] if phase is None else list(
                       range(int(phase), int(phase) + 16)),
                   "targets": targets, "actions": actions}
        rows.append(row); by_id[family] = row
    return rows


def validate_stream(stream: dict[str, Any], cfg: Any) -> dict[str, Any]:
    failures: list[str] = []
    if len(stream["targets"]) != 73 or len(stream["actions"]) != 73:
        failures.append("STREAM_DIMENSIONS")
    for issue, action in enumerate(stream["actions"]):
        if (action.get("issue_step") != issue
                or action.get("effect_state_index") != issue + 1
                or float(action.get("maximum_issued_delta_a", math.inf)) > .3000000001):
            failures.append(f"ACTION:{issue}")
    headroom = float(z27.z6._headroom(stream["targets"], cfg))
    if headroom < -1e-9:
        failures.append("ABSOLUTE_CURRENT_LIMIT")
    return {"rollout_id": stream["rollout_id"], "passed": not failures,
            "failures": failures, "minimum_absolute_current_headroom_a": headroom,
            "maximum_issued_delta_a": max(float(row["maximum_issued_delta_a"])
                                           for row in stream["actions"])}


def _runtime(stage: dict[str, Any], base: dict[str, Any], stream: dict[str, Any]) -> dict[str, Any]:
    value = dict(base); value.update(stage); value["horizon_steps"] = 73
    decision = int(stream["prefix_checkpoint_last_state"])
    value["decision_state_index"] = decision
    value["rounds"] = [{"round_index": 0, "decision_state_index": decision}]
    value["prefix_gates"] = {"checkpoint_indices": list(range(decision + 1))}
    value["empirical_exploration"] = dict(stage["empirical_exploration"])
    value["empirical_exploration"]["inner_novel_issue_clearance"] = dict(
        stage["empirical_exploration"]["simulator_development_preissue_clearance"])
    return value


def _execute_row(cfg: Any, stage: dict[str, Any], base: dict[str, Any],
                 stream: dict[str, Any], reference: dict[str, Any], revision: str,
                 output: Path, runner_cls: type | None = None) -> dict[str, Any]:
    row = z27.z6.one_rollout(cfg, _runtime(stage, base, stream), stream, reference,
                            runner_cls=runner_cls)
    row.update({"schema_version": ROW_SCHEMA, "source_revision": revision,
                "family_id": stream["family_id"], "kind": stream["kind"],
                "phase_issue": stream["phase_issue"], "axis_id": stream["axis_id"],
                "initial_sign": stream["initial_sign"],
                "fit_weight": 0, "data_role": stream["data_role"]})
    z27.io.write_new(output / f"{stream['rollout_id']}.json", row)
    return row


def _response(row: dict[str, Any], baseline: dict[str, Any], phase: int) -> np.ndarray:
    return np.asarray([[float(row["states"][phase + h][key])
                        - float(baseline["states"][phase + h][key])
                        for key in ("r_geo_m", "z_geo_m", "ip_a")]
                       for h in range(1, 9)], float)


def model_metrics(rows: Sequence[dict[str, Any]], baseline: dict[str, Any],
                  phase: int, prefix: str, model: dict[str, Any],
                  gates: dict[str, Any]) -> dict[str, Any]:
    scales = np.asarray([gates["response_scales"][key]
                         for key in ("r_geo_m", "z_geo_m", "ip_a")], float)
    errors: list[np.ndarray] = []; cosines: list[float] = []
    velocity: list[float] = []; truth_h8: list[np.ndarray] = []
    predicted_h8: list[np.ndarray] = []; branches: list[dict[str, Any]] = []
    by_id = {row["family_id"]: row for row in rows}
    for axis in ("q_r", "q_z"):
        prediction_base = np.asarray(model["odd_step_response"][axis], float)
        for sign_name, sign in (("plus", 1.0), ("minus", -1.0)):
            family = f"{prefix}_issue{phase}__{axis}__{sign_name}_then_return"
            row = by_id.get(family)
            complete = bool(row and row.get("passed") and len(row.get("states", [])) == 74)
            if not complete:
                branches.append({"family_id": family, "complete": False, "passed": False})
                continue
            truth = _response(row, baseline, phase); prediction = sign * prediction_base
            error = prediction - truth; errors.append(error)
            local_cosines = []
            for left, right in zip(prediction[:, :2], truth[:, :2]):
                denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
                value = float(np.dot(left, right) / denominator) if denominator else -1.0
                cosines.append(value); local_cosines.append(value)
            vel = float(np.linalg.norm(((prediction[7, :2] - prediction[6, :2])
                                        - (truth[7, :2] - truth[6, :2])) / .001))
            velocity.append(vel); truth_h8.append(truth[7, :2]); predicted_h8.append(prediction[7, :2])
            scaled = error / scales
            branches.append({"family_id": family, "complete": True,
                             "scaled_rmse": float(np.sqrt(np.mean(scaled ** 2))),
                             "scaled_absolute_error_p95": float(np.percentile(np.abs(scaled), 95)),
                             "minimum_rz_direction_cosine": min(local_cosines),
                             "terminal_response_velocity_error_m_per_s": vel,
                             "passed": True})
    if len(errors) != 4:
        return {"passed": False, "branches": branches, "complete_branches": len(errors)}
    array = np.stack(errors); scaled = array / scales
    regrets = []
    for index in range(int(gates["direction_grid_count"])):
        angle = 2 * math.pi * index / int(gates["direction_grid_count"])
        direction = np.asarray([math.cos(angle), math.sin(angle)])
        truth_value = np.asarray(truth_h8) @ direction
        prediction_value = np.asarray(predicted_h8) @ direction
        regrets.append(float(np.max(truth_value)
                             - truth_value[int(np.argmax(prediction_value))]))
    metrics = {"scaled_response_rmse": float(np.sqrt(np.mean(scaled ** 2))),
               "scaled_absolute_error_p95": float(np.percentile(np.abs(scaled), 95)),
               "minimum_rz_direction_cosine": min(cosines),
               "maximum_terminal_response_velocity_error_m_per_s": max(velocity),
               "maximum_h8_action_ranking_regret_m": max(regrets),
               "branches": branches, "raw_errors": array.tolist()}
    metrics["passed"] = bool(
        metrics["scaled_response_rmse"] <= gates["maximum_scaled_response_rmse"]
        and metrics["scaled_absolute_error_p95"] <= gates["maximum_scaled_absolute_error_p95"]
        and metrics["minimum_rz_direction_cosine"] >= gates["minimum_rz_direction_cosine"]
        and metrics["maximum_terminal_response_velocity_error_m_per_s"]
        <= gates["maximum_terminal_response_velocity_error_m_per_s"]
        and metrics["maximum_h8_action_ranking_regret_m"]
        <= gates["maximum_h8_action_ranking_regret_m"])
    return metrics


def calibrated_tube(calibration: dict[str, Any], gates: dict[str, Any]) -> np.ndarray:
    error = np.abs(np.asarray(calibration["raw_errors"], float))
    floor = np.asarray([gates["tube_floor"][key]
                        for key in ("r_geo_m", "z_geo_m", "ip_a")], float)
    return float(gates["tube_inflation"]) * np.max(error, axis=0) + floor


def blind_containment(blind: dict[str, Any], tube: np.ndarray) -> dict[str, Any]:
    if "raw_errors" not in blind:
        return {"passed": False, "contained": 0, "total": 96}
    error = np.abs(np.asarray(blind["raw_errors"], float))
    contained = error <= tube[None, :, :] + 1e-15
    return {"passed": bool(np.all(contained)), "contained": int(np.sum(contained)),
            "total": int(contained.size), "maximum_ratio": float(np.max(
                np.divide(error, tube[None, :, :], out=np.zeros_like(error), where=tube[None, :, :] > 0)))}


def offline(config: Path, revision: str) -> dict[str, Any]:
    failures: list[str] = []
    try:
        stage, _, cfg, preflight, tracked, _ = load(config)
        streams = build_streams(stage, cfg, preflight, tracked)
        checks = [validate_stream(row, cfg) for row in streams]
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
            preflight: dict[str, Any], tracked: dict[str, Any], model_result: dict[str, Any],
            revision: str, output: Path, storage: dict[str, Any],
            runner_cls: type | None = None) -> dict[str, Any]:
    isolation = z27.z7.configure_run_root(cfg, output)
    streams = build_streams(stage, cfg, preflight, tracked)
    rows: list[dict[str, Any]] = []; prefixes: list[dict[str, Any]] = []
    centered: dict[str, Any] | None = None; execution = True
    calibration: dict[str, Any] | None = None; tube: np.ndarray | None = None
    replay = {"passed": False, "failures": ["NOT_RUN"]}; blind_opened = False
    for index, stream in enumerate(streams):
        if index == 6:
            if centered is None:
                break
            calibration = model_metrics(rows, centered, 36, "cal",
                                        model_result["model"], stage["model_gates"])
            replay = z27.z6.replay_check(rows[3], rows[5], stage["semantic_artifacts"])
            if not calibration["passed"] or not replay["passed"]:
                break
            tube = calibrated_tube(calibration, stage["model_gates"])
            blind_opened = True
        reference_source = tracked if stream["kind"] == "center_baseline" else centered
        reference = (z27.z6._reference(tracked, 33) if stream["kind"] == "center_baseline"
                     else z27.z6._reference(centered or {}, int(stream["prefix_checkpoint_last_state"]) + 1))
        row = _execute_row(cfg, stage, base, stream, reference, revision, output,
                           runner_cls=runner_cls)
        rows.append(row)
        state_count = 33 if stream["kind"] == "center_baseline" else int(stream["prefix_checkpoint_last_state"]) + 1
        prefixes.append(z27.z6.prefix_check(row, reference_source or {}, state_count,
                                            state_count - 1, stage["semantic_artifacts"]))
        if stream["kind"] == "center_baseline" and row.get("passed") and len(row.get("states", [])) == 74:
            centered = row
        if not row.get("passed"):
            execution = False; break
    if calibration is None and centered is not None and len(rows) >= 6:
        calibration = model_metrics(rows, centered, 36, "cal",
                                    model_result["model"], stage["model_gates"])
        replay = z27.z6.replay_check(rows[3], rows[5], stage["semantic_artifacts"])
        if calibration.get("passed") and replay.get("passed"):
            tube = calibrated_tube(calibration, stage["model_gates"])
    blind = (model_metrics(rows, centered, 44, "blind", model_result["model"],
                           stage["model_gates"])
             if centered is not None and len(rows) == 10 else {"passed": False})
    containment = (blind_containment(blind, tube) if tube is not None
                   else {"passed": False, "contained": 0, "total": 96})
    counters = {key: sum(int(row.get(key, 0)) for row in rows) for key in
                ("reset_calls", "advance_attempts", "plant_advance_gotsc_calls",
                 "verified_plant_advances")}
    inventory = z27.io.raw_inventory(output, rows, stage)
    raw_ok = (not inventory["missing_required_artifacts"]
              and inventory["required_artifact_files"] == 5 * sum(len(row.get("states", [])) for row in rows))
    prefix_ok = len(prefixes) == len(rows) and all(row["passed"] for row in prefixes)
    if not execution:
        route = stage["routes"]["execution_or_interface_fail"]
    elif not raw_ok:
        route = stage["routes"]["raw_integrity_fail"]
    elif not prefix_ok:
        route = stage["routes"]["prefix_mismatch"]
    elif not replay["passed"]:
        route = stage["routes"]["replay_fail"]
    elif not calibration or not calibration.get("passed"):
        route = stage["routes"]["calibration_fail"]
    elif len(rows) != 10 or not blind.get("passed") or not containment["passed"]:
        route = stage["routes"]["blind_fail"]
    else:
        route = stage["routes"]["pass"]
    result = {"schema_version": SCHEMA, "source_revision": revision,
              "stage_config_sha256": CONFIG_SHA256, "passed": route == stage["routes"]["pass"],
              "route": route, "storage_gate": storage, "run_root_isolation": isolation,
              "execution_integrity_passed": execution, "raw_integrity_passed": raw_ok,
              "prefix_checks": prefixes, "replay_metrics": replay,
              "calibration_metrics": calibration, "calibrated_tube": None if tube is None else tube.tolist(),
              "blind_opened": blind_opened, "blind_metrics": blind,
              "blind_containment": containment, "rollouts_started": len(rows),
              "complete_rollouts": sum(bool(row.get("passed") and len(row.get("states", [])) == 74) for row in rows),
              **counters, **inventory, "models_fit_or_updated": 0,
              "calibration_records_read": min(4, max(0, len(rows) - 1)),
              "blind_records_read": max(0, len(rows) - 6),
              "future_feedback_records_read": 0,
              "model_payload_sha256": model_result["model"]["payload_sha256"],
              "claim_boundary": stage["claim_boundary"]}
    z27.io.write_new(output / "result.json", result)
    return result


def run(config: Path, revision: str, output: Path) -> dict[str, Any]:
    output = _inside(output, "output")
    if output.exists():
        raise FileExistsError(str(output))
    stage, base, cfg, preflight, tracked, model = load(config)
    output.parent.mkdir(parents=True, exist_ok=True)
    storage = z27.io.storage(stage, output); output.mkdir()
    pre = offline(config, revision); z27.io.write_new(output / "offline_preflight.json", pre)
    if not storage["passed"] or not pre["passed"]:
        route = stage["routes"]["storage_fail" if not storage["passed"] else "offline_or_input_fail"]
        result = {"schema_version": SCHEMA, "source_revision": revision,
                  "stage_config_sha256": CONFIG_SHA256, "passed": False,
                  "route": route, "storage_gate": storage, "reasons": pre["failures"],
                  "rollouts_started": 0, "reset_calls": 0, "advance_attempts": 0,
                  "plant_advance_gotsc_calls": 0, "verified_plant_advances": 0,
                  "models_fit_or_updated": 0}
        z27.io.write_new(output / "result.json", result); return result
    try:
        return execute(stage, base, cfg, preflight, tracked, model, revision, output, storage)
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
            inventory = z27.io.raw_inventory(output, rows, stage)
        except Exception as inventory_exc:
            inventory = {"required_artifact_files": 0, "required_artifact_bytes": 0,
                         "required_artifact_inventory_sha256": None,
                         "missing_required_artifacts": [
                             f"FINALIZER:{type(inventory_exc).__name__}:{inventory_exc}"]}
        result = {"schema_version": SCHEMA, "source_revision": revision,
                  "stage_config_sha256": CONFIG_SHA256, "passed": False,
                  "route": stage["routes"]["execution_or_interface_fail"],
                  "failure": f"{type(exc).__name__}:{exc}", "storage_gate": storage,
                  "rollouts_started": len(rows), "complete_rollouts": sum(
                      bool(row.get("passed") and len(row.get("states", [])) == 74)
                      for row in rows), **counters, **inventory,
                  "models_fit_or_updated": 0,
                  "claim_boundary": "Best-effort execution failure; no scientific qualification verdict."}
        if not (output / "result.json").exists():
            z27.io.write_new(output / "result.json", result)
        return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)
    if args.offline:
        value = offline(args.config, args.source_revision)
        z27.io.write_new(args.output, value)
    else:
        try:
            value = run(args.config, args.source_revision, args.output)
        except Exception as exc:
            value = {"schema_version": SCHEMA, "source_revision": args.source_revision,
                     "stage_config_sha256": _sha(args.config), "passed": False,
                     "route": _read(args.config)["routes"]["execution_or_interface_fail"],
                     "failure": f"{type(exc).__name__}:{exc}",
                     "models_fit_or_updated": 0}
            if not args.output.exists():
                args.output.mkdir(parents=True, exist_ok=True)
            if not (args.output / "result.json").exists():
                z27.io.write_new(args.output / "result.json", value)
    print(json.dumps(value, sort_keys=True, allow_nan=False))
    return 0 if value["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
