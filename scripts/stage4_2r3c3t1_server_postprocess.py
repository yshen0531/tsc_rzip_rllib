#!/usr/bin/env python3
"""Server-side raw recomputation and compact audit for Stage4.2R3c3T1."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t1_long_separation_zero_net_transport_identification as t1,
)


def _inventory(root: Path) -> dict[str, Any]:
    rows = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        rows.append(
            {
                "path": path.relative_to(root).as_posix(),
                "size_bytes": int(path.stat().st_size),
                "sha256": t1._sha256(path),
            }
        )
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    return {
        "n_files": len(rows),
        "total_bytes": sum(int(row["size_bytes"]) for row in rows),
        "digest": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "files": rows,
    }


def _runtime_package_fingerprint(
    run_manifest: dict[str, Any],
) -> dict[str, Any]:
    fingerprint = dict(
        run_manifest.get("deployed_package_fingerprint") or {}
    )
    if not fingerprint:
        raise ValueError(
            "Stage4.2R3c3T1 runtime package fingerprint missing"
        )
    return fingerprint


def _audit_package_compatibility(
    runtime: dict[str, Any], audit: dict[str, Any]
) -> dict[str, Any]:
    runtime_files = {
        str(row["path"]): str(row["sha256"])
        for row in runtime.get("files", [])
    }
    audit_files = {
        str(row["path"]): str(row["sha256"])
        for row in audit.get("files", [])
    }
    changed = sorted(
        path
        for path in set(runtime_files) | set(audit_files)
        if runtime_files.get(path) != audit_files.get(path)
    )
    return {
        "passed": runtime == audit,
        "runtime_package_digest": str(runtime.get("digest", "")),
        "audit_package_digest": str(audit.get("digest", "")),
        "changed_paths": changed,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3b-run", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3c3-run", required=True, type=Path)
    parser.add_argument(
        "--source-stage4-2r3c3-bank-dir", required=True, type=Path
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    run_dir = args.run_dir.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    if output_dir == run_dir or run_dir in output_dir.parents:
        raise SystemExit("audit output must remain outside the run tree")
    output_dir.mkdir(parents=True, exist_ok=True)
    ctx = t1.load_stage42r3c3t1_config(
        args.config,
        source_stage42r3b_run=args.source_stage4_2r3b_run,
        source_stage42r3c3_run=args.source_stage4_2r3c3_run,
        source_stage42r3c3_bank_dir=(
            args.source_stage4_2r3c3_bank_dir
        ),
        run_dir_override=run_dir,
    )
    selected_pairs, _ = t1.r3c3._recompute_selected_pairs(ctx.base_ctx)
    expected_specs = t1.build_control_specs(ctx, selected_pairs)
    expected_by_id = {
        str(spec["experiment_id"]): spec for spec in expected_specs
    }
    raw_dir = ctx.paths.control / "raw"
    raw_paths = sorted(raw_dir.glob("*.json.gz"))
    raw_results = [t1.r3c3.read_json_gz(path) for path in raw_paths]
    actual_by_id = {
        str(result.get("experiment_id", "")): result
        for result in raw_results
    }
    id_exact = set(actual_by_id) == set(expected_by_id)
    specs_exact = bool(
        id_exact
        and all(
            actual_by_id[experiment_id].get("spec") == spec
            for experiment_id, spec in expected_by_id.items()
        )
    )
    parse_complete = bool(
        len(raw_paths) == len(raw_results)
        and all(bool(result.get("completed")) for result in raw_results)
    )
    raw_inventory = _inventory(raw_dir)

    reported_summary_path = ctx.paths.control / "summary.json"
    reported_summary = (
        t1.r3c3.read_json(reported_summary_path)
        if reported_summary_path.is_file()
        else None
    )
    control_summary = t1.summarize_control(
        ctx, raw_results, selected_pairs
    )
    reported_summary_exact = reported_summary == control_summary

    run_manifest = t1.r3c3.read_json(ctx.paths.manifest)
    runtime_package = _runtime_package_fingerprint(run_manifest)
    audit_package = t1._deployed_package_fingerprint(ctx)
    package_compatibility = _audit_package_compatibility(
        runtime_package, audit_package
    )
    runtime_fingerprint_path = (
        ctx.paths.source_reference / "deployed_package_fingerprint.json"
    )
    runtime_fingerprint_evidence_exact = bool(
        runtime_fingerprint_path.is_file()
        and t1.r3c3.read_json(runtime_fingerprint_path)
        == runtime_package
    )
    manifest_compatibility = {
        "stage": run_manifest.get("stage") == t1.STAGE,
        "controller_revision": run_manifest.get("controller_revision")
        == t1.CONTROLLER_REVISION,
        "package_revision": run_manifest.get("package_revision")
        == t1.PACKAGE_REVISION,
        "source_stage4_2r3c3_run": run_manifest.get(
            "source_stage4_2r3c3_run"
        )
        == str(ctx.source_r3c3_run),
        "source_stage4_2r3c3_bank_dir": run_manifest.get(
            "source_stage4_2r3c3_bank_dir"
        )
        == str(ctx.source_bank_dir),
        "source_stage4_2r3c3_bank_fingerprint": run_manifest.get(
            "source_stage4_2r3c3_bank_fingerprint"
        )
        == ctx.source_bank_fingerprint,
        "source_stage4_2r3b_run": run_manifest.get(
            "source_stage4_2r3b_run"
        )
        == str(ctx.source_r3b_run),
        "source_fingerprint": run_manifest.get("source_fingerprint")
        == ctx.source_fingerprint,
        "source_stage4_2r3c_run": run_manifest.get(
            "source_stage4_2r3c_run"
        )
        == str(ctx.source_r3c_run),
        "source_stage4_2r3c_fingerprint": run_manifest.get(
            "source_stage4_2r3c_fingerprint"
        )
        == ctx.source_r3c_fingerprint,
        "source_stage4_2r3c1_run": run_manifest.get(
            "source_stage4_2r3c1_run"
        )
        == str(ctx.source_r3c1_run),
        "source_stage4_2r3c1_fingerprint": run_manifest.get(
            "source_stage4_2r3c1_fingerprint"
        )
        == ctx.source_r3c1_fingerprint,
        "source_stage4_2r3c2_run": run_manifest.get(
            "source_stage4_2r3c2_run"
        )
        == str(ctx.source_r3c2_run),
        "source_stage4_2r3c2_fingerprint": run_manifest.get(
            "source_stage4_2r3c2_fingerprint"
        )
        == ctx.source_r3c2_fingerprint,
        "deployed_package_fingerprint": (
            runtime_fingerprint_evidence_exact
            and package_compatibility["passed"]
        ),
        "config_digest": run_manifest.get("config_digest")
        == t1._canonical_digest(ctx.cfg),
        "control_spec_digest": run_manifest.get("control_spec_digest")
        == t1._canonical_digest(expected_specs),
        "phase_alignment": run_manifest.get("phase_alignment")
        == ctx.cfg["phase_alignment"],
        "identification_probe": run_manifest.get(
            "identification_probe"
        )
        == ctx.cfg["identification_probe"],
        "formal_timing_contract": run_manifest.get(
            "formal_timing_contract"
        )
        == ctx.cfg["formal_timing_contract"],
        "control_matrix": run_manifest.get("control_matrix")
        == ctx.cfg["control_matrix"],
    }
    manifest_compatibility["passed"] = all(
        manifest_compatibility.values()
    )

    expected_count = int(
        ctx.cfg["control_matrix"]["expected_rollouts"]
    )
    raw_integrity_pass = bool(
        len(raw_paths) == expected_count
        and id_exact
        and specs_exact
        and parse_complete
        and manifest_compatibility["passed"]
    )
    recomputed_gate_pass = bool(control_summary["passed"])
    certified_primary_pass = bool(
        raw_integrity_pass
        and reported_summary_exact
        and recomputed_gate_pass
    )
    run_inventory = _inventory(run_dir)
    audit = {
        "schema_version": 1,
        "stage": t1.STAGE,
        "run_dir": str(run_dir),
        "source_stage4_2r3c3_run": str(ctx.source_r3c3_run),
        "source_stage4_2r3c3_bank_dir": str(ctx.source_bank_dir),
        "source_stage4_2r3c3_bank_provenance_digest": (
            ctx.source_bank_fingerprint["bank_provenance_digest"]
        ),
        "controller_revision": t1.CONTROLLER_REVISION,
        "package_revision": t1.PACKAGE_REVISION,
        "runtime_package_fingerprint_digest": runtime_package["digest"],
        "audit_package_fingerprint_digest": audit_package["digest"],
        "package_compatibility": package_compatibility,
        "manifest_compatibility": manifest_compatibility,
        "control_raw_expected": expected_count,
        "control_raw_actual": len(raw_paths),
        "control_experiment_id_set_exact": id_exact,
        "control_specs_exact": specs_exact,
        "control_raw_parse_complete": parse_complete,
        "raw_inventory": raw_inventory,
        "runtime_or_environment_error_count": int(
            control_summary["runtime_or_environment_error_count"]
        ),
        "plant_restart_fidelity_failure_count": int(
            control_summary["plant_restart_fidelity_failure_count"]
        ),
        "controller_causality_failure_count": int(
            control_summary["controller_causality_failure_count"]
        ),
        "identification_probe_execution_failure_count": int(
            control_summary[
                "identification_probe_execution_failure_count"
            ]
        ),
        "statistics_or_reporting_error_count": (
            0 if reported_summary_exact else 1
        ),
        "formal_contract_pass_count": int(
            control_summary["formal_contract_pass_count"]
        ),
        "formal_contract_failure_count": int(
            control_summary["formal_contract_failure_count"]
        ),
        "formal_tracking_is_acceptance_gate": False,
        "central_symmetry_gate_passed": bool(
            control_summary["central_symmetry_gate_passed"]
        ),
        "matched_hidden_history_gate_passed": bool(
            control_summary["matched_hidden_history_gate_passed"]
        ),
        "transport_condition_number_gate_passed": bool(
            control_summary["condition_number_gate_passed"]
        ),
        "combined_condition_number_gate_passed": bool(
            control_summary["combined_condition_number_gate_passed"]
        ),
        "current_utilization_pass": bool(
            control_summary["current_utilization_pass"]
        ),
        "reported_summary_exact_on_recomputation": (
            reported_summary_exact
        ),
        "raw_and_manifest_integrity_passed": raw_integrity_pass,
        "recomputed_identification_gate_pass": recomputed_gate_pass,
        "certified_primary_pass": certified_primary_pass,
        "control_summary": control_summary,
        "run_inventory": run_inventory,
        "identification_only": True,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "development_set_only": True,
        "independent_hidden_history_confirmation": False,
        "large_raw_download_required": False,
        "bc_dagger_or_rl_allowed": False,
    }
    t1.r3c3.atomic_write_json(
        output_dir / "stage4_2r3c3t1_raw_inventory.json",
        raw_inventory,
    )
    t1.r3c3.atomic_write_json(
        output_dir / "stage4_2r3c3t1_run_inventory.json",
        run_inventory,
    )
    t1.r3c3.atomic_write_json(
        output_dir / "stage4_2r3c3t1_server_audit.json", audit
    )
    print(
        json.dumps(
            {
                "run_dir": str(run_dir),
                "control_raw": len(raw_paths),
                "raw_integrity_passed": raw_integrity_pass,
                "reported_summary_exact": reported_summary_exact,
                "execution_pass_count": control_summary[
                    "execution_pass_count"
                ],
                "formal_pass_count": control_summary[
                    "formal_contract_pass_count"
                ],
                "central_symmetry_gate_passed": control_summary[
                    "central_symmetry_gate_passed"
                ],
                "matched_hidden_history_gate_passed": control_summary[
                    "matched_hidden_history_gate_passed"
                ],
                "transport_condition_number_gate_passed": (
                    control_summary["condition_number_gate_passed"]
                ),
                "combined_condition_number_gate_passed": (
                    control_summary[
                        "combined_condition_number_gate_passed"
                    ]
                ),
                "certified_primary_pass": certified_primary_pass,
                "raw_inventory_digest": raw_inventory["digest"],
                "run_inventory_digest": run_inventory["digest"],
                "run_inventory_bytes": run_inventory["total_bytes"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
