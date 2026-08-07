"""Execute the frozen zero-TSC R8R6 causal innovation observer audit."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.control import causal_history_no_action_observer as observer
from tsc_rzip_rllib.control import causal_one_step_innovation_observer as innovation
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification as r8,
    stage4_2r3c3t13s24d1r14r8r5_context_robust_observer_campaign as r8r5,
    stage4_2r3c3t13s24d1r14r8r6_causal_one_step_innovation_observer as contract,
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
    stage: Path
    source_reference: Path
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
        source_reference=stage / "source_reference",
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
    source_ctx: r8r5.Context


def load_context(args: argparse.Namespace) -> Context:
    config_path = args.config.expanduser().resolve()
    cfg = _read(config_path)
    contract.validate_config(cfg, project_root=_root())
    values = vars(args).copy()
    values["config"] = (_root() / str(cfg["source_r8r5_config"])).resolve()
    values["run_dir"] = args.r8r5_run.expanduser().resolve()
    source_ctx = r8r5.load_context(argparse.Namespace(**values))
    return Context(
        cfg=cfg,
        config_path=config_path,
        paths=_paths(args.run_dir),
        source_ctx=source_ctx,
    )


def _package_fingerprint() -> dict[str, Any]:
    names = (
        "configs/stage4_2r3c3t13s24d1r14r8r6_causal_one_step_innovation_observer.json",
        "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r6_independent_forensics.py",
        "docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R6_CAUSAL_ONE_STEP_INNOVATION_OBSERVER_DESIGN.md",
        "run_stage4_2r3c3t13s24d1r14r8r6_common.sh",
        "run_stage4_2r3c3t13s24d1r14r8r6_native.sh",
        "run_stage4_2r3c3t13s24d1r14r8r6_nohup.sh",
        "run_stage4_2r3c3t13s24d1r14r8r6_self_test.sh",
        "run_stage4_2r3c3t13s24d1r14r8r6_verify_package.sh",
        "scripts/stage4_2r3c3t13s24d1r14r8r6_causal_one_step_innovation_observer.py",
        "scripts/stage4_2r3c3t13s24d1r14r8r6_shell_common.sh",
        "tests/test_stage4_2r3c3t13s24d1r14r8r6_causal_one_step_innovation_observer.py",
        "tsc_rzip_rllib/control/causal_history_no_action_observer.py",
        "tsc_rzip_rllib/control/causal_one_step_innovation_observer.py",
        "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r8r6_causal_one_step_innovation_observer.py",
        "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r8r6_causal_one_step_innovation_observer_audit.py",
    )
    rows = []
    for name in names:
        path = _root() / name
        if not path.is_file():
            raise ValueError(f"R8R6 package source missing: {name}")
        rows.append({"path": name, "bytes": path.stat().st_size, "sha256": _sha(path)})
    return {"files": rows, "digest": r8._digest(rows)}


def _authenticate_source(ctx: Context) -> dict[str, Any]:
    expected = ctx.cfg["source_r8r5_contract"]
    paths = ctx.source_ctx.paths
    analysis = {
        "holdout_raw_primary": paths.analysis / "holdout_raw_primary.json",
        "holdout_raw_independent": paths.analysis / "holdout_raw_independent.json",
        "development_model_primary_detailed": paths.analysis
        / "development_model_primary_detailed.json",
        "development_model_primary_summary": paths.analysis
        / "development_model_primary_summary.json",
        "development_model_independent": paths.analysis
        / "development_model_independent.json",
        "holdout_model_primary_detailed": paths.analysis
        / "holdout_model_primary_detailed.json",
        "holdout_model_primary_summary": paths.analysis
        / "holdout_model_primary_summary.json",
        "holdout_model_independent": paths.analysis
        / "holdout_model_independent.json",
        "final_report": paths.analysis / "final_report.json",
    }
    model = paths.model / "observer_model.json"
    tube = paths.model / "observer_tube.json"
    if (
        _sha(paths.manifest) != str(expected["stage_manifest_sha256"])
        or _sha(paths.state) != str(expected["stage_state_sha256"])
        or any(
            not path.is_file()
            or _sha(path) != str(expected[f"{name}_sha256"])
            for name, path in analysis.items()
        )
        or not model.is_file()
        or not tube.is_file()
        or _sha(model) != str(expected["observer_model_sha256"])
        or _sha(tube) != str(expected["observer_tube_sha256"])
    ):
        raise ValueError("R8R6 immutable R8R5 hashes changed")
    state = _read(paths.state)
    final = _read(analysis["final_report"])
    raw = r8._inventory(paths.phase_raw("holdout"))
    raw_independent = _read(analysis["holdout_raw_independent"])
    model_independent = _read(analysis["holdout_model_independent"])
    if (
        state.get("phase_status") != "complete"
        or state.get("finished") is not True
        or state.get("real_tsc_executed") is not True
        or int(state.get("new_raw_count", -1)) != 8
        or state.get("holdout_outcomes_opened") is not True
        or (state.get("verdict") or {}).get("route") != expected["required_route"]
        or (state.get("verdict") or {}).get("passed") is not False
        or final.get("route") != expected["required_route"]
        or final.get("scientific_gate_passed") is not False
        or raw["count"] != int(expected["holdout_raw_count"])
        or raw["bytes"] != int(expected["holdout_raw_bytes"])
        or raw["digest"] != str(expected["holdout_raw_digest"])
        or raw_independent.get("passed") is not True
        or raw_independent.get("primary_numerical_agreement") is not True
        or model_independent.get("passed") is not True
        or model_independent.get("primary_numerical_agreement") is not True
    ):
        raise ValueError("R8R6 immutable R8R5 outcome changed")
    inherited = r8r5._authenticate_source(ctx.source_ctx)
    return {
        "stage_manifest_sha256": _sha(paths.manifest),
        "stage_state_sha256": _sha(paths.state),
        "holdout_raw_inventory": raw,
        "observer_model_sha256": _sha(model),
        "observer_tube_sha256": _sha(tube),
        "inherited_r8r4_authentication": inherited,
        **{f"{name}_sha256": _sha(path) for name, path in analysis.items()},
    }


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
        or state.get("package_digest")
        != (manifest.get("package_fingerprint") or {}).get("digest")
        or _sha(ctx.config_path) != manifest.get("config_sha256")
    ):
        raise ValueError(
            f"R8R6 phase guard expected {phase_status!r}, got {state.get('phase_status')!r}"
        )
    return state


def prepare_offline(ctx: Context) -> dict[str, Any]:
    if ctx.paths.stage.exists() or ctx.paths.state.exists():
        raise ValueError("R8R6 offline requires a fresh run identity")
    source = _authenticate_source(ctx)
    package = _package_fingerprint()
    for path in (ctx.paths.stage, ctx.paths.source_reference, ctx.paths.analysis, ctx.paths.model):
        path.mkdir(parents=True, exist_ok=True)
    _write(ctx.paths.source_reference / "r8r5_authentication.json", source)
    manifest = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "campaign_identity": contract.IDENTITY,
        "package_revision": contract.PACKAGE_REVISION,
        "config_path": str(ctx.config_path),
        "config_sha256": _sha(ctx.config_path),
        "design_document_sha256": contract.DESIGN_SHA256,
        "source_r8r5_run": str(ctx.source_ctx.paths.run_dir),
        "source_r8r5_stage_state_sha256": source["stage_state_sha256"],
        "package_fingerprint": package,
        "formal_timing_unchanged": True,
        "zero_new_tsc": True,
        "all_stage_trajectories_allowed_in_expert_dataset": False,
    }
    state = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "phase_status": "offline_ready",
        "finished": False,
        "real_tsc_executed": False,
        "new_raw_count": 0,
        "source_trajectories_modified": False,
        "package_digest": package["digest"],
        "observer_model_sha256": "",
        "observer_tube_sha256": "",
        "innovation_contract_sha256": "",
        "verdict": {},
    }
    _write(ctx.paths.manifest, manifest)
    _write(ctx.paths.state, state)
    report = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "phase": "source_authentication",
        "source_r8r5_authenticated": True,
        "zero_new_tsc": True,
        "new_raw_count": 0,
        "passed": True,
    }
    _write(ctx.paths.analysis / "offline_preflight.json", report)
    return report


def _candidate(ctx: Context) -> observer.Candidate:
    value = ctx.cfg["fixed_model_contract"]
    return observer.Candidate(
        family=str(value["family"]),
        pca_rank=int(value["pca_rank"]),
        bandwidth_multiplier=float(value["bandwidth_multiplier"]),
        ridge=float(value["ridge"]),
    )


def _bank(ctx: Context) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    _authenticate_source(ctx)
    development, development_signature = r8r5._development_rows(ctx.source_ctx)
    holdout, holdout_signature = r8r5._holdout_rows(ctx.source_ctx)
    rows = sorted(development + holdout, key=lambda row: str(row["row_id"]))
    bank = ctx.cfg["bank_contract"]
    signature = {
        "development": development_signature,
        "r8r5_holdout": holdout_signature,
        "physical_pair_count": len({str(row["pair_id"]) for row in rows}),
        "history_context_count": len(
            {f"{row['pair_id']}|{row['history_member']}" for row in rows}
        ),
        "origin_row_count": len(rows),
        "prescribed_issue_row_count": sum(bool(row["prescribed_issue"]) for row in rows),
        "feature_dimension": len(np.asarray(rows[0]["feature"])),
        "forbidden_predictor_input_count": 0,
        "future_input_count": 0,
        "allowed_in_expert_dataset": False,
    }
    if (
        len({str(row["row_id"]) for row in rows}) != len(rows)
        or signature["physical_pair_count"] != int(bank["physical_pair_count"])
        or signature["history_context_count"] != int(bank["history_context_count"])
        or signature["origin_row_count"] != int(bank["origin_row_count"])
        or signature["prescribed_issue_row_count"]
        != int(bank["prescribed_issue_row_count"])
        or signature["feature_dimension"] != int(bank["feature_dimension"])
        or any(len(np.asarray(row["feature"])) != int(bank["feature_dimension"]) for row in rows)
    ):
        raise ValueError("R8R6 combined bank coverage changed")
    return rows, signature


def _startup_evaluation(rows: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> dict[str, Any]:
    required = int(cfg["gates"]["required_startup_fallback_pass_count"])
    residual = np.asarray([row["absolute_residual_physical"] for row in rows], dtype=float)
    result = {
        "row_count": len(rows),
        "required_pass_count": required,
        "point_pass_count": sum(bool(row["passed"]) for row in rows),
        "finite_exclusion_violation_count": sum(
            int(row["finite_exclusion_violation_count"]) for row in rows
        ),
        "maximum_absolute_physical_error": np.max(residual, axis=(0, 1)).tolist(),
        "maximum_absolute_scaled_point_error": max(
            float(row["maximum_absolute_scaled_point_error"]) for row in rows
        ),
        "rows": list(rows),
    }
    result["passed"] = bool(
        len(rows) == required
        and result["point_pass_count"] == required
        and result["finite_exclusion_violation_count"] == 0
    )
    return result


def _outer_predictions(
    items: Sequence[Mapping[str, Any]],
    candidate: observer.Candidate,
    cfg: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    startup_rows: list[dict[str, Any]] = []
    cold_rows: list[dict[str, Any]] = []
    adapted_rows: list[dict[str, Any]] = []
    folds: list[dict[str, Any]] = []
    for pair in sorted({str(item["pair_id"]) for item in items}):
        training = [item for item in items if str(item["pair_id"]) != pair]
        held = [item for item in items if str(item["pair_id"]) == pair]
        model = observer.fit_model(training, candidate, cfg)
        cold_predictions = observer.predict_model(model, held, cfg)
        predictions = {
            str(item["row_id"]): value for item, value in zip(held, cold_predictions)
        }
        fold_startup = fold_adapted = fold_clipped = 0
        for context in sorted(
            {f"{item['pair_id']}|{item['history_member']}" for item in held}
        ):
            current = sorted(
                [
                    item
                    for item in held
                    if f"{item['pair_id']}|{item['history_member']}" == context
                ],
                key=lambda item: int(item["origin_task_step"]),
            )
            origins = [int(item["origin_task_step"]) for item in current]
            if not origins or origins[0] != 10 or origins != list(range(10, origins[-1] + 1)):
                raise ValueError("R8R6 held context origin sequence changed")
            for index, item in enumerate(current):
                cold_prediction = predictions[str(item["row_id"])]
                cold_row = observer.prediction_row(item, cold_prediction, cfg)
                if index == 0:
                    fallback = dict(cold_row)
                    fallback["observer_mode"] = "cold_startup_fallback"
                    startup_rows.append(fallback)
                    fold_startup += int(bool(fallback["passed"]))
                    continue
                previous = current[index - 1]
                previous_prediction = predictions[str(previous["row_id"])]
                adapted_prediction, innovation_audit = innovation.adapt_prediction(
                    item["origin_visible"], previous_prediction, cold_prediction, cfg
                )
                adapted = observer.prediction_row(item, adapted_prediction, cfg)
                adapted.update(innovation_audit)
                adapted["observer_mode"] = "causal_one_step_innovation"
                cold_row["observer_mode"] = "cold_comparator"
                cold_rows.append(cold_row)
                adapted_rows.append(adapted)
                fold_adapted += int(bool(adapted["passed"]))
                fold_clipped += int(bool(innovation_audit["clip_activated"]))
        folds.append(
            {
                "held_pair_id": pair,
                "training_pair_count": 19,
                "held_context_count": len(
                    {f"{item['pair_id']}|{item['history_member']}" for item in held}
                ),
                "held_origin_row_count": len(held),
                "startup_fallback_pass_count": fold_startup,
                "adapted_point_pass_count": fold_adapted,
                "innovation_clip_row_count": fold_clipped,
            }
        )
    return (
        sorted(startup_rows, key=lambda row: str(row["row_id"])),
        sorted(cold_rows, key=lambda row: str(row["row_id"])),
        sorted(adapted_rows, key=lambda row: str(row["row_id"])),
        folds,
    )


def evaluate_primary(ctx: Context) -> dict[str, Any]:
    _require(ctx, "offline_ready")
    items, source_signature = _bank(ctx)
    candidate = _candidate(ctx)
    startup_rows, cold_rows, adapted_rows, folds = _outer_predictions(
        items, candidate, ctx.cfg
    )
    bank = ctx.cfg["bank_contract"]
    if (
        len(folds) != int(ctx.cfg["gates"]["required_outer_fold_count"])
        or len(startup_rows) != int(bank["startup_fallback_row_count"])
        or len(cold_rows) != int(bank["adapted_origin_row_count"])
        or len(adapted_rows) != int(bank["adapted_origin_row_count"])
        or sum(bool(row["prescribed_issue"]) for row in adapted_rows)
        != int(bank["adapted_prescribed_issue_row_count"])
    ):
        raise ValueError("R8R6 outer evaluation coverage changed")
    startup = _startup_evaluation(startup_rows, ctx.cfg)
    tube, tube_derivation = innovation.context_robust_tube(adapted_rows, ctx.cfg)
    adapted_evaluation = observer.practical_evaluation(adapted_rows, tube, ctx.cfg)
    usefulness = innovation.usefulness(cold_rows, adapted_rows, ctx.cfg)
    tube_caps = np.asarray(ctx.cfg["tube_contract"]["component_caps_physical"], dtype=float)
    tube_cap_passed = bool(np.all(tube <= tube_caps[None, :] + 1e-15))
    observer_qualified = bool(
        startup["passed"]
        and adapted_evaluation["passed"]
        and tube_cap_passed
        and len(folds) == int(ctx.cfg["gates"]["required_outer_fold_count"])
    )
    adaptive = bool(observer_qualified and usefulness["passed"])
    if not observer_qualified:
        route = str(ctx.cfg["routes"]["observer_fail"])
    elif adaptive:
        route = str(ctx.cfg["routes"]["adaptive_pass"])
    else:
        route = str(ctx.cfg["routes"]["static_pass"])

    model_sha = tube_sha = innovation_sha = ""
    if observer_qualified:
        fitted = observer.fit_model(items, candidate, ctx.cfg)
        model_path = ctx.paths.model / "observer_model.json"
        tube_path = ctx.paths.model / "observer_tube.json"
        innovation_path = ctx.paths.model / "innovation_contract.json"
        _write(
            model_path,
            {
                "schema_version": 1,
                "stage": contract.STAGE,
                "campaign_identity": contract.IDENTITY,
                "feature_contract": ctx.cfg["feature_contract"],
                "training_pair_count": 20,
                "training_origin_row_count": 600,
                "fixed_candidate": candidate.as_dict(),
                "source_r8r5_state_sha256": ctx.cfg["source_r8r5_contract"][
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
                "derivation": "causal_adapted_context_robust_global_higher_quantile_scaled_v1",
                "tube_derivation": tube_derivation,
                "fixed_candidate": candidate.as_dict(),
            },
        )
        _write(
            innovation_path,
            {
                "schema_version": 1,
                "stage": contract.STAGE,
                "campaign_identity": contract.IDENTITY,
                "innovation_contract": ctx.cfg["innovation_contract"],
                "adaptation_enabled": adaptive,
                "fallback": "cold_observer_until_prior_one_step_prediction_is_observable",
                "selection_reason": (
                    "prospective_measurable_benefit_passed"
                    if adaptive
                    else "prospective_measurable_benefit_failed_use_static_observer"
                ),
            },
        )
        model_sha, tube_sha, innovation_sha = (
            _sha(model_path),
            _sha(tube_path),
            _sha(innovation_path),
        )

    detailed = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "phase": "twenty_fold_causal_one_step_innovation_observer",
        "source_signature": source_signature,
        "outer_fold_count": len(folds),
        "outer_folds": folds,
        "fixed_candidate": candidate.as_dict(),
        "innovation_contract": ctx.cfg["innovation_contract"],
        "startup_evaluation": startup,
        "cold_comparator_rows": cold_rows,
        "tube_derivation": tube_derivation,
        "tube_physical": tube.tolist(),
        "tube_cap_passed": tube_cap_passed,
        "adapted_evaluation": adapted_evaluation,
        "usefulness_evaluation": usefulness,
        "observer_qualification_passed": observer_qualified,
        "adaptation_usefulness_passed": bool(usefulness["passed"]),
        "observer_model_sha256": model_sha,
        "observer_tube_sha256": tube_sha,
        "innovation_contract_sha256": innovation_sha,
        "route": route,
        "scientific_gate_passed": observer_qualified,
        "zero_new_tsc": True,
        "new_raw_count": 0,
        "all_stage_trajectories_allowed_in_expert_dataset": False,
        "passed": True,
    }
    detailed_path = ctx.paths.analysis / "primary_detailed.json"
    _write(detailed_path, detailed)
    summary = {
        key: value
        for key, value in detailed.items()
        if key not in {"outer_folds", "cold_comparator_rows"}
    }
    summary["startup_evaluation"] = {
        key: value for key, value in startup.items() if key != "rows"
    }
    summary["adapted_evaluation"] = {
        key: value for key, value in adapted_evaluation.items() if key != "rows"
    }
    summary["primary_detailed_sha256"] = _sha(detailed_path)
    summary_path = ctx.paths.analysis / "primary_summary.json"
    _write(summary_path, summary)
    _set_state(
        ctx,
        phase_status="primary_complete",
        primary_summary_sha256=_sha(summary_path),
        observer_qualification_passed=observer_qualified,
        adaptation_usefulness_passed=bool(usefulness["passed"]),
        observer_model_sha256=model_sha,
        observer_tube_sha256=tube_sha,
        innovation_contract_sha256=innovation_sha,
        verdict={"route": route, "passed": observer_qualified},
    )
    return summary


def postprocess(ctx: Context) -> dict[str, Any]:
    state = _require(ctx, "primary_complete")
    primary_path = ctx.paths.analysis / "primary_summary.json"
    independent_path = ctx.paths.analysis / "independent.json"
    if not independent_path.is_file():
        raise ValueError("R8R6 independent audit missing")
    primary = _read(primary_path)
    independent = _read(independent_path)
    if (
        independent.get("passed") is not True
        or independent.get("primary_numerical_agreement") is not True
        or independent.get("primary_outcome_agreement") is not True
        or independent.get("artifact_hash_agreement") is not True
        or independent.get("primary_summary_sha256") != _sha(primary_path)
        or independent.get("route") != primary.get("route")
        or independent.get("observer_qualification_passed")
        is not bool(primary.get("observer_qualification_passed"))
        or independent.get("adaptation_usefulness_passed")
        is not bool(primary.get("adaptation_usefulness_passed"))
    ):
        raise ValueError("R8R6 independent disagreement")
    final = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "phase": "final_dual_audit",
        "route": primary["route"],
        "observer_qualification_passed": primary["observer_qualification_passed"],
        "adaptation_usefulness_passed": primary["adaptation_usefulness_passed"],
        "scientific_gate_passed": primary["scientific_gate_passed"],
        "observer_model_sha256": state["observer_model_sha256"],
        "observer_tube_sha256": state["observer_tube_sha256"],
        "innovation_contract_sha256": state["innovation_contract_sha256"],
        "primary_summary_sha256": _sha(primary_path),
        "independent_sha256": _sha(independent_path),
        "real_tsc_executed": False,
        "new_raw_count": 0,
        "source_trajectories_modified": False,
        "all_stage_trajectories_allowed_in_expert_dataset": False,
        "mpc_validated": False,
        "gate_a_qualified": False,
        "expert_data_allowed": False,
        "bc_dagger_or_rl_allowed": False,
        "passed": True,
    }
    final_path = ctx.paths.analysis / "final_report.json"
    _write(final_path, final)
    _set_state(
        ctx,
        phase_status="complete",
        finished=True,
        final_report_sha256=_sha(final_path),
        stop_reason=(
            ""
            if bool(primary["observer_qualification_passed"])
            else "causal_one_step_observer_point_or_tube_gate_failed"
        ),
    )
    return final


def execute(ctx: Context, command: str) -> dict[str, Any]:
    if command == "offline":
        return prepare_offline(ctx)
    if command == "primary":
        return evaluate_primary(ctx)
    if command == "postprocess":
        return postprocess(ctx)
    raise ValueError(f"unsupported R8R6 command: {command}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--r8r5-run", type=Path, required=True)
    parser.add_argument("--r8-run", type=Path, required=True)
    parser.add_argument("--r8r3-output", type=Path, required=True)
    parser.add_argument("--r8r4-run", type=Path, required=True)
    for name in (
        "source-d1r11-run", "source-r2-run", "source-r4-run", "source-r6-run",
        "source-s21-run", "source-s23r1-output", "source-s24-run",
        "source-d1r9-v1", "source-d1r9-v2", "source-d1r10-run",
        "source-d1r10-audit", "source-stage42r3b-run", "source-stage42r3c3-run",
        "source-stage42r3c3-bank-dir", "source-stage42r3c3t1-run",
        "source-stage42r3c3t1-audit-dir", "source-stage42r3c3t3-controller-bank",
        "q1-run", "q2-run", "q1-audit", "q2-audit", "r3b-server-audit",
        "r3b-snapshot-checks",
    ):
        parser.add_argument(f"--{name}", dest=name.replace("-", "_"), type=Path, required=True)
    parser.add_argument("--command", choices=("offline", "primary", "postprocess"), required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    ctx = load_context(args)
    result = execute(ctx, args.command)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
