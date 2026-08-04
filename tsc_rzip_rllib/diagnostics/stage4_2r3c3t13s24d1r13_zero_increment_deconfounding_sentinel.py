"""Stage4.2R3c3T13S24D1R13 zero-increment deconfounding sentinel."""

from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import time
import traceback
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r11_full_replacement_sequential_transition_identification as d1r11,
)


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S24D1R13"
RUN_NAME = "stage4_2r3c3t13s24d1r13_zero_increment_deconfounding_sentinel"
CAMPAIGN_IDENTITY = "zero_increment_deconfounding_safety_sentinel_v1"
CONTROLLER_REVISION = "zero_increment_after_calibration_v42r3c3t13s24d1r13_v1"
N_COILS = 14
ZERO_START = 10
NON_SEMANTIC_STATE_FIELDS = frozenset({"gotsc_subprocess_s", "step_total_s"})


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _write_json_gz(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True)
class Paths:
    run_dir: Path
    stage_dir: Path
    variants: Path
    specs: Path
    source_reference: Path
    raw: Path
    analysis: Path
    state: Path
    manifest: Path


def _paths(run_dir: Path) -> Paths:
    root = run_dir.expanduser().resolve()
    stage = root / RUN_NAME
    return Paths(
        run_dir=root,
        stage_dir=stage,
        variants=stage / "variants",
        specs=stage / "specs",
        source_reference=stage / "source_reference",
        raw=stage / "raw",
        analysis=stage / "analysis",
        state=stage / "stage_state.json",
        manifest=stage / "stage_manifest.json",
    )


@dataclass(frozen=True)
class Context:
    cfg: dict[str, Any]
    config_path: Path
    source_ctx: Any
    source_d1r11_run: Path
    paths: Paths


def _validate_config(cfg: Mapping[str, Any], path: Path) -> None:
    root = _project_root()
    exact = {
        "schema_version": 1,
        "stage": STAGE,
        "run_name": RUN_NAME,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": "r42r3c3t13s24d1r13_zero_increment_deconfounding_v1",
    }
    for key, value in exact.items():
        if cfg.get(key) != value:
            raise ValueError(f"D1R13 frozen {key} changed")
    for key in ("design_document", "source_d1r11_config"):
        source = (root / str(cfg[key])).resolve()
        if root not in source.parents or not source.is_file():
            raise ValueError(f"D1R13 {key} is outside package")
        if _sha256(source) != str(cfg[f"{key}_sha256"]):
            raise ValueError(f"D1R13 {key} hash changed")
    source = cfg["source_contract"]
    if (
        int(source["d1r11_training_raw_count"]) != 600
        or int(source["d1r11_training_raw_total_bytes"]) != 35_511_922
        or str(source["d1r11_training_raw_inventory_digest"])
        != "8812d9fb0a5cb5a8b8309e17985bd85d180a82bbb0f08c02105fb1a749c7c0e7"
        or str(source["d1r11_execution_code_checkpoint"]) != "027f555"
        or str(source["d1r11_package_checkpoint"]) != "05c8521"
        or str(source["d1r11_final_route"])
        != "FULL_REPLACEMENT_TRANSITION_TRAINING_MODEL_FAIL"
        or int(source["d1r11_calibration_outcome_count"]) != 0
        or int(source["d1r11_holdout_outcome_count"]) != 0
    ):
        raise ValueError("D1R13 source contract changed")
    selected = list(map(str, cfg["selected_source_baseline_experiment_ids"]))
    expected_selected = [
        "s42r3c3_e574ecc025deeddc5117",
        "s42r3c3_55747cb1e2dcccbf3eb7",
        "s42r3c3_6d928c4f7114b0f1344c",
        "s42r3c3_88b51ffa3aede4eabdc1",
        "s42r3c3_79899b70dcebd962c190",
        "s42r3c3_b441b17c5dd5fb4f5140",
        "s42r3c3_7e1a653a8d2ac1c0ba96",
        "s42r3c3_08f34cdaca588ec030cd",
    ]
    if selected != expected_selected or len(set(selected)) != 8:
        raise ValueError("D1R13 selected source identities changed")
    controller = cfg["controller_contract"]
    if (
        int(controller["delegated_last_task_step"]) != 9
        or int(controller["zero_increment_first_task_step"]) != ZERO_START
        or int(controller["zero_action_width"]) != N_COILS
        or int(controller["expected_post_prefix_action_count"]) != 208
        or float(controller["maximum_current_utilization"]) != 0.55
        or not all(
            bool(controller[key])
            for key in (
                "require_exact_zero_action",
                "require_exact_zero_coil_current_increment",
                "require_exact_source_prefix",
                "forbid_future_r17_controller_execution",
            )
        )
    ):
        raise ValueError("D1R13 controller contract changed")
    formal = cfg["formal_timing_contract"]
    if (
        formal["normal"] != {"arrival_deadline_step": 25, "hold_through_step": 35}
        or formal["weak"] != {"arrival_deadline_step": 27, "hold_through_step": 37}
        or float(formal["position_tolerance_m"]) != 0.03
        or float(formal["speed_tolerance_m_per_s"]) != 0.1
        or float(formal["ip_tolerance_A"]) != 10000.0
        or int(formal["arrival_streak_steps"]) != 3
        or bool(formal["arrival_deadline_expansion_allowed"])
    ):
        raise ValueError("D1R13 formal timing changed")
    if int(cfg["parallel"]["n_workers"]) != 8:
        raise ValueError("D1R13 Ray capacity changed")
    if cfg["routes"] != {
        "offline_fail": "ZERO_INCREMENT_DECONFOUNDING_OFFLINE_FAIL_NO_TSC",
        "runtime_fail": "ZERO_INCREMENT_DECONFOUNDING_RUNTIME_OR_PREFIX_FAIL_STOP",
        "finite_fail": "ZERO_INCREMENT_DECONFOUNDING_PLANT_FINITE_FAIL_STABILIZING_SCAFFOLD_REQUIRED",
        "pass": "ZERO_INCREMENT_DECONFOUNDING_SENTINEL_PASS_EXCITATION_SENTINEL_DESIGN_REQUIRED",
    }:
        raise ValueError("D1R13 routes changed")
    if (
        not bool(cfg["identification_only"])
        or not bool(cfg["formal_tracking_diagnostic_only"])
        or bool(cfg["probe_trajectories_allowed_in_expert_dataset"])
        or bool(cfg["bc_dagger_or_rl_allowed"])
    ):
        raise ValueError("D1R13 scope changed")
    expected_path = root / "configs/stage4_2r3c3t13s24d1r13_zero_increment_deconfounding_sentinel_370ms.json"
    if path.resolve() != expected_path.resolve():
        raise ValueError("D1R13 config path changed")


def load_config(
    config_path: Path,
    *,
    source_d1r11_run: Path,
    run_dir: Path,
    source_s21_run: Path,
    source_s23r1_output: Path,
    source_s24_run: Path,
    source_d1r9_v1: Path,
    source_d1r9_v2: Path,
    source_d1r10_run: Path,
    source_d1r10_audit: Path,
    **source_kwargs: Path,
) -> Context:
    config_path = config_path.expanduser().resolve()
    cfg = _read_json(config_path)
    _validate_config(cfg, config_path)
    source_d1r11_run = source_d1r11_run.expanduser().resolve()
    source_cfg = (_project_root() / str(cfg["source_d1r11_config"])).resolve()
    source_ctx = d1r11.load_config(
        source_cfg,
        source_s21_run=source_s21_run,
        source_s23r1_output=source_s23r1_output,
        source_s24_run=source_s24_run,
        source_d1r9_v1=source_d1r9_v1,
        source_d1r9_v2=source_d1r9_v2,
        source_d1r10_run=source_d1r10_run,
        source_d1r10_audit=source_d1r10_audit,
        run_dir=source_d1r11_run,
        **source_kwargs,
    )
    if source_ctx.paths.run_dir != source_d1r11_run:
        raise ValueError("D1R13 source D1R11 run path changed")
    return Context(
        cfg=cfg,
        config_path=config_path,
        source_ctx=source_ctx,
        source_d1r11_run=source_d1r11_run,
        paths=_paths(run_dir),
    )


def _raw_inventory(raw_dir: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    rows = []
    total = 0
    for path in sorted(raw_dir.glob("*.json.gz")):
        size = path.stat().st_size
        sha = _sha256(path)
        total += size
        digest.update(f"{path.name}\0{size}\0{sha}\n".encode())
        rows.append({"name": path.name, "size": size, "sha256": sha})
    return {"count": len(rows), "bytes": total, "digest": digest.hexdigest(), "rows": rows}


def _read_gz(path: Path) -> dict[str, Any]:
    return d1r11.s21.s16.s9.t11.t1.r3c3.read_json_gz(path)


def _source_results(ctx: Context) -> list[dict[str, Any]]:
    selected = list(map(str, ctx.cfg["selected_source_baseline_experiment_ids"]))
    output = []
    for experiment_id in selected:
        path = ctx.source_ctx.paths.raw / f"{experiment_id}.json.gz"
        result = _read_gz(path)
        spec = result.get("spec") or {}
        if (
            not result.get("success")
            or not result.get("completed")
            or result.get("stage") != d1r11.STAGE
            or result.get("campaign_identity") != d1r11.CAMPAIGN_IDENTITY
            or result.get("experiment_id") != experiment_id
            or spec.get("partition") != "training"
            or spec.get("s24_role") != "baseline"
            or int(spec.get("s24_sequence_index", -2)) != -1
        ):
            raise ValueError(f"D1R13 invalid selected D1R11 baseline: {experiment_id}")
        output.append(result)
    return output


def _snapshot_audit(table: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Authenticate exactly the eight selected restart snapshots.

    The S21 helper is intentionally frozen to its 40-context campaign and
    therefore cannot be reused for this eight-context sentinel.
    """
    rows = []
    for context in table:
        directory = Path(str(context["restart_snapshot_dir"])).expanduser().resolve()
        passed, reason = False, ""
        try:
            manifest = _read_json(directory / "restart_snapshot_manifest.json")
            passed = bool(
                str(manifest.get("digest"))
                == str(context["restart_snapshot_manifest_digest"])
                and d1r11.s21.s16.s9.t11.t1.r1._validate_snapshot_inventory(
                    directory, manifest
                )
            )
            if not passed:
                reason = "snapshot inventory mismatch"
        except Exception as exc:
            reason = repr(exc)
        rows.append(
            {
                "pair_id": context["pair_id"],
                "history_member": context["history_member"],
                "state_generation_experiment_id": context[
                    "state_generation_experiment_id"
                ],
                "snapshot_dir": str(directory),
                "passed": passed,
                "failure_reason": reason,
            }
        )
    return {
        "expected": 8,
        "actual": len(rows),
        "pass_count": sum(bool(row["passed"]) for row in rows),
        "passed": len(rows) == 8 and all(bool(row["passed"]) for row in rows),
        "rows": rows,
    }


def _package_fingerprint() -> dict[str, Any]:
    project = _project_root()
    manifest = _read_json(project / "PACKAGE_MANIFEST.json")
    files = [str(path) for path in manifest["file_inventory"]]
    hashes = {path: _sha256(project / path) for path in files}
    required = {
        "configs/stage4_2r3c3t13s24d1r13_zero_increment_deconfounding_sentinel_370ms.json",
        "docs/codex/reports/STAGE4_2R3C3T13S24D1R13_ZERO_INCREMENT_DECONFOUNDING_SENTINEL_DESIGN.md",
        "scripts/stage4_2r3c3t13s24d1r13_zero_increment_deconfounding_sentinel.py",
        "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r13_zero_increment_deconfounding_sentinel.py",
    }
    if not required.issubset(hashes):
        missing = sorted(required.difference(hashes))
        raise ValueError(f"D1R13 package import closure is incomplete: {missing}")
    return {
        "declared_file_count": len(files),
        "hashes": hashes,
        "digest": _digest(hashes),
    }


def build_specs(ctx: Context, source_results: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for source_result in source_results:
        source = source_result["spec"]
        identity = {
            "stage": STAGE,
            "campaign_identity": CAMPAIGN_IDENTITY,
            "controller_revision": CONTROLLER_REVISION,
            "source_d1r11_experiment_id": source_result["experiment_id"],
            "snapshot_manifest_digest": source["restart_snapshot_manifest_digest"],
        }
        experiment_id = d1r11.s21.s16.s9.t11.t1.r3c3._scenario_digest(identity)
        spec = copy.deepcopy(source)
        spec.update(
            {
                "kind": "stage4_2r3c3t13s24d1r13_zero_increment_deconfounding_sentinel",
                "stage": STAGE,
                "campaign_identity": CAMPAIGN_IDENTITY,
                "controller_revision": CONTROLLER_REVISION,
                "experiment_id": experiment_id,
                "phase": "zero_increment_after_authenticated_calibration_prefix",
                "category": "safety_deconfounding_identification_only",
                "environment_variant": f"stage4_2r3c3t13s24d1r13_{experiment_id}",
                "source_d1r11_experiment_id": str(source_result["experiment_id"]),
                "source_d1r11_raw_sha256": _sha256(
                    ctx.source_ctx.paths.raw / f"{source_result['experiment_id']}.json.gz"
                ),
                "source_d1r11_raw_size_bytes": (
                    ctx.source_ctx.paths.raw / f"{source_result['experiment_id']}.json.gz"
                ).stat().st_size,
                "d1r13_zero_increment_first_task_step": ZERO_START,
                "d1r13_future_r17_controller_execution_allowed": False,
                "d1r13_zero_action_required": True,
                "probe_trajectory_allowed_in_expert_dataset": False,
                "pair_or_history_label_available_to_controller": False,
                "partition_label_available_to_controller": False,
                "source_result_available_to_controller": False,
                "source_action_available_to_controller": False,
                "source_coil_current_available_to_controller": False,
                "source_wire_current_available_to_controller": False,
                "hidden_wire_current_available_to_controller": False,
                "future_action_count": 0,
                "future_measurement_count": 0,
                "formal_timing_unchanged": True,
            }
        )
        output.append(spec)
    if len(output) != 8 or len({row["experiment_id"] for row in output}) != 8:
        raise ValueError("D1R13 spec identity coverage changed")
    horizons = {35: 0, 37: 0}
    targets = {"zero": 0, "shifted": 0}
    for spec in output:
        horizons[int(spec["horizon_steps"])] += 1
        key = "zero" if (
            float(spec["target_R_offset_m"]) == 0.0
            and float(spec["target_Z_offset_m"]) == 0.0
            and float(spec["target_Ip_offset_A"]) == 0.0
        ) else "shifted"
        targets[key] += 1
    if horizons != {35: 4, 37: 4} or targets != {"zero": 4, "shifted": 4}:
        raise ValueError("D1R13 matrix coverage changed")
    return output


def _prepare_dirs(paths: Paths) -> None:
    for path in (
        paths.run_dir,
        paths.stage_dir,
        paths.variants,
        paths.specs,
        paths.source_reference,
        paths.raw,
        paths.analysis,
    ):
        path.mkdir(parents=True, exist_ok=True)


def prepare_offline(ctx: Context) -> dict[str, Any]:
    if ctx.paths.stage_dir.exists() or ctx.paths.state.exists() or ctx.paths.manifest.exists():
        raise ValueError("D1R13 offline requires a fresh run identity")
    inventory = _raw_inventory(ctx.source_ctx.paths.raw)
    expected = ctx.cfg["source_contract"]
    if (
        inventory["count"] != int(expected["d1r11_training_raw_count"])
        or inventory["bytes"] != int(expected["d1r11_training_raw_total_bytes"])
        or inventory["digest"] != str(expected["d1r11_training_raw_inventory_digest"])
    ):
        raise ValueError("D1R13 D1R11 training inventory changed")
    source_state = _read_json(ctx.source_ctx.paths.state)
    if (
        source_state.get("phase_status") != "training_model_failed"
        or source_state.get("verdict", {}).get("route")
        != "FULL_REPLACEMENT_TRANSITION_TRAINING_MODEL_FAIL"
        or int(source_state.get("new_raw_count", -1)) != 600
    ):
        raise ValueError("D1R13 D1R11 final state changed")
    source_results = _source_results(ctx)
    specs = build_specs(ctx, source_results)
    snapshot_rows = [
        {
            "pair_id": spec["pair_id"],
            "history_member": spec["history_member"],
            "restart_snapshot_dir": spec["restart_snapshot_dir"],
            "restart_snapshot_manifest_digest": spec["restart_snapshot_manifest_digest"],
            "state_generation_experiment_id": spec["state_generation_experiment_id"],
        }
        for spec in specs
    ]
    snapshots = _snapshot_audit(snapshot_rows)
    if not snapshots.get("passed") or int(snapshots.get("pass_count", -1)) != 8:
        raise ValueError("D1R13 selected snapshot authentication failed")
    package = _package_fingerprint()
    _prepare_dirs(ctx.paths)
    _write_json(ctx.paths.specs / "sentinel_specs.json", specs)
    _write_json(ctx.paths.source_reference / "d1r11_training_inventory.json", inventory)
    _write_json(ctx.paths.source_reference / "selected_snapshot_audit.json", snapshots)
    _write_json(
        ctx.paths.source_reference / "selected_source_raw.json",
        [
            {
                "experiment_id": row["experiment_id"],
                "sha256": spec["source_d1r11_raw_sha256"],
                "size": spec["source_d1r11_raw_size_bytes"],
            }
            for row, spec in zip(source_results, specs)
        ],
    )
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": ctx.cfg["package_revision"],
        "config_path": str(ctx.config_path),
        "config_sha256": _sha256(ctx.config_path),
        "design_document_sha256": ctx.cfg["design_document_sha256"],
        "source_d1r11_run": str(ctx.source_d1r11_run),
        "source_inventory_digest": inventory["digest"],
        "spec_count": len(specs),
        "spec_digest": _digest(specs),
        "snapshot_pass_count": snapshots["pass_count"],
        "package_fingerprint": package,
        "formal_timing_unchanged": True,
        "formal_tracking_diagnostic_only": True,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "bc_dagger_or_rl_allowed": False,
    }
    state = {
        "schema_version": 1,
        "stage": STAGE,
        "phase_status": "offline_ready",
        "finished": False,
        "primary_pass": False,
        "real_tsc_executed": False,
        "new_raw_count": 0,
        "spec_digest": manifest["spec_digest"],
        "package_digest": package["digest"],
        "stop_reason": "",
        "verdict": {},
    }
    _write_json(ctx.paths.manifest, manifest)
    _write_json(ctx.paths.state, state)
    output = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "zero_plant_offline_preflight",
        "source_raw_count": inventory["count"],
        "selected_spec_count": len(specs),
        "snapshot_pass_count": snapshots["pass_count"],
        "expected_post_prefix_action_count": 208,
        "new_raw_count": 0,
        "real_tsc_executed": False,
        "passed": True,
    }
    _write_json(ctx.paths.analysis / "offline_preflight.json", output)
    return output


def zero_increment_action(step: int) -> np.ndarray:
    if int(step) < ZERO_START:
        raise ValueError("D1R13 zero branch called before task step 10")
    return np.zeros(N_COILS, dtype=float)


class ZeroIncrementController(d1r11.SequentialAmplitudeCodedProbeController):
    """Unchanged D1R11 calibration prefix followed by exact zero increments."""

    def action(self, current_state: Mapping[str, Any]) -> tuple[np.ndarray, dict[str, Any]]:
        if int(current_state["step_index"]) != self.step:
            raise ValueError("D1R13 controller/current task-state index mismatch")
        if self.step < ZERO_START:
            action, trace = super().action(current_state)
            trace.update(
                {
                    "r3c3t13s24d1r13_controller_revision": CONTROLLER_REVISION,
                    "r3c3t13s24d1r13_delegated_prefix": True,
                    "r3c3t13s24d1r13_zero_increment": False,
                    "r3c3t13s24d1r13_future_r17_executed": False,
                }
            )
            return np.asarray(action, dtype=float), trace
        action = zero_increment_action(self.step)
        trace = {
            "step": self.step,
            "task_step": self.step,
            "action_norm_tsc": action.tolist(),
            "computed_online": True,
            "solver_success": True,
            "measurement_max_state_index_used": self.step,
            "future_measurement_used": False,
            "hidden_wire_used": False,
            "source_action_used": False,
            "source_coil_current_used": False,
            "source_wire_current_used": False,
            "current_run_future_used": False,
            "pair_or_history_label_used": False,
            "source_result_used": False,
            "future_probe_schedule_available_to_underlying_controller": False,
            "r3c3t13s21_partition_label_used": False,
            "r3c3t13s24_pair_history_partition_label_used": False,
            "r3c3t13s24_delay_slew_target_id_label_used": False,
            "r3c3t13s24_source_or_matched_baseline_used": False,
            "r3c3t13s24_future_measurement_used": False,
            "r3c3t13s24_future_executed_action_used": False,
            "r3c3t13s24_hidden_wire_current_used": False,
            "r3c3t13s24_schedule_available_to_underlying_controller": False,
            "r3c3t13s24_event": "none",
            "r3c3t13s16_lattice_event": "none",
            "r3c3t13s24d1r13_controller_revision": CONTROLLER_REVISION,
            "r3c3t13s24d1r13_delegated_prefix": False,
            "r3c3t13s24d1r13_zero_increment": True,
            "r3c3t13s24d1r13_future_r17_executed": False,
        }
        return action, trace


def _payload(ctx: Context, spec: Mapping[str, Any]) -> dict[str, Any]:
    proxy = SimpleNamespace(
        base_ctx=ctx.source_ctx.base_ctx.base_ctx,
        paths=ctx.paths,
        cfg=ctx.source_ctx.base_ctx.cfg,
    )
    payload = d1r11.s21._payload(proxy, spec)
    experiment_id = str(spec["experiment_id"])
    payload.update(
        {
            "variant_id": f"stage4_2r3c3t13s24d1r13_{experiment_id}",
            "stage4_2r3c3t13s24d1r13_restart_snapshot_dir": str(
                spec["restart_snapshot_dir"]
            ),
            "stage4_2r3c3t13s24d1r13_snapshot_manifest_digest": str(
                spec["restart_snapshot_manifest_digest"]
            ),
            "stage4_2r3c3t13s24d1r13_zero_increment_first_task_step": ZERO_START,
        }
    )
    _write_json(ctx.paths.variants / f"payload_{experiment_id}.json", payload)
    return payload


class LocalWorker:
    """One fresh authentic TSC process and D1R13 controller per rollout."""

    def __init__(
        self,
        payload: dict[str, Any],
        library: dict[str, Any],
        bundle: dict[str, Any],
        worker_id: str,
        selector: dict[str, Any],
        lattice_cfg: dict[str, Any],
        calibration_cfg: dict[str, Any],
        dynamic_cfg: dict[str, Any],
        schedule_cfg: dict[str, Any],
    ):
        self.plant = d1r11.s21.s16.s9.t11.t1.r1.LocalPlantReplayWorker(
            payload, library, bundle, worker_id, selector
        )
        self.base = self.plant.base_worker
        self.bundle = bundle
        self.lattice_cfg = lattice_cfg
        self.calibration_cfg = calibration_cfg
        self.dynamic_cfg = dynamic_cfg
        self.schedule_cfg = schedule_cfg

    def close(self) -> None:
        self.plant.close()

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        failed = True
        trajectory: list[dict[str, Any]] = []
        trace: list[dict[str, Any]] = []
        result: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "campaign_identity": CAMPAIGN_IDENTITY,
            "controller_revision": CONTROLLER_REVISION,
            "underlying_prefix_controller_revision": d1r11.CONTROLLER_REVISION,
            "experiment_id": str(spec["experiment_id"]),
            "spec": copy.deepcopy(spec),
            "success": False,
            "completed": False,
            "failure_reason": "",
            "execution_failure_class": "",
            "trajectory": trajectory,
            "controller_trace": trace,
        }
        try:
            horizon = int(spec["horizon_steps"])
            if (
                horizon != d1r11.s21.s13._formal_horizon(float(spec["slew_scale"]))
                or horizon != int(spec["formal_horizon_steps"])
                or horizon != int(self.base.env.max_episode_steps)
            ):
                raise ValueError("D1R13 formal horizon changed")
            self.base.env.reset()
            zero = np.zeros(N_COILS, dtype=np.float32)
            trajectory.append(
                d1r11.s21.s16.s9.t11.t1.r1._state_record_full(self.base.env, 0, zero)
            )
            controller = ZeroIncrementController(
                self.base,
                self.bundle,
                d1r11.s21.s16.s9._controller_spec(spec),
                trajectory[0],
                self.lattice_cfg,
                self.calibration_cfg,
                self.dynamic_cfg,
                self.schedule_cfg,
            )
            for step in range(horizon):
                action, controller_row = controller.action(trajectory[-1])
                _, _, terminated, truncated, info = self.base.env.step(action)
                next_state = d1r11.s21.s16.s9.t11.t1.r1._state_record_full(
                    self.base.env, step + 1, action
                )
                trajectory.append(next_state)
                trace.append(controller_row)
                controller.advance(next_state)
                if terminated:
                    result["execution_failure_class"] = "plant_abnormal_termination"
                    raise RuntimeError(
                        str(info.get("failure_reason", "environment terminated"))
                    )
                if truncated and step + 1 < horizon:
                    result["execution_failure_class"] = "plant_early_truncation"
                    raise RuntimeError("environment truncated before D1R13 horizon")
            calibration_events = [
                row.get("r3c3t13s16_lattice_event")
                for row in trace[:ZERO_START]
                if row.get("r3c3t13s16_lattice_event") != "none"
            ]
            expected_calibration = [
                "calibration_issue",
                "calibration_cancel",
                "calibration_issue",
                "calibration_cancel",
                "calibration_issue",
                "calibration_cancel",
                "calibration_issue",
                "calibration_cancel",
            ]
            post_actions = np.asarray(
                [row["action_norm_tsc"] for row in trace[ZERO_START:]], dtype=float
            )
            currents = np.asarray(
                [row["currents_a_tsc"] for row in trajectory], dtype=float
            )
            post_current_delta = np.diff(currents[ZERO_START:], axis=0)
            success = bool(
                len(trajectory) == horizon + 1
                and len(trace) == horizon
                and calibration_events == expected_calibration
                and bool(trace[7].get("r3c3t13s21_exact_calibration_net_zero"))
                and all(bool(row.get("r3c3t13s24d1r13_delegated_prefix")) for row in trace[:ZERO_START])
                and all(bool(row.get("r3c3t13s24d1r13_zero_increment")) for row in trace[ZERO_START:])
                and np.array_equal(post_actions, np.zeros_like(post_actions))
                and np.array_equal(post_current_delta, np.zeros_like(post_current_delta))
                and not any(bool(row.get("abnormal")) for row in trajectory)
                and np.all(np.isfinite(currents))
            )
            result.update(
                {
                    "success": success,
                    "completed": True,
                    "failure_reason": "" if success else "incomplete or invalid D1R13 rollout",
                    "execution_failure_class": (
                        "" if success else "controller_or_action_semantics_error"
                    ),
                    "hidden_history_control_summary": {
                        "fresh_controller_actor": True,
                        "fresh_tsc_process": True,
                        "full_tsc_hidden_state_loaded_from_sprsina": True,
                        "prefix_controller_revision": d1r11.CONTROLLER_REVISION,
                        "zero_increment_first_task_step": ZERO_START,
                        "post_prefix_action_count": len(post_actions),
                        "post_prefix_actions_exact_zero": bool(
                            np.array_equal(post_actions, np.zeros_like(post_actions))
                        ),
                        "post_prefix_coil_current_increments_exact_zero": bool(
                            np.array_equal(post_current_delta, np.zeros_like(post_current_delta))
                        ),
                        "future_r17_controller_executed": False,
                        "formal_tracking_diagnostic_only": True,
                        "probe_trajectory_allowed_in_expert_dataset": False,
                        "hidden_wire_current_available_to_controller": False,
                        "full_wire_current_recorded_after_action_choice": True,
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
            return d1r11.s21.s16.s9.t11.t1._json_safe(result)
        except Exception as exc:
            failure_class = str(result.get("execution_failure_class") or "")
            if not failure_class:
                failure_class = "runtime_or_controller_error"
            result.update(
                {
                    "success": False,
                    "completed": True,
                    "failure_reason": repr(exc),
                    "execution_failure_class": failure_class,
                    "trajectory": trajectory,
                    "controller_trace": trace,
                    "traceback": traceback.format_exc(),
                    "wall_time_s": time.time() - started,
                }
            )
            return d1r11.s21.s16.s9.t11.t1._json_safe(result)
        finally:
            runner = getattr(self.base.env, "runner", None)
            if runner is not None:
                runner.cleanup_episode_workspace(
                    failed=failed,
                    reason="stage4_2r3c3t13s24d1r13_zero_increment_deconfounding",
                )


_RAY_ACTOR = None


def _ray_actor_class():
    global _RAY_ACTOR
    if _RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class Stage42R3C3T13S24D1R13Actor:
            def __init__(self, payload, library, bundle, worker_id, selector, lattice, calibration, dynamic, schedule):
                self.worker = LocalWorker(
                    payload,
                    library,
                    bundle,
                    worker_id,
                    selector,
                    lattice,
                    calibration,
                    dynamic,
                    schedule,
                )

            def evaluate(self, spec):
                return self.worker.evaluate(spec)

            def close(self):
                self.worker.close()
                return True

        _RAY_ACTOR = Stage42R3C3T13S24D1R13Actor
    return _RAY_ACTOR


def _saved_specs(ctx: Context) -> list[dict[str, Any]]:
    saved = _read_json(ctx.paths.specs / "sentinel_specs.json")
    rebuilt = build_specs(ctx, _source_results(ctx))
    if _digest(saved) != _digest(rebuilt):
        raise ValueError("D1R13 frozen specs changed")
    return saved


def _result_complete(path: Path, spec: Mapping[str, Any], *, require_success: bool) -> bool:
    if not path.is_file():
        return False
    try:
        result = _read_gz(path)
        horizon = int(spec["horizon_steps"])
        return bool(
            result.get("completed")
            and (result.get("success") or not require_success)
            and result.get("stage") == STAGE
            and result.get("campaign_identity") == CAMPAIGN_IDENTITY
            and result.get("controller_revision") == CONTROLLER_REVISION
            and result.get("experiment_id") == spec["experiment_id"]
            and result.get("spec") == dict(spec)
            and len(result.get("trajectory") or []) <= horizon + 1
            and len(result.get("controller_trace") or []) <= horizon
        )
    except Exception:
        return False


def evaluate_specs(ctx: Context, specs: Sequence[dict[str, Any]], *, backend: str, resume: bool) -> dict[str, Any]:
    ctx.paths.raw.mkdir(parents=True, exist_ok=True)
    pending = [
        spec
        for spec in specs
        if not (
            resume
            and _result_complete(
                ctx.paths.raw / f"{spec['experiment_id']}.json.gz",
                spec,
                require_success=True,
            )
        )
    ]
    payloads = {str(spec["experiment_id"]): _payload(ctx, spec) for spec in specs}
    library, bundle, selector = d1r11._library_bundle_selector(ctx.source_ctx)
    lattice = ctx.source_ctx.base_ctx.base_ctx.cfg["lattice_probe"]
    calibration = ctx.source_ctx.base_ctx.base_ctx.cfg["active_calibration"]
    dynamic = ctx.source_ctx.base_ctx.cfg["causal_model"]
    schedule = ctx.source_ctx.cfg["schedule_contract"]
    if backend == "serial":
        for index, spec in enumerate(pending):
            worker = LocalWorker(
                payloads[str(spec["experiment_id"])],
                library,
                bundle,
                f"stage42r3c3t13s24d1r13_serial_{index:04d}",
                selector,
                lattice,
                calibration,
                dynamic,
                schedule,
            )
            try:
                result = worker.evaluate(spec)
            finally:
                worker.close()
            _write_json_gz(ctx.paths.raw / f"{spec['experiment_id']}.json.gz", result)
            print(f"[D1R13] {index + 1}/{len(pending)}", flush=True)
    elif backend == "ray" and pending:
        import ray

        plan = d1r11.s21.s16.ensure_ray_worker_plan(
            ray,
            requested_workers=int(ctx.cfg["parallel"]["n_workers"]),
            pending_tasks=len(pending),
            ray_tmpdir=os.environ.get("RAY_TMPDIR") or ctx.cfg["storage"]["ray_tmpdir"],
            log_prefix="[D1R13]",
        )
        Actor = _ray_actor_class()
        completed = 0
        for batch_start in range(0, len(pending), plan.actor_count):
            batch = pending[batch_start : batch_start + plan.actor_count]
            actors, refs = [], {}
            for offset, spec in enumerate(batch):
                actor = Actor.remote(
                    payloads[str(spec["experiment_id"])],
                    library,
                    bundle,
                    f"stage42r3c3t13s24d1r13_{batch_start + offset:04d}",
                    selector,
                    lattice,
                    calibration,
                    dynamic,
                    schedule,
                )
                actors.append(actor)
                refs[actor.evaluate.remote(spec)] = spec
            try:
                while refs:
                    ready, _ = ray.wait(list(refs), num_returns=1, timeout=30.0)
                    if not ready:
                        print(f"[D1R13] waiting {completed}/{len(pending)}", flush=True)
                        continue
                    for ref in ready:
                        spec = refs.pop(ref)
                        try:
                            result = ray.get(ref)
                        except Exception as exc:
                            result = {
                                "schema_version": 1,
                                "stage": STAGE,
                                "campaign_identity": CAMPAIGN_IDENTITY,
                                "controller_revision": CONTROLLER_REVISION,
                                "experiment_id": str(spec["experiment_id"]),
                                "spec": copy.deepcopy(spec),
                                "success": False,
                                "completed": True,
                                "failure_reason": repr(exc),
                                "execution_failure_class": "ray_actor_runtime_error",
                                "traceback": traceback.format_exc(),
                                "trajectory": [],
                                "controller_trace": [],
                            }
                        _write_json_gz(
                            ctx.paths.raw / f"{spec['experiment_id']}.json.gz", result
                        )
                        completed += 1
                        print(f"[D1R13] {completed}/{len(pending)}", flush=True)
            finally:
                close_refs = [actor.close.remote() for actor in actors]
                if close_refs:
                    ray.get(
                        close_refs,
                        timeout=float(ctx.cfg["storage"]["actor_close_timeout_s"]),
                    )
                for actor in actors:
                    ray.kill(actor, no_restart=True)
    elif backend not in {"serial", "ray"}:
        raise ValueError(f"unsupported D1R13 backend: {backend}")
    completed = sum(
        _result_complete(
            ctx.paths.raw / f"{spec['experiment_id']}.json.gz",
            spec,
            require_success=False,
        )
        for spec in specs
    )
    successful = sum(
        _result_complete(
            ctx.paths.raw / f"{spec['experiment_id']}.json.gz",
            spec,
            require_success=True,
        )
        for spec in specs
    )
    return {
        "expected": len(specs),
        "pending_at_start": len(pending),
        "completed": completed,
        "successful": successful,
        "passed": completed == len(specs) and successful == len(specs),
    }


def _semantic_state(row: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key not in NON_SEMANTIC_STATE_FIELDS}


def _source_trace_projection(source: Mapping[str, Any], current: Mapping[str, Any]) -> bool:
    return all(current.get(key) == value for key, value in source.items())


FORBIDDEN_TRACE_KEYS = (
    "future_measurement_used",
    "hidden_wire_used",
    "source_action_used",
    "source_coil_current_used",
    "source_wire_current_used",
    "current_run_future_used",
    "pair_or_history_label_used",
    "source_result_used",
    "future_probe_schedule_available_to_underlying_controller",
    "r3c3t13s21_partition_label_used",
    "r3c3t13s24_pair_history_partition_label_used",
    "r3c3t13s24_delay_slew_target_id_label_used",
    "r3c3t13s24_source_or_matched_baseline_used",
    "r3c3t13s24_future_measurement_used",
    "r3c3t13s24_future_executed_action_used",
    "r3c3t13s24_hidden_wire_current_used",
    "r3c3t13s24_schedule_available_to_underlying_controller",
    "r3c3t13s24d1r13_future_r17_executed",
)


def postprocess(ctx: Context) -> dict[str, Any]:
    specs = _saved_specs(ctx)
    source_by_id = {row["experiment_id"]: row for row in _source_results(ctx)}
    evaluators, _ = d1r11._formal_callback(ctx.source_ctx, specs)
    rows = []
    expected_post = 0
    for spec in specs:
        path = ctx.paths.raw / f"{spec['experiment_id']}.json.gz"
        if not _result_complete(path, spec, require_success=False):
            rows.append(
                {
                    "experiment_id": spec["experiment_id"],
                    "failure_class": "runtime_or_raw_error",
                    "passed": False,
                }
            )
            continue
        result = _read_gz(path)
        source = source_by_id[str(spec["source_d1r11_experiment_id"])]
        trajectory = result.get("trajectory") or []
        trace = result.get("controller_trace") or []
        horizon = int(spec["horizon_steps"])
        expected_post += horizon - ZERO_START
        full_horizon = len(trajectory) == horizon + 1 and len(trace) == horizon
        prefix_state = bool(
            len(trajectory) >= ZERO_START + 1
            and all(
                _semantic_state(current) == _semantic_state(reference)
                for current, reference in zip(
                    trajectory[: ZERO_START + 1], source["trajectory"][: ZERO_START + 1]
                )
            )
        )
        prefix_trace = bool(
            len(trace) >= ZERO_START
            and all(
                _source_trace_projection(reference, current)
                for current, reference in zip(trace[:ZERO_START], source["controller_trace"][:ZERO_START])
            )
        )
        post_actions = np.asarray(
            [row.get("action_norm_tsc", []) for row in trace[ZERO_START:]], dtype=float
        )
        currents = np.asarray(
            [row.get("currents_a_tsc", []) for row in trajectory], dtype=float
        )
        wire_currents = [
            np.asarray(row.get("wire_currents_a", []), dtype=float)
            for row in trajectory
        ]
        post_current_delta = (
            np.diff(currents[ZERO_START:], axis=0)
            if currents.shape == (horizon + 1, N_COILS)
            else np.asarray([math.nan])
        )
        zero_actions = bool(
            post_actions.shape == (horizon - ZERO_START, N_COILS)
            and np.array_equal(post_actions, np.zeros_like(post_actions))
        )
        zero_currents = bool(
            post_current_delta.shape == (horizon - ZERO_START, N_COILS)
            and np.array_equal(post_current_delta, np.zeros_like(post_current_delta))
        )
        forbidden = sum(
            any(bool(row.get(key)) for key in FORBIDDEN_TRACE_KEYS) for row in trace
        )
        finite = bool(
            full_horizon
            and np.all(np.isfinite(currents))
            and all(values.size > 0 and np.all(np.isfinite(values)) for values in wire_currents)
            and all(
                math.isfinite(float(state[key]))
                for state in trajectory
                for key in ("R", "Z", "Ip")
            )
            and not any(bool(state.get("abnormal")) for state in trajectory)
        )
        payload = _payload(ctx, spec)
        minimum, maximum = d1r11.s21.s13._current_limits_tsc(payload)
        center, half = 0.5 * (minimum + maximum), 0.5 * (maximum - minimum)
        utilization = (
            float(np.max(np.abs((currents - center) / half)))
            if currents.shape == (horizon + 1, N_COILS)
            else math.inf
        )
        formal = evaluators[str(spec["experiment_id"])].evaluate(
            np.asarray([[row["R"], row["Z"], row["Ip"]] for row in trajectory], dtype=float)
        ) if full_horizon else {"formal_contract_pass": False}
        calibration_events = [
            row.get("r3c3t13s16_lattice_event")
            for row in trace[:ZERO_START]
            if row.get("r3c3t13s16_lattice_event") != "none"
        ]
        calibration = calibration_events == [
            "calibration_issue",
            "calibration_cancel",
            "calibration_issue",
            "calibration_cancel",
            "calibration_issue",
            "calibration_cancel",
            "calibration_issue",
            "calibration_cancel",
        ]
        passed = bool(
            result.get("success")
            and full_horizon
            and prefix_state
            and prefix_trace
            and calibration
            and zero_actions
            and zero_currents
            and finite
            and forbidden == 0
            and utilization <= float(ctx.cfg["controller_contract"]["maximum_current_utilization"]) + 1e-12
        )
        rows.append(
            {
                "experiment_id": spec["experiment_id"],
                "source_d1r11_experiment_id": spec["source_d1r11_experiment_id"],
                "pair_id": spec["pair_id"],
                "history_member": spec["history_member"],
                "horizon": horizon,
                "runtime_success": bool(result.get("success")),
                "execution_failure_class": str(
                    result.get("execution_failure_class") or ""
                ),
                "full_horizon": full_horizon,
                "source_prefix_state_exact": prefix_state,
                "source_prefix_trace_exact": prefix_trace,
                "calibration_exact": calibration,
                "post_prefix_action_count": len(trace[ZERO_START:]),
                "post_prefix_actions_exact_zero": zero_actions,
                "post_prefix_current_increments_exact_zero": zero_currents,
                "finite": finite,
                "forbidden_trace_count": forbidden,
                "maximum_current_utilization": utilization,
                "formal_contract_pass_diagnostic_only": bool(formal.get("formal_contract_pass")),
                "failure_reason": result.get("failure_reason", ""),
                "passed": passed,
            }
        )
    actual_inventory = _raw_inventory(ctx.paths.raw)
    pass_count = sum(bool(row["passed"]) for row in rows)
    formal_count = sum(bool(row.get("formal_contract_pass_diagnostic_only")) for row in rows)
    finite_count = sum(bool(row.get("finite")) for row in rows)
    plant_failure_count = sum(
        str(row.get("execution_failure_class", "")).startswith("plant_")
        for row in rows
    )
    runtime_error_count = sum(
        bool(row.get("execution_failure_class"))
        and not str(row.get("execution_failure_class", "")).startswith("plant_")
        for row in rows
    )
    passed = bool(
        len(rows) == 8
        and pass_count == 8
        and expected_post == int(ctx.cfg["controller_contract"]["expected_post_prefix_action_count"])
        and actual_inventory["count"] == 8
    )
    if passed:
        route = ctx.cfg["routes"]["pass"]
    elif finite_count < 8 and plant_failure_count > 0 and runtime_error_count == 0:
        route = ctx.cfg["routes"]["finite_fail"]
    else:
        route = ctx.cfg["routes"]["runtime_fail"]
    output = {
        "schema_version": 1,
        "stage": STAGE,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "controller_revision": CONTROLLER_REVISION,
        "expected_task_count": 8,
        "actual_row_count": len(rows),
        "pass_count": pass_count,
        "finite_count": finite_count,
        "plant_failure_count": plant_failure_count,
        "runtime_error_count": runtime_error_count,
        "expected_post_prefix_action_count": 208,
        "actual_post_prefix_action_count": sum(int(row.get("post_prefix_action_count", 0)) for row in rows),
        "zero_action_row_count": sum(bool(row.get("post_prefix_actions_exact_zero")) for row in rows),
        "zero_current_increment_row_count": sum(bool(row.get("post_prefix_current_increments_exact_zero")) for row in rows),
        "source_prefix_state_exact_count": sum(bool(row.get("source_prefix_state_exact")) for row in rows),
        "source_prefix_trace_exact_count": sum(bool(row.get("source_prefix_trace_exact")) for row in rows),
        "formal_tracking_pass_count_diagnostic_only": formal_count,
        "maximum_current_utilization": max((float(row.get("maximum_current_utilization", 0.0)) for row in rows), default=0.0),
        "raw_inventory": actual_inventory,
        "rows": rows,
        "route": route,
        "passed": passed,
        "scientific_scope": {
            "formal_tracking_diagnostic_only": True,
            "transition_model_validated": False,
            "mpc_validated": False,
            "long_hold_validated": False,
            "expert_data_allowed": False,
            "bc_dagger_or_rl_allowed": False,
        },
    }
    _write_json(ctx.paths.analysis / "final_result.json", output)
    _write_json(ctx.paths.run_dir / "final_result.json", output)
    state = _read_json(ctx.paths.state)
    state.update(
        {
            "phase_status": "complete" if passed else "failed",
            "finished": True,
            "primary_pass": passed,
            "real_tsc_executed": True,
            "new_raw_count": actual_inventory["count"],
            "stop_reason": "" if passed else route,
            "verdict": {"route": route, "passed": passed},
        }
    )
    _write_json(ctx.paths.state, state)
    return output


def run_real(ctx: Context, *, backend: str, resume: bool) -> dict[str, Any]:
    state = _read_json(ctx.paths.state)
    if state.get("phase_status") != "offline_ready" or bool(state.get("finished")):
        raise ValueError("D1R13 run requires offline_ready state")
    specs = _saved_specs(ctx)
    execution = evaluate_specs(ctx, specs, backend=backend, resume=resume)
    state.update(
        {
            "phase_status": "real_complete",
            "real_tsc_executed": True,
            "new_raw_count": len(list(ctx.paths.raw.glob("*.json.gz"))),
        }
    )
    _write_json(ctx.paths.state, state)
    _write_json(ctx.paths.analysis / "execution.json", execution)
    return execution


def execute(ctx: Context, *, command: str, backend: str, resume: bool) -> dict[str, Any]:
    if command == "offline":
        if resume:
            raise ValueError("D1R13 offline does not support resume")
        return prepare_offline(ctx)
    if command == "run":
        return run_real(ctx, backend=backend, resume=resume)
    if command == "postprocess":
        state = _read_json(ctx.paths.state)
        if state.get("phase_status") != "real_complete" or bool(state.get("finished")):
            raise ValueError("D1R13 postprocess requires real_complete state")
        return postprocess(ctx)
    raise ValueError(f"unsupported D1R13 command: {command}")


def self_test(config_path: Path) -> dict[str, Any]:
    config_path = config_path.expanduser().resolve()
    cfg = _read_json(config_path)
    _validate_config(cfg, config_path)
    action = zero_increment_action(ZERO_START)
    return {
        "stage": STAGE,
        "selected_source_count": len(cfg["selected_source_baseline_experiment_ids"]),
        "zero_start": ZERO_START,
        "zero_action_width": len(action),
        "zero_action_exact": bool(np.array_equal(action, np.zeros(N_COILS))),
        "expected_post_prefix_action_count": cfg["controller_contract"]["expected_post_prefix_action_count"],
        "real_tsc_executed": False,
        "passed": True,
    }


def _source_kwargs(args: argparse.Namespace) -> dict[str, Path]:
    return d1r11._source_kwargs(args)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source-d1r11-run", type=Path, required=True)
    parser.add_argument("--source-s21-run", type=Path, required=True)
    parser.add_argument("--source-s23r1-output", type=Path, required=True)
    parser.add_argument("--source-s24-run", type=Path, required=True)
    parser.add_argument("--source-d1r9-v1", type=Path, required=True)
    parser.add_argument("--source-d1r9-v2", type=Path, required=True)
    parser.add_argument("--source-d1r10-run", type=Path, required=True)
    parser.add_argument("--source-d1r10-audit", type=Path, required=True)
    parser.add_argument("--source-stage42r3b-run", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3-run", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3-bank-dir", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3t1-run", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3t1-audit-dir", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3t3-controller-bank", type=Path, required=True)
    parser.add_argument("--q1-run", type=Path, required=True)
    parser.add_argument("--q2-run", type=Path, required=True)
    parser.add_argument("--q1-audit", type=Path, required=True)
    parser.add_argument("--q2-audit", type=Path, required=True)
    parser.add_argument("--r3b-server-audit", type=Path, required=True)
    parser.add_argument("--r3b-snapshot-checks", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--command", choices=("offline", "run", "postprocess"), required=True)
    parser.add_argument("--backend", choices=("serial", "ray"), default="ray")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(args.config), sort_keys=True, indent=2))
        return
    ctx = load_config(
        args.config,
        source_d1r11_run=args.source_d1r11_run,
        run_dir=args.run_dir,
        source_s21_run=args.source_s21_run,
        source_s23r1_output=args.source_s23r1_output,
        source_s24_run=args.source_s24_run,
        source_d1r9_v1=args.source_d1r9_v1,
        source_d1r9_v2=args.source_d1r9_v2,
        source_d1r10_run=args.source_d1r10_run,
        source_d1r10_audit=args.source_d1r10_audit,
        **_source_kwargs(args),
    )
    result = execute(ctx, command=args.command, backend=args.backend, resume=args.resume)
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
