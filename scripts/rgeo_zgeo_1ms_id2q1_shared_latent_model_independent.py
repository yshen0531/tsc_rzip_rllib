#!/usr/bin/env python3
"""Separate-process deterministic recomputation audit for ID-2Q1."""
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

import rgeo_zgeo_1ms_id2q1_shared_latent_model_comparison as primary


SCHEMA = "rgeo-zgeo-1ms-id2q1-shared-latent-model-audit-v1"


def without_revision(value: dict[str, Any]) -> dict[str, Any]:
    copied = json.loads(json.dumps(value))
    copied.pop("source_revision", None)
    return copied


def audit(stage_path: Path, source_revision: str, output_dir: Path) -> dict[str, Any]:
    output_dir = primary.inside(output_dir, "ID2Q1 output directory")
    result_path = output_dir / "result.json"
    if not result_path.is_file():
        raise primary.IntegrityError("missing primary result")
    reported = primary.read_json(result_path)
    recomputed, payload = primary.compute(stage_path, source_revision)
    result_exact = without_revision(reported) == without_revision(recomputed)
    expected_payload_hash = None if payload is None else primary.canonical_sha(payload)
    model_path = output_dir / "model.json"
    if payload is None:
        model_exact = not model_path.exists() and reported.get("model_payload_sha256") is None
    else:
        model_exact = model_path.is_file() and primary.read_json(model_path) == payload
    passed = bool(
        result_exact
        and model_exact
        and reported.get("model_payload_sha256") == expected_payload_hash
        and reported.get("new_tsc_calls") == 0
        and reported.get("reset_calls") == 0
        and reported.get("plant_advances") == 0
        and reported.get("n1_records_used_for_fit") == 0
    )
    value = {
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "stage_config_sha256": primary.CONFIG_SHA256,
        "primary_result_sha256": primary.sha256(result_path),
        "primary_result_exactly_recomputed": result_exact,
        "model_payload_exactly_recomputed": model_exact,
        "model_payload_sha256": expected_payload_hash,
        "selected_kind": reported.get("selected_kind"),
        "primary_scientific_passed": reported.get("passed"),
        "new_tsc_calls": 0,
        "reset_calls": 0,
        "plant_advances": 0,
        "audit_passed": passed,
        "route": reported.get("route"),
        "claim_boundary": (
            "Separate-process deterministic recomputation of frozen ID2Q1; "
            "not independent calibration, uncertainty, authority or control evidence."
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
    except (primary.IntegrityError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"audit_passed": False, "error": f"{type(exc).__name__}: {exc}"}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
