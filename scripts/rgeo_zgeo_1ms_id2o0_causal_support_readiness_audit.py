#!/usr/bin/env python3
"""ID-2O0 read-only causal-support and control-utility readiness audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2o0_causal_support_readiness_audit.json"
SCHEMA = "rgeo-zgeo-1ms-id2o0-causal-support-readiness-result-v1"


class IntegrityError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def inside_root(value: str, label: str, *, directory: bool = False) -> Path:
    path = (ROOT / value).resolve()
    try:
        path.relative_to(ROOT)
    except ValueError as exc:
        raise IntegrityError(f"{label} escapes repository") from exc
    if directory and not path.is_dir():
        raise IntegrityError(f"missing directory: {label}")
    if not directory and not path.is_file():
        raise IntegrityError(f"missing file: {label}")
    return path


def require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise IntegrityError(f"{label}: expected {expected!r}, got {actual!r}")


def load_stage(path: Path = CONFIG) -> dict[str, Any]:
    path = path.resolve()
    try:
        path.relative_to(ROOT)
    except ValueError as exc:
        raise IntegrityError("config escapes repository") from exc
    stage = read_json(path)
    require_equal(stage.get("schema_version"),
                  "rgeo-zgeo-1ms-id2o0-causal-support-readiness-audit-v1", "schema")
    require_equal(stage.get("identity"), stage["schema_version"], "identity")
    require_equal(stage.get("execution_contract"),
                  "server_read_only_zero_tsc_zero_model_fit", "execution contract")
    require_equal(stage.get("takeover_time_ms"), 1100, "takeover")
    require_equal(stage.get("control_period_ms"), 1, "period")
    require_equal(stage.get("prediction_horizons_ms"), list(range(1, 9)), "horizons")
    require_equal(stage["causal_prefix"]["future_actual_current"], "forbidden", "future current")
    require_equal(stage["causal_prefix"]["labels_or_family_ids_as_features"],
                  "forbidden", "label features")
    require_equal(stage["data_roles"]["n1_holdout"], "unopened_forbidden", "holdout role")
    return stage


def load_bound_inputs(stage: dict[str, Any]) -> dict[str, Any]:
    loaded: dict[str, Any] = {}
    for name in ("k1_config", "k1_result", "k1_independent", "n1_config",
                 "n1_result", "n1_independent", "n1_calibration"):
        spec = stage["inputs"][name]
        path = inside_root(spec["path"], name)
        require_equal(sha256(path), spec["sha256"], f"{name} sha256")
        loaded[name] = read_json(path)
    require_equal(loaded["k1_result"].get("route"),
                  stage["inputs"]["k1_result"]["required_route"], "K1 route")
    require_equal(loaded["k1_result"].get("passed"), True, "K1 pass")
    require_equal(loaded["k1_independent"].get("audit_passed"), True, "K1 audit")
    require_equal(loaded["n1_result"].get("route"),
                  stage["inputs"]["n1_result"]["required_route"], "N1 route")
    require_equal(loaded["n1_result"].get("holdout_opened"), False, "N1 holdout")
    require_equal(loaded["n1_independent"].get("audit_passed"), True, "N1 audit")
    return loaded


def primary(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted((row for row in rows if int(row["replay_index"]) == 0),
                  key=lambda row: row["cell_id"])


def load_rows(stage: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    expected = stage["expected"]
    kdir = inside_root(stage["inputs"]["k1_directory"], "K1 directory", directory=True)
    ndir = inside_root(stage["inputs"]["n1_raw_directory"], "N1 raw directory", directory=True)
    krows = [read_json(path) for path in sorted(kdir.glob("h??__*__r*.json"))]
    nrows = [read_json(path) for path in sorted(ndir.glob("c??__*__r*.json"))]
    require_equal(len(krows), expected["k1_rollouts"], "K1 rollouts")
    require_equal(len(nrows), expected["n1_calibration_rollouts"], "N1 rollouts")
    for label, rows in (("K1", krows), ("N1", nrows)):
        for row in rows:
            require_equal(row.get("passed"), True, f"{label} rollout pass")
            require_equal(len(row.get("states", [])), expected["state_count_per_rollout"],
                          f"{label} states")
            require_equal(len(row.get("actions", [])), expected["action_count_per_rollout"],
                          f"{label} actions")
            require_equal([int(x["time_ms"]) for x in row["states"]],
                          list(range(1100, 1135)), f"{label} state clocks")
            require_equal([int(x["issue_step"]) for x in row["actions"]],
                          list(range(34)), f"{label} action clocks")
            for state in row["states"]:
                if len(state["actual_current_a_tsc"]) != 14 or len(state["wire_current_a"]) != 48:
                    raise IntegrityError(f"{label} incomplete current state")
                if not all(math.isfinite(float(state[key])) for key in ("r_geo_m", "z_geo_m", "ip_a")):
                    raise IntegrityError(f"{label} invalid RZI")
            for action in row["actions"]:
                if len(action["target_current_a_tsc"]) != 14:
                    raise IntegrityError(f"{label} incomplete target")
                if float(action["maximum_issued_delta_a"]) > 0.3 + 1e-12:
                    raise IntegrityError(f"{label} slew violation")
    require_equal(len({row["cell_id"] for row in krows}), expected["k1_unique_cells"],
                  "K1 unique cells")
    require_equal(len({row["group_id"] for row in krows}), expected["k1_families"],
                  "K1 families")
    require_equal(len({row["cell_id"] for row in nrows}), expected["n1_unique_cells"],
                  "N1 unique cells")
    require_equal(len({row["group_id"] for row in nrows}), expected["n1_families"],
                  "N1 families")
    return krows, nrows


def state_vector(state: dict[str, Any]) -> np.ndarray:
    return np.asarray([state["r_geo_m"], state["z_geo_m"], state["ip_a"]], dtype=float)


def target(action: dict[str, Any]) -> np.ndarray:
    return np.asarray(action["target_current_a_tsc"], dtype=float)


def prefix_vector(row: dict[str, Any], origin: int, stage: dict[str, Any]) -> np.ndarray:
    cfg = stage["causal_prefix"]
    state_scales = cfg["state_scales"]
    delta_scales = cfg["delta_scales"]
    current = row["states"][origin]
    values: list[float] = [
        float(current["r_geo_m"]) / float(state_scales["r_geo_m"]),
        float(current["z_geo_m"]) / float(state_scales["z_geo_m"]),
        float(current["ip_a"]) / float(state_scales["ip_a"]),
    ]
    for lag in cfg["delta_lags"]:
        prior = row["states"][max(0, origin - int(lag))]
        values.extend([
            (float(current["r_geo_m"]) - float(prior["r_geo_m"])) / float(delta_scales["r_geo_m"]),
            (float(current["z_geo_m"]) - float(prior["z_geo_m"])) / float(delta_scales["z_geo_m"]),
            (float(current["ip_a"]) - float(prior["ip_a"])) / float(delta_scales["ip_a"]),
        ])
    values.extend((np.asarray(current["actual_current_a_tsc"], dtype=float) /
                   float(cfg["actual_current_scale_a"])).tolist())
    source = target(row["actions"][0])
    for lag in cfg["issued_history_lags"]:
        issue = origin - int(lag)
        issued = source if issue < 0 else target(row["actions"][issue])
        values.extend(((issued - source) / float(cfg["issued_current_scale_a"])).tolist())
    result = np.asarray(values, dtype=float)
    if result.shape != (96,) or not np.all(np.isfinite(result)):
        raise IntegrityError("invalid causal prefix vector")
    return result


def schedule_signature(row: dict[str, Any]) -> tuple[Any, ...]:
    probe_issue = int(row["probe_issue_step"])
    conditioners = tuple(sorted((
        probe_issue - int(event["issue_step"]), int(event["duration_issues"]),
        event["direction"], event["sign"]
    ) for event in row["conditioners"]))
    return (conditioners, row["direction_id"], row["sign"], int(row["probe_duration_issues"]))


def paired_response(row: dict[str, Any], baseline: dict[str, Any], horizons: Sequence[int]) -> np.ndarray:
    origin = int(row["probe_issue_step"])
    return np.vstack([state_vector(row["states"][origin + horizon]) -
                      state_vector(baseline["states"][origin + horizon]) for horizon in horizons])


def baseline_map(rows: Sequence[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["group_id"]: row for row in primary(rows) if row["cell_kind"] == "baseline"}


def response_rows(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in primary(rows) if row["cell_kind"] != "baseline"]


def rms_distance(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(left - right))))


def cosine(left: np.ndarray, right: np.ndarray) -> float:
    denom = float(np.linalg.norm(left) * np.linalg.norm(right))
    return 1.0 if denom == 0.0 and np.array_equal(left, right) else (-1.0 if denom == 0.0 else float(left @ right / denom))


def causal_key(row: dict[str, Any], issue: int) -> str:
    states = []
    for state in row["states"][:issue + 1]:
        states.append({
            "time_ms": state["time_ms"], "r_geo_m": state["r_geo_m"],
            "z_geo_m": state["z_geo_m"], "ip_a": state["ip_a"],
            "actual_current_a_tsc": state["actual_current_a_tsc"],
        })
    actions = [{"issue_step": action["issue_step"],
                "target_current_a_tsc": action["target_current_a_tsc"]}
               for action in row["actions"][:issue + 1]]
    return canonical_sha({"states": states, "actions": actions})


def support_metrics(krows: Sequence[dict[str, Any]], nrows: Sequence[dict[str, Any]],
                    stage: dict[str, Any]) -> dict[str, Any]:
    horizons = stage["prediction_horizons_ms"]
    kb, nb = baseline_map(krows), baseline_map(nrows)
    kprobes, nprobes = response_rows(krows), response_rows(nrows)
    exact_signatures = {schedule_signature(row) for row in kprobes}
    scales = np.asarray([stage["response_scales"][key] for key in ("r_geo_m", "z_geo_m", "ip_a")])
    items, truths, predictions, positive = [], [], [], 0
    for row in nprobes:
        origin = int(row["probe_issue_step"])
        candidates = [candidate for candidate in kprobes
                      if candidate["direction_id"] == row["direction_id"] and candidate["sign"] == row["sign"]]
        if not candidates:
            raise IntegrityError(f"no same-action K1 candidate: {row['cell_id']}")
        vector = prefix_vector(row, origin, stage)
        distances = [(rms_distance(vector, prefix_vector(candidate, int(candidate["probe_issue_step"]), stage)), candidate)
                     for candidate in candidates]
        distance, nearest = min(distances, key=lambda item: (item[0], item[1]["cell_id"]))
        truth = paired_response(row, nb[row["group_id"]], horizons)
        prediction = paired_response(nearest, kb[nearest["group_id"]], horizons)
        scaled_truth, scaled_prediction = truth / scales, prediction / scales
        truths.append(scaled_truth.reshape(-1))
        predictions.append(scaled_prediction.reshape(-1))
        peak = int(np.argmax(np.linalg.norm(truth[:, :2], axis=1)))
        direction = cosine(truth[peak, :2], prediction[peak, :2])
        positive += int(direction > 0.0)
        items.append({
            "cell_id": row["cell_id"], "group_id": row["group_id"],
            "nearest_k1_cell_id": nearest["cell_id"], "prefix_rms_distance": distance,
            "exact_schedule_supported": schedule_signature(row) in exact_signatures,
            "peak_horizon_ms": horizons[peak], "peak_rz_cosine": direction,
            "truth_peak_rz_mm": (truth[peak, :2] * 1000.0).tolist(),
            "nearest_peak_rz_mm": (prediction[peak, :2] * 1000.0).tolist(),
        })
    truth_all, pred_all = np.concatenate(truths), np.concatenate(predictions)
    denom = float(np.sum(np.square(truth_all)))
    nrmse = float(np.sqrt(np.sum(np.square(pred_all - truth_all)) / denom)) if denom else math.inf
    return {
        "probe_count": len(items), "probe_metrics": items,
        "exact_schedule_supported": sum(int(item["exact_schedule_supported"]) for item in items),
        "exact_schedule_support_fraction": float(np.mean([item["exact_schedule_supported"] for item in items])),
        "positive_nearest_response_directions": positive,
        "nearest_response_nrmse": nrmse,
        "prefix_distance_minimum": min(item["prefix_rms_distance"] for item in items),
        "prefix_distance_median": float(np.median([item["prefix_rms_distance"] for item in items])),
        "prefix_distance_maximum": max(item["prefix_rms_distance"] for item in items),
    }


def action_ranking(krows: Sequence[dict[str, Any]], nrows: Sequence[dict[str, Any]],
                   support: dict[str, Any], stage: dict[str, Any]) -> dict[str, Any]:
    horizons = stage["prediction_horizons_ms"]
    kb, nb = baseline_map(krows), baseline_map(nrows)
    kby = {row["cell_id"]: row for row in primary(krows)}
    nby = {row["cell_id"]: row for row in primary(nrows)}
    nearest = {item["cell_id"]: item["nearest_k1_cell_id"] for item in support["probe_metrics"]}
    angles = np.linspace(0.0, 2.0 * np.pi, 16, endpoint=False)
    regrets, details = [], []
    for group in sorted(nb):
        probes = [row for row in response_rows(nrows) if row["group_id"] == group]
        if len(probes) != 2:
            raise IntegrityError(f"expected two probes for {group}")
        truth, prediction = [], []
        for row in probes:
            tr = paired_response(row, nb[group], horizons)
            pr = paired_response(kby[nearest[row["cell_id"]]], kb[kby[nearest[row["cell_id"]]]["group_id"]], horizons)
            peak = int(np.argmax(np.linalg.norm(tr[:, :2], axis=1)))
            truth.append(tr[peak, :2])
            prediction.append(pr[peak, :2])
        truth_array, pred_array = np.asarray(truth), np.asarray(prediction)
        family_regrets = []
        scale = max(float(np.max(np.linalg.norm(truth_array, axis=1))), 1e-12)
        for angle in angles:
            desired = np.asarray([math.cos(float(angle)), math.sin(float(angle))])
            truth_scores = truth_array @ desired
            selected = int(np.argmax(pred_array @ desired))
            regret = max(0.0, float(np.max(truth_scores) - truth_scores[selected])) / scale
            family_regrets.append(regret)
            regrets.append(regret)
        details.append({"group_id": group, "maximum_regret_fraction": max(family_regrets),
                        "mean_regret_fraction": float(np.mean(family_regrets))})
    return {"angle_count_per_family": 16, "family_metrics": details,
            "maximum_regret_fraction": max(regrets), "mean_regret_fraction": float(np.mean(regrets))}


def structure_metrics(krows: Sequence[dict[str, Any]], nrows: Sequence[dict[str, Any]],
                      stage: dict[str, Any]) -> dict[str, Any]:
    kp, np_ = primary(krows), primary(nrows)
    all_rows = [*kp, *np_]
    keys = [causal_key(row, issue) for row in all_rows for issue in range(34)]
    probe_matrix = np.vstack([prefix_vector(row, int(row["probe_issue_step"]), stage)
                              for row in [*response_rows(krows), *response_rows(nrows)]])
    centered = probe_matrix - np.mean(probe_matrix, axis=0, keepdims=True)
    singular = np.linalg.svd(centered, compute_uv=False)
    rank = int(np.linalg.matrix_rank(centered))
    condition = math.inf if rank == 0 else float(singular[0] / singular[rank - 1])
    duration_families: dict[str, int] = {}
    for duration in stage["readiness_gates"]["required_probe_durations"]:
        duration_families[str(duration)] = len({row["group_id"] for row in response_rows(krows)
                                                if int(row["probe_duration_issues"]) == int(duration)})
    return {
        "fit_eligible_independent_families": len({row["group_id"] for row in kp}),
        "consumed_challenge_families": len({row["group_id"] for row in np_}),
        "combined_independent_families_descriptive_only": len({("k1", row["group_id"]) for row in kp} |
                                                               {("n1", row["group_id"]) for row in np_}),
        "primary_transition_rows": len(all_rows) * 34,
        "unique_exact_causal_transition_keys": len(set(keys)),
        "probe_prefix_feature_count": int(probe_matrix.shape[1]),
        "probe_prefix_rank": rank,
        "probe_prefix_condition": condition,
        "fit_eligible_families_by_probe_duration": duration_families,
    }


def gate_results(structure: dict[str, Any], support: dict[str, Any], ranking: dict[str, Any],
                 stage: dict[str, Any]) -> dict[str, bool]:
    gates = stage["readiness_gates"]
    duration_ok = all(structure["fit_eligible_families_by_probe_duration"][str(duration)] >=
                      int(gates["minimum_fit_eligible_families_per_probe_duration"])
                      for duration in gates["required_probe_durations"])
    return {
        "independent_family_support": structure["fit_eligible_independent_families"] >=
                                      int(gates["minimum_fit_eligible_independent_families"]),
        "exact_schedule_support": support["exact_schedule_support_fraction"] >=
                                  float(gates["minimum_exact_schedule_support_fraction"]),
        "nearest_response_direction": (support["probe_count"] == int(gates["required_nearest_response_count"]) and
                                       support["positive_nearest_response_directions"] >=
                                       int(gates["minimum_positive_nearest_response_directions"])),
        "nearest_response_nrmse": support["nearest_response_nrmse"] <=
                                  float(gates["maximum_nearest_response_nrmse"]),
        "action_ranking_regret": ranking["maximum_regret_fraction"] <=
                                 float(gates["maximum_action_ranking_regret_fraction"]),
        "duration_support": duration_ok,
    }


def compute(stage_path: Path = CONFIG, source_revision: str = "development") -> dict[str, Any]:
    stage = load_stage(stage_path)
    loaded = load_bound_inputs(stage)
    krows, nrows = load_rows(stage)
    structure = structure_metrics(krows, nrows, stage)
    support = support_metrics(krows, nrows, stage)
    ranking = action_ranking(krows, nrows, support, stage)
    gates = gate_results(structure, support, ranking, stage)
    ready = all(gates.values())
    route = stage["routes"]["support_sufficient" if ready else "matched_factorial_required"]
    return {
        "schema_version": SCHEMA, "source_revision": source_revision,
        "stage_config_sha256": sha256(stage_path), "passed": True,
        "route": route, "support_ready_for_model_comparison": ready,
        "models_fit_or_updated": 0, "tsc_calls": 0, "reset_calls": 0,
        "plant_advances": 0, "holdout_opened": False,
        "input_evidence": {name: spec["sha256"] for name, spec in stage["inputs"].items()
                           if isinstance(spec, dict) and "sha256" in spec},
        "structure_metrics": structure, "support_metrics": support,
        "action_ranking_metrics": ranking, "readiness_gates": gates,
        "n1_calibration_route_preserved": loaded["n1_result"]["route"],
        "claim_boundary": stage["claim_boundary"],
    }


def write_new(path: Path, value: Any) -> None:
    path = path.resolve()
    try:
        path.relative_to(ROOT)
    except ValueError as exc:
        raise IntegrityError("output escapes repository") from exc
    if path.exists():
        raise IntegrityError(f"refusing overwrite: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = compute(args.config, args.source_revision)
    except Exception as exc:
        stage = load_stage(args.config)
        result = {"schema_version": SCHEMA, "source_revision": args.source_revision,
                  "stage_config_sha256": sha256(args.config), "passed": False,
                  "route": stage["routes"]["input_or_integrity_fail"],
                  "reasons": [f"{type(exc).__name__}: {exc}"],
                  "models_fit_or_updated": 0, "tsc_calls": 0, "reset_calls": 0,
                  "plant_advances": 0, "holdout_opened": False,
                  "claim_boundary": stage["claim_boundary"]}
    write_new(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
