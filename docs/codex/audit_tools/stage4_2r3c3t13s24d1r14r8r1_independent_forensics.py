#!/usr/bin/env python3
"""Structurally independent R8R1 fixed short-horizon recomputation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r7r2_independent_forensics as independent_model,
    stage4_2r3c3t13s24d1r14r8_independent_forensics as independent_r8,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r1_fixed_candidate_short_horizon_discriminator as contract,
)


def _json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _model_cfg(cfg: Mapping[str, Any], r8_cfg: Mapping[str, Any]) -> dict[str, Any]:
    return contract.model_config(cfg, r8_cfg)


def _truncate(row: Mapping[str, Any], horizon: int) -> dict[str, Any]:
    response = np.asarray(row["response"], dtype=float)
    if response.shape[1:] != (5,) or len(response) < horizon:
        raise ValueError("R8R1 independent response horizon changed")
    output = dict(row)
    output["descriptor"] = np.asarray(row["descriptor"], dtype=float)
    output["response"] = response[:horizon]
    return output


def _outer(
    items: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any], r8_cfg: Mapping[str, Any]
) -> tuple[dict[int, list[dict[str, Any]]], list[dict[str, Any]]]:
    mcfg = _model_cfg(cfg, r8_cfg)
    candidate = contract.candidate_tuple(cfg)
    horizons = tuple(map(int, cfg["horizon_contract"]["evaluated_relative_lags"]))
    maximum = max(horizons)
    pairs = sorted({str(row["pair_id"]) for row in items})
    rows = {horizon: [] for horizon in horizons}
    folds = []
    for pair in pairs:
        train = [_truncate(row, maximum) for row in items if str(row["pair_id"]) != pair]
        held = [_truncate(row, maximum) for row in items if str(row["pair_id"]) == pair]
        fitted = independent_model._fit(train, candidate, mcfg)
        for row in held:
            prediction = independent_model._predict(fitted, row, mcfg)
            for horizon in horizons:
                rows[horizon].append(
                    independent_model._metric(_truncate(row, horizon), prediction[:horizon], mcfg)
                )
        folds.append(
            {
                "held_pair_id": pair,
                "training_pair_count": 11,
                "held_response_count": len(held),
                "fixed_candidate": dict(cfg["fixed_candidate"]),
            }
        )
    for horizon in horizons:
        rows[horizon].sort(key=lambda row: str(row["response_id"]))
        if len(rows[horizon]) != 912:
            raise ValueError("R8R1 independent outer coverage changed")
    return rows, folds


def _aggregate(rows: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> dict[str, Any]:
    component = np.max(
        np.asarray([row["componentwise_maximum_absolute_scaled_error"] for row in rows]),
        axis=0,
    )
    scales = np.asarray(cfg["bank_contract"]["response_scales"], dtype=float)
    gates = cfg["gates"]
    precursor = (
        np.asarray(gates["response_floor_physical"], dtype=float) / scales
        + float(gates["tube_multiplier"]) * component
    )
    caps = np.asarray(gates["tube_caps_physical"], dtype=float) / scales
    return {
        "response_count": len(rows),
        "response_pass_count": sum(bool(row["passed"]) for row in rows),
        "maximum_relative_l2_error": max(float(row["relative_l2_error"]) for row in rows),
        "minimum_response_cosine": min(float(row["response_cosine"]) for row in rows),
        "minimum_peak_ratio": min(float(row["peak_ratio"]) for row in rows),
        "maximum_peak_ratio": max(float(row["peak_ratio"]) for row in rows),
        "maximum_absolute_scaled_point_error": max(float(row["maximum_absolute_scaled_point_error"]) for row in rows),
        "componentwise_maximum_absolute_scaled_error": component.tolist(),
        "tube_precursor_scaled": precursor.tolist(),
        "tube_precursor_physical": (precursor * scales).tolist(),
        "tube_cap_pass": bool(np.all(precursor <= caps + 1e-15)),
        "passed": bool(
            len(rows) == int(gates["required_response_pass_count"])
            and all(bool(row["passed"]) for row in rows)
            and np.all(precursor <= caps + 1e-15)
        ),
    }


def _actual_rows(items: Sequence[Mapping[str, Any]], horizon: int) -> list[dict[str, Any]]:
    output = []
    for source in items:
        row = _truncate(source, horizon)
        output.append(
            {
                "response_id": row["response_id"], "context_id": row["context_id"],
                "pair_id": row["pair_id"], "history_member": row["history_member"],
                "issue_task_step": row["issue_task_step"], "sign": row["sign"],
                "direction_index": row["direction_index"], "source_stage": row["source_stage"],
                "action_scale": row["action_scale"], "geometry_roles": list(row["geometry_roles"]),
                "predicted_response": np.asarray(row["response"], dtype=float).tolist(),
            }
        )
    return sorted(output, key=lambda row: str(row["response_id"]))


def _horizon(
    items: Sequence[Mapping[str, Any]], rows: Sequence[Mapping[str, Any]],
    horizon: int, cfg: Mapping[str, Any], r8_cfg: Mapping[str, Any],
) -> dict[str, Any]:
    mcfg = _model_cfg(cfg, r8_cfg)
    aggregate = _aggregate(rows, cfg)
    predicted = independent_model._geometry(rows, mcfg)
    actual = independent_model._geometry(_actual_rows(items, horizon), mcfg)
    actual["interpretation"] = "actual_truncated_response_geometry"
    return {
        "relative_lag_horizon": horizon,
        "elapsed_horizon_ms": 10 * horizon,
        "diagnostic_only": horizon in set(map(int, cfg["horizon_contract"]["diagnostic_only_relative_lags"])),
        "aggregate": aggregate,
        "predicted_geometry": predicted,
        "actual_geometry": actual,
        "passed": bool(aggregate["passed"] and predicted["passed"] and actual["passed"]),
    }


def _authenticate(args: argparse.Namespace, cfg: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    root = Path(__file__).resolve().parents[3]
    source_config = (root / str(cfg["source_r8_config"])).resolve()
    if _sha(source_config) != str(cfg["source_r8_config_sha256"]):
        raise ValueError("R8R1 independent source config changed")
    r8_cfg = _json(source_config)
    independent_r8._validate(r8_cfg)
    paths = independent_r8._paths(args.r8_run.resolve())
    source = cfg["source_r8_contract"]
    source_state_path = paths["stage"] / "stage_state.json"
    files = (
        (source_state_path, int(source["stage_state_bytes"]), str(source["stage_state_sha256"])),
        (paths["manifest"], int(source["stage_manifest_bytes"]), str(source["stage_manifest_sha256"])),
        (paths["analysis"] / "training_model_primary_detailed.json", None, str(source["primary_detailed_sha256"])),
        (paths["analysis"] / "training_model_primary_summary.json", None, str(source["primary_summary_sha256"])),
        (paths["analysis"] / "training_model_independent.json", int(source["independent_model_bytes"]), str(source["independent_model_sha256"])),
    )
    for path, size, sha in files:
        if not path.is_file() or (size is not None and path.stat().st_size != size) or _sha(path) != sha:
            raise ValueError("R8R1 independent source artifact changed")
    state = _json(source_state_path)
    source_independent = _json(paths["analysis"] / "training_model_independent.json")
    if (
        state.get("phase_status") != source["required_phase_status"]
        or int(state.get("new_raw_count", -1)) != int(source["required_new_raw_count"])
        or bool(state.get("heldout_outcomes_opened"))
        or (state.get("verdict") or {}).get("route") != source["required_route"]
        or source_independent.get("passed") is not True
        or source_independent.get("scientific_gate_passed") is not False
        or source_independent.get("primary_numerical_agreement") is not True
        or source_independent.get("primary_outcome_agreement") is not True
        or source_independent.get("model_artifact_presence_agreement") is not True
    ):
        raise ValueError("R8R1 independent source outcome changed")
    inventory = independent_r8._inventory(paths["raw_training"])
    if (
        inventory["count"] != int(source["training_raw_count"])
        or inventory["bytes"] != int(source["training_raw_bytes"])
        or inventory["digest"] != source["training_raw_digest"]
        or any(paths["raw_calibration"].glob("*.json.gz"))
        or any(paths["raw_holdout"].glob("*.json.gz"))
    ):
        raise ValueError("R8R1 independent raw/heldout boundary changed")
    items, existing, extension = independent_r8._training_items(r8_cfg, paths, args)
    if len(items) != 912 or len({row["pair_id"] for row in items}) != 12:
        raise ValueError("R8R1 independent training bank changed")
    return items, r8_cfg


def audit(args: argparse.Namespace) -> dict[str, Any]:
    cfg = _json(args.config.resolve())
    contract.validate_config(cfg)
    root = Path(__file__).resolve().parents[3]
    design = (root / str(cfg["design_document"])).resolve()
    if _sha(design) != str(cfg["design_document_sha256"]):
        raise ValueError("R8R1 independent design hash changed")
    output = args.output_dir.resolve()
    primary_path = output / "primary_detailed.json"
    summary_path = output / "primary_summary.json"
    state_path = output / "stage_state.json"
    if not all(path.is_file() for path in (primary_path, summary_path, state_path)):
        raise ValueError("R8R1 primary output missing")
    primary, primary_summary, state = _json(primary_path), _json(summary_path), _json(state_path)
    if state.get("independent_completed") is not False:
        raise ValueError("R8R1 independent audit already recorded")
    items, r8_cfg = _authenticate(args, cfg)
    rows, folds = _outer(items, cfg, r8_cfg)
    horizons = {
        horizon: _horizon(items, rows[horizon], horizon, cfg, r8_cfg)
        for horizon in map(int, cfg["horizon_contract"]["evaluated_relative_lags"])
    }
    selected = contract.select_horizon(horizons, cfg)
    route = contract.route_for(selected, cfg)
    primary_horizons = {int(key): value for key, value in primary["horizons"].items()}
    numerical = bool(
        independent_r8.r7_frozen._agrees(primary["outer_folds"], folds)
        and independent_r8.r7_frozen._agrees(primary_horizons, horizons)
    )
    outcome = bool(
        primary.get("selected_relative_lag_horizon") == selected
        and primary_summary.get("selected_relative_lag_horizon") == selected
        and primary.get("route") == route
        and primary_summary.get("route") == route
        and bool(primary.get("scientific_gate_passed")) is (selected is not None)
    )
    model_path = output / "selected_short_horizon_model.json"
    artifact_presence = model_path.is_file() is (selected is not None)
    model_sha = _sha(model_path) if model_path.is_file() else ""
    artifact_contract = bool(model_sha == str(primary.get("model_sha256", "")))
    result = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "audit_kind": "independent",
        "fixed_candidate": dict(cfg["fixed_candidate"]),
        "horizons": {str(key): contract.compact_horizon(value) for key, value in horizons.items()},
        "selected_relative_lag_horizon": selected,
        "route": route,
        "scientific_gate_passed": selected is not None,
        "primary_numerical_agreement": numerical,
        "primary_outcome_agreement": outcome,
        "model_artifact_presence_agreement": artifact_presence,
        "model_artifact_contract_agreement": artifact_contract,
        "model_sha256": model_sha,
        "source_primary_sha256": _sha(primary_path),
        "new_raw_count": 0,
        "ray_executed": False,
        "gotsc_executed": False,
        "tsc_executed": False,
        "plant_advance_count": 0,
        "passed": bool(numerical and outcome and artifact_presence and artifact_contract),
    }
    result_path = output / "independent.json"
    _write(result_path, result)
    state.update(
        {
            "independent_completed": True,
            "independent_passed": result["passed"],
            "independent_sha256": _sha(result_path),
        }
    )
    _write(state_path, state)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    if not result["passed"]:
        raise SystemExit(2)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--r8-run", type=Path, required=True)
    parser.add_argument("--source-r2-run", type=Path, required=True)
    parser.add_argument("--source-r4-run", type=Path, required=True)
    parser.add_argument("--source-r6-run", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


if __name__ == "__main__":
    audit(_parser().parse_args())
