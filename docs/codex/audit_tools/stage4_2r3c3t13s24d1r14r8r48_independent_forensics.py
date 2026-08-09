#!/usr/bin/env python3
"""Structurally independent raw/prefix/bridge audit for R8R48."""

from __future__ import annotations

import argparse
import json
import math
import traceback
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r31_independent_forensics as ind31,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r31_aligned_explicit_four_coordinate_feedback_sentinel
    as r8r31,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r48_q0_to_transport_causal_bridge_support_audit
    as r8r48,
)


STAGE = r8r48.STAGE
IDENTITY = r8r48.IDENTITY
ZERO = np.zeros(4, dtype=np.float64)

_read = r8r48._read
_write = r8r48._write
_sha = r8r48._sha
_digest = r8r48._digest
_jsonable = r8r48._jsonable


def _key(row: Mapping[str, Any]) -> tuple[str, str]:
    return str(row["pair_id"]), str(row["history_member"])


def _prefix(row: Mapping[str, Any]) -> dict[str, Any]:
    states = np.asarray(row["states"], dtype=np.float64)
    raw = list(row["trajectory"])
    if states.shape[0] < 13 or len(raw) < 13:
        raise ValueError("independent R8R48 prefix incomplete")
    return _jsonable({"states": states[:13], "trajectory": raw[:13]})


def _candidate_rows(cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = [
        {"index": index, "id": str(item["id"]), "q": np.asarray(item["q"], dtype=np.float64)}
        for index, item in enumerate(cfg["candidate_contract"]["candidates"])
    ]
    if len(rows) != 17 or rows[0]["id"] != "q0" or np.count_nonzero(rows[0]["q"]):
        raise ValueError("independent R8R48 candidate library changed")
    return rows


def _enumerate(
    raw_bank: Sequence[Mapping[str, Any]], candidates: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    contexts = sorted({_key(row) for row in raw_bank})
    nonzero = [row for row in candidates if int(row["index"]) > 0]
    references = {}
    for context in contexts:
        found = [
            row for row in raw_bank
            if _key(row) == context and str(row["schedule_id"]) == "q0"
        ]
        if len(found) != 1:
            raise ValueError("independent R8R48 q0 cardinality changed")
        first = found[0]["intervals"][0]
        if (
            int(first["decision"]) != 10
            or not np.array_equal(np.asarray(first["previous_q"], dtype=np.float64), ZERO)
            or not np.array_equal(np.asarray(first["q"], dtype=np.float64), ZERO)
        ):
            raise ValueError("independent R8R48 q0 metadata changed")
        references[context] = found[0]

    cells = []
    context_rows = []
    later_cell_count = 0
    for context in contexts:
        reference = references[context]
        reference_prefix = _prefix(reference)
        reference_digest = _digest(reference_prefix)
        rows = [row for row in raw_bank if _key(row) == context]
        exact_prefix_count = sum(_prefix(row) == reference_prefix for row in rows)
        covered = 0
        for candidate in nonzero:
            q = np.asarray(candidate["q"], dtype=np.float64)
            metadata_ids, authentic_ids, later_ids = set(), set(), set()
            for row in rows:
                interval0, interval1 = row["intervals"][:2]
                q0 = (
                    np.array_equal(np.asarray(interval0["previous_q"], dtype=np.float64), ZERO)
                    and np.array_equal(np.asarray(interval0["q"], dtype=np.float64), ZERO)
                )
                if (
                    q0
                    and int(interval1["decision"]) == 12
                    and np.array_equal(np.asarray(interval1["previous_q"], dtype=np.float64), ZERO)
                    and np.array_equal(np.asarray(interval1["q"], dtype=np.float64), q)
                    and len(interval1["targets"]) > 0
                ):
                    metadata_ids.add(str(row["trajectory_id"]))
                    if _prefix(row) == reference_prefix:
                        authentic_ids.add(str(row["trajectory_id"]))
                if q0 and any(
                    np.array_equal(np.asarray(interval["q"], dtype=np.float64), q)
                    for interval in row["intervals"][2:]
                ):
                    later_ids.add(str(row["trajectory_id"]))
            present = bool(authentic_ids)
            covered += int(present)
            later_cell_count += int(bool(later_ids))
            cells.append({
                "pair_id": context[0],
                "history_member": context[1],
                "candidate_index": int(candidate["index"]),
                "candidate_id": str(candidate["id"]),
                "candidate_q": q.tolist(),
                "reference_q0_trajectory_id": str(reference["trajectory_id"]),
                "reference_prefix_digest": reference_digest,
                "metadata_match_count": len(metadata_ids),
                "metadata_match_trajectory_ids": sorted(metadata_ids),
                "authentic_bridge_count": len(authentic_ids),
                "authentic_bridge_trajectory_ids": sorted(authentic_ids),
                "later_interval_match_count": len(later_ids),
                "later_interval_match_trajectory_ids": sorted(later_ids),
                "authentic_bridge_present": present,
            })
        context_rows.append({
            "pair_id": context[0],
            "history_member": context[1],
            "q0_trajectory_id": str(reference["trajectory_id"]),
            "q0_prefix_digest": reference_digest,
            "exact_prefix_trajectory_count": exact_prefix_count,
            "authentic_candidate_coverage_count": covered,
            "complete_candidate_coverage": covered == len(nonzero),
        })
    present_count = sum(row["authentic_bridge_present"] for row in cells)
    return {
        "q0_reference_context_count": len(references),
        "nonzero_candidate_count": len(nonzero),
        "required_bridge_cell_count": len(cells),
        "authentic_bridge_cell_count": present_count,
        "missing_bridge_cell_count": len(cells) - present_count,
        "metadata_only_bridge_cell_count": sum(
            row["metadata_match_count"] and not row["authentic_bridge_present"] for row in cells
        ),
        "later_interval_candidate_cell_count": later_cell_count,
        "complete_physical_bridge_support": present_count == len(cells),
        "q0_prefix_digest": _digest([
            {"pair_id": row["pair_id"], "history_member": row["history_member"], "digest": row["q0_prefix_digest"]}
            for row in context_rows
        ]),
        "bridge_matrix_digest": _digest([
            {
                key: value
                for key, value in row.items()
                if key not in {
                    "metadata_match_trajectory_ids",
                    "later_interval_match_trajectory_ids",
                }
            }
            for row in cells
        ]),
        "contexts": context_rows,
        "cells": cells,
    }


def _hull_supported(
    hull: Mapping[str, Any], previous: np.ndarray, current: np.ndarray, cfg: Mapping[str, Any]
) -> bool:
    contract = cfg["support_contract"]
    value = np.r_[previous, current] / float(contract["coordinate_scale"])
    centered = value - np.asarray(hull["origin"], dtype=np.float64)
    basis = np.asarray(hull["basis"], dtype=np.float64)
    projected = basis.T @ centered
    reconstructed = basis @ projected
    if float(np.linalg.norm(centered - reconstructed)) > float(contract["affine_residual_tolerance"]):
        return False
    equations = np.asarray(hull["equations"], dtype=np.float64)
    if equations.size == 0:
        return True
    return bool(np.all(equations[:, :-1] @ projected + equations[:, -1] <= float(contract["convex_hull_inequality_tolerance"])))


def _geometry(
    bank: Sequence[Mapping[str, Any]], candidates: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any], bridge: Mapping[str, Any]
) -> dict[str, Any]:
    support = ind31._planning_support(bank, cfg)
    hulls = ind31._transition_hulls(bank, cfg)
    interval = 1
    features = np.asarray(support["features"][interval], dtype=np.float64)
    threshold = float(support["thresholds"][interval])
    references = {_key(row): row for row in bank if str(row["schedule_id"]) == "q0"}
    candidates_by_index = {int(row["index"]): row for row in candidates}
    rows = []
    for cell in bridge["cells"]:
        context = str(cell["pair_id"]), str(cell["history_member"])
        feature = np.asarray(references[context]["intervals"][interval]["feature"], dtype=np.float64)
        distance = float(np.min(np.linalg.norm(features - feature, axis=1)))
        candidate = candidates_by_index[int(cell["candidate_index"])]
        rows.append({
            "pair_id": context[0],
            "history_member": context[1],
            "candidate_index": int(candidate["index"]),
            "candidate_id": str(candidate["id"]),
            "transition_hull_supported": _hull_supported(
                hulls[interval], ZERO, np.asarray(candidate["q"], dtype=np.float64), cfg
            ),
            "nearest_feature_distance": distance,
            "feature_support_threshold": threshold,
            "feature_supported": distance <= threshold + 1e-15,
            "authentic_bridge_present": bool(cell["authentic_bridge_present"]),
        })
    return {
        "interval": interval,
        "transition_hull_supported_cell_count": sum(row["transition_hull_supported"] for row in rows),
        "feature_supported_cell_count": sum(row["feature_supported"] for row in rows),
        "physical_bridge_cell_count": sum(row["authentic_bridge_present"] for row in rows),
        "maximum_nearest_feature_distance": max(row["nearest_feature_distance"] for row in rows),
        "feature_support_threshold": threshold,
        "geometric_support_substitutes_for_physical_bridge": False,
        "diagnostic_digest": _digest(rows),
        "cells": rows,
    }


def _bridge_view(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value[key]
        for key in (
            "q0_reference_context_count", "nonzero_candidate_count",
            "required_bridge_cell_count", "authentic_bridge_cell_count",
            "missing_bridge_cell_count", "metadata_only_bridge_cell_count",
            "later_interval_candidate_cell_count", "complete_physical_bridge_support",
            "q0_prefix_digest", "bridge_matrix_digest", "contexts", "cells",
        )
    }


def _geometry_difference(left: Mapping[str, Any], right: Mapping[str, Any]) -> float:
    a = {
        (str(row["pair_id"]), str(row["history_member"]), int(row["candidate_index"])): row
        for row in left["cells"]
    }
    b = {
        (str(row["pair_id"]), str(row["history_member"]), int(row["candidate_index"])): row
        for row in right["cells"]
    }
    if set(a) != set(b):
        return math.inf
    return max(
        abs(float(a[key]["nearest_feature_distance"]) - float(b[key]["nearest_feature_distance"]))
        for key in a
    )


def audit(args: argparse.Namespace) -> dict[str, Any]:
    ctx = r8r48.load_context(args)
    stage = ctx.paths.stage
    summary_path = stage / "analysis/primary_summary.json"
    detailed_path = stage / "analysis/primary_detailed.json"
    primary_summary = _read(summary_path)
    primary = _read(detailed_path)

    paths = r8r48._r8r46_paths(ctx.r8r46_stage)
    hashes = {name: _sha(path) for name, path in paths.items()}
    contract = ctx.cfg["source_r8r46"]
    source_ok = bool(
        all(hashes[name] == contract[f"{name}_sha256"] for name in hashes)
        and _read(paths["primary_summary"]).get("route") == contract["required_route"]
        and _read(paths["final_report"]).get("route") == contract["required_route"]
        and _read(paths["stage_state"]).get("finished") is True
    )
    if not source_ok:
        raise ValueError("independent R8R48 source authentication failed")

    independent_bank = ind31._build_bank(args, ctx.source_ctx.cfg)
    bank_evidence = ind31._bank_evidence(independent_bank)
    r8r48.verify_bank(bank_evidence, ctx.cfg)
    production_raw, _meta, production_evidence = r8r31.build_bank(ctx.source_ctx)
    if production_evidence != bank_evidence:
        raise ValueError("independent R8R48 raw/bank binding changed")
    independent_by_id = {str(row["trajectory_id"]): row for row in independent_bank}
    for raw in production_raw:
        other = independent_by_id.get(str(raw["trajectory_id"]))
        if other is None or any(
            not np.array_equal(np.asarray(a[field]), np.asarray(b[field]))
            for a, b in zip(raw["intervals"], other["intervals"])
            for field in ("feature", "q", "previous_q", "targets")
        ):
            raise ValueError("independent R8R48 interval reconstruction disagrees")

    candidates = _candidate_rows(ctx.source_ctx.cfg)
    bridge = _enumerate(production_raw, candidates)
    geometry = _geometry(independent_bank, candidates, ctx.source_ctx.cfg, bridge)
    route = ctx.cfg["routes"][
        "support_present" if bridge["complete_physical_bridge_support"] else "support_absent"
    ]
    difference = _geometry_difference(primary["geometric_diagnostics"], geometry)
    result = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "audit_kind": "q0_to_transport_causal_bridge_support_independent",
        "passed": True,
        "integrity_gate_passed": True,
        "scientific_gate_passed": bool(bridge["complete_physical_bridge_support"]),
        "route": route,
        "primary_source_agreement": hashes == primary["source_authentication"]["hashes"],
        "primary_bank_agreement": bank_evidence == primary["bank_evidence"],
        "primary_prefix_agreement": bridge["q0_prefix_digest"] == primary["bridge_audit"]["q0_prefix_digest"],
        "primary_bridge_matrix_agreement": _bridge_view(bridge) == _bridge_view(primary["bridge_audit"]),
        "primary_geometric_agreement": (
            geometry["diagnostic_digest"] == primary["geometric_diagnostics"]["diagnostic_digest"]
            and difference <= float(ctx.cfg["geometric_diagnostic_contract"]["primary_independent_distance_tolerance"])
        ),
        "primary_route_agreement": route == primary_summary["route"] == primary["route"],
        "primary_outcome_agreement": bool(bridge["complete_physical_bridge_support"]) == bool(primary["scientific_gate_passed"]),
        "maximum_geometric_distance_difference": difference,
        "q0_prefix_digest": bridge["q0_prefix_digest"],
        "bridge_matrix_digest": bridge["bridge_matrix_digest"],
        "geometric_diagnostic_digest": geometry["diagnostic_digest"],
        "authentic_bridge_cell_count": int(bridge["authentic_bridge_cell_count"]),
        "missing_bridge_cell_count": int(bridge["missing_bridge_cell_count"]),
        "transition_hull_supported_cell_count": int(geometry["transition_hull_supported_cell_count"]),
        "feature_supported_cell_count": int(geometry["feature_supported_cell_count"]),
        "primary_summary_sha256": _sha(summary_path),
        "primary_detailed_sha256": _sha(detailed_path),
        "real_tsc_executed": False,
        "plant_step_count": 0,
        "new_raw_count": 0,
        "model_fit_count": 0,
        "controller_execution_authorized": False,
        "gate_a_qualified": False,
        "expert_data_allowed": False,
    }
    agreements = [
        result[key] for key in r8r48.AGREEMENT_FIELDS
    ]
    result["passed"] = bool(all(agreements) and difference <= float(
        ctx.cfg["geometric_diagnostic_contract"]["primary_independent_distance_tolerance"]
    ))
    if not result["passed"]:
        raise ValueError("independent R8R48 comparison failed")
    _write(stage / "analysis/independent.json", result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in r8r48.ARGUMENT_NAMES:
        parser.add_argument(f"--{name}", dest=name.replace("-", "_"), type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    try:
        result = audit(args)
    except Exception as exc:
        try:
            ctx = r8r48.load_context(args)
            failure = {
                "schema_version": 1,
                "stage": STAGE,
                "identity": IDENTITY,
                "passed": False,
                "integrity_gate_passed": False,
                "scientific_gate_passed": False,
                "route": ctx.cfg["routes"]["execution_fail"],
                "failure_reason": repr(exc),
                "traceback": traceback.format_exc(),
                "real_tsc_executed": False,
                "plant_step_count": 0,
                "new_raw_count": 0,
            }
            _write(ctx.paths.analysis / "independent_failure.json", failure)
        except Exception:
            pass
        raise
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
