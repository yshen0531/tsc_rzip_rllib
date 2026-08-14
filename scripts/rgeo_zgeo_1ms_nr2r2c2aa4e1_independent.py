#!/usr/bin/env python3
"""Structurally separate raw audit for the C2aA4E1 one-successor run."""

from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_nr1_independent import _fields, _state  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    assert_exact_slew,
    card15_target_decimal_a,
    decimal_single_turn_currents_a,
)
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import Card15Target  # noqa: E402
from tsc_rzip_rllib.core.runner import TSCConfig  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-nr2r2c2aa4e1-single-successor-exploration-v1"
ROLLOUT_ID = "single_successor_r0"
INDEPENDENT_PASS = "ONE_MS_NR2R2C2AA4E1_INDEPENDENT_AUDIT_PASS"
INDEPENDENT_FAIL = "ONE_MS_NR2R2C2AA4E1_INDEPENDENT_AUDIT_FAIL_STOP"
OFFLINE_PASS = "ONE_MS_NR2R2C2AA4E1_OFFLINE_PREFLIGHT_PASS_RUN_ONLY"
STAGE_RELATIVE_PATH = "configs/rgeo_zgeo_1ms_nr2r2c2aa4e1_single_successor_exploration.json"
STAGE_SHA256 = "f218774252ce044cefd067754f301a87028be114bd73fdf320788ea82fbaedd3"
STATE_FOLDER = re.compile(r"^(\d+)ms$")
RUNTIME_ARTIFACT_FOLDER = re.compile(
    r"^runtime_artifacts_failed_"
    r"(nonzero_returncode|restart_update_failed|collect_outputs_failed|abnormal_output)_"
    r"(\d+)ms$"
)
EXACT_SCHEDULE = [
    {"first_step": 0, "last_step": 0, "level": "q0"},
    {"first_step": 1, "last_step": 1, "level": "level1"},
    {"first_step": 2, "last_step": 16, "level": "level2"},
]
EXACT_LEVEL1_FIELDS = [
    "-3.514E+01", "-4.514E+01", "-4.514E+01", "-3.514E+01",
    "-4.486E+01", "-4.486E+01", "-3.186E+01", "-3.214E+01",
    "-6.000E-02", "6.000E-02 ", "-7.530E+00", "-1.353E+01",
    "-8.170E+00", "-8.230E+00",
]
EXACT_LEVEL2_FIELDS = [
    "-3.528E+01", "-4.528E+01", "-4.528E+01", "-3.528E+01",
    "-4.472E+01", "-4.472E+01", "-3.172E+01", "-3.228E+01",
    "-1.200E-01", "1.200E-01 ", "-7.560E+00", "-1.356E+01",
    "-8.140E+00", "-8.260E+00",
]
EXACT_ROUTES = {
    "input_fail": "ONE_MS_NR2R2C2AA4E1_INPUT_INTEGRITY_FAIL_NO_TSC",
    "offline_fail": "ONE_MS_NR2R2C2AA4E1_OFFLINE_PREFLIGHT_FAIL_NO_TSC",
    "package_or_deployment_fail": "ONE_MS_NR2R2C2AA4E1_PACKAGE_OR_DEPLOYMENT_FAIL_NO_TSC",
    "known_prefix_fail": "ONE_MS_NR2R2C2AA4E1_KNOWN_PREFIX_REPLAY_FAIL_STOP",
    "clearance_fail": "ONE_MS_NR2R2C2AA4E1_PREISSUE_EXPLORATION_CLEARANCE_FAIL_STOP_BEFORE_ISSUE16",
    "novel_execution_fail": "ONE_MS_NR2R2C2AA4E1_NOVEL_SUCCESSOR_EXECUTION_FAIL_STOP",
    "hard_safety_fail": "ONE_MS_NR2R2C2AA4E1_HARD_SAFETY_FAIL_STOP",
    "acceptance_fail": "ONE_MS_NR2R2C2AA4E1_SUCCESSOR_ACCEPTANCE_FAIL_REDESIGN",
    "raw_reporting_fail": "ONE_MS_NR2R2C2AA4E1_RAW_OR_REPORTING_INTEGRITY_FAIL_PRESERVE_RAW",
    "observed": "ONE_MS_NR2R2C2AA4E1_SINGLE_SUCCESSOR_OBSERVED_WITHIN_EMPIRICAL_ENVELOPE_DEVELOPMENT_ONLY",
}


def sha256(path: Path) -> str:
    path = _inside_root(path, "hashed file")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_new(path: Path, payload: dict[str, Any]) -> None:
    path = _inside_root(path, "output")
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def inventory_digest(lines: Iterable[str]) -> str:
    payload = "".join(f"{line}\n" for line in sorted(lines)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _deduplicate(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _inside_root(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT.resolve()):
        raise ValueError(f"{label} leaves repository: {path}")
    return resolved


def _max_difference(left: Sequence[Any], right: Sequence[Any]) -> float:
    if len(left) != len(right):
        return math.inf
    return max((abs(float(a) - float(b)) for a, b in zip(left, right)), default=0.0)


def _load_stage(stage_path: Path) -> tuple[dict[str, Any], TSCConfig]:
    stage_path = _inside_root(stage_path, "stage config")
    if stage_path.relative_to(ROOT.resolve()).as_posix() != STAGE_RELATIVE_PATH:
        raise ValueError("unexpected C2aA4E1 stage-config path")
    if sha256(stage_path) != STAGE_SHA256:
        raise ValueError("C2aA4E1 stage-config hash mismatch")
    stage = json.loads(stage_path.read_text(encoding="utf-8"))
    if stage.get("schema_version") != SCHEMA:
        raise ValueError("unexpected C2aA4E1 schema")
    if any(stage.get(key) != value for key, value in {
        "takeover_time_ms": 1100,
        "control_period_ms": 1,
        "horizon_steps": 17,
        "rollouts": 1,
        "maximum_reset_calls": 1,
        "maximum_plant_advances": 17,
        "maximum_advance_attempts": 17,
        "maximum_plant_advance_gotsc_calls": 17,
        "completed_execution_required_state_count": 18,
        "completed_execution_required_artifact_files": 90,
        "known_prefix_last_issue_step": 15,
        "known_prefix_last_state_index": 16,
        "empirical_exploration_issue_step": 16,
        "empirical_exploration_effect_state_index": 17,
        "empirical_exploration_level2_effect_age": 15,
        "unknown_successor_count": 1,
        "holdout_records_read": 0,
        "raw_records_used_as_fixture": 0,
    }.items()):
        raise ValueError("C2aA4E1 frozen budget/timing/data-use contract mismatch")
    if stage.get("retry_after_any_advance_attempt") != "forbidden":
        raise ValueError("C2aA4E1 retry prohibition is missing")
    if stage.get("model_or_expert_use") != "forbidden" or stage.get("qualification_use") != "forbidden":
        raise ValueError("C2aA4E1 data-use boundary mismatch")
    if stage.get("intended_use") != "simulator_only_single_unknown_successor_development_exploration":
        raise ValueError("C2aA4E1 intended-use boundary mismatch")
    if stage.get("semantic_artifacts") != [
        "inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv"
    ] or stage.get("diagnostic_artifacts") != ["sprsina"]:
        raise ValueError("C2aA4E1 artifact contract mismatch")
    if stage.get("result_counter_contract") != {
        "record_reset_calls_separately": True,
        "record_advance_attempts_separately": True,
        "record_verified_successful_plant_advances_separately": True,
        "partial_failure_raw_must_be_preserved_and_reported": True,
    }:
        raise ValueError("C2aA4E1 counter contract mismatch")
    observation = stage.get("observation_contract", {})
    required_observation = {
        "r_geo_z_geo_ip_exact_noiseless_before_issue": True,
        "same_state_paired_boundary_required": True,
        "invalid_or_missing_boundary_fails_closed": True,
        "complete_causal_history_since_takeover_available": True,
        "pre_takeover_history_asserted_available": False,
        "future_successor_observed_before_issue": False,
    }
    if any(observation.get(key) is not value for key, value in required_observation.items()):
        raise ValueError("C2aA4E1 observation contract mismatch")
    stop = stage.get("post_state17_policy", {})
    if stop != {
        "unconditional_stop": True,
        "issue17_forbidden": True,
        "state18_forbidden": True,
        "return_or_cleanup_plant_action_forbidden": True,
    }:
        raise ValueError("C2aA4E1 post-state17 stop contract mismatch")
    if stage.get("schedule") != EXACT_SCHEDULE:
        raise ValueError("C2aA4E1 schedule mismatch")
    if stage.get("level1_card15_fields") != EXACT_LEVEL1_FIELDS:
        raise ValueError("C2aA4E1 level1 Card15 mismatch")
    if stage.get("level2_card15_fields") != EXACT_LEVEL2_FIELDS:
        raise ValueError("C2aA4E1 level2 Card15 mismatch")
    if stage.get("prefix_match_tolerance") != {
        "geometry_m": 1e-12, "ip_a": 1e-9, "coil_a": 1e-9, "wire_a": 1e-9,
    }:
        raise ValueError("C2aA4E1 prefix tolerance mismatch")
    if stage.get("empirical_successor_acceptance") != {
        "r_geo_m": 0.002,
        "z_geo_m": 0.002,
        "ip_a": 100.0,
        "state17_must_remain_in_inner_envelope": True,
        "is_preaction_transition_bound": False,
    }:
        raise ValueError("C2aA4E1 empirical acceptance mismatch")
    if stage.get("preissue16_outer_clearance") != {
        "r_geo_m": 0.020,
        "z_geo_m": 0.020,
        "ip_a": 1000.0,
        "is_qualified_transition_tube": False,
    }:
        raise ValueError("C2aA4E1 clearance contract mismatch")
    for key, value in {
        "inner_r_radius_m": 0.025,
        "inner_z_radius_m": 0.025,
        "inner_ip_fraction": 0.05,
        "outer_r_radius_m": 0.05,
        "outer_z_radius_m": 0.05,
        "outer_ip_fraction": 0.10,
    }.items():
        if stage.get(key) != value:
            raise ValueError(f"C2aA4E1 frozen threshold mismatch: {key}")
    if stage.get("routes") != EXACT_ROUTES:
        raise ValueError("C2aA4E1 route map mismatch")
    cfg_path = _inside_root(ROOT / stage["base_tsc_config"]["path"], "base TSC config")
    if sha256(cfg_path) != stage["base_tsc_config"]["sha256"]:
        raise ValueError("base TSC config hash mismatch")
    cfg = TSCConfig.from_json(cfg_path)
    if cfg.start_folder != "1100ms" or cfg.dt_ms != 1 or cfg.current_slew_a_per_ms != 0.3:
        raise ValueError("base TSC timing/slew contract mismatch")
    return stage, cfg


def _authenticate_evidence(stage: dict[str, Any], failures: list[str]) -> dict[str, Any]:
    records: dict[str, Any] = {}
    design = stage["design"]
    if sha256(ROOT / design["path"]) != design["sha256"]:
        failures.append("DESIGN_HASH")
    for name, identity in stage["evidence"].items():
        path = ROOT / identity["path"]
        if not path.is_file() or sha256(path) != identity["sha256"]:
            failures.append(f"EVIDENCE_HASH:{name}")
            continue
        if path.suffix == ".json":
            records[name] = json.loads(path.read_text(encoding="utf-8"))
    for name in ("a3_primary", "a3_independent", "a4_support_result"):
        identity = stage["evidence"][name]
        if name in records and records[name].get("route") != identity["expected_route"]:
            failures.append(f"EVIDENCE_ROUTE:{name}")
    primary = records.get("a3_primary", {})
    if (primary.get("passed") is not True or primary.get("execution_passed") is not True
            or primary.get("repeatability_passed") is not True or primary.get("plant_advances") != 64):
        failures.append("A3_PRIMARY_PREMISE")
    independent = records.get("a3_independent", {})
    if (independent.get("audit_passed") is not True or independent.get("plant_advances") != 64
            or independent.get("primary_result_sha256") != stage["evidence"]["a3_primary"]["sha256"]):
        failures.append("A3_INDEPENDENT_PREMISE")
    support = records.get("a4_support_result")
    if support is not None:
        identity = stage["evidence"]["a4_support_result"]
        first = support.get("first_unsupported") or {}
        checks = (
            support.get("supported_transitions") == identity["expected_supported_transitions"],
            support.get("required_transitions") == identity["expected_required_transitions"],
            first.get("issue_step") == identity["expected_first_unsupported_issue_step"],
            first.get("effect_state_index") == identity["expected_first_unsupported_effect_state_index"],
            first.get("level2_dwell_effect_age") == identity["expected_first_unsupported_level2_effect_age"],
        )
        if not all(checks):
            failures.append("A4_SUPPORT_RESULT_CONTRACT")
        if support.get("support_passed") is not False:
            failures.append("A4_SUPPORT_VERDICT")
    return records


def _reference_pair(records: dict[str, Any], stage: dict[str, Any],
                    failures: list[str]) -> dict[str, Any] | None:
    left = records.get("a3_replay_0")
    right = records.get("a3_replay_1")
    if left is None or right is None:
        return None
    if (left.get("passed") is not True or right.get("passed") is not True
            or left.get("plant_advances") != 32 or right.get("plant_advances") != 32):
        failures.append("A3_REFERENCE_EXECUTION")
    if len(left.get("states", [])) != 33 or len(right.get("states", [])) != 33:
        failures.append("A3_REFERENCE_STATE_COUNT")
        return None
    if len(left.get("actions", [])) != 32 or len(right.get("actions", [])) != 32:
        failures.append("A3_REFERENCE_ACTION_COUNT")
        return None
    tolerance = stage["prefix_match_tolerance"]
    semantic = tuple(stage["semantic_artifacts"])
    for index in range(17):
        a, b = left["states"][index], right["states"][index]
        if a.get("time_ms") != b.get("time_ms"):
            failures.append(f"A3_PAIR_TIME:{index}")
        if max(abs(float(a[key]) - float(b[key])) for key in
               ("r_geo_m", "z_geo_m", "r_mid_m", "r_inner_m", "r_outer_m")) > tolerance["geometry_m"]:
            failures.append(f"A3_PAIR_GEOMETRY:{index}")
        if abs(float(a["ip_a"]) - float(b["ip_a"])) > tolerance["ip_a"]:
            failures.append(f"A3_PAIR_IP:{index}")
        if _max_difference(a["actual_current_a_tsc"], b["actual_current_a_tsc"]) > tolerance["coil_a"]:
            failures.append(f"A3_PAIR_COIL:{index}")
        if _max_difference(a["wire_current_a"], b["wire_current_a"]) > tolerance["wire_a"]:
            failures.append(f"A3_PAIR_WIRE:{index}")
        if any(a["artifact_sha256"].get(name) != b["artifact_sha256"].get(name)
               for name in semantic):
            failures.append(f"A3_PAIR_SEMANTIC_ARTIFACT:{index}")
    for index in range(16):
        if left["actions"][index] != right["actions"][index]:
            failures.append(f"A3_PAIR_ACTION:{index}")
    return left


def _target(fields: Sequence[str], cfg: TSCConfig, name: str) -> Card15Target:
    exact = decimal_single_turn_currents_a(
        tuple(value.strip() for value in fields), cfg.turns_tsc, name=name)
    return Card15Target(tuple(fields), tuple(float(value) for value in exact))


def _targets(stage: dict[str, Any], reference: dict[str, Any],
             cfg: TSCConfig) -> tuple[Card15Target, ...]:
    q0 = _target(reference["actions"][0]["expected_card15_fields"], cfg, "e1.independent.q0")
    level1 = _target(stage["level1_card15_fields"], cfg, "e1.independent.level1")
    level2 = _target(stage["level2_card15_fields"], cfg, "e1.independent.level2")
    by_name = {"q0": q0, "level1": level1, "level2": level2}
    result: list[Card15Target | None] = [None] * 17
    for row in stage["schedule"]:
        for step in range(row["first_step"], row["last_step"] + 1):
            result[step] = by_name[row["level"]]
    if any(value is None for value in result):
        raise ValueError("incomplete E1 target stream")
    return tuple(value for value in result if value is not None)


def _expected_action(target: Card15Target, issue: int, maximum: float) -> dict[str, Any]:
    return {
        "issue_step": issue,
        "issue_time_ms": 1100 + issue,
        "expected_card15_fields": list(target.card15_fields),
        "target_current_a_tsc": list(target.current_a_tsc),
        "maximum_issued_delta_a": maximum,
        "effect_state_index": issue + 1,
        "effect_age_steps": 1,
        "effect_delay_steps": 1,
        "level2_dwell_effect_age": issue - 1 if issue >= 2 else None,
    }


def _audit_offline_binding(
    offline: dict[str, Any], stage: dict[str, Any], source_revision: str,
    targets: Sequence[Card15Target], reference: dict[str, Any], cfg: TSCConfig,
    failures: list[str],
) -> None:
    expected_identity = {
        row["path"]: row["sha256"]
        for row in (stage["design"], stage["base_tsc_config"], *stage["evidence"].values())
    }
    exact = {
        "schema_version": SCHEMA,
        "kind": "offline_preflight",
        "source_revision": source_revision,
        "passed": True,
        "route": OFFLINE_PASS,
        "failure_kind": None,
        "failures": [],
        "stage_config_path": STAGE_RELATIVE_PATH,
        "stage_config_sha256": STAGE_SHA256,
        "evidence_identity": expected_identity,
        "reset_calls": 0,
        "advance_attempts": 0,
        "verified_successful_plant_advances": 0,
        "plant_advance_gotsc_calls": 0,
        "new_tsc_or_plant_advances": 0,
    }
    if any(offline.get(key) != value for key, value in exact.items()):
        failures.append("OFFLINE_PREFLIGHT_BINDING")
    previous = tuple(Decimal(str(value)) for value in
                     reference["states"][0]["active_command_decimal_a_tsc"])
    expected_stream: list[dict[str, Any]] = []
    for issue, target in enumerate(targets):
        exact_target = card15_target_decimal_a(
            target, cfg.turns_tsc, name=f"e1.independent.offline.{issue}")
        maximum = assert_exact_slew(
            previous, exact_target, name=f"e1.independent.offline.{issue}")
        expected_stream.append(_expected_action(target, issue, maximum))
        previous = exact_target
    if offline.get("action_stream") != expected_stream:
        failures.append("OFFLINE_ACTION_STREAM")


def _tree_inventory(directories: Sequence[Path], run_dir: Path) -> dict[str, Any]:
    lines: list[str] = []
    total_bytes = 0
    for directory in sorted(directories, key=lambda value: value.as_posix()):
        directory = _inside_root(directory, "raw diagnostic directory")
        for path in sorted(directory.rglob("*"), key=lambda value: value.as_posix()):
            resolved = _inside_root(path, "raw diagnostic artifact")
            if resolved.is_dir():
                continue
            if not resolved.is_file():
                raise ValueError(f"unsupported raw artifact type: {path}")
            size = resolved.stat().st_size
            digest = sha256(resolved)
            total_bytes += size
            lines.append(f"{resolved.relative_to(run_dir).as_posix()}\t{size}\t{digest}")
    return {
        "directories": sorted(path.relative_to(run_dir).as_posix() for path in directories),
        "files": len(lines),
        "bytes": total_bytes,
        "sha256": inventory_digest(lines),
        "entries": sorted(lines),
    }


def _scan_raw_directories(rollout: Path, run_dir: Path) -> dict[str, Any]:
    state_directories: dict[int, Path] = {}
    runtime_directories: list[Path] = []
    unexpected: list[str] = []
    if rollout.is_dir():
        for raw_path in rollout.iterdir():
            path = _inside_root(raw_path, "rollout child")
            if not path.is_dir():
                continue
            state_match = STATE_FOLDER.fullmatch(path.name)
            runtime_match = RUNTIME_ARTIFACT_FOLDER.fullmatch(path.name)
            if state_match is not None:
                state_directories[int(state_match.group(1))] = path
            elif runtime_match is not None and 1100 <= int(runtime_match.group(2)) <= 1117:
                runtime_directories.append(path)
            else:
                unexpected.append(path.relative_to(run_dir).as_posix())
    actual_times = sorted(state_directories)
    actual_indices = [time_ms - 1100 for time_ms in actual_times]
    existing_authorized = [index for index in actual_indices if 0 <= index <= 17]
    continuous_authorized: list[int] = []
    for index in range(18):
        if index not in existing_authorized:
            break
        continuous_authorized.append(index)
    authorized_folders = [state_directories[1100 + index] for index in continuous_authorized]
    unexpected.extend(
        path.relative_to(run_dir).as_posix()
        for time_ms, path in state_directories.items()
        if time_ms < 1100 or time_ms > 1117
    )
    return {
        "state_directories": state_directories,
        "actual_times_ms": actual_times,
        "actual_state_indices": actual_indices,
        "existing_authorized_state_indices": existing_authorized,
        "continuous_state_indices": continuous_authorized,
        "noncontinuous_state_indices": [
            index for index in existing_authorized if index not in continuous_authorized
        ],
        "authorized_continuous_folders": authorized_folders,
        "forbidden_1118_present": 1118 in state_directories,
        "unexpected_directories": sorted(unexpected),
        "runtime_artifacts": _tree_inventory(runtime_directories, run_dir),
        "state_like_inventory": _tree_inventory(
            list(state_directories.values()) + runtime_directories, run_dir),
    }


def _required_raw_inventory(scan: dict[str, Any], run_dir: Path,
                            stage: dict[str, Any]) -> dict[str, Any]:
    names = tuple(stage["semantic_artifacts"]) + tuple(stage["diagnostic_artifacts"])
    lines: list[str] = []
    missing: list[str] = []
    total_bytes = 0
    state_directories = scan["state_directories"]
    authorized_times = [1100 + index for index in scan["existing_authorized_state_indices"]]
    for time_ms in authorized_times:
        folder = state_directories[time_ms]
        for name in names:
            path = _inside_root(folder / name, "required raw artifact")
            relative = path.relative_to(run_dir).as_posix()
            if not path.is_file():
                missing.append(relative)
                continue
            size = path.stat().st_size
            digest = sha256(path)
            total_bytes += size
            lines.append(f"{relative}\t{size}\t{digest}")
    return {
        "required_artifact_files_for_existing_state_directories": len(authorized_times) * len(names),
        "required_artifact_files": len(lines),
        "required_artifact_bytes": total_bytes,
        "required_artifact_inventory_sha256": inventory_digest(lines),
        "missing_required_artifacts_for_existing_state_directories": sorted(missing),
        "entries": sorted(lines),
    }


def _state17_card15_reasons(folder: Path, target: Card15Target) -> list[str]:
    """Validate final active level2 Card15 without interpreting it as issue17."""
    try:
        fields = _fields(_inside_root(folder / "inputa", "state17 inputa"))
    except Exception as exc:
        return [f"STATE17_INPUTA:{type(exc).__name__}:{exc}"]
    return [] if fields == target.card15_fields else ["STATE17_INPUTA_NOT_LEVEL2"]


def _primary_inventory_view(scan: dict[str, Any], required: dict[str, Any],
                            compact_record_count: int) -> dict[str, Any]:
    runtime = scan["runtime_artifacts"]
    continuous = scan["continuous_state_indices"]
    return {
        "compact_record_count": compact_record_count,
        "existing_raw_state_indices": scan["existing_authorized_state_indices"],
        "continuous_raw_state_indices": continuous,
        "continuous_raw_state_count": len(continuous),
        "raw_observed_plant_advances": max(0, len(continuous) - 1),
        "noncontinuous_raw_state_indices": scan["noncontinuous_state_indices"],
        "required_artifact_files_for_existing_state_directories": required[
            "required_artifact_files_for_existing_state_directories"
        ],
        "required_artifact_files": required["required_artifact_files"],
        "required_artifact_bytes": required["required_artifact_bytes"],
        "required_artifact_inventory_sha256": required["required_artifact_inventory_sha256"],
        "missing_required_artifacts_for_existing_state_directories": required[
            "missing_required_artifacts_for_existing_state_directories"
        ],
        "runtime_failure_diagnostic_directories": runtime["directories"],
        "runtime_failure_diagnostic_files": runtime["files"],
        "runtime_failure_diagnostic_bytes": runtime["bytes"],
        "runtime_failure_diagnostic_inventory_sha256": runtime["sha256"],
        "unexpected_rollout_directories": scan["unexpected_directories"],
        "state18_directory_present": scan["forbidden_1118_present"],
    }


def _parse_raw_states(folders: Sequence[Path], cfg: TSCConfig, stage: dict[str, Any]) -> tuple[
    list[dict[str, Any]], list[str], int, list[str]
]:
    states: list[dict[str, Any]] = []
    inventory: list[str] = []
    artifact_bytes = 0
    parse_errors: list[str] = []
    names = tuple(stage["semantic_artifacts"]) + tuple(stage["diagnostic_artifacts"])
    for index, folder in enumerate(folders):
        try:
            state = _state(folder, cfg)
            state["actual_current_decimal_a_tsc"] = state["current_decimal_a_tsc"]
            state["actual_current_a_tsc"] = list(state["current_a_tsc"])
            state["wire_current_a"] = list(state["wire_a"])
            state["artifact_sha256"] = {}
            state["artifact_size_bytes"] = {}
            for name in names:
                path = folder / name
                size = path.stat().st_size
                digest = sha256(path)
                artifact_bytes += size
                relative = path.relative_to(folder.parents[2]).as_posix()
                inventory.append(f"{relative}\t{size}\t{digest}")
                state["artifact_sha256"][name] = digest
                state["artifact_size_bytes"][name] = size
            if state["time_ms"] != 1100 + index:
                parse_errors.append(f"TIME:{index}")
            states.append(state)
        except Exception as exc:
            parse_errors.append(f"RAW_STATE:{index}:{type(exc).__name__}:{exc}")
            break
    return states, inventory, artifact_bytes, parse_errors


def _compare_primary_state(raw: dict[str, Any], compact: dict[str, Any], index: int,
                           inputa_was_rewritten: bool, failures: list[str]) -> None:
    scalar_keys = ("time_ms", "r_geo_m", "z_geo_m", "r_mid_m", "r_inner_m", "r_outer_m", "ip_a")
    if any(raw[key] != compact.get(key) for key in scalar_keys):
        failures.append(f"PRIMARY_STATE:{index}")
    if tuple(str(value) for value in raw["actual_current_decimal_a_tsc"]) != tuple(
            str(value) for value in compact.get("actual_current_decimal_a_tsc", ())):
        failures.append(f"PRIMARY_COIL:{index}")
    if tuple(raw["wire_current_a"]) != tuple(compact.get("wire_current_a", ())):
        failures.append(f"PRIMARY_WIRE:{index}")
    comparable = tuple(name for name in raw["artifact_sha256"]
                       if not (inputa_was_rewritten and name == "inputa"))
    if any(raw["artifact_sha256"][name] != compact.get("artifact_sha256", {}).get(name)
           for name in comparable):
        failures.append(f"PRIMARY_ARTIFACT_HASH:{index}")
    if any(raw["artifact_size_bytes"][name] != compact.get("artifact_size_bytes", {}).get(name)
           for name in comparable):
        failures.append(f"PRIMARY_ARTIFACT_SIZE:{index}")
    reported_returncode = compact.get("reported_returncode")
    reported_abnormal = compact.get("reported_abnormal")
    if not isinstance(reported_returncode, int) or isinstance(reported_returncode, bool):
        failures.append(f"PRIMARY_REPORTED_RETURNCODE:{index}")
    if reported_abnormal is not raw["abnormal"]:
        failures.append(f"PRIMARY_REPORTED_ABNORMAL:{index}")
    if compact.get("reported_runtime_ok") is not (
            reported_returncode == 0 and reported_abnormal is False):
        failures.append(f"PRIMARY_REPORTED_RUNTIME_OK:{index}")
    if not isinstance(compact.get("reported_done_reason"), str):
        failures.append(f"PRIMARY_DONE_REASON_TYPE:{index}")


def _prefix_metrics(states: Sequence[dict[str, Any]], reference: dict[str, Any],
                    stage: dict[str, Any]) -> tuple[dict[str, float], list[str]]:
    tolerance = stage["prefix_match_tolerance"]
    maxima = {"geometry_m": 0.0, "ip_a": 0.0, "coil_a": 0.0, "wire_a": 0.0}
    reasons: list[str] = []
    semantic = tuple(stage["semantic_artifacts"])
    last = min(len(states), 17)
    for index in range(last):
        raw, frozen = states[index], reference["states"][index]
        geometry = max(abs(float(raw[key]) - float(frozen[key])) for key in
                       ("r_geo_m", "z_geo_m", "r_mid_m", "r_inner_m", "r_outer_m"))
        ip = abs(float(raw["ip_a"]) - float(frozen["ip_a"]))
        coil = _max_difference(raw["actual_current_a_tsc"], frozen["actual_current_a_tsc"])
        wire = _max_difference(raw["wire_current_a"], frozen["wire_current_a"])
        maxima["geometry_m"] = max(maxima["geometry_m"], geometry)
        maxima["ip_a"] = max(maxima["ip_a"], ip)
        maxima["coil_a"] = max(maxima["coil_a"], coil)
        maxima["wire_a"] = max(maxima["wire_a"], wire)
        if geometry > tolerance["geometry_m"]:
            reasons.append(f"KNOWN_PREFIX_GEOMETRY:{index}")
        if ip > tolerance["ip_a"]:
            reasons.append(f"KNOWN_PREFIX_IP:{index}")
        if coil > tolerance["coil_a"]:
            reasons.append(f"KNOWN_PREFIX_COIL:{index}")
        if wire > tolerance["wire_a"]:
            reasons.append(f"KNOWN_PREFIX_WIRE:{index}")
        # Raw inputa was rewritten when its outgoing issue was attempted.  It
        # therefore cannot be compared to the in-memory pre-issue A3 record;
        # its Card15 action is reconstructed separately below.
        comparable = tuple(name for name in semantic if name != "inputa")
        if any(raw["artifact_sha256"].get(name) != frozen["artifact_sha256"].get(name)
               for name in comparable):
            reasons.append(f"KNOWN_PREFIX_SEMANTIC_ARTIFACT:{index}")
    return maxima, reasons


def _state_safety(states: Sequence[dict[str, Any]], cfg: TSCConfig,
                  stage: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    reasons: list[str] = []
    if not states:
        return reasons, {}
    source = states[0]
    outer_ip = stage["outer_ip_fraction"] * abs(source["ip_a"])
    inner_ip = stage["inner_ip_fraction"] * abs(source["ip_a"])
    for index, state in enumerate(states):
        if not all(math.isfinite(float(state[key])) for key in ("r_geo_m", "z_geo_m", "ip_a")):
            reasons.append(f"NONFINITE_STATE:{index}")
        if not state["r_inner_m"] <= state["r_geo_m"] <= state["r_outer_m"]:
            reasons.append(f"LIMITER:{index}")
        if any(not low <= value <= high for value, low, high in zip(
                state["current_a_tsc"], cfg.min_current_a_tsc, cfg.max_current_a_tsc)):
            reasons.append(f"ABSOLUTE_CURRENT:{index}")
        if abs(state["r_geo_m"] - source["r_geo_m"]) > stage["outer_r_radius_m"]:
            reasons.append(f"OUTER_R:{index}")
        if abs(state["z_geo_m"] - source["z_geo_m"]) > stage["outer_z_radius_m"]:
            reasons.append(f"OUTER_Z:{index}")
        if source["ip_a"] * state["ip_a"] <= 0 or abs(state["ip_a"] - source["ip_a"]) > outer_ip:
            reasons.append(f"OUTER_IP:{index}")
    state16 = states[16] if len(states) > 16 else None
    clearance = None
    if state16 is not None:
        drift_r = abs(state16["r_geo_m"] - source["r_geo_m"])
        drift_z = abs(state16["z_geo_m"] - source["z_geo_m"])
        drift_ip = abs(state16["ip_a"] - source["ip_a"])
        clearance = {
            "inner_envelope_passed": drift_r <= stage["inner_r_radius_m"]
            and drift_z <= stage["inner_z_radius_m"]
            and source["ip_a"] * state16["ip_a"] > 0 and drift_ip <= inner_ip,
            "remaining_outer_r_m": stage["outer_r_radius_m"] - drift_r,
            "remaining_outer_z_m": stage["outer_z_radius_m"] - drift_z,
            "remaining_outer_ip_a": outer_ip - drift_ip,
        }
        clearance["passed"] = bool(
            clearance["inner_envelope_passed"]
            and clearance["remaining_outer_r_m"] >= stage["preissue16_outer_clearance"]["r_geo_m"]
            and clearance["remaining_outer_z_m"] >= stage["preissue16_outer_clearance"]["z_geo_m"]
            and clearance["remaining_outer_ip_a"] >= stage["preissue16_outer_clearance"]["ip_a"])
    acceptance = None
    if len(states) == 18:
        state17 = states[17]
        dr = abs(state17["r_geo_m"] - state16["r_geo_m"])
        dz = abs(state17["z_geo_m"] - state16["z_geo_m"])
        dip = abs(state17["ip_a"] - state16["ip_a"])
        source_dr = abs(state17["r_geo_m"] - source["r_geo_m"])
        source_dz = abs(state17["z_geo_m"] - source["z_geo_m"])
        source_dip = abs(state17["ip_a"] - source["ip_a"])
        threshold = stage["empirical_successor_acceptance"]
        acceptance = {
            "delta_r_geo_m": dr,
            "delta_z_geo_m": dz,
            "delta_ip_a": dip,
            "state17_inner_envelope_passed": source_dr <= stage["inner_r_radius_m"]
            and source_dz <= stage["inner_z_radius_m"]
            and source["ip_a"] * state17["ip_a"] > 0 and source_dip <= inner_ip,
        }
        acceptance["passed"] = bool(
            acceptance["state17_inner_envelope_passed"]
            and dr <= threshold["r_geo_m"] and dz <= threshold["z_geo_m"]
            and dip <= threshold["ip_a"])
    return reasons, {"preissue16_clearance": clearance, "state17_acceptance": acceptance}


def _expected_route(stage: dict[str, Any], categories: Sequence[str]) -> str:
    routes = stage["routes"]
    if "raw_reporting" in categories:
        return routes["raw_reporting_fail"]
    if "hard_safety" in categories:
        return routes["hard_safety_fail"]
    if "known_prefix" in categories:
        return routes["known_prefix_fail"]
    if "clearance" in categories:
        return routes["clearance_fail"]
    if "novel_execution" in categories:
        return routes["novel_execution_fail"]
    if "acceptance" in categories:
        return routes["acceptance_fail"]
    return routes["observed"]


def audit(stage_path: Path, run_dir: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    stage_path = _inside_root(stage_path, "stage config")
    run_dir = _inside_root(run_dir, "run directory")
    stage, cfg = _load_stage(stage_path)
    records = _authenticate_evidence(stage, failures)
    reference = _reference_pair(records, stage, failures)
    primary_path = _inside_root(run_dir / "result.json", "primary result")
    compact_path = _inside_root(run_dir / "exploration.json", "primary compact")
    offline_path = _inside_root(run_dir / "offline_preflight.json", "offline preflight")
    if not primary_path.is_file():
        failures.append("PRIMARY_RESULT_MISSING")
        primary: dict[str, Any] = {}
    else:
        primary = json.loads(primary_path.read_text(encoding="utf-8"))
    if not compact_path.is_file():
        failures.append("PRIMARY_COMPACT_MISSING")
        compact: dict[str, Any] = {}
    else:
        compact = json.loads(compact_path.read_text(encoding="utf-8"))
    if not offline_path.is_file():
        failures.append("OFFLINE_PREFLIGHT_MISSING")
        offline: dict[str, Any] = {}
    else:
        offline = json.loads(offline_path.read_text(encoding="utf-8"))

    rollouts_root = _inside_root(run_dir / "rollouts", "rollouts root")
    rollout_entries = sorted(
        _inside_root(path, "rollouts child").name for path in rollouts_root.iterdir()
    ) if rollouts_root.is_dir() else []
    extra_rollout_entries = [name for name in rollout_entries if name != ROLLOUT_ID]
    rollout = _inside_root(rollouts_root / ROLLOUT_ID, "E1 rollout")
    scan = _scan_raw_directories(rollout, run_dir)
    folders = scan["authorized_continuous_folders"]
    states, _, _, raw_parse_errors = _parse_raw_states(folders, cfg, stage)
    required_inventory = _required_raw_inventory(scan, run_dir, stage)

    for name, record in (("PRIMARY", primary), ("COMPACT", compact)):
        if record:
            if record.get("source_revision") != source_revision:
                failures.append(f"{name}_SOURCE_REVISION")
            if record.get("schema_version") != SCHEMA:
                failures.append(f"{name}_SCHEMA")
    if compact.get("stage_config_path") != STAGE_RELATIVE_PATH:
        failures.append("COMPACT_STAGE_PATH")
    if compact.get("stage_config_sha256") != STAGE_SHA256:
        failures.append("COMPACT_STAGE_SHA256")
    compact_states = compact.get("states", [])
    if len(compact_states) != len(states):
        failures.append("PRIMARY_STATE_COUNT")
    counters = {
        key: compact.get(key) for key in (
            "reset_calls", "advance_attempts", "verified_successful_plant_advances",
            "raw_observed_plant_advances", "plant_advance_gotsc_calls")
    }
    for key, value in counters.items():
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            failures.append(f"COUNTER:{key}")
            counters[key] = -1
    reset_calls = counters["reset_calls"]
    attempts = counters["advance_attempts"]
    successes = counters["verified_successful_plant_advances"]
    raw_observed = counters["raw_observed_plant_advances"]
    gotsc_calls = counters["plant_advance_gotsc_calls"]
    raw_reporting_reasons: list[str] = []
    if reset_calls > 1 or attempts > 17 or successes > 17 or raw_observed > 17 or gotsc_calls > 17:
        raw_reporting_reasons.append("BUDGET_EXCEEDED")
    if states and reset_calls != 1:
        raw_reporting_reasons.append("RESET_COUNT")
    if raw_observed != max(len(states) - 1, 0):
        raw_reporting_reasons.append("RAW_OBSERVED_STATE_COUNT")
    if not (successes <= raw_observed <= gotsc_calls <= attempts <= successes + 1):
        raw_reporting_reasons.append("ATTEMPT_GOTSC_RAW_VERIFIED_ORDER")

    for index, (raw, recorded) in enumerate(zip(states, compact_states)):
        _compare_primary_state(raw, recorded, index, index < max(attempts, 0), failures)

    attempted_actions = compact.get("attempted_actions", [])
    recorded_actions = compact.get("actions", [])
    if len(attempted_actions) != attempts:
        raw_reporting_reasons.append("ATTEMPTED_ACTION_COUNT")
    if len(recorded_actions) != successes:
        raw_reporting_reasons.append("VERIFIED_ACTION_COUNT")
    if [row.get("issue_step") for row in attempted_actions] != list(range(max(attempts, 0))):
        raw_reporting_reasons.append("ATTEMPT_SEQUENCE_OR_RETRY")

    actions: list[dict[str, Any]] = []
    scientific_reasons: list[str] = []
    categories: list[str] = []
    effect_delay_checks: list[dict[str, Any]] = []
    level2_dwell_ages: list[int] = []
    if reference is not None:
        targets = _targets(stage, reference, cfg)
        if offline:
            _audit_offline_binding(
                offline, stage, source_revision, targets, reference, cfg, failures)
        previous_command = tuple(Decimal(str(value)) for value in
                                 reference["states"][0]["active_command_decimal_a_tsc"])
        for step in range(max(attempts, 0)):
            target = targets[step]
            try:
                fields = _fields(rollout / f"{1100 + step}ms" / "inputa")
                if fields != target.card15_fields:
                    scientific_reasons.append(f"CARD15:{step}")
                    categories.append("novel_execution" if step == 16 else "known_prefix")
                exact = card15_target_decimal_a(target, cfg.turns_tsc,
                                                name=f"e1.independent.issue.{step}")
                issued = assert_exact_slew(previous_command, exact,
                                           name=f"e1.independent.issue.{step}")
                attempted = _expected_action(target, step, issued)
                if step >= len(attempted_actions) or attempted_actions[step] != attempted:
                    failures.append(f"PRIMARY_ATTEMPTED_ACTION:{step}")
                previous_command = exact
            except Exception as exc:
                failures.append(f"ACTION_PARSE:{step}:{type(exc).__name__}:{exc}")
                break
        for step in range(max(raw_observed, 0)):
            target = targets[step]
            effect_delay_checks.append({
                "issue_step": step,
                "issue_time_ms": 1100 + step,
                "effect_state_index": step + 1,
                "effect_time_ms": states[step + 1]["time_ms"],
                "effect_delay_steps": 1,
                "passed": states[step + 1]["time_ms"] == 1101 + step,
            })
            if step >= 2:
                level2_dwell_ages.append(step - 1)
            if states[step + 1]["time_ms"] != 1101 + step:
                raw_reporting_reasons.append(f"EFFECT_CLOCK:{step}")
        for step in range(max(successes, 0)):
            target = targets[step]
            try:
                action = _expected_action(
                    target, step, assert_exact_slew(
                        tuple(Decimal(str(value)) for value in
                              reference["states"][0]["active_command_decimal_a_tsc"])
                        if step == 0 else card15_target_decimal_a(
                            targets[step - 1], cfg.turns_tsc, name=f"e1.independent.previous.{step}"),
                        card15_target_decimal_a(target, cfg.turns_tsc,
                                               name=f"e1.independent.target.{step}"),
                        name=f"e1.independent.reconstruct.{step}"))
                actions.append(action)
            except Exception as exc:
                failures.append(f"ACTION_RECONSTRUCTION:{step}:{type(exc).__name__}:{exc}")
                break
            try:
                assert_exact_slew(
                    states[step]["actual_current_decimal_a_tsc"],
                    states[step + 1]["actual_current_decimal_a_tsc"],
                    name=f"e1.independent.readback.{step}")
            except Exception as exc:
                scientific_reasons.append(f"OBSERVED_SLEW:{step}:{type(exc).__name__}:{exc}")
                categories.append("novel_execution" if step == 16 else "known_prefix")
        if actions != recorded_actions:
            failures.append("PRIMARY_VERIFIED_ACTIONS")
        if len(states) > 17:
            state17_reasons = _state17_card15_reasons(folders[17], targets[16])
            scientific_reasons.extend(state17_reasons)
            if state17_reasons:
                categories.append("novel_execution")
        else:
            state17_reasons = []
    else:
        targets = ()
        state17_reasons = []
    expected_dwell_ages = list(range(1, max(1, raw_observed - 1))) \
        if raw_observed >= 3 else []
    if level2_dwell_ages != expected_dwell_ages:
        failures.append("LEVEL2_DWELL_EFFECT_AGE_SEQUENCE")
    if any(row["effect_delay_steps"] != 1 or not row["passed"]
           for row in effect_delay_checks):
        raw_reporting_reasons.append("EFFECT_DELAY_NOT_ONE")

    if reference is not None:
        qualified_prefix = states[:min(max(successes, 0) + 1, 17)]
        prefix_maxima, prefix_reasons = _prefix_metrics(qualified_prefix, reference, stage)
        for index in range(min(len(qualified_prefix), len(compact_states), 17)):
            recorded = compact_states[index]
            frozen = reference["states"][index]
            if (recorded.get("active_command_card15_fields")
                    != frozen.get("active_command_card15_fields")):
                prefix_reasons.append(f"KNOWN_PREFIX_ACTIVE_CARD15:{index}")
            if tuple(recorded.get("active_command_decimal_a_tsc", ())) != tuple(
                    frozen.get("active_command_decimal_a_tsc", ())):
                prefix_reasons.append(f"KNOWN_PREFIX_ACTIVE_DECIMAL:{index}")
            if recorded.get("artifact_sha256", {}).get("inputa") != frozen.get(
                    "artifact_sha256", {}).get("inputa"):
                prefix_reasons.append(f"KNOWN_PREFIX_PREISSUE_INPUTA:{index}")
        scientific_reasons.extend(prefix_reasons)
        if prefix_reasons:
            categories.append("known_prefix")
    else:
        prefix_maxima = {}
    qualified_states = states[:max(successes, 0) + 1]
    hard_reasons, metrics = _state_safety(qualified_states, cfg, stage)
    scientific_reasons.extend(hard_reasons)
    if hard_reasons:
        categories.append("hard_safety")
    clearance = metrics.get("preissue16_clearance")
    acceptance = metrics.get("state17_acceptance")
    if (
        len(qualified_states) == 17
        and attempts == 16
        and clearance is not None
        and not clearance["passed"]
        and "known_prefix" not in categories
        and "hard_safety" not in categories
    ):
        categories.append("clearance")
    abnormal_indices = [index for index, state in enumerate(states) if state["abnormal"]]
    if abnormal_indices:
        failed_issue = abnormal_indices[-1] - 1
        scientific_reasons.append(f"RAW_OUTPUTA_ABNORMAL:{abnormal_indices[-1]}")
        categories.append("novel_execution" if failed_issue == 16 else "known_prefix")
    if attempts > raw_observed:
        scientific_reasons.append(f"ATTEMPT_WITHOUT_PARSEABLE_SUCCESSOR:{attempts - 1}")
        categories.append("novel_execution" if attempts == 17 else "known_prefix")
    elif raw_observed > successes and not abnormal_indices:
        scientific_reasons.append(f"UNQUALIFIED_REPORTED_SUCCESSOR:{raw_observed}")
        categories.append("novel_execution" if attempts == 17 else "known_prefix")
    if raw_parse_errors:
        scientific_reasons.extend(raw_parse_errors)
        categories.append("novel_execution" if attempts >= 17 else "known_prefix")
    if (
        successes == 17
        and not hard_reasons
        and acceptance is not None
        and not acceptance["passed"]
        and "novel_execution" not in categories
        and "known_prefix" not in categories
    ):
        categories.append("acceptance")
    if raw_observed < 17 and not categories:
        # Any unexplained stop before the sole unknown successor belongs to
        # the known-prefix execution layer (or the novel layer if issue16 was
        # attempted).  Runtime text is not trusted as raw scientific evidence.
        categories.append("novel_execution" if attempts >= 17 else "known_prefix")
    if (extra_rollout_entries or scan["unexpected_directories"]
            or scan["forbidden_1118_present"]
            or scan["noncontinuous_state_indices"]
            or required_inventory["missing_required_artifacts_for_existing_state_directories"]
            or len(compact_states) != len(scan["continuous_state_indices"])
            or raw_observed != max(0, len(scan["continuous_state_indices"]) - 1)):
        raw_reporting_reasons.append("RAW_DIRECTORY_OR_INVENTORY_INTEGRITY")
    if raw_reporting_reasons:
        categories.append("raw_reporting")
    primary_categories = compact.get("reason_categories", [])
    allowed_categories = {"known_prefix", "clearance", "novel_execution", "hard_safety",
                          "acceptance", "raw_reporting"}
    if not isinstance(primary_categories, list) or any(
            category not in allowed_categories for category in primary_categories):
        failures.append("PRIMARY_REASON_CATEGORY_DOMAIN")
        primary_categories = []
    if any(category not in primary_categories for category in set(categories)):
        failures.append("PRIMARY_REASON_CATEGORIES")
    expected_route = _expected_route(stage, primary_categories)
    if compact.get("route") != expected_route or primary.get("route") != expected_route:
        failures.append("PRIMARY_ROUTE")
    expected_scientific_pass = expected_route == stage["routes"]["observed"]
    if (compact.get("passed") is not expected_scientific_pass
            or primary.get("passed") is not expected_scientific_pass):
        failures.append("PRIMARY_SCIENTIFIC_VERDICT")
    if primary.get("reason_categories") != compact.get("reason_categories"):
        failures.append("PRIMARY_RESULT_CATEGORIES")
    if primary.get("reasons") != compact.get("reasons"):
        failures.append("PRIMARY_RESULT_REASONS")
    compact_reasons = compact.get("reasons", [])
    if (not isinstance(compact_reasons, list)
            or any(not isinstance(reason, str) or not reason for reason in compact_reasons)
            or compact_reasons != _deduplicate(compact_reasons)):
        failures.append("PRIMARY_REASON_LIST_INTEGRITY")

    for key, value in counters.items():
        if primary.get(key) != value:
            failures.append(f"PRIMARY_COUNTER:{key}")
    cross_keys = ("unknown_successor_attempted", "unknown_successor_observed",
                "state17_recorded", "unconditional_stop_after_state17",
                "issue17_attempted", "state18_observed", "retry_attempted", "identity_consumed",
                "raw_preservation_verified", "partial_failure_raw_preserved_and_reported",
                "failure_raw_preserved_and_reported")
    for key in cross_keys:
        if primary.get(key) != compact.get(key):
            failures.append(f"PRIMARY_STOP_FIELD:{key}")
    if primary.get("plant_advances") != successes or compact.get("plant_advances") != successes:
        failures.append("PRIMARY_PLANT_ADVANCE_ALIAS")
    if primary.get("execution_completed") is not (successes == 17):
        failures.append("PRIMARY_EXECUTION_COMPLETED")
    if primary.get("state16_clearance") != compact.get("state16_clearance"):
        failures.append("PRIMARY_STATE16_CLEARANCE")
    if primary.get("successor_acceptance") != compact.get("successor_acceptance"):
        failures.append("PRIMARY_SUCCESSOR_ACCEPTANCE")
    observed_state17 = len(states) == 18 and states[-1]["time_ms"] == 1117
    if compact.get("unknown_successor_attempted") is not (attempts == 17):
        failures.append("UNKNOWN_SUCCESSOR_ATTEMPT_FLAG")
    if compact.get("unknown_successor_observed") is not observed_state17:
        failures.append("UNKNOWN_SUCCESSOR_OBSERVED_FLAG")
    if compact.get("state17_recorded") is not observed_state17:
        failures.append("STATE17_RECORDED_FLAG")
    if compact.get("unconditional_stop_after_state17") is not (
            observed_state17 and attempts == 17):
        failures.append("UNCONDITIONAL_STOP_FLAG")
    if compact.get("issue17_attempted") is not (attempts > 17):
        failures.append("ISSUE17_ATTEMPTED")
    if compact.get("retry_attempted") is not False:
        failures.append("RETRY_ATTEMPTED")
    if compact.get("identity_consumed") is not (attempts > 0):
        failures.append("IDENTITY_CONSUMED_FLAG")
    compact_state18_observed = any(
        isinstance(state, dict) and int(state.get("time_ms", -1)) >= 1118
        for state in compact_states
    )
    if compact.get("state18_observed") is not compact_state18_observed:
        failures.append("STATE18_FLAG_COMPACT_DISAGREEMENT")
    if compact.get("state18_observed") is True and "raw_reporting" not in primary_categories:
        failures.append("STATE18_OBSERVED")

    inventory_view = _primary_inventory_view(scan, required_inventory, len(compact_states))
    if compact.get("raw_inventory") != inventory_view:
        failures.append("COMPACT_ARTIFACT_INVENTORY")
    if any(primary.get(key) != value for key, value in inventory_view.items()):
        failures.append("PRIMARY_ARTIFACT_INVENTORY")
    if primary.get("rollouts_completed") != (1 if compact else 0):
        failures.append("PRIMARY_ROLLOUT_COUNT")
    if compact.get("raw_reporting_integrity_failed") is not ("raw_reporting" in primary_categories):
        failures.append("PRIMARY_RAW_REPORTING_FLAG")

    independent_raw_preservation = bool(
        attempts > 0
        and len(scan["continuous_state_indices"]) > 0
        and not required_inventory["missing_required_artifacts_for_existing_state_directories"]
        and not scan["noncontinuous_state_indices"]
        and not scan["unexpected_directories"]
        and not extra_rollout_entries
        and not scan["forbidden_1118_present"]
        and len(compact_states) == len(scan["continuous_state_indices"])
    )
    if compact.get("raw_preservation_verified") is not independent_raw_preservation:
        failures.append("RAW_PRESERVATION_FLAG")
    expected_partial_preserved = bool(
        compact.get("passed") is False and len(compact_states) < 18
        and independent_raw_preservation
    )
    expected_failure_preserved = bool(
        compact.get("passed") is False and independent_raw_preservation
    )
    if compact.get("partial_failure_raw_preserved_and_reported") is not expected_partial_preserved:
        failures.append("PARTIAL_RAW_PRESERVATION_FLAG")
    if compact.get("failure_raw_preserved_and_reported") is not expected_failure_preserved:
        failures.append("FAILURE_RAW_PRESERVATION_FLAG")

    if attempts == 17 and observed_state17 and not scan["forbidden_1118_present"]:
        issue17_exclusion_proved = True
    else:
        issue17_exclusion_proved = False

    failures = _deduplicate(failures)
    audit_passed = not failures
    result = {
        "schema_version": SCHEMA + "-independent-v1",
        "source_revision": source_revision,
        "audit_passed": audit_passed,
        "route": INDEPENDENT_PASS if audit_passed else INDEPENDENT_FAIL,
        "failures": failures,
        "primary_route": primary.get("route"),
        "primary_scientific_passed": primary.get("passed"),
        "expected_primary_route": expected_route,
        "raw_rollouts": 1 if rollout.is_dir() else 0,
        "raw_states": len(states),
        "raw_observed_plant_advances": raw_observed,
        "reconstructed_verified_actions": len(actions),
        "counters": counters,
        "known_prefix_maximum_absolute_difference": prefix_maxima,
        "hard_safety_reasons": hard_reasons,
        "recomputed_scientific_reasons": _deduplicate(scientific_reasons),
        "recomputed_reason_categories": _deduplicate(categories),
        "raw_reporting_reasons": _deduplicate(raw_reporting_reasons),
        "preissue16_clearance": metrics.get("preissue16_clearance"),
        "state17_acceptance": metrics.get("state17_acceptance"),
        "state17_card15_reasons": state17_reasons,
        "state17_inputa_counted_as_issue17": False,
        "issue17_exclusion_proved_by_attempt_count_and_absent_state18": issue17_exclusion_proved,
        "effect_delay_steps_required": 1,
        "effect_delay_checks": effect_delay_checks,
        "level2_dwell_effect_ages_observed": level2_dwell_ages,
        "level2_dwell_effect_age_full_sequence_required": list(range(1, 16)),
        "raw_directory_scan": {
            "actual_times_ms": scan["actual_times_ms"],
            "actual_state_indices": scan["actual_state_indices"],
            "continuous_state_indices": scan["continuous_state_indices"],
            "noncontinuous_state_indices": scan["noncontinuous_state_indices"],
            "unexpected_directories": scan["unexpected_directories"],
            "forbidden_1118_present": scan["forbidden_1118_present"],
        },
        "runtime_failure_diagnostic_inventory": scan["runtime_artifacts"],
        "state_like_directory_inventory": scan["state_like_inventory"],
        "required_artifact_files": required_inventory["required_artifact_files"],
        "required_artifact_bytes": required_inventory["required_artifact_bytes"],
        "required_artifact_inventory_sha256": required_inventory[
            "required_artifact_inventory_sha256"
        ],
        "runtime_reconstruction_boundary": {
            "independently_reconstructed": [
                "raw state clocks and paired-boundary R_geo/Z_geo/Ip",
                "raw coil and wire readback",
                "outputa abnormal marker when outputa is retained",
                "all state-like and frozen runtime-failure diagnostic file hashes",
            ],
            "not_independently_reconstructible_from_required_raw": [
                "numeric subprocess returncode",
                "captured subprocess stdout and stderr",
                "an internal solver classification beyond retained outputa/artifacts",
                "Python exception text before a parseable expected-clock successor",
            ],
            "compact_reported_returncodes": [
                state.get("reported_returncode") for state in compact_states
            ],
            "compact_reported_done_reasons": [
                state.get("reported_done_reason") for state in compact_states
            ],
        },
        "primary_result_sha256": sha256(primary_path) if primary_path.is_file() else None,
        "offline_preflight_sha256": sha256(offline_path) if offline_path.is_file() else None,
        "claim_boundary": (
            "independent_raw_integrity_only; primary scientific acceptance or rejection retained; "
            "no tube, model, controller, hold, recovery, qualification, or expert-data claim"
        ),
    }
    write_new(run_dir / "independent_audit.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    result = audit(args.stage_config.resolve(), args.run_dir.resolve(), args.source_revision)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
