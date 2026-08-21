#!/usr/bin/env python3
"""Independent raw audit entrypoint for ID2Z33."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from scripts import rgeo_zgeo_1ms_id2z33_corrected_moving_center_d0 as primary
from scripts import rgeo_zgeo_1ms_id2z32_post_event_delayed_tail_d0_independent as old

SCHEMA = "rgeo-zgeo-1ms-id2z33-corrected-moving-center-d0-independent-v1"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=primary.CONFIG)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv); primary.install()
    try:
        value = old.audit(args.config, args.run_dir, args.source_revision)
        value["schema_version"] = SCHEMA
    except Exception as exc:
        value = {"schema_version": SCHEMA, "source_revision": args.source_revision,
                 "audit_passed": False, "failures": [f"{type(exc).__name__}:{exc}"]}
    primary.z32.z31.z30.z27.io.write_new(args.output, value)
    print(json.dumps(value, sort_keys=True, allow_nan=False))
    return 0 if value["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
