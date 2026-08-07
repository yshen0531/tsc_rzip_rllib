#!/usr/bin/env python3
"""Read-only R8R9 measured multipulse authority and R8R8 score audit."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_campaign as r8r7,
)


STAGE = "Stage4.2R3c3T13S24D1R14R8R9"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r9_measured_multipulse_authority_audit"
IDENTITY = "measured_multipulse_authority_audit_v1"


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def _read_gz(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(
            stream,
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


def _inventory(path: Path) -> dict[str, Any]:
    rows = []
    digest = hashlib.sha256()
    for item in sorted(path.glob("*.json.gz"), key=lambda value: value.name):
        size = item.stat().st_size
        sha = _sha(item)
        digest.update(f"{item.name}\0{size}\0{sha}\n".encode())
        rows.append({"name": item.name, "size": size, "sha256": sha})
    return {
        "count": len(rows),
        "bytes": sum(int(row["size"]) for row in rows),
        "digest": digest.hexdigest(),
    }


def validate_config(cfg: Mapping[str, Any], *, project_root: Path) -> None:
    design = project_root / str(cfg["design_document"])
    formal = cfg["formal_contract"]
    known = cfg["known_aggregate_contract"]
    gate = cfg["scientific_gate"]
    execution = cfg["execution_contract"]
    scope = cfg["scientific_scope"]
    if (
        int(cfg.get("schema_version", -1)) != 1
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or not design.is_file()
        or _sha(design) != str(cfg["design_document_sha256"])
        or int(formal["normal_arrival_deadline_step"]) != 25
        or int(formal["normal_hold_through_step"]) != 35
        or int(formal["weak_arrival_deadline_step"]) != 27
        or int(formal["weak_hold_through_step"]) != 37
        or float(formal["position_tolerance_m"]) != 0.03
        or float(formal["speed_tolerance_m_per_s"]) != 0.1
        or float(formal["ip_tolerance_A"]) != 10000.0
        or int(formal["arrival_streak_steps"]) != 3
        or float(formal["metric_equivalence_absolute_tolerance"]) != 1e-12
        or bool(formal["arrival_deadline_expansion_allowed"])
        or tuple(map(int, (
            known["context_count"],
            known["baseline_trajectory_count"],
            known["multipulse_trajectory_count"],
            known["schedules_per_context"],
            known["baseline_formal_pass_count"],
            known["multipulse_formal_pass_count"],
            known["r8r8_forecast_count"],
            known["r8r8_decision_count"],
            known["r8r8_nonzero_selection_count"],
        ))) != (16, 16, 32, 2, 6, 12, 576, 64, 0)
        or int(gate["failed_baseline_count"]) != 10
        or int(gate["minimum_repaired_failed_baseline_count"]) != 1
        or int(gate["minimum_measured_oracle_formal_pass_count"]) != 7
        or int(execution["new_raw_count"]) != 0
        or any(bool(execution[key]) for key in (
            "ray_executed", "gotsc_executed", "tsc_executed", "controller_executed"
        ))
        or int(execution["plant_steps_executed"]) != 0
        or not bool(execution["read_raw_in_place"])
        or not bool(execution["server_virtualenv_only"])
        or not bool(execution["direct_copy_only"])
        or bool(execution["local_archive_operations_allowed"])
        or bool(scope["measured_oracle_is_causal_selector"])
        or bool(scope["real_mpc_executed"])
        or bool(scope["gate_a_qualified"])
        or bool(scope["all_source_trajectories_allowed_in_expert_dataset"])
        or bool(scope["expert_data_allowed"])
        or bool(scope["bc_dagger_or_rl_allowed"])
        or bool(scope["global_plant_reachability_claimed"])
    ):
        raise ValueError("R8R9 frozen design changed")


def _expected_files(stage: Path, source: Mapping[str, Any]) -> dict[str, Path]:
    return {
        "all_specs": stage / "specs/all_specs.json",
        "baseline_specs": stage / "specs/baseline_specs.json",
        "multipulse_specs": stage / "specs/multipulse_specs.json",
        "baseline_raw_primary": stage / "analysis/baseline_raw_primary.json",
        "baseline_raw_independent": stage / "analysis/baseline_raw_independent.json",
        "multipulse_raw_primary": stage / "analysis/multipulse_raw_primary.json",
        "multipulse_raw_independent": stage / "analysis/multipulse_raw_independent.json",
        "final_report": stage / "analysis/final_report.json",
        "stage_manifest": stage / "stage_manifest.json",
        "stage_state": stage / "stage_state.json",
    }


def _authenticate_r8r7(stage: Path, cfg: Mapping[str, Any]) -> dict[str, Any]:
    source = cfg["source_r8r7"]
    paths = _expected_files(stage, source)
    hashes = {name: _sha(path) for name, path in paths.items()}
    for name, actual in hashes.items():
        if actual != str(source[f"{name}_sha256"]):
            raise ValueError(f"R8R9 R8R7 {name} hash changed")
    final = _read(paths["final_report"])
    state = _read(paths["stage_state"])
    if (
        final.get("route") != source["required_route"]
        or final.get("scientific_gate_passed") is not True
        or final.get("passed") is not True
        or state.get("phase_status") != "complete"
        or state.get("verdict", {}).get("route") != source["required_route"]
        or state.get("verdict", {}).get("passed") is not True
    ):
        raise ValueError("R8R9 R8R7 final result changed")
    inventories = {}
    for phase in ("baseline", "multipulse"):
        value = _inventory(stage / "raw" / phase)
        if (
            value["count"] != int(source[f"{phase}_raw_count"])
            or value["bytes"] != int(source[f"{phase}_raw_bytes"])
            or value["digest"] != str(source[f"{phase}_raw_digest"])
        ):
            raise ValueError(f"R8R9 R8R7 {phase} raw changed")
        inventories[phase] = value
    return {"hashes": hashes, "raw_inventories": inventories, "passed": True}


def _authenticate_r8r8(stage: Path, cfg: Mapping[str, Any]) -> dict[str, Any]:
    source = cfg["source_r8r8"]
    paths = {
        "offline_primary_detailed": stage / "analysis/offline_primary_detailed.json",
        "offline_primary_summary": stage / "analysis/offline_primary_summary.json",
        "offline_independent": stage / "analysis/offline_independent.json",
        "stage_manifest": stage / "stage_manifest.json",
        "stage_state": stage / "stage_state.json",
    }
    hashes = {name: _sha(path) for name, path in paths.items()}
    for name, actual in hashes.items():
        if actual != str(source[f"{name}_sha256"]):
            raise ValueError(f"R8R9 R8R8 {name} hash changed")
    summary = _read(paths["offline_primary_summary"])
    independent = _read(paths["offline_independent"])
    state = _read(paths["stage_state"])
    raw_count = len(list((stage / "raw").rglob("*.json.gz"))) if (stage / "raw").exists() else 0
    if (
        summary.get("route") != source["required_route"]
        or summary.get("passed") is not False
        or int(summary.get("nonzero_selection_count", -1))
        != int(source["required_nonzero_selection_count"])
        or summary.get("real_tsc_executed") is not False
        or int(summary.get("new_raw_count", -1)) != int(source["required_new_raw_count"])
        or independent.get("audit_agreement_passed") is not True
        or independent.get("scientific_gate_passed") is not False
        or independent.get("primary_route_agreement") is not True
        or independent.get("route") != source["required_route"]
        or state.get("phase_status") != "offline_primary_failed"
        or state.get("verdict", {}).get("route") != source["required_route"]
        or state.get("verdict", {}).get("passed") is not False
        or state.get("real_tsc_executed") is not False
        or int(state.get("new_raw_count", -1)) != int(source["required_new_raw_count"])
        or raw_count != 0
    ):
        raise ValueError("R8R9 R8R8 zero-TSC result changed")
    return {"hashes": hashes, "raw_count": raw_count, "passed": True}


def _r8r7_context(args: argparse.Namespace, cfg: Mapping[str, Any]) -> r8r7.Context:
    r8r8_cfg = _read(_root() / str(cfg["source_r8r8"]["config_path"]))
    source_args = argparse.Namespace(**vars(args))
    source_args.config = (_root() / str(r8r8_cfg["source_r8r7_config"])).resolve()
    source_args.run_dir = args.r8r7_run.expanduser().resolve()
    return r8r7.load_context(source_args)


def _formal_rows(
    source_ctx: r8r7.Context,
    source_stage: Path,
    specs: Sequence[Mapping[str, Any]],
    tolerance: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    evaluators, _ = r8r7.r8.d1r11._formal_callback(source_ctx.r8_ctx.d1r11_ctx, specs)
    rows = []
    maximum_difference = 0.0
    pass_agreement = arrival_agreement = True
    for spec in specs:
        experiment_id = str(spec["experiment_id"])
        partition = str(spec["partition"])
        result = _read_gz(source_stage / "raw" / partition / f"{experiment_id}.json.gz")
        trajectory = result.get("trajectory") or []
        if (
            result.get("success") is not True
            or len(trajectory) != int(spec["horizon_steps"]) + 1
        ):
            raise ValueError(f"R8R9 incomplete source trajectory: {experiment_id}")
        rzi = np.asarray([[item["R"], item["Z"], item["Ip"]] for item in trajectory], dtype=float)
        if not np.all(np.isfinite(rzi)):
            raise ValueError(f"R8R9 non-finite source trajectory: {experiment_id}")
        evaluator = evaluators[experiment_id]
        compact = evaluator.evaluate(rzi)
        existing = evaluator.exact_existing_metric(result, rzi)
        pass_agreement = bool(
            pass_agreement
            and compact["formal_contract_pass"] == existing["formal_contract_pass"]
        )
        arrival_agreement = bool(
            arrival_agreement
            and int(compact["formal_best_arrival_ms"])
            == int(existing["formal_best_arrival_ms"])
        )
        for key in ("formal_minimum_signed_margin", "formal_mean_signed_margin"):
            maximum_difference = max(
                maximum_difference, abs(float(compact[key]) - float(existing[key]))
            )
        rows.append(
            {
                "experiment_id": experiment_id,
                "partition": partition,
                "pair_id": str(spec["pair_id"]),
                "history_member": str(spec["history_member"]),
                "schedule_index": int(spec.get("r8r7_schedule_index", -1)),
                "formal_contract_pass": bool(compact["formal_contract_pass"]),
                "formal_minimum_signed_margin": float(compact["formal_minimum_signed_margin"]),
                "formal_mean_signed_margin": float(compact["formal_mean_signed_margin"]),
                "formal_best_arrival_ms": int(compact["formal_best_arrival_ms"]),
            }
        )
    equivalence = bool(pass_agreement and arrival_agreement and maximum_difference <= tolerance)
    return rows, {
        "row_count": len(rows),
        "pass_agreement": pass_agreement,
        "arrival_agreement": arrival_agreement,
        "maximum_margin_abs_difference": maximum_difference,
        "absolute_tolerance": tolerance,
        "passed": equivalence,
    }


def _authority(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    groups: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(str(row["pair_id"]), str(row["history_member"]))].append(row)
    context_rows = []
    for key, group in sorted(groups.items()):
        baseline = [row for row in group if row["partition"] == "baseline"]
        schedules = sorted(
            (row for row in group if row["partition"] == "multipulse"),
            key=lambda row: int(row["schedule_index"]),
        )
        if len(baseline) != 1 or len(schedules) != 2:
            raise ValueError(f"R8R9 context coverage changed: {key}")
        base = baseline[0]
        best_schedule = max(
            schedules,
            key=lambda row: (
                float(row["formal_minimum_signed_margin"]),
                float(row["formal_mean_signed_margin"]),
                -int(row["schedule_index"]),
            ),
        )
        candidates = [base, *schedules]
        oracle = max(
            enumerate(candidates),
            key=lambda item: (
                float(item[1]["formal_minimum_signed_margin"]),
                float(item[1]["formal_mean_signed_margin"]),
                -item[0],
            ),
        )[1]
        gain = float(best_schedule["formal_minimum_signed_margin"]) - float(
            base["formal_minimum_signed_margin"]
        )
        repaired = bool(
            not base["formal_contract_pass"]
            and any(bool(row["formal_contract_pass"]) for row in schedules)
        )
        context_rows.append(
            {
                "pair_id": key[0],
                "history_member": key[1],
                "baseline": dict(base),
                "schedules": [dict(row) for row in schedules],
                "best_schedule_index": int(best_schedule["schedule_index"]),
                "best_schedule_minimum_margin_gain": gain,
                "best_schedule_strictly_improves_minimum_margin": gain > 1e-12,
                "failed_baseline_repaired": repaired,
                "oracle_partition": str(oracle["partition"]),
                "oracle_schedule_index": int(oracle["schedule_index"]),
                "oracle_formal_contract_pass": bool(oracle["formal_contract_pass"]),
            }
        )
    baseline_count = sum(bool(row["baseline"]["formal_contract_pass"]) for row in context_rows)
    multipulse_count = sum(
        bool(schedule["formal_contract_pass"])
        for row in context_rows
        for schedule in row["schedules"]
    )
    repairs = sum(bool(row["failed_baseline_repaired"]) for row in context_rows)
    improved = sum(
        bool(row["best_schedule_strictly_improves_minimum_margin"])
        for row in context_rows
        if not row["baseline"]["formal_contract_pass"]
    )
    oracle_count = sum(bool(row["oracle_formal_contract_pass"]) for row in context_rows)
    gains = [float(row["best_schedule_minimum_margin_gain"]) for row in context_rows]
    return {
        "context_rows": context_rows,
        "context_count": len(context_rows),
        "baseline_formal_pass_count": baseline_count,
        "multipulse_formal_pass_count": multipulse_count,
        "failed_baseline_count": len(context_rows) - baseline_count,
        "repaired_failed_baseline_count": repairs,
        "failed_baseline_strict_margin_improvement_count": improved,
        "measured_oracle_formal_pass_count": oracle_count,
        "best_schedule_minimum_margin_gain_minimum": min(gains),
        "best_schedule_minimum_margin_gain_median": statistics.median(gains),
        "best_schedule_minimum_margin_gain_maximum": max(gains),
    }


def _score(values: np.ndarray, tube: np.ndarray, desired: np.ndarray, cfg: Mapping[str, Any]) -> float:
    objective = cfg["objective_contract"]
    scales = np.asarray(objective["physical_scales"], dtype=float)
    components = np.asarray(objective["component_weights"], dtype=float)
    lags = np.asarray(objective["lag_weights"], dtype=float)
    upper = np.abs(values * scales[None, :] - desired[None, :]) + tube
    return float(np.sum(lags[:, None] * components[None, :] * np.square(upper / scales[None, :])))


def _ratio_summary(values: Sequence[float]) -> dict[str, Any]:
    return {
        "minimum": min(map(float, values)),
        "median": statistics.median(map(float, values)),
        "maximum": max(map(float, values)),
        "strictly_better_than_zero_count": sum(float(value) < 1.0 for value in values),
        "meets_frozen_0_995_ratio_count": sum(float(value) <= 0.995 for value in values),
    }


def _score_attribution(stage: Path, cfg: Mapping[str, Any]) -> dict[str, Any]:
    source = cfg["source_r8r8"]
    r8cfg = _read(_root() / str(source["config_path"]))
    detailed = _read(stage / "analysis/offline_primary_detailed.json")
    specs = {
        str(row["experiment_id"]): row for row in _read(stage / "specs/core_specs.json")
    }
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in detailed["forecast_rows"]:
        groups[str(row["row_id"])].append(row)
    ratios = {"frozen_robust": [], "point_only": [], "common_static_tube": []}
    best_names = {key: Counter() for key in ratios}
    maximum_stored_score_difference = 0.0
    for row_id, group in sorted(groups.items()):
        ordered = sorted(group, key=lambda row: int(row["order"]))
        if len(ordered) != 9 or ordered[0]["name"] != "zero":
            raise ValueError(f"R8R9 R8R8 forecast coverage changed: {row_id}")
        spec = specs[str(ordered[0]["experiment_id"])]
        base = np.asarray(r8cfg["objective_contract"]["base_target_physical"], dtype=float)
        offset = np.asarray(spec["r8r8_numeric_target_offsets"], dtype=float)
        desired = np.asarray([base[0] + offset[0], base[1] + offset[1], 0.0, 0.0, base[2] + offset[2]])
        static_tube = np.asarray(ordered[0]["tube_physical"], dtype=float)
        scores: dict[str, list[float]] = {key: [] for key in ratios}
        for forecast in ordered:
            prediction = np.asarray(forecast["combined_prediction"], dtype=float)
            candidate_tube = np.asarray(forecast["tube_physical"], dtype=float)
            robust = _score(prediction, candidate_tube, desired, r8cfg)
            point = _score(prediction, np.zeros_like(candidate_tube), desired, r8cfg)
            common = _score(prediction, static_tube, desired, r8cfg)
            maximum_stored_score_difference = max(
                maximum_stored_score_difference, abs(robust - float(forecast["score"]))
            )
            scores["frozen_robust"].append(robust)
            scores["point_only"].append(point)
            scores["common_static_tube"].append(common)
        for kind, values in scores.items():
            best = min(range(1, len(values)), key=lambda index: (values[index], index))
            ratios[kind].append(float(values[best] / values[0]))
            best_names[kind][str(ordered[best]["name"])] += 1
    return {
        "forecast_count": len(detailed["forecast_rows"]),
        "decision_count": len(groups),
        "maximum_stored_robust_score_abs_difference": maximum_stored_score_difference,
        "frozen_robust": _ratio_summary(ratios["frozen_robust"]),
        "point_only": _ratio_summary(ratios["point_only"]),
        "common_static_tube": _ratio_summary(ratios["common_static_tube"]),
        "best_candidate_name_counts": {
            key: dict(sorted(value.items())) for key, value in best_names.items()
        },
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    config_path = args.config.expanduser().resolve()
    cfg = _read(config_path)
    validate_config(cfg, project_root=_root())
    output = args.run_dir.expanduser().resolve() / RUN_NAME
    if output.exists() and any(output.iterdir()):
        raise ValueError("R8R9 output must be absent or empty")
    source_r8r7 = args.r8r7_run.expanduser().resolve() / str(cfg["source_r8r7"]["stage_directory"])
    source_r8r8 = args.r8r8_run.expanduser().resolve() / str(cfg["source_r8r8"]["stage_directory"])
    auth7 = _authenticate_r8r7(source_r8r7, cfg)
    auth8 = _authenticate_r8r8(source_r8r8, cfg)
    source_ctx = _r8r7_context(args, cfg)
    specs = _read(source_r8r7 / "specs/all_specs.json")
    formal_rows, equivalence = _formal_rows(
        source_ctx,
        source_r8r7,
        specs,
        float(cfg["formal_contract"]["metric_equivalence_absolute_tolerance"]),
    )
    authority = _authority(formal_rows)
    attribution = _score_attribution(source_r8r8, cfg)
    known = cfg["known_aggregate_contract"]
    aggregate_reproduction = bool(
        authority["context_count"] == int(known["context_count"])
        and authority["baseline_formal_pass_count"] == int(known["baseline_formal_pass_count"])
        and authority["multipulse_formal_pass_count"] == int(known["multipulse_formal_pass_count"])
        and attribution["forecast_count"] == int(known["r8r8_forecast_count"])
        and attribution["decision_count"] == int(known["r8r8_decision_count"])
        and attribution["frozen_robust"]["strictly_better_than_zero_count"]
        == int(known["r8r8_nonzero_selection_count"])
    )
    integrity = bool(
        auth7["passed"]
        and auth8["passed"]
        and equivalence["passed"]
        and len(formal_rows) == 48
        and aggregate_reproduction
        and attribution["maximum_stored_robust_score_abs_difference"] <= 1e-12
    )
    gate = cfg["scientific_gate"]
    scientific = bool(
        integrity
        and authority["failed_baseline_count"] == int(gate["failed_baseline_count"])
        and authority["repaired_failed_baseline_count"]
        >= int(gate["minimum_repaired_failed_baseline_count"])
        and authority["measured_oracle_formal_pass_count"]
        >= int(gate["minimum_measured_oracle_formal_pass_count"])
    )
    route = cfg["routes"][
        "audit_fail" if not integrity else ("pass" if scientific else "authority_fail")
    ]
    detailed = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "source_r8r7_authentication": auth7,
        "source_r8r8_authentication": auth8,
        "formal_metric_equivalence": equivalence,
        "formal_rows": formal_rows,
        "authority": authority,
        "r8r8_score_attribution": attribution,
        "known_aggregate_reproduction_passed": aggregate_reproduction,
        "integrity_gate_passed": integrity,
        "scientific_gate_passed": scientific,
        "route": route,
        "real_tsc_executed": False,
        "new_raw_count": 0,
        "passed": scientific,
    }
    output.mkdir(parents=True, exist_ok=True)
    analysis = output / "analysis"
    _write(analysis / "primary_detailed.json", detailed)
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "source_r8r7_authenticated": bool(auth7["passed"]),
        "source_r8r8_authenticated": bool(auth8["passed"]),
        "formal_metric_equivalence": equivalence,
        **{key: value for key, value in authority.items() if key != "context_rows"},
        "r8r8_score_attribution": attribution,
        "known_aggregate_reproduction_passed": aggregate_reproduction,
        "integrity_gate_passed": integrity,
        "scientific_gate_passed": scientific,
        "primary_detailed_sha256": _sha(analysis / "primary_detailed.json"),
        "route": route,
        "real_tsc_executed": False,
        "new_raw_count": 0,
        "passed": scientific,
    }
    _write(analysis / "primary_summary.json", summary)
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "config_path": str(config_path),
        "config_sha256": _sha(config_path),
        "design_document_sha256": str(cfg["design_document_sha256"]),
        "source_r8r7_run": str(args.r8r7_run.expanduser().resolve()),
        "source_r8r8_run": str(args.r8r8_run.expanduser().resolve()),
        "primary_detailed_sha256": summary["primary_detailed_sha256"],
        "primary_summary_sha256": _sha(analysis / "primary_summary.json"),
        "real_tsc_executed": False,
        "new_raw_count": 0,
    }
    _write(output / "stage_manifest.json", manifest)
    _write(
        output / "stage_state.json",
        {
            "schema_version": 1,
            "stage": STAGE,
            "phase_status": "complete" if integrity else "audit_failed",
            "finished": True,
            "real_tsc_executed": False,
            "new_raw_count": 0,
            "stop_reason": "" if scientific else (
                "measured_multipulse_formal_authority_insufficient"
                if integrity
                else "source_or_audit_failed"
            ),
            "verdict": {"route": route, "passed": scientific},
        },
    )
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--r8r7-run", type=Path, required=True)
    parser.add_argument("--r8r8-run", type=Path, required=True)
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
    return parser


def main() -> None:
    result = run(_parser().parse_args())
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
