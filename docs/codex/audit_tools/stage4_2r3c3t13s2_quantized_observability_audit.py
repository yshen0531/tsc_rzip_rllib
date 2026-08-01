#!/usr/bin/env python3
"""Read-only T13S2 Card15 and causal-observability audit.

The tool authenticates and reads the completed T13S1 raw files in place.  It
reconstructs the source Card15 current serialization for every transition and
audits exact collisions in a label-free causal feature.  It never runs a
controller, Ray, gotsc, TSC, or a plant step.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.core.coil_order import display_to_tsc
from tsc_rzip_rllib.core.inputa import format_number


SOURCE_STAGE = "Stage4.2R3c3T13S1"
STAGE = "Stage4.2R3c3T13S2"
AUDIT_IDENTITY = "exact_card15_and_causal_observable_sufficiency_v1"
CAMPAIGN_IDENTITY = "restart_issue_time_single_step_transition_sentinel_v1"
CONTROLLER_REVISION = "single_step_transition_probe_v42r3c3t13s1_v1"
EXPECTED_RAW_COUNT = 52
EXPECTED_RAW_BYTES = 2_463_366
EXPECTED_RAW_DIGEST = (
    "de2be508888aa503628538a795474fbf70788252e7913f87af7603c5bc034603"
)
EXPECTED_RUN_INVENTORY_SHA256 = (
    "b5ce7f65747a9ba085e9c8aa731e004070ec2428f09a27a908c23ea716c91eca"
)
EXPECTED_STATE_SHA256 = (
    "c07890533574dfc4e852af64091524b5786601b8aba195548ea31fd4765e05cc"
)
EXPECTED_MANIFEST_SHA256 = (
    "971f0b1fa0d5b13f17696e7f601acce750822b5a89afc6859bea222c6c972dd9"
)
EXPECTED_CONFIG_SHA256 = (
    "65ecef19c0444419e2eb05a13271e5571dbd0e1cb261c2e6b598c3c4fdc06354"
)
EXPECTED_PACKAGE_FINGERPRINT_SHA256 = (
    "136bdba75bcd0a5378fa15b7a2005c2f3c0d41bf9f1f39887d06e7a1bd1c6f17"
)
EXPECTED_INPUTA_SHA256 = (
    "33760858ae0f80efa0cd5c418707261e1cdab60c0c78707002406db5335b6767"
)
EXPECTED_COIL_ORDER_SHA256 = (
    "37e61407e8d2775647255d44f8308482707f612f6a19112949c283862d432a01"
)
ACTUATOR_RESIDUAL_GATE_A = 1e-9
DT_S = 0.01
RESPONSE_SCALES = np.asarray([0.03, 0.03, 0.1, 0.1, 2000.0])
SYMMETRY_GATE = 0.10
N_COILS = 14


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


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


def _inventory(paths: Iterable[Path], *, relative_to: Path) -> dict[str, Any]:
    rows = [
        {
            "path": path.relative_to(relative_to).as_posix(),
            "size_bytes": int(path.stat().st_size),
            "sha256": _sha256(path),
        }
        for path in sorted(paths)
        if path.is_file()
    ]
    return {
        "n_files": len(rows),
        "total_bytes": sum(int(row["size_bytes"]) for row in rows),
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


def _trajectory_currents(result: Mapping[str, Any]) -> np.ndarray:
    values = np.asarray(
        [row["currents_a_tsc"] for row in result["trajectory"]], dtype=float
    )
    if values.shape != (51, N_COILS) or not np.all(np.isfinite(values)):
        raise ValueError("T13S1 trajectory current shape/finite contract failed")
    return values


def _trace_actions(result: Mapping[str, Any]) -> np.ndarray:
    values = np.asarray(
        [row["action_norm_tsc"] for row in result["controller_trace"]],
        dtype=float,
    )
    if values.shape != (50, N_COILS) or not np.all(np.isfinite(values)):
        raise ValueError("T13S1 trace action shape/finite contract failed")
    return values


def _plant_features(result: Mapping[str, Any]) -> np.ndarray:
    y = np.asarray(
        [[row["R"], row["Z"], row["Ip"]] for row in result["trajectory"]],
        dtype=float,
    )
    if y.shape != (51, 3) or not np.all(np.isfinite(y)):
        raise ValueError("T13S1 plant feature shape/finite contract failed")
    velocity = np.zeros((51, 2), dtype=float)
    velocity[1:] = np.diff(y[:, :2], axis=0) / DT_S
    return np.column_stack((y[:, :2], velocity, y[:, 2]))


def _env_arrays(env: Mapping[str, Any]) -> dict[str, np.ndarray | float]:
    turns = display_to_tsc(
        np.asarray(env["turns_display_order"], dtype=float)
    ).reshape(N_COILS)
    minimum = display_to_tsc(
        np.asarray(env["min_current_a_display_order"], dtype=float)
    ).reshape(N_COILS)
    maximum = display_to_tsc(
        np.asarray(env["max_current_a_display_order"], dtype=float)
    ).reshape(N_COILS)
    max_delta = float(env["current_slew_a_per_ms"]) * float(env["dt_ms"])
    if (
        np.any(turns == 0.0)
        or np.any(minimum >= maximum)
        or not math.isfinite(max_delta)
        or max_delta <= 0.0
    ):
        raise ValueError("invalid authenticated T13S1 environment actuator data")
    return {
        "turns": turns,
        "minimum": minimum,
        "maximum": maximum,
        "max_delta": max_delta,
    }


def card15_quantized_next_current(
    current_a_tsc: Sequence[float],
    action_norm_tsc: Sequence[float],
    env: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply the exact runner clip and source Card15 text round-trip."""
    arrays = _env_arrays(env)
    current = np.asarray(current_a_tsc, dtype=float).reshape(N_COILS)
    action = np.clip(
        np.asarray(action_norm_tsc, dtype=float).reshape(N_COILS), -1.0, 1.0
    )
    unconstrained = current + action * float(arrays["max_delta"])
    desired = np.clip(unconstrained, arrays["minimum"], arrays["maximum"])
    desired_kat = desired * arrays["turns"] / 1000.0
    fields = [format_number(value) for value in desired_kat]
    parsed_kat = np.asarray([float(value.strip()) for value in fields])
    predicted = parsed_kat * 1000.0 / arrays["turns"]
    return {
        "predicted_current_a_tsc": predicted,
        "desired_current_a_tsc": desired,
        "unconstrained_current_a_tsc": unconstrained,
        "card15_fields": fields,
        "clipped_components": np.not_equal(desired, unconstrained),
        "zero_effect_active_components": np.logical_and(
            np.abs(action) > 0.0, np.equal(predicted, current)
        ),
        "max_delta_a": float(arrays["max_delta"]),
        "turns_tsc": np.asarray(arrays["turns"], dtype=float),
    }


def audit_actuator_transitions(
    results: Sequence[Mapping[str, Any]],
    env_by_experiment: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, list[np.ndarray]]]:
    residuals: list[np.ndarray] = []
    predicted_by_id: dict[str, list[np.ndarray]] = {}
    field_lengths: list[int] = []
    clipped = 0
    zero_effect = 0
    exact = 0
    within_gate = 0
    for result in results:
        experiment_id = str(result["experiment_id"])
        env = env_by_experiment[experiment_id]
        currents = _trajectory_currents(result)
        actions = _trace_actions(result)
        predicted_rows: list[np.ndarray] = []
        for step in range(50):
            reconstructed = card15_quantized_next_current(
                currents[step], actions[step], env
            )
            predicted = np.asarray(
                reconstructed["predicted_current_a_tsc"], dtype=float
            )
            observed = currents[step + 1]
            residual = predicted - observed
            residuals.append(residual)
            predicted_rows.append(predicted)
            field_lengths.extend(
                len(value) for value in reconstructed["card15_fields"]
            )
            clipped += int(np.sum(reconstructed["clipped_components"]))
            zero_effect += int(
                np.sum(reconstructed["zero_effect_active_components"])
            )
            exact += int(np.sum(np.equal(predicted, observed)))
            within_gate += int(
                np.sum(np.abs(residual) <= ACTUATOR_RESIDUAL_GATE_A)
            )
        predicted_by_id[experiment_id] = predicted_rows
    matrix = np.asarray(residuals, dtype=float).reshape(-1, N_COILS)
    n_components = int(matrix.size)
    return (
        {
            "run_count": len(results),
            "transition_count": int(matrix.shape[0]),
            "component_count": n_components,
            "expected_transition_count": 2600,
            "expected_component_count": 36400,
            "exact_component_count": exact,
            "within_1e_9_A_component_count": within_gate,
            "maximum_abs_residual_A": float(np.max(np.abs(matrix))),
            "rms_residual_A": float(np.sqrt(np.mean(matrix**2))),
            "clipped_component_count": clipped,
            "active_action_zero_effect_component_count": zero_effect,
            "minimum_card15_field_length": min(field_lengths),
            "maximum_card15_field_length": max(field_lengths),
            "actuator_reconstruction_passed": bool(
                len(results) == EXPECTED_RAW_COUNT
                and matrix.shape == (2600, N_COILS)
                and within_gate == n_components
            ),
        },
        predicted_by_id,
    )


def _causal_feature(
    result: Mapping[str, Any], *, issue_step: int
) -> dict[str, Any]:
    trajectory = list(result["trajectory"])
    trace = list(result["controller_trace"])
    spec = result["spec"]
    state = trajectory[issue_step]
    if issue_step == 0:
        velocity: list[float] | None = None
        velocity_unknown = True
        queue_before: Any = {
            "fresh_restart": True,
            "authenticated_delay_steps": int(spec["action_delay_steps"]),
        }
    else:
        previous = trajectory[issue_step - 1]
        velocity = [
            (float(state["R"]) - float(previous["R"])) / DT_S,
            (float(state["Z"]) - float(previous["Z"])) / DT_S,
        ]
        velocity_unknown = False
        queue_before = trace[issue_step - 1].get("queue_after", [])
    return {
        "formal_task_step": issue_step,
        "target_offsets": [
            float(spec["target_R_offset_m"]),
            float(spec["target_Z_offset_m"]),
            float(spec["target_Ip_offset_A"]),
        ],
        "current_measurement": {
            "R": float(state["R"]),
            "Z": float(state["Z"]),
            "Ip": float(state["Ip"]),
            "velocity_RZ_m_per_s": velocity,
            "initial_velocity_unknown": velocity_unknown,
            "currents_a_tsc": [float(x) for x in state["currents_a_tsc"]],
        },
        "causal_measurement_history": [
            {
                "R": float(row["R"]),
                "Z": float(row["Z"]),
                "Ip": float(row["Ip"]),
                "currents_a_tsc": [float(x) for x in row["currents_a_tsc"]],
            }
            for row in trajectory[: issue_step + 1]
        ],
        "already_issued_action_norm_tsc": [
            [float(x) for x in row["action_norm_tsc"]]
            for row in trace[:issue_step]
        ],
        "authenticated_queue_before": queue_before,
        "finite_development_actuator_setting": {
            "delay_steps": int(spec["action_delay_steps"]),
            "slew_scale": float(spec["slew_scale"]),
        },
    }


def _issue_record(result: Mapping[str, Any]) -> dict[str, Any]:
    spec = result["spec"]
    schedule = {
        int(step): value
        for step, value in spec["r3c3_probe_delta_by_task_issue_step"].items()
    }
    if len(schedule) != 2:
        raise ValueError("T13S1 signed record must have exactly two issues")
    issue_step = min(schedule)
    first_effect = int(spec["r3c3_probe_first_effect_state"])
    if first_effect not in (3, 17) or issue_step >= first_effect:
        raise ValueError("T13S1 issue/effect contract changed")
    feature = _causal_feature(result, issue_step=issue_step)
    trace_row = result["controller_trace"][issue_step]
    decision = [
        float(x) for x in trace_row["r3c3_probe_applied_desired_delta"]
    ]
    currents = _trajectory_currents(result)
    applied_path = np.diff(currents[issue_step : first_effect + 1], axis=0)
    plant = _plant_features(result)
    plant_increment = plant[first_effect] - plant[first_effect - 1]
    return {
        "development_identity": {
            "experiment_id": str(result["experiment_id"]),
            "pair_id": str(spec["pair_id"]),
            "history_member": str(spec["history_member"]),
            "target_id": str(spec["target_id"]),
            "probe_window": str(spec["r3c3_probe_window"]),
            "probe_mode": int(spec["r3c3_probe_mode"]),
            "probe_sign": int(spec["r3c3_probe_sign"]),
        },
        "issue_step": issue_step,
        "first_effect_state": first_effect,
        "causal_feature_sha256": _canonical_digest(feature),
        "causal_feature": feature,
        "numeric_decision": decision,
        "numeric_decision_sha256": _canonical_digest(decision),
        "observed_applied_current_path_A": applied_path.tolist(),
        "observed_applied_current_path_sha256": _canonical_digest(
            applied_path.tolist()
        ),
        "first_effect_plant_increment": plant_increment.tolist(),
        "first_effect_plant_increment_sha256": _canonical_digest(
            plant_increment.tolist()
        ),
    }


def classify_exact_collisions(
    issue_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    by_feature: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    by_feature_and_path: dict[tuple[str, str], list[Mapping[str, Any]]] = (
        defaultdict(list)
    )
    for row in issue_records:
        feature_hash = str(row["causal_feature_sha256"])
        path_hash = str(row["observed_applied_current_path_sha256"])
        by_feature[feature_hash].append(row)
        by_feature_and_path[(feature_hash, path_hash)].append(row)
    feature_collisions = [rows for rows in by_feature.values() if len(rows) > 1]
    same_path = [
        rows for rows in by_feature_and_path.values() if len(rows) > 1
    ]
    aliases = [
        rows
        for rows in same_path
        if len(
            {str(row["first_effect_plant_increment_sha256"]) for row in rows}
        )
        > 1
    ]
    return {
        "issue_record_count": len(issue_records),
        "exact_causal_feature_collision_group_count": len(feature_collisions),
        "exact_feature_and_applied_path_collision_group_count": len(same_path),
        "exact_observational_alias_group_count": len(aliases),
        "route": (
            "EXACT_OBSERVATIONAL_ALIAS_REQUIRES_SET_VALUED_MODEL"
            if aliases
            else "FINITE_CLEAN_SEPARATION_ONLY"
        ),
        "alias_groups": [
            [row["development_identity"] for row in rows] for rows in aliases
        ],
    }


def _relative(numerator: np.ndarray, denominator: np.ndarray) -> float:
    den = float(np.linalg.norm(np.asarray(denominator, dtype=float)))
    return float(np.linalg.norm(np.asarray(numerator, dtype=float)) / max(den, 1e-300))


def signed_first_effect_audit(
    results: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    baselines: dict[tuple[Any, ...], Mapping[str, Any]] = {}
    signed: dict[tuple[Any, ...], dict[int, Mapping[str, Any]]] = defaultdict(dict)
    for result in results:
        spec = result["spec"]
        sign = int(spec["r3c3_probe_sign"])
        context = _context_key(spec)
        if sign == 0:
            baselines[context] = result
        else:
            group = context + (
                str(spec["r3c3_probe_window"]),
                int(spec["r3c3_probe_mode"]),
            )
            signed[group][sign] = result
    if len(baselines) != 4 or len(signed) != 24:
        raise ValueError("T13S1 signed/baseline coverage changed")
    rows = []
    for group in sorted(signed):
        members = signed[group]
        if set(members) != {-1, 1}:
            raise ValueError("T13S1 signed member coverage changed")
        plus, minus = members[1], members[-1]
        baseline = baselines[group[:5]]
        first = int(plus["spec"]["r3c3_probe_first_effect_state"])
        issue = min(
            int(step)
            for step in plus["spec"]["r3c3_probe_delta_by_task_issue_step"]
        )
        p_decision = np.asarray(
            plus["controller_trace"][issue][
                "r3c3_probe_applied_desired_delta"
            ],
            dtype=float,
        )
        m_decision = np.asarray(
            minus["controller_trace"][issue][
                "r3c3_probe_applied_desired_delta"
            ],
            dtype=float,
        )
        decision_odd = (p_decision - m_decision) / 2.0
        decision_even = (p_decision + m_decision) / 2.0
        p_current = _trajectory_currents(plus)
        m_current = _trajectory_currents(minus)
        b_current = _trajectory_currents(baseline)
        current_odd = (p_current[first] - m_current[first]) / 2.0
        current_even = (
            (p_current[first] + m_current[first]) / 2.0 - b_current[first]
        )
        p_plant = _plant_features(plus)
        m_plant = _plant_features(minus)
        b_plant = _plant_features(baseline)
        plant_odd = (p_plant[first] - m_plant[first]) / (2.0 * RESPONSE_SCALES)
        plant_even = (
            (p_plant[first] + m_plant[first]) / 2.0 - b_plant[first]
        ) / RESPONSE_SCALES
        rows.append(
            {
                "pair_id": group[0],
                "history_member": group[1],
                "target_id": group[2],
                "actual_delay_steps": group[3],
                "actual_slew_scale": group[4],
                "probe_window": group[5],
                "probe_mode": group[6],
                "first_effect_state": first,
                "numeric_decision_even_to_odd": _relative(
                    decision_even, decision_odd
                ),
                "observed_current_even_to_odd": _relative(
                    current_even, current_odd
                ),
                "plant_first_effect_even_to_odd": _relative(
                    plant_even, plant_odd
                ),
            }
        )
    return {
        "group_count": len(rows),
        "numeric_decision_symmetry_pass_count": sum(
            row["numeric_decision_even_to_odd"] <= SYMMETRY_GATE for row in rows
        ),
        "observed_current_symmetry_pass_count": sum(
            row["observed_current_even_to_odd"] <= SYMMETRY_GATE for row in rows
        ),
        "plant_first_effect_symmetry_pass_count": sum(
            row["plant_first_effect_even_to_odd"] <= SYMMETRY_GATE for row in rows
        ),
        "rows": rows,
    }


def _scaled_snapshot_distance(
    left: Mapping[str, Any], right: Mapping[str, Any]
) -> dict[str, float | bool]:
    lf = left["causal_feature"]
    rf = right["causal_feature"]
    lm = lf["current_measurement"]
    rm = rf["current_measurement"]
    position_ip = np.asarray(
        [
            (float(lm["R"]) - float(rm["R"])) / 0.03,
            (float(lm["Z"]) - float(rm["Z"])) / 0.03,
            (float(lm["Ip"]) - float(rm["Ip"])) / 10000.0,
        ]
    )
    unknown = bool(lm["initial_velocity_unknown"] or rm["initial_velocity_unknown"])
    velocity_distance = 0.0
    if not unknown:
        velocity_distance = float(
            np.linalg.norm(
                (
                    np.asarray(lm["velocity_RZ_m_per_s"])
                    - np.asarray(rm["velocity_RZ_m_per_s"])
                )
                / 0.1
            )
        )
    coil_distance = float(
        np.linalg.norm(
            np.asarray(lm["currents_a_tsc"])
            - np.asarray(rm["currents_a_tsc"])
        )
    )
    prior_left = np.asarray(lf["already_issued_action_norm_tsc"], dtype=float)
    prior_right = np.asarray(rf["already_issued_action_norm_tsc"], dtype=float)
    prior_distance = (
        float(np.linalg.norm(prior_left - prior_right))
        if prior_left.shape == prior_right.shape
        else math.inf
    )
    return {
        "scaled_R_Z_Ip_l2": float(np.linalg.norm(position_ip)),
        "scaled_velocity_l2": velocity_distance,
        "initial_velocity_unknown": unknown,
        "coil_current_l2_A": coil_distance,
        "prior_action_l2": prior_distance,
        "exact_causal_feature_match": bool(
            left["causal_feature_sha256"] == right["causal_feature_sha256"]
        ),
    }


def matched_history_separation(
    issue_records: Sequence[Mapping[str, Any]],
    results_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    grouped: dict[tuple[Any, ...], dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for row in issue_records:
        ident = row["development_identity"]
        key = (
            ident["pair_id"],
            ident["target_id"],
            ident["probe_window"],
            ident["probe_mode"],
            ident["probe_sign"],
        )
        grouped[key][ident["history_member"]] = row
    rows = []
    for key in sorted(grouped):
        members = grouped[key]
        if set(members) != {"minus_first", "plus_first"}:
            raise ValueError("T13S1 matched-history issue coverage changed")
        minus = members["minus_first"]
        plus = members["plus_first"]
        issue = int(minus["issue_step"])
        minus_result = results_by_id[
            minus["development_identity"]["experiment_id"]
        ]
        plus_result = results_by_id[
            plus["development_identity"]["experiment_id"]
        ]
        minus_wire = np.asarray(
            minus_result["trajectory"][issue]["wire_currents_a"], dtype=float
        )
        plus_wire = np.asarray(
            plus_result["trajectory"][issue]["wire_currents_a"], dtype=float
        )
        rows.append(
            {
                "pair_id": key[0],
                "target_id": key[1],
                "probe_window": key[2],
                "probe_mode": key[3],
                "probe_sign": key[4],
                "allowed_causal_snapshot": _scaled_snapshot_distance(
                    plus, minus
                ),
                "offline_forbidden_wire_diagnostic": {
                    "used_in_causal_feature": False,
                    "l2_A": float(np.linalg.norm(plus_wire - minus_wire)),
                    "rms_A": float(
                        np.sqrt(np.mean((plus_wire - minus_wire) ** 2))
                    ),
                },
            }
        )
    return {
        "matched_history_pair_count": len(rows),
        "exact_allowed_causal_feature_match_count": sum(
            row["allowed_causal_snapshot"]["exact_causal_feature_match"]
            for row in rows
        ),
        "finite_clean_separation_count": sum(
            not row["allowed_causal_snapshot"]["exact_causal_feature_match"]
            for row in rows
        ),
        "rows": rows,
    }


def _load_authenticated_inputs(
    project_root: Path, run_dir: Path, audit_dir: Path
) -> tuple[
    list[dict[str, Any]],
    dict[str, Mapping[str, Any]],
    dict[str, Any],
    dict[str, Any],
]:
    fixed_files = {
        run_dir / "stage4_2r3c3t13s1_state.json": EXPECTED_STATE_SHA256,
        run_dir / "stage4_2r3c3t13s1_manifest.json": EXPECTED_MANIFEST_SHA256,
        run_dir
        / "stage4_2r3c3t13s1_config.resolved.json": EXPECTED_CONFIG_SHA256,
        run_dir
        / "stage4_2r3c3t13s1_source_reference"
        / "deployed_package_fingerprint.json": EXPECTED_PACKAGE_FINGERPRINT_SHA256,
    }
    for path, expected in fixed_files.items():
        if _sha256(path) != expected:
            raise ValueError(f"fixed T13S1 evidence hash mismatch: {path}")
    state = _read_json(run_dir / "stage4_2r3c3t13s1_state.json")
    if (
        not bool(state.get("finished"))
        or bool(state.get("primary_pass"))
        or state.get("stop_reason") != "sentinel_scientific_gate_failed"
    ):
        raise ValueError("T13S1 official state was reinterpreted or changed")
    package_fingerprint = _read_json(
        run_dir
        / "stage4_2r3c3t13s1_source_reference"
        / "deployed_package_fingerprint.json"
    )
    package_index = {row["path"]: row for row in package_fingerprint["files"]}
    source_paths = {
        "tsc_rzip_rllib/core/inputa.py": project_root
        / "tsc_rzip_rllib/core/inputa.py",
        "tsc_rzip_rllib/core/coil_order.py": project_root
        / "tsc_rzip_rllib/core/coil_order.py",
    }
    expected_source = {
        "tsc_rzip_rllib/core/inputa.py": EXPECTED_INPUTA_SHA256,
        "tsc_rzip_rllib/core/coil_order.py": EXPECTED_COIL_ORDER_SHA256,
    }
    for relative, path in source_paths.items():
        actual = _sha256(path)
        if actual != expected_source[relative] or actual != package_index[relative]["sha256"]:
            raise ValueError(f"deployed actuator source mismatch: {relative}")
    run_inventory_path = audit_dir / "stage4_2r3c3t13s1_run_inventory.json"
    if _sha256(run_inventory_path) != EXPECTED_RUN_INVENTORY_SHA256:
        raise ValueError("T13S1 official run inventory hash mismatch")
    run_inventory = _read_json(run_inventory_path)
    run_index = {row["path"]: row for row in run_inventory["files"]}
    raw_dir = run_dir / "stage4_2r3c3t13s1_minimal_transition_sentinel/raw"
    raw_paths = sorted(raw_dir.glob("*.json.gz"))
    raw_inventory = _inventory(raw_paths, relative_to=raw_dir)
    if (
        raw_inventory["n_files"] != EXPECTED_RAW_COUNT
        or raw_inventory["total_bytes"] != EXPECTED_RAW_BYTES
        or raw_inventory["digest"] != EXPECTED_RAW_DIGEST
    ):
        raise ValueError("T13S1 immutable raw inventory mismatch")
    results = []
    env_by_experiment: dict[str, Mapping[str, Any]] = {}
    for raw_path in raw_paths:
        result = _read_json_gz(raw_path)
        experiment_id = str(result.get("experiment_id", ""))
        if (
            raw_path.name != f"{experiment_id}.json.gz"
            or result.get("stage") != SOURCE_STAGE
            or result.get("campaign_identity") != CAMPAIGN_IDENTITY
            or result.get("controller_revision") != CONTROLLER_REVISION
            or not bool(result.get("success"))
            or not bool(result.get("completed"))
            or result.get("failure_reason")
            or len(result.get("trajectory", [])) != 51
            or len(result.get("controller_trace", [])) != 50
        ):
            raise ValueError(f"T13S1 raw authentication failed: {raw_path.name}")
        env_relative = (
            "stage4_2r3c3t13s1_environment_variants/"
            f"env_{experiment_id}.json"
        )
        env_path = run_dir / env_relative
        inventory_row = run_index.get(env_relative)
        if (
            inventory_row is None
            or int(inventory_row["size_bytes"]) != env_path.stat().st_size
            or str(inventory_row["sha256"]) != _sha256(env_path)
        ):
            raise ValueError(f"T13S1 environment inventory mismatch: {experiment_id}")
        env_by_experiment[experiment_id] = _read_json(env_path)
        results.append(result)
    return results, env_by_experiment, raw_inventory, {
        "run_inventory_sha256": _sha256(run_inventory_path),
        "inputa_sha256": _sha256(source_paths["tsc_rzip_rllib/core/inputa.py"]),
        "coil_order_sha256": _sha256(
            source_paths["tsc_rzip_rllib/core/coil_order.py"]
        ),
        "package_fingerprint_sha256": _sha256(
            run_dir
            / "stage4_2r3c3t13s1_source_reference"
            / "deployed_package_fingerprint.json"
        ),
        "environment_file_count": len(env_by_experiment),
    }


def run_audit(args: argparse.Namespace) -> dict[str, Any]:
    project_root = args.project_root.expanduser().resolve()
    run_dir = args.run_dir.expanduser().resolve()
    audit_dir = args.audit_dir.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    if output_dir.exists():
        raise ValueError("T13S2 output directory must be new")
    if run_dir == output_dir or run_dir in output_dir.parents:
        raise ValueError("T13S2 output may not be inside immutable run evidence")
    results, env_by_id, raw_inventory, source = _load_authenticated_inputs(
        project_root, run_dir, audit_dir
    )
    actuator, _ = audit_actuator_transitions(results, env_by_id)
    signed = signed_first_effect_audit(results)
    issue_records = [
        _issue_record(result)
        for result in results
        if int(result["spec"]["r3c3_probe_sign"]) != 0
    ]
    collisions = classify_exact_collisions(issue_records)
    results_by_id = {str(result["experiment_id"]): result for result in results}
    history = matched_history_separation(issue_records, results_by_id)
    if actuator["actuator_reconstruction_passed"]:
        primary_route = collisions["route"]
    else:
        primary_route = "ACTUATOR_MAPPING_IMPLEMENTATION_GAP"
    report = {
        "schema_version": 1,
        "stage": STAGE,
        "audit_identity": AUDIT_IDENTITY,
        "classification": "read_only_exact_actuator_and_causal_observability_audit",
        "source_run": str(run_dir),
        "source_audit": str(audit_dir),
        "source_provenance": source,
        "raw_inventory": raw_inventory,
        "official_t13s1_result_unchanged": {
            "route": "SENTINEL_FAIL_STOP_IDENTIFICATION",
            "thresholds_changed": False,
            "verdict_reinterpreted": False,
        },
        "actuator_reconstruction": actuator,
        "signed_first_effect_layers": signed,
        "causal_observability": collisions,
        "matched_history_clean_separation": history,
        "route": {
            "primary": primary_route,
            "required_interface": "QUANTIZED_MULTI_HYPOTHESIS_TUBE",
            "point_plant_model_certified": False,
            "new_identification_campaign_authorized": False,
            "real_mpc_authorized": False,
        },
        "issue_records": issue_records,
        "scientific_classification": {
            "runtime_or_environment_error": False,
            "packaging_or_import_error": False,
            "raw_or_snapshot_corruption": False,
            "statistics_or_reporting_error": False,
            "actuator_serialization_model_gap": not bool(
                actuator["actuator_reconstruction_passed"]
            ),
            "exact_observational_alias": bool(
                collisions["exact_observational_alias_group_count"]
            ),
            "finite_clean_separation_only": bool(
                not collisions["exact_observational_alias_group_count"]
            ),
            "observer_noise_and_history_extrapolation_validated": False,
            "real_mpc_tested": False,
            "real_tsc_executed": False,
            "global_reachability_or_unreachability_proven": False,
            "probe_trajectories_allowed_in_expert_dataset": False,
            "bc_dagger_or_rl_allowed": False,
        },
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    report_path = output_dir / "stage4_2r3c3t13s2_quantized_observability_audit.json"
    _write_json(report_path, report)
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "audit_identity": AUDIT_IDENTITY,
        "source_raw_inventory_digest": EXPECTED_RAW_DIGEST,
        "report": {
            "path": report_path.name,
            "size_bytes": int(report_path.stat().st_size),
            "sha256": _sha256(report_path),
        },
        "raw_files_copied_or_modified": 0,
        "controller_ray_gotsc_tsc_or_plant_steps_executed": 0,
    }
    manifest_path = (
        output_dir / "stage4_2r3c3t13s2_quantized_observability_manifest.json"
    )
    _write_json(manifest_path, manifest)
    return {
        "output_dir": str(output_dir),
        "report_sha256": _sha256(report_path),
        "manifest_sha256": _sha256(manifest_path),
        "primary_route": primary_route,
        "required_interface": "QUANTIZED_MULTI_HYPOTHESIS_TUBE",
        "actuator_reconstruction": actuator,
        "causal_observability": collisions,
        "matched_history_clean_separation": {
            key: value for key, value in history.items() if key != "rows"
        },
        "real_tsc_executed": False,
        "plant_steps_executed": 0,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--audit-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main() -> None:
    print(json.dumps(run_audit(_parser().parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
