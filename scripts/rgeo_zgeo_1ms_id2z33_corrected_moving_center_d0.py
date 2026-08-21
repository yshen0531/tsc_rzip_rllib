#!/usr/bin/env python3
"""Run ID2Z33 with corrected general moving-center branch construction."""

from __future__ import annotations

import argparse
import copy
from decimal import Decimal
import json
from pathlib import Path
import sys
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_id2z32_post_event_delayed_tail_d0 as z32  # noqa: E402

CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z33_corrected_moving_center_d0.json"
CONFIG_SHA256 = "e4503fcd8c7d53cd768e50908af158d893dfd7986a52ecbae5857171f669388f"
SCHEMA = "rgeo-zgeo-1ms-id2z33-corrected-moving-center-d0-result-v1"
ROW_SCHEMA = "rgeo-zgeo-1ms-id2z33-corrected-moving-center-d0-row-v1"
OFFLINE_SCHEMA = "rgeo-zgeo-1ms-id2z33-corrected-moving-center-d0-offline-v1"
_Z32_LOAD = z32.load


def _require(stage: dict[str, Any]) -> None:
    if z32._sha(CONFIG) != CONFIG_SHA256 or stage != z32._read(CONFIG):
        raise ValueError("ID2Z33 frozen config changed")
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2z33-corrected-moving-center-d0-v1",
        "identity": "rgeo-zgeo-1ms-id2z33-corrected-moving-center-d0-v1",
        "stage": "ID-2Z33", "common_horizon_steps": 73,
        "phase_issue_steps": [50, 56],
        "output_aligned_axis_ids": ["q_r", "q_z"],
        "initial_signs": ["plus", "minus"],
        "maximum_rollouts": 10, "maximum_reset_calls": 10,
        "maximum_advance_attempts": 730, "maximum_gotsc_calls": 730,
        "maximum_verified_plant_advances": 730,
        "required_artifact_files_if_all_complete": 3700,
        "models_fit_or_updated": 0,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise ValueError(f"ID2Z33 frozen field changed: {key}")
    if sum(int(row.get("fit_weight", 0)) for row in stage["rollout_specs"]) != 8:
        raise ValueError("ID2Z33 data roles changed")


def load(config: Path = CONFIG):
    if config.resolve() != CONFIG.resolve():
        raise ValueError("ID2Z33 alternate config forbidden")
    stage = z32._read(config); _require(stage)
    for name, spec in stage["evidence"].items():
        path = ROOT / spec["path"]
        if z32._sha(path) != spec["sha256"]:
            raise ValueError(f"ID2Z33 evidence hash mismatch: {name}")
    forensic = z32._read(ROOT / stage["evidence"]["id2z32_forensic"]["path"])
    if (forensic.get("passed") is not True
            or forensic.get("corrected_classification")
            != stage["evidence"]["id2z32_forensic"]["required_classification"]):
        raise ValueError("ID2Z33 forensic prerequisite mismatch")
    _, base, cfg, preflight, tracked = _Z32_LOAD(z32.CONFIG)
    return stage, base, cfg, preflight, tracked


def _delta(left: Sequence[str], right: Sequence[str]) -> tuple[Decimal, ...]:
    return tuple(Decimal(a.strip()) - Decimal(b.strip()) for a, b in zip(left, right))


def _corrected_branch(center: Sequence[tuple[str, ...]], axis: Sequence[Decimal],
                      phase: int, first_sign: int) -> list[tuple[str, ...]]:
    fields = list(center[:phase])
    current = fields[-1]
    return_start: tuple[str, ...] | None = None
    for issue in range(phase, len(center)):
        if issue < phase + 8:
            center_delta = _delta(center[issue], center[issue - 1])
            step = tuple(value + Decimal(first_sign) * residual
                         for value, residual in zip(center_delta, axis))
            current = z32.z31.z30.z27.z26.z24._combined_step(current, step)
        elif issue < phase + 16:
            if return_start is None:
                return_start = current
            current = z32.z31.z30.z27.z26.z24._interpolate_target(
                return_start, center[phase + 15], issue - phase - 7, 8)
        else:
            current = center[issue]
        fields.append(current)
    return fields


def build_streams(stage: dict[str, Any], cfg: Any, preflight: dict[str, Any],
                  tracked: dict[str, Any]) -> list[dict[str, Any]]:
    center = next(row for row in preflight["prospective_static_streams"]
                  if row["rollout_id"] == "baseline_transition_center")
    center_fields = [tuple(value) for value in center["card15_targets"]]
    axes = {name: tuple(Decimal(value) for value in values) for name, values in
            preflight["output_aligned_field_increments"].items()}
    rows: list[dict[str, Any]] = []; by_id: dict[str, dict[str, Any]] = {}
    for spec in stage["rollout_specs"]:
        family = spec["family_id"]
        if spec["kind"] == "replay":
            row = copy.deepcopy(by_id[spec["source_family_id"]])
            row.update({"rollout_id": family, "candidate_id": family,
                        "family_id": family, "kind": "replay",
                        "source_family_id": spec["source_family_id"],
                        "fit_weight": 0, "data_role": "zero_fit_replay",
                        "cell_id": family})
        else:
            phase = spec.get("phase_issue")
            fields = center_fields if phase is None else _corrected_branch(
                center_fields, axes[spec["axis_id"]], int(phase),
                1 if spec["initial_sign"] == "plus" else -1)
            targets = z32.z31.z30.z27._targets(fields, cfg, family)
            actions = z32.z31.z30.z27._actions(targets, cfg, family, tracked)
            checkpoint = 32 if phase is None else int(phase)
            weight = int(spec["fit_weight"])
            row = {"rollout_id": family, "candidate_id": family,
                   "family_id": family, "kind": spec["kind"],
                   "data_role": "development" if weight else "zero_fit_baseline",
                   "phase_issue": phase, "axis_id": spec.get("axis_id"),
                   "initial_sign": spec.get("initial_sign"), "fit_weight": weight,
                   "round_index": 0, "round_id": "corrected_moving_center_d0",
                   "cell_id": family, "cell_kind": "corrected_moving_center",
                   "context_id": f"canonical_dynamic_state{checkpoint}",
                   "coordinate": "general_center_delta_plus_signed_q_return",
                   "probe_issue_step": phase,
                   "probe_duration_issues": 0 if phase is None else 8,
                   "prefix_checkpoint_last_state": checkpoint,
                   "non_nominal_issue_steps": [] if phase is None else list(
                       range(int(phase), int(phase) + 16)),
                   "targets": targets, "actions": actions}
        rows.append(row); by_id[family] = row
    return rows


def action_separation(streams: Sequence[dict[str, Any]]) -> dict[str, Any]:
    by_id = {row["rollout_id"]: row for row in streams}
    baseline = by_id["baseline_transition_center"]
    failures: list[str] = []; rows = []
    for stream in streams:
        if stream["kind"] not in ("output_aligned_branch",):
            continue
        phase = int(stream["phase_issue"])
        differing = [index for index, (left, right) in enumerate(
            zip(stream["actions"], baseline["actions"]))
            if left["expected_card15_fields"] != right["expected_card15_fields"]]
        outside = [index for index in differing if not phase <= index < phase + 16]
        first_nonzero = stream["actions"][phase]["maximum_issued_delta_a"] > 0
        terminal_equal = (stream["actions"][phase + 15]["expected_card15_fields"]
                          == baseline["actions"][phase + 15]["expected_card15_fields"])
        passed = bool(differing and not outside and first_nonzero and terminal_equal)
        if not passed: failures.append(stream["rollout_id"])
        rows.append({"family_id": stream["rollout_id"],
                     "differing_issue_indices": differing,
                     "outside_window": outside, "first_branch_issue_nonzero": first_nonzero,
                     "terminal_target_equals_center": terminal_equal, "passed": passed})
    for phase in (50, 56):
        for axis in ("q_r", "q_z"):
            plus = by_id[f"issue{phase}__{axis}__plus_then_return"]
            minus = by_id[f"issue{phase}__{axis}__minus_then_return"]
            if all(a["expected_card15_fields"] == b["expected_card15_fields"]
                   for a, b in zip(plus["actions"], minus["actions"])):
                failures.append(f"PLUS_MINUS_IDENTICAL:{phase}:{axis}")
    return {"passed": not failures and len(rows) == 8, "failures": failures,
            "rows": rows}


def offline(config: Path, revision: str) -> dict[str, Any]:
    failures: list[str] = []
    try:
        stage, _, cfg, preflight, tracked = load(config)
        streams = build_streams(stage, cfg, preflight, tracked)
        checks = [z32.z31.z30.validate_stream(row, cfg) for row in streams]
        separation = action_separation(streams)
        if len(streams) != 10 or not all(row["passed"] for row in checks):
            failures.append("STATIC_STREAMS")
        if not separation["passed"]:
            failures.append("ACTION_STREAM_SEPARATION")
    except Exception as exc:
        checks = []; separation = {"passed": False, "failures": [str(exc)], "rows": []}
        failures.append(f"{type(exc).__name__}:{exc}")
    return {"schema_version": OFFLINE_SCHEMA, "source_revision": revision,
            "stage_config_sha256": CONFIG_SHA256, "passed": not failures,
            "failures": failures, "stream_checks": checks,
            "action_stream_separation": separation, "reset_calls": 0,
            "plant_advance_gotsc_calls": 0, "models_fit_or_updated": 0}


def install() -> None:
    z32.CONFIG = CONFIG; z32.CONFIG_SHA256 = CONFIG_SHA256
    z32.SCHEMA = SCHEMA; z32.ROW_SCHEMA = ROW_SCHEMA; z32.OFFLINE_SCHEMA = OFFLINE_SCHEMA
    z32.load = load; z32.build_streams = build_streams; z32.offline = offline


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv); install()
    value = offline(args.config, args.source_revision) if args.offline else z32.run(
        args.config, args.source_revision, args.output)
    if args.offline:
        z32.z31.z30.z27.io.write_new(args.output, value)
    print(json.dumps(value, sort_keys=True, allow_nan=False))
    return 0 if value["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
