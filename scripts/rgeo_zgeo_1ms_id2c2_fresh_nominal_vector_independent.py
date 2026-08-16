#!/usr/bin/env python3
"""Independent raw reparse for ID-2C2 fresh nominal/vector validation."""

from __future__ import annotations

import argparse
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

from scripts.rgeo_zgeo_1ms_id0_vector_tail_independent import ARTIFACTS, _fields, _sha, _state  # noqa: E402
from scripts.rgeo_zgeo_1ms_id1a_context_anchor_pilot_independent import _numeric_max_difference  # noqa: E402
from scripts.rgeo_zgeo_1ms_id2c2_fresh_nominal_vector_validation import (  # noqa: E402
    CONFIG_SHA256,
    SCHEMA as PRIMARY_SCHEMA,
    load,
    write_new,
)


SCHEMA = "rgeo-zgeo-1ms-id2c2-fresh-nominal-vector-independent-v1"


def _inside(path: Path, label: str) -> Path:
    result = path.resolve()
    try:
        result.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} leaves repository root") from exc
    return result


def _campaign_order(stage: dict[str, Any]) -> dict[str, int]:
    rollout_ids = [
        f"{cell['cell_id']}_r{replay}"
        for cell in stage["cells_in_order"]
        for replay in range(stage["replays_per_cell"])
    ]
    return {rollout_id: index for index, rollout_id in enumerate(rollout_ids)}


def _angular_gap(vectors: Sequence[Sequence[float]]) -> float:
    angles = sorted(math.degrees(math.atan2(float(v[1]), float(v[0]))) % 360.0 for v in vectors)
    return max(b - a for a, b in zip(angles, angles[1:] + [angles[0] + 360.0]))


def _compare_pair(left: dict[str, Any], right: dict[str, Any], stage: dict[str, Any]) -> dict[str, Any]:
    maxima = {"geometry_m": 0.0, "ip_a": 0.0, "coil_a": 0.0, "wire_a": 0.0}
    failures: list[str] = []
    if left["actions"] != right["actions"]:
        failures.append("ACTION_STREAM")
    if len(left["states"]) != len(right["states"]):
        failures.append("STATE_COUNT")
    for index, (a, b) in enumerate(zip(left["states"], right["states"])):
        if a["time_ms"] != b["time_ms"]:
            failures.append(f"TIME:{index}")
        maxima["geometry_m"] = max(maxima["geometry_m"], *(abs(float(a[key]) - float(b[key])) for key in ("r_geo_m", "z_geo_m", "r_mid_m")))
        maxima["ip_a"] = max(maxima["ip_a"], abs(float(a["ip_a"]) - float(b["ip_a"])))
        if len(a["actual_current_decimal_a_tsc"]) != 14 or len(b["actual_current_decimal_a_tsc"]) != 14:
            failures.append(f"COIL_COUNT:{index}")
        else:
            maxima["coil_a"] = max(maxima["coil_a"], max(abs(float(x) - float(y)) for x, y in zip(a["actual_current_decimal_a_tsc"], b["actual_current_decimal_a_tsc"])))
        if len(a["wire_current_a"]) != 48 or len(b["wire_current_a"]) != 48:
            failures.append(f"WIRE_COUNT:{index}")
        else:
            maxima["wire_a"] = max(maxima["wire_a"], max(abs(float(x) - float(y)) for x, y in zip(a["wire_current_a"], b["wire_current_a"])))
        for name in stage["semantic_artifacts"]:
            if a["artifact_sha256"].get(name) != b["artifact_sha256"].get(name):
                failures.append(f"SEMANTIC_ARTIFACT:{index}:{name}")
    for key, maximum in maxima.items():
        if maximum > stage["repeatability"][key]:
            failures.append(key.upper())
    return {"cell_id": left["cell_id"], "passed": not failures, "failures": list(dict.fromkeys(failures)), "maximum_absolute_difference": maxima}


def _replay_metrics(rows: Sequence[dict[str, Any]], replay_index: int) -> dict[str, Any]:
    subset = {row["cell_id"]: row for row in rows if row["replay_index"] == replay_index}
    q0 = subset["fresh_q0_baseline"]
    nominal = subset["p03_minus_stride1_nominal"]
    source = q0["states"][0]
    q0_terminal = q0["states"][-1]
    nominal_terminal = nominal["states"][-1]
    q0_norm = math.hypot(q0_terminal["r_geo_m"] - source["r_geo_m"], q0_terminal["z_geo_m"] - source["z_geo_m"])
    nominal_norm = math.hypot(nominal_terminal["r_geo_m"] - source["r_geo_m"], nominal_terminal["z_geo_m"] - source["z_geo_m"])
    nominal_metrics = {
        "q0_terminal_source_rz_norm_m": q0_norm,
        "nominal_terminal_source_rz_norm_m": nominal_norm,
        "terminal_rz_norm_reduction_fraction_vs_matched_q0": 1.0 - nominal_norm / q0_norm,
        "maximum_absolute_nominal_ip_from_source_a": max(abs(state["ip_a"] - source["ip_a"]) for state in nominal["states"]),
    }
    baseline = subset["selected_nominal_probe_baseline"]
    base = np.asarray([[s["r_geo_m"], s["z_geo_m"], s["ip_a"]] for s in baseline["states"]], dtype=float)
    arm_metrics = []
    vectors = []
    ordered_cells = [
        "selected_nominal_p04_plus", "selected_nominal_p04_minus",
        "selected_nominal_p07_plus", "selected_nominal_p07_minus",
        "selected_nominal_p09_half_exact_center_plus", "selected_nominal_p09_half_exact_center_minus",
    ]
    for cell in ordered_cells:
        row = subset[cell]
        values = np.asarray([[s["r_geo_m"], s["z_geo_m"], s["ip_a"]] for s in row["states"]], dtype=float)
        response = values - base
        window = response[17:33]
        norms = np.linalg.norm(window[:, :2], axis=1)
        peak_offset = int(np.argmax(norms))
        peak = window[peak_offset, :2]
        peak_norm = float(norms[peak_offset])
        terminal_norm = float(norms[-1])
        vectors.append(peak)
        arm_metrics.append({
            "cell_id": cell,
            "direction_id": row["direction_id"],
            "sign": row["sign"],
            "peak_state_index": 17 + peak_offset,
            "peak_rz_response_m": peak.tolist(),
            "peak_rz_response_norm_m": peak_norm,
            "maximum_absolute_ip_response_a": float(np.max(np.abs(window[:, 2]))),
            "terminal_rz_response_norm_m": terminal_norm,
            "terminal_to_peak_rz_ratio": terminal_norm / peak_norm if peak_norm else math.inf,
            "terminal_rzi_response": response[-1].tolist(),
        })
    matrix = np.asarray(vectors, dtype=float).T
    conditions = []
    for left in range(6):
        for right in range(left + 1, 6):
            pair = matrix[:, [left, right]]
            if np.linalg.matrix_rank(pair) == 2:
                conditions.append(float(np.linalg.cond(pair)))
    pairs = []
    for direction in ("p04", "p07", "p09_half_exact_center"):
        plus = next(row for row in arm_metrics if row["direction_id"] == direction and row["sign"] == "plus")
        minus = next(row for row in arm_metrics if row["direction_id"] == direction and row["sign"] == "minus")
        p = np.asarray(plus["peak_rz_response_m"], dtype=float)
        m = np.asarray(minus["peak_rz_response_m"], dtype=float)
        pn = float(np.linalg.norm(p))
        mn = float(np.linalg.norm(m))
        pairs.append({"direction_id": direction, "plus_minus_peak_vector_cosine": float(np.dot(p, m) / (pn * mn)), "plus_over_minus_peak_norm_ratio": pn / mn})
    return {
        "replay_index": replay_index,
        "nominal_metrics": nominal_metrics,
        "arm_metrics": arm_metrics,
        "direction_pair_metrics": pairs,
        "peak_rz_rank": int(np.linalg.matrix_rank(matrix)),
        "best_pair_condition": min(conditions) if conditions else math.inf,
        "circular_maximum_angular_gap_deg": _angular_gap(vectors),
        "positive_span_claim_scope": "finite_one_issue_return_peak_response_rays_only",
        "p09_pooled_as_smooth_gain": False,
    }


def _metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any] | None:
    if len(rows) != 18 or not all(row["passed"] for row in rows):
        return None
    replay_metrics = [_replay_metrics(rows, replay) for replay in range(2)]
    repeatability = []
    for cell in stage["cells_in_order"]:
        pair = sorted((row for row in rows if row["cell_id"] == cell["cell_id"]), key=lambda row: row["replay_index"])
        repeatability.append(_compare_pair(pair[0], pair[1], stage))
    gates = stage["scientific_gates"]
    return {
        "replay_metrics": replay_metrics,
        "repeatability": repeatability,
        "gate_passes": {
            "repeatability": len(repeatability) == 9 and all(row["passed"] for row in repeatability),
            "nominal_authority": all(
                row["nominal_metrics"]["terminal_rz_norm_reduction_fraction_vs_matched_q0"] >= gates["minimum_terminal_rz_norm_reduction_fraction_vs_matched_q0"]
                and row["nominal_metrics"]["maximum_absolute_nominal_ip_from_source_a"] <= gates["maximum_absolute_nominal_ip_from_source_a"]
                for row in replay_metrics
            ),
            "residual_signal_and_ip": all(
                arm["peak_rz_response_norm_m"] >= gates["minimum_each_arm_peak_rz_response_m"]
                and arm["maximum_absolute_ip_response_a"] <= gates["maximum_each_arm_absolute_ip_response_a"]
                for row in replay_metrics for arm in row["arm_metrics"]
            ),
            "residual_tail": all(
                arm["terminal_to_peak_rz_ratio"] <= gates["maximum_each_arm_terminal_to_peak_rz_ratio"]
                for row in replay_metrics for arm in row["arm_metrics"]
            ),
            "two_sided_vector_geometry": all(
                row["peak_rz_rank"] == gates["required_peak_rz_rank"]
                and row["best_pair_condition"] <= gates["maximum_best_pair_condition"]
                and row["circular_maximum_angular_gap_deg"] <= gates["maximum_circular_angular_gap_deg"]
                and all(
                    pair["plus_minus_peak_vector_cosine"] <= gates["maximum_plus_minus_peak_vector_cosine"]
                    and gates["minimum_plus_minus_peak_norm_ratio"] <= pair["plus_over_minus_peak_norm_ratio"] <= gates["maximum_plus_minus_peak_norm_ratio"]
                    for pair in row["direction_pair_metrics"]
                )
                for row in replay_metrics
            ),
        },
    }


def audit(stage_path: Path, run_dir: Path, destination: Path | None = None) -> dict[str, Any]:
    failures: list[str] = []
    stage_path = _inside(stage_path, "stage config")
    run_dir = _inside(run_dir, "run directory")
    if _sha(stage_path) != CONFIG_SHA256:
        failures.append("STAGE_SHA256")
    try:
        stage, cfg, _, _, _ = load(stage_path)
    except Exception as exc:
        failures.append(f"STAGE_LOAD:{type(exc).__name__}:{exc}")
        stage = json.loads(stage_path.read_text(encoding="utf-8"))
        cfg = None
    primary_path = run_dir / "result.json"
    primary = json.loads(primary_path.read_text(encoding="utf-8")) if primary_path.is_file() else {}
    if primary.get("schema_version") != PRIMARY_SCHEMA:
        failures.append("PRIMARY_SCHEMA")
    compact_paths = sorted(path for path in run_dir.glob("*.json") if path.name not in ("result.json", "offline_preflight.json") and not path.name.startswith("independent_audit"))
    compact_rows = [json.loads(path.read_text(encoding="utf-8")) for path in compact_paths]
    order = _campaign_order(stage)
    if any(row.get("rollout_id") not in order for row in compact_rows):
        failures.append("UNKNOWN_COMPACT_ROLLOUT")
    compact_rows.sort(key=lambda row: order.get(row.get("rollout_id"), len(order)))
    actual_ids = sorted(path.name for path in (run_dir / "rollouts").iterdir() if path.is_dir()) if (run_dir / "rollouts").is_dir() else []
    expected_ids = sorted(row["rollout_id"] for row in compact_rows)
    if actual_ids != expected_ids:
        failures.append("ROLLOUT_DIRECTORY_SET")
    raw_rows = []
    inventory_lines = []
    inventory_bytes = 0
    if cfg is not None:
        for compact in compact_rows:
            rollout_id = compact["rollout_id"]
            folder = run_dir / "rollouts" / rollout_id
            times = [int(state["time_ms"]) for state in compact["states"]]
            actual_times = sorted(int(path.name[:-2]) for path in folder.iterdir() if path.is_dir() and path.name.endswith("ms"))
            if actual_times != times:
                failures.append(f"STATE_DIRECTORY_SET:{rollout_id}")
                continue
            states = []
            for index, time_ms in enumerate(times):
                state_folder = folder / f"{time_ms}ms"
                try:
                    state = _state(state_folder, cfg)
                    states.append(state)
                except Exception as exc:
                    failures.append(f"RAW_STATE:{rollout_id}:{time_ms}:{type(exc).__name__}:{exc}")
                    continue
                expected = compact["states"][index]
                for key, tolerance in (("r_geo_m", 1e-12), ("z_geo_m", 1e-12), ("r_mid_m", 1e-12), ("ip_a", 1e-9)):
                    if abs(float(state[key]) - float(expected[key])) > tolerance:
                        failures.append(f"STATE_VALUE:{rollout_id}:{time_ms}:{key}")
                if len(state["actual_current_decimal_a_tsc"]) != 14 or len(state["wire_current_a"]) != 48:
                    failures.append(f"STATE_VECTOR_LENGTH:{rollout_id}:{time_ms}")
                for name in ARTIFACTS:
                    path = state_folder / name
                    if not path.is_file():
                        failures.append(f"MISSING_ARTIFACT:{rollout_id}:{time_ms}:{name}")
                        continue
                    size = path.stat().st_size
                    label = path.relative_to(run_dir).as_posix()
                    inventory_lines.append(f"{label}\t{size}\t{_sha(path)}")
                    inventory_bytes += size
            for issue, action in enumerate(compact["actions"]):
                try:
                    observed = list(_fields(folder / f"{1100 + issue}ms" / "inputa"))
                    if observed != action["expected_card15_fields"]:
                        failures.append(f"ISSUED_CARD15:{rollout_id}:{issue}")
                except Exception as exc:
                    failures.append(f"INPUTA:{rollout_id}:{issue}:{type(exc).__name__}:{exc}")
            raw_rows.append({**{key: value for key, value in compact.items() if key not in ("states", "actions")}, "states": states, "actions": compact["actions"]})
    payload = "".join(f"{line}\n" for line in sorted(inventory_lines)).encode()
    inventory_sha = hashlib.sha256(payload).hexdigest()
    if inventory_sha != primary.get("required_artifact_inventory_sha256"):
        failures.append("INVENTORY_SHA256")
    if len(inventory_lines) != primary.get("required_artifact_files") or inventory_bytes != primary.get("required_artifact_bytes"):
        failures.append("INVENTORY_COUNT_OR_BYTES")
    raw_metrics = _metrics(raw_rows, stage)
    if _numeric_max_difference(raw_metrics, primary.get("validation_metrics")) > 1e-12:
        failures.append("VALIDATION_METRICS")
    counters = {
        "rollouts_completed": len(compact_rows),
        "reset_calls": sum(row.get("reset_calls", 0) for row in compact_rows),
        "advance_attempts": sum(row.get("advance_attempts", 0) for row in compact_rows),
        "plant_advance_gotsc_calls": sum(row.get("plant_advance_gotsc_calls", 0) for row in compact_rows),
        "verified_plant_advances": sum(row.get("verified_plant_advances", 0) for row in compact_rows),
    }
    for key, value in counters.items():
        if value != primary.get(key):
            failures.append(f"COUNTER:{key}")
    expected_pass = raw_metrics is not None and all(raw_metrics["gate_passes"].values())
    if expected_pass != bool(primary.get("passed")):
        failures.append("PRIMARY_VERDICT")
    if expected_pass and primary.get("route") != stage["routes"]["pass"]:
        failures.append("PRIMARY_ROUTE")
    result = {
        "schema_version": SCHEMA,
        "primary_sha256": _sha(primary_path) if primary_path.is_file() else None,
        "audit_passed": not failures,
        "failures": list(dict.fromkeys(failures)),
        "raw_rollouts": len(raw_rows),
        "raw_states": sum(len(row["states"]) for row in raw_rows),
        "recomputed_validation_metrics": raw_metrics,
        "recomputed_counters": counters,
        "recomputed_inventory_sha256": inventory_sha,
        "claim_boundary": "Independent raw reparse of finite fresh empirical validation; not fit, calibration, holdout, tube, controller or safety qualification.",
    }
    if destination is not None:
        write_new(_inside(destination, "independent output"), result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.stage_config, args.run_dir, args.output)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
