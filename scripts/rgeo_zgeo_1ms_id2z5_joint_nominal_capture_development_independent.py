#!/usr/bin/env python3
"""Independent full-raw audit wrapper for the frozen ID-2Z5 campaign."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_id0_vector_tail import write_new  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2z4r1_earlier_switch_capture_frontier_independent as raw  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2z5_joint_nominal_capture_development as primary  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-id2z5-joint-nominal-capture-development-independent-raw-v1"


def audit(stage_path: Path, run_dir: Path, source_revision: str) -> dict:
    original = raw.primary
    raw.primary = primary
    try:
        result = raw.audit(stage_path, run_dir, source_revision)
    finally:
        raw.primary = original
    result["schema_version"] = SCHEMA
    result.pop("finite_capture_candidate", None)
    result["development_data_ready"] = bool(
        result.get("audit_passed")
        and result.get("recomputed_route")
        == primary.load(stage_path)[0]["routes"]["capture_candidate"])
    result["claim_boundary"] = (
        "Independent full-raw finite ID2Z5 development audit; not hold, "
        "recovery, controller, waypoint or reachability qualification.")
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
    write_new(raw.inside(output, "output"), result)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
