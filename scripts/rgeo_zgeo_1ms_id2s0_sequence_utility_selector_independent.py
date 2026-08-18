#!/usr/bin/env python3
"""Separate-process deterministic recomputation for ID-2S0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_id0_vector_tail import inside_root, sha256, write_new  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2s0_sequence_utility_selector as primary  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-id2s0-sequence-utility-selector-independent-v1"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-config", type=Path, default=primary.CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    primary_path = inside_root(args.primary, "primary result")
    saved = json.loads(primary_path.read_text(encoding="utf-8"))
    recomputed = primary.execute(args.stage_config, args.source_revision)
    passed = saved == recomputed
    result = {"schema_version": SCHEMA, "source_revision": args.source_revision,
              "stage_config_sha256": primary.CONFIG_SHA256,
              "primary_sha256": sha256(primary_path), "audit_passed": passed,
              "failures": [] if passed else ["PRIMARY_RECOMPUTE"],
              "recomputed_route": recomputed.get("route"),
              "recomputed_selection": recomputed.get("selection"),
              "new_tsc_calls": 0, "reset_calls": 0, "plant_advances": 0,
              "models_fit_or_updated": 0,
              "claim_boundary": "Separate-process deterministic ID2S0 recomputation only; no TSC, model, authority, or control evidence."}
    write_new(inside_root(args.output, "independent output"), result)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())

