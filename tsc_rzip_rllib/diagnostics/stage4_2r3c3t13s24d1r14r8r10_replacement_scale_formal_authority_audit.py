#!/usr/bin/env python3
"""Read-only R8R10 replacement-scale formal-authority audit."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import statistics
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification as r8,
)


STAGE = "Stage4.2R3c3T13S24D1R14R8R10"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r10_replacement_scale_formal_authority_audit"
IDENTITY = "replacement_scale_formal_authority_audit_v1"
ISSUE_STEPS = (14, 18, 22)
SIGNS = (-1, 1)


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
        rows.append((item.name, size, sha))
    return {
        "count": len(rows),
        "bytes": sum(row[1] for row in rows),
        "digest": digest.hexdigest(),
    }


def validate_config(cfg: Mapping[str, Any], *, project_root: Path) -> None:
    design = project_root / str(cfg["design_document"])
    rows = cfg["row_contract"]
    formal = cfg["formal_contract"]
    gate = cfg["scientific_gate"]
    execution = cfg["execution_contract"]
    scope = cfg["scientific_scope"]
    source4 = cfg["source_r4"]
    source6 = cfg["source_r6"]
    source8 = cfg["source_r8"]
    if (
        int(cfg.get("schema_version", -1)) != 1
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("run_name") != RUN_NAME
        or cfg.get("source_r8_config")
        != "configs/stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification_370ms.json"
        or not design.is_file()
        or _sha(design) != str(cfg["design_document_sha256"])
        or tuple(map(int, (rows["pair_count"], rows["context_count"], rows["rows_per_context"], rows["selected_row_count"])))
        != (12, 24, 13, 312)
        or tuple(map(int, rows["issue_task_steps"])) != ISSUE_STEPS
        or tuple(map(int, rows["signs"])) != SIGNS
        or int(rows["direction_index"]) != 0
        or float(rows["canonical_scale"]) != 1.0
        or float(rows["replacement_scale"]) != 1.5
        or str(rows["canonical_matrix_digest"])
        != "c8cd62c00c1f60b46312927789659657dc8cc35717533193433b0e398c1ec94c"
        or str(rows["replacement_matrix_digest"])
        != "69528f0e204b51847c1d2a7df428555a557454e9fa6bc76768d39e7cc5a90da8"
        or tuple((
            source4["stage_directory"], source4["required_route"],
            int(source4["raw_count"]), int(source4["raw_bytes"]),
            source4["raw_digest"], int(source4["spec_count"]),
            source4["spec_digest"], int(source4["formal_pass_count"]),
        )) != (
            "stage4_2r3c3t13s24d1r14r4_time_shifted_sign_split_sentinel",
            "TIME_SHIFTED_SIGN_SPLIT_SENTINEL_GEOMETRY_FAIL_REDESIGN_REQUIRED",
            200, 6285765,
            "44a7eb8e677f88f32c57a6be59273501e73f7657527371e1b59578a95c2ae7a9",
            200, "080a2df84c86801d76251853a165839e8db59f6614f6b2b446141b0691841059", 50,
        )
        or tuple((
            source6["stage_directory"], source6["required_route"],
            int(source6["raw_count"]), int(source6["raw_bytes"]),
            source6["raw_digest"], int(source6["spec_count"]),
            source6["spec_digest"], int(source6["formal_pass_count"]),
        )) != (
            "stage4_2r3c3t13s24d1r14r6_direction0_replacement_sentinel",
            "DIRECTION0_REPLACEMENT_SENTINEL_PASS_MODEL_FIT_DESIGN_REQUIRED",
            48, 1509679,
            "c743eff98395325e4da35a28d2e646aacffb00e678753ceb0faf4b86a64aeb83",
            48, "2390d89f7b83f6177e0403252fa246aa2b677fab39ce2dedda50c578de5d1883", 12,
        )
        or tuple((
            source8["stage_directory"], source8["required_route"],
            int(source8["training_raw_count"]), int(source8["training_raw_bytes"]),
            source8["training_raw_digest"], int(source8["all_spec_count"]),
            int(source8["training_spec_count"]), source8["spec_digest"],
            int(source8["training_formal_pass_count"]),
            int(source8["calibration_raw_count"]), int(source8["holdout_raw_count"]),
        )) != (
            "stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification",
            "PARTITIONED_BROAD_RESPONSE_TRAINING_MODEL_FAIL_STOP",
            624, 19725920,
            "b5de1cabe0bd47b0d3a3b26aff04714ca0c05653483cd4c92403dc5867eeb762",
            1248, 624, "9e85ecaa2f0c8ec010490dab4f001541f18f714980b6cb7070636372edd1d667",
            234, 0, 0,
        )
        or tuple(map(int, (
            formal["normal_arrival_deadline_step"], formal["normal_hold_through_step"],
            formal["weak_arrival_deadline_step"], formal["weak_hold_through_step"],
            formal["arrival_streak_steps"],
        ))) != (25, 35, 27, 37, 3)
        or tuple(map(float, (
            formal["position_tolerance_m"], formal["speed_tolerance_m_per_s"],
            formal["ip_tolerance_A"], formal["metric_equivalence_absolute_tolerance"],
        ))) != (0.03, 0.1, 10000.0, 1e-12)
        or bool(formal["arrival_deadline_expansion_allowed"])
        or int(gate["minimum_failed_baseline_count"]) != 1
        or int(gate["minimum_replacement_repair_count"]) != 1
        or int(gate["minimum_replacement_only_repair_count"]) != 1
        or not bool(gate["require_replacement_oracle_improves_baseline"])
        or not bool(gate["require_combined_oracle_improves_canonical"])
        or int(execution["new_raw_count"]) != 0
        or any(bool(execution[name]) for name in (
            "ray_executed", "gotsc_executed", "tsc_executed", "controller_executed"
        ))
        or int(execution["plant_steps_executed"]) != 0
        or not bool(execution["read_raw_in_place"])
        or not bool(execution["server_virtualenv_only"])
        or not bool(execution["direct_copy_only"])
        or bool(execution["local_archive_operations_allowed"])
        or cfg["routes"] != {
            "audit_fail": "REPLACEMENT_SCALE_AUTHORITY_SOURCE_OR_AUDIT_FAIL_NO_TSC",
            "authority_fail": "REPLACEMENT_SCALE_FORMAL_AUTHORITY_INSUFFICIENT_SUSTAINED_ACTION_REDESIGN_REQUIRED",
            "pass": "REPLACEMENT_SCALE_FORMAL_AUTHORITY_PRESENT_FRESH_SENTINEL_DESIGN_REQUIRED",
        }
        or any(bool(scope[name]) for name in (
            "retrospective_oracle_is_causal_selector", "real_mpc_executed",
            "gate_a_qualified", "source_trajectories_allowed_in_expert_dataset",
            "expert_data_allowed", "bc_dagger_or_rl_allowed",
            "global_plant_reachability_claimed",
        ))
    ):
        raise ValueError("R8R10 frozen design changed")


def _context(args: argparse.Namespace, cfg: Mapping[str, Any]) -> r8.Context:
    kwargs = {
        name: getattr(args, name)
        for name in (
            "source_s21_run", "source_s23r1_output", "source_s24_run",
            "source_d1r9_v1", "source_d1r9_v2", "source_d1r10_run",
            "source_d1r10_audit", "source_stage42r3b_run",
            "source_stage42r3c3_run", "source_stage42r3c3_bank_dir",
            "source_stage42r3c3t1_run", "source_stage42r3c3t1_audit_dir",
            "source_stage42r3c3t3_controller_bank", "q1_run", "q2_run",
            "q1_audit", "q2_audit", "r3b_server_audit", "r3b_snapshot_checks",
        )
    }
    return r8.load_config(
        (_root() / str(cfg["source_r8_config"])).resolve(),
        source_d1r11_run=args.source_d1r11_run,
        source_r2_run=args.source_r2_run,
        source_r4_run=args.source_r4_run,
        source_r6_run=args.source_r6_run,
        run_dir=args.r8_run,
        **kwargs,
    )


def _hashed(path: Path, expected: str, label: str) -> dict[str, Any]:
    if not path.is_file() or _sha(path) != expected:
        raise ValueError(f"R8R10 {label} changed")
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": expected}


def _authenticate_legacy(run: Path, contract: Mapping[str, Any], *, source: str) -> dict[str, Any]:
    stage = run / str(contract["stage_directory"])
    files = {
        "final": _hashed(stage / "analysis/final_result.json", str(contract["final_result_sha256"]), f"{source} final"),
        "independent": _hashed(run / "server_independent_forensics_v1.json", str(contract["independent_sha256"]), f"{source} independent"),
        "manifest": _hashed(stage / "stage_manifest.json", str(contract["stage_manifest_sha256"]), f"{source} manifest"),
        "state": _hashed(stage / "stage_state.json", str(contract["stage_state_sha256"]), f"{source} state"),
    }
    state = _read(stage / "stage_state.json")
    specs = _read(stage / "specs/sentinel_specs.json")
    raw = _inventory(stage / "raw")
    if (
        not state.get("finished")
        or state.get("verdict", {}).get("route") != contract["required_route"]
        or state.get("spec_digest") != contract["spec_digest"]
        or len(specs) != int(contract["spec_count"])
        or _digest(specs) != str(contract["spec_digest"])
        or raw != {
            "count": int(contract["raw_count"]),
            "bytes": int(contract["raw_bytes"]),
            "digest": str(contract["raw_digest"]),
        }
    ):
        raise ValueError(f"R8R10 {source} source contract changed")
    return {"passed": True, "stage": str(stage), "files": files, "raw_inventory": raw, "specs": specs}


def _authenticate_r8(run: Path, contract: Mapping[str, Any]) -> dict[str, Any]:
    stage = run / str(contract["stage_directory"])
    files = {
        "raw_primary": _hashed(stage / "analysis/training_raw_primary.json", str(contract["raw_primary_sha256"]), "R8 raw primary"),
        "raw_independent": _hashed(stage / "analysis/training_raw_independent.json", str(contract["raw_independent_sha256"]), "R8 raw independent"),
        "manifest": _hashed(stage / "stage_manifest.json", str(contract["stage_manifest_sha256"]), "R8 manifest"),
        "state": _hashed(stage / "stage_state.json", str(contract["stage_state_sha256"]), "R8 state"),
    }
    state = _read(stage / "stage_state.json")
    specs = _read(stage / "specs/all_specs.json")
    training = [row for row in specs if str(row["partition"]) == "training"]
    raw = _inventory(stage / "raw/training")
    calibration = _inventory(stage / "raw/calibration")
    holdout = _inventory(stage / "raw/holdout")
    if (
        state.get("phase_status") != "training_model_failed"
        or state.get("verdict", {}).get("route") != contract["required_route"]
        or state.get("spec_digest") != contract["spec_digest"]
        or bool(state.get("heldout_outcomes_opened"))
        or len(specs) != int(contract["all_spec_count"])
        or len(training) != int(contract["training_spec_count"])
        or _digest(specs) != str(contract["spec_digest"])
        or raw != {
            "count": int(contract["training_raw_count"]),
            "bytes": int(contract["training_raw_bytes"]),
            "digest": str(contract["training_raw_digest"]),
        }
        or calibration["count"] != int(contract["calibration_raw_count"])
        or holdout["count"] != int(contract["holdout_raw_count"])
    ):
        raise ValueError("R8R10 R8 source contract changed")
    return {
        "passed": True, "stage": str(stage), "files": files,
        "raw_inventory": raw, "calibration_inventory": calibration,
        "holdout_inventory": holdout, "specs": training,
    }


def _normalize_spec(source: str, spec: Mapping[str, Any]) -> dict[str, Any] | None:
    base = {
        "source_bank": source,
        "experiment_id": str(spec["experiment_id"]),
        "pair_id": str(spec["pair_id"]),
        "history_member": str(spec["history_member"]),
    }
    if source == "R4":
        role = str(spec["d1r14r4_role"])
        if role == "baseline":
            return {**base, "role": "baseline", "action_scale": 0.0, "issue_task_step": -1, "sign": 0}
        issue = int(spec["d1r14r4_issue_task_step"])
        if role == "signed_probe" and int(spec["d1r14r4_direction_index"]) == 0 and issue in ISSUE_STEPS:
            return {**base, "role": "canonical", "action_scale": 1.0, "issue_task_step": issue, "sign": int(spec["d1r14r4_sign"])}
        return None
    if source == "R6":
        if str(spec["d1r14r6_role"]) != "signed_probe" or int(spec["d1r14r6_direction_index"]) != 0:
            return None
        issue = int(spec["d1r14r6_issue_task_step"])
        if issue not in ISSUE_STEPS:
            return None
        return {**base, "role": "replacement", "action_scale": 1.5, "issue_task_step": issue, "sign": int(spec["d1r14r6_sign"])}
    role = str(spec["d1r14r8_role"])
    if role == "baseline":
        return {**base, "role": "baseline", "action_scale": 0.0, "issue_task_step": -1, "sign": 0}
    issue = int(spec["d1r14r8_issue_task_step"])
    if role in {"canonical", "replacement"} and int(spec["d1r14r8_direction_index"]) == 0 and issue in ISSUE_STEPS:
        return {
            **base, "role": role, "action_scale": float(spec["d1r14r8_action_scale"]),
            "issue_task_step": issue, "sign": int(spec["d1r14r8_sign"]),
        }
    return None


def _evaluate_source(
    ctx: r8.Context,
    *,
    source: str,
    specs: Sequence[Mapping[str, Any]],
    raw_dir: Path,
    tolerance: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    evaluators, _ = r8.d1r11._formal_callback(ctx.d1r11_ctx, specs)
    selected = []
    formal_pass_count = 0
    maximum_difference = 0.0
    pass_agreement = arrival_agreement = True
    strict_count = 0
    for spec in specs:
        experiment_id = str(spec["experiment_id"])
        result = _read_gz(raw_dir / f"{experiment_id}.json.gz")
        trajectory = result.get("trajectory") or []
        if result.get("success") is not True or len(trajectory) != int(spec["horizon_steps"]) + 1:
            raise ValueError(f"R8R10 incomplete {source} raw: {experiment_id}")
        rzi = np.asarray([[row["R"], row["Z"], row["Ip"]] for row in trajectory], dtype=float)
        if rzi.shape != (len(trajectory), 3) or not np.all(np.isfinite(rzi)):
            raise ValueError(f"R8R10 non-finite {source} raw: {experiment_id}")
        strict_count += 1
        evaluator = evaluators[experiment_id]
        compact = evaluator.evaluate(rzi)
        formal_pass_count += bool(compact["formal_contract_pass"])
        normalized = _normalize_spec(source, spec)
        if normalized is None:
            continue
        existing = evaluator.exact_existing_metric(result, rzi)
        pass_agreement = bool(pass_agreement and compact["formal_contract_pass"] == existing["formal_contract_pass"])
        arrival_agreement = bool(arrival_agreement and int(compact["formal_best_arrival_ms"]) == int(existing["formal_best_arrival_ms"]))
        for name in ("formal_minimum_signed_margin", "formal_mean_signed_margin"):
            maximum_difference = max(maximum_difference, abs(float(compact[name]) - float(existing[name])))
        selected.append({
            **normalized,
            "formal_contract_pass": bool(compact["formal_contract_pass"]),
            "formal_minimum_signed_margin": float(compact["formal_minimum_signed_margin"]),
            "formal_mean_signed_margin": float(compact["formal_mean_signed_margin"]),
            "formal_best_arrival_ms": int(compact["formal_best_arrival_ms"]),
        })
    return selected, {
        "source_bank": source,
        "strict_raw_count": strict_count,
        "formal_pass_count": formal_pass_count,
        "selected_row_count": len(selected),
        "selected_pass_agreement": pass_agreement,
        "selected_arrival_agreement": arrival_agreement,
        "selected_maximum_margin_abs_difference": maximum_difference,
        "selected_metric_equivalence_passed": bool(pass_agreement and arrival_agreement and maximum_difference <= tolerance),
    }


def _candidate_key(row: Mapping[str, Any]) -> tuple[float, float, int, int, float]:
    issue = int(row["issue_task_step"])
    sign_order = 0 if int(row["sign"]) == -1 else 1
    return (
        float(row["formal_minimum_signed_margin"]),
        float(row["formal_mean_signed_margin"]),
        -issue,
        -sign_order,
        -float(row["action_scale"]),
    )


def _best(rows: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    return max(rows, key=_candidate_key)


def _statistics(values: Sequence[float]) -> dict[str, float | None]:
    if not values:
        return {"minimum": None, "median": None, "maximum": None}
    return {
        "minimum": min(map(float, values)),
        "median": statistics.median(map(float, values)),
        "maximum": max(map(float, values)),
    }


def _strata(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    dimensions = {
        "source_bank": lambda row: str(row["source_bank"]),
        "prefix_family": lambda row: str(row["pair_id"]).split("_", 1)[0],
        "history_member": lambda row: str(row["history_member"]),
        "role": lambda row: str(row["role"]),
        "issue_task_step": lambda row: str(row["issue_task_step"]),
        "sign": lambda row: str(row["sign"]),
    }
    for name, key in dimensions.items():
        total = Counter(key(row) for row in rows)
        passed = Counter(key(row) for row in rows if bool(row["formal_contract_pass"]))
        output[name] = {
            value: {"count": count, "formal_pass_count": passed[value]}
            for value, count in sorted(total.items())
        }
    return output


def authority(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    groups: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(str(row["pair_id"]), str(row["history_member"]))].append(row)
    contexts = []
    matched = []
    expected_members = {(issue, sign) for issue in ISSUE_STEPS for sign in SIGNS}
    for key, group in sorted(groups.items()):
        baseline = [row for row in group if row["role"] == "baseline"]
        canonical = [row for row in group if row["role"] == "canonical"]
        replacement = [row for row in group if row["role"] == "replacement"]
        cmap = {(int(row["issue_task_step"]), int(row["sign"])): row for row in canonical}
        rmap = {(int(row["issue_task_step"]), int(row["sign"])): row for row in replacement}
        if len(baseline) != 1 or len(canonical) != 6 or len(replacement) != 6 or set(cmap) != expected_members or set(rmap) != expected_members:
            raise ValueError(f"R8R10 context coverage changed: {key}")
        base = baseline[0]
        best_c = _best(canonical)
        best_r = _best(replacement)
        oracle_c = _best([base, *canonical])
        oracle_r = _best([base, *replacement])
        oracle_all = _best([base, *canonical, *replacement])
        c_repair = bool(not base["formal_contract_pass"] and any(row["formal_contract_pass"] for row in canonical))
        r_repair = bool(not base["formal_contract_pass"] and any(row["formal_contract_pass"] for row in replacement))
        for member in sorted(expected_members):
            matched.append({
                "pair_id": key[0], "history_member": key[1],
                "issue_task_step": member[0], "sign": member[1],
                "replacement_minus_canonical_minimum_margin": float(rmap[member]["formal_minimum_signed_margin"]) - float(cmap[member]["formal_minimum_signed_margin"]),
                "replacement_minus_canonical_mean_margin": float(rmap[member]["formal_mean_signed_margin"]) - float(cmap[member]["formal_mean_signed_margin"]),
            })
        contexts.append({
            "pair_id": key[0], "history_member": key[1], "baseline": dict(base),
            "canonical": [dict(cmap[item]) for item in sorted(cmap)],
            "replacement": [dict(rmap[item]) for item in sorted(rmap)],
            "best_canonical": dict(best_c), "best_replacement": dict(best_r),
            "canonical_minimum_margin_gain": float(best_c["formal_minimum_signed_margin"]) - float(base["formal_minimum_signed_margin"]),
            "replacement_minimum_margin_gain": float(best_r["formal_minimum_signed_margin"]) - float(base["formal_minimum_signed_margin"]),
            "canonical_repair": c_repair, "replacement_repair": r_repair,
            "replacement_only_repair": bool(r_repair and not c_repair),
            "canonical_oracle": dict(oracle_c), "replacement_oracle": dict(oracle_r),
            "combined_oracle": dict(oracle_all),
        })
    baseline_pass = sum(row["baseline"]["formal_contract_pass"] for row in contexts)
    failed = len(contexts) - baseline_pass
    canonical_repairs = sum(row["canonical_repair"] for row in contexts)
    replacement_repairs = sum(row["replacement_repair"] for row in contexts)
    replacement_only = sum(row["replacement_only_repair"] for row in contexts)
    c_oracle = sum(row["canonical_oracle"]["formal_contract_pass"] for row in contexts)
    r_oracle = sum(row["replacement_oracle"]["formal_contract_pass"] for row in contexts)
    all_oracle = sum(row["combined_oracle"]["formal_contract_pass"] for row in contexts)
    failed_contexts = [row for row in contexts if not row["baseline"]["formal_contract_pass"]]
    c_gains = [float(row["canonical_minimum_margin_gain"]) for row in failed_contexts]
    r_gains = [float(row["replacement_minimum_margin_gain"]) for row in failed_contexts]
    deltas = [float(row["replacement_minus_canonical_minimum_margin"]) for row in matched]
    return {
        "context_rows": contexts, "matched_scale_rows": matched, "strata": _strata(rows),
        "pair_count": len({row["pair_id"] for row in contexts}),
        "context_count": len(contexts), "selected_row_count": len(rows),
        "baseline_formal_pass_count": baseline_pass, "failed_baseline_count": failed,
        "canonical_formal_pass_trajectory_count": sum(row["formal_contract_pass"] for row in rows if row["role"] == "canonical"),
        "replacement_formal_pass_trajectory_count": sum(row["formal_contract_pass"] for row in rows if row["role"] == "replacement"),
        "canonical_repaired_failed_baseline_count": canonical_repairs,
        "replacement_repaired_failed_baseline_count": replacement_repairs,
        "replacement_only_repaired_failed_baseline_count": replacement_only,
        "canonical_oracle_formal_pass_count": c_oracle,
        "replacement_oracle_formal_pass_count": r_oracle,
        "combined_oracle_formal_pass_count": all_oracle,
        "failed_baseline_canonical_minimum_margin_gain": _statistics(c_gains),
        "failed_baseline_replacement_minimum_margin_gain": _statistics(r_gains),
        "matched_replacement_minus_canonical_minimum_margin": _statistics(deltas),
        "failed_baseline_canonical_strict_improvement_count": sum(value > 1e-12 for value in c_gains),
        "failed_baseline_replacement_strict_improvement_count": sum(value > 1e-12 for value in r_gains),
        "matched_replacement_strictly_better_count": sum(value > 1e-12 for value in deltas),
    }


def _compact_authority(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key not in {"context_rows", "matched_scale_rows", "strata"}}


def run(args: argparse.Namespace) -> dict[str, Any]:
    config_path = args.config.expanduser().resolve()
    cfg = _read(config_path)
    validate_config(cfg, project_root=_root())
    output = args.run_dir.expanduser().resolve() / RUN_NAME
    if output.exists() and any(output.iterdir()):
        raise ValueError("R8R10 output must be absent or empty")
    ctx = _context(args, cfg)
    auth4 = _authenticate_legacy(args.source_r4_run.expanduser().resolve(), cfg["source_r4"], source="R4")
    auth6 = _authenticate_legacy(args.source_r6_run.expanduser().resolve(), cfg["source_r6"], source="R6")
    auth8 = _authenticate_r8(args.r8_run.expanduser().resolve(), cfg["source_r8"])
    tolerance = float(cfg["formal_contract"]["metric_equivalence_absolute_tolerance"])
    selected4, formal4 = _evaluate_source(ctx, source="R4", specs=auth4.pop("specs"), raw_dir=Path(auth4["stage"]) / "raw", tolerance=tolerance)
    selected6, formal6 = _evaluate_source(ctx, source="R6", specs=auth6.pop("specs"), raw_dir=Path(auth6["stage"]) / "raw", tolerance=tolerance)
    selected8, formal8 = _evaluate_source(ctx, source="R8", specs=auth8.pop("specs"), raw_dir=Path(auth8["stage"]) / "raw/training", tolerance=tolerance)
    rows = [*selected4, *selected6, *selected8]
    result = authority(rows)
    source_formal = {"R4": formal4, "R6": formal6, "R8": formal8}
    known = bool(
        formal4["formal_pass_count"] == int(cfg["source_r4"]["formal_pass_count"])
        and formal6["formal_pass_count"] == int(cfg["source_r6"]["formal_pass_count"])
        and formal8["formal_pass_count"] == int(cfg["source_r8"]["training_formal_pass_count"])
    )
    equivalence = {
        "row_count": sum(item["selected_row_count"] for item in source_formal.values()),
        "pass_agreement": all(item["selected_pass_agreement"] for item in source_formal.values()),
        "arrival_agreement": all(item["selected_arrival_agreement"] for item in source_formal.values()),
        "maximum_margin_abs_difference": max(item["selected_maximum_margin_abs_difference"] for item in source_formal.values()),
        "absolute_tolerance": tolerance,
    }
    equivalence["passed"] = bool(
        equivalence["row_count"] == int(cfg["row_contract"]["selected_row_count"])
        and equivalence["pass_agreement"] and equivalence["arrival_agreement"]
        and equivalence["maximum_margin_abs_difference"] <= tolerance
    )
    integrity = bool(
        auth4["passed"] and auth6["passed"] and auth8["passed"]
        and known and equivalence["passed"]
        and result["pair_count"] == int(cfg["row_contract"]["pair_count"])
        and result["context_count"] == int(cfg["row_contract"]["context_count"])
        and result["selected_row_count"] == int(cfg["row_contract"]["selected_row_count"])
        and auth8["calibration_inventory"]["count"] == 0
        and auth8["holdout_inventory"]["count"] == 0
    )
    gate = cfg["scientific_gate"]
    scientific = bool(
        integrity
        and result["failed_baseline_count"] >= int(gate["minimum_failed_baseline_count"])
        and result["replacement_repaired_failed_baseline_count"] >= int(gate["minimum_replacement_repair_count"])
        and result["replacement_only_repaired_failed_baseline_count"] >= int(gate["minimum_replacement_only_repair_count"])
        and result["replacement_oracle_formal_pass_count"] > result["baseline_formal_pass_count"]
        and result["combined_oracle_formal_pass_count"] > result["canonical_oracle_formal_pass_count"]
    )
    route = cfg["routes"]["audit_fail" if not integrity else ("pass" if scientific else "authority_fail")]
    detailed = {
        "schema_version": 1, "stage": STAGE, "identity": IDENTITY,
        "source_authentication": {"R4": auth4, "R6": auth6, "R8": auth8},
        "source_formal_reproduction": source_formal,
        "known_source_aggregate_reproduction_passed": known,
        "formal_metric_equivalence": equivalence, "formal_rows": rows,
        "authority": result, "integrity_gate_passed": integrity,
        "scientific_gate_passed": scientific, "route": route,
        "real_tsc_executed": False, "new_raw_count": 0, "passed": scientific,
    }
    output.mkdir(parents=True, exist_ok=True)
    analysis = output / "analysis"
    _write(analysis / "primary_detailed.json", detailed)
    summary = {
        "schema_version": 1, "stage": STAGE, "identity": IDENTITY,
        "source_authenticated": {"R4": auth4["passed"], "R6": auth6["passed"], "R8": auth8["passed"]},
        "source_formal_reproduction": source_formal,
        "known_source_aggregate_reproduction_passed": known,
        "formal_metric_equivalence": equivalence,
        **_compact_authority(result),
        "integrity_gate_passed": integrity, "scientific_gate_passed": scientific,
        "primary_detailed_sha256": _sha(analysis / "primary_detailed.json"),
        "route": route, "real_tsc_executed": False, "new_raw_count": 0,
        "passed": scientific,
    }
    _write(analysis / "primary_summary.json", summary)
    manifest = {
        "schema_version": 1, "stage": STAGE, "identity": IDENTITY,
        "config_path": str(config_path), "config_sha256": _sha(config_path),
        "design_document_sha256": str(cfg["design_document_sha256"]),
        "source_r4_run": str(args.source_r4_run.expanduser().resolve()),
        "source_r6_run": str(args.source_r6_run.expanduser().resolve()),
        "source_r8_run": str(args.r8_run.expanduser().resolve()),
        "primary_detailed_sha256": summary["primary_detailed_sha256"],
        "primary_summary_sha256": _sha(analysis / "primary_summary.json"),
        "real_tsc_executed": False, "new_raw_count": 0,
    }
    _write(output / "stage_manifest.json", manifest)
    _write(output / "stage_state.json", {
        "schema_version": 1, "stage": STAGE,
        "phase_status": "complete" if integrity else "audit_failed",
        "finished": True, "real_tsc_executed": False, "new_raw_count": 0,
        "stop_reason": "" if scientific else ("replacement_scale_formal_authority_insufficient" if integrity else "source_or_audit_failed"),
        "verdict": {"route": route, "passed": scientific},
    })
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "config", "run-dir", "r8-run", "source-d1r11-run", "source-r2-run",
        "source-r4-run", "source-r6-run", "source-s21-run", "source-s23r1-output",
        "source-s24-run", "source-d1r9-v1", "source-d1r9-v2", "source-d1r10-run",
        "source-d1r10-audit", "source-stage42r3b-run", "source-stage42r3c3-run",
        "source-stage42r3c3-bank-dir", "source-stage42r3c3t1-run",
        "source-stage42r3c3t1-audit-dir", "source-stage42r3c3t3-controller-bank",
        "q1-run", "q2-run", "q1-audit", "q2-audit", "r3b-server-audit",
        "r3b-snapshot-checks",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    return parser


def main() -> None:
    print(json.dumps(run(_parser().parse_args()), indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
