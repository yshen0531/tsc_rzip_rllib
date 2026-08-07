"""Execute and audit the frozen R8R8 causal discrete-pulse MPC core."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import shutil
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.control import causal_discrete_pulse_mpc as mpc
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r1_fixed_candidate_short_horizon_discriminator as r8r1,
    stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_campaign as r8r7,
    stage4_2r3c3t13s24d1r14r8r8_causal_discrete_pulse_mpc_core as contract,
)


N_COILS = 14
PREFIX_END = 10


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
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
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
    stage: Path
    variants: Path
    specs: Path
    source_reference: Path
    raw: Path
    analysis: Path
    model: Path
    state: Path
    manifest: Path


def _paths(run_dir: Path) -> Paths:
    run = run_dir.expanduser().resolve()
    stage = run / contract.RUN_NAME
    return Paths(
        run_dir=run,
        stage=stage,
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
    source_run: Path
    source_ctx: r8r7.Context


def load_context(args: argparse.Namespace) -> Context:
    config_path = args.config.expanduser().resolve()
    cfg = _read(config_path)
    contract.validate_config(cfg, project_root=_root())
    source_args = argparse.Namespace(**vars(args))
    source_args.config = (_root() / str(cfg["source_r8r7_config"])).resolve()
    source_args.run_dir = args.r8r7_run.expanduser().resolve()
    return Context(
        cfg=cfg,
        config_path=config_path,
        paths=_paths(args.run_dir),
        source_run=args.r8r7_run.expanduser().resolve(),
        source_ctx=r8r7.load_context(source_args),
    )


def _source_stage(ctx: Context) -> Path:
    return ctx.source_ctx.paths.stage


def _package_fingerprint() -> dict[str, Any]:
    manifest = _read(_root() / "PACKAGE_MANIFEST.json")
    files = list(map(str, manifest["file_inventory"]))
    hashes = {name: _sha(_root() / name) for name in files}
    required = {
        "configs/stage4_2r3c3t13s24d1r14r8r8_causal_discrete_pulse_receding_horizon_mpc_core_370ms.json",
        "docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R8_CAUSAL_DISCRETE_PULSE_RECEDING_HORIZON_MPC_CORE_DESIGN.md",
        "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r8_independent_forensics.py",
        "scripts/stage4_2r3c3t13s24d1r14r8r8_causal_discrete_pulse_mpc_campaign.py",
        "tsc_rzip_rllib/control/causal_discrete_pulse_mpc.py",
        "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r8r8_causal_discrete_pulse_mpc_core.py",
        "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r8r8_causal_discrete_pulse_mpc_campaign.py",
    }
    if not required.issubset(hashes):
        raise ValueError(f"R8R8 package import closure incomplete: {sorted(required.difference(hashes))}")
    return {
        "declared_file_count": len(files),
        "hashes": hashes,
        "digest": r8r7.r8._digest(hashes),
    }


def _authenticate_source(ctx: Context) -> dict[str, Any]:
    stage = _source_stage(ctx)
    expected = ctx.cfg["source_r8r7_contract"]
    paths = {
        "all_specs": stage / "specs/all_specs.json",
        "baseline_specs": stage / "specs/baseline_specs.json",
        "response_model": stage / "model/response_model.json",
        "response_tube": stage / "model/response_tube.json",
        "combined_tube": stage / "model/combined_tube.json",
        "final_report": stage / "analysis/final_report.json",
        "stage_manifest": stage / "stage_manifest.json",
        "stage_state": stage / "stage_state.json",
    }
    if ctx.source_run.name != str(expected["run_name"]):
        raise ValueError("R8R8 source R8R7 run identity changed")
    for name, path in paths.items():
        if not path.is_file() or _sha(path) != str(expected[f"{name}_sha256"]):
            raise ValueError(f"R8R8 source R8R7 {name} changed")
    final = _read(paths["final_report"])
    state = _read(paths["stage_state"])
    if (
        final.get("route") != expected["required_route"]
        or final.get("scientific_gate_passed") is not True
        or final.get("passed") is not True
        or state.get("phase_status") != "complete"
        or state.get("verdict", {}).get("route") != expected["required_route"]
    ):
        raise ValueError("R8R8 source R8R7 final route changed")
    inventories = {}
    for phase in ("baseline", "multipulse"):
        inventory = r8r7.r8._inventory(stage / "raw" / phase)
        if (
            inventory["count"] != int(expected[f"{phase}_raw_count"])
            or inventory["bytes"] != int(expected[f"{phase}_raw_bytes"])
            or inventory["digest"] != str(expected[f"{phase}_raw_digest"])
        ):
            raise ValueError(f"R8R8 source R8R7 {phase} raw inventory changed")
        inventories[phase] = inventory
    r8r7._authenticate_r8(ctx.source_ctx)
    r8r7._authenticate_r8r1(ctx.source_ctx)
    r8r7._authenticate_r8r6(ctx.source_ctx)
    return {
        "paths": {name: str(path) for name, path in paths.items()},
        "hashes": {name: _sha(path) for name, path in paths.items()},
        "inventories": inventories,
        "required_route": expected["required_route"],
        "passed": True,
    }


def _new_specs(ctx: Context) -> list[dict[str, Any]]:
    sources = _read(_source_stage(ctx) / "specs/baseline_specs.json")
    if len(sources) != 16:
        raise ValueError("R8R8 source baseline coverage changed")
    output = []
    for index, source in enumerate(sorted(sources, key=lambda row: str(row["experiment_id"]))):
        spec = copy.deepcopy(source)
        offsets = [
            float(source["target_R_offset_m"]),
            float(source["target_Z_offset_m"]),
            float(source["target_Ip_offset_A"]),
        ]
        spec.update(
            {
                "kind": "stage4_2r3c3t13s24d1r14r8r8_causal_discrete_pulse_mpc_core",
                "stage": contract.STAGE,
                "campaign_identity": contract.IDENTITY,
                "controller_revision": contract.CONTROLLER_REVISION,
                "partition": "deterministic_core",
                "phase": "causal_discrete_pulse_mpc_core",
                "category": "finite_deterministic_mpc_core",
                "experiment_id": f"r8r8_core_{index:02d}",
                "source_r8r7_baseline_experiment_id": str(source["experiment_id"]),
                "r8r8_numeric_target_offsets": offsets,
                "r8r8_decision_task_steps": list(contract.DECISION_STEPS),
                "r8r8_candidate_alphabet_digest": contract.MATRIX_DIGEST,
                "r8r8_all_stage_trajectories_allowed_in_expert_dataset": False,
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
    if len(output) != 16 or len({row["experiment_id"] for row in output}) != 16:
        raise ValueError("R8R8 specification coverage changed")
    return output


def _model_bundle(ctx: Context, *, output_paths: bool) -> dict[str, Any]:
    source = _source_stage(ctx)
    static_root = r8r7._r8r6_paths(ctx.source_ctx).model
    paths = {
        "static_model": static_root / "observer_model.json",
        "static_tube": static_root / "observer_tube.json",
        "response_model": source / "model/response_model.json",
        "response_tube": source / "model/response_tube.json",
        "combined_tube": source / "model/combined_tube.json",
    }
    expected = ctx.cfg["source_model_contract"]
    checks = {
        "static_model": "static_observer_model_sha256",
        "static_tube": "static_observer_tube_sha256",
        "response_model": "response_model_sha256",
        "response_tube": "response_tube_sha256",
        "combined_tube": "combined_tube_sha256",
    }
    for name, key in checks.items():
        if not paths[name].is_file() or _sha(paths[name]) != str(expected[key]):
            raise ValueError(f"R8R8 source model artifact {name} changed")
    if output_paths:
        for name, path in paths.items():
            destination = ctx.paths.model / f"{name}.json"
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
            if _sha(destination) != _sha(path):
                raise ValueError("R8R8 model artifact direct copy changed bytes")
        paths = {name: ctx.paths.model / f"{name}.json" for name in paths}
    static_artifact = _read(paths["static_model"])
    response_artifact = _read(paths["response_model"])
    return {
        "static_model": mpc.observer_model_from_artifact(static_artifact),
        "action_model": mpc.response_model_from_artifact(response_artifact),
        "static_tube": np.asarray(_read(paths["static_tube"])["tube_physical"], dtype=float),
        "response_tube": np.asarray(_read(paths["response_tube"])["tube_physical"], dtype=float),
        "combined_tube": np.asarray(
            _read(paths["combined_tube"])["combined_tube_physical"], dtype=float
        ),
        "hashes": {name: _sha(path) for name, path in paths.items()},
    }


def _source_baselines(ctx: Context) -> dict[str, dict[str, Any]]:
    output = {}
    for path in sorted((_source_stage(ctx) / "raw/baseline").glob("*.json.gz")):
        value = r8r7.r8._read_gz(path)
        output[str(value["experiment_id"])] = value
    if len(output) != 16:
        raise ValueError("R8R8 source baseline raw coverage changed")
    return output


def _source_payload(ctx: Context, experiment_id: str) -> dict[str, Any]:
    return _read(_source_stage(ctx) / "variants" / f"payload_{experiment_id}.json")


def _offline_rows(
    ctx: Context, specs: Sequence[Mapping[str, Any]], models: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    sources = _source_baselines(ctx)
    r8r6_cfg = ctx.source_ctx.r8r6_cfg
    r8r7_cfg = ctx.source_ctx.cfg
    response_cfg = r8r1.model_config(ctx.source_ctx.r8r1_cfg, ctx.source_ctx.r8_cfg)
    lattice_cfg = ctx.source_ctx.r8_ctx.d1r11_ctx.base_ctx.base_ctx.cfg["lattice_probe"]
    rows = []
    selections = []
    for spec in specs:
        source_id = str(spec["source_r8r7_baseline_experiment_id"])
        source = sources[source_id]
        payload = _source_payload(ctx, source_id)
        actuator = mpc.actuator_from_payload(payload, lattice_cfg)
        states = source["trajectory"]
        actions = [row["action_norm_tsc"] for row in source["controller_trace"]]
        basis = source["controller_trace"][7]["r3c3t13s16_fixed_basis_delta_field_kAt_tsc"]
        for origin in contract.DECISION_STEPS:
            forecasts = mpc.predict_candidates(
                states=states[: origin + 1],
                actions=actions[:origin],
                target_offsets=spec["r8r8_numeric_target_offsets"],
                static_model=models["static_model"],
                action_model=models["action_model"],
                static_tube_physical=models["static_tube"],
                combined_tube_physical=models["combined_tube"],
                observer_cfg=r8r6_cfg,
                response_cfg=response_cfg,
                r8r7_cfg=r8r7_cfg,
                r8r8_cfg=ctx.cfg,
            )
            construction = {}
            eligible = []
            for candidate in mpc.candidates(ctx.cfg)[1:]:
                issue = mpc.construct_issue(
                    task_step=origin,
                    currents_a_tsc=states[origin]["currents_a_tsc"],
                    fixed_basis_delta_field_kat_tsc=basis,
                    candidate=candidate,
                    canonical_matrix_columns=ctx.cfg["candidate_contract"]["canonical_matrix_columns"],
                    actuator=actuator,
                    controller_cfg=ctx.cfg["controller_contract"],
                    lattice_cfg=lattice_cfg,
                )
                cancel = mpc.construct_cancel(
                    task_step=origin + 1,
                    currents_a_tsc=issue["nominal_issue_readback_current_a_tsc"],
                    issue_event=issue,
                    actuator=actuator,
                    controller_cfg=ctx.cfg["controller_contract"],
                    lattice_cfg=lattice_cfg,
                )
                passed = bool(issue["passed"] and cancel["passed"])
                if passed:
                    eligible.append(candidate.name)
                construction[candidate.name] = {
                    "issue": issue,
                    "cancel": cancel,
                    "passed": passed,
                }
            selection = mpc.select_candidate(
                forecasts,
                eligible,
                float(ctx.cfg["objective_contract"]["required_nonzero_score_ratio"]),
            )
            row_id = f"{spec['experiment_id']}|origin{origin:02d}"
            rows.extend(
                {
                    "row_id": row_id,
                    "experiment_id": str(spec["experiment_id"]),
                    "origin_task_step": origin,
                    **copy.deepcopy(forecast),
                }
                for forecast in forecasts
            )
            selections.append(
                {
                    "row_id": row_id,
                    "experiment_id": str(spec["experiment_id"]),
                    "origin_task_step": origin,
                    "selection": selection,
                    "constructions": construction,
                }
            )
    return rows, selections


def _fault_injection(ctx: Context) -> list[dict[str, Any]]:
    forecasts = [
        {
            "order": index,
            "name": candidate.name,
            "direction_index": candidate.direction_index,
            "sign": candidate.sign,
            "score": 10.0 if index == 0 else 10.0 + index,
        }
        for index, candidate in enumerate(mpc.candidates(ctx.cfg))
    ]
    cases = []
    for name, eligible, fault in (
        ("all_nonzero_infeasible", [], None),
        ("only_worse_nonzero", ["direction0_minus"], None),
        ("nonfinite_model_guard", ["direction0_minus"], "nonfinite"),
        ("model_exception_guard", ["direction0_minus"], "exception"),
    ):
        attempted = [dict(row) for row in forecasts]
        fallback_reason = ""
        try:
            if fault == "nonfinite":
                attempted[1]["score"] = float("nan")
            elif fault == "exception":
                raise RuntimeError("injected model exception")
            selected = mpc.select_candidate(
                attempted,
                eligible,
                float(ctx.cfg["objective_contract"]["required_nonzero_score_ratio"]),
            )
        except Exception as exc:
            fallback_reason = repr(exc)
            selected = {
                "selected_name": "zero",
                "selected_order": 0,
                "selected_direction_index": -1,
                "selected_sign": 0,
                "nonzero_selected": False,
                "robust_improvement_fraction": 0.0,
            }
        cases.append(
            {
                "case": name,
                "injected_fault": fault or name,
                "fallback_reason": fallback_reason,
                "selected_name": selected["selected_name"],
                "physical_action": [0.0] * N_COILS,
                "safe_zero": selected["selected_name"] == "zero",
            }
        )
    if not all(row["safe_zero"] for row in cases):
        raise ValueError("R8R8 fault-injected safe-zero fallback failed")
    return cases


def prepare_offline(ctx: Context) -> dict[str, Any]:
    if ctx.paths.stage.exists():
        raise ValueError("R8R8 offline requires a fresh run identity")
    source = _authenticate_source(ctx)
    specs = _new_specs(ctx)
    package = _package_fingerprint()
    for path in (
        ctx.paths.stage,
        ctx.paths.variants,
        ctx.paths.specs,
        ctx.paths.source_reference,
        ctx.paths.raw,
        ctx.paths.analysis,
        ctx.paths.model,
    ):
        path.mkdir(parents=True, exist_ok=True)
    _write(ctx.paths.specs / "core_specs.json", specs)
    _write(ctx.paths.source_reference / "r8r7_authentication.json", source)
    models = _model_bundle(ctx, output_paths=True)
    rows, selections = _offline_rows(ctx, specs, models)
    faults = _fault_injection(ctx)
    issue_count = sum(
        bool(value["issue"]["passed"])
        for row in selections
        for value in row["constructions"].values()
    )
    cancel_count = sum(
        bool(value["cancel"]["passed"])
        for row in selections
        for value in row["constructions"].values()
    )
    nonzero = sum(bool(row["selection"]["nonzero_selected"]) for row in selections)
    passed = bool(
        len(specs) == 16
        and len(rows) == 576
        and len(selections) == 64
        and issue_count == 512
        and cancel_count == 512
        and nonzero >= int(ctx.cfg["offline_gates"]["minimum_nonzero_selection_count"])
        and len(faults) == 4
        and all(row["safe_zero"] for row in faults)
    )
    detailed = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "phase": "zero_tsc_primary_offline_controller_acceptance",
        "source_authenticated": True,
        "spec_count": len(specs),
        "decision_origin_count": len(selections),
        "candidate_forecast_count": len(rows),
        "issue_construction_pass_count": issue_count,
        "cancel_construction_pass_count": cancel_count,
        "nonzero_selection_count": nonzero,
        "forbidden_or_future_input_count": 0,
        "enumeration_side_effect_count": 0,
        "fault_injection": faults,
        "forecast_rows": rows,
        "selection_rows": selections,
        "model_hashes": models["hashes"],
        "real_tsc_executed": False,
        "new_raw_count": 0,
        "route": ctx.cfg["routes"]["pass" if passed else "offline_fail"],
        "passed": passed,
    }
    detailed_path = ctx.paths.analysis / "offline_primary_detailed.json"
    _write(detailed_path, detailed)
    summary = {key: value for key, value in detailed.items() if key not in {"forecast_rows", "selection_rows"}}
    summary["primary_detailed_sha256"] = _sha(detailed_path)
    _write(ctx.paths.analysis / "offline_primary_summary.json", summary)
    manifest = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "campaign_identity": contract.IDENTITY,
        "controller_revision": contract.CONTROLLER_REVISION,
        "package_revision": contract.PACKAGE_REVISION,
        "config_path": str(ctx.config_path),
        "config_sha256": _sha(ctx.config_path),
        "design_document_sha256": contract.DESIGN_SHA256,
        "source_r8r7_run": str(ctx.source_run),
        "source_authentication_sha256": _sha(ctx.paths.source_reference / "r8r7_authentication.json"),
        "spec_count": len(specs),
        "spec_digest": r8r7.r8._digest(specs),
        "model_hashes": models["hashes"],
        "package_fingerprint": package,
        "formal_timing_unchanged": True,
        "all_stage_trajectories_allowed_in_expert_dataset": False,
    }
    _write(ctx.paths.manifest, manifest)
    _write(
        ctx.paths.state,
        {
            "schema_version": 1,
            "stage": contract.STAGE,
            "phase_status": "offline_primary_ready" if passed else "offline_primary_failed",
            "finished": not passed,
            "real_tsc_executed": False,
            "new_raw_count": 0,
            "spec_digest": manifest["spec_digest"],
            "package_digest": package["digest"],
            "offline_primary_summary_sha256": _sha(ctx.paths.analysis / "offline_primary_summary.json"),
            "stop_reason": "" if passed else "source_or_primary_offline_gate_failed",
            "verdict": {} if passed else {"route": ctx.cfg["routes"]["offline_fail"], "passed": False},
        },
    )
    return summary


def _saved_specs(ctx: Context) -> list[dict[str, Any]]:
    specs = _read(ctx.paths.specs / "core_specs.json")
    manifest = _read(ctx.paths.manifest)
    if (
        len(specs) != 16
        or r8r7.r8._digest(specs) != manifest.get("spec_digest")
        or manifest.get("stage") != contract.STAGE
        or manifest.get("campaign_identity") != contract.IDENTITY
        or manifest.get("controller_revision") != contract.CONTROLLER_REVISION
        or _sha(ctx.config_path) != manifest.get("config_sha256")
    ):
        raise ValueError("R8R8 saved identity or specs changed")
    return specs


def _require(ctx: Context, phase_status: str) -> dict[str, Any]:
    state = _read(ctx.paths.state)
    manifest = _read(ctx.paths.manifest)
    if (
        state.get("phase_status") != phase_status
        or bool(state.get("finished"))
        or state.get("spec_digest") != manifest.get("spec_digest")
        or state.get("package_digest") != (manifest.get("package_fingerprint") or {}).get("digest")
    ):
        raise ValueError(f"R8R8 phase guard expected {phase_status!r}, got {state.get('phase_status')!r}")
    return state


def authorize_real(ctx: Context) -> dict[str, Any]:
    state = _require(ctx, "offline_primary_ready")
    primary_path = ctx.paths.analysis / "offline_primary_summary.json"
    independent_path = ctx.paths.analysis / "offline_independent.json"
    if not independent_path.is_file():
        raise ValueError("R8R8 offline independent audit missing")
    primary = _read(primary_path)
    independent = _read(independent_path)
    if (
        primary.get("passed") is not True
        or independent.get("passed") is not True
        or independent.get("primary_numerical_agreement") is not True
        or independent.get("primary_outcome_agreement") is not True
        or independent.get("artifact_hash_agreement") is not True
        or independent.get("primary_sha256") != _sha(primary_path)
        or state.get("offline_primary_summary_sha256") != _sha(primary_path)
    ):
        raise ValueError("R8R8 dual offline acceptance failed")
    state.update(
        {
            "phase_status": "real_authorized",
            "offline_independent_sha256": _sha(independent_path),
        }
    )
    _write(ctx.paths.state, state)
    return {"stage": contract.STAGE, "phase": "real_authorized", "passed": True}


def _payload(ctx: Context, spec: Mapping[str, Any]) -> dict[str, Any]:
    source = ctx.source_ctx
    execution = r8r7.r8.Context(
        cfg=source.r8_cfg,
        config_path=source.r8_config_path,
        d1r11_ctx=source.r8_ctx.d1r11_ctx,
        source_d1r11_run=source.r8_ctx.source_d1r11_run,
        source_response_runs=source.r8_ctx.source_response_runs,
        paths=ctx.paths,  # type: ignore[arg-type]
    )
    payload = r8r7.r8._payload(execution, spec)
    experiment_id = str(spec["experiment_id"])
    payload.update(
        {
            "variant_id": f"stage4_2r3c3t13s24d1r14r8r8_{experiment_id}",
            "stage4_2r3c3t13s24d1r14r8r8_numeric_target_available_to_controller": True,
            "stage4_2r3c3t13s24d1r14r8r8_pair_history_label_available_to_controller": False,
        }
    )
    _write(ctx.paths.variants / f"payload_{experiment_id}.json", payload)
    return payload


class CausalDiscretePulseMPCController(r8r7.FixedCanonicalMultipulseController):
    """Causal four-step exhaustive MPC over the frozen canonical pulse alphabet."""

    def __init__(
        self,
        base_worker: Any,
        bundle: Mapping[str, Any],
        source_spec: Mapping[str, Any],
        initial_state: Mapping[str, Any],
        lattice_cfg: Mapping[str, Any],
        calibration_cfg: Mapping[str, Any],
        dynamic_cfg: Mapping[str, Any],
        schedule_cfg: Mapping[str, Any],
        inherited_controller_cfg: Mapping[str, Any],
        r8r8_cfg: Mapping[str, Any],
        observer_cfg: Mapping[str, Any],
        response_cfg: Mapping[str, Any],
        r8r7_cfg: Mapping[str, Any],
        model_bundle: Mapping[str, Any],
        numeric_target_offsets: Sequence[float],
    ):
        sanitized = copy.deepcopy(dict(source_spec))
        for key in list(sanitized):
            if key.startswith("r8r8_") or key.startswith("source_r8r7_"):
                sanitized.pop(key)
        super().__init__(
            base_worker,
            bundle,
            sanitized,
            initial_state,
            lattice_cfg,
            calibration_cfg,
            dynamic_cfg,
            schedule_cfg,
            inherited_controller_cfg,
        )
        if str(source_spec["r8r7_role"]) != "baseline":
            raise ValueError("R8R8 must inherit only an R8R7 baseline prefix")
        self.r8r8_cfg = copy.deepcopy(dict(r8r8_cfg))
        self.observer_cfg = copy.deepcopy(dict(observer_cfg))
        self.response_cfg = copy.deepcopy(dict(response_cfg))
        self.r8r7_cfg = copy.deepcopy(dict(r8r7_cfg))
        self.static_model = model_bundle["static_model"]
        self.action_model = model_bundle["action_model"]
        self.static_tube = np.asarray(model_bundle["static_tube"], dtype=float)
        self.combined_tube = np.asarray(model_bundle["combined_tube"], dtype=float)
        self.numeric_target_offsets = tuple(map(float, numeric_target_offsets))
        if len(self.numeric_target_offsets) != 3:
            raise ValueError("R8R8 numeric user target changed")
        self.r8r8_states = [copy.deepcopy(dict(initial_state))]
        self.r8r8_actions: list[list[float]] = []
        self.r8r8_decisions: list[dict[str, Any]] = []
        self.r8r8_model_fault_count = 0
        self.r8r8_selected_nonzero_count = 0

    def advance(self, next_state: Mapping[str, Any]) -> None:
        super().advance(next_state)
        self.r8r8_states.append(copy.deepcopy(dict(next_state)))

    def _finish_trace(
        self,
        trace: dict[str, Any],
        action: np.ndarray,
        *,
        event_name: str,
        event: Mapping[str, Any],
        decision: Mapping[str, Any] | None,
        delegated: bool,
    ) -> tuple[np.ndarray, dict[str, Any]]:
        trace.update(
            {
                "action_norm_tsc": action.tolist(),
                "solver_success": not bool(decision and decision.get("model_fault")),
                "r3c3t13s24d1r14r8r8_controller_revision": contract.CONTROLLER_REVISION,
                "r3c3t13s24d1r14r8r8_delegated_prefix": delegated,
                "r3c3t13s24d1r14r8r8_event": event_name,
                "r3c3t13s24d1r14r8r8_event_detail": copy.deepcopy(dict(event)),
                "r3c3t13s24d1r14r8r8_decision": copy.deepcopy(dict(decision or {})),
                "r3c3t13s24d1r14r8r8_pair_or_history_label_used": False,
                "r3c3t13s24d1r14r8r8_partition_label_used": False,
                "r3c3t13s24d1r14r8r8_source_result_used": False,
                "r3c3t13s24d1r14r8r8_source_formal_outcome_used": False,
                "r3c3t13s24d1r14r8r8_future_measurement_used": False,
                "r3c3t13s24d1r14r8r8_future_executed_action_used": False,
                "r3c3t13s24d1r14r8r8_hidden_wire_current_used": False,
                "r3c3t13s24d1r14r8r8_adaptation_enabled": False,
            }
        )
        self.r8r8_actions.append(action.tolist())
        return action, trace

    def action(self, current_state: Mapping[str, Any]) -> tuple[np.ndarray, dict[str, Any]]:
        if int(current_state["step_index"]) != self.step:
            raise ValueError("R8R8 controller/current task-state index mismatch")
        if len(self.r8r8_states) != self.step + 1 or len(self.r8r8_actions) != self.step:
            raise ValueError("R8R8 causal history clock changed")
        if self.step < PREFIX_END:
            action, trace = super().action(current_state)
            return self._finish_trace(
                trace,
                np.asarray(action, dtype=float),
                event_name="none",
                event={},
                decision=None,
                delegated=True,
            )
        action = r8r7.r4.zero_action(self.step)
        trace = r8r7.r4._trace_template(self.step, action)
        event_name = "none"
        event: dict[str, Any] = {}
        decision: dict[str, Any] | None = None
        if self.step in contract.DECISION_STEPS:
            decision = {
                "task_step": self.step,
                "model_fault": False,
                "fallback_reason": "",
                "candidate_forecasts": [],
                "candidate_constructions": [],
            }
            try:
                forecasts = mpc.predict_candidates(
                    states=self.r8r8_states,
                    actions=self.r8r8_actions,
                    target_offsets=self.numeric_target_offsets,
                    static_model=self.static_model,
                    action_model=self.action_model,
                    static_tube_physical=self.static_tube,
                    combined_tube_physical=self.combined_tube,
                    observer_cfg=self.observer_cfg,
                    response_cfg=self.response_cfg,
                    r8r7_cfg=self.r8r7_cfg,
                    r8r8_cfg=self.r8r8_cfg,
                )
                basis = [
                    [float(value) for value in self._fixed_basis_delta[index]]
                    for index in range(4)
                ]
                construction: dict[str, dict[str, Any]] = {}
                eligible = []
                for candidate in mpc.candidates(self.r8r8_cfg)[1:]:
                    try:
                        built_issue = mpc.construct_issue(
                            task_step=self.step,
                            currents_a_tsc=current_state["currents_a_tsc"],
                            fixed_basis_delta_field_kat_tsc=basis,
                            candidate=candidate,
                            canonical_matrix_columns=self.r8r8_cfg["candidate_contract"]["canonical_matrix_columns"],
                            actuator=self.actuator,
                            controller_cfg=self.r8r8_cfg["controller_contract"],
                            lattice_cfg=self.lattice_cfg,
                        )
                        built_cancel = mpc.construct_cancel(
                            task_step=self.step + 1,
                            currents_a_tsc=built_issue["nominal_issue_readback_current_a_tsc"],
                            issue_event=built_issue,
                            actuator=self.actuator,
                            controller_cfg=self.r8r8_cfg["controller_contract"],
                            lattice_cfg=self.lattice_cfg,
                        )
                        construction[candidate.name] = {
                            "candidate_name": candidate.name,
                            "issue": built_issue,
                            "nominal_cancel": built_cancel,
                            "passed": bool(built_issue["passed"] and built_cancel["passed"]),
                        }
                        if construction[candidate.name]["passed"]:
                            eligible.append(candidate.name)
                    except Exception as exc:
                        construction[candidate.name] = {
                            "candidate_name": candidate.name,
                            "passed": False,
                            "construction_error": repr(exc),
                        }
                selected = mpc.select_candidate(
                    forecasts,
                    eligible,
                    float(self.r8r8_cfg["objective_contract"]["required_nonzero_score_ratio"]),
                )
                decision.update(
                    {
                        "candidate_forecasts": forecasts,
                        "candidate_constructions": [construction[row.name] for row in mpc.candidates(self.r8r8_cfg)[1:]],
                        "selection": selected,
                    }
                )
                if selected["nonzero_selected"]:
                    selected_construction = construction[str(selected["selected_name"])]
                    event = copy.deepcopy(selected_construction["issue"])
                    if not event.get("passed"):
                        raise ValueError("R8R8 selected an ineligible action")
                    action = np.asarray(event["action_norm_tsc"], dtype=float)
                    self._active_issue = copy.deepcopy(event)
                    self.r8r8_selected_nonzero_count += 1
                    event_name = "mpc_issue"
                else:
                    event_name = "mpc_zero"
                    event = {"event": "mpc_zero", "task_step": self.step, "passed": True}
            except Exception as exc:
                self.r8r8_model_fault_count += 1
                decision.update(
                    {
                        "model_fault": True,
                        "fallback_reason": repr(exc),
                        "selection": {
                            "selected_name": "zero",
                            "selected_order": 0,
                            "selected_direction_index": -1,
                            "selected_sign": 0,
                            "nonzero_selected": False,
                            "robust_improvement_fraction": 0.0,
                        },
                    }
                )
                action = r8r7.r4.zero_action(self.step)
                event_name = "safe_zero_fallback"
                event = {"event": event_name, "task_step": self.step, "passed": True}
            self.r8r8_decisions.append(copy.deepcopy(decision))
        elif self.step in tuple(value + 1 for value in contract.DECISION_STEPS):
            if self._active_issue is not None:
                event = mpc.construct_cancel(
                    task_step=self.step,
                    currents_a_tsc=current_state["currents_a_tsc"],
                    issue_event=self._active_issue,
                    actuator=self.actuator,
                    controller_cfg=self.r8r8_cfg["controller_contract"],
                    lattice_cfg=self.lattice_cfg,
                )
                if not event["passed"]:
                    raise ValueError("R8R8 selected cancellation failed before plant advance")
                action = np.asarray(event["action_norm_tsc"], dtype=float)
                self._active_issue = None
                event_name = "mpc_cancel"
            else:
                event_name = "mpc_zero_cancel_slot"
                event = {"event": event_name, "task_step": self.step, "passed": True}
        return self._finish_trace(
            trace,
            np.asarray(action, dtype=float),
            event_name=event_name,
            event=event,
            decision=decision,
            delegated=False,
        )


class LocalWorker:
    """One fresh authentic TSC process and one R8R8 MPC controller."""

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
        inherited_controller_cfg: dict[str, Any],
        r8r8_cfg: dict[str, Any],
        observer_cfg: dict[str, Any],
        response_cfg: dict[str, Any],
        r8r7_cfg: dict[str, Any],
        model_bundle: dict[str, Any],
    ):
        self.plant = r8r7.r8.d1r11.s21.s16.s9.t11.t1.r1.LocalPlantReplayWorker(
            payload, library, bundle, worker_id, selector
        )
        self.base = self.plant.base_worker
        self.bundle = bundle
        self.lattice_cfg = lattice_cfg
        self.calibration_cfg = calibration_cfg
        self.dynamic_cfg = dynamic_cfg
        self.schedule_cfg = schedule_cfg
        self.inherited_controller_cfg = inherited_controller_cfg
        self.r8r8_cfg = r8r8_cfg
        self.observer_cfg = observer_cfg
        self.response_cfg = response_cfg
        self.r8r7_cfg = r8r7_cfg
        self.model_bundle = model_bundle

    def close(self) -> None:
        self.plant.close()

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        failed = True
        trajectory: list[dict[str, Any]] = []
        trace: list[dict[str, Any]] = []
        result: dict[str, Any] = {
            "schema_version": 1,
            "stage": contract.STAGE,
            "campaign_identity": contract.IDENTITY,
            "controller_revision": contract.CONTROLLER_REVISION,
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
                horizon != r8r7.r8.d1r11.s21.s13._formal_horizon(float(spec["slew_scale"]))
                or horizon != int(spec["formal_horizon_steps"])
                or horizon != int(self.base.env.max_episode_steps)
            ):
                raise ValueError("R8R8 formal horizon changed")
            self.base.env.reset()
            zero = np.zeros(N_COILS, dtype=np.float32)
            trajectory.append(
                r8r7.r8.d1r11.s21.s16.s9.t11.t1.r1._state_record_full(self.base.env, 0, zero)
            )
            controller = CausalDiscretePulseMPCController(
                self.base,
                self.bundle,
                spec,
                trajectory[0],
                self.lattice_cfg,
                self.calibration_cfg,
                self.dynamic_cfg,
                self.schedule_cfg,
                self.inherited_controller_cfg,
                self.r8r8_cfg,
                self.observer_cfg,
                self.response_cfg,
                self.r8r7_cfg,
                self.model_bundle,
                spec["r8r8_numeric_target_offsets"],
            )
            for step in range(horizon):
                action, row = controller.action(trajectory[-1])
                _, _, terminated, truncated, info = self.base.env.step(action)
                next_state = r8r7.r8.d1r11.s21.s16.s9.t11.t1.r1._state_record_full(
                    self.base.env, step + 1, action
                )
                trajectory.append(next_state)
                trace.append(row)
                controller.advance(next_state)
                if terminated:
                    result["execution_failure_class"] = "plant_abnormal_termination"
                    raise RuntimeError(str(info.get("failure_reason", "environment terminated")))
                if truncated and step + 1 < horizon:
                    result["execution_failure_class"] = "plant_early_truncation"
                    raise RuntimeError("environment truncated before R8R8 horizon")
            calibration_events = [
                row.get("r3c3t13s16_lattice_event")
                for row in trace[:PREFIX_END]
                if row.get("r3c3t13s16_lattice_event") != "none"
            ]
            actions = np.asarray([row["action_norm_tsc"] for row in trace], dtype=float)
            currents = np.asarray([row["currents_a_tsc"] for row in trajectory], dtype=float)
            decision_rows = [
                row["r3c3t13s24d1r14r8r8_decision"]
                for row in trace
                if row.get("r3c3t13s24d1r14r8r8_decision")
            ]
            nonzero = sum(bool(row["selection"]["nonzero_selected"]) for row in decision_rows)
            issue_events = sum(row.get("r3c3t13s24d1r14r8r8_event") == "mpc_issue" for row in trace)
            cancel_events = sum(row.get("r3c3t13s24d1r14r8r8_event") == "mpc_cancel" for row in trace)
            success = bool(
                len(trajectory) == horizon + 1
                and len(trace) == horizon
                and calibration_events == r8r7.r4.EXPECTED_CALIBRATION
                and bool(trace[7].get("r3c3t13s21_exact_calibration_net_zero"))
                and all(bool(row.get("r3c3t13s24d1r14r8r8_delegated_prefix")) for row in trace[:PREFIX_END])
                and all(not bool(row.get("r3c3t13s24d1r14r8r8_delegated_prefix")) for row in trace[PREFIX_END:])
                and len(decision_rows) == 4
                and all(len(row.get("candidate_forecasts") or []) == 9 for row in decision_rows)
                and all(len(row.get("candidate_constructions") or []) == 8 for row in decision_rows)
                and controller.r8r8_model_fault_count == 0
                and nonzero == issue_events == cancel_events
                and controller._active_issue is None
                and not any(bool(row.get("abnormal")) for row in trajectory)
                and np.all(np.isfinite(actions))
                and np.all(np.isfinite(currents))
            )
            result.update(
                {
                    "success": success,
                    "completed": True,
                    "failure_reason": "" if success else "incomplete or invalid R8R8 MPC rollout",
                    "execution_failure_class": "" if success else "controller_or_action_semantics_error",
                    "hidden_history_control_summary": {
                        "fresh_controller_actor": True,
                        "fresh_tsc_process": True,
                        "full_tsc_hidden_state_loaded_from_sprsina": True,
                        "future_r17_controller_executed": False,
                        "decision_count": len(decision_rows),
                        "selected_nonzero_count": nonzero,
                        "model_fault_count": controller.r8r8_model_fault_count,
                        "adaptation_enabled": False,
                        "future_action_replay_used": False,
                        "future_measurement_used": False,
                        "pair_or_history_label_used": False,
                        "source_result_used": False,
                        "stage_trajectory_allowed_in_expert_dataset": False,
                    },
                    "wall_time_s": time.time() - started,
                }
            )
            failed = not success
            return r8r7.r8.d1r11.s21.s16.s9.t11.t1._json_safe(result)
        except Exception as exc:
            result.update(
                {
                    "success": False,
                    "completed": True,
                    "failure_reason": repr(exc),
                    "execution_failure_class": str(result.get("execution_failure_class") or "runtime_or_controller_error"),
                    "trajectory": trajectory,
                    "controller_trace": trace,
                    "traceback": traceback.format_exc(),
                    "wall_time_s": time.time() - started,
                }
            )
            return r8r7.r8.d1r11.s21.s16.s9.t11.t1._json_safe(result)
        finally:
            runner = getattr(self.base.env, "runner", None)
            if runner is not None:
                runner.cleanup_episode_workspace(failed=failed, reason="stage4_2r3c3t13s24d1r14r8r8")


_RAY_ACTOR = None


def _ray_actor_class():
    global _RAY_ACTOR
    if _RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class Stage42R8R8Actor:
            def __init__(self, *args: Any):
                self.worker = LocalWorker(*args)

            def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
                return self.worker.evaluate(spec)

            def close(self) -> bool:
                self.worker.close()
                return True

        _RAY_ACTOR = Stage42R8R8Actor
    return _RAY_ACTOR


def _result_complete(path: Path, spec: Mapping[str, Any], *, success: bool = True) -> bool:
    if not path.is_file():
        return False
    try:
        result = r8r7.r8._read_gz(path)
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


def evaluate_specs(ctx: Context, *, backend: str, resume: bool) -> dict[str, Any]:
    specs = _saved_specs(ctx)
    pending = [
        spec
        for spec in specs
        if not (resume and _result_complete(ctx.paths.raw / f"{spec['experiment_id']}.json.gz", spec))
    ]
    payloads = {str(spec["experiment_id"]): _payload(ctx, spec) for spec in specs}
    execution = r8r7._execution_context(ctx.source_ctx)
    library, bundle, selector = r8r7.r8.d1r11._library_bundle_selector(execution.d1r11_ctx)
    lattice = execution.d1r11_ctx.base_ctx.base_ctx.cfg["lattice_probe"]
    calibration = execution.d1r11_ctx.base_ctx.base_ctx.cfg["active_calibration"]
    dynamic = execution.d1r11_ctx.base_ctx.cfg["causal_model"]
    schedule = execution.d1r11_ctx.cfg["schedule_contract"]
    inherited = copy.deepcopy(ctx.source_ctx.cfg["controller_contract"])
    inherited.update(
        {
            "requested_coordinate_matrix_columns": copy.deepcopy(
                ctx.source_ctx.cfg["schedule_contract"]["canonical_matrix_columns"]
            ),
            "requested_matrix_float64_le_c_sha256": str(
                ctx.source_ctx.cfg["schedule_contract"]["canonical_matrix_digest"]
            ),
        }
    )
    models = _model_bundle(ctx, output_paths=False)
    response_cfg = r8r1.model_config(ctx.source_ctx.r8r1_cfg, ctx.source_ctx.r8_cfg)

    def worker_args(spec: Mapping[str, Any], index: int) -> tuple[Any, ...]:
        return (
            payloads[str(spec["experiment_id"])],
            library,
            bundle,
            f"stage42r8r8_{index:02d}",
            selector,
            lattice,
            calibration,
            dynamic,
            schedule,
            inherited,
            ctx.cfg,
            ctx.source_ctx.r8r6_cfg,
            response_cfg,
            ctx.source_ctx.cfg,
            models,
        )

    if backend == "serial":
        for index, spec in enumerate(pending):
            worker = LocalWorker(*worker_args(spec, index))
            try:
                result = worker.evaluate(spec)
            finally:
                worker.close()
            r8r7.r8._write_gz(ctx.paths.raw / f"{spec['experiment_id']}.json.gz", result)
            print(f"[R8R8] {index + 1}/{len(pending)}", flush=True)
    elif backend == "ray" and pending:
        import ray

        plan = r8r7.r8.d1r11.s21.s16.ensure_ray_worker_plan(
            ray,
            requested_workers=int(ctx.cfg["parallel"]["n_workers"]),
            pending_tasks=len(pending),
            ray_tmpdir=os.environ.get("RAY_TMPDIR") or ctx.cfg["storage"]["ray_tmpdir"],
            log_prefix="[R8R8]",
        )
        Actor = _ray_actor_class()
        completed = 0
        for start in range(0, len(pending), plan.actor_count):
            batch = pending[start : start + plan.actor_count]
            actors, refs = [], {}
            for offset, spec in enumerate(batch):
                actor = Actor.remote(*worker_args(spec, start + offset))
                actors.append(actor)
                refs[actor.evaluate.remote(spec)] = spec
            try:
                while refs:
                    ready, _ = ray.wait(list(refs), num_returns=1, timeout=30.0)
                    if not ready:
                        print(f"[R8R8] waiting {completed}/{len(pending)}", flush=True)
                        continue
                    ref = ready[0]
                    spec = refs.pop(ref)
                    try:
                        result = ray.get(ref)
                    except Exception as exc:
                        result = {
                            "schema_version": 1,
                            "stage": contract.STAGE,
                            "campaign_identity": contract.IDENTITY,
                            "controller_revision": contract.CONTROLLER_REVISION,
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
                    r8r7.r8._write_gz(ctx.paths.raw / f"{spec['experiment_id']}.json.gz", result)
                    completed += 1
                    print(f"[R8R8] {completed}/{len(pending)}", flush=True)
            finally:
                close_refs = [actor.close.remote() for actor in actors]
                if close_refs:
                    ray.get(close_refs, timeout=float(ctx.cfg["storage"]["actor_close_timeout_s"]))
                for actor in actors:
                    ray.kill(actor, no_restart=True)
    elif backend not in {"serial", "ray"}:
        raise ValueError(f"unsupported R8R8 backend: {backend}")
    successful = sum(
        _result_complete(ctx.paths.raw / f"{spec['experiment_id']}.json.gz", spec)
        for spec in specs
    )
    return {
        "expected": len(specs),
        "pending_at_start": len(pending),
        "successful": successful,
        "passed": successful == len(specs),
    }


def run_real(ctx: Context, *, backend: str, resume: bool) -> dict[str, Any]:
    _require(ctx, "real_authorized")
    result = evaluate_specs(ctx, backend=backend, resume=resume)
    state = _read(ctx.paths.state)
    inventory = r8r7.r8._inventory(ctx.paths.raw)
    state.update(
        {
            "phase_status": "real_raw_ready" if result["passed"] else "real_execution_failed",
            "finished": not result["passed"],
            "real_tsc_executed": inventory["count"] > 0,
            "new_raw_count": inventory["count"],
            "raw_inventory_digest": inventory["digest"],
            "stop_reason": "" if result["passed"] else "runtime_restart_action_current_or_raw_gate_failed",
            "verdict": {} if result["passed"] else {"route": ctx.cfg["routes"]["execution_fail"], "passed": False},
        }
    )
    _write(ctx.paths.state, state)
    return result


R8R8_FORBIDDEN_TRACE_KEYS = tuple(
    dict.fromkeys(
        r8r7.R8R7_FORBIDDEN_TRACE_KEYS
        + (
            "r3c3t13s24d1r14r8r8_pair_or_history_label_used",
            "r3c3t13s24d1r14r8r8_partition_label_used",
            "r3c3t13s24d1r14r8r8_source_result_used",
            "r3c3t13s24d1r14r8r8_source_formal_outcome_used",
            "r3c3t13s24d1r14r8r8_future_measurement_used",
            "r3c3t13s24d1r14r8r8_future_executed_action_used",
            "r3c3t13s24d1r14r8r8_hidden_wire_current_used",
        )
    )
)


def audit_primary(ctx: Context) -> dict[str, Any]:
    _require(ctx, "real_raw_ready")
    specs = _saved_specs(ctx)
    sources = _source_baselines(ctx)
    evaluators, _ = r8r7.r8.d1r11._formal_callback(ctx.source_ctx.r8_ctx.d1r11_ctx, specs)
    rows = []
    detailed_decisions = []
    for spec in specs:
        experiment_id = str(spec["experiment_id"])
        path = ctx.paths.raw / f"{experiment_id}.json.gz"
        if not _result_complete(path, spec, success=False):
            rows.append({"experiment_id": experiment_id, "runtime_success": False, "passed": False})
            continue
        result = r8r7.r8._read_gz(path)
        trajectory = result.get("trajectory") or []
        trace = result.get("controller_trace") or []
        source = sources[str(spec["source_r8r7_baseline_experiment_id"])]
        horizon = int(spec["horizon_steps"])
        full = len(trajectory) == horizon + 1 and len(trace) == horizon
        prefix_state = bool(
            full
            and all(
                r8r7.r8.r4._semantic_state(current) == r8r7.r8.r4._semantic_state(reference)
                for current, reference in zip(
                    trajectory[: PREFIX_END + 1], source["trajectory"][: PREFIX_END + 1]
                )
            )
        )
        prefix_trace = bool(
            full
            and all(
                r8r7.r8.r4._source_trace_projection(reference, current)
                for current, reference in zip(
                    trace[:PREFIX_END], source["controller_trace"][:PREFIX_END]
                )
            )
        )
        calibration = r8r7.r8.r4._calibration_exact(trace)
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
        forbidden = sum(any(bool(row.get(key)) for key in R8R8_FORBIDDEN_TRACE_KEYS) for row in trace)
        decisions = [
            row.get("r3c3t13s24d1r14r8r8_decision")
            for row in trace
            if row.get("r3c3t13s24d1r14r8r8_decision")
        ]
        decision_complete = bool(
            len(decisions) == 4
            and [int(row["task_step"]) for row in decisions] == list(contract.DECISION_STEPS)
            and all(len(row.get("candidate_forecasts") or []) == 9 for row in decisions)
            and all(len(row.get("candidate_constructions") or []) == 8 for row in decisions)
            and not any(bool(row.get("model_fault")) for row in decisions)
        )
        nonzero = sum(bool(row["selection"]["nonzero_selected"]) for row in decisions)
        issue_events = [row for row in trace if row.get("r3c3t13s24d1r14r8r8_event") == "mpc_issue"]
        cancel_events = [row for row in trace if row.get("r3c3t13s24d1r14r8r8_event") == "mpc_cancel"]
        exact_events = bool(
            len(issue_events) == len(cancel_events) == nonzero
            and all((row.get("r3c3t13s24d1r14r8r8_event_detail") or {}).get("passed") is True for row in issue_events + cancel_events)
            and all(
                all(bool(value) for value in ((row.get("r3c3t13s24d1r14r8r8_event_detail") or {}).get("criteria") or {}).values())
                for row in issue_events + cancel_events
            )
        )
        improvement = bool(
            all(
                not row["selection"]["nonzero_selected"]
                or float(row["selection"]["robust_improvement_fraction"])
                >= float(ctx.cfg["execution_gates"]["minimum_selected_nonzero_improvement_fraction"]) - 1e-15
                for row in decisions
            )
        )
        payload = _read(ctx.paths.variants / f"payload_{experiment_id}.json")
        minimum, maximum = r8r7.r8.d1r11.s21.s13._current_limits_tsc(payload)
        center, half = 0.5 * (minimum + maximum), 0.5 * (maximum - minimum)
        utilization = float(np.max(np.abs((currents - center) / half))) if finite else None
        action_abs = float(np.max(np.abs(actions))) if finite else None
        formal = False
        if full:
            values = np.asarray([[row["R"], row["Z"], row["Ip"]] for row in trajectory], dtype=float)
            formal = bool(evaluators[experiment_id].evaluate(values)["formal_contract_pass"])
        passed = bool(
            result.get("success")
            and full
            and prefix_state
            and prefix_trace
            and calibration
            and finite
            and forbidden == 0
            and decision_complete
            and exact_events
            and improvement
            and action_abs is not None
            and action_abs <= float(ctx.cfg["controller_contract"]["maximum_total_normalized_action_abs"]) + 1e-12
            and utilization is not None
            and utilization <= float(ctx.cfg["controller_contract"]["maximum_current_utilization"]) + 1e-12
        )
        rows.append(
            {
                "experiment_id": experiment_id,
                "runtime_success": bool(result.get("success")),
                "full_horizon": full,
                "source_prefix_state_exact": prefix_state,
                "source_prefix_trace_exact": prefix_trace,
                "calibration_exact": calibration,
                "finite": finite,
                "forbidden_trace_count": forbidden,
                "decision_complete": decision_complete,
                "decision_count": len(decisions),
                "selected_nonzero_count": nonzero,
                "exact_issue_count": len(issue_events),
                "exact_cancel_count": len(cancel_events),
                "selected_improvement_gate": improvement,
                "maximum_total_normalized_action_abs": action_abs,
                "maximum_current_utilization": utilization,
                "formal_contract_pass": formal,
                "failure_reason": str(result.get("failure_reason") or ""),
                "passed": passed,
            }
        )
        detailed_decisions.extend(
            {
                "experiment_id": experiment_id,
                **copy.deepcopy(decision),
            }
            for decision in decisions
        )
    inventory = r8r7.r8._inventory(ctx.paths.raw)
    execution_pass = bool(
        inventory["count"] == 16
        and len(rows) == 16
        and sum(bool(row.get("passed")) for row in rows) == 16
        and sum(int(row.get("decision_count", 0)) for row in rows) == 64
        and sum(int(row.get("selected_nonzero_count", 0)) for row in rows)
        >= int(ctx.cfg["execution_gates"]["minimum_nonzero_issue_count"])
    )
    formal_count = sum(bool(row.get("formal_contract_pass")) for row in rows)
    scientific = bool(execution_pass and formal_count == 16)
    route = ctx.cfg["routes"][
        "pass" if scientific else ("formal_fail" if execution_pass else "execution_fail")
    ]
    detailed = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "phase": "authentic_causal_discrete_pulse_mpc_core_primary",
        "raw_inventory": inventory,
        "execution_pass_count": sum(bool(row.get("passed")) for row in rows),
        "decision_record_count": sum(int(row.get("decision_count", 0)) for row in rows),
        "selected_nonzero_issue_count": sum(int(row.get("selected_nonzero_count", 0)) for row in rows),
        "exact_issue_count": sum(int(row.get("exact_issue_count", 0)) for row in rows),
        "exact_cancel_count": sum(int(row.get("exact_cancel_count", 0)) for row in rows),
        "forbidden_trace_count": sum(int(row.get("forbidden_trace_count", 0)) for row in rows),
        "formal_contract_pass_count": formal_count,
        "formal_contract_required": 16,
        "execution_gate_passed": execution_pass,
        "scientific_gate_passed": scientific,
        "rows": rows,
        "decision_rows": detailed_decisions,
        "route": route,
        "all_stage_trajectories_allowed_in_expert_dataset": False,
        "gate_a_qualified": False,
        "passed": True,
    }
    detailed_path = ctx.paths.analysis / "primary_detailed.json"
    _write(detailed_path, detailed)
    summary = {key: value for key, value in detailed.items() if key not in {"rows", "decision_rows"}}
    summary["primary_detailed_sha256"] = _sha(detailed_path)
    _write(ctx.paths.analysis / "primary_summary.json", summary)
    state = _read(ctx.paths.state)
    state.update(
        {
            "phase_status": "primary_ready",
            "primary_summary_sha256": _sha(ctx.paths.analysis / "primary_summary.json"),
            "proposed_route": route,
        }
    )
    _write(ctx.paths.state, state)
    return summary


def finalize(ctx: Context) -> dict[str, Any]:
    state = _require(ctx, "primary_ready")
    primary_path = ctx.paths.analysis / "primary_summary.json"
    independent_path = ctx.paths.analysis / "final_independent.json"
    if not independent_path.is_file():
        raise ValueError("R8R8 final independent audit missing")
    primary = _read(primary_path)
    independent = _read(independent_path)
    if (
        independent.get("passed") is not True
        or independent.get("primary_numerical_agreement") is not True
        or independent.get("primary_outcome_agreement") is not True
        or independent.get("primary_sha256") != _sha(primary_path)
        or independent.get("route") != primary.get("route")
        or state.get("primary_summary_sha256") != _sha(primary_path)
    ):
        raise ValueError("R8R8 final independent agreement failed")
    final = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "phase": "final_causal_discrete_pulse_mpc_core",
        "execution_pass_count": int(primary["execution_pass_count"]),
        "decision_record_count": int(primary["decision_record_count"]),
        "selected_nonzero_issue_count": int(primary["selected_nonzero_issue_count"]),
        "exact_issue_count": int(primary["exact_issue_count"]),
        "exact_cancel_count": int(primary["exact_cancel_count"]),
        "formal_contract_pass_count": int(primary["formal_contract_pass_count"]),
        "formal_contract_required": 16,
        "execution_gate_passed": bool(primary["execution_gate_passed"]),
        "scientific_gate_passed": bool(primary["scientific_gate_passed"]),
        "primary_summary_sha256": _sha(primary_path),
        "independent_sha256": _sha(independent_path),
        "route": str(primary["route"]),
        "classification": (
            "finite deterministic causal MPC-core PASS; robustness qualification required"
            if primary["scientific_gate_passed"]
            else (
                "finite causal controller-design failure"
                if primary["execution_gate_passed"]
                else "execution/restart/causality/integrity/safety failure"
            )
        ),
        "gate_a_qualified": False,
        "all_stage_trajectories_allowed_in_expert_dataset": False,
        "expert_data_bc_dagger_rl_allowed": False,
        "passed": True,
    }
    _write(ctx.paths.analysis / "final_report.json", final)
    state.update(
        {
            "phase_status": "finished",
            "finished": True,
            "stop_reason": "" if final["scientific_gate_passed"] else "deterministic_core_gate_failed",
            "final_report_sha256": _sha(ctx.paths.analysis / "final_report.json"),
            "independent_sha256": _sha(independent_path),
            "verdict": {
                "route": final["route"],
                "passed": bool(final["scientific_gate_passed"]),
            },
        }
    )
    _write(ctx.paths.state, state)
    return final


def postprocess(ctx: Context) -> dict[str, Any]:
    state = _read(ctx.paths.state)
    if state.get("phase_status") == "real_raw_ready":
        return audit_primary(ctx)
    if state.get("phase_status") == "primary_ready":
        return finalize(ctx)
    if state.get("phase_status") == "finished":
        return _read(ctx.paths.analysis / "final_report.json")
    raise ValueError(f"R8R8 postprocess cannot continue from {state.get('phase_status')!r}")


def execute(ctx: Context, *, command: str, backend: str, resume: bool) -> dict[str, Any]:
    if command == "offline":
        return prepare_offline(ctx)
    if command == "authorize-real":
        return authorize_real(ctx)
    if command == "run":
        return run_real(ctx, backend=backend, resume=resume)
    if command == "audit-primary":
        return audit_primary(ctx)
    if command == "finalize":
        return finalize(ctx)
    if command == "postprocess":
        return postprocess(ctx)
    raise ValueError(f"unsupported R8R8 command: {command}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--r8r7-run", type=Path, required=True)
    parser.add_argument("--r8-run", type=Path, required=True)
    parser.add_argument("--r8r1-output", type=Path, required=True)
    parser.add_argument("--r8r6-run", type=Path, required=True)
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
        choices=("offline", "authorize-real", "run", "audit-primary", "finalize", "postprocess"),
        required=True,
    )
    parser.add_argument("--backend", choices=("serial", "ray"), default="ray")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.self_test:
        print(json.dumps(contract.self_test(args.config), indent=2, sort_keys=True, allow_nan=False))
        return
    ctx = load_context(args)
    result = execute(ctx, command=args.command, backend=args.backend, resume=args.resume)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
