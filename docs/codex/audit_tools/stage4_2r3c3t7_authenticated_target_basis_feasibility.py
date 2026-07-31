#!/usr/bin/env python3
"""Build and audit the fixed post-T6 target-relevant eight-basis bank."""

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

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t6_target_residual_new_direction_identification as t6,
)


STAGE = "Stage4.2R3c3T7"
IDENTITY = "authenticated_target_residual_global_eight_basis_feasibility_v1"
T6_RUN_MANIFEST = "stage4_2r3c3t6_manifest.json"
T6_STATE = "stage4_2r3c3t6_state.json"
T6_CONTROL = "stage4_2r3c3t6_target_residual_identification"
T6_SUMMARY = f"{T6_CONTROL}/summary.json"
T6_COMBINED = f"{T6_CONTROL}/combined_condition_number_results.json"
T6_RAW = f"{T6_CONTROL}/raw"
T6_SERVER_AUDIT = "stage4_2r3c3t6_server_audit.json"
T3_MANIFEST = "stage4_2r3c3t3_eight_basis_manifest_v1.json"
T3_AUDIT_BANK = "stage4_2r3c3t3_eight_basis_audit_bank_v1.json"
T3_CONTROLLER_BANK = "stage4_2r3c3t3_eight_basis_controller_bank_v1.json"
T3_FEASIBILITY = "stage4_2r3c3t3_eight_basis_feasibility_v1.json"


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


def _validate_design(cfg: Mapping[str, Any]) -> None:
    gate = cfg["acceptance_gate"]
    scope = cfg["scientific_scope"]
    selection = cfg["selection_policy"]
    if (
        int(cfg.get("schema_version", -1)) != 1
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("selected_t3_basis_indices") != [0, 1, 2, 3, 7]
        or tuple(cfg.get("selected_t6_probe_ids", ())) != t6.PROBE_IDS
        or int(selection["candidate_pool_size"]) != 11
        or int(selection["selected_basis_count"]) != 8
        or not bool(selection["same_global_subset_for_all_contexts"])
        or bool(selection["hidden_history_label_conditioning_allowed"])
        or bool(selection["pair_label_conditioning_allowed"])
        or bool(selection["posthoc_column_scaling_allowed"])
        or int(gate["context_count"]) != 32
        or int(gate["baseline_formal_pass_count"]) != 16
        or int(gate["required_rank"]) != 8
        or float(gate["maximum_velocity_condition_number"]) != 25.0
        or int(gate["condition_pass_count"]) != 32
        or int(gate["optimistic_formal_pass_count"]) != 32
        or int(gate["failed_baseline_repair_count"]) != 16
        or int(gate["baseline_pass_regression_count"]) != 0
        or float(gate["coefficient_lower_bound"]) != -1.0
        or float(gate["coefficient_upper_bound"]) != 1.0
        or bool(gate["formal_timing_changed"])
        or not bool(scope["development_set_only"])
        or not bool(scope["optimistic_linear_superposition_only"])
        or bool(scope["real_tsc_executed"])
        or bool(scope["probe_trajectories_are_demonstrations"])
        or bool(scope["bc_dagger_or_rl_allowed"])
    ):
        raise ValueError("T7 frozen design changed")


def _response_from_signed_pair(
    plus: Mapping[str, Any],
    minus: Mapping[str, Any],
    plus_path: Path,
    minus_path: Path,
    *,
    probe_id: str,
    basis_index: int,
    horizon: int,
) -> tuple[dict[str, Any], dict[str, Any], np.ndarray, np.ndarray]:
    plus_spec = plus["spec"]
    minus_spec = minus["spec"]
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
        str(plus_spec["r3c3_probe_id"]) != probe_id
        or str(minus_spec["r3c3_probe_id"]) != probe_id
        or int(plus_spec["r3c3_probe_sign"]) != 1
        or int(minus_spec["r3c3_probe_sign"]) != -1
        or set(plus_schedule) != set(minus_schedule)
        or len(plus_schedule) != 41
        or any(
            not np.array_equal(
                plus_schedule[step], -minus_schedule[step]
            )
            for step in plus_schedule
        )
        or not np.allclose(
            sum(plus_schedule.values(), np.zeros(t6.N_MODES)),
            np.zeros(t6.N_MODES),
            rtol=0.0,
            atol=1.0e-12,
        )
    ):
        raise ValueError(f"T7 signed response identity mismatch: {probe_id}")
    plus_y, plus_v = t6._arrays(plus, 0.01)
    minus_y, minus_v = t6._arrays(minus, 0.01)
    if plus_y.shape != minus_y.shape or plus_v.shape != minus_v.shape:
        raise ValueError(f"T7 signed response shape mismatch: {probe_id}")
    delta_y = ((plus_y - minus_y) / 2.0)[: horizon + 1]
    delta_v = ((plus_v - minus_v) / 2.0)[: horizon + 1]
    common = {
        "basis_index": basis_index,
        "basis_id": probe_id,
        "mode_index": -2,
        "amplitude": float(plus_spec["r3c3_probe_amplitude"]),
        "first_effect_state": int(
            plus_spec["r3c3_probe_first_effect_state"]
        ),
        "positive_schedule_by_task_issue_step": [
            [step, plus_schedule[step].tolist()]
            for step in sorted(plus_schedule)
        ],
        "formal_horizon_steps": horizon,
        "delta_RZI_by_state": delta_y.tolist(),
        "delta_velocity_RZ_by_state": delta_v.tolist(),
        "temporal_shape": f"t6_{probe_id}",
    }
    audit = {
        **copy.deepcopy(common),
        "plus_file": plus_path.name,
        "plus_sha256": _sha256(plus_path),
        "minus_file": minus_path.name,
        "minus_sha256": _sha256(minus_path),
    }
    return audit, copy.deepcopy(common), delta_y, delta_v


def _condition(columns: Sequence[np.ndarray]) -> tuple[int, float]:
    matrix = np.stack(
        [
            np.asarray(column, dtype=float)[3:, :2].reshape(-1)
            for column in columns
        ],
        axis=1,
    )
    return int(np.linalg.matrix_rank(matrix)), float(np.linalg.cond(matrix))


def _select_global_subset(
    matrices: Sequence[np.ndarray], *, size: int, maximum: float
) -> dict[str, Any]:
    candidates = []
    for indices in itertools.combinations(range(11), size):
        rows = []
        for matrix in matrices:
            selected = matrix[:, indices]
            rank = int(np.linalg.matrix_rank(selected))
            condition = float(np.linalg.cond(selected))
            rows.append((rank, condition))
        passed = sum(
            rank == size and math.isfinite(condition)
            and condition <= maximum
            for rank, condition in rows
        )
        worst = max(condition for _, condition in rows)
        mean = sum(condition for _, condition in rows) / len(rows)
        candidates.append(((-passed, worst, mean, indices), rows))
    (score, rows) = min(candidates, key=lambda item: item[0])
    return {
        "indices": list(score[3]),
        "pass_count": -int(score[0]),
        "worst_condition_number": float(score[1]),
        "mean_condition_number": float(score[2]),
        "minimum_rank": min(rank for rank, _ in rows),
    }


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--design-config", required=True, type=Path)
    parser.add_argument("--t6-config", required=True, type=Path)
    parser.add_argument("--t6-run-dir", required=True, type=Path)
    parser.add_argument("--t6-audit-dir", required=True, type=Path)
    parser.add_argument("--t3-result-dir", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3b-run", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3c3-run", required=True, type=Path)
    parser.add_argument(
        "--source-stage4-2r3c3-bank-dir", required=True, type=Path
    )
    parser.add_argument("--source-stage4-2r3c3t1-run", required=True, type=Path)
    parser.add_argument(
        "--source-stage4-2r3c3t1-audit-dir", required=True, type=Path
    )
    parser.add_argument("--frozen-t3-tool", required=True, type=Path)
    parser.add_argument("--frozen-formal-evaluator", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    output = args.output_dir.expanduser().resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite output directory: {output}")
    design_path = args.design_config.expanduser().resolve()
    cfg = _read_json(design_path)
    _validate_design(cfg)
    source = cfg["source_contract"]
    gate = cfg["acceptance_gate"]

    t6_run = args.t6_run_dir.expanduser().resolve()
    t6_audit_dir = args.t6_audit_dir.expanduser().resolve()
    t3_dir = args.t3_result_dir.expanduser().resolve()
    exact_paths = {
        "t6_run_manifest_sha256": t6_run / T6_RUN_MANIFEST,
        "t6_state_sha256": t6_run / T6_STATE,
        "t6_summary_sha256": t6_run / T6_SUMMARY,
        "t6_combined_condition_sha256": t6_run / T6_COMBINED,
        "t6_server_audit_sha256": t6_audit_dir / T6_SERVER_AUDIT,
        "t3_manifest_sha256": t3_dir / T3_MANIFEST,
        "t3_audit_bank_sha256": t3_dir / T3_AUDIT_BANK,
        "t3_controller_bank_sha256": t3_dir / T3_CONTROLLER_BANK,
        "t3_feasibility_sha256": t3_dir / T3_FEASIBILITY,
    }
    for field, path in exact_paths.items():
        if not path.is_file() or _sha256(path) != str(source[field]):
            raise ValueError(f"T7 authenticated input mismatch: {field}")
    if _sha256(Path(t6.__file__).resolve()) != str(
        source["t6_runtime_source_sha256"]
    ):
        raise ValueError("T7 installed T6 source mismatch")

    t3_tool = _load_module(
        args.frozen_t3_tool,
        str(source["frozen_t3_tool_sha256"]),
        "frozen_t3_audit",
    )
    formal = _load_module(
        args.frozen_formal_evaluator,
        str(source["frozen_formal_evaluator_sha256"]),
        "frozen_formal_evaluator",
    )
    server_audit = _read_json(exact_paths["t6_server_audit_sha256"])
    summary = _read_json(exact_paths["t6_summary_sha256"])
    manifest = _read_json(exact_paths["t6_run_manifest_sha256"])
    if (
        not bool(server_audit["raw_and_manifest_integrity_passed"])
        or not bool(server_audit["reported_summary_exact_on_recomputation"])
        or bool(server_audit["certified_primary_pass"])
        or int(server_audit["control_raw_actual"])
        != int(source["t6_raw_count"])
        or server_audit["raw_inventory"]["digest"]
        != source["t6_raw_inventory_digest"]
        or server_audit["runtime_package_fingerprint_digest"]
        != source["t6_runtime_package_digest"]
        or not bool(summary["execution_gate_passed"])
        or not bool(summary["central_symmetry_gate_passed"])
        or not bool(summary["matched_hidden_history_gate_passed"])
        or not bool(summary["condition_number_gate_passed"])
        or bool(summary["combined_condition_number_gate_passed"])
        or int(summary["combined_condition_pass_count"]) != 2
        or "semantics_preserving_summary_hotfix" not in manifest
    ):
        raise ValueError("T7 T6 scientific source outcome changed")

    raw_dir = t6_run / T6_RAW
    raw_paths = sorted(raw_dir.glob("*.json.gz"))
    raw_inventory = _inventory(raw_paths, raw_dir)
    if (
        raw_inventory != server_audit["raw_inventory"]
        or raw_inventory["n_files"] != int(source["t6_raw_count"])
    ):
        raise ValueError("T7 T6 raw inventory mismatch")
    results = [_read_json_gz(path) for path in raw_paths]
    result_paths = {
        str(result["experiment_id"]): path
        for result, path in zip(results, raw_paths)
    }
    if (
        len(result_paths) != len(results)
        or any(
            not bool(result.get("completed"))
            or not bool(result.get("success"))
            or bool(result.get("failure_reason"))
            for result in results
        )
    ):
        raise ValueError("T7 T6 raw execution authentication failed")
    grouped: dict[
        tuple[Any, ...], dict[tuple[str, int], Mapping[str, Any]]
    ] = defaultdict(dict)
    for result in results:
        spec = result["spec"]
        label = (
            str(spec["r3c3_probe_id"]),
            int(spec["r3c3_probe_sign"]),
        )
        grouped[_context_key(spec)][label] = result
    expected_labels = {(t6.BASELINE_PROBE_ID, 0)} | {
        (probe, sign) for probe in t6.PROBE_IDS for sign in (-1, 1)
    }
    if (
        len(grouped) != 32
        or any(set(members) != expected_labels for members in grouped.values())
    ):
        raise ValueError("T7 T6 context coverage mismatch")

    t3_audit = _read_json(exact_paths["t3_audit_bank_sha256"])
    t3_controller = _read_json(exact_paths["t3_controller_bank_sha256"])
    t3_feasibility = _read_json(exact_paths["t3_feasibility_sha256"])
    if (
        int(t3_audit["basis_count"]) != 8
        or int(t3_controller["basis_count"]) != 8
        or int(t3_feasibility["optimistic_formal_pass_count"]) != 16
        or int(t3_feasibility["failed_baseline_repair_count"]) != 0
        or int(t3_feasibility["eight_basis_condition_pass_count"]) != 11
        or bool(t3_feasibility["all_preregistered_gates_pass"])
    ):
        raise ValueError("T7 T3 source outcome changed")
    audit_by_key = {
        _audit_context_key(context): context
        for context in t3_audit["contexts"]
    }
    controller_by_key = {
        t6._t3_sample_key(sample): sample
        for sample in t3_controller["samples"]
    }
    if (
        set(audit_by_key) != set(grouped)
        or len(controller_by_key) != len(grouped)
    ):
        raise ValueError("T7 T3/T6 context-set mismatch")

    ctx = t6.load_stage42r3c3t6_config(
        args.t6_config,
        source_stage42r3b_run=args.source_stage4_2r3b_run,
        source_stage42r3c3_run=args.source_stage4_2r3c3_run,
        source_stage42r3c3_bank_dir=args.source_stage4_2r3c3_bank_dir,
        source_stage42r3c3t1_run=args.source_stage4_2r3c3t1_run,
        source_stage42r3c3t1_audit_dir=args.source_stage4_2r3c3t1_audit_dir,
        source_stage42r3c3t3_controller_bank=(
            t3_dir / T3_CONTROLLER_BANK
        ),
        run_dir_override=t6_run,
    )
    selected_old = [int(x) for x in cfg["selected_t3_basis_indices"]]
    selected_full = [*selected_old, 8, 9, 10]
    audit_contexts = []
    controller_samples = []
    feasibility_inputs = []
    condition_rows = []
    reproduction_rows = []
    full_matrices = []
    for key in sorted(grouped):
        members = grouped[key]
        baseline = members[(t6.BASELINE_PROBE_ID, 0)]
        horizon = t6._formal_horizon(float(key[4]))
        baseline_y, _ = t6._arrays(baseline, 0.01)
        baseline_y = baseline_y[: horizon + 1]
        source_context = audit_by_key[key]
        saved_baseline = np.asarray(
            source_context["offline_design_only_baseline"]["RZI_by_state"],
            dtype=float,
        )
        if not np.array_equal(baseline_y, saved_baseline):
            raise ValueError(f"T7 baseline prefix mismatch: {key}")
        controller_sample = controller_by_key.get(
            t6._result_sample_key(baseline)
        )
        if controller_sample is None:
            raise ValueError(f"T7 controller sample mismatch: {key}")
        old_audit = sorted(
            source_context["responses"],
            key=lambda row: int(row["basis_index"]),
        )
        old_controller = sorted(
            controller_sample["basis_responses"],
            key=lambda row: int(row["basis_index"]),
        )
        if len(old_audit) != 8 or len(old_controller) != 8:
            raise ValueError(f"T7 old basis count mismatch: {key}")
        selected_audit = []
        selected_controller = []
        position_columns = []
        velocity_columns = []
        all_velocity_columns = []
        for index, response in enumerate(old_audit):
            audit_y = np.asarray(response["delta_RZI_by_state"], dtype=float)
            audit_v = np.asarray(
                response["delta_velocity_RZ_by_state"], dtype=float
            )
            all_velocity_columns.append(audit_v)
            if index in selected_old:
                new_index = len(selected_audit)
                audit_copy = copy.deepcopy(response)
                controller_copy = copy.deepcopy(old_controller[index])
                audit_copy["basis_index"] = new_index
                controller_copy["basis_index"] = new_index
                if (
                    audit_copy["delta_RZI_by_state"]
                    != controller_copy["delta_RZI_by_state"]
                    or audit_copy["delta_velocity_RZ_by_state"]
                    != controller_copy["delta_velocity_RZ_by_state"]
                ):
                    raise ValueError(f"T7 audit/controller response mismatch: {key}")
                selected_audit.append(audit_copy)
                selected_controller.append(controller_copy)
                position_columns.append(audit_y)
                velocity_columns.append(audit_v)
        for probe_id in t6.PROBE_IDS:
            plus = members[(probe_id, 1)]
            minus = members[(probe_id, -1)]
            audit_response, controller_response, delta_y, delta_v = (
                _response_from_signed_pair(
                    plus,
                    minus,
                    result_paths[str(plus["experiment_id"])],
                    result_paths[str(minus["experiment_id"])],
                    probe_id=probe_id,
                    basis_index=len(selected_audit),
                    horizon=horizon,
                )
            )
            selected_audit.append(audit_response)
            selected_controller.append(controller_response)
            position_columns.append(delta_y)
            velocity_columns.append(delta_v)
            all_velocity_columns.append(delta_v)
        full_matrix = np.stack(
            [
                np.asarray(column)[3:, :2].reshape(-1)
                for column in all_velocity_columns
            ],
            axis=1,
        )
        full_matrices.append(full_matrix)
        rank, condition = _condition(velocity_columns)
        condition_rows.append(
            {
                "context": list(key),
                "matrix_rank": rank,
                "condition_number": condition,
                "passed": bool(
                    rank == int(gate["required_rank"])
                    and math.isfinite(condition)
                    and condition
                    <= float(gate["maximum_velocity_condition_number"])
                ),
            }
        )
        short_baseline = copy.deepcopy(baseline)
        short_baseline["trajectory"] = short_baseline["trajectory"][
            : horizon + 1
        ]
        evaluator = formal.FormalEvaluator(
            ctx.base_ctx.source_ctx, short_baseline
        )
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
        feasibility_inputs.append(
            {
                "key": key,
                "baseline": baseline_y,
                "evaluator": evaluator,
                "columns": position_columns,
                "saved_baseline_pass": saved_pass,
            }
        )
        audit_context = copy.deepcopy(source_context)
        audit_context["responses"] = selected_audit
        audit_context["basis_count"] = 8
        audit_context["basis_order"] = cfg["selected_basis_ids"]
        audit_contexts.append(audit_context)
        sample = copy.deepcopy(controller_sample)
        sample["basis_responses"] = selected_controller
        sample["basis_count"] = 8
        controller_samples.append(sample)

    if (
        sum(row["saved_pass"] for row in reproduction_rows) != 16
        or any(
            row["saved_pass"] != row["reproduced_pass"]
            for row in reproduction_rows
        )
        or max(row["absolute_margin_error"] for row in reproduction_rows)
        > 1.0e-12
    ):
        raise ValueError("T7 formal baseline reproduction failed")
    selection = _select_global_subset(
        full_matrices,
        size=8,
        maximum=float(gate["maximum_velocity_condition_number"]),
    )
    expected_worst = float(
        cfg["selection_policy"][
            "expected_selected_worst_condition_number"
        ]
    )
    if (
        selection["indices"] != selected_full
        or selection["pass_count"] != 32
        or abs(selection["worst_condition_number"] - expected_worst)
        > 1.0e-12
    ):
        raise ValueError("T7 deterministic global subset changed")

    rows = []
    for context in feasibility_inputs:
        optimized = t3_tool._optimize_context_n(
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
        pass_count == int(gate["optimistic_formal_pass_count"])
        and repaired == int(gate["failed_baseline_repair_count"])
        and regressions == int(gate["baseline_pass_regression_count"])
        and condition_pass == int(gate["condition_pass_count"])
    )
    provenance = {
        "stage": STAGE,
        "identity": IDENTITY,
        "design_config_sha256": _sha256(design_path),
        **copy.deepcopy(source),
        "selected_basis_ids": copy.deepcopy(cfg["selected_basis_ids"]),
        "selected_global_indices": selected_full,
        "coefficient_lower_bound": -1.0,
        "coefficient_upper_bound": 1.0,
        "formal_timing_changed": False,
    }
    provenance_digest = _canonical_digest(provenance)
    controller_bank = copy.deepcopy(t3_controller)
    controller_bank.update(
        {
            "schema_version": 4,
            "stage": STAGE,
            "purpose": "authenticated target-relevant global eight-basis development bank",
            "provenance_digest": provenance_digest,
            "sample_count": 32,
            "basis_count": 8,
            "basis_order": copy.deepcopy(cfg["selected_basis_ids"]),
            "samples": controller_samples,
            "identification_only": True,
            "demonstration_data": False,
            "development_set_only": True,
            "independent_confirmation": False,
            "hidden_history_labels_present": False,
        }
    )
    audit_bank = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "provenance": provenance,
        "provenance_digest": provenance_digest,
        "raw_inventory": raw_inventory,
        "selection_reproduction": selection,
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
        "condition_audit": {
            "context_count": len(condition_rows),
            "pass_count": condition_pass,
            "maximum_condition_number": maximum_condition,
            "rows": condition_rows,
        },
        "basis_count": 8,
        "contexts": audit_contexts,
        "scientific_guardrails": {
            **copy.deepcopy(cfg["scientific_scope"]),
            "formal_timing_changed": False,
        },
    }
    feasibility = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "provenance": provenance,
        "provenance_digest": provenance_digest,
        "selection_reproduction": selection,
        "coefficient_contract": copy.deepcopy(gate),
        "context_count": len(rows),
        "optimistic_formal_pass_count": pass_count,
        "optimistic_formal_failure_count": 32 - pass_count,
        "failed_baseline_repair_count": repaired,
        "baseline_pass_regression_count": regressions,
        "condition_pass_count": condition_pass,
        "maximum_condition_number": maximum_condition,
        "all_preregistered_gates_pass": all_gates_pass,
        "context_rows": rows,
        "scientific_classification": {
            "real_tsc_executed_by_this_tool": False,
            "runtime_error": False,
            "statistics_or_reporting_error": False,
            "optimistic_linear_superposition_only": True,
            "next_restart_mpc_implementation_authorized": all_gates_pass,
            "real_tsc_controller_execution_authorized": False,
            "probe_trajectories_are_demonstrations": False,
            "bc_dagger_or_rl_allowed": False,
        },
    }

    output.mkdir(parents=True, exist_ok=False)
    audit_output = output / "stage4_2r3c3t7_audit_bank_v1.json"
    controller_output = output / "stage4_2r3c3t7_controller_bank_v1.json"
    feasibility_output = output / "stage4_2r3c3t7_feasibility_v1.json"
    _write_json(audit_output, audit_bank)
    _write_json(controller_output, controller_bank)
    _write_json(feasibility_output, feasibility)
    manifest_output = output / "stage4_2r3c3t7_manifest_v1.json"
    manifest_output_value = {
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
            for path in (
                audit_output,
                controller_output,
                feasibility_output,
            )
        ],
        "all_preregistered_gates_pass": all_gates_pass,
    }
    _write_json(manifest_output, manifest_output_value)
    print(
        json.dumps(
            {
                "output_dir": str(output),
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
                "next_restart_mpc_implementation_authorized": (
                    all_gates_pass
                ),
                "real_tsc_executed": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
