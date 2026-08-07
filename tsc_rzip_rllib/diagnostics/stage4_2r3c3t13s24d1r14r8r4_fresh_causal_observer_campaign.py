"""Execute and audit the frozen R8R4 fresh causal observer campaign."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r7_causal_response_model as r7_source,
)
from scripts import (
    stage4_2r3c3t13s24d1r14r8r1_fixed_candidate_short_horizon_discriminator as r8r1_primary,
    stage4_2r3c3t13s24d1r14r8r2_causal_online_innovation_adaptation as r8r2_primary,
    stage4_2r3c3t13s24d1r14r8r3_causal_history_no_action_observer as r8r3_primary,
)
from tsc_rzip_rllib.control import causal_history_no_action_observer as observer
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification as r8,
    stage4_2r3c3t13s24d1r14r8r4_fresh_causal_observer_identification as contract,
)


PHASES = ("development", "holdout")


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class Paths:
    run_dir: Path
    stage_dir: Path
    variants: Path
    specs: Path
    source_reference: Path
    raw: Path
    analysis: Path
    model: Path
    state: Path
    manifest: Path

    def phase_raw(self, phase: str) -> Path:
        if phase not in PHASES:
            raise ValueError(f"invalid R8R4 phase: {phase}")
        return self.raw / phase


def _paths(run_dir: Path) -> Paths:
    run = run_dir.expanduser().resolve()
    stage = run / contract.RUN_NAME
    return Paths(
        run_dir=run,
        stage_dir=stage,
        variants=stage / "variants",
        specs=stage / "specs",
        source_reference=stage / "source_reference",
        raw=stage / "raw",
        analysis=stage / "analysis",
        model=stage / "model",
        state=stage / "stage_state.json",
        manifest=stage / "stage_manifest.json",
    )


@dataclass
class Context:
    cfg: dict[str, Any]
    config_path: Path
    paths: Paths
    r8_cfg: dict[str, Any]
    r8_config_path: Path
    r8_run: Path
    r8r3_output: Path
    r8_ctx: r8.Context
    source_r2_run: Path
    source_r4_run: Path
    source_r6_run: Path


def _package_fingerprint() -> dict[str, Any]:
    relative = (
        "configs/stage4_2r3c3t13s24d1r14r8r4_fresh_causal_observer_identification_370ms.json",
        "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r4_independent_forensics.py",
        "docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R4_FRESH_CAUSAL_OBSERVER_IDENTIFICATION_DESIGN.md",
        "run_stage4_2r3c3t13s24d1r14r8r4_common.sh",
        "run_stage4_2r3c3t13s24d1r14r8r4_native.sh",
        "run_stage4_2r3c3t13s24d1r14r8r4_nohup.sh",
        "run_stage4_2r3c3t13s24d1r14r8r4_self_test.sh",
        "run_stage4_2r3c3t13s24d1r14r8r4_verify_package.sh",
        "scripts/stage4_2r3c3t13s24d1r14r8r4_fresh_causal_observer_campaign.py",
        "scripts/stage4_2r3c3t13s24d1r14r8r4_shell_common.sh",
        "tests/test_stage4_2r3c3t13s24d1r14r8r4_fresh_causal_observer_identification.py",
        "tsc_rzip_rllib/control/causal_history_no_action_observer.py",
        "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r8r4_fresh_causal_observer_identification.py",
        "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r8r4_fresh_causal_observer_campaign.py",
    )
    files = []
    for name in relative:
        path = _root() / name
        if not path.is_file():
            raise ValueError(f"R8R4 package source missing: {name}")
        files.append({"path": name, "bytes": path.stat().st_size, "sha256": _sha(path)})
    return {"files": files, "digest": r8._digest(files)}


def load_context(args: argparse.Namespace) -> Context:
    config_path = args.config.expanduser().resolve()
    cfg = _read(config_path)
    contract.validate_config(cfg, project_root=_root())
    r8_config = (_root() / str(cfg["source_r8_config"])).resolve()
    r8_cfg = _read(r8_config)
    source_kwargs = {
        name: getattr(args, name)
        for name in (
            "source_s21_run",
            "source_s23r1_output",
            "source_s24_run",
            "source_d1r9_v1",
            "source_d1r9_v2",
            "source_d1r10_run",
            "source_d1r10_audit",
            "source_stage42r3b_run",
            "source_stage42r3c3_run",
            "source_stage42r3c3_bank_dir",
            "source_stage42r3c3t1_run",
            "source_stage42r3c3t1_audit_dir",
            "source_stage42r3c3t3_controller_bank",
            "q1_run",
            "q2_run",
            "q1_audit",
            "q2_audit",
            "r3b_server_audit",
            "r3b_snapshot_checks",
        )
    }
    r8_ctx = r8.load_config(
        r8_config,
        source_d1r11_run=args.source_d1r11_run,
        source_r2_run=args.source_r2_run,
        source_r4_run=args.source_r4_run,
        source_r6_run=args.source_r6_run,
        run_dir=args.r8_run,
        **source_kwargs,
    )
    return Context(
        cfg=cfg,
        config_path=config_path,
        paths=_paths(args.run_dir),
        r8_cfg=r8_cfg,
        r8_config_path=r8_config,
        r8_run=args.r8_run.expanduser().resolve(),
        r8r3_output=args.r8r3_output.expanduser().resolve(),
        r8_ctx=r8_ctx,
        source_r2_run=args.source_r2_run.expanduser().resolve(),
        source_r4_run=args.source_r4_run.expanduser().resolve(),
        source_r6_run=args.source_r6_run.expanduser().resolve(),
    )


def _authenticate_r8r3(ctx: Context) -> dict[str, Any]:
    expected = ctx.cfg["source_r8r3_contract"]
    paths = {
        "primary_detailed": ctx.r8r3_output / "primary_detailed.json",
        "primary_summary": ctx.r8r3_output / "primary_summary.json",
        "independent": ctx.r8r3_output / "independent.json",
        "stage_state": ctx.r8r3_output / "stage_state.json",
    }
    for name, path in paths.items():
        if (
            not path.is_file()
            or path.stat().st_size != int(expected[f"{name}_bytes"])
            or _sha(path) != str(expected[f"{name}_sha256"])
        ):
            raise ValueError(f"R8R4 R8R3 {name} changed")
    detailed = _read(paths["primary_detailed"])
    independent = _read(paths["independent"])
    state = _read(paths["stage_state"])
    route = str(expected["required_route"])
    if (
        detailed.get("route") != route
        or detailed.get("scientific_gate_passed") is not False
        or independent.get("route") != route
        or independent.get("primary_numerical_agreement") is not True
        or independent.get("primary_outcome_agreement") is not True
        or state.get("route") != route
        or state.get("finished") is not True
        or state.get("independent_completed") is not True
        or int(state.get("new_raw_count", -1)) != 0
        or bool(state.get("heldout_outcomes_opened"))
    ):
        raise ValueError("R8R4 R8R3 outcome changed")
    return {name + "_sha256": _sha(path) for name, path in paths.items()}


def _authenticate_r8(ctx: Context) -> dict[str, Any]:
    expected = ctx.cfg["source_r8_contract"]
    paths = r8._paths(ctx.r8_run)
    if (
        _sha(paths.state) != str(expected["stage_state_sha256"])
        or _sha(paths.manifest) != str(expected["stage_manifest_sha256"])
    ):
        raise ValueError("R8R4 source R8 state or manifest changed")
    state = _read(paths.state)
    training = r8._inventory(paths.phase_raw("training"))
    calibration = r8._inventory(paths.phase_raw("calibration"))
    holdout = r8._inventory(paths.phase_raw("holdout"))
    if (
        state.get("phase_status") != expected["required_phase_status"]
        or (state.get("verdict") or {}).get("route") != expected["required_route"]
        or training["count"] != int(expected["training_raw_count"])
        or training["bytes"] != int(expected["training_raw_bytes"])
        or training["digest"] != str(expected["training_raw_digest"])
        or calibration["count"] != 0
        or holdout["count"] != 0
    ):
        raise ValueError("R8R4 source R8 inventory or route changed")
    d1 = r8._authenticate_d1r11(ctx.r8_ctx)
    snapshots = r8._snapshot_audit(d1["context_table"])
    if not snapshots["passed"]:
        raise ValueError("R8R4 source restart snapshot authentication failed")
    return {
        "state_sha256": _sha(paths.state),
        "manifest_sha256": _sha(paths.manifest),
        "training_inventory": training,
        "calibration_inventory": calibration,
        "holdout_inventory": holdout,
        "source_snapshot_pass_count": int(snapshots["pass_count"]),
    }


def _new_specs(ctx: Context) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    mapping = {"development": "calibration", "holdout": "holdout"}
    for phase in PHASES:
        allowed = set(map(str, ctx.cfg["pair_partitions"][phase]))
        source = [
            row
            for row in r8._phase_specs(ctx.r8_ctx, mapping[phase])
            if str(row["d1r14r8_role"]) == "baseline"
            and str(row["pair_id"]) in allowed
        ]
        if len(source) != 8:
            raise ValueError(f"R8R4 {phase} baseline blueprint coverage changed")
        for index, original in enumerate(
            sorted(source, key=lambda row: (str(row["pair_id"]), str(row["history_member"])))
        ):
            spec = copy.deepcopy(original)
            source_id = str(spec["experiment_id"])
            spec.update(
                {
                    "kind": "stage4_2r3c3t13s24d1r14r8r4_fresh_causal_observer_baseline",
                    "partition": phase,
                    "experiment_id": f"r8r4_{phase}_{index:02d}",
                    "source_r8_blueprint_experiment_id": source_id,
                    "r8r4_baseline_only": True,
                    "r8r4_zero_action_first_task_step": 10,
                    "r8r4_allowed_in_expert_dataset": False,
                }
            )
            output.append(spec)
    if len(output) != 16 or len({row["experiment_id"] for row in output}) != 16:
        raise ValueError("R8R4 specification identity changed")
    return output


def prepare_offline(ctx: Context) -> dict[str, Any]:
    if ctx.paths.stage_dir.exists() or ctx.paths.state.exists():
        raise ValueError("R8R4 offline requires a fresh run identity")
    source_r8 = _authenticate_r8(ctx)
    source_r8r3 = _authenticate_r8r3(ctx)
    specs = _new_specs(ctx)
    package = _package_fingerprint()
    for path in (
        ctx.paths.stage_dir,
        ctx.paths.variants,
        ctx.paths.specs,
        ctx.paths.source_reference,
        ctx.paths.analysis,
        ctx.paths.model,
    ):
        path.mkdir(parents=True, exist_ok=True)
    for phase in PHASES:
        ctx.paths.phase_raw(phase).mkdir(parents=True, exist_ok=True)
    _write(ctx.paths.specs / "all_specs.json", specs)
    for phase in PHASES:
        _write(
            ctx.paths.specs / f"{phase}_specs.json",
            [row for row in specs if row["partition"] == phase],
        )
    _write(ctx.paths.source_reference / "r8_authentication.json", source_r8)
    _write(ctx.paths.source_reference / "r8r3_authentication.json", source_r8r3)
    manifest = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "campaign_identity": contract.IDENTITY,
        "controller_revision": contract.CONTROLLER_REVISION,
        "package_revision": contract.PACKAGE_REVISION,
        "config_path": str(ctx.config_path),
        "config_sha256": _sha(ctx.config_path),
        "design_document_sha256": contract.DESIGN_SHA256,
        "source_r8_run": str(ctx.r8_run),
        "source_r8r3_output": str(ctx.r8r3_output),
        "spec_count": len(specs),
        "spec_digest": r8._digest(specs),
        "package_fingerprint": package,
        "formal_timing_unchanged": True,
        "all_stage_trajectories_allowed_in_expert_dataset": False,
    }
    state = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "phase_status": "offline_ready",
        "finished": False,
        "real_tsc_executed": False,
        "new_raw_count": 0,
        "holdout_outcomes_opened": False,
        "observer_model_sha256": "",
        "observer_tube_sha256": "",
        "spec_digest": manifest["spec_digest"],
        "package_digest": package["digest"],
        "verdict": {},
    }
    _write(ctx.paths.manifest, manifest)
    _write(ctx.paths.state, state)
    report = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "phase": "source_and_spec_preflight",
        "source_r8_authenticated": True,
        "source_r8r3_authenticated": True,
        "spec_count": 16,
        "development_spec_count": 8,
        "holdout_spec_count": 8,
        "holdout_raw_count": 0,
        "new_raw_count": 0,
        "real_tsc_executed": False,
        "passed": True,
    }
    _write(ctx.paths.analysis / "offline_preflight.json", report)
    return report


def _saved_specs(ctx: Context) -> list[dict[str, Any]]:
    specs = _read(ctx.paths.specs / "all_specs.json")
    manifest = _read(ctx.paths.manifest)
    if (
        len(specs) != 16
        or r8._digest(specs) != manifest.get("spec_digest")
        or manifest.get("stage") != contract.STAGE
        or manifest.get("campaign_identity") != contract.IDENTITY
        or manifest.get("controller_revision") != contract.CONTROLLER_REVISION
        or _sha(ctx.config_path) != manifest.get("config_sha256")
    ):
        raise ValueError("R8R4 saved identity or spec digest changed")
    return specs


def _phase_specs(ctx: Context, phase: str) -> list[dict[str, Any]]:
    specs = [row for row in _saved_specs(ctx) if row["partition"] == phase]
    if phase not in PHASES or len(specs) != 8:
        raise ValueError("R8R4 saved phase coverage changed")
    return specs


def _set_state(ctx: Context, **updates: Any) -> dict[str, Any]:
    state = _read(ctx.paths.state)
    state.update(updates)
    _write(ctx.paths.state, state)
    return state


def _require(ctx: Context, phase_status: str) -> dict[str, Any]:
    state = _read(ctx.paths.state)
    manifest = _read(ctx.paths.manifest)
    if (
        state.get("phase_status") != phase_status
        or bool(state.get("finished"))
        or state.get("spec_digest") != manifest.get("spec_digest")
        or state.get("package_digest")
        != (manifest.get("package_fingerprint") or {}).get("digest")
    ):
        raise ValueError(
            f"R8R4 phase guard expected {phase_status!r}, got {state.get('phase_status')!r}"
        )
    return state


def _execution_context(ctx: Context) -> r8.Context:
    return r8.Context(
        cfg=ctx.r8_cfg,
        config_path=ctx.r8_config_path,
        d1r11_ctx=ctx.r8_ctx.d1r11_ctx,
        source_d1r11_run=ctx.r8_ctx.source_d1r11_run,
        source_response_runs=ctx.r8_ctx.source_response_runs,
        paths=ctx.paths,  # type: ignore[arg-type]
    )


def _payload(ctx: Context, spec: Mapping[str, Any]) -> dict[str, Any]:
    execution = _execution_context(ctx)
    payload = r8._payload(execution, spec)
    experiment_id = str(spec["experiment_id"])
    payload.update(
        {
            "variant_id": f"stage4_2r3c3t13s24d1r14r8r4_{experiment_id}",
            "stage4_2r3c3t13s24d1r14r8r4_baseline_only": True,
            "stage4_2r3c3t13s24d1r14r8r4_zero_action_first_task_step": 10,
            "stage4_2r3c3t13s24d1r14r8r4_pair_history_partition_label_available_to_controller": False,
        }
    )
    _write(ctx.paths.variants / f"payload_{experiment_id}.json", payload)
    return payload


class LocalWorker:
    """One inherited baseline controller and one fresh TSC process."""

    def __init__(self, *args: Any):
        self.worker = r8.LocalWorker(*args)

    def close(self) -> None:
        self.worker.close()

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        result = self.worker.evaluate(spec)
        result.update(
            {
                "schema_version": 1,
                "stage": contract.STAGE,
                "campaign_identity": contract.IDENTITY,
                "controller_revision": contract.CONTROLLER_REVISION,
                "experiment_id": str(spec["experiment_id"]),
                "spec": copy.deepcopy(spec),
                "inherited_execution_stage": r8.STAGE,
                "inherited_execution_controller_revision": r8.CONTROLLER_REVISION,
            }
        )
        for row in result.get("controller_trace") or []:
            row.update(
                {
                    "r3c3t13s24d1r14r8r4_controller_revision": contract.CONTROLLER_REVISION,
                    "r3c3t13s24d1r14r8r4_baseline_only": True,
                    "r3c3t13s24d1r14r8r4_future_r17_executed": False,
                    "r3c3t13s24d1r14r8r4_pair_or_history_label_used": False,
                    "r3c3t13s24d1r14r8r4_partition_label_used": False,
                    "r3c3t13s24d1r14r8r4_source_result_used": False,
                }
            )
        summary = result.setdefault("hidden_history_control_summary", {})
        summary.update(
            {
                "fresh_controller_actor": True,
                "fresh_tsc_process": True,
                "identification_only": True,
                "probe_trajectory_allowed_in_expert_dataset": False,
                "stage_trajectory_allowed_in_expert_dataset": False,
                "future_action_replay_used": False,
                "future_measurement_used": False,
                "pair_or_history_label_used": False,
                "partition_label_used": False,
                "source_result_used": False,
            }
        )
        return r8.d1r11.s21.s16.s9.t11.t1._json_safe(result)


_RAY_ACTOR = None


def _ray_actor_class():
    global _RAY_ACTOR
    if _RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class Stage42R8R4Actor:
            def __init__(self, *args: Any):
                self.worker = LocalWorker(*args)

            def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
                return self.worker.evaluate(spec)

            def close(self) -> bool:
                self.worker.close()
                return True

        _RAY_ACTOR = Stage42R8R4Actor
    return _RAY_ACTOR


def _result_complete(path: Path, spec: Mapping[str, Any], *, success: bool = True) -> bool:
    if not path.is_file():
        return False
    try:
        result = r8._read_gz(path)
        horizon = int(spec["horizon_steps"])
        return bool(
            result.get("completed")
            and (result.get("success") or not success)
            and result.get("stage") == contract.STAGE
            and result.get("campaign_identity") == contract.IDENTITY
            and result.get("controller_revision") == contract.CONTROLLER_REVISION
            and result.get("experiment_id") == spec["experiment_id"]
            and result.get("spec") == dict(spec)
            and (
                not success
                or (
                    len(result.get("trajectory") or []) == horizon + 1
                    and len(result.get("controller_trace") or []) == horizon
                )
            )
        )
    except Exception:
        return False


def evaluate_specs(
    ctx: Context,
    specs: Sequence[dict[str, Any]],
    *,
    phase: str,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    raw_dir = ctx.paths.phase_raw(phase)
    pending = [
        spec
        for spec in specs
        if not (resume and _result_complete(raw_dir / f"{spec['experiment_id']}.json.gz", spec))
    ]
    payloads = {str(spec["experiment_id"]): _payload(ctx, spec) for spec in specs}
    execution = _execution_context(ctx)
    library, bundle, selector = r8.d1r11._library_bundle_selector(execution.d1r11_ctx)
    lattice = execution.d1r11_ctx.base_ctx.base_ctx.cfg["lattice_probe"]
    calibration = execution.d1r11_ctx.base_ctx.base_ctx.cfg["active_calibration"]
    dynamic = execution.d1r11_ctx.base_ctx.cfg["causal_model"]
    schedule = execution.d1r11_ctx.cfg["schedule_contract"]

    def worker_args(spec: Mapping[str, Any], index: int) -> tuple[Any, ...]:
        kernel = str(spec["d1r14r8_execution_kernel"])
        return (
            payloads[str(spec["experiment_id"])],
            library,
            bundle,
            f"stage42r8r4_{phase}_{index:02d}",
            selector,
            lattice,
            calibration,
            dynamic,
            schedule,
            r8._kernel_contract(ctx.r8_cfg, kernel),
            kernel,
        )

    if backend == "serial":
        for index, spec in enumerate(pending):
            worker = LocalWorker(*worker_args(spec, index))
            try:
                result = worker.evaluate(spec)
            finally:
                worker.close()
            r8._write_gz(raw_dir / f"{spec['experiment_id']}.json.gz", result)
            print(f"[R8R4 {phase}] {index + 1}/{len(pending)}", flush=True)
    elif backend == "ray" and pending:
        import ray

        plan = r8.d1r11.s21.s16.ensure_ray_worker_plan(
            ray,
            requested_workers=int(ctx.cfg["parallel"]["n_workers"]),
            pending_tasks=len(pending),
            ray_tmpdir=os.environ.get("RAY_TMPDIR") or ctx.cfg["storage"]["ray_tmpdir"],
            log_prefix=f"[R8R4 {phase}]",
        )
        Actor = _ray_actor_class()
        for start in range(0, len(pending), plan.actor_count):
            batch = pending[start : start + plan.actor_count]
            actors = []
            refs = {}
            for offset, spec in enumerate(batch):
                actor = Actor.remote(*worker_args(spec, start + offset))
                actors.append(actor)
                refs[actor.evaluate.remote(spec)] = spec
            try:
                while refs:
                    ready, _ = ray.wait(list(refs), num_returns=1)
                    ref = ready[0]
                    spec = refs.pop(ref)
                    r8._write_gz(
                        raw_dir / f"{spec['experiment_id']}.json.gz", ray.get(ref)
                    )
                    print(
                        f"[R8R4 {phase}] {len(pending) - len(refs)}/{len(pending)}",
                        flush=True,
                    )
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
        raise ValueError(f"unsupported R8R4 backend: {backend}")
    successful = sum(
        _result_complete(raw_dir / f"{spec['experiment_id']}.json.gz", spec)
        for spec in specs
    )
    return {
        "phase": phase,
        "expected": len(specs),
        "pending_at_start": len(pending),
        "successful": successful,
        "passed": successful == len(specs),
    }


R8R4_FORBIDDEN_TRACE_KEYS = tuple(
    dict.fromkeys(
        r8.R8_FORBIDDEN_TRACE_KEYS
        + (
            "r3c3t13s24d1r14r8r4_future_r17_executed",
            "r3c3t13s24d1r14r8r4_pair_or_history_label_used",
            "r3c3t13s24d1r14r8r4_partition_label_used",
            "r3c3t13s24d1r14r8r4_source_result_used",
        )
    )
)


def audit_raw_phase(ctx: Context, phase: str) -> dict[str, Any]:
    specs = _phase_specs(ctx, phase)
    raw_dir = ctx.paths.phase_raw(phase)
    sources = r8._source_baseline_results(ctx.r8_ctx)
    rows: list[dict[str, Any]] = []
    for spec in specs:
        experiment_id = str(spec["experiment_id"])
        path = raw_dir / f"{experiment_id}.json.gz"
        if not _result_complete(path, spec, success=False):
            rows.append(
                {
                    "experiment_id": experiment_id,
                    "runtime_success": False,
                    "passed": False,
                    "failure_class": "runtime_or_raw_error",
                }
            )
            continue
        result = r8._read_gz(path)
        trajectory = result.get("trajectory") or []
        trace = result.get("controller_trace") or []
        source = sources[str(spec["source_s21_baseline_experiment_id"])]
        horizon = int(spec["horizon_steps"])
        full = len(trajectory) == horizon + 1 and len(trace) == horizon
        prefix_state = bool(
            len(trajectory) >= 11
            and all(
                r8.r4._semantic_state(current) == r8.r4._semantic_state(reference)
                for current, reference in zip(trajectory[:11], source["trajectory"][:11])
            )
        )
        prefix_trace = bool(
            len(trace) >= 10
            and all(
                r8.r4._source_trace_projection(reference, current)
                for current, reference in zip(
                    trace[:10], source["controller_trace"][:10]
                )
            )
        )
        calibration = r8.r4._calibration_exact(trace)
        actions = np.asarray(
            [row.get("action_norm_tsc", []) for row in trace], dtype=float
        )
        currents = np.asarray(
            [row.get("currents_a_tsc", []) for row in trajectory], dtype=float
        )
        wires = [
            np.asarray(row.get("wire_currents_a", []), dtype=float)
            for row in trajectory
        ]
        finite = bool(
            full
            and actions.shape == (horizon, 14)
            and currents.shape == (horizon + 1, 14)
            and np.all(np.isfinite(actions))
            and np.all(np.isfinite(currents))
            and all(value.size and np.all(np.isfinite(value)) for value in wires)
            and all(
                math.isfinite(float(row[key]))
                for row in trajectory
                for key in ("R", "Z", "Ip")
            )
            and not any(bool(row.get("abnormal")) for row in trajectory)
        )
        zero_future_action = bool(
            full and np.array_equal(actions[10:], np.zeros_like(actions[10:]))
        )
        constant_future_current = bool(
            full
            and np.array_equal(
                np.diff(currents[10:], axis=0),
                np.zeros_like(np.diff(currents[10:], axis=0)),
            )
        )
        forbidden = sum(
            any(bool(row.get(key)) for key in R8R4_FORBIDDEN_TRACE_KEYS)
            for row in trace
        )
        payload = _read(ctx.paths.variants / f"payload_{experiment_id}.json")
        minimum, maximum = r8.d1r11.s21.s13._current_limits_tsc(payload)
        center, half = 0.5 * (minimum + maximum), 0.5 * (maximum - minimum)
        utilization = (
            float(np.max(np.abs((currents - center) / half)))
            if currents.shape == (horizon + 1, 14)
            else math.inf
        )
        action_abs = (
            float(np.max(np.abs(actions))) if actions.shape == (horizon, 14) else math.inf
        )
        source_snapshot = bool(
            str(spec.get("restart_snapshot_dir") or "")
            and str(spec.get("restart_snapshot_manifest_digest") or "")
            and payload.get("stage4_2r3c3t13s24d1r14r8_snapshot_manifest_digest")
            == spec.get("restart_snapshot_manifest_digest")
        )
        passed = bool(
            result.get("success")
            and full
            and prefix_state
            and prefix_trace
            and calibration
            and finite
            and zero_future_action
            and constant_future_current
            and source_snapshot
            and forbidden == 0
            and action_abs
            <= float(ctx.cfg["controller_contract"]["maximum_total_normalized_action_abs"])
            + 1e-12
            and utilization
            <= float(ctx.cfg["controller_contract"]["maximum_current_utilization"])
            + 1e-12
        )
        rows.append(
            {
                "experiment_id": experiment_id,
                "pair_id": spec["pair_id"],
                "history_member": spec["history_member"],
                "runtime_success": bool(result.get("success")),
                "execution_failure_class": str(
                    result.get("execution_failure_class") or ""
                ),
                "full_horizon": full,
                "source_prefix_state_exact": prefix_state,
                "source_prefix_trace_exact": prefix_trace,
                "calibration_exact": calibration,
                "zero_future_action_exact": zero_future_action,
                "constant_future_commanded_current_exact": constant_future_current,
                "source_restart_snapshot_authenticated": source_snapshot,
                "finite": finite,
                "forbidden_trace_count": forbidden,
                "maximum_total_normalized_action_abs": action_abs,
                "maximum_current_utilization": utilization,
                "failure_reason": str(result.get("failure_reason") or ""),
                "passed": passed,
            }
        )
    inventory = r8._inventory(raw_dir)
    report = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "phase": phase,
        "expected_raw_count": 8,
        "raw_inventory": inventory,
        "runtime_success_count": sum(bool(row.get("runtime_success")) for row in rows),
        "full_horizon_count": sum(bool(row.get("full_horizon")) for row in rows),
        "source_prefix_state_exact_count": sum(
            bool(row.get("source_prefix_state_exact")) for row in rows
        ),
        "source_prefix_trace_exact_count": sum(
            bool(row.get("source_prefix_trace_exact")) for row in rows
        ),
        "zero_future_action_exact_count": sum(
            bool(row.get("zero_future_action_exact")) for row in rows
        ),
        "constant_future_commanded_current_exact_count": sum(
            bool(row.get("constant_future_commanded_current_exact")) for row in rows
        ),
        "source_restart_snapshot_authenticated_count": sum(
            bool(row.get("source_restart_snapshot_authenticated")) for row in rows
        ),
        "finite_count": sum(bool(row.get("finite")) for row in rows),
        "forbidden_trace_count": sum(int(row.get("forbidden_trace_count", 0)) for row in rows),
        "maximum_total_normalized_action_abs": max(
            (float(row.get("maximum_total_normalized_action_abs", math.inf)) for row in rows),
            default=math.inf,
        ),
        "maximum_current_utilization": max(
            (float(row.get("maximum_current_utilization", math.inf)) for row in rows),
            default=math.inf,
        ),
        "passed_count": sum(bool(row.get("passed")) for row in rows),
        "rows": rows,
    }
    report["passed"] = bool(
        inventory["count"] == 8 and len(rows) == 8 and report["passed_count"] == 8
    )
    report["route"] = ctx.cfg["routes"][
        "pass" if report["passed"] else f"{phase}_execution_fail"
    ]
    _write(ctx.paths.analysis / f"{phase}_raw_primary.json", report)
    return report


def run_phase(ctx: Context, phase: str, *, backend: str, resume: bool) -> dict[str, Any]:
    expected = {"development": "offline_ready", "holdout": "holdout_authorized"}[phase]
    _require(ctx, expected)
    if phase == "development" and any(ctx.paths.phase_raw("holdout").glob("*.json.gz")):
        raise ValueError("R8R4 holdout raw opened before development freeze")
    specs = _phase_specs(ctx, phase)
    execution = evaluate_specs(ctx, specs, phase=phase, backend=backend, resume=resume)
    primary = audit_raw_phase(ctx, phase)
    total = sum(r8._inventory(ctx.paths.phase_raw(name))["count"] for name in PHASES)
    if not execution["passed"] or not primary["passed"]:
        route = ctx.cfg["routes"][f"{phase}_execution_fail"]
        _set_state(
            ctx,
            phase_status=f"{phase}_execution_failed",
            finished=True,
            real_tsc_executed=total > 0,
            new_raw_count=total,
            holdout_outcomes_opened=phase == "holdout",
            stop_reason=f"{phase}_runtime_restart_action_current_or_raw_gate_failed",
            verdict={"route": route, "passed": False},
        )
    else:
        _set_state(
            ctx,
            phase_status=f"{phase}_raw_primary_passed",
            real_tsc_executed=True,
            new_raw_count=total,
            holdout_outcomes_opened=phase == "holdout",
            **{f"{phase}_raw_inventory_digest": primary["raw_inventory"]["digest"]},
        )
    return {
        "execution": execution,
        "primary_raw_audit": {key: value for key, value in primary.items() if key != "rows"},
    }


def _prior_rows(ctx: Context) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    r8r3_cfg = _read((_root() / str(ctx.cfg["source_r8r3_config"])).resolve())
    r8r2_config = (_root() / str(r8r3_cfg["source_r8r2_config"])).resolve()
    r8r2_cfg = _read(r8r2_config)
    r8r1_config = (_root() / str(r8r2_cfg["source_r8r1_config"])).resolve()
    r8r1_cfg = _read(r8r1_config)
    source_items, _, _, _ = r8r1_primary._source_items(
        r8r1_cfg,
        r8r1_config,
        ctx.r8_run,
        ctx.source_r2_run,
        ctx.source_r4_run,
        ctx.source_r6_run,
    )
    rows, signature = r8r3_primary._build_rows_and_probe_audit(
        r8r3_cfg,
        r8r2_cfg,
        r8r1_cfg,
        ctx.r8_cfg,
        ctx.r8_config_path,
        ctx.r8_run,
        ctx.source_r2_run,
        ctx.source_r4_run,
        ctx.source_r6_run,
        source_items,
    )
    if len({str(row["pair_id"]) for row in rows}) != 12:
        raise ValueError("R8R4 prior observer pair coverage changed")
    return rows, signature


def _fresh_rows(ctx: Context, phase: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    specs = _phase_specs(ctx, phase)
    scales = np.asarray(ctx.cfg["bank_contract"]["visible_scales"], dtype=float)
    prescribed = set(map(int, ctx.cfg["bank_contract"]["prescribed_issue_task_steps"]))
    rows: list[dict[str, Any]] = []
    raw_hashes: dict[str, str] = {}
    for spec in specs:
        path = ctx.paths.phase_raw(phase) / f"{spec['experiment_id']}.json.gz"
        if not _result_complete(path, spec):
            raise ValueError(f"R8R4 {phase} raw incomplete before row construction")
        result = r8._read_gz(path)
        visible = r7_source._visible(result["trajectory"], scales)
        actions = r8r3_primary._actions(result)
        currents = r8r3_primary._currents(result)
        maximum = len(visible) - 1 - int(ctx.cfg["bank_contract"]["future_state_count"])
        for origin in range(int(ctx.cfg["bank_contract"]["first_origin_task_step"]), maximum + 1):
            feature = observer.causal_feature(
                visible[: origin + 1],
                actions[:origin],
                currents[: origin + 1],
                r8r3_primary._target(spec),
                origin,
                ctx.cfg,
            )
            rows.append(
                {
                    "row_id": (
                        f"{phase}|{spec['pair_id']}|{spec['history_member']}|"
                        f"origin{origin:02d}"
                    ),
                    "context_id": f"{spec['pair_id']}|{spec['history_member']}",
                    "pair_id": str(spec["pair_id"]),
                    "history_member": str(spec["history_member"]),
                    "origin_task_step": origin,
                    "prescribed_issue": origin in prescribed,
                    "source_baseline_experiment_id": str(spec["experiment_id"]),
                    "feature": feature,
                    "origin_visible": visible[origin],
                    "target_delta": observer.target_delta(visible, origin, ctx.cfg),
                    "future_visible": visible[origin + 1 : origin + 13],
                }
            )
        raw_hashes[str(spec["experiment_id"])] = _sha(path)
    pairs = sorted({str(row["pair_id"]) for row in rows})
    contexts = sorted({str(row["context_id"]) for row in rows})
    issues = sum(bool(row["prescribed_issue"]) for row in rows)
    if (
        len(pairs) != 4
        or len(contexts) != 8
        or issues != 32
        or any(len(np.asarray(row["feature"])) != 353 for row in rows)
    ):
        raise ValueError(f"R8R4 {phase} causal row coverage changed")
    signature = {
        "phase": phase,
        "pair_count": len(pairs),
        "context_count": len(contexts),
        "origin_row_count": len(rows),
        "prescribed_issue_row_count": issues,
        "feature_dimension": 353,
        "raw_sha256": raw_hashes,
        "forbidden_predictor_input_count": 0,
        "future_input_count": 0,
        "allowed_in_expert_dataset": False,
    }
    return sorted(rows, key=lambda row: row["row_id"]), signature


def _point_evaluation(rows: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> dict[str, Any]:
    gates = cfg["gates"]
    issues = [row for row in rows if bool(row["prescribed_issue"])]

    def required(rate: float, total: int) -> int:
        return int(math.ceil(rate * total - 1e-15))

    contexts: dict[str, dict[str, Any]] = {}
    context_passed = True
    for pair, history in sorted(
        {(str(row["pair_id"]), str(row["history_member"])) for row in rows}
    ):
        current = [
            row
            for row in rows
            if str(row["pair_id"]) == pair and str(row["history_member"]) == history
        ]
        current_issues = [row for row in current if bool(row["prescribed_issue"])]
        count = sum(bool(row["passed"]) for row in current)
        issue_count = sum(bool(row["passed"]) for row in current_issues)
        need = required(float(gates["per_context_point_pass_rate"]), len(current))
        passed = bool(
            count >= need
            and issue_count >= int(gates["per_context_prescribed_issue_pass_count"])
        )
        context_passed = context_passed and passed
        contexts[f"{pair}|{history}"] = {
            "point_pass_count": count,
            "total": len(current),
            "required": need,
            "issue_point_pass_count": issue_count,
            "issue_total": len(current_issues),
            "issue_required": int(gates["per_context_prescribed_issue_pass_count"]),
            "passed": passed,
        }
    point_count = sum(bool(row["passed"]) for row in rows)
    issue_count = sum(bool(row["passed"]) for row in issues)
    point_need = required(float(gates["aggregate_point_pass_rate"]), len(rows))
    issue_need = required(float(gates["prescribed_issue_point_pass_rate"]), len(issues))
    exclusion = sum(int(row.get("finite_exclusion_violation_count", 0)) for row in rows)
    result = {
        "origin_row_count": len(rows),
        "origin_point_pass_count": point_count,
        "origin_point_required": point_need,
        "prescribed_issue_row_count": len(issues),
        "prescribed_issue_point_pass_count": issue_count,
        "prescribed_issue_point_required": issue_need,
        "finite_exclusion_violation_count": exclusion,
        "maximum_absolute_physical_error": np.max(
            np.asarray([row["absolute_residual_physical"] for row in rows]), axis=(0, 1)
        ).tolist(),
        "maximum_absolute_scaled_point_error": max(
            float(row["maximum_absolute_scaled_point_error"]) for row in rows
        ),
        "context_counts": contexts,
    }
    result["passed"] = bool(
        point_count >= point_need
        and issue_count >= issue_need
        and exclusion == 0
        and context_passed
    )
    return result


def _model_from_artifact(value: Mapping[str, Any]) -> dict[str, Any]:
    model = value["model"]
    candidate = observer.Candidate(**model["candidate"])
    output: dict[str, Any] = {
        "candidate": candidate,
        "preprocessor": {
            key: np.asarray(item, dtype=float)
            for key, item in model["preprocessor"].items()
        },
        "training_x": np.asarray(model["training_x"], dtype=float),
        "target_mean": np.asarray(model["target_mean"], dtype=float),
        "bandwidth": float(model["bandwidth"]),
    }
    output["beta" if candidate.family == "linear" else "alpha"] = np.asarray(
        model["beta" if candidate.family == "linear" else "alpha"], dtype=float
    )
    return output


def _independent(ctx: Context, name: str) -> dict[str, Any]:
    path = ctx.paths.analysis / f"{name}_independent.json"
    if not path.is_file():
        raise ValueError(f"R8R4 independent {name} audit missing")
    value = _read(path)
    if value.get("passed") is not True:
        raise ValueError(f"R8R4 independent {name} audit failed")
    return value


def fit_development(ctx: Context) -> dict[str, Any]:
    _require(ctx, "development_raw_primary_passed")
    primary_raw_path = ctx.paths.analysis / "development_raw_primary.json"
    primary_raw = _read(primary_raw_path)
    independent_raw = _independent(ctx, "development_raw")
    if (
        independent_raw.get("primary_sha256") != _sha(primary_raw_path)
        or independent_raw.get("raw_inventory") != primary_raw.get("raw_inventory")
    ):
        raise ValueError("R8R4 development raw audit disagreement")
    if any(ctx.paths.phase_raw("holdout").glob("*.json.gz")):
        raise ValueError("R8R4 holdout raw opened before model/tube freeze")
    prior, prior_signature = _prior_rows(ctx)
    fresh, fresh_signature = _fresh_rows(ctx, "development")
    items = sorted(prior + fresh, key=lambda row: row["row_id"])
    if len({str(row["pair_id"]) for row in items}) != 16:
        raise ValueError("R8R4 combined development pair coverage changed")

    outer_rows, folds = observer.nested_outer_predictions(items, ctx.cfg)
    outer_point = _point_evaluation(outer_rows, ctx.cfg)
    selected, scores, selected_oof_rows = observer.select_candidate(items, ctx.cfg)
    tube = observer.tube_from_rows(selected_oof_rows, ctx.cfg)
    tube_evaluation = observer.practical_evaluation(selected_oof_rows, tube, ctx.cfg)
    scientific = bool(
        len(folds) == int(ctx.cfg["gates"]["required_development_outer_fold_count"])
        and outer_point["passed"]
        and tube_evaluation["passed"]
    )
    model_sha = tube_sha = ""
    if scientific:
        fitted = observer.fit_model(items, selected, ctx.cfg)
        artifact = {
            "schema_version": 1,
            "stage": contract.STAGE,
            "campaign_identity": contract.IDENTITY,
            "feature_contract": ctx.cfg["feature_contract"],
            "bank_contract": ctx.cfg["bank_contract"],
            "training_pair_count": 16,
            "selected_candidate": selected.as_dict(),
            "source_r8_authentication_sha256": _sha(
                ctx.paths.source_reference / "r8_authentication.json"
            ),
            "source_r8r3_authentication_sha256": _sha(
                ctx.paths.source_reference / "r8r3_authentication.json"
            ),
            "model": observer.serializable_model(fitted, tube),
        }
        model_path = ctx.paths.model / "observer_model.json"
        tube_path = ctx.paths.model / "observer_tube.json"
        _write(model_path, artifact)
        _write(
            tube_path,
            {
                "schema_version": 1,
                "stage": contract.STAGE,
                "campaign_identity": contract.IDENTITY,
                "tube_physical": tube.tolist(),
                "derivation": "higher_quantile_scaled_whole_pair_oof",
                "selected_candidate": selected.as_dict(),
            },
        )
        model_sha = _sha(model_path)
        tube_sha = _sha(tube_path)
    route = ctx.cfg["routes"]["pass" if scientific else "development_model_fail"]
    detailed = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "phase": "development_nested_whole_pair_and_artifact_freeze",
        "prior_signature": prior_signature,
        "fresh_signature": fresh_signature,
        "combined_pair_count": 16,
        "combined_origin_row_count": len(items),
        "outer_fold_count": len(folds),
        "outer_point_evaluation": outer_point,
        "outer_folds": folds,
        "outer_rows": outer_rows,
        "all_development_selected_candidate": selected.as_dict(),
        "all_development_candidate_scores": scores,
        "all_development_oof_tube_evaluation": tube_evaluation,
        "all_development_oof_rows": observer.apply_tube(selected_oof_rows, tube),
        "tube_physical": tube.tolist(),
        "observer_model_sha256": model_sha,
        "observer_tube_sha256": tube_sha,
        "holdout_raw_count": 0,
        "route": route,
        "scientific_gate_passed": scientific,
        "passed": True,
    }
    detailed_path = ctx.paths.analysis / "development_model_primary_detailed.json"
    _write(detailed_path, detailed)
    summary = {
        key: value
        for key, value in detailed.items()
        if key
        not in {
            "outer_folds",
            "outer_rows",
            "all_development_candidate_scores",
            "all_development_oof_rows",
        }
    }
    summary["primary_detailed_sha256"] = _sha(detailed_path)
    summary_path = ctx.paths.analysis / "development_model_primary_summary.json"
    _write(summary_path, summary)
    _set_state(
        ctx,
        phase_status="development_model_primary_complete",
        observer_model_sha256=model_sha,
        observer_tube_sha256=tube_sha,
        development_model_primary_summary_sha256=_sha(summary_path),
        development_scientific_gate_passed=scientific,
        verdict={"route": route, "passed": scientific},
    )
    return summary


def authorize_holdout(ctx: Context) -> dict[str, Any]:
    state = _require(ctx, "development_model_primary_complete")
    independent = _independent(ctx, "development_model")
    summary_path = ctx.paths.analysis / "development_model_primary_summary.json"
    summary = _read(summary_path)
    scientific = bool(state.get("development_scientific_gate_passed"))
    if (
        independent.get("primary_summary_sha256") != _sha(summary_path)
        or independent.get("scientific_gate_passed") is not scientific
        or independent.get("route") != summary.get("route")
        or independent.get("observer_model_sha256")
        != str(state.get("observer_model_sha256") or "")
        or independent.get("observer_tube_sha256")
        != str(state.get("observer_tube_sha256") or "")
        or any(ctx.paths.phase_raw("holdout").glob("*.json.gz"))
    ):
        raise ValueError("R8R4 independent development decision disagreement")
    if not scientific:
        route = ctx.cfg["routes"]["development_model_fail"]
        _set_state(
            ctx,
            phase_status="development_model_failed",
            finished=True,
            stop_reason="development_practical_point_or_tube_gate_failed",
            verdict={"route": route, "passed": False},
        )
        return {"stage": contract.STAGE, "authorized": False, "route": route}
    model_path = ctx.paths.model / "observer_model.json"
    tube_path = ctx.paths.model / "observer_tube.json"
    if (
        _sha(model_path) != state["observer_model_sha256"]
        or _sha(tube_path) != state["observer_tube_sha256"]
    ):
        raise ValueError("R8R4 frozen model or tube hash changed")
    _set_state(ctx, phase_status="holdout_authorized")
    return {
        "stage": contract.STAGE,
        "authorized": True,
        "observer_model_sha256": state["observer_model_sha256"],
        "observer_tube_sha256": state["observer_tube_sha256"],
        "holdout_raw_count": 0,
    }


def finalize_holdout(ctx: Context) -> dict[str, Any]:
    state = _require(ctx, "holdout_raw_primary_passed")
    primary_raw_path = ctx.paths.analysis / "holdout_raw_primary.json"
    primary_raw = _read(primary_raw_path)
    independent_raw = _independent(ctx, "holdout_raw")
    if (
        independent_raw.get("primary_sha256") != _sha(primary_raw_path)
        or independent_raw.get("raw_inventory") != primary_raw.get("raw_inventory")
    ):
        raise ValueError("R8R4 holdout raw audit disagreement")
    model_path = ctx.paths.model / "observer_model.json"
    tube_path = ctx.paths.model / "observer_tube.json"
    if (
        _sha(model_path) != state["observer_model_sha256"]
        or _sha(tube_path) != state["observer_tube_sha256"]
    ):
        raise ValueError("R8R4 model/tube changed before holdout scoring")
    artifact = _read(model_path)
    tube_value = _read(tube_path)
    tube = np.asarray(tube_value["tube_physical"], dtype=float)
    model = _model_from_artifact(artifact)
    items, signature = _fresh_rows(ctx, "holdout")
    predictions = observer.predict_model(model, items, ctx.cfg)
    rows = [
        observer.prediction_row(item, prediction, ctx.cfg)
        for item, prediction in zip(items, predictions)
    ]
    evaluation = observer.practical_evaluation(rows, tube, ctx.cfg)
    coverage = bool(
        len({str(row["pair_id"]) for row in rows})
        == int(ctx.cfg["gates"]["required_holdout_pair_count"])
        and len(
            {(str(row["pair_id"]), str(row["history_member"])) for row in rows}
        )
        == int(ctx.cfg["gates"]["required_holdout_context_count"])
        and sum(bool(row["prescribed_issue"]) for row in rows)
        == int(ctx.cfg["gates"]["required_holdout_prescribed_issue_row_count"])
    )
    scientific = bool(coverage and evaluation["passed"])
    route = ctx.cfg["routes"]["pass" if scientific else "holdout_model_fail"]
    detailed = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "phase": "blind_holdout_fixed_model_and_tube",
        "holdout_signature": signature,
        "holdout_coverage_passed": coverage,
        "holdout_evaluation": evaluation,
        "observer_model_sha256": state["observer_model_sha256"],
        "observer_tube_sha256": state["observer_tube_sha256"],
        "route": route,
        "scientific_gate_passed": scientific,
        "heldout_outcomes_opened": True,
        "new_raw_count": 16,
        "all_stage_trajectories_allowed_in_expert_dataset": False,
        "mpc_validated": False,
        "gate_a_qualified": False,
        "bc_dagger_or_rl_allowed": False,
        "passed": True,
    }
    detailed_path = ctx.paths.analysis / "holdout_model_primary_detailed.json"
    _write(detailed_path, detailed)
    summary = dict(detailed)
    summary["holdout_evaluation"] = {
        key: value for key, value in evaluation.items() if key != "rows"
    }
    summary["primary_detailed_sha256"] = _sha(detailed_path)
    summary_path = ctx.paths.analysis / "holdout_model_primary_summary.json"
    _write(summary_path, summary)
    _set_state(
        ctx,
        phase_status="holdout_model_primary_complete",
        holdout_model_primary_summary_sha256=_sha(summary_path),
        holdout_scientific_gate_passed=scientific,
        verdict={"route": route, "passed": scientific},
    )
    return summary


def postprocess(ctx: Context) -> dict[str, Any]:
    state = _require(ctx, "holdout_model_primary_complete")
    independent = _independent(ctx, "holdout_model")
    summary_path = ctx.paths.analysis / "holdout_model_primary_summary.json"
    summary = _read(summary_path)
    scientific = bool(state.get("holdout_scientific_gate_passed"))
    if (
        independent.get("primary_summary_sha256") != _sha(summary_path)
        or independent.get("scientific_gate_passed") is not scientific
        or independent.get("route") != summary.get("route")
        or independent.get("observer_model_sha256") != state.get("observer_model_sha256")
        or independent.get("observer_tube_sha256") != state.get("observer_tube_sha256")
    ):
        raise ValueError("R8R4 independent holdout decision disagreement")
    inventories = {phase: r8._inventory(ctx.paths.phase_raw(phase)) for phase in PHASES}
    if any(value["count"] != 8 for value in inventories.values()):
        raise ValueError("R8R4 final raw inventory changed")
    route = str(summary["route"])
    final = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "phase": "final_dual_audit",
        "route": route,
        "scientific_gate_passed": scientific,
        "raw_inventories": inventories,
        "observer_model_sha256": state["observer_model_sha256"],
        "observer_tube_sha256": state["observer_tube_sha256"],
        "primary_summary_sha256": _sha(summary_path),
        "independent_sha256": _sha(
            ctx.paths.analysis / "holdout_model_independent.json"
        ),
        "new_raw_count": 16,
        "heldout_outcomes_opened": True,
        "all_stage_trajectories_allowed_in_expert_dataset": False,
        "passed": True,
    }
    final_path = ctx.paths.analysis / "final_report.json"
    _write(final_path, final)
    _set_state(
        ctx,
        phase_status="complete",
        finished=True,
        final_report_sha256=_sha(final_path),
        independent_holdout_model_sha256=final["independent_sha256"],
        stop_reason="" if scientific else "blind_holdout_point_or_tube_gate_failed",
        verdict={"route": route, "passed": scientific},
    )
    return final


def execute(
    ctx: Context, *, command: str, backend: str, resume: bool
) -> dict[str, Any]:
    if command == "offline":
        return prepare_offline(ctx)
    if command in PHASES:
        return run_phase(ctx, command, backend=backend, resume=resume)
    if command == "fit-development":
        return fit_development(ctx)
    if command == "authorize-holdout":
        return authorize_holdout(ctx)
    if command == "finalize":
        return finalize_holdout(ctx)
    if command == "postprocess":
        return postprocess(ctx)
    raise ValueError(f"unsupported R8R4 command: {command}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--r8-run", type=Path, required=True)
    parser.add_argument("--r8r3-output", type=Path, required=True)
    parser.add_argument("--source-d1r11-run", type=Path, required=True)
    parser.add_argument("--source-r2-run", type=Path, required=True)
    parser.add_argument("--source-r4-run", type=Path, required=True)
    parser.add_argument("--source-r6-run", type=Path, required=True)
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
    parser.add_argument(
        "--command",
        choices=(
            "offline",
            "development",
            "fit-development",
            "authorize-holdout",
            "holdout",
            "finalize",
            "postprocess",
        ),
        required=True,
    )
    parser.add_argument("--backend", choices=("serial", "ray"), default="ray")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    return parser


def main() -> None:
    parser = _parser()
    args = parser.parse_args()
    if args.self_test:
        print(
            json.dumps(
                contract.self_test(args.config),
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
        )
        return
    ctx = load_context(args)
    result = execute(ctx, command=args.command, backend=args.backend, resume=args.resume)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
