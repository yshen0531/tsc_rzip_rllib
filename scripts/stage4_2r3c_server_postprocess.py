#!/usr/bin/env python3
"""Server-side Stage4.2R3c raw recomputation and compact audit."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c_visible_state_phase_aligned_mpc as r3c,
)


def _inventory(root: Path) -> dict[str, Any]:
    rows = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        rows.append(
            {
                "path": path.relative_to(root).as_posix(),
                "size_bytes": int(path.stat().st_size),
                "sha256": r3c._sha256_file(path),
            }
        )
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    return {
        "n_files": len(rows),
        "total_bytes": sum(int(row["size_bytes"]) for row in rows),
        "digest": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "files": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3b-run", required=True, type=Path)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    run_dir = args.run_dir.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    if output_dir == run_dir or run_dir in output_dir.parents:
        raise SystemExit("audit output must remain outside the run tree")
    output_dir.mkdir(parents=True, exist_ok=True)
    ctx = r3c.load_stage42r3c_config(
        args.config,
        source_stage42r3b_run=args.source_stage4_2r3b_run,
        run_dir_override=run_dir,
    )
    selected_pairs, _ = r3c._recompute_selected_pairs(ctx)
    expected_specs = r3c.build_control_specs(ctx, selected_pairs)
    expected_by_id = {
        str(spec["experiment_id"]): spec for spec in expected_specs
    }
    raw_paths = sorted((ctx.paths.control / "raw").glob("*.json.gz"))
    raw_results = [r3c.read_json_gz(path) for path in raw_paths]
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
    control_summary = r3c.summarize_control(
        ctx, raw_results, selected_pairs
    )
    run_manifest = r3c.read_json(ctx.paths.manifest)
    package_fingerprint = r3c._deployed_package_fingerprint(ctx)
    manifest_compatibility = {
        "stage": run_manifest.get("stage") == r3c.STAGE,
        "controller_revision": run_manifest.get("controller_revision")
        == r3c.CONTROLLER_REVISION,
        "package_revision": run_manifest.get("package_revision")
        == r3c.PACKAGE_REVISION,
        "source_stage4_2r3b_run": run_manifest.get(
            "source_stage4_2r3b_run"
        )
        == str(ctx.source_r3b_run),
        "source_fingerprint": run_manifest.get("source_fingerprint")
        == ctx.source_fingerprint,
        "deployed_package_fingerprint": run_manifest.get(
            "deployed_package_fingerprint"
        )
        == package_fingerprint,
        "control_spec_digest": run_manifest.get("control_spec_digest")
        == r3c._canonical_digest(expected_specs),
        "phase_alignment": run_manifest.get("phase_alignment")
        == ctx.cfg["phase_alignment"],
        "formal_timing_contract": run_manifest.get(
            "formal_timing_contract"
        )
        == ctx.cfg["formal_timing_contract"],
    }
    manifest_compatibility["passed"] = all(
        manifest_compatibility.values()
    )
    runtime_errors = int(
        control_summary["runtime_or_environment_error_count"]
    )
    restart_failures = int(
        control_summary["plant_restart_fidelity_failure_count"]
    )
    causality_failures = int(
        control_summary["controller_causality_failure_count"]
    )
    phase_design_failures = int(
        control_summary[
            "phase_selection_or_transition_design_failure_count"
        ]
    )
    raw_integrity_pass = bool(
        len(raw_paths) == int(ctx.cfg["control_matrix"]["expected_rollouts"])
        and id_exact
        and specs_exact
        and parse_complete
        and manifest_compatibility["passed"]
    )
    run_inventory = _inventory(run_dir)
    audit = {
        "schema_version": 1,
        "stage": r3c.STAGE,
        "run_dir": str(run_dir),
        "source_stage4_2r3b_run": str(ctx.source_r3b_run),
        "source_fingerprint_digest": ctx.source_fingerprint["digest"],
        "controller_revision": r3c.CONTROLLER_REVISION,
        "package_revision": r3c.PACKAGE_REVISION,
        "deployed_package_fingerprint_digest": package_fingerprint[
            "digest"
        ],
        "manifest_compatibility": manifest_compatibility,
        "control_raw_expected": int(
            ctx.cfg["control_matrix"]["expected_rollouts"]
        ),
        "control_raw_actual": len(raw_paths),
        "control_experiment_id_set_exact": id_exact,
        "control_specs_exact": specs_exact,
        "control_raw_parse_complete": parse_complete,
        "runtime_or_environment_error_count": runtime_errors,
        "plant_restart_fidelity_failure_count": restart_failures,
        "controller_causality_failure_count": causality_failures,
        "phase_selection_or_transition_design_failure_count": (
            phase_design_failures
        ),
        "real_closed_loop_formal_control_failure_count": int(
            control_summary[
                "real_closed_loop_formal_control_failure_count"
            ]
        ),
        "control_summary": control_summary,
        "raw_and_manifest_integrity_passed": raw_integrity_pass,
        "recomputed_primary_pass": bool(control_summary["passed"]),
        "development_set_only": True,
        "independent_hidden_history_confirmation": False,
        "large_raw_download_required": False,
        "run_inventory": run_inventory,
    }
    r3c.atomic_write_json(
        output_dir / "stage4_2r3c_run_inventory.json",
        run_inventory,
    )
    r3c.atomic_write_json(
        output_dir / "stage4_2r3c_server_audit.json", audit
    )
    print(
        json.dumps(
            {
                "run_dir": str(run_dir),
                "raw_integrity_passed": raw_integrity_pass,
                "recomputed_primary_pass": bool(control_summary["passed"]),
                "control_raw": len(raw_paths),
                "formal_pass_fraction": control_summary[
                    "formal_contract_pass_fraction"
                ],
                "run_inventory_digest": run_inventory["digest"],
                "run_inventory_files": run_inventory["n_files"],
                "run_inventory_bytes": run_inventory["total_bytes"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
