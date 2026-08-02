#!/usr/bin/env python3
"""Post-result input-support forensic for the final T13S7R1 audit."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics
from typing import Any, Mapping, Sequence

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s6_independent_raw_audit as common,
)
from docs.codex.audit_tools import (
    stage4_2r3c3t13s7_causal_multi_history_tube_audit as s7,
)


STAGE = "Stage4.2R3c3T13S7R1SupportForensic"
SOURCE_R1_SHA256 = (
    "9fb7c8ce1efc03a66d69b8b8c848bff9509196cfc2e7b583f98eb547dd829c80"
)
SOURCE_R1_ROUTE = "CAMPAIGN_SPECIFIC_CAUSAL_MULTI_HYPOTHESIS_TUBE_INSUFFICIENT_REDESIGN"
FROZEN_SUPPORT_THRESHOLD = 0.15


def authenticate_r1(path: Path) -> Mapping[str, Any]:
    if common._sha256(path) != SOURCE_R1_SHA256:
        raise ValueError("T13S7R1 source audit SHA-256 mismatch")
    payload = common._strict_json(path)
    summary = payload.get("summary") or {}
    if not (
        payload.get("stage") == "Stage4.2R3c3T13S7R1"
        and payload.get("passed") is False
        and payload.get("route") == SOURCE_R1_ROUTE
        and summary.get("combined_raw_count") == 120
        and summary.get("local_rank_pass_count") == 16
        and summary.get("local_tube_pass_count") == 16
        and summary.get("heldout_prediction_count") == 112
        and summary.get("supported_hypothesis_pass_count") == 0
        and summary.get("componentwise_containment_pass_count") == 0
        and summary.get("scaled_relative_error_pass_count") == 0
    ):
        raise ValueError("T13S7R1 source audit content mismatch")
    return payload


def _contexts_and_models(
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    s1_raw_dir = (
        args.s1_run / "stage4_2r3c3t13s1_minimal_transition_sentinel" / "raw"
    )
    s5_raw_dir = (
        args.s5_run / "stage4_2r3c3t13s5_lattice_native_split_holdout" / "raw"
    )
    _, s1_raw, s1_digest = s7._inventory(s1_raw_dir)
    _, s5_raw, s5_digest = s7._inventory(s5_raw_dir)
    if (s1_digest, s5_digest) != (s7.EXPECTED_S1_DIGEST, s7.EXPECTED_S5_DIGEST):
        raise ValueError("T13S7R1 forensic raw digest mismatch")
    if not (
        s7._audit_certified(common._strict_json(args.source_s1_audit), s1_digest)
        and s7._audit_certified(common._strict_json(args.source_s5_audit), s5_digest)
    ):
        raise ValueError("T13S7R1 forensic source audit mismatch")
    s1_contexts, _, _ = s7.build_contexts(
        "s1",
        s1_raw,
        s7._payload_by_experiment("s1", args.s1_run),
        campaign_specific_effects=True,
    )
    s5_contexts, _, _ = s7.build_contexts(
        "s5",
        s5_raw,
        s7._payload_by_experiment("s5", args.s5_run),
        campaign_specific_effects=True,
    )
    contexts = s1_contexts + s5_contexts
    contexts.sort(key=lambda row: (row["stratum"], row["feature_digest"]))
    for index, context in enumerate(contexts):
        context["context_id"] = f"context_{index:02d}"
    cfg = common._strict_json(args.s5_config)["lattice_probe"]
    models = {
        (context["context_id"], window): s7.fit_local_model(context, window, cfg)
        for context in contexts
        for window in s7.WINDOWS
    }
    return contexts, models


def _distribution(values: Sequence[float]) -> dict[str, Any]:
    ordered = sorted(float(value) for value in values)
    return {
        "count": len(ordered),
        "minimum": min(ordered) if ordered else None,
        "median": statistics.median(ordered) if ordered else None,
        "maximum": max(ordered) if ordered else None,
        "frozen_support_pass_count": sum(
            value <= FROZEN_SUPPORT_THRESHOLD for value in ordered
        ),
    }


def build_forensic(args: argparse.Namespace) -> dict[str, Any]:
    authenticate_r1(args.source_r1_audit)
    contexts, models = _contexts_and_models(args)
    comparisons: list[dict[str, Any]] = []
    row_minima: dict[str, dict[str, list[float]]] = {}
    row_index = 0
    for stratum in ("easy", "hard"):
        stratum_contexts = [row for row in contexts if row["stratum"] == stratum]
        for held in stratum_contexts:
            training = [row for row in stratum_contexts if row is not held]
            for window in s7.WINDOWS:
                selected_ids = {
                    row["context_id"]
                    for _, row in s7.nearest_contexts(held, training, window=window)
                }
                for sample in held["samples"][window]:
                    for sign in s7.SIGNS:
                        model_input = sample["signed"][sign]["input"]
                        row_id = f"row_{row_index:03d}"
                        row_index += 1
                        buckets: dict[str, list[float]] = defaultdict(list)
                        for source in training:
                            residual, supported = s7.input_support(
                                models[(source["context_id"], window)], model_input
                            )
                            selected = source["context_id"] in selected_ids
                            relation = (
                                "same_campaign"
                                if source["campaign"] == held["campaign"]
                                else "cross_campaign"
                            )
                            comparisons.append(
                                {
                                    "row_id": row_id,
                                    "held_context_id": held["context_id"],
                                    "held_campaign": held["campaign"],
                                    "source_context_id": source["context_id"],
                                    "source_campaign": source["campaign"],
                                    "stratum": stratum,
                                    "window": window,
                                    "direction": sample["direction"],
                                    "sign": sign,
                                    "selected_by_frozen_feature_rule": selected,
                                    "campaign_relation": relation,
                                    "input_projection_residual": residual,
                                    "frozen_support_pass": supported,
                                }
                            )
                            buckets["all_training"].append(residual)
                            buckets[relation].append(residual)
                            if selected:
                                buckets["selected"].append(residual)
                        row_minima[row_id] = {
                            name: [min(values)] for name, values in buckets.items()
                        }

    group_values: dict[tuple[str, str, bool], list[float]] = defaultdict(list)
    for row in comparisons:
        group_values[
            (
                row["held_campaign"],
                row["source_campaign"],
                row["selected_by_frozen_feature_rule"],
            )
        ].append(row["input_projection_residual"])
    grouped = [
        {
            "held_campaign": key[0],
            "source_campaign": key[1],
            "selected_by_frozen_feature_rule": key[2],
            **_distribution(values),
        }
        for key, values in sorted(group_values.items())
    ]
    row_support = {}
    for bucket in ("all_training", "selected", "same_campaign", "cross_campaign"):
        minima = [
            values[bucket][0]
            for values in row_minima.values()
            if bucket in values
        ]
        row_support[bucket] = {
            "heldout_row_count_with_candidate": len(minima),
            "heldout_row_count_with_any_frozen_support": sum(
                value <= FROZEN_SUPPORT_THRESHOLD for value in minima
            ),
            "minimum_residual_distribution": _distribution(minima),
        }

    return {
        "schema_version": 1,
        "stage": STAGE,
        "source_r1_audit": str(args.source_r1_audit),
        "source_r1_audit_sha256": SOURCE_R1_SHA256,
        "source_r1_route_unchanged": SOURCE_R1_ROUTE,
        "post_result_diagnostic_only": True,
        "frozen_support_threshold_unchanged": FROZEN_SUPPORT_THRESHOLD,
        "real_tsc_executed": False,
        "controller_or_plant_step_executed": False,
        "formal_timing_unchanged": True,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "summary": {
            "context_count": len(contexts),
            "heldout_row_count": len(row_minima),
            "training_comparison_count": len(comparisons),
            "training_comparison_support_pass_count": sum(
                row["frozen_support_pass"] for row in comparisons
            ),
            "selected_comparison_count": sum(
                row["selected_by_frozen_feature_rule"] for row in comparisons
            ),
            "selected_comparison_support_pass_count": sum(
                row["selected_by_frozen_feature_rule"] and row["frozen_support_pass"]
                for row in comparisons
            ),
        },
        "row_support": row_support,
        "grouped_projection_residuals": grouped,
        "comparisons": comparisons,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--s1-run", required=True, type=Path)
    parser.add_argument("--source-s1-audit", required=True, type=Path)
    parser.add_argument("--s5-run", required=True, type=Path)
    parser.add_argument("--source-s5-audit", required=True, type=Path)
    parser.add_argument("--s5-config", required=True, type=Path)
    parser.add_argument("--source-r1-audit", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = build_forensic(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "sha256": common._sha256(args.output),
                "summary": output["summary"],
                "row_support": output["row_support"],
            },
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
