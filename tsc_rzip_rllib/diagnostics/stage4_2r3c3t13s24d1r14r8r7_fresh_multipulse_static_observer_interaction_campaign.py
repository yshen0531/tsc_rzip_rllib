"""Execute and audit the frozen R8R7 fresh multipulse interaction sentinel."""

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

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r7_causal_response_model as r7_source,
)
from scripts import (
    stage4_2r3c3t13s24d1r14r8r1_fixed_candidate_short_horizon_discriminator as r8r1_primary,
    stage4_2r3c3t13s24d1r14r8r3_causal_history_no_action_observer as r8r3_primary,
)
from tsc_rzip_rllib.control import action_conditioned_history_response_model as response_model
from tsc_rzip_rllib.control import causal_history_no_action_observer as observer
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r4_time_shifted_sign_split_sentinel as r4,
    stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification as r8,
    stage4_2r3c3t13s24d1r14r8r1_fixed_candidate_short_horizon_discriminator as r8r1,
    stage4_2r3c3t13s24d1r14r8r3_causal_history_no_action_observer as r8r3_contract,
    stage4_2r3c3t13s24d1r14r8r4_fresh_causal_observer_campaign as r8r4,
    stage4_2r3c3t13s24d1r14r8r6_causal_one_step_innovation_observer_audit as r8r6_audit,
    stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_sentinel as contract,
)


PHASES = ("baseline", "multipulse")
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
    stage: Path
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
            raise ValueError(f"invalid R8R7 phase: {phase}")
        return self.raw / phase


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
    r8_cfg: dict[str, Any]
    r8_config_path: Path
    r8r1_cfg: dict[str, Any]
    r8r1_config_path: Path
    r8r6_cfg: dict[str, Any]
    r8r6_config_path: Path
    r8_run: Path
    r8r1_output: Path
    r8r6_run: Path
    r8_ctx: r8.Context
    source_r2_run: Path
    source_r4_run: Path
    source_r6_run: Path


def load_context(args: argparse.Namespace) -> Context:
    config_path = args.config.expanduser().resolve()
    cfg = _read(config_path)
    contract.validate_config(cfg, project_root=_root())
    r8_config = (_root() / str(cfg["source_r8_config"])).resolve()
    r8r1_config = (_root() / str(cfg["source_r8r1_config"])).resolve()
    r8r6_config = (_root() / str(cfg["source_r8r6_config"])).resolve()
    r8_cfg, r8r1_cfg, r8r6_cfg = map(_read, (r8_config, r8r1_config, r8r6_config))
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
        r8r1_cfg=r8r1_cfg,
        r8r1_config_path=r8r1_config,
        r8r6_cfg=r8r6_cfg,
        r8r6_config_path=r8r6_config,
        r8_run=args.r8_run.expanduser().resolve(),
        r8r1_output=args.r8r1_output.expanduser().resolve(),
        r8r6_run=args.r8r6_run.expanduser().resolve(),
        r8_ctx=r8_ctx,
        source_r2_run=args.source_r2_run.expanduser().resolve(),
        source_r4_run=args.source_r4_run.expanduser().resolve(),
        source_r6_run=args.source_r6_run.expanduser().resolve(),
    )


def _package_fingerprint() -> dict[str, Any]:
    names = (
        "configs/stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_sentinel_370ms.json",
        "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r7_independent_forensics.py",
        "docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R7_FRESH_MULTIPULSE_STATIC_OBSERVER_INTERACTION_SENTINEL_DESIGN.md",
        "scripts/stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_campaign.py",
        "scripts/stage4_2r3c3t13s24d1r14r8r7_shell_common.sh",
        "tests/test_stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_sentinel.py",
        "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_sentinel.py",
        "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_campaign.py",
    )
    rows = []
    for name in names:
        path = _root() / name
        if not path.is_file():
            raise ValueError(f"R8R7 package source missing: {name}")
        rows.append({"path": name, "bytes": path.stat().st_size, "sha256": _sha(path)})
    return {"files": rows, "digest": r8._digest(rows)}


def _authenticate_r8(ctx: Context) -> dict[str, Any]:
    return r8r4._authenticate_r8(ctx)  # type: ignore[arg-type]


def _authenticate_r8r1(ctx: Context) -> dict[str, Any]:
    expected = ctx.cfg["source_r8r1_contract"]
    if ctx.r8r1_output.name != str(expected["output_name"]):
        raise ValueError("R8R7 R8R1 output identity changed")
    paths = {
        "primary_detailed": ctx.r8r1_output / "primary_detailed.json",
        "primary_summary": ctx.r8r1_output / "primary_summary.json",
        "independent": ctx.r8r1_output / "independent.json",
    }
    if any(
        not path.is_file() or _sha(path) != str(expected[f"{name}_sha256"])
        for name, path in paths.items()
    ):
        raise ValueError("R8R7 R8R1 evidence hash changed")
    detailed, summary, independent = map(_read, paths.values())
    horizon = detailed["horizons"][str(expected["required_horizon"])]
    if (
        detailed.get("route") != expected["required_route"]
        or detailed.get("scientific_gate_passed") is not False
        or summary.get("route") != expected["required_route"]
        or independent.get("primary_numerical_agreement") is not True
        or independent.get("primary_outcome_agreement") is not True
        or int(horizon["aggregate"]["response_count"]) != int(expected["required_response_count"])
        or int(horizon["aggregate"]["response_pass_count"])
        != int(expected["required_response_pass_count"])
        or int(horizon["actual_geometry"]["canonical"]["condition_pass_count"])
        != int(expected["required_canonical_condition_pass_count"])
        or int(horizon["actual_geometry"]["operational"]["condition_pass_count"])
        != int(expected["required_operational_condition_pass_count"])
    ):
        raise ValueError("R8R7 R8R1 scientific boundary changed")
    return {name + "_sha256": _sha(path) for name, path in paths.items()}


def _r8r6_paths(ctx: Context) -> r8r6_audit.Paths:
    return r8r6_audit._paths(ctx.r8r6_run)


def _authenticate_r8r6(ctx: Context) -> dict[str, Any]:
    expected = ctx.cfg["source_r8r6_contract"]
    if ctx.r8r6_run.name != str(expected["run_name"]):
        raise ValueError("R8R7 R8R6 run identity changed")
    paths = _r8r6_paths(ctx)
    files = {
        "stage_manifest": paths.manifest,
        "stage_state": paths.state,
        "primary_detailed": paths.analysis / "primary_detailed.json",
        "primary_summary": paths.analysis / "primary_summary.json",
        "independent": paths.analysis / "independent.json",
        "final_report": paths.analysis / "final_report.json",
        "observer_model": paths.model / "observer_model.json",
        "observer_tube": paths.model / "observer_tube.json",
        "innovation_contract": paths.model / "innovation_contract.json",
    }
    if any(
        not path.is_file() or _sha(path) != str(expected[f"{name}_sha256"])
        for name, path in files.items()
    ):
        raise ValueError("R8R7 R8R6 evidence or artifact hash changed")
    state = _read(paths.state)
    final = _read(files["final_report"])
    innovation_value = _read(files["innovation_contract"])
    if (
        state.get("finished") is not True
        or (state.get("verdict") or {}).get("route") != expected["required_route"]
        or final.get("route") != expected["required_route"]
        or final.get("observer_qualification_passed") is not True
        or innovation_value.get("adaptation_enabled")
        is not bool(expected["required_adaptation_enabled"])
    ):
        raise ValueError("R8R7 R8R6 outcome changed")
    return {name + "_sha256": _sha(path) for name, path in files.items()}


def _response_preflight(ctx: Context) -> dict[str, Any]:
    items, r8_cfg, authentication, _ = r8r1_primary._source_items(
        ctx.r8r1_cfg,
        ctx.r8r1_config_path,
        ctx.r8_run,
        ctx.source_r2_run,
        ctx.source_r4_run,
        ctx.source_r6_run,
    )
    rows_by_horizon, folds = r8r1.outer_prediction_rows(items, ctx.r8r1_cfg, r8_cfg)
    horizon = int(ctx.cfg["response_model_contract"]["relative_lag_horizon"])
    rows = rows_by_horizon[horizon]
    evaluation = r8r1.evaluate_horizon(items, rows, horizon, ctx.r8r1_cfg, r8_cfg)
    expected = ctx.cfg["source_r8r1_contract"]
    if (
        len(folds) != 12
        or int(evaluation["aggregate"]["response_count"]) != int(expected["required_response_count"])
        or int(evaluation["aggregate"]["response_pass_count"])
        != int(expected["required_response_pass_count"])
    ):
        raise ValueError("R8R7 R8R1 40 ms reproduction changed")
    item_by_id = {str(item["response_id"]): item for item in items}
    scales = np.asarray(ctx.cfg["bank_contract"]["response_scales"], dtype=float)
    residuals = np.asarray(
        [
            np.abs(
                np.asarray(row["predicted_response"], dtype=float)
                - np.asarray(item_by_id[str(row["response_id"])]["response"][:horizon], dtype=float)
            )
            * scales[None, :]
            for row in rows
        ],
        dtype=float,
    )
    response_tube = (
        np.asarray(ctx.cfg["tube_contract"]["response_floor_physical"], dtype=float)[None, :]
        + float(ctx.cfg["tube_contract"]["response_multiplier"])
        * np.max(residuals, axis=0)
    )
    candidate = response_model.Candidate(
        int(ctx.cfg["response_model_contract"]["pca_rank"]),
        float(ctx.cfg["response_model_contract"]["bandwidth_multiplier"]),
        float(ctx.cfg["response_model_contract"]["ridge"]),
    )
    mcfg = r8r1.model_config(ctx.r8r1_cfg, r8_cfg)
    truncated = [r8r1.truncate_item(item, horizon) for item in items]
    fitted = response_model.fit_model(truncated, candidate, mcfg)
    artifact = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "campaign_identity": contract.IDENTITY,
        "relative_lag_horizon": horizon,
        "fixed_candidate": candidate.as_dict(),
        "training_response_count": len(truncated),
        "training_pair_count": len({str(row["pair_id"]) for row in truncated}),
        "validation_claim": False,
        "model": response_model.serializable_model(fitted),
    }
    _write(ctx.paths.model / "response_model.json", artifact)
    _write(
        ctx.paths.model / "response_tube.json",
        {
            "schema_version": 1,
            "stage": contract.STAGE,
            "tube_physical": response_tube.tolist(),
            "derivation": ctx.cfg["tube_contract"]["response_method"],
            "source_oof_response_count": len(rows),
        },
    )
    static_tube = np.asarray(_read(_r8r6_paths(ctx).model / "observer_tube.json")["tube_physical"], dtype=float)
    if static_tube.shape != (12, 5):
        raise ValueError("R8R7 R8R6 static tube shape changed")
    combined = static_tube[:horizon] + response_tube
    caps = np.asarray(ctx.cfg["tube_contract"]["combined_caps_physical"], dtype=float)
    cap_pass = bool(np.all(combined <= caps[None, :] + 1e-15))
    _write(
        ctx.paths.model / "combined_tube.json",
        {
            "schema_version": 1,
            "stage": contract.STAGE,
            "static_observer_model_sha256": ctx.cfg["source_r8r6_contract"]["observer_model_sha256"],
            "static_observer_tube_sha256": ctx.cfg["source_r8r6_contract"]["observer_tube_sha256"],
            "response_model_sha256": _sha(ctx.paths.model / "response_model.json"),
            "response_tube_sha256": _sha(ctx.paths.model / "response_tube.json"),
            "combined_tube_physical": combined.tolist(),
            "combined_caps_physical": caps.tolist(),
            "cap_passed": cap_pass,
        },
    )
    if not cap_pass:
        raise ValueError("R8R7 combined tube exceeds a frozen cap")
    return {
        "source_authentication": authentication,
        "outer_fold_count": len(folds),
        "horizon_evaluation": r8r1.compact_horizon(evaluation),
        "response_model_sha256": _sha(ctx.paths.model / "response_model.json"),
        "response_tube_sha256": _sha(ctx.paths.model / "response_tube.json"),
        "combined_tube_sha256": _sha(ctx.paths.model / "combined_tube.json"),
        "combined_tube_cap_passed": cap_pass,
    }


def _new_specs(ctx: Context) -> list[dict[str, Any]]:
    blueprints = []
    allowed = set(contract.FRESH_PAIRS)
    for source_phase in ("calibration", "holdout"):
        blueprints.extend(
            row
            for row in r8._phase_specs(ctx.r8_ctx, source_phase)
            if str(row["d1r14r8_role"]) == "baseline"
            and str(row["pair_id"]) in allowed
        )
    blueprints = sorted(
        blueprints, key=lambda row: (str(row["pair_id"]), str(row["history_member"]))
    )
    contexts = {(str(row["pair_id"]), str(row["history_member"])) for row in blueprints}
    if len(blueprints) != 16 or len(contexts) != 16:
        raise ValueError("R8R7 fresh blueprint coverage changed")
    output = []
    matrix = np.asarray(ctx.cfg["schedule_contract"]["canonical_matrix_columns"], dtype=float)
    for index, original in enumerate(blueprints):
        source_id = str(original["experiment_id"])
        baseline = copy.deepcopy(original)
        baseline.update(
            {
                "kind": "stage4_2r3c3t13s24d1r14r8r7_fresh_baseline",
                "partition": "baseline",
                "experiment_id": f"r8r7_baseline_{index:02d}",
                "source_r8_blueprint_experiment_id": source_id,
                "r8r7_role": "baseline",
                "r8r7_schedule_index": -1,
                "r8r7_issue_task_steps": [],
                "r8r7_direction_indices": [],
                "r8r7_signs": [],
                "r8r7_requested_coordinates": [],
                "r8r7_allowed_in_expert_dataset": False,
            }
        )
        output.append(baseline)
        for schedule_index, (directions, signs) in enumerate(contract.SCHEDULES):
            spec = copy.deepcopy(original)
            spec.update(
                {
                    "kind": "stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse",
                    "partition": "multipulse",
                    "experiment_id": f"r8r7_multipulse_{index:02d}_{schedule_index}",
                    "source_r8_blueprint_experiment_id": source_id,
                    "r8r7_role": "multipulse",
                    "r8r7_schedule_index": schedule_index,
                    "r8r7_issue_task_steps": list(contract.ISSUE_STEPS),
                    "r8r7_direction_indices": list(directions),
                    "r8r7_signs": list(signs),
                    "r8r7_requested_coordinates": [
                        (matrix[:, direction] * sign).tolist()
                        for direction, sign in zip(directions, signs)
                    ],
                    "r8r7_allowed_in_expert_dataset": False,
                }
            )
            output.append(spec)
    if (
        len(output) != 48
        or sum(row["partition"] == "baseline" for row in output) != 16
        or sum(row["partition"] == "multipulse" for row in output) != 32
        or len({str(row["experiment_id"]) for row in output}) != 48
    ):
        raise ValueError("R8R7 specification coverage changed")
    return output


def prepare_offline(ctx: Context) -> dict[str, Any]:
    if ctx.paths.stage.exists():
        raise ValueError("R8R7 offline requires a fresh run identity")
    source_r8 = _authenticate_r8(ctx)
    source_r8r1 = _authenticate_r8r1(ctx)
    source_r8r6 = _authenticate_r8r6(ctx)
    specs = _new_specs(ctx)
    package = _package_fingerprint()
    for path in (
        ctx.paths.stage,
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
        _write(ctx.paths.specs / f"{phase}_specs.json", [row for row in specs if row["partition"] == phase])
    _write(ctx.paths.source_reference / "r8_authentication.json", source_r8)
    _write(ctx.paths.source_reference / "r8r1_authentication.json", source_r8r1)
    _write(ctx.paths.source_reference / "r8r6_authentication.json", source_r8r6)
    preflight = _response_preflight(ctx)
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
        "source_r8r1_output": str(ctx.r8r1_output),
        "source_r8r6_run": str(ctx.r8r6_run),
        "spec_count": len(specs),
        "spec_digest": r8._digest(specs),
        "response_model_sha256": preflight["response_model_sha256"],
        "response_tube_sha256": preflight["response_tube_sha256"],
        "combined_tube_sha256": preflight["combined_tube_sha256"],
        "static_observer_model_sha256": ctx.cfg["source_r8r6_contract"]["observer_model_sha256"],
        "static_observer_tube_sha256": ctx.cfg["source_r8r6_contract"]["observer_tube_sha256"],
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
            "phase_status": "offline_primary_ready",
            "finished": False,
            "real_tsc_executed": False,
            "new_raw_count": 0,
            "multipulse_outcomes_opened": False,
            "spec_digest": manifest["spec_digest"],
            "package_digest": package["digest"],
            "response_model_sha256": preflight["response_model_sha256"],
            "response_tube_sha256": preflight["response_tube_sha256"],
            "combined_tube_sha256": preflight["combined_tube_sha256"],
            "verdict": {},
        },
    )
    report = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "phase": "source_spec_model_tube_preflight",
        "source_r8_authenticated": True,
        "source_r8r1_authenticated": True,
        "source_r8r6_authenticated": True,
        "spec_count": len(specs),
        "baseline_spec_count": 16,
        "multipulse_spec_count": 32,
        "new_raw_count": 0,
        "real_tsc_executed": False,
        **preflight,
        "passed": True,
    }
    _write(ctx.paths.analysis / "offline_preflight.json", report)
    return report


def _saved_specs(ctx: Context) -> list[dict[str, Any]]:
    specs = _read(ctx.paths.specs / "all_specs.json")
    manifest = _read(ctx.paths.manifest)
    if (
        len(specs) != 48
        or r8._digest(specs) != manifest.get("spec_digest")
        or manifest.get("stage") != contract.STAGE
        or manifest.get("campaign_identity") != contract.IDENTITY
        or manifest.get("controller_revision") != contract.CONTROLLER_REVISION
        or _sha(ctx.config_path) != manifest.get("config_sha256")
    ):
        raise ValueError("R8R7 saved identity or specs changed")
    return specs


def _phase_specs(ctx: Context, phase: str) -> list[dict[str, Any]]:
    specs = [row for row in _saved_specs(ctx) if row["partition"] == phase]
    expected = {"baseline": 16, "multipulse": 32}
    if phase not in expected or len(specs) != expected[phase]:
        raise ValueError("R8R7 saved phase coverage changed")
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
            f"R8R7 phase guard expected {phase_status!r}, got {state.get('phase_status')!r}"
        )
    return state


def _independent(ctx: Context, name: str) -> dict[str, Any]:
    path = ctx.paths.analysis / f"{name}_independent.json"
    if not path.is_file():
        raise ValueError(f"R8R7 independent {name} audit missing")
    value = _read(path)
    if value.get("passed") is not True:
        raise ValueError(f"R8R7 independent {name} audit failed")
    return value


def authorize_baseline(ctx: Context) -> dict[str, Any]:
    state = _require(ctx, "offline_primary_ready")
    independent = _independent(ctx, "offline")
    primary = _read(ctx.paths.analysis / "offline_preflight.json")
    manifest = _read(ctx.paths.manifest)
    if (
        independent.get("primary_numerical_agreement") is not True
        or independent.get("primary_outcome_agreement") is not True
        or independent.get("artifact_hash_agreement") is not True
        or independent.get("primary_sha256") != _sha(ctx.paths.analysis / "offline_preflight.json")
        or independent.get("response_model_sha256") != state["response_model_sha256"]
        or independent.get("response_tube_sha256") != state["response_tube_sha256"]
        or independent.get("combined_tube_sha256") != state["combined_tube_sha256"]
        or primary.get("passed") is not True
        or manifest.get("combined_tube_sha256") != state["combined_tube_sha256"]
    ):
        raise ValueError("R8R7 offline independent agreement failed")
    _set_state(
        ctx,
        phase_status="baseline_authorized",
        offline_independent_sha256=_sha(ctx.paths.analysis / "offline_independent.json"),
    )
    return {"stage": contract.STAGE, "phase": "baseline_authorized", "passed": True}


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
    payload = r8._payload(_execution_context(ctx), spec)
    experiment_id = str(spec["experiment_id"])
    payload.update(
        {
            "variant_id": f"stage4_2r3c3t13s24d1r14r8r7_{experiment_id}",
            "stage4_2r3c3t13s24d1r14r8r7_role": str(spec["r8r7_role"]),
            "stage4_2r3c3t13s24d1r14r8r7_schedule_index": int(spec["r8r7_schedule_index"]),
            "stage4_2r3c3t13s24d1r14r8r7_pair_history_label_available_to_controller": False,
        }
    )
    _write(ctx.paths.variants / f"payload_{experiment_id}.json", payload)
    return payload


class FixedCanonicalMultipulseController(r4.MixedBasisSignedExcitationController):
    """Exact inherited prefix followed by zero or four fixed issue/cancel pairs."""

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
        controller_cfg: Mapping[str, Any],
    ):
        role = str(source_spec["r8r7_role"])
        directions = tuple(map(int, source_spec["r8r7_direction_indices"]))
        signs = tuple(map(int, source_spec["r8r7_signs"]))
        coordinates = tuple(
            tuple(map(float, row)) for row in source_spec["r8r7_requested_coordinates"]
        )
        if role == "baseline":
            init = {
                "role": "baseline",
                "direction_index": -1,
                "sign": 0,
                "requested_coordinate": [0.0] * 4,
                "issue_step": -1,
                "cancel_step": -1,
                "zero_after_step": PREFIX_END,
            }
        elif (
            role == "multipulse"
            and len(directions) == len(signs) == len(coordinates) == 4
            and tuple(map(int, source_spec["r8r7_issue_task_steps"])) == contract.ISSUE_STEPS
        ):
            inherited_issue_step = int(r4.ISSUE_STEPS[0])
            init = {
                "role": "signed_probe",
                "direction_index": directions[0],
                "sign": signs[0],
                "requested_coordinate": coordinates[0],
                "issue_step": inherited_issue_step,
                "cancel_step": inherited_issue_step + 1,
                "zero_after_step": inherited_issue_step + 2,
            }
        else:
            raise ValueError("R8R7 controller schedule changed")
        sanitized = r8._kernel_spec(source_spec)
        for key in list(sanitized):
            if key.startswith("r8r7_"):
                sanitized.pop(key)
        inherited = copy.deepcopy(dict(controller_cfg))
        inherited.update(
            {
                "requested_coordinate_matrix_columns": copy.deepcopy(
                    controller_cfg["requested_coordinate_matrix_columns"]
                ),
                "requested_matrix_float64_le_c_sha256": str(
                    controller_cfg["requested_matrix_float64_le_c_sha256"]
                ),
            }
        )
        super().__init__(
            base_worker,
            bundle,
            sanitized,
            initial_state,
            lattice_cfg,
            calibration_cfg,
            dynamic_cfg,
            schedule_cfg,
            inherited,
            **init,
        )
        self.r8r7_role = role
        self.r8r7_directions = directions
        self.r8r7_signs = signs
        self.r8r7_coordinates = coordinates
        if role == "multipulse":
            # The inherited constructor accepts only its historical R4 slots.
            # This subclass owns the frozen R8R7 four-slot clock in action().
            self.d1r14r4_issue_step = contract.ISSUE_STEPS[0]
            self.d1r14r4_cancel_step = contract.ISSUE_STEPS[0] + 1
            self.d1r14r4_zero_after_step = contract.ISSUE_STEPS[0] + 2

    def action(self, current_state: Mapping[str, Any]) -> tuple[np.ndarray, dict[str, Any]]:
        if int(current_state["step_index"]) != self.step:
            raise ValueError("R8R7 controller/current task-state index mismatch")
        if self.step < PREFIX_END:
            action, trace = super().action(current_state)
            trace.update(
                {
                    "r3c3t13s24d1r14r8r7_controller_revision": contract.CONTROLLER_REVISION,
                    "r3c3t13s24d1r14r8r7_delegated_prefix": True,
                    "r3c3t13s24d1r14r8r7_event": "none",
                    "r3c3t13s24d1r14r8r7_event_detail": {},
                    "r3c3t13s24d1r14r8r7_pair_or_history_label_used": False,
                    "r3c3t13s24d1r14r8r7_future_measurement_used": False,
                    "r3c3t13s24d1r14r8r7_future_executed_action_used": False,
                }
            )
            return np.asarray(action, dtype=float), trace
        action = r4.zero_action(self.step)
        trace = r4._trace_template(self.step, action)
        event: dict[str, Any] = {}
        event_name = "none"
        if self.r8r7_role == "multipulse" and self.step in contract.ISSUE_STEPS:
            index = contract.ISSUE_STEPS.index(self.step)
            direction = self.r8r7_directions[index]
            self.d1r14r4_direction_index = direction
            self.d1r14r4_sign = self.r8r7_signs[index]
            self.d1r14r4_requested_coordinate = np.asarray(
                self.r8r7_coordinates[index], dtype=float
            )
            action, event = self._issue(
                direction,
                np.asarray(current_state["currents_a_tsc"], dtype=float),
                np.zeros(N_COILS, dtype=float),
            )
            event["schedule_position"] = index
            event_name = "sequential_issue"
        elif self.r8r7_role == "multipulse" and self.step in tuple(
            value + 1 for value in contract.ISSUE_STEPS
        ):
            index = tuple(value + 1 for value in contract.ISSUE_STEPS).index(self.step)
            direction = self.r8r7_directions[index]
            action, event = self._cancel(
                direction,
                np.asarray(current_state["currents_a_tsc"], dtype=float),
                np.zeros(N_COILS, dtype=float),
            )
            event["schedule_position"] = index
            event_name = "sequential_cancel"
        trace.update(
            {
                "action_norm_tsc": action.tolist(),
                "r3c3t13s24d1r14r8r7_controller_revision": contract.CONTROLLER_REVISION,
                "r3c3t13s24d1r14r8r7_delegated_prefix": False,
                "r3c3t13s24d1r14r8r7_event": event_name,
                "r3c3t13s24d1r14r8r7_event_detail": event,
                "r3c3t13s24d1r14r8r7_pair_or_history_label_used": False,
                "r3c3t13s24d1r14r8r7_partition_label_used": False,
                "r3c3t13s24d1r14r8r7_source_result_used": False,
                "r3c3t13s24d1r14r8r7_future_measurement_used": False,
                "r3c3t13s24d1r14r8r7_future_executed_action_used": False,
                "r3c3t13s24d1r14r8r7_hidden_wire_current_used": False,
            }
        )
        return np.asarray(action, dtype=float), trace


class LocalWorker:
    """One fresh authentic TSC process and one R8R7 controller."""

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
        controller_cfg: dict[str, Any],
    ):
        self.plant = r8.d1r11.s21.s16.s9.t11.t1.r1.LocalPlantReplayWorker(
            payload, library, bundle, worker_id, selector
        )
        self.base = self.plant.base_worker
        self.bundle = bundle
        self.lattice_cfg = lattice_cfg
        self.calibration_cfg = calibration_cfg
        self.dynamic_cfg = dynamic_cfg
        self.schedule_cfg = schedule_cfg
        self.controller_cfg = controller_cfg

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
                horizon != r8.d1r11.s21.s13._formal_horizon(float(spec["slew_scale"]))
                or horizon != int(spec["formal_horizon_steps"])
                or horizon != int(self.base.env.max_episode_steps)
            ):
                raise ValueError("R8R7 formal horizon changed")
            self.base.env.reset()
            zero = np.zeros(N_COILS, dtype=np.float32)
            trajectory.append(
                r8.d1r11.s21.s16.s9.t11.t1.r1._state_record_full(self.base.env, 0, zero)
            )
            controller = FixedCanonicalMultipulseController(
                self.base,
                self.bundle,
                spec,
                trajectory[0],
                self.lattice_cfg,
                self.calibration_cfg,
                self.dynamic_cfg,
                self.schedule_cfg,
                self.controller_cfg,
            )
            for step in range(horizon):
                try:
                    action, row = controller.action(trajectory[-1])
                except ValueError as exc:
                    if "mixed-basis issue action failed" in str(exc) or "cancel action failed" in str(exc):
                        result["execution_failure_class"] = "controller_action_safety_gate_failure"
                    raise
                _, _, terminated, truncated, info = self.base.env.step(action)
                next_state = r8.d1r11.s21.s16.s9.t11.t1.r1._state_record_full(
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
                    raise RuntimeError("environment truncated before R8R7 horizon")
            calibration_events = [
                row.get("r3c3t13s16_lattice_event")
                for row in trace[:PREFIX_END]
                if row.get("r3c3t13s16_lattice_event") != "none"
            ]
            currents = np.asarray([row["currents_a_tsc"] for row in trajectory], dtype=float)
            event_steps = set(contract.ISSUE_STEPS) | {value + 1 for value in contract.ISSUE_STEPS}
            role = str(spec["r8r7_role"])
            events = [
                row.get("r3c3t13s24d1r14r8r7_event")
                for row in trace
                if row.get("r3c3t13s24d1r14r8r7_event") != "none"
            ]
            actions = np.asarray([row["action_norm_tsc"] for row in trace], dtype=float)
            zero_steps = [step for step in range(PREFIX_END, horizon) if step not in event_steps]
            zero_exact = bool(
                actions.shape == (horizon, N_COILS)
                and np.array_equal(actions[zero_steps], np.zeros((len(zero_steps), N_COILS)))
                and np.array_equal(
                    currents[np.asarray(zero_steps) + 1] - currents[zero_steps],
                    np.zeros((len(zero_steps), N_COILS)),
                )
            )
            if role == "baseline":
                role_success = bool(events == [] and zero_exact)
            else:
                role_success = bool(
                    events == [value for _ in range(4) for value in ("sequential_issue", "sequential_cancel")]
                    and zero_exact
                    and controller._active_issue is None
                    and all(
                        bool((trace[step].get("r3c3t13s24d1r14r8r7_event_detail") or {}).get("passed"))
                        for step in sorted(event_steps)
                    )
                )
            success = bool(
                len(trajectory) == horizon + 1
                and len(trace) == horizon
                and calibration_events == r4.EXPECTED_CALIBRATION
                and bool(trace[7].get("r3c3t13s21_exact_calibration_net_zero"))
                and all(bool(row.get("r3c3t13s24d1r14r8r7_delegated_prefix")) for row in trace[:PREFIX_END])
                and role_success
                and not any(bool(row.get("abnormal")) for row in trajectory)
                and np.all(np.isfinite(currents))
            )
            result.update(
                {
                    "success": success,
                    "completed": True,
                    "failure_reason": "" if success else "incomplete or invalid R8R7 rollout",
                    "execution_failure_class": "" if success else "controller_or_action_semantics_error",
                    "hidden_history_control_summary": {
                        "fresh_controller_actor": True,
                        "fresh_tsc_process": True,
                        "full_tsc_hidden_state_loaded_from_sprsina": True,
                        "role": role,
                        "future_r17_controller_executed": False,
                        "formal_tracking_diagnostic_only": True,
                        "stage_trajectory_allowed_in_expert_dataset": False,
                        "future_action_replay_used": False,
                        "future_measurement_used": False,
                        "pair_or_history_label_used": False,
                        "source_result_used": False,
                    },
                    "wall_time_s": time.time() - started,
                }
            )
            failed = not success
            return r8.d1r11.s21.s16.s9.t11.t1._json_safe(result)
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
            return r8.d1r11.s21.s16.s9.t11.t1._json_safe(result)
        finally:
            runner = getattr(self.base.env, "runner", None)
            if runner is not None:
                runner.cleanup_episode_workspace(failed=failed, reason="stage4_2r3c3t13s24d1r14r8r7")


_RAY_ACTOR = None


def _ray_actor_class():
    global _RAY_ACTOR
    if _RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class Stage42R8R7Actor:
            def __init__(self, *args: Any):
                self.worker = LocalWorker(*args)

            def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
                return self.worker.evaluate(spec)

            def close(self) -> bool:
                self.worker.close()
                return True

        _RAY_ACTOR = Stage42R8R7Actor
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
    controller_cfg = copy.deepcopy(ctx.cfg["controller_contract"])
    controller_cfg.update(
        {
            "requested_coordinate_matrix_columns": copy.deepcopy(
                ctx.cfg["schedule_contract"]["canonical_matrix_columns"]
            ),
            "requested_matrix_float64_le_c_sha256": str(
                ctx.cfg["schedule_contract"]["canonical_matrix_digest"]
            ),
        }
    )

    def worker_args(spec: Mapping[str, Any], index: int) -> tuple[Any, ...]:
        return (
            payloads[str(spec["experiment_id"])],
            library,
            bundle,
            f"stage42r8r7_{phase}_{index:02d}",
            selector,
            lattice,
            calibration,
            dynamic,
            schedule,
            controller_cfg,
        )

    if backend == "serial":
        for index, spec in enumerate(pending):
            worker = LocalWorker(*worker_args(spec, index))
            try:
                result = worker.evaluate(spec)
            finally:
                worker.close()
            r8._write_gz(raw_dir / f"{spec['experiment_id']}.json.gz", result)
            print(f"[R8R7 {phase}] {index + 1}/{len(pending)}", flush=True)
    elif backend == "ray" and pending:
        import ray

        plan = r8.d1r11.s21.s16.ensure_ray_worker_plan(
            ray,
            requested_workers=int(ctx.cfg["parallel"]["n_workers"]),
            pending_tasks=len(pending),
            ray_tmpdir=os.environ.get("RAY_TMPDIR") or ctx.cfg["storage"]["ray_tmpdir"],
            log_prefix=f"[R8R7 {phase}]",
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
                        print(f"[R8R7 {phase}] waiting {completed}/{len(pending)}", flush=True)
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
                    r8._write_gz(raw_dir / f"{spec['experiment_id']}.json.gz", result)
                    completed += 1
                    print(f"[R8R7 {phase}] {completed}/{len(pending)}", flush=True)
            finally:
                close_refs = [actor.close.remote() for actor in actors]
                if close_refs:
                    ray.get(close_refs, timeout=float(ctx.cfg["storage"]["actor_close_timeout_s"]))
                for actor in actors:
                    ray.kill(actor, no_restart=True)
    elif backend not in {"serial", "ray"}:
        raise ValueError(f"unsupported R8R7 backend: {backend}")
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


R8R7_FORBIDDEN_TRACE_KEYS = tuple(
    dict.fromkeys(
        r8.R8_FORBIDDEN_TRACE_KEYS
        + (
            "r3c3t13s24d1r14r8r7_pair_or_history_label_used",
            "r3c3t13s24d1r14r8r7_partition_label_used",
            "r3c3t13s24d1r14r8r7_source_result_used",
            "r3c3t13s24d1r14r8r7_future_measurement_used",
            "r3c3t13s24d1r14r8r7_future_executed_action_used",
            "r3c3t13s24d1r14r8r7_hidden_wire_current_used",
        )
    )
)


def _formal_diagnostics(ctx: Context, specs: Sequence[Mapping[str, Any]], phase: str) -> dict[str, Any]:
    evaluators, _ = r8.d1r11._formal_callback(ctx.r8_ctx.d1r11_ctx, specs)
    passed = 0
    for spec in specs:
        result = r8._read_gz(ctx.paths.phase_raw(phase) / f"{spec['experiment_id']}.json.gz")
        values = np.asarray(
            [[row["R"], row["Z"], row["Ip"]] for row in result.get("trajectory") or []],
            dtype=float,
        )
        if len(values) == int(spec["horizon_steps"]) + 1:
            passed += bool(evaluators[str(spec["experiment_id"])].evaluate(values)["formal_contract_pass"])
    return {"evaluated": len(specs), "formal_contract_pass_count_diagnostic_only": passed}


def audit_raw_phase(ctx: Context, phase: str) -> dict[str, Any]:
    specs = _phase_specs(ctx, phase)
    raw_dir = ctx.paths.phase_raw(phase)
    sources = r8._source_baseline_results(ctx.r8_ctx)
    rows = []
    event_steps = set(contract.ISSUE_STEPS) | {value + 1 for value in contract.ISSUE_STEPS}
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
            len(trajectory) >= PREFIX_END + 1
            and all(
                r8.r4._semantic_state(current) == r8.r4._semantic_state(reference)
                for current, reference in zip(
                    trajectory[: PREFIX_END + 1], source["trajectory"][: PREFIX_END + 1]
                )
            )
        )
        prefix_trace = bool(
            len(trace) >= PREFIX_END
            and all(
                r8.r4._source_trace_projection(reference, current)
                for current, reference in zip(
                    trace[:PREFIX_END], source["controller_trace"][:PREFIX_END]
                )
            )
        )
        calibration = r8.r4._calibration_exact(trace)
        actions = np.asarray([row.get("action_norm_tsc", []) for row in trace], dtype=float)
        currents = np.asarray([row.get("currents_a_tsc", []) for row in trajectory], dtype=float)
        wires = [np.asarray(row.get("wire_currents_a", []), dtype=float) for row in trajectory]
        finite = bool(
            full
            and actions.shape == (horizon, N_COILS)
            and currents.shape == (horizon + 1, N_COILS)
            and np.all(np.isfinite(actions))
            and np.all(np.isfinite(currents))
            and all(value.size and np.all(np.isfinite(value)) for value in wires)
            and all(math.isfinite(float(row[key])) for row in trajectory for key in ("R", "Z", "Ip"))
            and not any(bool(row.get("abnormal")) for row in trajectory)
        )
        forbidden = sum(any(bool(row.get(key)) for key in R8R7_FORBIDDEN_TRACE_KEYS) for row in trace)
        payload = _read(ctx.paths.variants / f"payload_{experiment_id}.json")
        minimum, maximum = r8.d1r11.s21.s13._current_limits_tsc(payload)
        center, half = 0.5 * (minimum + maximum), 0.5 * (maximum - minimum)
        utilization: float | None = (
            float(np.max(np.abs((currents - center) / half)))
            if currents.shape == (horizon + 1, N_COILS)
            else None
        )
        action_abs: float | None = (
            float(np.max(np.abs(actions)))
            if actions.shape == (horizon, N_COILS)
            else None
        )
        zero_steps = [step for step in range(PREFIX_END, horizon) if step not in event_steps]
        zero_exact = bool(
            full
            and np.array_equal(actions[zero_steps], np.zeros((len(zero_steps), N_COILS)))
            and np.array_equal(
                currents[np.asarray(zero_steps) + 1] - currents[zero_steps],
                np.zeros((len(zero_steps), N_COILS)),
            )
        )
        issue_exact = cancel_exact = True
        issue_count = cancel_count = 0
        max_increment = max_cancel = 0.0
        if phase == "multipulse" and full:
            matrix = np.asarray(ctx.cfg["schedule_contract"]["canonical_matrix_columns"], dtype=float)
            issue_exact = cancel_exact = True
            for index, issue_step in enumerate(contract.ISSUE_STEPS):
                cancel_step = issue_step + 1
                issue = trace[issue_step].get("r3c3t13s24d1r14r8r7_event_detail") or {}
                cancel = trace[cancel_step].get("r3c3t13s24d1r14r8r7_event_detail") or {}
                direction = int(spec["r8r7_direction_indices"][index])
                sign = int(spec["r8r7_signs"][index])
                expected_coordinate = (matrix[:, direction] * sign).tolist()
                current_issue = bool(
                    trace[issue_step].get("r3c3t13s24d1r14r8r7_event") == "sequential_issue"
                    and issue.get("event") == "sequential_issue"
                    and int(issue.get("task_step", -1)) == issue_step
                    and int(issue.get("slot", -1)) == direction
                    and list(map(float, issue.get("requested_coordinate", []))) == expected_coordinate
                    and issue.get("passed") is True
                    and all(bool(value) for value in (issue.get("criteria") or {}).values())
                )
                current_cancel = bool(
                    trace[cancel_step].get("r3c3t13s24d1r14r8r7_event") == "sequential_cancel"
                    and cancel.get("event") == "sequential_cancel"
                    and int(cancel.get("task_step", -1)) == cancel_step
                    and int(cancel.get("slot", -1)) == direction
                    and cancel.get("stored_center_card15_fields") == issue.get("center_card15_fields")
                    and cancel.get("passed") is True
                    and all(bool(value) for value in (cancel.get("criteria") or {}).values())
                )
                issue_exact = issue_exact and current_issue
                cancel_exact = cancel_exact and current_cancel
                issue_count += int(current_issue)
                cancel_count += int(current_cancel)
                issue_increment = issue.get("incremental_normalized_action_linf")
                cancel_increment = cancel.get("incremental_normalized_action_linf")
                if issue_increment is None or not math.isfinite(float(issue_increment)):
                    max_increment = None
                elif max_increment is not None:
                    max_increment = max(max_increment, float(issue_increment))
                if cancel_increment is None or not math.isfinite(float(cancel_increment)):
                    max_cancel = None
                elif max_cancel is not None:
                    max_cancel = max(max_cancel, float(cancel_increment))
        elif phase == "baseline":
            issue_exact = cancel_exact = bool(
                all(row.get("r3c3t13s24d1r14r8r7_event") == "none" for row in trace[PREFIX_END:])
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
            and zero_exact
            and issue_exact
            and cancel_exact
            and source_snapshot
            and forbidden == 0
            and action_abs is not None
            and action_abs <= float(ctx.cfg["controller_contract"]["maximum_total_normalized_action_abs"]) + 1e-12
            and max_increment is not None
            and max_increment <= float(ctx.cfg["controller_contract"]["maximum_incremental_normalized_action_linf"]) + 1e-12
            and max_cancel is not None
            and max_cancel <= float(ctx.cfg["controller_contract"]["maximum_online_cancel_incremental_linf"]) + 1e-12
            and utilization is not None
            and utilization <= float(ctx.cfg["controller_contract"]["maximum_current_utilization"]) + 1e-12
        )
        rows.append(
            {
                "experiment_id": experiment_id,
                "pair_id": spec["pair_id"],
                "history_member": spec["history_member"],
                "schedule_index": int(spec["r8r7_schedule_index"]),
                "runtime_success": bool(result.get("success")),
                "execution_failure_class": str(result.get("execution_failure_class") or ""),
                "full_horizon": full,
                "source_prefix_state_exact": prefix_state,
                "source_prefix_trace_exact": prefix_trace,
                "calibration_exact": calibration,
                "zero_non_event_action_and_current_exact": zero_exact,
                "issue_exact_count": issue_count,
                "cancel_exact_count": cancel_count,
                "source_restart_snapshot_authenticated": source_snapshot,
                "finite": finite,
                "forbidden_trace_count": forbidden,
                "maximum_incremental_issue_action": max_increment,
                "maximum_incremental_cancel_action": max_cancel,
                "maximum_total_normalized_action_abs": action_abs,
                "maximum_current_utilization": utilization,
                "failure_reason": str(result.get("failure_reason") or ""),
                "passed": passed,
            }
        )
    inventory = r8._inventory(raw_dir)
    expected = {"baseline": 16, "multipulse": 32}[phase]
    formal = (
        _formal_diagnostics(ctx, specs, phase)
        if len(rows) == expected and all(bool(row.get("runtime_success")) for row in rows)
        else {"evaluated": 0, "formal_contract_pass_count_diagnostic_only": 0}
    )
    def complete_maximum(name: str) -> float | None:
        values = [row.get(name) for row in rows]
        if not values or any(value is None or not math.isfinite(float(value)) for value in values):
            return None
        return max(float(value) for value in values)

    report = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "phase": phase,
        "expected_raw_count": expected,
        "raw_inventory": inventory,
        "runtime_success_count": sum(bool(row.get("runtime_success")) for row in rows),
        "full_horizon_count": sum(bool(row.get("full_horizon")) for row in rows),
        "source_prefix_state_exact_count": sum(bool(row.get("source_prefix_state_exact")) for row in rows),
        "source_prefix_trace_exact_count": sum(bool(row.get("source_prefix_trace_exact")) for row in rows),
        "calibration_exact_count": sum(bool(row.get("calibration_exact")) for row in rows),
        "zero_non_event_action_and_current_exact_count": sum(bool(row.get("zero_non_event_action_and_current_exact")) for row in rows),
        "issue_exact_count": sum(int(row.get("issue_exact_count", 0)) for row in rows),
        "cancel_exact_count": sum(int(row.get("cancel_exact_count", 0)) for row in rows),
        "source_restart_snapshot_authenticated_count": sum(bool(row.get("source_restart_snapshot_authenticated")) for row in rows),
        "finite_count": sum(bool(row.get("finite")) for row in rows),
        "forbidden_trace_count": sum(int(row.get("forbidden_trace_count", 0)) for row in rows),
        "maximum_incremental_issue_action": complete_maximum("maximum_incremental_issue_action"),
        "maximum_incremental_cancel_action": complete_maximum("maximum_incremental_cancel_action"),
        "maximum_total_normalized_action_abs": complete_maximum("maximum_total_normalized_action_abs"),
        "maximum_current_utilization": complete_maximum("maximum_current_utilization"),
        "passed_count": sum(bool(row.get("passed")) for row in rows),
        "formal_tracking_diagnostic_only": formal,
        "rows": rows,
    }
    report["passed"] = bool(
        inventory["count"] == expected
        and len(rows) == expected
        and report["passed_count"] == expected
        and (phase == "baseline" or (report["issue_exact_count"] == 128 and report["cancel_exact_count"] == 128))
    )
    report["route"] = ctx.cfg["routes"][
        "pass" if report["passed"] else f"{phase}_execution_fail"
    ]
    _write(ctx.paths.analysis / f"{phase}_raw_primary.json", report)
    return report


def run_phase(ctx: Context, phase: str, *, backend: str, resume: bool) -> dict[str, Any]:
    expected_status = {"baseline": "baseline_authorized", "multipulse": "multipulse_authorized"}[phase]
    _require(ctx, expected_status)
    if phase == "baseline" and any(ctx.paths.phase_raw("multipulse").glob("*.json.gz")):
        raise ValueError("R8R7 multipulse raw opened before baseline qualification")
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
            multipulse_outcomes_opened=phase == "multipulse",
            stop_reason=f"{phase}_runtime_restart_action_current_or_raw_gate_failed",
            verdict={"route": route, "passed": False},
        )
    else:
        _set_state(
            ctx,
            phase_status=f"{phase}_raw_primary_passed",
            real_tsc_executed=True,
            new_raw_count=total,
            multipulse_outcomes_opened=phase == "multipulse",
            **{f"{phase}_raw_inventory_digest": primary["raw_inventory"]["digest"]},
        )
    return {
        "execution": execution,
        "primary_raw_audit": {key: value for key, value in primary.items() if key != "rows"},
    }


def _response_model_from_artifact(value: Mapping[str, Any]) -> dict[str, Any]:
    model = value["model"]
    candidate = response_model.Candidate(**model["candidate"])
    return {
        "candidate": candidate,
        "preprocessor": {
            key: np.asarray(item, dtype=float)
            for key, item in model["preprocessor"].items()
        },
        "heads": {
            key: {
                "amplitude_mean": float(head["amplitude_mean"]),
                "amplitude_scale": float(head["amplitude_scale"]),
                "lags": [
                    {
                        "lag": int(row["lag"]),
                        "x": np.asarray(row["x"], dtype=float),
                        "bandwidth": float(row["bandwidth"]),
                        "y_mean": np.asarray(row["y_mean"], dtype=float),
                        "alpha": np.asarray(row["alpha"], dtype=float),
                    }
                    for row in head["lags"]
                ],
            }
            for key, head in model["heads"].items()
        },
    }


def _response_descriptor(
    visible: np.ndarray, spec: Mapping[str, Any], origin: int, cfg: Mapping[str, Any]
) -> np.ndarray:
    offsets = tuple(map(int, cfg["bank_contract"]["history_offsets"]))
    history = visible[[max(0, origin - offset) for offset in offsets]].reshape(-1)
    availability = np.asarray([float(offset <= origin) for offset in offsets])
    target = r8r3_primary._target(spec) / np.asarray(
        cfg["bank_contract"]["target_scales"], dtype=float
    )
    descriptor = np.concatenate((history, availability, target, [(origin - 10.0) / 12.0]))
    if descriptor.shape != (int(cfg["bank_contract"]["response_descriptor_dimension"]),):
        raise ValueError("R8R7 response descriptor changed")
    return descriptor


def _prediction_rows(ctx: Context, phase: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    static_artifact = _read(_r8r6_paths(ctx).model / "observer_model.json")
    static_model = r8r4._model_from_artifact(static_artifact)
    static_tube = np.asarray(
        _read(_r8r6_paths(ctx).model / "observer_tube.json")["tube_physical"], dtype=float
    )
    response_artifact = _read(ctx.paths.model / "response_model.json")
    action_model = _response_model_from_artifact(response_artifact)
    response_tube = np.asarray(_read(ctx.paths.model / "response_tube.json")["tube_physical"], dtype=float)
    combined_tube = np.asarray(
        _read(ctx.paths.model / "combined_tube.json")["combined_tube_physical"], dtype=float
    )
    horizon = int(ctx.cfg["rollout_contract"]["forecast_horizon_steps"])
    scales = np.asarray(ctx.cfg["bank_contract"]["visible_scales"], dtype=float)
    point_caps = np.asarray(ctx.cfg["gates"]["component_caps_physical"], dtype=float)
    exclusion_caps = np.asarray(ctx.cfg["gates"]["finite_exclusion_caps_physical"], dtype=float)
    if (
        static_tube.shape != (12, 5)
        or response_tube.shape != (horizon, 5)
        or combined_tube.shape != (horizon, 5)
    ):
        raise ValueError("R8R7 prediction tube shape changed")
    rows = []
    raw_hashes = {}
    for spec in _phase_specs(ctx, phase):
        path = ctx.paths.phase_raw(phase) / f"{spec['experiment_id']}.json.gz"
        if not _result_complete(path, spec):
            raise ValueError(f"R8R7 {phase} raw incomplete before prediction")
        result = r8._read_gz(path)
        visible = r7_source._visible(result["trajectory"], scales)
        actions = r8r3_primary._actions(result)
        currents = r8r3_primary._currents(result)
        for index, origin in enumerate(contract.ISSUE_STEPS):
            feature = observer.causal_feature(
                visible[: origin + 1],
                actions[:origin],
                currents[: origin + 1],
                r8r3_primary._target(spec),
                origin,
                ctx.r8r6_cfg,
            )
            static_item = {
                "row_id": f"{phase}|{spec['experiment_id']}|origin{origin:02d}",
                "pair_id": str(spec["pair_id"]),
                "history_member": str(spec["history_member"]),
                "origin_task_step": origin,
                "prescribed_issue": True,
                "feature": feature,
                "origin_visible": visible[origin],
                "target_delta": observer.target_delta(visible, origin, ctx.r8r6_cfg),
                "future_visible": visible[origin + 1 : origin + 13],
            }
            static_prediction = observer.predict_model(static_model, [static_item], ctx.r8r6_cfg)[0][
                :horizon
            ]
            direction = sign = None
            response_prediction = np.zeros((horizon, 5), dtype=float)
            tube = static_tube[:horizon]
            if phase == "multipulse":
                direction = int(spec["r8r7_direction_indices"][index])
                sign = int(spec["r8r7_signs"][index])
                response_item = {
                    "response_id": static_item["row_id"],
                    "context_id": "evaluator_label_not_used_by_model",
                    "pair_id": "evaluator_label_not_used_by_model",
                    "history_member": "evaluator_label_not_used_by_model",
                    "issue_task_step": origin,
                    "sign": sign,
                    "direction_index": direction,
                    "action_scale": 1.0,
                    "geometry_roles": [],
                    "descriptor": _response_descriptor(visible, spec, origin, ctx.cfg),
                    "response": np.zeros((horizon, 5), dtype=float),
                }
                response_prediction = response_model.predict_item(
                    action_model,
                    response_item,
                    r8r1.model_config(ctx.r8r1_cfg, ctx.r8_cfg),
                )
                tube = combined_tube
            prediction = static_prediction + response_prediction
            actual = visible[origin + 1 : origin + 1 + horizon]
            residual_physical = (prediction - actual) * scales[None, :]
            absolute = np.abs(residual_physical)
            point_pass = bool(
                np.all(np.isfinite(prediction))
                and np.all(absolute <= point_caps[None, :] + 1e-15)
            )
            contained = bool(np.all(absolute <= tube + 1e-15))
            exclusion = absolute > exclusion_caps[None, :] + 1e-15
            rows.append(
                {
                    "row_id": static_item["row_id"],
                    "experiment_id": str(spec["experiment_id"]),
                    "context_id": f"{spec['pair_id']}|{spec['history_member']}",
                    "pair_id": str(spec["pair_id"]),
                    "history_member": str(spec["history_member"]),
                    "schedule_index": int(spec["r8r7_schedule_index"]),
                    "origin_task_step": origin,
                    "direction_index": direction,
                    "sign": sign,
                    "static_prediction": static_prediction.tolist(),
                    "response_prediction": response_prediction.tolist(),
                    "combined_prediction": prediction.tolist(),
                    "actual_visible": actual.tolist(),
                    "absolute_residual_physical": absolute.tolist(),
                    "maximum_absolute_scaled_point_error": float(
                        np.max(np.abs(prediction - actual))
                    ),
                    "finite_exclusion_violation_count": int(np.sum(exclusion)),
                    "point_passed": point_pass,
                    "tube_contained": contained,
                }
            )
        raw_hashes[str(spec["experiment_id"])] = _sha(path)
    expected = {"baseline": 64, "multipulse": 128}[phase]
    if len(rows) != expected:
        raise ValueError("R8R7 prediction row coverage changed")
    return sorted(rows, key=lambda row: row["row_id"]), {
        "phase": phase,
        "row_count": len(rows),
        "context_count": len({str(row["context_id"]) for row in rows}),
        "raw_sha256": raw_hashes,
        "forbidden_predictor_input_count": 0,
        "future_input_count": 0,
        "adaptation_enabled": False,
        "allowed_in_expert_dataset": False,
    }


def _evaluate_prediction_rows(
    rows: Sequence[Mapping[str, Any]], phase: str, cfg: Mapping[str, Any]
) -> dict[str, Any]:
    point_count = sum(bool(row["point_passed"]) for row in rows)
    tube_count = sum(bool(row["tube_contained"]) for row in rows)
    exclusion = sum(int(row["finite_exclusion_violation_count"]) for row in rows)
    contexts: dict[str, Any] = {}
    contexts_passed = True
    for name in sorted({str(row["context_id"]) for row in rows}):
        current = [row for row in rows if str(row["context_id"]) == name]
        point = sum(bool(row["point_passed"]) for row in current)
        tube = sum(bool(row["tube_contained"]) for row in current)
        point_need = int(
            cfg["gates"][
                "baseline_per_context_point_pass_count"
                if phase == "baseline"
                else "multipulse_per_context_point_pass_count"
            ]
        )
        tube_need = int(
            cfg["gates"][
                "baseline_per_context_tube_pass_count"
                if phase == "baseline"
                else "multipulse_per_context_tube_pass_count"
            ]
        )
        passed = point >= point_need and tube >= tube_need
        contexts_passed = contexts_passed and passed
        contexts[name] = {
            "total": len(current),
            "point_pass_count": point,
            "point_required": point_need,
            "tube_pass_count": tube,
            "tube_required": tube_need,
            "passed": passed,
        }
    direction_counts: dict[str, Any] = {}
    sign_counts: dict[str, Any] = {}
    strata_passed = True
    if phase == "multipulse":
        for direction in range(4):
            current = [row for row in rows if int(row["direction_index"]) == direction]
            point = sum(bool(row["point_passed"]) for row in current)
            tube = sum(bool(row["tube_contained"]) for row in current)
            passed = bool(
                point >= int(cfg["gates"]["multipulse_per_direction_point_pass_count"])
                and tube >= int(cfg["gates"]["multipulse_per_direction_tube_pass_count"])
            )
            strata_passed = strata_passed and passed
            direction_counts[str(direction)] = {
                "total": len(current),
                "point_pass_count": point,
                "tube_pass_count": tube,
                "passed": passed,
            }
        for sign in (-1, 1):
            current = [row for row in rows if int(row["sign"]) == sign]
            point = sum(bool(row["point_passed"]) for row in current)
            tube = sum(bool(row["tube_contained"]) for row in current)
            passed = bool(
                point >= int(cfg["gates"]["multipulse_per_sign_point_pass_count"])
                and tube >= int(cfg["gates"]["multipulse_per_sign_tube_pass_count"])
            )
            strata_passed = strata_passed and passed
            sign_counts[str(sign)] = {
                "total": len(current),
                "point_pass_count": point,
                "tube_pass_count": tube,
                "passed": passed,
            }
    point_need = int(
        cfg["gates"][
            "baseline_required_point_pass_count"
            if phase == "baseline"
            else "multipulse_required_point_pass_count"
        ]
    )
    tube_need = int(
        cfg["gates"][
            "baseline_required_tube_pass_count"
            if phase == "baseline"
            else "multipulse_required_tube_pass_count"
        ]
    )
    maximum = np.max(
        np.asarray([row["absolute_residual_physical"] for row in rows], dtype=float),
        axis=(0, 1),
    )
    result = {
        "phase": phase,
        "row_count": len(rows),
        "point_pass_count": point_count,
        "point_required": point_need,
        "tube_containment_count": tube_count,
        "tube_required": tube_need,
        "finite_exclusion_violation_count": exclusion,
        "maximum_absolute_physical_error": maximum.tolist(),
        "maximum_absolute_scaled_point_error": max(
            float(row["maximum_absolute_scaled_point_error"]) for row in rows
        ),
        "context_counts": contexts,
        "direction_counts": direction_counts,
        "sign_counts": sign_counts,
    }
    result["passed"] = bool(
        point_count >= point_need
        and tube_count >= tube_need
        and exclusion == 0
        and contexts_passed
        and strata_passed
    )
    return result


def evaluate_baseline(ctx: Context) -> dict[str, Any]:
    state = _require(ctx, "baseline_raw_primary_passed")
    raw_independent = _independent(ctx, "baseline_raw")
    primary_raw = _read(ctx.paths.analysis / "baseline_raw_primary.json")
    if (
        raw_independent.get("primary_sha256") != _sha(ctx.paths.analysis / "baseline_raw_primary.json")
        or raw_independent.get("raw_inventory_digest") != primary_raw["raw_inventory"]["digest"]
        or primary_raw.get("passed") is not True
    ):
        raise ValueError("R8R7 baseline raw independent agreement failed")
    rows, signature = _prediction_rows(ctx, "baseline")
    evaluation = _evaluate_prediction_rows(rows, "baseline", ctx.cfg)
    route = ctx.cfg["routes"]["pass" if evaluation["passed"] else "baseline_model_fail"]
    detailed = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "phase": "fresh_baseline_static_observer",
        "source_signature": signature,
        "prediction_rows": rows,
        "evaluation": evaluation,
        "static_observer_model_sha256": ctx.cfg["source_r8r6_contract"]["observer_model_sha256"],
        "static_observer_tube_sha256": ctx.cfg["source_r8r6_contract"]["observer_tube_sha256"],
        "route": route,
        "scientific_gate_passed": bool(evaluation["passed"]),
        "all_stage_trajectories_allowed_in_expert_dataset": False,
        "passed": True,
    }
    detailed_path = ctx.paths.analysis / "baseline_model_primary_detailed.json"
    _write(detailed_path, detailed)
    summary = {key: value for key, value in detailed.items() if key != "prediction_rows"}
    summary["primary_detailed_sha256"] = _sha(detailed_path)
    _write(ctx.paths.analysis / "baseline_model_primary_summary.json", summary)
    if not evaluation["passed"]:
        _set_state(
            ctx,
            phase_status="baseline_model_failed",
            finished=True,
            stop_reason="fresh_baseline_static_observer_gate_failed",
            verdict={"route": route, "passed": False},
        )
    else:
        _set_state(
            ctx,
            phase_status="baseline_model_primary_passed",
            baseline_model_primary_summary_sha256=_sha(ctx.paths.analysis / "baseline_model_primary_summary.json"),
        )
    return summary


def authorize_multipulse(ctx: Context) -> dict[str, Any]:
    state = _require(ctx, "baseline_model_primary_passed")
    independent = _independent(ctx, "baseline_model")
    summary_path = ctx.paths.analysis / "baseline_model_primary_summary.json"
    if (
        independent.get("primary_numerical_agreement") is not True
        or independent.get("primary_outcome_agreement") is not True
        or independent.get("primary_sha256") != _sha(summary_path)
        or state.get("baseline_model_primary_summary_sha256") != _sha(summary_path)
        or independent.get("scientific_gate_passed") is not True
    ):
        raise ValueError("R8R7 baseline model independent agreement failed")
    _set_state(
        ctx,
        phase_status="multipulse_authorized",
        baseline_model_independent_sha256=_sha(ctx.paths.analysis / "baseline_model_independent.json"),
    )
    return {"stage": contract.STAGE, "phase": "multipulse_authorized", "passed": True}


def finalize_multipulse(ctx: Context) -> dict[str, Any]:
    _require(ctx, "multipulse_raw_primary_passed")
    raw_independent = _independent(ctx, "multipulse_raw")
    primary_raw_path = ctx.paths.analysis / "multipulse_raw_primary.json"
    primary_raw = _read(primary_raw_path)
    if (
        raw_independent.get("primary_sha256") != _sha(primary_raw_path)
        or raw_independent.get("raw_inventory_digest") != primary_raw["raw_inventory"]["digest"]
        or primary_raw.get("passed") is not True
    ):
        raise ValueError("R8R7 multipulse raw independent agreement failed")
    rows, signature = _prediction_rows(ctx, "multipulse")
    evaluation = _evaluate_prediction_rows(rows, "multipulse", ctx.cfg)
    combined = _read(ctx.paths.model / "combined_tube.json")
    scientific = bool(evaluation["passed"] and combined.get("cap_passed") is True)
    route = ctx.cfg["routes"]["pass" if scientific else "multipulse_model_fail"]
    detailed = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "phase": "fresh_multipulse_static_observer_interaction",
        "source_signature": signature,
        "prediction_rows": rows,
        "evaluation": evaluation,
        "response_model_sha256": _sha(ctx.paths.model / "response_model.json"),
        "response_tube_sha256": _sha(ctx.paths.model / "response_tube.json"),
        "combined_tube_sha256": _sha(ctx.paths.model / "combined_tube.json"),
        "combined_tube_cap_passed": bool(combined["cap_passed"]),
        "adaptation_enabled": False,
        "route": route,
        "scientific_gate_passed": scientific,
        "formal_tracking_diagnostic_only": primary_raw["formal_tracking_diagnostic_only"],
        "mpc_validated": False,
        "gate_a_qualified": False,
        "all_stage_trajectories_allowed_in_expert_dataset": False,
        "passed": True,
    }
    detailed_path = ctx.paths.analysis / "multipulse_model_primary_detailed.json"
    _write(detailed_path, detailed)
    summary = {key: value for key, value in detailed.items() if key != "prediction_rows"}
    summary["primary_detailed_sha256"] = _sha(detailed_path)
    _write(ctx.paths.analysis / "multipulse_model_primary_summary.json", summary)
    _set_state(
        ctx,
        phase_status="multipulse_model_primary_ready",
        multipulse_model_primary_summary_sha256=_sha(ctx.paths.analysis / "multipulse_model_primary_summary.json"),
        proposed_route=route,
    )
    return summary


def postprocess(ctx: Context) -> dict[str, Any]:
    state = _require(ctx, "multipulse_model_primary_ready")
    independent = _independent(ctx, "multipulse_model")
    summary_path = ctx.paths.analysis / "multipulse_model_primary_summary.json"
    summary = _read(summary_path)
    if (
        independent.get("primary_numerical_agreement") is not True
        or independent.get("primary_outcome_agreement") is not True
        or independent.get("artifact_hash_agreement") is not True
        or independent.get("primary_sha256") != _sha(summary_path)
        or independent.get("route") != summary["route"]
        or state.get("proposed_route") != summary["route"]
    ):
        raise ValueError("R8R7 final independent agreement failed")
    baseline_raw = _read(ctx.paths.analysis / "baseline_raw_primary.json")
    multipulse_raw = _read(ctx.paths.analysis / "multipulse_raw_primary.json")
    baseline_model = _read(ctx.paths.analysis / "baseline_model_primary_summary.json")
    final = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "campaign_identity": contract.IDENTITY,
        "baseline_raw_inventory": baseline_raw["raw_inventory"],
        "multipulse_raw_inventory": multipulse_raw["raw_inventory"],
        "baseline_execution_pass_count": baseline_raw["passed_count"],
        "multipulse_execution_pass_count": multipulse_raw["passed_count"],
        "safe_exact_issue_count": multipulse_raw["issue_exact_count"],
        "safe_exact_cancel_count": multipulse_raw["cancel_exact_count"],
        "baseline_evaluation": baseline_model["evaluation"],
        "multipulse_evaluation": summary["evaluation"],
        "response_model_sha256": summary["response_model_sha256"],
        "response_tube_sha256": summary["response_tube_sha256"],
        "combined_tube_sha256": summary["combined_tube_sha256"],
        "primary_summary_sha256": _sha(summary_path),
        "independent_sha256": _sha(ctx.paths.analysis / "multipulse_model_independent.json"),
        "primary_numerical_agreement": True,
        "primary_outcome_agreement": True,
        "artifact_hash_agreement": True,
        "route": summary["route"],
        "scientific_gate_passed": bool(summary["scientific_gate_passed"]),
        "formal_tracking_diagnostic_only": multipulse_raw["formal_tracking_diagnostic_only"],
        "new_raw_count": baseline_raw["raw_inventory"]["count"]
        + multipulse_raw["raw_inventory"]["count"],
        "real_tsc_executed": True,
        "mpc_validated": False,
        "gate_a_qualified": False,
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
        multipulse_model_independent_sha256=_sha(ctx.paths.analysis / "multipulse_model_independent.json"),
        stop_reason="" if final["scientific_gate_passed"] else "fresh_multipulse_prediction_gate_failed",
        verdict={"route": final["route"], "passed": bool(final["scientific_gate_passed"])},
    )
    return final


def execute(ctx: Context, *, command: str, backend: str, resume: bool) -> dict[str, Any]:
    if command == "offline":
        return prepare_offline(ctx)
    if command == "authorize-baseline":
        return authorize_baseline(ctx)
    if command in PHASES:
        return run_phase(ctx, command, backend=backend, resume=resume)
    if command == "evaluate-baseline":
        return evaluate_baseline(ctx)
    if command == "authorize-multipulse":
        return authorize_multipulse(ctx)
    if command == "finalize":
        return finalize_multipulse(ctx)
    if command == "postprocess":
        return postprocess(ctx)
    raise ValueError(f"unsupported R8R7 command: {command}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
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
        choices=(
            "offline",
            "authorize-baseline",
            "baseline",
            "evaluate-baseline",
            "authorize-multipulse",
            "multipulse",
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
    args = _parser().parse_args()
    if args.self_test:
        print(json.dumps(contract.self_test(args.config), indent=2, sort_keys=True, allow_nan=False))
        return
    ctx = load_context(args)
    result = execute(ctx, command=args.command, backend=args.backend, resume=args.resume)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
