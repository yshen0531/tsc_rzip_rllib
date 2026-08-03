#!/usr/bin/env python3
"""Zero-new-TSC causal recursive split-return preflight for D1R4 raw."""

from __future__ import annotations

import argparse
import copy
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r2_real_tsc_safety_sentinel as d1r2,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r4_causal_split_return_safety_sentinel as d1r4,
)


STAGE = "Stage4.2R3c3T13S24D1R5"
IDENTITY = "causal_recursive_split_return_preflight_v1"
CONTROLLER_REVISION = "causal_recursive_split_return_probe_v42r3c3t13s24d1r5_v1"
PACKAGE_REVISION = "r42r3c3t13s24d1r5_recursive_split_return_preflight_v1"
N_COILS = 14


def _read_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
    )


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _inventory(paths: Sequence[Path]) -> dict[str, Any]:
    rows = []
    digest = hashlib.sha256()
    for path in sorted(paths):
        sha = _sha256(path)
        size = path.stat().st_size
        digest.update(f"{path.name}\0{size}\0{sha}\n".encode())
        rows.append({"path": path.name, "bytes": size, "sha256": sha})
    return {
        "count": len(rows),
        "total_bytes": sum(int(row["bytes"]) for row in rows),
        "digest": digest.hexdigest(),
        "files": rows,
    }


def _validate_config(cfg: Mapping[str, Any], config_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    expected_path = (
        root
        / "configs/stage4_2r3c3t13s24d1r5_recursive_split_return_preflight_v1.json"
    ).resolve()
    if config_path.resolve() != expected_path:
        raise ValueError("D1R5 config path changed")
    exact = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "package_revision": PACKAGE_REVISION,
        "selection_status": (
            "frozen_after_d1r4_fail_before_d1r5_implementation_or_output"
        ),
    }
    if any(cfg.get(key) != value for key, value in exact.items()):
        raise ValueError("D1R5 frozen identity changed")
    design = (root / str(cfg["design_document"])).resolve()
    if not design.is_file() or _sha256(design) != cfg["design_document_sha256"]:
        raise ValueError("D1R5 design document changed")
    source = cfg["source_contract"]
    counts = {
        "raw_count": 9,
        "raw_total_bytes": 363_807,
        "strict_identity_count": 9,
        "restart_causality_calibration_count": 9,
        "source_prefix_exact_count": 9,
        "d1r3_split_start_exact_count": 9,
        "structured_split_finish_stop_count": 9,
        "formal_endpoint_evaluable_count": 0,
    }
    if any(source.get(key) != value for key, value in counts.items()):
        raise ValueError("D1R5 frozen source counts changed")
    hash_keys = (
        "execution_module_sha256",
        "execution_config_sha256",
        "package_manifest_sha256",
        "sha256sums_sha256",
        "raw_inventory_digest",
        "complete_log_sha256",
        "final_sha256",
        "manifest_sha256",
        "state_sha256",
        "prospective_audit_sha256",
        "retrospective_audit_sha256",
        "snapshot_audit_sha256",
        "source_authentication_sha256",
        "candidate_spec_digest",
    )
    if any(len(str(source.get(key, ""))) != 64 for key in hash_keys):
        raise ValueError("D1R5 frozen source hash changed")
    recursive = cfg["recursive_contract"]
    if (
        float(recursive["direct_finish_threshold"]) != 0.24
        or float(recursive["continuation_target_increment"]) != 0.175
        or float(recursive["maximum_continuation_increment"]) != 0.18
        or float(recursive["maximum_original_increment"]) != 0.25
        or float(recursive["maximum_total_normalized_action_abs"]) != 1.0
        or float(recursive["maximum_current_utilization"]) != 0.55
        or int(recursive["initial_split_task_step"]) != 18
        or int(recursive["continuation_task_step"]) != 19
        or int(recursive["latest_future_finish_task_step"]) != 22
        or int(recursive["split_slot"]) != 3
        or not all(
            bool(recursive[key])
            for key in (
                "require_direct_failure_reproduction",
                "require_exact_card15_continuation",
                "require_expanded_exact_decimal_telescope",
                "require_no_saturation_or_clipping",
            )
        )
        or bool(recursive["controller_label_access"])
        or bool(recursive["controller_future_access"])
    ):
        raise ValueError("D1R5 recursive contract changed")
    if cfg["execution_contract"] != {
        "new_raw_files": 0,
        "new_snapshots": 0,
        "ray_allowed": False,
        "gotsc_allowed": False,
        "tsc_allowed": False,
        "plant_advance_allowed": False,
        "server_side_raw_processing": True,
    }:
        raise ValueError("D1R5 zero-TSC contract changed")
    if bool(cfg["scientific_scope"]["bc_dagger_or_rl_allowed"]):
        raise ValueError("D1R5 may not authorize learning")


def _source_paths(ctx: d1r4.Context) -> dict[str, Path]:
    return {
        "final": ctx.paths.final,
        "manifest": ctx.paths.manifest,
        "state": ctx.paths.state,
        "prospective_audit": ctx.paths.analysis / "independent_server_forensics.json",
        "retrospective_audit": (
            ctx.paths.analysis
            / "retrospective_structured_failure_prefix_forensics_v1.json"
        ),
        "snapshot_audit": ctx.paths.source_reference / "snapshot_audit.json",
        "source_authentication": (
            ctx.paths.source_reference / "source_authentication.json"
        ),
    }


def _authenticate_source(
    ctx: d1r4.Context, cfg: Mapping[str, Any], complete_log: Path
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source = cfg["source_contract"]
    if ctx.paths.run_dir.name != source["run_name"]:
        raise ValueError("D1R5 D1R4 run identity changed")
    root = d1r4._project_root()
    module = (
        root
        / "tsc_rzip_rllib/diagnostics/"
        "stage4_2r3c3t13s24d1r4_causal_split_return_safety_sentinel.py"
    )
    paths = _source_paths(ctx)
    complete_log = complete_log.expanduser().resolve()
    exact_hashes = {
        "execution_module_sha256": _sha256(module),
        "execution_config_sha256": _sha256(ctx.config_path),
        "complete_log_sha256": _sha256(complete_log),
        "final_sha256": _sha256(paths["final"]),
        "manifest_sha256": _sha256(paths["manifest"]),
        "state_sha256": _sha256(paths["state"]),
        "prospective_audit_sha256": _sha256(paths["prospective_audit"]),
        "retrospective_audit_sha256": _sha256(paths["retrospective_audit"]),
        "snapshot_audit_sha256": _sha256(paths["snapshot_audit"]),
        "source_authentication_sha256": _sha256(paths["source_authentication"]),
    }
    if any(exact_hashes[key] != source[key] for key in exact_hashes):
        raise ValueError("D1R5 D1R4 evidence hash changed")
    raw = _inventory(list(ctx.paths.raw.glob("*.json.gz")))
    specs = d1r4._saved_specs(ctx)
    expected_names = sorted(f"{spec['experiment_id']}.json.gz" for spec in specs)
    manifest = _read_json(paths["manifest"])
    state = _read_json(paths["state"])
    final = _read_json(paths["final"])
    prospective = _read_json(paths["prospective_audit"])
    retrospective = _read_json(paths["retrospective_audit"])
    snapshot = _read_json(paths["snapshot_audit"])
    source_auth = _read_json(paths["source_authentication"])
    package = manifest.get("package_fingerprint") or {}
    passed = bool(
        raw["count"] == source["raw_count"]
        and raw["total_bytes"] == source["raw_total_bytes"]
        and raw["digest"] == source["raw_inventory_digest"]
        and sorted(str(row["path"]) for row in raw["files"]) == expected_names
        and package.get("package_revision") == source["execution_package_revision"]
        and package.get("package_manifest_sha256")
        == source["package_manifest_sha256"]
        and package.get("sha256sums_sha256") == source["sha256sums_sha256"]
        and package.get("implementation_sha256") == source["execution_module_sha256"]
        and package.get("config_sha256") == source["execution_config_sha256"]
        and state.get("finished")
        and state.get("verdict", {}).get("route") == source["required_route"]
        and manifest.get("route") == final.get("route") == source["required_route"]
        and final.get("raw_inventory") == manifest.get("raw_inventory") == raw
        and prospective.get("raw_inventory") == raw
        and retrospective.get("forensic_recomputation_passed")
        and retrospective.get("experiment_route") == source["required_route"]
        and retrospective.get("raw_count") == source["strict_identity_count"]
        and retrospective.get("restart_exact_count")
        == retrospective.get("causality_pass_count")
        == retrospective.get("calibration_pass_count")
        == source["restart_causality_calibration_count"]
        and retrospective.get("source_prefix_action_exact_count")
        == retrospective.get("source_prefix_trace_exact_count")
        == source["source_prefix_exact_count"]
        and retrospective.get("d1r3_split_start_exact_count")
        == source["d1r3_split_start_exact_count"]
        and retrospective.get("structured_split_finish_safe_stop_count")
        == source["structured_split_finish_stop_count"]
        and retrospective.get("formal_tracking_evaluable_count")
        == source["formal_endpoint_evaluable_count"]
        and snapshot.get("passed")
        and snapshot.get("pass_count") == 3
        and source_auth.get("passed")
        and manifest.get("source_fingerprint", {}).get("d1r3_candidate_specs_digest")
        == source["candidate_spec_digest"]
    )
    if not passed:
        raise ValueError(cfg["routes"]["source_stop"])
    return specs, {
        "passed": True,
        "run_dir": str(ctx.paths.run_dir),
        "raw_inventory": raw,
        "execution_package_fingerprint": copy.deepcopy(package),
        **exact_hashes,
    }


class CausalRecursiveSplitReturnPreflightController(
    d1r4.CausalSplitReturnSafetySentinelController
):
    """D1R4 prefix with a state-19 causal 0.175 continuation branch."""

    def __init__(self, *args: Any, recursive_cfg: Mapping[str, Any], **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.recursive_cfg = copy.deepcopy(dict(recursive_cfg))
        self._last_recursive_event: dict[str, Any] | None = None

    def _finish(
        self, currents: np.ndarray, baseline_action: np.ndarray
    ) -> tuple[np.ndarray, dict[str, Any]]:
        pending = self._split_pending
        if pending is None:
            raise ValueError("D1R5 continuation has no pending return")
        stored = tuple(map(str, pending["stored_center_card15_fields"]))
        target = tuple(map(str, pending["issue_target_card15_fields"]))
        previous = tuple(map(str, pending["intermediate_card15_fields"]))
        direct = d1r2.s24.s21.s16.s9.exact_stored_center_action(
            stored_fields=stored,
            measured_current_a_tsc=currents,
            baseline_action_norm_tsc=baseline_action,
            turns_tsc=self.turns_tsc,
            max_slew_step_a=float(self.base.max_delta_a),
            minimum_current_a_tsc=self.base.min_current,
            maximum_current_a_tsc=self.base.max_current,
            cfg=self.lattice_cfg,
        )
        direct_increment = float(direct["incremental_normalized_action_linf"])
        threshold = float(self.recursive_cfg["direct_finish_threshold"])
        baseline = np.asarray(baseline_action, dtype=float).reshape(N_COILS)
        direct_action = np.asarray(direct["action_norm_tsc"], dtype=float).reshape(
            N_COILS
        )
        target_increment = float(self.recursive_cfg["continuation_target_increment"])
        alpha = min(1.0, target_increment / direct_increment)
        continuation_action = baseline + alpha * (direct_action - baseline)
        applied = self.actuator.apply(currents, continuation_action)
        reproduced = self.actuator.apply(currents, continuation_action)
        fields = tuple(map(str, applied.card15_fields))
        turns = np.asarray(self.turns_tsc, dtype=float)
        target_current = np.asarray(
            [
                float(d1r2.s24.s21.s16.s9._decimal_field(field)) * 1000.0 / turn
                for field, turn in zip(fields, turns)
            ],
            dtype=float,
        )
        minimum = np.asarray(self.base.min_current, dtype=float)
        maximum = np.asarray(self.base.max_current, dtype=float)
        utilization = d1r2.s24.s21.s16.s9._current_utilization(
            target_current, minimum, maximum
        )
        increment = float(np.max(np.abs(continuation_action - baseline)))
        total = float(np.max(np.abs(continuation_action)))
        telescope = all(
            (
                d1r2.s24.s21.s16.s9._decimal_field(t)
                - d1r2.s24.s21.s16.s9._decimal_field(c)
            )
            + (
                d1r2.s24.s21.s16.s9._decimal_field(m18)
                - d1r2.s24.s21.s16.s9._decimal_field(t)
            )
            + (
                d1r2.s24.s21.s16.s9._decimal_field(m19)
                - d1r2.s24.s21.s16.s9._decimal_field(m18)
            )
            + (
                d1r2.s24.s21.s16.s9._decimal_field(c)
                - d1r2.s24.s21.s16.s9._decimal_field(m19)
            )
            == Decimal(0)
            for c, t, m18, m19 in zip(stored, target, previous, fields)
        )
        criteria = {
            "direct_requires_continuation": direct_increment > threshold + 1e-12,
            "direct_exceeds_original_cap": direct_increment
            > float(self.recursive_cfg["maximum_original_increment"]) + 1e-12,
            "continuation_step_exact": int(self.step)
            == int(self.recursive_cfg["continuation_task_step"]),
            "slot_exact": int(pending["slot"])
            == int(self.recursive_cfg["split_slot"]),
            "one_plant_advance": int(self.step) - int(pending["start_task_step"])
            == 1,
            "alpha_strictly_between_zero_and_one": 0.0 < alpha < 1.0,
            "continuation_increment": increment
            <= float(self.recursive_cfg["maximum_continuation_increment"]) + 1e-12,
            "original_increment": increment
            <= float(self.recursive_cfg["maximum_original_increment"]) + 1e-12,
            "total_action": total
            <= float(self.recursive_cfg["maximum_total_normalized_action_abs"])
            + 1e-12,
            "current_bounds": bool(
                np.all(target_current >= minimum) and np.all(target_current <= maximum)
            ),
            "current_utilization": utilization
            <= float(self.recursive_cfg["maximum_current_utilization"]) + 1e-12,
            "exact_card15_continuation": all(
                len(field) == 10
                and d1r2.s24.s21.s16.s9.format_number(
                    float(d1r2.s24.s21.s16.s9._decimal_field(field))
                )
                == field
                for field in fields
            ),
            "continuation_reproduction": list(reproduced.card15_fields) == list(fields),
            "continuation_differs_from_center": list(fields) != list(stored),
            "continuation_differs_from_previous": list(fields) != list(previous),
            "expanded_exact_decimal_telescope": telescope,
            "no_saturation": not any(applied.action_saturated),
            "no_current_clip": not any(applied.current_limit_clipped),
        }
        event = {
            "event": "sequential_cancel_split_continue",
            "stage": STAGE,
            "identity": IDENTITY,
            "controller_revision": CONTROLLER_REVISION,
            "slot": int(pending["slot"]),
            "split_start_task_step": int(pending["start_task_step"]),
            "task_step": int(self.step),
            "stored_center_card15_fields": list(stored),
            "issue_target_card15_fields": list(target),
            "previous_intermediate_card15_fields": list(previous),
            "continuation_card15_fields": list(fields),
            "baseline_action_norm_tsc": baseline.tolist(),
            "direct_finish_action_norm_tsc": direct_action.tolist(),
            "direct_finish_incremental_normalized_action_linf": direct_increment,
            "direct_finish_prediction": copy.deepcopy(direct),
            "continuation_target_increment": target_increment,
            "alpha": alpha,
            "continuation_action_norm_tsc": continuation_action.tolist(),
            "continuation_incremental_normalized_action_linf": increment,
            "continuation_total_normalized_action_abs": total,
            "predicted_current_utilization": utilization,
            "criteria": criteria,
            "passed": bool(all(criteria.values())),
        }
        self._last_recursive_event = copy.deepcopy(event)
        if not event["passed"]:
            raise ValueError(
                "D1R5 recursive continuation failed: "
                + json.dumps(event, sort_keys=True)
            )
        pending["intermediate_card15_fields"] = list(fields)
        pending["continuation_count"] = int(pending.get("continuation_count", 0)) + 1
        return continuation_action, event

    def action(
        self, current_state: Mapping[str, Any]
    ) -> tuple[np.ndarray, dict[str, Any]]:
        action, trace = super().action(current_state)
        event = copy.deepcopy(trace.get("r3c3t13s24d1r4_event_detail") or {})
        event_name = str(event.get("event", "none")) if event else "none"
        if event_name == "sequential_cancel_split_continue":
            trace["r3c3t13s24d1r4_event"] = event_name
        trace.update(
            {
                "action_norm_tsc": np.asarray(action, dtype=float).tolist(),
                "r3c3t13s24d1r5_preflight_only": True,
                "r3c3t13s24d1r5_controller_revision": CONTROLLER_REVISION,
                "r3c3t13s24d1r5_event": event_name,
                "r3c3t13s24d1r5_event_detail": event,
                "r3c3t13s24d1r5_split_pending_after_action": self._split_pending
                is not None,
                "r3c3t13s24d1r5_source_selection_label_used": False,
                "r3c3t13s24d1r5_pair_history_partition_label_used": False,
                "r3c3t13s24d1r5_source_outcome_used": False,
                "r3c3t13s24d1r5_future_measurement_used": False,
                "r3c3t13s24d1r5_future_executed_action_used": False,
                "r3c3t13s24d1r5_hidden_wire_current_used": False,
                "r3c3t13s24d1r5_schedule_available_to_underlying_controller": False,
            }
        )
        return np.asarray(action, dtype=float), trace


def _projection(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(value)
        for key, value in row.items()
        if not key.startswith("r3c3t13s24d1r5_")
    }


def _replay_one(
    ctx: d1r4.Context,
    cfg: Mapping[str, Any],
    spec: Mapping[str, Any],
    library: Mapping[str, Any],
    bundle: Mapping[str, Any],
    selector: Mapping[str, Any],
    index: int,
) -> dict[str, Any]:
    raw_path = ctx.paths.raw / f"{spec['experiment_id']}.json.gz"
    result = d1r4._read_raw(raw_path)
    trajectory = list(result["trajectory"])
    source_trace = list(result["controller_trace"])
    payload = _read_json(ctx.paths.variants / f"payload_{spec['experiment_id']}.json")
    worker = d1r2.s24.s21.s16.s9.t11.t1.r1.LocalPlantReplayWorker(
        payload,
        library,
        bundle,
        f"stage42r3c3t13s24d1r5_replay_{index:03d}",
        selector,
    )
    prefix_action_exact = True
    prefix_trace_exact = True
    maximum_action_difference = 0.0
    continuation: dict[str, Any] | None = None
    replay_error = ""
    try:
        s21_ctx = ctx.base_d1r2_ctx.base_s24_ctx.base_ctx
        controller = CausalRecursiveSplitReturnPreflightController(
            worker.base_worker,
            bundle,
            d1r4._controller_spec(spec),
            trajectory[0],
            s21_ctx.base_ctx.cfg["lattice_probe"],
            s21_ctx.base_ctx.cfg["active_calibration"],
            s21_ctx.cfg["causal_model"],
            ctx.base_d1r2_ctx.cfg["schedule_contract"],
            split_cfg=ctx.cfg["split_contract"],
            recursive_cfg=cfg["recursive_contract"],
        )
        for step in range(20):
            action, replay_trace = controller.action(trajectory[step])
            if step < len(source_trace):
                source_action = np.asarray(
                    source_trace[step]["action_norm_tsc"], dtype=float
                )
                difference = float(np.max(np.abs(action - source_action)))
                maximum_action_difference = max(maximum_action_difference, difference)
                prefix_action_exact = bool(prefix_action_exact and difference <= 1e-12)
                prefix_trace_exact = bool(
                    prefix_trace_exact
                    and _projection(replay_trace) == source_trace[step]
                )
            else:
                continuation = copy.deepcopy(controller._last_recursive_event)
            if step + 1 < len(trajectory):
                controller.advance(trajectory[step + 1])
    except Exception as exc:
        replay_error = repr(exc)
    finally:
        worker.close()
    saved = result.get("action_failure_event") or {}
    saved_prediction = saved.get("actuator_prediction") or {}
    direct_reproduced = bool(
        continuation
        and np.array_equal(
            np.asarray(continuation["baseline_action_norm_tsc"], dtype=float),
            np.asarray(saved["baseline_action_norm_tsc"], dtype=float),
        )
        and math.isclose(
            float(continuation["direct_finish_incremental_normalized_action_linf"]),
            float(saved["incremental_normalized_action_linf"]),
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        and np.allclose(
            np.asarray(continuation["direct_finish_action_norm_tsc"], dtype=float),
            np.asarray(saved["finish_action_norm_tsc"], dtype=float),
            rtol=0.0,
            atol=1e-12,
        )
        and continuation["direct_finish_prediction"] == saved_prediction
        and continuation["stored_center_card15_fields"]
        == saved["stored_center_card15_fields"]
        and continuation["issue_target_card15_fields"]
        == saved["issue_target_card15_fields"]
        and continuation["previous_intermediate_card15_fields"]
        == saved["intermediate_card15_fields"]
    )
    forbidden = 0
    if continuation:
        forbidden = sum(
            bool(value)
            for key, value in continuation.items()
            if key.endswith("_used")
        )
    passed = bool(
        len(trajectory) == 20
        and len(source_trace) == 19
        and result.get("completed")
        and not result.get("success")
        and result.get("failure_class") == "structured_action_schedule_gate"
        and prefix_action_exact
        and prefix_trace_exact
        and direct_reproduced
        and continuation
        and continuation.get("passed")
        and all(bool(value) for value in continuation["criteria"].values())
        and forbidden == 0
        and not replay_error
    )
    return {
        "source_experiment_id": spec["experiment_id"],
        "source_raw_sha256": _sha256(raw_path),
        "pair_id": spec["pair_id"],
        "history_member": spec["history_member"],
        "sequence_index": int(spec["s24_sequence_index"]),
        "source_trajectory_count": len(trajectory),
        "source_trace_count": len(source_trace),
        "source_prefix_action_exact": prefix_action_exact,
        "source_prefix_trace_exact": prefix_trace_exact,
        "maximum_source_action_difference": maximum_action_difference,
        "saved_direct_finish_reproduced": direct_reproduced,
        "continuation_event": continuation,
        "forbidden_input_count": forbidden,
        "state20_used": False,
        "replay_error": replay_error,
        "passed": passed,
    }


def _candidate_specs(
    rows: Sequence[Mapping[str, Any]],
    specs: Sequence[Mapping[str, Any]],
    cfg: Mapping[str, Any],
) -> list[dict[str, Any]]:
    by_id = {str(spec["experiment_id"]): spec for spec in specs}
    output = []
    for row in sorted(
        rows,
        key=lambda item: (
            str(item["pair_id"]),
            str(item["history_member"]),
            int(item["sequence_index"]),
        ),
    ):
        source = copy.deepcopy(by_id[str(row["source_experiment_id"])])
        seed = {
            "source_d1r4_experiment_id": row["source_experiment_id"],
            "source_raw_sha256": row["source_raw_sha256"],
            "design_document_sha256": cfg["design_document_sha256"],
            "recursive_contract": cfg["recursive_contract"],
        }
        experiment_id = "s42r3c3t13s24d1r6_" + _digest(seed)[:20]
        source.update(
            {
                "stage": cfg["next_stage"]["stage"],
                "campaign_identity": cfg["next_stage"]["campaign_identity"],
                "controller_revision": cfg["next_stage"]["controller_revision"],
                "probe_primitive_revision": cfg["next_stage"]["controller_revision"],
                "experiment_id": experiment_id,
                "environment_variant": "stage4_2r3c3t13s24d1r6_" + experiment_id,
                "kind": "stage4_2r3c3t13s24d1r6_recursive_split_return_safety_sentinel",
                "phase": "prospective_recursive_split_return_safety_sentinel",
                "d1r6_recursive_contract": copy.deepcopy(cfg["recursive_contract"]),
                "d1r6_source_d1r4_experiment_id": row["source_experiment_id"],
                "source_result_available_to_controller": False,
                "pair_or_history_label_available_to_controller": False,
                "partition_label_available_to_controller": False,
                "probe_trajectory_allowed_in_expert_dataset": False,
            }
        )
        output.append(source)
    if len({spec["experiment_id"] for spec in output}) != len(output):
        raise ValueError("D1R5 candidate identity collision")
    return output


def _load_d1r4_context(args: argparse.Namespace) -> d1r4.Context:
    return d1r4.load_config(
        args.source_d1r4_config,
        source_d1r2_run=args.source_d1r2_run,
        source_d1r3_output=args.source_d1r3_output,
        source_d1r3_primary_log=args.source_d1r3_primary_log,
        source_d1r3_repeat_log=args.source_d1r3_repeat_log,
        source_d1r1_output=args.source_d1r1_output,
        source_d1r1_log=args.source_d1r1_log,
        source_s21_run=args.source_s21_run,
        source_s23r1_output=args.source_s23r1_output,
        run_dir=args.source_d1r4_run,
        **d1r4._source_kwargs(args),
    )


def run_audit(args: argparse.Namespace) -> dict[str, Any]:
    config_path = args.config.expanduser().resolve()
    cfg = _read_json(config_path)
    _validate_config(cfg, config_path)
    output = args.output.expanduser().resolve()
    if output.exists():
        raise ValueError("D1R5 output directory must be new")
    ctx = _load_d1r4_context(args)
    specs, source = _authenticate_source(ctx, cfg, args.complete_log)
    library, bundle, selector = d1r2.s24._library_bundle_selector(
        ctx.base_d1r2_ctx.base_s24_ctx
    )
    rows = [
        _replay_one(ctx, cfg, spec, library, bundle, selector, index)
        for index, spec in enumerate(specs)
    ]
    candidates = _candidate_specs(rows, specs, cfg)
    continuations = [row["continuation_event"] for row in rows if row.get("continuation_event")]
    primary = bool(
        len(rows) == cfg["primary_gate"]["replay_count"]
        and sum(bool(row["source_prefix_action_exact"]) for row in rows)
        == cfg["primary_gate"]["source_prefix_pass_count"]
        and sum(bool(row["source_prefix_trace_exact"]) for row in rows)
        == cfg["primary_gate"]["source_prefix_pass_count"]
        and sum(bool(row["saved_direct_finish_reproduced"]) for row in rows)
        == cfg["primary_gate"]["direct_failure_reproduction_count"]
        and sum(bool(event.get("passed")) for event in continuations)
        == cfg["primary_gate"]["continuation_pass_count"]
        and len(candidates)
        == cfg["primary_gate"]["candidate_real_sentinel_spec_count"]
        and all(bool(row["passed"]) for row in rows)
        and all(float(event["continuation_incremental_normalized_action_linf"]) == 0.175 for event in continuations)
    )
    route = cfg["routes"]["pass" if primary else "fail"]
    detailed = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "controller_revision": CONTROLLER_REVISION,
        "classification": "zero_new_tsc_causal_recursive_controller_replay",
        "source_authentication": source,
        "replay_count": len(rows),
        "source_prefix_action_exact_count": sum(
            bool(row["source_prefix_action_exact"]) for row in rows
        ),
        "source_prefix_trace_exact_count": sum(
            bool(row["source_prefix_trace_exact"]) for row in rows
        ),
        "direct_failure_reproduction_count": sum(
            bool(row["saved_direct_finish_reproduced"]) for row in rows
        ),
        "continuation_pass_count": sum(
            bool(event.get("passed")) for event in continuations
        ),
        "minimum_direct_finish_increment": min(
            (float(event["direct_finish_incremental_normalized_action_linf"]) for event in continuations),
            default=0.0,
        ),
        "maximum_direct_finish_increment": max(
            (float(event["direct_finish_incremental_normalized_action_linf"]) for event in continuations),
            default=0.0,
        ),
        "maximum_continuation_increment": max(
            (float(event["continuation_incremental_normalized_action_linf"]) for event in continuations),
            default=0.0,
        ),
        "maximum_continuation_total_action": max(
            (float(event["continuation_total_normalized_action_abs"]) for event in continuations),
            default=0.0,
        ),
        "maximum_predicted_current_utilization": max(
            (float(event["predicted_current_utilization"]) for event in continuations),
            default=0.0,
        ),
        "candidate_real_sentinel_spec_count": len(candidates),
        "candidate_real_sentinel_spec_digest": _digest(candidates),
        "forbidden_input_count": sum(int(row["forbidden_input_count"]) for row in rows),
        "state20_used": False,
        "plant_advance_count": 0,
        "new_raw_count": 0,
        "new_snapshot_count": 0,
        "ray_gotsc_tsc_executed": False,
        "formal_tracking_evaluable": False,
        "real_sentinel_execution_authorized": False,
        "full_replacement_campaign_authorized": False,
        "mpc_or_learning_authorized": False,
        "primary_pass": primary,
        "route": route,
        "rows": rows,
    }
    summary = {key: value for key, value in detailed.items() if key != "rows"}
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "config_sha256": _sha256(config_path),
        "design_document_sha256": cfg["design_document_sha256"],
        "source_raw_inventory_digest": source["raw_inventory"]["digest"],
        "candidate_real_sentinel_spec_digest": _digest(candidates),
        "route": route,
        "primary_pass": primary,
        "real_tsc_executed": False,
        "new_raw_count": 0,
    }
    output.mkdir(parents=True, exist_ok=False)
    _write_json(output / "stage4_2r3c3t13s24d1r5_detailed_v1.json", detailed)
    _write_json(output / "stage4_2r3c3t13s24d1r5_summary_v1.json", summary)
    _write_json(output / "stage4_2r3c3t13s24d1r5_manifest_v1.json", manifest)
    _write_json(
        output / "stage4_2r3c3t13s24d1r5_candidate_real_sentinel_specs_v1.json",
        candidates,
    )
    print(json.dumps(summary, sort_keys=True, indent=2, allow_nan=False))
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source-d1r4-config", type=Path, required=True)
    parser.add_argument("--source-d1r4-run", type=Path, required=True)
    parser.add_argument("--complete-log", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    for name in (
        "source-d1r2-run",
        "source-d1r3-output",
        "source-d1r3-primary-log",
        "source-d1r3-repeat-log",
        "source-d1r1-output",
        "source-d1r1-log",
        "source-s21-run",
        "source-s23r1-output",
        "source-stage42r3b-run",
        "source-stage42r3c3-run",
        "source-stage42r3c3-bank-dir",
        "source-stage42r3c3t1-run",
        "source-stage42r3c3t1-audit-dir",
        "source-stage42r3c3t3-controller-bank",
        "q1-run",
        "q2-run",
        "q1-audit",
        "q2-audit",
        "r3b-server-audit",
        "r3b-snapshot-checks",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    return parser


def main() -> None:
    run_audit(_parser().parse_args())


if __name__ == "__main__":
    main()
