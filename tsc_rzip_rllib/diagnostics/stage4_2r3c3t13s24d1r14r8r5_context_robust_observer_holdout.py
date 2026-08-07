"""Frozen contract for the D1R14R8R5 context-robust observer holdout."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


STAGE = "Stage4.2R3c3T13S24D1R14R8R5"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r5_context_robust_observer_holdout"
IDENTITY = "context_robust_causal_observer_holdout_v1"
CONTROLLER_REVISION = (
    "inherited_exact_card15_zero_after_prefix_v42r3c3t13s24d1r14r8r5_v1"
)
PACKAGE_REVISION = "r42r3c3t13s24d1r14r8r5_context_robust_observer_v1"
DESIGN_SHA256 = "c7b5d570a6d74b39368e4ee4ef677f84a7a81b469a000515ea843e2797622daa"

HOLDOUT_PAIRS = (
    "p5_q1_a0p750_gap4_settle4",
    "p5_q2_a0p900_gap4_settle4",
    "p9_q1_a0p750_gap4_settle4",
    "p9_q2_a0p900_gap4_settle4",
)


def _read(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_config(cfg: Mapping[str, Any], *, project_root: Path | None = None) -> None:
    if (
        int(cfg.get("schema_version", -1)) != 1
        or cfg.get("stage") != STAGE
        or cfg.get("run_name") != RUN_NAME
        or cfg.get("campaign_identity") != IDENTITY
        or cfg.get("controller_revision") != CONTROLLER_REVISION
        or cfg.get("package_revision") != PACKAGE_REVISION
        or cfg.get("design_document_sha256") != DESIGN_SHA256
    ):
        raise ValueError("R8R5 frozen identity changed")
    if project_root is not None:
        root = project_root.resolve()
        for key, expected in (
            ("design_document", DESIGN_SHA256),
            ("source_r8_config", str(cfg["source_r8_config_sha256"])),
            ("source_r8r3_config", str(cfg["source_r8r3_config_sha256"])),
            ("source_r8r4_config", str(cfg["source_r8r4_config_sha256"])),
        ):
            if _sha((root / str(cfg[key])).resolve()) != expected:
                raise ValueError(f"R8R5 {key} hash changed")
    if tuple(map(str, cfg.get("holdout_pairs") or ())) != HOLDOUT_PAIRS:
        raise ValueError("R8R5 holdout pairs changed")
    rollout = cfg.get("rollout_contract") or {}
    if (
        int(rollout.get("development_new_rollouts", -1)) != 0
        or int(rollout.get("holdout_pairs", -1)) != 4
        or int(rollout.get("histories_per_pair", -1)) != 2
        or int(rollout.get("holdout_rollouts", -1)) != 8
        or int(rollout.get("maximum_new_rollouts", -1)) != 8
        or rollout.get("baseline_role_only") is not True
        or int(rollout.get("delegated_last_task_step", -1)) != 9
        or int(rollout.get("zero_action_first_task_step", -1)) != 10
    ):
        raise ValueError("R8R5 rollout contract changed")
    bank = cfg.get("bank_contract") or {}
    if (
        tuple(map(float, bank.get("visible_scales") or ()))
        != (0.03, 0.03, 0.1, 0.1, 10000.0)
        or float(bank.get("dt_s", -1.0)) != 0.01
        or int(bank.get("coil_count", -1)) != 14
        or int(bank.get("first_origin_task_step", -1)) != 10
        or int(bank.get("future_state_count", -1)) != 12
        or tuple(map(int, bank.get("prescribed_issue_task_steps") or ()))
        != (10, 14, 18, 22)
        or int(bank.get("feature_dimension", -1)) != 353
        or int(bank.get("development_pair_count", -1)) != 16
        or int(bank.get("holdout_pair_count", -1)) != 4
    ):
        raise ValueError("R8R5 bank contract changed")
    model = cfg.get("fixed_model_contract") or {}
    implementation_model = cfg.get("model_contract") or {}
    if (
        model.get("family") != "linear"
        or int(model.get("pca_rank", -1)) != 32
        or float(model.get("ridge", -1.0)) != 1e-6
        or float(model.get("bandwidth_multiplier", -1.0)) != 0.0
        or model.get("whole_pair_fixed_candidate_validation") is not True
        or bool(model.get("candidate_selection_allowed"))
        or bool(model.get("final_all_data_fit_is_validation"))
        or tuple(map(int, implementation_model.get("pca_ranks") or ())) != (32,)
        or tuple(implementation_model.get("rbf_median_distance_multipliers") or ())
        or tuple(map(float, implementation_model.get("kernel_ridges") or ()))
        != (1e-6,)
        or int(implementation_model.get("candidate_count", -1)) != 1
    ):
        raise ValueError("R8R5 fixed point model changed")
    tube = cfg.get("tube_contract") or {}
    gates = cfg.get("gates") or {}
    if (
        tube.get("method") != "context_robust_global_higher_quantile_scaled"
        or float(tube.get("base_absolute_residual_quantile", -1.0)) != 0.95
        or float(tube.get("aggregate_row_ratio_quantile", -1.0)) != 0.95
        or float(tube.get("per_context_row_ratio_quantile", -1.0)) != 0.90
        or float(tube.get("blind_holdout_reserve_multiplier", -1.0)) != 1.25
        or float(tube.get("scalar_floor", -1.0)) != 1.0
        or tuple(map(float, tube.get("component_caps_physical") or ()))
        != (0.01, 0.01, 0.05, 0.05, 3000.0)
        or tuple(map(float, gates.get("component_caps_physical") or ()))
        != (0.003, 0.003, 0.02, 0.02, 1000.0)
        or float(gates.get("aggregate_point_pass_rate", -1.0)) != 0.95
        or float(gates.get("per_context_point_pass_rate", -1.0)) != 0.90
        or float(gates.get("aggregate_tube_containment_rate", -1.0)) != 0.95
        or float(gates.get("per_context_tube_containment_rate", -1.0)) != 0.90
    ):
        raise ValueError("R8R5 context-robust qualification changed")
    timing = cfg.get("formal_timing_contract") or {}
    if (
        int(timing.get("normal_arrival_deadline_step", -1)) != 25
        or int(timing.get("normal_hold_through_step", -1)) != 35
        or int(timing.get("weak_arrival_deadline_step", -1)) != 27
        or int(timing.get("weak_hold_through_step", -1)) != 37
        or float(timing.get("position_tolerance_m", -1.0)) != 0.03
        or float(timing.get("speed_tolerance_m_per_s", -1.0)) != 0.1
        or float(timing.get("ip_tolerance_A", -1.0)) != 10000.0
        or int(timing.get("arrival_streak_steps", -1)) != 3
        or bool(timing.get("arrival_deadline_expansion_allowed"))
    ):
        raise ValueError("R8R5 formal timing changed")
    if (
        cfg.get("identification_only") is not True
        or bool(cfg.get("probe_trajectories_allowed_in_expert_dataset"))
        or bool(cfg.get("all_stage_trajectories_allowed_in_expert_dataset"))
        or bool(cfg.get("mpc_validated"))
        or bool(cfg.get("bc_dagger_or_rl_allowed"))
    ):
        raise ValueError("R8R5 learning boundary changed")


def self_test(config_path: Path) -> dict[str, Any]:
    path = config_path.expanduser().resolve()
    cfg = _read(path)
    validate_config(cfg, project_root=path.parents[1])
    return {
        "schema_version": 1,
        "stage": STAGE,
        "campaign_identity": IDENTITY,
        "development_new_rollout_count": 0,
        "holdout_rollout_count": 8,
        "fixed_candidate": cfg["fixed_model_contract"],
        "design_sha256": DESIGN_SHA256,
        "real_tsc_executed": False,
        "passed": True,
    }
