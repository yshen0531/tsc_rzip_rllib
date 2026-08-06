#!/usr/bin/env python3
"""Primary zero-TSC causal online innovation/adaptation audit for R8R2."""

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
)
from tsc_rzip_rllib.control import causal_online_innovation_adapter as adapter
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification as r8,
    stage4_2r3c3t13s24d1r14r8r2_causal_online_innovation_adaptation as contract,
)


def _json(path: Path) -> Any:
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


def _file(path: Path, *, size: int, sha: str, label: str) -> None:
    if not path.is_file() or path.stat().st_size != size or _sha(path) != sha:
        raise ValueError(f"R8R2 {label} contract changed")


def _authenticate_r8r1(output: Path, cfg: Mapping[str, Any]) -> dict[str, Any]:
    source = cfg["source_r8r1_contract"]
    paths = {
        "primary_detailed": output / "primary_detailed.json",
        "primary_summary": output / "primary_summary.json",
        "independent": output / "independent.json",
        "state": output / "stage_state.json",
    }
    contract_keys = {
        "primary_detailed": "primary_detailed",
        "primary_summary": "primary_summary",
        "independent": "independent",
        "state": "stage_state",
    }
    for key, contract_key in contract_keys.items():
        _file(
            paths[key],
            size=int(source[f"{contract_key}_bytes"]),
            sha=str(source[f"{contract_key}_sha256"]),
            label=f"source R8R1 {key}",
        )
    primary = _json(paths["primary_detailed"])
    independent = _json(paths["independent"])
    state = _json(paths["state"])
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
        or independent.get("model_artifact_presence_agreement") is not True
        or state.get("route") != route
        or state.get("finished") is not True
        or state.get("independent_completed") is not True
        or int(state.get("new_raw_count", -1)) != int(source["required_new_raw_count"])
        or bool(state.get("heldout_outcomes_opened"))
        != bool(source["required_heldout_outcomes_opened"])
        or str(state.get("model_sha256") or "") != str(source["required_model_sha256"])
    ):
        raise ValueError("R8R2 source R8R1 outcome changed")
    return {key + "_sha256": _sha(path) for key, path in paths.items()}


def _new_r8_context(
    r8_cfg: Mapping[str, Any], r8_config: Path, r8_run: Path,
    source_r2_run: Path, source_r4_run: Path, source_r6_run: Path,
) -> r8.Context:
    return r8.Context(
        cfg=r8_cfg,
        config_path=r8_config,
        d1r11_ctx=None,
        source_d1r11_run=r8_run,
        source_response_runs={
            "r2": source_r2_run,
            "r4": source_r4_run,
            "r6": source_r6_run,
        },
        paths=r8._paths(r8_run),
    )


def _records(
    cfg: Mapping[str, Any], r8r1_cfg: Mapping[str, Any], r8_cfg: Mapping[str, Any],
    r8_config: Path, r8_run: Path, source_r2_run: Path,
    source_r4_run: Path, source_r6_run: Path,
    source_items: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    scales = np.asarray(cfg["bank_contract"]["response_scales"], dtype=float)
    source_runs = {"r2": source_r2_run, "r4": source_r4_run, "r6": source_r6_run}
    existing_sources = {
        name: r7_source._authenticate_source(path, r8_cfg["source_response_contracts"][name])
        for name, path in source_runs.items()
    }
    existing_groups = {
        "r2": r7_source._groups(existing_sources["r2"], "d1r14r2", 10),
        "r4": r7_source._groups(existing_sources["r4"], "d1r14r4", -1),
        "r6": r7_source._groups(existing_sources["r6"], "d1r14r6", -1),
    }
    existing_by_id: dict[str, tuple[Mapping[str, Any], Mapping[str, Any]]] = {}
    for source in existing_sources.values():
        specs = {str(spec["experiment_id"]): spec for spec in source["specs"]}
        existing_by_id.update(
            {experiment_id: (specs[experiment_id], result) for experiment_id, result in source["results"].items()}
        )

    r8_ctx = _new_r8_context(
        r8_cfg, r8_config, r8_run, source_r2_run, source_r4_run, source_r6_run
    )
    new_specs = r8._phase_specs(r8_ctx, "training")
    new_results = r8._phase_results(r8_ctx, "training")
    new_spec_by_id = {str(spec["experiment_id"]): spec for spec in new_specs}
    new_baselines: dict[str, tuple[Mapping[str, Any], Mapping[str, Any]]] = {}
    for spec in new_specs:
        if str(spec["d1r14r8_role"]) == "baseline":
            key = f"{spec['pair_id']}|{spec['history_member']}"
            if key in new_baselines:
                raise ValueError("R8R2 duplicate new baseline context")
            new_baselines[key] = (spec, new_results[str(spec["experiment_id"])])

    records = []
    windows: dict[tuple[str, int], dict[str, Any]] = {}
    response_exact = descriptor_equal = 0
    for source_item in source_items:
        item = dict(source_item)
        experiment_id = str(item["response_id"])
        context = str(item["context_id"])
        issue = int(item["issue_task_step"])
        if str(item["source_stage"]) == "R8":
            probe_spec = new_spec_by_id[experiment_id]
            probe_result = new_results[experiment_id]
            baseline_spec, baseline_result = new_baselines[context]
        else:
            probe_spec, probe_result = existing_by_id[experiment_id]
            baseline_source = "r2" if issue == 10 else "r4"
            baseline_spec, baseline_result = existing_groups[baseline_source][context][
                ("baseline", -1, -1, 0)
            ]
        probe_visible = r7_source._visible(probe_result["trajectory"], scales)
        baseline_visible = r7_source._visible(baseline_result["trajectory"], scales)
        target_offsets = (
            float(probe_spec["target_R_offset_m"]),
            float(probe_spec["target_Z_offset_m"]),
            float(probe_spec["target_Ip_offset_A"]),
        )
        descriptor = adapter.probe_descriptor(probe_visible, issue, target_offsets, cfg)
        expected_response = np.asarray(item["response"], dtype=float)
        reconstructed = probe_visible[issue + 1 :] - baseline_visible[issue + 1 :]
        if reconstructed.shape != expected_response.shape or not np.array_equal(reconstructed, expected_response):
            raise ValueError("R8R2 matched response raw reconstruction changed")
        response_exact += 1
        descriptor_equal += int(np.array_equal(descriptor, np.asarray(item["descriptor"], dtype=float)))
        item.update(
            {
                "descriptor": descriptor,
                "response": expected_response,
                "probe_visible": probe_visible,
                "baseline_visible": baseline_visible,
            }
        )
        records.append(item)
        window_key = (context, issue)
        candidate = {
            "context_id": context,
            "pair_id": str(item["pair_id"]),
            "history_member": str(item["history_member"]),
            "issue_task_step": issue,
            "baseline_visible": baseline_visible,
        }
        if window_key in windows:
            if not np.array_equal(windows[window_key]["baseline_visible"], baseline_visible):
                raise ValueError("R8R2 baseline window changed within context")
        else:
            windows[window_key] = candidate
    records.sort(key=lambda row: str(row["response_id"]))
    window_rows = [windows[key] for key in sorted(windows)]
    bank = cfg["bank_contract"]
    pairs = sorted({str(row["pair_id"]) for row in records})
    contexts = sorted({str(row["context_id"]) for row in records})
    if (
        len(records) != int(bank["response_count"])
        or len(pairs) != int(bank["pair_count"])
        or len(contexts) != int(bank["context_count"])
        or len(window_rows) != int(bank["baseline_window_count"])
        or any(sum(str(row["pair_id"]) == pair for row in records) != int(bank["responses_per_pair"]) for pair in pairs)
        or any(sum(str(row["context_id"]) == context for row in records) != int(bank["responses_per_context"]) for context in contexts)
        or any(len(row["response"]) < int(bank["minimum_response_length"]) for row in records)
    ):
        raise ValueError("R8R2 online record bank coverage changed")
    signature = {
        "response_count": len(records),
        "pair_count": len(pairs),
        "context_count": len(contexts),
        "baseline_window_count": len(window_rows),
        "raw_matched_response_exact_count": response_exact,
        "probe_descriptor_equal_to_prior_baseline_descriptor_count": descriptor_equal,
        "probe_descriptor_reconstructed_from_probe_count": len(records),
        "matched_baseline_used_as_predictor_input_count": 0,
        "future_probe_state_used_as_predictor_input_count": 0,
    }
    return records, window_rows, signature


def _compact_geometry(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "field": value["field"],
        "passed": value["passed"],
        "canonical": {key: item for key, item in value["canonical"].items() if key != "rows"},
        "operational": {key: item for key, item in value["operational"].items() if key != "rows"},
    }


def _compact_update(value: Mapping[str, Any]) -> dict[str, Any]:
    output = {key: item for key, item in value.items() if key not in {"rows", "cold_rows", "predicted_geometry", "actual_geometry"}}
    output["predicted_geometry"] = _compact_geometry(value["predicted_geometry"])
    output["actual_geometry"] = _compact_geometry(value["actual_geometry"])
    return output


def run(args: argparse.Namespace) -> dict[str, Any]:
    config_path = args.config.resolve()
    cfg = _json(config_path)
    contract.validate_config(cfg)
    root = Path(__file__).resolve().parents[1]
    design = (root / str(cfg["design_document"])).resolve()
    source_r8r1_config = (root / str(cfg["source_r8r1_config"])).resolve()
    if _sha(design) != str(cfg["design_document_sha256"]):
        raise ValueError("R8R2 design hash changed")
    if _sha(source_r8r1_config) != str(cfg["source_r8r1_config_sha256"]):
        raise ValueError("R8R2 source R8R1 config changed")
    r8r1_cfg = _json(source_r8r1_config)
    r8r1_source = _authenticate_r8r1(args.r8r1_output.resolve(), cfg)
    r8_config = (root / str(r8r1_cfg["source_r8_config"])).resolve()
    r8_cfg = _json(r8_config)
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError("R8R2 primary output directory must be empty")
    output.mkdir(parents=True, exist_ok=True)
    source_items, _, r8_authentication, _ = r8r1_primary._source_items(
        r8r1_cfg,
        source_r8r1_config,
        args.r8_run.resolve(),
        args.source_r2_run.resolve(),
        args.source_r4_run.resolve(),
        args.source_r6_run.resolve(),
    )
    records, windows, record_signature = _records(
        cfg,
        r8r1_cfg,
        r8_cfg,
        r8_config,
        args.r8_run.resolve(),
        args.source_r2_run.resolve(),
        args.source_r4_run.resolve(),
        args.source_r6_run.resolve(),
        source_items,
    )
    baseline = adapter.baseline_forecast_audit(windows, cfg)
    update_results: dict[int, dict[str, Any]] = {}
    folds: list[dict[str, Any]] = []
    if baseline["passed"]:
        adapted, cold, folds = adapter.nested_outer_predictions(records, cfg)
        update_results = {
            update: adapter.evaluate_update(adapted[update], cold[update], cfg)
            for update in map(int, cfg["innovation_contract"]["update_relative_lags"])
        }
    selected = adapter.select_update(update_results, cfg) if update_results else None
    route = contract.route_for(bool(baseline["passed"]), selected, cfg)
    detailed = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "campaign_identity": contract.IDENTITY,
        "audit_kind": "primary",
        "source_r8r1_authentication": r8r1_source,
        "source_r8_authentication": r8_authentication,
        "record_signature": record_signature,
        "baseline_forecast": baseline,
        "outer_folds": folds,
        "updates": {str(key): value for key, value in update_results.items()},
        "selected_update_relative_lag": selected,
        "route": route,
        "scientific_gate_passed": selected is not None,
        "forbidden_predictor_input_count": 0,
        "matched_baseline_predictor_input_count": 0,
        "new_raw_count": 0,
        "ray_executed": False,
        "gotsc_executed": False,
        "tsc_executed": False,
        "controller_executed": False,
        "plant_advance_count": 0,
        "development_artifact_sha256": "",
        "heldout_outcomes_opened": False,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "mpc_validated": False,
        "gate_a_qualified": False,
        "bc_dagger_or_rl_allowed": False,
        "passed": True,
    }
    detailed_path = output / "primary_detailed.json"
    _write(detailed_path, detailed)
    compact = {key: value for key, value in detailed.items() if key not in {"baseline_forecast", "updates", "outer_folds"}}
    compact["baseline_forecast"] = {key: value for key, value in baseline.items() if key != "rows"}
    compact["updates"] = {str(key): _compact_update(value) for key, value in update_results.items()}
    compact["outer_fold_count"] = len(folds)
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
            "scientific_gate_passed": selected is not None,
            "selected_update_relative_lag": selected,
            "route": route,
            "development_artifact_sha256": "",
            "new_raw_count": 0,
            "heldout_outcomes_opened": False,
        },
    )
    print(json.dumps(compact, indent=2, sort_keys=True, allow_nan=False))
    return compact


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--r8r1-output", type=Path, required=True)
    parser.add_argument("--r8-run", type=Path, required=True)
    parser.add_argument("--source-r2-run", type=Path, required=True)
    parser.add_argument("--source-r4-run", type=Path, required=True)
    parser.add_argument("--source-r6-run", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


if __name__ == "__main__":
    run(_parser().parse_args())
