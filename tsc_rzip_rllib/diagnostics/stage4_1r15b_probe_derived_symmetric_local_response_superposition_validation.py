"""Stage4.1R15B probe-derived symmetric local-response validation.

R15 completed all 32 preregistered bounded probes without a runtime failure.  The
source-bank PCA/ridge model passed 31/32 probes, but it underpredicted the final
speed response of the positive RZ_p10_m10, delay-1, late-mode-0 probe by
8.350 mm/s, just above the preregistered 8 mm/s limit.  The plus/minus probe
pairs were nevertheless strongly centrally symmetric.  This stage therefore
uses the experimentally measured odd (central-difference) response of the four
R15 basis probes as a bounded local response model, and validates *superposition*
with a new orthogonal Hadamard combination bank.

This is identification-only.  It does not select a controller or claim closure
of the immutable 250/350 and 270/370 ms timing contracts.
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
from typing import Any, Mapping, Sequence

import numpy as np

from . import stage2_trajectory_optimization as s2
from . import stage4_1r13_original_deadline_delay_pipeline_early_braking as r13
from . import stage4_1r14_original_deadline_integrated_target_conditioned_deadline_mpc as r14
from . import stage4_1r15_bounded_early_braking_local_response_identification as r15
from tsc_rzip_rllib.utils.ray_runtime import ensure_ray_worker_plan

atomic_write_json = r15.atomic_write_json
atomic_write_json_gz = r15.atomic_write_json_gz
read_json = r15.read_json
read_json_gz = r15.read_json_gz
utc_timestamp = r15.utc_timestamp
write_csv = r15.write_csv

SCHEMA_VERSION = 1
STAGE = "Stage4.1R15B"
CONTROLLER_REVISION = "probe_derived_symmetric_local_response_superposition_v15b"
PACKAGE_REVISION = "r15b_hadamard_superposition_validation_v1"
EXPECTED_SOURCE_REVISION = r15.CONTROLLER_REVISION
EXPECTED_SOURCE_PACKAGE_REVISION = r15.PACKAGE_REVISION
N_MODES = 3
BASIS_ORDER = ("early_mode0", "early_mode1", "late_mode0", "late_mode1")
SOURCE_FAILURE_KEY = ("RZ_p10_m10", 1, "late_mode0", 1)


def _json_safe(value: Any) -> Any:
    return r15._json_safe(value)


def _as_float(value: Any, default: float = 0.0) -> float:
    return r15._as_float(value, default)


def _sha256_file(path: Path) -> str:
    return r15._sha256_file(path)


def _result_complete(path: Path) -> bool:
    return r15._result_complete(path)


def _scenario_digest(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        _json_safe(dict(payload)), sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return "s41r15b_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]


@dataclass(frozen=True)
class Stage41R15BPaths:
    run_dir: Path
    source_reference: Path
    source_audit: Path
    response_model: Path
    composition_validation: Path
    analysis: Path
    variants: Path
    state: Path
    manifest: Path

    @classmethod
    def from_run_dir(cls, run_dir: Path) -> "Stage41R15BPaths":
        run_dir = run_dir.expanduser().resolve()
        return cls(
            run_dir=run_dir,
            source_reference=run_dir / "stage4_1r15b_source_reference",
            source_audit=run_dir / "stage4_1r15b_source_audit",
            response_model=run_dir / "stage4_1r15b_probe_derived_response_model",
            composition_validation=run_dir / "stage4_1r15b_superposition_validation",
            analysis=run_dir / "stage4_1r15b_analysis",
            variants=run_dir / "stage4_1r15b_environment_variants",
            state=run_dir / "stage4_1r15b_state.json",
            manifest=run_dir / "stage4_1r15b_manifest.json",
        )


@dataclass
class Stage41R15BContext:
    cfg: dict[str, Any]
    paths: Stage41R15BPaths
    project_dir: Path
    source_stage41r15_run: Path
    source_stage41r14_run: Path
    source_stage41r13_run: Path
    source_manifest: dict[str, Any]
    source_state: dict[str, Any]
    source_cfg: dict[str, Any]
    source_verdict: dict[str, Any]
    r15_ctx: r15.Stage41R15Context
    source_fingerprint: dict[str, Any]


SOURCE_INVENTORY_CONTRACT = "r15b_direct_stage4_1r15_source_v1"


def _required_source_files(source: Path) -> list[Path]:
    required = [
        source / "stage4_1r15_manifest.json",
        source / "stage4_1r15_state.json",
        source / "stage4_1r15_config.resolved.json",
        source / "stage4_1r15_analysis" / "stage4_1r15_verdict.json",
        source / "stage4_1r15_analysis" / "stage4_1r15_summary.json",
        source / "stage4_1r15_source_audit" / "summary.json",
        source / "stage4_1r15_local_response_model" / "models.json",
        source / "stage4_1r15_local_response_model" / "summary.json",
        source / "stage4_1r15_local_response_model" / "cross_validation.csv",
        source / "stage4_1r15_bounded_probe_validation" / "summary.json",
        source / "stage4_1r15_bounded_probe_validation" / "results.json",
        source / "stage4_1r15_bounded_probe_validation" / "results.csv",
        source / "stage4_1r15_bounded_probe_validation" / "central_symmetry.csv",
    ]
    required.extend(
        sorted((source / "stage4_1r15_bounded_probe_validation" / "raw").glob("*.json.gz"))
    )
    return required


def _source_inventory(source: Path) -> dict[str, Any]:
    source = source.expanduser().resolve()
    rows: list[dict[str, Any]] = []
    total = 0
    for path in _required_source_files(source):
        if not path.is_file():
            raise FileNotFoundError(f"required Stage4.1R15 source file missing: {path}")
        size = path.stat().st_size
        total += size
        rows.append(
            {
                "relative_path": path.relative_to(source).as_posix(),
                "size_bytes": size,
                "sha256": _sha256_file(path),
            }
        )
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "schema_version": 1,
        "source_stage": "Stage4.1R15",
        "inventory_contract": SOURCE_INVENTORY_CONTRACT,
        "n_files": len(rows),
        "total_bytes": total,
        "digest": hashlib.sha256(canonical).hexdigest(),
        "files": rows,
    }


def validate_config(cfg: Mapping[str, Any]) -> None:
    if cfg.get("controller_revision") != CONTROLLER_REVISION:
        raise ValueError("R15B controller revision mismatch")
    timing = cfg["formal_timing_contract"]
    if not bool(timing.get("immutable")):
        raise ValueError("R15B formal timing must remain immutable")
    if int(timing["normal_slew"]["arrival_deadline_step"]) != 25 or int(
        timing["normal_slew"]["hold_through_step"]
    ) != 35:
        raise ValueError("R15B normal timing must remain 250/350 ms")
    if int(timing["weak_slew"]["arrival_deadline_step"]) != 27 or int(
        timing["weak_slew"]["hold_through_step"]
    ) != 37:
        raise ValueError("R15B weak timing must remain 270/370 ms")
    source = cfg["source_requirements"]
    if int(source["require_r15_raw_count"]) != 32:
        raise ValueError("R15B requires exactly 32 R15 probe raw files")
    model = cfg["probe_derived_response_model"]
    if list(model["basis_order"]) != list(BASIS_ORDER):
        raise ValueError("R15B basis order is immutable")
    combos = cfg["superposition_validation"]["hadamard_combinations"]
    matrix = np.asarray([row["coefficients"] for row in combos], dtype=float)
    if matrix.shape != (4, 4):
        raise ValueError("R15B requires a 4x4 Hadamard combination matrix")
    scale = float(cfg["superposition_validation"]["combination_scale"])
    expected = np.asarray(
        [[1, 1, 1, 1], [1, -1, 1, -1], [1, 1, -1, -1], [1, -1, -1, 1]],
        dtype=float,
    )
    if not np.array_equal(matrix, expected):
        raise ValueError("R15B Hadamard combinations changed")
    if not math.isclose(scale, 0.5, abs_tol=1e-15):
        raise ValueError("R15B combination scale must remain 0.5")
    if not np.allclose(matrix @ matrix.T, 4.0 * np.eye(4), atol=1e-12, rtol=0.0):
        raise ValueError("R15B combinations are not orthogonal")
    probe = cfg["superposition_validation"]
    if int(probe["expected_rollouts"]) != 32:
        raise ValueError("R15B expected rollout count must remain 32")
    if sorted(int(v) for v in probe["probe_signs"]) != [-1, 1]:
        raise ValueError("R15B requires plus/minus combination probes")
    if float(probe["maximum_requested_probe_component"]) > 0.015 + 1e-15:
        raise ValueError("R15B may not exceed the R15 probe amplitude")
    if not bool(cfg.get("identification_only")):
        raise ValueError("R15B must remain identification-only")
    if not bool(cfg.get("stage4_2r1_was_not_run_or_reused")):
        raise ValueError("R15B may not reuse Stage4.2R1")


def _validate_source_stage41r15(
    source: Path, cfg: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    source = source.expanduser().resolve()
    manifest = read_json(source / "stage4_1r15_manifest.json")
    state = read_json(source / "stage4_1r15_state.json")
    source_cfg = read_json(source / "stage4_1r15_config.resolved.json")
    verdict = read_json(source / "stage4_1r15_analysis" / "stage4_1r15_verdict.json")
    req = cfg["source_requirements"]
    checks = {
        "stage": manifest.get("stage") == "Stage4.1R15",
        "controller_revision": manifest.get("controller_revision") == EXPECTED_SOURCE_REVISION,
        "package_revision": manifest.get("package_revision") == EXPECTED_SOURCE_PACKAGE_REVISION,
        "finished": bool(state.get("finished")),
        "stop_reason": state.get("stop_reason") == "bounded_probe_model_validation_failed",
        "source_audit_passed": verdict.get("source_audit_status") == "passed",
        "local_model_passed": verdict.get("local_model_status") == "passed",
        "probe_validation_failed": verdict.get("bounded_probe_validation_status") == "failed",
        "identification_only": bool(verdict.get("identification_only")),
        "formal_timing_not_restored": not bool(verdict.get("formal_timing_contract_restored")),
        "stage4_2r1_not_reused": bool(verdict.get("stage4_2r1_was_not_run_or_reused")),
    }
    if not all(checks.values()):
        raise ValueError(f"R15B source R15 validation failed: {checks}")
    raw = sorted((source / "stage4_1r15_bounded_probe_validation" / "raw").glob("*.json.gz"))
    if len(raw) != int(req["require_r15_raw_count"]):
        raise ValueError(f"R15B expected 32 R15 raw files, found {len(raw)}")
    return manifest, state, source_cfg, verdict


def _resolve_recorded_run(project_dir: Path, recorded: str, root_name: str) -> Path:
    return r15._resolve_recorded_run(project_dir, recorded, root_name)


def load_stage41r15b_config(
    config_path: Path,
    *,
    source_stage41r15_run: Path,
    run_dir_override: Path | None = None,
) -> Stage41R15BContext:
    config_path = config_path.expanduser().resolve()
    cfg = read_json(config_path)
    validate_config(cfg)
    project_dir = config_path.parents[1]
    source_stage41r15_run = source_stage41r15_run.expanduser().resolve()
    manifest, state, source_cfg, verdict = _validate_source_stage41r15(
        source_stage41r15_run, cfg
    )
    source_stage41r14_run = _resolve_recorded_run(
        project_dir, str(manifest["source_stage4_1r14_run"]), "stage4_1r14_runs"
    )
    source_stage41r13_run = _resolve_recorded_run(
        project_dir, str(manifest["source_stage4_1r13_run"]), "stage4_1r13_runs"
    )
    if run_dir_override is None:
        root = project_dir / str(cfg.get("output_root", "stage4_1r15b_runs"))
        run_dir = root / f"{cfg.get('run_name', 'stage4_1r15b')}_{utc_timestamp()}"
    else:
        run_dir = run_dir_override.expanduser().resolve()
    packaged_r15_cfg = (
        project_dir
        / "configs"
        / "stage4_1r15_bounded_early_braking_local_response_identification_370ms.json"
    )
    if not packaged_r15_cfg.is_file():
        raise FileNotFoundError(f"packaged R15 dependency config missing: {packaged_r15_cfg}")
    r15_ctx = r15.load_stage41r15_config(
        packaged_r15_cfg,
        source_stage41r14_run=source_stage41r14_run,
        run_dir_override=run_dir,
    )
    if r15_ctx.source_stage41r13_run.resolve() != source_stage41r13_run.resolve():
        raise ValueError("R15B recorded R13 source does not match the reconstructed R15 chain")
    recorded_r14 = manifest.get("source_fingerprint") or {}
    current_r14 = r15._source_inventory(source_stage41r14_run)
    if recorded_r14.get("digest") != current_r14.get("digest"):
        raise ValueError("R15B nested Stage4.1R14 source fingerprint mismatch")
    storage = cfg["storage"]
    base34 = (
        r15_ctx.r14_ctx.r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34
    )
    env_cfg = copy.deepcopy(base34.env_cfg)
    env_cfg["tsc_timeout_s"] = float(cfg["runtime"]["tsc_timeout_s"])
    env_cfg["tsc_workspace_root"] = str(
        Path(
            os.environ.get(
                "STAGE4_1R15B_TSC_WORKSPACE_ROOT", storage["tsc_workspace_root"]
            )
        ).expanduser().resolve()
    )
    env_cfg["run_root"] = str(
        Path(
            os.environ.get("STAGE4_1R15B_TSC_RUN_ROOT", storage["tsc_run_root"])
        ).expanduser().resolve()
    )
    env_cfg["tsc_run_root"] = env_cfg["run_root"]
    env_cfg["keep_failed_episode_dir"] = bool(storage.get("keep_failed_episode_dir", False))
    env_cfg["keep_last_n_failed_episode_dirs"] = int(
        storage.get("keep_last_n_failed_episode_dirs", 0)
    )
    base34.env_cfg = env_cfg
    return Stage41R15BContext(
        cfg=cfg,
        paths=Stage41R15BPaths.from_run_dir(run_dir),
        project_dir=project_dir,
        source_stage41r15_run=source_stage41r15_run,
        source_stage41r14_run=source_stage41r14_run,
        source_stage41r13_run=source_stage41r13_run,
        source_manifest=manifest,
        source_state=state,
        source_cfg=source_cfg,
        source_verdict=verdict,
        r15_ctx=r15_ctx,
        source_fingerprint=_source_inventory(source_stage41r15_run),
    )


def _initial_state(ctx: Stage41R15BContext) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "prepared": True,
        "source_audit_complete": False,
        "response_model_complete": False,
        "composition_validation_complete": False,
        "finished": False,
        "stop_reason": "",
        "updated_utc": utc_timestamp(),
    }


def _update_state(ctx: Stage41R15BContext, **updates: Any) -> dict[str, Any]:
    state = read_json(ctx.paths.state) if ctx.paths.state.is_file() else _initial_state(ctx)
    state.update(_json_safe(updates))
    state["updated_utc"] = utc_timestamp()
    atomic_write_json(ctx.paths.state, state)
    return state


def prepare(ctx: Stage41R15BContext, *, resume: bool) -> None:
    for path in (
        ctx.paths.run_dir,
        ctx.paths.source_reference,
        ctx.paths.source_audit,
        ctx.paths.response_model,
        ctx.paths.composition_validation,
        ctx.paths.analysis,
        ctx.paths.variants,
    ):
        path.mkdir(parents=True, exist_ok=True)
    if ctx.paths.manifest.is_file():
        existing = read_json(ctx.paths.manifest)
        if existing.get("source_fingerprint", {}).get("digest") != ctx.source_fingerprint["digest"]:
            raise ValueError("R15B resume source fingerprint mismatch")
        if existing.get("controller_revision") != CONTROLLER_REVISION:
            raise ValueError("R15B resume controller revision mismatch")
        if existing.get("package_revision") != PACKAGE_REVISION:
            raise ValueError("R15B resume package revision mismatch")
    elif resume:
        raise FileNotFoundError("R15B resume requested but manifest is missing")
    atomic_write_json(ctx.paths.run_dir / "stage4_1r15b_config.resolved.json", ctx.cfg)
    for name, payload in (
        ("stage4_1r15_manifest.json", ctx.source_manifest),
        ("stage4_1r15_state.json", ctx.source_state),
        ("stage4_1r15_config.resolved.json", ctx.source_cfg),
        ("stage4_1r15_verdict.json", ctx.source_verdict),
        ("source_content_inventory.json", ctx.source_fingerprint),
        ("nested_stage4_1r14_source_inventory.json", ctx.source_manifest.get("source_fingerprint") or {}),
        ("nested_stage4_1r13_source_inventory.json", ctx.source_manifest.get("nested_stage4_1r13_source_fingerprint") or {}),
    ):
        atomic_write_json(ctx.paths.source_reference / name, payload)
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "created_utc": utc_timestamp(),
        "source_stage4_1r15_run": str(ctx.source_stage41r15_run),
        "source_stage4_1r14_run": str(ctx.source_stage41r14_run),
        "source_stage4_1r13_run": str(ctx.source_stage41r13_run),
        "source_fingerprint": ctx.source_fingerprint,
        "source_inventory_contract": SOURCE_INVENTORY_CONTRACT,
        "nested_stage4_1r14_source_fingerprint": ctx.source_manifest.get("source_fingerprint") or {},
        "nested_stage4_1r13_source_fingerprint": ctx.source_manifest.get("nested_stage4_1r13_source_fingerprint") or {},
        "workers": int(os.environ.get("STAGE4_1R15B_WORKERS", ctx.cfg["parallel"]["n_workers"])),
        "formal_timing_contract": ctx.cfg["formal_timing_contract"],
        "identification_only": True,
        "formal_timing_contract_restored": False,
        "stage4_2r1_was_not_run_or_reused": True,
        "finite_test_envelope_only": True,
        "final_task": ctx.cfg["final_task"],
    }
    if not ctx.paths.manifest.is_file():
        atomic_write_json(ctx.paths.manifest, manifest)
    if not ctx.paths.state.is_file():
        atomic_write_json(ctx.paths.state, _initial_state(ctx))


def _read_raw_dir(path: Path) -> list[dict[str, Any]]:
    return [read_json_gz(item) for item in sorted(path.glob("*.json.gz"))]


def _source_probe_map(ctx: Stage41R15BContext) -> dict[tuple[str, int, str, int], dict[str, Any]]:
    out: dict[tuple[str, int, str, int], dict[str, Any]] = {}
    raw = _read_raw_dir(
        ctx.source_stage41r15_run / "stage4_1r15_bounded_probe_validation" / "raw"
    )
    for result in raw:
        spec = result["spec"]
        key = (
            str(spec["target_id"]),
            int(spec["action_delay_steps"]),
            str(spec["r15_probe_id"]),
            int(spec["r15_probe_sign"]),
        )
        if key in out:
            raise ValueError(f"duplicate R15 source probe key: {key}")
        out[key] = result
    if len(out) != 32:
        raise ValueError(f"R15B expected 32 unique source probes, found {len(out)}")
    return out


def _baseline_map(ctx: Stage41R15BContext) -> dict[tuple[str, int], dict[str, Any]]:
    return r15._baseline_map(ctx.r15_ctx)


def run_source_audit(ctx: Stage41R15BContext) -> dict[str, Any]:
    source_summary = read_json(
        ctx.source_stage41r15_run / "stage4_1r15_bounded_probe_validation" / "summary.json"
    )
    results = read_json(
        ctx.source_stage41r15_run / "stage4_1r15_bounded_probe_validation" / "results.json"
    )
    symmetry_path = (
        ctx.source_stage41r15_run
        / "stage4_1r15_bounded_probe_validation"
        / "central_symmetry.csv"
    )
    import csv

    with symmetry_path.open("r", encoding="utf-8", newline="") as handle:
        symmetry = list(csv.DictReader(handle))
    failed = [row for row in results if not bool(row.get("model_prediction_pass"))]
    failed_keys = [
        (
            str(row["target_id"]),
            int(row["actual_delay_steps"]),
            str(row["probe_id"]),
            int(row["probe_sign"]),
        )
        for row in failed
    ]
    validation = ctx.source_cfg["bounded_probe_validation"]["model_validation"]
    failure = failed[0] if len(failed) == 1 else {}
    final_limit = float(validation["maximum_final_speed_error_m_per_s"])
    failure_excess = _as_float(failure.get("final_speed_error_m_per_s")) - final_limit
    checks = {
        "coverage_32": int(source_summary.get("n_rollouts", -1)) == 32,
        "runtime_32": math.isclose(float(source_summary.get("runtime_guard_pass_fraction", 0.0)), 1.0),
        "model_31_of_32": math.isclose(float(source_summary.get("model_prediction_pass_fraction", 0.0)), 31.0 / 32.0),
        "one_failure": len(failed) == 1,
        "failure_key_exact": failed_keys == [SOURCE_FAILURE_KEY],
        "only_final_speed_exceeds": bool(
            failure
            and _as_float(failure.get("velocity_component_rmse_m_per_s"))
            <= float(validation["maximum_velocity_component_rmse_m_per_s"])
            and _as_float(failure.get("endpoint_late_speed_error_m_per_s"))
            <= float(validation["maximum_endpoint_late_speed_error_m_per_s"])
            and _as_float(failure.get("final_speed_error_m_per_s")) > final_limit
            and _as_float(failure.get("position_rmse_m"))
            <= float(validation["maximum_position_rmse_m"])
            and _as_float(failure.get("ip_rmse_A")) <= float(validation["maximum_ip_rmse_A"])
        ),
        "symmetry_coverage": len(symmetry) == 16,
        "all_symmetry_pass": all(str(row.get("passed", "")).lower() == "true" for row in symmetry),
        "source_identification_only": bool(ctx.source_verdict.get("identification_only")),
        "formal_timing_not_restored": not bool(ctx.source_verdict.get("formal_timing_contract_restored")),
    }
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "source_audit",
        "source_stage4_1r15_run": str(ctx.source_stage41r15_run),
        "source_probe_rollouts": int(source_summary.get("n_rollouts", 0)),
        "environment_success_count": int(source_summary.get("environment_success_count", 0)),
        "runtime_guard_pass_fraction": float(source_summary.get("runtime_guard_pass_fraction", 0.0)),
        "source_model_prediction_pass_fraction": float(source_summary.get("model_prediction_pass_fraction", 0.0)),
        "source_failed_model_probe_count": len(failed),
        "source_failed_model_probe_keys": [list(key) for key in failed_keys],
        "failed_probe_final_speed_error_m_per_s": _as_float(failure.get("final_speed_error_m_per_s")),
        "failed_probe_final_speed_threshold_m_per_s": final_limit,
        "failed_probe_threshold_excess_m_per_s": failure_excess,
        "maximum_source_central_symmetry_velocity_rmse_m_per_s": max(
            float(row["central_symmetry_velocity_rmse_m_per_s"]) for row in symmetry
        ),
        "finite_bank_all_pass_requirement_was_correct": True,
        "posthoc_threshold_relaxation_allowed": False,
        "source_model_is_not_reinterpreted_as_validated": True,
        "stage4_2r1_was_not_run_or_reused": True,
        "checks": checks,
        "passed": all(checks.values()),
        "interpretation": (
            "R15 ran normally and 31/32 external probes passed. The single failure is not a runtime or rounding error: "
            "RZ_p10_m10, delay=1, positive late-mode-0 underpredicted final speed by 8.350 mm/s, "
            "0.350 mm/s above the preregistered limit. Plus/minus symmetry passed, so R15B replaces the "
            "source-bank absolute PCA model with a probe-derived odd differential response and tests superposition "
            "with new orthogonal combinations."
        ),
    }
    ctx.paths.source_audit.mkdir(parents=True, exist_ok=True)
    write_csv(ctx.paths.source_audit / "failed_source_model_probes.csv", failed)
    atomic_write_json(ctx.paths.source_audit / "summary.json", summary)
    _update_state(ctx, source_audit_complete=True, source_audit_summary=summary)
    return summary


def _output_layout(ctx: Stage41R15BContext) -> dict[str, int]:
    model_cfg = ctx.cfg["probe_derived_response_model"]
    start = int(model_cfg["output_state_start"])
    end = int(model_cfg["output_state_end_inclusive"])
    return {"state_start": start, "state_count": end - start + 1}


def _selected_velocity_indices(layout: Mapping[str, int]) -> list[int]:
    start = int(layout["state_start"])
    count = int(layout["state_count"])
    states = np.arange(start, start + count)
    selected_states = [24, 25, 26, 27, 34, 35, 36, 37]
    indices: list[int] = []
    for component in (0, 1):
        offset = component * count
        for state in selected_states:
            where = np.where(states == state)[0]
            if len(where) != 1:
                raise ValueError(f"R15B output layout does not contain state {state}")
            indices.append(offset + int(where[0]))
    return indices


def run_response_model(ctx: Stage41R15BContext) -> dict[str, Any]:
    source = _source_probe_map(ctx)
    baselines = _baseline_map(ctx)
    source_probe_cfg = ctx.source_cfg["bounded_probe_validation"]
    model_cfg = ctx.cfg["probe_derived_response_model"]
    layout = _output_layout(ctx)
    selected_indices = _selected_velocity_indices(layout)
    models: dict[str, Any] = {}
    rows: list[dict[str, Any]] = []
    all_pass = True
    for target in ("nominal", "RZ_p10_m10"):
        for delay in (1, 2):
            baseline_result = baselines[(target, delay)]
            baseline_y = r15._output_vector(
                baseline_result,
                start_state=int(model_cfg["output_state_start"]),
                end_state_inclusive=int(model_cfg["output_state_end_inclusive"]),
            )
            basis_responses: list[np.ndarray] = []
            pair_biases: list[np.ndarray] = []
            pair_rows: list[dict[str, Any]] = []
            for probe_id in BASIS_ORDER:
                plus = r15._output_vector(
                    source[(target, delay, probe_id, 1)],
                    start_state=int(model_cfg["output_state_start"]),
                    end_state_inclusive=int(model_cfg["output_state_end_inclusive"]),
                )
                minus = r15._output_vector(
                    source[(target, delay, probe_id, -1)],
                    start_state=int(model_cfg["output_state_start"]),
                    end_state_inclusive=int(model_cfg["output_state_end_inclusive"]),
                )
                odd = 0.5 * (plus - minus)
                even = 0.5 * (plus + minus) - baseline_y
                basis_responses.append(odd)
                pair_biases.append(even)
                count = int(layout["state_count"])
                velocity_even_rmse = float(np.sqrt(np.mean(even[: 2 * count] ** 2)))
                pair_rows.append(
                    {
                        "target_id": target,
                        "actual_delay_steps": delay,
                        "probe_id": probe_id,
                        "velocity_even_rmse_m_per_s": velocity_even_rmse,
                        "full_even_response_norm": float(np.linalg.norm(even)),
                    }
                )
            response_matrix = np.stack(basis_responses, axis=1)
            full_sv = np.linalg.svd(response_matrix, compute_uv=False)
            velocity_sv = np.linalg.svd(response_matrix[selected_indices], compute_uv=False)
            full_condition = float(full_sv[0] / max(full_sv[-1], 1e-15))
            velocity_condition = float(velocity_sv[0] / max(velocity_sv[-1], 1e-15))
            max_even_velocity = max(row["velocity_even_rmse_m_per_s"] for row in pair_rows)
            group_pass = bool(
                full_condition <= float(model_cfg["maximum_full_response_condition_number"])
                and velocity_condition
                <= float(model_cfg["maximum_selected_velocity_condition_number"])
                and max_even_velocity
                <= float(model_cfg["maximum_pair_even_velocity_rmse_m_per_s"])
            )
            all_pass = all_pass and group_pass
            group_id = f"{target}__d{delay}"
            models[group_id] = {
                "schema_version": 1,
                "target_id": target,
                "actual_delay_steps": delay,
                "baseline_experiment_id": baseline_result["experiment_id"],
                "basis_order": list(BASIS_ORDER),
                "baseline_output": baseline_y.tolist(),
                "basis_odd_response": response_matrix.T.tolist(),
                "basis_even_response": np.stack(pair_biases).tolist(),
                "full_singular_values": full_sv.tolist(),
                "selected_velocity_singular_values": velocity_sv.tolist(),
                "full_condition_number": full_condition,
                "selected_velocity_condition_number": velocity_condition,
                "pair_rows": pair_rows,
                "coefficient_semantics": "coefficient +1 equals the positive R15 0.015 probe; -1 equals the negative probe",
                "model_scope": "group-specific differential superposition around the R13 state-23 baseline",
            }
            rows.append(
                {
                    "group_id": group_id,
                    "target_id": target,
                    "actual_delay_steps": delay,
                    "basis_count": 4,
                    "full_condition_number": full_condition,
                    "selected_velocity_condition_number": velocity_condition,
                    "maximum_pair_even_velocity_rmse_m_per_s": max_even_velocity,
                    "passed": group_pass,
                }
            )
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "probe_derived_response_model",
        "group_count": len(models),
        "expected_group_count": 4,
        "basis_order": list(BASIS_ORDER),
        "model_is_probe_derived_central_difference": True,
        "source_absolute_pca_model_reused_as_validated": False,
        "group_rows": rows,
        "maximum_full_condition_number": max(row["full_condition_number"] for row in rows),
        "maximum_selected_velocity_condition_number": max(
            row["selected_velocity_condition_number"] for row in rows
        ),
        "maximum_pair_even_velocity_rmse_m_per_s": max(
            row["maximum_pair_even_velocity_rmse_m_per_s"] for row in rows
        ),
        "identification_only": True,
        "passed": bool(len(models) == 4 and all_pass),
    }
    ctx.paths.response_model.mkdir(parents=True, exist_ok=True)
    atomic_write_json(ctx.paths.response_model / "models.json", models)
    write_csv(ctx.paths.response_model / "group_summary.csv", rows)
    atomic_write_json(ctx.paths.response_model / "summary.json", summary)
    _update_state(ctx, response_model_complete=True, response_model_summary=summary)
    return summary


def _load_response_models(ctx: Stage41R15BContext) -> dict[str, Any]:
    path = ctx.paths.response_model / "models.json"
    if not path.is_file():
        raise FileNotFoundError("R15B response model artifact is missing")
    return read_json(path)


def _basis_schedules(
    ctx: Stage41R15BContext, *, actual_delay: int
) -> dict[str, dict[int, np.ndarray]]:
    source_probe = ctx.source_cfg["bounded_probe_validation"]
    basis_by_id = {str(row["probe_id"]): row for row in source_probe["probe_basis"]}
    schedules: dict[str, dict[int, np.ndarray]] = {}
    for probe_id in BASIS_ORDER:
        schedules[probe_id] = r15._probe_schedule(
            first_effect_state=int(source_probe["baseline_first_affected_state_step"]),
            actual_delay=int(actual_delay),
            basis=basis_by_id[probe_id],
            sign=1,
            amplitude_by_mode=source_probe["probe_amplitude_by_mode"],
        )
    return schedules


def _combined_schedule(
    ctx: Stage41R15BContext,
    *,
    actual_delay: int,
    coefficients: Sequence[float],
) -> dict[int, np.ndarray]:
    schedules = _basis_schedules(ctx, actual_delay=actual_delay)
    combined: dict[int, np.ndarray] = {}
    for probe_id, coefficient in zip(BASIS_ORDER, coefficients):
        for step, delta in schedules[probe_id].items():
            combined[step] = combined.get(step, np.zeros(N_MODES)) + float(coefficient) * delta
    return {step: value for step, value in sorted(combined.items()) if np.any(value != 0.0)}


class LocalStage41R15BProbeWorker:
    def __init__(
        self,
        payload: dict[str, Any],
        library: dict[str, Any],
        bundle: dict[str, Any],
        worker_id: str,
        selector_cfg: dict[str, Any],
    ):
        self.inner = r15.LocalStage41R15ProbeWorker(
            payload, library, bundle, worker_id, selector_cfg
        )

    def close(self) -> None:
        self.inner.close()

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        result = self.inner.evaluate(spec)
        result["controller_revision"] = CONTROLLER_REVISION
        result["stage4_1r15b_controller_revision"] = CONTROLLER_REVISION
        result["spec"] = copy.deepcopy(spec)
        result["r15b_combination_summary"] = {
            "combination_id": spec["r15b_combination_id"],
            "global_sign": int(spec["r15b_global_sign"]),
            "basis_order": list(BASIS_ORDER),
            "basis_coefficients": list(spec["r15b_basis_coefficients"]),
            "identification_only": True,
        }
        return _json_safe(result)


_RAY_ACTOR = None


def _ray_actor_class():
    global _RAY_ACTOR
    if _RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class Stage41R15BProbeActor:
            def __init__(self, payload, library, bundle, worker_id, selector_cfg):
                self.worker = LocalStage41R15BProbeWorker(
                    payload, library, bundle, worker_id, selector_cfg
                )

            def evaluate(self, spec):
                return self.worker.evaluate(spec)

            def close(self):
                self.worker.close()
                return True

        _RAY_ACTOR = Stage41R15BProbeActor
    return _RAY_ACTOR


def materialize_variant(ctx: Stage41R15BContext) -> tuple[str, dict[str, Any]]:
    variant, payload = r15.materialize_variant(ctx.r15_ctx)
    atomic_write_json(ctx.paths.variants / f"{variant}.payload.json", payload)
    return variant, payload


def _probe_specs(ctx: Stage41R15BContext) -> list[dict[str, Any]]:
    probe_cfg = ctx.cfg["superposition_validation"]
    variant, _ = materialize_variant(ctx)
    source_probe = ctx.source_cfg["bounded_probe_validation"]
    baseline_policy = {
        "policy_id": str(source_probe["baseline_policy_id"]),
        "first_affected_state_step": int(source_probe["baseline_first_affected_state_step"]),
    }
    specs: list[dict[str, Any]] = []
    scale = float(probe_cfg["combination_scale"])
    for delay in probe_cfg["actual_delay_steps"]:
        for target in probe_cfg["required_targets"]:
            for combo in probe_cfg["hadamard_combinations"]:
                base_coefficients = scale * np.asarray(combo["coefficients"], dtype=float)
                for global_sign in probe_cfg["probe_signs"]:
                    coefficients = float(global_sign) * base_coefficients
                    schedule = _combined_schedule(
                        ctx, actual_delay=int(delay), coefficients=coefficients
                    )
                    base_spec = r13._make_spec(
                        phase="superposition_validation",
                        policy=baseline_policy,
                        target=target,
                        actual_delay=int(delay),
                        modeled_delay=int(delay),
                        calibration_token=None,
                        trusted=True,
                        controller_variant="r15b_hadamard_superposition_probe",
                        environment_variant=variant,
                        ctx=ctx.r15_ctx.r14_ctx.r13_ctx,
                    )
                    identity = {
                        "revision": CONTROLLER_REVISION,
                        "target": dict(target),
                        "actual_delay": int(delay),
                        "combination_id": str(combo["combination_id"]),
                        "global_sign": int(global_sign),
                        "basis_coefficients": coefficients.tolist(),
                        "schedule": {
                            str(step): value.tolist() for step, value in sorted(schedule.items())
                        },
                    }
                    base_spec.update(
                        {
                            "kind": "stage4_1r15b_probe_derived_symmetric_local_response_superposition_validation",
                            "controller_revision": CONTROLLER_REVISION,
                            "experiment_id": _scenario_digest(identity),
                            "phase": "superposition_validation",
                            "category": "superposition_validation",
                            "scenario": (
                                f"{combo['combination_id']}__sign{int(global_sign):+d}__"
                                f"{target['target_id']}__d{int(delay)}__s0.9"
                            ),
                            "r15_probe_id": str(combo["combination_id"]),
                            "r15_probe_sign": int(global_sign),
                            "r15_probe_mode": -1,
                            "r15_probe_delta_by_issue_step": {
                                str(step): value.tolist() for step, value in sorted(schedule.items())
                            },
                            "r15_identification_only": True,
                            "r15b_combination_id": str(combo["combination_id"]),
                            "r15b_global_sign": int(global_sign),
                            "r15b_basis_order": list(BASIS_ORDER),
                            "r15b_basis_coefficients": coefficients.tolist(),
                            "r15b_superposition_validation_only": True,
                            "formal_tracking_pass_required": False,
                            "arrival_deadline_expansion_allowed": False,
                        }
                    )
                    specs.append(base_spec)
    if len(specs) != int(probe_cfg["expected_rollouts"]):
        raise ValueError("R15B probe specification count mismatch")
    ids = [spec["experiment_id"] for spec in specs]
    if len(set(ids)) != len(ids):
        raise ValueError("R15B probe experiment IDs are not unique")
    return specs


def evaluate_specs(
    ctx: Stage41R15BContext,
    specs: Sequence[dict[str, Any]],
    *,
    output_dir: Path,
    backend: str,
    resume: bool,
) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    variant, payload = materialize_variant(ctx)
    chain = (
        ctx.r15_ctx.r14_ctx.r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx
    )
    chain.variants[variant] = payload
    pending = [
        spec
        for spec in specs
        if not (resume and _result_complete(output_dir / f"{spec['experiment_id']}.json.gz"))
    ]
    library = chain.r3_ctx.source_library
    bundle = chain.r3_ctx.source_bundle
    selector_cfg = ctx.r15_ctx.r14_ctx.r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.cfg[
        "batch_selector"
    ]
    if backend == "serial":
        worker = LocalStage41R15BProbeWorker(
            payload, library, bundle, "stage41r15b_serial", selector_cfg
        )
        try:
            for index, spec in enumerate(pending, 1):
                atomic_write_json_gz(
                    output_dir / f"{spec['experiment_id']}.json.gz", worker.evaluate(spec)
                )
                print(f"[Stage4.1R15B superposition-probe] {index}/{len(pending)}", flush=True)
        finally:
            worker.close()
    elif backend == "ray" and pending:
        import ray

        requested = int(
            os.environ.get("STAGE4_1R15B_WORKERS", ctx.cfg["parallel"]["n_workers"])
        )
        plan = ensure_ray_worker_plan(
            ray,
            requested_workers=requested,
            pending_tasks=len(pending),
            ray_tmpdir=os.environ.get(
                "RAY_TMPDIR", ctx.cfg["parallel"].get("ray_tmpdir", "")
            )
            or None,
            log_prefix="[Stage4.1R15B superposition-probe]",
        )
        Actor = _ray_actor_class()
        actors = [
            Actor.remote(
                payload, library, bundle, f"stage41r15b_{index:03d}", selector_cfg
            )
            for index in range(plan.actor_count)
        ]
        refs: dict[Any, dict[str, Any]] = {}
        for index, spec in enumerate(pending):
            refs[actors[index % len(actors)].evaluate.remote(spec)] = spec
        done = 0
        try:
            while refs:
                ready, _ = ray.wait(list(refs), num_returns=1, timeout=30.0)
                if not ready:
                    print(
                        f"[Stage4.1R15B superposition-probe] waiting {done}/{len(pending)}",
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
                            "controller_revision": CONTROLLER_REVISION,
                            "experiment_id": spec["experiment_id"],
                            "spec": spec,
                            "success": False,
                            "failure_reason": repr(exc),
                            "traceback": traceback.format_exc(),
                            "trajectory": [],
                            "control_trace": [],
                        }
                    atomic_write_json_gz(
                        output_dir / f"{spec['experiment_id']}.json.gz", result
                    )
                    done += 1
                    if done % 10 == 0 or not refs:
                        print(
                            f"[Stage4.1R15B superposition-probe] {done}/{len(pending)}",
                            flush=True,
                        )
        finally:
            s2._close_ray_actors(
                actors,
                timeout_s=float(ctx.cfg["storage"].get("actor_close_timeout_s", 1800.0)),
            )
    elif backend not in {"serial", "ray"}:
        raise ValueError("backend must be 'ray' or 'serial'")
    return [
        read_json_gz(output_dir / f"{spec['experiment_id']}.json.gz") for spec in specs
    ]


def _predict_superposition(model: Mapping[str, Any], coefficients: Sequence[float]) -> np.ndarray:
    baseline = np.asarray(model["baseline_output"], dtype=float)
    basis = np.asarray(model["basis_odd_response"], dtype=float)
    coeff = np.asarray(coefficients, dtype=float).reshape(len(BASIS_ORDER))
    return baseline + coeff @ basis


def _reconstruction_metrics(
    original_basis: np.ndarray,
    reconstructed_basis: np.ndarray,
    layout: Mapping[str, int],
) -> dict[str, float]:
    count = int(layout["state_count"])
    diff = reconstructed_basis - original_basis
    return {
        "velocity_basis_rmse_m_per_s": float(np.sqrt(np.mean(diff[:, : 2 * count] ** 2))),
        "position_basis_rmse_m": float(
            np.sqrt(np.mean(diff[:, 2 * count : 4 * count] ** 2))
        ),
        "ip_basis_rmse_A": float(np.sqrt(np.mean(diff[:, 4 * count :] ** 2))),
    }


def run_composition_validation(
    ctx: Stage41R15BContext, *, backend: str, resume: bool
) -> dict[str, Any]:
    specs = _probe_specs(ctx)
    raw_dir = ctx.paths.composition_validation / "raw"
    results = evaluate_specs(ctx, specs, output_dir=raw_dir, backend=backend, resume=resume)
    models = _load_response_models(ctx)
    baselines = _baseline_map(ctx)
    probe_cfg = ctx.cfg["superposition_validation"]
    validation = probe_cfg["model_validation"]
    model_cfg = ctx.cfg["probe_derived_response_model"]
    layout = _output_layout(ctx)
    rows: list[dict[str, Any]] = []
    actual_outputs: dict[tuple[str, int, str, int], np.ndarray] = {}
    all_runtime_success = True
    for result in results:
        spec = result["spec"]
        target = str(spec["target_id"])
        delay = int(spec["action_delay_steps"])
        group_id = f"{target}__d{delay}"
        coefficients = np.asarray(spec["r15b_basis_coefficients"], dtype=float)
        predicted = _predict_superposition(models[group_id], coefficients)
        actual = r15._output_vector(
            result,
            start_state=int(model_cfg["output_state_start"]),
            end_state_inclusive=int(model_cfg["output_state_end_inclusive"]),
        )
        metrics = r15._prediction_metrics(actual, predicted, layout)
        summary = result.get("r15_probe_summary") or {}
        trace = list(result.get("anticipatory_damping_trace") or [])
        prefix_end = int(ctx.source_cfg["bounded_probe_validation"]["baseline_first_affected_state_step"]) - 1
        baseline = baselines[(target, delay)]
        physics_prefix = r14._physics_array(result)[: prefix_end + 1]
        baseline_prefix = r14._physics_array(baseline)[: prefix_end + 1]
        prefix_exact = bool(
            physics_prefix.shape == baseline_prefix.shape
            and np.array_equal(physics_prefix, baseline_prefix)
        )
        r8_ctx = (
            ctx.r15_ctx.r14_ctx.r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx
        )
        env_cfg = r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34.env_cfg
        currents = np.asarray(
            [row["currents_a_display"] for row in result.get("trajectory") or []],
            dtype=float,
        )
        min_i = np.asarray(env_cfg["min_current_a_display_order"], dtype=float)
        max_i = np.asarray(env_cfg["max_current_a_display_order"], dtype=float)
        center_i = 0.5 * (min_i + max_i)
        half_i = np.maximum(0.5 * (max_i - min_i), 1e-9)
        current_utilization = (
            float(np.max(np.abs((currents - center_i[None, :]) / half_i[None, :])))
            if currents.size
            else math.inf
        )
        runtime_success = bool(
            result.get("success")
            and not str(result.get("failure_reason", "")).strip()
            and not any(bool(row.get("abnormal", False)) for row in result.get("trajectory") or [])
            and all(bool(row.get("solver_success", False)) for row in trace)
            and bool((result.get("anticipatory_damping_summary") or {}).get("streaming_queue_consistent"))
            and not any(bool(row.get("future_measurement_used", True)) for row in trace)
            and bool(summary.get("probe_zero_net"))
            and bool(summary.get("applied_probe_zero_net"))
            and int(summary.get("probe_applied_issue_count", -1))
            == int(summary.get("probe_issue_count", -2))
            and _as_float(summary.get("maximum_applied_component"), math.inf)
            <= float(probe_cfg["maximum_requested_probe_component"]) + 1e-12
            and prefix_exact
            and current_utilization <= float(probe_cfg["maximum_current_utilization"])
        )
        model_pass = bool(
            metrics["velocity_component_rmse_m_per_s"]
            <= float(validation["maximum_velocity_component_rmse_m_per_s"])
            and metrics["endpoint_late_speed_error_m_per_s"]
            <= float(validation["maximum_endpoint_late_speed_error_m_per_s"])
            and metrics["final_speed_error_m_per_s"]
            <= float(validation["maximum_final_speed_error_m_per_s"])
            and metrics["position_rmse_m"]
            <= float(validation["maximum_position_rmse_m"])
            and metrics["ip_rmse_A"] <= float(validation["maximum_ip_rmse_A"])
        )
        row = {
            "experiment_id": result["experiment_id"],
            "target_id": target,
            "actual_delay_steps": delay,
            "combination_id": str(spec["r15b_combination_id"]),
            "global_sign": int(spec["r15b_global_sign"]),
            "basis_coefficients": list(spec["r15b_basis_coefficients"]),
            "environment_success": bool(result.get("success")),
            "failure_reason": str(result.get("failure_reason", "")),
            "prefix_exact_before_first_probe_effect": prefix_exact,
            "streaming_queue_consistent": bool(
                (result.get("anticipatory_damping_summary") or {}).get("streaming_queue_consistent")
            ),
            "no_future_measurement": not any(
                bool(item.get("future_measurement_used", True)) for item in trace
            ),
            "probe_zero_net": bool(summary.get("probe_zero_net")),
            "applied_probe_zero_net": bool(summary.get("applied_probe_zero_net")),
            "requested_probe_net_norm": _as_float(summary.get("requested_probe_net_norm")),
            "applied_probe_net_norm": _as_float(summary.get("applied_probe_net_norm"), math.inf),
            "probe_issue_count": int(summary.get("probe_issue_count", 0)),
            "probe_applied_issue_count": int(summary.get("probe_applied_issue_count", 0)),
            "maximum_requested_probe_component": _as_float(summary.get("maximum_requested_component")),
            "maximum_applied_probe_component": _as_float(summary.get("maximum_applied_component")),
            "maximum_current_utilization": current_utilization,
            **metrics,
            "runtime_guard_pass": runtime_success,
            "model_prediction_pass": model_pass,
        }
        rows.append(row)
        actual_outputs[
            (target, delay, str(spec["r15b_combination_id"]), int(spec["r15b_global_sign"]))
        ] = actual
        all_runtime_success = all_runtime_success and runtime_success

    symmetry_rows: list[dict[str, Any]] = []
    reconstruction_rows: list[dict[str, Any]] = []
    all_symmetry_pass = True
    all_reconstruction_pass = True
    count = int(layout["state_count"])
    hadamard = np.asarray(
        [row["coefficients"] for row in probe_cfg["hadamard_combinations"]],
        dtype=float,
    )
    scale = float(probe_cfg["combination_scale"])
    combo_ids = [str(row["combination_id"]) for row in probe_cfg["hadamard_combinations"]]
    for target in ("nominal", "RZ_p10_m10"):
        for delay in (1, 2):
            model = models[f"{target}__d{delay}"]
            baseline_y = np.asarray(model["baseline_output"], dtype=float)
            odd_columns: list[np.ndarray] = []
            for combo_id in combo_ids:
                plus = actual_outputs[(target, delay, combo_id, 1)]
                minus = actual_outputs[(target, delay, combo_id, -1)]
                asymmetry = plus + minus - 2.0 * baseline_y
                velocity_rmse = float(np.sqrt(np.mean(asymmetry[: 2 * count] ** 2)))
                passed = velocity_rmse <= float(
                    validation["maximum_central_symmetry_velocity_rmse_m_per_s"]
                )
                all_symmetry_pass = all_symmetry_pass and passed
                symmetry_rows.append(
                    {
                        "target_id": target,
                        "actual_delay_steps": delay,
                        "combination_id": combo_id,
                        "central_symmetry_velocity_rmse_m_per_s": velocity_rmse,
                        "passed": passed,
                    }
                )
                odd_columns.append(0.5 * (plus - minus))
            combo_odd = np.stack(odd_columns, axis=1)
            reconstructed = (combo_odd @ (hadamard * scale)).T
            original = np.asarray(model["basis_odd_response"], dtype=float)
            metrics = _reconstruction_metrics(original, reconstructed, layout)
            passed = bool(
                metrics["velocity_basis_rmse_m_per_s"]
                <= float(validation["maximum_basis_reconstruction_velocity_rmse_m_per_s"])
                and metrics["position_basis_rmse_m"]
                <= float(validation["maximum_basis_reconstruction_position_rmse_m"])
                and metrics["ip_basis_rmse_A"]
                <= float(validation["maximum_basis_reconstruction_ip_rmse_A"])
            )
            all_reconstruction_pass = all_reconstruction_pass and passed
            reconstruction_rows.append(
                {
                    "target_id": target,
                    "actual_delay_steps": delay,
                    **metrics,
                    "passed": passed,
                }
            )

    pass_fraction = float(
        np.mean(
            [
                bool(row["runtime_guard_pass"] and row["model_prediction_pass"])
                for row in rows
            ]
        )
    )
    passed = bool(
        len(rows) == int(probe_cfg["expected_rollouts"])
        and all_runtime_success
        and pass_fraction >= float(validation["minimum_pass_fraction"])
        and all_symmetry_pass
        and all_reconstruction_pass
    )
    ctx.paths.composition_validation.mkdir(parents=True, exist_ok=True)
    write_csv(ctx.paths.composition_validation / "results.csv", rows)
    atomic_write_json(ctx.paths.composition_validation / "results.json", rows)
    write_csv(ctx.paths.composition_validation / "central_symmetry.csv", symmetry_rows)
    write_csv(ctx.paths.composition_validation / "basis_reconstruction.csv", reconstruction_rows)
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "superposition_validation",
        "n_rollouts": len(rows),
        "expected_rollouts": int(probe_cfg["expected_rollouts"]),
        "coverage_complete": len(rows) == int(probe_cfg["expected_rollouts"]),
        "environment_success_count": sum(bool(row["environment_success"]) for row in rows),
        "runtime_guard_pass_fraction": float(
            np.mean([bool(row["runtime_guard_pass"]) for row in rows])
        ),
        "model_prediction_pass_fraction": float(
            np.mean([bool(row["model_prediction_pass"]) for row in rows])
        ),
        "joint_pass_fraction": pass_fraction,
        "maximum_velocity_component_rmse_m_per_s": max(
            row["velocity_component_rmse_m_per_s"] for row in rows
        ),
        "maximum_endpoint_late_speed_error_m_per_s": max(
            row["endpoint_late_speed_error_m_per_s"] for row in rows
        ),
        "maximum_final_speed_error_m_per_s": max(
            row["final_speed_error_m_per_s"] for row in rows
        ),
        "maximum_position_rmse_m": max(row["position_rmse_m"] for row in rows),
        "maximum_ip_rmse_A": max(row["ip_rmse_A"] for row in rows),
        "maximum_central_symmetry_velocity_rmse_m_per_s": max(
            row["central_symmetry_velocity_rmse_m_per_s"] for row in symmetry_rows
        ),
        "maximum_basis_reconstruction_velocity_rmse_m_per_s": max(
            row["velocity_basis_rmse_m_per_s"] for row in reconstruction_rows
        ),
        "maximum_basis_reconstruction_position_rmse_m": max(
            row["position_basis_rmse_m"] for row in reconstruction_rows
        ),
        "maximum_basis_reconstruction_ip_rmse_A": max(
            row["ip_basis_rmse_A"] for row in reconstruction_rows
        ),
        "hadamard_combinations_are_new_external_validation": True,
        "formal_tracking_pass_required": False,
        "formal_timing_contract_restored": False,
        "identification_only": True,
        "passed": passed,
    }
    atomic_write_json(ctx.paths.composition_validation / "summary.json", summary)
    _update_state(
        ctx,
        composition_validation_complete=True,
        composition_validation_summary=summary,
    )
    return summary


def finalize(ctx: Stage41R15BContext) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    source = state.get("source_audit_summary") or {}
    model = state.get("response_model_summary") or {}
    validation = state.get("composition_validation_summary") or {}
    passed = bool(source.get("passed") and model.get("passed") and validation.get("passed"))
    verdict = {
        "schema_version": 1,
        "stage": STAGE,
        "created_utc": utc_timestamp(),
        "verdict": (
            "STAGE4_1R15B_PROBE_DERIVED_SUPERPOSITION_MODEL_VALIDATED"
            if passed
            else "STAGE4_1R15B_PROBE_DERIVED_SUPERPOSITION_MODEL_INCOMPLETE"
        ),
        "source_stage4_1r15_run": str(ctx.source_stage41r15_run),
        "source_stage4_1r14_run": str(ctx.source_stage41r14_run),
        "source_stage4_1r13_run": str(ctx.source_stage41r13_run),
        "source_audit_status": "passed" if source.get("passed") else "failed",
        "probe_derived_model_status": "passed" if model.get("passed") else (
            "not_run" if not model else "failed"
        ),
        "superposition_validation_status": "passed" if validation.get("passed") else (
            "not_run" if not validation else "failed"
        ),
        "identification_only": True,
        "formal_timing_contract_restored": False,
        "arrival_deadline_expanded": False,
        "true_restart_validation_performed": False,
        "continuous_parameter_change_validated": False,
        "plant_parameter_robustness_validated": False,
        "unseen_hidden_state_robustness_validated": False,
        "deployment_robustness_validated": False,
        "stage4_2r1_was_not_run_or_reused": True,
        "finite_test_envelope_only": True,
        "next_if_pass": ctx.cfg["next_if_pass"],
        "next_if_fail": ctx.cfg["next_if_fail"],
        "final_task": ctx.cfg["final_task"],
        "phases": {
            "source_audit": source,
            "probe_derived_response_model": model,
            "superposition_validation": validation,
        },
    }
    ctx.paths.analysis.mkdir(parents=True, exist_ok=True)
    atomic_write_json(ctx.paths.analysis / "stage4_1r15b_verdict.json", verdict)
    atomic_write_json(ctx.paths.analysis / "stage4_1r15b_summary.json", verdict)
    stop_reason = "" if passed else (
        "superposition_model_validation_failed"
        if validation
        else "source_or_response_model_validation_failed"
    )
    _update_state(
        ctx,
        finished=True,
        stop_reason=stop_reason,
        final_verdict=verdict["verdict"],
    )
    return verdict


def execute(
    ctx: Stage41R15BContext,
    *,
    command: str,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    prepare(ctx, resume=resume)
    if command not in {"all", "audit", "model", "probes"}:
        raise ValueError("command must be all/audit/model/probes")
    state = read_json(ctx.paths.state)
    if command in {"all", "audit"} and not bool(state.get("source_audit_complete")):
        source = run_source_audit(ctx)
        if not source.get("passed"):
            return finalize(ctx)
    state = read_json(ctx.paths.state)
    if command in {"all", "model"} and not bool(state.get("response_model_complete")):
        model = run_response_model(ctx)
        if not model.get("passed"):
            return finalize(ctx)
    state = read_json(ctx.paths.state)
    if command in {"all", "probes"} and not bool(
        state.get("composition_validation_complete")
    ):
        validation = run_composition_validation(ctx, backend=backend, resume=resume)
        if not validation.get("passed"):
            return finalize(ctx)
    return finalize(ctx)


def self_test(project_dir: Path) -> dict[str, Any]:
    cfg_path = (
        project_dir
        / "configs"
        / "stage4_1r15b_probe_derived_symmetric_local_response_superposition_validation_370ms.json"
    )
    cfg = read_json(cfg_path)
    validate_config(cfg)
    # Synthetic model with four orthogonal response columns.
    baseline = np.arange(75, dtype=float) / 1000.0
    basis = np.arange(4 * 75, dtype=float).reshape(4, 75) / 10000.0
    model = {"baseline_output": baseline.tolist(), "basis_odd_response": basis.tolist()}
    coefficients = np.asarray([0.5, -0.5, 0.5, -0.5])
    predicted = _predict_superposition(model, coefficients)
    expected = baseline + coefficients @ basis
    # Verify every combined schedule remains zero-net and within 0.015.
    source_cfg = read_json(
        project_dir
        / "configs"
        / "stage4_1r15_bounded_early_braking_local_response_identification_370ms.json"
    )
    dummy = type("Dummy", (), {"cfg": cfg, "source_cfg": source_cfg})()
    schedule_rows: list[dict[str, Any]] = []
    scale = float(cfg["superposition_validation"]["combination_scale"])
    for delay in (1, 2):
        for combo in cfg["superposition_validation"]["hadamard_combinations"]:
            for sign in (-1, 1):
                coeff = sign * scale * np.asarray(combo["coefficients"], dtype=float)
                schedule = _combined_schedule(dummy, actual_delay=delay, coefficients=coeff)
                net = np.sum(np.stack(list(schedule.values())), axis=0)
                schedule_rows.append(
                    {
                        "zero_net": bool(np.allclose(net, np.zeros(3), atol=1e-12, rtol=0.0)),
                        "maximum_component": float(
                            max(np.max(np.abs(value)) for value in schedule.values())
                        ),
                    }
                )
    passed = bool(
        np.array_equal(predicted, expected)
        and len(schedule_rows) == 16
        and all(row["zero_net"] for row in schedule_rows)
        and max(row["maximum_component"] for row in schedule_rows) <= 0.015 + 1e-12
        and int(cfg["superposition_validation"]["expected_rollouts"]) == 32
        and cfg["formal_timing_contract"]["normal_slew"]["arrival_deadline_step"] == 25
        and cfg["formal_timing_contract"]["weak_slew"]["arrival_deadline_step"] == 27
        and cfg.get("stage4_2r1_was_not_run_or_reused")
    )
    return {
        "schema_version": 1,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "config_valid": True,
        "hadamard_combination_count": 4,
        "combination_probe_schedule_variants_per_target": len(schedule_rows),
        "expected_true_tsc_probe_rollouts": int(
            cfg["superposition_validation"]["expected_rollouts"]
        ),
        "all_probes_zero_net": all(row["zero_net"] for row in schedule_rows),
        "maximum_probe_component": max(row["maximum_component"] for row in schedule_rows),
        "synthetic_superposition_exact": bool(np.array_equal(predicted, expected)),
        "formal_timing_contract_immutable": True,
        "formal_timing_contract_restored_by_this_stage": False,
        "stage4_2r1_was_not_run_or_reused": True,
        "passed": passed,
    }


def _default_source(project_dir: Path) -> Path:
    env = os.environ.get("STAGE4_1R15B_SOURCE_STAGE4_1R15_RUN")
    if env:
        return Path(env).expanduser().resolve()
    latest = project_dir / "stage4_1r15_runs" / "latest_stage4_1r15_run.txt"
    if latest.is_file():
        return Path(latest.read_text(encoding="utf-8").strip()).expanduser().resolve()
    raise FileNotFoundError(
        "set STAGE4_1R15B_SOURCE_STAGE4_1R15_RUN or provide --source-stage4-1r15-run"
    )


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Stage4.1R15B probe-derived symmetric response superposition validation"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(
            "configs/stage4_1r15b_probe_derived_symmetric_local_response_superposition_validation_370ms.json"
        ),
    )
    parser.add_argument("--source-stage4-1r15-run", type=Path, default=None)
    parser.add_argument("--run-dir", type=Path, default=None)
    parser.add_argument(
        "--command",
        choices=["all", "audit", "model", "probes"],
        default=os.environ.get("STAGE4_1R15B_COMMAND", "all"),
    )
    parser.add_argument(
        "--backend",
        choices=["ray", "serial"],
        default=os.environ.get("STAGE4_1R15B_BACKEND", "ray"),
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=os.environ.get("STAGE4_1R15B_RESUME", "0") == "1",
    )
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    config_path = args.config.expanduser().resolve()
    project_dir = config_path.parents[1]
    if args.self_test:
        print(json.dumps(self_test(project_dir), indent=2, sort_keys=True))
        return
    source = args.source_stage4_1r15_run or _default_source(project_dir)
    run_dir = args.run_dir
    env_run = os.environ.get("STAGE4_1R15B_RUN_DIR")
    if run_dir is None and env_run:
        run_dir = Path(env_run)
    ctx = load_stage41r15b_config(
        config_path,
        source_stage41r15_run=source,
        run_dir_override=run_dir,
    )
    payload = execute(
        ctx,
        command=args.command,
        backend=args.backend,
        resume=bool(args.resume),
    )
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
