#!/usr/bin/env python3
"""Primary zero-TSC action-conditioned full-history audit for D1R14R7R2."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from docs.codex.audit_tools import stage4_2r3c3t13s24d1r14r7_causal_response_model as source
from tsc_rzip_rllib.control import action_conditioned_history_response_model as model
from tsc_rzip_rllib.control import causal_response_model as metrics


STAGE = "Stage4.2R3c3T13S24D1R14R7R2"
IDENTITY = "action_conditioned_full_history_kernel_development_v1"
DESIGN_SHA256 = "32d0a5d123b70f9565cd27534e576eb63a6688bb0f6021755746b2f1e98dfdc5"


def _validate_config(cfg: Mapping[str, Any]) -> None:
    bank = cfg["bank_contract"]
    request = cfg["request_contract"]
    contract = cfg["model_contract"]
    gates = cfg["gates"]
    execution = cfg["execution_contract"]
    timing = cfg["formal_timing_contract"]
    scope = cfg["scientific_scope"]
    invalid = (
        cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("package_revision")
        != "r42r3c3t13s24d1r14r7r2_action_conditioned_full_history_kernel_v1"
        or cfg.get("design_document_sha256") != DESIGN_SHA256
        or tuple(map(int, bank["issue_task_steps"])) != (10, 14, 18, 22)
        or tuple(map(int, bank["history_offsets"])) != tuple(range(23))
        or tuple(map(float, bank["response_scales"]))
        != (0.03, 0.03, 0.1, 0.1, 10000.0)
        or tuple(map(float, bank["target_scales"])) != (0.03, 0.03, 10000.0)
        or float(bank["dt_s"]) != 0.01
        or int(bank["maximum_relative_lag"]) != 27
        or tuple(
            int(bank[key])
            for key in (
                "context_count",
                "pair_count",
                "histories_per_pair",
                "direction_count",
                "response_count",
            )
        )
        != (8, 4, 2, 4, 304)
        or bank["source_response_counts"] != {"R2": 64, "R4": 192, "R6": 48}
        or request["canonical_matrix_digest"]
        != "c8cd62c00c1f60b46312927789659657dc8cc35717533193433b0e398c1ec94c"
        or request["replacement_matrix_digest"]
        != "69528f0e204b51847c1d2a7df428555a557454e9fa6bc76768d39e7cc5a90da8"
        or np.asarray(request["canonical_matrix_columns"], dtype=float).shape != (4, 4)
        or np.asarray(request["replacement_matrix_columns"], dtype=float).shape != (4, 4)
        or float(request["canonical_scale"]) != 1.0
        or int(request["replacement_direction_index"]) != 0
        or float(request["replacement_scale"]) != 1.5
        or float(request["coordinate_absolute_tolerance"]) != 1e-15
        or tuple(map(int, contract["pca_ranks"])) != (4, 8, 12)
        or tuple(map(float, contract["rbf_median_distance_multipliers"]))
        != (0.5, 1.0, 2.0)
        or tuple(map(float, contract["kernel_ridges"])) != (1e-6, 1e-3, 1e-1)
        or float(contract["standard_deviation_floor"]) != 1e-12
        or float(contract["bandwidth_floor"]) != 1e-12
        or int(contract["tail_polynomial_degree"]) != 2
        or int(contract["tail_fit_point_count"]) != 8
        or tuple(map(int, contract["output_indices"])) != (2, 3, 4)
        or contract["outer_group_key"] != "pair_id"
        or not bool(contract["heads_use_only_action_sign_and_direction"])
        or not bool(contract["nested_whole_pair_selection"])
        or bool(contract["final_all_data_fit_is_validation"])
        or len(model.candidates(cfg)) != 27
        or tuple(
            float(gates[key])
            for key in (
                "maximum_relative_l2_error",
                "minimum_response_cosine",
                "minimum_peak_ratio",
                "maximum_peak_ratio",
                "maximum_absolute_scaled_point_error",
                "minimum_predicted_peak",
                "maximum_condition_number",
            )
        )
        != (0.75, 0.8, 0.5, 1.5, 0.1, 0.0025, 20.0)
        or tuple(map(float, gates["response_floor_physical"]))
        != (1e-9, 1e-9, 1e-7, 1e-7, 1e-4)
        or float(gates["tube_multiplier"]) != 2.0
        or tuple(map(float, gates["tube_caps_physical"]))
        != (0.003, 0.003, 0.01, 0.01, 1000.0)
        or float(gates["rank_relative_tolerance"]) != 1e-10
        or tuple(
            int(gates[key])
            for key in (
                "required_rank",
                "required_response_pass_count",
                "required_signal_pass_count",
                "required_canonical_branch_count",
                "required_operational_branch_count",
            )
        )
        != (4, 304, 304, 64, 64)
        or tuple(cfg["forbidden_predictor_fields"])
        != (
            "pair_id",
            "history_member",
            "prefix",
            "target_id",
            "regime_id",
            "delay_label",
            "slew_label",
            "source_result",
            "source_action",
            "source_coil_current",
            "source_wire_current",
            "current_coil_current",
            "current_wire_current",
            "hidden_wire_current",
            "future_measurement",
            "future_executed_action",
        )
        or int(execution["new_raw_count"]) != 0
        or int(execution["plant_steps_executed"]) != 0
        or any(
            bool(execution[key])
            for key in ("controller_executed", "ray_executed", "gotsc_executed", "tsc_executed")
        )
        or not bool(execution["source_raw_read_in_place"])
        or tuple(
            int(timing[key])
            for key in (
                "normal_arrival_deadline_step",
                "normal_hold_through_step",
                "weak_arrival_deadline_step",
                "weak_hold_through_step",
            )
        )
        != (25, 35, 27, 37)
        or bool(timing["arrival_deadline_expansion_allowed"])
        or bool(timing["evaluated_in_r7r2"])
        or not bool(scope["identification_development_only"])
        or any(
            bool(scope[key])
            for key in (
                "probe_trajectories_allowed_in_expert_dataset",
                "transition_response_model_validated_fresh",
                "mpc_validated",
                "expert_data_allowed",
                "bc_dagger_or_rl_allowed",
            )
        )
        or cfg["routes"]
        != {
            "source_fail": "ACTION_CONDITIONED_FULL_HISTORY_SOURCE_FAIL_NO_TSC",
            "model_fail": "ACTION_CONDITIONED_FULL_HISTORY_MODEL_FAIL_NEW_IDENTIFICATION_REQUIRED",
            "pass": "ACTION_CONDITIONED_FULL_HISTORY_MODEL_PASS_FRESH_MULTIPULSE_DESIGN_REQUIRED",
        }
    )
    if invalid:
        raise ValueError("R7R2 frozen configuration changed")


def _request_scale(
    spec: Mapping[str, Any], prefix: str, direction: int, sign: int, cfg: Mapping[str, Any]
) -> float:
    request = cfg["request_contract"]
    replacement = prefix == "d1r14r6"
    matrix_key = "replacement_matrix_columns" if replacement else "canonical_matrix_columns"
    digest_key = "replacement_matrix_digest" if replacement else "canonical_matrix_digest"
    matrix = np.asarray(request[matrix_key], dtype=float)
    expected = sign * matrix[:, direction]
    coordinate = np.asarray(spec[f"{prefix}_requested_coordinate"], dtype=float)
    tolerance = float(request["coordinate_absolute_tolerance"])
    if (
        int(spec[f"{prefix}_direction_index"]) != direction
        or int(spec[f"{prefix}_sign"]) != sign
        or spec[f"{prefix}_requested_matrix_digest"] != request[digest_key]
        or coordinate.shape != (4,)
        or float(np.max(np.abs(coordinate - expected))) > tolerance
    ):
        raise ValueError("R7R2 requested coordinate changed")
    canonical = np.asarray(request["canonical_matrix_columns"], dtype=float)[:, direction]
    scale = float(np.linalg.norm(matrix[:, direction]) / np.linalg.norm(canonical))
    expected_scale = (
        float(request["replacement_scale"]) if replacement else float(request["canonical_scale"])
    )
    if replacement and direction != int(request["replacement_direction_index"]):
        raise ValueError("R7R2 replacement direction changed")
    if abs(scale - expected_scale) > 1e-12:
        raise ValueError("R7R2 request scale changed")
    return expected_scale


def build_items(
    sources: Mapping[str, Mapping[str, Any]], cfg: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    scales = np.asarray(cfg["bank_contract"]["response_scales"], dtype=float)
    target_scales = np.asarray(cfg["bank_contract"]["target_scales"], dtype=float)
    offsets = tuple(map(int, cfg["bank_contract"]["history_offsets"]))
    r2 = source._groups(sources["r2"], "d1r14r2", 10)
    r4 = source._groups(sources["r4"], "d1r14r4", -1)
    r6 = source._groups(sources["r6"], "d1r14r6", -1)
    contexts = sorted(r2)
    if contexts != sorted(r4) or contexts != sorted(r6) or len(contexts) != 8:
        raise ValueError("R7R2 context closure changed")
    items: list[dict[str, Any]] = []
    for context in contexts:
        for issue in (10, 14, 18, 22):
            baseline_group = r2[context] if issue == 10 else r4[context]
            baseline_spec, baseline_result = baseline_group[("baseline", -1, -1, 0)]
            baseline_visible = source._visible(baseline_result["trajectory"], scales)
            history = baseline_visible[[max(0, issue - offset) for offset in offsets]].reshape(-1)
            availability = np.asarray([float(offset <= issue) for offset in offsets])
            target = np.asarray(
                [
                    baseline_spec["target_R_offset_m"],
                    baseline_spec["target_Z_offset_m"],
                    baseline_spec["target_Ip_offset_A"],
                ],
                dtype=float,
            ) / target_scales
            descriptor = np.concatenate((history, availability, target, [(issue - 10.0) / 12.0]))
            if len(descriptor) != 142:
                raise ValueError("R7R2 causal descriptor dimension changed")
            for sign in (-1, 1):
                for direction in range(4):
                    if issue == 10:
                        canonical_spec, canonical_result = r2[context][
                            ("signed_probe", issue, direction, sign)
                        ]
                        canonical_prefix, canonical_stage = "d1r14r2", "R2"
                    else:
                        canonical_spec, canonical_result = r4[context][
                            ("signed_probe", issue, direction, sign)
                        ]
                        canonical_prefix, canonical_stage = "d1r14r4", "R4"
                    member = source._visible(canonical_result["trajectory"], scales)[issue + 1 :]
                    baseline = baseline_visible[issue + 1 :]
                    if member.shape != baseline.shape:
                        raise ValueError("R7R2 canonical response shape changed")
                    roles = ["canonical"]
                    if issue == 10 or direction != 0:
                        roles.append("operational")
                    items.append(
                        {
                            "response_id": str(canonical_spec["experiment_id"]),
                            "source_stage": canonical_stage,
                            "context_id": context,
                            "pair_id": str(canonical_spec["pair_id"]),
                            "history_member": str(canonical_spec["history_member"]),
                            "issue_task_step": issue,
                            "sign": sign,
                            "direction_index": direction,
                            "action_scale": _request_scale(
                                canonical_spec, canonical_prefix, direction, sign, cfg
                            ),
                            "geometry_roles": roles,
                            "descriptor": descriptor.tolist(),
                            "response": (member - baseline).tolist(),
                        }
                    )
                    if issue > 10 and direction == 0:
                        replacement_spec, replacement_result = r6[context][
                            ("signed_probe", issue, direction, sign)
                        ]
                        replacement = source._visible(replacement_result["trajectory"], scales)[
                            issue + 1 :
                        ]
                        if replacement.shape != baseline.shape:
                            raise ValueError("R7R2 replacement response shape changed")
                        items.append(
                            {
                                "response_id": str(replacement_spec["experiment_id"]),
                                "source_stage": "R6",
                                "context_id": context,
                                "pair_id": str(replacement_spec["pair_id"]),
                                "history_member": str(replacement_spec["history_member"]),
                                "issue_task_step": issue,
                                "sign": sign,
                                "direction_index": direction,
                                "action_scale": _request_scale(
                                    replacement_spec, "d1r14r6", direction, sign, cfg
                                ),
                                "geometry_roles": ["operational"],
                                "descriptor": descriptor.tolist(),
                                "response": (replacement - baseline).tolist(),
                            }
                        )
    items.sort(key=lambda row: row["response_id"])
    pairs = sorted({str(item["pair_id"]) for item in items})
    histories = {
        pair: sorted(
            {str(item["history_member"]) for item in items if item["pair_id"] == pair}
        )
        for pair in pairs
    }
    counts = {
        name: sum(item["source_stage"] == name for item in items)
        for name in ("R2", "R4", "R6")
    }
    signature = {
        "response_count": len(items),
        "context_count": len(contexts),
        "pair_count": len(pairs),
        "pairs": pairs,
        "histories_by_pair": histories,
        "source_counts": counts,
        "descriptor_dimension": 142,
        "canonical_geometry_item_count": sum(
            "canonical" in item["geometry_roles"] for item in items
        ),
        "operational_geometry_item_count": sum(
            "operational" in item["geometry_roles"] for item in items
        ),
        "bank_digest": metrics.canonical_digest(items),
    }
    if (
        len(items) != 304
        or len(pairs) != 4
        or any(value != ["minus_first", "plus_first"] for value in histories.values())
        or counts != {"R2": 64, "R4": 192, "R6": 48}
        or signature["canonical_geometry_item_count"] != 256
        or signature["operational_geometry_item_count"] != 256
    ):
        raise ValueError("R7R2 response bank contract changed")
    return items, signature


def _write(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    cfg = source._json(args.config.resolve())
    _validate_config(cfg)
    if source._sha256(args.design_document.resolve()) != cfg["design_document_sha256"]:
        raise ValueError("R7R2 design hash changed")
    if args.output.exists():
        raise ValueError("R7R2 output directory must be new")
    runs = {
        "r2": args.source_r2_run.resolve(),
        "r4": args.source_r4_run.resolve(),
        "r6": args.source_r6_run.resolve(),
    }
    sources = {
        name: source._authenticate_source(path, cfg["source_contracts"][name])
        for name, path in runs.items()
    }
    items, bank = build_items(sources, cfg)
    rows, folds = model.nested_outer_rows(items, cfg)
    aggregate = metrics.aggregate(rows, cfg)
    geometry = model.geometry(rows, cfg)
    passed = bool(aggregate["passed"] and geometry["passed"])
    final_candidate, final_scores = model.select_candidate(items, cfg)
    artifact = model.serializable_model(model.fit_model(items, final_candidate, cfg)) if passed else None
    model_digest = metrics.canonical_digest(artifact) if artifact is not None else None
    route = cfg["routes"]["pass" if passed else "model_fail"]
    detailed = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "passed": passed,
        "route": route,
        "source_authentication_passed": True,
        "source_inventories": {name: value["inventory"] for name, value in sources.items()},
        "bank": bank,
        "nested_outer_folds": folds,
        "outer_prediction_rows": rows,
        "aggregate": aggregate,
        "predicted_geometry": geometry,
        "final_candidate_development_only": final_candidate.as_dict(),
        "final_candidate_scores": final_scores,
        "final_model_digest": model_digest,
        "execution": {
            "new_raw_count": 0,
            "plant_steps_executed": 0,
            "controller_executed": False,
            "ray_executed": False,
            "gotsc_executed": False,
            "tsc_executed": False,
        },
        "scientific_scope": cfg["scientific_scope"],
    }
    summary_geometry = {
        "response_count": geometry["response_count"],
        "signal_pass_count": geometry["signal_pass_count"],
        "minimum_predicted_peak": geometry["minimum_predicted_peak"],
        "canonical": {key: value for key, value in geometry["canonical"].items() if key != "rows"},
        "operational": {
            key: value for key, value in geometry["operational"].items() if key != "rows"
        },
        "passed": geometry["passed"],
    }
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "passed": passed,
        "route": route,
        "bank": bank,
        "aggregate": aggregate,
        "predicted_geometry": summary_geometry,
        "outer_selected_candidates": [
            {"held_pair_id": row["held_pair_id"], "selected_candidate": row["selected_candidate"]}
            for row in folds
        ],
        "final_candidate_development_only": final_candidate.as_dict(),
        "final_model_digest": model_digest,
        "new_raw_count": 0,
        "tsc_executed": False,
    }
    args.output.mkdir(parents=True)
    detailed_path = args.output / "stage4_2r3c3t13s24d1r14r7r2_detailed_v1.json"
    summary_path = args.output / "stage4_2r3c3t13s24d1r14r7r2_summary_v1.json"
    _write(detailed_path, detailed)
    _write(summary_path, summary)
    model_path = args.output / "stage4_2r3c3t13s24d1r14r7r2_model_v1.json"
    if artifact is not None:
        _write(model_path, artifact)
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "package_revision": cfg["package_revision"],
        "config_sha256": source._sha256(args.config.resolve()),
        "design_document_sha256": source._sha256(args.design_document.resolve()),
        "detailed_sha256": source._sha256(detailed_path),
        "summary_sha256": source._sha256(summary_path),
        "model_sha256": source._sha256(model_path) if artifact is not None else None,
        "source_runs": {name: str(path) for name, path in runs.items()},
    }
    _write(args.output / "stage4_2r3c3t13s24d1r14r7r2_manifest_v1.json", manifest)
    print(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False))
    return detailed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--design-document", type=Path, required=True)
    parser.add_argument("--source-r2-run", type=Path, required=True)
    parser.add_argument("--source-r4-run", type=Path, required=True)
    parser.add_argument("--source-r6-run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


if __name__ == "__main__":
    run(_parser().parse_args())
