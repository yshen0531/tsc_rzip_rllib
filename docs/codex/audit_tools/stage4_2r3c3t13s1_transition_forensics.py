#!/usr/bin/env python3
"""Independent raw forensics for the completed T13S1 sentinel.

This tool reads the immutable 52-file T13S1 raw directory in place.  It does
not import the campaign evaluator and does not run a controller, Ray, gotsc,
TSC, or a plant step.  It separates requested command symmetry, observed
14-coil-current symmetry, immediate plant response, later closed-loop
accumulation, and paired-history dependence.  The frozen T13S1 verdict is
reported unchanged; the extra diagnostics are route evidence only.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


STAGE = "Stage4.2R3c3T13S1"
CAMPAIGN_IDENTITY = "restart_issue_time_single_step_transition_sentinel_v1"
CONTROLLER_REVISION = "single_step_transition_probe_v42r3c3t13s1_v1"
EXPECTED_RAW_COUNT = 52
EXPECTED_RAW_BYTES = 2_463_366
EXPECTED_RAW_DIGEST = (
    "de2be508888aa503628538a795474fbf70788252e7913f87af7603c5bc034603"
)
DT_S = 0.01
NOMINAL_MAX_DELTA_A = 3.0
SCALES = np.asarray([0.03, 0.03, 0.1, 0.1, 2000.0], dtype=float)
RELATIVE_GATE = 0.10
WINDOW_OFFSETS = (0, 1, 3, 7)
TURNS_TSC = np.asarray(
    [480.0] * 8 + [200.0, 200.0, 100.0, 100.0, 100.0, 100.0],
    dtype=float,
)
TURN_SOURCE_RELATIVE = Path(
    "stage4_1r17_runs/"
    "stage4_1r17_original_deadline_one_sided_robust_braking_closure_"
    "20260729_142501/stage4_1r4_environment_variants/"
    "env_slew_0p900_h37.json"
)
TURN_SOURCE_SHA256 = (
    "2305ae9750afc534c6c270651ec3aabda82308edd1dacad103501a653a94993e"
)


def _canonical_digest(value: Any) -> str:
    text = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_gz(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def _inventory(paths: Iterable[Path], *, relative_to: Path) -> dict[str, Any]:
    rows = [
        {
            "path": path.relative_to(relative_to).as_posix(),
            "size_bytes": int(path.stat().st_size),
            "sha256": _sha256(path),
        }
        for path in sorted(paths)
        if path.is_file()
    ]
    return {
        "n_files": len(rows),
        "total_bytes": sum(int(row["size_bytes"]) for row in rows),
        "digest": _canonical_digest(rows),
        "files": rows,
    }


def _context_key(spec: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        str(spec["pair_id"]),
        str(spec["history_member"]),
        str(spec["target_id"]),
        int(spec["action_delay_steps"]),
        float(spec["slew_scale"]),
    )


def _context_fields(key: Sequence[Any]) -> dict[str, Any]:
    return dict(
        zip(
            (
                "pair_id",
                "history_member",
                "target_id",
                "actual_delay_steps",
                "actual_slew_scale",
            ),
            key,
        )
    )


def _trajectory_feature(result: Mapping[str, Any]) -> np.ndarray:
    rows = result["trajectory"]
    y = np.asarray([[row["R"], row["Z"], row["Ip"]] for row in rows], dtype=float)
    if y.shape != (51, 3) or not np.all(np.isfinite(y)):
        raise ValueError("T13S1 trajectory must contain 51 finite R/Z/Ip states")
    velocity = np.zeros((51, 2), dtype=float)
    velocity[1:] = np.diff(y[:, :2], axis=0) / DT_S
    return np.column_stack((y[:, 0], y[:, 1], velocity, y[:, 2]))


def _current_array(result: Mapping[str, Any]) -> np.ndarray:
    value = np.asarray(
        [row["currents_a_tsc"] for row in result["trajectory"]], dtype=float
    )
    if value.shape != (51, 14) or not np.all(np.isfinite(value)):
        raise ValueError("T13S1 trajectory must contain 51 finite 14-coil states")
    return value


def _wire_array(result: Mapping[str, Any]) -> np.ndarray:
    value = np.asarray(
        [row["wire_currents_a"] for row in result["trajectory"]], dtype=float
    )
    if value.shape[0] != 51 or value.ndim != 2 or not np.all(np.isfinite(value)):
        raise ValueError("T13S1 trajectory has invalid wire-current telemetry")
    return value


def _trace_action_array(result: Mapping[str, Any]) -> np.ndarray:
    value = np.asarray(
        [row["action_norm_tsc"] for row in result["controller_trace"]],
        dtype=float,
    )
    if value.shape != (50, 14) or not np.all(np.isfinite(value)):
        raise ValueError("T13S1 trace must contain 50 finite 14-coil commands")
    return value


def _scaled_norm(value: np.ndarray) -> float:
    array = np.asarray(value, dtype=float)
    if array.shape[-1] != 5:
        raise ValueError("plant feature must end in five scaled components")
    return float(np.linalg.norm((array / SCALES).reshape(-1)))


def _relative(numerator: np.ndarray, denominator: np.ndarray) -> float:
    den = float(np.linalg.norm(np.asarray(denominator, dtype=float).reshape(-1)))
    return float(
        np.linalg.norm(np.asarray(numerator, dtype=float).reshape(-1))
        / max(den, 1e-300)
    )


def _scaled_relative(numerator: np.ndarray, denominator: np.ndarray) -> float:
    num = np.asarray(numerator, dtype=float) / SCALES
    den = np.asarray(denominator, dtype=float) / SCALES
    return _relative(num, den)


def _card15_formatter_grid_a(current_a_tsc: np.ndarray) -> np.ndarray:
    """Return one ``.3E`` Card15 least-significant step in single-turn A."""
    current = np.asarray(current_a_tsc, dtype=float).reshape(14)
    current_kat = np.abs(current * TURNS_TSC / 1000.0)
    exponents = np.zeros(14, dtype=int)
    nonzero = current_kat > 0.0
    exponents[nonzero] = np.floor(np.log10(current_kat[nonzero])).astype(int)
    grid_kat = np.power(10.0, exponents - 3)
    return grid_kat * 1000.0 / TURNS_TSC


def _grid_metrics(
    command: np.ndarray,
    observed: np.ndarray,
    baseline_current: np.ndarray,
) -> dict[str, Any]:
    command = np.asarray(command, dtype=float).reshape(14)
    observed = np.asarray(observed, dtype=float).reshape(14)
    grid = _card15_formatter_grid_a(baseline_current)
    active = np.abs(command) > 1e-12
    ratios = np.abs(command[active]) / grid[active]
    observed_grid_units = observed / grid
    ratio_metrics = {
        "minimum_command_to_grid_ratio": None,
        "median_command_to_grid_ratio": None,
        "maximum_command_to_grid_ratio": None,
    }
    if len(ratios):
        ratio_metrics = {
            "minimum_command_to_grid_ratio": float(np.min(ratios)),
            "median_command_to_grid_ratio": float(np.median(ratios)),
            "maximum_command_to_grid_ratio": float(np.max(ratios)),
        }
    return {
        "active_command_component_count": int(np.sum(active)),
        "command_components_below_one_grid": int(
            np.sum(np.abs(command[active]) < grid[active])
        ),
        **ratio_metrics,
        "minimum_formatter_grid_A": float(np.min(grid)),
        "maximum_formatter_grid_A": float(np.max(grid)),
        "maximum_observed_integer_grid_residual": float(
            np.max(np.abs(observed_grid_units - np.rint(observed_grid_units)))
        ),
    }


def _window_metrics(
    numerator: np.ndarray,
    denominator: np.ndarray,
    *,
    first: int,
    formal_end: int,
) -> dict[str, float]:
    output: dict[str, float] = {}
    for offset in WINDOW_OFFSETS:
        end = min(first + offset, formal_end)
        label = "first" if offset == 0 else f"first_through_plus_{offset}"
        output[label] = _scaled_relative(
            numerator[first : end + 1], denominator[first : end + 1]
        )
    output["first_through_formal_end"] = _scaled_relative(
        numerator[first : formal_end + 1], denominator[first : formal_end + 1]
    )
    return output


def _vector_difference_metrics(left: np.ndarray, right: np.ndarray) -> dict[str, Any]:
    left = np.asarray(left, dtype=float).reshape(-1)
    right = np.asarray(right, dtype=float).reshape(-1)
    difference = left - right
    return {
        "dimension": int(len(left)),
        "maximum_abs_difference": float(np.max(np.abs(difference))),
        "rms_difference": float(np.sqrt(np.mean(difference**2))),
        "l2_difference": float(np.linalg.norm(difference)),
        "relative_l2_to_right": float(
            np.linalg.norm(difference) / max(float(np.linalg.norm(right)), 1e-300)
        ),
        "exact": bool(np.array_equal(left, right)),
    }


def _load_and_authenticate(
    raw_dir: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    paths = sorted(raw_dir.glob("*.json.gz"))
    inventory = _inventory(paths, relative_to=raw_dir)
    if (
        int(inventory["n_files"]) != EXPECTED_RAW_COUNT
        or int(inventory["total_bytes"]) != EXPECTED_RAW_BYTES
        or str(inventory["digest"]) != EXPECTED_RAW_DIGEST
    ):
        raise ValueError(f"T13S1 immutable raw inventory mismatch: {inventory}")
    results = [_read_json_gz(path) for path in paths]
    identities: set[str] = set()
    for path, result in zip(paths, results):
        experiment_id = str(result.get("experiment_id", ""))
        if (
            not experiment_id
            or experiment_id in identities
            or path.name != f"{experiment_id}.json.gz"
            or result.get("stage") != STAGE
            or result.get("campaign_identity") != CAMPAIGN_IDENTITY
            or result.get("controller_revision") != CONTROLLER_REVISION
            or not bool(result.get("success"))
            or not bool(result.get("completed"))
            or result.get("failure_reason")
            or len(result.get("trajectory", [])) != 51
            or len(result.get("controller_trace", [])) != 50
        ):
            raise ValueError(f"T13S1 raw authentication failed: {path.name}")
        identities.add(experiment_id)
        _trajectory_feature(result)
        _current_array(result)
        _wire_array(result)
        _trace_action_array(result)
    return results, inventory


def analyze_results(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if len(results) != EXPECTED_RAW_COUNT:
        raise ValueError("T13S1 forensic analysis requires exactly 52 results")
    baselines: dict[tuple[Any, ...], Mapping[str, Any]] = {}
    signed: dict[
        tuple[Any, ...], dict[int, Mapping[str, Any]]
    ] = defaultdict(dict)
    for result in results:
        spec = result["spec"]
        sign = int(spec["r3c3_probe_sign"])
        context = _context_key(spec)
        if sign == 0:
            if context in baselines:
                raise ValueError("duplicate T13S1 baseline context")
            baselines[context] = result
            continue
        group = context + (
            str(spec["r3c3_probe_window"]),
            int(spec["r3c3_probe_mode"]),
        )
        if sign in signed[group]:
            raise ValueError("duplicate T13S1 signed member")
        signed[group][sign] = result
    if (
        len(baselines) != 4
        or len(signed) != 24
        or any(set(members) != {-1, 1} for members in signed.values())
    ):
        raise ValueError("T13S1 baseline/signed group coverage mismatch")

    plant_odds: dict[tuple[Any, ...], np.ndarray] = {}
    current_odds: dict[tuple[Any, ...], np.ndarray] = {}
    central_rows: list[dict[str, Any]] = []
    for group in sorted(signed):
        plus = signed[group][1]
        minus = signed[group][-1]
        baseline = baselines[group[:5]]
        p_feature = _trajectory_feature(plus)
        m_feature = _trajectory_feature(minus)
        b_feature = _trajectory_feature(baseline)
        p_current = _current_array(plus)
        m_current = _current_array(minus)
        b_current = _current_array(baseline)
        p_action = _trace_action_array(plus)
        m_action = _trace_action_array(minus)
        b_action = _trace_action_array(baseline)

        odd = (p_feature - m_feature) / 2.0
        even = (p_feature + m_feature) / 2.0 - b_feature
        current_odd = (p_current - m_current) / 2.0
        current_even = (p_current + m_current) / 2.0 - b_current
        first = int(plus["spec"]["r3c3_probe_first_effect_state"])
        cancel = int(plus["spec"]["r3c3_probe_cancel_effect_state"])
        formal_end = int(plus["spec"]["formal_horizon_steps"])
        issue_steps = sorted(
            int(step)
            for step in plus["spec"]["r3c3_probe_delta_by_task_issue_step"]
        )
        if (
            first not in (3, 17)
            or cancel != first + 1
            or len(issue_steps) != 2
        ):
            raise ValueError("T13S1 effect/issue schedule changed")
        issue = issue_steps[0]
        command_scale = NOMINAL_MAX_DELTA_A * float(group[4])
        command_plus = (p_action[issue] - b_action[issue]) * command_scale
        command_minus = (m_action[issue] - b_action[issue]) * command_scale
        command_odd = (command_plus - command_minus) / 2.0
        command_even = (command_plus + command_minus) / 2.0
        observed_plus = p_current[first] - b_current[first]
        observed_minus = m_current[first] - b_current[first]
        baseline_current = b_current[first]

        row = {
            **_context_fields(group[:5]),
            "probe_window": group[5],
            "probe_mode": group[6],
            "first_effect_state": first,
            "cancel_effect_state": cancel,
            "formal_end_state": formal_end,
            "requested_command_first_issue": {
                "odd_l2_A": float(np.linalg.norm(command_odd)),
                "even_l2_A": float(np.linalg.norm(command_even)),
                "even_to_odd_l2": _relative(command_even, command_odd),
                "plus_to_negative_minus_cosine": float(
                    np.dot(command_plus, -command_minus)
                    / max(
                        float(
                            np.linalg.norm(command_plus)
                            * np.linalg.norm(command_minus)
                        ),
                        1e-300,
                    )
                ),
            },
            "observed_current_first_effect": {
                "odd_l2_A": float(np.linalg.norm(current_odd[first])),
                "even_l2_A": float(np.linalg.norm(current_even[first])),
                "even_to_odd_l2": _relative(
                    current_even[first], current_odd[first]
                ),
                "plus_command_error_l2_A": float(
                    np.linalg.norm(observed_plus - command_plus)
                ),
                "minus_command_error_l2_A": float(
                    np.linalg.norm(observed_minus - command_minus)
                ),
                "plus_to_negative_minus_cosine": float(
                    np.dot(observed_plus, -observed_minus)
                    / max(
                        float(
                            np.linalg.norm(observed_plus)
                            * np.linalg.norm(observed_minus)
                        ),
                        1e-300,
                    )
                ),
                "maximum_abs_even_component_A": float(
                    np.max(np.abs(current_even[first]))
                ),
                "plus_card15_grid_diagnostic": _grid_metrics(
                    command_plus, observed_plus, baseline_current
                ),
                "minus_card15_grid_diagnostic": _grid_metrics(
                    command_minus, observed_minus, baseline_current
                ),
            },
            "plant_response": {
                "first_scaled_odd_l2": _scaled_norm(odd[first : first + 1]),
                "first_scaled_even_l2": _scaled_norm(even[first : first + 1]),
                "relative_by_window": _window_metrics(
                    even, odd, first=first, formal_end=formal_end
                ),
            },
            "pre_effect_exact": bool(
                np.array_equal(p_feature[:first], b_feature[:first])
                and np.array_equal(m_feature[:first], b_feature[:first])
                and np.array_equal(p_current[:first], b_current[:first])
                and np.array_equal(m_current[:first], b_current[:first])
            ),
        }
        central_rows.append(row)
        plant_odds[group] = odd
        current_odds[group] = current_odd

    history_rows: list[dict[str, Any]] = []
    history_group_keys = sorted(
        {(key[0], key[2], key[3], key[4], key[5], key[6]) for key in signed}
    )
    for key in history_group_keys:
        plus_key = (key[0], "plus_first", *key[1:])
        minus_key = (key[0], "minus_first", *key[1:])
        if plus_key not in plant_odds or minus_key not in plant_odds:
            raise ValueError("T13S1 matched-history coverage mismatch")
        plus_plant = plant_odds[plus_key]
        minus_plant = plant_odds[minus_key]
        plus_current = current_odds[plus_key]
        minus_current = current_odds[minus_key]
        first = 3 if key[4] == "transport" else 17
        formal_end = 37 if math.isclose(float(key[3]), 0.9) else 35
        plus_baseline = baselines[plus_key[:5]]
        minus_baseline = baselines[minus_key[:5]]
        plus_feature = _trajectory_feature(plus_baseline)
        minus_feature = _trajectory_feature(minus_baseline)
        plus_coil = _current_array(plus_baseline)
        minus_coil = _current_array(minus_baseline)
        plus_wire = _wire_array(plus_baseline)
        minus_wire = _wire_array(minus_baseline)
        history_rows.append(
            {
                "pair_id": key[0],
                "target_id": key[1],
                "actual_delay_steps": key[2],
                "actual_slew_scale": key[3],
                "probe_window": key[4],
                "probe_mode": key[5],
                "first_effect_state": first,
                "formal_end_state": formal_end,
                "plant_odd_response_relative_by_window": _window_metrics(
                    plus_plant - minus_plant,
                    minus_plant,
                    first=first,
                    formal_end=formal_end,
                ),
                "observed_current_odd_first_effect_relative_difference": _relative(
                    plus_current[first] - minus_current[first],
                    minus_current[first],
                ),
                "baseline_state0_difference": {
                    "R_m": float(plus_feature[0, 0] - minus_feature[0, 0]),
                    "Z_m": float(plus_feature[0, 1] - minus_feature[0, 1]),
                    "Ip_A": float(plus_feature[0, 4] - minus_feature[0, 4]),
                    "coil": _vector_difference_metrics(
                        plus_coil[0], minus_coil[0]
                    ),
                    "wire": _vector_difference_metrics(
                        plus_wire[0], minus_wire[0]
                    ),
                },
                "baseline_pre_effect_state_difference": {
                    "state_index": first - 1,
                    "scaled_feature_relative_to_minus": _scaled_relative(
                        plus_feature[first - 1 : first]
                        - minus_feature[first - 1 : first],
                        minus_feature[first - 1 : first],
                    ),
                    "plant_feature_difference": (
                        plus_feature[first - 1] - minus_feature[first - 1]
                    ).tolist(),
                    "coil": _vector_difference_metrics(
                        plus_coil[first - 1], minus_coil[first - 1]
                    ),
                    "wire": _vector_difference_metrics(
                        plus_wire[first - 1], minus_wire[first - 1]
                    ),
                },
            }
        )
    if len(history_rows) != 12:
        raise ValueError("T13S1 matched-history group count mismatch")

    def count_central(path: Sequence[str]) -> int:
        count = 0
        for row in central_rows:
            value: Any = row
            for field in path:
                value = value[field]
            count += float(value) <= RELATIVE_GATE
        return int(count)

    def count_history(field: str) -> int:
        return int(
            sum(
                float(row["plant_odd_response_relative_by_window"][field])
                <= RELATIVE_GATE
                for row in history_rows
            )
        )

    route_metrics = {
        "requested_command_first_issue_symmetry_pass_count": count_central(
            ("requested_command_first_issue", "even_to_odd_l2")
        ),
        "observed_current_first_effect_symmetry_pass_count": count_central(
            ("observed_current_first_effect", "even_to_odd_l2")
        ),
        "plant_first_effect_symmetry_pass_count": count_central(
            ("plant_response", "relative_by_window", "first")
        ),
        "plant_full_formal_window_symmetry_pass_count": count_central(
            (
                "plant_response",
                "relative_by_window",
                "first_through_formal_end",
            )
        ),
        "matched_history_first_effect_pass_count": count_history("first"),
        "matched_history_full_formal_window_pass_count": count_history(
            "first_through_formal_end"
        ),
        "central_group_count": len(central_rows),
        "matched_history_group_count": len(history_rows),
        "pre_effect_exact_count": int(
            sum(bool(row["pre_effect_exact"]) for row in central_rows)
        ),
        "command_components_below_one_card15_grid": int(
            sum(
                row["observed_current_first_effect"][side][
                    "command_components_below_one_grid"
                ]
                for row in central_rows
                for side in (
                    "plus_card15_grid_diagnostic",
                    "minus_card15_grid_diagnostic",
                )
            )
        ),
        "active_command_component_count": int(
            sum(
                row["observed_current_first_effect"][side][
                    "active_command_component_count"
                ]
                for row in central_rows
                for side in (
                    "plus_card15_grid_diagnostic",
                    "minus_card15_grid_diagnostic",
                )
            )
        ),
        "maximum_observed_integer_card15_grid_residual": float(
            max(
                row["observed_current_first_effect"][side][
                    "maximum_observed_integer_grid_residual"
                ]
                for row in central_rows
                for side in (
                    "plus_card15_grid_diagnostic",
                    "minus_card15_grid_diagnostic",
                )
            )
        ),
    }
    route_metrics["action_resolution_material"] = bool(
        route_metrics["observed_current_first_effect_symmetry_pass_count"] < 24
    )
    route_metrics["immediate_plant_nonlinearity_or_input_asymmetry_material"] = bool(
        route_metrics["plant_first_effect_symmetry_pass_count"] < 24
    )
    route_metrics["paired_state_or_hidden_history_dependence_material"] = bool(
        route_metrics["matched_history_first_effect_pass_count"] < 12
    )
    route_metrics["later_closed_loop_accumulation_material"] = bool(
        route_metrics["plant_full_formal_window_symmetry_pass_count"]
        < route_metrics["plant_first_effect_symmetry_pass_count"]
        or route_metrics["matched_history_full_formal_window_pass_count"]
        < route_metrics["matched_history_first_effect_pass_count"]
    )
    return {
        "central_rows": central_rows,
        "matched_history_rows": history_rows,
        "route_metrics": route_metrics,
    }


def run_audit(args: argparse.Namespace) -> dict[str, Any]:
    project_root = args.project_root.expanduser().resolve()
    run_dir = args.run_dir.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    if output_dir.exists():
        raise ValueError("T13S1 forensic output directory must be new")
    if run_dir == output_dir or run_dir in output_dir.parents:
        raise ValueError("forensic output may not be inside immutable run evidence")
    raw_dir = run_dir / "stage4_2r3c3t13s1_minimal_transition_sentinel/raw"
    results, inventory = _load_and_authenticate(raw_dir)
    analysis = analyze_results(results)

    official_summary = _read_json(
        run_dir
        / "stage4_2r3c3t13s1_minimal_transition_sentinel/summary.json"
    )
    official_state = _read_json(run_dir / "stage4_2r3c3t13s1_state.json")
    inputa_source = project_root / "tsc_rzip_rllib/core/inputa.py"
    runner_source = project_root / "tsc_rzip_rllib/core/runner.py"
    turn_source = project_root / TURN_SOURCE_RELATIVE
    source_text = inputa_source.read_text(encoding="utf-8")
    formatter_contract_present = 'f"{float(value):.3E}"' in source_text
    turn_config = _read_json(turn_source)
    if (
        _sha256(turn_source) != TURN_SOURCE_SHA256
        or np.asarray(turn_config["turns_display_order"], dtype=float).tolist()
        != TURNS_TSC.tolist()
    ):
        raise ValueError("T13S1 Card15 turn-count source mismatch")
    report = {
        "schema_version": 1,
        "stage": STAGE,
        "classification": "read_only_immutable_raw_transition_forensics",
        "run_dir": str(run_dir),
        "raw_inventory": inventory,
        "source_provenance": {
            "inputa_source_sha256": _sha256(inputa_source),
            "runner_source_sha256": _sha256(runner_source),
            "turn_count_source": TURN_SOURCE_RELATIVE.as_posix(),
            "turn_count_source_sha256": _sha256(turn_source),
            "turns_tsc": TURNS_TSC.tolist(),
            "ten_character_scientific_3_decimal_formatter_present": (
                formatter_contract_present
            ),
        },
        "official_result_unchanged": {
            "finished": bool(official_state.get("finished")),
            "primary_pass": bool(official_state.get("primary_pass")),
            "stop_reason": official_state.get("stop_reason"),
            "official_passed": bool(official_summary.get("passed")),
            "official_central_symmetry_pass_count": int(
                official_summary.get("central_symmetry_pass_count", -1)
            ),
            "official_matched_hidden_history_pass_count": int(
                official_summary.get("matched_hidden_history_pass_count", -1)
            ),
            "official_route": "SENTINEL_FAIL_STOP_IDENTIFICATION",
            "thresholds_changed": False,
            "verdict_reinterpreted": False,
        },
        **analysis,
        "scientific_classification": {
            "runtime_or_environment_error": False,
            "packaging_or_import_error": False,
            "raw_or_snapshot_corruption": False,
            "statistics_or_reporting_error": False,
            "design_or_model_action_resolution_gap": True,
            "real_mpc_tested": False,
            "global_unreachability_proven": False,
            "probe_trajectories_allowed_in_expert_dataset": False,
            "bc_dagger_or_rl_allowed": False,
        },
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    report_path = output_dir / "stage4_2r3c3t13s1_transition_forensics.json"
    _write_json(report_path, report)
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "report": {
            "path": report_path.name,
            "size_bytes": int(report_path.stat().st_size),
            "sha256": _sha256(report_path),
        },
        "raw_files_copied_or_modified": 0,
        "controller_ray_gotsc_tsc_or_plant_steps_executed": 0,
    }
    manifest_path = output_dir / "stage4_2r3c3t13s1_transition_forensics_manifest.json"
    _write_json(manifest_path, manifest)
    return {
        "output_dir": str(output_dir),
        "report_sha256": _sha256(report_path),
        "manifest_sha256": _sha256(manifest_path),
        "raw_inventory_digest": inventory["digest"],
        "official_route_unchanged": "SENTINEL_FAIL_STOP_IDENTIFICATION",
        "route_metrics": analysis["route_metrics"],
        "real_tsc_executed": False,
        "plant_steps_executed": 0,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main() -> None:
    print(json.dumps(run_audit(_parser().parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
