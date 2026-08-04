"""Structurally separate raw recomputation for D1R14R3."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r2_independent_forensics as frozen_r2,
)


STAGE = "Stage4.2R3c3T13S24D1R14R3"
R2_ROUTE = "MIXED_BASIS_SENTINEL_RESPONSE_GEOMETRY_FAIL_REDESIGN_REQUIRED"
PRIMARY_PASS_ROUTE = (
    "SIGN_SPLIT_RESPONSE_FEASIBILITY_PASS_TIME_SHIFT_SENTINEL_DESIGN_REQUIRED"
)


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for name, item in pairs:
        if name in value:
            raise ValueError(f"duplicate JSON key: {name}")
        value[name] = item
    return value


def _bad_constant(value: str) -> None:
    raise ValueError(f"nonstandard JSON constant: {value}")


def _loads(text: str) -> Any:
    return json.loads(
        text,
        object_pairs_hook=_pairs_no_duplicates,
        parse_constant=_bad_constant,
    )


def _json(path: Path) -> Any:
    return _loads(path.read_text(encoding="utf-8", errors="strict"))


def _raw(path: Path) -> dict[str, Any]:
    with gzip.open(path, mode="rt", encoding="utf-8", errors="strict") as stream:
        result = _loads(stream.read())
    if not isinstance(result, dict):
        raise ValueError(f"raw root must be an object: {path}")
    return result


def _hash(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            hasher.update(block)
    return hasher.hexdigest()


def _outputs(trajectory: Sequence[Mapping[str, Any]]) -> np.ndarray:
    count = len(trajectory)
    positions = np.asarray(
        [[float(row["R"]), float(row["Z"])] for row in trajectory], dtype=float
    )
    velocities = np.empty((count, 2), dtype=float)
    velocities[0] = (positions[1] - positions[0]) * 100.0
    velocities[1:] = (positions[1:] - positions[:-1]) * 100.0
    currents = np.asarray([float(row["Ip"]) for row in trajectory], dtype=float)
    combined = np.column_stack((positions, velocities, currents))
    combined /= np.asarray([0.03, 0.03, 0.1, 0.1, 10000.0], dtype=float)
    combined -= combined[10]
    return combined


def _read_campaign(
    run: Path,
) -> tuple[list[Mapping[str, Any]], dict[tuple[str, str, int, int], Mapping[str, Any]], Path]:
    stage = run.resolve() / frozen_r2.RUN_NAME
    specs = _json(stage / "specs" / "sentinel_specs.json")
    if not isinstance(specs, list) or len(specs) != 72:
        raise ValueError("D1R14R2 spec count is not 72")
    lookup: dict[tuple[str, str, int, int], Mapping[str, Any]] = {}
    for spec in specs:
        experiment_id = str(spec["experiment_id"])
        key = (
            str(spec["source_d1r13_experiment_id"]),
            str(spec["d1r14r2_role"]),
            int(spec["d1r14r2_direction_index"]),
            int(spec["d1r14r2_sign"]),
        )
        if key in lookup:
            raise ValueError(f"duplicate R2 semantic member: {key}")
        lookup[key] = _raw(stage / "raw" / f"{experiment_id}.json.gz")
    return specs, lookup, stage


def _recompute_branches(
    cfg: Mapping[str, Any],
    specs: Sequence[Mapping[str, Any]],
    lookup: Mapping[tuple[str, str, int, int], Mapping[str, Any]],
) -> dict[str, Any]:
    rule = cfg["sign_split_contract"]
    contexts = sorted(
        {str(spec["source_d1r13_experiment_id"]) for spec in specs}
    )
    context_metadata: dict[str, Mapping[str, Any]] = {}
    for spec in specs:
        context_metadata.setdefault(str(spec["source_d1r13_experiment_id"]), spec)
    branches: list[dict[str, Any]] = []
    for context in contexts:
        baseline = _outputs(lookup[(context, "baseline", -1, 0)]["trajectory"])[11:]
        for sign in (1, -1):
            unit_columns = []
            direction_rows = []
            for direction in range(4):
                sample = _outputs(
                    lookup[(context, "signed_probe", direction, sign)]["trajectory"]
                )[11:]
                delta = (sample - baseline) * float(sign)
                vector = np.ravel(delta, order="C")
                peak = float(np.abs(delta).max())
                length = float(np.sqrt(np.dot(vector, vector)))
                is_finite = bool(np.isfinite(delta).all())
                unit_columns.append(
                    vector / length
                    if is_finite and length > 0.0
                    else np.full(vector.size, np.nan)
                )
                direction_rows.append(
                    {
                        "direction_index": direction,
                        "direction_name": frozen_r2.DIRECTIONS[direction],
                        "peak_normalized_outputs5": peak,
                        "l2_norm": length,
                        "finite": is_finite,
                        "signal_pass": bool(
                            is_finite
                            and peak
                            >= float(rule["minimum_direction_peak_normalized_outputs5"])
                            - 1e-15
                        ),
                    }
                )
            response_matrix = np.stack(unit_columns, axis=1)
            finite_matrix = bool(np.isfinite(response_matrix).all())
            singular = (
                np.linalg.svd(response_matrix, full_matrices=False, compute_uv=False)
                if finite_matrix
                else np.full(4, np.nan)
            )
            cutoff = (
                singular[0] * float(rule["rank_relative_tolerance"])
                if finite_matrix
                else math.inf
            )
            rank = int(np.count_nonzero(singular > cutoff))
            condition = (
                float(singular[0] / singular[3])
                if rank == 4 and singular[3] > 0.0
                else None
            )
            passed = bool(
                all(row["signal_pass"] for row in direction_rows)
                and rank == int(rule["required_rank"])
                and condition is not None
                and condition <= float(rule["maximum_condition_number"]) + 1e-12
            )
            meta = context_metadata[context]
            branches.append(
                {
                    "source_d1r13_experiment_id": context,
                    "pair_id": meta["pair_id"],
                    "history_member": meta["history_member"],
                    "sign": sign,
                    "directions": direction_rows,
                    "singular_values": [float(item) for item in singular],
                    "rank": rank,
                    "condition_number": condition,
                    "passed": passed,
                }
            )
    direction_rows = [row for branch in branches for row in branch["directions"]]
    summary = {
        "context_count": len(contexts),
        "branch_count": len(branches),
        "branch_direction_count": len(direction_rows),
        "signal_pass_count": sum(bool(row["signal_pass"]) for row in direction_rows),
        "rank_pass_count": sum(
            int(branch["rank"]) == int(rule["required_rank"]) for branch in branches
        ),
        "condition_pass_count": sum(
            branch["condition_number"] is not None
            and branch["condition_number"]
            <= float(rule["maximum_condition_number"]) + 1e-12
            for branch in branches
        ),
        "minimum_direction_peak_normalized_outputs5": min(
            row["peak_normalized_outputs5"] for row in direction_rows
        ),
        "maximum_condition_number": max(
            branch["condition_number"]
            for branch in branches
            if branch["condition_number"] is not None
        ),
        "rows": branches,
    }
    summary["passed"] = bool(
        summary["context_count"] == 8
        and summary["branch_count"] == 16
        and summary["branch_direction_count"] == 64
        and summary["signal_pass_count"] == 64
        and summary["rank_pass_count"] == 16
        and summary["condition_pass_count"] == 16
    )
    return summary


def _recompute_issue_symmetry(
    lookup: Mapping[tuple[str, str, int, int], Mapping[str, Any]]
) -> dict[str, Any]:
    contexts = sorted({key[0] for key in lookup})
    rows = []
    for context in contexts:
        for direction in range(4):
            plus = lookup[(context, "signed_probe", direction, 1)]["controller_trace"][10][
                "r3c3t13s24d1r14r2_event_detail"
            ]
            minus = lookup[(context, "signed_probe", direction, -1)]["controller_trace"][10][
                "r3c3t13s24d1r14r2_event_detail"
            ]
            pc = np.asarray(plus["requested_coordinate"], dtype=np.float64)
            mc = np.asarray(minus["requested_coordinate"], dtype=np.float64)
            pf = np.asarray(plus["actual_signed_delta_field_kAt_tsc"], dtype=np.float64)
            mf = np.asarray(minus["actual_signed_delta_field_kAt_tsc"], dtype=np.float64)
            coordinate = bool((pc == np.negative(mc)).all())
            field = bool((pf == np.negative(mf)).all())
            rows.append(
                {
                    "source_d1r13_experiment_id": context,
                    "direction_index": direction,
                    "coordinate_exact_sign_opposite": coordinate,
                    "physical_field_exact_sign_opposite": field,
                    "passed": coordinate and field,
                }
            )
    return {
        "pair_count": len(rows),
        "coordinate_exact_count": sum(row["coordinate_exact_sign_opposite"] for row in rows),
        "physical_field_exact_count": sum(
            row["physical_field_exact_sign_opposite"] for row in rows
        ),
        "passed": len(rows) == 32 and all(row["passed"] for row in rows),
        "rows": rows,
    }


def _reproduction(cfg: Mapping[str, Any], geometry: Mapping[str, Any]) -> dict[str, Any]:
    frozen = cfg["r2_reproduction_contract"]
    tolerance = float(frozen["numeric_absolute_tolerance"])
    numeric_fields = (
        "minimum_odd_peak_normalized_outputs5",
        "maximum_even_to_odd_peak_ratio",
        "maximum_condition_number",
    )
    count_fields = (
        "signal_pass_count",
        "symmetry_pass_count",
        "rank_pass_count",
        "condition_pass_count",
    )
    aggregates = all(int(geometry[name]) == int(frozen[name]) for name in count_fields)
    aggregates = aggregates and all(
        abs(float(geometry[name]) - float(frozen[name])) <= tolerance
        for name in numeric_fields
    )
    failures = [row for row in geometry["pair_rows"] if not bool(row["symmetry_pass"])]
    return {
        "aggregate_match": aggregates,
        "original_geometry_passed": bool(geometry["passed"]),
        "failed_pair_count": len(failures),
        "failed_pair_rows": failures,
        "passed": bool(
            aggregates
            and not geometry["passed"]
            and len(failures) == int(frozen["failed_pair_count"])
        ),
    }


def _close(left: Any, right: Any, tolerance: float = 1e-12) -> bool:
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        return set(left) == set(right) and all(
            _close(left[key], right[key], tolerance) for key in left
        )
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            _close(a, b, tolerance) for a, b in zip(left, right)
        )
    if isinstance(left, bool) or isinstance(right, bool):
        return left is right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return math.isfinite(float(left)) and math.isfinite(float(right)) and abs(
            float(left) - float(right)
        ) <= tolerance
    return left == right


def audit(args: argparse.Namespace) -> dict[str, Any]:
    project = args.project.resolve()
    cfg = _json(args.config.resolve())
    source = cfg["source_r2_contract"]
    if cfg.get("stage") != STAGE or cfg.get("schema_version") != 1:
        raise ValueError("D1R14R3 config identity mismatch")
    if _hash(args.design_document.resolve()) != cfg["design_document_sha256"]:
        raise ValueError("D1R14R3 design hash mismatch")
    for path_name, hash_name in (
        ("config", "config_sha256"),
        ("implementation", "implementation_sha256"),
        ("independent_implementation", "independent_implementation_sha256"),
    ):
        if _hash(project / source[path_name]) != source[hash_name]:
            raise ValueError(f"R2 source hash mismatch: {path_name}")
    r2 = frozen_r2.audit(
        args.source_r2_run,
        args.source_d1r13_run,
        args.source_d1r11_run,
        args.source_r1a_output,
        project,
        args.source_log,
    )
    specs, lookup, stage = _read_campaign(args.source_r2_run)
    manifest = _json(stage / "stage_manifest.json")
    frozen_independent = _json(args.source_r2_independent_result.resolve())
    _json(args.source_posthoc.resolve())
    source_hashes = {
        "final_result": _hash(stage / "analysis" / "final_result.json"),
        "stage_state": _hash(stage / "stage_state.json"),
        "independent_result": _hash(args.source_r2_independent_result.resolve()),
        "posthoc_diagnostic": _hash(args.source_posthoc.resolve()),
    }
    expected_hashes = {
        "final_result": source["final_result_sha256"],
        "stage_state": source["stage_state_sha256"],
        "independent_result": source["independent_result_sha256"],
        "posthoc_diagnostic": source["posthoc_diagnostic_sha256"],
    }
    source_pass = bool(
        source_hashes == expected_hashes
        and r2.get("audit_completed") is True
        and r2.get("passed") is True
        and r2.get("independent_route") == R2_ROUTE
        and r2.get("official_route_reproduced") is True
        and int(r2.get("safety_pass_count", -1)) == 72
        and int(r2.get("issue_exact_count", -1)) == 64
        and int(r2.get("cancel_exact_count", -1)) == 64
        and int(r2.get("snapshot_pass_count", -1)) == 8
        and (r2.get("current_inventory") or {}).get("count") == int(source["raw_count"])
        and (r2.get("current_inventory") or {}).get("bytes")
        == int(source["raw_total_bytes"])
        and (r2.get("current_inventory") or {}).get("digest")
        == source["raw_inventory_digest"]
        and (manifest.get("package_fingerprint") or {}).get("digest")
        == source["package_fingerprint_digest"]
        and manifest.get("spec_digest") == source["spec_digest"]
        and manifest.get("requested_matrix_digest") == source["requested_matrix_digest"]
        and frozen_independent.get("audit_completed") is True
        and frozen_independent.get("independent_route") == R2_ROUTE
    )
    reproduction = _reproduction(cfg, r2["response_geometry"])
    issue = _recompute_issue_symmetry(lookup)
    branches = _recompute_branches(cfg, specs, lookup)
    primary = _json(args.primary.resolve())
    comparison = {
        "source_hashes": primary.get("source_static_hashes") == source_hashes,
        "r2_reproduction": _close(
            primary.get("r2_shared_model_reproduction"), reproduction
        ),
        "issue_symmetry": _close(
            primary.get("issue_coordinate_and_field_symmetry"), issue
        ),
        "sign_split_geometry": _close(primary.get("sign_split_geometry"), branches),
    }
    routes = cfg["routes"]
    if not source_pass:
        route = routes["source_fail"]
    elif not reproduction["passed"]:
        route = routes["r2_reproduction_fail"]
    elif not issue["passed"] or not branches["passed"]:
        route = routes["branch_fail"]
    else:
        route = routes["pass"]
    comparison["route"] = primary.get("route") == route
    comparison["passed"] = primary.get("passed") == (route == PRIMARY_PASS_ROUTE)
    agreement = all(comparison.values())
    return {
        "schema_version": 1,
        "stage": STAGE,
        "audit_revision": "independent_sign_split_response_raw_forensics_v1",
        "audit_completed": True,
        "passed": bool(source_pass and reproduction["passed"] and issue["passed"] and branches["passed"] and agreement),
        "route": route,
        "source_authenticated": source_pass,
        "source_r2_run": str(args.source_r2_run.resolve()),
        "source_static_hashes": source_hashes,
        "r2_shared_model_reproduction": reproduction,
        "issue_coordinate_and_field_symmetry": issue,
        "sign_split_geometry": branches,
        "primary_comparison": comparison,
        "primary_exact_agreement": agreement,
        "execution": {
            "new_raw_count": 0,
            "plant_steps_executed": 0,
            "controller_executed": False,
            "ray_executed": False,
            "gotsc_executed": False,
            "tsc_executed": False,
        },
        "classification": {
            "runtime_or_environment_error": False,
            "raw_or_snapshot_corruption": not source_pass,
            "summary_statistics_or_reporting_error": not agreement,
            "r2_shared_odd_model_design_failure_reproduced": reproduction["passed"],
            "sign_split_branch_design_failure": bool(
                source_pass and reproduction["passed"] and not branches["passed"]
            ),
            "real_control_or_mpc_conclusion": False,
        },
        "scientific_boundary": dict(cfg["scientific_scope"]),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--design-document", type=Path, required=True)
    parser.add_argument("--source-r2-run", type=Path, required=True)
    parser.add_argument("--source-d1r13-run", type=Path, required=True)
    parser.add_argument("--source-d1r11-run", type=Path, required=True)
    parser.add_argument("--source-r1a-output", type=Path, required=True)
    parser.add_argument("--source-r2-independent-result", type=Path, required=True)
    parser.add_argument("--source-posthoc", type=Path, required=True)
    parser.add_argument("--source-log", type=Path, action="append", required=True)
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    result = audit(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "sha256": _hash(args.output),
                "passed": result["passed"],
                "route": result["route"],
                "primary_exact_agreement": result["primary_exact_agreement"],
                "zero_new_tsc": True,
            },
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
