#!/usr/bin/env python3
"""Authenticate S21 raw and test its frozen four-direction affine authority.

This tool is read-only with respect to S21.  It executes no controller, Ray,
gotsc, TSC, plant step, or snapshot operation.  The only optimization is the
preregistered bounded four-coefficient synthetic trajectory discriminator.
"""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Mapping, Sequence

import numpy as np
from scipy.optimize import differential_evolution

STAGE = "Stage4.2R3c3T13S22"
IDENTITY = "full_horizon_state10_four_direction_affine_authority_v1"
S21_STAGE = "Stage4.2R3c3T13S21"
S21_CONTROLLER = (
    "stage4_2r3c3t13s21_cumulative_exact_card15_pooled_observer_campaign"
)
BASELINE_PROBE_ID = "lattice_baseline"
DIRECTIONS = (
    "mode0_coil8_component",
    "mode0_without_coil8",
    "mode1",
    "mode2",
)
PHASE_AUDITS = (
    "training_baseline_gate.json",
    "training_probe_execution.json",
    "calibration_baseline_gate.json",
    "calibration_probe_execution.json",
    "holdout_baseline_gate.json",
    "holdout_probe_execution.json",
)
s21: Any = None


def _load_s21_module() -> Any:
    """Delay the Unix-only historical import chain until the server audit."""
    global s21
    if s21 is None:
        from tsc_rzip_rllib.diagnostics import (
            stage4_2r3c3t13s21_cumulative_exact_card15_pooled_observer_campaign
            as loaded,
        )

        s21 = loaded
    return s21


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: Any) -> str:
    text = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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


def _validate_design(cfg: Mapping[str, Any]) -> None:
    source = cfg["source_contract"]
    response = cfg["response_contract"]
    formal = cfg["formal_contract"]
    optimizer = cfg["optimizer_contract"]
    gate = cfg["primary_gate"]
    execution = cfg["execution_contract"]
    scope = cfg["scientific_scope"]
    if (
        int(cfg.get("schema_version", -1)) != 1
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or str(source["s21_package_commit"]) != "98dc353"
        or int(source["s21_raw_count"]) != 360
        or int(source["s21_raw_total_bytes"]) != 21083271
        or int(source["expected_baseline_formal_pass_count"]) != 16
        or int(source["expected_probe_formal_pass_count"]) != 99
        or tuple(response["context_key_fields"]) != ("pair_id", "history_member")
        or int(response["expected_context_count"]) != 40
        or int(response["expected_baseline_count"]) != 40
        or int(response["expected_signed_probe_count"]) != 320
        or int(response["signed_probes_per_context"]) != 8
        or response["baseline_probe_id"] != BASELINE_PROBE_ID
        or tuple(response["ordered_directions"]) != DIRECTIONS
        or int(response["first_response_effect_state"]) != 11
        or float(response["dt_s"]) != 0.01
        or tuple(response["output_fields"]) != ("R", "Z", "vR", "vZ", "Ip")
        or tuple(map(float, response["even_residual_caps"]))
        != (0.003, 0.003, 0.01, 0.01, 1000.0)
        or float(response["coefficient_lower_bound"]) != -1.0
        or float(response["coefficient_upper_bound"]) != 1.0
        or bool(response["allow_direction_rescaling"])
        or bool(response["allow_new_basis"])
        or bool(response["allow_per_step_coefficients"])
        or bool(response["allow_source_or_current_future"])
        or int(formal["normal_arrival_deadline_step"]) != 25
        or int(formal["normal_hold_through_step"]) != 35
        or int(formal["weak_arrival_deadline_step"]) != 27
        or int(formal["weak_hold_through_step"]) != 37
        or float(formal["position_tolerance_m"]) != 0.03
        or float(formal["speed_tolerance_m_per_s"]) != 0.1
        or float(formal["ip_tolerance_A"]) != 10000.0
        or int(formal["arrival_streak_steps"]) != 3
        or float(formal["formal_pass_tolerance"]) != 1e-12
        or float(formal["metric_equivalence_tolerance"]) != 1e-12
        or bool(formal["arrival_deadline_expansion_allowed"])
        or optimizer["algorithm"] != "scipy_differential_evolution"
        or int(optimizer["seed"]) != 4201322
        or int(optimizer["population_multiplier"]) != 16
        or int(optimizer["maximum_generations"]) != 300
        or float(optimizer["absolute_tolerance"]) != 1e-10
        or float(optimizer["relative_tolerance"]) != 1e-10
        or not bool(optimizer["polish"])
        or int(optimizer["workers"]) != 1
        or optimizer["updating"] != "immediate"
        or float(optimizer["coefficient_bound_tolerance"]) != 1e-10
        or not bool(optimizer["independent_forward_evaluation"])
        or any(int(value) != expected for value, expected in zip(
            (
                gate["source_raw_authentication_required"],
                gate["baseline_formal_reproduction_required"],
                gate["measured_probe_formal_reproduction_required"],
                gate["finite_direction_construction_required"],
                gate["optimizer_completion_required"],
                gate["independent_check_required"],
                gate["optimistic_affine_formal_feasibility_required"],
            ),
            (360, 40, 320, 40, 40, 40, 40),
        ))
        or not bool(execution["server_side_only_for_large_raw"])
        or not bool(execution["read_raw_in_place"])
        or int(execution["new_raw_count"]) != 0
        or bool(execution["ray_executed"])
        or bool(execution["gotsc_executed"])
        or bool(execution["tsc_executed"])
        or int(execution["plant_steps_executed"]) != 0
        or bool(execution["controller_executed"])
        or bool(execution["snapshot_creation_allowed"])
        or bool(scope["affine_combination_is_assumed_physically_realizable"])
        or bool(scope["s21_result_changed"])
        or bool(scope["real_mpc_executed"])
        or bool(scope["global_plant_reachability_claimed"])
        or bool(scope["hidden_history_robustness_claimed"])
        or bool(scope["probe_trajectories_are_demonstrations"])
        or bool(scope["bc_dagger_or_rl_allowed"])
    ):
        raise ValueError("T13S22 frozen design changed")


def _context_key(spec: Mapping[str, Any]) -> tuple[str, str]:
    return str(spec["pair_id"]), str(spec["history_member"])


def _trajectory_rzi(result: Mapping[str, Any]) -> np.ndarray:
    output = np.asarray(
        [[row["R"], row["Z"], row["Ip"]] for row in result["trajectory"]],
        dtype=float,
    )
    if output.ndim != 2 or output.shape[1] != 3 or not np.all(np.isfinite(output)):
        raise ValueError("non-finite or malformed R/Z/Ip trajectory")
    return output


def _outputs5(rzi: np.ndarray, dt_s: float) -> np.ndarray:
    rzi = np.asarray(rzi, dtype=float)
    velocity = np.zeros((len(rzi), 2), dtype=float)
    if len(rzi) > 1:
        velocity[1:] = np.diff(rzi[:, :2], axis=0) / float(dt_s)
    return np.column_stack((rzi[:, 0], rzi[:, 1], velocity, rzi[:, 2]))


def _construct_responses(
    baseline: Mapping[str, Any],
    probes: Mapping[tuple[str, int], Mapping[str, Any]],
    *,
    effect_start: int,
    dt_s: float,
) -> dict[str, Any]:
    y0 = _trajectory_rzi(baseline)
    odd = []
    even5 = []
    rows = []
    for direction in DIRECTIONS:
        plus = _trajectory_rzi(probes[(direction, 1)])
        minus = _trajectory_rzi(probes[(direction, -1)])
        if plus.shape != y0.shape or minus.shape != y0.shape:
            raise ValueError("S21 signed response trajectory shape mismatch")
        r_plus = plus - y0
        r_minus = minus - y0
        g = 0.5 * (r_plus - r_minus)
        h = 0.5 * (r_plus + r_minus)
        g[:effect_start] = 0.0
        h5 = _outputs5(y0 + h, dt_s) - _outputs5(y0, dt_s)
        odd.append(g)
        even5.append(h5)
        rows.append({
            "direction": direction,
            "plus_experiment_id": probes[(direction, 1)]["experiment_id"],
            "minus_experiment_id": probes[(direction, -1)]["experiment_id"],
            "maximum_absolute_even_residual": np.max(
                np.abs(h5[effect_start:]), axis=0
            ).tolist(),
        })
    odd_array = np.stack(odd, axis=0)
    even_array = np.stack(even5, axis=0)
    if not np.all(np.isfinite(odd_array)) or not np.all(np.isfinite(even_array)):
        raise ValueError("non-finite affine response construction")
    return {
        "baseline_rzi": y0,
        "odd_rzi": odd_array,
        "even_outputs5": even_array,
        "direction_rows": rows,
    }


def _synthetic_result(
    baseline: Mapping[str, Any], rzi: np.ndarray
) -> dict[str, Any]:
    output = dict(baseline)
    trajectory = []
    for source, values in zip(baseline["trajectory"], np.asarray(rzi, dtype=float)):
        row = dict(source)
        row["R"], row["Z"], row["Ip"] = map(float, values)
        trajectory.append(row)
    output["trajectory"] = trajectory
    output["success"] = True
    output["failure_reason"] = ""
    return output


@dataclass(frozen=True)
class FormalEvaluator:
    """Fast algebraic evaluator exactly matching the frozen R8 metric."""

    r8: Any
    r8_ctx: Any
    policy: Mapping[str, Any]
    target: np.ndarray
    gate: Mapping[str, Any]
    dt_s: float

    @classmethod
    def from_context(
        cls, ctx: s21.Context, spec: Mapping[str, Any]
    ) -> "FormalEvaluator":
        base = ctx.base_ctx.base_ctx.base_ctx.base_ctx.base_ctx.source_ctx.source_ctx
        r3b = s21.s16.s9.t11.t1.r3b
        r13_ctx = r3b.r1._r13_ctx(base.r1_ctx)
        policy = r3b.r1.r13._timing_policy(
            r13_ctx,
            float(spec["slew_scale"]),
            policy_id=(
                f"s22_{spec['pair_id']}_{spec['history_member']}_"
                f"{spec['target_id']}_{spec['action_delay_steps']}_"
                f"{spec['slew_scale']}"
            ),
        )
        r8 = r3b.r1.r8
        r8_ctx = r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx
        metric_ctx = SimpleNamespace(
            cfg=copy.deepcopy(
                r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34.cfg
            ),
            env_cfg=r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34.env_cfg,
        )
        metric_ctx.cfg["gate"].update(copy.deepcopy(r8_ctx.cfg["gate"]))
        target = r8.s34.target_absolute(metric_ctx, r8._target_task(spec))
        dt_s = float(metric_ctx.env_cfg["dt_ms"]) / 1000.0
        return cls(
            r8=r8,
            r8_ctx=r8_ctx,
            policy=policy,
            target=np.asarray(target, dtype=float),
            gate=r8_ctx.cfg["gate"],
            dt_s=dt_s,
        )

    def evaluate(self, rzi: np.ndarray) -> dict[str, Any]:
        y = np.asarray(rzi, dtype=float)
        horizon = len(y) - 1
        if horizon != int(self.policy["horizon_steps"]):
            raise ValueError("synthetic affine horizon changed")
        error = y - self.target[None, :]
        speed = np.linalg.norm(
            self.r8._velocity_components(y, self.dt_s), axis=1
        )
        gate = self.gate
        ip_cfg = gate["ip_tracking"]
        terminal_ip_margin = 1.0 - abs(error[-1, 2]) / float(
            ip_cfg["terminal_abs_tolerance_A"]
        )
        endpoint_rows = []
        for endpoint in map(int, self.policy["allowed_arrival_steps"]):
            if endpoint > horizon:
                continue
            hard = self.r8.s32._endpoint_constraints_signed(
                error=error,
                speed=speed,
                endpoint=endpoint,
                horizon=horizon,
                tolerance=float(gate["precise_tolerance_m"]),
                endpoint_speed_limit=float(
                    gate["terminal_velocity_max_m_per_s"]
                ),
                rms_speed_limit=float(gate["late_velocity_rms_max_m_per_s"]),
                late_window_steps=int(gate["late_window_steps"]),
                ip_tolerance=float(gate["ip_safety_tolerance_A"]),
                streak_steps=int(gate["required_arrival_streak_steps"]),
                dt_ms=int(round(self.dt_s * 1000.0)),
            )
            window_start = int(hard["window_start_step"])
            hold_ip = error[window_start:, 2]
            ip_margins = np.asarray(
                [
                    terminal_ip_margin,
                    1.0
                    - float(np.sqrt(np.mean(hold_ip**2)))
                    / float(ip_cfg["hold_rms_tolerance_A"]),
                    1.0
                    - float(np.max(np.abs(hold_ip)))
                    / float(ip_cfg["sustained_max_tolerance_A"]),
                ],
                dtype=float,
            )
            combined = np.concatenate(
                [[float(hard["minimum_signed_margin"])], ip_margins]
            )
            endpoint_rows.append(
                {
                    "endpoint_step": endpoint,
                    "arrival_time_ms": int(hard["arrival_time_ms"]),
                    "pass": bool(
                        hard.get("pass", False) and np.min(ip_margins) >= -1e-12
                    ),
                    "minimum_signed_margin": float(np.min(combined)),
                    "mean_signed_margin": float(np.mean(combined)),
                }
            )
        passing = [row for row in endpoint_rows if row["pass"]]
        pool = passing if passing else endpoint_rows
        chosen = max(
            pool,
            key=lambda row: (
                float(row["minimum_signed_margin"]),
                float(row["mean_signed_margin"]),
                -int(row["endpoint_step"]),
            ),
        )
        return {
            "formal_contract_pass": bool(chosen["pass"]),
            "formal_minimum_signed_margin": float(
                chosen["minimum_signed_margin"]
            ),
            "formal_mean_signed_margin": float(chosen["mean_signed_margin"]),
            "formal_best_arrival_ms": int(chosen["arrival_time_ms"]),
        }

    def exact_existing_metric(
        self, baseline: Mapping[str, Any], rzi: np.ndarray
    ) -> dict[str, Any]:
        formal = self.r8.tracking_metrics(
            self.r8_ctx,
            _synthetic_result(baseline, rzi),
            self.policy,
        )
        return {
            "formal_contract_pass": bool(
                formal["stage3_4_target_tracking_pass"]
            ),
            "formal_minimum_signed_margin": float(
                formal["stage3_4_tracking_minimum_signed_margin"]
            ),
            "formal_mean_signed_margin": float(
                formal["stage3_4_tracking_mean_signed_margin"]
            ),
            "formal_best_arrival_ms": int(
                formal["stage3_4_best_endpoint_ms"]
            ),
        }


def _optimize_context(
    baseline: Mapping[str, Any],
    constructed: Mapping[str, Any],
    evaluator: FormalEvaluator,
    cfg: Mapping[str, Any],
) -> dict[str, Any]:
    y0 = np.asarray(constructed["baseline_rzi"], dtype=float)
    odd = np.asarray(constructed["odd_rzi"], dtype=float)
    lower = float(cfg["response_contract"]["coefficient_lower_bound"])
    upper = float(cfg["response_contract"]["coefficient_upper_bound"])
    optimizer = cfg["optimizer_contract"]

    def forward(alpha: Sequence[float]) -> np.ndarray:
        return y0 + np.tensordot(np.asarray(alpha, dtype=float), odd, axes=(0, 0))

    def objective(alpha: np.ndarray) -> float:
        return -float(
            evaluator.evaluate(forward(alpha))["formal_minimum_signed_margin"]
        )

    result = differential_evolution(
        objective,
        [(lower, upper)] * len(DIRECTIONS),
        seed=int(optimizer["seed"]),
        popsize=int(optimizer["population_multiplier"]),
        maxiter=int(optimizer["maximum_generations"]),
        atol=float(optimizer["absolute_tolerance"]),
        tol=float(optimizer["relative_tolerance"]),
        polish=bool(optimizer["polish"]),
        workers=int(optimizer["workers"]),
        updating=str(optimizer["updating"]),
    )
    alpha = np.asarray(result.x, dtype=float)
    optimized_rzi = forward(alpha)
    fast = evaluator.evaluate(optimized_rzi)
    exact = evaluator.exact_existing_metric(baseline, optimized_rzi)
    bound_tolerance = float(optimizer["coefficient_bound_tolerance"])
    metric_tolerance = float(cfg["formal_contract"]["metric_equivalence_tolerance"])
    pass_tolerance = float(cfg["formal_contract"]["formal_pass_tolerance"])
    coefficient_check = bool(
        alpha.shape == (4,)
        and np.all(np.isfinite(alpha))
        and np.all(alpha >= lower - bound_tolerance)
        and np.all(alpha <= upper + bound_tolerance)
    )
    metric_check = bool(
        fast["formal_contract_pass"] == exact["formal_contract_pass"]
        and fast["formal_best_arrival_ms"] == exact["formal_best_arrival_ms"]
        and abs(
            fast["formal_minimum_signed_margin"]
            - exact["formal_minimum_signed_margin"]
        )
        <= metric_tolerance
        and abs(
            fast["formal_mean_signed_margin"]
            - exact["formal_mean_signed_margin"]
        )
        <= metric_tolerance
    )
    normal_return = bool(
        alpha.shape == (4,)
        and np.all(np.isfinite(alpha))
        and math.isfinite(float(result.fun))
        and np.all(np.isfinite(optimized_rzi))
    )
    independent_check = bool(normal_return and coefficient_check and metric_check)
    feasible = bool(
        independent_check
        and exact["formal_contract_pass"]
        and exact["formal_minimum_signed_margin"] >= -pass_tolerance
    )
    return {
        "coefficients": {
            direction: float(value)
            for direction, value in zip(DIRECTIONS, alpha)
        },
        "optimizer_normal_return": normal_return,
        "optimizer_reported_success": bool(result.success),
        "optimizer_message": str(result.message),
        "optimizer_generations": int(result.nit),
        "optimizer_evaluations": int(result.nfev),
        "optimizer_objective": float(result.fun),
        "coefficient_check": coefficient_check,
        "fast_forward_formal": fast,
        "independent_existing_formal": exact,
        "metric_equivalence_check": metric_check,
        "independent_check": independent_check,
        "optimistic_affine_formal_feasible": feasible,
    }


def _phase_formal_map(run_dir: Path) -> tuple[dict[str, bool], dict[str, str]]:
    rows: dict[str, bool] = {}
    hashes: dict[str, str] = {}
    for name in PHASE_AUDITS:
        path = run_dir / "analysis" / name
        hashes[name] = _sha256(path)
        payload = _read_json(path)
        audit = payload["execution_audit"]
        if not bool(audit["passed"]):
            raise ValueError(f"S21 phase audit is not complete: {name}")
        for row in audit["rows"]:
            experiment_id = str(row["experiment_id"])
            if experiment_id in rows:
                raise ValueError("duplicate experiment in S21 phase audits")
            rows[experiment_id] = bool(
                row["formal_contract_pass_diagnostic"]
            )
    if len(rows) != 360:
        raise ValueError("S21 phase audit coverage changed")
    return rows, hashes


def _source_file_paths(run_dir: Path) -> dict[str, Path]:
    return {
        "manifest": run_dir / "stage4_2r3c3t13s21_manifest.json",
        "final_state": run_dir / "stage4_2r3c3t13s21_state.json",
        "training_model": run_dir / "model" / "training_pooled_observer.json",
        "calibrated_tube": run_dir / "model" / "calibrated_response_tube.json",
        "final_result": run_dir / "final_result.json",
        "independent_postprocess": run_dir / "server_independent_postprocess.json",
        "final_audit": run_dir / "server_final_audit.json",
    }


def _authenticate_source(
    ctx: s21.Context,
    config_path: Path,
    cfg: Mapping[str, Any],
) -> dict[str, Any]:
    source = cfg["source_contract"]
    run_dir = ctx.paths.run_dir
    if run_dir.name != str(source["s21_run_name"]):
        raise ValueError("immutable S21 run name mismatch")
    local_implementation = Path(s21.__file__).resolve()
    if (
        _sha256(ctx.config_path) != str(source["s21_config_sha256"])
        or _sha256(local_implementation)
        != str(source["s21_implementation_sha256"])
    ):
        raise ValueError("deployed S21 config or implementation changed")
    paths = _source_file_paths(run_dir)
    expected = {
        "manifest": source["s21_manifest_sha256"],
        "final_state": source["s21_final_state_sha256"],
        "training_model": source["s21_training_model_sha256"],
        "calibrated_tube": source["s21_calibrated_tube_sha256"],
        "final_result": source["s21_final_result_sha256"],
        "independent_postprocess": source[
            "s21_independent_postprocess_sha256"
        ],
        "final_audit": source["s21_final_audit_sha256"],
    }
    hashes = {name: _sha256(path) for name, path in paths.items()}
    if any(hashes[name] != str(value) for name, value in expected.items()):
        raise ValueError("immutable S21 compact artifact SHA-256 mismatch")
    state = _read_json(paths["final_state"])
    final_audit = _read_json(paths["final_audit"])
    if (
        state.get("phase_status") != "campaign_complete"
        or not bool(state.get("finished"))
        or not bool(state.get("primary_pass"))
        or int(state.get("new_raw_count", -1)) != 360
        or not bool(final_audit.get("passed"))
    ):
        raise ValueError("S21 final campaign state changed")
    inventory = s21._raw_inventory(ctx)
    if (
        int(inventory["count"]) != int(source["s21_raw_count"])
        or int(inventory["total_bytes"]) != int(source["s21_raw_total_bytes"])
        or inventory["digest"] != str(source["s21_raw_inventory_digest"])
        or final_audit["raw_inventory"]["digest"] != inventory["digest"]
    ):
        raise ValueError("S21 raw inventory mismatch")
    phase_map, phase_hashes = _phase_formal_map(run_dir)
    return {
        "design_config_sha256": _sha256(config_path),
        "s21_config_sha256": _sha256(ctx.config_path),
        "s21_implementation_sha256": _sha256(local_implementation),
        "source_file_hashes": hashes,
        "phase_audit_hashes": phase_hashes,
        "raw_inventory": inventory,
        "phase_formal_map": phase_map,
    }


def _load_and_authenticate_raw(
    ctx: s21.Context,
    phase_map: Mapping[str, bool],
) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[str, Any]]:
    contexts: dict[tuple[str, str], dict[str, Any]] = {}
    baseline_reproduced = 0
    probe_reproduced = 0
    baseline_pass = 0
    probe_pass = 0
    for path in sorted(ctx.paths.raw.glob("*.json.gz")):
        raw = _read_json_gz(path)
        spec = raw.get("spec") or {}
        experiment_id = str(raw.get("experiment_id"))
        if (
            raw.get("stage") != S21_STAGE
            or raw.get("controller_revision")
            != "cumulative_exact_card15_calibration_probe_v42r3c3t13s21_v1"
            or not bool(raw.get("success"))
            or experiment_id not in phase_map
            or len(raw.get("trajectory") or [])
            != int(spec.get("horizon_steps", -2)) + 1
            or len(raw.get("controller_trace") or [])
            != int(spec.get("horizon_steps", -1))
            or any(bool(row.get("abnormal")) for row in raw["trajectory"])
        ):
            raise ValueError(f"S21 raw identity/runtime mismatch: {path.name}")
        key = _context_key(spec)
        bucket = contexts.setdefault(key, {"baseline": None, "probes": {}})
        probe_id = str(spec["r3c3_probe_id"])
        direction = str(spec["r3c3_probe_direction"])
        sign = int(spec["r3c3_probe_sign"])
        evaluator = FormalEvaluator.from_context(ctx, spec)
        recomputed = evaluator.exact_existing_metric(raw, _trajectory_rzi(raw))
        reported = bool(phase_map[experiment_id])
        if recomputed["formal_contract_pass"] != reported:
            raise ValueError(
                f"S21 reported/raw formal mismatch: {experiment_id}"
            )
        raw["_s22_formal"] = recomputed
        raw["_s22_raw_sha256"] = _sha256(path)
        if probe_id == BASELINE_PROBE_ID:
            if direction or sign != 0 or bucket["baseline"] is not None:
                raise ValueError("S21 baseline matrix changed")
            bucket["baseline"] = raw
            baseline_reproduced += 1
            baseline_pass += int(recomputed["formal_contract_pass"])
        else:
            if direction not in DIRECTIONS or sign not in (-1, 1):
                raise ValueError("S21 signed direction matrix changed")
            probe_key = (direction, sign)
            if probe_key in bucket["probes"]:
                raise ValueError("duplicate S21 signed probe")
            bucket["probes"][probe_key] = raw
            probe_reproduced += 1
            probe_pass += int(recomputed["formal_contract_pass"])
    expected_keys = {(direction, sign) for direction in DIRECTIONS for sign in (-1, 1)}
    if (
        len(contexts) != 40
        or baseline_reproduced != 40
        or probe_reproduced != 320
        or any(
            row["baseline"] is None or set(row["probes"]) != expected_keys
            for row in contexts.values()
        )
    ):
        raise ValueError("S21 context/probe coverage changed")
    return contexts, {
        "baseline_formal_reproduction_count": baseline_reproduced,
        "measured_probe_formal_reproduction_count": probe_reproduced,
        "baseline_formal_pass_count": baseline_pass,
        "measured_probe_formal_pass_count": probe_pass,
    }


def _primary_gate_counts(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "finite_direction_construction": sum(
            bool(row["finite_direction_construction"]) for row in rows
        ),
        "optimizer_completion": sum(
            bool(row["optimizer"]["optimizer_normal_return"]) for row in rows
        ),
        "independent_check": sum(
            bool(row["optimizer"]["independent_check"]) for row in rows
        ),
        "optimistic_affine_formal_feasibility": sum(
            bool(row["optimizer"]["optimistic_affine_formal_feasible"])
            for row in rows
        ),
    }


def _route_from_counts(
    source_count: int,
    reproduction: Mapping[str, int],
    primary: Mapping[str, int],
    cfg: Mapping[str, Any],
) -> tuple[bool, str]:
    gate = cfg["primary_gate"]
    passed = bool(
        source_count == int(gate["source_raw_authentication_required"])
        and reproduction["baseline_formal_reproduction_count"]
        == int(gate["baseline_formal_reproduction_required"])
        and reproduction["measured_probe_formal_reproduction_count"]
        == int(gate["measured_probe_formal_reproduction_required"])
        and primary["finite_direction_construction"]
        == int(gate["finite_direction_construction_required"])
        and primary["optimizer_completion"]
        == int(gate["optimizer_completion_required"])
        and primary["independent_check"]
        == int(gate["independent_check_required"])
        and primary["optimistic_affine_formal_feasibility"]
        == int(gate["optimistic_affine_formal_feasibility_required"])
    )
    return passed, str(cfg["routes"]["pass" if passed else "fail"])


def run_audit(args: argparse.Namespace) -> dict[str, Any]:
    _load_s21_module()
    config_path = args.config.expanduser().resolve()
    cfg = _read_json(config_path)
    _validate_design(cfg)
    source_run = args.source_s21_run.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if output.exists():
        raise ValueError("T13S22 output directory must be new")
    if output == source_run or source_run in output.parents:
        raise ValueError("T13S22 output must remain outside immutable S21 evidence")
    ctx = s21.load_config(
        args.source_s21_config.expanduser().resolve(),
        source_stage42r3b_run=args.source_stage42r3b_run,
        source_stage42r3c3_run=args.source_stage42r3c3_run,
        source_stage42r3c3_bank_dir=args.source_stage42r3c3_bank_dir,
        source_stage42r3c3t1_run=args.source_stage42r3c3t1_run,
        source_stage42r3c3t1_audit_dir=args.source_stage42r3c3t1_audit_dir,
        source_stage42r3c3t3_controller_bank=(
            args.source_stage42r3c3t3_controller_bank
        ),
        q1_run=args.q1_run,
        q2_run=args.q2_run,
        q1_audit=args.q1_audit,
        q2_audit=args.q2_audit,
        r3b_server_audit=args.r3b_server_audit,
        r3b_snapshot_checks=args.r3b_snapshot_checks,
        run_dir=source_run,
    )
    authenticated = _authenticate_source(ctx, config_path, cfg)
    contexts, reproduction = _load_and_authenticate_raw(
        ctx, authenticated["phase_formal_map"]
    )
    source = cfg["source_contract"]
    if (
        reproduction["baseline_formal_pass_count"]
        != int(source["expected_baseline_formal_pass_count"])
        or reproduction["measured_probe_formal_pass_count"]
        != int(source["expected_probe_formal_pass_count"])
    ):
        raise ValueError("S21 frozen formal pass counts changed")

    caps = np.asarray(
        cfg["response_contract"]["even_residual_caps"], dtype=float
    )
    effect_start = int(
        cfg["response_contract"]["first_response_effect_state"]
    )
    rows = []
    for key in sorted(contexts):
        group = contexts[key]
        baseline = group["baseline"]
        constructed = _construct_responses(
            baseline,
            group["probes"],
            effect_start=effect_start,
            dt_s=float(cfg["response_contract"]["dt_s"]),
        )
        even_max = np.max(
            np.abs(constructed["even_outputs5"][:, effect_start:, :]),
            axis=(0, 1),
        )
        finite = bool(
            np.all(np.isfinite(constructed["baseline_rzi"]))
            and np.all(np.isfinite(constructed["odd_rzi"]))
            and np.all(np.isfinite(constructed["even_outputs5"]))
        )
        evaluator = FormalEvaluator.from_context(ctx, baseline["spec"])
        optimized = _optimize_context(
            baseline, constructed, evaluator, cfg
        )
        rows.append(
            {
                "pair_id": key[0],
                "history_member": key[1],
                "partition": baseline["spec"]["partition"],
                "target_id": baseline["spec"]["target_id"],
                "actual_delay_steps": int(
                    baseline["spec"]["action_delay_steps"]
                ),
                "actual_slew_scale": float(baseline["spec"]["slew_scale"]),
                "horizon_steps": int(baseline["spec"]["horizon_steps"]),
                "baseline_experiment_id": baseline["experiment_id"],
                "baseline_raw_sha256": baseline["_s22_raw_sha256"],
                "baseline_formal": baseline["_s22_formal"],
                "measured_probe_formal_pass_count": sum(
                    bool(value["_s22_formal"]["formal_contract_pass"])
                    for value in group["probes"].values()
                ),
                "finite_direction_construction": finite,
                "direction_rows": constructed["direction_rows"],
                "maximum_absolute_even_residual": even_max.tolist(),
                "even_residual_caps": caps.tolist(),
                "even_residual_cap_pass_by_component": (
                    even_max <= caps + 1e-12
                ).tolist(),
                "even_residual_all_caps_pass": bool(
                    np.all(even_max <= caps + 1e-12)
                ),
                "optimizer": optimized,
            }
        )
    primary = _primary_gate_counts(rows)
    source_count = int(authenticated["raw_inventory"]["count"])
    primary_pass, route = _route_from_counts(
        source_count, reproduction, primary, cfg
    )
    global_even_max = np.max(
        np.asarray(
            [row["maximum_absolute_even_residual"] for row in rows],
            dtype=float,
        ),
        axis=0,
    )
    provenance = {
        "stage": STAGE,
        "identity": IDENTITY,
        "design_config_sha256": authenticated["design_config_sha256"],
        "source_s21_run": str(source_run),
        "source_file_hashes": authenticated["source_file_hashes"],
        "phase_audit_hashes": authenticated["phase_audit_hashes"],
        "s21_raw_inventory_digest": authenticated["raw_inventory"]["digest"],
        "formal_timing_changed": False,
    }
    provenance_digest = _digest(provenance)
    detailed = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "classification": "read_only_full_horizon_affine_authority_discriminator",
        "provenance": provenance,
        "provenance_digest": provenance_digest,
        "source_authentication": {
            "raw_inventory": authenticated["raw_inventory"],
            "source_raw_authentication_count": source_count,
            "passed": source_count == 360,
        },
        "formal_reproduction": reproduction,
        "primary_gate_counts": primary,
        "context_rows": rows,
        "even_residual_diagnostic": {
            "output_fields": cfg["response_contract"]["output_fields"],
            "caps": caps.tolist(),
            "global_maximum_absolute": global_even_max.tolist(),
            "pass_by_component": (global_even_max <= caps + 1e-12).tolist(),
            "all_caps_pass": bool(np.all(global_even_max <= caps + 1e-12)),
            "is_primary_gate": False,
        },
        "primary_pass": primary_pass,
        "route": route,
        "scientific_guardrails": cfg["scientific_scope"],
        "execution": cfg["execution_contract"],
        "audit_complete": True,
    }
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "provenance_digest": provenance_digest,
        "source_raw_authentication_count": source_count,
        **reproduction,
        **primary,
        "even_residual_global_maximum_absolute": global_even_max.tolist(),
        "even_residual_all_caps_pass": bool(
            np.all(global_even_max <= caps + 1e-12)
        ),
        "primary_pass": primary_pass,
        "route": route,
        "scientific_classification": {
            "runtime_or_environment_error": False,
            "raw_or_snapshot_corruption": False,
            "statistics_or_reporting_error": False,
            "affine_model_class_authority_result": (
                "finite_optimistic_pass" if primary_pass else "finite_optimistic_fail"
            ),
            "real_tsc_executed_by_s22": False,
            "real_controller_or_mpc_executed_by_s22": False,
            "real_closed_loop_conclusion_from_s22": "not_tested",
            "global_plant_reachability_conclusion": "not_tested",
        },
    }

    output.mkdir(parents=True, exist_ok=False)
    detailed_path = output / "stage4_2r3c3t13s22_affine_authority_v1.json"
    summary_path = output / "stage4_2r3c3t13s22_summary_v1.json"
    _write_json(detailed_path, detailed)
    _write_json(summary_path, summary)
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "provenance_digest": provenance_digest,
        "output_files": [
            {
                "path": detailed_path.name,
                "size_bytes": detailed_path.stat().st_size,
                "sha256": _sha256(detailed_path),
            },
            {
                "path": summary_path.name,
                "size_bytes": summary_path.stat().st_size,
                "sha256": _sha256(summary_path),
            },
        ],
        "source_raw_files_copied_or_modified": 0,
        "new_raw_files_created": 0,
        "ray_gotsc_tsc_plant_or_controller_executed": False,
    }
    manifest_path = output / "stage4_2r3c3t13s22_manifest_v1.json"
    _write_json(manifest_path, manifest)
    return {
        "output": str(output),
        "detailed_sha256": _sha256(detailed_path),
        "summary_sha256": _sha256(summary_path),
        "manifest_sha256": _sha256(manifest_path),
        **summary,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source-s21-config", type=Path, required=True)
    parser.add_argument("--source-s21-run", type=Path, required=True)
    for name in (
        "source-stage42r3b-run",
        "source-stage42r3c3-run",
        "source-stage42r3c3-bank-dir",
        "source-stage42r3c3t1-run",
        "source-stage42r3c3t1-audit-dir",
        "source-stage42r3c3t3-controller-bank",
        "q1-run",
        "q2-run",
        "q1-audit",
        "q2-audit",
        "r3b-server-audit",
        "r3b-snapshot-checks",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    result = run_audit(_parser().parse_args())
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
