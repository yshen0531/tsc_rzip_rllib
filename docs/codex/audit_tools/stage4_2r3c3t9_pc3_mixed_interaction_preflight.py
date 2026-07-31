#!/usr/bin/env python3
"""Preflight a new PC3 direction and a direct mixed-action T9 design.

This tool authenticates the same R17, R3c1, T3, T6, T7, and T8 evidence
used by the preceding stages.  It adds the third equal-context target-action
principal direction outside the complete T6 eleven-schedule span.

It also freezes a label-independent 2x2 signed factorial:

    (+/- measured T7 failure-stress schedule)
    x (+/- new PC3 schedule)

The four combinations are direct mixed-action probes.  The tool only writes a
compact preflight JSON and never invokes Ray, gotsc, or TSC.
"""

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


SCRIPT_DIR = Path(__file__).resolve().parent
T6_PREFLIGHT_TOOL = (
    SCRIPT_DIR / "stage4_2r3c3t6_new_direction_preflight.py"
)
T7_SELECTED_OLD_INDICES = (0, 1, 2, 3, 7)
T6_PROBE_IDS = (
    "r17_target_action_residual",
    "matched_visible_target_equal_pc1",
    "matched_visible_target_equal_pc2",
)
FACTORIAL_SIGNS = ((1, 1), (1, -1), (-1, 1), (-1, -1))
ORTHOGONALITY_TOLERANCE = 1.0e-12
ZERO_NET_TOLERANCE = 1.0e-12


def _load_t6_tool() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "stage4_2r3c3t6_new_direction_preflight_for_t9",
        T6_PREFLIGHT_TOOL,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen T6 preflight tool")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


T6 = _load_t6_tool()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _validate_design(design: Mapping[str, Any]) -> None:
    if int(design["schema_version"]) != 1:
        raise ValueError("T9 design schema changed")
    if str(design["stage"]) != "Stage4.2R3c3T9":
        raise ValueError("T9 design stage changed")
    if (
        str(design["identity"])
        != "target_residual_pc3_mixed_interaction_preflight_v1"
    ):
        raise ValueError("T9 design identity changed")

    direction = design["direction_contract"]
    if (
        str(direction["action_coordinate"])
        != T6.ACTION_FIELD
        or str(direction["candidate_id"])
        != "matched_visible_target_equal_pc3"
        or int(direction["existing_full_span_basis_count"]) != 11
        or int(direction["augmented_full_span_basis_count"]) != 12
        or tuple(direction["selected_old_eight_indices"])
        != T7_SELECTED_OLD_INDICES
        or float(direction["maximum_formal_schedule_l2"])
        != T6.FORMAL_L2_LIMIT
        or float(direction["maximum_schedule_component_abs"])
        != T6.COMPONENT_ABS_LIMIT
        or tuple(direction["cancellation_effect_states"])
        != T6.CANCELLATION_EFFECT_STATES
        or int(direction["episode_horizon_steps"])
        != T6.EPISODE_HORIZON_STEPS
    ):
        raise ValueError("T9 direction contract changed")

    stress = design["stress_composite_contract"]
    if tuple(tuple(row) for row in stress["factorial_signs"]) != FACTORIAL_SIGNS:
        raise ValueError("T9 factorial signs changed")
    if (
        str(stress["runtime_schedule_key"])
        != "public_task_start_actuator_delay_and_slew_only"
    ):
        raise ValueError("T9 stress schedule is not label independent")

    prospective = design["prospective_real_identification_contract"]
    if (
        int(prospective["context_count"]) != 32
        or int(prospective["extended_baseline_count"]) != 32
        or int(prospective["standalone_pc3_signed_probe_count"]) != 64
        or int(prospective["mixed_factorial_probe_count"]) != 128
        or int(prospective["total_task_count"]) != 224
        or bool(prospective["formal_timing_changed"])
    ):
        raise ValueError("T9 prospective task or timing contract changed")

    scope = design["scientific_scope"]
    forbidden_true = (
        "preflight_executes_real_tsc",
        "action_schedule_novelty_is_plant_response_validation",
        "controller_implementation_authorized_by_preflight",
        "real_tsc_controller_execution_authorized_by_preflight",
        "probe_trajectories_are_demonstrations",
        "bc_dagger_or_rl_allowed",
    )
    if any(bool(scope[key]) for key in forbidden_true):
        raise ValueError("T9 scientific scope overclaims the preflight")


def _authenticate_compact(
    path: Path, *, required_sha256: str, description: str
) -> Mapping[str, Any]:
    actual = _sha256(path)
    if actual != required_sha256:
        raise ValueError(f"{description} SHA-256 mismatch")
    payload = _load_json(path)
    if not isinstance(payload, Mapping):
        raise ValueError(f"{description} is not a JSON object")
    return payload


def _formal_schedule(
    probe: Mapping[str, Any], *, formal_hold_step: int
) -> np.ndarray:
    rows = np.zeros((formal_hold_step, 3), dtype=float)
    for issue_step, delta in probe["formal_issue_schedule"]:
        issue_step = int(issue_step)
        if issue_step < 0 or issue_step >= formal_hold_step:
            raise ValueError("formal probe issue step is outside the window")
        rows[issue_step] = np.asarray(delta, dtype=float)
    return rows


def _case_key(delay_steps: int, slew_scale: float) -> str:
    if delay_steps == 0 and slew_scale == 1.0:
        return "delay0_slew1p0"
    if delay_steps == 2 and slew_scale == 0.9:
        return "delay2_slew0p9"
    raise ValueError("unexpected actuator case")


def _find_actuator_case(
    cases: Sequence[Mapping[str, Any]],
    *,
    delay_steps: int,
    slew_scale: float,
) -> Mapping[str, Any]:
    matches = [
        case
        for case in cases
        if int(case["delay_steps"]) == delay_steps
        and float(case["slew_scale"]) == slew_scale
    ]
    if len(matches) != 1:
        raise ValueError("actuator case is missing or duplicated")
    return matches[0]


def _scale_one_row(context: Mapping[str, Any]) -> Mapping[str, Any]:
    matches = [
        row
        for row in context["scale_rows"]
        if float(row["target_direction_scale"]) == 1.0
    ]
    if len(matches) != 1:
        raise ValueError("T8 scale-one row is missing or duplicated")
    return matches[0]


def _stress_coefficients(
    t8: Mapping[str, Any],
    design: Mapping[str, Any],
    *,
    delay_steps: int,
    slew_scale: float,
) -> tuple[np.ndarray, int]:
    failed: list[np.ndarray] = []
    for context in t8["context_rows"]:
        if (
            int(context["actual_delay_steps"]) != delay_steps
            or float(context["actual_slew_scale"]) != slew_scale
        ):
            continue
        scale_one = _scale_one_row(context)
        if not bool(scale_one["passed"]):
            coefficients = np.asarray(
                scale_one["best_coefficients"], dtype=float
            )
            if coefficients.shape != (8,):
                raise ValueError("T8 coefficient vector shape changed")
            failed.append(coefficients)
    if not failed:
        raise ValueError("T8 actuator case has no failed contexts")
    mean = np.mean(np.asarray(failed), axis=0)
    contract = design["stress_composite_contract"][
        _case_key(delay_steps, slew_scale)
    ]
    expected = np.asarray(contract["mean_coefficients"], dtype=float)
    if len(failed) != int(contract["failed_context_count"]):
        raise ValueError("T8 failed-context count changed")
    if float(np.max(np.abs(mean - expected))) > 1.0e-12:
        raise ValueError("T8 failure-stress coefficients changed")
    return mean, len(failed)


def _factorial_common_amplitude(
    stress_unit: np.ndarray,
    pc3_unit: np.ndarray,
    *,
    formal_hold_step: int,
    delay_steps: int,
) -> tuple[float, list[np.ndarray]]:
    combinations = [
        stress_sign * stress_unit + pc3_sign * pc3_unit
        for stress_sign, pc3_sign in FACTORIAL_SIGNS
    ]
    maximum_l2 = max(float(np.linalg.norm(item)) for item in combinations)
    maximum_component = max(
        float(np.max(np.abs(item))) for item in combinations
    )
    maximum_cancellation_component = 0.0
    for item in combinations:
        formal = item.reshape(formal_hold_step, 3)
        effective_issue_count = formal_hold_step - delay_steps
        net = np.sum(formal[:effective_issue_count], axis=0)
        maximum_cancellation_component = max(
            maximum_cancellation_component,
            float(np.max(np.abs(net / len(T6.CANCELLATION_EFFECT_STATES)))),
        )
    component_denominator = max(
        maximum_component, maximum_cancellation_component
    )
    amplitude = min(
        T6.FORMAL_L2_LIMIT / maximum_l2,
        T6.COMPONENT_ABS_LIMIT / component_denominator,
    )
    if not math.isfinite(amplitude) or amplitude <= 0.0:
        raise ValueError("invalid factorial common amplitude")
    return float(amplitude), combinations


def _factorial_probe_payload(
    *,
    stress_sign: int,
    pc3_sign: int,
    combination_unit_sum: np.ndarray,
    common_amplitude: float,
    formal_hold_step: int,
    delay_steps: int,
) -> dict[str, Any]:
    formal = (
        common_amplitude
        * np.asarray(combination_unit_sum, dtype=float).reshape(
            formal_hold_step, 3
        )
    )
    schedule = T6._zero_net_schedule(formal, delay_steps=delay_steps)
    cancellation = np.asarray(
        [row[1] for row in schedule["cancellation_issue_schedule"]],
        dtype=float,
    )
    return {
        "probe_id": (
            f"stress_{'plus' if stress_sign > 0 else 'minus'}"
            f"_pc3_{'plus' if pc3_sign > 0 else 'minus'}"
        ),
        "stress_sign": stress_sign,
        "pc3_sign": pc3_sign,
        "common_factorial_amplitude": common_amplitude,
        "formal_l2_norm": float(np.linalg.norm(formal)),
        "formal_max_abs_component": float(np.max(np.abs(formal))),
        "cancellation_max_abs_component": float(
            np.max(np.abs(cancellation))
        ),
        "formal_mode_energy_fraction": T6._mode_energy_fraction(formal),
        **schedule,
    }


def _matched_residual_inputs(
    r17: Mapping[tuple[str, int, float], Mapping[str, Any]],
    r3c1: Sequence[Mapping[str, Any]],
    old_matrix: np.ndarray,
    *,
    delay_steps: int,
    slew_scale: float,
    formal_hold_step: int,
    effective_issue_count: int,
) -> tuple[np.ndarray, np.ndarray, list[float], list[dict[str, str]]]:
    source_delta = T6._action_rows(
        r17[("RZ_p10_m10", delay_steps, slew_scale)],
        field=T6.ACTION_FIELD,
        formal_hold_step=formal_hold_step,
        effective_issue_count=effective_issue_count,
    ) - T6._action_rows(
        r17[("nominal", delay_steps, slew_scale)],
        field=T6.ACTION_FIELD,
        formal_hold_step=formal_hold_step,
        effective_issue_count=effective_issue_count,
    )
    source_residual = T6._project_residual(
        old_matrix, source_delta.reshape(-1)
    )
    source_direction = source_residual / np.linalg.norm(source_residual)
    source_direction = T6._canonical_sign(
        source_direction, source_residual
    )

    residuals: list[np.ndarray] = []
    relative_residuals: list[float] = []
    group_ids: list[dict[str, str]] = []
    groups = T6._same_state_groups(
        r3c1, delay_steps=delay_steps, slew_scale=slew_scale
    )
    for group in groups:
        delta = (
            T6._action_rows(
                group["RZ_p10_m10"],
                field=T6.ACTION_FIELD,
                formal_hold_step=formal_hold_step,
                effective_issue_count=effective_issue_count,
            )
            - T6._action_rows(
                group["nominal"],
                field=T6.ACTION_FIELD,
                formal_hold_step=formal_hold_step,
                effective_issue_count=effective_issue_count,
            )
        ).reshape(-1)
        residual = T6._project_residual(old_matrix, delta)
        residuals.append(residual)
        relative_residuals.append(
            float(np.linalg.norm(residual) / np.linalg.norm(delta))
        )
        spec = group["nominal"]["spec"]
        group_ids.append(
            {
                "state_generation_experiment_id": str(
                    spec["state_generation_experiment_id"]
                ),
                "pair_id": str(spec["pair_id"]),
                "history_member": str(spec["history_member"]),
            }
        )
    return (
        source_direction,
        np.asarray(residuals),
        relative_residuals,
        group_ids,
    )


def build_audit(
    *,
    project_root: Path,
    design_config: Path,
    r17_manifest: Path,
    r3c1_run: Path,
    r3c1_inventory: Path,
    eight_basis_bank: Path,
    t6_preflight: Path,
    t7_feasibility: Path,
    t8_diagnostic: Path,
) -> dict[str, Any]:
    design = _load_json(design_config)
    _validate_design(design)
    source_contract = design["source_contract"]

    t6_payload = _authenticate_compact(
        t6_preflight,
        required_sha256=str(source_contract["t6_preflight_sha256"]),
        description="T6 preflight",
    )
    t7_payload = _authenticate_compact(
        t7_feasibility,
        required_sha256=str(source_contract["t7_feasibility_sha256"]),
        description="T7 feasibility",
    )
    t8_payload = _authenticate_compact(
        t8_diagnostic,
        required_sha256=str(
            source_contract["t8_headroom_diagnostic_sha256"]
        ),
        description="T8 diagnostic",
    )
    if not bool(t6_payload["all_preflight_gates_pass"]):
        raise ValueError("authenticated T6 preflight was not a pass")
    if int(t7_payload["condition_pass_count"]) != 32:
        raise ValueError("authenticated T7 selected bank condition changed")
    if not bool(
        t8_payload["measured_directions_insufficient_through_scale_four"]
    ):
        raise ValueError("authenticated T8 route conclusion changed")

    r17, r17_auth = T6._authenticate_r17(
        project_root,
        r17_manifest,
        required_digest=str(
            source_contract["r17_selected_expert_digest"]
        ),
    )
    r3c1, r3c1_auth = T6._authenticate_r3c1(
        r3c1_run,
        r3c1_inventory,
        required_digest=str(
            source_contract["r3c1_run_inventory_digest"]
        ),
    )
    required_bank_sha256 = str(
        source_contract["eight_basis_controller_bank_sha256"]
    )
    if _sha256(eight_basis_bank) != required_bank_sha256:
        raise ValueError("eight-basis bank SHA-256 mismatch")
    bank = _load_json(eight_basis_bank)
    if int(bank["sample_count"]) != 32 or int(bank["basis_count"]) != 8:
        raise ValueError("eight-basis bank shape changed")

    direction_contract = design["direction_contract"]
    case_results: list[dict[str, Any]] = []
    for actuator in T6.ACTUATOR_CASES:
        delay_steps = int(actuator["delay_steps"])
        slew_scale = float(actuator["slew_scale"])
        formal_hold_step = int(actuator["formal_hold_step"])
        old_matrix, effective_issue_count = T6._schedule_matrix(
            bank["samples"],
            delay_steps=delay_steps,
            slew_scale=slew_scale,
            formal_hold_step=formal_hold_step,
        )
        old_normalized = old_matrix / np.linalg.norm(
            old_matrix, axis=0
        )
        (
            source_direction,
            residual_matrix,
            relative_residuals,
            group_ids,
        ) = _matched_residual_inputs(
            r17,
            r3c1,
            old_matrix,
            delay_steps=delay_steps,
            slew_scale=slew_scale,
            formal_hold_step=formal_hold_step,
            effective_issue_count=effective_issue_count,
        )

        after_source = residual_matrix - np.outer(
            residual_matrix @ source_direction, source_direction
        )
        normalized_rows = after_source / np.linalg.norm(
            after_source, axis=1
        )[:, None]
        _, singular_values, right = np.linalg.svd(
            normalized_rows, full_matrices=False
        )
        visible_directions: list[np.ndarray] = []
        for candidate in right[:3]:
            direction = T6._orthonormalize(
                candidate,
                old_matrix,
                [source_direction, *visible_directions],
            )
            direction = T6._canonical_sign(
                direction, np.mean(normalized_rows, axis=0)
            )
            visible_directions.append(direction)
        all_four = [source_direction, *visible_directions]
        pc3_direction = visible_directions[2]

        remaining = residual_matrix.copy()
        for direction in all_four:
            remaining -= np.outer(remaining @ direction, direction)
        per_group_coverage = 1.0 - np.sum(
            remaining * remaining, axis=1
        ) / np.sum(residual_matrix * residual_matrix, axis=1)
        aggregate_coverage = 1.0 - float(
            np.sum(remaining * remaining)
            / np.sum(residual_matrix * residual_matrix)
        )

        t6_case = _find_actuator_case(
            t6_payload["actuator_cases"],
            delay_steps=delay_steps,
            slew_scale=slew_scale,
        )
        t6_probe_map = {
            str(probe["probe_id"]): probe
            for probe in t6_case["probe_schedules"]
        }
        if tuple(t6_probe_map) != T6_PROBE_IDS:
            raise ValueError("T6 probe identity or order changed")
        reproduction_errors: list[float] = []
        for probe_id, unit_direction in zip(T6_PROBE_IDS, all_four[:3]):
            reproduced = T6._candidate_payload(
                probe_id,
                "T9 exact T6 schedule reproduction",
                unit_direction,
                formal_hold_step=formal_hold_step,
                delay_steps=delay_steps,
            )
            expected_formal = _formal_schedule(
                t6_probe_map[probe_id],
                formal_hold_step=formal_hold_step,
            )
            reproduced_formal = _formal_schedule(
                reproduced, formal_hold_step=formal_hold_step
            )
            reproduction_errors.append(
                float(np.max(np.abs(reproduced_formal - expected_formal)))
            )

        selected_columns = [
            old_matrix[:, index] for index in T7_SELECTED_OLD_INDICES
        ]
        selected_columns.extend(
            _formal_schedule(
                t6_probe_map[probe_id],
                formal_hold_step=formal_hold_step,
            ).reshape(-1)
            for probe_id in T6_PROBE_IDS
        )
        selected_matrix = np.column_stack(selected_columns)
        stress_coefficients, stress_failure_count = _stress_coefficients(
            t8_payload,
            design,
            delay_steps=delay_steps,
            slew_scale=slew_scale,
        )
        stress_raw = selected_matrix @ stress_coefficients
        stress_norm = float(np.linalg.norm(stress_raw))
        if not math.isfinite(stress_norm) or stress_norm <= 1.0e-14:
            raise ValueError("failure-stress schedule is degenerate")
        stress_unit = stress_raw / stress_norm

        common_amplitude, factorial_unit_sums = (
            _factorial_common_amplitude(
                stress_unit,
                pc3_direction,
                formal_hold_step=formal_hold_step,
                delay_steps=delay_steps,
            )
        )
        factorial_probes = [
            _factorial_probe_payload(
                stress_sign=stress_sign,
                pc3_sign=pc3_sign,
                combination_unit_sum=unit_sum,
                common_amplitude=common_amplitude,
                formal_hold_step=formal_hold_step,
                delay_steps=delay_steps,
            )
            for (stress_sign, pc3_sign), unit_sum in zip(
                FACTORIAL_SIGNS, factorial_unit_sums
            )
        ]
        standalone_pc3 = T6._candidate_payload(
            "matched_visible_target_equal_pc3",
            (
                "third equal-context principal direction of exact same-"
                "restart-state R3c1 target-action residual after removing "
                "the old eight columns, R17 residual, PC1, and PC2"
            ),
            pc3_direction,
            formal_hold_step=formal_hold_step,
            delay_steps=delay_steps,
        )

        full_augmented = np.column_stack(
            [old_normalized, *all_four]
        )
        selected_nine = np.column_stack(
            [selected_matrix, pc3_direction]
        )
        selected_nine_normalized = selected_nine / np.linalg.norm(
            selected_nine, axis=0
        )
        gram = np.column_stack(all_four).T @ np.column_stack(all_four)
        old_candidate_dots = [
            float(np.max(np.abs(old_matrix.T @ direction)))
            for direction in all_four
        ]
        all_schedules = [standalone_pc3, *factorial_probes]
        bounded_zero_net = all(
            float(probe["formal_l2_norm"])
            <= T6.FORMAL_L2_LIMIT + 1.0e-15
            and float(probe["formal_max_abs_component"])
            <= T6.COMPONENT_ABS_LIMIT + 1.0e-15
            and float(probe["cancellation_max_abs_component"])
            <= T6.COMPONENT_ABS_LIMIT + 1.0e-15
            and max(abs(value) for value in probe["requested_full_net"])
            <= ZERO_NET_TOLERANCE
            and int(probe["first_cancellation_effect_state"]) == 39
            for probe in all_schedules
        )

        case_results.append(
            {
                **actuator,
                "effective_formal_issue_count": effective_issue_count,
                "equal_context_singular_values": [
                    float(value) for value in singular_values
                ],
                "equal_context_first_three_energy_fraction": float(
                    np.sum(singular_values[:3] ** 2)
                    / np.sum(singular_values**2)
                ),
                "pc3_singular_value": float(singular_values[2]),
                "matched_visible_target_relative_residual": {
                    "minimum": float(np.min(relative_residuals)),
                    "median": float(np.median(relative_residuals)),
                    "maximum": float(np.max(relative_residuals)),
                    "per_group": [
                        {
                            **group_id,
                            "relative_residual": float(relative_residual),
                            "four_direction_subspace_coverage": float(
                                coverage
                            ),
                        }
                        for group_id, relative_residual, coverage in zip(
                            group_ids,
                            relative_residuals,
                            per_group_coverage,
                        )
                    ],
                },
                "four_direction_subspace_coverage": {
                    "minimum": float(np.min(per_group_coverage)),
                    "median": float(np.median(per_group_coverage)),
                    "maximum": float(np.max(per_group_coverage)),
                    "aggregate_energy_weighted": aggregate_coverage,
                },
                "complete_augmented_schedule_rank": int(
                    np.linalg.matrix_rank(full_augmented)
                ),
                "complete_augmented_schedule_normalized_condition": float(
                    np.linalg.cond(full_augmented)
                ),
                "selected_nine_schedule_rank": int(
                    np.linalg.matrix_rank(selected_nine)
                ),
                "selected_nine_schedule_normalized_condition": float(
                    np.linalg.cond(selected_nine_normalized)
                ),
                "maximum_all_four_orthogonality_error": float(
                    np.max(np.abs(gram - np.eye(4)))
                ),
                "maximum_old_schedule_candidate_dot": float(
                    max(old_candidate_dots)
                ),
                "maximum_T6_schedule_reproduction_error": float(
                    max(reproduction_errors)
                ),
                "pc3_formal_mode_energy_fraction": standalone_pc3[
                    "formal_mode_energy_fraction"
                ],
                "standalone_pc3_probe": standalone_pc3,
                "failure_stress_schedule": {
                    "source_failed_context_count": stress_failure_count,
                    "selected_basis_coefficients": [
                        float(value) for value in stress_coefficients
                    ],
                    "unnormalized_l2_norm": stress_norm,
                    "unit_pc3_dot": float(stress_unit @ pc3_direction),
                },
                "mixed_factorial": {
                    "common_amplitude": common_amplitude,
                    "probe_count": len(factorial_probes),
                    "probes": factorial_probes,
                },
                "bounded_and_zero_net_all_new_schedules": bounded_zero_net,
            }
        )

    gates = {
        "r17_authenticated_18_of_18": (
            int(r17_auth["authenticated_file_count"]) == 18
        ),
        "r3c1_authenticated_32_of_32": (
            int(r3c1_auth["authenticated_raw_count"]) == 32
        ),
        "T6_T7_T8_compact_sources_authenticated": True,
        "T6_first_three_schedules_reproduced_at_most_1e_12": all(
            case["maximum_T6_schedule_reproduction_error"] <= 1.0e-12
            for case in case_results
        ),
        "pc3_singular_value_at_least_frozen_minimum": all(
            case["pc3_singular_value"]
            >= float(
                direction_contract[
                    "minimum_equal_context_pc3_singular_value"
                ]
            )
            for case in case_results
        ),
        "four_direction_minimum_coverage_at_least_frozen_minimum": all(
            case["four_direction_subspace_coverage"]["minimum"]
            >= float(
                direction_contract[
                    "minimum_per_context_four_direction_coverage"
                ]
            )
            for case in case_results
        ),
        "complete_augmented_schedule_rank_12_of_12": all(
            case["complete_augmented_schedule_rank"] == 12
            for case in case_results
        ),
        "selected_nine_schedule_rank_9_of_9": all(
            case["selected_nine_schedule_rank"] == 9
            for case in case_results
        ),
        "normalized_action_schedule_condition_at_most_3": all(
            max(
                case["complete_augmented_schedule_normalized_condition"],
                case["selected_nine_schedule_normalized_condition"],
            )
            <= float(
                direction_contract[
                    "maximum_normalized_action_schedule_condition"
                ]
            )
            for case in case_results
        ),
        "orthogonality_at_most_1e_12": all(
            case["maximum_all_four_orthogonality_error"]
            <= float(direction_contract["maximum_orthogonality_error"])
            and case["maximum_old_schedule_candidate_dot"]
            <= float(direction_contract["maximum_orthogonality_error"])
            and abs(case["failure_stress_schedule"]["unit_pc3_dot"])
            <= float(direction_contract["maximum_orthogonality_error"])
            for case in case_results
        ),
        "pc3_has_nonzero_mode2_energy": all(
            case["pc3_formal_mode_energy_fraction"][2] > 0.0
            for case in case_results
        ),
        "all_new_schedules_bounded_zero_net_and_post_contract": all(
            case["bounded_and_zero_net_all_new_schedules"]
            for case in case_results
        ),
        "factorial_is_exactly_four_sign_combinations": all(
            [
                [probe["stress_sign"], probe["pc3_sign"]]
                for probe in case["mixed_factorial"]["probes"]
            ]
            == [list(signs) for signs in FACTORIAL_SIGNS]
            for case in case_results
        ),
        "prospective_task_count_exactly_224": (
            int(
                design["prospective_real_identification_contract"][
                    "total_task_count"
                ]
            )
            == 224
        ),
        "formal_timing_unchanged": not bool(
            design["prospective_real_identification_contract"][
                "formal_timing_changed"
            ]
        ),
    }
    return {
        "schema_version": 1,
        "stage": "Stage4.2R3c3T9",
        "identity": "target_residual_pc3_mixed_interaction_preflight_v1",
        "scientific_status": (
            "prospective action-design evidence only; no T9 plant response, "
            "interaction response, controller repair, or formal control "
            "validation"
        ),
        "real_tsc_executed": False,
        "ray_executed": False,
        "gotsc_executed": False,
        "formal_timing_unchanged": True,
        "design": {
            "path": str(design_config),
            "sha256": _sha256(design_config),
        },
        "inputs": {
            "r17": r17_auth,
            "r3c1": r3c1_auth,
            "eight_basis_bank": {
                "path": str(eight_basis_bank),
                "sha256": _sha256(eight_basis_bank),
                "sample_count": int(bank["sample_count"]),
                "basis_count": int(bank["basis_count"]),
            },
            "t6_preflight": {
                "path": str(t6_preflight),
                "sha256": _sha256(t6_preflight),
            },
            "t7_feasibility": {
                "path": str(t7_feasibility),
                "sha256": _sha256(t7_feasibility),
            },
            "t8_diagnostic": {
                "path": str(t8_diagnostic),
                "sha256": _sha256(t8_diagnostic),
            },
            "frozen_T6_preflight_tool": {
                "path": str(T6_PREFLIGHT_TOOL),
                "sha256": _sha256(T6_PREFLIGHT_TOOL),
            },
        },
        "prospective_matrix": {
            "context_count": 32,
            "per_context": {
                "extended_baseline": 1,
                "standalone_pc3_signs": 2,
                "mixed_factorial_sign_combinations": 4,
            },
            "total_task_count": 224,
        },
        "actuator_cases": case_results,
        "gates": gates,
        "all_preflight_gates_pass": all(gates.values()),
        "limitations": [
            "The inspected R17/R3c1/T8 data are development evidence, not independent confirmation.",
            "PC3 action-schedule novelty does not prove a novel or useful plant response.",
            "The factorial schedule only measures the frozen stress-by-PC3 mixed contrast.",
            "Current safety, response symmetry, hidden-history invariance, rank, and feasibility require new real signed TSC probes.",
            "A large measured interaction cannot be discarded; it requires a separately validated interaction-aware response model.",
            "No R3c4, BC, DAgger, or residual-RL execution is authorized by this preflight.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--design-config", type=Path, required=True)
    parser.add_argument("--r17-manifest", type=Path, required=True)
    parser.add_argument("--r3c1-run", type=Path, required=True)
    parser.add_argument("--r3c1-inventory", type=Path, required=True)
    parser.add_argument("--eight-basis-bank", type=Path, required=True)
    parser.add_argument("--t6-preflight", type=Path, required=True)
    parser.add_argument("--t7-feasibility", type=Path, required=True)
    parser.add_argument("--t8-diagnostic", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit = build_audit(
        project_root=args.project_root.resolve(),
        design_config=args.design_config.resolve(),
        r17_manifest=args.r17_manifest.resolve(),
        r3c1_run=args.r3c1_run.resolve(),
        r3c1_inventory=args.r3c1_inventory.resolve(),
        eight_basis_bank=args.eight_basis_bank.resolve(),
        t6_preflight=args.t6_preflight.resolve(),
        t7_feasibility=args.t7_feasibility.resolve(),
        t8_diagnostic=args.t8_diagnostic.resolve(),
    )
    _write_json(args.output, audit)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "all_preflight_gates_pass": audit[
                    "all_preflight_gates_pass"
                ],
                "prospective_task_count": audit["prospective_matrix"][
                    "total_task_count"
                ],
                "actuator_cases": [
                    {
                        "delay_steps": case["delay_steps"],
                        "slew_scale": case["slew_scale"],
                        "pc3_singular_value": case["pc3_singular_value"],
                        "minimum_four_direction_coverage": case[
                            "four_direction_subspace_coverage"
                        ]["minimum"],
                        "complete_rank": case[
                            "complete_augmented_schedule_rank"
                        ],
                        "complete_condition": case[
                            "complete_augmented_schedule_normalized_condition"
                        ],
                        "selected_nine_rank": case[
                            "selected_nine_schedule_rank"
                        ],
                        "selected_nine_condition": case[
                            "selected_nine_schedule_normalized_condition"
                        ],
                        "factorial_common_amplitude": case[
                            "mixed_factorial"
                        ]["common_amplitude"],
                    }
                    for case in audit["actuator_cases"]
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
