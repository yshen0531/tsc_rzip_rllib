#!/usr/bin/env python3
"""Independent server-side compact postprocess for T13S13."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s13_recurrent_sequence_tube_identification as s13,
)


def _inventory(paths: Sequence[Path], root: Path) -> dict[str, Any]:
    rows = [
        {"path": path.relative_to(root).as_posix(), "size_bytes": path.stat().st_size, "sha256": s13._sha256(path)}
        for path in sorted(paths)
    ]
    return {
        "file_count": len(rows), "total_bytes": sum(row["size_bytes"] for row in rows),
        "digest": s13._digest(rows), "files": rows,
    }


def run(ctx: s13.Context, audit_dir: Path) -> dict[str, Any]:
    audit_dir.mkdir(parents=True, exist_ok=True)
    offline = s13.prepare_offline(ctx, resume=True)
    table = s13.build_context_table(ctx)
    specs = s13.build_new_specs(ctx, table)
    spec_by_id = {str(row["experiment_id"]): row for row in specs}
    state = s13._state(ctx)
    raw_paths = sorted(ctx.paths.raw.glob("*.json.gz"))
    raw_inventory = _inventory(raw_paths, ctx.paths.run_dir)
    parse_count = 0
    compatible_count = 0
    success_count = 0
    runtime_errors = []
    corruption = []
    for path in raw_paths:
        try:
            result = s13._load_gz(path)
            parse_count += 1
            spec = spec_by_id.get(str(result.get("experiment_id")))
            if spec is not None and s13._result_complete(path, spec):
                compatible_count += 1
            else:
                corruption.append({"path": path.name, "failure_reason": "raw identity or structural contract mismatch"})
            if bool(result.get("success")):
                success_count += 1
            else:
                runtime_errors.append({"path": path.name, "failure_reason": result.get("failure_reason", "")})
        except Exception as exc:
            corruption.append({"path": path.name, "failure_reason": repr(exc)})
    expected_by_phase = {
        "offline_ready": 0,
        "training_baseline_complete": 24,
        "training_probe_complete": 408,
        "training_model_frozen": 408,
        "calibration_baseline_complete": 428,
        "calibration_probe_complete": 748,
        "calibration_tube_frozen": 748,
        "holdout_baseline_complete": 768,
        "holdout_probe_complete": 1088,
        "campaign_complete": 1088,
    }
    phase = str(state["phase_status"])
    expected = expected_by_phase.get(phase, -1)
    execution_recomputations = {}
    phase_contracts = (
        (24, "training_baseline", "training", True),
        (408, "training_probe", "training", False),
        (428, "calibration_baseline", "calibration", True),
        (748, "calibration_probe", "calibration", False),
        (768, "holdout_baseline", "holdout", True),
        (1088, "holdout_probe", "holdout", False),
    )
    recomputation_errors = []
    for threshold, name, partition, baseline in phase_contracts:
        if len(raw_paths) < threshold:
            continue
        phase_specs = s13._partition_specs(specs, table, partition, baseline=baseline)
        try:
            audit = (
                s13.audit_baselines(ctx, phase_specs)
                if baseline else s13.audit_probes(ctx, phase_specs)
            )
            execution_recomputations[name] = {
                key: audit[key] for key in (
                    "expected", "actual", "pass_count",
                    "formal_tracking_pass_count_diagnostic_only",
                    "formal_tracking_is_safety_gate", "passed",
                )
            }
        except Exception as exc:
            recomputation_errors.append({"phase": name, "failure_reason": repr(exc)})
    execution_recomputation_pass = bool(
        not recomputation_errors
        and all(row["passed"] for row in execution_recomputations.values())
    )
    model_path = ctx.paths.model / "training_center_model.json"
    tube_path = ctx.paths.model / "calibrated_sequence_tube.json"
    final_recomputed = None
    final_match = None
    if phase == "campaign_complete" and len(raw_paths) == 1088:
        old = s13._read_json(ctx.paths.analysis / "stage4_2r3c3t13s13_final_audit.json")
        final_recomputed = s13.evaluate_holdout(ctx, table, specs)
        final_match = old == final_recomputed
    passed = bool(
        offline["passed"] and expected >= 0 and len(raw_paths) == expected
        and parse_count == compatible_count == success_count == len(raw_paths)
        and not runtime_errors and not corruption
        and execution_recomputation_pass
        and (final_match is not False)
    )
    compact = {
        "schema_version": s13.SCHEMA_VERSION, "stage": s13.STAGE,
        "phase": "independent_server_postprocess",
        "run_dir": str(ctx.paths.run_dir), "phase_status": phase,
        "expected_new_raw_for_phase": expected,
        "raw_inventory": raw_inventory,
        "raw_parse_count": parse_count, "raw_compatible_count": compatible_count,
        "raw_success_count": success_count,
        "runtime_or_environment_errors": runtime_errors,
        "raw_corruption": corruption,
        "execution_evidence_recomputations": execution_recomputations,
        "execution_recomputation_errors": recomputation_errors,
        "execution_evidence_recomputation_pass": execution_recomputation_pass,
        "context_table_digest": s13._digest(table),
        "new_spec_digest": s13._digest(specs),
        "model_sha256": s13._sha256(model_path) if model_path.is_file() else "",
        "tube_sha256": s13._sha256(tube_path) if tube_path.is_file() else "",
        "final_recomputation_exact": final_match,
        "final_route": None if final_recomputed is None else final_recomputed["route"],
        "scientific_primary_pass": bool(state.get("primary_pass")),
        "scientific_stop_reason": str(state.get("stop_reason", "")),
        "probe_trajectories_allowed_in_expert_dataset": False,
        "formal_timing_unchanged": True,
        "bc_dagger_or_rl_allowed": False,
        "passed": passed,
    }
    s13._write_json(audit_dir / "stage4_2r3c3t13s13_server_audit.json", compact)
    s13._write_json(audit_dir / "stage4_2r3c3t13s13_raw_inventory.json", raw_inventory)
    return compact


def main() -> None:
    parser = argparse.ArgumentParser(description="T13S13 server-side compact postprocess")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3b-run", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3c3-run", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3c3-bank-dir", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3c3t1-run", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3c3t1-audit-dir", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3c3t3-controller-bank", required=True, type=Path)
    parser.add_argument("--q1-run", required=True, type=Path)
    parser.add_argument("--q2-run", required=True, type=Path)
    parser.add_argument("--q1-audit", required=True, type=Path)
    parser.add_argument("--q2-audit", required=True, type=Path)
    parser.add_argument("--r3b-server-audit", required=True, type=Path)
    parser.add_argument("--r3b-snapshot-checks", required=True, type=Path)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--audit-dir", required=True, type=Path)
    args = parser.parse_args()
    ctx = s13.load_config(
        args.config,
        source_stage42r3b_run=args.source_stage4_2r3b_run,
        source_stage42r3c3_run=args.source_stage4_2r3c3_run,
        source_stage42r3c3_bank_dir=args.source_stage4_2r3c3_bank_dir,
        source_stage42r3c3t1_run=args.source_stage4_2r3c3t1_run,
        source_stage42r3c3t1_audit_dir=args.source_stage4_2r3c3t1_audit_dir,
        source_stage42r3c3t3_controller_bank=args.source_stage4_2r3c3t3_controller_bank,
        q1_run=args.q1_run, q2_run=args.q2_run,
        q1_audit=args.q1_audit, q2_audit=args.q2_audit,
        r3b_server_audit=args.r3b_server_audit,
        r3b_snapshot_checks=args.r3b_snapshot_checks,
        run_dir=args.run_dir,
    )
    print(json.dumps(run(ctx, args.audit_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
