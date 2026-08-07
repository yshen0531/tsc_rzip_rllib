#!/usr/bin/env python3
"""Independent R8R9 full-metric and stored-score recomputation."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_campaign as r8r7,
)


STAGE = "Stage4.2R3c3T13S24D1R14R8R9"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r9_measured_multipulse_authority_audit"


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


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


def _inventory(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    count = total = 0
    for item in sorted(path.glob("*.json.gz"), key=lambda value: value.name):
        size = item.stat().st_size
        sha = _sha(item)
        digest.update(f"{item.name}\0{size}\0{sha}\n".encode())
        count += 1
        total += size
    return {"count": count, "bytes": total, "digest": digest.hexdigest()}


def _context(args: argparse.Namespace, cfg: Mapping[str, Any]) -> r8r7.Context:
    r8r8_cfg = _read(_root() / str(cfg["source_r8r8"]["config_path"]))
    source = argparse.Namespace(**vars(args))
    source.config = (_root() / str(r8r8_cfg["source_r8r7_config"])).resolve()
    source.run_dir = args.r8r7_run.expanduser().resolve()
    return r8r7.load_context(source)


def _authenticate(args: argparse.Namespace, cfg: Mapping[str, Any]) -> dict[str, Any]:
    stage7 = args.r8r7_run.expanduser().resolve() / str(cfg["source_r8r7"]["stage_directory"])
    files7 = {
        "all_specs": stage7 / "specs/all_specs.json",
        "baseline_specs": stage7 / "specs/baseline_specs.json",
        "multipulse_specs": stage7 / "specs/multipulse_specs.json",
        "baseline_raw_primary": stage7 / "analysis/baseline_raw_primary.json",
        "baseline_raw_independent": stage7 / "analysis/baseline_raw_independent.json",
        "multipulse_raw_primary": stage7 / "analysis/multipulse_raw_primary.json",
        "multipulse_raw_independent": stage7 / "analysis/multipulse_raw_independent.json",
        "final_report": stage7 / "analysis/final_report.json",
        "stage_manifest": stage7 / "stage_manifest.json",
        "stage_state": stage7 / "stage_state.json",
    }
    hashes7 = {name: _sha(path) for name, path in files7.items()}
    source7 = cfg["source_r8r7"]
    if any(hashes7[name] != str(source7[f"{name}_sha256"]) for name in files7):
        raise ValueError("R8R9 independent R8R7 source hash changed")
    inventories = {name: _inventory(stage7 / "raw" / name) for name in ("baseline", "multipulse")}
    if any(
        inventories[name] != {
            "count": int(source7[f"{name}_raw_count"]),
            "bytes": int(source7[f"{name}_raw_bytes"]),
            "digest": str(source7[f"{name}_raw_digest"]),
        }
        for name in inventories
    ):
        raise ValueError("R8R9 independent R8R7 raw inventory changed")
    stage8 = args.r8r8_run.expanduser().resolve() / str(cfg["source_r8r8"]["stage_directory"])
    files8 = {
        "offline_primary_detailed": stage8 / "analysis/offline_primary_detailed.json",
        "offline_primary_summary": stage8 / "analysis/offline_primary_summary.json",
        "offline_independent": stage8 / "analysis/offline_independent.json",
        "stage_manifest": stage8 / "stage_manifest.json",
        "stage_state": stage8 / "stage_state.json",
    }
    hashes8 = {name: _sha(path) for name, path in files8.items()}
    source8 = cfg["source_r8r8"]
    if any(hashes8[name] != str(source8[f"{name}_sha256"]) for name in files8):
        raise ValueError("R8R9 independent R8R8 source hash changed")
    return {
        "r8r7_hashes": hashes7,
        "r8r7_raw_inventories": inventories,
        "r8r8_hashes": hashes8,
        "passed": True,
    }


def _formal(
    ctx: r8r7.Context,
    stage: Path,
    specs: list[dict[str, Any]],
    primary: Mapping[str, Any],
    tolerance: float,
) -> dict[str, Any]:
    evaluators, _ = r8r7.r8.d1r11._formal_callback(ctx.r8_ctx.d1r11_ctx, specs)
    expected = {str(row["experiment_id"]): row for row in primary["formal_rows"]}
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    maximum_difference = 0.0
    exact_agreement = True
    for spec in specs:
        experiment_id = str(spec["experiment_id"])
        partition = str(spec["partition"])
        result = _gzip(stage / "raw" / partition / f"{experiment_id}.json.gz")
        rzi = np.asarray(
            [[row["R"], row["Z"], row["Ip"]] for row in result["trajectory"]], dtype=float
        )
        metric = evaluators[experiment_id].exact_existing_metric(result, rzi)
        recorded = expected[experiment_id]
        exact_agreement = bool(
            exact_agreement
            and bool(metric["formal_contract_pass"]) == bool(recorded["formal_contract_pass"])
            and int(metric["formal_best_arrival_ms"]) == int(recorded["formal_best_arrival_ms"])
        )
        for name in ("formal_minimum_signed_margin", "formal_mean_signed_margin"):
            maximum_difference = max(
                maximum_difference, abs(float(metric[name]) - float(recorded[name]))
            )
        groups[(str(spec["pair_id"]), str(spec["history_member"]))].append(
            {
                "partition": partition,
                "schedule_index": int(spec.get("r8r7_schedule_index", -1)),
                "passed": bool(metric["formal_contract_pass"]),
                "minimum": float(metric["formal_minimum_signed_margin"]),
                "mean": float(metric["formal_mean_signed_margin"]),
            }
        )
    baseline_pass = multipulse_pass = repair = oracle_pass = improved = 0
    gains = []
    for group in groups.values():
        baseline = next(row for row in group if row["partition"] == "baseline")
        schedules = sorted(
            (row for row in group if row["partition"] == "multipulse"),
            key=lambda row: row["schedule_index"],
        )
        best = max(schedules, key=lambda row: (row["minimum"], row["mean"], -row["schedule_index"]))
        oracle = max(
            enumerate([baseline, *schedules]),
            key=lambda item: (item[1]["minimum"], item[1]["mean"], -item[0]),
        )[1]
        gain = best["minimum"] - baseline["minimum"]
        gains.append(gain)
        baseline_pass += int(baseline["passed"])
        multipulse_pass += sum(int(row["passed"]) for row in schedules)
        repair += int(not baseline["passed"] and any(row["passed"] for row in schedules))
        improved += int(not baseline["passed"] and gain > tolerance)
        oracle_pass += int(oracle["passed"])
    return {
        "formal_row_count": len(expected),
        "primary_row_agreement": exact_agreement,
        "maximum_primary_margin_abs_difference": maximum_difference,
        "context_count": len(groups),
        "baseline_formal_pass_count": baseline_pass,
        "multipulse_formal_pass_count": multipulse_pass,
        "failed_baseline_count": len(groups) - baseline_pass,
        "repaired_failed_baseline_count": repair,
        "failed_baseline_strict_margin_improvement_count": improved,
        "measured_oracle_formal_pass_count": oracle_pass,
        "best_schedule_minimum_margin_gain_minimum": min(gains),
        "best_schedule_minimum_margin_gain_median": statistics.median(gains),
        "best_schedule_minimum_margin_gain_maximum": max(gains),
        "passed": bool(exact_agreement and maximum_difference <= tolerance),
    }


def _score(prediction: np.ndarray, tube: np.ndarray, desired: np.ndarray, objective: Mapping[str, Any]) -> float:
    scales = np.asarray(objective["physical_scales"], dtype=float)
    component = np.asarray(objective["component_weights"], dtype=float)
    lag = np.asarray(objective["lag_weights"], dtype=float)
    upper = np.abs(prediction * scales[None, :] - desired[None, :]) + tube
    return float(np.sum(lag[:, None] * component[None, :] * np.square(upper / scales[None, :])))


def _scores(stage: Path, cfg: Mapping[str, Any], primary: Mapping[str, Any]) -> dict[str, Any]:
    r8cfg = _read(_root() / str(cfg["source_r8r8"]["config_path"]))
    detailed = _read(stage / "analysis/offline_primary_detailed.json")
    specs = {row["experiment_id"]: row for row in _read(stage / "specs/core_specs.json")}
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in detailed["forecast_rows"]:
        groups[str(row["row_id"])].append(row)
    values: dict[str, list[float]] = {name: [] for name in ("frozen_robust", "point_only", "common_static_tube")}
    max_stored = 0.0
    for group in groups.values():
        ordered = sorted(group, key=lambda row: int(row["order"]))
        spec = specs[str(ordered[0]["experiment_id"])]
        base = np.asarray(r8cfg["objective_contract"]["base_target_physical"], dtype=float)
        offset = np.asarray(spec["r8r8_numeric_target_offsets"], dtype=float)
        desired = np.asarray([base[0] + offset[0], base[1] + offset[1], 0.0, 0.0, base[2] + offset[2]])
        static = np.asarray(ordered[0]["tube_physical"], dtype=float)
        scores = {name: [] for name in values}
        for row in ordered:
            prediction = np.asarray(row["combined_prediction"], dtype=float)
            tube = np.asarray(row["tube_physical"], dtype=float)
            robust = _score(prediction, tube, desired, r8cfg["objective_contract"])
            max_stored = max(max_stored, abs(robust - float(row["score"])))
            scores["frozen_robust"].append(robust)
            scores["point_only"].append(
                _score(prediction, np.zeros_like(tube), desired, r8cfg["objective_contract"])
            )
            scores["common_static_tube"].append(
                _score(prediction, static, desired, r8cfg["objective_contract"])
            )
        for name, current in scores.items():
            best = min(range(1, 9), key=lambda index: (current[index], index))
            values[name].append(current[best] / current[0])
    output: dict[str, Any] = {
        "forecast_count": len(detailed["forecast_rows"]),
        "decision_count": len(groups),
        "maximum_stored_robust_score_abs_difference": max_stored,
    }
    for name, current in values.items():
        output[name] = {
            "minimum": min(current),
            "median": statistics.median(current),
            "maximum": max(current),
            "strictly_better_than_zero_count": sum(value < 1.0 for value in current),
            "meets_frozen_0_995_ratio_count": sum(value <= 0.995 for value in current),
        }
    expected = primary["r8r8_score_attribution"]
    difference = 0.0
    for name in values:
        for metric in ("minimum", "median", "maximum"):
            difference = max(difference, abs(float(output[name][metric]) - float(expected[name][metric])))
    output["maximum_primary_ratio_abs_difference"] = difference
    output["passed"] = bool(max_stored <= 1e-12 and difference <= 1e-12)
    return output


def run(args: argparse.Namespace) -> dict[str, Any]:
    cfg = _read(args.config.expanduser().resolve())
    output = args.run_dir.expanduser().resolve() / RUN_NAME
    primary_path = output / "analysis/primary_detailed.json"
    primary = _read(primary_path)
    authentication = _authenticate(args, cfg)
    stage7 = args.r8r7_run.expanduser().resolve() / str(cfg["source_r8r7"]["stage_directory"])
    stage8 = args.r8r8_run.expanduser().resolve() / str(cfg["source_r8r8"]["stage_directory"])
    specs = _read(stage7 / "specs/all_specs.json")
    formal = _formal(
        _context(args, cfg),
        stage7,
        specs,
        primary,
        float(cfg["formal_contract"]["metric_equivalence_absolute_tolerance"]),
    )
    scores = _scores(stage8, cfg, primary)
    authority = primary["authority"]
    outcome_agreement = bool(
        all(
            formal[name] == authority[name]
            for name in (
                "context_count",
                "baseline_formal_pass_count",
                "multipulse_formal_pass_count",
                "failed_baseline_count",
                "repaired_failed_baseline_count",
                "failed_baseline_strict_margin_improvement_count",
                "measured_oracle_formal_pass_count",
            )
        )
        and bool(primary["integrity_gate_passed"])
    )
    numerical = bool(formal["passed"] and scores["passed"])
    route_agreement = bool(
        primary["route"]
        == cfg["routes"]["pass" if primary["scientific_gate_passed"] else "authority_fail"]
    )
    passed = bool(authentication["passed"] and numerical and outcome_agreement and route_agreement)
    result = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "independent_full_metric_and_score_recomputation",
        "source_authentication": authentication,
        "formal_recomputation": formal,
        "score_recomputation": scores,
        "primary_numerical_agreement": numerical,
        "primary_outcome_agreement": outcome_agreement,
        "primary_route_agreement": route_agreement,
        "primary_scientific_gate_passed": bool(primary["scientific_gate_passed"]),
        "scientific_gate_passed": bool(primary["scientific_gate_passed"] and passed),
        "primary_sha256": _sha(primary_path),
        "route": str(primary["route"]) if passed else str(cfg["routes"]["audit_fail"]),
        "real_tsc_executed": False,
        "new_raw_count": 0,
        "passed": passed,
    }
    _write(output / "analysis/independent.json", result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--r8r7-run", type=Path, required=True)
    parser.add_argument("--r8r8-run", type=Path, required=True)
    parser.add_argument("--r8-run", type=Path, required=True)
    parser.add_argument("--r8r1-output", type=Path, required=True)
    parser.add_argument("--r8r6-run", type=Path, required=True)
    parser.add_argument("--source-d1r11-run", type=Path, required=True)
    parser.add_argument("--source-r2-run", type=Path, required=True)
    parser.add_argument("--source-r4-run", type=Path, required=True)
    parser.add_argument("--source-r6-run", type=Path, required=True)
    parser.add_argument("--source-s21-run", type=Path, required=True)
    parser.add_argument("--source-s23r1-output", type=Path, required=True)
    parser.add_argument("--source-s24-run", type=Path, required=True)
    parser.add_argument("--source-d1r9-v1", type=Path, required=True)
    parser.add_argument("--source-d1r9-v2", type=Path, required=True)
    parser.add_argument("--source-d1r10-run", type=Path, required=True)
    parser.add_argument("--source-d1r10-audit", type=Path, required=True)
    parser.add_argument("--source-stage42r3b-run", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3-run", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3-bank-dir", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3t1-run", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3t1-audit-dir", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3t3-controller-bank", type=Path, required=True)
    parser.add_argument("--q1-run", type=Path, required=True)
    parser.add_argument("--q2-run", type=Path, required=True)
    parser.add_argument("--q1-audit", type=Path, required=True)
    parser.add_argument("--q2-audit", type=Path, required=True)
    parser.add_argument("--r3b-server-audit", type=Path, required=True)
    parser.add_argument("--r3b-snapshot-checks", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    return parser


def main() -> None:
    print(json.dumps(run(_parser().parse_args()), indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
