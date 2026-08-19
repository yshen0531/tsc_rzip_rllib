#!/usr/bin/env python3
"""Zero-TSC finalizer for the interrupted ID2Z6R1 resume attempt."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_id2z6_early_root_branch_teacher as primary  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2z6_early_root_branch_teacher_independent as independent  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2z6r1_resume as resume  # noqa: E402
from scripts.rgeo_zgeo_1ms_id2w1_sustained_branch_independent import (  # noqa: E402
    restore_arrival_active_commands,
)


SCHEMA = "rgeo-zgeo-1ms-id2z6r2-failure-finalize-v1"
STOP_REASON = "OPERATOR_STOP_AFTER_RUN_ROOT_CONTRACT_VIOLATION"


def _inside(path: Path, label: str) -> Path:
    value = path.resolve()
    try:
        value.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(f"{label} leaves repository") from exc
    return value


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"object required: {path}")
    return value


def reconstruct_partial(run_dir: Path, cfg: Any,
                        stream: dict[str, Any],
                        experiment_source_revision: str) -> dict[str, Any]:
    folder = run_dir / "rollouts" / stream["rollout_id"]
    times = sorted(
        int(path.name[:-2]) for path in folder.iterdir()
        if path.is_dir() and path.name.endswith("ms")
        and path.name[:-2].isdigit())
    if times != [1100, 1101, 1102]:
        raise ValueError(f"unexpected interrupted state set: {times}")
    states = [independent._state(folder / f"{time}ms", cfg) for time in times]
    actions = [dict(stream["actions"][issue]) for issue in range(3)]
    issued_fields = [list(independent._fields(
        folder / f"{1100 + issue}ms" / "inputa")) for issue in range(3)]
    if issued_fields != [row["expected_card15_fields"] for row in actions]:
        raise ValueError("interrupted outgoing actions do not match frozen stream")
    restore_arrival_active_commands(states, issued_fields)
    states[0]["active_command_card15_fields"] = list(independent._fields(
        cfg.simulation_root / cfg.start_folder / "inputa"))
    return {
        **{key: value for key, value in stream.items()
           if key not in ("targets", "actions")},
        "schema_version": primary.SCHEMA,
        "source_revision": experiment_source_revision,
        "passed": False,
        "reasons": [STOP_REASON],
        "fit_weight": 0,
        "states": states,
        "actions": actions,
        "attempted_actions": actions,
        "reset_calls": 1,
        "advance_attempts": 3,
        "plant_advance_gotsc_calls": 3,
        "verified_plant_advances": 2,
        "retry_attempted": False,
        "wall_time_s": None,
        "forensic_reconstruction": True,
        "claim_boundary": (
            "Three observed canonical-prefix states and three issued attempts; "
            "the third gotsc was terminated before a verified successor."),
    }


def prepare(run_dir: Path, experiment_source_revision: str,
            hotfix_source_revision: str) -> tuple[dict[str, Any], dict[str, Any]]:
    failures: list[str] = []
    run_dir = _inside(run_dir, "run directory")
    if (run_dir / "result.json").exists():
        failures.append("RESULT_ALREADY_EXISTS")
    if (run_dir / "independent_raw_audit.json").exists():
        failures.append("AUDIT_ALREADY_EXISTS")
    stage, cfg, targets, compact_reference, selected = primary.load()
    metadata_path = run_dir / "metadata" / "id2z6r1_resume_preflight.json"
    metadata = _load(metadata_path) if metadata_path.is_file() else {}
    if (metadata.get("experiment_source_revision") != experiment_source_revision
            or metadata.get("hotfix_source_revision") != hotfix_source_revision
            or not metadata.get("passed")):
        failures.append("RESUME_METADATA")

    round0_streams = primary.initial_round_streams(
        stage, cfg, targets, selected)
    round0_rows = [_load(run_dir / f"{stream['rollout_id']}.json")
                   for stream in round0_streams]
    round0_metric = primary.round_metrics(round0_rows, stage, 0, cfg)
    if (not round0_metric.get("passed")
            or round0_metric.get("selected_arm_id") != "f4"):
        failures.append("ROUND0_SELECTION")
    selected_stream = next(
        row for row in round0_streams if row["arm_id"] == "f4")
    selected_row = next(row for row in round0_rows if row["arm_id"] == "f4")
    round1_streams = primary.next_round_streams(
        stage, cfg, targets, selected_stream, 1)
    expected_existing = ["r1__hold4", "r1__b4"]
    round1_rows = []
    for rollout_id in expected_existing:
        path = run_dir / f"{rollout_id}.json"
        if not path.is_file():
            failures.append(f"COMPACT_MISSING:{rollout_id}")
        else:
            row = _load(path)
            if (not row.get("passed") or len(row.get("states", [])) != 70
                    or row.get("source_revision") != experiment_source_revision):
                failures.append(f"COMPACT_INELIGIBLE:{rollout_id}")
            round1_rows.append(row)
    partial_stream = next(
        row for row in round1_streams if row["rollout_id"] == "r1__f4")
    try:
        partial = reconstruct_partial(
            run_dir, cfg, partial_stream, experiment_source_revision)
    except Exception as exc:
        failures.append(f"PARTIAL_RECONSTRUCTION:{type(exc).__name__}:{exc}")
        partial = {}

    allowed_dirs = {
        *(row["rollout_id"] for row in round0_streams),
        "r1__hold4", "r1__b4", "r1__f4"}
    actual_dirs = sorted(
        path.name for path in (run_dir / "rollouts").iterdir()
        if path.is_dir())
    if actual_dirs != sorted(allowed_dirs):
        failures.append("RAW_DIRECTORY_SET")
    failures = list(dict.fromkeys(failures))
    preflight = {
        "schema_version": SCHEMA,
        "passed": not failures,
        "failures": failures,
        "experiment_source_revision": experiment_source_revision,
        "hotfix_source_revision": hotfix_source_revision,
        "stage_config_sha256": primary.CONFIG_SHA256,
        "complete_round0_rollouts": len(round0_rows),
        "complete_round1_rollouts": len(round1_rows),
        "partial_round1_states": len(partial.get("states", [])),
        "partial_round1_attempts": partial.get("advance_attempts"),
        "partial_round1_verified_advances": partial.get(
            "verified_plant_advances"),
        "reset_calls": 0,
        "advance_attempts": 0,
        "plant_advance_gotsc_calls": 0,
        "models_fit_or_updated": 0,
    }
    return preflight, {
        "stage": stage,
        "cfg": cfg,
        "compact_reference": compact_reference,
        "round0_rows": round0_rows,
        "round0_metric": round0_metric,
        "selected_row": selected_row,
        "round1_rows": round1_rows,
        "partial": partial,
        "metadata": metadata,
    }


def finalize(run_dir: Path, experiment_source_revision: str,
             hotfix_source_revision: str) -> dict[str, Any]:
    run_dir = _inside(run_dir, "run directory")
    preflight, context = prepare(
        run_dir, experiment_source_revision, hotfix_source_revision)
    if not preflight["passed"]:
        return preflight
    partial_path = run_dir / "r1__f4.json"
    primary.z5.z3.z1.y1r1.y1.x1.write_new(partial_path, context["partial"])
    rows = [*context["round0_rows"], *context["round1_rows"], context["partial"]]
    prefix_values = [primary.prefix_check(
        row, context["compact_reference"], 50, 49,
        context["stage"]["semantic_artifacts"])
        for row in context["round0_rows"]]
    result = resume._finalize(
        context["stage"], rows, [context["round0_metric"]],
        prefix_values, False, context["selected_row"], None,
        run_dir, experiment_source_revision, hotfix_source_revision,
        context["metadata"])
    result["failure_finalizer"] = SCHEMA
    result["failure_finalizer_zero_tsc"] = True
    # _finalize already wrote the immutable primary.  Preserve the extra
    # provenance in a separate metadata record rather than rewriting it.
    metadata_dir = run_dir / "metadata"
    primary.z5.z3.z1.y1r1.y1.x1.write_new(
        metadata_dir / "id2z6r2_failure_finalize.json", {
            **preflight,
            "primary_route": result["route"],
            "primary_sha256": primary.z5.base.sha256(run_dir / "result.json"),
            "reconstructed_partial_compact_sha256": primary.z5.base.sha256(
                partial_path),
        })
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--experiment-source-revision", required=True)
    parser.add_argument("--hotfix-source-revision", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args(argv)
    if args.preflight_only:
        result, _ = prepare(
            args.run_dir, args.experiment_source_revision,
            args.hotfix_source_revision)
    else:
        result = finalize(
            args.run_dir, args.experiment_source_revision,
            args.hotfix_source_revision)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    if args.preflight_only:
        return 0 if result.get("passed") else 2
    # The finalized experiment is intentionally a non-PASS execution route.
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
