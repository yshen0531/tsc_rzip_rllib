#!/usr/bin/env python3
"""Independent compact server-side forensics for a completed Stage4.2R2 run.

This tool is intentionally outside the experiment package.  It reads the
immutable server-side raw/source/snapshot evidence in place and writes only a
compact audit JSON, per-case CSV, and input inventory.  It never launches TSC.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r2_persistent_controller_checkpoint_replay as r2,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def strict_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle, parse_constant=reject_constant)


def strict_json_gz(path: Path) -> Any:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle, parse_constant=reject_constant)


def canonical_digest(payload: Mapping[str, Any]) -> str:
    text = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def exact(left: Any, right: Any) -> tuple[bool, float | None]:
    a = np.asarray(left, dtype=float)
    b = np.asarray(right, dtype=float)
    if a.shape != b.shape or not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)):
        return False, None
    if a.size == 0:
        return bool(np.array_equal(a, b)), 0.0
    return bool(np.array_equal(a, b)), float(np.max(np.abs(a - b)))


def visible(rows: list[Mapping[str, Any]]) -> np.ndarray:
    return r2.r1._visible_array({"trajectory": rows})


def wires(rows: list[Mapping[str, Any]]) -> np.ndarray:
    return r2.r1._wire_array({"trajectory": rows})


def forbidden_paths(value: Any, prefix: str = "") -> list[str]:
    forbidden = {
        "source_actions",
        "source_suffix_actions",
        "future_actions",
        "future_measurements",
        "source_future_trajectory",
    }
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            path = f"{prefix}.{key_text}" if prefix else key_text
            if key_text in forbidden:
                found.append(path)
            found.extend(forbidden_paths(item, path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(forbidden_paths(item, f"{prefix}[{index}]"))
    return found


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, allow_nan=False) + "\n"
    path.write_text(text, encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: (
                        json.dumps(value, sort_keys=True, separators=(",", ":"))
                        if isinstance(value, (dict, list))
                        else value
                    )
                    for key, value in row.items()
                }
            )


def run(project_dir: Path, run_dir: Path, output_dir: Path) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    run_dir = run_dir.resolve()
    output_dir = output_dir.resolve()
    if run_dir.parent != project_dir / "stage4_2r2_runs":
        raise ValueError("R2 run is outside canonical stage4_2r2_runs")
    if output_dir.parent != run_dir:
        raise ValueError("audit output must be an immediate child of the R2 run")

    manifest = strict_json(run_dir / "stage4_2r2_manifest.json")
    state = strict_json(run_dir / "stage4_2r2_state.json")
    cfg_path = project_dir / "configs/stage4_2r2_persistent_controller_checkpoint_replay_370ms.json"
    source_r1 = Path(str(manifest["source_stage4_2r1_run"])).resolve()
    ctx = r2.load_stage42r2_config(
        cfg_path,
        source_stage42r1_run=source_r1,
        run_dir_override=run_dir,
    )
    sources = r2._selected_sources(ctx)
    captures = r2._captures(ctx)
    r1_restarts = r2._r1_restarts(ctx)

    input_files = sorted(
        path
        for path in run_dir.rglob("*")
        if path.is_file() and output_dir not in path.parents
    )
    inventory = [
        {
            "path": path.relative_to(run_dir).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in input_files
    ]
    json_files = [path for path in input_files if path.suffix == ".json"]
    gz_files = [path for path in input_files if path.name.endswith(".json.gz")]
    for path in json_files:
        strict_json(path)
    for path in gz_files:
        strict_json_gz(path)

    checkpoint_paths = sorted(
        (run_dir / "stage4_2r2_controller_checkpoint_bank").glob(
            "*/controller_checkpoint.json"
        )
    )
    raw_paths = sorted(
        (run_dir / "stage4_2r2_controller_restart_replay" / "raw").glob(
            "*.json.gz"
        )
    )
    if len(checkpoint_paths) != 18 or len(raw_paths) != 18:
        raise ValueError("R2 checkpoint/raw coverage is not 18/18")
    checkpoints = {}
    for path in checkpoint_paths:
        payload = strict_json(path)
        recorded = str(payload["digest"])
        without_digest = dict(payload)
        without_digest.pop("digest")
        if canonical_digest(without_digest) != recorded:
            raise ValueError(f"checkpoint digest mismatch: {path}")
        key = (
            str(payload["target_id"]),
            int(payload["actual_delay_steps"]),
            float(payload["actual_slew_scale"]),
        )
        checkpoints[key] = payload

    raw = {}
    for path in raw_paths:
        result = strict_json_gz(path)
        key = r2._case_key(result)
        if key in raw:
            raise ValueError(f"duplicate R2 raw key: {key}")
        raw[key] = (path, result)
    if set(raw) != set(sources) or set(raw) != set(checkpoints):
        raise ValueError("R2/source/checkpoint case coverage differs")

    snapshot_file_count = 0
    snapshot_total_bytes = 0
    snapshot_hash_mismatch_count = 0
    snapshot_manifests = sorted(
        (source_r1 / "stage4_2r1_restart_bank").rglob(
            "restart_snapshot_manifest.json"
        )
    )
    if len(snapshot_manifests) != 18:
        raise ValueError("R1 snapshot manifest coverage is not 18")
    for manifest_path in snapshot_manifests:
        snapshot = strict_json(manifest_path)
        if not snapshot.get("passed") or snapshot.get("missing_required_files"):
            raise ValueError(f"failed source snapshot manifest: {manifest_path}")
        files = list(snapshot["files"])
        if len(files) != int(snapshot["n_files"]):
            raise ValueError(f"snapshot file count mismatch: {manifest_path}")
        for item in files:
            payload_path = manifest_path.parent / str(item["name"])
            actual_size = payload_path.stat().st_size
            actual_hash = sha256_file(payload_path)
            snapshot_file_count += 1
            snapshot_total_bytes += actual_size
            if (
                actual_size != int(item["size_bytes"])
                or actual_hash != str(item["sha256"])
            ):
                snapshot_hash_mismatch_count += 1

    r13_ctx = r2.r1._r13_ctx(ctx.r1_ctx)
    case_rows: list[dict[str, Any]] = []
    for key in sorted(raw, key=lambda item: (item[2], item[1], item[0])):
        raw_path, result = raw[key]
        source = sources[key]
        capture = captures[key]
        r1_restart = r1_restarts[key]
        checkpoint = checkpoints[key]
        horizon = r2._formal_horizon(key[2])
        trajectory = list(result["restart_trajectory"])
        source_rows = list(source["trajectory"])
        capture_rows = list(capture["trajectory"])
        r1_restart_rows = list(r1_restart["restart_trajectory"])
        source_suffix = source_rows[r2.CHECKPOINT_STEP : horizon + 1]
        trace = list(result["controller_trace"])

        checkpoint_history = list(checkpoint["measurement_history"])
        history_indices = [int(row["state_index"]) for row in checkpoint_history]
        checkpoint_digest_ok = not forbidden_paths(checkpoint)
        checkpoint_digest_ok = bool(
            checkpoint_digest_ok
            and history_indices == list(range(r2.CHECKPOINT_STEP + 1))
            and len(checkpoint["pending_delay_queue"])
            == int(checkpoint["modeled_delay_steps"])
        )
        source_raw_path = Path(
            next(
                row["path"]
                for row in ctx.r1_ctx.expert_fingerprint["files"]
                if str(row["experiment_id"]) == str(source["experiment_id"])
            )
        )
        capture_raw_path = (
            source_r1
            / "stage4_2r1_plant_checkpoint_capture"
            / "raw"
            / f"{capture['experiment_id']}.json.gz"
        )
        source_hash_ok = sha256_file(source_raw_path) == checkpoint["source_raw_sha256"]
        capture_hash_ok = (
            sha256_file(capture_raw_path) == checkpoint["capture_raw_sha256"]
        )
        checkpoint_action_exact, checkpoint_action_diff = exact(
            checkpoint["checkpoint_action_norm_tsc"],
            source_rows[r2.CHECKPOINT_STEP]["action_norm_tsc"],
        )
        checkpoint_wire_exact, checkpoint_wire_diff = exact(
            checkpoint["checkpoint_wire_currents_a"],
            capture_rows[r2.CHECKPOINT_STEP]["wire_currents_a"],
        )
        snapshot_manifest_digest_ok = bool(
            checkpoint["plant_snapshot_manifest_digest"]
            == capture["restart_snapshot"]["snapshot_manifest_digest"]
        )
        visible_exact, visible_diff = exact(visible(trajectory), visible(source_suffix))
        wire_exact, wire_diff = exact(wires(trajectory), wires(capture_rows[20 : horizon + 1]))
        r1_wire_exact, r1_wire_diff = exact(
            wires(trajectory), wires(r1_restart_rows[: horizon - 19])
        )
        action_exact, action_diff = exact(
            [row["action_norm_tsc"] for row in trajectory[1:]],
            [row["action_norm_tsc"] for row in source_suffix[1:]],
        )
        trace_action_exact, trace_action_diff = exact(
            [row["action_norm_tsc"] for row in trace],
            [row["action_norm_tsc"] for row in trajectory[1:]],
        )
        recombined = capture_rows[:20] + trajectory
        recombined_visible_exact, recombined_visible_diff = exact(
            visible(recombined), visible(source_rows[: horizon + 1])
        )
        recombined_wire_exact, recombined_wire_diff = exact(
            wires(recombined), wires(capture_rows[: horizon + 1])
        )
        trace_causal = bool(
            len(trace) == horizon - r2.CHECKPOINT_STEP
            and all(bool(row["computed_online"]) for row in trace)
            and all(
                int(row["measurement_max_state_index_used"]) <= int(row["step"])
                for row in trace
            )
            and not any(bool(row["future_measurement_used"]) for row in trace)
        )
        policy = r2.r1.r13._timing_policy(
            r13_ctx,
            key[2],
            policy_id=f"r42r2_remote_audit_{key[0]}_{key[1]}_{key[2]:.1f}",
        )
        formal = r2.r1.r8.tracking_metrics(
            r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx,
            {**source, "trajectory": recombined},
            policy,
        )
        controller_summary = result["controller_restart_summary"]
        passed = bool(
            result["success"]
            and checkpoint_digest_ok
            and source_hash_ok
            and capture_hash_ok
            and checkpoint_action_exact
            and checkpoint_wire_exact
            and snapshot_manifest_digest_ok
            and visible_exact
            and wire_exact
            and r1_wire_exact
            and action_exact
            and trace_action_exact
            and recombined_visible_exact
            and recombined_wire_exact
            and trace_causal
            and controller_summary["fresh_controller_actor"]
            and controller_summary["fresh_tsc_plant_restart"]
            and controller_summary["controller_checkpoint_loaded"]
            and controller_summary["online_action_recomputation"]
            and not controller_summary["future_action_replay_used"]
            and formal["stage3_4_target_tracking_pass"]
        )
        case_rows.append(
            {
                "experiment_id": result["experiment_id"],
                "raw_path": raw_path.relative_to(run_dir).as_posix(),
                "raw_size_bytes": raw_path.stat().st_size,
                "raw_sha256": sha256_file(raw_path),
                "target_id": key[0],
                "actual_delay_steps": key[1],
                "actual_slew_scale": key[2],
                "horizon_steps": horizon,
                "restart_state_count": len(trajectory),
                "controller_trace_count": len(trace),
                "environment_success": bool(result["success"]),
                "failure_reason": str(result.get("failure_reason", "")),
                "checkpoint_schema_and_digest_pass": checkpoint_digest_ok,
                "source_raw_hash_pass": source_hash_ok,
                "capture_raw_hash_pass": capture_hash_ok,
                "checkpoint_action_exact": checkpoint_action_exact,
                "checkpoint_action_max_abs_difference": checkpoint_action_diff,
                "checkpoint_wire_exact": checkpoint_wire_exact,
                "checkpoint_wire_max_abs_difference": checkpoint_wire_diff,
                "snapshot_manifest_digest_pass": snapshot_manifest_digest_ok,
                "restart_visible_exact": visible_exact,
                "restart_visible_max_abs_difference": visible_diff,
                "restart_wire_exact": wire_exact,
                "restart_wire_max_abs_difference": wire_diff,
                "restart_wire_exact_to_r1_restart": r1_wire_exact,
                "restart_wire_to_r1_max_abs_difference": r1_wire_diff,
                "online_action_exact": action_exact,
                "online_action_max_abs_difference": action_diff,
                "controller_trace_action_exact": trace_action_exact,
                "controller_trace_action_max_abs_difference": trace_action_diff,
                "recombined_visible_exact": recombined_visible_exact,
                "recombined_visible_max_abs_difference": recombined_visible_diff,
                "recombined_wire_exact": recombined_wire_exact,
                "recombined_wire_max_abs_difference": recombined_wire_diff,
                "controller_trace_causal": trace_causal,
                "fresh_controller_actor": bool(
                    controller_summary["fresh_controller_actor"]
                ),
                "fresh_tsc_plant_restart": bool(
                    controller_summary["fresh_tsc_plant_restart"]
                ),
                "future_action_replay_used": bool(
                    controller_summary["future_action_replay_used"]
                ),
                "formal_contract_pass": bool(
                    formal["stage3_4_target_tracking_pass"]
                ),
                "formal_best_arrival_ms": int(
                    formal["stage3_4_best_endpoint_ms"]
                ),
                "formal_minimum_signed_margin": float(
                    formal["stage3_4_tracking_minimum_signed_margin"]
                ),
                "passed": passed,
            }
        )

    saved_summary = strict_json(
        run_dir / "stage4_2r2_controller_restart_replay" / "summary.json"
    )
    derived_minimum = min(
        case_rows, key=lambda row: float(row["formal_minimum_signed_margin"])
    )
    derived = {
        "n_rollouts": len(case_rows),
        "environment_success_count": sum(
            bool(row["environment_success"]) for row in case_rows
        ),
        "online_action_exact_fraction": sum(
            bool(row["online_action_exact"]) for row in case_rows
        )
        / len(case_rows),
        "restart_visible_exact_fraction": sum(
            bool(row["restart_visible_exact"]) for row in case_rows
        )
        / len(case_rows),
        "restart_wire_exact_fraction": sum(
            bool(row["restart_wire_exact"]) for row in case_rows
        )
        / len(case_rows),
        "formal_contract_pass_fraction": sum(
            bool(row["formal_contract_pass"]) for row in case_rows
        )
        / len(case_rows),
        "minimum_formal_signed_margin": float(
            derived_minimum["formal_minimum_signed_margin"]
        ),
    }
    summary_agreement = all(
        saved_summary.get(key) == value for key, value in derived.items()
    )
    runtime_error_count = sum(not bool(row["environment_success"]) for row in case_rows)
    design_failure_count = sum(
        not bool(row["checkpoint_schema_and_digest_pass"])
        or not bool(row["controller_trace_causal"])
        or not bool(row["online_action_exact"])
        for row in case_rows
    )
    plant_restart_failure_count = sum(
        not bool(row["restart_visible_exact"])
        or not bool(row["restart_wire_exact"])
        or not bool(row["recombined_visible_exact"])
        for row in case_rows
    )
    formal_control_failure_count = sum(
        not bool(row["formal_contract_pass"]) for row in case_rows
    )
    case_pass = bool(len(case_rows) == 18 and all(row["passed"] for row in case_rows))
    fresh_restart_pass = bool(
        all(
            row["fresh_controller_actor"] and row["fresh_tsc_plant_restart"]
            for row in case_rows
        )
    )
    source_fingerprint_matches_manifest = bool(
        ctx.source_fingerprint == manifest["source_fingerprint"]
    )
    audit = {
        "schema_version": 1,
        "stage": "Stage4.2R2",
        "audit_contract": "independent_server_raw_snapshot_formal_recomputation_v1",
        "project_dir": str(project_dir),
        "run_dir": str(run_dir),
        "source_stage4_2r1_run": str(source_r1),
        "experiment_controller_revision": manifest["controller_revision"],
        "experiment_package_revision": manifest["package_revision"],
        "postprocessor_path": str(Path(__file__).resolve()),
        "postprocessor_sha256": sha256_file(Path(__file__).resolve()),
        "input_inventory": {
            "file_count": len(inventory),
            "total_bytes": sum(int(row["size_bytes"]) for row in inventory),
            "json_count": len(json_files),
            "json_gz_count": len(gz_files),
            "strict_json_parse_pass": True,
            "digest": canonical_digest({"files": inventory}),
        },
        "source_snapshot_inventory": {
            "manifest_count": len(snapshot_manifests),
            "payload_file_count": snapshot_file_count,
            "payload_total_bytes": snapshot_total_bytes,
            "hash_mismatch_count": snapshot_hash_mismatch_count,
            "passed": snapshot_hash_mismatch_count == 0,
        },
        "coverage": {
            "expected_cases": 18,
            "raw_cases": len(raw_paths),
            "controller_checkpoints": len(checkpoint_paths),
            "case_keys_exact_to_selected_source": set(raw) == set(sources),
            "source_fingerprint_matches_run_manifest": (
                source_fingerprint_matches_manifest
            ),
        },
        "independently_derived_metrics": derived,
        "saved_summary_agrees_with_independent_metrics": summary_agreement,
        "error_classification": {
            "runtime_or_environment_error_count": runtime_error_count,
            "raw_or_snapshot_corruption_count": snapshot_hash_mismatch_count,
            "statistics_or_reporting_error_count": 0 if summary_agreement else 1,
            "controller_checkpoint_or_design_failure_count": design_failure_count,
            "plant_restart_fidelity_failure_count": plant_restart_failure_count,
            "real_closed_loop_formal_control_failure_count": formal_control_failure_count,
        },
        "scientific_conclusion": {
            "same_source_finite_clean_persistent_controller_restart_validated": (
                case_pass and source_fingerprint_matches_manifest
            ),
            "online_suffix_actions_recomputed_not_replayed": bool(
                case_pass
                and all(
                    row["online_action_exact"]
                    and not row["future_action_replay_used"]
                    and row["controller_trace_causal"]
                    for row in case_rows
                )
            ),
            "fresh_controller_and_tsc_process_validated": fresh_restart_pass,
            "formal_contract_preserved": formal_control_failure_count == 0,
            "finite_test_envelope_only": True,
            "matched_visible_different_hidden_history_validated": False,
            "different_initial_state_validated": False,
            "unseen_target_validated": False,
            "continuous_parameter_change_validated": False,
            "plant_or_jacobian_error_validated": False,
            "measurement_noise_validated": False,
            "disturbance_recovery_validated": False,
            "independent_long_hold_validated": False,
            "bc_dagger_or_rl_allowed": False,
        },
        "minimum_margin_case": {
            "target_id": derived_minimum["target_id"],
            "actual_delay_steps": derived_minimum["actual_delay_steps"],
            "actual_slew_scale": derived_minimum["actual_slew_scale"],
            "formal_minimum_signed_margin": derived_minimum[
                "formal_minimum_signed_margin"
            ],
        },
        "state_finished": bool(state["finished"]),
        "state_primary_pass": bool(state["primary_pass"]),
        "passed": False,
    }
    audit["passed"] = bool(
        len(case_rows) == 18
        and all(bool(row["passed"]) for row in case_rows)
        and source_fingerprint_matches_manifest
        and snapshot_hash_mismatch_count == 0
        and summary_agreement
        and not any(audit["error_classification"].values())
        and state["finished"]
        and state["primary_pass"]
    )
    write_json(output_dir / "stage4_2r2_remote_forensic_audit.json", audit)
    write_json(output_dir / "stage4_2r2_case_rows.json", case_rows)
    write_csv(output_dir / "stage4_2r2_case_rows.csv", case_rows)
    write_json(output_dir / "stage4_2r2_input_inventory.json", inventory)
    return audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    payload = run(args.project_dir, args.run_dir, args.output_dir)
    print(json.dumps(payload, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
