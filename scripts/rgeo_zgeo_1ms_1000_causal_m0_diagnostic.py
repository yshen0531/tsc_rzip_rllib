#!/usr/bin/env python3
"""Deterministic attribution refit of the frozen fixed-1000 M0 model."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_1000_causal_m0 as m0  # noqa: E402


PRIMARY_SHA256 = "2f1e15426c5f48597c2ebb40c1db7e2b736517a5e9f4a43259191a8ba1c2b5e6"


def execute(config: Path, primary_result: Path, source_revision: str, output: Path) -> dict[str, Any]:
    primary_result = m0.b0.inside_root(primary_result, "M0 primary result")
    if m0.b0.sha256(primary_result) != PRIMARY_SHA256:
        raise m0.InputIntegrityError("M0 primary result hash mismatch")
    primary_payload = json.loads(primary_result.read_text(encoding="utf-8"))
    if primary_payload.get("route") != "ONE_MS_NR1000M0_CAUSAL_SHORT_HORIZON_MODEL_INSUFFICIENT":
        raise m0.InputIntegrityError("M0 primary route mismatch")
    stage, cfg, rows = m0.load(config)
    samples, _, _, feature_names, blind_width = m0.feature_rows(
        rows, cfg, stage["fixed_memory_poles"], stage["executed_action_rank"]
    )
    scales = np.asarray(stage["output_scales"], dtype=float)
    baseline_by_issue = {sample["issue"]: sample for sample in samples if sample["group"] == "b0"}
    folds = []
    all_large = []
    for fold in stage["whole_family_folds"]:
        test = [sample for sample in samples if m0._selectors(stage, fold, sample["family"])]
        train = [sample for sample in samples if not m0._selectors(stage, fold, sample["family"])]
        model = m0.fit_ridge(train, len(feature_names), stage["ridge_alpha"], scales)
        prediction = m0.predict(model, test, scales)
        truth = np.asarray([sample["y"] for sample in test])
        r_error = np.abs(prediction[:, 0] - truth[:, 0])
        train_x = np.asarray([sample["x"] for sample in train])[:, model["keep"]]
        train_z = (train_x - model["mean"][model["keep"]]) / model["std"][model["keep"]]
        test_x = np.asarray([sample["x"] for sample in test])[:, model["keep"]]
        test_z = (test_x - model["mean"][model["keep"]]) / model["std"][model["keep"]]
        distances = np.asarray([np.min(np.linalg.norm(train_z - row, axis=1)) for row in test_z])
        large = []
        for index in np.flatnonzero(r_error > 0.35):
            row = {
                "family": test[index]["family"], "issue": test[index]["issue"],
                "effect_state": test[index]["issue"] + 1,
                "truth_delta_r_mm": float(truth[index, 0]),
                "predicted_delta_r_mm": float(prediction[index, 0]),
                "absolute_r_error_mm": float(r_error[index]),
                "nearest_standardized_train_distance": float(distances[index]),
                "sign_flip": bool(truth[index, 0] * prediction[index, 0] < 0),
            }
            large.append(row)
            all_large.append({"fold": fold["name"], **row})
        top = sorted(large, key=lambda row: row["absolute_r_error_mm"], reverse=True)[:20]
        folds.append({
            "fold": fold["name"], "test_rows": len(test), "large_r_error_rows": len(large),
            "large_r_error_fraction": len(large) / len(test),
            "large_sign_flips": sum(row["sign_flip"] for row in large),
            "large_rows_supported_distance_le_median": sum(
                row["nearest_standardized_train_distance"] <= float(np.median(distances)) for row in large
            ),
            "nearest_distance_median": float(np.median(distances)),
            "nearest_distance_p95": float(np.quantile(distances, 0.95)),
            "top_large_rows": top,
        })
    state_counts = Counter(row["effect_state"] for row in all_large)
    family_counts = Counter(row["family"] for row in all_large)
    result = {
        "schema_version": f"{m0.SCHEMA}-diagnostic-v1",
        "kind": "deterministic_diagnostic_refit_no_new_candidate",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_revision": source_revision, "plant_advances": 0,
        "primary_result_sha256": PRIMARY_SHA256,
        "primary_route_preserved": primary_payload["route"],
        "folds": folds, "large_r_error_rows": len(all_large),
        "large_r_error_sign_flips": sum(row["sign_flip"] for row in all_large),
        "large_r_error_effect_state_counts": dict(sorted(state_counts.items())),
        "large_r_error_family_counts": dict(sorted(family_counts.items())),
        "conclusion_boundary": "attribution only; no model selection, qualification or controller authorization",
    }
    m0.b0.write_new(output, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--primary-result", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = execute(
        args.config.resolve(), args.primary_result.resolve(), args.source_revision, args.output.resolve()
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
