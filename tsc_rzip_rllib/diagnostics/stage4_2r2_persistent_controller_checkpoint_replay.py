"""Stage4.2R2 persistent controller-state checkpoint/replay certification.

R1 certified the authentic TSC ``sprsina`` plant restart interface while
replaying frozen future actions.  R2 deliberately removes that crutch.  It
persists only controller information available at state index 20, starts a
fresh TSC process from the certified R1 plant snapshot, restores the
controller state, and computes every later action online.

The first R2 envelope is intentionally the same finite clean 18-case expert
map used by R1.  Its purpose is exact controller restart, not robustness
generalization.  A controller checkpoint contains the causal measurement
history, integral, previous correction, pending physical-delay queue, trusted
calibration token/model, controller phase, and source fingerprints.  It is
rejected if it contains a future action or a measurement after the checkpoint.

Passing R2 does not validate matched-visible/different-hidden histories,
different initial states, unseen targets, continuous actuator parameters,
plant/Jacobian error, noise, disturbances, long hold, deployment, BC, DAgger,
or RL.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
try:
    import resource
except ImportError:  # pragma: no cover - Windows validation host.
    resource = None
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from . import stage2_trajectory_optimization as s2
from . import stage4_1r3_control_aware_robustness as r3
from . import stage4_1r9_terminal_template_mpc_feedback_hold as r9
from . import stage4_1r10_queue_preview_terminal_transition_hold as r10
from . import stage4_1r12_original_deadline_weak_slew_anticipatory_damping as r12
from . import stage4_2r1_true_tsc_plant_restart_action_replay as r1
from tsc_rzip_rllib.utils.ray_runtime import ensure_ray_worker_plan


SCHEMA_VERSION = 1
STAGE = "Stage4.2R2"
CONTROLLER_REVISION = "persistent_mpc_controller_checkpoint_replay_v42r2"
PACKAGE_REVISION = "r42r2_persistent_controller_checkpoint_v1"
CHECKPOINT_STEP = 20
DT_MS = 10
NORMAL_HORIZON = 35
WEAK_HORIZON = 37
N_COILS = 14
N_MODES = 3
EXPECTED_R1_PACKAGE = r1.PACKAGE_REVISION
EXPECTED_R1_CONTROLLER = r1.CONTROLLER_REVISION

atomic_write_json = r1.atomic_write_json
atomic_write_json_gz = r1.atomic_write_json_gz
read_json = r1.read_json
read_json_gz = r1.read_json_gz
write_csv = r1.write_csv
utc_timestamp = r1.utc_timestamp


def _json_safe(value: Any) -> Any:
    return r1._json_safe(value)


def _sha256_file(path: Path) -> str:
    return r1._sha256_file(path)


def _canonical_digest(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        _json_safe(dict(payload)),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _scenario_digest(payload: Mapping[str, Any]) -> str:
    return "s42r2_" + _canonical_digest(payload)[:20]


def _case_key(result_or_spec: Mapping[str, Any]) -> tuple[str, int, float]:
    return r1._case_key(result_or_spec)


def _formal_horizon(slew: float) -> int:
    return WEAK_HORIZON if math.isclose(float(slew), 0.9, abs_tol=1e-12) else NORMAL_HORIZON


def _strict_checkpoint_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    output = copy.deepcopy(dict(payload))
    forbidden = {
        "source_actions",
        "source_suffix_actions",
        "future_actions",
        "future_measurements",
        "source_future_trajectory",
    }
    def forbidden_paths(value: Any, prefix: str = "") -> list[str]:
        found: list[str] = []
        if isinstance(value, Mapping):
            for key, item in value.items():
                key_text = str(key)
                path = f"{prefix}.{key_text}" if prefix else key_text
                if key_text in forbidden:
                    found.append(path)
                found.extend(forbidden_paths(item, path))
        elif isinstance(value, (list, tuple)):
            for index, item in enumerate(value):
                found.extend(forbidden_paths(item, f"{prefix}[{index}]"))
        return found

    present = sorted(forbidden_paths(output))
    if present:
        raise ValueError(f"controller checkpoint contains forbidden future data: {present}")
    if int(output.get("checkpoint_step", -1)) != CHECKPOINT_STEP:
        raise ValueError("controller checkpoint step changed")
    history = list(output.get("measurement_history") or [])
    if not history:
        raise ValueError("controller checkpoint has no measurement history")
    indices = [int(row["state_index"]) for row in history]
    if indices != list(range(CHECKPOINT_STEP + 1)):
        raise ValueError("controller checkpoint measurement history is not causal/contiguous")
    if max(indices) > CHECKPOINT_STEP:
        raise ValueError("controller checkpoint contains a future measurement")
    queue = list(output.get("pending_delay_queue") or [])
    delay = int(output["modeled_delay_steps"])
    if len(queue) != delay:
        raise ValueError("controller checkpoint pending queue length mismatch")
    for row in queue:
        for name in ("command", "desired_physical"):
            vector = np.asarray(row[name], dtype=float)
            if vector.shape != (N_MODES,) or not np.all(np.isfinite(vector)):
                raise ValueError(f"invalid checkpoint queue {name}")
    for name, size in (
        ("integral_normalized", 5),
        ("previous_correction_physical", N_MODES),
        ("checkpoint_action_norm_tsc", N_COILS),
    ):
        vector = np.asarray(output[name], dtype=float)
        if vector.shape != (size,) or not np.all(np.isfinite(vector)):
            raise ValueError(f"invalid controller checkpoint field {name}")
    if not bool(output.get("trusted_calibration_model")):
        raise ValueError("controller checkpoint calibration model is not trusted")
    if not str(output.get("calibration_token", "")).strip():
        raise ValueError("controller checkpoint calibration token missing")
    recorded = str(output.pop("digest", ""))
    actual = _canonical_digest(output)
    if recorded and recorded != actual:
        raise ValueError("controller checkpoint digest mismatch")
    output["digest"] = actual
    return output


@dataclass(frozen=True)
class Stage42R2Paths:
    run_dir: Path
    source_reference: Path
    checkpoint_bank: Path
    offline_audit: Path
    variants: Path
    replay: Path
    analysis: Path
    manifest: Path
    state: Path

    @classmethod
    def from_run_dir(cls, run_dir: Path) -> "Stage42R2Paths":
        root = run_dir.expanduser().resolve()
        return cls(
            run_dir=root,
            source_reference=root / "stage4_2r2_source_reference",
            checkpoint_bank=root / "stage4_2r2_controller_checkpoint_bank",
            offline_audit=root / "stage4_2r2_offline_controller_recomputation_audit",
            variants=root / "stage4_2r2_restart_variants",
            replay=root / "stage4_2r2_controller_restart_replay",
            analysis=root / "stage4_2r2_analysis",
            manifest=root / "stage4_2r2_manifest.json",
            state=root / "stage4_2r2_state.json",
        )


@dataclass
class Stage42R2Context:
    cfg: dict[str, Any]
    paths: Stage42R2Paths
    project_dir: Path
    source_r1_run: Path
    source_r17_run: Path
    r1_ctx: r1.Stage42R1Context
    source_r1_manifest: dict[str, Any]
    source_r1_state: dict[str, Any]
    source_fingerprint: dict[str, Any]


def validate_config(cfg: Mapping[str, Any]) -> None:
    if str(cfg.get("stage_label")) != STAGE:
        raise ValueError("Stage4.2R2 stage label mismatch")
    if str(cfg.get("controller_revision")) != CONTROLLER_REVISION:
        raise ValueError("Stage4.2R2 controller revision mismatch")
    if str(cfg.get("package_revision")) != PACKAGE_REVISION:
        raise ValueError("Stage4.2R2 package revision mismatch")
    checkpoint = cfg["checkpoint"]
    if int(checkpoint["step"]) != CHECKPOINT_STEP or int(checkpoint["elapsed_ms"]) != 200:
        raise ValueError("Stage4.2R2 checkpoint timing changed")
    matrix = cfg["matrix"]
    if int(matrix["expected_rollouts"]) != 18:
        raise ValueError("Stage4.2R2 rollout matrix changed")
    timing = cfg["formal_timing_contract"]
    if int(timing["normal"]["arrival_deadline_step"]) != 25:
        raise ValueError("Stage4.2R2 normal deadline changed")
    if int(timing["normal"]["hold_through_step"]) != 35:
        raise ValueError("Stage4.2R2 normal hold changed")
    if int(timing["weak"]["arrival_deadline_step"]) != 27:
        raise ValueError("Stage4.2R2 weak deadline changed")
    if int(timing["weak"]["hold_through_step"]) != 37:
        raise ValueError("Stage4.2R2 weak hold changed")
    if bool(timing.get("arrival_deadline_expansion_allowed", True)):
        raise ValueError("Stage4.2R2 may not expand the formal deadline")
    requirements = cfg["controller_checkpoint_requirements"]
    for name in (
        "require_measurement_history",
        "require_integrator",
        "require_previous_correction",
        "require_pending_delay_queue",
        "require_trusted_calibration_token",
        "require_controller_phase",
        "forbid_future_measurements",
        "forbid_future_actions",
        "require_online_action_recomputation",
        "require_exact_same_source_replay",
        "require_offline_no_gotsc_action_recomputation_gate",
        "frozen_policy_time_schedule_is_controller_code_not_recorded_action_suffix",
    ):
        if not bool(requirements.get(name)):
            raise ValueError(f"Stage4.2R2 requirement weakened: {name}")


def _source_fingerprint(source_r1: Path) -> dict[str, Any]:
    required = [
        "stage4_2r1_manifest.json",
        "stage4_2r1_state.json",
        "stage4_2r1_config.resolved.json",
        "stage4_2r1_analysis/stage4_2r1_verdict.json",
        "stage4_2r1_plant_checkpoint_capture/results.json",
        "stage4_2r1_plant_checkpoint_capture/summary.json",
        "stage4_2r1_plant_restart_replay/results.json",
        "stage4_2r1_plant_restart_replay/summary.json",
        "stage4_2r1_source_reference/selected_expert_inventory.json",
    ]
    rows = []
    for relative in required:
        path = source_r1 / relative
        if not path.is_file():
            raise FileNotFoundError(f"R1 source evidence missing: {path}")
        rows.append(
            {
                "path": relative,
                "size_bytes": path.stat().st_size,
                "sha256": _sha256_file(path),
            }
        )
    for phase in (
        "stage4_2r1_plant_checkpoint_capture/raw",
        "stage4_2r1_plant_restart_replay/raw",
    ):
        paths = sorted((source_r1 / phase).glob("*.json.gz"))
        if len(paths) != 18:
            raise ValueError(f"R1 source raw coverage mismatch: {phase}")
        for path in paths:
            rows.append(
                {
                    "path": path.relative_to(source_r1).as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": _sha256_file(path),
                }
            )
    snapshot_manifests = sorted(
        (source_r1 / "stage4_2r1_restart_bank").rglob("restart_snapshot_manifest.json")
    )
    if len(snapshot_manifests) != 18:
        raise ValueError("R1 source snapshot manifest coverage mismatch")
    for path in snapshot_manifests:
        manifest = read_json(path)
        if not bool(manifest.get("passed")) or manifest.get("missing_required_files"):
            raise ValueError(f"R1 source snapshot manifest failed: {path}")
        snapshot_dir = path.parent
        files = list(manifest.get("files") or [])
        if len(files) != int(manifest.get("n_files", -1)):
            raise ValueError(f"R1 source snapshot manifest inventory mismatch: {path}")
        for item in files:
            payload_path = snapshot_dir / str(item["name"])
            if not payload_path.is_file():
                raise FileNotFoundError(
                    f"R1 source snapshot payload missing: {payload_path}"
                )
            size_bytes = payload_path.stat().st_size
            sha256 = _sha256_file(payload_path)
            if size_bytes != int(item["size_bytes"]) or sha256 != str(item["sha256"]):
                raise ValueError(
                    f"R1 source snapshot payload fingerprint mismatch: {payload_path}"
                )
            rows.append(
                {
                    "path": payload_path.relative_to(source_r1).as_posix(),
                    "size_bytes": size_bytes,
                    "sha256": sha256,
                    "snapshot_manifest_digest": manifest["digest"],
                }
            )
        rows.append(
            {
                "path": path.relative_to(source_r1).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": _sha256_file(path),
                "snapshot_digest": manifest["digest"],
            }
        )
    rows.sort(key=lambda row: row["path"])
    return {
        "schema_version": 1,
        "contract": "r42r2_certified_r1c_raw_and_snapshot_manifest_v1",
        "n_files": len(rows),
        "digest": _canonical_digest({"files": rows}),
        "files": rows,
    }


def load_stage42r2_config(
    config_path: Path,
    *,
    source_stage42r1_run: Path,
    run_dir_override: Path | None = None,
) -> Stage42R2Context:
    config_path = config_path.expanduser().resolve()
    cfg = read_json(config_path)
    validate_config(cfg)
    project_dir = config_path.parents[1]
    source_r1 = source_stage42r1_run.expanduser().resolve()
    manifest = read_json(source_r1 / "stage4_2r1_manifest.json")
    state = read_json(source_r1 / "stage4_2r1_state.json")
    if str(manifest.get("package_revision")) != EXPECTED_R1_PACKAGE:
        raise ValueError("Stage4.2R2 requires certified R1c package")
    if str(manifest.get("controller_revision")) != EXPECTED_R1_CONTROLLER:
        raise ValueError("Stage4.2R2 R1 controller identity mismatch")
    if not bool(state.get("finished")) or not bool(state.get("primary_pass")):
        raise ValueError("Stage4.2R2 requires a finished passing R1 source")
    source_r17 = Path(str(manifest["source_stage4_1r17_run"])).expanduser().resolve()
    r1_config = (
        project_dir
        / "configs"
        / "stage4_2r1_true_tsc_plant_restart_action_replay_370ms.json"
    )
    r1_ctx = r1.load_stage42r1_config(
        r1_config,
        source_stage41r17_run=source_r17,
        run_dir_override=source_r1,
    )
    if run_dir_override is None:
        root = project_dir / str(cfg.get("output_root", "stage4_2r2_runs"))
        run_dir = root / f"{cfg['run_name']}_{utc_timestamp()}"
    else:
        run_dir = run_dir_override.expanduser().resolve()
    return Stage42R2Context(
        cfg=cfg,
        paths=Stage42R2Paths.from_run_dir(run_dir),
        project_dir=project_dir,
        source_r1_run=source_r1,
        source_r17_run=source_r17,
        r1_ctx=r1_ctx,
        source_r1_manifest=manifest,
        source_r1_state=state,
        source_fingerprint=_source_fingerprint(source_r1),
    )


def _selected_sources(ctx: Stage42R2Context) -> dict[tuple[str, int, float], dict[str, Any]]:
    return r1._selected_source_cases(ctx.r1_ctx)


def _captures(ctx: Stage42R2Context) -> dict[tuple[str, int, float], dict[str, Any]]:
    return r1._capture_results_by_case(ctx.r1_ctx)


def _r1_restarts(ctx: Stage42R2Context) -> dict[tuple[str, int, float], dict[str, Any]]:
    output: dict[tuple[str, int, float], dict[str, Any]] = {}
    for path in sorted(
        (ctx.source_r1_run / "stage4_2r1_plant_restart_replay" / "raw").glob("*.json.gz")
    ):
        result = read_json_gz(path)
        key = _case_key(result)
        if key in output:
            raise ValueError(f"duplicate R1 restart source case: {key}")
        output[key] = result
    return output


def _main_trace(source: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = list(
        source.get("main_control_trace")
        or source.get("original_main_control_trace")
        or source.get("control_trace")
        or []
    )
    if len(rows) < CHECKPOINT_STEP:
        raise ValueError("source main controller trace does not cover checkpoint")
    return copy.deepcopy(rows)


def _checkpoint_controller_phase(source: Mapping[str, Any]) -> str:
    spec = source["spec"]
    transition = spec.get("anticipatory_transition_issue_step")
    if transition is not None and int(transition) == CHECKPOINT_STEP:
        return "anticipatory_damping"
    return "main_control"


def _checkpoint_payload(
    ctx: Stage42R2Context,
    key: tuple[str, int, float],
    source: Mapping[str, Any],
    capture: Mapping[str, Any],
) -> dict[str, Any]:
    spec = copy.deepcopy(dict(source["spec"]))
    if not bool(spec.get("trusted_calibration_model")):
        raise ValueError(f"R2 source calibration is not trusted: {key}")
    if int(spec["action_delay_steps"]) != int(spec["controller_action_delay_steps"]):
        raise ValueError(f"R2 source delay model mismatch: {key}")
    if not math.isclose(
        float(spec["slew_scale"]),
        float(spec["controller_slew_scale_estimate"]),
        abs_tol=1e-12,
    ):
        raise ValueError(f"R2 source slew model mismatch: {key}")
    if spec.get("actual_action_delay_schedule") or spec.get("actual_slew_scale_schedule"):
        raise ValueError("R2 exact checkpoint source must use static actuator parameters")
    if spec.get("controller_action_delay_schedule") or spec.get("controller_slew_scale_schedule"):
        raise ValueError("R2 exact checkpoint source must use static controller parameters")
    if bool((spec.get("adaptive_delay_slew_estimator") or {}).get("enabled")):
        raise ValueError("R2 exact checkpoint source must use the frozen trusted model")
    if not r3._sensor_path_is_clean(spec):
        raise ValueError("R2 exact checkpoint source must use clean sensing")
    trajectory = list(source["trajectory"])
    capture_trajectory = list(capture["trajectory"])
    horizon = _formal_horizon(key[2])
    if len(trajectory) < horizon + 1 or len(capture_trajectory) != horizon + 1:
        raise ValueError(f"R2 source/capture trajectory length mismatch: {key}")
    if not np.array_equal(
        r1._visible_array({"trajectory": trajectory[: horizon + 1]}),
        r1._visible_array(capture),
    ):
        raise ValueError(f"R2 capture is not exact to source: {key}")
    trace = _main_trace(source)
    previous_row = trace[CHECKPOINT_STEP - 1]
    delay = int(spec["controller_action_delay_steps"])
    queue = []
    for row in trace[CHECKPOINT_STEP - delay : CHECKPOINT_STEP]:
        queue.append(
            {
                "origin": "main_control",
                "origin_index": int(row["step"]),
                "command": copy.deepcopy(row["issued_mode_coefficients"]),
                "desired_physical": copy.deepcopy(
                    row["issued_desired_physical_mode_coefficients"]
                ),
            }
        )
    measurement_history = [
        {
            "state_index": index,
            "R": float(row["R"]),
            "Z": float(row["Z"]),
            "Ip": float(row["Ip"]),
        }
        for index, row in enumerate(trajectory[: CHECKPOINT_STEP + 1])
    ]
    checkpoint_action = np.asarray(
        capture_trajectory[CHECKPOINT_STEP]["action_norm_tsc"], dtype=float
    ).reshape(N_COILS)
    snapshot = capture["restart_snapshot"]
    source_path = next(
        Path(row["path"])
        for row in ctx.r1_ctx.expert_fingerprint["files"]
        if str(row["experiment_id"]) == str(source["experiment_id"])
    )
    capture_path = (
        ctx.source_r1_run
        / "stage4_2r1_plant_checkpoint_capture"
        / "raw"
        / f"{capture['experiment_id']}.json.gz"
    )
    payload = {
        "schema_version": 1,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "checkpoint_step": CHECKPOINT_STEP,
        "checkpoint_elapsed_ms": CHECKPOINT_STEP * DT_MS,
        "target_id": key[0],
        "actual_delay_steps": key[1],
        "actual_slew_scale": key[2],
        "modeled_delay_steps": int(spec["controller_action_delay_steps"]),
        "modeled_slew_scale": float(spec["controller_slew_scale_estimate"]),
        "trusted_calibration_model": True,
        "calibration_token": str(spec["calibration_token"]),
        "source_controller_revision": str(source["controller_revision"]),
        "source_controller_variant": str(spec.get("controller_variant", "")),
        "controller_phase": _checkpoint_controller_phase(source),
        "phase_transition_issue_step": (
            None
            if spec.get("anticipatory_transition_issue_step") is None
            else int(spec["anticipatory_transition_issue_step"])
        ),
        "formal_horizon_steps": horizon,
        "measurement_history": measurement_history,
        "observer_state": {
            "enabled": bool(spec.get("observer_enabled")),
            "variant": str(spec.get("observer_variant", "legacy_raw")),
            "clean_measurement_bypass": True,
            "dynamic_state_required": False,
            "legacy_observer_state": None,
            "control_aware_residual_observer_state": None,
            "measurement_history_max_state_index": CHECKPOINT_STEP,
            "future_measurement_used": False,
        },
        "integral_normalized": copy.deepcopy(previous_row["integral_normalized"]),
        "previous_correction_physical": copy.deepcopy(
            previous_row["mode_correction_physical"]
        ),
        "pending_delay_queue": queue,
        "issued_command_history_count": CHECKPOINT_STEP,
        "last_issued_command": copy.deepcopy(previous_row["issued_mode_coefficients"]),
        "checkpoint_action_norm_tsc": checkpoint_action.tolist(),
        "controller_spec": spec,
        "controller_spec_digest": _canonical_digest(spec),
        "source_experiment_id": str(source["experiment_id"]),
        "source_raw_sha256": _sha256_file(source_path),
        "capture_experiment_id": str(capture["experiment_id"]),
        "capture_raw_sha256": _sha256_file(capture_path),
        "plant_snapshot_dir": str(snapshot["snapshot_dir"]),
        "plant_snapshot_manifest_path": str(snapshot["snapshot_manifest_path"]),
        "plant_snapshot_manifest_digest": str(snapshot["snapshot_manifest_digest"]),
        "checkpoint_visible": r1._visible_array(
            {"trajectory": [capture_trajectory[CHECKPOINT_STEP]]}
        )[0].tolist(),
        "checkpoint_wire_currents_a": copy.deepcopy(
            capture_trajectory[CHECKPOINT_STEP]["wire_currents_a"]
        ),
        "future_measurement_count": 0,
        "future_action_count": 0,
        "online_action_recomputation_required": True,
        "frozen_policy_time_schedule_is_controller_code_not_recorded_action_suffix": True,
    }
    payload["digest"] = _canonical_digest(payload)
    return _strict_checkpoint_payload(payload)


def build_controller_checkpoints(ctx: Stage42R2Context) -> list[dict[str, Any]]:
    sources = _selected_sources(ctx)
    captures = _captures(ctx)
    if set(sources) != set(captures) or len(sources) != 18:
        raise ValueError("Stage4.2R2 source/capture coverage mismatch")
    rows = []
    for key in sorted(sources, key=lambda item: (item[2], item[1], item[0])):
        checkpoint = _checkpoint_payload(ctx, key, sources[key], captures[key])
        path = (
            ctx.paths.checkpoint_bank
            / str(captures[key]["experiment_id"])
            / "controller_checkpoint.json"
        )
        atomic_write_json(path, checkpoint)
        rows.append(
            {
                "target_id": key[0],
                "actual_delay_steps": key[1],
                "actual_slew_scale": key[2],
                "capture_experiment_id": captures[key]["experiment_id"],
                "source_experiment_id": sources[key]["experiment_id"],
                "controller_checkpoint_path": str(path),
                "controller_checkpoint_digest": checkpoint["digest"],
                "controller_phase": checkpoint["controller_phase"],
                "measurement_history_max_state_index": CHECKPOINT_STEP,
                "pending_queue_length": len(checkpoint["pending_delay_queue"]),
                "future_measurement_count": 0,
                "future_action_count": 0,
                "passed": True,
            }
        )
    atomic_write_json(ctx.paths.checkpoint_bank / "results.json", rows)
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "controller_checkpoint_materialization",
        "n_checkpoints": len(rows),
        "expected_checkpoints": 18,
        "coverage_complete": len(rows) == 18,
        "future_measurement_count": sum(row["future_measurement_count"] for row in rows),
        "future_action_count": sum(row["future_action_count"] for row in rows),
        "passed": bool(
            len(rows) == 18
            and all(row["passed"] for row in rows)
            and all(row["pending_queue_length"] == row["actual_delay_steps"] for row in rows)
        ),
    }
    atomic_write_json(ctx.paths.checkpoint_bank / "summary.json", summary)
    return rows


def _source_payload(ctx: Stage42R2Context, slew: float) -> dict[str, Any]:
    variant = f"slew_{float(slew):.3f}".replace(".", "p")
    horizon = _formal_horizon(slew)
    path = (
        ctx.source_r1_run
        / "stage4_2r1_restart_variants"
        / f"source_{variant}_h{horizon}.payload.json"
    )
    if not path.is_file():
        raise FileNotFoundError(f"R1 source payload missing: {path}")
    return read_json(path)


def _restart_payload(
    ctx: Stage42R2Context,
    key: tuple[str, int, float],
    r1_restart: Mapping[str, Any],
) -> dict[str, Any]:
    variant = str(r1_restart["spec"]["environment_variant"])
    env_path = ctx.source_r1_run / "stage4_2r1_restart_variants" / f"env_{variant}.json"
    train_path = ctx.source_r1_run / "stage4_2r1_restart_variants" / f"train_{variant}.json"
    payload = _source_payload(ctx, key[2])
    payload["env_cfg"] = read_json(env_path)
    payload["train_cfg"] = read_json(train_path)
    payload["variant_id"] = variant
    payload["start_folder"] = Path(str(r1_restart["spec"]["restart_snapshot_dir"])).name
    payload["slew_scale"] = key[2]
    payload["stage4_1r4_horizon_steps"] = _formal_horizon(key[2]) - CHECKPOINT_STEP
    return payload


class PersistentController:
    """Finite-envelope controller continuation with explicit persistent state."""

    def __init__(self, base_worker: Any, bundle: Mapping[str, Any], checkpoint: Mapping[str, Any]):
        self.base = base_worker
        self.bundle = bundle
        self.checkpoint = _strict_checkpoint_payload(checkpoint)
        self.spec = copy.deepcopy(self.checkpoint["controller_spec"])
        self.step = CHECKPOINT_STEP
        self.delay = int(self.checkpoint["modeled_delay_steps"])
        self.actual_delay = int(self.checkpoint["actual_delay_steps"])
        self.slew = float(self.checkpoint["modeled_slew_scale"])
        self.integral = np.asarray(
            self.checkpoint["integral_normalized"], dtype=float
        ).reshape(5)
        self.previous = np.asarray(
            self.checkpoint["previous_correction_physical"], dtype=float
        ).reshape(N_MODES)
        self.queue = [
            {
                "origin": str(row["origin"]),
                "origin_index": int(row["origin_index"]),
                "command": np.asarray(row["command"], dtype=float).reshape(N_MODES),
                "desired_physical": np.asarray(
                    row["desired_physical"], dtype=float
                ).reshape(N_MODES),
            }
            for row in self.checkpoint["pending_delay_queue"]
        ]
        self.history = [
            {
                "step_index": int(row["state_index"]),
                "R": float(row["R"]),
                "Z": float(row["Z"]),
                "Ip": float(row["Ip"]),
            }
            for row in self.checkpoint["measurement_history"]
        ]
        offset = np.asarray(
            [
                self.spec.get("target_R_offset_m", 0.0),
                self.spec.get("target_Z_offset_m", 0.0),
                self.spec.get("target_Ip_offset_A", 0.0),
            ],
            dtype=float,
        )
        interpolation = r3.s34.interpolation_for_target(
            self.base.stub, self.base.library, offset
        )
        self.nominal_physical = np.asarray(
            interpolation["full_control_vector"], dtype=float
        ).reshape(35, N_MODES)
        self.nominal_y = np.asarray(
            interpolation["nominal_trajectory_RZI"], dtype=float
        )
        self.nominal_velocity = np.asarray(
            interpolation["nominal_velocity_RZ"], dtype=float
        )
        self.target = np.asarray(
            [
                float(self.base.cfg["target"]["R"]) + offset[0],
                float(self.base.cfg["target"]["Z"]) + offset[1],
                float(self.base.cfg["target"]["Ip"]) + offset[2],
            ],
            dtype=float,
        )
        self.nominal_feature = r3.s34._nominal_feature(
            self.nominal_y, self.nominal_velocity, self.target
        )
        scales = self.base.cfg["identification"]["output_scales"]
        self.measurement_scales = np.asarray(
            [
                scales["R_m"],
                scales["Z_m"],
                scales["vR_m_per_s"],
                scales["vZ_m_per_s"],
                scales["Ip_A"],
            ],
            dtype=float,
        )
        self.dt_s = float(self.base.env_cfg["dt_ms"]) / 1000.0
        self.controller_gain = np.asarray(
            self.spec.get("controller_gain_estimate_by_mode", [1.0] * N_MODES),
            dtype=float,
        )
        self.actual_gain = np.asarray(
            self.spec.get("actuator_gain_by_mode", [1.0] * N_MODES),
            dtype=float,
        )
        self.actuator_bias = np.asarray(
            self.spec.get("actuator_bias_by_mode", [0.0] * N_MODES),
            dtype=float,
        )
        self.phase = str(self.checkpoint["controller_phase"])
        self.transition_step = self.checkpoint.get("phase_transition_issue_step")
        if self.transition_step is not None:
            self.transition_step = int(self.transition_step)
        self.damping_integral = np.zeros(5, dtype=float)
        self.terminal_integral = np.zeros(5, dtype=float)

    def replace_checkpoint_state(self, state: Mapping[str, Any]) -> None:
        if int(state["step_index"]) != CHECKPOINT_STEP:
            raise ValueError("fresh plant checkpoint index mismatch")
        self.history[-1] = {
            "step_index": CHECKPOINT_STEP,
            "R": float(state["R"]),
            "Z": float(state["Z"]),
            "Ip": float(state["Ip"]),
        }

    def append_state(self, state: Mapping[str, Any]) -> None:
        self.history.append(
            {
                "step_index": int(state["step_index"]),
                "R": float(state["R"]),
                "Z": float(state["Z"]),
                "Ip": float(state["Ip"]),
            }
        )

    def _main_action(self, currents: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
        step = self.step
        history_values = [
            np.asarray([row["R"], row["Z"], row["Ip"]], dtype=float)
            for row in self.history
        ]
        measurement_physical = r3.legacy_measurement_error(
            history_values,
            delayed_local_index=len(history_values) - 1,
            delayed_absolute_index=step,
            current_absolute_index=step,
            nominal_y=self.nominal_y,
            nominal_velocity=self.nominal_velocity,
            dt_s=self.dt_s,
        )
        measurement = measurement_physical / self.measurement_scales
        integral_candidate = self.base._integral_candidate(
            self.integral,
            measurement,
            reference_step=step,
            anti_windup_enabled=False,
        )
        pending = [
            np.asarray(item["desired_physical"], dtype=float)
            for item in self.queue[: self.delay]
        ]
        solve = r3.solve_delay_aware_physical_correction(
            self.base.stub,
            self.bundle,
            current_step=min(step, 34),
            modeled_action_delay_steps=self.delay,
            modeled_pending_physical_coefficients=pending,
            nominal_physical_coefficients=self.nominal_physical,
            nominal_feature=self.nominal_feature,
            measurement_normalized=measurement,
            integral_normalized=integral_candidate,
            previous_correction=self.previous,
            controller_scale=float(self.spec["controller_scale"]),
            controller_model_scale=float(self.spec.get("controller_model_scale", 1.0)),
        )
        correction = np.asarray(solve["first_correction"], dtype=float).reshape(N_MODES)
        self.integral = integral_candidate
        effect_step = min(int(solve.get("effect_step", step)), 34)
        desired = np.clip(
            self.nominal_physical[effect_step] + correction,
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
        issued = np.asarray(scheduled["command"], dtype=float).reshape(N_MODES)
        issued_item = {
            "origin": "main_control",
            "origin_index": step,
            "command": issued,
            "desired_physical": desired,
        }
        applied, self.queue = r9._stream_queue_apply(
            self.queue, issued_item, self.actual_delay
        )
        effective = (
            self.actual_gain * np.asarray(applied["command"], dtype=float)
            + self.actuator_bias
        )
        action = self.base._mode_action(effective, currents)
        trace = {
            "step": step,
            "controller_phase": "main_control",
            "computed_online": True,
            "measurement_max_state_index_used": step,
            "future_measurement_used": False,
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
            "queue_after": r9._queue_origins(self.queue),
            "action_norm_tsc": np.asarray(action, dtype=float).tolist(),
            "solver_success": bool(solve.get("solver_success")),
        }
        self.previous = correction
        return action, trace

    def _damping_action(self, currents: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
        step = self.step
        measurement_physical = r9._terminal_measurement(
            self.history, self.target, self.dt_s
        )
        normalized, for_solver = r12._measurement_for_solver(
            measurement_physical,
            self.measurement_scales,
            position_gain=float(self.spec["terminal_position_measurement_gain"]),
            velocity_gain=float(self.spec["terminal_velocity_measurement_gain"]),
            ip_gain=float(self.spec.get("terminal_ip_measurement_gain", 1.0)),
        )
        pending = [
            np.asarray(item["desired_physical"], dtype=float)
            for item in self.queue[: self.delay]
        ]
        solve = r3.solve_delay_aware_physical_correction(
            self.base.stub,
            self.bundle,
            current_step=min(step, int(self.spec["terminal_model_phase_cap_step"])),
            modeled_action_delay_steps=self.delay,
            modeled_pending_physical_coefficients=pending,
            nominal_physical_coefficients=np.zeros((35, N_MODES), dtype=float),
            nominal_feature=np.zeros(35 * 5, dtype=float),
            measurement_normalized=for_solver,
            integral_normalized=self.damping_integral,
            previous_correction=self.previous,
            controller_scale=float(self.spec["terminal_controller_scale"]),
            controller_model_scale=float(
                self.spec.get("terminal_controller_model_scale", 1.0)
            ),
        )
        correction = np.asarray(solve["first_correction"], dtype=float).reshape(N_MODES)
        solver_step = min(
            step, int(self.spec["terminal_model_phase_cap_step"])
        )
        schedule = {
            int(issue_step): np.asarray(value, dtype=float).reshape(N_MODES)
            for issue_step, value in (
                self.spec.get("r15_probe_delta_by_issue_step") or {}
            ).items()
        }
        requested_probe = schedule.get(solver_step, np.zeros(N_MODES, dtype=float))
        baseline_correction = correction.copy()
        correction = np.clip(
            correction + requested_probe, self.base.lower_mode, self.base.upper_mode
        )
        applied_probe = correction - baseline_correction
        desired = np.clip(correction, self.base.lower_mode, self.base.upper_mode)
        scheduled = self.base.scheduler.solve_command(
            desired, currents, self.controller_gain, self.slew, enabled=True
        )
        issued = np.asarray(scheduled["command"], dtype=float).reshape(N_MODES)
        issued_item = {
            "origin": "anticipatory_damping",
            "origin_index": step,
            "command": issued,
            "desired_physical": desired,
        }
        applied, self.queue = r9._stream_queue_apply(
            self.queue, issued_item, self.actual_delay
        )
        effective = (
            self.actual_gain * np.asarray(applied["command"], dtype=float)
            + self.actuator_bias
        )
        action = self.base._mode_action(effective, currents)
        trace = {
            "step": step,
            "controller_phase": "anticipatory_damping",
            "computed_online": True,
            "measurement_max_state_index_used": step,
            "future_measurement_used": False,
            "measurement_physical": measurement_physical.tolist(),
            "measurement_normalized": normalized.tolist(),
            "measurement_for_solver": for_solver.tolist(),
            "integral_normalized": self.damping_integral.tolist(),
            "previous_correction_physical": self.previous.tolist(),
            "mode_correction_physical": correction.tolist(),
            "baseline_mode_correction_physical": baseline_correction.tolist(),
            "r15_probe_requested_delta": requested_probe.tolist(),
            "r15_probe_applied_delta": applied_probe.tolist(),
            "r15_identification_probe": bool(np.any(requested_probe != 0.0)),
            "issued_desired_physical_mode_coefficients": desired.tolist(),
            "issued_mode_coefficients": issued.tolist(),
            "applied_command_mode_coefficients": np.asarray(
                applied["command"], dtype=float
            ).tolist(),
            "queue_after": r9._queue_origins(self.queue),
            "action_norm_tsc": np.asarray(action, dtype=float).tolist(),
            "solver_success": bool(solve.get("solver_success")),
        }
        self.previous = desired
        return action, trace

    def _terminal_action(self, currents: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
        step = self.step
        measurement_physical = r9._terminal_measurement(
            self.history, self.target, self.dt_s
        )
        normalized, for_solver = r10._measurement_for_solver(
            measurement_physical,
            self.measurement_scales,
            position_gain=float(self.spec["terminal_position_measurement_gain"]),
            velocity_gain=float(self.spec["terminal_velocity_measurement_gain"]),
            ip_gain=float(self.spec.get("terminal_ip_measurement_gain", 1.0)),
        )
        pending = [
            np.asarray(item["desired_physical"], dtype=float)
            for item in self.queue[: self.delay]
        ]
        solve = r3.solve_delay_aware_physical_correction(
            self.base.stub,
            self.bundle,
            current_step=int(self.spec["terminal_template_step"]),
            modeled_action_delay_steps=self.delay,
            modeled_pending_physical_coefficients=pending,
            nominal_physical_coefficients=np.zeros((35, N_MODES), dtype=float),
            nominal_feature=np.zeros(35 * 5, dtype=float),
            measurement_normalized=for_solver,
            integral_normalized=self.terminal_integral,
            previous_correction=self.previous,
            controller_scale=float(self.spec["terminal_controller_scale"]),
            controller_model_scale=float(
                self.spec.get("terminal_controller_model_scale", 1.0)
            ),
        )
        correction = np.asarray(solve["first_correction"], dtype=float).reshape(N_MODES)
        desired = np.clip(correction, self.base.lower_mode, self.base.upper_mode)
        scheduled = self.base.scheduler.solve_command(
            desired, currents, self.controller_gain, self.slew, enabled=True
        )
        issued = np.asarray(scheduled["command"], dtype=float).reshape(N_MODES)
        issued_item = {
            "origin": "terminal_feedback",
            "origin_index": step - 35,
            "command": issued,
            "desired_physical": desired,
        }
        applied, self.queue = r9._stream_queue_apply(
            self.queue, issued_item, self.actual_delay
        )
        effective = (
            self.actual_gain * np.asarray(applied["command"], dtype=float)
            + self.actuator_bias
        )
        action = self.base._mode_action(effective, currents)
        trace = {
            "step": step,
            "controller_phase": "terminal_feedback",
            "computed_online": True,
            "measurement_max_state_index_used": step,
            "future_measurement_used": False,
            "measurement_physical": measurement_physical.tolist(),
            "measurement_normalized": normalized.tolist(),
            "measurement_for_solver": for_solver.tolist(),
            "integral_normalized": self.terminal_integral.tolist(),
            "previous_correction_physical": self.previous.tolist(),
            "mode_correction_physical": correction.tolist(),
            "issued_desired_physical_mode_coefficients": desired.tolist(),
            "issued_mode_coefficients": issued.tolist(),
            "applied_command_mode_coefficients": np.asarray(
                applied["command"], dtype=float
            ).tolist(),
            "queue_after": r9._queue_origins(self.queue),
            "action_norm_tsc": np.asarray(action, dtype=float).tolist(),
            "solver_success": bool(solve.get("solver_success")),
        }
        self.previous = desired
        return action, trace

    def action(self, current_state: Mapping[str, Any]) -> tuple[np.ndarray, dict[str, Any]]:
        if int(current_state["step_index"]) != self.step:
            raise ValueError("controller/current plant state index mismatch")
        currents = np.asarray(current_state["currents_a_tsc"], dtype=float).reshape(N_COILS)
        if self.transition_step is not None and self.step >= self.transition_step:
            self.phase = "anticipatory_damping"
        elif self.step >= 35:
            self.phase = "terminal_feedback"
        if self.phase == "main_control":
            return self._main_action(currents)
        if self.phase == "anticipatory_damping":
            return self._damping_action(currents)
        if self.phase == "terminal_feedback":
            return self._terminal_action(currents)
        raise ValueError(f"unsupported persistent controller phase: {self.phase}")

    def advance(self, next_state: Mapping[str, Any]) -> None:
        self.step += 1
        if int(next_state["step_index"]) != self.step:
            raise ValueError("controller next-state index mismatch")
        self.append_state(next_state)


class LocalPersistentControllerReplayWorker:
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
        result = {
            "schema_version": 1,
            "stage": STAGE,
            "controller_revision": CONTROLLER_REVISION,
            "experiment_id": spec.get("experiment_id"),
            "spec": copy.deepcopy(spec),
            "success": False,
            "failure_reason": "",
            "restart_trajectory": [],
            "controller_trace": [],
        }
        try:
            checkpoint = _strict_checkpoint_payload(
                read_json(Path(spec["controller_checkpoint_path"]))
            )
            if checkpoint["digest"] != spec["controller_checkpoint_digest"]:
                raise ValueError("controller checkpoint/spec digest mismatch")
            horizon = int(spec["horizon_steps"])
            self.base.env.reset()
            initial = r1._state_record_full(
                self.base.env,
                CHECKPOINT_STEP,
                np.asarray(checkpoint["checkpoint_action_norm_tsc"], dtype=float),
            )
            initial_visible = r1._visible_array({"trajectory": [initial]})[0]
            if not np.array_equal(
                initial_visible, np.asarray(checkpoint["checkpoint_visible"], dtype=float)
            ):
                raise ValueError("fresh plant initial visible state differs from checkpoint")
            if not np.array_equal(
                np.asarray(initial["wire_currents_a"], dtype=float),
                np.asarray(checkpoint["checkpoint_wire_currents_a"], dtype=float),
            ):
                raise ValueError("fresh plant initial wire state differs from checkpoint")
            controller = PersistentController(self.base, self.bundle, checkpoint)
            controller.replace_checkpoint_state(initial)
            trajectory = [initial]
            trace = []
            for step in range(CHECKPOINT_STEP, horizon):
                action, controller_row = controller.action(trajectory[-1])
                _, _, terminated, truncated, info = self.base.env.step(action)
                next_state = r1._state_record_full(self.base.env, step + 1, action)
                trajectory.append(next_state)
                trace.append(controller_row)
                controller.advance(next_state)
                if terminated:
                    raise RuntimeError(str(info.get("failure_reason", "terminated")))
                if truncated and step + 1 < horizon:
                    raise RuntimeError("environment truncated before R2 formal horizon")
            success = bool(
                len(trajectory) == horizon - CHECKPOINT_STEP + 1
                and len(trace) == horizon - CHECKPOINT_STEP
                and not any(bool(row.get("abnormal")) for row in trajectory)
                and all(bool(row.get("computed_online")) for row in trace)
                and not any(bool(row.get("future_measurement_used")) for row in trace)
            )
            result.update(
                {
                    "success": success,
                    "failure_reason": "" if success else "incomplete controller restart replay",
                    "restart_trajectory": trajectory,
                    "controller_trace": trace,
                    "controller_restart_summary": {
                        "fresh_controller_actor": True,
                        "fresh_tsc_plant_restart": True,
                        "controller_checkpoint_loaded": True,
                        "controller_checkpoint_digest": checkpoint["digest"],
                        "measurement_history_restored": True,
                        "integrator_restored": True,
                        "previous_correction_restored": True,
                        "pending_delay_queue_restored": True,
                        "trusted_calibration_token_restored": True,
                        "online_action_recomputation": True,
                        "future_action_replay_used": False,
                        "future_measurement_used": False,
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
                    failed=failed, reason="stage4_2r2_controller_restart"
                )


_RAY_ACTOR = None


def _ray_actor_class():
    global _RAY_ACTOR
    if _RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class Stage42R2Actor:
            def __init__(self, payload, library, bundle, worker_id, selector_cfg):
                self.worker = LocalPersistentControllerReplayWorker(
                    payload, library, bundle, worker_id, selector_cfg
                )

            def evaluate(self, spec):
                return self.worker.evaluate(spec)

            def close(self):
                self.worker.close()
                return True

        _RAY_ACTOR = Stage42R2Actor
    return _RAY_ACTOR


def _checkpoint_rows(ctx: Stage42R2Context) -> list[dict[str, Any]]:
    path = ctx.paths.checkpoint_bank / "results.json"
    return read_json(path) if path.is_file() else build_controller_checkpoints(ctx)


def build_replay_specs(ctx: Stage42R2Context) -> list[dict[str, Any]]:
    checkpoints = {
        (
            str(row["target_id"]),
            int(row["actual_delay_steps"]),
            float(row["actual_slew_scale"]),
        ): row
        for row in _checkpoint_rows(ctx)
    }
    sources = _selected_sources(ctx)
    captures = _captures(ctx)
    specs = []
    for key in sorted(sources, key=lambda item: (item[2], item[1], item[0])):
        checkpoint = checkpoints[key]
        source = sources[key]
        capture = captures[key]
        identity = {
            "controller_revision": CONTROLLER_REVISION,
            "target_id": key[0],
            "delay": key[1],
            "slew": key[2],
            "checkpoint_digest": checkpoint["controller_checkpoint_digest"],
            "snapshot_digest": capture["restart_snapshot"]["snapshot_manifest_digest"],
            "source_experiment_id": source["experiment_id"],
        }
        specs.append(
            {
                "kind": "stage4_2r2_persistent_controller_checkpoint_replay",
                "controller_revision": CONTROLLER_REVISION,
                "experiment_id": _scenario_digest(identity),
                "target_id": key[0],
                "action_delay_steps": key[1],
                "slew_scale": key[2],
                "horizon_steps": _formal_horizon(key[2]),
                "checkpoint_step": CHECKPOINT_STEP,
                "source_experiment_id": source["experiment_id"],
                "capture_experiment_id": capture["experiment_id"],
                "controller_checkpoint_path": checkpoint["controller_checkpoint_path"],
                "controller_checkpoint_digest": checkpoint[
                    "controller_checkpoint_digest"
                ],
                "plant_snapshot_dir": capture["restart_snapshot"]["snapshot_dir"],
                "plant_snapshot_manifest_digest": capture["restart_snapshot"][
                    "snapshot_manifest_digest"
                ],
                "online_action_recomputation": True,
                "future_action_replay_used": False,
            }
        )
    if len(specs) != 18:
        raise ValueError("Stage4.2R2 replay spec count mismatch")
    return specs


def run_offline_controller_recomputation_audit(
    ctx: Stage42R2Context,
) -> dict[str, Any]:
    """Recompute every suffix action without resetting or stepping TSC.

    Source suffix states are supplied one state at a time only to this audit
    harness.  They are never written to a controller checkpoint.  At each
    step, the persistent controller may inspect only its accumulated history
    through that state index.  Exact agreement with the authenticated expert
    action is a mandatory no-gotsc gate before any fresh restart rollout.
    """

    ctx.paths.offline_audit.mkdir(parents=True, exist_ok=True)
    sources = _selected_sources(ctx)
    r1_restarts = _r1_restarts(ctx)
    checkpoints = {
        (
            str(row["target_id"]),
            int(row["actual_delay_steps"]),
            float(row["actual_slew_scale"]),
        ): row
        for row in _checkpoint_rows(ctx)
    }
    library, bundle, selector = r1._library_bundle_selector(ctx.r1_ctx)
    rows: list[dict[str, Any]] = []
    for index, key in enumerate(
        sorted(sources, key=lambda item: (item[2], item[1], item[0]))
    ):
        source = sources[key]
        checkpoint_row = checkpoints[key]
        checkpoint = _strict_checkpoint_payload(
            read_json(Path(checkpoint_row["controller_checkpoint_path"]))
        )
        worker = LocalPersistentControllerReplayWorker(
            _restart_payload(ctx, key, r1_restarts[key]),
            library,
            bundle,
            f"stage42r2_offline_{index:03d}",
            selector,
        )
        exact = True
        max_abs_difference = 0.0
        first_mismatch_step: int | None = None
        phase_counts: dict[str, int] = {}
        try:
            controller = PersistentController(worker.base, bundle, checkpoint)
            horizon = _formal_horizon(key[2])
            checkpoint_state = copy.deepcopy(source["trajectory"][CHECKPOINT_STEP])
            checkpoint_state["step_index"] = CHECKPOINT_STEP
            controller.replace_checkpoint_state(checkpoint_state)
            for step in range(CHECKPOINT_STEP, horizon):
                current_state = copy.deepcopy(source["trajectory"][step])
                current_state["step_index"] = step
                action, trace = controller.action(current_state)
                expected = np.asarray(
                    source["trajectory"][step + 1]["action_norm_tsc"], dtype=float
                ).reshape(N_COILS)
                difference = float(
                    np.max(np.abs(np.asarray(action, dtype=float) - expected))
                )
                max_abs_difference = max(max_abs_difference, difference)
                step_exact = bool(np.array_equal(np.asarray(action, dtype=float), expected))
                if not step_exact:
                    exact = False
                    if first_mismatch_step is None:
                        first_mismatch_step = step
                if int(trace["measurement_max_state_index_used"]) > step:
                    raise ValueError("offline controller used a future measurement")
                phase = str(trace["controller_phase"])
                phase_counts[phase] = phase_counts.get(phase, 0) + 1
                next_state = copy.deepcopy(source["trajectory"][step + 1])
                next_state["step_index"] = step + 1
                controller.advance(next_state)
        finally:
            worker.close()
        rows.append(
            {
                "target_id": key[0],
                "actual_delay_steps": key[1],
                "actual_slew_scale": key[2],
                "source_experiment_id": source["experiment_id"],
                "controller_checkpoint_digest": checkpoint["digest"],
                "suffix_action_steps": _formal_horizon(key[2]) - CHECKPOINT_STEP,
                "phase_counts": phase_counts,
                "source_suffix_state_streamed_only_to_audit_harness": True,
                "source_suffix_persisted_in_checkpoint": False,
                "source_future_action_read_by_controller": False,
                "online_action_exact": exact,
                "maximum_online_action_abs_difference": max_abs_difference,
                "first_mismatch_step": first_mismatch_step,
                "passed": exact and first_mismatch_step is None,
            }
        )
    maximum = max(
        (float(row["maximum_online_action_abs_difference"]) for row in rows),
        default=math.inf,
    )
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "offline_controller_recomputation_audit",
        "new_tsc_processes_started": 0,
        "n_cases": len(rows),
        "expected_cases": 18,
        "n_suffix_action_steps": sum(int(row["suffix_action_steps"]) for row in rows),
        "exact_action_case_count": sum(bool(row["online_action_exact"]) for row in rows),
        "maximum_online_action_abs_difference": maximum,
        "future_measurement_use_count": 0,
        "future_action_replay_count": 0,
        "passed": bool(
            len(rows) == 18
            and all(bool(row["passed"]) for row in rows)
            and maximum == 0.0
        ),
    }
    write_csv(ctx.paths.offline_audit / "results.csv", rows)
    atomic_write_json(ctx.paths.offline_audit / "results.json", rows)
    atomic_write_json(ctx.paths.offline_audit / "summary.json", summary)
    return summary


def _result_complete(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        result = read_json_gz(path)
        return bool(
            result.get("success")
            and result.get("controller_restart_summary", {}).get(
                "online_action_recomputation"
            )
            and not result.get("controller_restart_summary", {}).get(
                "future_action_replay_used", True
            )
        )
    except Exception:
        return False


def evaluate_replay(
    ctx: Stage42R2Context,
    specs: Sequence[dict[str, Any]],
    *,
    backend: str,
    resume: bool,
) -> list[dict[str, Any]]:
    raw_dir = ctx.paths.replay / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    r1_restarts = _r1_restarts(ctx)
    library, bundle, selector = r1._library_bundle_selector(ctx.r1_ctx)
    payloads = {
        key: _restart_payload(ctx, key, r1_restarts[key])
        for key in r1_restarts
    }
    pending = [
        spec
        for spec in specs
        if not (resume and _result_complete(raw_dir / f"{spec['experiment_id']}.json.gz"))
    ]
    if backend == "serial":
        for index, spec in enumerate(pending):
            key = _case_key(spec)
            worker = LocalPersistentControllerReplayWorker(
                payloads[key], library, bundle, f"stage42r2_serial_{index:03d}", selector
            )
            try:
                result = worker.evaluate(spec)
            finally:
                worker.close()
            atomic_write_json_gz(raw_dir / f"{spec['experiment_id']}.json.gz", result)
            print(f"[Stage4.2R2 controller-restart] {index + 1}/{len(pending)}", flush=True)
    elif backend == "ray" and pending:
        import ray

        requested = int(os.environ.get("STAGE4_2R2_WORKERS", ctx.cfg["parallel"]["n_workers"]))
        plan = ensure_ray_worker_plan(
            ray,
            requested_workers=requested,
            pending_tasks=len(pending),
            ray_tmpdir=os.environ.get("RAY_TMPDIR") or ctx.cfg["parallel"].get("ray_tmpdir"),
            log_prefix="[Stage4.2R2 controller-restart]",
        )
        Actor = _ray_actor_class()
        actors = []
        refs = {}
        for index, spec in enumerate(pending):
            key = _case_key(spec)
            actor = Actor.remote(
                payloads[key],
                library,
                bundle,
                f"stage42r2_{index:03d}",
                selector,
            )
            actors.append(actor)
            refs[actor.evaluate.remote(spec)] = spec
        print(
            "[Stage4.2R2 controller-restart] actor_count="
            f"{plan.actor_count} pending={len(pending)}",
            flush=True,
        )
        done = 0
        try:
            while refs:
                ready, _ = ray.wait(list(refs), num_returns=1, timeout=30.0)
                if not ready:
                    print(
                        f"[Stage4.2R2 controller-restart] waiting {done}/{len(pending)}",
                        flush=True,
                    )
                    continue
                for ref in ready:
                    spec = refs.pop(ref)
                    try:
                        result = ray.get(ref)
                    except Exception as exc:
                        result = {
                            "schema_version": 1,
                            "stage": STAGE,
                            "controller_revision": CONTROLLER_REVISION,
                            "experiment_id": spec["experiment_id"],
                            "spec": spec,
                            "success": False,
                            "failure_reason": repr(exc),
                            "traceback": traceback.format_exc(),
                            "restart_trajectory": [],
                            "controller_trace": [],
                        }
                    atomic_write_json_gz(
                        raw_dir / f"{spec['experiment_id']}.json.gz", result
                    )
                    done += 1
                    if done % 10 == 0 or not refs:
                        print(
                            f"[Stage4.2R2 controller-restart] {done}/{len(pending)}",
                            flush=True,
                        )
        finally:
            s2._close_ray_actors(
                actors,
                timeout_s=float(ctx.cfg["storage"].get("actor_close_timeout_s", 1800.0)),
            )
    elif backend not in {"serial", "ray"}:
        raise ValueError("backend must be serial or ray")
    return [
        read_json_gz(raw_dir / f"{spec['experiment_id']}.json.gz") for spec in specs
    ]


def _recombined(
    capture: Mapping[str, Any], replay: Mapping[str, Any], horizon: int
) -> dict[str, Any]:
    trajectory = (
        copy.deepcopy(list(capture["trajectory"])[:CHECKPOINT_STEP])
        + copy.deepcopy(list(replay["restart_trajectory"]))
    )
    if len(trajectory) != horizon + 1:
        raise ValueError("Stage4.2R2 recombined trajectory length mismatch")
    return {"trajectory": trajectory}


def _result_row(
    ctx: Stage42R2Context,
    result: Mapping[str, Any],
) -> dict[str, Any]:
    key = _case_key(result)
    controller_summary = result.get("controller_restart_summary") or {}
    trace = list(result.get("controller_trace") or [])
    if not bool(result.get("success")):
        return {
            "experiment_id": result.get("experiment_id"),
            "target_id": key[0],
            "actual_delay_steps": key[1],
            "actual_slew_scale": key[2],
            "environment_success": False,
            "failure_reason": str(result.get("failure_reason", "")),
            "runtime_traceback_present": bool(result.get("traceback")),
            "controller_checkpoint_loaded": bool(
                controller_summary.get("controller_checkpoint_loaded")
            ),
            "online_action_recomputation": bool(
                controller_summary.get("online_action_recomputation")
            ),
            "future_action_replay_used": bool(
                controller_summary.get("future_action_replay_used", False)
            ),
            "future_measurement_used": any(
                bool(row.get("future_measurement_used")) for row in trace
            ),
            "controller_trace_steps": len(trace),
            "failure_class": "runtime_or_environment_error",
            "passed": False,
        }
    source = _selected_sources(ctx)[key]
    capture = _captures(ctx)[key]
    horizon = _formal_horizon(key[2])
    restart_trajectory = list(result.get("restart_trajectory") or [])
    source_suffix = list(source["trajectory"])[CHECKPOINT_STEP : horizon + 1]
    visible = r1._compare_arrays(
        r1._visible_array(result, trajectory_key="restart_trajectory"),
        r1._visible_array({"trajectory": source_suffix}),
        atol=0.0,
    )
    wire = r1._compare_arrays(
        r1._wire_array(result, trajectory_key="restart_trajectory"),
        r1._wire_array({"trajectory": list(capture["trajectory"])[CHECKPOINT_STEP : horizon + 1]}),
        atol=0.0,
    )
    actual_actions = np.asarray(
        [row["action_norm_tsc"] for row in restart_trajectory[1:]], dtype=float
    )
    source_actions = np.asarray(
        [row["action_norm_tsc"] for row in source_suffix[1:]], dtype=float
    )
    action = r1._compare_arrays(actual_actions, source_actions, atol=0.0)
    recombined = _recombined(capture, result, horizon)
    recombined_visible = r1._compare_arrays(
        r1._visible_array(recombined),
        r1._visible_array({"trajectory": list(source["trajectory"])[: horizon + 1]}),
        atol=0.0,
    )
    r13_ctx = r1._r13_ctx(ctx.r1_ctx)
    policy = r1.r13._timing_policy(
        r13_ctx, key[2], policy_id=f"r42r2_{key[0]}_{key[1]}_{key[2]:.1f}"
    )
    formal = r1.r8.tracking_metrics(
        r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx,
        {**copy.deepcopy(source), "trajectory": recombined["trajectory"]},
        policy,
    )
    passed = bool(
        result.get("success")
        and visible["exact"]
        and wire["exact"]
        and action["exact"]
        and recombined_visible["exact"]
        and len(trace) == horizon - CHECKPOINT_STEP
        and all(bool(row.get("computed_online")) for row in trace)
        and not any(bool(row.get("future_measurement_used")) for row in trace)
        and bool(controller_summary.get("controller_checkpoint_loaded"))
        and bool(controller_summary.get("online_action_recomputation"))
        and not bool(controller_summary.get("future_action_replay_used", True))
        and bool(formal["stage3_4_target_tracking_pass"])
    )
    if passed:
        failure_class = ""
    elif not bool(controller_summary.get("controller_checkpoint_loaded")):
        failure_class = "controller_checkpoint_error"
    elif (
        not bool(controller_summary.get("online_action_recomputation"))
        or bool(controller_summary.get("future_action_replay_used", True))
        or any(bool(row.get("future_measurement_used")) for row in trace)
        or not action["exact"]
    ):
        failure_class = "controller_reconstruction_or_design_failure"
    elif not visible["exact"] or not wire["exact"] or not recombined_visible["exact"]:
        failure_class = "plant_restart_fidelity_failure"
    elif not bool(formal["stage3_4_target_tracking_pass"]):
        failure_class = "real_closed_loop_formal_control_failure"
    else:
        failure_class = "unclassified_scientific_failure"
    return {
        "experiment_id": result.get("experiment_id"),
        "target_id": key[0],
        "actual_delay_steps": key[1],
        "actual_slew_scale": key[2],
        "environment_success": bool(result.get("success")),
        "failure_reason": str(result.get("failure_reason", "")),
        "controller_checkpoint_loaded": bool(
            controller_summary.get("controller_checkpoint_loaded")
        ),
        "online_action_recomputation": bool(
            controller_summary.get("online_action_recomputation")
        ),
        "future_action_replay_used": bool(
            controller_summary.get("future_action_replay_used", True)
        ),
        "future_measurement_used": any(
            bool(row.get("future_measurement_used")) for row in trace
        ),
        "controller_trace_steps": len(trace),
        "restart_visible_exact": visible["exact"],
        "restart_visible_maximum_abs_difference": visible["maximum_abs_difference"],
        "restart_wire_exact": wire["exact"],
        "restart_wire_maximum_abs_difference": wire["maximum_abs_difference"],
        "online_action_exact": action["exact"],
        "online_action_maximum_abs_difference": action["maximum_abs_difference"],
        "recombined_visible_exact": recombined_visible["exact"],
        "formal_contract_pass": bool(formal["stage3_4_target_tracking_pass"]),
        "formal_best_arrival_ms": int(formal["stage3_4_best_endpoint_ms"]),
        "formal_minimum_signed_margin": float(
            formal["stage3_4_tracking_minimum_signed_margin"]
        ),
        "failure_class": failure_class,
        "passed": passed,
    }


def summarize_replay(
    ctx: Stage42R2Context,
    results: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    rows = []
    for result in results:
        try:
            rows.append(_result_row(ctx, result))
        except Exception as exc:
            key = _case_key(result)
            rows.append(
                {
                    "experiment_id": result.get("experiment_id"),
                    "target_id": key[0],
                    "actual_delay_steps": key[1],
                    "actual_slew_scale": key[2],
                    "environment_success": bool(result.get("success")),
                    "failure_reason": str(result.get("failure_reason", "")),
                    "summary_exception": repr(exc),
                    "failure_class": "statistics_or_reporting_error",
                    "passed": False,
                }
            )
    minimum = min(
        (
            row
            for row in rows
            if row.get("formal_minimum_signed_margin") is not None
        ),
        key=lambda row: float(row["formal_minimum_signed_margin"]),
        default={},
    )
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "persistent_controller_checkpoint_replay",
        "n_rollouts": len(rows),
        "expected_rollouts": 18,
        "coverage_complete": len(rows) == 18,
        "environment_success_count": sum(
            bool(row.get("environment_success")) for row in rows
        ),
        "runtime_or_environment_error_count": sum(
            row.get("failure_class") == "runtime_or_environment_error"
            for row in rows
        ),
        "statistics_or_reporting_error_count": sum(
            row.get("failure_class") == "statistics_or_reporting_error"
            for row in rows
        ),
        "controller_checkpoint_error_count": sum(
            row.get("failure_class") == "controller_checkpoint_error"
            for row in rows
        ),
        "controller_reconstruction_or_design_failure_count": sum(
            row.get("failure_class")
            == "controller_reconstruction_or_design_failure"
            for row in rows
        ),
        "plant_restart_fidelity_failure_count": sum(
            row.get("failure_class") == "plant_restart_fidelity_failure"
            for row in rows
        ),
        "real_closed_loop_formal_control_failure_count": sum(
            row.get("failure_class") == "real_closed_loop_formal_control_failure"
            for row in rows
        ),
        "controller_checkpoint_loaded_fraction": sum(
            bool(row.get("controller_checkpoint_loaded")) for row in rows
        )
        / len(rows)
        if rows
        else 0.0,
        "online_action_recomputation_fraction": sum(
            bool(row.get("online_action_recomputation")) for row in rows
        )
        / len(rows)
        if rows
        else 0.0,
        "future_action_replay_count": sum(
            bool(row.get("future_action_replay_used", True)) for row in rows
        ),
        "future_measurement_use_count": sum(
            bool(row.get("future_measurement_used", True)) for row in rows
        ),
        "online_action_exact_fraction": sum(
            bool(row.get("online_action_exact")) for row in rows
        )
        / len(rows)
        if rows
        else 0.0,
        "restart_visible_exact_fraction": sum(
            bool(row.get("restart_visible_exact")) for row in rows
        )
        / len(rows)
        if rows
        else 0.0,
        "restart_wire_exact_fraction": sum(
            bool(row.get("restart_wire_exact")) for row in rows
        )
        / len(rows)
        if rows
        else 0.0,
        "formal_contract_pass_fraction": sum(
            bool(row.get("formal_contract_pass")) for row in rows
        )
        / len(rows)
        if rows
        else 0.0,
        "maximum_online_action_abs_difference": r1._finite_metric_max(
            rows, "online_action_maximum_abs_difference"
        ),
        "maximum_restart_visible_abs_difference": r1._finite_metric_max(
            rows, "restart_visible_maximum_abs_difference"
        ),
        "maximum_restart_wire_abs_difference": r1._finite_metric_max(
            rows, "restart_wire_maximum_abs_difference"
        ),
        "minimum_formal_signed_margin": minimum.get(
            "formal_minimum_signed_margin"
        ),
        "minimum_margin_case": (
            {
                "target_id": minimum["target_id"],
                "actual_delay_steps": minimum["actual_delay_steps"],
                "actual_slew_scale": minimum["actual_slew_scale"],
            }
            if minimum
            else {}
        ),
        "passed": False,
    }
    summary["passed"] = bool(
        summary["coverage_complete"]
        and summary["environment_success_count"] == 18
        and summary["controller_checkpoint_loaded_fraction"] == 1.0
        and summary["online_action_recomputation_fraction"] == 1.0
        and summary["future_action_replay_count"] == 0
        and summary["future_measurement_use_count"] == 0
        and summary["online_action_exact_fraction"] == 1.0
        and summary["restart_visible_exact_fraction"] == 1.0
        and summary["restart_wire_exact_fraction"] == 1.0
        and summary["formal_contract_pass_fraction"] == 1.0
        and summary["maximum_online_action_abs_difference"] == 0.0
        and summary["maximum_restart_visible_abs_difference"] == 0.0
        and summary["maximum_restart_wire_abs_difference"] == 0.0
        and all(bool(row.get("passed")) for row in rows)
    )
    write_csv(ctx.paths.replay / "results.csv", rows)
    atomic_write_json(ctx.paths.replay / "results.json", rows)
    atomic_write_json(ctx.paths.replay / "summary.json", summary)
    return summary


def prepare(ctx: Stage42R2Context, *, resume: bool) -> None:
    for path in (
        ctx.paths.run_dir,
        ctx.paths.source_reference,
        ctx.paths.checkpoint_bank,
        ctx.paths.offline_audit,
        ctx.paths.variants,
        ctx.paths.replay,
        ctx.paths.analysis,
    ):
        path.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "created_utc": utc_timestamp(),
        "source_stage4_2r1_run": str(ctx.source_r1_run),
        "source_stage4_1r17_run": str(ctx.source_r17_run),
        "source_fingerprint": ctx.source_fingerprint,
        "checkpoint_step": CHECKPOINT_STEP,
        "checkpoint_elapsed_ms": CHECKPOINT_STEP * DT_MS,
        "future_action_replay_forbidden": True,
        "online_action_recomputation_required": True,
        "formal_timing_contract": ctx.cfg["formal_timing_contract"],
        "finite_test_envelope_only": True,
    }
    if ctx.paths.manifest.is_file():
        old = read_json(ctx.paths.manifest)
        for name in (
            "stage",
            "controller_revision",
            "package_revision",
            "source_fingerprint",
            "checkpoint_step",
        ):
            if old.get(name) != manifest.get(name):
                raise ValueError(f"Stage4.2R2 resume manifest mismatch: {name}")
    elif resume:
        raise FileNotFoundError("Stage4.2R2 resume manifest missing")
    else:
        atomic_write_json(ctx.paths.manifest, manifest)
        atomic_write_json(
            ctx.paths.state,
            {
                "schema_version": 1,
                "stage": STAGE,
                "controller_revision": CONTROLLER_REVISION,
                "package_revision": PACKAGE_REVISION,
                "prepared": True,
                "finished": False,
                "primary_pass": False,
                "stop_reason": "",
                "updated_utc": utc_timestamp(),
            },
        )
    atomic_write_json(ctx.paths.run_dir / "stage4_2r2_config.resolved.json", ctx.cfg)
    atomic_write_json(
        ctx.paths.source_reference / "stage4_2r1_fingerprint.json",
        ctx.source_fingerprint,
    )


def analyze(
    ctx: Stage42R2Context,
    checkpoint_summary: Mapping[str, Any],
    offline_summary: Mapping[str, Any] | None = None,
    replay_summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    checkpoint_pass = bool(checkpoint_summary.get("passed"))
    offline_pass = bool(offline_summary and offline_summary.get("passed"))
    replay_pass = bool(replay_summary and replay_summary.get("passed"))
    primary_pass = bool(checkpoint_pass and offline_pass and replay_pass)
    verdict = {
        "schema_version": 1,
        "stage": STAGE,
        "verdict": (
            "STAGE4_2R2_PERSISTENT_CONTROLLER_CHECKPOINT_REPLAY_CERTIFIED"
            if primary_pass
            else "STAGE4_2R2_PERSISTENT_CONTROLLER_CHECKPOINT_REPLAY_INCOMPLETE"
        ),
        "source_stage4_2r1_run": str(ctx.source_r1_run),
        "controller_checkpoint_status": "passed" if checkpoint_pass else "failed",
        "offline_controller_recomputation_status": (
            "passed" if offline_pass else "failed" if offline_summary else "not_run"
        ),
        "controller_restart_replay_status": (
            "passed" if replay_pass else "failed" if replay_summary else "not_run"
        ),
        "online_action_recomputation_validated": replay_pass,
        "future_action_replay_used": False if replay_summary else None,
        "same_source_exact_controller_restart_validated": replay_pass,
        "matched_visible_different_hidden_history_validated": False,
        "different_initial_state_validated": False,
        "unseen_target_validated": False,
        "continuous_parameter_change_validated": False,
        "measurement_noise_robustness_validated": False,
        "disturbance_recovery_validated": False,
        "finite_test_envelope_only": True,
        "formal_contract_preserved": (
            bool(replay_summary.get("formal_contract_pass_fraction") == 1.0)
            if replay_summary
            else None
        ),
        "primary_pass": primary_pass,
        "next_if_pass": (
            "Proceed to matched-visible/different-hidden-history and different-initial-state "
            "controller tests. Do not start BC, DAgger, or RL."
        ),
        "next_if_fail": (
            "Separate checkpoint schema, controller phase, queue, observer/integrator, "
            "online action, plant suffix, and formal failures without replaying future actions."
        ),
    }
    summary = {
        **verdict,
        "created_utc": utc_timestamp(),
        "phases": {
            "controller_checkpoint_materialization": dict(checkpoint_summary),
            "offline_controller_recomputation_audit": (
                None if offline_summary is None else dict(offline_summary)
            ),
            "persistent_controller_checkpoint_replay": (
                None if replay_summary is None else dict(replay_summary)
            ),
        },
    }
    atomic_write_json(ctx.paths.analysis / "stage4_2r2_verdict.json", verdict)
    atomic_write_json(ctx.paths.analysis / "stage4_2r2_summary.json", summary)
    state = read_json(ctx.paths.state)
    state.update(
        {
            "finished": True,
            "primary_pass": primary_pass,
            "stop_reason": (
                ""
                if primary_pass
                else "controller_checkpoint_failed"
                if not checkpoint_pass
                else "offline_controller_recomputation_failed"
                if not offline_pass
                else "controller_restart_replay_failed"
            ),
            "updated_utc": utc_timestamp(),
            "verdict": verdict,
        }
    )
    atomic_write_json(ctx.paths.state, state)
    return summary


def execute(
    ctx: Stage42R2Context,
    *,
    command: str,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    prepare(ctx, resume=resume)
    checkpoint_rows = build_controller_checkpoints(ctx)
    checkpoint_summary = read_json(ctx.paths.checkpoint_bank / "summary.json")
    if command == "checkpoint" or not checkpoint_summary.get("passed"):
        return analyze(ctx, checkpoint_summary)
    offline_summary = run_offline_controller_recomputation_audit(ctx)
    if command == "offline" or not offline_summary.get("passed"):
        return analyze(ctx, checkpoint_summary, offline_summary)
    specs = build_replay_specs(ctx)
    results = evaluate_replay(ctx, specs, backend=backend, resume=resume)
    replay_summary = summarize_replay(ctx, results)
    return analyze(ctx, checkpoint_summary, offline_summary, replay_summary)


def self_test() -> dict[str, Any]:
    checkpoint = {
        "schema_version": 1,
        "checkpoint_step": CHECKPOINT_STEP,
        "measurement_history": [
            {"state_index": step, "R": 0.7, "Z": 0.0, "Ip": 30000.0}
            for step in range(CHECKPOINT_STEP + 1)
        ],
        "modeled_delay_steps": 2,
        "actual_delay_steps": 2,
        "modeled_slew_scale": 0.9,
        "trusted_calibration_model": True,
        "calibration_token": "trusted",
        "integral_normalized": [0.0] * 5,
        "previous_correction_physical": [0.0] * 3,
        "checkpoint_action_norm_tsc": [0.0] * N_COILS,
        "pending_delay_queue": [
            {
                "origin": "main_control",
                "origin_index": 18 + index,
                "command": [0.0] * 3,
                "desired_physical": [0.0] * 3,
            }
            for index in range(2)
        ],
        "future_measurement_count": 0,
        "future_action_count": 0,
        "online_action_recomputation_required": True,
    }
    checkpoint["digest"] = _canonical_digest(checkpoint)
    valid = _strict_checkpoint_payload(checkpoint)
    future_rejected = False
    bad = copy.deepcopy(checkpoint)
    bad.pop("digest")
    bad["future_actions"] = [[0.0] * N_COILS]
    bad["digest"] = _canonical_digest(bad)
    try:
        _strict_checkpoint_payload(bad)
    except ValueError:
        future_rejected = True
    return {
        "schema_version": 1,
        "stage": STAGE,
        "package_revision": PACKAGE_REVISION,
        "checkpoint_digest_valid": valid["digest"] == checkpoint["digest"],
        "future_action_checkpoint_rejected": future_rejected,
        "formal_timing_unchanged": True,
        "passed": bool(future_rejected),
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
        description="Stage4.2R2 persistent controller checkpoint replay"
    )
    parser.add_argument("--config", type=Path)
    parser.add_argument("--source-stage4-2r1-run", type=Path)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument(
        "--command",
        choices=("all", "checkpoint", "offline", "replay"),
        default="all",
    )
    parser.add_argument("--backend", choices=("serial", "ray"), default="ray")
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
            ("--source-stage4-2r1-run", args.source_stage4_2r1_run),
            ("--run-dir", args.run_dir),
        )
        if value is None
    ]
    if missing:
        parser.error("missing required arguments: " + ", ".join(missing))
    ctx = load_stage42r2_config(
        args.config,
        source_stage42r1_run=args.source_stage4_2r1_run,
        run_dir_override=args.run_dir,
    )
    payload = execute(
        ctx,
        command=args.command,
        backend=args.backend,
        resume=args.resume,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
