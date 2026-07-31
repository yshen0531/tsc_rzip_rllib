#!/usr/bin/env python3
"""Preflight six persistent transport/braking step-response schedules."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, Sequence

import numpy as np


STAGE = "Stage4.2R3c3T11"
IDENTITY = "persistent_transport_braking_step_response_preflight_v1"
SCRIPT_DIR = Path(__file__).resolve().parent
T6_TOOL_PATH = SCRIPT_DIR / "stage4_2r3c3t6_new_direction_preflight.py"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _load_t6_tool(expected_sha256: str) -> ModuleType:
    if _sha256(T6_TOOL_PATH) != expected_sha256:
        raise ValueError("frozen T6 preflight tool hash mismatch")
    spec = importlib.util.spec_from_file_location(
        "stage4_2r3c3t11_frozen_t6_preflight", T6_TOOL_PATH
    )
    if spec is None or spec.loader is None:
        raise ValueError("cannot load frozen T6 preflight tool")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _authenticate(path: Path, expected: str, label: str) -> Mapping[str, Any]:
    if not path.is_file() or _sha256(path) != expected:
        raise ValueError(f"{label} hash mismatch")
    value = _read_json(path)
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} is not a JSON object")
    return value


def _validate_design(cfg: Mapping[str, Any]) -> None:
    source = cfg["source_contract"]
    step = cfg["persistent_step_contract"]
    gate = cfg["action_preflight_gate"]
    real = cfg["prospective_real_identification_contract"]
    timing = cfg["formal_timing_contract"]
    scope = cfg["scientific_scope"]
    if (
        int(cfg.get("schema_version", -1)) != 1
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or source["t3_eight_basis_controller_bank_sha256"]
        != "6328ef4116ea5a2ecac66d04583fb92af7830ad5ff6ea484486524cbd2021e86"
        or list(map(int, step["mode_indices"])) != [0, 1, 2]
        or int(step["transport_first_effect_state"]) != 3
        or int(step["braking_first_effect_state"]) != 17
        or float(step["step_amplitude"]) != 0.0075
        or list(map(int, step["cancellation_effect_states"]))
        != [39, 40, 41, 42, 43, 44]
        or int(step["observation_horizon_steps"]) != 50
        or float(step["maximum_formal_schedule_l2"]) != 0.015
        or float(step["maximum_schedule_component_abs"]) != 0.0075
        or int(step["required_nonzero_issue_count"]) != 7
        or not bool(step["require_exact_zero_net"])
        or float(step["zero_net_atol"]) != 1e-12
        or not bool(step["schedule_depends_only_on_public_delay_slew_and_probe_id"])
        or bool(step["hidden_history_or_pair_label_input_allowed"])
        or bool(step["source_result_or_action_input_allowed"])
        or bool(step["source_or_current_wire_input_allowed"])
        or int(gate["actuator_case_count"]) != 2
        or int(gate["existing_schedule_rank"]) != 12
        or float(gate["maximum_existing_reproduction_error"]) != 1e-12
        or int(gate["new_schedule_count"]) != 6
        or int(gate["new_schedule_rank"]) != 6
        or int(gate["augmented_schedule_rank"]) != 18
        or float(gate["maximum_augmented_normalized_condition_number"])
        != 10.0
        or float(gate["minimum_new_column_residual_norm_outside_existing_span"])
        != 0.25
        or bool(gate["formal_timing_changed"])
        or int(real["context_count"]) != 32
        or int(real["extended_baseline_count"]) != 32
        or int(real["signed_probe_count"]) != 384
        or int(real["total_task_count"]) != 416
        or int(real["probe_basis_count"]) != 6
        or int(real["probe_sign_count"]) != 2
        or float(real["maximum_current_utilization"]) != 0.55
        or float(real["central_symmetry_maximum_even_velocity_rmse_m_per_s"])
        != 0.004
        or float(real["central_symmetry_maximum_even_position_rmse_m"])
        != 0.0005
        or float(real["central_symmetry_maximum_even_ip_rmse_A"]) != 20.0
        or float(real["matched_history_maximum_odd_velocity_rmse_m_per_s"])
        != 0.006
        or float(real["matched_history_maximum_odd_position_rmse_m"]) != 0.001
        or float(real["matched_history_maximum_odd_ip_rmse_A"]) != 40.0
        or int(real["required_response_rank"]) != 6
        or float(real["maximum_response_velocity_condition_number"]) != 25.0
        or bool(real["formal_tracking_is_identification_gate"])
        or bool(real["formal_timing_changed"])
        or int(timing["normal_arrival_deadline_step"]) != 25
        or int(timing["normal_hold_through_step"]) != 35
        or int(timing["weak_arrival_deadline_step"]) != 27
        or int(timing["weak_hold_through_step"]) != 37
        or float(timing["position_tolerance_m"]) != 0.03
        or float(timing["speed_threshold_m_per_s"]) != 0.1
        or not bool(timing["ip_threshold_unchanged"])
        or bool(scope["preflight_executes_real_tsc"])
        or bool(scope["action_schedule_novelty_is_plant_response_validation"])
        or bool(scope["persistent_step_linearization_is_global_nonlinear_validation"])
        or bool(scope["controller_implementation_authorized_by_preflight"])
        or bool(scope["real_tsc_controller_execution_authorized_by_preflight"])
        or bool(scope["probe_trajectories_are_demonstrations"])
        or not bool(scope["development_set_only"])
        or bool(scope["independent_hidden_history_confirmation"])
        or bool(scope["bc_dagger_or_rl_allowed"])
    ):
        raise ValueError("T11 frozen design changed")


def _find_case(
    cases: Sequence[Mapping[str, Any]], delay: int, slew: float
) -> Mapping[str, Any]:
    matches = [
        case
        for case in cases
        if int(case["delay_steps"]) == delay
        and math.isclose(float(case["slew_scale"]), slew, abs_tol=1e-12)
    ]
    if len(matches) != 1:
        raise ValueError("actuator case coverage mismatch")
    return matches[0]


def _formal_schedule(
    probe: Mapping[str, Any], formal_hold_step: int
) -> np.ndarray:
    rows = np.zeros((formal_hold_step, 3), dtype=float)
    for issue, value in probe["formal_issue_schedule"]:
        issue = int(issue)
        if issue < 0 or issue >= formal_hold_step:
            raise ValueError("formal issue outside hold window")
        rows[issue] = np.asarray(value, dtype=float)
    return rows


def _persistent_step_payload(
    *, mode: int, first_effect_state: int, delay: int, cfg: Mapping[str, Any]
) -> dict[str, Any]:
    step = cfg["persistent_step_contract"]
    amplitude = float(step["step_amplitude"])
    vector = np.zeros(3, dtype=float)
    vector[mode] = amplitude
    formal_issue = first_effect_state - delay - 1
    if formal_issue < 0:
        raise ValueError("persistent step issue precedes task start")
    formal = [[formal_issue, vector.tolist()]]
    cancellation = []
    cancellation_vector = -vector / len(step["cancellation_effect_states"])
    for effect in step["cancellation_effect_states"]:
        cancellation.append([int(effect) - delay - 1, cancellation_vector.tolist()])
    full = formal + cancellation
    net = np.sum(np.asarray([row[1] for row in full]), axis=0)
    name = "transport" if first_effect_state == 3 else "braking"
    return {
        "probe_id": f"persistent_{name}_step_mode{mode}",
        "mode_index": mode,
        "first_effect_state": first_effect_state,
        "formal_issue_schedule": formal,
        "cancellation_issue_schedule": cancellation,
        "positive_schedule_by_task_issue_step": full,
        "nonzero_issue_count": len(full),
        "formal_l2_norm": float(np.linalg.norm(vector)),
        "full_l2_norm": float(np.linalg.norm(np.asarray([row[1] for row in full]))),
        "formal_max_abs_component": float(np.max(np.abs(vector))),
        "cancellation_max_abs_component": float(np.max(np.abs(cancellation_vector))),
        "requested_full_net": net.tolist(),
        "first_cancellation_effect_state": int(step["cancellation_effect_states"][0]),
        "last_cancellation_effect_state": int(step["cancellation_effect_states"][-1]),
    }


def _normalized(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=0)
    if np.any(norms <= 1e-14):
        raise ValueError("zero action schedule column")
    return matrix / norms


def build_preflight(args: argparse.Namespace) -> dict[str, Any]:
    config_path = args.config.resolve()
    cfg = _read_json(config_path)
    _validate_design(cfg)
    source = cfg["source_contract"]
    t6_tool = _load_t6_tool(str(source["t6_preflight_tool_sha256"]))
    t6 = _authenticate(args.t6_preflight.resolve(), str(source["t6_preflight_sha256"]), "T6 preflight")
    t9 = _authenticate(args.t9_preflight.resolve(), str(source["t9_preflight_sha256"]), "T9 preflight")
    t10_manifest = _authenticate(args.t10_manifest.resolve(), str(source["t10_manifest_sha256"]), "T10 manifest")
    t10_audit = _authenticate(args.t10_audit.resolve(), str(source["t10_audit_sha256"]), "T10 audit")
    t10_feasibility = _authenticate(args.t10_feasibility.resolve(), str(source["t10_feasibility_sha256"]), "T10 feasibility")
    bank_path = args.eight_basis_bank.resolve()
    bank = _authenticate(
        bank_path,
        str(source["t3_eight_basis_controller_bank_sha256"]),
        "T3 eight-basis controller bank",
    )
    failed_baseline_rows = [
        row
        for row in t10_feasibility["context_rows"]
        if not bool(row["saved_baseline_pass"])
    ]
    failed_baseline_corners = [
        row
        for row in failed_baseline_rows
        if all(math.isclose(abs(float(value)), 1.0, abs_tol=1e-12)
               for value in row["best_coordinates"])
    ]
    if (
        not bool(t6["all_preflight_gates_pass"])
        or not bool(t9["all_preflight_gates_pass"])
        or bool(t10_manifest["all_preregistered_gates_pass"])
        or int(t10_feasibility["optimistic_formal_pass_count"])
        != int(source["t10_required_formal_pass_count"])
        or int(t10_feasibility["failed_baseline_repair_count"])
        != int(source["t10_required_repair_count"])
        or len(failed_baseline_corners)
        != int(source["t10_required_failed_corner_count"])
        or int(t10_audit["model_fit"]["pass_count"]) != 32
        or int(bank["sample_count"]) != 32
        or int(bank["basis_count"]) != 8
    ):
        raise ValueError("authenticated source outcome changed")

    step_cfg = cfg["persistent_step_contract"]
    gate_cfg = cfg["action_preflight_gate"]
    case_rows = []
    for actuator in t6_tool.ACTUATOR_CASES:
        delay = int(actuator["delay_steps"])
        slew = float(actuator["slew_scale"])
        hold = int(actuator["formal_hold_step"])
        old, effective = t6_tool._schedule_matrix(
            bank["samples"],
            delay_steps=delay,
            slew_scale=slew,
            formal_hold_step=hold,
        )
        t6_case = _find_case(t6["actuator_cases"], delay, slew)
        t9_case = _find_case(t9["actuator_cases"], delay, slew)
        t6_columns = [
            _formal_schedule(probe, hold).reshape(-1)
            for probe in t6_case["probe_schedules"]
        ]
        pc3 = _formal_schedule(t9_case["standalone_pc3_probe"], hold).reshape(-1)
        existing = np.column_stack([old, *t6_columns, pc3])
        existing_normalized = _normalized(existing)
        old_rank = int(np.linalg.matrix_rank(existing_normalized))
        old_condition = float(np.linalg.cond(existing_normalized))
        if old_rank != 12:
            raise ValueError("existing 12-column schedule rank changed")
        expected_rank = int(t9_case["complete_augmented_schedule_rank"])
        expected_condition = float(t9_case["complete_augmented_schedule_normalized_condition"])
        reproduction_error = max(abs(old_rank - expected_rank), abs(old_condition - expected_condition))

        probes = []
        new_columns = []
        residual_norms = []
        for first_effect in (
            int(step_cfg["transport_first_effect_state"]),
            int(step_cfg["braking_first_effect_state"]),
        ):
            for mode in map(int, step_cfg["mode_indices"]):
                probe = _persistent_step_payload(
                    mode=mode,
                    first_effect_state=first_effect,
                    delay=delay,
                    cfg=cfg,
                )
                column = _formal_schedule(probe, hold).reshape(-1)
                normalized = column / np.linalg.norm(column)
                projection, *_ = np.linalg.lstsq(
                    existing_normalized, normalized, rcond=None
                )
                residual = normalized - existing_normalized @ projection
                residual_norm = float(np.linalg.norm(residual))
                probe["residual_norm_outside_existing_span"] = residual_norm
                probes.append(probe)
                new_columns.append(column)
                residual_norms.append(residual_norm)
        new_matrix = np.column_stack(new_columns)
        augmented = np.column_stack([existing, new_matrix])
        new_normalized = _normalized(new_matrix)
        augmented_normalized = _normalized(augmented)
        new_rank = int(np.linalg.matrix_rank(new_normalized))
        augmented_rank = int(np.linalg.matrix_rank(augmented_normalized))
        augmented_condition = float(np.linalg.cond(augmented_normalized))
        bounded = all(
            int(probe["nonzero_issue_count"]) == int(step_cfg["required_nonzero_issue_count"])
            and len({int(row[0]) for row in probe["positive_schedule_by_task_issue_step"]})
            == int(step_cfg["required_nonzero_issue_count"])
            and min(int(row[0]) for row in probe["positive_schedule_by_task_issue_step"])
            >= 0
            and max(int(row[0]) for row in probe["positive_schedule_by_task_issue_step"])
            < int(step_cfg["observation_horizon_steps"])
            and float(probe["formal_l2_norm"]) <= float(step_cfg["maximum_formal_schedule_l2"])
            and float(probe["formal_max_abs_component"]) <= float(step_cfg["maximum_schedule_component_abs"])
            and float(probe["cancellation_max_abs_component"]) <= float(step_cfg["maximum_schedule_component_abs"])
            and max(abs(value) for value in probe["requested_full_net"]) <= float(step_cfg["zero_net_atol"])
            for probe in probes
        )
        passed = bool(
            reproduction_error <= float(gate_cfg["maximum_existing_reproduction_error"])
            and new_rank == int(gate_cfg["new_schedule_rank"])
            and augmented_rank == int(gate_cfg["augmented_schedule_rank"])
            and augmented_condition <= float(gate_cfg["maximum_augmented_normalized_condition_number"])
            and min(residual_norms) >= float(gate_cfg["minimum_new_column_residual_norm_outside_existing_span"])
            and bounded
        )
        case_rows.append(
            {
                "delay_steps": delay,
                "slew_scale": slew,
                "formal_hold_step": hold,
                "effective_formal_issue_count": effective,
                "existing_schedule_rank": old_rank,
                "existing_schedule_normalized_condition": old_condition,
                "existing_T9_reproduction_error": reproduction_error,
                "new_schedule_rank": new_rank,
                "augmented_schedule_rank": augmented_rank,
                "augmented_schedule_normalized_condition": augmented_condition,
                "minimum_new_column_residual_norm_outside_existing_span": min(residual_norms),
                "maximum_new_column_residual_norm_outside_existing_span": max(residual_norms),
                "bounded_and_zero_net": bounded,
                "probe_schedules": probes,
                "passed": passed,
            }
        )

    all_pass = bool(
        len(case_rows) == int(gate_cfg["actuator_case_count"])
        and all(row["passed"] for row in case_rows)
    )
    output = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "design_config_sha256": _sha256(config_path),
        "source_hashes": {
            "t6_preflight_tool": _sha256(T6_TOOL_PATH),
            "t6_preflight": _sha256(args.t6_preflight.resolve()),
            "t3_eight_basis_controller_bank": _sha256(bank_path),
            "t9_preflight": _sha256(args.t9_preflight.resolve()),
            "t10_manifest": _sha256(args.t10_manifest.resolve()),
            "t10_audit": _sha256(args.t10_audit.resolve()),
            "t10_feasibility": _sha256(args.t10_feasibility.resolve()),
        },
        "actuator_cases": case_rows,
        "prospective_real_identification_contract": cfg["prospective_real_identification_contract"],
        "formal_timing_contract": cfg["formal_timing_contract"],
        "scientific_scope": cfg["scientific_scope"],
        "all_preflight_gates_pass": all_pass,
        "real_tsc_executed": False,
        "ray_executed": False,
        "gotsc_executed": False,
        "controller_implementation_authorized": False,
        "real_identification_implementation_authorized": all_pass,
        "bc_dagger_or_rl_allowed": False,
    }
    _write_json(args.output.resolve(), output)
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "sha256": _sha256(args.output.resolve()),
                "all_preflight_gates_pass": all_pass,
                "case_count": len(case_rows),
                "maximum_augmented_condition": max(
                    row["augmented_schedule_normalized_condition"] for row in case_rows
                ),
                "minimum_novelty_residual": min(
                    row["minimum_new_column_residual_norm_outside_existing_span"] for row in case_rows
                ),
                "real_tsc_executed": False,
            },
            sort_keys=True,
        )
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--t6-preflight", required=True, type=Path)
    parser.add_argument("--eight-basis-bank", required=True, type=Path)
    parser.add_argument("--t9-preflight", required=True, type=Path)
    parser.add_argument("--t10-manifest", required=True, type=Path)
    parser.add_argument("--t10-audit", required=True, type=Path)
    parser.add_argument("--t10-feasibility", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    build_preflight(parser.parse_args())


if __name__ == "__main__":
    main()
