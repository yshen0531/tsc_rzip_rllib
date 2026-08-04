#!/usr/bin/env python3
"""Independent server raw/snapshot audit for Stage4.2R3c3T13S24D1R14R4."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

import numpy as np


STAGE = "Stage4.2R3c3T13S24D1R14R4"
RUN_NAME = "stage4_2r3c3t13s24d1r14r4_time_shifted_sign_split_sentinel"
SOURCE_D1R13_NAME = "stage4_2r3c3t13s24d1r13_zero_increment_deconfounding_sentinel"
SOURCE_D1R11_NAME = (
    "stage4_2r3c3t13s24d1r11_full_replacement_sequential_transition_identification"
)
CAMPAIGN_IDENTITY = "time_shifted_sign_split_safety_identification_sentinel_v1"
CONTROLLER_REVISION = "time_shifted_sign_split_v42r3c3t13s24d1r14r4_v1"
N_COILS = 14
PREFIX_END = 10
ISSUE_STEPS = (14, 18, 22)
DIRECTIONS = (
    "pooled_mixed_0",
    "pooled_mixed_1",
    "pooled_mixed_2",
    "pooled_mixed_3",
)
R1A_OUTPUT_NAME = (
    "stage4_2r3c3t13s24d1r14r1a_quantization_margin_preflight_20260804_b8040b6_v1"
)
R1A_HASHES = {
    "stage4_2r3c3t13s24d1r14r1a_detailed_v1.json": (
        "a9ffc98b798d4735d7302b1ca4407dbc60266228007d82d34418a291df2b0e8d"
    ),
    "stage4_2r3c3t13s24d1r14r1a_summary_v1.json": (
        "77194861b0406257d055b5ebe0e087b9f9c8222e76600fa443de9d34e7fc682f"
    ),
    "stage4_2r3c3t13s24d1r14r1a_manifest_v1.json": (
        "d6b4c53c46b8948d979d3eaee1861885f61d33ac70097a7576110361f0bafa87"
    ),
}
R1A_MANIFEST_HASHES = {
    "detailed": R1A_HASHES[
        "stage4_2r3c3t13s24d1r14r1a_detailed_v1.json"
    ],
    "summary": R1A_HASHES[
        "stage4_2r3c3t13s24d1r14r1a_summary_v1.json"
    ],
    "manifest": R1A_HASHES[
        "stage4_2r3c3t13s24d1r14r1a_manifest_v1.json"
    ],
}
MATRIX_DIGEST = "c8cd62c00c1f60b46312927789659657dc8cc35717533193433b0e398c1ec94c"
PASS_ROUTE = "TIME_SHIFTED_SIGN_SPLIT_SENTINEL_PASS_CAUSAL_MODEL_FIT_DESIGN_REQUIRED"
RUNTIME_ROUTE = "TIME_SHIFTED_SIGN_SPLIT_SENTINEL_RUNTIME_OR_PREFIX_FAIL_STOP"
SAFETY_ROUTE = "TIME_SHIFTED_SIGN_SPLIT_SENTINEL_ACTION_SAFETY_FAIL_REDESIGN_REQUIRED"
GEOMETRY_ROUTE = "TIME_SHIFTED_SIGN_SPLIT_SENTINEL_GEOMETRY_FAIL_REDESIGN_REQUIRED"
SOURCE_R2_NAME = "stage4_2r3c3t13s24d1r14r2_mixed_basis_signed_excitation_sentinel"
D1R13_COUNT = 8
D1R13_BYTES = 241_738
D1R13_DIGEST = "f9b4dd9259736ebe2d26f9fcfd06bb0497be69a886de7ecc8d359009992f1c0a"
D1R11_COUNT = 600
D1R11_BYTES = 35_511_922
D1R11_DIGEST = "8812d9fb0a5cb5a8b8309e17985bd85d180a82bbb0f08c02105fb1a749c7c0e7"
NON_SEMANTIC = frozenset({"gotsc_subprocess_s", "step_total_s"})
EXPECTED_CALIBRATION = [
    "calibration_issue",
    "calibration_cancel",
    "calibration_issue",
    "calibration_cancel",
    "calibration_issue",
    "calibration_cancel",
    "calibration_issue",
    "calibration_cancel",
]
FORBIDDEN_TRACE_KEYS = (
    "future_measurement_used",
    "hidden_wire_used",
    "source_action_used",
    "source_coil_current_used",
    "source_wire_current_used",
    "current_run_future_used",
    "pair_or_history_label_used",
    "source_result_used",
    "future_probe_schedule_available_to_underlying_controller",
    "r3c3t13s21_partition_label_used",
    "r3c3t13s24_pair_history_partition_label_used",
    "r3c3t13s24_delay_slew_target_id_label_used",
    "r3c3t13s24_source_or_matched_baseline_used",
    "r3c3t13s24_future_measurement_used",
    "r3c3t13s24_future_executed_action_used",
    "r3c3t13s24_hidden_wire_current_used",
    "r3c3t13s24_schedule_available_to_underlying_controller",
    "r3c3t13s24d1r13_future_r17_executed",
    "r3c3t13s24d1r14r4_future_r17_executed",
)


def _strict_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def _strict_gzip(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(
            stream,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _r1a_authentication(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    files = {name: directory / name for name in R1A_HASHES}
    hashes = {
        name: _sha256(path) if path.is_file() else None for name, path in files.items()
    }
    detailed = _strict_json(files["stage4_2r3c3t13s24d1r14r1a_detailed_v1.json"])
    summary = _strict_json(files["stage4_2r3c3t13s24d1r14r1a_summary_v1.json"])
    manifest = _strict_json(files["stage4_2r3c3t13s24d1r14r1a_manifest_v1.json"])
    passed = bool(
        directory.name == R1A_OUTPUT_NAME
        and hashes == R1A_HASHES
        and detailed.get("identity") == "fixed_third_column_quantization_margin_preflight_v1"
        and detailed.get("passed") is True
        and detailed.get("route")
        == "QUANTIZATION_MARGIN_PREFLIGHT_PASS_R2_SENTINEL_DESIGN_REQUIRED"
        and (detailed.get("fixed_matrix") or {}).get("matrix_float64_le_c_sha256")
        == MATRIX_DIGEST
        and (detailed.get("fixed_matrix") or {}).get("passed") is True
        and int((detailed.get("static_issue_preflight") or {}).get("construction_count", -1))
        == 64
        and int(
            (detailed.get("static_issue_preflight") or {}).get(
                "construction_pass_count", -1
            )
        )
        == 64
        and int(
            ((detailed.get("source_d1r14_authentication") or {}).get("raw_inventory") or {}).get(
                "count", -1
            )
        )
        == 72
        and (detailed.get("static_issue_preflight") or {}).get(
            "online_cancellation_proved"
        )
        is False
        and (detailed.get("execution") or {}).get("tsc_executed") is False
        and int((detailed.get("execution") or {}).get("new_raw_count", -1)) == 0
        and summary.get("passed") is True
        and summary.get("matrix_digest") == MATRIX_DIGEST
        and summary.get("route")
        == "QUANTIZATION_MARGIN_PREFLIGHT_PASS_R2_SENTINEL_DESIGN_REQUIRED"
        and int(summary.get("static_issue_construction_count", -1)) == 64
        and int(summary.get("static_issue_construction_pass_count", -1)) == 64
        and int(summary.get("source_raw_count", -1)) == 72
        and summary.get("online_cancellation_proved") is False
        and summary.get("tsc_executed") is False
        and int(summary.get("new_raw_count", -1)) == 0
        and manifest.get("stage") == "Stage4.2R3c3T13S24D1R14R1A"
        and manifest.get("route")
        == "QUANTIZATION_MARGIN_PREFLIGHT_PASS_R2_SENTINEL_DESIGN_REQUIRED"
        and manifest.get("ray_gotsc_tsc_plant_or_controller_executed") is False
        and int(manifest.get("new_raw_files_created", -1)) == 0
        and manifest.get("outputs")
        == {
            "stage4_2r3c3t13s24d1r14r1a_detailed_v1.json": R1A_HASHES[
                "stage4_2r3c3t13s24d1r14r1a_detailed_v1.json"
            ],
            "stage4_2r3c3t13s24d1r14r1a_summary_v1.json": R1A_HASHES[
                "stage4_2r3c3t13s24d1r14r1a_summary_v1.json"
            ],
        }
    )
    return {
        "directory": str(directory),
        "hashes": hashes,
        "matrix_digest": summary.get("matrix_digest"),
        "passed": passed,
    }


def _r3_r2_authentication(
    project: Path,
    source_r2_run: Path,
    source_r3_initial_output: Path,
    source_r3_corrected_output: Path,
) -> dict[str, Any]:
    cfg = _strict_json(
        project
        / "configs/stage4_2r3c3t13s24d1r14r4_time_shifted_sign_split_sentinel_370ms.json"
    )
    r3 = cfg["source_r3_contract"]
    r2 = cfg["source_r2_contract"]
    r3_paths = {
        "initial_primary": source_r3_initial_output
        / "stage4_2r3c3t13s24d1r14r3_primary_v1.json",
        "initial_independent": source_r3_initial_output
        / "stage4_2r3c3t13s24d1r14r3_independent_v1.json",
        "corrected_primary": source_r3_corrected_output
        / "stage4_2r3c3t13s24d1r14r3_primary_v1.json",
        "corrected_independent": source_r3_corrected_output
        / "stage4_2r3c3t13s24d1r14r3_independent_v1.json",
        "compact_manifest": source_r3_corrected_output / "compact_evidence_manifest_v2.json",
    }
    r3_hashes = {name: _sha256(path) for name, path in r3_paths.items()}
    expected_r3_hashes = {
        name: str(r3[f"{name}_sha256"]) for name in r3_paths
    }
    initial_primary = _strict_json(r3_paths["initial_primary"])
    initial_independent = _strict_json(r3_paths["initial_independent"])
    corrected_primary = _strict_json(r3_paths["corrected_primary"])
    corrected_independent = _strict_json(r3_paths["corrected_independent"])
    split = corrected_primary.get("sign_split_geometry") or {}
    issue = corrected_primary.get("issue_coordinate_and_field_symmetry") or {}
    execution = corrected_primary.get("execution") or {}
    r3_passed = bool(
        source_r3_initial_output.name == r3["initial_output_name"]
        and source_r3_corrected_output.name == r3["corrected_output_name"]
        and r3_hashes == expected_r3_hashes
        and _sha256(project / r3["config"]) == r3["config_sha256"]
        and _sha256(project / r3["primary_implementation"])
        == r3["primary_implementation_sha256"]
        and _sha256(project / r3["independent_implementation"])
        == r3["independent_implementation_sha256"]
        and _sha256(project / r3["source_hash_erratum"])
        == r3["source_hash_erratum_sha256"]
        and initial_primary.get("route") == r3["required_initial_route"]
        and initial_independent.get("route") == r3["required_initial_route"]
        and initial_primary.get("passed") is False
        and initial_independent.get("passed") is False
        and corrected_primary.get("route") == r3["required_corrected_route"]
        and corrected_independent.get("route") == r3["required_corrected_route"]
        and corrected_primary.get("passed") is True
        and corrected_independent.get("passed") is True
        and corrected_independent.get("primary_exact_agreement") is True
        and int(split.get("signal_pass_count", -1)) == r3["required_signal_pass_count"]
        and int(split.get("rank_pass_count", -1)) == r3["required_rank_pass_count"]
        and int(split.get("condition_pass_count", -1))
        == r3["required_condition_pass_count"]
        and int(issue.get("coordinate_exact_count", -1))
        == r3["required_issue_symmetry_count"]
        and int(issue.get("physical_field_exact_count", -1))
        == r3["required_issue_symmetry_count"]
        and int(execution.get("new_raw_count", -1)) == r3["required_new_raw_count"]
        and bool(execution.get("tsc_executed")) == r3["required_tsc_executed"]
    )
    r2_stage = source_r2_run / SOURCE_R2_NAME
    r2_inventory = _raw_inventory(r2_stage / "raw")
    r2_final_path = r2_stage / "analysis/final_result.json"
    r2_independent_path = source_r2_run / "server_independent_forensics_v1.json"
    r2_final = _strict_json(r2_final_path)
    r2_independent = _strict_json(r2_independent_path)
    r2_specs = _strict_json(r2_stage / "specs/sentinel_specs.json")
    r2_passed = bool(
        source_r2_run.name == r2["run_name"]
        and r2_inventory["count"] == r2["raw_count"]
        and r2_inventory["bytes"] == r2["raw_total_bytes"]
        and r2_inventory["digest"] == r2["raw_inventory_digest"]
        and _sha256(r2_final_path) == r2["final_result_sha256"]
        and _sha256(r2_independent_path) == r2["independent_result_sha256"]
        and r2_final.get("route") == r2["required_route"]
        and r2_independent.get("independent_route") == r2["required_route"]
        and r2_independent.get("audit_completed") is True
        and int(r2_final.get("safety_pass_count", -1))
        == r2["required_safety_pass_count"]
        and len(r2_specs) == r2["raw_count"]
        and sum(spec.get("d1r14r2_role") == "baseline" for spec in r2_specs)
        == r2["required_baseline_count"]
        and sum(spec.get("d1r14r2_role") == "signed_probe" for spec in r2_specs)
        == r2["required_signed_probe_count"]
    )
    return {
        "r3_hashes": r3_hashes,
        "r3_passed": r3_passed,
        "r2_inventory": r2_inventory,
        "r2_specs_count": len(r2_specs),
        "r2_passed": r2_passed,
        "passed": r3_passed and r2_passed,
    }


def _raw_inventory(directory: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    rows = []
    total = 0
    for path in sorted(directory.glob("*.json.gz")):
        size = path.stat().st_size
        sha = _sha256(path)
        total += size
        digest.update(f"{path.name}\0{size}\0{sha}\n".encode())
        rows.append({"name": path.name, "size": size, "sha256": sha})
    return {"count": len(rows), "bytes": total, "digest": digest.hexdigest(), "rows": rows}


def _semantic(row: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key not in NON_SEMANTIC}


def _trace_projection(source: Mapping[str, Any], current: Mapping[str, Any]) -> bool:
    return all(current.get(key) == value for key, value in source.items())


def _all_finite(values: Any) -> bool:
    if isinstance(values, bool):
        return True
    if isinstance(values, (int, float)):
        return math.isfinite(float(values))
    if isinstance(values, Sequence) and not isinstance(values, (str, bytes)):
        return all(_all_finite(value) for value in values)
    return False


def _nested_true_count(value: Any, names: frozenset[str]) -> int:
    if isinstance(value, Mapping):
        count = 0
        for key, item in value.items():
            if str(key) in names:
                if isinstance(item, Sequence) and not isinstance(item, (str, bytes)):
                    count += sum(bool(flag) for flag in item)
                else:
                    count += int(bool(item))
            count += _nested_true_count(item, names)
        return count
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return sum(_nested_true_count(item, names) for item in value)
    return 0


def _snapshot_inventory(snapshot: Path, expected_digest: str) -> dict[str, Any]:
    manifest_path = snapshot / "restart_snapshot_manifest.json"
    manifest = _strict_json(manifest_path)
    rows = list(manifest.get("files") or [])
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    row_digest = hashlib.sha256(canonical.encode()).hexdigest()
    failures = []
    for row in rows:
        path = snapshot / str(row["name"])
        if (
            not path.is_file()
            or path.stat().st_size != int(row["size_bytes"])
            or _sha256(path) != str(row["sha256"])
        ):
            failures.append(str(row["name"]))
    passed = bool(
        rows
        and not manifest.get("missing_required_files")
        and str(manifest.get("digest")) == expected_digest == row_digest
        and not failures
    )
    return {
        "snapshot_dir": str(snapshot),
        "manifest_sha256": _sha256(manifest_path),
        "file_count": len(rows),
        "total_bytes": sum(int(row["size_bytes"]) for row in rows),
        "failure_files": failures,
        "passed": passed,
    }


def _log_audit(paths: Sequence[Path]) -> list[dict[str, Any]]:
    pattern = re.compile(r"Traceback|ERROR|RayTaskError|Killed")
    rows = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="strict")
        rows.append(
            {
                "path": str(path),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
                "line_count": len(text.splitlines()),
                "error_marker_count": len(pattern.findall(text)),
                "passed": not pattern.search(text),
            }
        )
    return rows


def _event_passes(
    event: Mapping[str, Any], *, expected_name: str, slot: int, task_step: int
) -> bool:
    criteria = event.get("criteria") or {}
    return bool(
        event.get("event") == expected_name
        and int(event.get("slot", -1)) == slot
        and int(event.get("task_step", -1)) == task_step
        and event.get("passed")
        and criteria
        and all(bool(value) for value in criteria.values())
    )


def _optional_close(left: Any, right: Any, *, atol: float = 1e-12) -> bool:
    if left is None or right is None:
        return left is None and right is None
    return math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=atol)


def _visible(trajectory: Sequence[Mapping[str, Any]]) -> np.ndarray:
    scales = np.asarray([0.03, 0.03, 0.1, 0.1, 10000.0], dtype=float)
    rows = []
    for index, state in enumerate(trajectory):
        if index == 0:
            other = trajectory[1]
            v_r = (float(other["R"]) - float(state["R"])) / 0.01
            v_z = (float(other["Z"]) - float(state["Z"])) / 0.01
        else:
            previous = trajectory[index - 1]
            v_r = (float(state["R"]) - float(previous["R"])) / 0.01
            v_z = (float(state["Z"]) - float(previous["Z"])) / 0.01
        rows.append([state["R"], state["Z"], v_r, v_z, state["Ip"]])
    values = np.asarray(rows, dtype=float) / scales[None, :]
    return values - values[PREFIX_END][None, :]


def _geometry(
    specs: Sequence[Mapping[str, Any]],
    results: Mapping[str, Mapping[str, Any]],
    source_r2_specs: Sequence[Mapping[str, Any]],
    source_r2_results: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    def group(
        bank_specs: Sequence[Mapping[str, Any]],
        bank_results: Mapping[str, Mapping[str, Any]],
        prefix: str,
        default_issue: int,
    ) -> dict[str, dict[tuple[str, int, int, int], Mapping[str, Any]]]:
        index = {str(spec["experiment_id"]): spec for spec in bank_specs}
        output: dict[str, dict[tuple[str, int, int, int], Mapping[str, Any]]] = {}
        for experiment_id, result in bank_results.items():
            spec = index[str(experiment_id)]
            role = str(spec[f"{prefix}_role"])
            issue = int(spec.get(f"{prefix}_issue_task_step", default_issue)) if role == "signed_probe" else -1
            key = (
                role,
                issue,
                int(spec[f"{prefix}_direction_index"]),
                int(spec[f"{prefix}_sign"]),
            )
            output.setdefault(str(spec["source_d1r13_experiment_id"]), {})[key] = result
        return output

    r2_groups = group(source_r2_specs, source_r2_results, "d1r14r2", 10)
    r4_groups = group(specs, results, "d1r14r4", -1)
    meta = {
        str(spec["source_d1r13_experiment_id"]): spec for spec in specs
    }
    branch_rows = []
    issue_rows = []
    cross_sign_rows = []
    responses: dict[tuple[str, int, int, int], np.ndarray] = {}
    for context_id in sorted(meta):
        r2_group = r2_groups[context_id]
        r4_group = r4_groups[context_id]
        r2_baseline = r2_group[("baseline", -1, -1, 0)]
        r4_baseline = r4_group[("baseline", -1, -1, 0)]
        for issue_step in (10, 14, 18, 22):
            source_stage = "D1R14R2" if issue_step == 10 else "D1R14R4"
            prefix = "d1r14r2" if issue_step == 10 else "d1r14r4"
            members = r2_group if issue_step == 10 else r4_group
            baseline_result = r2_baseline if issue_step == 10 else r4_baseline
            baseline = _visible(baseline_result["trajectory"])[issue_step + 1 :]
            signed: dict[int, list[Mapping[str, Any]]] = {}
            for sign in (1, -1):
                columns = []
                directions = []
                signed[sign] = []
                for direction, name in enumerate(DIRECTIONS):
                    current = members[("signed_probe", issue_step, direction, sign)]
                    member = _visible(current["trajectory"])[issue_step + 1 :]
                    response = member - baseline if sign == 1 else baseline - member
                    flattened = response.reshape(-1)
                    peak = float(np.max(np.abs(response)))
                    norm = float(np.linalg.norm(flattened))
                    finite = bool(np.all(np.isfinite(response)))
                    signal = bool(finite and norm > 0.0 and peak >= 0.005 - 1e-15)
                    columns.append(
                        flattened / norm
                        if finite and norm > 0.0
                        else np.full(flattened.shape, math.nan)
                    )
                    signed[sign].append(current)
                    responses[(context_id, issue_step, sign, direction)] = response
                    directions.append(
                        {
                            "direction_index": direction,
                            "direction_name": name,
                            "experiment_id": current["experiment_id"],
                            "peak_normalized_outputs5": peak,
                            "l2_norm": norm,
                            "finite": finite,
                            "signal_pass": signal,
                        }
                    )
                matrix = np.column_stack(columns)
                finite_matrix = bool(np.all(np.isfinite(matrix)))
                singular = np.linalg.svd(matrix, compute_uv=False) if finite_matrix else np.full(4, math.nan)
                rank = int(np.sum(singular > singular[0] * 1e-10)) if finite_matrix and singular[0] > 0.0 else 0
                condition = float(singular[0] / singular[-1]) if rank == 4 and singular[-1] > 0.0 else None
                branch_rows.append(
                    {
                        "source_d1r13_experiment_id": context_id,
                        "pair_id": meta[context_id]["pair_id"],
                        "history_member": meta[context_id]["history_member"],
                        "source_stage": source_stage,
                        "issue_task_step": issue_step,
                        "sign": sign,
                        "directions": directions,
                        "singular_values": [float(value) if math.isfinite(float(value)) else None for value in singular],
                        "rank": rank,
                        "condition_number": condition,
                        "passed": bool(
                            all(row["signal_pass"] for row in directions)
                            and rank == 4
                            and condition is not None
                            and condition <= 20.0 + 1e-12
                        ),
                    }
                )
            for direction, name in enumerate(DIRECTIONS):
                positive = signed[1][direction]
                negative = signed[-1][direction]
                positive_event = positive["controller_trace"][issue_step].get(
                    f"r3c3t13s24{prefix}_event_detail"
                ) or {}
                negative_event = negative["controller_trace"][issue_step].get(
                    f"r3c3t13s24{prefix}_event_detail"
                ) or {}
                pc = np.asarray(positive_event.get("requested_coordinate", []), dtype=float)
                nc = np.asarray(negative_event.get("requested_coordinate", []), dtype=float)
                pf = np.asarray(positive_event.get("actual_signed_delta_field_kAt_tsc", []), dtype=float)
                nf = np.asarray(negative_event.get("actual_signed_delta_field_kAt_tsc", []), dtype=float)
                coordinate_exact = bool(pc.shape == nc.shape == (4,) and np.array_equal(pc, -nc))
                field_exact = bool(pf.shape == nf.shape == (14,) and np.array_equal(pf, -nf))
                issue_rows.append(
                    {
                        "source_d1r13_experiment_id": context_id,
                        "source_stage": source_stage,
                        "issue_task_step": issue_step,
                        "direction_index": direction,
                        "coordinate_exact_sign_opposite": coordinate_exact,
                        "physical_field_exact_sign_opposite": field_exact,
                        "passed": coordinate_exact and field_exact,
                    }
                )
                left = responses[(context_id, issue_step, 1, direction)]
                right = responses[(context_id, issue_step, -1, direction)]
                peak = max(float(np.max(np.abs(left))), float(np.max(np.abs(right))))
                difference = float(np.max(np.abs(left - right)))
                cross_sign_rows.append(
                    {
                        "source_d1r13_experiment_id": context_id,
                        "issue_task_step": issue_step,
                        "direction_index": direction,
                        "maximum_absolute_branch_difference": difference,
                        "relative_to_branch_peak": difference / peak if peak > 0.0 else None,
                        "acceptance_gate": False,
                    }
                )
    history_rows = []
    pair_contexts: dict[str, list[str]] = {}
    for context_id, spec in meta.items():
        pair_contexts.setdefault(str(spec["pair_id"]), []).append(context_id)
    for pair_id, contexts in sorted(pair_contexts.items()):
        for issue_step in (10, 14, 18, 22):
            for sign in (1, -1):
                for direction, name in enumerate(DIRECTIONS):
                    left = responses[(contexts[0], issue_step, sign, direction)]
                    right = responses[(contexts[1], issue_step, sign, direction)]
                    peak = max(float(np.max(np.abs(left))), float(np.max(np.abs(right))))
                    difference = float(np.max(np.abs(left - right)))
                    history_rows.append(
                        {
                            "pair_id": pair_id,
                            "issue_task_step": issue_step,
                            "sign": sign,
                            "direction_index": direction,
                            "direction_name": name,
                            "maximum_absolute_response_difference": difference,
                            "relative_to_pair_response_peak": difference / peak if peak > 0.0 else None,
                            "acceptance_gate": False,
                        }
                    )
    cross_time_rows = []
    for context_id in meta:
        for sign in (1, -1):
            for direction, name in enumerate(DIRECTIONS):
                times = (10, 14, 18, 22)
                for left_index, left_time in enumerate(times):
                    for right_time in times[left_index + 1 :]:
                        left = responses[(context_id, left_time, sign, direction)]
                        right = responses[(context_id, right_time, sign, direction)]
                        common = min(len(left), len(right))
                        difference = float(np.max(np.abs(left[:common] - right[:common])))
                        peak = max(float(np.max(np.abs(left[:common]))), float(np.max(np.abs(right[:common]))))
                        cross_time_rows.append(
                            {
                                "source_d1r13_experiment_id": context_id,
                                "sign": sign,
                                "direction_index": direction,
                                "direction_name": name,
                                "issue_task_steps": [left_time, right_time],
                                "maximum_absolute_response_difference": difference,
                                "relative_to_response_peak": difference / peak if peak > 0.0 else None,
                                "acceptance_gate": False,
                            }
                        )
    all_directions = [row for branch in branch_rows for row in branch["directions"]]
    condition_values = [row["condition_number"] for row in branch_rows if row["condition_number"] is not None]
    source_issue = [row for row in issue_rows if row["source_stage"] == "D1R14R2"]
    new_issue = [row for row in issue_rows if row["source_stage"] == "D1R14R4"]
    issue_symmetry = {
        "source_pair_count": len(source_issue),
        "new_pair_count": len(new_issue),
        "combined_pair_count": len(issue_rows),
        "coordinate_exact_count": sum(row["coordinate_exact_sign_opposite"] for row in issue_rows),
        "physical_field_exact_count": sum(row["physical_field_exact_sign_opposite"] for row in issue_rows),
        "rows": issue_rows,
        "passed": bool(len(source_issue) == 32 and len(new_issue) == 96 and all(row["passed"] for row in issue_rows)),
    }
    signal_count = sum(row["signal_pass"] for row in all_directions)
    rank_count = sum(row["rank"] == 4 for row in branch_rows)
    condition_count = sum(
        row["condition_number"] is not None and row["condition_number"] <= 20.0 + 1e-12
        for row in branch_rows
    )
    return {
        "evaluated": True,
        "context_count": len(meta),
        "issue_task_steps": [10, 14, 18, 22],
        "branch_count": len(branch_rows),
        "branch_direction_count": len(all_directions),
        "signal_pass_count": signal_count,
        "rank_pass_count": rank_count,
        "condition_pass_count": condition_count,
        "minimum_direction_peak_normalized_outputs5": min(
            (row["peak_normalized_outputs5"] for row in all_directions), default=None
        ),
        "maximum_condition_number": max(condition_values, default=None),
        "branch_rows": branch_rows,
        "issue_coordinate_and_field_symmetry": issue_symmetry,
        "cross_sign_response_rows_report_only": cross_sign_rows,
        "matched_hidden_history_rows_report_only": history_rows,
        "cross_time_response_rows_report_only": cross_time_rows,
        "passed": bool(
            len(meta) == 8
            and len(branch_rows) == 64
            and len(all_directions) == 256
            and signal_count == 256
            and rank_count == 64
            and condition_count == 64
            and issue_symmetry["passed"]
        ),
    }


def audit(
    run_dir: Path,
    source_d1r13_run: Path,
    source_d1r11_run: Path,
    source_r1a_output: Path,
    source_r2_run: Path,
    source_r3_initial_output: Path,
    source_r3_corrected_output: Path,
    project: Path,
    logs: Sequence[Path],
) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    source_d1r13_run = source_d1r13_run.resolve()
    source_d1r11_run = source_d1r11_run.resolve()
    source_r1a_output = source_r1a_output.resolve()
    source_r2_run = source_r2_run.resolve()
    source_r3_initial_output = source_r3_initial_output.resolve()
    source_r3_corrected_output = source_r3_corrected_output.resolve()
    project = project.resolve()
    stage = run_dir / RUN_NAME
    source13_stage = source_d1r13_run / SOURCE_D1R13_NAME
    source11_stage = source_d1r11_run / SOURCE_D1R11_NAME
    specs = _strict_json(stage / "specs/sentinel_specs.json")
    state = _strict_json(stage / "stage_state.json")
    manifest = _strict_json(stage / "stage_manifest.json")
    final = _strict_json(stage / "analysis/final_result.json")
    root_final = _strict_json(run_dir / "final_result.json")
    inventory = _raw_inventory(stage / "raw")
    source13_inventory = _raw_inventory(source13_stage / "raw")
    source11_inventory = _raw_inventory(source11_stage / "raw")
    r1a = _r1a_authentication(source_r1a_output)
    r3_r2 = _r3_r2_authentication(
        project,
        source_r2_run,
        source_r3_initial_output,
        source_r3_corrected_output,
    )
    source_r2_stage = source_r2_run / SOURCE_R2_NAME
    source_r2_specs = _strict_json(source_r2_stage / "specs/sentinel_specs.json")
    source_r2_results = {}
    source_r2_identity_count = 0
    for source_spec in source_r2_specs:
        source_id = str(source_spec["experiment_id"])
        source_result = _strict_gzip(source_r2_stage / "raw" / f"{source_id}.json.gz")
        source_r2_results[source_id] = source_result
        source_r2_identity_count += int(
            source_result.get("stage") == "Stage4.2R3c3T13S24D1R14R2"
            and source_result.get("campaign_identity")
            == "mixed_basis_signed_excitation_safety_geometry_sentinel_v1"
            and source_result.get("experiment_id") == source_id
            and source_result.get("spec") == source_spec
            and source_result.get("success") is True
            and source_result.get("completed") is True
        )
    rows = []
    results = {}
    snapshots: dict[str, dict[str, Any]] = {}
    for spec in specs:
        experiment_id = str(spec["experiment_id"])
        path = stage / "raw" / f"{experiment_id}.json.gz"
        current = _strict_gzip(path)
        results[experiment_id] = current
        source13_id = str(spec["source_d1r13_experiment_id"])
        source11_id = str(spec["source_d1r11_experiment_id"])
        source13_path = source13_stage / "raw" / f"{source13_id}.json.gz"
        source11_path = source11_stage / "raw" / f"{source11_id}.json.gz"
        source13 = _strict_gzip(source13_path)
        source11 = _strict_gzip(source11_path)
        horizon = int(spec["horizon_steps"])
        trajectory = list(current.get("trajectory") or [])
        trace = list(current.get("controller_trace") or [])
        full = len(trajectory) == horizon + 1 and len(trace) == horizon
        prefix_state = bool(
            len(trajectory) >= 11
            and all(
                _semantic(left) == _semantic(right)
                for left, right in zip(trajectory[:11], source13["trajectory"][:11])
            )
        )
        prefix_trace = bool(
            len(trace) >= 10
            and all(
                _trace_projection(reference, actual)
                for reference, actual in zip(source11["controller_trace"][:10], trace[:10])
            )
        )
        calibration = [
            row.get("r3c3t13s16_lattice_event")
            for row in trace[:10]
            if row.get("r3c3t13s16_lattice_event") != "none"
        ] == EXPECTED_CALIBRATION
        currents = [list(map(float, row.get("currents_a_tsc") or [])) for row in trajectory]
        finite = bool(
            full
            and all(
                _all_finite([row.get("R"), row.get("Z"), row.get("Ip")])
                and len(row.get("currents_a_tsc") or []) == 14
                and _all_finite(row.get("currents_a_tsc") or [])
                and bool(row.get("wire_currents_a"))
                and _all_finite(row.get("wire_currents_a") or [])
                and int(row.get("wire_current_count", -1)) == len(row.get("wire_currents_a") or [])
                and not row.get("abnormal")
                for row in trajectory
            )
        )
        forbidden = sum(any(bool(row.get(key)) for key in FORBIDDEN_TRACE_KEYS) for row in trace)
        solver = sum(not bool(row.get("solver_success")) for row in trace)
        saturation = _nested_true_count(trace, frozenset({"action_saturated", "current_limit_clipped"}))
        payload = _strict_json(stage / "variants" / f"payload_{experiment_id}.json")
        minimum = list(map(float, payload["min_current_tsc"]))
        maximum = list(map(float, payload["max_current_tsc"]))
        utilization = max(
            abs((value - 0.5 * (lo + hi)) / (0.5 * (hi - lo)))
            for current_row in currents
            for value, lo, hi in zip(current_row, minimum, maximum)
        ) if full else None
        role = str(spec["d1r14r4_role"])
        baseline_reproduction = issue_exact = cancel_exact = False
        preissue_zero_actions = preissue_zero_currents = False
        zero_actions = zero_currents = False
        if role == "baseline" and full:
            baseline_reproduction = bool(
                all(
                    _semantic(left) == _semantic(right)
                    for left, right in zip(trajectory, source13["trajectory"])
                )
                and [row.get("action_norm_tsc") for row in trace]
                == [row.get("action_norm_tsc") for row in source13["controller_trace"]]
            )
            zero_actions = all(
                list(map(float, row.get("action_norm_tsc") or [])) == [0.0] * 14
                for row in trace[10:]
            )
            zero_currents = all(currents[index + 1] == currents[index] for index in range(10, horizon))
            role_pass = baseline_reproduction and zero_actions and zero_currents
        elif role == "signed_probe" and full:
            direction = int(spec["d1r14r4_direction_index"])
            issue_step = int(spec["d1r14r4_issue_task_step"])
            cancel_step = int(spec["d1r14r4_cancel_task_step"])
            zero_after_step = int(spec["d1r14r4_zero_after_task_step"])
            preissue_zero_actions = all(
                list(map(float, row.get("action_norm_tsc") or [])) == [0.0] * 14
                for row in trace[10:issue_step]
            )
            preissue_zero_currents = all(
                currents[index + 1] == currents[index]
                for index in range(10, issue_step)
            )
            issue = trace[issue_step].get("r3c3t13s24d1r14r4_event_detail") or {}
            cancel = trace[cancel_step].get("r3c3t13s24d1r14r4_event_detail") or {}
            issue_exact = bool(
                _event_passes(issue, expected_name="sequential_issue", slot=direction, task_step=issue_step)
                and list(map(float, issue.get("requested_coordinate") or []))
                == list(map(float, spec["d1r14r4_requested_coordinate"]))
            )
            cancel_exact = bool(
                _event_passes(cancel, expected_name="sequential_cancel", slot=direction, task_step=cancel_step)
                and cancel.get("stored_center_card15_fields") == issue.get("center_card15_fields")
            )
            zero_actions = all(
                list(map(float, row.get("action_norm_tsc") or [])) == [0.0] * 14
                for row in trace[zero_after_step:]
            )
            zero_currents = all(
                currents[index + 1] == currents[index]
                for index in range(zero_after_step, horizon)
            )
            role_pass = bool(
                preissue_zero_actions
                and preissue_zero_currents
                and issue_exact
                and cancel_exact
                and zero_actions
                and zero_currents
            )
        else:
            role_pass = False
        snapshot_key = str(spec["restart_snapshot_dir"])
        if snapshot_key not in snapshots:
            snapshots[snapshot_key] = _snapshot_inventory(
                Path(snapshot_key).resolve(), str(spec["restart_snapshot_manifest_digest"])
            )
        summary = current.get("hidden_history_control_summary") or {}
        fresh = bool(
            summary.get("fresh_controller_actor")
            and summary.get("fresh_tsc_process")
            and summary.get("full_tsc_hidden_state_loaded_from_sprsina")
            and not summary.get("future_r17_controller_executed")
        )
        identity = bool(
            current.get("stage") == STAGE
            and current.get("campaign_identity") == CAMPAIGN_IDENTITY
            and current.get("controller_revision") == CONTROLLER_REVISION
            and current.get("experiment_id") == experiment_id
            and current.get("spec") == spec
            and spec.get("d1r14r4_requested_matrix_digest") == MATRIX_DIGEST
            and str(spec.get("d1r14r4_direction_name", ""))
            == (DIRECTIONS[int(spec["d1r14r4_direction_index"])] if role == "signed_probe" else "")
            and _sha256(source13_path) == str(spec["source_d1r13_raw_sha256"])
            and source13_path.stat().st_size == int(spec["source_d1r13_raw_size_bytes"])
            and source13.get("success") is True
            and source11.get("success") is True
        )
        passed = bool(
            identity
            and current.get("success") is True
            and current.get("completed") is True
            and full
            and prefix_state
            and prefix_trace
            and calibration
            and role_pass
            and finite
            and forbidden == solver == saturation == 0
            and utilization is not None
            and utilization <= 0.55 + 1e-12
            and fresh
            and snapshots[snapshot_key]["passed"]
        )
        rows.append(
            {
                "experiment_id": experiment_id,
                "source_d1r13_experiment_id": source13_id,
                "source_d1r11_experiment_id": source11_id,
                "role": role,
                "identity_exact": identity,
                "runtime_success": bool(
                    current.get("success") is True
                    and current.get("completed") is True
                    and not current.get("failure_reason")
                    and not current.get("execution_failure_class")
                ),
                "execution_failure_class": str(
                    current.get("execution_failure_class") or ""
                ),
                "full_horizon": full,
                "source_prefix_state_exact": prefix_state,
                "source_prefix_trace_exact": prefix_trace,
                "calibration_exact": calibration,
                "fresh_baseline_reproduces_d1r13": baseline_reproduction,
                "preissue_actions_exact_zero": preissue_zero_actions,
                "preissue_current_increments_exact_zero": preissue_zero_currents,
                "issue_exact": issue_exact,
                "cancel_exact": cancel_exact,
                "zero_after_role_actions_exact": zero_actions,
                "zero_after_role_current_increments_exact": zero_currents,
                "finite_coil_and_wire_records": finite,
                "forbidden_trace_count": forbidden,
                "solver_error_count": solver,
                "saturation_or_clip_count": saturation,
                "fresh_controller_and_tsc": fresh,
                "maximum_current_utilization": utilization,
                "raw_sha256": _sha256(path),
                "raw_size_bytes": path.stat().st_size,
                "passed": passed,
            }
        )
    safety_pass_count = sum(bool(row["passed"]) for row in rows)
    runtime_error_count = sum(
        row["execution_failure_class"]
        in {"runtime_or_controller_error", "ray_actor_runtime_error"}
        for row in rows
    )
    prefix_failure_count = sum(
        not (
            row["source_prefix_state_exact"]
            and row["source_prefix_trace_exact"]
            and row["calibration_exact"]
        )
        for row in rows
    )
    plant_failure_count = sum(
        row["execution_failure_class"].startswith("plant_") for row in rows
    )
    action_safety_failure_count = sum(
        row["execution_failure_class"]
        in {"controller_action_safety_gate_failure", "controller_or_action_semantics_error"}
        for row in rows
    )
    geometry = (
        _geometry(specs, results, source_r2_specs, source_r2_results)
        if len(rows) == 200 and safety_pass_count == 200
        else {"evaluated": False, "passed": False, "reason": "safety_or_prefix_gate_failed"}
    )
    log_rows = _log_audit(logs)
    official_geometry = final.get("response_geometry") or {}
    geometry_match = bool(
        geometry.get("evaluated") == official_geometry.get("evaluated")
        and geometry.get("passed") == official_geometry.get("passed")
        and geometry.get("branch_count") == official_geometry.get("branch_count")
        and geometry.get("branch_direction_count")
        == official_geometry.get("branch_direction_count")
        and geometry.get("signal_pass_count") == official_geometry.get("signal_pass_count")
        and geometry.get("rank_pass_count") == official_geometry.get("rank_pass_count")
        and geometry.get("condition_pass_count") == official_geometry.get("condition_pass_count")
        and _optional_close(
            geometry.get("minimum_direction_peak_normalized_outputs5"),
            official_geometry.get("minimum_direction_peak_normalized_outputs5"),
        )
        and _optional_close(
            geometry.get("maximum_condition_number"),
            official_geometry.get("maximum_condition_number"),
        )
        and (geometry.get("issue_coordinate_and_field_symmetry") or {}).get("source_pair_count")
        == (official_geometry.get("issue_coordinate_and_field_symmetry") or {}).get("source_pair_count")
        and (geometry.get("issue_coordinate_and_field_symmetry") or {}).get("new_pair_count")
        == (official_geometry.get("issue_coordinate_and_field_symmetry") or {}).get("new_pair_count")
        and (geometry.get("issue_coordinate_and_field_symmetry") or {}).get("coordinate_exact_count")
        == (official_geometry.get("issue_coordinate_and_field_symmetry") or {}).get("coordinate_exact_count")
        and (geometry.get("issue_coordinate_and_field_symmetry") or {}).get("physical_field_exact_count")
        == (official_geometry.get("issue_coordinate_and_field_symmetry") or {}).get("physical_field_exact_count")
    )
    if runtime_error_count > 0 or prefix_failure_count > 0 or inventory["count"] != 200:
        independent_route = RUNTIME_ROUTE
    elif safety_pass_count != 200:
        independent_route = SAFETY_ROUTE
    elif not geometry.get("passed"):
        independent_route = GEOMETRY_ROUTE
    else:
        independent_route = PASS_ROUTE
    official_route_reproduced = bool(
        final.get("route") == independent_route
        and bool(final.get("passed"))
        == (independent_route == PASS_ROUTE)
        and int(final.get("safety_pass_count", -1)) == safety_pass_count
        and int(final.get("runtime_error_count", -1)) == runtime_error_count
        and int(final.get("prefix_failure_count", -1)) == prefix_failure_count
    )
    audit_completed = bool(
        len(specs) == 200
        and len({row["experiment_id"] for row in specs}) == 200
        and _digest(specs) == str(manifest["spec_digest"])
        and r1a["passed"]
        and r3_r2["passed"]
        and source_r2_identity_count == 72
        and manifest.get("source_r1a_output") == str(source_r1a_output)
        and manifest.get("source_r1a_hashes") == R1A_MANIFEST_HASHES
        and manifest.get("source_r2_run") == str(source_r2_run)
        and manifest.get("source_r3_initial_output") == str(source_r3_initial_output)
        and manifest.get("source_r3_corrected_output") == str(source_r3_corrected_output)
        and manifest.get("requested_matrix_digest") == MATRIX_DIGEST
        and source13_inventory["count"] == D1R13_COUNT
        and source13_inventory["bytes"] == D1R13_BYTES
        and source13_inventory["digest"] == D1R13_DIGEST
        and source11_inventory["count"] == D1R11_COUNT
        and source11_inventory["bytes"] == D1R11_BYTES
        and source11_inventory["digest"] == D1R11_DIGEST
        and inventory["count"] == 200
        and len(rows) == 200
        and all(row["identity_exact"] for row in rows)
        and len(snapshots) == 8
        and all(row["passed"] for row in snapshots.values())
        and all(row["passed"] for row in log_rows)
        and geometry_match
        and final == root_final
        and official_route_reproduced
        and state.get("phase_status") in {"complete", "failed"}
        and state.get("finished") is True
        and state.get("real_tsc_executed") is True
        and int(state.get("new_raw_count", -1)) == 200
    )
    package_hashes = {
        name: _sha256(project / name)
        for name in (
            "PACKAGE_MANIFEST.json",
            "SHA256SUMS",
            "configs/stage4_2r3c3t13s24d1r14r4_time_shifted_sign_split_sentinel_370ms.json",
            "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r4_time_shifted_sign_split_sentinel.py",
        )
    }
    return {
        "schema_version": 1,
        "stage": STAGE,
        "audit_revision": "independent_server_raw_snapshot_geometry_audit_v1",
        "passed": audit_completed,
        "audit_completed": audit_completed,
        "independent_route": independent_route,
        "official_route_reproduced": official_route_reproduced,
        "run_dir": str(run_dir),
        "source_d1r13_run": str(source_d1r13_run),
        "source_d1r11_run": str(source_d1r11_run),
        "source_r1a_output": str(source_r1a_output),
        "source_r1a_authentication": r1a,
        "source_r2_run": str(source_r2_run),
        "source_r3_initial_output": str(source_r3_initial_output),
        "source_r3_corrected_output": str(source_r3_corrected_output),
        "source_r3_r2_authentication": r3_r2,
        "source_r2_strict_parse_count": len(source_r2_results),
        "source_r2_identity_exact_count": source_r2_identity_count,
        "expected_task_count": 200,
        "strict_raw_parse_count": len(rows),
        "raw_pass_count": safety_pass_count,
        "safety_pass_count": safety_pass_count,
        "source_d1r13_inventory": source13_inventory,
        "source_d1r11_inventory": source11_inventory,
        "current_inventory": inventory,
        "snapshot_unique_count": len(snapshots),
        "snapshot_pass_count": sum(bool(row["passed"]) for row in snapshots.values()),
        "source_prefix_state_exact_count": sum(row["source_prefix_state_exact"] for row in rows),
        "source_prefix_trace_exact_count": sum(row["source_prefix_trace_exact"] for row in rows),
        "baseline_reproduction_count": sum(row["fresh_baseline_reproduces_d1r13"] for row in rows),
        "issue_exact_count": sum(row["issue_exact"] for row in rows),
        "cancel_exact_count": sum(row["cancel_exact"] for row in rows),
        "finite_row_count": sum(row["finite_coil_and_wire_records"] for row in rows),
        "runtime_or_environment_error_count": runtime_error_count,
        "prefix_failure_count": prefix_failure_count,
        "plant_failure_count": plant_failure_count,
        "action_safety_failure_count": action_safety_failure_count,
        "solver_error_count": sum(row["solver_error_count"] for row in rows),
        "saturation_or_clip_count": sum(row["saturation_or_clip_count"] for row in rows),
        "forbidden_trace_count": sum(row["forbidden_trace_count"] for row in rows),
        "maximum_current_utilization": max(
            (row["maximum_current_utilization"] for row in rows if row["maximum_current_utilization"] is not None),
            default=None,
        ),
        "formal_tracking_pass_count_diagnostic_only": int(
            final.get("formal_tracking_pass_count_diagnostic_only", -1)
        ),
        "response_geometry": geometry,
        "official_geometry_exact": geometry_match,
        "official_result_sha256": _sha256(stage / "analysis/final_result.json"),
        "stage_state_sha256": _sha256(stage / "stage_state.json"),
        "stage_manifest_sha256": _sha256(stage / "stage_manifest.json"),
        "package_hashes": package_hashes,
        "logs": log_rows,
        "snapshots": list(snapshots.values()),
        "rows": rows,
        "classification": {
            "runtime_or_environment_error": runtime_error_count > 0,
            "packaging_import_or_deployment_error": False,
            "raw_or_snapshot_corruption": any(not row["identity_exact"] for row in rows)
            or source_r2_identity_count != 72
            or any(not row["passed"] for row in snapshots.values()),
            "summary_or_reporting_error": not geometry_match,
            "plant_restart_failure": any(not row["source_prefix_state_exact"] for row in rows),
            "action_or_safety_failure": safety_pass_count < 200,
            "plant_execution_failure": plant_failure_count > 0,
            "geometry_design_failure": bool(geometry.get("evaluated"))
            and not bool(geometry.get("passed")),
            "sentinel_pass": independent_route
            == PASS_ROUTE,
            "real_mpc_or_control_success_established": False,
        },
        "scientific_boundary": {
            "formal_tracking_is_diagnostic_only": True,
            "time_distributed_identification_validated": independent_route == PASS_ROUTE,
            "transition_model_validated": False,
            "mpc_validated": False,
            "long_hold_validated": False,
            "expert_dataset_authorized": False,
            "bc_dagger_or_rl_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-d1r13-run", type=Path, required=True)
    parser.add_argument("--source-d1r11-run", type=Path, required=True)
    parser.add_argument("--source-r1a-output", type=Path, required=True)
    parser.add_argument("--source-r2-run", type=Path, required=True)
    parser.add_argument("--source-r3-initial-output", type=Path, required=True)
    parser.add_argument("--source-r3-corrected-output", type=Path, required=True)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--log", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(
        args.run_dir,
        args.source_d1r13_run,
        args.source_d1r11_run,
        args.source_r1a_output,
        args.source_r2_run,
        args.source_r3_initial_output,
        args.source_r3_corrected_output,
        args.project,
        args.log,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "sha256": _sha256(args.output),
                "passed": result["passed"],
                "raw_pass_count": result["raw_pass_count"],
                "formal_tracking_pass_count_diagnostic_only": result[
                    "formal_tracking_pass_count_diagnostic_only"
                ],
            },
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
