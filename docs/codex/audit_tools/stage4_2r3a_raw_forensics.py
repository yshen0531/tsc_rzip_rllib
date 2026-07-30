#!/usr/bin/env python3
"""Independent Stage4.2R3a raw state-generation forensics.

Run this on the server so the large raw/snapshot tree never needs to be
downloaded.  The output is compact and contains only recomputed metrics.
"""

from __future__ import annotations

import argparse
import copy
import itertools
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3a_delayed_counterpulse_hidden_history_initial_state as r3,
)


def _range(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, Any]:
    values = [float(row[key]) for row in rows if row.get(key) is not None]
    return {
        "minimum": min(values) if values else None,
        "maximum": max(values) if values else None,
    }


def _public_pair(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in row.items()
        if key not in {"plus_first_state", "minus_first_state"}
    }


def _group_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "pair_count": len(rows),
        "visible_match_count": sum(
            bool(row.get("visible_match_pass")) for row in rows
        ),
        "absolute_hidden_gate_count": sum(
            float(row.get("wire_max_abs_difference_A", -np.inf)) >= 1.0
            for row in rows
        ),
        "relative_hidden_gate_count": sum(
            float(row.get("wire_relative_rms_difference", -np.inf)) >= 0.05
            for row in rows
        ),
        "full_hidden_gate_count": sum(
            bool(row.get("hidden_separation_pass")) for row in rows
        ),
        "wire_max_abs_difference_A": _range(
            rows, "wire_max_abs_difference_A"
        ),
        "wire_relative_rms_difference": _range(
            rows, "wire_relative_rms_difference"
        ),
        "visible_max_normalized_ratio": _range(
            rows, "visible_max_normalized_ratio"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--source-stage4-2r2-run", required=True, type=Path)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--server-audit", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    run_dir = args.run_dir.expanduser().resolve()
    ctx = r3.load_stage42r3a_config(
        args.config,
        source_stage42r2_run=args.source_stage4_2r2_run,
        run_dir_override=run_dir,
    )
    raw_paths = sorted(
        (ctx.paths.state_generation / "raw").glob("*.json.gz")
    )
    raw_results = [r3.read_json_gz(path) for path in raw_paths]
    state_rows = [r3._state_row(result) for result in raw_results]
    by_pair: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in state_rows:
        by_pair[str(row["pair_id"])][str(row["history_order"])] = row
    pair_rows: list[dict[str, Any]] = []
    frozen = r3._frozen_initial_state(ctx)
    for pair_id in sorted(by_pair):
        members = by_pair[pair_id]
        if set(members) != {"plus_first", "minus_first"}:
            raise RuntimeError(f"incomplete raw pair: {pair_id}")
        pair = r3._pair_metrics(
            members["plus_first"],
            members["minus_first"],
            ctx.cfg["pair_gate"],
        )
        pair.update(
            r3._different_initial_metrics(
                pair, frozen, ctx.cfg["different_initial_state_gate"]
            )
        )
        pair_rows.append(pair)

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in pair_rows:
        key = (
            f"p{int(row['common_prefix_steps'])}_"
            f"q{int(row['nullspace_direction_index'])}_"
            f"gap{int(row['gap_steps'])}"
        )
        grouped[key].append(row)

    visible_gate_keys = {
        "R_abs_difference_m": "R_abs_difference_m_max",
        "Z_abs_difference_m": "Z_abs_difference_m_max",
        "Ip_abs_difference_A": "Ip_abs_difference_A_max",
        "vR_abs_difference_m_per_s": "vR_abs_difference_m_per_s_max",
        "vZ_abs_difference_m_per_s": "vZ_abs_difference_m_per_s_max",
        "coil_max_abs_difference_A": "coil_max_abs_difference_A_max",
        "coil_rms_difference_A": "coil_rms_difference_A_max",
        "action_max_abs_difference": "action_max_abs_difference_max",
    }
    visible_failures = {
        metric: sum(
            float(row[metric]) > float(ctx.cfg["pair_gate"][gate_key])
            for row in pair_rows
        )
        for metric, gate_key in visible_gate_keys.items()
    }

    cross_rows: list[dict[str, Any]] = []
    for left, right in itertools.combinations(state_rows, 2):
        if (
            not bool(left.get("success"))
            or not bool(right.get("success"))
            or int(left["snapshot_time_ms"]) != int(right["snapshot_time_ms"])
            or int(left["horizon_steps"]) != int(right["horizon_steps"])
        ):
            continue
        pair = r3._pair_metrics(left, right, ctx.cfg["pair_gate"])
        pair["left_experiment_id"] = str(left["experiment_id"])
        pair["right_experiment_id"] = str(right["experiment_id"])
        pair["left_pair_id"] = str(left["pair_id"])
        pair["right_pair_id"] = str(right["pair_id"])
        pair["left_history_order"] = str(left["history_order"])
        pair["right_history_order"] = str(right["history_order"])
        cross_rows.append(pair)

    visible_cross = [
        row for row in cross_rows if bool(row["visible_match_pass"])
    ]
    full_hidden_cross = [
        row for row in visible_cross if bool(row["hidden_separation_pass"])
    ]
    top_original = sorted(
        pair_rows,
        key=lambda row: (
            -float(row["wire_relative_rms_difference"]),
            -float(row["wire_max_abs_difference_A"]),
        ),
    )[:20]
    top_cross = sorted(
        visible_cross,
        key=lambda row: (
            -float(row["wire_relative_rms_difference"]),
            -float(row["wire_max_abs_difference_A"]),
        ),
    )[:30]

    prefix_separation = r3._prefix_group_separation(
        pair_rows,
        ctx.cfg["different_initial_state_gate"][
            "required_common_prefix_lengths"
        ],
        ctx.cfg["different_initial_state_gate"],
    )
    server_audit = json.loads(
        args.server_audit.read_text(encoding="utf-8")
    )
    output = {
        "schema_version": 1,
        "stage": r3.STAGE,
        "purpose": "independent_raw_state_generation_forensics",
        "r3a_verdict_changed": False,
        "run_dir": str(run_dir),
        "raw_file_count": len(raw_paths),
        "raw_success_count": sum(
            bool(result.get("success")) for result in raw_results
        ),
        "snapshot_valid_count": int(
            server_audit["snapshot_valid_count"]
        ),
        "run_inventory_digest": server_audit["run_inventory"]["digest"],
        "run_inventory_file_count": int(
            server_audit["run_inventory"]["n_files"]
        ),
        "run_inventory_total_bytes": int(
            server_audit["run_inventory"]["total_bytes"]
        ),
        "original_pair_summary": _group_summary(pair_rows),
        "visible_gate_failure_counts": visible_failures,
        "different_initial_state_pass_count": sum(
            bool(row["different_initial_state_pass"]) for row in pair_rows
        ),
        "visible_matched_and_different_initial_count": sum(
            bool(row["visible_match_pass"])
            and bool(row["different_initial_state_pass"])
            for row in pair_rows
        ),
        "all_pair_prefix_group_separation": prefix_separation,
        "grouped_original_pair_summary": {
            key: _group_summary(rows) for key, rows in sorted(grouped.items())
        },
        "same_clock_cross_pair_summary": {
            "pair_count": len(cross_rows),
            "visible_match_count": len(visible_cross),
            "visible_matched_absolute_hidden_gate_count": sum(
                float(row["wire_max_abs_difference_A"]) >= 1.0
                for row in visible_cross
            ),
            "visible_matched_relative_hidden_gate_count": sum(
                float(row["wire_relative_rms_difference"]) >= 0.05
                for row in visible_cross
            ),
            "visible_matched_full_hidden_gate_count": len(
                full_hidden_cross
            ),
            "visible_matched_wire_max_abs_difference_A": _range(
                visible_cross, "wire_max_abs_difference_A"
            ),
            "visible_matched_wire_relative_rms_difference": _range(
                visible_cross, "wire_relative_rms_difference"
            ),
        },
        "top_original_pairs": [
            _public_pair(row) for row in top_original
        ],
        "top_visible_matched_cross_pairs": [
            _public_pair(row) for row in top_cross
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    r3.atomic_write_json(args.output, copy.deepcopy(output))
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
