#!/usr/bin/env python3
"""Separate-process deterministic recomputation audit for ID-2M0."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

import rgeo_zgeo_1ms_id2m0_diagnostic_refit_attribution as primary


ROOT = primary.ROOT
SCHEMA = "rgeo-zgeo-1ms-id2m0-diagnostic-refit-audit-v1"


def _without_runtime_identity(value: dict[str, Any]) -> dict[str, Any]:
    result = json.loads(json.dumps(value))
    result.pop("source_revision", None)
    return result


def audit(stage_path: Path, source_revision: str, output_dir: Path) -> dict[str, Any]:
    output_dir = primary.inside(output_dir, "ID2M0 output directory")
    result_path = output_dir / "result.json"
    prediction_path = output_dir / "predictions.json"
    if not result_path.is_file() or not prediction_path.is_file():
        raise primary.IntegrityError("primary compact outputs are incomplete")
    reported = json.loads(result_path.read_text(encoding="utf-8"))
    reported_predictions = json.loads(prediction_path.read_text(encoding="utf-8"))
    recomputed, recomputed_predictions = primary.compute(stage_path, source_revision)
    result_exact = _without_runtime_identity(reported) == _without_runtime_identity(recomputed)
    predictions_exact = _without_runtime_identity(reported_predictions) == _without_runtime_identity(recomputed_predictions)
    result_hash = primary.sha256(result_path)
    prediction_hash = primary.sha256(prediction_path)
    passed = bool(result_exact and predictions_exact and reported.get("passed")
                  and reported.get("route") == primary.load_stage(stage_path)["routes"]["pass"])
    value = {
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "stage_config_sha256": primary.CONFIG_SHA256,
        "primary_result_sha256": result_hash,
        "primary_predictions_sha256": prediction_hash,
        "primary_result_exactly_recomputed": result_exact,
        "primary_predictions_exactly_recomputed": predictions_exact,
        "diagnostic_refits_recomputed": 4,
        "new_candidates": 0,
        "model_payload_sha256": None,
        "reset_calls": 0,
        "tsc_calls": 0,
        "plant_advances": 0,
        "audit_passed": passed,
        "route": reported.get("route"),
        "claim_boundary": "Separate-process deterministic replay of ID2M0 using the frozen ID2L1 implementation; not an independent model semantics theorem.",
    }
    audit_path = output_dir / "independent_audit.json"
    primary.write_new(audit_path, value)
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=primary.CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        value = audit(args.config, args.source_revision, args.output_dir)
        print(json.dumps(value, indent=2, sort_keys=True, allow_nan=False))
        return 0 if value["audit_passed"] else 2
    except (primary.IntegrityError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"audit_passed": False, "error": f"{type(exc).__name__}: {exc}"}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
