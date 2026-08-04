#!/usr/bin/env python3
"""Independent server raw/snapshot audit for Stage4.2R3c3T13S24D1R14."""

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


STAGE = "Stage4.2R3c3T13S24D1R14"
RUN_NAME = "stage4_2r3c3t13s24d1r14_zero_baseline_signed_excitation_sentinel"
SOURCE_D1R13_NAME = "stage4_2r3c3t13s24d1r13_zero_increment_deconfounding_sentinel"
SOURCE_D1R11_NAME = (
    "stage4_2r3c3t13s24d1r11_full_replacement_sequential_transition_identification"
)
CAMPAIGN_IDENTITY = "zero_baseline_signed_excitation_safety_geometry_sentinel_v1"
CONTROLLER_REVISION = "zero_baseline_signed_excitation_v42r3c3t13s24d1r14_v2"
N_COILS = 14
PREFIX_END = 10
ISSUE_STEP = 10
CANCEL_STEP = 11
ZERO_AFTER = 12
DIRECTIONS = (
    "mode0_without_coil8",
    "mode0_coil8_component",
    "mode1",
    "mode2",
)
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
    "r3c3t13s24d1r14_future_r17_executed",
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
    specs: Sequence[Mapping[str, Any]], results: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    by_context: dict[str, dict[tuple[str, int, int], Mapping[str, Any]]] = {}
    spec_by_id = {str(spec["experiment_id"]): spec for spec in specs}
    for experiment_id, result in results.items():
        spec = spec_by_id[experiment_id]
        key = (
            str(spec["d1r14_role"]),
            int(spec["d1r14_direction_index"]),
            int(spec["d1r14_sign"]),
        )
        by_context.setdefault(str(spec["source_d1r13_experiment_id"]), {})[key] = result
    pair_rows = []
    context_rows = []
    odd_bank: dict[tuple[str, int], np.ndarray] = {}
    for context_id, group in sorted(by_context.items()):
        baseline = _visible(group[("baseline", -1, 0)]["trajectory"])[11:]
        columns = []
        direction_passes = []
        for direction, name in enumerate(DIRECTIONS):
            positive = _visible(group[("signed_probe", direction, 1)]["trajectory"])[11:]
            negative = _visible(group[("signed_probe", direction, -1)]["trajectory"])[11:]
            odd = 0.5 * (positive - negative)
            even = 0.5 * (positive + negative) - baseline
            odd_peak = float(np.max(np.abs(odd)))
            even_peak = float(np.max(np.abs(even)))
            ratio = even_peak / odd_peak if odd_peak > 0.0 else None
            signal = odd_peak >= 0.005 - 1e-15
            symmetry = ratio is not None and ratio <= 0.5 + 1e-12
            column = odd.reshape(-1)
            norm = float(np.linalg.norm(column))
            columns.append(column / norm if norm > 0.0 else np.full(column.shape, math.nan))
            direction_passes.append(signal and symmetry)
            odd_bank[(context_id, direction)] = odd
            pair_rows.append(
                {
                    "source_d1r13_experiment_id": context_id,
                    "direction_index": direction,
                    "direction_name": name,
                    "odd_peak_normalized_outputs5": odd_peak,
                    "even_peak_normalized_outputs5": even_peak,
                    "even_to_odd_peak_ratio": ratio,
                    "signal_pass": signal,
                    "symmetry_pass": symmetry,
                    "passed": signal and symmetry,
                }
            )
        matrix = np.column_stack(columns)
        finite = bool(np.all(np.isfinite(matrix)))
        singular = np.linalg.svd(matrix, compute_uv=False) if finite else np.full(4, math.nan)
        rank = int(np.sum(singular > singular[0] * 1e-10)) if finite and singular[0] > 0 else 0
        condition = float(singular[0] / singular[-1]) if rank == 4 and singular[-1] > 0 else None
        source_spec = next(
            spec for spec in specs if str(spec["source_d1r13_experiment_id"]) == context_id
        )
        context_rows.append(
            {
                "source_d1r13_experiment_id": context_id,
                "pair_id": source_spec["pair_id"],
                "history_member": source_spec["history_member"],
                "singular_values": [
                    float(value) if math.isfinite(float(value)) else None for value in singular
                ],
                "rank": rank,
                "condition_number": condition,
                "passed": bool(
                    all(direction_passes)
                    and rank == 4
                    and condition is not None
                    and condition <= 20.0 + 1e-12
                ),
            }
        )
    history_rows = []
    pair_contexts: dict[str, list[str]] = {}
    for row in context_rows:
        pair_contexts.setdefault(str(row["pair_id"]), []).append(
            str(row["source_d1r13_experiment_id"])
        )
    for pair_id, contexts in sorted(pair_contexts.items()):
        for direction, name in enumerate(DIRECTIONS):
            left = odd_bank[(contexts[0], direction)]
            right = odd_bank[(contexts[1], direction)]
            difference = float(np.max(np.abs(left - right)))
            peak = max(float(np.max(np.abs(left))), float(np.max(np.abs(right))))
            history_rows.append(
                {
                    "pair_id": pair_id,
                    "direction_index": direction,
                    "direction_name": name,
                    "maximum_absolute_odd_difference": difference,
                    "relative_to_pair_odd_peak": difference / peak if peak > 0 else None,
                    "report_only": True,
                }
            )
    ratio_values = [row["even_to_odd_peak_ratio"] for row in pair_rows if row["even_to_odd_peak_ratio"] is not None]
    condition_values = [row["condition_number"] for row in context_rows if row["condition_number"] is not None]
    return {
        "evaluated": True,
        "signed_pair_count": len(pair_rows),
        "signal_pass_count": sum(bool(row["signal_pass"]) for row in pair_rows),
        "symmetry_pass_count": sum(bool(row["symmetry_pass"]) for row in pair_rows),
        "rank_pass_count": sum(int(row["rank"]) == 4 for row in context_rows),
        "condition_pass_count": sum(
            row["condition_number"] is not None and row["condition_number"] <= 20.0 + 1e-12
            for row in context_rows
        ),
        "minimum_odd_peak_normalized_outputs5": min(
            (row["odd_peak_normalized_outputs5"] for row in pair_rows), default=0.0
        ),
        "maximum_even_to_odd_peak_ratio": max(ratio_values, default=None),
        "maximum_condition_number": max(condition_values, default=None),
        "pair_rows": pair_rows,
        "context_rows": context_rows,
        "matched_hidden_history_rows_report_only": history_rows,
        "passed": bool(
            len(pair_rows) == 32
            and all(row["passed"] for row in pair_rows)
            and len(context_rows) == 8
            and all(row["passed"] for row in context_rows)
        ),
    }


def audit(
    run_dir: Path,
    source_d1r13_run: Path,
    source_d1r11_run: Path,
    project: Path,
    logs: Sequence[Path],
) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    source_d1r13_run = source_d1r13_run.resolve()
    source_d1r11_run = source_d1r11_run.resolve()
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
        role = str(spec["d1r14_role"])
        baseline_reproduction = issue_exact = cancel_exact = False
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
            direction = int(spec["d1r14_direction_index"])
            issue = trace[10].get("r3c3t13s24d1r14_event_detail") or {}
            cancel = trace[11].get("r3c3t13s24d1r14_event_detail") or {}
            issue_exact = bool(
                _event_passes(issue, expected_name="sequential_issue", slot=direction, task_step=10)
                and list(map(float, issue.get("requested_coordinate") or []))
                == list(map(float, spec["d1r14_requested_coordinate"]))
            )
            cancel_exact = bool(
                _event_passes(cancel, expected_name="sequential_cancel", slot=direction, task_step=11)
                and cancel.get("stored_center_card15_fields") == issue.get("center_card15_fields")
            )
            zero_actions = all(
                list(map(float, row.get("action_norm_tsc") or [])) == [0.0] * 14
                for row in trace[12:]
            )
            zero_currents = all(currents[index + 1] == currents[index] for index in range(12, horizon))
            role_pass = issue_exact and cancel_exact and zero_actions and zero_currents
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
    geometry = _geometry(specs, results) if len(rows) == 72 and safety_pass_count == 72 else {"evaluated": False, "passed": False, "reason": "safety_or_prefix_gate_failed"}
    log_rows = _log_audit(logs)
    official_geometry = final.get("response_geometry") or {}
    geometry_match = bool(
        geometry.get("evaluated") == official_geometry.get("evaluated")
        and geometry.get("passed") == official_geometry.get("passed")
        and geometry.get("signal_pass_count") == official_geometry.get("signal_pass_count")
        and geometry.get("symmetry_pass_count") == official_geometry.get("symmetry_pass_count")
        and geometry.get("rank_pass_count") == official_geometry.get("rank_pass_count")
        and geometry.get("condition_pass_count") == official_geometry.get("condition_pass_count")
        and _optional_close(
            geometry.get("minimum_odd_peak_normalized_outputs5"),
            official_geometry.get("minimum_odd_peak_normalized_outputs5"),
        )
        and _optional_close(
            geometry.get("maximum_even_to_odd_peak_ratio"),
            official_geometry.get("maximum_even_to_odd_peak_ratio"),
        )
        and _optional_close(
            geometry.get("maximum_condition_number"),
            official_geometry.get("maximum_condition_number"),
        )
    )
    if runtime_error_count > 0 or prefix_failure_count > 0 or inventory["count"] != 72:
        independent_route = "ZERO_BASELINE_EXCITATION_RUNTIME_OR_PREFIX_FAIL_STOP"
    elif safety_pass_count != 72:
        independent_route = "ZERO_BASELINE_EXCITATION_SAFETY_FAIL_REDESIGN_REQUIRED"
    elif not geometry.get("passed"):
        independent_route = "ZERO_BASELINE_EXCITATION_GEOMETRY_FAIL_REDESIGN_REQUIRED"
    else:
        independent_route = "ZERO_BASELINE_EXCITATION_SENTINEL_PASS_TIME_DISTRIBUTED_ID_DESIGN_REQUIRED"
    official_route_reproduced = bool(
        final.get("route") == independent_route
        and bool(final.get("passed"))
        == (independent_route == "ZERO_BASELINE_EXCITATION_SENTINEL_PASS_TIME_DISTRIBUTED_ID_DESIGN_REQUIRED")
        and int(final.get("safety_pass_count", -1)) == safety_pass_count
        and int(final.get("runtime_error_count", -1)) == runtime_error_count
        and int(final.get("prefix_failure_count", -1)) == prefix_failure_count
    )
    audit_completed = bool(
        len(specs) == 72
        and len({row["experiment_id"] for row in specs}) == 72
        and _digest(specs) == str(manifest["spec_digest"])
        and source13_inventory["count"] == D1R13_COUNT
        and source13_inventory["bytes"] == D1R13_BYTES
        and source13_inventory["digest"] == D1R13_DIGEST
        and source11_inventory["count"] == D1R11_COUNT
        and source11_inventory["bytes"] == D1R11_BYTES
        and source11_inventory["digest"] == D1R11_DIGEST
        and inventory["count"] == 72
        and len(rows) == 72
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
        and int(state.get("new_raw_count", -1)) == 72
    )
    package_hashes = {
        name: _sha256(project / name)
        for name in (
            "PACKAGE_MANIFEST.json",
            "SHA256SUMS",
            "configs/stage4_2r3c3t13s24d1r14_zero_baseline_signed_excitation_sentinel_370ms.json",
            "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14_zero_baseline_signed_excitation_sentinel.py",
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
        "expected_task_count": 72,
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
            or any(not row["passed"] for row in snapshots.values()),
            "summary_or_reporting_error": not geometry_match,
            "plant_restart_failure": any(not row["source_prefix_state_exact"] for row in rows),
            "action_or_safety_failure": safety_pass_count < 72,
            "plant_execution_failure": plant_failure_count > 0,
            "geometry_design_failure": bool(geometry.get("evaluated"))
            and not bool(geometry.get("passed")),
            "sentinel_pass": independent_route
            == "ZERO_BASELINE_EXCITATION_SENTINEL_PASS_TIME_DISTRIBUTED_ID_DESIGN_REQUIRED",
            "real_mpc_or_control_success_established": False,
        },
        "scientific_boundary": {
            "formal_tracking_is_diagnostic_only": True,
            "time_distributed_identification_validated": False,
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
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--log", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(
        args.run_dir,
        args.source_d1r13_run,
        args.source_d1r11_run,
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
