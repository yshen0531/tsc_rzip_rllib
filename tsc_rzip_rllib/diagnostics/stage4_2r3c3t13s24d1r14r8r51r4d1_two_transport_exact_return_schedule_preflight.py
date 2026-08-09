"""Zero-TSC exact two-transport schedule preflight for R8R51R4D1."""
from __future__ import annotations

import argparse
import copy
import hashlib
import itertools
import json
import math
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r51r4_failed_context_sustained_transport_dwell_sentinel
    as r4,
)


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S24D1R14R8R51R4D1"
IDENTITY = "two_transport_exact_return_schedule_preflight_v1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r51r4d1_two_transport_exact_return_schedule_preflight"
CANDIDATE_IDS = ("d0m", "d1p", "d2m", "d3p", "u1p50")
Q0_STEP = 10
FIRST_ISSUE_STEP = 12
SECOND_ISSUE_STEP = 16
RETURN_STEP = 20
N_COILS = 14


class SourceBlockedError(RuntimeError):
    """Raised when immutable R51R4 evidence no longer authenticates."""


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream, parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"non-finite JSON token {token} in {path}")
        ))


def _write(path: Path, value: Any, *, replace: bool = False) -> None:
    if path.exists() and not replace:
        raise ValueError(f"R8R51R4D1 output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
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
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode(
            "utf-8"
        )
    ).hexdigest()


def _file_inventory(paths: Sequence[Path]) -> dict[str, Any]:
    rows = [
        {"name": path.name, "size": path.stat().st_size, "sha256": _sha(path)}
        for path in sorted(paths)
    ]
    return {
        "count": len(rows),
        "bytes": sum(int(row["size"]) for row in rows),
        "digest": _digest(rows),
        "rows": rows,
    }


@dataclass(frozen=True)
class Paths:
    stage: Path
    specs: Path
    source_reference: Path
    analysis: Path
    state: Path
    manifest: Path


def _paths(run_dir: Path) -> Paths:
    stage = run_dir.expanduser().resolve() / RUN_NAME
    return Paths(
        stage=stage,
        specs=stage / "specs",
        source_reference=stage / "source_reference",
        analysis=stage / "analysis",
        state=stage / "stage_state.json",
        manifest=stage / "stage_manifest.json",
    )


@dataclass(frozen=True)
class Context:
    cfg: dict[str, Any]
    config_path: Path
    paths: Paths
    r4_ctx: r4.Context
    r4_stage: Path


def validate_config(cfg: Mapping[str, Any], *, project_root: Path) -> None:
    matrix = cfg.get("matrix_contract", {})
    schedule = cfg.get("schedule_contract", {})
    action = cfg.get("action_contract", {})
    coverage = cfg.get("coverage_gate", {})
    scope = cfg.get("scientific_scope", {})
    source = cfg.get("source_r51r4", {})
    design = project_root / str(cfg.get("design_document", ""))
    reporting_fix = project_root / str(cfg.get("reporting_fix_contract", ""))
    source_config = project_root / str(cfg.get("source_r51r4_config", ""))
    source_implementation = project_root / (
        "tsc_rzip_rllib/diagnostics/"
        "stage4_2r3c3t13s24d1r14r8r51r4_failed_context_sustained_transport_dwell_sentinel.py"
    )
    source_independent = project_root / (
        "docs/codex/audit_tools/"
        "stage4_2r3c3t13s24d1r14r8r51r4_independent_forensics.py"
    )
    expected_routes = {
        "source_blocked": "REDUCED_Q0_TRANSPORT_BRIDGE_R51R4D1_BLOCKED_BY_SOURCE",
        "geometry_fail": "REDUCED_Q0_TRANSPORT_BRIDGE_R51R4D1_TWO_TRANSPORT_SCHEDULE_GEOMETRY_INSUFFICIENT_NO_REAL_TSC",
        "pass": "REDUCED_Q0_TRANSPORT_BRIDGE_R51R4D1_TWO_TRANSPORT_SCHEDULE_PREFLIGHT_COMPLETE_R51R4D2_DESIGN_REQUIRED",
    }
    required_hashes = tuple(key for key in source if key.endswith("_sha256"))
    failed_ids = tuple(matrix.get("failed_source_baseline_ids", ()))
    invalid = (
        cfg.get("schema_version") != SCHEMA_VERSION
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("run_name") != RUN_NAME
        or cfg.get("model_revision")
        != "no_model_two_transport_exact_return_schedule_preflight_v1"
        or cfg.get("package_revision")
        != "r42r3c3t13s24d1r14r8r51r4d1_two_transport_schedule_preflight_v2_refresh_reporting_fix"
        or not design.is_file()
        or _sha(design) != cfg.get("design_document_sha256")
        or not reporting_fix.is_file()
        or _sha(reporting_fix) != cfg.get("reporting_fix_contract_sha256")
        or cfg.get("reporting_fix_required_action_stream_digest")
        != "d1607012ca5e39cca3b3113c269c569c754603c49704cef419b239d810ea7ccb"
        or not source_config.is_file()
        or _sha(source_config) != cfg.get("source_r51r4_config_sha256")
        or not source_implementation.is_file()
        or _sha(source_implementation) != cfg.get("source_r51r4_implementation_sha256")
        or not source_independent.is_file()
        or _sha(source_independent) != cfg.get("source_r51r4_independent_sha256")
        or any(
            not isinstance(source.get(key), str)
            or len(str(source[key])) != 64
            or any(ch not in "0123456789abcdef" for ch in str(source[key]))
            for key in required_hashes
        )
        or source.get("run_name")
        != "stage4_2r3c3t13s24d1r14r8r51r4_failed_context_sustained_transport_dwell_sentinel_20260810_7b394cb_v2"
        or source.get("stage_directory")
        != "stage4_2r3c3t13s24d1r14r8r51r4_failed_context_sustained_transport_dwell_sentinel"
        or source.get("required_route")
        != "REDUCED_Q0_TRANSPORT_BRIDGE_R51R4_SUSTAINED_DWELL_AUTHORITY_INSUFFICIENT_LONGER_SEQUENTIAL_REDESIGN_REQUIRED"
        or tuple(int(matrix.get(key, -1)) for key in (
            "context_count", "candidate_count", "ordered_pair_count_per_context",
            "specification_count",
        )) != (10, 5, 25, 250)
        or tuple(matrix.get("candidate_ids", ())) != CANDIDATE_IDS
        or failed_ids != tuple(f"r8r7_baseline_{index:02d}" for index in (*range(8), 12, 13))
        or tuple(int(schedule.get(key, -1)) for key in (
            "q0_issue_task_step", "q0_observe_task_step",
            "first_transport_issue_task_step", "second_transport_issue_task_step",
            "stored_center_return_task_step", "first_restored_center_state_step",
            "dynamic_exact_search_radius",
        )) != (10, 11, 12, 16, 20, 21, 16)
        or tuple(map(int, schedule.get("first_transport_hold_task_steps", ()))) != (13, 14, 15)
        or tuple(map(int, schedule.get("second_transport_hold_task_steps", ()))) != (17, 18, 19)
        or schedule.get("require_exact_center_refresh_after_return") is not True
        or tuple(float(action.get(key, -1.0)) for key in (
            "maximum_q0_integration_action_linf",
            "maximum_incremental_normalized_action_linf",
            "maximum_total_normalized_action_abs", "maximum_current_utilization",
            "minimum_desired_applied_current_cosine",
            "maximum_relative_off_basis_residual", "numerical_tolerance",
        )) != (1e-5, 0.25, 1.0, 0.55, 0.98, 0.10, 1e-12)
        or any(action.get(key) is not True for key in (
            "require_equal_pair_zero_increment", "require_exact_card15_target",
            "require_exact_stored_center_return", "forbid_response_inputs",
        ))
        or tuple(int(coverage.get(key, -1)) for key in (
            "minimum_eligible_ordered_pairs_per_context",
            "required_first_candidate_count_per_context",
            "required_second_candidate_count_per_context",
            "minimum_distinct_successors_per_first_candidate",
            "required_history_pair_count",
        )) != (10, 5, 5, 1, 5)
        or coverage.get("require_equal_eligible_pair_set_within_history_pair") is not True
        or cfg.get("routes") != expected_routes
        or scope.get("zero_new_tsc") is not True
        or scope.get("response_values_used") is not False
        or any(scope.get(key) is not False for key in (
            "model_fit_allowed", "controller_executed", "real_mpc_executed",
            "gate_a_qualified", "expert_data_allowed", "bc_dagger_or_rl_allowed",
            "all_source_trajectories_allowed_in_expert_dataset",
            "global_plant_reachability_claimed",
        ))
    )
    if invalid:
        raise ValueError("R8R51R4D1 frozen design changed")


def load_context(args: argparse.Namespace) -> Context:
    config_path = args.config.expanduser().resolve()
    cfg = _read(config_path)
    validate_config(cfg, project_root=_root())
    source_args = SimpleNamespace(**vars(args))
    source_args.config = (_root() / str(cfg["source_r51r4_config"])).resolve()
    source_args.run_dir = args.r51r4_run.expanduser().resolve()
    r4_ctx = r4.load_context(source_args)
    r4_stage = r4_ctx.paths.stage
    expected = cfg["source_r51r4"]
    if r4_stage.parent.name != expected["run_name"] or r4_stage.name != expected["stage_directory"]:
        raise ValueError("R8R51R4D1 source R51R4 run identity changed")
    return Context(cfg, config_path, _paths(args.run_dir), r4_ctx, r4_stage)


ARTIFACTS = {
    "stage_state": "stage_state.json",
    "stage_manifest": "stage_manifest.json",
    "specs": "specs/all_specs.json",
    "offline_construction": "analysis/offline_construction.json",
    "offline_primary": "analysis/offline_primary.json",
    "offline_independent": "analysis/offline_independent.json",
    "original_raw_primary": "analysis/raw_integrity_primary.json",
    "original_raw_independent": "analysis/raw_integrity_independent.json",
    "hotfix_raw_primary": "analysis/current_equivalence_reporting_hotfix_raw_primary.json",
    "hotfix_raw_independent": "analysis/current_equivalence_reporting_hotfix_raw_independent.json",
    "hotfix_raw_compact": "analysis/current_equivalence_reporting_hotfix_raw_compact_audit.json",
    "hotfix_formal_detailed": "analysis/current_equivalence_reporting_hotfix_formal_primary_detailed.json",
    "hotfix_formal_summary": "analysis/current_equivalence_reporting_hotfix_formal_primary_summary.json",
    "hotfix_formal_independent": "analysis/current_equivalence_reporting_hotfix_formal_independent.json",
    "hotfix_compact": "analysis/current_equivalence_reporting_hotfix_compact_audit.json",
    "hotfix_final": "analysis/current_equivalence_reporting_hotfix_final_report.json",
    "hotfix_server_evidence": "analysis/current_equivalence_reporting_hotfix_server_evidence.json",
}


def authenticate_source(ctx: Context) -> dict[str, Any]:
    expected = ctx.cfg["source_r51r4"]
    inherited = r4.authenticate_sources(ctx.r4_ctx)
    hashes: dict[str, str] = {}
    for key, relative in ARTIFACTS.items():
        path = ctx.r4_stage / relative
        if not path.is_file():
            raise SourceBlockedError(f"R8R51R4D1 source artifact missing: {relative}")
        hashes[key] = _sha(path)
        if hashes[key] != expected[f"{key}_sha256"]:
            raise SourceBlockedError(f"R8R51R4D1 source artifact changed: {relative}")
    raw_inventory = r4.r51.r8r7.r8._inventory(ctx.r4_stage / "raw")
    payload_inventory = _file_inventory(list((ctx.r4_stage / "variants").glob("payload_*.json")))
    if (
        int(raw_inventory["count"]) != int(expected["raw_count"])
        or int(raw_inventory["bytes"]) != int(expected["raw_bytes"])
        or raw_inventory["digest"] != expected["raw_digest"]
        or int(payload_inventory["count"]) != int(expected["payload_count"])
        or int(payload_inventory["bytes"]) != int(expected["payload_bytes"])
        or payload_inventory["digest"] != expected["payload_digest"]
    ):
        raise SourceBlockedError("R8R51R4D1 source raw or payload inventory changed")
    raw_primary = _read(ctx.r4_stage / ARTIFACTS["hotfix_raw_primary"])
    raw_independent = _read(ctx.r4_stage / ARTIFACTS["hotfix_raw_independent"])
    summary = _read(ctx.r4_stage / ARTIFACTS["hotfix_formal_summary"])
    independent = _read(ctx.r4_stage / ARTIFACTS["hotfix_formal_independent"])
    final = _read(ctx.r4_stage / ARTIFACTS["hotfix_final"])
    server = _read(ctx.r4_stage / ARTIFACTS["hotfix_server_evidence"])
    if (
        inherited.get("passed") is not True
        or raw_primary.get("passed") is not True
        or raw_independent.get("passed") is not True
        or raw_independent.get("primary_agreement") is not True
        or int(raw_primary.get("passed_count", -1)) != 100
        or summary.get("integrity_gate_passed") is not True
        or summary.get("scientific_gate_passed") is not False
        or int(summary.get("candidate_formal_pass_count", -1)) != 0
        or int(summary.get("repaired_failed_baseline_count", -1)) != 0
        or int(summary.get("measured_oracle_formal_pass_count", -1)) != 6
        or independent.get("audit_passed") is not True
        or independent.get("primary_discrete_agreement") is not True
        or independent.get("primary_numerical_agreement") is not True
        or final.get("audit_passed") is not True
        or final.get("independent_agreement") is not True
        or final.get("passed") is not False
        or final.get("route") != expected["required_route"]
        or final.get("all_stage_trajectories_allowed_in_expert_dataset") is not False
        or (server.get("final") or {}).get("r51r5_executed") is not False
        or (server.get("final") or {}).get("route") != expected["required_route"]
    ):
        raise SourceBlockedError("R8R51R4D1 final R51R4 provenance changed")
    return {
        "stage": str(ctx.r4_stage),
        "hashes": hashes,
        "raw_inventory": raw_inventory,
        "payload_inventory": payload_inventory,
        "inherited_source_authentication_digest": _digest(inherited),
        "required_route": expected["required_route"],
        "response_values_available_to_construction": False,
        "passed": True,
    }


def _source_specs(ctx: Context) -> list[dict[str, Any]]:
    rows = _read(ctx.r4_stage / "specs/all_specs.json")
    if len(rows) != 100 or _sha(ctx.r4_stage / "specs/all_specs.json") != ctx.cfg["source_r51r4"]["specs_sha256"]:
        raise SourceBlockedError("R8R51R4D1 source specifications changed")
    return rows


def build_specs(ctx: Context) -> list[dict[str, Any]]:
    source_rows = _source_specs(ctx)
    by_key = {
        (
            str(row["source_r8r7_baseline_experiment_id"]),
            str(row["r8r51r4_candidate_id"]),
            int(row["r8r51r4_return_task_step"]),
        ): row
        for row in source_rows
    }
    specs = []
    for context_index, baseline_id in enumerate(ctx.cfg["matrix_contract"]["failed_source_baseline_ids"]):
        for first_id, second_id in itertools.product(CANDIDATE_IDS, repeat=2):
            first = by_key[(str(baseline_id), first_id, 16)]
            second = by_key[(str(baseline_id), second_id, 16)]
            specs.append(
                {
                    "stage": STAGE,
                    "identity": IDENTITY,
                    "experiment_id": f"r8r51r4d1_c{context_index:02d}_{first_id}_to_{second_id}",
                    "context_index": context_index,
                    "source_r8r7_baseline_experiment_id": str(baseline_id),
                    "pair_id": str(first["pair_id"]),
                    "history_member": str(first["history_member"]),
                    "horizon_steps": int(first["horizon_steps"]),
                    "first_candidate_id": first_id,
                    "first_candidate_index": int(first["r8r51r4_candidate_index"]),
                    "first_candidate_q": copy.deepcopy(first["r8r51r4_candidate_q"]),
                    "first_requested_coordinate": copy.deepcopy(first["r8r51r4_requested_coordinate"]),
                    "first_source_experiment_id": str(first["experiment_id"]),
                    "second_candidate_id": second_id,
                    "second_candidate_index": int(second["r8r51r4_candidate_index"]),
                    "second_candidate_q": copy.deepcopy(second["r8r51r4_candidate_q"]),
                    "second_requested_coordinate": copy.deepcopy(second["r8r51r4_requested_coordinate"]),
                    "second_source_experiment_id": str(second["experiment_id"]),
                    "decision_task_steps": [FIRST_ISSUE_STEP, SECOND_ISSUE_STEP, RETURN_STEP],
                    "pair_or_history_label_available_to_controller": False,
                    "source_result_available_to_construction": False,
                    "future_measurement_count": 0,
                    "future_action_count": 0,
                    "allowed_in_expert_dataset": False,
                }
            )
    coverage = {
        (row["source_r8r7_baseline_experiment_id"], row["first_candidate_id"], row["second_candidate_id"])
        for row in specs
    }
    if len(specs) != 250 or len(coverage) != 250 or len({row["experiment_id"] for row in specs}) != 250:
        raise ValueError("R8R51R4D1 frozen specification matrix changed")
    return specs


def _canonical_event(event: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "event": str(event.get("event", "")),
        "task_step": int(event["task_step"]),
        "target_card15_fields": list(event.get("target_card15_fields") or event.get("stored_target_card15_fields") or ()),
        "action_norm_tsc": list(map(float, event.get("action_norm_tsc") or ())),
        "nominal_readback_current_a_tsc": list(map(float, event.get("nominal_readback_current_a_tsc") or event.get("nominal_issue_readback_current_a_tsc") or ())),
        "criteria": {str(key): bool(value) for key, value in sorted((event.get("criteria") or {}).items())},
        "passed": bool(event.get("passed")),
    }


def _transition_geometry(
    *, before: np.ndarray, after: np.ndarray, desired_target: np.ndarray,
    field_basis: np.ndarray, turns: np.ndarray,
) -> tuple[float, float]:
    desired = desired_target - before
    actual = after - before
    current_basis = np.asarray(field_basis, dtype=float) * 1000.0 / turns[:, None]
    coordinate = np.linalg.lstsq(current_basis, actual, rcond=None)[0]
    reconstructed = current_basis @ coordinate
    cosine = float(np.dot(desired, actual) / max(np.linalg.norm(desired) * np.linalg.norm(actual), 1e-300))
    off_basis = float(np.linalg.norm(actual - reconstructed) / max(np.linalg.norm(actual), 1e-300))
    return cosine, off_basis


def _runtime_parts(ctx: Context, source_spec: Mapping[str, Any]) -> tuple[Any, Any, np.ndarray, Mapping[str, Any], Mapping[str, Any]]:
    _, sources = r4.r51._source_baselines(ctx.r4_ctx.base_ctx)
    source = sources[str(source_spec["source_r8r7_baseline_experiment_id"])]
    execution = r4._execution_context(ctx.r4_ctx)
    lattice = execution.d1r11_ctx.base_ctx.base_ctx.cfg["lattice_probe"]
    contract = r4._controller_contract(ctx.r4_ctx)
    payload = _read(ctx.r4_stage / "variants" / f"payload_{source_spec['experiment_id']}.json")
    actuator = r4.r51.r8r22.mpc.actuator_from_payload(payload, lattice)
    field_basis = r4.r51.r8r22._fixed_basis(source)
    return actuator, source, field_basis, lattice, contract


def construct_schedule(
    ctx: Context,
    spec: Mapping[str, Any],
    source_by_experiment: Mapping[str, Mapping[str, Any]],
    base_cache: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    first_spec = source_by_experiment[str(spec["first_source_experiment_id"])]
    second_spec = source_by_experiment[str(spec["second_source_experiment_id"])]
    for source_spec in (first_spec, second_spec):
        key = str(source_spec["experiment_id"])
        if key not in base_cache:
            base_cache[key] = r4.construct_event_stream(ctx.r4_ctx, source_spec, include_events=True)
    first_base = base_cache[str(first_spec["experiment_id"])]
    second_base = base_cache[str(second_spec["experiment_id"])]
    first_events = first_base["events"]
    second_events = second_base["events"]
    first_issue = next(event for event in first_events if int(event["task_step"]) == FIRST_ISSUE_STEP)
    second_source_issue = next(event for event in second_events if int(event["task_step"]) == FIRST_ISSUE_STEP)
    prefix = [copy.deepcopy(event) for event in first_events if int(event["task_step"]) <= 15]
    if tuple(int(event["task_step"]) for event in prefix) != (10, 11, 12, 13, 14, 15):
        raise ValueError("R8R51R4D1 first schedule prefix changed")
    actuator, _, field_basis, lattice, contract = _runtime_parts(ctx, first_spec)
    current = np.asarray(prefix[-1]["nominal_readback_current_a_tsc"], dtype=float)
    second = r4.r51.r8r22._refresh_event(
        task_step=SECOND_ISSUE_STEP,
        currents=current,
        target_fields=second_source_issue["target_card15_fields"],
        actuator=actuator,
        turns_tsc=actuator.turns_tsc,
        max_delta_a=actuator.max_slew_step_a,
        minimum_current=actuator.minimum_current_a_tsc,
        maximum_current=actuator.maximum_current_a_tsc,
        lattice_cfg=lattice,
        contract=contract,
    )
    second["event"] = "second_transport_exact_target_issue"
    second["candidate_id"] = str(spec["second_candidate_id"])
    second["target_card15_fields"] = list(second["stored_target_card15_fields"])
    after_second = np.asarray(second["nominal_readback_current_a_tsc"], dtype=float)
    desired_target = np.asarray(second_source_issue["nominal_issue_readback_current_a_tsc"], dtype=float)
    cosine, off_basis = _transition_geometry(
        before=current,
        after=after_second,
        desired_target=desired_target,
        field_basis=field_basis,
        turns=np.asarray(actuator.turns_tsc, dtype=float),
    ) if not np.array_equal(after_second, current) else (1.0, 0.0)
    equal_pair = str(spec["first_candidate_id"]) == str(spec["second_candidate_id"])
    zero_second = bool(np.array_equal(np.asarray(second["action_norm_tsc"]), np.zeros(N_COILS)))
    second["desired_applied_current_cosine"] = cosine
    second["relative_off_basis_residual"] = off_basis
    second["criteria"].update(
        {
            "cosine": cosine >= float(contract["minimum_desired_applied_current_cosine"]) - 1e-12,
            "off_basis": off_basis <= float(contract["maximum_relative_off_basis_residual"]) + 1e-12,
            "equal_pair_zero_increment": (not equal_pair) or zero_second,
            "distinct_pair_nonzero_increment": equal_pair or (not zero_second),
            "source_target_exact": list(second["stored_target_card15_fields"])
            == list(second_source_issue["target_card15_fields"]),
        }
    )
    second["passed"] = bool(all(second["criteria"].values()))
    events = prefix + [second]
    current = after_second
    for step in (17, 18, 19):
        hold = r4.r51._observe_event(
            task_step=step,
            currents=current,
            target_fields=second["stored_target_card15_fields"],
            actuator=actuator,
            contract=contract,
            event="second_transport_exact_target_hold",
        )
        events.append(hold)
        current = np.asarray(hold["nominal_readback_current_a_tsc"], dtype=float)
    return_issue = {
        "target_card15_fields": list(second["stored_target_card15_fields"]),
        "center_nominal_readback_current_a_tsc": list(first_issue["center_nominal_readback_current_a_tsc"]),
    }
    returned = r4.r51._return_event(
        task_step=RETURN_STEP,
        currents=current,
        center_fields=first_events[0]["q0_center_card15_fields"],
        issue_event=return_issue,
        field_basis=field_basis,
        actuator=actuator,
        lattice=lattice,
        contract=contract,
    )
    returned["event"] = "two_transport_stored_center_return"
    events.append(returned)
    current = np.asarray(returned["nominal_readback_current_a_tsc"], dtype=float)
    for step in range(RETURN_STEP + 1, int(spec["horizon_steps"])):
        refresh = r4.r51.r8r22._refresh_event(
            task_step=step,
            currents=current,
            target_fields=first_events[0]["q0_center_card15_fields"],
            actuator=actuator,
            turns_tsc=actuator.turns_tsc,
            max_delta_a=actuator.max_slew_step_a,
            minimum_current=actuator.minimum_current_a_tsc,
            maximum_current=actuator.maximum_current_a_tsc,
            lattice_cfg=lattice,
            contract=contract,
        )
        refresh["event"] = "post_two_transport_exact_center_refresh"
        events.append(refresh)
        current = np.asarray(refresh["nominal_readback_current_a_tsc"], dtype=float)
    center_current = np.asarray(first_issue["center_nominal_readback_current_a_tsc"], dtype=float)
    post_return = events[events.index(returned) + 1 :]
    numerical = [
        float(event[key])
        for event in events
        for key in ("incremental_normalized_action_linf", "total_normalized_action_abs", "predicted_current_utilization")
        if key in event
    ] + [cosine, off_basis]
    criteria = {
        "source_first_event_stream_pass": bool(first_base["passed"]),
        "source_second_event_stream_pass": bool(second_base["passed"]),
        "fixed_task_clock": tuple(int(event["task_step"]) for event in events)
        == tuple(range(Q0_STEP, int(spec["horizon_steps"]))),
        "q0_integration_action": float(events[0]["incremental_normalized_action_linf"])
        <= float(ctx.cfg["action_contract"]["maximum_q0_integration_action_linf"]) + 1e-12,
        "second_target_exact": list(second["stored_target_card15_fields"])
        == list(second_source_issue["target_card15_fields"]),
        "equal_pair_zero_increment": (not equal_pair) or zero_second,
        "distinct_pair_nonzero_increment": equal_pair or (not zero_second),
        "all_event_gates": all(bool(event.get("passed")) for event in events),
        "stored_center_return": bool(returned["passed"]),
        "stored_center_current_exact": bool(np.array_equal(
            np.asarray(returned["nominal_readback_current_a_tsc"], dtype=float), center_current
        )),
        "post_return_center_exact": all(
            list(event["stored_target_card15_fields"]) == list(first_events[0]["q0_center_card15_fields"])
            and np.array_equal(np.asarray(event["nominal_readback_current_a_tsc"], dtype=float), center_current)
            for event in post_return
        ),
        "incremental_action_limits": all(
            float(event["incremental_normalized_action_linf"])
            <= float(ctx.cfg["action_contract"]["maximum_incremental_normalized_action_linf"]) + 1e-12
            for event in events
        ),
        "total_action_limits": all(
            max(map(abs, event.get("action_norm_tsc") or [math.inf]))
            <= float(ctx.cfg["action_contract"]["maximum_total_normalized_action_abs"]) + 1e-12
            for event in events
        ),
        "current_utilization_limits": all(
            float(event["predicted_current_utilization"])
            <= float(ctx.cfg["action_contract"]["maximum_current_utilization"]) + 1e-12
            for event in events
        ),
        "finite": all(math.isfinite(value) for value in numerical),
        "no_response_input": spec.get("source_result_available_to_construction") is False,
        "learning_forbidden": spec.get("allowed_in_expert_dataset") is False,
    }
    return {
        "experiment_id": str(spec["experiment_id"]),
        "context_index": int(spec["context_index"]),
        "source_r8r7_baseline_experiment_id": str(spec["source_r8r7_baseline_experiment_id"]),
        "pair_id": str(spec["pair_id"]),
        "history_member": str(spec["history_member"]),
        "first_candidate_id": str(spec["first_candidate_id"]),
        "second_candidate_id": str(spec["second_candidate_id"]),
        "equal_pair": equal_pair,
        "event_count": len(events),
        "action_stream_digest": _digest([_canonical_event(event) for event in events]),
        "maximum_incremental_action_linf": max(float(event.get("incremental_normalized_action_linf", 0.0)) for event in events),
        "maximum_total_normalized_action_abs": max(float(event.get("total_normalized_action_abs", 0.0)) for event in events),
        "maximum_predicted_current_utilization": max(float(event.get("predicted_current_utilization", 0.0)) for event in events),
        "second_transition_cosine": cosine,
        "second_transition_relative_off_basis_residual": off_basis,
        "second_transition_incremental_action_linf": float(second["incremental_normalized_action_linf"]),
        "return_incremental_action_linf": float(returned["incremental_normalized_action_linf"]),
        "post_return_refresh_zero_increment_diagnostic": all(
            np.array_equal(np.asarray(event["action_norm_tsc"], dtype=float), np.zeros(N_COILS))
            for event in post_return
        ),
        "criteria": criteria,
        "eligible": bool(all(criteria.values())),
    }


def evaluate_coverage(rows: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> dict[str, Any]:
    candidate_set = set(CANDIDATE_IDS)
    contexts = []
    for context_index in range(10):
        context_rows = [row for row in rows if int(row["context_index"]) == context_index]
        eligible = [row for row in context_rows if row["eligible"]]
        first = {str(row["first_candidate_id"]) for row in eligible}
        second = {str(row["second_candidate_id"]) for row in eligible}
        successors = {
            candidate: {
                str(row["second_candidate_id"])
                for row in eligible
                if str(row["first_candidate_id"]) == candidate
                and str(row["second_candidate_id"]) != candidate
            }
            for candidate in CANDIDATE_IDS
        }
        gates = {
            "all_ordered_pairs_reported": len(context_rows) == 25,
            "minimum_eligible_pairs": len(eligible) >= int(cfg["coverage_gate"]["minimum_eligible_ordered_pairs_per_context"]),
            "all_first_candidates_supported": first == candidate_set,
            "all_second_candidates_supported": second == candidate_set,
            "distinct_successor_per_first": all(len(successors[candidate]) >= 1 for candidate in CANDIDATE_IDS),
        }
        contexts.append(
            {
                "context_index": context_index,
                "pair_id": str(context_rows[0]["pair_id"]),
                "history_member": str(context_rows[0]["history_member"]),
                "eligible_pair_count": len(eligible),
                "eligible_pair_ids": sorted(
                    f"{row['first_candidate_id']}->{row['second_candidate_id']}" for row in eligible
                ),
                "first_candidate_count": len(first),
                "second_candidate_count": len(second),
                "distinct_successor_counts": {key: len(value) for key, value in successors.items()},
                "gates": gates,
                "passed": bool(all(gates.values())),
            }
        )
    history_pair_rows = []
    for pair_id in sorted({str(row["pair_id"]) for row in contexts}):
        members = [row for row in contexts if row["pair_id"] == pair_id]
        equal = len(members) == 2 and members[0]["eligible_pair_ids"] == members[1]["eligible_pair_ids"]
        history_pair_rows.append({"pair_id": pair_id, "context_indices": [row["context_index"] for row in members], "eligible_pair_set_equal": equal})
    gates = {
        "all_specifications_reported": len(rows) == 250,
        "all_context_gates": len(contexts) == 10 and all(row["passed"] for row in contexts),
        "history_pair_count": len(history_pair_rows) == int(cfg["coverage_gate"]["required_history_pair_count"]),
        "history_pair_eligible_sets_equal": all(row["eligible_pair_set_equal"] for row in history_pair_rows),
    }
    return {
        "eligible_specification_count": sum(bool(row["eligible"]) for row in rows),
        "context_pass_count": sum(bool(row["passed"]) for row in contexts),
        "history_pair_pass_count": sum(bool(row["eligible_pair_set_equal"]) for row in history_pair_rows),
        "contexts": contexts,
        "history_pairs": history_pair_rows,
        "gates": gates,
        "passed": bool(all(gates.values())),
    }


def run_primary(ctx: Context) -> dict[str, Any]:
    if ctx.paths.stage.exists():
        raise ValueError("R8R51R4D1 primary requires a fresh run identity")
    for path in (ctx.paths.stage, ctx.paths.specs, ctx.paths.source_reference, ctx.paths.analysis):
        path.mkdir(parents=True, exist_ok=True)
    try:
        authentication = authenticate_source(ctx)
        specs = build_specs(ctx)
        source_rows = _source_specs(ctx)
        source_by_experiment = {str(row["experiment_id"]): row for row in source_rows}
        cache: dict[str, dict[str, Any]] = {}
        rows = [construct_schedule(ctx, spec, source_by_experiment, cache) for spec in specs]
        coverage = evaluate_coverage(rows, ctx.cfg)
        action_stream_digest = _digest([(row["experiment_id"], row["action_stream_digest"]) for row in rows])
        if action_stream_digest != ctx.cfg["reporting_fix_required_action_stream_digest"]:
            raise SourceBlockedError("R8R51R4D1 reporting fix changed the frozen action streams")
        construction = {
            "schema_version": 1,
            "stage": STAGE,
            "specification_count": len(rows),
            "eligible_specification_count": coverage["eligible_specification_count"],
            "maximum_incremental_action_linf": max(float(row["maximum_incremental_action_linf"]) for row in rows),
            "maximum_total_normalized_action_abs": max(float(row["maximum_total_normalized_action_abs"]) for row in rows),
            "maximum_predicted_current_utilization": max(float(row["maximum_predicted_current_utilization"]) for row in rows),
            "minimum_second_transition_cosine": min(float(row["second_transition_cosine"]) for row in rows),
            "maximum_second_transition_relative_off_basis_residual": max(float(row["second_transition_relative_off_basis_residual"]) for row in rows),
            "action_stream_digest": action_stream_digest,
            "coverage": coverage,
            "rows": rows,
            "passed": bool(coverage["passed"]),
        }
        route = ctx.cfg["routes"]["pass" if construction["passed"] else "geometry_fail"]
        _write(ctx.paths.specs / "all_specs.json", specs)
        _write(ctx.paths.source_reference / "source_authentication.json", authentication)
        _write(ctx.paths.analysis / "offline_construction_primary.json", construction)
        package = r4.r51.r8r7._package_fingerprint()
        manifest = {
            "schema_version": 1,
            "stage": STAGE,
            "identity": IDENTITY,
            "package_revision": ctx.cfg["package_revision"],
            "config_sha256": _sha(ctx.config_path),
            "design_document_sha256": ctx.cfg["design_document_sha256"],
            "source_r51r4_stage": str(ctx.r4_stage),
            "source_authentication_digest": _digest(authentication),
            "spec_count": len(specs),
            "spec_digest": _digest(specs),
            "construction_digest": _digest(construction),
            "package_fingerprint": package,
            "all_stage_trajectories_allowed_in_expert_dataset": False,
        }
        _write(ctx.paths.manifest, manifest)
        _write(
            ctx.paths.state,
            {
                "schema_version": 1,
                "stage": STAGE,
                "phase_status": "offline_primary_complete_independent_required",
                "finished": False,
                "real_tsc_executed": False,
                "plant_step_count": 0,
                "new_raw_count": 0,
                "response_outcomes_opened": False,
                "route": route,
                "verdict": {"route": route, "passed": bool(construction["passed"])},
                "stop_reason": "",
            },
        )
        report = {
            "schema_version": 1,
            "stage": STAGE,
            "phase": "offline_primary",
            "source_authenticated": True,
            "specification_count": len(rows),
            "eligible_specification_count": coverage["eligible_specification_count"],
            "context_pass_count": coverage["context_pass_count"],
            "history_pair_pass_count": coverage["history_pair_pass_count"],
            "maximum_incremental_action_linf": construction["maximum_incremental_action_linf"],
            "maximum_predicted_current_utilization": construction["maximum_predicted_current_utilization"],
            "action_stream_digest": construction["action_stream_digest"],
            "new_tsc_count": 0,
            "plant_step_count": 0,
            "response_values_used": False,
            "route": route,
            "passed": bool(construction["passed"]),
        }
    except SourceBlockedError as exc:
        route = ctx.cfg["routes"]["source_blocked"]
        report = {
            "schema_version": 1,
            "stage": STAGE,
            "phase": "offline_primary",
            "source_authenticated": False,
            "specification_count": 0,
            "eligible_specification_count": 0,
            "new_tsc_count": 0,
            "plant_step_count": 0,
            "response_values_used": False,
            "route": route,
            "passed": False,
            "failure_reason": repr(exc),
        }
        _write(ctx.paths.manifest, {"schema_version": 1, "stage": STAGE, "source_blocked": True})
        _write(ctx.paths.state, {
            "schema_version": 1, "stage": STAGE, "phase_status": "source_blocked",
            "finished": True, "real_tsc_executed": False, "plant_step_count": 0,
            "new_raw_count": 0, "response_outcomes_opened": False, "route": route,
            "verdict": {"route": route, "passed": False},
            "stop_reason": "source_authentication_failed",
        })
    _write(ctx.paths.analysis / "offline_primary.json", report)
    return report


def _parser() -> argparse.ArgumentParser:
    parser = r4._parser()
    parser.description = __doc__
    parser.add_argument("--r51r4-run", type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command != "offline":
        raise ValueError("R8R51R4D1 is zero-TSC and supports only offline")
    result = run_primary(load_context(args))
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
