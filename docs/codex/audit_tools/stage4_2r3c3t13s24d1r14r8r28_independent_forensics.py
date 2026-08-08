#!/usr/bin/env python3
"""Structurally independent R8R28 source, action, raw, and formal forensics."""

from __future__ import annotations

import argparse
import contextlib
import copy
import gzip
import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any, Mapping

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r11_independent_forensics as ind11,
    stage4_2r3c3t13s24d1r14r8r14_independent_forensics as ind14,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_campaign as r8r7,
    stage4_2r3c3t13s24d1r14r8r9_measured_multipulse_authority_audit as r8r9,
)


STAGE = "Stage4.2R3c3T13S24D1R14R8R28"
IDENTITY = "front_loaded_cumulative_endpoint_timing_authority_sentinel_v1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r28_front_loaded_cumulative_endpoint_timing_authority_sentinel"
CONTROLLER_REVISION = "front_loaded_cumulative_endpoint_timing_v42r3c3t13s24d1r14r8r28_v1"
PHASES = ("safety", "qualification")
PREFIX_END = 10
N_COILS = 14


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
    path.parent.mkdir(parents=True, exist_ok=True)
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
    files = sorted(path.glob("*.json.gz"), key=lambda value: value.name)
    digest = hashlib.sha256()
    rows = []
    for file in files:
        size, sha = file.stat().st_size, _sha(file)
        digest.update(f"{file.name}\0{size}\0{sha}\n".encode())
        rows.append({"name": file.name, "size": size, "sha256": sha})
    return {
        "count": len(rows),
        "bytes": sum(int(row["size"]) for row in rows),
        "digest": digest.hexdigest(),
        "rows": rows,
    }


def _stage(args: argparse.Namespace) -> Path:
    return args.run_dir.expanduser().resolve() / RUN_NAME


def _source_stage(args: argparse.Namespace, cfg: Mapping[str, Any]) -> Path:
    return args.r8r7_run.expanduser().resolve() / str(cfg["source_r8r7"]["stage_directory"])


def _r8r14_stage(args: argparse.Namespace, cfg: Mapping[str, Any]) -> Path:
    return args.r8r14_run.expanduser().resolve() / str(cfg["source_r8r14"]["stage_directory"])


def _r8r27_stage(args: argparse.Namespace, cfg: Mapping[str, Any]) -> Path:
    return args.r8r27_run.expanduser().resolve() / str(cfg["source_r8r27"]["stage_directory"])


def _source_context(args: argparse.Namespace, cfg: Mapping[str, Any]) -> r8r7.Context:
    source_args = argparse.Namespace(**vars(args))
    source_args.config = (_root() / str(cfg["source_r8r7_config"])).resolve()
    source_args.run_dir = args.r8r7_run.expanduser().resolve()
    return r8r7.load_context(source_args)


def _source_baselines(
    args: argparse.Namespace, cfg: Mapping[str, Any], source_ctx: r8r7.Context
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    return ind14._source_baselines(args, cfg, source_ctx)


def _expected_specs(
    args: argparse.Namespace, cfg: Mapping[str, Any], source_ctx: r8r7.Context
) -> list[dict[str, Any]]:
    baselines, _ = _source_baselines(args, cfg, source_ctx)
    safety = set(map(str, cfg["context_contract"]["safety_pairs"]))
    schedule = cfg["schedule_contract"]
    output = []
    for index, source in enumerate(baselines):
        phase = "safety" if str(source["pair_id"]) in safety else "qualification"
        for grid in schedule["timing_grids"]:
            grid_id = str(grid["grid_id"])
            decisions = list(map(int, grid["decision_task_steps"]))
            for endpoint in schedule["endpoint_sequences"]:
                sequence = str(endpoint["sequence_id"])
                direction, sign = int(endpoint["direction_index"]), int(endpoint["sign"])
                requested = (
                    np.asarray(schedule["canonical_matrix_columns"], dtype=float)[:, direction]
                    * sign
                )
                row = copy.deepcopy(source)
                row.update(
                    {
                        "kind": "stage4_2r3c3t13s24d1r14r8r28_front_loaded_timing",
                        "stage": STAGE,
                        "campaign_identity": IDENTITY,
                        "controller_revision": CONTROLLER_REVISION,
                        "partition": phase,
                        "experiment_id": f"r8r28_{phase}_{index:02d}_{grid_id}_{sequence.lower()}",
                        "source_r8r7_baseline_experiment_id": str(source["experiment_id"]),
                        "r8r28_role": "front_loaded_cumulative_endpoint_timing",
                        "r8r28_grid_id": grid_id,
                        "r8r28_sequence_id": sequence,
                        "r8r28_direction_index": direction,
                        "r8r28_sign": sign,
                        "r8r28_canonical_scale": 1.0,
                        "r8r28_requested_coordinate": requested.tolist(),
                        "r8r28_decision_task_steps": decisions,
                        "r8r28_allowed_in_expert_dataset": False,
                        "r8r14_direction_index": direction,
                        "r8r14_sign": sign,
                        "r8r14_canonical_scale": 1.0,
                        "r8r14_requested_coordinate": requested.tolist(),
                        "r8r14_matrix_digest": str(schedule["canonical_matrix_float64_le_c_sha256"]),
                        "r8r14_decision_task_steps": decisions,
                        "pair_or_history_label_available_to_controller": False,
                        "source_result_available_to_controller": False,
                        "future_measurement_count": 0,
                        "future_action_count": 0,
                        "formal_timing_unchanged": True,
                    }
                )
                output.append(row)
    counts = {phase: sum(row["partition"] == phase for row in output) for phase in PHASES}
    if len(output) != 64 or counts != {"safety": 16, "qualification": 48}:
        raise ValueError("independent R8R28 specification matrix changed")
    return output


def _authenticate_stage(
    stage: Path, expected: Mapping[str, Any], *, r8r14: bool
) -> dict[str, Any]:
    names = ("primary_detailed", "primary_summary", "final_report", "manifest", "state")
    paths = {
        "primary_detailed": stage / "analysis/primary_detailed.json",
        "primary_summary": stage / "analysis/primary_summary.json",
        "final_report": stage / "analysis/final_report.json",
        "manifest": stage / "stage_manifest.json",
        "state": stage / "stage_state.json",
    }
    independent_name = "final_independent" if r8r14 else "independent"
    paths[independent_name] = stage / f"analysis/{independent_name}.json"
    hashes = {name: _sha(path) for name, path in paths.items()}
    for name in (*names, independent_name):
        key = (
            "stage_manifest_sha256"
            if name == "manifest"
            else "stage_state_sha256"
            if name == "state"
            else f"{name}_sha256"
        )
        if hashes[name] != str(expected[key]):
            raise ValueError(f"independent R8R28 source {name} changed")
    final, state = _read(paths["final_report"]), _read(paths["state"])
    passed = bool(
        final.get("route") == expected["required_route"]
        and state.get("finished") is True
        and (state.get("verdict") or {}).get("route") == expected["required_route"]
    )
    if r8r14:
        inventories = {phase: _inventory(stage / "raw" / phase) for phase in PHASES}
        for phase, inventory in inventories.items():
            if (
                inventory["count"] != int(expected[f"{phase}_raw_count"])
                or inventory["bytes"] != int(expected[f"{phase}_raw_bytes"])
                or inventory["digest"] != str(expected[f"{phase}_raw_digest"])
            ):
                raise ValueError(f"independent R8R28 R8R14 {phase} raw changed")
        passed = bool(
            passed
            and final.get("passed") is False
            and int(state.get("new_raw_count", -1)) == 112
            and state.get("real_tsc_executed") is True
        )
        return {"stage": str(stage), "hashes": hashes, "inventories": inventories, "passed": passed}
    passed = bool(
        passed
        and final.get("passed") is True
        and final.get("point_authority_present") is False
        and state.get("real_tsc_executed") is False
        and int(state.get("new_raw_count", -1)) == 0
    )
    return {"stage": str(stage), "hashes": hashes, "passed": passed}


@contextlib.contextmanager
def _r28_stage_for_ind14():
    old = ind14.RUN_NAME
    try:
        ind14.RUN_NAME = RUN_NAME
        yield
    finally:
        ind14.RUN_NAME = old


def offline_audit(args: argparse.Namespace, cfg: Mapping[str, Any]) -> dict[str, Any]:
    stage = _stage(args)
    source_ctx = _source_context(args, cfg)
    _, sources = _source_baselines(args, cfg, source_ctx)
    expected_specs = _expected_specs(args, cfg, source_ctx)
    saved_specs = _read(stage / "specs/all_specs.json")
    source_r8r7 = r8r9._authenticate_r8r7(_source_stage(args, cfg), cfg)
    source_r8r14 = _authenticate_stage(_r8r14_stage(args, cfg), cfg["source_r8r14"], r8r14=True)
    source_r8r27 = _authenticate_stage(_r8r27_stage(args, cfg), cfg["source_r8r27"], r8r14=False)
    with _r28_stage_for_ind14():
        recomputed = ind14._recompute_preflight(args, cfg, source_ctx, expected_specs, sources)
    recomputed["passed"] = bool(
        recomputed["spec_count"] == 64
        and recomputed["level_construction_count"] == 256
        and recomputed["level_construction_pass_count"] == 256
        and recomputed["refresh_construction_count"] == 1408
        and recomputed["refresh_construction_pass_count"] == 1408
        and all(row["passed"] for row in recomputed["rows"])
    )
    primary_preflight = _read(stage / "analysis/offline_timing_preflight.json")
    primary_path = stage / "analysis/offline_primary.json"
    primary = _read(primary_path)
    specs_exact = saved_specs == expected_specs
    construction_exact = recomputed == primary_preflight
    outcome = bool(
        primary.get("passed") is True
        and int(primary.get("spec_count", -1)) == 64
        and int(primary.get("level_construction_pass_count", -1)) == 256
        and int(primary.get("refresh_construction_pass_count", -1)) == 1408
    )
    result = {
        "schema_version": 1,
        "stage": STAGE,
        "audit_kind": "offline_independent",
        "source_r8r7_authenticated": bool(source_r8r7["passed"]),
        "source_r8r14_authenticated": bool(source_r8r14["passed"]),
        "source_r8r27_authenticated": bool(source_r8r27["passed"]),
        "spec_count": len(expected_specs),
        "specs_exact": specs_exact,
        "level_construction_count": recomputed["level_construction_count"],
        "refresh_construction_count": recomputed["refresh_construction_count"],
        "construction_exact": construction_exact,
        "primary_outcome_agreement": outcome,
        "primary_sha256": _sha(primary_path),
        "real_tsc_executed": False,
        "new_raw_count": 0,
        "passed": bool(
            source_r8r7["passed"]
            and source_r8r14["passed"]
            and source_r8r27["passed"]
            and specs_exact
            and recomputed["passed"]
            and construction_exact
            and outcome
        ),
    }
    _write(stage / "analysis/offline_independent.json", result)
    return result


def raw_audit(args: argparse.Namespace, cfg: Mapping[str, Any], phase: str) -> dict[str, Any]:
    stage = _stage(args)
    source_ctx = _source_context(args, cfg)
    specs = [row for row in _expected_specs(args, cfg, source_ctx) if row["partition"] == phase]
    _, sources = _source_baselines(args, cfg, source_ctx)
    contract = cfg["controller_contract"]
    rows = []
    for spec in specs:
        result = _gzip(stage / "raw" / phase / f"{spec['experiment_id']}.json.gz")
        trajectory, trace = result.get("trajectory") or [], result.get("controller_trace") or []
        horizon = int(spec["horizon_steps"])
        full = len(trajectory) == horizon + 1 and len(trace) == horizon
        source = sources[str(spec["source_r8r7_baseline_experiment_id"])]
        prefix_state = bool(
            full
            and all(
                r8r7.r8.r4._semantic_state(current) == r8r7.r8.r4._semantic_state(reference)
                for current, reference in zip(trajectory[: PREFIX_END + 1], source["trajectory"][: PREFIX_END + 1])
            )
        )
        prefix_trace = bool(
            full
            and all(
                ind14._source_trace_projection(reference, current)
                for current, reference in zip(trace[:PREFIX_END], source["controller_trace"][:PREFIX_END])
            )
        )
        calibration = bool(full and r8r7.r8.r4._calibration_exact(trace))
        decisions = set(map(int, spec["r8r28_decision_task_steps"]))
        names = [trace[step].get("r3c3t13s24d1r14r8r14_event") for step in range(PREFIX_END, horizon)] if full else []
        events = [trace[step].get("r3c3t13s24d1r14r8r14_event_detail") or {} for step in range(PREFIX_END, horizon)] if full else []
        event_exact = bool(
            full
            and all(
                name == ("staircase_issue" if step in decisions else "staircase_refresh")
                and event.get("passed") is True
                and all(bool(value) for value in (event.get("criteria") or {}).values())
                for step, name, event in zip(range(PREFIX_END, horizon), names, events)
            )
        )
        active, target_chain = None, event_exact
        if event_exact:
            for name, event in zip(names, events):
                if name == "staircase_issue":
                    active = list(event.get("target_card15_fields") or [])
                elif list(event.get("stored_target_card15_fields") or []) != active:
                    target_chain = False
        actions = np.asarray([row.get("action_norm_tsc", []) for row in trace], dtype=float)
        currents = np.asarray([row.get("currents_a_tsc", []) for row in trajectory], dtype=float)
        finite = bool(
            full
            and actions.shape == (horizon, N_COILS)
            and currents.shape == (horizon + 1, N_COILS)
            and np.all(np.isfinite(actions))
            and np.all(np.isfinite(currents))
            and all(math.isfinite(float(row[key])) for row in trajectory for key in ("R", "Z", "Ip"))
            and all(np.all(np.isfinite(np.asarray(row.get("wire_currents_a", []), dtype=float))) for row in trajectory)
            and not any(bool(row.get("abnormal")) for row in trajectory)
        )
        forbidden = sum(
            any(
                bool(row.get(key))
                for key in (
                    "r3c3t13s24d1r14r8r14_forbidden_input_used",
                    "r3c3t13s24d1r14r8r14_pair_or_history_label_used",
                    "r3c3t13s24d1r14r8r14_future_measurement_used",
                    "r3c3t13s24d1r14r8r14_future_action_used",
                    "r3c3t13s24d1r14r8r14_source_result_used",
                    "r3c3t13s24d1r14r8r14_hidden_wire_used",
                )
            )
            for row in trace
        )
        payload = _read(stage / "variants" / f"payload_{spec['experiment_id']}.json")
        minimum, maximum = r8r7.r8.d1r11.s21.s13._current_limits_tsc(payload)
        center, half = 0.5 * (minimum + maximum), 0.5 * (maximum - minimum)
        utilization = float(np.max(np.abs((currents - center) / half))) if currents.shape == (horizon + 1, N_COILS) else None
        issues = [event for name, event in zip(names, events) if name == "staircase_issue"]
        refreshes = [event for name, event in zip(names, events) if name == "staircase_refresh"]
        issue_increment = max((float(row["incremental_normalized_action_linf"]) for row in issues), default=None)
        refresh_increment = max((float(row["incremental_normalized_action_linf"]) for row in refreshes), default=None)
        passed = bool(
            result.get("success")
            and full
            and prefix_state
            and prefix_trace
            and calibration
            and event_exact
            and target_chain
            and len(issues) == 4
            and len(refreshes) == horizon - PREFIX_END - 4
            and finite
            and forbidden == 0
            and issue_increment is not None
            and issue_increment <= float(contract["maximum_incremental_normalized_action_linf"]) + 1e-12
            and refresh_increment is not None
            and refresh_increment <= float(contract["maximum_incremental_normalized_action_linf"]) + 1e-12
            and utilization is not None
            and utilization <= float(contract["maximum_current_utilization"]) + 1e-12
        )
        rows.append(
            {
                "experiment_id": spec["experiment_id"],
                "pair_id": spec["pair_id"],
                "history_member": spec["history_member"],
                "grid_id": spec["r8r28_grid_id"],
                "sequence_id": spec["r8r28_sequence_id"],
                "runtime_success": bool(result.get("success")),
                "full_horizon": full,
                "source_prefix_state_exact": prefix_state,
                "source_prefix_trace_exact": prefix_trace,
                "calibration_exact": calibration,
                "event_exact": event_exact,
                "target_chain_exact": target_chain,
                "issue_count": len(issues),
                "refresh_count": len(refreshes),
                "finite": finite,
                "forbidden_trace_count": forbidden,
                "maximum_issue_increment": issue_increment,
                "maximum_refresh_increment": refresh_increment,
                "maximum_current_utilization": utilization,
                "failure_reason": str(result.get("failure_reason") or ""),
                "passed": passed,
            }
        )
    inventory = _inventory(stage / "raw" / phase)
    primary_path = stage / "analysis" / f"{phase}_raw_primary.json"
    primary = _read(primary_path)
    expected = {"safety": 16, "qualification": 48}[phase]
    aggregate = {
        "expected_raw_count": expected,
        "raw_inventory": inventory,
        "runtime_success_count": sum(bool(row["runtime_success"]) for row in rows),
        "full_horizon_count": sum(bool(row["full_horizon"]) for row in rows),
        "source_prefix_state_exact_count": sum(bool(row["source_prefix_state_exact"]) for row in rows),
        "source_prefix_trace_exact_count": sum(bool(row["source_prefix_trace_exact"]) for row in rows),
        "calibration_exact_count": sum(bool(row["calibration_exact"]) for row in rows),
        "event_exact_count": sum(bool(row["event_exact"]) for row in rows),
        "target_chain_exact_count": sum(bool(row["target_chain_exact"]) for row in rows),
        "issue_count": sum(int(row["issue_count"]) for row in rows),
        "refresh_count": sum(int(row["refresh_count"]) for row in rows),
        "finite_count": sum(bool(row["finite"]) for row in rows),
        "forbidden_trace_count": sum(int(row["forbidden_trace_count"]) for row in rows),
        "maximum_issue_increment": max((float(row["maximum_issue_increment"]) for row in rows if row["maximum_issue_increment"] is not None), default=None),
        "maximum_refresh_increment": max((float(row["maximum_refresh_increment"]) for row in rows if row["maximum_refresh_increment"] is not None), default=None),
        "maximum_current_utilization": max((float(row["maximum_current_utilization"]) for row in rows if row["maximum_current_utilization"] is not None), default=None),
        "passed_count": sum(bool(row["passed"]) for row in rows),
        "rows": rows,
    }
    agreement = all(primary.get(key) == value for key, value in aggregate.items())
    result = {
        "schema_version": 1,
        "stage": STAGE,
        "audit_kind": f"{phase}_raw_independent",
        "phase": phase,
        **aggregate,
        "primary_sha256": _sha(primary_path),
        "primary_agreement": agreement,
        "passed": bool(len(rows) == expected and aggregate["passed_count"] == expected and agreement),
    }
    _write(stage / "analysis" / f"{phase}_raw_independent.json", result)
    return result


def _formal_recompute(args: argparse.Namespace, cfg: Mapping[str, Any]) -> dict[str, Any]:
    stage = _stage(args)
    source_ctx = _source_context(args, cfg)
    baseline_specs, baseline_results = _source_baselines(args, cfg, source_ctx)
    specs = _expected_specs(args, cfg, source_ctx)
    evaluators, _ = r8r7.r8.d1r11._formal_callback(source_ctx.r8_ctx.d1r11_ctx, baseline_specs)
    evaluator_by_context = {
        (str(spec["pair_id"]), str(spec["history_member"])): evaluators[str(spec["experiment_id"])]
        for spec in baseline_specs
    }
    rows = []
    for spec in baseline_specs:
        rows.append(
            ind11._formal_row(
                evaluators[str(spec["experiment_id"])],
                baseline_results[str(spec["experiment_id"])],
                {
                    "kind": "baseline",
                    "source": "R8R7",
                    "experiment_id": spec["experiment_id"],
                    "pair_id": spec["pair_id"],
                    "history_member": spec["history_member"],
                    "grid_id": "baseline",
                    "sequence_id": "baseline",
                },
            )
        )
    for spec in specs:
        rows.append(
            ind11._formal_row(
                evaluator_by_context[(str(spec["pair_id"]), str(spec["history_member"]))],
                _gzip(stage / "raw" / str(spec["partition"]) / f"{spec['experiment_id']}.json.gz"),
                {
                    "kind": "candidate",
                    "source": "R8R28",
                    "experiment_id": spec["experiment_id"],
                    "pair_id": spec["pair_id"],
                    "history_member": spec["history_member"],
                    "grid_id": spec["r8r28_grid_id"],
                    "sequence_id": spec["r8r28_sequence_id"],
                },
            )
        )
    tolerance = float(cfg["formal_contract"]["metric_equivalence_absolute_tolerance"])
    equivalence = all(
        row["formal_contract_pass"] == row["existing_pass"]
        and row["formal_best_arrival_ms"] == row["existing_arrival_ms"]
        and float(row["maximum_margin_abs_difference"]) <= tolerance
        for row in rows
    )
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault((str(row["pair_id"]), str(row["history_member"])), []).append(row)
    expected_members = {("g3", "UUUU"), ("g3", "VVVV"), ("g2", "UUUU"), ("g2", "VVVV")}
    contexts = []
    for key, group in sorted(groups.items()):
        baseline = [row for row in group if row["kind"] == "baseline"]
        candidates = [row for row in group if row["kind"] == "candidate"]
        members = {(str(row["grid_id"]), str(row["sequence_id"])) for row in candidates}
        if len(baseline) != 1 or len(candidates) != 4 or members != expected_members:
            raise ValueError("independent R8R28 formal context coverage changed")
        base = baseline[0]
        oracle = max(
            [base, *candidates],
            key=lambda row: (float(row["formal_minimum_signed_margin"]), float(row["formal_mean_signed_margin"]), row["kind"] == "baseline"),
        )
        best = max(
            candidates,
            key=lambda row: (float(row["formal_minimum_signed_margin"]), float(row["formal_mean_signed_margin"]), str(row["grid_id"]), str(row["sequence_id"])),
        )
        contexts.append(
            {
                "pair_id": key[0],
                "history_member": key[1],
                "baseline": base,
                "candidates": sorted(candidates, key=lambda row: (str(row["grid_id"]), str(row["sequence_id"]))),
                "best_candidate": best,
                "best_candidate_minimum_margin_gain": float(best["formal_minimum_signed_margin"]) - float(base["formal_minimum_signed_margin"]),
                "failed_baseline_repaired": bool(not base["formal_contract_pass"] and any(row["formal_contract_pass"] for row in candidates)),
                "held_oracle_formal_pass": bool(oracle["formal_contract_pass"]),
                "held_oracle_experiment_id": oracle["experiment_id"],
            }
        )
    baseline_pass = sum(bool(row["baseline"]["formal_contract_pass"]) for row in contexts)
    repairs = sum(bool(row["failed_baseline_repaired"]) for row in contexts)
    oracle_pass = sum(bool(row["held_oracle_formal_pass"]) for row in contexts)
    gains = [float(row["best_candidate_minimum_margin_gain"]) for row in contexts if not row["baseline"]["formal_contract_pass"]]
    gate = cfg["scientific_gate"]
    scientific = bool(
        baseline_pass == int(gate["required_baseline_formal_pass_count"])
        and len(contexts) - baseline_pass == int(gate["required_failed_baseline_count"])
        and repairs >= int(gate["minimum_repaired_failed_baseline_count"])
        and oracle_pass >= int(gate["minimum_held_oracle_formal_pass_count"])
        and oracle_pass > baseline_pass
    )
    candidate_summaries = []
    for grid_id, sequence_id in sorted(expected_members):
        selected = [row for row in rows if row["kind"] == "candidate" and row["grid_id"] == grid_id and row["sequence_id"] == sequence_id]
        candidate_summaries.append(
            {
                "grid_id": grid_id,
                "sequence_id": sequence_id,
                "context_count": len(selected),
                "formal_pass_count": sum(bool(row["formal_contract_pass"]) for row in selected),
                "repaired_failed_baseline_count": sum(
                    not context["baseline"]["formal_contract_pass"]
                    and next(row for row in context["candidates"] if row["grid_id"] == grid_id and row["sequence_id"] == sequence_id)["formal_contract_pass"]
                    for context in contexts
                ),
                "baseline_pass_regression_count": sum(
                    context["baseline"]["formal_contract_pass"]
                    and not next(row for row in context["candidates"] if row["grid_id"] == grid_id and row["sequence_id"] == sequence_id)["formal_contract_pass"]
                    for context in contexts
                ),
            }
        )
    return {
        "row_count": len(rows),
        "formal_metric_equivalence_passed": equivalence,
        "maximum_margin_abs_difference": max(float(row["maximum_margin_abs_difference"]) for row in rows),
        "context_count": len(contexts),
        "baseline_formal_pass_count": baseline_pass,
        "failed_baseline_count": len(contexts) - baseline_pass,
        "new_candidate_formal_pass_count": sum(bool(row["formal_contract_pass"]) for row in rows if row["source"] == "R8R28"),
        "repaired_failed_baseline_count": repairs,
        "held_oracle_formal_pass_count": oracle_pass,
        "failed_baseline_best_candidate_margin_gain": {"minimum": min(gains), "median": statistics.median(gains), "maximum": max(gains)},
        "candidate_summaries": candidate_summaries,
        "scientific_gate_passed": scientific,
    }


def final_audit(args: argparse.Namespace, cfg: Mapping[str, Any]) -> dict[str, Any]:
    stage = _stage(args)
    recomputed = _formal_recompute(args, cfg)
    integrity = bool(
        recomputed["formal_metric_equivalence_passed"]
        and recomputed["row_count"] == 80
        and recomputed["context_count"] == 16
    )
    scientific = bool(integrity and recomputed["scientific_gate_passed"])
    route = cfg["routes"]["pass" if scientific else "authority_fail"]
    primary_path = stage / "analysis/primary_summary.json"
    primary = _read(primary_path)
    numerical = bool(
        float(primary["maximum_margin_abs_difference"]) == recomputed["maximum_margin_abs_difference"]
        and primary["failed_baseline_best_candidate_margin_gain"] == recomputed["failed_baseline_best_candidate_margin_gain"]
        and primary["candidate_summaries"] == recomputed["candidate_summaries"]
    )
    outcome = bool(
        int(primary["baseline_formal_pass_count"]) == recomputed["baseline_formal_pass_count"]
        and int(primary["failed_baseline_count"]) == recomputed["failed_baseline_count"]
        and int(primary["new_candidate_formal_pass_count"]) == recomputed["new_candidate_formal_pass_count"]
        and int(primary["repaired_failed_baseline_count"]) == recomputed["repaired_failed_baseline_count"]
        and int(primary["held_oracle_formal_pass_count"]) == recomputed["held_oracle_formal_pass_count"]
        and bool(primary["scientific_gate_passed"]) == scientific
        and bool(primary["integrity_gate_passed"]) == integrity
        and bool(primary["formal_metric_equivalence_passed"]) == recomputed["formal_metric_equivalence_passed"]
    )
    result = {
        "schema_version": 1,
        "stage": STAGE,
        "audit_kind": "final_independent",
        "integrity_gate_passed": integrity,
        **recomputed,
        "scientific_gate_passed": scientific,
        "route": route,
        "primary_sha256": _sha(primary_path),
        "primary_route_agreement": primary.get("route") == route,
        "primary_outcome_agreement": outcome,
        "primary_numerical_agreement": numerical,
        "passed": bool(integrity and primary.get("route") == route and outcome and numerical),
    }
    _write(stage / "analysis/final_independent.json", result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("config", "r8r7-run", "r8r14-run", "r8r27-run", "r8-run", "r8r1-output", "r8r6-run"):
        parser.add_argument(f"--{name}", dest=name.replace("-", "_"), type=Path, required=True)
    for name in (
        "source-d1r11-run", "source-r2-run", "source-r4-run", "source-r6-run",
        "source-s21-run", "source-s23r1-output", "source-s24-run", "source-d1r9-v1",
        "source-d1r9-v2", "source-d1r10-run", "source-d1r10-audit", "source-stage42r3b-run",
        "source-stage42r3c3-run", "source-stage42r3c3-bank-dir", "source-stage42r3c3t1-run",
        "source-stage42r3c3t1-audit-dir", "source-stage42r3c3t3-controller-bank", "q1-run",
        "q2-run", "q1-audit", "q2-audit", "r3b-server-audit", "r3b-snapshot-checks",
    ):
        parser.add_argument(f"--{name}", dest=name.replace("-", "_"), type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--audit-kind", choices=("offline", "safety_raw", "qualification_raw", "final"), required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    cfg = _read(args.config.expanduser().resolve())
    if cfg.get("stage") != STAGE or cfg.get("identity") != IDENTITY:
        raise ValueError("independent R8R28 configuration identity changed")
    if args.audit_kind == "offline":
        result = offline_audit(args, cfg)
    elif args.audit_kind in {"safety_raw", "qualification_raw"}:
        result = raw_audit(args, cfg, args.audit_kind.removesuffix("_raw"))
    else:
        result = final_audit(args, cfg)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
