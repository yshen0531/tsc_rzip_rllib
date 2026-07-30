#!/usr/bin/env python3
"""No-TSC diagnostic for the Stage4.2R3c1 restart-controller failure.

The tool reads the completed R3c1 raw results in place on the server and
recomputes only controller actions.  It tests a prospective architecture:
preserve the exact phase-zero R17 path, but use the already frozen
target-error damping MPC immediately when a visible restart selects a
nonzero phase.  It never advances a plant or launches gotsc.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c1_authenticated_visible_manifold_phase_mpc as r3c,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _finite_range(values: Iterable[float]) -> dict[str, float | None]:
    array = np.asarray(
        [float(value) for value in values if math.isfinite(float(value))],
        dtype=float,
    )
    if not array.size:
        return {"minimum": None, "maximum": None, "mean": None}
    return {
        "minimum": float(np.min(array)),
        "maximum": float(np.max(array)),
        "mean": float(np.mean(array)),
    }


def _payload_for_source_case(
    ctx: r3c.Stage42R3C1Context,
    slew: float,
) -> dict[str, Any]:
    horizon = r3c._formal_horizon(slew)
    variant = f"slew_{slew:.3f}".replace(".", "p")
    return r3c.read_json(
        ctx.source_ctx.source_r1_run
        / "stage4_2r1_restart_variants"
        / f"source_{variant}_h{horizon}.payload.json"
    )


def _initial_state(
    state: Mapping[str, Any],
    *,
    wire_override: bool = False,
) -> dict[str, Any]:
    initial = {
        "step_index": 0,
        "R": float(state["R"]),
        "Z": float(state["Z"]),
        "Ip": float(state["Ip"]),
        "currents_a_tsc": list(state["coil_currents_a"]),
    }
    if wire_override:
        initial["wire_currents_a"] = [
            float(index + 1) * 1.0e9 for index in range(r3c.N_WIRES)
        ]
    return initial


def _group(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> dict[str, Any]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[key] for key in keys)].append(row)
    output = {}
    for values, members in sorted(groups.items(), key=lambda item: str(item[0])):
        label = "|".join(
            f"{key}={value}" for key, value in zip(keys, values)
        )
        output[label] = {
            "count": len(members),
            "observed_formal_pass_count": sum(
                bool(member["observed_formal_pass"]) for member in members
            ),
            "observed_immediate_damping_count": sum(
                bool(member["observed_first_phase_is_damping"])
                for member in members
            ),
            "prospective_regulation_selected_count": sum(
                bool(member["prospective_restart_regulation_selected"])
                for member in members
            ),
            "prospective_first_action_difference_from_observed": (
                _finite_range(
                    member[
                        "prospective_first_action_max_abs_difference_from_observed"
                    ]
                    for member in members
                )
            ),
            "first_observed_radial_position_derivative": _finite_range(
                member["observed_first_radial_position_derivative_m2_per_s"]
                for member in members
            ),
        }
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3b-run", required=True, type=Path)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    run_dir = args.run_dir.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if output == run_dir or run_dir in output.parents:
        raise SystemExit("diagnostic output must remain outside the run tree")

    ctx = r3c.load_stage42r3c1_config(
        args.config,
        source_stage42r3b_run=args.source_stage4_2r3b_run,
        run_dir_override=run_dir,
    )
    selected_pairs, state_by_id = r3c._recompute_selected_pairs(ctx)
    selected_by_id = {
        str(pair["pair_id"]): pair for pair in selected_pairs
    }
    specs = r3c.read_json(ctx.paths.source_reference / "control_specs.json")
    results = {
        str(result["experiment_id"]): result
        for result in (
            r3c.read_json_gz(path)
            for path in sorted((ctx.paths.control / "raw").glob("*.json.gz"))
        )
    }
    saved_rows = {
        str(row["experiment_id"]): row
        for row in r3c.read_json(ctx.paths.control / "results.json")
    }
    source_cases = r3c._source_controller_cases(ctx)
    library, bundle, selector = r3c.r1._library_bundle_selector(
        ctx.source_ctx.r1_ctx
    )

    by_source_key: dict[
        tuple[str, int, float], list[Mapping[str, Any]]
    ] = defaultdict(list)
    for spec in specs:
        by_source_key[
            (
                str(spec["target_id"]),
                int(spec["action_delay_steps"]),
                float(spec["slew_scale"]),
            )
        ].append(spec)

    rows: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    worker_count = 0
    for source_key in sorted(
        by_source_key, key=lambda key: (key[2], key[1], key[0])
    ):
        source = source_cases[source_key]
        payload = _payload_for_source_case(ctx, source_key[2])
        plant = r3c.r1.LocalPlantReplayWorker(
            payload,
            library,
            bundle,
            f"stage42r3c1_restart_regulation_diag_{worker_count:03d}",
            selector,
        )
        worker_count += 1
        try:
            source_spec = copy.deepcopy(source["spec"])
            source_spec["phase_alignment"] = copy.deepcopy(
                ctx.cfg["phase_alignment"]
            )
            source_spec["visible_reference_manifold"] = copy.deepcopy(
                by_source_key[source_key][0]["visible_reference_manifold"]
            )
            source_initial = copy.deepcopy(source["trajectory"][0])
            source_initial["step_index"] = 0
            source_controller = (
                r3c.AuthenticatedVisibleManifoldPhaseTaskController(
                    plant.base_worker,
                    bundle,
                    source_spec,
                    source_initial,
                )
            )
            source_action, source_trace = source_controller.action(
                source_initial
            )
            source_expected = np.asarray(
                source["trajectory"][1]["action_norm_tsc"], dtype=float
            ).reshape(r3c.N_COILS)
            source_rows.append(
                {
                    "target_id": source_key[0],
                    "actual_delay_steps": source_key[1],
                    "actual_slew_scale": source_key[2],
                    "selected_reference_phase": int(
                        source_controller.reference_phase_start
                    ),
                    "prospective_restart_regulation_selected": bool(
                        source_controller.reference_phase_start > 0
                    ),
                    "controller_phase": str(
                        source_trace["controller_phase"]
                    ),
                    "online_action_exact": bool(
                        np.array_equal(
                            np.asarray(source_action, dtype=float),
                            source_expected,
                        )
                    ),
                    "maximum_online_action_abs_difference": float(
                        np.max(
                            np.abs(
                                np.asarray(source_action, dtype=float)
                                - source_expected
                            )
                        )
                    ),
                }
            )

            for spec in sorted(
                by_source_key[source_key],
                key=lambda row: str(row["experiment_id"]),
            ):
                experiment_id = str(spec["experiment_id"])
                result = results[experiment_id]
                saved = saved_rows[experiment_id]
                state = state_by_id[
                    str(spec["state_generation_experiment_id"])
                ]
                initial = _initial_state(state)
                hidden_initial = _initial_state(state, wire_override=True)

                observed_controller = (
                    r3c.AuthenticatedVisibleManifoldPhaseTaskController(
                        plant.base_worker,
                        bundle,
                        spec,
                        initial,
                    )
                )
                observed_recomputed, observed_recomputed_trace = (
                    observed_controller.action(initial)
                )

                regulation_spec = copy.deepcopy(spec)
                regulation_spec.setdefault(
                    "terminal_model_phase_cap_step",
                    int(regulation_spec.get("terminal_template_step", 28)),
                )
                regulator = (
                    r3c.AuthenticatedVisibleManifoldPhaseTaskController(
                        plant.base_worker,
                        bundle,
                        regulation_spec,
                        initial,
                    )
                )
                prospective_action, prospective_trace = (
                    regulator._damping_action(
                        np.asarray(
                            initial["currents_a_tsc"], dtype=float
                        ).reshape(r3c.N_COILS)
                    )
                )
                hidden_regulator = (
                    r3c.AuthenticatedVisibleManifoldPhaseTaskController(
                        plant.base_worker,
                        bundle,
                        regulation_spec,
                        hidden_initial,
                    )
                )
                hidden_action, _ = hidden_regulator._damping_action(
                    np.asarray(
                        hidden_initial["currents_a_tsc"], dtype=float
                    ).reshape(r3c.N_COILS)
                )

                trajectory = list(result["trajectory"])
                observed_action = np.asarray(
                    trajectory[1]["action_norm_tsc"], dtype=float
                ).reshape(r3c.N_COILS)
                observed_trace = list(result["controller_trace"])[0]
                position = np.asarray(
                    [initial["R"], initial["Z"]], dtype=float
                )
                target = np.asarray(regulator.target[:2], dtype=float)
                first_position = np.asarray(
                    [trajectory[1]["R"], trajectory[1]["Z"]],
                    dtype=float,
                )
                dt_s = float(regulator.dt_s)
                first_velocity = (first_position - position) / dt_s
                position_error = position - target
                radial_derivative = float(
                    np.dot(position_error, first_velocity)
                )
                pair = selected_by_id[str(spec["pair_id"])]
                prospective_measurement = np.asarray(
                    prospective_trace["measurement_physical"], dtype=float
                )
                rows.append(
                    {
                        "experiment_id": experiment_id,
                        "pair_id": str(spec["pair_id"]),
                        "history_member": str(spec["history_member"]),
                        "target_id": str(spec["target_id"]),
                        "actual_delay_steps": int(
                            spec["action_delay_steps"]
                        ),
                        "actual_slew_scale": float(spec["slew_scale"]),
                        "common_prefix_steps": int(
                            pair["common_prefix_steps"]
                        ),
                        "reference_phase_start": int(
                            regulator.reference_phase_start
                        ),
                        "observed_formal_pass": bool(
                            saved["formal_contract_pass"]
                        ),
                        "observed_formal_minimum_signed_margin": float(
                            saved["formal_minimum_signed_margin"]
                        ),
                        "observed_first_controller_phase": str(
                            observed_trace["controller_phase"]
                        ),
                        "observed_first_phase_is_damping": bool(
                            observed_trace["controller_phase"]
                            == "phase_aligned_anticipatory_damping"
                        ),
                        "observed_first_action_recomputed_exact": bool(
                            np.array_equal(
                                np.asarray(
                                    observed_recomputed, dtype=float
                                ),
                                observed_action,
                            )
                        ),
                        "observed_first_action_recomputed_difference": float(
                            np.max(
                                np.abs(
                                    np.asarray(
                                        observed_recomputed, dtype=float
                                    )
                                    - observed_action
                                )
                            )
                        ),
                        "prospective_rule": (
                            "nonzero_visible_phase_uses_target_state_"
                            "regulation_from_task_step_zero"
                        ),
                        "prospective_restart_regulation_selected": bool(
                            regulator.reference_phase_start > 0
                        ),
                        "prospective_controller_phase": str(
                            prospective_trace["controller_phase"]
                        ),
                        "prospective_solver_success": bool(
                            prospective_trace["solver_success"]
                        ),
                        "prospective_measurement_physical": (
                            prospective_measurement.tolist()
                        ),
                        "prospective_step_zero_velocity_exact_zero": bool(
                            np.array_equal(
                                prospective_measurement[2:4],
                                np.zeros(2, dtype=float),
                            )
                        ),
                        "prospective_first_action_finite": bool(
                            np.all(np.isfinite(prospective_action))
                        ),
                        "prospective_first_action_max_abs": float(
                            np.max(np.abs(prospective_action))
                        ),
                        "prospective_first_action_max_abs_difference_from_observed": (
                            float(
                                np.max(
                                    np.abs(
                                        np.asarray(
                                            prospective_action, dtype=float
                                        )
                                        - observed_action
                                    )
                                )
                            )
                        ),
                        "prospective_hidden_wire_variant_exact": bool(
                            np.array_equal(
                                np.asarray(
                                    prospective_action, dtype=float
                                ),
                                np.asarray(hidden_action, dtype=float),
                            )
                        ),
                        "prospective_source_action_used": False,
                        "prospective_source_coil_current_used": False,
                        "prospective_source_wire_current_used": False,
                        "prospective_current_run_future_used": False,
                        "prospective_measurement_max_state_index_used": 0,
                        "initial_R_error_m": float(position_error[0]),
                        "initial_Z_error_m": float(position_error[1]),
                        "observed_first_vR_m_per_s": float(
                            first_velocity[0]
                        ),
                        "observed_first_vZ_m_per_s": float(
                            first_velocity[1]
                        ),
                        "observed_first_speed_m_per_s": float(
                            np.linalg.norm(first_velocity)
                        ),
                        "observed_first_radial_position_derivative_m2_per_s": (
                            radial_derivative
                        ),
                        "observed_first_motion_toward_target": bool(
                            radial_derivative < 0.0
                        ),
                        "observed_trace_recomputed_phase": str(
                            observed_recomputed_trace["controller_phase"]
                        ),
                    }
                )
        finally:
            plant.close()

    phase20 = [row for row in rows if row["reference_phase_start"] == 20]
    failures = [row for row in rows if not row["observed_formal_pass"]]
    diagnostic = {
        "schema_version": 1,
        "stage": r3c.STAGE,
        "purpose": (
            "no_tsc_restart_target_state_regulation_architecture_diagnostic"
        ),
        "run_dir": str(run_dir),
        "run_manifest_sha256": _sha256(ctx.paths.manifest),
        "control_raw_count": len(results),
        "real_tsc_executed": False,
        "plant_advanced": False,
        "prospective_design_not_yet_validated_by_tsc": True,
        "observed_result": {
            "formal_pass_count": sum(
                bool(row["observed_formal_pass"]) for row in rows
            ),
            "formal_failure_count": len(failures),
            "reference_phase_counts": dict(
                sorted(
                    Counter(
                        row["reference_phase_start"] for row in rows
                    ).items()
                )
            ),
            "first_controller_phase_counts": dict(
                sorted(
                    Counter(
                        row["observed_first_controller_phase"]
                        for row in rows
                    ).items()
                )
            ),
            "phase20_count": len(phase20),
            "phase20_formal_pass_count": sum(
                bool(row["observed_formal_pass"]) for row in phase20
            ),
            "phase20_immediate_damping_count": sum(
                bool(row["observed_first_phase_is_damping"])
                for row in phase20
            ),
            "first_speed_m_per_s": _finite_range(
                row["observed_first_speed_m_per_s"] for row in rows
            ),
            "first_motion_toward_target_count": sum(
                bool(row["observed_first_motion_toward_target"])
                for row in rows
            ),
        },
        "prospective_action_recomputation": {
            "rule": (
                "phase_zero_preserves_existing_R17_controller; "
                "nonzero visible phase starts frozen target-error damping MPC"
            ),
            "development_case_count": len(rows),
            "nonzero_phase_regulation_selected_count": sum(
                bool(row["prospective_restart_regulation_selected"])
                for row in rows
            ),
            "finite_first_action_count": sum(
                bool(row["prospective_first_action_finite"]) for row in rows
            ),
            "solver_success_count": sum(
                bool(row["prospective_solver_success"]) for row in rows
            ),
            "zero_velocity_bootstrap_count": sum(
                bool(row["prospective_step_zero_velocity_exact_zero"])
                for row in rows
            ),
            "hidden_wire_invariant_count": sum(
                bool(row["prospective_hidden_wire_variant_exact"])
                for row in rows
            ),
            "observed_action_recomputation_exact_count": sum(
                bool(row["observed_first_action_recomputed_exact"])
                for row in rows
            ),
            "source_action_use_count": 0,
            "source_coil_current_use_count": 0,
            "source_wire_current_use_count": 0,
            "current_run_future_use_count": 0,
            "first_action_max_abs": _finite_range(
                row["prospective_first_action_max_abs"] for row in rows
            ),
            "first_action_difference_from_observed": _finite_range(
                row[
                    "prospective_first_action_max_abs_difference_from_observed"
                ]
                for row in rows
            ),
        },
        "original_start_preservation": {
            "source_case_count": len(source_rows),
            "phase_zero_count": sum(
                row["selected_reference_phase"] == 0
                for row in source_rows
            ),
            "prospective_regulation_selected_count": sum(
                bool(row["prospective_restart_regulation_selected"])
                for row in source_rows
            ),
            "online_action_exact_count": sum(
                bool(row["online_action_exact"]) for row in source_rows
            ),
            "maximum_action_abs_difference": max(
                (
                    float(row["maximum_online_action_abs_difference"])
                    for row in source_rows
                ),
                default=math.inf,
            ),
        },
        "grouped_observed_and_action_diagnostic": {
            "by_prefix_target_actuator": _group(
                rows,
                (
                    "common_prefix_steps",
                    "target_id",
                    "actual_delay_steps",
                    "actual_slew_scale",
                ),
            ),
            "by_reference_phase": _group(
                rows, ("reference_phase_start",)
            ),
        },
        "source_rows": source_rows,
        "control_rows": rows,
        "interpretation_guardrails": {
            "runtime_error_diagnosis": False,
            "plant_restart_failure_diagnosis": False,
            "reporting_error_diagnosis": False,
            "supports_new_controller_identity": True,
            "counterfactual_closed_loop_pass_claimed": False,
            "independent_hidden_history_robustness_claimed": False,
            "formal_gate_change_allowed": False,
        },
    }

    expected = 32
    checks = diagnostic["prospective_action_recomputation"]
    source_check = diagnostic["original_start_preservation"]
    diagnostic["diagnostic_passed"] = bool(
        len(rows) == expected
        and len(results) == expected
        and checks["nonzero_phase_regulation_selected_count"] == expected
        and checks["finite_first_action_count"] == expected
        and checks["solver_success_count"] == expected
        and checks["zero_velocity_bootstrap_count"] == expected
        and checks["hidden_wire_invariant_count"] == expected
        and checks["observed_action_recomputation_exact_count"] == expected
        and source_check["source_case_count"] == 4
        and source_check["phase_zero_count"] == 4
        and source_check["prospective_regulation_selected_count"] == 0
        and source_check["online_action_exact_count"] == 4
        and source_check["maximum_action_abs_difference"] == 0.0
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    r3c.atomic_write_json(output, diagnostic)
    print(
        json.dumps(
            {
                "output": str(output),
                "output_sha256": _sha256(output),
                "diagnostic_passed": diagnostic["diagnostic_passed"],
                "control_count": len(rows),
                "source_count": len(source_rows),
                "real_tsc_executed": False,
                "prospective": checks,
                "original_start": source_check,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
