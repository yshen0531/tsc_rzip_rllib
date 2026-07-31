#!/usr/bin/env python3
"""Stage4.2R3c3T9 PC3 and direct mixed-interaction identification.

The runtime reuses the already validated T6 plant/restart execution machinery
through an explicit process-local adapter.  T6 source files and experiment
identities are not modified.  T9 has independent specs, fingerprints, raw
files, summaries, and verdicts.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t1_long_separation_zero_net_transport_identification as t1,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t2_post_contract_neutralized_held_transport_identification as t2,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t6_target_residual_new_direction_identification as t6,
)


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T9"
CONTROLLER_REVISION = "pc3_mixed_interaction_probe_v42r3c3t9_v1"
PACKAGE_REVISION = "r42r3c3t9_pc3_mixed_interaction_identification_v1"
RUN_NAME = "stage4_2r3c3t9_pc3_mixed_interaction_identification"
OBSERVATION_HORIZON = 50
BASELINE_PROBE_ID = "pc3_mixed_interaction_baseline"
PC3_PROBE_ID = "matched_visible_target_equal_pc3"
FACTORIAL_PROBE_IDS = (
    "stress_plus_pc3_plus",
    "stress_plus_pc3_minus",
    "stress_minus_pc3_plus",
    "stress_minus_pc3_minus",
)
NONBASELINE_PROBE_IDS = (PC3_PROBE_ID, *FACTORIAL_PROBE_IDS)
FACTORIAL_SIGNS = ((1, 1), (1, -1), (-1, 1), (-1, -1))
N_MODES = t1.N_MODES
N_COILS = t1.N_COILS
_ORIGINAL_T6_CONTROLLER = t6.TargetResidualNewDirectionProbeController


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_digest(value: Any) -> str:
    return t1._canonical_digest(value)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _formal_horizon(slew: float) -> int:
    return t2._formal_horizon(slew)


@dataclass(frozen=True)
class Stage42R3C3T9Paths:
    run_dir: Path
    control: Path
    raw: Path
    variants: Path
    source_reference: Path
    analysis: Path
    manifest: Path
    state: Path


@dataclass(frozen=True)
class Stage42R3C3T9Context:
    cfg: dict[str, Any]
    base_config_path: Path
    base_ctx: t2.Stage42R3C3T2Context
    preflight_path: Path
    preflight: dict[str, Any]
    t7_controller_bank_path: Path
    paths: Stage42R3C3T9Paths


def _paths(run_dir: Path) -> Stage42R3C3T9Paths:
    root = run_dir.expanduser().resolve()
    control = root / "stage4_2r3c3t9_pc3_mixed_interaction"
    return Stage42R3C3T9Paths(
        run_dir=root,
        control=control,
        raw=control / "raw",
        variants=root / "stage4_2r3c3t9_environment_variants",
        source_reference=root / "stage4_2r3c3t9_source_reference",
        analysis=root / "stage4_2r3c3t9_analysis",
        manifest=root / "stage4_2r3c3t9_manifest.json",
        state=root / "stage4_2r3c3t9_state.json",
    )


def _validate_config(cfg: Mapping[str, Any]) -> None:
    if (
        cfg.get("stage") != STAGE
        or int(cfg.get("design_revision", -1)) != 1
        or cfg.get("run_name") != RUN_NAME
        or cfg.get("controller_revision") != CONTROLLER_REVISION
        or cfg.get("package_revision") != PACKAGE_REVISION
    ):
        raise ValueError("Stage4.2R3c3T9 identity changed")
    probe = cfg["identification_probe"]
    matrix = cfg["control_matrix"]
    if (
        int(probe["observation_horizon_steps"]) != OBSERVATION_HORIZON
        or probe["standalone_probe_id"] != PC3_PROBE_ID
        or tuple(probe["factorial_probe_ids"]) != FACTORIAL_PROBE_IDS
        or tuple(tuple(row) for row in probe["factorial_signs"])
        != FACTORIAL_SIGNS
        or probe["extended_baseline_probe_id"] != BASELINE_PROBE_ID
        or int(probe["required_issue_count_per_nonbaseline_probe"]) != 41
        or list(map(int, probe["cancellation_effect_states"]))
        != [39, 40, 41, 42, 43, 44]
        or float(probe["maximum_formal_schedule_l2"]) != 0.015
        or float(probe["maximum_schedule_component_abs"]) != 0.0075
        or float(probe["maximum_current_utilization"]) != 0.55
        or float(
            probe["maximum_selected_nine_velocity_condition_number"]
        )
        != 25.0
        or float(
            probe[
                "maximum_mixed_velocity_norm_ratio_for_linear_route"
            ]
        )
        != 0.1
        or float(
            probe[
                "maximum_pc3_main_effect_modulation_ratio_for_linear_route"
            ]
        )
        != 0.1
    ):
        raise ValueError("Stage4.2R3c3T9 probe contract changed")
    if (
        int(matrix["expected_rollouts"]) != 224
        or int(matrix["expected_standalone_signed_probe_rollouts"]) != 64
        or int(matrix["expected_mixed_factorial_rollouts"]) != 128
        or int(matrix["expected_nonbaseline_rollouts"]) != 192
        or int(matrix["expected_extended_baseline_rollouts"]) != 32
        or int(matrix["expected_rollouts_per_baseline_context"]) != 7
        or int(matrix["expected_standalone_response_groups"]) != 32
        or int(matrix["expected_mixed_factorial_groups"]) != 32
        or int(
            matrix["expected_matched_hidden_history_pc3_groups"]
        )
        != 16
        or int(
            matrix["expected_matched_hidden_history_mixed_groups"]
        )
        != 16
    ):
        raise ValueError("Stage4.2R3c3T9 task matrix changed")
    contract = cfg["formal_timing_contract"]
    if (
        int(contract["normal"]["arrival_deadline_step"]) != 25
        or int(contract["normal"]["hold_through_step"]) != 35
        or int(contract["weak"]["arrival_deadline_step"]) != 27
        or int(contract["weak"]["hold_through_step"]) != 37
        or float(contract["position_tolerance_m"]) != 0.03
        or float(contract["speed_tolerance_m_per_s"]) != 0.1
        or bool(contract["arrival_deadline_expansion_allowed"])
    ):
        raise ValueError("Stage4.2R3c3T9 formal timing changed")
    if (
        not bool(cfg["development_set_only"])
        or bool(cfg["independent_hidden_history_confirmation"])
        or bool(cfg["independent_long_hold_validated"])
        or bool(cfg["bc_dagger_or_rl_allowed"])
    ):
        raise ValueError("Stage4.2R3c3T9 scope changed")


def _authenticate_preflight(
    cfg: Mapping[str, Any],
) -> tuple[Path, dict[str, Any]]:
    required = cfg["candidate_preflight"]
    path = (_project_root() / str(required["path"])).resolve()
    if not path.is_file() or _sha256(path) != str(required["sha256"]):
        raise ValueError("T9 candidate preflight fingerprint mismatch")
    payload = t1.r3c3.read_json(path)
    if (
        not bool(payload["all_preflight_gates_pass"])
        or bool(payload["real_tsc_executed"])
        or bool(payload["ray_executed"])
        or bool(payload["gotsc_executed"])
        or int(payload["prospective_matrix"]["total_task_count"]) != 224
        or len(payload["actuator_cases"]) != 2
        or int(payload["inputs"]["r17"]["authenticated_file_count"])
        != int(required["required_r17_authenticated_count"])
        or int(payload["inputs"]["r3c1"]["authenticated_raw_count"])
        != int(required["required_r3c1_authenticated_count"])
    ):
        raise ValueError("T9 candidate preflight content mismatch")
    for case in payload["actuator_cases"]:
        if (
            int(case["complete_augmented_schedule_rank"])
            != int(required["required_complete_schedule_rank"])
            or int(case["selected_nine_schedule_rank"])
            != int(required["required_selected_schedule_rank"])
            or max(
                float(
                    case[
                        "complete_augmented_schedule_normalized_condition"
                    ]
                ),
                float(
                    case[
                        "selected_nine_schedule_normalized_condition"
                    ]
                ),
            )
            > float(required["maximum_normalized_schedule_condition"])
            or int(
                case["standalone_pc3_probe"][
                    "first_cancellation_effect_state"
                ]
            )
            != int(required["required_first_cancellation_effect_state"])
            or int(
                case["standalone_pc3_probe"][
                    "last_cancellation_effect_state"
                ]
            )
            != int(required["required_last_cancellation_effect_state"])
            or len(case["mixed_factorial"]["probes"]) != 4
        ):
            raise ValueError("T9 preflight actuator gate mismatch")
        schedules = [
            case["standalone_pc3_probe"],
            *case["mixed_factorial"]["probes"],
        ]
        for schedule in schedules:
            if (
                len(schedule["positive_schedule_by_task_issue_step"])
                != int(
                    required[
                        "required_issue_count_per_nonbaseline_probe"
                    ]
                )
                or max(
                    abs(float(value))
                    for value in schedule["requested_full_net"]
                )
                > 1.0e-12
                or int(schedule["first_cancellation_effect_state"])
                != 39
            ):
                raise ValueError("T9 frozen schedule mismatch")
    return path, payload


def load_stage42r3c3t9_config(
    config_path: Path,
    *,
    source_stage42r3b_run: Path,
    source_stage42r3c3_run: Path,
    source_stage42r3c3_bank_dir: Path,
    source_stage42r3c3t1_run: Path,
    source_stage42r3c3t1_audit_dir: Path,
    source_stage42r3c3t7_controller_bank: Path,
    run_dir_override: Path,
) -> Stage42R3C3T9Context:
    config_path = config_path.expanduser().resolve()
    cfg = t1.r3c3.read_json(config_path)
    _validate_config(cfg)
    base_path = (
        _project_root() / str(cfg["base_stage_config"])
    ).resolve()
    if (
        not base_path.is_file()
        or _sha256(base_path) != str(cfg["base_stage_config_sha256"])
    ):
        raise ValueError("T9 frozen T2 base config mismatch")
    base_ctx = t2.load_stage42r3c3t2_config(
        base_path,
        source_stage42r3b_run=source_stage42r3b_run,
        source_stage42r3c3_run=source_stage42r3c3_run,
        source_stage42r3c3_bank_dir=source_stage42r3c3_bank_dir,
        source_stage42r3c3t1_run=source_stage42r3c3t1_run,
        source_stage42r3c3t1_audit_dir=source_stage42r3c3t1_audit_dir,
        run_dir_override=run_dir_override,
    )
    preflight_path, preflight = _authenticate_preflight(cfg)
    bank = source_stage42r3c3t7_controller_bank.expanduser().resolve()
    bank_cfg = cfg["source_T7_controller_bank"]
    if not bank.is_file() or _sha256(bank) != str(bank_cfg["sha256"]):
        raise ValueError("T9 source T7 controller bank mismatch")
    bank_payload = t1.r3c3.read_json(bank)
    if (
        int(bank_payload["sample_count"])
        != int(bank_cfg["required_sample_count"])
        or int(bank_payload["basis_count"])
        != int(bank_cfg["required_basis_count"])
        or list(bank_payload["basis_order"])
        != list(bank_cfg["required_basis_order"])
    ):
        raise ValueError("T9 source T7 controller bank content changed")
    return Stage42R3C3T9Context(
        cfg=cfg,
        base_config_path=base_path,
        base_ctx=base_ctx,
        preflight_path=preflight_path,
        preflight=preflight,
        t7_controller_bank_path=bank,
        paths=_paths(run_dir_override),
    )


def _context_key(spec: Mapping[str, Any]) -> tuple[Any, ...]:
    return t6._context_key(spec)


def _preflight_case(
    ctx: Stage42R3C3T9Context, *, delay: int, slew: float
) -> Mapping[str, Any]:
    matches = [
        case
        for case in ctx.preflight["actuator_cases"]
        if int(case["delay_steps"]) == delay
        and math.isclose(
            float(case["slew_scale"]),
            slew,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        )
    ]
    if len(matches) != 1:
        raise ValueError("T9 preflight actuator selection mismatch")
    return matches[0]


def _schedule(
    probe: Mapping[str, Any], *, multiplier: int = 1
) -> dict[int, np.ndarray]:
    if multiplier not in {-1, 1}:
        raise ValueError("T9 schedule multiplier changed")
    result: dict[int, np.ndarray] = {}
    for issue_step, values in probe[
        "positive_schedule_by_task_issue_step"
    ]:
        issue_step = int(issue_step)
        value = (
            np.asarray(values, dtype=float).reshape(N_MODES) * multiplier
        )
        if (
            issue_step in result
            or issue_step < 0
            or issue_step >= OBSERVATION_HORIZON
        ):
            raise ValueError("T9 issue schedule invalid")
        result[issue_step] = value
    if len(result) != 41:
        raise ValueError("T9 issue count changed")
    net = np.sum(np.stack(list(result.values())), axis=0)
    if not np.allclose(net, np.zeros(N_MODES), rtol=0.0, atol=1e-12):
        raise ValueError("T9 schedule is not zero net")
    return result


def build_control_specs(
    ctx: Stage42R3C3T9Context,
    selected_pairs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    source_specs = t1.build_control_specs(
        ctx.base_ctx.source_ctx, selected_pairs
    )
    templates: dict[tuple[Any, ...], Mapping[str, Any]] = {}
    for spec in source_specs:
        templates.setdefault(_context_key(spec), spec)
    if len(templates) != 32:
        raise ValueError("T9 source context coverage mismatch")

    specs: list[dict[str, Any]] = []
    for key in sorted(templates):
        template = copy.deepcopy(dict(templates[key]))
        delay = int(template["action_delay_steps"])
        slew = float(template["slew_scale"])
        case = _preflight_case(ctx, delay=delay, slew=slew)
        pc3 = case["standalone_pc3_probe"]
        factorial = {
            str(probe["probe_id"]): probe
            for probe in case["mixed_factorial"]["probes"]
        }
        if set(factorial) != set(FACTORIAL_PROBE_IDS):
            raise ValueError("T9 factorial probe set changed")

        members: list[
            tuple[
                str,
                int,
                int | None,
                int | None,
                dict[int, np.ndarray],
                Mapping[str, Any] | None,
                str,
            ]
        ] = [
            (BASELINE_PROBE_ID, 0, None, None, {}, None, "baseline")
        ]
        for sign in (-1, 1):
            members.append(
                (
                    PC3_PROBE_ID,
                    sign,
                    None,
                    sign,
                    _schedule(pc3, multiplier=sign),
                    pc3,
                    "standalone_pc3",
                )
            )
        for probe_id, signs in zip(FACTORIAL_PROBE_IDS, FACTORIAL_SIGNS):
            frozen = factorial[probe_id]
            if (
                int(frozen["stress_sign"]) != signs[0]
                or int(frozen["pc3_sign"]) != signs[1]
            ):
                raise ValueError("T9 factorial sign mapping changed")
            members.append(
                (
                    probe_id,
                    signs[1],
                    signs[0],
                    signs[1],
                    _schedule(frozen),
                    frozen,
                    "mixed_factorial",
                )
            )

        for (
            probe_id,
            probe_sign,
            stress_sign,
            pc3_sign,
            schedule,
            frozen,
            family,
        ) in members:
            schedule_json = {
                str(step): value.tolist()
                for step, value in sorted(schedule.items())
            }
            identity = {
                "stage": STAGE,
                "source_context": list(key),
                "probe_id": probe_id,
                "probe_sign": probe_sign,
                "probe_family": family,
                "stress_sign": stress_sign,
                "pc3_sign": pc3_sign,
                "schedule": schedule_json,
                "candidate_preflight_sha256": _sha256(
                    ctx.preflight_path
                ),
                "observation_horizon_steps": OBSERVATION_HORIZON,
                "controller_revision": CONTROLLER_REVISION,
                "source_t1_raw_inventory_digest": (
                    ctx.base_ctx.source_t1_fingerprint[
                        "raw_inventory_digest"
                    ]
                ),
            }
            experiment_id = t1.r3c3._scenario_digest(identity)
            spec = copy.deepcopy(template)
            spec.update(
                {
                    "kind": (
                        "stage4_2r3c3t9_pc3_mixed_interaction_"
                        "identification"
                    ),
                    "stage": STAGE,
                    "controller_revision": CONTROLLER_REVISION,
                    "underlying_controller_revision": (
                        t1.r3c1.CONTROLLER_REVISION
                    ),
                    "experiment_id": experiment_id,
                    "phase": "pc3_mixed_interaction_identification",
                    "category": "pc3_mixed_interaction_identification",
                    "environment_variant": f"stage4_2r3c3t9_{experiment_id}",
                    "horizon_steps": OBSERVATION_HORIZON,
                    "formal_horizon_steps": _formal_horizon(slew),
                    "identification_only": True,
                    "r3c3_probe_id": probe_id,
                    "r3c3_probe_mode": -1 if not schedule else -2,
                    "r3c3_probe_sign": probe_sign,
                    "r3c3_probe_first_effect_state": (
                        -1
                        if frozen is None
                        else int(frozen["first_formal_effect_state"])
                    ),
                    "r3c3_probe_delta_by_task_issue_step": schedule_json,
                    "r3c3_requested_probe_net": (
                        [0.0] * N_MODES
                        if not schedule
                        else np.sum(
                            np.stack(list(schedule.values())), axis=0
                        ).tolist()
                    ),
                    "r3c3_probe_amplitude": (
                        0.0
                        if frozen is None
                        else float(frozen["formal_max_abs_component"])
                    ),
                    "r3c3_probe_expected_issue_count": len(schedule),
                    "r3c3t9_probe_family": family,
                    "r3c3t9_stress_sign": stress_sign,
                    "r3c3t9_pc3_sign": pc3_sign,
                    "r3c3t9_standalone_pc3_scale": float(
                        pc3["scale"]
                    ),
                    "r3c3t9_factorial_common_amplitude": float(
                        case["mixed_factorial"]["common_amplitude"]
                    ),
                    "r3c3t9_schedule_contract": (
                        "authenticated_pc3_and_stress_by_pc3_factorial_"
                        "formal_then_effect_states_39_to_44_zero_net_v1"
                    ),
                    "candidate_preflight_sha256": _sha256(
                        ctx.preflight_path
                    ),
                    "source_stage4_2r3c3t1_raw_inventory_digest": (
                        ctx.base_ctx.source_t1_fingerprint[
                            "raw_inventory_digest"
                        ]
                    ),
                    "probe_trajectory_allowed_in_expert_dataset": False,
                    "pair_or_history_label_available_to_controller": False,
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
        raise ValueError("T9 control identity coverage mismatch")
    return specs


class PC3MixedInteractionProbeController(_ORIGINAL_T6_CONTROLLER):
    """Exact R3c1 controller plus one frozen T9 schedule."""

    def __init__(
        self,
        base_worker: Any,
        bundle: Mapping[str, Any],
        source_spec: Mapping[str, Any],
        initial_state: Mapping[str, Any],
    ):
        _install_t6_runtime_adapter(reset_ray_actor=False)
        self.t9_probe_family = source_spec.get("r3c3t9_probe_family")
        self.t9_stress_sign = source_spec.get("r3c3t9_stress_sign")
        self.t9_pc3_sign = source_spec.get("r3c3t9_pc3_sign")
        super().__init__(
            base_worker, bundle, source_spec, initial_state
        )

    def action(
        self, current_state: Mapping[str, Any]
    ) -> tuple[np.ndarray, dict[str, Any]]:
        action, trace = super().action(current_state)
        trace.pop("r3c3t6_identification_only", None)
        trace.update(
            {
                "r3c3t9_identification_only": True,
                "r3c3t9_observation_horizon_steps": OBSERVATION_HORIZON,
                "r3c3t9_post_contract_neutralization": True,
                "r3c3t9_probe_family": self.t9_probe_family,
                "r3c3t9_stress_sign": self.t9_stress_sign,
                "r3c3t9_pc3_sign": self.t9_pc3_sign,
            }
        )
        return action, trace


def _control_payload(
    ctx: Stage42R3C3T9Context, *, spec: Mapping[str, Any]
) -> dict[str, Any]:
    proxy = SimpleNamespace(
        source_ctx=ctx.base_ctx.source_ctx.source_ctx,
        cfg=ctx.base_ctx.cfg,
        paths=ctx.paths,
    )
    payload = t1.r3c3._control_payload(proxy, spec=spec)
    train_cfg = copy.deepcopy(payload["train_cfg"])
    train_cfg.setdefault("episode", {})[
        "max_episode_steps"
    ] = OBSERVATION_HORIZON
    experiment_id = str(spec["experiment_id"])
    t1.r3c3.atomic_write_json(
        ctx.paths.variants / f"train_{experiment_id}.json", train_cfg
    )
    payload["train_cfg"] = train_cfg
    payload["stage4_1r4_horizon_steps"] = OBSERVATION_HORIZON
    payload["variant_id"] = f"stage4_2r3c3t9_{experiment_id}"
    payload["stage4_2r3c3t9_restart_snapshot_dir"] = str(
        spec["restart_snapshot_dir"]
    )
    payload["stage4_2r3c3t9_snapshot_manifest_digest"] = str(
        spec["restart_snapshot_manifest_digest"]
    )
    t1.r3c3.atomic_write_json(
        ctx.paths.variants / f"payload_{experiment_id}.json", payload
    )
    return payload


def _install_t6_runtime_adapter(*, reset_ray_actor: bool) -> None:
    """Install the T9 identity in the current process's T6 runtime shell."""

    t6.STAGE = STAGE
    t6.CONTROLLER_REVISION = CONTROLLER_REVISION
    t6.PACKAGE_REVISION = PACKAGE_REVISION
    t6.RUN_NAME = RUN_NAME
    t6.BASELINE_PROBE_ID = BASELINE_PROBE_ID
    t6.PROBE_IDS = NONBASELINE_PROBE_IDS
    t6.TargetResidualNewDirectionProbeController = (
        PC3MixedInteractionProbeController
    )
    t6._control_payload = _control_payload
    t6.build_control_specs = build_control_specs
    if reset_ray_actor:
        t6._CONTROL_RAY_ACTOR = None


def _prepare_dirs(paths: Stage42R3C3T9Paths) -> None:
    for path in (
        paths.run_dir,
        paths.control,
        paths.raw,
        paths.variants,
        paths.source_reference,
        paths.analysis,
    ):
        path.mkdir(parents=True, exist_ok=True)


def _deployed_package_fingerprint() -> dict[str, Any]:
    root = _project_root()
    manifest = t1.r3c3.read_json(root / "PACKAGE_MANIFEST.json")
    relative_paths = list(manifest["file_inventory"]) + ["SHA256SUMS"]
    rows = []
    for relative in sorted(set(relative_paths)):
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(f"package file missing: {path}")
        rows.append(
            {
                "path": relative,
                "size_bytes": int(path.stat().st_size),
                "sha256": _sha256(path),
            }
        )
    return {
        "schema_version": 1,
        "contract": "r42r3c3t9_deployed_package_source_v1",
        "n_files": len(rows),
        "digest": _canonical_digest(rows),
        "files": rows,
    }


def prepare(
    ctx: Stage42R3C3T9Context, *, resume: bool
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    _prepare_dirs(ctx.paths)
    selected_pairs, _ = t1.r3c3._recompute_selected_pairs(
        ctx.base_ctx.source_ctx.base_ctx
    )
    specs = build_control_specs(ctx, selected_pairs)
    package = _deployed_package_fingerprint()
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "source_stage4_2r3c3t1_run": str(ctx.base_ctx.source_t1_run),
        "source_stage4_2r3c3t1_audit_dir": str(
            ctx.base_ctx.source_t1_audit_dir
        ),
        "source_stage4_2r3c3t1_fingerprint": (
            ctx.base_ctx.source_t1_fingerprint
        ),
        "source_stage4_2r3c3_run": str(
            ctx.base_ctx.source_ctx.source_r3c3_run
        ),
        "source_stage4_2r3c3_bank_dir": str(
            ctx.base_ctx.source_ctx.source_bank_dir
        ),
        "source_stage4_2r3b_run": str(
            ctx.base_ctx.source_ctx.source_r3b_run
        ),
        "source_stage4_2r3c1_run": str(
            ctx.base_ctx.source_ctx.source_r3c1_run
        ),
        "source_stage4_2r3c3t7_controller_bank": str(
            ctx.t7_controller_bank_path
        ),
        "source_stage4_2r3c3t7_controller_bank_sha256": _sha256(
            ctx.t7_controller_bank_path
        ),
        "candidate_preflight_path": str(ctx.preflight_path),
        "candidate_preflight_sha256": _sha256(ctx.preflight_path),
        "deployed_package_fingerprint": package,
        "config_digest": _canonical_digest(ctx.cfg),
        "control_spec_digest": _canonical_digest(specs),
        "identification_probe": copy.deepcopy(
            ctx.cfg["identification_probe"]
        ),
        "formal_timing_contract": copy.deepcopy(
            ctx.cfg["formal_timing_contract"]
        ),
        "control_matrix": copy.deepcopy(ctx.cfg["control_matrix"]),
        "development_set_only": True,
        "independent_hidden_history_confirmation": False,
        "independent_long_hold_validated": False,
    }
    if ctx.paths.manifest.is_file():
        if not resume:
            raise FileExistsError(
                "Stage4.2R3c3T9 run exists; use resume or a fresh run"
            )
        old = t1.r3c3.read_json(ctx.paths.manifest)
        if old != manifest:
            raise ValueError("T9 resume manifest or package changed")
    else:
        t1.r3c3.atomic_write_json(ctx.paths.manifest, manifest)
    t1.r3c3.atomic_write_json(
        ctx.paths.run_dir / "stage4_2r3c3t9_config.resolved.json", ctx.cfg
    )
    t1.r3c3.atomic_write_json(
        ctx.paths.source_reference / "control_specs.json", specs
    )
    t1.r3c3.atomic_write_json(
        ctx.paths.source_reference / "candidate_preflight.json",
        ctx.preflight,
    )
    t1.r3c3.atomic_write_json(
        ctx.paths.source_reference / "deployed_package_fingerprint.json",
        package,
    )
    state = (
        t1.r3c3.read_json(ctx.paths.state)
        if ctx.paths.state.is_file()
        else {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "controller_revision": CONTROLLER_REVISION,
            "package_revision": PACKAGE_REVISION,
            "prepared": True,
            "finished": False,
            "primary_pass": False,
            "linear_route_passed": False,
            "phase_status": "prepared",
            "stop_reason": "",
        }
    )
    state["updated_utc"] = t1.r3c3.utc_timestamp()
    t1.r3c3.atomic_write_json(ctx.paths.state, state)
    return list(selected_pairs), specs


def run_offline_probe_audit(
    ctx: Stage42R3C3T9Context,
    selected_pairs: Sequence[Mapping[str, Any]],
    *,
    allow_existing_raw: bool = False,
) -> dict[str, Any]:
    _install_t6_runtime_adapter(reset_ray_actor=True)
    summary = t6.run_offline_probe_audit(
        ctx,
        selected_pairs,
        allow_existing_raw=allow_existing_raw,
    )
    summary = copy.deepcopy(summary)
    summary.update(
        {
            "stage": STAGE,
            "phase": "offline_pc3_mixed_interaction_probe_audit",
            "standalone_pc3_spec_count": 64,
            "mixed_factorial_spec_count": 128,
        }
    )
    t1.r3c3.atomic_write_json(
        ctx.paths.source_reference
        / "offline_pc3_mixed_interaction_audit.json",
        summary,
    )
    return summary


def _evaluate_control(
    ctx: Stage42R3C3T9Context,
    specs: Sequence[dict[str, Any]],
    *,
    backend: str,
    resume: bool,
) -> list[dict[str, Any]]:
    _install_t6_runtime_adapter(reset_ray_actor=True)
    return t6._evaluate_control(
        ctx, specs, backend=backend, resume=resume
    )


def _formal_prefix_result(
    result: Mapping[str, Any],
) -> dict[str, Any]:
    return t6._formal_prefix_result(result)


def _phase_trace_valid(result: Mapping[str, Any]) -> dict[str, Any]:
    """Use the frozen T6 trace checker with an explicit T9 flag bridge."""

    shadow = copy.deepcopy(dict(result))
    original = list(result.get("controller_trace") or [])
    shadow_trace = copy.deepcopy(original)
    t9_flags_exact = bool(
        len(original) == OBSERVATION_HORIZON
        and all(bool(row.get("r3c3t9_identification_only")) for row in original)
        and not any(bool(row.get("r3c3t6_identification_only")) for row in original)
    )
    for row in shadow_trace:
        row["r3c3t6_identification_only"] = True
    shadow["controller_trace"] = shadow_trace
    checked = t6._phase_trace_valid(shadow)
    checked["t9_identification_flags_exact"] = t9_flags_exact
    checked["passed"] = bool(checked["passed"] and t9_flags_exact)
    return checked


def _arrays(
    result: Mapping[str, Any], dt_s: float
) -> tuple[np.ndarray, np.ndarray]:
    return t6._arrays(result, dt_s)


def _initial_arrays(
    result: Mapping[str, Any],
) -> tuple[np.ndarray, np.ndarray]:
    return t6._initial_arrays(result)


def _rmse(array: np.ndarray) -> float:
    return t6._rmse(array)


def _member_key(spec: Mapping[str, Any]) -> str:
    probe_id = str(spec["r3c3_probe_id"])
    if probe_id == PC3_PROBE_ID:
        return f"{PC3_PROBE_ID}:{int(spec['r3c3_probe_sign'])}"
    return probe_id


def _same_initial(results: Sequence[Mapping[str, Any]]) -> bool:
    arrays = [_initial_arrays(result) for result in results]
    return bool(
        arrays
        and all(
            np.array_equal(arrays[0][0], item[0])
            and np.array_equal(arrays[0][1], item[1])
            for item in arrays[1:]
        )
    )


def _norm_ratio(numerator: np.ndarray, denominator: float) -> float:
    value = float(np.linalg.norm(numerator))
    if denominator <= 1.0e-15:
        return 0.0 if value <= 1.0e-15 else math.inf
    return value / denominator


def _walsh_contrasts(
    arrays: Mapping[tuple[int, int], np.ndarray],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if set(arrays) != set(FACTORIAL_SIGNS):
        raise ValueError("T9 factorial contrast coverage changed")
    shapes = {np.asarray(value).shape for value in arrays.values()}
    if len(shapes) != 1:
        raise ValueError("T9 factorial contrast shapes differ")
    intercept = sum(
        np.asarray(arrays[signs], dtype=float)
        for signs in FACTORIAL_SIGNS
    ) / 4.0
    stress = sum(
        stress_sign * np.asarray(arrays[(stress_sign, pc3_sign)], dtype=float)
        for stress_sign, pc3_sign in FACTORIAL_SIGNS
    ) / 4.0
    pc3 = sum(
        pc3_sign * np.asarray(arrays[(stress_sign, pc3_sign)], dtype=float)
        for stress_sign, pc3_sign in FACTORIAL_SIGNS
    ) / 4.0
    mixed = sum(
        stress_sign
        * pc3_sign
        * np.asarray(arrays[(stress_sign, pc3_sign)], dtype=float)
        for stress_sign, pc3_sign in FACTORIAL_SIGNS
    ) / 4.0
    return intercept, stress, pc3, mixed


def summarize_control(
    ctx: Stage42R3C3T9Context,
    results: Sequence[Mapping[str, Any]],
    selected_pairs: Sequence[Mapping[str, Any]],
    *,
    write_outputs: bool = True,
) -> dict[str, Any]:
    _install_t6_runtime_adapter(reset_ray_actor=False)
    expected = int(ctx.cfg["control_matrix"]["expected_rollouts"])
    probe_cfg = ctx.cfg["identification_probe"]
    matrix_cfg = ctx.cfg["control_matrix"]
    central_cfg = probe_cfg["standalone_central_symmetry"]
    pc3_history_cfg = probe_cfg["matched_hidden_history_pc3"]
    mixed_history_cfg = probe_cfg[
        "matched_hidden_history_mixed_contrast"
    ]
    dt_ms = int(
        t1.r1._r13_ctx(ctx.base_ctx.source_ctx.source_ctx.r1_ctx)
        .r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34.env_cfg[
            "dt_ms"
        ]
    )
    dt_s = dt_ms / 1000.0
    state_map = t1.r3b._selected_state_map(selected_pairs)
    base_source_ctx = ctx.base_ctx.source_ctx.source_ctx
    rows = []
    by_context: dict[tuple[Any, ...], dict[str, Mapping[str, Any]]] = (
        defaultdict(dict)
    )
    for result in results:
        spec = result["spec"]
        key = _context_key(spec)
        member = _member_key(spec)
        if member in by_context[key]:
            raise ValueError("T9 result member duplicated")
        by_context[key][member] = result
        state_id = str(spec["state_generation_experiment_id"])
        base = t1.r3b._control_row(
            base_source_ctx,
            _formal_prefix_result(result),
            state_map[state_id],
        )
        phase = _phase_trace_valid(result)
        formal = (
            t2._formal_prefix_metrics(ctx.base_ctx, result)
            if bool(result.get("success"))
            else {}
        )
        baseline = str(spec["r3c3_probe_id"]) == BASELINE_PROBE_ID
        prefix_exact = bool(
            baseline
            and result.get("success")
            and t2._source_prefix_exact(ctx.base_ctx, result)
        )
        execution_pass = bool(
            result.get("success")
            and base["fresh_controller"]
            and base["fresh_tsc_process"]
            and base["initial_restart_exact"]
            and base["controller_trace_causal"]
            and phase["passed"]
            and (not baseline or prefix_exact)
        )
        if not bool(result.get("success")):
            failure_class = "runtime_or_environment_error"
        elif not bool(base["initial_restart_exact"]):
            failure_class = "plant_restart_fidelity_failure"
        elif not bool(base["controller_trace_causal"]):
            failure_class = "controller_causality_failure"
        elif not bool(phase["passed"]):
            failure_class = "identification_probe_execution_failure"
        elif baseline and not prefix_exact:
            failure_class = "extended_baseline_prefix_mismatch"
        else:
            failure_class = ""
        rows.append(
            {
                **base,
                "probe_id": str(spec["r3c3_probe_id"]),
                "probe_sign": int(spec["r3c3_probe_sign"]),
                "probe_family": str(spec["r3c3t9_probe_family"]),
                "stress_sign": spec["r3c3t9_stress_sign"],
                "pc3_sign": spec["r3c3t9_pc3_sign"],
                "extended_baseline": baseline,
                "extended_baseline_prefix_exact": prefix_exact,
                "phase_trace_valid": bool(phase["passed"]),
                "probe_trace_exact": bool(phase["probe_trace_exact"]),
                "probe_issued_count": int(phase["probe_issued_count"]),
                "probe_applied_exact": bool(phase["probe_applied_exact"]),
                "probe_zero_net": bool(phase["probe_zero_net"]),
                "solver_failure_count": int(
                    phase["solver_failure_count"]
                ),
                "forbidden_trace_count": int(
                    phase["forbidden_trace_count"]
                ),
                "max_current_utilization": (
                    t2._full_current_utilization(ctx.base_ctx, result)
                    if bool(result.get("success"))
                    else None
                ),
                "formal_contract_pass": bool(
                    formal.get("stage3_4_target_tracking_pass", False)
                ),
                "formal_minimum_signed_margin": (
                    float(
                        formal["stage3_4_tracking_minimum_signed_margin"]
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

    if len(by_context) != 32:
        raise ValueError("T9 context coverage mismatch")
    baselines: dict[tuple[Any, ...], Mapping[str, Any]] = {}
    pc3_odd: dict[
        tuple[Any, ...], tuple[np.ndarray, np.ndarray, int, float]
    ] = {}
    central_rows = []
    for key in sorted(by_context):
        members = by_context[key]
        baseline = members.get(BASELINE_PROBE_ID)
        plus = members.get(f"{PC3_PROBE_ID}:1")
        minus = members.get(f"{PC3_PROBE_ID}:-1")
        row: dict[str, Any] = {
            "pair_id": key[0],
            "history_member": key[1],
            "target_id": key[2],
            "actual_delay_steps": key[3],
            "actual_slew_scale": key[4],
            "response_available": False,
            "baseline_initial_state_exact": False,
            "even_velocity_rmse_m_per_s": None,
            "even_position_rmse_m": None,
            "even_ip_rmse_A": None,
            "central_symmetry_pass": False,
        }
        if baseline is not None:
            baselines[key] = baseline
        if (
            baseline is not None
            and plus is not None
            and minus is not None
            and all(
                bool(item.get("success"))
                for item in (baseline, plus, minus)
            )
        ):
            base_y, base_v = _arrays(baseline, dt_s)
            plus_y, plus_v = _arrays(plus, dt_s)
            minus_y, minus_v = _arrays(minus, dt_s)
            initial_exact = _same_initial((baseline, plus, minus))
            if (
                plus_y.shape == minus_y.shape == base_y.shape
                and plus_v.shape == minus_v.shape == base_v.shape
            ):
                first = int(
                    plus["spec"]["r3c3_probe_first_effect_state"]
                )
                section = slice(first, OBSERVATION_HORIZON + 1)
                odd_y = (plus_y - minus_y) / 2.0
                odd_v = (plus_v - minus_v) / 2.0
                even_y = (plus_y + minus_y) / 2.0 - base_y
                even_v = (plus_v + minus_v) / 2.0 - base_v
                velocity_rmse = _rmse(even_v[section, :2])
                position_rmse = _rmse(even_y[section, :2])
                ip_rmse = _rmse(even_y[section, 2])
                passed = bool(
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
                standalone_scale = float(
                    plus["spec"]["r3c3t9_standalone_pc3_scale"]
                )
                pc3_odd[key] = (
                    odd_y,
                    odd_v,
                    first,
                    standalone_scale,
                )
                row.update(
                    {
                        "response_available": True,
                        "baseline_initial_state_exact": initial_exact,
                        "first_effect_state": first,
                        "standalone_pc3_scale": standalone_scale,
                        "even_velocity_rmse_m_per_s": velocity_rmse,
                        "even_position_rmse_m": position_rmse,
                        "even_ip_rmse_A": ip_rmse,
                        "central_symmetry_pass": passed,
                    }
                )
        central_rows.append(row)

    pc3_history_groups: dict[
        tuple[Any, ...], dict[str, tuple[np.ndarray, np.ndarray, int, float]]
    ] = defaultdict(dict)
    for key, response in pc3_odd.items():
        pc3_history_groups[(key[0], key[2], key[3], key[4])][
            key[1]
        ] = response
    pc3_history_rows = []
    for key in sorted(pc3_history_groups):
        members = pc3_history_groups[key]
        row = {
            "pair_id": key[0],
            "target_id": key[1],
            "actual_delay_steps": key[2],
            "actual_slew_scale": key[3],
            "history_member_count": len(members),
            "odd_velocity_rmse_m_per_s": None,
            "odd_position_rmse_m": None,
            "odd_ip_rmse_A": None,
            "matched_hidden_history_pass": False,
        }
        if set(members) == {"plus_first", "minus_first"}:
            plus = members["plus_first"]
            minus = members["minus_first"]
            first = min(plus[2], minus[2])
            section = slice(first, OBSERVATION_HORIZON + 1)
            velocity_rmse = _rmse(
                plus[1][section, :2] - minus[1][section, :2]
            )
            position_rmse = _rmse(
                plus[0][section, :2] - minus[0][section, :2]
            )
            ip_rmse = _rmse(
                plus[0][section, 2] - minus[0][section, 2]
            )
            row.update(
                {
                    "odd_velocity_rmse_m_per_s": velocity_rmse,
                    "odd_position_rmse_m": position_rmse,
                    "odd_ip_rmse_A": ip_rmse,
                    "matched_hidden_history_pass": bool(
                        velocity_rmse
                        <= float(
                            pc3_history_cfg[
                                "maximum_odd_velocity_rmse_m_per_s"
                            ]
                        )
                        and position_rmse
                        <= float(
                            pc3_history_cfg[
                                "maximum_odd_position_rmse_m"
                            ]
                        )
                        and ip_rmse
                        <= float(
                            pc3_history_cfg["maximum_odd_ip_rmse_A"]
                        )
                    ),
                }
            )
        pc3_history_rows.append(row)

    mixed_contrasts: dict[
        tuple[Any, ...], tuple[np.ndarray, np.ndarray, int]
    ] = {}
    factorial_rows = []
    for key in sorted(by_context):
        members = by_context[key]
        baseline = baselines.get(key)
        signed: dict[tuple[int, int], Mapping[str, Any]] = {}
        for probe_id, signs in zip(FACTORIAL_PROBE_IDS, FACTORIAL_SIGNS):
            if probe_id in members:
                signed[signs] = members[probe_id]
        row: dict[str, Any] = {
            "pair_id": key[0],
            "history_member": key[1],
            "target_id": key[2],
            "actual_delay_steps": key[3],
            "actual_slew_scale": key[4],
            "factorial_member_count": len(signed),
            "response_available": False,
            "baseline_initial_state_exact": False,
            "mixed_velocity_norm_ratio": None,
            "pc3_main_effect_modulation_ratio": None,
            "linear_route_pass": False,
        }
        if (
            baseline is not None
            and set(signed) == set(FACTORIAL_SIGNS)
            and bool(baseline.get("success"))
            and all(bool(item.get("success")) for item in signed.values())
            and key in pc3_odd
        ):
            ordered = [signed[signs] for signs in FACTORIAL_SIGNS]
            initial_exact = _same_initial((baseline, *ordered))
            arrays = {
                signs: _arrays(signed[signs], dt_s)
                for signs in FACTORIAL_SIGNS
            }
            shapes = {
                (values[0].shape, values[1].shape)
                for values in arrays.values()
            }
            if len(shapes) == 1:
                y = {key_: value[0] for key_, value in arrays.items()}
                v = {key_: value[1] for key_, value in arrays.items()}
                _, stress_y, pc3_y, mixed_y = _walsh_contrasts(y)
                _, stress_v, pc3_v, mixed_v = _walsh_contrasts(v)
                first = min(
                    int(item["spec"]["r3c3_probe_first_effect_state"])
                    for item in ordered
                )
                horizon = _formal_horizon(float(key[4]))
                section = slice(3, horizon + 1)
                main_norm = float(
                    np.linalg.norm(stress_v[section, :2])
                    + np.linalg.norm(pc3_v[section, :2])
                )
                mixed_ratio = _norm_ratio(
                    mixed_v[section, :2], main_norm
                )
                standalone = pc3_odd[key]
                common_amplitude = float(
                    ordered[0]["spec"][
                        "r3c3t9_factorial_common_amplitude"
                    ]
                )
                scale_ratio = common_amplitude / standalone[3]
                expected_pc3 = standalone[1] * scale_ratio
                expected_norm = float(
                    np.linalg.norm(expected_pc3[section, :2])
                )
                modulation = _norm_ratio(
                    pc3_v[section, :2]
                    - expected_pc3[section, :2],
                    expected_norm,
                )
                linear_pass = bool(
                    initial_exact
                    and mixed_ratio
                    <= float(
                        probe_cfg[
                            "maximum_mixed_velocity_norm_ratio_for_linear_route"
                        ]
                    )
                    and modulation
                    <= float(
                        probe_cfg[
                            "maximum_pc3_main_effect_modulation_ratio_for_linear_route"
                        ]
                    )
                )
                mixed_contrasts[key] = (mixed_y, mixed_v, first)
                row.update(
                    {
                        "response_available": True,
                        "baseline_initial_state_exact": initial_exact,
                        "first_effect_state": first,
                        "factorial_common_amplitude": common_amplitude,
                        "standalone_to_factorial_pc3_scale_ratio": (
                            scale_ratio
                        ),
                        "mixed_velocity_norm_ratio": mixed_ratio,
                        "pc3_main_effect_modulation_ratio": modulation,
                        "linear_route_pass": linear_pass,
                        "stress_main_velocity_norm": float(
                            np.linalg.norm(stress_v[section, :2])
                        ),
                        "pc3_main_velocity_norm": float(
                            np.linalg.norm(pc3_v[section, :2])
                        ),
                        "mixed_velocity_norm": float(
                            np.linalg.norm(mixed_v[section, :2])
                        ),
                        "stress_main_position_norm": float(
                            np.linalg.norm(stress_y[section, :2])
                        ),
                        "pc3_main_position_norm": float(
                            np.linalg.norm(pc3_y[section, :2])
                        ),
                        "mixed_position_norm": float(
                            np.linalg.norm(mixed_y[section, :2])
                        ),
                    }
                )
        factorial_rows.append(row)

    mixed_history_groups: dict[
        tuple[Any, ...], dict[str, tuple[np.ndarray, np.ndarray, int]]
    ] = defaultdict(dict)
    for key, response in mixed_contrasts.items():
        mixed_history_groups[(key[0], key[2], key[3], key[4])][
            key[1]
        ] = response
    mixed_history_rows = []
    for key in sorted(mixed_history_groups):
        members = mixed_history_groups[key]
        row = {
            "pair_id": key[0],
            "target_id": key[1],
            "actual_delay_steps": key[2],
            "actual_slew_scale": key[3],
            "history_member_count": len(members),
            "mixed_velocity_rmse_m_per_s": None,
            "mixed_position_rmse_m": None,
            "mixed_ip_rmse_A": None,
            "matched_hidden_history_pass": False,
        }
        if set(members) == {"plus_first", "minus_first"}:
            plus = members["plus_first"]
            minus = members["minus_first"]
            first = min(plus[2], minus[2])
            section = slice(first, OBSERVATION_HORIZON + 1)
            velocity_rmse = _rmse(
                plus[1][section, :2] - minus[1][section, :2]
            )
            position_rmse = _rmse(
                plus[0][section, :2] - minus[0][section, :2]
            )
            ip_rmse = _rmse(
                plus[0][section, 2] - minus[0][section, 2]
            )
            row.update(
                {
                    "mixed_velocity_rmse_m_per_s": velocity_rmse,
                    "mixed_position_rmse_m": position_rmse,
                    "mixed_ip_rmse_A": ip_rmse,
                    "matched_hidden_history_pass": bool(
                        velocity_rmse
                        <= float(
                            mixed_history_cfg[
                                "maximum_velocity_rmse_m_per_s"
                            ]
                        )
                        and position_rmse
                        <= float(
                            mixed_history_cfg["maximum_position_rmse_m"]
                        )
                        and ip_rmse
                        <= float(mixed_history_cfg["maximum_ip_rmse_A"])
                    ),
                }
            )
        mixed_history_rows.append(row)

    t7_bank = t1.r3c3.read_json(ctx.t7_controller_bank_path)
    old_by_sample = {
        t6._t3_sample_key(sample): [
            np.asarray(
                response["delta_velocity_RZ_by_state"], dtype=float
            )
            for response in sorted(
                sample["basis_responses"],
                key=lambda item: int(item["basis_index"]),
            )
        ]
        for sample in t7_bank["samples"]
    }
    condition_rows = []
    for key in sorted(pc3_odd):
        baseline = baselines[key]
        old = old_by_sample.get(t6._result_sample_key(baseline), [])
        horizon = _formal_horizon(float(key[4]))
        arrays = [*old, pc3_odd[key][1][: horizon + 1]]
        rank, condition, passed = t6._condition_row(
            arrays,
            expected_rank=9,
            maximum=float(
                probe_cfg[
                    "maximum_selected_nine_velocity_condition_number"
                ]
            ),
        )
        condition_rows.append(
            {
                "pair_id": key[0],
                "history_member": key[1],
                "target_id": key[2],
                "actual_delay_steps": key[3],
                "actual_slew_scale": key[4],
                "controller_use_start_state": 3,
                "controller_use_end_state": horizon,
                "basis_count": 9,
                "velocity_response_matrix_rank": rank,
                "selected_velocity_condition_number": condition,
                "condition_number_pass": passed,
                "t7_sample_match": len(old) == 8,
            }
        )

    def count(rows_: Sequence[Mapping[str, Any]], field: str) -> int:
        return sum(bool(row[field]) for row in rows_)

    current_values = [
        float(row["max_current_utilization"])
        for row in rows
        if row["max_current_utilization"] is not None
    ]
    maximum_current = max(current_values) if current_values else None
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "pc3_mixed_interaction_identification",
        "identification_only": True,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "development_set_only": True,
        "independent_hidden_history_confirmation": False,
        "observation_horizon_steps": OBSERVATION_HORIZON,
        "formal_timing_unchanged": True,
        "expected_rollouts": expected,
        "n_rollouts": len(rows),
        "execution_pass_count": count(rows, "execution_pass"),
        "extended_baseline_prefix_exact_count": count(
            rows, "extended_baseline_prefix_exact"
        ),
        "expected_extended_baseline_count": 32,
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
        "identification_probe_execution_failure_count": sum(
            row["failure_class"]
            == "identification_probe_execution_failure"
            for row in rows
        ),
        "extended_baseline_prefix_mismatch_count": sum(
            row["failure_class"] == "extended_baseline_prefix_mismatch"
            for row in rows
        ),
        "forbidden_controller_input_count": sum(
            int(row["forbidden_trace_count"]) for row in rows
        ),
        "solver_failure_count": sum(
            int(row["solver_failure_count"]) for row in rows
        ),
        "formal_contract_pass_count": count(rows, "formal_contract_pass"),
        "formal_contract_failure_count": len(rows)
        - count(rows, "formal_contract_pass"),
        "formal_tracking_is_acceptance_gate": False,
        "standalone_response_group_count": len(central_rows),
        "standalone_central_symmetry_pass_count": count(
            central_rows, "central_symmetry_pass"
        ),
        "pc3_matched_history_group_count": len(pc3_history_rows),
        "pc3_matched_history_pass_count": count(
            pc3_history_rows, "matched_hidden_history_pass"
        ),
        "mixed_factorial_group_count": len(factorial_rows),
        "mixed_factorial_response_available_count": count(
            factorial_rows, "response_available"
        ),
        "mixed_matched_history_group_count": len(mixed_history_rows),
        "mixed_matched_history_pass_count": count(
            mixed_history_rows, "matched_hidden_history_pass"
        ),
        "selected_nine_condition_group_count": len(condition_rows),
        "selected_nine_condition_pass_count": count(
            condition_rows, "condition_number_pass"
        ),
        "maximum_selected_nine_velocity_condition_number": max(
            (
                float(row["selected_velocity_condition_number"])
                for row in condition_rows
                if row["selected_velocity_condition_number"] is not None
            ),
            default=None,
        ),
        "linear_route_context_pass_count": count(
            factorial_rows, "linear_route_pass"
        ),
        "maximum_mixed_velocity_norm_ratio": max(
            (
                float(row["mixed_velocity_norm_ratio"])
                for row in factorial_rows
                if row["mixed_velocity_norm_ratio"] is not None
            ),
            default=None,
        ),
        "maximum_pc3_main_effect_modulation_ratio": max(
            (
                float(row["pc3_main_effect_modulation_ratio"])
                for row in factorial_rows
                if row["pc3_main_effect_modulation_ratio"] is not None
            ),
            default=None,
        ),
        "maximum_current_utilization": maximum_current,
        "maximum_current_utilization_allowed": float(
            probe_cfg["maximum_current_utilization"]
        ),
    }
    summary["execution_gate_passed"] = bool(
        len(rows) == expected
        and summary["execution_pass_count"] == expected
        and summary["extended_baseline_prefix_exact_count"] == 32
        and summary["forbidden_controller_input_count"] == 0
        and summary["solver_failure_count"] == 0
    )
    summary["standalone_central_symmetry_gate_passed"] = bool(
        len(central_rows)
        == summary["standalone_central_symmetry_pass_count"]
        == int(matrix_cfg["expected_standalone_response_groups"])
    )
    summary["pc3_matched_history_gate_passed"] = bool(
        len(pc3_history_rows)
        == summary["pc3_matched_history_pass_count"]
        == int(
            matrix_cfg[
                "expected_matched_hidden_history_pc3_groups"
            ]
        )
    )
    summary["mixed_factorial_response_gate_passed"] = bool(
        len(factorial_rows)
        == summary["mixed_factorial_response_available_count"]
        == int(matrix_cfg["expected_mixed_factorial_groups"])
    )
    summary["mixed_matched_history_gate_passed"] = bool(
        len(mixed_history_rows)
        == summary["mixed_matched_history_pass_count"]
        == int(
            matrix_cfg[
                "expected_matched_hidden_history_mixed_groups"
            ]
        )
    )
    summary["selected_nine_condition_gate_passed"] = bool(
        len(condition_rows)
        == summary["selected_nine_condition_pass_count"]
        == 32
    )
    summary["current_utilization_pass"] = bool(
        maximum_current is not None
        and maximum_current
        <= float(probe_cfg["maximum_current_utilization"])
    )
    summary["identification_passed"] = bool(
        summary["execution_gate_passed"]
        and summary["standalone_central_symmetry_gate_passed"]
        and summary["pc3_matched_history_gate_passed"]
        and summary["mixed_factorial_response_gate_passed"]
        and summary["mixed_matched_history_gate_passed"]
        and summary["selected_nine_condition_gate_passed"]
        and summary["current_utilization_pass"]
    )
    summary["linear_route_passed"] = bool(
        summary["identification_passed"]
        and summary["linear_route_context_pass_count"] == 32
    )
    summary["passed"] = summary["identification_passed"]
    if write_outputs:
        outputs = (
            ("results", rows),
            ("standalone_pc3_response_results", central_rows),
            ("pc3_matched_hidden_history_results", pc3_history_rows),
            ("mixed_factorial_results", factorial_rows),
            ("mixed_matched_hidden_history_results", mixed_history_rows),
            ("selected_nine_condition_results", condition_rows),
        )
        ctx.paths.control.mkdir(parents=True, exist_ok=True)
        for name, values in outputs:
            t1.r3c3.atomic_write_json(
                ctx.paths.control / f"{name}.json", values
            )
            t1.r3c3.write_csv(
                ctx.paths.control / f"{name}.csv", values
            )
        t1.r3c3.atomic_write_json(
            ctx.paths.control / "summary.json", summary
        )
    return summary


def analyze(
    ctx: Stage42R3C3T9Context,
    control_summary: Mapping[str, Any],
) -> dict[str, Any]:
    identification_passed = bool(
        control_summary.get("identification_passed")
    )
    linear_route_passed = bool(
        control_summary.get("linear_route_passed")
    )
    if not identification_passed:
        verdict_text = (
            "STAGE4_2R3C3T9_MIXED_INTERACTION_IDENTIFICATION_FAIL"
        )
    elif linear_route_passed:
        verdict_text = (
            "STAGE4_2R3C3T9_IDENTIFICATION_PASS_LINEAR_ROUTE_CANDIDATE"
        )
    else:
        verdict_text = (
            "STAGE4_2R3C3T9_IDENTIFICATION_PASS_INTERACTION_AWARE_REQUIRED"
        )
    verdict = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "verdict": verdict_text,
        "primary_pass": identification_passed,
        "identification_passed": identification_passed,
        "linear_route_passed": linear_route_passed,
        "identification_only": True,
        "formal_tracking_is_acceptance_gate": False,
        "observation_horizon_is_long_hold_validation": False,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "development_set_only": True,
        "independent_hidden_history_confirmation": False,
        "r3c4_implementation_authorized": False,
        "bc_dagger_or_rl_allowed": False,
        "next_if_linear_route_passes": (
            "Build the authenticated measured nine-basis bank and require "
            "unchanged-contract optimistic feasibility 32/32."
        ),
        "next_if_interaction_aware_required": (
            "Preregister an interaction-aware response model using the "
            "measured mixed contrast; do not discard the interaction."
        ),
        "next_if_identification_fails": (
            "Preserve raw and redesign identification without weakening "
            "timing, restart, history, response, current, or condition gates."
        ),
    }
    t1.r3c3.atomic_write_json(
        ctx.paths.analysis / "stage4_2r3c3t9_summary.json",
        dict(control_summary),
    )
    t1.r3c3.atomic_write_json(
        ctx.paths.analysis / "stage4_2r3c3t9_verdict.json", verdict
    )
    state = t1.r3c3.read_json(ctx.paths.state)
    state.update(
        {
            "finished": True,
            "primary_pass": identification_passed,
            "linear_route_passed": linear_route_passed,
            "phase_status": "campaign_complete",
            "stop_reason": (
                "" if identification_passed else "identification_gate_failed"
            ),
            "verdict": verdict,
            "updated_utc": t1.r3c3.utc_timestamp(),
        }
    )
    t1.r3c3.atomic_write_json(ctx.paths.state, state)
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "control_summary": dict(control_summary),
        "verdict": verdict,
    }


def execute(
    ctx: Stage42R3C3T9Context,
    *,
    command: str,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    selected_pairs, specs = prepare(ctx, resume=resume)
    offline = run_offline_probe_audit(
        ctx, selected_pairs, allow_existing_raw=resume
    )
    if not bool(offline.get("passed")):
        raise RuntimeError(
            "Stage4.2R3c3T9 offline gate failed; no real TSC started"
        )
    if command == "offline":
        state = t1.r3c3.read_json(ctx.paths.state)
        state.update(
            {
                "finished": False,
                "primary_pass": False,
                "linear_route_passed": False,
                "phase_status": "offline_gate_complete",
                "stop_reason": "",
                "offline_probe_audit": dict(offline),
                "updated_utc": t1.r3c3.utc_timestamp(),
            }
        )
        t1.r3c3.atomic_write_json(ctx.paths.state, state)
        return {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "phase": "offline_pc3_mixed_interaction_probe_audit",
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
    cfg = t1.r3c3.read_json(
        _project_root()
        / "configs/stage4_2r3c3t9_pc3_mixed_interaction_"
        "identification_500ms.json"
    )
    _validate_config(cfg)
    path, preflight = _authenticate_preflight(cfg)
    cases = []
    for case in preflight["actuator_cases"]:
        schedules = [
            case["standalone_pc3_probe"],
            *case["mixed_factorial"]["probes"],
        ]
        rows = []
        for frozen in schedules:
            schedule = _schedule(frozen)
            delay = int(case["delay_steps"])
            effects = sorted(step + delay + 1 for step in schedule)
            rows.append(
                {
                    "probe_id": frozen["probe_id"],
                    "issue_count": len(schedule),
                    "cancellation_effect_states": effects[35:],
                    "requested_net": np.sum(
                        np.stack(list(schedule.values())), axis=0
                    ).tolist(),
                }
            )
        cases.append(
            {
                "delay_steps": int(case["delay_steps"]),
                "slew_scale": float(case["slew_scale"]),
                "schedules": rows,
            }
        )
    passed = bool(
        len(cases) == 2
        and all(
            len(case["schedules"]) == 5
            and all(
                row["issue_count"] == 41
                and row["cancellation_effect_states"]
                == [39, 40, 41, 42, 43, 44]
                and max(abs(value) for value in row["requested_net"])
                <= 1.0e-12
                for row in case["schedules"]
            )
            for case in cases
        )
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "design_revision": 1,
        "candidate_preflight_path": str(path),
        "candidate_preflight_sha256": _sha256(path),
        "expected_rollouts": 224,
        "cases": cases,
        "identification_only": True,
        "real_tsc_executed": False,
        "formal_timing_unchanged": True,
        "bc_dagger_or_rl_allowed": False,
        "passed": passed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage4.2R3c3T9 PC3 mixed-interaction identification"
    )
    parser.add_argument("--config", type=Path)
    parser.add_argument("--source-stage4-2r3b-run", type=Path)
    parser.add_argument("--source-stage4-2r3c3-run", type=Path)
    parser.add_argument("--source-stage4-2r3c3-bank-dir", type=Path)
    parser.add_argument("--source-stage4-2r3c3t1-run", type=Path)
    parser.add_argument("--source-stage4-2r3c3t1-audit-dir", type=Path)
    parser.add_argument(
        "--source-stage4-2r3c3t7-controller-bank", type=Path
    )
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
    t6._set_resource_limits()
    if args.self_test:
        print(json.dumps(self_test(), indent=2, sort_keys=True))
        return
    required = (
        ("--config", args.config),
        ("--source-stage4-2r3b-run", args.source_stage4_2r3b_run),
        ("--source-stage4-2r3c3-run", args.source_stage4_2r3c3_run),
        (
            "--source-stage4-2r3c3-bank-dir",
            args.source_stage4_2r3c3_bank_dir,
        ),
        ("--source-stage4-2r3c3t1-run", args.source_stage4_2r3c3t1_run),
        (
            "--source-stage4-2r3c3t1-audit-dir",
            args.source_stage4_2r3c3t1_audit_dir,
        ),
        (
            "--source-stage4-2r3c3t7-controller-bank",
            args.source_stage4_2r3c3t7_controller_bank,
        ),
        ("--run-dir", args.run_dir),
    )
    missing = [name for name, value in required if value is None]
    if missing:
        parser.error("missing required arguments: " + ", ".join(missing))
    ctx = load_stage42r3c3t9_config(
        args.config,
        source_stage42r3b_run=args.source_stage4_2r3b_run,
        source_stage42r3c3_run=args.source_stage4_2r3c3_run,
        source_stage42r3c3_bank_dir=args.source_stage4_2r3c3_bank_dir,
        source_stage42r3c3t1_run=args.source_stage4_2r3c3t1_run,
        source_stage42r3c3t1_audit_dir=(
            args.source_stage4_2r3c3t1_audit_dir
        ),
        source_stage42r3c3t7_controller_bank=(
            args.source_stage4_2r3c3t7_controller_bank
        ),
        run_dir_override=args.run_dir,
    )
    ctx.cfg["parallel"]["n_workers"] = int(
        ctx.cfg["parallel"]["n_workers"]
    )
    result = execute(
        ctx,
        command=args.command,
        backend=args.backend,
        resume=bool(args.resume),
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
