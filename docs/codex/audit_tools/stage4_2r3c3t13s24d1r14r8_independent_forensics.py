#!/usr/bin/env python3
"""Structurally independent raw/model/route recomputation for Stage4.2 R8."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r4_independent_forensics as raw_helpers,
    stage4_2r3c3t13s24d1r14r7_independent_forensics as r7_frozen,
    stage4_2r3c3t13s24d1r14r7r2_independent_forensics as r7,
)


STAGE = "Stage4.2R3c3T13S24D1R14R8"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification"
IDENTITY = "partitioned_broad_deconfounded_response_identification_v1"
CONTROLLER_REVISION = "inherited_exact_card15_issue_cancel_v42r3c3t13s24d1r14r8_v1"
PREFIX_END = 10
ISSUES = (10, 14, 18, 22)
PHASES = ("training", "calibration", "holdout")
N_COILS = 14


def _json(path: Path) -> Any:
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


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def _inventory(directory: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    rows = []
    for path in sorted(directory.glob("*.json.gz")):
        size, sha = path.stat().st_size, _sha(path)
        digest.update(f"{path.name}\0{size}\0{sha}\n".encode())
        rows.append({"name": path.name, "size": size, "sha256": sha})
    return {
        "count": len(rows),
        "bytes": sum(row["size"] for row in rows),
        "digest": digest.hexdigest(),
        "rows": rows,
    }


def _validate(cfg: Mapping[str, Any]) -> None:
    request, bank, model, gates = (
        cfg["request_contract"], cfg["bank_contract"], cfg["model_contract"], cfg["gates"]
    )
    partitions = cfg["pair_partitions"]
    groups = [set(map(str, partitions[key])) for key in (
        "consumed_training", "training_extension", "calibration", "holdout"
    )]
    invalid = (
        cfg.get("stage") != STAGE
        or cfg.get("run_name") != RUN_NAME
        or cfg.get("campaign_identity") != IDENTITY
        or cfg.get("controller_revision") != CONTROLLER_REVISION
        or tuple(map(int, request["issue_task_steps"])) != ISSUES
        or request["canonical_matrix_digest"] != "c8cd62c00c1f60b46312927789659657dc8cc35717533193433b0e398c1ec94c"
        or request["replacement_matrix_digest"] != "69528f0e204b51847c1d2a7df428555a557454e9fa6bc76768d39e7cc5a90da8"
        or np.asarray(request["canonical_matrix_columns"], dtype=float).shape != (4, 4)
        or np.asarray(request["replacement_matrix_columns"], dtype=float).shape != (4, 4)
        or tuple(map(len, groups)) != (4, 8, 4, 4)
        or len(set().union(*groups)) != 20
        or tuple(map(int, bank["history_offsets"])) != tuple(range(23))
        or tuple(map(float, bank["response_scales"])) != (0.03, 0.03, 0.1, 0.1, 10000.0)
        or tuple(map(float, bank["target_scales"])) != (0.03, 0.03, 10000.0)
        or tuple(map(int, model["pca_ranks"])) != (4, 8, 12)
        or tuple(map(float, model["rbf_median_distance_multipliers"])) != (0.5, 1.0, 2.0)
        or tuple(map(float, model["kernel_ridges"])) != (1e-6, 1e-3, 1e-1)
        or tuple(float(gates[key]) for key in (
            "maximum_relative_l2_error", "minimum_response_cosine",
            "minimum_peak_ratio", "maximum_peak_ratio",
            "maximum_absolute_scaled_point_error", "maximum_condition_number",
        )) != (0.75, 0.8, 0.5, 1.5, 0.1, 20.0)
        or bool(cfg["probe_trajectories_allowed_in_expert_dataset"])
        or bool(cfg["mpc_validated"])
        or bool(cfg["bc_dagger_or_rl_allowed"])
    )
    if invalid:
        raise ValueError("R8 independent frozen configuration changed")


def _paths(run_dir: Path) -> dict[str, Path]:
    stage = run_dir.resolve() / RUN_NAME
    return {
        "run": run_dir.resolve(),
        "stage": stage,
        "specs": stage / "specs" / "all_specs.json",
        "manifest": stage / "stage_manifest.json",
        "analysis": stage / "analysis",
        "model": stage / "model",
        "variants": stage / "variants",
        "source_index": stage / "source_reference" / "s21_baseline_index.json",
        **{f"raw_{phase}": stage / "raw" / phase for phase in PHASES},
    }


def _specs(paths: Mapping[str, Path], phase: str | None = None) -> list[dict[str, Any]]:
    rows = _json(paths["specs"])
    manifest = _json(paths["manifest"])
    if len(rows) != 1248 or _digest(rows) != manifest["spec_digest"]:
        raise ValueError("R8 independent saved spec digest mismatch")
    if phase is not None:
        rows = [row for row in rows if row["partition"] == phase]
        expected = {"training": 624, "calibration": 312, "holdout": 312}[phase]
        if len(rows) != expected:
            raise ValueError("R8 independent phase spec coverage mismatch")
    return rows


def _sources(paths: Mapping[str, Path]) -> dict[str, dict[str, Any]]:
    output = {}
    for row in _json(paths["source_index"]):
        path = Path(str(row["path"])).expanduser().resolve()
        if _sha(path) != row["sha256"]:
            raise ValueError("R8 independent source baseline hash mismatch")
        result = _gzip(path)
        if result.get("experiment_id") != row["experiment_id"]:
            raise ValueError("R8 independent source baseline identity mismatch")
        output[str(row["experiment_id"])] = result
    if len(output) != 40:
        raise ValueError("R8 independent source baseline coverage mismatch")
    return output


FORBIDDEN = (
    "future_measurement_used", "hidden_wire_used", "source_action_used",
    "source_coil_current_used", "source_wire_current_used", "current_run_future_used",
    "pair_or_history_label_used", "source_result_used",
    "r3c3t13s24d1r14r8_future_r17_executed",
    "r3c3t13s24d1r14r8_pair_or_history_label_used",
    "r3c3t13s24d1r14r8_partition_label_used",
    "r3c3t13s24d1r14r8_source_result_used",
)


def _event(trace: Sequence[Mapping[str, Any]], spec: Mapping[str, Any], step: int) -> Mapping[str, Any]:
    kernel = str(spec["d1r14r8_execution_kernel"])
    return trace[step].get(f"r3c3t13s24d1r14{kernel}_event_detail") or {}


def raw_audit(cfg: Mapping[str, Any], paths: Mapping[str, Path], phase: str) -> dict[str, Any]:
    specs = _specs(paths, phase)
    sources = _sources(paths)
    raw_dir = paths[f"raw_{phase}"]
    inventory = _inventory(raw_dir)
    rows = []
    snapshots: dict[str, dict[str, Any]] = {}
    for spec in specs:
        path = raw_dir / f"{spec['experiment_id']}.json.gz"
        if not path.is_file():
            rows.append({"experiment_id": spec["experiment_id"], "passed": False})
            continue
        try:
            result = _gzip(path)
            trajectory, trace = result.get("trajectory") or [], result.get("controller_trace") or []
            horizon = int(spec["horizon_steps"])
            source = sources[str(spec["source_s21_baseline_experiment_id"])]
            full = len(trajectory) == horizon + 1 and len(trace) == horizon
            prefix_state = bool(
                full
                and all(
                    raw_helpers._semantic(current) == raw_helpers._semantic(reference)
                    for current, reference in zip(
                        trajectory[: PREFIX_END + 1], source["trajectory"][: PREFIX_END + 1]
                    )
                )
            )
            prefix_trace = bool(
                full
                and all(
                    raw_helpers._trace_projection(reference, current)
                    for current, reference in zip(
                        trace[:PREFIX_END], source["controller_trace"][:PREFIX_END]
                    )
                )
            )
            events = [
                row.get("r3c3t13s16_lattice_event")
                for row in trace[:PREFIX_END]
                if row.get("r3c3t13s16_lattice_event") != "none"
            ]
            calibration = bool(
                events == ["calibration_issue", "calibration_cancel"] * 4
                and trace[7].get("r3c3t13s21_exact_calibration_net_zero")
            ) if full else False
            currents = np.asarray([row.get("currents_a_tsc", []) for row in trajectory], dtype=float)
            finite = bool(
                full
                and currents.shape == (horizon + 1, N_COILS)
                and raw_helpers._all_finite(trajectory)
                and raw_helpers._all_finite(trace)
                and not any(bool(row.get("abnormal")) for row in trajectory)
            )
            forbidden = sum(any(bool(row.get(key)) for key in FORBIDDEN) for row in trace)
            solver = sum(not bool(row.get("solver_success")) for row in trace)
            saturation = raw_helpers._nested_true_count(
                trace, frozenset({"action_saturated", "current_limit_clipped"})
            )
            payload = _json(paths["variants"] / f"payload_{spec['experiment_id']}.json")
            minimum = np.asarray(payload["min_current_tsc"], dtype=float)
            maximum = np.asarray(payload["max_current_tsc"], dtype=float)
            current_center, current_half = 0.5 * (minimum + maximum), 0.5 * (maximum - minimum)
            utilization = (
                float(np.max(np.abs((currents - current_center) / current_half)))
                if currents.shape == (horizon + 1, N_COILS)
                else math.inf
            )
            snapshot_key = str(spec["restart_snapshot_dir"])
            if snapshot_key not in snapshots:
                snapshots[snapshot_key] = raw_helpers._snapshot_inventory(
                    Path(snapshot_key).resolve(), str(spec["restart_snapshot_manifest_digest"])
                )
            summary = result.get("hidden_history_control_summary") or {}
            fresh = bool(
                summary.get("fresh_controller_actor")
                and summary.get("fresh_tsc_process")
                and summary.get("full_tsc_hidden_state_loaded_from_sprsina")
                and not summary.get("future_action_replay_used")
                and not summary.get("future_measurement_used")
            )
            role = str(spec["d1r14r8_role"])
            issue, cancel, zero_after = (
                int(spec["d1r14r8_issue_task_step"]),
                int(spec["d1r14r8_cancel_task_step"]),
                int(spec["d1r14r8_zero_after_task_step"]),
            )
            before = after = issue_pass = cancel_pass = True
            if full and role == "baseline":
                actions = np.asarray([row["action_norm_tsc"] for row in trace[PREFIX_END:]], dtype=float)
                delta = np.diff(currents[PREFIX_END:], axis=0)
                before = bool(np.array_equal(actions, np.zeros_like(actions)) and np.array_equal(delta, np.zeros_like(delta)))
            elif full:
                actions = np.asarray([row["action_norm_tsc"] for row in trace[PREFIX_END:issue]], dtype=float)
                delta = np.diff(currents[PREFIX_END : issue + 1], axis=0)
                before = bool(np.array_equal(actions, np.zeros_like(actions)) and np.array_equal(delta, np.zeros_like(delta)))
                actions = np.asarray([row["action_norm_tsc"] for row in trace[zero_after:]], dtype=float)
                delta = np.diff(currents[zero_after:], axis=0)
                after = bool(np.array_equal(actions, np.zeros_like(actions)) and np.array_equal(delta, np.zeros_like(delta)))
                issued, cancelled = _event(trace, spec, issue), _event(trace, spec, cancel)
                issue_pass = bool(
                    raw_helpers._event_passes(
                        issued,
                        expected_name="sequential_issue",
                        slot=int(spec["d1r14r8_direction_index"]),
                        task_step=issue,
                    )
                    and list(map(float, issued.get("requested_coordinate", [])))
                    == list(map(float, spec["d1r14r8_requested_coordinate"]))
                    and float(issued.get("incremental_normalized_action_linf", math.inf)) <= 0.25 + 1e-12
                )
                cancel_pass = bool(
                    raw_helpers._event_passes(
                        cancelled,
                        expected_name="sequential_cancel",
                        slot=int(spec["d1r14r8_direction_index"]),
                        task_step=cancel,
                    )
                    and cancelled.get("stored_center_card15_fields") == issued.get("center_card15_fields")
                    and float(cancelled.get("incremental_normalized_action_linf", math.inf)) <= 0.24 + 1e-12
                )
            else:
                before = after = issue_pass = cancel_pass = False
            identity = bool(
                result.get("stage") == STAGE
                and result.get("campaign_identity") == IDENTITY
                and result.get("controller_revision") == CONTROLLER_REVISION
                and result.get("experiment_id") == spec["experiment_id"]
                and result.get("spec") == spec
                and result.get("completed") is True
                and result.get("success") is True
            )
            passed = bool(
                identity and full and prefix_state and prefix_trace and calibration and finite
                and forbidden == solver == saturation == 0
                and utilization <= 0.55 + 1e-12
                and fresh and snapshots[snapshot_key]["passed"]
                and before and after and issue_pass and cancel_pass
            )
            rows.append(
                {
                    "experiment_id": spec["experiment_id"],
                    "identity": identity,
                    "full_horizon": full,
                    "source_prefix_state_exact": prefix_state,
                    "source_prefix_trace_exact": prefix_trace,
                    "calibration_exact": calibration,
                    "finite": finite,
                    "forbidden_trace_count": forbidden,
                    "solver_error_count": solver,
                    "saturation_or_clip_count": saturation,
                    "maximum_current_utilization": utilization,
                    "fresh_controller_and_tsc": fresh,
                    "snapshot_passed": snapshots[snapshot_key]["passed"],
                    "action_semantics": bool(before and after and issue_pass and cancel_pass),
                    "passed": passed,
                }
            )
        except Exception as exc:
            rows.append({"experiment_id": spec["experiment_id"], "passed": False, "failure_reason": repr(exc)})
    expected = {"training": 624, "calibration": 312, "holdout": 312}[phase]
    primary_path = paths["analysis"] / f"{phase}_raw_primary.json"
    primary = _json(primary_path)
    summary = {
        "expected_raw_count": expected,
        "raw_inventory_digest": inventory["digest"],
        "raw_inventory_count": inventory["count"],
        "passed_count": sum(bool(row.get("passed")) for row in rows),
        "source_prefix_state_exact_count": sum(bool(row.get("source_prefix_state_exact")) for row in rows),
        "source_prefix_trace_exact_count": sum(bool(row.get("source_prefix_trace_exact")) for row in rows),
        "action_semantics_pass_count": sum(bool(row.get("action_semantics")) for row in rows),
        "forbidden_trace_count": sum(int(row.get("forbidden_trace_count", 0)) for row in rows),
        "solver_error_count": sum(int(row.get("solver_error_count", 0)) for row in rows),
        "saturation_or_clip_count": sum(int(row.get("saturation_or_clip_count", 0)) for row in rows),
        "maximum_current_utilization": max((float(row.get("maximum_current_utilization", math.inf)) for row in rows), default=math.inf),
        "snapshot_pass_count": sum(bool(row["passed"]) for row in snapshots.values()),
    }
    agreement = bool(
        inventory["digest"] == primary["raw_inventory"]["digest"]
        and inventory["count"] == primary["raw_inventory"]["count"]
        and summary["passed_count"] == primary["passed_count"]
        and summary["source_prefix_state_exact_count"] == primary["source_prefix_state_exact_count"]
        and summary["source_prefix_trace_exact_count"] == primary["source_prefix_trace_exact_count"]
            and summary["action_semantics_pass_count"] == primary["action_semantics_pass_count"]
            and summary["forbidden_trace_count"] == primary["forbidden_trace_count"]
            and math.isclose(summary["maximum_current_utilization"], primary["maximum_current_utilization"], rel_tol=1e-12, abs_tol=1e-12)
    )
    return {
        "schema_version": 1,
        "stage": STAGE,
        "audit_kind": f"{phase}_raw",
        "phase": phase,
        **summary,
        "primary_sha256": _sha(primary_path),
        "primary_agreement": agreement,
        "rows": rows,
        "passed": bool(
            inventory["count"] == expected
            and len(rows) == expected
            and summary["passed_count"] == expected
            and summary["solver_error_count"] == 0
            and summary["saturation_or_clip_count"] == 0
            and summary["snapshot_pass_count"] == expected // 39
            and agreement
        ),
    }


def _phase_cfg(cfg: Mapping[str, Any], phase: str) -> dict[str, Any]:
    output = json.loads(json.dumps(cfg))
    responses, branches = (912, 192) if phase == "training" else (304, 64)
    output["gates"].update(
        {
            "required_response_pass_count": responses,
            "required_signal_pass_count": responses,
            "required_canonical_branch_count": branches,
            "required_operational_branch_count": branches,
        }
    )
    return output


def _new_items(
    cfg: Mapping[str, Any], paths: Mapping[str, Path], phase: str
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    specs = _specs(paths, phase)
    results = {str(spec["experiment_id"]): _gzip(paths[f"raw_{phase}"] / f"{spec['experiment_id']}.json.gz") for spec in specs}
    scales = np.asarray(cfg["bank_contract"]["response_scales"], dtype=float)
    target_scales = np.asarray(cfg["bank_contract"]["target_scales"], dtype=float)
    offsets = tuple(map(int, cfg["bank_contract"]["history_offsets"]))
    grouped: dict[tuple[str, str], dict[tuple[str, int, int, int], tuple[Mapping[str, Any], Mapping[str, Any]]]] = {}
    for spec in specs:
        context = (str(spec["pair_id"]), str(spec["history_member"]))
        key = (str(spec["d1r14r8_role"]), int(spec["d1r14r8_issue_task_step"]), int(spec["d1r14r8_direction_index"]), int(spec["d1r14r8_sign"]))
        grouped.setdefault(context, {})[key] = (spec, results[str(spec["experiment_id"])])
    rows = []
    for context, members in sorted(grouped.items()):
        baseline_spec, baseline_result = members[("baseline", -1, -1, 0)]
        visible = r7_frozen._visible(baseline_result["trajectory"], scales)
        context_id = f"{context[0]}|{context[1]}"
        for issue in ISSUES:
            descriptor = np.concatenate(
                (
                    visible[[max(0, issue - offset) for offset in offsets]].reshape(-1),
                    [float(offset <= issue) for offset in offsets],
                    np.asarray(
                        [baseline_spec["target_R_offset_m"], baseline_spec["target_Z_offset_m"], baseline_spec["target_Ip_offset_A"]],
                        dtype=float,
                    ) / target_scales,
                    [(issue - 10.0) / 12.0],
                )
            )
            baseline = visible[issue + 1 :]
            for sign in (-1, 1):
                for direction in range(4):
                    spec, result = members[("canonical", issue, direction, sign)]
                    response = r7_frozen._visible(result["trajectory"], scales)[issue + 1 :] - baseline
                    rows.append(
                        {
                            "response_id": str(spec["experiment_id"]), "source_stage": "R8",
                            "context_id": context_id, "pair_id": context[0], "history_member": context[1],
                            "issue_task_step": issue, "sign": sign, "direction_index": direction,
                            "action_scale": 1.0,
                            "geometry_roles": ["canonical"] + (["operational"] if issue == 10 or direction != 0 else []),
                            "descriptor": descriptor, "response": response,
                        }
                    )
                if issue > 10:
                    spec, result = members[("replacement", issue, 0, sign)]
                    response = r7_frozen._visible(result["trajectory"], scales)[issue + 1 :] - baseline
                    rows.append(
                        {
                            "response_id": str(spec["experiment_id"]), "source_stage": "R8",
                            "context_id": context_id, "pair_id": context[0], "history_member": context[1],
                            "issue_task_step": issue, "sign": sign, "direction_index": 0,
                            "action_scale": 1.5, "geometry_roles": ["operational"],
                            "descriptor": descriptor, "response": response,
                        }
                    )
    rows.sort(key=lambda row: row["response_id"])
    serial = [{key: value.tolist() if isinstance(value, np.ndarray) else value for key, value in row.items()} for row in rows]
    signature = {
        "phase": phase,
        "response_count": len(rows),
        "pair_count": len({row["pair_id"] for row in rows}),
        "context_count": len({row["context_id"] for row in rows}),
        "pairs": sorted({row["pair_id"] for row in rows}),
        "descriptor_dimension": 142,
        "canonical_geometry_item_count": sum("canonical" in row["geometry_roles"] for row in rows),
        "operational_geometry_item_count": sum("operational" in row["geometry_roles"] for row in rows),
        "bank_digest": _digest(serial),
    }
    expected = {"training": 608, "calibration": 304, "holdout": 304}[phase]
    if len(rows) != expected:
        raise ValueError("R8 independent new item coverage changed")
    return rows, signature


def _training_items(cfg: Mapping[str, Any], paths: Mapping[str, Path], args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    sources = {
        "r2": r7_frozen._read_source(args.source_r2_run.resolve(), cfg["source_response_contracts"]["r2"]),
        "r4": r7_frozen._read_source(args.source_r4_run.resolve(), cfg["source_response_contracts"]["r4"]),
        "r6": r7_frozen._read_source(args.source_r6_run.resolve(), cfg["source_response_contracts"]["r6"]),
    }
    existing, existing_bank = r7._items(sources, cfg)
    extension, extension_bank = _new_items(cfg, paths, "training")
    items = sorted(existing + extension, key=lambda row: row["response_id"])
    if len(items) != 912 or len({row["pair_id"] for row in items}) != 12:
        raise ValueError("R8 independent combined training bank changed")
    return items, existing_bank, extension_bank


def _actual_geometry(items: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> dict[str, Any]:
    rows = [
        {
            "response_id": row["response_id"], "context_id": row["context_id"],
            "pair_id": row["pair_id"], "history_member": row["history_member"],
            "issue_task_step": row["issue_task_step"], "sign": row["sign"],
            "direction_index": row["direction_index"], "source_stage": row["source_stage"],
            "action_scale": row["action_scale"], "geometry_roles": row["geometry_roles"],
            "predicted_response": np.asarray(row["response"]).tolist(),
        }
        for row in items
    ]
    value = r7._geometry(rows, cfg)
    value["interpretation"] = "actual_response_geometry"
    return value


def training_model_audit(cfg: Mapping[str, Any], paths: Mapping[str, Path], args: argparse.Namespace) -> dict[str, Any]:
    items, existing_bank, extension_bank = _training_items(cfg, paths, args)
    phase_cfg = _phase_cfg(cfg, "training")
    rows, folds = r7._nested(items, phase_cfg)
    aggregate = r7_frozen._aggregate(rows, phase_cfg)
    geometry = r7._geometry(rows, phase_cfg)
    actual = _actual_geometry(items, phase_cfg)
    selected, scores = r7._select(items, phase_cfg)
    candidate = {"pca_rank": selected[0], "bandwidth_multiplier": selected[1], "ridge": selected[2]}
    primary_path = paths["analysis"] / "training_model_primary_detailed.json"
    primary = _json(primary_path)
    agreement = bool(
        r7_frozen._agrees(primary["existing_bank"], existing_bank)
        and r7_frozen._agrees(primary["extension_bank"], extension_bank)
        and r7_frozen._agrees(primary["nested_outer_folds"], folds)
        and r7_frozen._agrees(primary["outer_prediction_rows"], rows)
        and r7_frozen._agrees(primary["aggregate"], aggregate)
        and r7_frozen._agrees(primary["predicted_geometry"], geometry)
        and r7_frozen._agrees(primary["actual_geometry"], actual)
        and r7_frozen._agrees(primary["selected_candidate"], candidate)
        and r7_frozen._agrees(primary["candidate_scores"], scores)
    )
    model_path = paths["model"] / "training_response_model.json"
    summary_path = paths["analysis"] / "training_model_primary_summary.json"
    passed_science = bool(aggregate["passed"] and geometry["passed"] and actual["passed"])
    return {
        "schema_version": 1, "stage": STAGE, "audit_kind": "training_model",
        "training_model_sha256": _sha(model_path),
        "primary_summary_sha256": _sha(summary_path),
        "selected_candidate": candidate, "candidate_scores": scores,
        "aggregate": aggregate, "predicted_geometry": geometry, "actual_geometry": actual,
        "primary_numerical_agreement": agreement,
        "scientific_gate_passed": passed_science,
        "passed": bool(agreement and passed_science and primary["passed"]),
    }


def _fit_training_independent(cfg: Mapping[str, Any], paths: Mapping[str, Path], args: argparse.Namespace) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    items, _, _ = _training_items(cfg, paths, args)
    audit = _json(paths["analysis"] / "training_model_independent.json")
    selected = audit["selected_candidate"]
    candidate = (int(selected["pca_rank"]), float(selected["bandwidth_multiplier"]), float(selected["ridge"]))
    return r7._fit(items, candidate, _phase_cfg(cfg, "training")), items


def _fixed_rows(model: Mapping[str, Any], items: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        [r7._metric(row, r7._predict(model, row, cfg), cfg) for row in items],
        key=lambda row: row["response_id"],
    )


def calibration_model_audit(cfg: Mapping[str, Any], paths: Mapping[str, Path], args: argparse.Namespace) -> dict[str, Any]:
    model, _ = _fit_training_independent(cfg, paths, args)
    items, bank = _new_items(cfg, paths, "calibration")
    phase_cfg = _phase_cfg(cfg, "calibration")
    rows = _fixed_rows(model, items, phase_cfg)
    aggregate = r7_frozen._aggregate(rows, phase_cfg)
    geometry, actual = r7._geometry(rows, phase_cfg), _actual_geometry(items, phase_cfg)
    training = _json(paths["analysis"] / "training_model_independent.json")
    component = np.maximum(
        np.asarray(training["aggregate"]["componentwise_maximum_absolute_scaled_error"]),
        np.asarray(aggregate["componentwise_maximum_absolute_scaled_error"]),
    )
    scales = np.asarray(cfg["bank_contract"]["response_scales"], dtype=float)
    tube = np.asarray(cfg["gates"]["response_floor_physical"]) / scales + float(cfg["gates"]["tube_multiplier"]) * component
    caps = np.asarray(cfg["gates"]["tube_caps_physical"]) / scales
    tube_report = {
        "componentwise_maximum_absolute_scaled_error": component.tolist(),
        "tube_halfwidth_scaled": tube.tolist(),
        "tube_halfwidth_physical": (tube * scales).tolist(),
        "tube_caps_physical": list(map(float, cfg["gates"]["tube_caps_physical"])),
        "tube_cap_pass": bool(np.all(tube <= caps + 1e-15)),
    }
    primary_path = paths["analysis"] / "calibration_model_primary_detailed.json"
    primary = _json(primary_path)
    agreement = bool(
        r7_frozen._agrees(primary["bank"], bank)
        and r7_frozen._agrees(primary["prediction_rows"], rows)
        and r7_frozen._agrees(primary["aggregate"], aggregate)
        and r7_frozen._agrees(primary["predicted_geometry"], geometry)
        and r7_frozen._agrees(primary["actual_geometry"], actual)
        and r7_frozen._agrees(primary["calibrated_tube"], tube_report)
    )
    model_path = paths["model"] / "training_response_model.json"
    tube_path = paths["model"] / "calibrated_response_tube.json"
    summary_path = paths["analysis"] / "calibration_model_primary_summary.json"
    passed_science = bool(aggregate["passed"] and geometry["passed"] and actual["passed"] and tube_report["tube_cap_pass"])
    return {
        "schema_version": 1, "stage": STAGE, "audit_kind": "calibration_model",
        "training_model_sha256": _sha(model_path),
        "calibrated_tube_sha256": _sha(tube_path),
        "primary_summary_sha256": _sha(summary_path),
        "aggregate": aggregate, "predicted_geometry": geometry, "actual_geometry": actual,
        "calibrated_tube": tube_report, "primary_numerical_agreement": agreement,
        "scientific_gate_passed": passed_science,
        "passed": bool(agreement and passed_science and primary["passed"]),
    }


def holdout_model_audit(cfg: Mapping[str, Any], paths: Mapping[str, Path], args: argparse.Namespace) -> dict[str, Any]:
    model, _ = _fit_training_independent(cfg, paths, args)
    items, bank = _new_items(cfg, paths, "holdout")
    phase_cfg = _phase_cfg(cfg, "holdout")
    tube_audit = _json(paths["analysis"] / "calibration_model_independent.json")
    halfwidth = np.asarray(tube_audit["calibrated_tube"]["tube_halfwidth_scaled"], dtype=float)
    rows = []
    for item in items:
        prediction = r7._predict(model, item, phase_cfg)
        row = r7._metric(item, prediction, phase_cfg)
        error = np.abs(prediction - np.asarray(item["response"]))
        row["tube_containment"] = bool(np.all(error <= halfwidth[None, :] + 1e-15))
        row["tube_maximum_fraction"] = float(np.max(error / np.maximum(halfwidth[None, :], 1e-300)))
        rows.append(row)
    rows.sort(key=lambda row: row["response_id"])
    aggregate = r7_frozen._aggregate(rows, phase_cfg)
    geometry, actual = r7._geometry(rows, phase_cfg), _actual_geometry(items, phase_cfg)
    containment = sum(row["tube_containment"] for row in rows)
    passed_science = bool(
        aggregate["passed"] and geometry["passed"] and actual["passed"]
        and containment == 304 and tube_audit["calibrated_tube"]["tube_cap_pass"]
    )
    route = cfg["routes"]["pass" if passed_science else "holdout_model_fail"]
    final_path = paths["run"] / "final_result.json"
    detailed_path = paths["run"] / "final_result_detailed.json"
    primary = _json(detailed_path)
    agreement = bool(
        r7_frozen._agrees(primary["bank"], bank)
        and r7_frozen._agrees(primary["prediction_rows"], rows)
        and r7_frozen._agrees(primary["aggregate"], aggregate)
        and r7_frozen._agrees(primary["predicted_geometry"], geometry)
        and r7_frozen._agrees(primary["actual_geometry"], actual)
        and primary["tube_containment_pass_count"] == containment
        and math.isclose(primary["maximum_tube_fraction"], max(row["tube_maximum_fraction"] for row in rows), rel_tol=1e-10, abs_tol=1e-12)
        and primary["route"] == route
        and primary["passed"] == passed_science
    )
    return {
        "schema_version": 1, "stage": STAGE, "audit_kind": "holdout_model",
        "final_result_sha256": _sha(final_path), "route": route,
        "aggregate": aggregate, "predicted_geometry": geometry, "actual_geometry": actual,
        "tube_containment_pass_count": containment,
        "maximum_tube_fraction": max(row["tube_maximum_fraction"] for row in rows),
        "primary_numerical_agreement": agreement,
        "scientific_gate_passed": passed_science,
        "passed": agreement,
    }


def audit(args: argparse.Namespace) -> dict[str, Any]:
    cfg = _json(args.config.resolve())
    _validate(cfg)
    paths = _paths(args.run_dir)
    kind = args.audit_kind
    if kind.endswith("_raw"):
        result = raw_audit(cfg, paths, kind.removesuffix("_raw"))
    elif kind == "training_model":
        result = training_model_audit(cfg, paths, args)
    elif kind == "calibration_model":
        result = calibration_model_audit(cfg, paths, args)
    elif kind == "holdout_model":
        result = holdout_model_audit(cfg, paths, args)
    else:
        raise ValueError("unsupported R8 independent audit kind")
    output = paths["analysis"] / f"{kind}_independent.json"
    _write(output, result)
    print(json.dumps({key: result.get(key) for key in ("stage", "audit_kind", "route", "passed")}, indent=2, sort_keys=True, allow_nan=False))
    if not result["passed"]:
        raise ValueError(f"R8 independent audit failed: {kind}")
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-r2-run", type=Path, required=True)
    parser.add_argument("--source-r4-run", type=Path, required=True)
    parser.add_argument("--source-r6-run", type=Path, required=True)
    parser.add_argument(
        "--audit-kind",
        choices=("training_raw", "training_model", "calibration_raw", "calibration_model", "holdout_raw", "holdout_model"),
        required=True,
    )
    return parser


if __name__ == "__main__":
    audit(_parser().parse_args())
