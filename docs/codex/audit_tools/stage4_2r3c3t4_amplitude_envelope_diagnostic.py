#!/usr/bin/env python3
"""Diagnose unvalidated amplitude requirements of the failed T3 bank."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import itertools
import json
import math
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.optimize import minimize

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t2_post_contract_neutralized_held_transport_identification
    as t2,
)


EXPECTED_T3_AUDIT_TOOL_SHA256 = (
    "e3c067574ebcb98dc6f30d4e29a41521c38368862fa23f01c0714e8d28dac093"
)
EXPECTED_FROZEN_FORMAL_EVALUATOR_SHA256 = (
    "7b7b3d15b770efaa9a6d648aa69e4dfb35dbdb596c34dc8d6e38fdfba65f31b2"
)
EXPECTED_T3_MANIFEST_SHA256 = (
    "2c9389af0ea8d0f9538a0e4af34e604331981e77cfc0bc9c5bf353617c541b09"
)
EXPECTED_T3_AUDIT_BANK_SHA256 = (
    "f6cf5ae8642b68fc9947eaa1c2a3d18074e4e3e5be1f422f50ffa03f1a1a1970"
)
EXPECTED_T3_CONTROLLER_BANK_SHA256 = (
    "6328ef4116ea5a2ecac66d04583fb92af7830ad5ff6ea484486524cbd2021e86"
)
EXPECTED_T3_FEASIBILITY_SHA256 = (
    "08c253f7e8b66165704ec22e7b56c7e5c1abb1a30b8738be8b1d240211729744"
)
EXPECTED_T3_PROVENANCE_DIGEST = (
    "a536183fc8e192fafc8c28bdc9897ecf3acb5dc9f0c5ed6257f236e2e8c03935"
)
EXPECTED_T1_RAW_DIGEST = (
    "f19a04dcb6b597e97517482d602a6cfdb3c0a1f0b4bfd7a1507b90ae2cc0876f"
)
EXPECTED_T2_RAW_DIGEST = (
    "e40dbf9b531886344bd97a18590db342897570ec8f21b18a37d16c4fb528c90f"
)
EXPECTED_BASELINE_DIGEST = (
    "3e82504dde79215ed34626531e4f926f5bd65404832790cba6a2eb2f2cc3a97e"
)
AMPLITUDE_SCALES = (1.25, 1.5, 2.0)
PROFILE_NAMES = ("transport_only", "uniform_all")
MAXIMUM_CONDITION = 25.0


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


def _load_exact_module(
    path: Path, *, expected_sha256: str, name: str
) -> ModuleType:
    resolved = path.expanduser().resolve()
    if not resolved.is_file() or _sha256(resolved) != expected_sha256:
        raise ValueError(f"{name} hash mismatch")
    spec = importlib.util.spec_from_file_location(name, resolved)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _audit_key(context: Mapping[str, Any]) -> tuple[Any, ...]:
    identity = context["audit_identity"]
    return (
        str(identity["pair_id"]),
        str(identity["history_member"]),
        str(identity["target_id"]),
        int(context["actual_delay_steps"]),
        float(context["actual_slew_scale"]),
    )


def _row_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        str(row["pair_id"]),
        str(row["history_member"]),
        str(row["target_id"]),
        int(row["actual_delay_steps"]),
        float(row["actual_slew_scale"]),
    )


def _condition_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    context = row["context"]
    return (
        str(context[0]),
        str(context[1]),
        str(context[2]),
        int(context[3]),
        float(context[4]),
    )


def _bounds_for_profile(
    profile_name: str, amplitude_scale: float
) -> tuple[float, ...]:
    scale = float(amplitude_scale)
    if scale <= 1.0:
        raise ValueError("diagnostic amplitude scale must exceed one")
    if profile_name == "transport_only":
        return (1.0, 1.0, 1.0, 1.0, scale, scale, scale, scale)
    if profile_name == "uniform_all":
        return (scale,) * 8
    raise ValueError(f"unknown amplitude profile: {profile_name}")


def _deduplicate_starts(starts: Sequence[np.ndarray]) -> list[np.ndarray]:
    unique: list[np.ndarray] = []
    seen: set[tuple[float, ...]] = set()
    for start in starts:
        key = tuple(np.round(np.asarray(start, dtype=float), 12))
        if key not in seen:
            seen.add(key)
            unique.append(np.asarray(start, dtype=float))
    return unique


def _optimize_context_bounds(
    evaluator: Any,
    baseline: np.ndarray,
    columns: Sequence[np.ndarray],
    *,
    bounds: Sequence[float],
    t3_seed: Sequence[float],
) -> dict[str, Any]:
    if len(columns) != 8 or len(bounds) != 8 or len(t3_seed) != 8:
        raise ValueError("amplitude-envelope optimizer requires eight bases")
    upper = np.asarray(bounds, dtype=float)
    if np.any(upper <= 1.0 - 1.0e-15):
        raise ValueError("diagnostic bounds may not contract T3 authority")
    response = np.stack(columns, axis=2)

    def values(coefficients: np.ndarray) -> np.ndarray:
        return baseline + np.tensordot(
            response,
            np.asarray(coefficients, dtype=float),
            axes=(2, 0),
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
            "method": "exact_baseline_already_passes",
        }

    grid = np.asarray(
        list(
            itertools.product(
                *[(-bound, 0.0, bound) for bound in upper]
            )
        ),
        dtype=float,
    )
    endpoint_values = [
        int(endpoint)
        for endpoint in evaluator.policy["allowed_arrival_steps"]
        if int(endpoint) <= evaluator.horizon
    ]
    grid_rows = []
    best = (zero_margin, zero, zero_row, "zero_baseline")
    for coefficients in grid:
        margin, row = evaluator.best(values(coefficients))
        grid_rows.append((margin, coefficients.copy(), row))
        if margin > best[0]:
            best = (
                margin,
                coefficients.copy(),
                row,
                "exhaustive_scaled_ternary_grid",
            )

    global_grid_starts = [
        row[1]
        for row in sorted(
            grid_rows, key=lambda item: item[0], reverse=True
        )[:12]
    ]
    saved = np.clip(np.asarray(t3_seed, dtype=float), -upper, upper)
    scaled_saved = np.clip(saved * upper, -upper, upper)
    starts = _deduplicate_starts(
        [*global_grid_starts, zero, saved, scaled_saved]
    )
    scipy_bounds = [(-float(bound), float(bound)) for bound in upper]
    for endpoint in endpoint_values:
        endpoint_starts = sorted(
            starts,
            key=lambda start: evaluator.endpoint_margin(
                values(start), endpoint
            )[0],
            reverse=True,
        )[:6]
        for start in endpoint_starts:
            result = minimize(
                lambda coefficients: -evaluator.endpoint_margin(
                    values(coefficients), endpoint
                )[0],
                np.asarray(start, dtype=float),
                method="SLSQP",
                bounds=scipy_bounds,
                options={
                    "maxiter": 400,
                    "ftol": 1.0e-12,
                    "disp": False,
                },
            )
            coefficients = np.clip(
                np.asarray(result.x, dtype=float), -upper, upper
            )
            margin, row = evaluator.best(values(coefficients))
            if margin > best[0]:
                best = (
                    margin,
                    coefficients,
                    row,
                    "per_endpoint_scaled_multistart_slsqp",
                )
    return {
        "passed": bool(best[0] >= -1.0e-12),
        "best_minimum_signed_margin": float(best[0]),
        "best_endpoint_step": int(best[2]["endpoint_step"]),
        "best_coefficients": np.round(best[1], 12).tolist(),
        "active_constraint": str(best[2]["active_constraint"]),
        "method": best[3],
    }


def _profile_id(profile_name: str, scale: float) -> str:
    scale_text = f"{float(scale):.2f}".replace(".", "p")
    return f"{profile_name}_x{scale_text}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3b-run", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3c3-run", required=True, type=Path)
    parser.add_argument(
        "--source-stage4-2r3c3-bank-dir", required=True, type=Path
    )
    parser.add_argument("--source-stage4-2r3c3t1-run", required=True, type=Path)
    parser.add_argument(
        "--source-stage4-2r3c3t1-audit-dir", required=True, type=Path
    )
    parser.add_argument("--t2-run-dir", required=True, type=Path)
    parser.add_argument("--t3-result-dir", required=True, type=Path)
    parser.add_argument("--frozen-t3-audit", required=True, type=Path)
    parser.add_argument(
        "--frozen-formal-evaluator", required=True, type=Path
    )
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    output = args.output.expanduser().resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite output: {output}")
    if (
        not args.frozen_t3_audit.expanduser().resolve().is_file()
        or _sha256(args.frozen_t3_audit.expanduser().resolve())
        != EXPECTED_T3_AUDIT_TOOL_SHA256
    ):
        raise ValueError("frozen T3 audit tool hash mismatch")
    frozen = _load_exact_module(
        args.frozen_formal_evaluator,
        expected_sha256=EXPECTED_FROZEN_FORMAL_EVALUATOR_SHA256,
        name="frozen_t1_formal_evaluator",
    )

    result_dir = args.t3_result_dir.expanduser().resolve()
    paths = {
        "manifest": (
            result_dir / "stage4_2r3c3t3_eight_basis_manifest_v1.json"
        ),
        "audit_bank": (
            result_dir / "stage4_2r3c3t3_eight_basis_audit_bank_v1.json"
        ),
        "controller_bank": (
            result_dir
            / "stage4_2r3c3t3_eight_basis_controller_bank_v1.json"
        ),
        "feasibility": (
            result_dir / "stage4_2r3c3t3_eight_basis_feasibility_v1.json"
        ),
    }
    expected_hashes = {
        "manifest": EXPECTED_T3_MANIFEST_SHA256,
        "audit_bank": EXPECTED_T3_AUDIT_BANK_SHA256,
        "controller_bank": EXPECTED_T3_CONTROLLER_BANK_SHA256,
        "feasibility": EXPECTED_T3_FEASIBILITY_SHA256,
    }
    for name, path in paths.items():
        if not path.is_file() or _sha256(path) != expected_hashes[name]:
            raise ValueError(f"authenticated T3 {name} mismatch")
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    audit_bank = json.loads(
        paths["audit_bank"].read_text(encoding="utf-8")
    )
    controller_bank = json.loads(
        paths["controller_bank"].read_text(encoding="utf-8")
    )
    feasibility = json.loads(
        paths["feasibility"].read_text(encoding="utf-8")
    )
    manifest_inventory = {
        str(row["path"]): (int(row["size_bytes"]), str(row["sha256"]))
        for row in manifest["outputs"]
    }
    expected_inventory = {
        paths[name].name: (
            paths[name].stat().st_size,
            expected_hashes[name],
        )
        for name in ("audit_bank", "controller_bank", "feasibility")
    }
    if manifest_inventory != expected_inventory:
        raise ValueError("T3 manifest inventory mismatch")
    provenance = audit_bank["provenance_contract"]
    if (
        str(manifest["provenance_digest"])
        != EXPECTED_T3_PROVENANCE_DIGEST
        or str(audit_bank["provenance_digest"])
        != EXPECTED_T3_PROVENANCE_DIGEST
        or str(controller_bank["provenance_digest"])
        != EXPECTED_T3_PROVENANCE_DIGEST
        or str(feasibility["provenance_digest"])
        != EXPECTED_T3_PROVENANCE_DIGEST
        or provenance["t1_raw_inventory_digest"]
        != EXPECTED_T1_RAW_DIGEST
        or provenance["t2_raw_inventory_digest"]
        != EXPECTED_T2_RAW_DIGEST
        or provenance["r3c1_baseline_inventory_digest"]
        != EXPECTED_BASELINE_DIGEST
        or int(audit_bank["basis_count"]) != 8
        or int(controller_bank["basis_count"]) != 8
        or bool(manifest["all_preregistered_gates_pass"])
        or bool(feasibility["all_preregistered_gates_pass"])
        or int(feasibility["optimistic_formal_pass_count"]) != 16
        or int(feasibility["failed_baseline_repair_count"]) != 0
        or int(feasibility["eight_basis_condition_pass_count"]) != 11
    ):
        raise ValueError("T3 identity or failed outcome changed")

    t2_run = args.t2_run_dir.expanduser().resolve()
    ctx = t2.load_stage42r3c3t2_config(
        args.config,
        source_stage42r3b_run=args.source_stage4_2r3b_run,
        source_stage42r3c3_run=args.source_stage4_2r3c3_run,
        source_stage42r3c3_bank_dir=args.source_stage4_2r3c3_bank_dir,
        source_stage42r3c3t1_run=args.source_stage4_2r3c3t1_run,
        source_stage42r3c3t1_audit_dir=(
            args.source_stage4_2r3c3t1_audit_dir
        ),
        run_dir_override=t2_run,
    )
    audit_by_key = {
        _audit_key(context): context for context in audit_bank["contexts"]
    }
    t3_by_key = {
        _row_key(row): row for row in feasibility["context_rows"]
    }
    condition_by_key = {
        _condition_key(row): row
        for row in audit_bank["eight_basis_condition_audit"]["rows"]
    }
    if (
        len(audit_by_key) != 32
        or set(audit_by_key) != set(t3_by_key)
        or set(audit_by_key) != set(condition_by_key)
    ):
        raise ValueError("T3 context mapping mismatch")

    contexts = []
    reproduction_rows = []
    for key in sorted(audit_by_key):
        source = audit_by_key[key]
        baseline_file = source["baseline_file"]
        baseline_path = (
            ctx.source_ctx.source_r3c1_run
            / "stage4_2r3c1_authenticated_visible_manifold_control"
            / "raw"
            / str(baseline_file["path"])
        )
        if (
            not baseline_path.is_file()
            or baseline_path.stat().st_size
            != int(baseline_file["size_bytes"])
            or _sha256(baseline_path) != str(baseline_file["sha256"])
        ):
            raise ValueError(f"R3c1 baseline file mismatch: {key}")
        baseline_result = t2.t1.r3c3.read_json_gz(baseline_path)
        baseline, _ = t2.t1.r3c3._trajectory_arrays(
            baseline_result, 0.01
        )
        embedded = np.asarray(
            source["offline_design_only_baseline"]["RZI_by_state"],
            dtype=float,
        )
        if not np.array_equal(baseline, embedded):
            raise ValueError(f"embedded T3 baseline mismatch: {key}")
        responses = sorted(
            source["responses"], key=lambda row: int(row["basis_index"])
        )
        if (
            len(responses) != 8
            or [int(row["basis_index"]) for row in responses]
            != list(range(8))
        ):
            raise ValueError(f"T3 response ordering mismatch: {key}")
        position_columns = [
            np.asarray(row["delta_RZI_by_state"], dtype=float)
            for row in responses
        ]
        velocity_columns = [
            np.asarray(row["delta_velocity_RZ_by_state"], dtype=float)
            for row in responses
        ]
        evaluator = frozen.FormalEvaluator(ctx.source_ctx, baseline_result)
        t3_row = t3_by_key[key]
        coefficients = np.asarray(
            t3_row["best_coefficients"], dtype=float
        )
        predicted = baseline + np.tensordot(
            np.stack(position_columns, axis=2),
            coefficients,
            axes=(2, 0),
        )
        margin, reproduced = evaluator.best(predicted)
        margin_error = abs(
            margin - float(t3_row["best_minimum_signed_margin"])
        )
        if (
            margin_error > 1.0e-9
            or bool(margin >= -1.0e-12) != bool(t3_row["passed"])
        ):
            raise ValueError(f"T3 optimized row reproduction failed: {key}")
        rank, condition = frozen._velocity_condition(velocity_columns)
        saved_condition = condition_by_key[key]
        if (
            rank != int(saved_condition["matrix_rank"])
            or not math.isclose(
                condition,
                float(saved_condition["condition_number"]),
                rel_tol=0.0,
                abs_tol=1.0e-12,
            )
        ):
            raise ValueError(f"T3 condition reproduction failed: {key}")
        reproduction_rows.append(
            {
                "context": list(key),
                "saved_pass": bool(t3_row["passed"]),
                "reproduced_pass": bool(margin >= -1.0e-12),
                "saved_margin": float(
                    t3_row["best_minimum_signed_margin"]
                ),
                "reproduced_margin": float(margin),
                "absolute_margin_error": margin_error,
            }
        )
        contexts.append(
            {
                "key": key,
                "baseline": baseline,
                "evaluator": evaluator,
                "position_columns": position_columns,
                "velocity_columns": velocity_columns,
                "t3_row": t3_row,
            }
        )
    if (
        sum(row["saved_pass"] for row in reproduction_rows) != 16
        or any(
            row["saved_pass"] != row["reproduced_pass"]
            for row in reproduction_rows
        )
        or max(row["absolute_margin_error"] for row in reproduction_rows)
        > 1.0e-9
    ):
        raise ValueError("T3 optimized feasibility reproduction failed")

    profile_summaries = []
    for profile_name in PROFILE_NAMES:
        for scale in AMPLITUDE_SCALES:
            bounds = _bounds_for_profile(profile_name, scale)
            rows = []
            condition_rows = []
            for context in contexts:
                optimized = _optimize_context_bounds(
                    context["evaluator"],
                    context["baseline"],
                    context["position_columns"],
                    bounds=bounds,
                    t3_seed=context["t3_row"]["best_coefficients"],
                )
                key = context["key"]
                rows.append(
                    {
                        "pair_id": key[0],
                        "history_member": key[1],
                        "target_id": key[2],
                        "actual_delay_steps": key[3],
                        "actual_slew_scale": key[4],
                        "saved_baseline_pass": bool(
                            context["t3_row"]["saved_baseline_pass"]
                        ),
                        "t3_passed": bool(context["t3_row"]["passed"]),
                        "t3_minimum_signed_margin": float(
                            context["t3_row"][
                                "best_minimum_signed_margin"
                            ]
                        ),
                        "margin_delta_vs_t3": float(
                            optimized["best_minimum_signed_margin"]
                            - float(
                                context["t3_row"][
                                    "best_minimum_signed_margin"
                                ]
                            )
                        ),
                        **optimized,
                    }
                )
                scaled_velocity = [
                    column * float(bound)
                    for column, bound in zip(
                        context["velocity_columns"], bounds
                    )
                ]
                rank, condition = frozen._velocity_condition(
                    scaled_velocity
                )
                condition_rows.append(
                    {
                        "context": list(key),
                        "matrix_rank": rank,
                        "condition_number": condition,
                        "passed": bool(
                            rank == 8
                            and math.isfinite(condition)
                            and condition <= MAXIMUM_CONDITION
                        ),
                    }
                )
            pass_count = sum(row["passed"] for row in rows)
            repaired = sum(
                row["passed"] and not row["saved_baseline_pass"]
                for row in rows
            )
            regressions = sum(
                not row["passed"] and row["saved_baseline_pass"]
                for row in rows
            )
            condition_pass = sum(row["passed"] for row in condition_rows)
            profile_summaries.append(
                {
                    "profile_id": _profile_id(profile_name, scale),
                    "profile_name": profile_name,
                    "amplitude_scale": float(scale),
                    "coefficient_bounds": [
                        [-float(bound), float(bound)] for bound in bounds
                    ],
                    "implied_basis_amplitudes": [
                        float(amplitude) * float(bound)
                        for amplitude, bound in zip(
                            controller_bank["basis_amplitudes"], bounds
                        )
                    ],
                    "context_count": 32,
                    "optimistic_formal_pass_count": pass_count,
                    "optimistic_formal_failure_count": 32 - pass_count,
                    "failed_baseline_repair_count": repaired,
                    "baseline_pass_regression_count": regressions,
                    "extrapolated_condition_pass_count": condition_pass,
                    "maximum_extrapolated_condition_number": max(
                        row["condition_number"] for row in condition_rows
                    ),
                    "formal_32_of_32": pass_count == 32,
                    "formal_and_extrapolated_condition_32_of_32": bool(
                        pass_count == 32 and condition_pass == 32
                    ),
                    "rows": rows,
                    "condition_rows": condition_rows,
                }
            )

    failed_keys = {
        key for key, row in t3_by_key.items() if not bool(row["passed"])
    }
    minimum_scale_rows = []
    summaries_by_profile = {
        profile_name: [
            summary
            for summary in profile_summaries
            if summary["profile_name"] == profile_name
        ]
        for profile_name in PROFILE_NAMES
    }
    for key in sorted(failed_keys):
        row = {
            "context": list(key),
            "t3_minimum_signed_margin": float(
                t3_by_key[key]["best_minimum_signed_margin"]
            ),
        }
        for profile_name in PROFILE_NAMES:
            first = None
            for summary in summaries_by_profile[profile_name]:
                candidate = {
                    _row_key(item): item for item in summary["rows"]
                }[key]
                if candidate["passed"]:
                    first = float(summary["amplitude_scale"])
                    break
            row[f"{profile_name}_first_passing_grid_scale"] = first
        minimum_scale_rows.append(row)

    provenance = {
        "stage": "Stage4.2R3c3T4",
        "identity": "eight_basis_unvalidated_amplitude_envelope_v1",
        "t3_manifest_sha256": EXPECTED_T3_MANIFEST_SHA256,
        "t3_audit_bank_sha256": EXPECTED_T3_AUDIT_BANK_SHA256,
        "t3_controller_bank_sha256": EXPECTED_T3_CONTROLLER_BANK_SHA256,
        "t3_feasibility_sha256": EXPECTED_T3_FEASIBILITY_SHA256,
        "t3_audit_tool_sha256": EXPECTED_T3_AUDIT_TOOL_SHA256,
        "frozen_formal_evaluator_sha256": (
            EXPECTED_FROZEN_FORMAL_EVALUATOR_SHA256
        ),
        "amplitude_scales": list(AMPLITUDE_SCALES),
        "profile_names": list(PROFILE_NAMES),
        "formal_timing_changed": False,
    }
    result = {
        "schema_version": 1,
        "stage": "Stage4.2R3c3T4",
        "identity": "eight_basis_unvalidated_amplitude_envelope_v1",
        "purpose": (
            "route-selection diagnostic for the amount and location of "
            "unvalidated amplitude extrapolation required after failed T3"
        ),
        "provenance": provenance,
        "provenance_digest": _canonical_digest(provenance),
        "t3_reproduction": {
            "context_count": 32,
            "saved_pass_count": 16,
            "pass_match_count": sum(
                row["saved_pass"] == row["reproduced_pass"]
                for row in reproduction_rows
            ),
            "maximum_absolute_margin_error": max(
                row["absolute_margin_error"]
                for row in reproduction_rows
            ),
            "rows": reproduction_rows,
        },
        "diagnostic_contract": {
            "amplitude_scales": list(AMPLITUDE_SCALES),
            "profiles": {
                "transport_only": (
                    "R3c3 local four remain at [-1,1]; T1/T2 transport "
                    "four expand symmetrically"
                ),
                "uniform_all": (
                    "all eight authenticated odd-response coefficients "
                    "expand symmetrically"
                ),
            },
            "maximum_uniform_scale": 2.0,
            "formal_timing_changed": False,
            "linear_extrapolation_is_validation": False,
            "condition_scaling_is_validation": False,
        },
        "profile_summaries": profile_summaries,
        "failed_context_minimum_passing_grid_scale": minimum_scale_rows,
        "route_summary": {
            "transport_only_formal_32_by_2x": any(
                summary["formal_32_of_32"]
                for summary in summaries_by_profile["transport_only"]
            ),
            "uniform_all_formal_32_by_2x": any(
                summary["formal_32_of_32"]
                for summary in summaries_by_profile["uniform_all"]
            ),
            "any_profile_formal_and_extrapolated_condition_32_by_2x": any(
                summary[
                    "formal_and_extrapolated_condition_32_of_32"
                ]
                for summary in profile_summaries
            ),
        },
        "scientific_classification": {
            "real_tsc_executed_by_this_tool": False,
            "runtime_error": False,
            "statistics_or_reporting_error": False,
            "optimistic_linear_extrapolation_only": True,
            "amplitude_safety_validated": False,
            "combined_action_safety_validated": False,
            "r3c4_implementation_authorized": False,
            "r3c4_real_tsc_execution_authorized": False,
            "bc_dagger_or_rl_allowed": False,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(output),
                "output_sha256": _sha256(output),
                "profile_results": [
                    {
                        key: summary[key]
                        for key in (
                            "profile_id",
                            "optimistic_formal_pass_count",
                            "failed_baseline_repair_count",
                            "baseline_pass_regression_count",
                            "extrapolated_condition_pass_count",
                            "maximum_extrapolated_condition_number",
                        )
                    }
                    for summary in profile_summaries
                ],
                "route_summary": result["route_summary"],
                "real_tsc_executed": False,
                "r3c4_implementation_authorized": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
