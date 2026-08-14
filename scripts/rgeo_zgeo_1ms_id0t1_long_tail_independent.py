#!/usr/bin/env python3
"""Independent raw-directory audit for the frozen 1 ms ID-0T1 campaign."""

from __future__ import annotations

import argparse
from decimal import Decimal
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

from scripts import rgeo_zgeo_1ms_id0_vector_tail_independent as raw  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    Card15Target, assert_exact_slew, decimal_single_turn_currents_a, quantize_target,
)
from tsc_rzip_rllib.core.runner import TSCConfig  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-id0t1-long-tail-v1-independent"
PRIMARY_SCHEMA = "rgeo-zgeo-1ms-id0t1-long-tail-v1"
CONFIG_SHA256 = "2b5137284435845587e6d93ed9f1cc9736e4bef43ded17da26c6e02cf5356df3"
ARTIFACTS = ("inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv", "sprsina")


def _inside_root(path: Path, label: str) -> Path:
    result = path.resolve()
    if not result.is_relative_to(ROOT.resolve()):
        raise ValueError(f"{label} leaves repository: {path}")
    return result


def _sha(path: Path) -> str:
    return raw._sha(path)


def _specs(stage: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        {"rollout_id": f"baseline_q0_r{repeat}", "context_id": "baseline",
         "direction_id": None, "sign": None, "repeat_index": repeat,
         "pulse_issue_step": None, "return_issue_step": None}
        for repeat in range(2)
    ]
    context = stage["context"]
    for direction in stage["directions"]:
        for sign in ("plus", "minus"):
            rows.append({
                "rollout_id": f"early_{direction['direction_id']}_{sign}_r0",
                "context_id": context["context_id"], "direction_id": direction["direction_id"],
                "sign": sign, "repeat_index": 0,
                "pulse_issue_step": context["pulse_issue_step"],
                "return_issue_step": context["return_issue_step"],
            })
    return rows


def _target(fields: Sequence[str], cfg: TSCConfig) -> Card15Target:
    exact = decimal_single_turn_currents_a(tuple(value.strip() for value in fields), cfg.turns_tsc, name="id0t1.audit.target")
    return Card15Target(tuple(fields), tuple(float(value) for value in exact))


def _stream(stage: dict[str, Any], cfg: TSCConfig, spec: dict[str, Any], q0: Card15Target) -> list[Card15Target]:
    output = [q0] * stage["horizon_steps"]
    if spec["pulse_issue_step"] is not None:
        direction = next(row for row in stage["directions"] if row["direction_id"] == spec["direction_id"])
        output[spec["pulse_issue_step"]] = _target(direction[f"{spec['sign']}_card15_fields"], cfg)
    return output


def _compare_prefix(left: dict[str, Any], right: dict[str, Any], stage: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    maxima = {"geometry_m": 0.0, "ip_a": 0.0, "coil_a": 0.0, "wire_a": 0.0}
    if left["actions"] != right["actions"]:
        failures.append("ACTION_STREAM")
    if len(left["states"]) != len(right["states"]):
        failures.append("STATE_COUNT")
    for index, (a, b) in enumerate(zip(left["states"], right["states"])):
        if a["time_ms"] != b["time_ms"]:
            failures.append(f"TIME:{index}")
        maxima["geometry_m"] = max(maxima["geometry_m"], *(abs(a[key] - b[key]) for key in ("r_geo_m", "z_geo_m", "r_mid_m")))
        maxima["ip_a"] = max(maxima["ip_a"], abs(a["ip_a"] - b["ip_a"]))
        maxima["coil_a"] = max(maxima["coil_a"], raw._maxdiff(a["actual_current_decimal_a_tsc"], b["actual_current_decimal_a_tsc"]))
        maxima["wire_a"] = max(maxima["wire_a"], raw._maxdiff(a["wire_current_a"], b["wire_current_a"]))
        for name in stage["semantic_artifacts"]:
            # The raw state directory's inputa has been rewritten to the
            # outgoing issue at that state, while the compact reference hash
            # was captured before that rewrite.  Outgoing inputa is audited
            # independently against the frozen Card15 stream below.
            if name == "inputa":
                continue
            if a["artifact_sha256"].get(name) != b["artifact_sha256"].get(name):
                failures.append(f"SEMANTIC_ARTIFACT:{index}:{name}")
    for key, value in maxima.items():
        if value > stage["prefix_match"][key]:
            failures.append(key.upper())
    return {"passed": not failures, "failures": list(dict.fromkeys(failures)), "maximum_absolute_difference": maxima}


def _source_preissue_active_command(references: dict[str, dict[str, Any]]) -> list[str]:
    commands = {
        tuple(row["states"][0]["active_command_decimal_a_tsc"])
        for row in references.values()
    }
    if len(commands) != 1:
        raise ValueError("reference source active command is not unique")
    command = list(next(iter(commands)))
    if len(command) != 14:
        raise ValueError("reference source active command is not length 14")
    return command


def _baseline(rows: Sequence[dict[str, Any]]) -> list[dict[str, float]]:
    selected = [row for row in rows if row["context_id"] == "baseline"]
    if len(selected) != 2:
        raise ValueError("two baselines required")
    return [{key: float(np.mean([row["states"][index][key] for row in selected]))
             for key in ("r_geo_m", "z_geo_m", "ip_a")} for index in range(33)]


def _metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    baseline = _baseline(rows)
    gates = stage["scientific_gates"]
    first, last = gates["peak_response_states"]
    arm_metrics = []
    for row in rows:
        if row["context_id"] == "baseline":
            continue
        response = np.asarray([
            [state["r_geo_m"] - base["r_geo_m"], state["z_geo_m"] - base["z_geo_m"], state["ip_a"] - base["ip_a"]]
            for state, base in zip(row["states"], baseline)
        ], dtype=float)
        norms = np.linalg.norm(response[:, :2], axis=1)
        peak = float(np.max(norms[first:last + 1]))
        terminal = gates["tail_terminal_state_index"]
        arm_metrics.append({
            "rollout_id": row["rollout_id"], "direction_id": row["direction_id"], "sign": row["sign"],
            "peak_rz_norm_m_states_3_32": peak, "terminal_state_index": terminal,
            "terminal_rz_norm_m": float(norms[terminal]),
            "terminal_peak_fraction": float(norms[terminal] / peak) if peak else math.inf,
            "terminal_absolute_ip_response_a": float(abs(response[terminal, 2])),
        })
    passed = all(
        row["terminal_rz_norm_m"] <= gates["tail_terminal_maximum_rz_norm_m"]
        and row["terminal_peak_fraction"] <= gates["tail_terminal_maximum_peak_fraction"]
        and row["terminal_absolute_ip_response_a"] <= gates["tail_terminal_maximum_abs_ip_a"]
        for row in arm_metrics
    )
    return {"arm_metrics": arm_metrics, "tail_passed": passed}


def _expected_route(stage: dict[str, Any], prefix_ok: bool, metrics: dict[str, Any]) -> str:
    if not prefix_ok:
        return stage["routes"]["prefix_match_fail"]
    return stage["routes"]["pass"] if metrics["tail_passed"] else stage["routes"]["tail_horizon_fail"]


def audit(stage_path: Path, run_dir: Path, source_revision: str, *, output_name: str = "independent_audit.json") -> dict[str, Any]:
    failures: list[str] = []
    stage_path = _inside_root(stage_path, "stage config")
    run_dir = _inside_root(run_dir, "run dir")
    stage = json.loads(stage_path.read_text(encoding="utf-8"))
    if _sha(stage_path) != CONFIG_SHA256 or stage.get("schema_version") != PRIMARY_SCHEMA:
        failures.append("STAGE_IDENTITY")
    for label in ("id0_result_report", "id0_result", "id0_independent"):
        row = stage["evidence"][label]
        path = _inside_root(ROOT / row["path"], label)
        if not path.is_file() or _sha(path) != row["sha256"]:
            failures.append(f"EVIDENCE:{label}")
    references = {}
    for row in stage["evidence"]["reference_records"]:
        path = _inside_root(ROOT / row["path"], "reference")
        if not path.is_file() or _sha(path) != row["sha256"]:
            failures.append(f"REFERENCE_HASH:{path.name}")
        else:
            references[path.stem] = json.loads(path.read_text(encoding="utf-8"))
    source_preissue_active_command = _source_preissue_active_command(references)
    base = _inside_root(ROOT / stage["base_tsc_config"], "base config")
    if _sha(base) != stage["evidence"]["base_tsc_config_sha256"]:
        failures.append("BASE_IDENTITY")
    cfg = TSCConfig.from_json(base)
    primary_path = run_dir / "result.json"
    primary = json.loads(primary_path.read_text(encoding="utf-8")) if primary_path.is_file() else {}
    if not primary:
        failures.append("PRIMARY_RESULT_MISSING")
    specs = _specs(stage)
    rollout_root = run_dir / "rollouts"
    actual_dirs = sorted(path.name for path in rollout_root.iterdir() if path.is_dir()) if rollout_root.is_dir() else []
    if actual_dirs != sorted(row["rollout_id"] for row in specs):
        failures.append("ROLLOUT_DIRECTORY_SET")
    rows = []
    inventory_lines: list[str] = []
    try:
        for spec in specs:
            folder = rollout_root / spec["rollout_id"]
            state_dirs = sorted(path.name for path in folder.iterdir() if path.is_dir() and path.name.endswith("ms"))
            expected_dirs = [f"{time}ms" for time in range(1100, 1133)]
            if state_dirs != expected_dirs:
                raise ValueError(f"state directory set:{spec['rollout_id']}")
            states = [raw._state(folder / f"{time}ms", cfg) for time in range(1100, 1133)]
            q0 = quantize_target(tuple(float(value) for value in states[0]["actual_current_decimal_a_tsc"]), cfg.turns_tsc)
            targets = _stream(stage, cfg, spec, q0)
            actions = []
            # state1100/inputa in the retained raw tree is the outgoing issue0
            # q0 command.  The pre-issue source command is recoverable from the
            # frozen source compacts and is required to preserve the real
            # 1e-5 A source-to-q0 settling action.
            previous_command = source_preissue_active_command
            source = states[0]
            outer = stage["empirical_exploration"]["outer_hard_envelope"]
            inner = stage["empirical_exploration"]["inner_pulse_issue_clearance"]
            caps = stage["empirical_exploration"]["post_successor_step_caps"]
            for index, state in enumerate(states):
                if not state["r_inner_m"] <= state["r_geo_m"] <= state["r_outer_m"]:
                    failures.append(f"LIMITER:{spec['rollout_id']}:{index}")
                if abs(state["r_geo_m"] - source["r_geo_m"]) > outer["r_geo_m"]:
                    failures.append(f"OUTER_R:{spec['rollout_id']}:{index}")
                if abs(state["z_geo_m"] - source["z_geo_m"]) > outer["z_geo_m"]:
                    failures.append(f"OUTER_Z:{spec['rollout_id']}:{index}")
                if source["ip_a"] * state["ip_a"] <= 0 or abs(state["ip_a"] - source["ip_a"]) > outer["ip_fraction"] * abs(source["ip_a"]):
                    failures.append(f"OUTER_IP:{spec['rollout_id']}:{index}")
                if any(float(value) < low or float(value) > high for value, low, high in zip(state["actual_current_decimal_a_tsc"], cfg.min_current_a_tsc, cfg.max_current_a_tsc)):
                    failures.append(f"ACTUAL_CURRENT_LIMIT:{spec['rollout_id']}:{index}")
            if spec["pulse_issue_step"] is not None:
                pulse = states[spec["pulse_issue_step"]]
                if abs(pulse["r_geo_m"] - source["r_geo_m"]) > inner["r_geo_m"]:
                    failures.append(f"PULSE_CLEARANCE_R:{spec['rollout_id']}")
                if abs(pulse["z_geo_m"] - source["z_geo_m"]) > inner["z_geo_m"]:
                    failures.append(f"PULSE_CLEARANCE_Z:{spec['rollout_id']}")
                if abs(pulse["ip_a"] - source["ip_a"]) > inner["ip_fraction"] * abs(source["ip_a"]):
                    failures.append(f"PULSE_CLEARANCE_IP:{spec['rollout_id']}")
            for issue, target in enumerate(targets):
                if raw._fields(folder / f"{1100 + issue}ms" / "inputa") != target.card15_fields:
                    failures.append(f"CARD15:{spec['rollout_id']}:{issue}")
                exact = decimal_single_turn_currents_a(tuple(value.strip() for value in target.card15_fields), cfg.turns_tsc, name="audit.target")
                maximum = assert_exact_slew(previous_command, exact, name=f"audit.issue.{spec['rollout_id']}.{issue}")
                observed = assert_exact_slew(states[issue]["actual_current_decimal_a_tsc"], states[issue + 1]["actual_current_decimal_a_tsc"], name=f"audit.observed.{spec['rollout_id']}.{issue}")
                if abs(states[issue + 1]["r_geo_m"] - states[issue]["r_geo_m"]) > caps["r_geo_m"]:
                    failures.append(f"EMPIRICAL_STEP_R:{spec['rollout_id']}:{issue}")
                if abs(states[issue + 1]["z_geo_m"] - states[issue]["z_geo_m"]) > caps["z_geo_m"]:
                    failures.append(f"EMPIRICAL_STEP_Z:{spec['rollout_id']}:{issue}")
                if abs(states[issue + 1]["ip_a"] - states[issue]["ip_a"]) > caps["ip_a"]:
                    failures.append(f"EMPIRICAL_STEP_IP:{spec['rollout_id']}:{issue}")
                actions.append({"issue_step": issue, "issue_time_ms": 1100 + issue,
                                "effect_state_index": issue + 1, "effect_time_ms": 1101 + issue,
                                "expected_card15_fields": list(target.card15_fields),
                                "target_current_a_tsc": list(target.current_a_tsc),
                                "maximum_issued_delta_a": maximum})
                states[issue + 1]["maximum_observed_delta_a"] = observed
                previous_command = exact
            if tuple(states[-1]["active_command_card15_fields"]) != q0.card15_fields:
                failures.append(f"FINAL_ACTIVE_CARD15:{spec['rollout_id']}")
            rows.append({**spec, "states": states, "actions": actions})
            for state in states:
                for name in ARTIFACTS:
                    path = folder / f"{state['time_ms']}ms" / name
                    label = path.relative_to(run_dir).as_posix()
                    inventory_lines.append(f"{label}\t{path.stat().st_size}\t{_sha(path)}")
    except Exception as exc:
        failures.append(f"RAW:{type(exc).__name__}:{exc}")
    comparisons = metrics = expected_route = None
    if len(rows) == 8 and not any(item.startswith("RAW:") for item in failures):
        comparisons = []
        for row in rows:
            prefix = {**row, "states": row["states"][:21], "actions": row["actions"][:20]}
            keys = ("baseline_q0_r0", "baseline_q0_r1") if row["context_id"] == "baseline" else tuple(
                f"early_{row['direction_id']}_{row['sign']}_r{repeat}" for repeat in range(2)
            )
            for key in keys:
                comparisons.append({"new_rollout_id": row["rollout_id"], "reference_rollout_id": key,
                                    **_compare_prefix(prefix, references[key], stage)})
        prefix_ok = len(comparisons) == 16 and all(row["passed"] for row in comparisons)
        metrics = _metrics(rows, stage)
        expected_route = _expected_route(stage, prefix_ok, metrics)
        payload = "".join(f"{line}\n" for line in sorted(inventory_lines)).encode()
        inventory_sha = hashlib.sha256(payload).hexdigest()
        total_bytes = sum(int(line.split("\t")[1]) for line in inventory_lines)
        if len(inventory_lines) != 1320 or primary.get("required_artifact_files") != 1320:
            failures.append("INVENTORY_COUNT")
        if primary.get("required_artifact_inventory_sha256") != inventory_sha or primary.get("required_artifact_bytes") != total_bytes:
            failures.append("INVENTORY_IDENTITY")
        if primary.get("route") != expected_route:
            failures.append("PRIMARY_ROUTE")
        if primary.get("source_revision") != source_revision or primary.get("schema_version") != PRIMARY_SCHEMA:
            failures.append("PRIMARY_IDENTITY")
        if primary.get("reset_calls") != 8 or primary.get("advance_attempts") != 256 or primary.get("plant_advance_gotsc_calls") != 256 or primary.get("verified_plant_advances") != 256:
            failures.append("PRIMARY_COUNTERS")
        if json.dumps(primary.get("prefix_comparisons"), sort_keys=True, allow_nan=False) != json.dumps(comparisons, sort_keys=True, allow_nan=False):
            failures.append("PRIMARY_PREFIX")
        if json.dumps(primary.get("scientific_metrics"), sort_keys=True, allow_nan=False) != json.dumps(metrics, sort_keys=True, allow_nan=False):
            failures.append("PRIMARY_METRICS")
    failures = list(dict.fromkeys(failures))
    result = {
        "schema_version": SCHEMA, "source_revision": source_revision,
        "audit_passed": not failures, "passed": not failures,
        "route": "ONE_MS_ID0T1_INDEPENDENT_AUDIT_PASS" if not failures else "ONE_MS_ID0T1_INDEPENDENT_AUDIT_FAIL",
        "failures": failures, "raw_rollouts": len(rows), "raw_states": sum(len(row["states"]) for row in rows),
        "recomputed_scientific_route": expected_route, "prefix_comparisons": comparisons,
        "scientific_metrics": metrics, "primary_scientific_passed": primary.get("passed"),
        "raw_inputa_semantics": "outgoing_issue_verified_against_card15_not_compared_to_prewrite_compact_hash",
        "issue0_previous_command_semantics": "frozen_unique_preissue_source_command_from_id0_reference_compacts",
        "claim_boundary": "independent_raw_state32_tail_recomputation_not_model_controller_or_safety_qualification",
    }
    if output_name not in ("independent_audit.json", "independent_audit_hotfix.json"):
        raise ValueError("invalid independent audit output name")
    destination = run_dir / output_name
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite {destination}")
    destination.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output-name", default="independent_audit.json")
    args = parser.parse_args()
    result = audit(args.stage_config.resolve(), args.run_dir.resolve(), args.source_revision, output_name=args.output_name)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
