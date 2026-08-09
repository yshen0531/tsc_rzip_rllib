#!/usr/bin/env python3
"""Independent raw-bank and augmented-least-squares audit for R8R32."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r31_independent_forensics as ind31,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r31_aligned_explicit_four_coordinate_feedback_sentinel
    as r8r31,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r32_rank_regularized_schedule_generalizing_feedback_preflight
    as r8r32,
)


STAGE = r8r32.STAGE
IDENTITY = r8r32.IDENTITY
AUDIT_KIND = "rank_regularized_schedule_generalizing_preflight_independent"


def _read(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _maximum_difference(left: Any, right: Any) -> float:
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        if set(left) != set(right):
            return math.inf
        return max(
            (_maximum_difference(left[key], right[key]) for key in left), default=0.0
        )
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return math.inf
        return max(
            (_maximum_difference(a, b) for a, b in zip(left, right)), default=0.0
        )
    if isinstance(left, bool) or isinstance(right, bool):
        return 0.0 if left is right else math.inf
    if isinstance(left, str) or isinstance(right, str):
        return 0.0 if left == right else math.inf
    if left is None or right is None:
        return 0.0 if left is right else math.inf
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return abs(float(left) - float(right))
    return 0.0 if left == right else math.inf


def _without_digests(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: _without_digests(item)
            for key, item in value.items()
            if key not in {"model_digest", "residual_digest", "tube_digest", "solver"}
        }
    if isinstance(value, list):
        return [_without_digests(item) for item in value]
    return value


def _canonical_loadings(z: np.ndarray, cfg: Mapping[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    _u, singular, vh = np.linalg.svd(z, full_matrices=False)
    relative = float(cfg["model_contract"]["rank_relative_tolerance"])
    numerical_rank = (
        int(np.count_nonzero(singular > relative * singular[0]))
        if singular[0] > 0.0
        else 0
    )
    retained = int(cfg["model_contract"]["pca_rank"])
    if numerical_rank < retained:
        raise ValueError("independent R8R32 fold-local base rank below 32")
    loadings = vh[:retained].T.copy()
    for column in range(retained):
        pivot = int(np.argmax(np.abs(loadings[:, column])))
        if loadings[pivot, column] < 0.0:
            loadings[:, column] *= -1.0
    return loadings, singular


def _fit_head(
    rows: Sequence[Mapping[str, Any]],
    *,
    offset: int,
    cfg: Mapping[str, Any],
    solver: str,
) -> dict[str, Any]:
    if solver != "augmented_lstsq":
        raise ValueError("independent R8R32 requires augmented least squares")
    current = [row for row in rows if len(row["targets"]) > offset]
    base = np.asarray([row["feature"] for row in current], dtype=float).reshape((-1, 44))
    expanded = np.asarray([row["expanded"] for row in current], dtype=float).reshape((-1, 238))
    action = expanded[:, 44:62]
    q = np.asarray([row["q"] for row in current], dtype=float).reshape((-1, 4))
    target = np.asarray([row["targets"][offset] for row in current], dtype=float).reshape((-1, 5))

    base_mean = np.mean(base, axis=0)
    base_scale = np.maximum(
        np.sqrt(np.mean(np.square(base - base_mean), axis=0)),
        float(cfg["model_contract"]["base_scale_floor"]),
    )
    standardized = (base - base_mean) / base_scale
    loadings, singular = _canonical_loadings(standardized, cfg)
    scores = standardized @ loadings
    transformed = np.column_stack(
        [scores, action, *(scores * q[:, coordinate, None] for coordinate in range(4))]
    )
    if transformed.shape[1] != int(cfg["model_contract"]["transformed_dimension"]):
        raise ValueError("independent R8R32 transformed dimension changed")
    transformed_mean = np.mean(transformed, axis=0)
    transformed_scale = np.maximum(
        np.sqrt(np.mean(np.square(transformed - transformed_mean), axis=0)),
        float(cfg["model_contract"]["transformed_scale_floor"]),
    )
    standardized_transformed = (transformed - transformed_mean) / transformed_scale
    mean_x = np.mean(standardized_transformed, axis=0)
    mean_y = np.mean(target, axis=0)
    dx = standardized_transformed - mean_x
    dy = target - mean_y
    ridge = float(cfg["model_contract"]["ridge_penalty"])
    dimension = transformed.shape[1]
    augmented_x = np.vstack((dx, np.sqrt(ridge) * np.eye(dimension)))
    augmented_y = np.vstack((dy, np.zeros((dimension, 5))))
    beta = np.linalg.lstsq(augmented_x, augmented_y, rcond=None)[0]
    transformed_intercept = mean_y - mean_x @ beta

    rank = loadings.shape[1]
    affine = np.zeros((238, rank * 5 + 18), dtype=float)
    constant = np.zeros(rank * 5 + 18, dtype=float)
    base_map = loadings / base_scale[:, None]
    score_constant = -(base_mean / base_scale) @ loadings
    affine[:44, :rank] = base_map
    constant[:rank] = score_constant
    affine[44:62, rank : rank + 18] = np.eye(18)
    for coordinate in range(4):
        start = rank + 18 + coordinate * rank
        affine[62 + coordinate * 44 : 62 + (coordinate + 1) * 44, start : start + rank] = base_map
        # expanded action entries 44:48 are exactly q0:q3.
        affine[44 + coordinate, start : start + rank] = score_constant
    scaled_beta = beta / transformed_scale[:, None]
    coefficients = affine @ scaled_beta
    intercept = transformed_intercept + (
        (constant - transformed_mean) / transformed_scale
    ) @ beta
    direct = transformed_intercept + standardized_transformed @ beta
    equivalent = intercept + expanded @ coefficients
    equivalence_error = float(np.max(np.abs(direct - equivalent)))
    if (
        coefficients.shape != (238, 5)
        or intercept.shape != (5,)
        or not np.all(np.isfinite(coefficients))
        or not np.all(np.isfinite(intercept))
        or equivalence_error > 1e-12
    ):
        raise ValueError("independent R8R32 transformed/expanded equivalence failed")
    return {
        "sample_offset": offset,
        "training_row_count": len(current),
        "base_mean": base_mean,
        "base_scale": base_scale,
        "base_loadings": loadings,
        "base_singular_values": singular,
        "transformed_mean": transformed_mean,
        "transformed_scale": transformed_scale,
        "transformed_coefficients": beta,
        "intercept": intercept,
        "coefficients": coefficients,
    }


def _prediction_difference(
    primary: Mapping[str, Any],
    independent: Mapping[str, Any],
    bank: Sequence[Mapping[str, Any]],
) -> float:
    difference = 0.0
    primary_outer = {row["held_pair"]: row["model"] for row in primary["outer_models"]}
    independent_outer = {
        row["held_pair"]: row["model"] for row in independent["outer_models"]
    }
    if set(primary_outer) != set(independent_outer):
        return math.inf
    for held_pair in sorted(primary_outer):
        for trajectory in bank:
            if trajectory["pair_id"] != held_pair:
                continue
            for row in trajectory["intervals"]:
                left = r8r31.predict(primary_outer[held_pair], row)
                right = r8r31.predict(independent_outer[held_pair], row)
                difference = max(difference, float(np.max(np.abs(left - right))))
    for trajectory in bank:
        for row in trajectory["intervals"]:
            left = r8r31.predict(primary["planning_model"], row)
            right = r8r31.predict(independent["planning_model"], row)
            difference = max(difference, float(np.max(np.abs(left - right))))
    return difference


def audit(args: argparse.Namespace) -> dict[str, Any]:
    ctx = r8r32.load_context(args)
    if ctx.cfg.get("stage") != STAGE or ctx.cfg.get("identity") != IDENTITY:
        raise ValueError("independent R8R32 configuration identity changed")
    stage = ctx.paths.stage
    primary_summary_path = stage / "analysis/primary_summary.json"
    primary_detailed_path = stage / "analysis/primary_detailed.json"
    primary_model_path = stage / "model/preflight_model.json"
    primary_summary = _read(primary_summary_path)
    primary_detailed = _read(primary_detailed_path)
    primary_model = _read(primary_model_path)

    production_authentication = r8r32.authenticate_sources(ctx)
    independent_authentication = ind31._authenticate(args, ctx.source_ctx.cfg)
    bank = ind31._build_bank(args, ctx.source_ctx.cfg)
    bank_evidence = ind31._bank_evidence(bank)
    # Planning metadata is source/controller metadata, not a fitted response.  The
    # independent raw bank above remains the sole model and residual input.
    _ignored_source_bank, context_meta = r8r31.r8r23.build_bank(ctx.source_ctx.r8r23_ctx)
    if set(context_meta) != {
        (str(row["pair_id"]), str(row["history_member"])) for row in bank
    }:
        raise ValueError("independent R8R32 planning metadata coverage changed")

    independent_detailed, independent_model = r8r32.compute_from_bank(
        ctx,
        production_authentication,
        bank,
        context_meta,
        bank_evidence,
        solver="augmented_lstsq",
        fit_head_fn=_fit_head,
    )
    tolerance = float(ctx.cfg["offline_gate"]["primary_independent_absolute_tolerance"])
    bank_difference = _maximum_difference(
        primary_detailed["bank_evidence"], independent_detailed["bank_evidence"]
    )
    model_prediction_difference = _prediction_difference(
        primary_model, independent_model, bank
    )
    model_auxiliary_difference = _maximum_difference(
        _without_digests(
            {
                "pair_tube": primary_model["pair_tube"],
                "schedule_tube": primary_model["schedule_tube"],
                "combined_tube": primary_model["combined_tube"],
                "support": primary_model["support"],
                "transition_hulls": primary_model["transition_hulls"],
            }
        ),
        _without_digests(
            {
                "pair_tube": independent_model["pair_tube"],
                "schedule_tube": independent_model["schedule_tube"],
                "combined_tube": independent_model["combined_tube"],
                "support": independent_model["support"],
                "transition_hulls": independent_model["transition_hulls"],
            }
        ),
    )
    model_difference = max(model_prediction_difference, model_auxiliary_difference)
    outer_difference = _maximum_difference(
        _without_digests(primary_detailed["outer_model_evaluation"]),
        _without_digests(independent_detailed["outer_model_evaluation"]),
    )
    schedule_difference = _maximum_difference(
        _without_digests(primary_detailed["schedule_jackknife"]),
        _without_digests(independent_detailed["schedule_jackknife"]),
    )
    planning_fields = (
        "pair_planning_tube_evidence",
        "combined_tube_maximum_physical_half_width",
        "combined_tube_cap_passed",
        "model_gate_passed",
        "transition_hulls",
        "planning_evaluation",
        "fault_injection",
    )
    planning_difference = _maximum_difference(
        _without_digests({key: primary_detailed[key] for key in planning_fields}),
        _without_digests({key: independent_detailed[key] for key in planning_fields}),
    )
    route_agreement = bool(
        primary_detailed["route"] == independent_detailed["route"]
        and primary_summary["route"] == independent_detailed["route"]
    )
    outcome_agreement = bool(
        primary_detailed["integrity_gate_passed"] is True
        and independent_detailed["integrity_gate_passed"] is True
        and primary_detailed["scientific_gate_passed"]
        is independent_detailed["scientific_gate_passed"]
        and primary_summary["scientific_gate_passed"]
        is independent_detailed["scientific_gate_passed"]
    )
    result = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "audit_kind": AUDIT_KIND,
        "source_authentication": {
            "r8r31_final": production_authentication,
            "independent_transitive": independent_authentication,
            "passed": True,
        },
        "bank_evidence": bank_evidence,
        "independent_model_artifact_sha256": _digest(independent_model),
        "maximum_bank_absolute_difference": bank_difference,
        "maximum_model_absolute_difference": model_difference,
        "maximum_model_prediction_absolute_difference": model_prediction_difference,
        "maximum_model_auxiliary_absolute_difference": model_auxiliary_difference,
        "maximum_outer_absolute_difference": outer_difference,
        "maximum_schedule_absolute_difference": schedule_difference,
        "maximum_planning_absolute_difference": planning_difference,
        "primary_bank_agreement": bank_difference <= tolerance,
        "primary_model_agreement": model_difference <= tolerance,
        "primary_outer_agreement": outer_difference <= tolerance,
        "primary_schedule_agreement": schedule_difference <= tolerance,
        "primary_planning_agreement": planning_difference <= tolerance,
        "primary_route_agreement": route_agreement,
        "primary_outcome_agreement": outcome_agreement,
        "route": independent_detailed["route"],
        "scientific_gate_passed": bool(independent_detailed["scientific_gate_passed"]),
        "primary_summary_sha256": _sha(primary_summary_path),
        "primary_detailed_sha256": _sha(primary_detailed_path),
        "primary_model_sha256": _sha(primary_model_path),
        "real_tsc_executed": False,
        "plant_step_count": 0,
        "new_raw_count": 0,
    }
    result["passed"] = bool(
        result["primary_bank_agreement"]
        and result["primary_model_agreement"]
        and result["primary_outer_agreement"]
        and result["primary_schedule_agreement"]
        and result["primary_planning_agreement"]
        and result["primary_route_agreement"]
        and result["primary_outcome_agreement"]
    )
    if not result["passed"]:
        _write(stage / "analysis/independent_failure.json", result)
        raise ValueError("independent R8R32 preflight disagrees with primary")
    _write(stage / "analysis/independent.json", result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "config",
        "run-dir",
        "r8r31-run",
        "r8r23-run",
        "r8r28-run",
        "r8r22-run",
        "r8r7-run",
        "r8r12-run",
        "r8r14-run",
        "r8r15-run",
        "r8r19-run",
        "r8r20-run",
        "r8r27-run",
        "r8-run",
        "r8r1-output",
        "r8r6-run",
        "source-d1r11-run",
        "source-r2-run",
        "source-r4-run",
        "source-r6-run",
        "source-s21-run",
        "source-s23r1-output",
        "source-s24-run",
        "source-d1r9-v1",
        "source-d1r9-v2",
        "source-d1r10-run",
        "source-d1r10-audit",
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
        parser.add_argument(
            f"--{name}", dest=name.replace("-", "_"), type=Path, required=True
        )
    return parser


def main() -> None:
    args = _parser().parse_args()
    result = audit(args)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
