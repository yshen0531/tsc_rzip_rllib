#!/usr/bin/env python3
"""Independent server-side raw audit for Stage4.2R3c3T2."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t2_post_contract_neutralized_held_transport_identification
    as t2,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_digest(value: Any) -> str:
    text = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _inventory(
    paths: Iterable[Path], *, relative_to: Path
) -> dict[str, Any]:
    rows = [
        {
            "path": path.relative_to(relative_to).as_posix(),
            "size_bytes": int(path.stat().st_size),
            "sha256": _sha256(path),
        }
        for path in sorted(paths)
        if path.is_file()
    ]
    return {
        "n_files": len(rows),
        "total_bytes": sum(row["size_bytes"] for row in rows),
        "digest": _canonical_digest(rows),
        "files": rows,
    }


def _summary_fields(summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "expected_rollouts",
        "n_rollouts",
        "execution_pass_count",
        "extended_baseline_prefix_exact_count",
        "runtime_or_environment_error_count",
        "plant_restart_fidelity_failure_count",
        "controller_causality_failure_count",
        "identification_probe_execution_failure_count",
        "extended_baseline_prefix_mismatch_count",
        "forbidden_controller_input_count",
        "solver_failure_count",
        "formal_contract_pass_count",
        "formal_contract_failure_count",
        "response_group_count",
        "central_symmetry_pass_count",
        "matched_hidden_history_group_count",
        "matched_hidden_history_pass_count",
        "condition_number_group_count",
        "condition_number_pass_count",
        "maximum_selected_velocity_condition_number",
        "combined_condition_group_count",
        "combined_condition_pass_count",
        "maximum_combined_velocity_condition_number",
        "maximum_current_utilization",
        "execution_gate_passed",
        "central_symmetry_gate_passed",
        "matched_hidden_history_gate_passed",
        "condition_number_gate_passed",
        "combined_condition_number_gate_passed",
        "current_utilization_pass",
        "passed",
    )
    return {key: summary.get(key) for key in keys}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3b-run", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3c3-run", required=True, type=Path)
    parser.add_argument(
        "--source-stage4-2r3c3-bank-dir", required=True, type=Path
    )
    parser.add_argument(
        "--source-stage4-2r3c3t1-run", required=True, type=Path
    )
    parser.add_argument(
        "--source-stage4-2r3c3t1-audit-dir", required=True, type=Path
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--audit-dir", required=True, type=Path)
    args = parser.parse_args()

    run_dir = args.run_dir.expanduser().resolve()
    audit_dir = args.audit_dir.expanduser().resolve()
    if run_dir == audit_dir or run_dir in audit_dir.parents:
        raise SystemExit("audit directory must remain outside the run tree")
    ctx = t2.load_stage42r3c3t2_config(
        args.config,
        source_stage42r3b_run=args.source_stage4_2r3b_run,
        source_stage42r3c3_run=args.source_stage4_2r3c3_run,
        source_stage42r3c3_bank_dir=(
            args.source_stage4_2r3c3_bank_dir
        ),
        source_stage42r3c3t1_run=args.source_stage4_2r3c3t1_run,
        source_stage42r3c3t1_audit_dir=(
            args.source_stage4_2r3c3t1_audit_dir
        ),
        run_dir_override=run_dir,
    )
    manifest = t2.t1.r3c3.read_json(ctx.paths.manifest)
    reported = t2.t1.r3c3.read_json(
        ctx.paths.control / "summary.json"
    )
    selected_pairs, _ = t2.t1.r3c3._recompute_selected_pairs(
        ctx.source_ctx.base_ctx
    )
    specs = t2.build_control_specs(ctx, selected_pairs)
    raw_paths = sorted(ctx.paths.raw.glob("*.json.gz"))
    raw_inventory = _inventory(raw_paths, relative_to=ctx.paths.raw)
    results = [t2.t1.r3c3.read_json_gz(path) for path in raw_paths]
    expected_by_id = {
        str(spec["experiment_id"]): spec for spec in specs
    }
    actual_by_id = {
        str(result["experiment_id"]): result for result in results
    }
    identity_exact = bool(
        len(raw_paths) == len(specs) == 160
        and set(actual_by_id) == set(expected_by_id)
    )
    specs_exact = bool(
        identity_exact
        and all(
            actual_by_id[experiment_id].get("spec") == spec
            for experiment_id, spec in expected_by_id.items()
        )
    )
    parse_complete = bool(
        len(results) == len(raw_paths)
        and all(
            isinstance(result.get("success"), bool)
            and isinstance(result.get("trajectory"), list)
            and isinstance(result.get("controller_trace"), list)
            for result in results
        )
    )
    recomputed = t2.summarize_control(ctx, results, selected_pairs)
    summary_exact = (
        _summary_fields(reported) == _summary_fields(recomputed)
    )
    package = t2._deployed_package_fingerprint(ctx)
    package_exact = bool(
        manifest.get("deployed_package_fingerprint") == package
    )
    manifest_exact = bool(
        manifest.get("stage") == t2.STAGE
        and manifest.get("controller_revision")
        == t2.CONTROLLER_REVISION
        and manifest.get("package_revision") == t2.PACKAGE_REVISION
        and manifest.get("config_digest")
        == _canonical_digest(ctx.cfg)
        and manifest.get("control_spec_digest")
        == _canonical_digest(specs)
        and manifest.get("source_stage4_2r3c3t1_fingerprint")
        == ctx.source_t1_fingerprint
    )
    run_inventory = _inventory(
        (path for path in run_dir.rglob("*") if path.is_file()),
        relative_to=run_dir,
    )
    integrity = bool(
        identity_exact
        and specs_exact
        and parse_complete
        and manifest_exact
        and package_exact
    )
    audit = {
        "schema_version": 1,
        "stage": t2.STAGE,
        "run_dir": str(run_dir),
        "source_stage4_2r3c3t1_run": str(ctx.source_t1_run),
        "source_stage4_2r3c3t1_fingerprint": (
            ctx.source_t1_fingerprint
        ),
        "controller_revision": t2.CONTROLLER_REVISION,
        "package_revision": t2.PACKAGE_REVISION,
        "control_raw_expected": 160,
        "control_raw_actual": len(raw_paths),
        "control_raw_parse_complete": parse_complete,
        "control_experiment_id_set_exact": identity_exact,
        "control_specs_exact": specs_exact,
        "manifest_compatibility": manifest_exact,
        "package_compatibility": package_exact,
        "runtime_package_fingerprint_digest": manifest[
            "deployed_package_fingerprint"
        ]["digest"],
        "audit_package_fingerprint_digest": package["digest"],
        "raw_inventory": raw_inventory,
        "run_inventory": run_inventory,
        "raw_and_manifest_integrity_passed": integrity,
        "reported_summary_exact_on_recomputation": summary_exact,
        "statistics_or_reporting_error_count": 0
        if summary_exact
        else 1,
        "control_summary": recomputed,
        "runtime_or_environment_error_count": int(
            recomputed["runtime_or_environment_error_count"]
        ),
        "plant_restart_fidelity_failure_count": int(
            recomputed["plant_restart_fidelity_failure_count"]
        ),
        "controller_causality_failure_count": int(
            recomputed["controller_causality_failure_count"]
        ),
        "extended_baseline_prefix_exact_count": int(
            recomputed["extended_baseline_prefix_exact_count"]
        ),
        "central_symmetry_gate_passed": bool(
            recomputed["central_symmetry_gate_passed"]
        ),
        "matched_hidden_history_gate_passed": bool(
            recomputed["matched_hidden_history_gate_passed"]
        ),
        "transport_condition_number_gate_passed": bool(
            recomputed["condition_number_gate_passed"]
        ),
        "combined_condition_number_gate_passed": bool(
            recomputed["combined_condition_number_gate_passed"]
        ),
        "current_utilization_pass": bool(
            recomputed["current_utilization_pass"]
        ),
        "recomputed_identification_gate_pass": bool(
            recomputed["passed"]
        ),
        "certified_primary_pass": bool(
            integrity and summary_exact and recomputed["passed"]
        ),
        "formal_tracking_is_acceptance_gate": False,
        "observation_horizon_is_long_hold_validation": False,
        "identification_only": True,
        "development_set_only": True,
        "independent_hidden_history_confirmation": False,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "large_raw_download_required": False,
        "bc_dagger_or_rl_allowed": False,
    }
    audit_dir.mkdir(parents=True, exist_ok=True)
    raw_path = audit_dir / "stage4_2r3c3t2_raw_inventory.json"
    run_path = audit_dir / "stage4_2r3c3t2_run_inventory.json"
    audit_path = audit_dir / "stage4_2r3c3t2_server_audit.json"
    t2.t1.r3c3.atomic_write_json(raw_path, raw_inventory)
    t2.t1.r3c3.atomic_write_json(run_path, run_inventory)
    t2.t1.r3c3.atomic_write_json(audit_path, audit)
    print(
        json.dumps(
            {
                "audit": str(audit_path),
                "audit_sha256": _sha256(audit_path),
                "raw_count": len(raw_paths),
                "raw_inventory_digest": raw_inventory["digest"],
                "summary_exact": summary_exact,
                "certified_primary_pass": audit[
                    "certified_primary_pass"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
