"""Stage4.2R3c2 causal restart target-state regulation MPC development.

R3c2 preserves the exact R3c1 phase-zero R17 path.  A nonzero visible
restart phase instead enters the frozen target-error regulation MPC at task
step zero and remains there.  Visible phase still initializes the response
model and delay queue.  Source actions, current-run future values, pair or
history labels, and hidden wire state are never controller inputs.
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
    stage4_2r3c1_authenticated_visible_manifold_phase_mpc as r3c1,
    stage4_2r3b_confirmatory_hidden_history_initial_state as r3b,
)
from tsc_rzip_rllib.utils.ray_runtime import ensure_ray_worker_plan


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c2"
CONTROLLER_REVISION = "restart_target_state_regulation_mpc_v42r3c2"
PACKAGE_REVISION = "r42r3c2_restart_target_state_regulation_mpc_v1"
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
    return "s42r3c2_" + _canonical_digest(dict(value))[:20]


def _formal_horizon(slew: float) -> int:
    return (
        WEAK_HORIZON
        if math.isclose(float(slew), 0.9, abs_tol=1e-12)
        else NORMAL_HORIZON
    )


def _requested_workers(cfg: Mapping[str, Any]) -> int:
    fixed = int(cfg["parallel"]["n_workers"])
    requested = int(os.environ.get("STAGE4_2R3C2_WORKERS", fixed))
    if requested != fixed:
        raise ValueError(
            f"Stage4.2R3c2 Ray capacity is frozen at {fixed}, got {requested}"
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
        raise ValueError("Stage4.2R3c2 config stage mismatch")
    if str(cfg.get("controller_revision")) != CONTROLLER_REVISION:
        raise ValueError("Stage4.2R3c2 controller revision mismatch")
    if str(cfg.get("package_revision")) != PACKAGE_REVISION:
        raise ValueError("Stage4.2R3c2 package revision mismatch")
    if int(cfg["parallel"]["n_workers"]) != 128:
        raise ValueError("Stage4.2R3c2 is fixed to 128 Ray workers")
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
        raise ValueError("Stage4.2R3c2 phase-alignment contract changed")
    expected_regulation = {
        "phase_zero_policy": "preserve_r3c1_path",
        "nonzero_phase_policy": (
            "target_state_regulation_from_task_step_zero"
        ),
        "nonzero_phase_regulation_persistent": True,
        "step_zero_velocity_initialization": "zero",
        "subsequent_velocity_source": (
            "causal_current_run_finite_difference"
        ),
        "model_phase_policy": (
            "min_reference_phase_and_frozen_terminal_cap"
        ),
        "normal_model_phase_cap_source": "terminal_template_step",
        "zero_nominal_physical_coefficients": True,
        "zero_nominal_feature": True,
        "retain_phase_aligned_delay_queue_priming": True,
        "retain_frozen_terminal_gains": True,
        "retain_frozen_weak_probe_schedule": True,
        "pair_or_history_label_input_allowed": False,
        "source_result_input_allowed": False,
    }
    if dict(cfg["restart_regulation"]) != expected_regulation:
        raise ValueError("Stage4.2R3c2 restart-regulation contract changed")
    matrix = cfg["control_matrix"]
    if list(map(str, matrix["targets"])) != [
        "nominal",
        "RZ_p10_m10",
    ]:
        raise ValueError("Stage4.2R3c2 target matrix changed")
    actuator = [
        (
            int(row["actual_delay_steps"]),
            float(row["actual_slew_scale"]),
        )
        for row in matrix["future_actuator_cases"]
    ]
    if actuator != [(0, 1.0), (2, 0.9)]:
        raise ValueError("Stage4.2R3c2 actuator matrix changed")
    if (
        list(map(str, matrix["history_members"]))
        != ["plus_first", "minus_first"]
        or int(matrix["expected_rollouts_per_selected_pair"]) != 8
        or int(matrix["expected_selected_pairs"]) != 4
        or int(matrix["expected_rollouts"]) != 32
        or not bool(matrix["require_fresh_controller"])
        or not bool(matrix["require_fresh_tsc_process"])
        or not bool(matrix["forbid_future_actions"])
        or not bool(matrix["forbid_future_measurements"])
        or not bool(matrix["require_online_action_computation"])
    ):
        raise ValueError("Stage4.2R3c2 control coverage changed")
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
        raise ValueError("Stage4.2R3c2 formal timing changed")
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
        raise ValueError("Stage4.2R3c2 R3b source contract changed")
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
        raise ValueError("Stage4.2R3c2 R3c evidence contract changed")
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
        raise ValueError("Stage4.2R3c2 R3c1 evidence contract changed")
    expected_ids = [
        "p5_q1_a0p900_gap2_settle4",
        "p5_q2_a0p900_gap2_settle4",
        "p9_q1_a0p750_gap2_settle4",
        "p9_q2_a0p750_gap2_settle4",
    ]
    if list(map(str, requirements["required_selected_pair_ids"])) != expected_ids:
        raise ValueError("Stage4.2R3c2 selected pair identities changed")
    if (
        not bool(cfg.get("development_set_only"))
        or bool(cfg.get("independent_hidden_history_confirmation"))
        or bool(cfg.get("bc_dagger_or_rl_allowed"))
    ):
        raise ValueError("Stage4.2R3c2 scientific scope changed")


@dataclass(frozen=True)
class Stage42R3C2Paths:
    run_dir: Path
    source_reference: Path
    variants: Path
    control: Path
    analysis: Path
    state: Path
    manifest: Path

    @classmethod
    def from_run_dir(cls, run_dir: Path) -> "Stage42R3C2Paths":
        root = run_dir.expanduser().resolve()
        return cls(
            run_dir=root,
            source_reference=root / "stage4_2r3c2_source_reference",
            variants=root / "stage4_2r3c2_environment_variants",
            control=(
                root
                / "stage4_2r3c2_restart_target_state_regulation_control"
            ),
            analysis=root / "stage4_2r3c2_analysis",
            state=root / "stage4_2r3c2_state.json",
            manifest=root / "stage4_2r3c2_manifest.json",
        )


@dataclass
class Stage42R3C2Context:
    cfg: dict[str, Any]
    paths: Stage42R3C2Paths
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
                f"Stage4.2R3c2 source evidence missing: {name}: {path}"
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
        raise ValueError("Stage4.2R3c2 source R3b scientific state mismatch")
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
        raise ValueError("Stage4.2R3c2 source R3b audit/inventory mismatch")
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
        "contract": "r42r3c2_exact_r3b_development_source_v1",
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
                f"Stage4.2R3c2 R3c evidence missing: {name}: {path}"
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
        raise ValueError("Stage4.2R3c2 R3c scientific state mismatch")
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
        raise ValueError("Stage4.2R3c2 R3c audit/inventory mismatch")
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
        "contract": "r42r3c2_exact_failed_r3c_evidence_v1",
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
                f"Stage4.2R3c2 R3c1 evidence missing: {name}: {path}"
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
        raise ValueError("Stage4.2R3c2 R3c1 scientific state mismatch")
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
        raise ValueError("Stage4.2R3c2 R3c1 audit/inventory mismatch")
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
        "contract": "r42r3c2_exact_failed_r3c1_evidence_v1",
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


def load_stage42r3c2_config(
    config_path: Path,
    *,
    source_stage42r3b_run: Path,
    run_dir_override: Path | None = None,
) -> Stage42R3C2Context:
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
    return Stage42R3C2Context(
        cfg=cfg,
        paths=Stage42R3C2Paths.from_run_dir(run_dir),
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
    )


def _recompute_selected_pairs(
    ctx: Stage42R3C2Context,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    raw_paths = sorted(
        (ctx.source_ctx.paths.state_generation / "raw").glob("*.json.gz")
    )
    if len(raw_paths) != int(
        ctx.cfg["source_requirements"]["required_state_raw_count"]
    ):
        raise ValueError("Stage4.2R3c2 source state raw count mismatch")
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
            f"Stage4.2R3c2 raw-recomputed selected pair mismatch: {actual_ids}"
        )
    for pair in selected:
        for member in ("plus_first", "minus_first"):
            state = pair[f"{member}_state"]
            if not _selected_snapshot_state_is_valid(state):
                raise ValueError(
                    "Stage4.2R3c2 selected source snapshot is invalid"
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
    ctx: Stage42R3C2Context,
) -> dict[str, Any]:
    relative_paths = [
        "PACKAGE_MANIFEST.json",
        "SHA256SUMS",
        "configs/stage4_2r3c2_restart_target_state_regulation_mpc_370ms.json",
        "run_stage4_2r3c2_restart_target_state_regulation_mpc_native.sh",
        "run_stage4_2r3c2_restart_target_state_regulation_mpc_nohup.sh",
        "run_stage4_2r3c2_self_test.sh",
        "run_stage4_2r3c2_server_postprocess.sh",
        "run_stage4_2r3c2_verify_package.sh",
        "run_stop_stage4_2r3c2_now.sh",
        "scripts/stage4_2r3c2_shell_common.sh",
        "scripts/stage4_2r3c2_restart_target_state_regulation_mpc.py",
        "scripts/stage4_2r3c2_server_postprocess.py",
        "tsc_rzip_rllib/diagnostics/stage4_2r3c2_restart_target_state_regulation_mpc.py",
    ]
    rows = []
    for relative in relative_paths:
        path = ctx.project_dir / relative
        if not path.is_file():
            raise FileNotFoundError(
                f"Stage4.2R3c2 package file missing: {relative}"
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
        "contract": "r42r3c2_deployed_package_source_v1",
        "n_files": len(rows),
        "digest": _canonical_digest(rows),
        "files": rows,
    }


def _semantics_preserving_resume_compatibility(
    ctx: Stage42R3C2Context,
    original: Mapping[str, Any],
    active: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Require the exact R3c2 package for every resume."""

    if dict(original) == dict(active):
        return None
    raise ValueError(
        "Stage4.2R3c2 deployed package fingerprint changed; "
        "in-place resume is forbidden"
    )


def _source_controller_cases(
    ctx: Stage42R3C2Context,
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
        raise ValueError("Stage4.2R3c2 frozen controller source mismatch")
    return sources


def _source_raw_files_by_experiment_id(
    ctx: Stage42R3C2Context,
) -> dict[str, Path]:
    paths = r1._selected_source_files(ctx.source_ctx.r1_ctx)
    output: dict[str, Path] = {}
    for path in paths:
        result = read_json_gz(path)
        experiment_id = str(result.get("experiment_id", ""))
        if not experiment_id or experiment_id in output:
            raise ValueError(
                "Stage4.2R3c2 invalid or duplicate R17 source raw identity"
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
        raise ValueError("Stage4.2R3c2 R17 visible manifold is too short")
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
        raise ValueError("Stage4.2R3c2 R17 visible manifold is invalid")
    experiment_id = str(source.get("experiment_id", ""))
    raw_result = read_json_gz(source_raw_path)
    if (
        not experiment_id
        or str(raw_result.get("experiment_id", "")) != experiment_id
        or list(raw_result.get("trajectory") or [])[:21]
        != trajectory[:21]
    ):
        raise ValueError(
            "Stage4.2R3c2 R17 visible manifold/raw authentication failed"
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
        raise ValueError("Stage4.2R3c2 visible manifold schema changed")
    return manifold


def _visible_reference_manifolds(
    ctx: Stage42R3C2Context,
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
                "Stage4.2R3c2 selected R17 raw source missing: "
                f"{experiment_id}"
            )
        output[key] = _visible_reference_manifold(source, path)
    if set(output) != set(sources):
        raise ValueError(
            "Stage4.2R3c2 visible manifold source coverage mismatch"
        )
    return output


def build_control_specs(
    ctx: Stage42R3C2Context,
    selected_pairs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    sources = _source_controller_cases(ctx)
    manifolds = _visible_reference_manifolds(ctx, sources)
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
                    spec = copy.deepcopy(source["spec"])
                    if r3b._forbidden_future_paths(spec):
                        raise ValueError(
                            "Stage4.2R3c2 source spec contains future data"
                        )
                    identity = {
                        "stage": STAGE,
                        "phase": (
                            "restart_target_state_regulation_"
                            "development_control"
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
                        "controller_revision": CONTROLLER_REVISION,
                        "phase_alignment": ctx.cfg["phase_alignment"],
                        "restart_regulation": (
                            ctx.cfg["restart_regulation"]
                        ),
                        "visible_reference_manifold_digest": (
                            manifold["values_digest"]
                        ),
                    }
                    experiment_id = _scenario_digest(identity)
                    spec.update(
                        {
                            "kind": (
                                "stage4_2r3c2_restart_target_state_"
                                "regulation_development_control"
                            ),
                            "stage": STAGE,
                            "controller_revision": CONTROLLER_REVISION,
                            "underlying_controller_revision": str(
                                source.get("controller_revision", "")
                            ),
                            "experiment_id": experiment_id,
                            "phase": (
                                "restart_target_state_regulation_"
                                "development_control"
                            ),
                            "category": (
                                "restart_target_state_regulation_"
                                "development_control"
                            ),
                            "pair_id": str(pair["pair_id"]),
                            "history_member": str(member),
                            "state_generation_experiment_id": str(
                                state["experiment_id"]
                            ),
                            "restart_snapshot_dir": str(snapshot_dir),
                            "restart_snapshot_manifest_digest": snapshot_digest,
                            "environment_variant": (
                                f"stage4_2r3c2_{experiment_id}"
                            ),
                            "horizon_steps": _formal_horizon(slew),
                            "phase_alignment": copy.deepcopy(
                                ctx.cfg["phase_alignment"]
                            ),
                            "restart_regulation": copy.deepcopy(
                                ctx.cfg["restart_regulation"]
                            ),
                            "visible_reference_manifold": copy.deepcopy(
                                manifold
                            ),
                            "visible_reference_manifold_digest": str(
                                manifold["values_digest"]
                            ),
                            "visible_reference_manifold_source": (
                                "authenticated_R17_actual_closed_loop_RZI"
                            ),
                            "source_action_available_to_controller": False,
                            "source_coil_current_available_to_controller": (
                                False
                            ),
                            "source_wire_current_available_to_controller": (
                                False
                            ),
                            "fresh_controller_required": True,
                            "fresh_tsc_process_required": True,
                            "controller_history_initialization": (
                                "current_visible_state_only_at_task_step_zero"
                            ),
                            "controller_integral_initialization": "zero",
                            "restart_regulation_initialization": (
                                "nonzero_visible_phase_from_task_step_zero"
                            ),
                            "pair_or_history_label_available_to_controller": (
                                False
                            ),
                            "source_result_available_to_controller": False,
                            "hidden_wire_current_available_to_controller": False,
                            "full_wire_current_recorded_after_action_choice": True,
                            "future_action_count": 0,
                            "future_measurement_count": 0,
                            "online_action_computation_required": True,
                            "task_clock_starts_at_zero": True,
                            "formal_timing_unchanged": True,
                            "development_set_only": True,
                        }
                    )
                    spec.setdefault(
                        "terminal_model_phase_cap_step",
                        int(spec.get("terminal_template_step", 28)),
                    )
                    specs.append(spec)
    expected = int(ctx.cfg["control_matrix"]["expected_rollouts"])
    if (
        len(specs) != expected
        or len({str(spec["experiment_id"]) for spec in specs}) != expected
    ):
        raise ValueError("Stage4.2R3c2 control coverage mismatch")
    return specs


def _control_payload(
    ctx: Stage42R3C2Context,
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
                "STAGE4_2R3C2_TSC_WORKSPACE_ROOT",
                storage["tsc_workspace_root"],
            )
        )
        .expanduser()
        .resolve()
    )
    env_cfg["run_root"] = str(
        Path(
            os.environ.get(
                "STAGE4_2R3C2_TSC_RUN_ROOT", storage["tsc_run_root"]
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
    payload["variant_id"] = f"stage4_2r3c2_{experiment_id}"
    payload["start_folder"] = snapshot_dir.name
    payload["slew_scale"] = slew
    payload["stage4_1r4_horizon_steps"] = horizon
    payload["stage4_2r3c2_restart_snapshot_dir"] = str(snapshot_dir)
    payload["stage4_2r3c2_snapshot_manifest_digest"] = str(
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


class RestartTargetStateRegulationTaskController(r3b.FreshTaskController):
    """Preserve phase zero; regulate target state for nonzero restarts."""

    def __init__(
        self,
        base_worker: Any,
        bundle: Mapping[str, Any],
        source_spec: Mapping[str, Any],
        initial_state: Mapping[str, Any],
    ):
        super().__init__(base_worker, bundle, source_spec, initial_state)
        phase_cfg = source_spec["phase_alignment"]
        manifold = dict(source_spec["visible_reference_manifold"])
        reference_rzi = np.asarray(manifold.get("values"), dtype=float)
        if (
            str(manifold.get("contract"))
            != "authenticated_r17_actual_closed_loop_visible_RZI_v1"
            or list(manifold.get("visible_fields") or [])
            != ["R", "Z", "Ip"]
            or int(manifold.get("phase_min", -1)) != 0
            or int(manifold.get("phase_max", -1)) != 20
            or int(manifold.get("phase_count", -1)) != 21
            or not str(manifold.get("source_experiment_id", ""))
            or len(str(manifold.get("source_raw_sha256", ""))) != 64
            or int(manifold.get("source_raw_size_bytes", 0)) <= 0
            or reference_rzi.shape != (21, 3)
            or not np.all(np.isfinite(reference_rzi))
            or str(manifold.get("values_digest", ""))
            != _canonical_digest(reference_rzi.tolist())
            or bool(manifold.get("source_actions_included"))
            or bool(manifold.get("source_coil_currents_included"))
            or bool(manifold.get("source_wire_currents_included"))
            or bool(manifold.get("current_run_future_included"))
        ):
            raise ValueError(
                "Stage4.2R3c2 visible reference manifold contract invalid"
            )
        selection = select_visible_reference_phase(
            reference_rzi,
            [
                float(initial_state["R"]),
                float(initial_state["Z"]),
                float(initial_state["Ip"]),
            ],
            candidate_min_phase=int(phase_cfg["candidate_min_phase"]),
            candidate_max_phase=int(phase_cfg["candidate_max_phase"]),
            scales=[
                float(phase_cfg["R_scale_m"]),
                float(phase_cfg["Z_scale_m"]),
                float(phase_cfg["Ip_scale_A"]),
            ],
        )
        self.phase_selection = selection
        self.visible_reference_manifold_digest = str(
            manifold["values_digest"]
        )
        self.visible_reference_source_experiment_id = str(
            manifold["source_experiment_id"]
        )
        self.reference_phase_start = int(selection["selected_phase"])
        self.restart_regulation_enabled = bool(
            self.reference_phase_start > 0
        )
        cap_value = self.spec.get(
            "terminal_model_phase_cap_step",
            self.spec.get("terminal_template_step"),
        )
        if cap_value is None:
            raise ValueError(
                "restart regulation requires a frozen terminal model phase"
            )
        self.restart_regulation_model_phase_cap = int(cap_value)
        source_transition = self.transition_step
        self.source_transition_phase = source_transition
        self.transition_step = (
            None
            if source_transition is None
            else max(0, int(source_transition) - self.reference_phase_start)
        )
        self.terminal_transition_step = max(
            0, 35 - self.reference_phase_start
        )
        aligned_nominal = np.asarray(
            [
                self.nominal_physical[
                    min(self.reference_phase_start + index, 34)
                ]
                for index in range(35)
            ],
            dtype=float,
        )
        initial_currents = np.asarray(
            initial_state["currents_a_tsc"], dtype=float
        ).reshape(N_COILS)
        nominal_commands, _ = self.base._nominal_command_plan(
            aligned_nominal,
            initial_currents,
            self.controller_gain,
            self.slew,
            True,
        )
        prime_default = bool(
            self.base.robust_cfg["controller_upgrade"]["delay_aware"].get(
                "prime_action_queue_with_nominal", True
            )
        )
        prime_queue = bool(
            self.spec.get("prime_action_queue_with_nominal", prime_default)
        )
        self.queue = []
        for index in range(self.actual_delay):
            model_phase = min(self.reference_phase_start + index, 34)
            command = (
                np.asarray(nominal_commands[index], dtype=float).reshape(
                    N_MODES
                )
                if prime_queue
                else np.zeros(N_MODES, dtype=float)
            )
            desired = (
                self.nominal_physical[model_phase].copy()
                if prime_queue
                else np.zeros(N_MODES, dtype=float)
            )
            self.queue.append(
                {
                    "origin": "phase_aligned_prime",
                    "origin_index": -self.actual_delay + index,
                    "command": command,
                    "desired_physical": desired,
                    "reference_phase": model_phase,
                }
            )

    def reference_phase(self) -> int:
        """Return the monotonic reference clock, including its terminal tail."""

        return self.reference_phase_start + self.step

    def model_phase(self) -> int:
        """Return the bounded phase used by finite R17 arrays."""

        return min(self.reference_phase(), 34)

    def _main_action(
        self, currents: np.ndarray
    ) -> tuple[np.ndarray, dict[str, Any]]:
        task_step = self.step
        reference_phase = self.reference_phase()
        model_phase = self.model_phase()
        history_values = [
            np.asarray([row["R"], row["Z"], row["Ip"]], dtype=float)
            for row in self.history
        ]
        measurement_physical = r2.r3.legacy_measurement_error(
            history_values,
            delayed_local_index=len(history_values) - 1,
            delayed_absolute_index=model_phase,
            current_absolute_index=model_phase,
            nominal_y=self.nominal_y,
            nominal_velocity=self.nominal_velocity,
            dt_s=self.dt_s,
        )
        measurement = measurement_physical / self.measurement_scales
        integral_candidate = self.base._integral_candidate(
            self.integral,
            measurement,
            reference_step=model_phase,
            anti_windup_enabled=False,
        )
        pending = [
            np.asarray(item["desired_physical"], dtype=float)
            for item in self.queue[: self.delay]
        ]
        solve = r2.r3.solve_delay_aware_physical_correction(
            self.base.stub,
            self.bundle,
            current_step=model_phase,
            modeled_action_delay_steps=self.delay,
            modeled_pending_physical_coefficients=pending,
            nominal_physical_coefficients=self.nominal_physical,
            nominal_feature=self.nominal_feature,
            measurement_normalized=measurement,
            integral_normalized=integral_candidate,
            previous_correction=self.previous,
            controller_scale=float(self.spec["controller_scale"]),
            controller_model_scale=float(
                self.spec.get("controller_model_scale", 1.0)
            ),
        )
        correction = np.asarray(
            solve["first_correction"], dtype=float
        ).reshape(N_MODES)
        self.integral = integral_candidate
        effect_phase = min(
            int(solve.get("effect_step", model_phase)), 34
        )
        desired = np.clip(
            self.nominal_physical[effect_phase] + correction,
            self.base.lower_mode,
            self.base.upper_mode,
        )
        scheduled = self.base.scheduler.solve_command(
            desired,
            currents,
            self.controller_gain,
            self.slew,
            enabled=True,
        )
        issued = np.asarray(
            scheduled["command"], dtype=float
        ).reshape(N_MODES)
        issued_item = {
            "origin": "phase_aligned_main_control",
            "origin_index": task_step,
            "reference_phase": reference_phase,
            "model_phase": model_phase,
            "command": issued,
            "desired_physical": desired,
        }
        applied, self.queue = r2.r9._stream_queue_apply(
            self.queue, issued_item, self.actual_delay
        )
        effective = (
            self.actual_gain
            * np.asarray(applied["command"], dtype=float)
            + self.actuator_bias
        )
        action = self.base._mode_action(effective, currents)
        trace = {
            "step": task_step,
            "task_step": task_step,
            "reference_phase": reference_phase,
            "model_phase": model_phase,
            "reference_phase_start": self.reference_phase_start,
            "controller_phase": "phase_aligned_main_control",
            "visible_reference_manifold_digest": (
                self.visible_reference_manifold_digest
            ),
            "visible_reference_source_experiment_id": (
                self.visible_reference_source_experiment_id
            ),
            "source_action_used": False,
            "source_coil_current_used": False,
            "source_wire_current_used": False,
            "current_run_future_used": False,
            "computed_online": True,
            "measurement_max_state_index_used": task_step,
            "future_measurement_used": False,
            "hidden_wire_used": False,
            "measurement_physical": measurement_physical.tolist(),
            "measurement_normalized": measurement.tolist(),
            "integral_normalized": self.integral.tolist(),
            "previous_correction_physical": self.previous.tolist(),
            "mode_correction_physical": correction.tolist(),
            "issued_desired_physical_mode_coefficients": desired.tolist(),
            "issued_mode_coefficients": issued.tolist(),
            "applied_command_mode_coefficients": np.asarray(
                applied["command"], dtype=float
            ).tolist(),
            "queue_after": r2.r9._queue_origins(self.queue),
            "action_norm_tsc": np.asarray(action, dtype=float).tolist(),
            "solver_success": bool(solve.get("solver_success")),
        }
        self.previous = correction
        return action, trace

    def _damping_action(
        self, currents: np.ndarray
    ) -> tuple[np.ndarray, dict[str, Any]]:
        task_step = self.step
        reference_phase = self.reference_phase()
        measurement_physical = _fresh_task_terminal_measurement(
            self.history, self.target, self.dt_s
        )
        normalized, for_solver = r2.r12._measurement_for_solver(
            measurement_physical,
            self.measurement_scales,
            position_gain=float(
                self.spec["terminal_position_measurement_gain"]
            ),
            velocity_gain=float(
                self.spec["terminal_velocity_measurement_gain"]
            ),
            ip_gain=float(
                self.spec.get("terminal_ip_measurement_gain", 1.0)
            ),
        )
        pending = [
            np.asarray(item["desired_physical"], dtype=float)
            for item in self.queue[: self.delay]
        ]
        solver_phase = min(
            reference_phase,
            self.restart_regulation_model_phase_cap,
        )
        solve = r2.r3.solve_delay_aware_physical_correction(
            self.base.stub,
            self.bundle,
            current_step=solver_phase,
            modeled_action_delay_steps=self.delay,
            modeled_pending_physical_coefficients=pending,
            nominal_physical_coefficients=np.zeros(
                (35, N_MODES), dtype=float
            ),
            nominal_feature=np.zeros(35 * 5, dtype=float),
            measurement_normalized=for_solver,
            integral_normalized=self.damping_integral,
            previous_correction=self.previous,
            controller_scale=float(self.spec["terminal_controller_scale"]),
            controller_model_scale=float(
                self.spec.get("terminal_controller_model_scale", 1.0)
            ),
        )
        correction = np.asarray(
            solve["first_correction"], dtype=float
        ).reshape(N_MODES)
        schedule = {
            int(issue_step): np.asarray(value, dtype=float).reshape(N_MODES)
            for issue_step, value in (
                self.spec.get("r15_probe_delta_by_issue_step") or {}
            ).items()
        }
        requested_probe = schedule.get(
            solver_phase, np.zeros(N_MODES, dtype=float)
        )
        baseline_correction = correction.copy()
        correction = np.clip(
            correction + requested_probe,
            self.base.lower_mode,
            self.base.upper_mode,
        )
        applied_probe = correction - baseline_correction
        desired = np.clip(
            correction, self.base.lower_mode, self.base.upper_mode
        )
        scheduled = self.base.scheduler.solve_command(
            desired,
            currents,
            self.controller_gain,
            self.slew,
            enabled=True,
        )
        issued = np.asarray(
            scheduled["command"], dtype=float
        ).reshape(N_MODES)
        phase_name = (
            "restart_target_state_regulation"
            if self.restart_regulation_enabled
            else "phase_aligned_anticipatory_damping"
        )
        issued_item = {
            "origin": phase_name,
            "origin_index": task_step,
            "reference_phase": reference_phase,
            "model_phase": solver_phase,
            "command": issued,
            "desired_physical": desired,
        }
        applied, self.queue = r2.r9._stream_queue_apply(
            self.queue, issued_item, self.actual_delay
        )
        effective = (
            self.actual_gain
            * np.asarray(applied["command"], dtype=float)
            + self.actuator_bias
        )
        action = self.base._mode_action(effective, currents)
        trace = {
            "step": task_step,
            "task_step": task_step,
            "reference_phase": reference_phase,
            "model_phase": solver_phase,
            "reference_phase_start": self.reference_phase_start,
            "controller_phase": phase_name,
            "restart_regulation_enabled": (
                self.restart_regulation_enabled
            ),
            "restart_regulation_persistent": bool(
                self.restart_regulation_enabled
            ),
            "step_zero_velocity_initialized_to_zero": bool(
                task_step == 0
            ),
            "velocity_source": (
                "zero_at_unavailable_first_sample"
                if task_step == 0
                else "causal_current_run_finite_difference"
            ),
            "pair_or_history_label_used": False,
            "source_result_used": False,
            "visible_reference_manifold_digest": (
                self.visible_reference_manifold_digest
            ),
            "visible_reference_source_experiment_id": (
                self.visible_reference_source_experiment_id
            ),
            "source_action_used": False,
            "source_coil_current_used": False,
            "source_wire_current_used": False,
            "current_run_future_used": False,
            "computed_online": True,
            "measurement_max_state_index_used": task_step,
            "future_measurement_used": False,
            "hidden_wire_used": False,
            "measurement_physical": measurement_physical.tolist(),
            "measurement_normalized": normalized.tolist(),
            "measurement_for_solver": for_solver.tolist(),
            "integral_normalized": self.damping_integral.tolist(),
            "previous_correction_physical": self.previous.tolist(),
            "mode_correction_physical": correction.tolist(),
            "baseline_mode_correction_physical": (
                baseline_correction.tolist()
            ),
            "r15_probe_requested_delta": requested_probe.tolist(),
            "r15_probe_applied_delta": applied_probe.tolist(),
            "r15_identification_probe": bool(
                np.any(requested_probe != 0.0)
            ),
            "issued_desired_physical_mode_coefficients": desired.tolist(),
            "issued_mode_coefficients": issued.tolist(),
            "applied_command_mode_coefficients": np.asarray(
                applied["command"], dtype=float
            ).tolist(),
            "queue_after": r2.r9._queue_origins(self.queue),
            "action_norm_tsc": np.asarray(action, dtype=float).tolist(),
            "solver_success": bool(solve.get("solver_success")),
        }
        self.previous = desired
        return action, trace

    def action(
        self, current_state: Mapping[str, Any]
    ) -> tuple[np.ndarray, dict[str, Any]]:
        if int(current_state["step_index"]) != self.step:
            raise ValueError("controller/current task-state index mismatch")
        currents = np.asarray(
            current_state["currents_a_tsc"], dtype=float
        ).reshape(N_COILS)
        if self.restart_regulation_enabled:
            self.phase = "restart_target_state_regulation"
            return self._damping_action(currents)
        if (
            self.transition_step is not None
            and self.step >= self.transition_step
        ):
            self.phase = "anticipatory_damping"
        elif self.step >= self.terminal_transition_step:
            self.phase = "terminal_feedback"
        if self.phase == "main_control":
            return self._main_action(currents)
        if self.phase == "anticipatory_damping":
            return self._damping_action(currents)
        if self.phase == "terminal_feedback":
            action, trace = super()._terminal_action(currents)
            trace.update(
                {
                    "task_step": self.step,
                    "reference_phase": self.reference_phase(),
                    "model_phase": int(
                        self.spec["terminal_template_step"]
                    ),
                    "reference_phase_start": self.reference_phase_start,
                    "controller_phase": (
                        "phase_aligned_terminal_feedback"
                    ),
                    "visible_reference_manifold_digest": (
                        self.visible_reference_manifold_digest
                    ),
                    "visible_reference_source_experiment_id": (
                        self.visible_reference_source_experiment_id
                    ),
                    "source_action_used": False,
                    "source_coil_current_used": False,
                    "source_wire_current_used": False,
                    "current_run_future_used": False,
                    "hidden_wire_used": False,
                }
            )
            return action, trace
        raise ValueError(
            f"unsupported phase-aligned controller phase: {self.phase}"
        )


class LocalRestartTargetStateRegulationControlWorker:
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
            "underlying_controller_revision": r1.r17.CONTROLLER_REVISION,
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
                raise ValueError("Stage4.2R3c2 formal horizon changed")
            self.base.env.reset()
            zero_action = np.zeros(N_COILS, dtype=np.float32)
            initial = r1._state_record_full(
                self.base.env, 0, zero_action
            )
            trajectory = [initial]
            controller = RestartTargetStateRegulationTaskController(
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
            )
            result.update(
                {
                    "success": success,
                    "completed": True,
                    "failure_reason": (
                        ""
                        if success
                        else "incomplete restart-regulation control rollout"
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
                        "restart_regulation_enabled": (
                            controller.restart_regulation_enabled
                        ),
                        "restart_regulation_model_phase_cap": (
                            controller.restart_regulation_model_phase_cap
                        ),
                        "restart_regulation_policy": (
                            "nonzero_visible_phase_target_state_"
                            "regulation_from_task_step_zero"
                        ),
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
                        "stage4_2r3c2_restart_target_state_"
                        "regulation_control"
                    ),
                )


_CONTROL_RAY_ACTOR = None


def _control_ray_actor_class():
    global _CONTROL_RAY_ACTOR
    if _CONTROL_RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class Stage42R3C2ControlActor:
            def __init__(
                self, payload, library, bundle, worker_id, selector_cfg
            ):
                self.worker = LocalRestartTargetStateRegulationControlWorker(
                    payload, library, bundle, worker_id, selector_cfg
                )

            def evaluate(self, spec):
                return self.worker.evaluate(spec)

            def close(self):
                self.worker.close()
                return True

        _CONTROL_RAY_ACTOR = Stage42R3C2ControlActor
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
    ctx: Stage42R3C2Context,
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
            worker = LocalRestartTargetStateRegulationControlWorker(
                payloads[str(spec["experiment_id"])],
                library,
                bundle,
                f"stage42r3c2_control_serial_{index:03d}",
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
                f"[Stage4.2R3c2 control] {index + 1}/{len(pending)}",
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
            log_prefix="[Stage4.2R3c2 control]",
        )
        Actor = _control_ray_actor_class()
        actors = []
        refs = {}
        for index, spec in enumerate(pending):
            actor = Actor.remote(
                payloads[str(spec["experiment_id"])],
                library,
                bundle,
                f"stage42r3c2_control_{index:03d}",
                selector,
            )
            actors.append(actor)
            refs[actor.evaluate.remote(spec)] = spec
        print(
            "[Stage4.2R3c2 control] "
            f"actor_count={plan.actor_count} pending={len(pending)}",
            flush=True,
        )
        completed = 0
        try:
            while refs:
                ready, _ = ray.wait(
                    list(refs), num_returns=1, timeout=30.0
                )
                if not ready:
                    print(
                        "[Stage4.2R3c2 control] "
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
                        raw_dir / f"{spec['experiment_id']}.json.gz",
                        result,
                    )
                    completed += 1
                    if completed % 8 == 0 or not refs:
                        print(
                            "[Stage4.2R3c2 control] "
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
    trace = list(result.get("controller_trace") or [])
    if not trace:
        return {
            "passed": False,
            "reference_phase_start": None,
            "task_clock_starts_at_zero": False,
            "reference_phase_monotonic": False,
            "reference_phase_exact": False,
            "model_phase_exact": False,
            "hidden_wire_trace_count": 0,
            "source_action_trace_count": 0,
            "source_coil_current_trace_count": 0,
            "source_wire_current_trace_count": 0,
            "current_run_future_trace_count": 0,
            "visible_reference_manifold_exact": False,
            "restart_regulation_trace_count": 0,
            "pair_or_history_label_trace_count": 0,
            "source_result_trace_count": 0,
        }
    starts = {
        int(row["reference_phase_start"]) for row in trace
    }
    start = next(iter(starts)) if len(starts) == 1 else None
    task = [int(row["task_step"]) for row in trace]
    phase = [int(row["reference_phase"]) for row in trace]
    model = [int(row["model_phase"]) for row in trace]
    expected_task = list(range(len(trace)))
    expected_phase = (
        [int(start) + step for step in expected_task]
        if start is not None
        else []
    )
    hidden_count = sum(bool(row.get("hidden_wire_used")) for row in trace)
    spec = result.get("spec") or {}
    source_action_count = sum(
        bool(row.get("source_action_used")) for row in trace
    )
    source_coil_count = sum(
        bool(row.get("source_coil_current_used")) for row in trace
    )
    source_wire_count = sum(
        bool(row.get("source_wire_current_used")) for row in trace
    )
    current_future_count = sum(
        bool(row.get("current_run_future_used")) for row in trace
    )
    pair_or_history_count = sum(
        bool(row.get("pair_or_history_label_used")) for row in trace
    )
    source_result_count = sum(
        bool(row.get("source_result_used")) for row in trace
    )
    restart_regulation_count = sum(
        str(row.get("controller_phase", ""))
        == "restart_target_state_regulation"
        for row in trace
    )
    expected_manifold_digest = str(
        spec.get("visible_reference_manifold_digest", "")
    )
    manifold_exact = bool(
        expected_manifold_digest
        and all(
            str(row.get("visible_reference_manifold_digest", ""))
            == expected_manifold_digest
            for row in trace
        )
    )
    expected_model = []
    for row, reference in zip(trace, phase):
        controller_phase = str(row.get("controller_phase", ""))
        if controller_phase == "phase_aligned_main_control":
            expected_model.append(min(reference, 34))
        elif controller_phase == "phase_aligned_anticipatory_damping":
            expected_model.append(
                min(
                    reference,
                    int(spec["terminal_model_phase_cap_step"]),
                )
            )
        elif controller_phase == "restart_target_state_regulation":
            cap = int(
                spec.get(
                    "terminal_model_phase_cap_step",
                    spec.get("terminal_template_step", 28),
                )
            )
            expected_model.append(min(reference, cap))
        elif controller_phase == "phase_aligned_terminal_feedback":
            expected_model.append(int(spec["terminal_template_step"]))
        else:
            expected_model.append(-1)
    return {
        "passed": bool(
            start is not None
            and task == expected_task
            and phase == expected_phase
            and model == expected_model
            and hidden_count == 0
            and source_action_count == 0
            and source_coil_count == 0
            and source_wire_count == 0
            and current_future_count == 0
            and pair_or_history_count == 0
            and source_result_count == 0
            and manifold_exact
            and (
                (start == 0 and restart_regulation_count == 0)
                or (
                    start is not None
                    and start > 0
                    and restart_regulation_count == len(trace)
                )
            )
        ),
        "reference_phase_start": start,
        "task_clock_starts_at_zero": bool(task and task[0] == 0),
        "reference_phase_monotonic": bool(
            all(right >= left for left, right in zip(phase, phase[1:]))
        ),
        "reference_phase_exact": phase == expected_phase,
        "model_phase_exact": model == expected_model,
        "hidden_wire_trace_count": hidden_count,
        "source_action_trace_count": source_action_count,
        "source_coil_current_trace_count": source_coil_count,
        "source_wire_current_trace_count": source_wire_count,
        "current_run_future_trace_count": current_future_count,
        "visible_reference_manifold_exact": manifold_exact,
        "restart_regulation_trace_count": restart_regulation_count,
        "pair_or_history_label_trace_count": pair_or_history_count,
        "source_result_trace_count": source_result_count,
    }


def summarize_control(
    ctx: Stage42R3C2Context,
    results: Sequence[Mapping[str, Any]],
    selected_pairs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    state_map = r3b._selected_state_map(selected_pairs)
    rows = []
    result_by_id = {}
    for result in results:
        result_by_id[str(result["experiment_id"])] = result
        state_id = str(
            result["spec"]["state_generation_experiment_id"]
        )
        base = r3b._control_row(
            ctx.source_ctx, result, state_map[state_id]
        )
        phase = _phase_trace_valid(result)
        summary = result.get("hidden_history_control_summary") or {}
        row = {
            **base,
            "reference_phase_start": phase["reference_phase_start"],
            "phase_trace_valid": bool(phase["passed"]),
            "task_clock_starts_at_zero": bool(
                phase["task_clock_starts_at_zero"]
            ),
            "reference_phase_monotonic": bool(
                phase["reference_phase_monotonic"]
            ),
            "reference_phase_exact": bool(
                phase["reference_phase_exact"]
            ),
            "model_phase_exact": bool(phase["model_phase_exact"]),
            "phase_hidden_wire_trace_count": int(
                phase["hidden_wire_trace_count"]
            ),
            "phase_source_action_trace_count": int(
                phase["source_action_trace_count"]
            ),
            "phase_source_coil_current_trace_count": int(
                phase["source_coil_current_trace_count"]
            ),
            "phase_source_wire_current_trace_count": int(
                phase["source_wire_current_trace_count"]
            ),
            "phase_current_run_future_trace_count": int(
                phase["current_run_future_trace_count"]
            ),
            "visible_reference_manifold_exact": bool(
                phase["visible_reference_manifold_exact"]
            ),
            "restart_regulation_trace_count": int(
                phase["restart_regulation_trace_count"]
            ),
            "pair_or_history_label_trace_count": int(
                phase["pair_or_history_label_trace_count"]
            ),
            "source_result_trace_count": int(
                phase["source_result_trace_count"]
            ),
            "restart_regulation_enabled": bool(
                summary.get("restart_regulation_enabled", False)
            ),
            "formal_clock_shifted": bool(
                summary.get("formal_clock_shifted", True)
            ),
            "development_set_only": True,
        }
        phase_failure = bool(
            not row["phase_trace_valid"]
            or not row["task_clock_starts_at_zero"]
            or row["formal_clock_shifted"]
        )
        source_data_failure = bool(
            row["phase_source_action_trace_count"]
            or row["phase_source_coil_current_trace_count"]
            or row["phase_source_wire_current_trace_count"]
            or row["phase_current_run_future_trace_count"]
            or row["pair_or_history_label_trace_count"]
            or row["source_result_trace_count"]
            or not row["visible_reference_manifold_exact"]
        )
        row["controller_trace_causal"] = bool(
            row["controller_trace_causal"] and not source_data_failure
        )
        row["phase_selection_or_transition_design_failure"] = (
            phase_failure
        )
        if (
            bool(row["environment_success"])
            and bool(row["initial_restart_exact"])
            and source_data_failure
        ):
            row["failure_class"] = "controller_causality_failure"
        elif (
            bool(row["environment_success"])
            and bool(row["initial_restart_exact"])
            and bool(row["controller_trace_causal"])
            and phase_failure
        ):
            row["failure_class"] = (
                "phase_selection_or_transition_design_failure"
            )
        row["passed"] = bool(
            row["passed"]
            and row["phase_trace_valid"]
            and row["task_clock_starts_at_zero"]
            and not row["formal_clock_shifted"]
        )
        rows.append(row)
    grouped: dict[
        tuple[str, str, int, float], list[dict[str, Any]]
    ] = defaultdict(list)
    for row in rows:
        key = (
            str(row["pair_id"]),
            str(row["target_id"]),
            int(row["actual_delay_steps"]),
            float(row["actual_slew_scale"]),
        )
        grouped[key].append(row)
    pair_rows = []
    for key in sorted(grouped):
        members = grouped[key]
        member_rows = {
            str(row["history_member"]): row for row in members
        }
        member_results = {
            member: result_by_id[str(row["experiment_id"])]
            for member, row in member_rows.items()
        }
        plus_pass = bool(
            member_rows.get("plus_first", {}).get("passed", False)
        )
        minus_pass = bool(
            member_rows.get("minus_first", {}).get("passed", False)
        )
        assessment = classify_pair_assessment(
            plus_pass, minus_pass
        )
        pair_rows.append(
            {
                "pair_id": key[0],
                "target_id": key[1],
                "actual_delay_steps": key[2],
                "actual_slew_scale": key[3],
                "member_count": len(members),
                "plus_first_pass": plus_pass,
                "minus_first_pass": minus_pass,
                "both_members_pass": plus_pass and minus_pass,
                "history_sensitive_outcome": (
                    plus_pass != minus_pass
                ),
                "history_assessment_status": assessment,
                **r3b._control_pair_divergence(
                    member_results.get("plus_first"),
                    member_results.get("minus_first"),
                ),
            }
        )
    expected = int(ctx.cfg["control_matrix"]["expected_rollouts"])
    margins = [
        row
        for row in rows
        if row.get("formal_minimum_signed_margin") is not None
    ]
    minimum = min(
        margins,
        key=lambda row: float(row["formal_minimum_signed_margin"]),
        default={},
    )
    masked = sum(
        row["history_assessment_status"]
        == "masked_by_common_mode_both_fail"
        for row in pair_rows
    )
    sensitive = sum(
        row["history_sensitive_outcome"] for row in pair_rows
    )
    both_pass = sum(row["both_members_pass"] for row in pair_rows)
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "restart_target_state_regulation_development_control",
        "development_set_only": True,
        "independent_hidden_history_confirmation": False,
        "selected_pair_count": len(selected_pairs),
        "expected_rollouts": expected,
        "n_rollouts": len(rows),
        "environment_success_count": sum(
            bool(row["environment_success"]) for row in rows
        ),
        "fresh_controller_fraction": (
            sum(bool(row["fresh_controller"]) for row in rows) / len(rows)
            if rows
            else 0.0
        ),
        "fresh_tsc_process_fraction": (
            sum(bool(row["fresh_tsc_process"]) for row in rows) / len(rows)
            if rows
            else 0.0
        ),
        "initial_restart_exact_fraction": (
            sum(bool(row["initial_restart_exact"]) for row in rows)
            / len(rows)
            if rows
            else 0.0
        ),
        "controller_trace_causal_fraction": (
            sum(bool(row["controller_trace_causal"]) for row in rows)
            / len(rows)
            if rows
            else 0.0
        ),
        "phase_trace_valid_fraction": (
            sum(bool(row["phase_trace_valid"]) for row in rows)
            / len(rows)
            if rows
            else 0.0
        ),
        "model_phase_exact_fraction": (
            sum(bool(row["model_phase_exact"]) for row in rows)
            / len(rows)
            if rows
            else 0.0
        ),
        "formal_clock_shift_count": sum(
            bool(row["formal_clock_shifted"]) for row in rows
        ),
        "future_action_replay_count": sum(
            bool(row.get("future_action_replay_used")) for row in rows
        ),
        "future_measurement_use_count": sum(
            bool(row.get("future_measurement_used")) for row in rows
        ),
        "hidden_wire_controller_input_count": sum(
            bool(row.get("hidden_wire_available_to_controller"))
            for row in rows
        )
        + sum(
            int(row["phase_hidden_wire_trace_count"]) for row in rows
        ),
        "source_action_use_count": sum(
            int(row["phase_source_action_trace_count"]) for row in rows
        ),
        "source_coil_current_use_count": sum(
            int(row["phase_source_coil_current_trace_count"])
            for row in rows
        ),
        "source_wire_current_use_count": sum(
            int(row["phase_source_wire_current_trace_count"])
            for row in rows
        ),
        "current_run_future_use_count": sum(
            int(row["phase_current_run_future_trace_count"])
            for row in rows
        ),
        "pair_or_history_label_use_count": sum(
            int(row["pair_or_history_label_trace_count"])
            for row in rows
        ),
        "source_result_use_count": sum(
            int(row["source_result_trace_count"]) for row in rows
        ),
        "restart_regulation_enabled_fraction": (
            sum(bool(row["restart_regulation_enabled"]) for row in rows)
            / len(rows)
            if rows
            else 0.0
        ),
        "restart_regulation_complete_trace_fraction": (
            sum(
                int(row["restart_regulation_trace_count"])
                == int(row["controller_trace_row_count"])
                for row in rows
            )
            / len(rows)
            if rows
            else 0.0
        ),
        "visible_reference_manifold_exact_fraction": (
            sum(
                bool(row["visible_reference_manifold_exact"])
                for row in rows
            )
            / len(rows)
            if rows
            else 0.0
        ),
        "formal_contract_pass_fraction": (
            sum(bool(row["formal_contract_pass"]) for row in rows)
            / len(rows)
            if rows
            else 0.0
        ),
        "pair_control_group_count": len(pair_rows),
        "pair_both_members_pass_count": both_pass,
        "pair_both_members_pass_fraction": (
            both_pass / len(pair_rows) if pair_rows else 0.0
        ),
        "history_sensitive_outcome_count": sensitive,
        "common_mode_both_fail_masked_group_count": masked,
        "observer_or_history_identification_failure_count": (
            None if masked else sensitive
        ),
        "hidden_history_assessment_inconclusive": bool(masked),
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
        "phase_selection_or_transition_design_failure_count": sum(
            bool(
                row["phase_selection_or_transition_design_failure"]
            )
            for row in rows
        ),
        "real_closed_loop_formal_control_failure_count": sum(
            row["failure_class"]
            == "real_closed_loop_formal_control_failure"
            for row in rows
        ),
        "reference_phase_start_values": sorted(
            {
                int(row["reference_phase_start"])
                for row in rows
                if row["reference_phase_start"] is not None
            }
        ),
        "minimum_formal_signed_margin": minimum.get(
            "formal_minimum_signed_margin"
        ),
        "minimum_margin_case": (
            {
                "pair_id": minimum.get("pair_id"),
                "history_member": minimum.get("history_member"),
                "target_id": minimum.get("target_id"),
                "actual_delay_steps": minimum.get(
                    "actual_delay_steps"
                ),
                "actual_slew_scale": minimum.get(
                    "actual_slew_scale"
                ),
            }
            if minimum
            else None
        ),
    }
    summary["passed"] = bool(
        len(rows) == expected
        and summary["environment_success_count"] == expected
        and summary["fresh_controller_fraction"] == 1.0
        and summary["fresh_tsc_process_fraction"] == 1.0
        and summary["initial_restart_exact_fraction"] == 1.0
        and summary["controller_trace_causal_fraction"] == 1.0
        and summary["phase_trace_valid_fraction"] == 1.0
        and summary["model_phase_exact_fraction"] == 1.0
        and summary["formal_clock_shift_count"] == 0
        and summary["future_action_replay_count"] == 0
        and summary["future_measurement_use_count"] == 0
        and summary["hidden_wire_controller_input_count"] == 0
        and summary["source_action_use_count"] == 0
        and summary["source_coil_current_use_count"] == 0
        and summary["source_wire_current_use_count"] == 0
        and summary["current_run_future_use_count"] == 0
        and summary["pair_or_history_label_use_count"] == 0
        and summary["source_result_use_count"] == 0
        and summary["restart_regulation_enabled_fraction"] == 1.0
        and summary["restart_regulation_complete_trace_fraction"] == 1.0
        and summary["visible_reference_manifold_exact_fraction"] == 1.0
        and summary["formal_contract_pass_fraction"] == 1.0
        and summary["pair_both_members_pass_fraction"] == 1.0
        and masked == 0
    )
    atomic_write_json(ctx.paths.control / "results.json", rows)
    write_csv(ctx.paths.control / "results.csv", rows)
    atomic_write_json(ctx.paths.control / "pair_results.json", pair_rows)
    write_csv(ctx.paths.control / "pair_results.csv", pair_rows)
    atomic_write_json(ctx.paths.control / "summary.json", summary)
    return summary


def _prepare_dirs(paths: Stage42R3C2Paths) -> None:
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
    ctx: Stage42R3C2Context,
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
            "Stage4.2R3c2 requires four authenticated visible manifolds"
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
        "restart_regulation": copy.deepcopy(
            ctx.cfg["restart_regulation"]
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
                "Stage4.2R3c2 run exists; use --resume or a fresh run"
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
            "config_digest",
            "selected_snapshot_source_digest",
            "control_spec_digest",
            "visible_reference_manifold_digest",
            "phase_alignment",
            "restart_regulation",
            "formal_timing_contract",
            "control_matrix",
        ):
            if old.get(key) != manifest.get(key):
                raise ValueError(
                    "Stage4.2R3c2 resume incompatibility in "
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
        ctx.paths.run_dir / "stage4_2r3c2_config.resolved.json",
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


def run_offline_restart_regulation_audit(
    ctx: Stage42R3C2Context,
    selected_pairs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    sources = _source_controller_cases(ctx)
    manifolds = _visible_reference_manifolds(ctx, sources)
    built_specs = build_control_specs(ctx, selected_pairs)
    development_spec_by_key = {
        (
            str(spec["pair_id"]),
            str(spec["history_member"]),
            str(spec["target_id"]),
            int(spec["action_delay_steps"]),
            float(spec["slew_scale"]),
        ): spec
        for spec in built_specs
    }
    diagnostic_by_key = {
        (
            str(row["pair_id"]),
            str(row["history_member"]),
            str(row["target_id"]),
            int(row["actual_delay_steps"]),
            float(row["actual_slew_scale"]),
        ): row
        for row in ctx.source_r3c1_restart_regulation_diagnostic[
            "control_rows"
        ]
    }
    library, bundle, selector = r1._library_bundle_selector(
        ctx.source_ctx.r1_ctx
    )
    source_rows = []
    development_rows = []
    for index, key in enumerate(
        sorted(sources, key=lambda item: (item[2], item[1], item[0]))
    ):
        source = sources[key]
        slew = float(key[2])
        horizon = _formal_horizon(slew)
        variant = f"slew_{slew:.3f}".replace(".", "p")
        payload = read_json(
            ctx.source_ctx.source_r1_run
            / "stage4_2r1_restart_variants"
            / f"source_{variant}_h{horizon}.payload.json"
        )
        plant = r1.LocalPlantReplayWorker(
            payload,
            library,
            bundle,
            f"stage42r3c2_offline_{index:03d}",
            selector,
        )
        try:
            trajectory = list(source.get("trajectory") or [])
            if len(trajectory) < horizon + 1:
                raise ValueError("R17 source trajectory too short")
            source_spec = copy.deepcopy(source["spec"])
            source_spec["phase_alignment"] = copy.deepcopy(
                ctx.cfg["phase_alignment"]
            )
            source_spec["restart_regulation"] = copy.deepcopy(
                ctx.cfg["restart_regulation"]
            )
            source_spec["visible_reference_manifold"] = copy.deepcopy(
                manifolds[key]
            )
            source_spec["visible_reference_manifold_digest"] = str(
                manifolds[key]["values_digest"]
            )
            initial = copy.deepcopy(dict(trajectory[0]))
            initial["step_index"] = 0
            controller = RestartTargetStateRegulationTaskController(
                plant.base_worker,
                bundle,
                _controller_spec(source_spec),
                initial,
            )
            hidden_variant = copy.deepcopy(initial)
            hidden_variant["wire_currents_a"] = [
                float(index + 1) * 1e9
                for index in range(N_WIRES)
            ]
            hidden_controller = RestartTargetStateRegulationTaskController(
                plant.base_worker,
                bundle,
                _controller_spec(source_spec),
                hidden_variant,
            )
            phase_zero = bool(
                controller.reference_phase_start == 0
                and hidden_controller.reference_phase_start == 0
            )
            exact = True
            maximum = 0.0
            first_mismatch = None
            hidden_first_exact = None
            phase_trace_rows = []
            for step in range(horizon):
                current = copy.deepcopy(dict(trajectory[step]))
                current["step_index"] = step
                action, trace = controller.action(current)
                expected = np.asarray(
                    trajectory[step + 1]["action_norm_tsc"],
                    dtype=float,
                ).reshape(N_COILS)
                difference = float(
                    np.max(
                        np.abs(
                            np.asarray(action, dtype=float) - expected
                        )
                    )
                )
                maximum = max(maximum, difference)
                if not np.array_equal(
                    np.asarray(action, dtype=float), expected
                ):
                    exact = False
                    if first_mismatch is None:
                        first_mismatch = step
                if step == 0:
                    hidden_action, _ = hidden_controller.action(
                        hidden_variant
                    )
                    hidden_first_exact = bool(
                        np.array_equal(
                            np.asarray(action, dtype=float),
                            np.asarray(hidden_action, dtype=float),
                        )
                    )
                if (
                    int(trace["measurement_max_state_index_used"]) > step
                    or bool(trace.get("future_measurement_used"))
                    or bool(trace.get("hidden_wire_used"))
                ):
                    raise ValueError(
                        "R3c2 offline source trace is not causal"
                    )
                phase_trace_rows.append(copy.deepcopy(trace))
                next_state = copy.deepcopy(dict(trajectory[step + 1]))
                next_state["step_index"] = step + 1
                controller.advance(next_state)
            phase_trace = _phase_trace_valid(
                {
                    "controller_trace": phase_trace_rows,
                    "spec": source_spec,
                }
            )
            source_rows.append(
                {
                    "target_id": key[0],
                    "actual_delay_steps": key[1],
                    "actual_slew_scale": key[2],
                    "source_experiment_id": str(source["experiment_id"]),
                    "visible_reference_manifold_digest": str(
                        manifolds[key]["values_digest"]
                    ),
                    "visible_reference_phase_count": int(
                        manifolds[key]["phase_count"]
                    ),
                    "selected_reference_phase": (
                        controller.reference_phase_start
                    ),
                    "phase_zero_selected": phase_zero,
                    "action_steps": horizon,
                    "online_action_exact": exact,
                    "maximum_online_action_abs_difference": maximum,
                    "first_mismatch_step": first_mismatch,
                    "hidden_wire_variant_first_action_exact": (
                        hidden_first_exact
                    ),
                    "source_action_used": False,
                    "source_coil_current_used": False,
                    "source_wire_current_used": False,
                    "current_run_future_used": False,
                    "phase_trace_valid": bool(phase_trace["passed"]),
                    "passed": bool(
                        phase_zero
                        and exact
                        and first_mismatch is None
                        and hidden_first_exact
                        and phase_trace["passed"]
                    ),
                }
            )
            for pair in selected_pairs:
                for member in ("plus_first", "minus_first"):
                    state = pair[f"{member}_state"]
                    development_key = (
                        str(pair["pair_id"]),
                        str(member),
                        str(key[0]),
                        int(key[1]),
                        float(key[2]),
                    )
                    development_spec = development_spec_by_key[
                        development_key
                    ]
                    diagnostic_row = diagnostic_by_key[development_key]
                    initial_development = {
                        "step_index": 0,
                        "R": float(state["R"]),
                        "Z": float(state["Z"]),
                        "Ip": float(state["Ip"]),
                        "currents_a_tsc": list(
                            state["coil_currents_a"]
                        ),
                    }
                    development_controller = RestartTargetStateRegulationTaskController(
                        plant.base_worker,
                        bundle,
                        _controller_spec(development_spec),
                        initial_development,
                    )
                    development_action, development_trace = (
                        development_controller.action(
                            initial_development
                        )
                    )
                    hidden_development = copy.deepcopy(
                        initial_development
                    )
                    hidden_development["wire_currents_a"] = [
                        float(wire + 1) * 1e9
                        for wire in range(N_WIRES)
                    ]
                    hidden_development_controller = (
                        RestartTargetStateRegulationTaskController(
                            plant.base_worker,
                            bundle,
                            _controller_spec(development_spec),
                            hidden_development,
                        )
                    )
                    hidden_development_action, _ = (
                        hidden_development_controller.action(
                            hidden_development
                        )
                    )
                    action_max_abs = float(
                        np.max(
                            np.abs(
                                np.asarray(
                                    development_action, dtype=float
                                )
                            )
                        )
                    )
                    diagnostic_action_max_abs = float(
                        diagnostic_row[
                            "prospective_first_action_max_abs"
                        ]
                    )
                    development_rows.append(
                        {
                            "pair_id": str(pair["pair_id"]),
                            "history_member": member,
                            "target_id": key[0],
                            "actual_delay_steps": key[1],
                            "actual_slew_scale": key[2],
                            "selected_reference_phase": (
                                development_controller.reference_phase_start
                            ),
                            "selected_cost": float(
                                development_controller.phase_selection[
                                    "selected_cost"
                                ]
                            ),
                            "restart_regulation_enabled": bool(
                                development_controller.restart_regulation_enabled
                            ),
                            "controller_phase": str(
                                development_trace["controller_phase"]
                            ),
                            "solver_success": bool(
                                development_trace["solver_success"]
                            ),
                            "step_zero_velocity_exact_zero": bool(
                                np.array_equal(
                                    np.asarray(
                                        development_trace[
                                            "measurement_physical"
                                        ][2:4],
                                        dtype=float,
                                    ),
                                    np.zeros(2, dtype=float),
                                )
                            ),
                            "first_action_finite": bool(
                                np.all(
                                    np.isfinite(development_action)
                                )
                            ),
                            "first_action_max_abs": action_max_abs,
                            "diagnostic_first_action_max_abs": (
                                diagnostic_action_max_abs
                            ),
                            "diagnostic_first_action_scalar_exact": (
                                action_max_abs
                                == diagnostic_action_max_abs
                            ),
                            "first_action_digest": _canonical_digest(
                                np.asarray(
                                    development_action, dtype=float
                                ).tolist()
                            ),
                            "hidden_wire_variant_first_action_exact": bool(
                                np.array_equal(
                                    np.asarray(
                                        development_action, dtype=float
                                    ),
                                    np.asarray(
                                        hidden_development_action,
                                        dtype=float,
                                    ),
                                )
                            ),
                            "controller_spec_forbidden_key_count": len(
                                _FORBIDDEN_CONTROLLER_SPEC_KEYS.intersection(
                                    _controller_spec(development_spec)
                                )
                            ),
                            "hidden_wire_used": False,
                            "source_action_used": False,
                            "source_coil_current_used": False,
                            "source_wire_current_used": False,
                            "current_run_future_used": False,
                        }
                    )
        finally:
            plant.close()
    expected_development = int(
        ctx.cfg["control_matrix"]["expected_rollouts"]
    )
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "offline_restart_target_state_regulation_audit",
        "expected_source_cases": 4,
        "source_case_count": len(source_rows),
        "source_phase_zero_count": sum(
            bool(row["phase_zero_selected"]) for row in source_rows
        ),
        "source_exact_action_count": sum(
            bool(row["online_action_exact"]) for row in source_rows
        ),
        "maximum_source_action_abs_difference": max(
            (
                float(row["maximum_online_action_abs_difference"])
                for row in source_rows
            ),
            default=math.inf,
        ),
        "hidden_wire_invariant_source_case_count": sum(
            bool(row["hidden_wire_variant_first_action_exact"])
            for row in source_rows
        ),
        "source_phase_trace_valid_count": sum(
            bool(row["phase_trace_valid"]) for row in source_rows
        ),
        "authenticated_visible_reference_manifold_count": len(manifolds),
        "authenticated_visible_reference_manifold_digests": sorted(
            str(row["values_digest"]) for row in manifolds.values()
        ),
        "source_action_use_count": sum(
            bool(row["source_action_used"]) for row in source_rows
        ),
        "source_coil_current_use_count": sum(
            bool(row["source_coil_current_used"]) for row in source_rows
        ),
        "source_wire_current_use_count": sum(
            bool(row["source_wire_current_used"]) for row in source_rows
        ),
        "current_run_future_use_count": sum(
            bool(row["current_run_future_used"]) for row in source_rows
        ),
        "expected_development_phase_selections": expected_development,
        "development_phase_selection_count": len(development_rows),
        "development_reference_phase_values": sorted(
            {
                int(row["selected_reference_phase"])
                for row in development_rows
            }
        ),
        "development_hidden_wire_use_count": sum(
            bool(row["hidden_wire_used"]) for row in development_rows
        ),
        "development_restart_regulation_count": sum(
            bool(row["restart_regulation_enabled"])
            for row in development_rows
        ),
        "development_regulation_phase_count": sum(
            str(row["controller_phase"])
            == "restart_target_state_regulation"
            for row in development_rows
        ),
        "development_solver_success_count": sum(
            bool(row["solver_success"]) for row in development_rows
        ),
        "development_zero_velocity_bootstrap_count": sum(
            bool(row["step_zero_velocity_exact_zero"])
            for row in development_rows
        ),
        "development_finite_first_action_count": sum(
            bool(row["first_action_finite"]) for row in development_rows
        ),
        "development_hidden_wire_invariant_count": sum(
            bool(row["hidden_wire_variant_first_action_exact"])
            for row in development_rows
        ),
        "development_diagnostic_scalar_exact_count": sum(
            bool(row["diagnostic_first_action_scalar_exact"])
            for row in development_rows
        ),
        "development_forbidden_controller_key_count": sum(
            int(row["controller_spec_forbidden_key_count"])
            for row in development_rows
        ),
        "future_action_read_count": 0,
        "future_measurement_use_count": 0,
        "real_tsc_executed": False,
    }
    summary["passed"] = bool(
        len(source_rows) == 4
        and all(bool(row["passed"]) for row in source_rows)
        and len(development_rows) == expected_development
        and all(
            0 <= int(row["selected_reference_phase"]) <= 20
            for row in development_rows
        )
        and len(manifolds) == 4
        and len(
            {
                str(row["values_digest"])
                for row in manifolds.values()
            }
        )
        == 4
        and summary["source_action_use_count"] == 0
        and summary["source_coil_current_use_count"] == 0
        and summary["source_wire_current_use_count"] == 0
        and summary["current_run_future_use_count"] == 0
        and summary["development_hidden_wire_use_count"] == 0
        and summary["development_restart_regulation_count"]
        == expected_development
        and summary["development_regulation_phase_count"]
        == expected_development
        and summary["development_solver_success_count"]
        == expected_development
        and summary["development_zero_velocity_bootstrap_count"]
        == expected_development
        and summary["development_finite_first_action_count"]
        == expected_development
        and summary["development_hidden_wire_invariant_count"]
        == expected_development
        and summary["development_diagnostic_scalar_exact_count"]
        == expected_development
        and summary["development_forbidden_controller_key_count"] == 0
    )
    output = {
        "summary": summary,
        "source_results": source_rows,
        "development_restart_regulation_actions": development_rows,
    }
    atomic_write_json(
        ctx.paths.source_reference
        / "offline_restart_regulation_audit.json",
        output,
    )
    return summary


def analyze(
    ctx: Stage42R3C2Context,
    control_summary: Mapping[str, Any],
) -> dict[str, Any]:
    primary_pass = bool(control_summary.get("passed"))
    verdict = {
        "schema_version": 1,
        "stage": STAGE,
        "verdict": (
            "STAGE4_2R3C2_RESTART_TARGET_STATE_REGULATION_PASS"
            if primary_pass
            else "STAGE4_2R3C2_RESTART_TARGET_STATE_REGULATION_FAILED"
        ),
        "source_stage4_2r3b_run": str(ctx.source_r3b_run),
        "source_stage4_2r3c_run": str(ctx.source_r3c_run),
        "source_stage4_2r3c1_run": str(ctx.source_r3c1_run),
        "plant_restart_fidelity_preserved": bool(
            control_summary.get("initial_restart_exact_fraction") == 1.0
        ),
        "controller_causality_preserved": bool(
            control_summary.get("controller_trace_causal_fraction") == 1.0
        ),
        "formal_contract_preserved": bool(
            control_summary.get("formal_contract_pass_fraction") == 1.0
        ),
        "development_set_restart_regulation_validated": primary_pass,
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
            "Proceed only to Stage4.2R3d independent new-history "
            "confirmation. Do not start new targets, BC, DAgger, or RL."
        ),
        "next_if_fail": (
            "Preserve R3c2 raw evidence and create a new controller "
            "revision without weakening the formal gate."
        ),
    }
    summary = {
        **verdict,
        "created_utc": utc_timestamp(),
        "control_summary": dict(control_summary),
    }
    atomic_write_json(
        ctx.paths.analysis / "stage4_2r3c2_verdict.json", verdict
    )
    atomic_write_json(
        ctx.paths.analysis / "stage4_2r3c2_summary.json", summary
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
                else "restart_target_state_regulation_control_failed"
            ),
            "updated_utc": utc_timestamp(),
            "verdict": verdict,
        }
    )
    atomic_write_json(ctx.paths.state, state)
    return summary


def execute(
    ctx: Stage42R3C2Context,
    *,
    command: str,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    selected_pairs, specs = prepare(ctx, resume=resume)
    offline = run_offline_restart_regulation_audit(
        ctx, selected_pairs
    )
    if not bool(offline.get("passed")):
        raise RuntimeError(
            "Stage4.2R3c2 offline restart-regulation gate failed; "
            "no real TSC control was started"
        )
    if command == "offline":
        state = read_json(ctx.paths.state)
        state.update(
            {
                "finished": False,
                "primary_pass": False,
                "phase_status": "offline_gate_complete",
                "stop_reason": "",
                "offline_restart_regulation_audit": dict(offline),
                "updated_utc": utc_timestamp(),
            }
        )
        atomic_write_json(ctx.paths.state, state)
        return {
            "schema_version": 1,
            "stage": STAGE,
            "phase": "offline_restart_target_state_regulation_audit",
            "offline_restart_regulation_audit": dict(offline),
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
            "Stage4.2R3c2 restart target-state regulation MPC"
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
    ctx = load_stage42r3c2_config(
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
