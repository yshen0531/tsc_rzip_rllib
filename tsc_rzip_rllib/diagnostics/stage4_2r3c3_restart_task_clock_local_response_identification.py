"""Stage4.2R3c3 bounded task-clock response identification.

Every authentic R3b restart context runs the exact R3c1 target-conditioned
baseline with a preregistered, bidirectional, zero-net physical-mode probe.
The probe schedule is task-relative and remains inside the unchanged
scheduler, delay queue, and physical limits.  This is identification only,
not a candidate control or formal-closure campaign.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import time
import traceback
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

try:
    import resource
except ImportError:  # pragma: no cover - Windows validation host
    resource = None

from . import (
    stage4_2r3c2_restart_target_state_regulation_mpc as r3c2,
    stage4_2r3c1_authenticated_visible_manifold_phase_mpc as r3c1,
    stage4_2r3b_confirmatory_hidden_history_initial_state as r3b,
)
from tsc_rzip_rllib.utils.ray_runtime import ensure_ray_worker_plan


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3"
CONTROLLER_REVISION = "restart_task_clock_local_response_probe_v42r3c3"
PACKAGE_REVISION = "r42r3c3_restart_task_clock_local_response_identification_v1"
N_COILS = r3b.N_COILS
N_MODES = r3b.N_MODES
N_WIRES = r3b.N_WIRES
NORMAL_HORIZON = r3b.NORMAL_HORIZON
WEAK_HORIZON = r3b.WEAK_HORIZON

r1 = r3b.r1
r2 = r3b.r2
read_json = r3b.read_json
read_json_gz = r3b.read_json_gz
atomic_write_json = r3b.atomic_write_json
atomic_write_json_gz = r3b.atomic_write_json_gz
write_csv = r3b.write_csv
utc_timestamp = r3b.utc_timestamp


def _json_safe(value: Any) -> Any:
    return r3b._json_safe(value)


def _sha256_file(path: Path) -> str:
    return r3b._sha256_file(path)


def _canonical_digest(value: Any) -> str:
    payload = json.dumps(
        _json_safe(value),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _scenario_digest(value: Mapping[str, Any]) -> str:
    return "s42r3c3_" + _canonical_digest(dict(value))[:20]


def _formal_horizon(slew: float) -> int:
    return (
        WEAK_HORIZON
        if math.isclose(float(slew), 0.9, abs_tol=1e-12)
        else NORMAL_HORIZON
    )


def _requested_workers(cfg: Mapping[str, Any]) -> int:
    fixed = int(cfg["parallel"]["n_workers"])
    requested = int(os.environ.get("STAGE4_2R3C3_WORKERS", fixed))
    if requested != fixed:
        raise ValueError(
            f"Stage4.2R3c3 Ray capacity is frozen at {fixed}, got {requested}"
        )
    return requested


def select_visible_reference_phase(
    reference_rzi: np.ndarray,
    current_rzi: Sequence[float],
    *,
    candidate_min_phase: int,
    candidate_max_phase: int,
    scales: Sequence[float],
) -> dict[str, Any]:
    """Choose the earliest phase on a frozen visible R/Z/Ip manifold."""

    reference = np.asarray(reference_rzi, dtype=float)
    current = np.asarray(current_rzi, dtype=float).reshape(3)
    scale = np.asarray(scales, dtype=float).reshape(3)
    lower = int(candidate_min_phase)
    upper = int(candidate_max_phase)
    if (
        reference.ndim != 2
        or reference.shape[1] != 3
        or lower < 0
        or upper < lower
        or upper >= len(reference)
        or not np.all(np.isfinite(reference))
        or not np.all(np.isfinite(current))
        or not np.all(np.isfinite(scale))
        or np.any(scale <= 0.0)
    ):
        raise ValueError("invalid visible-state phase-selection input")
    candidates = np.arange(lower, upper + 1, dtype=int)
    residual = (
        current[None, :] - reference[candidates]
    ) / scale[None, :]
    costs = np.sum(residual**2, axis=1)
    local = int(np.argmin(costs))
    selected = int(candidates[local])
    return {
        "selected_phase": selected,
        "selected_cost": float(costs[local]),
        "candidate_min_phase": lower,
        "candidate_max_phase": upper,
        "scales": scale.tolist(),
        "costs": [
            {"phase": int(phase), "cost": float(cost)}
            for phase, cost in zip(candidates, costs)
        ],
        "tie_break": "earliest_phase",
        "visible_fields": ["R", "Z", "Ip"],
        "reference_source": (
            "authenticated_r17_actual_closed_loop_visible_RZI"
        ),
        "source_action_used": False,
        "source_coil_current_used": False,
        "source_wire_current_used": False,
        "current_run_future_used": False,
        "hidden_wire_used": False,
    }


def _fresh_task_terminal_measurement(
    trajectory: Sequence[Mapping[str, Any]],
    target: np.ndarray,
    dt_s: float,
) -> np.ndarray:
    """Build a causal terminal measurement at a fresh task boundary.

    The frozen fresh-controller contract exposes only the current visible
    state at task step zero.  Its established main-control measurement path
    initializes the unavailable first finite difference to zero.  Apply that
    same convention when phase alignment enters damping immediately; after a
    second current-run sample exists, delegate exactly to the frozen terminal
    measurement implementation.
    """

    if not trajectory:
        raise ValueError(
            "fresh terminal feedback requires a current visible state"
        )
    if len(trajectory) >= 2:
        return r2.r9._terminal_measurement(trajectory, target, dt_s)
    current = trajectory[-1]
    target_array = np.asarray(target, dtype=float).reshape(3)
    return np.asarray(
        [
            float(current["R"]) - target_array[0],
            float(current["Z"]) - target_array[1],
            0.0,
            0.0,
            float(current["Ip"]) - target_array[2],
        ],
        dtype=float,
    )


def classify_pair_assessment(
    plus_pass: bool, minus_pass: bool
) -> str:
    if plus_pass and minus_pass:
        return "both_pass_development_pair_success"
    if bool(plus_pass) != bool(minus_pass):
        return "history_sensitive_pass_fail_outcome"
    return "masked_by_common_mode_both_fail"


def validate_config(cfg: Mapping[str, Any]) -> None:
    if str(cfg.get("stage")) != STAGE:
        raise ValueError("Stage4.2R3c3 config stage mismatch")
    if str(cfg.get("controller_revision")) != CONTROLLER_REVISION:
        raise ValueError("Stage4.2R3c3 controller revision mismatch")
    if str(cfg.get("package_revision")) != PACKAGE_REVISION:
        raise ValueError("Stage4.2R3c3 package revision mismatch")
    if int(cfg["parallel"]["n_workers"]) != 128:
        raise ValueError("Stage4.2R3c3 is fixed to 128 Ray workers")
    phase = cfg["phase_alignment"]
    expected_phase = {
        "candidate_min_phase": 0,
        "candidate_max_phase": 20,
        "R_scale_m": 0.03,
        "Z_scale_m": 0.03,
        "Ip_scale_A": 2000.0,
        "tie_break": "earliest_phase",
        "task_clock_starts_at_zero": True,
        "reference_clock_separate_from_task_clock": True,
        "align_nominal_reference": True,
        "align_response_model_phase": True,
        "align_delay_queue_priming": True,
        "align_braking_transition": True,
        "align_terminal_transition": True,
        "hidden_wire_input_allowed": False,
        "reference_manifold": (
            "authenticated_r17_actual_closed_loop_visible_RZI"
        ),
        "reference_fields": ["R", "Z", "Ip"],
        "reference_phase_count": 21,
        "source_actions_allowed": False,
        "source_coil_currents_allowed": False,
        "source_wire_currents_allowed": False,
    }
    if dict(phase) != expected_phase:
        raise ValueError("Stage4.2R3c3 phase-alignment contract changed")
    probe = cfg["identification_probe"]
    if (
        str(probe["baseline_controller"]) != r3c1.CONTROLLER_REVISION
        or str(probe["baseline_package"]) != r3c1.PACKAGE_REVISION
        or list(map(float, probe["physical_mode_amplitude"]))
        != [0.0075, 0.0075, 0.0]
        or list(map(int, probe["probe_signs"])) != [-1, 1]
        or not bool(probe["require_requested_and_applied_zero_net"])
        or not math.isclose(
            float(probe["zero_net_atol"]), 1e-12, abs_tol=0.0
        )
        or not math.isclose(
            float(probe["maximum_current_utilization"]),
            0.55,
            abs_tol=1e-15,
        )
        or bool(probe["formal_tracking_pass_required"])
        or bool(probe["probe_trajectories_allowed_in_expert_dataset"])
        or bool(probe["pair_or_history_label_input_allowed"])
        or bool(probe["source_result_input_allowed"])
        or bool(probe["source_action_input_allowed"])
        or bool(probe["source_or_current_wire_input_allowed"])
    ):
        raise ValueError("Stage4.2R3c3 identification-probe contract changed")
    expected_basis = [
        ("early_mode0", 0, 5),
        ("early_mode1", 1, 5),
        ("deadline_mode0", 0, 17),
        ("deadline_mode1", 1, 17),
    ]
    actual_basis = []
    for row in probe["basis"]:
        if (
            list(map(int, row["effect_offsets"])) != [0, 1, 3, 4]
            or list(map(int, row["sign_pattern"])) != [1, 1, -1, -1]
        ):
            raise ValueError("Stage4.2R3c3 probe pulse shape changed")
        actual_basis.append(
            (
                str(row["probe_id"]),
                int(row["mode"]),
                int(row["first_effect_state"]),
            )
        )
    if actual_basis != expected_basis:
        raise ValueError("Stage4.2R3c3 probe basis changed")
    symmetry = probe["central_symmetry"]
    hidden = probe["matched_hidden_history"]
    if (
        float(symmetry["maximum_even_velocity_rmse_m_per_s"]) != 0.004
        or float(symmetry["maximum_even_position_rmse_m"]) != 0.0005
        or float(symmetry["maximum_even_ip_rmse_A"]) != 20.0
        or float(hidden["maximum_odd_velocity_rmse_m_per_s"]) != 0.006
        or float(hidden["maximum_odd_position_rmse_m"]) != 0.001
        or float(hidden["maximum_odd_ip_rmse_A"]) != 40.0
        or float(probe["maximum_selected_velocity_condition_number"])
        != 25.0
    ):
        raise ValueError("Stage4.2R3c3 identification gates changed")
    matrix = cfg["control_matrix"]
    if list(map(str, matrix["targets"])) != [
        "nominal",
        "RZ_p10_m10",
    ]:
        raise ValueError("Stage4.2R3c3 target matrix changed")
    actuator = [
        (
            int(row["actual_delay_steps"]),
            float(row["actual_slew_scale"]),
        )
        for row in matrix["future_actuator_cases"]
    ]
    if actuator != [(0, 1.0), (2, 0.9)]:
        raise ValueError("Stage4.2R3c3 actuator matrix changed")
    if (
        list(map(str, matrix["history_members"]))
        != ["plus_first", "minus_first"]
        or int(matrix["probe_basis_count"]) != 4
        or int(matrix["probe_sign_count"]) != 2
        or int(matrix["expected_rollouts_per_baseline_context"]) != 8
        or int(matrix["expected_baseline_contexts_per_selected_pair"]) != 8
        or int(matrix["expected_rollouts_per_selected_pair"]) != 64
        or int(matrix["expected_selected_pairs"]) != 4
        or int(matrix["expected_baseline_contexts"]) != 32
        or int(matrix["expected_rollouts"]) != 256
        or not bool(matrix["require_fresh_controller"])
        or not bool(matrix["require_fresh_tsc_process"])
        or not bool(matrix["forbid_future_actions"])
        or not bool(matrix["forbid_future_measurements"])
        or not bool(matrix["require_online_action_computation"])
    ):
        raise ValueError("Stage4.2R3c3 control coverage changed")
    timing = cfg["formal_timing_contract"]
    if (
        int(timing["normal"]["arrival_deadline_step"]) != 25
        or int(timing["normal"]["arrival_deadline_ms"]) != 250
        or int(timing["normal"]["hold_through_step"]) != 35
        or int(timing["normal"]["hold_through_ms"]) != 350
        or int(timing["weak"]["arrival_deadline_step"]) != 27
        or int(timing["weak"]["arrival_deadline_ms"]) != 270
        or int(timing["weak"]["hold_through_step"]) != 37
        or int(timing["weak"]["hold_through_ms"]) != 370
        or not math.isclose(
            float(timing["position_tolerance_m"]), 0.03, abs_tol=1e-15
        )
        or not math.isclose(
            float(timing["speed_tolerance_m_per_s"]), 0.1, abs_tol=1e-15
        )
        or not bool(timing["arrival_streak_steps_unchanged"])
        or not bool(timing["ip_threshold_unchanged"])
        or bool(timing["arrival_deadline_expansion_allowed"])
    ):
        raise ValueError("Stage4.2R3c3 formal timing changed")
    requirements = cfg["source_requirements"]
    if (
        str(requirements["required_stage4_2r3b_run_name"])
        != (
            "stage4_2r3b_confirmatory_hidden_history_initial_state_"
            "20260730_115526"
        )
        or str(requirements["required_stage4_2r3b_stage"])
        != r3b.STAGE
        or str(requirements["required_stage4_2r3b_controller_revision"])
        != r3b.CONTROLLER_REVISION
        or str(requirements["required_stage4_2r3b_package_revision"])
        != r3b.PACKAGE_REVISION
        or int(requirements["required_state_raw_count"]) != 72
        or int(requirements["required_control_raw_count"]) != 32
        or int(requirements["required_snapshot_valid_count"]) != 72
        or int(requirements["required_selected_pair_count"]) != 4
        or int(requirements["require_source_control_formal_pass_count"])
        != 0
        or not bool(requirements["require_source_finished"])
        or not bool(requirements["require_source_state_gate_pass"])
        or not bool(requirements["require_source_primary_fail"])
    ):
        raise ValueError("Stage4.2R3c3 R3b source contract changed")
    if (
        str(requirements["required_stage4_2r3c_run_name"])
        != (
            "stage4_2r3c_visible_state_phase_aligned_mpc_"
            "20260730_132807"
        )
        or str(requirements["required_stage4_2r3c_stage"])
        != "Stage4.2R3c"
        or str(requirements["required_stage4_2r3c_controller_revision"])
        != "visible_state_phase_aligned_mpc_v42r3c"
        or str(requirements["required_stage4_2r3c_package_revision"])
        != "r42r3c_visible_state_phase_aligned_mpc_v1"
        or str(requirements["required_stage4_2r3c_run_inventory_digest"])
        != "278395b364bb355c73b5f6de7461478b4bb239584a3f6bf9bf048aad12be9d13"
        or int(
            requirements["required_stage4_2r3c_run_inventory_file_count"]
        )
        != 143
        or int(
            requirements["required_stage4_2r3c_run_inventory_total_bytes"]
        )
        != 2_963_470
        or str(
            requirements["required_stage4_2r3c_run_inventory_file_sha256"]
        )
        != "309158ec585abebaab2bce2e60264419d54ce71bee3fc9343c59468bb8b6fe97"
        or str(requirements["required_stage4_2r3c_server_audit_sha256"])
        != "d5276a0f30edbc503e8e09b8850023bcdf00a20cc70504fec54a44eacb0485d2"
        or str(requirements["required_stage4_2r3c_raw_forensics_sha256"])
        != "395427285a5bad0de9611629df0a13ade037ddd4f0e30e993e475a56c3dbafaa"
        or int(requirements["required_stage4_2r3c_control_raw_count"])
        != 32
        or int(requirements["required_stage4_2r3c_formal_pass_count"])
        != 20
        or int(requirements["required_stage4_2r3c_formal_failure_count"])
        != 12
    ):
        raise ValueError("Stage4.2R3c3 R3c evidence contract changed")
    if (
        str(requirements["required_stage4_2r3c1_run_name"])
        != (
            "stage4_2r3c1_authenticated_visible_manifold_phase_mpc_"
            "20260730_143218"
        )
        or str(requirements["required_stage4_2r3c1_stage"])
        != r3c1.STAGE
        or str(
            requirements["required_stage4_2r3c1_controller_revision"]
        )
        != r3c1.CONTROLLER_REVISION
        or str(requirements["required_stage4_2r3c1_package_revision"])
        != r3c1.PACKAGE_REVISION
        or str(
            requirements["required_stage4_2r3c1_run_inventory_digest"]
        )
        != "5bb79906dff14e4128e57f80dcd36576c881b46202e68a63f8dd977777812d2f"
        or int(
            requirements["required_stage4_2r3c1_run_inventory_file_count"]
        )
        != 166
        or int(
            requirements["required_stage4_2r3c1_run_inventory_total_bytes"]
        )
        != 3_409_736
        or str(
            requirements[
                "required_stage4_2r3c1_run_inventory_file_sha256"
            ]
        )
        != "8a2451dd5368f8d0e2dbf6e0b22616751b5136f80ec0dee5ee22e8959062af5e"
        or str(
            requirements["required_stage4_2r3c1_server_audit_sha256"]
        )
        != "0d81cbe3e0d9b67d72cf093143edd8a825a3b60ea5e3c449cf29de7cf0cc7712"
        or str(
            requirements["required_stage4_2r3c1_raw_forensics_sha256"]
        )
        != "29e37da1d570179228a39700ac4f4c2c66067cf2a7295c2b744f2bfb40d50edd"
        or str(
            requirements[
                "required_stage4_2r3c1_restart_regulation_diagnostic_sha256"
            ]
        )
        != "9a278b5e97416ae2d98d05b4cff7ad2328ddd0a1ec8f3d14ded0421b184c124d"
        or int(
            requirements["required_stage4_2r3c1_control_raw_count"]
        )
        != 32
        or int(
            requirements["required_stage4_2r3c1_formal_pass_count"]
        )
        != 16
        or int(
            requirements["required_stage4_2r3c1_formal_failure_count"]
        )
        != 16
    ):
        raise ValueError("Stage4.2R3c3 R3c1 evidence contract changed")
    if (
        str(requirements["required_stage4_2r3c2_run_name"])
        != (
            "stage4_2r3c2_restart_target_state_regulation_mpc_"
            "20260730_164616"
        )
        or str(requirements["required_stage4_2r3c2_stage"])
        != r3c2.STAGE
        or str(
            requirements["required_stage4_2r3c2_controller_revision"]
        )
        != r3c2.CONTROLLER_REVISION
        or str(requirements["required_stage4_2r3c2_package_revision"])
        != r3c2.PACKAGE_REVISION
        or str(
            requirements["required_stage4_2r3c2_run_inventory_digest"]
        )
        != "2119d2edad615dbb9594ad4332b758a9cf7ffc2e62b988650c41297aace8cff2"
        or int(
            requirements["required_stage4_2r3c2_run_inventory_file_count"]
        )
        != 147
        or int(
            requirements["required_stage4_2r3c2_run_inventory_total_bytes"]
        )
        != 3_287_591
        or str(
            requirements[
                "required_stage4_2r3c2_run_inventory_file_sha256"
            ]
        )
        != "8f9baa408e28a02874a95d4a6549ca6bcdef7bd3d8d3adb94707ed1eede90913"
        or str(
            requirements["required_stage4_2r3c2_server_audit_sha256"]
        )
        != "87461800e5fd9ea6f228d49e36269eb80ffbb537720fcf804c69812ed2ddf7cf"
        or str(
            requirements["required_stage4_2r3c2_raw_forensics_sha256"]
        )
        != "644da85280e03015732bb63deb1205bf5fcafeabc53b0f8a9e606565a27efbb2"
        or int(
            requirements["required_stage4_2r3c2_control_raw_count"]
        )
        != 32
        or int(
            requirements["required_stage4_2r3c2_formal_pass_count"]
        )
        != 12
        or int(
            requirements["required_stage4_2r3c2_formal_failure_count"]
        )
        != 20
    ):
        raise ValueError("Stage4.2R3c3 R3c2 evidence contract changed")
    expected_ids = [
        "p5_q1_a0p900_gap2_settle4",
        "p5_q2_a0p900_gap2_settle4",
        "p9_q1_a0p750_gap2_settle4",
        "p9_q2_a0p750_gap2_settle4",
    ]
    if list(map(str, requirements["required_selected_pair_ids"])) != expected_ids:
        raise ValueError("Stage4.2R3c3 selected pair identities changed")
    if (
        not bool(cfg.get("development_set_only"))
        or bool(cfg.get("independent_hidden_history_confirmation"))
        or bool(cfg.get("bc_dagger_or_rl_allowed"))
    ):
        raise ValueError("Stage4.2R3c3 scientific scope changed")


@dataclass(frozen=True)
class Stage42R3C3Paths:
    run_dir: Path
    source_reference: Path
    variants: Path
    control: Path
    analysis: Path
    state: Path
    manifest: Path

    @classmethod
    def from_run_dir(cls, run_dir: Path) -> "Stage42R3C3Paths":
        root = run_dir.expanduser().resolve()
        return cls(
            run_dir=root,
            source_reference=root / "stage4_2r3c3_source_reference",
            variants=root / "stage4_2r3c3_environment_variants",
            control=(
                root
                / "stage4_2r3c3_restart_task_clock_probe_identification"
            ),
            analysis=root / "stage4_2r3c3_analysis",
            state=root / "stage4_2r3c3_state.json",
            manifest=root / "stage4_2r3c3_manifest.json",
        )


@dataclass
class Stage42R3C3Context:
    cfg: dict[str, Any]
    paths: Stage42R3C3Paths
    project_dir: Path
    source_r3b_run: Path
    source_r3b_audit: Path
    source_ctx: r3b.Stage42R3BContext
    source_manifest: dict[str, Any]
    source_state: dict[str, Any]
    source_audit: dict[str, Any]
    source_fingerprint: dict[str, Any]
    source_r3c_run: Path
    source_r3c_audit: Path
    source_r3c_fingerprint: dict[str, Any]
    source_r3c1_run: Path
    source_r3c1_audit: Path
    source_r3c1_fingerprint: dict[str, Any]
    source_r3c1_restart_regulation_diagnostic: dict[str, Any]
    source_r3c2_run: Path
    source_r3c2_audit: Path
    source_r3c2_fingerprint: dict[str, Any]


def _source_audit_dir(source_run: Path) -> Path:
    project = source_run.parent.parent
    return (
        project
        / "stage4_2r3b_audits"
        / source_run.name
    )


def _source_fingerprint(
    source_run: Path,
    source_audit: Path,
    cfg: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    requirements = cfg["source_requirements"]
    files = {
        "manifest": source_run / "stage4_2r3b_manifest.json",
        "state": source_run / "stage4_2r3b_state.json",
        "resolved_config": source_run / "stage4_2r3b_config.resolved.json",
        "state_summary": (
            source_run / "stage4_2r3b_state_generation" / "summary.json"
        ),
        "selected_pairs": (
            source_run / "stage4_2r3b_pair_analysis" / "selected_pairs.json"
        ),
        "pair_summary": (
            source_run / "stage4_2r3b_pair_analysis" / "summary.json"
        ),
        "control_summary": (
            source_run / "stage4_2r3b_hidden_history_control" / "summary.json"
        ),
        "verdict": (
            source_run / "stage4_2r3b_analysis" / "stage4_2r3b_verdict.json"
        ),
        "run_inventory": source_audit / "stage4_2r3b_run_inventory.json",
        "server_audit": source_audit / "stage4_2r3b_server_audit.json",
        "raw_forensics": (
            source_audit / "stage4_2r3b_raw_control_forensics.json"
        ),
        "snapshot_checks": (
            source_audit / "stage4_2r3b_snapshot_checks.json"
        ),
    }
    for name, path in files.items():
        if not path.is_file():
            raise FileNotFoundError(
                f"Stage4.2R3c3 source evidence missing: {name}: {path}"
            )
    manifest = read_json(files["manifest"])
    state = read_json(files["state"])
    audit = read_json(files["server_audit"])
    inventory = read_json(files["run_inventory"])
    forensics = read_json(files["raw_forensics"])
    state_summary = read_json(files["state_summary"])
    control_summary = read_json(files["control_summary"])
    verdict = read_json(files["verdict"])
    if (
        source_run.name
        != str(requirements["required_stage4_2r3b_run_name"])
        or str(manifest.get("stage"))
        != str(requirements["required_stage4_2r3b_stage"])
        or str(manifest.get("controller_revision"))
        != str(requirements["required_stage4_2r3b_controller_revision"])
        or str(manifest.get("package_revision"))
        != str(requirements["required_stage4_2r3b_package_revision"])
        or not bool(state.get("finished"))
        or bool(state.get("primary_pass"))
        or not bool(state_summary.get("passed"))
        or int(control_summary.get("n_rollouts", -1))
        != int(requirements["required_control_raw_count"])
        or int(
            round(
                float(control_summary.get("formal_contract_pass_fraction", -1))
                * int(control_summary.get("n_rollouts", 0))
            )
        )
        != int(requirements["require_source_control_formal_pass_count"])
        or bool(verdict.get("primary_pass"))
    ):
        raise ValueError("Stage4.2R3c3 source R3b scientific state mismatch")
    if (
        str(inventory.get("digest"))
        != str(requirements["required_stage4_2r3b_run_inventory_digest"])
        or int(inventory.get("n_files", -1))
        != int(requirements["required_stage4_2r3b_run_inventory_file_count"])
        or int(inventory.get("total_bytes", -1))
        != int(requirements["required_stage4_2r3b_run_inventory_total_bytes"])
        or _sha256_file(files["run_inventory"])
        != str(
            requirements["required_stage4_2r3b_run_inventory_file_sha256"]
        )
        or _sha256_file(files["server_audit"])
        != str(requirements["required_stage4_2r3b_server_audit_sha256"])
        or _sha256_file(files["raw_forensics"])
        != str(requirements["required_stage4_2r3b_raw_forensics_sha256"])
        or str(audit["run_inventory"]["digest"])
        != str(inventory["digest"])
        or int(audit.get("state_raw_actual", -1))
        != int(requirements["required_state_raw_count"])
        or int(audit.get("control_raw_actual", -1))
        != int(requirements["required_control_raw_count"])
        or int(audit.get("snapshot_valid_count", -1))
        != int(requirements["required_snapshot_valid_count"])
        or int(forensics.get("state_raw_file_count", -1))
        != int(requirements["required_state_raw_count"])
        or int(forensics.get("control_raw_file_count", -1))
        != int(requirements["required_control_raw_count"])
    ):
        raise ValueError("Stage4.2R3c3 source R3b audit/inventory mismatch")
    rows = [
        {
            "name": name,
            "path": str(path.resolve()),
            "size_bytes": int(path.stat().st_size),
            "sha256": _sha256_file(path),
        }
        for name, path in sorted(files.items())
    ]
    fingerprint = {
        "schema_version": 1,
        "contract": "r42r3c3_exact_r3b_development_source_v1",
        "source_run": str(source_run),
        "source_audit": str(source_audit),
        "run_inventory_digest": str(inventory["digest"]),
        "run_inventory_file_count": int(inventory["n_files"]),
        "run_inventory_total_bytes": int(inventory["total_bytes"]),
        "n_files": len(rows),
        "digest": _canonical_digest(rows),
        "files": rows,
    }
    return manifest, state, {"audit": audit, "fingerprint": fingerprint}


def _r3c_evidence_fingerprint(
    project_dir: Path,
    cfg: Mapping[str, Any],
) -> tuple[Path, Path, dict[str, Any]]:
    """Authenticate the exact failed R3c development evidence."""

    requirements = cfg["source_requirements"]
    run_name = str(requirements["required_stage4_2r3c_run_name"])
    source_run = (project_dir / "stage4_2r3c_runs" / run_name).resolve()
    source_audit = (
        project_dir / "stage4_2r3c_audits" / run_name
    ).resolve()
    files = {
        "manifest": source_run / "stage4_2r3c_manifest.json",
        "state": source_run / "stage4_2r3c_state.json",
        "resolved_config": (
            source_run / "stage4_2r3c_config.resolved.json"
        ),
        "control_results": (
            source_run
            / "stage4_2r3c_phase_aligned_control"
            / "results.json"
        ),
        "control_summary": (
            source_run
            / "stage4_2r3c_phase_aligned_control"
            / "summary.json"
        ),
        "verdict": (
            source_run
            / "stage4_2r3c_analysis"
            / "stage4_2r3c_verdict.json"
        ),
        "run_inventory": (
            source_audit / "stage4_2r3c_run_inventory.json"
        ),
        "server_audit": (
            source_audit / "stage4_2r3c_server_audit.json"
        ),
        "raw_forensics": (
            source_audit / "stage4_2r3c_raw_control_forensics.json"
        ),
    }
    for name, path in files.items():
        if not path.is_file():
            raise FileNotFoundError(
                f"Stage4.2R3c3 R3c evidence missing: {name}: {path}"
            )
    manifest = read_json(files["manifest"])
    state = read_json(files["state"])
    control_results = read_json(files["control_results"])
    control_summary = read_json(files["control_summary"])
    verdict = read_json(files["verdict"])
    inventory = read_json(files["run_inventory"])
    audit = read_json(files["server_audit"])
    forensics = read_json(files["raw_forensics"])
    integrity = forensics["integrity_and_execution"]
    formal = forensics["formal_outcome"]
    if (
        source_run.name != run_name
        or str(manifest.get("stage"))
        != str(requirements["required_stage4_2r3c_stage"])
        or str(manifest.get("controller_revision"))
        != str(
            requirements["required_stage4_2r3c_controller_revision"]
        )
        or str(manifest.get("package_revision"))
        != str(requirements["required_stage4_2r3c_package_revision"])
        or not bool(state.get("finished"))
        or bool(state.get("primary_pass"))
        or bool(verdict.get("primary_pass"))
        or len(control_results)
        != int(requirements["required_stage4_2r3c_control_raw_count"])
        or int(control_summary.get("n_rollouts", -1))
        != int(requirements["required_stage4_2r3c_control_raw_count"])
        or int(
            round(
                float(
                    control_summary.get(
                        "formal_contract_pass_fraction", -1.0
                    )
                )
                * int(control_summary.get("n_rollouts", 0))
            )
        )
        != int(requirements["required_stage4_2r3c_formal_pass_count"])
    ):
        raise ValueError("Stage4.2R3c3 R3c scientific state mismatch")
    if (
        str(inventory.get("digest"))
        != str(requirements["required_stage4_2r3c_run_inventory_digest"])
        or int(inventory.get("n_files", -1))
        != int(
            requirements["required_stage4_2r3c_run_inventory_file_count"]
        )
        or int(inventory.get("total_bytes", -1))
        != int(
            requirements["required_stage4_2r3c_run_inventory_total_bytes"]
        )
        or _sha256_file(files["run_inventory"])
        != str(
            requirements["required_stage4_2r3c_run_inventory_file_sha256"]
        )
        or _sha256_file(files["server_audit"])
        != str(requirements["required_stage4_2r3c_server_audit_sha256"])
        or _sha256_file(files["raw_forensics"])
        != str(requirements["required_stage4_2r3c_raw_forensics_sha256"])
        or str(audit["run_inventory"]["digest"])
        != str(inventory["digest"])
        or not bool(audit.get("raw_and_manifest_integrity_passed"))
        or int(audit.get("control_raw_actual", -1))
        != int(requirements["required_stage4_2r3c_control_raw_count"])
        or int(integrity.get("control_raw_count", -1))
        != int(requirements["required_stage4_2r3c_control_raw_count"])
        or int(integrity.get("runtime_or_environment_error_count", -1))
        != 0
        or int(integrity.get("plant_restart_fidelity_failure_count", -1))
        != 0
        or int(integrity.get("controller_causality_failure_count", -1))
        != 0
        or int(formal.get("pass_count", -1))
        != int(requirements["required_stage4_2r3c_formal_pass_count"])
        or int(formal.get("failure_count", -1))
        != int(requirements["required_stage4_2r3c_formal_failure_count"])
    ):
        raise ValueError("Stage4.2R3c3 R3c audit/inventory mismatch")
    rows = [
        {
            "name": name,
            "path": str(path.resolve()),
            "size_bytes": int(path.stat().st_size),
            "sha256": _sha256_file(path),
        }
        for name, path in sorted(files.items())
    ]
    fingerprint = {
        "schema_version": 1,
        "contract": "r42r3c3_exact_failed_r3c_evidence_v1",
        "source_run": str(source_run),
        "source_audit": str(source_audit),
        "run_inventory_digest": str(inventory["digest"]),
        "run_inventory_file_count": int(inventory["n_files"]),
        "run_inventory_total_bytes": int(inventory["total_bytes"]),
        "formal_pass_count": int(formal["pass_count"]),
        "formal_failure_count": int(formal["failure_count"]),
        "n_files": len(rows),
        "digest": _canonical_digest(rows),
        "files": rows,
    }
    return source_run, source_audit, fingerprint


def _r3c1_evidence_fingerprint(
    project_dir: Path,
    cfg: Mapping[str, Any],
) -> tuple[Path, Path, dict[str, Any], dict[str, Any]]:
    """Authenticate the exact failed R3c1 result and no-TSC diagnosis."""

    requirements = cfg["source_requirements"]
    run_name = str(requirements["required_stage4_2r3c1_run_name"])
    source_run = (project_dir / "stage4_2r3c1_runs" / run_name).resolve()
    source_audit = (
        project_dir / "stage4_2r3c1_audits" / run_name
    ).resolve()
    files = {
        "manifest": source_run / "stage4_2r3c1_manifest.json",
        "state": source_run / "stage4_2r3c1_state.json",
        "resolved_config": (
            source_run / "stage4_2r3c1_config.resolved.json"
        ),
        "control_results": (
            source_run
            / "stage4_2r3c1_authenticated_visible_manifold_control"
            / "results.json"
        ),
        "control_summary": (
            source_run
            / "stage4_2r3c1_authenticated_visible_manifold_control"
            / "summary.json"
        ),
        "verdict": (
            source_run
            / "stage4_2r3c1_analysis"
            / "stage4_2r3c1_verdict.json"
        ),
        "run_inventory": (
            source_audit / "stage4_2r3c1_run_inventory.json"
        ),
        "server_audit": (
            source_audit / "stage4_2r3c1_server_audit.json"
        ),
        "raw_forensics": (
            source_audit / "stage4_2r3c1_raw_control_forensics.json"
        ),
        "restart_regulation_diagnostic": (
            source_audit
            / "stage4_2r3c1_restart_regulation_diagnostic.json"
        ),
    }
    for name, path in files.items():
        if not path.is_file():
            raise FileNotFoundError(
                f"Stage4.2R3c3 R3c1 evidence missing: {name}: {path}"
            )
    manifest = read_json(files["manifest"])
    state = read_json(files["state"])
    control_results = read_json(files["control_results"])
    control_summary = read_json(files["control_summary"])
    verdict = read_json(files["verdict"])
    inventory = read_json(files["run_inventory"])
    audit = read_json(files["server_audit"])
    forensics = read_json(files["raw_forensics"])
    diagnostic = read_json(files["restart_regulation_diagnostic"])
    integrity = forensics["integrity_and_execution"]
    formal = forensics["formal_outcome"]
    if (
        source_run.name != run_name
        or str(manifest.get("stage"))
        != str(requirements["required_stage4_2r3c1_stage"])
        or str(manifest.get("controller_revision"))
        != str(
            requirements["required_stage4_2r3c1_controller_revision"]
        )
        or str(manifest.get("package_revision"))
        != str(requirements["required_stage4_2r3c1_package_revision"])
        or not bool(state.get("finished"))
        or bool(state.get("primary_pass"))
        or bool(verdict.get("primary_pass"))
        or len(control_results)
        != int(requirements["required_stage4_2r3c1_control_raw_count"])
        or int(control_summary.get("n_rollouts", -1))
        != int(requirements["required_stage4_2r3c1_control_raw_count"])
        or int(
            round(
                float(
                    control_summary.get(
                        "formal_contract_pass_fraction", -1.0
                    )
                )
                * int(control_summary.get("n_rollouts", 0))
            )
        )
        != int(requirements["required_stage4_2r3c1_formal_pass_count"])
    ):
        raise ValueError("Stage4.2R3c3 R3c1 scientific state mismatch")
    if (
        str(inventory.get("digest"))
        != str(
            requirements["required_stage4_2r3c1_run_inventory_digest"]
        )
        or int(inventory.get("n_files", -1))
        != int(
            requirements["required_stage4_2r3c1_run_inventory_file_count"]
        )
        or int(inventory.get("total_bytes", -1))
        != int(
            requirements["required_stage4_2r3c1_run_inventory_total_bytes"]
        )
        or _sha256_file(files["run_inventory"])
        != str(
            requirements[
                "required_stage4_2r3c1_run_inventory_file_sha256"
            ]
        )
        or _sha256_file(files["server_audit"])
        != str(
            requirements["required_stage4_2r3c1_server_audit_sha256"]
        )
        or _sha256_file(files["raw_forensics"])
        != str(
            requirements["required_stage4_2r3c1_raw_forensics_sha256"]
        )
        or _sha256_file(files["restart_regulation_diagnostic"])
        != str(
            requirements[
                "required_stage4_2r3c1_restart_regulation_diagnostic_sha256"
            ]
        )
        or str(audit["run_inventory"]["digest"])
        != str(inventory["digest"])
        or not bool(audit.get("raw_and_manifest_integrity_passed"))
        or int(audit.get("control_raw_actual", -1))
        != int(requirements["required_stage4_2r3c1_control_raw_count"])
        or int(integrity.get("control_raw_count", -1))
        != int(requirements["required_stage4_2r3c1_control_raw_count"])
        or int(integrity.get("runtime_or_environment_error_count", -1))
        != 0
        or int(integrity.get("plant_restart_fidelity_failure_count", -1))
        != 0
        or int(integrity.get("controller_causality_failure_count", -1))
        != 0
        or int(formal.get("pass_count", -1))
        != int(requirements["required_stage4_2r3c1_formal_pass_count"])
        or int(formal.get("failure_count", -1))
        != int(requirements["required_stage4_2r3c1_formal_failure_count"])
        or not bool(diagnostic.get("diagnostic_passed"))
        or bool(diagnostic.get("real_tsc_executed"))
        or bool(diagnostic.get("plant_advanced"))
        or int(diagnostic.get("control_raw_count", -1)) != 32
    ):
        raise ValueError("Stage4.2R3c3 R3c1 audit/inventory mismatch")
    rows = [
        {
            "name": name,
            "path": str(path.resolve()),
            "size_bytes": int(path.stat().st_size),
            "sha256": _sha256_file(path),
        }
        for name, path in sorted(files.items())
    ]
    fingerprint = {
        "schema_version": 1,
        "contract": "r42r3c3_exact_failed_r3c1_evidence_v1",
        "source_run": str(source_run),
        "source_audit": str(source_audit),
        "run_inventory_digest": str(inventory["digest"]),
        "run_inventory_file_count": int(inventory["n_files"]),
        "run_inventory_total_bytes": int(inventory["total_bytes"]),
        "formal_pass_count": int(formal["pass_count"]),
        "formal_failure_count": int(formal["failure_count"]),
        "restart_regulation_diagnostic_sha256": _sha256_file(
            files["restart_regulation_diagnostic"]
        ),
        "n_files": len(rows),
        "digest": _canonical_digest(rows),
        "files": rows,
    }
    return source_run, source_audit, fingerprint, diagnostic


def _r3c2_evidence_fingerprint(
    project_dir: Path,
    cfg: Mapping[str, Any],
) -> tuple[Path, Path, dict[str, Any]]:
    """Authenticate the exact completed R3c2 failure."""

    requirements = cfg["source_requirements"]
    run_name = str(requirements["required_stage4_2r3c2_run_name"])
    source_run = (project_dir / "stage4_2r3c2_runs" / run_name).resolve()
    source_audit = (
        project_dir / "stage4_2r3c2_audits" / run_name
    ).resolve()
    files = {
        "manifest": source_run / "stage4_2r3c2_manifest.json",
        "state": source_run / "stage4_2r3c2_state.json",
        "resolved_config": (
            source_run / "stage4_2r3c2_config.resolved.json"
        ),
        "control_results": (
            source_run
            / "stage4_2r3c2_restart_target_state_regulation_control"
            / "results.json"
        ),
        "control_summary": (
            source_run
            / "stage4_2r3c2_restart_target_state_regulation_control"
            / "summary.json"
        ),
        "verdict": (
            source_run
            / "stage4_2r3c2_analysis"
            / "stage4_2r3c2_verdict.json"
        ),
        "run_inventory": (
            source_audit / "stage4_2r3c2_run_inventory.json"
        ),
        "server_audit": (
            source_audit / "stage4_2r3c2_server_audit.json"
        ),
        "raw_forensics": (
            source_audit / "stage4_2r3c2_raw_control_forensics.json"
        ),
    }
    for name, path in files.items():
        if not path.is_file():
            raise FileNotFoundError(
                f"Stage4.2R3c3 R3c2 evidence missing: {name}: {path}"
            )
    manifest = read_json(files["manifest"])
    state = read_json(files["state"])
    results = read_json(files["control_results"])
    summary = read_json(files["control_summary"])
    verdict = read_json(files["verdict"])
    inventory = read_json(files["run_inventory"])
    audit = read_json(files["server_audit"])
    forensics = read_json(files["raw_forensics"])
    integrity = forensics["integrity_and_execution"]
    formal = forensics["formal_outcome"]
    if (
        source_run.name != run_name
        or str(manifest.get("stage"))
        != str(requirements["required_stage4_2r3c2_stage"])
        or str(manifest.get("controller_revision"))
        != str(
            requirements["required_stage4_2r3c2_controller_revision"]
        )
        or str(manifest.get("package_revision"))
        != str(requirements["required_stage4_2r3c2_package_revision"])
        or not bool(state.get("finished"))
        or bool(state.get("primary_pass"))
        or bool(verdict.get("primary_pass"))
        or len(results)
        != int(requirements["required_stage4_2r3c2_control_raw_count"])
        or int(summary.get("n_rollouts", -1))
        != int(requirements["required_stage4_2r3c2_control_raw_count"])
        or int(
            round(
                float(summary["formal_contract_pass_fraction"])
                * int(summary["n_rollouts"])
            )
        )
        != int(requirements["required_stage4_2r3c2_formal_pass_count"])
    ):
        raise ValueError("Stage4.2R3c3 R3c2 scientific state mismatch")
    if (
        str(inventory.get("digest"))
        != str(requirements["required_stage4_2r3c2_run_inventory_digest"])
        or int(inventory.get("n_files", -1))
        != int(
            requirements["required_stage4_2r3c2_run_inventory_file_count"]
        )
        or int(inventory.get("total_bytes", -1))
        != int(
            requirements["required_stage4_2r3c2_run_inventory_total_bytes"]
        )
        or _sha256_file(files["run_inventory"])
        != str(
            requirements[
                "required_stage4_2r3c2_run_inventory_file_sha256"
            ]
        )
        or _sha256_file(files["server_audit"])
        != str(requirements["required_stage4_2r3c2_server_audit_sha256"])
        or _sha256_file(files["raw_forensics"])
        != str(requirements["required_stage4_2r3c2_raw_forensics_sha256"])
        or str(audit["run_inventory"]["digest"])
        != str(inventory["digest"])
        or not bool(audit.get("raw_and_manifest_integrity_passed"))
        or int(integrity.get("control_raw_count", -1))
        != int(requirements["required_stage4_2r3c2_control_raw_count"])
        or int(integrity.get("runtime_or_environment_error_count", -1))
        != 0
        or int(integrity.get("plant_restart_fidelity_failure_count", -1))
        != 0
        or int(integrity.get("controller_causality_failure_count", -1))
        != 0
        or int(formal.get("pass_count", -1))
        != int(requirements["required_stage4_2r3c2_formal_pass_count"])
        or int(formal.get("failure_count", -1))
        != int(requirements["required_stage4_2r3c2_formal_failure_count"])
    ):
        raise ValueError("Stage4.2R3c3 R3c2 audit/inventory mismatch")
    rows = [
        {
            "name": name,
            "path": str(path.resolve()),
            "size_bytes": int(path.stat().st_size),
            "sha256": _sha256_file(path),
        }
        for name, path in sorted(files.items())
    ]
    fingerprint = {
        "schema_version": 1,
        "contract": "r42r3c3_exact_failed_r3c2_evidence_v1",
        "source_run": str(source_run),
        "source_audit": str(source_audit),
        "run_inventory_digest": str(inventory["digest"]),
        "run_inventory_file_count": int(inventory["n_files"]),
        "run_inventory_total_bytes": int(inventory["total_bytes"]),
        "formal_pass_count": int(formal["pass_count"]),
        "formal_failure_count": int(formal["failure_count"]),
        "n_files": len(rows),
        "digest": _canonical_digest(rows),
        "files": rows,
    }
    return source_run, source_audit, fingerprint


def load_stage42r3c3_config(
    config_path: Path,
    *,
    source_stage42r3b_run: Path,
    run_dir_override: Path | None = None,
) -> Stage42R3C3Context:
    config_path = config_path.expanduser().resolve()
    cfg = read_json(config_path)
    validate_config(cfg)
    project_dir = config_path.parents[1]
    source_run = source_stage42r3b_run.expanduser().resolve()
    source_audit = _source_audit_dir(source_run)
    manifest, state, source_data = _source_fingerprint(
        source_run, source_audit, cfg
    )
    source_r3c_run, source_r3c_audit, source_r3c_fingerprint = (
        _r3c_evidence_fingerprint(project_dir, cfg)
    )
    (
        source_r3c1_run,
        source_r3c1_audit,
        source_r3c1_fingerprint,
        source_r3c1_restart_regulation_diagnostic,
    ) = _r3c1_evidence_fingerprint(project_dir, cfg)
    source_r3c2_run, source_r3c2_audit, source_r3c2_fingerprint = (
        _r3c2_evidence_fingerprint(project_dir, cfg)
    )
    source_r2 = Path(
        str(manifest["source_stage4_2r2_run"])
    ).expanduser().resolve()
    calibration_r3a = Path(
        str(manifest["calibration_stage4_2r3a_run"])
    ).expanduser().resolve()
    source_ctx = r3b.load_stage42r3b_config(
        project_dir
        / "configs"
        / "stage4_2r3b_confirmatory_hidden_history_initial_state_370ms.json",
        source_stage42r2_run=source_r2,
        calibration_stage42r3a_run=calibration_r3a,
        run_dir_override=source_run,
    )
    if run_dir_override is None:
        root = project_dir / str(cfg["output_root"])
        run_dir = root / f"{cfg['run_name']}_{utc_timestamp()}"
    else:
        run_dir = run_dir_override.expanduser().resolve()
    return Stage42R3C3Context(
        cfg=cfg,
        paths=Stage42R3C3Paths.from_run_dir(run_dir),
        project_dir=project_dir,
        source_r3b_run=source_run,
        source_r3b_audit=source_audit,
        source_ctx=source_ctx,
        source_manifest=manifest,
        source_state=state,
        source_audit=source_data["audit"],
        source_fingerprint=source_data["fingerprint"],
        source_r3c_run=source_r3c_run,
        source_r3c_audit=source_r3c_audit,
        source_r3c_fingerprint=source_r3c_fingerprint,
        source_r3c1_run=source_r3c1_run,
        source_r3c1_audit=source_r3c1_audit,
        source_r3c1_fingerprint=source_r3c1_fingerprint,
        source_r3c1_restart_regulation_diagnostic=(
            source_r3c1_restart_regulation_diagnostic
        ),
        source_r3c2_run=source_r3c2_run,
        source_r3c2_audit=source_r3c2_audit,
        source_r3c2_fingerprint=source_r3c2_fingerprint,
    )


def _recompute_selected_pairs(
    ctx: Stage42R3C3Context,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    raw_paths = sorted(
        (ctx.source_ctx.paths.state_generation / "raw").glob("*.json.gz")
    )
    if len(raw_paths) != int(
        ctx.cfg["source_requirements"]["required_state_raw_count"]
    ):
        raise ValueError("Stage4.2R3c3 source state raw count mismatch")
    state_rows = [
        r3b._state_row(read_json_gz(path)) for path in raw_paths
    ]
    state_by_id = {
        str(row["experiment_id"]): row for row in state_rows
    }
    by_pair: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in state_rows:
        by_pair[str(row["pair_id"])][str(row["history_order"])] = row
    pair_rows = []
    for pair_id in sorted(by_pair):
        members = by_pair[pair_id]
        if set(members) != {"plus_first", "minus_first"}:
            raise ValueError(f"incomplete R3b source pair: {pair_id}")
        pair_rows.append(
            r3b._pair_metrics(
                members["plus_first"],
                members["minus_first"],
                ctx.source_ctx.cfg["pair_gate"],
            )
        )
    accepted = [row for row in pair_rows if bool(row.get("accepted"))]
    selected = []
    for prefix in (5, 9):
        for direction in (1, 2):
            candidates = [
                row
                for row in accepted
                if int(row["common_prefix_steps"]) == prefix
                and int(row["nullspace_direction_index"]) == direction
            ]
            if not candidates:
                raise ValueError(
                    f"R3b source selection stratum missing: {prefix}/{direction}"
                )
            candidates.sort(
                key=lambda row: (
                    -float(row["wire_relative_rms_difference"]),
                    -float(row["wire_rms_difference_A"]),
                    -float(row["wire_max_abs_difference_A"]),
                    float(row["visible_max_normalized_ratio"]),
                    float(row["amplitude_fraction"]),
                    -int(row["gap_steps"]),
                    str(row["pair_id"]),
                )
            )
            selected.append(copy.deepcopy(candidates[0]))
    selected.sort(key=lambda row: str(row["pair_id"]))
    actual_ids = [str(row["pair_id"]) for row in selected]
    required_ids = list(
        map(
            str,
            ctx.cfg["source_requirements"]["required_selected_pair_ids"],
        )
    )
    if actual_ids != required_ids:
        raise ValueError(
            f"Stage4.2R3c3 raw-recomputed selected pair mismatch: {actual_ids}"
        )
    for pair in selected:
        for member in ("plus_first", "minus_first"):
            state = pair[f"{member}_state"]
            if not _selected_snapshot_state_is_valid(state):
                raise ValueError(
                    "Stage4.2R3c3 selected source snapshot is invalid"
                )
    return selected, state_by_id


def _selected_snapshot_state_is_valid(
    state: Mapping[str, Any],
) -> bool:
    """Honor R3b `_state_row`: `success` already includes snapshot checks."""

    return bool(
        state.get("success")
        and str(state.get("snapshot_manifest_digest", "")).strip()
        and Path(str(state.get("snapshot_dir", ""))).is_dir()
    )


def _deployed_package_fingerprint(
    ctx: Stage42R3C3Context,
) -> dict[str, Any]:
    relative_paths = [
        "PACKAGE_MANIFEST.json",
        "SHA256SUMS",
        "configs/stage4_2r3c3_restart_task_clock_local_response_identification_370ms.json",
        "run_stage4_2r3c3_restart_task_clock_local_response_identification_native.sh",
        "run_stage4_2r3c3_restart_task_clock_local_response_identification_nohup.sh",
        "run_stage4_2r3c3_self_test.sh",
        "run_stage4_2r3c3_server_postprocess.sh",
        "run_stage4_2r3c3_verify_package.sh",
        "run_stop_stage4_2r3c3_now.sh",
        "scripts/stage4_2r3c3_shell_common.sh",
        "scripts/stage4_2r3c3_restart_task_clock_local_response_identification.py",
        "scripts/stage4_2r3c3_server_postprocess.py",
        "tsc_rzip_rllib/diagnostics/stage4_2r3c3_restart_task_clock_local_response_identification.py",
    ]
    rows = []
    for relative in relative_paths:
        path = ctx.project_dir / relative
        if not path.is_file():
            raise FileNotFoundError(
                f"Stage4.2R3c3 package file missing: {relative}"
            )
        rows.append(
            {
                "path": relative,
                "size_bytes": int(path.stat().st_size),
                "sha256": _sha256_file(path),
            }
        )
    return {
        "schema_version": 1,
        "contract": "r42r3c3_deployed_package_source_v1",
        "n_files": len(rows),
        "digest": _canonical_digest(rows),
        "files": rows,
    }


def _semantics_preserving_resume_compatibility(
    ctx: Stage42R3C3Context,
    original: Mapping[str, Any],
    active: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Require the exact R3c3 package for every resume."""

    if dict(original) == dict(active):
        return None
    raise ValueError(
        "Stage4.2R3c3 deployed package fingerprint changed; "
        "in-place resume is forbidden"
    )


def _source_controller_cases(
    ctx: Stage42R3C3Context,
) -> dict[tuple[str, int, float], dict[str, Any]]:
    sources = r3b._source_controller_cases(ctx.source_ctx)
    required = {
        (
            str(target),
            int(actuator["actual_delay_steps"]),
            float(actuator["actual_slew_scale"]),
        )
        for target in ctx.cfg["control_matrix"]["targets"]
        for actuator in ctx.cfg["control_matrix"][
            "future_actuator_cases"
        ]
    }
    if set(sources) != required:
        raise ValueError("Stage4.2R3c3 frozen controller source mismatch")
    return sources


def _source_raw_files_by_experiment_id(
    ctx: Stage42R3C3Context,
) -> dict[str, Path]:
    paths = r1._selected_source_files(ctx.source_ctx.r1_ctx)
    output: dict[str, Path] = {}
    for path in paths:
        result = read_json_gz(path)
        experiment_id = str(result.get("experiment_id", ""))
        if not experiment_id or experiment_id in output:
            raise ValueError(
                "Stage4.2R3c3 invalid or duplicate R17 source raw identity"
            )
        output[experiment_id] = path.resolve()
    return output


def _visible_reference_manifold(
    source: Mapping[str, Any],
    source_raw_path: Path,
) -> dict[str, Any]:
    """Extract the only R17 trajectory calibration permitted: R/Z/Ip."""

    trajectory = list(source.get("trajectory") or [])
    if len(trajectory) < 21:
        raise ValueError("Stage4.2R3c3 R17 visible manifold is too short")
    values = np.asarray(
        [
            [
                float(trajectory[phase]["R"]),
                float(trajectory[phase]["Z"]),
                float(trajectory[phase]["Ip"]),
            ]
            for phase in range(21)
        ],
        dtype=float,
    )
    if values.shape != (21, 3) or not np.all(np.isfinite(values)):
        raise ValueError("Stage4.2R3c3 R17 visible manifold is invalid")
    experiment_id = str(source.get("experiment_id", ""))
    raw_result = read_json_gz(source_raw_path)
    if (
        not experiment_id
        or str(raw_result.get("experiment_id", "")) != experiment_id
        or list(raw_result.get("trajectory") or [])[:21]
        != trajectory[:21]
    ):
        raise ValueError(
            "Stage4.2R3c3 R17 visible manifold/raw authentication failed"
        )
    manifold = {
        "schema_version": 1,
        "contract": "authenticated_r17_actual_closed_loop_visible_RZI_v1",
        "source_experiment_id": experiment_id,
        "source_raw_sha256": _sha256_file(source_raw_path),
        "source_raw_size_bytes": int(source_raw_path.stat().st_size),
        "visible_fields": ["R", "Z", "Ip"],
        "phase_min": 0,
        "phase_max": 20,
        "phase_count": 21,
        "values": values.tolist(),
        "source_actions_included": False,
        "source_coil_currents_included": False,
        "source_wire_currents_included": False,
        "current_run_future_included": False,
    }
    manifold["values_digest"] = _canonical_digest(manifold["values"])
    allowed = {
        "schema_version",
        "contract",
        "source_experiment_id",
        "source_raw_sha256",
        "source_raw_size_bytes",
        "visible_fields",
        "phase_min",
        "phase_max",
        "phase_count",
        "values",
        "values_digest",
        "source_actions_included",
        "source_coil_currents_included",
        "source_wire_currents_included",
        "current_run_future_included",
    }
    if set(manifold) != allowed:
        raise ValueError("Stage4.2R3c3 visible manifold schema changed")
    return manifold


def _visible_reference_manifolds(
    ctx: Stage42R3C3Context,
    sources: Mapping[
        tuple[str, int, float], Mapping[str, Any]
    ],
) -> dict[tuple[str, int, float], dict[str, Any]]:
    raw_by_id = _source_raw_files_by_experiment_id(ctx)
    output = {}
    for key, source in sources.items():
        experiment_id = str(source.get("experiment_id", ""))
        path = raw_by_id.get(experiment_id)
        if path is None:
            raise FileNotFoundError(
                "Stage4.2R3c3 selected R17 raw source missing: "
                f"{experiment_id}"
            )
        output[key] = _visible_reference_manifold(source, path)
    if set(output) != set(sources):
        raise ValueError(
            "Stage4.2R3c3 visible manifold source coverage mismatch"
        )
    return output


def _probe_schedule(
    *,
    first_effect_state: int,
    actual_delay: int,
    basis: Mapping[str, Any],
    sign: int,
    amplitude_by_mode: Sequence[float],
) -> dict[int, np.ndarray]:
    mode = int(basis["mode"])
    amplitude = float(amplitude_by_mode[mode]) * int(sign)
    schedule: dict[int, np.ndarray] = {}
    for offset, pattern in zip(
        basis["effect_offsets"], basis["sign_pattern"]
    ):
        effect_state = int(first_effect_state) + int(offset)
        issue_step = effect_state - int(actual_delay) - 1
        if issue_step < 0:
            raise ValueError("Stage4.2R3c3 probe issue step is negative")
        delta = np.zeros(N_MODES, dtype=float)
        delta[mode] = amplitude * int(pattern)
        schedule[issue_step] = (
            schedule.get(issue_step, np.zeros(N_MODES, dtype=float))
            + delta
        )
    return schedule


def _r3c1_baseline_result_ids(
    ctx: Stage42R3C3Context,
) -> dict[tuple[str, str, str, int, float], str]:
    rows = read_json(
        ctx.source_r3c1_run
        / "stage4_2r3c1_authenticated_visible_manifold_control"
        / "results.json"
    )
    output = {}
    for row in rows:
        key = (
            str(row["pair_id"]),
            str(row["history_member"]),
            str(row["target_id"]),
            int(row["actual_delay_steps"]),
            float(row["actual_slew_scale"]),
        )
        if key in output:
            raise ValueError("duplicate R3c1 baseline context")
        output[key] = str(row["experiment_id"])
    if len(output) != 32:
        raise ValueError("R3c1 baseline context coverage mismatch")
    return output


def build_control_specs(
    ctx: Stage42R3C3Context,
    selected_pairs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    sources = _source_controller_cases(ctx)
    manifolds = _visible_reference_manifolds(ctx, sources)
    baseline_ids = _r3c1_baseline_result_ids(ctx)
    probe_cfg = ctx.cfg["identification_probe"]
    amplitudes = list(map(float, probe_cfg["physical_mode_amplitude"]))
    specs = []
    for pair in sorted(selected_pairs, key=lambda row: str(row["pair_id"])):
        for member in ctx.cfg["control_matrix"]["history_members"]:
            state = pair[f"{member}_state"]
            snapshot_dir = Path(
                str(state["snapshot_dir"])
            ).expanduser().resolve()
            snapshot_digest = str(state["snapshot_manifest_digest"])
            for target in ctx.cfg["control_matrix"]["targets"]:
                for actuator in ctx.cfg["control_matrix"][
                    "future_actuator_cases"
                ]:
                    delay = int(actuator["actual_delay_steps"])
                    slew = float(actuator["actual_slew_scale"])
                    source = sources[(str(target), delay, slew)]
                    manifold = manifolds[(str(target), delay, slew)]
                    baseline_key = (
                        str(pair["pair_id"]),
                        str(member),
                        str(target),
                        delay,
                        slew,
                    )
                    baseline_id = baseline_ids.get(baseline_key)
                    if baseline_id is None:
                        raise ValueError("R3c1 baseline context missing")
                    for basis in probe_cfg["basis"]:
                        for probe_sign in probe_cfg["probe_signs"]:
                            spec = copy.deepcopy(source["spec"])
                            if r3b._forbidden_future_paths(spec):
                                raise ValueError(
                                    "Stage4.2R3c3 source spec contains "
                                    "future data"
                                )
                            schedule = _probe_schedule(
                                first_effect_state=int(
                                    basis["first_effect_state"]
                                ),
                                actual_delay=delay,
                                basis=basis,
                                sign=int(probe_sign),
                                amplitude_by_mode=amplitudes,
                            )
                            requested_net = np.sum(
                                np.stack(list(schedule.values())), axis=0
                            )
                            if not np.array_equal(
                                requested_net,
                                np.zeros(N_MODES, dtype=float),
                            ):
                                raise ValueError(
                                    "Stage4.2R3c3 requested probe is "
                                    "not exactly zero net"
                                )
                            identity = {
                                "stage": STAGE,
                                "phase": (
                                    "restart_task_clock_local_response_"
                                    "identification"
                                ),
                                "pair_id": str(pair["pair_id"]),
                                "history_member": str(member),
                                "state_generation_experiment_id": str(
                                    state["experiment_id"]
                                ),
                                "snapshot_manifest_digest": snapshot_digest,
                                "target_id": str(target),
                                "actual_delay_steps": delay,
                                "actual_slew_scale": slew,
                                "probe_id": str(basis["probe_id"]),
                                "probe_sign": int(probe_sign),
                                "probe_schedule": {
                                    str(step): value.tolist()
                                    for step, value in sorted(
                                        schedule.items()
                                    )
                                },
                                "controller_revision": CONTROLLER_REVISION,
                                "phase_alignment": (
                                    ctx.cfg["phase_alignment"]
                                ),
                                "visible_reference_manifold_digest": (
                                    manifold["values_digest"]
                                ),
                            }
                            experiment_id = _scenario_digest(identity)
                            spec.update(
                                {
                                    "kind": (
                                        "stage4_2r3c3_restart_task_clock_"
                                        "local_response_identification"
                                    ),
                                    "stage": STAGE,
                                    "controller_revision": (
                                        CONTROLLER_REVISION
                                    ),
                                    "underlying_controller_revision": (
                                        r3c1.CONTROLLER_REVISION
                                    ),
                                    "experiment_id": experiment_id,
                                    "baseline_experiment_id": baseline_id,
                                    "phase": (
                                        "restart_task_clock_local_response_"
                                        "identification"
                                    ),
                                    "category": (
                                        "restart_task_clock_local_response_"
                                        "identification"
                                    ),
                                    "pair_id": str(pair["pair_id"]),
                                    "history_member": str(member),
                                    "state_generation_experiment_id": str(
                                        state["experiment_id"]
                                    ),
                                    "restart_snapshot_dir": str(
                                        snapshot_dir
                                    ),
                                    "restart_snapshot_manifest_digest": (
                                        snapshot_digest
                                    ),
                                    "environment_variant": (
                                        f"stage4_2r3c3_{experiment_id}"
                                    ),
                                    "horizon_steps": (
                                        _formal_horizon(slew)
                                    ),
                                    "phase_alignment": copy.deepcopy(
                                        ctx.cfg["phase_alignment"]
                                    ),
                                    "visible_reference_manifold": (
                                        copy.deepcopy(manifold)
                                    ),
                                    "visible_reference_manifold_digest": str(
                                        manifold["values_digest"]
                                    ),
                                    "visible_reference_manifold_source": (
                                        "authenticated_R17_actual_"
                                        "closed_loop_RZI"
                                    ),
                                    "r3c3_probe_id": str(
                                        basis["probe_id"]
                                    ),
                                    "r3c3_probe_mode": int(basis["mode"]),
                                    "r3c3_probe_sign": int(probe_sign),
                                    "r3c3_probe_first_effect_state": int(
                                        basis["first_effect_state"]
                                    ),
                                    "r3c3_probe_delta_by_task_issue_step": {
                                        str(step): value.tolist()
                                        for step, value in sorted(
                                            schedule.items()
                                        )
                                    },
                                    "r3c3_requested_probe_net": (
                                        requested_net.tolist()
                                    ),
                                    "r3c3_probe_amplitude": float(
                                        amplitudes[int(basis["mode"])]
                                    ),
                                    "source_action_available_to_controller": (
                                        False
                                    ),
                                    "source_coil_current_available_to_controller": (
                                        False
                                    ),
                                    "source_wire_current_available_to_controller": (
                                        False
                                    ),
                                    "fresh_controller_required": True,
                                    "fresh_tsc_process_required": True,
                                    "controller_history_initialization": (
                                        "current_visible_state_only_at_"
                                        "task_step_zero"
                                    ),
                                    "controller_integral_initialization": (
                                        "zero"
                                    ),
                                    "pair_or_history_label_available_to_controller": (
                                        False
                                    ),
                                    "source_result_available_to_controller": (
                                        False
                                    ),
                                    "hidden_wire_current_available_to_controller": (
                                        False
                                    ),
                                    "full_wire_current_recorded_after_action_choice": (
                                        True
                                    ),
                                    "future_action_count": 0,
                                    "future_measurement_count": 0,
                                    "online_action_computation_required": True,
                                    "task_clock_starts_at_zero": True,
                                    "formal_timing_unchanged": True,
                                    "identification_only": True,
                                    "probe_trajectory_allowed_in_expert_dataset": (
                                        False
                                    ),
                                    "development_set_only": True,
                                }
                            )
                            specs.append(spec)
    expected = int(ctx.cfg["control_matrix"]["expected_rollouts"])
    if (
        len(specs) != expected
        or len({str(spec["experiment_id"]) for spec in specs}) != expected
    ):
        raise ValueError("Stage4.2R3c3 control coverage mismatch")
    return specs


def _control_payload(
    ctx: Stage42R3C3Context,
    *,
    spec: Mapping[str, Any],
) -> dict[str, Any]:
    slew = float(spec["slew_scale"])
    horizon = _formal_horizon(slew)
    variant = f"slew_{slew:.3f}".replace(".", "p")
    payload = copy.deepcopy(
        read_json(
            ctx.source_ctx.source_r1_run
            / "stage4_2r1_restart_variants"
            / f"source_{variant}_h{horizon}.payload.json"
        )
    )
    env_cfg = copy.deepcopy(payload["env_cfg"])
    snapshot_dir = Path(str(spec["restart_snapshot_dir"]))
    storage = ctx.cfg["storage"]
    env_cfg["simulation_root"] = str(snapshot_dir.parent)
    env_cfg["start_folder"] = snapshot_dir.name
    env_cfg["tsc_timeout_s"] = float(ctx.cfg["runtime"]["tsc_timeout_s"])
    env_cfg["tsc_workspace_root"] = str(
        Path(
            os.environ.get(
                "STAGE4_2R3C3_TSC_WORKSPACE_ROOT",
                storage["tsc_workspace_root"],
            )
        )
        .expanduser()
        .resolve()
    )
    env_cfg["run_root"] = str(
        Path(
            os.environ.get(
                "STAGE4_2R3C3_TSC_RUN_ROOT", storage["tsc_run_root"]
            )
        )
        .expanduser()
        .resolve()
    )
    env_cfg["tsc_run_root"] = env_cfg["run_root"]
    env_cfg["runtime_only_fast_mode"] = True
    env_cfg["save_step_artifacts"] = False
    env_cfg["save_artifacts_every_n_steps"] = 0
    env_cfg["cleanup_episode_dir"] = True
    env_cfg["keep_failed_episode_dir"] = bool(
        storage.get("keep_failed_episode_dir", False)
    )
    env_cfg["keep_last_n_failed_episode_dirs"] = int(
        storage.get("keep_last_n_failed_episode_dirs", 0)
    )
    train_cfg = copy.deepcopy(payload["train_cfg"])
    experiment_id = str(spec["experiment_id"])
    env_path = ctx.paths.variants / f"env_{experiment_id}.json"
    train_path = ctx.paths.variants / f"train_{experiment_id}.json"
    atomic_write_json(env_path, env_cfg)
    train_cfg["env_config"] = str(env_path)
    train_cfg.setdefault("episode", {})["max_episode_steps"] = horizon
    atomic_write_json(train_path, train_cfg)
    payload["env_cfg"] = env_cfg
    payload["train_cfg"] = train_cfg
    payload["variant_id"] = f"stage4_2r3c3_{experiment_id}"
    payload["start_folder"] = snapshot_dir.name
    payload["slew_scale"] = slew
    payload["stage4_1r4_horizon_steps"] = horizon
    payload["stage4_2r3c3_restart_snapshot_dir"] = str(snapshot_dir)
    payload["stage4_2r3c3_snapshot_manifest_digest"] = str(
        spec["restart_snapshot_manifest_digest"]
    )
    atomic_write_json(
        ctx.paths.variants / f"payload_{experiment_id}.json", payload
    )
    return payload


_FORBIDDEN_CONTROLLER_SPEC_KEYS = frozenset(
    {
        "pair_id",
        "history_member",
        "state_generation_experiment_id",
        "baseline_experiment_id",
        "restart_snapshot_dir",
        "restart_snapshot_manifest_digest",
        "experiment_id",
        "environment_variant",
        "kind",
        "phase",
        "category",
    }
)


def _controller_spec(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Remove experiment/history identity before constructing the controller."""

    output = copy.deepcopy(dict(spec))
    for key in _FORBIDDEN_CONTROLLER_SPEC_KEYS:
        output.pop(key, None)
    if _FORBIDDEN_CONTROLLER_SPEC_KEYS.intersection(output):
        raise ValueError("forbidden experiment identity reached controller")
    return output


class RestartTaskClockLocalResponseProbeController(
    r3c1.AuthenticatedVisibleManifoldPhaseTaskController
):
    """Exact R3c1 baseline with a bounded task-relative probe."""

    def __init__(
        self,
        base_worker: Any,
        bundle: Mapping[str, Any],
        source_spec: Mapping[str, Any],
        initial_state: Mapping[str, Any],
    ):
        super().__init__(base_worker, bundle, source_spec, initial_state)
        self.probe_schedule = {
            int(step): np.asarray(value, dtype=float).reshape(N_MODES)
            for step, value in (
                source_spec.get(
                    "r3c3_probe_delta_by_task_issue_step"
                )
                or {}
            ).items()
        }
        self.probe_id = str(source_spec["r3c3_probe_id"])
        self.probe_mode = int(source_spec["r3c3_probe_mode"])
        self.probe_sign = int(source_spec["r3c3_probe_sign"])
        self.probe_first_effect_state = int(
            source_spec["r3c3_probe_first_effect_state"]
        )
        self.probe_amplitude = float(
            source_spec["r3c3_probe_amplitude"]
        )
        if (
            self.probe_mode not in {0, 1}
            or self.probe_sign not in {-1, 1}
            or not math.isclose(
                self.probe_amplitude, 0.0075, abs_tol=1e-15
            )
            or len(self.probe_schedule) != 4
        ):
            raise ValueError("Stage4.2R3c3 probe controller contract invalid")
        requested = np.sum(
            np.stack(list(self.probe_schedule.values())), axis=0
        )
        if not np.array_equal(
            requested, np.zeros(N_MODES, dtype=float)
        ):
            raise ValueError("Stage4.2R3c3 controller probe is not zero net")

    def action(
        self, current_state: Mapping[str, Any]
    ) -> tuple[np.ndarray, dict[str, Any]]:
        task_step = self.step
        requested = self.probe_schedule.get(
            task_step, np.zeros(N_MODES, dtype=float)
        )
        original = r2.r3.solve_delay_aware_physical_correction
        probe_info: dict[str, Any] = {}

        def wrapped(*args: Any, **kwargs: Any) -> dict[str, Any]:
            out = original(*args, **kwargs)
            if not np.any(requested != 0.0):
                return out
            baseline = np.asarray(
                out["first_correction"], dtype=float
            ).reshape(N_MODES)
            nominal = np.asarray(
                kwargs["nominal_physical_coefficients"], dtype=float
            ).reshape(35, N_MODES)
            effect_step = min(
                int(out.get("effect_step", kwargs["current_step"])), 34
            )
            feedforward = nominal[effect_step]
            lower = np.asarray(
                self.base.stub.cfg["trajectory"]["coefficient_lower"],
                dtype=float,
            ).reshape(N_MODES)
            upper = np.asarray(
                self.base.stub.cfg["trajectory"]["coefficient_upper"],
                dtype=float,
            ).reshape(N_MODES)
            baseline_desired = np.clip(
                feedforward + baseline, lower, upper
            )
            modified_desired = np.clip(
                feedforward + baseline + requested, lower, upper
            )
            modified = modified_desired - feedforward
            updated = dict(out)
            updated["first_correction"] = modified
            sequence = np.asarray(
                updated.get(
                    "sequence_correction",
                    np.zeros((0, N_MODES), dtype=float),
                ),
                dtype=float,
            )
            if sequence.ndim == 2 and len(sequence):
                sequence = sequence.copy()
                sequence[0] = modified
                updated["sequence_correction"] = sequence
            probe_info.update(
                {
                    "requested_delta": requested.tolist(),
                    "applied_correction_delta": (
                        modified - baseline
                    ).tolist(),
                    "applied_desired_delta": (
                        modified_desired - baseline_desired
                    ).tolist(),
                    "baseline_correction": baseline.tolist(),
                    "modified_correction": modified.tolist(),
                    "baseline_desired": baseline_desired.tolist(),
                    "modified_desired": modified_desired.tolist(),
                    "solver_effect_step": effect_step,
                }
            )
            return updated

        r2.r3.solve_delay_aware_physical_correction = wrapped
        try:
            action, trace = super().action(current_state)
        finally:
            r2.r3.solve_delay_aware_physical_correction = original
        if np.any(requested != 0.0) and not probe_info:
            raise ValueError(
                "Stage4.2R3c3 scheduled probe did not reach the solver"
            )
        zeros = np.zeros(N_MODES, dtype=float).tolist()
        trace.update(
            {
                "task_step": task_step,
                "baseline_controller_revision": r3c1.CONTROLLER_REVISION,
                "r3c3_identification_only": True,
                "r3c3_probe_id": self.probe_id,
                "r3c3_probe_mode": self.probe_mode,
                "r3c3_probe_sign": self.probe_sign,
                "r3c3_probe_first_effect_state": (
                    self.probe_first_effect_state
                ),
                "r3c3_probe_task_issue_step": task_step,
                "r3c3_probe_requested_delta": probe_info.get(
                    "requested_delta", zeros
                ),
                "r3c3_probe_applied_correction_delta": probe_info.get(
                    "applied_correction_delta", zeros
                ),
                "r3c3_probe_applied_desired_delta": probe_info.get(
                    "applied_desired_delta", zeros
                ),
                "r3c3_probe_issued": bool(probe_info),
                "pair_or_history_label_used": False,
                "source_result_used": False,
                "source_action_used": False,
                "source_coil_current_used": False,
                "source_wire_current_used": False,
                "current_run_future_used": False,
                "hidden_wire_used": False,
            }
        )
        return action, trace


class LocalRestartTaskClockResponseProbeWorker:
    def __init__(
        self,
        payload: dict[str, Any],
        library: dict[str, Any],
        bundle: dict[str, Any],
        worker_id: str,
        selector_cfg: dict[str, Any],
    ):
        self.plant = r1.LocalPlantReplayWorker(
            payload, library, bundle, worker_id, selector_cfg
        )
        self.base = self.plant.base_worker
        self.bundle = bundle

    def close(self) -> None:
        self.plant.close()

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        failed = True
        result: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "controller_revision": CONTROLLER_REVISION,
            "underlying_controller_revision": r3c1.CONTROLLER_REVISION,
            "experiment_id": str(spec["experiment_id"]),
            "spec": copy.deepcopy(spec),
            "success": False,
            "completed": False,
            "failure_reason": "",
            "trajectory": [],
            "controller_trace": [],
        }
        try:
            horizon = int(spec["horizon_steps"])
            if horizon != _formal_horizon(float(spec["slew_scale"])):
                raise ValueError("Stage4.2R3c3 formal horizon changed")
            self.base.env.reset()
            zero_action = np.zeros(N_COILS, dtype=np.float32)
            initial = r1._state_record_full(
                self.base.env, 0, zero_action
            )
            trajectory = [initial]
            controller = RestartTaskClockLocalResponseProbeController(
                self.base,
                self.bundle,
                _controller_spec(spec),
                initial,
            )
            trace = []
            for step in range(horizon):
                action, controller_row = controller.action(trajectory[-1])
                _, _, terminated, truncated, info = self.base.env.step(
                    action
                )
                next_state = r1._state_record_full(
                    self.base.env, step + 1, action
                )
                trajectory.append(next_state)
                trace.append(controller_row)
                controller.advance(next_state)
                if terminated:
                    raise RuntimeError(
                        str(
                            info.get(
                                "failure_reason",
                                "environment terminated",
                            )
                        )
                    )
                if truncated and step + 1 < horizon:
                    raise RuntimeError(
                        "environment truncated before formal horizon"
                    )
            requested = np.asarray(
                [
                    row["r3c3_probe_requested_delta"]
                    for row in trace
                    if row.get("r3c3_probe_issued")
                ],
                dtype=float,
            )
            applied = np.asarray(
                [
                    row["r3c3_probe_applied_desired_delta"]
                    for row in trace
                    if row.get("r3c3_probe_issued")
                ],
                dtype=float,
            )
            expected_schedule = {
                int(step): np.asarray(value, dtype=float)
                for step, value in spec[
                    "r3c3_probe_delta_by_task_issue_step"
                ].items()
            }
            issued_rows = {
                int(row["task_step"]): row
                for row in trace
                if row.get("r3c3_probe_issued")
            }
            scheduled_probe_exact = bool(
                len(issued_rows) == len(expected_schedule) == 4
                and set(issued_rows) == set(expected_schedule)
                and all(
                    np.array_equal(
                        np.asarray(
                            issued_rows[step][
                                "r3c3_probe_requested_delta"
                            ],
                            dtype=float,
                        ),
                        value,
                    )
                    for step, value in expected_schedule.items()
                )
            )
            applied_probe_exact = bool(
                requested.shape == applied.shape == (4, N_MODES)
                and np.allclose(
                    requested, applied, rtol=0.0, atol=1.0e-12
                )
            )
            requested_net = (
                np.sum(requested, axis=0)
                if requested.shape == (4, N_MODES)
                else np.full(N_MODES, np.nan)
            )
            applied_net = (
                np.sum(applied, axis=0)
                if applied.shape == (4, N_MODES)
                else np.full(N_MODES, np.nan)
            )
            zero_net = bool(
                np.allclose(
                    requested_net,
                    np.zeros(N_MODES),
                    rtol=0.0,
                    atol=1.0e-12,
                )
                and np.allclose(
                    applied_net,
                    np.zeros(N_MODES),
                    rtol=0.0,
                    atol=1.0e-12,
                )
            )
            success = bool(
                len(trajectory) == horizon + 1
                and len(trace) == horizon
                and not any(
                    bool(row.get("abnormal")) for row in trajectory
                )
                and all(bool(row.get("computed_online")) for row in trace)
                and not any(
                    bool(row.get("future_measurement_used"))
                    or bool(row.get("hidden_wire_used"))
                    or bool(row.get("source_action_used"))
                    or bool(row.get("source_coil_current_used"))
                    or bool(row.get("source_wire_current_used"))
                    or bool(row.get("current_run_future_used"))
                    for row in trace
                )
                and all(bool(row.get("solver_success")) for row in trace)
                and scheduled_probe_exact
                and applied_probe_exact
                and zero_net
            )
            result.update(
                {
                    "success": success,
                    "completed": True,
                    "failure_reason": (
                        ""
                        if success
                        else "incomplete or invalid identification-probe rollout"
                    ),
                    "trajectory": trajectory,
                    "controller_trace": trace,
                    "hidden_history_control_summary": {
                        "fresh_controller_actor": True,
                        "fresh_tsc_process": True,
                        "full_tsc_hidden_state_loaded_from_sprsina": True,
                        "controller_history_initialization": (
                            "current_visible_state_only_at_task_step_zero"
                        ),
                        "controller_integral_initialization": "zero",
                        "controller_previous_correction_initialization": "zero",
                        "controller_delay_queue_initialization": (
                            "authenticated_visible_manifold_"
                            "phase_aligned_nominal_prime"
                        ),
                        "reference_phase_start": (
                            controller.reference_phase_start
                        ),
                        "baseline_controller_revision": (
                            r3c1.CONTROLLER_REVISION
                        ),
                        "identification_only": True,
                        "probe_id": controller.probe_id,
                        "probe_mode": controller.probe_mode,
                        "probe_sign": controller.probe_sign,
                        "probe_first_effect_state": (
                            controller.probe_first_effect_state
                        ),
                        "probe_issue_steps": sorted(expected_schedule),
                        "scheduled_probe_exact": scheduled_probe_exact,
                        "applied_probe_exact": applied_probe_exact,
                        "requested_probe_net": requested_net.tolist(),
                        "applied_probe_net": applied_net.tolist(),
                        "requested_and_applied_zero_net": zero_net,
                        "probe_trajectory_allowed_in_expert_dataset": False,
                        "phase_selection": copy.deepcopy(
                            controller.phase_selection
                        ),
                        "visible_reference_manifold_digest": (
                            controller.visible_reference_manifold_digest
                        ),
                        "visible_reference_source_experiment_id": (
                            controller.visible_reference_source_experiment_id
                        ),
                        "task_clock_starts_at_zero": True,
                        "formal_clock_shifted": False,
                        "hidden_wire_current_available_to_controller": False,
                        "full_wire_current_recorded_after_action_choice": True,
                        "online_action_computation": True,
                        "future_action_replay_used": False,
                        "future_measurement_used": False,
                        "source_action_used": False,
                        "source_coil_current_used": False,
                        "source_wire_current_used": False,
                        "current_run_future_used": False,
                    },
                    "wall_time_s": time.time() - started,
                }
            )
            failed = not success
            return _json_safe(result)
        except Exception as exc:
            result.update(
                {
                    "success": False,
                    "completed": True,
                    "failure_reason": repr(exc),
                    "traceback": traceback.format_exc(),
                    "wall_time_s": time.time() - started,
                }
            )
            return _json_safe(result)
        finally:
            runner = getattr(self.base.env, "runner", None)
            if runner is not None:
                runner.cleanup_episode_workspace(
                    failed=failed,
                    reason=(
                        "stage4_2r3c3_restart_task_clock_"
                        "local_response_identification"
                    ),
                )


_CONTROL_RAY_ACTOR = None


def _control_ray_actor_class():
    global _CONTROL_RAY_ACTOR
    if _CONTROL_RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class Stage42R3C3ControlActor:
            def __init__(
                self, payload, library, bundle, worker_id, selector_cfg
            ):
                self.worker = LocalRestartTaskClockResponseProbeWorker(
                    payload, library, bundle, worker_id, selector_cfg
                )

            def evaluate(self, spec):
                return self.worker.evaluate(spec)

            def close(self):
                self.worker.close()
                return True

        _CONTROL_RAY_ACTOR = Stage42R3C3ControlActor
    return _CONTROL_RAY_ACTOR


def _result_complete(
    path: Path, expected_spec: Mapping[str, Any]
) -> bool:
    if not path.is_file():
        return False
    try:
        result = read_json_gz(path)
        identity_complete = bool(
            result.get("completed")
            and str(result.get("stage")) == STAGE
            and str(result.get("controller_revision"))
            == CONTROLLER_REVISION
            and str(result.get("experiment_id"))
            == str(expected_spec["experiment_id"])
            and result.get("spec") == dict(expected_spec)
            and isinstance(result.get("success"), bool)
            and isinstance(result.get("trajectory"), list)
            and isinstance(result.get("controller_trace"), list)
        )
        return identity_complete
    except Exception:
        return False


def _structured_actor_failure(
    spec: Mapping[str, Any], exc: Exception
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "experiment_id": str(spec["experiment_id"]),
        "spec": copy.deepcopy(dict(spec)),
        "success": False,
        "completed": True,
        "failure_reason": repr(exc),
        "traceback": traceback.format_exc(),
        "trajectory": [],
        "controller_trace": [],
    }


def _evaluate_control(
    ctx: Stage42R3C3Context,
    specs: Sequence[dict[str, Any]],
    *,
    backend: str,
    resume: bool,
) -> list[dict[str, Any]]:
    raw_dir = ctx.paths.control / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    library, bundle, selector = r1._library_bundle_selector(
        ctx.source_ctx.r1_ctx
    )
    pending = [
        spec
        for spec in specs
        if not (
            resume
            and _result_complete(
                raw_dir / f"{spec['experiment_id']}.json.gz",
                spec,
            )
        )
    ]
    payloads = {
        str(spec["experiment_id"]): _control_payload(ctx, spec=spec)
        for spec in specs
    }
    if backend == "serial":
        for index, spec in enumerate(pending):
            worker = LocalRestartTaskClockResponseProbeWorker(
                payloads[str(spec["experiment_id"])],
                library,
                bundle,
                f"stage42r3c3_probe_serial_{index:03d}",
                selector,
            )
            try:
                result = worker.evaluate(spec)
            finally:
                worker.close()
            atomic_write_json_gz(
                raw_dir / f"{spec['experiment_id']}.json.gz", result
            )
            print(
                f"[Stage4.2R3c3 control] {index + 1}/{len(pending)}",
                flush=True,
            )
    elif backend == "ray" and pending:
        import ray

        requested = _requested_workers(ctx.cfg)
        plan = ensure_ray_worker_plan(
            ray,
            requested_workers=requested,
            pending_tasks=len(pending),
            ray_tmpdir=os.environ.get("RAY_TMPDIR")
            or ctx.cfg["parallel"].get("ray_tmpdir"),
            log_prefix="[Stage4.2R3c3 control]",
        )
        Actor = _control_ray_actor_class()
        print(
            "[Stage4.2R3c3 control] "
            f"maximum_actor_count={plan.actor_count} "
            f"pending={len(pending)}",
            flush=True,
        )
        completed = 0
        for batch_start in range(0, len(pending), plan.actor_count):
            batch = pending[
                batch_start : batch_start + plan.actor_count
            ]
            actors = []
            refs = {}
            for offset, spec in enumerate(batch):
                index = batch_start + offset
                actor = Actor.remote(
                    payloads[str(spec["experiment_id"])],
                    library,
                    bundle,
                    f"stage42r3c3_probe_{index:03d}",
                    selector,
                )
                actors.append(actor)
                refs[actor.evaluate.remote(spec)] = spec
            print(
                "[Stage4.2R3c3 control] "
                f"batch={batch_start // plan.actor_count + 1} "
                f"actor_count={len(actors)}",
                flush=True,
            )
            try:
                while refs:
                    ready, _ = ray.wait(
                        list(refs), num_returns=1, timeout=30.0
                    )
                    if not ready:
                        print(
                            "[Stage4.2R3c3 control] "
                            f"waiting {completed}/{len(pending)}",
                            flush=True,
                        )
                        continue
                    for ref in ready:
                        spec = refs.pop(ref)
                        try:
                            result = ray.get(ref)
                        except Exception as exc:
                            result = _structured_actor_failure(spec, exc)
                        atomic_write_json_gz(
                            raw_dir
                            / f"{spec['experiment_id']}.json.gz",
                            result,
                        )
                        completed += 1
                        if completed % 8 == 0 or not refs:
                            print(
                                "[Stage4.2R3c3 control] "
                                f"{completed}/{len(pending)}",
                                flush=True,
                            )
            finally:
                r3b.s2._close_ray_actors(
                    actors,
                    timeout_s=float(
                        ctx.cfg["storage"].get(
                            "actor_close_timeout_s", 1800.0
                        )
                    ),
                )
    elif backend not in {"serial", "ray"}:
        raise ValueError("backend must be serial or ray")
    return [
        read_json_gz(raw_dir / f"{spec['experiment_id']}.json.gz")
        for spec in specs
    ]


def _phase_trace_valid(result: Mapping[str, Any]) -> dict[str, Any]:
    """Authenticate the inherited R3c1 trace and the probe overlay."""

    base = r3c1._phase_trace_valid(result)
    trace = list(result.get("controller_trace") or [])
    spec = dict(result.get("spec") or {})
    schedule = {
        int(step): np.asarray(value, dtype=float).reshape(N_MODES)
        for step, value in (
            spec.get("r3c3_probe_delta_by_task_issue_step") or {}
        ).items()
    }
    zeros = np.zeros(N_MODES, dtype=float)
    pair_or_history_count = 0
    source_result_count = 0
    solver_failure_count = 0
    issued_count = 0
    requested_rows = []
    applied_rows = []
    trace_exact = bool(trace and len(schedule) == 4)
    for row in trace:
        step = int(row.get("task_step", -1))
        expected = schedule.get(step, zeros)
        requested = np.asarray(
            row.get("r3c3_probe_requested_delta", []), dtype=float
        ).reshape(-1)
        applied = np.asarray(
            row.get("r3c3_probe_applied_desired_delta", []), dtype=float
        ).reshape(-1)
        issued = bool(row.get("r3c3_probe_issued"))
        expected_issued = step in schedule
        pair_or_history_count += bool(
            row.get("pair_or_history_label_used")
        )
        source_result_count += bool(row.get("source_result_used"))
        solver_failure_count += not bool(row.get("solver_success"))
        issued_count += issued
        trace_exact = bool(
            trace_exact
            and requested.shape == (N_MODES,)
            and applied.shape == (N_MODES,)
            and np.array_equal(requested, expected)
            and issued == expected_issued
            and str(row.get("baseline_controller_revision"))
            == r3c1.CONTROLLER_REVISION
            and bool(row.get("r3c3_identification_only"))
            and str(row.get("r3c3_probe_id"))
            == str(spec.get("r3c3_probe_id"))
            and int(row.get("r3c3_probe_mode", -1))
            == int(spec.get("r3c3_probe_mode", -2))
            and int(row.get("r3c3_probe_sign", 0))
            == int(spec.get("r3c3_probe_sign", 1))
        )
        if issued:
            requested_rows.append(requested)
            applied_rows.append(applied)
    requested = (
        np.stack(requested_rows)
        if len(requested_rows) == 4
        else np.empty((0, N_MODES), dtype=float)
    )
    applied = (
        np.stack(applied_rows)
        if len(applied_rows) == 4
        else np.empty((0, N_MODES), dtype=float)
    )
    requested_net = (
        np.sum(requested, axis=0)
        if requested.shape == (4, N_MODES)
        else np.full(N_MODES, np.nan)
    )
    applied_net = (
        np.sum(applied, axis=0)
        if applied.shape == (4, N_MODES)
        else np.full(N_MODES, np.nan)
    )
    applied_exact = bool(
        requested.shape == applied.shape == (4, N_MODES)
        and np.allclose(requested, applied, rtol=0.0, atol=1.0e-12)
    )
    zero_net = bool(
        np.allclose(requested_net, zeros, rtol=0.0, atol=1.0e-12)
        and np.allclose(applied_net, zeros, rtol=0.0, atol=1.0e-12)
    )
    first_effect_exact = bool(
        schedule
        and min(schedule)
        + int(spec.get("action_delay_steps", -100))
        + 1
        == int(spec.get("r3c3_probe_first_effect_state", -1))
    )
    passed = bool(
        base["passed"]
        and trace_exact
        and issued_count == 4
        and applied_exact
        and zero_net
        and first_effect_exact
        and pair_or_history_count == 0
        and source_result_count == 0
        and solver_failure_count == 0
    )
    return {
        **base,
        "passed": passed,
        "probe_trace_exact": trace_exact,
        "probe_issued_count": issued_count,
        "probe_applied_exact": applied_exact,
        "probe_requested_net": requested_net.tolist(),
        "probe_applied_net": applied_net.tolist(),
        "probe_zero_net": zero_net,
        "probe_first_effect_exact": first_effect_exact,
        "pair_or_history_label_trace_count": pair_or_history_count,
        "source_result_trace_count": source_result_count,
        "solver_failure_count": solver_failure_count,
    }


def _formal_metrics(
    ctx: Stage42R3C3Context, result: Mapping[str, Any]
) -> dict[str, Any]:
    spec = result["spec"]
    r13_ctx = r1._r13_ctx(ctx.source_ctx.r1_ctx)
    policy = r1.r13._timing_policy(
        r13_ctx,
        float(spec["slew_scale"]),
        policy_id=(
            f"r42r3c3_{spec['pair_id']}_{spec['history_member']}_"
            f"{spec['target_id']}_{spec['action_delay_steps']}_"
            f"{spec['slew_scale']}_{spec['r3c3_probe_id']}_"
            f"{spec['r3c3_probe_sign']}"
        ),
    )
    return r1.r8.tracking_metrics(
        r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx,
        result,
        policy,
    )


def _trajectory_arrays(
    result: Mapping[str, Any], dt_s: float
) -> tuple[np.ndarray, np.ndarray]:
    y = np.asarray(
        [
            [row["R"], row["Z"], row["Ip"]]
            for row in result["trajectory"]
        ],
        dtype=float,
    )
    if y.ndim != 2 or y.shape[1] != 3 or not np.all(np.isfinite(y)):
        raise ValueError("invalid R/Z/Ip trajectory")
    velocity = r1.r8._velocity_components(y, dt_s)
    return y, velocity


def _initial_restart_arrays(
    result: Mapping[str, Any],
) -> tuple[np.ndarray, np.ndarray]:
    row = result["trajectory"][0]
    visible = np.asarray(
        [row["R"], row["Z"], row["Ip"], *row["currents_a_tsc"]],
        dtype=float,
    )
    wire = np.asarray(row["wire_currents_a"], dtype=float).reshape(-1)
    return visible, wire


def _rmse(array: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.asarray(array, dtype=float) ** 2)))


def summarize_control(
    ctx: Stage42R3C3Context,
    results: Sequence[Mapping[str, Any]],
    selected_pairs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Summarize execution and preregistered response-identification gates."""

    expected = int(ctx.cfg["control_matrix"]["expected_rollouts"])
    probe_cfg = ctx.cfg["identification_probe"]
    central_cfg = probe_cfg["central_symmetry"]
    history_cfg = probe_cfg["matched_hidden_history"]
    max_util_allowed = float(probe_cfg["maximum_current_utilization"])
    dt_ms = int(
        r1._r13_ctx(ctx.source_ctx.r1_ctx)
        .r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34.env_cfg[
            "dt_ms"
        ]
    )
    dt_s = dt_ms / 1000.0
    state_map = r3b._selected_state_map(selected_pairs)
    result_by_id = {
        str(result["experiment_id"]): result for result in results
    }
    baseline_cache: dict[str, dict[str, Any]] = {}
    baseline_raw_dir = (
        ctx.source_r3c1_run
        / "stage4_2r3c1_authenticated_visible_manifold_control"
        / "raw"
    )

    rows = []
    for result in results:
        spec = result["spec"]
        state_id = str(spec["state_generation_experiment_id"])
        base = r3b._control_row(
            ctx.source_ctx, result, state_map[state_id]
        )
        phase = _phase_trace_valid(result)
        formal = (
            _formal_metrics(ctx, result)
            if bool(result.get("success"))
            else {}
        )
        execution_pass = bool(
            result.get("success")
            and base["fresh_controller"]
            and base["fresh_tsc_process"]
            and base["initial_restart_exact"]
            and base["controller_trace_causal"]
            and phase["passed"]
        )
        if not bool(result.get("success")):
            failure_class = "runtime_or_environment_error"
        elif not bool(base["initial_restart_exact"]):
            failure_class = "plant_restart_fidelity_failure"
        elif not bool(base["controller_trace_causal"]):
            failure_class = "controller_causality_failure"
        elif not bool(phase["passed"]):
            failure_class = "identification_probe_execution_failure"
        else:
            failure_class = ""
        rows.append(
            {
                **base,
                "probe_id": str(spec["r3c3_probe_id"]),
                "probe_mode": int(spec["r3c3_probe_mode"]),
                "probe_sign": int(spec["r3c3_probe_sign"]),
                "probe_first_effect_state": int(
                    spec["r3c3_probe_first_effect_state"]
                ),
                "baseline_experiment_id": str(
                    spec["baseline_experiment_id"]
                ),
                "phase_trace_valid": bool(phase["passed"]),
                "probe_trace_exact": bool(phase["probe_trace_exact"]),
                "probe_issued_count": int(phase["probe_issued_count"]),
                "probe_applied_exact": bool(
                    phase["probe_applied_exact"]
                ),
                "probe_zero_net": bool(phase["probe_zero_net"]),
                "probe_first_effect_exact": bool(
                    phase["probe_first_effect_exact"]
                ),
                "solver_failure_count": int(
                    phase["solver_failure_count"]
                ),
                "pair_or_history_label_trace_count": int(
                    phase["pair_or_history_label_trace_count"]
                ),
                "source_result_trace_count": int(
                    phase["source_result_trace_count"]
                ),
                "hidden_wire_trace_count": int(
                    phase["hidden_wire_trace_count"]
                ),
                "source_action_trace_count": int(
                    phase["source_action_trace_count"]
                ),
                "source_coil_current_trace_count": int(
                    phase["source_coil_current_trace_count"]
                ),
                "source_wire_current_trace_count": int(
                    phase["source_wire_current_trace_count"]
                ),
                "current_run_future_trace_count": int(
                    phase["current_run_future_trace_count"]
                ),
                "max_current_utilization": (
                    float(formal["max_current_utilization"])
                    if formal
                    else None
                ),
                "formal_contract_pass": bool(
                    formal.get("stage3_4_target_tracking_pass", False)
                ),
                "formal_minimum_signed_margin": (
                    float(
                        formal[
                            "stage3_4_tracking_minimum_signed_margin"
                        ]
                    )
                    if formal
                    else None
                ),
                "execution_pass": execution_pass,
                "failure_class": failure_class,
                "passed": execution_pass,
                "identification_only": True,
                "probe_trajectory_allowed_in_expert_dataset": False,
            }
        )

    signed_groups: dict[
        tuple[str, str, str, int, float, str],
        dict[int, Mapping[str, Any]],
    ] = defaultdict(dict)
    for result in results:
        spec = result["spec"]
        key = (
            str(spec["pair_id"]),
            str(spec["history_member"]),
            str(spec["target_id"]),
            int(spec["action_delay_steps"]),
            float(spec["slew_scale"]),
            str(spec["r3c3_probe_id"]),
        )
        sign = int(spec["r3c3_probe_sign"])
        if sign in signed_groups[key]:
            raise ValueError("duplicate signed response probe")
        signed_groups[key][sign] = result

    response_rows = []
    odd_by_key: dict[
        tuple[str, str, str, int, float, str],
        tuple[np.ndarray, np.ndarray, np.ndarray, int],
    ] = {}
    for key in sorted(signed_groups):
        signed = signed_groups[key]
        row: dict[str, Any] = {
            "pair_id": key[0],
            "history_member": key[1],
            "target_id": key[2],
            "actual_delay_steps": key[3],
            "actual_slew_scale": key[4],
            "probe_id": key[5],
            "signed_member_count": len(signed),
            "response_available": False,
            "baseline_initial_state_exact": False,
            "even_velocity_rmse_m_per_s": None,
            "even_position_rmse_m": None,
            "even_ip_rmse_A": None,
            "central_symmetry_pass": False,
        }
        if set(signed) == {-1, 1} and all(
            bool(result.get("success")) for result in signed.values()
        ):
            plus = signed[1]
            minus = signed[-1]
            baseline_id = str(
                plus["spec"]["baseline_experiment_id"]
            )
            if (
                baseline_id
                != str(minus["spec"]["baseline_experiment_id"])
            ):
                raise ValueError("signed probe baseline mismatch")
            if baseline_id not in baseline_cache:
                baseline_cache[baseline_id] = read_json_gz(
                    baseline_raw_dir / f"{baseline_id}.json.gz"
                )
            baseline = baseline_cache[baseline_id]
            plus_y, plus_v = _trajectory_arrays(plus, dt_s)
            minus_y, minus_v = _trajectory_arrays(minus, dt_s)
            base_y, base_v = _trajectory_arrays(baseline, dt_s)
            same_shape = (
                plus_y.shape == minus_y.shape == base_y.shape
                and plus_v.shape == minus_v.shape == base_v.shape
            )
            plus_initial = _initial_restart_arrays(plus)
            minus_initial = _initial_restart_arrays(minus)
            base_initial = _initial_restart_arrays(baseline)
            initial_exact = bool(
                np.array_equal(plus_initial[0], minus_initial[0])
                and np.array_equal(plus_initial[0], base_initial[0])
                and np.array_equal(plus_initial[1], minus_initial[1])
                and np.array_equal(plus_initial[1], base_initial[1])
            )
            first_effect = int(
                plus["spec"]["r3c3_probe_first_effect_state"]
            )
            if same_shape and first_effect < len(plus_y):
                section = slice(first_effect, len(plus_y))
                odd_y = (plus_y - minus_y) / 2.0
                odd_v = (plus_v - minus_v) / 2.0
                even_y = (plus_y + minus_y) / 2.0 - base_y
                even_v = (plus_v + minus_v) / 2.0 - base_v
                velocity_rmse = _rmse(even_v[section, :2])
                position_rmse = _rmse(even_y[section, :2])
                ip_rmse = _rmse(even_y[section, 2])
                central_pass = bool(
                    initial_exact
                    and velocity_rmse
                    <= float(
                        central_cfg[
                            "maximum_even_velocity_rmse_m_per_s"
                        ]
                    )
                    and position_rmse
                    <= float(
                        central_cfg["maximum_even_position_rmse_m"]
                    )
                    and ip_rmse
                    <= float(central_cfg["maximum_even_ip_rmse_A"])
                )
                row.update(
                    {
                        "response_available": True,
                        "baseline_initial_state_exact": initial_exact,
                        "first_effect_state": first_effect,
                        "even_velocity_rmse_m_per_s": velocity_rmse,
                        "even_position_rmse_m": position_rmse,
                        "even_ip_rmse_A": ip_rmse,
                        "central_symmetry_pass": central_pass,
                    }
                )
                odd_by_key[key] = (
                    odd_y,
                    odd_v,
                    base_y,
                    first_effect,
                )
        response_rows.append(row)

    history_rows = []
    history_groups: dict[
        tuple[str, str, int, float, str],
        dict[str, tuple[np.ndarray, np.ndarray, np.ndarray, int]],
    ] = defaultdict(dict)
    for key, response in odd_by_key.items():
        history_groups[(key[0], key[2], key[3], key[4], key[5])][
            key[1]
        ] = response
    for key in sorted(history_groups):
        members = history_groups[key]
        row = {
            "pair_id": key[0],
            "target_id": key[1],
            "actual_delay_steps": key[2],
            "actual_slew_scale": key[3],
            "probe_id": key[4],
            "history_member_count": len(members),
            "odd_velocity_rmse_m_per_s": None,
            "odd_position_rmse_m": None,
            "odd_ip_rmse_A": None,
            "matched_hidden_history_pass": False,
        }
        if set(members) == {"plus_first", "minus_first"}:
            plus = members["plus_first"]
            minus = members["minus_first"]
            if plus[0].shape == minus[0].shape:
                first_effect = max(plus[3], minus[3])
                section = slice(first_effect, len(plus[0]))
                position_rmse = _rmse(
                    plus[0][section, :2] - minus[0][section, :2]
                )
                velocity_rmse = _rmse(
                    plus[1][section, :2] - minus[1][section, :2]
                )
                ip_rmse = _rmse(
                    plus[0][section, 2] - minus[0][section, 2]
                )
                matched_pass = bool(
                    velocity_rmse
                    <= float(
                        history_cfg[
                            "maximum_odd_velocity_rmse_m_per_s"
                        ]
                    )
                    and position_rmse
                    <= float(
                        history_cfg["maximum_odd_position_rmse_m"]
                    )
                    and ip_rmse
                    <= float(history_cfg["maximum_odd_ip_rmse_A"])
                )
                row.update(
                    {
                        "odd_velocity_rmse_m_per_s": velocity_rmse,
                        "odd_position_rmse_m": position_rmse,
                        "odd_ip_rmse_A": ip_rmse,
                        "matched_hidden_history_pass": matched_pass,
                    }
                )
        history_rows.append(row)

    condition_rows = []
    context_groups: dict[
        tuple[str, str, str, int, float],
        dict[str, tuple[np.ndarray, np.ndarray, np.ndarray, int]],
    ] = defaultdict(dict)
    for key, response in odd_by_key.items():
        context_groups[key[:5]][key[5]] = response
    expected_probe_ids = {
        str(row["probe_id"]) for row in probe_cfg["basis"]
    }
    for key in sorted(context_groups):
        probes = context_groups[key]
        condition = None
        matrix_rank = None
        passed = False
        if set(probes) == expected_probe_ids:
            first_state = min(value[3] for value in probes.values())
            columns = [
                probes[probe_id][1][first_state:, :2].reshape(-1)
                for probe_id in sorted(expected_probe_ids)
            ]
            matrix = np.stack(columns, axis=1)
            matrix_rank = int(np.linalg.matrix_rank(matrix))
            condition = float(np.linalg.cond(matrix))
            passed = bool(
                matrix_rank == len(expected_probe_ids)
                and math.isfinite(condition)
                and condition
                <= float(
                    probe_cfg[
                        "maximum_selected_velocity_condition_number"
                    ]
                )
            )
        condition_rows.append(
            {
                "pair_id": key[0],
                "history_member": key[1],
                "target_id": key[2],
                "actual_delay_steps": key[3],
                "actual_slew_scale": key[4],
                "probe_basis_count": len(probes),
                "velocity_response_matrix_rank": matrix_rank,
                "selected_velocity_condition_number": condition,
                "condition_number_pass": passed,
            }
        )

    current_values = [
        float(row["max_current_utilization"])
        for row in rows
        if row["max_current_utilization"] is not None
    ]
    execution_pass_count = sum(bool(row["execution_pass"]) for row in rows)
    central_pass_count = sum(
        bool(row["central_symmetry_pass"]) for row in response_rows
    )
    history_pass_count = sum(
        bool(row["matched_hidden_history_pass"]) for row in history_rows
    )
    condition_pass_count = sum(
        bool(row["condition_number_pass"]) for row in condition_rows
    )
    maximum_current_utilization = (
        max(current_values) if current_values else None
    )
    expected_response_groups = expected // 2
    expected_history_groups = expected // 4
    expected_condition_groups = int(
        ctx.cfg["control_matrix"]["expected_baseline_contexts"]
    )
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "restart_task_clock_local_response_identification",
        "identification_only": True,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "development_set_only": True,
        "independent_hidden_history_confirmation": False,
        "expected_rollouts": expected,
        "n_rollouts": len(rows),
        "execution_pass_count": execution_pass_count,
        "runtime_or_environment_error_count": sum(
            row["failure_class"] == "runtime_or_environment_error"
            for row in rows
        ),
        "plant_restart_fidelity_failure_count": sum(
            row["failure_class"] == "plant_restart_fidelity_failure"
            for row in rows
        ),
        "controller_causality_failure_count": sum(
            row["failure_class"] == "controller_causality_failure"
            for row in rows
        ),
        "hidden_wire_controller_input_count": sum(
            int(row["hidden_wire_trace_count"]) for row in rows
        ),
        "source_action_use_count": sum(
            int(row["source_action_trace_count"]) for row in rows
        ),
        "source_coil_current_use_count": sum(
            int(row["source_coil_current_trace_count"])
            for row in rows
        ),
        "source_wire_current_use_count": sum(
            int(row["source_wire_current_trace_count"])
            for row in rows
        ),
        "current_run_future_use_count": sum(
            int(row["current_run_future_trace_count"])
            for row in rows
        ),
        "pair_or_history_label_use_count": sum(
            int(row["pair_or_history_label_trace_count"])
            for row in rows
        ),
        "source_result_use_count": sum(
            int(row["source_result_trace_count"]) for row in rows
        ),
        "identification_probe_execution_failure_count": sum(
            row["failure_class"]
            == "identification_probe_execution_failure"
            for row in rows
        ),
        "solver_failure_count": sum(
            int(row["solver_failure_count"]) for row in rows
        ),
        "formal_contract_pass_count": sum(
            bool(row["formal_contract_pass"]) for row in rows
        ),
        "formal_contract_failure_count": sum(
            not bool(row["formal_contract_pass"]) for row in rows
        ),
        "formal_tracking_is_acceptance_gate": False,
        "response_group_count": len(response_rows),
        "expected_response_group_count": expected_response_groups,
        "central_symmetry_pass_count": central_pass_count,
        "central_symmetry_failure_count": (
            len(response_rows) - central_pass_count
        ),
        "matched_hidden_history_group_count": len(history_rows),
        "expected_matched_hidden_history_group_count": (
            expected_history_groups
        ),
        "matched_hidden_history_pass_count": history_pass_count,
        "matched_hidden_history_failure_count": (
            len(history_rows) - history_pass_count
        ),
        "condition_number_group_count": len(condition_rows),
        "expected_condition_number_group_count": (
            expected_condition_groups
        ),
        "condition_number_pass_count": condition_pass_count,
        "condition_number_failure_count": (
            len(condition_rows) - condition_pass_count
        ),
        "maximum_selected_velocity_condition_number": (
            max(
                float(row["selected_velocity_condition_number"])
                for row in condition_rows
                if row["selected_velocity_condition_number"] is not None
            )
            if any(
                row["selected_velocity_condition_number"] is not None
                for row in condition_rows
            )
            else None
        ),
        "maximum_current_utilization": maximum_current_utilization,
        "maximum_current_utilization_allowed": max_util_allowed,
        "current_utilization_pass": bool(
            maximum_current_utilization is not None
            and maximum_current_utilization <= max_util_allowed
        ),
    }
    summary["execution_gate_passed"] = bool(
        len(rows) == expected
        and execution_pass_count == expected
        and summary["hidden_wire_controller_input_count"] == 0
        and summary["source_action_use_count"] == 0
        and summary["source_coil_current_use_count"] == 0
        and summary["source_wire_current_use_count"] == 0
        and summary["current_run_future_use_count"] == 0
        and summary["pair_or_history_label_use_count"] == 0
        and summary["source_result_use_count"] == 0
    )
    summary["central_symmetry_gate_passed"] = bool(
        len(response_rows) == expected_response_groups
        and central_pass_count == expected_response_groups
    )
    summary["matched_hidden_history_gate_passed"] = bool(
        len(history_rows) == expected_history_groups
        and history_pass_count == expected_history_groups
    )
    summary["condition_number_gate_passed"] = bool(
        len(condition_rows) == expected_condition_groups
        and condition_pass_count == expected_condition_groups
    )
    summary["passed"] = bool(
        summary["execution_gate_passed"]
        and summary["central_symmetry_gate_passed"]
        and summary["matched_hidden_history_gate_passed"]
        and summary["condition_number_gate_passed"]
        and summary["current_utilization_pass"]
    )
    atomic_write_json(ctx.paths.control / "results.json", rows)
    write_csv(ctx.paths.control / "results.csv", rows)
    atomic_write_json(
        ctx.paths.control / "central_response_results.json",
        response_rows,
    )
    write_csv(
        ctx.paths.control / "central_response_results.csv",
        response_rows,
    )
    atomic_write_json(
        ctx.paths.control / "matched_hidden_history_results.json",
        history_rows,
    )
    write_csv(
        ctx.paths.control / "matched_hidden_history_results.csv",
        history_rows,
    )
    atomic_write_json(
        ctx.paths.control / "condition_number_results.json",
        condition_rows,
    )
    write_csv(
        ctx.paths.control / "condition_number_results.csv",
        condition_rows,
    )
    atomic_write_json(ctx.paths.control / "summary.json", summary)
    return summary

def _prepare_dirs(paths: Stage42R3C3Paths) -> None:
    for path in (
        paths.run_dir,
        paths.source_reference,
        paths.variants,
        paths.control,
        paths.control / "raw",
        paths.analysis,
    ):
        path.mkdir(parents=True, exist_ok=True)


def prepare(
    ctx: Stage42R3C3Context,
    *,
    resume: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    _prepare_dirs(ctx.paths)
    selected_pairs, _ = _recompute_selected_pairs(ctx)
    specs = build_control_specs(ctx, selected_pairs)
    package_fingerprint = _deployed_package_fingerprint(ctx)
    manifold_by_digest = {
        str(spec["visible_reference_manifold_digest"]): copy.deepcopy(
            spec["visible_reference_manifold"]
        )
        for spec in specs
    }
    visible_reference_manifolds = [
        manifold_by_digest[digest]
        for digest in sorted(manifold_by_digest)
    ]
    if len(visible_reference_manifolds) != 4:
        raise ValueError(
            "Stage4.2R3c3 requires four authenticated visible manifolds"
        )
    selected_public = [
        {
            "pair_id": str(pair["pair_id"]),
            "common_prefix_steps": int(pair["common_prefix_steps"]),
            "nullspace_direction_index": int(
                pair["nullspace_direction_index"]
            ),
            "amplitude_fraction": float(pair["amplitude_fraction"]),
            "gap_steps": int(pair["gap_steps"]),
            "plus_first_experiment_id": str(
                pair["plus_first_state"]["experiment_id"]
            ),
            "minus_first_experiment_id": str(
                pair["minus_first_state"]["experiment_id"]
            ),
            "plus_first_snapshot_dir": str(
                pair["plus_first_state"]["snapshot_dir"]
            ),
            "minus_first_snapshot_dir": str(
                pair["minus_first_state"]["snapshot_dir"]
            ),
            "plus_first_snapshot_manifest_digest": str(
                pair["plus_first_state"]["snapshot_manifest_digest"]
            ),
            "minus_first_snapshot_manifest_digest": str(
                pair["minus_first_state"]["snapshot_manifest_digest"]
            ),
        }
        for pair in selected_pairs
    ]
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "source_stage4_2r3b_run": str(ctx.source_r3b_run),
        "source_stage4_2r3b_audit": str(ctx.source_r3b_audit),
        "source_fingerprint": ctx.source_fingerprint,
        "source_stage4_2r3c_run": str(ctx.source_r3c_run),
        "source_stage4_2r3c_audit": str(ctx.source_r3c_audit),
        "source_stage4_2r3c_fingerprint": (
            ctx.source_r3c_fingerprint
        ),
        "source_stage4_2r3c1_run": str(ctx.source_r3c1_run),
        "source_stage4_2r3c1_audit": str(ctx.source_r3c1_audit),
        "source_stage4_2r3c1_fingerprint": (
            ctx.source_r3c1_fingerprint
        ),
        "source_stage4_2r3c2_run": str(ctx.source_r3c2_run),
        "source_stage4_2r3c2_audit": str(ctx.source_r3c2_audit),
        "source_stage4_2r3c2_fingerprint": (
            ctx.source_r3c2_fingerprint
        ),
        "deployed_package_fingerprint": package_fingerprint,
        "config_digest": _canonical_digest(ctx.cfg),
        "selected_snapshot_sources": selected_public,
        "selected_snapshot_source_digest": _canonical_digest(
            selected_public
        ),
        "control_spec_digest": _canonical_digest(specs),
        "visible_reference_manifolds": visible_reference_manifolds,
        "visible_reference_manifold_digest": _canonical_digest(
            visible_reference_manifolds
        ),
        "phase_alignment": copy.deepcopy(ctx.cfg["phase_alignment"]),
        "identification_probe": copy.deepcopy(
            ctx.cfg["identification_probe"]
        ),
        "formal_timing_contract": copy.deepcopy(
            ctx.cfg["formal_timing_contract"]
        ),
        "control_matrix": copy.deepcopy(ctx.cfg["control_matrix"]),
        "development_set_only": True,
        "independent_hidden_history_confirmation": False,
    }
    original_package_fingerprint = package_fingerprint
    if ctx.paths.manifest.is_file():
        old = read_json(ctx.paths.manifest)
        if not resume:
            raise FileExistsError(
                "Stage4.2R3c3 run exists; use --resume or a fresh run"
            )
        for key in (
            "stage",
            "controller_revision",
            "package_revision",
            "source_stage4_2r3b_run",
            "source_stage4_2r3b_audit",
            "source_fingerprint",
            "source_stage4_2r3c_run",
            "source_stage4_2r3c_audit",
            "source_stage4_2r3c_fingerprint",
            "source_stage4_2r3c1_run",
            "source_stage4_2r3c1_audit",
            "source_stage4_2r3c1_fingerprint",
            "source_stage4_2r3c2_run",
            "source_stage4_2r3c2_audit",
            "source_stage4_2r3c2_fingerprint",
            "config_digest",
            "selected_snapshot_source_digest",
            "control_spec_digest",
            "visible_reference_manifold_digest",
            "phase_alignment",
            "identification_probe",
            "formal_timing_contract",
            "control_matrix",
        ):
            if old.get(key) != manifest.get(key):
                raise ValueError(
                    "Stage4.2R3c3 resume incompatibility in "
                    f"manifest field {key}"
                )
        original_package_fingerprint = dict(
            old.get("deployed_package_fingerprint") or {}
        )
        _semantics_preserving_resume_compatibility(
            ctx, original_package_fingerprint, package_fingerprint
        )
    else:
        atomic_write_json(ctx.paths.manifest, manifest)
    atomic_write_json(
        ctx.paths.run_dir / "stage4_2r3c3_config.resolved.json",
        ctx.cfg,
    )
    atomic_write_json(
        ctx.paths.source_reference
        / "stage4_2r3b_source_fingerprint.json",
        ctx.source_fingerprint,
    )
    atomic_write_json(
        ctx.paths.source_reference
        / "stage4_2r3c_source_fingerprint.json",
        ctx.source_r3c_fingerprint,
    )
    atomic_write_json(
        ctx.paths.source_reference
        / "stage4_2r3c1_source_fingerprint.json",
        ctx.source_r3c1_fingerprint,
    )
    atomic_write_json(
        ctx.paths.source_reference
        / "stage4_2r3c1_restart_regulation_diagnostic.json",
        ctx.source_r3c1_restart_regulation_diagnostic,
    )
    atomic_write_json(
        ctx.paths.source_reference
        / "stage4_2r3c2_source_fingerprint.json",
        ctx.source_r3c2_fingerprint,
    )
    original_fingerprint_path = (
        ctx.paths.source_reference
        / "deployed_package_fingerprint.json"
    )
    atomic_write_json(original_fingerprint_path, package_fingerprint)
    atomic_write_json(
        ctx.paths.source_reference / "selected_snapshot_sources.json",
        selected_public,
    )
    atomic_write_json(
        ctx.paths.source_reference
        / "authenticated_visible_reference_manifolds.json",
        visible_reference_manifolds,
    )
    atomic_write_json(
        ctx.paths.source_reference / "control_specs.json", specs
    )
    state = (
        read_json(ctx.paths.state)
        if ctx.paths.state.is_file()
        else {
            "schema_version": 1,
            "stage": STAGE,
            "controller_revision": CONTROLLER_REVISION,
            "package_revision": PACKAGE_REVISION,
            "prepared": True,
            "finished": False,
            "primary_pass": False,
            "phase_status": "prepared",
            "stop_reason": "",
        }
    )
    state.update({"updated_utc": utc_timestamp()})
    atomic_write_json(ctx.paths.state, state)
    return selected_pairs, specs


def run_offline_probe_audit(
    ctx: Stage42R3C3Context,
    selected_pairs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Fail-closed audit without advancing a TSC process."""

    specs = build_control_specs(ctx, selected_pairs)
    library, bundle, selector = r1._library_bundle_selector(
        ctx.source_ctx.r1_ctx
    )
    baseline_raw_dir = (
        ctx.source_r3c1_run
        / "stage4_2r3c1_authenticated_visible_manifold_control"
        / "raw"
    )
    schedule_rows = []
    for spec in specs:
        schedule = {
            int(step): np.asarray(value, dtype=float).reshape(N_MODES)
            for step, value in spec[
                "r3c3_probe_delta_by_task_issue_step"
            ].items()
        }
        requested_net = np.sum(
            np.stack(list(schedule.values())), axis=0
        )
        nonzero = np.asarray(
            [value for value in schedule.values()], dtype=float
        )
        amplitude = float(spec["r3c3_probe_amplitude"])
        mode = int(spec["r3c3_probe_mode"])
        first_effect_exact = bool(
            min(schedule)
            + int(spec["action_delay_steps"])
            + 1
            == int(spec["r3c3_probe_first_effect_state"])
        )
        schedule_exact = bool(
            len(schedule) == 4
            and np.array_equal(
                requested_net, np.zeros(N_MODES, dtype=float)
            )
            and first_effect_exact
            and all(
                np.count_nonzero(value) == 1
                and math.isclose(
                    abs(float(value[mode])),
                    amplitude,
                    rel_tol=0.0,
                    abs_tol=1.0e-15,
                )
                for value in nonzero
            )
            and not _FORBIDDEN_CONTROLLER_SPEC_KEYS.intersection(
                _controller_spec(spec)
            )
        )
        schedule_rows.append(
            {
                "experiment_id": str(spec["experiment_id"]),
                "baseline_experiment_id": str(
                    spec["baseline_experiment_id"]
                ),
                "pair_id": str(spec["pair_id"]),
                "history_member": str(spec["history_member"]),
                "target_id": str(spec["target_id"]),
                "actual_delay_steps": int(
                    spec["action_delay_steps"]
                ),
                "actual_slew_scale": float(spec["slew_scale"]),
                "probe_id": str(spec["r3c3_probe_id"]),
                "probe_sign": int(spec["r3c3_probe_sign"]),
                "issue_steps": sorted(schedule),
                "first_effect_state": int(
                    spec["r3c3_probe_first_effect_state"]
                ),
                "requested_net": requested_net.tolist(),
                "schedule_exact": schedule_exact,
            }
        )

    context_specs: dict[
        tuple[str, str, str, int, float], Mapping[str, Any]
    ] = {}
    for spec in specs:
        key = (
            str(spec["pair_id"]),
            str(spec["history_member"]),
            str(spec["target_id"]),
            int(spec["action_delay_steps"]),
            float(spec["slew_scale"]),
        )
        context_specs.setdefault(key, spec)

    context_rows = []
    for index, key in enumerate(sorted(context_specs)):
        spec = context_specs[key]
        baseline_id = str(spec["baseline_experiment_id"])
        baseline = read_json_gz(
            baseline_raw_dir / f"{baseline_id}.json.gz"
        )
        trajectory = list(baseline.get("trajectory") or [])
        if len(trajectory) != int(spec["horizon_steps"]) + 1:
            raise ValueError("R3c1 baseline trajectory length mismatch")
        initial = copy.deepcopy(dict(trajectory[0]))
        initial["step_index"] = 0
        payload = _control_payload(ctx, spec=spec)
        plant = r1.LocalPlantReplayWorker(
            payload,
            library,
            bundle,
            f"stage42r3c3_offline_{index:03d}",
            selector,
        )
        try:
            sanitized = _controller_spec(spec)
            baseline_controller = (
                r3c1.AuthenticatedVisibleManifoldPhaseTaskController(
                    plant.base_worker, bundle, sanitized, initial
                )
            )
            probe_controller = (
                RestartTaskClockLocalResponseProbeController(
                    plant.base_worker, bundle, sanitized, initial
                )
            )
            hidden_initial = copy.deepcopy(initial)
            hidden_initial["wire_currents_a"] = [
                float(wire_index + 1) * 1.0e9
                for wire_index in range(N_WIRES)
            ]
            hidden_controller = (
                RestartTaskClockLocalResponseProbeController(
                    plant.base_worker,
                    bundle,
                    sanitized,
                    hidden_initial,
                )
            )
            baseline_action, baseline_trace = (
                baseline_controller.action(initial)
            )
            probe_action, probe_trace = probe_controller.action(initial)
            hidden_action, _ = hidden_controller.action(hidden_initial)
            recorded_action = np.asarray(
                trajectory[1]["action_norm_tsc"], dtype=float
            ).reshape(N_COILS)
            baseline_difference = float(
                np.max(
                    np.abs(
                        np.asarray(baseline_action, dtype=float)
                        - recorded_action
                    )
                )
            )
            probe_difference = float(
                np.max(
                    np.abs(
                        np.asarray(probe_action, dtype=float)
                        - baseline_action
                    )
                )
            )
            hidden_difference = float(
                np.max(
                    np.abs(
                        np.asarray(hidden_action, dtype=float)
                        - probe_action
                    )
                )
            )
            passed = bool(
                np.array_equal(
                    np.asarray(baseline_action, dtype=float),
                    recorded_action,
                )
                and np.array_equal(
                    np.asarray(probe_action, dtype=float),
                    np.asarray(baseline_action, dtype=float),
                )
                and np.array_equal(
                    np.asarray(hidden_action, dtype=float),
                    np.asarray(probe_action, dtype=float),
                )
                and int(baseline_trace["task_step"]) == 0
                and int(probe_trace["task_step"]) == 0
                and not bool(probe_trace["r3c3_probe_issued"])
                and not bool(probe_trace["hidden_wire_used"])
                and not bool(probe_trace["source_action_used"])
                and not bool(probe_trace["source_result_used"])
                and int(
                    probe_trace["measurement_max_state_index_used"]
                )
                == 0
            )
            context_rows.append(
                {
                    "pair_id": key[0],
                    "history_member": key[1],
                    "target_id": key[2],
                    "actual_delay_steps": key[3],
                    "actual_slew_scale": key[4],
                    "baseline_experiment_id": baseline_id,
                    "selected_reference_phase": int(
                        probe_controller.reference_phase_start
                    ),
                    "baseline_first_action_exact": bool(
                        baseline_difference == 0.0
                    ),
                    "probe_first_action_preserves_baseline": bool(
                        probe_difference == 0.0
                    ),
                    "hidden_wire_variant_first_action_exact": bool(
                        hidden_difference == 0.0
                    ),
                    "maximum_baseline_action_abs_difference": (
                        baseline_difference
                    ),
                    "maximum_probe_action_abs_difference": (
                        probe_difference
                    ),
                    "maximum_hidden_action_abs_difference": (
                        hidden_difference
                    ),
                    "passed": passed,
                }
            )
        finally:
            plant.close()

    expected_rollouts = int(
        ctx.cfg["control_matrix"]["expected_rollouts"]
    )
    expected_contexts = int(
        ctx.cfg["control_matrix"]["expected_baseline_contexts"]
    )
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "offline_restart_task_clock_probe_audit",
        "expected_probe_specs": expected_rollouts,
        "probe_spec_count": len(schedule_rows),
        "probe_schedule_exact_count": sum(
            bool(row["schedule_exact"]) for row in schedule_rows
        ),
        "expected_baseline_contexts": expected_contexts,
        "baseline_context_count": len(context_rows),
        "baseline_first_action_exact_count": sum(
            bool(row["baseline_first_action_exact"])
            for row in context_rows
        ),
        "probe_first_action_preserved_count": sum(
            bool(row["probe_first_action_preserves_baseline"])
            for row in context_rows
        ),
        "hidden_wire_invariant_first_action_count": sum(
            bool(row["hidden_wire_variant_first_action_exact"])
            for row in context_rows
        ),
        "future_action_read_count": 0,
        "future_measurement_use_count": 0,
        "pair_or_history_label_controller_input_count": 0,
        "source_result_controller_input_count": 0,
        "real_tsc_executed": False,
    }
    summary["passed"] = bool(
        len(schedule_rows) == expected_rollouts
        and summary["probe_schedule_exact_count"] == expected_rollouts
        and len(context_rows) == expected_contexts
        and summary["baseline_first_action_exact_count"]
        == expected_contexts
        and summary["probe_first_action_preserved_count"]
        == expected_contexts
        and summary["hidden_wire_invariant_first_action_count"]
        == expected_contexts
    )
    output = {
        "summary": summary,
        "probe_schedules": schedule_rows,
        "baseline_contexts": context_rows,
    }
    atomic_write_json(
        ctx.paths.source_reference
        / "offline_restart_task_clock_probe_audit.json",
        output,
    )
    return summary

def analyze(
    ctx: Stage42R3C3Context,
    control_summary: Mapping[str, Any],
) -> dict[str, Any]:
    primary_pass = bool(control_summary.get("passed"))
    verdict = {
        "schema_version": 1,
        "stage": STAGE,
        "verdict": (
            "STAGE4_2R3C3_LOCAL_RESPONSE_IDENTIFICATION_PASS"
            if primary_pass
            else "STAGE4_2R3C3_LOCAL_RESPONSE_IDENTIFICATION_FAILED"
        ),
        "source_stage4_2r3b_run": str(ctx.source_r3b_run),
        "source_stage4_2r3c_run": str(ctx.source_r3c_run),
        "source_stage4_2r3c1_run": str(ctx.source_r3c1_run),
        "source_stage4_2r3c2_run": str(ctx.source_r3c2_run),
        "plant_restart_fidelity_preserved": bool(
            control_summary.get(
                "plant_restart_fidelity_failure_count", 1
            )
            == 0
            and control_summary.get("execution_gate_passed")
        ),
        "controller_causality_preserved": bool(
            control_summary.get("controller_causality_failure_count", 1)
            == 0
            and control_summary.get("execution_gate_passed")
        ),
        "formal_contract_pass_count": int(
            control_summary.get("formal_contract_pass_count", 0)
        ),
        "formal_contract_failure_count": int(
            control_summary.get("formal_contract_failure_count", 0)
        ),
        "formal_tracking_is_acceptance_gate": False,
        "central_symmetry_gate_passed": bool(
            control_summary.get("central_symmetry_gate_passed")
        ),
        "matched_hidden_history_gate_passed": bool(
            control_summary.get("matched_hidden_history_gate_passed")
        ),
        "condition_number_gate_passed": bool(
            control_summary.get("condition_number_gate_passed")
        ),
        "current_utilization_pass": bool(
            control_summary.get("current_utilization_pass")
        ),
        "development_set_local_response_identified": primary_pass,
        "identification_only": True,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "independent_hidden_history_confirmation": False,
        "matched_visible_different_hidden_history_validated": False,
        "different_initial_state_independent_validation": False,
        "unseen_target_validated": False,
        "continuous_parameter_change_validated": False,
        "plant_jacobian_error_validated": False,
        "measurement_noise_validated": False,
        "disturbance_recovery_validated": False,
        "independent_long_hold_validated": False,
        "finite_test_envelope_only": True,
        "bc_dagger_or_rl_allowed": False,
        "primary_pass": primary_pass,
        "next_if_pass": (
            "Freeze the authenticated local response envelope and build "
            "Stage4.2R3c4 restart-task-clock response-model MPC. Do not "
            "start BC, DAgger, or RL."
        ),
        "next_if_fail": (
            "Preserve all raw probes. If matched-history response fails, "
            "add observer/history-state identification before more MPC; "
            "if central symmetry or conditioning fails, revise the "
            "identification design without weakening preregistered gates."
        ),
    }
    summary = {
        **verdict,
        "created_utc": utc_timestamp(),
        "control_summary": dict(control_summary),
    }
    atomic_write_json(
        ctx.paths.analysis / "stage4_2r3c3_verdict.json", verdict
    )
    atomic_write_json(
        ctx.paths.analysis / "stage4_2r3c3_summary.json", summary
    )
    state = read_json(ctx.paths.state)
    state.update(
        {
            "finished": True,
            "primary_pass": primary_pass,
            "phase_status": "campaign_complete",
            "stop_reason": (
                ""
                if primary_pass
                else "local_response_identification_gate_failed"
            ),
            "updated_utc": utc_timestamp(),
            "verdict": verdict,
        }
    )
    atomic_write_json(ctx.paths.state, state)
    return summary


def execute(
    ctx: Stage42R3C3Context,
    *,
    command: str,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    selected_pairs, specs = prepare(ctx, resume=resume)
    offline = run_offline_probe_audit(
        ctx, selected_pairs
    )
    if not bool(offline.get("passed")):
        raise RuntimeError(
            "Stage4.2R3c3 offline identification-probe gate failed; "
            "no real TSC probe was started"
        )
    if command == "offline":
        state = read_json(ctx.paths.state)
        state.update(
            {
                "finished": False,
                "primary_pass": False,
                "phase_status": "offline_gate_complete",
                "stop_reason": "",
                "offline_probe_audit": dict(offline),
                "updated_utc": utc_timestamp(),
            }
        )
        atomic_write_json(ctx.paths.state, state)
        return {
            "schema_version": 1,
            "stage": STAGE,
            "phase": "offline_restart_task_clock_probe_audit",
            "offline_probe_audit": dict(offline),
            "real_tsc_executed": False,
            "finished": False,
            "primary_pass": False,
        }
    results = _evaluate_control(
        ctx, specs, backend=backend, resume=resume
    )
    control_summary = summarize_control(
        ctx, results, selected_pairs
    )
    return analyze(ctx, control_summary)


def self_test() -> dict[str, Any]:
    nominal = np.asarray(
        [[float(index), 0.0, 100.0 * index] for index in range(35)],
        dtype=float,
    )
    selected = select_visible_reference_phase(
        nominal,
        [12.1, 0.0, 1210.0],
        candidate_min_phase=0,
        candidate_max_phase=20,
        scales=[1.0, 1.0, 100.0],
    )
    tie_nominal = np.zeros((35, 3), dtype=float)
    tied = select_visible_reference_phase(
        tie_nominal,
        [0.0, 0.0, 0.0],
        candidate_min_phase=0,
        candidate_max_phase=20,
        scales=[0.03, 0.03, 2000.0],
    )
    classifications = {
        "both_pass": classify_pair_assessment(True, True),
        "sensitive": classify_pair_assessment(True, False),
        "masked": classify_pair_assessment(False, False),
    }
    basis = {
        "mode": 0,
        "effect_offsets": [0, 1, 3, 4],
        "sign_pattern": [1, 1, -1, -1],
    }
    schedule = _probe_schedule(
        first_effect_state=5,
        actual_delay=2,
        basis=basis,
        sign=1,
        amplitude_by_mode=[0.0075, 0.0075, 0.0],
    )
    schedule_net = np.sum(np.stack(list(schedule.values())), axis=0)
    passed = bool(
        selected["selected_phase"] == 12
        and not selected["hidden_wire_used"]
        and not selected["source_action_used"]
        and not selected["source_coil_current_used"]
        and not selected["source_wire_current_used"]
        and not selected["current_run_future_used"]
        and selected["reference_source"]
        == "authenticated_r17_actual_closed_loop_visible_RZI"
        and tied["selected_phase"] == 0
        and classifications["both_pass"]
        == "both_pass_development_pair_success"
        and classifications["sensitive"]
        == "history_sensitive_pass_fail_outcome"
        and classifications["masked"]
        == "masked_by_common_mode_both_fail"
        and sorted(schedule) == [2, 3, 5, 6]
        and np.array_equal(
            schedule_net, np.zeros(N_MODES, dtype=float)
        )
    )
    return {
        "schema_version": 1,
        "stage": STAGE,
        "selected_phase": selected["selected_phase"],
        "earliest_tie_phase": tied["selected_phase"],
        "hidden_wire_used": selected["hidden_wire_used"],
        "source_action_used": selected["source_action_used"],
        "source_coil_current_used": selected[
            "source_coil_current_used"
        ],
        "source_wire_current_used": selected[
            "source_wire_current_used"
        ],
        "current_run_future_used": selected[
            "current_run_future_used"
        ],
        "reference_source": selected["reference_source"],
        "pair_classifications": classifications,
        "probe_issue_steps": sorted(schedule),
        "probe_requested_net": schedule_net.tolist(),
        "identification_only": True,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "formal_timing_unchanged": True,
        "development_set_only": True,
        "bc_dagger_or_rl_allowed": False,
        "passed": passed,
    }


def _set_resource_limits() -> None:
    if resource is None:
        return
    try:
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    except Exception:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Stage4.2R3c3 restart task-clock local-response identification"
        )
    )
    parser.add_argument("--config", type=Path)
    parser.add_argument("--source-stage4-2r3b-run", type=Path)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument(
        "--command", choices=("all", "offline"), default="all"
    )
    parser.add_argument(
        "--backend", choices=("serial", "ray"), default="ray"
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    _set_resource_limits()
    if args.self_test:
        print(json.dumps(self_test(), indent=2, sort_keys=True))
        return
    missing = [
        name
        for name, value in (
            ("--config", args.config),
            ("--source-stage4-2r3b-run", args.source_stage4_2r3b_run),
            ("--run-dir", args.run_dir),
        )
        if value is None
    ]
    if missing:
        parser.error(
            "missing required arguments: " + ", ".join(missing)
        )
    ctx = load_stage42r3c3_config(
        args.config,
        source_stage42r3b_run=args.source_stage4_2r3b_run,
        run_dir_override=args.run_dir,
    )
    result = execute(
        ctx,
        command=args.command,
        backend=args.backend,
        resume=args.resume,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
