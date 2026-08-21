#!/usr/bin/env python3
"""Causal exact-observation-recentered development model for fixed 1000 ms."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_1000_baseline_b0 as b0  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import decimal_single_turn_currents_a  # noqa: E402
from tsc_rzip_rllib.core.runner import TSCConfig  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-1000-causal-m0-v1"
CONFIG_SHA256 = "47a5dbbe8f9b25068a3194751de3e707b72eb5414e6caf46f5246c892c46ae7a"
DEFAULT_CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_causal_m0.json"


class InputIntegrityError(ValueError):
    """Frozen M0 data, roles or design changed."""


def _manifest_digest(paths: Sequence[Path]) -> str:
    rows = [[path.relative_to(ROOT).as_posix(), b0.sha256(path)] for path in sorted(paths, key=lambda p: p.as_posix())]
    encoded = json.dumps(rows, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load(config_path: Path) -> tuple[dict[str, Any], TSCConfig, list[tuple[str, Path, dict[str, Any]]]]:
    config_path = b0.inside_root(config_path, "M0 config")
    if b0.sha256(config_path) != CONFIG_SHA256:
        raise InputIntegrityError("M0 config SHA-256 mismatch")
    stage = json.loads(config_path.read_text(encoding="utf-8"))
    exact = {
        "schema_version": SCHEMA,
        "model_id": "rgeo_zgeo_1ms_1000_causal_m0_v1",
        "takeover_time_ms": 1000,
        "control_period_ms": 1,
        "history_steps": 8,
        "fixed_memory_poles": [0.25, 0.5, 0.75, 0.9],
        "ridge_alpha": 1.0,
        "output_scales": [0.1, 0.1, 25.0],
        "dataset_manifest_digest": "c7f53d08b6ce3df3ee63bb6ec3a7aaf908b758ca03dca483610c9a927e97c4f8",
        "dataset_file_count": 25,
        "executed_action_rank": 6,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise InputIntegrityError(f"frozen field mismatch: {key}")
    roles = stage.get("data_roles", {})
    if roles != {
        "listed_primary_rows": "development_fit_eligible_weight_1",
        "critical_replays": "excluded_zero_fit_weight",
        "calibration": "unopened",
        "holdout": "unopened",
        "controller_or_recourse": "forbidden",
        "fixed_1100_data": "forbidden",
    }:
        raise InputIntegrityError("M0 data roles changed")
    base = b0.inside_root(ROOT / stage["base_tsc_config"], "M0 base config")
    if b0.sha256(base) != stage["base_tsc_config_sha256"]:
        raise InputIntegrityError("M0 base config hash mismatch")
    cfg = TSCConfig.from_json(base)
    baseline_path = b0.inside_root(ROOT / stage["baseline_path"], "M0 baseline")
    files = [baseline_path]
    rows: list[tuple[str, Path, dict[str, Any]]] = []
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if baseline.get("repeat_index") not in (None, 0) or not baseline.get("passed") or baseline.get(
        "data_role"
    ) != "development_fit_eligible_baseline_weight_1":
        raise InputIntegrityError("M0 baseline role is not primary development")
    rows.append(("b0", baseline_path, baseline))
    excluded = tuple(stage["exclude_filename_substrings"])
    for group in stage["development_groups"]:
        directory = b0.inside_root(ROOT / group["directory"], f"M0 {group['name']} directory")
        selected = [path for path in directory.glob(group["glob"])
                    if not any(token in path.name for token in excluded)]
        for path in sorted(selected):
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("repeat_index") != 0 or payload.get("passed") is not True:
                raise InputIntegrityError(f"M0 non-primary or failed row: {path.name}")
            if payload.get("data_role") != "development_fit_eligible_weight_1":
                raise InputIntegrityError(f"M0 row role mismatch: {path.name}")
            rows.append((group["name"], path, payload))
            files.append(path)
    if len(files) != stage["dataset_file_count"] or _manifest_digest(files) != stage["dataset_manifest_digest"]:
        raise InputIntegrityError("M0 dataset manifest mismatch")
    if any("1100" in path.as_posix() for path in files):
        raise InputIntegrityError("fixed-1100 data entered M0")
    return stage, cfg, rows


def _target_current(action: dict[str, Any], cfg: TSCConfig) -> np.ndarray:
    values = decimal_single_turn_currents_a(
        tuple(str(value).strip() for value in action["expected_card15_fields"]),
        cfg.turns_tsc, name="m0.target",
    )
    return np.asarray([float(value) for value in values], dtype=float)


def _action_basis(
    rows: Sequence[tuple[str, Path, dict[str, Any]]], cfg: TSCConfig, expected_rank: int,
) -> tuple[np.ndarray, np.ndarray]:
    baseline = rows[0][2]
    q0 = np.asarray([float(value) for value in baseline["states"][0]["active_command_decimal_a_tsc"]])
    deltas = []
    for _, _, payload in rows:
        deltas.extend(_target_current(action, cfg) - q0 for action in payload["actions"])
    matrix = np.asarray(deltas, dtype=float)
    _, singular, vt = np.linalg.svd(matrix, full_matrices=False)
    rank = int(np.sum(singular > 1e-9))
    if rank != expected_rank:
        raise InputIntegrityError(f"M0 executed action rank changed: {rank}")
    return vt[:rank].T, singular[:rank]


def _velocity(states: Sequence[dict[str, Any]], issue: int, width: int) -> np.ndarray:
    start = max(0, issue - width)
    steps = issue - start
    if steps == 0:
        return np.zeros(3)
    a, z = states[start], states[issue]
    return np.asarray([
        1000.0 * (z["r_geo_m"] - a["r_geo_m"]) / steps,
        1000.0 * (z["z_geo_m"] - a["z_geo_m"]) / steps,
        (z["ip_a"] - a["ip_a"]) / (25.0 * steps),
    ])


def feature_rows(
    rows: Sequence[tuple[str, Path, dict[str, Any]]], cfg: TSCConfig,
    poles: Sequence[float], expected_rank: int,
) -> tuple[list[dict[str, Any]], np.ndarray, np.ndarray, list[str], int]:
    basis, singular = _action_basis(rows, cfg, expected_rank)
    action_rank = basis.shape[1]
    baseline = rows[0][2]
    source_state = baseline["states"][0]
    source_rzi = np.asarray([source_state["r_geo_m"], source_state["z_geo_m"], source_state["ip_a"]])
    source_actual = np.asarray(source_state["actual_current_a_tsc"], dtype=float)
    q0 = np.asarray([float(value) for value in source_state["active_command_decimal_a_tsc"]])
    samples: list[dict[str, Any]] = []
    names = [
        "time", "time2", "r_mm", "z_mm", "ip_100a",
        "v1_r_mm", "v1_z_mm", "v1_ip_25a", "v4_r_mm", "v4_z_mm", "v4_ip_25a",
    ] + [f"actual_c{axis}" for axis in range(action_rank)] + [
        f"target_c{axis}" for axis in range(action_rank)
    ] + [f"dtarget_c{axis}" for axis in range(action_rank)] + [
        f"memory_p{pole}_{axis}" for pole in poles for axis in range(action_rank)
    ] + [
        "active_age", "change_age", "target_norm2",
    ]
    for group, path, payload in rows:
        states, actions = payload["states"], payload["actions"]
        if len(states) != len(actions) + 1:
            raise InputIntegrityError(f"M0 state/action cardinality mismatch: {path.name}")
        targets = [(_target_current(action, cfg) - q0) @ basis for action in actions]
        memories = [np.zeros(action_rank) for _ in poles]
        active_age = change_age = 0
        previous = np.zeros(action_rank)
        family = f"{group}:{payload.get('rollout_id', path.stem)}"
        for issue, (state, nxt, target) in enumerate(zip(states[:-1], states[1:], targets)):
            changed = not np.allclose(target, previous, atol=1e-12, rtol=0.0)
            active_age = active_age + 1 if np.linalg.norm(target) > 1e-12 else 0
            change_age = 0 if changed else change_age + 1
            for index, pole in enumerate(poles):
                memories[index] = pole * memories[index] + (1.0 - pole) * target
            rzi = np.asarray([state["r_geo_m"], state["z_geo_m"], state["ip_a"]])
            rel = rzi - source_rzi
            actual = (np.asarray(state["actual_current_a_tsc"], dtype=float) - source_actual) @ basis
            dtarget = target - previous
            time = issue / 64.0
            base = np.asarray([
                time, time * time, 1000.0 * rel[0], 1000.0 * rel[1], rel[2] / 100.0,
                *_velocity(states, issue, 1), *_velocity(states, issue, 4),
            ])
            action_part = np.concatenate([
                actual, target, dtarget, *memories,
                np.asarray([active_age / 64.0, change_age / 64.0, float(target @ target)]),
            ])
            y = np.asarray([
                1000.0 * (nxt["r_geo_m"] - state["r_geo_m"]),
                1000.0 * (nxt["z_geo_m"] - state["z_geo_m"]),
                nxt["ip_a"] - state["ip_a"],
            ])
            samples.append({
                "family": family, "group": group, "issue": issue,
                "x": np.concatenate([base, action_part]), "y": y,
            })
            previous = target
    return samples, basis, singular, names, 11


def _deduplicate(samples: Sequence[dict[str, Any]], width: int) -> list[dict[str, Any]]:
    unique: dict[tuple[float, ...], dict[str, Any]] = {}
    for sample in samples:
        key = tuple(np.round(np.concatenate([sample["x"][:width], sample["y"]]), 12))
        unique.setdefault(key, sample)
    return list(unique.values())


def fit_ridge(
    train: Sequence[dict[str, Any]], width: int, alpha: float, output_scales: np.ndarray,
) -> dict[str, Any]:
    train = _deduplicate(train, width)
    x = np.asarray([sample["x"][:width] for sample in train])
    y = np.asarray([sample["y"] / output_scales for sample in train])
    mean, std = x.mean(axis=0), x.std(axis=0)
    keep = std > 1e-12
    z = (x[:, keep] - mean[keep]) / std[keep]
    design = np.column_stack([np.ones(len(z)), z])
    penalty = np.eye(design.shape[1]) * alpha
    penalty[0, 0] = 0.0
    coefficient = np.linalg.solve(design.T @ design + penalty, design.T @ y)
    return {
        "width": width, "mean": mean, "std": std, "keep": keep,
        "coefficient": coefficient, "train_unique_rows": len(train),
        "rank": int(np.linalg.matrix_rank(design)),
        "condition": float(np.linalg.cond(design)),
    }


def predict(model: dict[str, Any], samples: Sequence[dict[str, Any]], scales: np.ndarray) -> np.ndarray:
    x = np.asarray([sample["x"][:model["width"]] for sample in samples])
    z = (x[:, model["keep"]] - model["mean"][model["keep"]]) / model["std"][model["keep"]]
    return np.column_stack([np.ones(len(z)), z]) @ model["coefficient"] * scales


def _fold_metrics(
    model: dict[str, Any], test: Sequence[dict[str, Any]], baseline_by_issue: dict[int, dict[str, Any]],
    scales: np.ndarray,
) -> dict[str, Any]:
    prediction = predict(model, test, scales)
    truth = np.asarray([sample["y"] for sample in test])
    error = np.abs(prediction - truth)
    baseline_samples = [baseline_by_issue[sample["issue"]] for sample in test]
    baseline_prediction = predict(model, baseline_samples, scales)
    baseline_truth = np.asarray([sample["y"] for sample in baseline_samples])
    response_truth = truth - baseline_truth
    response_prediction = prediction - baseline_prediction
    denominator = float(np.mean(np.sum((response_truth / scales) ** 2, axis=1)))
    response_nrmse = math.sqrt(float(np.mean(np.sum(((response_prediction - response_truth) / scales) ** 2, axis=1))) / denominator) if denominator > 0 else math.inf
    cosines = []
    for family in sorted({sample["family"] for sample in test}):
        indices = [index for index, sample in enumerate(test) if sample["family"] == family]
        peak = max(indices, key=lambda index: np.linalg.norm(response_truth[index, :2]))
        a, b = response_truth[peak, :2], response_prediction[peak, :2]
        denom = float(np.linalg.norm(a) * np.linalg.norm(b))
        cosines.append(float(a @ b / denom) if denom > 0 else -1.0)
    return {
        "rows": len(test),
        "r_p95_mm": float(np.quantile(error[:, 0], 0.95)),
        "z_p95_mm": float(np.quantile(error[:, 1], 0.95)),
        "ip_p95_a": float(np.quantile(error[:, 2], 0.95)),
        "r_max_mm": float(np.max(error[:, 0])),
        "paired_response_nrmse": response_nrmse,
        "minimum_family_peak_direction_cosine": min(cosines),
        "family_peak_direction_cosines": cosines,
    }


def _selectors(stage: dict[str, Any], fold: dict[str, Any], family: str) -> bool:
    return any(family.startswith(selector) for selector in fold["selectors"])


def execute(config_path: Path, source_revision: str, output_dir: Path) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {output_dir}")
    output_dir.mkdir(parents=True)
    try:
        stage, cfg, rows = load(config_path)
        samples, basis, singular, feature_names, blind_width = feature_rows(
            rows, cfg, stage["fixed_memory_poles"], stage["executed_action_rank"]
        )
    except Exception as exc:
        result = {
            "schema_version": SCHEMA, "kind": "fixed_1000_causal_model_development",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "source_revision": source_revision, "passed": False,
            "route": "ONE_MS_NR1000M0_INPUT_INTEGRITY_FAIL_ZERO_TSC",
            "failures": [f"{type(exc).__name__}:{exc}"], "plant_advances": 0,
        }
        b0.write_new(output_dir / "result.json", result)
        return result
    scales = np.asarray(stage["output_scales"], dtype=float)
    baseline_samples = [sample for sample in samples if sample["group"] == "b0"]
    baseline_by_issue = {sample["issue"]: sample for sample in baseline_samples}
    folds = []
    for fold in stage["whole_family_folds"]:
        test = [sample for sample in samples if _selectors(stage, fold, sample["family"])]
        train = [sample for sample in samples if not _selectors(stage, fold, sample["family"])]
        if not test or any(sample["group"] == "b0" for sample in test):
            raise InputIntegrityError(f"invalid M0 fold: {fold['name']}")
        aware = fit_ridge(train, len(feature_names), stage["ridge_alpha"], scales)
        blind = fit_ridge(train, blind_width, stage["ridge_alpha"], scales)
        aware_metrics = _fold_metrics(aware, test, baseline_by_issue, scales)
        blind_metrics = _fold_metrics(blind, test, baseline_by_issue, scales)
        folds.append({
            "fold": fold["name"], "held_families": sorted({sample["family"] for sample in test}),
            "aware": aware_metrics, "blind": blind_metrics,
            "aware_train_unique_rows": aware["train_unique_rows"],
            "aware_feature_rank": aware["rank"], "aware_feature_condition": aware["condition"],
        })
    gates = stage["gates"]
    aware_nrmse = float(np.mean([fold["aware"]["paired_response_nrmse"] for fold in folds]))
    blind_nrmse = float(np.mean([fold["blind"]["paired_response_nrmse"] for fold in folds]))
    improvement = 1.0 - aware_nrmse / blind_nrmse
    absolute_pass = all(
        fold["aware"]["r_p95_mm"] <= gates["maximum_each_fold_one_step_r_p95_mm"]
        and fold["aware"]["z_p95_mm"] <= gates["maximum_each_fold_one_step_z_p95_mm"]
        and fold["aware"]["ip_p95_a"] <= gates["maximum_each_fold_one_step_ip_p95_a"]
        and fold["aware"]["r_max_mm"] <= gates["maximum_each_fold_one_step_r_max_mm"]
        for fold in folds
    )
    response_pass = (
        aware_nrmse <= gates["maximum_mean_paired_response_nrmse"]
        and improvement >= gates["minimum_action_aware_improvement_over_blind_fraction"]
        and min(fold["aware"]["minimum_family_peak_direction_cosine"] for fold in folds)
        >= gates["minimum_peak_response_direction_cosine"]
    )
    passed = absolute_pass and response_pass
    result = {
        "schema_version": SCHEMA, "kind": "fixed_1000_causal_model_development",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_revision": source_revision, "passed": passed,
        "route": stage["routes"]["pass"] if passed else stage["routes"]["model_fail"],
        "plant_advances": 0, "trajectory_count": len(rows), "sample_rows": len(samples),
        "action_basis_singular_values_a": singular.tolist(),
        "action_basis_rank": stage["executed_action_rank"],
        "feature_names": feature_names, "blind_feature_count": blind_width,
        "folds": folds, "mean_paired_response_nrmse": aware_nrmse,
        "blind_mean_paired_response_nrmse": blind_nrmse,
        "action_aware_improvement_over_blind_fraction": improvement,
        "absolute_gate_pass": absolute_pass, "response_gate_pass": response_pass,
        "claim_boundary": "fixed-1000 retrospective development only; no calibration/holdout/controller",
    }
    if passed:
        final = fit_ridge(samples, len(feature_names), stage["ridge_alpha"], scales)
        artifact = {
            "schema_version": f"{SCHEMA}-artifact", "source_revision": source_revision,
            "feature_names": feature_names, "output_scales": scales.tolist(),
            "mean": final["mean"].tolist(), "std": final["std"].tolist(),
            "keep": final["keep"].tolist(), "coefficient": final["coefficient"].tolist(),
            "action_basis_tsc_order": basis.tolist(),
            "action_basis_singular_values_a": singular.tolist(),
            "qualification": "development_only_fresh_calibration_and_holdout_required",
        }
        b0.write_new(output_dir / "model_artifact.json", artifact)
        result["model_artifact_sha256"] = b0.sha256(output_dir / "model_artifact.json")
    b0.write_new(output_dir / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = execute(args.config.resolve(), args.source_revision, args.output.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
