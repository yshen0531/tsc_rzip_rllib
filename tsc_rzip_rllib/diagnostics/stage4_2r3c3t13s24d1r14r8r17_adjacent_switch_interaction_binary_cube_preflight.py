#!/usr/bin/env python3
"""Run the frozen zero-TSC R8R17 adjacent-switch interaction preflight."""

from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r15_binary_temporal_switching_staircase_authority_sentinel as r15,
)


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S24D1R14R8R17"
IDENTITY = "adjacent_switch_interaction_binary_cube_preflight_v1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r17_adjacent_switch_interaction_binary_cube_preflight"
COMPONENTS = ("R", "Z", "Ip")


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
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


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


@dataclass(frozen=True)
class Paths:
    run_dir: Path
    stage: Path
    source_reference: Path
    analysis: Path
    state: Path
    manifest: Path


@dataclass(frozen=True)
class Context:
    cfg: dict[str, Any]
    config_path: Path
    paths: Paths
    r15_ctx: r15.Context
    r8r15_run: Path
    r8r16_run: Path


def _paths(run_dir: Path) -> Paths:
    root = run_dir.expanduser().resolve()
    stage = root / RUN_NAME
    return Paths(
        run_dir=root,
        stage=stage,
        source_reference=stage / "source_reference",
        analysis=stage / "analysis",
        state=stage / "stage_state.json",
        manifest=stage / "stage_manifest.json",
    )


def _codes(cfg: Mapping[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    contract = cfg["code_contract"]
    return tuple(contract["development_codes"]), tuple(contract["calibration_codes"]), tuple(contract["missing_codes"])


def code_row(code: str) -> np.ndarray:
    if len(code) != 4 or any(symbol not in "UV" for symbol in code):
        raise ValueError(f"invalid R8R17 code: {code}")
    q = np.asarray([1.0 if symbol == "U" else -1.0 for symbol in code])
    adjacent = float((q[0] * q[1] + q[1] * q[2] + q[2] * q[3]) / 3.0)
    return np.asarray([1.0, *q, adjacent])


def design_matrix(codes: Sequence[str]) -> np.ndarray:
    return np.asarray([code_row(code) for code in codes], dtype=float)


def validate_config(cfg: Mapping[str, Any], *, project_root: Path) -> None:
    design = project_root / str(cfg["design_document"])
    source_config = project_root / str(cfg["source_r8r15_config"])
    development, calibration, missing = _codes(cfg)
    all_codes = {"".join(symbols) for symbols in __import__("itertools").product("UV", repeat=4)}
    measured = set(development) | set(calibration)
    model = cfg["model_contract"]
    gates = cfg["calibration_gates"]
    authority = cfg["authority_gate"]
    formal = cfg["formal_contract"]
    scope = cfg["scientific_scope"]
    if (
        int(cfg.get("schema_version", -1)) != SCHEMA_VERSION
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("run_name") != RUN_NAME
        or not design.is_file()
        or _sha(design) != str(cfg["design_document_sha256"])
        or not source_config.is_file()
        or _sha(source_config) != str(cfg["source_r8r15_config_sha256"])
        or development != ("UUUU", "VVVV", "UVVV", "UUVV", "UUUV", "VUUU")
        or calibration != ("VVUU", "VVVU", "UVUV", "VUVU")
        or missing != ("UVUU", "UUVU", "UVVU", "VUUV", "VVUV", "VUVV")
        or measured & set(missing)
        or measured | set(missing) != all_codes
        or tuple(map(int, cfg["code_contract"]["decision_task_steps"])) != (10, 14, 18, 22)
        or (len(development), len(calibration), len(missing)) != (6, 4, 6)
        or (int(cfg["code_contract"]["context_count"]), int(cfg["code_contract"]["calibration_trajectory_count"]), int(cfg["code_contract"]["missing_prediction_count"])) != (16, 64, 96)
        or tuple(model["feature_order"]) != ("intercept", "q10", "q14", "q18", "q22", "normalized_adjacent_persistence")
        or model.get("adjacent_interaction_formula") != "(q10*q14+q14*q18+q18*q22)/3"
        or tuple(model["response_components"]) != COMPONENTS
        or not bool(model["response_relative_to_matched_baseline"])
        or int(model["first_state_index"]) != 10
        or float(model["svd_rcond"]) != 1e-12
        or int(model["required_rank"]) != 6
        or float(model["maximum_development_condition"]) != 6.70
        or float(model["maximum_full_condition"]) != 2.62
        or float(model["maximum_cube_condition"]) != 1.74
        or bool(model["ridge_allowed"])
        or not bool(model["nonlinear_terms_allowed"])
        or bool(model["per_context_hyperparameters_allowed"])
        or tuple(map(float, gates["response_scales"])) != (0.03, 0.03, 10000.0)
        or tuple(map(float, gates["component_error_caps"])) != (0.003, 0.003, 1000.0)
        or float(gates["maximum_scaled_point_error"]) != 0.10
        or (int(gates["required_trajectory_pass_count"]), int(gates["required_formal_classification_count"])) != (64, 64)
        or float(gates["maximum_minimum_margin_absolute_error"]) != 0.05
        or float(gates["tube_multiplier"]) != 2.0
        or tuple(map(float, gates["tube_caps"])) != (0.01, 0.01, 3000.0)
        or (int(authority["required_baseline_formal_pass_count"]), int(authority["required_failed_baseline_count"]), int(authority["minimum_robust_predicted_repair_count"]), int(authority["minimum_robust_predicted_oracle_pass_count"])) != (6, 10, 1, 7)
        or not bool(authority["require_oracle_strictly_improves_baseline"])
        or not bool(authority["robust_margin_strictly_positive"])
        or (int(formal["normal_arrival_deadline_step"]), int(formal["normal_hold_through_step"]), int(formal["weak_arrival_deadline_step"]), int(formal["weak_hold_through_step"])) != (25, 35, 27, 37)
        or (float(formal["position_tolerance_m"]), float(formal["speed_tolerance_m_per_s"]), float(formal["ip_tolerance_A"]), int(formal["arrival_streak_steps"])) != (0.03, 0.1, 10000.0, 3)
        or bool(formal["arrival_deadline_expansion_allowed"])
        or any(bool(scope[key]) for key in ("real_tsc_executed", "controller_executed", "physical_authority_validated", "real_mpc_executed", "gate_a_qualified", "all_source_trajectories_allowed_in_expert_dataset", "expert_data_allowed", "bc_dagger_or_rl_allowed", "global_plant_reachability_claimed"))
        or int(scope["new_raw_count"]) != 0
        or bool(scope["r8r16_predictions_used_as_model_input"])
    ):
        raise ValueError("R8R17 frozen design changed")
    x_dev = design_matrix(development)
    x_full = design_matrix((*development, *calibration))
    x_cube = design_matrix(sorted(all_codes))
    if (
        np.linalg.matrix_rank(x_dev) != 6
        or np.linalg.matrix_rank(x_full) != 6
        or np.linalg.matrix_rank(x_cube) != 6
        or float(np.linalg.cond(x_dev)) > float(model["maximum_development_condition"])
        or float(np.linalg.cond(x_full)) > float(model["maximum_full_condition"])
        or float(np.linalg.cond(x_cube)) > float(model["maximum_cube_condition"])
    ):
        raise ValueError("R8R17 frozen matrix geometry changed")


def load_context(args: argparse.Namespace) -> Context:
    config_path = args.config.expanduser().resolve()
    cfg = _read(config_path)
    validate_config(cfg, project_root=_root())
    source_args = argparse.Namespace(**vars(args))
    source_args.config = (_root() / str(cfg["source_r8r15_config"])).resolve()
    source_args.run_dir = args.r8r15_run.expanduser().resolve()
    return Context(
        cfg=cfg,
        config_path=config_path,
        paths=_paths(args.run_dir),
        r15_ctx=r15.load_context(source_args),
        r8r15_run=args.r8r15_run.expanduser().resolve(),
        r8r16_run=args.r8r16_run.expanduser().resolve(),
    )


def _source_stage(ctx: Context) -> Path:
    return ctx.r8r15_run / str(ctx.cfg["source_r8r15"]["stage_directory"])


def _authenticate_r8r16(ctx: Context) -> dict[str, Any]:
    expected = ctx.cfg["source_r8r16"]
    stage = ctx.r8r16_run / str(expected["stage_directory"])
    paths = {
        "primary_detailed": stage / "analysis/primary_detailed.json",
        "primary_summary": stage / "analysis/primary_summary.json",
        "independent": stage / "analysis/independent.json",
        "final_report": stage / "analysis/final_report.json",
        "source_authentication": stage / "source_reference/r8r15_authentication.json",
        "stage_manifest": stage / "stage_manifest.json",
        "stage_state": stage / "stage_state.json",
    }
    hashes = {name: _sha(path) for name, path in paths.items()}
    if any(hashes[name] != str(expected[f"{name}_sha256"]) for name in hashes):
        raise ValueError("R8R17 source R8R16 hash changed")
    summary = _read(paths["primary_summary"])
    independent = _read(paths["independent"])
    final = _read(paths["final_report"])
    state = _read(paths["stage_state"])
    passed = bool(
        summary.get("route") == expected["required_route"]
        and summary.get("calibration_trajectory_count") == int(expected["calibration_trajectory_count"])
        and summary.get("calibration_pass_count") == int(expected["calibration_pass_count"])
        and summary.get("real_tsc_executed") is False
        and summary.get("new_raw_count") == 0
        and independent.get("passed") is True
        and independent.get("primary_agreement") is True
        and final.get("route") == expected["required_route"]
        and state.get("finished") is True
        and state.get("verdict", {}).get("route") == expected["required_route"]
    )
    result = {"stage": str(stage), "hashes": hashes, "route": final["route"], "passed": passed}
    _write(ctx.paths.source_reference / "r8r16_authentication.json", result)
    return result


def _authenticate_source(ctx: Context) -> dict[str, Any]:
    stage = _source_stage(ctx)
    expected = ctx.cfg["source_r8r15"]
    hashes = {
        "primary_detailed": _sha(stage / "analysis/primary_detailed.json"),
        "primary_summary": _sha(stage / "analysis/primary_summary.json"),
        "final_independent": _sha(stage / "analysis/final_independent.json"),
        "final_report": _sha(stage / "analysis/final_report.json"),
        "stage_manifest": _sha(stage / "stage_manifest.json"),
        "stage_state": _sha(stage / "stage_state.json"),
    }
    for name, digest in hashes.items():
        if digest != str(expected[f"{name}_sha256"]):
            raise ValueError(f"R8R17 source R8R15 {name} changed")
    state = _read(stage / "stage_state.json")
    final = _read(stage / "analysis/final_report.json")
    inventories = {}
    for phase in ("safety", "qualification"):
        inventory = r15.r8r7.r8._inventory(stage / "raw" / phase)
        inventories[phase] = {
            "count": int(inventory["count"]),
            "bytes": int(inventory["bytes"]),
            "digest": str(inventory["digest"]),
        }
        if inventories[phase] != {
            "count": int(expected[f"{phase}_raw_count"]),
            "bytes": int(expected[f"{phase}_raw_bytes"]),
            "digest": str(expected[f"{phase}_raw_digest"]),
        }:
            raise ValueError(f"R8R17 source R8R15 {phase} inventory changed")
    if (
        state.get("finished") is not True
        or state.get("new_raw_count") != 128
        or state.get("verdict", {}).get("route") != expected["required_route"]
        or final.get("route") != expected["required_route"]
        or final.get("scientific_gate_passed") is not False
    ):
        raise ValueError("R8R17 source R8R15 outcome changed")
    r12 = r15._authenticate_r8r12(ctx.r15_ctx)
    r14 = r15._authenticate_r8r14(ctx.r15_ctx)
    result = {
        "stage": str(stage),
        "hashes": hashes,
        "inventories": inventories,
        "source_r8r12_authenticated": bool(r12["passed"]),
        "source_r8r14_authenticated": bool(r14["passed"]),
        "route": final["route"],
        "passed": bool(r12["passed"] and r14["passed"]),
    }
    _write(ctx.paths.source_reference / "r8r15_authentication.json", result)
    return result


def _context_key(spec: Mapping[str, Any]) -> tuple[str, str]:
    return str(spec["pair_id"]), str(spec["history_member"])


def _collect(ctx: Context) -> tuple[list[dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    baseline_specs, baseline_results = r15._source_baselines(ctx.r15_ctx)
    u_specs, u_results = r15._source_r8r12_candidates(ctx.r15_ctx)
    v_specs, v_results = r15._source_r8r14_candidates(ctx.r15_ctx)
    new_specs = r15._saved_specs(ctx.r15_ctx)
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    for spec in baseline_specs:
        key = _context_key(spec)
        groups[key] = {
            "spec": copy.deepcopy(spec),
            "baseline": baseline_results[str(spec["experiment_id"])],
            "candidates": {},
        }
    for code, specs, results in (("UUUU", u_specs, u_results), ("VVVV", v_specs, v_results)):
        for spec in specs:
            groups[_context_key(spec)]["candidates"][code] = results[str(spec["experiment_id"])]
    stage = _source_stage(ctx)
    for spec in new_specs:
        code = str(spec["r8r15_sequence_code"])
        result = r15.r8r7.r8._read_gz(stage / "raw" / str(spec["partition"]) / f"{spec['experiment_id']}.json.gz")
        groups[_context_key(spec)]["candidates"][code] = result
    expected_codes = set((*ctx.cfg["code_contract"]["development_codes"], *ctx.cfg["code_contract"]["calibration_codes"]))
    if len(groups) != 16 or any(set(group["candidates"]) != expected_codes for group in groups.values()):
        raise ValueError("R8R17 measured context/code coverage changed")
    return baseline_specs, groups


def _response(result: Mapping[str, Any], baseline: Mapping[str, Any], first: int) -> np.ndarray:
    trajectory = result.get("trajectory") or []
    center = baseline.get("trajectory") or []
    if len(trajectory) != len(center) or len(trajectory) <= first:
        raise ValueError("R8R17 source trajectory horizon changed")
    values = np.asarray([[row[key] for key in COMPONENTS] for row in trajectory], dtype=float)
    base = np.asarray([[row[key] for key in COMPONENTS] for row in center], dtype=float)
    if not np.all(np.isfinite(values)) or not np.all(np.isfinite(base)):
        raise ValueError("R8R17 source trajectory is non-finite")
    return values[first:] - base[first:]


def fit_svd(codes: Sequence[str], responses: Sequence[np.ndarray], *, rcond: float) -> np.ndarray:
    x = design_matrix(codes)
    y = np.asarray(responses, dtype=float)
    if y.ndim != 3 or y.shape[0] != len(codes) or not np.all(np.isfinite(y)):
        raise ValueError("R8R17 response fit shape changed")
    u, singular, vt = np.linalg.svd(x, full_matrices=False)
    cutoff = rcond * singular[0]
    inverse = np.asarray([1.0 / value if value > cutoff else 0.0 for value in singular])
    pinv = (vt.T * inverse) @ u.T
    return (pinv @ y.reshape(len(codes), -1)).reshape(6, y.shape[1], y.shape[2])


def predict(coefficients: np.ndarray, code: str) -> np.ndarray:
    output = np.tensordot(code_row(code), np.asarray(coefficients, dtype=float), axes=(0, 0))
    if output.ndim != 2 or output.shape[1] != 3 or not np.all(np.isfinite(output)):
        raise ValueError("R8R17 predicted response is invalid")
    return output


def _predicted_result(baseline: Mapping[str, Any], response: np.ndarray, first: int) -> dict[str, Any]:
    result = copy.deepcopy(baseline)
    trajectory = result["trajectory"]
    if response.shape != (len(trajectory) - first, 3):
        raise ValueError("R8R17 predicted horizon changed")
    for offset, values in enumerate(response):
        row = trajectory[first + offset]
        for key, value in zip(COMPONENTS, values):
            row[key] = float(row[key]) + float(value)
    return result


def _formal(evaluator: Any, result: Mapping[str, Any]) -> dict[str, Any]:
    values = np.asarray([[row[key] for key in COMPONENTS] for row in result["trajectory"]], dtype=float)
    output = evaluator.evaluate(values)
    return {
        "formal_contract_pass": bool(output["formal_contract_pass"]),
        "formal_best_arrival_ms": int(output["formal_best_arrival_ms"]),
        "formal_minimum_signed_margin": float(output["formal_minimum_signed_margin"]),
        "formal_mean_signed_margin": float(output["formal_mean_signed_margin"]),
    }


def compute(ctx: Context) -> dict[str, Any]:
    source = _authenticate_source(ctx)
    r8r16_source = _authenticate_r8r16(ctx)
    baseline_specs, groups = _collect(ctx)
    evaluators, _ = r15.r8r7.r8.d1r11._formal_callback(ctx.r15_ctx.source_ctx.r8_ctx.d1r11_ctx, baseline_specs)
    evaluator_by_key = {_context_key(spec): evaluators[str(spec["experiment_id"])] for spec in baseline_specs}
    development, calibration, missing = _codes(ctx.cfg)
    first = int(ctx.cfg["model_contract"]["first_state_index"])
    rcond = float(ctx.cfg["model_contract"]["svd_rcond"])
    scales = np.asarray(ctx.cfg["calibration_gates"]["response_scales"], dtype=float)
    component_caps = np.asarray(ctx.cfg["calibration_gates"]["component_error_caps"], dtype=float)
    tube_caps = np.asarray(ctx.cfg["calibration_gates"]["tube_caps"], dtype=float)
    multiplier = float(ctx.cfg["calibration_gates"]["tube_multiplier"])
    calibration_rows: list[dict[str, Any]] = []
    residuals_by_relative_state: dict[int, list[np.ndarray]] = {}
    context_models: dict[tuple[str, str], dict[str, Any]] = {}
    for key in sorted(groups):
        group = groups[key]
        responses = {code: _response(result, group["baseline"], first) for code, result in group["candidates"].items()}
        coefficients = fit_svd(development, [responses[code] for code in development], rcond=rcond)
        context_models[key] = {"responses": responses, "development_coefficients": coefficients}
        evaluator = evaluator_by_key[key]
        for code in calibration:
            predicted = predict(coefficients, code)
            residual = predicted - responses[code]
            absolute = np.abs(residual)
            component_max = np.max(absolute, axis=0)
            scaled_max = float(np.max(absolute / scales))
            actual_formal = _formal(evaluator, group["candidates"][code])
            predicted_formal = _formal(evaluator, _predicted_result(group["baseline"], predicted, first))
            margin_error = abs(predicted_formal["formal_minimum_signed_margin"] - actual_formal["formal_minimum_signed_margin"])
            passed = bool(
                np.all(component_max <= component_caps)
                and scaled_max <= float(ctx.cfg["calibration_gates"]["maximum_scaled_point_error"])
                and predicted_formal["formal_contract_pass"] == actual_formal["formal_contract_pass"]
                and margin_error <= float(ctx.cfg["calibration_gates"]["maximum_minimum_margin_absolute_error"])
            )
            calibration_rows.append({
                "pair_id": key[0], "history_member": key[1], "sequence_code": code,
                "component_maximum_absolute_error": component_max.tolist(),
                "maximum_scaled_point_error": scaled_max,
                "actual_formal": actual_formal, "predicted_formal": predicted_formal,
                "minimum_margin_absolute_error": margin_error, "passed": passed,
            })
            for relative, row in enumerate(absolute):
                residuals_by_relative_state.setdefault(relative, []).append(row)
    tube_rows = []
    for relative, rows in sorted(residuals_by_relative_state.items()):
        half_width = multiplier * np.max(np.asarray(rows, dtype=float), axis=0)
        tube_rows.append({"relative_state": relative, "half_width": half_width.tolist(), "within_caps": bool(np.all(half_width <= tube_caps))})
    calibration_pass_count = sum(bool(row["passed"]) for row in calibration_rows)
    classification_count = sum(row["actual_formal"]["formal_contract_pass"] == row["predicted_formal"]["formal_contract_pass"] for row in calibration_rows)
    maximum_component_error = np.max(np.asarray([row["component_maximum_absolute_error"] for row in calibration_rows]), axis=0)
    maximum_scaled_error = max(float(row["maximum_scaled_point_error"]) for row in calibration_rows)
    maximum_margin_error = max(float(row["minimum_margin_absolute_error"]) for row in calibration_rows)
    tube_passed = all(row["within_caps"] for row in tube_rows)
    geometry = {
        "development_rank": int(np.linalg.matrix_rank(design_matrix(development))),
        "development_condition": float(np.linalg.cond(design_matrix(development))),
        "full_rank": int(np.linalg.matrix_rank(design_matrix((*development, *calibration)))),
        "full_condition": float(np.linalg.cond(design_matrix((*development, *calibration)))),
        "cube_rank": int(np.linalg.matrix_rank(design_matrix(sorted({"".join(row) for row in __import__("itertools").product("UV", repeat=4)})))),
        "cube_condition": float(np.linalg.cond(design_matrix(sorted({"".join(row) for row in __import__("itertools").product("UV", repeat=4)})))),
    }
    model_gate = bool(
        source["passed"]
        and r8r16_source["passed"]
        and geometry["development_rank"] == int(ctx.cfg["model_contract"]["required_rank"])
        and geometry["full_rank"] == int(ctx.cfg["model_contract"]["required_rank"])
        and geometry["development_condition"] <= float(ctx.cfg["model_contract"]["maximum_development_condition"])
        and geometry["full_condition"] <= float(ctx.cfg["model_contract"]["maximum_full_condition"])
        and geometry["cube_rank"] == int(ctx.cfg["model_contract"]["required_rank"])
        and geometry["cube_condition"] <= float(ctx.cfg["model_contract"]["maximum_cube_condition"])
        and calibration_pass_count == int(ctx.cfg["calibration_gates"]["required_trajectory_pass_count"])
        and classification_count == int(ctx.cfg["calibration_gates"]["required_formal_classification_count"])
        and tube_passed
    )
    missing_rows: list[dict[str, Any]] = []
    context_rows: list[dict[str, Any]] = []
    baseline_pass_count = 0
    robust_repairs = 0
    robust_oracle_pass = 0
    margin_buffer = multiplier * maximum_margin_error
    if model_gate:
        measured = (*development, *calibration)
        for key in sorted(groups):
            group = groups[key]
            model = context_models[key]
            coefficients = fit_svd(measured, [model["responses"][code] for code in measured], rcond=rcond)
            evaluator = evaluator_by_key[key]
            baseline_formal = _formal(evaluator, group["baseline"])
            baseline_pass_count += int(baseline_formal["formal_contract_pass"])
            candidates = []
            for code in missing:
                predicted = predict(coefficients, code)
                formal = _formal(evaluator, _predicted_result(group["baseline"], predicted, first))
                lower = float(formal["formal_minimum_signed_margin"]) - margin_buffer
                eligible = bool(formal["formal_contract_pass"] and lower > 0.0)
                row = {"pair_id": key[0], "history_member": key[1], "sequence_code": code, "predicted_formal": formal, "robust_lower_margin": lower, "robustly_eligible": eligible}
                missing_rows.append(row)
                candidates.append(row)
            best = max(candidates, key=lambda row: (float(row["robust_lower_margin"]), -missing.index(str(row["sequence_code"]))))
            repaired = bool(not baseline_formal["formal_contract_pass"] and any(row["robustly_eligible"] for row in candidates))
            oracle = bool(baseline_formal["formal_contract_pass"] or any(row["robustly_eligible"] for row in candidates))
            robust_repairs += int(repaired)
            robust_oracle_pass += int(oracle)
            context_rows.append({"pair_id": key[0], "history_member": key[1], "baseline_formal": baseline_formal, "best_missing": best, "robust_predicted_repair": repaired, "robust_predicted_oracle_pass": oracle})
    authority = ctx.cfg["authority_gate"]
    authority_gate = bool(
        model_gate
        and baseline_pass_count == int(authority["required_baseline_formal_pass_count"])
        and len(context_rows) - baseline_pass_count == int(authority["required_failed_baseline_count"])
        and robust_repairs >= int(authority["minimum_robust_predicted_repair_count"])
        and robust_oracle_pass >= int(authority["minimum_robust_predicted_oracle_pass_count"])
        and robust_oracle_pass > baseline_pass_count
    )
    if not model_gate:
        route = ctx.cfg["routes"]["model_fail"]
    elif not authority_gate:
        route = ctx.cfg["routes"]["authority_fail"]
    else:
        route = ctx.cfg["routes"]["pass"]
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "identity": IDENTITY,
        "source_authenticated": bool(source["passed"] and r8r16_source["passed"]),
        "geometry": geometry,
        "development_codes": list(development),
        "calibration_codes": list(calibration),
        "missing_codes": list(missing),
        "calibration_trajectory_count": len(calibration_rows),
        "calibration_pass_count": calibration_pass_count,
        "calibration_formal_classification_count": classification_count,
        "maximum_component_absolute_error": maximum_component_error.tolist(),
        "maximum_scaled_point_error": maximum_scaled_error,
        "maximum_minimum_margin_absolute_error": maximum_margin_error,
        "formal_margin_buffer": margin_buffer,
        "tube_passed": tube_passed,
        "tube_rows": tube_rows,
        "model_gate_passed": model_gate,
        "missing_prediction_count": len(missing_rows),
        "baseline_formal_pass_count": baseline_pass_count,
        "failed_baseline_count": len(context_rows) - baseline_pass_count,
        "robust_predicted_repair_count": robust_repairs,
        "robust_predicted_oracle_pass_count": robust_oracle_pass,
        "authority_gate_passed": authority_gate,
        "calibration_rows": calibration_rows,
        "missing_rows": missing_rows,
        "context_rows": context_rows,
        "route": route,
        "passed": authority_gate,
        "real_tsc_executed": False,
        "new_raw_count": 0,
    }


def _summary(detailed: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "schema_version", "stage", "identity", "source_authenticated", "geometry",
        "development_codes", "calibration_codes", "missing_codes",
        "calibration_trajectory_count", "calibration_pass_count",
        "calibration_formal_classification_count", "maximum_component_absolute_error",
        "maximum_scaled_point_error", "maximum_minimum_margin_absolute_error",
        "formal_margin_buffer", "tube_passed", "model_gate_passed",
        "missing_prediction_count", "baseline_formal_pass_count", "failed_baseline_count",
        "robust_predicted_repair_count", "robust_predicted_oracle_pass_count",
        "authority_gate_passed", "route", "passed", "real_tsc_executed", "new_raw_count",
    )
    return {key: copy.deepcopy(detailed[key]) for key in keys}


def run_primary(ctx: Context) -> dict[str, Any]:
    if ctx.paths.stage.exists() and any(ctx.paths.stage.iterdir()):
        raise ValueError("R8R17 output directory is not empty")
    ctx.paths.analysis.mkdir(parents=True, exist_ok=True)
    detailed = compute(ctx)
    summary = _summary(detailed)
    _write(ctx.paths.analysis / "primary_detailed.json", detailed)
    _write(ctx.paths.analysis / "primary_summary.json", summary)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "identity": IDENTITY,
        "config_path": str(ctx.config_path),
        "config_sha256": _sha(ctx.config_path),
        "design_document_sha256": ctx.cfg["design_document_sha256"],
        "source_r8r15_run": str(ctx.r8r15_run),
        "source_r8r16_run": str(ctx.r8r16_run),
        "source_authenticated": detailed["source_authenticated"],
        "real_tsc_executed": False,
        "new_raw_count": 0,
        "all_source_trajectories_allowed_in_expert_dataset": False,
    }
    _write(ctx.paths.manifest, manifest)
    state = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase_status": "primary_ready",
        "finished": False,
        "real_tsc_executed": False,
        "new_raw_count": 0,
        "primary_summary_sha256": _sha(ctx.paths.analysis / "primary_summary.json"),
        "verdict": {},
    }
    _write(ctx.paths.state, state)
    return summary


def postprocess(ctx: Context) -> dict[str, Any]:
    primary = _read(ctx.paths.analysis / "primary_summary.json")
    independent = _read(ctx.paths.analysis / "independent.json")
    if independent.get("passed") is not True or independent.get("primary_agreement") is not True:
        raise ValueError("R8R17 independent agreement failed")
    final = {
        **copy.deepcopy(primary),
        "phase": "final",
        "primary_detailed_sha256": _sha(ctx.paths.analysis / "primary_detailed.json"),
        "primary_summary_sha256": _sha(ctx.paths.analysis / "primary_summary.json"),
        "independent_sha256": _sha(ctx.paths.analysis / "independent.json"),
        "stage_manifest_sha256": _sha(ctx.paths.manifest),
    }
    _write(ctx.paths.analysis / "final_report.json", final)
    state = _read(ctx.paths.state)
    state.update({
        "phase_status": "complete", "finished": True,
        "stop_reason": "" if primary["passed"] else ("adjacent_switch_interaction_model_gate_failed" if not primary["model_gate_passed"] else "robust_predicted_authority_gate_failed"),
        "final_report_sha256": _sha(ctx.paths.analysis / "final_report.json"),
        "independent_sha256": _sha(ctx.paths.analysis / "independent.json"),
        "verdict": {"route": primary["route"], "passed": primary["passed"]},
    })
    _write(ctx.paths.state, state)
    return final


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--r8r15-run", type=Path, required=True)
    parser.add_argument("--r8r16-run", type=Path, required=True)
    parser.add_argument("--r8r7-run", type=Path, required=True)
    parser.add_argument("--r8r12-run", type=Path, required=True)
    parser.add_argument("--r8r14-run", type=Path, required=True)
    parser.add_argument("--r8-run", type=Path, required=True)
    parser.add_argument("--r8r1-output", type=Path, required=True)
    parser.add_argument("--r8r6-run", type=Path, required=True)
    for name in (
        "source-d1r11-run", "source-r2-run", "source-r4-run", "source-r6-run",
        "source-s21-run", "source-s23r1-output", "source-s24-run",
        "source-d1r9-v1", "source-d1r9-v2", "source-d1r10-run", "source-d1r10-audit",
        "source-stage42r3b-run", "source-stage42r3c3-run", "source-stage42r3c3-bank-dir",
        "source-stage42r3c3t1-run", "source-stage42r3c3t1-audit-dir",
        "source-stage42r3c3t3-controller-bank", "q1-run", "q2-run", "q1-audit",
        "q2-audit", "r3b-server-audit", "r3b-snapshot-checks",
    ):
        parser.add_argument(f"--{name}", dest=name.replace("-", "_"), type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--command", choices=("primary", "postprocess"), required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    ctx = load_context(args)
    result = run_primary(ctx) if args.command == "primary" else postprocess(ctx)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
