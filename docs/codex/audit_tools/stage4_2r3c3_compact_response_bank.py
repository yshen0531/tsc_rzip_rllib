#!/usr/bin/env python3
"""Build the authenticated compact Stage4.2R3c3 response bank.

This tool is intentionally run on the TSC server.  It reads every immutable
R3c3 JSON.GZ result and the exact R3c1 baseline results in place.  It writes:

* an audit bank containing provenance and audit-only identities;
* a controller-facing bank containing only allowed numeric causal features;
* a file manifest authenticating both outputs.

The controller-facing bank contains no source-result trajectory, pair,
history, wire-current, experiment, pass/fail, or raw-file identity fields.
R3c3 probe trajectories remain identification evidence, never
demonstrations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3_restart_task_clock_local_response_identification as r3c,
)


SCHEMA_VERSION = 1
EXPECTED_RUN_NAME = (
    "stage4_2r3c3_restart_task_clock_local_response_identification_"
    "20260730_182427"
)
EXPECTED_RAW_COUNT = 256
EXPECTED_RAW_BYTES = 8_933_607
EXPECTED_RAW_INVENTORY_DIGEST = (
    "88bcd02a5dd2ec4def60c1f2e7f2304fb57859836d3b9a34b090bfd91e00e563"
)
EXPECTED_SERVER_AUDIT_SHA256 = (
    "5172fc54a8446418bbcccd31c84515f62ad2594a52904b831a3b2064d52a44b4"
)
EXPECTED_R3C3_PACKAGE_FINGERPRINT = (
    "1ba40b276a6a998e266e68d044c8ad3e819d86b6f7c8e52c7c60c6000a05a661"
)
EXPECTED_R3C3_CONTROL_SPEC_DIGEST = (
    "141e2d167424ad1ab4ddfc6a68ac3a795abcfa1ecc775f4e30a18857d28ae56f"
)
EXPECTED_VISIBLE_MANIFOLD_DIGEST = (
    "538e081d0212174c00ac921b2fd1ce9cf7df4b69e6810892fa9aaf7202e47f9a"
)
EXPECTED_MAX_CONDITION = 8.09839956523926
EXPECTED_MAX_CURRENT_UTILIZATION = 0.39039999999999997

FORBIDDEN_CONTROLLER_KEY_FRAGMENTS = (
    "pair",
    "history",
    "source",
    "experiment",
    "raw",
    "result",
    "wire",
    "pass",
    "fail",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _canonical_digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _rmse(array: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.asarray(array, dtype=float) ** 2)))


def _trajectory_arrays(
    result: Mapping[str, Any], dt_s: float
) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(
        [[row["R"], row["Z"], row["Ip"]] for row in result["trajectory"]],
        dtype=float,
    )
    if (
        values.ndim != 2
        or values.shape[1] != 3
        or len(values) < 2
        or not np.all(np.isfinite(values))
    ):
        raise ValueError("non-finite or malformed R/Z/Ip trajectory")
    velocity = r3c.r1.r8._velocity_components(values, dt_s)
    if velocity.shape != (len(values), 2) or not np.all(
        np.isfinite(velocity)
    ):
        raise ValueError("non-finite or malformed velocity trajectory")
    return values, velocity


def _initial_arrays(
    result: Mapping[str, Any],
) -> tuple[np.ndarray, np.ndarray]:
    row = result["trajectory"][0]
    visible = np.asarray(
        [row["R"], row["Z"], row["Ip"], *row["currents_a_tsc"]],
        dtype=float,
    )
    wire = np.asarray(row["wire_currents_a"], dtype=float).reshape(-1)
    if visible.shape != (17,) or wire.shape != (48,):
        raise ValueError("unexpected initial visible or wire shape")
    if not np.all(np.isfinite(visible)) or not np.all(np.isfinite(wire)):
        raise ValueError("non-finite initial visible or wire state")
    return visible, wire


def _trace_audit(result: Mapping[str, Any]) -> dict[str, Any]:
    spec = dict(result.get("spec") or {})
    trace = list(result.get("controller_trace") or [])
    schedule = {
        int(step): np.asarray(value, dtype=float).reshape(-1)
        for step, value in (
            spec.get("r3c3_probe_delta_by_task_issue_step") or {}
        ).items()
    }
    n_modes = len(next(iter(schedule.values()))) if schedule else 3
    zeros = np.zeros(n_modes, dtype=float)
    forbidden_counts = Counter()
    requested_rows: list[np.ndarray] = []
    applied_rows: list[np.ndarray] = []
    exact = bool(trace and len(schedule) == 4)
    previous_measurement_max = -1
    for row in trace:
        step = int(row.get("task_step", -1))
        expected = schedule.get(step, zeros)
        requested = np.asarray(
            row.get("r3c3_probe_requested_delta", []), dtype=float
        ).reshape(-1)
        applied = np.asarray(
            row.get("r3c3_probe_applied_desired_delta", []), dtype=float
        ).reshape(-1)
        issued = bool(row.get("r3c3_probe_issued"))
        measurement_max = int(row.get("measurement_max_state_index_used", -1))
        exact = bool(
            exact
            and requested.shape == expected.shape == (n_modes,)
            and applied.shape == (n_modes,)
            and np.array_equal(requested, expected)
            and issued == (step in schedule)
            and bool(row.get("computed_online"))
            and str(row.get("baseline_controller_revision"))
            == r3c.r3c1.CONTROLLER_REVISION
            and bool(row.get("r3c3_identification_only"))
            and str(row.get("r3c3_probe_id"))
            == str(spec.get("r3c3_probe_id"))
            and int(row.get("r3c3_probe_mode", -1))
            == int(spec.get("r3c3_probe_mode", -2))
            and int(row.get("r3c3_probe_sign", 0))
            == int(spec.get("r3c3_probe_sign", 1))
            and measurement_max <= step
            and measurement_max >= previous_measurement_max
        )
        previous_measurement_max = measurement_max
        for key in (
            "hidden_wire_used",
            "source_action_used",
            "source_coil_current_used",
            "source_wire_current_used",
            "current_run_future_used",
            "future_measurement_used",
            "pair_or_history_label_used",
            "source_result_used",
        ):
            forbidden_counts[key] += bool(row.get(key))
        forbidden_counts["solver_failure"] += not bool(
            row.get("solver_success")
        )
        forbidden_counts["issued"] += issued
        if issued:
            requested_rows.append(requested)
            applied_rows.append(applied)
    requested = (
        np.stack(requested_rows)
        if len(requested_rows) == 4
        else np.empty((0, n_modes), dtype=float)
    )
    applied = (
        np.stack(applied_rows)
        if len(applied_rows) == 4
        else np.empty((0, n_modes), dtype=float)
    )
    applied_exact = bool(
        requested.shape == applied.shape == (4, n_modes)
        and np.allclose(requested, applied, rtol=0.0, atol=1.0e-12)
    )
    zero_net = bool(
        requested.shape == applied.shape == (4, n_modes)
        and np.allclose(
            requested.sum(axis=0), zeros, rtol=0.0, atol=1.0e-12
        )
        and np.allclose(
            applied.sum(axis=0), zeros, rtol=0.0, atol=1.0e-12
        )
    )
    first_effect_exact = bool(
        schedule
        and min(schedule)
        + int(spec.get("action_delay_steps", -100))
        + 1
        == int(spec.get("r3c3_probe_first_effect_state", -1))
    )
    forbidden_input_count = sum(
        forbidden_counts[key]
        for key in (
            "hidden_wire_used",
            "source_action_used",
            "source_coil_current_used",
            "source_wire_current_used",
            "current_run_future_used",
            "future_measurement_used",
            "pair_or_history_label_used",
            "source_result_used",
        )
    )
    passed = bool(
        exact
        and forbidden_counts["issued"] == 4
        and applied_exact
        and zero_net
        and first_effect_exact
        and forbidden_counts["solver_failure"] == 0
        and forbidden_input_count == 0
    )
    return {
        "passed": passed,
        "trace_exact": exact,
        "trace_steps": len(trace),
        "issued_count": int(forbidden_counts["issued"]),
        "applied_exact": applied_exact,
        "zero_net": zero_net,
        "first_effect_exact": first_effect_exact,
        "solver_failure_count": int(forbidden_counts["solver_failure"]),
        "forbidden_input_count": int(forbidden_input_count),
    }


def _raw_identity(paths: Sequence[Path]) -> list[dict[str, Any]]:
    return [
        {
            "path": path.name,
            "size_bytes": int(path.stat().st_size),
            "sha256": _sha256(path),
        }
        for path in paths
    ]


def _assert_controller_schema(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            lowered = str(key).lower()
            if any(
                fragment in lowered
                for fragment in FORBIDDEN_CONTROLLER_KEY_FRAGMENTS
            ):
                raise ValueError(
                    f"forbidden controller-bank key at {path}: {key}"
                )
            _assert_controller_schema(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _assert_controller_schema(item, f"{path}[{index}]")


def _finite_range(values: Iterable[float]) -> dict[str, float]:
    array = np.asarray(list(values), dtype=float)
    if not array.size or not np.all(np.isfinite(array)):
        raise ValueError("range input is empty or non-finite")
    return {
        "minimum": float(np.min(array)),
        "mean": float(np.mean(array)),
        "maximum": float(np.max(array)),
    }


def _context_key(spec: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        str(spec["pair_id"]),
        str(spec["history_member"]),
        str(spec["target_id"]),
        int(spec["action_delay_steps"]),
        float(spec["slew_scale"]),
    )


def _signed_key(spec: Mapping[str, Any]) -> tuple[Any, ...]:
    return (*_context_key(spec), str(spec["r3c3_probe_id"]))


def _model_feature(context: Mapping[str, Any]) -> list[Any]:
    initial = context["initial_visible"]
    return [
        float(context["target_R_offset_m"]),
        float(context["target_Z_offset_m"]),
        float(context["target_Ip_offset_A"]),
        int(context["actual_delay_steps"]),
        float(context["actual_slew_scale"]),
        *map(float, initial),
    ]


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    r3c.atomic_write_json(path, value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3b-run", required=True, type=Path)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--server-audit", required=True, type=Path)
    parser.add_argument("--audit-output", required=True, type=Path)
    parser.add_argument("--controller-output", required=True, type=Path)
    parser.add_argument("--manifest-output", required=True, type=Path)
    args = parser.parse_args()

    run_dir = args.run_dir.expanduser().resolve()
    server_audit_path = args.server_audit.expanduser().resolve()
    outputs = [
        args.audit_output.expanduser().resolve(),
        args.controller_output.expanduser().resolve(),
        args.manifest_output.expanduser().resolve(),
    ]
    if run_dir.name != EXPECTED_RUN_NAME:
        raise SystemExit(f"unexpected immutable run: {run_dir}")
    for output in outputs:
        if output == run_dir or run_dir in output.parents:
            raise SystemExit("all response-bank outputs must remain outside run")
    if len(set(outputs)) != len(outputs):
        raise SystemExit("response-bank output paths must be distinct")
    if _sha256(server_audit_path) != EXPECTED_SERVER_AUDIT_SHA256:
        raise SystemExit("server audit fingerprint mismatch")

    ctx = r3c.load_stage42r3c3_config(
        args.config,
        source_stage42r3b_run=args.source_stage4_2r3b_run,
        run_dir_override=run_dir,
    )
    selected_pairs, _ = r3c._recompute_selected_pairs(ctx)
    expected_specs = r3c.build_control_specs(ctx, selected_pairs)
    expected_by_id = {
        str(spec["experiment_id"]): spec for spec in expected_specs
    }
    if len(expected_by_id) != EXPECTED_RAW_COUNT:
        raise ValueError("recomputed expected R3c3 control coverage changed")

    manifest = json.loads(
        (run_dir / "stage4_2r3c3_manifest.json").read_text(encoding="utf-8")
    )
    if (
        str(manifest.get("control_spec_digest"))
        != EXPECTED_R3C3_CONTROL_SPEC_DIGEST
        or str(manifest.get("visible_reference_manifold_digest"))
        != EXPECTED_VISIBLE_MANIFOLD_DIGEST
        or str(
            (manifest.get("deployed_package_fingerprint") or {}).get(
                "digest"
            )
        )
        != EXPECTED_R3C3_PACKAGE_FINGERPRINT
    ):
        raise ValueError("immutable R3c3 manifest fingerprint mismatch")

    raw_paths = sorted((ctx.paths.control / "raw").glob("*.json.gz"))
    raw_identity = _raw_identity(raw_paths)
    raw_inventory = {
        "digest": _canonical_digest(raw_identity),
        "n_files": len(raw_identity),
        "total_bytes": sum(int(row["size_bytes"]) for row in raw_identity),
        "files": raw_identity,
    }
    if (
        raw_inventory["n_files"] != EXPECTED_RAW_COUNT
        or raw_inventory["total_bytes"] != EXPECTED_RAW_BYTES
        or raw_inventory["digest"] != EXPECTED_RAW_INVENTORY_DIGEST
    ):
        raise ValueError("immutable R3c3 raw inventory mismatch")

    results = [r3c.read_json_gz(path) for path in raw_paths]
    actual_by_id = {
        str(result.get("experiment_id", "")): result for result in results
    }
    if set(actual_by_id) != set(expected_by_id):
        raise ValueError("R3c3 raw experiment identity set mismatch")
    if any(
        actual_by_id[experiment_id].get("spec") != expected
        for experiment_id, expected in expected_by_id.items()
    ):
        raise ValueError("R3c3 raw spec mismatch")
    if any(
        not bool(result.get("success"))
        or not bool(result.get("completed"))
        or result.get("stage") != r3c.STAGE
        or result.get("controller_revision") != r3c.CONTROLLER_REVISION
        for result in results
    ):
        raise ValueError("R3c3 raw execution completeness mismatch")

    server_audit = json.loads(server_audit_path.read_text(encoding="utf-8"))
    if (
        server_audit.get("stage") != r3c.STAGE
        or Path(str(server_audit.get("run_dir", ""))).resolve() != run_dir
        or not bool(server_audit.get("raw_and_manifest_integrity_passed"))
        or not bool(server_audit.get("recomputed_identification_gate_pass"))
        or int(server_audit.get("control_raw_actual", -1))
        != EXPECTED_RAW_COUNT
        or str(server_audit.get("deployed_package_fingerprint_digest"))
        != EXPECTED_R3C3_PACKAGE_FINGERPRINT
    ):
        raise ValueError("R3c3 server audit is incompatible")

    dt_ms = int(
        r3c.r1._r13_ctx(ctx.source_ctx.r1_ctx)
        .r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34.env_cfg[
            "dt_ms"
        ]
    )
    dt_s = dt_ms / 1000.0
    baseline_dir = (
        ctx.source_r3c1_run
        / "stage4_2r3c1_authenticated_visible_manifold_control"
        / "raw"
    )
    baseline_cache: dict[str, Mapping[str, Any]] = {}
    baseline_paths: dict[str, Path] = {}
    signed_groups: dict[
        tuple[Any, ...], dict[int, Mapping[str, Any]]
    ] = defaultdict(dict)
    raw_path_by_id = {
        path.name.removesuffix(".json.gz"): path for path in raw_paths
    }
    for result in results:
        spec = result["spec"]
        key = _signed_key(spec)
        sign = int(spec["r3c3_probe_sign"])
        if sign in signed_groups[key]:
            raise ValueError(f"duplicate signed response {key} {sign}")
        signed_groups[key][sign] = result

    expected_basis = [
        dict(row) for row in ctx.cfg["identification_probe"]["basis"]
    ]
    expected_basis_by_id = {
        str(row["probe_id"]): (index, row)
        for index, row in enumerate(expected_basis)
    }
    central_cfg = ctx.cfg["identification_probe"]["central_symmetry"]
    context_audit: dict[tuple[Any, ...], dict[str, Any]] = {}
    response_metrics: list[dict[str, Any]] = []
    odd_by_key: dict[
        tuple[Any, ...], tuple[np.ndarray, np.ndarray, int]
    ] = {}
    trace_pass_count = 0
    max_current_values: list[float] = []

    for result in results:
        trace = _trace_audit(result)
        trace_pass_count += bool(trace["passed"])
        formal = r3c._formal_metrics(ctx, result)
        max_current_values.append(float(formal["max_current_utilization"]))
    if trace_pass_count != EXPECTED_RAW_COUNT:
        raise ValueError("R3c3 causal probe trace authentication failed")

    for key in sorted(signed_groups):
        members = signed_groups[key]
        if set(members) != {-1, 1}:
            raise ValueError(f"incomplete signed response {key}")
        plus = members[1]
        minus = members[-1]
        plus_spec = plus["spec"]
        minus_spec = minus["spec"]
        baseline_id = str(plus_spec["baseline_experiment_id"])
        if baseline_id != str(minus_spec["baseline_experiment_id"]):
            raise ValueError(f"signed baseline mismatch {key}")
        baseline_path = baseline_dir / f"{baseline_id}.json.gz"
        if baseline_id not in baseline_cache:
            if not baseline_path.is_file():
                raise ValueError(f"missing R3c1 baseline {baseline_id}")
            baseline_cache[baseline_id] = r3c.read_json_gz(baseline_path)
            baseline_paths[baseline_id] = baseline_path
        baseline = baseline_cache[baseline_id]
        if (
            not bool(baseline.get("success"))
            or baseline.get("stage") != r3c.r3c1.STAGE
            or baseline.get("controller_revision")
            != r3c.r3c1.CONTROLLER_REVISION
        ):
            raise ValueError(f"invalid R3c1 baseline {baseline_id}")

        plus_y, plus_v = _trajectory_arrays(plus, dt_s)
        minus_y, minus_v = _trajectory_arrays(minus, dt_s)
        base_y, base_v = _trajectory_arrays(baseline, dt_s)
        if (
            plus_y.shape != minus_y.shape
            or plus_y.shape != base_y.shape
            or plus_v.shape != minus_v.shape
            or plus_v.shape != base_v.shape
        ):
            raise ValueError(f"signed/baseline trajectory shape mismatch {key}")
        plus_initial = _initial_arrays(plus)
        minus_initial = _initial_arrays(minus)
        base_initial = _initial_arrays(baseline)
        initial_exact = bool(
            np.array_equal(plus_initial[0], minus_initial[0])
            and np.array_equal(plus_initial[0], base_initial[0])
            and np.array_equal(plus_initial[1], minus_initial[1])
            and np.array_equal(plus_initial[1], base_initial[1])
        )
        if not initial_exact:
            raise ValueError(f"signed/baseline initial restart mismatch {key}")

        probe_id = str(plus_spec["r3c3_probe_id"])
        if probe_id not in expected_basis_by_id:
            raise ValueError(f"unknown response basis {probe_id}")
        basis_index, basis_spec = expected_basis_by_id[probe_id]
        amplitude = float(plus_spec["r3c3_probe_amplitude"])
        first_effect = int(plus_spec["r3c3_probe_first_effect_state"])
        if (
            not math.isclose(amplitude, 0.0075, rel_tol=0.0, abs_tol=1e-15)
            or float(minus_spec["r3c3_probe_amplitude"]) != amplitude
            or int(plus_spec["r3c3_probe_mode"])
            != int(basis_spec["mode"])
            or int(minus_spec["r3c3_probe_mode"])
            != int(basis_spec["mode"])
            or first_effect != int(basis_spec["first_effect_state"])
            or int(minus_spec["r3c3_probe_first_effect_state"])
            != first_effect
        ):
            raise ValueError(f"response basis contract mismatch {key}")
        plus_schedule = {
            int(step): list(map(float, value))
            for step, value in plus_spec[
                "r3c3_probe_delta_by_task_issue_step"
            ].items()
        }
        minus_schedule = {
            int(step): list(map(float, value))
            for step, value in minus_spec[
                "r3c3_probe_delta_by_task_issue_step"
            ].items()
        }
        if (
            set(plus_schedule) != set(minus_schedule)
            or len(plus_schedule) != 4
            or any(
                not np.array_equal(
                    np.asarray(plus_schedule[step], dtype=float),
                    -np.asarray(minus_schedule[step], dtype=float),
                )
                for step in plus_schedule
            )
            or min(plus_schedule)
            + int(plus_spec["action_delay_steps"])
            + 1
            != first_effect
        ):
            raise ValueError(f"signed schedule mismatch {key}")

        odd_y = (plus_y - minus_y) / 2.0
        odd_v = (plus_v - minus_v) / 2.0
        even_y = (plus_y + minus_y) / 2.0 - base_y
        even_v = (plus_v + minus_v) / 2.0 - base_v
        section = slice(first_effect, len(plus_y))
        velocity_rmse = _rmse(even_v[section, :2])
        position_rmse = _rmse(even_y[section, :2])
        ip_rmse = _rmse(even_y[section, 2])
        central_pass = bool(
            velocity_rmse
            <= float(central_cfg["maximum_even_velocity_rmse_m_per_s"])
            and position_rmse
            <= float(central_cfg["maximum_even_position_rmse_m"])
            and ip_rmse <= float(central_cfg["maximum_even_ip_rmse_A"])
        )
        if not central_pass:
            raise ValueError(f"central response gate failed {key}")
        odd_by_key[key] = (odd_y, odd_v, first_effect)

        context_key = key[:5]
        context = context_audit.get(context_key)
        if context is None:
            initial_visible, initial_wire = base_initial
            baseline_trace = list(baseline.get("controller_trace") or [])
            reference_phases = {
                int(row["reference_phase_start"])
                for row in baseline_trace
                if "reference_phase_start" in row
            }
            if len(reference_phases) != 1:
                raise ValueError(
                    f"R3c1 baseline reference phase is not unique {context_key}"
                )
            context = {
                "audit_identity": {
                    "pair_id": str(context_key[0]),
                    "history_member": str(context_key[1]),
                    "target_id": str(context_key[2]),
                    "baseline_experiment_id": baseline_id,
                    "state_generation_experiment_id": str(
                        plus_spec["state_generation_experiment_id"]
                    ),
                },
                "actual_delay_steps": int(context_key[3]),
                "actual_slew_scale": float(context_key[4]),
                "actuator_gain_by_mode": list(
                    map(float, plus_spec["actuator_gain_by_mode"])
                ),
                "target_R_offset_m": float(plus_spec["target_R_offset_m"]),
                "target_Z_offset_m": float(plus_spec["target_Z_offset_m"]),
                "target_Ip_offset_A": float(plus_spec["target_Ip_offset_A"]),
                "reference_phase_start": int(next(iter(reference_phases))),
                "horizon_steps": int(plus_spec["horizon_steps"]),
                "initial_visible": initial_visible.tolist(),
                "initial_wire_sha256": _canonical_digest(
                    initial_wire.tolist()
                ),
                "baseline_file": {
                    "path": baseline_path.name,
                    "size_bytes": int(baseline_path.stat().st_size),
                    "sha256": _sha256(baseline_path),
                },
                "offline_design_only_baseline": {
                    "RZI_by_state": base_y.tolist(),
                    "velocity_RZ_by_state": base_v.tolist(),
                    "formal_metrics": r3c._formal_metrics(ctx, baseline),
                    "controller_use_forbidden": True,
                },
                "responses": [],
            }
            context_audit[context_key] = context
        elif (
            context["audit_identity"]["baseline_experiment_id"] != baseline_id
            or context["initial_visible"] != base_initial[0].tolist()
            or context["initial_wire_sha256"]
            != _canonical_digest(base_initial[1].tolist())
        ):
            raise ValueError(f"context baseline identity changed {context_key}")

        response = {
            "basis_index": int(basis_index),
            "audit_probe_id": probe_id,
            "mode_index": int(basis_spec["mode"]),
            "amplitude": amplitude,
            "first_effect_state": first_effect,
            "plus_file": {
                "path": raw_path_by_id[str(plus["experiment_id"])].name,
                "size_bytes": int(
                    raw_path_by_id[str(plus["experiment_id"])].stat().st_size
                ),
                "sha256": _sha256(
                    raw_path_by_id[str(plus["experiment_id"])]
                ),
            },
            "minus_file": {
                "path": raw_path_by_id[str(minus["experiment_id"])].name,
                "size_bytes": int(
                    raw_path_by_id[str(minus["experiment_id"])].stat().st_size
                ),
                "sha256": _sha256(
                    raw_path_by_id[str(minus["experiment_id"])]
                ),
            },
            "positive_schedule_by_task_issue_step": [
                [int(step), list(map(float, plus_schedule[step]))]
                for step in sorted(plus_schedule)
            ],
            "delta_RZI_by_state": odd_y.tolist(),
            "delta_velocity_RZ_by_state": odd_v.tolist(),
            "central_even_metrics": {
                "velocity_RZ_rmse_m_per_s": velocity_rmse,
                "position_RZ_rmse_m": position_rmse,
                "Ip_rmse_A": ip_rmse,
                "passed": central_pass,
            },
        }
        context["responses"].append(response)
        response_metrics.append(
            {
                "context_key": list(context_key),
                "basis_index": int(basis_index),
                "velocity_RZ_rmse_m_per_s": velocity_rmse,
                "position_RZ_rmse_m": position_rmse,
                "Ip_rmse_A": ip_rmse,
            }
        )

    expected_contexts = int(
        ctx.cfg["control_matrix"]["expected_baseline_contexts"]
    )
    if len(context_audit) != expected_contexts:
        raise ValueError("baseline context coverage mismatch")
    if len(baseline_cache) != expected_contexts:
        raise ValueError("R3c1 baseline identity coverage mismatch")
    for key, context in context_audit.items():
        context["responses"].sort(key=lambda row: row["basis_index"])
        if [row["basis_index"] for row in context["responses"]] != [0, 1, 2, 3]:
            raise ValueError(f"response basis coverage mismatch {key}")

    hidden_cfg = ctx.cfg["identification_probe"]["matched_hidden_history"]
    hidden_groups: dict[
        tuple[Any, ...], dict[str, tuple[np.ndarray, np.ndarray, int]]
    ] = defaultdict(dict)
    for key, value in odd_by_key.items():
        hidden_groups[(key[0], key[2], key[3], key[4], key[5])][
            str(key[1])
        ] = value
    hidden_rows = []
    for key in sorted(hidden_groups):
        members = hidden_groups[key]
        if set(members) != {"plus_first", "minus_first"}:
            raise ValueError(f"matched-hidden-history coverage mismatch {key}")
        plus = members["plus_first"]
        minus = members["minus_first"]
        section = slice(max(plus[2], minus[2]), len(plus[0]))
        velocity_rmse = _rmse(
            plus[1][section, :2] - minus[1][section, :2]
        )
        position_rmse = _rmse(
            plus[0][section, :2] - minus[0][section, :2]
        )
        ip_rmse = _rmse(plus[0][section, 2] - minus[0][section, 2])
        passed = bool(
            velocity_rmse
            <= float(hidden_cfg["maximum_odd_velocity_rmse_m_per_s"])
            and position_rmse
            <= float(hidden_cfg["maximum_odd_position_rmse_m"])
            and ip_rmse <= float(hidden_cfg["maximum_odd_ip_rmse_A"])
        )
        if not passed:
            raise ValueError(f"matched-hidden-history response failed {key}")
        hidden_rows.append(
            {
                "audit_group": list(key),
                "velocity_RZ_rmse_m_per_s": velocity_rmse,
                "position_RZ_rmse_m": position_rmse,
                "Ip_rmse_A": ip_rmse,
                "passed": passed,
            }
        )

    condition_groups: dict[
        tuple[Any, ...], dict[str, tuple[np.ndarray, np.ndarray, int]]
    ] = defaultdict(dict)
    for key, value in odd_by_key.items():
        condition_groups[key[:5]][str(key[5])] = value
    condition_rows = []
    maximum_allowed = float(
        ctx.cfg["identification_probe"][
            "maximum_selected_velocity_condition_number"
        ]
    )
    for key in sorted(condition_groups):
        responses = condition_groups[key]
        if set(responses) != set(expected_basis_by_id):
            raise ValueError(f"condition basis coverage mismatch {key}")
        first_state = min(value[2] for value in responses.values())
        matrix = np.stack(
            [
                responses[probe_id][1][first_state:, :2].reshape(-1)
                for probe_id in sorted(responses)
            ],
            axis=1,
        )
        rank = int(np.linalg.matrix_rank(matrix))
        condition = float(np.linalg.cond(matrix))
        passed = bool(
            rank == 4
            and math.isfinite(condition)
            and condition <= maximum_allowed
        )
        if not passed:
            raise ValueError(f"response condition gate failed {key}")
        condition_rows.append(
            {
                "audit_context": list(key),
                "rank": rank,
                "condition_number": condition,
                "passed": passed,
            }
        )

    max_condition = max(row["condition_number"] for row in condition_rows)
    max_current = max(max_current_values)
    if not math.isclose(
        max_condition, EXPECTED_MAX_CONDITION, rel_tol=0.0, abs_tol=1e-14
    ):
        raise ValueError("recomputed maximum condition number changed")
    if not math.isclose(
        max_current,
        EXPECTED_MAX_CURRENT_UTILIZATION,
        rel_tol=0.0,
        abs_tol=1e-15,
    ):
        raise ValueError("recomputed maximum current utilization changed")

    baseline_identity = [
        {
            "path": path.name,
            "size_bytes": int(path.stat().st_size),
            "sha256": _sha256(path),
        }
        for _, path in sorted(baseline_paths.items())
    ]
    provenance_contract = {
        "schema_version": SCHEMA_VERSION,
        "stage": r3c.STAGE,
        "run_name": run_dir.name,
        "raw_inventory_digest": raw_inventory["digest"],
        "server_audit_sha256": _sha256(server_audit_path),
        "r3c3_package_fingerprint": EXPECTED_R3C3_PACKAGE_FINGERPRINT,
        "r3c3_control_spec_digest": EXPECTED_R3C3_CONTROL_SPEC_DIGEST,
        "visible_manifold_digest": EXPECTED_VISIBLE_MANIFOLD_DIGEST,
        "r3c1_baseline_inventory_digest": _canonical_digest(
            baseline_identity
        ),
        "signed_response_contract": (
            "half_positive_minus_negative_about_exact_R3c1_baseline"
        ),
        "probe_amplitude": 0.0075,
        "probe_trajectories_are_demonstrations": False,
    }
    provenance_digest = _canonical_digest(provenance_contract)

    audit_contexts = [
        context_audit[key] for key in sorted(context_audit)
    ]
    audit_bank = {
        "schema_version": SCHEMA_VERSION,
        "purpose": "Stage4.2R3c3 compact authenticated response audit bank",
        "immutable_run_dir": str(run_dir),
        "provenance_contract": provenance_contract,
        "provenance_digest": provenance_digest,
        "raw_inventory": raw_inventory,
        "r3c1_baseline_inventory": {
            "digest": _canonical_digest(baseline_identity),
            "n_files": len(baseline_identity),
            "total_bytes": sum(
                int(row["size_bytes"]) for row in baseline_identity
            ),
            "files": baseline_identity,
        },
        "authentication_summary": {
            "expected_raw_count": EXPECTED_RAW_COUNT,
            "actual_raw_count": len(results),
            "expected_context_count": expected_contexts,
            "actual_context_count": len(audit_contexts),
            "signed_response_count": len(response_metrics),
            "trace_authentication_count": trace_pass_count,
            "central_symmetry_count": len(response_metrics),
            "matched_hidden_history_count": len(hidden_rows),
            "condition_number_count": len(condition_rows),
            "maximum_selected_velocity_condition_number": max_condition,
            "maximum_current_utilization": max_current,
            "all_authentication_gates_passed": True,
        },
        "response_metric_ranges": {
            "central_even_velocity_RZ_rmse_m_per_s": _finite_range(
                row["velocity_RZ_rmse_m_per_s"] for row in response_metrics
            ),
            "central_even_position_RZ_rmse_m": _finite_range(
                row["position_RZ_rmse_m"] for row in response_metrics
            ),
            "central_even_Ip_rmse_A": _finite_range(
                row["Ip_rmse_A"] for row in response_metrics
            ),
            "matched_hidden_velocity_RZ_rmse_m_per_s": _finite_range(
                row["velocity_RZ_rmse_m_per_s"] for row in hidden_rows
            ),
            "matched_hidden_position_RZ_rmse_m": _finite_range(
                row["position_RZ_rmse_m"] for row in hidden_rows
            ),
            "matched_hidden_Ip_rmse_A": _finite_range(
                row["Ip_rmse_A"] for row in hidden_rows
            ),
            "condition_number": _finite_range(
                row["condition_number"] for row in condition_rows
            ),
        },
        "contexts": audit_contexts,
        "matched_hidden_history_audit": hidden_rows,
        "condition_number_audit": condition_rows,
        "scientific_guardrails": {
            "development_set_only": True,
            "independent_hidden_history_confirmation": False,
            "unseen_target_validation": False,
            "probe_trajectories_allowed_in_expert_dataset": False,
            "offline_baseline_trajectories_allowed_in_controller": False,
        },
    }

    controller_samples = []
    for context in audit_contexts:
        initial = list(map(float, context["initial_visible"]))
        responses = []
        for response in context["responses"]:
            responses.append(
                {
                    "basis_index": int(response["basis_index"]),
                    "mode_index": int(response["mode_index"]),
                    "amplitude": float(response["amplitude"]),
                    "first_effect_state": int(
                        response["first_effect_state"]
                    ),
                    "positive_schedule_by_task_issue_step": response[
                        "positive_schedule_by_task_issue_step"
                    ],
                    "delta_RZI_by_state": response["delta_RZI_by_state"],
                    "delta_velocity_RZ_by_state": response[
                        "delta_velocity_RZ_by_state"
                    ],
                }
            )
        controller_samples.append(
            {
                "sample_index": -1,
                "initial_R_m": initial[0],
                "initial_Z_m": initial[1],
                "initial_Ip_A": initial[2],
                "initial_coil_currents_A": initial[3:],
                "target_R_offset_m": float(context["target_R_offset_m"]),
                "target_Z_offset_m": float(context["target_Z_offset_m"]),
                "target_Ip_offset_A": float(context["target_Ip_offset_A"]),
                "actuator_delay_steps": int(
                    context["actual_delay_steps"]
                ),
                "actuator_gain_by_mode": list(
                    map(float, context["actuator_gain_by_mode"])
                ),
                "actuator_slew_scale": float(
                    context["actual_slew_scale"]
                ),
                "reference_phase_start": int(
                    context["reference_phase_start"]
                ),
                "horizon_steps": int(context["horizon_steps"]),
                "basis_responses": responses,
            }
        )
    controller_samples.sort(
        key=lambda row: _model_feature(
            {
                "target_R_offset_m": row["target_R_offset_m"],
                "target_Z_offset_m": row["target_Z_offset_m"],
                "target_Ip_offset_A": row["target_Ip_offset_A"],
                "actual_delay_steps": row["actuator_delay_steps"],
                "actual_slew_scale": row["actuator_slew_scale"],
                "initial_visible": [
                    row["initial_R_m"],
                    row["initial_Z_m"],
                    row["initial_Ip_A"],
                    *row["initial_coil_currents_A"],
                ],
            }
        )
    )
    for index, sample in enumerate(controller_samples):
        sample["sample_index"] = index

    controller_bank = {
        "schema_version": SCHEMA_VERSION,
        "purpose": "bounded numeric local response model for Stage4.2R3c4",
        "provenance_digest": provenance_digest,
        "nominal_controller_revision": r3c.r3c1.CONTROLLER_REVISION,
        "sample_count": len(controller_samples),
        "basis_count": 4,
        "coefficient_lower_bound": -1.0,
        "coefficient_upper_bound": 1.0,
        "amplitude": 0.0075,
        "selection_contract": (
            "exact_target_and_actuator_filter_then_scaled_numeric_"
            "visible_and_coil_nearest_neighbor"
        ),
        "allowed_measurement_fields": [
            "R",
            "Z",
            "Ip",
            "coil_currents",
        ],
        "samples": controller_samples,
        "identification_only": True,
        "demonstration_data": False,
        "independent_confirmation": False,
    }
    _assert_controller_schema(controller_bank)
    if len(controller_samples) != expected_contexts:
        raise ValueError("controller-facing response sample count mismatch")

    audit_bank["controller_bank_canonical_digest"] = _canonical_digest(
        controller_bank
    )
    _write_json(outputs[0], audit_bank)
    _write_json(outputs[1], controller_bank)
    file_rows = [
        {
            "role": "audit_bank",
            "path": outputs[0].name,
            "size_bytes": int(outputs[0].stat().st_size),
            "sha256": _sha256(outputs[0]),
        },
        {
            "role": "controller_bank",
            "path": outputs[1].name,
            "size_bytes": int(outputs[1].stat().st_size),
            "sha256": _sha256(outputs[1]),
            "canonical_digest": _canonical_digest(controller_bank),
        },
    ]
    output_manifest = {
        "schema_version": SCHEMA_VERSION,
        "purpose": "Stage4.2R3c3 compact response-bank file manifest",
        "provenance_digest": provenance_digest,
        "files": file_rows,
        "inventory_digest": _canonical_digest(file_rows),
    }
    _write_json(outputs[2], output_manifest)

    print(
        json.dumps(
            {
                "audit_output": str(outputs[0]),
                "audit_sha256": _sha256(outputs[0]),
                "controller_output": str(outputs[1]),
                "controller_sha256": _sha256(outputs[1]),
                "manifest_output": str(outputs[2]),
                "manifest_sha256": _sha256(outputs[2]),
                "raw_count": len(results),
                "context_count": len(controller_samples),
                "signed_response_count": len(response_metrics),
                "matched_hidden_history_count": len(hidden_rows),
                "condition_number_count": len(condition_rows),
                "provenance_digest": provenance_digest,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
