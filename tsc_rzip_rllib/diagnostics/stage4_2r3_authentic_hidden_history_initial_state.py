"""Stage4.2R3 authentic hidden-history and different-initial-state validation.

R3 first generates real TSC restart states with reversed, zero-net,
full-coil nullspace pulse histories.  Pair validity is decided only from the
preregistered checkpoint gates.  Every selected member is then restarted in
a fresh TSC process and controlled online by the frozen R17 expert.

Full wire current is audit telemetry only.  It is recorded after each action
is chosen and never enters the controller.
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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

try:
    import resource
except ImportError:  # pragma: no cover - Windows validation host
    resource = None

from . import stage2_trajectory_optimization as s2
from . import stage4_2r1_true_tsc_plant_restart_action_replay as r1
from . import stage4_2r2_persistent_controller_checkpoint_replay as r2
from tsc_rzip_rllib.utils.ray_runtime import ensure_ray_worker_plan


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3"
CONTROLLER_REVISION = "authentic_hidden_history_initial_state_mpc_v42r3"
PACKAGE_REVISION = "r42r3_authentic_hidden_history_initial_state_v1"
EXPECTED_R2_CONTROLLER = r2.CONTROLLER_REVISION
EXPECTED_R2_PACKAGE = r2.PACKAGE_REVISION
N_COILS = 14
N_MODES = 3
N_WIRES = 48
DT_MS = 10
NORMAL_HORIZON = 35
WEAK_HORIZON = 37

read_json = r2.read_json
read_json_gz = r2.read_json_gz
atomic_write_json = r2.atomic_write_json
atomic_write_json_gz = r2.atomic_write_json_gz
write_csv = r2.write_csv
utc_timestamp = r2.utc_timestamp


def _json_safe(value: Any) -> Any:
    return r2._json_safe(value)


def _sha256_file(path: Path) -> str:
    return r2._sha256_file(path)


def _canonical_digest(payload: Any) -> str:
    canonical = json.dumps(
        _json_safe(payload), sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _scenario_digest(payload: Mapping[str, Any]) -> str:
    return "s42r3_" + _canonical_digest(dict(payload))[:20]


def _rms(value: np.ndarray) -> float:
    array = np.asarray(value, dtype=float)
    return float(np.sqrt(np.mean(array**2)))


def _formal_horizon(slew: float) -> int:
    return WEAK_HORIZON if math.isclose(float(slew), 0.9, abs_tol=1e-12) else NORMAL_HORIZON


def _requested_workers(cfg: Mapping[str, Any]) -> int:
    fixed = int(cfg["parallel"]["n_workers"])
    requested = int(os.environ.get("STAGE4_2R3_WORKERS", fixed))
    if requested != fixed:
        raise ValueError(
            f"Stage4.2R3 Ray capacity is frozen at {fixed}, got {requested}"
        )
    return requested


def _forbidden_future_paths(value: Any, prefix: str = "") -> list[str]:
    forbidden = {
        "source_actions",
        "source_suffix_actions",
        "future_actions",
        "future_measurements",
        "source_future_trajectory",
    }
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            name = str(key)
            path = f"{prefix}.{name}" if prefix else name
            if name in forbidden:
                found.append(path)
            found.extend(_forbidden_future_paths(item, path))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            found.extend(_forbidden_future_paths(item, f"{prefix}[{index}]"))
    return found


def validate_config(cfg: Mapping[str, Any]) -> None:
    if str(cfg.get("stage")) != STAGE:
        raise ValueError("Stage4.2R3 config stage mismatch")
    if str(cfg.get("controller_revision")) != CONTROLLER_REVISION:
        raise ValueError("Stage4.2R3 controller revision mismatch")
    if str(cfg.get("package_revision")) != PACKAGE_REVISION:
        raise ValueError("Stage4.2R3 package revision mismatch")
    if int(cfg["parallel"]["n_workers"]) != 128:
        raise ValueError("Stage4.2R3 is fixed to 128 Ray workers")
    generation = cfg["state_generation"]
    if list(map(int, generation["nullspace_direction_indices"])) != [0, 1, 2]:
        raise ValueError("Stage4.2R3 nullspace direction grid changed")
    if list(map(float, generation["amplitude_fractions"])) != [0.05, 0.1, 0.2]:
        raise ValueError("Stage4.2R3 amplitude grid changed")
    if list(map(int, generation["settle_steps"])) != [4, 8, 12]:
        raise ValueError("Stage4.2R3 settle grid changed")
    if list(map(str, generation["history_orders"])) != [
        "plus_first",
        "minus_first",
    ]:
        raise ValueError("Stage4.2R3 history order changed")
    if (
        int(generation["expected_pairs"]) != 27
        or int(generation["expected_rollouts"]) != 54
        or int(generation["pulse_steps"]) != 2
        or not math.isclose(
            float(generation["maximum_abs_action"]), 0.2, abs_tol=1e-15
        )
    ):
        raise ValueError("Stage4.2R3 state-generation contract changed")
    gate = cfg["pair_gate"]
    expected_gate = {
        "R_abs_difference_m_max": 0.0005,
        "Z_abs_difference_m_max": 0.0005,
        "Ip_abs_difference_A_max": 2000.0,
        "vR_abs_difference_m_per_s_max": 0.02,
        "vZ_abs_difference_m_per_s_max": 0.02,
        "coil_max_abs_difference_A_max": 2000.0,
        "coil_rms_difference_A_max": 500.0,
        "action_max_abs_difference_max": 1e-12,
        "wire_max_abs_difference_A_min": 1000.0,
        "wire_relative_rms_difference_min": 0.05,
    }
    for key, expected in expected_gate.items():
        if not math.isclose(float(gate[key]), expected, abs_tol=1e-15):
            raise ValueError(f"Stage4.2R3 pair gate changed: {key}")
    if (
        int(gate["wire_count"]) != N_WIRES
        or int(gate["minimum_selected_pairs"]) != 2
        or int(gate["maximum_selected_pairs"]) != 3
        or not bool(gate["forbid_control_outcome_selection"])
    ):
        raise ValueError("Stage4.2R3 pair coverage/selection gate changed")
    initial = cfg["different_initial_state_gate"]
    expected_initial = {
        "R_centroid_difference_m_min": 0.0005,
        "Z_centroid_difference_m_min": 0.0005,
        "Ip_centroid_difference_A_min": 2000.0,
        "coil_centroid_rms_difference_A_min": 500.0,
    }
    for key, expected in expected_initial.items():
        if not math.isclose(float(initial[key]), expected, abs_tol=1e-15):
            raise ValueError(f"Stage4.2R3 initial-state gate changed: {key}")
    if int(initial["minimum_selected_centroids"]) != 2:
        raise ValueError("Stage4.2R3 initial-state coverage gate changed")
    matrix = cfg["control_matrix"]
    if list(map(str, matrix["targets"])) != ["nominal", "RZ_p10_m10"]:
        raise ValueError("Stage4.2R3 target matrix changed")
    actuator = [
        (int(row["actual_delay_steps"]), float(row["actual_slew_scale"]))
        for row in matrix["future_actuator_cases"]
    ]
    if actuator != [(0, 1.0), (2, 0.9)]:
        raise ValueError("Stage4.2R3 future actuator matrix changed")
    if (
        int(matrix["expected_rollouts_per_selected_pair"]) != 8
        or int(matrix["minimum_expected_rollouts"]) != 16
        or int(matrix["maximum_expected_rollouts"]) != 24
    ):
        raise ValueError("Stage4.2R3 control rollout coverage changed")
    timing = cfg["formal_timing_contract"]
    if (
        int(timing["normal"]["arrival_deadline_step"]) != 25
        or int(timing["normal"]["hold_through_step"]) != 35
        or int(timing["weak"]["arrival_deadline_step"]) != 27
        or int(timing["weak"]["hold_through_step"]) != 37
        or bool(timing["arrival_deadline_expansion_allowed"])
    ):
        raise ValueError("Stage4.2R3 formal timing changed")
    if bool(cfg.get("bc_dagger_or_rl_allowed")):
        raise ValueError("Stage4.2R3 may not authorize BC, DAgger, or RL")


@dataclass(frozen=True)
class Stage42R3Paths:
    run_dir: Path
    source_reference: Path
    state_generation: Path
    pair_analysis: Path
    variants: Path
    control: Path
    analysis: Path
    state: Path
    manifest: Path

    @classmethod
    def from_run_dir(cls, run_dir: Path) -> "Stage42R3Paths":
        root = run_dir.expanduser().resolve()
        return cls(
            run_dir=root,
            source_reference=root / "stage4_2r3_source_reference",
            state_generation=root / "stage4_2r3_state_generation",
            pair_analysis=root / "stage4_2r3_pair_analysis",
            variants=root / "stage4_2r3_environment_variants",
            control=root / "stage4_2r3_hidden_history_control",
            analysis=root / "stage4_2r3_analysis",
            state=root / "stage4_2r3_state.json",
            manifest=root / "stage4_2r3_manifest.json",
        )


@dataclass
class Stage42R3Context:
    cfg: dict[str, Any]
    paths: Stage42R3Paths
    project_dir: Path
    source_r2_run: Path
    source_r1_run: Path
    source_r17_run: Path
    source_r2_manifest: dict[str, Any]
    source_r2_state: dict[str, Any]
    r1_ctx: r1.Stage42R1Context
    source_fingerprint: dict[str, Any]


def _source_fingerprint(
    source_r2: Path, source_r1: Path, source_r17: Path
) -> dict[str, Any]:
    required = [
        source_r2 / "stage4_2r2_manifest.json",
        source_r2 / "stage4_2r2_state.json",
        source_r2 / "stage4_2r2_config.resolved.json",
        source_r2 / "stage4_2r2_analysis" / "stage4_2r2_summary.json",
        source_r2 / "stage4_2r2_controller_checkpoint_bank" / "results.json",
        source_r1 / "stage4_2r1_manifest.json",
        source_r1 / "stage4_2r1_state.json",
        source_r1 / "stage4_2r1_source_reference" / "selected_expert_inventory.json",
        source_r1
        / "stage4_2r1_restart_variants"
        / "source_slew_1p000_h35.payload.json",
        source_r1
        / "stage4_2r1_restart_variants"
        / "source_slew_0p900_h37.payload.json",
        source_r17 / "stage4_1r17_manifest.json",
        source_r17 / "stage4_1r17_state.json",
    ]
    required.extend(
        sorted(
            (
                source_r2
                / "stage4_2r2_controller_restart_replay"
                / "raw"
            ).glob("*.json.gz")
        )
    )
    if len(required) != 30:
        raise ValueError(
            f"Stage4.2R3 source fingerprint expected 30 files, got {len(required)}"
        )
    missing = [path for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Stage4.2R3 source file missing: {missing[0]}")
    rows = []
    for path in required:
        if path.is_relative_to(source_r2):
            label = "stage4_2r2/" + path.relative_to(source_r2).as_posix()
        elif path.is_relative_to(source_r1):
            label = "stage4_2r1/" + path.relative_to(source_r1).as_posix()
        else:
            label = "stage4_1r17/" + path.relative_to(source_r17).as_posix()
        rows.append(
            {
                "path": label,
                "size_bytes": int(path.stat().st_size),
                "sha256": _sha256_file(path),
            }
        )
    return {
        "schema_version": 1,
        "contract": "r42r3_r2_r1_r17_direct_source_v1",
        "n_files": len(rows),
        "total_bytes": sum(int(row["size_bytes"]) for row in rows),
        "digest": _canonical_digest(rows),
        "files": rows,
    }


def load_stage42r3_config(
    config_path: Path,
    *,
    source_stage42r2_run: Path,
    run_dir_override: Path | None = None,
) -> Stage42R3Context:
    config_path = config_path.expanduser().resolve()
    cfg = read_json(config_path)
    validate_config(cfg)
    project_dir = config_path.parents[1]
    source_r2 = source_stage42r2_run.expanduser().resolve()
    manifest = read_json(source_r2 / "stage4_2r2_manifest.json")
    state = read_json(source_r2 / "stage4_2r2_state.json")
    if str(manifest.get("stage")) != "Stage4.2R2":
        raise ValueError("Stage4.2R3 source stage mismatch")
    if str(manifest.get("controller_revision")) != EXPECTED_R2_CONTROLLER:
        raise ValueError("Stage4.2R3 source R2 controller mismatch")
    if str(manifest.get("package_revision")) != EXPECTED_R2_PACKAGE:
        raise ValueError("Stage4.2R3 source R2 package mismatch")
    if not bool(state.get("finished")) or not bool(state.get("primary_pass")):
        raise ValueError("Stage4.2R3 requires a finished passing R2 source")
    source_r1 = Path(str(manifest["source_stage4_2r1_run"])).expanduser().resolve()
    r1_manifest = read_json(source_r1 / "stage4_2r1_manifest.json")
    source_r17 = Path(str(r1_manifest["source_stage4_1r17_run"])).expanduser().resolve()
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
        root = project_dir / str(cfg.get("output_root", "stage4_2r3_runs"))
        run_dir = root / f"{cfg['run_name']}_{utc_timestamp()}"
    else:
        run_dir = run_dir_override.expanduser().resolve()
    return Stage42R3Context(
        cfg=cfg,
        paths=Stage42R3Paths.from_run_dir(run_dir),
        project_dir=project_dir,
        source_r2_run=source_r2,
        source_r1_run=source_r1,
        source_r17_run=source_r17,
        source_r2_manifest=manifest,
        source_r2_state=state,
        r1_ctx=r1_ctx,
        source_fingerprint=_source_fingerprint(source_r2, source_r1, source_r17),
    )


def _nullspace_directions(modes_tsc: np.ndarray) -> np.ndarray:
    modes = np.asarray(modes_tsc, dtype=float)
    if modes.shape != (N_COILS, N_MODES) or not np.all(np.isfinite(modes)):
        raise ValueError("Stage4.2R3 frozen mode basis shape/value mismatch")
    projector = np.eye(N_COILS) - modes @ np.linalg.pinv(modes)
    directions: list[np.ndarray] = []
    for coil_index in range(N_COILS):
        candidate = projector[:, coil_index].copy()
        for existing in directions:
            candidate -= float(candidate @ existing) * existing
        norm = float(np.linalg.norm(candidate))
        if norm <= 1e-10:
            continue
        candidate /= norm
        largest = int(np.argmax(np.abs(candidate)))
        if candidate[largest] < 0.0:
            candidate *= -1.0
        candidate /= float(np.max(np.abs(candidate)))
        directions.append(candidate)
    if len(directions) < 3:
        raise ValueError("Stage4.2R3 could not construct three nullspace directions")
    output = np.stack(directions[:3])
    if float(np.max(np.abs(output @ modes))) > 1e-9:
        raise ValueError("Stage4.2R3 generated direction is not orthogonal to modes")
    return output


def _generation_base_payload(ctx: Stage42R3Context) -> dict[str, Any]:
    path = (
        ctx.source_r1_run
        / "stage4_2r1_restart_variants"
        / "source_slew_1p000_h35.payload.json"
    )
    payload = copy.deepcopy(read_json(path))
    env_cfg = copy.deepcopy(payload["env_cfg"])
    storage = ctx.cfg["storage"]
    env_cfg["tsc_timeout_s"] = float(ctx.cfg["runtime"]["tsc_timeout_s"])
    env_cfg["tsc_workspace_root"] = str(
        Path(
            os.environ.get(
                "STAGE4_2R3_TSC_WORKSPACE_ROOT", storage["tsc_workspace_root"]
            )
        )
        .expanduser()
        .resolve()
    )
    env_cfg["run_root"] = str(
        Path(
            os.environ.get("STAGE4_2R3_TSC_RUN_ROOT", storage["tsc_run_root"])
        )
        .expanduser()
        .resolve()
    )
    env_cfg["tsc_run_root"] = env_cfg["run_root"]
    env_cfg["keep_failed_episode_dir"] = bool(
        storage.get("keep_failed_episode_dir", False)
    )
    env_cfg["keep_last_n_failed_episode_dirs"] = int(
        storage.get("keep_last_n_failed_episode_dirs", 0)
    )
    train_cfg = copy.deepcopy(payload["train_cfg"])
    env_path = ctx.paths.variants / "state_generation_env.json"
    train_path = ctx.paths.variants / "state_generation_train.json"
    atomic_write_json(env_path, env_cfg)
    train_cfg["env_config"] = str(env_path)
    train_cfg.setdefault("episode", {})["max_episode_steps"] = 14
    atomic_write_json(train_path, train_cfg)
    payload["env_cfg"] = env_cfg
    payload["train_cfg"] = train_cfg
    payload["variant_id"] = "stage4_2r3_state_generation"
    return payload


def _state_spec_grid(directions: np.ndarray, cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    generation = cfg["state_generation"]
    specs: list[dict[str, Any]] = []
    for direction_index in map(int, generation["nullspace_direction_indices"]):
        direction = np.asarray(directions[direction_index], dtype=float).reshape(N_COILS)
        for amplitude in map(float, generation["amplitude_fractions"]):
            for settle_steps in map(int, generation["settle_steps"]):
                pair_id = (
                    f"q{direction_index}_a{amplitude:.3f}_settle{settle_steps}"
                    .replace(".", "p")
                )
                horizon = int(generation["pulse_steps"]) + settle_steps
                for order in map(str, generation["history_orders"]):
                    sign = 1.0 if order == "plus_first" else -1.0
                    actions = [
                        (sign * amplitude * direction).tolist(),
                        (-sign * amplitude * direction).tolist(),
                    ]
                    actions.extend([[0.0] * N_COILS for _ in range(settle_steps)])
                    identity = {
                        "stage": STAGE,
                        "phase": "authentic_state_generation",
                        "pair_id": pair_id,
                        "history_order": order,
                        "direction_index": direction_index,
                        "amplitude_fraction": amplitude,
                        "settle_steps": settle_steps,
                        "direction": direction.tolist(),
                        "controller_revision": CONTROLLER_REVISION,
                    }
                    specs.append(
                        {
                            "kind": "stage4_2r3_authentic_hidden_history_state_generation",
                            "controller_revision": CONTROLLER_REVISION,
                            "experiment_id": _scenario_digest(identity),
                            "phase": "authentic_state_generation",
                            "target_id": "preconditioning",
                            "target_R_offset_m": 0.0,
                            "target_Z_offset_m": 0.0,
                            "target_Ip_offset_A": 0.0,
                            "action_delay_steps": 0,
                            "controller_action_delay_steps": 0,
                            "slew_scale": 1.0,
                            "controller_slew_scale_estimate": 1.0,
                            "environment_variant": "stage4_2r3_state_generation",
                            "horizon_steps": horizon,
                            "checkpoint_step": horizon,
                            "source_initial_action": [0.0] * N_COILS,
                            "source_actions": actions,
                            "pair_id": pair_id,
                            "history_order": order,
                            "nullspace_direction_index": direction_index,
                            "nullspace_direction": direction.tolist(),
                            "amplitude_fraction": amplitude,
                            "settle_steps": settle_steps,
                            "zero_requested_net_coil_increment": True,
                            "authentic_tsc_state_generation": True,
                            "hidden_state_edited": False,
                            "control_outcome_available_to_pair_selector": False,
                        }
                    )
    expected = int(generation["expected_rollouts"])
    if len(specs) != expected or len({spec["experiment_id"] for spec in specs}) != expected:
        raise ValueError("Stage4.2R3 state-generation specification coverage mismatch")
    return specs


class LocalStateGenerationWorker:
    def __init__(
        self,
        payload: dict[str, Any],
        library: dict[str, Any],
        bundle: dict[str, Any],
        worker_id: str,
        selector_cfg: dict[str, Any],
        snapshot_root: str,
        checkpoint_cfg: dict[str, Any],
    ):
        self.worker = r1.LocalPlantReplayWorker(
            payload,
            library,
            bundle,
            worker_id,
            selector_cfg,
            snapshot_root,
            checkpoint_cfg,
        )

    def close(self) -> None:
        self.worker.close()

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        result = self.worker.evaluate_capture(spec)
        result["stage"] = STAGE
        result["controller_revision"] = CONTROLLER_REVISION
        result["spec"] = copy.deepcopy(spec)
        result["completed"] = True
        result["exact_source_action_replay_requested"] = False
        result["state_generation_summary"] = {
            "authentic_tsc_actions": True,
            "authentic_snapshot_requested": True,
            "hidden_state_edited": False,
            "full_wire_telemetry_recorded": True,
            "pair_id": spec["pair_id"],
            "history_order": spec["history_order"],
            "zero_requested_net_coil_increment": True,
        }
        return _json_safe(result)


_STATE_RAY_ACTOR = None


def _state_ray_actor_class():
    global _STATE_RAY_ACTOR
    if _STATE_RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class Stage42R3StateActor:
            def __init__(
                self,
                payload,
                library,
                bundle,
                worker_id,
                selector_cfg,
                snapshot_root,
                checkpoint_cfg,
            ):
                self.worker = LocalStateGenerationWorker(
                    payload,
                    library,
                    bundle,
                    worker_id,
                    selector_cfg,
                    snapshot_root,
                    checkpoint_cfg,
                )

            def evaluate(self, spec):
                return self.worker.evaluate(spec)

            def close(self):
                self.worker.close()
                return True

        _STATE_RAY_ACTOR = Stage42R3StateActor
    return _STATE_RAY_ACTOR


def _result_complete(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        result = read_json_gz(path)
        return bool(
            result.get("completed")
            and str(result.get("experiment_id", "")).strip()
            and isinstance(result.get("spec"), Mapping)
        )
    except Exception:
        return False


def _structured_actor_failure(spec: Mapping[str, Any], exc: Exception) -> dict[str, Any]:
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
    }


def _evaluate_state_generation(
    ctx: Stage42R3Context,
    specs: Sequence[dict[str, Any]],
    *,
    backend: str,
    resume: bool,
) -> list[dict[str, Any]]:
    raw_dir = ctx.paths.state_generation / "raw"
    snapshot_root = ctx.paths.state_generation / "snapshots"
    raw_dir.mkdir(parents=True, exist_ok=True)
    snapshot_root.mkdir(parents=True, exist_ok=True)
    payload = _generation_base_payload(ctx)
    library, bundle, selector = r1._library_bundle_selector(ctx.r1_ctx)
    checkpoint_cfg = copy.deepcopy(ctx.r1_ctx.cfg["checkpoint"])
    pending = [
        spec
        for spec in specs
        if not (
            resume
            and _result_complete(raw_dir / f"{spec['experiment_id']}.json.gz")
        )
    ]
    if backend == "serial":
        for index, spec in enumerate(pending):
            worker = LocalStateGenerationWorker(
                payload,
                library,
                bundle,
                f"stage42r3_state_serial_{index:03d}",
                selector,
                str(snapshot_root),
                checkpoint_cfg,
            )
            try:
                result = worker.evaluate(spec)
            finally:
                worker.close()
            atomic_write_json_gz(raw_dir / f"{spec['experiment_id']}.json.gz", result)
            print(
                f"[Stage4.2R3 state-generation] {index + 1}/{len(pending)}",
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
            log_prefix="[Stage4.2R3 state-generation]",
        )
        Actor = _state_ray_actor_class()
        actors = []
        refs = {}
        for index, spec in enumerate(pending):
            actor = Actor.remote(
                payload,
                library,
                bundle,
                f"stage42r3_state_{index:03d}",
                selector,
                str(snapshot_root),
                checkpoint_cfg,
            )
            actors.append(actor)
            refs[actor.evaluate.remote(spec)] = spec
        print(
            "[Stage4.2R3 state-generation] "
            f"actor_count={plan.actor_count} pending={len(pending)}",
            flush=True,
        )
        completed = 0
        try:
            while refs:
                ready, _ = ray.wait(list(refs), num_returns=1, timeout=30.0)
                if not ready:
                    print(
                        f"[Stage4.2R3 state-generation] waiting {completed}/{len(pending)}",
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
                        raw_dir / f"{spec['experiment_id']}.json.gz", result
                    )
                    completed += 1
                    if completed % 10 == 0 or not refs:
                        print(
                            f"[Stage4.2R3 state-generation] {completed}/{len(pending)}",
                            flush=True,
                        )
        finally:
            s2._close_ray_actors(
                actors,
                timeout_s=float(
                    ctx.cfg["storage"].get("actor_close_timeout_s", 1800.0)
                ),
            )
    elif backend not in {"serial", "ray"}:
        raise ValueError("backend must be serial or ray")
    return [
        read_json_gz(raw_dir / f"{spec['experiment_id']}.json.gz") for spec in specs
    ]


def _state_row(result: Mapping[str, Any]) -> dict[str, Any]:
    trajectory = list(result.get("trajectory") or [])
    spec = result["spec"]
    horizon = int(spec["horizon_steps"])
    valid_shape = len(trajectory) == horizon + 1 and horizon >= 2
    if not bool(result.get("success")) or not valid_shape:
        return {
            "experiment_id": str(result["experiment_id"]),
            "pair_id": str(spec["pair_id"]),
            "history_order": str(spec["history_order"]),
            "success": False,
            "failure_reason": str(result.get("failure_reason", "")),
            "failure_class": "runtime_or_environment_error",
        }
    final = trajectory[-1]
    previous = trajectory[-2]
    coil = np.asarray(final["currents_a_tsc"], dtype=float).reshape(-1)
    action = np.asarray(final["action_norm_tsc"], dtype=float).reshape(-1)
    wire = np.asarray(final["wire_currents_a"], dtype=float).reshape(-1)
    if (
        coil.shape != (N_COILS,)
        or action.shape != (N_COILS,)
        or wire.shape != (N_WIRES,)
        or not np.all(np.isfinite(np.concatenate([coil, action, wire])))
    ):
        return {
            "experiment_id": str(result["experiment_id"]),
            "pair_id": str(spec["pair_id"]),
            "history_order": str(spec["history_order"]),
            "success": False,
            "failure_reason": "invalid endpoint coil/action/wire telemetry",
            "failure_class": "raw_or_snapshot_corruption",
        }
    snapshot = result.get("restart_snapshot") or {}
    snapshot_dir = Path(str(snapshot.get("snapshot_dir", "")))
    snapshot_manifest_path = Path(
        str(snapshot.get("snapshot_manifest_path", ""))
    )
    try:
        snapshot_manifest = read_json(snapshot_manifest_path)
        snapshot_pass = bool(
            snapshot.get("snapshot_files_valid")
            and snapshot.get("snapshot_wire_vector_exact_to_capture_state")
            and str(snapshot.get("snapshot_manifest_digest", "")).strip()
            and snapshot_dir.is_dir()
            and snapshot_manifest_path.is_file()
            and str(snapshot_manifest.get("digest", ""))
            == str(snapshot["snapshot_manifest_digest"])
            and r1._validate_snapshot_inventory(
                snapshot_dir, snapshot_manifest
            )
        )
    except Exception:
        snapshot_pass = False
    return {
        "experiment_id": str(result["experiment_id"]),
        "pair_id": str(spec["pair_id"]),
        "history_order": str(spec["history_order"]),
        "nullspace_direction_index": int(spec["nullspace_direction_index"]),
        "amplitude_fraction": float(spec["amplitude_fraction"]),
        "settle_steps": int(spec["settle_steps"]),
        "horizon_steps": horizon,
        "success": snapshot_pass,
        "failure_reason": "" if snapshot_pass else "snapshot integrity flags failed",
        "failure_class": "" if snapshot_pass else "raw_or_snapshot_corruption",
        "R": float(final["R"]),
        "Z": float(final["Z"]),
        "Ip": float(final["Ip"]),
        "vR_m_per_s": (float(final["R"]) - float(previous["R"])) / (DT_MS / 1000.0),
        "vZ_m_per_s": (float(final["Z"]) - float(previous["Z"])) / (DT_MS / 1000.0),
        "coil_currents_a": coil.tolist(),
        "action_norm_tsc": action.tolist(),
        "wire_currents_a": wire.tolist(),
        "wire_rms_a": _rms(wire),
        "snapshot_dir": str(snapshot["snapshot_dir"]),
        "snapshot_manifest_path": str(snapshot["snapshot_manifest_path"]),
        "snapshot_manifest_digest": str(snapshot["snapshot_manifest_digest"]),
        "snapshot_time_ms": int(snapshot["snapshot_time_ms"]),
    }


def _pair_metrics(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    gate: Mapping[str, Any],
) -> dict[str, Any]:
    if not bool(left.get("success")) or not bool(right.get("success")):
        return {
            "pair_id": str(left.get("pair_id", right.get("pair_id", ""))),
            "pair_members_valid": False,
            "visible_match_pass": False,
            "hidden_separation_pass": False,
            "accepted": False,
            "failure_class": "state_generation_member_failure",
        }
    coil_left = np.asarray(left["coil_currents_a"], dtype=float)
    coil_right = np.asarray(right["coil_currents_a"], dtype=float)
    action_left = np.asarray(left["action_norm_tsc"], dtype=float)
    action_right = np.asarray(right["action_norm_tsc"], dtype=float)
    wire_left = np.asarray(left["wire_currents_a"], dtype=float)
    wire_right = np.asarray(right["wire_currents_a"], dtype=float)
    coil_diff = coil_left - coil_right
    action_diff = action_left - action_right
    wire_diff = wire_left - wire_right
    denominator = max(
        1.0,
        0.5 * (float(left["wire_rms_a"]) + float(right["wire_rms_a"])),
    )
    metrics = {
        "R_abs_difference_m": abs(float(left["R"]) - float(right["R"])),
        "Z_abs_difference_m": abs(float(left["Z"]) - float(right["Z"])),
        "Ip_abs_difference_A": abs(float(left["Ip"]) - float(right["Ip"])),
        "vR_abs_difference_m_per_s": abs(
            float(left["vR_m_per_s"]) - float(right["vR_m_per_s"])
        ),
        "vZ_abs_difference_m_per_s": abs(
            float(left["vZ_m_per_s"]) - float(right["vZ_m_per_s"])
        ),
        "coil_max_abs_difference_A": float(np.max(np.abs(coil_diff))),
        "coil_rms_difference_A": _rms(coil_diff),
        "action_max_abs_difference": float(np.max(np.abs(action_diff))),
        "wire_max_abs_difference_A": float(np.max(np.abs(wire_diff))),
        "wire_rms_difference_A": _rms(wire_diff),
        "wire_relative_rms_difference": _rms(wire_diff) / denominator,
    }
    ratios = [
        metrics["R_abs_difference_m"] / float(gate["R_abs_difference_m_max"]),
        metrics["Z_abs_difference_m"] / float(gate["Z_abs_difference_m_max"]),
        metrics["Ip_abs_difference_A"] / float(gate["Ip_abs_difference_A_max"]),
        metrics["vR_abs_difference_m_per_s"]
        / float(gate["vR_abs_difference_m_per_s_max"]),
        metrics["vZ_abs_difference_m_per_s"]
        / float(gate["vZ_abs_difference_m_per_s_max"]),
        metrics["coil_max_abs_difference_A"]
        / float(gate["coil_max_abs_difference_A_max"]),
        metrics["coil_rms_difference_A"]
        / float(gate["coil_rms_difference_A_max"]),
        metrics["action_max_abs_difference"]
        / float(gate["action_max_abs_difference_max"]),
    ]
    same_clock = bool(
        int(left["snapshot_time_ms"]) == int(right["snapshot_time_ms"])
        and int(left["horizon_steps"]) == int(right["horizon_steps"])
    )
    visible_pass = bool(max(ratios) <= 1.0 and same_clock)
    hidden_pass = bool(
        wire_left.shape == wire_right.shape == (int(gate["wire_count"]),)
        and metrics["wire_max_abs_difference_A"]
        >= float(gate["wire_max_abs_difference_A_min"])
        and metrics["wire_relative_rms_difference"]
        >= float(gate["wire_relative_rms_difference_min"])
    )
    return {
        "pair_id": str(left["pair_id"]),
        "nullspace_direction_index": int(left["nullspace_direction_index"]),
        "amplitude_fraction": float(left["amplitude_fraction"]),
        "settle_steps": int(left["settle_steps"]),
        "pair_members_valid": True,
        "same_snapshot_clock": same_clock,
        "plus_first_experiment_id": str(left["experiment_id"]),
        "minus_first_experiment_id": str(right["experiment_id"]),
        "plus_first_snapshot_dir": str(left["snapshot_dir"]),
        "minus_first_snapshot_dir": str(right["snapshot_dir"]),
        "plus_first_snapshot_manifest_digest": str(
            left["snapshot_manifest_digest"]
        ),
        "minus_first_snapshot_manifest_digest": str(
            right["snapshot_manifest_digest"]
        ),
        "plus_first_state": copy.deepcopy(dict(left)),
        "minus_first_state": copy.deepcopy(dict(right)),
        **metrics,
        "visible_max_normalized_ratio": max(ratios),
        "visible_match_pass": visible_pass,
        "hidden_separation_pass": hidden_pass,
        "accepted": bool(visible_pass and hidden_pass),
        "failure_class": (
            ""
            if visible_pass and hidden_pass
            else "invalid_visible_match"
            if not visible_pass
            else "insufficient_hidden_separation"
        ),
    }


def _frozen_initial_state(ctx: Stage42R3Context) -> dict[str, Any]:
    sources = r1._selected_source_cases(ctx.r1_ctx)
    rows = [list(result["trajectory"])[0] for result in sources.values()]
    if len(rows) != 18:
        raise ValueError("Stage4.2R3 frozen source initial-state coverage mismatch")
    reference = rows[0]
    reference_vector = np.asarray(
        [reference["R"], reference["Z"], reference["Ip"], *reference["currents_a_tsc"]],
        dtype=float,
    )
    for row in rows[1:]:
        vector = np.asarray(
            [row["R"], row["Z"], row["Ip"], *row["currents_a_tsc"]], dtype=float
        )
        if not np.array_equal(vector, reference_vector):
            raise ValueError("Stage4.2R3 R17 cases do not share one frozen initial state")
    return {
        "R": float(reference["R"]),
        "Z": float(reference["Z"]),
        "Ip": float(reference["Ip"]),
        "coil_currents_a": list(map(float, reference["currents_a_tsc"])),
    }


def _different_initial_metrics(
    pair: Mapping[str, Any],
    frozen: Mapping[str, Any],
    gate: Mapping[str, Any],
) -> dict[str, Any]:
    plus = pair["plus_first_state"]
    minus = pair["minus_first_state"]
    centroid_r = 0.5 * (float(plus["R"]) + float(minus["R"]))
    centroid_z = 0.5 * (float(plus["Z"]) + float(minus["Z"]))
    centroid_ip = 0.5 * (float(plus["Ip"]) + float(minus["Ip"]))
    centroid_coil = 0.5 * (
        np.asarray(plus["coil_currents_a"], dtype=float)
        + np.asarray(minus["coil_currents_a"], dtype=float)
    )
    frozen_coil = np.asarray(frozen["coil_currents_a"], dtype=float)
    metrics = {
        "centroid_R": centroid_r,
        "centroid_Z": centroid_z,
        "centroid_Ip": centroid_ip,
        "centroid_R_difference_m": abs(centroid_r - float(frozen["R"])),
        "centroid_Z_difference_m": abs(centroid_z - float(frozen["Z"])),
        "centroid_Ip_difference_A": abs(centroid_ip - float(frozen["Ip"])),
        "centroid_coil_rms_difference_A": _rms(centroid_coil - frozen_coil),
    }
    passed = bool(
        metrics["centroid_R_difference_m"]
        >= float(gate["R_centroid_difference_m_min"])
        or metrics["centroid_Z_difference_m"]
        >= float(gate["Z_centroid_difference_m_min"])
        or metrics["centroid_Ip_difference_A"]
        >= float(gate["Ip_centroid_difference_A_min"])
        or metrics["centroid_coil_rms_difference_A"]
        >= float(gate["coil_centroid_rms_difference_A_min"])
    )
    return {**metrics, "different_initial_state_pass": passed}


def analyze_state_generation(
    ctx: Stage42R3Context, results: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    state_rows = [_state_row(result) for result in results]
    by_pair: dict[str, dict[str, dict[str, Any]]] = {}
    for row in state_rows:
        by_pair.setdefault(str(row["pair_id"]), {})[str(row["history_order"])] = row
    pair_rows = []
    for pair_id in sorted(by_pair):
        members = by_pair[pair_id]
        if set(members) != {"plus_first", "minus_first"}:
            pair_rows.append(
                {
                    "pair_id": pair_id,
                    "pair_members_valid": False,
                    "visible_match_pass": False,
                    "hidden_separation_pass": False,
                    "accepted": False,
                    "failure_class": "missing_pair_member",
                }
            )
            continue
        pair_rows.append(
            _pair_metrics(
                members["plus_first"],
                members["minus_first"],
                ctx.cfg["pair_gate"],
            )
        )
    accepted = [row for row in pair_rows if bool(row.get("accepted"))]
    selected: list[dict[str, Any]] = []
    for direction in map(
        int, ctx.cfg["state_generation"]["nullspace_direction_indices"]
    ):
        candidates = [
            row
            for row in accepted
            if int(row["nullspace_direction_index"]) == direction
        ]
        if not candidates:
            continue
        candidates.sort(
            key=lambda row: (
                -float(row["wire_relative_rms_difference"]),
                float(row["visible_max_normalized_ratio"]),
                float(row["amplitude_fraction"]),
                -int(row["settle_steps"]),
                str(row["pair_id"]),
            )
        )
        selected.append(copy.deepcopy(candidates[0]))
    selected_ids = {str(row["pair_id"]) for row in selected}
    frozen = _frozen_initial_state(ctx)
    initial_gate = ctx.cfg["different_initial_state_gate"]
    for row in pair_rows:
        row["selected"] = str(row["pair_id"]) in selected_ids
        if row["selected"]:
            metrics = _different_initial_metrics(row, frozen, initial_gate)
            row.update(metrics)
    selected = [row for row in pair_rows if bool(row.get("selected"))]
    different_count = sum(
        bool(row.get("different_initial_state_pass")) for row in selected
    )
    minimum_pairs = int(ctx.cfg["pair_gate"]["minimum_selected_pairs"])
    maximum_pairs = int(ctx.cfg["pair_gate"]["maximum_selected_pairs"])
    minimum_initial = int(initial_gate["minimum_selected_centroids"])
    expected_rollouts = int(ctx.cfg["state_generation"]["expected_rollouts"])
    environment_success_count = sum(
        bool(row.get("success")) for row in state_rows
    )
    runtime_error_count = sum(
        row.get("failure_class") == "runtime_or_environment_error"
        for row in state_rows
    )
    corruption_count = sum(
        row.get("failure_class") == "raw_or_snapshot_corruption"
        for row in state_rows
    )
    complete_state_grid = bool(
        len(state_rows) == expected_rollouts
        and environment_success_count == expected_rollouts
        and runtime_error_count == 0
        and corruption_count == 0
    )
    passed = bool(
        complete_state_grid
        and len(pair_rows) == int(ctx.cfg["state_generation"]["expected_pairs"])
        and len(selected) >= minimum_pairs
        and len(selected) <= maximum_pairs
        and different_count >= minimum_initial
    )
    state_public = [
        {
            key: value
            for key, value in row.items()
            if key not in {"coil_currents_a", "action_norm_tsc", "wire_currents_a"}
        }
        for row in state_rows
    ]
    pair_public = []
    for row in pair_rows:
        pair_public.append(
            {
                key: value
                for key, value in row.items()
                if key not in {"plus_first_state", "minus_first_state"}
            }
        )
    atomic_write_json(ctx.paths.state_generation / "results.json", state_public)
    write_csv(ctx.paths.state_generation / "results.csv", state_public)
    atomic_write_json(ctx.paths.pair_analysis / "results.json", pair_public)
    write_csv(ctx.paths.pair_analysis / "results.csv", pair_public)
    atomic_write_json(ctx.paths.pair_analysis / "selected_pairs.json", selected)
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "authentic_hidden_history_state_generation_and_pair_selection",
        "expected_state_rollouts": int(
            ctx.cfg["state_generation"]["expected_rollouts"]
        ),
        "state_rollout_count": len(state_rows),
        "state_environment_success_count": environment_success_count,
        "runtime_or_environment_error_count": runtime_error_count,
        "raw_or_snapshot_corruption_count": corruption_count,
        "complete_state_grid": complete_state_grid,
        "expected_pair_count": int(ctx.cfg["state_generation"]["expected_pairs"]),
        "pair_count": len(pair_rows),
        "visible_match_pair_count": sum(
            bool(row.get("visible_match_pass")) for row in pair_rows
        ),
        "hidden_separation_pair_count": sum(
            bool(row.get("hidden_separation_pass")) for row in pair_rows
        ),
        "accepted_pair_count": len(accepted),
        "selected_pair_count": len(selected),
        "selected_pair_ids": [str(row["pair_id"]) for row in selected],
        "selected_different_initial_state_count": different_count,
        "minimum_selected_pairs_required": minimum_pairs,
        "minimum_different_initial_centroids_required": minimum_initial,
        "control_outcome_used_for_selection": False,
        "hidden_state_edited": False,
        "passed": passed,
        "stop_reason": (
            ""
            if passed
            else "state_generation_runtime_or_environment_error"
            if runtime_error_count
            else "raw_or_snapshot_corruption"
            if corruption_count
            else "incomplete_state_generation_grid"
            if not complete_state_grid
            else "insufficient_valid_pairs"
            if len(selected) < minimum_pairs
            else "selected_pair_count_exceeds_preregistered_maximum"
            if len(selected) > maximum_pairs
            else "insufficient_different_initial_state_centroids"
        ),
    }
    atomic_write_json(ctx.paths.state_generation / "summary.json", summary)
    atomic_write_json(ctx.paths.pair_analysis / "summary.json", summary)
    return summary


def _prepare_dirs(paths: Stage42R3Paths) -> None:
    for path in (
        paths.run_dir,
        paths.source_reference,
        paths.state_generation,
        paths.state_generation / "raw",
        paths.state_generation / "snapshots",
        paths.pair_analysis,
        paths.variants,
        paths.control,
        paths.control / "raw",
        paths.analysis,
    ):
        path.mkdir(parents=True, exist_ok=True)


def prepare(ctx: Stage42R3Context, *, resume: bool) -> None:
    _prepare_dirs(ctx.paths)
    payload = _generation_base_payload(ctx)
    directions = _nullspace_directions(np.asarray(payload["modes_tsc"], dtype=float))
    specs = _state_spec_grid(directions, ctx.cfg)
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "source_stage4_2r2_run": str(ctx.source_r2_run),
        "source_stage4_2r1_run": str(ctx.source_r1_run),
        "source_stage4_1r17_run": str(ctx.source_r17_run),
        "source_fingerprint": ctx.source_fingerprint,
        "config_digest": _canonical_digest(ctx.cfg),
        "state_generation_spec_digest": _canonical_digest(specs),
        "nullspace_directions": directions.tolist(),
        "formal_timing_contract": copy.deepcopy(
            ctx.cfg["formal_timing_contract"]
        ),
        "preregistered_pair_gate": copy.deepcopy(ctx.cfg["pair_gate"]),
        "preregistered_initial_state_gate": copy.deepcopy(
            ctx.cfg["different_initial_state_gate"]
        ),
        "control_matrix": copy.deepcopy(ctx.cfg["control_matrix"]),
    }
    if ctx.paths.manifest.is_file():
        old = read_json(ctx.paths.manifest)
        for key in (
            "stage",
            "controller_revision",
            "package_revision",
            "source_stage4_2r2_run",
            "source_stage4_2r1_run",
            "source_stage4_1r17_run",
            "config_digest",
            "state_generation_spec_digest",
            "source_fingerprint",
        ):
            if old.get(key) != manifest.get(key):
                raise ValueError(
                    f"Stage4.2R3 resume incompatibility in manifest field {key}"
                )
        if not resume:
            raise FileExistsError(
                "Stage4.2R3 run already exists; use --resume or a fresh run"
            )
    else:
        atomic_write_json(ctx.paths.manifest, manifest)
    atomic_write_json(ctx.paths.run_dir / "stage4_2r3_config.resolved.json", ctx.cfg)
    atomic_write_json(
        ctx.paths.source_reference / "stage4_2r3_source_fingerprint.json",
        ctx.source_fingerprint,
    )
    atomic_write_json(
        ctx.paths.source_reference / "state_generation_specs.json", specs
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


def _source_controller_cases(
    ctx: Stage42R3Context,
) -> dict[tuple[str, int, float], dict[str, Any]]:
    sources = r1._selected_source_cases(ctx.r1_ctx)
    required = {
        (target, int(actuator["actual_delay_steps"]), float(actuator["actual_slew_scale"]))
        for target in ctx.cfg["control_matrix"]["targets"]
        for actuator in ctx.cfg["control_matrix"]["future_actuator_cases"]
    }
    if not required.issubset(sources):
        raise ValueError(f"Stage4.2R3 frozen source cases missing: {required - set(sources)}")
    return {key: sources[key] for key in sorted(required)}


def _control_payload(
    ctx: Stage42R3Context,
    *,
    snapshot_dir: Path,
    snapshot_digest: str,
    slew: float,
    experiment_id: str,
) -> dict[str, Any]:
    horizon = _formal_horizon(slew)
    variant = f"slew_{float(slew):.3f}".replace(".", "p")
    base_path = (
        ctx.source_r1_run
        / "stage4_2r1_restart_variants"
        / f"source_{variant}_h{horizon}.payload.json"
    )
    payload = copy.deepcopy(read_json(base_path))
    env_cfg = copy.deepcopy(payload["env_cfg"])
    storage = ctx.cfg["storage"]
    env_cfg["simulation_root"] = str(snapshot_dir.parent)
    env_cfg["start_folder"] = snapshot_dir.name
    env_cfg["tsc_timeout_s"] = float(ctx.cfg["runtime"]["tsc_timeout_s"])
    env_cfg["tsc_workspace_root"] = str(
        Path(
            os.environ.get(
                "STAGE4_2R3_TSC_WORKSPACE_ROOT", storage["tsc_workspace_root"]
            )
        )
        .expanduser()
        .resolve()
    )
    env_cfg["run_root"] = str(
        Path(
            os.environ.get("STAGE4_2R3_TSC_RUN_ROOT", storage["tsc_run_root"])
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
    env_path = ctx.paths.variants / f"env_{experiment_id}.json"
    train_path = ctx.paths.variants / f"train_{experiment_id}.json"
    atomic_write_json(env_path, env_cfg)
    train_cfg["env_config"] = str(env_path)
    train_cfg.setdefault("episode", {})["max_episode_steps"] = horizon
    atomic_write_json(train_path, train_cfg)
    payload["env_cfg"] = env_cfg
    payload["train_cfg"] = train_cfg
    payload["variant_id"] = f"stage4_2r3_{experiment_id}"
    payload["start_folder"] = snapshot_dir.name
    payload["slew_scale"] = float(slew)
    payload["stage4_1r4_horizon_steps"] = horizon
    payload["stage4_2r3_restart_snapshot_dir"] = str(snapshot_dir)
    payload["stage4_2r3_snapshot_manifest_digest"] = str(snapshot_digest)
    atomic_write_json(
        ctx.paths.variants / f"payload_{experiment_id}.json", payload
    )
    return payload


def build_control_specs(
    ctx: Stage42R3Context, selected_pairs: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    sources = _source_controller_cases(ctx)
    specs: list[dict[str, Any]] = []
    for pair in sorted(selected_pairs, key=lambda row: str(row["pair_id"])):
        for member in ctx.cfg["control_matrix"]["history_members"]:
            state = pair[f"{member}_state"]
            snapshot_dir = Path(str(state["snapshot_dir"])).expanduser().resolve()
            snapshot_digest = str(state["snapshot_manifest_digest"])
            for target in ctx.cfg["control_matrix"]["targets"]:
                for actuator in ctx.cfg["control_matrix"]["future_actuator_cases"]:
                    delay = int(actuator["actual_delay_steps"])
                    slew = float(actuator["actual_slew_scale"])
                    source = sources[(str(target), delay, slew)]
                    spec = copy.deepcopy(source["spec"])
                    if _forbidden_future_paths(spec):
                        raise ValueError(
                            "Stage4.2R3 frozen controller spec contains future data"
                        )
                    identity = {
                        "stage": STAGE,
                        "phase": "hidden_history_control",
                        "pair_id": str(pair["pair_id"]),
                        "history_member": str(member),
                        "state_generation_experiment_id": str(state["experiment_id"]),
                        "snapshot_manifest_digest": snapshot_digest,
                        "target_id": str(target),
                        "actual_delay_steps": delay,
                        "actual_slew_scale": slew,
                        "controller_revision": CONTROLLER_REVISION,
                    }
                    experiment_id = _scenario_digest(identity)
                    spec.update(
                        {
                            "kind": "stage4_2r3_authentic_hidden_history_control",
                            "controller_revision": CONTROLLER_REVISION,
                            "underlying_controller_revision": str(
                                source.get("controller_revision", "")
                            ),
                            "experiment_id": experiment_id,
                            "phase": "hidden_history_control",
                            "category": "hidden_history_control",
                            "pair_id": str(pair["pair_id"]),
                            "history_member": str(member),
                            "state_generation_experiment_id": str(
                                state["experiment_id"]
                            ),
                            "restart_snapshot_dir": str(snapshot_dir),
                            "restart_snapshot_manifest_digest": snapshot_digest,
                            "environment_variant": f"stage4_2r3_{experiment_id}",
                            "horizon_steps": _formal_horizon(slew),
                            "fresh_controller_required": True,
                            "fresh_tsc_process_required": True,
                            "controller_history_initialization": "empty_at_new_task_start",
                            "controller_integral_initialization": "zero",
                            "hidden_wire_current_available_to_controller": False,
                            "full_wire_current_recorded_after_action_choice": True,
                            "future_action_count": 0,
                            "future_measurement_count": 0,
                            "online_action_computation_required": True,
                            "formal_timing_unchanged": True,
                        }
                    )
                    specs.append(spec)
    expected_per_pair = int(
        ctx.cfg["control_matrix"]["expected_rollouts_per_selected_pair"]
    )
    expected = len(selected_pairs) * expected_per_pair
    if len(specs) != expected or len({spec["experiment_id"] for spec in specs}) != expected:
        raise ValueError("Stage4.2R3 control specification coverage mismatch")
    if expected and not (
        int(ctx.cfg["control_matrix"]["minimum_expected_rollouts"])
        <= expected
        <= int(ctx.cfg["control_matrix"]["maximum_expected_rollouts"])
    ):
        raise ValueError("Stage4.2R3 selected-pair rollout count is outside contract")
    return specs


def _validate_fresh_controller_source(
    base_worker: Any, spec: Mapping[str, Any]
) -> dict[str, Any]:
    """Reject source semantics that ``FreshTaskController`` does not reproduce."""

    output = copy.deepcopy(dict(spec))
    if _forbidden_future_paths(output):
        raise ValueError("fresh controller source contains forbidden future data")
    if not bool(output.get("trusted_calibration_model")):
        raise ValueError("fresh controller source calibration model is not trusted")
    if int(output["action_delay_steps"]) != int(
        output["controller_action_delay_steps"]
    ):
        raise ValueError("fresh controller source delay model does not match plant")
    if not math.isclose(
        float(output["slew_scale"]),
        float(output["controller_slew_scale_estimate"]),
        abs_tol=1e-12,
    ):
        raise ValueError("fresh controller source slew model does not match plant")
    if output.get("actual_action_delay_schedule") or output.get(
        "actual_slew_scale_schedule"
    ):
        raise ValueError("fresh controller requires static plant actuator parameters")
    if output.get("controller_action_delay_schedule") or output.get(
        "controller_slew_scale_schedule"
    ):
        raise ValueError(
            "fresh controller requires static modeled actuator parameters"
        )
    if bool((output.get("adaptive_delay_slew_estimator") or {}).get("enabled")):
        raise ValueError("fresh controller may not use the adaptive estimator")
    if not r2.r3._sensor_path_is_clean(output):
        raise ValueError("fresh controller source must use clean sensing")
    if output.get("prelude_mode_deltas"):
        raise ValueError("fresh controller source may not contain a prelude")
    if not bool(
        base_worker._flag(
            output, "delay_aware", "delay_aware_enabled"
        )
    ):
        raise ValueError("fresh controller source must use delay-aware MPC")
    if not bool(
        base_worker._flag(
            output, "gain_slew_scheduling", "gain_slew_scheduling_enabled"
        )
    ):
        raise ValueError("fresh controller source must use gain/slew scheduling")
    maximum_delay = int(
        base_worker.robust_cfg["controller_upgrade"]["delay_aware"].get(
            "maximum_modeled_action_delay_steps", 2
        )
    )
    if int(output["controller_action_delay_steps"]) > maximum_delay:
        raise ValueError("fresh controller modeled delay exceeds frozen MPC support")
    return output


class FreshTaskController(r2.PersistentController):
    """Frozen finite-envelope MPC initialized causally at a new task start.

    Unlike R2, no controller checkpoint is restored.  Only the current visible
    state is supplied at state index zero.  Hidden wire/vessel currents remain
    in the audit trajectory and never enter this object.
    """

    def __init__(
        self,
        base_worker: Any,
        bundle: Mapping[str, Any],
        source_spec: Mapping[str, Any],
        initial_state: Mapping[str, Any],
    ):
        if int(initial_state["step_index"]) != 0:
            raise ValueError("fresh task controller must start at state index zero")
        self.base = base_worker
        self.bundle = bundle
        self.checkpoint = None
        self.spec = _validate_fresh_controller_source(base_worker, source_spec)
        self.step = 0
        self.delay = int(self.spec["controller_action_delay_steps"])
        self.actual_delay = int(self.spec["action_delay_steps"])
        self.slew = float(self.spec["controller_slew_scale_estimate"])
        self.integral = np.zeros(5, dtype=float)
        self.previous = np.zeros(N_MODES, dtype=float)
        self.history = [
            {
                "step_index": 0,
                "R": float(initial_state["R"]),
                "Z": float(initial_state["Z"]),
                "Ip": float(initial_state["Ip"]),
            }
        ]
        offset = np.asarray(
            [
                self.spec.get("target_R_offset_m", 0.0),
                self.spec.get("target_Z_offset_m", 0.0),
                self.spec.get("target_Ip_offset_A", 0.0),
            ],
            dtype=float,
        )
        interpolation = r2.r3.s34.interpolation_for_target(
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
        self.nominal_feature = r2.r3.s34._nominal_feature(
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
        ).reshape(N_MODES)
        self.actual_gain = np.asarray(
            self.spec.get("actuator_gain_by_mode", [1.0] * N_MODES),
            dtype=float,
        ).reshape(N_MODES)
        self.actuator_bias = np.asarray(
            self.spec.get("actuator_bias_by_mode", [0.0] * N_MODES),
            dtype=float,
        ).reshape(N_MODES)
        self.phase = "main_control"
        transition = self.spec.get("anticipatory_transition_issue_step")
        self.transition_step = None if transition is None else int(transition)
        self.damping_integral = np.zeros(5, dtype=float)
        self.terminal_integral = np.zeros(5, dtype=float)

        initial_currents = np.asarray(
            initial_state["currents_a_tsc"], dtype=float
        ).reshape(N_COILS)
        nominal_commands, _ = self.base._nominal_command_plan(
            self.nominal_physical,
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
            command = (
                np.asarray(nominal_commands[index], dtype=float).reshape(N_MODES)
                if prime_queue
                else np.zeros(N_MODES, dtype=float)
            )
            desired = (
                self.nominal_physical[index].copy()
                if prime_queue
                else np.zeros(N_MODES, dtype=float)
            )
            self.queue.append(
                {
                    "origin": "prime",
                    "origin_index": -self.actual_delay + index,
                    "command": command,
                    "desired_physical": desired,
                }
            )


def run_offline_frozen_controller_audit(
    ctx: Stage42R3Context,
) -> dict[str, Any]:
    """Prove the fresh step-zero controller exactly reproduces frozen R17.

    The source trajectory is streamed one current state at a time solely to
    this no-TSC audit harness.  Neither future states nor expected actions are
    stored in the controller or in any real rollout specification.
    """

    sources = _source_controller_cases(ctx)
    library, bundle, selector = r1._library_bundle_selector(ctx.r1_ctx)
    rows: list[dict[str, Any]] = []
    for index, key in enumerate(
        sorted(sources, key=lambda item: (item[2], item[1], item[0]))
    ):
        source = sources[key]
        slew = float(key[2])
        horizon = _formal_horizon(slew)
        variant = f"slew_{slew:.3f}".replace(".", "p")
        payload = read_json(
            ctx.source_r1_run
            / "stage4_2r1_restart_variants"
            / f"source_{variant}_h{horizon}.payload.json"
        )
        plant = r1.LocalPlantReplayWorker(
            payload,
            library,
            bundle,
            f"stage42r3_offline_{index:03d}",
            selector,
        )
        exact = True
        maximum = 0.0
        first_mismatch: int | None = None
        phase_counts: dict[str, int] = {}
        try:
            trajectory = list(source.get("trajectory") or [])
            if len(trajectory) < horizon + 1:
                raise ValueError("R17 source trajectory is shorter than formal horizon")
            initial = copy.deepcopy(dict(trajectory[0]))
            initial["step_index"] = 0
            controller = FreshTaskController(
                plant.base_worker, bundle, source["spec"], initial
            )
            for step in range(horizon):
                current = copy.deepcopy(dict(trajectory[step]))
                current["step_index"] = step
                action, trace = controller.action(current)
                expected = np.asarray(
                    trajectory[step + 1]["action_norm_tsc"], dtype=float
                ).reshape(N_COILS)
                difference = float(
                    np.max(np.abs(np.asarray(action, dtype=float) - expected))
                )
                maximum = max(maximum, difference)
                if not np.array_equal(np.asarray(action, dtype=float), expected):
                    exact = False
                    if first_mismatch is None:
                        first_mismatch = step
                if int(trace["measurement_max_state_index_used"]) > step:
                    raise ValueError("fresh controller used a future measurement")
                if bool(trace.get("future_measurement_used")):
                    raise ValueError("fresh controller declared future measurement use")
                phase = str(trace["controller_phase"])
                phase_counts[phase] = phase_counts.get(phase, 0) + 1
                next_state = copy.deepcopy(dict(trajectory[step + 1]))
                next_state["step_index"] = step + 1
                controller.advance(next_state)
        finally:
            plant.close()
        rows.append(
            {
                "target_id": key[0],
                "actual_delay_steps": key[1],
                "actual_slew_scale": key[2],
                "source_experiment_id": str(source["experiment_id"]),
                "action_steps": horizon,
                "phase_counts": phase_counts,
                "source_state_streamed_only_to_offline_audit": True,
                "source_future_state_persisted_in_controller": False,
                "source_future_action_read_by_controller": False,
                "online_action_exact": exact,
                "maximum_online_action_abs_difference": maximum,
                "first_mismatch_step": first_mismatch,
                "passed": bool(exact and first_mismatch is None),
            }
        )
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "offline_frozen_controller_recomputation",
        "expected_cases": len(sources),
        "n_cases": len(rows),
        "exact_case_count": sum(bool(row["online_action_exact"]) for row in rows),
        "maximum_online_action_abs_difference": max(
            (
                float(row["maximum_online_action_abs_difference"])
                for row in rows
            ),
            default=math.inf,
        ),
        "future_action_read_count": sum(
            bool(row["source_future_action_read_by_controller"]) for row in rows
        ),
        "future_state_persisted_count": sum(
            bool(row["source_future_state_persisted_in_controller"])
            for row in rows
        ),
        "real_tsc_executed": False,
    }
    summary["passed"] = bool(
        len(rows) == len(sources)
        and rows
        and all(bool(row["passed"]) for row in rows)
        and summary["future_action_read_count"] == 0
        and summary["future_state_persisted_count"] == 0
    )
    output = {"summary": summary, "results": rows}
    atomic_write_json(
        ctx.paths.source_reference
        / "offline_frozen_controller_recomputation_audit.json",
        output,
    )
    return summary


class LocalHiddenHistoryControlWorker:
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
                raise ValueError("hidden-history control horizon changed")
            self.base.env.reset()
            zero_action = np.zeros(N_COILS, dtype=np.float32)
            initial = r1._state_record_full(self.base.env, 0, zero_action)
            trajectory = [initial]
            controller = FreshTaskController(
                self.base, self.bundle, spec, initial
            )
            trace: list[dict[str, Any]] = []
            for step in range(horizon):
                action, controller_row = controller.action(trajectory[-1])
                _, _, terminated, truncated, info = self.base.env.step(action)
                next_state = r1._state_record_full(
                    self.base.env, step + 1, action
                )
                trajectory.append(next_state)
                trace.append(controller_row)
                controller.advance(next_state)
                if terminated:
                    raise RuntimeError(
                        str(info.get("failure_reason", "environment terminated"))
                    )
                if truncated and step + 1 < horizon:
                    raise RuntimeError(
                        "environment truncated before R3 formal horizon"
                    )
            success = bool(
                len(trajectory) == horizon + 1
                and len(trace) == horizon
                and not any(bool(row.get("abnormal")) for row in trajectory)
                and all(bool(row.get("computed_online")) for row in trace)
                and not any(
                    bool(row.get("future_measurement_used")) for row in trace
                )
            )
            result.update(
                {
                    "success": success,
                    "completed": True,
                    "failure_reason": (
                        ""
                        if success
                        else "incomplete hidden-history control rollout"
                    ),
                    "trajectory": trajectory,
                    "controller_trace": trace,
                    "hidden_history_control_summary": {
                        "fresh_controller_actor": True,
                        "fresh_tsc_process": True,
                        "full_tsc_hidden_state_loaded_from_sprsina": True,
                        "controller_history_initialization": (
                            "current_visible_state_only_at_new_task_start"
                        ),
                        "controller_integral_initialization": "zero",
                        "controller_previous_correction_initialization": "zero",
                        "controller_delay_queue_initialization": (
                            "frozen_nominal_prime_policy"
                        ),
                        "hidden_wire_current_available_to_controller": False,
                        "full_wire_current_recorded_after_action_choice": True,
                        "online_action_computation": True,
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
                    failed=failed, reason="stage4_2r3_hidden_history_control"
                )


_CONTROL_RAY_ACTOR = None


def _control_ray_actor_class():
    global _CONTROL_RAY_ACTOR
    if _CONTROL_RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class Stage42R3ControlActor:
            def __init__(self, payload, library, bundle, worker_id, selector_cfg):
                self.worker = LocalHiddenHistoryControlWorker(
                    payload, library, bundle, worker_id, selector_cfg
                )

            def evaluate(self, spec):
                return self.worker.evaluate(spec)

            def close(self):
                self.worker.close()
                return True

        _CONTROL_RAY_ACTOR = Stage42R3ControlActor
    return _CONTROL_RAY_ACTOR


def _evaluate_control(
    ctx: Stage42R3Context,
    specs: Sequence[dict[str, Any]],
    *,
    backend: str,
    resume: bool,
) -> list[dict[str, Any]]:
    raw_dir = ctx.paths.control / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    library, bundle, selector = r1._library_bundle_selector(ctx.r1_ctx)
    pending = [
        spec
        for spec in specs
        if not (
            resume
            and _result_complete(raw_dir / f"{spec['experiment_id']}.json.gz")
        )
    ]
    payloads = {
        spec["experiment_id"]: _control_payload(
            ctx,
            snapshot_dir=Path(spec["restart_snapshot_dir"]),
            snapshot_digest=str(spec["restart_snapshot_manifest_digest"]),
            slew=float(spec["slew_scale"]),
            experiment_id=str(spec["experiment_id"]),
        )
        for spec in specs
    }
    if backend == "serial":
        for index, spec in enumerate(pending):
            worker = LocalHiddenHistoryControlWorker(
                payloads[spec["experiment_id"]],
                library,
                bundle,
                f"stage42r3_control_serial_{index:03d}",
                selector,
            )
            try:
                result = worker.evaluate(spec)
            finally:
                worker.close()
            atomic_write_json_gz(raw_dir / f"{spec['experiment_id']}.json.gz", result)
            print(
                f"[Stage4.2R3 hidden-history-control] {index + 1}/{len(pending)}",
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
            log_prefix="[Stage4.2R3 hidden-history-control]",
        )
        Actor = _control_ray_actor_class()
        actors = []
        refs = {}
        for index, spec in enumerate(pending):
            actor = Actor.remote(
                payloads[spec["experiment_id"]],
                library,
                bundle,
                f"stage42r3_control_{index:03d}",
                selector,
            )
            actors.append(actor)
            refs[actor.evaluate.remote(spec)] = spec
        print(
            "[Stage4.2R3 hidden-history-control] "
            f"actor_count={plan.actor_count} pending={len(pending)}",
            flush=True,
        )
        completed = 0
        try:
            while refs:
                ready, _ = ray.wait(list(refs), num_returns=1, timeout=30.0)
                if not ready:
                    print(
                        f"[Stage4.2R3 hidden-history-control] waiting {completed}/{len(pending)}",
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
                        raw_dir / f"{spec['experiment_id']}.json.gz", result
                    )
                    completed += 1
                    if completed % 10 == 0 or not refs:
                        print(
                            f"[Stage4.2R3 hidden-history-control] {completed}/{len(pending)}",
                            flush=True,
                        )
        finally:
            s2._close_ray_actors(
                actors,
                timeout_s=float(
                    ctx.cfg["storage"].get("actor_close_timeout_s", 1800.0)
                ),
            )
    elif backend not in {"serial", "ray"}:
        raise ValueError("backend must be serial or ray")
    return [
        read_json_gz(raw_dir / f"{spec['experiment_id']}.json.gz") for spec in specs
    ]


def _trace_rows(value: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, item in value.items():
        if "trace" in str(key).lower() and isinstance(item, list):
            rows.extend(dict(row) for row in item if isinstance(row, Mapping))
    return rows


def _trace_is_causal(result: Mapping[str, Any]) -> tuple[bool, int]:
    rows = _trace_rows(result)
    for row in rows:
        if bool(row.get("future_measurement_used", False)):
            return False, len(rows)
        if bool(row.get("future_action_replay_used", False)):
            return False, len(rows)
        issue = row.get("step", row.get("issue_step"))
        measurement = row.get(
            "measurement_max_state_index_used",
            row.get("measurement_reference_step", row.get("reference_step")),
        )
        if issue is not None and measurement is not None:
            if int(measurement) > int(issue):
                return False, len(rows)
    return True, len(rows)


def _selected_state_map(
    selected_pairs: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    output = {}
    for pair in selected_pairs:
        for member in ("plus_first", "minus_first"):
            state = copy.deepcopy(dict(pair[f"{member}_state"]))
            output[str(state["experiment_id"])] = state
    return output


def _control_row(
    ctx: Stage42R3Context,
    result: Mapping[str, Any],
    generated_state: Mapping[str, Any],
) -> dict[str, Any]:
    spec = result["spec"]
    base = {
        "experiment_id": str(result["experiment_id"]),
        "pair_id": str(spec["pair_id"]),
        "history_member": str(spec["history_member"]),
        "state_generation_experiment_id": str(
            spec["state_generation_experiment_id"]
        ),
        "target_id": str(spec["target_id"]),
        "actual_delay_steps": int(spec["action_delay_steps"]),
        "actual_slew_scale": float(spec["slew_scale"]),
        "horizon_steps": int(spec["horizon_steps"]),
        "environment_success": bool(result.get("success")),
        "failure_reason": str(result.get("failure_reason", "")),
    }
    if not bool(result.get("success")):
        return {
            **base,
            "fresh_controller": False,
            "fresh_tsc_process": False,
            "initial_restart_exact": False,
            "controller_trace_causal": False,
            "future_action_replay_used": None,
            "future_measurement_used": None,
            "formal_contract_pass": False,
            "formal_minimum_signed_margin": None,
            "formal_best_arrival_ms": None,
            "failure_class": "runtime_or_environment_error",
            "passed": False,
        }
    trajectory = list(result.get("trajectory") or [])
    horizon = int(spec["horizon_steps"])
    if len(trajectory) != horizon + 1:
        return {
            **base,
            "fresh_controller": True,
            "fresh_tsc_process": True,
            "initial_restart_exact": False,
            "controller_trace_causal": False,
            "future_action_replay_used": False,
            "future_measurement_used": False,
            "formal_contract_pass": False,
            "formal_minimum_signed_margin": None,
            "formal_best_arrival_ms": None,
            "failure_class": "runtime_or_environment_error",
            "failure_reason": "control trajectory length mismatch",
            "passed": False,
        }
    initial = trajectory[0]
    generated_visible = np.asarray(
        [
            generated_state["R"],
            generated_state["Z"],
            generated_state["Ip"],
            *generated_state["coil_currents_a"],
        ],
        dtype=float,
    )
    restart_visible = np.asarray(
        [initial["R"], initial["Z"], initial["Ip"], *initial["currents_a_tsc"]],
        dtype=float,
    )
    generated_wire = np.asarray(generated_state["wire_currents_a"], dtype=float)
    restart_wire = np.asarray(initial.get("wire_currents_a"), dtype=float).reshape(-1)
    initial_visible_exact = bool(np.array_equal(generated_visible, restart_visible))
    initial_wire_exact = bool(
        generated_wire.shape == restart_wire.shape == (N_WIRES,)
        and np.array_equal(generated_wire, restart_wire)
    )
    initial_exact = bool(initial_visible_exact and initial_wire_exact)
    summary = result.get("hidden_history_control_summary") or {}
    fresh_controller = bool(summary.get("fresh_controller_actor"))
    fresh_tsc = bool(summary.get("fresh_tsc_process"))
    future_action = bool(summary.get("future_action_replay_used", True))
    future_measurement = bool(summary.get("future_measurement_used", True))
    causal, trace_count = _trace_is_causal(result)
    forbidden = _forbidden_future_paths(spec)
    causal = bool(causal and not forbidden and not future_action and not future_measurement)
    r13_ctx = r1._r13_ctx(ctx.r1_ctx)
    policy = r1.r13._timing_policy(
        r13_ctx,
        float(spec["slew_scale"]),
        policy_id=(
            f"r42r3_{spec['pair_id']}_{spec['history_member']}_"
            f"{spec['target_id']}_{spec['action_delay_steps']}_{spec['slew_scale']}"
        ),
    )
    formal = r1.r8.tracking_metrics(
        r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx,
        result,
        policy,
    )
    formal_pass = bool(formal["stage3_4_target_tracking_pass"])
    if not initial_exact:
        failure_class = "plant_restart_fidelity_failure"
    elif not causal:
        failure_class = "controller_causality_failure"
    elif not formal_pass:
        failure_class = "real_closed_loop_formal_control_failure"
    else:
        failure_class = ""
    passed = bool(
        fresh_controller
        and fresh_tsc
        and initial_exact
        and causal
        and formal_pass
        and not bool(summary.get("hidden_wire_current_available_to_controller", True))
        and bool(summary.get("online_action_computation"))
    )
    return {
        **base,
        "fresh_controller": fresh_controller,
        "fresh_tsc_process": fresh_tsc,
        "initial_restart_visible_exact": initial_visible_exact,
        "initial_restart_wire_exact": initial_wire_exact,
        "initial_restart_exact": initial_exact,
        "controller_trace_causal": causal,
        "controller_trace_row_count": trace_count,
        "forbidden_future_paths": forbidden,
        "future_action_replay_used": future_action,
        "future_measurement_used": future_measurement,
        "hidden_wire_available_to_controller": bool(
            summary.get("hidden_wire_current_available_to_controller", True)
        ),
        "online_action_computation": bool(
            summary.get("online_action_computation")
        ),
        "formal_contract_pass": formal_pass,
        "formal_minimum_signed_margin": float(
            formal["stage3_4_tracking_minimum_signed_margin"]
        ),
        "formal_best_arrival_ms": int(formal["stage3_4_best_endpoint_ms"]),
        "failure_class": failure_class,
        "passed": passed,
    }


def summarize_control(
    ctx: Stage42R3Context,
    results: Sequence[Mapping[str, Any]],
    selected_pairs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    state_map = _selected_state_map(selected_pairs)
    rows = [
        _control_row(
            ctx,
            result,
            state_map[str(result["spec"]["state_generation_experiment_id"])],
        )
        for result in results
    ]
    group_map: dict[tuple[str, str, int, float], list[dict[str, Any]]] = {}
    for row in rows:
        key = (
            str(row["pair_id"]),
            str(row["target_id"]),
            int(row["actual_delay_steps"]),
            float(row["actual_slew_scale"]),
        )
        group_map.setdefault(key, []).append(row)
    pair_rows = []
    for key in sorted(group_map):
        members = group_map[key]
        member_pass = {
            str(row["history_member"]): bool(row["passed"]) for row in members
        }
        pair_rows.append(
            {
                "pair_id": key[0],
                "target_id": key[1],
                "actual_delay_steps": key[2],
                "actual_slew_scale": key[3],
                "member_count": len(members),
                "plus_first_pass": member_pass.get("plus_first", False),
                "minus_first_pass": member_pass.get("minus_first", False),
                "both_members_pass": bool(
                    len(members) == 2
                    and member_pass.get("plus_first", False)
                    and member_pass.get("minus_first", False)
                ),
                "history_sensitive_outcome": bool(
                    len(members) == 2
                    and member_pass.get("plus_first", False)
                    != member_pass.get("minus_first", False)
                ),
            }
        )
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
    expected = len(selected_pairs) * int(
        ctx.cfg["control_matrix"]["expected_rollouts_per_selected_pair"]
    )
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "authentic_hidden_history_and_initial_state_control",
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
            sum(bool(row["initial_restart_exact"]) for row in rows) / len(rows)
            if rows
            else 0.0
        ),
        "controller_trace_causal_fraction": (
            sum(bool(row["controller_trace_causal"]) for row in rows) / len(rows)
            if rows
            else 0.0
        ),
        "future_action_replay_count": sum(
            bool(row.get("future_action_replay_used")) for row in rows
        ),
        "future_measurement_use_count": sum(
            bool(row.get("future_measurement_used")) for row in rows
        ),
        "hidden_wire_controller_input_count": sum(
            bool(row.get("hidden_wire_available_to_controller")) for row in rows
        ),
        "formal_contract_pass_fraction": (
            sum(bool(row["formal_contract_pass"]) for row in rows) / len(rows)
            if rows
            else 0.0
        ),
        "pair_control_group_count": len(pair_rows),
        "pair_both_members_pass_fraction": (
            sum(bool(row["both_members_pass"]) for row in pair_rows)
            / len(pair_rows)
            if pair_rows
            else 0.0
        ),
        "history_sensitive_outcome_count": sum(
            bool(row["history_sensitive_outcome"]) for row in pair_rows
        ),
        "observer_or_history_identification_failure_count": sum(
            bool(row["history_sensitive_outcome"]) for row in pair_rows
        ),
        "runtime_or_environment_error_count": sum(
            row["failure_class"] == "runtime_or_environment_error" for row in rows
        ),
        "plant_restart_fidelity_failure_count": sum(
            row["failure_class"] == "plant_restart_fidelity_failure" for row in rows
        ),
        "controller_causality_failure_count": sum(
            row["failure_class"] == "controller_causality_failure" for row in rows
        ),
        "real_closed_loop_formal_control_failure_count": sum(
            row["failure_class"] == "real_closed_loop_formal_control_failure"
            for row in rows
        ),
        "minimum_formal_signed_margin": minimum.get(
            "formal_minimum_signed_margin"
        ),
        "minimum_margin_case": (
            {
                "pair_id": minimum.get("pair_id"),
                "history_member": minimum.get("history_member"),
                "target_id": minimum.get("target_id"),
                "actual_delay_steps": minimum.get("actual_delay_steps"),
                "actual_slew_scale": minimum.get("actual_slew_scale"),
            }
            if minimum
            else None
        ),
    }
    summary["passed"] = bool(
        len(rows) == expected
        and expected
        >= int(ctx.cfg["control_matrix"]["minimum_expected_rollouts"])
        and summary["environment_success_count"] == expected
        and summary["fresh_controller_fraction"] == 1.0
        and summary["fresh_tsc_process_fraction"] == 1.0
        and summary["initial_restart_exact_fraction"] == 1.0
        and summary["controller_trace_causal_fraction"] == 1.0
        and summary["future_action_replay_count"] == 0
        and summary["future_measurement_use_count"] == 0
        and summary["hidden_wire_controller_input_count"] == 0
        and summary["formal_contract_pass_fraction"] == 1.0
        and summary["pair_both_members_pass_fraction"] == 1.0
    )
    atomic_write_json(ctx.paths.control / "results.json", rows)
    write_csv(ctx.paths.control / "results.csv", rows)
    atomic_write_json(ctx.paths.control / "pair_results.json", pair_rows)
    write_csv(ctx.paths.control / "pair_results.csv", pair_rows)
    atomic_write_json(ctx.paths.control / "summary.json", summary)
    return summary


def analyze(
    ctx: Stage42R3Context,
    state_summary: Mapping[str, Any],
    control_summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
    state_pass = bool(state_summary.get("passed"))
    control_pass = bool(control_summary and control_summary.get("passed"))
    primary_pass = bool(state_pass and control_pass)
    control_run = control_summary is not None
    if primary_pass:
        verdict_label = (
            "STAGE4_2R3_AUTHENTIC_HIDDEN_HISTORY_AND_INITIAL_STATE_FINITE_ENVELOPE_PASS"
        )
    elif not state_pass:
        verdict_label = "STAGE4_2R3_STATE_GENERATION_OR_PAIR_GATE_INCOMPLETE"
    elif control_run:
        verdict_label = "STAGE4_2R3_AUTHENTIC_HIDDEN_HISTORY_CONTROL_FAILED"
    else:
        verdict_label = "STAGE4_2R3_CONTROL_NOT_RUN"
    verdict = {
        "schema_version": 1,
        "stage": STAGE,
        "verdict": verdict_label,
        "source_stage4_2r2_run": str(ctx.source_r2_run),
        "authentic_state_generation_status": "passed" if state_pass else "failed",
        "hidden_history_control_status": (
            "passed" if control_pass else "failed" if control_run else "not_run"
        ),
        "matched_visible_different_hidden_history_validated": primary_pass,
        "different_initial_state_validated": primary_pass,
        "future_action_replay_used": (
            bool(control_summary.get("future_action_replay_count", 0))
            if control_summary
            else None
        ),
        "hidden_wire_used_as_controller_input": (
            bool(control_summary.get("hidden_wire_controller_input_count", 0))
            if control_summary
            else None
        ),
        "formal_contract_preserved": (
            bool(control_summary.get("formal_contract_pass_fraction") == 1.0)
            if control_summary
            else None
        ),
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
            "Proceed to new preregistered targets, then continuous actuator and "
            "plant/Jacobian variation. Do not start BC, DAgger, or RL."
        ),
        "next_if_fail": (
            "Separate authentic state-generation validity, observer/history "
            "identification, plant restart, causality, and real formal control."
        ),
    }
    summary = {
        **verdict,
        "created_utc": utc_timestamp(),
        "phases": {
            "authentic_state_generation_and_pair_selection": dict(state_summary),
            "authentic_hidden_history_control": (
                None if control_summary is None else dict(control_summary)
            ),
        },
    }
    atomic_write_json(ctx.paths.analysis / "stage4_2r3_verdict.json", verdict)
    atomic_write_json(ctx.paths.analysis / "stage4_2r3_summary.json", summary)
    state = read_json(ctx.paths.state)
    campaign_finished = bool(primary_pass or not state_pass or control_run)
    state.update(
        {
            "finished": campaign_finished,
            "primary_pass": primary_pass,
            "phase_status": (
                "campaign_complete"
                if campaign_finished
                else "state_generation_complete"
            ),
            "stop_reason": (
                ""
                if primary_pass
                else str(state_summary.get("stop_reason", "state_generation_failed"))
                if not state_pass
                else "hidden_history_control_failed"
                if control_run
                else ""
            ),
            "updated_utc": utc_timestamp(),
            "verdict": verdict,
        }
    )
    atomic_write_json(ctx.paths.state, state)
    return summary


def execute(
    ctx: Stage42R3Context,
    *,
    command: str,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    prepare(ctx, resume=resume)
    offline_summary = run_offline_frozen_controller_audit(ctx)
    if not bool(offline_summary.get("passed")):
        raise RuntimeError(
            "Stage4.2R3 offline frozen-controller recomputation gate failed; "
            "no real TSC state generation was started"
        )
    payload = _generation_base_payload(ctx)
    directions = _nullspace_directions(np.asarray(payload["modes_tsc"], dtype=float))
    state_specs = _state_spec_grid(directions, ctx.cfg)
    state_results = _evaluate_state_generation(
        ctx, state_specs, backend=backend, resume=resume
    )
    state_summary = analyze_state_generation(ctx, state_results)
    if command == "state" or not bool(state_summary.get("passed")):
        return analyze(ctx, state_summary, None)
    selected_pairs = read_json(ctx.paths.pair_analysis / "selected_pairs.json")
    control_specs = build_control_specs(ctx, selected_pairs)
    atomic_write_json(ctx.paths.source_reference / "control_specs.json", control_specs)
    control_results = _evaluate_control(
        ctx, control_specs, backend=backend, resume=resume
    )
    control_summary = summarize_control(ctx, control_results, selected_pairs)
    return analyze(ctx, state_summary, control_summary)


def self_test() -> dict[str, Any]:
    modes = np.zeros((N_COILS, N_MODES), dtype=float)
    modes[0, 0] = 1.0
    modes[1, 1] = 1.0
    modes[2, 2] = 1.0
    directions = _nullspace_directions(modes)
    orthogonal = bool(np.max(np.abs(directions @ modes)) <= 1e-12)
    max_normalized = bool(np.max(np.abs(directions)) == 1.0)
    gate = {
        "R_abs_difference_m_max": 0.0005,
        "Z_abs_difference_m_max": 0.0005,
        "Ip_abs_difference_A_max": 2000.0,
        "vR_abs_difference_m_per_s_max": 0.02,
        "vZ_abs_difference_m_per_s_max": 0.02,
        "coil_max_abs_difference_A_max": 2000.0,
        "coil_rms_difference_A_max": 500.0,
        "action_max_abs_difference_max": 1e-12,
        "wire_count": 48,
        "wire_max_abs_difference_A_min": 1000.0,
        "wire_relative_rms_difference_min": 0.05,
    }
    base = {
        "experiment_id": "plus",
        "pair_id": "pair",
        "history_order": "plus_first",
        "nullspace_direction_index": 0,
        "amplitude_fraction": 0.1,
        "settle_steps": 8,
        "horizon_steps": 10,
        "success": True,
        "R": 1.0,
        "Z": 0.0,
        "Ip": 1.0e6,
        "vR_m_per_s": 0.0,
        "vZ_m_per_s": 0.0,
        "coil_currents_a": [0.0] * N_COILS,
        "action_norm_tsc": [0.0] * N_COILS,
        "wire_currents_a": [10000.0] * N_WIRES,
        "wire_rms_a": 10000.0,
        "snapshot_dir": "/synthetic/plus",
        "snapshot_manifest_digest": "plus",
        "snapshot_time_ms": 1200,
    }
    other = copy.deepcopy(base)
    other["experiment_id"] = "minus"
    other["history_order"] = "minus_first"
    other["snapshot_dir"] = "/synthetic/minus"
    other["snapshot_manifest_digest"] = "minus"
    other["wire_currents_a"] = [9000.0] * 24 + [11000.0] * 24
    other["wire_rms_a"] = _rms(np.asarray(other["wire_currents_a"]))
    pair = _pair_metrics(base, other, gate)
    future_rejected = bool(
        _forbidden_future_paths(
            {"controller": {"future_actions": [[0.0] * N_COILS]}}
        )
    )
    return {
        "schema_version": 1,
        "stage": STAGE,
        "nullspace_orthogonal": orthogonal,
        "nullspace_max_normalized": max_normalized,
        "synthetic_pair_visible_match": bool(pair["visible_match_pass"]),
        "synthetic_pair_hidden_separation": bool(pair["hidden_separation_pass"]),
        "synthetic_pair_accepted": bool(pair["accepted"]),
        "future_action_payload_rejected": future_rejected,
        "formal_timing_unchanged": True,
        "bc_dagger_or_rl_allowed": False,
        "passed": bool(
            orthogonal
            and max_normalized
            and pair["accepted"]
            and future_rejected
        ),
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
        description="Stage4.2R3 authentic hidden-history and initial-state validation"
    )
    parser.add_argument("--config", type=Path)
    parser.add_argument("--source-stage4-2r2-run", type=Path)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--command", choices=("all", "state"), default="all")
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
            ("--source-stage4-2r2-run", args.source_stage4_2r2_run),
            ("--run-dir", args.run_dir),
        )
        if value is None
    ]
    if missing:
        parser.error("missing required arguments: " + ", ".join(missing))
    ctx = load_stage42r3_config(
        args.config,
        source_stage42r2_run=args.source_stage4_2r2_run,
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
