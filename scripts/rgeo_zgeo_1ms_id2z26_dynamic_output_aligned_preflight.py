#!/usr/bin/env python3
"""Zero-TSC exact Card15 preflight for ID-2Z26."""

from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_id2z24_centered_coallocation_preflight as z24  # noqa: E402


CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z26_dynamic_output_aligned_preflight.json"
CONFIG_SHA256 = "a9b4aec984c7aa23dc0437cf806f0222d9e76c8699eac9c0406a9639fd8a1283"
SCHEMA = "rgeo-zgeo-1ms-id2z26-dynamic-output-aligned-preflight-result-v1"


def _error(message: str) -> ValueError:
    return ValueError(f"ID2Z26: {message}")


def _inside(path: Path, label: str) -> Path:
    value = path.resolve()
    try:
        value.relative_to(ROOT)
    except ValueError as exc:
        raise _error(f"{label} escapes repository") from exc
    return value


def _sha(path: Path) -> str:
    return hashlib.sha256(_inside(path, "hash path").read_bytes()).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(_inside(path, "JSON path").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise _error(f"JSON object required: {path}")
    return value


def _require(stage: dict[str, Any]) -> None:
    if _sha(CONFIG) != CONFIG_SHA256:
        raise _error("config hash mismatch")
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2z26-dynamic-output-aligned-preflight-v1",
        "identity": "rgeo-zgeo-1ms-id2z26-dynamic-output-aligned-preflight-v1",
        "stage": "ID-2Z26", "takeover_time_ms": 1100,
        "control_period_ms": 1, "models_fit_or_updated": 0,
        "maximum_tsc_calls": 0, "maximum_plant_advances": 0,
        "calibration_or_holdout_reads": 0, "common_horizon_steps": 73,
        "common_terminal_state_index": 73,
        "exact_full_f_prefix_last_issue": 31,
        "transition_center_first_issue": 32,
        "transition_center_last_issue": 55,
        "held_tail_first_issue": 56, "held_tail_last_issue": 72,
        "nominal_share": "0.50", "phase_issue_steps": [32, 40],
        "same_sign_duration_issues": 8, "opposite_sign_return_issues": 8,
        "maximum_prospective_rollouts": 11,
        "maximum_prospective_reset_calls": 11,
        "maximum_prospective_advance_attempts": 803,
        "maximum_prospective_gotsc_calls": 803,
        "maximum_prospective_verified_plant_advances": 803,
        "maximum_prospective_retained_states": 814,
        "required_artifact_files_if_all_complete": 4070,
        "retry_after_any_advance_attempt": "forbidden",
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise _error(f"frozen field mismatch: {key}")
    if [(row.get("axis_id"), row.get("formula"))
            for row in stage.get("output_aligned_axes", [])] != [
                ("q_r", "0.5*(r5-r6)"), ("q_z", "0.5*(r5+r6)")]:
        raise _error("output-aligned axis formulas changed")
    if len(stage.get("prospective_rollout_ids", [])) != 11:
        raise _error("prospective rollout matrix changed")


def _evidence(stage: dict[str, Any]) -> dict[str, dict[str, Any]]:
    values: dict[str, dict[str, Any]] = {}
    for name, spec in stage["evidence"].items():
        path = _inside(ROOT / spec["path"], f"evidence {name}")
        if _sha(path) != spec["sha256"]:
            raise _error(f"evidence hash mismatch: {name}")
        if path.suffix == ".json":
            values[name] = _read(path)
    z24e, z25e = values["id2z24r2_compact"], values["id2z25_compact"]
    if (z24e.get("route") != stage["evidence"]["id2z24r2_compact"]["required_route"]
            or z24e.get("passed") is not True
            or z24e.get("independent_audit_passed") is not True):
        raise _error("ID2Z24R2 source identity mismatch")
    if (z25e.get("route") != stage["evidence"]["id2z25_compact"]["required_route"]
            or z25e.get("passed") is not False
            or z25e.get("independent_audit_passed") is not True
            or z25e.get("branch_signal_passed") != 10
            or z25e.get("branch_signal_total") != 12):
        raise _error("ID2Z25 final identity mismatch")
    return values


def _scaled(values: Sequence[Decimal], scale: Decimal) -> tuple[Decimal, ...]:
    return tuple(scale * value for value in values)


def _combine(left: Sequence[Decimal], right: Sequence[Decimal], sign: int) -> tuple[Decimal, ...]:
    return tuple(a + Decimal(sign) * b for a, b in zip(left, right))


def _axis_seeds(evidence: dict[str, dict[str, Any]]) -> tuple[tuple[Decimal, ...], dict[str, tuple[Decimal, ...]]]:
    f = z24._field_delta(evidence["baseline_full_f"], 24)
    nominal = _scaled(f, Decimal("0.50"))
    r5 = z24._field_delta(evidence["issue24_p05_plus"], 24)
    r6 = _scaled(z24._field_delta(evidence["issue24_p06_plus"], 24), Decimal("0.50"))
    axes = {
        "q_r": _scaled(_combine(r5, r6, -1), Decimal("0.50")),
        "q_z": _scaled(_combine(r5, r6, 1), Decimal("0.50")),
    }
    return nominal, axes


def _build_center(baseline: dict[str, Any], nominal: Sequence[Decimal],
                  horizon: int = 73) -> list[tuple[str, ...]]:
    fields = [tuple(row["expected_card15_fields"]) for row in baseline["actions"][:32]]
    current = fields[-1]
    for issue in range(32, horizon):
        if issue <= 55:
            current = z24._combined_step(current, nominal)
        fields.append(current)
    return fields


def _build_full_f(baseline: dict[str, Any], nominal_f: Sequence[Decimal],
                  horizon: int = 73) -> list[tuple[str, ...]]:
    fields = [tuple(row["expected_card15_fields"]) for row in baseline["actions"][:32]]
    current = fields[-1]
    for issue in range(32, horizon):
        if issue <= 55:
            current = z24._combined_step(current, nominal_f)
        fields.append(current)
    return fields


def _build_branch(center: Sequence[tuple[str, ...]], nominal: Sequence[Decimal],
                  axis: Sequence[Decimal], phase: int, first_sign: int) -> list[tuple[str, ...]]:
    fields = list(center[:phase])
    current = fields[-1]
    for issue in range(phase, len(center)):
        if issue <= 55:
            sign = 0
            if phase <= issue < phase + 8:
                sign = first_sign
            elif phase + 8 <= issue < phase + 16:
                sign = -first_sign
            delta = nominal if sign == 0 else _combine(nominal, axis, sign)
            current = z24._combined_step(current, delta)
        fields.append(current)
    return fields


def _metrics(fields: Sequence[Sequence[str]], turns: Sequence[Decimal],
             lower: np.ndarray, upper: np.ndarray) -> dict[str, Any]:
    currents = [z24._currents(row, turns) for row in fields]
    slews = [float(np.max(np.abs(currents[i] - currents[i - 1])))
             for i in range(1, len(currents))]
    headroom = [float(np.min(np.minimum(row - lower, upper - row))) for row in currents]
    return {
        "maximum_issued_delta_a": max(slews),
        "minimum_absolute_current_headroom_a": min(headroom),
        "terminal_card15_fields": list(fields[-1]),
    }


def execute(config: Path = CONFIG, source_revision: str = "UNKNOWN") -> dict[str, Any]:
    config = _inside(config, "config")
    if config != CONFIG.resolve():
        raise _error("alternate config forbidden")
    stage = _read(config)
    _require(stage)
    evidence = _evidence(stage)
    base = evidence["base_tsc_config"]
    turns = tuple(Decimal(str(value)) for value in base["turns_display_order"])
    lower = np.asarray(base["min_current_a_display_order"], dtype=float)
    upper = np.asarray(base["max_current_a_display_order"], dtype=float)
    baseline = evidence["baseline_full_f"]
    full_f = z24._field_delta(baseline, 24)
    nominal, axes = _axis_seeds(evidence)
    center = _build_center(baseline, nominal)
    full = _build_full_f(baseline, full_f)
    gate = stage["static_gates"]
    failures: list[str] = []
    local_rows: list[dict[str, Any]] = []
    for issue in range(32, 56):
        previous = center[issue - 1]
        columns: list[np.ndarray] = []
        maximum = 0.0
        headroom = math.inf
        for axis in axes.values():
            plus = z24._combined_step(previous, _combine(nominal, axis, 1))
            minus = z24._combined_step(previous, _combine(nominal, axis, -1))
            plus_delta = z24._currents(plus, turns) - z24._currents(previous, turns)
            minus_delta = z24._currents(minus, turns) - z24._currents(previous, turns)
            columns.append((plus_delta - minus_delta) / 2.0)
            maximum = max(maximum, float(np.max(np.abs(plus_delta))),
                          float(np.max(np.abs(minus_delta))))
            headroom = min(headroom, z24._headroom(plus, turns, lower, upper),
                           z24._headroom(minus, turns, lower, upper))
        matrix = np.column_stack(columns)
        singular = np.linalg.svd(matrix, compute_uv=False)
        tolerance = gate["structural_svd_relative_tolerance"] * float(singular[0])
        rank = int(np.sum(singular > tolerance))
        condition = float(singular[0] / singular[1]) if rank == 2 else math.inf
        passed = (rank == gate["required_output_aligned_input_rank"]
                  and condition <= gate["maximum_output_aligned_input_condition"]
                  and maximum <= gate["maximum_absolute_issued_delta_a"]
                  and headroom >= gate["minimum_absolute_current_headroom_a"])
        local_rows.append({"issue": issue, "rank": rank, "condition": condition,
                           "maximum_signed_issued_delta_a": maximum,
                           "minimum_signed_target_headroom_a": headroom,
                           "passed": bool(passed)})
        if not passed:
            failures.append(f"LOCAL_VERTEX:{issue}")
    streams: list[dict[str, Any]] = []
    streams.append({"rollout_id": "baseline_transition_center",
                    "card15_targets": [list(row) for row in center],
                    "prefix_exact": True, "closure_exact": True,
                    **_metrics(center, turns, lower, upper)})
    streams.append({"rollout_id": "diagnostic_baseline_full_f",
                    "card15_targets": [list(row) for row in full],
                    "prefix_exact": True, "closure_exact": True,
                    **_metrics(full, turns, lower, upper)})
    for phase in stage["phase_issue_steps"]:
        for axis_id, axis in axes.items():
            for first_sign, label in ((1, "plus_then_minus"), (-1, "minus_then_plus")):
                branch = _build_branch(center, nominal, axis, int(phase), first_sign)
                close_issue = int(phase) + 15
                prefix_exact = branch[:int(phase)] == center[:int(phase)]
                closure_exact = branch[close_issue] == center[close_issue]
                row = {"rollout_id": f"issue{phase}__{axis_id}__{label}",
                       "card15_targets": [list(value) for value in branch],
                       "prefix_exact": prefix_exact, "closure_exact": closure_exact,
                       "closure_issue": close_issue,
                       **_metrics(branch, turns, lower, upper)}
                streams.append(row)
                if (not prefix_exact or not closure_exact
                        or row["maximum_issued_delta_a"] > gate["maximum_absolute_issued_delta_a"]
                        or row["minimum_absolute_current_headroom_a"] < gate["minimum_absolute_current_headroom_a"]):
                    failures.append(f"STREAM:{row['rollout_id']}")
    replay_source = next(row for row in streams
                         if row["rollout_id"] == "issue32__q_z__plus_then_minus")
    streams.append({**replay_source,
                    "rollout_id": "replay_issue32__q_z__plus_then_minus"})
    if [row["rollout_id"] for row in streams] != stage["prospective_rollout_ids"]:
        failures.append("ROLLOUT_ORDER")
    if any(not row["passed"] for row in local_rows):
        route = stage["routes"]["exact_lattice_fail"]
    elif failures:
        route = stage["routes"]["static_stream_fail"]
    else:
        route = stage["routes"]["pass"]
    return {
        "schema_version": SCHEMA, "source_revision": source_revision,
        "stage_config_sha256": _sha(config), "route": route,
        "passed": not failures, "failures": failures,
        "models_fit_or_updated": 0, "tsc_calls": 0, "plant_advances": 0,
        "calibration_or_holdout_reads": 0,
        "nominal_field_increment": [str(value) for value in nominal],
        "output_aligned_field_increments": {
            key: [str(value) for value in axis] for key, axis in axes.items()},
        "local_vertex_checks": local_rows,
        "prospective_static_streams": streams,
        "prospective_budget": {
            "rollouts": stage["maximum_prospective_rollouts"],
            "advance_attempts": stage["maximum_prospective_advance_attempts"],
            "retained_states": stage["maximum_prospective_retained_states"],
            "required_artifact_files": stage["required_artifact_files_if_all_complete"],
        },
        "claim_boundary": stage["claim_boundary"],
    }


def _write_new(path: Path, value: dict[str, Any]) -> None:
    output = _inside(path, "output")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = execute(args.config, args.source_revision)
    except Exception as exc:
        stage = _read(args.config)
        result = {"schema_version": SCHEMA, "source_revision": args.source_revision,
                  "stage_config_sha256": _sha(args.config),
                  "route": stage["routes"]["input_or_attribution_fail"],
                  "passed": False, "failures": [f"{type(exc).__name__}:{exc}"],
                  "models_fit_or_updated": 0, "tsc_calls": 0, "plant_advances": 0,
                  "calibration_or_holdout_reads": 0}
    _write_new(args.output, result)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
