#!/usr/bin/env python3
"""Structurally independent raw/model forensics for frozen R8R5."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r3_independent_forensics as ind3,
    stage4_2r3c3t13s24d1r14r8r4_independent_forensics as ind4,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification as r8,
    stage4_2r3c3t13s24d1r14r8r5_context_robust_observer_holdout as contract,
)


def _read(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def _gzip(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(
            stream,
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
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inventory(directory: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    rows, total = [], 0
    for path in sorted(directory.glob("*.json.gz"), key=lambda value: value.name):
        size, sha = path.stat().st_size, _sha(path)
        total += size
        digest.update(f"{path.name}\0{size}\0{sha}\n".encode())
        rows.append({"name": path.name, "size": size, "sha256": sha})
    return {"count": len(rows), "bytes": total, "digest": digest.hexdigest(), "rows": rows}


def _stage(run_dir: Path) -> Path:
    return run_dir.expanduser().resolve() / contract.RUN_NAME


def _specs(stage: Path) -> list[dict[str, Any]]:
    manifest = _read(stage / "stage_manifest.json")
    specs = _read(stage / "specs" / "holdout_specs.json")
    if len(specs) != 8 or r8._digest(specs) != manifest.get("spec_digest"):
        raise ValueError("R8R5 independent spec digest changed")
    return specs


def _source_baselines(r8_run: Path) -> dict[str, dict[str, Any]]:
    return ind4._source_baselines(r8_run)


def _semantic_state(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return r8.r4._semantic_state(row)


def raw_audit(args: argparse.Namespace, cfg: Mapping[str, Any]) -> dict[str, Any]:
    stage = _stage(args.run_dir)
    specs = _specs(stage)
    sources = _source_baselines(args.r8_run.resolve())
    raw_dir = stage / "raw" / "holdout"
    rows = []
    forbidden_keys = tuple(
        dict.fromkeys(
            r8.R8_FORBIDDEN_TRACE_KEYS
            + (
                "r3c3t13s24d1r14r8r5_future_r17_executed",
                "r3c3t13s24d1r14r8r5_pair_or_history_label_used",
                "r3c3t13s24d1r14r8r5_partition_label_used",
                "r3c3t13s24d1r14r8r5_source_result_used",
            )
        )
    )
    for spec in specs:
        experiment = str(spec["experiment_id"])
        path = raw_dir / f"{experiment}.json.gz"
        try:
            result = _gzip(path)
        except Exception:
            rows.append({"experiment_id": experiment, "runtime_success": False, "passed": False})
            continue
        trajectory = result.get("trajectory") or []
        trace = result.get("controller_trace") or []
        horizon = int(spec["horizon_steps"])
        baseline = sources[str(spec["source_s21_baseline_experiment_id"])]
        identity = bool(
            result.get("stage") == contract.STAGE
            and result.get("campaign_identity") == contract.IDENTITY
            and result.get("controller_revision") == contract.CONTROLLER_REVISION
            and result.get("experiment_id") == experiment
            and result.get("spec") == spec
        )
        full = len(trajectory) == horizon + 1 and len(trace) == horizon
        prefix_state = bool(
            len(trajectory) >= 11
            and all(
                _semantic_state(current) == _semantic_state(reference)
                for current, reference in zip(trajectory[:11], baseline["trajectory"][:11])
            )
        )
        prefix_trace = bool(
            len(trace) >= 10
            and all(
                r8.r4._source_trace_projection(reference, current)
                for current, reference in zip(trace[:10], baseline["controller_trace"][:10])
            )
        )
        action = np.asarray([row.get("action_norm_tsc", []) for row in trace], dtype=float)
        current = np.asarray([row.get("currents_a_tsc", []) for row in trajectory], dtype=float)
        wires = [np.asarray(row.get("wire_currents_a", []), dtype=float) for row in trajectory]
        finite = bool(
            full
            and action.shape == (horizon, 14)
            and current.shape == (horizon + 1, 14)
            and np.all(np.isfinite(action))
            and np.all(np.isfinite(current))
            and all(value.size and np.all(np.isfinite(value)) for value in wires)
            and all(
                math.isfinite(float(row[key]))
                for row in trajectory
                for key in ("R", "Z", "Ip")
            )
            and not any(bool(row.get("abnormal")) for row in trajectory)
        )
        zero_future = bool(full and np.array_equal(action[10:], np.zeros_like(action[10:])))
        constant_future = bool(
            full
            and np.array_equal(
                np.diff(current[10:], axis=0),
                np.zeros_like(np.diff(current[10:], axis=0)),
            )
        )
        forbidden = sum(any(bool(row.get(key)) for key in forbidden_keys) for row in trace)
        payload = _read(stage / "variants" / f"payload_{experiment}.json")
        minimum, maximum = r8.d1r11.s21.s13._current_limits_tsc(payload)
        center, half = 0.5 * (minimum + maximum), 0.5 * (maximum - minimum)
        utilization = (
            float(np.max(np.abs((current - center) / half)))
            if current.shape == (horizon + 1, 14)
            else math.inf
        )
        action_abs = float(np.max(np.abs(action))) if action.shape == (horizon, 14) else math.inf
        snapshot = bool(
            str(spec.get("restart_snapshot_dir") or "")
            and str(spec.get("restart_snapshot_manifest_digest") or "")
            and payload.get("stage4_2r3c3t13s24d1r14r8_snapshot_manifest_digest")
            == spec.get("restart_snapshot_manifest_digest")
        )
        calibration = r8.r4._calibration_exact(trace)
        passed = bool(
            result.get("completed")
            and result.get("success")
            and identity
            and full
            and prefix_state
            and prefix_trace
            and calibration
            and finite
            and zero_future
            and constant_future
            and snapshot
            and forbidden == 0
            and action_abs <= 1.0 + 1e-12
            and utilization <= 0.55 + 1e-12
        )
        rows.append(
            {
                "experiment_id": experiment,
                "pair_id": spec["pair_id"],
                "history_member": spec["history_member"],
                "runtime_success": bool(result.get("success")),
                "full_horizon": full,
                "source_prefix_state_exact": prefix_state,
                "source_prefix_trace_exact": prefix_trace,
                "calibration_exact": calibration,
                "zero_future_action_exact": zero_future,
                "constant_future_commanded_current_exact": constant_future,
                "source_restart_snapshot_authenticated": snapshot,
                "finite": finite,
                "forbidden_trace_count": forbidden,
                "maximum_total_normalized_action_abs": action_abs,
                "maximum_current_utilization": utilization,
                "failure_reason": str(result.get("failure_reason") or ""),
                "passed": passed,
            }
        )
    inventory = _inventory(raw_dir)
    primary_path = stage / "analysis" / "holdout_raw_primary.json"
    primary = _read(primary_path)
    numerical = ind3._agrees(primary.get("rows"), rows, cfg)
    result = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "audit_kind": "holdout_raw_independent",
        "raw_inventory": inventory,
        "passed_count": sum(bool(row["passed"]) for row in rows),
        "primary_sha256": _sha(primary_path),
        "primary_numerical_agreement": numerical,
        "passed": bool(
            inventory["count"] == 8
            and len(rows) == 8
            and all(bool(row["passed"]) for row in rows)
            and inventory == primary.get("raw_inventory")
            and numerical
        ),
    }
    if not result["passed"]:
        raise ValueError("R8R5 independent raw audit disagrees")
    _write(stage / "analysis" / "holdout_raw_independent.json", result)
    return result


def _development_rows(
    args: argparse.Namespace, cfg: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    prior, prior_signature = ind4._prior_rows(args, cfg)
    source_args = argparse.Namespace(**{**vars(args), "run_dir": args.r8r4_run})
    fresh, fresh_signature = ind4._fresh_rows(source_args, cfg, "development")
    rows = sorted(prior + fresh, key=lambda row: row["row_id"])
    if (
        len({str(row["pair_id"]) for row in rows}) != 16
        or len({f"{row['pair_id']}|{row['history_member']}" for row in rows}) != 32
    ):
        raise ValueError("R8R5 independent development coverage changed")
    return rows, {"prior": prior_signature, "fresh_r8r4": fresh_signature}


def _candidate(cfg: Mapping[str, Any]) -> tuple[str, int, float, float]:
    value = cfg["fixed_model_contract"]
    return (
        str(value["family"]),
        int(value["pca_rank"]),
        float(value["bandwidth_multiplier"]),
        float(value["ridge"]),
    )


def _fixed_outer(
    items: Sequence[Mapping[str, Any]],
    candidate: tuple[str, int, float, float],
    cfg: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows, folds = [], []
    for pair in sorted({str(item["pair_id"]) for item in items}):
        training = [item for item in items if str(item["pair_id"]) != pair]
        held = [item for item in items if str(item["pair_id"]) == pair]
        model = ind3._fit(training, candidate, cfg)
        current = [
            ind4._metric(item, value, cfg)
            for item, value in zip(held, ind3._predict(model, held, cfg))
        ]
        rows.extend(current)
        folds.append(
            {
                "held_pair_id": pair,
                "training_pair_count": 15,
                "held_origin_row_count": len(held),
                "point_pass_count": sum(bool(row["passed"]) for row in current),
                "finite_exclusion_violation_count": sum(
                    int(row["finite_exclusion_violation_count"]) for row in current
                ),
            }
        )
    return sorted(rows, key=lambda row: row["row_id"]), folds


def _context_tube(
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
        values = [
            ratio
            for row, ratio in zip(rows, ratios)
            if f"{row['pair_id']}|{row['history_member']}" == context
        ]
        context_values[context] = float(
            np.quantile(
                np.asarray(values),
                float(tube_cfg["per_context_row_ratio_quantile"]),
                method="higher",
            )
        )
    calibration = max([aggregate, *context_values.values()])
    scalar = max(
        float(tube_cfg["scalar_floor"]),
        float(tube_cfg["blind_holdout_reserve_multiplier"]) * calibration,
    )
    tube = scalar * base
    return tube, {
        "aggregate_q95_row_ratio": aggregate,
        "per_context_q90_row_ratios": context_values,
        "calibration_ratio": calibration,
        "reserve_multiplier": float(tube_cfg["blind_holdout_reserve_multiplier"]),
        "scalar": scalar,
    }


def development_model_audit(
    args: argparse.Namespace, cfg: Mapping[str, Any]
) -> dict[str, Any]:
    stage = _stage(args.run_dir)
    primary_path = stage / "analysis" / "development_model_primary_detailed.json"
    summary_path = stage / "analysis" / "development_model_primary_summary.json"
    primary, summary = _read(primary_path), _read(summary_path)
    items, signature = _development_rows(args, cfg)
    candidate = _candidate(cfg)
    rows, folds = _fixed_outer(items, candidate, cfg)
    point = ind4._point(rows, cfg)
    tube, tube_derivation = _context_tube(rows, cfg)
    tube_evaluation = ind4._practical(rows, tube, cfg)
    caps = np.asarray(cfg["tube_contract"]["component_caps_physical"], dtype=float)
    tube_cap_passed = bool(np.all(tube <= caps[None, :] + 1e-15))
    scientific = bool(
        len(folds) == int(cfg["gates"]["required_development_outer_fold_count"])
        and point["passed"]
        and tube_evaluation["passed"]
        and tube_cap_passed
    )
    route = str(cfg["routes"]["pass" if scientific else "development_model_fail"])
    model_sha = tube_sha = ""
    if scientific:
        model = ind3._fit(items, candidate, cfg)
        artifact = {
            "schema_version": 1,
            "stage": contract.STAGE,
            "campaign_identity": contract.IDENTITY,
            "feature_contract": cfg["feature_contract"],
            "training_pair_count": 16,
            "fixed_candidate": ind3._candidate_dict(candidate),
            "source_r8r4_state_sha256": cfg["source_r8r4_contract"]["stage_state_sha256"],
            "model": ind4._serializable(model, tube),
        }
        expected_model = stage / "analysis" / "development_model_independent_expected_model.json"
        expected_tube = stage / "analysis" / "development_model_independent_expected_tube.json"
        _write(expected_model, artifact)
        _write(
            expected_tube,
            {
                "schema_version": 1,
                "stage": contract.STAGE,
                "campaign_identity": contract.IDENTITY,
                "tube_physical": tube.tolist(),
                "derivation": "context_robust_global_higher_quantile_scaled_v1",
                "tube_derivation": tube_derivation,
                "fixed_candidate": ind3._candidate_dict(candidate),
            },
        )
        model_sha, tube_sha = _sha(expected_model), _sha(expected_tube)
    numerical = bool(
        ind3._agrees(primary.get("source_signature"), signature, cfg)
        and ind3._agrees(primary.get("outer_folds"), folds, cfg)
        and ind3._agrees(primary.get("outer_rows"), rows, cfg)
        and ind3._agrees(primary.get("point_evaluation"), point, cfg)
        and ind3._agrees(primary.get("tube_derivation"), tube_derivation, cfg)
        and ind3._agrees(primary.get("tube_physical"), tube.tolist(), cfg)
        and ind3._agrees(primary.get("tube_evaluation"), tube_evaluation, cfg)
        and primary.get("tube_cap_passed") is tube_cap_passed
    )
    outcome = bool(
        primary.get("route") == route
        and summary.get("route") == route
        and bool(primary.get("scientific_gate_passed")) is scientific
        and bool(summary.get("scientific_gate_passed")) is scientific
    )
    artifact_agreement = bool(
        primary.get("observer_model_sha256") == model_sha
        and primary.get("observer_tube_sha256") == tube_sha
        and (
            not scientific
            or (
                _sha(stage / "model" / "observer_model.json") == model_sha
                and _sha(stage / "model" / "observer_tube.json") == tube_sha
            )
        )
    )
    result = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "audit_kind": "development_model_independent",
        "source_signature": signature,
        "fixed_candidate": ind3._candidate_dict(candidate),
        "point_evaluation": point,
        "tube_derivation": tube_derivation,
        "tube_evaluation": {key: value for key, value in tube_evaluation.items() if key != "rows"},
        "route": route,
        "scientific_gate_passed": scientific,
        "observer_model_sha256": model_sha,
        "observer_tube_sha256": tube_sha,
        "primary_summary_sha256": _sha(summary_path),
        "primary_numerical_agreement": numerical,
        "primary_outcome_agreement": outcome,
        "artifact_hash_agreement": artifact_agreement,
        "holdout_raw_count": _inventory(stage / "raw" / "holdout")["count"],
        "passed": bool(numerical and outcome and artifact_agreement),
    }
    if not result["passed"] or result["holdout_raw_count"] != 0:
        raise ValueError("R8R5 independent development audit disagrees")
    _write(stage / "analysis" / "development_model_independent.json", result)
    return result


def _holdout_rows(
    args: argparse.Namespace, cfg: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    stage = _stage(args.run_dir)
    specs = _specs(stage)
    scales = np.asarray(cfg["bank_contract"]["visible_scales"], dtype=float)
    issues = set(map(int, cfg["bank_contract"]["prescribed_issue_task_steps"]))
    rows, hashes = [], {}
    for spec in specs:
        path = stage / "raw" / "holdout" / f"{spec['experiment_id']}.json.gz"
        result = _gzip(path)
        visible = ind3.frozen._visible(result["trajectory"], scales)
        actions, currents = ind3._actions(result), ind3._currents(result)
        for origin in range(10, len(visible) - 12):
            feature = ind3._feature(
                visible[: origin + 1],
                actions[:origin],
                currents[: origin + 1],
                ind3._target(spec),
                origin,
                cfg,
            )
            future = visible[origin + 1 : origin + 13]
            rows.append(
                {
                    "row_id": f"holdout|{spec['pair_id']}|{spec['history_member']}|origin{origin:02d}",
                    "context_id": f"{spec['pair_id']}|{spec['history_member']}",
                    "pair_id": str(spec["pair_id"]),
                    "history_member": str(spec["history_member"]),
                    "origin_task_step": origin,
                    "prescribed_issue": origin in issues,
                    "feature": feature,
                    "origin_visible": visible[origin],
                    "target_delta": future[:, 2:5] - visible[origin, 2:5],
                    "future_visible": future,
                }
            )
        hashes[str(spec["experiment_id"])] = _sha(path)
    signature = {
        "pair_count": len({row["pair_id"] for row in rows}),
        "context_count": len({row["context_id"] for row in rows}),
        "origin_row_count": len(rows),
        "prescribed_issue_row_count": sum(bool(row["prescribed_issue"]) for row in rows),
        "feature_dimension": 353,
        "raw_sha256": hashes,
        "forbidden_predictor_input_count": 0,
        "future_input_count": 0,
        "allowed_in_expert_dataset": False,
    }
    if signature["pair_count"] != 4 or signature["context_count"] != 8 or signature["prescribed_issue_row_count"] != 32:
        raise ValueError("R8R5 independent holdout coverage changed")
    return sorted(rows, key=lambda row: row["row_id"]), signature


def _artifact_model(value: Mapping[str, Any]) -> dict[str, Any]:
    return ind4._artifact_model(value)


def holdout_model_audit(
    args: argparse.Namespace, cfg: Mapping[str, Any]
) -> dict[str, Any]:
    stage = _stage(args.run_dir)
    primary_path = stage / "analysis" / "holdout_model_primary_detailed.json"
    summary_path = stage / "analysis" / "holdout_model_primary_summary.json"
    primary, summary = _read(primary_path), _read(summary_path)
    model_path, tube_path = stage / "model" / "observer_model.json", stage / "model" / "observer_tube.json"
    items, signature = _holdout_rows(args, cfg)
    model = _artifact_model(_read(model_path))
    rows = [
        ind4._metric(item, value, cfg)
        for item, value in zip(items, ind3._predict(model, items, cfg))
    ]
    tube = np.asarray(_read(tube_path)["tube_physical"], dtype=float)
    evaluation = ind4._practical(rows, tube, cfg)
    coverage = bool(
        len({row["pair_id"] for row in rows}) == 4
        and len({(row["pair_id"], row["history_member"]) for row in rows}) == 8
        and sum(bool(row["prescribed_issue"]) for row in rows) == 32
    )
    scientific = bool(coverage and evaluation["passed"])
    route = str(cfg["routes"]["pass" if scientific else "holdout_model_fail"])
    numerical = bool(
        ind3._agrees(primary.get("holdout_signature"), signature, cfg)
        and ind3._agrees(primary.get("holdout_evaluation"), evaluation, cfg)
        and primary.get("holdout_coverage_passed") is coverage
    )
    outcome = bool(
        primary.get("route") == route
        and summary.get("route") == route
        and bool(primary.get("scientific_gate_passed")) is scientific
        and bool(summary.get("scientific_gate_passed")) is scientific
    )
    result = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "audit_kind": "holdout_model_independent",
        "holdout_signature": signature,
        "holdout_evaluation": {key: value for key, value in evaluation.items() if key != "rows"},
        "route": route,
        "scientific_gate_passed": scientific,
        "observer_model_sha256": _sha(model_path),
        "observer_tube_sha256": _sha(tube_path),
        "primary_summary_sha256": _sha(summary_path),
        "primary_numerical_agreement": numerical,
        "primary_outcome_agreement": outcome,
        "passed": bool(numerical and outcome),
    }
    if not result["passed"]:
        raise ValueError("R8R5 independent holdout audit disagrees")
    _write(stage / "analysis" / "holdout_model_independent.json", result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--r8-run", type=Path, required=True)
    parser.add_argument("--r8r4-run", type=Path, required=True)
    parser.add_argument("--source-r2-run", type=Path, required=True)
    parser.add_argument("--source-r4-run", type=Path, required=True)
    parser.add_argument("--source-r6-run", type=Path, required=True)
    parser.add_argument(
        "--audit-kind",
        choices=("development_model", "holdout_raw", "holdout_model"),
        required=True,
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    cfg = _read(args.config.expanduser().resolve())
    contract.validate_config(cfg, project_root=Path(__file__).resolve().parents[3])
    if args.audit_kind == "development_model":
        result = development_model_audit(args, cfg)
    elif args.audit_kind == "holdout_raw":
        result = raw_audit(args, cfg)
    else:
        result = holdout_model_audit(args, cfg)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
