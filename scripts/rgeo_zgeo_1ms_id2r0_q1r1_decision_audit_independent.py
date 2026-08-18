#!/usr/bin/env python3
"""Separate-process deterministic recomputation for ID-2R0."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import rgeo_zgeo_1ms_id2r0_q1r1_decision_audit as primary


SCHEMA = "rgeo-zgeo-1ms-id2r0-q1r1-decision-audit-independent-v1"


def without_revision(value: dict[str, Any]) -> dict[str, Any]:
    copied = json.loads(json.dumps(value))
    copied.pop("source_revision", None)
    return copied


def audit(config: Path, source_revision: str, output_dir: Path) -> dict[str, Any]:
    output_dir = primary.inside(output_dir, "ID2R0 output directory")
    result_path = output_dir / "result.json"
    predictions_path = output_dir / "predictions.json"
    if not result_path.is_file() or not predictions_path.is_file():
        raise primary.IntegrityError("missing primary result or predictions")
    reported = primary.read_json(result_path)
    reported_predictions = primary.read_json(predictions_path)
    recomputed, recomputed_predictions = primary.compute(config, source_revision)
    result_exact = without_revision(reported) == without_revision(recomputed)
    predictions_exact = without_revision(reported_predictions) == without_revision(recomputed_predictions)
    passed = bool(
        result_exact
        and predictions_exact
        and reported.get("audit_passed") is True
        and reported.get("q1_original_verdict_unchanged") is True
        and reported.get("new_candidate_count") == 0
        and reported.get("full_data_model_fits") == 0
        and reported.get("model_payloads_emitted") == 0
        and reported.get("new_tsc_calls") == 0
        and reported.get("reset_calls") == 0
        and reported.get("plant_advances") == 0
        and reported.get("n1_records_read") == 0
        and reported.get("predictions_canonical_sha256") ==
        primary.canonical_sha(reported_predictions)
    )
    value = {
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "stage_config_sha256": primary.CONFIG_SHA256,
        "primary_result_sha256": primary.sha256(result_path),
        "primary_predictions_sha256": primary.sha256(predictions_path),
        "primary_result_exactly_recomputed": result_exact,
        "primary_predictions_exactly_recomputed": predictions_exact,
        "primary_route": reported.get("route"),
        "q1_original_verdict_unchanged": reported.get("q1_original_verdict_unchanged"),
        "new_candidate_count": 0,
        "model_payloads_emitted": 0,
        "new_tsc_calls": 0,
        "reset_calls": 0,
        "plant_advances": 0,
        "n1_records_read": 0,
        "audit_passed": passed,
        "claim_boundary": (
            "Separate-process deterministic recomputation of ID2R0 only; "
            "not independent calibration, authority, recovery, model, or control evidence."
        ),
    }
    primary.write_new(output_dir / "independent_audit.json", value)
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
    except (primary.IntegrityError, OSError, ValueError, KeyError,
            json.JSONDecodeError) as exc:
        print(json.dumps({"audit_passed": False,
                          "error": f"{type(exc).__name__}: {exc}"}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
