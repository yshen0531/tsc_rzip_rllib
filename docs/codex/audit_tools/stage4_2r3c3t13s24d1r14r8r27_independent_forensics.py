#!/usr/bin/env python3
"""Structurally independent zero-TSC audit for frozen R8R27."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r26_independent_forensics as ind26,
)


ind25 = ind26.ind25
ind24 = ind26.ind24
ind23 = ind26.ind23
STAGE = "Stage4.2R3c3T13S24D1R14R8R27"
IDENTITY = "point_versus_reserve_authority_discriminator_v1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r27_point_versus_reserve_authority_discriminator"
LAYERS = ("point_only", "pair_tube", "combined_tube")


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


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
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _validate_config(cfg: Mapping[str, Any]) -> None:
    root = _root().resolve()
    design = (root / str(cfg["design_document"])).resolve()
    source = (root / str(cfg["source_r8r26_config"])).resolve()
    layer = cfg["layer_contract"]
    search = cfg["unchanged_search_contract"]
    formal = cfg["formal_contract"]
    gate = cfg["classification_gate"]
    if (
        int(cfg.get("schema_version", -1)) != 1
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("run_name") != RUN_NAME
        or not design.is_relative_to(root)
        or not source.is_relative_to(root)
        or _sha(design) != str(cfg["design_document_sha256"])
        or _sha(source) != str(cfg["source_r8r26_config_sha256"])
        or tuple(map(str, layer["ordered_layers"])) != LAYERS
        or layer.get("point_only_tube") != "exact_zero_with_source_interval_shapes"
        or layer.get("pair_tube_source") != "immutable_r8r25_all_eight_outer_jackknife_planning_tube"
        or layer.get("combined_tube_source") != "final_r8r26_componentwise_pair_schedule_maximum"
        or layer.get("pair_combined_elementwise_equality_required") is not True
        or layer.get("combined_r8r26_plan_reproduction_required") is not True
        or any(layer.get(key) is not False for key in (
            "tube_refit_allowed", "tube_rescale_allowed", "tube_clipping_allowed",
            "outcome_selected_tube_allowed",
        ))
        or tuple(map(int, search["decision_task_steps"])) != (10, 14, 18, 22)
        or tuple(map(int, (
            search["lattice_denominator"], search["maximum_coordinate_sum_units"],
            search["lattice_level_count"], search["coarse_level_count"],
            search["beam_width"], search["terminal_seed_count"],
            search["maximum_sweeps_per_step"],
        ))) != (16, 24, 325, 33, 256, 32, 16)
        or tuple(map(int, search["refinement_step_units"])) != (2, 1)
        or tuple(tuple(map(int, row)) for row in search["refinement_directions"])
        != ((1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1))
        or search.get("global_optimality_claimed") is not False
        or search.get("failed_plan_deployment_allowed") is not False
        or tuple(map(int, (
            formal["normal_arrival_deadline_step"], formal["normal_hold_through_step"],
            formal["weak_arrival_deadline_step"], formal["weak_hold_through_step"],
            formal["arrival_streak_steps"],
        ))) != (25, 35, 27, 37, 3)
        or tuple(map(float, (
            formal["position_tolerance_m"], formal["speed_tolerance_m_per_s"],
            formal["ip_tolerance_A"],
        ))) != (0.03, 0.1, 10000.0)
        or formal.get("arrival_deadline_expansion_allowed") is not False
        or tuple(map(int, (
            gate["required_safe_search_context_count_per_layer"],
            gate["minimum_point_only_repaired_failed_baseline_count_for_uncertainty_route"],
            gate["minimum_point_only_oracle_count_for_uncertainty_route"],
        ))) != (16, 1, 7)
        or float(gate["primary_independent_absolute_tolerance"]) != 1e-12
        or cfg.get("routes") != {
            "evidence_fail": "R8R27_INTEGRITY_FAIL_STOP",
            "uncertainty": "POINT_AUTHORITY_PRESENT_RESERVED_UNCERTAINTY_EXCITATION_REDESIGN_REQUIRED",
            "action_timing": "POINT_ACTION_TIMING_AUTHORITY_INSUFFICIENT_BROADER_CONTROLLER_REDESIGN_REQUIRED",
        }
        or cfg.get("zero_new_tsc") is not True
        or cfg.get("expert_data_allowed") is not False
        or cfg.get("gate_a_qualified") is not False
    ):
        raise ValueError("independent R8R27 frozen contract changed")


def _source_cfg(cfg: Mapping[str, Any]) -> Mapping[str, Any]:
    return _read((_root() / str(cfg["source_r8r26_config"])).resolve())


def _source_stage(args: argparse.Namespace, cfg: Mapping[str, Any]) -> Path:
    return args.r8r26_run.expanduser().resolve() / str(cfg["source_r8r26"]["stage_directory"])


def _plan_summaries(plans: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for plan in plans:
        selected = plan["selected_plan"]
        selected_summary = None
        if selected is not None:
            selected_summary = {
                key: selected[key]
                for key in (
                    "q_units", "q_values", "robust_formal_pass",
                    "worst_formal_margin_violation", "integrated_normalized_error",
                    "cumulative_normalized_action_movement",
                    "maximum_predicted_current_utilization",
                )
            }
            selected_summary["predicted_states_digest"] = _digest(selected["predicted_states"])
            selected_summary["reserved_tubes_digest"] = _digest(selected["reserved_tubes"])
        row = {
            key: plan[key]
            for key in (
                "pair_id", "history_member", "coarse_level_count", "beam_counts",
                "terminal_seed_count", "safe_search_complete", "robust_formal_plan_found",
                "causal_selected_mode", "search_counts", "evaluated_sequence_digest",
                "baseline_formal_pass_for_postselection_scoring",
                "hybrid_predicted_formal_pass",
            )
        }
        row["selected_plan"] = selected_summary
        output.append(row)
    return output


def _authenticate(args: argparse.Namespace, cfg: Mapping[str, Any]) -> dict[str, Any]:
    stage, expected = _source_stage(args, cfg), cfg["source_r8r26"]
    paths = {
        "primary_detailed": stage / "analysis/primary_detailed.json",
        "primary_summary": stage / "analysis/primary_summary.json",
        "independent": stage / "analysis/independent.json",
        "final_report": stage / "analysis/final_report.json",
        "model_evidence": stage / "model/preflight_evidence.json",
        "stage_manifest": stage / "stage_manifest.json",
        "stage_state": stage / "stage_state.json",
        "compact_audit": stage / "analysis/compact_audit.json",
    }
    hashes = {name: _sha(path) for name, path in paths.items()}
    if any(hashes[name] != str(expected[f"{name}_sha256"]) for name in paths):
        raise ValueError("independent R8R27 R8R26 source hash changed")
    primary = _read(paths["primary_detailed"])
    independent = _read(paths["independent"])
    final = _read(paths["final_report"])
    state = _read(paths["stage_state"])
    compact = _read(paths["compact_audit"])
    if (
        stage.parent.name != str(expected["run_name"])
        or primary.get("route") != str(expected["required_route"])
        or primary.get("model_gate_passed") is not True
        or primary.get("predicted_feasibility_gate_passed") is not False
        or independent.get("passed") is not True
        or final.get("primary_independent_agreement") is not True
        or final.get("passed") is not False
        or state.get("finished") is not True
        or compact.get("passed") is not True
        or compact.get("scientific_gate_passed") is not False
        or _digest(compact["plan_summaries"]) != str(expected["plan_summary_digest"])
        or _digest(compact["transition_hull_evidence"])
        != str(expected["transition_hull_evidence_digest"])
        or _digest(compact["coarse_level_units"]) != str(expected["coarse_level_digest"])
        or _digest([row["evaluated_sequence_digest"] for row in compact["plan_summaries"]])
        != str(expected["evaluated_token_digest_list_digest"])
    ):
        raise ValueError("independent R8R27 R8R26 source outcome changed")
    cfg26 = _source_cfg(cfg)
    transitive = ind26._authenticate(args, cfg26)
    if transitive.get("passed") is not True:
        raise ValueError("independent R8R27 transitive authentication failed")
    return {"hashes": hashes, "route": str(final["route"]), "transitive": transitive, "passed": True}


def _planning_inputs(args: argparse.Namespace, cfg: Mapping[str, Any]) -> tuple[Any, ...]:
    cfg26 = _source_cfg(cfg)
    cfg25 = ind26._source_cfg(cfg26)
    cfg24 = ind25._source_config(cfg25)
    r23_cfg = ind24._source_config(cfg24)
    bank = ind23._build_bank(args, r23_cfg)
    bank_evidence = ind23._bank_evidence(bank)
    expected = cfg["source_r8r26"]
    schedules = sorted({str(row["schedule_id"]) for row in bank})
    if (
        bank_evidence["feature_digest"] != str(expected["feature_digest"])
        or bank_evidence["target_digest"] != str(expected["target_digest"])
        or len(schedules) != int(expected["schedule_count"])
    ):
        raise ValueError("independent R8R27 bank changed")
    pairs = tuple(sorted({str(row["pair_id"]) for row in bank}))
    model = ind23._fit(bank, pairs, float(cfg26["model_contract"]["ridge_penalty"]))
    source_evidence = _read(_source_stage(args, cfg) / "model/preflight_evidence.json")
    pair = [np.asarray(value, dtype=float) for value in source_evidence["pair_tube"]]
    combined = [np.asarray(value, dtype=float) for value in source_evidence["combined_tube"]]
    zero = [np.zeros_like(value) for value in combined]
    equality = max(float(np.max(np.abs(left - right))) for left, right in zip(pair, combined))
    if (
        _digest(ind23._serial(model)) != str(expected["planning_model_digest"])
        or _digest([value.tolist() for value in pair]) != str(expected["pair_tube_digest"])
        or _digest([value.tolist() for value in combined]) != str(expected["combined_tube_digest"])
        or equality != 0.0
    ):
        raise ValueError("independent R8R27 model/tube changed")
    support = ind26._planning_support(bank, cfg25)
    hulls = ind26._transition_hulls(bank, cfg26)
    hull_evidence = [
        {
            "interval": int(hull["interval"]),
            "observed_transition_count": int(hull["observed_transition_count"]),
            "affine_rank": int(hull["affine_rank"]),
            "singular_values": np.asarray(hull["singular_values"]).tolist(),
            "transition_digest": str(hull["digest"]),
            "hull_equation_digest": _digest(np.asarray(hull["equations"]).tolist()),
        }
        for hull in hulls
    ]
    _, r22_cfg, _ = ind24._planning_metadata(args, r23_cfg)
    coarse = [list(value) for value in ind26._coarse_units(r22_cfg, cfg26)]
    if (
        _digest(hull_evidence) != str(expected["transition_hull_evidence_digest"])
        or _digest(coarse) != str(expected["coarse_level_digest"])
    ):
        raise ValueError("independent R8R27 hull/coarse changed")
    return cfg26, cfg25, r23_cfg, bank, bank_evidence, schedules, model, zero, pair, combined, support, hulls, hull_evidence


def _point_authority_present(point: Mapping[str, Any], cfg: Mapping[str, Any]) -> bool:
    gate = cfg["classification_gate"]
    return bool(
        int(point["predicted_repaired_failed_baseline_count"])
        >= int(gate["minimum_point_only_repaired_failed_baseline_count_for_uncertainty_route"])
        and int(point["predicted_baseline_fallback_plus_plan_oracle_count"])
        >= int(gate["minimum_point_only_oracle_count_for_uncertainty_route"])
    )


def audit(args: argparse.Namespace, cfg: Mapping[str, Any]) -> dict[str, Any]:
    _validate_config(cfg)
    authentication = _authenticate(args, cfg)
    (
        cfg26, cfg25, r23_cfg, bank, bank_evidence, schedules, model, zero, pair,
        combined, support, hulls, hull_evidence,
    ) = _planning_inputs(args, cfg)
    tubes = {"point_only": zero, "pair_tube": pair, "combined_tube": combined}
    results = {
        layer: ind26._planning(
            args, cfg26, cfg25, r23_cfg, model, tubes[layer], support, hulls
        )
        for layer in LAYERS
    }
    source_primary = _read(_source_stage(args, cfg) / "analysis/primary_detailed.json")
    combined_difference = ind23._maximum_difference(
        source_primary["planning_evaluation"], results["combined_tube"]
    )
    pair_combined_difference = ind23._maximum_difference(
        results["pair_tube"], results["combined_tube"]
    )
    gate = cfg["classification_gate"]
    safe = all(
        int(results[layer]["safe_search_context_count"])
        == int(gate["required_safe_search_context_count_per_layer"])
        for layer in LAYERS
    )
    reproduction = bool(combined_difference <= 1e-12 and pair_combined_difference <= 1e-12)
    if not (safe and reproduction):
        raise ValueError("independent R8R27 source search reproduction failed")
    point = results["point_only"]
    uncertainty = _point_authority_present(point, cfg)
    route = str(cfg["routes"]["uncertainty" if uncertainty else "action_timing"])

    stage = args.run_dir.expanduser().resolve() / RUN_NAME
    primary_path = stage / "analysis/primary_detailed.json"
    summary_path = stage / "analysis/primary_summary.json"
    evidence_path = stage / "model/discriminator_evidence.json"
    primary, summary = _read(primary_path), _read(summary_path)
    tolerance = float(gate["primary_independent_absolute_tolerance"])
    model_tube = {
        "planning_model_digest": _digest(ind23._serial(model)),
        "layer_tube_digests": {
            layer: _digest([value.tolist() for value in tubes[layer]]) for layer in LAYERS
        },
        "pair_combined_elementwise_maximum_absolute_difference": max(
            float(np.max(np.abs(left - right))) for left, right in zip(pair, combined)
        ),
    }
    primary_model_tube = {
        key: primary[key]
        for key in (
            "planning_model_digest", "layer_tube_digests",
            "pair_combined_elementwise_maximum_absolute_difference",
        )
    }
    bank_agreement = bool(
        primary["bank_evidence"]["feature_digest"] == bank_evidence["feature_digest"]
        and primary["bank_evidence"]["target_digest"] == bank_evidence["target_digest"]
        and primary["bank_evidence"]["schedule_ids"] == schedules
    )
    model_tube_difference = ind23._maximum_difference(primary_model_tube, model_tube)
    hull_difference = ind23._maximum_difference(primary["transition_hull_evidence"], hull_evidence)
    plan_difference = ind23._maximum_difference(primary["layer_results"], results)
    reproduction_difference = max(
        abs(float(primary["maximum_combined_source_plan_absolute_difference"]) - combined_difference),
        abs(float(primary["maximum_pair_combined_plan_absolute_difference"]) - pair_combined_difference),
    )
    result = {
        "schema_version": 1,
        "stage": STAGE,
        "audit_kind": "point_versus_reserve_authority_discriminator_independent",
        "source_authentication": authentication,
        "bank_evidence": {**bank_evidence, "schedule_count": len(schedules), "schedule_ids": schedules},
        **model_tube,
        "transition_hull_evidence": hull_evidence,
        "layer_results": results,
        "maximum_combined_source_plan_absolute_difference": combined_difference,
        "maximum_pair_combined_plan_absolute_difference": pair_combined_difference,
        "all_layer_safe_search_gate_passed": safe,
        "source_reproduction_gate_passed": reproduction,
        "classification_completed": True,
        "point_authority_present": uncertainty,
        "route": route,
        "maximum_model_tube_absolute_difference": model_tube_difference,
        "maximum_hull_absolute_difference": hull_difference,
        "maximum_layer_plan_absolute_difference": plan_difference,
        "maximum_reproduction_absolute_difference": reproduction_difference,
        "primary_bank_agreement": bank_agreement,
        "primary_model_tube_agreement": model_tube_difference <= tolerance,
        "primary_hull_agreement": hull_difference <= tolerance,
        "primary_layer_plan_agreement": plan_difference <= tolerance,
        "primary_reproduction_agreement": reproduction_difference <= tolerance,
        "primary_route_agreement": primary.get("route") == route and summary.get("route") == route,
        "primary_outcome_agreement": bool(
            primary.get("point_authority_present") is uncertainty
            and primary.get("classification_completed") is True
        ),
        "primary_detailed_sha256": _sha(primary_path),
        "primary_summary_sha256": _sha(summary_path),
        "primary_evidence_sha256": _sha(evidence_path),
        "fresh_controller_sentinel_authorized": False,
        "real_tsc_executed": False,
        "plant_step_count": 0,
        "new_raw_count": 0,
        "gate_a_qualified": False,
    }
    result["passed"] = all(bool(result[key]) for key in (
        "primary_bank_agreement", "primary_model_tube_agreement",
        "primary_hull_agreement", "primary_layer_plan_agreement",
        "primary_reproduction_agreement", "primary_route_agreement",
        "primary_outcome_agreement",
    ))
    if not result["passed"]:
        raise ValueError("independent R8R27 audit disagrees with primary")
    _write(stage / "analysis/independent.json", result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--r8r26-run", type=Path, required=True)
    parser.add_argument("--r8r25-run", type=Path, required=True)
    parser.add_argument("--r8r24-run", type=Path, required=True)
    parser.add_argument("--r8r23-run", type=Path, required=True)
    for name in (
        "r8r22-run", "r8r7-run", "r8r12-run", "r8r14-run", "r8r15-run",
        "r8r19-run", "r8r20-run", "r8-run", "r8r1-output", "r8r6-run",
        "source-d1r11-run", "source-r2-run", "source-r4-run", "source-r6-run",
        "source-s21-run", "source-s23r1-output", "source-s24-run",
        "source-d1r9-v1", "source-d1r9-v2", "source-d1r10-run",
        "source-d1r10-audit", "source-stage42r3b-run", "source-stage42r3c3-run",
        "source-stage42r3c3-bank-dir", "source-stage42r3c3t1-run",
        "source-stage42r3c3t1-audit-dir", "source-stage42r3c3t3-controller-bank",
        "q1-run", "q2-run", "q1-audit", "q2-audit", "r3b-server-audit",
        "r3b-snapshot-checks",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    cfg = _read(args.config.expanduser().resolve())
    result = audit(args, cfg)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
