"""Independent deterministic full-refit audit for ID-2L1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_id2l1_structured_history_model import (  # noqa: E402
    CONFIG,
    CONFIG_SHA256,
    execute,
    inside,
    load_stage,
    sha256,
    write_new,
)


SCHEMA = "rgeo-zgeo-1ms-id2l1-structured-history-model-independent-v1"


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
    primary_path = inside(primary_path, "ID2L1 primary")
    primary = json.loads(primary_path.read_text(encoding="utf-8"))
    recomputed = execute(stage_path, source_revision, ROOT / ".codex_tmp" / "unused_id2l1", emit_artifacts=False)
    failures = []
    exact_fields = (
        "schema_version", "source_revision", "stage_config_sha256",
        "source_primary_sha256", "source_independent_sha256",
        "source_compact_inventory_sha256", "dataset_sha256", "model_payload_sha256",
        "unique_cells", "whole_history_families", "integrity_replays_fit_weight",
        "action_basis_rank", "id2i1_records_read", "id2j0_records_read",
        "id2c2_records_read", "calibration_records_read", "holdout_records_read",
        "models_fit", "reset_calls", "tsc_calls", "plant_advances", "passed",
        "route", "fresh_calibration_design_authorized", "controller_authorized",
        "claim_boundary",
    )
    for key in exact_fields:
        if primary.get(key) != recomputed.get(key):
            failures.append(f"PRIMARY_FIELD:{key}")
    difference = numeric_maximum(primary.get("comparison"), recomputed.get("comparison"))
    if difference > 1e-9:
        failures.append("COMPARISON_NUMERIC_REPRODUCIBILITY")
    for key in ("id2i1_records_read", "id2j0_records_read", "id2c2_records_read",
                "calibration_records_read", "holdout_records_read", "reset_calls", "tsc_calls", "plant_advances"):
        if int(primary.get(key, -1)) != 0:
            failures.append(f"FORBIDDEN_COUNTER:{key}")
    return {
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "primary_sha256": sha256(primary_path),
        "audit_passed": not failures,
        "failures": failures,
        "maximum_numeric_difference": difference,
        "dataset_sha256": recomputed["dataset_sha256"],
        "model_payload_sha256": recomputed["model_payload_sha256"],
        "selected_candidate": recomputed["comparison"]["selected_candidate"],
        "primary_passed": recomputed["passed"],
        "primary_route": recomputed["route"],
        "models_refit": recomputed["models_fit"],
        "reset_calls": 0,
        "tsc_calls": 0,
        "plant_advances": 0,
        "fresh_calibration_design_authorized": bool(recomputed["passed"] and not failures),
        "claim_boundary": "Independent deterministic development-data full refit only; not calibration, holdout or control qualification.",
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
