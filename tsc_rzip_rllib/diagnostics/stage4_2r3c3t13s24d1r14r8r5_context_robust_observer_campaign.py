"""Execute and audit the frozen R8R5 context-robust observer holdout."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.control import causal_history_no_action_observer as observer
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification as r8,
    stage4_2r3c3t13s24d1r14r8r4_fresh_causal_observer_campaign as source,
    stage4_2r3c3t13s24d1r14r8r5_context_robust_observer_holdout as contract,
)


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
        if phase != "holdout":
            raise ValueError(f"invalid R8R5 raw phase: {phase}")
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
    source_ctx: source.Context
    r8r4_run: Path


def _source_args(args: argparse.Namespace, config_path: Path) -> argparse.Namespace:
    values = vars(args).copy()
    values["config"] = config_path
    values["run_dir"] = args.r8r4_run
    return argparse.Namespace(**values)


def load_context(args: argparse.Namespace) -> Context:
    config_path = args.config.expanduser().resolve()
    cfg = _read(config_path)
    contract.validate_config(cfg, project_root=_root())
    source_config = (_root() / str(cfg["source_r8r4_config"])).resolve()
    source_ctx = source.load_context(_source_args(args, source_config))
    return Context(
        cfg=cfg,
        config_path=config_path,
        paths=_paths(args.run_dir),
        source_ctx=source_ctx,
        r8r4_run=args.r8r4_run.expanduser().resolve(),
    )


def _package_fingerprint() -> dict[str, Any]:
    names = (
        "configs/stage4_2r3c3t13s24d1r14r8r5_context_robust_observer_holdout_370ms.json",
        "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r5_independent_forensics.py",
        "docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R5_CONTEXT_ROBUST_OBSERVER_HOLDOUT_DESIGN.md",
        "run_stage4_2r3c3t13s24d1r14r8r5_common.sh",
        "run_stage4_2r3c3t13s24d1r14r8r5_native.sh",
        "run_stage4_2r3c3t13s24d1r14r8r5_nohup.sh",
        "run_stage4_2r3c3t13s24d1r14r8r5_self_test.sh",
        "run_stage4_2r3c3t13s24d1r14r8r5_verify_package.sh",
        "scripts/stage4_2r3c3t13s24d1r14r8r5_context_robust_observer_campaign.py",
        "scripts/stage4_2r3c3t13s24d1r14r8r5_shell_common.sh",
        "tests/test_stage4_2r3c3t13s24d1r14r8r5_context_robust_observer_holdout.py",
        "tsc_rzip_rllib/control/causal_history_no_action_observer.py",
        "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r8r5_context_robust_observer_holdout.py",
        "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r8r5_context_robust_observer_campaign.py",
    )
    rows = []
    for name in names:
        path = _root() / name
        if not path.is_file():
            raise ValueError(f"R8R5 package source missing: {name}")
        rows.append({"path": name, "bytes": path.stat().st_size, "sha256": _sha(path)})
    return {"files": rows, "digest": r8._digest(rows)}


def _authenticate_source(ctx: Context) -> dict[str, Any]:
    expected = ctx.cfg["source_r8r4_contract"]
    paths = ctx.source_ctx.paths
    audit = {
        "development_raw_primary": paths.analysis / "development_raw_primary.json",
        "development_raw_independent": paths.analysis
        / "development_raw_independent.json",
        "development_model_primary_detailed": paths.analysis
        / "development_model_primary_detailed.json",
        "development_model_primary_summary": paths.analysis
        / "development_model_primary_summary.json",
        "development_model_independent": paths.analysis
        / "development_model_independent.json",
    }
    if (
        _sha(paths.manifest) != str(expected["stage_manifest_sha256"])
        or _sha(paths.state) != str(expected["stage_state_sha256"])
        or any(
            not path.is_file()
            or _sha(path) != str(expected[f"{name}_sha256"])
            for name, path in audit.items()
        )
    ):
        raise ValueError("R8R5 immutable R8R4 hashes changed")
    state = _read(paths.state)
    development = r8._inventory(paths.phase_raw("development"))
    holdout = r8._inventory(paths.phase_raw("holdout"))
    model_files = [path for path in paths.model.iterdir() if path.is_file()]
    independent = _read(audit["development_model_independent"])
    if (
        state.get("phase_status") != "development_model_failed"
        or state.get("finished") is not True
        or state.get("holdout_outcomes_opened") is not False
        or (state.get("verdict") or {}).get("route") != expected["required_route"]
        or development["count"] != int(expected["development_raw_count"])
        or development["bytes"] != int(expected["development_raw_bytes"])
        or development["digest"] != str(expected["development_raw_digest"])
        or holdout["count"] != int(expected["holdout_raw_count"])
        or len(model_files) != int(expected["model_file_count"])
        or independent.get("passed") is not True
        or independent.get("primary_numerical_agreement") is not True
        or independent.get("scientific_gate_passed") is not False
        or independent.get("route") != expected["required_route"]
    ):
        raise ValueError("R8R5 immutable R8R4 outcome changed")
    return {
        "stage_manifest_sha256": _sha(paths.manifest),
        "stage_state_sha256": _sha(paths.state),
        "development_raw_inventory": development,
        "holdout_raw_inventory": holdout,
        "model_file_count": len(model_files),
        **{f"{name}_sha256": _sha(path) for name, path in audit.items()},
    }


def _holdout_specs(ctx: Context) -> list[dict[str, Any]]:
    originals = source._phase_specs(ctx.source_ctx, "holdout")
    output = []
    for index, original in enumerate(
        sorted(originals, key=lambda row: (str(row["pair_id"]), str(row["history_member"])))
    ):
        spec = copy.deepcopy(original)
        source_id = str(spec["experiment_id"])
        for key in tuple(spec):
            if str(key).startswith("r8r4_"):
                spec.pop(key)
        spec.update(
            {
                "kind": "stage4_2r3c3t13s24d1r14r8r5_context_robust_observer_holdout_baseline",
                "partition": "holdout",
                "experiment_id": f"r8r5_holdout_{index:02d}",
                "source_r8r4_blueprint_experiment_id": source_id,
                "r8r5_baseline_only": True,
                "r8r5_zero_action_first_task_step": 10,
                "r8r5_allowed_in_expert_dataset": False,
            }
        )
        output.append(spec)
    if (
        len(output) != 8
        or {str(row["pair_id"]) for row in output} != set(contract.HOLDOUT_PAIRS)
        or len({str(row["experiment_id"]) for row in output}) != 8
    ):
        raise ValueError("R8R5 holdout specification coverage changed")
    return output


def prepare_offline(ctx: Context) -> dict[str, Any]:
    if ctx.paths.stage_dir.exists() or ctx.paths.state.exists():
        raise ValueError("R8R5 offline requires a fresh run identity")
    source_auth = _authenticate_source(ctx)
    specs = _holdout_specs(ctx)
    package = _package_fingerprint()
    for path in (
        ctx.paths.stage_dir,
        ctx.paths.variants,
        ctx.paths.specs,
        ctx.paths.source_reference,
        ctx.paths.analysis,
        ctx.paths.model,
        ctx.paths.phase_raw("holdout"),
    ):
        path.mkdir(parents=True, exist_ok=True)
    _write(ctx.paths.specs / "holdout_specs.json", specs)
    _write(ctx.paths.source_reference / "r8r4_authentication.json", source_auth)
    manifest = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "campaign_identity": contract.IDENTITY,
        "controller_revision": contract.CONTROLLER_REVISION,
        "package_revision": contract.PACKAGE_REVISION,
        "config_path": str(ctx.config_path),
        "config_sha256": _sha(ctx.config_path),
        "design_document_sha256": contract.DESIGN_SHA256,
        "source_r8r4_run": str(ctx.r8r4_run),
        "holdout_spec_count": 8,
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
        "source_r8r4_authenticated": True,
        "development_new_raw_count": 0,
        "holdout_spec_count": 8,
        "holdout_raw_count": 0,
        "real_tsc_executed": False,
        "passed": True,
    }
    _write(ctx.paths.analysis / "offline_preflight.json", report)
    return report


def _specs(ctx: Context) -> list[dict[str, Any]]:
    specs = _read(ctx.paths.specs / "holdout_specs.json")
    manifest = _read(ctx.paths.manifest)
    if (
        len(specs) != 8
        or r8._digest(specs) != manifest.get("spec_digest")
        or manifest.get("stage") != contract.STAGE
        or manifest.get("campaign_identity") != contract.IDENTITY
        or manifest.get("controller_revision") != contract.CONTROLLER_REVISION
        or _sha(ctx.config_path) != manifest.get("config_sha256")
    ):
        raise ValueError("R8R5 saved identity or specs changed")
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
            f"R8R5 phase guard expected {phase_status!r}, got {state.get('phase_status')!r}"
        )
    return state


def _candidate(ctx: Context) -> observer.Candidate:
    value = ctx.cfg["fixed_model_contract"]
    return observer.Candidate(
        family=str(value["family"]),
        pca_rank=int(value["pca_rank"]),
        bandwidth_multiplier=float(value["bandwidth_multiplier"]),
        ridge=float(value["ridge"]),
    )


def _development_rows(ctx: Context) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    prior, prior_signature = source._prior_rows(ctx.source_ctx)
    fresh, fresh_signature = source._fresh_rows(ctx.source_ctx, "development")
    rows = sorted(prior + fresh, key=lambda row: row["row_id"])
    if (
        len({str(row["pair_id"]) for row in rows}) != 16
        or len({f"{row['pair_id']}|{row['history_member']}" for row in rows}) != 32
    ):
        raise ValueError("R8R5 consumed development coverage changed")
    return rows, {"prior": prior_signature, "fresh_r8r4": fresh_signature}


def fixed_outer_predictions(
    items: Sequence[Mapping[str, Any]], candidate: observer.Candidate, cfg: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    folds: list[dict[str, Any]] = []
    for pair in sorted({str(item["pair_id"]) for item in items}):
        training = [item for item in items if str(item["pair_id"]) != pair]
        held = [item for item in items if str(item["pair_id"]) == pair]
        model = observer.fit_model(training, candidate, cfg)
        current = [
            observer.prediction_row(item, prediction, cfg)
            for item, prediction in zip(held, observer.predict_model(model, held, cfg))
        ]
        rows.extend(current)
        folds.append(
            {
                "held_pair_id": pair,
                "training_pair_count": 15,
                "held_origin_row_count": len(held),
                "point_pass_count": sum(bool(row["passed"]) for row in current),
                "finite_exclusion_violation_count": sum(
                    int(row["finite_exclusion_violation_count"]) for row in current
                ),
            }
        )
    return sorted(rows, key=lambda row: row["row_id"]), folds


def context_robust_tube(
    rows: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> tuple[np.ndarray, dict[str, Any]]:
    residual = np.asarray([row["absolute_residual_physical"] for row in rows], dtype=float)
    floor = np.asarray(cfg["tube_contract"]["component_floor_physical"], dtype=float)
    if residual.ndim != 3 or residual.shape[1:] != (12, 5):
        raise ValueError("R8R5 tube residual shape changed")
    tube_cfg = cfg["tube_contract"]
    base = np.quantile(
        residual,
        float(tube_cfg["base_absolute_residual_quantile"]),
        axis=0,
        method="higher",
    ) + floor[None, :]
    ratios = np.max(residual / base[None, :, :], axis=(1, 2))
    aggregate = float(
        np.quantile(
            ratios,
            float(tube_cfg["aggregate_row_ratio_quantile"]),
            method="higher",
        )
    )
    context_values: dict[str, float] = {}
    for context in sorted(
        {f"{row['pair_id']}|{row['history_member']}" for row in rows}
    ):
        current = np.asarray(
            [
                ratio
                for row, ratio in zip(rows, ratios)
                if f"{row['pair_id']}|{row['history_member']}" == context
            ],
            dtype=float,
        )
        context_values[context] = float(
            np.quantile(
                current,
                float(tube_cfg["per_context_row_ratio_quantile"]),
                method="higher",
            )
        )
    calibration = max([aggregate, *context_values.values()])
    scalar = max(
        float(tube_cfg["scalar_floor"]),
        float(tube_cfg["blind_holdout_reserve_multiplier"]) * calibration,
    )
    tube = scalar * base
    if not np.all(np.isfinite(tube)):
        raise ValueError("R8R5 tube is non-finite")
    return tube, {
        "aggregate_q95_row_ratio": aggregate,
        "per_context_q90_row_ratios": context_values,
        "calibration_ratio": calibration,
        "reserve_multiplier": float(tube_cfg["blind_holdout_reserve_multiplier"]),
        "scalar": scalar,
    }


def fit_development(ctx: Context) -> dict[str, Any]:
    _require(ctx, "offline_ready")
    _authenticate_source(ctx)
    if r8._inventory(ctx.paths.phase_raw("holdout"))["count"]:
        raise ValueError("R8R5 holdout opened before development freeze")
    items, source_signature = _development_rows(ctx)
    candidate = _candidate(ctx)
    outer_rows, folds = fixed_outer_predictions(items, candidate, ctx.cfg)
    point = source._point_evaluation(outer_rows, ctx.cfg)
    tube, tube_derivation = context_robust_tube(outer_rows, ctx.cfg)
    tube_evaluation = observer.practical_evaluation(outer_rows, tube, ctx.cfg)
    cap = np.asarray(ctx.cfg["tube_contract"]["component_caps_physical"], dtype=float)
    tube_cap_passed = bool(np.all(tube <= cap[None, :] + 1e-15))
    scientific = bool(
        len(folds) == int(ctx.cfg["gates"]["required_development_outer_fold_count"])
        and point["passed"]
        and tube_evaluation["passed"]
        and tube_cap_passed
    )
    model_sha = tube_sha = ""
    if scientific:
        fitted = observer.fit_model(items, candidate, ctx.cfg)
        model_path = ctx.paths.model / "observer_model.json"
        tube_path = ctx.paths.model / "observer_tube.json"
        _write(
            model_path,
            {
                "schema_version": 1,
                "stage": contract.STAGE,
                "campaign_identity": contract.IDENTITY,
                "feature_contract": ctx.cfg["feature_contract"],
                "training_pair_count": 16,
                "fixed_candidate": candidate.as_dict(),
                "source_r8r4_state_sha256": ctx.cfg["source_r8r4_contract"][
                    "stage_state_sha256"
                ],
                "model": observer.serializable_model(fitted, tube),
            },
        )
        _write(
            tube_path,
            {
                "schema_version": 1,
                "stage": contract.STAGE,
                "campaign_identity": contract.IDENTITY,
                "tube_physical": tube.tolist(),
                "derivation": "context_robust_global_higher_quantile_scaled_v1",
                "tube_derivation": tube_derivation,
                "fixed_candidate": candidate.as_dict(),
            },
        )
        model_sha, tube_sha = _sha(model_path), _sha(tube_path)
    route = ctx.cfg["routes"]["pass" if scientific else "development_model_fail"]
    detailed = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "phase": "fixed_candidate_context_robust_development_freeze",
        "source_signature": source_signature,
        "development_pair_count": 16,
        "development_context_count": 32,
        "development_origin_row_count": len(items),
        "outer_fold_count": len(folds),
        "fixed_candidate": candidate.as_dict(),
        "outer_folds": folds,
        "outer_rows": outer_rows,
        "point_evaluation": point,
        "tube_derivation": tube_derivation,
        "tube_physical": tube.tolist(),
        "tube_cap_passed": tube_cap_passed,
        "tube_evaluation": tube_evaluation,
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
        if key not in {"outer_folds", "outer_rows"}
    }
    summary["tube_evaluation"] = {
        key: value for key, value in tube_evaluation.items() if key != "rows"
    }
    summary["primary_detailed_sha256"] = _sha(detailed_path)
    summary_path = ctx.paths.analysis / "development_model_primary_summary.json"
    _write(summary_path, summary)
    _set_state(
        ctx,
        phase_status="development_model_primary_complete",
        development_scientific_gate_passed=scientific,
        development_model_primary_summary_sha256=_sha(summary_path),
        observer_model_sha256=model_sha,
        observer_tube_sha256=tube_sha,
        verdict={"route": route, "passed": scientific},
    )
    return summary


def _independent(ctx: Context, name: str) -> dict[str, Any]:
    path = ctx.paths.analysis / f"{name}_independent.json"
    if not path.is_file():
        raise ValueError(f"R8R5 independent {name} audit missing")
    value = _read(path)
    if value.get("passed") is not True:
        raise ValueError(f"R8R5 independent {name} audit failed")
    return value


def authorize_holdout(ctx: Context) -> dict[str, Any]:
    state = _require(ctx, "development_model_primary_complete")
    independent = _independent(ctx, "development_model")
    summary_path = ctx.paths.analysis / "development_model_primary_summary.json"
    summary = _read(summary_path)
    scientific = bool(state.get("development_scientific_gate_passed"))
    if (
        independent.get("primary_summary_sha256") != _sha(summary_path)
        or independent.get("primary_numerical_agreement") is not True
        or independent.get("scientific_gate_passed") is not scientific
        or independent.get("route") != summary.get("route")
        or independent.get("observer_model_sha256")
        != str(state.get("observer_model_sha256") or "")
        or independent.get("observer_tube_sha256")
        != str(state.get("observer_tube_sha256") or "")
        or r8._inventory(ctx.paths.phase_raw("holdout"))["count"]
    ):
        raise ValueError("R8R5 independent development disagreement")
    if not scientific:
        route = ctx.cfg["routes"]["development_model_fail"]
        _set_state(
            ctx,
            phase_status="development_model_failed",
            finished=True,
            stop_reason="fixed_point_or_context_robust_tube_development_failed",
            verdict={"route": route, "passed": False},
        )
        return {"stage": contract.STAGE, "authorized": False, "route": route}
    if (
        _sha(ctx.paths.model / "observer_model.json")
        != state["observer_model_sha256"]
        or _sha(ctx.paths.model / "observer_tube.json")
        != state["observer_tube_sha256"]
    ):
        raise ValueError("R8R5 frozen model or tube changed")
    _set_state(ctx, phase_status="holdout_authorized")
    return {
        "stage": contract.STAGE,
        "authorized": True,
        "observer_model_sha256": state["observer_model_sha256"],
        "observer_tube_sha256": state["observer_tube_sha256"],
        "holdout_raw_count": 0,
    }


def _execution_context(ctx: Context) -> r8.Context:
    source_ctx = ctx.source_ctx
    return r8.Context(
        cfg=source_ctx.r8_cfg,
        config_path=source_ctx.r8_config_path,
        d1r11_ctx=source_ctx.r8_ctx.d1r11_ctx,
        source_d1r11_run=source_ctx.r8_ctx.source_d1r11_run,
        source_response_runs=source_ctx.r8_ctx.source_response_runs,
        paths=ctx.paths,  # type: ignore[arg-type]
    )


def _payload(ctx: Context, spec: Mapping[str, Any]) -> dict[str, Any]:
    payload = r8._payload(_execution_context(ctx), spec)
    experiment_id = str(spec["experiment_id"])
    payload.update(
        {
            "variant_id": f"stage4_2r3c3t13s24d1r14r8r5_{experiment_id}",
            "stage4_2r3c3t13s24d1r14r8r5_baseline_only": True,
            "stage4_2r3c3t13s24d1r14r8r5_zero_action_first_task_step": 10,
            "stage4_2r3c3t13s24d1r14r8r5_pair_history_label_available_to_controller": False,
        }
    )
    _write(ctx.paths.variants / f"payload_{experiment_id}.json", payload)
    return payload


class LocalWorker:
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
                    "r3c3t13s24d1r14r8r5_controller_revision": contract.CONTROLLER_REVISION,
                    "r3c3t13s24d1r14r8r5_baseline_only": True,
                    "r3c3t13s24d1r14r8r5_future_r17_executed": False,
                    "r3c3t13s24d1r14r8r5_pair_or_history_label_used": False,
                    "r3c3t13s24d1r14r8r5_partition_label_used": False,
                    "r3c3t13s24d1r14r8r5_source_result_used": False,
                }
            )
        result.setdefault("hidden_history_control_summary", {}).update(
            {
                "fresh_controller_actor": True,
                "fresh_tsc_process": True,
                "identification_only": True,
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
        class Stage42R8R5Actor:
            def __init__(self, *args: Any):
                self.worker = LocalWorker(*args)

            def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
                return self.worker.evaluate(spec)

            def close(self) -> bool:
                self.worker.close()
                return True

        _RAY_ACTOR = Stage42R8R5Actor
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


def evaluate_specs(ctx: Context, *, backend: str, resume: bool) -> dict[str, Any]:
    specs = _specs(ctx)
    raw_dir = ctx.paths.phase_raw("holdout")
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
            f"stage42r8r5_holdout_{index:02d}",
            selector,
            lattice,
            calibration,
            dynamic,
            schedule,
            r8._kernel_contract(ctx.source_ctx.r8_cfg, kernel),
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
            print(f"[R8R5 holdout] {index + 1}/{len(pending)}", flush=True)
    elif backend == "ray" and pending:
        import ray

        plan = r8.d1r11.s21.s16.ensure_ray_worker_plan(
            ray,
            requested_workers=int(ctx.cfg["parallel"]["n_workers"]),
            pending_tasks=len(pending),
            ray_tmpdir=os.environ.get("RAY_TMPDIR") or ctx.cfg["storage"]["ray_tmpdir"],
            log_prefix="[R8R5 holdout]",
        )
        Actor = _ray_actor_class()
        for start in range(0, len(pending), plan.actor_count):
            batch = pending[start : start + plan.actor_count]
            actors, refs = [], {}
            for offset, spec in enumerate(batch):
                actor = Actor.remote(*worker_args(spec, start + offset))
                actors.append(actor)
                refs[actor.evaluate.remote(spec)] = spec
            try:
                while refs:
                    ready, _ = ray.wait(list(refs), num_returns=1)
                    ref = ready[0]
                    spec = refs.pop(ref)
                    r8._write_gz(raw_dir / f"{spec['experiment_id']}.json.gz", ray.get(ref))
                    print(
                        f"[R8R5 holdout] {len(pending) - len(refs)}/{len(pending)}",
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
        raise ValueError(f"unsupported R8R5 backend: {backend}")
    successful = sum(
        _result_complete(raw_dir / f"{spec['experiment_id']}.json.gz", spec)
        for spec in specs
    )
    return {
        "phase": "holdout",
        "expected": 8,
        "pending_at_start": len(pending),
        "successful": successful,
        "passed": successful == 8,
    }


R8R5_FORBIDDEN_TRACE_KEYS = tuple(
    dict.fromkeys(
        r8.R8_FORBIDDEN_TRACE_KEYS
        + (
            "r3c3t13s24d1r14r8r5_future_r17_executed",
            "r3c3t13s24d1r14r8r5_pair_or_history_label_used",
            "r3c3t13s24d1r14r8r5_partition_label_used",
            "r3c3t13s24d1r14r8r5_source_result_used",
        )
    )
)


def audit_raw(ctx: Context) -> dict[str, Any]:
    specs = _specs(ctx)
    raw_dir = ctx.paths.phase_raw("holdout")
    sources = r8._source_baseline_results(ctx.source_ctx.r8_ctx)
    rows = []
    for spec in specs:
        experiment_id = str(spec["experiment_id"])
        path = raw_dir / f"{experiment_id}.json.gz"
        if not _result_complete(path, spec, success=False):
            rows.append(
                {"experiment_id": experiment_id, "runtime_success": False, "passed": False}
            )
            continue
        result = r8._read_gz(path)
        trajectory = result.get("trajectory") or []
        trace = result.get("controller_trace") or []
        baseline = sources[str(spec["source_s21_baseline_experiment_id"])]
        horizon = int(spec["horizon_steps"])
        full = len(trajectory) == horizon + 1 and len(trace) == horizon
        prefix_state = bool(
            len(trajectory) >= 11
            and all(
                r8.r4._semantic_state(current) == r8.r4._semantic_state(reference)
                for current, reference in zip(trajectory[:11], baseline["trajectory"][:11])
            )
        )
        prefix_trace = bool(
            len(trace) >= 10
            and all(
                r8.r4._source_trace_projection(reference, current)
                for current, reference in zip(trace[:10], baseline["controller_trace"][:10])
            )
        )
        calibration = r8.r4._calibration_exact(trace)
        actions = np.asarray([row.get("action_norm_tsc", []) for row in trace], dtype=float)
        currents = np.asarray([row.get("currents_a_tsc", []) for row in trajectory], dtype=float)
        wires = [np.asarray(row.get("wire_currents_a", []), dtype=float) for row in trajectory]
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
        zero_future = bool(full and np.array_equal(actions[10:], np.zeros_like(actions[10:])))
        constant_future = bool(
            full
            and np.array_equal(
                np.diff(currents[10:], axis=0),
                np.zeros_like(np.diff(currents[10:], axis=0)),
            )
        )
        forbidden = sum(
            any(bool(row.get(key)) for key in R8R5_FORBIDDEN_TRACE_KEYS) for row in trace
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
            and zero_future
            and constant_future
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
                "full_horizon": full,
                "source_prefix_state_exact": prefix_state,
                "source_prefix_trace_exact": prefix_trace,
                "calibration_exact": calibration,
                "zero_future_action_exact": zero_future,
                "constant_future_commanded_current_exact": constant_future,
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
        "phase": "holdout",
        "expected_raw_count": 8,
        "raw_inventory": inventory,
        "runtime_success_count": sum(bool(row.get("runtime_success")) for row in rows),
        "full_horizon_count": sum(bool(row.get("full_horizon")) for row in rows),
        "source_prefix_state_exact_count": sum(bool(row.get("source_prefix_state_exact")) for row in rows),
        "source_prefix_trace_exact_count": sum(bool(row.get("source_prefix_trace_exact")) for row in rows),
        "zero_future_action_exact_count": sum(bool(row.get("zero_future_action_exact")) for row in rows),
        "constant_future_commanded_current_exact_count": sum(bool(row.get("constant_future_commanded_current_exact")) for row in rows),
        "source_restart_snapshot_authenticated_count": sum(bool(row.get("source_restart_snapshot_authenticated")) for row in rows),
        "finite_count": sum(bool(row.get("finite")) for row in rows),
        "forbidden_trace_count": sum(int(row.get("forbidden_trace_count", 0)) for row in rows),
        "maximum_total_normalized_action_abs": max((float(row.get("maximum_total_normalized_action_abs", math.inf)) for row in rows), default=math.inf),
        "maximum_current_utilization": max((float(row.get("maximum_current_utilization", math.inf)) for row in rows), default=math.inf),
        "passed_count": sum(bool(row.get("passed")) for row in rows),
        "rows": rows,
    }
    report["passed"] = bool(inventory["count"] == 8 and len(rows) == 8 and report["passed_count"] == 8)
    report["route"] = ctx.cfg["routes"]["pass" if report["passed"] else "holdout_execution_fail"]
    _write(ctx.paths.analysis / "holdout_raw_primary.json", report)
    return report


def run_holdout(ctx: Context, *, backend: str, resume: bool) -> dict[str, Any]:
    _require(ctx, "holdout_authorized")
    execution = evaluate_specs(ctx, backend=backend, resume=resume)
    primary = audit_raw(ctx)
    if not execution["passed"] or not primary["passed"]:
        route = ctx.cfg["routes"]["holdout_execution_fail"]
        _set_state(
            ctx,
            phase_status="holdout_execution_failed",
            finished=True,
            real_tsc_executed=primary["raw_inventory"]["count"] > 0,
            new_raw_count=primary["raw_inventory"]["count"],
            holdout_outcomes_opened=True,
            stop_reason="holdout_runtime_restart_action_current_or_raw_gate_failed",
            verdict={"route": route, "passed": False},
        )
    else:
        _set_state(
            ctx,
            phase_status="holdout_raw_primary_passed",
            real_tsc_executed=True,
            new_raw_count=8,
            holdout_outcomes_opened=True,
            holdout_raw_inventory_digest=primary["raw_inventory"]["digest"],
        )
    return {
        "execution": execution,
        "primary_raw_audit": {key: value for key, value in primary.items() if key != "rows"},
    }


def _holdout_rows(ctx: Context) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    scales = np.asarray(ctx.cfg["bank_contract"]["visible_scales"], dtype=float)
    prescribed = set(map(int, ctx.cfg["bank_contract"]["prescribed_issue_task_steps"]))
    rows, raw_hashes = [], {}
    for spec in _specs(ctx):
        path = ctx.paths.phase_raw("holdout") / f"{spec['experiment_id']}.json.gz"
        if not _result_complete(path, spec):
            raise ValueError("R8R5 holdout raw incomplete before scoring")
        result = r8._read_gz(path)
        visible = source.r7_source._visible(result["trajectory"], scales)
        actions = source.r8r3_primary._actions(result)
        currents = source.r8r3_primary._currents(result)
        maximum = len(visible) - 1 - int(ctx.cfg["bank_contract"]["future_state_count"])
        for origin in range(int(ctx.cfg["bank_contract"]["first_origin_task_step"]), maximum + 1):
            feature = observer.causal_feature(
                visible[: origin + 1],
                actions[:origin],
                currents[: origin + 1],
                source.r8r3_primary._target(spec),
                origin,
                ctx.cfg,
            )
            rows.append(
                {
                    "row_id": f"holdout|{spec['pair_id']}|{spec['history_member']}|origin{origin:02d}",
                    "context_id": f"{spec['pair_id']}|{spec['history_member']}",
                    "pair_id": str(spec["pair_id"]),
                    "history_member": str(spec["history_member"]),
                    "origin_task_step": origin,
                    "prescribed_issue": origin in prescribed,
                    "feature": feature,
                    "origin_visible": visible[origin],
                    "target_delta": observer.target_delta(visible, origin, ctx.cfg),
                    "future_visible": visible[origin + 1 : origin + 13],
                }
            )
        raw_hashes[str(spec["experiment_id"])] = _sha(path)
    signature = {
        "pair_count": len({str(row["pair_id"]) for row in rows}),
        "context_count": len({str(row["context_id"]) for row in rows}),
        "origin_row_count": len(rows),
        "prescribed_issue_row_count": sum(bool(row["prescribed_issue"]) for row in rows),
        "feature_dimension": 353,
        "raw_sha256": raw_hashes,
        "forbidden_predictor_input_count": 0,
        "future_input_count": 0,
        "allowed_in_expert_dataset": False,
    }
    if (
        signature["pair_count"] != 4
        or signature["context_count"] != 8
        or signature["prescribed_issue_row_count"] != 32
        or any(len(np.asarray(row["feature"])) != 353 for row in rows)
    ):
        raise ValueError("R8R5 holdout causal row coverage changed")
    return sorted(rows, key=lambda row: row["row_id"]), signature


def finalize_holdout(ctx: Context) -> dict[str, Any]:
    state = _require(ctx, "holdout_raw_primary_passed")
    primary_raw_path = ctx.paths.analysis / "holdout_raw_primary.json"
    independent_raw = _independent(ctx, "holdout_raw")
    if (
        independent_raw.get("primary_sha256") != _sha(primary_raw_path)
        or independent_raw.get("raw_inventory") != _read(primary_raw_path).get("raw_inventory")
    ):
        raise ValueError("R8R5 independent raw disagreement")
    model_path = ctx.paths.model / "observer_model.json"
    tube_path = ctx.paths.model / "observer_tube.json"
    if _sha(model_path) != state["observer_model_sha256"] or _sha(tube_path) != state["observer_tube_sha256"]:
        raise ValueError("R8R5 frozen model/tube changed before holdout scoring")
    artifact = _read(model_path)
    tube = np.asarray(_read(tube_path)["tube_physical"], dtype=float)
    model = source._model_from_artifact(artifact)
    items, signature = _holdout_rows(ctx)
    rows = [
        observer.prediction_row(item, prediction, ctx.cfg)
        for item, prediction in zip(items, observer.predict_model(model, items, ctx.cfg))
    ]
    evaluation = observer.practical_evaluation(rows, tube, ctx.cfg)
    coverage = bool(
        len({str(row["pair_id"]) for row in rows}) == 4
        and len({f"{row['pair_id']}|{row['history_member']}" for row in rows}) == 8
        and sum(bool(row["prescribed_issue"]) for row in rows) == 32
    )
    scientific = bool(coverage and evaluation["passed"])
    route = ctx.cfg["routes"]["pass" if scientific else "holdout_model_fail"]
    detailed = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "phase": "blind_holdout_fixed_model_and_context_robust_tube",
        "holdout_signature": signature,
        "holdout_coverage_passed": coverage,
        "holdout_evaluation": evaluation,
        "observer_model_sha256": state["observer_model_sha256"],
        "observer_tube_sha256": state["observer_tube_sha256"],
        "route": route,
        "scientific_gate_passed": scientific,
        "heldout_outcomes_opened": True,
        "new_raw_count": 8,
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
        or independent.get("primary_numerical_agreement") is not True
        or independent.get("scientific_gate_passed") is not scientific
        or independent.get("route") != summary.get("route")
        or independent.get("observer_model_sha256") != state.get("observer_model_sha256")
        or independent.get("observer_tube_sha256") != state.get("observer_tube_sha256")
    ):
        raise ValueError("R8R5 independent holdout disagreement")
    inventory = r8._inventory(ctx.paths.phase_raw("holdout"))
    if inventory["count"] != 8:
        raise ValueError("R8R5 final raw inventory changed")
    final = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "phase": "final_dual_audit",
        "route": str(summary["route"]),
        "scientific_gate_passed": scientific,
        "holdout_raw_inventory": inventory,
        "observer_model_sha256": state["observer_model_sha256"],
        "observer_tube_sha256": state["observer_tube_sha256"],
        "primary_summary_sha256": _sha(summary_path),
        "independent_sha256": _sha(ctx.paths.analysis / "holdout_model_independent.json"),
        "new_raw_count": 8,
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
        stop_reason="" if scientific else "blind_holdout_point_or_tube_gate_failed",
        verdict={"route": final["route"], "passed": scientific},
    )
    return final


def execute(ctx: Context, *, command: str, backend: str, resume: bool) -> dict[str, Any]:
    if command == "offline":
        return prepare_offline(ctx)
    if command == "fit-development":
        return fit_development(ctx)
    if command == "authorize-holdout":
        return authorize_holdout(ctx)
    if command == "holdout":
        return run_holdout(ctx, backend=backend, resume=resume)
    if command == "finalize":
        return finalize_holdout(ctx)
    if command == "postprocess":
        return postprocess(ctx)
    raise ValueError(f"unsupported R8R5 command: {command}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--r8-run", type=Path, required=True)
    parser.add_argument("--r8r3-output", type=Path, required=True)
    parser.add_argument("--r8r4-run", type=Path, required=True)
    for name in (
        "source-d1r11-run",
        "source-r2-run",
        "source-r4-run",
        "source-r6-run",
        "source-s21-run",
        "source-s23r1-output",
        "source-s24-run",
        "source-d1r9-v1",
        "source-d1r9-v2",
        "source-d1r10-run",
        "source-d1r10-audit",
        "source-stage42r3b-run",
        "source-stage42r3c3-run",
        "source-stage42r3c3-bank-dir",
        "source-stage42r3c3t1-run",
        "source-stage42r3c3t1-audit-dir",
        "source-stage42r3c3t3-controller-bank",
        "q1-run",
        "q2-run",
        "q1-audit",
        "q2-audit",
        "r3b-server-audit",
        "r3b-snapshot-checks",
    ):
        parser.add_argument(f"--{name}", dest=name.replace("-", "_"), type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument(
        "--command",
        choices=(
            "offline",
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
    args = _parser().parse_args()
    if args.self_test:
        print(json.dumps(contract.self_test(args.config), indent=2, sort_keys=True))
        return
    ctx = load_context(args)
    result = execute(ctx, command=args.command, backend=args.backend, resume=args.resume)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
