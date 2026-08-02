#!/usr/bin/env python3
"""Independent raw-to-route audit for the completed T13S6 reinterpretation."""

from __future__ import annotations

import argparse
from collections import defaultdict
from decimal import Decimal
import gzip
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


DIRECTIONS = (
    "mode0_without_coil8",
    "mode0_coil8_component",
    "mode1",
    "mode2",
)
WINDOWS = ("transport", "braking")
SIGNS = (-1, 1)
BASELINE_ID = "lattice_baseline"
DISPLAY_TO_TSC_INDEX = (0, 2, 4, 1, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13)
EXPECTED_ROUTE = "IMMEDIATE_EFFECT_LOCAL_MAP_INSUFFICIENT_REDESIGN"
FORBIDDEN_TRACE_KEYS = (
    "pair_or_history_label_used",
    "source_result_used",
    "source_action_used",
    "source_coil_current_used",
    "source_wire_current_used",
    "current_run_future_used",
    "future_measurement_used",
    "hidden_wire_used",
)


def _strict_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def _strict_json_gz(path: Path) -> Any:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(
            handle,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_digest(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _feature_arrays(result: Mapping[str, Any], dt_s: float) -> np.ndarray:
    y = np.asarray(
        [[row["R"], row["Z"], row["Ip"]] for row in result["trajectory"]],
        dtype=float,
    )
    if y.ndim != 2 or y.shape[1] != 3 or not np.all(np.isfinite(y)):
        raise ValueError("invalid raw R/Z/Ip trajectory")
    velocity = np.zeros((len(y), 2), dtype=float)
    velocity[1:] = np.diff(y[:, :2], axis=0) / dt_s
    return np.column_stack((y[:, 0], y[:, 1], velocity[:, 0], velocity[:, 1], y[:, 2]))


def _context_key(spec: Mapping[str, Any]) -> tuple[str, str]:
    return str(spec["r3c3t13s5_offline_role"]), str(spec["r3c3t13s5_stratum"])


def _member_key(spec: Mapping[str, Any]) -> str:
    if str(spec["r3c3_probe_id"]) == BASELINE_ID:
        return BASELINE_ID
    return ":".join(
        (
            str(spec["r3c3_probe_window"]),
            str(spec["r3c3_probe_direction"]),
            str(int(spec["r3c3_probe_sign"])),
        )
    )


def _issue_trace(result: Mapping[str, Any]) -> Mapping[str, Any]:
    rows = [
        row
        for row in result["controller_trace"]
        if row.get("r3c3t13s5_lattice_event") == "issue"
    ]
    if len(rows) != 1:
        raise ValueError("raw issue trace identity mismatch")
    return rows[0]


def _effect_response(
    result: Mapping[str, Any],
    baseline: Mapping[str, Any],
    *,
    dt_s: float,
    radius_a: np.ndarray,
) -> dict[str, Any]:
    spec = result["spec"]
    first = int(spec["r3c3_probe_issue_step"]) + 1
    cancel = int(spec["r3c3_probe_cancel_step"]) + 1
    if cancel != first + 1:
        raise ValueError("corrected raw effect states are not adjacent")
    feature = _feature_arrays(result, dt_s)
    base_feature = _feature_arrays(baseline, dt_s)
    current = np.asarray(
        [row["currents_a_tsc"] for row in result["trajectory"]], dtype=float
    )
    base_current = np.asarray(
        [row["currents_a_tsc"] for row in baseline["trajectory"]], dtype=float
    )
    displacement = current[[first, cancel]] - base_current[[first, cancel]]
    pre_feature = feature[:first] - base_feature[:first]
    pre_current = current[:first] - base_current[:first]
    return {
        "first": first,
        "cancel": cancel,
        "response": np.concatenate(
            (feature[first] - base_feature[first], feature[cancel] - base_feature[cancel])
        ),
        "input": displacement.reshape(-1),
        "first_current": displacement[0],
        "pre_position": float(np.max(np.abs(pre_feature[:, :2]))) if len(pre_feature) else 0.0,
        "pre_velocity": float(np.max(np.abs(pre_feature[:, 2:4]))) if len(pre_feature) else 0.0,
        "pre_ip": float(np.max(np.abs(pre_feature[:, 4]))) if len(pre_feature) else 0.0,
        "pre_coil": (
            float(np.max(np.abs(pre_current) / radius_a[None, :]))
            if len(pre_current)
            else 0.0
        ),
    }


def _target_symmetry(
    plus: Mapping[str, Any], minus: Mapping[str, Any]
) -> bool:
    plus_trace = _issue_trace(plus)
    minus_trace = _issue_trace(minus)
    plus_fields = plus_trace["r3c3t13s5_actuator_prediction"]["card15_fields"]
    minus_fields = minus_trace["r3c3t13s5_actuator_prediction"]["card15_fields"]
    plus_center = plus_trace["r3c3t13s5_center_card15_fields"]
    minus_center = minus_trace["r3c3t13s5_center_card15_fields"]
    return bool(
        plus_center == minus_center
        and all(
            Decimal(p) - Decimal(c) == Decimal(c) - Decimal(m)
            for p, c, m in zip(plus_fields, plus_center, minus_fields)
        )
    )


def _raw_signed_rows(
    groups: Mapping[tuple[str, str], Mapping[str, Mapping[str, Any]]],
    *,
    cfg: Mapping[str, Any],
    dt_s: float,
    radius_a: np.ndarray,
) -> list[dict[str, Any]]:
    scales = np.asarray(cfg["response_scales"], dtype=float)
    floor_one = np.asarray([1e-9, 1e-9, 1e-7, 1e-7, 1e-4], dtype=float)
    floor_scaled = float(np.linalg.norm(np.tile(floor_one / scales, 2)))
    rows: list[dict[str, Any]] = []
    for (role, stratum), members in sorted(groups.items()):
        baseline = members[BASELINE_ID]
        for window in WINDOWS:
            for direction in DIRECTIONS:
                signed = {
                    sign: members[f"{window}:{direction}:{sign}"] for sign in SIGNS
                }
                response = {
                    sign: _effect_response(
                        value, baseline, dt_s=dt_s, radius_a=radius_a
                    )
                    for sign, value in signed.items()
                }
                plus_first = response[1]["first_current"]
                minus_first = response[-1]["first_current"]
                odd_current = (plus_first - minus_first) / 2.0
                even_current = (plus_first + minus_first) / 2.0
                odd_norm = float(np.linalg.norm(odd_current))
                even_norm = float(np.linalg.norm(even_current))
                signal = bool(
                    odd_norm
                    >= float(cfg["required_observed_odd_signal_radius_l2"])
                    * float(np.linalg.norm(radius_a))
                )
                target_symmetry = _target_symmetry(signed[1], signed[-1])
                ratio = even_norm / max(odd_norm, 1e-300)
                symmetry = bool(
                    target_symmetry
                    and signal
                    and ratio <= float(cfg["maximum_observed_even_to_odd_l2"])
                )
                pre_position = max(response[s]["pre_position"] for s in SIGNS)
                pre_velocity = max(response[s]["pre_velocity"] for s in SIGNS)
                pre_ip = max(response[s]["pre_ip"] for s in SIGNS)
                pre_coil = max(response[s]["pre_coil"] for s in SIGNS)
                pre_pass = bool(
                    pre_position <= float(cfg["pre_effect_position_max_m"])
                    and pre_velocity <= float(cfg["pre_effect_velocity_max_m_per_s"])
                    and pre_ip <= float(cfg["pre_effect_ip_max_A"])
                    and pre_coil <= 1.0 + 1e-12
                )
                odd_input = (response[1]["input"] - response[-1]["input"]) / 2.0
                odd_output = (
                    response[1]["response"] - response[-1]["response"]
                ) / 2.0
                development_signal = bool(
                    np.linalg.norm(odd_output / np.tile(scales, 2))
                    >= float(cfg["signal_floor_multiplier"]) * floor_scaled
                )
                rows.append(
                    {
                        "offline_role": role,
                        "stratum": stratum,
                        "probe_window": window,
                        "probe_direction": direction,
                        "first": response[1]["first"],
                        "cancel": response[1]["cancel"],
                        "target_symmetry": target_symmetry,
                        "signal": signal,
                        "symmetry": symmetry,
                        "pre_pass": pre_pass,
                        "development_signal": development_signal,
                        "odd_input": odd_input,
                        "odd_output": odd_output,
                        "signed_inputs": {s: response[s]["input"] for s in SIGNS},
                        "signed_outputs": {s: response[s]["response"] for s in SIGNS},
                    }
                )
    return rows


def _fit_models(
    rows: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> dict[tuple[str, str], dict[str, Any]]:
    models: dict[tuple[str, str], dict[str, Any]] = {}
    floor = np.tile(np.asarray([1e-9, 1e-9, 1e-7, 1e-7, 1e-4]), 2)
    caps = np.asarray(cfg["tube_caps_unscaled"], dtype=float)
    for stratum in ("easy", "hard"):
        for window in WINDOWS:
            cell = sorted(
                (
                    row
                    for row in rows
                    if row["offline_role"] == "development"
                    and row["stratum"] == stratum
                    and row["probe_window"] == window
                ),
                key=lambda row: DIRECTIONS.index(str(row["probe_direction"])),
            )
            if len(cell) != 4:
                raise ValueError("development cell coverage mismatch")
            x = np.asarray([row["odd_input"] for row in cell])
            y = np.asarray([row["odd_output"] for row in cell])
            jacobian = np.linalg.lstsq(x, y, rcond=None)[0]
            residuals = np.asarray(
                [
                    row["signed_outputs"][sign]
                    - row["signed_inputs"][sign] @ jacobian
                    for row in cell
                    for sign in SIGNS
                ]
            )
            radius = floor + float(cfg["tube_residual_multiplier"]) * np.max(
                np.abs(residuals), axis=0
            )
            condition = float(np.linalg.cond(x))
            models[(stratum, window)] = {
                "rank": int(np.linalg.matrix_rank(x)),
                "condition": condition if math.isfinite(condition) else None,
                "jacobian": jacobian,
                "radius": radius,
                "tube_pass": bool(np.all(radius <= caps)),
                "maximum_tube_to_cap_ratio": float(np.max(radius / caps)),
                "signal_pass": all(bool(row["development_signal"]) for row in cell),
            }
    return models


def _validation_rows(
    rows: Sequence[Mapping[str, Any]],
    models: Mapping[tuple[str, str], Mapping[str, Any]],
    cfg: Mapping[str, Any],
) -> list[dict[str, Any]]:
    scales = np.tile(np.asarray(cfg["response_scales"], dtype=float), 2)
    floor = float(
        np.linalg.norm(
            np.tile(
                np.asarray([1e-9, 1e-9, 1e-7, 1e-7, 1e-4])
                / np.asarray(cfg["response_scales"]),
                2,
            )
        )
    )
    output = []
    for row in rows:
        if row["offline_role"] != "blind_holdout":
            continue
        key = str(row["stratum"]), str(row["probe_window"])
        model = models[key]
        for sign in SIGNS:
            actual = row["signed_outputs"][sign]
            residual = actual - row["signed_inputs"][sign] @ model["jacobian"]
            relative = float(
                np.linalg.norm(residual / scales)
                / max(np.linalg.norm(actual / scales), floor)
            )
            output.append(
                {
                    "stratum": key[0],
                    "probe_window": key[1],
                    "probe_direction": row["probe_direction"],
                    "probe_sign": sign,
                    "componentwise_contained": bool(
                        np.all(np.abs(residual) <= model["radius"] + 1e-15)
                    ),
                    "scaled_center_relative_error": relative,
                    "scaled_center_relative_error_pass": bool(
                        relative
                        <= float(cfg["maximum_holdout_scaled_center_relative_error"])
                    ),
                    "pre_effect_causality_pass": bool(row["pre_pass"]),
                }
            )
    return output


def _max_array_discrepancy(
    raw_rows: Sequence[Mapping[str, Any]], reported_rows: Sequence[Mapping[str, Any]]
) -> float:
    reported = {
        (
            row["offline_role"],
            row["stratum"],
            row["probe_window"],
            row["probe_direction"],
        ): row
        for row in reported_rows
    }
    maximum = 0.0
    for row in raw_rows:
        key = (
            row["offline_role"],
            row["stratum"],
            row["probe_window"],
            row["probe_direction"],
        )
        target = reported[key]
        pairs = (
            (row["odd_input"], target["odd_input_measured_current_A"]),
            (row["odd_output"], target["odd_response_unscaled"]),
            *(
                (
                    row["signed_inputs"][sign],
                    target["signed_inputs_measured_current_A"][str(sign)],
                )
                for sign in SIGNS
            ),
            *(
                (
                    row["signed_outputs"][sign],
                    target["signed_responses_unscaled"][str(sign)],
                )
                for sign in SIGNS
            ),
        )
        maximum = max(
            maximum,
            *(float(np.max(np.abs(np.asarray(a) - np.asarray(b)))) for a, b in pairs),
        )
    return maximum


def run_audit(
    *, result_path: Path, run_dir: Path, source_audit_path: Path, config_path: Path
) -> dict[str, Any]:
    result = _strict_json(result_path)
    config = _strict_json(config_path)
    source_audit = _strict_json(source_audit_path)
    probe_cfg = config["lattice_probe"]

    raw_dir = run_dir / "stage4_2r3c3t13s5_lattice_native_split_holdout" / "raw"
    raw_paths = sorted(raw_dir.glob("*.json.gz"))
    inventory = [
        {"path": path.name, "size_bytes": path.stat().st_size, "sha256": _sha256(path)}
        for path in raw_paths
    ]
    inventory_digest = _canonical_digest(inventory)
    if inventory != result["raw_inventory"]:
        raise ValueError("independent raw inventory differs from T13S6 result")
    if not (
        len(raw_paths) == 68
        and inventory_digest == result["summary"]["raw_inventory_digest"]
        and source_audit.get("certified_scientific_result")
        and source_audit.get("control_raw_identity_exact")
        and source_audit.get("raw_inventory", {}).get("digest") == inventory_digest
    ):
        raise ValueError("independent source/raw authentication failed")

    raw = [_strict_json_gz(path) for path in raw_paths]
    if not all(
        item.get("success")
        and item.get("completed")
        and item.get("stage") == "Stage4.2R3c3T13S5"
        and len(item.get("trajectory", []))
        == int(item["spec"]["formal_horizon_steps"]) + 1
        for item in raw
    ):
        raise ValueError("raw completion or horizon mismatch")

    trace_identity_count = 0
    forbidden_count = 0
    groups: dict[tuple[str, str], dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for item in raw:
        spec = item["spec"]
        key = _context_key(spec)
        member = _member_key(spec)
        if member in groups[key]:
            raise ValueError("duplicate independent raw group member")
        groups[key][member] = item
        events = [
            row.get("r3c3t13s5_lattice_event")
            for row in item["controller_trace"]
            if row.get("r3c3t13s5_lattice_event") != "none"
        ]
        trace_identity_count += int(events == ([] if member == BASELINE_ID else ["issue", "cancel"]))
        forbidden_count += sum(
            any(bool(row.get(field)) for field in FORBIDDEN_TRACE_KEYS)
            for row in item["controller_trace"]
        )
    if len(groups) != 4 or any(len(members) != 17 for members in groups.values()):
        raise ValueError("independent context/member coverage mismatch")

    payloads = sorted(
        (run_dir / "stage4_2r3c3t13s5_lattice_native_split_holdout" / "variants").glob(
            "payload_*.json"
        )
    )
    if len(payloads) != 68:
        raise ValueError("payload inventory mismatch")
    turns_display = np.asarray(
        _strict_json(payloads[0])["env_cfg"]["turns_display_order"], dtype=float
    )
    turns_tsc = turns_display[np.asarray(DISPLAY_TO_TSC_INDEX)]
    radius_a = float(probe_cfg["output_grid_kAt"]) * 1000.0 / turns_tsc
    time_values = np.asarray([row["time_ms"] for row in raw[0]["trajectory"]], dtype=float)
    time_deltas = np.diff(time_values)
    if not np.allclose(time_deltas, time_deltas[0], rtol=0.0, atol=1e-12):
        raise ValueError("trajectory time grid is not uniform")
    dt_s = float(time_deltas[0]) / 1000.0

    signed_rows = _raw_signed_rows(
        groups, cfg=probe_cfg, dt_s=dt_s, radius_a=radius_a
    )
    models = _fit_models(signed_rows, probe_cfg)
    validation = _validation_rows(signed_rows, models, probe_cfg)
    discrepancy = _max_array_discrepancy(signed_rows, result["signed_group_results"])

    result_models = {
        (row["stratum"], row["probe_window"]): row for row in result["model_cells"]
    }
    maximum_model_discrepancy = 0.0
    for key, model in models.items():
        target = result_models[key]
        maximum_model_discrepancy = max(
            maximum_model_discrepancy,
            float(np.max(np.abs(model["jacobian"] - np.asarray(target["jacobian"])))),
            float(np.max(np.abs(model["radius"] - np.asarray(target["tube_radius_unscaled"])))),
            abs(float(model["maximum_tube_to_cap_ratio"]) - float(target["maximum_tube_to_cap_ratio"])),
            abs(float(model["condition"]) - float(target["condition_number"])),
        )

    result_validation = {
        (
            row["stratum"],
            row["probe_window"],
            row["probe_direction"],
            int(row["probe_sign"]),
        ): row
        for row in result["consumed_validation_results"]
    }
    maximum_validation_discrepancy = 0.0
    validation_boolean_exact = True
    for row in validation:
        key = (
            row["stratum"],
            row["probe_window"],
            row["probe_direction"],
            int(row["probe_sign"]),
        )
        target = result_validation[key]
        maximum_validation_discrepancy = max(
            maximum_validation_discrepancy,
            abs(
                float(row["scaled_center_relative_error"])
                - float(target["scaled_center_relative_error"])
            ),
        )
        validation_boolean_exact = validation_boolean_exact and all(
            bool(row[field]) == bool(target[field])
            for field in (
                "componentwise_contained",
                "scaled_center_relative_error_pass",
                "pre_effect_causality_pass",
            )
        )

    summary = {
        "raw_identity_pass_count": len(raw),
        "raw_expected": 68,
        "raw_total_bytes": sum(row["size_bytes"] for row in inventory),
        "raw_inventory_digest": inventory_digest,
        "source_t13s5_audit_certified": True,
        "trace_identity_pass_count": trace_identity_count,
        "trace_identity_expected": 68,
        "signed_group_count": len(signed_rows),
        "target_field_symmetry_pass_count": sum(row["target_symmetry"] for row in signed_rows),
        "corrected_pre_effect_causality_pass_count": sum(row["pre_pass"] for row in signed_rows),
        "observed_current_signal_pass_count": sum(row["signal"] for row in signed_rows),
        "observed_current_symmetry_pass_count": sum(row["symmetry"] for row in signed_rows),
        "development_group_count": sum(row["offline_role"] == "development" for row in signed_rows),
        "development_signal_pass_count": sum(
            row["offline_role"] == "development" and row["development_signal"]
            for row in signed_rows
        ),
        "model_cell_count": len(models),
        "model_rank_condition_pass_count": sum(
            model["rank"] == int(probe_cfg["required_development_rank"])
            and model["condition"] is not None
            and model["condition"] <= float(probe_cfg["maximum_development_condition_number"])
            for model in models.values()
        ),
        "model_tube_pass_count": sum(model["tube_pass"] for model in models.values()),
        "maximum_finite_condition_number": max(float(model["condition"]) for model in models.values()),
        "nonfinite_condition_count": sum(model["condition"] is None for model in models.values()),
        "maximum_tube_to_cap_ratio": max(model["maximum_tube_to_cap_ratio"] for model in models.values()),
        "consumed_validation_row_count": len(validation),
        "validation_containment_pass_count": sum(row["componentwise_contained"] for row in validation),
        "validation_relative_error_pass_count": sum(row["scaled_center_relative_error_pass"] for row in validation),
        "validation_pre_effect_causality_pass_count": sum(row["pre_effect_causality_pass"] for row in validation),
        "maximum_validation_scaled_relative_error": max(row["scaled_center_relative_error"] for row in validation),
        "forbidden_model_or_trace_input_count": forbidden_count,
    }
    summary_boolean_exact = all(
        (math.isclose(float(value), float(result["summary"][key]), rel_tol=1e-12, abs_tol=1e-12)
         if isinstance(value, float)
         else value == result["summary"][key])
        for key, value in summary.items()
    )
    certified = bool(
        discrepancy <= 1e-12
        and maximum_model_discrepancy <= 1e-12
        and maximum_validation_discrepancy <= 1e-12
        and validation_boolean_exact
        and summary_boolean_exact
        and result["route"] == EXPECTED_ROUTE
        and result["passed"] is False
        and result["real_tsc_executed"] is False
        and result["controller_or_plant_step_executed"] is False
    )
    breakdown: dict[str, dict[str, Any]] = {}
    for key in ((s, w) for s in ("easy", "hard") for w in WINDOWS):
        cell = [row for row in validation if (row["stratum"], row["probe_window"]) == key]
        breakdown["/".join(key)] = {
            "rows": len(cell),
            "containment_pass": sum(row["componentwise_contained"] for row in cell),
            "relative_error_pass": sum(row["scaled_center_relative_error_pass"] for row in cell),
            "maximum_scaled_relative_error": max(row["scaled_center_relative_error"] for row in cell),
        }
    return {
        "schema_version": 1,
        "stage": "Stage4.2R3c3T13S6",
        "audit_revision": "independent_raw_to_route_v1",
        "source_result": str(result_path),
        "source_result_sha256": _sha256(result_path),
        "source_t13s5_audit": str(source_audit_path),
        "source_t13s5_audit_sha256": _sha256(source_audit_path),
        "raw_inventory": {
            "count": len(inventory),
            "total_bytes": sum(row["size_bytes"] for row in inventory),
            "digest": inventory_digest,
        },
        "raw_to_reported_array_max_abs_discrepancy": discrepancy,
        "independent_model_max_abs_discrepancy": maximum_model_discrepancy,
        "independent_validation_error_max_abs_discrepancy": maximum_validation_discrepancy,
        "validation_boolean_exact": validation_boolean_exact,
        "summary_exact": summary_boolean_exact,
        "summary": summary,
        "validation_breakdown": breakdown,
        "certified_scientific_result": certified,
        "runtime_or_environment_error": False,
        "raw_or_snapshot_corruption": False,
        "statistics_or_reporting_error": not certified,
        "design_failure": True,
        "real_controller_or_mpc_executed": False,
        "route": EXPECTED_ROUTE if certified else "INDEPENDENT_AUDIT_MISMATCH",
        "formal_timing_unchanged": True,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "bc_dagger_or_rl_allowed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--source-audit", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = run_audit(
        result_path=args.result,
        run_dir=args.run_dir,
        source_audit_path=args.source_audit,
        config_path=args.config,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "sha256": _sha256(args.output),
                "certified": output["certified_scientific_result"],
                "route": output["route"],
                "summary": output["summary"],
            },
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
