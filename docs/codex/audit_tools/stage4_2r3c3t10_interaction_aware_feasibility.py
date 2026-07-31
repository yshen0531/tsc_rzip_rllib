#!/usr/bin/env python3
"""Authenticate T9 raw and audit a fixed interaction-aware interpolant.

This tool is deliberately retrospective and read-only.  It fits the frozen
six-term two-coordinate surface at the seven T9 measured nodes and evaluates
unchanged-contract optimistic feasibility.  It cannot authorize R3c4.
"""

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
from scipy.optimize import minimize

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t9_pc3_mixed_interaction_identification as t9,
)


STAGE = "Stage4.2R3c3T10"
IDENTITY = "measured_two_coordinate_interaction_aware_feasibility_v1"
TERM_ORDER = (
    "stress",
    "pc3",
    "stress_pc3",
    "stress_squared",
    "pc3_squared",
    "stress_squared_pc3",
)
T9_MANIFEST = "stage4_2r3c3t9_manifest.json"
T9_STATE = "stage4_2r3c3t9_state.json"
T9_SUMMARY = "stage4_2r3c3t9_pc3_mixed_interaction/summary.json"
T9_RESULTS = "stage4_2r3c3t9_pc3_mixed_interaction/results.json"
T9_RAW = "stage4_2r3c3t9_pc3_mixed_interaction/raw"
T9_SERVER_AUDIT = "stage4_2r3c3t9_server_audit.json"


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


def _read_json(path: Path) -> Any:
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
            ensure_ascii=False,
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


def _inventory(paths: Sequence[Path]) -> dict[str, Any]:
    rows = [
        {
            "path": path.name,
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


def _features(stress: float, pc3: float) -> np.ndarray:
    return np.asarray(
        [
            stress,
            pc3,
            stress * pc3,
            stress * stress,
            pc3 * pc3,
            stress * stress * pc3,
        ],
        dtype=float,
    )


def _design_nodes(standalone_coordinate: float) -> list[tuple[float, float]]:
    return [
        (0.0, standalone_coordinate),
        (0.0, -standalone_coordinate),
        (1.0, 1.0),
        (1.0, -1.0),
        (-1.0, 1.0),
        (-1.0, -1.0),
    ]


def _design_matrix(standalone_coordinate: float) -> np.ndarray:
    return np.stack(
        [_features(stress, pc3) for stress, pc3 in _design_nodes(standalone_coordinate)]
    )


def _fit_terms(
    baseline: np.ndarray,
    node_values: Sequence[np.ndarray],
    standalone_coordinate: float,
) -> tuple[np.ndarray, dict[str, Any]]:
    matrix = _design_matrix(standalone_coordinate)
    values = np.stack(
        [np.asarray(value, dtype=float) - baseline for value in node_values]
    )
    if values.shape[0] != 6:
        raise ValueError("T10 requires exactly six nonbaseline nodes")
    terms = np.linalg.solve(matrix, values.reshape(6, -1)).reshape(
        (6,) + baseline.shape
    )
    reconstructed = np.stack(
        [
            baseline
            + np.tensordot(_features(stress, pc3), terms, axes=(0, 0))
            for stress, pc3 in _design_nodes(standalone_coordinate)
        ]
    )
    errors = np.abs(reconstructed - np.stack(node_values))
    return terms, {
        "rank": int(np.linalg.matrix_rank(matrix)),
        "condition_number": float(np.linalg.cond(matrix)),
        "maximum_node_reconstruction_abs_error": float(np.max(errors)),
    }


def _validate_design(cfg: Mapping[str, Any]) -> None:
    source = cfg["source_contract"]
    model = cfg["model_contract"]
    gate = cfg["acceptance_gate"]
    scope = cfg["scientific_scope"]
    if (
        int(cfg.get("schema_version", -1)) != 1
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or tuple(model["coordinates"]) != ("stress", "pc3")
        or tuple(model["term_order"]) != TERM_ORDER
        or float(model["coordinate_lower_bound"]) != -1.0
        or float(model["coordinate_upper_bound"]) != 1.0
        or int(model["required_node_count_per_context"]) != 7
        or int(model["required_nonbaseline_node_count_per_context"]) != 6
        or int(model["required_design_rank"]) != 6
        or float(model["maximum_design_condition_number"]) != 3.0
        or float(model["maximum_node_reconstruction_abs_error"]) != 1e-12
        or not bool(model["formal_prefix_only"])
        or bool(model["formal_timing_changed"])
        or int(model["optimizer_grid_points_per_axis"]) != 41
        or int(model["optimizer_multistart_count_per_endpoint"]) != 4
        or int(gate["context_count"]) != 32
        or int(gate["authenticated_raw_count"]) != 224
        or int(gate["baseline_formal_pass_count"]) != 16
        or int(gate["model_fit_pass_count"]) != 32
        or int(gate["optimistic_formal_pass_count"]) != 32
        or int(gate["failed_baseline_repair_count"]) != 16
        or int(gate["baseline_pass_regression_count"]) != 0
        or float(gate["coordinate_lower_bound"]) != -1.0
        or float(gate["coordinate_upper_bound"]) != 1.0
        or bool(gate["formal_timing_changed"])
        or int(source["t9_raw_count"]) != 224
        or not bool(scope["development_set_only"])
        or not bool(scope["retrospective_after_T9"])
        or not bool(scope["measured_node_interpolant_only"])
        or bool(scope["real_tsc_executed"])
        or bool(scope["real_mpc_executed"])
        or bool(scope["stress_only_axis_validated_at_common_amplitude"])
        or bool(scope["pc3_only_axis_validated_at_common_amplitude"])
        or bool(scope["r3c4_implementation_authorized"])
        or bool(scope["bc_dagger_or_rl_allowed"])
    ):
        raise ValueError("T10 frozen design changed")


def _context_key_from_row(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        str(row["pair_id"]),
        str(row["history_member"]),
        str(row["target_id"]),
        int(row["actual_delay_steps"]),
        float(row["actual_slew_scale"]),
    )


def _optimize_context(
    evaluator: Any,
    baseline: np.ndarray,
    terms: np.ndarray,
    model_cfg: Mapping[str, Any],
) -> dict[str, Any]:
    lower = float(model_cfg["coordinate_lower_bound"])
    upper = float(model_cfg["coordinate_upper_bound"])

    def values(coordinates: Sequence[float]) -> np.ndarray:
        stress, pc3 = np.asarray(coordinates, dtype=float)
        return baseline + np.tensordot(
            _features(float(stress), float(pc3)), terms, axes=(0, 0)
        )

    zero = np.zeros(2, dtype=float)
    zero_margin, zero_row = evaluator.best(values(zero))
    if zero_margin >= -1e-12:
        return {
            "passed": True,
            "best_minimum_signed_margin": float(zero_margin),
            "best_endpoint_step": int(zero_row["endpoint_step"]),
            "best_coordinates": [0.0, 0.0],
            "active_constraint": str(zero_row["active_constraint"]),
            "method": "exact_baseline_already_passes",
        }

    axis = np.linspace(
        lower,
        upper,
        int(model_cfg["optimizer_grid_points_per_axis"]),
    )
    grid_rows = []
    best = (zero_margin, zero.copy(), zero_row, "zero_baseline")
    for stress, pc3 in itertools.product(axis, repeat=2):
        coordinates = np.asarray([stress, pc3], dtype=float)
        margin, row = evaluator.best(values(coordinates))
        grid_rows.append((float(margin), coordinates.copy(), row))
        if margin > best[0]:
            best = (
                float(margin),
                coordinates.copy(),
                row,
                "fixed_41_by_41_grid",
            )

    endpoints = [
        int(endpoint)
        for endpoint in evaluator.policy["allowed_arrival_steps"]
        if int(endpoint) <= evaluator.horizon
    ]
    start_count = int(model_cfg["optimizer_multistart_count_per_endpoint"])
    for endpoint in endpoints:
        starts = sorted(
            grid_rows,
            key=lambda item: evaluator.endpoint_margin(
                values(item[1]), endpoint
            )[0],
            reverse=True,
        )[:start_count]
        for _, start, _ in starts:
            result = minimize(
                lambda coordinates: -evaluator.endpoint_margin(
                    values(coordinates), endpoint
                )[0],
                start,
                method="SLSQP",
                bounds=[(lower, upper), (lower, upper)],
                options={
                    "maxiter": int(model_cfg["optimizer_max_iterations"]),
                    "ftol": float(model_cfg["optimizer_ftol"]),
                    "disp": False,
                },
            )
            coordinates = np.clip(
                np.asarray(result.x, dtype=float), lower, upper
            )
            margin, row = evaluator.best(values(coordinates))
            if margin > best[0]:
                best = (
                    float(margin),
                    coordinates,
                    row,
                    "per_endpoint_multistart_slsqp",
                )
    return {
        "passed": bool(best[0] >= -1e-12),
        "best_minimum_signed_margin": float(best[0]),
        "best_endpoint_step": int(best[2]["endpoint_step"]),
        "best_coordinates": np.round(best[1], 12).tolist(),
        "active_constraint": str(best[2]["active_constraint"]),
        "method": best[3],
    }


def _authenticate_t9_files(
    cfg: Mapping[str, Any], run_dir: Path, audit_dir: Path
) -> dict[str, Any]:
    source = cfg["source_contract"]
    if run_dir.name != str(source["t9_run_name"]):
        raise ValueError("immutable T9 run name mismatch")
    paths = {
        "manifest": run_dir / T9_MANIFEST,
        "state": run_dir / T9_STATE,
        "summary": run_dir / T9_SUMMARY,
        "results": run_dir / T9_RESULTS,
        "server_audit": audit_dir / T9_SERVER_AUDIT,
    }
    expected = {
        "manifest": source["t9_manifest_sha256"],
        "state": source["t9_state_sha256"],
        "summary": source["t9_summary_sha256"],
        "results": source["t9_results_sha256"],
        "server_audit": source["t9_server_audit_sha256"],
    }
    hashes = {}
    for name, path in paths.items():
        actual = _sha256(path)
        if actual != str(expected[name]):
            raise ValueError(f"T9 {name} hash mismatch")
        hashes[name] = actual
    server = _read_json(paths["server_audit"])
    if (
        not bool(server["raw_and_manifest_integrity_passed"])
        or not bool(server["reported_summary_exact_on_recomputation"])
        or int(server["statistics_or_reporting_error_count"]) != 0
        or int(server["runtime_or_environment_error_count"]) != 0
        or not bool(server["certified_primary_pass"])
        or bool(server["recomputed_linear_route_pass"])
        or str(server["runtime_package_fingerprint_digest"])
        != str(source["t9_runtime_package_digest"])
    ):
        raise ValueError("T9 certified outcome changed")
    summary = _read_json(paths["summary"])
    if (
        not bool(summary["identification_passed"])
        or bool(summary["linear_route_passed"])
        or int(summary["n_rollouts"]) != int(source["t9_raw_count"])
        or int(summary["runtime_or_environment_error_count"]) != 0
    ):
        raise ValueError("T9 summary outcome changed")
    return {"paths": paths, "hashes": hashes, "server": server, "summary": summary}


def run_audit(args: argparse.Namespace) -> dict[str, Any]:
    design_path = args.config.expanduser().resolve()
    cfg = _read_json(design_path)
    _validate_design(cfg)
    source = cfg["source_contract"]
    output = args.output.expanduser().resolve()
    run_dir = args.source_stage4_2r3c3t9_run.expanduser().resolve()
    audit_dir = args.source_stage4_2r3c3t9_audit_dir.expanduser().resolve()
    if output.exists():
        raise ValueError("T10 output directory must be new")
    if output == run_dir or run_dir in output.parents:
        raise ValueError("T10 output must remain outside the immutable T9 run")

    t9_auth = _authenticate_t9_files(cfg, run_dir, audit_dir)
    if _sha256(Path(t9.__file__).resolve()) != str(
        source["t9_runtime_source_sha256"]
    ):
        raise ValueError("T9 source hash mismatch")
    formal = _load_module(
        args.frozen_formal_evaluator,
        str(source["frozen_formal_evaluator_sha256"]),
        "stage4_2r3c3t10_frozen_formal_evaluator",
    )
    if _sha256(args.source_stage4_2r3c3t7_controller_bank.resolve()) != str(
        source["t7_controller_bank_sha256"]
    ):
        raise ValueError("T7 controller bank hash mismatch")

    t9_ctx = t9.load_stage42r3c3t9_config(
        args.t9_config,
        source_stage42r3b_run=args.source_stage4_2r3b_run,
        source_stage42r3c3_run=args.source_stage4_2r3c3_run,
        source_stage42r3c3_bank_dir=args.source_stage4_2r3c3_bank_dir,
        source_stage42r3c3t1_run=args.source_stage4_2r3c3t1_run,
        source_stage42r3c3t1_audit_dir=args.source_stage4_2r3c3t1_audit_dir,
        source_stage42r3c3t7_controller_bank=(
            args.source_stage4_2r3c3t7_controller_bank
        ),
        run_dir_override=run_dir,
    )
    selected_pairs, _ = t9.t1.r3c3._recompute_selected_pairs(
        t9_ctx.base_ctx.source_ctx.base_ctx
    )
    expected_specs = t9.build_control_specs(t9_ctx, selected_pairs)
    expected_by_id = {
        str(spec["experiment_id"]): spec for spec in expected_specs
    }

    raw_paths = sorted((run_dir / T9_RAW).glob("*.json.gz"))
    inventory = _inventory(raw_paths)
    if (
        int(inventory["n_files"]) != int(source["t9_raw_count"])
        or inventory["digest"] != str(source["t9_raw_inventory_digest"])
    ):
        raise ValueError("T9 raw inventory mismatch")
    results = [_read_json_gz(path) for path in raw_paths]
    actual_by_id = {
        str(result.get("experiment_id", "")): result for result in results
    }
    if (
        set(actual_by_id) != set(expected_by_id)
        or len(actual_by_id) != int(source["t9_raw_count"])
        or any(
            actual_by_id[experiment_id].get("spec") != spec
            for experiment_id, spec in expected_by_id.items()
        )
        or any(
            not bool(result.get("success"))
            or not bool(t9._phase_trace_valid(result)["passed"])
            for result in results
        )
    ):
        raise ValueError("T9 raw identity or execution authentication failed")
    reported_results = _read_json(t9_auth["paths"]["results"])
    if len(reported_results) != 224:
        raise ValueError("T9 reported result count changed")
    saved_baselines = {
        _context_key_from_row(row): row
        for row in reported_results
        if str(row["probe_id"]) == t9.BASELINE_PROBE_ID
    }
    if len(saved_baselines) != 32:
        raise ValueError("T9 saved baseline coverage mismatch")

    by_context: dict[tuple[Any, ...], dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for result in results:
        key = t9._context_key(result["spec"])
        member = t9._member_key(result["spec"])
        if member in by_context[key]:
            raise ValueError("T9 raw member duplicated")
        by_context[key][member] = result
    if len(by_context) != 32:
        raise ValueError("T9 raw context coverage mismatch")

    model_cfg = cfg["model_contract"]
    gate = cfg["acceptance_gate"]
    expected_q = float(model_cfg["required_standalone_coordinate_abs"])
    model_rows = []
    model_bank_contexts = []
    reproduction_rows = []
    feasibility_inputs = []
    for key in sorted(by_context):
        members = by_context[key]
        required = {
            t9.BASELINE_PROBE_ID,
            f"{t9.PC3_PROBE_ID}:1",
            f"{t9.PC3_PROBE_ID}:-1",
            *t9.FACTORIAL_PROBE_IDS,
        }
        if set(members) != required:
            raise ValueError(f"T9 node coverage mismatch: {key}")
        baseline_result = members[t9.BASELINE_PROBE_ID]
        plus = members[f"{t9.PC3_PROBE_ID}:1"]
        minus = members[f"{t9.PC3_PROBE_ID}:-1"]
        factorial_by_sign = {
            (
                int(members[probe_id]["spec"]["r3c3t9_stress_sign"]),
                int(members[probe_id]["spec"]["r3c3t9_pc3_sign"]),
            ): members[probe_id]
            for probe_id in t9.FACTORIAL_PROBE_IDS
        }
        if set(factorial_by_sign) != set(t9.FACTORIAL_SIGNS):
            raise ValueError("T9 factorial sign coverage changed")
        common_amplitude = float(
            next(iter(factorial_by_sign.values()))["spec"][
                "r3c3t9_factorial_common_amplitude"
            ]
        )
        standalone_scale = float(
            plus["spec"]["r3c3t9_standalone_pc3_scale"]
        )
        q = standalone_scale / common_amplitude
        if not math.isclose(q, expected_q, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError("T9 standalone/common coordinate ratio changed")
        baseline = t9._arrays(baseline_result, 0.01)[0]
        nodes = [
            t9._arrays(plus, 0.01)[0],
            t9._arrays(minus, 0.01)[0],
            *[
                t9._arrays(factorial_by_sign[signs], 0.01)[0]
                for signs in t9.FACTORIAL_SIGNS
            ],
        ]
        if baseline.shape != (51, 3) or any(
            node.shape != baseline.shape for node in nodes
        ):
            raise ValueError("T9 model node trajectory shape changed")
        terms, fit = _fit_terms(baseline, nodes, q)
        fit_pass = bool(
            fit["rank"] == int(model_cfg["required_design_rank"])
            and fit["condition_number"]
            <= float(model_cfg["maximum_design_condition_number"])
            and fit["maximum_node_reconstruction_abs_error"]
            <= float(model_cfg["maximum_node_reconstruction_abs_error"])
        )
        model_rows.append(
            {
                "context": list(key),
                "standalone_coordinate_abs": q,
                **fit,
                "passed": fit_pass,
            }
        )
        horizon = int(baseline_result["spec"]["formal_horizon_steps"])
        short_result = copy.deepcopy(baseline_result)
        short_result["trajectory"] = short_result["trajectory"][: horizon + 1]
        evaluator = formal.FormalEvaluator(
            t9_ctx.base_ctx.source_ctx, short_result
        )
        formal_baseline = baseline[: horizon + 1]
        margin, reproduced = evaluator.best(formal_baseline)
        saved = saved_baselines[key]
        saved_margin = float(saved["formal_minimum_signed_margin"])
        saved_pass = bool(saved["formal_contract_pass"])
        reproduction_rows.append(
            {
                "context": list(key),
                "saved_pass": saved_pass,
                "reproduced_pass": bool(margin >= -1e-12),
                "saved_margin": saved_margin,
                "reproduced_margin": float(margin),
                "absolute_margin_error": abs(saved_margin - margin),
                "reproduced_endpoint_step": int(reproduced["endpoint_step"]),
            }
        )
        feasibility_inputs.append(
            {
                "key": key,
                "baseline": formal_baseline,
                "terms": terms[:, : horizon + 1],
                "evaluator": evaluator,
                "saved_pass": saved_pass,
            }
        )
        model_bank_contexts.append(
            {
                "context": list(key),
                "baseline_experiment_id": str(
                    baseline_result["experiment_id"]
                ),
                "formal_horizon_steps": horizon,
                "standalone_coordinate_abs": q,
                "term_order": list(TERM_ORDER),
                "baseline_RZI_by_state": baseline.tolist(),
                "term_delta_RZI_by_state": terms.tolist(),
                "node_experiment_ids": [
                    str(plus["experiment_id"]),
                    str(minus["experiment_id"]),
                    *[
                        str(factorial_by_sign[signs]["experiment_id"])
                        for signs in t9.FACTORIAL_SIGNS
                    ],
                ],
            }
        )

    if (
        sum(row["saved_pass"] for row in reproduction_rows)
        != int(gate["baseline_formal_pass_count"])
        or any(
            row["saved_pass"] != row["reproduced_pass"]
            for row in reproduction_rows
        )
        or max(row["absolute_margin_error"] for row in reproduction_rows)
        > 1e-12
    ):
        raise ValueError("T9 formal baseline reproduction failed")

    feasibility_rows = []
    for context in feasibility_inputs:
        optimized = _optimize_context(
            context["evaluator"],
            context["baseline"],
            context["terms"],
            model_cfg,
        )
        feasibility_rows.append(
            {
                "pair_id": context["key"][0],
                "history_member": context["key"][1],
                "target_id": context["key"][2],
                "actual_delay_steps": context["key"][3],
                "actual_slew_scale": context["key"][4],
                "saved_baseline_pass": context["saved_pass"],
                **optimized,
            }
        )
    fit_pass_count = sum(row["passed"] for row in model_rows)
    pass_count = sum(row["passed"] for row in feasibility_rows)
    repaired = sum(
        row["passed"] and not row["saved_baseline_pass"]
        for row in feasibility_rows
    )
    regressions = sum(
        not row["passed"] and row["saved_baseline_pass"]
        for row in feasibility_rows
    )
    coordinates_in_bounds = all(
        all(-1.0 <= value <= 1.0 for value in row["best_coordinates"])
        for row in feasibility_rows
    )
    all_gates = bool(
        fit_pass_count == int(gate["model_fit_pass_count"])
        and pass_count == int(gate["optimistic_formal_pass_count"])
        and repaired == int(gate["failed_baseline_repair_count"])
        and regressions == int(gate["baseline_pass_regression_count"])
        and coordinates_in_bounds
    )

    provenance = {
        "stage": STAGE,
        "identity": IDENTITY,
        "design_config_sha256": _sha256(design_path),
        "t9_run": str(run_dir),
        "t9_audit_dir": str(audit_dir),
        "t9_file_hashes": t9_auth["hashes"],
        "t9_raw_inventory": inventory,
        "t9_runtime_package_digest": str(source["t9_runtime_package_digest"]),
        "t9_runtime_source_sha256": str(source["t9_runtime_source_sha256"]),
        "t7_controller_bank_sha256": str(source["t7_controller_bank_sha256"]),
        "frozen_formal_evaluator_sha256": str(
            source["frozen_formal_evaluator_sha256"]
        ),
        "formal_timing_changed": False,
    }
    provenance_digest = _canonical_digest(provenance)
    model_bank = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "provenance_digest": provenance_digest,
        "model_contract": copy.deepcopy(model_cfg),
        "context_count": len(model_bank_contexts),
        "contexts": model_bank_contexts,
        "identification_only": True,
        "measured_node_interpolant_only": True,
        "demonstration_data": False,
        "controller_bank": False,
    }
    audit = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "provenance": provenance,
        "provenance_digest": provenance_digest,
        "raw_authentication": {
            "expected_count": int(source["t9_raw_count"]),
            "actual_count": len(results),
            "inventory_digest": inventory["digest"],
            "spec_identity_exact": True,
            "execution_authentication_exact": True,
            "t9_certified_identification_pass": True,
            "t9_certified_linear_route_pass": False,
        },
        "formal_evaluator_reproduction": {
            "context_count": len(reproduction_rows),
            "saved_pass_count": sum(
                row["saved_pass"] for row in reproduction_rows
            ),
            "pass_match_count": sum(
                row["saved_pass"] == row["reproduced_pass"]
                for row in reproduction_rows
            ),
            "maximum_absolute_margin_error": max(
                row["absolute_margin_error"] for row in reproduction_rows
            ),
            "rows": reproduction_rows,
        },
        "model_fit": {
            "context_count": len(model_rows),
            "pass_count": fit_pass_count,
            "maximum_design_condition_number": max(
                row["condition_number"] for row in model_rows
            ),
            "maximum_node_reconstruction_abs_error": max(
                row["maximum_node_reconstruction_abs_error"]
                for row in model_rows
            ),
            "rows": model_rows,
        },
        "scientific_guardrails": copy.deepcopy(cfg["scientific_scope"]),
    }
    feasibility = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "provenance_digest": provenance_digest,
        "acceptance_gate": copy.deepcopy(gate),
        "context_count": len(feasibility_rows),
        "optimistic_formal_pass_count": pass_count,
        "optimistic_formal_failure_count": len(feasibility_rows) - pass_count,
        "failed_baseline_repair_count": repaired,
        "baseline_pass_regression_count": regressions,
        "model_fit_pass_count": fit_pass_count,
        "optimized_coordinates_in_bounds": coordinates_in_bounds,
        "all_preregistered_gates_pass": all_gates,
        "context_rows": feasibility_rows,
        "scientific_classification": {
            "real_tsc_executed_by_this_tool": False,
            "real_mpc_executed_by_this_tool": False,
            "runtime_error": False,
            "statistics_or_reporting_error": False,
            "raw_corruption": False,
            "measured_node_interpolant_only": True,
            "continuous_surface_validated": False,
            "unmeasured_alias_terms_remain": [
                "stress_pc3_squared",
                "stress_squared_pc3_squared",
            ],
            "next_axis_validation_campaign_authorized": all_gates,
            "r3c4_implementation_authorized": False,
            "real_tsc_controller_execution_authorized": False,
            "probe_trajectories_are_demonstrations": False,
            "bc_dagger_or_rl_allowed": False,
        },
    }

    output.mkdir(parents=True, exist_ok=False)
    model_path = output / "stage4_2r3c3t10_interaction_model_bank_v1.json"
    audit_path = output / "stage4_2r3c3t10_audit_v1.json"
    feasibility_path = output / "stage4_2r3c3t10_feasibility_v1.json"
    _write_json(model_path, model_bank)
    _write_json(audit_path, audit)
    _write_json(feasibility_path, feasibility)
    manifest_path = output / "stage4_2r3c3t10_manifest_v1.json"
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "provenance_digest": provenance_digest,
        "outputs": [
            {
                "path": path.name,
                "size_bytes": int(path.stat().st_size),
                "sha256": _sha256(path),
            }
            for path in (model_path, audit_path, feasibility_path)
        ],
        "all_preregistered_gates_pass": all_gates,
        "next_axis_validation_campaign_authorized": all_gates,
        "r3c4_implementation_authorized": False,
    }
    _write_json(manifest_path, manifest)
    result = {
        "output_dir": str(output),
        "manifest_sha256": _sha256(manifest_path),
        "model_bank_sha256": _sha256(model_path),
        "audit_sha256": _sha256(audit_path),
        "feasibility_sha256": _sha256(feasibility_path),
        "context_count": len(feasibility_rows),
        "model_fit_pass_count": fit_pass_count,
        "optimistic_formal_pass_count": pass_count,
        "failed_baseline_repair_count": repaired,
        "baseline_pass_regression_count": regressions,
        "all_preregistered_gates_pass": all_gates,
        "next_axis_validation_campaign_authorized": all_gates,
        "r3c4_implementation_authorized": False,
        "real_tsc_executed": False,
    }
    print(json.dumps(result, sort_keys=True))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--t9-config", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3b-run", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3c3-run", required=True, type=Path)
    parser.add_argument(
        "--source-stage4-2r3c3-bank-dir", required=True, type=Path
    )
    parser.add_argument("--source-stage4-2r3c3t1-run", required=True, type=Path)
    parser.add_argument(
        "--source-stage4-2r3c3t1-audit-dir", required=True, type=Path
    )
    parser.add_argument(
        "--source-stage4-2r3c3t7-controller-bank", required=True, type=Path
    )
    parser.add_argument("--source-stage4-2r3c3t9-run", required=True, type=Path)
    parser.add_argument(
        "--source-stage4-2r3c3t9-audit-dir", required=True, type=Path
    )
    parser.add_argument("--frozen-formal-evaluator", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    run_audit(parser.parse_args())


if __name__ == "__main__":
    main()
