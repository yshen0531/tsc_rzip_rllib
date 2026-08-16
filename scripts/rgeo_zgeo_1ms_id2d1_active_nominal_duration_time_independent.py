#!/usr/bin/env python3
"""Independent raw reparse for ID-2D1 duration/time development."""

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
from scripts.rgeo_zgeo_1ms_id2d1_active_nominal_duration_time_development import (  # noqa: E402
    CONFIG_SHA256,
    SCHEMA as PRIMARY_SCHEMA,
    campaign_streams,
    load,
    write_new,
)


SCHEMA = "rgeo-zgeo-1ms-id2d1-active-nominal-duration-time-independent-v1"


def _inside(path: Path, label: str) -> Path:
    result = path.resolve()
    try:
        result.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} leaves repository root") from exc
    return result


def _order(stage: dict[str, Any], cfg: Any, targets: dict[str, Any], id2c1_stage: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    streams = campaign_streams(stage, cfg, targets, id2c1_stage)
    return streams, {row["rollout_id"]: index for index, row in enumerate(streams)}


def _repeatability(left: dict[str, Any], right: dict[str, Any], stage: dict[str, Any]) -> dict[str, Any]:
    maxima = {"geometry_m": 0.0, "ip_a": 0.0, "coil_a": 0.0, "wire_a": 0.0}
    failures = []
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
        if maximum > stage["baseline_repeatability"][key]:
            failures.append(key.upper())
    return {"passed": not failures, "failures": list(dict.fromkeys(failures)), "maximum_absolute_difference": maxima}


def _lag_support(rows: Sequence[dict[str, Any]], lag_steps: int) -> dict[str, Any]:
    matrix_rows = []
    for row in rows:
        u = np.asarray([action["probe_virtual_action"] for action in row["actions"]], dtype=float)
        for issue in range(len(u)):
            feature = []
            for lag in range(lag_steps):
                feature.extend(u[issue - lag].tolist() if issue >= lag else [0.0, 0.0, 0.0])
            matrix_rows.append(feature)
    matrix = np.asarray(matrix_rows, dtype=float)
    singular = np.linalg.svd(matrix, compute_uv=False)
    return {
        "rows": int(matrix.shape[0]),
        "columns": int(matrix.shape[1]),
        "rank": int(np.linalg.matrix_rank(matrix)),
        "condition": float(singular[0] / singular[-1]) if singular.size and singular[-1] > 0 else math.inf,
        "minimum_singular_value": float(singular[-1]) if singular.size else 0.0,
    }


def _metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any] | None:
    if len(rows) != 24 or not all(row["passed"] for row in rows):
        return None
    baselines = [row for row in rows if row["cell_kind"] == "baseline"]
    repeatability = _repeatability(baselines[0], baselines[1], stage)
    base = np.mean(np.asarray([[[state[key] for key in ("r_geo_m", "z_geo_m", "ip_a")] for state in row["states"]] for row in baselines], dtype=float), axis=0)
    arms = []
    for row in rows:
        if row["cell_kind"] == "baseline":
            continue
        values = np.asarray([[state[key] for key in ("r_geo_m", "z_geo_m", "ip_a")] for state in row["states"]], dtype=float)
        response = values - base
        effect = int(row["probe_issue_step"]) + 1
        window = response[effect:33]
        norms = np.linalg.norm(window[:, :2], axis=1)
        peak = int(np.argmax(norms))
        arms.append({
            "cell_id": row["cell_id"],
            "cell_kind": row["cell_kind"],
            "direction_id": row["direction_id"],
            "sign": row["sign"],
            "probe_issue_step": row["probe_issue_step"],
            "probe_duration_issues": row["probe_duration_issues"],
            "effect_state_index": effect,
            "peak_state_index": effect + peak,
            "peak_rz_response_m": window[peak, :2].tolist(),
            "peak_rz_response_norm_m": float(norms[peak]),
            "maximum_absolute_ip_response_a": float(np.max(np.abs(window[:, 2]))),
            "terminal_rzi_response": response[-1].tolist(),
            "terminal_to_peak_rz_ratio": float(norms[-1] / norms[peak]) if norms[peak] else math.inf,
            "complete_response": response[effect:33].tolist(),
        })
    support = _lag_support(rows, int(stage["fit_eligibility_gates"]["lag_steps"]))
    gates = stage["fit_eligibility_gates"]
    smooth = [row for row in arms if row["cell_kind"] == "smooth_residual"]
    event = [row for row in arms if row["cell_kind"] == "event_residual"]
    gate_passes = {
        "baseline_repeatability": repeatability["passed"],
        "virtual_lag_support": support["rank"] == gates["required_lag_block_rank"],
        "response_signal_and_ip": all(
            row["peak_rz_response_norm_m"] >= gates["minimum_each_smooth_arm_peak_rz_response_m"]
            and row["maximum_absolute_ip_response_a"] <= gates["maximum_each_smooth_arm_absolute_ip_response_a"]
            for row in smooth
        ) and all(
            row["peak_rz_response_norm_m"] >= gates["minimum_each_event_arm_peak_rz_response_m"]
            and row["maximum_absolute_ip_response_a"] <= gates["maximum_each_event_arm_absolute_ip_response_a"]
            for row in event
        ),
    }
    return {"baseline_repeatability": repeatability, "lag_support": support, "arm_metrics": arms, "gate_passes": gate_passes}


def audit(stage_path: Path, run_dir: Path, destination: Path | None = None) -> dict[str, Any]:
    failures: list[str] = []
    stage_path = _inside(stage_path, "stage config")
    run_dir = _inside(run_dir, "run directory")
    if _sha(stage_path) != CONFIG_SHA256:
        failures.append("STAGE_SHA256")
    try:
        stage, cfg, targets, id2c1_stage = load(stage_path)
        streams, order = _order(stage, cfg, targets, id2c1_stage)
    except Exception as exc:
        failures.append(f"STAGE_LOAD:{type(exc).__name__}:{exc}")
        stage = json.loads(stage_path.read_text(encoding="utf-8"))
        cfg = None
        streams = []
        order = {}
    primary_path = run_dir / "result.json"
    primary = json.loads(primary_path.read_text(encoding="utf-8")) if primary_path.is_file() else {}
    if primary.get("schema_version") != PRIMARY_SCHEMA:
        failures.append("PRIMARY_SCHEMA")
    compact_paths = sorted(path for path in run_dir.glob("*.json") if path.name not in ("result.json", "offline_preflight.json") and not path.name.startswith("independent_audit"))
    compact_rows = [json.loads(path.read_text(encoding="utf-8")) for path in compact_paths]
    if any(row.get("rollout_id") not in order for row in compact_rows):
        failures.append("UNKNOWN_COMPACT_ROLLOUT")
    compact_rows.sort(key=lambda row: order.get(row.get("rollout_id"), len(order)))
    expected_ids = [row["rollout_id"] for row in streams[:len(compact_rows)]]
    if [row.get("rollout_id") for row in compact_rows] != expected_ids:
        failures.append("COMPACT_ROLLOUT_ORDER")
    actual_ids = sorted(path.name for path in (run_dir / "rollouts").iterdir() if path.is_dir()) if (run_dir / "rollouts").is_dir() else []
    if actual_ids != sorted(row["rollout_id"] for row in compact_rows):
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
                    inventory_lines.append(f"{path.relative_to(run_dir).as_posix()}\t{size}\t{_sha(path)}")
                    inventory_bytes += size
            for issue, action in enumerate(compact["actions"]):
                try:
                    if list(_fields(folder / f"{1100 + issue}ms" / "inputa")) != action["expected_card15_fields"]:
                        failures.append(f"ISSUED_CARD15:{rollout_id}:{issue}")
                except Exception as exc:
                    failures.append(f"INPUTA:{rollout_id}:{issue}:{type(exc).__name__}:{exc}")
            raw_rows.append({**{key: value for key, value in compact.items() if key not in ("states", "actions")}, "states": states, "actions": compact["actions"]})
    inventory_sha = hashlib.sha256("".join(f"{line}\n" for line in sorted(inventory_lines)).encode()).hexdigest()
    if inventory_sha != primary.get("required_artifact_inventory_sha256"):
        failures.append("INVENTORY_SHA256")
    if len(inventory_lines) != primary.get("required_artifact_files") or inventory_bytes != primary.get("required_artifact_bytes"):
        failures.append("INVENTORY_COUNT_OR_BYTES")
    raw_metrics = _metrics(raw_rows, stage)
    if _numeric_max_difference(raw_metrics, primary.get("development_metrics")) > 1e-12:
        failures.append("DEVELOPMENT_METRICS")
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
        "recomputed_development_metrics": raw_metrics,
        "recomputed_counters": counters,
        "recomputed_inventory_sha256": inventory_sha,
        "model_fit_data_eligible": expected_pass and not failures,
        "claim_boundary": "Independent raw reparse of finite source-local duration/time development; not calibration, holdout, tube, controller or safety qualification.",
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
