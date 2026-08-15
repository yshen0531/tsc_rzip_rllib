#!/usr/bin/env python3
"""Independent raw reparse for the ID2B0 readiness audit."""

from __future__ import annotations

import argparse
from decimal import Decimal
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
    SCHEMA as ID2A_SCHEMA,
    load as load_id2a,
    rollout_specs,
    targets_and_streams,
)
from scripts.rgeo_zgeo_1ms_id2b0_model_readiness_audit import (  # noqa: E402
    COMPLETE_ROUTE,
    CONFIG_SHA256,
    ID2A_SOURCE_REVISION,
    SCHEMA as PRIMARY_SCHEMA,
    SUPPORT_FAIL_ROUTE,
    analyze_rows,
    audit_old_id2b,
    inside,
    load_config,
    read_json,
    sha256_file,
)
from scripts.rgeo_zgeo_1ms_nr1_qualification import _source  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    assert_exact_slew,
    decimal_single_turn_currents_a,
)


SCHEMA = "rgeo-zgeo-1ms-id2b0-model-readiness-audit-independent-v1"


def audit(
    repo_root: Path,
    config_path: Path,
    id2a_run_dir: Path,
    output_dir: Path,
    source_revision: str,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    config_path = inside(repo_root, config_path, "config")
    id2a_run_dir = inside(repo_root, id2a_run_dir, "ID2A run directory")
    output_dir = inside(repo_root, output_dir, "ID2B0 output directory")
    config = load_config(repo_root, config_path)
    primary_path = output_dir / "result.json"
    if not primary_path.is_file():
        raise ValueError("missing ID2B0 primary result")
    primary = read_json(primary_path)
    if primary.get("schema_version") != PRIMARY_SCHEMA or primary.get("source_revision") != source_revision:
        raise ValueError("ID2B0 primary identity mismatch")
    if primary.get("config_sha256") != CONFIG_SHA256:
        raise ValueError("ID2B0 primary config mismatch")

    stage_path = inside(repo_root, repo_root / config["id2a_stage_config"]["path"], "ID2A stage config")
    stage, cfg, _ = load_id2a(stage_path)
    source = _source(cfg)
    streams = targets_and_streams(stage, cfg, source)
    stream_by_id = {row["rollout_id"]: row for row in streams}
    specs = rollout_specs(stage)
    failures: list[str] = []
    raw_rows: list[dict[str, Any]] = []
    raw_states_reparsed = 0

    for spec in specs:
        compact_path = id2a_run_dir / f"{spec['rollout_id']}.json"
        if not compact_path.is_file():
            failures.append(f"MISSING_COMPACT:{spec['rollout_id']}")
            continue
        compact = read_json(compact_path)
        states: list[dict[str, Any]] = []
        for state_index in range(stage["horizon_steps"] + 1):
            folder = id2a_run_dir / "rollouts" / spec["rollout_id"] / f"{stage['takeover_time_ms'] + state_index}ms"
            try:
                state = _state(folder, cfg)
            except Exception as exc:
                failures.append(f"RAW_STATE:{spec['rollout_id']}:{state_index}:{type(exc).__name__}:{exc}")
                break
            if set(state.get("artifact_sha256", {})) != set(ARTIFACTS):
                failures.append(f"ARTIFACT_SET:{spec['rollout_id']}:{state_index}")
            if len(state.get("actual_current_decimal_a_tsc", [])) != 14:
                failures.append(f"COIL_LENGTH:{spec['rollout_id']}:{state_index}")
            if len(state.get("wire_current_a", [])) != 48:
                failures.append(f"WIRE_LENGTH:{spec['rollout_id']}:{state_index}")
            states.append(state)
            raw_states_reparsed += 1

        expected = stream_by_id[spec["rollout_id"]]
        actions: list[dict[str, Any]] = []
        previous_command = source["active_command_decimal_a_tsc"]
        for issue_index, frozen in enumerate(expected["actions"]):
            action = dict(frozen)
            exact = decimal_single_turn_currents_a(
                tuple(value.strip() for value in frozen["expected_card15_fields"]),
                cfg.turns_tsc,
                name=f"id2b0.independent.{spec['rollout_id']}.{issue_index}",
            )
            action["maximum_issued_delta_a"] = assert_exact_slew(
                previous_command,
                exact,
                name=f"id2b0.independent.issue.{spec['rollout_id']}.{issue_index}",
            )
            previous_command = exact
            actions.append(action)
        raw = {
            **spec,
            "schema_version": ID2A_SCHEMA,
            "source_revision": ID2A_SOURCE_REVISION,
            "passed": len(states) == stage["horizon_steps"] + 1,
            "states": states,
            "actions": actions[: max(0, len(states) - 1)],
        }
        if len(states) == stage["horizon_steps"] + 1:
            mismatch = _compare_compact(raw, compact, stage)
            failures.extend(f"COMPACT:{spec['rollout_id']}:{value}" for value in mismatch)
            for state_index, state in enumerate(states):
                if state["time_ms"] != stage["takeover_time_ms"] + state_index:
                    failures.append(f"TIME:{spec['rollout_id']}:{state_index}")
                if not state["r_inner_m"] <= state["r_geo_m"] <= state["r_outer_m"]:
                    failures.append(f"LIMITER:{spec['rollout_id']}:{state_index}")
                for value, low, high in zip(
                    state["actual_current_decimal_a_tsc"],
                    cfg.min_current_a_tsc,
                    cfg.max_current_a_tsc,
                ):
                    if Decimal(value) < Decimal(str(low)) or Decimal(value) > Decimal(str(high)):
                        failures.append(f"ABSOLUTE_CURRENT:{spec['rollout_id']}:{state_index}")
        raw_rows.append(raw)

    analysis = None
    old_audit = None
    if len(raw_rows) == 42 and all(len(row["states"]) == 33 for row in raw_rows):
        analysis = analyze_rows(raw_rows, config, stage)
        old_audit = audit_old_id2b(repo_root, config, analysis)
        if _numeric_max_difference(analysis, primary.get("analysis")) > 1e-12:
            failures.append("PRIMARY_ANALYSIS_RECOMPUTATION")
        if _numeric_max_difference(old_audit, primary.get("superseded_id2b_v1_audit")) > 1e-12:
            failures.append("PRIMARY_ID2B_V1_AUDIT_RECOMPUTATION")
    else:
        failures.append("RAW_MATRIX_INCOMPLETE")

    expected_route = None
    expected_passed = False
    if analysis is not None:
        expected_passed = not analysis["exact_causal_collisions"]
        expected_route = COMPLETE_ROUTE if expected_passed else SUPPORT_FAIL_ROUTE
        if primary.get("route") != expected_route or primary.get("passed") != expected_passed:
            failures.append("PRIMARY_ROUTE_OR_VERDICT")
    if primary.get("counters", {}).get("plant_advances") != 0 or primary.get("counters", {}).get("models_fit_or_trained") != 0:
        failures.append("PRIMARY_ZERO_EXECUTION_COUNTER")
    if primary.get("counters", {}).get("holdout_records_read") != 0:
        failures.append("PRIMARY_HOLDOUT_COUNTER")

    result = {
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "config_sha256": CONFIG_SHA256,
        "audit_passed": not failures,
        "failures": list(dict.fromkeys(failures)),
        "primary_result_sha256": sha256_file(primary_path),
        "raw_rollouts_reparsed": len(raw_rows),
        "raw_states_reparsed": raw_states_reparsed,
        "maximum_numeric_difference_vs_primary": None if analysis is None else _numeric_max_difference(analysis, primary.get("analysis")),
        "recomputed_route": expected_route,
        "recomputed_scientific_passed": expected_passed,
        "analysis": analysis,
        "superseded_id2b_v1_audit": old_audit,
        "counters": {
            "plant_advances": 0,
            "tsc_calls": 0,
            "models_fit_or_trained": 0,
            "holdout_records_read": 0,
        },
    }
    output = output_dir / "independent_audit.json"
    if output.exists():
        raise FileExistsError(f"refusing to overwrite independent audit: {output}")
    output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path, default=Path("configs/rgeo_zgeo_1ms_id2b0_model_readiness_audit.json"))
    parser.add_argument("--id2a-run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    run_dir = args.id2a_run_dir if args.id2a_run_dir.is_absolute() else root / args.id2a_run_dir
    output_dir = args.output_dir if args.output_dir.is_absolute() else root / args.output_dir
    result = audit(root, config_path, run_dir, output_dir, args.source_revision)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
