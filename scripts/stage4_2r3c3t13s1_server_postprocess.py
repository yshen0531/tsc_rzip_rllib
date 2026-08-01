#!/usr/bin/env python3
"""Independent server-side raw audit for Stage4.2R3c3T13S1."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s1_minimal_transition_sentinel as t13s1,
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


def _snapshot_integrity(
    specs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    by_state: dict[str, set[tuple[str, str]]] = {}
    for spec in specs:
        state_id = str(spec["state_generation_experiment_id"])
        by_state.setdefault(state_id, set()).add(
            (
                str(spec["restart_snapshot_dir"]),
                str(spec["restart_snapshot_manifest_digest"]),
            )
        )
    rows = []
    for state_id in sorted(by_state):
        identities = by_state[state_id]
        row: dict[str, Any] = {
            "state_generation_experiment_id": state_id,
            "snapshot_identity_count": len(identities),
            "snapshot_dir": "",
            "expected_manifest_digest": "",
            "actual_manifest_digest": "",
            "manifest_file_count": 0,
            "manifest_total_bytes": 0,
            "passed": False,
            "failure_reason": "",
        }
        if len(identities) != 1:
            row["failure_reason"] = (
                "one source state maps to multiple snapshot identities"
            )
            rows.append(row)
            continue
        directory_text, expected_digest = next(iter(identities))
        directory = Path(directory_text)
        manifest_path = directory / "restart_snapshot_manifest.json"
        row["snapshot_dir"] = directory_text
        row["expected_manifest_digest"] = expected_digest
        try:
            manifest = t13s1.t11.t1.r3c3.read_json(manifest_path)
            actual_digest = str(manifest.get("digest", ""))
            passed = bool(
                directory.is_dir()
                and manifest_path.is_file()
                and expected_digest
                and actual_digest == expected_digest
                and t13s1.t11.t1.r1._validate_snapshot_inventory(
                    directory, manifest
                )
            )
            row.update(
                {
                    "actual_manifest_digest": actual_digest,
                    "manifest_file_count": int(manifest.get("n_files", 0)),
                    "manifest_total_bytes": int(
                        manifest.get("total_bytes", 0)
                    ),
                    "passed": passed,
                    "failure_reason": (
                        ""
                        if passed
                        else "snapshot manifest or file inventory mismatch"
                    ),
                }
            )
        except Exception as exc:
            row["failure_reason"] = (
                f"snapshot audit exception: {type(exc).__name__}: {exc}"
            )
        rows.append(row)
    passed_count = sum(bool(row["passed"]) for row in rows)
    return {
        "expected_unique_state_count": len(by_state),
        "actual_unique_state_count": len(rows),
        "passed_count": passed_count,
        "failed_count": len(rows) - passed_count,
        "passed": bool(rows and passed_count == len(rows)),
        "states": rows,
    }


def _summary_fields(summary: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "expected_rollouts",
        "n_rollouts",
        "execution_pass_count",
        "extended_baseline_prefix_exact_count",
        "baseline_formal_reproduction_count",
        "runtime_or_environment_error_count",
        "plant_restart_fidelity_failure_count",
        "controller_causality_failure_count",
        "identification_probe_execution_failure_count",
        "command_subspace_execution_failure_count",
        "extended_baseline_prefix_mismatch_count",
        "baseline_formal_reproduction_mismatch_count",
        "forbidden_controller_input_count",
        "solver_failure_count",
        "scheduler_failure_count",
        "mode_action_rescale_count",
        "maximum_command_mode_subspace_residual_A",
        "response_group_count",
        "signal_pass_count",
        "pre_effect_causality_pass_count",
        "central_symmetry_pass_count",
        "matched_hidden_history_group_count",
        "matched_hidden_history_pass_count",
        "local_response_matrix_count",
        "local_response_matrix_pass_count",
        "maximum_normalized_condition_number",
        "maximum_current_utilization",
        "execution_gate_passed",
        "signal_gate_passed",
        "pre_effect_causality_gate_passed",
        "central_symmetry_gate_passed",
        "matched_hidden_history_gate_passed",
        "local_identifiability_gate_passed",
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
    parser.add_argument(
        "--source-stage4-2r3c3t3-controller-bank",
        required=True,
        type=Path,
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--audit-dir", required=True, type=Path)
    args = parser.parse_args()

    run_dir = args.run_dir.expanduser().resolve()
    audit_dir = args.audit_dir.expanduser().resolve()
    if run_dir == audit_dir or run_dir in audit_dir.parents:
        raise SystemExit("audit directory must remain outside the run tree")
    ctx = t13s1.load_stage42r3c3t13s1_config(
        args.config,
        source_stage42r3b_run=args.source_stage4_2r3b_run,
        source_stage42r3c3_run=args.source_stage4_2r3c3_run,
        source_stage42r3c3_bank_dir=args.source_stage4_2r3c3_bank_dir,
        source_stage42r3c3t1_run=args.source_stage4_2r3c3t1_run,
        source_stage42r3c3t1_audit_dir=(
            args.source_stage4_2r3c3t1_audit_dir
        ),
        source_stage42r3c3t3_controller_bank=(
            args.source_stage4_2r3c3t3_controller_bank
        ),
        run_dir_override=run_dir,
    )
    manifest = t13s1.t11.t1.r3c3.read_json(ctx.paths.manifest)
    reported = t13s1.t11.t1.r3c3.read_json(
        ctx.paths.control / "summary.json"
    )
    selected_pairs = t13s1._selected_pairs(ctx)
    specs = t13s1.build_control_specs(ctx, selected_pairs)
    expected_by_id = {str(spec["experiment_id"]): spec for spec in specs}
    raw_paths = sorted(ctx.paths.raw.glob("*.json.gz"))
    raw_inventory = _inventory(raw_paths, relative_to=ctx.paths.raw)
    results = [
        t13s1.t11.t1.r3c3.read_json_gz(path) for path in raw_paths
    ]
    actual_by_id = {
        str(result.get("experiment_id", "")): result for result in results
    }
    expected_count = int(ctx.cfg["control_matrix"]["expected_rollouts"])
    identity_exact = bool(
        len(raw_paths)
        == len(results)
        == len(specs)
        == expected_count
        and len(actual_by_id) == expected_count
        and set(actual_by_id) == set(expected_by_id)
    )
    filename_identity_exact = bool(
        len(raw_paths) == expected_count
        and all(
            path.name.removesuffix(".json.gz")
            == str(result.get("experiment_id", ""))
            for path, result in zip(raw_paths, results)
        )
    )
    specs_exact = bool(
        identity_exact
        and all(
            actual_by_id[experiment_id].get("spec") == spec
            for experiment_id, spec in expected_by_id.items()
        )
    )
    parse_complete = bool(
        len(results) == expected_count
        and all(
            isinstance(result.get("success"), bool)
            and isinstance(result.get("trajectory"), list)
            and isinstance(result.get("controller_trace"), list)
            for result in results
        )
    )
    recomputed = t13s1.summarize_control(
        ctx, results, selected_pairs, write_outputs=False
    )
    summary_exact = bool(
        reported == recomputed
        and _summary_fields(reported) == _summary_fields(recomputed)
    )
    active_package = t13s1._deployed_package_fingerprint(ctx)
    runtime_package = dict(
        manifest.get("deployed_package_fingerprint") or {}
    )
    package_exact = runtime_package == active_package
    control_specs_path = (
        ctx.paths.source_reference / "control_specs.json"
    )
    resolved_config_path = (
        ctx.paths.run_dir / "stage4_2r3c3t13s1_config.resolved.json"
    )
    fingerprint_path = (
        ctx.paths.source_reference / "deployed_package_fingerprint.json"
    )
    evidence_files_exact = bool(
        control_specs_path.is_file()
        and t13s1.t11.t1.r3c3.read_json(control_specs_path) == specs
        and resolved_config_path.is_file()
        and t13s1.t11.t1.r3c3.read_json(resolved_config_path) == ctx.cfg
        and fingerprint_path.is_file()
        and t13s1.t11.t1.r3c3.read_json(fingerprint_path) == runtime_package
    )
    manifest_checks = {
        "stage": manifest.get("stage") == t13s1.STAGE,
        "campaign_identity": manifest.get("campaign_identity")
        == t13s1.CAMPAIGN_IDENTITY,
        "controller_revision": manifest.get("controller_revision")
        == t13s1.CONTROLLER_REVISION,
        "package_revision": manifest.get("package_revision")
        == t13s1.PACKAGE_REVISION,
        "source_t11_config_sha256": manifest.get(
            "source_stage4_2r3c3t11_config_sha256"
        )
        == t13s1._sha256(ctx.base_config_path),
        "deployed_package_fingerprint": package_exact,
        "config_digest": manifest.get("config_digest")
        == t13s1._canonical_digest(ctx.cfg),
        "control_spec_digest": manifest.get("control_spec_digest")
        == t13s1._canonical_digest(specs),
        "identification_probe": manifest.get("identification_probe")
        == ctx.cfg["identification_probe"],
        "formal_timing_contract": manifest.get("formal_timing_contract")
        == ctx.cfg["formal_timing_contract"],
        "control_matrix": manifest.get("control_matrix")
        == ctx.cfg["control_matrix"],
        "evidence_files_exact": evidence_files_exact,
    }
    manifest_checks["passed"] = all(manifest_checks.values())
    snapshot_integrity = _snapshot_integrity(specs)
    snapshot_state_count_exact = bool(
        snapshot_integrity["expected_unique_state_count"]
        == snapshot_integrity["actual_unique_state_count"]
        == 4
    )
    raw_and_manifest_integrity = bool(
        identity_exact
        and filename_identity_exact
        and specs_exact
        and parse_complete
        and manifest_checks["passed"]
        and snapshot_state_count_exact
        and snapshot_integrity["passed"]
    )
    run_inventory = _inventory(
        (path for path in run_dir.rglob("*") if path.is_file()),
        relative_to=run_dir,
    )
    execution_complete = bool(recomputed["execution_gate_passed"])
    certified_scientific_result = bool(
        raw_and_manifest_integrity and summary_exact and execution_complete
    )
    certified_primary_pass = bool(
        certified_scientific_result and recomputed["passed"]
    )
    audit = {
        "schema_version": 1,
        "stage": t13s1.STAGE,
        "campaign_identity": t13s1.CAMPAIGN_IDENTITY,
        "run_dir": str(run_dir),
        "controller_revision": t13s1.CONTROLLER_REVISION,
        "package_revision": t13s1.PACKAGE_REVISION,
        "runtime_package_fingerprint_digest": str(
            runtime_package.get("digest", "")
        ),
        "audit_package_fingerprint_digest": str(
            active_package.get("digest", "")
        ),
        "package_exact": package_exact,
        "manifest_compatibility": manifest_checks,
        "control_raw_expected": expected_count,
        "control_raw_actual": len(raw_paths),
        "control_raw_parse_complete": parse_complete,
        "control_experiment_id_set_exact": identity_exact,
        "control_filename_identity_exact": filename_identity_exact,
        "control_specs_exact": specs_exact,
        "declared_unique_snapshot_count": 4,
        "snapshot_state_count_exact": snapshot_state_count_exact,
        "snapshot_integrity": snapshot_integrity,
        "raw_inventory": raw_inventory,
        "run_inventory": run_inventory,
        "raw_and_manifest_integrity_passed": raw_and_manifest_integrity,
        "reported_summary_exact_on_recomputation": summary_exact,
        "statistics_or_reporting_error_count": 0 if summary_exact else 1,
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
        "identification_probe_execution_failure_count": int(
            recomputed["identification_probe_execution_failure_count"]
        ),
        "signal_gate_passed": bool(recomputed["signal_gate_passed"]),
        "central_symmetry_gate_passed": bool(
            recomputed["central_symmetry_gate_passed"]
        ),
        "matched_hidden_history_gate_passed": bool(
            recomputed["matched_hidden_history_gate_passed"]
        ),
        "local_identifiability_gate_passed": bool(
            recomputed["local_identifiability_gate_passed"]
        ),
        "current_utilization_pass": bool(
            recomputed["current_utilization_pass"]
        ),
        "certified_scientific_result": certified_scientific_result,
        "certified_primary_pass": certified_primary_pass,
        "scientific_route": (
            "SENTINEL_PASS_OFFLINE_MODEL_ONLY"
            if certified_primary_pass
            else (
                "SENTINEL_FAIL_STOP_IDENTIFICATION"
                if certified_scientific_result
                else "NOT_RUN_OR_UNCERTIFIED"
            )
        ),
        "formal_tracking_is_acceptance_gate_for_probes": False,
        "observation_horizon_is_long_hold_validation": False,
        "identification_only": True,
        "development_set_only": True,
        "independent_hidden_history_confirmation": False,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "large_raw_download_required": False,
        "bc_dagger_or_rl_allowed": False,
    }
    audit_dir.mkdir(parents=True, exist_ok=True)
    raw_path = audit_dir / "stage4_2r3c3t13s1_raw_inventory.json"
    run_path = audit_dir / "stage4_2r3c3t13s1_run_inventory.json"
    snapshot_path = audit_dir / "stage4_2r3c3t13s1_snapshot_audit.json"
    audit_path = audit_dir / "stage4_2r3c3t13s1_server_audit.json"
    t13s1.t11.t1.r3c3.atomic_write_json(raw_path, raw_inventory)
    t13s1.t11.t1.r3c3.atomic_write_json(run_path, run_inventory)
    t13s1.t11.t1.r3c3.atomic_write_json(
        snapshot_path, snapshot_integrity
    )
    t13s1.t11.t1.r3c3.atomic_write_json(audit_path, audit)
    print(
        json.dumps(
            {
                "audit": str(audit_path),
                "audit_sha256": _sha256(audit_path),
                "raw_count": len(raw_paths),
                "raw_inventory_digest": raw_inventory["digest"],
                "snapshot_pass_count": snapshot_integrity["passed_count"],
                "snapshot_expected_count": snapshot_integrity[
                    "expected_unique_state_count"
                ],
                "summary_exact": summary_exact,
                "certified_scientific_result": certified_scientific_result,
                "certified_primary_pass": certified_primary_pass,
                "scientific_route": audit["scientific_route"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
