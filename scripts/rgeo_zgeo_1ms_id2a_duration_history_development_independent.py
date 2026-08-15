#!/usr/bin/env python3
"""Independent raw reparse for the frozen 1 ms ID2A campaign."""

from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_id0_vector_tail_independent import ARTIFACTS, _state  # noqa: E402
from scripts.rgeo_zgeo_1ms_id1a_context_anchor_pilot_independent import (  # noqa: E402
    _compare_compact,
    _numeric_max_difference,
)
from scripts.rgeo_zgeo_1ms_id2a_duration_history_development import (  # noqa: E402
    CONFIG_SHA256,
    SCHEMA as PRIMARY_SCHEMA,
    lag_support,
    load,
    route_for,
    rollout_specs,
    scientific_metrics,
    targets_and_streams,
)
from scripts.rgeo_zgeo_1ms_nr1_qualification import _source  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    assert_exact_slew,
    decimal_single_turn_currents_a,
)


SCHEMA = "rgeo-zgeo-1ms-id2a-duration-history-development-v1-independent"


def _inside(path: Path, label: str) -> Path:
    result = path.resolve()
    try:
        result.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} leaves repository root") from exc
    return result


def _inventory(run_dir: Path, specs: list[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    names = tuple(stage["semantic_artifacts"]) + tuple(stage["diagnostic_artifacts"])
    lines: list[str] = []
    missing: list[str] = []
    total = 0
    for spec in specs:
        for state_index in range(stage["horizon_steps"] + 1):
            folder = run_dir / "rollouts" / spec["rollout_id"] / f"{stage['takeover_time_ms'] + state_index}ms"
            for name in names:
                path = folder / name
                label = path.relative_to(run_dir).as_posix()
                if not path.is_file():
                    missing.append(label)
                    continue
                size = path.stat().st_size
                total += size
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                lines.append(f"{label}\t{size}\t{digest}")
    payload = "".join(f"{line}\n" for line in sorted(lines)).encode()
    return {
        "required_artifact_files": len(lines), "required_artifact_bytes": total,
        "required_artifact_inventory_sha256": hashlib.sha256(payload).hexdigest(),
        "missing_required_artifacts": missing,
    }


def audit(stage_path: Path, run_dir: Path, source_revision: str) -> dict[str, Any]:
    run_dir = _inside(run_dir, "run directory")
    stage, cfg, _ = load(stage_path)
    primary = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    if primary.get("source_revision") != source_revision or primary.get("stage_config_sha256") != CONFIG_SHA256:
        raise ValueError("primary identity mismatch")
    source = _source(cfg)
    streams = targets_and_streams(stage, cfg, source)
    stream_by_id = {row["rollout_id"]: row for row in streams}
    specs = rollout_specs(stage)
    failures: list[str] = []
    rows: list[dict[str, Any]] = []
    for spec in specs:
        compact_path = run_dir / f"{spec['rollout_id']}.json"
        if not compact_path.is_file():
            failures.append(f"MISSING_COMPACT:{spec['rollout_id']}")
            continue
        compact = json.loads(compact_path.read_text(encoding="utf-8"))
        raw_states = []
        for index in range(stage["horizon_steps"] + 1):
            folder = run_dir / "rollouts" / spec["rollout_id"] / f"{stage['takeover_time_ms'] + index}ms"
            try:
                raw_states.append(_state(folder, cfg))
            except Exception as exc:
                failures.append(f"RAW_STATE:{spec['rollout_id']}:{index}:{type(exc).__name__}:{exc}")
                break
        expected = stream_by_id[spec["rollout_id"]]
        actions = []
        previous_command = source["active_command_decimal_a_tsc"]
        for index, frozen in enumerate(expected["actions"]):
            action = dict(frozen)
            exact = decimal_single_turn_currents_a(
                tuple(value.strip() for value in frozen["expected_card15_fields"]),
                cfg.turns_tsc, name=f"id2a.audit.{spec['rollout_id']}.{index}",
            )
            action["maximum_issued_delta_a"] = assert_exact_slew(
                previous_command, exact, name=f"id2a.audit.issue.{spec['rollout_id']}.{index}",
            )
            previous_command = exact
            actions.append(action)
        raw = {
            **spec, "schema_version": PRIMARY_SCHEMA, "source_revision": source_revision,
            "passed": len(raw_states) == stage["horizon_steps"] + 1,
            "states": raw_states, "actions": actions[:max(0, len(raw_states) - 1)],
        }
        if len(raw_states) == stage["horizon_steps"] + 1:
            outer = stage["empirical_exploration"]["outer_hard_envelope"]
            inner = stage["empirical_exploration"]["inner_probe_issue_clearance"]
            caps = stage["empirical_exploration"]["post_successor_step_caps"]
            for index, state in enumerate(raw_states):
                if state["time_ms"] != stage["takeover_time_ms"] + index:
                    failures.append(f"TIME:{spec['rollout_id']}:{index}")
                if set(state.get("artifact_sha256", {})) != set(ARTIFACTS):
                    failures.append(f"ARTIFACT_SET:{spec['rollout_id']}:{index}")
                if len(state["actual_current_decimal_a_tsc"]) != 14 or len(state["wire_current_a"]) != 48:
                    failures.append(f"STATE_VECTOR_LENGTH:{spec['rollout_id']}:{index}")
                if not state["r_inner_m"] <= state["r_geo_m"] <= state["r_outer_m"]:
                    failures.append(f"LIMITER:{spec['rollout_id']}:{index}")
                if abs(state["r_geo_m"] - raw_states[0]["r_geo_m"]) > outer["r_geo_m"]:
                    failures.append(f"OUTER_R:{spec['rollout_id']}:{index}")
                if abs(state["z_geo_m"] - raw_states[0]["z_geo_m"]) > outer["z_geo_m"]:
                    failures.append(f"OUTER_Z:{spec['rollout_id']}:{index}")
                if raw_states[0]["ip_a"] * state["ip_a"] <= 0 or abs(state["ip_a"] - raw_states[0]["ip_a"]) > outer["ip_fraction"] * abs(raw_states[0]["ip_a"]):
                    failures.append(f"OUTER_IP:{spec['rollout_id']}:{index}")
                for value, low, high in zip(state["actual_current_decimal_a_tsc"], cfg.min_current_a_tsc, cfg.max_current_a_tsc):
                    if Decimal(value) < Decimal(str(low)) or Decimal(value) > Decimal(str(high)):
                        failures.append(f"ABSOLUTE_CURRENT:{spec['rollout_id']}:{index}")
            probe_state = raw_states[spec["pulse_issue_step"]]
            if abs(probe_state["r_geo_m"] - raw_states[0]["r_geo_m"]) > inner["r_geo_m"]:
                failures.append(f"PROBE_CLEARANCE_R:{spec['rollout_id']}")
            if abs(probe_state["z_geo_m"] - raw_states[0]["z_geo_m"]) > inner["z_geo_m"]:
                failures.append(f"PROBE_CLEARANCE_Z:{spec['rollout_id']}")
            if abs(probe_state["ip_a"] - raw_states[0]["ip_a"]) > inner["ip_fraction"] * abs(raw_states[0]["ip_a"]):
                failures.append(f"PROBE_CLEARANCE_IP:{spec['rollout_id']}")
            for index, action in enumerate(expected["actions"]):
                if tuple(raw_states[index]["active_command_card15_fields"]) != tuple(action["expected_card15_fields"]):
                    failures.append(f"CARD15:{spec['rollout_id']}:{index}")
                assert_exact_slew(
                    raw_states[index]["actual_current_decimal_a_tsc"],
                    raw_states[index + 1]["actual_current_decimal_a_tsc"],
                    name=f"id2a.audit.observed.{spec['rollout_id']}.{index}",
                )
                if abs(raw_states[index + 1]["r_geo_m"] - raw_states[index]["r_geo_m"]) > caps["r_geo_m"]:
                    failures.append(f"EMPIRICAL_STEP_R:{spec['rollout_id']}:{index}")
                if abs(raw_states[index + 1]["z_geo_m"] - raw_states[index]["z_geo_m"]) > caps["z_geo_m"]:
                    failures.append(f"EMPIRICAL_STEP_Z:{spec['rollout_id']}:{index}")
                if abs(raw_states[index + 1]["ip_a"] - raw_states[index]["ip_a"]) > caps["ip_a"]:
                    failures.append(f"EMPIRICAL_STEP_IP:{spec['rollout_id']}:{index}")
            mismatch = _compare_compact(raw, compact, stage)
            failures.extend(f"COMPACT:{spec['rollout_id']}:{value}" for value in mismatch)
        rows.append(raw)
    inventory = _inventory(run_dir, specs, stage)
    if inventory["missing_required_artifacts"] or inventory["required_artifact_files"] != stage["completed_required_artifact_files"]:
        failures.append("RAW_INVENTORY")
    for key in ("required_artifact_files", "required_artifact_bytes", "required_artifact_inventory_sha256"):
        if inventory[key] != primary.get(key):
            failures.append(f"PRIMARY_INVENTORY:{key}")
    support = lag_support(streams, stage)
    metrics = scientific_metrics(rows, stage) if len(rows) == stage["rollouts"] and all(len(row["states"]) == stage["horizon_steps"] + 1 for row in rows) else None
    if support != primary.get("virtual_action_lag_support"):
        failures.append("INPUT_SUPPORT_RECOMPUTATION")
    if metrics is not None and _numeric_max_difference(metrics, primary.get("scientific_metrics")) > 1e-12:
        failures.append("SCIENTIFIC_METRICS_RECOMPUTATION")
    comparisons = []
    if metrics is not None:
        from scripts.rgeo_zgeo_1ms_id0_vector_tail import compare_rows
        for context in (row["context_id"] for row in stage["contexts"]):
            selected = [row for row in rows if row["context_id"] == context and row["direction_id"] == "p09_half_exact_center" and row["sign"] == "minus" and row["duration_issues"] == 4]
            comparisons.append({"pair_id": f"{context}:p09_minus:d4", **compare_rows(selected[0], selected[1], stage)})
    repeatable = bool(comparisons) and all(row["passed"] for row in comparisons)
    if _numeric_max_difference(comparisons, primary.get("repeatability_comparisons")) > 1e-12:
        failures.append("REPEATABILITY_RECOMPUTATION")
    for key, expected in {
        "rollouts_completed": stage["rollouts"], "reset_calls": stage["maximum_reset_calls"],
        "advance_attempts": stage["maximum_advance_attempts"], "plant_advance_gotsc_calls": stage["maximum_gotsc_calls"],
        "verified_plant_advances": stage["maximum_verified_plant_advances"],
    }.items():
        if primary.get(key) != expected:
            failures.append(f"PRIMARY_COUNTER:{key}")
    expected_route = route_for(stage, True, not inventory["missing_required_artifacts"], repeatable, support["passed"], metrics)
    if primary.get("route") != expected_route or primary.get("passed") != (expected_route == stage["routes"]["pass"]):
        failures.append("PRIMARY_ROUTE_OR_VERDICT")
    passed = not failures
    result = {
        "schema_version": SCHEMA, "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256, "audit_passed": passed,
        "failures": list(dict.fromkeys(failures)), "raw_states_reparsed": sum(len(row["states"]) for row in rows),
        "rollouts_reparsed": len(rows), "repeatability_passed": repeatable,
        "virtual_action_lag_support": support, "scientific_metrics": metrics,
        "recomputed_scientific_route": expected_route,
        "maximum_numeric_difference_vs_primary": None if metrics is None else _numeric_max_difference(metrics, primary.get("scientific_metrics")),
        **inventory,
        "plant_advances": 0, "model_fit_or_training": 0, "holdout_records_read": 0,
    }
    output = run_dir / "independent_audit.json"
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-config", type=Path, default=ROOT / "configs/rgeo_zgeo_1ms_id2a_duration_history_development.json")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    result = audit(args.stage_config.resolve(), args.run_dir.resolve(), args.source_revision)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
