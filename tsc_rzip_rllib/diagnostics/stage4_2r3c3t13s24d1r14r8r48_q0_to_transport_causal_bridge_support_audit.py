"""R8R48 zero-TSC q0-to-transport causal-bridge support audit."""

from __future__ import annotations

import argparse
import copy
import json
import math
import traceback
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r31_aligned_explicit_four_coordinate_feedback_sentinel
    as r8r31,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r46_q0_calibration_causal_innovation_controller_preflight
    as r8r46,
)


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S24D1R14R8R48"
IDENTITY = "q0_to_transport_causal_bridge_support_audit_v1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r48_q0_to_transport_causal_bridge_support_audit"
ZERO_Q = np.zeros(4, dtype=np.float64)

_read = r8r46._read
_write = r8r46._write
_sha = r8r46._sha
_digest = r8r46._digest
_jsonable = r8r46._jsonable


class SourceBlockedError(RuntimeError):
    pass


@dataclass(frozen=True)
class Paths:
    stage: Path
    analysis: Path
    state: Path
    manifest: Path


@dataclass(frozen=True)
class Context:
    cfg: dict[str, Any]
    config_path: Path
    paths: Paths
    r8r46_ctx: r8r46.Context
    r8r46_stage: Path

    @property
    def source_ctx(self):
        return self.r8r46_ctx.source_ctx


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _paths(run_dir: Path) -> Paths:
    stage = run_dir.expanduser().resolve() / RUN_NAME
    return Paths(
        stage=stage,
        analysis=stage / "analysis",
        state=stage / "stage_state.json",
        manifest=stage / "stage_manifest.json",
    )


def validate_config(cfg: Mapping[str, Any], *, project_root: Path) -> None:
    bridge = cfg.get("bridge_contract", {})
    geometry = cfg.get("geometric_diagnostic_contract", {})
    scope = cfg.get("scientific_scope", {})
    routes = {
        "source_blocked": "Q0_TO_TRANSPORT_CAUSAL_BRIDGE_AUDIT_BLOCKED_BY_SOURCE",
        "execution_fail": "Q0_TO_TRANSPORT_CAUSAL_BRIDGE_AUDIT_EXECUTION_FAIL_STOP",
        "support_absent": "Q0_CALIBRATION_TO_TRANSPORT_CAUSAL_BRIDGE_SUPPORT_ABSENT_FRESH_SENTINEL_REQUIRED",
        "support_present": "Q0_CALIBRATION_TO_TRANSPORT_CAUSAL_BRIDGE_SUPPORT_PRESENT_REANALYSIS_REQUIRED",
    }
    design = project_root / str(cfg.get("design_document", ""))
    source = project_root / str(cfg.get("source_r8r46_config", ""))
    invalid = (
        cfg.get("schema_version") != SCHEMA_VERSION
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("run_name") != RUN_NAME
        or not design.is_file()
        or _sha(design) != cfg.get("design_document_sha256")
        or not source.is_file()
        or _sha(source) != cfg.get("source_r8r46_config_sha256")
        or cfg.get("source_r8r46", {}).get("required_route")
        != "Q0_CALIBRATION_CAUSAL_INNOVATION_MODEL_INSUFFICIENT_NO_TSC"
        or list(bridge.get("decision_task_steps", [])) != [10, 12, 14, 16, 18, 22]
        or tuple(int(bridge.get(key, -1)) for key in (
            "prefix_through_task_step",
            "primary_transport_interval",
            "primary_transport_task_step",
            "required_q0_reference_context_count",
            "candidate_count",
            "nonzero_candidate_count",
            "required_bridge_cell_count",
        )) != (12, 1, 12, 16, 17, 16, 256)
        or any(bridge.get(key) is not True for key in (
            "require_exact_binary64_q", "require_exact_physical_prefix"
        ))
        or any(bridge.get(key) is not False for key in (
            "metadata_only_support_allowed",
            "later_interval_substitution_allowed",
            "candidate_or_context_selection_allowed",
        ))
        or geometry.get("canonical_matrix_float64_le_c_sha256")
        != "c8cd62c00c1f60b46312927789659657dc8cc35717533193433b0e398c1ec94c"
        or tuple(int(geometry.get(key, -1)) for key in (
            "transition_dimension", "feature_dimension"
        )) != (8, 44)
        or float(geometry.get("primary_independent_distance_tolerance", -1.0)) != 1e-12
        or geometry.get("geometric_support_substitutes_for_physical_bridge") is not False
        or cfg.get("routes") != routes
        or scope.get("zero_new_tsc") is not True
        or any(scope.get(key) is not False for key in (
            "model_fit_allowed",
            "controller_execution_authorized",
            "gate_a_qualified",
            "expert_data_allowed",
            "bc_dagger_or_rl_allowed",
            "all_stage_trajectories_allowed_in_expert_dataset",
            "global_plant_reachability_claimed",
        ))
    )
    if invalid:
        raise ValueError("R8R48 frozen config changed")


def load_context(args: argparse.Namespace) -> Context:
    root = _root()
    config_path = args.config.expanduser().resolve()
    cfg = _read(config_path)
    validate_config(cfg, project_root=root)
    source_args = SimpleNamespace(**vars(args))
    source_args.config = (root / str(cfg["source_r8r46_config"])).resolve()
    source_args.run_dir = args.r8r46_run.expanduser().resolve()
    source_ctx = r8r46.load_context(source_args)
    return Context(
        cfg=cfg,
        config_path=config_path,
        paths=_paths(args.run_dir),
        r8r46_ctx=source_ctx,
        r8r46_stage=source_ctx.paths.stage,
    )


def _r8r46_paths(stage: Path) -> dict[str, Path]:
    return {
        "primary_summary": stage / "analysis/primary_summary.json",
        "primary_detailed": stage / "analysis/primary_detailed.json",
        "model": stage / "model/preflight_model.json",
        "independent": stage / "analysis/independent.json",
        "compact_audit": stage / "analysis/compact_audit.json",
        "final_report": stage / "analysis/final_report.json",
        "stage_state": stage / "stage_state.json",
        "stage_manifest": stage / "stage_manifest.json",
    }


def authenticate_sources(ctx: Context) -> dict[str, Any]:
    paths = _r8r46_paths(ctx.r8r46_stage)
    contract = ctx.cfg["source_r8r46"]
    if any(not path.is_file() for path in paths.values()):
        raise SourceBlockedError("R8R48 R8R46 source evidence incomplete")
    hashes = {name: _sha(path) for name, path in paths.items()}
    if any(hashes[name] != contract[f"{name}_sha256"] for name in hashes):
        raise SourceBlockedError("R8R48 R8R46 source hash changed")
    summary = _read(paths["primary_summary"])
    final = _read(paths["final_report"])
    state = _read(paths["stage_state"])
    if (
        summary.get("route") != contract["required_route"]
        or final.get("route") != contract["required_route"]
        or state.get("route") != contract["required_route"]
        or final.get("passed") is not True
        or state.get("finished") is not True
        or not bool(final.get("independent_agreement"))
        or bool(final.get("real_tsc_executed"))
        or int(final.get("plant_step_count", -1)) != 0
        or int(final.get("new_raw_count", -1)) != 0
    ):
        raise SourceBlockedError("R8R48 R8R46 final outcome changed")
    return {"hashes": hashes, "required_route": contract["required_route"], "passed": True}


def verify_bank(bank: Mapping[str, Any], cfg: Mapping[str, Any]) -> None:
    expected = cfg["bank_contract"]
    if any(bank.get(key) != expected[key] for key in (
        "trajectory_count", "context_count", "schedule_count",
        "interval_record_count", "bank_digest", "feature_digest", "target_digest"
    )):
        raise SourceBlockedError("R8R48 source bank identity changed")


def _prefix_payload(trajectory: Mapping[str, Any], through: int = 12) -> dict[str, Any]:
    states = np.asarray(trajectory["states"], dtype=np.float64)
    raw = list(trajectory["trajectory"])
    if states.shape[0] <= through or len(raw) <= through:
        raise ValueError("R8R48 source prefix is incomplete")
    return _jsonable({
        "states": states[: through + 1],
        "trajectory": raw[: through + 1],
    })


def _context_key(row: Mapping[str, Any]) -> tuple[str, str]:
    return str(row["pair_id"]), str(row["history_member"])


def enumerate_bridges(
    trajectories: Sequence[Mapping[str, Any]],
    candidates: Sequence[Mapping[str, Any]],
    *,
    prefix_through: int = 12,
) -> dict[str, Any]:
    contexts = sorted({_context_key(row) for row in trajectories})
    nonzero = [row for row in candidates if int(row["index"]) != 0]
    q0_by_context: dict[tuple[str, str], Mapping[str, Any]] = {}
    for key in contexts:
        rows = [row for row in trajectories if _context_key(row) == key and str(row["schedule_id"]) == "q0"]
        if len(rows) != 1:
            raise ValueError("R8R48 q0 reference cardinality changed")
        interval0 = rows[0]["intervals"][0]
        if (
            int(interval0["decision"]) != 10
            or not np.array_equal(np.asarray(interval0["q"], dtype=np.float64), ZERO_Q)
            or not np.array_equal(np.asarray(interval0["previous_q"], dtype=np.float64), ZERO_Q)
        ):
            raise ValueError("R8R48 q0 reference metadata changed")
        q0_by_context[key] = rows[0]

    cells: list[dict[str, Any]] = []
    context_rows: list[dict[str, Any]] = []
    later_counts = 0
    for key in contexts:
        reference = q0_by_context[key]
        reference_payload = _prefix_payload(reference, prefix_through)
        reference_digest = _digest(reference_payload)
        same_context = [row for row in trajectories if _context_key(row) == key]
        exact_prefix_rows = [
            row for row in same_context
            if _prefix_payload(row, prefix_through) == reference_payload
        ]
        context_present = 0
        for candidate in nonzero:
            q = np.asarray(candidate["q"], dtype=np.float64)
            matches = []
            metadata_matches = []
            later_matches = []
            for trajectory in same_context:
                interval0 = trajectory["intervals"][0]
                exact_q0 = (
                    np.array_equal(np.asarray(interval0["previous_q"], dtype=np.float64), ZERO_Q)
                    and np.array_equal(np.asarray(interval0["q"], dtype=np.float64), ZERO_Q)
                )
                interval1 = trajectory["intervals"][1]
                primary_metadata = (
                    exact_q0
                    and int(interval1["decision"]) == 12
                    and np.array_equal(np.asarray(interval1["previous_q"], dtype=np.float64), ZERO_Q)
                    and np.array_equal(np.asarray(interval1["q"], dtype=np.float64), q)
                    and len(interval1["targets"]) > 0
                )
                if primary_metadata:
                    metadata_matches.append(str(trajectory["trajectory_id"]))
                    if _prefix_payload(trajectory, prefix_through) == reference_payload:
                        matches.append(str(trajectory["trajectory_id"]))
                if exact_q0:
                    for interval in trajectory["intervals"][2:]:
                        if np.array_equal(np.asarray(interval["q"], dtype=np.float64), q):
                            later_matches.append(str(trajectory["trajectory_id"]))
                            break
            present = bool(matches)
            context_present += int(present)
            later_counts += int(bool(later_matches))
            cells.append({
                "pair_id": key[0],
                "history_member": key[1],
                "candidate_index": int(candidate["index"]),
                "candidate_id": str(candidate["id"]),
                "candidate_q": q.tolist(),
                "reference_q0_trajectory_id": str(reference["trajectory_id"]),
                "reference_prefix_digest": reference_digest,
                "metadata_match_count": len(set(metadata_matches)),
                "metadata_match_trajectory_ids": sorted(set(metadata_matches)),
                "authentic_bridge_count": len(set(matches)),
                "authentic_bridge_trajectory_ids": sorted(set(matches)),
                "later_interval_match_count": len(set(later_matches)),
                "later_interval_match_trajectory_ids": sorted(set(later_matches)),
                "authentic_bridge_present": present,
            })
        context_rows.append({
            "pair_id": key[0],
            "history_member": key[1],
            "q0_trajectory_id": str(reference["trajectory_id"]),
            "q0_prefix_digest": reference_digest,
            "exact_prefix_trajectory_count": len(exact_prefix_rows),
            "authentic_candidate_coverage_count": context_present,
            "complete_candidate_coverage": context_present == len(nonzero),
        })
    present_count = sum(bool(row["authentic_bridge_present"]) for row in cells)
    serial = [
        {key: value for key, value in row.items() if key not in {"metadata_match_trajectory_ids", "later_interval_match_trajectory_ids"}}
        for row in cells
    ]
    return {
        "q0_reference_context_count": len(q0_by_context),
        "nonzero_candidate_count": len(nonzero),
        "required_bridge_cell_count": len(contexts) * len(nonzero),
        "authentic_bridge_cell_count": present_count,
        "missing_bridge_cell_count": len(cells) - present_count,
        "metadata_only_bridge_cell_count": sum(
            row["metadata_match_count"] > 0 and not row["authentic_bridge_present"] for row in cells
        ),
        "later_interval_candidate_cell_count": later_counts,
        "complete_physical_bridge_support": present_count == len(cells),
        "q0_prefix_digest": _digest(sorted(
            ({"pair_id": row["pair_id"], "history_member": row["history_member"], "digest": row["q0_prefix_digest"]} for row in context_rows),
            key=lambda row: (row["pair_id"], row["history_member"]),
        )),
        "bridge_matrix_digest": _digest(serial),
        "contexts": context_rows,
        "cells": cells,
    }


def geometric_diagnostics(
    trajectories: Sequence[Mapping[str, Any]],
    candidates: Sequence[Mapping[str, Any]],
    source_cfg: Mapping[str, Any],
    bridge: Mapping[str, Any],
) -> dict[str, Any]:
    support = r8r31.planning_support(trajectories, source_cfg)
    hulls = r8r31.transition_hulls(trajectories, source_cfg)
    interval = 1
    training = np.asarray(support["features"][interval], dtype=np.float64)
    threshold = float(support["thresholds"][interval])
    candidates_by_index = {int(row["index"]): row for row in candidates}
    q0 = {
        _context_key(row): row
        for row in trajectories
        if str(row["schedule_id"]) == "q0"
    }
    rows = []
    for cell in bridge["cells"]:
        key = (str(cell["pair_id"]), str(cell["history_member"]))
        feature = np.asarray(q0[key]["intervals"][interval]["feature"], dtype=np.float64)
        distance = float(np.min(np.linalg.norm(training - feature, axis=1)))
        candidate = candidates_by_index[int(cell["candidate_index"])]
        hull_pass = r8r31.transition_supported(
            hulls[interval], ZERO_Q, np.asarray(candidate["q"], dtype=np.float64), source_cfg
        )
        rows.append({
            "pair_id": key[0],
            "history_member": key[1],
            "candidate_index": int(candidate["index"]),
            "candidate_id": str(candidate["id"]),
            "transition_hull_supported": bool(hull_pass),
            "nearest_feature_distance": distance,
            "feature_support_threshold": threshold,
            "feature_supported": distance <= threshold + 1e-15,
            "authentic_bridge_present": bool(cell["authentic_bridge_present"]),
        })
    return {
        "interval": interval,
        "transition_hull_supported_cell_count": sum(row["transition_hull_supported"] for row in rows),
        "feature_supported_cell_count": sum(row["feature_supported"] for row in rows),
        "physical_bridge_cell_count": sum(row["authentic_bridge_present"] for row in rows),
        "maximum_nearest_feature_distance": max(row["nearest_feature_distance"] for row in rows),
        "feature_support_threshold": threshold,
        "geometric_support_substitutes_for_physical_bridge": False,
        "diagnostic_digest": _digest(rows),
        "cells": rows,
    }


def assemble_result(
    cfg: Mapping[str, Any],
    authentication: Mapping[str, Any],
    bank: Mapping[str, Any],
    bridge: Mapping[str, Any],
    geometry: Mapping[str, Any],
) -> dict[str, Any]:
    contract = cfg["bridge_contract"]
    integrity = bool(
        authentication.get("passed")
        and int(bridge["q0_reference_context_count"]) == int(contract["required_q0_reference_context_count"])
        and int(bridge["nonzero_candidate_count"]) == int(contract["nonzero_candidate_count"])
        and int(bridge["required_bridge_cell_count"]) == int(contract["required_bridge_cell_count"])
    )
    support_present = bool(integrity and bridge["complete_physical_bridge_support"])
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "identity": IDENTITY,
        "source_authentication": authentication,
        "bank_evidence": bank,
        "bridge_audit": bridge,
        "geometric_diagnostics": geometry,
        "integrity_gate_passed": integrity,
        "scientific_gate_passed": support_present,
        "passed": integrity,
        "route": cfg["routes"]["support_present" if support_present else "support_absent"],
        "real_tsc_executed": False,
        "plant_step_count": 0,
        "new_raw_count": 0,
        "model_fit_count": 0,
        "controller_execution_authorized": False,
        "gate_a_qualified": False,
        "expert_data_allowed": False,
    }


def compute(
    ctx: Context,
    authentication: Mapping[str, Any],
    trajectories: Sequence[Mapping[str, Any]],
    bank: Mapping[str, Any],
) -> dict[str, Any]:
    verify_bank(bank, ctx.cfg)
    candidates = r8r31._candidate_rows(ctx.source_ctx.cfg)
    if len(candidates) != int(ctx.cfg["bridge_contract"]["candidate_count"]):
        raise SourceBlockedError("R8R48 candidate library changed")
    bridge = enumerate_bridges(trajectories, candidates)
    geometry = geometric_diagnostics(trajectories, candidates, ctx.source_ctx.cfg, bridge)
    return assemble_result(ctx.cfg, authentication, bank, bridge, geometry)


def _summary(detailed: Mapping[str, Any]) -> dict[str, Any]:
    bridge = detailed["bridge_audit"]
    geometry = detailed["geometric_diagnostics"]
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "identity": IDENTITY,
        "phase": "offline_primary",
        "passed": bool(detailed["passed"]),
        "integrity_gate_passed": bool(detailed["integrity_gate_passed"]),
        "scientific_gate_passed": bool(detailed["scientific_gate_passed"]),
        "route": detailed["route"],
        "trajectory_count": int(detailed["bank_evidence"]["trajectory_count"]),
        "context_count": int(detailed["bank_evidence"]["context_count"]),
        "schedule_count": int(detailed["bank_evidence"]["schedule_count"]),
        "interval_record_count": int(detailed["bank_evidence"]["interval_record_count"]),
        "bank_digest": detailed["bank_evidence"]["bank_digest"],
        "q0_reference_context_count": int(bridge["q0_reference_context_count"]),
        "required_bridge_cell_count": int(bridge["required_bridge_cell_count"]),
        "authentic_bridge_cell_count": int(bridge["authentic_bridge_cell_count"]),
        "missing_bridge_cell_count": int(bridge["missing_bridge_cell_count"]),
        "metadata_only_bridge_cell_count": int(bridge["metadata_only_bridge_cell_count"]),
        "later_interval_candidate_cell_count": int(bridge["later_interval_candidate_cell_count"]),
        "transition_hull_supported_cell_count": int(geometry["transition_hull_supported_cell_count"]),
        "feature_supported_cell_count": int(geometry["feature_supported_cell_count"]),
        "q0_prefix_digest": bridge["q0_prefix_digest"],
        "bridge_matrix_digest": bridge["bridge_matrix_digest"],
        "geometric_diagnostic_digest": geometry["diagnostic_digest"],
        "real_tsc_executed": False,
        "plant_step_count": 0,
        "new_raw_count": 0,
        "model_fit_count": 0,
        "controller_execution_authorized": False,
        "gate_a_qualified": False,
        "expert_data_allowed": False,
    }


def run_primary(ctx: Context) -> dict[str, Any]:
    if ctx.paths.stage.exists():
        raise ValueError("R8R48 primary requires a fresh stage directory")
    ctx.paths.stage.mkdir(parents=True)
    ctx.paths.analysis.mkdir()
    try:
        authentication = authenticate_sources(ctx)
        trajectories, _context_meta, bank = r8r31.build_bank(ctx.source_ctx)
        detailed = compute(ctx, authentication, trajectories, bank)
        detailed_path = ctx.paths.analysis / "primary_detailed.json"
        summary_path = ctx.paths.analysis / "primary_summary.json"
        _write(detailed_path, detailed)
        summary = _summary(detailed)
        _write(summary_path, summary)
        _write(ctx.paths.manifest, {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "identity": IDENTITY,
            "config_sha256": _sha(ctx.config_path),
            "design_sha256": str(ctx.cfg["design_document_sha256"]),
            "primary_summary_sha256": _sha(summary_path),
            "primary_detailed_sha256": _sha(detailed_path),
            "zero_tsc_audit": True,
        })
        _write(ctx.paths.state, {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "phase_status": "offline_primary_ready_for_independent",
            "finished": False,
            "primary_completed": True,
            "independent_completed": False,
            "scientific_gate_passed": bool(summary["scientific_gate_passed"]),
            "route": summary["route"],
            "real_tsc_executed": False,
            "plant_step_count": 0,
            "new_raw_count": 0,
        })
        return summary
    except Exception as exc:
        route = ctx.cfg["routes"]["source_blocked" if isinstance(exc, SourceBlockedError) else "execution_fail"]
        failure = {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "identity": IDENTITY,
            "phase": "offline_primary",
            "passed": False,
            "integrity_gate_passed": False,
            "scientific_gate_passed": False,
            "route": route,
            "failure_reason": repr(exc),
            "traceback": traceback.format_exc(),
            "real_tsc_executed": False,
            "plant_step_count": 0,
            "new_raw_count": 0,
        }
        _write(ctx.paths.analysis / "primary_failure.json", failure)
        _write(ctx.paths.state, {**failure, "phase_status": "offline_primary_execution_failed"})
        raise


AGREEMENT_FIELDS = (
    "primary_source_agreement",
    "primary_bank_agreement",
    "primary_prefix_agreement",
    "primary_bridge_matrix_agreement",
    "primary_geometric_agreement",
    "primary_route_agreement",
    "primary_outcome_agreement",
)


def run_finalize(ctx: Context) -> dict[str, Any]:
    paths = {
        "primary_summary": ctx.paths.analysis / "primary_summary.json",
        "primary_detailed": ctx.paths.analysis / "primary_detailed.json",
        "independent": ctx.paths.analysis / "independent.json",
    }
    if any(not path.is_file() for path in (*paths.values(), ctx.paths.manifest, ctx.paths.state)):
        raise ValueError("R8R48 finalization evidence incomplete")
    summary = _read(paths["primary_summary"])
    detailed = _read(paths["primary_detailed"])
    independent = _read(paths["independent"])
    hashes = {name: _sha(path) for name, path in paths.items()}
    tolerance = float(ctx.cfg["geometric_diagnostic_contract"]["primary_independent_distance_tolerance"])
    agreement = bool(
        independent.get("passed") is True
        and all(independent.get(field) is True for field in AGREEMENT_FIELDS)
        and float(independent.get("maximum_geometric_distance_difference", math.inf)) <= tolerance
        and independent.get("primary_summary_sha256") == hashes["primary_summary"]
        and independent.get("primary_detailed_sha256") == hashes["primary_detailed"]
        and independent.get("route") == summary.get("route")
        and not bool(independent.get("real_tsc_executed"))
        and int(independent.get("plant_step_count", -1)) == 0
        and int(independent.get("new_raw_count", -1)) == 0
    )
    if not agreement:
        raise ValueError("R8R48 finalization independent disagreement")
    compact = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "identity": IDENTITY,
        "audit_kind": "r8r48_compact_primary_independent_finalization",
        "passed": True,
        "integrity_gate_passed": True,
        "scientific_gate_passed": bool(summary["scientific_gate_passed"]),
        "route": summary["route"],
        "source_file_sha256": hashes,
        "summary": summary,
        "source_authentication": detailed["source_authentication"],
        "bank_evidence": detailed["bank_evidence"],
        "bridge_summary": {key: value for key, value in detailed["bridge_audit"].items() if key != "cells"},
        "geometric_summary": {key: value for key, value in detailed["geometric_diagnostics"].items() if key != "cells"},
        "missing_bridge_cells": [
            {key: row[key] for key in (
                "pair_id", "history_member", "candidate_index", "candidate_id",
                "metadata_match_count", "later_interval_match_count"
            )}
            for row in detailed["bridge_audit"]["cells"]
            if not bool(row["authentic_bridge_present"])
        ],
        "independent_agreement": {field: independent.get(field) for field in AGREEMENT_FIELDS},
        "maximum_geometric_distance_difference": independent.get("maximum_geometric_distance_difference"),
        "real_tsc_executed": False,
        "plant_step_count": 0,
        "new_raw_count": 0,
        "model_fit_count": 0,
        "controller_execution_authorized": False,
        "gate_a_qualified": False,
        "expert_data_allowed": False,
    }
    compact_path = ctx.paths.analysis / "compact_audit.json"
    _write(compact_path, compact)
    final = copy.deepcopy(compact)
    final["audit_kind"] = "r8r48_final_report"
    final["compact_audit_sha256"] = _sha(compact_path)
    final_path = ctx.paths.analysis / "final_report.json"
    _write(final_path, final)
    manifest = _read(ctx.paths.manifest)
    manifest.update({
        "independent_sha256": hashes["independent"],
        "compact_audit_sha256": _sha(compact_path),
        "final_report_sha256": _sha(final_path),
        "final_route": summary["route"],
        "independent_completed": True,
        "independent_validation_passed": True,
    })
    _write(ctx.paths.manifest, manifest)
    state = _read(ctx.paths.state)
    state.update({
        "phase_status": "offline_audit_final",
        "finished": True,
        "independent_completed": True,
        "independent_validation_passed": True,
        "scientific_gate_passed": bool(summary["scientific_gate_passed"]),
        "primary_route": summary["route"],
        "route": summary["route"],
    })
    _write(ctx.paths.state, state)
    return final


ARGUMENT_NAMES = ("config", "run-dir", "r8r46-run") + tuple(
    name for name in r8r46.ARGUMENT_NAMES if name not in {"config", "run-dir"}
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ARGUMENT_NAMES:
        parser.add_argument(f"--{name}", dest=name.replace("-", "_"), type=Path, required=True)
    parser.add_argument("--command", choices=("primary", "finalize"), default="primary")
    return parser


def main() -> None:
    args = _parser().parse_args()
    ctx = load_context(args)
    result = run_primary(ctx) if args.command == "primary" else run_finalize(ctx)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
