"""Stage4.2R3c3T13S24D1R14R8R28 front-loaded timing sentinel."""
from __future__ import annotations

import argparse
import contextlib
import copy
import hashlib
import json
import math
import os
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r14_cumulative_multidirection_staircase_authority_identification as r14,
    stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_campaign as r8r7,
    stage4_2r3c3t13s24d1r14r8r9_measured_multipulse_authority_audit as r8r9,
    stage4_2r3c3t13s24d1r14r8r11_sustained_exact_target_refresh_authority_sentinel as r8r11,
)


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S24D1R14R8R28"
IDENTITY = "front_loaded_cumulative_endpoint_timing_authority_sentinel_v1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r28_front_loaded_cumulative_endpoint_timing_authority_sentinel"
CONTROLLER_REVISION = "front_loaded_cumulative_endpoint_timing_v42r3c3t13s24d1r14r8r28_v1"
PHASES = ("safety", "qualification")
PREFIX_END = 10
N_COILS = 14


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


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _matrix_digest(value: Sequence[Sequence[float]]) -> str:
    return hashlib.sha256(
        np.ascontiguousarray(np.asarray(value, dtype="<f8")).tobytes(order="C")
    ).hexdigest()


@dataclass(frozen=True)
class Paths:
    run_dir: Path
    stage: Path
    variants: Path
    specs: Path
    source_reference: Path
    raw: Path
    analysis: Path
    state: Path
    manifest: Path

    def phase_raw(self, phase: str) -> Path:
        if phase not in PHASES:
            raise ValueError(phase)
        return self.raw / phase


def _paths(run_dir: Path) -> Paths:
    root = run_dir.expanduser().resolve()
    stage = root / RUN_NAME
    return Paths(
        run_dir=root,
        stage=stage,
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
    paths: Paths
    r8r7_run: Path
    r8r14_run: Path
    r8r27_run: Path
    source_ctx: r8r7.Context


def validate_config(cfg: Mapping[str, Any], *, project_root: Path) -> None:
    contexts = cfg["context_contract"]
    schedule = cfg["schedule_contract"]
    controller = cfg["controller_contract"]
    formal = cfg["formal_contract"]
    gate = cfg["scientific_gate"]
    scope = cfg["scientific_scope"]
    grids = [
        (str(row["grid_id"]), tuple(map(int, row["decision_task_steps"])))
        for row in schedule["timing_grids"]
    ]
    endpoints = [
        (str(row["sequence_id"]), int(row["direction_index"]), int(row["sign"]))
        for row in schedule["endpoint_sequences"]
    ]
    design = project_root / str(cfg["design_document"])
    if (
        int(cfg.get("schema_version", -1)) != 1
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("run_name") != RUN_NAME
        or cfg.get("controller_revision") != CONTROLLER_REVISION
        or not design.is_file()
        or _sha(design) != str(cfg["design_document_sha256"])
        or tuple(contexts["histories"]) != ("minus_first", "plus_first")
        or tuple(contexts["ordered_pairs"])
        != (
            "p5_q1_a0p900_gap3_settle4",
            "p5_q2_a0p750_gap3_settle4",
            "p9_q1_a0p900_gap3_settle4",
            "p9_q2_a0p750_gap3_settle4",
            "p5_q1_a0p750_gap4_settle4",
            "p5_q2_a0p900_gap4_settle4",
            "p9_q1_a0p750_gap4_settle4",
            "p9_q2_a0p900_gap4_settle4",
        )
        or tuple(contexts["safety_pairs"]) != tuple(contexts["ordered_pairs"][:2])
        or (
            int(contexts["context_count"]),
            int(contexts["safety_context_count"]),
            int(contexts["qualification_context_count"]),
        ) != (16, 4, 12)
        or grids != [("g3", (10, 13, 16, 19)), ("g2", (10, 12, 14, 16))]
        or endpoints != [("UUUU", 2, 1), ("VVVV", 1, -1)]
        or float(schedule["canonical_scale"]) != 1.0
        or np.asarray(schedule["canonical_matrix_columns"], dtype=float).shape != (4, 4)
        or _matrix_digest(schedule["canonical_matrix_columns"])
        != str(schedule["canonical_matrix_float64_le_c_sha256"])
        or int(schedule["dynamic_exact_search_radius"]) != 16
        or (
            int(schedule["safety_spec_count"]),
            int(schedule["qualification_spec_count"]),
            int(schedule["total_spec_count"]),
            int(schedule["issue_count"]),
            int(schedule["refresh_count"]),
            int(schedule["level_count_per_spec"]),
        ) != (16, 48, 64, 256, 1408, 4)
        or int(controller["delegated_last_task_step"]) != 9
        or (
            float(controller["maximum_incremental_normalized_action_linf"]),
            float(controller["maximum_total_normalized_action_abs"]),
            float(controller["maximum_current_utilization"]),
            float(controller["minimum_desired_applied_current_cosine"]),
            float(controller["maximum_relative_off_basis_residual"]),
        ) != (0.25, 1.0, 0.55, 0.98, 0.10)
        or not all(
            bool(controller[key])
            for key in (
                "require_exact_card15_issue",
                "require_exact_card15_refresh",
                "require_exact_source_prefix",
                "forbid_future_r17_controller_execution",
                "safe_stop_before_failed_advance",
            )
        )
        or (
            int(formal["normal_arrival_deadline_step"]),
            int(formal["normal_hold_through_step"]),
            int(formal["weak_arrival_deadline_step"]),
            int(formal["weak_hold_through_step"]),
            float(formal["position_tolerance_m"]),
            float(formal["speed_tolerance_m_per_s"]),
            float(formal["ip_tolerance_A"]),
            int(formal["arrival_streak_steps"]),
        ) != (25, 35, 27, 37, 0.03, 0.1, 10000.0, 3)
        or float(formal["metric_equivalence_absolute_tolerance"]) != 1e-12
        or bool(formal["arrival_deadline_expansion_allowed"])
        or (
            int(gate["required_baseline_formal_pass_count"]),
            int(gate["required_failed_baseline_count"]),
            int(gate["minimum_repaired_failed_baseline_count"]),
            int(gate["minimum_held_oracle_formal_pass_count"]),
        ) != (6, 10, 1, 7)
        or not bool(gate["require_held_oracle_strictly_improves_baseline"])
        or not bool(scope["real_timing_authority_sentinel_only"])
        or any(
            bool(scope[key])
            for key in (
                "held_oracle_is_causal_selector",
                "real_mpc_executed",
                "gate_a_qualified",
                "all_stage_trajectories_allowed_in_expert_dataset",
                "expert_data_allowed",
                "bc_dagger_or_rl_allowed",
                "global_plant_reachability_claimed",
            )
        )
    ):
        raise ValueError("R8R28 frozen design changed")


def load_context(args: argparse.Namespace) -> Context:
    config_path = args.config.expanduser().resolve()
    cfg = _read(config_path)
    validate_config(cfg, project_root=_root())
    source_args = argparse.Namespace(**vars(args))
    source_args.config = (_root() / str(cfg["source_r8r7_config"])).resolve()
    source_args.run_dir = args.r8r7_run.expanduser().resolve()
    source_ctx = r8r7.load_context(source_args)
    return Context(
        cfg=cfg,
        config_path=config_path,
        paths=_paths(args.run_dir),
        r8r7_run=args.r8r7_run.expanduser().resolve(),
        r8r14_run=args.r8r14_run.expanduser().resolve(),
        r8r27_run=args.r8r27_run.expanduser().resolve(),
        source_ctx=source_ctx,
    )


def _source_stage(ctx: Context) -> Path:
    return ctx.r8r7_run / str(ctx.cfg["source_r8r7"]["stage_directory"])


def _r8r14_stage(ctx: Context) -> Path:
    return ctx.r8r14_run / str(ctx.cfg["source_r8r14"]["stage_directory"])


def _r8r27_stage(ctx: Context) -> Path:
    return ctx.r8r27_run / str(ctx.cfg["source_r8r27"]["stage_directory"])


def _authenticate_r8r14(ctx: Context) -> dict[str, Any]:
    stage, expected = _r8r14_stage(ctx), ctx.cfg["source_r8r14"]
    paths = {
        "primary_detailed": stage / "analysis/primary_detailed.json",
        "primary_summary": stage / "analysis/primary_summary.json",
        "final_independent": stage / "analysis/final_independent.json",
        "final_report": stage / "analysis/final_report.json",
        "manifest": stage / "stage_manifest.json",
        "state": stage / "stage_state.json",
    }
    hashes = {key: _sha(path) for key, path in paths.items()}
    for key in hashes:
        expected_key = "stage_manifest_sha256" if key == "manifest" else (
            "stage_state_sha256" if key == "state" else f"{key}_sha256"
        )
        if hashes[key] != str(expected[expected_key]):
            raise ValueError(f"R8R28 R8R14 {key} changed")
    if _sha(stage / "specs/all_specs.json") != str(expected["all_specs_sha256"]):
        raise ValueError("R8R28 R8R14 specs changed")
    inventories = {phase: r8r7.r8._inventory(stage / "raw" / phase) for phase in PHASES}
    for phase, inventory in inventories.items():
        if (
            inventory["count"] != int(expected[f"{phase}_raw_count"])
            or inventory["bytes"] != int(expected[f"{phase}_raw_bytes"])
            or inventory["digest"] != str(expected[f"{phase}_raw_digest"])
        ):
            raise ValueError(f"R8R28 R8R14 {phase} raw changed")
    final, state = _read(paths["final_report"]), _read(paths["state"])
    passed = bool(
        final.get("route") == expected["required_route"]
        and final.get("passed") is False
        and state.get("finished") is True
        and state.get("real_tsc_executed") is True
        and int(state.get("new_raw_count", -1)) == 112
    )
    if not passed:
        raise ValueError("R8R28 R8R14 result changed")
    return {"stage": str(stage), "hashes": hashes, "inventories": inventories, "passed": True}


def _authenticate_r8r27(ctx: Context) -> dict[str, Any]:
    stage, expected = _r8r27_stage(ctx), ctx.cfg["source_r8r27"]
    paths = {
        "primary_detailed": stage / "analysis/primary_detailed.json",
        "primary_summary": stage / "analysis/primary_summary.json",
        "independent": stage / "analysis/independent.json",
        "final_report": stage / "analysis/final_report.json",
        "manifest": stage / "stage_manifest.json",
        "state": stage / "stage_state.json",
    }
    hashes = {key: _sha(path) for key, path in paths.items()}
    for key in hashes:
        expected_key = "stage_manifest_sha256" if key == "manifest" else (
            "stage_state_sha256" if key == "state" else f"{key}_sha256"
        )
        if hashes[key] != str(expected[expected_key]):
            raise ValueError(f"R8R28 R8R27 {key} changed")
    final, state = _read(paths["final_report"]), _read(paths["state"])
    passed = bool(
        final.get("route") == expected["required_route"]
        and final.get("passed") is True
        and final.get("point_authority_present") is False
        and final.get("real_tsc_executed") is False
        and state.get("finished") is True
        and int(state.get("new_raw_count", -1)) == 0
    )
    if not passed:
        raise ValueError("R8R28 R8R27 result changed")
    return {"stage": str(stage), "hashes": hashes, "passed": True}


def _source_baselines(ctx: Context):
    return r14._source_baselines(ctx)


def build_specs(ctx: Context) -> list[dict[str, Any]]:
    baselines, _ = _source_baselines(ctx)
    safety = set(map(str, ctx.cfg["context_contract"]["safety_pairs"]))
    schedule = ctx.cfg["schedule_contract"]
    output = []
    for index, source in enumerate(baselines):
        phase = "safety" if str(source["pair_id"]) in safety else "qualification"
        for grid in schedule["timing_grids"]:
            grid_id = str(grid["grid_id"])
            decisions = list(map(int, grid["decision_task_steps"]))
            for endpoint in schedule["endpoint_sequences"]:
                sequence = str(endpoint["sequence_id"])
                direction, sign = int(endpoint["direction_index"]), int(endpoint["sign"])
                requested = np.asarray(schedule["canonical_matrix_columns"], dtype=float)[:, direction] * sign
                spec = copy.deepcopy(source)
                spec.update(
                    {
                        "kind": "stage4_2r3c3t13s24d1r14r8r28_front_loaded_timing",
                        "stage": STAGE,
                        "campaign_identity": IDENTITY,
                        "controller_revision": CONTROLLER_REVISION,
                        "partition": phase,
                        "experiment_id": f"r8r28_{phase}_{index:02d}_{grid_id}_{sequence.lower()}",
                        "source_r8r7_baseline_experiment_id": str(source["experiment_id"]),
                        "r8r28_role": "front_loaded_cumulative_endpoint_timing",
                        "r8r28_grid_id": grid_id,
                        "r8r28_sequence_id": sequence,
                        "r8r28_direction_index": direction,
                        "r8r28_sign": sign,
                        "r8r28_canonical_scale": 1.0,
                        "r8r28_requested_coordinate": requested.tolist(),
                        "r8r28_decision_task_steps": decisions,
                        "r8r28_allowed_in_expert_dataset": False,
                        # Reuse only the audited R8R14 low-level controller contract.
                        "r8r14_direction_index": direction,
                        "r8r14_sign": sign,
                        "r8r14_canonical_scale": 1.0,
                        "r8r14_requested_coordinate": requested.tolist(),
                        "r8r14_matrix_digest": str(schedule["canonical_matrix_float64_le_c_sha256"]),
                        "r8r14_decision_task_steps": decisions,
                        "pair_or_history_label_available_to_controller": False,
                        "source_result_available_to_controller": False,
                        "future_measurement_count": 0,
                        "future_action_count": 0,
                        "formal_timing_unchanged": True,
                    }
                )
                output.append(spec)
    counts = {phase: sum(row["partition"] == phase for row in output) for phase in PHASES}
    if counts != {"safety": 16, "qualification": 48} or len(output) != 64:
        raise ValueError("R8R28 frozen specification matrix changed")
    return output


def _payload(ctx: Context, spec: Mapping[str, Any]) -> dict[str, Any]:
    payload = r8r7.r8._payload(r14._execution_context(ctx), spec)
    experiment_id = str(spec["experiment_id"])
    payload.update(
        {
            "variant_id": f"stage4_2r3c3t13s24d1r14r8r28_{experiment_id}",
            "stage4_2r3c3t13s24d1r14r8r28_decision_task_steps": list(
                map(int, spec["r8r28_decision_task_steps"])
            ),
            "stage4_2r3c3t13s24d1r14r8r28_pair_history_label_available_to_controller": False,
        }
    )
    _write(ctx.paths.variants / f"payload_{experiment_id}.json", payload)
    return payload


def _saved_specs(ctx: Context) -> list[dict[str, Any]]:
    rows = _read(ctx.paths.specs / "all_specs.json")
    if rows != build_specs(ctx):
        raise ValueError("R8R28 saved specifications changed")
    return rows


def _phase_specs(ctx: Context, phase: str) -> list[dict[str, Any]]:
    rows = [row for row in _saved_specs(ctx) if row["partition"] == phase]
    if len(rows) != {"safety": 16, "qualification": 48}[phase]:
        raise ValueError("R8R28 saved phase coverage changed")
    return rows


def _set_state(ctx: Context, **updates: Any) -> dict[str, Any]:
    state = _read(ctx.paths.state)
    state.update(updates)
    _write(ctx.paths.state, state)
    return state


class _Worker(r14.LocalWorker):
    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        with _activated():
            return super().evaluate(spec)


_RAY_ACTOR = None


def _ray_actor_class():
    global _RAY_ACTOR
    if _RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class R8R28Actor:
            def __init__(self, *args: Any):
                self.worker = _Worker(*args)

            def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
                return self.worker.evaluate(spec)

            def close(self) -> bool:
                self.worker.close()
                return True

        _RAY_ACTOR = R8R28Actor
    return _RAY_ACTOR


@contextlib.contextmanager
def _activated():
    replacements = {
        "STAGE": STAGE,
        "IDENTITY": IDENTITY,
        "RUN_NAME": RUN_NAME,
        "CONTROLLER_REVISION": CONTROLLER_REVISION,
        "_payload": _payload,
        "_phase_specs": _phase_specs,
        "audit_raw_phase": audit_raw_phase,
        "LocalWorker": _Worker,
        "_ray_actor_class": _ray_actor_class,
    }
    old = {key: getattr(r14, key) for key in replacements}
    try:
        for key, value in replacements.items():
            setattr(r14, key, value)
        yield
    finally:
        for key, value in old.items():
            setattr(r14, key, value)


def prepare_offline(ctx: Context) -> dict[str, Any]:
    if ctx.paths.stage.exists():
        raise ValueError("R8R28 offline requires a fresh run identity")
    source_r8r7 = r8r9._authenticate_r8r7(_source_stage(ctx), ctx.cfg)
    source_r8r14 = _authenticate_r8r14(ctx)
    source_r8r27 = _authenticate_r8r27(ctx)
    lineage = {
        "r8": r8r7._authenticate_r8(ctx.source_ctx),
        "r8r1": r8r7._authenticate_r8r1(ctx.source_ctx),
        "r8r6": r8r7._authenticate_r8r6(ctx.source_ctx),
    }
    specs = build_specs(ctx)
    for path in (ctx.paths.stage, ctx.paths.variants, ctx.paths.specs, ctx.paths.source_reference, ctx.paths.analysis):
        path.mkdir(parents=True, exist_ok=True)
    for phase in PHASES:
        ctx.paths.phase_raw(phase).mkdir(parents=True, exist_ok=True)
    for spec in specs:
        _payload(ctx, spec)
    with _activated():
        preflight = r14._offline_construction(ctx, specs)
    preflight["passed"] = bool(
        preflight["spec_count"] == 64
        and preflight["level_construction_count"] == 256
        and preflight["level_construction_pass_count"] == 256
        and preflight["refresh_construction_count"] == 1408
        and preflight["refresh_construction_pass_count"] == 1408
        and all(row["passed"] for row in preflight["rows"])
    )
    if not preflight["passed"]:
        raise ValueError("R8R28 frozen timing construction preflight failed")
    _write(ctx.paths.specs / "all_specs.json", specs)
    for phase in PHASES:
        _write(ctx.paths.specs / f"{phase}_specs.json", [row for row in specs if row["partition"] == phase])
    _write(ctx.paths.source_reference / "r8r7_authentication.json", source_r8r7)
    _write(ctx.paths.source_reference / "r8r14_authentication.json", source_r8r14)
    _write(ctx.paths.source_reference / "r8r27_authentication.json", source_r8r27)
    _write(ctx.paths.source_reference / "lineage_authentication.json", lineage)
    _write(ctx.paths.analysis / "offline_timing_preflight.json", preflight)
    package = r8r7._package_fingerprint()
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": ctx.cfg["package_revision"],
        "config_path": str(ctx.config_path),
        "config_sha256": _sha(ctx.config_path),
        "design_document_sha256": ctx.cfg["design_document_sha256"],
        "source_r8r7_run": str(ctx.r8r7_run),
        "source_r8r14_run": str(ctx.r8r14_run),
        "source_r8r27_run": str(ctx.r8r27_run),
        "source_r8r7_authenticated": True,
        "source_r8r14_authenticated": True,
        "source_r8r27_authenticated": True,
        "lineage_authenticated": True,
        "spec_count": 64,
        "spec_digest": _digest(specs),
        "offline_preflight_digest": _digest(preflight),
        "package_fingerprint": package,
        "formal_timing_unchanged": True,
        "all_stage_trajectories_allowed_in_expert_dataset": False,
    }
    _write(ctx.paths.manifest, manifest)
    _write(
        ctx.paths.state,
        {
            "schema_version": 1,
            "stage": STAGE,
            "phase_status": "offline_primary_ready",
            "finished": False,
            "real_tsc_executed": False,
            "new_raw_count": 0,
            "formal_outcomes_opened": False,
            "qualification_outcomes_opened": False,
            "spec_digest": manifest["spec_digest"],
            "package_digest": package["digest"],
            "stop_reason": "",
            "verdict": {},
        },
    )
    report = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "offline_primary",
        "source_r8r7_authenticated": True,
        "source_r8r14_authenticated": True,
        "source_r8r27_authenticated": True,
        "lineage_authenticated": True,
        "spec_count": 64,
        "safety_spec_count": 16,
        "qualification_spec_count": 48,
        "level_construction_count": preflight["level_construction_count"],
        "level_construction_pass_count": preflight["level_construction_pass_count"],
        "refresh_construction_count": preflight["refresh_construction_count"],
        "refresh_construction_pass_count": preflight["refresh_construction_pass_count"],
        "maximum_issue_increment": preflight["maximum_issue_increment"],
        "maximum_refresh_increment": preflight["maximum_refresh_increment"],
        "maximum_predicted_current_utilization": preflight["maximum_predicted_current_utilization"],
        "new_raw_count": 0,
        "real_tsc_executed": False,
        "passed": True,
    }
    _write(ctx.paths.analysis / "offline_primary.json", report)
    return report


def _result_complete(path: Path, spec: Mapping[str, Any], *, require_success: bool = True) -> bool:
    with _activated():
        return r14._result_complete(path, spec, require_success=require_success)


def audit_raw_phase(ctx: Context, phase: str) -> dict[str, Any]:
    specs = _phase_specs(ctx, phase)
    _, sources = _source_baselines(ctx)
    contract = ctx.cfg["controller_contract"]
    rows = []
    for spec in specs:
        path = ctx.paths.phase_raw(phase) / f"{spec['experiment_id']}.json.gz"
        result = r8r7.r8._read_gz(path) if _result_complete(path, spec, require_success=False) else {}
        trajectory, trace = result.get("trajectory") or [], result.get("controller_trace") or []
        horizon = int(spec["horizon_steps"])
        full = len(trajectory) == horizon + 1 and len(trace) == horizon
        source = sources[str(spec["source_r8r7_baseline_experiment_id"])]
        prefix_state = bool(
            full
            and all(
                r8r7.r8.r4._semantic_state(current) == r8r7.r8.r4._semantic_state(reference)
                for current, reference in zip(trajectory[: PREFIX_END + 1], source["trajectory"][: PREFIX_END + 1])
            )
        )
        prefix_trace = bool(
            full
            and all(
                r14._source_trace_semantic_projection(reference, current)
                for current, reference in zip(trace[:PREFIX_END], source["controller_trace"][:PREFIX_END])
            )
        )
        calibration = bool(full and r8r7.r8.r4._calibration_exact(trace))
        decisions = set(map(int, spec["r8r28_decision_task_steps"]))
        names = [trace[step].get("r3c3t13s24d1r14r8r14_event") for step in range(PREFIX_END, horizon)] if full else []
        events = [trace[step].get("r3c3t13s24d1r14r8r14_event_detail") or {} for step in range(PREFIX_END, horizon)] if full else []
        event_exact = bool(
            full
            and all(
                name == ("staircase_issue" if step in decisions else "staircase_refresh")
                and event.get("passed") is True
                and all(bool(value) for value in (event.get("criteria") or {}).values())
                for step, name, event in zip(range(PREFIX_END, horizon), names, events)
            )
        )
        active_target = None
        target_chain = event_exact
        if event_exact:
            for name, event in zip(names, events):
                if name == "staircase_issue":
                    active_target = list(event.get("target_card15_fields") or [])
                elif list(event.get("stored_target_card15_fields") or []) != active_target:
                    target_chain = False
        actions = np.asarray([row.get("action_norm_tsc", []) for row in trace], dtype=float)
        currents = np.asarray([row.get("currents_a_tsc", []) for row in trajectory], dtype=float)
        finite = bool(
            full
            and actions.shape == (horizon, N_COILS)
            and currents.shape == (horizon + 1, N_COILS)
            and np.all(np.isfinite(actions))
            and np.all(np.isfinite(currents))
            and all(math.isfinite(float(row[key])) for row in trajectory for key in ("R", "Z", "Ip"))
            and not any(bool(row.get("abnormal")) for row in trajectory)
        )
        forbidden = sum(
            any(
                bool(row.get(key))
                for key in (
                    "r3c3t13s24d1r14r8r14_forbidden_input_used",
                    "r3c3t13s24d1r14r8r14_pair_or_history_label_used",
                    "r3c3t13s24d1r14r8r14_future_measurement_used",
                    "r3c3t13s24d1r14r8r14_future_action_used",
                    "r3c3t13s24d1r14r8r14_source_result_used",
                    "r3c3t13s24d1r14r8r14_hidden_wire_used",
                )
            )
            for row in trace
        )
        payload = _read(ctx.paths.variants / f"payload_{spec['experiment_id']}.json")
        minimum, maximum = r8r7.r8.d1r11.s21.s13._current_limits_tsc(payload)
        center, half = 0.5 * (minimum + maximum), 0.5 * (maximum - minimum)
        utilization = float(np.max(np.abs((currents - center) / half))) if currents.shape == (horizon + 1, N_COILS) else None
        issues = [event for name, event in zip(names, events) if name == "staircase_issue"]
        refreshes = [event for name, event in zip(names, events) if name == "staircase_refresh"]
        issue_increment = max((float(row["incremental_normalized_action_linf"]) for row in issues), default=None)
        refresh_increment = max((float(row["incremental_normalized_action_linf"]) for row in refreshes), default=None)
        passed = bool(
            result.get("success")
            and full
            and prefix_state
            and prefix_trace
            and calibration
            and event_exact
            and target_chain
            and len(issues) == 4
            and len(refreshes) == horizon - PREFIX_END - 4
            and finite
            and forbidden == 0
            and issue_increment is not None
            and issue_increment <= float(contract["maximum_incremental_normalized_action_linf"]) + 1e-12
            and refresh_increment is not None
            and refresh_increment <= float(contract["maximum_incremental_normalized_action_linf"]) + 1e-12
            and utilization is not None
            and utilization <= float(contract["maximum_current_utilization"]) + 1e-12
        )
        rows.append(
            {
                "experiment_id": spec["experiment_id"],
                "pair_id": spec["pair_id"],
                "history_member": spec["history_member"],
                "grid_id": spec["r8r28_grid_id"],
                "sequence_id": spec["r8r28_sequence_id"],
                "runtime_success": bool(result.get("success")),
                "full_horizon": full,
                "source_prefix_state_exact": prefix_state,
                "source_prefix_trace_exact": prefix_trace,
                "calibration_exact": calibration,
                "event_exact": event_exact,
                "target_chain_exact": target_chain,
                "issue_count": len(issues),
                "refresh_count": len(refreshes),
                "finite": finite,
                "forbidden_trace_count": forbidden,
                "maximum_issue_increment": issue_increment,
                "maximum_refresh_increment": refresh_increment,
                "maximum_current_utilization": utilization,
                "failure_reason": str(result.get("failure_reason") or ""),
                "passed": passed,
            }
        )
    inventory = r8r7.r8._inventory(ctx.paths.phase_raw(phase))
    expected = {"safety": 16, "qualification": 48}[phase]
    report = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": phase,
        "expected_raw_count": expected,
        "raw_inventory": inventory,
        "runtime_success_count": sum(bool(row["runtime_success"]) for row in rows),
        "full_horizon_count": sum(bool(row["full_horizon"]) for row in rows),
        "source_prefix_state_exact_count": sum(bool(row["source_prefix_state_exact"]) for row in rows),
        "source_prefix_trace_exact_count": sum(bool(row["source_prefix_trace_exact"]) for row in rows),
        "calibration_exact_count": sum(bool(row["calibration_exact"]) for row in rows),
        "event_exact_count": sum(bool(row["event_exact"]) for row in rows),
        "target_chain_exact_count": sum(bool(row["target_chain_exact"]) for row in rows),
        "issue_count": sum(int(row["issue_count"]) for row in rows),
        "refresh_count": sum(int(row["refresh_count"]) for row in rows),
        "finite_count": sum(bool(row["finite"]) for row in rows),
        "forbidden_trace_count": sum(int(row["forbidden_trace_count"]) for row in rows),
        "maximum_issue_increment": max((float(row["maximum_issue_increment"]) for row in rows if row["maximum_issue_increment"] is not None), default=None),
        "maximum_refresh_increment": max((float(row["maximum_refresh_increment"]) for row in rows if row["maximum_refresh_increment"] is not None), default=None),
        "maximum_current_utilization": max((float(row["maximum_current_utilization"]) for row in rows if row["maximum_current_utilization"] is not None), default=None),
        "passed_count": sum(bool(row["passed"]) for row in rows),
        "rows": rows,
    }
    report["passed"] = bool(inventory["count"] == expected and len(rows) == expected and report["passed_count"] == expected)
    report["route"] = ctx.cfg["routes"]["pass" if report["passed"] else "execution_fail"]
    _write(ctx.paths.analysis / f"{phase}_raw_primary.json", report)
    return report


def authorize_safety(ctx: Context) -> dict[str, Any]:
    with _activated():
        return r14.authorize_safety(ctx)


def run_phase(ctx: Context, phase: str, *, backend: str, resume: bool) -> dict[str, Any]:
    with _activated():
        return r14.run_phase(ctx, phase, backend=backend, resume=resume)


def authorize_qualification(ctx: Context) -> dict[str, Any]:
    with _activated():
        return r14.authorize_qualification(ctx)


def compute_formal_authority(ctx: Context) -> dict[str, Any]:
    specs = _saved_specs(ctx)
    baseline_specs, baseline_results = _source_baselines(ctx)
    evaluators, _ = r8r7.r8.d1r11._formal_callback(ctx.source_ctx.r8_ctx.d1r11_ctx, baseline_specs)
    evaluator_by_context = {
        (str(spec["pair_id"]), str(spec["history_member"])): evaluators[str(spec["experiment_id"])]
        for spec in baseline_specs
    }
    rows = []
    for spec in baseline_specs:
        rows.append(
            r8r11._formal_row(
                evaluators[str(spec["experiment_id"])],
                baseline_results[str(spec["experiment_id"])],
                {
                    "kind": "baseline",
                    "source": "R8R7",
                    "experiment_id": spec["experiment_id"],
                    "pair_id": spec["pair_id"],
                    "history_member": spec["history_member"],
                    "grid_id": "baseline",
                    "sequence_id": "baseline",
                },
            )
        )
    for spec in specs:
        result = r8r7.r8._read_gz(ctx.paths.phase_raw(str(spec["partition"])) / f"{spec['experiment_id']}.json.gz")
        rows.append(
            r8r11._formal_row(
                evaluator_by_context[(str(spec["pair_id"]), str(spec["history_member"]))],
                result,
                {
                    "kind": "candidate",
                    "source": "R8R28",
                    "experiment_id": spec["experiment_id"],
                    "pair_id": spec["pair_id"],
                    "history_member": spec["history_member"],
                    "grid_id": spec["r8r28_grid_id"],
                    "sequence_id": spec["r8r28_sequence_id"],
                },
            )
        )
    tolerance = float(ctx.cfg["formal_contract"]["metric_equivalence_absolute_tolerance"])
    equivalence = all(
        row["formal_contract_pass"] == row["existing_pass"]
        and row["formal_best_arrival_ms"] == row["existing_arrival_ms"]
        and float(row["maximum_margin_abs_difference"]) <= tolerance
        for row in rows
    )
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault((str(row["pair_id"]), str(row["history_member"])), []).append(row)
    expected_members = {("g3", "UUUU"), ("g3", "VVVV"), ("g2", "UUUU"), ("g2", "VVVV")}
    contexts = []
    for key, group in sorted(groups.items()):
        baseline = [row for row in group if row["kind"] == "baseline"]
        candidates = [row for row in group if row["kind"] == "candidate"]
        members = {(str(row["grid_id"]), str(row["sequence_id"])) for row in candidates}
        if len(baseline) != 1 or len(candidates) != 4 or members != expected_members:
            raise ValueError("R8R28 formal context coverage changed")
        base = baseline[0]
        oracle = max([base, *candidates], key=lambda row: (float(row["formal_minimum_signed_margin"]), float(row["formal_mean_signed_margin"]), row["kind"] == "baseline"))
        best = max(candidates, key=lambda row: (float(row["formal_minimum_signed_margin"]), float(row["formal_mean_signed_margin"]), str(row["grid_id"]), str(row["sequence_id"])))
        contexts.append(
            {
                "pair_id": key[0],
                "history_member": key[1],
                "baseline": base,
                "candidates": sorted(candidates, key=lambda row: (str(row["grid_id"]), str(row["sequence_id"]))),
                "best_candidate": best,
                "best_candidate_minimum_margin_gain": float(best["formal_minimum_signed_margin"]) - float(base["formal_minimum_signed_margin"]),
                "failed_baseline_repaired": bool(not base["formal_contract_pass"] and any(row["formal_contract_pass"] for row in candidates)),
                "held_oracle_formal_pass": bool(oracle["formal_contract_pass"]),
                "held_oracle_experiment_id": oracle["experiment_id"],
            }
        )
    baseline_pass = sum(bool(row["baseline"]["formal_contract_pass"]) for row in contexts)
    repairs = sum(bool(row["failed_baseline_repaired"]) for row in contexts)
    oracle_pass = sum(bool(row["held_oracle_formal_pass"]) for row in contexts)
    gains = [float(row["best_candidate_minimum_margin_gain"]) for row in contexts if not row["baseline"]["formal_contract_pass"]]
    gate = ctx.cfg["scientific_gate"]
    scientific = bool(
        baseline_pass == int(gate["required_baseline_formal_pass_count"])
        and len(contexts) - baseline_pass == int(gate["required_failed_baseline_count"])
        and repairs >= int(gate["minimum_repaired_failed_baseline_count"])
        and oracle_pass >= int(gate["minimum_held_oracle_formal_pass_count"])
        and oracle_pass > baseline_pass
    )
    candidate_summaries = []
    for grid_id, sequence_id in sorted(expected_members):
        selected = [row for row in rows if row["kind"] == "candidate" and row["grid_id"] == grid_id and row["sequence_id"] == sequence_id]
        candidate_summaries.append(
            {
                "grid_id": grid_id,
                "sequence_id": sequence_id,
                "context_count": len(selected),
                "formal_pass_count": sum(bool(row["formal_contract_pass"]) for row in selected),
                "repaired_failed_baseline_count": sum(not context["baseline"]["formal_contract_pass"] and next(row for row in context["candidates"] if row["grid_id"] == grid_id and row["sequence_id"] == sequence_id)["formal_contract_pass"] for context in contexts),
                "baseline_pass_regression_count": sum(context["baseline"]["formal_contract_pass"] and not next(row for row in context["candidates"] if row["grid_id"] == grid_id and row["sequence_id"] == sequence_id)["formal_contract_pass"] for context in contexts),
            }
        )
    return {
        "row_count": len(rows),
        "formal_metric_equivalence_passed": equivalence,
        "maximum_margin_abs_difference": max(float(row["maximum_margin_abs_difference"]) for row in rows),
        "context_count": len(contexts),
        "baseline_formal_pass_count": baseline_pass,
        "failed_baseline_count": len(contexts) - baseline_pass,
        "new_candidate_formal_pass_count": sum(bool(row["formal_contract_pass"]) for row in rows if row["source"] == "R8R28"),
        "repaired_failed_baseline_count": repairs,
        "held_oracle_formal_pass_count": oracle_pass,
        "failed_baseline_best_candidate_margin_gain": {"minimum": min(gains), "median": statistics.median(gains), "maximum": max(gains)},
        "candidate_summaries": candidate_summaries,
        "context_rows": contexts,
        "rows": rows,
        "scientific_gate_passed": scientific,
    }


def finalize_primary(ctx: Context) -> dict[str, Any]:
    state = _read(ctx.paths.state)
    reports = [_read(ctx.paths.analysis / f"{phase}_raw_{kind}.json") for phase in PHASES for kind in ("primary", "independent")]
    if (
        state.get("phase_status") != "qualification_primary_ready"
        or not all(report.get("passed") is True for report in reports)
        or not all(report.get("primary_agreement") is True for report in reports if report.get("audit_kind"))
    ):
        raise ValueError("R8R28 raw independent gates incomplete")
    formal = compute_formal_authority(ctx)
    integrity = bool(formal["formal_metric_equivalence_passed"] and formal["row_count"] == 80 and formal["context_count"] == 16)
    scientific = bool(integrity and formal["scientific_gate_passed"])
    route = ctx.cfg["routes"]["pass" if scientific else "authority_fail"]
    detailed = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "source_authenticated": True,
        "integrity_gate_passed": integrity,
        "scientific_gate_passed": scientific,
        "formal_authority": formal,
        "safety_raw_inventory": reports[0]["raw_inventory"],
        "qualification_raw_inventory": reports[2]["raw_inventory"],
        "new_raw_count": 64,
        "real_tsc_executed": True,
        "route": route,
        "passed": scientific,
    }
    _write(ctx.paths.analysis / "primary_detailed.json", detailed)
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "source_authenticated": True,
        "integrity_gate_passed": integrity,
        "scientific_gate_passed": scientific,
        "formal_metric_equivalence_passed": formal["formal_metric_equivalence_passed"],
        "maximum_margin_abs_difference": formal["maximum_margin_abs_difference"],
        "context_count": formal["context_count"],
        "baseline_formal_pass_count": formal["baseline_formal_pass_count"],
        "failed_baseline_count": formal["failed_baseline_count"],
        "new_candidate_formal_pass_count": formal["new_candidate_formal_pass_count"],
        "candidate_summaries": formal["candidate_summaries"],
        "repaired_failed_baseline_count": formal["repaired_failed_baseline_count"],
        "held_oracle_formal_pass_count": formal["held_oracle_formal_pass_count"],
        "failed_baseline_best_candidate_margin_gain": formal["failed_baseline_best_candidate_margin_gain"],
        "new_raw_count": 64,
        "real_tsc_executed": True,
        "route": route,
        "passed": scientific,
    }
    _write(ctx.paths.analysis / "primary_summary.json", summary)
    _set_state(ctx, phase_status="final_primary_ready", formal_outcomes_opened=True, primary_route=route, primary_summary_sha256=_sha(ctx.paths.analysis / "primary_summary.json"))
    return summary


def postprocess(ctx: Context) -> dict[str, Any]:
    state = _read(ctx.paths.state)
    primary = _read(ctx.paths.analysis / "primary_summary.json")
    independent = _read(ctx.paths.analysis / "final_independent.json")
    if (
        state.get("phase_status") != "final_primary_ready"
        or independent.get("passed") is not True
        or independent.get("primary_route_agreement") is not True
        or independent.get("primary_outcome_agreement") is not True
        or independent.get("primary_numerical_agreement") is not True
    ):
        raise ValueError("R8R28 final independent agreement failed")
    final = copy.deepcopy(primary)
    final.update(
        {
            "phase": "final",
            "primary_detailed_sha256": _sha(ctx.paths.analysis / "primary_detailed.json"),
            "primary_summary_sha256": _sha(ctx.paths.analysis / "primary_summary.json"),
            "independent_sha256": _sha(ctx.paths.analysis / "final_independent.json"),
            "stage_manifest_sha256": _sha(ctx.paths.manifest),
        }
    )
    _write(ctx.paths.analysis / "final_report.json", final)
    _set_state(
        ctx,
        phase_status="complete",
        finished=True,
        real_tsc_executed=True,
        new_raw_count=64,
        qualification_outcomes_opened=True,
        formal_outcomes_opened=True,
        final_report_sha256=_sha(ctx.paths.analysis / "final_report.json"),
        final_independent_sha256=_sha(ctx.paths.analysis / "final_independent.json"),
        stop_reason="" if final["passed"] else "formal_authority_gate_failed",
        verdict={"route": final["route"], "passed": bool(final["passed"])},
    )
    return final


def execute(ctx: Context, *, command: str, backend: str, resume: bool) -> dict[str, Any]:
    if command == "offline":
        return prepare_offline(ctx)
    if command == "authorize-safety":
        return authorize_safety(ctx)
    if command in PHASES:
        return run_phase(ctx, command, backend=backend, resume=resume)
    if command == "authorize-qualification":
        return authorize_qualification(ctx)
    if command == "finalize-primary":
        return finalize_primary(ctx)
    if command == "postprocess":
        return postprocess(ctx)
    raise ValueError(command)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("config", "r8r7-run", "r8r14-run", "r8r27-run", "r8-run", "r8r1-output", "r8r6-run"):
        parser.add_argument(f"--{name}", dest=name.replace("-", "_"), type=Path, required=True)
    for name in (
        "source-d1r11-run", "source-r2-run", "source-r4-run", "source-r6-run",
        "source-s21-run", "source-s23r1-output", "source-s24-run", "source-d1r9-v1",
        "source-d1r9-v2", "source-d1r10-run", "source-d1r10-audit", "source-stage42r3b-run",
        "source-stage42r3c3-run", "source-stage42r3c3-bank-dir", "source-stage42r3c3t1-run",
        "source-stage42r3c3t1-audit-dir", "source-stage42r3c3t3-controller-bank", "q1-run",
        "q2-run", "q1-audit", "q2-audit", "r3b-server-audit", "r3b-snapshot-checks",
    ):
        parser.add_argument(f"--{name}", dest=name.replace("-", "_"), type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--command", choices=("offline", "authorize-safety", "safety", "authorize-qualification", "qualification", "finalize-primary", "postprocess"), required=True)
    parser.add_argument("--backend", choices=("serial", "ray"), default="ray")
    parser.add_argument("--resume", action="store_true")
    return parser


def main() -> None:
    args = _parser().parse_args()
    ctx = load_context(args)
    result = execute(ctx, command=args.command, backend=args.backend, resume=args.resume)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
