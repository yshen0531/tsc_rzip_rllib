#!/usr/bin/env python3
"""Deterministic replay audit for the zero-TSC ID-2Z19 comparison."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

import rgeo_zgeo_1ms_id2z19_two_candidate_model_comparison as primary


def audit(output_dir: Path) -> dict:
    output = primary.inside(output_dir, "ID2Z19 output")
    result_path = output / "result.json"
    result = primary.read_json(result_path)
    recomputed, artifact = primary.compute(primary.CONFIG, result["source_revision"])
    failures = []
    if primary.canonical_sha256(recomputed) != primary.canonical_sha256(result):
        failures.append("PRIMARY_RESULT_REPLAY")
    artifact_path = output / "selected_model.json"
    if artifact is None:
        if artifact_path.exists():
            failures.append("UNEXPECTED_MODEL_ARTIFACT")
    else:
        if not artifact_path.is_file():
            failures.append("MISSING_MODEL_ARTIFACT")
        elif primary.canonical_sha256(primary.read_json(artifact_path)) != primary.canonical_sha256(artifact):
            failures.append("MODEL_ARTIFACT_REPLAY")
    if result.get("new_tsc_calls") != 0 or result.get("plant_advances") != 0:
        failures.append("NONZERO_PLANT_COUNT")
    if result.get("calibration_records_read") != 0 or result.get("blind_holdout_records_read") != 0:
        failures.append("HELD_DATA_READ")
    value = {
        "schema_version": "rgeo-zgeo-1ms-id2z19-deterministic-replay-audit-v1",
        "audit_passed": not failures,
        "failures": failures,
        "primary_sha256": primary.sha256(result_path),
        "primary_route": result.get("route"),
        "recomputed_route": recomputed.get("route"),
        "selected_candidate_id": result.get("comparison", {}).get("selected_candidate_id"),
        "model_artifact_present": artifact is not None,
        "new_tsc_calls": 0, "reset_calls": 0, "plant_advances": 0,
        "claim_boundary": "Deterministic same-code replay audit; not a structurally independent scientific evaluator or calibration."
    }
    path = output / "deterministic_replay_audit.json"
    primary.write_new(path, value)
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        value = audit(args.output)
        print(json.dumps(value, indent=2, sort_keys=True))
        return 0 if value["audit_passed"] else 2
    except Exception as exc:
        print(json.dumps({"audit_passed": False, "failures": [f"AUDIT_EXCEPTION:{exc}"],
                          "new_tsc_calls": 0}, indent=2, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
