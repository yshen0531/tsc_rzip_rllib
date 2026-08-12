#!/usr/bin/env python3
"""Fit/calibrate frozen NR2 candidates and evaluate fresh holdout once."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tsc_rzip_rllib.control.rgeo_zgeo_nr2_models import (  # noqa: E402
    Normalizer,
    OUTPUT_SCALES,
    POINT_SCALES,
    build_neural,
    fit_arx,
    fit_neural,
    recursive_errors,
    recursive_rollout,
)
from tsc_rzip_rllib.control.rgeo_zgeo_nr2_spec import NR2_CAMPAIGN_ID, build_nr2_specs  # noqa: E402


SEEDS = (1701, 1702, 1703, 1704, 1705)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_new(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_trajectories(campaign_dir: Path, splits: set[str]) -> list[dict[str, Any]]:
    result = []
    for spec in build_nr2_specs():
        if spec.split not in splits:
            continue
        record = json.loads((campaign_dir / "records" / f"{spec.trajectory_id}.json").read_text(encoding="utf-8"))
        if record.get("passed") is not True or record.get("spec") != spec.to_dict():
            raise ValueError(f"invalid NR2 record {spec.trajectory_id}")
        states = [[
            float(state["r_geo_m"]), float(state["z_geo_m"]), float(state["ip_a"]),
            *map(float, state["actual_current_a_tsc"]),
        ] for state in record["states"]]
        actions = [list(map(float, action["target"]["quantized_current_a_tsc"])) for action in record["actions"]]
        if len(states) != 9 or len(actions) != 8:
            raise ValueError(f"invalid trajectory shape {spec.trajectory_id}")
        result.append({"id": spec.trajectory_id, "split": spec.split, "pair_index": spec.pair_index,
                       "states": states, "actions": actions})
    return result


def _normalizer(trajectories: list[dict[str, Any]]) -> Normalizer:
    return Normalizer.fit(np.asarray([row["states"] for row in trajectories]),
                          np.asarray([row["actions"] for row in trajectories]))


def _metric(models: list[Any], trajectories: list[dict[str, Any]], normalizer: Normalizer, neural: bool) -> float:
    values = []
    for trajectory in trajectories:
        predictions = [recursive_rollout(model, trajectory, normalizer, neural) for model in models]
        mean = np.mean(predictions, axis=0)
        actual = np.asarray(trajectory["states"])
        values.append(np.mean(((mean[1:] - actual[1:]) / OUTPUT_SCALES) ** 2))
    return float(np.mean(values))


def _folds(trajectories: list[dict[str, Any]]):
    for fold in range(4):
        train = [row for row in trajectories if row["pair_index"] % 4 != fold]
        validation = [row for row in trajectories if row["pair_index"] % 4 == fold]
        yield train, validation


def select_candidates(development: list[dict[str, Any]], normalizer: Normalizer) -> dict[str, Any]:
    table = []
    for ridge in (1e-6, 1e-4, 1e-2):
        scores = []
        for train, validation in _folds(development):
            fold_normalizer = _normalizer(train)
            scores.append(_metric([fit_arx(train, fold_normalizer, ridge)], validation, fold_normalizer, False))
        table.append({"class": "arx", "value": ridge, "fold_scores": scores, "mean": float(np.mean(scores))})
    for kind in ("gru", "lstm", "tcn"):
        for width in (8, 12):
            scores = []
            for fold, (train, validation) in enumerate(_folds(development)):
                fold_normalizer = _normalizer(train)
                model = fit_neural(kind, width, train, fold_normalizer, SEEDS[0] + fold)
                scores.append(_metric([model], validation, fold_normalizer, True))
            table.append({"class": kind, "value": width, "fold_scores": scores, "mean": float(np.mean(scores))})
    selected = {}
    for kind in ("arx", "gru", "lstm", "tcn"):
        rows = [row for row in table if row["class"] == kind]
        selected[kind] = min(rows, key=lambda row: (row["mean"], row["value"]))["value"]
    return {"table": table, "selected": selected}


def fit_ensembles(development: list[dict[str, Any]], normalizer: Normalizer, selected: dict[str, Any]):
    output = {}
    count = len(development)
    for kind, value in selected.items():
        members = []
        for seed in SEEDS:
            if kind == "arx":
                rng = np.random.default_rng(seed)
                indices = rng.integers(0, count, size=count)
                members.append(fit_arx(development, normalizer, float(value), indices))
            else:
                members.append(fit_neural(kind, int(value), development, normalizer, seed))
        output[kind] = members
    return output


def _ensemble_predictions(models, trajectories, normalizer, neural):
    return [[recursive_rollout(model, trajectory, normalizer, neural) for model in models] for trajectory in trajectories]


def calibrate(models, development, calibration, normalizer, neural):
    dev_predictions = _ensemble_predictions(models, development, normalizer, neural)
    residuals = []
    for predictions, trajectory in zip(dev_predictions, development):
        mean = np.mean(predictions, axis=0)
        residuals.append(np.abs(mean[1:] - np.asarray(trajectory["states"])[1:]))
    base = np.quantile(np.concatenate(residuals), 0.95, axis=0, method="linear")
    base = np.maximum(base, np.asarray([1e-9, 1e-9, 1e-6] + [1e-6] * 14))
    calibration_predictions = _ensemble_predictions(models, calibration, normalizer, neural)
    ratios = []
    for predictions, trajectory in zip(calibration_predictions, calibration):
        mean = np.mean(predictions, axis=0)
        ratios.extend(np.max(np.abs(mean[1:] - np.asarray(trajectory["states"])[1:]) / base, axis=1))
    multiplier = float(np.quantile(ratios, 0.90, method="higher"))
    half = multiplier * base
    coverage = float(np.mean(np.asarray(ratios) <= multiplier + 1e-12))
    eligible = coverage >= 0.90 and bool(np.all(half[:3] <= np.asarray([0.02, 0.02, 2000.0])))
    return {"base_half_width": base.tolist(), "multiplier": multiplier, "half_width": half.tolist(),
            "joint_coverage": coverage, "eligible": eligible}


def _serialize(ensembles, selected, normalizer, calibration_rows):
    members = {}
    for kind, models in ensembles.items():
        if kind == "arx":
            members[kind] = [{"coefficient": model.coefficient} for model in models]
        else:
            members[kind] = [model.state_dict() for model in models]
    return {"campaign_id": NR2_CAMPAIGN_ID, "selected": selected, "normalizer": normalizer.to_dict(),
            "calibration": calibration_rows, "members": members, "seeds": SEEDS}


def fit_calibrate(campaign_dir: Path, source_revision: str) -> dict[str, Any]:
    audit = json.loads((campaign_dir / "development_calibration_independent.json").read_text(encoding="utf-8"))
    if audit.get("passed") is not True or audit.get("source_revision") != source_revision:
        raise RuntimeError("independent development/calibration audit is not accepted")
    development = load_trajectories(campaign_dir, {"development"})
    calibration_data = load_trajectories(campaign_dir, {"calibration"})
    normalizer = _normalizer(development)
    selection = select_candidates(development, normalizer)
    ensembles = fit_ensembles(development, normalizer, selection["selected"])
    calibration_rows = {kind: calibrate(models, development, calibration_data, normalizer, kind != "arx")
                        for kind, models in ensembles.items()}
    bundle_path = campaign_dir / "frozen_models.pt"
    if bundle_path.exists():
        raise FileExistsError(f"refusing to overwrite {bundle_path}")
    torch.save(_serialize(ensembles, selection["selected"], normalizer, calibration_rows), bundle_path)
    bundle_hash = _sha256(bundle_path)
    eligible = sorted(kind for kind, row in calibration_rows.items() if row["eligible"])
    result = {"campaign_id": NR2_CAMPAIGN_ID, "source_revision": source_revision, "passed": bool(eligible),
              "route": "NR2_CALIBRATED_CANDIDATES_FROZEN_HOLDOUT_AUTHORIZED" if eligible else "NR2_CALIBRATION_FAIL_NO_HOLDOUT",
              "selection": selection, "calibration": calibration_rows, "eligible_classes": eligible,
              "frozen_model_sha256": bundle_hash}
    _write_new(campaign_dir / "fit_calibrate.json", result)
    if eligible:
        _write_new(campaign_dir / "holdout_authorization.json", {"campaign_id": NR2_CAMPAIGN_ID,
                   "holdout_authorized": True, "source_revision": source_revision,
                   "frozen_model_sha256": [bundle_hash], "eligible_classes": eligible})
    return result


def _deserialize(bundle):
    normalizer = Normalizer.from_dict(bundle["normalizer"])
    ensembles = {}
    for kind, rows in bundle["members"].items():
        if kind == "arx":
            from tsc_rzip_rllib.control.rgeo_zgeo_nr2_models import ARXModel
            ensembles[kind] = [ARXModel(normalizer, row["coefficient"].numpy() if hasattr(row["coefficient"], "numpy") else row["coefficient"]) for row in rows]
        else:
            models = []
            for state in rows:
                model = build_neural(kind, int(bundle["selected"][kind]))
                model.load_state_dict(state); model.eval(); models.append(model)
            ensembles[kind] = models
    return normalizer, ensembles


def evaluate_holdout(campaign_dir: Path, source_revision: str) -> dict[str, Any]:
    auth = json.loads((campaign_dir / "holdout_authorization.json").read_text(encoding="utf-8"))
    audit = json.loads((campaign_dir / "holdout_independent.json").read_text(encoding="utf-8"))
    bundle_path = campaign_dir / "frozen_models.pt"
    if auth["frozen_model_sha256"] != [_sha256(bundle_path)] or audit.get("passed") is not True:
        raise RuntimeError("holdout audit or frozen model hash mismatch")
    bundle = torch.load(bundle_path, map_location="cpu", weights_only=False)
    normalizer, ensembles = _deserialize(bundle)
    holdout = load_trajectories(campaign_dir, {"holdout"})
    rows = {}
    for kind in auth["eligible_classes"]:
        predictions = _ensemble_predictions(ensembles[kind], holdout, normalizer, kind != "arx")
        scaled_rows=[]; current_rows=[]; coverage_rows=[]; finite=True; mse=[]
        half=np.asarray(bundle["calibration"][kind]["half_width"])
        for member_predictions, trajectory in zip(predictions, holdout):
            mean=np.mean(member_predictions,axis=0); actual=np.asarray(trajectory["states"])
            errors=recursive_errors(mean,trajectory); finite=finite and errors["finite"]
            scaled_rows.extend(np.max(errors["scaled"],axis=1)); current_rows.extend(errors["current_max_abs_a"])
            coverage_rows.extend(np.all(np.abs(mean[1:,:3]-actual[1:,:3]) <= half[:3],axis=1))
            mse.append(np.mean(((mean[1:]-actual[1:])/OUTPUT_SCALES)**2))
        metrics={"finite":finite,"joint_point_fraction":float(np.mean(np.asarray(scaled_rows)<=1.0)),
                 "p95_scaled_error":float(np.quantile(scaled_rows,0.95,method="linear")),
                 "joint_interval_coverage":float(np.mean(coverage_rows)),
                 "p95_current_error_a":float(np.quantile(current_rows,0.95,method="linear")),
                 "mean_squared_scaled_error":float(np.mean(mse))}
        metrics["passed"]=finite and metrics["joint_point_fraction"]>=0.90 and metrics["p95_scaled_error"]<=1.0 and metrics["joint_interval_coverage"]>=0.90 and metrics["p95_current_error_a"]<=0.05
        rows[kind]=metrics
    passed=[kind for kind,row in rows.items() if row["passed"]]
    winner=None
    if passed:
        best=min(passed,key=lambda kind: rows[kind]["mean_squared_scaled_error"])
        if best != "arx" and "arx" in passed:
            gain=1.0-rows[best]["mean_squared_scaled_error"]/rows["arx"]["mean_squared_scaled_error"]
            if gain < 0.15 or rows[best]["joint_interval_coverage"] < rows["arx"]["joint_interval_coverage"] or rows[best]["p95_scaled_error"] > rows["arx"]["p95_scaled_error"]:
                best="arx"
        winner=best
    result={"campaign_id":NR2_CAMPAIGN_ID,"source_revision":source_revision,"passed":winner is not None,
            "route":"NR2_CAUSAL_MODEL_QUALIFIED" if winner else "CAUSAL_MODEL_COMPARISON_FAIL_REDESIGN",
            "winner":winner,"models":rows,"frozen_model_sha256":_sha256(bundle_path)}
    _write_new(campaign_dir/"holdout_evaluation.json",result)
    return result


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("mode",choices=("fit_calibrate","evaluate_holdout")); parser.add_argument("--campaign-dir",type=Path,required=True); parser.add_argument("--source-revision",required=True); args=parser.parse_args()
    result=fit_calibrate(args.campaign_dir.resolve(),args.source_revision) if args.mode=="fit_calibrate" else evaluate_holdout(args.campaign_dir.resolve(),args.source_revision)
    print(json.dumps(result,indent=2,sort_keys=True)); return 0 if result["passed"] else 2


if __name__ == "__main__": raise SystemExit(main())
