#!/usr/bin/env python3
"""Independent raw reparse for ID-2F1 repeated-context development."""

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
from scripts.rgeo_zgeo_1ms_id2f1_repeated_context_development import (  # noqa: E402
    CONFIG_SHA256,
    SCHEMA as PRIMARY_SCHEMA,
    campaign_streams,
    load,
    route_for,
    write_new,
)


SCHEMA = "rgeo-zgeo-1ms-id2f1r1-repeated-context-independent-v1"


def _inside(path: Path, label: str) -> Path:
    result = path.resolve()
    try:
        result.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} leaves repository root") from exc
    return result


def _repeatability(left: dict[str, Any], right: dict[str, Any], stage: dict[str, Any]) -> dict[str, Any]:
    maxima = {"geometry_m": 0.0, "ip_a": 0.0, "coil_a": 0.0, "wire_a": 0.0}
    failures: list[str] = []
    if left["actions"] != right["actions"]:
        failures.append("ACTION_STREAM")
    if len(left["states"]) != len(right["states"]):
        failures.append("STATE_COUNT")
    for index, (a, b) in enumerate(zip(left["states"], right["states"])):
        if a["time_ms"] != b["time_ms"]:
            failures.append(f"TIME:{index}")
        maxima["geometry_m"] = max(maxima["geometry_m"],
                                    *(abs(float(a[key]) - float(b[key])) for key in ("r_geo_m", "z_geo_m", "r_mid_m")))
        maxima["ip_a"] = max(maxima["ip_a"], abs(float(a["ip_a"]) - float(b["ip_a"])))
        if len(a["actual_current_decimal_a_tsc"]) != 14 or len(b["actual_current_decimal_a_tsc"]) != 14:
            failures.append(f"COIL_COUNT:{index}")
        else:
            maxima["coil_a"] = max(maxima["coil_a"], max(
                abs(float(x) - float(y)) for x, y in zip(a["actual_current_decimal_a_tsc"], b["actual_current_decimal_a_tsc"])))
        if len(a["wire_current_a"]) != 48 or len(b["wire_current_a"]) != 48:
            failures.append(f"WIRE_COUNT:{index}")
        else:
            maxima["wire_a"] = max(maxima["wire_a"], max(
                abs(float(x) - float(y)) for x, y in zip(a["wire_current_a"], b["wire_current_a"])))
        for name in stage["semantic_artifacts"]:
            if a["artifact_sha256"].get(name) != b["artifact_sha256"].get(name):
                failures.append(f"SEMANTIC_ARTIFACT:{index}:{name}")
    for key, maximum in maxima.items():
        if maximum > stage["repeatability"][key]:
            failures.append(key.upper())
    return {"passed": not failures, "failures": list(dict.fromkeys(failures)),
            "maximum_absolute_difference": maxima}


def _lag_support(rows: Sequence[dict[str, Any]], lag_steps: int) -> dict[str, Any]:
    matrix_rows: list[list[float]] = []
    for row in rows:
        u = np.asarray([action["probe_virtual_action"] for action in row["actions"]], dtype=float)
        for issue in range(len(u)):
            feature: list[float] = []
            for lag in range(lag_steps):
                feature.extend(u[issue - lag].tolist() if issue >= lag else [0.0, 0.0])
            matrix_rows.append(feature)
    matrix = np.asarray(matrix_rows, dtype=float)
    singular = np.linalg.svd(matrix, compute_uv=False)
    return {"rows": int(matrix.shape[0]), "columns": int(matrix.shape[1]),
            "rank": int(np.linalg.matrix_rank(matrix)),
            "condition": float(singular[0] / singular[-1]) if singular.size and singular[-1] > 0 else math.inf,
            "minimum_singular_value": float(singular[-1]) if singular.size else 0.0}


def _metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any] | None:
    if len(rows) != stage["maximum_rollouts"] or not all(row["passed"] for row in rows):
        return None
    by_cell: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_cell.setdefault(row["cell_id"], []).append(row)
    pair_checks = []
    for cell_id, members in sorted(by_cell.items()):
        if len(members) != stage["replays_per_cell"]:
            return None
        pair_checks.append({"cell_id": cell_id, **_repeatability(members[0], members[1], stage)})
    baselines: dict[str, np.ndarray] = {}
    for context in (row["context_id"] for row in stage["contexts"]):
        members = [row for row in rows if row["context_id"] == context and row["cell_kind"] == "baseline"]
        values = np.asarray([[[state[key] for key in ("r_geo_m", "z_geo_m", "ip_a")]
                              for state in row["states"]] for row in members], dtype=float)
        baselines[context] = np.mean(values, axis=0)
    arms = []
    for cell_id, members in sorted(by_cell.items()):
        if members[0]["cell_kind"] == "baseline":
            continue
        context = members[0]["context_id"]
        values = np.mean(np.asarray([[[state[key] for key in ("r_geo_m", "z_geo_m", "ip_a")]
                                      for state in row["states"]] for row in members], dtype=float), axis=0)
        response = values - baselines[context]
        effect = int(members[0]["probe_issue_step"]) + 1
        window = response[effect:stage["horizon_steps"] + 1]
        norms = np.linalg.norm(window[:, :2], axis=1)
        peak = int(np.argmax(norms))
        arms.append({
            "cell_id": cell_id, "context_id": context,
            "direction_id": members[0]["direction_id"], "sign": members[0]["sign"],
            "probe_issue_step": members[0]["probe_issue_step"],
            "probe_duration_issues": members[0]["probe_duration_issues"],
            "effect_state_index": effect, "peak_state_index": effect + peak,
            "peak_rz_response_m": window[peak, :2].tolist(),
            "peak_rz_response_norm_m": float(norms[peak]),
            "maximum_absolute_ip_response_a": float(np.max(np.abs(window[:, 2]))),
            "terminal_rzi_response": response[-1].tolist(),
            "response_event_state_indices_ge_0p3mm": [effect + i for i, value in enumerate(norms) if value >= 0.0003],
            "complete_response": window.tolist(),
        })
    support = _lag_support(rows, int(stage["fit_eligibility_gates"]["lag_steps"]))
    gates = stage["fit_eligibility_gates"]
    families = []
    for direction in stage["probe_directions"]:
        for sign in stage["probe_signs"]:
            members = [row for row in arms if row["direction_id"] == direction and row["sign"] == sign]
            families.append({"direction_id": direction, "sign": sign,
                             "maximum_peak_rz_response_norm_m": max(row["peak_rz_response_norm_m"] for row in members),
                             "supported": any(row["peak_rz_response_norm_m"] >= gates["minimum_peak_rz_response_m_for_family_support"] for row in members)})
    gate_passes = {
        "repeatability": all(row["passed"] for row in pair_checks),
        "action_history_support": (support["rank"] == gates["required_lag_block_rank"]
                                   and support["condition"] <= gates["maximum_lag_block_condition"]),
        "signal_and_ip": (all(row["supported"] for row in families)
                          and all(row["maximum_absolute_ip_response_a"] <= gates["maximum_each_arm_absolute_ip_response_a"] for row in arms)),
    }
    return {"replay_pair_checks": pair_checks, "lag_support": support,
            "family_support": families, "arm_metrics": arms, "gate_passes": gate_passes}


def audit(stage_path: Path, run_dir: Path, destination: Path | None = None) -> dict[str, Any]:
    failures: list[str] = []
    stage_path = _inside(stage_path, "stage config")
    run_dir = _inside(run_dir, "run directory")
    if _sha(stage_path) != CONFIG_SHA256:
        failures.append("STAGE_SHA256")
    try:
        stage, cfg, targets, id2c1_stage = load(stage_path)
        streams = campaign_streams(stage, cfg, targets, id2c1_stage)
        order = {row["rollout_id"]: index for index, row in enumerate(streams)}
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
    compact_paths = sorted(path for path in run_dir.glob("*.json")
                           if path.name not in ("result.json", "offline_preflight.json")
                           and not path.name.startswith("independent_audit"))
    compact_rows = [json.loads(path.read_text(encoding="utf-8")) for path in compact_paths]
    if any(row.get("rollout_id") not in order for row in compact_rows):
        failures.append("UNKNOWN_COMPACT_ROLLOUT")
    compact_rows.sort(key=lambda row: order.get(row.get("rollout_id"), len(order)))
    if [row.get("rollout_id") for row in compact_rows] != [row["rollout_id"] for row in streams[:len(compact_rows)]]:
        failures.append("COMPACT_ROLLOUT_ORDER")
    rollout_root = run_dir / "rollouts"
    actual_ids = sorted(path.name for path in rollout_root.iterdir() if path.is_dir()) if rollout_root.is_dir() else []
    if actual_ids != sorted(row["rollout_id"] for row in compact_rows):
        failures.append("ROLLOUT_DIRECTORY_SET")
    raw_rows: list[dict[str, Any]] = []
    inventory_lines: list[str] = []
    inventory_bytes = 0
    if cfg is not None:
        for compact in compact_rows:
            rollout_id = compact["rollout_id"]
            folder = rollout_root / rollout_id
            times = [int(state["time_ms"]) for state in compact["states"]]
            actual_times = sorted(int(path.name[:-2]) for path in folder.iterdir()
                                  if path.is_dir() and path.name.endswith("ms"))
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
                for key, tolerance in (("r_geo_m", 1e-12), ("z_geo_m", 1e-12),
                                       ("r_mid_m", 1e-12), ("ip_a", 1e-9)):
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
            raw_rows.append({**{key: value for key, value in compact.items() if key not in ("states", "actions")},
                             "states": states, "actions": compact["actions"]})
    inventory_sha = hashlib.sha256("".join(f"{line}\n" for line in sorted(inventory_lines)).encode()).hexdigest()
    if inventory_sha != primary.get("required_artifact_inventory_sha256"):
        failures.append("INVENTORY_SHA256")
    if len(inventory_lines) != primary.get("required_artifact_files") or inventory_bytes != primary.get("required_artifact_bytes"):
        failures.append("INVENTORY_COUNT_OR_BYTES")
    raw_metrics = _metrics(raw_rows, stage)
    if _numeric_max_difference(raw_metrics, primary.get("development_metrics")) > 1e-12:
        failures.append("DEVELOPMENT_METRICS")
    counters = {"rollouts_completed": len(compact_rows),
                "unique_cells_completed": len({row.get("cell_id") for row in compact_rows}),
                "reset_calls": sum(row.get("reset_calls", 0) for row in compact_rows),
                "advance_attempts": sum(row.get("advance_attempts", 0) for row in compact_rows),
                "plant_advance_gotsc_calls": sum(row.get("plant_advance_gotsc_calls", 0) for row in compact_rows),
                "verified_plant_advances": sum(row.get("verified_plant_advances", 0) for row in compact_rows)}
    for key, value in counters.items():
        if value != primary.get(key):
            failures.append(f"COUNTER:{key}")
    raw_ok = not any(value.startswith(("RAW_STATE:", "MISSING_ARTIFACT:", "STATE_DIRECTORY_SET:")) for value in failures)
    expected_route = route_for(stage, raw_rows, raw_ok, raw_metrics)
    if primary.get("route") != expected_route:
        failures.append("PRIMARY_ROUTE")
    expected_pass = expected_route == stage["routes"]["pass"]
    if bool(primary.get("passed")) != expected_pass:
        failures.append("PRIMARY_VERDICT")
    result = {"schema_version": SCHEMA,
              "primary_sha256": _sha(primary_path) if primary_path.is_file() else None,
              "audit_passed": not failures, "failures": list(dict.fromkeys(failures)),
              "raw_rollouts": len(raw_rows), "raw_states": sum(len(row["states"]) for row in raw_rows),
              "recomputed_development_metrics": raw_metrics, "recomputed_counters": counters,
              "recomputed_inventory_sha256": inventory_sha,
              "model_fit_data_eligible": expected_pass and not failures,
              "id2c2_records_read": 0,
              "claim_boundary": "Independent raw reparse of finite ID2F1 repeated-context development; not calibration, holdout, controller or safety qualification."}
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
