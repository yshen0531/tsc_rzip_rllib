#!/usr/bin/env python3
"""Run the frozen zero-TSC R8R13 measured additive composition audit."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r12_causal_cumulative_direction2_staircase_authority_sentinel as r8r12,
)


STAGE = "Stage4.2R3c3T13S24D1R14R8R13"
IDENTITY = "measured_additive_direction0_on_direction2_composition_v1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r13_measured_additive_direction0_on_direction2_composition"
ISSUE_STEPS = (14, 18, 22)
SIGNS = (-1, 1)
COMPONENTS = ("R", "Z", "Ip")


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


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


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
        "rows": rows,
    }


def validate_config(cfg: Mapping[str, Any], *, project_root: Path) -> None:
    design = project_root / str(cfg["design_document"])
    contexts = cfg["context_contract"]
    candidates = cfg["candidate_contract"]
    formal = cfg["formal_contract"]
    gate = cfg["scientific_gate"]
    execution = cfg["execution_contract"]
    scope = cfg["scientific_scope"]
    if (
        _digest(cfg) != "915d538896ce61c87f80c0c31d208a2efb3b20842d85cad2ad75e255545bc058"
        or int(cfg.get("schema_version", -1)) != 1
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("run_name") != RUN_NAME
        or cfg.get("source_r8r12_config")
        != "configs/stage4_2r3c3t13s24d1r14r8r12_causal_cumulative_direction2_staircase_authority_sentinel_370ms.json"
        or not design.is_file()
        or _sha(design) != str(cfg["design_document_sha256"])
        or _digest(cfg["source_r8r7"]) != "7d57f9489afb7ae7abbb19db5d9fdd9559ec1d25346363f5599222cd7eebc957"
        or _digest(cfg["source_r8r11"]) != "e7f1616832e3e510fbd4f31486cb65431df33f85fbea2da1edd5450e2ed3793e"
        or _digest(cfg["source_r8r12"]) != "03e8e9689492d26e080e3a9833c63889ed3ce82fe1fb5ecd8981346b2a5d2dcf"
        or len(contexts["ordered_pairs"]) != 8
        or tuple(map(str, contexts["histories"])) != ("minus_first", "plus_first")
        or int(contexts["context_count"]) != 16
        or tuple(map(int, candidates["issue_task_steps"])) != ISSUE_STEPS
        or tuple(map(int, candidates["signs"])) != SIGNS
        or int(candidates["direction_index"]) != 0
        or float(candidates["scale"]) != 1.5
        or tuple(map(int, (candidates["candidate_count"], candidates["r8r11_raw_count"], candidates["r8r12_raw_count"], candidates["r8r7_baseline_raw_count"], candidates["total_source_raw_count"])))
        != (6, 96, 16, 16, 128)
        or tuple(map(str, candidates["additive_components"])) != COMPONENTS
        or float(candidates["additive_absolute_tolerance"]) != 1e-12
        or not bool(candidates["global_candidate_only"])
        or bool(candidates["per_context_oracle_allowed"])
        or tuple(map(int, (formal["normal_arrival_deadline_step"], formal["normal_hold_through_step"], formal["weak_arrival_deadline_step"], formal["weak_hold_through_step"], formal["arrival_streak_steps"])))
        != (25, 35, 27, 37, 3)
        or tuple(map(float, (formal["position_tolerance_m"], formal["speed_tolerance_m_per_s"], formal["ip_tolerance_A"], formal["metric_equivalence_absolute_tolerance"])))
        != (0.03, 0.1, 10000.0, 1e-12)
        or bool(formal["arrival_deadline_expansion_allowed"])
        or tuple(map(int, (gate["required_baseline_formal_pass_count"], gate["required_r8r11_candidate_formal_pass_count"], gate["required_r8r12_candidate_formal_pass_count"], gate["required_failed_baseline_count"], gate["minimum_selected_formal_pass_count"], gate["minimum_repaired_failed_baseline_count"], gate["maximum_baseline_pass_regression_count"])))
        != (6, 36, 6, 10, 7, 1, 0)
        or int(execution["new_raw_count"]) != 0
        or any(bool(execution[key]) for key in ("ray_executed", "gotsc_executed", "tsc_executed", "controller_executed"))
        or int(execution["plant_steps_executed"]) != 0
        or not bool(execution["read_raw_in_place"])
        or not bool(execution["server_virtualenv_only"])
        or not bool(execution["direct_copy_only"])
        or bool(execution["local_archive_operations_allowed"])
        or any(bool(scope[key]) for key in (
            "additive_composition_is_physical_validation",
            "combined_action_safety_validated",
            "retrospective_composition_is_causal_selector",
            "real_mpc_executed",
            "gate_a_qualified",
            "source_trajectories_allowed_in_expert_dataset",
            "expert_data_allowed",
            "bc_dagger_or_rl_allowed",
            "global_plant_reachability_claimed",
        ))
    ):
        raise ValueError("R8R13 frozen design changed")


def _source_context(args: argparse.Namespace, cfg: Mapping[str, Any]) -> r8r12.Context:
    source_args = argparse.Namespace(**vars(args))
    source_args.config = (_root() / str(cfg["source_r8r12_config"])).resolve()
    source_args.run_dir = args.r8r12_run.expanduser().resolve()
    return r8r12.load_context(source_args)


def _hashed(path: Path, expected: str, label: str) -> dict[str, Any]:
    if not path.is_file() or _sha(path) != expected:
        raise ValueError(f"R8R13 {label} changed")
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": expected}


def _check_inventory(
    path: Path, contract: Mapping[str, Any], prefix: str, label: str
) -> dict[str, Any]:
    current = _inventory(path)
    if (
        current["count"] != int(contract[f"{prefix}_raw_count"])
        or current["bytes"] != int(contract[f"{prefix}_raw_bytes"])
        or current["digest"] != str(contract[f"{prefix}_raw_digest"])
    ):
        raise ValueError(f"R8R13 {label} raw inventory changed")
    return current


def _authenticate_sources(
    args: argparse.Namespace, cfg: Mapping[str, Any], ctx: r8r12.Context
) -> dict[str, Any]:
    r8r7_stage = ctx.r8r7_run / str(ctx.cfg["source_r8r7"]["stage_directory"])
    c7 = cfg["source_r8r7"]
    files7 = {
        "final_report": _hashed(r8r7_stage / "analysis/final_report.json", str(c7["final_report_sha256"]), "R8R7 final"),
        "manifest": _hashed(r8r7_stage / "stage_manifest.json", str(c7["stage_manifest_sha256"]), "R8R7 manifest"),
        "state": _hashed(r8r7_stage / "stage_state.json", str(c7["stage_state_sha256"]), "R8R7 state"),
    }
    inv7 = _check_inventory(r8r7_stage / "raw/baseline", c7, "baseline", "R8R7 baseline")
    final7, state7 = _read(r8r7_stage / "analysis/final_report.json"), _read(r8r7_stage / "stage_state.json")
    if final7.get("route") != c7["required_route"] or (state7.get("verdict") or {}).get("route") != c7["required_route"]:
        raise ValueError("R8R13 R8R7 route changed")

    r8r11_stage = ctx.r8r11_run / str(ctx.cfg["source_r8r11"]["stage_directory"])
    c11 = cfg["source_r8r11"]
    files11 = {
        name: _hashed(r8r11_stage / relative, str(c11[key]), f"R8R11 {name}")
        for name, relative, key in (
            ("primary_detailed", "analysis/primary_detailed.json", "primary_detailed_sha256"),
            ("primary_summary", "analysis/primary_summary.json", "primary_summary_sha256"),
            ("final_independent", "analysis/final_independent.json", "final_independent_sha256"),
            ("final_report", "analysis/final_report.json", "final_report_sha256"),
            ("manifest", "stage_manifest.json", "stage_manifest_sha256"),
            ("state", "stage_state.json", "stage_state_sha256"),
        )
    }
    inv11 = {phase: _check_inventory(r8r11_stage / "raw" / phase, c11, phase, f"R8R11 {phase}") for phase in ("safety", "qualification")}
    final11, state11 = _read(r8r11_stage / "analysis/final_report.json"), _read(r8r11_stage / "stage_state.json")
    if final11.get("route") != c11["required_route"] or (state11.get("verdict") or {}).get("route") != c11["required_route"]:
        raise ValueError("R8R13 R8R11 route changed")

    r8r12_stage = ctx.paths.stage
    c12 = cfg["source_r8r12"]
    files12 = {
        name: _hashed(r8r12_stage / relative, str(c12[key]), f"R8R12 {name}")
        for name, relative, key in (
            ("primary_detailed", "analysis/primary_detailed.json", "primary_detailed_sha256"),
            ("primary_summary", "analysis/primary_summary.json", "primary_summary_sha256"),
            ("final_independent", "analysis/final_independent.json", "final_independent_sha256"),
            ("final_report", "analysis/final_report.json", "final_report_sha256"),
            ("manifest", "stage_manifest.json", "stage_manifest_sha256"),
            ("state", "stage_state.json", "stage_state_sha256"),
        )
    }
    inv12 = {phase: _check_inventory(r8r12_stage / "raw" / phase, c12, phase, f"R8R12 {phase}") for phase in ("safety", "qualification")}
    final12, state12 = _read(r8r12_stage / "analysis/final_report.json"), _read(r8r12_stage / "stage_state.json")
    if final12.get("route") != c12["required_route"] or (state12.get("verdict") or {}).get("route") != c12["required_route"]:
        raise ValueError("R8R13 R8R12 route changed")
    return {
        "R8R7": {"stage": str(r8r7_stage), "files": files7, "inventories": {"baseline": inv7}, "passed": True},
        "R8R11": {"stage": str(r8r11_stage), "files": files11, "inventories": inv11, "passed": True},
        "R8R12": {"stage": str(r8r12_stage), "files": files12, "inventories": inv12, "passed": True},
    }


def _strict_result(path: Path, spec: Mapping[str, Any], label: str) -> dict[str, Any]:
    result = r8r12.r8r7.r8._read_gz(path)
    trajectory = result.get("trajectory") or []
    horizon = int(spec["horizon_steps"])
    values = np.asarray([[row[key] for key in COMPONENTS] for row in trajectory], dtype=float)
    if (
        result.get("success") is not True
        or len(trajectory) != horizon + 1
        or values.shape != (horizon + 1, 3)
        or not np.all(np.isfinite(values))
        or any(not all(math.isfinite(float(row[key])) for key in COMPONENTS) for row in trajectory)
    ):
        raise ValueError(f"R8R13 incomplete or non-finite {label}: {spec['experiment_id']}")
    return result


def _load_sources(
    cfg: Mapping[str, Any], ctx: r8r12.Context
) -> tuple[list[dict[str, Any]], dict[tuple[str, str], dict[str, Any]], dict[tuple[str, str, int, int], dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    baseline_specs, baseline_by_id = r8r12._source_baselines(ctx)
    baseline = {}
    for spec in baseline_specs:
        key = (str(spec["pair_id"]), str(spec["history_member"]))
        source_path = Path(ctx.r8r7_run) / str(ctx.cfg["source_r8r7"]["stage_directory"]) / "raw/baseline" / f"{spec['experiment_id']}.json.gz"
        result = _strict_result(source_path, spec, "R8R7 baseline")
        if result != baseline_by_id[str(spec["experiment_id"])]:
            raise ValueError("R8R13 baseline parser disagreement")
        baseline[key] = {"spec": spec, "result": result}

    stage11 = Path(ctx.r8r11_run) / str(ctx.cfg["source_r8r11"]["stage_directory"])
    specs11 = _read(stage11 / "specs/all_specs.json")
    rows11 = {}
    for spec in specs11:
        key = (str(spec["pair_id"]), str(spec["history_member"]), int(spec["r8r11_issue_task_step"]), int(spec["r8r11_sign"]))
        result = _strict_result(stage11 / "raw" / str(spec["partition"]) / f"{spec['experiment_id']}.json.gz", spec, "R8R11 candidate")
        rows11[key] = {"spec": spec, "result": result}

    specs12 = _read(ctx.paths.specs / "all_specs.json")
    rows12 = {}
    for spec in specs12:
        key = (str(spec["pair_id"]), str(spec["history_member"]))
        result = _strict_result(ctx.paths.raw / str(spec["partition"]) / f"{spec['experiment_id']}.json.gz", spec, "R8R12 candidate")
        rows12[key] = {"spec": spec, "result": result}
    expected_contexts = int(cfg["context_contract"]["context_count"])
    if len(baseline) != expected_contexts or len(rows11) != 96 or len(rows12) != expected_contexts:
        raise ValueError("R8R13 source coverage changed")
    return baseline_specs, baseline, rows11, rows12


def _rzi(result: Mapping[str, Any]) -> np.ndarray:
    return np.asarray([[row[key] for key in COMPONENTS] for row in result["trajectory"]], dtype=float)


def _formal(evaluator: Any, result: Mapping[str, Any], meta: Mapping[str, Any]) -> dict[str, Any]:
    return r8r12._formal_row(evaluator, result, meta)


def _synthetic(source: Mapping[str, Any], values: np.ndarray) -> dict[str, Any]:
    result = copy.deepcopy(source)
    if values.shape != (len(result["trajectory"]), 3):
        raise ValueError("R8R13 synthetic trajectory shape changed")
    for row, value in zip(result["trajectory"], values):
        for key, item in zip(COMPONENTS, value):
            row[key] = float(item)
    return result


def _source_formal(
    evaluators: Mapping[str, Any],
    baseline: Mapping[tuple[str, str], Mapping[str, Any]],
    rows11: Mapping[tuple[str, str, int, int], Mapping[str, Any]],
    rows12: Mapping[tuple[str, str], Mapping[str, Any]],
    tolerance: float,
) -> tuple[dict[str, Any], dict[tuple[str, str], dict[str, Any]]]:
    base_formal = {}
    all_rows: dict[str, list[dict[str, Any]]] = {"R8R7": [], "R8R11": [], "R8R12": []}
    for key, item in baseline.items():
        evaluator = evaluators[str(item["spec"]["experiment_id"])]
        row = _formal(evaluator, item["result"], {"pair_id": key[0], "history_member": key[1]})
        base_formal[key] = row
        all_rows["R8R7"].append(row)
    for key, item in rows11.items():
        evaluator = evaluators[str(baseline[key[:2]]["spec"]["experiment_id"])]
        all_rows["R8R11"].append(_formal(evaluator, item["result"], {"pair_id": key[0], "history_member": key[1], "issue_task_step": key[2], "sign": key[3]}))
    for key, item in rows12.items():
        evaluator = evaluators[str(baseline[key]["spec"]["experiment_id"])]
        all_rows["R8R12"].append(_formal(evaluator, item["result"], {"pair_id": key[0], "history_member": key[1]}))
    output = {}
    for source, rows in all_rows.items():
        output[source] = {
            "strict_raw_count": len(rows),
            "formal_pass_count": sum(bool(row["formal_contract_pass"]) for row in rows),
            "pass_agreement": all(row["formal_contract_pass"] == row["existing_pass"] for row in rows),
            "arrival_agreement": all(row["formal_best_arrival_ms"] == row["existing_arrival_ms"] for row in rows),
            "maximum_margin_abs_difference": max(float(row["maximum_margin_abs_difference"]) for row in rows),
        }
        output[source]["metric_equivalence_passed"] = bool(
            output[source]["pass_agreement"]
            and output[source]["arrival_agreement"]
            and output[source]["maximum_margin_abs_difference"] <= tolerance
        )
    return output, base_formal


def _gain_statistics(values: Sequence[float]) -> dict[str, float]:
    return {
        "minimum": min(map(float, values)),
        "median": statistics.median(map(float, values)),
        "maximum": max(map(float, values)),
    }


def _rank_candidates(rows: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            -int(row["formal_pass_count"]),
            -int(row["repaired_failed_baseline_count"]),
            int(row["baseline_pass_regression_count"]),
            -float(row["failed_baseline_minimum_margin_gain"]["minimum"]),
            int(row["candidate_index"]),
        ),
    )


def _compose(
    cfg: Mapping[str, Any],
    evaluators: Mapping[str, Any],
    baseline: Mapping[tuple[str, str], Mapping[str, Any]],
    base_formal: Mapping[tuple[str, str], Mapping[str, Any]],
    rows11: Mapping[tuple[str, str, int, int], Mapping[str, Any]],
    rows12: Mapping[tuple[str, str], Mapping[str, Any]],
) -> dict[str, Any]:
    tolerance = float(cfg["candidate_contract"]["additive_absolute_tolerance"])
    contexts = [(str(pair), str(history)) for pair in cfg["context_contract"]["ordered_pairs"] for history in cfg["context_contract"]["histories"]]
    candidates = []
    maximum_algebra_difference = 0.0
    maximum_metric_difference = 0.0
    zero_maximum_value_difference = 0.0
    zero_rows = []
    for key in contexts:
        base = _rzi(baseline[key]["result"])
        r12 = _rzi(rows12[key]["result"])
        zero = r12 + (base - base)
        zero_maximum_value_difference = max(zero_maximum_value_difference, float(np.max(np.abs(zero - r12))))
        evaluator = evaluators[str(baseline[key]["spec"]["experiment_id"])]
        zero_formal = _formal(evaluator, _synthetic(rows12[key]["result"], zero), {"pair_id": key[0], "history_member": key[1]})
        source_formal = _formal(evaluator, rows12[key]["result"], {"pair_id": key[0], "history_member": key[1]})
        zero_rows.append({
            "pair_id": key[0], "history_member": key[1],
            "values_exact": bool(np.array_equal(zero, r12)),
            "formal_exact": zero_formal == source_formal,
        })
    for candidate_index, (issue, sign) in enumerate((item for issue in ISSUE_STEPS for item in ((issue, -1), (issue, 1)))):
        rows = []
        for key in contexts:
            base_result = baseline[key]["result"]
            r11_result = rows11[(*key, issue, sign)]["result"]
            r12_result = rows12[key]["result"]
            base, r11, r12 = _rzi(base_result), _rzi(r11_result), _rzi(r12_result)
            if base.shape != r11.shape or base.shape != r12.shape:
                raise ValueError("R8R13 source time grids changed")
            additive = r12 + (r11 - base)
            additive_check = base + (r12 - base) + (r11 - base)
            difference = float(np.max(np.abs(additive - additive_check)))
            maximum_algebra_difference = max(maximum_algebra_difference, difference)
            evaluator = evaluators[str(baseline[key]["spec"]["experiment_id"])]
            formal = _formal(evaluator, _synthetic(r12_result, additive), {
                "pair_id": key[0], "history_member": key[1],
                "candidate_index": candidate_index, "issue_task_step": issue, "sign": sign,
            })
            maximum_metric_difference = max(maximum_metric_difference, float(formal["maximum_margin_abs_difference"]))
            base_row = base_formal[key]
            gain = float(formal["formal_minimum_signed_margin"]) - float(base_row["formal_minimum_signed_margin"])
            rows.append({
                **formal,
                "algebra_maximum_abs_difference": difference,
                "baseline_formal_pass": bool(base_row["formal_contract_pass"]),
                "baseline_minimum_signed_margin": float(base_row["formal_minimum_signed_margin"]),
                "minimum_signed_margin_gain": gain,
                "failed_baseline_repaired": bool(not base_row["formal_contract_pass"] and formal["formal_contract_pass"]),
                "baseline_pass_regressed": bool(base_row["formal_contract_pass"] and not formal["formal_contract_pass"]),
            })
        failed_gains = [float(row["minimum_signed_margin_gain"]) for row in rows if not row["baseline_formal_pass"]]
        candidates.append({
            "candidate_index": candidate_index,
            "issue_task_step": issue,
            "sign": sign,
            "context_count": len(rows),
            "formal_pass_count": sum(bool(row["formal_contract_pass"]) for row in rows),
            "repaired_failed_baseline_count": sum(bool(row["failed_baseline_repaired"]) for row in rows),
            "baseline_pass_regression_count": sum(bool(row["baseline_pass_regressed"]) for row in rows),
            "failed_baseline_minimum_margin_gain": _gain_statistics(failed_gains),
            "context_rows": rows,
        })
    ranked = _rank_candidates(candidates)
    selected = ranked[0]
    gate = cfg["scientific_gate"]
    return {
        "candidate_count": len(candidates),
        "context_count": len(contexts),
        "maximum_additive_algebra_abs_difference": maximum_algebra_difference,
        "maximum_formal_metric_abs_difference": maximum_metric_difference,
        "zero_correction_maximum_value_abs_difference": zero_maximum_value_difference,
        "zero_correction_exact_count": sum(bool(row["values_exact"] and row["formal_exact"]) for row in zero_rows),
        "zero_correction_rows": zero_rows,
        "candidates": candidates,
        "ranking": [int(row["candidate_index"]) for row in ranked],
        "selected_candidate": selected,
        "additive_equivalence_passed": maximum_algebra_difference <= tolerance,
        "formal_metric_equivalence_passed": maximum_metric_difference <= float(cfg["formal_contract"]["metric_equivalence_absolute_tolerance"]),
        "zero_correction_reproduction_passed": bool(zero_maximum_value_difference <= tolerance and all(row["values_exact"] and row["formal_exact"] for row in zero_rows)),
        "scientific_gate_passed": bool(
            int(selected["formal_pass_count"]) >= int(gate["minimum_selected_formal_pass_count"])
            and int(selected["repaired_failed_baseline_count"]) >= int(gate["minimum_repaired_failed_baseline_count"])
            and int(selected["baseline_pass_regression_count"]) <= int(gate["maximum_baseline_pass_regression_count"])
        ),
    }


def _comparison_payload(summary: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: summary[key]
        for key in (
            "source_formal_reproduction",
            "integrity_gate_passed",
            "scientific_gate_passed",
            "selected_candidate_index",
            "selected_issue_task_step",
            "selected_sign",
            "selected_formal_pass_count",
            "selected_repaired_failed_baseline_count",
            "selected_baseline_pass_regression_count",
            "selected_failed_baseline_minimum_margin_gain",
            "candidate_summaries",
            "candidate_ranking",
            "maximum_additive_algebra_abs_difference",
            "maximum_formal_metric_abs_difference",
            "zero_correction_maximum_value_abs_difference",
            "route",
            "real_tsc_executed",
            "new_raw_count",
        )
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    config_path = args.config.expanduser().resolve()
    cfg = _read(config_path)
    validate_config(cfg, project_root=_root())
    output = args.run_dir.expanduser().resolve() / RUN_NAME
    if output.exists() and any(output.iterdir()):
        raise ValueError("R8R13 output must be absent or empty")
    ctx = _source_context(args, cfg)
    auth = _authenticate_sources(args, cfg, ctx)
    baseline_specs, baseline, rows11, rows12 = _load_sources(cfg, ctx)
    evaluators, _ = r8r12.r8r7.r8.d1r11._formal_callback(ctx.source_ctx.r8_ctx.d1r11_ctx, baseline_specs)
    tolerance = float(cfg["formal_contract"]["metric_equivalence_absolute_tolerance"])
    source_formal, base_formal = _source_formal(evaluators, baseline, rows11, rows12, tolerance)
    expected = cfg["scientific_gate"]
    source_reproduction = bool(
        source_formal["R8R7"]["formal_pass_count"] == int(expected["required_baseline_formal_pass_count"])
        and source_formal["R8R11"]["formal_pass_count"] == int(expected["required_r8r11_candidate_formal_pass_count"])
        and source_formal["R8R12"]["formal_pass_count"] == int(expected["required_r8r12_candidate_formal_pass_count"])
        and all(row["metric_equivalence_passed"] for row in source_formal.values())
    )
    composition = _compose(cfg, evaluators, baseline, base_formal, rows11, rows12)
    integrity = bool(
        all(row["passed"] for row in auth.values())
        and source_reproduction
        and composition["additive_equivalence_passed"]
        and composition["formal_metric_equivalence_passed"]
        and composition["zero_correction_reproduction_passed"]
        and composition["context_count"] == 16
        and composition["candidate_count"] == 6
    )
    scientific = bool(integrity and composition["scientific_gate_passed"])
    route = cfg["routes"]["integrity_fail" if not integrity else ("pass" if scientific else "authority_fail")]
    output.mkdir(parents=True, exist_ok=True)
    analysis = output / "analysis"
    source_reference = output / "source_reference"
    _write(source_reference / "source_authentication.json", auth)
    detailed = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "source_authentication": auth,
        "source_formal_reproduction": source_formal,
        "known_source_aggregate_reproduction_passed": source_reproduction,
        "composition": composition,
        "integrity_gate_passed": integrity,
        "scientific_gate_passed": scientific,
        "route": route,
        "real_tsc_executed": False,
        "new_raw_count": 0,
        "passed": scientific,
    }
    _write(analysis / "primary_detailed.json", detailed)
    selected = composition["selected_candidate"]
    candidate_summaries = [
        {key: row[key] for key in (
            "candidate_index", "issue_task_step", "sign", "context_count",
            "formal_pass_count", "repaired_failed_baseline_count",
            "baseline_pass_regression_count", "failed_baseline_minimum_margin_gain",
        )}
        for row in composition["candidates"]
    ]
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "source_formal_reproduction": source_formal,
        "known_source_aggregate_reproduction_passed": source_reproduction,
        "integrity_gate_passed": integrity,
        "scientific_gate_passed": scientific,
        "selected_candidate_index": int(selected["candidate_index"]),
        "selected_issue_task_step": int(selected["issue_task_step"]),
        "selected_sign": int(selected["sign"]),
        "selected_formal_pass_count": int(selected["formal_pass_count"]),
        "selected_repaired_failed_baseline_count": int(selected["repaired_failed_baseline_count"]),
        "selected_baseline_pass_regression_count": int(selected["baseline_pass_regression_count"]),
        "selected_failed_baseline_minimum_margin_gain": selected["failed_baseline_minimum_margin_gain"],
        "candidate_summaries": candidate_summaries,
        "candidate_ranking": composition["ranking"],
        "maximum_additive_algebra_abs_difference": composition["maximum_additive_algebra_abs_difference"],
        "maximum_formal_metric_abs_difference": composition["maximum_formal_metric_abs_difference"],
        "zero_correction_maximum_value_abs_difference": composition["zero_correction_maximum_value_abs_difference"],
        "primary_detailed_sha256": _sha(analysis / "primary_detailed.json"),
        "route": route,
        "real_tsc_executed": False,
        "new_raw_count": 0,
        "passed": scientific,
    }
    summary["comparison_payload"] = _comparison_payload(summary)
    _write(analysis / "primary_summary.json", summary)
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "config_path": str(config_path),
        "config_sha256": _sha(config_path),
        "design_document_sha256": str(cfg["design_document_sha256"]),
        "source_r8r7_run": str(args.r8r7_run.expanduser().resolve()),
        "source_r8r11_run": str(args.r8r11_run.expanduser().resolve()),
        "source_r8r12_run": str(args.r8r12_run.expanduser().resolve()),
        "source_authentication_sha256": _sha(source_reference / "source_authentication.json"),
        "primary_detailed_sha256": summary["primary_detailed_sha256"],
        "primary_summary_sha256": _sha(analysis / "primary_summary.json"),
        "real_tsc_executed": False,
        "new_raw_count": 0,
    }
    _write(output / "stage_manifest.json", manifest)
    _write(output / "stage_state.json", {
        "schema_version": 1,
        "stage": STAGE,
        "phase_status": "primary_ready",
        "finished": False,
        "real_tsc_executed": False,
        "new_raw_count": 0,
        "formal_outcomes_opened": True,
        "stop_reason": "awaiting_independent_forensics",
        "verdict": None,
    })
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "config", "run-dir", "r8r7-run", "r8r11-run", "r8r12-run", "r8-run", "r8r1-output", "r8r6-run",
        "source-d1r11-run", "source-r2-run", "source-r4-run", "source-r6-run", "source-s21-run", "source-s23r1-output", "source-s24-run",
        "source-d1r9-v1", "source-d1r9-v2", "source-d1r10-run", "source-d1r10-audit", "source-stage42r3b-run", "source-stage42r3c3-run",
        "source-stage42r3c3-bank-dir", "source-stage42r3c3t1-run", "source-stage42r3c3t1-audit-dir", "source-stage42r3c3t3-controller-bank",
        "q1-run", "q2-run", "q1-audit", "q2-audit", "r3b-server-audit", "r3b-snapshot-checks",
    ):
        parser.add_argument(f"--{name}", dest=name.replace("-", "_"), type=Path, required=True)
    return parser


def main() -> None:
    print(json.dumps(run(_parser().parse_args()), indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
