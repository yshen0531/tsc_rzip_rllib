"""Zero-TSC sign-split response feasibility audit for D1R14R3."""

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
    stage4_2r3c3t13s24d1r14r2_independent_forensics as r2_forensics,
)


STAGE = "Stage4.2R3c3T13S24D1R14R3"
IDENTITY = "sign_split_response_feasibility_raw_audit_v1"
R2_ROUTE = "MIXED_BASIS_SENTINEL_RESPONSE_GEOMETRY_FAIL_REDESIGN_REQUIRED"


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"nonstandard JSON constant: {value}")


def _strict_loads(text: str) -> Any:
    return json.loads(
        text,
        object_pairs_hook=_reject_duplicate_pairs,
        parse_constant=_reject_constant,
    )


def _strict_json(path: Path) -> Any:
    return _strict_loads(path.read_text(encoding="utf-8", errors="strict"))


def _strict_gzip(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8", errors="strict") as handle:
        result = _strict_loads(handle.read())
    if not isinstance(result, dict):
        raise ValueError(f"raw JSON root is not an object: {path}")
    return result


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _finite(value: Any) -> bool:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return True
    if isinstance(value, (int, float)):
        return math.isfinite(float(value))
    if isinstance(value, Mapping):
        return all(_finite(item) for item in value.values())
    if isinstance(value, Sequence):
        return all(_finite(item) for item in value)
    return False


def _validate_config(cfg: Mapping[str, Any], project: Path, design: Path) -> None:
    if cfg.get("schema_version") != 1 or cfg.get("stage") != STAGE:
        raise ValueError("D1R14R3 config identity changed")
    if cfg.get("identity") != IDENTITY:
        raise ValueError("D1R14R3 audit identity changed")
    if _sha256(design) != cfg.get("design_document_sha256"):
        raise ValueError("D1R14R3 frozen design hash mismatch")
    source = cfg["source_r2_contract"]
    for path_key, hash_key in (
        ("config", "config_sha256"),
        ("implementation", "implementation_sha256"),
        ("independent_implementation", "independent_implementation_sha256"),
    ):
        if _sha256(project / source[path_key]) != source[hash_key]:
            raise ValueError(f"D1R14R2 source code hash mismatch: {path_key}")
    split = cfg["sign_split_contract"]
    expected_split = {
        "context_count": 8,
        "signs": [1, -1],
        "direction_count": 4,
        "branch_count": 16,
        "branch_direction_count": 64,
        "minimum_direction_peak_normalized_outputs5": 0.005,
        "rank_relative_tolerance": 1e-10,
        "required_rank": 4,
        "maximum_condition_number": 20.0,
        "normalize_columns_to_unit_l2": True,
        "require_exact_issue_coordinate_sign_symmetry": True,
        "require_exact_issue_field_sign_symmetry": True,
        "cross_sign_response_symmetry_is_acceptance_gate": False,
    }
    if dict(split) != expected_split:
        raise ValueError("D1R14R3 frozen sign-split contract changed")
    execution = cfg["execution_contract"]
    if any(
        execution[key]
        for key in (
            "new_raw_count",
            "plant_steps_executed",
            "controller_executed",
            "ray_executed",
            "gotsc_executed",
            "tsc_executed",
            "snapshot_creation_allowed",
        )
    ):
        raise ValueError("D1R14R3 must remain zero-TSC and read-only")


def _visible(trajectory: Sequence[Mapping[str, Any]]) -> np.ndarray:
    rows: list[list[float]] = []
    for index, state in enumerate(trajectory):
        if index == 0:
            other = trajectory[1]
            v_r = (float(other["R"]) - float(state["R"])) / 0.01
            v_z = (float(other["Z"]) - float(state["Z"])) / 0.01
        else:
            previous = trajectory[index - 1]
            v_r = (float(state["R"]) - float(previous["R"])) / 0.01
            v_z = (float(state["Z"]) - float(previous["Z"])) / 0.01
        rows.append(
            [float(state["R"]), float(state["Z"]), v_r, v_z, float(state["Ip"])]
        )
    scales = np.asarray([0.03, 0.03, 0.1, 0.1, 10000.0], dtype=float)
    values = np.asarray(rows, dtype=float) / scales[None, :]
    return values - values[10][None, :]


def _load_r2_raw(
    run_dir: Path,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], Path]:
    stage = run_dir / r2_forensics.RUN_NAME
    specs = _strict_json(stage / "specs" / "sentinel_specs.json")
    if not isinstance(specs, list):
        raise ValueError("D1R14R2 specs are not a list")
    results: dict[str, dict[str, Any]] = {}
    for spec in specs:
        experiment_id = str(spec["experiment_id"])
        results[experiment_id] = _strict_gzip(
            stage / "raw" / f"{experiment_id}.json.gz"
        )
    return specs, results, stage


def _group_results(
    specs: Sequence[Mapping[str, Any]],
    results: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[tuple[str, int, int], Mapping[str, Any]]]:
    grouped: dict[str, dict[tuple[str, int, int], Mapping[str, Any]]] = {}
    for spec in specs:
        experiment_id = str(spec["experiment_id"])
        key = (
            str(spec["d1r14r2_role"]),
            int(spec["d1r14r2_direction_index"]),
            int(spec["d1r14r2_sign"]),
        )
        grouped.setdefault(str(spec["source_d1r13_experiment_id"]), {})[key] = (
            results[experiment_id]
        )
    return grouped


def _sign_split_geometry(
    cfg: Mapping[str, Any],
    specs: Sequence[Mapping[str, Any]],
    results: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    contract = cfg["sign_split_contract"]
    grouped = _group_results(specs, results)
    source_spec = {
        str(spec["source_d1r13_experiment_id"]): spec for spec in specs
    }
    rows: list[dict[str, Any]] = []
    for context_id in sorted(grouped):
        group = grouped[context_id]
        baseline = _visible(group[("baseline", -1, 0)]["trajectory"])[11:]
        for sign in (1, -1):
            columns: list[np.ndarray] = []
            directions: list[dict[str, Any]] = []
            for direction in range(4):
                member = _visible(
                    group[("signed_probe", direction, sign)]["trajectory"]
                )[11:]
                response = member - baseline if sign == 1 else baseline - member
                flattened = response.reshape(-1)
                peak = float(np.max(np.abs(response)))
                norm = float(np.linalg.norm(flattened))
                finite = bool(np.all(np.isfinite(response)))
                signal = bool(
                    finite
                    and peak
                    >= float(contract["minimum_direction_peak_normalized_outputs5"])
                    - 1e-15
                )
                columns.append(
                    flattened / norm
                    if finite and norm > 0.0
                    else np.full(flattened.shape, math.nan)
                )
                directions.append(
                    {
                        "direction_index": direction,
                        "direction_name": r2_forensics.DIRECTIONS[direction],
                        "peak_normalized_outputs5": peak,
                        "l2_norm": norm,
                        "finite": finite,
                        "signal_pass": signal,
                    }
                )
            matrix = np.column_stack(columns)
            finite_matrix = bool(np.all(np.isfinite(matrix)))
            singular = (
                np.linalg.svd(matrix, compute_uv=False)
                if finite_matrix
                else np.full(4, math.nan)
            )
            rank = (
                int(
                    np.sum(
                        singular
                        > singular[0] * float(contract["rank_relative_tolerance"])
                    )
                )
                if finite_matrix and singular[0] > 0.0
                else 0
            )
            condition = (
                float(singular[0] / singular[-1])
                if rank == 4 and singular[-1] > 0.0
                else None
            )
            passed = bool(
                all(row["signal_pass"] for row in directions)
                and rank == int(contract["required_rank"])
                and condition is not None
                and condition <= float(contract["maximum_condition_number"]) + 1e-12
            )
            meta = source_spec[context_id]
            rows.append(
                {
                    "source_d1r13_experiment_id": context_id,
                    "pair_id": meta["pair_id"],
                    "history_member": meta["history_member"],
                    "sign": sign,
                    "directions": directions,
                    "singular_values": [float(value) for value in singular],
                    "rank": rank,
                    "condition_number": condition,
                    "passed": passed,
                }
            )
    all_directions = [row for branch in rows for row in branch["directions"]]
    result = {
        "context_count": len(grouped),
        "branch_count": len(rows),
        "branch_direction_count": len(all_directions),
        "signal_pass_count": sum(bool(row["signal_pass"]) for row in all_directions),
        "rank_pass_count": sum(
            int(row["rank"]) == int(contract["required_rank"]) for row in rows
        ),
        "condition_pass_count": sum(
            row["condition_number"] is not None
            and row["condition_number"]
            <= float(contract["maximum_condition_number"]) + 1e-12
            for row in rows
        ),
        "minimum_direction_peak_normalized_outputs5": min(
            (row["peak_normalized_outputs5"] for row in all_directions), default=None
        ),
        "maximum_condition_number": max(
            (row["condition_number"] for row in rows if row["condition_number"] is not None),
            default=None,
        ),
        "rows": rows,
    }
    result["passed"] = bool(
        result["context_count"] == int(contract["context_count"])
        and result["branch_count"] == int(contract["branch_count"])
        and result["branch_direction_count"]
        == int(contract["branch_direction_count"])
        and result["signal_pass_count"]
        == int(contract["branch_direction_count"])
        and result["rank_pass_count"] == int(contract["branch_count"])
        and result["condition_pass_count"] == int(contract["branch_count"])
    )
    return result


def _issue_symmetry(
    specs: Sequence[Mapping[str, Any]],
    results: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    grouped = _group_results(specs, results)
    rows: list[dict[str, Any]] = []
    for context_id in sorted(grouped):
        group = grouped[context_id]
        for direction in range(4):
            positive = group[("signed_probe", direction, 1)]["controller_trace"][10][
                "r3c3t13s24d1r14r2_event_detail"
            ]
            negative = group[("signed_probe", direction, -1)]["controller_trace"][10][
                "r3c3t13s24d1r14r2_event_detail"
            ]
            pos_coordinate = np.asarray(positive["requested_coordinate"], dtype=float)
            neg_coordinate = np.asarray(negative["requested_coordinate"], dtype=float)
            pos_field = np.asarray(positive["actual_signed_delta_field_kAt_tsc"], dtype=float)
            neg_field = np.asarray(negative["actual_signed_delta_field_kAt_tsc"], dtype=float)
            coordinate_exact = bool(np.array_equal(pos_coordinate, -neg_coordinate))
            field_exact = bool(np.array_equal(pos_field, -neg_field))
            rows.append(
                {
                    "source_d1r13_experiment_id": context_id,
                    "direction_index": direction,
                    "coordinate_exact_sign_opposite": coordinate_exact,
                    "physical_field_exact_sign_opposite": field_exact,
                    "passed": coordinate_exact and field_exact,
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


def _r2_reproduced(
    cfg: Mapping[str, Any], geometry: Mapping[str, Any]
) -> dict[str, Any]:
    contract = cfg["r2_reproduction_contract"]
    tolerance = float(contract["numeric_absolute_tolerance"])
    failed_rows = [row for row in geometry["pair_rows"] if not row["symmetry_pass"]]
    aggregate_match = bool(
        int(geometry["signal_pass_count"]) == int(contract["signal_pass_count"])
        and int(geometry["symmetry_pass_count"]) == int(contract["symmetry_pass_count"])
        and int(geometry["rank_pass_count"]) == int(contract["rank_pass_count"])
        and int(geometry["condition_pass_count"])
        == int(contract["condition_pass_count"])
        and abs(
            float(geometry["minimum_odd_peak_normalized_outputs5"])
            - float(contract["minimum_odd_peak_normalized_outputs5"])
        )
        <= tolerance
        and abs(
            float(geometry["maximum_even_to_odd_peak_ratio"])
            - float(contract["maximum_even_to_odd_peak_ratio"])
        )
        <= tolerance
        and abs(
            float(geometry["maximum_condition_number"])
            - float(contract["maximum_condition_number"])
        )
        <= tolerance
    )
    return {
        "aggregate_match": aggregate_match,
        "original_geometry_passed": bool(geometry["passed"]),
        "failed_pair_count": len(failed_rows),
        "failed_pair_rows": failed_rows,
        "passed": bool(
            aggregate_match
            and not geometry["passed"]
            and len(failed_rows) == int(contract["failed_pair_count"])
        ),
    }


def audit(
    *,
    project: Path,
    config_path: Path,
    design: Path,
    source_r2_run: Path,
    source_d1r13_run: Path,
    source_d1r11_run: Path,
    source_r1a_output: Path,
    source_r2_independent_result: Path,
    source_posthoc: Path,
    logs: Sequence[Path],
) -> dict[str, Any]:
    project = project.resolve()
    cfg = _strict_json(config_path.resolve())
    _validate_config(cfg, project, design.resolve())
    source_contract = cfg["source_r2_contract"]
    r2_audit = r2_forensics.audit(
        source_r2_run,
        source_d1r13_run,
        source_d1r11_run,
        source_r1a_output,
        project,
        logs,
    )
    specs, results, stage = _load_r2_raw(source_r2_run.resolve())
    manifest = _strict_json(stage / "stage_manifest.json")
    saved_independent = _strict_json(source_r2_independent_result.resolve())
    _strict_json(source_posthoc.resolve())
    static_hashes = {
        "final_result": _sha256(stage / "analysis" / "final_result.json"),
        "stage_state": _sha256(stage / "stage_state.json"),
        "independent_result": _sha256(source_r2_independent_result.resolve()),
        "posthoc_diagnostic": _sha256(source_posthoc.resolve()),
    }
    expected_hashes = {
        "final_result": source_contract["final_result_sha256"],
        "stage_state": source_contract["stage_state_sha256"],
        "independent_result": source_contract["independent_result_sha256"],
        "posthoc_diagnostic": source_contract["posthoc_diagnostic_sha256"],
    }
    source_authenticated = bool(
        static_hashes == expected_hashes
        and r2_audit.get("audit_completed") is True
        and r2_audit.get("passed") is True
        and r2_audit.get("independent_route") == R2_ROUTE
        and r2_audit.get("official_route_reproduced") is True
        and int(r2_audit.get("safety_pass_count", -1))
        == int(source_contract["required_safety_pass_count"])
        and int(r2_audit.get("issue_exact_count", -1))
        == int(source_contract["required_issue_exact_count"])
        and int(r2_audit.get("cancel_exact_count", -1))
        == int(source_contract["required_cancel_exact_count"])
        and int(r2_audit.get("snapshot_pass_count", -1))
        == int(source_contract["required_snapshot_pass_count"])
        and (r2_audit.get("current_inventory") or {}).get("count")
        == int(source_contract["raw_count"])
        and (r2_audit.get("current_inventory") or {}).get("bytes")
        == int(source_contract["raw_total_bytes"])
        and (r2_audit.get("current_inventory") or {}).get("digest")
        == source_contract["raw_inventory_digest"]
        and (manifest.get("package_fingerprint") or {}).get("digest")
        == source_contract["package_fingerprint_digest"]
        and manifest.get("spec_digest") == source_contract["spec_digest"]
        and manifest.get("requested_matrix_digest")
        == source_contract["requested_matrix_digest"]
        and saved_independent.get("audit_completed") is True
        and saved_independent.get("independent_route") == R2_ROUTE
    )
    r2_geometry = r2_audit["response_geometry"]
    reproduction = _r2_reproduced(cfg, r2_geometry)
    issue_symmetry = _issue_symmetry(specs, results)
    split = _sign_split_geometry(cfg, specs, results)
    routes = cfg["routes"]
    if not source_authenticated:
        route = routes["source_fail"]
    elif not reproduction["passed"]:
        route = routes["r2_reproduction_fail"]
    elif not issue_symmetry["passed"] or not split["passed"]:
        route = routes["branch_fail"]
    else:
        route = routes["pass"]
    passed = route == routes["pass"]
    result = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "audit_revision": "primary_sign_split_response_raw_audit_v1",
        "audit_completed": True,
        "passed": passed,
        "route": route,
        "source_authenticated": source_authenticated,
        "source_r2_run": str(source_r2_run.resolve()),
        "source_static_hashes": static_hashes,
        "source_expected_hashes": expected_hashes,
        "source_r2_authentication": {
            key: r2_audit.get(key)
            for key in (
                "audit_completed",
                "passed",
                "independent_route",
                "official_route_reproduced",
                "strict_raw_parse_count",
                "safety_pass_count",
                "snapshot_pass_count",
                "issue_exact_count",
                "cancel_exact_count",
                "runtime_or_environment_error_count",
                "prefix_failure_count",
                "plant_failure_count",
                "action_safety_failure_count",
                "solver_error_count",
                "saturation_or_clip_count",
                "forbidden_trace_count",
                "maximum_current_utilization",
                "current_inventory",
            )
        },
        "r2_shared_model_reproduction": reproduction,
        "r2_response_geometry": r2_geometry,
        "issue_coordinate_and_field_symmetry": issue_symmetry,
        "sign_split_geometry": split,
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
            "packaging_import_or_deployment_error": False,
            "raw_or_snapshot_corruption": not source_authenticated,
            "summary_statistics_or_reporting_error": False,
            "r2_shared_odd_model_design_failure_reproduced": bool(
                reproduction["passed"]
            ),
            "sign_split_branch_design_failure": bool(
                source_authenticated and reproduction["passed"] and not split["passed"]
            ),
            "real_control_or_mpc_conclusion": False,
        },
        "scientific_boundary": dict(cfg["scientific_scope"]),
    }
    if not _finite(result):
        raise ValueError("D1R14R3 result contains non-finite values")
    return result


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
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    result = audit(
        project=args.project,
        config_path=args.config,
        design=args.design_document,
        source_r2_run=args.source_r2_run,
        source_d1r13_run=args.source_d1r13_run,
        source_d1r11_run=args.source_d1r11_run,
        source_r1a_output=args.source_r1a_output,
        source_r2_independent_result=args.source_r2_independent_result,
        source_posthoc=args.source_posthoc,
        logs=args.source_log,
    )
    args.output.mkdir(parents=True, exist_ok=False)
    output = args.output / "stage4_2r3c3t13s24d1r14r3_primary_v1.json"
    output.write_text(
        json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(output.resolve()),
                "sha256": _sha256(output),
                "route": result["route"],
                "passed": result["passed"],
                "zero_new_tsc": True,
            },
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
