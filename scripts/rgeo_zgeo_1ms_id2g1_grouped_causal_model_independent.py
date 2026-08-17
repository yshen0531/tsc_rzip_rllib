"""Deterministic raw re-extraction/refit audit for ID-2G1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_id2g1_grouped_causal_model import (  # noqa: E402
    CONFIG,
    CONFIG_SHA256,
    execute,
    inside,
    load_stage,
    sha256,
    write_new,
)


SCHEMA = "rgeo-zgeo-1ms-id2g1r1-full-card15-model-independent-v1"


def numeric_maximum(left: Any, right: Any) -> float:
    if isinstance(left, bool) or isinstance(right, bool):
        return 0.0 if left is right else float("inf")
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return abs(float(left) - float(right))
    if isinstance(left, dict) and isinstance(right, dict):
        if set(left) != set(right):
            return float("inf")
        return max((numeric_maximum(left[key], right[key]) for key in left), default=0.0)
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return float("inf")
        return max((numeric_maximum(a, b) for a, b in zip(left, right)), default=0.0)
    return 0.0 if left == right else float("inf")


def audit(stage_path: Path, primary_path: Path, source_revision: str) -> dict[str, Any]:
    stage = load_stage(stage_path)
    primary_path = inside(primary_path, "ID2G1 primary")
    primary = json.loads(primary_path.read_text(encoding="utf-8"))
    recomputed = execute(stage_path, source_revision, ROOT / ".codex_tmp" / "unused_id2g1", emit_artifacts=False)
    failures = []
    for key in ("schema_version", "source_revision", "stage_config_sha256",
                "source_primary_sha256", "source_independent_sha256", "source_inventory_sha256",
                "dataset_sha256", "unique_cells", "contexts", "replays_counted_as_independent_samples",
                "executor_representation", "executor_dimension", "id2c2_records_read",
                "calibration_records_read", "holdout_records_read", "reset_calls", "tsc_calls",
                "plant_advances", "passed", "route", "fresh_calibration_design_authorized",
                "controller_authorized", "claim_boundary"):
        if primary.get(key) != recomputed.get(key):
            failures.append(f"PRIMARY_FIELD:{key}")
    difference = numeric_maximum(primary.get("comparison"), recomputed.get("comparison"))
    if difference > 1e-10:
        failures.append("COMPARISON_NUMERIC_REPRODUCIBILITY")
    if int(primary.get("id2c2_records_read", -1)) != stage["data_contract"]["id2c2_records_allowed"]:
        failures.append("ID2C2_READ")
    if int(primary.get("calibration_records_read", -1)) != stage["data_contract"]["calibration_records_allowed"]:
        failures.append("CALIBRATION_READ")
    if int(primary.get("holdout_records_read", -1)) != stage["data_contract"]["holdout_records_allowed"]:
        failures.append("HOLDOUT_READ")
    return {
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "primary_sha256": sha256(primary_path),
        "audit_passed": not failures,
        "failures": failures,
        "maximum_numeric_difference": difference,
        "dataset_sha256": recomputed["dataset_sha256"],
        "selected_candidate": recomputed["comparison"]["selected_candidate"],
        "primary_passed": recomputed["passed"],
        "primary_route": recomputed["route"],
        "id2c2_records_read": 0,
        "calibration_records_read": 0,
        "holdout_records_read": 0,
        "reset_calls": 0,
        "tsc_calls": 0,
        "plant_advances": 0,
        "fresh_calibration_design_authorized": bool(recomputed["passed"] and not failures),
        "claim_boundary": "Independent deterministic raw re-extraction and full refit; not calibration, holdout or control qualification.",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-config", type=Path, default=CONFIG)
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    value = audit(args.stage_config, args.primary, args.source_revision)
    write_new(args.output, value)
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0 if value["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
