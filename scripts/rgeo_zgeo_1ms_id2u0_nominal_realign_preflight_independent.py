#!/usr/bin/env python3
"""Separate-process exact recomputation for ID-2U0."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import rgeo_zgeo_1ms_id2u0_nominal_realign_preflight as primary


SCHEMA = "rgeo-zgeo-1ms-id2u0-nominal-realign-independent-v1"


def canonical_sha(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise primary.IntegrityError("primary result must be an object")
    return value


def execute(primary_result: Path, config: Path = primary.CONFIG) -> dict[str, Any]:
    primary_result = primary.inside(primary_result, "primary result")
    saved = read_json(primary_result)
    recomputed = primary.execute(config)
    failures = []
    if saved.get("passed") is not True:
        failures.append("PRIMARY_NOT_PASS")
    if saved.get("route") != recomputed.get("route"):
        failures.append("ROUTE")
    for key in (
        "stage_config_sha256", "new_tsc_calls", "reset_calls", "plant_advances",
        "models_fit_or_trained", "holdout_records_read", "family_count",
        "stream_count", "role_counts", "nominal_metrics_from_id2c1",
        "nominal_lineage", "event_map", "early_late_alignment",
        "prospective_campaign_streams", "claim_boundary",
    ):
        if canonical_sha(saved.get(key)) != canonical_sha(recomputed.get(key)):
            failures.append(f"MISMATCH:{key}")
    return {
        "schema_version": SCHEMA,
        "audit_passed": not failures,
        "failures": failures,
        "primary_result_sha256": primary.sha256(primary_result),
        "primary_source_revision": saved.get("source_revision"),
        "recomputed_route": recomputed["route"],
        "recomputed_stream_count": recomputed["stream_count"],
        "recomputed_family_count": recomputed["family_count"],
        "primary_result_exactly_recomputed": not failures,
        "new_tsc_calls": 0, "reset_calls": 0, "plant_advances": 0,
        "models_fit_or_trained": 0, "holdout_records_read": 0,
        "claim_boundary": "Separate-process exact ID2U0 recomputation; not a plant, model, controller or safety result.",
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--primary-result", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=primary.CONFIG)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = execute(args.primary_result, args.config)
    primary.write_new(args.output, result)
    print(json.dumps({"audit_passed": result["audit_passed"],
                      "route": result["recomputed_route"]}, sort_keys=True))
    return 0 if result["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
