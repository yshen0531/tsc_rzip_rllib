#!/usr/bin/env python3
"""Audit a separable even/odd quadratic model of the T3 response bank."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import math
import statistics
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
R3C3_RAW_SUBDIR = (
    "stage4_2r3c3_restart_task_clock_probe_identification/raw"
)
T1_RAW_SUBDIR = "stage4_2r3c3t1_transport_response_identification/raw"
T2_RAW_SUBDIR = "stage4_2r3c3t2_held_transport_identification/raw"


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


def _signed_file_metadata(
    response: Mapping[str, Any], side: str
) -> tuple[str, str, int | None]:
    value = response[f"{side}_file"]
    if isinstance(value, Mapping):
        return (
            str(value["path"]),
            str(value["sha256"]),
            int(value["size_bytes"]),
        )
    return (
        str(value),
        str(response[f"{side}_sha256"]),
        None,
    )


def _predict(
    baseline: np.ndarray,
    odd_columns: Sequence[np.ndarray],
    even_columns: Sequence[np.ndarray],
    coefficients: Sequence[float],
) -> np.ndarray:
    coefficient_array = np.asarray(coefficients, dtype=float)
    odd = np.stack(odd_columns, axis=2)
    even = np.stack(even_columns, axis=2)
    return (
        baseline
        + np.tensordot(odd, coefficient_array, axes=(2, 0))
        + np.tensordot(even, coefficient_array**2, axes=(2, 0))
    )


def _deduplicate_starts(starts: Sequence[np.ndarray]) -> list[np.ndarray]:
    unique: list[np.ndarray] = []
    seen: set[tuple[float, ...]] = set()
    for start in starts:
        value = np.asarray(start, dtype=float)
        key = tuple(np.round(value, 12))
        if key not in seen:
            seen.add(key)
            unique.append(value)
    return unique


def _optimize_context(
    evaluator: Any,
    baseline: np.ndarray,
    odd_columns: Sequence[np.ndarray],
    even_columns: Sequence[np.ndarray],
    *,
    t3_seed: Sequence[float],
) -> dict[str, Any]:
    if (
        len(odd_columns) != 8
        or len(even_columns) != 8
        or len(t3_seed) != 8
    ):
        raise ValueError("separable quadratic optimizer requires eight bases")

    def values(coefficients: np.ndarray) -> np.ndarray:
        return _predict(
            baseline,
            odd_columns,
            even_columns,
            coefficients,
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
        list(itertools.product((-1.0, 0.0, 1.0), repeat=8)),
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
                "exhaustive_quadratic_ternary_grid",
            )
    starts = _deduplicate_starts(
        [
            *[
                row[1]
                for row in sorted(
                    grid_rows, key=lambda item: item[0], reverse=True
                )[:12]
            ],
            zero,
            np.clip(np.asarray(t3_seed, dtype=float), -1.0, 1.0),
        ]
    )
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
                bounds=[(-1.0, 1.0)] * 8,
                options={
                    "maxiter": 400,
                    "ftol": 1.0e-12,
                    "disp": False,
                },
            )
            coefficients = np.clip(
                np.asarray(result.x, dtype=float), -1.0, 1.0
            )
            margin, row = evaluator.best(values(coefficients))
            if margin > best[0]:
                best = (
                    margin,
                    coefficients,
                    row,
                    "per_endpoint_quadratic_multistart_slsqp",
                )
    return {
        "passed": bool(best[0] >= -1.0e-12),
        "best_minimum_signed_margin": float(best[0]),
        "best_endpoint_step": int(best[2]["endpoint_step"]),
        "best_coefficients": np.round(best[1], 12).tolist(),
        "active_constraint": str(best[2]["active_constraint"]),
        "method": best[3],
    }


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
    frozen_t3_path = args.frozen_t3_audit.expanduser().resolve()
    if (
        not frozen_t3_path.is_file()
        or _sha256(frozen_t3_path) != EXPECTED_T3_AUDIT_TOOL_SHA256
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
    provenance = audit_bank["provenance_contract"]
    if (
        manifest_inventory != expected_inventory
        or str(manifest["provenance_digest"])
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
        or bool(manifest["all_preregistered_gates_pass"])
        or bool(feasibility["all_preregistered_gates_pass"])
        or int(feasibility["optimistic_formal_pass_count"]) != 16
        or int(feasibility["eight_basis_condition_pass_count"]) != 11
    ):
        raise ValueError("T3 identity or failed outcome changed")

    ctx = t2.load_stage42r3c3t2_config(
        args.config,
        source_stage42r3b_run=args.source_stage4_2r3b_run,
        source_stage42r3c3_run=args.source_stage4_2r3c3_run,
        source_stage42r3c3_bank_dir=args.source_stage4_2r3c3_bank_dir,
        source_stage42r3c3t1_run=args.source_stage4_2r3c3t1_run,
        source_stage42r3c3t1_audit_dir=(
            args.source_stage4_2r3c3t1_audit_dir
        ),
        run_dir_override=args.t2_run_dir,
    )
    raw_roots = {
        **{
            index: args.source_stage4_2r3c3_run.expanduser().resolve()
            / R3C3_RAW_SUBDIR
            for index in range(4)
        },
        **{
            index: args.source_stage4_2r3c3t1_run.expanduser().resolve()
            / T1_RAW_SUBDIR
            for index in (4, 5)
        },
        **{
            index: args.t2_run_dir.expanduser().resolve() / T2_RAW_SUBDIR
            for index in (6, 7)
        },
    }
    if any(not root.is_dir() for root in raw_roots.values()):
        raise ValueError("one or more signed raw roots are missing")

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
    signed_inventory = []
    even_metric_rows = []
    reproduction_rows = []
    maximum_odd_error = 0.0
    maximum_signed_endpoint_error = 0.0
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
        evaluator = frozen.FormalEvaluator(ctx.source_ctx, baseline_result)
        responses = sorted(
            source["responses"], key=lambda row: int(row["basis_index"])
        )
        if (
            len(responses) != 8
            or [int(row["basis_index"]) for row in responses]
            != list(range(8))
        ):
            raise ValueError(f"T3 response ordering mismatch: {key}")
        odd_columns = []
        even_columns = []
        velocity_columns = []
        for response in responses:
            index = int(response["basis_index"])
            signed_values = {}
            for side in ("plus", "minus"):
                name, expected_sha, expected_size = _signed_file_metadata(
                    response, side
                )
                path = raw_roots[index] / name
                actual_sha = _sha256(path) if path.is_file() else None
                if (
                    actual_sha != expected_sha
                    or (
                        expected_size is not None
                        and path.stat().st_size != expected_size
                    )
                ):
                    raise ValueError(
                        f"signed raw file mismatch: {key} {index} {side}"
                    )
                result = t2.t1.r3c3.read_json_gz(path)
                if (
                    not bool(result.get("completed"))
                    or not bool(result.get("success"))
                    or bool(result.get("failure_reason"))
                ):
                    raise ValueError(
                        f"signed raw result failed: {key} {index} {side}"
                    )
                values, _ = t2.t1.r3c3._trajectory_arrays(result, 0.01)
                if len(values) < len(baseline):
                    raise ValueError(
                        f"signed raw horizon mismatch: {key} {index} {side}"
                    )
                signed_values[side] = values[: len(baseline)]
                signed_inventory.append(
                    {
                        "context": list(key),
                        "basis_index": index,
                        "side": side,
                        "path": name,
                        "size_bytes": int(path.stat().st_size),
                        "sha256": actual_sha,
                    }
                )
            plus = signed_values["plus"]
            minus = signed_values["minus"]
            odd = (plus - minus) / 2.0
            even = (plus + minus) / 2.0 - baseline
            saved_odd = np.asarray(
                response["delta_RZI_by_state"], dtype=float
            )
            odd_error = float(np.max(np.abs(odd - saved_odd)))
            signed_error = max(
                float(np.max(np.abs(baseline + odd + even - plus))),
                float(np.max(np.abs(baseline - odd + even - minus))),
            )
            maximum_odd_error = max(maximum_odd_error, odd_error)
            maximum_signed_endpoint_error = max(
                maximum_signed_endpoint_error, signed_error
            )
            if odd_error > 1.0e-12 or signed_error > 1.0e-12:
                raise ValueError(
                    f"signed response reproduction mismatch: {key} {index}"
                )
            even_velocity = np.diff(even[:, :2], axis=0) / 0.01
            even_metric_rows.append(
                {
                    "context": list(key),
                    "basis_index": index,
                    "probe_id": str(response["audit_probe_id"]),
                    "maximum_even_RZ_m": float(
                        np.max(np.abs(even[:, :2]))
                    ),
                    "maximum_even_Ip_A": float(
                        np.max(np.abs(even[:, 2]))
                    ),
                    "maximum_even_speed_m_per_s": float(
                        np.max(
                            np.linalg.norm(even_velocity, axis=1)
                        )
                    ),
                }
            )
            odd_columns.append(odd)
            even_columns.append(even)
            velocity_columns.append(
                np.asarray(
                    response["delta_velocity_RZ_by_state"], dtype=float
                )
            )
        t3_row = t3_by_key[key]
        t3_prediction = baseline + np.tensordot(
            np.stack(odd_columns, axis=2),
            np.asarray(t3_row["best_coefficients"], dtype=float),
            axes=(2, 0),
        )
        t3_margin, _ = evaluator.best(t3_prediction)
        t3_margin_error = abs(
            t3_margin - float(t3_row["best_minimum_signed_margin"])
        )
        if t3_margin_error > 1.0e-9:
            raise ValueError(f"T3 linear row reproduction failed: {key}")
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
                "reproduced_pass": bool(t3_margin >= -1.0e-12),
                "saved_margin": float(
                    t3_row["best_minimum_signed_margin"]
                ),
                "reproduced_margin": float(t3_margin),
                "absolute_margin_error": t3_margin_error,
            }
        )
        contexts.append(
            {
                "key": key,
                "baseline": baseline,
                "evaluator": evaluator,
                "odd_columns": odd_columns,
                "even_columns": even_columns,
                "t3_row": t3_row,
            }
        )
    if (
        len(signed_inventory) != 512
        or len(even_metric_rows) != 256
        or maximum_odd_error != 0.0
        or maximum_signed_endpoint_error > 1.0e-12
        or sum(row["saved_pass"] for row in reproduction_rows) != 16
        or any(
            row["saved_pass"] != row["reproduced_pass"]
            for row in reproduction_rows
        )
    ):
        raise ValueError("T5 input authentication aggregate mismatch")

    rows = []
    for context in contexts:
        optimized = _optimize_context(
            context["evaluator"],
            context["baseline"],
            context["odd_columns"],
            context["even_columns"],
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
                    context["t3_row"]["best_minimum_signed_margin"]
                ),
                "margin_delta_vs_t3": float(
                    optimized["best_minimum_signed_margin"]
                    - float(
                        context["t3_row"]["best_minimum_signed_margin"]
                    )
                ),
                **optimized,
            }
        )
    pass_count = sum(row["passed"] for row in rows)
    repaired = sum(
        row["passed"] and not row["saved_baseline_pass"] for row in rows
    )
    regressions = sum(
        not row["passed"] and row["saved_baseline_pass"] for row in rows
    )
    failed = [row for row in rows if not row["passed"]]
    failed_margins = [
        float(row["best_minimum_signed_margin"]) for row in failed
    ]
    provenance_value = {
        "stage": "Stage4.2R3c3T5",
        "identity": "separable_even_odd_quadratic_diagnostic_v1",
        "t3_manifest_sha256": EXPECTED_T3_MANIFEST_SHA256,
        "t3_audit_bank_sha256": EXPECTED_T3_AUDIT_BANK_SHA256,
        "t3_controller_bank_sha256": EXPECTED_T3_CONTROLLER_BANK_SHA256,
        "t3_feasibility_sha256": EXPECTED_T3_FEASIBILITY_SHA256,
        "t3_audit_tool_sha256": EXPECTED_T3_AUDIT_TOOL_SHA256,
        "frozen_formal_evaluator_sha256": (
            EXPECTED_FROZEN_FORMAL_EVALUATOR_SHA256
        ),
        "coefficient_lower_bound": -1.0,
        "coefficient_upper_bound": 1.0,
        "formal_timing_changed": False,
    }
    result = {
        "schema_version": 1,
        "stage": "Stage4.2R3c3T5",
        "identity": "separable_even_odd_quadratic_diagnostic_v1",
        "purpose": (
            "route-selection diagnostic for exact per-basis even response "
            "terms with all cross interactions omitted"
        ),
        "provenance": provenance_value,
        "provenance_digest": _canonical_digest(provenance_value),
        "input_authentication": {
            "signed_raw_file_count": 512,
            "signed_pair_count": 256,
            "signed_inventory_digest": _canonical_digest(
                signed_inventory
            ),
            "maximum_odd_reproduction_error": maximum_odd_error,
            "maximum_signed_endpoint_reproduction_error": (
                maximum_signed_endpoint_error
            ),
            "t3_reproduction_context_count": 32,
            "t3_reproduction_pass_match_count": sum(
                row["saved_pass"] == row["reproduced_pass"]
                for row in reproduction_rows
            ),
            "maximum_t3_margin_reproduction_error": max(
                row["absolute_margin_error"]
                for row in reproduction_rows
            ),
            "t3_reproduction_rows": reproduction_rows,
        },
        "model_contract": {
            "formula": (
                "baseline + sum(c_i * odd_i + c_i^2 * even_i)"
            ),
            "basis_count": 8,
            "coefficient_lower_bound": -1.0,
            "coefficient_upper_bound": 1.0,
            "single_basis_signed_endpoints_exact": True,
            "cross_interactions_included": False,
            "combined_action_safety_validated": False,
            "formal_timing_changed": False,
        },
        "even_term_metrics": {
            "row_count": len(even_metric_rows),
            "maximum_even_RZ_m": max(
                row["maximum_even_RZ_m"] for row in even_metric_rows
            ),
            "median_even_RZ_m": statistics.median(
                row["maximum_even_RZ_m"] for row in even_metric_rows
            ),
            "maximum_even_Ip_A": max(
                row["maximum_even_Ip_A"] for row in even_metric_rows
            ),
            "maximum_even_speed_m_per_s": max(
                row["maximum_even_speed_m_per_s"]
                for row in even_metric_rows
            ),
            "rows": even_metric_rows,
        },
        "context_count": 32,
        "optimistic_formal_pass_count": pass_count,
        "optimistic_formal_failure_count": 32 - pass_count,
        "failed_baseline_repair_count": repaired,
        "baseline_pass_regression_count": regressions,
        "unchanged_odd_condition_pass_count": int(
            audit_bank["eight_basis_condition_audit"]["pass_count"]
        ),
        "maximum_unchanged_odd_condition_number": float(
            audit_bank["eight_basis_condition_audit"][
                "maximum_condition_number"
            ]
        ),
        "best_remaining_failed_margin": (
            max(failed_margins) if failed_margins else None
        ),
        "worst_remaining_failed_margin": (
            min(failed_margins) if failed_margins else None
        ),
        "context_rows": rows,
        "route_summary": {
            "separable_quadratic_formal_32_of_32": pass_count == 32,
            "separable_quadratic_repairs_all_16": repaired == 16,
            "unchanged_odd_condition_32_of_32": False,
            "r3c4_implementation_authorized": False,
        },
        "scientific_classification": {
            "real_tsc_executed_by_this_tool": False,
            "runtime_error": False,
            "statistics_or_reporting_error": False,
            "optimistic_separable_quadratic_only": True,
            "cross_interactions_validated": False,
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
                "signed_raw_file_count": 512,
                "signed_pair_count": 256,
                "maximum_odd_reproduction_error": maximum_odd_error,
                "optimistic_formal_pass_count": pass_count,
                "failed_baseline_repair_count": repaired,
                "baseline_pass_regression_count": regressions,
                "unchanged_odd_condition_pass_count": int(
                    audit_bank["eight_basis_condition_audit"][
                        "pass_count"
                    ]
                ),
                "best_remaining_failed_margin": result[
                    "best_remaining_failed_margin"
                ],
                "worst_remaining_failed_margin": result[
                    "worst_remaining_failed_margin"
                ],
                "r3c4_implementation_authorized": False,
                "real_tsc_executed": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
