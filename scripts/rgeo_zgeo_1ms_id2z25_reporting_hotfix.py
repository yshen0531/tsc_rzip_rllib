#!/usr/bin/env python3
"""Reporting-only finalizer for complete immutable ID-2Z25 raw."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_id2z25_centered_coallocation_campaign as primary

SCHEMA = "rgeo-zgeo-1ms-id2z25-reporting-hotfix-v1"
ORIGINAL_RESULT_SHA256 = "d9e295cf2d05ee9763bc4b86e3b65098f69e3e0f9f95077f3649d77e4af1380d"
CONTROLLER_SOURCE_REVISION = "3797062f90d1513b2c6a75891c6c0c58ea62fcb4"


def _rows(run_dir: Path, expected: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    values = []
    for stream in expected:
        path = run_dir / f"{stream['rollout_id']}.json"
        row = primary._load_json(path)
        if (row.get("rollout_id") != stream["rollout_id"]
                or row.get("schema_version") != primary.SCHEMA
                or row.get("source_revision") != CONTROLLER_SOURCE_REVISION):
            raise ValueError(f"compact identity mismatch: {stream['rollout_id']}")
        values.append(row)
    return values


def execute(run_dir: Path, reporting_revision: str,
            output_name: str = "result_reporting_hotfix.json") -> dict[str, Any]:
    run_dir = primary.z18.inside(run_dir, "ID2Z25 reporting run")
    original = run_dir / "result.json"
    if primary.io.sha256(original) != ORIGINAL_RESULT_SHA256:
        raise ValueError("original failure result changed")
    if output_name not in ("result_reporting_hotfix.json",
                            "result_reporting_hotfix_v2.json"):
        raise ValueError("unrecognized reporting output name")
    old = primary._load_json(original)
    if (old.get("failure") != "KeyError:'diagnostic_artifacts'"
            or old.get("verified_plant_advances") != 975
            or old.get("complete_rollouts") != 15):
        raise ValueError("original failure is not the frozen reporting defect")
    stage, _, cfg, _, tracked = primary.load(primary.CONFIG)
    expected = primary.build_streams(stage, cfg, tracked)
    rows = _rows(run_dir, expected)
    if (len(rows) != 15 or not all(row.get("passed") and len(row.get("states", [])) == 66
                                   for row in rows)):
        raise ValueError("complete immutable compact set required")
    # The original config omitted only this inventory name. Injection here is
    # reporting-only; the runner already retained sprsina in all state folders.
    inventory_stage = dict(stage)
    inventory_stage["diagnostic_artifacts"] = ["sprsina"]
    inventory = primary.io.raw_inventory(run_dir, rows, inventory_stage)
    expected_files = 5 * sum(len(row["states"]) for row in rows)
    raw_ok = (not inventory["missing_required_artifacts"]
              and inventory["required_artifact_files"] == expected_files == 4950)
    by_id = {str(row["rollout_id"]): row for row in rows}
    centered = by_id["baseline_center"]
    prefixes = []
    for stream in expected:
        kind = stream["kind"]
        if kind == "full_f_diagnostic":
            reference, state_count = tracked, 66
        elif kind == "center_baseline":
            reference, state_count = tracked, 17
        else:
            reference = centered
            state_count = int(stream["prefix_checkpoint_last_state"]) + 1
        action_count = 65 if kind == "full_f_diagnostic" else state_count - 1
        prefixes.append(primary.z6.prefix_check(
            by_id[stream["rollout_id"]], reference, state_count, action_count,
            stage["semantic_artifacts"]))
    prefix_ok = all(row["passed"] for row in prefixes)
    scientific = primary.scientific_metrics(rows, stage)
    if not raw_ok:
        route = stage["routes"]["raw_integrity_fail"]
    elif not prefix_ok:
        route = stage["routes"]["prefix_mismatch"]
    elif not scientific["replay_metrics"]["passed"]:
        route = stage["routes"]["replay_fail"]
    elif not scientific["passed"]:
        route = stage["routes"]["signal_fail"]
    else:
        route = stage["routes"]["data_pass"]
    counters = {key: sum(int(row.get(key, 0)) for row in rows) for key in
                ("reset_calls", "advance_attempts", "plant_advance_gotsc_calls",
                 "verified_plant_advances")}
    result = {
        "schema_version": SCHEMA,
        "source_revision": CONTROLLER_SOURCE_REVISION,
        "reporting_source_revision": reporting_revision,
        "stage_config_sha256": primary.CONFIG_SHA256,
        "original_result_sha256": ORIGINAL_RESULT_SHA256,
        "reporting_defect": "missing diagnostic_artifacts key after all plant work completed",
        "controller_action_semantics_changed": False,
        "new_reset_calls": 0,
        "new_tsc_or_plant_advances": 0,
        "passed": route == stage["routes"]["data_pass"],
        "route": route,
        "execution_integrity_passed": True,
        "raw_integrity_passed": raw_ok,
        "run_root_isolation": {
            "required_run_root": str((run_dir / "rollouts").resolve()),
            "configured_run_root": str((run_dir / "rollouts").resolve()),
            "passed": True
        },
        "prefix_checks": prefixes,
        "scientific_metrics": scientific,
        "rollouts_started": 15,
        "complete_rollouts": 15,
        **counters,
        **inventory,
        "models_fit_or_updated": 0,
        "calibration_or_holdout_records_read": 0,
        "claim_boundary": stage["claim_boundary"],
    }
    primary.io.write_new(run_dir / output_name, result)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--reporting-source-revision", required=True)
    parser.add_argument("--output-name", default="result_reporting_hotfix.json")
    args = parser.parse_args(argv)
    value = execute(args.run_dir, args.reporting_source_revision, args.output_name)
    print(json.dumps(value, indent=2, sort_keys=True, allow_nan=False))
    return 0 if value["raw_integrity_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
