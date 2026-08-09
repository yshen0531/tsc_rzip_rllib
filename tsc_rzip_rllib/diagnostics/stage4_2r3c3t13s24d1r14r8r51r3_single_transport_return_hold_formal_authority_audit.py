#!/usr/bin/env python3
"""Frozen zero-TSC full-horizon authority audit for R8R51R3."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r51r2_reduced_q0_transport_bridge_whole_pair_causal_model_preflight
    as r51r2,
)


STAGE = "Stage4.2R3c3T13S24D1R14R8R51R3"
IDENTITY = "single_transport_return_hold_formal_authority_audit_v1"
PRIMARY_DETAIL = "primary_detailed.json"
PRIMARY_SUMMARY = "primary_summary.json"
INDEPENDENT = "independent.json"


def _reject_constant(value: str) -> Any:
    raise ValueError(f"non-finite JSON constant: {value}")


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=_reject_constant)


def _read_gzip(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(stream, parse_constant=_reject_constant)


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
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode(
            "utf-8"
        )
    ).hexdigest()


def validate_config(cfg: Mapping[str, Any], project: Path) -> None:
    formal = cfg.get("formal_contract", {})
    known = cfg.get("known_aggregate_contract", {})
    gate = cfg.get("scientific_gate", {})
    execution = cfg.get("execution_contract", {})
    scope = cfg.get("scientific_scope", {})
    routes = cfg.get("routes", {})
    expected_routes = {
        "source_blocked": "REDUCED_Q0_TRANSPORT_BRIDGE_R51R3_FORMAL_AUTHORITY_AUDIT_BLOCKED_BY_SOURCE",
        "execution_fail": "REDUCED_Q0_TRANSPORT_BRIDGE_R51R3_FORMAL_AUTHORITY_AUDIT_EXECUTION_FAIL_STOP",
        "authority_insufficient": "REDUCED_Q0_TRANSPORT_BRIDGE_R51R3_SINGLE_TRANSPORT_RETURN_HOLD_AUTHORITY_INSUFFICIENT_SEQUENTIAL_MODEL_REQUIRED",
        "pass": "REDUCED_Q0_TRANSPORT_BRIDGE_R51R3_FORMAL_AUTHORITY_PRESENT_MODEL_SELECTED_CONTROLLER_PREFLIGHT_REQUIRED",
    }
    design = project / str(cfg.get("design_document", ""))
    source_hashes = [
        value
        for section in ("source_r51r2", "source_r51r1", "source_r8r7")
        for key, value in cfg.get(section, {}).items()
        if key.endswith("sha256") or key.endswith("digest")
    ]
    if (
        int(cfg.get("schema_version", -1)) != 1
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("run_name")
        != "stage4_2r3c3t13s24d1r14r8r51r3_single_transport_return_hold_formal_authority_audit"
        or cfg.get("package_revision")
        != "r42r3c3t13s24d1r14r8r51r3_formal_authority_audit_v1"
        or not design.is_file()
        or _sha(design) != cfg.get("design_document_sha256")
        or not source_hashes
        or any(not isinstance(item, str) or len(item) != 64 for item in source_hashes)
        or tuple(map(float, formal.get("base_target_physical", ())))
        != (0.75, 0.0, 29779.724)
        or float(formal.get("dt_s", -1.0)) != 0.01
        or tuple(
            int(formal.get(key, -1))
            for key in (
                "normal_arrival_first_step",
                "normal_arrival_deadline_step",
                "normal_hold_through_step",
                "weak_arrival_first_step",
                "weak_arrival_deadline_step",
                "weak_hold_through_step",
            )
        )
        != (12, 25, 35, 12, 27, 37)
        or tuple(
            float(formal.get(key, -1.0))
            for key in (
                "position_tolerance_m",
                "endpoint_speed_tolerance_m_per_s",
                "rms_speed_tolerance_m_per_s",
                "ip_safety_tolerance_A",
                "ip_terminal_abs_tolerance_A",
                "ip_hold_rms_tolerance_A",
                "ip_sustained_max_tolerance_A",
                "formal_pass_tolerance",
                "metric_equivalence_absolute_tolerance",
            )
        )
        != (0.03, 0.1, 0.1, 10000.0, 2000.0, 2400.0, 4000.0, 1e-12, 1e-12)
        or int(formal.get("late_window_steps", -1)) != 4
        or int(formal.get("arrival_streak_steps", -1)) != 3
        or bool(formal.get("arrival_deadline_expansion_allowed", True))
        or tuple(
            int(known.get(key, -1))
            for key in (
                "context_count",
                "baseline_trajectory_count",
                "candidate_trajectory_count",
                "total_formal_row_count",
                "candidates_per_context",
                "baseline_formal_pass_count",
                "failed_baseline_count",
            )
        )
        != (16, 16, 208, 224, 13, 6, 10)
        or int(gate.get("minimum_repaired_failed_baseline_count", -1)) != 1
        or int(gate.get("minimum_measured_oracle_formal_pass_count", -1)) != 7
        or routes != expected_routes
        or any(int(execution.get(key, -1)) != 0 for key in (
            "new_tsc_count",
            "new_raw_count",
            "snapshot_count",
            "controller_execution_count",
            "plant_step_count",
            "model_fit_count",
            "model_selection_count",
            "optimization_count",
        ))
        or not bool(execution.get("read_raw_in_place"))
        or not bool(execution.get("server_virtualenv_only"))
        or not bool(execution.get("direct_copy_only"))
        or bool(execution.get("local_archive_operations_allowed"))
        or any(bool(scope.get(key)) for key in (
            "measured_oracle_is_causal_selector",
            "real_controller_or_mpc_executed",
            "gate_a_qualified",
            "all_source_trajectories_allowed_in_expert_dataset",
            "expert_data_allowed",
            "bc_dagger_or_rl_allowed",
            "global_plant_reachability_claimed",
        ))
    ):
        raise ValueError("R8R51R3 frozen design changed")


def _source_r51r2_paths(stage: Path) -> dict[str, Path]:
    return {
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


def authenticate_r51r2(
    cfg: Mapping[str, Any], source_run: Path, project: Path
) -> dict[str, Any]:
    contract = cfg["source_r51r2"]
    stage = source_run.expanduser().resolve() / str(contract["stage_directory"])
    if stage.parent.name != contract["run_name"]:
        raise ValueError("R8R51R3 R51R2 run identity changed")
    code_paths = {
        "config": project
        / "configs/stage4_2r3c3t13s24d1r14r8r51r2_reduced_q0_transport_bridge_whole_pair_causal_model_preflight.json",
        "implementation": project
        / "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r8r51r2_reduced_q0_transport_bridge_whole_pair_causal_model_preflight.py",
        "independent_implementation": project
        / "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r51r2_independent_forensics.py",
    }
    for name, path in code_paths.items():
        if not path.is_file() or _sha(path) != contract[f"{name}_sha256"]:
            raise ValueError(f"R8R51R3 R51R2 source code changed: {name}")
    paths = _source_r51r2_paths(stage)
    hashes = {}
    for name, path in paths.items():
        if not path.is_file():
            raise ValueError(f"R8R51R3 R51R2 artifact missing: {name}")
        hashes[name] = _sha(path)
        if hashes[name] != contract[f"{name}_sha256"]:
            raise ValueError(f"R8R51R3 R51R2 artifact changed: {name}")
    summary = _read(paths["primary_summary"])
    independent = _read(paths["independent"])
    final = _read(paths["final_report"])
    state = _read(paths["stage_state"])
    manifest = _read(paths["stage_manifest"])
    evidence = _read(paths["server_final_evidence"])
    route = contract["required_route"]
    if (
        summary.get("route") != route
        or summary.get("scientific_gate_passed") is not True
        or int(summary.get("prediction_coverage_count", -1)) != 208
        or int(summary.get("point_error_pass_count", -1)) != 208
        or int(summary.get("containment_pass_count", -1)) != 208
        or int(summary.get("tube_cap_fold_pass_count", -1)) != 8
        or independent.get("audit_passed") is not True
        or independent.get("route") != route
        or final.get("passed") is not True
        or final.get("route") != route
        or state.get("finished") is not True
        or state.get("route") != route
        or manifest.get("finished") is not True
        or evidence.get("passed") is not True
        or evidence.get("route") != route
        or any(int(evidence.get(key, -1)) != 0 for key in (
            "new_tsc_count", "new_raw_count", "snapshot_count",
            "controller_execution_count", "plant_step_count", "model_selection_count"
        ))
    ):
        raise ValueError("R8R51R3 R51R2 final source result changed")
    return {"stage": str(stage), "hashes": hashes, "passed": True}


def authenticate_sources(
    cfg: Mapping[str, Any], r51r1_run: Path, r8r7_run: Path
) -> dict[str, Any]:
    source = r51r2.authenticate_sources(cfg, r51r1_run, r8r7_run)
    r7_stage = Path(source["r7_stage"])
    paths = {
        "baseline_raw_primary": r7_stage / "analysis/baseline_raw_primary.json",
        "baseline_raw_independent": r7_stage
        / "analysis/baseline_raw_independent.json",
    }
    for name, path in paths.items():
        if not path.is_file() or _sha(path) != cfg["source_r8r7"][f"{name}_sha256"]:
            raise ValueError(f"R8R51R3 R8R7 baseline audit changed: {name}")
    primary = _read(paths["baseline_raw_primary"])
    independent = _read(paths["baseline_raw_independent"])
    formal = primary.get("formal_tracking_diagnostic_only", {})
    if (
        primary.get("passed") is not True
        or int(primary.get("passed_count", -1)) != 16
        or int(primary.get("full_horizon_count", -1)) != 16
        or int(primary.get("finite_count", -1)) != 16
        or int(primary.get("forbidden_trace_count", -1)) != 0
        or int(formal.get("evaluated", -1)) != 16
        or int(formal.get("formal_contract_pass_count_diagnostic_only", -1)) != 6
        or independent.get("passed") is not True
        or independent.get("primary_outcome_agreement") is not True
    ):
        raise ValueError("R8R51R3 R8R7 baseline integrity changed")
    source["r8r7_baseline_audit_hashes"] = {
        name: _sha(path) for name, path in paths.items()
    }
    return source


def formal_metric(
    spec: Mapping[str, Any], trajectory: Sequence[Mapping[str, Any]], contract: Mapping[str, Any]
) -> dict[str, Any]:
    y = np.asarray(
        [[row["R"], row["Z"], row["Ip"]] for row in trajectory], dtype=float
    )
    horizon = len(y) - 1
    slew = float(spec["slew_scale"])
    weak = abs(slew - 0.9) <= 1e-12
    expected_horizon = int(
        contract["weak_hold_through_step"] if weak else contract["normal_hold_through_step"]
    )
    if slew not in (0.9, 1.0, 1.1) or horizon != expected_horizon or not np.all(np.isfinite(y)):
        raise ValueError(f"R8R51R3 malformed formal trajectory: {spec['experiment_id']}")
    base = np.asarray(contract["base_target_physical"], dtype=float)
    target = base + np.asarray(
        [spec["target_R_offset_m"], spec["target_Z_offset_m"], spec["target_Ip_offset_A"]],
        dtype=float,
    )
    error = y - target[None, :]
    velocity = np.zeros((len(y), 2), dtype=float)
    velocity[1:] = np.diff(y[:, :2], axis=0) / float(contract["dt_s"])
    speed = np.linalg.norm(velocity, axis=1)
    first = int(
        contract["weak_arrival_first_step"] if weak else contract["normal_arrival_first_step"]
    )
    deadline = int(
        contract["weak_arrival_deadline_step"] if weak else contract["normal_arrival_deadline_step"]
    )
    pass_tolerance = float(contract["formal_pass_tolerance"])
    endpoint_rows = []
    for endpoint in range(first, deadline + 1):
        window_start = endpoint - int(contract["arrival_streak_steps"]) + 1
        sustained_box = float(np.max(np.abs(error[window_start : horizon + 1, :2])))
        endpoint_speed = float(speed[endpoint])
        late_start = max(1, endpoint - int(contract["late_window_steps"]) + 1)
        late_rms = float(np.sqrt(np.mean(speed[late_start : endpoint + 1] ** 2)))
        post_rms = float(np.sqrt(np.mean(speed[endpoint : horizon + 1] ** 2)))
        final_speed = float(speed[horizon])
        sustained_ip = float(np.max(np.abs(error[window_start : horizon + 1, 2])))
        hard = np.asarray(
            [
                1.0 - sustained_box / float(contract["position_tolerance_m"]),
                1.0 - endpoint_speed / float(contract["endpoint_speed_tolerance_m_per_s"]),
                1.0 - late_rms / float(contract["rms_speed_tolerance_m_per_s"]),
                1.0 - post_rms / float(contract["rms_speed_tolerance_m_per_s"]),
                1.0 - final_speed / float(contract["endpoint_speed_tolerance_m_per_s"]),
                1.0 - sustained_ip / float(contract["ip_safety_tolerance_A"]),
            ],
            dtype=float,
        )
        hold_ip = error[window_start:, 2]
        ip_margins = np.asarray(
            [
                1.0 - abs(float(error[-1, 2])) / float(contract["ip_terminal_abs_tolerance_A"]),
                1.0
                - float(np.sqrt(np.mean(hold_ip**2)))
                / float(contract["ip_hold_rms_tolerance_A"]),
                1.0
                - float(np.max(np.abs(hold_ip)))
                / float(contract["ip_sustained_max_tolerance_A"]),
            ],
            dtype=float,
        )
        combined = np.concatenate(([float(np.min(hard))], ip_margins))
        endpoint_rows.append(
            {
                "endpoint_step": endpoint,
                "arrival_time_ms": int(round(1000.0 * endpoint * float(contract["dt_s"]))),
                "pass": bool(np.min(hard) >= -pass_tolerance and np.min(ip_margins) >= -pass_tolerance),
                "minimum_signed_margin": float(np.min(combined)),
                "mean_signed_margin": float(np.mean(combined)),
            }
        )
    passing = [row for row in endpoint_rows if row["pass"]]
    chosen = max(
        passing if passing else endpoint_rows,
        key=lambda row: (
            float(row["minimum_signed_margin"]),
            float(row["mean_signed_margin"]),
            -int(row["endpoint_step"]),
        ),
    )
    return {
        "formal_contract_pass": bool(chosen["pass"]),
        "formal_minimum_signed_margin": float(chosen["minimum_signed_margin"]),
        "formal_mean_signed_margin": float(chosen["mean_signed_margin"]),
        "formal_best_arrival_ms": int(chosen["arrival_time_ms"]),
    }


def build_formal_rows(cfg: Mapping[str, Any], source: Mapping[str, Any]) -> dict[str, Any]:
    r51_stage = Path(source["r51_stage"])
    r7_stage = Path(source["r7_stage"])
    baseline_specs = _read(Path(source["paths"]["r7_baseline_specs"]))
    candidate_specs = source["specs"]
    old_rows = {
        str(row["experiment_id"]): row for row in source["raw_primary"]["rows"]
    }
    rows = []
    baselines: dict[str, dict[str, Any]] = {}
    for spec in baseline_specs:
        experiment_id = str(spec["experiment_id"])
        result = _read_gzip(r7_stage / "raw/baseline" / f"{experiment_id}.json.gz")
        trajectory = result.get("trajectory") or []
        if (
            result.get("success") is not True
            or result.get("spec") != spec
            or len(trajectory) != int(spec["horizon_steps"]) + 1
        ):
            raise ValueError(f"R8R51R3 baseline row changed: {experiment_id}")
        baselines[experiment_id] = result
        rows.append(
            {
                "experiment_id": experiment_id,
                "partition": "baseline",
                "pair_id": str(spec["pair_id"]),
                "history_member": str(spec["history_member"]),
                "candidate_index": -1,
                "candidate_id": "baseline",
                **formal_metric(spec, trajectory, cfg["formal_contract"]),
            }
        )
    for spec in candidate_specs:
        experiment_id = str(spec["experiment_id"])
        result = _read_gzip(r51_stage / "raw" / f"{experiment_id}.json.gz")
        trajectory = result.get("trajectory") or []
        old = old_rows.get(experiment_id)
        baseline_id = str(spec["source_r8r7_baseline_experiment_id"])
        baseline_spec = baselines.get(baseline_id, {}).get("spec")
        if (
            old is None
            or baseline_spec is None
            or result.get("success") is not True
            or result.get("spec") != spec
            or len(trajectory) != int(spec["horizon_steps"]) + 1
            or str(spec["pair_id"]) != str(baseline_spec["pair_id"])
            or str(spec["history_member"]) != str(baseline_spec["history_member"])
            or not all(
                old.get(key) is True
                for key in (
                    "runtime_success", "full_horizon", "authentic_restart",
                    "source_prefix_state_exact", "source_prefix_trace_exact",
                    "source_trace_difference_wrapper_only", "calibration_exact",
                    "q0_exact", "q0_offline_parity", "within_context_q0_prefix_exact",
                    "candidate_exact", "event_sequence_exact", "event_gates_passed",
                    "first_effect_at_issue_plus_one", "finite_response", "return_exact", "finite",
                )
            )
            or int(old.get("forbidden_trace_count", -1)) != 0
        ):
            raise ValueError(f"R8R51R3 candidate row changed: {experiment_id}")
        rows.append(
            {
                "experiment_id": experiment_id,
                "partition": "candidate",
                "pair_id": str(spec["pair_id"]),
                "history_member": str(spec["history_member"]),
                "candidate_index": int(spec["r8r51r1_candidate_index"]),
                "candidate_id": str(spec["r8r51r1_candidate_id"]),
                "source_baseline_experiment_id": baseline_id,
                **formal_metric(spec, trajectory, cfg["formal_contract"]),
            }
        )
    rows.sort(
        key=lambda row: (
            row["pair_id"], row["history_member"],
            0 if row["partition"] == "baseline" else 1,
            int(row["candidate_index"]), row["experiment_id"],
        )
    )
    groups: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["pair_id"], row["history_member"])].append(row)
    candidate_ids = sorted(map(str, cfg["source_r51r1"]["candidate_ids"]))
    coverage = all(
        len([row for row in group if row["partition"] == "baseline"]) == 1
        and len([row for row in group if row["partition"] == "candidate"]) == 13
        and sorted(row["candidate_id"] for row in group if row["partition"] == "candidate")
        == candidate_ids
        for group in groups.values()
    )
    if len(rows) != 224 or len(groups) != 16 or len(baselines) != 16 or not coverage:
        raise ValueError("R8R51R3 immutable formal-row coverage changed")
    return {
        "rows": rows,
        "strict_full_horizon_count": len(rows),
        "baseline_count": len(baselines),
        "candidate_count": len(rows) - len(baselines),
        "context_count": len(groups),
        "source_or_row_exclusion_count": 0,
        "formal_metric_digest": _digest(rows),
    }


def authority(rows: Sequence[Mapping[str, Any]], tolerance: float) -> dict[str, Any]:
    groups: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(str(row["pair_id"]), str(row["history_member"]))].append(row)
    contexts = []
    for key, group in sorted(groups.items()):
        baseline_rows = [row for row in group if row["partition"] == "baseline"]
        candidates = sorted(
            (row for row in group if row["partition"] == "candidate"),
            key=lambda row: int(row["candidate_index"]),
        )
        if len(baseline_rows) != 1 or len(candidates) != 13:
            raise ValueError(f"R8R51R3 context coverage changed: {key}")
        baseline = baseline_rows[0]
        best = max(
            candidates,
            key=lambda row: (
                float(row["formal_minimum_signed_margin"]),
                float(row["formal_mean_signed_margin"]),
                -int(row["candidate_index"]),
            ),
        )
        oracle_pool = [baseline, *candidates]
        oracle = max(
            enumerate(oracle_pool),
            key=lambda item: (
                float(item[1]["formal_minimum_signed_margin"]),
                float(item[1]["formal_mean_signed_margin"]),
                -item[0],
            ),
        )[1]
        gain = float(best["formal_minimum_signed_margin"]) - float(
            baseline["formal_minimum_signed_margin"]
        )
        repaired = bool(
            not baseline["formal_contract_pass"]
            and any(bool(row["formal_contract_pass"]) for row in candidates)
        )
        contexts.append(
            {
                "pair_id": key[0],
                "history_member": key[1],
                "baseline": dict(baseline),
                "candidates": [dict(row) for row in candidates],
                "best_candidate_index": int(best["candidate_index"]),
                "best_candidate_id": str(best["candidate_id"]),
                "best_candidate_minimum_margin_gain": gain,
                "best_candidate_strictly_improves_minimum_margin": gain > tolerance,
                "failed_baseline_repaired": repaired,
                "oracle_partition": str(oracle["partition"]),
                "oracle_candidate_index": int(oracle["candidate_index"]),
                "oracle_candidate_id": str(oracle["candidate_id"]),
                "oracle_formal_contract_pass": bool(oracle["formal_contract_pass"]),
            }
        )
    baseline_pass = sum(bool(row["baseline"]["formal_contract_pass"]) for row in contexts)
    candidate_pass = sum(
        bool(candidate["formal_contract_pass"])
        for row in contexts
        for candidate in row["candidates"]
    )
    candidate_pass_contexts = sum(
        any(bool(candidate["formal_contract_pass"]) for candidate in row["candidates"])
        for row in contexts
    )
    repairs = sum(bool(row["failed_baseline_repaired"]) for row in contexts)
    improved = sum(
        bool(row["best_candidate_strictly_improves_minimum_margin"])
        for row in contexts
        if not row["baseline"]["formal_contract_pass"]
    )
    oracle_pass = sum(bool(row["oracle_formal_contract_pass"]) for row in contexts)
    gains = [float(row["best_candidate_minimum_margin_gain"]) for row in contexts]
    return {
        "context_rows": contexts,
        "context_count": len(contexts),
        "baseline_formal_pass_count": baseline_pass,
        "candidate_formal_pass_count": candidate_pass,
        "candidate_formal_pass_context_count": candidate_pass_contexts,
        "failed_baseline_count": len(contexts) - baseline_pass,
        "repaired_failed_baseline_count": repairs,
        "failed_baseline_strict_margin_improvement_count": improved,
        "measured_oracle_formal_pass_count": oracle_pass,
        "best_candidate_minimum_margin_gain_minimum": min(gains),
        "best_candidate_minimum_margin_gain_median": statistics.median(gains),
        "best_candidate_minimum_margin_gain_maximum": max(gains),
        "context_outcome_digest": _digest(contexts),
    }


def _paths(run_dir: Path, cfg: Mapping[str, Any]) -> dict[str, Path]:
    stage = run_dir.expanduser().resolve() / str(cfg["run_name"])
    return {
        "stage": stage,
        "analysis": stage / "analysis",
        "source": stage / "source_reference",
        "state": stage / "stage_state.json",
        "manifest": stage / "stage_manifest.json",
    }


def run_primary(args: argparse.Namespace) -> dict[str, Any]:
    project = Path(__file__).resolve().parents[2]
    cfg = _read(args.config.expanduser().resolve())
    validate_config(cfg, project)
    paths = _paths(args.run_dir, cfg)
    if paths["stage"].exists():
        raise ValueError("R8R51R3 primary requires a fresh output identity")
    paths["analysis"].mkdir(parents=True)
    paths["source"].mkdir(parents=True)
    auth2 = authenticate_r51r2(cfg, args.r51r2_run, project)
    source = authenticate_sources(cfg, args.r51r1_run, args.r8r7_run)
    bank = build_formal_rows(cfg, source)
    outcome = authority(
        bank["rows"], float(cfg["formal_contract"]["metric_equivalence_absolute_tolerance"])
    )
    known = cfg["known_aggregate_contract"]
    integrity = bool(
        auth2["passed"]
        and source["passed"]
        and bank["strict_full_horizon_count"] == int(known["total_formal_row_count"])
        and bank["baseline_count"] == int(known["baseline_trajectory_count"])
        and bank["candidate_count"] == int(known["candidate_trajectory_count"])
        and bank["context_count"] == int(known["context_count"])
        and bank["source_or_row_exclusion_count"] == 0
        and outcome["baseline_formal_pass_count"] == int(known["baseline_formal_pass_count"])
        and outcome["failed_baseline_count"] == int(known["failed_baseline_count"])
    )
    gate = cfg["scientific_gate"]
    scientific = bool(
        integrity
        and outcome["repaired_failed_baseline_count"]
        >= int(gate["minimum_repaired_failed_baseline_count"])
        and outcome["measured_oracle_formal_pass_count"]
        >= int(gate["minimum_measured_oracle_formal_pass_count"])
    )
    route = cfg["routes"][
        "execution_fail" if not integrity else ("pass" if scientific else "authority_insufficient")
    ]
    detailed = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "phase": "primary",
        "source_r51r2_authentication": auth2,
        "formal_rows": bank["rows"],
        "context_rows": outcome["context_rows"],
        "formal_metric_digest": bank["formal_metric_digest"],
        **{key: value for key, value in bank.items() if key not in {"rows", "formal_metric_digest"}},
        **{key: value for key, value in outcome.items() if key != "context_rows"},
        "source_r51r1_authentication_passed": bool(source["passed"]),
        "source_r8r7_authentication_passed": bool(source["passed"]),
        "candidate_action_authentication_count": 208,
        "integrity_gate_passed": integrity,
        "scientific_gate_passed": scientific,
        "route": route,
        **dict(cfg["execution_contract"]),
    }
    _write(paths["analysis"] / PRIMARY_DETAIL, detailed)
    summary_keys = (
        "schema_version", "stage", "identity", "phase", "formal_metric_digest",
        "strict_full_horizon_count", "baseline_count", "candidate_count", "context_count",
        "source_or_row_exclusion_count", "context_outcome_digest",
        "baseline_formal_pass_count", "candidate_formal_pass_count",
        "candidate_formal_pass_context_count", "failed_baseline_count",
        "repaired_failed_baseline_count", "failed_baseline_strict_margin_improvement_count",
        "measured_oracle_formal_pass_count", "best_candidate_minimum_margin_gain_minimum",
        "best_candidate_minimum_margin_gain_median", "best_candidate_minimum_margin_gain_maximum",
        "source_r51r1_authentication_passed", "source_r8r7_authentication_passed",
        "candidate_action_authentication_count", "integrity_gate_passed",
        "scientific_gate_passed", "route", "new_tsc_count", "new_raw_count",
        "snapshot_count", "controller_execution_count", "plant_step_count",
        "model_fit_count", "model_selection_count", "optimization_count",
    )
    summary = {key: detailed[key] for key in summary_keys}
    summary["source_r51r2_authentication_passed"] = True
    summary["primary_detailed_sha256"] = _sha(paths["analysis"] / PRIMARY_DETAIL)
    source_serial = {
        "schema_version": 1,
        "stage": STAGE,
        "source_r51r2": auth2,
        "source_r51r1_stage": str(source["r51_stage"]),
        "source_r8r7_stage": str(source["r7_stage"]),
        "source_r51r1_raw_inventory": source["raw_inventory"],
        "source_r8r7_baseline_inventory": source["baseline_inventory"],
        "source_r8r7_baseline_audit_hashes": source["r8r7_baseline_audit_hashes"],
        "passed": True,
    }
    _write(paths["source"] / "source_authentication.json", source_serial)
    _write(paths["analysis"] / PRIMARY_SUMMARY, summary)
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "package_revision": cfg["package_revision"],
        "config_sha256": _sha(args.config.expanduser().resolve()),
        "design_document_sha256": cfg["design_document_sha256"],
        "package_manifest_sha256": _sha(project / "PACKAGE_MANIFEST.json"),
        "sha256sums_sha256": _sha(project / "SHA256SUMS"),
        "source_r51r2_run": str(args.r51r2_run.expanduser().resolve()),
        "source_r51r1_run": str(args.r51r1_run.expanduser().resolve()),
        "source_r8r7_run": str(args.r8r7_run.expanduser().resolve()),
        "source_authentication_sha256": _sha(paths["source"] / "source_authentication.json"),
        "primary_detailed_sha256": summary["primary_detailed_sha256"],
        "primary_summary_sha256": _sha(paths["analysis"] / PRIMARY_SUMMARY),
        "all_source_trajectories_allowed_in_expert_dataset": False,
        **dict(cfg["execution_contract"]),
    }
    _write(paths["manifest"], manifest)
    _write(
        paths["state"],
        {
            "schema_version": 1,
            "stage": STAGE,
            "phase_status": "primary_ready",
            "finished": False,
            "route": route,
            "integrity_gate_passed": integrity,
            "scientific_gate_passed": scientific,
            "source_outcomes_opened": True,
            "all_source_trajectories_allowed_in_expert_dataset": False,
            **dict(cfg["execution_contract"]),
        },
    )
    return summary


def finalize(args: argparse.Namespace) -> dict[str, Any]:
    project = Path(__file__).resolve().parents[2]
    cfg = _read(args.config.expanduser().resolve())
    validate_config(cfg, project)
    paths = _paths(args.run_dir, cfg)
    primary = _read(paths["analysis"] / PRIMARY_SUMMARY)
    independent = _read(paths["analysis"] / INDEPENDENT)
    state = _read(paths["state"])
    if (
        state.get("phase_status") != "primary_ready"
        or independent.get("audit_passed") is not True
        or independent.get("primary_outcome_agreement") is not True
        or independent.get("primary_discrete_agreement") is not True
        or independent.get("primary_numerical_agreement") is not True
        or independent.get("route") != primary.get("route")
        or independent.get("scientific_gate_passed") != primary.get("scientific_gate_passed")
    ):
        raise ValueError("R8R51R3 finalization integrity failed")
    compact = {
        **primary,
        "phase": "compact_audit",
        "primary_summary_sha256": _sha(paths["analysis"] / PRIMARY_SUMMARY),
        "primary_detailed_sha256": _sha(paths["analysis"] / PRIMARY_DETAIL),
        "independent_sha256": _sha(paths["analysis"] / INDEPENDENT),
        "primary_independent_maximum_numerical_difference": independent[
            "maximum_primary_numerical_difference"
        ],
        "primary_independent_discrete_agreement": True,
        "primary_independent_numerical_agreement": True,
        "audit_passed": True,
    }
    _write(paths["analysis"] / "compact_audit.json", compact)
    final = {
        **compact,
        "phase": "final",
        "compact_audit_sha256": _sha(paths["analysis"] / "compact_audit.json"),
        "passed": bool(primary["scientific_gate_passed"]),
        "classification": {
            "runtime_or_environment_error": False,
            "packaging_import_or_deployment_error": False,
            "raw_or_snapshot_corruption": False,
            "summary_or_reporting_error": False,
            "single_transport_return_hold_authority_insufficient": not bool(
                primary["scientific_gate_passed"]
            ),
            "real_controller_or_mpc_executed": False,
            "global_plant_reachability_claimed": False,
            "gate_a_qualified": False,
        },
        "all_source_trajectories_allowed_in_expert_dataset": False,
    }
    _write(paths["analysis"] / "final_report.json", final)
    state.update(
        {
            "phase_status": "complete",
            "finished": True,
            "route": final["route"],
            "integrity_gate_passed": final["integrity_gate_passed"],
            "scientific_gate_passed": final["scientific_gate_passed"],
            "final_report_sha256": _sha(paths["analysis"] / "final_report.json"),
        }
    )
    _write(paths["state"], state)
    manifest = _read(paths["manifest"])
    manifest.update(
        {
            "independent_sha256": _sha(paths["analysis"] / INDEPENDENT),
            "compact_audit_sha256": _sha(paths["analysis"] / "compact_audit.json"),
            "final_report_sha256": _sha(paths["analysis"] / "final_report.json"),
            "stage_state_sha256": _sha(paths["state"]),
            "finished": True,
        }
    )
    _write(paths["manifest"], manifest)
    return final


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--command", choices=("primary", "finalize"), required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--r51r2-run", type=Path)
    parser.add_argument("--r51r1-run", type=Path)
    parser.add_argument("--r8r7-run", type=Path)
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "primary":
        if args.r51r2_run is None or args.r51r1_run is None or args.r8r7_run is None:
            raise ValueError("R8R51R3 primary requires all source run paths")
        result = run_primary(args)
    else:
        result = finalize(args)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
