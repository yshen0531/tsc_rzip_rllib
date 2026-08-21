#!/usr/bin/env python3
"""One bounded event-aware point-model trial for the fixed-1000 route."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
from typing import Any, Sequence

import numpy as np
import torch
from torch import nn


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_1000_baseline_b0 as b0  # noqa: E402
from scripts import rgeo_zgeo_1ms_1000_causal_m0 as m0  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-1000-causal-m1-v1"
CONFIG_SHA256 = "e50635a0e725d9a711690a8d9bff4361140cc92bf23b597decc3820717d15c7e"
DEFAULT_CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_causal_m1.json"


class InputIntegrityError(ValueError):
    """Frozen M1 evidence, data role or model contract changed."""


class EventResidualNet(nn.Module):
    def __init__(self, width: int, hidden: Sequence[int]) -> None:
        super().__init__()
        layers: list[nn.Module] = []
        previous = width
        for value in hidden:
            layers.extend([nn.Linear(previous, value), nn.Tanh()])
            previous = value
        layers.append(nn.Linear(previous, 3))
        self.network = nn.Sequential(*layers)

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return self.network(value)


def _exact_stage(stage: dict[str, Any]) -> None:
    exact = {
        "schema_version": SCHEMA,
        "model_id": "rgeo_zgeo_1ms_1000_causal_m1_v1",
        "takeover_time_ms": 1000,
        "control_period_ms": 1,
        "m0_config_path": "configs/rgeo_zgeo_1ms_1000_causal_m0.json",
        "m0_config_sha256": m0.CONFIG_SHA256,
        "m0_result_path": "artifacts/server_validation/rgeo_zgeo_1ms_1000_m0_20260822_4d12ab54_v1/result.json",
        "m0_result_sha256": "2f1e15426c5f48597c2ebb40c1db7e2b736517a5e9f4a43259191a8ba1c2b5e6",
        "m0_diagnostic_path": "artifacts/server_validation/rgeo_zgeo_1ms_1000_m0_diagnostic_96c050a9.json",
        "m0_diagnostic_sha256": "70e28cf34e0a422eda53e780c85976cf76404e811f919d022f768a98a99eeab1",
        "dataset_manifest_digest": "c7f53d08b6ce3df3ee63bb6ec3a7aaf908b758ca03dca483610c9a927e97c4f8",
        "dataset_file_count": 25,
        "executed_action_rank": 6,
        "maximum_issue_index": 63,
        "event_encoding": "absolute_issue_one_hot_0_through_63",
        "target": "paired_response_delta_relative_to_same_issue_q0",
        "hidden_widths": [64, 32],
        "activation": "tanh",
        "optimizer": "adam",
        "learning_rate": 0.002,
        "weight_decay": 0.0001,
        "epochs": 1200,
        "seeds": [11, 23, 37],
        "output_scales": [0.1, 0.1, 25.0],
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise InputIntegrityError(f"frozen M1 field mismatch: {key}")
    roles = {
        "m0_development_rows": "development_fit_eligible_weight_1",
        "critical_replays": "excluded_zero_fit_weight",
        "m0_result_and_diagnostic": "route_and_design_evidence_only",
        "calibration": "unopened",
        "holdout": "unopened",
        "controller_or_recourse": "forbidden",
        "fixed_1100_data": "forbidden",
    }
    if stage.get("data_roles") != roles:
        raise InputIntegrityError("M1 data roles changed")


def load(config_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]], np.ndarray, np.ndarray, list[str]]:
    config_path = b0.inside_root(config_path, "M1 config")
    if b0.sha256(config_path) != CONFIG_SHA256:
        raise InputIntegrityError("M1 config SHA-256 mismatch")
    stage = json.loads(config_path.read_text(encoding="utf-8"))
    _exact_stage(stage)
    m0_config = b0.inside_root(ROOT / stage["m0_config_path"], "M1 M0 config")
    if b0.sha256(m0_config) != stage["m0_config_sha256"]:
        raise InputIntegrityError("M1 M0 config hash mismatch")
    primary = b0.inside_root(ROOT / stage["m0_result_path"], "M1 M0 result")
    diagnostic = b0.inside_root(ROOT / stage["m0_diagnostic_path"], "M1 M0 diagnostic")
    if b0.sha256(primary) != stage["m0_result_sha256"] or b0.sha256(diagnostic) != stage["m0_diagnostic_sha256"]:
        raise InputIntegrityError("M1 predecessor evidence hash mismatch")
    predecessor = json.loads(primary.read_text(encoding="utf-8"))
    attribution = json.loads(diagnostic.read_text(encoding="utf-8"))
    if predecessor.get("passed") is not False or predecessor.get("route") != "ONE_MS_NR1000M0_CAUSAL_SHORT_HORIZON_MODEL_INSUFFICIENT":
        raise InputIntegrityError("M1 predecessor is not the frozen M0 failure")
    if predecessor.get("plant_advances") != 0 or predecessor.get("model_artifact_sha256") is not None:
        raise InputIntegrityError("M1 predecessor evidence boundary changed")
    if attribution.get("conclusion_boundary") != "attribution only; no model selection, qualification or controller authorization":
        raise InputIntegrityError("M1 attribution boundary changed")
    m0_stage, cfg, rows = m0.load(m0_config)
    if stage["whole_family_folds"] != m0_stage["whole_family_folds"]:
        raise InputIntegrityError("M1 folds differ from M0")
    if stage["dataset_manifest_digest"] != m0_stage["dataset_manifest_digest"] or stage["dataset_file_count"] != len(rows):
        raise InputIntegrityError("M1 dataset identity changed")
    raw, basis, singular, names, _ = m0.feature_rows(
        rows, cfg, m0_stage["fixed_memory_poles"], stage["executed_action_rank"]
    )
    samples, feature_names = event_rows(raw, names, stage["maximum_issue_index"])
    return stage, samples, basis, singular, feature_names


def event_rows(
    raw: Sequence[dict[str, Any]], names: Sequence[str], maximum_issue: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    baseline = {sample["issue"]: sample for sample in raw if sample["group"] == "b0"}
    if set(baseline) != set(range(maximum_issue + 1)):
        raise InputIntegrityError("M1 q0 baseline does not cover every issue")
    result: list[dict[str, Any]] = []
    for sample in raw:
        issue = int(sample["issue"])
        if issue < 0 or issue > maximum_issue:
            raise InputIntegrityError(f"M1 issue outside event vocabulary: {issue}")
        reference = baseline[issue]
        event = np.zeros(maximum_issue + 1)
        event[issue] = 1.0
        result.append({
            **sample,
            "x_event": np.concatenate([sample["x"], sample["x"] - reference["x"], event]),
            "response": sample["y"] - reference["y"],
            "baseline_y": reference["y"],
        })
    feature_names = list(names) + [f"delta_q0_{name}" for name in names] + [
        f"issue_{index}" for index in range(maximum_issue + 1)
    ]
    return result, feature_names


def _deduplicate(samples: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[tuple[float, ...], dict[str, Any]] = {}
    for sample in samples:
        key = tuple(np.round(np.concatenate([sample["x_event"], sample["response"]]), 12))
        unique.setdefault(key, sample)
    return list(unique.values())


def fit_ensemble(
    train: Sequence[dict[str, Any]], hidden: Sequence[int], seeds: Sequence[int],
    epochs: int, learning_rate: float, weight_decay: float, scales: np.ndarray,
) -> dict[str, Any]:
    unique = _deduplicate(train)
    x = np.asarray([sample["x_event"] for sample in unique], dtype=np.float64)
    y = np.asarray([sample["response"] / scales for sample in unique], dtype=np.float64)
    mean, std = x.mean(axis=0), x.std(axis=0)
    keep = std > 1e-12
    z = ((x[:, keep] - mean[keep]) / std[keep]).astype(np.float32)
    target = y.astype(np.float32)
    inputs = torch.from_numpy(z)
    targets = torch.from_numpy(target)
    models = []
    torch.set_num_threads(1)
    for seed in seeds:
        torch.manual_seed(int(seed))
        network = EventResidualNet(z.shape[1], hidden)
        optimizer = torch.optim.Adam(
            network.parameters(), lr=learning_rate, weight_decay=weight_decay
        )
        for _ in range(epochs):
            optimizer.zero_grad(set_to_none=True)
            loss = torch.mean((network(inputs) - targets) ** 2)
            loss.backward()
            optimizer.step()
        network.eval()
        models.append(network)
    return {
        "mean": mean, "std": std, "keep": keep, "models": models,
        "train_unique_rows": len(unique), "input_width": int(z.shape[1]),
    }


def predict_response(model: dict[str, Any], samples: Sequence[dict[str, Any]], scales: np.ndarray) -> np.ndarray:
    x = np.asarray([sample["x_event"] for sample in samples], dtype=np.float64)
    z = ((x[:, model["keep"]] - model["mean"][model["keep"]]) / model["std"][model["keep"]]).astype(np.float32)
    inputs = torch.from_numpy(z)
    with torch.no_grad():
        values = [network(inputs).cpu().numpy().astype(np.float64) for network in model["models"]]
    return np.mean(values, axis=0) * scales


def fold_metrics(model: dict[str, Any], test: Sequence[dict[str, Any]], scales: np.ndarray) -> dict[str, Any]:
    response_prediction = predict_response(model, test, scales)
    response_truth = np.asarray([sample["response"] for sample in test])
    prediction = response_prediction + np.asarray([sample["baseline_y"] for sample in test])
    truth = np.asarray([sample["y"] for sample in test])
    error = np.abs(prediction - truth)
    denominator = float(np.mean(np.sum((response_truth / scales) ** 2, axis=1)))
    numerator = float(np.mean(np.sum(((response_prediction - response_truth) / scales) ** 2, axis=1)))
    nrmse = math.sqrt(numerator / denominator) if denominator > 0 else math.inf
    cosines = []
    for family in sorted({sample["family"] for sample in test}):
        indices = [index for index, sample in enumerate(test) if sample["family"] == family]
        peak = max(indices, key=lambda index: np.linalg.norm(response_truth[index, :2]))
        actual, predicted = response_truth[peak, :2], response_prediction[peak, :2]
        norm = float(np.linalg.norm(actual) * np.linalg.norm(predicted))
        cosines.append(float(actual @ predicted / norm) if norm > 0 else -1.0)
    return {
        "rows": len(test),
        "r_p95_mm": float(np.quantile(error[:, 0], 0.95)),
        "z_p95_mm": float(np.quantile(error[:, 1], 0.95)),
        "ip_p95_a": float(np.quantile(error[:, 2], 0.95)),
        "r_max_mm": float(np.max(error[:, 0])),
        "paired_response_nrmse": nrmse,
        "improvement_over_zero_response_fraction": 1.0 - nrmse,
        "minimum_family_peak_direction_cosine": min(cosines),
        "family_peak_direction_cosines": cosines,
    }


def _selectors(fold: dict[str, Any], family: str) -> bool:
    return any(family.startswith(selector) for selector in fold["selectors"])


def _artifact_network(network: nn.Module) -> dict[str, Any]:
    return {name: tensor.detach().cpu().numpy().tolist() for name, tensor in network.state_dict().items()}


def execute(config_path: Path, source_revision: str, output_dir: Path) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {output_dir}")
    output_dir.mkdir(parents=True)
    try:
        stage, samples, basis, singular, feature_names = load(config_path)
    except Exception as exc:
        result = {
            "schema_version": SCHEMA, "kind": "fixed_1000_event_aware_model_development",
            "created_utc": datetime.now(timezone.utc).isoformat(), "source_revision": source_revision,
            "passed": False, "route": "ONE_MS_NR1000M1_INPUT_INTEGRITY_FAIL_ZERO_TSC",
            "failures": [f"{type(exc).__name__}:{exc}"], "plant_advances": 0,
        }
        b0.write_new(output_dir / "result.json", result)
        return result
    scales = np.asarray(stage["output_scales"], dtype=float)
    folds = []
    for fold in stage["whole_family_folds"]:
        test = [sample for sample in samples if _selectors(fold, sample["family"])]
        train = [sample for sample in samples if not _selectors(fold, sample["family"])]
        if not test or any(sample["group"] == "b0" for sample in test):
            raise InputIntegrityError(f"invalid M1 fold: {fold['name']}")
        model = fit_ensemble(
            train, stage["hidden_widths"], stage["seeds"], stage["epochs"],
            stage["learning_rate"], stage["weight_decay"], scales,
        )
        folds.append({
            "fold": fold["name"], "held_families": sorted({sample["family"] for sample in test}),
            "metrics": fold_metrics(model, test, scales),
            "train_unique_rows": model["train_unique_rows"], "network_input_width": model["input_width"],
        })
    gates = stage["gates"]
    mean_nrmse = float(np.mean([fold["metrics"]["paired_response_nrmse"] for fold in folds]))
    absolute_pass = all(
        fold["metrics"]["r_p95_mm"] <= gates["maximum_each_fold_one_step_r_p95_mm"]
        and fold["metrics"]["z_p95_mm"] <= gates["maximum_each_fold_one_step_z_p95_mm"]
        and fold["metrics"]["ip_p95_a"] <= gates["maximum_each_fold_one_step_ip_p95_a"]
        and fold["metrics"]["r_max_mm"] <= gates["maximum_each_fold_one_step_r_max_mm"]
        for fold in folds
    )
    response_pass = (
        mean_nrmse <= gates["maximum_mean_paired_response_nrmse"]
        and 1.0 - mean_nrmse >= gates["minimum_improvement_over_zero_response_fraction"]
        and min(fold["metrics"]["minimum_family_peak_direction_cosine"] for fold in folds)
        >= gates["minimum_peak_response_direction_cosine"]
    )
    passed = absolute_pass and response_pass
    result = {
        "schema_version": SCHEMA, "kind": "fixed_1000_event_aware_model_development",
        "created_utc": datetime.now(timezone.utc).isoformat(), "source_revision": source_revision,
        "passed": passed, "route": stage["routes"]["pass"] if passed else stage["routes"]["model_fail"],
        "plant_advances": 0, "trajectory_count": 25, "sample_rows": len(samples),
        "event_feature_count": 64, "feature_count": len(feature_names),
        "action_basis_rank": 6, "action_basis_singular_values_a": singular.tolist(),
        "folds": folds, "mean_paired_response_nrmse": mean_nrmse,
        "improvement_over_zero_response_fraction": 1.0 - mean_nrmse,
        "absolute_gate_pass": absolute_pass, "response_gate_pass": response_pass,
        "claim_boundary": "fixed-1000 retrospective development only; no calibration/holdout/controller",
    }
    if passed:
        final = fit_ensemble(
            samples, stage["hidden_widths"], stage["seeds"], stage["epochs"],
            stage["learning_rate"], stage["weight_decay"], scales,
        )
        artifact = {
            "schema_version": f"{SCHEMA}-artifact", "source_revision": source_revision,
            "feature_names": feature_names, "output_scales": scales.tolist(),
            "mean": final["mean"].tolist(), "std": final["std"].tolist(),
            "keep": final["keep"].tolist(), "hidden_widths": stage["hidden_widths"],
            "seeds": stage["seeds"], "networks": [_artifact_network(value) for value in final["models"]],
            "action_basis_tsc_order": basis.tolist(),
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
