"""Frozen zero-TSC R8R23 causal online-feedback preflight.

This module authenticates immutable R8-family development evidence, builds the
prospectively fixed causal transition bank, and evaluates a nested whole-pair
ridge/tube/support contract.  It never launches Ray, gotsc, a controller, or a
plant step.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r22_bounded_continuous_multidirection_authority_sentinel
    as r8r22,
)


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S24D1R14R8R23"
IDENTITY = "causal_online_innovation_receding_horizon_preflight_v1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r23_causal_online_innovation_receding_horizon_preflight"
DECISIONS = (10, 14, 18, 22)
OUTPUT_FACTORS = np.asarray([0.03, 0.03, 10000.0, 1.0, 1.0], dtype=float)


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class Paths:
    stage: Path
    analysis: Path
    model: Path
    state: Path
    manifest: Path


@dataclass(frozen=True)
class Context:
    cfg: Mapping[str, Any]
    config_path: Path
    paths: Paths
    r8r22_ctx: Any


def _paths(run_dir: Path) -> Paths:
    stage = run_dir.expanduser().resolve() / RUN_NAME
    return Paths(
        stage=stage,
        analysis=stage / "analysis",
        model=stage / "model",
        state=stage / "stage_state.json",
        manifest=stage / "stage_manifest.json",
    )


def validate_config(cfg: Mapping[str, Any], *, project_root: Path) -> None:
    root = project_root.resolve()
    design = (root / str(cfg["design_document"])).resolve()
    source_cfg_path = (root / str(cfg["source_r8r22_config"])).resolve()
    if (
        int(cfg.get("schema_version", -1)) != SCHEMA_VERSION
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("run_name") != RUN_NAME
        or not design.is_relative_to(root)
        or not source_cfg_path.is_relative_to(root)
        or _sha(design) != str(cfg["design_document_sha256"])
        or _sha(source_cfg_path) != str(cfg["source_r8r22_config_sha256"])
    ):
        raise ValueError("R8R23 identity or frozen document changed")
    source_cfg = _read(source_cfg_path)
    bank = cfg["bank_contract"]
    model = cfg["model_contract"]
    action = cfg["action_contract"]
    formal = cfg["formal_contract"]
    if (
        tuple(map(int, bank["decision_task_steps"])) != DECISIONS
        or tuple(map(int, bank["maximum_forecast_samples_by_interval"]))
        != (4, 4, 4, 15)
        or int(bank["physical_pair_count"]) != 8
        or int(bank["history_context_count"]) != 16
        or int(bank["trajectory_count_per_context"]) != 27
        or int(bank["total_trajectory_count"]) != 432
        or int(bank["causal_feature_dimension"]) != 42
        or int(bank["expanded_feature_dimension"]) != 133
        or tuple(map(float, bank["visible_scales"])) != (0.03, 0.03, 10000.0)
        or float(model["ridge_penalty"]) != 1e-4
        or int(model["outer_fold_count"]) != 8
        or int(model["nested_fold_count_per_outer"]) != 7
        or float(model["tube_reserve_multiplier"]) != 1.25
        or float(model["support_threshold_multiplier"]) != 1.5
        or int(action["alphabet_size"]) != 11
        or int(action["maximum_unfiltered_sequence_count"]) != 14641
        or tuple(map(str, action["mixing_weight_tokens"]))
        != tuple(map(str, source_cfg["schedule_contract"]["mixing_weight_tokens"]))
        or tuple(map(str, action["amplitude_tokens"]))
        != tuple(map(str, source_cfg["schedule_contract"]["amplitude_tokens"]))
        or tuple(map(int, source_cfg["schedule_contract"]["decision_task_steps"]))
        != DECISIONS
        or (
            float(formal["position_tolerance_m"]),
            float(formal["speed_tolerance_m_per_s"]),
            float(formal["ip_tolerance_A"]),
            int(formal["arrival_streak_steps"]),
        )
        != (0.03, 0.1, 10000.0, 3)
        or formal.get("arrival_deadline_expansion_allowed") is not False
        or cfg.get("zero_new_tsc") is not True
        or cfg.get("expert_data_allowed") is not False
        or cfg.get("gate_a_qualified") is not False
    ):
        raise ValueError("R8R23 frozen numerical contract changed")
    routes = cfg["routes"]
    if set(routes) != {"evidence_fail", "model_fail", "static_pass", "adaptive_pass"}:
        raise ValueError("R8R23 route set changed")


def _r8r22_context(args: argparse.Namespace, cfg: Mapping[str, Any]) -> Any:
    source_args = copy.copy(args)
    source_args.config = (_root() / str(cfg["source_r8r22_config"])).resolve()
    source_args.run_dir = args.r8r22_run
    return r8r22.load_context(source_args)


def load_context(args: argparse.Namespace) -> Context:
    config_path = args.config.expanduser().resolve()
    cfg = _read(config_path)
    validate_config(cfg, project_root=_root())
    return Context(
        cfg=cfg,
        config_path=config_path,
        paths=_paths(args.run_dir),
        r8r22_ctx=_r8r22_context(args, cfg),
    )


def _authenticate_source(ctx: Context) -> dict[str, Any]:
    source = ctx.r8r22_ctx
    stage = source.paths.stage
    expected = ctx.cfg["source_r8r22"]
    paths = {
        "primary_detailed": stage / "analysis/primary_detailed.json",
        "primary_summary": stage / "analysis/primary_summary.json",
        "final_independent": stage / "analysis/final_independent.json",
        "final_report": stage / "analysis/final_report.json",
        "offline_primary": stage / "analysis/offline_primary.json",
        "offline_independent": stage / "analysis/offline_independent.json",
        "safety_raw_primary": stage / "analysis/safety_raw_primary.json",
        "safety_raw_independent": stage / "analysis/safety_raw_independent.json",
        "qualification_raw_primary": stage / "analysis/qualification_raw_primary.json",
        "qualification_raw_independent": stage / "analysis/qualification_raw_independent.json",
        "stage_manifest": stage / "stage_manifest.json",
        "stage_state": stage / "stage_state.json",
    }
    hashes = {name: _sha(path) for name, path in paths.items()}
    for name, value in hashes.items():
        if value != str(expected[f"{name}_sha256"]):
            raise ValueError(f"R8R23 R8R22 {name} hash changed")
    final = _read(paths["final_report"])
    independent = _read(paths["final_independent"])
    state = _read(paths["stage_state"])
    specs = _read(stage / "specs/all_specs.json")
    inventories = {
        phase: r8r22.r8r7.r8._inventory(stage / "raw" / phase)
        for phase in ("safety", "qualification")
    }
    for phase, inventory in inventories.items():
        if (
            int(inventory["count"]) != int(expected[f"{phase}_raw_count"])
            or int(inventory["bytes"]) != int(expected[f"{phase}_raw_bytes"])
            or inventory["digest"] != str(expected[f"{phase}_raw_digest"])
        ):
            raise ValueError(f"R8R23 R8R22 {phase} raw inventory changed")
    route = str(expected["actual_route"])
    if (
        source.paths.run_dir.name != str(expected["run_name"])
        or _digest(specs) != str(expected["spec_digest"])
        or final.get("route") != route
        or route not in set(map(str, expected["required_routes"]))
        or final.get("integrity_gate_passed") is not True
        or final.get("scientific_gate_passed") is not False
        or independent.get("passed") is not True
        or independent.get("primary_numerical_agreement") is not True
        or independent.get("primary_outcome_agreement") is not True
        or state.get("finished") is not True
        or state.get("real_tsc_executed") is not True
        or int(state.get("new_raw_count", -1)) != int(expected["new_raw_count"])
        or (state.get("verdict") or {}).get("route") != route
    ):
        raise ValueError("R8R23 R8R22 final integrity or allowed route changed")
    transitive = {
        "r8r12": r8r22._authenticate_r8r12(source),
        "r8r14": r8r22._authenticate_r8r14(source),
        "r8r15": r8r22._authenticate_r8r15(source),
        "r8r19": r8r22._authenticate_r8r19(source),
        "r8r20": r8r22._authenticate_r8r20(source),
    }
    if not all(bool(value["passed"]) for value in transitive.values()):
        raise ValueError("R8R23 transitive source authentication failed")
    return {
        "source_stage": str(stage),
        "hashes": hashes,
        "raw_inventories": inventories,
        "spec_digest": _digest(specs),
        "route": route,
        "transitive_source_authentication": transitive,
        "passed": True,
    }


def _state_matrix(result: Mapping[str, Any], target: Sequence[float]) -> np.ndarray:
    trajectory = result["trajectory"]
    target_array = np.asarray(target, dtype=float).reshape(3)
    rows = []
    for index, state in enumerate(trajectory):
        previous = trajectory[max(0, index - 1)]
        if index == 0:
            previous = state
        rows.append(
            [
                (float(state["R"]) - target_array[0]) / OUTPUT_FACTORS[0],
                (float(state["Z"]) - target_array[1]) / OUTPUT_FACTORS[1],
                (float(state["Ip"]) - target_array[2]) / OUTPUT_FACTORS[2],
                (float(state["R"]) - float(previous["R"])) / 0.01,
                (float(state["Z"]) - float(previous["Z"])) / 0.01,
            ]
        )
    values = np.asarray(rows, dtype=float)
    if values.ndim != 2 or values.shape[1] != 5 or not np.all(np.isfinite(values)):
        raise ValueError("R8R23 visible state matrix invalid")
    return values


def causal_feature(
    states: np.ndarray,
    trajectory: Sequence[Mapping[str, Any]],
    *,
    decision: int,
    previous_decision: int,
    previous_q: Sequence[float],
    coil_limits: Sequence[float],
) -> np.ndarray:
    limits = np.asarray(coil_limits, dtype=float).reshape(14)
    current = np.asarray(trajectory[decision]["currents_a_tsc"], dtype=float).reshape(14)
    previous = np.asarray(
        trajectory[previous_decision]["currents_a_tsc"], dtype=float
    ).reshape(14)
    visible = states[decision - 3 : decision + 1, :3].reshape(-1)
    feature = np.concatenate(
        (
            visible,
            current / limits,
            (current - previous) / limits,
            np.asarray(previous_q, dtype=float).reshape(2) / 1.5,
        )
    )
    if feature.shape != (42,) or not np.all(np.isfinite(feature)):
        raise ValueError("R8R23 causal feature invalid")
    return feature


def expanded_feature(feature: Sequence[float], q: Sequence[float]) -> np.ndarray:
    base = np.asarray(feature, dtype=float).reshape(42)
    q_u, q_v = map(float, np.asarray(q, dtype=float).reshape(2))
    action = np.asarray(
        [q_u, q_v, q_u * q_u, q_u * q_v, q_v * q_v, q_u, q_v],
        dtype=float,
    )
    # The last two entries are overwritten with the causal change from the
    # previous level by build_bank; this pure helper defaults previous q to 0.
    value = np.concatenate((base, action, base * q_u, base * q_v))
    if value.shape != (133,) or not np.all(np.isfinite(value)):
        raise ValueError("R8R23 expanded feature invalid")
    return value


def _expanded_row(row: Mapping[str, Any]) -> np.ndarray:
    base = np.asarray(row["feature"], dtype=float).reshape(42)
    q_u, q_v = map(float, row["q"])
    p_u, p_v = map(float, row["previous_q"])
    action = np.asarray(
        [q_u, q_v, q_u * q_u, q_u * q_v, q_v * q_v, q_u - p_u, q_v - p_v],
        dtype=float,
    )
    value = np.concatenate((base, action, base * q_u, base * q_v))
    if value.shape != (133,) or not np.all(np.isfinite(value)):
        raise ValueError("R8R23 expanded row invalid")
    return value


def _schedule_entries(ctx: Context) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source = ctx.r8r22_ctx
    baseline_specs, baseline_results = r8r22._source_baselines(source)
    u_specs, u_results = r8r22._source_r8r12_candidates(source)
    v_specs, v_results = r8r22._source_r8r14_candidates(source)
    r15_specs, r15_results = r8r22._source_r8r15_candidates(source)
    r20_specs, r20_results = r8r22._source_r8r20_candidates(source)
    r22_specs = r8r22._saved_specs(source)
    evaluators, _ = r8r22.r8r7.r8.d1r11._formal_callback(
        source.source_ctx.r8_ctx.d1r11_ctx, baseline_specs
    )
    evaluator_by_context = {
        (str(spec["pair_id"]), str(spec["history_member"])): evaluators[
            str(spec["experiment_id"])
        ]
        for spec in baseline_specs
    }
    rows: list[dict[str, Any]] = []

    def add(
        spec: Mapping[str, Any],
        result: Mapping[str, Any],
        schedule_id: str,
        q_sequence: Sequence[Sequence[float]],
        source_name: str,
    ) -> None:
        rows.append(
            {
                "spec": spec,
                "result": result,
                "schedule_id": schedule_id,
                "q_sequence": [list(map(float, q)) for q in q_sequence],
                "source": source_name,
            }
        )

    zero = [[0.0, 0.0]] * 4
    for spec in baseline_specs:
        add(spec, baseline_results[str(spec["experiment_id"])], "q0", zero, "R8R7")
    for spec in u_specs:
        add(spec, u_results[str(spec["experiment_id"])], "UUUU", [[1.0, 0.0]] * 4, "R8R12")
    for spec in v_specs:
        add(spec, v_results[str(spec["experiment_id"])], "VVVV", [[0.0, 1.0]] * 4, "R8R14")
    for spec in r15_specs:
        code = str(spec["r8r15_sequence_code"])
        add(
            spec,
            r15_results[str(spec["experiment_id"])],
            code,
            [[1.0, 0.0] if symbol == "U" else [0.0, 1.0] for symbol in code],
            "R8R15",
        )
    for spec in r20_specs:
        code = str(spec["r8r20_sequence_code"])
        add(
            spec,
            r20_results[str(spec["experiment_id"])],
            code,
            [[1.0, 0.0] if symbol == "U" else [0.0, 1.0] for symbol in code],
            "R8R20",
        )
    for spec in r22_specs:
        result = r8r22.r8r7.r8._read_gz(
            source.paths.phase_raw(str(spec["partition"]))
            / f"{spec['experiment_id']}.json.gz"
        )
        q = [
            float(spec["r8r22_amplitude"]) * float(spec["r8r22_mixing_weight"]),
            float(spec["r8r22_amplitude"]) * (1.0 - float(spec["r8r22_mixing_weight"])),
        ]
        add(spec, result, str(spec["r8r22_candidate_id"]), [q] * 4, "R8R22")
    return rows, evaluator_by_context


def build_bank(ctx: Context) -> tuple[list[dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    entries, evaluators = _schedule_entries(ctx)
    source = ctx.r8r22_ctx
    r22_specs = r8r22._saved_specs(source)
    spec_by_context = {}
    for spec in r22_specs:
        spec_by_context.setdefault(
            (str(spec["pair_id"]), str(spec["history_member"])), spec
        )
    execution = r8r22._execution_context(source)
    lattice = execution.d1r11_ctx.base_ctx.base_ctx.cfg["lattice_probe"]
    baseline_specs, baseline_results = r8r22._source_baselines(source)
    baseline_by_context = {
        (str(spec["pair_id"]), str(spec["history_member"])): (
            spec,
            baseline_results[str(spec["experiment_id"])],
        )
        for spec in baseline_specs
    }
    context_meta: dict[tuple[str, str], dict[str, Any]] = {}
    for key, spec in spec_by_context.items():
        payload = _read(source.paths.variants / f"payload_{spec['experiment_id']}.json")
        actuator = r8r22.mpc.actuator_from_payload(payload, lattice)
        limits = np.maximum(
            np.abs(np.asarray(actuator.minimum_current_a_tsc, dtype=float)),
            np.abs(np.asarray(actuator.maximum_current_a_tsc, dtype=float)),
        )
        if limits.shape != (14,) or np.any(limits <= 0.0):
            raise ValueError("R8R23 coil limits invalid")
        base_spec, base_result = baseline_by_context[key]
        context_meta[key] = {
            "pair_id": key[0],
            "history_member": key[1],
            "target": np.asarray(evaluators[key].target, dtype=float),
            "coil_limits": limits,
            "actuator": actuator,
            "payload": payload,
            "lattice": lattice,
            "fixed_basis": r8r22._fixed_basis(base_result).T,
            "baseline_spec": base_spec,
            "baseline_result": base_result,
            "slew_scale": float(base_spec["slew_scale"]),
            "horizon": int(base_spec["horizon_steps"]),
        }
    trajectories = []
    for entry in entries:
        spec, result = entry["spec"], entry["result"]
        key = (str(spec["pair_id"]), str(spec["history_member"]))
        meta = context_meta[key]
        trajectory = result["trajectory"]
        horizon = int(spec["horizon_steps"])
        if (
            result.get("success") is not True
            or len(trajectory) != horizon + 1
            or horizon != int(meta["horizon"])
        ):
            raise ValueError("R8R23 source trajectory incomplete")
        states = _state_matrix(result, meta["target"])
        interval_rows = []
        q_sequence = entry["q_sequence"]
        for interval, decision in enumerate(DECISIONS):
            previous_decision = decision if interval == 0 else DECISIONS[interval - 1]
            previous_q = [0.0, 0.0] if interval == 0 else q_sequence[interval - 1]
            end = DECISIONS[interval + 1] if interval < 3 else horizon
            targets = states[decision + 1 : end + 1]
            row = {
                "row_id": f"{entry['source']}|{spec['experiment_id']}|i{interval}",
                "pair_id": key[0],
                "history_member": key[1],
                "schedule_id": entry["schedule_id"],
                "source": entry["source"],
                "interval": interval,
                "decision": decision,
                "feature": causal_feature(
                    states,
                    trajectory,
                    decision=decision,
                    previous_decision=previous_decision,
                    previous_q=previous_q,
                    coil_limits=meta["coil_limits"],
                ),
                "q": np.asarray(q_sequence[interval], dtype=float),
                "previous_q": np.asarray(previous_q, dtype=float),
                "targets": targets,
            }
            row["expanded"] = _expanded_row(row)
            interval_rows.append(row)
        trajectories.append(
            {
                "trajectory_id": f"{entry['source']}|{spec['experiment_id']}",
                "pair_id": key[0],
                "history_member": key[1],
                "schedule_id": entry["schedule_id"],
                "source": entry["source"],
                "spec": spec,
                "states": states,
                "trajectory": trajectory,
                "intervals": interval_rows,
            }
        )
    contexts = {(row["pair_id"], row["history_member"]) for row in trajectories}
    schedules = {
        (row["pair_id"], row["history_member"]): set() for row in trajectories
    }
    for row in trajectories:
        schedules[(row["pair_id"], row["history_member"])].add(row["schedule_id"])
    if (
        len(trajectories) != 432
        or len(contexts) != 16
        or any(len(value) != 27 for value in schedules.values())
        or sum(len(row["intervals"]) for row in trajectories) != 1728
    ):
        raise ValueError("R8R23 development bank coverage changed")
    return sorted(trajectories, key=lambda row: row["trajectory_id"]), context_meta


def _model_serializable(model: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "intervals": [
            {
                "interval": int(interval["interval"]),
                "offsets": [
                    {
                        "sample_offset": int(offset["sample_offset"]),
                        "training_row_count": int(offset["training_row_count"]),
                        "intercept": np.asarray(offset["intercept"], dtype=float).tolist(),
                        "coefficients": np.asarray(
                            offset["coefficients"], dtype=float
                        ).tolist(),
                    }
                    for offset in interval["offsets"]
                ],
            }
            for interval in model["intervals"]
        ]
    }


def fit_models(
    trajectories: Sequence[Mapping[str, Any]],
    training_pairs: Sequence[str],
    *,
    ridge: float,
) -> dict[str, Any]:
    allowed = set(map(str, training_pairs))
    intervals = []
    for interval in range(4):
        current = [
            trajectory["intervals"][interval]
            for trajectory in trajectories
            if str(trajectory["pair_id"]) in allowed
        ]
        maximum = max(len(row["targets"]) for row in current)
        offsets = []
        for offset in range(maximum):
            selected = [row for row in current if len(row["targets"]) > offset]
            x = np.asarray([row["expanded"] for row in selected], dtype=float)
            y = np.asarray([row["targets"][offset] for row in selected], dtype=float)
            x_mean = np.mean(x, axis=0)
            y_mean = np.mean(y, axis=0)
            centered_x = x - x_mean
            centered_y = y - y_mean
            gram = centered_x.T @ centered_x
            coefficients = np.linalg.solve(
                gram + float(ridge) * np.eye(gram.shape[0]),
                centered_x.T @ centered_y,
            )
            intercept = y_mean - x_mean @ coefficients
            if (
                coefficients.shape != (133, 5)
                or intercept.shape != (5,)
                or not np.all(np.isfinite(coefficients))
                or not np.all(np.isfinite(intercept))
            ):
                raise ValueError("R8R23 ridge fit invalid")
            offsets.append(
                {
                    "sample_offset": offset,
                    "training_row_count": len(selected),
                    "intercept": intercept,
                    "coefficients": coefficients,
                }
            )
        intervals.append({"interval": interval, "offsets": offsets})
    return {"intervals": intervals}


def predict_row(model: Mapping[str, Any], row: Mapping[str, Any]) -> np.ndarray:
    interval = int(row["interval"])
    expanded = np.asarray(row["expanded"], dtype=float).reshape(133)
    count = len(row["targets"])
    offsets = model["intervals"][interval]["offsets"][:count]
    prediction = np.asarray(
        [
            np.asarray(offset["intercept"], dtype=float)
            + expanded @ np.asarray(offset["coefficients"], dtype=float)
            for offset in offsets
        ],
        dtype=float,
    )
    if prediction.shape != (count, 5) or not np.all(np.isfinite(prediction)):
        raise ValueError("R8R23 prediction invalid")
    return prediction


def _empty_tube() -> list[np.ndarray]:
    return [
        np.zeros((count, 5), dtype=float)
        for count in (4, 4, 4, 15)
    ]


def _support_for_fold(
    trajectories: Sequence[Mapping[str, Any]],
    training_pairs: Sequence[str],
    held_pair: str,
    *,
    multiplier: float,
) -> dict[str, Any]:
    training = set(map(str, training_pairs))
    thresholds, held_maxima, pass_counts, row_counts = [], [], [], []
    for interval in range(4):
        by_pair = {
            pair: np.asarray(
                [
                    trajectory["intervals"][interval]["feature"]
                    for trajectory in trajectories
                    if str(trajectory["pair_id"]) == pair
                ],
                dtype=float,
            )
            for pair in sorted(training)
        }
        nested_distances = []
        for pair, values in by_pair.items():
            others = np.concatenate(
                [other for name, other in by_pair.items() if name != pair], axis=0
            )
            distance = np.linalg.norm(
                values[:, None, :] - others[None, :, :], axis=2
            )
            nested_distances.extend(np.min(distance, axis=1).tolist())
        threshold = float(multiplier) * max(map(float, nested_distances), default=0.0)
        train_values = np.concatenate(list(by_pair.values()), axis=0)
        held_values = np.asarray(
            [
                trajectory["intervals"][interval]["feature"]
                for trajectory in trajectories
                if str(trajectory["pair_id"]) == held_pair
            ],
            dtype=float,
        )
        distances = np.min(
            np.linalg.norm(
                held_values[:, None, :] - train_values[None, :, :], axis=2
            ),
            axis=1,
        )
        passed = distances <= threshold + 1e-15
        thresholds.append(threshold)
        held_maxima.append(float(np.max(distances)))
        pass_counts.append(int(np.count_nonzero(passed)))
        row_counts.append(len(distances))
    return {
        "thresholds": thresholds,
        "maximum_held_distances": held_maxima,
        "pass_counts": pass_counts,
        "row_counts": row_counts,
        "passed": sum(pass_counts) == sum(row_counts),
    }


def _cold_predictions(
    model: Mapping[str, Any], trajectories: Sequence[Mapping[str, Any]]
) -> dict[str, list[np.ndarray]]:
    return {
        str(trajectory["trajectory_id"]): [
            predict_row(model, row) for row in trajectory["intervals"]
        ]
        for trajectory in trajectories
    }


def _nested_tube(
    trajectories: Sequence[Mapping[str, Any]],
    training_pairs: Sequence[str],
    *,
    ridge: float,
) -> tuple[list[np.ndarray], list[dict[str, Any]]]:
    pairs = tuple(sorted(map(str, training_pairs)))
    base = _empty_tube()
    evidence = []
    for nested_held in pairs:
        nested_train = tuple(pair for pair in pairs if pair != nested_held)
        model = fit_models(trajectories, nested_train, ridge=ridge)
        held = [
            row for row in trajectories if str(row["pair_id"]) == nested_held
        ]
        predictions = _cold_predictions(model, held)
        for trajectory in held:
            for interval, row in enumerate(trajectory["intervals"]):
                residual = np.abs(
                    np.asarray(row["targets"], dtype=float)
                    - predictions[str(trajectory["trajectory_id"])][interval]
                )
                base[interval][: len(residual)] = np.maximum(
                    base[interval][: len(residual)], residual
                )
        serial = _model_serializable(model)
        evidence.append(
            {
                "held_pair": nested_held,
                "training_pairs": list(nested_train),
                "model_digest": _digest(serial),
            }
        )
    return base, evidence


def _adapt_predictions(
    trajectories: Sequence[Mapping[str, Any]],
    cold: Mapping[str, Sequence[np.ndarray]],
    base_tube: Sequence[np.ndarray],
) -> tuple[dict[str, list[np.ndarray]], int]:
    output: dict[str, list[np.ndarray]] = {}
    clipping = 0
    for trajectory in trajectories:
        identifier = str(trajectory["trajectory_id"])
        bias = np.zeros(5, dtype=float)
        forecasts = []
        for interval, row in enumerate(trajectory["intervals"]):
            current = np.asarray(cold[identifier][interval], dtype=float) + bias[None, :]
            forecasts.append(current)
            residual = np.asarray(row["targets"][-1], dtype=float) - current[-1]
            candidate = 0.5 * bias + 0.5 * residual
            bound = np.asarray(base_tube[interval][len(row["targets"]) - 1], dtype=float)
            clipping += int(np.any(np.abs(candidate) > bound + 1e-15))
            bias = np.clip(candidate, -bound, bound)
        output[identifier] = forecasts
    return output, clipping


def _prediction_sse(
    trajectories: Sequence[Mapping[str, Any]],
    predictions: Mapping[str, Sequence[np.ndarray]],
) -> float:
    value = 0.0
    for trajectory in trajectories:
        identifier = str(trajectory["trajectory_id"])
        for interval, row in enumerate(trajectory["intervals"]):
            residual = np.asarray(row["targets"], dtype=float) - np.asarray(
                predictions[identifier][interval], dtype=float
            )
            value += float(np.sum(residual * residual))
    return value


def _outer_fold(
    trajectories: Sequence[Mapping[str, Any]],
    all_pairs: Sequence[str],
    held_pair: str,
    cfg: Mapping[str, Any],
) -> dict[str, Any]:
    training_pairs = tuple(pair for pair in all_pairs if pair != held_pair)
    ridge = float(cfg["model_contract"]["ridge_penalty"])
    model = fit_models(trajectories, training_pairs, ridge=ridge)
    base_tube, nested = _nested_tube(
        trajectories, training_pairs, ridge=ridge
    )
    reserve = float(cfg["model_contract"]["tube_reserve_multiplier"])
    reserved_tube = [value * reserve for value in base_tube]
    held = [row for row in trajectories if str(row["pair_id"]) == held_pair]
    cold = _cold_predictions(model, held)
    adapted, clipping = _adapt_predictions(held, cold, base_tube)
    support = _support_for_fold(
        trajectories,
        training_pairs,
        held_pair,
        multiplier=float(cfg["model_contract"]["support_threshold_multiplier"]),
    )
    return {
        "held_pair": held_pair,
        "training_pairs": list(training_pairs),
        "model": model,
        "model_digest": _digest(_model_serializable(model)),
        "nested_fit_evidence": nested,
        "base_tube": base_tube,
        "reserved_tube": reserved_tube,
        "held_trajectories": held,
        "cold_predictions": cold,
        "adapted_predictions": adapted,
        "cold_squared_error": _prediction_sse(held, cold),
        "adapted_squared_error": _prediction_sse(held, adapted),
        "innovation_clipping_row_count": clipping,
        "support": support,
    }


def _usefulness(folds: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> dict[str, Any]:
    cold = sum(float(fold["cold_squared_error"]) for fold in folds)
    adapted = sum(float(fold["adapted_squared_error"]) for fold in folds)
    ratio = adapted / cold if cold > 0.0 else math.inf
    rows = []
    for fold in folds:
        current_cold = float(fold["cold_squared_error"])
        current_adapted = float(fold["adapted_squared_error"])
        current_ratio = current_adapted / current_cold if current_cold > 0.0 else math.inf
        rows.append(
            {
                "pair_id": fold["held_pair"],
                "cold_squared_error": current_cold,
                "adapted_squared_error": current_adapted,
                "adapted_to_cold_ratio": current_ratio,
                "strictly_improved": current_adapted < current_cold,
            }
        )
    gate = cfg["adaptation_gates"]
    clipping = sum(int(fold["innovation_clipping_row_count"]) for fold in folds)
    improved = sum(bool(row["strictly_improved"]) for row in rows)
    passed = bool(
        ratio <= float(gate["maximum_aggregate_squared_error_ratio"]) + 1e-15
        and improved >= int(gate["minimum_strictly_improved_outer_pair_count"])
        and all(
            float(row["adapted_to_cold_ratio"])
            <= float(gate["maximum_outer_pair_squared_error_ratio"]) + 1e-15
            for row in rows
        )
        and clipping <= int(gate["maximum_innovation_clipping_row_count"])
    )
    return {
        "cold_squared_error": cold,
        "adapted_squared_error": adapted,
        "adapted_to_cold_ratio": ratio,
        "strictly_improved_outer_pair_count": improved,
        "innovation_clipping_row_count": clipping,
        "rows": rows,
        "passed": passed,
    }


def _evaluate_model(
    folds: Sequence[Mapping[str, Any]],
    *,
    adapted: bool,
    cfg: Mapping[str, Any],
) -> dict[str, Any]:
    maxima = np.zeros(5, dtype=float)
    tube_maxima = np.zeros(5, dtype=float)
    contained = total = finite_exclusions = 0
    support_pass = support_total = 0
    fold_rows = []
    for fold in folds:
        predictions = fold[
            "adapted_predictions" if adapted else "cold_predictions"
        ]
        fold_max = np.zeros(5, dtype=float)
        fold_contained = fold_total = 0
        for trajectory in fold["held_trajectories"]:
            identifier = str(trajectory["trajectory_id"])
            for interval, row in enumerate(trajectory["intervals"]):
                actual = np.asarray(row["targets"], dtype=float)
                predicted = np.asarray(predictions[identifier][interval], dtype=float)
                residual = np.abs(actual - predicted)
                physical = residual * OUTPUT_FACTORS[None, :]
                fold_max = np.maximum(fold_max, np.max(physical, axis=0))
                maxima = np.maximum(maxima, np.max(physical, axis=0))
                tube = np.asarray(fold["reserved_tube"][interval][: len(actual)], dtype=float)
                current = residual <= tube + 1e-15
                fold_contained += int(np.count_nonzero(current))
                fold_total += int(current.size)
                finite_exclusions += int(
                    not np.all(np.isfinite(actual)) or not np.all(np.isfinite(predicted))
                )
        physical_tube = np.max(
            np.concatenate(
                [value for value in fold["reserved_tube"]], axis=0
            )
            * OUTPUT_FACTORS
        )
        current_tube_max = np.max(
            np.concatenate([value for value in fold["reserved_tube"]], axis=0)
            * OUTPUT_FACTORS[None, :],
            axis=0,
        )
        tube_maxima = np.maximum(tube_maxima, current_tube_max)
        contained += fold_contained
        total += fold_total
        support_pass += sum(map(int, fold["support"]["pass_counts"]))
        support_total += sum(map(int, fold["support"]["row_counts"]))
        fold_rows.append(
            {
                "pair_id": fold["held_pair"],
                "maximum_absolute_physical_error": fold_max.tolist(),
                "reserved_tube_contained_component_count": fold_contained,
                "reserved_tube_component_count": fold_total,
                "reserved_tube_containment_rate": fold_contained / fold_total,
                "maximum_reserved_physical_tube_half_width": current_tube_max.tolist(),
                "support": fold["support"],
            }
        )
        del physical_tube
    gates = cfg["model_gates"]
    point_passed = bool(
        maxima[0] <= float(gates["maximum_R_point_error_m"]) + 1e-15
        and maxima[1] <= float(gates["maximum_Z_point_error_m"]) + 1e-15
        and maxima[2] <= float(gates["maximum_Ip_point_error_A"]) + 1e-12
        and maxima[3] <= float(gates["maximum_vR_point_error_m_per_s"]) + 1e-15
        and maxima[4] <= float(gates["maximum_vZ_point_error_m_per_s"]) + 1e-15
    )
    tube_cap_passed = bool(
        tube_maxima[0] <= float(gates["maximum_reserved_R_tube_half_width_m"]) + 1e-15
        and tube_maxima[1] <= float(gates["maximum_reserved_Z_tube_half_width_m"]) + 1e-15
        and tube_maxima[2] <= float(gates["maximum_reserved_Ip_tube_half_width_A"]) + 1e-12
        and tube_maxima[3]
        <= float(gates["maximum_reserved_vR_tube_half_width_m_per_s"]) + 1e-15
        and tube_maxima[4]
        <= float(gates["maximum_reserved_vZ_tube_half_width_m_per_s"]) + 1e-15
    )
    containment_rate = contained / total
    support_rate = support_pass / support_total
    passed = bool(
        point_passed
        and tube_cap_passed
        and containment_rate
        >= float(gates["required_reserved_tube_containment_rate"]) - 1e-15
        and support_rate >= float(gates["required_support_rate"]) - 1e-15
        and finite_exclusions <= int(gates["maximum_finite_exclusion_count"])
    )
    return {
        "selected_predictor": "adapted" if adapted else "cold",
        "maximum_absolute_physical_error": maxima.tolist(),
        "maximum_reserved_physical_tube_half_width": tube_maxima.tolist(),
        "reserved_tube_contained_component_count": contained,
        "reserved_tube_component_count": total,
        "reserved_tube_containment_rate": containment_rate,
        "support_pass_count": support_pass,
        "support_row_count": support_total,
        "support_rate": support_rate,
        "finite_exclusion_count": finite_exclusions,
        "forbidden_input_count": 0,
        "point_error_gate_passed": point_passed,
        "tube_cap_gate_passed": tube_cap_passed,
        "fold_rows": fold_rows,
        "passed": passed,
    }


def _action_levels(ctx: Context) -> list[dict[str, Any]]:
    schedule = ctx.r8r22_ctx.cfg["schedule_contract"]
    rows = [{"index": 0, "level_id": "q0", "q": [0.0, 0.0]}]
    for index, candidate in enumerate(r8r22._candidate_definitions(schedule), start=1):
        amplitude = float(candidate["amplitude"])
        weight = float(candidate["mixing_weight"])
        rows.append(
            {
                "index": index,
                "level_id": str(candidate["candidate_id"]),
                "q": [amplitude * weight, amplitude * (1.0 - weight)],
            }
        )
    if len(rows) != 11:
        raise ValueError("R8R23 action alphabet changed")
    return rows


def _planning_feature(
    states: np.ndarray,
    current: np.ndarray,
    previous_current: np.ndarray,
    previous_q: np.ndarray,
    limits: np.ndarray,
) -> np.ndarray:
    value = np.concatenate(
        (
            np.asarray(states[-4:, :3], dtype=float).reshape(-1),
            current / limits,
            (current - previous_current) / limits,
            previous_q / 1.5,
        )
    )
    if value.shape != (42,) or not np.all(np.isfinite(value)):
        raise ValueError("R8R23 planned causal feature invalid")
    return value


def _safe_issue(
    ctx: Context,
    meta: Mapping[str, Any],
    current: np.ndarray,
    level: Mapping[str, Any],
    task_step: int,
) -> dict[str, Any]:
    q = np.asarray(level["q"], dtype=float)
    actuator = meta["actuator"]
    if np.array_equal(q, np.zeros(2, dtype=float)):
        applied = actuator.apply(current, np.zeros(14, dtype=float))
        minimum = np.asarray(actuator.minimum_current_a_tsc, dtype=float)
        maximum = np.asarray(actuator.maximum_current_a_tsc, dtype=float)
        center, half = 0.5 * (minimum + maximum), 0.5 * (maximum - minimum)
        utilization = float(
            np.max(
                np.abs(
                    (np.asarray(applied.nominal_readback_current_a_tsc) - center) / half
                )
            )
        )
        passed = bool(
            not any(applied.action_saturated)
            and not any(applied.current_limit_clipped)
            and utilization
            <= float(ctx.cfg["action_contract"]["maximum_current_utilization"])
            + 1e-12
        )
        return {
            "passed": passed,
            "nominal_issue_readback_current_a_tsc": list(
                map(float, applied.nominal_readback_current_a_tsc)
            ),
            "predicted_current_utilization": utilization,
            "incremental_normalized_action_linf": 0.0,
            "level_id": level["level_id"],
        }
    schedule = ctx.r8r22_ctx.cfg["schedule_contract"]
    matrix = np.asarray(schedule["canonical_matrix_columns"], dtype=float)
    endpoint_u = matrix[:, int(schedule["endpoint_u"]["direction_index"])] * int(
        schedule["endpoint_u"]["sign"]
    )
    endpoint_v = matrix[:, int(schedule["endpoint_v"]["direction_index"])] * int(
        schedule["endpoint_v"]["sign"]
    )
    coordinate = q[0] * endpoint_u + q[1] * endpoint_v
    contract = copy.deepcopy(ctx.cfg["action_contract"])
    contract["dynamic_exact_search_radius"] = int(
        schedule["dynamic_exact_search_radius"]
    )
    result = r8r22._construct_coordinate_issue(
        task_step=task_step,
        currents_a_tsc=current,
        fixed_basis_delta_field_kat_tsc=meta["fixed_basis"],
        requested_coordinate=coordinate,
        candidate_id=str(level["level_id"]),
        actuator=actuator,
        controller_cfg=contract,
        lattice_cfg=meta["lattice"],
    )
    return result


def _robust_formal(
    states: np.ndarray,
    tubes: np.ndarray,
    *,
    deadline: int,
    endpoint: int,
    cfg: Mapping[str, Any],
) -> tuple[bool, float, float]:
    formal = cfg["formal_contract"]
    physical = np.abs(states) * OUTPUT_FACTORS[None, :]
    robust = physical + tubes * OUTPUT_FACTORS[None, :]
    normalized_violation = np.column_stack(
        (
            robust[:, 0] / float(formal["position_tolerance_m"]),
            robust[:, 1] / float(formal["position_tolerance_m"]),
            robust[:, 2] / float(formal["ip_tolerance_A"]),
            robust[:, 3] / float(formal["speed_tolerance_m_per_s"]),
            robust[:, 4] / float(formal["speed_tolerance_m_per_s"]),
        )
    ) - 1.0
    per_step = np.max(normalized_violation, axis=1)
    streak = int(formal["arrival_streak_steps"])
    candidates = range(0, max(0, deadline - streak + 2))
    worst = min(
        (float(np.max(per_step[start : endpoint + 1])) for start in candidates),
        default=math.inf,
    )
    passed = worst <= 1e-15
    integrated = float(np.sum(states[10 : endpoint + 1, :3] ** 2))
    return passed, max(0.0, worst), integrated


def _plan_context(
    ctx: Context,
    meta: Mapping[str, Any],
    fold: Mapping[str, Any],
) -> dict[str, Any]:
    levels = _action_levels(ctx)
    model = fold["model"]
    baseline = meta["baseline_result"]
    states = _state_matrix(baseline, meta["target"])
    prefix_states = states[: DECISIONS[0] + 1]
    prefix_tubes = np.zeros_like(prefix_states)
    trajectory = baseline["trajectory"]
    initial_current = np.asarray(
        trajectory[DECISIONS[0]]["currents_a_tsc"], dtype=float
    )
    horizon = int(meta["horizon"])
    deadline = (
        int(ctx.cfg["formal_contract"]["weak_arrival_deadline_step"])
        if math.isclose(float(meta["slew_scale"]), 0.9, abs_tol=1e-15)
        else int(ctx.cfg["formal_contract"]["normal_arrival_deadline_step"])
    )
    endpoint = (
        int(ctx.cfg["formal_contract"]["weak_hold_through_step"])
        if math.isclose(float(meta["slew_scale"]), 0.9, abs_tol=1e-15)
        else int(ctx.cfg["formal_contract"]["normal_hold_through_step"])
    )
    if endpoint != horizon:
        raise ValueError("R8R23 formal endpoint and source horizon differ")
    best_key: tuple[Any, ...] | None = None
    best: dict[str, Any] | None = None
    complete_sequences = safe_issue_count = 0

    def visit(
        interval: int,
        current_states: np.ndarray,
        current_tubes: np.ndarray,
        current: np.ndarray,
        previous_current: np.ndarray,
        previous_q: np.ndarray,
        indices: tuple[int, ...],
        movement: float,
        maximum_current: float,
    ) -> None:
        nonlocal best_key, best, complete_sequences, safe_issue_count
        if interval == 4:
            complete_sequences += 1
            passed, violation, integrated = _robust_formal(
                current_states,
                current_tubes,
                deadline=deadline,
                endpoint=endpoint,
                cfg=ctx.cfg,
            )
            key = (
                not passed,
                violation,
                integrated,
                movement,
                maximum_current,
                indices,
            )
            if best_key is None or key < best_key:
                best_key = key
                best = {
                    "alphabet_indices": list(indices),
                    "level_ids": [levels[index]["level_id"] for index in indices],
                    "robust_formal_pass": passed,
                    "worst_formal_margin_violation": violation,
                    "integrated_normalized_error": integrated,
                    "cumulative_normalized_action_movement": movement,
                    "maximum_predicted_current_utilization": maximum_current,
                }
            return
        feature = _planning_feature(
            current_states,
            current,
            previous_current,
            previous_q,
            np.asarray(meta["coil_limits"], dtype=float),
        )
        count = 4 if interval < 3 else endpoint - DECISIONS[3]
        for level in levels:
            issue = _safe_issue(ctx, meta, current, level, DECISIONS[interval])
            if not bool(issue["passed"]):
                continue
            safe_issue_count += 1
            q = np.asarray(level["q"], dtype=float)
            row = {
                "interval": interval,
                "feature": feature,
                "q": q,
                "previous_q": previous_q,
                "targets": np.zeros((count, 5), dtype=float),
            }
            row["expanded"] = _expanded_row(row)
            prediction = predict_row(model, row)
            next_states = np.concatenate((current_states, prediction), axis=0)
            next_tubes = np.concatenate(
                (
                    current_tubes,
                    np.asarray(fold["reserved_tube"][interval][:count], dtype=float),
                ),
                axis=0,
            )
            next_current = np.asarray(
                issue["nominal_issue_readback_current_a_tsc"], dtype=float
            )
            visit(
                interval + 1,
                next_states,
                next_tubes,
                next_current,
                current,
                q,
                indices + (int(level["index"]),),
                movement + float(np.sum(np.abs(q - previous_q))),
                max(maximum_current, float(issue["predicted_current_utilization"])),
            )

    visit(
        0,
        prefix_states,
        prefix_tubes,
        initial_current,
        initial_current,
        np.zeros(2, dtype=float),
        (),
        0.0,
        0.0,
    )
    return {
        "pair_id": meta["pair_id"],
        "history_member": meta["history_member"],
        "unfiltered_sequence_count": 14641,
        "safe_issue_node_count": safe_issue_count,
        "safe_complete_sequence_count": complete_sequences,
        "selected_plan": best,
        "safe_complete_plan": best is not None,
        "predicted_formal_pass": bool(best and best["robust_formal_pass"]),
    }


def _planning_evaluation(
    ctx: Context,
    folds: Sequence[Mapping[str, Any]],
    context_meta: Mapping[tuple[str, str], Mapping[str, Any]],
) -> dict[str, Any]:
    by_pair = {str(fold["held_pair"]): fold for fold in folds}
    plans = [
        _plan_context(ctx, context_meta[key], by_pair[key[0]])
        for key in sorted(context_meta)
    ]
    source = _read(ctx.r8r22_ctx.paths.analysis / "primary_detailed.json")
    baseline = {
        (str(row["pair_id"]), str(row["history_member"])): bool(
            row["baseline"]["formal_contract_pass"]
        )
        for row in source["formal_authority"]["context_rows"]
    }
    repairs = regressions = oracle = 0
    for plan in plans:
        key = (str(plan["pair_id"]), str(plan["history_member"]))
        predicted = bool(plan["predicted_formal_pass"])
        repairs += int(not baseline[key] and predicted)
        regressions += int(baseline[key] and not predicted)
        oracle += int(baseline[key] or predicted)
    gate = ctx.cfg["planning_gate"]
    complete = sum(bool(row["safe_complete_plan"]) for row in plans)
    passed = bool(
        complete == int(gate["required_safe_complete_plan_count"])
        and repairs >= int(gate["minimum_predicted_repaired_failed_baseline_count"])
        and regressions <= int(gate["maximum_predicted_regressed_baseline_pass_count"])
        and oracle >= int(gate["minimum_predicted_oracle_count"])
    )
    return {
        "safe_complete_plan_count": complete,
        "predicted_repaired_failed_baseline_count": repairs,
        "predicted_regressed_baseline_pass_count": regressions,
        "predicted_baseline_plus_policy_oracle_count": oracle,
        "plans": plans,
        "passed": passed,
    }


def _bank_evidence(trajectories: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = []
    target_rows = []
    for trajectory in trajectories:
        for row in trajectory["intervals"]:
            rows.append(
                {
                    "row_id": row["row_id"],
                    "feature": np.asarray(row["feature"], dtype=float).tolist(),
                    "q": np.asarray(row["q"], dtype=float).tolist(),
                    "previous_q": np.asarray(row["previous_q"], dtype=float).tolist(),
                    "expanded": np.asarray(row["expanded"], dtype=float).tolist(),
                }
            )
            target_rows.append(
                {
                    "row_id": row["row_id"],
                    "targets": np.asarray(row["targets"], dtype=float).tolist(),
                }
            )
    return {
        "trajectory_count": len(trajectories),
        "origin_row_count": len(rows),
        "forecast_point_count": sum(
            len(row["targets"])
            for trajectory in trajectories
            for row in trajectory["intervals"]
        ),
        "feature_digest": _digest(rows),
        "target_digest": _digest(target_rows),
        "feature_dimension": 42,
        "expanded_feature_dimension": 133,
        "forbidden_input_count": 0,
        "allowed_in_expert_dataset": False,
    }


def compute(ctx: Context) -> tuple[dict[str, Any], dict[str, Any]]:
    authentication = _authenticate_source(ctx)
    trajectories, context_meta = build_bank(ctx)
    bank = _bank_evidence(trajectories)
    pairs = tuple(sorted({str(row["pair_id"]) for row in trajectories}))
    folds = [_outer_fold(trajectories, pairs, held, ctx.cfg) for held in pairs]
    usefulness = _usefulness(folds, ctx.cfg)
    adaptation_enabled = bool(usefulness["passed"])
    model_evaluation = _evaluate_model(
        folds, adapted=adaptation_enabled, cfg=ctx.cfg
    )
    planning = (
        _planning_evaluation(ctx, folds, context_meta)
        if model_evaluation["passed"]
        else {
            "safe_complete_plan_count": 0,
            "predicted_repaired_failed_baseline_count": 0,
            "predicted_regressed_baseline_pass_count": 0,
            "predicted_baseline_plus_policy_oracle_count": 6,
            "plans": [],
            "skipped_reason": "frozen_model_tube_or_support_gate_failed",
            "passed": False,
        }
    )
    scientific = bool(model_evaluation["passed"] and planning["passed"])
    route = str(
        ctx.cfg["routes"][
            ("adaptive_pass" if adaptation_enabled else "static_pass")
            if scientific
            else "model_fail"
        ]
    )
    fold_summaries = []
    model_folds = []
    for fold in folds:
        fold_summaries.append(
            {
                "held_pair": fold["held_pair"],
                "training_pairs": fold["training_pairs"],
                "model_digest": fold["model_digest"],
                "nested_fit_evidence": fold["nested_fit_evidence"],
                "base_tube": [value.tolist() for value in fold["base_tube"]],
                "reserved_tube": [value.tolist() for value in fold["reserved_tube"]],
                "cold_squared_error": fold["cold_squared_error"],
                "adapted_squared_error": fold["adapted_squared_error"],
                "innovation_clipping_row_count": fold[
                    "innovation_clipping_row_count"
                ],
                "support": fold["support"],
            }
        )
        model_folds.append(
            {
                "held_pair": fold["held_pair"],
                "model": _model_serializable(fold["model"]),
                "nested_fit_evidence": fold["nested_fit_evidence"],
            }
        )
    detailed = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "source_authentication": authentication,
        "bank_evidence": bank,
        "outer_fold_count": len(folds),
        "folds": fold_summaries,
        "adaptation_usefulness": usefulness,
        "adaptation_enabled": adaptation_enabled,
        "adaptation_status": (
            "causal_innovation_enabled"
            if adaptation_enabled
            else "innovation_disabled_no_measurable_gain"
        ),
        "model_evaluation": model_evaluation,
        "planning_evaluation": planning,
        "model_gate_passed": bool(model_evaluation["passed"]),
        "predicted_feasibility_gate_passed": bool(planning["passed"]),
        "scientific_gate_passed": scientific,
        "route": route,
        "real_tsc_executed": False,
        "plant_step_count": 0,
        "new_raw_count": 0,
        "allowed_in_expert_dataset": False,
    }
    model_evidence = {
        "schema_version": 1,
        "stage": STAGE,
        "feature_digest": bank["feature_digest"],
        "target_digest": bank["target_digest"],
        "folds": model_folds,
    }
    return detailed, model_evidence


def _summary(detailed: Mapping[str, Any], model_sha: str) -> dict[str, Any]:
    model = detailed["model_evaluation"]
    planning = detailed["planning_evaluation"]
    return {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "source_route": detailed["source_authentication"]["route"],
        "trajectory_count": detailed["bank_evidence"]["trajectory_count"],
        "origin_row_count": detailed["bank_evidence"]["origin_row_count"],
        "forecast_point_count": detailed["bank_evidence"]["forecast_point_count"],
        "feature_digest": detailed["bank_evidence"]["feature_digest"],
        "target_digest": detailed["bank_evidence"]["target_digest"],
        "model_evidence_sha256": model_sha,
        "adaptation_enabled": detailed["adaptation_enabled"],
        "adaptation_status": detailed["adaptation_status"],
        "adapted_to_cold_squared_error_ratio": detailed["adaptation_usefulness"][
            "adapted_to_cold_ratio"
        ],
        "maximum_absolute_physical_error": model[
            "maximum_absolute_physical_error"
        ],
        "maximum_reserved_physical_tube_half_width": model[
            "maximum_reserved_physical_tube_half_width"
        ],
        "reserved_tube_containment_rate": model[
            "reserved_tube_containment_rate"
        ],
        "support_rate": model["support_rate"],
        "model_gate_passed": detailed["model_gate_passed"],
        "safe_complete_plan_count": planning["safe_complete_plan_count"],
        "predicted_repaired_failed_baseline_count": planning[
            "predicted_repaired_failed_baseline_count"
        ],
        "predicted_regressed_baseline_pass_count": planning[
            "predicted_regressed_baseline_pass_count"
        ],
        "predicted_baseline_plus_policy_oracle_count": planning[
            "predicted_baseline_plus_policy_oracle_count"
        ],
        "predicted_feasibility_gate_passed": detailed[
            "predicted_feasibility_gate_passed"
        ],
        "scientific_gate_passed": detailed["scientific_gate_passed"],
        "route": detailed["route"],
        "real_tsc_executed": False,
        "plant_step_count": 0,
        "new_raw_count": 0,
        "gate_a_qualified": False,
    }


def run_primary(ctx: Context) -> dict[str, Any]:
    if ctx.paths.stage.exists() and any(ctx.paths.stage.iterdir()):
        raise ValueError("R8R23 primary requires an empty stage directory")
    ctx.paths.analysis.mkdir(parents=True, exist_ok=True)
    ctx.paths.model.mkdir(parents=True, exist_ok=True)
    detailed, model_evidence = compute(ctx)
    model_path = ctx.paths.model / "outer_fold_models.json"
    _write(model_path, model_evidence)
    model_sha = _sha(model_path)
    detailed["model_evidence_sha256"] = model_sha
    detailed_path = ctx.paths.analysis / "primary_detailed.json"
    _write(detailed_path, detailed)
    summary = _summary(detailed, model_sha)
    summary_path = ctx.paths.analysis / "primary_summary.json"
    _write(summary_path, summary)
    _write(
        ctx.paths.manifest,
        {
            "schema_version": 1,
            "stage": STAGE,
            "identity": IDENTITY,
            "config_path": str(ctx.config_path),
            "config_sha256": _sha(ctx.config_path),
            "design_document_sha256": ctx.cfg["design_document_sha256"],
            "source_r8r22_run": str(ctx.r8r22_ctx.paths.run_dir),
            "source_r8r22_stage_state_sha256": ctx.cfg["source_r8r22"][
                "stage_state_sha256"
            ],
            "primary_detailed_sha256": _sha(detailed_path),
            "primary_summary_sha256": _sha(summary_path),
            "model_evidence_sha256": model_sha,
            "zero_new_tsc": True,
            "all_source_trajectories_allowed_in_expert_dataset": False,
        },
    )
    _write(
        ctx.paths.state,
        {
            "schema_version": 1,
            "stage": STAGE,
            "phase_status": "primary_complete",
            "finished": False,
            "route": detailed["route"],
            "primary_detailed_sha256": _sha(detailed_path),
            "primary_summary_sha256": _sha(summary_path),
            "model_evidence_sha256": model_sha,
            "real_tsc_executed": False,
            "plant_step_count": 0,
            "new_raw_count": 0,
        },
    )
    return summary


def postprocess(ctx: Context) -> dict[str, Any]:
    primary_path = ctx.paths.analysis / "primary_detailed.json"
    summary_path = ctx.paths.analysis / "primary_summary.json"
    independent_path = ctx.paths.analysis / "independent.json"
    independent = _read(independent_path)
    primary = _read(primary_path)
    summary = _read(summary_path)
    if (
        independent.get("passed") is not True
        or independent.get("primary_feature_agreement") is not True
        or independent.get("primary_fit_agreement") is not True
        or independent.get("primary_tube_agreement") is not True
        or independent.get("primary_plan_agreement") is not True
        or independent.get("primary_route_agreement") is not True
    ):
        raise ValueError("R8R23 independent agreement is incomplete")
    final = {
        **summary,
        "primary_detailed_sha256": _sha(primary_path),
        "primary_summary_sha256": _sha(summary_path),
        "independent_sha256": _sha(independent_path),
        "primary_independent_agreement": True,
        "passed": bool(primary["scientific_gate_passed"]),
    }
    final_path = ctx.paths.analysis / "final_report.json"
    _write(final_path, final)
    _write(
        ctx.paths.state,
        {
            "schema_version": 1,
            "stage": STAGE,
            "phase_status": "complete",
            "finished": True,
            "verdict": {"passed": final["passed"], "route": final["route"]},
            "primary_detailed_sha256": _sha(primary_path),
            "primary_summary_sha256": _sha(summary_path),
            "independent_sha256": _sha(independent_path),
            "final_report_sha256": _sha(final_path),
            "real_tsc_executed": False,
            "plant_step_count": 0,
            "new_raw_count": 0,
            "stop_reason": (
                "fresh_controller_sentinel_design_required"
                if final["passed"]
                else "model_preflight_gate_failed"
            ),
        },
    )
    return final


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--r8r22-run", type=Path, required=True)
    parser.add_argument("--r8r7-run", type=Path, required=True)
    parser.add_argument("--r8r12-run", type=Path, required=True)
    parser.add_argument("--r8r14-run", type=Path, required=True)
    parser.add_argument("--r8r15-run", type=Path, required=True)
    parser.add_argument("--r8r19-run", type=Path, required=True)
    parser.add_argument("--r8r20-run", type=Path, required=True)
    parser.add_argument("--r8-run", type=Path, required=True)
    parser.add_argument("--r8r1-output", type=Path, required=True)
    parser.add_argument("--r8r6-run", type=Path, required=True)
    parser.add_argument("--source-d1r11-run", type=Path, required=True)
    parser.add_argument("--source-r2-run", type=Path, required=True)
    parser.add_argument("--source-r4-run", type=Path, required=True)
    parser.add_argument("--source-r6-run", type=Path, required=True)
    parser.add_argument("--source-s21-run", type=Path, required=True)
    parser.add_argument("--source-s23r1-output", type=Path, required=True)
    parser.add_argument("--source-s24-run", type=Path, required=True)
    parser.add_argument("--source-d1r9-v1", type=Path, required=True)
    parser.add_argument("--source-d1r9-v2", type=Path, required=True)
    parser.add_argument("--source-d1r10-run", type=Path, required=True)
    parser.add_argument("--source-d1r10-audit", type=Path, required=True)
    parser.add_argument("--source-stage42r3b-run", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3-run", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3-bank-dir", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3t1-run", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3t1-audit-dir", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3t3-controller-bank", type=Path, required=True)
    parser.add_argument("--q1-run", type=Path, required=True)
    parser.add_argument("--q2-run", type=Path, required=True)
    parser.add_argument("--q1-audit", type=Path, required=True)
    parser.add_argument("--q2-audit", type=Path, required=True)
    parser.add_argument("--r3b-server-audit", type=Path, required=True)
    parser.add_argument("--r3b-snapshot-checks", type=Path, required=True)
    parser.add_argument("--command", choices=("primary", "postprocess"), default="primary")
    return parser


def main() -> None:
    args = _parser().parse_args()
    ctx = load_context(args)
    result = run_primary(ctx) if args.command == "primary" else postprocess(ctx)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
