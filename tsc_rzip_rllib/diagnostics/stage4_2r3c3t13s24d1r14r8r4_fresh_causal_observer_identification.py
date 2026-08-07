"""Frozen contract for the D1R14R8R4 fresh causal observer campaign."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


STAGE = "Stage4.2R3c3T13S24D1R14R8R4"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r4_fresh_causal_observer_identification"
IDENTITY = "fresh_baseline_causal_no_action_observer_v1"
CONTROLLER_REVISION = (
    "inherited_exact_card15_zero_after_prefix_v42r3c3t13s24d1r14r8r4_v1"
)
PACKAGE_REVISION = "r42r3c3t13s24d1r14r8r4_fresh_causal_observer_v1"
DESIGN_SHA256 = "942b7698e9d19ee905d75dc7ee9fda370e642e9e986298af32d8f17ed22f8119"

DEVELOPMENT_PAIRS = (
    "p5_q1_a0p900_gap3_settle4",
    "p5_q2_a0p750_gap3_settle4",
    "p9_q1_a0p900_gap3_settle4",
    "p9_q2_a0p750_gap3_settle4",
)
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


def _sha256(path: Path) -> str:
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
        raise ValueError("R8R4 frozen identity changed")
    if project_root is not None:
        root = project_root.resolve()
        design = (root / str(cfg["design_document"])).resolve()
        source_r8 = (root / str(cfg["source_r8_config"])).resolve()
        source_r8r3 = (root / str(cfg["source_r8r3_config"])).resolve()
        if (
            _sha256(design) != DESIGN_SHA256
            or _sha256(source_r8) != str(cfg["source_r8_config_sha256"])
            or _sha256(source_r8r3) != str(cfg["source_r8r3_config_sha256"])
        ):
            raise ValueError("R8R4 design or source config hash changed")

    partitions = cfg.get("pair_partitions") or {}
    if (
        tuple(map(str, partitions.get("development") or ())) != DEVELOPMENT_PAIRS
        or tuple(map(str, partitions.get("holdout") or ())) != HOLDOUT_PAIRS
        or set(DEVELOPMENT_PAIRS) & set(HOLDOUT_PAIRS)
    ):
        raise ValueError("R8R4 pair partition changed")

    rollout = cfg.get("rollout_contract") or {}
    if (
        int(rollout.get("histories_per_pair", -1)) != 2
        or int(rollout.get("development_pairs", -1)) != 4
        or int(rollout.get("development_rollouts", -1)) != 8
        or int(rollout.get("holdout_pairs", -1)) != 4
        or int(rollout.get("holdout_rollouts", -1)) != 8
        or int(rollout.get("maximum_new_rollouts", -1)) != 16
        or rollout.get("baseline_role_only") is not True
        or int(rollout.get("delegated_last_task_step", -1)) != 9
        or int(rollout.get("zero_action_first_task_step", -1)) != 10
    ):
        raise ValueError("R8R4 rollout contract changed")

    bank = cfg.get("bank_contract") or {}
    if (
        tuple(map(float, bank.get("visible_scales") or ()))
        != (0.03, 0.03, 0.1, 0.1, 10000.0)
        or tuple(map(float, bank.get("target_scales") or ()))
        != (0.03, 0.03, 10000.0)
        or float(bank.get("dt_s", -1.0)) != 0.01
        or int(bank.get("coil_count", -1)) != 14
        or int(bank.get("first_origin_task_step", -1)) != 10
        or int(bank.get("future_state_count", -1)) != 12
        or tuple(map(int, bank.get("prescribed_issue_task_steps") or ()))
        != (10, 14, 18, 22)
        or int(bank.get("feature_dimension", -1)) != 353
        or int(bank.get("development_combined_pair_count", -1)) != 16
        or int(bank.get("holdout_pair_count", -1)) != 4
    ):
        raise ValueError("R8R4 observer bank contract changed")

    feature = cfg.get("feature_contract") or {}
    if (
        tuple(map(int, feature.get("visible_state_offsets") or ()))
        != tuple(range(-10, 1))
        or tuple(map(int, feature.get("issued_action_offsets") or ()))
        != tuple(range(-10, 0))
        or tuple(map(int, feature.get("applied_current_offsets") or ()))
        != tuple(range(-10, 1))
        or int(feature.get("relative_clock_origin", -1)) != 10
        or float(feature.get("relative_clock_scale", -1.0)) != 15.0
    ):
        raise ValueError("R8R4 causal feature contract changed")

    model = cfg.get("model_contract") or {}
    if (
        tuple(map(int, model.get("pca_ranks") or ())) != (32, 48, 64, 96)
        or tuple(map(float, model.get("rbf_median_distance_multipliers") or ()))
        != (0.5, 1.0, 2.0)
        or tuple(map(float, model.get("kernel_ridges") or ()))
        != (1e-6, 1e-4, 1e-2)
        or int(model.get("candidate_count", -1)) != 48
        or model.get("nested_whole_pair_selection") is not True
        or bool(model.get("final_all_data_fit_is_validation"))
    ):
        raise ValueError("R8R4 candidate family changed")

    tube = cfg.get("tube_contract") or {}
    gates = cfg.get("gates") or {}
    if (
        tube.get("method") != "higher_quantile_scaled"
        or float(tube.get("base_absolute_residual_quantile", -1.0)) != 0.95
        or float(tube.get("row_ratio_quantile", -1.0)) != 0.95
        or tuple(map(float, tube.get("component_caps_physical") or ()))
        != (0.01, 0.01, 0.05, 0.05, 3000.0)
        or tuple(map(float, gates.get("component_caps_physical") or ()))
        != (0.003, 0.003, 0.02, 0.02, 1000.0)
        or tuple(map(float, gates.get("finite_exclusion_caps_physical") or ()))
        != (0.01, 0.01, 0.05, 0.05, 3000.0)
        or float(gates.get("aggregate_point_pass_rate", -1.0)) != 0.95
        or float(gates.get("per_context_point_pass_rate", -1.0)) != 0.90
        or float(gates.get("aggregate_tube_containment_rate", -1.0)) != 0.95
        or float(gates.get("per_context_tube_containment_rate", -1.0)) != 0.90
    ):
        raise ValueError("R8R4 practical qualification gates changed")

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
        raise ValueError("R8R4 formal timing changed")
    if (
        cfg.get("identification_only") is not True
        or bool(cfg.get("probe_trajectories_allowed_in_expert_dataset"))
        or bool(cfg.get("all_stage_trajectories_allowed_in_expert_dataset"))
        or bool(cfg.get("mpc_validated"))
        or bool(cfg.get("bc_dagger_or_rl_allowed"))
    ):
        raise ValueError("R8R4 learning boundary changed")


def self_test(config_path: Path) -> dict[str, Any]:
    path = config_path.expanduser().resolve()
    cfg = _read(path)
    validate_config(cfg, project_root=path.parents[1])
    return {
        "schema_version": 1,
        "stage": STAGE,
        "campaign_identity": IDENTITY,
        "development_pair_count": len(DEVELOPMENT_PAIRS),
        "holdout_pair_count": len(HOLDOUT_PAIRS),
        "prospective_rollout_count": int(
            cfg["rollout_contract"]["maximum_new_rollouts"]
        ),
        "candidate_count": int(cfg["model_contract"]["candidate_count"]),
        "design_sha256": DESIGN_SHA256,
        "real_tsc_executed": False,
        "passed": True,
    }
