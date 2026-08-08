#!/usr/bin/env python3
"""Structurally independent R8R13 raw and additive-composition forensics."""

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

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r12_independent_forensics as ind12,
)


STAGE = "Stage4.2R3c3T13S24D1R14R8R13"
IDENTITY = "measured_additive_direction0_on_direction2_composition_v1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r13_measured_additive_direction0_on_direction2_composition"
ISSUES = (14, 18, 22)
SIGNS = (-1, 1)
FIELDS = ("R", "Z", "Ip")


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
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _inventory(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    rows = []
    for file in sorted(path.glob("*.json.gz"), key=lambda value: value.name):
        size = file.stat().st_size
        sha = _sha(file)
        digest.update(f"{file.name}\0{size}\0{sha}\n".encode())
        rows.append({"name": file.name, "size": size, "sha256": sha})
    return {
        "count": len(rows),
        "bytes": sum(int(row["size"]) for row in rows),
        "digest": digest.hexdigest(),
        "rows": rows,
    }


def _hashed(path: Path, expected: str, label: str) -> dict[str, Any]:
    actual = _sha(path) if path.is_file() else ""
    if actual != expected:
        raise ValueError(f"independent R8R13 {label} changed")
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": actual}


def _check_inventory(path: Path, contract: Mapping[str, Any], prefix: str, label: str) -> dict[str, Any]:
    current = _inventory(path)
    expected = {
        "count": int(contract[f"{prefix}_raw_count"]),
        "bytes": int(contract[f"{prefix}_raw_bytes"]),
        "digest": str(contract[f"{prefix}_raw_digest"]),
    }
    if any(current[key] != value for key, value in expected.items()):
        raise ValueError(f"independent R8R13 {label} inventory changed")
    return current


def _validate(cfg: Mapping[str, Any]) -> None:
    design = _root() / str(cfg["design_document"])
    candidates = cfg["candidate_contract"]
    formal = cfg["formal_contract"]
    gate = cfg["scientific_gate"]
    execution = cfg["execution_contract"]
    scope = cfg["scientific_scope"]
    if (
        _digest(cfg) != "915d538896ce61c87f80c0c31d208a2efb3b20842d85cad2ad75e255545bc058"
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("run_name") != RUN_NAME
        or not design.is_file()
        or _sha(design) != cfg["design_document_sha256"]
        or _digest(cfg["source_r8r7"]) != "7d57f9489afb7ae7abbb19db5d9fdd9559ec1d25346363f5599222cd7eebc957"
        or _digest(cfg["source_r8r11"]) != "e7f1616832e3e510fbd4f31486cb65431df33f85fbea2da1edd5450e2ed3793e"
        or _digest(cfg["source_r8r12"]) != "03e8e9689492d26e080e3a9833c63889ed3ce82fe1fb5ecd8981346b2a5d2dcf"
        or tuple(map(int, candidates["issue_task_steps"])) != ISSUES
        or tuple(map(int, candidates["signs"])) != SIGNS
        or int(candidates["direction_index"]) != 0
        or float(candidates["scale"]) != 1.5
        or int(candidates["total_source_raw_count"]) != 128
        or tuple(map(str, candidates["additive_components"])) != FIELDS
        or float(candidates["additive_absolute_tolerance"]) != 1e-12
        or not candidates["global_candidate_only"]
        or candidates["per_context_oracle_allowed"]
        or tuple(map(int, (formal["normal_arrival_deadline_step"], formal["normal_hold_through_step"], formal["weak_arrival_deadline_step"], formal["weak_hold_through_step"], formal["arrival_streak_steps"]))) != (25, 35, 27, 37, 3)
        or tuple(map(int, (gate["required_baseline_formal_pass_count"], gate["required_r8r11_candidate_formal_pass_count"], gate["required_r8r12_candidate_formal_pass_count"], gate["required_failed_baseline_count"], gate["minimum_selected_formal_pass_count"], gate["minimum_repaired_failed_baseline_count"], gate["maximum_baseline_pass_regression_count"]))) != (6, 36, 6, 10, 7, 1, 0)
        or int(execution["new_raw_count"]) != 0
        or int(execution["plant_steps_executed"]) != 0
        or any(execution[key] for key in ("ray_executed", "gotsc_executed", "tsc_executed", "controller_executed"))
        or any(scope[key] for key in (
            "additive_composition_is_physical_validation", "combined_action_safety_validated",
            "retrospective_composition_is_causal_selector", "real_mpc_executed", "gate_a_qualified",
            "source_trajectories_allowed_in_expert_dataset", "expert_data_allowed",
            "bc_dagger_or_rl_allowed", "global_plant_reachability_claimed",
        ))
    ):
        raise ValueError("independent R8R13 frozen design changed")


def _r8r12_args(args: argparse.Namespace, cfg: Mapping[str, Any]) -> tuple[argparse.Namespace, dict[str, Any]]:
    source_cfg_path = (_root() / str(cfg["source_r8r12_config"])).resolve()
    source_cfg = _read(source_cfg_path)
    source_args = argparse.Namespace(**vars(args))
    source_args.config = source_cfg_path
    source_args.run_dir = args.r8r12_run.expanduser().resolve()
    return source_args, source_cfg


def _authenticate(
    args: argparse.Namespace,
    cfg: Mapping[str, Any],
    source_args: argparse.Namespace,
    source_cfg: Mapping[str, Any],
) -> dict[str, Any]:
    stage7 = args.r8r7_run.expanduser().resolve() / str(source_cfg["source_r8r7"]["stage_directory"])
    c7 = cfg["source_r8r7"]
    f7 = {
        name: _hashed(stage7 / rel, str(c7[key]), f"R8R7 {name}")
        for name, rel, key in (
            ("final_report", "analysis/final_report.json", "final_report_sha256"),
            ("manifest", "stage_manifest.json", "stage_manifest_sha256"),
            ("state", "stage_state.json", "stage_state_sha256"),
        )
    }
    i7 = _check_inventory(stage7 / "raw/baseline", c7, "baseline", "R8R7 baseline")
    if _read(stage7 / "analysis/final_report.json").get("route") != c7["required_route"]:
        raise ValueError("independent R8R13 R8R7 route changed")

    stage11 = args.r8r11_run.expanduser().resolve() / str(source_cfg["source_r8r11"]["stage_directory"])
    c11 = cfg["source_r8r11"]
    f11 = {
        name: _hashed(stage11 / rel, str(c11[key]), f"R8R11 {name}")
        for name, rel, key in (
            ("primary_detailed", "analysis/primary_detailed.json", "primary_detailed_sha256"),
            ("primary_summary", "analysis/primary_summary.json", "primary_summary_sha256"),
            ("final_independent", "analysis/final_independent.json", "final_independent_sha256"),
            ("final_report", "analysis/final_report.json", "final_report_sha256"),
            ("manifest", "stage_manifest.json", "stage_manifest_sha256"),
            ("state", "stage_state.json", "stage_state_sha256"),
        )
    }
    i11 = {phase: _check_inventory(stage11 / "raw" / phase, c11, phase, f"R8R11 {phase}") for phase in ("safety", "qualification")}
    if _read(stage11 / "analysis/final_report.json").get("route") != c11["required_route"]:
        raise ValueError("independent R8R13 R8R11 route changed")

    stage12 = args.r8r12_run.expanduser().resolve() / str(source_cfg["run_name"])
    c12 = cfg["source_r8r12"]
    f12 = {
        name: _hashed(stage12 / rel, str(c12[key]), f"R8R12 {name}")
        for name, rel, key in (
            ("primary_detailed", "analysis/primary_detailed.json", "primary_detailed_sha256"),
            ("primary_summary", "analysis/primary_summary.json", "primary_summary_sha256"),
            ("final_independent", "analysis/final_independent.json", "final_independent_sha256"),
            ("final_report", "analysis/final_report.json", "final_report_sha256"),
            ("manifest", "stage_manifest.json", "stage_manifest_sha256"),
            ("state", "stage_state.json", "stage_state_sha256"),
        )
    }
    i12 = {phase: _check_inventory(stage12 / "raw" / phase, c12, phase, f"R8R12 {phase}") for phase in ("safety", "qualification")}
    if _read(stage12 / "analysis/final_report.json").get("route") != c12["required_route"]:
        raise ValueError("independent R8R13 R8R12 route changed")
    return {
        "R8R7": {"stage": str(stage7), "files": f7, "inventories": {"baseline": i7}, "passed": True},
        "R8R11": {"stage": str(stage11), "files": f11, "inventories": i11, "passed": True},
        "R8R12": {"stage": str(stage12), "files": f12, "inventories": i12, "passed": True},
    }


def _strict(path: Path, spec: Mapping[str, Any], source: str) -> dict[str, Any]:
    result = ind12._gzip(path)
    trajectory = result.get("trajectory") or []
    horizon = int(spec["horizon_steps"])
    values = np.asarray([[row[key] for key in FIELDS] for row in trajectory], dtype=float)
    if (
        result.get("success") is not True
        or len(trajectory) != horizon + 1
        or values.shape != (horizon + 1, 3)
        or not np.all(np.isfinite(values))
        or any(not all(math.isfinite(float(row[key])) for key in FIELDS) for row in trajectory)
    ):
        raise ValueError(f"independent R8R13 invalid {source}: {spec['experiment_id']}")
    return result


def _load(
    args: argparse.Namespace,
    cfg: Mapping[str, Any],
    source_args: argparse.Namespace,
    source_cfg: Mapping[str, Any],
    source_ctx: Any,
) -> tuple[list[dict[str, Any]], dict[tuple[str, str], dict[str, Any]], dict[tuple[str, str, int, int], dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    specs7, _ = ind12._source_baselines(source_args, source_cfg, source_ctx)
    stage7 = args.r8r7_run.expanduser().resolve() / str(source_cfg["source_r8r7"]["stage_directory"])
    baseline = {}
    for spec in specs7:
        key = (str(spec["pair_id"]), str(spec["history_member"]))
        baseline[key] = {"spec": spec, "result": _strict(stage7 / "raw/baseline" / f"{spec['experiment_id']}.json.gz", spec, "R8R7")}

    stage11 = args.r8r11_run.expanduser().resolve() / str(source_cfg["source_r8r11"]["stage_directory"])
    bank11 = {}
    for spec in _read(stage11 / "specs/all_specs.json"):
        key = (str(spec["pair_id"]), str(spec["history_member"]), int(spec["r8r11_issue_task_step"]), int(spec["r8r11_sign"]))
        bank11[key] = {"spec": spec, "result": _strict(stage11 / "raw" / str(spec["partition"]) / f"{spec['experiment_id']}.json.gz", spec, "R8R11")}

    stage12 = args.r8r12_run.expanduser().resolve() / str(source_cfg["run_name"])
    bank12 = {}
    for spec in _read(stage12 / "specs/all_specs.json"):
        key = (str(spec["pair_id"]), str(spec["history_member"]))
        bank12[key] = {"spec": spec, "result": _strict(stage12 / "raw" / str(spec["partition"]) / f"{spec['experiment_id']}.json.gz", spec, "R8R12")}
    if (len(baseline), len(bank11), len(bank12)) != (16, 96, 16):
        raise ValueError("independent R8R13 source coverage changed")
    return specs7, baseline, bank11, bank12


def _values(result: Mapping[str, Any]) -> np.ndarray:
    return np.asarray([[row[field] for field in FIELDS] for row in result["trajectory"]], dtype=float)


def _synthetic(source: Mapping[str, Any], values: np.ndarray) -> dict[str, Any]:
    result = copy.deepcopy(source)
    for row, vector in zip(result["trajectory"], values):
        row.update({field: float(value) for field, value in zip(FIELDS, vector)})
    return result


def _formal(evaluator: Any, result: Mapping[str, Any], meta: Mapping[str, Any]) -> dict[str, Any]:
    return ind12.ind11._formal_row(evaluator, result, meta)


def _reproduce(
    evaluators: Mapping[str, Any],
    baseline: Mapping[tuple[str, str], Mapping[str, Any]],
    bank11: Mapping[tuple[str, str, int, int], Mapping[str, Any]],
    bank12: Mapping[tuple[str, str], Mapping[str, Any]],
    tolerance: float,
) -> tuple[dict[str, Any], dict[tuple[str, str], dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {"R8R7": [], "R8R11": [], "R8R12": []}
    base_formal = {}
    for key, item in baseline.items():
        evaluator = evaluators[str(item["spec"]["experiment_id"])]
        row = _formal(evaluator, item["result"], {"pair_id": key[0], "history_member": key[1]})
        groups["R8R7"].append(row)
        base_formal[key] = row
    for key, item in bank11.items():
        evaluator = evaluators[str(baseline[key[:2]]["spec"]["experiment_id"])]
        groups["R8R11"].append(_formal(evaluator, item["result"], {"pair_id": key[0], "history_member": key[1], "issue_task_step": key[2], "sign": key[3]}))
    for key, item in bank12.items():
        evaluator = evaluators[str(baseline[key]["spec"]["experiment_id"])]
        groups["R8R12"].append(_formal(evaluator, item["result"], {"pair_id": key[0], "history_member": key[1]}))
    output = {}
    for source, rows in groups.items():
        row = {
            "strict_raw_count": len(rows),
            "formal_pass_count": sum(bool(item["formal_contract_pass"]) for item in rows),
            "pass_agreement": all(item["formal_contract_pass"] == item["existing_pass"] for item in rows),
            "arrival_agreement": all(item["formal_best_arrival_ms"] == item["existing_arrival_ms"] for item in rows),
            "maximum_margin_abs_difference": max(float(item["maximum_margin_abs_difference"]) for item in rows),
        }
        row["metric_equivalence_passed"] = bool(row["pass_agreement"] and row["arrival_agreement"] and row["maximum_margin_abs_difference"] <= tolerance)
        output[source] = row
    return output, base_formal


def _stats(values: Sequence[float]) -> dict[str, float]:
    return {"minimum": min(values), "median": statistics.median(values), "maximum": max(values)}


def _rank(rows: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return sorted(rows, key=lambda row: (
        -int(row["formal_pass_count"]),
        -int(row["repaired_failed_baseline_count"]),
        int(row["baseline_pass_regression_count"]),
        -float(row["failed_baseline_minimum_margin_gain"]["minimum"]),
        int(row["candidate_index"]),
    ))


def _composition(
    cfg: Mapping[str, Any],
    evaluators: Mapping[str, Any],
    baseline: Mapping[tuple[str, str], Mapping[str, Any]],
    base_formal: Mapping[tuple[str, str], Mapping[str, Any]],
    bank11: Mapping[tuple[str, str, int, int], Mapping[str, Any]],
    bank12: Mapping[tuple[str, str], Mapping[str, Any]],
) -> dict[str, Any]:
    contexts = [(str(pair), str(history)) for pair in cfg["context_contract"]["ordered_pairs"] for history in cfg["context_contract"]["histories"]]
    maximum_algebra = maximum_metric = maximum_zero = 0.0
    zero_exact = 0
    for key in contexts:
        base, r12 = _values(baseline[key]["result"]), _values(bank12[key]["result"])
        zero = r12 + (base - base)
        maximum_zero = max(maximum_zero, float(np.max(np.abs(zero - r12))))
        evaluator = evaluators[str(baseline[key]["spec"]["experiment_id"])]
        zf = _formal(evaluator, _synthetic(bank12[key]["result"], zero), {})
        sf = _formal(evaluator, bank12[key]["result"], {})
        zero_exact += bool(np.array_equal(zero, r12) and zf == sf)
    candidates = []
    index = 0
    for issue in ISSUES:
        for sign in SIGNS:
            rows = []
            for key in contexts:
                base = _values(baseline[key]["result"])
                r11 = _values(bank11[(*key, issue, sign)]["result"])
                r12 = _values(bank12[key]["result"])
                if not (base.shape == r11.shape == r12.shape):
                    raise ValueError("independent R8R13 time grid changed")
                path_a = r12 + (r11 - base)
                path_b = base + (r12 - base) + (r11 - base)
                algebra = float(np.max(np.abs(path_a - path_b)))
                maximum_algebra = max(maximum_algebra, algebra)
                evaluator = evaluators[str(baseline[key]["spec"]["experiment_id"])]
                formal = _formal(evaluator, _synthetic(bank12[key]["result"], path_a), {})
                maximum_metric = max(maximum_metric, float(formal["maximum_margin_abs_difference"]))
                base_row = base_formal[key]
                rows.append({
                    "pass": bool(formal["formal_contract_pass"]),
                    "base_pass": bool(base_row["formal_contract_pass"]),
                    "gain": float(formal["formal_minimum_signed_margin"]) - float(base_row["formal_minimum_signed_margin"]),
                })
            failed_gains = [float(row["gain"]) for row in rows if not row["base_pass"]]
            candidates.append({
                "candidate_index": index,
                "issue_task_step": issue,
                "sign": sign,
                "context_count": len(rows),
                "formal_pass_count": sum(row["pass"] for row in rows),
                "repaired_failed_baseline_count": sum(not row["base_pass"] and row["pass"] for row in rows),
                "baseline_pass_regression_count": sum(row["base_pass"] and not row["pass"] for row in rows),
                "failed_baseline_minimum_margin_gain": _stats(failed_gains),
            })
            index += 1
    ranked = _rank(candidates)
    selected = ranked[0]
    gate = cfg["scientific_gate"]
    return {
        "candidate_summaries": candidates,
        "candidate_ranking": [int(row["candidate_index"]) for row in ranked],
        "selected": selected,
        "maximum_additive_algebra_abs_difference": maximum_algebra,
        "maximum_formal_metric_abs_difference": maximum_metric,
        "zero_correction_maximum_value_abs_difference": maximum_zero,
        "zero_correction_exact_count": zero_exact,
        "additive_equivalence_passed": maximum_algebra <= float(cfg["candidate_contract"]["additive_absolute_tolerance"]),
        "metric_equivalence_passed": maximum_metric <= float(cfg["formal_contract"]["metric_equivalence_absolute_tolerance"]),
        "zero_reproduction_passed": zero_exact == 16 and maximum_zero <= float(cfg["candidate_contract"]["additive_absolute_tolerance"]),
        "scientific_gate_passed": bool(
            int(selected["formal_pass_count"]) >= int(gate["minimum_selected_formal_pass_count"])
            and int(selected["repaired_failed_baseline_count"]) >= int(gate["minimum_repaired_failed_baseline_count"])
            and int(selected["baseline_pass_regression_count"]) <= int(gate["maximum_baseline_pass_regression_count"])
        ),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    config_path = args.config.expanduser().resolve()
    cfg = _read(config_path)
    _validate(cfg)
    output = args.run_dir.expanduser().resolve() / RUN_NAME
    primary_path = output / "analysis/primary_summary.json"
    state_path = output / "stage_state.json"
    if not primary_path.is_file() or _read(state_path).get("phase_status") != "primary_ready":
        raise ValueError("independent R8R13 primary is not ready")
    source_args, source_cfg = _r8r12_args(args, cfg)
    source_ctx = ind12._source_context(source_args, source_cfg)
    auth = _authenticate(args, cfg, source_args, source_cfg)
    specs, baseline, bank11, bank12 = _load(args, cfg, source_args, source_cfg, source_ctx)
    evaluators, _ = ind12.r8r7.r8.d1r11._formal_callback(source_ctx.r8_ctx.d1r11_ctx, specs)
    tolerance = float(cfg["formal_contract"]["metric_equivalence_absolute_tolerance"])
    source_formal, base_formal = _reproduce(evaluators, baseline, bank11, bank12, tolerance)
    gate = cfg["scientific_gate"]
    source_reproduction = bool(
        source_formal["R8R7"]["formal_pass_count"] == int(gate["required_baseline_formal_pass_count"])
        and source_formal["R8R11"]["formal_pass_count"] == int(gate["required_r8r11_candidate_formal_pass_count"])
        and source_formal["R8R12"]["formal_pass_count"] == int(gate["required_r8r12_candidate_formal_pass_count"])
        and all(row["metric_equivalence_passed"] for row in source_formal.values())
    )
    composition = _composition(cfg, evaluators, baseline, base_formal, bank11, bank12)
    integrity = bool(
        all(item["passed"] for item in auth.values())
        and source_reproduction
        and composition["additive_equivalence_passed"]
        and composition["metric_equivalence_passed"]
        and composition["zero_reproduction_passed"]
    )
    scientific = bool(integrity and composition["scientific_gate_passed"])
    route = cfg["routes"]["integrity_fail" if not integrity else ("pass" if scientific else "authority_fail")]
    selected = composition["selected"]
    payload = {
        "source_formal_reproduction": source_formal,
        "integrity_gate_passed": integrity,
        "scientific_gate_passed": scientific,
        "selected_candidate_index": int(selected["candidate_index"]),
        "selected_issue_task_step": int(selected["issue_task_step"]),
        "selected_sign": int(selected["sign"]),
        "selected_formal_pass_count": int(selected["formal_pass_count"]),
        "selected_repaired_failed_baseline_count": int(selected["repaired_failed_baseline_count"]),
        "selected_baseline_pass_regression_count": int(selected["baseline_pass_regression_count"]),
        "selected_failed_baseline_minimum_margin_gain": selected["failed_baseline_minimum_margin_gain"],
        "candidate_summaries": composition["candidate_summaries"],
        "candidate_ranking": composition["candidate_ranking"],
        "maximum_additive_algebra_abs_difference": composition["maximum_additive_algebra_abs_difference"],
        "maximum_formal_metric_abs_difference": composition["maximum_formal_metric_abs_difference"],
        "zero_correction_maximum_value_abs_difference": composition["zero_correction_maximum_value_abs_difference"],
        "route": route,
        "real_tsc_executed": False,
        "new_raw_count": 0,
    }
    primary = _read(primary_path)
    agreement = payload == primary.get("comparison_payload")
    result = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "audit_kind": "final_independent",
        "source_authentication": auth,
        "comparison_payload": payload,
        "primary_sha256": _sha(primary_path),
        "primary_exact_agreement": agreement,
        "passed": bool(integrity and agreement),
    }
    independent_path = output / "analysis/final_independent.json"
    _write(independent_path, result)
    if not result["passed"]:
        raise ValueError("independent R8R13 did not reproduce primary")
    final = copy.deepcopy(primary)
    final.update({
        "phase": "final",
        "primary_summary_sha256": _sha(primary_path),
        "independent_sha256": _sha(independent_path),
        "stage_manifest_sha256": _sha(output / "stage_manifest.json"),
    })
    _write(output / "analysis/final_report.json", final)
    _write(state_path, {
        "schema_version": 1,
        "stage": STAGE,
        "phase_status": "complete",
        "finished": True,
        "real_tsc_executed": False,
        "new_raw_count": 0,
        "formal_outcomes_opened": True,
        "stop_reason": "" if scientific else "measured_additive_authority_insufficient",
        "final_report_sha256": _sha(output / "analysis/final_report.json"),
        "final_independent_sha256": _sha(independent_path),
        "verdict": {"route": route, "passed": scientific},
    })
    return result


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
