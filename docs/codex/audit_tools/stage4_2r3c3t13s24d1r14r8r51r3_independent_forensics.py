#!/usr/bin/env python3
"""Structurally independent raw-algebra audit for R8R51R3."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence


STAGE = "Stage4.2R3c3T13S24D1R14R8R51R3"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r51r3_single_transport_return_hold_formal_authority_audit"
R51_ORIGINAL_ROUTE = "REDUCED_Q0_TRANSPORT_BRIDGE_Q0_GATE_INTEGRATION_EXECUTION_FAIL_STOP"


def _reject(value: str) -> Any:
    raise ValueError(f"non-finite JSON constant: {value}")


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=_reject)


def _gzip(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(stream, parse_constant=_reject)


def _save(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def _sha(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _inventory(directory: Path) -> dict[str, Any]:
    combined = hashlib.sha256()
    count = total = 0
    for item in sorted(directory.glob("*.json.gz"), key=lambda path: path.name):
        size = item.stat().st_size
        sha = _sha(item)
        combined.update(f"{item.name}\0{size}\0{sha}\n".encode())
        count += 1
        total += size
    return {"count": count, "bytes": total, "digest": combined.hexdigest()}


def _stage(run: Path, contract: Mapping[str, Any]) -> Path:
    output = run.expanduser().resolve() / str(contract["stage_directory"])
    if output.parent.name != contract["run_name"]:
        raise ValueError("R8R51R3 independent source run identity changed")
    return output


def _authenticate_r51r2(cfg: Mapping[str, Any], run: Path, project: Path) -> dict[str, Any]:
    contract = cfg["source_r51r2"]
    stage = _stage(run, contract)
    local = {
        "config": project
        / "configs/stage4_2r3c3t13s24d1r14r8r51r2_reduced_q0_transport_bridge_whole_pair_causal_model_preflight.json",
        "implementation": project
        / "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r8r51r2_reduced_q0_transport_bridge_whole_pair_causal_model_preflight.py",
        "independent_implementation": project
        / "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r51r2_independent_forensics.py",
    }
    for name, path in local.items():
        if not path.is_file() or _sha(path) != contract[f"{name}_sha256"]:
            raise ValueError(f"R8R51R3 independent R51R2 code changed: {name}")
    paths = {
        "primary_summary": stage / "analysis/primary_summary.json",
        "primary_detailed": stage / "analysis/primary_detailed.json",
        "independent": stage / "analysis/independent.json",
        "compact_audit": stage / "analysis/compact_audit.json",
        "final_report": stage / "analysis/final_report.json",
        "stage_state": stage / "stage_state.json",
        "stage_manifest": stage / "stage_manifest.json",
        "source_authentication": stage / "source_reference/source_authentication.json",
        "server_final_evidence": stage / "analysis/server_final_evidence.json",
    }
    hashes = {}
    for name, path in paths.items():
        if not path.is_file():
            raise ValueError(f"R8R51R3 independent R51R2 artifact missing: {name}")
        hashes[name] = _sha(path)
        if hashes[name] != contract[f"{name}_sha256"]:
            raise ValueError(f"R8R51R3 independent R51R2 artifact changed: {name}")
    final = _load(paths["final_report"])
    independent = _load(paths["independent"])
    state = _load(paths["stage_state"])
    evidence = _load(paths["server_final_evidence"])
    route = contract["required_route"]
    if (
        final.get("route") != route
        or final.get("passed") is not True
        or independent.get("audit_passed") is not True
        or independent.get("route") != route
        or state.get("finished") is not True
        or state.get("route") != route
        or evidence.get("passed") is not True
        or evidence.get("route") != route
        or int(evidence.get("new_tsc_count", -1)) != 0
        or int(evidence.get("new_raw_count", -1)) != 0
        or int(evidence.get("plant_step_count", -1)) != 0
    ):
        raise ValueError("R8R51R3 independent R51R2 result changed")
    return {"stage": str(stage), "hashes": hashes, "passed": True}


def _authenticate_sources(
    cfg: Mapping[str, Any], r51_run: Path, r7_run: Path, project: Path
) -> dict[str, Any]:
    c51 = cfg["source_r51r1"]
    c7 = cfg["source_r8r7"]
    stage51 = _stage(r51_run, c51)
    stage7 = _stage(r7_run, c7)
    code51 = {
        "config": project
        / "configs/stage4_2r3c3t13s24d1r14r8r51r1_reduced_q0_transport_bridge_q0_gate_integration_sentinel_370ms.json",
        "implementation": project
        / "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r8r51r1_reduced_q0_transport_bridge_q0_gate_integration_sentinel.py",
    }
    for name, path in code51.items():
        if not path.is_file() or _sha(path) != c51[f"{name}_sha256"]:
            raise ValueError(f"R8R51R3 independent R51R1 code changed: {name}")
    paths51 = {
        "raw_primary": stage51 / "analysis/raw_primary.json",
        "raw_independent": stage51 / "analysis/raw_independent.json",
        "hotfix_primary": stage51 / "analysis/q0_first_effect_reporting_hotfix_primary.json",
        "hotfix_independent": stage51
        / "analysis/q0_first_effect_reporting_hotfix_independent.json",
        "compact_audit": stage51
        / "analysis/q0_first_effect_reporting_hotfix_compact_audit.json",
        "final_report": stage51
        / "analysis/q0_first_effect_reporting_hotfix_final_report.json",
        "stage_state": stage51 / "stage_state.json",
        "stage_manifest": stage51 / "stage_manifest.json",
        "all_specs": stage51 / "specs/all_specs.json",
        "offline_construction": stage51 / "analysis/offline_construction.json",
    }
    for name, path in paths51.items():
        if not path.is_file() or _sha(path) != c51[f"{name}_sha256"]:
            raise ValueError(f"R8R51R3 independent R51R1 artifact changed: {name}")
    inventory51 = _inventory(stage51 / "raw")
    if inventory51 != {
        "count": int(c51["raw_count"]),
        "bytes": int(c51["raw_bytes"]),
        "digest": c51["raw_inventory_digest"],
    }:
        raise ValueError("R8R51R3 independent R51R1 raw inventory changed")
    raw_primary = _load(paths51["raw_primary"])
    final51 = _load(paths51["final_report"])
    if (
        raw_primary.get("route") != R51_ORIGINAL_ROUTE
        or int(raw_primary.get("strict_parse_count", -1)) != 208
        or int(raw_primary.get("runtime_success_count", -1)) != 208
        or int(raw_primary.get("full_horizon_count", -1)) != 208
        or final51.get("passed") is not True
        or final51.get("route") != c51["required_route"]
        or int(final51.get("corrected_numerical_equivalence_count", -1)) != 208
        or final51.get("raw_inventory") != {
            **inventory51,
            "rows": final51.get("raw_inventory", {}).get("rows", []),
        }
    ):
        raise ValueError("R8R51R3 independent R51R1 result changed")
    paths7 = {
        "all_specs": stage7 / "specs/all_specs.json",
        "baseline_specs": stage7 / "specs/baseline_specs.json",
        "baseline_raw_primary": stage7 / "analysis/baseline_raw_primary.json",
        "baseline_raw_independent": stage7 / "analysis/baseline_raw_independent.json",
        "final_report": stage7 / "analysis/final_report.json",
        "stage_manifest": stage7 / "stage_manifest.json",
        "stage_state": stage7 / "stage_state.json",
    }
    for name, path in paths7.items():
        if not path.is_file() or _sha(path) != c7[f"{name}_sha256"]:
            raise ValueError(f"R8R51R3 independent R8R7 artifact changed: {name}")
    inventory7 = _inventory(stage7 / "raw/baseline")
    if inventory7 != {
        "count": int(c7["baseline_raw_count"]),
        "bytes": int(c7["baseline_raw_bytes"]),
        "digest": c7["baseline_raw_digest"],
    }:
        raise ValueError("R8R51R3 independent R8R7 raw inventory changed")
    primary7 = _load(paths7["baseline_raw_primary"])
    independent7 = _load(paths7["baseline_raw_independent"])
    formal7 = primary7.get("formal_tracking_diagnostic_only", {})
    if (
        primary7.get("passed") is not True
        or int(primary7.get("passed_count", -1)) != 16
        or int(primary7.get("full_horizon_count", -1)) != 16
        or int(primary7.get("finite_count", -1)) != 16
        or int(formal7.get("evaluated", -1)) != 16
        or int(formal7.get("formal_contract_pass_count_diagnostic_only", -1)) != 6
        or independent7.get("passed") is not True
        or independent7.get("primary_outcome_agreement") is not True
    ):
        raise ValueError("R8R51R3 independent R8R7 result changed")
    return {
        "r51_stage": stage51,
        "r7_stage": stage7,
        "r51_inventory": inventory51,
        "r7_inventory": inventory7,
        "candidate_specs": _load(paths51["all_specs"]),
        "baseline_specs": _load(paths7["baseline_specs"]),
        "r51_raw_primary": raw_primary,
        "passed": True,
    }


def scalar_formal_metric(
    spec: Mapping[str, Any], trajectory: Sequence[Mapping[str, Any]], contract: Mapping[str, Any]
) -> dict[str, Any]:
    y = [tuple(float(row[key]) for key in ("R", "Z", "Ip")) for row in trajectory]
    if not y or any(not math.isfinite(value) for row in y for value in row):
        raise ValueError("R8R51R3 independent non-finite trajectory")
    horizon = len(y) - 1
    slew = float(spec["slew_scale"])
    weak = math.isclose(slew, 0.9, rel_tol=0.0, abs_tol=1e-12)
    expected_horizon = int(
        contract["weak_hold_through_step"] if weak else contract["normal_hold_through_step"]
    )
    if slew not in (0.9, 1.0, 1.1) or horizon != expected_horizon:
        raise ValueError("R8R51R3 independent formal horizon changed")
    base = tuple(map(float, contract["base_target_physical"]))
    target = (
        base[0] + float(spec["target_R_offset_m"]),
        base[1] + float(spec["target_Z_offset_m"]),
        base[2] + float(spec["target_Ip_offset_A"]),
    )
    error = [tuple(row[index] - target[index] for index in range(3)) for row in y]
    speed = [0.0]
    dt = float(contract["dt_s"])
    for current, previous in zip(y[1:], y[:-1]):
        speed.append(math.hypot((current[0] - previous[0]) / dt, (current[1] - previous[1]) / dt))
    first = int(
        contract["weak_arrival_first_step"] if weak else contract["normal_arrival_first_step"]
    )
    deadline = int(
        contract["weak_arrival_deadline_step"] if weak else contract["normal_arrival_deadline_step"]
    )
    tolerance = float(contract["formal_pass_tolerance"])
    endpoints = []
    for endpoint in range(first, deadline + 1):
        start = endpoint - int(contract["arrival_streak_steps"]) + 1
        sustained_box = max(abs(error[step][axis]) for step in range(start, horizon + 1) for axis in (0, 1))
        late_start = max(1, endpoint - int(contract["late_window_steps"]) + 1)
        late_rms = math.sqrt(math.fsum(speed[step] ** 2 for step in range(late_start, endpoint + 1)) / (endpoint - late_start + 1))
        post_rms = math.sqrt(math.fsum(speed[step] ** 2 for step in range(endpoint, horizon + 1)) / (horizon - endpoint + 1))
        sustained_ip = max(abs(error[step][2]) for step in range(start, horizon + 1))
        hard = (
            1.0 - sustained_box / float(contract["position_tolerance_m"]),
            1.0 - speed[endpoint] / float(contract["endpoint_speed_tolerance_m_per_s"]),
            1.0 - late_rms / float(contract["rms_speed_tolerance_m_per_s"]),
            1.0 - post_rms / float(contract["rms_speed_tolerance_m_per_s"]),
            1.0 - speed[horizon] / float(contract["endpoint_speed_tolerance_m_per_s"]),
            1.0 - sustained_ip / float(contract["ip_safety_tolerance_A"]),
        )
        hold = [error[step][2] for step in range(start, horizon + 1)]
        ip = (
            1.0 - abs(error[-1][2]) / float(contract["ip_terminal_abs_tolerance_A"]),
            1.0 - math.sqrt(math.fsum(value * value for value in hold) / len(hold)) / float(contract["ip_hold_rms_tolerance_A"]),
            1.0 - max(abs(value) for value in hold) / float(contract["ip_sustained_max_tolerance_A"]),
        )
        combined = (min(hard), *ip)
        endpoints.append(
            {
                "endpoint": endpoint,
                "arrival": int(round(1000.0 * endpoint * dt)),
                "passed": min(hard) >= -tolerance and min(ip) >= -tolerance,
                "minimum": min(combined),
                "mean": math.fsum(combined) / len(combined),
            }
        )
    passing = [row for row in endpoints if row["passed"]]
    chosen = max(
        passing if passing else endpoints,
        key=lambda row: (row["minimum"], row["mean"], -row["endpoint"]),
    )
    return {
        "formal_contract_pass": bool(chosen["passed"]),
        "formal_minimum_signed_margin": float(chosen["minimum"]),
        "formal_mean_signed_margin": float(chosen["mean"]),
        "formal_best_arrival_ms": int(chosen["arrival"]),
    }


def _rows(cfg: Mapping[str, Any], source: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    baselines: dict[str, Mapping[str, Any]] = {}
    for spec in source["baseline_specs"]:
        experiment_id = str(spec["experiment_id"])
        result = _gzip(source["r7_stage"] / "raw/baseline" / f"{experiment_id}.json.gz")
        trajectory = result.get("trajectory") or []
        if result.get("success") is not True or result.get("spec") != spec or len(trajectory) != int(spec["horizon_steps"]) + 1:
            raise ValueError(f"R8R51R3 independent baseline changed: {experiment_id}")
        baselines[experiment_id] = spec
        rows.append({
            "experiment_id": experiment_id,
            "partition": "baseline",
            "pair_id": str(spec["pair_id"]),
            "history_member": str(spec["history_member"]),
            "candidate_index": -1,
            "candidate_id": "baseline",
            **scalar_formal_metric(spec, trajectory, cfg["formal_contract"]),
        })
    old = {str(row["experiment_id"]): row for row in source["r51_raw_primary"]["rows"]}
    for spec in source["candidate_specs"]:
        experiment_id = str(spec["experiment_id"])
        result = _gzip(source["r51_stage"] / "raw" / f"{experiment_id}.json.gz")
        trajectory = result.get("trajectory") or []
        recorded = old.get(experiment_id)
        baseline_id = str(spec["source_r8r7_baseline_experiment_id"])
        baseline = baselines.get(baseline_id)
        if (
            recorded is None or baseline is None or result.get("success") is not True
            or result.get("spec") != spec or len(trajectory) != int(spec["horizon_steps"]) + 1
            or str(spec["pair_id"]) != str(baseline["pair_id"])
            or str(spec["history_member"]) != str(baseline["history_member"])
            or int(recorded.get("forbidden_trace_count", -1)) != 0
            or not all(recorded.get(key) is True for key in (
                "runtime_success", "full_horizon", "authentic_restart",
                "source_prefix_state_exact", "source_prefix_trace_exact",
                "source_trace_difference_wrapper_only", "calibration_exact", "q0_exact",
                "q0_offline_parity", "within_context_q0_prefix_exact", "candidate_exact",
                "event_sequence_exact", "event_gates_passed", "first_effect_at_issue_plus_one",
                "finite_response", "return_exact", "finite",
            ))
        ):
            raise ValueError(f"R8R51R3 independent candidate changed: {experiment_id}")
        rows.append({
            "experiment_id": experiment_id,
            "partition": "candidate",
            "pair_id": str(spec["pair_id"]),
            "history_member": str(spec["history_member"]),
            "candidate_index": int(spec["r8r51r1_candidate_index"]),
            "candidate_id": str(spec["r8r51r1_candidate_id"]),
            "source_baseline_experiment_id": baseline_id,
            **scalar_formal_metric(spec, trajectory, cfg["formal_contract"]),
        })
    rows.sort(key=lambda row: (
        row["pair_id"], row["history_member"], 0 if row["partition"] == "baseline" else 1,
        int(row["candidate_index"]), row["experiment_id"],
    ))
    groups: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["pair_id"], row["history_member"])].append(row)
    expected_ids = sorted(map(str, cfg["source_r51r1"]["candidate_ids"]))
    if (
        len(rows) != 224 or len(groups) != 16
        or any(len([row for row in group if row["partition"] == "baseline"]) != 1 for group in groups.values())
        or any(sorted(row["candidate_id"] for row in group if row["partition"] == "candidate") != expected_ids for group in groups.values())
    ):
        raise ValueError("R8R51R3 independent coverage changed")
    return rows


def _authority(rows: Sequence[Mapping[str, Any]], tolerance: float) -> dict[str, Any]:
    groups: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(str(row["pair_id"]), str(row["history_member"]))].append(row)
    baseline_pass = candidate_pass = candidate_context_pass = repairs = improved = oracle_pass = 0
    gains = []
    outcomes = []
    for key, group in sorted(groups.items()):
        baseline = next(row for row in group if row["partition"] == "baseline")
        candidates = sorted((row for row in group if row["partition"] == "candidate"), key=lambda row: int(row["candidate_index"]))
        best = max(candidates, key=lambda row: (
            float(row["formal_minimum_signed_margin"]),
            float(row["formal_mean_signed_margin"]),
            -int(row["candidate_index"]),
        ))
        oracle = max(enumerate([baseline, *candidates]), key=lambda item: (
            float(item[1]["formal_minimum_signed_margin"]),
            float(item[1]["formal_mean_signed_margin"]),
            -item[0],
        ))[1]
        gain = float(best["formal_minimum_signed_margin"]) - float(baseline["formal_minimum_signed_margin"])
        repair = not bool(baseline["formal_contract_pass"]) and any(bool(row["formal_contract_pass"]) for row in candidates)
        baseline_pass += int(bool(baseline["formal_contract_pass"]))
        candidate_pass += sum(int(bool(row["formal_contract_pass"])) for row in candidates)
        candidate_context_pass += int(any(bool(row["formal_contract_pass"]) for row in candidates))
        repairs += int(repair)
        improved += int(not bool(baseline["formal_contract_pass"]) and gain > tolerance)
        oracle_pass += int(bool(oracle["formal_contract_pass"]))
        gains.append(gain)
        outcomes.append({
            "pair_id": key[0], "history_member": key[1],
            "best_candidate_index": int(best["candidate_index"]),
            "best_candidate_id": str(best["candidate_id"]),
            "gain": gain, "repair": bool(repair),
            "oracle_partition": str(oracle["partition"]),
            "oracle_candidate_index": int(oracle["candidate_index"]),
            "oracle_candidate_id": str(oracle["candidate_id"]),
            "oracle_pass": bool(oracle["formal_contract_pass"]),
        })
    return {
        "context_count": len(groups),
        "baseline_formal_pass_count": baseline_pass,
        "candidate_formal_pass_count": candidate_pass,
        "candidate_formal_pass_context_count": candidate_context_pass,
        "failed_baseline_count": len(groups) - baseline_pass,
        "repaired_failed_baseline_count": repairs,
        "failed_baseline_strict_margin_improvement_count": improved,
        "measured_oracle_formal_pass_count": oracle_pass,
        "best_candidate_minimum_margin_gain_minimum": min(gains),
        "best_candidate_minimum_margin_gain_median": statistics.median(gains),
        "best_candidate_minimum_margin_gain_maximum": max(gains),
        "independent_context_outcome_digest": _digest(outcomes),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    project = Path(__file__).resolve().parents[3]
    cfg = _load(args.config.expanduser().resolve())
    output = args.run_dir.expanduser().resolve() / RUN_NAME
    primary_path = output / "analysis/primary_detailed.json"
    summary_path = output / "analysis/primary_summary.json"
    manifest_path = output / "stage_manifest.json"
    state_path = output / "stage_state.json"
    primary = _load(primary_path)
    summary = _load(summary_path)
    manifest = _load(manifest_path)
    state = _load(state_path)
    design = project / str(cfg["design_document"])
    if (
        manifest.get("config_sha256") != _sha(args.config.expanduser().resolve())
        or manifest.get("design_document_sha256") != cfg["design_document_sha256"]
        or not design.is_file()
        or _sha(design) != cfg["design_document_sha256"]
        or manifest.get("primary_detailed_sha256") != _sha(primary_path)
        or manifest.get("primary_summary_sha256") != _sha(summary_path)
        or summary.get("primary_detailed_sha256") != _sha(primary_path)
        or state.get("phase_status") != "primary_ready"
        or primary.get("stage") != STAGE
        or summary.get("stage") != STAGE
    ):
        raise ValueError("R8R51R3 independent primary/config identity changed")
    auth2 = _authenticate_r51r2(cfg, args.r51r2_run, project)
    source = _authenticate_sources(cfg, args.r51r1_run, args.r8r7_run, project)
    rows = _rows(cfg, source)
    tolerance = float(cfg["formal_contract"]["metric_equivalence_absolute_tolerance"])
    result = _authority(rows, tolerance)
    expected = {str(row["experiment_id"]): row for row in primary["formal_rows"]}
    discrete = len(expected) == len(rows)
    maximum = 0.0
    first = ""
    for row in rows:
        other = expected.get(str(row["experiment_id"]))
        if other is None:
            discrete = False
            first = first or str(row["experiment_id"])
            continue
        same = (
            row["partition"] == other["partition"]
            and row["pair_id"] == other["pair_id"]
            and row["history_member"] == other["history_member"]
            and int(row["candidate_index"]) == int(other["candidate_index"])
            and row["candidate_id"] == other["candidate_id"]
            and bool(row["formal_contract_pass"]) == bool(other["formal_contract_pass"])
            and int(row["formal_best_arrival_ms"]) == int(other["formal_best_arrival_ms"])
        )
        if not same:
            discrete = False
            first = first or str(row["experiment_id"])
        for key in ("formal_minimum_signed_margin", "formal_mean_signed_margin"):
            difference = abs(float(row[key]) - float(other[key]))
            maximum = max(maximum, difference)
            if difference > tolerance:
                first = first or f"{row['experiment_id']}:{key}"
    numerical = maximum <= tolerance
    compare_keys = (
        "context_count", "baseline_formal_pass_count", "candidate_formal_pass_count",
        "candidate_formal_pass_context_count", "failed_baseline_count",
        "repaired_failed_baseline_count", "failed_baseline_strict_margin_improvement_count",
        "measured_oracle_formal_pass_count",
    )
    outcome = all(result[key] == primary[key] for key in compare_keys)
    for key in (
        "best_candidate_minimum_margin_gain_minimum",
        "best_candidate_minimum_margin_gain_median",
        "best_candidate_minimum_margin_gain_maximum",
    ):
        difference = abs(float(result[key]) - float(primary[key]))
        maximum = max(maximum, difference)
        outcome = bool(outcome and difference <= tolerance)
    known = cfg["known_aggregate_contract"]
    integrity = bool(
        auth2["passed"] and source["passed"] and len(rows) == int(known["total_formal_row_count"])
        and result["context_count"] == int(known["context_count"])
        and result["baseline_formal_pass_count"] == int(known["baseline_formal_pass_count"])
        and result["failed_baseline_count"] == int(known["failed_baseline_count"])
        and discrete and numerical and outcome
    )
    gate = cfg["scientific_gate"]
    scientific = bool(
        integrity
        and result["repaired_failed_baseline_count"] >= int(gate["minimum_repaired_failed_baseline_count"])
        and result["measured_oracle_formal_pass_count"] >= int(gate["minimum_measured_oracle_formal_pass_count"])
    )
    route = cfg["routes"]["execution_fail" if not integrity else ("pass" if scientific else "authority_insufficient")]
    audit = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "independent",
        "source_r51r2_authentication": auth2,
        "source_r51r1_raw_inventory": source["r51_inventory"],
        "source_r8r7_baseline_inventory": source["r7_inventory"],
        "formal_row_count": len(rows),
        "independent_formal_metric_digest": _digest(rows),
        **result,
        "primary_discrete_agreement": discrete,
        "primary_numerical_agreement": numerical,
        "primary_outcome_agreement": outcome,
        "maximum_primary_numerical_difference": maximum,
        "comparison_absolute_tolerance": tolerance,
        "first_disagreement": first,
        "integrity_gate_passed": integrity,
        "scientific_gate_passed": scientific,
        "route": route,
        "audit_passed": integrity,
        **dict(cfg["execution_contract"]),
    }
    _save(output / "analysis/independent.json", audit)
    return audit


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--r51r2-run", type=Path, required=True)
    parser.add_argument("--r51r1-run", type=Path, required=True)
    parser.add_argument("--r8r7-run", type=Path, required=True)
    return parser


def main() -> None:
    print(json.dumps(run(_parser().parse_args()), indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
