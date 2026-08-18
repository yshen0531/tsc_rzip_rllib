#!/usr/bin/env python3
"""Separate-process deterministic recomputation audit for ID-2M1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

import rgeo_zgeo_1ms_id2m1_bounded_event_innovation_model as primary


SCHEMA = "rgeo-zgeo-1ms-id2m1-bounded-event-innovation-audit-v1"


def _without_revision(value: dict[str, Any]) -> dict[str, Any]:
    result = json.loads(json.dumps(value))
    result.pop("source_revision", None)
    return result


def audit(stage_path: Path, source_revision: str, output_dir: Path) -> dict[str, Any]:
    output_dir = primary.inside(output_dir, "ID2M1 output directory")
    result_path = output_dir / "result.json"
    if not result_path.is_file():
        raise primary.IntegrityError("missing primary result")
    reported = json.loads(result_path.read_text(encoding="utf-8"))
    recomputed, payload = primary.compute(stage_path, source_revision)
    result_exact = _without_revision(reported) == _without_revision(recomputed)
    expected_payload_hash = primary.canonical_sha256(payload) if payload else None
    model_path = output_dir / "model.json"
    if payload is None:
        model_exact = not model_path.exists() and reported.get("model_payload_sha256") is None
    else:
        model_exact = model_path.is_file() and json.loads(model_path.read_text(encoding="utf-8")) == payload
    passed = bool(result_exact and model_exact and reported.get("model_payload_sha256") == expected_payload_hash)
    value = {
        "schema_version": SCHEMA, "source_revision": source_revision,
        "stage_config_sha256": primary.CONFIG_SHA256,
        "primary_result_sha256": primary.sha256(result_path),
        "primary_result_exactly_recomputed": result_exact,
        "model_payload_exactly_recomputed": model_exact,
        "model_payload_sha256": expected_payload_hash,
        "selected_candidate": reported.get("selected_candidate"),
        "primary_scientific_passed": reported.get("passed"),
        "reset_calls": 0, "tsc_calls": 0, "plant_advances": 0,
        "audit_passed": passed, "route": reported.get("route"),
        "claim_boundary": "Separate-process deterministic recomputation of the frozen ID2M1 development comparison; not an independent safety or calibration claim.",
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
