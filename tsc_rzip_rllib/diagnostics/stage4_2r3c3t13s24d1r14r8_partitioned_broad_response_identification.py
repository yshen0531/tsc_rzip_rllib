"""Partitioned broad authentic response identification for Stage4.2 R8.

The campaign is deliberately phase locked.  It authenticates and freezes all
prospective identities before TSC, then admits training, calibration and
holdout raw in that order.  Probe trajectories are identification evidence
only and are never expert data.
"""

from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import time
import traceback
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r7_causal_response_model as r7_source,
    stage4_2r3c3t13s24d1r14r7r2_action_conditioned_full_history_kernel as r7r2,
)
from tsc_rzip_rllib.control import action_conditioned_history_response_model as response_model
from tsc_rzip_rllib.control import causal_response_model as response_metrics
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r11_full_replacement_sequential_transition_identification as d1r11,
    stage4_2r3c3t13s24d1r14r2_mixed_basis_signed_excitation_sentinel as r2,
    stage4_2r3c3t13s24d1r14r4_time_shifted_sign_split_sentinel as r4,
    stage4_2r3c3t13s24d1r14r6_direction0_replacement_sentinel as r6,
)


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S24D1R14R8"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification"
CAMPAIGN_IDENTITY = "partitioned_broad_deconfounded_response_identification_v1"
CONTROLLER_REVISION = "inherited_exact_card15_issue_cancel_v42r3c3t13s24d1r14r8_v1"
N_COILS = 14
PREFIX_END = 10
ISSUE_STEPS = (10, 14, 18, 22)
CANCEL_OFFSET = 1
ZERO_AFTER_OFFSET = 2
HISTORIES = ("minus_first", "plus_first")
PHASES = ("training", "calibration", "holdout")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _matrix_digest(value: Sequence[Sequence[float]]) -> str:
    matrix = np.ascontiguousarray(np.asarray(value, dtype="<f8"))
    return hashlib.sha256(matrix.tobytes(order="C")).hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def _read_gz(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(
            stream,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )


def _write_gz(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _inventory(directory: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    rows = []
    for path in sorted(directory.glob("*.json.gz")):
        size = path.stat().st_size
        sha = _sha256(path)
        digest.update(f"{path.name}\0{size}\0{sha}\n".encode())
        rows.append({"name": path.name, "size": size, "sha256": sha})
    return {
        "count": len(rows),
        "bytes": sum(int(row["size"]) for row in rows),
        "digest": digest.hexdigest(),
        "rows": rows,
    }


@dataclass(frozen=True)
class Paths:
    run_dir: Path
    stage_dir: Path
    variants: Path
    specs: Path
    source_reference: Path
    raw: Path
    analysis: Path
    model: Path
    state: Path
    manifest: Path

    def phase_raw(self, phase: str) -> Path:
        if phase not in PHASES:
            raise ValueError(f"invalid R8 phase: {phase}")
        return self.raw / phase


def _paths(run_dir: Path) -> Paths:
    root = run_dir.expanduser().resolve()
    stage = root / RUN_NAME
    return Paths(
        run_dir=root,
        stage_dir=stage,
        variants=stage / "variants",
        specs=stage / "specs",
        source_reference=stage / "source_reference",
        raw=stage / "raw",
        analysis=stage / "analysis",
        model=stage / "model",
        state=stage / "stage_state.json",
        manifest=stage / "stage_manifest.json",
    )


@dataclass(frozen=True)
class Context:
    cfg: dict[str, Any]
    config_path: Path
    d1r11_ctx: Any
    source_d1r11_run: Path
    source_response_runs: dict[str, Path]
    paths: Paths


def _validate_config(cfg: Mapping[str, Any], config_path: Path) -> None:
    root = _project_root()
    exact = {
        "schema_version": 1,
        "stage": STAGE,
        "run_name": RUN_NAME,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": "r42r3c3t13s24d1r14r8_partitioned_broad_response_identification_v1",
    }
    for key, value in exact.items():
        if cfg.get(key) != value:
            raise ValueError(f"R8 frozen {key} changed")
    expected_config = (
        root
        / "configs/stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification_370ms.json"
    ).resolve()
    if config_path.resolve() != expected_config:
        raise ValueError("R8 config path changed")
    for key in ("design_document", "source_d1r11_config"):
        path = (root / str(cfg[key])).resolve()
        if root not in path.parents or not path.is_file():
            raise ValueError(f"R8 {key} is outside the package")
        if _sha256(path) != str(cfg[f"{key}_sha256"]):
            raise ValueError(f"R8 {key} hash changed")

    request = cfg["request_contract"]
    canonical = np.asarray(request["canonical_matrix_columns"], dtype=float)
    replacement = np.asarray(request["replacement_matrix_columns"], dtype=float)
    if (
        tuple(map(int, request["issue_task_steps"])) != ISSUE_STEPS
        or canonical.shape != (4, 4)
        or replacement.shape != (4, 4)
        or _matrix_digest(canonical) != str(request["canonical_matrix_digest"])
        or _matrix_digest(replacement) != str(request["replacement_matrix_digest"])
        or not np.array_equal(replacement[:, 1:], canonical[:, 1:])
        or not np.array_equal(replacement[:, 0], 1.5 * canonical[:, 0])
        or float(request["canonical_scale"]) != 1.0
        or int(request["replacement_direction_index"]) != 0
        or float(request["replacement_scale"]) != 1.5
        or tuple(map(int, request["replacement_issue_task_steps"])) != (14, 18, 22)
        or float(request["coordinate_absolute_tolerance"]) != 1e-15
    ):
        raise ValueError("R8 action request contract changed")

    partitions = cfg["pair_partitions"]
    groups = [list(map(str, partitions[key])) for key in (
        "consumed_training", "training_extension", "calibration", "holdout"
    )]
    if (
        tuple(map(len, groups)) != (4, 8, 4, 4)
        or len(set().union(*map(set, groups))) != 20
        or sum(map(len, groups)) != 20
    ):
        raise ValueError("R8 whole-pair split changed")
    rollouts = cfg["rollout_contract"]
    expected_rollouts = {
        "histories_per_pair": 2,
        "responses_per_context": 38,
        "rollouts_per_context": 39,
        "training_extension_pairs": 8,
        "training_extension_contexts": 16,
        "training_extension_rollouts": 624,
        "training_existing_responses": 304,
        "training_new_responses": 608,
        "training_combined_responses": 912,
        "training_combined_pairs": 12,
        "calibration_pairs": 4,
        "calibration_contexts": 8,
        "calibration_rollouts": 312,
        "calibration_responses": 304,
        "holdout_pairs": 4,
        "holdout_contexts": 8,
        "holdout_rollouts": 312,
        "holdout_responses": 304,
        "maximum_new_rollouts": 1248,
    }
    if any(int(rollouts.get(key, -1)) != value for key, value in expected_rollouts.items()):
        raise ValueError("R8 rollout contract changed")

    bank = cfg["bank_contract"]
    model_cfg = cfg["model_contract"]
    gates = cfg["gates"]
    controller = cfg["controller_contract"]
    timing = cfg["formal_timing_contract"]
    if (
        tuple(map(float, bank["response_scales"])) != (0.03, 0.03, 0.1, 0.1, 10000.0)
        or tuple(map(float, bank["target_scales"])) != (0.03, 0.03, 10000.0)
        or tuple(map(int, bank["history_offsets"])) != tuple(range(23))
        or float(bank["dt_s"]) != 0.01
        or int(bank["maximum_relative_lag"]) != 27
        or int(bank["direction_count"]) != 4
        or tuple(map(int, model_cfg["pca_ranks"])) != (4, 8, 12)
        or tuple(map(float, model_cfg["rbf_median_distance_multipliers"])) != (0.5, 1.0, 2.0)
        or tuple(map(float, model_cfg["kernel_ridges"])) != (1e-6, 1e-3, 1e-1)
        or len(response_model.candidates(cfg)) != 27
        or int(controller["delegated_last_task_step"]) != 9
        or int(controller["cancel_step_offset"]) != 1
        or int(controller["zero_after_cancel_step_offset"]) != 2
        or int(controller["zero_action_width"]) != N_COILS
        or tuple(float(controller[key]) for key in (
            "maximum_incremental_normalized_action_linf",
            "maximum_online_cancel_incremental_linf",
            "maximum_total_normalized_action_abs",
            "maximum_current_utilization",
            "minimum_desired_applied_current_cosine",
            "maximum_relative_off_basis_residual",
        )) != (0.25, 0.24, 1.0, 0.55, 0.98, 0.1)
        or not all(bool(controller[key]) for key in (
            "require_exact_stored_center_cancellation",
            "require_exact_zero_target_jump_net",
            "require_exact_source_prefix",
            "require_fresh_controller",
            "require_fresh_tsc_process",
            "forbid_future_r17_controller_execution",
        ))
        or tuple(int(timing[key]) for key in (
            "normal_arrival_deadline_step", "normal_hold_through_step",
            "weak_arrival_deadline_step", "weak_hold_through_step",
        )) != (25, 35, 27, 37)
        or bool(timing["arrival_deadline_expansion_allowed"])
        or not bool(timing["formal_tracking_diagnostic_only"])
        or tuple(float(gates[key]) for key in (
            "maximum_relative_l2_error", "minimum_response_cosine",
            "minimum_peak_ratio", "maximum_peak_ratio",
            "maximum_absolute_scaled_point_error", "tube_multiplier",
            "minimum_predicted_peak", "minimum_actual_peak",
            "maximum_condition_number",
        )) != (0.75, 0.8, 0.5, 1.5, 0.1, 2.0, 0.0025, 0.0025, 20.0)
        or tuple(map(float, gates["tube_caps_physical"])) != (0.003, 0.003, 0.01, 0.01, 1000.0)
        or tuple(map(float, gates["response_floor_physical"])) != (1e-9, 1e-9, 1e-7, 1e-7, 1e-4)
        or bool(cfg["probe_trajectories_allowed_in_expert_dataset"])
        or bool(cfg["mpc_validated"])
        or bool(cfg["bc_dagger_or_rl_allowed"])
    ):
        raise ValueError("R8 scientific or safety contract changed")


def load_config(
    config_path: Path,
    *,
    source_d1r11_run: Path,
    source_r2_run: Path,
    source_r4_run: Path,
    source_r6_run: Path,
    run_dir: Path,
    **d1r11_kwargs: Path,
) -> Context:
    config_path = config_path.expanduser().resolve()
    cfg = _read_json(config_path)
    _validate_config(cfg, config_path)
    source_d1r11_run = source_d1r11_run.expanduser().resolve()
    source_s21_run = d1r11_kwargs.pop("source_s21_run")
    source_ctx = d1r11.load_config(
        (_project_root() / str(cfg["source_d1r11_config"])).resolve(),
        source_s21_run=source_s21_run,
        run_dir=source_d1r11_run,
        **d1r11_kwargs,
    )
    return Context(
        cfg=cfg,
        config_path=config_path,
        d1r11_ctx=source_ctx,
        source_d1r11_run=source_d1r11_run,
        source_response_runs={
            "r2": source_r2_run.expanduser().resolve(),
            "r4": source_r4_run.expanduser().resolve(),
            "r6": source_r6_run.expanduser().resolve(),
        },
        paths=_paths(run_dir),
    )


def _phase_for_pair(cfg: Mapping[str, Any], pair: str) -> str:
    groups = cfg["pair_partitions"]
    if pair in set(map(str, groups["training_extension"])):
        return "training"
    if pair in set(map(str, groups["calibration"])):
        return "calibration"
    if pair in set(map(str, groups["holdout"])):
        return "holdout"
    if pair in set(map(str, groups["consumed_training"])):
        # ``consumed_training`` is only R8 bookkeeping for the four D1R11
        # pairs whose responses already exist.  Their immutable prospective
        # D1R11 partition remains ``training``.
        return "training"
    raise ValueError(f"R8 undeclared pair: {pair}")


def _source_artifact(ctx: Context, relative: str) -> Path:
    return ctx.d1r11_ctx.paths.stage_dir / str(
        ctx.cfg["source_d1r11_contract"][relative]
    )


def _load_s21_baselines(ctx: Context) -> dict[tuple[str, str], dict[str, Any]]:
    output: dict[tuple[str, str], dict[str, Any]] = {}
    raw = ctx.d1r11_ctx.source_s21_ctx.paths.raw
    for path in sorted(raw.glob("*.json.gz")):
        result = _read_gz(path)
        spec = result.get("spec") or {}
        if spec.get("r3c3_probe_id") != d1r11.s21.BASELINE_PROBE_ID:
            continue
        key = (str(spec["pair_id"]), str(spec["history_member"]))
        if key in output:
            raise ValueError("R8 duplicate S21 baseline context")
        if not result.get("success") or not result.get("completed"):
            raise ValueError("R8 incomplete S21 baseline")
        output[key] = {"result": result, "path": path, "sha256": _sha256(path)}
    if len(output) != 40:
        raise ValueError("R8 S21 baseline coverage changed")
    return output


def _authenticate_d1r11(ctx: Context) -> dict[str, Any]:
    contract = ctx.cfg["source_d1r11_contract"]
    stage = ctx.d1r11_ctx.paths.stage_dir
    required = {
        "context_table_path": ("context_table_bytes", "context_table_sha256"),
        "all_specs_path": ("all_specs_bytes", "all_specs_sha256"),
        "stage_state_path": ("stage_state_bytes", "stage_state_sha256"),
        "stage_manifest_path": ("stage_manifest_bytes", "stage_manifest_sha256"),
    }
    files = {}
    for path_key, (size_key, sha_key) in required.items():
        path = stage / str(contract[path_key])
        if path.stat().st_size != int(contract[size_key]) or _sha256(path) != str(contract[sha_key]):
            raise ValueError(f"R8 D1R11 {path_key} changed")
        files[path_key] = {"path": str(path), "bytes": path.stat().st_size, "sha256": _sha256(path)}
    state = _read_json(stage / str(contract["stage_state_path"]))
    if (
        state.get("phase_status") != contract["required_phase_status"]
        or (state.get("verdict") or {}).get("route") != contract["required_route"]
        or bool(state.get("heldout_outcomes_opened")) != bool(contract["required_heldout_outcomes_opened"])
        or str(state.get("training_model_sha256") or "")
        or str(state.get("calibrated_tube_sha256") or "")
    ):
        raise ValueError("R8 D1R11 frozen failure state changed")
    training = _inventory(ctx.d1r11_ctx.paths.raw)
    if (
        training["count"] != int(contract["training_raw_count"])
        or training["bytes"] != int(contract["training_raw_bytes"])
        or training["digest"] != str(contract["training_raw_digest"])
    ):
        raise ValueError("R8 D1R11 training raw inventory changed")
    table = _read_json(stage / str(contract["context_table_path"]))
    specs = _read_json(stage / str(contract["all_specs_path"]))
    if (
        len(table) != 40
        or _digest(table) != str(contract["context_table_digest"])
        or len(specs) != 1000
        or _digest(specs) != str(contract["ordered_spec_digest"])
    ):
        raise ValueError("R8 D1R11 table/spec digest changed")
    rebuilt_table = d1r11.build_context_table(ctx.d1r11_ctx)
    rebuilt_specs = d1r11.build_specs(ctx.d1r11_ctx, rebuilt_table)
    if table != rebuilt_table or specs != rebuilt_specs:
        raise ValueError("R8 D1R11 table/spec reconstruction mismatch")
    if int(contract["calibration_raw_count"]) != 0 or int(contract["holdout_raw_count"]) != 0:
        raise ValueError("R8 D1R11 unopened held-out contract changed")
    s21_auth = d1r11._authenticate_s21_source(ctx.d1r11_ctx)
    baselines = _load_s21_baselines(ctx)
    d1r11_baselines = {
        (str(spec["pair_id"]), str(spec["history_member"])): spec
        for spec in specs
        if spec.get("s24_role") == "baseline"
    }
    if len(d1r11_baselines) != 40:
        raise ValueError("R8 D1R11 baseline blueprint coverage changed")
    prefix_rows = []
    for key, spec in sorted(d1r11_baselines.items()):
        phase = str(spec["partition"])
        expected = _phase_for_pair(ctx.cfg, key[0])
        if expected != phase:
            raise ValueError("R8 pair partition differs from D1R11 preregistration")
        if phase != "training":
            continue
        source_path = ctx.d1r11_ctx.paths.raw / f"{spec['experiment_id']}.json.gz"
        if not source_path.is_file():
            raise ValueError("R8 missing D1R11 training baseline")
        source = _read_gz(source_path)
        reference = baselines[key]["result"]
        state_exact = bool(
            len(source.get("trajectory") or []) >= PREFIX_END + 1
            and all(
                r4._semantic_state(current) == r4._semantic_state(prior)
                for current, prior in zip(
                    source["trajectory"][: PREFIX_END + 1],
                    reference["trajectory"][: PREFIX_END + 1],
                )
            )
        )
        trace_exact = bool(
            len(source.get("controller_trace") or []) >= PREFIX_END
            and all(
                r4._source_trace_projection(prior, current)
                for current, prior in zip(
                    source["controller_trace"][:PREFIX_END],
                    reference["controller_trace"][:PREFIX_END],
                )
            )
        )
        prefix_rows.append({"pair_id": key[0], "history_member": key[1], "state_exact": state_exact, "trace_exact": trace_exact})
    if len(prefix_rows) != 24 or not all(row["state_exact"] and row["trace_exact"] for row in prefix_rows):
        raise ValueError("R8 D1R11/S21 causal prefix equivalence failed")
    return {
        "files": files,
        "state": state,
        "training_inventory": training,
        "context_table": table,
        "all_specs": specs,
        "d1r11_baselines": d1r11_baselines,
        "s21_baselines": baselines,
        "s21_authentication": s21_auth,
        "training_prefix_equivalence": {
            "expected": 24,
            "state_exact_count": sum(row["state_exact"] for row in prefix_rows),
            "trace_exact_count": sum(row["trace_exact"] for row in prefix_rows),
            "passed": True,
            "rows": prefix_rows,
        },
    }


def _snapshot_audit(table: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = []
    for context in table:
        directory = Path(str(context["restart_snapshot_dir"])).expanduser().resolve()
        reason = ""
        try:
            manifest = _read_json(directory / "restart_snapshot_manifest.json")
            passed = bool(
                str(manifest.get("digest")) == str(context["restart_snapshot_manifest_digest"])
                and d1r11.s21.s16.s9.t11.t1.r1._validate_snapshot_inventory(directory, manifest)
            )
            if not passed:
                reason = "snapshot inventory mismatch"
        except Exception as exc:
            passed, reason = False, repr(exc)
        rows.append({
            "pair_id": str(context["pair_id"]),
            "history_member": str(context["history_member"]),
            "state_generation_experiment_id": str(context["state_generation_experiment_id"]),
            "snapshot_dir": str(directory),
            "passed": passed,
            "failure_reason": reason,
        })
    return {
        "expected": 40,
        "actual": len(rows),
        "pass_count": sum(row["passed"] for row in rows),
        "passed": len(rows) == 40 and all(row["passed"] for row in rows),
        "rows": rows,
    }


def _roles() -> list[tuple[str, str, int, int, int]]:
    rows = [("baseline", "r4", -1, 0, -1)]
    for issue in ISSUE_STEPS:
        for direction in range(4):
            for sign in (-1, 1):
                rows.append(("canonical", "r2" if issue == 10 else "r4", direction, sign, issue))
        if issue > 10:
            for sign in (-1, 1):
                rows.append(("replacement", "r6", 0, sign, issue))
    if len(rows) != 39:
        raise AssertionError("R8 per-context role coverage changed")
    return rows


def build_specs(
    cfg: Mapping[str, Any],
    baseline_specs: Mapping[tuple[str, str], Mapping[str, Any]],
    s21_baselines: Mapping[tuple[str, str], Mapping[str, Any]],
) -> list[dict[str, Any]]:
    canonical = np.asarray(cfg["request_contract"]["canonical_matrix_columns"], dtype=float)
    replacement = np.asarray(cfg["request_contract"]["replacement_matrix_columns"], dtype=float)
    output = []
    consumed = set(map(str, cfg["pair_partitions"]["consumed_training"]))
    for key in sorted(baseline_specs):
        pair, history = key
        if pair in consumed:
            continue
        source = baseline_specs[key]
        phase = _phase_for_pair(cfg, pair)
        if phase not in PHASES or str(source["partition"]) != phase:
            raise ValueError("R8 source blueprint partition changed")
        s21 = s21_baselines[key]
        staged = []
        for role, kernel, direction, sign, issue in _roles():
            matrix = replacement if role == "replacement" else canonical
            coordinate = np.zeros(4) if role == "baseline" else matrix[:, direction] * sign
            digest = (
                "" if role == "baseline" else str(cfg["request_contract"][
                    "replacement_matrix_digest" if role == "replacement" else "canonical_matrix_digest"
                ])
            )
            identity = {
                "stage": STAGE,
                "campaign_identity": CAMPAIGN_IDENTITY,
                "controller_revision": CONTROLLER_REVISION,
                "partition": phase,
                "pair_id": pair,
                "history_member": history,
                "state_generation_experiment_id": source["state_generation_experiment_id"],
                "snapshot_manifest_digest": source["restart_snapshot_manifest_digest"],
                "role": role,
                "kernel": kernel,
                "direction_index": direction,
                "sign": sign,
                "issue_task_step": issue,
                "requested_matrix_digest": digest,
            }
            experiment_id = d1r11.s21.s16.s9.t11.t1.r3c3._scenario_digest(identity)
            spec = copy.deepcopy(dict(source))
            spec.update({
                "kind": "stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification",
                "stage": STAGE,
                "campaign_identity": CAMPAIGN_IDENTITY,
                "controller_revision": CONTROLLER_REVISION,
                "experiment_id": experiment_id,
                "phase": phase,
                "category": "partitioned_broad_safety_identification_only",
                "partition": phase,
                "environment_variant": f"stage4_2r3c3t13s24d1r14r8_{experiment_id}",
                "baseline_experiment_id": "",
                "source_d1r11_baseline_experiment_id": str(source["experiment_id"]),
                "source_s21_baseline_experiment_id": str(s21["result"]["experiment_id"]),
                "source_s21_baseline_raw_sha256": str(s21["sha256"]),
                "d1r14r8_role": role,
                "d1r14r8_execution_kernel": kernel,
                "d1r14r8_direction_index": direction,
                "d1r14r8_sign": sign,
                "d1r14r8_requested_coordinate": coordinate.tolist(),
                "d1r14r8_requested_matrix_digest": digest,
                "d1r14r8_action_scale": 0.0 if role == "baseline" else (1.5 if role == "replacement" else 1.0),
                "d1r14r8_issue_task_step": issue,
                "d1r14r8_cancel_task_step": -1 if role == "baseline" else issue + CANCEL_OFFSET,
                "d1r14r8_zero_after_task_step": PREFIX_END if role == "baseline" else issue + ZERO_AFTER_OFFSET,
                "probe_trajectory_allowed_in_expert_dataset": False,
                "pair_or_history_label_available_to_controller": False,
                "partition_label_available_to_controller": False,
                "source_result_available_to_controller": False,
                "source_action_available_to_controller": False,
                "source_coil_current_available_to_controller": False,
                "source_wire_current_available_to_controller": False,
                "hidden_wire_current_available_to_controller": False,
                "future_action_count": 0,
                "future_measurement_count": 0,
                "formal_timing_unchanged": True,
            })
            staged.append(spec)
        baseline_id = str(staged[0]["experiment_id"])
        for spec in staged:
            spec["baseline_experiment_id"] = "" if spec["d1r14r8_role"] == "baseline" else baseline_id
            output.append(spec)
    output.sort(key=lambda row: (str(row["partition"]), str(row["pair_id"]), str(row["history_member"]), str(row["experiment_id"])))
    counts = {phase: sum(str(row["partition"]) == phase for row in output) for phase in PHASES}
    if (
        len(output) != 1248
        or len({str(row["experiment_id"]) for row in output}) != 1248
        or counts != {"training": 624, "calibration": 312, "holdout": 312}
    ):
        raise ValueError("R8 prospective identity coverage changed")
    return output


def _static_card15_audit(cfg: Mapping[str, Any]) -> dict[str, Any]:
    zeros = [d1r11.s21.s16.s9.format_number(0.0) for _ in range(N_COILS)]
    steps = [d1r11.s21.s16.s9.local_symmetric_card15_step(value) for value in zeros]
    canonical = cfg["request_contract"]["canonical_matrix_columns"]
    replacement = cfg["request_contract"]["replacement_matrix_columns"]
    passed = bool(
        all(len(value) == 10 for value in zeros)
        and all(step > 0 for step in steps)
        and _matrix_digest(canonical) == cfg["request_contract"]["canonical_matrix_digest"]
        and _matrix_digest(replacement) == cfg["request_contract"]["replacement_matrix_digest"]
    )
    return {
        "algorithm": "dynamic_exact_target_plus_exact_stored_center_action",
        "canonical_matrix_digest": _matrix_digest(canonical),
        "replacement_matrix_digest": _matrix_digest(replacement),
        "card15_zero_widths": [len(value) for value in zeros],
        "positive_local_step_count": sum(step > 0 for step in steps),
        "physical_issue_time_centers_available_offline": False,
        "physical_margin_claimed_offline": False,
        "physical_issue_and_cancel_margin_gate": "mandatory_per_real_row",
        "passed": passed,
    }


def _package_fingerprint() -> dict[str, Any]:
    root = _project_root()
    manifest = _read_json(root / "PACKAGE_MANIFEST.json")
    files = list(map(str, manifest["file_inventory"]))
    hashes = {name: _sha256(root / name) for name in files}
    required = {
        "configs/stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification_370ms.json",
        "docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8_PARTITIONED_BROAD_RESPONSE_IDENTIFICATION_DESIGN.md",
        "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8_independent_forensics.py",
        "scripts/stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification.py",
        "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification.py",
        "tsc_rzip_rllib/control/action_conditioned_history_response_model.py",
    }
    if not required.issubset(hashes):
        raise ValueError(f"R8 package import closure is incomplete: {sorted(required.difference(hashes))}")
    return {"declared_file_count": len(files), "hashes": hashes, "digest": _digest(hashes)}


def _prepare_dirs(paths: Paths) -> None:
    for path in (paths.run_dir, paths.stage_dir, paths.variants, paths.specs, paths.source_reference, paths.raw, paths.analysis, paths.model):
        path.mkdir(parents=True, exist_ok=True)
    for phase in PHASES:
        paths.phase_raw(phase).mkdir(parents=True, exist_ok=True)


def prepare_offline(ctx: Context) -> dict[str, Any]:
    if ctx.paths.stage_dir.exists() or ctx.paths.state.exists() or ctx.paths.manifest.exists():
        raise ValueError("R8 offline requires a fresh run identity")
    d1 = _authenticate_d1r11(ctx)
    sources = {
        name: r7_source._authenticate_source(ctx.source_response_runs[name], ctx.cfg["source_response_contracts"][name])
        for name in ("r2", "r4", "r6")
    }
    snapshots = _snapshot_audit(d1["context_table"])
    if not snapshots["passed"]:
        raise ValueError("R8 source snapshot authentication failed")
    specs = build_specs(ctx.cfg, d1["d1r11_baselines"], d1["s21_baselines"])
    static = _static_card15_audit(ctx.cfg)
    if not static["passed"]:
        raise ValueError("R8 static Card15 algorithm/configuration gate failed")
    package = _package_fingerprint()
    _prepare_dirs(ctx.paths)
    _write_json(ctx.paths.specs / "all_specs.json", specs)
    for phase in PHASES:
        _write_json(ctx.paths.specs / f"{phase}_specs.json", [row for row in specs if row["partition"] == phase])
    _write_json(ctx.paths.source_reference / "d1r11_authentication.json", {
        "files": d1["files"],
        "state": d1["state"],
        "training_inventory": d1["training_inventory"],
        "s21_authentication": d1["s21_authentication"],
        "training_prefix_equivalence": d1["training_prefix_equivalence"],
    })
    _write_json(ctx.paths.source_reference / "snapshot_audit.json", snapshots)
    _write_json(ctx.paths.source_reference / "static_card15_audit.json", static)
    _write_json(ctx.paths.source_reference / "source_response_inventories.json", {
        name: source["inventory"] for name, source in sources.items()
    })
    _write_json(ctx.paths.source_reference / "s21_baseline_index.json", [
        {
            "pair_id": key[0], "history_member": key[1],
            "experiment_id": row["result"]["experiment_id"],
            "path": str(row["path"]), "sha256": row["sha256"],
        }
        for key, row in sorted(d1["s21_baselines"].items())
    ])
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": ctx.cfg["package_revision"],
        "config_path": str(ctx.config_path),
        "config_sha256": _sha256(ctx.config_path),
        "design_document_sha256": ctx.cfg["design_document_sha256"],
        "source_d1r11_run": str(ctx.source_d1r11_run),
        "source_s21_run": str(ctx.d1r11_ctx.source_s21_ctx.paths.run_dir),
        "source_response_runs": {name: str(path) for name, path in ctx.source_response_runs.items()},
        "spec_count": len(specs),
        "spec_digest": _digest(specs),
        "package_fingerprint": package,
        "snapshot_pass_count": snapshots["pass_count"],
        "formal_timing_unchanged": True,
        "formal_tracking_diagnostic_only": True,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "bc_dagger_or_rl_allowed": False,
    }
    state = {
        "schema_version": 1,
        "stage": STAGE,
        "phase_status": "offline_ready",
        "finished": False,
        "primary_pass": False,
        "real_tsc_executed": False,
        "new_raw_count": 0,
        "heldout_outcomes_opened": False,
        "training_model_sha256": "",
        "calibrated_tube_sha256": "",
        "spec_digest": manifest["spec_digest"],
        "package_digest": package["digest"],
        "verdict": {},
    }
    _write_json(ctx.paths.manifest, manifest)
    _write_json(ctx.paths.state, state)
    output = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "zero_tsc_source_and_full_spec_gate",
        "source_d1r11_authenticated": True,
        "source_r2_r4_r6_authenticated": True,
        "source_s21_baseline_count": 40,
        "source_snapshot_pass_count": snapshots["pass_count"],
        "prospective_spec_count": len(specs),
        "training_spec_count": 624,
        "calibration_spec_count": 312,
        "holdout_spec_count": 312,
        "static_card15_algorithm_configuration_passed": static["passed"],
        "physical_margin_claimed_offline": False,
        "new_raw_count": 0,
        "real_tsc_executed": False,
        "passed": True,
    }
    _write_json(ctx.paths.analysis / "offline_preflight.json", output)
    return output


def _saved_specs(ctx: Context) -> list[dict[str, Any]]:
    specs = _read_json(ctx.paths.specs / "all_specs.json")
    manifest = _read_json(ctx.paths.manifest)
    if (
        len(specs) != 1248
        or _digest(specs) != str(manifest["spec_digest"])
        or manifest.get("stage") != STAGE
        or manifest.get("campaign_identity") != CAMPAIGN_IDENTITY
        or manifest.get("controller_revision") != CONTROLLER_REVISION
        or _sha256(ctx.config_path) != str(manifest["config_sha256"])
    ):
        raise ValueError("R8 saved identity or spec digest changed")
    return specs


def _phase_specs(ctx: Context, phase: str) -> list[dict[str, Any]]:
    if phase not in PHASES:
        raise ValueError(f"invalid R8 phase: {phase}")
    specs = [row for row in _saved_specs(ctx) if str(row["partition"]) == phase]
    expected = {"training": 624, "calibration": 312, "holdout": 312}[phase]
    if len(specs) != expected:
        raise ValueError("R8 saved phase coverage changed")
    return specs


def _set_state(ctx: Context, **updates: Any) -> dict[str, Any]:
    state = _read_json(ctx.paths.state)
    state.update(updates)
    _write_json(ctx.paths.state, state)
    return state


def _require_phase(ctx: Context, expected: str) -> dict[str, Any]:
    state = _read_json(ctx.paths.state)
    if state.get("phase_status") != expected or bool(state.get("finished")):
        raise ValueError(
            f"R8 phase guard expected {expected!r}, got {state.get('phase_status')!r}"
        )
    manifest = _read_json(ctx.paths.manifest)
    if (
        state.get("spec_digest") != manifest.get("spec_digest")
        or state.get("package_digest")
        != (manifest.get("package_fingerprint") or {}).get("digest")
    ):
        raise ValueError("R8 resume identity changed")
    return state


def _kernel_contract(cfg: Mapping[str, Any], kernel: str) -> dict[str, Any]:
    base = copy.deepcopy(dict(cfg["controller_contract"]))
    request = cfg["request_contract"]
    matrix_key = "replacement_matrix_columns" if kernel == "r6" else "canonical_matrix_columns"
    digest_key = "replacement_matrix_digest" if kernel == "r6" else "canonical_matrix_digest"
    base.update(
        {
            "requested_coordinate_matrix_columns": copy.deepcopy(request[matrix_key]),
            "requested_matrix_float64_le_c_sha256": str(request[digest_key]),
            "direction_names": list(r4.DIRECTIONS),
            "issue_task_steps": [14, 18, 22],
            "issue_task_step": 10,
            "cancel_task_step": 11,
            "zero_after_cancel_first_task_step": 12,
            "require_fresh_baseline_reproduction": True,
            "require_exact_r4_baseline_issue_state_reproduction": True,
        }
    )
    return base


def _kernel_spec(spec: Mapping[str, Any]) -> dict[str, Any]:
    output = copy.deepcopy(dict(spec))
    for key in list(output):
        if key.startswith("d1r14r8_") or key.startswith("source_s21_"):
            output.pop(key)
    role = str(spec["d1r14r8_role"])
    kernel = str(spec["d1r14r8_execution_kernel"])
    kernel_role = "baseline" if role == "baseline" else "signed_probe"
    direction = int(spec["d1r14r8_direction_index"])
    sign = int(spec["d1r14r8_sign"])
    issue = int(spec["d1r14r8_issue_task_step"])
    cancel = int(spec["d1r14r8_cancel_task_step"])
    zero_after = int(spec["d1r14r8_zero_after_task_step"])
    requested = copy.deepcopy(spec["d1r14r8_requested_coordinate"])
    digest = str(spec["d1r14r8_requested_matrix_digest"])
    source_id = str(spec["source_d1r11_baseline_experiment_id"])
    output["source_d1r13_experiment_id"] = str(spec["source_s21_baseline_experiment_id"])
    output["source_d1r11_experiment_id"] = source_id
    if kernel == "r2":
        if role != "canonical" or issue != 10:
            raise ValueError("R8 R2 kernel assignment changed")
        output.update(
            {
                "d1r14r2_role": kernel_role,
                "d1r14r2_direction_index": direction,
                "d1r14r2_direction_name": r4.DIRECTIONS[direction],
                "d1r14r2_sign": sign,
                "d1r14r2_requested_coordinate": requested,
                "d1r14r2_requested_matrix_digest": digest,
                "d1r14r2_issue_task_step": issue,
                "d1r14r2_cancel_task_step": cancel,
                "d1r14r2_zero_after_task_step": zero_after,
            }
        )
    elif kernel == "r4":
        if role not in {"baseline", "canonical"} or (role == "canonical" and issue not in (14, 18, 22)):
            raise ValueError("R8 R4 kernel assignment changed")
        output.update(
            {
                "d1r14r4_role": kernel_role,
                "d1r14r4_direction_index": direction,
                "d1r14r4_direction_name": "" if direction < 0 else r4.DIRECTIONS[direction],
                "d1r14r4_sign": sign,
                "d1r14r4_requested_coordinate": requested,
                "d1r14r4_requested_matrix_digest": digest,
                "d1r14r4_issue_task_step": issue,
                "d1r14r4_cancel_task_step": cancel,
                "d1r14r4_zero_after_task_step": zero_after,
            }
        )
    elif kernel == "r6":
        if role != "replacement" or issue not in (14, 18, 22) or direction != 0:
            raise ValueError("R8 R6 kernel assignment changed")
        output.update(
            {
                "d1r14r6_role": kernel_role,
                "d1r14r6_direction_index": direction,
                "d1r14r6_direction_name": r4.DIRECTIONS[direction],
                "d1r14r6_sign": sign,
                "d1r14r6_requested_coordinate": requested,
                "d1r14r6_requested_matrix_digest": digest,
                "d1r14r6_issue_task_step": issue,
                "d1r14r6_cancel_task_step": cancel,
                "d1r14r6_zero_after_task_step": zero_after,
            }
        )
    else:
        raise ValueError("R8 unknown execution kernel")
    return output


def _payload(ctx: Context, spec: Mapping[str, Any]) -> dict[str, Any]:
    proxy = SimpleNamespace(
        base_ctx=ctx.d1r11_ctx.base_ctx.base_ctx,
        paths=ctx.paths,
        cfg=ctx.d1r11_ctx.base_ctx.cfg,
    )
    payload = d1r11.s21._payload(proxy, spec)
    experiment_id = str(spec["experiment_id"])
    payload.update(
        {
            "variant_id": f"stage4_2r3c3t13s24d1r14r8_{experiment_id}",
            "stage4_2r3c3t13s24d1r14r8_restart_snapshot_dir": str(
                spec["restart_snapshot_dir"]
            ),
            "stage4_2r3c3t13s24d1r14r8_snapshot_manifest_digest": str(
                spec["restart_snapshot_manifest_digest"]
            ),
            "stage4_2r3c3t13s24d1r14r8_issue_task_step": int(
                spec["d1r14r8_issue_task_step"]
            ),
            "stage4_2r3c3t13s24d1r14r8_cancel_task_step": int(
                spec["d1r14r8_cancel_task_step"]
            ),
            "stage4_2r3c3t13s24d1r14r8_pair_history_partition_label_available_to_controller": False,
        }
    )
    _write_json(ctx.paths.variants / f"payload_{experiment_id}.json", payload)
    return payload


R8_FORBIDDEN_TRACE_KEYS = tuple(
    dict.fromkeys(
        r4.FORBIDDEN_TRACE_KEYS
        + (
            "r3c3t13s24d1r14r8_future_r17_executed",
            "r3c3t13s24d1r14r8_pair_or_history_label_used",
            "r3c3t13s24d1r14r8_partition_label_used",
            "r3c3t13s24d1r14r8_source_result_used",
        )
    )
)


class LocalWorker:
    """One delegated, already-audited controller kernel and fresh TSC process."""

    def __init__(
        self,
        payload: dict[str, Any],
        library: dict[str, Any],
        bundle: dict[str, Any],
        worker_id: str,
        selector: dict[str, Any],
        lattice_cfg: dict[str, Any],
        calibration_cfg: dict[str, Any],
        dynamic_cfg: dict[str, Any],
        schedule_cfg: dict[str, Any],
        controller_cfg: dict[str, Any],
        kernel: str,
    ):
        cls = {"r2": r2.LocalWorker, "r4": r4.LocalWorker, "r6": r6.LocalWorker}.get(kernel)
        if cls is None:
            raise ValueError("R8 invalid worker kernel")
        self.kernel = kernel
        self.worker = cls(
            payload,
            library,
            bundle,
            worker_id,
            selector,
            lattice_cfg,
            calibration_cfg,
            dynamic_cfg,
            schedule_cfg,
            controller_cfg,
        )

    def close(self) -> None:
        self.worker.close()

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        kernel_spec = _kernel_spec(spec)
        result = self.worker.evaluate(kernel_spec)
        for row in result.get("controller_trace") or []:
            row.update(
                {
                    "r3c3t13s24d1r14r8_controller_revision": CONTROLLER_REVISION,
                    "r3c3t13s24d1r14r8_execution_kernel": self.kernel,
                    "r3c3t13s24d1r14r8_future_r17_executed": False,
                    "r3c3t13s24d1r14r8_pair_or_history_label_used": False,
                    "r3c3t13s24d1r14r8_partition_label_used": False,
                    "r3c3t13s24d1r14r8_source_result_used": False,
                }
            )
        result.update(
            {
                "schema_version": SCHEMA_VERSION,
                "stage": STAGE,
                "campaign_identity": CAMPAIGN_IDENTITY,
                "controller_revision": CONTROLLER_REVISION,
                "execution_kernel_stage": {"r2": r2.STAGE, "r4": r4.STAGE, "r6": r6.STAGE}[self.kernel],
                "execution_kernel_controller_revision": {
                    "r2": r2.CONTROLLER_REVISION,
                    "r4": r4.CONTROLLER_REVISION,
                    "r6": r6.CONTROLLER_REVISION,
                }[self.kernel],
                "experiment_id": str(spec["experiment_id"]),
                "spec": copy.deepcopy(spec),
            }
        )
        summary = result.setdefault("hidden_history_control_summary", {})
        summary.update(
            {
                "fresh_controller_actor": True,
                "fresh_tsc_process": True,
                "identification_only": True,
                "probe_trajectory_allowed_in_expert_dataset": False,
                "future_action_replay_used": False,
                "future_measurement_used": False,
                "source_action_used": False,
                "source_coil_current_used": False,
                "source_wire_current_used": False,
                "current_run_future_used": False,
                "pair_or_history_label_used": False,
                "partition_label_used": False,
                "source_result_used": False,
            }
        )
        return d1r11.s21.s16.s9.t11.t1._json_safe(result)


_RAY_ACTOR = None


def _ray_actor_class():
    global _RAY_ACTOR
    if _RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class Stage42R8Actor:
            def __init__(self, *args):
                self.worker = LocalWorker(*args)

            def evaluate(self, spec):
                return self.worker.evaluate(spec)

            def close(self):
                self.worker.close()
                return True

        _RAY_ACTOR = Stage42R8Actor
    return _RAY_ACTOR


def _result_complete(path: Path, spec: Mapping[str, Any], *, require_success: bool = True) -> bool:
    if not path.is_file():
        return False
    try:
        result = _read_gz(path)
        horizon = int(spec["horizon_steps"])
        return bool(
            result.get("completed")
            and (result.get("success") or not require_success)
            and result.get("stage") == STAGE
            and result.get("campaign_identity") == CAMPAIGN_IDENTITY
            and result.get("controller_revision") == CONTROLLER_REVISION
            and result.get("experiment_id") == spec["experiment_id"]
            and result.get("spec") == dict(spec)
            and (
                not require_success
                or (
                    len(result.get("trajectory") or []) == horizon + 1
                    and len(result.get("controller_trace") or []) == horizon
                )
            )
        )
    except Exception:
        return False


def evaluate_specs(
    ctx: Context,
    specs: Sequence[dict[str, Any]],
    *,
    phase: str,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    raw_dir = ctx.paths.phase_raw(phase)
    raw_dir.mkdir(parents=True, exist_ok=True)
    pending = [
        spec
        for spec in specs
        if not (resume and _result_complete(raw_dir / f"{spec['experiment_id']}.json.gz", spec))
    ]
    payloads = {str(spec["experiment_id"]): _payload(ctx, spec) for spec in specs}
    library, bundle, selector = d1r11._library_bundle_selector(ctx.d1r11_ctx)
    lattice = ctx.d1r11_ctx.base_ctx.base_ctx.cfg["lattice_probe"]
    calibration = ctx.d1r11_ctx.base_ctx.base_ctx.cfg["active_calibration"]
    dynamic = ctx.d1r11_ctx.base_ctx.cfg["causal_model"]
    schedule = ctx.d1r11_ctx.cfg["schedule_contract"]

    def worker_args(spec: Mapping[str, Any], index: int) -> tuple[Any, ...]:
        kernel = str(spec["d1r14r8_execution_kernel"])
        return (
            payloads[str(spec["experiment_id"])], library, bundle,
            f"stage42r8_{phase}_{index:04d}", selector, lattice, calibration,
            dynamic, schedule, _kernel_contract(ctx.cfg, kernel), kernel,
        )

    if backend == "serial":
        for index, spec in enumerate(pending):
            worker = LocalWorker(*worker_args(spec, index))
            try:
                result = worker.evaluate(spec)
            finally:
                worker.close()
            _write_gz(raw_dir / f"{spec['experiment_id']}.json.gz", result)
            print(f"[R8 {phase}] {index + 1}/{len(pending)}", flush=True)
    elif backend == "ray" and pending:
        import ray

        plan = d1r11.s21.s16.ensure_ray_worker_plan(
            ray,
            requested_workers=int(ctx.cfg["parallel"]["n_workers"]),
            pending_tasks=len(pending),
            ray_tmpdir=os.environ.get("RAY_TMPDIR") or ctx.cfg["storage"]["ray_tmpdir"],
            log_prefix=f"[R8 {phase}]",
        )
        Actor = _ray_actor_class()
        completed = 0
        for batch_start in range(0, len(pending), plan.actor_count):
            batch = pending[batch_start : batch_start + plan.actor_count]
            actors, refs = [], {}
            for offset, spec in enumerate(batch):
                actor = Actor.remote(*worker_args(spec, batch_start + offset))
                actors.append(actor)
                refs[actor.evaluate.remote(spec)] = spec
            try:
                while refs:
                    ready, _ = ray.wait(list(refs), num_returns=1, timeout=30.0)
                    if not ready:
                        print(f"[R8 {phase}] waiting {completed}/{len(pending)}", flush=True)
                        continue
                    for ref in ready:
                        spec = refs.pop(ref)
                        try:
                            result = ray.get(ref)
                        except Exception as exc:
                            result = {
                                "schema_version": 1,
                                "stage": STAGE,
                                "campaign_identity": CAMPAIGN_IDENTITY,
                                "controller_revision": CONTROLLER_REVISION,
                                "experiment_id": str(spec["experiment_id"]),
                                "spec": copy.deepcopy(spec),
                                "success": False,
                                "completed": True,
                                "failure_reason": repr(exc),
                                "execution_failure_class": "ray_actor_runtime_error",
                                "traceback": traceback.format_exc(),
                                "trajectory": [],
                                "controller_trace": [],
                            }
                        _write_gz(raw_dir / f"{spec['experiment_id']}.json.gz", result)
                        completed += 1
                        print(f"[R8 {phase}] {completed}/{len(pending)}", flush=True)
            finally:
                close_refs = [actor.close.remote() for actor in actors]
                if close_refs:
                    ray.get(close_refs, timeout=float(ctx.cfg["storage"]["actor_close_timeout_s"]))
                for actor in actors:
                    ray.kill(actor, no_restart=True)
    elif backend not in {"serial", "ray"}:
        raise ValueError(f"unsupported R8 backend: {backend}")
    successful = sum(
        _result_complete(raw_dir / f"{spec['experiment_id']}.json.gz", spec)
        for spec in specs
    )
    return {
        "phase": phase,
        "expected": len(specs),
        "pending_at_start": len(pending),
        "successful": successful,
        "passed": successful == len(specs),
    }


def _source_baseline_results(ctx: Context) -> dict[str, dict[str, Any]]:
    rows = _read_json(ctx.paths.source_reference / "s21_baseline_index.json")
    output = {}
    for row in rows:
        path = Path(str(row["path"])).expanduser().resolve()
        if _sha256(path) != str(row["sha256"]):
            raise ValueError("R8 S21 baseline raw changed after offline freeze")
        result = _read_gz(path)
        if result.get("experiment_id") != row["experiment_id"]:
            raise ValueError("R8 S21 baseline identity changed")
        output[str(row["experiment_id"])] = result
    if len(output) != 40:
        raise ValueError("R8 frozen S21 baseline index changed")
    return output


def _event_detail(trace: Sequence[Mapping[str, Any]], spec: Mapping[str, Any], step: int) -> dict[str, Any]:
    kernel = str(spec["d1r14r8_execution_kernel"])
    return copy.deepcopy(
        (trace[step].get(f"r3c3t13s24d1r14{kernel}_event_detail") or {})
    )


def _formal_diagnostics(ctx: Context, specs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    evaluators, _ = d1r11._formal_callback(ctx.d1r11_ctx, specs)
    passed = 0
    for spec in specs:
        result = _read_gz(ctx.paths.phase_raw(str(spec["partition"])) / f"{spec['experiment_id']}.json.gz")
        trajectory = result.get("trajectory") or []
        values = np.asarray([[row["R"], row["Z"], row["Ip"]] for row in trajectory], dtype=float)
        if len(values) == int(spec["horizon_steps"]) + 1:
            passed += bool(evaluators[str(spec["experiment_id"])].evaluate(values)["formal_contract_pass"])
    return {"evaluated": len(specs), "formal_contract_pass_count_diagnostic_only": passed}


def audit_raw_phase(ctx: Context, phase: str) -> dict[str, Any]:
    specs = _phase_specs(ctx, phase)
    raw_dir = ctx.paths.phase_raw(phase)
    sources = _source_baseline_results(ctx)
    controller_cfg = ctx.cfg["controller_contract"]
    rows = []
    for spec in specs:
        experiment_id = str(spec["experiment_id"])
        path = raw_dir / f"{experiment_id}.json.gz"
        if not _result_complete(path, spec, require_success=False):
            rows.append({"experiment_id": experiment_id, "runtime_success": False, "passed": False, "failure_class": "runtime_or_raw_error"})
            continue
        result = _read_gz(path)
        trajectory = result.get("trajectory") or []
        trace = result.get("controller_trace") or []
        source = sources[str(spec["source_s21_baseline_experiment_id"])]
        horizon = int(spec["horizon_steps"])
        full = len(trajectory) == horizon + 1 and len(trace) == horizon
        prefix_state = bool(
            len(trajectory) >= PREFIX_END + 1
            and all(
                r4._semantic_state(current) == r4._semantic_state(reference)
                for current, reference in zip(
                    trajectory[: PREFIX_END + 1], source["trajectory"][: PREFIX_END + 1]
                )
            )
        )
        prefix_trace = bool(
            len(trace) >= PREFIX_END
            and all(
                r4._source_trace_projection(reference, current)
                for current, reference in zip(
                    trace[:PREFIX_END], source["controller_trace"][:PREFIX_END]
                )
            )
        )
        calibration = r4._calibration_exact(trace)
        currents = np.asarray([row.get("currents_a_tsc", []) for row in trajectory], dtype=float)
        wires = [np.asarray(row.get("wire_currents_a", []), dtype=float) for row in trajectory]
        finite = bool(
            full
            and currents.shape == (horizon + 1, N_COILS)
            and np.all(np.isfinite(currents))
            and all(value.size and np.all(np.isfinite(value)) for value in wires)
            and all(math.isfinite(float(row[key])) for row in trajectory for key in ("R", "Z", "Ip"))
            and not any(bool(row.get("abnormal")) for row in trajectory)
        )
        forbidden = sum(any(bool(row.get(key)) for key in R8_FORBIDDEN_TRACE_KEYS) for row in trace)
        payload = _read_json(ctx.paths.variants / f"payload_{experiment_id}.json")
        minimum, maximum = d1r11.s21.s13._current_limits_tsc(payload)
        center, half = 0.5 * (minimum + maximum), 0.5 * (maximum - minimum)
        utilization = float(np.max(np.abs((currents - center) / half))) if currents.shape == (horizon + 1, N_COILS) else math.inf
        role = str(spec["d1r14r8_role"])
        issue = int(spec["d1r14r8_issue_task_step"])
        cancel = int(spec["d1r14r8_cancel_task_step"])
        zero_after = int(spec["d1r14r8_zero_after_task_step"])
        preissue_zero = after_zero = issue_exact = cancel_exact = True
        if full:
            if role == "baseline":
                post_actions = np.asarray([row.get("action_norm_tsc", []) for row in trace[PREFIX_END:]], dtype=float)
                post_delta = np.diff(currents[PREFIX_END:], axis=0)
                preissue_zero = bool(
                    post_actions.shape == (horizon - PREFIX_END, N_COILS)
                    and np.array_equal(post_actions, np.zeros_like(post_actions))
                    and post_delta.shape == (horizon - PREFIX_END, N_COILS)
                    and np.array_equal(post_delta, np.zeros_like(post_delta))
                )
            else:
                before_actions = np.asarray([row.get("action_norm_tsc", []) for row in trace[PREFIX_END:issue]], dtype=float)
                before_delta = np.diff(currents[PREFIX_END : issue + 1], axis=0)
                after_actions = np.asarray([row.get("action_norm_tsc", []) for row in trace[zero_after:]], dtype=float)
                after_delta = np.diff(currents[zero_after:], axis=0)
                preissue_zero = bool(
                    before_actions.shape == (issue - PREFIX_END, N_COILS)
                    and np.array_equal(before_actions, np.zeros_like(before_actions))
                    and before_delta.shape == (issue - PREFIX_END, N_COILS)
                    and np.array_equal(before_delta, np.zeros_like(before_delta))
                )
                after_zero = bool(
                    after_actions.shape == (horizon - zero_after, N_COILS)
                    and np.array_equal(after_actions, np.zeros_like(after_actions))
                    and after_delta.shape == (horizon - zero_after, N_COILS)
                    and np.array_equal(after_delta, np.zeros_like(after_delta))
                )
                issue_event = _event_detail(trace, spec, issue)
                cancel_event = _event_detail(trace, spec, cancel)
                expected_coordinate = list(map(float, spec["d1r14r8_requested_coordinate"]))
                issue_exact = bool(
                    issue_event.get("event") == "sequential_issue"
                    and int(issue_event.get("task_step", -1)) == issue
                    and int(issue_event.get("slot", -1)) == int(spec["d1r14r8_direction_index"])
                    and list(map(float, issue_event.get("requested_coordinate", []))) == expected_coordinate
                    and issue_event.get("passed") is True
                    and all(bool(value) for value in (issue_event.get("criteria") or {}).values())
                    and float(issue_event.get("incremental_normalized_action_linf", math.inf)) <= float(controller_cfg["maximum_incremental_normalized_action_linf"]) + 1e-12
                )
                cancel_exact = bool(
                    cancel_event.get("event") == "sequential_cancel"
                    and int(cancel_event.get("task_step", -1)) == cancel
                    and int(cancel_event.get("slot", -1)) == int(spec["d1r14r8_direction_index"])
                    and cancel_event.get("stored_center_card15_fields") == issue_event.get("center_card15_fields")
                    and cancel_event.get("passed") is True
                    and all(bool(value) for value in (cancel_event.get("criteria") or {}).values())
                    and float(cancel_event.get("incremental_normalized_action_linf", math.inf)) <= float(controller_cfg["maximum_online_cancel_incremental_linf"]) + 1e-12
                )
        else:
            preissue_zero = after_zero = issue_exact = cancel_exact = False
        passed = bool(
            result.get("success")
            and full and prefix_state and prefix_trace and calibration and finite
            and forbidden == 0
            and utilization <= float(controller_cfg["maximum_current_utilization"]) + 1e-12
            and preissue_zero and after_zero and issue_exact and cancel_exact
        )
        rows.append(
            {
                "experiment_id": experiment_id,
                "pair_id": spec["pair_id"],
                "history_member": spec["history_member"],
                "role": role,
                "execution_kernel": spec["d1r14r8_execution_kernel"],
                "issue_task_step": issue,
                "runtime_success": bool(result.get("success")),
                "execution_failure_class": str(result.get("execution_failure_class") or ""),
                "full_horizon": full,
                "source_prefix_state_exact": prefix_state,
                "source_prefix_trace_exact": prefix_trace,
                "calibration_exact": calibration,
                "preissue_or_baseline_zero_exact": preissue_zero,
                "issue_exact": issue_exact,
                "cancel_exact": cancel_exact,
                "postcancel_zero_exact": after_zero,
                "finite": finite,
                "forbidden_trace_count": forbidden,
                "maximum_current_utilization": utilization,
                "failure_reason": str(result.get("failure_reason") or ""),
                "passed": passed,
            }
        )
    inventory = _inventory(raw_dir)
    expected = {"training": 624, "calibration": 312, "holdout": 312}[phase]
    formal = _formal_diagnostics(ctx, specs) if len(rows) == expected and all(row["runtime_success"] for row in rows) else {"evaluated": 0, "formal_contract_pass_count_diagnostic_only": 0}
    report = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": phase,
        "expected_raw_count": expected,
        "raw_inventory": inventory,
        "runtime_success_count": sum(row["runtime_success"] for row in rows),
        "full_horizon_count": sum(row["full_horizon"] for row in rows),
        "source_prefix_state_exact_count": sum(row["source_prefix_state_exact"] for row in rows),
        "source_prefix_trace_exact_count": sum(row["source_prefix_trace_exact"] for row in rows),
        "calibration_exact_count": sum(row["calibration_exact"] for row in rows),
        "action_semantics_pass_count": sum(
            row["preissue_or_baseline_zero_exact"] and row["issue_exact"] and row["cancel_exact"] and row["postcancel_zero_exact"]
            for row in rows
        ),
        "finite_count": sum(row["finite"] for row in rows),
        "forbidden_trace_count": sum(int(row["forbidden_trace_count"]) for row in rows),
        "maximum_current_utilization": max((float(row["maximum_current_utilization"]) for row in rows), default=math.inf),
        "passed_count": sum(row["passed"] for row in rows),
        "formal_tracking_diagnostic_only": formal,
        "rows": rows,
    }
    report["passed"] = bool(
        inventory["count"] == expected
        and len(rows) == expected
        and report["passed_count"] == expected
    )
    report["route"] = ctx.cfg["routes"][
        f"{phase}_execution_fail" if not report["passed"] else (
            "pass" if phase == "holdout" else f"{phase}_model_fail"
        )
    ]
    _write_json(ctx.paths.analysis / f"{phase}_raw_primary.json", report)
    return report


def run_phase(ctx: Context, phase: str, *, backend: str, resume: bool) -> dict[str, Any]:
    expected_state = {
        "training": "offline_ready",
        "calibration": "training_model_frozen",
        "holdout": "calibrated_tube_frozen",
    }[phase]
    _require_phase(ctx, expected_state)
    for future in PHASES[PHASES.index(phase) + 1 :]:
        if any(ctx.paths.phase_raw(future).glob("*.json.gz")):
            raise ValueError(f"R8 {future} raw exists before {phase} completion")
    specs = _phase_specs(ctx, phase)
    execution = evaluate_specs(ctx, specs, phase=phase, backend=backend, resume=resume)
    primary = audit_raw_phase(ctx, phase)
    total = sum(_inventory(ctx.paths.phase_raw(name))["count"] for name in PHASES)
    if not execution["passed"] or not primary["passed"]:
        route = ctx.cfg["routes"][f"{phase}_execution_fail"]
        _set_state(
            ctx,
            phase_status=f"{phase}_execution_failed",
            finished=True,
            primary_pass=False,
            real_tsc_executed=total > 0,
            new_raw_count=total,
            stop_reason=f"{phase}_runtime_restart_action_or_raw_gate_failed",
            verdict={"route": route, "passed": False},
        )
    else:
        _set_state(
            ctx,
            phase_status=f"{phase}_raw_primary_passed",
            real_tsc_executed=True,
            new_raw_count=total,
            heldout_outcomes_opened=phase == "holdout",
            **{f"{phase}_raw_inventory_digest": primary["raw_inventory"]["digest"]},
        )
    return {"execution": execution, "primary_raw_audit": {key: value for key, value in primary.items() if key != "rows"}}


def _phase_model_cfg(cfg: Mapping[str, Any], phase: str) -> dict[str, Any]:
    output = copy.deepcopy(dict(cfg))
    gates = output["gates"]
    if phase == "training":
        responses, branches = 912, 192
    elif phase in {"calibration", "holdout"}:
        responses, branches = 304, 64
    else:
        raise ValueError("R8 invalid model phase")
    gates.update(
        {
            "required_response_pass_count": responses,
            "required_signal_pass_count": responses,
            "required_canonical_branch_count": branches,
            "required_operational_branch_count": branches,
        }
    )
    return output


def _phase_results(ctx: Context, phase: str) -> dict[str, dict[str, Any]]:
    output = {}
    for spec in _phase_specs(ctx, phase):
        path = ctx.paths.phase_raw(phase) / f"{spec['experiment_id']}.json.gz"
        if not _result_complete(path, spec):
            raise ValueError(f"R8 {phase} raw is incomplete before model evaluation")
        output[str(spec["experiment_id"])] = _read_gz(path)
    return output


def build_new_items(ctx: Context, phase: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    specs = _phase_specs(ctx, phase)
    results = _phase_results(ctx, phase)
    scales = np.asarray(ctx.cfg["bank_contract"]["response_scales"], dtype=float)
    target_scales = np.asarray(ctx.cfg["bank_contract"]["target_scales"], dtype=float)
    offsets = tuple(map(int, ctx.cfg["bank_contract"]["history_offsets"]))
    grouped: dict[tuple[str, str], dict[tuple[str, int, int, int], Mapping[str, Any]]] = {}
    spec_by_id = {str(spec["experiment_id"]): spec for spec in specs}
    for spec in specs:
        key = (str(spec["pair_id"]), str(spec["history_member"]))
        member = (
            str(spec["d1r14r8_role"]),
            int(spec["d1r14r8_issue_task_step"]),
            int(spec["d1r14r8_direction_index"]),
            int(spec["d1r14r8_sign"]),
        )
        if member in grouped.setdefault(key, {}):
            raise ValueError("R8 duplicate new response member")
        grouped[key][member] = results[str(spec["experiment_id"])]
    items = []
    for context, members in sorted(grouped.items()):
        baseline_result = members[("baseline", -1, -1, 0)]
        baseline_spec = spec_by_id[str(baseline_result["experiment_id"])]
        baseline_visible = r7_source._visible(baseline_result["trajectory"], scales)
        context_id = f"{context[0]}|{context[1]}"
        for issue in ISSUE_STEPS:
            history = baseline_visible[
                [max(0, issue - offset) for offset in offsets]
            ].reshape(-1)
            availability = np.asarray([float(offset <= issue) for offset in offsets])
            target = np.asarray(
                [
                    baseline_spec["target_R_offset_m"],
                    baseline_spec["target_Z_offset_m"],
                    baseline_spec["target_Ip_offset_A"],
                ],
                dtype=float,
            ) / target_scales
            descriptor = np.concatenate(
                (history, availability, target, [(issue - 10.0) / 12.0])
            )
            if len(descriptor) != 142:
                raise ValueError("R8 causal descriptor dimension changed")
            for sign in (-1, 1):
                for direction in range(4):
                    result = members[("canonical", issue, direction, sign)]
                    spec = spec_by_id[str(result["experiment_id"])]
                    member = r7_source._visible(result["trajectory"], scales)[issue + 1 :]
                    baseline = baseline_visible[issue + 1 :]
                    roles = ["canonical"]
                    if issue == 10 or direction != 0:
                        roles.append("operational")
                    items.append(
                        {
                            "response_id": str(spec["experiment_id"]),
                            "source_stage": "R8",
                            "context_id": context_id,
                            "pair_id": context[0],
                            "history_member": context[1],
                            "issue_task_step": issue,
                            "sign": sign,
                            "direction_index": direction,
                            "action_scale": 1.0,
                            "geometry_roles": roles,
                            "descriptor": descriptor.tolist(),
                            "response": (member - baseline).tolist(),
                        }
                    )
                if issue > 10:
                    result = members[("replacement", issue, 0, sign)]
                    spec = spec_by_id[str(result["experiment_id"])]
                    member = r7_source._visible(result["trajectory"], scales)[issue + 1 :]
                    baseline = baseline_visible[issue + 1 :]
                    items.append(
                        {
                            "response_id": str(spec["experiment_id"]),
                            "source_stage": "R8",
                            "context_id": context_id,
                            "pair_id": context[0],
                            "history_member": context[1],
                            "issue_task_step": issue,
                            "sign": sign,
                            "direction_index": 0,
                            "action_scale": 1.5,
                            "geometry_roles": ["operational"],
                            "descriptor": descriptor.tolist(),
                            "response": (member - baseline).tolist(),
                        }
                    )
    items.sort(key=lambda row: str(row["response_id"]))
    expected = {"training": 608, "calibration": 304, "holdout": 304}[phase]
    pairs = sorted({str(row["pair_id"]) for row in items})
    contexts = sorted({str(row["context_id"]) for row in items})
    signature = {
        "phase": phase,
        "response_count": len(items),
        "pair_count": len(pairs),
        "context_count": len(contexts),
        "pairs": pairs,
        "descriptor_dimension": 142,
        "canonical_geometry_item_count": sum("canonical" in row["geometry_roles"] for row in items),
        "operational_geometry_item_count": sum("operational" in row["geometry_roles"] for row in items),
        "bank_digest": response_metrics.canonical_digest(items),
    }
    if (
        len(items) != expected
        or len(pairs) != (8 if phase == "training" else 4)
        or len(contexts) != (16 if phase == "training" else 8)
        or signature["canonical_geometry_item_count"] != (512 if phase == "training" else 256)
        or signature["operational_geometry_item_count"] != (512 if phase == "training" else 256)
    ):
        raise ValueError("R8 new response bank coverage changed")
    return items, signature


def _existing_training_items(ctx: Context) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    sources = {
        name: r7_source._authenticate_source(
            ctx.source_response_runs[name], ctx.cfg["source_response_contracts"][name]
        )
        for name in ("r2", "r4", "r6")
    }
    items, signature = r7r2.build_items(sources, ctx.cfg)
    if set(signature["pairs"]) != set(map(str, ctx.cfg["pair_partitions"]["consumed_training"])):
        raise ValueError("R8 consumed training pair bank changed")
    return items, signature


def _actual_geometry(items: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> dict[str, Any]:
    rows = [
        {
            "response_id": row["response_id"],
            "context_id": row["context_id"],
            "pair_id": row["pair_id"],
            "history_member": row["history_member"],
            "issue_task_step": row["issue_task_step"],
            "sign": row["sign"],
            "direction_index": row["direction_index"],
            "source_stage": row["source_stage"],
            "action_scale": row["action_scale"],
            "geometry_roles": row["geometry_roles"],
            "predicted_response": row["response"],
        }
        for row in items
    ]
    value = response_model.geometry(rows, cfg)
    value["interpretation"] = "actual_response_geometry"
    return value


def _summary_geometry(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "response_count": value["response_count"],
        "signal_pass_count": value["signal_pass_count"],
        "minimum_predicted_peak": value["minimum_predicted_peak"],
        "canonical": {key: row for key, row in value["canonical"].items() if key != "rows"},
        "operational": {key: row for key, row in value["operational"].items() if key != "rows"},
        "passed": value["passed"],
    }


def _independent_file(ctx: Context, name: str) -> dict[str, Any]:
    path = ctx.paths.analysis / f"{name}_independent.json"
    if not path.is_file():
        raise ValueError(f"R8 required independent audit is absent: {name}")
    value = _read_json(path)
    if value.get("stage") != STAGE or value.get("audit_kind") != name or not value.get("passed"):
        raise ValueError(f"R8 independent audit failed or changed: {name}")
    return value


def _deserialize_model(value: Mapping[str, Any]) -> dict[str, Any]:
    candidate = value["candidate"]
    return {
        "candidate": response_model.Candidate(
            int(candidate["pca_rank"]),
            float(candidate["bandwidth_multiplier"]),
            float(candidate["ridge"]),
        ),
        "preprocessor": {
            key: np.asarray(row, dtype=float) for key, row in value["preprocessor"].items()
        },
        "heads": {
            key: {
                "amplitude_mean": float(head["amplitude_mean"]),
                "amplitude_scale": float(head["amplitude_scale"]),
                "lags": [
                    {
                        "lag": int(row["lag"]),
                        "x": np.asarray(row["x"], dtype=float),
                        "bandwidth": float(row["bandwidth"]),
                        "y_mean": np.asarray(row["y_mean"], dtype=float),
                        "alpha": np.asarray(row["alpha"], dtype=float),
                    }
                    for row in head["lags"]
                ],
            }
            for key, head in value["heads"].items()
        },
    }


def _predict_rows(
    model: Mapping[str, Any], items: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> list[dict[str, Any]]:
    return sorted(
        [
            response_model.prediction_row(
                item, response_model.predict_item(model, item, cfg), cfg
            )
            for item in items
        ],
        key=lambda row: str(row["response_id"]),
    )


def run_fit_training(ctx: Context) -> dict[str, Any]:
    _require_phase(ctx, "training_raw_primary_passed")
    raw_independent = _independent_file(ctx, "training_raw")
    primary_raw = _read_json(ctx.paths.analysis / "training_raw_primary.json")
    if raw_independent.get("raw_inventory_digest") != primary_raw["raw_inventory"]["digest"]:
        raise ValueError("R8 training independent raw inventory disagreement")
    if any(ctx.paths.phase_raw("calibration").glob("*.json.gz")) or any(ctx.paths.phase_raw("holdout").glob("*.json.gz")):
        raise ValueError("R8 held-out raw opened before training model hash")
    existing, existing_signature = _existing_training_items(ctx)
    extension, extension_signature = build_new_items(ctx, "training")
    items = sorted(existing + extension, key=lambda row: str(row["response_id"]))
    cfg = _phase_model_cfg(ctx.cfg, "training")
    if len(items) != 912 or len({str(row["pair_id"]) for row in items}) != 12:
        raise ValueError("R8 combined training response bank changed")
    rows, folds = response_model.nested_outer_rows(items, cfg)
    aggregate = response_metrics.aggregate(rows, cfg)
    predicted_geometry = response_model.geometry(rows, cfg)
    actual_geometry = _actual_geometry(items, cfg)
    passed = bool(aggregate["passed"] and predicted_geometry["passed"] and actual_geometry["passed"])
    selected, scores = response_model.select_candidate(items, cfg)
    detailed = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "training_nested_whole_pair_oof",
        "passed": passed,
        "route": ctx.cfg["routes"]["pass" if passed else "training_model_fail"],
        "existing_bank": existing_signature,
        "extension_bank": extension_signature,
        "combined_response_count": len(items),
        "combined_pair_count": len({str(row["pair_id"]) for row in items}),
        "nested_outer_folds": folds,
        "outer_prediction_rows": rows,
        "aggregate": aggregate,
        "predicted_geometry": predicted_geometry,
        "actual_geometry": actual_geometry,
        "selected_candidate": selected.as_dict(),
        "candidate_scores": scores,
        "forbidden_predictor_input_count": 0,
    }
    detailed_path = ctx.paths.analysis / "training_model_primary_detailed.json"
    _write_json(detailed_path, detailed)
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": detailed["phase"],
        "passed": passed,
        "route": detailed["route"],
        "combined_response_count": len(items),
        "combined_pair_count": detailed["combined_pair_count"],
        "aggregate": aggregate,
        "predicted_geometry": _summary_geometry(predicted_geometry),
        "actual_geometry": _summary_geometry(actual_geometry),
        "outer_selected_candidates": [
            {"held_pair_id": row["held_pair_id"], "training_pair_count": row["training_pair_count"], "selected_candidate": row["selected_candidate"]}
            for row in folds
        ],
        "selected_candidate": selected.as_dict(),
        "detailed_sha256": _sha256(detailed_path),
    }
    summary_path = ctx.paths.analysis / "training_model_primary_summary.json"
    _write_json(summary_path, summary)
    if not passed:
        _set_state(
            ctx,
            phase_status="training_model_failed",
            finished=True,
            primary_pass=False,
            stop_reason="training_whole_pair_response_model_or_geometry_gate_failed",
            verdict={"route": ctx.cfg["routes"]["training_model_fail"], "passed": False},
        )
        return summary
    fitted = response_model.fit_model(items, selected, cfg)
    artifact = response_model.serializable_model(fitted)
    model_path = ctx.paths.model / "training_response_model.json"
    _write_json(model_path, artifact)
    model_sha = _sha256(model_path)
    summary["training_model_sha256"] = model_sha
    _write_json(summary_path, summary)
    _set_state(
        ctx,
        phase_status="training_model_primary_frozen",
        training_model_sha256=model_sha,
        training_model_primary_summary_sha256=_sha256(summary_path),
    )
    return summary


def authorize_calibration(ctx: Context) -> dict[str, Any]:
    state = _require_phase(ctx, "training_model_primary_frozen")
    independent = _independent_file(ctx, "training_model")
    model_path = ctx.paths.model / "training_response_model.json"
    summary_path = ctx.paths.analysis / "training_model_primary_summary.json"
    if (
        _sha256(model_path) != state["training_model_sha256"]
        or _sha256(summary_path) != state["training_model_primary_summary_sha256"]
        or independent.get("training_model_sha256") != state["training_model_sha256"]
        or independent.get("primary_summary_sha256") != state["training_model_primary_summary_sha256"]
    ):
        raise ValueError("R8 independent training model/hash disagreement")
    _set_state(ctx, phase_status="training_model_frozen", training_model_independent_sha256=_sha256(ctx.paths.analysis / "training_model_independent.json"))
    return {"stage": STAGE, "phase": "training_model_dual_audit_frozen", "training_model_sha256": state["training_model_sha256"], "passed": True}


def _combined_tube(
    training_component: Sequence[float], calibration_component: Sequence[float], cfg: Mapping[str, Any]
) -> dict[str, Any]:
    scales = np.asarray(cfg["bank_contract"]["response_scales"], dtype=float)
    gates = cfg["gates"]
    component = np.maximum(np.asarray(training_component, dtype=float), np.asarray(calibration_component, dtype=float))
    tube = np.asarray(gates["response_floor_physical"], dtype=float) / scales + float(gates["tube_multiplier"]) * component
    caps = np.asarray(gates["tube_caps_physical"], dtype=float) / scales
    return {
        "componentwise_maximum_absolute_scaled_error": component.tolist(),
        "tube_halfwidth_scaled": tube.tolist(),
        "tube_halfwidth_physical": (tube * scales).tolist(),
        "tube_caps_physical": list(map(float, gates["tube_caps_physical"])),
        "tube_cap_pass": bool(np.all(tube <= caps + 1e-15)),
    }


def run_fit_calibration(ctx: Context) -> dict[str, Any]:
    state = _require_phase(ctx, "calibration_raw_primary_passed")
    raw_independent = _independent_file(ctx, "calibration_raw")
    primary_raw = _read_json(ctx.paths.analysis / "calibration_raw_primary.json")
    if raw_independent.get("raw_inventory_digest") != primary_raw["raw_inventory"]["digest"]:
        raise ValueError("R8 calibration independent raw inventory disagreement")
    if any(ctx.paths.phase_raw("holdout").glob("*.json.gz")):
        raise ValueError("R8 holdout raw opened before calibrated tube hash")
    model_path = ctx.paths.model / "training_response_model.json"
    if _sha256(model_path) != state["training_model_sha256"]:
        raise ValueError("R8 training model changed before calibration")
    model = _deserialize_model(_read_json(model_path))
    items, signature = build_new_items(ctx, "calibration")
    cfg = _phase_model_cfg(ctx.cfg, "calibration")
    rows = _predict_rows(model, items, cfg)
    aggregate = response_metrics.aggregate(rows, cfg)
    predicted_geometry = response_model.geometry(rows, cfg)
    actual_geometry = _actual_geometry(items, cfg)
    training = _read_json(ctx.paths.analysis / "training_model_primary_summary.json")
    tube = _combined_tube(
        training["aggregate"]["componentwise_maximum_absolute_scaled_error"],
        aggregate["componentwise_maximum_absolute_scaled_error"],
        cfg,
    )
    passed = bool(
        aggregate["passed"] and predicted_geometry["passed"] and actual_geometry["passed"] and tube["tube_cap_pass"]
    )
    detailed = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "calibration_fixed_model_predictions",
        "passed": passed,
        "route": ctx.cfg["routes"]["pass" if passed else "calibration_model_fail"],
        "bank": signature,
        "training_model_sha256": state["training_model_sha256"],
        "prediction_rows": rows,
        "aggregate": aggregate,
        "predicted_geometry": predicted_geometry,
        "actual_geometry": actual_geometry,
        "calibrated_tube": tube,
        "forbidden_predictor_input_count": 0,
    }
    detailed_path = ctx.paths.analysis / "calibration_model_primary_detailed.json"
    _write_json(detailed_path, detailed)
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": detailed["phase"],
        "passed": passed,
        "route": detailed["route"],
        "bank": signature,
        "training_model_sha256": state["training_model_sha256"],
        "aggregate": aggregate,
        "predicted_geometry": _summary_geometry(predicted_geometry),
        "actual_geometry": _summary_geometry(actual_geometry),
        "calibrated_tube": tube,
        "detailed_sha256": _sha256(detailed_path),
    }
    summary_path = ctx.paths.analysis / "calibration_model_primary_summary.json"
    _write_json(summary_path, summary)
    if not passed:
        _set_state(
            ctx,
            phase_status="calibration_model_failed",
            finished=True,
            primary_pass=False,
            stop_reason="calibration_response_tube_or_geometry_gate_failed",
            verdict={"route": ctx.cfg["routes"]["calibration_model_fail"], "passed": False},
        )
        return summary
    tube_artifact = {
        "schema_version": 1,
        "stage": STAGE,
        "training_model_sha256": state["training_model_sha256"],
        **tube,
    }
    tube_path = ctx.paths.model / "calibrated_response_tube.json"
    _write_json(tube_path, tube_artifact)
    _set_state(
        ctx,
        phase_status="calibrated_tube_primary_frozen",
        calibrated_tube_sha256=_sha256(tube_path),
        calibration_model_primary_summary_sha256=_sha256(summary_path),
    )
    summary["calibrated_tube_sha256"] = _sha256(tube_path)
    _write_json(summary_path, summary)
    _set_state(ctx, calibration_model_primary_summary_sha256=_sha256(summary_path))
    return summary


def authorize_holdout(ctx: Context) -> dict[str, Any]:
    state = _require_phase(ctx, "calibrated_tube_primary_frozen")
    independent = _independent_file(ctx, "calibration_model")
    model_path = ctx.paths.model / "training_response_model.json"
    tube_path = ctx.paths.model / "calibrated_response_tube.json"
    summary_path = ctx.paths.analysis / "calibration_model_primary_summary.json"
    if (
        _sha256(model_path) != state["training_model_sha256"]
        or _sha256(tube_path) != state["calibrated_tube_sha256"]
        or _sha256(summary_path) != state["calibration_model_primary_summary_sha256"]
        or independent.get("training_model_sha256") != state["training_model_sha256"]
        or independent.get("calibrated_tube_sha256") != state["calibrated_tube_sha256"]
        or independent.get("primary_summary_sha256") != state["calibration_model_primary_summary_sha256"]
    ):
        raise ValueError("R8 independent calibration model/tube disagreement")
    _set_state(ctx, phase_status="calibrated_tube_frozen", calibration_model_independent_sha256=_sha256(ctx.paths.analysis / "calibration_model_independent.json"))
    return {"stage": STAGE, "phase": "calibrated_tube_dual_audit_frozen", "training_model_sha256": state["training_model_sha256"], "calibrated_tube_sha256": state["calibrated_tube_sha256"], "passed": True}


def run_finalize(ctx: Context) -> dict[str, Any]:
    state = _require_phase(ctx, "holdout_raw_primary_passed")
    raw_independent = _independent_file(ctx, "holdout_raw")
    primary_raw = _read_json(ctx.paths.analysis / "holdout_raw_primary.json")
    if raw_independent.get("raw_inventory_digest") != primary_raw["raw_inventory"]["digest"]:
        raise ValueError("R8 holdout independent raw inventory disagreement")
    model_path = ctx.paths.model / "training_response_model.json"
    tube_path = ctx.paths.model / "calibrated_response_tube.json"
    if (
        _sha256(model_path) != state["training_model_sha256"]
        or _sha256(tube_path) != state["calibrated_tube_sha256"]
        or not bool(state["heldout_outcomes_opened"])
    ):
        raise ValueError("R8 frozen model/tube or holdout ordering changed")
    model = _deserialize_model(_read_json(model_path))
    tube = _read_json(tube_path)
    items, signature = build_new_items(ctx, "holdout")
    cfg = _phase_model_cfg(ctx.cfg, "holdout")
    predictions = {
        str(item["response_id"]): response_model.predict_item(model, item, cfg)
        for item in items
    }
    rows = []
    halfwidth = np.asarray(tube["tube_halfwidth_scaled"], dtype=float)
    for item in items:
        predicted = predictions[str(item["response_id"])]
        row = response_model.prediction_row(item, predicted, cfg)
        error = np.abs(predicted - np.asarray(item["response"], dtype=float))
        row["tube_containment"] = bool(np.all(error <= halfwidth[None, :] + 1e-15))
        row["tube_maximum_fraction"] = float(np.max(error / np.maximum(halfwidth[None, :], 1e-300)))
        rows.append(row)
    rows.sort(key=lambda row: str(row["response_id"]))
    aggregate = response_metrics.aggregate(rows, cfg)
    predicted_geometry = response_model.geometry(rows, cfg)
    actual_geometry = _actual_geometry(items, cfg)
    containment = sum(bool(row["tube_containment"]) for row in rows)
    passed = bool(
        aggregate["passed"]
        and predicted_geometry["passed"]
        and actual_geometry["passed"]
        and containment == 304
        and bool(tube["tube_cap_pass"])
    )
    route = ctx.cfg["routes"]["pass" if passed else "holdout_model_fail"]
    detailed = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "fresh_holdout_fixed_model_and_tube",
        "passed": passed,
        "route": route,
        "bank": signature,
        "training_model_sha256": state["training_model_sha256"],
        "calibrated_tube_sha256": state["calibrated_tube_sha256"],
        "prediction_rows": rows,
        "aggregate": aggregate,
        "predicted_geometry": predicted_geometry,
        "actual_geometry": actual_geometry,
        "tube_containment_pass_count": containment,
        "maximum_tube_fraction": max(float(row["tube_maximum_fraction"]) for row in rows),
        "forbidden_predictor_input_count": 0,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "mpc_validated": False,
        "bc_dagger_or_rl_allowed": False,
    }
    detailed_path = ctx.paths.run_dir / "final_result_detailed.json"
    _write_json(detailed_path, detailed)
    final = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": detailed["phase"],
        "passed": passed,
        "route": route,
        "bank": signature,
        "training_model_sha256": state["training_model_sha256"],
        "calibrated_tube_sha256": state["calibrated_tube_sha256"],
        "aggregate": aggregate,
        "predicted_geometry": _summary_geometry(predicted_geometry),
        "actual_geometry": _summary_geometry(actual_geometry),
        "tube_containment_pass_count": containment,
        "maximum_tube_fraction": detailed["maximum_tube_fraction"],
        "new_raw_count": 1248,
        "formal_timing_unchanged": True,
        "formal_tracking_diagnostic_only": True,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "mpc_validated": False,
        "bc_dagger_or_rl_allowed": False,
        "detailed_sha256": _sha256(detailed_path),
    }
    final_path = ctx.paths.run_dir / "final_result.json"
    _write_json(final_path, final)
    _set_state(
        ctx,
        phase_status="holdout_model_primary_complete",
        primary_pass=passed,
        final_result_sha256=_sha256(final_path),
        final_detailed_sha256=_sha256(detailed_path),
    )
    return final


def run_postprocess(ctx: Context) -> dict[str, Any]:
    state = _require_phase(ctx, "holdout_model_primary_complete")
    independent = _independent_file(ctx, "holdout_model")
    final_path = ctx.paths.run_dir / "final_result.json"
    if (
        _sha256(final_path) != state["final_result_sha256"]
        or independent.get("final_result_sha256") != state["final_result_sha256"]
        or bool(independent.get("route")) and independent.get("route") != _read_json(final_path)["route"]
    ):
        raise ValueError("R8 independent holdout route/hash disagreement")
    inventories = {phase: _inventory(ctx.paths.phase_raw(phase)) for phase in PHASES}
    expected = {"training": 624, "calibration": 312, "holdout": 312}
    inventory_pass = all(inventories[key]["count"] == value for key, value in expected.items())
    final = _read_json(final_path)
    passed = bool(inventory_pass and independent["passed"] and final["passed"])
    route = final["route"]
    report = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "final_server_raw_inventory_and_independent_route_audit",
        "raw_inventories": inventories,
        "expected_raw_counts": expected,
        "actual_raw_count": sum(row["count"] for row in inventories.values()),
        "final_result_sha256": state["final_result_sha256"],
        "independent_holdout_model_sha256": _sha256(ctx.paths.analysis / "holdout_model_independent.json"),
        "route": route,
        "passed": passed,
    }
    _write_json(ctx.paths.run_dir / "server_final_audit.json", report)
    _set_state(
        ctx,
        phase_status="campaign_complete",
        finished=True,
        primary_pass=passed,
        real_tsc_executed=True,
        new_raw_count=1248,
        independent_holdout_model_sha256=report["independent_holdout_model_sha256"],
        server_final_audit_sha256=_sha256(ctx.paths.run_dir / "server_final_audit.json"),
        stop_reason="" if passed else "fresh_holdout_model_or_independent_gate_failed",
        verdict={"route": route, "passed": passed},
    )
    return report


def execute(ctx: Context, *, command: str, backend: str, resume: bool) -> dict[str, Any]:
    if command == "offline":
        if resume:
            raise ValueError("R8 offline does not support resume")
        return prepare_offline(ctx)
    if command in PHASES:
        return run_phase(ctx, command, backend=backend, resume=resume)
    if command == "fit-training":
        return run_fit_training(ctx)
    if command == "authorize-calibration":
        return authorize_calibration(ctx)
    if command == "fit-calibration":
        return run_fit_calibration(ctx)
    if command == "authorize-holdout":
        return authorize_holdout(ctx)
    if command == "finalize":
        return run_finalize(ctx)
    if command == "postprocess":
        return run_postprocess(ctx)
    raise ValueError(f"unsupported R8 command: {command}")


def self_test(config_path: Path) -> dict[str, Any]:
    config_path = config_path.expanduser().resolve()
    cfg = _read_json(config_path)
    _validate_config(cfg, config_path)
    roles = _roles()
    canonical = np.asarray(cfg["request_contract"]["canonical_matrix_columns"], dtype=float)
    replacement = np.asarray(cfg["request_contract"]["replacement_matrix_columns"], dtype=float)
    static = _static_card15_audit(cfg)
    return {
        "schema_version": 1,
        "stage": STAGE,
        "role_count_per_context": len(roles),
        "baseline_count_per_context": sum(row[0] == "baseline" for row in roles),
        "canonical_count_per_context": sum(row[0] == "canonical" for row in roles),
        "replacement_count_per_context": sum(row[0] == "replacement" for row in roles),
        "prospective_rollout_count": int(cfg["rollout_contract"]["maximum_new_rollouts"]),
        "canonical_matrix_rank": int(np.linalg.matrix_rank(canonical)),
        "replacement_matrix_rank": int(np.linalg.matrix_rank(replacement)),
        "static_card15": static,
        "physical_issue_time_centers_available_offline": False,
        "real_tsc_executed": False,
        "passed": bool(
            len(roles) == 39
            and int(np.linalg.matrix_rank(canonical)) == 4
            and int(np.linalg.matrix_rank(replacement)) == 4
            and static["passed"]
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source-d1r11-run", type=Path, required=True)
    parser.add_argument("--source-r2-run", type=Path, required=True)
    parser.add_argument("--source-r4-run", type=Path, required=True)
    parser.add_argument("--source-r6-run", type=Path, required=True)
    parser.add_argument("--source-s21-run", type=Path, required=True)
    parser.add_argument("--source-s23r1-output", type=Path, required=True)
    parser.add_argument("--source-s24-run", type=Path, required=True)
    parser.add_argument("--source-d1r9-v1", type=Path, required=True)
    parser.add_argument("--source-d1r9-v2", type=Path, required=True)
    parser.add_argument("--source-d1r10-run", type=Path, required=True)
    parser.add_argument("--source-d1r10-audit", type=Path, required=True)
    parser.add_argument("--source-stage42r3b-run", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3-run", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3-bank-dir", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3t1-run", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3t1-audit-dir", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3t3-controller-bank", type=Path, required=True)
    parser.add_argument("--q1-run", type=Path, required=True)
    parser.add_argument("--q2-run", type=Path, required=True)
    parser.add_argument("--q1-audit", type=Path, required=True)
    parser.add_argument("--q2-audit", type=Path, required=True)
    parser.add_argument("--r3b-server-audit", type=Path, required=True)
    parser.add_argument("--r3b-snapshot-checks", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument(
        "--command",
        choices=(
            "offline", "training", "fit-training", "authorize-calibration",
            "calibration", "fit-calibration", "authorize-holdout",
            "holdout", "finalize", "postprocess",
        ),
        required=True,
    )
    parser.add_argument("--backend", choices=("serial", "ray"), default="ray")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(args.config), indent=2, sort_keys=True, allow_nan=False))
        return
    context = load_config(
        args.config,
        source_d1r11_run=args.source_d1r11_run,
        source_r2_run=args.source_r2_run,
        source_r4_run=args.source_r4_run,
        source_r6_run=args.source_r6_run,
        run_dir=args.run_dir,
        source_s21_run=args.source_s21_run,
        source_s23r1_output=args.source_s23r1_output,
        source_s24_run=args.source_s24_run,
        source_d1r9_v1=args.source_d1r9_v1,
        source_d1r9_v2=args.source_d1r9_v2,
        source_d1r10_run=args.source_d1r10_run,
        source_d1r10_audit=args.source_d1r10_audit,
        **d1r11._source_kwargs(args),
    )
    result = execute(context, command=args.command, backend=args.backend, resume=args.resume)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
