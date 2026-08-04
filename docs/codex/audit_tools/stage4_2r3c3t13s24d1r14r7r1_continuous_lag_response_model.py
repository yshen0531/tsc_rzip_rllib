#!/usr/bin/env python3
"""Primary zero-TSC continuous-lag response-model audit for D1R14R7R1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from docs.codex.audit_tools import stage4_2r3c3t13s24d1r14r7_causal_response_model as source
from tsc_rzip_rllib.control import causal_response_model as metrics
from tsc_rzip_rllib.control import continuous_lag_response_model as model


STAGE = "Stage4.2R3c3T13S24D1R14R7R1"
IDENTITY = "continuous_lag_causal_response_model_development_v1"


def _validate_config(cfg: Mapping[str, Any]) -> None:
    bank = cfg["bank_contract"]
    contract = cfg["model_contract"]
    gates = cfg["gates"]
    execution = cfg["execution_contract"]
    timing = cfg["formal_timing_contract"]
    scope = cfg["scientific_scope"]
    invalid = (
        cfg.get("stage") != STAGE or cfg.get("identity") != IDENTITY
        or cfg.get("package_revision") != "r42r3c3t13s24d1r14r7r1_continuous_lag_response_model_v1"
        or cfg.get("design_document_sha256") != "959decfbdebda3e41d793cb85ddbee1a2d0919a8b88a126dad422536054d9e4b"
        or tuple(map(int, bank["issue_task_steps"])) != (10, 14, 18, 22)
        or tuple(map(float, bank["response_scales"])) != (0.03, 0.03, 0.1, 0.1, 10000.0)
        or tuple(map(float, bank["target_scales"])) != (0.03, 0.03, 10000.0)
        or tuple(map(int, bank["descriptor_state_offsets"])) != (0, 1, 2, 4, 8)
        or float(bank["dt_s"]) != 0.01
        or int(bank["maximum_relative_lag"]) != 27 or int(bank["response_count"]) != 256
        or tuple(int(bank[key]) for key in ("context_count", "pair_count", "histories_per_pair", "direction_count")) != (8, 4, 2, 4)
        or tuple(map(int, contract["pca_ranks"])) != (2, 4, 6)
        or tuple(map(int, contract["temporal_legendre_degrees"])) != (2, 3, 5)
        or tuple(map(float, contract["ridges"])) != (1e-6, 1e-3, 1e-1)
        or float(contract["standard_deviation_floor"]) != 1e-12
        or tuple(map(int, contract["output_indices"])) != (2, 3, 4)
        or contract["outer_group_key"] != "pair_id"
        or not bool(contract["heads_use_only_action_sign_and_direction"])
        or not bool(contract["nested_whole_pair_selection"]) or bool(contract["final_all_data_fit_is_validation"])
        or len(model.candidates(cfg)) != 27
        or tuple(float(gates[key]) for key in ("maximum_relative_l2_error", "minimum_response_cosine", "minimum_peak_ratio", "maximum_peak_ratio", "maximum_absolute_scaled_point_error", "minimum_predicted_peak", "maximum_condition_number")) != (0.75, 0.8, 0.5, 1.5, 0.1, 0.0025, 20.0)
        or tuple(map(float, gates["response_floor_physical"])) != (1e-9, 1e-9, 1e-7, 1e-7, 1e-4)
        or float(gates["tube_multiplier"]) != 2.0
        or tuple(map(float, gates["tube_caps_physical"])) != (0.003, 0.003, 0.01, 0.01, 1000.0)
        or float(gates["rank_relative_tolerance"]) != 1e-10
        or tuple(int(gates[key]) for key in ("required_rank", "required_response_pass_count", "required_branch_pass_count")) != (4, 256, 64)
        or tuple(cfg["forbidden_predictor_fields"]) != ("pair_id", "history_member", "prefix", "target_id", "regime_id", "source_result", "matched_future_baseline", "source_action", "source_coil_current", "source_wire_current", "hidden_wire_current", "future_measurement", "future_executed_action")
        or int(execution["new_raw_count"]) != 0 or int(execution["plant_steps_executed"]) != 0
        or any(bool(execution[key]) for key in ("controller_executed", "ray_executed", "gotsc_executed", "tsc_executed"))
        or not bool(execution["source_raw_read_in_place"])
        or tuple(int(timing[key]) for key in ("normal_arrival_deadline_step", "normal_hold_through_step", "weak_arrival_deadline_step", "weak_hold_through_step")) != (25, 35, 27, 37)
        or bool(timing["arrival_deadline_expansion_allowed"]) or bool(timing["evaluated_in_r7r1"])
        or not bool(scope["identification_development_only"])
        or any(bool(scope[key]) for key in ("probe_trajectories_allowed_in_expert_dataset", "transition_response_model_validated_fresh", "mpc_validated", "expert_data_allowed", "bc_dagger_or_rl_allowed"))
        or cfg["routes"] != {
            "source_fail": "CONTINUOUS_LAG_RESPONSE_MODEL_SOURCE_FAIL_NO_TSC",
            "model_fail": "CONTINUOUS_LAG_RESPONSE_MODEL_DEVELOPMENT_FAIL_BROADER_DECONFOUNDED_IDENTIFICATION_REQUIRED",
            "pass": "CONTINUOUS_LAG_RESPONSE_MODEL_DEVELOPMENT_PASS_FRESH_MULTIPULSE_VALIDATION_DESIGN_REQUIRED",
        }
    )
    if invalid:
        raise ValueError("R7R1 frozen configuration changed")


def _write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    cfg = source._json(args.config.resolve())
    _validate_config(cfg)
    if source._sha256(args.design_document.resolve()) != cfg["design_document_sha256"]:
        raise ValueError("R7R1 design hash changed")
    if args.output.exists():
        raise ValueError("R7R1 output directory must be new")
    runs = {"r2": args.source_r2_run.resolve(), "r4": args.source_r4_run.resolve(), "r6": args.source_r6_run.resolve()}
    sources = {name: source._authenticate_source(path, cfg["source_contracts"][name]) for name, path in runs.items()}
    items, bank = source.build_items(sources, cfg)
    rows, folds = model.nested_outer_rows(items, cfg)
    aggregate = metrics.aggregate(rows, cfg)
    geometry = metrics.geometry(rows, cfg)
    passed = bool(aggregate["passed"] and geometry["passed"])
    final_candidate, final_scores = model.select_candidate(items, cfg)
    artifact = model.serializable_model(model.fit_model(items, final_candidate, cfg)) if passed else None
    model_digest = metrics.canonical_digest(artifact) if artifact is not None else None
    route = cfg["routes"]["pass" if passed else "model_fail"]
    detailed = {
        "schema_version": 1, "stage": STAGE, "identity": IDENTITY, "passed": passed, "route": route,
        "source_authentication_passed": True, "source_inventories": {name: value["inventory"] for name, value in sources.items()},
        "bank": bank, "nested_outer_folds": folds, "outer_prediction_rows": rows,
        "aggregate": aggregate, "predicted_geometry": geometry,
        "final_candidate_development_only": final_candidate.as_dict(), "final_candidate_scores": final_scores,
        "final_model_digest": model_digest,
        "execution": {"new_raw_count": 0, "plant_steps_executed": 0, "controller_executed": False, "ray_executed": False, "gotsc_executed": False, "tsc_executed": False},
        "scientific_scope": cfg["scientific_scope"],
    }
    summary = {
        "schema_version": 1, "stage": STAGE, "passed": passed, "route": route, "bank": bank, "aggregate": aggregate,
        "predicted_geometry": {key: value for key, value in geometry.items() if key != "rows"},
        "outer_selected_candidates": [{"held_pair_id": row["held_pair_id"], "selected_candidate": row["selected_candidate"]} for row in folds],
        "final_candidate_development_only": final_candidate.as_dict(), "final_model_digest": model_digest,
        "new_raw_count": 0, "tsc_executed": False,
    }
    args.output.mkdir(parents=True)
    detailed_path = args.output / "stage4_2r3c3t13s24d1r14r7r1_detailed_v1.json"
    summary_path = args.output / "stage4_2r3c3t13s24d1r14r7r1_summary_v1.json"
    _write(detailed_path, detailed); _write(summary_path, summary)
    if artifact is not None:
        _write(args.output / "stage4_2r3c3t13s24d1r14r7r1_model_v1.json", artifact)
    manifest = {"schema_version": 1, "stage": STAGE, "package_revision": cfg["package_revision"], "config_sha256": source._sha256(args.config.resolve()), "design_document_sha256": source._sha256(args.design_document.resolve()), "detailed_sha256": source._sha256(detailed_path), "summary_sha256": source._sha256(summary_path), "model_sha256": source._sha256(args.output / "stage4_2r3c3t13s24d1r14r7r1_model_v1.json") if artifact is not None else None, "source_runs": {name: str(path) for name, path in runs.items()}}
    _write(args.output / "stage4_2r3c3t13s24d1r14r7r1_manifest_v1.json", manifest)
    print(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False))
    return detailed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True); parser.add_argument("--design-document", type=Path, required=True)
    parser.add_argument("--source-r2-run", type=Path, required=True); parser.add_argument("--source-r4-run", type=Path, required=True); parser.add_argument("--source-r6-run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


if __name__ == "__main__":
    run(_parser().parse_args())
