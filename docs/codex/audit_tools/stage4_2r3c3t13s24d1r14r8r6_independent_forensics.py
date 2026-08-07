#!/usr/bin/env python3
"""Structurally independent zero-TSC audit for frozen R8R6."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r3_independent_forensics as ind3,
    stage4_2r3c3t13s24d1r14r8r4_independent_forensics as ind4,
    stage4_2r3c3t13s24d1r14r8r5_independent_forensics as ind5,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r5_context_robust_observer_holdout as source_contract,
    stage4_2r3c3t13s24d1r14r8r6_causal_one_step_innovation_observer as contract,
)


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


def _source_stage(run_dir: Path) -> Path:
    return run_dir.expanduser().resolve() / source_contract.RUN_NAME


def _stage(run_dir: Path) -> Path:
    return run_dir.expanduser().resolve() / contract.RUN_NAME


def _inventory(directory: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    rows, total = [], 0
    for path in sorted(directory.glob("*.json.gz"), key=lambda item: item.name):
        size, fingerprint = path.stat().st_size, _sha(path)
        total += size
        digest.update(f"{path.name}\0{size}\0{fingerprint}\n".encode())
        rows.append({"name": path.name, "size": size, "sha256": fingerprint})
    return {"count": len(rows), "bytes": total, "digest": digest.hexdigest(), "rows": rows}


def _authenticate(args: argparse.Namespace, cfg: Mapping[str, Any]) -> dict[str, Any]:
    stage = _source_stage(args.r8r5_run)
    expected = cfg["source_r8r5_contract"]
    analysis = {
        "holdout_raw_primary": stage / "analysis" / "holdout_raw_primary.json",
        "holdout_raw_independent": stage / "analysis" / "holdout_raw_independent.json",
        "development_model_primary_detailed": stage / "analysis" / "development_model_primary_detailed.json",
        "development_model_primary_summary": stage / "analysis" / "development_model_primary_summary.json",
        "development_model_independent": stage / "analysis" / "development_model_independent.json",
        "holdout_model_primary_detailed": stage / "analysis" / "holdout_model_primary_detailed.json",
        "holdout_model_primary_summary": stage / "analysis" / "holdout_model_primary_summary.json",
        "holdout_model_independent": stage / "analysis" / "holdout_model_independent.json",
        "final_report": stage / "analysis" / "final_report.json",
    }
    manifest, state_path = stage / "stage_manifest.json", stage / "stage_state.json"
    model, tube = stage / "model" / "observer_model.json", stage / "model" / "observer_tube.json"
    if (
        _sha(manifest) != expected["stage_manifest_sha256"]
        or _sha(state_path) != expected["stage_state_sha256"]
        or _sha(model) != expected["observer_model_sha256"]
        or _sha(tube) != expected["observer_tube_sha256"]
        or any(_sha(path) != expected[f"{name}_sha256"] for name, path in analysis.items())
    ):
        raise ValueError("R8R6 independent R8R5 hash authentication failed")
    state, final = _read(state_path), _read(analysis["final_report"])
    raw = _inventory(stage / "raw" / "holdout")
    if (
        state.get("phase_status") != "complete"
        or state.get("finished") is not True
        or (state.get("verdict") or {}).get("route") != expected["required_route"]
        or (state.get("verdict") or {}).get("passed") is not False
        or final.get("scientific_gate_passed") is not False
        or raw["count"] != int(expected["holdout_raw_count"])
        or raw["bytes"] != int(expected["holdout_raw_bytes"])
        or raw["digest"] != expected["holdout_raw_digest"]
    ):
        raise ValueError("R8R6 independent R8R5 outcome authentication failed")
    return {
        "stage_manifest_sha256": _sha(manifest),
        "stage_state_sha256": _sha(state_path),
        "holdout_raw_inventory": raw,
        "observer_model_sha256": _sha(model),
        "observer_tube_sha256": _sha(tube),
    }


def _bank(
    args: argparse.Namespace, cfg: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    root = Path(__file__).resolve().parents[3]
    source_cfg = _read((root / str(cfg["source_r8r5_config"])).resolve())
    source_args = argparse.Namespace(
        run_dir=args.r8r5_run,
        r8_run=args.r8_run,
        r8r4_run=args.r8r4_run,
        source_r2_run=args.source_r2_run,
        source_r4_run=args.source_r4_run,
        source_r6_run=args.source_r6_run,
    )
    development, development_signature = ind5._development_rows(source_args, source_cfg)
    holdout, holdout_signature = ind5._holdout_rows(source_args, source_cfg)
    rows = sorted(development + holdout, key=lambda row: str(row["row_id"]))
    signature = {
        "development": development_signature,
        "r8r5_holdout": holdout_signature,
        "physical_pair_count": len({str(row["pair_id"]) for row in rows}),
        "history_context_count": len(
            {f"{row['pair_id']}|{row['history_member']}" for row in rows}
        ),
        "origin_row_count": len(rows),
        "prescribed_issue_row_count": sum(bool(row["prescribed_issue"]) for row in rows),
        "feature_dimension": len(np.asarray(rows[0]["feature"])),
        "forbidden_predictor_input_count": 0,
        "future_input_count": 0,
        "allowed_in_expert_dataset": False,
    }
    bank = cfg["bank_contract"]
    if (
        signature["physical_pair_count"] != int(bank["physical_pair_count"])
        or signature["history_context_count"] != int(bank["history_context_count"])
        or signature["origin_row_count"] != int(bank["origin_row_count"])
        or signature["prescribed_issue_row_count"] != int(bank["prescribed_issue_row_count"])
        or signature["feature_dimension"] != int(bank["feature_dimension"])
    ):
        raise ValueError("R8R6 independent bank coverage changed")
    return rows, signature


def _adapt(
    item: Mapping[str, Any],
    previous_prediction: Sequence[Sequence[float]],
    cold_prediction: Sequence[Sequence[float]],
    cfg: Mapping[str, Any],
) -> tuple[np.ndarray, dict[str, Any]]:
    origin = np.asarray(item["origin_visible"], dtype=float)
    previous = np.asarray(previous_prediction, dtype=float)
    cold = np.asarray(cold_prediction, dtype=float)
    scales = np.asarray(cfg["bank_contract"]["visible_scales"], dtype=float)
    dt = float(cfg["bank_contract"]["dt_s"])
    clip = np.asarray(cfg["innovation_contract"]["clip_physical"], dtype=float)
    rho = float(cfg["innovation_contract"]["persistence"])
    raw_scaled = origin[2:5] - previous[0, 2:5]
    raw_physical = raw_scaled * scales[2:5]
    clipped_physical = np.maximum(-clip, np.minimum(clip, raw_physical))
    clipped_scaled = clipped_physical / scales[2:5]
    output = cold.copy()
    for lag in range(12):
        output[lag, 2:5] += (rho**lag) * clipped_scaled
    output[:, 0] = origin[0] + np.cumsum(output[:, 2]) * dt * scales[2] / scales[0]
    output[:, 1] = origin[1] + np.cumsum(output[:, 3]) * dt * scales[3] / scales[1]
    return output, {
        "innovation_physical": raw_physical.tolist(),
        "clipped_innovation_physical": clipped_physical.tolist(),
        "clip_activated": bool(np.any(np.abs(raw_physical) > clip + 1e-15)),
        "persistence": rho,
    }


def _outer(
    items: Sequence[Mapping[str, Any]],
    candidate: tuple[str, int, float, float],
    cfg: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    startup, cold_rows, adapted_rows, folds = [], [], [], []
    for pair in sorted({str(item["pair_id"]) for item in items}):
        training = [item for item in items if str(item["pair_id"]) != pair]
        held = [item for item in items if str(item["pair_id"]) == pair]
        model = ind3._fit(training, candidate, cfg)
        values = ind3._predict(model, held, cfg)
        predictions = {str(item["row_id"]): value for item, value in zip(held, values)}
        fold_startup = fold_adapted = fold_clipped = 0
        for context in sorted(
            {f"{item['pair_id']}|{item['history_member']}" for item in held}
        ):
            current = sorted(
                [
                    item
                    for item in held
                    if f"{item['pair_id']}|{item['history_member']}" == context
                ],
                key=lambda item: int(item["origin_task_step"]),
            )
            origins = [int(item["origin_task_step"]) for item in current]
            if not origins or origins[0] != 10 or origins != list(range(10, origins[-1] + 1)):
                raise ValueError("R8R6 independent context origin sequence changed")
            for index, item in enumerate(current):
                cold_prediction = predictions[str(item["row_id"])]
                cold_row = ind4._metric(item, cold_prediction, cfg)
                if index == 0:
                    cold_row["observer_mode"] = "cold_startup_fallback"
                    startup.append(cold_row)
                    fold_startup += int(bool(cold_row["passed"]))
                    continue
                previous = current[index - 1]
                adapted_prediction, audit = _adapt(
                    item, predictions[str(previous["row_id"])], cold_prediction, cfg
                )
                adapted = ind4._metric(item, adapted_prediction, cfg)
                adapted.update(audit)
                adapted["observer_mode"] = "causal_one_step_innovation"
                cold_row["observer_mode"] = "cold_comparator"
                cold_rows.append(cold_row)
                adapted_rows.append(adapted)
                fold_adapted += int(bool(adapted["passed"]))
                fold_clipped += int(bool(audit["clip_activated"]))
        folds.append(
            {
                "held_pair_id": pair,
                "training_pair_count": 19,
                "held_context_count": len(
                    {f"{item['pair_id']}|{item['history_member']}" for item in held}
                ),
                "held_origin_row_count": len(held),
                "startup_fallback_pass_count": fold_startup,
                "adapted_point_pass_count": fold_adapted,
                "innovation_clip_row_count": fold_clipped,
            }
        )
    return (
        sorted(startup, key=lambda row: str(row["row_id"])),
        sorted(cold_rows, key=lambda row: str(row["row_id"])),
        sorted(adapted_rows, key=lambda row: str(row["row_id"])),
        folds,
    )


def _startup(rows: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> dict[str, Any]:
    residual = np.asarray([row["absolute_residual_physical"] for row in rows], dtype=float)
    required = int(cfg["gates"]["required_startup_fallback_pass_count"])
    result = {
        "row_count": len(rows),
        "required_pass_count": required,
        "point_pass_count": sum(bool(row["passed"]) for row in rows),
        "finite_exclusion_violation_count": sum(
            int(row["finite_exclusion_violation_count"]) for row in rows
        ),
        "maximum_absolute_physical_error": np.max(residual, axis=(0, 1)).tolist(),
        "maximum_absolute_scaled_point_error": max(
            float(row["maximum_absolute_scaled_point_error"]) for row in rows
        ),
        "rows": list(rows),
    }
    result["passed"] = bool(
        len(rows) == required
        and result["point_pass_count"] == required
        and result["finite_exclusion_violation_count"] == 0
    )
    return result


def _tube(
    rows: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> tuple[np.ndarray, dict[str, Any]]:
    residual = np.asarray([row["absolute_residual_physical"] for row in rows], dtype=float)
    tube_cfg = cfg["tube_contract"]
    floor = np.asarray(tube_cfg["component_floor_physical"], dtype=float)
    base = np.quantile(
        residual,
        float(tube_cfg["base_absolute_residual_quantile"]),
        axis=0,
        method="higher",
    ) + floor[None, :]
    ratios = np.max(residual / base[None, :, :], axis=(1, 2))
    aggregate = float(
        np.quantile(
            ratios,
            float(tube_cfg["aggregate_row_ratio_quantile"]),
            method="higher",
        )
    )
    context_values = {}
    for context in sorted({f"{row['pair_id']}|{row['history_member']}" for row in rows}):
        current = np.asarray(
            [
                ratio
                for row, ratio in zip(rows, ratios)
                if f"{row['pair_id']}|{row['history_member']}" == context
            ]
        )
        context_values[context] = float(
            np.quantile(
                current,
                float(tube_cfg["per_context_row_ratio_quantile"]),
                method="higher",
            )
        )
    calibration = max([aggregate, *context_values.values()])
    scalar = max(
        float(tube_cfg["scalar_floor"]),
        float(tube_cfg["prospective_reserve_multiplier"]) * calibration,
    )
    return scalar * base, {
        "aggregate_q95_row_ratio": aggregate,
        "per_context_q90_row_ratios": context_values,
        "calibration_ratio": calibration,
        "prospective_reserve_multiplier": float(tube_cfg["prospective_reserve_multiplier"]),
        "scalar": scalar,
    }


def _usefulness(
    cold_rows: Sequence[Mapping[str, Any]],
    adapted_rows: Sequence[Mapping[str, Any]],
    cfg: Mapping[str, Any],
) -> dict[str, Any]:
    cold = {str(row["row_id"]): row for row in cold_rows}
    adapted = {str(row["row_id"]): row for row in adapted_rows}
    if set(cold) != set(adapted):
        raise ValueError("R8R6 independent comparator coverage changed")
    cold_mean = float(np.mean([float(row["mean_squared_scaled_error"]) for row in cold.values()]))
    adapted_mean = float(
        np.mean([float(row["mean_squared_scaled_error"]) for row in adapted.values()])
    )
    contexts = sorted({f"{row['pair_id']}|{row['history_member']}" for row in adapted.values()})
    context_counts, improved, no_regression = {}, 0, True
    for context in contexts:
        keys = [
            key
            for key, row in adapted.items()
            if f"{row['pair_id']}|{row['history_member']}" == context
        ]
        cold_value = float(np.mean([float(cold[key]["mean_squared_scaled_error"]) for key in keys]))
        adapted_value = float(
            np.mean([float(adapted[key]["mean_squared_scaled_error"]) for key in keys])
        )
        ratio = adapted_value / cold_value if cold_value > 0.0 else float("inf")
        current_improved = adapted_value < cold_value
        current_no_regression = ratio <= float(cfg["gates"]["maximum_context_mse_ratio"]) + 1e-15
        improved += int(current_improved)
        no_regression = no_regression and current_no_regression
        context_counts[context] = {
            "cold_mean_squared_scaled_error": cold_value,
            "adapted_mean_squared_scaled_error": adapted_value,
            "adapted_to_cold_ratio": ratio,
            "strictly_improved": current_improved,
            "no_more_than_five_percent_regression": current_no_regression,
        }
    ratio = adapted_mean / cold_mean if cold_mean > 0.0 else float("inf")
    result = {
        "cold_mean_squared_scaled_error": cold_mean,
        "adapted_mean_squared_scaled_error": adapted_mean,
        "adapted_to_cold_ratio": ratio,
        "required_maximum_aggregate_ratio": float(cfg["gates"]["maximum_aggregate_mse_ratio"]),
        "strictly_improved_context_count": improved,
        "required_strictly_improved_context_count": int(
            cfg["gates"]["minimum_strictly_improved_context_count"]
        ),
        "all_contexts_within_regression_limit": no_regression,
        "context_counts": context_counts,
    }
    result["passed"] = bool(
        ratio <= float(cfg["gates"]["maximum_aggregate_mse_ratio"]) + 1e-15
        and no_regression
        and improved >= int(cfg["gates"]["minimum_strictly_improved_context_count"])
    )
    return result


def audit(args: argparse.Namespace, cfg: Mapping[str, Any]) -> dict[str, Any]:
    source_auth = _authenticate(args, cfg)
    stage = _stage(args.run_dir)
    primary_path = stage / "analysis" / "primary_detailed.json"
    summary_path = stage / "analysis" / "primary_summary.json"
    primary, summary = _read(primary_path), _read(summary_path)
    items, source_signature = _bank(args, cfg)
    candidate = (
        "linear",
        int(cfg["fixed_model_contract"]["pca_rank"]),
        0.0,
        float(cfg["fixed_model_contract"]["ridge"]),
    )
    startup_rows, cold_rows, adapted_rows, folds = _outer(items, candidate, cfg)
    startup = _startup(startup_rows, cfg)
    tube, tube_derivation = _tube(adapted_rows, cfg)
    adapted_evaluation = ind4._practical(adapted_rows, tube, cfg)
    usefulness = _usefulness(cold_rows, adapted_rows, cfg)
    caps = np.asarray(cfg["tube_contract"]["component_caps_physical"], dtype=float)
    tube_cap_passed = bool(np.all(tube <= caps[None, :] + 1e-15))
    observer_qualified = bool(
        startup["passed"]
        and adapted_evaluation["passed"]
        and tube_cap_passed
        and len(folds) == int(cfg["gates"]["required_outer_fold_count"])
    )
    adaptive = bool(observer_qualified and usefulness["passed"])
    if not observer_qualified:
        route = str(cfg["routes"]["observer_fail"])
    elif adaptive:
        route = str(cfg["routes"]["adaptive_pass"])
    else:
        route = str(cfg["routes"]["static_pass"])

    model_sha = tube_sha = innovation_sha = ""
    if observer_qualified:
        model = ind3._fit(items, candidate, cfg)
        expected_model = stage / "analysis" / "independent_expected_model.json"
        expected_tube = stage / "analysis" / "independent_expected_tube.json"
        expected_innovation = stage / "analysis" / "independent_expected_innovation.json"
        _write(
            expected_model,
            {
                "schema_version": 1,
                "stage": contract.STAGE,
                "campaign_identity": contract.IDENTITY,
                "feature_contract": cfg["feature_contract"],
                "training_pair_count": 20,
                "training_origin_row_count": 600,
                "fixed_candidate": ind3._candidate_dict(candidate),
                "source_r8r5_state_sha256": cfg["source_r8r5_contract"]["stage_state_sha256"],
                "model": ind4._serializable(model, tube),
            },
        )
        _write(
            expected_tube,
            {
                "schema_version": 1,
                "stage": contract.STAGE,
                "campaign_identity": contract.IDENTITY,
                "tube_physical": tube.tolist(),
                "derivation": "causal_adapted_context_robust_global_higher_quantile_scaled_v1",
                "tube_derivation": tube_derivation,
                "fixed_candidate": ind3._candidate_dict(candidate),
            },
        )
        _write(
            expected_innovation,
            {
                "schema_version": 1,
                "stage": contract.STAGE,
                "campaign_identity": contract.IDENTITY,
                "innovation_contract": cfg["innovation_contract"],
                "adaptation_enabled": adaptive,
                "fallback": "cold_observer_until_prior_one_step_prediction_is_observable",
                "selection_reason": (
                    "prospective_measurable_benefit_passed"
                    if adaptive
                    else "prospective_measurable_benefit_failed_use_static_observer"
                ),
            },
        )
        model_sha, tube_sha, innovation_sha = (
            _sha(expected_model),
            _sha(expected_tube),
            _sha(expected_innovation),
        )

    numerical = bool(
        ind3._agrees(primary.get("source_signature"), source_signature, cfg)
        and ind3._agrees(primary.get("outer_folds"), folds, cfg)
        and ind3._agrees(primary.get("startup_evaluation"), startup, cfg)
        and ind3._agrees(primary.get("cold_comparator_rows"), cold_rows, cfg)
        and ind3._agrees(primary.get("tube_derivation"), tube_derivation, cfg)
        and ind3._agrees(primary.get("tube_physical"), tube.tolist(), cfg)
        and ind3._agrees(primary.get("adapted_evaluation"), adapted_evaluation, cfg)
        and ind3._agrees(primary.get("usefulness_evaluation"), usefulness, cfg)
        and primary.get("tube_cap_passed") is tube_cap_passed
    )
    outcome = bool(
        primary.get("route") == route
        and summary.get("route") == route
        and bool(primary.get("observer_qualification_passed")) is observer_qualified
        and bool(primary.get("adaptation_usefulness_passed")) is bool(usefulness["passed"])
        and bool(summary.get("observer_qualification_passed")) is observer_qualified
        and bool(summary.get("adaptation_usefulness_passed")) is bool(usefulness["passed"])
    )
    artifact = bool(
        primary.get("observer_model_sha256") == model_sha
        and primary.get("observer_tube_sha256") == tube_sha
        and primary.get("innovation_contract_sha256") == innovation_sha
        and (
            not observer_qualified
            or (
                _sha(stage / "model" / "observer_model.json") == model_sha
                and _sha(stage / "model" / "observer_tube.json") == tube_sha
                and _sha(stage / "model" / "innovation_contract.json") == innovation_sha
            )
        )
    )
    result = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "audit_kind": "causal_one_step_innovation_observer_independent",
        "source_authentication": source_auth,
        "source_signature": source_signature,
        "fixed_candidate": ind3._candidate_dict(candidate),
        "startup_evaluation": {key: value for key, value in startup.items() if key != "rows"},
        "tube_derivation": tube_derivation,
        "tube_evaluation": {
            key: value for key, value in adapted_evaluation.items() if key != "rows"
        },
        "usefulness_evaluation": usefulness,
        "observer_qualification_passed": observer_qualified,
        "adaptation_usefulness_passed": bool(usefulness["passed"]),
        "observer_model_sha256": model_sha,
        "observer_tube_sha256": tube_sha,
        "innovation_contract_sha256": innovation_sha,
        "route": route,
        "primary_summary_sha256": _sha(summary_path),
        "primary_numerical_agreement": numerical,
        "primary_outcome_agreement": outcome,
        "artifact_hash_agreement": artifact,
        "real_tsc_executed": False,
        "new_raw_count": 0,
        "passed": bool(numerical and outcome and artifact),
    }
    if not result["passed"]:
        raise ValueError("R8R6 independent audit disagrees")
    _write(stage / "analysis" / "independent.json", result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--r8r5-run", type=Path, required=True)
    parser.add_argument("--r8-run", type=Path, required=True)
    parser.add_argument("--r8r4-run", type=Path, required=True)
    parser.add_argument("--source-r2-run", type=Path, required=True)
    parser.add_argument("--source-r4-run", type=Path, required=True)
    parser.add_argument("--source-r6-run", type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    path = args.config.expanduser().resolve()
    cfg = _read(path)
    contract.validate_config(cfg, project_root=Path(__file__).resolve().parents[3])
    result = audit(args, cfg)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
