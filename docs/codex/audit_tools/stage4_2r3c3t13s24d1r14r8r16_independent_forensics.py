#!/usr/bin/env python3
"""Structurally independent R8R16 temporal-affine completion audit."""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r15_binary_temporal_switching_staircase_authority_sentinel as r15,
)


STAGE = "Stage4.2R3c3T13S24D1R14R8R16"
IDENTITY = "temporal_affine_binary_cube_completion_preflight_v1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r16_temporal_affine_binary_cube_completion_preflight"
R15_RUN_NAME = "stage4_2r3c3t13s24d1r14r8r15_binary_temporal_switching_staircase_authority_sentinel"
COMPONENTS = ("R", "Z", "Ip")


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def _gzip(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(stream, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _row(code: str) -> np.ndarray:
    if len(code) != 4 or any(symbol not in "UV" for symbol in code):
        raise ValueError("independent R8R16 code changed")
    return np.asarray([1.0, *(1.0 if symbol == "U" else -1.0 for symbol in code)])


def _matrix(codes: Sequence[str]) -> np.ndarray:
    return np.asarray([_row(code) for code in codes], dtype=float)


def _fit(codes: Sequence[str], values: Sequence[np.ndarray]) -> np.ndarray:
    x = _matrix(codes)
    y = np.asarray(values, dtype=float)
    flat, _, rank, _ = np.linalg.lstsq(x, y.reshape(len(codes), -1), rcond=1e-12)
    if rank != 5 or not np.all(np.isfinite(flat)):
        raise ValueError("independent R8R16 fit changed")
    return flat.reshape(5, y.shape[1], y.shape[2])


def _predict(coefficients: np.ndarray, code: str) -> np.ndarray:
    return np.einsum("i,ijk->jk", _row(code), coefficients)


def _key(spec: Mapping[str, Any]) -> tuple[str, str]:
    return str(spec["pair_id"]), str(spec["history_member"])


def _response(result: Mapping[str, Any], baseline: Mapping[str, Any]) -> np.ndarray:
    values = np.asarray([[row[key] for key in COMPONENTS] for row in result["trajectory"]], dtype=float)
    center = np.asarray([[row[key] for key in COMPONENTS] for row in baseline["trajectory"]], dtype=float)
    if values.shape != center.shape or values.shape[0] <= 10 or not np.all(np.isfinite(values)) or not np.all(np.isfinite(center)):
        raise ValueError("independent R8R16 source trajectory changed")
    return values[10:] - center[10:]


def _prediction_result(baseline: Mapping[str, Any], delta: np.ndarray) -> dict[str, Any]:
    output = copy.deepcopy(baseline)
    if delta.shape != (len(output["trajectory"]) - 10, 3):
        raise ValueError("independent R8R16 predicted horizon changed")
    for offset, values in enumerate(delta):
        for component, value in zip(COMPONENTS, values):
            output["trajectory"][10 + offset][component] = float(output["trajectory"][10 + offset][component]) + float(value)
    return output


def _formal(evaluator: Any, result: Mapping[str, Any]) -> dict[str, Any]:
    values = np.asarray([[row[key] for key in COMPONENTS] for row in result["trajectory"]], dtype=float)
    outcome = evaluator.evaluate(values)
    return {
        "formal_contract_pass": bool(outcome["formal_contract_pass"]),
        "formal_best_arrival_ms": int(outcome["formal_best_arrival_ms"]),
        "formal_minimum_signed_margin": float(outcome["formal_minimum_signed_margin"]),
        "formal_mean_signed_margin": float(outcome["formal_mean_signed_margin"]),
    }


def _r15_context(args: argparse.Namespace, cfg: Mapping[str, Any]) -> r15.Context:
    forwarded = argparse.Namespace(**vars(args))
    forwarded.config = (_root() / str(cfg["source_r8r15_config"])).resolve()
    forwarded.run_dir = args.r8r15_run.expanduser().resolve()
    return r15.load_context(forwarded)


def _authenticate(args: argparse.Namespace, cfg: Mapping[str, Any], source_ctx: r15.Context) -> dict[str, Any]:
    stage = args.r8r15_run.expanduser().resolve() / R15_RUN_NAME
    expected = cfg["source_r8r15"]
    paths = {
        "primary_detailed": stage / "analysis/primary_detailed.json",
        "primary_summary": stage / "analysis/primary_summary.json",
        "final_independent": stage / "analysis/final_independent.json",
        "final_report": stage / "analysis/final_report.json",
        "stage_manifest": stage / "stage_manifest.json",
        "stage_state": stage / "stage_state.json",
    }
    hashes = {name: _sha(path) for name, path in paths.items()}
    if any(hashes[name] != str(expected[f"{name}_sha256"]) for name in hashes):
        raise ValueError("independent R8R16 source hash changed")
    for phase in ("safety", "qualification"):
        inventory = r15.r8r7.r8._inventory(stage / "raw" / phase)
        if (int(inventory["count"]), int(inventory["bytes"]), str(inventory["digest"])) != (
            int(expected[f"{phase}_raw_count"]), int(expected[f"{phase}_raw_bytes"]), str(expected[f"{phase}_raw_digest"])
        ):
            raise ValueError("independent R8R16 source inventory changed")
    final = _read(paths["final_report"])
    state = _read(paths["stage_state"])
    r12 = r15._authenticate_r8r12(source_ctx)
    r14 = r15._authenticate_r8r14(source_ctx)
    passed = bool(
        final.get("route") == expected["required_route"]
        and final.get("scientific_gate_passed") is False
        and state.get("finished") is True
        and state.get("new_raw_count") == 128
        and r12["passed"] and r14["passed"]
    )
    return {"hashes": hashes, "passed": passed}


def _collect(args: argparse.Namespace, cfg: Mapping[str, Any], source_ctx: r15.Context) -> tuple[list[dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    baseline_specs, baseline_results = r15._source_baselines(source_ctx)
    u_specs, u_results = r15._source_r8r12_candidates(source_ctx)
    v_specs, v_results = r15._source_r8r14_candidates(source_ctx)
    all_specs = _read(args.r8r15_run.expanduser().resolve() / R15_RUN_NAME / "specs/all_specs.json")
    groups = {_key(spec): {"baseline": baseline_results[str(spec["experiment_id"])], "candidates": {}} for spec in baseline_specs}
    for code, specs, results in (("UUUU", u_specs, u_results), ("VVVV", v_specs, v_results)):
        for spec in specs:
            groups[_key(spec)]["candidates"][code] = results[str(spec["experiment_id"])]
    stage = args.r8r15_run.expanduser().resolve() / R15_RUN_NAME
    for spec in all_specs:
        groups[_key(spec)]["candidates"][str(spec["r8r15_sequence_code"])] = _gzip(stage / "raw" / str(spec["partition"]) / f"{spec['experiment_id']}.json.gz")
    measured = set((*cfg["code_contract"]["development_codes"], *cfg["code_contract"]["calibration_codes"]))
    if len(groups) != 16 or any(set(group["candidates"]) != measured for group in groups.values()):
        raise ValueError("independent R8R16 measured coverage changed")
    return baseline_specs, groups


def recompute(args: argparse.Namespace, cfg: Mapping[str, Any]) -> dict[str, Any]:
    design = _root() / str(cfg["design_document"])
    source_config = _root() / str(cfg["source_r8r15_config"])
    if (
        cfg.get("stage") != STAGE or cfg.get("identity") != IDENTITY
        or _sha(design) != str(cfg["design_document_sha256"])
        or _sha(source_config) != str(cfg["source_r8r15_config_sha256"])
    ):
        raise ValueError("independent R8R16 frozen design changed")
    development = tuple(map(str, cfg["code_contract"]["development_codes"]))
    calibration = tuple(map(str, cfg["code_contract"]["calibration_codes"]))
    missing = tuple(map(str, cfg["code_contract"]["missing_codes"]))
    source_ctx = _r15_context(args, cfg)
    source = _authenticate(args, cfg, source_ctx)
    baseline_specs, groups = _collect(args, cfg, source_ctx)
    evaluators, _ = r15.r8r7.r8.d1r11._formal_callback(source_ctx.source_ctx.r8_ctx.d1r11_ctx, baseline_specs)
    evaluator_by_key = {_key(spec): evaluators[str(spec["experiment_id"])] for spec in baseline_specs}
    scales = np.asarray(cfg["calibration_gates"]["response_scales"], dtype=float)
    caps = np.asarray(cfg["calibration_gates"]["component_error_caps"], dtype=float)
    tube_caps = np.asarray(cfg["calibration_gates"]["tube_caps"], dtype=float)
    multiplier = float(cfg["calibration_gates"]["tube_multiplier"])
    calibration_rows = []
    residuals: dict[int, list[np.ndarray]] = {}
    models = {}
    for key in sorted(groups):
        group = groups[key]
        responses = {code: _response(result, group["baseline"]) for code, result in group["candidates"].items()}
        coefficients = _fit(development, [responses[code] for code in development])
        models[key] = (responses, coefficients)
        for code in calibration:
            estimate = _predict(coefficients, code)
            error = np.abs(estimate - responses[code])
            component = np.max(error, axis=0)
            scaled = float(np.max(error / scales))
            actual = _formal(evaluator_by_key[key], group["candidates"][code])
            predicted = _formal(evaluator_by_key[key], _prediction_result(group["baseline"], estimate))
            margin_error = abs(float(predicted["formal_minimum_signed_margin"]) - float(actual["formal_minimum_signed_margin"]))
            passed = bool(
                np.all(component <= caps)
                and scaled <= float(cfg["calibration_gates"]["maximum_scaled_point_error"])
                and actual["formal_contract_pass"] == predicted["formal_contract_pass"]
                and margin_error <= float(cfg["calibration_gates"]["maximum_minimum_margin_absolute_error"])
            )
            calibration_rows.append({"component": component, "scaled": scaled, "actual": actual, "predicted": predicted, "margin_error": margin_error, "passed": passed})
            for relative, row in enumerate(error):
                residuals.setdefault(relative, []).append(row)
    tube_passed = all(np.all(multiplier * np.max(np.asarray(rows), axis=0) <= tube_caps) for rows in residuals.values())
    pass_count = sum(bool(row["passed"]) for row in calibration_rows)
    classification_count = sum(row["actual"]["formal_contract_pass"] == row["predicted"]["formal_contract_pass"] for row in calibration_rows)
    maximum_component = np.max(np.asarray([row["component"] for row in calibration_rows]), axis=0)
    maximum_scaled = max(float(row["scaled"]) for row in calibration_rows)
    maximum_margin = max(float(row["margin_error"]) for row in calibration_rows)
    geometry = {
        "development_rank": int(np.linalg.matrix_rank(_matrix(development))),
        "development_condition": float(np.linalg.cond(_matrix(development))),
        "full_rank": int(np.linalg.matrix_rank(_matrix((*development, *calibration)))),
        "full_condition": float(np.linalg.cond(_matrix((*development, *calibration)))),
    }
    model_gate = bool(
        source["passed"]
        and geometry["development_rank"] == 5 and geometry["full_rank"] == 5
        and geometry["development_condition"] <= float(cfg["model_contract"]["maximum_development_condition"])
        and geometry["full_condition"] <= float(cfg["model_contract"]["maximum_full_condition"])
        and pass_count == int(cfg["calibration_gates"]["required_trajectory_pass_count"])
        and classification_count == int(cfg["calibration_gates"]["required_formal_classification_count"])
        and tube_passed
    )
    buffer = multiplier * maximum_margin
    baseline_pass = repairs = oracle_pass = predictions = 0
    if model_gate:
        measured = (*development, *calibration)
        for key in sorted(groups):
            group = groups[key]
            responses, _ = models[key]
            coefficients = _fit(measured, [responses[code] for code in measured])
            baseline = _formal(evaluator_by_key[key], group["baseline"])
            baseline_pass += int(baseline["formal_contract_pass"])
            eligible = []
            for code in missing:
                formal = _formal(evaluator_by_key[key], _prediction_result(group["baseline"], _predict(coefficients, code)))
                eligible.append(bool(formal["formal_contract_pass"] and float(formal["formal_minimum_signed_margin"]) - buffer > 0.0))
                predictions += 1
            repairs += int(not baseline["formal_contract_pass"] and any(eligible))
            oracle_pass += int(baseline["formal_contract_pass"] or any(eligible))
    authority = cfg["authority_gate"]
    authority_gate = bool(
        model_gate and baseline_pass == int(authority["required_baseline_formal_pass_count"])
        and 16 - baseline_pass == int(authority["required_failed_baseline_count"])
        and repairs >= int(authority["minimum_robust_predicted_repair_count"])
        and oracle_pass >= int(authority["minimum_robust_predicted_oracle_pass_count"])
        and oracle_pass > baseline_pass
    )
    route = cfg["routes"]["model_fail"] if not model_gate else (cfg["routes"]["pass"] if authority_gate else cfg["routes"]["authority_fail"])
    return {
        "schema_version": 1, "stage": STAGE, "identity": IDENTITY,
        "source_authenticated": bool(source["passed"]), "geometry": geometry,
        "development_codes": list(development), "calibration_codes": list(calibration), "missing_codes": list(missing),
        "calibration_trajectory_count": len(calibration_rows), "calibration_pass_count": pass_count,
        "calibration_formal_classification_count": classification_count,
        "maximum_component_absolute_error": maximum_component.tolist(),
        "maximum_scaled_point_error": maximum_scaled,
        "maximum_minimum_margin_absolute_error": maximum_margin,
        "formal_margin_buffer": buffer, "tube_passed": tube_passed,
        "model_gate_passed": model_gate, "missing_prediction_count": predictions,
        "baseline_formal_pass_count": baseline_pass, "failed_baseline_count": 16 - baseline_pass if model_gate else 0,
        "robust_predicted_repair_count": repairs, "robust_predicted_oracle_pass_count": oracle_pass,
        "authority_gate_passed": authority_gate, "route": route, "passed": authority_gate,
        "real_tsc_executed": False, "new_raw_count": 0,
    }


def _compare(left: Any, right: Any, *, atol: float, rtol: float) -> tuple[bool, float]:
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        if set(left) != set(right):
            return False, math.inf
        results = [_compare(left[key], right[key], atol=atol, rtol=rtol) for key in left]
        return all(row[0] for row in results), max((row[1] for row in results), default=0.0)
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return False, math.inf
        results = [_compare(a, b, atol=atol, rtol=rtol) for a, b in zip(left, right)]
        return all(row[0] for row in results), max((row[1] for row in results), default=0.0)
    if isinstance(left, bool) or isinstance(right, bool) or isinstance(left, str) or isinstance(right, str) or left is None or right is None:
        return left == right, 0.0 if left == right else math.inf
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        difference = abs(float(left) - float(right))
        return math.isclose(float(left), float(right), abs_tol=atol, rel_tol=rtol), difference
    return left == right, 0.0 if left == right else math.inf


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--r8r15-run", type=Path, required=True)
    parser.add_argument("--r8r7-run", type=Path, required=True)
    parser.add_argument("--r8r12-run", type=Path, required=True)
    parser.add_argument("--r8r14-run", type=Path, required=True)
    parser.add_argument("--r8-run", type=Path, required=True)
    parser.add_argument("--r8r1-output", type=Path, required=True)
    parser.add_argument("--r8r6-run", type=Path, required=True)
    for name in (
        "source-d1r11-run", "source-r2-run", "source-r4-run", "source-r6-run", "source-s21-run",
        "source-s23r1-output", "source-s24-run", "source-d1r9-v1", "source-d1r9-v2", "source-d1r10-run",
        "source-d1r10-audit", "source-stage42r3b-run", "source-stage42r3c3-run", "source-stage42r3c3-bank-dir",
        "source-stage42r3c3t1-run", "source-stage42r3c3t1-audit-dir", "source-stage42r3c3t3-controller-bank",
        "q1-run", "q2-run", "q1-audit", "q2-audit", "r3b-server-audit", "r3b-snapshot-checks",
    ):
        parser.add_argument(f"--{name}", dest=name.replace("-", "_"), type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    cfg = _read(args.config.expanduser().resolve())
    primary_path = args.run_dir.expanduser().resolve() / RUN_NAME / "analysis/primary_summary.json"
    primary = _read(primary_path)
    audited = recompute(args, cfg)
    agreement, maximum = _compare(primary, audited, atol=float(cfg["calibration_gates"]["independent_absolute_tolerance"]), rtol=float(cfg["calibration_gates"]["independent_relative_tolerance"]))
    result = {
        "schema_version": 1, "stage": STAGE, "audit_kind": "independent",
        **audited,
        "primary_agreement": bool(agreement),
        "maximum_primary_numerical_difference": maximum,
        "primary_route_agreement": primary.get("route") == audited["route"],
        "primary_outcome_agreement": primary.get("passed") == audited["passed"],
        "primary_sha256": _sha(primary_path),
        "primary_scientific_gate_passed": bool(audited["authority_gate_passed"]),
        "passed": bool(agreement),
    }
    _write(args.run_dir.expanduser().resolve() / RUN_NAME / "analysis/independent.json", result)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
