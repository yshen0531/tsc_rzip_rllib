#!/usr/bin/env python3
"""Structurally independent R8R12 source, action, raw, and formal forensics."""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.control import causal_discrete_pulse_mpc as mpc
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_campaign as r8r7,
    stage4_2r3c3t13s24d1r14r8r9_measured_multipulse_authority_audit as r8r9,
)
from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r11_independent_forensics as ind11,
)


STAGE = "Stage4.2R3c3T13S24D1R14R8R12"
IDENTITY = "causal_cumulative_direction2_staircase_authority_sentinel_v1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r12_causal_cumulative_direction2_staircase_authority_sentinel"
CONTROLLER_REVISION = "causal_cumulative_direction2_staircase_v42r3c3t13s24d1r14r8r12_v1"
PREFIX_END = 10
N_COILS = 14
PHASES = ("safety", "qualification")
SOURCE_WRAPPER_METADATA_PREFIXES = (
    "r3c3t13s24d1r14r4_",
    "r3c3t13s24d1r14r8r7_",
)


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


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _inventory(path: Path) -> dict[str, Any]:
    files = sorted(path.glob("*.json.gz"), key=lambda value: value.name)
    digest = hashlib.sha256()
    rows = []
    for file in files:
        size = file.stat().st_size
        sha = _sha(file)
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
    return args.r8r7_run.expanduser().resolve() / str(
        cfg["source_r8r7"]["stage_directory"]
    )


def _r8r11_stage(args: argparse.Namespace, cfg: Mapping[str, Any]) -> Path:
    return args.r8r11_run.expanduser().resolve() / str(
        cfg["source_r8r11"]["stage_directory"]
    )


def _source_context(args: argparse.Namespace, cfg: Mapping[str, Any]) -> r8r7.Context:
    source_args = argparse.Namespace(**vars(args))
    source_args.config = (_root() / str(cfg["source_r8r7_config"])).resolve()
    source_args.run_dir = args.r8r7_run.expanduser().resolve()
    return r8r7.load_context(source_args)


def _source_baselines(
    args: argparse.Namespace, cfg: Mapping[str, Any], source_ctx: r8r7.Context
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    specs = [copy.deepcopy(row) for row in r8r7._phase_specs(source_ctx, "baseline")]
    ordered = tuple(map(str, cfg["context_contract"]["ordered_pairs"]))
    histories = tuple(map(str, cfg["context_contract"]["histories"]))
    order = {
        (pair, history): (pair_index, history_index)
        for pair_index, pair in enumerate(ordered)
        for history_index, history in enumerate(histories)
    }
    specs.sort(key=lambda row: order[(str(row["pair_id"]), str(row["history_member"]))])
    if len(specs) != 16 or {
        (str(row["pair_id"]), str(row["history_member"])) for row in specs
    } != set(order):
        raise ValueError("independent R8R12 source coverage changed")
    source = _source_stage(args, cfg)
    results = {
        str(row["experiment_id"]): _gzip(
            source / "raw" / "baseline" / f"{row['experiment_id']}.json.gz"
        )
        for row in specs
    }
    return specs, results


def _expected_specs(
    args: argparse.Namespace, cfg: Mapping[str, Any], source_ctx: r8r7.Context
) -> list[dict[str, Any]]:
    baselines, _ = _source_baselines(args, cfg, source_ctx)
    safety = set(map(str, cfg["context_contract"]["safety_pairs"]))
    requested = np.asarray(cfg["schedule_contract"]["canonical_matrix_columns"], dtype=float)[:, 2]
    output = []
    for index, source in enumerate(baselines):
        phase = "safety" if str(source["pair_id"]) in safety else "qualification"
        row = copy.deepcopy(source)
        row.update(
            {
                "kind": "stage4_2r3c3t13s24d1r14r8r12_causal_cumulative_direction2_staircase",
                "stage": STAGE,
                "campaign_identity": IDENTITY,
                "controller_revision": CONTROLLER_REVISION,
                "partition": phase,
                "experiment_id": f"r8r12_{phase}_{index:02d}",
                "source_r8r7_baseline_experiment_id": str(source["experiment_id"]),
                "r8r12_role": "causal_cumulative_direction2_staircase",
                "r8r12_direction_index": 2,
                "r8r12_sign": 1,
                "r8r12_canonical_scale": 1.0,
                "r8r12_requested_coordinate": requested.tolist(),
                "r8r12_matrix_digest": str(
                    cfg["schedule_contract"]["canonical_matrix_float64_le_c_sha256"]
                ),
                "r8r12_decision_task_steps": list(
                    map(int, cfg["schedule_contract"]["decision_task_steps"])
                ),
                "r8r12_allowed_in_expert_dataset": False,
                "pair_or_history_label_available_to_controller": False,
                "source_result_available_to_controller": False,
                "future_measurement_count": 0,
                "future_action_count": 0,
                "formal_timing_unchanged": True,
            }
        )
        output.append(row)
    return output


def _authenticate_r8r11(
    args: argparse.Namespace, cfg: Mapping[str, Any]
) -> dict[str, Any]:
    stage = _r8r11_stage(args, cfg)
    expected = cfg["source_r8r11"]
    paths = {
        "primary_summary": stage / "analysis" / "primary_summary.json",
        "final_independent": stage / "analysis" / "final_independent.json",
        "final_report": stage / "analysis" / "final_report.json",
        "manifest": stage / "stage_manifest.json",
        "state": stage / "stage_state.json",
    }
    hashes = {name: _sha(path) for name, path in paths.items()}
    for name, key in (
        ("primary_summary", "primary_summary_sha256"),
        ("final_independent", "final_independent_sha256"),
        ("final_report", "final_report_sha256"),
        ("manifest", "stage_manifest_sha256"),
        ("state", "stage_state_sha256"),
    ):
        if hashes[name] != expected[key]:
            raise ValueError(f"independent R8R12 R8R11 {name} changed")
    final = _read(paths["final_report"])
    state = _read(paths["state"])
    inventories = {phase: _inventory(stage / "raw" / phase) for phase in PHASES}
    for phase in PHASES:
        current = inventories[phase]
        if (
            current["count"] != int(expected[f"{phase}_raw_count"])
            or current["bytes"] != int(expected[f"{phase}_raw_bytes"])
            or current["digest"] != expected[f"{phase}_raw_digest"]
        ):
            raise ValueError(f"independent R8R12 R8R11 {phase} raw changed")
    passed = bool(
        final.get("route") == expected["required_route"]
        and final.get("passed") is False
        and state.get("finished") is True
        and (state.get("verdict") or {}).get("route") == expected["required_route"]
    )
    return {
        "stage": str(stage),
        "hashes": hashes,
        "inventories": inventories,
        "required_route": expected["required_route"],
        "passed": passed,
    }


def _execution_context(source_ctx: r8r7.Context, stage: Path) -> Any:
    paths = type("Paths", (), {"variants": stage / "variants"})()
    return r8r7.r8.Context(
        cfg=source_ctx.r8_cfg,
        config_path=source_ctx.r8_config_path,
        d1r11_ctx=source_ctx.r8_ctx.d1r11_ctx,
        source_d1r11_run=source_ctx.r8_ctx.source_d1r11_run,
        source_response_runs=source_ctx.r8_ctx.source_response_runs,
        paths=paths,
    )


def _fixed_basis(result: Mapping[str, Any]) -> np.ndarray:
    values = [
        row.get("r3c3t13s16_fixed_basis_delta_field_kAt_tsc")
        for row in result["controller_trace"][:11]
        if row.get("r3c3t13s16_fixed_basis_delta_field_kAt_tsc")
    ]
    if not values or any(value != values[0] for value in values[1:]):
        raise ValueError("independent R8R12 fixed basis changed")
    matrix = np.asarray(values[0], dtype=float).T
    if matrix.shape != (N_COILS, 4) or not np.all(np.isfinite(matrix)):
        raise ValueError("independent R8R12 fixed basis invalid")
    return matrix


def _refresh(
    *,
    task_step: int,
    currents: np.ndarray,
    target_fields: Sequence[str],
    actuator: Any,
    lattice: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    stored = tuple(map(str, target_fields))
    chosen = r8r7.r8.d1r11.s21.s16.s9.exact_stored_center_action(
        stored_fields=stored,
        measured_current_a_tsc=currents,
        baseline_action_norm_tsc=np.zeros(N_COILS),
        turns_tsc=actuator.turns_tsc,
        max_slew_step_a=actuator.max_slew_step_a,
        minimum_current_a_tsc=actuator.minimum_current_a_tsc,
        maximum_current_a_tsc=actuator.maximum_current_a_tsc,
        cfg=lattice,
    )
    applied = actuator.apply(currents, chosen["action_norm_tsc"])
    criteria = {
        "finite": bool(np.all(np.isfinite(currents))),
        "target_exact": list(applied.card15_fields) == list(stored),
        "exact_fields": all(len(field) == 10 for field in stored),
        "no_saturation": not any(applied.action_saturated),
        "no_current_clip": not any(applied.current_limit_clipped),
        "incremental_action": float(chosen["incremental_normalized_action_linf"])
        <= float(contract["maximum_incremental_normalized_action_linf"]) + 1e-12,
        "total_action": float(chosen["total_normalized_action_abs"])
        <= float(contract["maximum_total_normalized_action_abs"]) + 1e-12,
        "current_utilization": float(chosen["predicted_maximum_current_utilization"])
        <= float(contract["maximum_current_utilization"]) + 1e-12,
        "actuator_gate": bool(chosen["passed"]),
    }
    return {
        "task_step": task_step,
        "target_card15_fields": list(stored),
        "action_norm_tsc": list(map(float, chosen["action_norm_tsc"])),
        "incremental_normalized_action_linf": float(
            chosen["incremental_normalized_action_linf"]
        ),
        "predicted_current_utilization": float(
            chosen["predicted_maximum_current_utilization"]
        ),
        "criteria": criteria,
        "nominal_readback_current_a_tsc": list(applied.nominal_readback_current_a_tsc),
        "passed": bool(all(criteria.values())),
    }


def _recompute_preflight(
    args: argparse.Namespace,
    cfg: Mapping[str, Any],
    source_ctx: r8r7.Context,
    specs: Sequence[Mapping[str, Any]],
    sources: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    stage = _stage(args)
    execution = _execution_context(source_ctx, stage)
    lattice = execution.d1r11_ctx.base_ctx.base_ctx.cfg["lattice_probe"]
    candidate = mpc.Candidate("direction2_plus", 2, 1, 1.0)
    controller = copy.deepcopy(cfg["controller_contract"])
    controller["dynamic_exact_search_radius"] = int(
        cfg["schedule_contract"]["dynamic_exact_search_radius"]
    )
    rows = []
    for spec in specs:
        source = sources[str(spec["source_r8r7_baseline_experiment_id"])]
        payload = _read(stage / "variants" / f"payload_{spec['experiment_id']}.json")
        actuator = mpc.actuator_from_payload(payload, lattice)
        current = np.asarray(source["trajectory"][PREFIX_END]["currents_a_tsc"], dtype=float)
        basis = _fixed_basis(source).T
        decisions = tuple(map(int, spec["r8r12_decision_task_steps"]))
        levels = []
        horizon = int(spec["horizon_steps"])
        for level, decision in enumerate(decisions, start=1):
            issue = mpc.construct_issue(
                task_step=decision,
                currents_a_tsc=current,
                fixed_basis_delta_field_kat_tsc=basis,
                candidate=candidate,
                canonical_matrix_columns=cfg["schedule_contract"]["canonical_matrix_columns"],
                actuator=actuator,
                controller_cfg=controller,
                lattice_cfg=lattice,
            )
            current = np.asarray(issue["nominal_issue_readback_current_a_tsc"], dtype=float)
            next_decision = decisions[level] if level < len(decisions) else horizon
            refreshes = []
            for task_step in range(decision + 1, next_decision):
                refresh = _refresh(
                    task_step=task_step,
                    currents=current,
                    target_fields=issue["target_card15_fields"],
                    actuator=actuator,
                    lattice=lattice,
                    contract=cfg["controller_contract"],
                )
                current = np.asarray(refresh["nominal_readback_current_a_tsc"], dtype=float)
                refreshes.append({key: refresh[key] for key in (
                    "task_step", "target_card15_fields", "action_norm_tsc",
                    "incremental_normalized_action_linf", "predicted_current_utilization",
                    "criteria", "passed",
                )})
            levels.append(
                {
                    "level": level,
                    "decision_task_step": decision,
                    "center_card15_fields": issue["center_card15_fields"],
                    "target_card15_fields": issue["target_card15_fields"],
                    "action_norm_tsc": issue["action_norm_tsc"],
                    "integer_grid_steps_tsc": issue["integer_grid_steps_tsc"],
                    "incremental_normalized_action_linf": issue[
                        "incremental_normalized_action_linf"
                    ],
                    "predicted_current_utilization": issue[
                        "predicted_current_utilization"
                    ],
                    "desired_applied_current_cosine": issue[
                        "desired_applied_current_cosine"
                    ],
                    "relative_off_basis_residual": issue[
                        "relative_off_basis_residual"
                    ],
                    "criteria": issue["criteria"],
                    "refreshes": refreshes,
                    "passed": bool(issue["passed"] and all(row["passed"] for row in refreshes)),
                }
            )
        rows.append(
            {
                "experiment_id": spec["experiment_id"],
                "pair_id": spec["pair_id"],
                "history_member": spec["history_member"],
                "partition": spec["partition"],
                "levels": levels,
                "passed": all(level["passed"] for level in levels),
            }
        )
    issue_levels = [level for row in rows for level in row["levels"]]
    refreshes = [refresh for level in issue_levels for refresh in level["refreshes"]]
    return {
        "spec_count": len(rows),
        "level_construction_count": len(issue_levels),
        "level_construction_pass_count": sum(bool(row["passed"]) for row in issue_levels),
        "refresh_construction_count": len(refreshes),
        "refresh_construction_pass_count": sum(bool(row["passed"]) for row in refreshes),
        "maximum_issue_increment": max(
            float(row["incremental_normalized_action_linf"]) for row in issue_levels
        ),
        "maximum_refresh_increment": max(
            float(row["incremental_normalized_action_linf"]) for row in refreshes
        ),
        "maximum_predicted_current_utilization": max(
            [float(row["predicted_current_utilization"]) for row in issue_levels]
            + [float(row["predicted_current_utilization"]) for row in refreshes]
        ),
        "rows": rows,
        "passed": bool(len(rows) == 16 and all(row["passed"] for row in rows)),
    }


def offline_audit(args: argparse.Namespace, cfg: Mapping[str, Any]) -> dict[str, Any]:
    stage = _stage(args)
    source_ctx = _source_context(args, cfg)
    specs, sources = _source_baselines(args, cfg, source_ctx)
    expected_specs = _expected_specs(args, cfg, source_ctx)
    saved_specs = _read(stage / "specs" / "all_specs.json")
    source_r8r7 = r8r9._authenticate_r8r7(_source_stage(args, cfg), cfg)
    source_r8r11 = _authenticate_r8r11(args, cfg)
    recomputed = _recompute_preflight(
        args, cfg, source_ctx, expected_specs, sources
    )
    primary_preflight = _read(stage / "analysis" / "offline_cumulative_preflight.json")
    primary_path = stage / "analysis" / "offline_primary.json"
    primary = _read(primary_path)
    specs_exact = saved_specs == expected_specs and len(specs) == len(expected_specs)
    construction_exact = recomputed == primary_preflight
    outcome = bool(
        primary.get("passed") is True
        and int(primary.get("spec_count", -1)) == 16
        and int(primary.get("level_construction_pass_count", -1)) == 64
        and int(primary.get("refresh_construction_pass_count", -1))
        == int(recomputed["refresh_construction_count"])
    )
    result = {
        "schema_version": 1,
        "stage": STAGE,
        "audit_kind": "offline_independent",
        "source_r8r7_authenticated": bool(source_r8r7["passed"]),
        "source_r8r11_authenticated": bool(source_r8r11["passed"]),
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
            and source_r8r11["passed"]
            and specs_exact
            and recomputed["passed"]
            and construction_exact
            and outcome
        ),
    }
    _write(stage / "analysis" / "offline_independent.json", result)
    return result


def _source_trace_projection(
    source: Mapping[str, Any], current: Mapping[str, Any]
) -> bool:
    return all(
        current.get(key) == value
        for key, value in source.items()
        if not key.startswith(SOURCE_WRAPPER_METADATA_PREFIXES)
    )


def raw_audit(
    args: argparse.Namespace, cfg: Mapping[str, Any], phase: str
) -> dict[str, Any]:
    stage = _stage(args)
    source_ctx = _source_context(args, cfg)
    expected_specs = _expected_specs(args, cfg, source_ctx)
    specs = [row for row in expected_specs if row["partition"] == phase]
    _, sources = _source_baselines(args, cfg, source_ctx)
    decisions = set(map(int, cfg["schedule_contract"]["decision_task_steps"]))
    rows = []
    for spec in specs:
        result = _gzip(stage / "raw" / phase / f"{spec['experiment_id']}.json.gz")
        trajectory = result.get("trajectory") or []
        trace = result.get("controller_trace") or []
        horizon = int(spec["horizon_steps"])
        full = len(trajectory) == horizon + 1 and len(trace) == horizon
        source = sources[str(spec["source_r8r7_baseline_experiment_id"])]
        prefix_state = bool(
            full
            and all(
                r8r7.r8.r4._semantic_state(current)
                == r8r7.r8.r4._semantic_state(reference)
                for current, reference in zip(
                    trajectory[: PREFIX_END + 1], source["trajectory"][: PREFIX_END + 1]
                )
            )
        )
        prefix_trace = bool(
            full
            and all(
                _source_trace_projection(reference, current)
                for current, reference in zip(
                    trace[:PREFIX_END], source["controller_trace"][:PREFIX_END]
                )
            )
        )
        calibration = bool(full and r8r7.r8.r4._calibration_exact(trace))
        names = [
            trace[step].get("r3c3t13s24d1r14r8r12_event")
            for step in range(PREFIX_END, horizon)
        ] if full else []
        events = [
            trace[step].get("r3c3t13s24d1r14r8r12_event_detail") or {}
            for step in range(PREFIX_END, horizon)
        ] if full else []
        event_exact = bool(
            full
            and all(
                name == ("staircase_issue" if step in decisions else "staircase_refresh")
                and event.get("passed") is True
                and all(bool(value) for value in (event.get("criteria") or {}).values())
                for step, name, event in zip(range(PREFIX_END, horizon), names, events)
            )
        )
        active = None
        target_chain = event_exact
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
            and all(
                math.isfinite(float(row[key])) for row in trajectory for key in ("R", "Z", "Ip")
            )
            and all(
                np.all(np.isfinite(np.asarray(row.get("wire_currents_a", []), dtype=float)))
                for row in trajectory
            )
            and not any(bool(row.get("abnormal")) for row in trajectory)
        )
        forbidden = sum(
            any(
                bool(row.get(key))
                for key in (
                    "r3c3t13s24d1r14r8r12_forbidden_input_used",
                    "r3c3t13s24d1r14r8r12_pair_or_history_label_used",
                    "r3c3t13s24d1r14r8r12_future_measurement_used",
                    "r3c3t13s24d1r14r8r12_future_action_used",
                    "r3c3t13s24d1r14r8r12_source_result_used",
                    "r3c3t13s24d1r14r8r12_hidden_wire_used",
                )
            )
            for row in trace
        )
        payload = _read(stage / "variants" / f"payload_{spec['experiment_id']}.json")
        minimum, maximum = r8r7.r8.d1r11.s21.s13._current_limits_tsc(payload)
        center, half = 0.5 * (minimum + maximum), 0.5 * (maximum - minimum)
        utilization = (
            float(np.max(np.abs((currents - center) / half)))
            if currents.shape == (horizon + 1, N_COILS)
            else None
        )
        issues = [event for name, event in zip(names, events) if name == "staircase_issue"]
        refreshes = [event for name, event in zip(names, events) if name == "staircase_refresh"]
        issue_increment = max(
            (float(row["incremental_normalized_action_linf"]) for row in issues),
            default=None,
        )
        refresh_increment = max(
            (float(row["incremental_normalized_action_linf"]) for row in refreshes),
            default=None,
        )
        passed = bool(
            result.get("success")
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
            and issue_increment
            <= float(cfg["controller_contract"]["maximum_incremental_normalized_action_linf"])
            + 1e-12
            and refresh_increment is not None
            and refresh_increment
            <= float(cfg["controller_contract"]["maximum_incremental_normalized_action_linf"])
            + 1e-12
            and utilization is not None
            and utilization
            <= float(cfg["controller_contract"]["maximum_current_utilization"]) + 1e-12
        )
        rows.append(
            {
                "experiment_id": spec["experiment_id"],
                "pair_id": spec["pair_id"],
                "history_member": spec["history_member"],
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
    expected = {"safety": 4, "qualification": 12}[phase]
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
        "maximum_issue_increment": max(
            (float(row["maximum_issue_increment"]) for row in rows if row["maximum_issue_increment"] is not None),
            default=None,
        ),
        "maximum_refresh_increment": max(
            (float(row["maximum_refresh_increment"]) for row in rows if row["maximum_refresh_increment"] is not None),
            default=None,
        ),
        "maximum_current_utilization": max(
            (float(row["maximum_current_utilization"]) for row in rows if row["maximum_current_utilization"] is not None),
            default=None,
        ),
        "passed_count": sum(bool(row["passed"]) for row in rows),
        "rows": rows,
    }
    keys = tuple(aggregate)
    agreement = all(primary.get(key) == aggregate[key] for key in keys)
    passed = bool(len(rows) == expected and aggregate["passed_count"] == expected)
    result = {
        "schema_version": 1,
        "stage": STAGE,
        "audit_kind": f"{phase}_raw_independent",
        "phase": phase,
        **aggregate,
        "primary_sha256": _sha(primary_path),
        "primary_agreement": agreement,
        "passed": bool(passed and agreement),
    }
    _write(stage / "analysis" / f"{phase}_raw_independent.json", result)
    return result


def final_audit(args: argparse.Namespace, cfg: Mapping[str, Any]) -> dict[str, Any]:
    stage = _stage(args)
    source_ctx = _source_context(args, cfg)
    baseline_specs, baseline_results = _source_baselines(args, cfg, source_ctx)
    specs = _expected_specs(args, cfg, source_ctx)
    evaluators, _ = r8r7.r8.d1r11._formal_callback(
        source_ctx.r8_ctx.d1r11_ctx, [*baseline_specs, *specs]
    )
    rows = []
    for spec in baseline_specs:
        rows.append(
            ind11._formal_row(
                evaluators[str(spec["experiment_id"])],
                baseline_results[str(spec["experiment_id"])],
                {
                    "kind": "baseline",
                    "experiment_id": spec["experiment_id"],
                    "pair_id": spec["pair_id"],
                    "history_member": spec["history_member"],
                },
            )
        )
    for spec in specs:
        rows.append(
            ind11._formal_row(
                evaluators[str(spec["experiment_id"])],
                _gzip(stage / "raw" / str(spec["partition"]) / f"{spec['experiment_id']}.json.gz"),
                {
                    "kind": "candidate",
                    "experiment_id": spec["experiment_id"],
                    "pair_id": spec["pair_id"],
                    "history_member": spec["history_member"],
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
    contexts = []
    for key, group in sorted(groups.items()):
        base = next(row for row in group if row["kind"] == "baseline")
        cand = next(row for row in group if row["kind"] == "candidate")
        oracle = max(
            (base, cand),
            key=lambda row: (
                float(row["formal_minimum_signed_margin"]),
                float(row["formal_mean_signed_margin"]),
                row["kind"] == "baseline",
            ),
        )
        contexts.append(
            {
                "pair_id": key[0],
                "history_member": key[1],
                "baseline": base,
                "candidate": cand,
                "gain": float(cand["formal_minimum_signed_margin"])
                - float(base["formal_minimum_signed_margin"]),
                "repair": bool(not base["formal_contract_pass"] and cand["formal_contract_pass"]),
                "oracle_pass": bool(oracle["formal_contract_pass"]),
            }
        )
    baseline_pass = sum(bool(row["baseline"]["formal_contract_pass"]) for row in contexts)
    candidate_pass = sum(bool(row["candidate"]["formal_contract_pass"]) for row in contexts)
    repairs = sum(bool(row["repair"]) for row in contexts)
    oracle_pass = sum(bool(row["oracle_pass"]) for row in contexts)
    gains = [float(row["gain"]) for row in contexts if not row["baseline"]["formal_contract_pass"]]
    gate = cfg["scientific_gate"]
    scientific = bool(
        baseline_pass == int(gate["required_baseline_formal_pass_count"])
        and len(contexts) - baseline_pass == int(gate["required_failed_baseline_count"])
        and repairs >= int(gate["minimum_repaired_failed_baseline_count"])
        and oracle_pass >= int(gate["minimum_held_oracle_formal_pass_count"])
        and oracle_pass > baseline_pass
    )
    route = cfg["routes"]["pass" if equivalence and scientific else "authority_fail"]
    primary_path = stage / "analysis" / "primary_summary.json"
    primary = _read(primary_path)
    gains_summary = {
        "minimum": min(gains),
        "median": statistics.median(gains),
        "maximum": max(gains),
    }
    numerical = bool(
        float(primary["maximum_margin_abs_difference"])
        == max(float(row["maximum_margin_abs_difference"]) for row in rows)
        and primary["failed_baseline_candidate_margin_gain"] == gains_summary
    )
    outcome = bool(
        int(primary["baseline_formal_pass_count"]) == baseline_pass
        and int(primary["failed_baseline_count"]) == len(contexts) - baseline_pass
        and int(primary["candidate_formal_pass_count"]) == candidate_pass
        and int(primary["repaired_failed_baseline_count"]) == repairs
        and int(primary["held_oracle_formal_pass_count"]) == oracle_pass
        and bool(primary["scientific_gate_passed"]) == scientific
        and bool(primary["formal_metric_equivalence_passed"]) == equivalence
    )
    result = {
        "schema_version": 1,
        "stage": STAGE,
        "audit_kind": "final_independent",
        "formal_metric_equivalence_passed": equivalence,
        "maximum_margin_abs_difference": max(
            float(row["maximum_margin_abs_difference"]) for row in rows
        ),
        "context_count": len(contexts),
        "baseline_formal_pass_count": baseline_pass,
        "failed_baseline_count": len(contexts) - baseline_pass,
        "candidate_formal_pass_count": candidate_pass,
        "repaired_failed_baseline_count": repairs,
        "held_oracle_formal_pass_count": oracle_pass,
        "failed_baseline_candidate_margin_gain": gains_summary,
        "scientific_gate_passed": scientific,
        "route": route,
        "primary_sha256": _sha(primary_path),
        "primary_route_agreement": primary.get("route") == route,
        "primary_outcome_agreement": outcome,
        "primary_numerical_agreement": numerical,
        "passed": bool(equivalence and primary.get("route") == route and outcome and numerical),
    }
    _write(stage / "analysis" / "final_independent.json", result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--r8r7-run", type=Path, required=True)
    parser.add_argument("--r8r11-run", type=Path, required=True)
    parser.add_argument("--r8-run", type=Path, required=True)
    parser.add_argument("--r8r1-output", type=Path, required=True)
    parser.add_argument("--r8r6-run", type=Path, required=True)
    for name in (
        "source-d1r11-run", "source-r2-run", "source-r4-run", "source-r6-run",
        "source-s21-run", "source-s23r1-output", "source-s24-run", "source-d1r9-v1",
        "source-d1r9-v2", "source-d1r10-run", "source-d1r10-audit", "source-stage42r3b-run",
        "source-stage42r3c3-run", "source-stage42r3c3-bank-dir", "source-stage42r3c3t1-run",
        "source-stage42r3c3t1-audit-dir", "source-stage42r3c3t3-controller-bank",
        "q1-run", "q2-run", "q1-audit", "q2-audit", "r3b-server-audit", "r3b-snapshot-checks",
    ):
        parser.add_argument(f"--{name}", dest=name.replace("-", "_"), type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument(
        "--audit-kind",
        choices=("offline", "safety_raw", "qualification_raw", "final"),
        required=True,
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    cfg = _read(args.config.expanduser().resolve())
    if cfg.get("stage") != STAGE or cfg.get("identity") != IDENTITY:
        raise ValueError("independent R8R12 configuration identity changed")
    if args.audit_kind == "offline":
        result = offline_audit(args, cfg)
    elif args.audit_kind in {"safety_raw", "qualification_raw"}:
        result = raw_audit(args, cfg, args.audit_kind.removesuffix("_raw"))
    else:
        result = final_audit(args, cfg)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
