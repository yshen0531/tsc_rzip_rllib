#!/usr/bin/env python3
"""Stage4.2R3c3T13S17 causal multi-drift belief preflight."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.core.coil_order import DISPLAY_TO_TSC_INDEX


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S17"
AUDIT_IDENTITY = "causal_multi_drift_belief_preflight_v1"
PACKAGE_REVISION = "r42r3c3t13s17_causal_multi_drift_belief_preflight_v1"
PASS_ROUTE = "CAUSAL_MULTI_DRIFT_BELIEF_PREFLIGHT_PASS_FRESH_WHOLE_PAIR_REQUIRED"
FAIL_ROUTE = "CAUSAL_MULTI_DRIFT_BELIEF_PREFLIGHT_FAIL_ROBUST_OBSERVER_REDESIGN"
SOURCE_STAGE = "Stage4.2R3c3T13S16"
SOURCE_CAMPAIGN_IDENTITY = "orthogonal_fixed_basis_identification_sentinel_v1"
SOURCE_CONTROLLER_REVISION = "orthogonal_fixed_basis_identification_probe_v42r3c3t13s16_v1"
SOURCE_RUN_NAME = "stage4_2r3c3t13s16_orthogonal_fixed_basis_identification"
BASELINE_PROBE_ID = "lattice_baseline"
N_COILS = 14
SOURCE_RAW_SUBDIR = Path(SOURCE_RUN_NAME) / "raw"
SOURCE_VARIANTS_SUBDIR = Path("stage4_2r3c3t13s16_environment_variants")
ARTIFACT_NAME = "causal_belief_artifact.json"
STATE_NAME = "stage4_2r3c3t13s17_state.json"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def _read_json_gz(path: Path) -> Any:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(stream)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _load_config(path: Path) -> dict[str, Any]:
    cfg = _read_json(path.expanduser().resolve())
    _validate_config(cfg)
    return cfg


def _designs(cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    history = cfg["causal_history"]
    inputs = np.asarray(history["fixed_input_codes"], dtype=float)
    t = np.linspace(-1.0, 1.0, 10)
    output = []
    for degree in map(int, cfg["hypotheses"]["legendre_drift_degrees"]):
        polynomial = np.polynomial.legendre.legvander(t, degree)
        design = np.column_stack((polynomial, inputs))
        output.append({
            "degree": degree,
            "design": design,
            "rank": int(np.linalg.matrix_rank(design)),
            "condition": float(np.linalg.cond(design)),
        })
    return output


def _validate_config(cfg: Mapping[str, Any]) -> None:
    history = cfg["causal_history"]
    hypotheses = cfg["hypotheses"]
    gates = cfg["gates"]
    execution = cfg["execution"]
    if (
        int(cfg.get("schema_version", -1)) != SCHEMA_VERSION
        or cfg.get("stage") != STAGE
        or int(cfg.get("design_revision", -1)) != 1
        or cfg.get("audit_identity") != AUDIT_IDENTITY
        or cfg.get("package_revision") != PACKAGE_REVISION
    ):
        raise ValueError("T13S17 identity changed")
    source = cfg["source"]
    if (
        source.get("stage") != SOURCE_STAGE
        or source.get("campaign_identity") != SOURCE_CAMPAIGN_IDENTITY
        or source.get("controller_revision") != SOURCE_CONTROLLER_REVISION
        or int(source.get("raw_expected", -1)) != 144
        or int(source.get("raw_total_bytes", -1)) != 8188964
        or source.get("raw_inventory_digest")
        != "b0bf9c03b94cd353b3ccb68b0de318c46285a4805acfb0c25016704f79057668"
        or len(source.get("required_file_sha256", {})) != 12
    ):
        raise ValueError("T13S17 source identity changed")
    expected_codes = np.asarray([
        [1, 0, 0, 0], [-1, 0, 0, 0],
        [0, 1, 0, 0], [0, -1, 0, 0],
        [0, 0, 1, 0], [0, 0, -1, 0],
        [0, 0, 0, 1], [0, 0, 0, -1],
        [0, 0, 0, 0], [0, 0, 0, 0],
    ], dtype=float)
    if (
        tuple(map(int, history["state_indices"])) != tuple(range(1, 11))
        or tuple(map(int, history["input_steps"])) != tuple(range(10))
        or not np.array_equal(np.asarray(history["fixed_input_codes"], dtype=float), expected_codes)
        or int(history["response_issue_step"]) != 10
        or int(history["response_first_effect_state"]) != 11
        or tuple(history["allowed_output_fields"])
        != ("R", "Z", "backward_vR", "backward_vZ", "Ip")
    ):
        raise ValueError("T13S17 causal history changed")
    if (
        tuple(map(int, hypotheses["legendre_drift_degrees"])) != (1, 2, 3)
        or float(hypotheses["maximum_design_condition"]) != 4.0
        or float(hypotheses["minimum_response_basis_cosine"]) != 0.98
        or float(hypotheses["maximum_response_off_basis_residual"]) != 0.15
        or tuple(map(float, hypotheses["response_floor"])) != (1e-9, 1e-9, 1e-7, 1e-7, 1e-4)
        or tuple(map(float, hypotheses["response_scales"])) != (0.03, 0.03, 0.1, 0.1, 2000.0)
        or tuple(map(float, hypotheses["belief_halfwidth_caps"])) != (0.003, 0.003, 0.01, 0.01, 1000.0)
        or float(hypotheses["containment_tolerance"]) != 1e-12
    ):
        raise ValueError("T13S17 hypothesis contract changed")
    if (
        int(gates["expected_snapshots"]) != 16
        or int(gates["expected_response_rows"]) != 128
        or int(gates["expected_hypothesis_rows"]) != 384
        or not bool(gates["require_belief_before_outcome"])
        or not bool(gates["require_all_hypotheses"])
        or not bool(gates["require_all_response_contained"])
        or not bool(gates["require_all_belief_caps"])
        or int(gates["maximum_forbidden_predictor_input_count"]) != 0
        or int(gates["maximum_new_tsc_or_plant_steps"]) != 0
    ):
        raise ValueError("T13S17 gate contract changed")
    if any(bool(execution[key]) for key in (
        "new_tsc_allowed", "ray_allowed", "gotsc_allowed", "controller_allowed",
        "optimizer_allowed", "probe_trajectories_allowed_in_expert_dataset",
        "bc_dagger_or_rl_allowed",
    )) or bool(cfg["formal_timing_contract"]["arrival_deadline_expansion_allowed"]):
        raise ValueError("T13S17 execution or formal contract changed")
    designs = _designs(cfg)
    expected = [(1, 6), (2, 7), (3, 8)]
    for item, (degree, rank) in zip(designs, expected):
        if (
            item["degree"] != degree or item["rank"] != rank
            or item["condition"] > float(hypotheses["maximum_design_condition"])
        ):
            raise ValueError("T13S17 fixed design is invalid")


def _source_paths(source_run: Path) -> dict[str, Path]:
    root = source_run.expanduser().resolve()
    return {
        "root": root,
        "raw": root / SOURCE_RAW_SUBDIR,
        "variants": root / SOURCE_VARIANTS_SUBDIR,
        "snapshot_audit": root / "stage4_2r3c3t13s16_source_reference" / "snapshot_audit.json",
        "state": root / "stage4_2r3c3t13s16_state.json",
        "final_model": root / "stage4_2r3c3t13s16_analysis" / "final_model_audit.json",
    }


def _raw_inventory(raw_dir: Path) -> dict[str, Any]:
    files = sorted(raw_dir.glob("*.json.gz"))
    rows = [
        {"path": path.name, "size_bytes": path.stat().st_size, "sha256": _sha256(path)}
        for path in files
    ]
    return {
        "actual": len(rows),
        "total_bytes": sum(row["size_bytes"] for row in rows),
        "digest": _digest(rows),
        "files": rows,
    }


def _authenticate_source(cfg: Mapping[str, Any], source_run: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    paths = _source_paths(source_run)
    source = cfg["source"]
    if not paths["root"].is_dir() or not paths["raw"].is_dir():
        raise ValueError("T13S17 source run or raw directory is missing")
    file_rows = []
    for relative, expected in sorted(source["required_file_sha256"].items()):
        path = paths["root"] / relative
        actual = _sha256(path) if path.is_file() else ""
        file_rows.append({"path": relative, "expected": expected, "actual": actual, "passed": actual == expected})
    if not all(row["passed"] for row in file_rows):
        raise ValueError("T13S17 source compact-file hash mismatch")
    inventory = _raw_inventory(paths["raw"])
    if (
        inventory["actual"] != int(source["raw_expected"])
        or inventory["total_bytes"] != int(source["raw_total_bytes"])
        or inventory["digest"] != source["raw_inventory_digest"]
    ):
        raise ValueError("T13S17 source raw inventory mismatch")
    state = _read_json(paths["state"])
    snapshots = _read_json(paths["snapshot_audit"])
    if (
        not bool(state.get("finished")) or not bool(state.get("real_tsc_executed"))
        or int(state.get("new_raw_count", -1)) != 144
        or state.get("package_digest") != source["package_digest"]
        or snapshots.get("expected") != 16 or snapshots.get("actual") != 16
        or snapshots.get("pass_count") != 16 or not bool(snapshots.get("passed"))
        or any(not Path(row["snapshot_dir"]).is_dir() or not row.get("passed") for row in snapshots["rows"])
    ):
        raise ValueError("T13S17 source state or snapshot audit mismatch")
    results = []
    parse_count = 0
    for row in inventory["files"]:
        result = _read_json_gz(paths["raw"] / row["path"])
        parse_count += 1
        if (
            result.get("stage") != SOURCE_STAGE
            or result.get("campaign_identity") != SOURCE_CAMPAIGN_IDENTITY
            or result.get("controller_revision") != SOURCE_CONTROLLER_REVISION
            or not bool(result.get("success")) or not bool(result.get("completed"))
            or len(result.get("trajectory", [])) < 12
            or len(result.get("controller_trace", [])) < 11
        ):
            raise ValueError("T13S17 source raw semantic authentication failed")
        results.append(result)
    ids = [str(result["experiment_id"]) for result in results]
    if len(set(ids)) != 144:
        raise ValueError("T13S17 source experiment identities are not unique")
    audit = {
        "source_run": str(paths["root"]),
        "required_file_count": len(file_rows),
        "required_files": file_rows,
        "raw_count": len(results),
        "raw_parse_count": parse_count,
        "raw_total_bytes": inventory["total_bytes"],
        "raw_inventory_digest": inventory["digest"],
        "snapshot_count": 16,
        "snapshot_pass_count": 16,
        "passed": True,
    }
    return audit, results


def _visible_outputs_prefix(result: Mapping[str, Any]) -> np.ndarray:
    trajectory = result["trajectory"]
    rows = []
    for index in range(1, 11):
        current, previous = trajectory[index], trajectory[index - 1]
        rows.append([
            float(current["R"]), float(current["Z"]),
            (float(current["R"]) - float(previous["R"])) / 0.01,
            (float(current["Z"]) - float(previous["Z"])) / 0.01,
            float(current["Ip"]),
        ])
    output = np.asarray(rows, dtype=float)
    if output.shape != (10, 5) or not np.all(np.isfinite(output)):
        raise ValueError("T13S17 causal visible prefix is invalid")
    return output


def _payload(paths: Mapping[str, Path], experiment_id: str) -> dict[str, Any]:
    return _read_json(paths["variants"] / f"payload_{experiment_id}.json")


def _source_join_key(result: Mapping[str, Any]) -> tuple[str, str, int, float]:
    """Join a probe to its baseline without opening pair/history labels."""
    spec = result["spec"]
    return (
        str(spec["state_generation_experiment_id"]), str(spec["target_id"]),
        int(spec["action_delay_steps"]), float(spec["slew_scale"]),
    )


def _prediction(trace_row: Mapping[str, Any]) -> Mapping[str, Any]:
    for key in ("r3c3t13s9_actuator_prediction", "r3c3t13s5_actuator_prediction"):
        value = trace_row.get(key)
        if isinstance(value, Mapping):
            return value
    raise ValueError("T13S17 actuator prediction is missing")


def _turns_tsc(payload: Mapping[str, Any]) -> np.ndarray:
    turns = np.asarray(payload["env_cfg"]["turns_display_order"], dtype=float)[
        np.asarray(DISPLAY_TO_TSC_INDEX)
    ]
    if turns.shape != (N_COILS,) or not np.all(np.isfinite(turns)) or np.any(turns <= 0.0):
        raise ValueError("T13S17 invalid TSC-order turn counts")
    return turns


def _response_coordinate(
    result: Mapping[str, Any], baseline: Mapping[str, Any], payload: Mapping[str, Any],
    cfg: Mapping[str, Any],
) -> dict[str, Any]:
    trace = result["controller_trace"]
    recorded = [row.get("r3c3t13s16_fixed_basis_delta_field_kAt_tsc") or [] for row in trace[:11]]
    constant = bool(
        len(recorded) == 11 and all(row == recorded[0] for row in recorded)
        and np.asarray(recorded[0], dtype=float).shape == (4, N_COILS)
    )
    if not constant:
        raise ValueError("T13S17 fixed basis is not causal and constant")
    turns = _turns_tsc(payload)
    fields = np.asarray(recorded[0], dtype=float).T
    basis = fields * 1000.0 / turns[:, None]
    signed_field = np.asarray(trace[10].get("r3c3t13s9_signed_issue_delta_kAt_tsc"), dtype=float)
    requested_current = signed_field * 1000.0 / turns
    coordinates, _, _, _ = np.linalg.lstsq(basis, requested_current, rcond=None)
    reconstructed = basis @ coordinates
    request_norm = float(np.linalg.norm(requested_current))
    reconstruction_norm = float(np.linalg.norm(reconstructed))
    cosine = float(np.dot(requested_current, reconstructed) / max(request_norm * reconstruction_norm, 1e-300))
    residual = float(np.linalg.norm(requested_current - reconstructed) / max(request_norm, 1e-300))
    base_prediction = _prediction(baseline["controller_trace"][10])
    probe_prediction = _prediction(trace[10])
    base_radius = 0.5 * (
        np.asarray(base_prediction["readback_upper_a_tsc"], dtype=float)
        - np.asarray(base_prediction["readback_lower_a_tsc"], dtype=float)
    )
    probe_radius = 0.5 * (
        np.asarray(probe_prediction["readback_upper_a_tsc"], dtype=float)
        - np.asarray(probe_prediction["readback_lower_a_tsc"], dtype=float)
    )
    coordinate_radius = np.abs(np.linalg.pinv(basis)) @ (base_radius + probe_radius)
    hypotheses = cfg["hypotheses"]
    projection_pass = bool(
        np.all(np.isfinite(coordinates)) and np.all(np.isfinite(coordinate_radius))
        and cosine >= float(hypotheses["minimum_response_basis_cosine"])
        and residual <= float(hypotheses["maximum_response_off_basis_residual"])
    )
    return {
        "coordinates": coordinates,
        "coordinate_radius": coordinate_radius,
        "cosine": cosine,
        "relative_residual": residual,
        "passed": projection_pass,
    }


def _belief_row(
    result: Mapping[str, Any], baseline: Mapping[str, Any], payload: Mapping[str, Any],
    cfg: Mapping[str, Any], designs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    outputs = _visible_outputs_prefix(result)
    response = _response_coordinate(result, baseline, payload, cfg)
    if not response["passed"]:
        raise ValueError("T13S17 response projection failed")
    coordinates = response["coordinates"]
    coordinate_radius = response["coordinate_radius"]
    floor = np.asarray(cfg["hypotheses"]["response_floor"], dtype=float)
    hypotheses = []
    lowers, uppers = [], []
    for item in designs:
        degree = int(item["degree"])
        design = np.asarray(item["design"], dtype=float)
        coefficients = np.linalg.pinv(design) @ outputs
        fitted = design @ coefficients
        residual = np.max(np.abs(outputs - fitted), axis=0)
        query = np.concatenate((np.zeros(degree + 1), coordinates))
        weights = query @ np.linalg.pinv(design)
        prediction = query @ coefficients
        input_coefficients = coefficients[-4:]
        residual_radius = float(np.sum(np.abs(weights))) * residual
        input_radius = np.abs(input_coefficients).T @ coordinate_radius
        radius = floor + residual_radius + input_radius
        lower, upper = prediction - radius, prediction + radius
        finite = bool(
            np.all(np.isfinite(coefficients)) and np.all(np.isfinite(prediction))
            and np.all(np.isfinite(radius)) and np.all(radius >= 0.0)
        )
        if not finite:
            raise ValueError("T13S17 non-finite hypothesis interval")
        hypotheses.append({
            "degree": degree,
            "design_rank": int(item["rank"]),
            "design_condition": float(item["condition"]),
            "prediction": prediction.tolist(),
            "maximum_regression_residual": residual.tolist(),
            "prediction_leverage_l1": float(np.sum(np.abs(weights))),
            "residual_radius": residual_radius.tolist(),
            "input_radius": input_radius.tolist(),
            "interval_radius": radius.tolist(),
            "lower": lower.tolist(),
            "upper": upper.tolist(),
            "passed": True,
        })
        lowers.append(lower)
        uppers.append(upper)
    lower = np.min(np.asarray(lowers), axis=0)
    upper = np.max(np.asarray(uppers), axis=0)
    center = 0.5 * (lower + upper)
    halfwidth = 0.5 * (upper - lower)
    return {
        "experiment_id": str(result["experiment_id"]),
        "baseline_experiment_id": str(baseline["experiment_id"]),
        "causal_state_indices": list(range(1, 11)),
        "causal_input_steps": list(range(10)),
        "response_basis_coordinates": coordinates.tolist(),
        "response_basis_coordinate_radius": coordinate_radius.tolist(),
        "response_basis_cosine": response["cosine"],
        "response_relative_off_basis_residual": response["relative_residual"],
        "hypotheses": hypotheses,
        "belief_lower": lower.tolist(),
        "belief_upper": upper.tolist(),
        "belief_center": center.tolist(),
        "belief_halfwidth": halfwidth.tolist(),
        "forbidden_predictor_input_count": 0,
        "future_response_value_access_count": 0,
        "passed": True,
    }


def _actual_response(result: Mapping[str, Any], baseline: Mapping[str, Any]) -> np.ndarray:
    spec = result["spec"]
    issue = int(spec["r3c3_probe_issue_step"])
    declared = int(spec["r3c3_probe_first_effect_state"])
    effect = issue + 1
    if issue != 10 or declared != 11 or effect != 11:
        raise ValueError("T13S17 source response-effect contract changed")
    probe = result["trajectory"]
    base = baseline["trajectory"]
    if len(probe) <= effect or len(base) <= effect:
        raise ValueError("T13S17 source response trajectory is incomplete")
    probe_state, base_state = probe[effect], base[effect]
    probe_previous, base_previous = probe[effect - 1], base[effect - 1]
    output = np.asarray([
        float(probe_state["R"]) - float(base_state["R"]),
        float(probe_state["Z"]) - float(base_state["Z"]),
        ((float(probe_state["R"]) - float(probe_previous["R"]))
         - (float(base_state["R"]) - float(base_previous["R"]))) / 0.01,
        ((float(probe_state["Z"]) - float(probe_previous["Z"]))
         - (float(base_state["Z"]) - float(base_previous["Z"]))) / 0.01,
        float(probe_state["Ip"]) - float(base_state["Ip"]),
    ], dtype=float)
    if output.shape != (5,) or not np.all(np.isfinite(output)):
        raise ValueError("T13S17 source actual response is invalid")
    return output


def prepare(
    cfg: Mapping[str, Any], config_path: Path, source_run: Path, output_dir: Path,
) -> dict[str, Any]:
    output = output_dir.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    state_path = output / STATE_NAME
    if state_path.exists() or (output / ARTIFACT_NAME).exists():
        raise ValueError("T13S17 prepare requires a fresh output identity")
    source_audit, results = _authenticate_source(cfg, source_run)
    paths = _source_paths(source_run)
    probes = [result for result in results if result["spec"].get("r3c3_probe_id") != BASELINE_PROBE_ID]
    baselines = [result for result in results if result["spec"].get("r3c3_probe_id") == BASELINE_PROBE_ID]
    if len(probes) != 128:
        raise ValueError("T13S17 response coverage mismatch")
    if len(baselines) != 16:
        raise ValueError("T13S17 baseline coverage mismatch")
    baseline_by_source = {_source_join_key(result): result for result in baselines}
    if len(baseline_by_source) != 16:
        raise ValueError("T13S17 opaque source-to-baseline join is not unique")
    designs = _designs(cfg)
    rows = []
    for result in sorted(probes, key=lambda item: str(item["experiment_id"])):
        baseline = baseline_by_source.get(_source_join_key(result))
        if baseline is None:
            raise ValueError("T13S17 causal baseline identity mismatch")
        payload = _payload(paths, str(result["experiment_id"]))
        rows.append(_belief_row(result, baseline, payload, cfg, designs))
    hypothesis_count = sum(len(row["hypotheses"]) for row in rows)
    max_condition = max(item["condition"] for item in designs)
    passed = bool(
        len(rows) == 128 and hypothesis_count == 384
        and all(row["passed"] for row in rows)
        and max_condition <= float(cfg["hypotheses"]["maximum_design_condition"])
    )
    artifact = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "causal_belief_frozen_before_outcome",
        "audit_identity": AUDIT_IDENTITY,
        "config_sha256": _sha256(config_path),
        "source_run": str(source_run.expanduser().resolve()),
        "source_raw_inventory_digest": source_audit["raw_inventory_digest"],
        "source_manifest_sha256": cfg["source"]["required_file_sha256"]["stage4_2r3c3t13s16_manifest.json"],
        "response_row_count": len(rows),
        "hypothesis_row_count": hypothesis_count,
        "designs": [{key: value for key, value in item.items() if key != "design"} for item in designs],
        "maximum_design_condition": max_condition,
        "outcome_value_access_count": 0,
        "forbidden_predictor_input_count": 0,
        "new_tsc_or_plant_step_count": 0,
        "passed": passed,
        "rows": rows,
    }
    if not passed:
        raise ValueError("T13S17 causal belief artifact gate failed")
    source_path = output / "source_authentication.json"
    artifact_path = output / ARTIFACT_NAME
    _write_json(source_path, source_audit)
    _write_json(artifact_path, artifact)
    artifact_sha = _sha256(artifact_path)
    state = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase_status": "causal_belief_frozen",
        "finished": False,
        "real_tsc_executed": False,
        "new_raw_count": 0,
        "source_raw_count": 144,
        "causal_belief_sha256": artifact_sha,
        "outcome_opened": False,
    }
    _write_json(state_path, state)
    return {
        "stage": STAGE, "phase": "causal_belief_frozen_before_outcome",
        "source_authentication_sha256": _sha256(source_path),
        "causal_belief_sha256": artifact_sha,
        "response_row_count": len(rows), "hypothesis_row_count": hypothesis_count,
        "maximum_design_condition": max_condition,
        "real_tsc_executed": False, "passed": True,
    }


def _evaluate_rows(
    cfg: Mapping[str, Any], source_run: Path, artifact: Mapping[str, Any],
) -> dict[str, Any]:
    source_audit, results = _authenticate_source(cfg, source_run)
    paths = _source_paths(source_run)
    final_model = _read_json(paths["final_model"])
    saved = {str(row["experiment_id"]): row for row in final_model["rows"]}
    by_id = {str(result["experiment_id"]): result for result in results}
    caps = np.asarray(cfg["hypotheses"]["belief_halfwidth_caps"], dtype=float)
    scales = np.asarray(cfg["hypotheses"]["response_scales"], dtype=float)
    tolerance = float(cfg["hypotheses"]["containment_tolerance"])
    rows = []
    for belief in artifact["rows"]:
        experiment_id = str(belief["experiment_id"])
        result = by_id[experiment_id]
        baseline = by_id[str(belief["baseline_experiment_id"])]
        actual = _actual_response(result, baseline)
        saved_row = saved[experiment_id]
        saved_actual = np.asarray(saved_row["actual_response"], dtype=float)
        saved_coordinates = np.asarray(saved_row["response_basis_coordinates"], dtype=float)
        saved_radius = np.asarray(saved_row["response_basis_coordinate_radius"], dtype=float)
        lower = np.asarray(belief["belief_lower"], dtype=float)
        upper = np.asarray(belief["belief_upper"], dtype=float)
        center = np.asarray(belief["belief_center"], dtype=float)
        halfwidth = np.asarray(belief["belief_halfwidth"], dtype=float)
        source_match = bool(
            np.allclose(actual, saved_actual, rtol=0.0, atol=1e-15)
            and np.allclose(np.asarray(belief["response_basis_coordinates"]), saved_coordinates, rtol=0.0, atol=1e-12)
            and np.allclose(np.asarray(belief["response_basis_coordinate_radius"]), saved_radius, rtol=0.0, atol=1e-12)
        )
        contained_components = (actual >= lower - tolerance) & (actual <= upper + tolerance)
        containment_pass = bool(np.all(contained_components))
        cap_components = halfwidth <= caps + tolerance
        cap_pass = bool(np.all(cap_components))
        midpoint_error = np.abs(actual - center) / scales
        spec = result["spec"]
        rows.append({
            "experiment_id": experiment_id,
            "pair_id": str(spec["pair_id"]),
            "history_member": str(spec["history_member"]),
            "direction": str(spec["r3c3_probe_direction"]),
            "sign": int(spec["r3c3_probe_sign"]),
            "target_id": str(spec["target_id"]),
            "delay": int(spec["action_delay_steps"]),
            "slew": float(spec["slew_scale"]),
            "actual_response": actual.tolist(),
            "source_response_match": source_match,
            "contained_components": contained_components.tolist(),
            "containment_pass": containment_pass,
            "cap_components": cap_components.tolist(),
            "cap_pass": cap_pass,
            "belief_halfwidth": halfwidth.tolist(),
            "midpoint_scaled_error": midpoint_error.tolist(),
            "maximum_midpoint_scaled_error": float(np.max(midpoint_error)),
            "passed": bool(source_match and containment_pass and cap_pass),
        })
    containment = sum(row["containment_pass"] for row in rows)
    caps_pass = sum(row["cap_pass"] for row in rows)
    joint = sum(row["passed"] for row in rows)
    source_match = sum(row["source_response_match"] for row in rows)
    max_halfwidth = np.max(np.asarray([row["belief_halfwidth"] for row in rows]), axis=0)
    max_midpoint_error = max(row["maximum_midpoint_scaled_error"] for row in rows)
    passed = bool(
        source_audit["passed"] and len(rows) == 128 and source_match == 128
        and containment == 128 and caps_pass == 128 and joint == 128
    )
    return {
        "source_authentication": source_audit,
        "response_row_count": len(rows),
        "source_response_match_count": source_match,
        "containment_pass_count": containment,
        "belief_cap_pass_count": caps_pass,
        "joint_pass_count": joint,
        "maximum_belief_halfwidth": max_halfwidth.tolist(),
        "maximum_midpoint_scaled_error": max_midpoint_error,
        "rows": rows,
        "passed": passed,
    }


def evaluate(cfg: Mapping[str, Any], source_run: Path, output_dir: Path) -> dict[str, Any]:
    output = output_dir.expanduser().resolve()
    state_path = output / STATE_NAME
    artifact_path = output / ARTIFACT_NAME
    state = _read_json(state_path)
    if (
        state.get("phase_status") != "causal_belief_frozen"
        or bool(state.get("outcome_opened")) or bool(state.get("real_tsc_executed"))
        or _sha256(artifact_path) != state.get("causal_belief_sha256")
    ):
        raise ValueError("T13S17 outcome gate opened before immutable belief")
    artifact_sha = _sha256(artifact_path)
    artifact = _read_json(artifact_path)
    if artifact.get("outcome_value_access_count") != 0 or not artifact.get("passed"):
        raise ValueError("T13S17 causal belief artifact is invalid")
    audit = _evaluate_rows(cfg, source_run, artifact)
    route = PASS_ROUTE if audit["passed"] else FAIL_ROUTE
    result = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "final_causal_multi_drift_belief_preflight",
        "audit_identity": AUDIT_IDENTITY,
        "causal_belief_sha256": artifact_sha,
        "belief_frozen_before_outcome": True,
        "source_raw_count": 144,
        "response_row_count": audit["response_row_count"],
        "hypothesis_row_count": int(artifact["hypothesis_row_count"]),
        "source_response_match_count": audit["source_response_match_count"],
        "containment_pass_count": audit["containment_pass_count"],
        "belief_cap_pass_count": audit["belief_cap_pass_count"],
        "joint_pass_count": audit["joint_pass_count"],
        "maximum_design_condition": artifact["maximum_design_condition"],
        "maximum_belief_halfwidth": audit["maximum_belief_halfwidth"],
        "maximum_midpoint_scaled_error": audit["maximum_midpoint_scaled_error"],
        "forbidden_predictor_input_count": 0,
        "runtime_or_environment_error_count": 0,
        "source_raw_or_restart_error_count": 0,
        "statistics_or_reporting_error_count": 0,
        "new_tsc_or_plant_step_count": 0,
        "real_tsc_executed": False,
        "route": route,
        "passed": audit["passed"],
        "rows": audit["rows"],
    }
    final_path = output / "final_result.json"
    _write_json(final_path, result)
    final_sha = _sha256(final_path)
    _write_json(state_path, {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase_status": "audit_complete",
        "finished": True,
        "primary_pass": audit["passed"],
        "real_tsc_executed": False,
        "new_raw_count": 0,
        "source_raw_count": 144,
        "causal_belief_sha256": artifact_sha,
        "outcome_opened": True,
        "final_result_sha256": final_sha,
        "verdict": {"route": route, "passed": audit["passed"]},
    })
    return {key: result[key] for key in (
        "stage", "phase", "route", "passed", "real_tsc_executed",
        "response_row_count", "hypothesis_row_count", "containment_pass_count",
        "belief_cap_pass_count", "joint_pass_count", "maximum_design_condition",
        "maximum_belief_halfwidth", "maximum_midpoint_scaled_error",
    )}


def postprocess(cfg: Mapping[str, Any], source_run: Path, output_dir: Path) -> dict[str, Any]:
    output = output_dir.expanduser().resolve()
    state = _read_json(output / STATE_NAME)
    artifact_path = output / ARTIFACT_NAME
    final_path = output / "final_result.json"
    if (
        state.get("phase_status") != "audit_complete"
        or _sha256(artifact_path) != state.get("causal_belief_sha256")
        or _sha256(final_path) != state.get("final_result_sha256")
    ):
        raise ValueError("T13S17 independent postprocess identity mismatch")
    artifact = _read_json(artifact_path)
    final = _read_json(final_path)
    audit = _evaluate_rows(cfg, source_run, artifact)
    exact = bool(
        audit["response_row_count"] == final["response_row_count"]
        and audit["source_response_match_count"] == final["source_response_match_count"]
        and audit["containment_pass_count"] == final["containment_pass_count"]
        and audit["belief_cap_pass_count"] == final["belief_cap_pass_count"]
        and audit["joint_pass_count"] == final["joint_pass_count"]
        and np.allclose(audit["maximum_belief_halfwidth"], final["maximum_belief_halfwidth"], rtol=0.0, atol=0.0)
        and audit["maximum_midpoint_scaled_error"] == final["maximum_midpoint_scaled_error"]
        and audit["passed"] == final["passed"]
    )
    result = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "independent_server_side_raw_recomputation",
        "source_raw_count": 144,
        "source_raw_inventory_digest": audit["source_authentication"]["raw_inventory_digest"],
        "response_row_count": audit["response_row_count"],
        "source_response_match_count": audit["source_response_match_count"],
        "containment_pass_count": audit["containment_pass_count"],
        "belief_cap_pass_count": audit["belief_cap_pass_count"],
        "joint_pass_count": audit["joint_pass_count"],
        "reported_summary_exact_on_recomputation": exact,
        "runtime_or_environment_error_count": 0,
        "source_raw_or_restart_error_count": 0,
        "statistics_or_reporting_error_count": 0 if exact else 1,
        "new_tsc_or_plant_step_count": 0,
        "real_tsc_executed": False,
        "route": final["route"],
        "model_passed": final["passed"],
        "passed": exact,
    }
    _write_json(output / "server_independent_postprocess.json", result)
    return result


def self_test(config_path: Path) -> dict[str, Any]:
    cfg = _load_config(config_path)
    designs = _designs(cfg)
    leverage = []
    for item in designs:
        design = item["design"]
        for direction in range(4):
            query = np.concatenate((np.zeros(item["degree"] + 1), np.eye(4)[direction]))
            leverage.append(float(np.sum(np.abs(query @ np.linalg.pinv(design)))))
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "self_test",
        "degrees": [item["degree"] for item in designs],
        "ranks": [item["rank"] for item in designs],
        "conditions": [item["condition"] for item in designs],
        "maximum_leverage_l1": max(leverage),
        "new_tsc_or_plant_step_count": 0,
        "real_tsc_executed": False,
        "passed": [item["rank"] for item in designs] == [6, 7, 8]
        and max(item["condition"] for item in designs) <= 4.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=_project_root() / "configs/stage4_2r3c3t13s17_causal_multi_drift_belief_preflight.json")
    parser.add_argument("--source-run", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--command", choices=("prepare", "evaluate", "postprocess"), default="prepare")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    cfg = _load_config(args.config)
    if args.self_test:
        result = self_test(args.config)
    else:
        if args.source_run is None or args.output_dir is None:
            parser.error("--source-run and --output-dir are required")
        if args.command == "prepare":
            result = prepare(cfg, args.config.expanduser().resolve(), args.source_run, args.output_dir)
        elif args.command == "evaluate":
            result = evaluate(cfg, args.source_run, args.output_dir)
        else:
            result = postprocess(cfg, args.source_run, args.output_dir)
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
