#!/usr/bin/env python3
"""Audit measured-current headroom after the failed T7 feasibility result."""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import importlib.util
import itertools
import json
import math
from collections import defaultdict
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.optimize import LinearConstraint, minimize

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t6_target_residual_new_direction_identification as t6,
)


STAGE = "Stage4.2R3c3T8"
IDENTITY = (
    "measured_current_constrained_target_direction_headroom_diagnostic_v1"
)
T7_MANIFEST = "stage4_2r3c3t7_manifest_v1.json"
T7_AUDIT = "stage4_2r3c3t7_audit_bank_v1.json"
T7_CONTROLLER = "stage4_2r3c3t7_controller_bank_v1.json"
T7_FEASIBILITY = "stage4_2r3c3t7_feasibility_v1.json"
T8_RESULT = "stage4_2r3c3t8_headroom_diagnostic_v1.json"
T8_MANIFEST = "stage4_2r3c3t8_manifest_v1.json"
R3C3_RAW = (
    "stage4_2r3c3_restart_task_clock_probe_identification/raw"
)
T2_RAW = "stage4_2r3c3t2_held_transport_identification/raw"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_digest(value: Any) -> str:
    text = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_gz(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def _load_module(path: Path, expected: str, name: str) -> ModuleType:
    resolved = path.expanduser().resolve()
    if not resolved.is_file() or _sha256(resolved) != expected:
        raise ValueError(f"{name} hash mismatch")
    spec = importlib.util.spec_from_file_location(name, resolved)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _inventory(paths: Sequence[Path], root: Path) -> dict[str, Any]:
    rows = [
        {
            "path": path.relative_to(root).as_posix(),
            "size_bytes": int(path.stat().st_size),
            "sha256": _sha256(path),
        }
        for path in sorted(paths)
    ]
    return {
        "n_files": len(rows),
        "total_bytes": sum(row["size_bytes"] for row in rows),
        "digest": _canonical_digest(rows),
        "files": rows,
    }


def _context_key(spec: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        str(spec["pair_id"]),
        str(spec["history_member"]),
        str(spec["target_id"]),
        int(spec["action_delay_steps"]),
        float(spec["slew_scale"]),
    )


def _audit_context_key(context: Mapping[str, Any]) -> tuple[Any, ...]:
    identity = context["audit_identity"]
    return (
        str(identity["pair_id"]),
        str(identity["history_member"]),
        str(identity["target_id"]),
        int(context["actual_delay_steps"]),
        float(context["actual_slew_scale"]),
    )


def _feasibility_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        str(row["pair_id"]),
        str(row["history_member"]),
        str(row["target_id"]),
        int(row["actual_delay_steps"]),
        float(row["actual_slew_scale"]),
    )


def _validate_design(cfg: Mapping[str, Any]) -> None:
    contract = cfg["diagnostic_contract"]
    scope = cfg["scientific_scope"]
    if (
        int(cfg.get("schema_version", -1)) != 1
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or len(cfg.get("selected_basis_ids", ())) != 8
        or int(contract["context_count"]) != 32
        or int(contract["baseline_formal_pass_count"]) != 16
        or int(contract["old_basis_count"]) != 5
        or contract["target_direction_basis_indices"] != [5, 6, 7]
        or float(contract["old_coefficient_lower_bound"]) != -1.0
        or float(contract["old_coefficient_upper_bound"]) != 1.0
        or list(
            map(
                float,
                contract["target_direction_common_scale_grid"],
            )
        )
        != [1.0, 1.25, 1.5, 2.0, 3.0, 4.0]
        or float(contract["maximum_predicted_current_utilization"])
        != 0.55
        or float(
            contract["maximum_midpoint_current_model_error_utilization"]
        )
        != 0.0013
        or not bool(contract["scale_one_must_exactly_reproduce_T7"])
        or bool(contract["formal_timing_changed"])
        or float(contract["position_tolerance_m"]) != 0.03
        or float(contract["speed_tolerance_m_per_s"]) != 0.1
        or not bool(scope["development_set_only"])
        or not bool(scope["optimistic_linear_superposition_only"])
        or not bool(scope["current_response_is_signed_pair_odd_component"])
        or bool(
            scope[
                "response_extrapolation_beyond_measured_amplitude_is_validation"
            ]
        )
        or bool(scope["real_tsc_executed"])
        or bool(scope["controller_implementation_authorized"])
        or bool(scope["real_tsc_controller_execution_authorized"])
        or bool(scope["probe_trajectories_are_demonstrations"])
        or bool(scope["bc_dagger_or_rl_allowed"])
    ):
        raise ValueError("T8 frozen design changed")


def _current_arrays(result: Mapping[str, Any]) -> np.ndarray:
    currents = np.asarray(
        [
            row["currents_a_display"]
            for row in result.get("trajectory") or []
        ],
        dtype=float,
    )
    if (
        currents.ndim != 2
        or currents.shape[1] != 14
        or not np.all(np.isfinite(currents))
    ):
        raise ValueError("invalid display-order current trajectory")
    return currents


def _current_odd_component(
    plus: np.ndarray,
    minus: np.ndarray,
    baseline: np.ndarray,
) -> tuple[np.ndarray, float]:
    plus = np.asarray(plus, dtype=float)
    minus = np.asarray(minus, dtype=float)
    baseline = np.asarray(baseline, dtype=float)
    if plus.shape != minus.shape or plus.shape != baseline.shape:
        raise ValueError("current signed-pair shape mismatch")
    odd = (plus - minus) / 2.0
    midpoint_error = float(
        np.max(np.abs((plus + minus) / 2.0 - baseline))
    )
    return odd, midpoint_error


def _current_utilization(
    currents: np.ndarray,
    minimum: np.ndarray,
    maximum: np.ndarray,
) -> float:
    currents = np.asarray(currents, dtype=float)
    minimum = np.asarray(minimum, dtype=float)
    maximum = np.asarray(maximum, dtype=float)
    center = 0.5 * (minimum + maximum)
    half = np.maximum(0.5 * (maximum - minimum), 1.0e-9)
    return float(
        np.max(np.abs((currents - center[None, :]) / half[None, :]))
    )


def _predict(
    baseline: np.ndarray,
    columns: Sequence[np.ndarray],
    coefficients: Sequence[float],
) -> np.ndarray:
    response = np.stack(columns, axis=2)
    return baseline + np.tensordot(
        response,
        np.asarray(coefficients, dtype=float),
        axes=(2, 0),
    )


def _optimize_context(
    evaluator: Any,
    baseline: np.ndarray,
    columns: Sequence[np.ndarray],
    baseline_current: np.ndarray,
    current_columns: Sequence[np.ndarray],
    minimum_current: np.ndarray,
    maximum_current: np.ndarray,
    *,
    target_scale: float,
    maximum_current_utilization: float,
    warm_starts: Sequence[Sequence[float]],
) -> dict[str, Any]:
    if len(columns) != 8 or len(current_columns) != 8:
        raise ValueError("T8 optimizer requires eight response columns")
    bounds = [(-1.0, 1.0)] * 5 + [
        (-target_scale, target_scale)
    ] * 3
    response = np.stack(columns, axis=2)
    current_response = np.stack(current_columns, axis=2)
    center = 0.5 * (minimum_current + maximum_current)
    half = np.maximum(
        0.5 * (maximum_current - minimum_current), 1.0e-9
    )
    normalized_baseline = (
        baseline_current - center[None, :]
    ) / half[None, :]
    normalized_response = current_response / half[None, :, None]
    matrix = normalized_response.reshape(-1, 8)
    base_vector = normalized_baseline.reshape(-1)
    current_constraint = LinearConstraint(
        matrix,
        -maximum_current_utilization - base_vector,
        maximum_current_utilization - base_vector,
    )

    def values(coefficients: np.ndarray) -> np.ndarray:
        return baseline + np.tensordot(
            response,
            np.asarray(coefficients, dtype=float),
            axes=(2, 0),
        )

    def currents(coefficients: np.ndarray) -> np.ndarray:
        return baseline_current + np.tensordot(
            current_response,
            np.asarray(coefficients, dtype=float),
            axes=(2, 0),
        )

    def feasible(coefficients: np.ndarray) -> bool:
        return bool(
            _current_utilization(
                currents(coefficients), minimum_current, maximum_current
            )
            <= maximum_current_utilization + 1.0e-10
        )

    zero = np.zeros(8, dtype=float)
    zero_margin, zero_row = evaluator.best(values(zero))
    if zero_margin >= -1.0e-12:
        return {
            "passed": True,
            "best_minimum_signed_margin": float(zero_margin),
            "best_endpoint_step": int(zero_row["endpoint_step"]),
            "best_coefficients": zero.tolist(),
            "active_constraint": str(zero_row["active_constraint"]),
            "predicted_max_current_utilization": _current_utilization(
                baseline_current, minimum_current, maximum_current
            ),
            "method": "exact_baseline_already_passes",
        }

    axis_values = [(-1.0, 0.0, 1.0)] * 5 + [
        (-target_scale, 0.0, target_scale)
    ] * 3
    grid_rows: list[tuple[float, np.ndarray, Mapping[str, Any]]] = []
    best = (zero_margin, zero, zero_row, "zero_baseline")
    for raw in itertools.product(*axis_values):
        coefficients = np.asarray(raw, dtype=float)
        if not feasible(coefficients):
            continue
        margin, row = evaluator.best(values(coefficients))
        grid_rows.append((margin, coefficients.copy(), row))
        if margin > best[0]:
            best = (
                margin,
                coefficients.copy(),
                row,
                "exhaustive_scaled_ternary_grid",
            )

    if best[0] < -1.0e-12:
        starts = sorted(
            grid_rows, key=lambda item: item[0], reverse=True
        )[:8]
        for raw in warm_starts:
            candidate = np.asarray(raw, dtype=float)
            if candidate.shape != (8,):
                continue
            candidate = np.asarray(
                [
                    np.clip(value, lower, upper)
                    for value, (lower, upper) in zip(candidate, bounds)
                ],
                dtype=float,
            )
            if feasible(candidate):
                margin, row = evaluator.best(values(candidate))
                starts.append((margin, candidate, row))
        starts.append((zero_margin, zero, zero_row))
        endpoints = [
            int(endpoint)
            for endpoint in evaluator.policy["allowed_arrival_steps"]
            if int(endpoint) <= evaluator.horizon
        ]
        for endpoint in endpoints:
            endpoint_starts = sorted(
                starts,
                key=lambda item: evaluator.endpoint_margin(
                    values(item[1]), endpoint
                )[0],
                reverse=True,
            )[:4]
            for _, start, _ in endpoint_starts:
                result = minimize(
                    lambda coefficients: -evaluator.endpoint_margin(
                        values(coefficients), endpoint
                    )[0],
                    np.asarray(start, dtype=float),
                    method="SLSQP",
                    bounds=bounds,
                    constraints=[current_constraint],
                    options={
                        "maxiter": 400,
                        "ftol": 1.0e-12,
                        "disp": False,
                    },
                )
                coefficients = np.asarray(
                    [
                        np.clip(value, lower, upper)
                        for value, (lower, upper) in zip(
                            result.x, bounds
                        )
                    ],
                    dtype=float,
                )
                if not feasible(coefficients):
                    continue
                margin, row = evaluator.best(values(coefficients))
                if margin > best[0]:
                    best = (
                        margin,
                        coefficients,
                        row,
                        "per_endpoint_current_constrained_multistart_slsqp",
                    )

    rounded = np.round(best[1], 12)
    predicted_current = currents(rounded)
    return {
        "passed": bool(best[0] >= -1.0e-12),
        "best_minimum_signed_margin": float(best[0]),
        "best_endpoint_step": int(best[2]["endpoint_step"]),
        "best_coefficients": rounded.tolist(),
        "active_constraint": str(best[2]["active_constraint"]),
        "predicted_max_current_utilization": _current_utilization(
            predicted_current, minimum_current, maximum_current
        ),
        "method": best[3],
    }


def _response_reference(
    response: Mapping[str, Any], side: str
) -> tuple[str, str]:
    value = response[f"{side}_file"]
    if isinstance(value, Mapping):
        return str(value["path"]), str(value["sha256"])
    return str(value), str(response[f"{side}_sha256"])


def _raw_lookup(directories: Sequence[Path]) -> dict[str, Path]:
    by_name: dict[str, list[Path]] = defaultdict(list)
    for directory in directories:
        if not directory.is_dir():
            raise ValueError(f"raw directory missing: {directory}")
        for path in directory.glob("*.json.gz"):
            by_name[path.name].append(path)
    duplicates = {
        name: paths for name, paths in by_name.items() if len(paths) != 1
    }
    if duplicates:
        raise ValueError(
            f"ambiguous cross-stage raw filenames: {sorted(duplicates)[:3]}"
        )
    return {name: paths[0] for name, paths in by_name.items()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--design-config", required=True, type=Path)
    parser.add_argument("--t6-config", required=True, type=Path)
    parser.add_argument("--t7-config", required=True, type=Path)
    parser.add_argument("--t7-result-dir", required=True, type=Path)
    parser.add_argument("--t6-run-dir", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3b-run", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3c3-run", required=True, type=Path)
    parser.add_argument(
        "--source-stage4-2r3c3-bank-dir", required=True, type=Path
    )
    parser.add_argument("--source-stage4-2r3c3t1-run", required=True, type=Path)
    parser.add_argument(
        "--source-stage4-2r3c3t1-audit-dir", required=True, type=Path
    )
    parser.add_argument("--source-stage4-2r3c3t2-run", required=True, type=Path)
    parser.add_argument(
        "--source-stage4-2r3c3t3-controller-bank",
        required=True,
        type=Path,
    )
    parser.add_argument("--frozen-t7-tool", required=True, type=Path)
    parser.add_argument(
        "--frozen-formal-evaluator", required=True, type=Path
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    output = args.output_dir.expanduser().resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite output directory: {output}")
    design_path = args.design_config.expanduser().resolve()
    cfg = _read_json(design_path)
    _validate_design(cfg)
    source = cfg["source_contract"]
    contract = cfg["diagnostic_contract"]

    t6_config = args.t6_config.expanduser().resolve()
    t7_config = args.t7_config.expanduser().resolve()
    if (
        _sha256(t6_config) != source["t6_config_sha256"]
        or _sha256(t7_config) != source["t7_config_sha256"]
        or _sha256(Path(t6.__file__).resolve())
        != source["t6_runtime_source_sha256"]
    ):
        raise ValueError("T8 installed config/runtime identity mismatch")
    _load_module(
        args.frozen_t7_tool,
        str(source["frozen_t7_tool_sha256"]),
        "frozen_t7_tool",
    )
    formal = _load_module(
        args.frozen_formal_evaluator,
        str(source["frozen_formal_evaluator_sha256"]),
        "frozen_formal_evaluator",
    )

    t7_dir = args.t7_result_dir.expanduser().resolve()
    t7_paths = {
        "t7_manifest_sha256": t7_dir / T7_MANIFEST,
        "t7_audit_bank_sha256": t7_dir / T7_AUDIT,
        "t7_controller_bank_sha256": t7_dir / T7_CONTROLLER,
        "t7_feasibility_sha256": t7_dir / T7_FEASIBILITY,
    }
    for field, path in t7_paths.items():
        if not path.is_file() or _sha256(path) != str(source[field]):
            raise ValueError(f"T8 authenticated T7 input mismatch: {field}")
    t7_manifest = _read_json(t7_paths["t7_manifest_sha256"])
    t7_audit = _read_json(t7_paths["t7_audit_bank_sha256"])
    t7_controller = _read_json(t7_paths["t7_controller_bank_sha256"])
    t7_feasibility = _read_json(t7_paths["t7_feasibility_sha256"])
    if (
        bool(t7_manifest["all_preregistered_gates_pass"])
        or int(t7_audit["basis_count"]) != 8
        or int(t7_audit["condition_audit"]["pass_count"]) != 32
        or int(t7_controller["basis_count"]) != 8
        or int(t7_feasibility["context_count"]) != 32
        or int(t7_feasibility["optimistic_formal_pass_count"]) != 16
        or int(t7_feasibility["failed_baseline_repair_count"]) != 0
        or bool(t7_feasibility["all_preregistered_gates_pass"])
        or bool(
            t7_feasibility["scientific_classification"][
                "next_restart_mpc_implementation_authorized"
            ]
        )
    ):
        raise ValueError("T8 T7 source outcome changed")

    t6_run = args.t6_run_dir.expanduser().resolve()
    ctx = t6.load_stage42r3c3t6_config(
        t6_config,
        source_stage42r3b_run=args.source_stage4_2r3b_run,
        source_stage42r3c3_run=args.source_stage4_2r3c3_run,
        source_stage42r3c3_bank_dir=args.source_stage4_2r3c3_bank_dir,
        source_stage42r3c3t1_run=args.source_stage4_2r3c3t1_run,
        source_stage42r3c3t1_audit_dir=(
            args.source_stage4_2r3c3t1_audit_dir
        ),
        source_stage42r3c3t3_controller_bank=(
            args.source_stage4_2r3c3t3_controller_bank
        ),
        run_dir_override=t6_run,
    )
    t6_raw_paths = sorted(ctx.paths.raw.glob("*.json.gz"))
    t6_inventory = _inventory(t6_raw_paths, ctx.paths.raw)
    if (
        t6_inventory != t7_audit["raw_inventory"]
        or int(t6_inventory["n_files"]) != int(source["t6_raw_count"])
        or t6_inventory["digest"] != source["t6_raw_inventory_digest"]
    ):
        raise ValueError("T8 T6 raw inventory mismatch")
    t6_results = [_read_json_gz(path) for path in t6_raw_paths]
    grouped: dict[
        tuple[Any, ...], dict[tuple[str, int], Mapping[str, Any]]
    ] = defaultdict(dict)
    for result in t6_results:
        spec = result["spec"]
        if (
            not bool(result.get("completed"))
            or not bool(result.get("success"))
            or bool(result.get("failure_reason"))
        ):
            raise ValueError("T8 encountered incomplete T6 raw")
        grouped[_context_key(spec)][
            (
                str(spec["r3c3_probe_id"]),
                int(spec["r3c3_probe_sign"]),
            )
        ] = result
    expected_labels = {(t6.BASELINE_PROBE_ID, 0)} | {
        (probe, sign) for probe in t6.PROBE_IDS for sign in (-1, 1)
    }
    if (
        len(grouped) != 32
        or any(set(members) != expected_labels for members in grouped.values())
    ):
        raise ValueError("T8 T6 context coverage mismatch")

    audit_by_key = {
        _audit_context_key(context): context
        for context in t7_audit["contexts"]
    }
    feasibility_by_key = {
        _feasibility_key(row): row
        for row in t7_feasibility["context_rows"]
    }
    if (
        set(audit_by_key) != set(grouped)
        or set(feasibility_by_key) != set(grouped)
    ):
        raise ValueError("T8 T7/T6 context-set mismatch")

    r3c3_raw = (
        args.source_stage4_2r3c3_run.expanduser().resolve() / R3C3_RAW
    )
    t2_raw = (
        args.source_stage4_2r3c3t2_run.expanduser().resolve() / T2_RAW
    )
    lookup = _raw_lookup((r3c3_raw, t2_raw, ctx.paths.raw))
    cache: dict[Path, dict[str, Any]] = {
        path: result for path, result in zip(t6_raw_paths, t6_results)
    }

    def load_response(
        response: Mapping[str, Any], side: str
    ) -> Mapping[str, Any]:
        name, expected_hash = _response_reference(response, side)
        path = lookup.get(name)
        if path is None or _sha256(path) != expected_hash:
            raise ValueError(f"T8 response raw mismatch: {name}")
        if path not in cache:
            cache[path] = _read_json_gz(path)
        result = cache[path]
        if (
            not bool(result.get("completed"))
            or not bool(result.get("success"))
            or bool(result.get("failure_reason"))
        ):
            raise ValueError(f"T8 response raw incomplete: {name}")
        return result

    scale_grid = list(
        map(float, contract["target_direction_common_scale_grid"])
    )
    maximum_current = float(
        contract["maximum_predicted_current_utilization"]
    )
    context_rows = []
    maximum_midpoint_error_a = 0.0
    maximum_midpoint_error_utilization = 0.0
    scale_one_maximum_margin_error = 0.0
    for key in sorted(grouped):
        baseline_result = grouped[key][(t6.BASELINE_PROBE_ID, 0)]
        horizon = t6._formal_horizon(float(key[4]))
        short_baseline = copy.deepcopy(baseline_result)
        short_baseline["trajectory"] = short_baseline["trajectory"][
            : horizon + 1
        ]
        baseline_y, _ = t6._arrays(short_baseline, 0.01)
        baseline_current = _current_arrays(short_baseline)
        evaluator = formal.FormalEvaluator(
            ctx.base_ctx.source_ctx, short_baseline
        )
        minimum_current = np.asarray(
            evaluator.metric_ctx.env_cfg["min_current_a_display_order"],
            dtype=float,
        )
        maximum_current_values = np.asarray(
            evaluator.metric_ctx.env_cfg["max_current_a_display_order"],
            dtype=float,
        )
        half_current = np.maximum(
            0.5 * (maximum_current_values - minimum_current), 1.0e-9
        )
        audit_context = audit_by_key[key]
        saved_baseline = np.asarray(
            audit_context["offline_design_only_baseline"]["RZI_by_state"],
            dtype=float,
        )
        if not np.array_equal(baseline_y, saved_baseline):
            raise ValueError(f"T8 baseline prefix mismatch: {key}")

        responses = sorted(
            audit_context["responses"],
            key=lambda row: int(row["basis_index"]),
        )
        if (
            len(responses) != 8
            or [int(row["basis_index"]) for row in responses]
            != list(range(8))
        ):
            raise ValueError(f"T8 selected response ordering mismatch: {key}")
        position_columns = []
        current_columns = []
        context_midpoint_error_a = 0.0
        context_midpoint_error_utilization = 0.0
        for response in responses:
            plus = load_response(response, "plus")
            minus = load_response(response, "minus")
            plus_y, _ = t6._arrays(plus, 0.01)
            minus_y, _ = t6._arrays(minus, 0.01)
            expected_y = ((plus_y - minus_y) / 2.0)[: horizon + 1]
            saved_y = np.asarray(
                response["delta_RZI_by_state"], dtype=float
            )
            if not np.array_equal(expected_y, saved_y):
                raise ValueError(f"T8 position response mismatch: {key}")
            plus_current = _current_arrays(plus)[: horizon + 1]
            minus_current = _current_arrays(minus)[: horizon + 1]
            odd_current, midpoint_error_a = _current_odd_component(
                plus_current, minus_current, baseline_current
            )
            midpoint_error_utilization = float(
                midpoint_error_a / float(np.min(half_current))
            )
            context_midpoint_error_a = max(
                context_midpoint_error_a, midpoint_error_a
            )
            context_midpoint_error_utilization = max(
                context_midpoint_error_utilization,
                midpoint_error_utilization,
            )
            position_columns.append(saved_y)
            current_columns.append(odd_current)

        maximum_midpoint_error_a = max(
            maximum_midpoint_error_a, context_midpoint_error_a
        )
        maximum_midpoint_error_utilization = max(
            maximum_midpoint_error_utilization,
            context_midpoint_error_utilization,
        )
        t7_row = feasibility_by_key[key]
        t7_coefficients = np.asarray(
            t7_row["best_coefficients"], dtype=float
        )
        reproduced_values = _predict(
            baseline_y, position_columns, t7_coefficients
        )
        reproduced_margin, reproduced_endpoint = evaluator.best(
            reproduced_values
        )
        margin_error = abs(
            reproduced_margin
            - float(t7_row["best_minimum_signed_margin"])
        )
        scale_one_maximum_margin_error = max(
            scale_one_maximum_margin_error, margin_error
        )
        if (
            margin_error > 1.0e-8
            or bool(reproduced_margin >= -1.0e-12)
            != bool(t7_row["passed"])
        ):
            raise ValueError(f"T8 exact T7 reproduction failed: {key}")
        reproduced_current = _predict(
            baseline_current, current_columns, t7_coefficients
        )
        scale_rows = [
            {
                "target_direction_scale": 1.0,
                "passed": bool(t7_row["passed"]),
                "best_minimum_signed_margin": float(
                    t7_row["best_minimum_signed_margin"]
                ),
                "best_endpoint_step": int(
                    t7_row["best_endpoint_step"]
                ),
                "best_coefficients": t7_coefficients.tolist(),
                "active_constraint": str(t7_row["active_constraint"]),
                "predicted_max_current_utilization": _current_utilization(
                    reproduced_current,
                    minimum_current,
                    maximum_current_values,
                ),
                "method": "authenticated_exact_T7_result",
            }
        ]
        warm_starts: list[Sequence[float]] = [t7_coefficients]
        for scale in scale_grid[1:]:
            optimized = _optimize_context(
                evaluator,
                baseline_y,
                position_columns,
                baseline_current,
                current_columns,
                minimum_current,
                maximum_current_values,
                target_scale=scale,
                maximum_current_utilization=maximum_current,
                warm_starts=warm_starts,
            )
            scale_rows.append(
                {
                    "target_direction_scale": scale,
                    **optimized,
                }
            )
            warm_starts.append(optimized["best_coefficients"])
        context_rows.append(
            {
                "pair_id": key[0],
                "history_member": key[1],
                "target_id": key[2],
                "actual_delay_steps": key[3],
                "actual_slew_scale": key[4],
                "saved_baseline_pass": bool(
                    t7_row["saved_baseline_pass"]
                ),
                "midpoint_current_model_error_A": (
                    context_midpoint_error_a
                ),
                "midpoint_current_model_error_utilization": (
                    context_midpoint_error_utilization
                ),
                "scale_rows": scale_rows,
            }
        )

    maximum_midpoint_allowed = float(
        contract["maximum_midpoint_current_model_error_utilization"]
    )
    if maximum_midpoint_error_utilization > maximum_midpoint_allowed:
        raise ValueError("T8 current midpoint model error exceeds contract")
    if scale_one_maximum_margin_error > 1.0e-8:
        raise ValueError("T8 T7 margin reproduction exceeds tolerance")

    scale_summaries = []
    for scale_index, scale in enumerate(scale_grid):
        rows = [
            context["scale_rows"][scale_index]
            for context in context_rows
        ]
        pass_count = sum(bool(row["passed"]) for row in rows)
        repair_count = sum(
            bool(row["passed"])
            and not bool(context["saved_baseline_pass"])
            for row, context in zip(rows, context_rows)
        )
        regressions = sum(
            not bool(row["passed"])
            and bool(context["saved_baseline_pass"])
            for row, context in zip(rows, context_rows)
        )
        scale_summaries.append(
            {
                "target_direction_scale": scale,
                "optimistic_formal_pass_count": pass_count,
                "failed_baseline_repair_count": repair_count,
                "baseline_pass_regression_count": regressions,
                "maximum_predicted_current_utilization": max(
                    float(row["predicted_max_current_utilization"])
                    for row in rows
                ),
                "current_constraint_pass_count": sum(
                    float(row["predicted_max_current_utilization"])
                    <= maximum_current + 1.0e-10
                    for row in rows
                ),
                "all_contexts_optimistically_pass": pass_count == 32,
            }
        )
    full_scales = [
        float(row["target_direction_scale"])
        for row in scale_summaries
        if bool(row["all_contexts_optimistically_pass"])
        and int(row["current_constraint_pass_count"]) == 32
    ]
    first_full_scale = min(full_scales) if full_scales else None
    route_exposed = bool(first_full_scale is not None)

    provenance = {
        "stage": STAGE,
        "identity": IDENTITY,
        "design_config_sha256": _sha256(design_path),
        **copy.deepcopy(source),
        "selected_basis_ids": copy.deepcopy(cfg["selected_basis_ids"]),
        "old_basis_bounds": [-1.0, 1.0],
        "target_direction_scale_grid": scale_grid,
        "maximum_predicted_current_utilization": maximum_current,
        "formal_timing_changed": False,
    }
    result = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "provenance": provenance,
        "provenance_digest": _canonical_digest(provenance),
        "context_count": len(context_rows),
        "scale_one_exact_T7_reproduction": {
            "passed": True,
            "maximum_absolute_margin_error": (
                scale_one_maximum_margin_error
            ),
            "optimistic_formal_pass_count": 16,
            "failed_baseline_repair_count": 0,
        },
        "current_model": {
            "signed_pair_response_count": len(context_rows) * 8,
            "maximum_midpoint_error_A": maximum_midpoint_error_a,
            "maximum_midpoint_error_utilization": (
                maximum_midpoint_error_utilization
            ),
            "maximum_allowed_midpoint_error_utilization": (
                maximum_midpoint_allowed
            ),
            "maximum_allowed_predicted_current_utilization": (
                maximum_current
            ),
            "passed": True,
        },
        "scale_summaries": scale_summaries,
        "first_full_optimistic_pass_scale": first_full_scale,
        "bounded_current_headroom_route_exposed": route_exposed,
        "measured_directions_insufficient_through_scale_four": (
            not route_exposed
        ),
        "context_rows": context_rows,
        "scientific_classification": {
            "real_tsc_executed_by_this_tool": False,
            "runtime_error": False,
            "statistics_or_reporting_error": False,
            "optimistic_linear_superposition_only": True,
            "response_above_scale_one_is_unvalidated_extrapolation": True,
            "candidate_combined_amplitude_identification_route_exposed": (
                route_exposed
            ),
            "controller_implementation_authorized": False,
            "real_tsc_controller_execution_authorized": False,
            "probe_trajectories_are_demonstrations": False,
            "bc_dagger_or_rl_allowed": False,
        },
    }
    output.mkdir(parents=True, exist_ok=False)
    result_path = output / T8_RESULT
    _write_json(result_path, result)
    manifest_path = output / T8_MANIFEST
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "provenance_digest": result["provenance_digest"],
        "outputs": [
            {
                "path": result_path.name,
                "size_bytes": int(result_path.stat().st_size),
                "sha256": _sha256(result_path),
            }
        ],
        "real_tsc_executed": False,
        "controller_implementation_authorized": False,
    }
    _write_json(manifest_path, manifest)
    print(
        json.dumps(
            {
                "output_dir": str(output),
                "manifest_sha256": _sha256(manifest_path),
                "result_sha256": _sha256(result_path),
                "context_count": len(context_rows),
                "first_full_optimistic_pass_scale": first_full_scale,
                "bounded_current_headroom_route_exposed": route_exposed,
                "real_tsc_executed": False,
                "controller_implementation_authorized": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
