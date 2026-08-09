#!/usr/bin/env python3
"""Independent immutable-source recomputation for the R8R51R2 preflight."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import numbers
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


STAGE = "Stage4.2R3c3T13S24D1R14R8R51R2"
R51_RAW_ROUTE = "REDUCED_Q0_TRANSPORT_BRIDGE_Q0_GATE_INTEGRATION_EXECUTION_FAIL_STOP"
N_COILS = 14


def validate_config(cfg: Mapping[str, Any], project: Path) -> None:
    design = project / str(cfg.get("design_document", ""))
    feature = cfg.get("feature_contract", {})
    model = cfg.get("model_contract", {})
    scope = cfg.get("scientific_scope", {})
    if (
        cfg.get("stage") != STAGE
        or cfg.get("identity")
        != "reduced_q0_transport_bridge_whole_pair_causal_model_preflight_v1"
        or feature.get("feature_dimension") != 44
        or feature.get("expanded_dimension") != 180
        or feature.get("history_state_steps") != [9, 10, 11, 12]
        or feature.get("previous_current_state_step") != 10
        or feature.get("candidate_first_effect_state_step") != 13
        or feature.get("candidate_second_effect_state_step") != 14
        or feature.get("q_scale") != 1.5
        or model.get("physical_pair_count") != 8
        or model.get("row_count") != 208
        or model.get("outer_training_row_count") != 182
        or model.get("outer_holdout_row_count") != 26
        or model.get("nested_training_row_count") != 156
        or model.get("nested_holdout_row_count") != 26
        or model.get("ridge_penalty") != 0.0001
        or model.get("tube_reserve_multiplier") != 1.25
        or model.get("point_error_floors")
        != [0.015, 0.015, 3000.0, 0.015, 0.015, 3000.0]
        or model.get("tube_half_width_caps")
        != [0.025, 0.025, 5000.0, 0.025, 0.025, 5000.0]
        or model.get("comparison_absolute_tolerance") != 1e-12
        or model.get("intercept_allowed") is not False
        or model.get("feature_only_term_allowed") is not False
        or model.get("hyperparameter_selection_count") != 0
        or scope.get("zero_new_tsc") is not True
        or scope.get("maximum_new_tsc_trajectories") != 0
        or scope.get("controller_execution_allowed") is not False
        or scope.get("model_selection_allowed") is not False
        or scope.get("gate_a_qualified") is not False
        or scope.get("all_source_trajectories_allowed_in_expert_dataset") is not False
        or not design.is_file()
        or _sha(design) != cfg.get("design_document_sha256")
    ):
        raise ValueError("independent R8R51R2 frozen design changed")


def _reject_constant(value: str) -> Any:
    raise ValueError(f"non-finite JSON constant: {value}")


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=_reject_constant)


def _load_gzip(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(stream, parse_constant=_reject_constant)


def _save(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _json_digest(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _raw_inventory(directory: Path) -> dict[str, Any]:
    rows = []
    aggregate = hashlib.sha256()
    for path in sorted(directory.glob("*.json.gz"), key=lambda item: item.name):
        size = path.stat().st_size
        sha = _sha(path)
        aggregate.update(f"{path.name}\0{size}\0{sha}\n".encode("utf-8"))
        rows.append({"name": path.name, "size": size, "sha256": sha})
    return {
        "count": len(rows),
        "bytes": sum(row["size"] for row in rows),
        "digest": aggregate.hexdigest(),
        "rows": rows,
    }


def _source_files(r51: Path, r7: Path) -> dict[str, Path]:
    return {
        "r51_raw_primary": r51 / "analysis/raw_primary.json",
        "r51_raw_independent": r51 / "analysis/raw_independent.json",
        "r51_hotfix_primary": r51
        / "analysis/q0_first_effect_reporting_hotfix_primary.json",
        "r51_hotfix_independent": r51
        / "analysis/q0_first_effect_reporting_hotfix_independent.json",
        "r51_compact": r51
        / "analysis/q0_first_effect_reporting_hotfix_compact_audit.json",
        "r51_final": r51
        / "analysis/q0_first_effect_reporting_hotfix_final_report.json",
        "r51_state": r51 / "stage_state.json",
        "r51_manifest": r51 / "stage_manifest.json",
        "r51_specs": r51 / "specs/all_specs.json",
        "r51_offline": r51 / "analysis/offline_construction.json",
        "r7_all_specs": r7 / "specs/all_specs.json",
        "r7_baseline_specs": r7 / "specs/baseline_specs.json",
        "r7_final": r7 / "analysis/final_report.json",
        "r7_manifest": r7 / "stage_manifest.json",
        "r7_state": r7 / "stage_state.json",
    }


def authenticate(
    cfg: Mapping[str, Any], r51_run: Path, r7_run: Path, project: Path
) -> dict[str, Any]:
    c51 = cfg["source_r51r1"]
    c7 = cfg["source_r8r7"]
    r51 = r51_run.resolve() / c51["stage_directory"]
    r7 = r7_run.resolve() / c7["stage_directory"]
    if r51.parent.name != c51["run_name"] or r7.parent.name != c7["run_name"]:
        raise ValueError("independent R8R51R2 source run identity changed")
    paths = _source_files(r51, r7)
    expected = {
        "r51_raw_primary": c51["raw_primary_sha256"],
        "r51_raw_independent": c51["raw_independent_sha256"],
        "r51_hotfix_primary": c51["hotfix_primary_sha256"],
        "r51_hotfix_independent": c51["hotfix_independent_sha256"],
        "r51_compact": c51["compact_audit_sha256"],
        "r51_final": c51["final_report_sha256"],
        "r51_state": c51["stage_state_sha256"],
        "r51_manifest": c51["stage_manifest_sha256"],
        "r51_specs": c51["all_specs_sha256"],
        "r51_offline": c51["offline_construction_sha256"],
        "r7_all_specs": c7["all_specs_sha256"],
        "r7_baseline_specs": c7["baseline_specs_sha256"],
        "r7_final": c7["final_report_sha256"],
        "r7_manifest": c7["stage_manifest_sha256"],
        "r7_state": c7["stage_state_sha256"],
    }
    for name in sorted(expected):
        if not paths[name].is_file() or _sha(paths[name]) != expected[name]:
            raise ValueError(f"independent R8R51R2 source artifact changed: {name}")
    source_code = {
        "config": project
        / "configs/stage4_2r3c3t13s24d1r14r8r51r1_reduced_q0_transport_bridge_q0_gate_integration_sentinel_370ms.json",
        "implementation": project
        / "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r8r51r1_reduced_q0_transport_bridge_q0_gate_integration_sentinel.py",
    }
    if (
        _sha(source_code["config"]) != c51["config_sha256"]
        or _sha(source_code["implementation"]) != c51["implementation_sha256"]
    ):
        raise ValueError("independent R8R51R2 R51R1 source code changed")
    r51_inventory = _raw_inventory(r51 / "raw")
    r7_inventory = _raw_inventory(r7 / "raw/baseline")
    if (
        r51_inventory["count"] != c51["raw_count"]
        or r51_inventory["bytes"] != c51["raw_bytes"]
        or r51_inventory["digest"] != c51["raw_inventory_digest"]
        or r7_inventory["count"] != c7["baseline_raw_count"]
        or r7_inventory["bytes"] != c7["baseline_raw_bytes"]
        or r7_inventory["digest"] != c7["baseline_raw_digest"]
    ):
        raise ValueError("independent R8R51R2 source raw inventory changed")
    primary = _load(paths["r51_raw_primary"])
    old_independent = _load(paths["r51_raw_independent"])
    hotfix = _load(paths["r51_hotfix_primary"])
    hotfix_independent = _load(paths["r51_hotfix_independent"])
    final = _load(paths["r51_final"])
    state = _load(paths["r51_state"])
    manifest = _load(paths["r51_manifest"])
    r7_final = _load(paths["r7_final"])
    r7_state = _load(paths["r7_state"])
    strict_boolean_fields = (
        "runtime_success",
        "full_horizon",
        "authentic_restart",
        "source_prefix_state_exact",
        "source_prefix_trace_exact",
        "source_trace_difference_wrapper_only",
        "calibration_exact",
        "q0_exact",
        "q0_offline_parity",
        "within_context_q0_prefix_exact",
        "candidate_exact",
        "event_sequence_exact",
        "event_gates_passed",
        "first_effect_at_issue_plus_one",
        "finite_response",
        "return_exact",
        "finite",
    )
    if (
        primary.get("route") != R51_RAW_ROUTE
        or len(primary.get("rows", [])) != 208
        or old_independent.get("primary_agreement") is not True
        or hotfix.get("passed") is not True
        or hotfix_independent.get("passed") is not True
        or hotfix_independent.get("primary_agreement") is not True
        or final.get("passed") is not True
        or final.get("primary_independent_agreement") is not True
        or final.get("route") != c51["required_route"]
        or final.get("raw_inventory") != r51_inventory
        or final.get("prefix_digest") != c51["prefix_digest"]
        or final.get("response_digest") != c51["response_digest"]
        or int(final.get("corrected_numerical_equivalence_count", -1)) != 208
        or state.get("route") != R51_RAW_ROUTE
        or state.get("real_tsc_executed") is not True
        or int(state.get("new_raw_count", -1)) != 208
        or manifest.get("spec_digest") != c51["spec_digest"]
        or int(manifest.get("spec_count", -1)) != 208
        or r7_final.get("route") != c7["required_route"]
        or r7_final.get("passed") is not True
        or r7_state.get("finished") is not True
    ):
        raise ValueError("independent R8R51R2 source scientific contract changed")
    rows_by_id = {str(row["experiment_id"]): row for row in primary["rows"]}
    if len(rows_by_id) != 208 or any(
        not all(row.get(field) is True for field in strict_boolean_fields)
        or int(row.get("forbidden_trace_count", -1)) != 0
        for row in rows_by_id.values()
    ):
        raise ValueError("independent R8R51R2 strict source rows changed")
    specs = _load(paths["r51_specs"])
    if _json_digest(specs) != c51["spec_digest"]:
        raise ValueError("independent R8R51R2 spec digest changed")
    return {
        "r51": r51,
        "r7": r7,
        "specs": specs,
        "old_rows": rows_by_id,
        "r51_inventory": r51_inventory,
        "r7_inventory": r7_inventory,
    }


def make_feature(trajectory: Sequence[Mapping[str, Any]], scales: np.ndarray) -> np.ndarray:
    visible = []
    for step in (9, 10, 11, 12):
        visible.extend(float(trajectory[step][name]) for name in ("R", "Z", "Ip"))
    current = np.asarray(trajectory[12]["currents_a_tsc"], dtype=float)
    previous = np.asarray(trajectory[10]["currents_a_tsc"], dtype=float)
    value = np.asarray(
        visible
        + list(current / scales)
        + list((current - previous) / scales)
        + [0.0, 0.0, 0.0, 0.0],
        dtype=float,
    )
    if value.shape != (44,) or not np.all(np.isfinite(value)):
        raise ValueError("independent R8R51R2 invalid causal feature")
    return value


def build_rows(cfg: Mapping[str, Any], source: Mapping[str, Any]) -> dict[str, Any]:
    baselines: dict[str, dict[str, Any]] = {}
    rows = []
    prefix_exact = 0
    out_scale = np.asarray(cfg["model_contract"]["output_scales"], dtype=float)
    for spec in source["specs"]:
        row_id = str(spec["experiment_id"])
        result = _load_gzip(source["r51"] / "raw" / f"{row_id}.json.gz")
        baseline_id = str(spec["source_r8r7_baseline_experiment_id"])
        if baseline_id not in baselines:
            baselines[baseline_id] = _load_gzip(
                source["r7"] / "raw/baseline" / f"{baseline_id}.json.gz"
            )
        baseline = baselines[baseline_id]
        trajectory = result.get("trajectory") or []
        reference = baseline.get("trajectory") or []
        if (
            result.get("success") is not True
            or result.get("spec") != spec
            or len(trajectory) != int(spec["horizon_steps"]) + 1
            or baseline.get("success") is not True
            or len(reference) != int(spec["horizon_steps"]) + 1
            or str(baseline.get("experiment_id")) != baseline_id
        ):
            raise ValueError(f"independent R8R51R2 raw contract changed: {row_id}")
        exact = True
        for step in (9, 10, 11, 12):
            for name in ("R", "Z", "Ip"):
                exact = exact and trajectory[step][name] == reference[step][name]
            exact = exact and (
                trajectory[step]["currents_a_tsc"]
                == reference[step]["currents_a_tsc"]
            )
        prefix_exact += int(exact)
        if not exact:
            raise ValueError(f"independent R8R51R2 physical prefix changed: {row_id}")
        payload = _load(source["r51"] / "variants" / f"payload_{row_id}.json")
        lower = np.asarray(payload["min_current_tsc"], dtype=float).reshape(N_COILS)
        upper = np.asarray(payload["max_current_tsc"], dtype=float).reshape(N_COILS)
        scales = np.maximum(np.abs(lower), np.abs(upper))
        if np.any(scales <= 0.0) or not np.all(np.isfinite(scales)):
            raise ValueError(f"independent R8R51R2 current scale changed: {row_id}")
        q = np.asarray(spec["r8r51r1_candidate_q"], dtype=float).reshape(4)
        response = []
        for step in (13, 14):
            response.extend(
                float(trajectory[step][name]) - float(reference[step][name])
                for name in ("R", "Z", "Ip")
            )
        response_array = np.asarray(response, dtype=float)
        rows.append(
            {
                "row_id": row_id,
                "pair_id": str(spec["pair_id"]),
                "history_member": str(spec["history_member"]),
                "candidate_index": int(spec["r8r51r1_candidate_index"]),
                "candidate_id": str(spec["r8r51r1_candidate_id"]),
                "feature": make_feature(trajectory, scales),
                "q": q,
                "response": response_array,
                "normalized_response": response_array / out_scale,
                "current_scales": scales,
                "source_baseline_id": baseline_id,
            }
        )
    rows.sort(key=lambda row: row["row_id"])
    pairs = sorted({row["pair_id"] for row in rows})
    contexts = {(row["pair_id"], row["history_member"]) for row in rows}
    expected_candidates = sorted(cfg["source_r51r1"]["candidate_ids"])
    if (
        len(rows) != 208
        or len(pairs) != 8
        or len(contexts) != 16
        or len(baselines) != 16
        or prefix_exact != 208
        or any(sum(row["pair_id"] == pair for row in rows) != 26 for pair in pairs)
        or any(
            sorted(
                row["candidate_id"]
                for row in rows
                if row["pair_id"] == pair and row["history_member"] == history
            )
            != expected_candidates
            for pair, history in contexts
        )
    ):
        raise ValueError("independent R8R51R2 bank coverage changed")
    serial = [
        {
            "row_id": row["row_id"],
            "pair_id": row["pair_id"],
            "history_member": row["history_member"],
            "candidate_index": row["candidate_index"],
            "candidate_id": row["candidate_id"],
            "feature": row["feature"].tolist(),
            "q": row["q"].tolist(),
            "response": row["response"].tolist(),
            "current_scales": row["current_scales"].tolist(),
            "source_baseline_id": row["source_baseline_id"],
        }
        for row in rows
    ]
    return {
        "rows": rows,
        "pairs": pairs,
        "serial": serial,
        "bank_digest": _json_digest(serial),
        "feature_digest": _json_digest([row["feature"] for row in serial]),
        "response_digest": _json_digest([row["response"] for row in serial]),
        "physical_prefix_exact_count": prefix_exact,
    }


def expand(feature: np.ndarray, q: np.ndarray, mean: np.ndarray, scale: np.ndarray) -> np.ndarray:
    q_scaled = q / 1.5
    whitened = (feature - mean) / scale
    values = list(q_scaled)
    for feature_value in whitened:
        for q_value in q_scaled:
            values.append(feature_value * q_value)
    result = np.asarray(values, dtype=float)
    if result.shape != (180,) or not np.all(np.isfinite(result)):
        raise ValueError("independent R8R51R2 invalid expanded feature")
    return result


def fit(rows: Sequence[Mapping[str, Any]], pairs: Sequence[str], ridge: float) -> dict[str, Any]:
    allowed = set(pairs)
    chosen = [row for row in rows if row["pair_id"] in allowed]
    feature_matrix = np.asarray([row["feature"] for row in chosen], dtype=float)
    mean = feature_matrix.sum(axis=0) / len(chosen)
    raw_scale = np.sqrt(np.mean((feature_matrix - mean) ** 2, axis=0))
    scale = raw_scale.copy()
    scale[raw_scale < 1e-12] = 1.0
    design = np.vstack(
        [expand(row["feature"], row["q"], mean, scale) for row in chosen]
    )
    targets = np.vstack([row["normalized_response"] for row in chosen])
    coefficients = np.linalg.solve(
        design.T.dot(design) + ridge * np.identity(180), design.T.dot(targets)
    )
    return {
        "training_pairs": sorted(allowed),
        "training_row_count": len(chosen),
        "mean": mean,
        "scale": scale,
        "coefficients": coefficients,
    }


def predict(model: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]) -> np.ndarray:
    design = np.vstack(
        [
            expand(row["feature"], row["q"], model["mean"], model["scale"])
            for row in rows
        ]
    )
    return design.dot(model["coefficients"])


def _serial_model(model: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "training_pairs": list(model["training_pairs"]),
        "training_row_count": int(model["training_row_count"]),
        "mean": np.asarray(model["mean"]).tolist(),
        "scale": np.asarray(model["scale"]).tolist(),
        "coefficients": np.asarray(model["coefficients"]).tolist(),
    }


def recompute(cfg: Mapping[str, Any], bank: Mapping[str, Any]) -> dict[str, Any]:
    contract = cfg["model_contract"]
    rows = bank["rows"]
    pairs = bank["pairs"]
    ridge = float(contract["ridge_penalty"])
    reserve = float(contract["tube_reserve_multiplier"])
    output_scale = np.asarray(contract["output_scales"], dtype=float)
    floors = np.asarray(contract["point_error_floors"], dtype=float)
    caps = np.asarray(contract["tube_half_width_caps"], dtype=float)
    tolerance = float(contract["comparison_absolute_tolerance"])
    folds = []
    point_total = containment_total = coverage = tube_total = 0
    max_error = np.zeros(6)
    max_tube = np.zeros(6)
    for outer_held in pairs:
        training_pairs = [pair for pair in pairs if pair != outer_held]
        nested_max = np.zeros(6)
        nested_rows_serial = []
        for nested_held in training_pairs:
            inner_pairs = [pair for pair in training_pairs if pair != nested_held]
            inner_model = fit(rows, inner_pairs, ridge)
            validation = [row for row in rows if row["pair_id"] == nested_held]
            residual = np.abs(
                predict(inner_model, validation)
                - np.vstack([row["normalized_response"] for row in validation])
            ) * output_scale
            inner_max = np.max(residual, axis=0)
            nested_max = np.maximum(nested_max, inner_max)
            model_serial = _serial_model(inner_model)
            nested_rows_serial.append(
                {
                    "held_pair": nested_held,
                    "model": model_serial,
                    "model_digest": _json_digest(model_serial),
                    "maximum_absolute_physical_residual": inner_max.tolist(),
                }
            )
        tube = np.maximum(floors, reserve * nested_max)
        tube_pass = bool(np.all(tube <= caps + tolerance))
        tube_total += int(tube_pass)
        max_tube = np.maximum(max_tube, tube)
        outer_model = fit(rows, training_pairs, ridge)
        held_rows = [row for row in rows if row["pair_id"] == outer_held]
        predictions = predict(outer_model, held_rows)
        actual = np.vstack([row["normalized_response"] for row in held_rows])
        error = np.abs(predictions - actual) * output_scale
        point = np.all(error <= floors + tolerance, axis=1)
        contained = np.all(error <= tube + tolerance, axis=1)
        coverage += len(held_rows)
        point_total += int(np.count_nonzero(point))
        containment_total += int(np.count_nonzero(contained))
        max_error = np.maximum(max_error, np.max(error, axis=0))
        model_serial = _serial_model(outer_model)
        prediction_rows = []
        for index, row in enumerate(held_rows):
            prediction_rows.append(
                {
                    "row_id": row["row_id"],
                    "actual_response": row["response"].tolist(),
                    "predicted_response": (predictions[index] * output_scale).tolist(),
                    "absolute_physical_error": error[index].tolist(),
                    "point_error_passed": bool(point[index]),
                    "tube_contained": bool(contained[index]),
                }
            )
        folds.append(
            {
                "held_pair": outer_held,
                "training_pairs": training_pairs,
                "outer_model": model_serial,
                "outer_model_digest": _json_digest(model_serial),
                "nested_models": nested_rows_serial,
                "nested_maximum_absolute_physical_residual": nested_max.tolist(),
                "tube_half_width": tube.tolist(),
                "tube_cap_passed": tube_pass,
                "point_error_pass_count": int(np.count_nonzero(point)),
                "containment_pass_count": int(np.count_nonzero(contained)),
                "prediction_rows": prediction_rows,
                "prediction_digest": _json_digest(prediction_rows),
            }
        )
    passed = bool(
        coverage == 208
        and point_total == 208
        and containment_total == 208
        and tube_total == 8
    )
    route = cfg["routes"]["pass" if passed else "model_insufficient"]
    return {
        "folds": folds,
        "outer_fold_count": len(folds),
        "prediction_coverage_count": coverage,
        "point_error_pass_count": point_total,
        "containment_pass_count": containment_total,
        "tube_cap_fold_pass_count": tube_total,
        "maximum_absolute_physical_error": max_error.tolist(),
        "maximum_tube_half_width": max_tube.tolist(),
        "fold_digest": _json_digest(
            [
                {
                    "held_pair": fold["held_pair"],
                    "outer_model_digest": fold["outer_model_digest"],
                    "nested_model_digests": [
                        row["model_digest"] for row in fold["nested_models"]
                    ],
                    "tube_half_width": fold["tube_half_width"],
                    "prediction_digest": fold["prediction_digest"],
                }
                for fold in folds
            ]
        ),
        "route": route,
        "scientific_gate_passed": passed,
    }


def compare(left: Any, right: Any, path: str = "root") -> tuple[bool, float, str]:
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        if set(left) != set(right):
            return False, 0.0, f"{path}: keys differ"
        maximum = 0.0
        for key in sorted(left):
            passed, difference, reason = compare(left[key], right[key], f"{path}.{key}")
            maximum = max(maximum, difference)
            if not passed:
                return False, maximum, reason
        return True, maximum, ""
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return False, 0.0, f"{path}: lengths differ"
        maximum = 0.0
        for index, (left_item, right_item) in enumerate(zip(left, right)):
            passed, difference, reason = compare(
                left_item, right_item, f"{path}[{index}]"
            )
            maximum = max(maximum, difference)
            if not passed:
                return False, maximum, reason
        return True, maximum, ""
    if (
        isinstance(left, numbers.Real)
        and isinstance(right, numbers.Real)
        and not isinstance(left, (bool, int))
        and not isinstance(right, (bool, int))
    ):
        difference = abs(float(left) - float(right))
        return bool(np.isfinite(difference)), difference, "" if np.isfinite(difference) else path
    return (left == right, 0.0, "" if left == right else f"{path}: values differ")


def run(args: argparse.Namespace) -> dict[str, Any]:
    config_path = args.config.resolve()
    cfg = _load(config_path)
    project = Path(__file__).resolve().parents[3]
    validate_config(cfg, project)
    source = authenticate(cfg, args.r51r1_run, args.r8r7_run, project)
    bank = build_rows(cfg, source)
    evaluation = recompute(cfg, bank)
    stage = args.run_dir.resolve() / cfg["run_name"]
    analysis = stage / "analysis"
    primary_path = analysis / "primary_detailed.json"
    summary_path = analysis / "primary_summary.json"
    bank_path = analysis / "bank_detailed.json"
    manifest_path = stage / "stage_manifest.json"
    state_path = stage / "stage_state.json"
    manifest = _load(manifest_path)
    state = _load(state_path)
    primary = _load(primary_path)
    primary_summary = _load(summary_path)
    bank_primary = _load(bank_path)
    if (
        manifest.get("config_sha256") != _sha(config_path)
        or manifest.get("primary_detailed_sha256") != _sha(primary_path)
        or manifest.get("primary_summary_sha256") != _sha(summary_path)
        or manifest.get("bank_detailed_sha256") != _sha(bank_path)
        or state.get("phase_status") != "primary_ready"
        or int(state.get("new_tsc_count", -1)) != 0
        or bank_primary.get("bank_digest") != bank["bank_digest"]
        or bank_primary.get("feature_digest") != bank["feature_digest"]
        or bank_primary.get("response_digest") != bank["response_digest"]
        or bank_primary.get("rows") != bank["serial"]
    ):
        raise ValueError("independent R8R51R2 primary artifact authentication failed")
    primary_view = {key: primary[key] for key in evaluation}
    discrete, numerical_difference, disagreement = compare(primary_view, evaluation)
    tolerance = float(cfg["model_contract"]["comparison_absolute_tolerance"])
    numerical = bool(numerical_difference <= tolerance)
    outcome = bool(
        primary_summary.get("route") == evaluation["route"]
        and primary_summary.get("scientific_gate_passed")
        == evaluation["scientific_gate_passed"]
        and int(primary_summary.get("point_error_pass_count", -1))
        == evaluation["point_error_pass_count"]
        and int(primary_summary.get("containment_pass_count", -1))
        == evaluation["containment_pass_count"]
        and int(primary_summary.get("tube_cap_fold_pass_count", -1))
        == evaluation["tube_cap_fold_pass_count"]
    )
    audit_passed = bool(discrete and numerical and outcome)
    result = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "independent",
        "source_authentication_passed": True,
        "strict_source_row_count": 208,
        "physical_prefix_exact_count": bank["physical_prefix_exact_count"],
        "bank_digest": bank["bank_digest"],
        "feature_digest": bank["feature_digest"],
        "response_digest": bank["response_digest"],
        "outer_fold_count": evaluation["outer_fold_count"],
        "prediction_coverage_count": evaluation["prediction_coverage_count"],
        "point_error_pass_count": evaluation["point_error_pass_count"],
        "containment_pass_count": evaluation["containment_pass_count"],
        "tube_cap_fold_pass_count": evaluation["tube_cap_fold_pass_count"],
        "maximum_absolute_physical_error": evaluation[
            "maximum_absolute_physical_error"
        ],
        "maximum_tube_half_width": evaluation["maximum_tube_half_width"],
        "fold_digest": evaluation["fold_digest"],
        "route": evaluation["route"],
        "scientific_gate_passed": evaluation["scientific_gate_passed"],
        "primary_numerical_agreement": numerical,
        "primary_discrete_agreement": discrete,
        "primary_outcome_agreement": outcome,
        "maximum_primary_numerical_difference": numerical_difference,
        "first_disagreement": disagreement,
        "comparison_absolute_tolerance": tolerance,
        "forbidden_model_input_count": 0,
        "source_or_row_exclusion_count": 0,
        "new_tsc_count": 0,
        "new_raw_count": 0,
        "snapshot_count": 0,
        "controller_execution_count": 0,
        "plant_step_count": 0,
        "model_selection_count": 0,
        "audit_passed": audit_passed,
    }
    if not audit_passed:
        raise ValueError(f"independent R8R51R2 comparison failed: {result}")
    _save(analysis / "independent.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--r51r1-run", type=Path, required=True)
    parser.add_argument("--r8r7-run", type=Path, required=True)
    result = run(parser.parse_args())
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
