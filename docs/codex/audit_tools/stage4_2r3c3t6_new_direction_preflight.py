#!/usr/bin/env python3
"""Authenticate and freeze target-relevant Stage4.2R3c3T6 probe directions.

This tool is read-only with respect to its inputs.  It combines:

* the authenticated Stage4.1R17 nominal/offset expert action difference;
* exact same-restart-state Stage4.2R3c1 nominal/offset action differences;
* the authenticated Stage4.2R3c3T3 eight-schedule action span.

Only issue steps whose physical effects can reach the immutable formal hold
endpoint participate in the direction construction.  Each frozen positive
probe is neutralized at physical states 39..44, after the formal contract.
The output is a compact design audit; this script never invokes TSC.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


TARGETS = ("nominal", "RZ_p10_m10")
ACTUATOR_CASES = (
    {"delay_steps": 0, "slew_scale": 1.0, "formal_hold_step": 35},
    {"delay_steps": 2, "slew_scale": 0.9, "formal_hold_step": 37},
)
ACTION_FIELD = "issued_desired_physical_mode_coefficients"
FORMAL_L2_LIMIT = 0.015
COMPONENT_ABS_LIMIT = 0.0075
CANCELLATION_EFFECT_STATES = tuple(range(39, 45))
EPISODE_HORIZON_STEPS = 50
ORTHOGONALITY_TOLERANCE = 1.0e-12
ZERO_NET_TOLERANCE = 1.0e-12


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path) -> Any:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        return json.load(stream)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _project_residual(matrix: np.ndarray, vector: np.ndarray) -> np.ndarray:
    matrix = np.asarray(matrix, dtype=float)
    vector = np.asarray(vector, dtype=float).reshape(-1)
    if matrix.shape[0] != vector.size:
        raise ValueError("projection matrix/vector dimension mismatch")
    coefficients = np.linalg.lstsq(matrix, vector, rcond=None)[0]
    return vector - matrix @ coefficients


def _canonical_sign(vector: np.ndarray, reference: np.ndarray) -> np.ndarray:
    vector = np.asarray(vector, dtype=float).copy()
    reference = np.asarray(reference, dtype=float).reshape(-1)
    signed_alignment = float(vector @ reference)
    if signed_alignment < 0.0:
        vector *= -1.0
    elif signed_alignment == 0.0:
        pivot = int(np.argmax(np.abs(vector)))
        if vector[pivot] < 0.0:
            vector *= -1.0
    return vector


def _orthonormalize(
    vector: np.ndarray,
    existing_matrix: np.ndarray,
    prior_directions: Sequence[np.ndarray],
) -> np.ndarray:
    residual = _project_residual(existing_matrix, vector)
    for prior in prior_directions:
        prior = np.asarray(prior, dtype=float).reshape(-1)
        residual -= prior * float(prior @ residual)
    norm = float(np.linalg.norm(residual))
    if not math.isfinite(norm) or norm <= 1.0e-14:
        raise ValueError("candidate direction is degenerate")
    return residual / norm


def _schedule_matrix(
    samples: Sequence[Mapping[str, Any]],
    *,
    delay_steps: int,
    slew_scale: float,
    formal_hold_step: int,
) -> tuple[np.ndarray, int]:
    matching = [
        sample
        for sample in samples
        if int(sample["actuator_delay_steps"]) == delay_steps
        and float(sample["actuator_slew_scale"]) == slew_scale
    ]
    if len(matching) != 16:
        raise ValueError(
            f"expected 16 bank samples for actuator case, found {len(matching)}"
        )
    effective_issue_count = formal_hold_step - delay_steps
    matrices: list[np.ndarray] = []
    for sample in matching:
        responses = list(sample["basis_responses"])
        if len(responses) != 8:
            raise ValueError("eight-basis sample does not contain eight responses")
        columns: list[np.ndarray] = []
        for expected_index, response in enumerate(responses):
            if int(response["basis_index"]) != expected_index:
                raise ValueError("basis order changed")
            schedule = np.zeros((formal_hold_step, 3), dtype=float)
            for issue_step, delta in response[
                "positive_schedule_by_task_issue_step"
            ]:
                issue_step = int(issue_step)
                if issue_step < effective_issue_count:
                    schedule[issue_step] = np.asarray(delta, dtype=float)
            columns.append(schedule.reshape(-1))
        matrices.append(np.column_stack(columns))
    first = matrices[0]
    if not all(np.array_equal(first, item) for item in matrices[1:]):
        raise ValueError("existing schedule bank varies inside an actuator case")
    if int(np.linalg.matrix_rank(first)) != 8:
        raise ValueError("existing formal action schedule span is not rank eight")
    return first, effective_issue_count


def _scaled_formal_schedule(
    unit_direction: np.ndarray,
    *,
    formal_hold_step: int,
) -> tuple[np.ndarray, float]:
    direction = np.asarray(unit_direction, dtype=float).reshape(
        formal_hold_step, 3
    )
    direction_l2 = float(np.linalg.norm(direction))
    if abs(direction_l2 - 1.0) > 1.0e-12:
        raise ValueError("candidate direction must have unit L2 norm")
    maximum = float(np.max(np.abs(direction)))
    scale = min(FORMAL_L2_LIMIT, COMPONENT_ABS_LIMIT / maximum)
    return direction * scale, float(scale)


def _zero_net_schedule(
    formal_schedule: np.ndarray,
    *,
    delay_steps: int,
) -> dict[str, Any]:
    formal_schedule = np.asarray(formal_schedule, dtype=float)
    formal_hold_step = int(formal_schedule.shape[0])
    expected_effective_issue_count = formal_hold_step - delay_steps
    if np.any(formal_schedule[expected_effective_issue_count:] != 0.0):
        raise ValueError("noncausal-to-formal issue rows must be exactly zero")

    formal_rows = [
        [issue_step, [float(value) for value in formal_schedule[issue_step]]]
        for issue_step in range(expected_effective_issue_count)
    ]
    requested_formal_net = np.sum(
        formal_schedule[:expected_effective_issue_count], axis=0
    )
    cancellation_rows: list[list[Any]] = []
    cancellation_vectors: list[np.ndarray] = []
    equal_vector = -requested_formal_net / len(CANCELLATION_EFFECT_STATES)
    for effect_state in CANCELLATION_EFFECT_STATES[:-1]:
        issue_step = int(effect_state - delay_steps - 1)
        cancellation_vectors.append(equal_vector.copy())
        cancellation_rows.append(
            [issue_step, [float(value) for value in equal_vector]]
        )
    final_vector = -requested_formal_net - np.sum(
        np.asarray(cancellation_vectors), axis=0
    )
    final_effect_state = CANCELLATION_EFFECT_STATES[-1]
    cancellation_vectors.append(final_vector)
    cancellation_rows.append(
        [
            int(final_effect_state - delay_steps - 1),
            [float(value) for value in final_vector],
        ]
    )
    full_rows = formal_rows + cancellation_rows
    full_net = np.sum(
        np.asarray([row[1] for row in full_rows], dtype=float), axis=0
    )
    if float(np.max(np.abs(full_net))) > ZERO_NET_TOLERANCE:
        raise ValueError("constructed probe schedule is not zero net")
    if max(row[0] for row in full_rows) >= EPISODE_HORIZON_STEPS:
        raise ValueError("probe issue step exceeds episode horizon")
    return {
        "formal_issue_schedule": formal_rows,
        "cancellation_issue_schedule": cancellation_rows,
        "positive_schedule_by_task_issue_step": full_rows,
        "requested_formal_net": [
            float(value) for value in requested_formal_net
        ],
        "requested_full_net": [float(value) for value in full_net],
        "first_formal_effect_state": delay_steps + 1,
        "last_formal_effect_state": formal_hold_step,
        "first_cancellation_effect_state": CANCELLATION_EFFECT_STATES[0],
        "last_cancellation_effect_state": CANCELLATION_EFFECT_STATES[-1],
        "formal_issue_count": expected_effective_issue_count,
        "cancellation_issue_count": len(cancellation_rows),
    }


def _mode_energy_fraction(vector: np.ndarray) -> list[float]:
    rows = np.asarray(vector, dtype=float).reshape(-1, 3)
    energy = np.sum(rows * rows, axis=0)
    return [float(value) for value in energy / np.sum(energy)]


def _authenticate_r17(
    project_root: Path,
    manifest_path: Path,
    *,
    required_digest: str,
) -> tuple[dict[tuple[str, int, float], Mapping[str, Any]], dict[str, Any]]:
    manifest = _load_json(manifest_path)
    fingerprint = manifest["selected_expert_fingerprint"]
    if fingerprint["inventory_contract"] != (
        "r42r1_selected_18_calibrated_expert_raw_v1"
    ):
        raise ValueError("R17 selected expert inventory contract changed")
    if int(fingerprint["n_files"]) != 18:
        raise ValueError("R17 selected expert file count changed")
    if str(fingerprint["digest"]) != required_digest:
        raise ValueError("R17 selected expert digest mismatch")

    parsed: dict[tuple[str, int, float], Mapping[str, Any]] = {}
    for entry in fingerprint["files"]:
        path = Path(str(entry["path"]))
        if not path.is_absolute():
            path = project_root / path
        if path.stat().st_size != int(entry["size_bytes"]):
            raise ValueError(f"R17 size mismatch: {path}")
        if _sha256(path) != str(entry["sha256"]):
            raise ValueError(f"R17 SHA-256 mismatch: {path}")
        payload = _load_json(path)
        if not bool(payload.get("success")):
            raise ValueError(f"R17 source is not successful: {path}")
        spec = payload["spec"]
        key = (
            str(spec["target_id"]),
            int(spec["action_delay_steps"]),
            float(spec["slew_scale"]),
        )
        if key in parsed:
            raise ValueError(f"duplicate R17 expert key: {key}")
        parsed[key] = payload
    if len(parsed) != 18:
        raise ValueError("R17 expert key count changed")
    return parsed, {
        "manifest_path": str(manifest_path),
        "manifest_sha256": _sha256(manifest_path),
        "inventory_contract": fingerprint["inventory_contract"],
        "inventory_digest": fingerprint["digest"],
        "authenticated_file_count": len(parsed),
    }


def _authenticate_r3c1(
    run_dir: Path,
    inventory_path: Path,
    *,
    required_digest: str,
) -> tuple[list[Mapping[str, Any]], dict[str, Any]]:
    inventory = _load_json(inventory_path)
    if str(inventory["digest"]) != required_digest:
        raise ValueError("R3c1 run inventory digest mismatch")
    raw_prefix = (
        "stage4_2r3c1_authenticated_visible_manifold_control/raw/"
    )
    entries = [
        entry
        for entry in inventory["files"]
        if str(entry["path"]).startswith(raw_prefix)
        and str(entry["path"]).endswith(".json.gz")
    ]
    if len(entries) != 32:
        raise ValueError(f"expected 32 R3c1 raw entries, found {len(entries)}")
    payloads: list[Mapping[str, Any]] = []
    for entry in entries:
        path = run_dir / str(entry["path"])
        if path.stat().st_size != int(entry["size_bytes"]):
            raise ValueError(f"R3c1 size mismatch: {path}")
        if _sha256(path) != str(entry["sha256"]):
            raise ValueError(f"R3c1 SHA-256 mismatch: {path}")
        payload = _load_json(path)
        if not bool(payload.get("success")) or not bool(
            payload.get("completed")
        ):
            raise ValueError(f"R3c1 raw is not successful: {path}")
        payloads.append(payload)
    return payloads, {
        "run_dir": str(run_dir),
        "inventory_path": str(inventory_path),
        "inventory_sha256": _sha256(inventory_path),
        "inventory_digest": inventory["digest"],
        "authenticated_raw_count": len(payloads),
    }


def _action_rows(
    payload: Mapping[str, Any],
    *,
    field: str,
    formal_hold_step: int,
    effective_issue_count: int,
) -> np.ndarray:
    trace = list(
        payload.get("controller_trace")
        or payload.get("control_trace")
        or []
    )
    if len(trace) < formal_hold_step:
        raise ValueError("source trace is shorter than formal hold")
    rows = np.asarray(
        [trace[index][field] for index in range(formal_hold_step)],
        dtype=float,
    )
    if rows.shape != (formal_hold_step, 3):
        raise ValueError("action trace shape changed")
    rows[effective_issue_count:] = 0.0
    return rows


def _same_state_groups(
    payloads: Sequence[Mapping[str, Any]],
    *,
    delay_steps: int,
    slew_scale: float,
) -> list[dict[str, Mapping[str, Any]]]:
    groups: dict[
        tuple[str, str, str], dict[str, Mapping[str, Any]]
    ] = {}
    for payload in payloads:
        spec = payload["spec"]
        if int(spec["action_delay_steps"]) != delay_steps or float(
            spec["slew_scale"]
        ) != slew_scale:
            continue
        key = (
            str(spec["state_generation_experiment_id"]),
            str(spec["pair_id"]),
            str(spec["history_member"]),
        )
        target = str(spec["target_id"])
        groups.setdefault(key, {})[target] = payload
    if len(groups) != 8:
        raise ValueError(
            f"expected eight same-state groups, found {len(groups)}"
        )
    ordered: list[dict[str, Mapping[str, Any]]] = []
    for key in sorted(groups):
        group = groups[key]
        if set(group) != set(TARGETS):
            raise ValueError(f"incomplete target pair for {key}")
        nominal = group["nominal"]
        offset = group["RZ_p10_m10"]
        for field in ("R", "Z", "Ip", "currents_a_display", "currents_a_tsc"):
            if nominal["trajectory"][0][field] != offset["trajectory"][0][field]:
                raise ValueError(f"initial same-state mismatch in {field}")
        nominal_spec = nominal["spec"]
        offset_spec = offset["spec"]
        target_offset_delta = np.asarray(
            [
                float(offset_spec["target_R_offset_m"])
                - float(nominal_spec["target_R_offset_m"]),
                float(offset_spec["target_Z_offset_m"])
                - float(nominal_spec["target_Z_offset_m"]),
                float(offset_spec["target_Ip_offset_A"])
                - float(nominal_spec["target_Ip_offset_A"]),
            ]
        )
        if float(
            np.max(
                np.abs(
                    target_offset_delta - np.asarray([0.01, -0.01, 0.0])
                )
            )
        ) > 1.0e-12:
            raise ValueError("same-state visible target offset changed")
        ordered.append(group)
    return ordered


def _candidate_payload(
    probe_id: str,
    derivation: str,
    unit_direction: np.ndarray,
    *,
    formal_hold_step: int,
    delay_steps: int,
) -> dict[str, Any]:
    formal_schedule, scale = _scaled_formal_schedule(
        unit_direction, formal_hold_step=formal_hold_step
    )
    schedule = _zero_net_schedule(
        formal_schedule, delay_steps=delay_steps
    )
    cancellation = np.asarray(
        [row[1] for row in schedule["cancellation_issue_schedule"]],
        dtype=float,
    )
    return {
        "probe_id": probe_id,
        "derivation": derivation,
        "normalization_rule": (
            "unit_direction_times_min(0.015_l2,"
            "0.0075_over_unit_max_abs)"
        ),
        "scale": scale,
        "formal_l2_norm": float(np.linalg.norm(formal_schedule)),
        "formal_max_abs_component": float(
            np.max(np.abs(formal_schedule))
        ),
        "cancellation_max_abs_component": float(
            np.max(np.abs(cancellation))
        ),
        "full_l2_norm": float(
            math.sqrt(
                float(np.sum(formal_schedule * formal_schedule))
                + float(np.sum(cancellation * cancellation))
            )
        ),
        "formal_mode_energy_fraction": _mode_energy_fraction(
            formal_schedule
        ),
        **schedule,
    }


def build_audit(
    *,
    project_root: Path,
    r17_manifest: Path,
    r3c1_run: Path,
    r3c1_inventory: Path,
    eight_basis_bank: Path,
    required_r17_digest: str,
    required_r3c1_digest: str,
    required_bank_sha256: str,
) -> dict[str, Any]:
    r17, r17_auth = _authenticate_r17(
        project_root, r17_manifest, required_digest=required_r17_digest
    )
    r3c1, r3c1_auth = _authenticate_r3c1(
        r3c1_run, r3c1_inventory, required_digest=required_r3c1_digest
    )
    if _sha256(eight_basis_bank) != required_bank_sha256:
        raise ValueError("eight-basis controller bank SHA-256 mismatch")
    bank = _load_json(eight_basis_bank)
    if int(bank["sample_count"]) != 32 or int(bank["basis_count"]) != 8:
        raise ValueError("eight-basis bank shape changed")

    case_results: list[dict[str, Any]] = []
    for actuator in ACTUATOR_CASES:
        delay_steps = int(actuator["delay_steps"])
        slew_scale = float(actuator["slew_scale"])
        formal_hold_step = int(actuator["formal_hold_step"])
        matrix, effective_issue_count = _schedule_matrix(
            bank["samples"],
            delay_steps=delay_steps,
            slew_scale=slew_scale,
            formal_hold_step=formal_hold_step,
        )
        normalized_matrix = matrix / np.linalg.norm(matrix, axis=0)

        source_by_target: dict[str, Mapping[str, Any]] = {}
        for target in TARGETS:
            key = (target, delay_steps, slew_scale)
            if key not in r17:
                raise ValueError(f"missing R17 source key: {key}")
            source_by_target[target] = r17[key]
        source_delta = _action_rows(
            source_by_target["RZ_p10_m10"],
            field=ACTION_FIELD,
            formal_hold_step=formal_hold_step,
            effective_issue_count=effective_issue_count,
        ) - _action_rows(
            source_by_target["nominal"],
            field=ACTION_FIELD,
            formal_hold_step=formal_hold_step,
            effective_issue_count=effective_issue_count,
        )
        source_residual = _project_residual(
            matrix, source_delta.reshape(-1)
        )
        source_relative_residual = float(
            np.linalg.norm(source_residual)
            / np.linalg.norm(source_delta)
        )
        source_direction = source_residual / np.linalg.norm(
            source_residual
        )
        source_direction = _canonical_sign(
            source_direction, source_residual
        )

        groups = _same_state_groups(
            r3c1,
            delay_steps=delay_steps,
            slew_scale=slew_scale,
        )
        matched_residuals: list[np.ndarray] = []
        matched_relative_residuals: list[float] = []
        group_ids: list[dict[str, str]] = []
        for group in groups:
            offset_action = _action_rows(
                group["RZ_p10_m10"],
                field=ACTION_FIELD,
                formal_hold_step=formal_hold_step,
                effective_issue_count=effective_issue_count,
            )
            nominal_action = _action_rows(
                group["nominal"],
                field=ACTION_FIELD,
                formal_hold_step=formal_hold_step,
                effective_issue_count=effective_issue_count,
            )
            delta = (offset_action - nominal_action).reshape(-1)
            residual = _project_residual(matrix, delta)
            matched_residuals.append(residual)
            matched_relative_residuals.append(
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
        residual_matrix = np.asarray(matched_residuals)
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
        for candidate in right[:2]:
            direction = _orthonormalize(
                candidate, matrix, [source_direction, *visible_directions]
            )
            direction = _canonical_sign(
                direction, np.mean(normalized_rows, axis=0)
            )
            visible_directions.append(direction)

        all_directions = [source_direction, *visible_directions]
        remaining = residual_matrix.copy()
        for direction in all_directions:
            remaining -= np.outer(remaining @ direction, direction)
        per_group_coverage = 1.0 - np.sum(
            remaining * remaining, axis=1
        ) / np.sum(residual_matrix * residual_matrix, axis=1)
        aggregate_coverage = 1.0 - float(
            np.sum(remaining * remaining)
            / np.sum(residual_matrix * residual_matrix)
        )
        augmented = np.column_stack(
            [normalized_matrix, *all_directions]
        )
        gram = np.column_stack(all_directions).T @ np.column_stack(
            all_directions
        )
        direction_old_dots = [
            float(np.max(np.abs(matrix.T @ direction)))
            for direction in all_directions
        ]
        probes = [
            _candidate_payload(
                "r17_target_action_residual",
                (
                    "authenticated R17 RZ_p10_m10 minus nominal desired-"
                    "physical action, projected outside the existing eight "
                    "formal schedule columns"
                ),
                source_direction,
                formal_hold_step=formal_hold_step,
                delay_steps=delay_steps,
            ),
            _candidate_payload(
                "matched_visible_target_equal_pc1",
                (
                    "first equal-context principal direction of exact same-"
                    "restart-state R3c1 target-action residual after removing "
                    "the old eight columns and R17 residual"
                ),
                visible_directions[0],
                formal_hold_step=formal_hold_step,
                delay_steps=delay_steps,
            ),
            _candidate_payload(
                "matched_visible_target_equal_pc2",
                (
                    "second equal-context principal direction of exact same-"
                    "restart-state R3c1 target-action residual after removing "
                    "the old eight columns and R17 residual"
                ),
                visible_directions[1],
                formal_hold_step=formal_hold_step,
                delay_steps=delay_steps,
            ),
        ]
        for probe in probes:
            if probe["formal_max_abs_component"] > COMPONENT_ABS_LIMIT + 1e-15:
                raise ValueError("candidate formal component exceeds bound")
            if probe["cancellation_max_abs_component"] > COMPONENT_ABS_LIMIT:
                raise ValueError("candidate cancellation component exceeds bound")
            if max(abs(x) for x in probe["requested_full_net"]) > ZERO_NET_TOLERANCE:
                raise ValueError("candidate full net is not zero")

        case_results.append(
            {
                **actuator,
                "effective_formal_issue_count": effective_issue_count,
                "noncausal_to_formal_issue_count": (
                    formal_hold_step - effective_issue_count
                ),
                "existing_schedule_rank": int(
                    np.linalg.matrix_rank(matrix)
                ),
                "existing_schedule_normalized_condition": float(
                    np.linalg.cond(normalized_matrix)
                ),
                "r17_target_action_relative_residual": (
                    source_relative_residual
                ),
                "matched_visible_target_relative_residual": {
                    "minimum": float(np.min(matched_relative_residuals)),
                    "median": float(np.median(matched_relative_residuals)),
                    "maximum": float(np.max(matched_relative_residuals)),
                    "per_group": [
                        {
                            **group_id,
                            "relative_residual": residual,
                            "candidate_subspace_coverage": float(coverage),
                        }
                        for group_id, residual, coverage in zip(
                            group_ids,
                            matched_relative_residuals,
                            per_group_coverage,
                        )
                    ],
                },
                "equal_context_singular_values": [
                    float(value) for value in singular_values
                ],
                "equal_context_first_two_energy_fraction": float(
                    np.sum(singular_values[:2] ** 2)
                    / np.sum(singular_values**2)
                ),
                "candidate_subspace_coverage": {
                    "minimum": float(np.min(per_group_coverage)),
                    "median": float(np.median(per_group_coverage)),
                    "maximum": float(np.max(per_group_coverage)),
                    "aggregate_energy_weighted": aggregate_coverage,
                },
                "augmented_schedule_rank": int(
                    np.linalg.matrix_rank(augmented)
                ),
                "augmented_schedule_normalized_condition": float(
                    np.linalg.cond(augmented)
                ),
                "maximum_candidate_pair_orthogonality_error": float(
                    np.max(np.abs(gram - np.eye(3)))
                ),
                "maximum_old_schedule_candidate_dot": float(
                    max(direction_old_dots)
                ),
                "probe_schedules": probes,
            }
        )

    gates = {
        "r17_authenticated_18_of_18": (
            r17_auth["authenticated_file_count"] == 18
        ),
        "r3c1_authenticated_32_of_32": (
            r3c1_auth["authenticated_raw_count"] == 32
        ),
        "same_state_target_groups_16_of_16": True,
        "r17_relative_residual_at_least_0p80": all(
            case["r17_target_action_relative_residual"] >= 0.80
            for case in case_results
        ),
        "matched_target_median_relative_residual_at_least_0p90": all(
            case["matched_visible_target_relative_residual"]["median"] >= 0.90
            for case in case_results
        ),
        "augmented_schedule_rank_11_of_11": all(
            case["augmented_schedule_rank"] == 11
            for case in case_results
        ),
        "augmented_schedule_normalized_condition_at_most_3": all(
            case["augmented_schedule_normalized_condition"] <= 3.0
            for case in case_results
        ),
        "orthogonality_at_most_1e_12": all(
            case["maximum_candidate_pair_orthogonality_error"]
            <= ORTHOGONALITY_TOLERANCE
            and case["maximum_old_schedule_candidate_dot"]
            <= ORTHOGONALITY_TOLERANCE
            for case in case_results
        ),
        "nonzero_mode2_energy_all_candidates": all(
            probe["formal_mode_energy_fraction"][2] > 0.0
            for case in case_results
            for probe in case["probe_schedules"]
        ),
        "bounded_and_zero_net_all_candidates": all(
            probe["formal_max_abs_component"] <= COMPONENT_ABS_LIMIT
            and probe["cancellation_max_abs_component"]
            <= COMPONENT_ABS_LIMIT
            and max(abs(x) for x in probe["requested_full_net"])
            <= ZERO_NET_TOLERANCE
            for case in case_results
            for probe in case["probe_schedules"]
        ),
        "first_cancellation_effect_state_exactly_39": all(
            probe["first_cancellation_effect_state"] == 39
            for case in case_results
            for probe in case["probe_schedules"]
        ),
    }
    return {
        "schema_version": 1,
        "audit_kind": "stage4_2r3c3t6_new_direction_design_preflight",
        "scientific_status": (
            "prospective identification design evidence only; no plant "
            "response, controller repair, or formal control validation"
        ),
        "real_tsc_executed": False,
        "action_coordinate": ACTION_FIELD,
        "formal_timing_unchanged": True,
        "formal_l2_limit": FORMAL_L2_LIMIT,
        "component_abs_limit": COMPONENT_ABS_LIMIT,
        "cancellation_effect_states": list(CANCELLATION_EFFECT_STATES),
        "episode_horizon_steps": EPISODE_HORIZON_STEPS,
        "candidate_count_per_actuator": 3,
        "prospective_context_count": 32,
        "prospective_task_count": 32 * (1 + 3 * 2),
        "inputs": {
            "r17": r17_auth,
            "r3c1": r3c1_auth,
            "eight_basis_bank": {
                "path": str(eight_basis_bank),
                "sha256": _sha256(eight_basis_bank),
                "sample_count": int(bank["sample_count"]),
                "basis_count": int(bank["basis_count"]),
            },
        },
        "method": {
            "formal_issue_rule": (
                "keep issue i only when i + delay + 1 <= formal_hold_step"
            ),
            "source_direction": (
                "R17 offset-minus-nominal target action delta projected "
                "outside the existing eight action schedules"
            ),
            "visible_directions": (
                "equal-context SVD of same-restart-state R3c1 offset-minus-"
                "nominal target action residual after old-span and source-"
                "direction removal"
            ),
            "runtime_information_boundary": (
                "directions are frozen by actuator delay/slew only; pair, "
                "history, hidden wire state, source actions, and future "
                "values are not runtime inputs"
            ),
        },
        "actuator_cases": case_results,
        "gates": gates,
        "all_preflight_gates_pass": all(gates.values()),
        "limitations": [
            "R3c1 and R17 are inspected development evidence, not independent confirmation.",
            "Action-schedule novelty does not prove plant-response novelty.",
            "Probe safety and response condition require new signed real TSC identification.",
            "Probe trajectories are identification data and are not demonstrations.",
            "No R3c4 controller execution is authorized by this preflight.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--r17-manifest", type=Path, required=True)
    parser.add_argument("--r3c1-run", type=Path, required=True)
    parser.add_argument("--r3c1-inventory", type=Path, required=True)
    parser.add_argument("--eight-basis-bank", type=Path, required=True)
    parser.add_argument("--required-r17-digest", required=True)
    parser.add_argument("--required-r3c1-digest", required=True)
    parser.add_argument("--required-bank-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit = build_audit(
        project_root=args.project_root.resolve(),
        r17_manifest=args.r17_manifest.resolve(),
        r3c1_run=args.r3c1_run.resolve(),
        r3c1_inventory=args.r3c1_inventory.resolve(),
        eight_basis_bank=args.eight_basis_bank.resolve(),
        required_r17_digest=args.required_r17_digest,
        required_r3c1_digest=args.required_r3c1_digest,
        required_bank_sha256=args.required_bank_sha256,
    )
    _write_json(args.output, audit)
    print(json.dumps(
        {
            "output": str(args.output),
            "all_preflight_gates_pass": audit["all_preflight_gates_pass"],
            "prospective_task_count": audit["prospective_task_count"],
            "case_summary": [
                {
                    "delay_steps": case["delay_steps"],
                    "slew_scale": case["slew_scale"],
                    "r17_relative_residual": case[
                        "r17_target_action_relative_residual"
                    ],
                    "matched_median_relative_residual": case[
                        "matched_visible_target_relative_residual"
                    ]["median"],
                    "augmented_rank": case["augmented_schedule_rank"],
                    "augmented_condition": case[
                        "augmented_schedule_normalized_condition"
                    ],
                    "minimum_candidate_coverage": case[
                        "candidate_subspace_coverage"
                    ]["minimum"],
                }
                for case in audit["actuator_cases"]
            ],
        },
        indent=2,
        sort_keys=True,
    ))


if __name__ == "__main__":
    main()
