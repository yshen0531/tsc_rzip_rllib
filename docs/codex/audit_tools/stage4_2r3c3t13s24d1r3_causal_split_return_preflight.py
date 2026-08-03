"""Zero-new-TSC causal split-return preflight for D1R2 raw trajectories."""

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

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r2_real_tsc_safety_sentinel_forensics as d1r2_forensics,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r2_real_tsc_safety_sentinel as d1r2,
)


STAGE = "Stage4.2R3c3T13S24D1R3"
IDENTITY = "causal_split_exact_return_preflight_v1"
PACKAGE_REVISION = "r42r3c3t13s24d1r3_causal_split_return_preflight_v1"
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


def _validate_config(cfg: Mapping[str, Any], config_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    expected_path = (
        root
        / "configs/stage4_2r3c3t13s24d1r3_causal_split_return_preflight_v1.json"
    ).resolve()
    if config_path.resolve() != expected_path:
        raise ValueError("D1R3 config path changed")
    exact = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "package_revision": PACKAGE_REVISION,
        "selection_status": (
            "frozen_after_d1r2_fail_before_d1r3_implementation_or_candidate_replay"
        ),
    }
    if any(cfg.get(key) != value for key, value in exact.items()):
        raise ValueError("D1R3 frozen identity changed")
    design = (root / str(cfg["design_document"])).resolve()
    if not design.is_file() or _sha256(design) != cfg["design_document_sha256"]:
        raise ValueError("D1R3 design document changed")
    source = cfg["source_contract"]
    required_source = {
        "raw_count": 54,
        "raw_total_bytes": 3_078_383,
        "full_success_count": 45,
        "structured_safe_stop_count": 9,
        "restart_causality_calibration_pass_count": 54,
        "issue_gate_pass_count": 216,
        "successful_cancel_gate_pass_count": 207,
        "failed_cancel_attempt_count": 9,
        "original_cancel_cap_failure_count": 5,
    }
    if any(source.get(key) != value for key, value in required_source.items()):
        raise ValueError("D1R3 frozen source counts changed")
    if any(
        len(str(source[key])) != 64
        for key in (
            "execution_module_sha256",
            "execution_config_sha256",
            "raw_inventory_digest",
            "normalized_spec_digest",
            "prospective_audit_sha256",
            "retrospective_audit_sha256",
            "complete_log_sha256",
        )
    ):
        raise ValueError("D1R3 frozen source hash changed")
    split = cfg["split_contract"]
    if (
        float(split["direct_cancel_threshold"]) != 0.24
        or float(split["split_construction_target_increment"]) != 0.175
        or float(split["maximum_split_start_increment"]) != 0.18
        or float(split["maximum_original_increment"]) != 0.25
        or float(split["maximum_total_normalized_action_abs"]) != 1.0
        or float(split["maximum_current_utilization"]) != 0.55
        or int(split["split_start_task_step"]) != 18
        or int(split["split_finish_task_step"]) != 19
        or int(split["split_slot"]) != 3
        or split["failed_sequence_indices"] != [6, 10, 18]
        or not all(
            bool(split[key])
            for key in (
                "require_exact_card15_intermediate",
                "require_exact_decimal_telescoping_net",
                "require_no_saturation_or_clipping",
            )
        )
        or bool(split["controller_label_access"])
        or bool(split["controller_future_access"])
    ):
        raise ValueError("D1R3 split construction changed")
    execution = cfg["execution_contract"]
    if execution != {
        "new_raw_files": 0,
        "new_snapshots": 0,
        "ray_allowed": False,
        "gotsc_allowed": False,
        "tsc_allowed": False,
        "plant_advance_allowed": False,
        "server_side_raw_processing": True,
    }:
        raise ValueError("D1R3 zero-TSC contract changed")
    if bool(cfg["scientific_scope"]["bc_dagger_or_rl_allowed"]):
        raise ValueError("D1R3 may not authorize learning")


class CausalSplitReturnPreflightController(
    d1r2.GeometryRestoredSafetySentinelController
):
    """D1R2 controller with only the frozen split-start branch added."""

    def __init__(self, *args: Any, split_cfg: Mapping[str, Any], **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.split_cfg = copy.deepcopy(dict(split_cfg))
        self._last_split_start_event: dict[str, Any] | None = None

    def _cancel(
        self, slot: int, currents: np.ndarray, baseline_action: np.ndarray
    ) -> tuple[np.ndarray, dict[str, Any]]:
        if self._active_issue is None or int(self._active_issue["slot"]) != slot:
            raise ValueError("D1R3 cancellation has no matching causal issue")
        stored = tuple(map(str, self._active_issue["center_card15_fields"]))
        issue_target = tuple(map(str, self._active_issue["target_card15_fields"]))
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
        threshold = float(self.split_cfg["direct_cancel_threshold"])
        if direct_increment <= threshold + 1e-12:
            return super()._cancel(slot, currents, baseline_action)

        baseline = np.asarray(baseline_action, dtype=float).reshape(N_COILS)
        direct_action = np.asarray(direct["action_norm_tsc"], dtype=float).reshape(
            N_COILS
        )
        target_increment = float(
            self.split_cfg["split_construction_target_increment"]
        )
        alpha = min(1.0, target_increment / direct_increment)
        split_action = baseline + alpha * (direct_action - baseline)
        intermediate = self.actuator.apply(currents, split_action)
        reproduced = self.actuator.apply(currents, split_action)
        intermediate_fields = tuple(map(str, intermediate.card15_fields))
        turns = np.asarray(self.turns_tsc, dtype=float)
        target_current = np.asarray(
            [
                float(d1r2.s24.s21.s16.s9._decimal_field(field)) * 1000.0 / turn
                for field, turn in zip(intermediate_fields, turns)
            ],
            dtype=float,
        )
        minimum = np.asarray(self.base.min_current, dtype=float)
        maximum = np.asarray(self.base.max_current, dtype=float)
        utilization = d1r2.s24.s21.s16.s9._current_utilization(
            target_current, minimum, maximum
        )
        increment = float(np.max(np.abs(split_action - baseline)))
        total = float(np.max(np.abs(split_action)))
        telescope = all(
            (
                d1r2.s24.s21.s16.s9._decimal_field(target)
                - d1r2.s24.s21.s16.s9._decimal_field(center)
            )
            + (
                d1r2.s24.s21.s16.s9._decimal_field(middle)
                - d1r2.s24.s21.s16.s9._decimal_field(target)
            )
            + (
                d1r2.s24.s21.s16.s9._decimal_field(center)
                - d1r2.s24.s21.s16.s9._decimal_field(middle)
            )
            == Decimal(0)
            for center, target, middle in zip(stored, issue_target, intermediate_fields)
        )
        criteria = {
            "direct_requires_split": direct_increment > threshold + 1e-12,
            "construction_target_exact": math.isclose(
                target_increment, 0.175, rel_tol=0.0, abs_tol=0.0
            ),
            "alpha_strictly_between_zero_and_one": 0.0 < alpha < 1.0,
            "split_start_increment": increment
            <= float(self.split_cfg["maximum_split_start_increment"]) + 1e-12,
            "total_action": total
            <= float(self.split_cfg["maximum_total_normalized_action_abs"])
            + 1e-12,
            "current_bounds": bool(
                np.all(target_current >= minimum) and np.all(target_current <= maximum)
            ),
            "current_utilization": utilization
            <= float(self.split_cfg["maximum_current_utilization"]) + 1e-12,
            "exact_card15_intermediate": all(
                len(field) == 10
                and d1r2.s24.s21.s16.s9.format_number(
                    float(d1r2.s24.s21.s16.s9._decimal_field(field))
                )
                == field
                for field in intermediate_fields
            ),
            "intermediate_reproduction": list(reproduced.card15_fields)
            == list(intermediate_fields),
            "intermediate_differs_from_issue_target": list(intermediate_fields)
            != list(issue_target),
            "intermediate_differs_from_center": list(intermediate_fields)
            != list(stored),
            "exact_decimal_telescoping_net": telescope,
            "no_saturation": not any(intermediate.action_saturated),
            "no_current_clip": not any(intermediate.current_limit_clipped),
        }
        event = {
            "event": "sequential_cancel_split_start",
            "stage": STAGE,
            "identity": IDENTITY,
            "slot": slot,
            "task_step": self.step,
            "stored_center_card15_fields": list(stored),
            "issue_target_card15_fields": list(issue_target),
            "intermediate_card15_fields": list(intermediate_fields),
            "direct_incremental_normalized_action_linf": direct_increment,
            "direct_total_normalized_action_abs": float(
                direct["total_normalized_action_abs"]
            ),
            "direct_predicted_current_utilization": float(
                direct["predicted_maximum_current_utilization"]
            ),
            "direct_target_card15_fields": list(direct["target_fields"]),
            "split_construction_target_increment": target_increment,
            "alpha": alpha,
            "split_start_incremental_normalized_action_linf": increment,
            "split_start_total_normalized_action_abs": total,
            "predicted_current_utilization": utilization,
            "direct_action_norm_tsc": direct_action.tolist(),
            "baseline_action_norm_tsc": baseline.tolist(),
            "split_start_action_norm_tsc": split_action.tolist(),
            "criteria": criteria,
            "passed": bool(all(criteria.values())),
        }
        self._last_split_start_event = copy.deepcopy(event)
        if not event["passed"]:
            raise ValueError(
                "D1R3 split-start construction failed: "
                + json.dumps(event, sort_keys=True)
            )
        return split_action, event


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
        "total_bytes": sum(row["bytes"] for row in rows),
        "digest": digest.hexdigest(),
        "files": rows,
    }


def _authenticate_source(
    ctx: d1r2.Context, cfg: Mapping[str, Any], complete_log: Path
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source = cfg["source_contract"]
    if ctx.paths.run_dir.name != source["run_name"]:
        raise ValueError("D1R3 D1R2 run identity changed")
    root = d1r2._project_root()
    if (
        _sha256(
            root
            / "tsc_rzip_rllib/diagnostics/"
            "stage4_2r3c3t13s24d1r2_real_tsc_safety_sentinel.py"
        )
        != source["execution_module_sha256"]
        or _sha256(ctx.config_path) != source["execution_config_sha256"]
        or _sha256(complete_log) != source["complete_log_sha256"]
    ):
        raise ValueError("D1R3 D1R2 execution source hash changed")
    prospective = ctx.paths.analysis / "independent_server_forensics.json"
    retrospective = (
        ctx.paths.analysis / "retrospective_structured_failure_prefix_forensics_v1.json"
    )
    if (
        _sha256(prospective) != source["prospective_audit_sha256"]
        or _sha256(retrospective) != source["retrospective_audit_sha256"]
    ):
        raise ValueError("D1R3 D1R2 forensic audit hash changed")
    prior = _read_json(retrospective)
    state = _read_json(ctx.paths.state)
    manifest = _read_json(ctx.paths.manifest)
    final = _read_json(ctx.paths.final)
    specs = d1r2._saved_specs(ctx)
    raw = _inventory(list(ctx.paths.raw.glob("*.json.gz")))
    snapshots = d1r2._selected_snapshot_audit(d1r2._selected_context_table(specs))
    passed = bool(
        raw["count"] == source["raw_count"]
        and raw["total_bytes"] == source["raw_total_bytes"]
        and raw["digest"] == source["raw_inventory_digest"]
        and d1r2._digest(specs) == source["normalized_spec_digest"]
        and state.get("finished")
        and state.get("real_tsc_executed")
        and state.get("verdict", {}).get("route") == source["required_route"]
        and manifest.get("route") == final.get("route") == source["required_route"]
        and snapshots.get("passed")
        and snapshots.get("pass_count") == 18
        and prior.get("forensic_recomputation_passed")
        and prior.get("full_horizon_success_count") == source["full_success_count"]
        and prior.get("structured_safe_stop_count")
        == source["structured_safe_stop_count"]
        and prior.get("restart_exact_count")
        == prior.get("causality_pass_count")
        == prior.get("calibration_pass_count")
        == source["restart_causality_calibration_pass_count"]
        and prior.get("issue_gate_pass_count") == source["issue_gate_pass_count"]
        and prior.get("successful_cancel_gate_pass_count")
        == source["successful_cancel_gate_pass_count"]
        and prior.get("failed_cancel_attempt_count")
        == source["failed_cancel_attempt_count"]
        and prior.get("original_cancel_cap_failure_count")
        == source["original_cancel_cap_failure_count"]
    )
    if not passed:
        raise ValueError(cfg["routes"]["source_stop"])
    return specs, {
        "passed": True,
        "run_dir": str(ctx.paths.run_dir),
        "raw_inventory": raw,
        "snapshot_pass_count": snapshots["pass_count"],
        "prospective_audit_sha256": _sha256(prospective),
        "retrospective_audit_sha256": _sha256(retrospective),
        "complete_log_sha256": _sha256(complete_log),
    }


def _replay_one(
    ctx: d1r2.Context,
    cfg: Mapping[str, Any],
    spec: Mapping[str, Any],
    library: Mapping[str, Any],
    bundle: Mapping[str, Any],
    selector: Mapping[str, Any],
    index: int,
) -> dict[str, Any]:
    result = d1r2._read_raw(ctx.paths.raw / f"{spec['experiment_id']}.json.gz")
    trajectory = list(result["trajectory"])
    source_trace = list(result["controller_trace"])
    payload = _read_json(ctx.paths.variants / f"payload_{spec['experiment_id']}.json")
    worker = d1r2.s24.s21.s16.s9.t11.t1.r1.LocalPlantReplayWorker(
        payload,
        library,
        bundle,
        f"stage42r3c3t13s24d1r3_replay_{index:03d}",
        selector,
    )
    maximum_prefix_difference = 0.0
    prefix_equal = True
    trace_equal = True
    split_event: dict[str, Any] | None = None
    replay_error = ""
    try:
        s21_ctx = ctx.base_s24_ctx.base_ctx
        controller = CausalSplitReturnPreflightController(
            worker.base_worker,
            bundle,
            d1r2.s24.s21.s16.s9._controller_spec(spec),
            trajectory[0],
            s21_ctx.base_ctx.cfg["lattice_probe"],
            s21_ctx.base_ctx.cfg["active_calibration"],
            s21_ctx.cfg["causal_model"],
            ctx.cfg["schedule_contract"],
            split_cfg=cfg["split_contract"],
        )
        replay_steps = len(source_trace) if result.get("success") else len(source_trace) + 1
        for step in range(replay_steps):
            try:
                action, replay_trace = controller.action(trajectory[step])
            except Exception as exc:
                split_event = copy.deepcopy(controller._last_split_start_event)
                replay_error = repr(exc)
                break
            if step < len(source_trace):
                source_action = np.asarray(
                    source_trace[step]["action_norm_tsc"], dtype=float
                )
                difference = float(np.max(np.abs(action - source_action)))
                maximum_prefix_difference = max(maximum_prefix_difference, difference)
                prefix_equal = bool(prefix_equal and difference <= 1e-12)
                trace_equal = bool(trace_equal and replay_trace == source_trace[step])
            else:
                split_event = copy.deepcopy(controller._last_split_start_event)
            if step + 1 < len(trajectory):
                controller.advance(trajectory[step + 1])
    finally:
        worker.close()
    saved_failure = result.get("action_failure_event") or {}
    success = bool(result.get("success"))
    saved_prediction = saved_failure.get("actuator_prediction") or {}
    direct_reproduced = bool(
        success
        or (
            split_event is not None
            and math.isclose(
                float(split_event["direct_incremental_normalized_action_linf"]),
                float(saved_failure["incremental_normalized_action_linf"]),
                rel_tol=0.0,
                abs_tol=1e-12,
            )
            and np.allclose(
                np.asarray(split_event["direct_action_norm_tsc"], dtype=float),
                np.asarray(saved_prediction["action_norm_tsc"], dtype=float),
                rtol=0.0,
                atol=1e-12,
            )
            and list(split_event["direct_target_card15_fields"])
            == list(saved_prediction["target_fields"])
            and list(split_event["stored_center_card15_fields"])
            == list(saved_failure["stored_center_card15_fields"])
            and list(split_event["issue_target_card15_fields"])
            == list(saved_failure["issue_target_card15_fields"])
        )
    )
    passed = bool(
        prefix_equal
        and trace_equal
        and direct_reproduced
        and not replay_error
        and ((success and split_event is None) or (not success and split_event and split_event["passed"]))
    )
    return {
        "source_experiment_id": spec["experiment_id"],
        "source_raw_sha256": _sha256(
            ctx.paths.raw / f"{spec['experiment_id']}.json.gz"
        ),
        "pair_id": spec["pair_id"],
        "history_member": spec["history_member"],
        "sequence_index": int(spec["s24_sequence_index"]),
        "source_success": success,
        "source_trajectory_count": len(trajectory),
        "source_trace_count": len(source_trace),
        "unchanged_source_action_prefix": prefix_equal,
        "unchanged_source_trace_prefix": trace_equal,
        "maximum_source_action_prefix_difference": maximum_prefix_difference,
        "direct_failure_increment_reproduced": direct_reproduced,
        "split_branch_selected": split_event is not None,
        "split_start_event": split_event,
        "replay_error": replay_error,
        "passed": passed,
    }


def _sentinel_specs(
    rows: Sequence[Mapping[str, Any]], specs: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> list[dict[str, Any]]:
    spec_by_id = {str(spec["experiment_id"]): spec for spec in specs}
    output = []
    for row in sorted(
        (
            item
            for item in rows
            if item["split_branch_selected"] and item["passed"]
        ),
        key=lambda item: (
            str(item["pair_id"]),
            str(item["history_member"]),
            int(item["sequence_index"]),
        ),
    ):
        source = copy.deepcopy(spec_by_id[str(row["source_experiment_id"])])
        seed = {
            "source_experiment_id": row["source_experiment_id"],
            "source_raw_sha256": row["source_raw_sha256"],
            "design_document_sha256": cfg["design_document_sha256"],
            "split_contract": cfg["split_contract"],
        }
        experiment_id = "s42r3c3t13s24d1r4_" + _digest(seed)[:20]
        source.update(
            {
                "stage": cfg["next_stage"]["stage"],
                "campaign_identity": cfg["next_stage"]["campaign_identity"],
                "controller_revision": cfg["next_stage"]["controller_revision"],
                "probe_primitive_revision": cfg["next_stage"]["controller_revision"],
                "experiment_id": experiment_id,
                "environment_variant": "stage4_2r3c3t13s24d1r4_" + experiment_id,
                "kind": "stage4_2r3c3t13s24d1r4_causal_split_return_safety_sentinel",
                "phase": "prospective_causal_split_exact_return_safety_sentinel",
                "d1r4_split_contract": copy.deepcopy(cfg["split_contract"]),
                "d1r4_source_d1r2_experiment_id": row["source_experiment_id"],
                "source_result_available_to_controller": False,
                "pair_or_history_label_available_to_controller": False,
                "partition_label_available_to_controller": False,
                "probe_trajectory_allowed_in_expert_dataset": False,
            }
        )
        output.append(source)
    if len({spec["experiment_id"] for spec in output}) != len(output):
        raise ValueError("D1R3 candidate sentinel identity collision")
    return output


def run_audit(args: argparse.Namespace) -> dict[str, Any]:
    config_path = args.config.expanduser().resolve()
    cfg = _read_json(config_path)
    _validate_config(cfg, config_path)
    output = args.output.expanduser().resolve()
    if output.exists():
        raise ValueError("D1R3 output directory must be new")
    d1r2_ctx = d1r2.load_config(
        args.source_d1r2_config,
        source_d1r1_output=args.source_d1r1_output,
        source_d1r1_log=args.source_d1r1_log,
        source_s21_run=args.source_s21_run,
        source_s23r1_output=args.source_s23r1_output,
        run_dir=args.source_d1r2_run,
        **d1r2._source_kwargs(args),
    )
    specs, source = _authenticate_source(d1r2_ctx, cfg, args.complete_log)
    library, bundle, selector = d1r2.s24._library_bundle_selector(
        d1r2_ctx.base_s24_ctx
    )
    rows = [
        _replay_one(d1r2_ctx, cfg, spec, library, bundle, selector, index)
        for index, spec in enumerate(specs)
    ]
    sentinel = _sentinel_specs(rows, specs, cfg)
    success_rows = [row for row in rows if row["source_success"]]
    failure_rows = [row for row in rows if not row["source_success"]]
    split_rows = [row for row in rows if row["split_branch_selected"]]
    expected_sequences = sorted(
        int(value) for value in cfg["split_contract"]["failed_sequence_indices"]
        for _ in range(3)
    )
    split_localization_pass = bool(
        sorted(int(row["sequence_index"]) for row in split_rows)
        == expected_sequences
        and all(
            int(row["split_start_event"]["task_step"])
            == int(cfg["split_contract"]["split_start_task_step"])
            and int(row["split_start_event"]["slot"])
            == int(cfg["split_contract"]["split_slot"])
            for row in split_rows
        )
    )
    split_maximum = max(
        (
            float(row["split_start_event"]["split_start_incremental_normalized_action_linf"])
            for row in split_rows
        ),
        default=0.0,
    )
    primary = bool(
        len(rows) == cfg["primary_gate"]["replay_count"]
        and len(success_rows) == cfg["primary_gate"]["unchanged_full_success_count"]
        and len(failure_rows) == cfg["primary_gate"]["unchanged_failure_prefix_count"]
        and len(split_rows) == cfg["primary_gate"]["split_start_pass_count"]
        and len(sentinel) == cfg["primary_gate"]["candidate_sentinel_spec_count"]
        and all(row["passed"] for row in rows)
        and all(row["unchanged_source_trace_prefix"] for row in rows)
        and all(not row["split_branch_selected"] for row in success_rows)
        and all(row["split_branch_selected"] for row in failure_rows)
        and split_localization_pass
        and split_maximum
        <= float(cfg["split_contract"]["maximum_split_start_increment"]) + 1e-12
    )
    route = cfg["routes"]["pass" if primary else "fail"]
    detailed = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "classification": "zero_new_tsc_causal_controller_prefix_replay",
        "source_authentication": source,
        "replay_count": len(rows),
        "unchanged_full_success_count": sum(
            row["source_success"] and row["passed"] for row in rows
        ),
        "unchanged_failure_prefix_count": sum(
            (not row["source_success"]) and row["unchanged_source_action_prefix"]
            for row in rows
        ),
        "split_start_pass_count": sum(
            bool(row["split_start_event"] and row["split_start_event"]["passed"])
            for row in rows
        ),
        "split_failure_localization_passed": split_localization_pass,
        "maximum_split_start_increment": split_maximum,
        "candidate_sentinel_spec_count": len(sentinel),
        "candidate_sentinel_spec_digest": _digest(sentinel),
        "plant_advance_count": 0,
        "new_raw_count": 0,
        "new_snapshot_count": 0,
        "ray_gotsc_tsc_executed": False,
        "split_finish_evaluated": False,
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
        "package_revision": PACKAGE_REVISION,
        "config_path": str(config_path),
        "config_sha256": _sha256(config_path),
        "design_document_sha256": cfg["design_document_sha256"],
        "source_raw_inventory_digest": source["raw_inventory"]["digest"],
        "candidate_sentinel_spec_digest": _digest(sentinel),
        "route": route,
        "primary_pass": primary,
        "real_tsc_executed": False,
        "new_raw_count": 0,
    }
    output.mkdir(parents=True, exist_ok=False)
    _write_json(output / "stage4_2r3c3t13s24d1r3_detailed_v1.json", detailed)
    _write_json(output / "stage4_2r3c3t13s24d1r3_summary_v1.json", summary)
    _write_json(output / "stage4_2r3c3t13s24d1r3_manifest_v1.json", manifest)
    _write_json(output / "stage4_2r3c3t13s24d1r3_candidate_sentinel_specs_v1.json", sentinel)
    print(json.dumps(summary, sort_keys=True, indent=2, allow_nan=False))
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source-d1r2-config", type=Path, required=True)
    parser.add_argument("--source-d1r2-run", type=Path, required=True)
    parser.add_argument("--complete-log", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    for name in (
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
