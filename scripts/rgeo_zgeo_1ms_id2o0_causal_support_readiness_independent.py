#!/usr/bin/env python3
"""Separate-process exact recomputation for ID-2O0."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from scripts import rgeo_zgeo_1ms_id2o0_causal_support_readiness_audit as primary


SCHEMA = "rgeo-zgeo-1ms-id2o0-causal-support-readiness-independent-v1"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=primary.CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    original = primary.read_json(args.primary)
    recomputed = primary.compute(args.config, args.source_revision)
    failures = []
    if primary.canonical_sha(original) != primary.canonical_sha(recomputed):
        failures.append("PRIMARY_RECOMPUTATION_MISMATCH")
    result = {
        "schema_version": SCHEMA, "source_revision": args.source_revision,
        "stage_config_sha256": primary.sha256(args.config),
        "primary_sha256": primary.sha256(args.primary),
        "audit_passed": not failures, "failures": failures,
        "recomputed_route": recomputed["route"],
        "recomputed_readiness_gates": recomputed["readiness_gates"],
        "models_fit_or_updated": 0, "tsc_calls": 0, "reset_calls": 0,
        "plant_advances": 0, "holdout_opened": False,
        "claim_boundary": recomputed["claim_boundary"],
    }
    primary.write_new(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
