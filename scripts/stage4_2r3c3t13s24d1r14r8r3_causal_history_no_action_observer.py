#!/usr/bin/env python3
"""Primary zero-TSC causal history no-action observer audit for R8R3."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r7_causal_response_model as r7_source,
)
from scripts import (
    stage4_2r3c3t13s24d1r14r8r1_fixed_candidate_short_horizon_discriminator as r8r1_primary,
    stage4_2r3c3t13s24d1r14r8r2_causal_online_innovation_adaptation as r8r2_primary,
)
from tsc_rzip_rllib.control import causal_history_no_action_observer as observer
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification as r8,
    stage4_2r3c3t13s24d1r14r8r3_causal_history_no_action_observer as contract,
)


def _json(path: Path) -> Any:
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


def _file(path: Path, *, size: int, sha: str, label: str) -> None:
    if not path.is_file() or path.stat().st_size != size or _sha(path) != sha:
        raise ValueError(f"R8R3 {label} contract changed")


def _authenticate_r8r2(output: Path, cfg: Mapping[str, Any]) -> dict[str, Any]:
    source = cfg["source_r8r2_contract"]
    paths = {
        "primary_detailed": output / "primary_detailed.json",
        "primary_summary": output / "primary_summary.json",
        "independent": output / "independent.json",
        "stage_state": output / "stage_state.json",
    }
    for key, path in paths.items():
        _file(
            path,
            size=int(source[f"{key}_bytes"]),
            sha=str(source[f"{key}_sha256"]),
            label=f"source R8R2 {key}",
        )
    primary = _json(paths["primary_detailed"])
    independent = _json(paths["independent"])
    state = _json(paths["stage_state"])
    route = str(source["required_route"])
    if (
        primary.get("route") != route
        or primary.get("passed") is not True
        or primary.get("scientific_gate_passed") is not False
        or independent.get("route") != route
        or independent.get("passed") is not True
        or independent.get("scientific_gate_passed") is not False
        or independent.get("primary_numerical_agreement") is not True
        or independent.get("primary_outcome_agreement") is not True
        or state.get("route") != route
        or state.get("finished") is not True
        or state.get("independent_completed") is not True
        or bool(state.get("scientific_gate_passed"))
        or int(state.get("new_raw_count", -1)) != 0
        or bool(state.get("heldout_outcomes_opened"))
        or str(state.get("development_artifact_sha256") or "")
    ):
        raise ValueError("R8R3 source R8R2 outcome changed")
    return {key + "_sha256": _sha(path) for key, path in paths.items()}


def _actions(result: Mapping[str, Any]) -> np.ndarray:
    value = np.asarray(
        [row.get("action_norm_tsc", []) for row in result.get("controller_trace") or []],
        dtype=float,
    )
    if value.ndim != 2 or value.shape[1] != 14 or not np.all(np.isfinite(value)):
        raise ValueError("R8R3 action history invalid")
    return value


def _currents(result: Mapping[str, Any]) -> np.ndarray:
    value = np.asarray(
        [row.get("currents_a_tsc", []) for row in result.get("trajectory") or []],
        dtype=float,
    )
    if value.ndim != 2 or value.shape[1] != 14 or not np.all(np.isfinite(value)):
        raise ValueError("R8R3 applied-current history invalid")
    return value


def _target(spec: Mapping[str, Any]) -> tuple[float, float, float]:
    return (
        float(spec["target_R_offset_m"]),
        float(spec["target_Z_offset_m"]),
        float(spec["target_Ip_offset_A"]),
    )


def _baseline_sources(
    r8_cfg: Mapping[str, Any],
    r8_config: Path,
    r8_run: Path,
    r2_run: Path,
    r4_run: Path,
    r6_run: Path,
) -> tuple[
    dict[str, tuple[Mapping[str, Any], Mapping[str, Any]]],
    dict[str, tuple[Mapping[str, Any], Mapping[str, Any]]],
    dict[str, tuple[Mapping[str, Any], Mapping[str, Any]]],
    dict[str, tuple[Mapping[str, Any], Mapping[str, Any]]],
    dict[str, tuple[Mapping[str, Any], Mapping[str, Any]]],
]:
    source_runs = {"r2": r2_run, "r4": r4_run, "r6": r6_run}
    existing = {
        name: r7_source._authenticate_source(path, r8_cfg["source_response_contracts"][name])
        for name, path in source_runs.items()
    }
    groups = {
        "r2": r7_source._groups(existing["r2"], "d1r14r2", 10),
        "r4": r7_source._groups(existing["r4"], "d1r14r4", -1),
    }
    existing_by_id: dict[str, tuple[Mapping[str, Any], Mapping[str, Any]]] = {}
    for source in existing.values():
        specs = {str(spec["experiment_id"]): spec for spec in source["specs"]}
        existing_by_id.update(
            {
                experiment_id: (specs[experiment_id], result)
                for experiment_id, result in source["results"].items()
            }
        )
    r8_ctx = r8r2_primary._new_r8_context(
        r8_cfg, r8_config, r8_run, r2_run, r4_run, r6_run
    )
    new_specs = r8._phase_specs(r8_ctx, "training")
    new_results = r8._phase_results(r8_ctx, "training")
    new_by_id = {
        str(spec["experiment_id"]): (spec, new_results[str(spec["experiment_id"])])
        for spec in new_specs
    }
    new_baselines: dict[str, tuple[Mapping[str, Any], Mapping[str, Any]]] = {}
    for spec in new_specs:
        if str(spec["d1r14r8_role"]) == "baseline":
            context = f"{spec['pair_id']}|{spec['history_member']}"
            if context in new_baselines:
                raise ValueError("R8R3 duplicate R8 baseline")
            new_baselines[context] = (spec, new_results[str(spec["experiment_id"])])
    r2_baselines = {
        context: members[("baseline", -1, -1, 0)] for context, members in groups["r2"].items()
    }
    r4_baselines = {
        context: members[("baseline", -1, -1, 0)] for context, members in groups["r4"].items()
    }
    return new_baselines, r2_baselines, r4_baselines, new_by_id, existing_by_id


def _build_rows_and_probe_audit(
    cfg: Mapping[str, Any],
    r8r2_cfg: Mapping[str, Any],
    r8r1_cfg: Mapping[str, Any],
    r8_cfg: Mapping[str, Any],
    r8_config: Path,
    r8_run: Path,
    r2_run: Path,
    r4_run: Path,
    r6_run: Path,
    source_items: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records, windows, r8r2_signature = r8r2_primary._records(
        r8r2_cfg,
        r8r1_cfg,
        r8_cfg,
        r8_config,
        r8_run,
        r2_run,
        r4_run,
        r6_run,
        source_items,
    )
    new_baselines, r2_baselines, r4_baselines, new_by_id, existing_by_id = _baseline_sources(
        r8_cfg, r8_config, r8_run, r2_run, r4_run, r6_run
    )
    context_meta = {
        str(row["context_id"]): (str(row["pair_id"]), str(row["history_member"]))
        for row in records
    }
    prescribed = set(map(int, cfg["bank_contract"]["prescribed_issue_task_steps"]))
    scales = np.asarray(cfg["bank_contract"]["visible_scales"], dtype=float)
    r8r2_windows = {
        (str(row["context_id"]), int(row["issue_task_step"])): np.asarray(
            row["baseline_visible"], dtype=float
        )
        for row in windows
    }
    rows: list[dict[str, Any]] = []
    selected_results: dict[str, Mapping[str, Any]] = {}
    prescribed_exact = 0
    for context in sorted(context_meta):
        pair, history = context_meta[context]
        if context in new_baselines:
            selectors = {10: new_baselines[context], 11: new_baselines[context]}
        else:
            selectors = {10: r2_baselines[context], 11: r4_baselines[context]}
        later_visible = r7_source._visible(selectors[11][1]["trajectory"], scales)
        maximum_origin = len(later_visible) - 1 - int(cfg["bank_contract"]["future_state_count"])
        for origin in range(int(cfg["bank_contract"]["first_origin_task_step"]), maximum_origin + 1):
            spec, result = selectors[10 if origin == 10 else 11]
            trajectory = result.get("trajectory") or []
            visible = r7_source._visible(trajectory, scales)
            actions = _actions(result)
            currents = _currents(result)
            feature = observer.causal_feature(
                visible[: origin + 1],
                actions[:origin],
                currents[: origin + 1],
                _target(spec),
                origin,
                cfg,
            )
            future = visible[origin + 1 : origin + 13]
            delta = observer.target_delta(visible, origin, cfg)
            if origin in prescribed:
                expected = r8r2_windows[(context, origin)]
                if not np.array_equal(visible, expected):
                    raise ValueError("R8R3 prescribed baseline differs from R8R2")
                prescribed_exact += 1
            experiment_id = str(result["experiment_id"])
            selected_results[experiment_id] = result
            rows.append(
                {
                    "row_id": f"{context}|origin{origin:02d}",
                    "context_id": context,
                    "pair_id": pair,
                    "history_member": history,
                    "origin_task_step": origin,
                    "prescribed_issue": origin in prescribed,
                    "source_baseline_experiment_id": experiment_id,
                    "feature": feature,
                    "origin_visible": visible[origin],
                    "target_delta": delta,
                    "future_visible": future,
                }
            )
    zero_action = constant_current = 0
    for result in selected_results.values():
        actions = _actions(result)
        currents = _currents(result)
        if np.array_equal(actions[10:], np.zeros_like(actions[10:])):
            zero_action += 1
        if np.array_equal(np.diff(currents[10:], axis=0), np.zeros_like(np.diff(currents[10:], axis=0))):
            constant_current += 1
    row_by_context_origin = {
        (str(row["context_id"]), int(row["origin_task_step"])): row for row in rows
    }
    probe_equal = 0
    for record in records:
        experiment_id = str(record["response_id"])
        if str(record["source_stage"]) == "R8":
            spec, result = new_by_id[experiment_id]
        else:
            spec, result = existing_by_id[experiment_id]
        issue = int(record["issue_task_step"])
        trajectory = result.get("trajectory") or []
        visible = r7_source._visible(trajectory[: issue + 1], scales)
        feature = observer.causal_feature(
            visible,
            _actions(result)[:issue],
            _currents(result)[: issue + 1],
            _target(spec),
            issue,
            cfg,
        )
        baseline_feature = np.asarray(
            row_by_context_origin[(str(record["context_id"]), issue)]["feature"], dtype=float
        )
        probe_equal += int(np.array_equal(feature, baseline_feature))
    pairs = sorted({str(row["pair_id"]) for row in rows})
    contexts = sorted({str(row["context_id"]) for row in rows})
    lengths = sorted({len(np.asarray(row["future_visible"])) for row in rows})
    bank = cfg["bank_contract"]
    if (
        len(rows) != int(bank["origin_row_count"])
        or len(pairs) != int(bank["pair_count"])
        or len(contexts) != int(bank["context_count"])
        or sum(bool(row["prescribed_issue"]) for row in rows)
        != int(bank["prescribed_issue_row_count"])
        or prescribed_exact != int(bank["prescribed_issue_row_count"])
        or probe_equal != int(bank["probe_feature_count"])
        or len(selected_results) != 32
        or zero_action != 32
        or constant_current != 32
        or lengths != [12]
    ):
        raise ValueError("R8R3 causal row or source coverage changed")
    signature = {
        "pair_count": len(pairs),
        "context_count": len(contexts),
        "origin_row_count": len(rows),
        "prescribed_issue_row_count": sum(bool(row["prescribed_issue"]) for row in rows),
        "prescribed_baseline_exact_count": prescribed_exact,
        "selected_baseline_raw_count": len(selected_results),
        "zero_future_action_baseline_count": zero_action,
        "constant_future_current_baseline_count": constant_current,
        "probe_feature_count": len(records),
        "probe_feature_equal_count": probe_equal,
        "feature_dimension": len(rows[0]["feature"]),
        "forbidden_predictor_input_count": 0,
        "matched_baseline_future_predictor_input_count": 0,
        "future_probe_state_predictor_input_count": 0,
        "r8r2_record_signature": r8r2_signature,
    }
    return sorted(rows, key=lambda row: row["row_id"]), signature


def _compact_outer(value: Mapping[str, Any]) -> dict[str, Any]:
    return dict(value)


def run(args: argparse.Namespace) -> dict[str, Any]:
    config_path = args.config.resolve()
    cfg = _json(config_path)
    contract.validate_config(cfg)
    root = Path(__file__).resolve().parents[1]
    design = (root / str(cfg["design_document"])).resolve()
    source_r8r2_config = (root / str(cfg["source_r8r2_config"])).resolve()
    if _sha(design) != str(cfg["design_document_sha256"]):
        raise ValueError("R8R3 design hash changed")
    if _sha(source_r8r2_config) != str(cfg["source_r8r2_config_sha256"]):
        raise ValueError("R8R3 source R8R2 config changed")
    source_r8r2 = _authenticate_r8r2(args.r8r2_output.resolve(), cfg)
    r8r2_cfg = _json(source_r8r2_config)
    source_r8r1_config = (root / str(r8r2_cfg["source_r8r1_config"])).resolve()
    r8r1_cfg = _json(source_r8r1_config)
    r8_config = (root / str(r8r1_cfg["source_r8_config"])).resolve()
    r8_cfg = _json(r8_config)
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError("R8R3 primary output directory must be empty")
    output.mkdir(parents=True, exist_ok=True)
    source_items, _, r8_authentication, _ = r8r1_primary._source_items(
        r8r1_cfg,
        source_r8r1_config,
        args.r8_run.resolve(),
        args.source_r2_run.resolve(),
        args.source_r4_run.resolve(),
        args.source_r6_run.resolve(),
    )
    rows, signature = _build_rows_and_probe_audit(
        cfg,
        r8r2_cfg,
        r8r1_cfg,
        r8_cfg,
        r8_config,
        args.r8_run.resolve(),
        args.source_r2_run.resolve(),
        args.source_r4_run.resolve(),
        args.source_r6_run.resolve(),
        source_items,
    )
    outer_rows, folds = observer.nested_outer_predictions(rows, cfg)
    evaluation = observer.evaluate_outer(outer_rows, folds, cfg)
    scientific = bool(evaluation["passed"])
    artifact_sha = ""
    all_development_selection: dict[str, Any] = {}
    if scientific:
        selected, scores, cv_rows = observer.select_candidate(rows, cfg)
        tube = observer.tube_from_rows(cv_rows, cfg)
        model = observer.fit_model(rows, selected, cfg)
        artifact = {
            "schema_version": 1,
            "stage": contract.STAGE,
            "campaign_identity": contract.IDENTITY,
            "feature_contract": cfg["feature_contract"],
            "bank_contract": cfg["bank_contract"],
            "source_r8r2_authentication": source_r8r2,
            "model": observer.serializable_model(model, tube),
        }
        artifact_path = output / "observer_model.json"
        _write(artifact_path, artifact)
        artifact_sha = _sha(artifact_path)
        all_development_selection = {
            "selected_candidate": selected.as_dict(),
            "candidate_scores": scores,
            "tube_physical": tube.tolist(),
            "artifact_sha256": artifact_sha,
        }
    route = contract.route_for(scientific, cfg)
    detailed = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "campaign_identity": contract.IDENTITY,
        "audit_kind": "primary",
        "source_r8r2_authentication": source_r8r2,
        "source_r8_authentication": r8_authentication,
        "record_signature": signature,
        "outer_evaluation": evaluation,
        "outer_folds": folds,
        "outer_rows": outer_rows,
        "all_development_selection": all_development_selection,
        "route": route,
        "scientific_gate_passed": scientific,
        "forbidden_predictor_input_count": 0,
        "matched_baseline_future_predictor_input_count": 0,
        "future_probe_state_predictor_input_count": 0,
        "new_raw_count": 0,
        "ray_executed": False,
        "gotsc_executed": False,
        "tsc_executed": False,
        "controller_executed": False,
        "plant_advance_count": 0,
        "development_artifact_sha256": artifact_sha,
        "heldout_outcomes_opened": False,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "mpc_validated": False,
        "gate_a_qualified": False,
        "bc_dagger_or_rl_allowed": False,
        "passed": True,
    }
    detailed_path = output / "primary_detailed.json"
    _write(detailed_path, detailed)
    compact = {
        key: value
        for key, value in detailed.items()
        if key not in {"outer_folds", "outer_rows", "all_development_selection"}
    }
    compact["outer_fold_selections"] = [
        {
            "held_pair_id": fold["held_pair_id"],
            "selected_candidate": fold["selected_candidate"],
            "tube_cap_passed": fold["tube_cap_passed"],
            "held_tube_contained_count": fold["held_tube_contained_count"],
            "held_origin_row_count": fold["held_origin_row_count"],
            "passed": fold["passed"],
        }
        for fold in folds
    ]
    compact["all_development_selected_candidate"] = all_development_selection.get(
        "selected_candidate"
    )
    compact["primary_detailed_sha256"] = _sha(detailed_path)
    _write(output / "primary_summary.json", compact)
    _write(
        output / "stage_state.json",
        {
            "schema_version": 1,
            "stage": contract.STAGE,
            "finished": True,
            "primary_completed": True,
            "independent_completed": False,
            "scientific_gate_passed": scientific,
            "route": route,
            "development_artifact_sha256": artifact_sha,
            "new_raw_count": 0,
            "heldout_outcomes_opened": False,
        },
    )
    print(json.dumps(compact, indent=2, sort_keys=True, allow_nan=False))
    return compact


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--r8r2-output", type=Path, required=True)
    parser.add_argument("--r8-run", type=Path, required=True)
    parser.add_argument("--source-r2-run", type=Path, required=True)
    parser.add_argument("--source-r4-run", type=Path, required=True)
    parser.add_argument("--source-r6-run", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


if __name__ == "__main__":
    run(_parser().parse_args())
