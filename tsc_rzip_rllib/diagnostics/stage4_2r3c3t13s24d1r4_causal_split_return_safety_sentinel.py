"""Stage4.2R3c3T13S24D1R4 authentic split-return safety sentinel."""

from __future__ import annotations

import argparse
import copy
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path
from types import SimpleNamespace
import time
import traceback
from typing import Any, Mapping, Sequence

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r3_causal_split_return_preflight as d1r3,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r2_real_tsc_safety_sentinel as d1r2,
)


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S24D1R4"
RUN_NAME = "stage4_2r3c3t13s24d1r4_causal_split_return_safety_sentinel"
CAMPAIGN_IDENTITY = "causal_split_exact_return_safety_sentinel_v1"
CONTROLLER_REVISION = "causal_split_exact_return_probe_v42r3c3t13s24d1r4_v1"
PACKAGE_REVISION = "r42r3c3t13s24d1r4_causal_split_return_safety_sentinel_v1h1"
N_COILS = 14


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
    )


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _write_json_gz(path: Path, value: Any) -> None:
    d1r2._write_json_gz(path, value)


def _package_path(cfg: Mapping[str, Any], key: str) -> Path:
    root = _project_root()
    path = (root / str(cfg[key])).resolve()
    if path != root and root not in path.parents:
        raise ValueError(f"D1R4 {key} is outside package")
    return path


@dataclass(frozen=True)
class Paths:
    run_dir: Path
    stage_dir: Path
    variants: Path
    specs: Path
    source_reference: Path
    raw: Path
    analysis: Path
    state: Path
    manifest: Path
    final: Path


def _paths(run_dir: Path) -> Paths:
    root = run_dir.expanduser().resolve()
    stage = root / RUN_NAME
    return Paths(
        run_dir=root,
        stage_dir=stage,
        variants=stage / "variants",
        specs=stage / "specs",
        source_reference=stage / "source_reference",
        raw=stage / "raw",
        analysis=stage / "analysis",
        state=stage / "stage_state.json",
        manifest=stage / "stage_manifest.json",
        final=stage / "final_result.json",
    )


@dataclass(frozen=True)
class Context:
    cfg: dict[str, Any]
    config_path: Path
    base_d1r2_ctx: d1r2.Context
    source_d1r2_run: Path
    source_d1r3_output: Path
    source_d1r3_primary_log: Path
    source_d1r3_repeat_log: Path
    paths: Paths


def _validate_config(cfg: Mapping[str, Any], config_path: Path) -> None:
    exact = {
        "schema_version": 1,
        "stage": STAGE,
        "run_name": RUN_NAME,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "selection_status": "frozen_after_d1r3_pass_before_d1r4_implementation_or_tsc",
    }
    if any(cfg.get(key) != value for key, value in exact.items()):
        raise ValueError("D1R4 frozen identity changed")
    expected_config = (
        _project_root()
        / "configs/stage4_2r3c3t13s24d1r4_causal_split_return_safety_sentinel_350ms.json"
    ).resolve()
    if config_path.resolve() != expected_config:
        raise ValueError("D1R4 config path changed")
    for key in (
        "design_document",
        "base_d1r2_config",
        "base_d1r2_implementation",
        "d1r3_implementation",
    ):
        path = _package_path(cfg, key)
        if not path.is_file() or _sha256(path) != str(cfg[f"{key}_sha256"]):
            raise ValueError(f"D1R4 frozen {key} hash changed")
    source = cfg["source_contract"]
    if (
        source["d1r2_raw_count"] != 54
        or source["d1r2_raw_total_bytes"] != 3_078_383
        or source["d1r3_replay_count"] != 54
        or source["d1r3_full_success_count"] != 45
        or source["d1r3_structured_stop_count"] != 9
        or source["d1r3_split_start_pass_count"] != 9
        or any(
            len(str(value)) != 64
            for key, value in source.items()
            if key.endswith("sha256") or key.endswith("digest")
        )
    ):
        raise ValueError("D1R4 source contract changed")
    split = cfg["split_contract"]
    if (
        float(split["direct_cancel_threshold"]) != 0.24
        or float(split["split_construction_target_increment"]) != 0.175
        or float(split["maximum_split_start_increment"]) != 0.18
        or float(split["maximum_finish_increment"]) != 0.24
        or float(split["maximum_original_increment"]) != 0.25
        or float(split["maximum_total_normalized_action_abs"]) != 1.0
        or float(split["maximum_current_utilization"]) != 0.55
        or int(split["split_start_task_step"]) != 18
        or int(split["split_finish_task_step"]) != 19
        or int(split["split_slot"]) != 3
        or not bool(split["one_plant_advance_between_start_and_finish"])
        or not bool(split["require_exact_card15_intermediate_and_finish"])
        or not bool(split["require_exact_decimal_telescoping_net"])
        or not bool(split["require_no_saturation_or_clipping"])
        or bool(split["finish_retry_or_deferral_allowed"])
    ):
        raise ValueError("D1R4 split state machine changed")
    specs = cfg["spec_contract"]
    if (
        specs["expected_specs"] != 9
        or specs["expected_snapshots"] != 3
        or specs["expected_horizon_counts"] != {"35": 9, "37": 0}
        or specs["expected_sequence_index_counts"]
        != {"6": 3, "10": 3, "18": 3}
        or not all(
            bool(specs[key])
            for key in (
                "fresh_tsc_process_required",
                "fresh_controller_required",
                "full_horizon_required",
            )
        )
        or bool(specs["source_outcome_available_to_controller"])
        or bool(specs["pair_history_partition_label_available_to_controller"])
    ):
        raise ValueError("D1R4 task matrix changed")
    gate = cfg["execution_gate"]
    expected_gate = {
        "raw_files_required": 9,
        "fresh_actor_tsc_controller_required": 9,
        "strict_parse_required": 9,
        "restart_required": 9,
        "causality_required": 9,
        "calibration_required": 9,
        "full_horizon_required": 9,
        "issue_events_required": 36,
        "direct_cancel_events_required": 27,
        "split_start_events_required": 9,
        "split_finish_events_required": 9,
        "forbidden_use_count_required": 0,
    }
    if dict(gate) != expected_gate:
        raise ValueError("D1R4 execution gates changed")
    formal = cfg["formal_timing_contract"]
    if (
        formal["normal"] != {"arrival_deadline_step": 25, "hold_through_step": 35}
        or formal["weak"] != {"arrival_deadline_step": 27, "hold_through_step": 37}
        or float(formal["position_tolerance_m"]) != 0.03
        or float(formal["speed_tolerance_m_per_s"]) != 0.1
        or float(formal["ip_tolerance_A"]) != 10_000.0
        or int(formal["arrival_streak_steps"]) != 3
        or bool(formal["arrival_deadline_expansion_allowed"])
        or not bool(formal["formal_tracking_is_diagnostic_only"])
    ):
        raise ValueError("D1R4 formal timing changed")
    if cfg["routes"] != {
        "source_stop": "CAUSAL_SPLIT_RETURN_SENTINEL_SOURCE_STOP",
        "runtime_incomplete": "CAUSAL_SPLIT_RETURN_SENTINEL_RUNTIME_INCOMPLETE",
        "action_fail": "CAUSAL_SPLIT_RETURN_SENTINEL_FAIL_REDESIGN_REQUIRED",
        "pass": "CAUSAL_SPLIT_RETURN_SENTINEL_PASS_FULL_REPLACEMENT_CAMPAIGN_DESIGN_REQUIRED",
    }:
        raise ValueError("D1R4 routes changed")
    if int(cfg["parallel"]["n_workers"]) != 9:
        raise ValueError("D1R4 capacity changed")
    scope = cfg["scientific_scope"]
    if (
        not bool(scope["development_set_real_tsc_safety_sentinel_only"])
        or bool(scope["model_fit_executed"])
        or bool(scope["real_mpc_executed"])
        or not bool(scope["pass_authorizes_full_replacement_campaign_design_only"])
        or bool(scope["pass_authorizes_mpc"])
        or bool(scope["probe_trajectories_allowed_in_expert_dataset"])
        or bool(scope["independent_long_hold_validated"])
        or bool(scope["bc_dagger_or_rl_allowed"])
    ):
        raise ValueError("D1R4 scientific scope changed")


def load_config(
    config_path: Path,
    *,
    source_d1r2_run: Path,
    source_d1r3_output: Path,
    source_d1r3_primary_log: Path,
    source_d1r3_repeat_log: Path,
    source_d1r1_output: Path,
    source_d1r1_log: Path,
    source_s21_run: Path,
    source_s23r1_output: Path,
    run_dir: Path,
    **source_kwargs: Path,
) -> Context:
    config_path = config_path.expanduser().resolve()
    cfg = _read_json(config_path)
    _validate_config(cfg, config_path)
    base = d1r2.load_config(
        _package_path(cfg, "base_d1r2_config"),
        source_d1r1_output=source_d1r1_output,
        source_d1r1_log=source_d1r1_log,
        source_s21_run=source_s21_run,
        source_s23r1_output=source_s23r1_output,
        run_dir=run_dir,
        **source_kwargs,
    )
    return Context(
        cfg=dict(cfg),
        config_path=config_path,
        base_d1r2_ctx=base,
        source_d1r2_run=source_d1r2_run.expanduser().resolve(),
        source_d1r3_output=source_d1r3_output.expanduser().resolve(),
        source_d1r3_primary_log=source_d1r3_primary_log.expanduser().resolve(),
        source_d1r3_repeat_log=source_d1r3_repeat_log.expanduser().resolve(),
        paths=_paths(run_dir),
    )


def _raw_inventory(raw_dir: Path) -> dict[str, Any]:
    rows = []
    digest = hashlib.sha256()
    for path in sorted(raw_dir.glob("*.json.gz")):
        sha = _sha256(path)
        size = path.stat().st_size
        digest.update(f"{path.name}\0{size}\0{sha}\n".encode())
        rows.append({"path": path.name, "bytes": size, "sha256": sha})
    return {
        "count": len(rows),
        "total_bytes": sum(int(row["bytes"]) for row in rows),
        "digest": digest.hexdigest(),
        "files": rows,
    }


def _selected_snapshot_audit(
    contexts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Re-aggregate the inherited per-snapshot audit for D1R4's subset."""
    source_audit = d1r2.s24.s21._snapshot_audit(contexts)
    rows = list(source_audit.get("rows") or [])
    pass_count = sum(bool(row.get("passed")) for row in rows)
    expected = 3
    passed = bool(
        len(contexts) == expected
        and len(rows) == expected
        and pass_count == expected
        and all(bool(row.get("passed")) for row in rows)
    )
    return {
        "expected": expected,
        "actual": len(rows),
        "pass_count": pass_count,
        "passed": passed,
        "rows": rows,
        "source_helper_expected": source_audit.get("expected"),
        "source_helper_actual": source_audit.get("actual"),
        "source_helper_pass_count": source_audit.get("pass_count"),
        "source_helper_passed": source_audit.get("passed"),
    }


def _authenticate_source(
    ctx: Context,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    source = ctx.cfg["source_contract"]
    if ctx.source_d1r2_run.name != source["d1r2_run_name"]:
        raise ValueError(ctx.cfg["routes"]["source_stop"])
    d1r2_raw = ctx.source_d1r2_run / d1r2.RUN_NAME / "raw"
    inventory = _raw_inventory(d1r2_raw)
    if (
        inventory["count"] != source["d1r2_raw_count"]
        or inventory["total_bytes"] != source["d1r2_raw_total_bytes"]
        or inventory["digest"] != source["d1r2_raw_inventory_digest"]
        or ctx.source_d1r3_output.name != source["d1r3_output_name"]
    ):
        raise ValueError(ctx.cfg["routes"]["source_stop"])
    outputs = {
        "detailed": (
            ctx.source_d1r3_output / "stage4_2r3c3t13s24d1r3_detailed_v1.json",
            "d1r3_detailed_sha256",
        ),
        "summary": (
            ctx.source_d1r3_output / "stage4_2r3c3t13s24d1r3_summary_v1.json",
            "d1r3_summary_sha256",
        ),
        "manifest": (
            ctx.source_d1r3_output / "stage4_2r3c3t13s24d1r3_manifest_v1.json",
            "d1r3_manifest_sha256",
        ),
        "candidate_specs": (
            ctx.source_d1r3_output
            / "stage4_2r3c3t13s24d1r3_candidate_sentinel_specs_v1.json",
            "d1r3_candidate_specs_sha256",
        ),
        "independent_forensics": (
            ctx.source_d1r3_output
            / "stage4_2r3c3t13s24d1r3_independent_server_forensics_v1.json",
            "d1r3_independent_forensics_sha256",
        ),
        "primary_log": (ctx.source_d1r3_primary_log, "d1r3_primary_log_sha256"),
        "repeat_log": (ctx.source_d1r3_repeat_log, "d1r3_repeat_log_sha256"),
    }
    hashes = {}
    for name, (path, key) in outputs.items():
        if not path.is_file() or _sha256(path) != source[key]:
            raise ValueError(ctx.cfg["routes"]["source_stop"])
        hashes[name] = _sha256(path)
    detailed = _read_json(outputs["detailed"][0])
    summary = _read_json(outputs["summary"][0])
    manifest = _read_json(outputs["manifest"][0])
    independent = _read_json(outputs["independent_forensics"][0])
    specs = _read_json(outputs["candidate_specs"][0])
    rows = detailed.get("rows") or []
    if not (
        detailed.get("primary_pass")
        and detailed.get("route") == source["d1r3_required_route"]
        and summary == {key: value for key, value in detailed.items() if key != "rows"}
        and manifest.get("route") == source["d1r3_required_route"]
        and independent.get("forensic_recomputation_passed")
        and independent.get("route_reproduced") == source["d1r3_required_route"]
        and len(rows) == source["d1r3_replay_count"]
        and sum(bool(row.get("source_success")) for row in rows)
        == source["d1r3_full_success_count"]
        and sum(not bool(row.get("source_success")) for row in rows)
        == source["d1r3_structured_stop_count"]
        and sum(bool(row.get("split_branch_selected")) for row in rows)
        == source["d1r3_split_start_pass_count"]
        and all(bool(row.get("passed")) for row in rows)
        and len(specs) == ctx.cfg["spec_contract"]["expected_specs"]
        and _digest(specs) == source["d1r3_candidate_specs_digest"]
        and Counter(str(spec["horizon_steps"]) for spec in specs)
        == Counter({"35": 9})
        and Counter(str(spec["s24_sequence_index"]) for spec in specs)
        == Counter({"6": 3, "10": 3, "18": 3})
        and len({str(spec["experiment_id"]) for spec in specs}) == 9
        and all(
            spec.get("stage") == STAGE
            and spec.get("campaign_identity") == CAMPAIGN_IDENTITY
            and spec.get("controller_revision") == CONTROLLER_REVISION
            and spec.get("probe_primitive_revision") == CONTROLLER_REVISION
            and not bool(spec.get("source_result_available_to_controller"))
            and not bool(spec.get("pair_or_history_label_available_to_controller"))
            and not bool(spec.get("partition_label_available_to_controller"))
            and not bool(spec.get("probe_trajectory_allowed_in_expert_dataset"))
            for spec in specs
        )
    ):
        raise ValueError(ctx.cfg["routes"]["source_stop"])
    d1r3_rows = {
        str(row["source_experiment_id"]): row
        for row in rows
        if row.get("split_branch_selected")
    }
    raw_by_name = {row["path"]: row for row in inventory["files"]}
    for spec in specs:
        source_id = str(spec["d1r4_source_d1r2_experiment_id"])
        row = d1r3_rows.get(source_id)
        raw = raw_by_name.get(source_id + ".json.gz")
        if (
            row is None
            or raw is None
            or row.get("source_raw_sha256") != raw.get("sha256")
            or not bool(row.get("split_start_event", {}).get("passed"))
        ):
            raise ValueError(ctx.cfg["routes"]["source_stop"])
    snapshots = _selected_snapshot_audit(d1r2._selected_context_table(specs))
    if not (
        snapshots.get("passed")
        and snapshots.get("pass_count")
        == ctx.cfg["spec_contract"]["expected_snapshots"]
    ):
        raise ValueError(ctx.cfg["routes"]["source_stop"])
    auth = {
        "passed": True,
        "d1r2_raw_inventory": inventory,
        "d1r3_output_hashes": hashes,
        "d1r3_candidate_specs_digest": _digest(specs),
        "d1r3_split_row_count": len(d1r3_rows),
        "selected_snapshot_pass_count": snapshots["pass_count"],
    }
    return auth, specs, snapshots


def _package_fingerprint(ctx: Context) -> dict[str, Any]:
    root = _project_root()
    return {
        "package_revision": PACKAGE_REVISION,
        "package_manifest_sha256": _sha256(root / "PACKAGE_MANIFEST.json"),
        "sha256sums_sha256": _sha256(root / "SHA256SUMS"),
        "config_sha256": _sha256(ctx.config_path),
        "implementation_sha256": _sha256(Path(__file__).resolve()),
    }


def _verify_package(ctx: Context) -> dict[str, Any]:
    root = _project_root()
    manifest = _read_json(root / "PACKAGE_MANIFEST.json")
    if any(
        manifest.get(key) != value
        for key, value in {
            "stage": STAGE,
            "run_name": RUN_NAME,
            "campaign_identity": CAMPAIGN_IDENTITY,
            "controller_revision": CONTROLLER_REVISION,
            "package_revision": PACKAGE_REVISION,
        }.items()
    ):
        raise ValueError("D1R4 installed package manifest identity changed")
    lines = [
        line
        for line in (root / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    listed = [line.split(None, 1)[1].strip() for line in lines]
    if (
        listed != manifest.get("file_inventory")
        or listed != sorted(set(listed))
        or len(listed) != manifest.get("declared_file_count")
    ):
        raise ValueError("D1R4 installed package inventory changed")
    for line in lines:
        expected, relative = line.split(None, 1)
        path = root / relative.strip()
        if not path.is_file() or _sha256(path) != expected:
            raise ValueError(f"D1R4 package hash changed: {relative.strip()}")
    return {"passed": True, **_package_fingerprint(ctx), "file_count": len(listed)}


def _prepare_dirs(paths: Paths) -> None:
    if paths.state.exists() or paths.final.exists() or any(paths.raw.glob("*.json.gz")):
        raise ValueError("D1R4 fresh offline preflight requires a new empty stage")
    for path in (
        paths.variants,
        paths.specs,
        paths.source_reference,
        paths.raw,
        paths.analysis,
    ):
        path.mkdir(parents=True, exist_ok=True)


def prepare_offline(ctx: Context) -> dict[str, Any]:
    _prepare_dirs(ctx.paths)
    package = _verify_package(ctx)
    auth, specs, snapshots = _authenticate_source(ctx)
    _write_json(ctx.paths.specs / "sentinel_specs.json", specs)
    _write_json(ctx.paths.source_reference / "source_authentication.json", auth)
    _write_json(ctx.paths.source_reference / "snapshot_audit.json", snapshots)
    state = {
        "schema_version": 1,
        "stage": STAGE,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "phase_status": "offline_ready",
        "finished": False,
        "real_tsc_executed": False,
        "new_raw_count": 0,
        "package_fingerprint": package,
        "source_fingerprint": auth,
        "spec_digest": _digest(specs),
        "verdict": None,
    }
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "package_fingerprint": package,
        "source_fingerprint": auth,
        "spec_count": len(specs),
        "spec_digest": _digest(specs),
        "snapshot_pass_count": snapshots["pass_count"],
        "finished": False,
    }
    _write_json(ctx.paths.state, state)
    _write_json(ctx.paths.manifest, manifest)
    output = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "zero_plant_offline_preflight",
        "source_authentication_passed": True,
        "package_verification_passed": True,
        "spec_count": len(specs),
        "snapshot_pass_count": snapshots["pass_count"],
        "new_raw_count": 0,
        "real_tsc_executed": False,
        "passed": True,
    }
    _write_json(ctx.paths.analysis / "offline_preflight.json", output)
    return output


def _saved_specs(ctx: Context) -> list[dict[str, Any]]:
    state = _read_json(ctx.paths.state)
    manifest = _read_json(ctx.paths.manifest)
    auth, rebuilt, _ = _authenticate_source(ctx)
    saved = _read_json(ctx.paths.specs / "sentinel_specs.json")
    if (
        saved != rebuilt
        or _digest(saved) != state.get("spec_digest")
        or _digest(saved) != manifest.get("spec_digest")
        or state.get("package_fingerprint") != _verify_package(ctx)
        or state.get("source_fingerprint") != auth
        or manifest.get("source_fingerprint") != auth
    ):
        raise ValueError("D1R4 frozen resume/source fingerprint changed")
    return saved


def _payload(ctx: Context, spec: Mapping[str, Any]) -> dict[str, Any]:
    s21_ctx = ctx.base_d1r2_ctx.base_s24_ctx.base_ctx
    proxy = SimpleNamespace(
        base_ctx=s21_ctx.base_ctx,
        paths=ctx.paths,
        cfg=s21_ctx.cfg,
    )
    payload = d1r2.s24.s21._payload(proxy, spec)
    experiment_id = str(spec["experiment_id"])
    payload.update(
        {
            "variant_id": f"stage4_2r3c3t13s24d1r4_{experiment_id}",
            "stage4_2r3c3t13s24d1r4_restart_snapshot_dir": str(
                spec["restart_snapshot_dir"]
            ),
            "stage4_2r3c3t13s24d1r4_snapshot_manifest_digest": str(
                spec["restart_snapshot_manifest_digest"]
            ),
            "stage4_2r3c3t13s24d1r4_selection_label_available_to_controller": False,
        }
    )
    _write_json(ctx.paths.variants / f"payload_{experiment_id}.json", payload)
    return payload


_D1R4_CONTROLLER_FORBIDDEN_SPEC_KEYS = frozenset(
    {
        "d1r4_source_d1r2_experiment_id",
        "d1r4_split_contract",
        "candidate_preflight_sha256",
    }
)


def _controller_spec(spec: Mapping[str, Any]) -> dict[str, Any]:
    clean = copy.deepcopy(dict(spec))
    for key in _D1R4_CONTROLLER_FORBIDDEN_SPEC_KEYS:
        clean.pop(key, None)
    output = d1r2.s24.s21.s16.s9._controller_spec(clean)
    forbidden = {
        *_D1R4_CONTROLLER_FORBIDDEN_SPEC_KEYS,
        "pair_id",
        "history_member",
        "partition",
        "d1r4_source_d1r2_experiment_id",
    }
    if forbidden.intersection(output):
        raise ValueError("D1R4 forbidden selection label reached controller")
    return output


class CausalSplitReturnSafetySentinelController(
    d1r3.CausalSplitReturnPreflightController
):
    """Frozen D1R3 split start plus one-step-later exact causal finish."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._split_pending: dict[str, Any] | None = None
        self._split_start_count = 0
        self._split_finish_count = 0

    def _cancel(
        self, slot: int, currents: np.ndarray, baseline_action: np.ndarray
    ) -> tuple[np.ndarray, dict[str, Any]]:
        try:
            action, source_event = super()._cancel(slot, currents, baseline_action)
        except Exception:
            split_failure = copy.deepcopy(self._last_split_start_event)
            if isinstance(split_failure, dict) and not bool(
                split_failure.get("passed")
            ):
                self._last_failed_event = split_failure
            raise
        if source_event.get("event") != "sequential_cancel_split_start":
            return action, source_event
        if self._split_pending is not None:
            raise ValueError("D1R4 split start while finish already pending")
        event = copy.deepcopy(source_event)
        event.update(
            {
                "stage": STAGE,
                "campaign_identity": CAMPAIGN_IDENTITY,
                "controller_revision": CONTROLLER_REVISION,
            }
        )
        self._split_pending = {
            "slot": int(slot),
            "start_task_step": int(self.step),
            "stored_center_card15_fields": copy.deepcopy(
                event["stored_center_card15_fields"]
            ),
            "issue_target_card15_fields": copy.deepcopy(
                event["issue_target_card15_fields"]
            ),
            "intermediate_card15_fields": copy.deepcopy(
                event["intermediate_card15_fields"]
            ),
            "split_start_event": copy.deepcopy(event),
        }
        self._split_start_count += 1
        self._last_split_start_event = copy.deepcopy(event)
        return np.asarray(action, dtype=float), event

    def _finish(
        self, currents: np.ndarray, baseline_action: np.ndarray
    ) -> tuple[np.ndarray, dict[str, Any]]:
        pending = self._split_pending
        if pending is None:
            raise ValueError("D1R4 split finish has no pending start")
        split_cfg = self.split_cfg
        stored = tuple(map(str, pending["stored_center_card15_fields"]))
        target = tuple(map(str, pending["issue_target_card15_fields"]))
        middle = tuple(map(str, pending["intermediate_card15_fields"]))
        chosen = d1r2.s24.s21.s16.s9.exact_stored_center_action(
            stored_fields=stored,
            measured_current_a_tsc=currents,
            baseline_action_norm_tsc=baseline_action,
            turns_tsc=self.turns_tsc,
            max_slew_step_a=float(self.base.max_delta_a),
            minimum_current_a_tsc=self.base.min_current,
            maximum_current_a_tsc=self.base.max_current,
            cfg=self.lattice_cfg,
        )
        finished = self.actuator.apply(currents, chosen["action_norm_tsc"])
        telescope = all(
            (
                d1r2.s24.s21.s16.s9._decimal_field(t)
                - d1r2.s24.s21.s16.s9._decimal_field(c)
            )
            + (
                d1r2.s24.s21.s16.s9._decimal_field(m)
                - d1r2.s24.s21.s16.s9._decimal_field(t)
            )
            + (
                d1r2.s24.s21.s16.s9._decimal_field(c)
                - d1r2.s24.s21.s16.s9._decimal_field(m)
            )
            == Decimal(0)
            for c, t, m in zip(stored, target, middle)
        )
        increment = float(chosen["incremental_normalized_action_linf"])
        criteria = {
            "pending_start_step_exact": int(pending["start_task_step"])
            == int(split_cfg["split_start_task_step"]),
            "finish_step_exact": int(self.step)
            == int(split_cfg["split_finish_task_step"]),
            "slot_exact": int(pending["slot"]) == int(split_cfg["split_slot"]),
            "one_plant_advance": int(self.step) - int(pending["start_task_step"])
            == 1,
            "chosen_target_exact": list(chosen["target_fields"]) == list(stored),
            "stored_issue_center_exact": bool(chosen["exact_stored_issue_center"]),
            "target_exact": list(finished.card15_fields) == list(stored),
            "exact_fields": all(
                len(field) == 10
                and d1r2.s24.s21.s16.s9.format_number(
                    float(d1r2.s24.s21.s16.s9._decimal_field(field))
                )
                == field
                for field in stored
            ),
            "exact_decimal_telescoping_net": telescope,
            "no_saturation": not any(finished.action_saturated),
            "no_current_clip": not any(finished.current_limit_clipped),
            "finish_increment": increment
            <= float(split_cfg["maximum_finish_increment"]) + 1e-12,
            "original_increment": increment
            <= float(split_cfg["maximum_original_increment"]) + 1e-12,
            "total_action": float(chosen["total_normalized_action_abs"])
            <= float(split_cfg["maximum_total_normalized_action_abs"]) + 1e-12,
            "current_bounds": bool(chosen["current_bounds_pass"]),
            "current_utilization": float(
                chosen["predicted_maximum_current_utilization"]
            )
            <= float(split_cfg["maximum_current_utilization"]) + 1e-12,
            "actuator_gate": bool(chosen["passed"]),
        }
        event = {
            "event": "sequential_cancel_split_finish",
            "stage": STAGE,
            "campaign_identity": CAMPAIGN_IDENTITY,
            "controller_revision": CONTROLLER_REVISION,
            "slot": int(pending["slot"]),
            "split_start_task_step": int(pending["start_task_step"]),
            "task_step": int(self.step),
            "stored_center_card15_fields": list(stored),
            "issue_target_card15_fields": list(target),
            "intermediate_card15_fields": list(middle),
            "baseline_action_norm_tsc": np.asarray(
                baseline_action, dtype=float
            ).tolist(),
            "finish_action_norm_tsc": list(chosen["action_norm_tsc"]),
            "incremental_normalized_action_linf": increment,
            "total_normalized_action_abs": float(chosen["total_normalized_action_abs"]),
            "predicted_current_utilization": float(
                chosen["predicted_maximum_current_utilization"]
            ),
            "criteria": criteria,
            "passed": bool(all(criteria.values())),
            "actuator_prediction": copy.deepcopy(chosen),
        }
        if not event["passed"]:
            self._last_failed_event = copy.deepcopy(event)
            raise ValueError(
                "D1R4 split finish action failed: "
                + json.dumps(event, sort_keys=True)
            )
        self._active_issue = None
        self._split_pending = None
        self._split_finish_count += 1
        return np.asarray(chosen["action_norm_tsc"], dtype=float), event

    def action(
        self, current_state: Mapping[str, Any]
    ) -> tuple[np.ndarray, dict[str, Any]]:
        pending_before = self._split_pending is not None
        if pending_before and int(self.step) != int(
            self.split_cfg["split_finish_task_step"]
        ):
            raise ValueError("D1R4 pending finish reached an unexpected task step")
        action, trace = super().action(current_state)
        action = np.asarray(action, dtype=float)
        event: dict[str, Any] = {}
        event_name = "none"
        if pending_before:
            action, event = self._finish(
                np.asarray(current_state["currents_a_tsc"], dtype=float), action
            )
            event_name = "sequential_cancel_split_finish"
        else:
            source_event = copy.deepcopy(
                trace.get("r3c3t13s24d1r2_event_detail") or {}
            )
            if source_event:
                event = source_event
                event_name = str(source_event.get("event", "none"))
        trace.update(
            {
                "action_norm_tsc": action.tolist(),
                "r3c3t13s24d1r4_safety_sentinel_only": True,
                "r3c3t13s24d1r4_controller_revision": CONTROLLER_REVISION,
                "r3c3t13s24d1r4_event": event_name,
                "r3c3t13s24d1r4_event_detail": copy.deepcopy(event),
                "r3c3t13s24d1r4_split_pending_after_action": self._split_pending
                is not None,
                "r3c3t13s24d1r4_source_selection_label_used": False,
                "r3c3t13s24d1r4_pair_history_partition_label_used": False,
                "r3c3t13s24d1r4_source_outcome_used": False,
                "r3c3t13s24d1r4_future_measurement_used": False,
                "r3c3t13s24d1r4_future_executed_action_used": False,
                "r3c3t13s24d1r4_hidden_wire_current_used": False,
                "r3c3t13s24d1r4_schedule_available_to_underlying_controller": False,
            }
        )
        return action, trace


class LocalWorker:
    """One fresh authentic TSC process and D1R4 controller per rollout."""

    def __init__(
        self,
        payload: dict[str, Any],
        library: dict[str, Any],
        bundle: dict[str, Any],
        worker_id: str,
        selector: dict[str, Any],
        lattice_cfg: dict[str, Any],
        calibration_cfg: dict[str, Any],
        dynamic_cfg: dict[str, Any],
        schedule_cfg: dict[str, Any],
        split_cfg: dict[str, Any],
    ):
        self.plant = d1r2.s24.s21.s16.s9.t11.t1.r1.LocalPlantReplayWorker(
            payload, library, bundle, worker_id, selector
        )
        self.base = self.plant.base_worker
        self.bundle = bundle
        self.lattice_cfg = lattice_cfg
        self.calibration_cfg = calibration_cfg
        self.dynamic_cfg = dynamic_cfg
        self.schedule_cfg = schedule_cfg
        self.split_cfg = split_cfg

    def close(self) -> None:
        self.plant.close()

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        failed = True
        trajectory: list[dict[str, Any]] = []
        trace: list[dict[str, Any]] = []
        controller: CausalSplitReturnSafetySentinelController | None = None
        result: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "campaign_identity": CAMPAIGN_IDENTITY,
            "controller_revision": CONTROLLER_REVISION,
            "probe_primitive_revision": CONTROLLER_REVISION,
            "underlying_controller_revision": (
                d1r2.s24.s21.s16.s9.t11.t1.r3c1.CONTROLLER_REVISION
            ),
            "experiment_id": str(spec["experiment_id"]),
            "spec": copy.deepcopy(spec),
            "success": False,
            "completed": False,
            "failure_class": "",
            "failure_reason": "",
            "trajectory": trajectory,
            "controller_trace": trace,
        }
        try:
            horizon = int(spec["horizon_steps"])
            if (
                horizon != 35
                or horizon != int(spec["formal_horizon_steps"])
                or horizon != int(self.base.env.max_episode_steps)
            ):
                raise ValueError("D1R4 formal horizon changed")
            self.base.env.reset()
            zero = np.zeros(N_COILS, dtype=np.float32)
            trajectory.append(
                d1r2.s24.s21.s16.s9.t11.t1.r1._state_record_full(
                    self.base.env, 0, zero
                )
            )
            controller = CausalSplitReturnSafetySentinelController(
                self.base,
                self.bundle,
                _controller_spec(spec),
                trajectory[0],
                self.lattice_cfg,
                self.calibration_cfg,
                self.dynamic_cfg,
                self.schedule_cfg,
                split_cfg=self.split_cfg,
            )
            for step in range(horizon):
                action, controller_row = controller.action(trajectory[-1])
                _, _, terminated, truncated, info = self.base.env.step(action)
                next_state = d1r2.s24.s21.s16.s9.t11.t1.r1._state_record_full(
                    self.base.env, step + 1, action
                )
                trajectory.append(next_state)
                trace.append(controller_row)
                controller.advance(next_state)
                if terminated:
                    raise RuntimeError(
                        str(info.get("failure_reason", "environment terminated"))
                    )
                if truncated and step + 1 < horizon:
                    raise RuntimeError("environment truncated before D1R4 horizon")
            events = [
                row["r3c3t13s24d1r4_event"]
                for row in trace
                if row["r3c3t13s24d1r4_event"] != "none"
            ]
            expected = [
                "sequential_issue",
                "sequential_cancel",
                "sequential_issue",
                "sequential_cancel",
                "sequential_issue",
                "sequential_cancel",
                "sequential_issue",
                "sequential_cancel_split_start",
                "sequential_cancel_split_finish",
            ]
            details = [
                row["r3c3t13s24d1r4_event_detail"]
                for row in trace
                if row["r3c3t13s24d1r4_event"] != "none"
            ]
            success = bool(
                len(trajectory) == horizon + 1
                and len(trace) == horizon
                and not any(bool(row.get("abnormal")) for row in trajectory)
                and all(
                    bool(row.get("computed_online"))
                    and bool(row.get("solver_success"))
                    for row in trace
                )
                and events == expected
                and len(details) == 9
                and all(bool(row.get("passed")) for row in details)
                and bool(trace[7]["r3c3t13s21_exact_calibration_net_zero"])
                and controller._active_issue is None
                and controller._split_pending is None
                and controller._split_start_count == 1
                and controller._split_finish_count == 1
            )
            result.update(
                {
                    "success": success,
                    "completed": True,
                    "failure_class": "" if success else "runtime_or_execution_gate",
                    "failure_reason": "" if success else "invalid D1R4 full rollout",
                    "hidden_history_control_summary": {
                        "fresh_controller_actor": True,
                        "fresh_tsc_process": True,
                        "full_tsc_hidden_state_loaded_from_sprsina": True,
                        "controller_history_initialization": (
                            "current_visible_state_only_at_task_step_zero"
                        ),
                        "controller_integral_initialization": "zero",
                        "safety_sentinel_only": True,
                        "split_start_count": controller._split_start_count,
                        "split_finish_count": controller._split_finish_count,
                        "split_pending_at_end": controller._split_pending is not None,
                        "full_event_schedule_exact": events == expected,
                        "observation_horizon_steps": horizon,
                        "formal_horizon_steps": horizon,
                        "probe_trajectory_allowed_in_expert_dataset": False,
                        "task_clock_starts_at_zero": True,
                        "formal_clock_shifted": False,
                        "hidden_wire_current_available_to_controller": False,
                        "full_wire_current_recorded_after_action_choice": True,
                        "online_action_computation": True,
                        "future_action_replay_used": False,
                        "future_measurement_used": False,
                        "source_action_used": False,
                        "source_coil_current_used": False,
                        "source_wire_current_used": False,
                        "current_run_future_used": False,
                        "pair_or_history_label_used": False,
                        "partition_label_available_to_controller": False,
                        "source_result_used": False,
                    },
                    "wall_time_s": time.time() - started,
                }
            )
            failed = not success
            return d1r2.s24.s21.s16.s9.t11.t1._json_safe(result)
        except Exception as exc:
            action_failure = (
                copy.deepcopy(controller._last_failed_event)
                if controller is not None
                else None
            )
            result.update(
                {
                    "success": False,
                    "completed": True,
                    "failure_class": (
                        "structured_action_schedule_gate"
                        if action_failure is not None
                        else "runtime_or_environment"
                    ),
                    "failure_reason": repr(exc),
                    "action_failure_event": action_failure,
                    "trajectory": trajectory,
                    "controller_trace": trace,
                    "traceback": traceback.format_exc(),
                    "wall_time_s": time.time() - started,
                }
            )
            return d1r2.s24.s21.s16.s9.t11.t1._json_safe(result)
        finally:
            runner = getattr(self.base.env, "runner", None)
            if runner is not None:
                runner.cleanup_episode_workspace(
                    failed=failed,
                    reason="stage4_2r3c3t13s24d1r4_split_return_safety_sentinel",
                )


_RAY_ACTOR = None


def _ray_actor_class():
    global _RAY_ACTOR
    if _RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1)
        class Stage42R3C3T13S24D1R4Actor:
            def __init__(self, *args: Any):
                self.worker = LocalWorker(*args)

            def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
                return self.worker.evaluate(spec)

            def close(self) -> bool:
                self.worker.close()
                return True

        _RAY_ACTOR = Stage42R3C3T13S24D1R4Actor
    return _RAY_ACTOR


def _read_raw(path: Path) -> dict[str, Any]:
    return d1r2._read_raw(path)


def _result_covered(path: Path, spec: Mapping[str, Any]) -> bool:
    if not path.is_file():
        return False
    try:
        result = _read_raw(path)
        trajectory = result.get("trajectory") or []
        trace = result.get("controller_trace") or []
        identity = bool(
            result.get("completed")
            and result.get("stage") == STAGE
            and result.get("campaign_identity") == CAMPAIGN_IDENTITY
            and result.get("controller_revision") == CONTROLLER_REVISION
            and result.get("probe_primitive_revision") == CONTROLLER_REVISION
            and result.get("experiment_id") == spec["experiment_id"]
            and result.get("spec") == dict(spec)
            and len(trajectory) == len(trace) + 1
        )
        if not identity:
            return False
        if result.get("success"):
            return len(trajectory) == 36 and len(trace) == 35
        return result.get("failure_class") in {
            "structured_action_schedule_gate",
            "runtime_or_environment",
            "runtime_or_execution_gate",
        }
    except Exception:
        return False


def evaluate_specs(
    ctx: Context,
    specs: Sequence[dict[str, Any]],
    *,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    ctx.paths.raw.mkdir(parents=True, exist_ok=True)
    for spec in specs:
        path = ctx.paths.raw / f"{spec['experiment_id']}.json.gz"
        if path.exists() and not _result_covered(path, spec):
            raise ValueError("D1R4 existing raw incompatible; refusing overwrite")
    pending = [
        spec
        for spec in specs
        if not (
            resume
            and _result_covered(
                ctx.paths.raw / f"{spec['experiment_id']}.json.gz", spec
            )
        )
    ]
    if not resume and any(ctx.paths.raw.glob("*.json.gz")):
        raise ValueError("D1R4 fresh rollout requires empty raw directory")
    payloads = {str(spec["experiment_id"]): _payload(ctx, spec) for spec in specs}
    base_s24 = ctx.base_d1r2_ctx.base_s24_ctx
    library, bundle, selector = d1r2.s24._library_bundle_selector(base_s24)
    s21_ctx = base_s24.base_ctx
    args_tail = (
        library,
        bundle,
        selector,
        s21_ctx.base_ctx.cfg["lattice_probe"],
        s21_ctx.base_ctx.cfg["active_calibration"],
        s21_ctx.cfg["causal_model"],
        ctx.base_d1r2_ctx.cfg["schedule_contract"],
        ctx.cfg["split_contract"],
    )
    if backend == "serial":
        for index, spec in enumerate(pending):
            worker = LocalWorker(
                payloads[str(spec["experiment_id"])],
                args_tail[0],
                args_tail[1],
                f"stage42r3c3t13s24d1r4_serial_{index:03d}",
                *args_tail[2:],
            )
            try:
                result = worker.evaluate(spec)
            finally:
                worker.close()
            _write_json_gz(ctx.paths.raw / f"{spec['experiment_id']}.json.gz", result)
            print(f"[T13S24D1R4] {index + 1}/{len(pending)}", flush=True)
    elif backend == "ray" and pending:
        import ray

        plan = d1r2.s24.s21.s16.ensure_ray_worker_plan(
            ray,
            requested_workers=int(ctx.cfg["parallel"]["n_workers"]),
            pending_tasks=len(pending),
            ray_tmpdir=os.environ.get("RAY_TMPDIR") or ctx.cfg["storage"]["ray_tmpdir"],
            log_prefix="[T13S24D1R4]",
        )
        Actor = _ray_actor_class()
        completed = 0
        for batch_start in range(0, len(pending), plan.actor_count):
            batch = pending[batch_start : batch_start + plan.actor_count]
            actors, refs = [], {}
            for offset, spec in enumerate(batch):
                actor = Actor.remote(
                    payloads[str(spec["experiment_id"])],
                    args_tail[0],
                    args_tail[1],
                    f"stage42r3c3t13s24d1r4_{batch_start + offset:03d}",
                    *args_tail[2:],
                )
                actors.append(actor)
                refs[actor.evaluate.remote(spec)] = spec
            try:
                while refs:
                    ready, _ = ray.wait(list(refs), num_returns=1, timeout=30.0)
                    if not ready:
                        print(
                            f"[T13S24D1R4] waiting {completed}/{len(pending)}",
                            flush=True,
                        )
                        continue
                    for ref in ready:
                        spec = refs.pop(ref)
                        try:
                            result = ray.get(ref)
                        except Exception as exc:
                            result = {
                                "schema_version": 1,
                                "stage": STAGE,
                                "campaign_identity": CAMPAIGN_IDENTITY,
                                "controller_revision": CONTROLLER_REVISION,
                                "probe_primitive_revision": CONTROLLER_REVISION,
                                "experiment_id": str(spec["experiment_id"]),
                                "spec": copy.deepcopy(spec),
                                "success": False,
                                "completed": True,
                                "failure_class": "runtime_or_environment",
                                "failure_reason": repr(exc),
                                "traceback": traceback.format_exc(),
                                "trajectory": [],
                                "controller_trace": [],
                            }
                        _write_json_gz(
                            ctx.paths.raw / f"{spec['experiment_id']}.json.gz", result
                        )
                        completed += 1
                        print(f"[T13S24D1R4] {completed}/{len(pending)}", flush=True)
            finally:
                close_refs = [actor.close.remote() for actor in actors]
                if close_refs:
                    ray.get(close_refs, timeout=120.0)
                for actor in actors:
                    ray.kill(actor, no_restart=True)
    elif backend != "ray":
        raise ValueError(f"unsupported D1R4 backend: {backend}")
    covered = sum(
        _result_covered(ctx.paths.raw / f"{spec['experiment_id']}.json.gz", spec)
        for spec in specs
    )
    return {
        "expected": len(specs),
        "pending_at_start": len(pending),
        "covered_after": covered,
        "backend": backend,
        "resume": resume,
    }


def _forbidden_trace_count(trace: Sequence[Mapping[str, Any]]) -> int:
    base = d1r2._forbidden_trace_count(trace)
    keys = (
        "r3c3t13s24d1r4_source_selection_label_used",
        "r3c3t13s24d1r4_pair_history_partition_label_used",
        "r3c3t13s24d1r4_source_outcome_used",
        "r3c3t13s24d1r4_future_measurement_used",
        "r3c3t13s24d1r4_future_executed_action_used",
        "r3c3t13s24d1r4_hidden_wire_current_used",
        "r3c3t13s24d1r4_schedule_available_to_underlying_controller",
    )
    return base + sum(any(bool(row.get(key)) for key in keys) for row in trace)


def _source_trace_projection(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(value)
        for key, value in row.items()
        if not key.startswith("r3c3t13s24d1r4_")
    }


def _execution_audit(
    ctx: Context, specs: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    inventory = _raw_inventory(ctx.paths.raw)
    expected_raw_names = sorted(f"{spec['experiment_id']}.json.gz" for spec in specs)
    actual_raw_names = sorted(str(row["path"]) for row in inventory["files"])
    raw_inventory_exact = bool(
        inventory["count"] == len(specs) and actual_raw_names == expected_raw_names
    )
    state_map = d1r2.s24.s21.s13._source_state_map(
        ctx.base_d1r2_ctx.base_s24_ctx.base_ctx.base_ctx.base_ctx
    )
    base_source_ctx = (
        ctx.base_d1r2_ctx.base_s24_ctx.base_ctx.base_ctx.base_ctx.base_ctx.base_ctx
        .base_ctx.source_ctx.source_ctx
    )
    _, _, _ = _authenticate_source(ctx)
    d1r3_detail = _read_json(
        ctx.source_d1r3_output / "stage4_2r3c3t13s24d1r3_detailed_v1.json"
    )
    d1r3_split = {
        str(row["source_experiment_id"]): row["split_start_event"]
        for row in d1r3_detail["rows"]
        if row.get("split_branch_selected")
    }
    source_raw_dir = ctx.source_d1r2_run / d1r2.RUN_NAME / "raw"
    expected_calibration = [
        "calibration_issue",
        "calibration_cancel",
        "calibration_issue",
        "calibration_cancel",
        "calibration_issue",
        "calibration_cancel",
        "calibration_issue",
        "calibration_cancel",
    ]
    expected_events = [
        "sequential_issue",
        "sequential_cancel",
        "sequential_issue",
        "sequential_cancel",
        "sequential_issue",
        "sequential_cancel",
        "sequential_issue",
        "sequential_cancel_split_start",
        "sequential_cancel_split_finish",
    ]
    rows: list[dict[str, Any]] = []
    for spec in specs:
        path = ctx.paths.raw / f"{spec['experiment_id']}.json.gz"
        base_row = {
            "experiment_id": spec["experiment_id"],
            "source_experiment_id": spec["d1r4_source_d1r2_experiment_id"],
            "pair_id": spec["pair_id"],
            "history_member": spec["history_member"],
            "sequence_index": int(spec["s24_sequence_index"]),
            "horizon_steps": int(spec["horizon_steps"]),
        }
        if not path.is_file():
            rows.append(
                {
                    **base_row,
                    "classification": "runtime_or_raw_error",
                    "failure_reason": "missing raw",
                    "passed": False,
                }
            )
            continue
        try:
            result = _read_raw(path)
        except Exception as exc:
            rows.append(
                {
                    **base_row,
                    "classification": "raw_corruption_error",
                    "failure_reason": f"strict parse failed: {exc!r}",
                    "passed": False,
                }
            )
            continue
        identity = bool(
            result.get("completed")
            and result.get("stage") == STAGE
            and result.get("campaign_identity") == CAMPAIGN_IDENTITY
            and result.get("controller_revision") == CONTROLLER_REVISION
            and result.get("probe_primitive_revision") == CONTROLLER_REVISION
            and result.get("experiment_id") == spec["experiment_id"]
            and result.get("spec") == dict(spec)
        )
        trajectory = result.get("trajectory") or []
        trace = result.get("controller_trace") or []
        if not identity:
            rows.append(
                {
                    **base_row,
                    "strict_parse_pass": True,
                    "identity_pass": False,
                    "classification": "raw_identity_error",
                    "failure_reason": "raw identity/spec mismatch",
                    "passed": False,
                }
            )
            continue
        if not result.get("success"):
            event = result.get("action_failure_event")
            structured = bool(
                result.get("failure_class") == "structured_action_schedule_gate"
                and isinstance(event, dict)
                and not bool(event.get("passed"))
            )
            execution_gate = result.get("failure_class") == "runtime_or_execution_gate"
            rows.append(
                {
                    **base_row,
                    "strict_parse_pass": True,
                    "identity_pass": True,
                    "result_success": False,
                    "structured_action_failure": structured,
                    "failure_event": copy.deepcopy(event),
                    "classification": (
                        "action_schedule_design_failure"
                        if structured
                        else (
                            "scientific_gate_failure"
                            if execution_gate
                            else "runtime_or_environment_error"
                        )
                    ),
                    "failure_reason": str(result.get("failure_reason", "")),
                    "passed": False,
                }
            )
            continue
        try:
            payload = _payload(ctx, spec)
            currents = np.asarray(
                [row["currents_a_tsc"] for row in trajectory], dtype=float
            )
            actions = np.asarray([row["action_norm_tsc"] for row in trace], dtype=float)
            recorded = np.asarray(
                [row["action_norm_tsc"] for row in trajectory[1:]], dtype=float
            )
            minimum, maximum = d1r2.s24.s21.s13._current_limits_tsc(payload)
            center, half = 0.5 * (minimum + maximum), 0.5 * (maximum - minimum)
            utilization = float(np.max(np.abs((currents - center) / half)))
            restart = d1r2.s24.s21.s16.s9.t11.t1.r3b._control_row(
                base_source_ctx,
                result,
                state_map[str(spec["state_generation_experiment_id"])],
            )
            phase = d1r2.s24.s21.s16.s9.t11.t1.r3c1._phase_trace_valid(result)
            calibration = d1r2.s24.s21._dynamic_calibration_trace_audit(
                result, ctx.base_d1r2_ctx.base_s24_ctx.base_ctx.cfg
            )
            calibration_events = [
                row.get("r3c3t13s16_lattice_event")
                for row in trace
                if row.get("r3c3t13s16_lattice_event") != "none"
            ]
            events = [
                row.get("r3c3t13s24d1r4_event")
                for row in trace
                if row.get("r3c3t13s24d1r4_event") != "none"
            ]
            details = [
                row["r3c3t13s24d1r4_event_detail"]
                for row in trace
                if row.get("r3c3t13s24d1r4_event") != "none"
            ]
            issues = [row for row in details if row.get("event") == "sequential_issue"]
            direct = [row for row in details if row.get("event") == "sequential_cancel"]
            starts = [
                row
                for row in details
                if row.get("event") == "sequential_cancel_split_start"
            ]
            finishes = [
                row
                for row in details
                if row.get("event") == "sequential_cancel_split_finish"
            ]
            source_id = str(spec["d1r4_source_d1r2_experiment_id"])
            source_result = _read_raw(source_raw_dir / f"{source_id}.json.gz")
            source_trace = source_result.get("controller_trace") or []
            prefix_action_exact = bool(
                len(source_trace) == 18
                and np.array_equal(
                    np.asarray([row["action_norm_tsc"] for row in trace[:18]]),
                    np.asarray([row["action_norm_tsc"] for row in source_trace]),
                )
            )
            prefix_trace_exact = bool(
                len(source_trace) == 18
                and all(
                    _source_trace_projection(current) == source
                    for current, source in zip(trace[:18], source_trace)
                )
            )
            d1r3_start = d1r3_split[source_id]
            start_match = bool(
                len(starts) == 1
                and np.array_equal(
                    np.asarray(starts[0]["split_start_action_norm_tsc"]),
                    np.asarray(d1r3_start["split_start_action_norm_tsc"]),
                )
                and starts[0]["intermediate_card15_fields"]
                == d1r3_start["intermediate_card15_fields"]
                and math.isclose(
                    float(starts[0]["alpha"]),
                    float(d1r3_start["alpha"]),
                    rel_tol=0.0,
                    abs_tol=1e-12,
                )
            )
            finish = finishes[0] if len(finishes) == 1 else {}
            finish_pass = bool(
                finish.get("passed")
                and all((finish.get("criteria") or {}).values())
                and float(finish.get("incremental_normalized_action_linf", math.inf))
                <= 0.24 + 1e-12
            )
            forbidden = _forbidden_trace_count(trace)
            summary = result.get("hidden_history_control_summary") or {}
            runtime_pass = bool(
                len(trajectory) == 36
                and len(trace) == 35
                and np.all(np.isfinite(currents))
                and np.all(np.isfinite(actions))
                and not any(bool(row.get("abnormal")) for row in trajectory)
            )
            restart_pass = bool(
                restart.get("fresh_controller")
                and restart.get("fresh_tsc_process")
                and restart.get("initial_restart_exact")
                and restart.get("controller_trace_causal")
            )
            action_pass = bool(
                all(
                    bool(row.get("computed_online"))
                    and bool(row.get("solver_success"))
                    for row in trace
                )
                and calibration_events == expected_calibration
                and events == expected_events
                and len(issues) == 4
                and len(direct) == 3
                and len(starts) == len(finishes) == 1
                and all(bool(row.get("passed")) for row in details)
                and prefix_action_exact
                and prefix_trace_exact
                and start_match
                and finish_pass
                and forbidden == 0
                and bool(phase["passed"])
                and np.array_equal(actions, recorded)
                and float(np.max(np.abs(actions))) <= 1.0 + 1e-12
                and not bool(summary.get("split_pending_at_end"))
                and int(summary.get("split_start_count", 0)) == 1
                and int(summary.get("split_finish_count", 0)) == 1
            )
            passed = bool(
                runtime_pass
                and restart_pass
                and action_pass
                and calibration["passed"]
                and utilization
                <= float(ctx.cfg["split_contract"]["maximum_current_utilization"])
                + 1e-12
            )
            rows.append(
                {
                    **base_row,
                    "strict_parse_pass": True,
                    "identity_pass": True,
                    "result_success": True,
                    "runtime_full_horizon_pass": runtime_pass,
                    "restart_pass": restart_pass,
                    "phase_causality_pass": bool(phase["passed"]),
                    "calibration_pass": bool(calibration["passed"]),
                    "source_prefix_action_exact": prefix_action_exact,
                    "source_prefix_trace_exact": prefix_trace_exact,
                    "d1r3_split_start_exact": start_match,
                    "action_trace_pass": action_pass,
                    "issue_event_count": len(issues),
                    "direct_cancel_event_count": len(direct),
                    "split_start_event_count": len(starts),
                    "split_finish_event_count": len(finishes),
                    "split_finish_incremental_normalized_action_linf": float(
                        finish.get("incremental_normalized_action_linf", math.inf)
                    ),
                    "maximum_current_utilization": utilization,
                    "forbidden_trace_count": forbidden,
                    "formal_contract_pass_diagnostic": bool(
                        restart.get("formal_contract_pass")
                    ),
                    "classification": "pass" if passed else "scientific_gate_failure",
                    "passed": passed,
                }
            )
        except Exception as exc:
            rows.append(
                {
                    **base_row,
                    "strict_parse_pass": True,
                    "identity_pass": True,
                    "result_success": True,
                    "classification": "scientific_gate_failure",
                    "failure_reason": repr(exc),
                    "passed": False,
                }
            )
    runtime_failures = [
        row
        for row in rows
        if row.get("classification")
        in {"runtime_or_raw_error", "runtime_or_environment_error"}
    ]
    scientific_failures = [
        row
        for row in rows
        if row.get("classification")
        in {
            "action_schedule_design_failure",
            "scientific_gate_failure",
            "raw_corruption_error",
            "raw_identity_error",
        }
    ]
    passed = bool(
        raw_inventory_exact
        and len(rows) == len(specs)
        and all(bool(row.get("passed")) for row in rows)
    )
    if passed:
        route = ctx.cfg["routes"]["pass"]
    elif scientific_failures or not raw_inventory_exact:
        route = ctx.cfg["routes"]["action_fail"]
    else:
        route = ctx.cfg["routes"]["runtime_incomplete"]
    return {
        "schema_version": 1,
        "stage": STAGE,
        "expected": len(specs),
        "actual_rows": len(rows),
        "raw_inventory": inventory,
        "raw_inventory_exact": raw_inventory_exact,
        "strict_parse_count": sum(bool(row.get("strict_parse_pass")) for row in rows),
        "identity_pass_count": sum(bool(row.get("identity_pass")) for row in rows),
        "success_count": sum(bool(row.get("result_success")) for row in rows),
        "pass_count": sum(bool(row.get("passed")) for row in rows),
        "runtime_or_raw_failure_count": len(runtime_failures),
        "scientific_or_action_failure_count": len(scientific_failures),
        "full_horizon_pass_count": sum(
            bool(row.get("runtime_full_horizon_pass")) for row in rows
        ),
        "restart_pass_count": sum(bool(row.get("restart_pass")) for row in rows),
        "causality_pass_count": sum(
            bool(row.get("phase_causality_pass")) for row in rows
        ),
        "calibration_pass_count": sum(
            bool(row.get("calibration_pass")) for row in rows
        ),
        "source_prefix_action_exact_count": sum(
            bool(row.get("source_prefix_action_exact")) for row in rows
        ),
        "source_prefix_trace_exact_count": sum(
            bool(row.get("source_prefix_trace_exact")) for row in rows
        ),
        "d1r3_split_start_exact_count": sum(
            bool(row.get("d1r3_split_start_exact")) for row in rows
        ),
        "issue_event_count": sum(int(row.get("issue_event_count", 0)) for row in rows),
        "direct_cancel_event_count": sum(
            int(row.get("direct_cancel_event_count", 0)) for row in rows
        ),
        "split_start_event_count": sum(
            int(row.get("split_start_event_count", 0)) for row in rows
        ),
        "split_finish_event_count": sum(
            int(row.get("split_finish_event_count", 0)) for row in rows
        ),
        "maximum_split_finish_incremental_normalized_action_linf": max(
            (
                float(row.get("split_finish_incremental_normalized_action_linf", 0.0))
                for row in rows
                if math.isfinite(
                    float(row.get("split_finish_incremental_normalized_action_linf", math.inf))
                )
            ),
            default=0.0,
        ),
        "maximum_current_utilization": max(
            (float(row.get("maximum_current_utilization", 0.0)) for row in rows),
            default=0.0,
        ),
        "forbidden_trace_count": sum(
            int(row.get("forbidden_trace_count", 0)) for row in rows
        ),
        "formal_tracking_pass_count_diagnostic_only": sum(
            bool(row.get("formal_contract_pass_diagnostic")) for row in rows
        ),
        "route": route,
        "passed": passed,
        "rows": rows,
    }


def run_rollout(ctx: Context, *, backend: str, resume: bool) -> dict[str, Any]:
    state = _read_json(ctx.paths.state)
    if state.get("phase_status") != "offline_ready" or state.get("finished"):
        raise ValueError("D1R4 rollout requires open offline-ready state")
    specs = _saved_specs(ctx)
    execution = evaluate_specs(ctx, specs, backend=backend, resume=resume)
    audit = _execution_audit(ctx, specs)
    inventory = _raw_inventory(ctx.paths.raw)
    final = {
        "schema_version": 1,
        "stage": STAGE,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "execution": execution,
        "execution_audit": audit,
        "raw_inventory": inventory,
        "formal_timing_unchanged": True,
        "formal_tracking_is_diagnostic_only": True,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "full_replacement_campaign_design_authorized": bool(audit["passed"]),
        "full_replacement_campaign_execution_authorized": False,
        "mpc_or_rl_authorized": False,
        "route": audit["route"],
        "passed": bool(audit["passed"]),
    }
    _write_json(ctx.paths.analysis / "internal_execution_audit.json", audit)
    _write_json(ctx.paths.final, final)
    state.update(
        {
            "phase_status": "sentinel_complete" if audit["passed"] else "sentinel_failed",
            "finished": True,
            "primary_pass": bool(audit["passed"]),
            "real_tsc_executed": inventory["count"] > 0,
            "new_raw_count": inventory["count"],
            "stop_reason": "" if audit["passed"] else audit["route"],
            "verdict": {"route": audit["route"], "passed": bool(audit["passed"])},
        }
    )
    _write_json(ctx.paths.state, state)
    manifest = _read_json(ctx.paths.manifest)
    manifest.update(
        {
            "raw_inventory": inventory,
            "final_result_sha256": _sha256(ctx.paths.final),
            "internal_execution_audit_sha256": _sha256(
                ctx.paths.analysis / "internal_execution_audit.json"
            ),
            "finished": True,
            "route": audit["route"],
            "passed": bool(audit["passed"]),
        }
    )
    _write_json(ctx.paths.manifest, manifest)
    return final


def run_postprocess(ctx: Context) -> dict[str, Any]:
    if not ctx.paths.state.is_file() or not ctx.paths.final.is_file():
        raise ValueError("D1R4 postprocess requires completed sentinel outputs")
    specs = _saved_specs(ctx)
    audit = _execution_audit(ctx, specs)
    inventory = _raw_inventory(ctx.paths.raw)
    output = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "server_internal_raw_recomputation",
        "raw_inventory": inventory,
        "execution_audit": audit,
        "passed": bool(
            inventory["count"] == ctx.cfg["execution_gate"]["raw_files_required"]
            and audit["passed"]
        ),
        "route": audit["route"],
    }
    _write_json(ctx.paths.analysis / "server_internal_raw_recomputation.json", output)
    return output


def execute(
    ctx: Context, *, command: str, backend: str, resume: bool
) -> dict[str, Any]:
    if command == "offline":
        if resume:
            raise ValueError("D1R4 offline cannot resume")
        return prepare_offline(ctx)
    if command == "rollout":
        return run_rollout(ctx, backend=backend, resume=resume)
    if command == "postprocess":
        return run_postprocess(ctx)
    if command == "all":
        if resume:
            if not ctx.paths.state.is_file():
                raise ValueError("D1R4 resume requires existing frozen state")
        else:
            prepare_offline(ctx)
        final = run_rollout(ctx, backend=backend, resume=resume)
        internal = run_postprocess(ctx)
        return {"final": final, "postprocess": internal}
    raise ValueError(f"unsupported D1R4 command: {command}")


def self_test(config_path: Path) -> dict[str, Any]:
    config_path = config_path.expanduser().resolve()
    cfg = _read_json(config_path)
    _validate_config(cfg, config_path)
    return {
        "schema_version": 1,
        "stage": STAGE,
        "expected_real_tsc_rollouts": cfg["spec_contract"]["expected_specs"],
        "split_start_task_step": cfg["split_contract"]["split_start_task_step"],
        "split_finish_task_step": cfg["split_contract"]["split_finish_task_step"],
        "maximum_finish_increment": cfg["split_contract"]["maximum_finish_increment"],
        "formal_arrival_deadline_step": cfg["formal_timing_contract"]["normal"][
            "arrival_deadline_step"
        ],
        "real_tsc_executed": False,
        "passed": True,
    }


def _source_kwargs(args: argparse.Namespace) -> dict[str, Path]:
    return d1r2._source_kwargs(args)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source-d1r2-run", type=Path, required=True)
    parser.add_argument("--source-d1r3-output", type=Path, required=True)
    parser.add_argument("--source-d1r3-primary-log", type=Path, required=True)
    parser.add_argument("--source-d1r3-repeat-log", type=Path, required=True)
    parser.add_argument("--source-d1r1-output", type=Path, required=True)
    parser.add_argument("--source-d1r1-log", type=Path, required=True)
    parser.add_argument("--source-s21-run", type=Path, required=True)
    parser.add_argument("--source-s23r1-output", type=Path, required=True)
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
    parser.add_argument(
        "--command", choices=("offline", "rollout", "postprocess", "all"), required=True
    )
    parser.add_argument("--backend", choices=("serial", "ray"), default="ray")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        result = self_test(args.config)
    else:
        ctx = load_config(
            args.config,
            source_d1r2_run=args.source_d1r2_run,
            source_d1r3_output=args.source_d1r3_output,
            source_d1r3_primary_log=args.source_d1r3_primary_log,
            source_d1r3_repeat_log=args.source_d1r3_repeat_log,
            source_d1r1_output=args.source_d1r1_output,
            source_d1r1_log=args.source_d1r1_log,
            source_s21_run=args.source_s21_run,
            source_s23r1_output=args.source_s23r1_output,
            run_dir=args.run_dir,
            **_source_kwargs(args),
        )
        result = execute(ctx, command=args.command, backend=args.backend, resume=args.resume)
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
