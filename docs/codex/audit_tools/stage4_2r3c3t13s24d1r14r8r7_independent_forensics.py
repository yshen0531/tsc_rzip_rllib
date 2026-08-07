#!/usr/bin/env python3
"""Structurally independent R8R7 source, raw, and prediction forensics."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r7r2_independent_forensics as independent_response,
    stage4_2r3c3t13s24d1r14r8_independent_forensics as independent_r8,
    stage4_2r3c3t13s24d1r14r8r1_independent_forensics as independent_r8r1,
    stage4_2r3c3t13s24d1r14r8r3_independent_forensics as independent_observer,
    stage4_2r3c3t13s24d1r14r8r4_independent_forensics as independent_observer_metrics,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r1_fixed_candidate_short_horizon_discriminator as r8r1,
    stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_sentinel as contract,
)


def _read(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def _gzip(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(
            stream,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stage(run_dir: Path) -> Path:
    return run_dir.expanduser().resolve() / contract.RUN_NAME


def _inventory(path: Path) -> dict[str, Any]:
    files = sorted(path.glob("*.json.gz"), key=lambda value: value.name)
    digest = hashlib.sha256()
    rows = []
    for value in files:
        size = value.stat().st_size
        sha = _sha(value)
        digest.update(f"{value.name}\0{size}\0{sha}\n".encode())
        rows.append({"name": value.name, "size": size, "sha256": sha})
    return {
        "count": len(rows),
        "bytes": sum(int(row["size"]) for row in rows),
        "digest": digest.hexdigest(),
        "rows": rows,
    }


def _response_training(args: argparse.Namespace, cfg: Mapping[str, Any]):
    r8r1_cfg = _read(Path(__file__).resolve().parents[3] / str(cfg["source_r8r1_config"]))
    items, r8_cfg = independent_r8r1._authenticate(args, r8r1_cfg)
    rows, folds = independent_r8r1._outer(items, r8r1_cfg, r8_cfg)
    horizon = int(cfg["response_model_contract"]["relative_lag_horizon"])
    evaluation = independent_r8r1._horizon(items, rows[horizon], horizon, r8r1_cfg, r8_cfg)
    truncated = [independent_r8r1._truncate(item, horizon) for item in items]
    mcfg = independent_r8r1._model_cfg(r8r1_cfg, r8_cfg)
    fitted = independent_response._fit(truncated, (4, 2.0, 0.1), mcfg)
    return items, rows[horizon], folds, evaluation, fitted, mcfg


def _serialize_response(model: Mapping[str, Any]) -> dict[str, Any]:
    mean, scale, components = model["prep"]
    heads = {}
    for (sign, direction), (amplitude_mean, amplitude_scale, lags) in model["heads"].items():
        heads[f"{sign}:{direction}"] = {
            "amplitude_mean": float(amplitude_mean),
            "amplitude_scale": float(amplitude_scale),
            "lags": [
                {
                    "lag": index + 1,
                    "x": np.asarray(x).tolist(),
                    "bandwidth": float(bandwidth),
                    "y_mean": np.asarray(y_mean).tolist(),
                    "alpha": np.asarray(alpha).tolist(),
                }
                for index, (x, bandwidth, y_mean, alpha) in enumerate(lags)
            ],
        }
    return {
        "candidate": {"pca_rank": 4, "bandwidth_multiplier": 2.0, "ridge": 0.1},
        "preprocessor": {
            "mean": np.asarray(mean).tolist(),
            "scale": np.asarray(scale).tolist(),
            "components": np.asarray(components).tolist(),
        },
        "heads": heads,
    }


def offline_audit(args: argparse.Namespace, cfg: Mapping[str, Any]) -> dict[str, Any]:
    stage = _stage(args.run_dir)
    primary_path = stage / "analysis" / "offline_preflight.json"
    primary = _read(primary_path)
    items, rows, folds, evaluation, fitted, _ = _response_training(args, cfg)
    horizon = 4
    by_id = {str(row["response_id"]): row for row in items}
    scales = np.asarray(cfg["bank_contract"]["response_scales"], dtype=float)
    residual = np.asarray(
        [
            np.abs(
                np.asarray(row["predicted_response"], dtype=float)
                - np.asarray(by_id[str(row["response_id"])]["response"][:horizon], dtype=float)
            )
            * scales[None, :]
            for row in rows
        ]
    )
    response_tube = (
        np.asarray(cfg["tube_contract"]["response_floor_physical"], dtype=float)[None, :]
        + 2.0 * np.max(residual, axis=0)
    )
    response_artifact = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "campaign_identity": contract.IDENTITY,
        "relative_lag_horizon": 4,
        "fixed_candidate": {"pca_rank": 4, "bandwidth_multiplier": 2.0, "ridge": 0.1},
        "training_response_count": 912,
        "training_pair_count": 12,
        "validation_claim": False,
        "model": _serialize_response(fitted),
    }
    expected_model = stage / "analysis" / "offline_independent_expected_response_model.json"
    expected_tube = stage / "analysis" / "offline_independent_expected_response_tube.json"
    _write(expected_model, response_artifact)
    _write(
        expected_tube,
        {
            "schema_version": 1,
            "stage": contract.STAGE,
            "tube_physical": response_tube.tolist(),
            "derivation": cfg["tube_contract"]["response_method"],
            "source_oof_response_count": 912,
        },
    )
    r8r6_stage = args.r8r6_run.resolve() / "stage4_2r3c3t13s24d1r14r8r6_causal_one_step_innovation_observer"
    static_tube = np.asarray(_read(r8r6_stage / "model" / "observer_tube.json")["tube_physical"], dtype=float)
    combined = static_tube[:4] + response_tube
    combined_value = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "static_observer_model_sha256": cfg["source_r8r6_contract"]["observer_model_sha256"],
        "static_observer_tube_sha256": cfg["source_r8r6_contract"]["observer_tube_sha256"],
        "response_model_sha256": _sha(expected_model),
        "response_tube_sha256": _sha(expected_tube),
        "combined_tube_physical": combined.tolist(),
        "combined_caps_physical": list(map(float, cfg["tube_contract"]["combined_caps_physical"])),
        "cap_passed": bool(
            np.all(combined <= np.asarray(cfg["tube_contract"]["combined_caps_physical"])[None, :] + 1e-15)
        ),
    }
    expected_combined = stage / "analysis" / "offline_independent_expected_combined_tube.json"
    _write(expected_combined, combined_value)
    specs = _read(stage / "specs" / "all_specs.json")
    spec_ok = bool(
        len(specs) == 48
        and sum(row["partition"] == "baseline" for row in specs) == 16
        and sum(row["partition"] == "multipulse" for row in specs) == 32
        and all(row.get("r8r7_allowed_in_expert_dataset") is False for row in specs)
        and all(
            tuple(map(int, row["r8r7_issue_task_steps"])) == contract.ISSUE_STEPS
            for row in specs
            if row["partition"] == "multipulse"
        )
    )
    model_sha = _sha(expected_model)
    tube_sha = _sha(expected_tube)
    combined_sha = _sha(expected_combined)
    numerical = bool(
        len(folds) == 12
        and int(evaluation["aggregate"]["response_pass_count"]) == 832
        and primary["horizon_evaluation"] == r8r1.compact_horizon(evaluation)
    )
    artifact = bool(
        model_sha == _sha(stage / "model" / "response_model.json")
        and tube_sha == _sha(stage / "model" / "response_tube.json")
        and combined_sha == _sha(stage / "model" / "combined_tube.json")
    )
    outcome = bool(primary.get("passed") is True and spec_ok and combined_value["cap_passed"])
    result = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "audit_kind": "offline_independent",
        "response_model_sha256": model_sha,
        "response_tube_sha256": tube_sha,
        "combined_tube_sha256": combined_sha,
        "primary_sha256": _sha(primary_path),
        "primary_numerical_agreement": numerical,
        "primary_outcome_agreement": outcome,
        "artifact_hash_agreement": artifact,
        "new_raw_count": 0,
        "plant_advance_count": 0,
        "passed": bool(numerical and outcome and artifact),
    }
    if not result["passed"]:
        raise ValueError("R8R7 independent offline audit disagrees")
    _write(stage / "analysis" / "offline_independent.json", result)
    return result


def raw_audit(args: argparse.Namespace, cfg: Mapping[str, Any], phase: str) -> dict[str, Any]:
    stage = _stage(args.run_dir)
    specs = [row for row in _read(stage / "specs" / "all_specs.json") if row["partition"] == phase]
    expected = {"baseline": 16, "multipulse": 32}[phase]
    rows = []
    for spec in specs:
        path = stage / "raw" / phase / f"{spec['experiment_id']}.json.gz"
        value = _gzip(path)
        horizon = int(spec["horizon_steps"])
        trajectory, trace = value.get("trajectory") or [], value.get("controller_trace") or []
        events = [
            row.get("r3c3t13s24d1r14r8r7_event")
            for row in trace[10:]
            if row.get("r3c3t13s24d1r14r8r7_event") != "none"
        ]
        event_details = [
            row.get("r3c3t13s24d1r14r8r7_event_detail") or {}
            for row in trace[10:]
            if row.get("r3c3t13s24d1r14r8r7_event") != "none"
        ]
        action = np.asarray([row.get("action_norm_tsc", []) for row in trace], dtype=float)
        current = np.asarray([row.get("currents_a_tsc", []) for row in trajectory], dtype=float)
        forbidden = sum(
            any(bool(row.get(key)) for key in cfg["forbidden_predictor_fields"])
            for row in trace
        )
        passed = bool(
            value.get("success")
            and value.get("completed")
            and value.get("stage") == contract.STAGE
            and value.get("campaign_identity") == contract.IDENTITY
            and value.get("controller_revision") == contract.CONTROLLER_REVISION
            and value.get("spec") == spec
            and len(trajectory) == horizon + 1
            and len(trace) == horizon
            and action.shape == (horizon, 14)
            and current.shape == (horizon + 1, 14)
            and np.all(np.isfinite(action))
            and np.all(np.isfinite(current))
            and forbidden == 0
            and (
                (phase == "baseline" and events == [])
                or (
                    phase == "multipulse"
                    and events
                    == [value for _ in range(4) for value in ("sequential_issue", "sequential_cancel")]
                    and len(event_details) == 8
                    and all(item.get("passed") is True for item in event_details)
                    and all(all(bool(v) for v in (item.get("criteria") or {}).values()) for item in event_details)
                )
            )
        )
        rows.append({"experiment_id": spec["experiment_id"], "passed": passed})
    inventory = _inventory(stage / "raw" / phase)
    primary_path = stage / "analysis" / f"{phase}_raw_primary.json"
    primary = _read(primary_path)
    outcome = bool(
        len(rows) == expected
        and sum(row["passed"] for row in rows) == expected
        and inventory["count"] == expected
        and primary.get("passed") is True
        and primary["raw_inventory"]["digest"] == inventory["digest"]
    )
    result = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "audit_kind": f"{phase}_raw_independent",
        "raw_inventory": inventory,
        "raw_inventory_digest": inventory["digest"],
        "strict_parse_count": len(rows),
        "passed_count": sum(row["passed"] for row in rows),
        "primary_sha256": _sha(primary_path),
        "primary_outcome_agreement": outcome,
        "passed": outcome,
    }
    if not result["passed"]:
        raise ValueError(f"R8R7 independent {phase} raw audit disagrees")
    _write(stage / "analysis" / f"{phase}_raw_independent.json", result)
    return result


def _descriptor(
    visible: np.ndarray, spec: Mapping[str, Any], origin: int, cfg: Mapping[str, Any]
) -> np.ndarray:
    offsets = tuple(map(int, cfg["bank_contract"]["history_offsets"]))
    history = visible[[max(0, origin - offset) for offset in offsets]].reshape(-1)
    available = np.asarray([float(offset <= origin) for offset in offsets])
    target = independent_observer._target(spec) / np.asarray(
        cfg["bank_contract"]["target_scales"], dtype=float
    )
    value = np.concatenate((history, available, target, [(origin - 10.0) / 12.0]))
    if value.shape != (142,):
        raise ValueError("R8R7 independent response descriptor changed")
    return value


def _prediction_rows(
    args: argparse.Namespace, cfg: Mapping[str, Any], phase: str
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    stage = _stage(args.run_dir)
    root = Path(__file__).resolve().parents[3]
    r8r6_cfg = _read(root / str(cfg["source_r8r6_config"]))
    r8r6_stage = args.r8r6_run.resolve() / "stage4_2r3c3t13s24d1r14r8r6_causal_one_step_innovation_observer"
    static_model = independent_observer_metrics._artifact_model(
        _read(r8r6_stage / "model" / "observer_model.json")
    )
    static_tube = np.asarray(
        _read(r8r6_stage / "model" / "observer_tube.json")["tube_physical"], dtype=float
    )
    _, _, _, _, action_model, action_cfg = _response_training(args, cfg)
    combined_tube = np.asarray(
        _read(stage / "model" / "combined_tube.json")["combined_tube_physical"], dtype=float
    )
    specs = [row for row in _read(stage / "specs" / "all_specs.json") if row["partition"] == phase]
    scales = np.asarray(cfg["bank_contract"]["visible_scales"], dtype=float)
    point_caps = np.asarray(cfg["gates"]["component_caps_physical"], dtype=float)
    exclusion_caps = np.asarray(cfg["gates"]["finite_exclusion_caps_physical"], dtype=float)
    rows, raw_hashes = [], {}
    for spec in specs:
        path = stage / "raw" / phase / f"{spec['experiment_id']}.json.gz"
        result = _gzip(path)
        visible = independent_observer.frozen._visible(result["trajectory"], scales)
        actions = independent_observer._actions(result)
        currents = independent_observer._currents(result)
        for index, origin in enumerate(contract.ISSUE_STEPS):
            feature = independent_observer._feature(
                visible[: origin + 1],
                actions[:origin],
                currents[: origin + 1],
                independent_observer._target(spec),
                origin,
                r8r6_cfg,
            )
            static_item = {
                "row_id": f"{phase}|{spec['experiment_id']}|origin{origin:02d}",
                "pair_id": str(spec["pair_id"]),
                "history_member": str(spec["history_member"]),
                "origin_task_step": origin,
                "prescribed_issue": True,
                "feature": feature,
                "origin_visible": visible[origin],
                "target_delta": visible[origin + 1 : origin + 13, 2:5]
                - visible[origin, 2:5],
                "future_visible": visible[origin + 1 : origin + 13],
            }
            static_prediction = independent_observer._predict(
                static_model, [static_item], r8r6_cfg
            )[0][:4]
            direction = sign = None
            response_prediction = np.zeros((4, 5), dtype=float)
            tube = static_tube[:4]
            if phase == "multipulse":
                direction = int(spec["r8r7_direction_indices"][index])
                sign = int(spec["r8r7_signs"][index])
                response_item = {
                    "response_id": static_item["row_id"],
                    "descriptor": _descriptor(visible, spec, origin, cfg),
                    "response": np.zeros((4, 5), dtype=float),
                    "sign": sign,
                    "direction_index": direction,
                    "action_scale": 1.0,
                }
                response_prediction = independent_response._predict(
                    action_model, response_item, action_cfg
                )
                tube = combined_tube
            prediction = static_prediction + response_prediction
            actual = visible[origin + 1 : origin + 5]
            absolute = np.abs((prediction - actual) * scales[None, :])
            rows.append(
                {
                    "row_id": static_item["row_id"],
                    "experiment_id": str(spec["experiment_id"]),
                    "context_id": f"{spec['pair_id']}|{spec['history_member']}",
                    "pair_id": str(spec["pair_id"]),
                    "history_member": str(spec["history_member"]),
                    "schedule_index": int(spec["r8r7_schedule_index"]),
                    "origin_task_step": origin,
                    "direction_index": direction,
                    "sign": sign,
                    "static_prediction": static_prediction.tolist(),
                    "response_prediction": response_prediction.tolist(),
                    "combined_prediction": prediction.tolist(),
                    "actual_visible": actual.tolist(),
                    "absolute_residual_physical": absolute.tolist(),
                    "maximum_absolute_scaled_point_error": float(np.max(np.abs(prediction - actual))),
                    "finite_exclusion_violation_count": int(
                        np.sum(absolute > exclusion_caps[None, :] + 1e-15)
                    ),
                    "point_passed": bool(
                        np.all(np.isfinite(prediction))
                        and np.all(absolute <= point_caps[None, :] + 1e-15)
                    ),
                    "tube_contained": bool(np.all(absolute <= tube + 1e-15)),
                }
            )
        raw_hashes[str(spec["experiment_id"])] = _sha(path)
    return sorted(rows, key=lambda row: row["row_id"]), {
        "phase": phase,
        "row_count": len(rows),
        "context_count": len({row["context_id"] for row in rows}),
        "raw_sha256": raw_hashes,
        "forbidden_predictor_input_count": 0,
        "future_input_count": 0,
        "adaptation_enabled": False,
        "allowed_in_expert_dataset": False,
    }


def _evaluate(
    rows: Sequence[Mapping[str, Any]], phase: str, cfg: Mapping[str, Any]
) -> dict[str, Any]:
    point_count = sum(bool(row["point_passed"]) for row in rows)
    tube_count = sum(bool(row["tube_contained"]) for row in rows)
    exclusion = sum(int(row["finite_exclusion_violation_count"]) for row in rows)
    contexts, contexts_passed = {}, True
    for name in sorted({str(row["context_id"]) for row in rows}):
        current = [row for row in rows if row["context_id"] == name]
        point = sum(bool(row["point_passed"]) for row in current)
        tube = sum(bool(row["tube_contained"]) for row in current)
        point_need = int(cfg["gates"][f"{phase}_per_context_point_pass_count"])
        tube_need = int(cfg["gates"][f"{phase}_per_context_tube_pass_count"])
        passed = point >= point_need and tube >= tube_need
        contexts_passed = contexts_passed and passed
        contexts[name] = {
            "total": len(current),
            "point_pass_count": point,
            "point_required": point_need,
            "tube_pass_count": tube,
            "tube_required": tube_need,
            "passed": passed,
        }
    directions, signs, strata_passed = {}, {}, True
    if phase == "multipulse":
        for direction in range(4):
            current = [row for row in rows if int(row["direction_index"]) == direction]
            point = sum(bool(row["point_passed"]) for row in current)
            tube = sum(bool(row["tube_contained"]) for row in current)
            passed = bool(
                point >= int(cfg["gates"]["multipulse_per_direction_point_pass_count"])
                and tube >= int(cfg["gates"]["multipulse_per_direction_tube_pass_count"])
            )
            strata_passed = strata_passed and passed
            directions[str(direction)] = {
                "total": len(current),
                "point_pass_count": point,
                "tube_pass_count": tube,
                "passed": passed,
            }
        for sign in (-1, 1):
            current = [row for row in rows if int(row["sign"]) == sign]
            point = sum(bool(row["point_passed"]) for row in current)
            tube = sum(bool(row["tube_contained"]) for row in current)
            passed = bool(
                point >= int(cfg["gates"]["multipulse_per_sign_point_pass_count"])
                and tube >= int(cfg["gates"]["multipulse_per_sign_tube_pass_count"])
            )
            strata_passed = strata_passed and passed
            signs[str(sign)] = {
                "total": len(current),
                "point_pass_count": point,
                "tube_pass_count": tube,
                "passed": passed,
            }
    point_need = int(cfg["gates"][f"{phase}_required_point_pass_count"])
    tube_need = int(cfg["gates"][f"{phase}_required_tube_pass_count"])
    result = {
        "phase": phase,
        "row_count": len(rows),
        "point_pass_count": point_count,
        "point_required": point_need,
        "tube_containment_count": tube_count,
        "tube_required": tube_need,
        "finite_exclusion_violation_count": exclusion,
        "maximum_absolute_physical_error": np.max(
            np.asarray([row["absolute_residual_physical"] for row in rows]), axis=(0, 1)
        ).tolist(),
        "maximum_absolute_scaled_point_error": max(
            float(row["maximum_absolute_scaled_point_error"]) for row in rows
        ),
        "context_counts": contexts,
        "direction_counts": directions,
        "sign_counts": signs,
    }
    result["passed"] = bool(
        point_count >= point_need
        and tube_count >= tube_need
        and exclusion == 0
        and contexts_passed
        and strata_passed
    )
    return result


def model_audit(args: argparse.Namespace, cfg: Mapping[str, Any], phase: str) -> dict[str, Any]:
    stage = _stage(args.run_dir)
    primary_detailed_path = stage / "analysis" / f"{phase}_model_primary_detailed.json"
    primary_summary_path = stage / "analysis" / f"{phase}_model_primary_summary.json"
    primary = _read(primary_detailed_path)
    summary = _read(primary_summary_path)
    rows, signature = _prediction_rows(args, cfg, phase)
    evaluation = _evaluate(rows, phase, cfg)
    scientific = bool(evaluation["passed"])
    route = str(
        cfg["routes"][
            "pass"
            if scientific
            else ("baseline_model_fail" if phase == "baseline" else "multipulse_model_fail")
        ]
    )
    numerical = bool(
        independent_observer._agrees(primary["source_signature"], signature, cfg)
        and independent_observer._agrees(primary["prediction_rows"], rows, cfg)
        and independent_observer._agrees(primary["evaluation"], evaluation, cfg)
    )
    outcome = bool(
        primary.get("route") == route
        and summary.get("route") == route
        and bool(primary.get("scientific_gate_passed")) is scientific
        and bool(summary.get("scientific_gate_passed")) is scientific
    )
    manifest = _read(stage / "stage_manifest.json")
    artifact = bool(
        _sha(stage / "model" / "response_model.json")
        == manifest.get("response_model_sha256")
        and _sha(stage / "model" / "response_tube.json")
        == manifest.get("response_tube_sha256")
        and _sha(stage / "model" / "combined_tube.json")
        == manifest.get("combined_tube_sha256")
        and _read(stage / "model" / "combined_tube.json").get("cap_passed") is True
    )
    result = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "audit_kind": f"{phase}_model_independent",
        "evaluation": evaluation,
        "route": route,
        "scientific_gate_passed": scientific,
        "primary_sha256": _sha(primary_summary_path),
        "primary_detailed_sha256": _sha(primary_detailed_path),
        "response_model_sha256": _sha(stage / "model" / "response_model.json"),
        "response_tube_sha256": _sha(stage / "model" / "response_tube.json"),
        "combined_tube_sha256": _sha(stage / "model" / "combined_tube.json"),
        "primary_numerical_agreement": numerical,
        "primary_outcome_agreement": outcome,
        "artifact_hash_agreement": artifact,
        "passed": bool(numerical and outcome and artifact),
    }
    if not result["passed"]:
        raise ValueError(f"R8R7 independent {phase} model audit disagrees")
    _write(stage / "analysis" / f"{phase}_model_independent.json", result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--r8-run", type=Path, required=True)
    parser.add_argument("--r8r1-output", type=Path, required=True)
    parser.add_argument("--r8r6-run", type=Path, required=True)
    parser.add_argument("--source-d1r11-run", type=Path, required=True)
    parser.add_argument("--source-r2-run", type=Path, required=True)
    parser.add_argument("--source-r4-run", type=Path, required=True)
    parser.add_argument("--source-r6-run", type=Path, required=True)
    parser.add_argument("--source-s21-run", type=Path, required=True)
    parser.add_argument("--source-s23r1-output", type=Path, required=True)
    parser.add_argument("--source-s24-run", type=Path, required=True)
    parser.add_argument("--source-d1r9-v1", type=Path, required=True)
    parser.add_argument("--source-d1r9-v2", type=Path, required=True)
    parser.add_argument("--source-d1r10-run", type=Path, required=True)
    parser.add_argument("--source-d1r10-audit", type=Path, required=True)
    parser.add_argument("--source-stage42r3b-run", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3-run", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3-bank-dir", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3t1-run", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3t1-audit-dir", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3t3-controller-bank", type=Path, required=True)
    parser.add_argument("--q1-run", type=Path, required=True)
    parser.add_argument("--q2-run", type=Path, required=True)
    parser.add_argument("--q1-audit", type=Path, required=True)
    parser.add_argument("--q2-audit", type=Path, required=True)
    parser.add_argument("--r3b-server-audit", type=Path, required=True)
    parser.add_argument("--r3b-snapshot-checks", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--command", choices=("offline",), required=True)
    parser.add_argument("--backend", choices=("serial", "ray"), default="ray")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument(
        "--audit-kind",
        choices=("offline", "baseline_raw", "baseline_model", "multipulse_raw", "multipulse_model"),
        required=True,
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    cfg = _read(args.config.expanduser().resolve())
    contract.validate_config(cfg, project_root=Path(__file__).resolve().parents[3])
    if args.audit_kind == "offline":
        result = offline_audit(args, cfg)
    elif args.audit_kind.endswith("_raw"):
        result = raw_audit(args, cfg, args.audit_kind.removesuffix("_raw"))
    else:
        result = model_audit(args, cfg, args.audit_kind.removesuffix("_model"))
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
