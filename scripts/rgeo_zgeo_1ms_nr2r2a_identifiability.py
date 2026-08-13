#!/usr/bin/env python3
"""Primary zero-fit NR2R2A identifiability audit."""

from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import inspect
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tsc_rzip_rllib.control import rgeo_zgeo_1ms_nr2_models as old_models  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr2_spec import (  # noqa: E402
    build_one_ms_nr2_specs,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_new(path: Path, payload: Any) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config["schema_version"] != "rgeo-zgeo-1ms-nr2r2a-identifiability-audit-v1":
        raise ValueError("unexpected NR2R2A schema")
    return config


def _inventory(path: Path) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for line in path.read_text(encoding="ascii").splitlines():
        name, digest = line.split(" ")
        if Path(name).name != name or len(digest) != 64:
            raise ValueError("invalid frozen inventory row")
        rows.append((name, digest))
    if len({name for name, _ in rows}) != len(rows):
        raise ValueError("duplicate frozen inventory filename")
    return rows


def _inventory_digest(rows: list[tuple[str, str]]) -> str:
    content = "".join(f"{name} {digest}\n" for name, digest in rows).encode("ascii")
    return hashlib.sha256(content).hexdigest()


def _finite_vector(value: Any, length: int, name: str) -> np.ndarray:
    result = np.asarray([float(item) for item in value], dtype=float)
    if result.shape != (length,) or not np.all(np.isfinite(result)):
        raise ValueError(f"invalid {name}")
    return result


def _load_records(config: dict[str, Any], records_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    inventory_path = ROOT / config["input_inventory"]
    rows = _inventory(inventory_path)
    if len(rows) != config["expected_files"]:
        raise ValueError("frozen inventory count mismatch")
    if _inventory_digest(rows) != config["expected_ordered_inventory_sha256"]:
        raise ValueError("frozen inventory identity mismatch")
    expected_names = {name for name, _ in rows}
    selected_names = {
        path.name
        for path in records_dir.glob("*.json")
        if path.name.startswith("development_") or path.name.startswith("calibration_")
    }
    if selected_names != expected_names:
        raise ValueError("selected compact-record inventory mismatch")
    specs = {spec.trajectory_id: spec.to_dict() for spec in build_one_ms_nr2_specs()}
    records: list[dict[str, Any]] = []
    total_bytes = 0
    for name, digest in rows:
        path = records_dir / name
        if not path.is_file() or _sha(path) != digest:
            raise ValueError(f"compact record hash mismatch: {name}")
        total_bytes += path.stat().st_size
        record = json.loads(path.read_text(encoding="utf-8"))
        spec = record.get("spec", {})
        trajectory_id = spec.get("trajectory_id")
        if spec.get("split") not in config["allowed_splits"] or spec.get("split") in config["forbidden_splits"]:
            raise ValueError("forbidden split selected")
        if trajectory_id not in specs or spec != specs[trajectory_id]:
            raise ValueError(f"embedded deterministic spec mismatch: {name}")
        if name != f"{trajectory_id}.json":
            raise ValueError("filename/spec identity mismatch")
        if record.get("schema_version") != "rgeo-zgeo-1ms-nr2r1-v1":
            raise ValueError("record schema/campaign mismatch")
        states, actions = record.get("states"), record.get("actions")
        if record.get("passed") is not True or record.get("plant_advances") != 16:
            raise ValueError("record did not complete the frozen campaign")
        if not isinstance(states, list) or len(states) != 17 or not isinstance(actions, list) or len(actions) != 16:
            raise ValueError("record shape mismatch")
        for index, state in enumerate(states):
            if state.get("time_ms") != config["takeover_time_ms"] + index:
                raise ValueError("state timing mismatch")
            for key in ("r_geo_m", "z_geo_m", "ip_a", "r_mid_m"):
                if not math.isfinite(float(state[key])):
                    raise ValueError(f"nonfinite state {key}")
            _finite_vector(state["actual_current_decimal_a_tsc"], 14, "actual current")
            _finite_vector(state["wire_current_a"], 48, "wire current")
            expected_side = "HFS" if float(state["r_geo_m"]) < float(state["r_mid_m"]) else "LFS"
            if state.get("side") != expected_side:
                raise ValueError("side label mismatch")
        for index, action in enumerate(actions):
            if action.get("issue_step") != index or action.get("issue_time_ms") != 1100 + index:
                raise ValueError("action timing mismatch")
            _finite_vector(action["command_delta_decimal_a_tsc"], 14, "issued increment")
            _finite_vector(action["target"]["current_a_tsc"], 14, "target current")
        records.append(record)
    if total_bytes != config["expected_bytes"]:
        raise ValueError("compact record byte count mismatch")
    return records, {
        "files": len(rows),
        "bytes": total_bytes,
        "ordered_inventory_sha256": _inventory_digest(rows),
        "holdout_records_read": 0,
        "campaign_identity_basis": "frozen_inventory_plus_record_schema_plus_deterministic_spec",
    }


def _ss_fraction(values: np.ndarray) -> float:
    overall = float(np.mean(values))
    between = values.shape[0] * float(np.sum((np.mean(values, axis=0) - overall) ** 2))
    total = float(np.sum((values - overall) ** 2))
    return between / total


def _matrix_table(sequences: np.ndarray, lag_lengths: list[int], scale: float) -> dict[str, Any]:
    table: dict[str, Any] = {}
    largest_full = 0
    for lag in lag_lengths:
        matrix = np.asarray(
            [sequence[end - lag + 1 : end + 1].reshape(-1) / scale for sequence in sequences for end in range(lag - 1, 16)],
            dtype=float,
        )
        singular = np.linalg.svd(matrix, compute_uv=False)
        tolerance = max(matrix.shape) * np.finfo(float).eps * float(singular[0]) if singular.size else 0.0
        rank = int(np.count_nonzero(singular > tolerance))
        full = rank == matrix.shape[1]
        if full:
            largest_full = lag
        retained_min = float(singular[rank - 1]) if rank else 0.0
        table[str(lag)] = {
            "rows": int(matrix.shape[0]),
            "columns": int(matrix.shape[1]),
            "rank": rank,
            "full_column_rank": full,
            "rank_tolerance": tolerance,
            "largest_singular_value": float(singular[0]) if singular.size else 0.0,
            "smallest_retained_singular_value": retained_min,
            "relative_smallest_retained_singular_value": retained_min / float(singular[0]) if rank else 0.0,
            "condition_number_if_full_column_rank": float(singular[0] / singular[-1]) if full else None,
        }
    return {"largest_full_column_rank_lag": largest_full, "by_lag": table}


def _action_geometry(records: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    all_q0 = 0
    max_offset = Decimal("0")
    max_increment = Decimal("0")
    cumulative_outside = False
    age_counts = {"zero": 0, "half": 0, "full": 0}
    for record in records:
        actions = record["actions"]
        q0 = tuple(Decimal(str(x)) for x in actions[0]["target"]["current_a_tsc"])
        offsets = []
        increments = []
        is_all_q0 = True
        for (amplitude, _), action in zip(record["spec"]["schedule"], actions):
            age_counts[amplitude] += 1
            target = tuple(Decimal(str(x)) for x in action["target"]["current_a_tsc"])
            offset = tuple(value - center for value, center in zip(target, q0))
            increment = tuple(Decimal(str(x)) for x in action["command_delta_decimal_a_tsc"])
            offsets.append([float(x) for x in offset])
            increments.append([float(x) for x in increment])
            max_offset = max(max_offset, *(abs(x) for x in offset))
            max_increment = max(max_increment, *(abs(x) for x in increment))
            is_all_q0 = is_all_q0 and all(x == 0 for x in offset)
            cumulative_outside = cumulative_outside or any(abs(x) > Decimal("0.3") for x in offset)
        all_q0 += int(is_all_q0)
        record["_audit_q0_offset"] = offsets
        record["_audit_issued_increment"] = increments
    for split in config["allowed_splits"]:
        selected = [record for record in records if record["spec"]["split"] == split]
        result[split] = {}
        for coordinate, key in (("issued_increment", "_audit_issued_increment"), ("q0_offset", "_audit_q0_offset")):
            result[split][coordinate] = _matrix_table(
                np.asarray([record[key] for record in selected], dtype=float),
                config["lag_lengths"],
                float(config["matrix_scale_a"]),
            )
    return {
        "lag_support": result,
        "full_horizon_all_q0_trajectories": all_q0,
        "maximum_absolute_q0_offset_a": float(max_offset),
        "maximum_absolute_issued_increment_a": float(max_increment),
        "cumulative_target_outside_q0_plus_or_minus_0p3_a": cumulative_outside,
        "target_amplitude_issue_counts": age_counts,
    }


def _pair_and_prefix_geometry(records: list[dict[str, Any]]) -> dict[str, Any]:
    pair_half = []
    groups: dict[tuple[str, int], dict[int, dict[str, Any]]] = {}
    for record in records:
        spec = record["spec"]
        groups.setdefault((spec["split"], spec["pair_index"]), {})[spec["sign"]] = record
    for mates in groups.values():
        plus, minus = mates[1], mates[-1]
        p = np.asarray([[s["r_geo_m"], s["z_geo_m"], s["ip_a"]] for s in plus["states"]], dtype=float)
        m = np.asarray([[s["r_geo_m"], s["z_geo_m"], s["ip_a"]] for s in minus["states"]], dtype=float)
        pair_half.append((p - m) / 2.0)
    maximum_half = np.max(np.abs(np.asarray(pair_half)), axis=(0, 1))
    step11 = []
    for record in records:
        if record["spec"]["schedule_type"] != "impulse":
            continue
        q0 = np.asarray(record["states"][1]["actual_current_decimal_a_tsc"], dtype=float)
        current = np.asarray(record["states"][11]["actual_current_decimal_a_tsc"], dtype=float)
        delta = np.asarray(record["actions"][11]["command_delta_decimal_a_tsc"], dtype=float)
        if np.array_equal(current, q0) and np.count_nonzero(delta) == 0:
            step11.append(record)
    state = np.asarray([[r["states"][11][k] for k in ("r_geo_m", "z_geo_m", "ip_a")] for r in step11], dtype=float)
    successor = np.asarray(
        [[r["states"][12][k] - r["states"][11][k] for k in ("r_geo_m", "z_geo_m", "ip_a")] for r in step11],
        dtype=float,
    )
    wires = np.asarray([r["states"][11]["wire_current_a"] for r in step11], dtype=float)
    return {
        "signed_pair_maximum_absolute_half_difference": {
            "r_geo_m": float(maximum_half[0]), "z_geo_m": float(maximum_half[1]), "ip_a": float(maximum_half[2])
        },
        "step_11_impulse_q0_zero_increment": {
            "paths": len(step11),
            "state_component_range": dict(zip(("r_geo_m", "z_geo_m", "ip_a"), np.ptp(state, axis=0).tolist())),
            "next_increment_component_range": dict(zip(("r_geo_m", "z_geo_m", "ip_a"), np.ptp(successor, axis=0).tolist())),
            "wire_current_maximum_component_range_a": float(np.max(np.ptp(wires, axis=0))),
        },
    }


def _state_geometry(records: list[dict[str, Any]]) -> dict[str, Any]:
    state = np.asarray(
        [[[s["r_geo_m"], s["z_geo_m"], s["ip_a"], s["r_mid_m"]] for s in r["states"]] for r in records],
        dtype=float,
    )
    time = np.asarray([[s["time_ms"] for s in r["states"]] for r in records], dtype=float)
    starts = {tuple(row[0, :3]) for row in state}
    flat = state.reshape(-1, 4)
    correlation = [float(np.corrcoef(time.reshape(-1), state[:, :, i].reshape(-1))[0, 1]) for i in range(3)]
    mean_endpoint = np.mean(state[:, -1, :3] - state[:, 0, :3], axis=0)
    side_counts = {side: sum(s["side"] == side for r in records for s in r["states"]) for side in ("HFS", "LFS")}
    return {
        "trajectories": len(records),
        "states": len(records) * 17,
        "unique_physical_starts": len(starts),
        "independent_position_anchors": 1,
        "side_counts": side_counts,
        "range": {
            "r_geo_m": {"minimum": float(np.min(flat[:, 0])), "maximum": float(np.max(flat[:, 0])), "span": float(np.ptp(flat[:, 0]))},
            "z_geo_m": {"minimum": float(np.min(flat[:, 1])), "maximum": float(np.max(flat[:, 1])), "span": float(np.ptp(flat[:, 1]))},
            "ip_a": {"minimum": float(np.min(flat[:, 2])), "maximum": float(np.max(flat[:, 2])), "span": float(np.ptp(flat[:, 2]))},
            "r_geo_minus_r_mid_m": {"minimum": float(np.min(flat[:, 0] - flat[:, 3])), "maximum": float(np.max(flat[:, 0] - flat[:, 3]))},
        },
        "mean_horizon_16_delta": dict(zip(("r_geo_m", "z_geo_m", "ip_a"), mean_endpoint.tolist())),
        "between_time_sum_of_squares_fraction": dict(zip(("r_geo", "z_geo", "ip"), [_ss_fraction(state[:, :, i]) for i in range(3)])),
        "pearson_correlation_with_time": dict(zip(("r_geo", "z_geo", "ip"), correlation)),
    }


def _source_representation() -> dict[str, Any]:
    train_path = ROOT / "scripts/rgeo_zgeo_1ms_nr2_train.py"
    module_path = ROOT / "tsc_rzip_rllib/control/rgeo_zgeo_1ms_nr2_models.py"
    model_source = inspect.getsource(old_models.history_feature)
    train_source = train_path.read_text(encoding="utf-8")
    module_source = module_path.read_text(encoding="utf-8")
    facts = {
        "arx_history_steps": old_models.HISTORY_STEPS,
        "short_history_repeats_first_frame": "selected.insert(0,selected[0])" in model_source.replace(" ", ""),
        "absolute_step_over_16_feature": "s/16.0" in train_source.replace(" ", ""),
        "explicit_stable_low_order_passive_innovation_state": any(token in module_source for token in ("spectral_radius", "innovation_state", "passive_state")),
        "train_source_sha256": _sha(train_path),
        "model_source_sha256": _sha(module_path),
    }
    if {key: facts[key] for key in (
        "arx_history_steps", "short_history_repeats_first_frame",
        "absolute_step_over_16_feature", "explicit_stable_low_order_passive_innovation_state",
    )} != {"arx_history_steps": 8, "short_history_repeats_first_frame": True,
           "absolute_step_over_16_feature": True,
           "explicit_stable_low_order_passive_innovation_state": False}:
        raise ValueError("NR2R1 source representation no longer matches the frozen audit premise")
    return facts


def audit(config_path: Path, records_dir: Path) -> dict[str, Any]:
    config = _load_config(config_path)
    records, authenticated = _load_records(config, records_dir)
    action = _action_geometry(records, config)
    result = {
        "schema_version": config["schema_version"],
        "stage_identity": config["schema_version"],
        "audit_complete": True,
        "route": config["routes"]["complete"],
        "input": authenticated,
        "state_geometry": _state_geometry(records),
        "action_geometry": action,
        "pair_and_prefix_geometry": _pair_and_prefix_geometry(records),
        "factorization_support": {
            "independent_all_q0_baseline": action["full_horizon_all_q0_trajectories"] > 0,
            "same_primitive_repeated_across_position_anchors": False,
            "matched_time_different_position": False,
            "matched_position_different_time_or_arrival_history": False,
            "position_time_history_effects_separable": False,
        },
        "source_representation": _source_representation(),
        "deployable_state_boundary": {
            "required": ["r_geo", "z_geo", "ip", "actual_14_coil_currents_tsc", "issued_quantized_applied_action", "queue_and_action_age", "time_since_1100_ms", "dt", "r_geo_minus_r_mid", "missing_masks"],
            "causal_belief_required": ["velocity_and_drift", "low_order_passive_and_innovation_memory", "calibrated_1100ms_initial_uncertainty"],
            "wire_current_48": "offline_diagnostic_or_auxiliary_only_until_deployment_interface_qualified",
            "forbidden": ["future_reference_in_dynamics", "source_or_history_id", "restart_hash", "outcome_label", "tsc_only_hidden_state"],
        },
        "counters": {"server_accesses": 0, "server_raw_reads": 0, "new_tsc_or_plant_advances": 0, "new_snapshots_or_replay_branches": 0, "model_fits_or_training_runs": 0, "holdout_records_read": 0, "controller_or_optimizer_executions": 0},
        "claim_boundary": "dataset_identifiability_and_state_representation_only_not_model_or_control_qualification",
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs/rgeo_zgeo_1ms_nr2r2a_identifiability_audit.json")
    parser.add_argument("--records-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit(args.config.resolve(), args.records_dir.resolve())
        _write_new(args.output.resolve(), result)
    except Exception as exc:
        print(json.dumps({"audit_complete": False, "route": "ONE_MS_NR2R2A_INPUT_AUDIT_FAIL_STOP", "error": f"{type(exc).__name__}: {exc}"}, indent=2))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
