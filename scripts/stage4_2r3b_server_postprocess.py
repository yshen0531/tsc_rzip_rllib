#!/usr/bin/env python3
"""Server-side Stage4.2R3b raw-evidence recomputation and compact audit.

This tool intentionally reads and hashes the large raw/snapshot tree in place.
Only its compact JSON/CSV summaries and hash inventory need to be transferred.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3b_confirmatory_hidden_history_initial_state as r3,
)


def _inventory(root: Path) -> dict[str, Any]:
    rows = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        rows.append(
            {
                "path": relative,
                "size_bytes": int(path.stat().st_size),
                "sha256": r3._sha256_file(path),
            }
        )
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    return {
        "n_files": len(rows),
        "total_bytes": sum(int(row["size_bytes"]) for row in rows),
        "digest": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "files": rows,
    }


def _raw_results(raw_dir: Path) -> list[dict[str, Any]]:
    return [r3.read_json_gz(path) for path in sorted(raw_dir.glob("*.json.gz"))]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recompute Stage4.2R3b evidence on the server"
    )
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--source-stage4-2r2-run", required=True, type=Path)
    parser.add_argument(
        "--calibration-stage4-2r3a-run", required=True, type=Path
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    run_dir = args.run_dir.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    if output_dir == run_dir or run_dir in output_dir.parents:
        raise SystemExit("output directory must be outside the large run tree")
    output_dir.mkdir(parents=True, exist_ok=True)
    ctx = r3.load_stage42r3b_config(
        args.config,
        source_stage42r2_run=args.source_stage4_2r2_run,
        calibration_stage42r3a_run=args.calibration_stage4_2r3a_run,
        run_dir_override=run_dir,
    )

    generation_payload = r3._generation_base_payload(ctx)
    directions = r3._nullspace_directions(generation_payload["modes_tsc"])
    common_prefix = r3._common_prefix_source(ctx)
    expected_state_specs = r3._state_spec_grid(
        directions, ctx.cfg, common_prefix
    )
    run_manifest = r3.read_json(ctx.paths.manifest)
    current_package_fingerprint = r3._deployed_package_fingerprint(ctx)
    manifest_compatibility = {
        "stage": run_manifest.get("stage") == r3.STAGE,
        "controller_revision": run_manifest.get("controller_revision")
        == r3.CONTROLLER_REVISION,
        "package_revision": run_manifest.get("package_revision")
        == r3.PACKAGE_REVISION,
        "source_fingerprint": run_manifest.get("source_fingerprint")
        == ctx.source_fingerprint,
        "calibration_stage4_2r3a_run": run_manifest.get(
            "calibration_stage4_2r3a_run"
        )
        == str(ctx.calibration_r3a_run),
        "calibration_fingerprint": run_manifest.get(
            "calibration_fingerprint"
        )
        == ctx.calibration_fingerprint,
        "deployed_package_fingerprint": run_manifest.get(
            "deployed_package_fingerprint"
        )
        == current_package_fingerprint,
        "common_prefix_source": run_manifest.get("common_prefix_source")
        == common_prefix,
        "state_generation_spec_digest": run_manifest.get(
            "state_generation_spec_digest"
        )
        == r3._canonical_digest(expected_state_specs),
    }
    manifest_compatibility["passed"] = all(manifest_compatibility.values())
    expected_state_ids = {
        str(spec["experiment_id"]) for spec in expected_state_specs
    }
    expected_state_by_id = {
        str(spec["experiment_id"]): spec for spec in expected_state_specs
    }
    state_results = _raw_results(ctx.paths.state_generation / "raw")
    actual_state_ids = {
        str(result.get("experiment_id", "")) for result in state_results
    }
    state_id_exact = actual_state_ids == expected_state_ids
    state_specs_exact = bool(
        state_id_exact
        and all(
            result.get("spec")
            == expected_state_by_id[str(result.get("experiment_id", ""))]
            for result in state_results
        )
    )
    state_parse_complete = bool(
        len(state_results) == len(expected_state_specs)
        and state_id_exact
        and state_specs_exact
        and all(
            bool(result.get("completed"))
            and isinstance(result.get("spec"), dict)
            and (
                not bool(result.get("success"))
                or len(result.get("trajectory") or [])
                == int(result["spec"]["horizon_steps"]) + 1
            )
            for result in state_results
        )
    )

    snapshot_checks = []
    for result in state_results:
        restart = result.get("restart_snapshot") or {}
        snapshot_dir = Path(str(restart.get("snapshot_dir", "")))
        manifest_path = snapshot_dir / "restart_snapshot_manifest.json"
        manifest = (
            r3.read_json(manifest_path) if manifest_path.is_file() else {}
        )
        expected_digest = str(
            restart.get("snapshot_manifest_digest", "")
        )
        valid = bool(
            result.get("success")
            and manifest
            and str(manifest.get("digest", "")) == expected_digest
            and r3.r1._validate_snapshot_inventory(snapshot_dir, manifest)
        )
        snapshot_checks.append(
            {
                "experiment_id": str(result.get("experiment_id", "")),
                "snapshot_dir": str(snapshot_dir),
                "manifest_digest": expected_digest,
                "n_files": int(manifest.get("n_files", 0)),
                "total_bytes": int(manifest.get("total_bytes", 0)),
                "valid": valid,
            }
        )

    state_summary = r3.analyze_state_generation(ctx, state_results)
    selected_pairs = (
        r3.read_json(ctx.paths.pair_analysis / "selected_pairs.json")
        if (ctx.paths.pair_analysis / "selected_pairs.json").is_file()
        else []
    )
    control_results = _raw_results(ctx.paths.control / "raw")
    expected_control_specs = (
        r3.build_control_specs(ctx, selected_pairs)
        if bool(state_summary.get("passed"))
        else []
    )
    expected_control_ids = {
        str(spec["experiment_id"]) for spec in expected_control_specs
    }
    expected_control_by_id = {
        str(spec["experiment_id"]): spec for spec in expected_control_specs
    }
    actual_control_ids = {
        str(result.get("experiment_id", "")) for result in control_results
    }
    control_id_exact = actual_control_ids == expected_control_ids
    control_specs_exact = bool(
        control_id_exact
        and all(
            result.get("spec")
            == expected_control_by_id[str(result.get("experiment_id", ""))]
            for result in control_results
        )
    )
    control_parse_complete = bool(
        expected_control_specs
        and len(control_results) == len(expected_control_specs)
        and control_id_exact
        and control_specs_exact
        and all(
            bool(result.get("completed"))
            and isinstance(result.get("spec"), dict)
            for result in control_results
        )
    )
    control_summary = (
        r3.summarize_control(ctx, control_results, selected_pairs)
        if control_parse_complete
        else None
    )
    recomputed = r3.analyze(ctx, state_summary, control_summary)

    inventory = _inventory(run_dir)
    audit = {
        "schema_version": 1,
        "stage": r3.STAGE,
        "controller_revision": r3.CONTROLLER_REVISION,
        "package_revision": r3.PACKAGE_REVISION,
        "run_dir": str(run_dir),
        "source_stage4_2r2_run": str(ctx.source_r2_run),
        "calibration_stage4_2r3a_run": str(ctx.calibration_r3a_run),
        "calibration_fingerprint_digest": ctx.calibration_fingerprint[
            "digest"
        ],
        "source_fingerprint_digest": ctx.source_fingerprint["digest"],
        "deployed_package_fingerprint_digest": current_package_fingerprint[
            "digest"
        ],
        "common_prefix_source_experiment_id": common_prefix[
            "source_experiment_id"
        ],
        "common_prefix_action_digest": common_prefix["action_digest"],
        "common_prefix_action_digests": common_prefix[
            "prefix_action_digests"
        ],
        "manifest_compatibility": manifest_compatibility,
        "state_raw_expected": len(expected_state_specs),
        "state_raw_actual": len(state_results),
        "state_experiment_id_set_exact": state_id_exact,
        "state_specs_exact": state_specs_exact,
        "state_raw_parse_complete": state_parse_complete,
        "snapshot_expected": len(state_results),
        "snapshot_valid_count": sum(
            bool(row["valid"]) for row in snapshot_checks
        ),
        "state_runtime_or_environment_error_count": int(
            state_summary["runtime_or_environment_error_count"]
        ),
        "state_raw_or_snapshot_corruption_count": int(
            state_summary["raw_or_snapshot_corruption_count"]
        ),
        "control_raw_expected": len(expected_control_specs),
        "control_raw_actual": len(control_results),
        "control_experiment_id_set_exact": control_id_exact,
        "control_specs_exact": control_specs_exact,
        "control_raw_parse_complete": control_parse_complete,
        "state_summary": state_summary,
        "control_summary": control_summary,
        "recomputed_primary_pass": bool(recomputed.get("primary_pass")),
        "runtime_or_environment_error_count": (
            int(state_summary["runtime_or_environment_error_count"])
            if control_summary is None
            else int(state_summary["runtime_or_environment_error_count"])
            + int(control_summary["runtime_or_environment_error_count"])
        ),
        "plant_restart_fidelity_failure_count": (
            None
            if control_summary is None
            else int(control_summary["plant_restart_fidelity_failure_count"])
        ),
        "controller_causality_failure_count": (
            None
            if control_summary is None
            else int(control_summary["controller_causality_failure_count"])
        ),
        "real_closed_loop_formal_control_failure_count": (
            None
            if control_summary is None
            else int(
                control_summary[
                    "real_closed_loop_formal_control_failure_count"
                ]
            )
        ),
        "reporting_recomputation_completed": True,
        "large_raw_download_required": False,
        "run_inventory": inventory,
        "passed": bool(
            manifest_compatibility["passed"]
            and state_parse_complete
            and len(snapshot_checks) == len(expected_state_specs)
            and all(bool(row["valid"]) for row in snapshot_checks)
            and (
                (not bool(state_summary.get("passed")) and not control_results)
                or (
                    control_parse_complete
                    and control_summary is not None
                    and bool(control_summary.get("passed"))
                )
            )
        ),
    }
    r3.atomic_write_json(output_dir / "stage4_2r3b_server_audit.json", audit)
    r3.atomic_write_json(
        output_dir / "stage4_2r3b_snapshot_checks.json", snapshot_checks
    )
    r3.atomic_write_json(
        output_dir / "stage4_2r3b_run_inventory.json", inventory
    )
    print(json.dumps(audit, sort_keys=True))


if __name__ == "__main__":
    main()
