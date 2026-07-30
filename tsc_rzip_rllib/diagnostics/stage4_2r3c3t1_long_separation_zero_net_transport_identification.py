"""Stage4.2R3c3T1 long-separation zero-net transport identification.

R3c3T1 keeps the exact R3c1 controller and the authenticated R3c3
development contexts.  It adds two prospectively fixed, bounded transport
probe schedules.  The stage is identification-only: probe trajectories are
never demonstrations or expert data.
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
from types import FunctionType, SimpleNamespace
from typing import Any, Mapping, Sequence

import numpy as np

try:
    import resource
except ImportError:  # pragma: no cover - Windows local validation
    resource = None

from tsc_rzip_rllib.utils.ray_runtime import ensure_ray_worker_plan

from . import (
    stage4_2r3c3_restart_task_clock_local_response_identification as r3c3,
)


STAGE = "Stage4.2R3c3T1"
CONTROLLER_REVISION = (
    "long_separation_zero_net_transport_probe_v42r3c3t1"
)
PACKAGE_REVISION = (
    "r42r3c3t1_long_separation_transport_identification_v1"
)
SCHEMA_VERSION = 1

r3c1 = r3c3.r3c1
r3b = r3c3.r3b
r2 = r3c3.r2
r1 = r3c3.r1

N_COILS = r3c3.N_COILS
N_MODES = r3c3.N_MODES
N_WIRES = r3c3.N_WIRES

EXPECTED_R3C3_RUN_NAME = (
    "stage4_2r3c3_restart_task_clock_local_response_identification_"
    "20260730_182427"
)
EXPECTED_AUDIT_BANK_NAME = (
    "stage4_2r3c3_compact_response_audit_bank_v1.json"
)
EXPECTED_CONTROLLER_BANK_NAME = (
    "stage4_2r3c3_controller_response_bank_v1.json"
)
EXPECTED_BANK_MANIFEST_NAME = (
    "stage4_2r3c3_compact_response_bank_manifest_v1.json"
)


def _json_safe(value: Any) -> Any:
    return r3c3._json_safe(value)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_digest(value: Any) -> str:
    return r3c3._canonical_digest(value)


def _formal_horizon(slew: float) -> int:
    return r3c3._formal_horizon(slew)


def _requested_workers(cfg: Mapping[str, Any]) -> int:
    return int(
        os.environ.get(
            "STAGE4_2R3C3T1_WORKERS",
            cfg["parallel"]["n_workers"],
        )
    )


def _validate_formal_timing(cfg: Mapping[str, Any]) -> None:
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
        or float(timing["position_tolerance_m"]) != 0.03
        or float(timing["speed_tolerance_m_per_s"]) != 0.1
        or not bool(timing["arrival_streak_steps_unchanged"])
        or not bool(timing["ip_threshold_unchanged"])
        or bool(timing["arrival_deadline_expansion_allowed"])
    ):
        raise ValueError("Stage4.2R3c3T1 formal timing changed")


def validate_config(cfg: Mapping[str, Any]) -> None:
    if str(cfg.get("stage")) != STAGE:
        raise ValueError("Stage4.2R3c3T1 config stage mismatch")
    if str(cfg.get("controller_revision")) != CONTROLLER_REVISION:
        raise ValueError("Stage4.2R3c3T1 controller revision mismatch")
    if str(cfg.get("package_revision")) != PACKAGE_REVISION:
        raise ValueError("Stage4.2R3c3T1 package revision mismatch")
    if int(cfg["parallel"]["n_workers"]) != 128:
        raise ValueError("Stage4.2R3c3T1 requires 128 Ray workers")
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
    if dict(cfg["phase_alignment"]) != expected_phase:
        raise ValueError("Stage4.2R3c3T1 phase contract changed")
    probe = cfg["identification_probe"]
    if (
        str(probe["baseline_controller"]) != r3c1.CONTROLLER_REVISION
        or str(probe["baseline_package"]) != r3c1.PACKAGE_REVISION
        or list(map(float, probe["physical_mode_amplitude"]))
        != [0.0075, 0.0075, 0.0]
        or list(map(int, probe["probe_signs"])) != [-1, 1]
        or int(probe["required_nonzero_issue_count"]) != 12
        or not bool(probe["require_requested_and_applied_zero_net"])
        or float(probe["zero_net_atol"]) != 1.0e-12
        or float(probe["maximum_current_utilization"]) != 0.55
        or bool(probe["formal_tracking_pass_required"])
        or bool(probe["probe_trajectories_allowed_in_expert_dataset"])
        or bool(probe["pair_or_history_label_input_allowed"])
        or bool(probe["source_result_input_allowed"])
        or bool(probe["source_action_input_allowed"])
        or bool(probe["source_or_current_wire_input_allowed"])
    ):
        raise ValueError("Stage4.2R3c3T1 probe contract changed")
    expected_offsets = [0, 1, 2, 3, 4, 5, 12, 13, 14, 15, 16, 17]
    expected_signs = [1, 1, 1, 1, 1, 1, -1, -1, -1, -1, -1, -1]
    expected_basis = [
        ("transport_mode0", 0, 3),
        ("transport_mode1", 1, 3),
    ]
    actual_basis = []
    for row in probe["basis"]:
        if (
            list(map(int, row["effect_offsets"])) != expected_offsets
            or list(map(int, row["sign_pattern"])) != expected_signs
        ):
            raise ValueError("Stage4.2R3c3T1 transport shape changed")
        actual_basis.append(
            (
                str(row["probe_id"]),
                int(row["mode"]),
                int(row["first_effect_state"]),
            )
        )
    if actual_basis != expected_basis:
        raise ValueError("Stage4.2R3c3T1 basis changed")
    symmetry = probe["central_symmetry"]
    hidden = probe["matched_hidden_history"]
    if (
        float(symmetry["maximum_even_velocity_rmse_m_per_s"]) != 0.004
        or float(symmetry["maximum_even_position_rmse_m"]) != 0.0005
        or float(symmetry["maximum_even_ip_rmse_A"]) != 20.0
        or float(hidden["maximum_odd_velocity_rmse_m_per_s"]) != 0.006
        or float(hidden["maximum_odd_position_rmse_m"]) != 0.001
        or float(hidden["maximum_odd_ip_rmse_A"]) != 40.0
        or float(
            probe["maximum_selected_velocity_condition_number"]
        )
        != 25.0
        or float(probe["maximum_combined_velocity_condition_number"])
        != 25.0
    ):
        raise ValueError("Stage4.2R3c3T1 response gates changed")
    matrix = cfg["control_matrix"]
    actuator = [
        (
            int(row["actual_delay_steps"]),
            float(row["actual_slew_scale"]),
        )
        for row in matrix["future_actuator_cases"]
    ]
    if (
        list(map(str, matrix["targets"]))
        != ["nominal", "RZ_p10_m10"]
        or actuator != [(0, 1.0), (2, 0.9)]
        or list(map(str, matrix["history_members"]))
        != ["plus_first", "minus_first"]
        or int(matrix["probe_basis_count"]) != 2
        or int(matrix["probe_sign_count"]) != 2
        or int(matrix["expected_rollouts_per_baseline_context"]) != 4
        or int(matrix["expected_baseline_contexts_per_selected_pair"]) != 8
        or int(matrix["expected_rollouts_per_selected_pair"]) != 32
        or int(matrix["expected_selected_pairs"]) != 4
        or int(matrix["expected_baseline_contexts"]) != 32
        or int(matrix["expected_rollouts"]) != 128
        or not bool(matrix["require_fresh_controller"])
        or not bool(matrix["require_fresh_tsc_process"])
        or not bool(matrix["forbid_future_actions"])
        or not bool(matrix["forbid_future_measurements"])
        or not bool(matrix["require_online_action_computation"])
    ):
        raise ValueError("Stage4.2R3c3T1 matrix changed")
    _validate_formal_timing(cfg)
    if (
        not bool(cfg["development_set_only"])
        or bool(cfg["independent_hidden_history_confirmation"])
        or bool(cfg["different_initial_state_validated"])
        or bool(cfg["unseen_target_validated"])
        or bool(cfg["continuous_parameter_change_validated"])
        or bool(cfg["plant_jacobian_error_validated"])
        or bool(cfg["measurement_noise_validated"])
        or bool(cfg["disturbance_recovery_validated"])
        or bool(cfg["independent_long_hold_validated"])
        or bool(cfg["bc_dagger_or_rl_allowed"])
    ):
        raise ValueError("Stage4.2R3c3T1 scope guard changed")


@dataclass
class Stage42R3C3T1Paths:
    run_dir: Path
    source_reference: Path
    variants: Path
    control: Path
    analysis: Path
    state: Path
    manifest: Path

    @classmethod
    def from_run_dir(cls, run_dir: Path) -> "Stage42R3C3T1Paths":
        root = run_dir.expanduser().resolve()
        return cls(
            run_dir=root,
            source_reference=root / "stage4_2r3c3t1_source_reference",
            variants=root / "stage4_2r3c3t1_environment_variants",
            control=root
            / "stage4_2r3c3t1_transport_response_identification",
            analysis=root / "stage4_2r3c3t1_analysis",
            state=root / "stage4_2r3c3t1_state.json",
            manifest=root / "stage4_2r3c3t1_manifest.json",
        )


@dataclass
class Stage42R3C3T1Context:
    cfg: dict[str, Any]
    paths: Stage42R3C3T1Paths
    project_dir: Path
    source_r3c3_run: Path
    source_bank_dir: Path
    source_bank_fingerprint: dict[str, Any]
    base_ctx: r3c3.Stage42R3C3Context

    @property
    def source_ctx(self) -> Any:
        return self.base_ctx.source_ctx

    @property
    def source_r3b_run(self) -> Path:
        return self.base_ctx.source_r3b_run

    @property
    def source_r3b_audit(self) -> Path:
        return self.base_ctx.source_r3b_audit

    @property
    def source_fingerprint(self) -> dict[str, Any]:
        return self.base_ctx.source_fingerprint

    @property
    def source_r3c_run(self) -> Path:
        return self.base_ctx.source_r3c_run

    @property
    def source_r3c_audit(self) -> Path:
        return self.base_ctx.source_r3c_audit

    @property
    def source_r3c_fingerprint(self) -> dict[str, Any]:
        return self.base_ctx.source_r3c_fingerprint

    @property
    def source_r3c1_run(self) -> Path:
        return self.base_ctx.source_r3c1_run

    @property
    def source_r3c1_audit(self) -> Path:
        return self.base_ctx.source_r3c1_audit

    @property
    def source_r3c1_fingerprint(self) -> dict[str, Any]:
        return self.base_ctx.source_r3c1_fingerprint

    @property
    def source_r3c2_run(self) -> Path:
        return self.base_ctx.source_r3c2_run

    @property
    def source_r3c2_audit(self) -> Path:
        return self.base_ctx.source_r3c2_audit

    @property
    def source_r3c2_fingerprint(self) -> dict[str, Any]:
        return self.base_ctx.source_r3c2_fingerprint


def _raw_identity(paths: Sequence[Path]) -> list[dict[str, Any]]:
    return [
        {
            "path": path.name,
            "size_bytes": int(path.stat().st_size),
            "sha256": _sha256(path),
        }
        for path in paths
    ]


def _source_bank_fingerprint(
    cfg: Mapping[str, Any],
    source_r3c3_run: Path,
    source_bank_dir: Path,
) -> dict[str, Any]:
    requirements = cfg["source_requirements"]
    if source_r3c3_run.name != str(
        requirements["required_stage4_2r3c3_run_name"]
    ):
        raise ValueError("Stage4.2R3c3T1 source R3c3 run changed")
    files = {
        "audit_bank": source_bank_dir / EXPECTED_AUDIT_BANK_NAME,
        "controller_bank": source_bank_dir / EXPECTED_CONTROLLER_BANK_NAME,
        "bank_manifest": source_bank_dir / EXPECTED_BANK_MANIFEST_NAME,
        "run_manifest": source_r3c3_run / "stage4_2r3c3_manifest.json",
        "run_state": source_r3c3_run / "stage4_2r3c3_state.json",
    }
    for name, path in files.items():
        if not path.is_file():
            raise FileNotFoundError(
                f"Stage4.2R3c3T1 source evidence missing: {name}: {path}"
            )
    expected_hashes = {
        "audit_bank": str(
            requirements["required_stage4_2r3c3_audit_bank_sha256"]
        ),
        "controller_bank": str(
            requirements["required_stage4_2r3c3_controller_bank_sha256"]
        ),
        "bank_manifest": str(
            requirements["required_stage4_2r3c3_bank_manifest_sha256"]
        ),
    }
    for name, expected in expected_hashes.items():
        if _sha256(files[name]) != expected:
            raise ValueError(f"Stage4.2R3c3T1 {name} hash changed")
    bank_audit = r3c3.read_json(files["audit_bank"])
    controller_bank = r3c3.read_json(files["controller_bank"])
    bank_manifest = r3c3.read_json(files["bank_manifest"])
    run_manifest = r3c3.read_json(files["run_manifest"])
    run_state = r3c3.read_json(files["run_state"])
    provenance = str(
        requirements["required_stage4_2r3c3_bank_provenance_digest"]
    )
    if (
        str(bank_audit.get("provenance_digest")) != provenance
        or str(controller_bank.get("provenance_digest")) != provenance
        or str(bank_manifest.get("provenance_digest")) != provenance
        or str(
            bank_audit["provenance_contract"][
                "r3c1_baseline_inventory_digest"
            ]
        )
        != str(
            requirements[
                "required_stage4_2r3c1_baseline_inventory_digest"
            ]
        )
        or int(controller_bank.get("sample_count", -1)) != 32
        or int(controller_bank.get("basis_count", -1)) != 4
        or not bool(
            bank_audit["authentication_summary"][
                "all_authentication_gates_passed"
            ]
        )
        or run_manifest.get("stage") != r3c3.STAGE
        or run_manifest.get("controller_revision")
        != r3c3.CONTROLLER_REVISION
        or run_manifest.get("package_revision") != r3c3.PACKAGE_REVISION
        or not bool(run_state.get("finished"))
        or not bool(run_state.get("primary_pass"))
    ):
        raise ValueError("Stage4.2R3c3T1 source bank contract changed")
    raw_dir = (
        source_r3c3_run
        / "stage4_2r3c3_restart_task_clock_probe_identification"
        / "raw"
    )
    raw_paths = sorted(raw_dir.glob("*.json.gz"))
    raw_identity = _raw_identity(raw_paths)
    raw_digest = _canonical_digest(raw_identity)
    if (
        len(raw_paths)
        != int(requirements["required_stage4_2r3c3_raw_count"])
        or raw_digest
        != str(
            requirements["required_stage4_2r3c3_raw_inventory_digest"]
        )
    ):
        raise ValueError("Stage4.2R3c3T1 source raw inventory changed")
    return {
        "schema_version": 1,
        "source_r3c3_run": str(source_r3c3_run),
        "source_bank_dir": str(source_bank_dir),
        "raw_count": len(raw_paths),
        "raw_inventory_digest": raw_digest,
        "audit_bank_sha256": _sha256(files["audit_bank"]),
        "controller_bank_sha256": _sha256(files["controller_bank"]),
        "bank_manifest_sha256": _sha256(files["bank_manifest"]),
        "bank_provenance_digest": provenance,
        "r3c1_baseline_inventory_digest": str(
            bank_audit["provenance_contract"][
                "r3c1_baseline_inventory_digest"
            ]
        ),
        "run_manifest_digest": _canonical_digest(run_manifest),
    }


def load_stage42r3c3t1_config(
    config_path: Path,
    *,
    source_stage42r3b_run: Path,
    source_stage42r3c3_run: Path,
    source_stage42r3c3_bank_dir: Path,
    run_dir_override: Path | None = None,
) -> Stage42R3C3T1Context:
    config_path = config_path.expanduser().resolve()
    cfg = r3c3.read_json(config_path)
    validate_config(cfg)
    project_dir = config_path.parents[1]
    source_r3c3_run = source_stage42r3c3_run.expanduser().resolve()
    source_bank_dir = source_stage42r3c3_bank_dir.expanduser().resolve()
    fingerprint = _source_bank_fingerprint(
        cfg, source_r3c3_run, source_bank_dir
    )
    base_ctx = r3c3.load_stage42r3c3_config(
        project_dir
        / "configs"
        / (
            "stage4_2r3c3_restart_task_clock_local_response_"
            "identification_370ms.json"
        ),
        source_stage42r3b_run=source_stage42r3b_run,
        run_dir_override=source_r3c3_run,
    )
    if run_dir_override is None:
        run_dir = (
            project_dir
            / str(cfg["output_root"])
            / f"{cfg['run_name']}_{r3c3.utc_timestamp()}"
        )
    else:
        run_dir = run_dir_override.expanduser().resolve()
    return Stage42R3C3T1Context(
        cfg=cfg,
        paths=Stage42R3C3T1Paths.from_run_dir(run_dir),
        project_dir=project_dir,
        source_r3c3_run=source_r3c3_run,
        source_bank_dir=source_bank_dir,
        source_bank_fingerprint=fingerprint,
        base_ctx=base_ctx,
    )


def _probe_schedule(
    *,
    basis: Mapping[str, Any],
    actual_delay: int,
    sign: int,
    amplitude_by_mode: Sequence[float],
) -> dict[int, np.ndarray]:
    return r3c3._probe_schedule(
        first_effect_state=int(basis["first_effect_state"]),
        actual_delay=actual_delay,
        basis=basis,
        sign=sign,
        amplitude_by_mode=amplitude_by_mode,
    )


def build_control_specs(
    ctx: Stage42R3C3T1Context,
    selected_pairs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    original = r3c3.build_control_specs(ctx.base_ctx, selected_pairs)
    templates: dict[tuple[Any, ...], Mapping[str, Any]] = {}
    for spec in original:
        key = (
            str(spec["pair_id"]),
            str(spec["history_member"]),
            str(spec["target_id"]),
            int(spec["action_delay_steps"]),
            float(spec["slew_scale"]),
        )
        if (
            str(spec["r3c3_probe_id"]) == "early_mode0"
            and int(spec["r3c3_probe_sign"]) == 1
        ):
            templates[key] = spec
    if len(templates) != 32:
        raise ValueError("Stage4.2R3c3T1 template coverage mismatch")
    amplitudes = list(
        map(float, ctx.cfg["identification_probe"]["physical_mode_amplitude"])
    )
    specs = []
    for key in sorted(templates):
        template = templates[key]
        for basis in ctx.cfg["identification_probe"]["basis"]:
            for sign in ctx.cfg["identification_probe"]["probe_signs"]:
                schedule = _probe_schedule(
                    basis=basis,
                    actual_delay=int(template["action_delay_steps"]),
                    sign=int(sign),
                    amplitude_by_mode=amplitudes,
                )
                if len(schedule) != 12:
                    raise ValueError("transport schedule issue count changed")
                requested_net = np.sum(
                    np.stack(list(schedule.values())), axis=0
                )
                if not np.array_equal(
                    requested_net, np.zeros(N_MODES, dtype=float)
                ):
                    raise ValueError("transport schedule is not zero net")
                identity = {
                    "stage": STAGE,
                    "pair_id": str(template["pair_id"]),
                    "history_member": str(template["history_member"]),
                    "state_generation_experiment_id": str(
                        template["state_generation_experiment_id"]
                    ),
                    "snapshot_manifest_digest": str(
                        template["restart_snapshot_manifest_digest"]
                    ),
                    "target_id": str(template["target_id"]),
                    "actual_delay_steps": int(
                        template["action_delay_steps"]
                    ),
                    "actual_slew_scale": float(template["slew_scale"]),
                    "probe_id": str(basis["probe_id"]),
                    "probe_sign": int(sign),
                    "probe_schedule": {
                        str(step): value.tolist()
                        for step, value in schedule.items()
                    },
                    "controller_revision": CONTROLLER_REVISION,
                    "source_bank_provenance_digest": str(
                        ctx.source_bank_fingerprint[
                            "bank_provenance_digest"
                        ]
                    ),
                }
                experiment_id = r3c3._scenario_digest(identity)
                spec = copy.deepcopy(dict(template))
                spec.update(
                    {
                        "kind": (
                            "stage4_2r3c3t1_long_separation_zero_net_"
                            "transport_identification"
                        ),
                        "stage": STAGE,
                        "controller_revision": CONTROLLER_REVISION,
                        "underlying_controller_revision": (
                            r3c1.CONTROLLER_REVISION
                        ),
                        "experiment_id": experiment_id,
                        "phase": (
                            "long_separation_zero_net_transport_"
                            "identification"
                        ),
                        "category": (
                            "long_separation_zero_net_transport_"
                            "identification"
                        ),
                        "environment_variant": (
                            f"stage4_2r3c3t1_{experiment_id}"
                        ),
                        "identification_only": True,
                        "r3c3_probe_id": str(basis["probe_id"]),
                        "r3c3_probe_mode": int(basis["mode"]),
                        "r3c3_probe_sign": int(sign),
                        "r3c3_probe_first_effect_state": int(
                            basis["first_effect_state"]
                        ),
                        "r3c3_probe_delta_by_task_issue_step": {
                            str(step): value.tolist()
                            for step, value in schedule.items()
                        },
                        "r3c3_requested_probe_net": (
                            requested_net.tolist()
                        ),
                        "r3c3_probe_amplitude": float(
                            amplitudes[int(basis["mode"])]
                        ),
                        "r3c3t1_transport_contract": (
                            "positive_states_3_to_8_negative_"
                            "states_15_to_20_zero_net_v1"
                        ),
                        "source_stage4_2r3c3_bank_provenance_digest": (
                            ctx.source_bank_fingerprint[
                                "bank_provenance_digest"
                            ]
                        ),
                        "probe_trajectory_allowed_in_expert_dataset": (
                            False
                        ),
                        "pair_or_history_label_available_to_controller": (
                            False
                        ),
                        "source_result_available_to_controller": False,
                        "source_action_available_to_controller": False,
                        "source_coil_current_available_to_controller": False,
                        "source_wire_current_available_to_controller": False,
                        "hidden_wire_current_available_to_controller": False,
                        "future_action_count": 0,
                        "future_measurement_count": 0,
                        "online_action_computation_required": True,
                        "task_clock_starts_at_zero": True,
                        "formal_timing_unchanged": True,
                        "development_set_only": True,
                    }
                )
                specs.append(spec)
    expected = int(ctx.cfg["control_matrix"]["expected_rollouts"])
    if (
        len(specs) != expected
        or len({str(spec["experiment_id"]) for spec in specs}) != expected
    ):
        raise ValueError("Stage4.2R3c3T1 control coverage mismatch")
    return specs


def _controller_spec(spec: Mapping[str, Any]) -> dict[str, Any]:
    return r3c3._controller_spec(spec)


class LongSeparationTransportProbeController(
    r3c1.AuthenticatedVisibleManifoldPhaseTaskController
):
    """Exact R3c1 controller plus one fixed bounded transport basis."""

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
                source_spec.get("r3c3_probe_delta_by_task_issue_step")
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
            self.probe_id
            not in {"transport_mode0", "transport_mode1"}
            or self.probe_mode not in {0, 1}
            or self.probe_sign not in {-1, 1}
            or self.probe_first_effect_state != 3
            or not math.isclose(
                self.probe_amplitude,
                0.0075,
                rel_tol=0.0,
                abs_tol=1.0e-15,
            )
            or len(self.probe_schedule) != 12
        ):
            raise ValueError("Stage4.2R3c3T1 controller contract invalid")
        requested = np.sum(
            np.stack(list(self.probe_schedule.values())), axis=0
        )
        if not np.array_equal(
            requested, np.zeros(N_MODES, dtype=float)
        ):
            raise ValueError("Stage4.2R3c3T1 probe is not zero net")

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
            raise ValueError("scheduled transport probe missed solver")
        zeros = np.zeros(N_MODES, dtype=float).tolist()
        trace.update(
            {
                "task_step": task_step,
                "baseline_controller_revision": r3c1.CONTROLLER_REVISION,
                "r3c3_identification_only": True,
                "r3c3t1_identification_only": True,
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


def _control_payload(
    ctx: Stage42R3C3T1Context, *, spec: Mapping[str, Any]
) -> dict[str, Any]:
    proxy = SimpleNamespace(
        source_ctx=ctx.source_ctx,
        cfg=ctx.cfg,
        paths=ctx.paths,
    )
    payload = r3c3._control_payload(proxy, spec=spec)
    payload["variant_id"] = (
        f"stage4_2r3c3t1_{spec['experiment_id']}"
    )
    payload["stage4_2r3c3t1_restart_snapshot_dir"] = str(
        spec["restart_snapshot_dir"]
    )
    payload["stage4_2r3c3t1_snapshot_manifest_digest"] = str(
        spec["restart_snapshot_manifest_digest"]
    )
    r3c3.atomic_write_json(
        ctx.paths.variants / f"payload_{spec['experiment_id']}.json",
        payload,
    )
    return payload


class LocalTransportResponseProbeWorker:
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
                raise ValueError("Stage4.2R3c3T1 formal horizon changed")
            self.base.env.reset()
            zero_action = np.zeros(N_COILS, dtype=np.float32)
            initial = r1._state_record_full(
                self.base.env, 0, zero_action
            )
            trajectory = [initial]
            controller = LongSeparationTransportProbeController(
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
            expected_shape = (12, N_MODES)
            scheduled_exact = bool(
                len(issued_rows) == len(expected_schedule) == 12
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
            applied_exact = bool(
                requested.shape == applied.shape == expected_shape
                and np.allclose(
                    requested, applied, rtol=0.0, atol=1.0e-12
                )
            )
            requested_net = (
                np.sum(requested, axis=0)
                if requested.shape == expected_shape
                else np.full(N_MODES, np.nan)
            )
            applied_net = (
                np.sum(applied, axis=0)
                if applied.shape == expected_shape
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
                    or bool(row.get("pair_or_history_label_used"))
                    or bool(row.get("source_result_used"))
                    for row in trace
                )
                and all(bool(row.get("solver_success")) for row in trace)
                and scheduled_exact
                and applied_exact
                and zero_net
            )
            result.update(
                {
                    "success": success,
                    "completed": True,
                    "failure_reason": (
                        ""
                        if success
                        else "incomplete or invalid transport-probe rollout"
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
                        "controller_previous_correction_initialization": (
                            "zero"
                        ),
                        "controller_delay_queue_initialization": (
                            "authenticated_visible_manifold_phase_"
                            "aligned_nominal_prime"
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
                        "scheduled_probe_exact": scheduled_exact,
                        "applied_probe_exact": applied_exact,
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
                        "pair_or_history_label_used": False,
                        "source_result_used": False,
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
                        "stage4_2r3c3t1_long_separation_transport_"
                        "identification"
                    ),
                )


_CONTROL_RAY_ACTOR = None


def _control_ray_actor_class():
    global _CONTROL_RAY_ACTOR
    if _CONTROL_RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class Stage42R3C3T1ControlActor:
            def __init__(
                self, payload, library, bundle, worker_id, selector_cfg
            ):
                self.worker = LocalTransportResponseProbeWorker(
                    payload, library, bundle, worker_id, selector_cfg
                )

            def evaluate(self, spec):
                return self.worker.evaluate(spec)

            def close(self):
                self.worker.close()
                return True

        _CONTROL_RAY_ACTOR = Stage42R3C3T1ControlActor
    return _CONTROL_RAY_ACTOR


def _result_complete(
    path: Path, expected_spec: Mapping[str, Any]
) -> bool:
    if not path.is_file():
        return False
    try:
        result = r3c3.read_json_gz(path)
        return bool(
            result.get("completed")
            and result.get("stage") == STAGE
            and result.get("controller_revision") == CONTROLLER_REVISION
            and result.get("experiment_id")
            == expected_spec["experiment_id"]
            and result.get("spec") == dict(expected_spec)
            and isinstance(result.get("success"), bool)
            and isinstance(result.get("trajectory"), list)
            and isinstance(result.get("controller_trace"), list)
        )
    except Exception:
        return False


def _structured_actor_failure(
    spec: Mapping[str, Any], exc: Exception
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
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
    ctx: Stage42R3C3T1Context,
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
                raw_dir / f"{spec['experiment_id']}.json.gz", spec
            )
        )
    ]
    payloads = {
        str(spec["experiment_id"]): _control_payload(ctx, spec=spec)
        for spec in specs
    }
    if backend == "serial":
        for index, spec in enumerate(pending):
            worker = LocalTransportResponseProbeWorker(
                payloads[str(spec["experiment_id"])],
                library,
                bundle,
                f"stage42r3c3t1_serial_{index:03d}",
                selector,
            )
            try:
                result = worker.evaluate(spec)
            finally:
                worker.close()
            r3c3.atomic_write_json_gz(
                raw_dir / f"{spec['experiment_id']}.json.gz", result
            )
            print(
                f"[Stage4.2R3c3T1] {index + 1}/{len(pending)}",
                flush=True,
            )
    elif backend == "ray" and pending:
        import ray

        plan = ensure_ray_worker_plan(
            ray,
            requested_workers=_requested_workers(ctx.cfg),
            pending_tasks=len(pending),
            ray_tmpdir=os.environ.get("RAY_TMPDIR")
            or ctx.cfg["parallel"].get("ray_tmpdir"),
            log_prefix="[Stage4.2R3c3T1]",
        )
        Actor = _control_ray_actor_class()
        completed = 0
        print(
            "[Stage4.2R3c3T1] "
            f"maximum_actor_count={plan.actor_count} "
            f"pending={len(pending)}",
            flush=True,
        )
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
                    f"stage42r3c3t1_{index:03d}",
                    selector,
                )
                actors.append(actor)
                refs[actor.evaluate.remote(spec)] = spec
            try:
                while refs:
                    ready, _ = ray.wait(
                        list(refs), num_returns=1, timeout=30.0
                    )
                    if not ready:
                        print(
                            "[Stage4.2R3c3T1] "
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
                        r3c3.atomic_write_json_gz(
                            raw_dir
                            / f"{spec['experiment_id']}.json.gz",
                            result,
                        )
                        completed += 1
                        if completed % 8 == 0 or not refs:
                            print(
                                "[Stage4.2R3c3T1] "
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
        r3c3.read_json_gz(
            raw_dir / f"{spec['experiment_id']}.json.gz"
        )
        for spec in specs
    ]


def _phase_trace_valid(result: Mapping[str, Any]) -> dict[str, Any]:
    """Authenticate the inherited R3c1 trace and all 12 T1 injections."""

    base = r3c1._phase_trace_valid(result)
    trace = list(result.get("controller_trace") or [])
    spec = dict(result.get("spec") or {})
    schedule = {
        int(step): np.asarray(value, dtype=float).reshape(N_MODES)
        for step, value in (
            spec.get("r3c3_probe_delta_by_task_issue_step") or {}
        ).items()
    }
    expected_count = len(schedule)
    zeros = np.zeros(N_MODES, dtype=float)
    pair_or_history_count = 0
    source_result_count = 0
    solver_failure_count = 0
    issued_count = 0
    requested_rows = []
    applied_rows = []
    trace_exact = bool(trace and expected_count == 12)
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
    expected_shape = (expected_count, N_MODES)
    requested = (
        np.stack(requested_rows)
        if len(requested_rows) == expected_count
        else np.empty((0, N_MODES), dtype=float)
    )
    applied = (
        np.stack(applied_rows)
        if len(applied_rows) == expected_count
        else np.empty((0, N_MODES), dtype=float)
    )
    requested_net = (
        np.sum(requested, axis=0)
        if requested.shape == expected_shape
        else np.full(N_MODES, np.nan)
    )
    applied_net = (
        np.sum(applied, axis=0)
        if applied.shape == expected_shape
        else np.full(N_MODES, np.nan)
    )
    applied_exact = bool(
        requested.shape == applied.shape == expected_shape
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
        and issued_count == expected_count == 12
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


def _combined_condition_rows(
    ctx: Stage42R3C3T1Context,
    results: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    audit_bank = r3c3.read_json(
        ctx.source_bank_dir / EXPECTED_AUDIT_BANK_NAME
    )
    old_by_key = {}
    for context in audit_bank["contexts"]:
        identity = context["audit_identity"]
        key = (
            str(identity["pair_id"]),
            str(identity["history_member"]),
            str(identity["target_id"]),
            int(context["actual_delay_steps"]),
            float(context["actual_slew_scale"]),
        )
        old_by_key[key] = [
            np.asarray(
                response["delta_velocity_RZ_by_state"], dtype=float
            )
            for response in sorted(
                context["responses"],
                key=lambda row: int(row["basis_index"]),
            )
        ]
    dt_ms = int(
        r1._r13_ctx(ctx.source_ctx.r1_ctx)
        .r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34.env_cfg[
            "dt_ms"
        ]
    )
    dt_s = dt_ms / 1000.0
    signed: dict[
        tuple[Any, ...], dict[int, Mapping[str, Any]]
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
        signed[key][int(spec["r3c3_probe_sign"])] = result
    transport: dict[tuple[Any, ...], dict[str, np.ndarray]] = (
        defaultdict(dict)
    )
    for key, members in signed.items():
        if set(members) != {-1, 1}:
            continue
        _, plus_v = r3c3._trajectory_arrays(members[1], dt_s)
        _, minus_v = r3c3._trajectory_arrays(members[-1], dt_s)
        transport[key[:5]][key[5]] = (plus_v - minus_v) / 2.0
    rows = []
    maximum = float(
        ctx.cfg["identification_probe"][
            "maximum_combined_velocity_condition_number"
        ]
    )
    for key in sorted(old_by_key):
        new = transport.get(key, {})
        rank = None
        condition = None
        passed = False
        if set(new) == {"transport_mode0", "transport_mode1"}:
            arrays = [
                *old_by_key[key],
                new["transport_mode0"],
                new["transport_mode1"],
            ]
            if len({array.shape for array in arrays}) == 1:
                matrix = np.stack(
                    [array[3:, :2].reshape(-1) for array in arrays],
                    axis=1,
                )
                rank = int(np.linalg.matrix_rank(matrix))
                condition = float(np.linalg.cond(matrix))
                passed = bool(
                    rank == 6
                    and math.isfinite(condition)
                    and condition <= maximum
                )
        rows.append(
            {
                "pair_id": key[0],
                "history_member": key[1],
                "target_id": key[2],
                "actual_delay_steps": key[3],
                "actual_slew_scale": key[4],
                "basis_count": 6,
                "velocity_response_matrix_rank": rank,
                "selected_velocity_condition_number": condition,
                "condition_number_pass": passed,
            }
        )
    return rows


def _summarize_transport_responses(
    ctx: Stage42R3C3T1Context,
    results: Sequence[Mapping[str, Any]],
    selected_pairs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Reuse frozen statistics without mutating the R3c3 module.

    The R3c3 summary implementation is valid for arbitrary probe-basis
    cardinality except that its phase validator freezes four issue steps.
    Execute the same immutable code object in an isolated globals namespace
    whose only semantic substitutions are the T1 stage label and the local
    12-issue phase validator.  The imported R3c3 module and its functions are
    never patched or reassigned.
    """

    namespace = dict(r3c3.summarize_control.__globals__)
    namespace["STAGE"] = STAGE
    namespace["_phase_trace_valid"] = _phase_trace_valid
    summarize = FunctionType(
        r3c3.summarize_control.__code__,
        namespace,
        name="_stage4_2r3c3t1_response_summary",
        argdefs=r3c3.summarize_control.__defaults__,
        closure=r3c3.summarize_control.__closure__,
    )
    summarize.__kwdefaults__ = r3c3.summarize_control.__kwdefaults__
    return summarize(ctx, results, selected_pairs)


def summarize_control(
    ctx: Stage42R3C3T1Context,
    results: Sequence[Mapping[str, Any]],
    selected_pairs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    summary = _summarize_transport_responses(
        ctx, results, selected_pairs
    )
    combined = _combined_condition_rows(ctx, results)
    combined_pass_count = sum(
        bool(row["condition_number_pass"]) for row in combined
    )
    combined_max = (
        max(
            float(row["selected_velocity_condition_number"])
            for row in combined
            if row["selected_velocity_condition_number"] is not None
        )
        if any(
            row["selected_velocity_condition_number"] is not None
            for row in combined
        )
        else None
    )
    expected = int(
        ctx.cfg["control_matrix"]["expected_baseline_contexts"]
    )
    combined_pass = bool(
        len(combined) == expected and combined_pass_count == expected
    )
    summary.update(
        {
            "stage": STAGE,
            "phase": (
                "long_separation_zero_net_transport_identification"
            ),
            "expected_combined_condition_group_count": expected,
            "combined_condition_group_count": len(combined),
            "combined_condition_pass_count": combined_pass_count,
            "combined_condition_failure_count": (
                len(combined) - combined_pass_count
            ),
            "maximum_combined_velocity_condition_number": combined_max,
            "combined_condition_number_gate_passed": combined_pass,
        }
    )
    summary["passed"] = bool(summary["passed"] and combined_pass)
    r3c3.atomic_write_json(
        ctx.paths.control / "combined_condition_number_results.json",
        combined,
    )
    r3c3.write_csv(
        ctx.paths.control / "combined_condition_number_results.csv",
        combined,
    )
    r3c3.atomic_write_json(ctx.paths.control / "summary.json", summary)
    return summary


def _package_files(ctx: Stage42R3C3T1Context) -> list[Path]:
    names = [
        "PACKAGE_MANIFEST.json",
        "SHA256SUMS",
        (
            "configs/stage4_2r3c3t1_long_separation_zero_net_"
            "transport_identification_370ms.json"
        ),
        (
            "tsc_rzip_rllib/diagnostics/"
            "stage4_2r3c3t1_long_separation_zero_net_"
            "transport_identification.py"
        ),
        (
            "tsc_rzip_rllib/diagnostics/"
            "stage4_2r3c3_restart_task_clock_local_response_"
            "identification.py"
        ),
        "scripts/stage4_2r3c3_shell_common.sh",
        (
            "scripts/stage4_2r3c3t1_long_separation_zero_net_"
            "transport_identification.py"
        ),
        "scripts/stage4_2r3c3t1_shell_common.sh",
        "scripts/stage4_2r3c3t1_server_postprocess.py",
        (
            "tests/test_stage4_2r3c3t1_long_separation_zero_net_"
            "transport_identification.py"
        ),
        (
            "run_stage4_2r3c3t1_long_separation_zero_net_"
            "transport_identification_native.sh"
        ),
        (
            "run_stage4_2r3c3t1_long_separation_zero_net_"
            "transport_identification_nohup.sh"
        ),
        "run_stage4_2r3c3t1_self_test.sh",
        "run_stage4_2r3c3t1_server_postprocess.sh",
        "run_stage4_2r3c3t1_verify_package.sh",
        "run_stop_stage4_2r3c3t1_now.sh",
    ]
    return [ctx.project_dir / name for name in names]


def _deployed_package_fingerprint(
    ctx: Stage42R3C3T1Context,
) -> dict[str, Any]:
    rows = []
    for path in _package_files(ctx):
        if not path.is_file():
            raise FileNotFoundError(f"package file missing: {path}")
        rows.append(
            {
                "path": path.relative_to(ctx.project_dir).as_posix(),
                "size_bytes": int(path.stat().st_size),
                "sha256": _sha256(path),
            }
        )
    return {
        "schema_version": 1,
        "contract": "r42r3c3t1_deployed_package_source_v1",
        "n_files": len(rows),
        "digest": _canonical_digest(rows),
        "files": rows,
    }


def _prepare_dirs(paths: Stage42R3C3T1Paths) -> None:
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
    ctx: Stage42R3C3T1Context, *, resume: bool
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    _prepare_dirs(ctx.paths)
    selected_pairs, _ = r3c3._recompute_selected_pairs(ctx.base_ctx)
    specs = build_control_specs(ctx, selected_pairs)
    package_fingerprint = _deployed_package_fingerprint(ctx)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "source_stage4_2r3c3_run": str(ctx.source_r3c3_run),
        "source_stage4_2r3c3_bank_dir": str(ctx.source_bank_dir),
        "source_stage4_2r3c3_bank_fingerprint": (
            ctx.source_bank_fingerprint
        ),
        "source_stage4_2r3b_run": str(ctx.source_r3b_run),
        "source_fingerprint": ctx.source_fingerprint,
        "source_stage4_2r3c_run": str(ctx.source_r3c_run),
        "source_stage4_2r3c_fingerprint": (
            ctx.source_r3c_fingerprint
        ),
        "source_stage4_2r3c1_run": str(ctx.source_r3c1_run),
        "source_stage4_2r3c1_fingerprint": (
            ctx.source_r3c1_fingerprint
        ),
        "source_stage4_2r3c2_run": str(ctx.source_r3c2_run),
        "source_stage4_2r3c2_fingerprint": (
            ctx.source_r3c2_fingerprint
        ),
        "deployed_package_fingerprint": package_fingerprint,
        "config_digest": _canonical_digest(ctx.cfg),
        "control_spec_digest": _canonical_digest(specs),
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
    if ctx.paths.manifest.is_file():
        if not resume:
            raise FileExistsError(
                "Stage4.2R3c3T1 run exists; use resume or a fresh run"
            )
        old = r3c3.read_json(ctx.paths.manifest)
        for key in (
            "stage",
            "controller_revision",
            "package_revision",
            "source_stage4_2r3c3_run",
            "source_stage4_2r3c3_bank_dir",
            "source_stage4_2r3c3_bank_fingerprint",
            "source_stage4_2r3b_run",
            "source_fingerprint",
            "source_stage4_2r3c_run",
            "source_stage4_2r3c_fingerprint",
            "source_stage4_2r3c1_run",
            "source_stage4_2r3c1_fingerprint",
            "source_stage4_2r3c2_run",
            "source_stage4_2r3c2_fingerprint",
            "deployed_package_fingerprint",
            "config_digest",
            "control_spec_digest",
            "phase_alignment",
            "identification_probe",
            "formal_timing_contract",
            "control_matrix",
        ):
            if old.get(key) != manifest.get(key):
                raise ValueError(
                    "Stage4.2R3c3T1 resume incompatibility in "
                    f"manifest field {key}"
                )
    else:
        r3c3.atomic_write_json(ctx.paths.manifest, manifest)
    r3c3.atomic_write_json(
        ctx.paths.run_dir / "stage4_2r3c3t1_config.resolved.json",
        ctx.cfg,
    )
    r3c3.atomic_write_json(
        ctx.paths.source_reference
        / "stage4_2r3c3_bank_fingerprint.json",
        ctx.source_bank_fingerprint,
    )
    r3c3.atomic_write_json(
        ctx.paths.source_reference / "control_specs.json", specs
    )
    r3c3.atomic_write_json(
        ctx.paths.source_reference
        / "deployed_package_fingerprint.json",
        package_fingerprint,
    )
    state = (
        r3c3.read_json(ctx.paths.state)
        if ctx.paths.state.is_file()
        else {
            "schema_version": SCHEMA_VERSION,
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
    state["updated_utc"] = r3c3.utc_timestamp()
    r3c3.atomic_write_json(ctx.paths.state, state)
    return list(selected_pairs), specs


def run_offline_probe_audit(
    ctx: Stage42R3C3T1Context,
    selected_pairs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    specs = build_control_specs(ctx, selected_pairs)
    library, bundle, selector = r1._library_bundle_selector(
        ctx.source_ctx.r1_ctx
    )
    baseline_dir = (
        ctx.source_r3c1_run
        / "stage4_2r3c1_authenticated_visible_manifold_control"
        / "raw"
    )
    grouped: dict[tuple[Any, ...], list[Mapping[str, Any]]] = (
        defaultdict(list)
    )
    schedule_rows = []
    for spec in specs:
        schedule = {
            int(step): np.asarray(value, dtype=float).reshape(N_MODES)
            for step, value in spec[
                "r3c3_probe_delta_by_task_issue_step"
            ].items()
        }
        net = np.sum(np.stack(list(schedule.values())), axis=0)
        mode = int(spec["r3c3_probe_mode"])
        amplitude = float(spec["r3c3_probe_amplitude"])
        schedule_exact = bool(
            len(schedule) == 12
            and np.array_equal(net, np.zeros(N_MODES, dtype=float))
            and min(schedule)
            + int(spec["action_delay_steps"])
            + 1
            == 3
            and all(
                np.count_nonzero(value) == 1
                and math.isclose(
                    abs(float(value[mode])),
                    amplitude,
                    rel_tol=0.0,
                    abs_tol=1.0e-15,
                )
                for value in schedule.values()
            )
            and not r3c3._FORBIDDEN_CONTROLLER_SPEC_KEYS.intersection(
                _controller_spec(spec)
            )
        )
        schedule_rows.append(
            {
                "experiment_id": str(spec["experiment_id"]),
                "probe_id": str(spec["r3c3_probe_id"]),
                "probe_sign": int(spec["r3c3_probe_sign"]),
                "actual_delay_steps": int(
                    spec["action_delay_steps"]
                ),
                "issue_steps": sorted(schedule),
                "requested_net": net.tolist(),
                "schedule_exact": schedule_exact,
            }
        )
        key = (
            str(spec["pair_id"]),
            str(spec["history_member"]),
            str(spec["target_id"]),
            int(spec["action_delay_steps"]),
            float(spec["slew_scale"]),
        )
        grouped[key].append(spec)
    action_rows = []
    for index, key in enumerate(sorted(grouped)):
        context_specs = grouped[key]
        baseline_id = str(context_specs[0]["baseline_experiment_id"])
        baseline = r3c3.read_json_gz(
            baseline_dir / f"{baseline_id}.json.gz"
        )
        initial = copy.deepcopy(dict(baseline["trajectory"][0]))
        initial["step_index"] = 0
        payload = _control_payload(ctx, spec=context_specs[0])
        plant = r1.LocalPlantReplayWorker(
            payload,
            library,
            bundle,
            f"stage42r3c3t1_offline_{index:03d}",
            selector,
        )
        try:
            baseline_controller = (
                r3c1.AuthenticatedVisibleManifoldPhaseTaskController(
                    plant.base_worker,
                    bundle,
                    _controller_spec(context_specs[0]),
                    initial,
                )
            )
            baseline_action, _ = baseline_controller.action(initial)
            recorded_action = np.asarray(
                baseline["trajectory"][1]["action_norm_tsc"],
                dtype=float,
            )
            zero_spec = _controller_spec(context_specs[0])
            zero_spec["r3c3_probe_delta_by_task_issue_step"] = {
                step: np.zeros(N_MODES).tolist()
                for step in zero_spec[
                    "r3c3_probe_delta_by_task_issue_step"
                ]
            }
            zero_controller = LongSeparationTransportProbeController(
                plant.base_worker, bundle, zero_spec, initial
            )
            zero_action, _ = zero_controller.action(initial)
            baseline_exact = bool(
                np.array_equal(baseline_action, recorded_action)
                and np.array_equal(zero_action, baseline_action)
            )
            for spec in context_specs:
                sanitized = _controller_spec(spec)
                controller = LongSeparationTransportProbeController(
                    plant.base_worker, bundle, sanitized, initial
                )
                action, trace = controller.action(initial)
                hidden = copy.deepcopy(initial)
                hidden["wire_currents_a"] = [
                    float(wire + 1) * 1.0e9
                    for wire in range(N_WIRES)
                ]
                hidden_controller = (
                    LongSeparationTransportProbeController(
                        plant.base_worker, bundle, sanitized, hidden
                    )
                )
                hidden_action, hidden_trace = hidden_controller.action(
                    hidden
                )
                expected_issued = (
                    int(spec["action_delay_steps"]) == 2
                )
                passed = bool(
                    baseline_exact
                    and np.all(np.isfinite(action))
                    and np.array_equal(action, hidden_action)
                    and bool(trace["r3c3_probe_issued"])
                    == expected_issued
                    and bool(hidden_trace["r3c3_probe_issued"])
                    == expected_issued
                    and int(trace["measurement_max_state_index_used"]) == 0
                    and not bool(trace["future_measurement_used"])
                    and not bool(trace["hidden_wire_used"])
                    and not bool(trace["source_action_used"])
                    and not bool(trace["source_result_used"])
                    and not bool(trace["pair_or_history_label_used"])
                )
                action_rows.append(
                    {
                        "experiment_id": str(spec["experiment_id"]),
                        "baseline_first_action_exact": baseline_exact,
                        "finite_first_action": bool(
                            np.all(np.isfinite(action))
                        ),
                        "hidden_wire_invariant": bool(
                            np.array_equal(action, hidden_action)
                        ),
                        "probe_issue_at_step_zero_expected": (
                            expected_issued
                        ),
                        "probe_issue_at_step_zero_actual": bool(
                            trace["r3c3_probe_issued"]
                        ),
                        "passed": passed,
                    }
                )
        finally:
            plant.close()
    expected = int(ctx.cfg["control_matrix"]["expected_rollouts"])
    raw_count = len(list((ctx.paths.control / "raw").glob("*.json.gz")))
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "offline_transport_probe_audit",
        "expected_probe_specs": expected,
        "probe_spec_count": len(schedule_rows),
        "probe_schedule_exact_count": sum(
            bool(row["schedule_exact"]) for row in schedule_rows
        ),
        "finite_causal_action_count": sum(
            bool(row["passed"]) for row in action_rows
        ),
        "baseline_context_count": len(grouped),
        "baseline_first_action_exact_count": sum(
            bool(row["baseline_first_action_exact"])
            for row in action_rows[::4]
        ),
        "hidden_wire_invariant_action_count": sum(
            bool(row["hidden_wire_invariant"]) for row in action_rows
        ),
        "future_action_read_count": 0,
        "future_measurement_use_count": 0,
        "pair_or_history_label_controller_input_count": 0,
        "source_result_controller_input_count": 0,
        "raw_count": raw_count,
        "plant_advance_count": 0,
        "real_tsc_executed": False,
    }
    summary["passed"] = bool(
        len(schedule_rows) == expected
        and summary["probe_schedule_exact_count"] == expected
        and len(action_rows) == expected
        and summary["finite_causal_action_count"] == expected
        and len(grouped) == 32
        and summary["hidden_wire_invariant_action_count"] == expected
        and raw_count == 0
    )
    r3c3.atomic_write_json(
        ctx.paths.source_reference
        / "offline_transport_probe_audit.json",
        {
            "summary": summary,
            "probe_schedules": schedule_rows,
            "first_actions": action_rows,
        },
    )
    return summary


def analyze(
    ctx: Stage42R3C3T1Context,
    control_summary: Mapping[str, Any],
) -> dict[str, Any]:
    primary_pass = bool(control_summary.get("passed"))
    verdict = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "verdict": (
            "STAGE4_2R3C3T1_TRANSPORT_IDENTIFICATION_PASS"
            if primary_pass
            else "STAGE4_2R3C3T1_TRANSPORT_IDENTIFICATION_FAIL"
        ),
        "primary_pass": primary_pass,
        "identification_only": True,
        "formal_tracking_is_acceptance_gate": False,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "development_set_only": True,
        "independent_hidden_history_confirmation": False,
        "bc_dagger_or_rl_allowed": False,
        "next_if_pass": (
            "Build a combined six-basis compact bank and require 32/32 "
            "bounded optimistic R3c4 feasibility before implementation."
        ),
        "next_if_fail": (
            "Preserve all raw and redesign transport identification "
            "without weakening timing or response gates."
        ),
    }
    r3c3.atomic_write_json(
        ctx.paths.analysis / "stage4_2r3c3t1_summary.json",
        dict(control_summary),
    )
    r3c3.atomic_write_json(
        ctx.paths.analysis / "stage4_2r3c3t1_verdict.json",
        verdict,
    )
    state = r3c3.read_json(ctx.paths.state)
    state.update(
        {
            "finished": True,
            "primary_pass": primary_pass,
            "phase_status": "campaign_complete",
            "stop_reason": "" if primary_pass else "identification_gate_failed",
            "verdict": verdict,
            "updated_utc": r3c3.utc_timestamp(),
        }
    )
    r3c3.atomic_write_json(ctx.paths.state, state)
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "control_summary": dict(control_summary),
        "verdict": verdict,
    }


def execute(
    ctx: Stage42R3C3T1Context,
    *,
    command: str,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    selected_pairs, specs = prepare(ctx, resume=resume)
    offline = run_offline_probe_audit(ctx, selected_pairs)
    if not bool(offline.get("passed")):
        raise RuntimeError(
            "Stage4.2R3c3T1 offline gate failed; no real TSC started"
        )
    if command == "offline":
        state = r3c3.read_json(ctx.paths.state)
        state.update(
            {
                "finished": False,
                "primary_pass": False,
                "phase_status": "offline_gate_complete",
                "stop_reason": "",
                "offline_probe_audit": dict(offline),
                "updated_utc": r3c3.utc_timestamp(),
            }
        )
        r3c3.atomic_write_json(ctx.paths.state, state)
        return {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "phase": "offline_transport_probe_audit",
            "offline_probe_audit": dict(offline),
            "real_tsc_executed": False,
            "finished": False,
            "primary_pass": False,
        }
    results = _evaluate_control(
        ctx, specs, backend=backend, resume=resume
    )
    summary = summarize_control(ctx, results, selected_pairs)
    return analyze(ctx, summary)


def self_test() -> dict[str, Any]:
    basis = {
        "mode": 0,
        "first_effect_state": 3,
        "effect_offsets": [
            0,
            1,
            2,
            3,
            4,
            5,
            12,
            13,
            14,
            15,
            16,
            17,
        ],
        "sign_pattern": [
            1,
            1,
            1,
            1,
            1,
            1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
        ],
    }
    delay0 = _probe_schedule(
        basis=basis,
        actual_delay=0,
        sign=1,
        amplitude_by_mode=[0.0075, 0.0075, 0.0],
    )
    delay2 = _probe_schedule(
        basis=basis,
        actual_delay=2,
        sign=1,
        amplitude_by_mode=[0.0075, 0.0075, 0.0],
    )
    net0 = np.sum(np.stack(list(delay0.values())), axis=0)
    net2 = np.sum(np.stack(list(delay2.values())), axis=0)
    passed = bool(
        sorted(delay0)
        == [2, 3, 4, 5, 6, 7, 14, 15, 16, 17, 18, 19]
        and sorted(delay2)
        == [0, 1, 2, 3, 4, 5, 12, 13, 14, 15, 16, 17]
        and np.array_equal(net0, np.zeros(N_MODES))
        and np.array_equal(net2, np.zeros(N_MODES))
        and max(
            float(np.max(np.abs(value))) for value in delay0.values()
        )
        == 0.0075
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "delay0_issue_steps": sorted(delay0),
        "delay2_issue_steps": sorted(delay2),
        "delay0_requested_net": net0.tolist(),
        "delay2_requested_net": net2.tolist(),
        "identification_only": True,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "formal_timing_unchanged": True,
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
            "Stage4.2R3c3T1 long-separation zero-net transport "
            "identification"
        )
    )
    parser.add_argument("--config", type=Path)
    parser.add_argument("--source-stage4-2r3b-run", type=Path)
    parser.add_argument("--source-stage4-2r3c3-run", type=Path)
    parser.add_argument("--source-stage4-2r3c3-bank-dir", type=Path)
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
            ("--source-stage4-2r3c3-run", args.source_stage4_2r3c3_run),
            (
                "--source-stage4-2r3c3-bank-dir",
                args.source_stage4_2r3c3_bank_dir,
            ),
            ("--run-dir", args.run_dir),
        )
        if value is None
    ]
    if missing:
        parser.error(
            "missing required arguments: " + ", ".join(missing)
        )
    ctx = load_stage42r3c3t1_config(
        args.config,
        source_stage42r3b_run=args.source_stage4_2r3b_run,
        source_stage42r3c3_run=args.source_stage4_2r3c3_run,
        source_stage42r3c3_bank_dir=(
            args.source_stage4_2r3c3_bank_dir
        ),
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
