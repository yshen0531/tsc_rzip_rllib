#!/usr/bin/env python3
"""Audit the complementary R3c3 + T1 + T2 eight-basis upper bound."""

from __future__ import annotations

import argparse
import copy
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
    stage4_2r3c3t2_post_contract_neutralized_held_transport_identification
    as t2,
)


EXPECTED_SIX_BUILDER_SHA256 = (
    "62c748de11956b468b73dd0ae3937ce2a19b6f241da7281b0fe5e7cd0425f2ab"
)
EXPECTED_FROZEN_FEASIBILITY_TOOL_SHA256 = (
    "7b7b3d15b770efaa9a6d648aa69e4dfb35dbdb596c34dc8d6e38fdfba65f31b2"
)
EXPECTED_SIX_MANIFEST_SHA256 = (
    "46bc47cfc1b8fb779b9ed1308e1d322364e80e780e8596e58e9b9cdc5d0dc2b5"
)
EXPECTED_SIX_AUDIT_BANK_SHA256 = (
    "0ef668da87d97012c101245556ee268b00cac535011b6025aa3fecc82bbb6081"
)
EXPECTED_SIX_CONTROLLER_BANK_SHA256 = (
    "81e3c309d9055ba23587f4162641692680464d465f68342a845184e03b53b2fe"
)
EXPECTED_SIX_FEASIBILITY_SHA256 = (
    "1c74a6c1ef05ff447eb1030f7a7ef1e13390eacfc74e795a556899405c95eacb"
)
EXPECTED_T1_SERVER_AUDIT_SHA256 = (
    "0f24b44f32493b390832474d5c78cc2455a8ba0c455b496b16c04f8deaf3a2bd"
)
EXPECTED_T1_RAW_COUNT = 128
EXPECTED_T1_RAW_DIGEST = (
    "f19a04dcb6b597e97517482d602a6cfdb3c0a1f0b4bfd7a1507b90ae2cc0876f"
)
EXPECTED_T2_RAW_DIGEST = (
    "e40dbf9b531886344bd97a18590db342897570ec8f21b18a37d16c4fb528c90f"
)
EXPECTED_BASELINE_DIGEST = (
    "3e82504dde79215ed34626531e4f926f5bd65404832790cba6a2eb2f2cc3a97e"
)
T1_PROBE_IDS = ("transport_mode0", "transport_mode1")
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


def _context_key(spec: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        str(spec["pair_id"]),
        str(spec["history_member"]),
        str(spec["target_id"]),
        int(spec["action_delay_steps"]),
        float(spec["slew_scale"]),
    )


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


def _optimize_context_n(
    evaluator: Any,
    baseline: np.ndarray,
    columns: Sequence[np.ndarray],
) -> dict[str, Any]:
    basis_count = len(columns)
    if basis_count != 8:
        raise ValueError("eight-basis optimizer received wrong basis count")
    response = np.stack(columns, axis=2)

    def values(coefficients: np.ndarray) -> np.ndarray:
        return baseline + np.tensordot(
            response,
            np.asarray(coefficients, dtype=float),
            axes=(2, 0),
        )

    zero = np.zeros(basis_count)
    zero_margin, zero_row = evaluator.best(values(zero))
    if zero_margin >= -1.0e-12:
        return {
            "passed": True,
            "best_minimum_signed_margin": zero_margin,
            "best_endpoint_step": int(zero_row["endpoint_step"]),
            "best_coefficients": zero.tolist(),
            "active_constraint": str(zero_row["active_constraint"]),
            "method": "exact_baseline_already_passes",
        }

    grid = np.asarray(
        list(
            itertools.product(
                (-1.0, 0.0, 1.0), repeat=basis_count
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
                "exhaustive_ternary_grid",
            )
    if best[0] < -1.0e-12:
        starts = sorted(
            grid_rows, key=lambda row: row[0], reverse=True
        )[:8]
        starts.append((zero_margin, zero, zero_row))
        for endpoint in endpoint_values:
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
                    bounds=[(-1.0, 1.0)] * basis_count,
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
                        "per_endpoint_multistart_slsqp",
                    )
    return {
        "passed": bool(best[0] >= -1.0e-12),
        "best_minimum_signed_margin": float(best[0]),
        "best_endpoint_step": int(best[2]["endpoint_step"]),
        "best_coefficients": np.round(best[1], 12).tolist(),
        "active_constraint": str(best[2]["active_constraint"]),
        "method": best[3],
    }


def _t1_response(
    *,
    plus: Mapping[str, Any],
    minus: Mapping[str, Any],
    plus_path: Path,
    minus_path: Path,
    basis_index: int,
) -> tuple[dict[str, Any], dict[str, Any], np.ndarray, np.ndarray]:
    plus_spec = plus["spec"]
    minus_spec = minus["spec"]
    probe_id = str(plus_spec["r3c3_probe_id"])
    mode = int(plus_spec["r3c3_probe_mode"])
    if (
        probe_id != T1_PROBE_IDS[mode]
        or probe_id != str(minus_spec["r3c3_probe_id"])
        or int(plus_spec["r3c3_probe_sign"]) != 1
        or int(minus_spec["r3c3_probe_sign"]) != -1
        or not math.isclose(
            float(plus_spec["r3c3_probe_amplitude"]),
            0.0075,
            rel_tol=0.0,
            abs_tol=1.0e-15,
        )
    ):
        raise ValueError(f"T1 signed-response identity mismatch: {probe_id}")
    plus_schedule = {
        int(step): np.asarray(value, dtype=float)
        for step, value in plus_spec[
            "r3c3_probe_delta_by_task_issue_step"
        ].items()
    }
    minus_schedule = {
        int(step): np.asarray(value, dtype=float)
        for step, value in minus_spec[
            "r3c3_probe_delta_by_task_issue_step"
        ].items()
    }
    if (
        len(plus_schedule) != 12
        or set(plus_schedule) != set(minus_schedule)
        or any(
            not np.array_equal(plus_schedule[step], -minus_schedule[step])
            for step in plus_schedule
        )
        or not np.allclose(
            sum(plus_schedule.values(), np.zeros(t2.N_MODES)),
            np.zeros(t2.N_MODES),
            rtol=0.0,
            atol=1.0e-12,
        )
    ):
        raise ValueError(f"T1 schedule mismatch: {probe_id}")
    plus_y, plus_v = t2.t1.r3c3._trajectory_arrays(plus, 0.01)
    minus_y, minus_v = t2.t1.r3c3._trajectory_arrays(minus, 0.01)
    if plus_y.shape != minus_y.shape or plus_v.shape != minus_v.shape:
        raise ValueError(f"T1 response shape mismatch: {probe_id}")
    delta_y = (plus_y - minus_y) / 2.0
    delta_v = (plus_v - minus_v) / 2.0
    schedule_rows = [
        [step, plus_schedule[step].tolist()]
        for step in sorted(plus_schedule)
    ]
    common = {
        "basis_index": basis_index,
        "mode_index": mode,
        "amplitude": 0.0075,
        "first_effect_state": int(
            plus_spec["r3c3_probe_first_effect_state"]
        ),
        "positive_schedule_by_task_issue_step": schedule_rows,
        "formal_horizon_steps": len(delta_y) - 1,
        "delta_RZI_by_state": delta_y.tolist(),
        "delta_velocity_RZ_by_state": delta_v.tolist(),
        "temporal_shape": "t1_long_separation_zero_net",
    }
    audit = {
        **copy.deepcopy(common),
        "audit_probe_id": probe_id,
        "plus_file": plus_path.name,
        "plus_sha256": _sha256(plus_path),
        "minus_file": minus_path.name,
        "minus_sha256": _sha256(minus_path),
    }
    return audit, copy.deepcopy(common), delta_y, delta_v


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
    parser.add_argument("--t1-server-audit", required=True, type=Path)
    parser.add_argument("--six-basis-result-dir", required=True, type=Path)
    parser.add_argument("--frozen-six-builder", required=True, type=Path)
    parser.add_argument(
        "--frozen-feasibility-tool", required=True, type=Path
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    output_dir = args.output_dir.expanduser().resolve()
    if output_dir.exists():
        raise SystemExit(f"refusing to overwrite output directory: {output_dir}")
    t2_run = args.t2_run_dir.expanduser().resolve()
    if t2_run == output_dir or t2_run in output_dir.parents:
        raise SystemExit("eight-basis output must remain outside T2 run tree")

    six = _load_exact_module(
        args.frozen_six_builder,
        expected_sha256=EXPECTED_SIX_BUILDER_SHA256,
        name="frozen_t2_six_basis_builder",
    )
    frozen = _load_exact_module(
        args.frozen_feasibility_tool,
        expected_sha256=EXPECTED_FROZEN_FEASIBILITY_TOOL_SHA256,
        name="frozen_t1_feasibility",
    )
    six_dir = args.six_basis_result_dir.expanduser().resolve()
    six_paths = {
        "manifest": (
            six_dir
            / "stage4_2r3c3t2_combined_six_basis_manifest_v1.json"
        ),
        "audit": (
            six_dir
            / "stage4_2r3c3t2_combined_six_basis_audit_bank_v1.json"
        ),
        "controller": (
            six_dir
            / "stage4_2r3c3t2_combined_six_basis_controller_bank_v1.json"
        ),
        "feasibility": (
            six_dir
            / "stage4_2r3c3t2_six_basis_optimistic_feasibility_v1.json"
        ),
    }
    expected_six_hashes = {
        "manifest": EXPECTED_SIX_MANIFEST_SHA256,
        "audit": EXPECTED_SIX_AUDIT_BANK_SHA256,
        "controller": EXPECTED_SIX_CONTROLLER_BANK_SHA256,
        "feasibility": EXPECTED_SIX_FEASIBILITY_SHA256,
    }
    for name, path in six_paths.items():
        if (
            not path.is_file()
            or _sha256(path) != expected_six_hashes[name]
        ):
            raise ValueError(f"authenticated six-basis {name} mismatch")
    six_manifest = json.loads(
        six_paths["manifest"].read_text(encoding="utf-8")
    )
    six_audit = json.loads(
        six_paths["audit"].read_text(encoding="utf-8")
    )
    six_controller = json.loads(
        six_paths["controller"].read_text(encoding="utf-8")
    )
    six_feasibility = json.loads(
        six_paths["feasibility"].read_text(encoding="utf-8")
    )
    if (
        bool(six_manifest["all_preregistered_gates_pass"])
        or bool(six_feasibility["all_preregistered_gates_pass"])
        or int(six_feasibility["optimistic_formal_pass_count"]) != 16
        or int(six_audit["basis_count"]) != 6
        or int(six_controller["basis_count"]) != 6
        or six_audit["t2_raw_inventory"]["digest"]
        != EXPECTED_T2_RAW_DIGEST
    ):
        raise ValueError("six-basis source outcome changed")

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
    t1_audit_path = args.t1_server_audit.expanduser().resolve()
    if (
        not t1_audit_path.is_file()
        or _sha256(t1_audit_path) != EXPECTED_T1_SERVER_AUDIT_SHA256
    ):
        raise ValueError("T1 server audit hash mismatch")
    t1_audit = json.loads(t1_audit_path.read_text(encoding="utf-8"))
    if (
        not bool(t1_audit["raw_and_manifest_integrity_passed"])
        or bool(t1_audit["certified_primary_pass"])
        or int(t1_audit["control_raw_actual"]) != EXPECTED_T1_RAW_COUNT
        or t1_audit["raw_inventory"]["digest"] != EXPECTED_T1_RAW_DIGEST
    ):
        raise ValueError("T1 authenticated source outcome changed")
    t1_raw_dir = ctx.source_ctx.paths.control / "raw"
    t1_paths = sorted(t1_raw_dir.glob("*.json.gz"))
    t1_inventory = six._inventory(t1_paths, relative_to=t1_raw_dir)
    if (
        t1_inventory["n_files"] != EXPECTED_T1_RAW_COUNT
        or t1_inventory["digest"] != EXPECTED_T1_RAW_DIGEST
        or t1_inventory != t1_audit["raw_inventory"]
    ):
        raise ValueError("T1 raw inventory mismatch")
    t1_results = [t2.t1.r3c3.read_json_gz(path) for path in t1_paths]
    t1_result_paths = {
        str(result["experiment_id"]): path
        for result, path in zip(t1_results, t1_paths)
    }
    if (
        len(t1_result_paths) != EXPECTED_T1_RAW_COUNT
        or any(
            not bool(result.get("completed"))
            or not bool(result.get("success"))
            or bool(result.get("failure_reason"))
            or not bool(t2.t1._phase_trace_valid(result)["passed"])
            for result in t1_results
        )
    ):
        raise ValueError("T1 raw execution authentication failed")
    t1_grouped: dict[
        tuple[Any, ...], dict[str, Mapping[str, Any]]
    ] = defaultdict(dict)
    for result in t1_results:
        spec = result["spec"]
        label = (
            f"{spec['r3c3_probe_id']}:{int(spec['r3c3_probe_sign'])}"
        )
        t1_grouped[_context_key(spec)][label] = result

    six_by_key = {
        six._old_context_key(context): context
        for context in six_audit["contexts"]
    }
    expected_t1_labels = {
        f"{probe_id}:{sign}"
        for probe_id in T1_PROBE_IDS
        for sign in (-1, 1)
    }
    if (
        set(t1_grouped) != set(six_by_key)
        or len(six_by_key) != 32
        or any(
            set(group) != expected_t1_labels
            for group in t1_grouped.values()
        )
    ):
        raise ValueError("T1/T2 context-set mismatch")
    numeric_controller = {
        six._numeric_controller_key(sample): sample
        for sample in six_controller["samples"]
    }
    if (
        set(map(six._numeric_audit_key, six_by_key.values()))
        != set(numeric_controller)
    ):
        raise ValueError("six-basis audit/controller mapping mismatch")

    feasibility_contexts = []
    eight_audit_contexts = []
    controller_t1: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    reproduction_rows = []
    condition_rows = []
    for key in sorted(six_by_key):
        source_context = six_by_key[key]
        source_responses = sorted(
            source_context["responses"],
            key=lambda row: int(row["basis_index"]),
        )
        if len(source_responses) != 6:
            raise ValueError(f"six-basis response count mismatch: {key}")
        baseline_id = str(
            source_context["audit_identity"]["baseline_experiment_id"]
        )
        baseline_path = (
            ctx.source_ctx.source_r3c1_run
            / "stage4_2r3c1_authenticated_visible_manifold_control"
            / "raw"
            / f"{baseline_id}.json.gz"
        )
        baseline_result = t2.t1.r3c3.read_json_gz(baseline_path)
        baseline_y, _ = t2.t1.r3c3._trajectory_arrays(
            baseline_result, 0.01
        )
        expected_baseline = np.asarray(
            source_context["offline_design_only_baseline"][
                "RZI_by_state"
            ],
            dtype=float,
        )
        if not np.array_equal(baseline_y, expected_baseline):
            raise ValueError(f"R3c1 baseline mismatch: {key}")
        evaluator = frozen.FormalEvaluator(ctx.source_ctx, baseline_result)
        margin, reproduced = evaluator.best(baseline_y)
        saved = source_context["offline_design_only_baseline"][
            "formal_metrics"
        ]
        saved_margin = float(
            saved["stage3_4_tracking_minimum_signed_margin"]
        )
        saved_pass = bool(saved["stage3_4_target_tracking_pass"])
        reproduction_rows.append(
            {
                "context": list(key),
                "saved_pass": saved_pass,
                "reproduced_pass": bool(margin >= -1.0e-12),
                "saved_margin": saved_margin,
                "reproduced_margin": margin,
                "absolute_margin_error": abs(saved_margin - margin),
                "reproduced_endpoint": int(reproduced["endpoint_step"]),
            }
        )
        t1_audit_responses = []
        t1_controller_responses = []
        t1_position = []
        t1_velocity = []
        for offset, probe_id in enumerate(T1_PROBE_IDS):
            plus = t1_grouped[key][f"{probe_id}:1"]
            minus = t1_grouped[key][f"{probe_id}:-1"]
            audit_response, controller_response, delta_y, delta_v = (
                _t1_response(
                    plus=plus,
                    minus=minus,
                    plus_path=t1_result_paths[str(plus["experiment_id"])],
                    minus_path=t1_result_paths[str(minus["experiment_id"])],
                    basis_index=4 + offset,
                )
            )
            if delta_y.shape != baseline_y.shape:
                raise ValueError(f"T1/baseline horizon mismatch: {key}")
            t1_audit_responses.append(audit_response)
            t1_controller_responses.append(controller_response)
            t1_position.append(delta_y)
            t1_velocity.append(delta_v)
        old_four = source_responses[:4]
        held_two = copy.deepcopy(source_responses[4:])
        for index, response in enumerate(held_two, start=6):
            response["basis_index"] = index
        combined_responses = [
            *copy.deepcopy(old_four),
            *t1_audit_responses,
            *held_two,
        ]
        position_columns = [
            *[
                np.asarray(row["delta_RZI_by_state"], dtype=float)
                for row in old_four
            ],
            *t1_position,
            *[
                np.asarray(row["delta_RZI_by_state"], dtype=float)
                for row in source_responses[4:]
            ],
        ]
        velocity_columns = [
            *[
                np.asarray(
                    row["delta_velocity_RZ_by_state"], dtype=float
                )
                for row in old_four
            ],
            *t1_velocity,
            *[
                np.asarray(
                    row["delta_velocity_RZ_by_state"], dtype=float
                )
                for row in source_responses[4:]
            ],
        ]
        rank, condition = frozen._velocity_condition(velocity_columns)
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
        feasibility_contexts.append(
            {
                "key": key,
                "baseline": baseline_y,
                "evaluator": evaluator,
                "columns": position_columns,
                "saved_baseline_pass": saved_pass,
            }
        )
        updated_context = copy.deepcopy(source_context)
        updated_context["responses"] = combined_responses
        updated_context["basis_count"] = 8
        updated_context["temporal_basis_order"] = [
            "r3c3_early_mode0",
            "r3c3_early_mode1",
            "r3c3_deadline_mode0",
            "r3c3_deadline_mode1",
            "t1_long_separation_mode0",
            "t1_long_separation_mode1",
            "t2_held_transport_mode0",
            "t2_held_transport_mode1",
        ]
        eight_audit_contexts.append(updated_context)
        controller_t1[
            six._numeric_audit_key(source_context)
        ] = t1_controller_responses

    if (
        sum(row["saved_pass"] for row in reproduction_rows) != 16
        or any(
            row["saved_pass"] != row["reproduced_pass"]
            for row in reproduction_rows
        )
        or max(row["absolute_margin_error"] for row in reproduction_rows)
        > 1.0e-12
    ):
        raise ValueError("formal evaluator reproduction failed")

    rows = []
    for context in feasibility_contexts:
        optimized = _optimize_context_n(
            context["evaluator"],
            context["baseline"],
            context["columns"],
        )
        rows.append(
            {
                "pair_id": context["key"][0],
                "history_member": context["key"][1],
                "target_id": context["key"][2],
                "actual_delay_steps": context["key"][3],
                "actual_slew_scale": context["key"][4],
                "saved_baseline_pass": context["saved_baseline_pass"],
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
    condition_pass = sum(row["passed"] for row in condition_rows)
    maximum_condition = max(
        row["condition_number"] for row in condition_rows
    )
    all_gates_pass = bool(
        pass_count == 32
        and repaired == 16
        and regressions == 0
        and condition_pass == 32
    )

    provenance = {
        "stage": "Stage4.2R3c3T3",
        "identity": "eight_basis_temporal_complementarity_audit_v1",
        "six_basis_manifest_sha256": EXPECTED_SIX_MANIFEST_SHA256,
        "six_basis_audit_bank_sha256": EXPECTED_SIX_AUDIT_BANK_SHA256,
        "six_basis_controller_bank_sha256": (
            EXPECTED_SIX_CONTROLLER_BANK_SHA256
        ),
        "t1_server_audit_sha256": EXPECTED_T1_SERVER_AUDIT_SHA256,
        "t1_raw_inventory_digest": EXPECTED_T1_RAW_DIGEST,
        "t2_raw_inventory_digest": EXPECTED_T2_RAW_DIGEST,
        "r3c1_baseline_inventory_digest": EXPECTED_BASELINE_DIGEST,
        "frozen_six_builder_sha256": EXPECTED_SIX_BUILDER_SHA256,
        "frozen_formal_evaluator_sha256": (
            EXPECTED_FROZEN_FEASIBILITY_TOOL_SHA256
        ),
        "coefficient_lower_bound": -1.0,
        "coefficient_upper_bound": 1.0,
        "formal_timing_changed": False,
    }
    provenance_digest = _canonical_digest(provenance)

    combined_samples = []
    for sample in six_controller["samples"]:
        source = sorted(
            sample["basis_responses"],
            key=lambda row: int(row["basis_index"]),
        )
        if len(source) != 6:
            raise ValueError("six-basis controller sample mismatch")
        t1_additions = copy.deepcopy(
            controller_t1[six._numeric_controller_key(sample)]
        )
        held = copy.deepcopy(source[4:])
        for index, response in enumerate(held, start=6):
            response["basis_index"] = index
        updated = copy.deepcopy(sample)
        updated["basis_responses"] = [
            *copy.deepcopy(source[:4]),
            *t1_additions,
            *held,
        ]
        if [
            int(response["basis_index"])
            for response in updated["basis_responses"]
        ] != list(range(8)):
            raise ValueError("eight-basis controller ordering mismatch")
        combined_samples.append(updated)
    controller_bank = copy.deepcopy(six_controller)
    controller_bank.update(
        {
            "schema_version": 3,
            "purpose": (
                "authenticated eight-basis temporal-complementarity "
                "development bank"
            ),
            "provenance_digest": provenance_digest,
            "sample_count": 32,
            "basis_count": 8,
            "basis_amplitudes": [
                0.0075,
                0.0075,
                0.0075,
                0.0075,
                0.0075,
                0.0075,
                0.006,
                0.0075,
            ],
            "samples": combined_samples,
            "identification_only": True,
            "demonstration_data": False,
            "independent_confirmation": False,
            "hidden_history_labels_present": False,
        }
    )
    audit_bank = {
        "schema_version": 1,
        "stage": "Stage4.2R3c3T3",
        "purpose": (
            "authenticated audit bank combining four local, two T1 "
            "long-separation, and two T2 held-transport responses"
        ),
        "provenance_contract": provenance,
        "provenance_digest": provenance_digest,
        "t1_raw_inventory": t1_inventory,
        "t2_raw_inventory_digest": EXPECTED_T2_RAW_DIGEST,
        "basis_count": 8,
        "contexts": eight_audit_contexts,
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
                row["absolute_margin_error"]
                for row in reproduction_rows
            ),
            "rows": reproduction_rows,
        },
        "eight_basis_condition_audit": {
            "context_count": len(condition_rows),
            "pass_count": condition_pass,
            "maximum_condition_number": maximum_condition,
            "rows": condition_rows,
        },
        "scientific_guardrails": {
            "formal_timing_changed": False,
            "optimistic_linear_superposition_only": True,
            "real_tsc_executed_by_this_tool": False,
            "probe_trajectories_are_demonstrations": False,
            "bc_dagger_or_rl_allowed": False,
        },
    }
    feasibility = {
        "schema_version": 1,
        "stage": "Stage4.2R3c3T3",
        "identity": "eight_basis_temporal_complementarity_audit_v1",
        "provenance": provenance,
        "provenance_digest": provenance_digest,
        "coefficient_contract": {
            "basis_count": 8,
            "coefficient_lower_bound": -1.0,
            "coefficient_upper_bound": 1.0,
            "formal_timing_changed": False,
            "position_tolerance_m": 0.03,
            "speed_tolerance_m_per_s": 0.1,
        },
        "context_count": len(rows),
        "optimistic_formal_pass_count": pass_count,
        "optimistic_formal_failure_count": 32 - pass_count,
        "failed_baseline_repair_count": repaired,
        "baseline_pass_regression_count": regressions,
        "eight_basis_condition_pass_count": condition_pass,
        "maximum_condition_number": maximum_condition,
        "all_preregistered_gates_pass": all_gates_pass,
        "context_rows": rows,
        "scientific_classification": {
            "real_tsc_executed_by_this_tool": False,
            "runtime_error": False,
            "statistics_or_reporting_error": False,
            "optimistic_linear_superposition_only": True,
            "r3c4_implementation_authorized": all_gates_pass,
            "r3c4_real_tsc_execution_authorized": False,
            "bc_dagger_or_rl_allowed": False,
        },
    }

    output_dir.mkdir(parents=True, exist_ok=False)
    audit_output = (
        output_dir / "stage4_2r3c3t3_eight_basis_audit_bank_v1.json"
    )
    controller_output = (
        output_dir / "stage4_2r3c3t3_eight_basis_controller_bank_v1.json"
    )
    feasibility_output = (
        output_dir / "stage4_2r3c3t3_eight_basis_feasibility_v1.json"
    )
    t2.t1.r3c3.atomic_write_json(audit_output, audit_bank)
    t2.t1.r3c3.atomic_write_json(controller_output, controller_bank)
    t2.t1.r3c3.atomic_write_json(feasibility_output, feasibility)
    manifest_output = (
        output_dir / "stage4_2r3c3t3_eight_basis_manifest_v1.json"
    )
    manifest = {
        "schema_version": 1,
        "stage": "Stage4.2R3c3T3",
        "provenance_digest": provenance_digest,
        "outputs": [
            {
                "path": path.name,
                "size_bytes": int(path.stat().st_size),
                "sha256": _sha256(path),
            }
            for path in (
                audit_output,
                controller_output,
                feasibility_output,
            )
        ],
        "all_preregistered_gates_pass": all_gates_pass,
    }
    t2.t1.r3c3.atomic_write_json(manifest_output, manifest)
    print(
        json.dumps(
            {
                "output_dir": str(output_dir),
                "manifest_sha256": _sha256(manifest_output),
                "audit_bank_sha256": _sha256(audit_output),
                "controller_bank_sha256": _sha256(controller_output),
                "feasibility_sha256": _sha256(feasibility_output),
                "context_count": len(rows),
                "optimistic_formal_pass_count": pass_count,
                "failed_baseline_repair_count": repaired,
                "baseline_pass_regression_count": regressions,
                "condition_pass_count": condition_pass,
                "maximum_condition_number": maximum_condition,
                "all_preregistered_gates_pass": all_gates_pass,
                "r3c4_implementation_authorized": all_gates_pass,
                "real_tsc_executed": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
