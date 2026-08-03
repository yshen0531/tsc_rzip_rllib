"""Stage4.2R3c3T13S24D1R6 authentic split-return safety sentinel."""

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
    stage4_2r3c3t13s24d1r5_recursive_split_return_preflight as d1r5,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r2_real_tsc_safety_sentinel as d1r2,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r4_causal_split_return_safety_sentinel as d1r4,
)


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S24D1R6"
RUN_NAME = "stage4_2r3c3t13s24d1r6_recursive_split_return_safety_sentinel"
CAMPAIGN_IDENTITY = "causal_recursive_split_return_safety_sentinel_v1"
CONTROLLER_REVISION = "causal_recursive_split_return_probe_v42r3c3t13s24d1r6_v1"
PACKAGE_REVISION = "r42r3c3t13s24d1r6_recursive_split_return_safety_sentinel_v1"
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
        raise ValueError(f"D1R6 {key} is outside package")
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
    source_d1r4_ctx: d1r4.Context
    source_d1r4_complete_log: Path
    source_d1r5_primary_output: Path
    source_d1r5_repeat_output: Path
    source_d1r5_primary_log: Path
    source_d1r5_repeat_log: Path
    paths: Paths


def _validate_config(cfg: Mapping[str, Any], config_path: Path) -> None:
    exact = {
        "schema_version": 1,
        "stage": STAGE,
        "run_name": RUN_NAME,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "selection_status": "frozen_after_d1r5_pass_before_d1r6_implementation_or_tsc",
    }
    if any(cfg.get(key) != value for key, value in exact.items()):
        raise ValueError("D1R6 frozen identity changed")
    expected_config = (
        _project_root()
        / "configs/stage4_2r3c3t13s24d1r6_recursive_split_return_safety_sentinel_350ms.json"
    ).resolve()
    if config_path.resolve() != expected_config:
        raise ValueError("D1R6 config path changed")
    for key in (
        "design_document",
        "base_d1r4_config",
        "base_d1r4_implementation",
        "d1r5_config",
        "d1r5_primary_implementation",
    ):
        source_path = _package_path(cfg, key)
        if not source_path.is_file() or _sha256(source_path) != cfg[f"{key}_sha256"]:
            raise ValueError(f"D1R6 frozen {key} hash changed")
    source = cfg["source_contract"]
    if (
        source["d1r4_raw_count"] != 9
        or source["d1r4_raw_total_bytes"] != 363_807
        or source["d1r5_replay_count"] != 9
        or source["d1r5_independent_pass_count"] != 9
        or any(
            len(str(value)) != 64
            for key, value in source.items()
            if key.endswith("sha256") or key.endswith("digest")
        )
    ):
        raise ValueError("D1R6 source contract changed")
    recursive = cfg["recursive_contract"]
    expected_recursive = {
        "direct_finish_threshold": 0.24,
        "continuation_target_increment": 0.175,
        "maximum_continuation_increment": 0.18,
        "maximum_original_increment": 0.25,
        "maximum_total_normalized_action_abs": 1.0,
        "maximum_current_utilization": 0.55,
        "initial_split_task_step": 18,
        "first_continuation_task_step": 19,
        "latest_finish_task_step": 22,
        "split_slot": 3,
        "minimum_continuation_count": 1,
        "maximum_continuation_count": 3,
        "require_exact_card15": True,
        "require_expanded_exact_decimal_telescope": True,
        "require_no_saturation_or_clipping": True,
        "failed_candidate_plant_advance_allowed": False,
        "retry_or_horizon_extension_allowed": False,
    }
    if dict(recursive) != expected_recursive:
        raise ValueError("D1R6 recursive state machine changed")
    specs = cfg["spec_contract"]
    if specs != {
        "expected_specs": 9,
        "expected_snapshots": 3,
        "expected_horizon_counts": {"35": 9, "37": 0},
        "expected_sequence_index_counts": {"6": 3, "10": 3, "18": 3},
        "fresh_tsc_process_required": True,
        "fresh_controller_required": True,
        "full_horizon_required_for_pass": True,
        "source_outcome_available_to_controller": False,
        "pair_history_partition_label_available_to_controller": False,
    }:
        raise ValueError("D1R6 task matrix changed")
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
        "first_continuation_events_required": 9,
        "split_finish_events_required": 9,
        "forbidden_use_count_required": 0,
    }
    if cfg["execution_gate"] != expected_gate:
        raise ValueError("D1R6 execution gates changed")
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
        raise ValueError("D1R6 formal timing changed")
    if cfg["routes"] != {
        "source_stop": "CAUSAL_RECURSIVE_SPLIT_RETURN_SENTINEL_SOURCE_STOP",
        "runtime_incomplete": "CAUSAL_RECURSIVE_SPLIT_RETURN_SENTINEL_RUNTIME_INCOMPLETE",
        "action_fail": "CAUSAL_RECURSIVE_SPLIT_RETURN_SENTINEL_FAIL_REDESIGN_REQUIRED",
        "pass": "CAUSAL_RECURSIVE_SPLIT_RETURN_SENTINEL_PASS_FULL_REPLACEMENT_CAMPAIGN_DESIGN_REQUIRED",
    }:
        raise ValueError("D1R6 routes changed")
    if cfg["parallel"] != {
        "n_workers": 9,
        "one_fresh_actor_tsc_controller_per_spec": True,
    }:
        raise ValueError("D1R6 capacity changed")
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
        raise ValueError("D1R6 scientific scope changed")


def load_config(
    config_path: Path,
    *,
    source_d1r4_run: Path,
    source_d1r4_complete_log: Path,
    source_d1r5_primary_output: Path,
    source_d1r5_repeat_output: Path,
    source_d1r5_primary_log: Path,
    source_d1r5_repeat_log: Path,
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
    source_d1r4_ctx = d1r4.load_config(
        _package_path(cfg, "base_d1r4_config"),
        source_d1r2_run=source_d1r2_run,
        source_d1r3_output=source_d1r3_output,
        source_d1r3_primary_log=source_d1r3_primary_log,
        source_d1r3_repeat_log=source_d1r3_repeat_log,
        source_d1r1_output=source_d1r1_output,
        source_d1r1_log=source_d1r1_log,
        source_s21_run=source_s21_run,
        source_s23r1_output=source_s23r1_output,
        run_dir=source_d1r4_run,
        **source_kwargs,
    )
    return Context(
        cfg=dict(cfg),
        config_path=config_path,
        base_d1r2_ctx=source_d1r4_ctx.base_d1r2_ctx,
        source_d1r4_ctx=source_d1r4_ctx,
        source_d1r4_complete_log=source_d1r4_complete_log.expanduser().resolve(),
        source_d1r5_primary_output=source_d1r5_primary_output.expanduser().resolve(),
        source_d1r5_repeat_output=source_d1r5_repeat_output.expanduser().resolve(),
        source_d1r5_primary_log=source_d1r5_primary_log.expanduser().resolve(),
        source_d1r5_repeat_log=source_d1r5_repeat_log.expanduser().resolve(),
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
    """Re-aggregate the inherited per-snapshot audit for D1R6's subset."""
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
    if (
        ctx.source_d1r4_ctx.paths.run_dir.name != source["d1r4_run_name"]
        or ctx.source_d1r5_primary_output.name != source["d1r5_primary_output_name"]
        or ctx.source_d1r5_repeat_output.name != source["d1r5_repeat_output_name"]
    ):
        raise ValueError(ctx.cfg["routes"]["source_stop"])
    d1r5_config_path = _package_path(ctx.cfg, "d1r5_config")
    d1r5_cfg = _read_json(d1r5_config_path)
    d1r5._validate_config(d1r5_cfg, d1r5_config_path)
    _, d1r4_auth = d1r5._authenticate_source(
        ctx.source_d1r4_ctx, d1r5_cfg, ctx.source_d1r4_complete_log
    )
    names = {
        "candidate_specs": "stage4_2r3c3t13s24d1r5_candidate_real_sentinel_specs_v1.json",
        "detailed": "stage4_2r3c3t13s24d1r5_detailed_v1.json",
        "independent": "stage4_2r3c3t13s24d1r5_independent_forensics_v1.json",
        "manifest": "stage4_2r3c3t13s24d1r5_manifest_v1.json",
        "summary": "stage4_2r3c3t13s24d1r5_summary_v1.json",
    }
    source_keys = {
        "candidate_specs": "d1r5_candidate_specs_sha256",
        "detailed": "d1r5_detailed_sha256",
        "independent": "d1r5_independent_sha256",
        "manifest": "d1r5_manifest_sha256",
        "summary": "d1r5_summary_sha256",
    }
    hashes: dict[str, str] = {}
    for key, name in names.items():
        primary = ctx.source_d1r5_primary_output / name
        repeat = ctx.source_d1r5_repeat_output / name
        if not primary.is_file() or not repeat.is_file():
            raise ValueError(ctx.cfg["routes"]["source_stop"])
        primary_hash = _sha256(primary)
        repeat_hash = _sha256(repeat)
        if primary_hash != source[source_keys[key]] or repeat_hash != primary_hash:
            raise ValueError(ctx.cfg["routes"]["source_stop"])
        hashes[key] = primary_hash
    log_hashes = {
        "primary_log": _sha256(ctx.source_d1r5_primary_log),
        "repeat_log": _sha256(ctx.source_d1r5_repeat_log),
    }
    if (
        log_hashes["primary_log"] != source["d1r5_primary_log_sha256"]
        or log_hashes["repeat_log"] != source["d1r5_repeat_log_sha256"]
    ):
        raise ValueError(ctx.cfg["routes"]["source_stop"])
    detailed = _read_json(ctx.source_d1r5_primary_output / names["detailed"])
    summary = _read_json(ctx.source_d1r5_primary_output / names["summary"])
    manifest = _read_json(ctx.source_d1r5_primary_output / names["manifest"])
    independent = _read_json(ctx.source_d1r5_primary_output / names["independent"])
    specs = _read_json(ctx.source_d1r5_primary_output / names["candidate_specs"])
    raw_inventory = d1r4_auth["raw_inventory"]
    recursive = ctx.cfg["recursive_contract"]
    identity_pass = all(
        spec.get("stage") == STAGE
        and spec.get("campaign_identity") == CAMPAIGN_IDENTITY
        and spec.get("controller_revision") == CONTROLLER_REVISION
        and spec.get("probe_primitive_revision") == CONTROLLER_REVISION
        and not bool(spec.get("source_result_available_to_controller"))
        and not bool(spec.get("pair_or_history_label_available_to_controller"))
        and not bool(spec.get("partition_label_available_to_controller"))
        and not bool(spec.get("probe_trajectory_allowed_in_expert_dataset"))
        and int(spec.get("horizon_steps", -1)) == 35
        and int(spec.get("formal_horizon_steps", -1)) == 35
        and float(spec["d1r6_recursive_contract"]["direct_finish_threshold"])
        == float(recursive["direct_finish_threshold"])
        and float(spec["d1r6_recursive_contract"]["continuation_target_increment"])
        == float(recursive["continuation_target_increment"])
        and int(spec["d1r6_recursive_contract"]["latest_future_finish_task_step"])
        == int(recursive["latest_finish_task_step"])
        for spec in specs
    )
    if not (
        d1r4_auth.get("passed")
        and raw_inventory["count"] == source["d1r4_raw_count"]
        and raw_inventory["total_bytes"] == source["d1r4_raw_total_bytes"]
        and raw_inventory["digest"] == source["d1r4_raw_inventory_digest"]
        and detailed.get("primary_pass")
        and detailed.get("route") == source["d1r5_required_route"]
        and detailed.get("continuation_pass_count") == source["d1r5_replay_count"]
        and detailed.get("direct_failure_reproduction_count")
        == source["d1r5_replay_count"]
        and summary == {key: value for key, value in detailed.items() if key != "rows"}
        and manifest.get("route") == source["d1r5_required_route"]
        and independent.get("forensic_recomputation_passed")
        and independent.get("independent_pass_count")
        == source["d1r5_independent_pass_count"]
        and independent.get("route") == source["d1r5_required_route"]
        and len(specs) == ctx.cfg["spec_contract"]["expected_specs"]
        and _digest(specs) == source["d1r5_candidate_specs_digest"]
        and detailed.get("candidate_real_sentinel_spec_digest") == _digest(specs)
        and independent.get("candidate_spec_digest") == _digest(specs)
        and Counter(str(spec["horizon_steps"]) for spec in specs)
        == Counter({"35": 9})
        and Counter(str(spec["s24_sequence_index"]) for spec in specs)
        == Counter({"6": 3, "10": 3, "18": 3})
        and len({str(spec["experiment_id"]) for spec in specs}) == 9
        and identity_pass
    ):
        raise ValueError(ctx.cfg["routes"]["source_stop"])
    snapshots = _read_json(
        ctx.source_d1r4_ctx.paths.source_reference / "snapshot_audit.json"
    )
    if not snapshots.get("passed") or snapshots.get("pass_count") != 3:
        raise ValueError(ctx.cfg["routes"]["source_stop"])
    auth = {
        "passed": True,
        "d1r4_authentication": copy.deepcopy(d1r4_auth),
        "d1r5_output_hashes": hashes,
        "d1r5_log_hashes": log_hashes,
        "d1r5_candidate_specs_digest": _digest(specs),
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
        raise ValueError("D1R6 installed package manifest identity changed")
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
        raise ValueError("D1R6 installed package inventory changed")
    for line in lines:
        expected, relative = line.split(None, 1)
        path = root / relative.strip()
        if not path.is_file() or _sha256(path) != expected:
            raise ValueError(f"D1R6 package hash changed: {relative.strip()}")
    return {"passed": True, **_package_fingerprint(ctx), "file_count": len(listed)}


def _prepare_dirs(paths: Paths) -> None:
    if paths.state.exists() or paths.final.exists() or any(paths.raw.glob("*.json.gz")):
        raise ValueError("D1R6 fresh offline preflight requires a new empty stage")
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
        raise ValueError("D1R6 frozen resume/source fingerprint changed")
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
            "variant_id": f"stage4_2r3c3t13s24d1r6_{experiment_id}",
            "stage4_2r3c3t13s24d1r6_restart_snapshot_dir": str(
                spec["restart_snapshot_dir"]
            ),
            "stage4_2r3c3t13s24d1r6_snapshot_manifest_digest": str(
                spec["restart_snapshot_manifest_digest"]
            ),
            "stage4_2r3c3t13s24d1r6_selection_label_available_to_controller": False,
        }
    )
    _write_json(ctx.paths.variants / f"payload_{experiment_id}.json", payload)
    return payload


_D1R6_CONTROLLER_FORBIDDEN_SPEC_KEYS = frozenset(
    {
        "d1r4_source_d1r2_experiment_id",
        "d1r4_split_contract",
        "d1r6_source_d1r4_experiment_id",
        "d1r6_recursive_contract",
        "candidate_preflight_sha256",
        "pair_id",
        "history_member",
        "partition",
    }
)


def _controller_spec(spec: Mapping[str, Any]) -> dict[str, Any]:
    clean = copy.deepcopy(dict(spec))
    for key in _D1R6_CONTROLLER_FORBIDDEN_SPEC_KEYS:
        clean.pop(key, None)
    output = d1r2.s24.s21.s16.s9._controller_spec(clean)
    forbidden = {
        *_D1R6_CONTROLLER_FORBIDDEN_SPEC_KEYS,
        "pair_id",
        "history_member",
        "partition",
        "d1r4_source_d1r2_experiment_id",
        "d1r6_source_d1r4_experiment_id",
        "d1r6_recursive_contract",
    }
    remaining = forbidden.intersection(output)
    if remaining:
        raise ValueError(
            "D1R6 forbidden selection label reached controller: "
            + ",".join(sorted(remaining))
        )
    return output


class CausalRecursiveSplitReturnSafetySentinelController(
    d1r4.CausalSplitReturnSafetySentinelController
):
    """Fresh causal recursive return with a hard task-step-22 finish boundary."""

    def __init__(self, *args: Any, recursive_cfg: Mapping[str, Any], **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.recursive_cfg = copy.deepcopy(dict(recursive_cfg))
        self._recursive_continuation_count = 0
        self._recursive_finish_count = 0
        self._last_recursive_event: dict[str, Any] | None = None

    def _cancel(
        self, slot: int, currents: np.ndarray, baseline_action: np.ndarray
    ) -> tuple[np.ndarray, dict[str, Any]]:
        action, event = super()._cancel(slot, currents, baseline_action)
        if event.get("event") != "sequential_cancel_split_start":
            return action, event
        event = copy.deepcopy(event)
        event.update(
            stage=STAGE,
            campaign_identity=CAMPAIGN_IDENTITY,
            controller_revision=CONTROLLER_REVISION,
        )
        if self._split_pending is None:
            raise ValueError("D1R6 split start did not create pending state")
        self._split_pending["split_start_event"] = copy.deepcopy(event)
        self._split_pending["intermediate_history"] = [
            copy.deepcopy(event["intermediate_card15_fields"])
        ]
        self._split_pending["continuation_count"] = 0
        self._last_split_start_event = copy.deepcopy(event)
        return np.asarray(action, dtype=float), event

    def _telescope(
        self,
        stored: Sequence[str],
        target: Sequence[str],
        history: Sequence[Sequence[str]],
    ) -> bool:
        if not history:
            return False
        for coil in range(N_COILS):
            c = d1r2.s24.s21.s16.s9._decimal_field(stored[coil])
            t = d1r2.s24.s21.s16.s9._decimal_field(target[coil])
            values = [
                d1r2.s24.s21.s16.s9._decimal_field(row[coil]) for row in history
            ]
            total = (t - c) + (values[0] - t)
            total += sum(
                (right - left) for left, right in zip(values[:-1], values[1:])
            )
            total += c - values[-1]
            if total != Decimal(0):
                return False
        return True

    def _direct_event(
        self, currents: np.ndarray, baseline_action: np.ndarray
    ) -> tuple[np.ndarray, dict[str, Any]]:
        pending = self._split_pending
        if pending is None:
            raise ValueError("D1R6 direct finish has no pending return")
        stored = tuple(map(str, pending["stored_center_card15_fields"]))
        target = tuple(map(str, pending["issue_target_card15_fields"]))
        history = [tuple(map(str, row)) for row in pending["intermediate_history"]]
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
        action = np.asarray(chosen["action_norm_tsc"], dtype=float).reshape(N_COILS)
        applied = self.actuator.apply(currents, action)
        increment = float(chosen["incremental_normalized_action_linf"])
        criteria = {
            "pending_start_step_exact": int(pending["start_task_step"])
            == int(self.recursive_cfg["initial_split_task_step"]),
            "finish_window": int(self.recursive_cfg["first_continuation_task_step"])
            <= int(self.step)
            <= int(self.recursive_cfg["latest_finish_task_step"]),
            "slot_exact": int(pending["slot"])
            == int(self.recursive_cfg["split_slot"]),
            "minimum_one_continuation": int(pending.get("continuation_count", 0))
            >= int(self.recursive_cfg["minimum_continuation_count"]),
            "maximum_continuations": int(pending.get("continuation_count", 0))
            <= int(self.recursive_cfg["maximum_continuation_count"]),
            "chosen_target_exact": list(chosen["target_fields"]) == list(stored),
            "stored_issue_center_exact": bool(chosen["exact_stored_issue_center"]),
            "target_exact": list(applied.card15_fields) == list(stored),
            "exact_fields": all(
                len(field) == 10
                and d1r2.s24.s21.s16.s9.format_number(
                    float(d1r2.s24.s21.s16.s9._decimal_field(field))
                )
                == field
                for field in stored
            ),
            "expanded_exact_decimal_telescope": self._telescope(stored, target, history),
            "no_saturation": not any(applied.action_saturated),
            "no_current_clip": not any(applied.current_limit_clipped),
            "finish_increment": increment
            <= float(self.recursive_cfg["direct_finish_threshold"]) + 1e-12,
            "original_increment": increment
            <= float(self.recursive_cfg["maximum_original_increment"]) + 1e-12,
            "total_action": float(chosen["total_normalized_action_abs"])
            <= float(self.recursive_cfg["maximum_total_normalized_action_abs"]) + 1e-12,
            "current_bounds": bool(chosen["current_bounds_pass"]),
            "current_utilization": float(chosen["predicted_maximum_current_utilization"])
            <= float(self.recursive_cfg["maximum_current_utilization"]) + 1e-12,
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
            "continuation_count": int(pending.get("continuation_count", 0)),
            "stored_center_card15_fields": list(stored),
            "issue_target_card15_fields": list(target),
            "intermediate_history_card15_fields": [list(row) for row in history],
            "baseline_action_norm_tsc": np.asarray(baseline_action, dtype=float).tolist(),
            "finish_action_norm_tsc": action.tolist(),
            "incremental_normalized_action_linf": increment,
            "total_normalized_action_abs": float(chosen["total_normalized_action_abs"]),
            "predicted_current_utilization": float(
                chosen["predicted_maximum_current_utilization"]
            ),
            "criteria": criteria,
            "passed": bool(all(criteria.values())),
            "actuator_prediction": copy.deepcopy(chosen),
        }
        return action, event

    def _continuation(
        self,
        currents: np.ndarray,
        baseline_action: np.ndarray,
        direct_action: np.ndarray,
        direct_event: Mapping[str, Any],
    ) -> tuple[np.ndarray, dict[str, Any]]:
        pending = self._split_pending
        if pending is None:
            raise ValueError("D1R6 continuation has no pending return")
        stored = tuple(map(str, pending["stored_center_card15_fields"]))
        target = tuple(map(str, pending["issue_target_card15_fields"]))
        history = [tuple(map(str, row)) for row in pending["intermediate_history"]]
        baseline = np.asarray(baseline_action, dtype=float).reshape(N_COILS)
        direct = np.asarray(direct_action, dtype=float).reshape(N_COILS)
        direct_increment = float(direct_event["incremental_normalized_action_linf"])
        target_increment = float(self.recursive_cfg["continuation_target_increment"])
        alpha = target_increment / direct_increment if direct_increment > 0.0 else 0.0
        alpha = min(1.0, alpha)
        action = baseline + alpha * (direct - baseline)
        applied = self.actuator.apply(currents, action)
        reproduced = self.actuator.apply(currents, action)
        fields = tuple(map(str, applied.card15_fields))
        turns = np.asarray(self.turns_tsc, dtype=float)
        target_current = np.asarray(
            [
                float(d1r2.s24.s21.s16.s9._decimal_field(field)) * 1000.0 / turn
                for field, turn in zip(fields, turns)
            ],
            dtype=float,
        )
        minimum = np.asarray(self.base.min_current, dtype=float)
        maximum = np.asarray(self.base.max_current, dtype=float)
        utilization = d1r2.s24.s21.s16.s9._current_utilization(
            target_current, minimum, maximum
        )
        increment = float(np.max(np.abs(action - baseline)))
        total = float(np.max(np.abs(action)))
        new_history = history + [fields]
        count = int(pending.get("continuation_count", 0)) + 1
        criteria = {
            "direct_finish_rejected": not bool(direct_event.get("passed")),
            "before_latest_finish_step": int(self.step)
            < int(self.recursive_cfg["latest_finish_task_step"]),
            "first_continuation_step_exact": count != 1
            or int(self.step) == int(self.recursive_cfg["first_continuation_task_step"]),
            "continuation_count": count
            <= int(self.recursive_cfg["maximum_continuation_count"]),
            "slot_exact": int(pending["slot"])
            == int(self.recursive_cfg["split_slot"]),
            "alpha_strictly_between_zero_and_one": 0.0 < alpha < 1.0,
            "continuation_increment_exact": abs(increment - target_increment) <= 1e-12,
            "continuation_increment_cap": increment
            <= float(self.recursive_cfg["maximum_continuation_increment"]) + 1e-12,
            "original_increment": increment
            <= float(self.recursive_cfg["maximum_original_increment"]) + 1e-12,
            "total_action": total
            <= float(self.recursive_cfg["maximum_total_normalized_action_abs"]) + 1e-12,
            "current_bounds": bool(
                np.all(target_current >= minimum) and np.all(target_current <= maximum)
            ),
            "current_utilization": utilization
            <= float(self.recursive_cfg["maximum_current_utilization"]) + 1e-12,
            "exact_card15_continuation": all(
                len(field) == 10
                and d1r2.s24.s21.s16.s9.format_number(
                    float(d1r2.s24.s21.s16.s9._decimal_field(field))
                )
                == field
                for field in fields
            ),
            "continuation_reproduction": list(reproduced.card15_fields) == list(fields),
            "continuation_differs_from_center": list(fields) != list(stored),
            "continuation_differs_from_previous": list(fields) != list(history[-1]),
            "expanded_exact_decimal_telescope": self._telescope(
                stored, target, new_history
            ),
            "no_saturation": not any(applied.action_saturated),
            "no_current_clip": not any(applied.current_limit_clipped),
        }
        event = {
            "event": "sequential_cancel_split_continue",
            "stage": STAGE,
            "campaign_identity": CAMPAIGN_IDENTITY,
            "controller_revision": CONTROLLER_REVISION,
            "slot": int(pending["slot"]),
            "split_start_task_step": int(pending["start_task_step"]),
            "task_step": int(self.step),
            "continuation_count": count,
            "stored_center_card15_fields": list(stored),
            "issue_target_card15_fields": list(target),
            "previous_intermediate_card15_fields": list(history[-1]),
            "continuation_card15_fields": list(fields),
            "baseline_action_norm_tsc": baseline.tolist(),
            "direct_finish_event": copy.deepcopy(dict(direct_event)),
            "continuation_target_increment": target_increment,
            "alpha": alpha,
            "continuation_action_norm_tsc": action.tolist(),
            "continuation_incremental_normalized_action_linf": increment,
            "continuation_total_normalized_action_abs": total,
            "predicted_current_utilization": utilization,
            "criteria": criteria,
            "passed": bool(all(criteria.values())),
        }
        self._last_recursive_event = copy.deepcopy(event)
        if not event["passed"]:
            self._last_failed_event = copy.deepcopy(event)
            raise ValueError(
                "D1R6 recursive continuation failed: "
                + json.dumps(event, sort_keys=True)
            )
        pending["intermediate_card15_fields"] = list(fields)
        pending["intermediate_history"] = [list(row) for row in new_history]
        pending["continuation_count"] = count
        self._recursive_continuation_count += 1
        return action, event

    def _finish(
        self, currents: np.ndarray, baseline_action: np.ndarray
    ) -> tuple[np.ndarray, dict[str, Any]]:
        direct_action, direct_event = self._direct_event(currents, baseline_action)
        if direct_event["passed"]:
            self._active_issue = None
            self._split_pending = None
            self._split_finish_count += 1
            self._recursive_finish_count += 1
            self._last_recursive_event = copy.deepcopy(direct_event)
            return direct_action, direct_event
        if int(self.step) < int(self.recursive_cfg["latest_finish_task_step"]):
            return self._continuation(
                currents, baseline_action, direct_action, direct_event
            )
        stop = copy.deepcopy(direct_event)
        stop.update(
            event="sequential_cancel_recursive_deadline_stop",
            direct_finish_event=copy.deepcopy(direct_event),
            failed_candidate_applied=False,
            plant_advance_after_failure=False,
            passed=False,
        )
        self._last_recursive_event = copy.deepcopy(stop)
        self._last_failed_event = copy.deepcopy(stop)
        raise ValueError(
            "D1R6 recursive finish deadline failed: "
            + json.dumps(stop, sort_keys=True)
        )

    def action(
        self, current_state: Mapping[str, Any]
    ) -> tuple[np.ndarray, dict[str, Any]]:
        pending_before = self._split_pending is not None
        if pending_before and not (
            int(self.recursive_cfg["first_continuation_task_step"])
            <= int(self.step)
            <= int(self.recursive_cfg["latest_finish_task_step"])
        ):
            raise ValueError("D1R6 pending return reached an unexpected task step")
        action, trace = super(
            d1r4.CausalSplitReturnSafetySentinelController, self
        ).action(current_state)
        action = np.asarray(action, dtype=float)
        event: dict[str, Any] = {}
        event_name = "none"
        if pending_before:
            action, event = self._finish(
                np.asarray(current_state["currents_a_tsc"], dtype=float), action
            )
            event_name = str(event["event"])
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
                "r3c3t13s24d1r6_safety_sentinel_only": True,
                "r3c3t13s24d1r6_controller_revision": CONTROLLER_REVISION,
                "r3c3t13s24d1r6_event": event_name,
                "r3c3t13s24d1r6_event_detail": copy.deepcopy(event),
                "r3c3t13s24d1r6_split_pending_after_action": self._split_pending
                is not None,
                "r3c3t13s24d1r6_source_selection_label_used": False,
                "r3c3t13s24d1r6_pair_history_partition_label_used": False,
                "r3c3t13s24d1r6_source_outcome_used": False,
                "r3c3t13s24d1r6_future_measurement_used": False,
                "r3c3t13s24d1r6_future_executed_action_used": False,
                "r3c3t13s24d1r6_hidden_wire_current_used": False,
                "r3c3t13s24d1r6_schedule_available_to_underlying_controller": False,
            }
        )
        return action, trace


class LocalWorker:
    """One fresh authentic TSC process and D1R6 controller per rollout."""

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
        recursive_cfg: dict[str, Any],
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
        self.recursive_cfg = recursive_cfg

    def close(self) -> None:
        self.plant.close()

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        failed = True
        trajectory: list[dict[str, Any]] = []
        trace: list[dict[str, Any]] = []
        controller: CausalRecursiveSplitReturnSafetySentinelController | None = None
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
                raise ValueError("D1R6 formal horizon changed")
            self.base.env.reset()
            zero = np.zeros(N_COILS, dtype=np.float32)
            trajectory.append(
                d1r2.s24.s21.s16.s9.t11.t1.r1._state_record_full(
                    self.base.env, 0, zero
                )
            )
            controller = CausalRecursiveSplitReturnSafetySentinelController(
                self.base,
                self.bundle,
                _controller_spec(spec),
                trajectory[0],
                self.lattice_cfg,
                self.calibration_cfg,
                self.dynamic_cfg,
                self.schedule_cfg,
                split_cfg=self.split_cfg,
                recursive_cfg=self.recursive_cfg,
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
                    raise RuntimeError("environment truncated before D1R6 horizon")
            events = [
                row["r3c3t13s24d1r6_event"]
                for row in trace
                if row["r3c3t13s24d1r6_event"] != "none"
            ]
            expected_prefix = [
                "sequential_issue",
                "sequential_cancel",
                "sequential_issue",
                "sequential_cancel",
                "sequential_issue",
                "sequential_cancel",
                "sequential_issue",
                "sequential_cancel_split_start",
            ]
            details = [
                row["r3c3t13s24d1r6_event_detail"]
                for row in trace
                if row["r3c3t13s24d1r6_event"] != "none"
            ]
            continuation_events = [
                row for row in details if row.get("event") == "sequential_cancel_split_continue"
            ]
            finish_events = [
                row for row in details if row.get("event") == "sequential_cancel_split_finish"
            ]
            event_schedule_exact = bool(
                events[:8] == expected_prefix
                and 1 <= len(continuation_events) <= 3
                and events[8:-1]
                == ["sequential_cancel_split_continue"] * len(continuation_events)
                and events[-1:] == ["sequential_cancel_split_finish"]
                and len(finish_events) == 1
                and int(continuation_events[0].get("task_step", -1)) == 19
                and int(finish_events[0].get("task_step", 99)) <= 22
            )
            success = bool(
                len(trajectory) == horizon + 1
                and len(trace) == horizon
                and not any(bool(row.get("abnormal")) for row in trajectory)
                and all(
                    bool(row.get("computed_online"))
                    and bool(row.get("solver_success"))
                    for row in trace
                )
                and event_schedule_exact
                and len(details) == 8 + len(continuation_events) + 1
                and all(bool(row.get("passed")) for row in details)
                and bool(trace[7]["r3c3t13s21_exact_calibration_net_zero"])
                and controller._active_issue is None
                and controller._split_pending is None
                and controller._split_start_count == 1
                and controller._split_finish_count == 1
                and controller._recursive_finish_count == 1
                and controller._recursive_continuation_count
                == len(continuation_events)
            )
            result.update(
                {
                    "success": success,
                    "completed": True,
                    "failure_class": "" if success else "runtime_or_execution_gate",
                    "failure_reason": "" if success else "invalid D1R6 full rollout",
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
                        "recursive_continuation_count": (
                            controller._recursive_continuation_count
                        ),
                        "recursive_finish_count": controller._recursive_finish_count,
                        "recursive_finish_task_step": int(
                            finish_events[0]["task_step"]
                        ) if finish_events else None,
                        "split_pending_at_end": controller._split_pending is not None,
                        "full_event_schedule_exact": event_schedule_exact,
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
                    reason="stage4_2r3c3t13s24d1r6_split_return_safety_sentinel",
                )


_RAY_ACTOR = None


def _ray_actor_class():
    global _RAY_ACTOR
    if _RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1)
        class Stage42R3C3T13S24D1R6Actor:
            def __init__(self, *args: Any):
                self.worker = LocalWorker(*args)

            def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
                return self.worker.evaluate(spec)

            def close(self) -> bool:
                self.worker.close()
                return True

        _RAY_ACTOR = Stage42R3C3T13S24D1R6Actor
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
            raise ValueError("D1R6 existing raw incompatible; refusing overwrite")
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
        raise ValueError("D1R6 fresh rollout requires empty raw directory")
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
        ctx.source_d1r4_ctx.cfg["split_contract"],
        ctx.cfg["recursive_contract"],
    )
    if backend == "serial":
        for index, spec in enumerate(pending):
            worker = LocalWorker(
                payloads[str(spec["experiment_id"])],
                args_tail[0],
                args_tail[1],
                f"stage42r3c3t13s24d1r6_serial_{index:03d}",
                *args_tail[2:],
            )
            try:
                result = worker.evaluate(spec)
            finally:
                worker.close()
            _write_json_gz(ctx.paths.raw / f"{spec['experiment_id']}.json.gz", result)
            print(f"[T13S24D1R6] {index + 1}/{len(pending)}", flush=True)
    elif backend == "ray" and pending:
        import ray

        plan = d1r2.s24.s21.s16.ensure_ray_worker_plan(
            ray,
            requested_workers=int(ctx.cfg["parallel"]["n_workers"]),
            pending_tasks=len(pending),
            ray_tmpdir=os.environ.get("RAY_TMPDIR") or ctx.cfg["storage"]["ray_tmpdir"],
            log_prefix="[T13S24D1R6]",
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
                    f"stage42r3c3t13s24d1r6_{batch_start + offset:03d}",
                    *args_tail[2:],
                )
                actors.append(actor)
                refs[actor.evaluate.remote(spec)] = spec
            try:
                while refs:
                    ready, _ = ray.wait(list(refs), num_returns=1, timeout=30.0)
                    if not ready:
                        print(
                            f"[T13S24D1R6] waiting {completed}/{len(pending)}",
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
                        print(f"[T13S24D1R6] {completed}/{len(pending)}", flush=True)
            finally:
                close_refs = [actor.close.remote() for actor in actors]
                if close_refs:
                    ray.get(close_refs, timeout=120.0)
                for actor in actors:
                    ray.kill(actor, no_restart=True)
    elif backend != "ray":
        raise ValueError(f"unsupported D1R6 backend: {backend}")
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
        "r3c3t13s24d1r6_source_selection_label_used",
        "r3c3t13s24d1r6_pair_history_partition_label_used",
        "r3c3t13s24d1r6_source_outcome_used",
        "r3c3t13s24d1r6_future_measurement_used",
        "r3c3t13s24d1r6_future_executed_action_used",
        "r3c3t13s24d1r6_hidden_wire_current_used",
        "r3c3t13s24d1r6_schedule_available_to_underlying_controller",
    )
    return base + sum(any(bool(row.get(key)) for key in keys) for row in trace)


def _source_trace_projection(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(value)
        for key, value in row.items()
        if not key.startswith("r3c3t13s24d1r6_")
    }


def _all_finite(value: Any) -> bool:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return True
    if isinstance(value, (int, float)):
        return math.isfinite(float(value))
    if isinstance(value, Mapping):
        return all(_all_finite(item) for item in value.values())
    if isinstance(value, Sequence):
        return all(_all_finite(item) for item in value)
    return True


def _initial_restart_exact(
    result: Mapping[str, Any], state_map: Mapping[str, Mapping[str, Any]]
) -> tuple[bool, bool, bool]:
    initial = result["trajectory"][0]
    generated = state_map[str(result["spec"]["state_generation_experiment_id"])]
    generated_visible = np.asarray(
        [generated["R"], generated["Z"], generated["Ip"], *generated["coil_currents_a"]],
        dtype=float,
    )
    restarted_visible = np.asarray(
        [initial["R"], initial["Z"], initial["Ip"], *initial["currents_a_tsc"]],
        dtype=float,
    )
    generated_wire = np.asarray(generated["wire_currents_a"], dtype=float)
    restarted_wire = np.asarray(initial["wire_currents_a"], dtype=float)
    visible = bool(np.array_equal(generated_visible, restarted_visible))
    wire = bool(
        generated_wire.shape == restarted_wire.shape
        and np.array_equal(generated_wire, restarted_wire)
    )
    return visible, wire, bool(visible and wire)


def _float_exact(left: Any, right: Any) -> bool:
    return math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=1e-12)


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
    _, _, _ = _authenticate_source(ctx)
    source_raw_dir = ctx.source_d1r4_ctx.paths.raw
    d1r5_detailed = _read_json(
        ctx.source_d1r5_primary_output
        / "stage4_2r3c3t13s24d1r5_detailed_v1.json"
    )
    d1r5_rows = {
        str(row["source_experiment_id"]): row for row in d1r5_detailed["rows"]
    }
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
    expected_prefix_events = [
        "sequential_issue",
        "sequential_cancel",
        "sequential_issue",
        "sequential_cancel",
        "sequential_issue",
        "sequential_cancel",
        "sequential_issue",
        "sequential_cancel_split_start",
    ]
    rows: list[dict[str, Any]] = []
    for spec in specs:
        path = ctx.paths.raw / f"{spec['experiment_id']}.json.gz"
        base_row = {
            "experiment_id": spec["experiment_id"],
            "source_d1r4_experiment_id": spec["d1r6_source_d1r4_experiment_id"],
            "source_d1r2_experiment_id": spec["d1r4_source_d1r2_experiment_id"],
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
        failure_event = result.get("action_failure_event") or {}
        structured = bool(
            not result.get("success")
            and result.get("failure_class") == "structured_action_schedule_gate"
            and isinstance(failure_event, dict)
            and not bool(failure_event.get("passed"))
        )
        if not result.get("success") and not structured:
            rows.append(
                {
                    **base_row,
                    "strict_parse_pass": True,
                    "identity_pass": True,
                    "result_success": False,
                    "structured_action_failure": False,
                    "failure_event": copy.deepcopy(failure_event),
                    "classification": (
                        "scientific_gate_failure"
                        if result.get("failure_class") == "runtime_or_execution_gate"
                        else "runtime_or_environment_error"
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
            restart_visible, restart_wire, restart_exact = _initial_restart_exact(
                result, state_map
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
                row.get("r3c3t13s24d1r6_event")
                for row in trace
                if row.get("r3c3t13s24d1r6_event") != "none"
            ]
            details = [
                row["r3c3t13s24d1r6_event_detail"]
                for row in trace
                if row.get("r3c3t13s24d1r6_event") != "none"
            ]
            issues = [row for row in details if row.get("event") == "sequential_issue"]
            direct = [row for row in details if row.get("event") == "sequential_cancel"]
            starts = [
                row
                for row in details
                if row.get("event") == "sequential_cancel_split_start"
            ]
            continuations = [
                row
                for row in details
                if row.get("event") == "sequential_cancel_split_continue"
            ]
            finishes = [
                row
                for row in details
                if row.get("event") == "sequential_cancel_split_finish"
            ]
            source_id = str(spec["d1r6_source_d1r4_experiment_id"])
            source_result = _read_raw(source_raw_dir / f"{source_id}.json.gz")
            source_trace = source_result.get("controller_trace") or []
            source_trajectory = source_result.get("trajectory") or []
            prefix_action_exact = bool(
                len(source_trace) == 19
                and len(trace) >= 19
                and np.array_equal(
                    np.asarray([row["action_norm_tsc"] for row in trace[:19]]),
                    np.asarray([row["action_norm_tsc"] for row in source_trace]),
                )
            )
            prefix_trace_exact = bool(
                len(source_trace) == 19
                and len(trace) >= 18
                and all(
                    _source_trace_projection(current)
                    == d1r4._source_trace_projection(source)
                    for current, source in zip(trace[:18], source_trace[:18])
                )
            )
            prefix_state_exact = bool(
                len(source_trajectory) == 20
                and len(trajectory) >= 20
                and trajectory[:20] == source_trajectory
            )
            source_starts = [
                row["r3c3t13s24d1r4_event_detail"]
                for row in source_trace
                if row.get("r3c3t13s24d1r4_event")
                == "sequential_cancel_split_start"
            ]
            start_match = bool(
                len(starts) == 1
                and len(source_starts) == 1
                and np.array_equal(
                    np.asarray(starts[0]["split_start_action_norm_tsc"]),
                    np.asarray(source_starts[0]["split_start_action_norm_tsc"]),
                )
                and starts[0]["intermediate_card15_fields"]
                == source_starts[0]["intermediate_card15_fields"]
                and math.isclose(
                    float(starts[0]["alpha"]),
                    float(source_starts[0]["alpha"]),
                    rel_tol=0.0,
                    abs_tol=1e-12,
                )
                and int(starts[0].get("task_step", -1)) == 18
                and float(
                    starts[0].get(
                        "split_start_incremental_normalized_action_linf", math.inf
                    )
                )
                == 0.175
                and bool(starts[0].get("passed"))
                and all(bool(value) for value in (starts[0].get("criteria") or {}).values())
            )
            first_continuation = continuations[0] if continuations else {}
            d1r5_event = d1r5_rows[source_id]["continuation_event"]
            first_direct = first_continuation.get("direct_finish_event") or {}
            d1r5_direct = d1r5_event.get("direct_finish_prediction") or {}
            first_continuation_exact = bool(
                len(continuations) >= 1
                and int(first_continuation.get("task_step", -1)) == 19
                and int(first_continuation.get("continuation_count", -1)) == 1
                and np.array_equal(
                    np.asarray(first_continuation.get("baseline_action_norm_tsc")),
                    np.asarray(d1r5_event["baseline_action_norm_tsc"]),
                )
                and np.array_equal(
                    np.asarray(first_continuation.get("continuation_action_norm_tsc")),
                    np.asarray(d1r5_event["continuation_action_norm_tsc"]),
                )
                and first_continuation.get("continuation_card15_fields")
                == d1r5_event["continuation_card15_fields"]
                and first_continuation.get("previous_intermediate_card15_fields")
                == d1r5_event["previous_intermediate_card15_fields"]
                and first_continuation.get("stored_center_card15_fields")
                == d1r5_event["stored_center_card15_fields"]
                and first_continuation.get("issue_target_card15_fields")
                == d1r5_event["issue_target_card15_fields"]
                and _float_exact(first_continuation.get("alpha"), d1r5_event["alpha"])
                and _float_exact(
                    first_continuation.get(
                        "continuation_incremental_normalized_action_linf"
                    ),
                    d1r5_event["continuation_incremental_normalized_action_linf"],
                )
                and _float_exact(
                    first_continuation.get("continuation_total_normalized_action_abs"),
                    d1r5_event["continuation_total_normalized_action_abs"],
                )
                and np.array_equal(
                    np.asarray(first_direct.get("finish_action_norm_tsc")),
                    np.asarray(d1r5_direct["action_norm_tsc"]),
                )
                and _float_exact(
                    first_direct.get("incremental_normalized_action_linf"),
                    d1r5_direct["incremental_normalized_action_linf"],
                )
                and first_direct.get("stored_center_card15_fields")
                == d1r5_direct["target_fields"]
            )
            continuation_steps = [int(row.get("task_step", -1)) for row in continuations]
            continuation_schedule = bool(
                1 <= len(continuations) <= 3
                and continuation_steps == list(range(19, 19 + len(continuations)))
                and all(
                    int(row.get("continuation_count", -1)) == index
                    and bool(row.get("passed"))
                    and all(bool(value) for value in (row.get("criteria") or {}).values())
                    and _float_exact(
                        row.get("continuation_incremental_normalized_action_linf"),
                        ctx.cfg["recursive_contract"]["continuation_target_increment"],
                    )
                    for index, row in enumerate(continuations, start=1)
                )
            )
            finish = finishes[0] if len(finishes) == 1 else {}
            finish_pass = bool(
                finish.get("passed")
                and all((finish.get("criteria") or {}).values())
                and float(finish.get("incremental_normalized_action_linf", math.inf))
                <= 0.24 + 1e-12
                and 20 <= int(finish.get("task_step", -1)) <= 22
                and int(finish.get("task_step", -1)) == 19 + len(continuations)
                and int(finish.get("continuation_count", -1)) == len(continuations)
            )
            forbidden = _forbidden_trace_count(trace)
            summary = result.get("hidden_history_control_summary") or {}
            runtime_pass = bool(
                len(trajectory) == 36
                and len(trace) == 35
                and np.all(np.isfinite(currents))
                and np.all(np.isfinite(actions))
                and _all_finite(result)
                and not any(bool(row.get("abnormal")) for row in trajectory)
                and all(
                    float(row.get("gotsc_subprocess_s", 0.0)) > 0.0
                    for row in trajectory[1:]
                )
            )
            restart_pass = restart_exact
            expected_events = [
                *expected_prefix_events,
                *(["sequential_cancel_split_continue"] * len(continuations)),
                "sequential_cancel_split_finish",
            ]
            action_pass = bool(
                result.get("success")
                and
                all(
                    bool(row.get("computed_online"))
                    and bool(row.get("solver_success"))
                    for row in trace
                )
                and calibration_events == expected_calibration
                and events == expected_events
                and len(issues) == 4
                and len(direct) == 3
                and len(starts) == 1
                and len(finishes) == 1
                and all(bool(row.get("passed")) for row in details)
                and prefix_action_exact
                and prefix_trace_exact
                and prefix_state_exact
                and start_match
                and first_continuation_exact
                and continuation_schedule
                and finish_pass
                and forbidden == 0
                and bool(phase["passed"])
                and np.array_equal(actions, recorded)
                and float(np.max(np.abs(actions))) <= 1.0 + 1e-12
                and not bool(summary.get("split_pending_at_end"))
                and int(summary.get("split_start_count", 0)) == 1
                and int(summary.get("split_finish_count", 0)) == 1
                and int(summary.get("recursive_continuation_count", 0))
                == len(continuations)
                and int(summary.get("recursive_finish_count", 0)) == 1
                and int(summary.get("recursive_finish_task_step", -1))
                == int(finish.get("task_step", -2))
            )
            passed = bool(
                runtime_pass
                and restart_pass
                and action_pass
                and calibration["passed"]
                and utilization
                <= float(ctx.cfg["recursive_contract"]["maximum_current_utilization"])
                + 1e-12
            )
            if structured:
                deadline_stop = bool(
                    failure_event.get("event")
                    == "sequential_cancel_recursive_deadline_stop"
                    and int(failure_event.get("task_step", -1)) == 22
                    and not bool(failure_event.get("failed_candidate_applied", True))
                    and not bool(failure_event.get("plant_advance_after_failure", True))
                    and len(trajectory) == len(trace) + 1
                    and len(trajectory) == 23
                    and len(trace) == 22
                    and int(trace[-1].get("task_step", -1)) == 21
                )
                executed_prefix_pass = bool(
                    restart_pass
                    and phase["passed"]
                    and calibration["passed"]
                    and calibration_events == expected_calibration
                    and events
                    == [
                        *expected_prefix_events,
                        *(["sequential_cancel_split_continue"] * len(continuations)),
                    ]
                    and len(issues) == 4
                    and len(direct) == 3
                    and len(starts) == 1
                    and not finishes
                    and prefix_action_exact
                    and prefix_trace_exact
                    and prefix_state_exact
                    and start_match
                    and first_continuation_exact
                    and continuation_schedule
                    and forbidden == 0
                    and np.array_equal(actions, recorded)
                    and _all_finite(result)
                    and np.all(np.isfinite(currents))
                    and np.all(np.isfinite(actions))
                    and not any(bool(row.get("abnormal")) for row in trajectory)
                    and all(
                        float(row.get("gotsc_subprocess_s", 0.0)) > 0.0
                        for row in trajectory[1:]
                    )
                )
                rows.append(
                    {
                        **base_row,
                        "strict_parse_pass": True,
                        "identity_pass": True,
                        "result_success": False,
                        "structured_action_failure": True,
                        "structured_deadline_safe_stop": deadline_stop,
                        "executed_prefix_pass": executed_prefix_pass,
                        "failure_event": copy.deepcopy(failure_event),
                        "restart_visible_exact": restart_visible,
                        "restart_wire_exact": restart_wire,
                        "restart_pass": restart_pass,
                        "phase_causality_pass": bool(phase["passed"]),
                        "calibration_pass": bool(calibration["passed"]),
                        "source_prefix_action_exact": prefix_action_exact,
                        "source_prefix_trace_exact": prefix_trace_exact,
                        "source_prefix_state_exact": prefix_state_exact,
                        "split_start_exact": start_match,
                        "first_d1r5_continuation_exact": first_continuation_exact,
                        "continuation_schedule_pass": continuation_schedule,
                        "continuation_event_count": len(continuations),
                        "split_finish_event_count": 0,
                        "maximum_current_utilization": utilization,
                        "forbidden_trace_count": forbidden,
                        "formal_contract_evaluable": False,
                        "classification": "action_schedule_design_failure",
                        "failure_reason": str(result.get("failure_reason", "")),
                        "passed": False,
                    }
                )
                continue
            rows.append(
                {
                    **base_row,
                    "strict_parse_pass": True,
                    "identity_pass": True,
                    "result_success": True,
                    "runtime_full_horizon_pass": runtime_pass,
                    "restart_pass": restart_pass,
                    "restart_visible_exact": restart_visible,
                    "restart_wire_exact": restart_wire,
                    "phase_causality_pass": bool(phase["passed"]),
                    "calibration_pass": bool(calibration["passed"]),
                    "source_prefix_action_exact": prefix_action_exact,
                    "source_prefix_trace_exact": prefix_trace_exact,
                    "source_prefix_state_exact": prefix_state_exact,
                    "split_start_exact": start_match,
                    "first_d1r5_continuation_exact": first_continuation_exact,
                    "continuation_schedule_pass": continuation_schedule,
                    "action_trace_pass": action_pass,
                    "issue_event_count": len(issues),
                    "direct_cancel_event_count": len(direct),
                    "split_start_event_count": len(starts),
                    "continuation_event_count": len(continuations),
                    "split_finish_event_count": len(finishes),
                    "split_finish_incremental_normalized_action_linf": float(
                        finish.get("incremental_normalized_action_linf", math.inf)
                    ),
                    "maximum_current_utilization": utilization,
                    "forbidden_trace_count": forbidden,
                    "finish_task_step": int(finish.get("task_step", -1)),
                    "expanded_decimal_telescope_pass": bool(
                        (finish.get("criteria") or {}).get(
                            "expanded_exact_decimal_telescope"
                        )
                    ),
                    "formal_contract_evaluable": True,
                    "formal_contract_pass_diagnostic": bool(
                        d1r2.s24.s21.s16.s9.t11.t1.r3b._control_row(
                            ctx.base_d1r2_ctx.base_s24_ctx.base_ctx.base_ctx.base_ctx
                            .base_ctx.base_ctx.base_ctx.source_ctx.source_ctx,
                            result,
                            state_map[str(spec["state_generation_experiment_id"])],
                        ).get("formal_contract_pass")
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
        in {
            "runtime_or_raw_error",
            "runtime_or_environment_error",
            "raw_corruption_error",
            "raw_identity_error",
        }
    ]
    scientific_failures = [
        row
        for row in rows
        if row.get("classification")
        in {
            "action_schedule_design_failure",
            "scientific_gate_failure",
        }
    ]
    passed = bool(
        raw_inventory_exact
        and len(rows) == len(specs)
        and all(bool(row.get("passed")) for row in rows)
    )
    if passed:
        route = ctx.cfg["routes"]["pass"]
    elif scientific_failures:
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
        "source_prefix_state_exact_count": sum(
            bool(row.get("source_prefix_state_exact")) for row in rows
        ),
        "split_start_exact_count": sum(
            bool(row.get("split_start_exact")) for row in rows
        ),
        "first_d1r5_continuation_exact_count": sum(
            bool(row.get("first_d1r5_continuation_exact")) for row in rows
        ),
        "issue_event_count": sum(int(row.get("issue_event_count", 0)) for row in rows),
        "direct_cancel_event_count": sum(
            int(row.get("direct_cancel_event_count", 0)) for row in rows
        ),
        "split_start_event_count": sum(
            int(row.get("split_start_event_count", 0)) for row in rows
        ),
        "continuation_event_count": sum(
            int(row.get("continuation_event_count", 0)) for row in rows
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
        "finish_task_step_counts": [
            {"task_step": step, "count": count}
            for step, count in sorted(
                Counter(
                    int(row["finish_task_step"])
                    for row in rows
                    if int(row.get("finish_task_step", -1)) >= 0
                ).items()
            )
        ],
        "expanded_decimal_telescope_pass_count": sum(
            bool(row.get("expanded_decimal_telescope_pass")) for row in rows
        ),
        "structured_deadline_safe_stop_count": sum(
            bool(row.get("structured_deadline_safe_stop")) for row in rows
        ),
        "forbidden_trace_count": sum(
            int(row.get("forbidden_trace_count", 0)) for row in rows
        ),
        "formal_tracking_pass_count_diagnostic_only": sum(
            bool(row.get("formal_contract_pass_diagnostic")) for row in rows
        ),
        "formal_tracking_evaluable_count": sum(
            bool(row.get("formal_contract_evaluable")) for row in rows
        ),
        "route": route,
        "passed": passed,
        "rows": rows,
    }


def run_rollout(ctx: Context, *, backend: str, resume: bool) -> dict[str, Any]:
    state = _read_json(ctx.paths.state)
    if state.get("phase_status") != "offline_ready" or state.get("finished"):
        raise ValueError("D1R6 rollout requires open offline-ready state")
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
        raise ValueError("D1R6 postprocess requires completed sentinel outputs")
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
            raise ValueError("D1R6 offline cannot resume")
        return prepare_offline(ctx)
    if command == "rollout":
        return run_rollout(ctx, backend=backend, resume=resume)
    if command == "postprocess":
        return run_postprocess(ctx)
    if command == "all":
        if resume:
            if not ctx.paths.state.is_file():
                raise ValueError("D1R6 resume requires existing frozen state")
        else:
            prepare_offline(ctx)
        final = run_rollout(ctx, backend=backend, resume=resume)
        internal = run_postprocess(ctx)
        return {"final": final, "postprocess": internal}
    raise ValueError(f"unsupported D1R6 command: {command}")


def self_test(config_path: Path) -> dict[str, Any]:
    config_path = config_path.expanduser().resolve()
    cfg = _read_json(config_path)
    _validate_config(cfg, config_path)
    return {
        "schema_version": 1,
        "stage": STAGE,
        "expected_real_tsc_rollouts": cfg["spec_contract"]["expected_specs"],
        "split_start_task_step": cfg["recursive_contract"][
            "initial_split_task_step"
        ],
        "first_continuation_task_step": cfg["recursive_contract"][
            "first_continuation_task_step"
        ],
        "latest_finish_task_step": cfg["recursive_contract"][
            "latest_finish_task_step"
        ],
        "maximum_finish_increment": cfg["recursive_contract"][
            "direct_finish_threshold"
        ],
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
    parser.add_argument("--source-d1r4-run", type=Path, required=True)
    parser.add_argument("--source-d1r4-complete-log", type=Path, required=True)
    parser.add_argument("--source-d1r5-primary-output", type=Path, required=True)
    parser.add_argument("--source-d1r5-repeat-output", type=Path, required=True)
    parser.add_argument("--source-d1r5-primary-log", type=Path, required=True)
    parser.add_argument("--source-d1r5-repeat-log", type=Path, required=True)
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
            source_d1r4_run=args.source_d1r4_run,
            source_d1r4_complete_log=args.source_d1r4_complete_log,
            source_d1r5_primary_output=args.source_d1r5_primary_output,
            source_d1r5_repeat_output=args.source_d1r5_repeat_output,
            source_d1r5_primary_log=args.source_d1r5_primary_log,
            source_d1r5_repeat_log=args.source_d1r5_repeat_log,
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
