#!/usr/bin/env python3
"""Independent full-raw audit for ID-2Z20 Authority-L0."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_id2z20_authority_l0_feedback as primary  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2z9_late_root_branch_utility_support_independent as z9i  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-id2z20-authority-l0-feedback-independent-raw-v1"


def inside(path: Path, label: str) -> Path:
    value = path.resolve()
    try:
        value.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(f"{label} leaves repository") from exc
    return value


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("object required")
    return value


def _ordered_ids(stage: dict[str, Any]) -> list[str]:
    values = ["dev_hold"]
    for phase in stage["phase_issues"]:
        values.extend(f"dev_p{phase}_{arm}" for arm in primary.ARM_IDS[1:])
    values.extend(stage["phase_b"]["candidate_ids"])
    values.extend(("selected_replay", "validation_hold", "validation_policy",
                   "validation_finite_return"))
    return values


def compact_rows(run_dir: Path, stage: dict[str, Any], failures: list[str]) -> list[dict[str, Any]]:
    excluded = {"result.json", "offline_preflight.json", "independent_raw_audit.json"}
    rows = [load_json(path) for path in run_dir.glob("*.json") if path.name not in excluded]
    rows = [row for row in rows if "rollout_id" in row]
    order = {name: index for index, name in enumerate(_ordered_ids(stage))}
    rows.sort(key=lambda row: order.get(str(row.get("rollout_id")), 999))
    ids = [str(row.get("rollout_id")) for row in rows]
    expected = _ordered_ids(stage)
    if ids != expected[:len(ids)] or len(ids) != len(set(ids)):
        failures.append("COMPACT_ORDER_OR_IDENTITY")
    return rows


def _selector_choice(stage: dict[str, Any], library: dict[str, Any],
                     state: dict[str, Any], previous: dict[str, Any],
                     source: dict[str, Any], issue: int, horizon: int,
                     arms: dict[str, Any], center: Any) -> tuple[str, list[dict[str, Any]]]:
    phase = 32 if issue < 40 else 40
    cell = library["phases"][str(phase)][str(horizon)]
    velocity = np.asarray(((float(state["r_geo_m"]) - float(previous["r_geo_m"])) * 1000.0,
                           (float(state["z_geo_m"]) - float(previous["z_geo_m"])) * 1000.0))
    center_current = np.asarray(center.current_a_tsc, dtype=float)
    candidates = []
    for order, arm in enumerate(primary.ARM_IDS):
        response = cell["arms"][arm]
        disp = np.asarray(cell["baseline_displacement"], dtype=float) + np.asarray(
            response["response_displacement"], dtype=float)
        r = float(state["r_geo_m"]) + disp[0]
        z = float(state["z_geo_m"]) + disp[1]
        ip = float(state["ip_a"]) + disp[2]
        terminal_velocity = velocity + np.asarray(cell["baseline_velocity_change_m_per_s"])
        terminal_velocity += np.asarray(response["response_velocity_m_per_s"])
        distance = math.hypot(r - float(source["r_geo_m"]), z - float(source["z_geo_m"]))
        speed = float(np.linalg.norm(terminal_velocity))
        ip_fraction = abs(ip - float(source["ip_a"])) / abs(float(source["ip_a"]))
        score = max(distance / .025, speed / .1, ip_fraction / .05)
        excursion = float(np.linalg.norm(np.asarray(arms[arm].current_a_tsc) - center_current))
        candidates.append({"arm_id": arm, "predicted_score": score,
                           "predicted_distance_m": distance,
                           "predicted_speed_m_per_s": speed,
                           "predicted_ip_fraction": ip_fraction,
                           "current_excursion_a_l2": excursion,
                           "frozen_order": order})
    selected = min(candidates, key=lambda row: (row["predicted_score"],
                                                 row["current_excursion_a_l2"],
                                                 row["frozen_order"]))
    return selected["arm_id"], candidates


def action_checks(raw_rows: Sequence[dict[str, Any]], compact: Sequence[dict[str, Any]],
                  stage: dict[str, Any], cfg: Any, dev: dict[str, Any],
                  validation: dict[str, Any], failures: list[str]) -> None:
    raw_by_id = {str(row["rollout_id"]): row for row in raw_rows}
    compact_by_id = {str(row["rollout_id"]): row for row in compact}
    phase_a_raw = [raw_by_id[name] for name in _ordered_ids(stage)[:17]
                   if name in raw_by_id]
    if len(phase_a_raw) < 17:
        return
    library = primary.response_library(phase_a_raw, stage)
    for name, row in raw_by_id.items():
        reference = validation if row.get("root_family_id") == validation.get("family_id") else dev
        prefix = primary.root_targets(reference, cfg, f"audit.{name}")
        center = prefix[-1]
        arms = primary.basis_targets(stage, center, cfg, f"audit.{name}")
        compact_row = compact_by_id[name]
        for issue, action in enumerate(compact_row.get("actions", [])):
            fields = action.get("expected_card15_fields")
            if issue < 32:
                expected = prefix[issue].card15_fields
                if fields != list(expected):
                    failures.append(f"ROOT_ACTION:{name}:{issue}")
                continue
            if name.startswith("dev_p"):
                phase = int(name.split("_")[1][1:])
                arm = "_".join(name.split("_")[2:])
                expected_arm = arm if issue == phase else "hold"
                if fields != list(arms[expected_arm].card15_fields):
                    failures.append(f"PHASE_A_ACTION:{name}:{issue}")
                continue
            if name in ("dev_hold", "validation_hold"):
                if fields != list(center.card15_fields):
                    failures.append(f"HOLD_ACTION:{name}:{issue}")
                continue
            decision = action.get("selector_decision")
            if decision is not None:
                horizon = int(row.get("response_horizon_ms", 0))
                selected, candidates = _selector_choice(
                    stage, library, row["states"][issue], row["states"][issue - 1],
                    row["states"][0], issue, horizon, arms, center)
                if (decision.get("selected_arm_id") != selected
                        or decision.get("candidate_values") != candidates
                        or fields != list(arms[selected].card15_fields)):
                    failures.append(f"SELECTOR_DECISION:{name}:{issue}")
            elif fields != list(center.card15_fields):
                failures.append(f"DYNAMIC_RETURN_OR_HOLD:{name}:{issue}")
        if row.get("finite_return_only"):
            nonholds = [action for action in compact_row.get("actions", [])
                        if action.get("arm_id") not in ("root", "hold")]
            if len(nonholds) > 1:
                failures.append(f"FINITE_RETURN_MULTIPLE_PULSES:{name}")


def audit(stage_path: Path, run_dir: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    stage_path, run_dir = inside(stage_path, "config"), inside(run_dir, "run")
    result = load_json(run_dir / "result.json")
    try:
        stage, _, cfg, _, dev, validation = primary.load(stage_path)
    except Exception as exc:
        failures.append(f"STAGE_LOAD:{type(exc).__name__}:{exc}")
        stage, cfg, dev, validation = load_json(stage_path), None, {}, {}
    compact = compact_rows(run_dir, stage, failures)
    for row in compact:
        if (row.get("schema_version") != primary.SCHEMA
                or row.get("source_revision") != source_revision):
            failures.append(f"COMPACT_IDENTITY:{row.get('rollout_id')}")
    rollout_root = run_dir / "rollouts"
    actual_ids = (sorted(path.name for path in rollout_root.iterdir() if path.is_dir())
                  if rollout_root.is_dir() else [])
    if actual_ids != sorted(str(row.get("rollout_id")) for row in compact):
        failures.append("ROLLOUT_DIRECTORY_SET")
    raw_rows: list[dict[str, Any]] = []
    lines: list[str] = []
    byte_count = 0
    if cfg is not None:
        expected = [{"rollout_id": row["rollout_id"], "actions": row.get("actions", [])}
                    for row in compact]
        raw_rows, lines, byte_count = z9i._raw_rows(run_dir, cfg, expected, compact, failures)
        action_checks(raw_rows, compact, stage, cfg, dev, validation, failures)
    digest = hashlib.sha256(
        "".join(f"{line}\n" for line in sorted(lines)).encode()).hexdigest()
    if (digest != result.get("required_artifact_inventory_sha256")
            or len(lines) != result.get("required_artifact_files")
            or byte_count != result.get("required_artifact_bytes")):
        failures.append("INVENTORY")
    raw_by_id = {str(row.get("rollout_id")): row for row in raw_rows}
    phase_a_rows = [raw_by_id[name] for name in _ordered_ids(stage)[:17] if name in raw_by_id]
    phase_a = primary.phase_a_metrics(phase_a_rows, stage)
    library = primary.response_library(phase_a_rows, stage) if phase_a.get("passed") else {}
    hold = raw_by_id.get("dev_hold", {})
    utility_values = []
    for candidate in stage["phase_b"]["candidate_ids"]:
        row = raw_by_id.get(candidate)
        if row is not None:
            utility_values.append({"candidate_id": candidate,
                                   **primary.utility_metrics(row, hold, stage)})
    eligible = [value for value in utility_values if value.get("passed")]
    selected_id = (min(eligible, key=lambda value: (
        value["candidate"]["terminal_worst_normalized_score"], value["candidate_id"]))["candidate_id"]
                   if eligible else None)
    selected = raw_by_id.get(selected_id or "")
    replay = raw_by_id.get("selected_replay")
    replay_check = (primary.z6.compare_rows(selected, replay, stage)
                    if selected is not None and replay is not None else
                    {"passed": False, "failures": ["NOT_RUN"]})
    validation_hold = raw_by_id.get("validation_hold")
    validation_policy = raw_by_id.get("validation_policy")
    finite = raw_by_id.get("validation_finite_return")
    validation_utility = (primary.utility_metrics(validation_policy, validation_hold, stage)
                          if validation_policy and validation_hold else {"passed": False})
    finite_value = (primary.finite_return_metrics(finite, validation_hold, stage)
                    if finite and validation_hold else {"passed": False})
    selected_capture = bool(selected and primary.terminal_metrics(selected, stage)["capture_passed"])
    replay_capture = bool(replay and primary.terminal_metrics(replay, stage)["capture_passed"])
    capture = bool(selected_capture and replay_capture)
    prefix_values = [primary.prefix_check(
        next(row for row in compact if row["rollout_id"] == raw["rollout_id"]),
        validation if raw.get("root_family_id") == validation.get("family_id") else dev, stage)
        for raw in raw_rows]
    execution = bool(raw_rows and all(row.get("passed") or primary.safe_stop(row, stage)
                                      for row in raw_rows)
                     and all(value.get("passed") for value in prefix_values))
    raw_ok = bool(len(lines) == 5 * sum(len(row.get("states", [])) for row in raw_rows)
                  and not any(value.startswith("MISSING_ARTIFACT") for value in failures))
    route = primary._route(stage, execution, raw_ok, bool(phase_a.get("passed")),
                           selected_id is not None, bool(replay_check.get("passed")),
                           bool(validation_utility.get("passed") and finite_value.get("passed")),
                           capture)
    scientific = {"phase_a": phase_a, "response_library": library,
                  "phase_b_candidates": utility_values, "selected_candidate_id": selected_id,
                  "selected_replay_check": replay_check,
                  "development_capture_seed_passed": selected_capture,
                  "fresh_replay_capture_seed_passed": replay_capture,
                  "validation_policy_utility": validation_utility,
                  "validation_finite_return": finite_value,
                  "authority_l0_passed": bool(validation_utility.get("passed")
                                              and finite_value.get("passed")),
                  "six_state_capture_seed_passed": capture,
                  "recourse_l1_claimed": False}
    if result.get("prefix_checks") != prefix_values:
        failures.append("RECOMPUTE_PREFIX_CHECKS")
    if result.get("scientific_metrics") != scientific:
        failures.append("RECOMPUTE_SCIENTIFIC_METRICS")
    expected_pass = route in (stage["routes"]["authority_pass_no_capture"],
                              stage["routes"]["authority_and_capture_pass"])
    if result.get("route") != route or result.get("passed") != expected_pass:
        failures.append("PRIMARY_ROUTE_OR_VERDICT")
    counters = {key: sum(int(row.get(key, 0)) for row in compact) for key in
                ("reset_calls", "advance_attempts", "plant_advance_gotsc_calls",
                 "verified_plant_advances")}
    for key, value in counters.items():
        if result.get(key) != value:
            failures.append(f"COUNTER:{key}")
    if (result.get("models_fit_or_updated") != 0
            or result.get("calibration_or_holdout_records_read") != 0):
        failures.append("FORBIDDEN_DATA_OR_MODEL_USE")
    failures = list(dict.fromkeys(failures))
    return {"schema_version": SCHEMA, "source_revision": source_revision,
            "stage_config_sha256": primary.CONFIG_SHA256,
            "primary_sha256": primary.io.sha256(run_dir / "result.json"),
            "audit_passed": not failures, "failures": failures,
            "primary_route": result.get("route"), "recomputed_route": route,
            "recomputed_scientific_metrics": scientific,
            "required_artifact_files": len(lines), "required_artifact_bytes": byte_count,
            "required_artifact_inventory_sha256": digest,
            "raw_rollouts_reparsed": len(raw_rows),
            "raw_states_reparsed": sum(len(row.get("states", [])) for row in raw_rows),
            **counters, "models_fit_or_updated": 0,
            "calibration_or_holdout_records_read": 0,
            "claim_boundary": "Independent raw audit; no Recourse-L1 or controller claim."}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-config", type=Path, default=primary.CONFIG)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    value = audit(args.stage_config, args.run_dir, args.source_revision)
    primary.io.write_new(inside(args.output, "audit output"), value)
    print(json.dumps(value, indent=2, sort_keys=True, allow_nan=False))
    return 0 if value["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
