#!/usr/bin/env python3
"""Independent cross-check of an ID-2C0 control-relevance result."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_id2b1_structured_model_development import (  # noqa: E402
    feature_vector,
    load_config as load_id2b1_config,
    load_rows,
)
from scripts.rgeo_zgeo_1ms_id2c0_control_relevance_audit import (  # noqa: E402
    CONFIG_SHA256,
    PASS,
    inside,
    load_stage,
    read_json,
    sha256_file,
    write_new,
)


SCHEMA = "rgeo-zgeo-1ms-id2c0-control-relevance-independent-v1"


def independent(repo_root: Path, config_path: Path, id2a_run_dir: Path, primary_path: Path) -> dict[str, Any]:
    failures: list[str] = []
    try:
        _, bound = load_stage(repo_root, config_path)
        primary_path = inside(repo_root, primary_path, "ID2C0 primary")
        primary = read_json(primary_path)
        id2b1_config = load_id2b1_config(
            repo_root, repo_root / "configs/rgeo_zgeo_1ms_id2b1_structured_model_development.json"
        )
        _, rows, identity = load_rows(repo_root, id2b1_config, id2a_run_dir)
        baselines = {row["context_id"]: row for row in rows if row["direction_id"] == "baseline"}
        arms = sorted(
            {
                (row["direction_id"], row["sign"], int(row["duration_issues"]))
                for row in rows
                if row["direction_id"] != "baseline"
            }
        )
        indexed = {
            (row["context_id"], row["direction_id"], row["sign"], int(row["duration_issues"])): row
            for row in rows
        }
        recomputed: dict[str, float] = {}
        for model_id in ("stable_exp_signed", "stable_exp_signed_even"):
            maximum = 0.0
            for arm in arms:
                vectors = []
                for context in sorted(baselines):
                    chunks = []
                    for horizon in range(1, 23):
                        chunks.append(
                            feature_vector(indexed[(context, *arm)], 10, horizon, model_id, id2b1_config)
                            - feature_vector(baselines[context], 10, horizon, model_id, id2b1_config)
                        )
                    vectors.append(np.concatenate(chunks))
                for candidate in vectors[1:]:
                    maximum = max(maximum, float(np.max(np.abs(candidate - vectors[0]))))
            recomputed[model_id] = maximum
        b0 = next(value["json"] for key, value in bound.items() if "id2b0_readiness" in key and key.endswith("result.json"))
        c2a = next(value["json"] for key, value in bound.items() if "c2a_search_result" in key)
        id1b = next(value["json"] for key, value in bound.items() if "id1b_result" in key)
        expected = {
            "row_count": 39,
            "exact_collision_count": len(b0["analysis"]["exact_causal_collisions"]),
            "constant_dwell_passed": c2a["passed"],
            "positive_span_passed": id1b["scientific_metrics"]["positive_span_passed"],
        }
        checks = {
            "primary_schema": primary.get("schema_version") == "rgeo-zgeo-1ms-id2c0-control-relevance-audit-result-v1",
            "primary_config": primary.get("config_sha256") == CONFIG_SHA256,
            "primary_route": primary.get("route") == PASS and primary.get("passed") is True,
            "primary_hashes": primary.get("bound_input_sha256")
            == {key: value["sha256"] for key, value in sorted(bound.items())},
            "primary_source_identity": primary.get("source_identity") == identity,
            "row_count": expected["row_count"] == len(rows),
            "no_exact_collision": expected["exact_collision_count"] == 0,
            "no_constant_hold": expected["constant_dwell_passed"] is False,
            "no_positive_span": expected["positive_span_passed"] is False,
            "signed_feature_cancellation": recomputed["stable_exp_signed"] <= 1e-12,
            "signed_even_feature_cancellation": recomputed["stable_exp_signed_even"] <= 1e-12,
            "zero_execution": all(
                primary["counters"].get(key) == 0
                for key in ("plant_advances", "tsc_calls", "models_fit_or_trained", "calibration_records_read", "holdout_records_read")
            ),
        }
        failures = [key for key, passed in checks.items() if not passed]
        return {
            "schema_version": SCHEMA,
            "primary_sha256": sha256_file(primary_path),
            "audit_passed": not failures,
            "failures": failures,
            "checks": checks,
            "recomputed_feature_cancellation": recomputed,
            "recomputed_evidence": expected,
            "claim_boundary": "Independent zero-TSC arithmetic audit; no model or controller qualification.",
        }
    except Exception as exc:
        return {
            "schema_version": SCHEMA,
            "audit_passed": False,
            "failures": [f"{type(exc).__name__}:{exc}"],
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--id2a-run-dir", type=Path, required=True)
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = independent(ROOT, args.config, args.id2a_run_dir, args.primary)
    write_new(inside(ROOT, args.output, "ID2C0 independent output"), result)
    print(json.dumps({"audit_passed": result["audit_passed"], "failures": result["failures"]}, sort_keys=True))
    return 0 if result["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
