#!/usr/bin/env python3
"""Audit the frozen Stage3.4 lifted Jacobian on existing restart raw only.

This tool never runs a controller, optimizer, Ray, gotsc, TSC, a plant step,
or snapshot creation. Large immutable raw is read in place on the server and
only compact audit files are written to a new output directory.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


STAGE = "Stage4.2R3c3T13"
IDENTITY = "time_resolved_stage3_4_restart_model_compatibility_v2"
DESIGN_SHA256 = "604ebc9139c334647ef4142e5427dbb04d667e008acf78317e24846cc87b24cd"
STAGE34_SOURCE_SHA256 = "a6097b8dea3293bdccf0e742ee86dc9df65b5318f2bd700ee4e5e81d72968f27"
STAGE34_BUNDLE_SHA256 = "7b307e82c35bc12beea51be303be90d0a5dd7554f54156e3684b167f37ee8987"
STAGE34_CONFIG_SHA256 = "6d705aaad12bc6872af776a0adf041041cbda38a4d545581017ad5ecdc7b34b4"
STAGE34_ENV_SHA256 = "a0ed368a4aeb93b0073ff46f90583a8d63c3ef076eeef6400460ec0cb50c546a"
STAGE34_MANIFEST_SHA256 = "f66b84d59f53ecc665571337726f2ad6c77a749059abc06ff96995589e9af460"
MODES_FLOAT64_SHA256 = "a6438d4d32cb00a391e0f4f1f9341b8ba162aeddf75cacb599ac433fe4af0b54"
RUNNER_SOURCE_SHA256 = "304e412d86220b871011c409b4e9c899149341c2c48499b1bbabfcafadbc0021"
INPUTA_SOURCE_SHA256 = "33760858ae0f80efa0cd5c418707261e1cdab60c0c78707002406db5335b6767"
ENV_SOURCE_SHA256 = "6bfe266533424d0a671369578bcd0458ce3a9823233ce2ef02df109d49a3b270"
STAGE1_SOURCE_SHA256 = "7214dea9d93364bd4cacd3d324f2156879fcf255a75c9a5ac7423e02d6acbb58"
NOMINAL_MAX_DELTA_A = 3.0
DT_S = 0.01
OUTPUT_SCALES = np.concatenate(
    [
        np.full(35, 0.03),
        np.full(35, 0.03),
        np.full(35, 0.1),
        np.full(35, 0.1),
        np.full(35, 2000.0),
    ]
)
CONTEXT_FIELDS = (
    "pair_id",
    "history_member",
    "target_id",
    "action_delay_steps",
    "slew_scale",
)

RUNS: dict[str, dict[str, Any]] = {
    "R3c3": {
        "stage": "Stage4.2R3c3",
        "run": "stage4_2r3c3_runs/stage4_2r3c3_restart_task_clock_local_response_identification_20260730_182427",
        "raw": "stage4_2r3c3_restart_task_clock_probe_identification/raw",
        "count": 256,
        "bytes": 8933607,
        "digest": "88bcd02a5dd2ec4def60c1f2e7f2304fb57859836d3b9a34b090bfd91e00e563",
        "trajectory": 36,
        "trace": 35,
        "baseline": None,
        "signed_pairs": 128,
        "nodes": 0,
    },
    "T1": {
        "stage": "Stage4.2R3c3T1",
        "run": "stage4_2r3c3t1_runs/stage4_2r3c3t1_long_separation_zero_net_transport_identification_20260730_204441",
        "raw": "stage4_2r3c3t1_transport_response_identification/raw",
        "count": 128,
        "bytes": 4505015,
        "digest": "f19a04dcb6b597e97517482d602a6cfdb3c0a1f0b4bfd7a1507b90ae2cc0876f",
        "trajectory": 36,
        "trace": 35,
        "baseline": None,
        "signed_pairs": 64,
        "nodes": 0,
    },
    "T2": {
        "stage": "Stage4.2R3c3T2",
        "run": "stage4_2r3c3t2_runs/stage4_2r3c3t2_post_contract_neutralized_held_transport_identification_20260730_225902",
        "raw": "stage4_2r3c3t2_held_transport_identification/raw",
        "count": 160,
        "bytes": 7404198,
        "digest": "e40dbf9b531886344bd97a18590db342897570ec8f21b18a37d16c4fb528c90f",
        "trajectory": 51,
        "trace": 50,
        "baseline": "held_transport_baseline",
        "signed_pairs": 64,
        "nodes": 128,
    },
    "T6": {
        "stage": "Stage4.2R3c3T6",
        "run": "stage4_2r3c3t6_runs/stage4_2r3c3t6_target_residual_new_direction_identification_20260731_040257",
        "raw": "stage4_2r3c3t6_target_residual_identification/raw",
        "count": 224,
        "bytes": 11124363,
        "digest": "594b4333eb848c762aec557744fe2dcef9101e1cc495f8713ed8bbe2f2913f61",
        "trajectory": 51,
        "trace": 50,
        "baseline": "target_residual_baseline",
        "signed_pairs": 96,
        "nodes": 192,
    },
    "T9": {
        "stage": "Stage4.2R3c3T9",
        "run": "stage4_2r3c3t9_runs/stage4_2r3c3t9_pc3_mixed_interaction_identification_20260731_090005",
        "raw": "stage4_2r3c3t9_pc3_mixed_interaction/raw",
        "count": 224,
        "bytes": 11204025,
        "digest": "e53f06fc772682d85144b578a915e614b1a5d24b34aea6dfa77ab35f5091eea2",
        "trajectory": 51,
        "trace": 50,
        "baseline": "pc3_mixed_interaction_baseline",
        "signed_pairs": 32,
        "nodes": 192,
    },
    "T11": {
        "stage": "Stage4.2R3c3T11",
        "run": "stage4_2r3c3t11_runs/stage4_2r3c3t11_persistent_step_response_identification_20260801_40944f9",
        "raw": "stage4_2r3c3t11_persistent_step_response_identification/raw",
        "count": 416,
        "bytes": 19273198,
        "digest": "f84fd31fcbe6db03bd9db0a1d694097b8532120915ec0e3e03668cff0dd908c3",
        "trajectory": 51,
        "trace": 50,
        "baseline": "persistent_step_baseline",
        "signed_pairs": 192,
        "nodes": 384,
    },
}

GATES = {
    "velocity_component_rmse_m_per_s": 0.008,
    "endpoint_late_response_speed_error_m_per_s": 0.004,
    "final_response_speed_error_m_per_s": 0.010,
    "position_rmse_m": 0.001,
    "ip_rmse_A": 30.0,
    "relative_response_l2": 0.10,
    "pre_effect_position_max_m": 1e-9,
    "pre_effect_velocity_max_m_per_s": 1e-7,
    "pre_effect_ip_max_A": 1e-4,
    "command_modal_residual_max_A": 1e-9,
}


@dataclass(frozen=True)
class Record:
    stage_name: str
    experiment_id: str
    spec: Mapping[str, Any]
    summary: Mapping[str, Any]
    y: np.ndarray
    u: np.ndarray


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


def _read_gz(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


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
        "total_bytes": sum(int(row["size_bytes"]) for row in rows),
        "digest": _canonical_digest(rows),
    }


def _context_key(spec: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        str(spec["pair_id"]),
        str(spec["history_member"]),
        str(spec["target_id"]),
        int(spec["action_delay_steps"]),
        float(spec["slew_scale"]),
    )


def _context_dict(spec: Mapping[str, Any]) -> dict[str, Any]:
    return dict(zip(CONTEXT_FIELDS, _context_key(spec)))


def _feature(trajectory: Sequence[Mapping[str, Any]]) -> np.ndarray:
    if len(trajectory) < 36:
        raise ValueError("trajectory is shorter than the Stage3.4 horizon")
    y = np.asarray(
        [[row["R"], row["Z"], row["Ip"]] for row in trajectory[:36]],
        dtype=float,
    )
    velocity = np.zeros((36, 2), dtype=float)
    velocity[1:] = np.diff(y[:, :2], axis=0) / DT_S
    return np.concatenate(
        [y[1:, 0], y[1:, 1], velocity[1:, 0], velocity[1:, 1], y[1:, 2]]
    )


def _input_sequence(
    trajectory: Sequence[Mapping[str, Any]],
    trace: Sequence[Mapping[str, Any]],
    *,
    slew_scale: float,
    modes: np.ndarray,
) -> tuple[np.ndarray, float, float, np.ndarray]:
    currents = np.asarray(
        [row["currents_a_tsc"] for row in trajectory[:36]], dtype=float
    )
    actions = np.asarray(
        [row["action_norm_tsc"] for row in trace[:35]], dtype=float
    )
    if currents.shape != (36, 14) or actions.shape != (35, 14):
        raise ValueError("unexpected current/action shape")
    observed_delta_i = np.diff(currents, axis=0)
    command_delta_i = actions * NOMINAL_MAX_DELTA_A * float(slew_scale)
    u = (command_delta_i / NOMINAL_MAX_DELTA_A) @ modes
    reconstructed = NOMINAL_MAX_DELTA_A * (u @ modes.T)
    command_modal_error = float(
        np.max(np.abs(command_delta_i - reconstructed))
    )
    observed_command_difference = np.abs(observed_delta_i - command_delta_i)
    observed_u = (observed_delta_i / NOMINAL_MAX_DELTA_A) @ modes
    observed_reconstructed = NOMINAL_MAX_DELTA_A * (observed_u @ modes.T)
    observed_modal_error = float(
        np.max(np.abs(observed_delta_i - observed_reconstructed))
    )
    return (
        u,
        command_modal_error,
        observed_modal_error,
        observed_command_difference,
    )


def _forbidden_contract_clean(raw: Mapping[str, Any]) -> bool:
    spec = raw["spec"]
    trace = raw["controller_trace"]
    return bool(
        not spec.get("hidden_wire_current_available_to_controller")
        and not spec.get("pair_or_history_label_available_to_controller")
        and not spec.get("source_action_available_to_controller")
        and not spec.get("source_coil_current_available_to_controller")
        and not spec.get("source_wire_current_available_to_controller")
        and not spec.get("source_result_available_to_controller")
        and int(spec.get("future_action_count", -1)) == 0
        and int(spec.get("future_measurement_count", -1)) == 0
        and all(
            not row.get("hidden_wire_used")
            and not row.get("pair_or_history_label_used")
            and not row.get("source_action_used")
            and not row.get("source_coil_current_used")
            and not row.get("source_wire_current_used")
            and not row.get("source_result_used")
            and not row.get("current_run_future_used")
            and not row.get("future_measurement_used")
            for row in trace
        )
    )


def _load_model(project_root: Path) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    stage34_run = (
        project_root
        / "stage3_4_runs/stage3_4_late_arrival_continuation_mpc_350ms_20260724_030829"
    )
    paths = {
        "source": project_root
        / "tsc_rzip_rllib/diagnostics/stage3_4_late_arrival_continuation_mpc.py",
        "config": stage34_run / "stage3_4_config.resolved.json",
        "env": stage34_run / "env_config.resolved.json",
        "manifest": stage34_run / "stage3_4_manifest.json",
        "bundle": stage34_run / "stage3_4_identification/full_horizon_bundle.json",
        "runner": project_root / "tsc_rzip_rllib/core/runner.py",
        "inputa": project_root / "tsc_rzip_rllib/core/inputa.py",
        "env_source": project_root / "tsc_rzip_rllib/envs/rzip_env.py",
        "stage1_source": project_root
        / "tsc_rzip_rllib/diagnostics/stage1_controllability.py",
    }
    expected = {
        "source": STAGE34_SOURCE_SHA256,
        "config": STAGE34_CONFIG_SHA256,
        "env": STAGE34_ENV_SHA256,
        "manifest": STAGE34_MANIFEST_SHA256,
        "bundle": STAGE34_BUNDLE_SHA256,
        "runner": RUNNER_SOURCE_SHA256,
        "inputa": INPUTA_SOURCE_SHA256,
        "env_source": ENV_SOURCE_SHA256,
        "stage1_source": STAGE1_SOURCE_SHA256,
    }
    hashes = {name: _sha256(path) for name, path in paths.items()}
    if hashes != expected:
        raise ValueError(f"Stage3.4 source/model hash mismatch: {hashes}")
    bundle = _read_json(paths["bundle"])
    jacobian = np.asarray(bundle["jacobian_physical_units"], dtype=float)
    if jacobian.shape != (175, 105):
        raise ValueError("Stage3.4 Jacobian shape mismatch")
    if bool(bundle["online_feedback_validated"]) or bool(
        bundle["robustness_validated"]
    ):
        raise ValueError("Stage3.4 bundle unsupported claim changed")

    sys.path.insert(0, str(project_root))
    old_project = os.environ.get("PROJECT_DIR")
    old_root = os.environ.get("TSC_ALL_ROOT")
    os.environ["PROJECT_DIR"] = str(project_root)
    os.environ["TSC_ALL_ROOT"] = str(project_root.parent)
    try:
        from tsc_rzip_rllib.diagnostics import (
            stage3_4_late_arrival_continuation_mpc as s34,
        )

        manifest = _read_json(paths["manifest"])
        ctx = s34.load_stage34_config(
            paths["config"],
            source_stage33_run=manifest["source_stage3_3_run"],
            run_dir_override=stage34_run,
        )
        modes = np.asarray(ctx.modes_tsc, dtype=np.float64)
        max_delta = float(ctx.max_delta_a)
    finally:
        if old_project is None:
            os.environ.pop("PROJECT_DIR", None)
        else:
            os.environ["PROJECT_DIR"] = old_project
        if old_root is None:
            os.environ.pop("TSC_ALL_ROOT", None)
        else:
            os.environ["TSC_ALL_ROOT"] = old_root
    if (
        modes.shape != (14, 3)
        or hashlib.sha256(modes.tobytes(order="C")).hexdigest()
        != MODES_FLOAT64_SHA256
        or not math.isclose(max_delta, NOMINAL_MAX_DELTA_A, abs_tol=1e-15)
        or float(np.max(np.abs(modes.T @ modes - np.eye(3)))) > 1e-12
    ):
        raise ValueError("Stage3.4 mode basis identity mismatch")
    return jacobian, modes, hashes


def _load_raw(
    project_root: Path, modes: np.ndarray
) -> tuple[dict[str, list[Record]], dict[str, Any]]:
    all_records: dict[str, list[Record]] = {}
    authentication: dict[str, Any] = {}
    all_ids: set[str] = set()
    global_command_modal_error = 0.0
    global_observed_modal_error = 0.0
    observed_mismatch_by_slew: dict[str, float] = defaultdict(float)
    observed_mismatch_by_coil = np.zeros(14, dtype=float)
    for stage_name, contract in RUNS.items():
        raw_dir = project_root / contract["run"] / contract["raw"]
        paths = sorted(raw_dir.glob("*.json.gz"))
        inventory = _inventory(paths)
        if (
            int(inventory["n_files"]) != int(contract["count"])
            or int(inventory["total_bytes"]) != int(contract["bytes"])
            or str(inventory["digest"]) != str(contract["digest"])
        ):
            raise ValueError(f"{stage_name} raw inventory mismatch: {inventory}")
        records: list[Record] = []
        max_command_modal_error = 0.0
        max_observed_modal_error = 0.0
        max_observed_command_difference = 0.0
        contexts: set[tuple[Any, ...]] = set()
        for path in paths:
            raw = _read_gz(path)
            experiment_id = str(raw.get("experiment_id", ""))
            if (
                not experiment_id
                or experiment_id in all_ids
                or raw.get("stage") != contract["stage"]
                or not bool(raw.get("success"))
                or not bool(raw.get("completed"))
                or len(raw.get("trajectory", [])) != int(contract["trajectory"])
                or len(raw.get("controller_trace", [])) != int(contract["trace"])
                or not _forbidden_contract_clean(raw)
            ):
                raise ValueError(f"{stage_name} raw authentication failed: {path.name}")
            all_ids.add(experiment_id)
            spec = raw["spec"]
            (
                u,
                command_modal_error,
                observed_modal_error,
                observed_command_difference,
            ) = _input_sequence(
                raw["trajectory"],
                raw["controller_trace"],
                slew_scale=float(spec["slew_scale"]),
                modes=modes,
            )
            if (
                command_modal_error > GATES["command_modal_residual_max_A"]
                or not np.all(np.isfinite(u))
                or not np.all(np.isfinite(observed_command_difference))
            ):
                raise ValueError(
                    f"{stage_name} applied-input reconstruction failed: {path.name}; "
                    f"command_modal={command_modal_error}"
                )
            max_command_modal_error = max(
                max_command_modal_error, command_modal_error
            )
            max_observed_modal_error = max(
                max_observed_modal_error, observed_modal_error
            )
            observed_max = float(np.max(observed_command_difference))
            max_observed_command_difference = max(
                max_observed_command_difference, observed_max
            )
            slew_key = str(float(spec["slew_scale"]))
            observed_mismatch_by_slew[slew_key] = max(
                observed_mismatch_by_slew[slew_key], observed_max
            )
            observed_mismatch_by_coil = np.maximum(
                observed_mismatch_by_coil,
                np.max(observed_command_difference, axis=0),
            )
            contexts.add(_context_key(spec))
            records.append(
                Record(
                    stage_name=stage_name,
                    experiment_id=experiment_id,
                    spec=spec,
                    summary=raw.get("hidden_history_control_summary") or {},
                    y=_feature(raw["trajectory"]),
                    u=u,
                )
            )
        if len(contexts) != 32:
            raise ValueError(f"{stage_name} context count mismatch")
        all_records[stage_name] = records
        authentication[stage_name] = {
            "raw_count": len(records),
            "total_bytes": int(inventory["total_bytes"]),
            "inventory_digest": inventory["digest"],
            "context_count": len(contexts),
            "success_completed_count": len(records),
            "forbidden_contract_clean_count": len(records),
            "maximum_command_modal_residual_A": max_command_modal_error,
            "maximum_observed_current_modal_residual_A": max_observed_modal_error,
            "maximum_observed_current_command_difference_A": (
                max_observed_command_difference
            ),
        }
        global_command_modal_error = max(
            global_command_modal_error, max_command_modal_error
        )
        global_observed_modal_error = max(
            global_observed_modal_error, max_observed_modal_error
        )
    authentication["total"] = {
        "raw_count": sum(len(rows) for rows in all_records.values()),
        "total_bytes": sum(int(RUNS[name]["bytes"]) for name in RUNS),
        "unique_experiment_id_count": len(all_ids),
        "maximum_command_modal_residual_A": global_command_modal_error,
        "maximum_observed_current_modal_residual_A": (
            global_observed_modal_error
        ),
        "maximum_observed_current_command_difference_by_slew_A": dict(
            sorted(observed_mismatch_by_slew.items())
        ),
        "maximum_observed_current_command_difference_by_coil_A": (
            observed_mismatch_by_coil.tolist()
        ),
    }
    if authentication["total"]["raw_count"] != 1408:
        raise ValueError("global raw count mismatch")
    return all_records, authentication


def _first_effect_state(delta_u: np.ndarray) -> int | None:
    active = np.flatnonzero(np.max(np.abs(delta_u), axis=1) > 1e-12)
    return None if not len(active) else int(active[0]) + 1


def _prediction_metrics(
    actual: np.ndarray,
    predicted: np.ndarray,
    delta_u: np.ndarray,
    *,
    expected_first_effect_state: int | None,
) -> dict[str, Any]:
    actual = np.asarray(actual, dtype=float).reshape(175)
    predicted = np.asarray(predicted, dtype=float).reshape(175)
    error = predicted - actual
    r, z, vr, vz, ip = [actual[index * 35 : (index + 1) * 35] for index in range(5)]
    pr, pz, pvr, pvz, pip = [
        predicted[index * 35 : (index + 1) * 35] for index in range(5)
    ]
    position_rmse = float(
        np.sqrt(np.mean(np.concatenate([pr - r, pz - z]) ** 2))
    )
    velocity_rmse = float(
        np.sqrt(np.mean(np.concatenate([pvr - vr, pvz - vz]) ** 2))
    )
    ip_rmse = float(np.sqrt(np.mean((pip - ip) ** 2)))
    actual_speed = np.sqrt(vr**2 + vz**2)
    predicted_speed = np.sqrt(pvr**2 + pvz**2)
    endpoint_error = float(
        abs(
            np.sqrt(np.mean(actual_speed[31:35] ** 2))
            - np.sqrt(np.mean(predicted_speed[31:35] ** 2))
        )
    )
    final_error = float(abs(actual_speed[34] - predicted_speed[34]))
    relative_l2 = float(
        np.linalg.norm(error / OUTPUT_SCALES)
        / max(float(np.linalg.norm(actual / OUTPUT_SCALES)), 1e-12)
    )
    first_effect = _first_effect_state(delta_u)
    pre_count = 0 if first_effect is None else first_effect - 1
    if pre_count:
        position_pre = float(
            max(
                np.max(np.abs(r[:pre_count])),
                np.max(np.abs(z[:pre_count])),
                np.max(np.abs(pr[:pre_count])),
                np.max(np.abs(pz[:pre_count])),
            )
        )
        velocity_pre = float(
            max(
                np.max(np.abs(vr[:pre_count])),
                np.max(np.abs(vz[:pre_count])),
                np.max(np.abs(pvr[:pre_count])),
                np.max(np.abs(pvz[:pre_count])),
            )
        )
        ip_pre = float(
            max(np.max(np.abs(ip[:pre_count])), np.max(np.abs(pip[:pre_count])))
        )
    else:
        position_pre = velocity_pre = ip_pre = 0.0
    first_effect_match = bool(
        first_effect is not None
        and (
            expected_first_effect_state is None
            or first_effect == int(expected_first_effect_state)
        )
    )
    metrics = {
        "velocity_component_rmse_m_per_s": velocity_rmse,
        "endpoint_late_response_speed_error_m_per_s": endpoint_error,
        "final_response_speed_error_m_per_s": final_error,
        "position_rmse_m": position_rmse,
        "ip_rmse_A": ip_rmse,
        "relative_response_l2": relative_l2,
        "first_reconstructed_effect_state": first_effect,
        "expected_first_effect_state": expected_first_effect_state,
        "first_effect_state_match": first_effect_match,
        "pre_effect_position_max_m": position_pre,
        "pre_effect_velocity_max_m_per_s": velocity_pre,
        "pre_effect_ip_max_A": ip_pre,
    }
    metrics["prediction_gate_pass"] = bool(
        velocity_rmse <= GATES["velocity_component_rmse_m_per_s"]
        and endpoint_error
        <= GATES["endpoint_late_response_speed_error_m_per_s"]
        and final_error <= GATES["final_response_speed_error_m_per_s"]
        and position_rmse <= GATES["position_rmse_m"]
        and ip_rmse <= GATES["ip_rmse_A"]
        and relative_l2 <= GATES["relative_response_l2"]
    )
    metrics["causality_gate_pass"] = bool(
        first_effect_match
        and position_pre <= GATES["pre_effect_position_max_m"]
        and velocity_pre <= GATES["pre_effect_velocity_max_m_per_s"]
        and ip_pre <= GATES["pre_effect_ip_max_A"]
    )
    metrics["all_gates_pass"] = bool(
        metrics["prediction_gate_pass"] and metrics["causality_gate_pass"]
    )
    return metrics


def _expected_effect(record: Record) -> int | None:
    value = record.summary.get("probe_first_effect_state")
    if value is None:
        value = record.spec.get("r3c3_probe_first_effect_state")
    return None if value is None else int(value)


def _comparison_row(
    *,
    tier: str,
    stage_name: str,
    family: str,
    spec: Mapping[str, Any],
    experiment_ids: Sequence[str],
    actual: np.ndarray,
    delta_u: np.ndarray,
    jacobian: np.ndarray,
    expected_first_effect_state: int | None,
) -> dict[str, Any]:
    predicted = jacobian @ np.asarray(delta_u, dtype=float).reshape(105)
    return {
        "tier": tier,
        "stage": stage_name,
        "family": family,
        **_context_dict(spec),
        "prefix": str(spec["pair_id"]).split("_", 1)[0],
        "experiment_ids": list(experiment_ids),
        **_prediction_metrics(
            actual,
            predicted,
            delta_u,
            expected_first_effect_state=expected_first_effect_state,
        ),
    }


def _signed_rows(
    records: Mapping[str, Sequence[Record]], jacobian: np.ndarray
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for stage_name, stage_records in records.items():
        groups: dict[tuple[Any, ...], list[Record]] = defaultdict(list)
        for record in stage_records:
            if stage_name == "T9" and record.spec.get("r3c3t9_probe_family") != "standalone_pc3":
                continue
            sign = int(record.spec["r3c3_probe_sign"])
            if sign not in (-1, 1):
                continue
            groups[_context_key(record.spec) + (str(record.spec["r3c3_probe_id"]),)].append(record)
        for key in sorted(groups):
            rows = groups[key]
            by_sign = {int(row.spec["r3c3_probe_sign"]): row for row in rows}
            if len(rows) != 2 or set(by_sign) != {-1, 1}:
                raise ValueError(f"signed-pair coverage mismatch: {stage_name} {key}")
            minus, plus = by_sign[-1], by_sign[1]
            expected_values = {_expected_effect(minus), _expected_effect(plus)}
            if len(expected_values) != 1:
                raise ValueError("signed-pair effect-state contract mismatch")
            output.append(
                _comparison_row(
                    tier="signed",
                    stage_name=stage_name,
                    family=str(plus.spec["r3c3_probe_id"]),
                    spec=plus.spec,
                    experiment_ids=(minus.experiment_id, plus.experiment_id),
                    actual=(plus.y - minus.y) / 2.0,
                    delta_u=(plus.u - minus.u) / 2.0,
                    jacobian=jacobian,
                    expected_first_effect_state=expected_values.pop(),
                )
            )
        if len(groups) != int(RUNS[stage_name]["signed_pairs"]):
            raise ValueError(f"{stage_name} signed-pair count mismatch")
    if len(output) != 576:
        raise ValueError("global signed-pair count mismatch")
    return output


def _node_rows(
    records: Mapping[str, Sequence[Record]], jacobian: np.ndarray
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for stage_name, contract in RUNS.items():
        baseline_id = contract["baseline"]
        if baseline_id is None:
            continue
        by_context: dict[tuple[Any, ...], list[Record]] = defaultdict(list)
        for record in records[stage_name]:
            by_context[_context_key(record.spec)].append(record)
        for key in sorted(by_context):
            rows = by_context[key]
            baselines = [
                row for row in rows if str(row.spec["r3c3_probe_id"]) == baseline_id
            ]
            if len(baselines) != 1:
                raise ValueError(f"{stage_name} baseline coverage mismatch: {key}")
            baseline = baselines[0]
            for node in rows:
                if node is baseline:
                    continue
                output.append(
                    _comparison_row(
                        tier="finite_node",
                        stage_name=stage_name,
                        family=str(node.spec["r3c3_probe_id"]),
                        spec=node.spec,
                        experiment_ids=(baseline.experiment_id, node.experiment_id),
                        actual=node.y - baseline.y,
                        delta_u=node.u - baseline.u,
                        jacobian=jacobian,
                        expected_first_effect_state=_expected_effect(node),
                    )
                )
        actual_count = sum(
            1
            for row in output
            if row["stage"] == stage_name and row["tier"] == "finite_node"
        )
        if actual_count != int(contract["nodes"]):
            raise ValueError(f"{stage_name} finite-node count mismatch")
    if len(output) != 896:
        raise ValueError("global finite-node count mismatch")
    return output


def _interaction_rows(
    records: Mapping[str, Sequence[Record]], jacobian: np.ndarray
) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[Record]] = defaultdict(list)
    for record in records["T9"]:
        if record.spec.get("r3c3t9_probe_family") == "mixed_factorial":
            groups[_context_key(record.spec)].append(record)
    output: list[dict[str, Any]] = []
    for key in sorted(groups):
        rows = groups[key]
        by_sign = {
            (
                int(row.spec["r3c3t9_stress_sign"]),
                int(row.spec["r3c3t9_pc3_sign"]),
            ): row
            for row in rows
        }
        required = {(1, 1), (1, -1), (-1, 1), (-1, -1)}
        if len(rows) != 4 or set(by_sign) != required:
            raise ValueError(f"T9 interaction coverage mismatch: {key}")
        pp, pm, mp, mm = (
            by_sign[(1, 1)],
            by_sign[(1, -1)],
            by_sign[(-1, 1)],
            by_sign[(-1, -1)],
        )
        output.append(
            _comparison_row(
                tier="interaction",
                stage_name="T9",
                family="stress_by_pc3_walsh_interaction",
                spec=pp.spec,
                experiment_ids=(
                    pp.experiment_id,
                    pm.experiment_id,
                    mp.experiment_id,
                    mm.experiment_id,
                ),
                actual=(pp.y - pm.y - mp.y + mm.y) / 4.0,
                delta_u=(pp.u - pm.u - mp.u + mm.u) / 4.0,
                jacobian=jacobian,
                expected_first_effect_state=None,
            )
        )
    if len(output) != 32:
        raise ValueError("T9 interaction count mismatch")
    return output


def _tier_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    metric_names = tuple(GATES)[:6]
    failures = [dict(row) for row in rows if not bool(row["all_gates_pass"])]
    pass_count = len(rows) - len(failures)
    by_stage = Counter(str(row["stage"]) for row in rows)
    pass_by_stage = Counter(
        str(row["stage"]) for row in rows if bool(row["all_gates_pass"])
    )
    by_prefix = Counter(str(row["prefix"]) for row in failures)
    by_target = Counter(str(row["target_id"]) for row in failures)
    by_actuator = Counter(
        f"delay{row['action_delay_steps']}_slew{row['slew_scale']}"
        for row in failures
    )
    return {
        "comparison_count": len(rows),
        "pass_count": pass_count,
        "fail_count": len(failures),
        "tier_pass": pass_count == len(rows),
        "maximum_metrics": {
            name: max(float(row[name]) for row in rows) for name in metric_names
        },
        "counts_by_stage": dict(sorted(by_stage.items())),
        "pass_counts_by_stage": dict(sorted(pass_by_stage.items())),
        "failure_counts_by_prefix": dict(sorted(by_prefix.items())),
        "failure_counts_by_target": dict(sorted(by_target.items())),
        "failure_counts_by_actuator": dict(sorted(by_actuator.items())),
        "failure_rows": failures,
    }


def run_audit(args: argparse.Namespace) -> dict[str, Any]:
    project_root = args.project_root.expanduser().resolve()
    design = args.design.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if _sha256(design) != DESIGN_SHA256:
        raise ValueError("T13 prospective design hash mismatch")
    if output.exists():
        raise ValueError("T13 output directory must be new")
    for contract in RUNS.values():
        run = (project_root / contract["run"]).resolve()
        if output == run or run in output.parents:
            raise ValueError("T13 output may not be inside immutable raw evidence")

    jacobian, modes, model_hashes = _load_model(project_root)
    records, authentication = _load_raw(project_root, modes)
    signed = _signed_rows(records, jacobian)
    nodes = _node_rows(records, jacobian)
    interactions = _interaction_rows(records, jacobian)
    tiers = {
        "signed": _tier_summary(signed),
        "finite_node": _tier_summary(nodes),
        "interaction": _tier_summary(interactions),
    }
    all_tiers_pass = all(bool(row["tier_pass"]) for row in tiers.values())
    route = {
        "stage3_4_unqualified_restart_predictor_vetoed": not all_tiers_pass,
        "stage3_4_predictor_eligible_for_remaining_offline_t13": all_tiers_pass,
        "t13_final_route_decision_made": False,
        "provisional_next_step": (
            "complete_remaining_offline_architecture_and_terminal-tail evidence map"
            if all_tiers_pass
            else "specify one state-and-issue-time-conditioned minimal sentinel"
        ),
        "full_identification_campaign_authorized": False,
        "real_controller_authorized": False,
        "r3c4_authorized": False,
        "bc_dagger_or_residual_rl_authorized": False,
    }
    provenance = {
        "stage": STAGE,
        "identity": IDENTITY,
        "design_sha256": DESIGN_SHA256,
        "project_root": str(project_root),
        "model_hashes": model_hashes,
        "modes_float64_sha256": MODES_FLOAT64_SHA256,
        "raw_inventory_digests": {
            name: contract["digest"] for name, contract in RUNS.items()
        },
        "formal_timing_changed": False,
    }
    provenance_digest = _canonical_digest(provenance)
    audit = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "classification": "read_only_existing_raw_prediction_model_audit",
        "provenance": provenance,
        "provenance_digest": provenance_digest,
        "raw_authentication": authentication,
        "gates": GATES,
        "tiers": tiers,
        "route": route,
        "scientific_classification": {
            "runtime_or_environment_error": False,
            "packaging_or_import_error": False,
            "raw_or_snapshot_corruption": False,
            "statistics_or_reporting_error": False,
            "prediction_model_design_gap": not all_tiers_pass,
            "real_tsc_executed_by_t13": False,
            "real_controller_or_optimizer_executed_by_t13": False,
            "plant_steps_executed_by_t13": 0,
            "real_closed_loop_conclusion": "not_tested",
            "global_reachability_conclusion": "not_tested",
        },
        "structural_limitations": {
            "prediction_horizon_ends_at_state": 35,
            "weak_slew_formal_hold_ends_at_state": 37,
            "state_36_37_modeled_by_this_audit": False,
            "absolute_restart_prediction_tested": False,
            "arbitrary_per_step_sequence_validated": False,
        },
        "audit_complete": True,
    }

    output.mkdir(parents=True, exist_ok=False)
    audit_path = output / "stage4_2r3c3t13_time_resolved_model_audit_v2.json"
    route_path = output / "stage4_2r3c3t13_time_resolved_model_route_v2.json"
    _write_json(audit_path, audit)
    _write_json(
        route_path,
        {
            "schema_version": 1,
            "stage": STAGE,
            "identity": IDENTITY,
            "provenance_digest": provenance_digest,
            "tier_results": {
                name: {
                    "comparison_count": row["comparison_count"],
                    "pass_count": row["pass_count"],
                    "fail_count": row["fail_count"],
                    "tier_pass": row["tier_pass"],
                }
                for name, row in tiers.items()
            },
            "route": route,
            "formal_timing_changed": False,
            "real_tsc_executed": False,
            "real_controller_executed": False,
        },
    )
    manifest_path = output / "stage4_2r3c3t13_time_resolved_model_manifest_v2.json"
    _write_json(
        manifest_path,
        {
            "schema_version": 1,
            "stage": STAGE,
            "identity": IDENTITY,
            "provenance_digest": provenance_digest,
            "output_files": [
                {
                    "path": path.name,
                    "size_bytes": path.stat().st_size,
                    "sha256": _sha256(path),
                }
                for path in (audit_path, route_path)
            ],
            "raw_files_copied_or_modified": 0,
            "ray_gotsc_tsc_controller_or_optimizer_executed": False,
        },
    )
    return {
        "output": str(output),
        "audit_sha256": _sha256(audit_path),
        "route_sha256": _sha256(route_path),
        "manifest_sha256": _sha256(manifest_path),
        "tier_results": {
            name: {
                "comparison_count": row["comparison_count"],
                "pass_count": row["pass_count"],
                "fail_count": row["fail_count"],
                "tier_pass": row["tier_pass"],
            }
            for name, row in tiers.items()
        },
        "route": route,
        "real_tsc_executed": False,
        "real_controller_executed": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    print(
        json.dumps(
            run_audit(_parser().parse_args()),
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
