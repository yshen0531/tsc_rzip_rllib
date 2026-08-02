#!/usr/bin/env python3
"""Independent server-side authentication of the T13S9 blind holdout."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s9_unified_postqueue_q1_identification as s4,
)


def _inventory(paths: Sequence[Path], relative_to: Path) -> dict[str, Any]:
    rows = [
        {
            "path": path.relative_to(relative_to).as_posix(),
            "size_bytes": int(path.stat().st_size),
            "sha256": s4._sha256(path),
        }
        for path in sorted(paths)
    ]
    return {
        "n_files": len(rows),
        "total_bytes": sum(row["size_bytes"] for row in rows),
        "digest": s4._canonical_digest(rows),
        "files": rows,
    }


def _snapshot_integrity(specs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    identities: dict[str, set[tuple[str, str]]] = {}
    for spec in specs:
        identities.setdefault(str(spec["state_generation_experiment_id"]), set()).add(
            (
                str(spec["restart_snapshot_dir"]),
                str(spec["restart_snapshot_manifest_digest"]),
            )
        )
    rows = []
    for state_id, values in sorted(identities.items()):
        row = {
            "state_generation_experiment_id": state_id,
            "snapshot_identity_count": len(values),
            "passed": False,
            "failure_reason": "",
        }
        if len(values) != 1:
            row["failure_reason"] = "multiple snapshot identities"
            rows.append(row)
            continue
        directory_text, expected = next(iter(values))
        directory = Path(directory_text)
        manifest_path = directory / "restart_snapshot_manifest.json"
        try:
            manifest = s4.t11.t1.r3c3.read_json(manifest_path)
            passed = bool(
                directory.is_dir()
                and str(manifest.get("digest")) == expected
                and s4.t11.t1.r1._validate_snapshot_inventory(directory, manifest)
            )
            row.update({
                "snapshot_dir": directory_text,
                "expected_manifest_digest": expected,
                "actual_manifest_digest": str(manifest.get("digest", "")),
                "manifest_file_count": int(manifest.get("n_files", 0)),
                "manifest_total_bytes": int(manifest.get("total_bytes", 0)),
                "passed": passed,
                "failure_reason": "" if passed else "snapshot inventory mismatch",
            })
        except Exception as exc:
            row["failure_reason"] = f"{type(exc).__name__}: {exc}"
        rows.append(row)
    passed_count = sum(bool(row["passed"]) for row in rows)
    return {
        "expected_unique_state_count": 4,
        "actual_unique_state_count": len(rows),
        "passed_count": passed_count,
        "failed_count": len(rows) - passed_count,
        "passed": len(rows) == passed_count == 4,
        "states": rows,
    }


def _finalize_existing_raw(
    ctx: s4.Stage42R3C3T13S9Context,
) -> dict[str, Any]:
    """Finalize a completed run without the resume path pre-opening holdout raw."""
    selected_pairs, specs = s4.prepare(ctx, resume=True)
    offline = s4.run_offline_lattice_audit(
        ctx, selected_pairs, allow_existing_raw=True
    )
    if not bool(offline.get("passed")):
        raise RuntimeError("T13S9 offline gate failed during reporting finalization")
    summary = s4.summarize_from_raw(
        ctx, specs, selected_pairs, write_outputs=True
    )
    return s4.analyze(ctx, summary)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3b-run", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3c3-run", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3c3-bank-dir", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3c3t1-run", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3c3t1-audit-dir", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3c3t3-controller-bank", required=True, type=Path)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--audit-dir", required=True, type=Path)
    parser.add_argument("--finalize-existing-raw", action="store_true")
    args = parser.parse_args()
    run_dir = args.run_dir.expanduser().resolve()
    audit_dir = args.audit_dir.expanduser().resolve()
    if run_dir == audit_dir or run_dir in audit_dir.parents:
        raise SystemExit("audit directory must remain outside the run tree")
    ctx = s4.load_stage42r3c3t13s9_config(
        args.config,
        source_stage42r3b_run=args.source_stage4_2r3b_run,
        source_stage42r3c3_run=args.source_stage4_2r3c3_run,
        source_stage42r3c3_bank_dir=args.source_stage4_2r3c3_bank_dir,
        source_stage42r3c3t1_run=args.source_stage4_2r3c3t1_run,
        source_stage42r3c3t1_audit_dir=args.source_stage4_2r3c3t1_audit_dir,
        source_stage42r3c3t3_controller_bank=args.source_stage4_2r3c3t3_controller_bank,
        run_dir_override=run_dir,
    )
    if args.finalize_existing_raw:
        _finalize_existing_raw(ctx)
    selected_pairs = s4._selected_pairs(ctx)
    specs = s4.build_control_specs(ctx, selected_pairs)
    # This must be the first raw read in this independent invocation. The
    # module enforces development -> model hash -> blind holdout.
    recomputed = s4.summarize_from_raw(
        ctx, specs, selected_pairs, write_outputs=False
    )
    reported = s4.t11.t1.r3c3.read_json(ctx.paths.control / "summary.json")
    summary_exact = recomputed == reported
    expected_paths = [
        ctx.paths.raw / f"{spec['experiment_id']}.json.gz" for spec in specs
    ]
    raw_inventory = _inventory(expected_paths, ctx.paths.raw)
    raw_identity_exact = bool(
        len(expected_paths) == 68
        and len(list(ctx.paths.raw.glob("*.json.gz"))) == 68
        and all(s4._result_complete(path, spec) for path, spec in zip(expected_paths, specs))
    )
    manifest = s4.t11.t1.r3c3.read_json(ctx.paths.manifest)
    package = s4._deployed_package_fingerprint(ctx)
    execution_config_path = (
        run_dir / "stage4_2r3c3t13s9_config.resolved.json"
    )
    execution_config = s4.t11.t1.r3c3.read_json(execution_config_path)
    reporting_hotfix = bool(
        manifest.get("package_revision") == s4.EXECUTION_PACKAGE_REVISION
        and s4._reporting_hotfix_config_compatible(execution_config, ctx.cfg)
    )
    package_resume_compatible = False
    try:
        s4._resume_compatible(
            dict(manifest.get("deployed_package_fingerprint") or {}),
            package,
            allow_reporting_hotfix=reporting_hotfix,
        )
        package_resume_compatible = True
    except ValueError:
        package_resume_compatible = False
    execution_manifest_exact = bool(
        manifest.get("stage") == s4.STAGE
        and manifest.get("campaign_identity") == s4.CAMPAIGN_IDENTITY
        and manifest.get("controller_revision") == s4.CONTROLLER_REVISION
        and manifest.get("package_revision")
        in {s4.EXECUTION_PACKAGE_REVISION, s4.PACKAGE_REVISION}
        and manifest.get("config_digest")
        == s4._canonical_digest(execution_config)
        and manifest.get("control_spec_digest") == s4._canonical_digest(specs)
    )
    manifest_exact = bool(
        execution_manifest_exact and package_resume_compatible
    )
    snapshots = _snapshot_integrity(specs)
    run_paths = [path for path in run_dir.rglob("*") if path.is_file()]
    run_inventory = _inventory(run_paths, run_dir)
    certified = bool(
        summary_exact and raw_identity_exact and manifest_exact
        and snapshots["passed"] and recomputed["execution_gate_passed"]
    )
    primary_pass = bool(certified and recomputed["passed"])
    audit = {
        "schema_version": 1,
        "stage": s4.STAGE,
        "campaign_identity": s4.CAMPAIGN_IDENTITY,
        "run_dir": str(run_dir),
        "controller_revision": s4.CONTROLLER_REVISION,
        "execution_package_revision": manifest.get("package_revision"),
        "reporting_package_revision": s4.PACKAGE_REVISION,
        "semantics_preserving_reporting_hotfix": reporting_hotfix,
        "execution_manifest_exact": execution_manifest_exact,
        "reporting_package_resume_compatible": package_resume_compatible,
        "package_exact": manifest_exact,
        "control_raw_expected": 68,
        "control_raw_actual": raw_inventory["n_files"],
        "control_raw_identity_exact": raw_identity_exact,
        "raw_inventory": raw_inventory,
        "run_inventory": run_inventory,
        "snapshot_integrity": snapshots,
        "reported_summary_exact_on_recomputation": summary_exact,
        "statistics_or_reporting_error_count": 0 if summary_exact else 1,
        "development_before_holdout_open_order_pass": bool(
            recomputed["development_before_holdout_open_order_pass"]
        ),
        "model_file_sha256": recomputed["model_file_sha256"],
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
        "certified_scientific_result": certified,
        "certified_primary_pass": primary_pass,
        "scientific_route": (
            "UNIFIED_POSTQUEUE_Q1_IDENTIFICATION_COMPLETE_COMBINE_Q2_REQUIRED"
            if primary_pass else (
                "UNIFIED_POSTQUEUE_Q1_IDENTIFICATION_FAIL_REDESIGN"
                if certified else "NOT_RUN_OR_UNCERTIFIED"
            )
        ),
        "real_mpc_executed": False,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "large_raw_download_required": False,
        "bc_dagger_or_rl_allowed": False,
    }
    audit_dir.mkdir(parents=True, exist_ok=True)
    for name, value in (
        ("stage4_2r3c3t13s9_raw_inventory.json", raw_inventory),
        ("stage4_2r3c3t13s9_run_inventory.json", run_inventory),
        ("stage4_2r3c3t13s9_snapshot_audit.json", snapshots),
        ("stage4_2r3c3t13s9_server_audit.json", audit),
    ):
        s4.t11.t1.r3c3.atomic_write_json(audit_dir / name, value)
    audit_path = audit_dir / "stage4_2r3c3t13s9_server_audit.json"
    print(json.dumps({
        "audit": str(audit_path),
        "audit_sha256": s4._sha256(audit_path),
        "raw_count": raw_inventory["n_files"],
        "raw_inventory_digest": raw_inventory["digest"],
        "summary_exact": summary_exact,
        "certified_scientific_result": certified,
        "certified_primary_pass": primary_pass,
        "scientific_route": audit["scientific_route"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
