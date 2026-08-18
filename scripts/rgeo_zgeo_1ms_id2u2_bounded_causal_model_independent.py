#!/usr/bin/env python3
"""Separate-process deterministic recomputation for ID-2U2."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

import rgeo_zgeo_1ms_id2u2_bounded_causal_model_comparison as primary


SCHEMA = "rgeo-zgeo-1ms-id2u2-bounded-causal-model-independent-v1"


def audit(stage_path: Path, primary_dir: Path) -> dict[str, Any]:
    stage = primary.load_stage(stage_path)
    folder = primary.inside(primary_dir, "primary output directory")
    result_path = primary.inside(folder / "result.json", "primary result")
    result = primary.read_json(result_path)
    if result.get("schema_version") != primary.SCHEMA:
        raise primary.IntegrityError("primary result schema changed")
    if result.get("stage_config_sha256") != primary.sha256(primary.inside(stage_path, "stage config")):
        raise primary.IntegrityError("primary stage SHA changed")
    recomputed_result, recomputed_model = primary.compute(stage_path, str(result["source_revision"]))
    result_equal = primary.canonical_sha256(result) == primary.canonical_sha256(recomputed_result)
    expected_model_sha = result.get("model_payload_sha256")
    model_path = folder / "model.json"
    model_failures: list[str] = []
    if expected_model_sha is None:
        if model_path.exists() or recomputed_model is not None:
            model_failures.append("UNEXPECTED_MODEL")
        model_equal = not model_failures
        primary_model_file_sha = None
    else:
        if not model_path.is_file() or recomputed_model is None:
            model_failures.append("MISSING_MODEL")
            model_equal = False
            primary_model_file_sha = None
        else:
            saved = primary.read_json(model_path)
            primary_model_file_sha = primary.sha256(model_path)
            model_equal = (
                primary.canonical_sha256(saved) == expected_model_sha
                and primary.canonical_sha256(recomputed_model) == expected_model_sha
            )
            if not model_equal:
                model_failures.append("MODEL_MISMATCH")
    failures = list(model_failures)
    if not result_equal:
        failures.append("RESULT_MISMATCH")
    if result.get("calibration_family_ids_read") or result.get("blind_holdout_family_ids_read"):
        failures.append("FORBIDDEN_DATA_READ")
    passed = not failures
    return {
        "schema_version": SCHEMA,
        "source_revision": result["source_revision"],
        "stage_config_sha256": result["stage_config_sha256"],
        "audit_passed": passed,
        "route": "ONE_MS_ID2U2_INDEPENDENT_RECOMPUTATION_PASS" if passed else "ONE_MS_ID2U2_INDEPENDENT_RECOMPUTATION_FAIL",
        "failures": failures,
        "primary_result_sha256": primary.sha256(result_path),
        "primary_result_canonical_sha256": primary.canonical_sha256(result),
        "recomputed_result_canonical_sha256": primary.canonical_sha256(recomputed_result),
        "result_equal": result_equal,
        "primary_model_file_sha256": primary_model_file_sha,
        "model_payload_equal": model_equal,
        "primary_passed": bool(result["passed"]),
        "primary_route": result["route"],
        "selected_kind": result.get("comparison", {}).get("selected_kind"),
        "development_cells_read": result.get("development_cells_read"),
        "calibration_family_ids_read": [],
        "blind_holdout_family_ids_read": [],
        "new_tsc_calls": 0,
        "reset_calls": 0,
        "plant_advances": 0,
        "claim_boundary": stage["claim_boundary"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=primary.CONFIG)
    parser.add_argument("--primary-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    value = audit(args.config, args.primary_dir)
    primary.write_new(args.output, value)
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0 if value["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
