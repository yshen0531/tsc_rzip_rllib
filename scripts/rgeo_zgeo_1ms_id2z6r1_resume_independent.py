#!/usr/bin/env python3
"""Independent provenance wrapper for the ID2Z6R1 in-place resume."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_id0_vector_tail import sha256, write_new  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2z6_early_root_branch_teacher as primary  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2z6_early_root_branch_teacher_independent as base  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2z6r1_resume as resume  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-id2z6r1-independent-raw-v1"


def _inside(path: Path, label: str) -> Path:
    value = path.resolve()
    try:
        value.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(f"{label} leaves repository") from exc
    return value


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"object required: {path}")
    return value


def audit(stage_path: Path, run_dir: Path,
          experiment_source_revision: str,
          hotfix_source_revision: str) -> dict[str, Any]:
    run_dir = _inside(run_dir, "run directory")
    failures: list[str] = []
    base_result = base.audit(
        stage_path, run_dir, experiment_source_revision)
    failures.extend(base_result.get("failures", []))
    result_path = run_dir / "result.json"
    result = _load(result_path) if result_path.is_file() else {}
    metadata_path = run_dir / "metadata" / "id2z6r1_resume_preflight.json"
    metadata = _load(metadata_path) if metadata_path.is_file() else {}
    if result.get("resume_hotfix_source_revision") != hotfix_source_revision:
        failures.append("HOTFIX_SOURCE_REVISION")
    if result.get("source_revision") != experiment_source_revision:
        failures.append("EXPERIMENT_SOURCE_REVISION")
    if result.get("original_round0_rollouts_reused_without_rerun") != 5:
        failures.append("ROUND0_REUSE_COUNT")
    if (metadata.get("schema_version") != resume.PREFLIGHT_SCHEMA
            or metadata.get("experiment_source_revision")
            != experiment_source_revision
            or metadata.get("hotfix_source_revision") != hotfix_source_revision
            or not metadata.get("passed")
            or metadata.get("original_round0_rollouts_authenticated") != 5
            or metadata.get("original_round0_states_authenticated") != 350
            or metadata.get("original_round0_artifacts_authenticated") != 1750
            or metadata.get("plant_advance_gotsc_calls") != 0):
        failures.append("RESUME_PREFLIGHT_IDENTITY")
    if metadata and result.get("resume_preflight_sha256") != resume._metadata_sha(
            metadata):
        failures.append("RESUME_PREFLIGHT_SHA256")

    compact_paths = sorted(
        path for path in run_dir.glob("*.json")
        if path.name not in {
            "offline_preflight.json", "result.json", "independent_raw_audit.json"})
    rows = [_load(path) for path in compact_paths]
    round0 = [row for row in rows if row.get("round_index") == 0]
    if (len(round0) != 5
            or any(row.get("source_revision") != experiment_source_revision
                   for row in round0)):
        failures.append("IMMUTABLE_ROUND0_IDENTITY")

    failures = list(dict.fromkeys(failures))
    return {
        "schema_version": SCHEMA,
        "experiment_source_revision": experiment_source_revision,
        "hotfix_source_revision": hotfix_source_revision,
        "stage_config_sha256": primary.CONFIG_SHA256,
        "audit_passed": not failures,
        "failures": failures,
        "base_independent_audit": base_result,
        "primary_sha256": sha256(result_path) if result_path.is_file() else None,
        "resume_preflight_sha256": (
            sha256(metadata_path) if metadata_path.is_file() else None),
        "primary_route": result.get("route"),
        "primary_scientific_passed": result.get("passed"),
        "original_round0_rollouts_reused_without_rerun": result.get(
            "original_round0_rollouts_reused_without_rerun"),
        "models_fit_or_updated": 0,
        "claim_boundary": (
            "Independent full-raw ID2Z6 audit plus explicit authentication "
            "of the reporting-only ID2Z6R1 in-place continuation provenance; "
            "not controller, recovery, waypoint or reachability evidence."),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-config", type=Path, default=primary.CONFIG)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--experiment-source-revision", required=True)
    parser.add_argument("--hotfix-source-revision", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = audit(
        args.stage_config, args.run_dir,
        args.experiment_source_revision, args.hotfix_source_revision)
    output = args.output or args.run_dir / "independent_raw_audit.json"
    write_new(_inside(output, "output"), result)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
