#!/usr/bin/env python3
"""Authenticate T11 raw and separate conditioning from measured formal gaps.

This retrospective tool is deliberately read-only with respect to the T11
run and audit trees.  It never combines response columns, fits a response
model, or executes a controller, optimizer, Ray, gotsc, or TSC.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence


STAGE = "Stage4.2R3c3T12"
IDENTITY = "post_t11_formal_gap_route_discriminator_v1"
T11_STAGE = "Stage4.2R3c3T11"
T11_CONTROL = "stage4_2r3c3t11_persistent_step_response_identification"
BASELINE_PROBE_ID = "persistent_step_baseline"
CONTEXT_FIELDS = (
    "pair_id",
    "history_member",
    "target_id",
    "actual_delay_steps",
    "actual_slew_scale",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_digest(value: Any) -> str:
    text = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_gz(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def _inventory(paths: Sequence[Path]) -> dict[str, Any]:
    rows = [
        {
            "path": path.name,
            "size_bytes": int(path.stat().st_size),
            "sha256": _sha256(path),
        }
        for path in sorted(paths)
    ]
    return {
        "n_files": len(rows),
        "total_bytes": sum(row["size_bytes"] for row in rows),
        "digest": _canonical_digest(rows),
        "files": rows,
    }


def _context_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        str(row["pair_id"]),
        str(row["history_member"]),
        str(row["target_id"]),
        int(row["actual_delay_steps"]),
        float(row["actual_slew_scale"]),
    )


def _context_record(key: Sequence[Any]) -> dict[str, Any]:
    return dict(zip(CONTEXT_FIELDS, key))


def _validate_design(cfg: Mapping[str, Any]) -> None:
    source = cfg["source_contract"]
    analysis = cfg["analysis_contract"]
    expected = cfg["forensic_reproduction_expectations"]
    execution = cfg["execution_contract"]
    scope = cfg["scientific_scope"]
    if (
        int(cfg.get("schema_version", -1)) != 1
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or int(source["t11_raw_count"]) != 416
        or int(source["t11_raw_total_bytes"]) != 19273198
        or tuple(analysis["context_key_fields"]) != CONTEXT_FIELDS
        or int(analysis["expected_context_count"]) != 32
        or int(analysis["expected_baseline_count"]) != 32
        or str(analysis["baseline_probe_id"]) != BASELINE_PROBE_ID
        or int(analysis["expected_signed_probe_count_per_context"]) != 12
        or int(analysis["expected_probe_count"]) != 384
        or float(analysis["frozen_condition_threshold"]) != 25.0
        or bool(analysis["allow_column_normalization"])
        or bool(analysis["allow_column_rescaling"])
        or bool(analysis["allow_probe_combination"])
        or bool(analysis["allow_response_model_fit"])
        or bool(analysis["allow_formal_feasibility_optimization"])
        or bool(analysis["allow_raw_or_source_mutation"])
        or int(expected["baseline_formal_pass_count"]) != 16
        or int(expected["baseline_formal_fail_count"]) != 16
        or int(expected["condition_pass_count"]) != 25
        or int(expected["condition_fail_count"]) != 7
        or int(expected["formal_pass_condition_pass"]) != 12
        or int(expected["formal_pass_condition_fail"]) != 4
        or int(expected["formal_fail_condition_pass"]) != 13
        or int(expected["formal_fail_condition_fail"]) != 3
        or int(expected["failed_baseline_with_any_single_probe_repair"]) != 0
        or int(expected["failed_baseline_single_probe_repair_total"]) != 0
        or int(expected["passing_baseline_single_probe_regression_total"]) != 1
        or not bool(execution["server_side_only_for_large_raw"])
        or not bool(execution["read_raw_in_place"])
        or bool(execution["ray_executed"])
        or bool(execution["gotsc_executed"])
        or bool(execution["tsc_executed"])
        or int(execution["plant_steps_executed"]) != 0
        or bool(execution["real_mpc_executed"])
        or bool(execution["snapshot_creation_allowed"])
        or not bool(scope["retrospective_development_evidence"])
        or bool(scope["t11_verdict_may_change"])
        or bool(scope["t11_response_bank_created"])
        or bool(scope["r3c4_feasibility_model_created"])
        or bool(scope["global_plant_reachability_claimed"])
        or bool(scope["probe_trajectories_are_demonstrations"])
        or bool(scope["full_size_new_identification_campaign_authorized"])
        or bool(scope["r3c4_implementation_authorized"])
        or bool(scope["bc_dagger_or_rl_allowed"])
    ):
        raise ValueError("T12 frozen design changed")


def _source_paths(run_dir: Path, audit_dir: Path) -> dict[str, Path]:
    control = run_dir / T11_CONTROL
    analysis = run_dir / "stage4_2r3c3t11_analysis"
    return {
        "config": run_dir / "stage4_2r3c3t11_config.resolved.json",
        "manifest": run_dir / "stage4_2r3c3t11_manifest.json",
        "state": run_dir / "stage4_2r3c3t11_state.json",
        "results": control / "results.json",
        "summary": control / "summary.json",
        "condition_results": control / "condition_number_results.json",
        "central_results": control / "central_response_results.json",
        "matched_history_results": control / "matched_hidden_history_results.json",
        "verdict": analysis / "stage4_2r3c3t11_verdict.json",
        "server_audit": audit_dir / "stage4_2r3c3t11_server_audit.json",
        "raw_inventory": audit_dir / "stage4_2r3c3t11_raw_inventory.json",
        "snapshot_audit": audit_dir / "stage4_2r3c3t11_snapshot_audit.json",
        "raw_dir": control / "raw",
    }


def _authenticate_source_files(
    cfg: Mapping[str, Any], run_dir: Path, audit_dir: Path
) -> dict[str, Any]:
    source = cfg["source_contract"]
    if run_dir.name != str(source["t11_run_name"]):
        raise ValueError("immutable T11 run name mismatch")
    paths = _source_paths(run_dir, audit_dir)
    expected_hashes = {
        "config": source["t11_config_sha256"],
        "manifest": source["t11_manifest_sha256"],
        "state": source["t11_state_sha256"],
        "results": source["t11_results_sha256"],
        "summary": source["t11_summary_sha256"],
        "condition_results": source["t11_condition_results_sha256"],
        "central_results": source["t11_central_results_sha256"],
        "matched_history_results": source[
            "t11_matched_history_results_sha256"
        ],
        "verdict": source["t11_verdict_sha256"],
        "server_audit": source["t11_server_audit_sha256"],
        "raw_inventory": source["t11_raw_inventory_file_sha256"],
        "snapshot_audit": source["t11_snapshot_audit_sha256"],
    }
    hashes = {}
    for name, expected in expected_hashes.items():
        actual = _sha256(paths[name])
        if actual != str(expected):
            raise ValueError(f"T11 {name} SHA-256 mismatch")
        hashes[name] = actual

    summary = _read_json(paths["summary"])
    verdict = _read_json(paths["verdict"])
    if (
        int(summary["n_rollouts"]) != 416
        or int(summary["execution_pass_count"]) != 416
        or int(summary["formal_contract_pass_count"]) != 207
        or bool(summary["formal_tracking_is_acceptance_gate"])
        or int(summary["condition_number_pass_count"]) != 25
        or bool(summary["passed"])
        or bool(verdict["primary_pass"])
        or str(verdict["verdict"])
        != "STAGE4_2R3C3T11_PERSISTENT_STEP_IDENTIFICATION_FAIL"
    ):
        raise ValueError("T11 frozen scientific outcome changed")
    return {"paths": paths, "hashes": hashes, "summary": summary}


def _raw_spec_matches_reported(
    raw: Mapping[str, Any], reported: Mapping[str, Any]
) -> bool:
    spec = raw["spec"]
    return bool(
        str(raw["experiment_id"]) == str(reported["experiment_id"])
        and str(spec["pair_id"]) == str(reported["pair_id"])
        and str(spec["history_member"]) == str(reported["history_member"])
        and str(spec["target_id"]) == str(reported["target_id"])
        and int(spec["action_delay_steps"])
        == int(reported["actual_delay_steps"])
        and float(spec["slew_scale"])
        == float(reported["actual_slew_scale"])
        and str(spec["r3c3_probe_id"]) == str(reported["probe_id"])
        and int(spec["r3c3_probe_sign"]) == int(reported["probe_sign"])
    )


def _audit_raw_files(
    cfg: Mapping[str, Any], raw_dir: Path, reported_results: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    source = cfg["source_contract"]
    raw_paths = sorted(raw_dir.glob("*.json.gz"))
    inventory = _inventory(raw_paths)
    if (
        int(inventory["n_files"]) != int(source["t11_raw_count"])
        or int(inventory["total_bytes"]) != int(source["t11_raw_total_bytes"])
        or str(inventory["digest"]) != str(source["t11_raw_inventory_digest"])
    ):
        raise ValueError("T11 raw inventory mismatch")

    raw_by_id: dict[str, Mapping[str, Any]] = {}
    for path in raw_paths:
        raw = _read_json_gz(path)
        experiment_id = str(raw.get("experiment_id", ""))
        spec = raw.get("spec", {})
        forbidden_clean = bool(
            not spec.get("hidden_wire_current_available_to_controller")
            and not spec.get("pair_or_history_label_available_to_controller")
            and not spec.get("source_action_available_to_controller")
            and not spec.get("source_coil_current_available_to_controller")
            and not spec.get("source_wire_current_available_to_controller")
            and not spec.get("source_result_available_to_controller")
            and int(spec.get("future_action_count", -1)) == 0
            and int(spec.get("future_measurement_count", -1)) == 0
        )
        if (
            not experiment_id
            or experiment_id in raw_by_id
            or raw.get("stage") != T11_STAGE
            or not bool(raw.get("success"))
            or not bool(raw.get("completed"))
            or len(raw.get("trajectory", [])) != 51
            or len(raw.get("controller_trace", [])) != 50
            or not forbidden_clean
        ):
            raise ValueError(f"T11 raw authentication failed: {path.name}")
        raw_by_id[experiment_id] = raw

    reported_by_id = {
        str(row["experiment_id"]): row for row in reported_results
    }
    if (
        len(reported_by_id) != int(source["t11_raw_count"])
        or set(reported_by_id) != set(raw_by_id)
        or any(
            not _raw_spec_matches_reported(raw_by_id[key], row)
            for key, row in reported_by_id.items()
        )
    ):
        raise ValueError("T11 raw-to-reported identity mismatch")
    return {
        "expected_count": int(source["t11_raw_count"]),
        "actual_count": len(raw_by_id),
        "unique_experiment_id_count": len(raw_by_id),
        "inventory_digest": inventory["digest"],
        "total_bytes": inventory["total_bytes"],
        "success_completed_count": len(raw_by_id),
        "trajectory_51_count": len(raw_by_id),
        "controller_trace_50_count": len(raw_by_id),
        "forbidden_input_contract_clean_count": len(raw_by_id),
        "raw_to_reported_identity_match_count": len(raw_by_id),
    }


def _counter_rows(counter: Counter[str]) -> list[dict[str, Any]]:
    return [
        {"name": name, "count": int(count)}
        for name, count in sorted(counter.items())
    ]


def _analyze_reported_results(
    cfg: Mapping[str, Any],
    reported_results: Sequence[Mapping[str, Any]],
    condition_results: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    contract = cfg["analysis_contract"]
    expected = cfg["forensic_reproduction_expectations"]
    by_context: dict[tuple[Any, ...], list[Mapping[str, Any]]] = defaultdict(list)
    for row in reported_results:
        margin = float(row[contract["formal_margin_field"]])
        if not math.isfinite(margin):
            raise ValueError("nonfinite T11 formal margin")
        by_context[_context_key(row)].append(row)
    condition_by_context = {
        _context_key(row): row for row in condition_results
    }
    if (
        len(reported_results)
        != int(contract["expected_baseline_count"])
        + int(contract["expected_probe_count"])
        or len(by_context) != int(contract["expected_context_count"])
        or len(condition_by_context) != int(contract["expected_context_count"])
        or set(by_context) != set(condition_by_context)
    ):
        raise ValueError("T11 context coverage mismatch")

    cross = Counter()
    failed_rows = []
    passing_rows = []
    repair_by_probe = Counter()
    regression_by_probe = Counter()
    probe_delta_sum = Counter()
    probe_delta_count = Counter()
    strata_baseline_fail = Counter()
    strata_any_repair = Counter()

    for key in sorted(by_context):
        rows = by_context[key]
        baselines = [row for row in rows if bool(row["extended_baseline"])]
        probes = [row for row in rows if not bool(row["extended_baseline"])]
        if (
            len(baselines) != 1
            or str(baselines[0]["probe_id"]) != BASELINE_PROBE_ID
            or len(probes)
            != int(contract["expected_signed_probe_count_per_context"])
            or len(
                {
                    (str(row["probe_id"]), int(row["probe_sign"]))
                    for row in probes
                }
            )
            != int(contract["expected_signed_probe_count_per_context"])
        ):
            raise ValueError(f"T11 measured-member coverage mismatch: {key}")
        baseline = baselines[0]
        baseline_pass = bool(baseline[contract["formal_pass_field"]])
        condition = condition_by_context[key]
        condition_value = float(condition[contract["condition_value_field"]])
        condition_pass = bool(condition[contract["condition_pass_field"]])
        if (
            not math.isfinite(condition_value)
            or condition_pass
            != (condition_value <= float(contract["frozen_condition_threshold"]))
        ):
            raise ValueError("T11 frozen condition classification mismatch")
        cross[(baseline_pass, condition_pass)] += 1

        baseline_margin = float(baseline[contract["formal_margin_field"]])
        best = max(
            probes, key=lambda row: float(row[contract["formal_margin_field"]])
        )
        best_margin = float(best[contract["formal_margin_field"]])
        best_gain = best_margin - baseline_margin
        repaired = [
            row for row in probes if bool(row[contract["formal_pass_field"]])
        ]
        regressed = [
            row for row in probes if not bool(row[contract["formal_pass_field"]])
        ]
        for row in probes:
            label = f"{row['probe_id']}:{int(row['probe_sign']):+d}"
            probe_delta_sum[label] += (
                float(row[contract["formal_margin_field"]]) - baseline_margin
            )
            probe_delta_count[label] += 1
        context = _context_record(key)
        context["condition_pass"] = condition_pass
        context["condition_number"] = condition_value
        context["baseline_margin"] = baseline_margin

        if not baseline_pass:
            gap = abs(baseline_margin)
            coverage = max(0.0, best_gain) / gap if gap > 0.0 else 0.0
            repair_labels = [
                f"{row['probe_id']}:{int(row['probe_sign']):+d}"
                for row in repaired
            ]
            for label in repair_labels:
                repair_by_probe[label] += 1
            stratum_names = (
                f"prefix:{str(key[0]).split('_', 1)[0]}",
                f"target:{key[2]}",
                f"actuator:delay{key[3]}_slew{key[4]}",
                f"history:{key[1]}",
            )
            for name in stratum_names:
                strata_baseline_fail[name] += 1
                if repaired:
                    strata_any_repair[name] += 1
            failed_rows.append(
                {
                    **context,
                    "best_measured_probe_id": str(best["probe_id"]),
                    "best_measured_probe_sign": int(best["probe_sign"]),
                    "best_measured_probe_margin": best_margin,
                    "best_measured_margin_gain": best_gain,
                    "best_measured_gap_coverage_ratio": coverage,
                    "single_probe_repair_count": len(repaired),
                    "single_probe_repairs": repair_labels,
                }
            )
        else:
            regression_labels = [
                f"{row['probe_id']}:{int(row['probe_sign']):+d}"
                for row in regressed
            ]
            for label in regression_labels:
                regression_by_probe[label] += 1
            passing_rows.append(
                {
                    **context,
                    "single_probe_regression_count": len(regressed),
                    "single_probe_regressions": regression_labels,
                }
            )

    cross_fields = {
        "formal_pass_condition_pass": cross[(True, True)],
        "formal_pass_condition_fail": cross[(True, False)],
        "formal_fail_condition_pass": cross[(False, True)],
        "formal_fail_condition_fail": cross[(False, False)],
    }
    baseline_pass_count = sum(key[0] for key in cross.elements())
    condition_pass_count = sum(key[1] for key in cross.elements())
    failed_with_repair = sum(
        row["single_probe_repair_count"] > 0 for row in failed_rows
    )
    repair_total = sum(row["single_probe_repair_count"] for row in failed_rows)
    regression_total = sum(
        row["single_probe_regression_count"] for row in passing_rows
    )
    reproduced = {
        "baseline_formal_pass_count": baseline_pass_count,
        "baseline_formal_fail_count": len(by_context) - baseline_pass_count,
        "condition_pass_count": condition_pass_count,
        "condition_fail_count": len(by_context) - condition_pass_count,
        **cross_fields,
        "failed_baseline_with_any_single_probe_repair": failed_with_repair,
        "failed_baseline_single_probe_repair_total": repair_total,
        "passing_baseline_single_probe_regression_total": regression_total,
    }
    if any(int(reproduced[name]) != int(value) for name, value in expected.items()):
        raise ValueError("T12 forensic reproduction expectation mismatch")

    probe_rows = []
    for label in sorted(probe_delta_count):
        probe_rows.append(
            {
                "probe": label,
                "context_count": int(probe_delta_count[label]),
                "mean_measured_margin_delta": float(
                    probe_delta_sum[label] / probe_delta_count[label]
                ),
                "failed_baseline_repair_count": int(repair_by_probe[label]),
                "passing_baseline_regression_count": int(
                    regression_by_probe[label]
                ),
            }
        )

    audit = {
        "context_count": len(by_context),
        "reported_result_count": len(reported_results),
        "cross_table": cross_fields,
        "reproduced_expectations": reproduced,
        "failed_baseline_rows": failed_rows,
        "passing_baseline_rows": passing_rows,
        "probe_rows": probe_rows,
        "failed_baseline_strata": _counter_rows(strata_baseline_fail),
        "failed_baseline_any_repair_strata": _counter_rows(
            strata_any_repair
        ),
        "best_measured_margin_gain_minimum": min(
            row["best_measured_margin_gain"] for row in failed_rows
        ),
        "best_measured_margin_gain_maximum": max(
            row["best_measured_margin_gain"] for row in failed_rows
        ),
        "best_measured_gap_coverage_ratio_minimum": min(
            row["best_measured_gap_coverage_ratio"] for row in failed_rows
        ),
        "best_measured_gap_coverage_ratio_maximum": max(
            row["best_measured_gap_coverage_ratio"] for row in failed_rows
        ),
    }
    route = {
        "condition_failure_is_not_necessary_for_formal_failure": bool(
            cross[(False, True)] > 0
        ),
        "condition_pass_is_not_sufficient_for_formal_control": bool(
            cross[(False, True)] > 0
        ),
        "condition_failure_is_not_sufficient_for_formal_failure": bool(
            cross[(True, False)] > 0
        ),
        "fixed_condition_first_route_vetoed": bool(
            cross[(True, False)] > 0 and cross[(False, True)] > 0
        ),
        "all_failed_baselines_repaired_by_a_measured_single_probe": bool(
            failed_with_repair == len(failed_rows)
        ),
        "t11_verdict_changed": False,
        "t11_response_bank_created": False,
        "r3c4_feasibility_model_created": False,
        "full_size_new_identification_campaign_authorized": False,
        "r3c4_authorized": False,
        "bc_dagger_or_rl_allowed": False,
        "next_route": str(cfg["next_route"]),
    }
    return audit, route


def run_audit(args: argparse.Namespace) -> dict[str, Any]:
    config_path = args.config.expanduser().resolve()
    cfg = _read_json(config_path)
    _validate_design(cfg)
    run_dir = args.source_t11_run.expanduser().resolve()
    audit_dir = args.source_t11_audit_dir.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if output.exists():
        raise ValueError("T12 output directory must be new")
    if (
        output == run_dir
        or run_dir in output.parents
        or output == audit_dir
        or audit_dir in output.parents
    ):
        raise ValueError("T12 output must remain outside immutable T11 evidence")

    authenticated = _authenticate_source_files(cfg, run_dir, audit_dir)
    results = _read_json(authenticated["paths"]["results"])
    conditions = _read_json(authenticated["paths"]["condition_results"])
    raw = _audit_raw_files(
        cfg, authenticated["paths"]["raw_dir"], results
    )
    analysis, route = _analyze_reported_results(cfg, results, conditions)
    provenance = {
        "stage": STAGE,
        "identity": IDENTITY,
        "design_config_sha256": _sha256(config_path),
        "source_t11_run": str(run_dir),
        "source_t11_audit_dir": str(audit_dir),
        "source_file_hashes": authenticated["hashes"],
        "t11_raw_inventory_digest": raw["inventory_digest"],
        "formal_timing_changed": False,
    }
    provenance_digest = _canonical_digest(provenance)
    audit_output = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "classification": "retrospective_formal_gap_route_audit",
        "provenance": provenance,
        "provenance_digest": provenance_digest,
        "raw_authentication": raw,
        "analysis": analysis,
        "scientific_guardrails": cfg["scientific_scope"],
        "audit_complete": True,
    }
    route_output = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "provenance_digest": provenance_digest,
        "route_result": route,
        "scientific_classification": {
            "runtime_or_environment_error": False,
            "raw_or_snapshot_corruption": False,
            "statistics_or_reporting_error": False,
            "t11_identification_design_failure_preserved": True,
            "real_tsc_executed_by_t12": False,
            "real_mpc_executed_by_t12": False,
            "real_closed_loop_conclusion_from_t12": "not_tested",
            "global_plant_reachability_conclusion": "not_tested",
        },
    }

    output.mkdir(parents=True, exist_ok=False)
    audit_path = output / "stage4_2r3c3t12_audit_v1.json"
    route_path = output / "stage4_2r3c3t12_route_result_v1.json"
    _write_json(audit_path, audit_output)
    _write_json(route_path, route_output)
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "provenance_digest": provenance_digest,
        "output_files": [
            {
                "path": audit_path.name,
                "size_bytes": audit_path.stat().st_size,
                "sha256": _sha256(audit_path),
            },
            {
                "path": route_path.name,
                "size_bytes": route_path.stat().st_size,
                "sha256": _sha256(route_path),
            },
        ],
        "raw_files_copied_or_modified": 0,
        "ray_gotsc_tsc_or_controller_executed": False,
    }
    manifest_path = output / "stage4_2r3c3t12_manifest_v1.json"
    _write_json(manifest_path, manifest)
    return {
        "output": str(output),
        "audit_sha256": _sha256(audit_path),
        "route_result_sha256": _sha256(route_path),
        "manifest_sha256": _sha256(manifest_path),
        "cross_table": analysis["cross_table"],
        "failed_baseline_with_any_single_probe_repair": analysis[
            "reproduced_expectations"
        ]["failed_baseline_with_any_single_probe_repair"],
        "fixed_condition_first_route_vetoed": route[
            "fixed_condition_first_route_vetoed"
        ],
        "real_tsc_executed": False,
        "real_mpc_executed": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source-t11-run", type=Path, required=True)
    parser.add_argument("--source-t11-audit-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    result = run_audit(_parser().parse_args())
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
