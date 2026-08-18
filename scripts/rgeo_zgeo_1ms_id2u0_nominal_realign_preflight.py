#!/usr/bin/env python3
"""Zero-TSC ID-2U0 nominal realignment and exact action-grammar audit."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import rgeo_zgeo_1ms_id2c1_active_nominal_vector_search as c1


CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2u0_nominal_realign_preflight.json"
CONFIG_SHA256 = "0f834ba5f2ae718ec28ad49fd958a66148009054743efdb1caa48557e243effb"
SCHEMA = "rgeo-zgeo-1ms-id2u0-nominal-realign-preflight-result-v1"


class IntegrityError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inside(path: Path, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError as exc:
        raise IntegrityError(f"{label} escapes repository") from exc
    return resolved


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise IntegrityError(f"{path} must contain an object")
    return value


def require(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise IntegrityError(f"{label}: expected {expected!r}, got {actual!r}")


def checked_file(row: dict[str, Any], label: str) -> Path:
    path = inside(ROOT / row["path"], label)
    require(sha256(path), row["sha256"], f"{label} hash")
    return path


def load_stage(path: Path = CONFIG) -> tuple[dict[str, Any], Any, dict[str, Any], dict[str, Any]]:
    path = inside(path, "ID2U0 config")
    require(sha256(path), CONFIG_SHA256, "ID2U0 config hash")
    stage = read_json(path)
    require(stage.get("schema_version"),
            "rgeo-zgeo-1ms-id2u0-nominal-realign-preflight-v1", "schema")
    require(stage.get("identity"), stage.get("schema_version"), "identity")
    require(stage.get("execution_contract"),
            "server_only_zero_new_tsc_zero_fit_nominal_realign_and_action_grammar_audit",
            "execution contract")
    for key in ("new_tsc_calls", "reset_calls", "plant_advances",
                "models_fit_or_trained", "holdout_records_read"):
        require(int(stage[key]), 0, key)
    if not all(stage["forbidden"].values()):
        raise IntegrityError("forbidden-use contract weakened")
    checked_file(stage["design"], "design")
    checked_file(stage["route_review"], "route review")
    c1_config = checked_file(stage["id2c1"]["config"], "ID2C1 config")
    c1_compact_path = checked_file(stage["id2c1"]["compact"], "ID2C1 compact")
    c1_compact = read_json(c1_compact_path)
    require(c1_compact.get("primary_route"),
            stage["id2c1"]["compact"]["required_route"], "ID2C1 route")
    require(c1_compact.get("primary_passed"), True, "ID2C1 primary")
    require(c1_compact.get("independent_audit_passed"), True, "ID2C1 independent")
    require(c1_compact["phase_a"]["selected_nominal_candidate_id"],
            stage["nominal_contract"]["selected_candidate_id"], "selected nominal")

    p1_config = checked_file(stage["id2p1"]["config"], "ID2P1 config")
    del p1_config
    p1_dir = inside(ROOT / stage["id2p1"]["directory"], "ID2P1 directory")
    require(sha256(p1_dir / "result.json"), stage["id2p1"]["result_sha256"],
            "ID2P1 result hash")
    require(sha256(p1_dir / "independent_raw_audit.json"),
            stage["id2p1"]["independent_sha256"], "ID2P1 independent hash")
    require(read_json(p1_dir / "result.json").get("passed"), True, "ID2P1 result")
    require(read_json(p1_dir / "independent_raw_audit.json").get("audit_passed"),
            True, "ID2P1 audit")

    for key in ("id2s1", "id2s2"):
        row = stage[key]
        path_value = inside(ROOT / row["result"], key)
        require(sha256(path_value), row["sha256"], f"{key} hash")
        value = read_json(path_value)
        require(value.get("route"), row["required_route"], f"{key} route")
        require(value.get("passed"), True, f"{key} passed")

    t1_dir = inside(ROOT / stage["id2t1"]["directory"], "ID2T1 directory")
    checked_file(stage["id2t1"]["config"], "ID2T1 config")
    require(sha256(t1_dir / "result.json"), stage["id2t1"]["result_sha256"],
            "ID2T1 result hash")
    require(sha256(t1_dir / "independent_raw_audit.json"),
            stage["id2t1"]["independent_sha256"], "ID2T1 independent hash")
    t1_result = read_json(t1_dir / "result.json")
    require(t1_result.get("route"), stage["id2t1"]["required_route"], "ID2T1 route")
    require(t1_result.get("passed"), False, "ID2T1 must remain FAIL")
    require(read_json(t1_dir / "independent_raw_audit.json").get("audit_passed"),
            True, "ID2T1 audit")

    c1_stage, cfg, source, targets = c1.load(c1_config)
    return stage, cfg, source, targets


def primary_p1_rows(stage: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    folder = inside(ROOT / stage["id2p1"]["directory"], "ID2P1 directory")
    rows: list[dict[str, Any]] = []
    baselines: dict[str, dict[str, Any]] = {}
    for path in sorted(folder.glob("f??__*__r0.json")):
        row = read_json(path)
        if int(row.get("replay_index", -1)) != 0:
            continue
        if row.get("cell_kind") == "baseline":
            baselines[str(row["group_id"])] = row
        elif row.get("cell_kind") == "probe":
            rows.append(row)
    require(len(rows), int(stage["event_gates"]["required_primary_probe_cells"]),
            "P1 primary probe count")
    require(len(baselines), 8, "P1 baseline count")
    return rows, baselines


def rz_response(row: dict[str, Any], baseline: dict[str, Any], state_index: int) -> tuple[float, float]:
    state = row["states"][state_index]
    base = baseline["states"][state_index]
    return (1000.0 * (float(state["r_geo_m"]) - float(base["r_geo_m"])),
            1000.0 * (float(state["z_geo_m"]) - float(base["z_geo_m"])))


def event_map(stage: dict[str, Any]) -> dict[str, Any]:
    rows, baselines = primary_p1_rows(stage)
    samples = []
    for row in rows:
        origin = int(row["probe_issue_step"])
        baseline = baselines[str(row["group_id"])]
        for state_index in range(origin + 1, min(origin + 9, len(row["states"]))):
            dr, dz = rz_response(row, baseline, state_index)
            samples.append({
                "family_id": row["group_id"], "cell_id": row["cell_id"],
                "state_index": state_index, "time_ms": 1100 + state_index,
                "response_r_mm": dr, "response_z_mm": dz,
                "response_norm_mm": math.hypot(dr, dz),
            })
    threshold = float(stage["event_gates"]["large_response_threshold_mm"])
    large = [sample for sample in samples if sample["response_norm_mm"] > threshold]
    non27 = [sample for sample in samples if sample["state_index"] != 27]
    require(len(large), int(stage["event_gates"]["required_large_response_count"]),
            "large event count")
    require({sample["state_index"] for sample in large},
            {int(stage["event_gates"]["required_large_response_state_index"])},
            "large event state")
    maximum_non27 = max(sample["response_norm_mm"] for sample in non27)
    if maximum_non27 > float(stage["event_gates"]["maximum_non_state27_response_mm"]):
        raise IntegrityError("non-state27 response cap changed")
    return {
        "primary_probe_cells": len(rows),
        "response_samples": len(samples),
        "large_response_threshold_mm": threshold,
        "large_response_count": len(large),
        "large_response_state_indices": sorted({sample["state_index"] for sample in large}),
        "maximum_non_state27_response_norm_mm": maximum_non27,
        "large_events": large,
    }


def t1_rows(stage: dict[str, Any]) -> list[dict[str, Any]]:
    folder = inside(ROOT / stage["id2t1"]["directory"], "ID2T1 directory")
    paths = sorted(folder.glob("f03__*__p04_plus_cont_t1.json"))
    require(len(paths), int(stage["id2t1"]["required_rollouts"]), "ID2T1 rollouts")
    return [read_json(path) for path in paths]


def early_late_alignment(stage: dict[str, Any]) -> dict[str, Any]:
    p1_folder = inside(ROOT / stage["id2p1"]["directory"], "ID2P1 directory")
    early = read_json(p1_folder / "f03__p04_plus_i24_d2__r0.json")
    early_base = read_json(p1_folder / "f03__baseline__r0.json")
    s2_folder = inside(ROOT / stage["id2s2"]["result"], "ID2S2 result").parent
    early_response = [rz_response(early, early_base, state) for state in range(25, 29)]
    late_responses = []
    for row in t1_rows(stage):
        reference = read_json(s2_folder / f"{row['reference_rollout_id']}.json")
        late_responses.append([rz_response(row, reference, state) for state in range(31, 35)])
    late_mean = []
    for offset in range(4):
        late_mean.append((
            sum(value[offset][0] for value in late_responses) / len(late_responses),
            sum(value[offset][1] for value in late_responses) / len(late_responses),
        ))
    r_differences = [abs(late_mean[index][0] - early_response[index][0])
                     for index in range(4)]
    if r_differences[1] > float(stage["event_gates"]["maximum_early_late_h2_r_difference_mm"]):
        raise IntegrityError("early/late h2 alignment changed")
    if r_differences[2] < float(stage["event_gates"]["minimum_early_late_h3_r_difference_mm"]):
        raise IntegrityError("early/late return-event contrast changed")
    return {
        "early_issue": 24, "late_issue": 30,
        "early_response_rz_mm": early_response,
        "late_four_response_rz_mm": late_responses,
        "late_mean_response_rz_mm": late_mean,
        "absolute_r_difference_mm": r_differences,
        "classification": "direct_h1_h2_aligned_return_effect_h3_hybrid_contrast",
        "smooth_gain_sign_reversal_claimed": False,
    }


def build_campaign(stage: dict[str, Any], cfg: Any, source: dict[str, Any],
                   targets: dict[str, Any]) -> list[dict[str, Any]]:
    del source
    q0 = targets["q0"]
    p03 = targets["p03:minus"]
    horizon = int(stage["prospective_campaign"]["horizon_steps"])
    streams = []
    for group in stage["prospective_campaign"]["groups"]:
        probe_issue = int(group["probe_issue"])
        nominal_level = int(group["nominal_level"])
        increments = {int(value) for value in group["increment_issues"]}
        if len(increments) != nominal_level or min(increments) < 1 or max(increments) >= probe_issue:
            raise IntegrityError(f"invalid arrival schedule: {group['family_id']}")
        definitions = [("baseline", None, None)]
        definitions.extend((f"{direction}_{sign}", direction, sign)
                           for direction in stage["prospective_campaign"]["directions"]
                           for sign in stage["prospective_campaign"]["signs"])
        for cell_name, direction, sign in definitions:
            level = 0
            sequence = []
            virtual = []
            for issue in range(horizon):
                if issue in increments:
                    level += 1
                if issue == probe_issue + 3:
                    level += 1
                elif issue > probe_issue + 3 and level < 31:
                    level += 1
                target = c1._offset_target(q0, p03, level, cfg,
                                           f"{group['family_id']}.{cell_name}.level{level}")
                marker = [float(level), 0.0, 0.0]
                if direction is not None and probe_issue <= issue < probe_issue + 2:
                    target = c1._translated_target(
                        target, q0, targets[f"{direction}:{sign}"], cfg,
                        f"{group['family_id']}.{cell_name}.probe{issue}")
                    marker[1 if direction == "p04" else 2] = 1.0 if sign == "plus" else -1.0
                sequence.append(target)
                virtual.append(marker)
            if level != min(31, nominal_level + max(0, horizon - (probe_issue + 3))):
                raise IntegrityError(f"unexpected terminal level: {group['family_id']}")
            rollout_id = f"{group['family_id']}__{cell_name}"
            actions = c1._actions(sequence, cfg, rollout_id, virtual)
            maximum = max(float(action["maximum_issued_delta_a"]) for action in actions)
            if maximum > float(stage["nominal_contract"]["maximum_adjacent_coil_delta_a"]):
                raise IntegrityError(f"slew violation: {rollout_id}")
            streams.append({
                "rollout_id": rollout_id, "family_id": group["family_id"],
                "role": group["role"], "arrival": group["arrival"],
                "probe_issue": probe_issue, "nominal_level_at_probe": nominal_level,
                "direction": direction, "sign": sign,
                "probe_duration_issues": 0 if direction is None else 2,
                "increment_issues_before_probe": sorted(increments),
                "maximum_adjacent_coil_delta_a": maximum,
                "actions": actions,
            })
    require(len(streams), len(stage["prospective_campaign"]["groups"]) *
            int(stage["prospective_campaign"]["cells_per_family"]), "stream count")
    return streams


def nominal_lineage(stage: dict[str, Any], cfg: Any, targets: dict[str, Any]) -> dict[str, Any]:
    streams = c1.phase_a_streams(stage=read_json(ROOT / stage["id2c1"]["config"]["path"]),
                                 cfg=cfg, targets=targets)
    selected = next(row for row in streams if row["candidate_id"] ==
                    stage["nominal_contract"]["selected_candidate_id"])
    increments = selected["p03_minus_increment_issues"]
    require(increments, stage["nominal_contract"]["increment_issues"], "nominal increments")
    held = list(selected["targets"][:16]) + [selected["targets"][15]] * 16
    held_actions = c1._actions(held, cfg, "held_after15_audit", [[0.0] * 4 for _ in held])
    return {
        "selected_candidate_id": selected["candidate_id"],
        "moving_increment_issues": increments,
        "moving_actions": selected["actions"],
        "held_after15_actions": held_actions,
        "issue24_level_difference": 24 - 15,
        "issue30_level_difference": 30 - 15,
        "held_corridor_is_selected_nominal": False,
    }


def execute(config: Path = CONFIG) -> dict[str, Any]:
    stage, cfg, source, targets = load_stage(config)
    lineage = nominal_lineage(stage, cfg, targets)
    events = event_map(stage)
    alignment = early_late_alignment(stage)
    streams = build_campaign(stage, cfg, source, targets)
    c1_compact = read_json(ROOT / stage["id2c1"]["compact"]["path"])
    return {
        "schema_version": SCHEMA,
        "stage": stage["stage"],
        "passed": True,
        "route": stage["routes"]["pass"],
        "stage_config_sha256": CONFIG_SHA256,
        "new_tsc_calls": 0, "reset_calls": 0, "plant_advances": 0,
        "models_fit_or_trained": 0, "holdout_records_read": 0,
        "nominal_metrics_from_id2c1": c1_compact["phase_a"],
        "nominal_lineage": lineage,
        "event_map": events,
        "early_late_alignment": alignment,
        "prospective_campaign_streams": streams,
        "family_count": len(stage["prospective_campaign"]["groups"]),
        "stream_count": len(streams),
        "role_counts": {
            role: sum(1 for group in stage["prospective_campaign"]["groups"]
                      if group["role"] == role)
            for role in ("development", "calibration", "blind_holdout")
        },
        "claim_boundary": stage["claim_boundary"],
    }


def write_new(path: Path, value: Any) -> None:
    path = inside(path, "output")
    if path.exists():
        raise IntegrityError(f"refusing overwrite: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
                    encoding="utf-8")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        result = execute(args.config)
        result["source_revision"] = args.source_revision
    except Exception as exc:
        result = {
            "schema_version": SCHEMA, "stage": "ID-2U0", "passed": False,
            "route": "ONE_MS_ID2U0_INPUT_OR_EVIDENCE_FAIL_STOP",
            "failures": [f"{type(exc).__name__}:{exc}"],
            "stage_config_sha256": sha256(args.config) if args.config.exists() else None,
            "source_revision": args.source_revision,
            "new_tsc_calls": 0, "reset_calls": 0, "plant_advances": 0,
            "models_fit_or_trained": 0, "holdout_records_read": 0,
        }
    write_new(args.output, result)
    print(json.dumps({"passed": result["passed"], "route": result["route"]},
                     sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
