#!/usr/bin/env python3
"""Structurally separate NR2R2A scalar and lag-rank recomputation."""

from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr2_spec import build_one_ms_nr2_specs  # noqa: E402


def digest(path: Path) -> str:
    block = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            block.update(chunk)
    return block.hexdigest()


def save_exclusive(path: Path, value: Any) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def read_inputs(config: dict[str, Any], folder: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    listed = []
    for text in (ROOT / config["input_inventory"]).read_text(encoding="ascii").splitlines():
        filename, expected = text.split(" ")
        listed.append((filename, expected))
    inventory_bytes = "".join(f"{name} {sha}\n" for name, sha in listed).encode("ascii")
    identity = hashlib.sha256(inventory_bytes).hexdigest()
    if identity != config["expected_ordered_inventory_sha256"] or len(listed) != 28:
        raise RuntimeError("independent frozen inventory mismatch")
    seen = {path.name for path in folder.glob("*.json") if path.name.startswith(("development_", "calibration_"))}
    if seen != {name for name, _ in listed}:
        raise RuntimeError("independent selected inventory mismatch")
    frozen_specs = {item.trajectory_id: item.to_dict() for item in build_one_ms_nr2_specs()}
    data = []
    byte_count = 0
    for filename, expected in listed:
        source = folder / filename
        if digest(source) != expected:
            raise RuntimeError(f"independent hash mismatch: {filename}")
        byte_count += source.stat().st_size
        value = json.loads(source.read_text(encoding="utf-8"))
        spec = value["spec"]
        if spec["split"] not in ("development", "calibration") or filename != spec["trajectory_id"] + ".json":
            raise RuntimeError("independent split/filename mismatch")
        if frozen_specs.get(spec["trajectory_id"]) != spec:
            raise RuntimeError("independent deterministic spec mismatch")
        if value.get("schema_version") != "rgeo-zgeo-1ms-nr2r1-v1" or value.get("passed") is not True:
            raise RuntimeError("independent record identity mismatch")
        if value.get("plant_advances") != 16 or len(value["states"]) != 17 or len(value["actions"]) != 16:
            raise RuntimeError("independent record shape mismatch")
        for step, state in enumerate(value["states"]):
            if state["time_ms"] != 1100 + step:
                raise RuntimeError("independent state timing mismatch")
            numbers = [state[k] for k in ("r_geo_m", "z_geo_m", "ip_a", "r_mid_m")]
            if not all(math.isfinite(float(x)) for x in numbers) or len(state["actual_current_decimal_a_tsc"]) != 14 or len(state["wire_current_a"]) != 48:
                raise RuntimeError("independent state field mismatch")
            if not all(math.isfinite(float(x)) for x in state["actual_current_decimal_a_tsc"] + state["wire_current_a"]):
                raise RuntimeError("independent nonfinite current field")
            if state["side"] != ("HFS" if state["r_geo_m"] < state["r_mid_m"] else "LFS"):
                raise RuntimeError("independent side mismatch")
        for step, action in enumerate(value["actions"]):
            if action["issue_step"] != step or action["issue_time_ms"] != 1100 + step:
                raise RuntimeError("independent action timing mismatch")
            if len(action["command_delta_decimal_a_tsc"]) != 14 or len(action["target"]["current_a_tsc"]) != 14:
                raise RuntimeError("independent action field mismatch")
            if not all(math.isfinite(float(x)) for x in action["command_delta_decimal_a_tsc"] + action["target"]["current_a_tsc"]):
                raise RuntimeError("independent nonfinite action field")
        data.append(value)
    if byte_count != config["expected_bytes"]:
        raise RuntimeError("independent byte count mismatch")
    return data, {
        "files": len(data), "bytes": byte_count, "ordered_inventory_sha256": identity,
        "holdout_records_read": 0,
        "campaign_identity_basis": "frozen_inventory_plus_record_schema_plus_deterministic_spec",
    }


def time_fraction(cube: np.ndarray) -> float:
    center = np.sum(cube) / cube.size
    per_step = np.sum(cube, axis=0) / cube.shape[0]
    numerator = cube.shape[0] * np.sum((per_step - center) ** 2)
    denominator = np.sum((cube - center) ** 2)
    return float(numerator / denominator)


def states_result(data: list[dict[str, Any]]) -> dict[str, Any]:
    cube = np.array([[[x["r_geo_m"], x["z_geo_m"], x["ip_a"], x["r_mid_m"]] for x in item["states"]] for item in data], dtype=np.float64)
    flat = cube.reshape((-1, 4))
    clocks = np.tile(np.arange(1100, 1117), cube.shape[0])
    change = np.sum(cube[:, 16, :3] - cube[:, 0, :3], axis=0) / cube.shape[0]
    names = ("r_geo", "z_geo", "ip")
    return {
        "trajectories": cube.shape[0], "states": cube.shape[0] * cube.shape[1],
        "unique_physical_starts": len({tuple(row) for row in cube[:, 0, :3]}),
        "independent_position_anchors": 1,
        "side_counts": {side: sum(x["side"] == side for item in data for x in item["states"]) for side in ("HFS", "LFS")},
        "range": {
            "r_geo_m": {"minimum": float(flat[:, 0].min()), "maximum": float(flat[:, 0].max()), "span": float(np.ptp(flat[:, 0]))},
            "z_geo_m": {"minimum": float(flat[:, 1].min()), "maximum": float(flat[:, 1].max()), "span": float(np.ptp(flat[:, 1]))},
            "ip_a": {"minimum": float(flat[:, 2].min()), "maximum": float(flat[:, 2].max()), "span": float(np.ptp(flat[:, 2]))},
            "r_geo_minus_r_mid_m": {"minimum": float(np.min(flat[:, 0] - flat[:, 3])), "maximum": float(np.max(flat[:, 0] - flat[:, 3]))},
        },
        "mean_horizon_16_delta": {"r_geo_m": float(change[0]), "z_geo_m": float(change[1]), "ip_a": float(change[2])},
        "between_time_sum_of_squares_fraction": {name: time_fraction(cube[:, :, index]) for index, name in enumerate(names)},
        "pearson_correlation_with_time": {name: float(np.corrcoef(clocks, cube[:, :, index].reshape(-1))[0, 1]) for index, name in enumerate(names)},
    }


def lag_rows(sequences: list[list[list[float]]], lag: int, divisor: float) -> dict[str, Any]:
    material = []
    for sequence in sequences:
        for terminal in range(lag - 1, 16):
            material.append(np.array(sequence[terminal - lag + 1 : terminal + 1], dtype=np.float64).ravel() / divisor)
    matrix = np.stack(material, axis=0)
    values = np.linalg.svd(matrix, full_matrices=False, compute_uv=False)
    cutoff = max(matrix.shape) * np.finfo(np.float64).eps * values[0]
    active = values[values > cutoff]
    rank = int(active.size)
    complete = rank == matrix.shape[1]
    return {
        "rows": matrix.shape[0], "columns": matrix.shape[1], "rank": rank,
        "full_column_rank": complete, "rank_tolerance": float(cutoff),
        "largest_singular_value": float(values[0]),
        "smallest_retained_singular_value": float(active[-1]) if active.size else 0.0,
        "relative_smallest_retained_singular_value": float(active[-1] / values[0]) if active.size else 0.0,
        "condition_number_if_full_column_rank": float(values[0] / values[-1]) if complete else None,
    }


def actions_result(data: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    streams: dict[str, dict[str, list[list[list[float]]]]] = {
        split: {"issued_increment": [], "q0_offset": []} for split in config["allowed_splits"]
    }
    all_zero = 0
    maximum_offset = Decimal(0)
    maximum_increment = Decimal(0)
    outside = False
    counts = {"zero": 0, "half": 0, "full": 0}
    for item in data:
        split = item["spec"]["split"]
        q0 = [Decimal(str(x)) for x in item["actions"][0]["target"]["current_a_tsc"]]
        target_stream = []
        increment_stream = []
        trajectory_zero = True
        for schedule, action in zip(item["spec"]["schedule"], item["actions"]):
            counts[schedule[0]] += 1
            target = [Decimal(str(x)) for x in action["target"]["current_a_tsc"]]
            offset = [x - y for x, y in zip(target, q0)]
            increment = [Decimal(str(x)) for x in action["command_delta_decimal_a_tsc"]]
            target_stream.append([float(x) for x in offset])
            increment_stream.append([float(x) for x in increment])
            maximum_offset = max([maximum_offset] + [abs(x) for x in offset])
            maximum_increment = max([maximum_increment] + [abs(x) for x in increment])
            trajectory_zero = trajectory_zero and not any(offset)
            outside = outside or any(abs(x) > Decimal("0.3") for x in offset)
        all_zero += int(trajectory_zero)
        streams[split]["issued_increment"].append(increment_stream)
        streams[split]["q0_offset"].append(target_stream)
    lag_support = {}
    for split, coordinates in streams.items():
        lag_support[split] = {}
        for name, sequence in coordinates.items():
            table = {str(lag): lag_rows(sequence, lag, config["matrix_scale_a"]) for lag in config["lag_lengths"]}
            full = [int(lag) for lag, row in table.items() if row["full_column_rank"]]
            lag_support[split][name] = {"largest_full_column_rank_lag": max(full, default=0), "by_lag": table}
    return {
        "lag_support": lag_support, "full_horizon_all_q0_trajectories": all_zero,
        "maximum_absolute_q0_offset_a": float(maximum_offset),
        "maximum_absolute_issued_increment_a": float(maximum_increment),
        "cumulative_target_outside_q0_plus_or_minus_0p3_a": outside,
        "target_amplitude_issue_counts": counts,
    }


def pair_result(data: list[dict[str, Any]]) -> dict[str, Any]:
    members: dict[tuple[str, int], dict[int, dict[str, Any]]] = {}
    for item in data:
        spec = item["spec"]
        members.setdefault((spec["split"], spec["pair_index"]), {})[spec["sign"]] = item
    halves = []
    for pair in members.values():
        plus = np.array([[x[k] for k in ("r_geo_m", "z_geo_m", "ip_a")] for x in pair[1]["states"]])
        minus = np.array([[x[k] for k in ("r_geo_m", "z_geo_m", "ip_a")] for x in pair[-1]["states"]])
        halves.append((plus - minus) * 0.5)
    maxima = np.max(np.abs(np.stack(halves)), axis=(0, 1))
    eligible = []
    for item in data:
        if item["spec"]["schedule_type"] != "impulse":
            continue
        q0 = [Decimal(str(x)) for x in item["states"][1]["actual_current_decimal_a_tsc"]]
        current = [Decimal(str(x)) for x in item["states"][11]["actual_current_decimal_a_tsc"]]
        issued = [Decimal(str(x)) for x in item["actions"][11]["command_delta_decimal_a_tsc"]]
        if current == q0 and not any(issued):
            eligible.append(item)
    now = np.array([[x["states"][11][k] for k in ("r_geo_m", "z_geo_m", "ip_a")] for x in eligible])
    future = np.array([[x["states"][12][k] - x["states"][11][k] for k in ("r_geo_m", "z_geo_m", "ip_a")] for x in eligible])
    wire = np.array([x["states"][11]["wire_current_a"] for x in eligible])
    return {
        "signed_pair_maximum_absolute_half_difference": {"r_geo_m": float(maxima[0]), "z_geo_m": float(maxima[1]), "ip_a": float(maxima[2])},
        "step_11_impulse_q0_zero_increment": {
            "paths": len(eligible),
            "state_component_range": {k: float(v) for k, v in zip(("r_geo_m", "z_geo_m", "ip_a"), np.ptp(now, axis=0))},
            "next_increment_component_range": {k: float(v) for k, v in zip(("r_geo_m", "z_geo_m", "ip_a"), np.ptp(future, axis=0))},
            "wire_current_maximum_component_range_a": float(np.max(np.ptp(wire, axis=0))),
        },
    }


def source_result() -> dict[str, Any]:
    train_path = ROOT / "scripts/rgeo_zgeo_1ms_nr2_train.py"
    model_path = ROOT / "tsc_rzip_rllib/control/rgeo_zgeo_1ms_nr2_models.py"
    train = train_path.read_text(encoding="utf-8")
    model = model_path.read_text(encoding="utf-8")
    facts = {
        "arx_history_steps": 8 if "HISTORY_STEPS = 8" in model else None,
        "short_history_repeats_first_frame": "selected.insert(0,selected[0])" in model.replace(" ", ""),
        "absolute_step_over_16_feature": "s/16.0" in train.replace(" ", ""),
        "explicit_stable_low_order_passive_innovation_state": any(token in model for token in ("spectral_radius", "innovation_state", "passive_state")),
        "train_source_sha256": digest(train_path),
        "model_source_sha256": digest(model_path),
    }
    if facts["arx_history_steps"] != 8 or not facts["short_history_repeats_first_frame"] or not facts["absolute_step_over_16_feature"] or facts["explicit_stable_low_order_passive_innovation_state"]:
        raise RuntimeError("independent source-representation premise mismatch")
    return facts


def same(left: Any, right: Any, atol: float, rtol: float, path: str = "root") -> None:
    if isinstance(left, dict) and isinstance(right, dict):
        if set(left) != set(right):
            raise AssertionError(f"keys differ at {path}")
        for key in left:
            same(left[key], right[key], atol, rtol, f"{path}.{key}")
    elif isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            raise AssertionError(f"length differs at {path}")
        for index, (a, b) in enumerate(zip(left, right)):
            same(a, b, atol, rtol, f"{path}[{index}]")
    elif isinstance(left, (float, int)) and not isinstance(left, bool) and isinstance(right, (float, int)) and not isinstance(right, bool):
        if not math.isclose(float(left), float(right), abs_tol=atol, rel_tol=rtol):
            raise AssertionError(f"numeric mismatch at {path}: {left} != {right}")
    elif left != right:
        raise AssertionError(f"value mismatch at {path}: {left!r} != {right!r}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs/rgeo_zgeo_1ms_nr2r2a_identifiability_audit.json")
    parser.add_argument("--records-dir", type=Path, required=True)
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        config = json.loads(args.config.resolve().read_text(encoding="utf-8"))
        data, input_result = read_inputs(config, args.records_dir.resolve())
        recomputed = {
            "input": input_result,
            "state_geometry": states_result(data),
            "action_geometry": actions_result(data, config),
            "pair_and_prefix_geometry": pair_result(data),
            "source_representation": source_result(),
            "factorization_support": {
                "independent_all_q0_baseline": False,
                "same_primitive_repeated_across_position_anchors": False,
                "matched_time_different_position": False,
                "matched_position_different_time_or_arrival_history": False,
                "position_time_history_effects_separable": False,
            },
        }
        primary = json.loads(args.primary.resolve().read_text(encoding="utf-8"))
        for key, value in recomputed.items():
            same(value, primary[key], config["numeric_agreement_atol"], config["numeric_agreement_rtol"], key)
        result = {
            "schema_version": config["schema_version"], "passed": True,
            "route": config["routes"]["complete"], "primary_sha256": digest(args.primary.resolve()),
            "recomputed": recomputed,
            "agreement": {"counts_identities_ranks_booleans": "exact", "numeric_atol": config["numeric_agreement_atol"], "numeric_rtol": config["numeric_agreement_rtol"]},
            "counters": {"server_accesses": 0, "server_raw_reads": 0, "new_tsc_or_plant_advances": 0, "model_fits_or_training_runs": 0, "holdout_records_read": 0},
        }
        save_exclusive(args.output.resolve(), result)
    except Exception as error:
        print(json.dumps({"passed": False, "route": "ONE_MS_NR2R2A_INDEPENDENT_RECOMPUTE_MISMATCH_STOP", "error": f"{type(error).__name__}: {error}"}, indent=2))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
