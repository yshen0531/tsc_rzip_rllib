#!/usr/bin/env python3
"""Structurally independent raw/model forensics for frozen R8R4."""

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
    stage4_2r3c3t13s24d1r14r8_independent_forensics as r8_independent,
    stage4_2r3c3t13s24d1r14r8r3_independent_forensics as ind3,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification as r8,
    stage4_2r3c3t13s24d1r14r8r4_fresh_causal_observer_identification as contract,
)


RUN_NAME = contract.RUN_NAME


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
    rows = []
    total = 0
    for path in sorted(directory.glob("*.json.gz"), key=lambda value: value.name):
        size = path.stat().st_size
        sha = _sha(path)
        total += size
        digest.update(f"{path.name}\0{size}\0{sha}\n".encode())
        rows.append({"name": path.name, "size": size, "sha256": sha})
    return {"count": len(rows), "bytes": total, "digest": digest.hexdigest(), "rows": rows}


def _stage(run_dir: Path) -> Path:
    return run_dir.expanduser().resolve() / RUN_NAME


def _specs(stage: Path, phase: str) -> list[dict[str, Any]]:
    manifest = _read(stage / "stage_manifest.json")
    values = _read(stage / "specs" / "all_specs.json")
    if len(values) != 16 or r8._digest(values) != manifest.get("spec_digest"):
        raise ValueError("R8R4 independent spec digest changed")
    output = [row for row in values if row.get("partition") == phase]
    if len(output) != 8:
        raise ValueError("R8R4 independent phase spec coverage changed")
    return output


def _source_baselines(r8_run: Path) -> dict[str, dict[str, Any]]:
    stage = r8._paths(r8_run)
    index = _read(stage.source_reference / "s21_baseline_index.json")
    output = {}
    for row in index:
        path = Path(str(row["path"])).expanduser().resolve()
        if _sha(path) != str(row["sha256"]):
            raise ValueError("R8R4 independent source baseline changed")
        value = _gzip(path)
        if value.get("experiment_id") != row.get("experiment_id"):
            raise ValueError("R8R4 independent source baseline identity changed")
        output[str(row["experiment_id"])] = value
    if len(output) != 40:
        raise ValueError("R8R4 independent source baseline count changed")
    return output


def raw_audit(args: argparse.Namespace, cfg: Mapping[str, Any], phase: str) -> dict[str, Any]:
    stage = _stage(args.run_dir)
    specs = _specs(stage, phase)
    sources = _source_baselines(args.r8_run.resolve())
    raw_dir = stage / "raw" / phase
    rows = []
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
        full = len(trajectory) == horizon + 1 and len(trace) == horizon
        source = sources[str(spec["source_s21_baseline_experiment_id"])]
        prefix_state = bool(
            len(trajectory) >= 11
            and all(
                r8.r4._semantic_state(left) == r8.r4._semantic_state(right)
                for left, right in zip(trajectory[:11], source["trajectory"][:11])
            )
        )
        prefix_trace = bool(
            len(trace) >= 10
            and all(
                r8.r4._source_trace_projection(right, left)
                for left, right in zip(trace[:10], source["controller_trace"][:10])
            )
        )
        calibration = r8.r4._calibration_exact(trace)
        actions = np.asarray([row.get("action_norm_tsc", []) for row in trace], dtype=float)
        currents = np.asarray(
            [row.get("currents_a_tsc", []) for row in trajectory], dtype=float
        )
        wires = [np.asarray(row.get("wire_currents_a", []), dtype=float) for row in trajectory]
        finite = bool(
            full
            and actions.shape == (horizon, 14)
            and currents.shape == (horizon + 1, 14)
            and np.all(np.isfinite(actions))
            and np.all(np.isfinite(currents))
            and all(value.size and np.all(np.isfinite(value)) for value in wires)
            and all(
                math.isfinite(float(row[key]))
                for row in trajectory
                for key in ("R", "Z", "Ip")
            )
            and not any(bool(row.get("abnormal")) for row in trajectory)
        )
        zero = bool(full and np.array_equal(actions[10:], np.zeros_like(actions[10:])))
        difference = np.diff(currents[10:], axis=0) if full else np.asarray([math.inf])
        constant = bool(full and np.array_equal(difference, np.zeros_like(difference)))
        forbidden_keys = tuple(
            dict.fromkeys(
                r8.R8_FORBIDDEN_TRACE_KEYS
                + (
                    "r3c3t13s24d1r14r8r4_future_r17_executed",
                    "r3c3t13s24d1r14r8r4_pair_or_history_label_used",
                    "r3c3t13s24d1r14r8r4_partition_label_used",
                    "r3c3t13s24d1r14r8r4_source_result_used",
                )
            )
        )
        forbidden = sum(
            any(bool(row.get(key)) for key in forbidden_keys) for row in trace
        )
        payload = _read(stage / "variants" / f"payload_{experiment}.json")
        minimum, maximum = r8.d1r11.s21.s13._current_limits_tsc(payload)
        center, half = 0.5 * (minimum + maximum), 0.5 * (maximum - minimum)
        utilization = (
            float(np.max(np.abs((currents - center) / half)))
            if currents.shape == (horizon + 1, 14)
            else math.inf
        )
        action_abs = (
            float(np.max(np.abs(actions))) if actions.shape == (horizon, 14) else math.inf
        )
        snapshot = bool(
            str(spec.get("restart_snapshot_dir") or "")
            and str(spec.get("restart_snapshot_manifest_digest") or "")
            and payload.get("stage4_2r3c3t13s24d1r14r8_snapshot_manifest_digest")
            == spec.get("restart_snapshot_manifest_digest")
        )
        identity = bool(
            result.get("completed")
            and result.get("stage") == contract.STAGE
            and result.get("campaign_identity") == contract.IDENTITY
            and result.get("controller_revision") == contract.CONTROLLER_REVISION
            and result.get("experiment_id") == experiment
            and result.get("spec") == spec
        )
        passed = bool(
            result.get("success")
            and identity
            and full
            and prefix_state
            and prefix_trace
            and calibration
            and finite
            and zero
            and constant
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
                "execution_failure_class": str(result.get("execution_failure_class") or ""),
                "full_horizon": full,
                "source_prefix_state_exact": prefix_state,
                "source_prefix_trace_exact": prefix_trace,
                "calibration_exact": calibration,
                "zero_future_action_exact": zero,
                "constant_future_commanded_current_exact": constant,
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
    primary_path = stage / "analysis" / f"{phase}_raw_primary.json"
    primary = _read(primary_path)
    numerical = ind3._agrees(primary.get("rows"), rows, cfg)
    result = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "audit_kind": f"{phase}_raw_independent",
        "raw_inventory": inventory,
        "passed_count": sum(bool(row.get("passed")) for row in rows),
        "primary_sha256": _sha(primary_path),
        "primary_numerical_agreement": numerical,
        "passed": bool(
            inventory["count"] == 8
            and len(rows) == 8
            and all(bool(row.get("passed")) for row in rows)
            and inventory == primary.get("raw_inventory")
            and numerical
        ),
    }
    if not result["passed"]:
        raise ValueError(f"R8R4 independent {phase} raw audit disagrees")
    _write(stage / "analysis" / f"{phase}_raw_independent.json", result)
    return result


def _prior_rows(args: argparse.Namespace, cfg: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    root = Path(__file__).resolve().parents[3]
    r8r3_cfg = _read((root / str(cfg["source_r8r3_config"])).resolve())
    r8r2_config = (root / str(r8r3_cfg["source_r8r2_config"])).resolve()
    r8r2_cfg = _read(r8r2_config)
    r8_config = (root / str(cfg["source_r8_config"])).resolve()
    r8_cfg = _read(r8_config)
    paths = r8_independent._paths(args.r8_run.resolve())
    rows, signature = ind3._source_rows(r8r3_cfg, r8r2_cfg, r8_cfg, paths, args)
    if len({str(row["pair_id"]) for row in rows}) != 12:
        raise ValueError("R8R4 independent prior pair coverage changed")
    return rows, signature


def _fresh_rows(
    args: argparse.Namespace, cfg: Mapping[str, Any], phase: str
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    stage = _stage(args.run_dir)
    specs = _specs(stage, phase)
    scales = np.asarray(cfg["bank_contract"]["visible_scales"], dtype=float)
    issues = set(map(int, cfg["bank_contract"]["prescribed_issue_task_steps"]))
    rows = []
    hashes = {}
    for spec in specs:
        path = stage / "raw" / phase / f"{spec['experiment_id']}.json.gz"
        result = _gzip(path)
        visible = ind3.frozen._visible(result["trajectory"], scales)
        action = ind3._actions(result)
        current = ind3._currents(result)
        maximum = len(visible) - 13
        for origin in range(10, maximum + 1):
            feature = ind3._feature(
                visible[: origin + 1],
                action[:origin],
                current[: origin + 1],
                ind3._target(spec),
                origin,
                cfg,
            )
            future = visible[origin + 1 : origin + 13]
            rows.append(
                {
                    "row_id": (
                        f"{phase}|{spec['pair_id']}|{spec['history_member']}|"
                        f"origin{origin:02d}"
                    ),
                    "context_id": f"{spec['pair_id']}|{spec['history_member']}",
                    "pair_id": str(spec["pair_id"]),
                    "history_member": str(spec["history_member"]),
                    "origin_task_step": origin,
                    "prescribed_issue": origin in issues,
                    "source_baseline_experiment_id": str(spec["experiment_id"]),
                    "feature": feature,
                    "origin_visible": visible[origin],
                    "target_delta": future[:, 2:5] - visible[origin, 2:5],
                    "future_visible": future,
                }
            )
        hashes[str(spec["experiment_id"])] = _sha(path)
    signature = {
        "phase": phase,
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
    if (
        signature["pair_count"] != 4
        or signature["context_count"] != 8
        or signature["prescribed_issue_row_count"] != 32
    ):
        raise ValueError(f"R8R4 independent {phase} causal coverage changed")
    return sorted(rows, key=lambda row: row["row_id"]), signature


def _metric(
    item: Mapping[str, Any], prediction: np.ndarray, cfg: Mapping[str, Any]
) -> dict[str, Any]:
    target = np.asarray(item["future_visible"], dtype=float)
    scales = np.asarray(cfg["bank_contract"]["visible_scales"], dtype=float)
    caps = np.asarray(cfg["gates"]["component_caps_physical"], dtype=float)
    exclusion_caps = np.asarray(
        cfg["gates"]["finite_exclusion_caps_physical"], dtype=float
    )
    residual = prediction - target
    absolute = np.abs(residual * scales)
    violation = absolute > caps[None, :] + 1e-15
    exclusion = absolute > exclusion_caps[None, :] + 1e-15
    return {
        "row_id": str(item["row_id"]),
        "pair_id": str(item["pair_id"]),
        "history_member": str(item["history_member"]),
        "origin_task_step": int(item["origin_task_step"]),
        "prescribed_issue": bool(item["prescribed_issue"]),
        "predicted_visible": prediction.tolist(),
        "target_visible": target.tolist(),
        "absolute_residual_physical": absolute.tolist(),
        "component_future_violation_count": int(np.sum(violation)),
        "component_violation_counts": np.sum(violation, axis=0).astype(int).tolist(),
        "maximum_absolute_scaled_point_error": float(np.max(np.abs(residual))),
        "mean_squared_scaled_error": float(np.mean(residual * residual)),
        "passed": bool(not np.any(violation) and np.all(np.isfinite(prediction))),
        "finite_exclusion_violation_count": int(np.sum(exclusion)),
        "finite_exclusion_component_counts": np.sum(exclusion, axis=0).astype(int).tolist(),
        "finite_exclusion_passed": bool(
            not np.any(exclusion) and np.all(np.isfinite(prediction))
        ),
    }


def _score(
    rows: Sequence[Mapping[str, Any]], candidate: tuple[str, int, float, float]
) -> tuple[Any, ...]:
    maxima = np.asarray([row["maximum_absolute_scaled_point_error"] for row in rows])
    return (
        sum(not bool(row["passed"]) for row in rows),
        sum(int(row["component_future_violation_count"]) for row in rows),
        sum(not bool(row["finite_exclusion_passed"]) for row in rows),
        float(np.max(maxima)),
        float(np.quantile(maxima, 0.95, method="linear")),
        float(np.mean([row["mean_squared_scaled_error"] for row in rows])),
        0 if candidate[0] == "linear" else 1,
        candidate[1],
        candidate[2],
        candidate[3],
    )


def _select(
    items: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> tuple[tuple[str, int, float, float], list[dict[str, Any]], list[dict[str, Any]]]:
    stored = {ind3._key(candidate): [] for candidate in ind3._candidates(cfg)}
    for pair in sorted({str(row["pair_id"]) for row in items}):
        training = [row for row in items if str(row["pair_id"]) != pair]
        held = [row for row in items if str(row["pair_id"]) == pair]
        predicted = ind3._all_predictions(training, held, cfg)
        for candidate in ind3._candidates(cfg):
            stored[ind3._key(candidate)].extend(
                _metric(item, value, cfg)
                for item, value in zip(held, predicted[ind3._key(candidate)])
            )
    scored = []
    for candidate in ind3._candidates(cfg):
        rows = sorted(stored[ind3._key(candidate)], key=lambda row: row["row_id"])
        scored.append((candidate, _score(rows, candidate), rows))
    selected, _, rows = min(scored, key=lambda value: value[1])
    report = [
        {
            "candidate": ind3._candidate_dict(candidate),
            "selection_score": list(score[:-4]),
        }
        for candidate, score, _ in scored
    ]
    return selected, report, rows


def _tube(rows: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> np.ndarray:
    residual = np.asarray([row["absolute_residual_physical"] for row in rows])
    floor = np.asarray(cfg["tube_contract"]["component_floor_physical"], dtype=float)
    base = np.quantile(
        residual,
        float(cfg["tube_contract"]["base_absolute_residual_quantile"]),
        axis=0,
        method="higher",
    ) + floor[None, :]
    ratio = np.max(residual / base[None, :, :], axis=(1, 2))
    scalar = max(
        1.0,
        float(
            np.quantile(
                ratio,
                float(cfg["tube_contract"]["row_ratio_quantile"]),
                method="higher",
            )
        ),
    )
    return scalar * base


def _outer(
    items: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows, folds = [], []
    caps = np.asarray(cfg["tube_contract"]["component_caps_physical"], dtype=float)
    pairs = sorted({str(row["pair_id"]) for row in items})
    for pair in pairs:
        training = [row for row in items if str(row["pair_id"]) != pair]
        held = [row for row in items if str(row["pair_id"]) == pair]
        selected, scores, inner_rows = _select(training, cfg)
        tube = _tube(inner_rows, cfg)
        model = ind3._fit(training, selected, cfg)
        held_rows = [
            _metric(item, value, cfg)
            for item, value in zip(held, ind3._predict(model, held, cfg))
        ]
        contained = 0
        for row in held_rows:
            residual = np.asarray(row["absolute_residual_physical"], dtype=float)
            row["tube_contained"] = bool(np.all(residual <= tube + 1e-15))
            contained += int(row["tube_contained"])
        cap_passed = bool(np.all(tube <= caps[None, :] + 1e-15))
        rows.extend(held_rows)
        folds.append(
            {
                "held_pair_id": pair,
                "training_pair_count": len(pairs) - 1,
                "training_origin_row_count": len(training),
                "held_origin_row_count": len(held),
                "selected_candidate": ind3._candidate_dict(selected),
                "inner_candidate_scores": scores,
                "tube_physical": tube.tolist(),
                "tube_cap_passed": cap_passed,
                "held_tube_contained_count": contained,
                "passed": bool(
                    cap_passed
                    and contained == len(held_rows)
                    and all(bool(row["passed"]) for row in held_rows)
                ),
            }
        )
    return sorted(rows, key=lambda row: row["row_id"]), folds


def _required(rate: float, total: int) -> int:
    return int(math.ceil(rate * total - 1e-15))


def _point(rows: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> dict[str, Any]:
    gates = cfg["gates"]
    issues = [row for row in rows if bool(row["prescribed_issue"])]
    contexts = {}
    context_passed = True
    for pair, history in sorted(
        {(str(row["pair_id"]), str(row["history_member"])) for row in rows}
    ):
        current = [
            row
            for row in rows
            if str(row["pair_id"]) == pair and str(row["history_member"]) == history
        ]
        current_issues = [row for row in current if bool(row["prescribed_issue"])]
        count = sum(bool(row["passed"]) for row in current)
        issue_count = sum(bool(row["passed"]) for row in current_issues)
        need = _required(float(gates["per_context_point_pass_rate"]), len(current))
        passed = bool(
            count >= need
            and issue_count >= int(gates["per_context_prescribed_issue_pass_count"])
        )
        context_passed = context_passed and passed
        contexts[f"{pair}|{history}"] = {
            "point_pass_count": count,
            "total": len(current),
            "required": need,
            "issue_point_pass_count": issue_count,
            "issue_total": len(current_issues),
            "issue_required": int(gates["per_context_prescribed_issue_pass_count"]),
            "passed": passed,
        }
    point_count = sum(bool(row["passed"]) for row in rows)
    issue_count = sum(bool(row["passed"]) for row in issues)
    point_need = _required(float(gates["aggregate_point_pass_rate"]), len(rows))
    issue_need = _required(float(gates["prescribed_issue_point_pass_rate"]), len(issues))
    exclusion = sum(int(row["finite_exclusion_violation_count"]) for row in rows)
    result = {
        "origin_row_count": len(rows),
        "origin_point_pass_count": point_count,
        "origin_point_required": point_need,
        "prescribed_issue_row_count": len(issues),
        "prescribed_issue_point_pass_count": issue_count,
        "prescribed_issue_point_required": issue_need,
        "finite_exclusion_violation_count": exclusion,
        "maximum_absolute_physical_error": np.max(
            np.asarray([row["absolute_residual_physical"] for row in rows]), axis=(0, 1)
        ).tolist(),
        "maximum_absolute_scaled_point_error": max(
            float(row["maximum_absolute_scaled_point_error"]) for row in rows
        ),
        "context_counts": contexts,
    }
    result["passed"] = bool(
        point_count >= point_need
        and issue_count >= issue_need
        and exclusion == 0
        and context_passed
    )
    return result


def _practical(
    rows: Sequence[Mapping[str, Any]], tube: np.ndarray, cfg: Mapping[str, Any]
) -> dict[str, Any]:
    values = []
    for source in rows:
        row = dict(source)
        residual = np.asarray(row["absolute_residual_physical"], dtype=float)
        row["tube_contained"] = bool(np.all(residual <= tube + 1e-15))
        values.append(row)
    point = _point(values, cfg)
    gates = cfg["gates"]
    contexts = {}
    context_passed = True
    for pair, history in sorted(
        {(str(row["pair_id"]), str(row["history_member"])) for row in values}
    ):
        current = [
            row
            for row in values
            if str(row["pair_id"]) == pair and str(row["history_member"]) == history
        ]
        point_context = point["context_counts"][f"{pair}|{history}"]
        tube_count = sum(bool(row["tube_contained"]) for row in current)
        tube_need = _required(
            float(gates["per_context_tube_containment_rate"]), len(current)
        )
        passed = bool(point_context["passed"] and tube_count >= tube_need)
        context_passed = context_passed and passed
        contexts[f"{pair}|{history}"] = {
            "origin_point_pass_count": point_context["point_pass_count"],
            "origin_total": point_context["total"],
            "origin_point_required": point_context["required"],
            "prescribed_issue_point_pass_count": point_context[
                "issue_point_pass_count"
            ],
            "prescribed_issue_total": point_context["issue_total"],
            "prescribed_issue_required": point_context["issue_required"],
            "tube_contained_count": tube_count,
            "tube_required": tube_need,
            "passed": passed,
        }
    tube_count = sum(bool(row["tube_contained"]) for row in values)
    tube_need = _required(float(gates["aggregate_tube_containment_rate"]), len(values))
    caps = np.asarray(cfg["tube_contract"]["component_caps_physical"], dtype=float)
    result = {
        "origin_row_count": point["origin_row_count"],
        "origin_point_pass_count": point["origin_point_pass_count"],
        "origin_point_required": point["origin_point_required"],
        "prescribed_issue_row_count": point["prescribed_issue_row_count"],
        "prescribed_issue_point_pass_count": point["prescribed_issue_point_pass_count"],
        "prescribed_issue_point_required": point["prescribed_issue_point_required"],
        "tube_contained_origin_count": tube_count,
        "tube_contained_origin_required": tube_need,
        "finite_exclusion_violation_count": point["finite_exclusion_violation_count"],
        "tube_cap_passed": bool(np.all(tube <= caps[None, :] + 1e-15)),
        "maximum_tube_physical": np.max(tube, axis=0).tolist(),
        "maximum_absolute_physical_error": point["maximum_absolute_physical_error"],
        "maximum_absolute_scaled_point_error": point[
            "maximum_absolute_scaled_point_error"
        ],
        "context_counts": contexts,
        "rows": values,
    }
    result["passed"] = bool(
        point["passed"]
        and tube_count >= tube_need
        and result["tube_cap_passed"]
        and context_passed
    )
    return result


def _serializable(model: Mapping[str, Any], tube: np.ndarray) -> dict[str, Any]:
    candidate = model["candidate"]
    output = {
        "candidate": ind3._candidate_dict(candidate),
        "preprocessor": {
            key: np.asarray(value).tolist() for key, value in model["pre"].items()
        },
        "training_x": np.asarray(model["x"]).tolist(),
        "target_mean": np.asarray(model["mean"]).tolist(),
        "bandwidth": float(model.get("bandwidth", 0.0)),
        "tube_physical": tube.tolist(),
    }
    output["beta" if candidate[0] == "linear" else "alpha"] = np.asarray(
        model["weights"]
    ).tolist()
    return output


def development_model_audit(
    args: argparse.Namespace, cfg: Mapping[str, Any]
) -> dict[str, Any]:
    stage = _stage(args.run_dir)
    primary_path = stage / "analysis" / "development_model_primary_detailed.json"
    summary_path = stage / "analysis" / "development_model_primary_summary.json"
    primary = _read(primary_path)
    summary = _read(summary_path)
    prior, prior_signature = _prior_rows(args, cfg)
    fresh, fresh_signature = _fresh_rows(args, cfg, "development")
    items = sorted(prior + fresh, key=lambda row: row["row_id"])
    outer_rows, folds = _outer(items, cfg)
    outer_point = _point(outer_rows, cfg)
    selected, scores, selected_rows = _select(items, cfg)
    tube = _tube(selected_rows, cfg)
    tube_evaluation = _practical(selected_rows, tube, cfg)
    scientific = bool(
        len(folds) == int(cfg["gates"]["required_development_outer_fold_count"])
        and outer_point["passed"]
        and tube_evaluation["passed"]
    )
    route = str(cfg["routes"]["pass" if scientific else "development_model_fail"])
    model_sha = tube_sha = ""
    if scientific:
        fitted = ind3._fit(items, selected, cfg)
        artifact = {
            "schema_version": 1,
            "stage": contract.STAGE,
            "campaign_identity": contract.IDENTITY,
            "feature_contract": cfg["feature_contract"],
            "bank_contract": cfg["bank_contract"],
            "training_pair_count": 16,
            "selected_candidate": ind3._candidate_dict(selected),
            "source_r8_authentication_sha256": _sha(
                stage / "source_reference" / "r8_authentication.json"
            ),
            "source_r8r3_authentication_sha256": _sha(
                stage / "source_reference" / "r8r3_authentication.json"
            ),
            "model": _serializable(fitted, tube),
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
                "derivation": "higher_quantile_scaled_whole_pair_oof",
                "selected_candidate": ind3._candidate_dict(selected),
            },
        )
        model_sha, tube_sha = _sha(expected_model), _sha(expected_tube)
    numerical = bool(
        ind3._agrees(primary.get("prior_signature"), prior_signature, cfg)
        and ind3._agrees(primary.get("fresh_signature"), fresh_signature, cfg)
        and ind3._agrees(primary.get("outer_point_evaluation"), outer_point, cfg)
        and ind3._agrees(primary.get("outer_rows"), outer_rows, cfg)
        and ind3._agrees(primary.get("outer_folds"), folds, cfg)
        and ind3._agrees(
            primary.get("all_development_selected_candidate"),
            ind3._candidate_dict(selected),
            cfg,
        )
        and ind3._agrees(primary.get("all_development_candidate_scores"), scores, cfg)
        and ind3._agrees(
            primary.get("all_development_oof_tube_evaluation"), tube_evaluation, cfg
        )
        and ind3._agrees(primary.get("tube_physical"), tube.tolist(), cfg)
    )
    outcome = bool(
        primary.get("route") == route
        and summary.get("route") == route
        and bool(primary.get("scientific_gate_passed")) is scientific
        and bool(summary.get("scientific_gate_passed")) is scientific
    )
    artifact = bool(
        primary.get("observer_model_sha256") == model_sha
        and primary.get("observer_tube_sha256") == tube_sha
        and (
            (not scientific)
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
        "prior_signature": prior_signature,
        "fresh_signature": fresh_signature,
        "outer_point_evaluation": outer_point,
        "selected_candidate": ind3._candidate_dict(selected),
        "tube_evaluation": {key: value for key, value in tube_evaluation.items() if key != "rows"},
        "route": route,
        "scientific_gate_passed": scientific,
        "observer_model_sha256": model_sha,
        "observer_tube_sha256": tube_sha,
        "primary_summary_sha256": _sha(summary_path),
        "primary_numerical_agreement": numerical,
        "primary_outcome_agreement": outcome,
        "artifact_hash_agreement": artifact,
        "holdout_raw_count": _inventory(stage / "raw" / "holdout")["count"],
        "passed": bool(numerical and outcome and artifact),
    }
    if not result["passed"] or result["holdout_raw_count"] != 0:
        raise ValueError("R8R4 independent development model audit disagrees")
    _write(stage / "analysis" / "development_model_independent.json", result)
    return result


def _artifact_model(value: Mapping[str, Any]) -> dict[str, Any]:
    model = value["model"]
    candidate = (
        str(model["candidate"]["family"]),
        int(model["candidate"]["pca_rank"]),
        float(model["candidate"]["bandwidth_multiplier"]),
        float(model["candidate"]["ridge"]),
    )
    output = {
        "candidate": candidate,
        "pre": {
            key: np.asarray(item, dtype=float)
            for key, item in model["preprocessor"].items()
        },
        "x": np.asarray(model["training_x"], dtype=float),
        "mean": np.asarray(model["target_mean"], dtype=float),
        "weights": np.asarray(
            model["beta" if candidate[0] == "linear" else "alpha"], dtype=float
        ),
    }
    if candidate[0] == "rbf":
        output["bandwidth"] = float(model["bandwidth"])
    return output


def holdout_model_audit(args: argparse.Namespace, cfg: Mapping[str, Any]) -> dict[str, Any]:
    stage = _stage(args.run_dir)
    primary_path = stage / "analysis" / "holdout_model_primary_detailed.json"
    summary_path = stage / "analysis" / "holdout_model_primary_summary.json"
    primary, summary = _read(primary_path), _read(summary_path)
    model_path = stage / "model" / "observer_model.json"
    tube_path = stage / "model" / "observer_tube.json"
    artifact, tube_value = _read(model_path), _read(tube_path)
    items, signature = _fresh_rows(args, cfg, "holdout")
    model = _artifact_model(artifact)
    rows = [
        _metric(item, value, cfg)
        for item, value in zip(items, ind3._predict(model, items, cfg))
    ]
    tube = np.asarray(tube_value["tube_physical"], dtype=float)
    evaluation = _practical(rows, tube, cfg)
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
        raise ValueError("R8R4 independent holdout model audit disagrees")
    _write(stage / "analysis" / "holdout_model_independent.json", result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--r8-run", type=Path, required=True)
    parser.add_argument("--r8r2-output", type=Path, required=True)
    parser.add_argument("--source-r2-run", type=Path, required=True)
    parser.add_argument("--source-r4-run", type=Path, required=True)
    parser.add_argument("--source-r6-run", type=Path, required=True)
    parser.add_argument(
        "--audit-kind",
        choices=(
            "development_raw",
            "development_model",
            "holdout_raw",
            "holdout_model",
        ),
        required=True,
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    cfg = _read(args.config.resolve())
    contract.validate_config(cfg, project_root=Path(__file__).resolve().parents[3])
    if args.audit_kind == "development_raw":
        result = raw_audit(args, cfg, "development")
    elif args.audit_kind == "development_model":
        result = development_model_audit(args, cfg)
    elif args.audit_kind == "holdout_raw":
        result = raw_audit(args, cfg, "holdout")
    else:
        result = holdout_model_audit(args, cfg)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
