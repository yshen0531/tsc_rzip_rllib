#!/usr/bin/env python3
"""Frozen NR2R2C2aA4E1 one-successor simulator exploration."""

from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_nr1_qualification import _record, _source  # noqa: E402
from scripts.rgeo_zgeo_1ms_nr2r2c2aa1_authority import (  # noqa: E402
    target_from_fields,
    targets_for,
)
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    Card15Target,
    OneMsNR1SafetyEnvelope,
    assert_exact_slew,
    build_frozen_one_ms_prefixes,
    card15_target_decimal_a,
    validate_one_ms_config,
)
from tsc_rzip_rllib.control.rgeo_zgeo_contract import (  # noqa: E402
    ContractError,
    RGeoZGeoSignal,
)
from tsc_rzip_rllib.core.runner import TSCConfig, TSCStepRunner  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-nr2r2c2aa4e1-single-successor-exploration-v1"
OFFLINE_PASS_ROUTE = "ONE_MS_NR2R2C2AA4E1_OFFLINE_PREFLIGHT_PASS_RUN_ONLY"
ROLLOUT_ID = "single_successor_r0"


class InputIntegrityError(ValueError):
    """A frozen input, identity or evidence binding is invalid."""


class StopRollout(Exception):
    """Internal non-error control flow after a classified fail-closed stop."""


class CountingTSCStepRunner(TSCStepRunner):
    """Count actual gotsc entry calls, including a call which later raises."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.plant_advance_gotsc_calls = 0

    def _run_tsc(self) -> tuple[int, str, str]:
        self.plant_advance_gotsc_calls += 1
        return super()._run_tsc()


def _inside_root(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT.resolve()):
        raise InputIntegrityError(f"{label} leaves repository: {path}")
    return resolved


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path: Path, payload: Any) -> None:
    path = _inside_root(path, "output")
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _load_hashed(row: dict[str, Any], label: str) -> tuple[Path, Any]:
    try:
        path = _inside_root(ROOT / row["path"], label)
        expected = str(row["sha256"])
    except (KeyError, TypeError) as exc:
        raise InputIntegrityError(f"invalid hashed-input declaration: {label}") from exc
    if not path.is_file() or sha256(path) != expected:
        raise InputIntegrityError(f"{label} hash mismatch: {row.get('path')}")
    if path.suffix == ".json":
        return path, json.loads(path.read_text(encoding="utf-8"))
    return path, None


def _require_exact_stage(stage: dict[str, Any]) -> None:
    exact = {
        "schema_version": SCHEMA,
        "takeover_time_ms": 1100,
        "control_period_ms": 1,
        "horizon_steps": 17,
        "rollouts": 1,
        "maximum_reset_calls": 1,
        "maximum_plant_advances": 17,
        "maximum_advance_attempts": 17,
        "maximum_plant_advance_gotsc_calls": 17,
        "retry_after_any_advance_attempt": "forbidden",
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
    }
    for key, value in exact.items():
        if stage.get(key) != value:
            raise InputIntegrityError(f"frozen E1 field mismatch: {key}")
    exact_objects = {
        "intended_use": "simulator_only_single_unknown_successor_development_exploration",
        "model_or_expert_use": "forbidden",
        "qualification_use": "forbidden",
        "prefix_match_tolerance": {
            "geometry_m": 1e-12,
            "ip_a": 1e-9,
            "coil_a": 1e-9,
            "wire_a": 1e-9,
        },
        "empirical_successor_acceptance": {
            "r_geo_m": 0.002,
            "z_geo_m": 0.002,
            "ip_a": 100.0,
            "state17_must_remain_in_inner_envelope": True,
            "is_preaction_transition_bound": False,
        },
        "preissue16_outer_clearance": {
            "r_geo_m": 0.020,
            "z_geo_m": 0.020,
            "ip_a": 1000.0,
            "is_qualified_transition_tube": False,
        },
        "schedule": [
            {"first_step": 0, "last_step": 0, "level": "q0"},
            {"first_step": 1, "last_step": 1, "level": "level1"},
            {"first_step": 2, "last_step": 16, "level": "level2"},
        ],
        "routes": {
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
        },
    }
    for key, value in exact_objects.items():
        if stage.get(key) != value:
            raise InputIntegrityError(f"frozen E1 object mismatch: {key}")
    exact_scalars = {
        "inner_r_radius_m": 0.025,
        "inner_z_radius_m": 0.025,
        "inner_ip_fraction": 0.05,
        "outer_r_radius_m": 0.05,
        "outer_z_radius_m": 0.05,
        "outer_ip_fraction": 0.10,
    }
    for key, value in exact_scalars.items():
        if stage.get(key) != value:
            raise InputIntegrityError(f"frozen E1 envelope mismatch: {key}")
    if stage.get("observation_contract") != {
        "r_geo_z_geo_ip_exact_noiseless_before_issue": True,
        "same_state_paired_boundary_required": True,
        "invalid_or_missing_boundary_fails_closed": True,
        "complete_causal_history_since_takeover_available": True,
        "pre_takeover_history_asserted_available": False,
        "future_successor_observed_before_issue": False,
    }:
        raise InputIntegrityError("E1 observation contract mismatch")
    if stage.get("post_state17_policy") != {
        "unconditional_stop": True,
        "issue17_forbidden": True,
        "state18_forbidden": True,
        "return_or_cleanup_plant_action_forbidden": True,
    }:
        raise InputIntegrityError("E1 post-state17 policy mismatch")
    if stage.get("result_counter_contract") != {
        "record_reset_calls_separately": True,
        "record_advance_attempts_separately": True,
        "record_verified_successful_plant_advances_separately": True,
        "partial_failure_raw_must_be_preserved_and_reported": True,
    }:
        raise InputIntegrityError("E1 result-counter contract mismatch")
    if stage.get("semantic_artifacts") != [
        "inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv"
    ] or stage.get("diagnostic_artifacts") != ["sprsina"]:
        raise InputIntegrityError("E1 artifact contract mismatch")


def _replays_equal(
    left: dict[str, Any], right: dict[str, Any], stage: dict[str, Any]
) -> tuple[bool, bool]:
    if (
        left.get("passed") is not True
        or right.get("passed") is not True
        or left.get("plant_advances") != 32
        or right.get("plant_advances") != 32
        or len(left.get("states", ())) != 33
        or len(right.get("states", ())) != 33
        or len(left.get("actions", ())) != 32
        or len(right.get("actions", ())) != 32
    ):
        return False, False
    tolerances = stage["prefix_match_tolerance"]
    semantic = stage["semantic_artifacts"]
    sprsina_differs = False
    for index in range(17):
        a, b = left["states"][index], right["states"][index]
        if (
            len(a.get("actual_current_decimal_a_tsc", ())) != 14
            or len(b.get("actual_current_decimal_a_tsc", ())) != 14
        ):
            return False, False
        if (
            len(a.get("wire_current_a", ())) != 48
            or len(b.get("wire_current_a", ())) != 48
        ):
            return False, False
        if a["time_ms"] != 1100 + index or b["time_ms"] != 1100 + index:
            return False, False
        if max(abs(float(a[key]) - float(b[key])) for key in ("r_geo_m", "z_geo_m", "r_mid_m")) > tolerances["geometry_m"]:
            return False, False
        if abs(float(a["ip_a"]) - float(b["ip_a"])) > tolerances["ip_a"]:
            return False, False
        if max(abs(Decimal(x) - Decimal(y)) for x, y in zip(
            a["actual_current_decimal_a_tsc"], b["actual_current_decimal_a_tsc"]
        )) > Decimal(str(tolerances["coil_a"])):
            return False, False
        if max(abs(float(x) - float(y)) for x, y in zip(
            a["wire_current_a"], b["wire_current_a"]
        )) > tolerances["wire_a"]:
            return False, False
        if any(a["artifact_sha256"][name] != b["artifact_sha256"][name] for name in semantic):
            return False, False
        sprsina_differs = sprsina_differs or (
            a["artifact_sha256"]["sprsina"] != b["artifact_sha256"]["sprsina"]
        )
    for issue in range(16):
        if left["actions"][issue] != right["actions"][issue]:
            return False, sprsina_differs
    return True, sprsina_differs


def load(stage_path: Path) -> tuple[dict[str, Any], TSCConfig, dict[str, Any]]:
    stage_path = _inside_root(stage_path, "stage config")
    if not stage_path.is_file():
        raise InputIntegrityError("E1 stage config is missing")
    stage = json.loads(stage_path.read_text(encoding="utf-8"))
    _require_exact_stage(stage)

    _, _ = _load_hashed(stage["design"], "E1 design")
    base_path, _ = _load_hashed(stage["base_tsc_config"], "base TSC config")
    evidence: dict[str, Any] = {}
    for key, row in stage["evidence"].items():
        _, evidence[key] = _load_hashed(row, key)

    primary = evidence["a3_primary"]
    independent = evidence["a3_independent"]
    support = evidence["a4_support_result"]
    if (
        primary.get("route") != stage["evidence"]["a3_primary"]["expected_route"]
        or primary.get("passed") is not True
        or primary.get("execution_passed") is not True
        or primary.get("repeatability_passed") is not True
        or primary.get("plant_advances") != 64
    ):
        raise InputIntegrityError("A3 primary premise mismatch")
    if (
        independent.get("route") != stage["evidence"]["a3_independent"]["expected_route"]
        or independent.get("audit_passed") is not True
        or independent.get("primary_result_sha256")
        != stage["evidence"]["a3_primary"]["sha256"]
        or independent.get("plant_advances") != 64
    ):
        raise InputIntegrityError("A3 independent premise mismatch")
    for key in (
        "required_artifact_files",
        "required_artifact_bytes",
        "required_artifact_inventory_sha256",
    ):
        if primary.get(key) != independent.get(key):
            raise InputIntegrityError(f"A3 inventory binding mismatch: {key}")
    support_row = stage["evidence"]["a4_support_result"]
    if (
        support.get("route") != support_row["expected_route"]
        or support.get("support_passed") is not False
        or support.get("supported_transitions") != support_row["expected_supported_transitions"]
        or support.get("required_transitions") != support_row["expected_required_transitions"]
        or support.get("first_unsupported", {}).get("issue_step")
        != support_row["expected_first_unsupported_issue_step"]
        or support.get("first_unsupported", {}).get("effect_state_index")
        != support_row["expected_first_unsupported_effect_state_index"]
        or support.get("first_unsupported", {}).get("level2_dwell_effect_age")
        != support_row["expected_first_unsupported_level2_effect_age"]
    ):
        raise InputIntegrityError("A4 support-result premise mismatch")

    replay0, replay1 = evidence["a3_replay_0"], evidence["a3_replay_1"]
    equal, sprsina_differs = _replays_equal(replay0, replay1, stage)
    if not equal:
        raise InputIntegrityError("A3 checked prefix replay pair mismatch")
    if not sprsina_differs:
        raise InputIntegrityError("A3 sprsina diagnostic premise mismatch")

    cfg = TSCConfig.from_json(base_path)
    validate_one_ms_config(
        start_folder=cfg.start_folder,
        dt_ms=cfg.dt_ms,
        slew_a_per_ms=cfg.current_slew_a_per_ms,
    )
    return stage, cfg, evidence


def _targets(
    stage: dict[str, Any], cfg: TSCConfig, source: dict[str, Any]
) -> tuple[Card15Target, ...]:
    frozen = build_frozen_one_ms_prefixes(
        source_current_a_tsc=source["currents_a_tsc"],
        turns_tsc=cfg.turns_tsc,
        min_current_a_tsc=cfg.min_current_a_tsc,
        max_current_a_tsc=cfg.max_current_a_tsc,
    )
    level1 = target_from_fields(stage["level1_card15_fields"], cfg, "c2aa4e1.level1")
    level2 = target_from_fields(stage["level2_card15_fields"], cfg, "c2aa4e1.level2")
    targets = targets_for(stage, frozen.q0, level1, level2)
    if targets[15].card15_fields != targets[16].card15_fields:
        raise InputIntegrityError("issue16 is not an exact repeated level2 target")
    level2_15 = card15_target_decimal_a(targets[15], cfg.turns_tsc, name="e1.level2.15")
    level2_16 = card15_target_decimal_a(targets[16], cfg.turns_tsc, name="e1.level2.16")
    if level2_15 != level2_16:
        raise InputIntegrityError("issue16 requested change is not exactly zero")
    return targets


def _target_action(target: Card15Target, issue: int, maximum: float) -> dict[str, Any]:
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


def _action_matches_reference(action: dict[str, Any], reference: dict[str, Any]) -> bool:
    return (
        action["issue_step"] == reference["issue_step"]
        and action["issue_time_ms"] == reference["issue_time_ms"]
        and action["effect_state_index"] == reference["effect_state_index"]
        and action["effect_age_steps"] == reference["effect_age_steps"]
        and action["expected_card15_fields"] == reference["expected_card15_fields"]
        and action["target_current_a_tsc"] == reference["target_current_a_tsc"]
        and action["maximum_issued_delta_a"] == reference["maximum_issued_delta_a"]
    )


def prefix_mismatch_reasons(
    states: Sequence[dict[str, Any]],
    actions: Sequence[dict[str, Any]],
    reference: dict[str, Any],
    stage: dict[str, Any],
    issue: int,
) -> list[str]:
    """Compare the complete checked live prefix before issuing ``issue``."""
    reasons: list[str] = []
    if len(states) != issue + 1 or len(actions) != issue:
        return [f"PREFIX_SHAPE:{issue}"]
    tolerance = stage["prefix_match_tolerance"]
    semantic = stage["semantic_artifacts"]
    for index, state in enumerate(states):
        expected = reference["states"][index]
        if (
            len(state.get("actual_current_decimal_a_tsc", ())) != 14
            or len(expected.get("actual_current_decimal_a_tsc", ())) != 14
        ):
            reasons.append(f"PREFIX_COIL_LENGTH:{index}")
        if (
            len(state.get("wire_current_a", ())) != 48
            or len(expected.get("wire_current_a", ())) != 48
        ):
            reasons.append(f"PREFIX_WIRE_LENGTH:{index}")
        if state["time_ms"] != expected["time_ms"]:
            reasons.append(f"PREFIX_TIME:{index}")
        if max(abs(float(state[key]) - float(expected[key])) for key in (
            "r_geo_m", "z_geo_m", "r_mid_m"
        )) > tolerance["geometry_m"]:
            reasons.append(f"PREFIX_GEOMETRY:{index}")
        if abs(float(state["ip_a"]) - float(expected["ip_a"])) > tolerance["ip_a"]:
            reasons.append(f"PREFIX_IP:{index}")
        if (
            len(state.get("actual_current_decimal_a_tsc", ())) == 14
            and len(expected.get("actual_current_decimal_a_tsc", ())) == 14
            and max(abs(Decimal(x) - Decimal(y)) for x, y in zip(
                state["actual_current_decimal_a_tsc"],
                expected["actual_current_decimal_a_tsc"],
            )) > Decimal(str(tolerance["coil_a"]))
        ):
            reasons.append(f"PREFIX_COIL:{index}")
        if (
            len(state.get("wire_current_a", ())) == 48
            and len(expected.get("wire_current_a", ())) == 48
            and max(abs(float(x) - float(y)) for x, y in zip(
                state["wire_current_a"], expected["wire_current_a"]
            )) > tolerance["wire_a"]
        ):
            reasons.append(f"PREFIX_WIRE:{index}")
        if any(
            state["artifact_sha256"][name] != expected["artifact_sha256"][name]
            for name in semantic
        ):
            reasons.append(f"PREFIX_SEMANTIC_ARTIFACT:{index}")
    for index, action in enumerate(actions):
        if not _action_matches_reference(action, reference["actions"][index]):
            reasons.append(f"PREFIX_ACTION:{index}")
    return list(dict.fromkeys(reasons))


def _record_with_sizes(
    cfg: TSCConfig, state: dict[str, Any], stage: dict[str, Any]
) -> dict[str, Any]:
    # Preserve a parseable abnormal/nonzero successor as diagnostic compact
    # evidence without qualifying it as a control observation.
    parse_state = state
    if bool(state.get("abnormal", False)):
        parse_state = dict(state)
        parse_state["abnormal"] = False
    record = _record(cfg, parse_state)
    folder = Path(state["folder"])
    names = tuple(stage["semantic_artifacts"]) + tuple(stage["diagnostic_artifacts"])
    record["artifact_size_bytes"] = {name: (folder / name).stat().st_size for name in names}
    record["reported_returncode"] = int(state.get("returncode", 0))
    record["reported_abnormal"] = bool(state.get("abnormal", False))
    record["reported_done_reason"] = str(state.get("done_reason", ""))
    record["reported_runtime_ok"] = (
        record["reported_returncode"] == 0 and not record["reported_abnormal"]
    )
    return record


def _source_offset(source: RGeoZGeoSignal, current: RGeoZGeoSignal) -> dict[str, float]:
    return {
        "r_geo_m": abs(current.boundary.r_geo_m - source.boundary.r_geo_m),
        "z_geo_m": abs(current.boundary.z_geo_m - source.boundary.z_geo_m),
        "ip_a": abs(current.ip_a - source.ip_a),
    }


def _outer_reasons(
    stage: dict[str, Any], source: RGeoZGeoSignal, current: RGeoZGeoSignal
) -> list[str]:
    offset = _source_offset(source, current)
    reasons: list[str] = []
    if offset["r_geo_m"] > stage["outer_r_radius_m"]:
        reasons.append("OUTER_R")
    if offset["z_geo_m"] > stage["outer_z_radius_m"]:
        reasons.append("OUTER_Z")
    if source.ip_a * current.ip_a <= 0 or offset["ip_a"] > stage["outer_ip_fraction"] * abs(source.ip_a):
        reasons.append("OUTER_IP")
    return reasons


def _state16_clearance_reasons(
    stage: dict[str, Any], source: RGeoZGeoSignal, current: RGeoZGeoSignal
) -> tuple[list[str], dict[str, Any]]:
    offset = _source_offset(source, current)
    inner = {
        "r_geo_m": stage["inner_r_radius_m"] - offset["r_geo_m"],
        "z_geo_m": stage["inner_z_radius_m"] - offset["z_geo_m"],
        "ip_a": stage["inner_ip_fraction"] * abs(source.ip_a) - offset["ip_a"],
    }
    outer = {
        "r_geo_m": stage["outer_r_radius_m"] - offset["r_geo_m"],
        "z_geo_m": stage["outer_z_radius_m"] - offset["z_geo_m"],
        "ip_a": stage["outer_ip_fraction"] * abs(source.ip_a) - offset["ip_a"],
    }
    required = stage["preissue16_outer_clearance"]
    reasons = []
    for key in ("r_geo_m", "z_geo_m", "ip_a"):
        if inner[key] < 0.0:
            reasons.append(f"STATE16_INNER_{key.upper()}")
        if outer[key] < required[key]:
            reasons.append(f"STATE16_CLEARANCE_{key.upper()}")
    return reasons, {
        "source_offset": offset,
        "remaining_to_inner": inner,
        "remaining_to_outer": outer,
        "required_outer_clearance": {
            key: required[key] for key in ("r_geo_m", "z_geo_m", "ip_a")
        },
        "qualified_transition_tube": False,
    }


def _state17_acceptance(
    stage: dict[str, Any], source: RGeoZGeoSignal, before: dict[str, Any], after: dict[str, Any]
) -> tuple[list[str], dict[str, Any]]:
    # ``after`` was produced by the fail-closed same-state signal parser.
    offset = {
        "r_geo_m": abs(float(after["r_geo_m"]) - source.boundary.r_geo_m),
        "z_geo_m": abs(float(after["z_geo_m"]) - source.boundary.z_geo_m),
        "ip_a": abs(float(after["ip_a"]) - source.ip_a),
    }
    delta = {
        "r_geo_m": abs(float(after["r_geo_m"]) - float(before["r_geo_m"])),
        "z_geo_m": abs(float(after["z_geo_m"]) - float(before["z_geo_m"])),
        "ip_a": abs(float(after["ip_a"]) - float(before["ip_a"])),
    }
    cap = stage["empirical_successor_acceptance"]
    reasons: list[str] = []
    if offset["r_geo_m"] > stage["inner_r_radius_m"]:
        reasons.append("STATE17_INNER_R")
    if offset["z_geo_m"] > stage["inner_z_radius_m"]:
        reasons.append("STATE17_INNER_Z")
    if offset["ip_a"] > stage["inner_ip_fraction"] * abs(source.ip_a):
        reasons.append("STATE17_INNER_IP")
    for key in ("r_geo_m", "z_geo_m", "ip_a"):
        if delta[key] > cap[key]:
            reasons.append(f"STATE17_EMPIRICAL_DELTA_{key.upper()}")
    return reasons, {
        "source_offset": offset,
        "state16_to_state17_absolute_delta": delta,
        "empirical_caps": {key: cap[key] for key in ("r_geo_m", "z_geo_m", "ip_a")},
        "is_preaction_transition_bound": False,
    }


def offline(stage_path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    failure_kind: str | None = None
    stage = None
    source_signal = None
    frozen = None
    action_stream: list[dict[str, Any]] = []
    evidence_identity: dict[str, str] = {}
    try:
        stage, cfg, evidence = load(stage_path)
        source = _source(cfg)
        source_signal = RGeoZGeoSignal.from_tsc_state(source)
        envelope = OneMsNR1SafetyEnvelope.from_signal(source_signal)
        source_reasons = envelope.state_reasons(
            source_signal,
            source["currents_a_tsc"],
            cfg.min_current_a_tsc,
            cfg.max_current_a_tsc,
        )
        if source_reasons:
            raise ContractError(f"source safety failed: {source_reasons}")
        frozen = build_frozen_one_ms_prefixes(
            source_current_a_tsc=source["currents_a_tsc"],
            turns_tsc=cfg.turns_tsc,
            min_current_a_tsc=cfg.min_current_a_tsc,
            max_current_a_tsc=cfg.max_current_a_tsc,
        )
        targets = _targets(stage, cfg, source)
        reference = evidence["a3_replay_0"]
        previous: Sequence[Any] = source["active_command_decimal_a_tsc"]
        for issue, target in enumerate(targets):
            exact = card15_target_decimal_a(target, cfg.turns_tsc, name=f"e1.offline.{issue}")
            if any(
                value < Decimal(str(low)) or value > Decimal(str(high))
                for value, low, high in zip(exact, cfg.min_current_a_tsc, cfg.max_current_a_tsc)
            ):
                raise ContractError(f"offline target leaves absolute current limits: {issue}")
            maximum = assert_exact_slew(previous, exact, name=f"e1.offline.{issue}")
            action = _target_action(target, issue, maximum)
            if issue <= 15 and not _action_matches_reference(action, reference["actions"][issue]):
                raise InputIntegrityError(f"E1 action does not reproduce A3 at issue {issue}")
            action_stream.append(action)
            previous = exact
        if action_stream[16]["maximum_issued_delta_a"] != 0.0:
            raise InputIntegrityError("issue16 does not request an exact zero change")
        evidence_identity = {
            row["path"]: row["sha256"]
            for row in (
                stage["design"],
                stage["base_tsc_config"],
                *stage["evidence"].values(),
            )
        }
    except InputIntegrityError as exc:
        failure_kind = "input_integrity"
        failures.append(f"{type(exc).__name__}:{exc}")
    except Exception as exc:
        failure_kind = "offline_preflight"
        failures.append(f"{type(exc).__name__}:{exc}")
    passed = not failures
    routes = {} if stage is None else stage.get("routes", {})
    route = (
        OFFLINE_PASS_ROUTE
        if passed
        else routes.get("input_fail", "ONE_MS_NR2R2C2AA4E1_INPUT_INTEGRITY_FAIL_NO_TSC")
        if failure_kind == "input_integrity"
        else routes.get("offline_fail", "ONE_MS_NR2R2C2AA4E1_OFFLINE_PREFLIGHT_FAIL_NO_TSC")
    )
    try:
        safe_stage_path = _inside_root(stage_path, "stage config")
        stage_path_label = str(safe_stage_path.relative_to(ROOT.resolve())).replace("\\", "/")
        stage_path_sha256 = sha256(safe_stage_path) if safe_stage_path.is_file() else None
    except InputIntegrityError:
        stage_path_label = None
        stage_path_sha256 = None
    return {
        "schema_version": SCHEMA,
        "kind": "offline_preflight",
        "source_revision": source_revision,
        "passed": passed,
        "route": route,
        "failure_kind": failure_kind,
        "failures": failures,
        "stage_config_path": stage_path_label,
        "stage_config_sha256": stage_path_sha256,
        "evidence_identity": evidence_identity,
        "source_signal": None if source_signal is None else source_signal.to_dict(),
        "frozen_prefixes": None if frozen is None else frozen.to_dict(),
        "action_stream": action_stream,
        "reset_calls": 0,
        "advance_attempts": 0,
        "verified_successful_plant_advances": 0,
        "plant_advance_gotsc_calls": 0,
        "new_tsc_or_plant_advances": 0,
        "claim_boundary": "zero_plant_preflight_only",
    }


def _raw_inventory(output: Path, compact_record_count: int, stage: dict[str, Any]) -> dict[str, Any]:
    names = tuple(stage["semantic_artifacts"]) + tuple(stage["diagnostic_artifacts"])
    episode = output / "rollouts" / ROLLOUT_ID
    lines: list[str] = []
    missing: list[str] = []
    total_bytes = 0
    existing_state_indices: list[int] = []
    for state_index in range(18):
        folder = episode / f"{1100 + state_index}ms"
        if not folder.is_dir():
            continue
        existing_state_indices.append(state_index)
        for name in names:
            path = folder / name
            relative = path.relative_to(output).as_posix()
            if not path.is_file():
                missing.append(relative)
                continue
            size = path.stat().st_size
            digest = sha256(path)
            total_bytes += size
            lines.append(f"{relative}\t{size}\t{digest}")
    continuous_state_indices: list[int] = []
    for state_index in range(18):
        if state_index not in existing_state_indices:
            break
        continuous_state_indices.append(state_index)
    noncontinuous_state_indices = [
        index for index in existing_state_indices if index not in continuous_state_indices
    ]

    diagnostic_lines: list[str] = []
    diagnostic_bytes = 0
    diagnostic_directories: list[str] = []
    unexpected_directories: list[str] = []
    if episode.is_dir():
        allowed_states = {f"{time_ms}ms" for time_ms in range(1100, 1118)}
        for folder in sorted(path for path in episode.iterdir() if path.is_dir()):
            if (
                folder.name not in allowed_states
                and not folder.name.startswith("runtime_artifacts_failed_")
            ):
                unexpected_directories.append(folder.relative_to(output).as_posix())
        for folder in sorted(episode.glob("runtime_artifacts_failed_*")):
            if not folder.is_dir():
                continue
            diagnostic_directories.append(folder.relative_to(output).as_posix())
            for path in sorted(folder.iterdir()):
                if not path.is_file():
                    continue
                size = path.stat().st_size
                digest = sha256(path)
                diagnostic_bytes += size
                diagnostic_lines.append(
                    f"{path.relative_to(output).as_posix()}\t{size}\t{digest}"
                )
    payload = "".join(f"{line}\n" for line in sorted(lines)).encode("utf-8")
    diagnostic_payload = "".join(
        f"{line}\n" for line in sorted(diagnostic_lines)
    ).encode("utf-8")
    state18 = episode / "1118ms"
    return {
        "compact_record_count": compact_record_count,
        "existing_raw_state_indices": existing_state_indices,
        "continuous_raw_state_indices": continuous_state_indices,
        "continuous_raw_state_count": len(continuous_state_indices),
        "raw_observed_plant_advances": max(0, len(continuous_state_indices) - 1),
        "noncontinuous_raw_state_indices": noncontinuous_state_indices,
        "required_artifact_files_for_existing_state_directories": len(existing_state_indices) * len(names),
        "required_artifact_files": len(lines),
        "required_artifact_bytes": total_bytes,
        "required_artifact_inventory_sha256": hashlib.sha256(payload).hexdigest(),
        "missing_required_artifacts_for_existing_state_directories": missing,
        "runtime_failure_diagnostic_directories": diagnostic_directories,
        "runtime_failure_diagnostic_files": len(diagnostic_lines),
        "runtime_failure_diagnostic_bytes": diagnostic_bytes,
        "runtime_failure_diagnostic_inventory_sha256": hashlib.sha256(
            diagnostic_payload
        ).hexdigest(),
        "unexpected_rollout_directories": unexpected_directories,
        "state18_directory_present": state18.exists(),
    }


def _route_for_rollout(stage: dict[str, Any], row: dict[str, Any]) -> str:
    routes = stage["routes"]
    categories = row["reason_categories"]
    if row["raw_reporting_integrity_failed"]:
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


def one_rollout(
    cfg: TSCConfig,
    stage: dict[str, Any],
    reference: dict[str, Any],
    targets: Sequence[Card15Target],
) -> dict[str, Any]:
    runner: CountingTSCStepRunner | None = None
    states: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    attempted_actions: list[dict[str, Any]] = []
    reasons: list[str] = []
    categories: list[str] = []
    reset_calls = 0
    advance_attempts = 0
    successful = 0
    advance_times: list[float] = []
    state16_clearance = None
    successor_acceptance = None
    failed_issue_step: int | None = None
    cleanup_error: str | None = None
    started = time.perf_counter()
    try:
        runner = CountingTSCStepRunner(
            cfg, worker_id="c2aa4e1_single_successor_r0", keep_workspace=False
        )
        reset_calls += 1
        state = runner.reset(episode_name=ROLLOUT_ID)
        source_record = _record_with_sizes(cfg, state, stage)
        states.append(source_record)
        if (
            source_record["time_ms"] != 1100
            or source_record["reported_returncode"] != 0
            or source_record["reported_abnormal"]
        ):
            reasons.append(
                "SOURCE_RESET_INVALID:"
                f"returncode={source_record['reported_returncode']}:"
                f"abnormal={source_record['reported_abnormal']}:"
                f"time={source_record['time_ms']}"
            )
            categories.append("known_prefix")
            raise StopRollout
        source_signal = RGeoZGeoSignal.from_tsc_state(state)
        envelope = OneMsNR1SafetyEnvelope.from_signal(source_signal)

        for issue, target in enumerate(targets):
            failed_issue_step = issue
            current_signal = RGeoZGeoSignal.from_tsc_state(state)
            prefix_reasons = prefix_mismatch_reasons(states, actions, reference, stage, issue)
            hard = list(envelope.state_reasons(
                current_signal,
                state["currents_a_tsc"],
                cfg.min_current_a_tsc,
                cfg.max_current_a_tsc,
            )) + _outer_reasons(stage, source_signal, current_signal)
            if prefix_reasons:
                reasons.extend(prefix_reasons)
                categories.append("known_prefix")
            if hard:
                reasons.extend(f"PREISSUE_{reason}:{issue}" for reason in hard)
                categories.append("hard_safety")
            if prefix_reasons or hard:
                break
            if issue == 16:
                clearance_reasons, state16_clearance = _state16_clearance_reasons(
                    stage, source_signal, current_signal
                )
                if clearance_reasons:
                    reasons.extend(clearance_reasons)
                    categories.append("clearance")
                    break
            try:
                target_exact = card15_target_decimal_a(
                    target, cfg.turns_tsc, name=f"e1.run.target.{issue}"
                )
                maximum = assert_exact_slew(
                    states[-1]["active_command_decimal_a_tsc"],
                    target_exact,
                    name=f"e1.run.issue.{issue}",
                )
                if any(
                    value < Decimal(str(low)) or value > Decimal(str(high))
                    for value, low, high in zip(
                        target_exact, cfg.min_current_a_tsc, cfg.max_current_a_tsc
                    )
                ):
                    raise ContractError("target leaves absolute current limits")
            except ContractError as exc:
                reasons.append(f"ISSUED_ACTION:{issue}:{exc}")
                categories.append("novel_execution" if issue == 16 else "known_prefix")
                break
            action = _target_action(target, issue, maximum)
            attempted_actions.append(action)
            advance_attempts += 1
            advance_started = time.perf_counter()
            try:
                successor_state = runner.step_current_a(
                    np.asarray(target.current_a_tsc, dtype=float)
                )
            except Exception as exc:
                advance_times.append(time.perf_counter() - advance_started)
                reasons.append(f"STEP_EXECUTION:{issue}:{type(exc).__name__}:{exc}")
                categories.append("novel_execution" if issue == 16 else "known_prefix")
                break
            advance_times.append(time.perf_counter() - advance_started)

            # Capture the successor before interpreting its scientific route.
            try:
                record = _record_with_sizes(cfg, successor_state, stage)
            except Exception as exc:
                reasons.append(f"SUCCESSOR_RECORD:{issue}:{type(exc).__name__}:{exc}")
                categories.append("novel_execution" if issue == 16 else "known_prefix")
                break
            expected_time = 1101 + issue
            if record["time_ms"] == expected_time:
                # Keep a parseable expected-clock successor even when TSC
                # reports abnormal/nonzero; it is raw-observed, not verified.
                states.append(record)
            if record["time_ms"] != expected_time:
                reasons.append(
                    f"SUCCESSOR_EXECUTION:{issue}:returncode={successor_state.get('returncode', 0)}:"
                    f"abnormal={bool(successor_state.get('abnormal', False))}:time={record['time_ms']}"
                )
                categories.append("novel_execution" if issue == 16 else "known_prefix")
                break
            if record["reported_returncode"] != 0 or record["reported_abnormal"]:
                reasons.append(
                    f"SUCCESSOR_EXECUTION:{issue}:returncode={record['reported_returncode']}:"
                    f"abnormal={record['reported_abnormal']}:time={record['time_ms']}"
                )
                categories.append("novel_execution" if issue == 16 else "known_prefix")
                state = successor_state
                break
            actions.append(action)
            successful += 1

            interface_reasons: list[str] = []
            if tuple(record["active_command_card15_fields"]) != target.card15_fields:
                interface_reasons.append(f"CARD15:{issue}")
            try:
                record["maximum_observed_delta_a"] = assert_exact_slew(
                    states[-2]["actual_current_decimal_a_tsc"],
                    record["actual_current_decimal_a_tsc"],
                    name=f"e1.run.observed.{issue}",
                )
            except ContractError as exc:
                interface_reasons.append(f"OBSERVED_SLEW:{issue}:{exc}")
            successor_signal = RGeoZGeoSignal.from_tsc_state(successor_state)
            hard = list(envelope.state_reasons(
                successor_signal,
                successor_state["currents_a_tsc"],
                cfg.min_current_a_tsc,
                cfg.max_current_a_tsc,
            )) + _outer_reasons(stage, source_signal, successor_signal)
            if interface_reasons:
                reasons.extend(interface_reasons)
                categories.append("novel_execution" if issue == 16 else "known_prefix")
            if hard:
                reasons.extend(f"POSTISSUE_{reason}:{issue}" for reason in hard)
                categories.append("hard_safety")
            if interface_reasons or hard:
                state = successor_state
                break

            state = successor_state
            if issue == 16:
                acceptance_reasons, successor_acceptance = _state17_acceptance(
                    stage, source_signal, states[-2], states[-1]
                )
                if acceptance_reasons:
                    reasons.extend(acceptance_reasons)
                    categories.append("acceptance")
                break  # Unconditional: never issue step17 or create state18.
    except StopRollout:
        pass
    except Exception as exc:
        reasons.append(f"ROLLOUT_EXECUTION:{type(exc).__name__}:{exc}")
        categories.append("known_prefix" if advance_attempts < 17 else "novel_execution")
    finally:
        if runner is not None:
            try:
                runner.cleanup_runtime_workspace()
            except Exception as exc:
                cleanup_error = f"CLEANUP:{type(exc).__name__}:{exc}"
                reasons.append(cleanup_error)
                categories.append("novel_execution" if advance_attempts == 17 else "known_prefix")

    reasons = list(dict.fromkeys(reasons))
    categories = list(dict.fromkeys(categories))
    gotsc_calls = 0 if runner is None else int(
        getattr(runner, "plant_advance_gotsc_calls", 0)
    )
    state17_recorded = any(state["time_ms"] == 1117 for state in states)
    raw_observed = max(0, len(states) - 1)
    passed = not reasons and state17_recorded and successful == 17
    return {
        "rollout_id": ROLLOUT_ID,
        "candidate_id": ROLLOUT_ID,
        "passed": passed,
        "reasons": reasons,
        "reason_categories": categories,
        "failed_issue_step": None if passed else failed_issue_step,
        "reset_calls": reset_calls,
        "advance_attempts": advance_attempts,
        "verified_successful_plant_advances": successful,
        "plant_advances": successful,
        "raw_observed_plant_advances": raw_observed,
        "plant_advance_gotsc_calls": gotsc_calls,
        "states": states,
        "actions": actions,
        "attempted_actions": attempted_actions,
        "state16_clearance": state16_clearance,
        "successor_acceptance": successor_acceptance,
        "unknown_successor_attempted": advance_attempts == 17,
        "unknown_successor_observed": state17_recorded,
        "state17_recorded": state17_recorded,
        "unconditional_stop_after_state17": state17_recorded and advance_attempts == 17,
        "issue17_attempted": advance_attempts > 17,
        "state18_observed": any(state["time_ms"] >= 1118 for state in states),
        "retry_attempted": False,
        "identity_consumed": advance_attempts > 0,
        "cleanup_error": cleanup_error,
        "advance_wall_time_s": advance_times,
        "wall_time_s": time.perf_counter() - started,
    }


def run(stage_path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = _inside_root(output, "run output")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    output.mkdir(parents=True)
    gate = offline(stage_path, source_revision)
    write_new(output / "offline_preflight.json", gate)
    package_fields = {
        "package_gate_external": True,
        "package_or_deployment_route_emitted_by_this_script": False,
    }
    if not gate["passed"]:
        result = {
            "schema_version": SCHEMA,
            "source_revision": source_revision,
            "passed": False,
            "execution_completed": False,
            "route": gate["route"],
            "reason_categories": [gate["failure_kind"] or "offline_preflight"],
            "reasons": gate["failures"],
            "rollouts_completed": 0,
            "reset_calls": 0,
            "advance_attempts": 0,
            "verified_successful_plant_advances": 0,
            "plant_advances": 0,
            "raw_observed_plant_advances": 0,
            "plant_advance_gotsc_calls": 0,
            "unknown_successor_attempted": False,
            "unknown_successor_observed": False,
            "state17_recorded": False,
            "unconditional_stop_after_state17": False,
            "issue17_attempted": False,
            "state18_observed": False,
            "retry_attempted": False,
            "identity_consumed": False,
            "raw_preservation_verified": False,
            "partial_failure_raw_preserved_and_reported": False,
            "failure_raw_preserved_and_reported": False,
            "offline_preflight_path": "offline_preflight.json",
            **package_fields,
            "claim_boundary": "offline_gate_failure_no_tsc_or_plant_advance",
        }
        write_new(output / "result.json", result)
        return result

    stage, cfg, evidence = load(stage_path)
    stage_path = _inside_root(stage_path, "stage config")
    stage_path_label = str(stage_path.relative_to(ROOT.resolve())).replace("\\", "/")
    stage_path_sha256 = sha256(stage_path)
    if gate.get("stage_config_sha256") != stage_path_sha256:
        raise InputIntegrityError("stage config changed after offline preflight")
    cfg.run_root = output / "rollouts"
    source = _source(cfg)
    targets = _targets(stage, cfg, source)
    row = one_rollout(cfg, stage, evidence["a3_replay_0"], targets)
    row.update({
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "stage_config_path": stage_path_label,
        "stage_config_sha256": stage_path_sha256,
        **package_fields,
    })
    inventory_error = None
    try:
        inventory = _raw_inventory(output, len(row["states"]), stage)
    except Exception as exc:
        inventory_error = f"RAW_INVENTORY:{type(exc).__name__}:{exc}"
        inventory = {
            "compact_record_count": len(row["states"]),
            "existing_raw_state_indices": [],
            "continuous_raw_state_indices": [],
            "continuous_raw_state_count": 0,
            "raw_observed_plant_advances": 0,
            "noncontinuous_raw_state_indices": [],
            "required_artifact_files_for_existing_state_directories": 0,
            "required_artifact_files": 0,
            "required_artifact_bytes": 0,
            "required_artifact_inventory_sha256": None,
            "missing_required_artifacts_for_existing_state_directories": [],
            "runtime_failure_diagnostic_directories": [],
            "runtime_failure_diagnostic_files": 0,
            "runtime_failure_diagnostic_bytes": 0,
            "runtime_failure_diagnostic_inventory_sha256": None,
            "unexpected_rollout_directories": [],
            "state18_directory_present": False,
        }
    row["raw_inventory"] = inventory
    row["raw_reporting_integrity_failed"] = bool(
        inventory_error
        or inventory["missing_required_artifacts_for_existing_state_directories"]
        or inventory["noncontinuous_raw_state_indices"]
        or inventory["unexpected_rollout_directories"]
        or inventory["state18_directory_present"]
        or (row["state17_recorded"] and inventory["required_artifact_files"] != 90)
        or inventory["compact_record_count"] != inventory["continuous_raw_state_count"]
        or row["raw_observed_plant_advances"] != inventory["raw_observed_plant_advances"]
        or row["issue17_attempted"]
        or row["state18_observed"]
        or row["reset_calls"] > 1
        or row["advance_attempts"] > 17
        or row["plant_advance_gotsc_calls"] > 17
        or row["verified_successful_plant_advances"] != len(row["actions"])
        or row["advance_attempts"] != len(row["attempted_actions"])
        or row["raw_observed_plant_advances"] < row["verified_successful_plant_advances"]
        or not (
            row["verified_successful_plant_advances"]
            <= row["plant_advance_gotsc_calls"]
            <= row["advance_attempts"]
            <= row["verified_successful_plant_advances"] + 1
        )
        or (
            bool(row["states"])
            and len(row["states"]) != row["raw_observed_plant_advances"] + 1
        )
    )
    if row["raw_reporting_integrity_failed"]:
        row["passed"] = False
        additions = ["RAW_OR_COUNTER_INTEGRITY"]
        if inventory_error is not None:
            additions.append(inventory_error)
        row["reasons"] = list(dict.fromkeys(row["reasons"] + additions))
        row["reason_categories"] = list(dict.fromkeys(row["reason_categories"] + ["raw_reporting"]))
    row["route"] = _route_for_rollout(stage, row)
    raw_preservation_verified = bool(
        row["advance_attempts"] > 0
        and not inventory_error
        and inventory["continuous_raw_state_count"] > 0
        and not inventory["missing_required_artifacts_for_existing_state_directories"]
        and not inventory["noncontinuous_raw_state_indices"]
        and not inventory["unexpected_rollout_directories"]
        and not inventory["state18_directory_present"]
        and inventory["compact_record_count"] == inventory["continuous_raw_state_count"]
    )
    row["raw_preservation_verified"] = raw_preservation_verified
    row["partial_failure_raw_preserved_and_reported"] = bool(
        not row["passed"] and len(row["states"]) < 18 and raw_preservation_verified
    )
    row["failure_raw_preserved_and_reported"] = bool(
        not row["passed"] and raw_preservation_verified
    )
    exploration_write_error = None
    try:
        write_new(output / "exploration.json", row)
    except Exception as exc:
        exploration_write_error = f"COMPACT_WRITE:{type(exc).__name__}:{exc}"
        row["passed"] = False
        row["route"] = stage["routes"]["raw_reporting_fail"]
        row["reasons"] = list(dict.fromkeys(row["reasons"] + [exploration_write_error]))
        row["reason_categories"] = list(dict.fromkeys(row["reason_categories"] + ["raw_reporting"]))
        row["partial_failure_raw_preserved_and_reported"] = False
        row["failure_raw_preserved_and_reported"] = False

    result = {
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "passed": row["passed"],
        "execution_completed": row["verified_successful_plant_advances"] == 17,
        "route": row["route"],
        "reason_categories": row["reason_categories"],
        "rollouts_completed": 1,
        "reset_calls": row["reset_calls"],
        "advance_attempts": row["advance_attempts"],
        "verified_successful_plant_advances": row["verified_successful_plant_advances"],
        "plant_advances": row["verified_successful_plant_advances"],
        "raw_observed_plant_advances": row["raw_observed_plant_advances"],
        "plant_advance_gotsc_calls": row["plant_advance_gotsc_calls"],
        "unknown_successor_attempted": row["unknown_successor_attempted"],
        "unknown_successor_observed": row["unknown_successor_observed"],
        "state17_recorded": row["state17_recorded"],
        "unconditional_stop_after_state17": row["unconditional_stop_after_state17"],
        "issue17_attempted": row["issue17_attempted"],
        "state18_observed": row["state18_observed"],
        "retry_attempted": row["retry_attempted"],
        "identity_consumed": row["identity_consumed"],
        "raw_preservation_verified": row["raw_preservation_verified"],
        "partial_failure_raw_preserved_and_reported": row[
            "partial_failure_raw_preserved_and_reported"
        ],
        "failure_raw_preserved_and_reported": row["failure_raw_preserved_and_reported"],
        "reasons": row["reasons"],
        "state16_clearance": row["state16_clearance"],
        "successor_acceptance": row["successor_acceptance"],
        **inventory,
        "rollout_compact_path": None if exploration_write_error else "exploration.json",
        "exploration_write_error": exploration_write_error,
        **package_fields,
        "claim_boundary": (
            "one_simulator_only_unseen_successor_development_observation; not_a_transition_"
            "tube_hold_model_controller_optimizer_training_fixture_or_qualification"
        ),
    }
    write_new(output / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("offline", "run"))
    parser.add_argument(
        "--stage-config",
        type=Path,
        default=ROOT / "configs/rgeo_zgeo_1ms_nr2r2c2aa4e1_single_successor_exploration.json",
    )
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "offline":
        result = offline(args.stage_config.resolve(), args.source_revision)
        write_new(args.output.resolve(), result)
    else:
        result = run(args.stage_config.resolve(), args.source_revision, args.output.resolve())
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
