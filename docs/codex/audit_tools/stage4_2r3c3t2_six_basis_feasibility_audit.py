#!/usr/bin/env python3
"""Build and audit the authenticated post-T2 six-basis response bank.

This server-side, no-TSC tool authenticates the frozen four-basis R3c3 bank
and all 160 certified T2 raw results.  It derives the two held-transport odd
responses, truncates them only at each unchanged 35/37-step formal horizon,
and invokes the exact corrected T1 optimistic-feasibility implementation.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
from collections import defaultdict
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t2_post_contract_neutralized_held_transport_identification
    as t2,
)


EXPECTED_RUN_NAME = (
    "stage4_2r3c3t2_post_contract_neutralized_held_transport_"
    "identification_20260730_225902"
)
EXPECTED_CONTROLLER_REVISION = (
    "post_contract_neutralized_held_transport_probe_v42r3c3t2_v2"
)
EXPECTED_PACKAGE_REVISION = (
    "r42r3c3t2_post_contract_held_transport_identification_v2h1"
)
EXPECTED_RUNTIME_PACKAGE_DIGEST = (
    "5544b0fe4bc50e03d4dc83183f846c9315db353dcb17c7179371f8fe1b046011"
)
EXPECTED_SERVER_AUDIT_SHA256 = (
    "e96f9538f5878ac745424d783e8f57c5ff41d61220b7d22ea66bfb1a08107d9c"
)
EXPECTED_RAW_COUNT = 160
EXPECTED_RAW_DIGEST = (
    "e40dbf9b531886344bd97a18590db342897570ec8f21b18a37d16c4fb528c90f"
)
EXPECTED_OLD_AUDIT_BANK_SHA256 = (
    "51bb4eeabfc8a4c5cc3983d75469f484a2278e6ef37cf03cf93ac650f9404b32"
)
EXPECTED_OLD_CONTROLLER_BANK_SHA256 = (
    "6610dd4c434497240cb89ef0fbaa40716e42df68168efa66cddb919dd8679cf0"
)
EXPECTED_BASELINE_DIGEST = (
    "3e82504dde79215ed34626531e4f926f5bd65404832790cba6a2eb2f2cc3a97e"
)
EXPECTED_FROZEN_FEASIBILITY_TOOL_SHA256 = (
    "7b7b3d15b770efaa9a6d648aa69e4dfb35dbdb596c34dc8d6e38fdfba65f31b2"
)
EXPECTED_T2_CONDITION_MAXIMUM = 22.89380096837352
MAXIMUM_CONDITION = 25.0
PROBE_IDS = ("held_transport_mode0", "held_transport_mode1")
PROBE_AMPLITUDES = (0.006, 0.0075)


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


def _inventory(paths: Sequence[Path], *, relative_to: Path) -> dict[str, Any]:
    rows = [
        {
            "path": path.relative_to(relative_to).as_posix(),
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


def _old_context_key(context: Mapping[str, Any]) -> tuple[Any, ...]:
    identity = context["audit_identity"]
    return (
        str(identity["pair_id"]),
        str(identity["history_member"]),
        str(identity["target_id"]),
        int(context["actual_delay_steps"]),
        float(context["actual_slew_scale"]),
    )


def _numeric_audit_key(context: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        *tuple(map(float, context["initial_visible"])),
        float(context["target_R_offset_m"]),
        float(context["target_Z_offset_m"]),
        float(context["target_Ip_offset_A"]),
        int(context["actual_delay_steps"]),
        *tuple(map(float, context["actuator_gain_by_mode"])),
        float(context["actual_slew_scale"]),
    )


def _numeric_controller_key(sample: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        float(sample["initial_R_m"]),
        float(sample["initial_Z_m"]),
        float(sample["initial_Ip_A"]),
        *tuple(map(float, sample["initial_coil_currents_A"])),
        float(sample["target_R_offset_m"]),
        float(sample["target_Z_offset_m"]),
        float(sample["target_Ip_offset_A"]),
        int(sample["actuator_delay_steps"]),
        *tuple(map(float, sample["actuator_gain_by_mode"])),
        float(sample["actuator_slew_scale"]),
    )


def _load_frozen_tool(path: Path) -> ModuleType:
    resolved = path.expanduser().resolve()
    if (
        not resolved.is_file()
        or _sha256(resolved) != EXPECTED_FROZEN_FEASIBILITY_TOOL_SHA256
    ):
        raise ValueError("frozen corrected feasibility tool hash mismatch")
    spec = importlib.util.spec_from_file_location(
        "frozen_stage4_2r3c3t1_six_basis_feasibility", resolved
    )
    if spec is None or spec.loader is None:
        raise ValueError("cannot load frozen corrected feasibility tool")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _schedule_rows(spec: Mapping[str, Any]) -> list[list[Any]]:
    return [
        [int(step), list(map(float, value))]
        for step, value in sorted(
            spec["r3c3_probe_delta_by_task_issue_step"].items(),
            key=lambda item: int(item[0]),
        )
    ]


def _signed_response(
    *,
    plus: Mapping[str, Any],
    minus: Mapping[str, Any],
    plus_path: Path,
    minus_path: Path,
    horizon: int,
    basis_index: int,
) -> tuple[dict[str, Any], dict[str, Any], np.ndarray, np.ndarray]:
    plus_spec = plus["spec"]
    minus_spec = minus["spec"]
    probe_id = str(plus_spec["r3c3_probe_id"])
    mode = int(plus_spec["r3c3_probe_mode"])
    if (
        probe_id != str(minus_spec["r3c3_probe_id"])
        or probe_id != PROBE_IDS[mode]
        or int(plus_spec["r3c3_probe_sign"]) != 1
        or int(minus_spec["r3c3_probe_sign"]) != -1
        or not math.isclose(
            float(plus_spec["r3c3_probe_amplitude"]),
            PROBE_AMPLITUDES[mode],
            rel_tol=0.0,
            abs_tol=1.0e-15,
        )
        or float(minus_spec["r3c3_probe_amplitude"])
        != float(plus_spec["r3c3_probe_amplitude"])
        or int(plus_spec["formal_horizon_steps"]) != horizon
        or int(minus_spec["formal_horizon_steps"]) != horizon
    ):
        raise ValueError(f"T2 signed response identity mismatch: {probe_id}")
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
        raise ValueError(f"T2 signed schedule mismatch: {probe_id}")
    plus_y, plus_v = t2._arrays(plus, 0.01)
    minus_y, minus_v = t2._arrays(minus, 0.01)
    if plus_y.shape != (51, 3) or plus_v.shape != (51, 2):
        raise ValueError(f"T2 observation shape mismatch: {probe_id}")
    full_y = (plus_y - minus_y) / 2.0
    full_v = (plus_v - minus_v) / 2.0
    formal_y = full_y[: horizon + 1]
    formal_v = full_v[: horizon + 1]
    common = {
        "basis_index": basis_index,
        "mode_index": mode,
        "audit_probe_id": probe_id,
        "amplitude": PROBE_AMPLITUDES[mode],
        "first_effect_state": 3,
        "positive_effect_states": [3, 4, 5, 6, 7, 8],
        "negative_effect_states": [39, 40, 41, 42, 43, 44],
        "positive_schedule_by_task_issue_step": _schedule_rows(plus_spec),
        "formal_horizon_steps": horizon,
        "delta_RZI_by_state": formal_y.tolist(),
        "delta_velocity_RZ_by_state": formal_v.tolist(),
    }
    audit = {
        **copy.deepcopy(common),
        "plus_file": plus_path.name,
        "plus_sha256": _sha256(plus_path),
        "minus_file": minus_path.name,
        "minus_sha256": _sha256(minus_path),
        "full_observation_horizon_steps": 50,
        "full_delta_RZI_by_state": full_y.tolist(),
        "full_delta_velocity_RZ_by_state": full_v.tolist(),
        "post_contract_neutralization_excluded_from_formal_column": True,
    }
    controller = copy.deepcopy(common)
    controller.pop("audit_probe_id")
    return audit, controller, formal_y, formal_v


def _authenticate_server_audit(path: Path) -> dict[str, Any]:
    if _sha256(path) != EXPECTED_SERVER_AUDIT_SHA256:
        raise ValueError("T2 server audit hash mismatch")
    audit = json.loads(path.read_text(encoding="utf-8"))
    summary = audit["control_summary"]
    if (
        audit.get("controller_revision") != EXPECTED_CONTROLLER_REVISION
        or audit.get("package_revision") != EXPECTED_PACKAGE_REVISION
        or audit.get("runtime_package_fingerprint_digest")
        != EXPECTED_RUNTIME_PACKAGE_DIGEST
        or int(audit.get("control_raw_actual", -1)) != EXPECTED_RAW_COUNT
        or audit["raw_inventory"]["digest"] != EXPECTED_RAW_DIGEST
        or not bool(audit.get("raw_and_manifest_integrity_passed"))
        or not bool(audit.get("reported_summary_exact_on_recomputation"))
        or not bool(audit.get("certified_primary_pass"))
        or int(summary["execution_pass_count"]) != EXPECTED_RAW_COUNT
        or int(summary["combined_condition_pass_count"]) != 32
        or not math.isclose(
            float(summary["maximum_combined_velocity_condition_number"]),
            EXPECTED_T2_CONDITION_MAXIMUM,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        )
    ):
        raise ValueError("T2 certified server audit outcome changed")
    return audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3b-run", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3c3-run", required=True, type=Path)
    parser.add_argument(
        "--source-stage4-2r3c3-bank-dir", required=True, type=Path
    )
    parser.add_argument(
        "--source-stage4-2r3c3t1-run", required=True, type=Path
    )
    parser.add_argument(
        "--source-stage4-2r3c3t1-audit-dir", required=True, type=Path
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--server-audit", required=True, type=Path)
    parser.add_argument("--old-audit-bank", required=True, type=Path)
    parser.add_argument("--old-controller-bank", required=True, type=Path)
    parser.add_argument(
        "--frozen-feasibility-tool", required=True, type=Path
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    run_dir = args.run_dir.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    if run_dir.name != EXPECTED_RUN_NAME:
        raise SystemExit(f"unexpected immutable T2 run: {run_dir}")
    if output_dir.exists():
        raise SystemExit(f"refusing to overwrite output directory: {output_dir}")
    if run_dir == output_dir or run_dir in output_dir.parents:
        raise SystemExit("combined-bank output must remain outside run tree")

    audit_path = args.server_audit.expanduser().resolve()
    old_audit_path = args.old_audit_bank.expanduser().resolve()
    old_controller_path = args.old_controller_bank.expanduser().resolve()
    server_audit = _authenticate_server_audit(audit_path)
    if _sha256(old_audit_path) != EXPECTED_OLD_AUDIT_BANK_SHA256:
        raise ValueError("old R3c3 audit bank hash mismatch")
    if _sha256(old_controller_path) != EXPECTED_OLD_CONTROLLER_BANK_SHA256:
        raise ValueError("old R3c3 controller bank hash mismatch")
    frozen = _load_frozen_tool(args.frozen_feasibility_tool)

    ctx = t2.load_stage42r3c3t2_config(
        args.config,
        source_stage42r3b_run=args.source_stage4_2r3b_run,
        source_stage42r3c3_run=args.source_stage4_2r3c3_run,
        source_stage42r3c3_bank_dir=args.source_stage4_2r3c3_bank_dir,
        source_stage42r3c3t1_run=args.source_stage4_2r3c3t1_run,
        source_stage42r3c3t1_audit_dir=(
            args.source_stage4_2r3c3t1_audit_dir
        ),
        run_dir_override=run_dir,
    )
    manifest = t2.t1.r3c3.read_json(ctx.paths.manifest)
    state = t2.t1.r3c3.read_json(ctx.paths.state)
    if (
        manifest.get("stage") != t2.STAGE
        or manifest.get("controller_revision") != EXPECTED_CONTROLLER_REVISION
        or manifest.get("package_revision") != EXPECTED_PACKAGE_REVISION
        or manifest["deployed_package_fingerprint"]["digest"]
        != EXPECTED_RUNTIME_PACKAGE_DIGEST
        or not bool(state.get("finished"))
        or not bool(state.get("primary_pass"))
        or state.get("phase_status") != "campaign_complete"
    ):
        raise ValueError("T2 run manifest/state authentication failed")

    raw_paths = sorted(ctx.paths.raw.glob("*.json.gz"))
    raw_inventory = _inventory(raw_paths, relative_to=ctx.paths.raw)
    if (
        raw_inventory["n_files"] != EXPECTED_RAW_COUNT
        or raw_inventory["digest"] != EXPECTED_RAW_DIGEST
        or raw_inventory != server_audit["raw_inventory"]
    ):
        raise ValueError("T2 raw inventory mismatch")
    results = [t2.t1.r3c3.read_json_gz(path) for path in raw_paths]
    result_paths = {
        str(result["experiment_id"]): path
        for result, path in zip(results, raw_paths)
    }
    if (
        len(result_paths) != EXPECTED_RAW_COUNT
        or any(
            result.get("stage") != t2.STAGE
            or result.get("controller_revision")
            != EXPECTED_CONTROLLER_REVISION
            or not bool(result.get("completed"))
            or not bool(result.get("success"))
            or bool(result.get("failure_reason"))
            or len(result.get("trajectory") or []) != 51
            or len(result.get("controller_trace") or []) != 50
            or not bool(t2._phase_trace_valid(result)["passed"])
            for result in results
        )
    ):
        raise ValueError("T2 raw execution authentication failed")

    old_audit = json.loads(old_audit_path.read_text(encoding="utf-8"))
    old_controller = json.loads(
        old_controller_path.read_text(encoding="utf-8")
    )
    if (
        old_audit["provenance_contract"][
            "r3c1_baseline_inventory_digest"
        ]
        != EXPECTED_BASELINE_DIGEST
        or int(old_controller["basis_count"]) != 4
        or int(old_controller["sample_count"]) != 32
    ):
        raise ValueError("old R3c3 bank contract mismatch")
    old_by_key = {
        _old_context_key(context): context
        for context in old_audit["contexts"]
    }
    old_controller_by_numeric = {
        _numeric_controller_key(sample): sample
        for sample in old_controller["samples"]
    }
    if (
        len(old_by_key) != 32
        or len(old_controller_by_numeric) != 32
        or set(map(_numeric_audit_key, old_by_key.values()))
        != set(old_controller_by_numeric)
    ):
        raise ValueError("old audit/controller bank mapping mismatch")

    grouped: dict[tuple[Any, ...], dict[str, Mapping[str, Any]]] = (
        defaultdict(dict)
    )
    for result in results:
        spec = result["spec"]
        key = t2._context_key(spec)
        probe_id = str(spec["r3c3_probe_id"])
        label = (
            t2.BASELINE_PROBE_ID
            if probe_id == t2.BASELINE_PROBE_ID
            else f"{probe_id}:{int(spec['r3c3_probe_sign'])}"
        )
        grouped[key][label] = result
    expected_labels = {
        t2.BASELINE_PROBE_ID,
        *{
            f"{probe_id}:{sign}"
            for probe_id in PROBE_IDS
            for sign in (-1, 1)
        },
    }
    if (
        set(grouped) != set(old_by_key)
        or any(set(rows) != expected_labels for rows in grouped.values())
    ):
        raise ValueError("T2/old-bank context coverage mismatch")

    contexts = []
    audit_contexts = []
    controller_additions: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    baseline_identity = []
    reproduction_rows = []
    condition_rows = []
    for key in sorted(old_by_key):
        old_context = old_by_key[key]
        rows = grouped[key]
        if not t2._source_prefix_exact(
            ctx, rows[t2.BASELINE_PROBE_ID]
        ):
            raise ValueError(f"T2 extended baseline prefix mismatch: {key}")
        baseline_id = str(
            old_context["audit_identity"]["baseline_experiment_id"]
        )
        baseline_path = (
            ctx.source_ctx.source_r3c1_run
            / "stage4_2r3c1_authenticated_visible_manifold_control"
            / "raw"
            / f"{baseline_id}.json.gz"
        )
        baseline_result = t2.t1.r3c3.read_json_gz(baseline_path)
        baseline_identity.append(
            {
                "path": baseline_path.name,
                "size_bytes": int(baseline_path.stat().st_size),
                "sha256": _sha256(baseline_path),
            }
        )
        baseline_y, _ = t2.t1.r3c3._trajectory_arrays(
            baseline_result, 0.01
        )
        expected_baseline = np.asarray(
            old_context["offline_design_only_baseline"]["RZI_by_state"],
            dtype=float,
        )
        if not np.array_equal(baseline_y, expected_baseline):
            raise ValueError(f"R3c1 baseline trajectory mismatch: {key}")
        evaluator = frozen.FormalEvaluator(ctx.source_ctx, baseline_result)
        reproduced_margin, reproduced_row = evaluator.best(baseline_y)
        saved = old_context["offline_design_only_baseline"][
            "formal_metrics"
        ]
        saved_pass = bool(saved["stage3_4_target_tracking_pass"])
        reproduced_pass = bool(reproduced_margin >= -1.0e-12)
        reproduction_rows.append(
            {
                "context": list(key),
                "saved_pass": saved_pass,
                "reproduced_pass": reproduced_pass,
                "saved_margin": float(
                    saved["stage3_4_tracking_minimum_signed_margin"]
                ),
                "reproduced_margin": reproduced_margin,
                "absolute_margin_error": abs(
                    float(
                        saved[
                            "stage3_4_tracking_minimum_signed_margin"
                        ]
                    )
                    - reproduced_margin
                ),
                "reproduced_endpoint": int(
                    reproduced_row["endpoint_step"]
                ),
            }
        )
        old_responses = sorted(
            old_context["responses"],
            key=lambda row: int(row["basis_index"]),
        )
        old_position = [
            np.asarray(row["delta_RZI_by_state"], dtype=float)
            for row in old_responses
        ]
        old_velocity = [
            np.asarray(row["delta_velocity_RZ_by_state"], dtype=float)
            for row in old_responses
        ]
        horizon = len(baseline_y) - 1
        audit_additions = []
        controller_rows = []
        new_position = []
        new_velocity = []
        for offset, probe_id in enumerate(PROBE_IDS):
            plus = rows[f"{probe_id}:1"]
            minus = rows[f"{probe_id}:-1"]
            plus_path = result_paths[str(plus["experiment_id"])]
            minus_path = result_paths[str(minus["experiment_id"])]
            audit_response, controller_response, delta_y, delta_v = (
                _signed_response(
                    plus=plus,
                    minus=minus,
                    plus_path=plus_path,
                    minus_path=minus_path,
                    horizon=horizon,
                    basis_index=4 + offset,
                )
            )
            audit_additions.append(audit_response)
            controller_rows.append(controller_response)
            new_position.append(delta_y)
            new_velocity.append(delta_v)
        position_columns = [*old_position, *new_position]
        velocity_columns = [*old_velocity, *new_velocity]
        rank, condition = frozen._velocity_condition(velocity_columns)
        condition_rows.append(
            {
                "context": list(key),
                "matrix_rank": rank,
                "condition_number": condition,
                "passed": bool(
                    rank == 6
                    and math.isfinite(condition)
                    and condition <= MAXIMUM_CONDITION
                ),
            }
        )
        contexts.append(
            {
                "key": key,
                "baseline": baseline_y,
                "evaluator": evaluator,
                "position_columns": position_columns,
                "velocity_columns": velocity_columns,
                "saved_baseline_pass": saved_pass,
            }
        )
        combined_context = copy.deepcopy(old_context)
        combined_context["responses"] = [
            *copy.deepcopy(old_responses),
            *audit_additions,
        ]
        combined_context["basis_count"] = 6
        combined_context[
            "held_transport_formal_prefix_only_for_controller_use"
        ] = True
        audit_contexts.append(combined_context)
        controller_additions[
            _numeric_audit_key(old_context)
        ] = controller_rows

    baseline_digest = _canonical_digest(
        sorted(baseline_identity, key=lambda row: row["path"])
    )
    if baseline_digest != EXPECTED_BASELINE_DIGEST:
        raise ValueError("recomputed R3c1 baseline inventory mismatch")
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
    if (
        sum(row["passed"] for row in condition_rows) != 32
        or not math.isclose(
            max(row["condition_number"] for row in condition_rows),
            EXPECTED_T2_CONDITION_MAXIMUM,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        )
    ):
        raise ValueError("T2 six-basis velocity condition reproduction failed")

    feasibility_rows = []
    for context in contexts:
        optimized = frozen._optimize_context(
            context["evaluator"],
            context["baseline"],
            context["position_columns"],
        )
        feasibility_rows.append(
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
    pass_count = sum(row["passed"] for row in feasibility_rows)
    repaired_count = sum(
        row["passed"] and not row["saved_baseline_pass"]
        for row in feasibility_rows
    )
    regression_count = sum(
        not row["passed"] and row["saved_baseline_pass"]
        for row in feasibility_rows
    )
    all_gates_pass = bool(
        pass_count == 32
        and repaired_count == 16
        and regression_count == 0
        and sum(row["passed"] for row in condition_rows) == 32
    )

    provenance = {
        "stage": "Stage4.2R3c3T2_six_basis_feasibility",
        "t2_run": str(run_dir),
        "t2_server_audit_sha256": _sha256(audit_path),
        "t2_raw_inventory_digest": raw_inventory["digest"],
        "t2_runtime_package_fingerprint_digest": (
            EXPECTED_RUNTIME_PACKAGE_DIGEST
        ),
        "old_audit_bank_sha256": _sha256(old_audit_path),
        "old_controller_bank_sha256": _sha256(old_controller_path),
        "r3c1_baseline_inventory_digest": baseline_digest,
        "frozen_feasibility_tool_sha256": _sha256(
            args.frozen_feasibility_tool.expanduser().resolve()
        ),
        "coefficient_lower_bound": -1.0,
        "coefficient_upper_bound": 1.0,
        "formal_timing_changed": False,
    }
    provenance_digest = _canonical_digest(provenance)

    combined_samples = []
    for sample in old_controller["samples"]:
        numeric_key = _numeric_controller_key(sample)
        additions = controller_additions[numeric_key]
        updated = copy.deepcopy(sample)
        updated["basis_responses"] = [
            *copy.deepcopy(sample["basis_responses"]),
            *copy.deepcopy(additions),
        ]
        if [row["basis_index"] for row in updated["basis_responses"]] != list(
            range(6)
        ):
            raise ValueError("combined controller basis ordering mismatch")
        combined_samples.append(updated)
    controller_bank = copy.deepcopy(old_controller)
    controller_bank.update(
        {
            "schema_version": 2,
            "purpose": (
                "authenticated six-basis development controller bank; "
                "R3c4 implementation only after feasibility pass"
            ),
            "provenance_digest": provenance_digest,
            "sample_count": 32,
            "basis_count": 6,
            "basis_amplitudes": [0.0075] * 4
            + list(PROBE_AMPLITUDES),
            "coefficient_lower_bound": -1.0,
            "coefficient_upper_bound": 1.0,
            "samples": combined_samples,
            "identification_only": True,
            "demonstration_data": False,
            "independent_confirmation": False,
            "hidden_history_labels_present": False,
        }
    )
    controller_bank.pop("amplitude", None)

    audit_bank = {
        "schema_version": 2,
        "purpose": (
            "authenticated audit bank combining frozen R3c3 four-basis "
            "responses with certified T2 held-transport formal prefixes"
        ),
        "provenance_contract": provenance,
        "provenance_digest": provenance_digest,
        "t2_raw_inventory": raw_inventory,
        "r3c1_baseline_inventory": sorted(
            baseline_identity, key=lambda row: row["path"]
        ),
        "basis_count": 6,
        "contexts": audit_contexts,
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
        "six_basis_condition_audit": {
            "context_count": len(condition_rows),
            "pass_count": sum(row["passed"] for row in condition_rows),
            "maximum_condition_number": max(
                row["condition_number"] for row in condition_rows
            ),
            "rows": condition_rows,
        },
        "scientific_guardrails": {
            "formal_timing_changed": False,
            "linear_superposition_is_optimistic_design_model": True,
            "real_tsc_executed_by_this_tool": False,
            "probe_trajectories_are_demonstrations": False,
            "independent_confirmation": False,
            "bc_dagger_or_rl_allowed": False,
        },
    }
    feasibility = {
        "schema_version": 1,
        "stage": "Stage4.2R3c3T2_six_basis_optimistic_feasibility",
        "provenance": provenance,
        "provenance_digest": provenance_digest,
        "formal_evaluator_reproduction": (
            audit_bank["formal_evaluator_reproduction"]
        ),
        "condition_reproduction": (
            audit_bank["six_basis_condition_audit"]
        ),
        "coefficient_contract": {
            "basis_count": 6,
            "coefficient_lower_bound": -1.0,
            "coefficient_upper_bound": 1.0,
            "formal_timing_changed": False,
            "position_tolerance_m": 0.03,
            "speed_tolerance_m_per_s": 0.1,
        },
        "context_count": len(feasibility_rows),
        "optimistic_formal_pass_count": pass_count,
        "optimistic_formal_failure_count": 32 - pass_count,
        "failed_baseline_repair_count": repaired_count,
        "baseline_pass_regression_count": regression_count,
        "six_basis_condition_pass_count": sum(
            row["passed"] for row in condition_rows
        ),
        "maximum_condition_number": max(
            row["condition_number"] for row in condition_rows
        ),
        "all_preregistered_gates_pass": all_gates_pass,
        "context_rows": feasibility_rows,
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
        output_dir
        / "stage4_2r3c3t2_combined_six_basis_audit_bank_v1.json"
    )
    controller_output = (
        output_dir
        / "stage4_2r3c3t2_combined_six_basis_controller_bank_v1.json"
    )
    feasibility_output = (
        output_dir
        / "stage4_2r3c3t2_six_basis_optimistic_feasibility_v1.json"
    )
    t2.t1.r3c3.atomic_write_json(audit_output, audit_bank)
    t2.t1.r3c3.atomic_write_json(controller_output, controller_bank)
    t2.t1.r3c3.atomic_write_json(feasibility_output, feasibility)
    manifest_output = (
        output_dir
        / "stage4_2r3c3t2_combined_six_basis_manifest_v1.json"
    )
    output_manifest = {
        "schema_version": 1,
        "stage": "Stage4.2R3c3T2_six_basis_feasibility",
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
    t2.t1.r3c3.atomic_write_json(manifest_output, output_manifest)
    print(
        json.dumps(
            {
                "output_dir": str(output_dir),
                "manifest_sha256": _sha256(manifest_output),
                "audit_bank_sha256": _sha256(audit_output),
                "controller_bank_sha256": _sha256(controller_output),
                "feasibility_sha256": _sha256(feasibility_output),
                "context_count": len(feasibility_rows),
                "optimistic_formal_pass_count": pass_count,
                "failed_baseline_repair_count": repaired_count,
                "baseline_pass_regression_count": regression_count,
                "condition_pass_count": sum(
                    row["passed"] for row in condition_rows
                ),
                "maximum_condition_number": max(
                    row["condition_number"] for row in condition_rows
                ),
                "all_preregistered_gates_pass": all_gates_pass,
                "r3c4_implementation_authorized": all_gates_pass,
                "real_tsc_executed": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
