#!/usr/bin/env python3
"""Audit-only six-basis conditioning diagnostic for Stage4.2R3c3T1.

Run on the TSC server.  The script authenticates every immutable T1 raw
result, reconstructs the two signed odd transport responses, combines them
with the frozen four-basis R3c3 audit bank, and tests whether a *global
reduction* of either new probe amplitude could produce a prospectively
testable T2 design.  It does not change the failed T1 verdict and does not
authorize R3c4.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t1_long_separation_zero_net_transport_identification as t1,
)


EXPECTED_RUN_NAME = (
    "stage4_2r3c3t1_long_separation_zero_net_transport_identification_"
    "20260730_204441"
)
EXPECTED_SERVER_AUDIT_SHA256 = (
    "0f24b44f32493b390832474d5c78cc2455a8ba0c455b496b16c04f8deaf3a2bd"
)
EXPECTED_OLD_BANK_SHA256 = (
    "51bb4eeabfc8a4c5cc3983d75469f484a2278e6ef37cf03cf93ac650f9404b32"
)
EXPECTED_RAW_COUNT = 128
EXPECTED_RAW_DIGEST = (
    "f19a04dcb6b597e97517482d602a6cfdb3c0a1f0b4bfd7a1507b90ae2cc0876f"
)
MAXIMUM_CONDITION = 25.0


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_digest(value: Any) -> str:
    text = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _raw_identity(paths: Sequence[Path]) -> list[dict[str, Any]]:
    return [
        {
            "path": path.name,
            "size_bytes": int(path.stat().st_size),
            "sha256": _sha256(path),
        }
        for path in paths
    ]


def _context_key(spec: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        str(spec["pair_id"]),
        str(spec["history_member"]),
        str(spec["target_id"]),
        int(spec["action_delay_steps"]),
        float(spec["slew_scale"]),
    )


def _old_context_key(context: Mapping[str, Any]) -> tuple[Any, ...]:
    identity = context["audit_identity"]
    return (
        str(identity["pair_id"]),
        str(identity["history_member"]),
        str(identity["target_id"]),
        int(context["actual_delay_steps"]),
        float(context["actual_slew_scale"]),
    )


def _condition(columns: Sequence[np.ndarray]) -> tuple[int, float, list[float]]:
    matrix = np.stack(
        [np.asarray(column, dtype=float)[3:, :2].reshape(-1) for column in columns],
        axis=1,
    )
    singular = np.linalg.svd(matrix, compute_uv=False)
    return (
        int(np.linalg.matrix_rank(matrix)),
        float(np.linalg.cond(matrix)),
        singular.tolist(),
    )


def _scaled_conditions(
    contexts: Sequence[dict[str, Any]], scale0: float, scale1: float
) -> np.ndarray:
    values = []
    for context in contexts:
        columns = [
            *context["old_columns"],
            context["new_columns"][0] * scale0,
            context["new_columns"][1] * scale1,
        ]
        values.append(_condition(columns)[1])
    return np.asarray(values, dtype=float)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--server-audit", required=True, type=Path)
    parser.add_argument("--old-audit-bank", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    run_dir = args.run_dir.expanduser().resolve()
    server_audit_path = args.server_audit.expanduser().resolve()
    old_bank_path = args.old_audit_bank.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if run_dir.name != EXPECTED_RUN_NAME:
        raise SystemExit(f"unexpected immutable T1 run: {run_dir}")
    if output == run_dir or run_dir in output.parents:
        raise SystemExit("diagnostic output must remain outside run tree")
    if _sha256(server_audit_path) != EXPECTED_SERVER_AUDIT_SHA256:
        raise SystemExit("T1 server audit hash mismatch")
    if _sha256(old_bank_path) != EXPECTED_OLD_BANK_SHA256:
        raise SystemExit("old R3c3 bank hash mismatch")

    server_audit = json.loads(
        server_audit_path.read_text(encoding="utf-8")
    )
    if (
        server_audit.get("stage") != t1.STAGE
        or not bool(server_audit.get("raw_and_manifest_integrity_passed"))
        or bool(server_audit.get("certified_primary_pass"))
        or bool(
            server_audit.get("combined_condition_number_gate_passed")
        )
        or int(server_audit.get("control_raw_actual", -1))
        != EXPECTED_RAW_COUNT
    ):
        raise ValueError("T1 server audit outcome changed")

    raw_dir = (
        run_dir
        / "stage4_2r3c3t1_transport_response_identification"
        / "raw"
    )
    raw_paths = sorted(raw_dir.glob("*.json.gz"))
    raw_identity = _raw_identity(raw_paths)
    if (
        len(raw_paths) != EXPECTED_RAW_COUNT
        or _canonical_digest(raw_identity) != EXPECTED_RAW_DIGEST
    ):
        raise ValueError("T1 raw inventory mismatch")
    results = [t1.r3c3.read_json_gz(path) for path in raw_paths]
    if any(
        result.get("stage") != t1.STAGE
        or result.get("controller_revision") != t1.CONTROLLER_REVISION
        or not bool(result.get("completed"))
        or not bool(result.get("success"))
        or not bool(t1._phase_trace_valid(result)["passed"])
        for result in results
    ):
        raise ValueError("T1 raw execution or trace authentication failed")

    signed: dict[
        tuple[Any, ...], dict[str, dict[int, Mapping[str, Any]]]
    ] = defaultdict(lambda: defaultdict(dict))
    for result in results:
        spec = result["spec"]
        signed[_context_key(spec)][str(spec["r3c3_probe_id"])][
            int(spec["r3c3_probe_sign"])
        ] = result

    old_bank = json.loads(old_bank_path.read_text(encoding="utf-8"))
    old_by_key = {
        _old_context_key(context): context
        for context in old_bank["contexts"]
    }
    if len(old_by_key) != 32 or set(old_by_key) != set(signed):
        raise ValueError("old/new response context coverage mismatch")

    contexts: list[dict[str, Any]] = []
    rows = []
    for key in sorted(old_by_key):
        probes = signed[key]
        if set(probes) != {"transport_mode0", "transport_mode1"}:
            raise ValueError(f"T1 basis coverage mismatch: {key}")
        new_columns = []
        for probe_id in ("transport_mode0", "transport_mode1"):
            members = probes[probe_id]
            if set(members) != {-1, 1}:
                raise ValueError(f"T1 signed coverage mismatch: {key}")
            _, plus_v = t1.r3c3._trajectory_arrays(members[1], 0.01)
            _, minus_v = t1.r3c3._trajectory_arrays(members[-1], 0.01)
            new_columns.append((plus_v - minus_v) / 2.0)
        old_columns = [
            np.asarray(
                response["delta_velocity_RZ_by_state"], dtype=float
            )
            for response in sorted(
                old_by_key[key]["responses"],
                key=lambda row: int(row["basis_index"]),
            )
        ]
        if len(old_columns) != 4 or len(
            {column.shape for column in [*old_columns, *new_columns]}
        ) != 1:
            raise ValueError(f"six-basis response shape mismatch: {key}")
        rank, condition, singular = _condition(
            [*old_columns, *new_columns]
        )
        matrix = np.stack(
            [
                column[3:, :2].reshape(-1)
                for column in [*old_columns, *new_columns]
            ],
            axis=1,
        )
        norms = np.linalg.norm(matrix, axis=0)
        normalized = matrix / np.maximum(norms[None, :], 1.0e-30)
        correlation = normalized.T @ normalized
        cross_old_new = np.abs(correlation[:4, 4:])
        row = {
            "pair_id": key[0],
            "history_member": key[1],
            "target_id": key[2],
            "actual_delay_steps": key[3],
            "actual_slew_scale": key[4],
            "rank": rank,
            "condition_number": condition,
            "condition_number_pass": bool(
                rank == 6
                and math.isfinite(condition)
                and condition <= MAXIMUM_CONDITION
            ),
            "singular_values": singular,
            "column_norms": norms.tolist(),
            "maximum_absolute_old_new_column_correlation": float(
                np.max(cross_old_new)
            ),
        }
        rows.append(row)
        contexts.append(
            {
                "key": key,
                "old_columns": old_columns,
                "new_columns": new_columns,
            }
        )

    scales = np.linspace(0.25, 1.0, 151)
    best = None
    feasible = []
    for scale0 in scales:
        for scale1 in scales:
            conditions = _scaled_conditions(
                contexts, float(scale0), float(scale1)
            )
            maximum = float(np.max(conditions))
            candidate = {
                "transport_mode0_scale": float(scale0),
                "transport_mode1_scale": float(scale1),
                "maximum_condition_number": maximum,
                "pass_count": int(
                    np.count_nonzero(conditions <= MAXIMUM_CONDITION)
                ),
                "failure_count": int(
                    np.count_nonzero(conditions > MAXIMUM_CONDITION)
                ),
                "minimum_condition_number": float(np.min(conditions)),
                "mean_condition_number": float(np.mean(conditions)),
            }
            score = (
                maximum,
                max(1.0 - scale0, 1.0 - scale1),
                2.0 - scale0 - scale1,
            )
            if best is None or score < best[0]:
                best = (score, candidate)
            if maximum <= MAXIMUM_CONDITION:
                feasible.append(candidate)
    if best is None:
        raise RuntimeError("empty scaling diagnostic")
    least_reduction = None
    if feasible:
        least_reduction = min(
            feasible,
            key=lambda row: (
                max(
                    1.0 - row["transport_mode0_scale"],
                    1.0 - row["transport_mode1_scale"],
                ),
                2.0
                - row["transport_mode0_scale"]
                - row["transport_mode1_scale"],
                row["maximum_condition_number"],
            ),
        )

    original_conditions = _scaled_conditions(contexts, 1.0, 1.0)
    result = {
        "schema_version": 1,
        "stage": "Stage4.2R3c3T1_condition_diagnostic",
        "purpose": (
            "audit-only global reduced-amplitude T2 basis design; "
            "does not change failed T1 verdict"
        ),
        "inputs": {
            "immutable_t1_run": str(run_dir),
            "server_audit_sha256": _sha256(server_audit_path),
            "old_audit_bank_sha256": _sha256(old_bank_path),
            "t1_raw_count": len(raw_paths),
            "t1_raw_inventory_digest": _canonical_digest(raw_identity),
        },
        "original_six_basis": {
            "context_count": len(rows),
            "rank6_count": sum(row["rank"] == 6 for row in rows),
            "condition_pass_count": sum(
                row["condition_number_pass"] for row in rows
            ),
            "condition_failure_count": sum(
                not row["condition_number_pass"] for row in rows
            ),
            "minimum_condition_number": float(
                np.min(original_conditions)
            ),
            "mean_condition_number": float(
                np.mean(original_conditions)
            ),
            "maximum_condition_number": float(
                np.max(original_conditions)
            ),
            "maximum_absolute_old_new_column_correlation": max(
                row[
                    "maximum_absolute_old_new_column_correlation"
                ]
                for row in rows
            ),
        },
        "global_reduced_amplitude_grid": {
            "scale_minimum": float(scales[0]),
            "scale_maximum": float(scales[-1]),
            "scale_step": float(scales[1] - scales[0]),
            "candidate_count": int(len(scales) ** 2),
            "maximum_allowed_condition_number": MAXIMUM_CONDITION,
            "feasible_candidate_count": len(feasible),
            "minimum_maximum_condition_candidate": best[1],
            "least_amplitude_reduction_feasible_candidate": (
                least_reduction
            ),
        },
        "context_rows": rows,
        "scientific_classification": {
            "t1_verdict_changed": False,
            "runtime_error": False,
            "statistics_or_reporting_error": False,
            "plant_restart_failure": False,
            "control_failure_claimed": False,
            "design_failure": True,
            "t2_real_tsc_validation_required": True,
            "r3c4_authorized": False,
            "bc_dagger_or_rl_allowed": False,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    t1.r3c3.atomic_write_json(output, result)
    print(
        json.dumps(
            {
                "output": str(output),
                "output_sha256": _sha256(output),
                "original_pass_count": result["original_six_basis"][
                    "condition_pass_count"
                ],
                "original_maximum_condition": result[
                    "original_six_basis"
                ]["maximum_condition_number"],
                "feasible_scaling_count": len(feasible),
                "least_reduction_feasible": least_reduction,
                "minimum_maximum_candidate": best[1],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
