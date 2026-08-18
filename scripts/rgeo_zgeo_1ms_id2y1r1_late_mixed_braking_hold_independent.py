#!/usr/bin/env python3
"""Independent full-raw audit entrypoint for ID-2Y1R1."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_id0_vector_tail import write_new  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2y1_late_mixed_braking_hold_independent as base  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2y1r1_late_mixed_braking_hold as primary  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-id2y1r1-independent-raw-v1"


def audit(stage_path: Path, run_dir: Path, source_revision: str) -> dict[str, Any]:
    """Reuse the frozen full-raw parser with the repaired stage module.

    Y1 and Y1R1 have identical horizon, raw lifecycle, prefix length, counters
    and gates.  Only the prospectively changed action matrix and identities
    differ; replacing the module binding makes every expected action and route
    come from the R1 implementation while retaining the separate raw parser.
    """
    saved_primary, saved_schema = base.primary, base.SCHEMA
    try:
        base.primary, base.SCHEMA = primary, SCHEMA
        result = base.audit(stage_path, run_dir, source_revision)
    finally:
        base.primary, base.SCHEMA = saved_primary, saved_schema
    result["claim_boundary"] = (
        "Independent full-raw ID2Y1R1 audit; PASS/FAIL remains finite "
        "source-local repaired late mixed-braking branch evidence only.")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-config", type=Path, default=primary.CONFIG)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = audit(args.stage_config, args.run_dir, args.source_revision)
    output = args.output or args.run_dir / "independent_raw_audit.json"
    write_new(base.inside(output, "output"), result)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
