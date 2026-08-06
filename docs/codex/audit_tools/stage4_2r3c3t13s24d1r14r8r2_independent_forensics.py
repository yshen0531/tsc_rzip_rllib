#!/usr/bin/env python3
"""Structurally independent R8R2 causal innovation recomputation."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r7_independent_forensics as frozen,
    stage4_2r3c3t13s24d1r14r7r2_independent_forensics as kernel,
    stage4_2r3c3t13s24d1r14r8_independent_forensics as r8_independent,
    stage4_2r3c3t13s24d1r14r8r1_independent_forensics as r8r1_independent,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r2_causal_online_innovation_adaptation as contract,
)


def _json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def _write(path: Path, value: Any) -> None:
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


def _check(path: Path, size: int, sha: str) -> None:
    if not path.is_file() or path.stat().st_size != size or _sha(path) != sha:
        raise ValueError("R8R2 independent source artifact changed")


def _r8r1_source(output: Path, cfg: Mapping[str, Any]) -> dict[str, Any]:
    source = cfg["source_r8r1_contract"]
    paths = {
        "primary_detailed": output / "primary_detailed.json",
        "primary_summary": output / "primary_summary.json",
        "independent": output / "independent.json",
        "state": output / "stage_state.json",
    }
    contract_keys = {
        "primary_detailed": "primary_detailed",
        "primary_summary": "primary_summary",
        "independent": "independent",
        "state": "stage_state",
    }
    for key, contract_key in contract_keys.items():
        _check(
            paths[key],
            int(source[f"{contract_key}_bytes"]),
            str(source[f"{contract_key}_sha256"]),
        )
    primary, independent, state = (
        _json(paths["primary_detailed"]),
        _json(paths["independent"]),
        _json(paths["state"]),
    )
    route = str(source["required_route"])
    if (
        primary.get("route") != route
        or primary.get("passed") is not True
        or primary.get("scientific_gate_passed") is not False
        or independent.get("route") != route
        or independent.get("passed") is not True
        or independent.get("primary_numerical_agreement") is not True
        or independent.get("primary_outcome_agreement") is not True
        or state.get("route") != route
        or state.get("independent_completed") is not True
        or int(state.get("new_raw_count", -1)) != 0
        or bool(state.get("heldout_outcomes_opened"))
        or str(state.get("model_sha256") or "")
    ):
        raise ValueError("R8R2 independent source R8R1 outcome changed")
    return {key + "_sha256": _sha(path) for key, path in paths.items()}


def _visible_descriptor(
    visible: np.ndarray, issue: int, target: Sequence[float], cfg: Mapping[str, Any]
) -> np.ndarray:
    offsets = tuple(map(int, cfg["bank_contract"]["history_offsets"]))
    history = visible[[max(0, issue - offset) for offset in offsets]].reshape(-1)
    availability = np.asarray([float(offset <= issue) for offset in offsets])
    scaled_target = np.asarray(target, dtype=float) / np.asarray(
        cfg["bank_contract"]["target_scales"], dtype=float
    )
    descriptor = np.r_[history, availability, scaled_target, (issue - 10.0) / 12.0]
    if descriptor.shape != (142,) or not np.all(np.isfinite(descriptor)):
        raise ValueError("R8R2 independent probe descriptor invalid")
    return descriptor


def _source_records(
    cfg: Mapping[str, Any], r8_cfg: Mapping[str, Any], paths: Mapping[str, Path],
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    items, _, _ = r8_independent._training_items(r8_cfg, paths, args)
    scales = np.asarray(cfg["bank_contract"]["response_scales"], dtype=float)
    sources = {
        "r2": frozen._read_source(args.source_r2_run.resolve(), r8_cfg["source_response_contracts"]["r2"]),
        "r4": frozen._read_source(args.source_r4_run.resolve(), r8_cfg["source_response_contracts"]["r4"]),
        "r6": frozen._read_source(args.source_r6_run.resolve(), r8_cfg["source_response_contracts"]["r6"]),
    }
    indexes = {
        "r2": frozen._index(sources["r2"], "d1r14r2", 10),
        "r4": frozen._index(sources["r4"], "d1r14r4", -1),
        "r6": frozen._index(sources["r6"], "d1r14r6", -1),
    }
    existing_by_id = {}
    for source in sources.values():
        specs = {str(row["experiment_id"]): row for row in source["specs"]}
        existing_by_id.update(
            {experiment_id: (specs[experiment_id], result) for experiment_id, result in source["results"].items()}
        )
    specs = r8_independent._specs(paths, "training")
    results = {
        str(spec["experiment_id"]): r8_independent._gzip(
            paths["raw_training"] / f"{spec['experiment_id']}.json.gz"
        )
        for spec in specs
    }
    spec_by_id = {str(spec["experiment_id"]): spec for spec in specs}
    new_baselines = {}
    for spec in specs:
        if str(spec["d1r14r8_role"]) == "baseline":
            context = f"{spec['pair_id']}|{spec['history_member']}"
            new_baselines[context] = (spec, results[str(spec["experiment_id"])])
    records = []
    windows = {}
    response_exact = descriptor_equal = 0
    for source_item in items:
        item = dict(source_item)
        response_id = str(item["response_id"])
        context = str(item["context_id"])
        issue = int(item["issue_task_step"])
        if str(item["source_stage"]) == "R8":
            probe_spec, probe_result = spec_by_id[response_id], results[response_id]
            baseline_spec, baseline_result = new_baselines[context]
        else:
            probe_spec, probe_result = existing_by_id[response_id]
            baseline_spec, baseline_result = indexes["r2" if issue == 10 else "r4"][context][
                ("baseline", -1, -1, 0)
            ]
        probe = frozen._visible(probe_result["trajectory"], scales)
        baseline = frozen._visible(baseline_result["trajectory"], scales)
        descriptor = _visible_descriptor(
            probe,
            issue,
            (
                float(probe_spec["target_R_offset_m"]),
                float(probe_spec["target_Z_offset_m"]),
                float(probe_spec["target_Ip_offset_A"]),
            ),
            cfg,
        )
        target = probe[issue + 1 :] - baseline[issue + 1 :]
        if target.shape != np.asarray(item["response"]).shape or not np.array_equal(target, item["response"]):
            raise ValueError("R8R2 independent matched response reconstruction changed")
        response_exact += 1
        descriptor_equal += int(np.array_equal(descriptor, np.asarray(item["descriptor"])))
        item.update(
            {
                "descriptor": descriptor,
                "response": target,
                "probe_visible": probe,
                "baseline_visible": baseline,
            }
        )
        records.append(item)
        key = (context, issue)
        if key in windows and not np.array_equal(windows[key]["baseline_visible"], baseline):
            raise ValueError("R8R2 independent baseline changed within context")
        windows.setdefault(
            key,
            {
                "context_id": context,
                "pair_id": str(item["pair_id"]),
                "history_member": str(item["history_member"]),
                "issue_task_step": issue,
                "baseline_visible": baseline,
            },
        )
    records.sort(key=lambda row: str(row["response_id"]))
    window_rows = [windows[key] for key in sorted(windows)]
    bank = cfg["bank_contract"]
    pairs = sorted({str(row["pair_id"]) for row in records})
    contexts = sorted({str(row["context_id"]) for row in records})
    if (
        len(records) != int(bank["response_count"])
        or len(pairs) != int(bank["pair_count"])
        or len(contexts) != int(bank["context_count"])
        or len(window_rows) != int(bank["baseline_window_count"])
    ):
        raise ValueError("R8R2 independent record coverage changed")
    signature = {
        "response_count": len(records),
        "pair_count": len(pairs),
        "context_count": len(contexts),
        "baseline_window_count": len(window_rows),
        "raw_matched_response_exact_count": response_exact,
        "probe_descriptor_equal_to_prior_baseline_descriptor_count": descriptor_equal,
        "probe_descriptor_reconstructed_from_probe_count": len(records),
        "matched_baseline_used_as_predictor_input_count": 0,
        "future_probe_state_used_as_predictor_input_count": 0,
    }
    return records, window_rows, signature


def _forecast(visible: np.ndarray, issue: int, cfg: Mapping[str, Any]) -> np.ndarray:
    offsets = np.asarray([-3.0, -2.0, -1.0, 0.0])
    samples = np.asarray(visible, dtype=float)[issue - 3 : issue + 1, 2:5]
    coefficients = np.column_stack(
        [np.polyfit(offsets, samples[:, component], 1) for component in range(3)]
    )
    future = np.arange(1.0, 13.0)
    output = np.zeros((12, 5))
    output[:, 2:5] = np.column_stack((future, np.ones(12))) @ coefficients
    scales = np.asarray(cfg["bank_contract"]["response_scales"], dtype=float)
    dt = float(cfg["bank_contract"]["dt_s"])
    output[:, 0] = visible[issue, 0] + np.cumsum(output[:, 2]) * dt * scales[2] / scales[0]
    output[:, 1] = visible[issue, 1] + np.cumsum(output[:, 3]) * dt * scales[3] / scales[1]
    if not np.all(np.isfinite(output)):
        raise ValueError("R8R2 independent baseline forecast non-finite")
    return output


def _baseline(windows: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> dict[str, Any]:
    caps = np.asarray(cfg["gates"]["baseline_component_caps_physical"], dtype=float)
    scales = np.asarray(cfg["bank_contract"]["response_scales"], dtype=float)
    rows = []
    for window in windows:
        issue = int(window["issue_task_step"])
        visible = np.asarray(window["baseline_visible"], dtype=float)
        forecast = _forecast(visible, issue, cfg)
        actual = visible[issue + 1 : issue + 13]
        error = np.max(np.abs(forecast - actual), axis=0) * scales
        rows.append(
            {
                "context_id": str(window["context_id"]),
                "pair_id": str(window["pair_id"]),
                "history_member": str(window["history_member"]),
                "issue_task_step": issue,
                "componentwise_maximum_absolute_error_physical": error.tolist(),
                "maximum_scaled_point_error": float(np.max(error / caps)),
                "passed": bool(np.all(np.isfinite(actual)) and np.all(error <= caps + 1e-15)),
            }
        )
    return {
        "window_count": len(rows),
        "pass_count": sum(row["passed"] for row in rows),
        "componentwise_maximum_absolute_error_physical": np.max(
            np.asarray([row["componentwise_maximum_absolute_error_physical"] for row in rows]), axis=0
        ).tolist(),
        "maximum_scaled_point_error": max(row["maximum_scaled_point_error"] for row in rows),
        "rows": rows,
        "passed": bool(len(rows) == 96 and all(row["passed"] for row in rows)),
    }


def _adapt(
    item: Mapping[str, Any], base: np.ndarray, update: int, recency: float,
    cfg: Mapping[str, Any],
) -> np.ndarray:
    probe = np.asarray(item["probe_visible"], dtype=float)
    issue = int(item["issue_task_step"])
    baseline = _forecast(probe, issue, cfg)
    observed = probe[issue + 1 : issue + update + 1] - baseline[:update]
    innovations = observed[:, 2:5] - base[:update, 2:5]
    if recency == 0.0:
        correction = innovations[-1]
    else:
        weights = recency ** np.arange(update - 1, -1, -1, dtype=float)
        correction = np.average(innovations, axis=0, weights=weights)
    output = np.asarray(base[update : update + 8], dtype=float).copy()
    output[:, 2:5] += correction
    scales = np.asarray(cfg["bank_contract"]["response_scales"], dtype=float)
    dt = float(cfg["bank_contract"]["dt_s"])
    output[:, 0] = observed[-1, 0] + np.cumsum(output[:, 2]) * dt * scales[2] / scales[0]
    output[:, 1] = observed[-1, 1] + np.cumsum(output[:, 3]) * dt * scales[3] / scales[1]
    return output


def _row(item: Mapping[str, Any], prediction: np.ndarray, update: int, cfg: Mapping[str, Any]) -> dict[str, Any]:
    scored = dict(item)
    target = np.asarray(item["response"], dtype=float)[update : update + 8]
    scored["response"] = target
    row = kernel._metric(scored, prediction, cfg)
    row.update(
        {
            "source_stage": str(item["source_stage"]),
            "action_scale": float(item["action_scale"]),
            "geometry_roles": list(item["geometry_roles"]),
            "update_relative_lag": update,
            "actual_response": target.tolist(),
        }
    )
    return row


def _hard(row: Mapping[str, Any], cfg: Mapping[str, Any]) -> bool:
    gates = cfg["gates"]
    return bool(
        row["criteria"]["finite"]
        and row["maximum_absolute_scaled_point_error"] <= gates["maximum_absolute_scaled_point_error"] + 1e-15
        and row["response_cosine"] >= gates["hard_minimum_response_cosine"] - 1e-15
        and gates["hard_minimum_peak_ratio"] - 1e-15 <= row["peak_ratio"] <= gates["hard_maximum_peak_ratio"] + 1e-15
        and row["actual_peak"] >= gates["minimum_actual_peak"] - 1e-15
        and row["predicted_peak"] >= gates["minimum_predicted_peak"] - 1e-15
    )


def _geometry(rows: Sequence[Mapping[str, Any]], field: str, cfg: Mapping[str, Any]) -> dict[str, Any]:
    proxy = []
    for row in rows:
        value = dict(row)
        value["predicted_response"] = row[field]
        proxy.append(value)
    result = r8_independent._geometry(proxy, cfg)
    result["field"] = field
    for family in ("canonical", "operational"):
        result[family]["field"] = field
        result[family]["minimum_peak"] = min(
            float(np.max(np.abs(np.asarray(row[field], dtype=float))))
            for row in proxy if family in row["geometry_roles"]
        )
        result[family]["failed_branch_count"] = sum(
            not bool(branch["passed"]) for branch in result[family]["rows"]
        )
    return result


def _selection_score(rows: Sequence[Mapping[str, Any]], recency: float, cfg: Mapping[str, Any]) -> tuple[Any, ...]:
    aggregate = r8_independent._aggregate(rows, cfg)
    predicted, actual = _geometry(rows, "predicted_response", cfg), _geometry(rows, "actual_response", cfg)
    hard = (
        sum(not _hard(row, cfg) for row in rows)
        + int(not aggregate["tube_cap_pass"])
        + sum(predicted[family]["failed_branch_count"] + actual[family]["failed_branch_count"] for family in ("canonical", "operational"))
    )
    relative = np.asarray([row["relative_l2_error"] for row in rows])
    return (
        hard,
        sum(not row["passed"] for row in rows),
        max(row["maximum_absolute_scaled_point_error"] for row in rows),
        float(np.quantile(relative, 0.95, method="linear")),
        recency,
    )


def _nested(
    items: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any], model_cfg: Mapping[str, Any]
) -> tuple[dict[int, list[dict[str, Any]]], dict[int, list[dict[str, Any]]], list[dict[str, Any]]]:
    updates, recencies = (2, 4), (0.0, 0.5, 0.8)
    candidate = (4, 2.0, 0.1)
    adapted, cold = {2: [], 4: []}, {2: [], 4: []}
    folds = []
    pairs = sorted({str(row["pair_id"]) for row in items})
    for outer_pair in pairs:
        train = [row for row in items if str(row["pair_id"]) != outer_pair]
        held = [row for row in items if str(row["pair_id"]) == outer_pair]
        inner_predictions = {}
        for inner_pair in sorted({str(row["pair_id"]) for row in train}):
            inner_train = [row for row in train if str(row["pair_id"]) != inner_pair]
            inner_held = [row for row in train if str(row["pair_id"]) == inner_pair]
            fitted = kernel._fit(inner_train, candidate, model_cfg)
            for row in inner_held:
                inner_predictions[str(row["response_id"])] = kernel._predict(fitted, row, model_cfg)
        selected, reports = {}, {}
        for update in updates:
            scored = []
            for recency in recencies:
                rows = [
                    _row(row, _adapt(row, inner_predictions[str(row["response_id"])], update, recency, cfg), update, cfg)
                    for row in train
                ]
                scored.append((recency, _selection_score(rows, recency, cfg)))
            selected[update] = min(scored, key=lambda value: value[1])[0]
            reports[update] = [
                {"recency_factor": recency, "selection_score": list(score)}
                for recency, score in scored
            ]
        fitted = kernel._fit(train, candidate, model_cfg)
        for row in held:
            base = kernel._predict(fitted, row, model_cfg)
            for update in updates:
                adapted[update].append(_row(row, _adapt(row, base, update, selected[update], cfg), update, cfg))
                cold[update].append(_row(row, base[update : update + 8], update, cfg))
        folds.append(
            {
                "held_pair_id": outer_pair,
                "training_pair_count": 11,
                "held_response_count": len(held),
                "fixed_candidate": {"pca_rank": 4, "bandwidth_multiplier": 2.0, "ridge": 0.1},
                "selected_recency_by_update": {str(key): value for key, value in selected.items()},
                "inner_scores_by_update": {str(key): value for key, value in reports.items()},
            }
        )
    for table in (adapted, cold):
        for update in updates:
            table[update].sort(key=lambda row: str(row["response_id"]))
    return adapted, cold, folds


def _evaluate(rows: Sequence[Mapping[str, Any]], cold: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> dict[str, Any]:
    aggregate, comparator = r8_independent._aggregate(rows, cfg), r8_independent._aggregate(cold, cfg)
    predicted, actual = _geometry(rows, "predicted_response", cfg), _geometry(rows, "actual_response", cfg)
    pair_counts = {pair: sum(row["passed"] for row in rows if row["pair_id"] == pair) for pair in sorted({row["pair_id"] for row in rows})}
    cold_pair = {pair: sum(row["passed"] for row in cold if row["pair_id"] == pair) for pair in pair_counts}
    context_counts = {context: sum(row["passed"] for row in rows if row["context_id"] == context) for context in sorted({row["context_id"] for row in rows})}
    improvement = aggregate["response_pass_count"] - comparator["response_pass_count"]
    hard_pass = bool(all(_hard(row, cfg) for row in rows) and aggregate["tube_cap_pass"] and predicted["passed"] and actual["passed"])
    gates = cfg["gates"]
    useful = bool(
        aggregate["response_pass_count"] >= gates["useful_required_response_pass_count"]
        and all(value >= gates["useful_required_pair_pass_count"] for value in pair_counts.values())
        and all(value >= gates["useful_required_context_pass_count"] for value in context_counts.values())
        and improvement >= gates["useful_required_improvement_count"]
        and all(pair_counts[key] >= cold_pair[key] for key in pair_counts)
    )
    return {
        "update_relative_lag": int(rows[0]["update_relative_lag"]),
        "elapsed_warmup_ms": 10 * int(rows[0]["update_relative_lag"]),
        "future_horizon_ms": 80,
        "aggregate": aggregate,
        "cold_comparator_aggregate": comparator,
        "response_pass_improvement": improvement,
        "pair_pass_counts": pair_counts,
        "cold_pair_pass_counts": cold_pair,
        "context_pass_counts": context_counts,
        "hard_row_pass_count": sum(_hard(row, cfg) for row in rows),
        "predicted_geometry": predicted,
        "actual_geometry": actual,
        "hard_envelope_passed": hard_pass,
        "useful_performance_passed": useful,
        "passed": bool(hard_pass and useful),
        "rows": list(rows),
        "cold_rows": list(cold),
    }


def _compact_geometry(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "field": value["field"],
        "passed": value["passed"],
        "canonical": {key: item for key, item in value["canonical"].items() if key != "rows"},
        "operational": {key: item for key, item in value["operational"].items() if key != "rows"},
    }


def _compact_update(value: Mapping[str, Any]) -> dict[str, Any]:
    output = {key: item for key, item in value.items() if key not in {"rows", "cold_rows", "predicted_geometry", "actual_geometry"}}
    output["predicted_geometry"] = _compact_geometry(value["predicted_geometry"])
    output["actual_geometry"] = _compact_geometry(value["actual_geometry"])
    return output


def _agrees(left: Any, right: Any, cfg: Mapping[str, Any]) -> bool:
    if isinstance(left, (int, float)) and not isinstance(left, bool) and isinstance(right, (int, float)) and not isinstance(right, bool):
        return bool(
            np.isclose(
                float(left), float(right),
                rtol=float(cfg["gates"]["independent_relative_tolerance"]),
                atol=float(cfg["gates"]["independent_absolute_tolerance"]),
            )
        )
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        return set(left) == set(right) and all(_agrees(left[key], right[key], cfg) for key in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(_agrees(a, b, cfg) for a, b in zip(left, right))
    return type(left) is type(right) and left == right


def run(args: argparse.Namespace) -> dict[str, Any]:
    cfg = _json(args.config.resolve())
    contract.validate_config(cfg)
    output = args.output_dir.resolve()
    primary = _json(output / "primary_detailed.json")
    primary_summary = _json(output / "primary_summary.json")
    state_path = output / "stage_state.json"
    state = _json(state_path)
    if state.get("primary_completed") is not True or state.get("independent_completed") is True:
        raise ValueError("R8R2 independent state boundary changed")
    root = Path(__file__).resolve().parents[3]
    design = (root / cfg["design_document"]).resolve()
    source_r8r1_config_path = (root / cfg["source_r8r1_config"]).resolve()
    if _sha(design) != cfg["design_document_sha256"] or _sha(source_r8r1_config_path) != cfg["source_r8r1_config_sha256"]:
        raise ValueError("R8R2 independent design or source-config hash changed")
    r8r1_source = _r8r1_source(args.r8r1_output.resolve(), cfg)
    source_r8r1_cfg = _json(source_r8r1_config_path)
    authenticated_items, authenticated_r8_cfg = r8r1_independent._authenticate(
        args, source_r8r1_cfg
    )
    r8_cfg = _json((root / source_r8r1_cfg["source_r8_config"]).resolve())
    if len(authenticated_items) != 912 or authenticated_r8_cfg != r8_cfg:
        raise ValueError("R8R2 independent R8 source authentication changed")
    r8_paths = r8_independent._paths(args.r8_run.resolve())
    records, windows, signature = _source_records(cfg, r8_cfg, r8_paths, args)
    baseline = _baseline(windows, cfg)
    updates, folds = {}, []
    if baseline["passed"]:
        model_cfg = copy.deepcopy(r8_cfg)
        model_cfg["gates"].update(copy.deepcopy(cfg["gates"]))
        model_cfg["gates"]["required_signal_pass_count"] = 912
        adapted, cold, folds = _nested(records, cfg, model_cfg)
        updates = {update: _evaluate(adapted[update], cold[update], cfg) for update in (2, 4)}
    selected = next((update for update in (2, 4) if updates[update]["passed"]), None) if updates else None
    route = contract.route_for(bool(baseline["passed"]), selected, cfg)
    compact_baseline = {key: value for key, value in baseline.items() if key != "rows"}
    compact_updates = {str(key): _compact_update(value) for key, value in updates.items()}
    numerical = bool(
        _agrees(primary["record_signature"], signature, cfg)
        and _agrees(primary_summary["baseline_forecast"], compact_baseline, cfg)
        and _agrees(primary_summary["updates"], compact_updates, cfg)
        and _agrees(primary["outer_folds"], folds, cfg)
    )
    outcome = bool(
        primary.get("selected_update_relative_lag") == selected
        and primary_summary.get("selected_update_relative_lag") == selected
        and primary.get("route") == route
        and primary_summary.get("route") == route
        and bool(primary.get("scientific_gate_passed")) == (selected is not None)
    )
    result = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "audit_kind": "independent",
        "record_signature": signature,
        "source_r8r1_authentication": r8r1_source,
        "baseline_forecast": compact_baseline,
        "updates": compact_updates,
        "outer_fold_count": len(folds),
        "selected_update_relative_lag": selected,
        "route": route,
        "scientific_gate_passed": selected is not None,
        "primary_numerical_agreement": numerical,
        "primary_outcome_agreement": outcome,
        "development_artifact_presence_agreement": not (output / "causal_online_innovation_artifact.json").exists() and primary.get("development_artifact_sha256") == "",
        "new_raw_count": 0,
        "ray_executed": False,
        "gotsc_executed": False,
        "tsc_executed": False,
        "controller_executed": False,
        "plant_advance_count": 0,
        "passed": bool(numerical and outcome),
    }
    if not result["passed"]:
        raise ValueError("R8R2 independent recomputation disagrees with primary")
    independent_path = output / "independent.json"
    _write(independent_path, result)
    state.update(
        {
            "independent_completed": True,
            "independent_passed": True,
            "independent_sha256": _sha(independent_path),
        }
    )
    _write(state_path, state)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--r8r1-output", type=Path, required=True)
    parser.add_argument("--r8-run", type=Path, required=True)
    parser.add_argument("--source-r2-run", type=Path, required=True)
    parser.add_argument("--source-r4-run", type=Path, required=True)
    parser.add_argument("--source-r6-run", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


if __name__ == "__main__":
    run(_parser().parse_args())
