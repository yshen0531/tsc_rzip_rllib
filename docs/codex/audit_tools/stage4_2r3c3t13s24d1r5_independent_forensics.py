#!/usr/bin/env python3
"""Independent raw/controller recomputation for the D1R5 preflight."""

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
OUTPUT_NAME = "stage4_2r3c3t13s24d1r5_independent_forensics_v1.json"


def _read(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
    )


def _write(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n",
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
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _inventory(raw_dir: Path) -> dict[str, Any]:
    rows = []
    digest = hashlib.sha256()
    for path in sorted(raw_dir.glob("*.json.gz")):
        sha = _sha(path)
        size = path.stat().st_size
        digest.update(f"{path.name}\0{size}\0{sha}\n".encode())
        rows.append({"path": path.name, "bytes": size, "sha256": sha})
    return {
        "count": len(rows),
        "total_bytes": sum(int(row["bytes"]) for row in rows),
        "digest": digest.hexdigest(),
        "files": rows,
    }


def _load_context(args: argparse.Namespace) -> d1r4.Context:
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


def _source_authentication(
    ctx: d1r4.Context, cfg: Mapping[str, Any], complete_log: Path
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source = cfg["source_contract"]
    raw = _inventory(ctx.paths.raw)
    specs = d1r4._saved_specs(ctx)
    expected_names = sorted(f"{spec['experiment_id']}.json.gz" for spec in specs)
    paths = {
        "final_sha256": ctx.paths.final,
        "manifest_sha256": ctx.paths.manifest,
        "state_sha256": ctx.paths.state,
        "prospective_audit_sha256": (
            ctx.paths.analysis / "independent_server_forensics.json"
        ),
        "retrospective_audit_sha256": (
            ctx.paths.analysis
            / "retrospective_structured_failure_prefix_forensics_v1.json"
        ),
        "snapshot_audit_sha256": (
            ctx.paths.source_reference / "snapshot_audit.json"
        ),
        "source_authentication_sha256": (
            ctx.paths.source_reference / "source_authentication.json"
        ),
    }
    hashes = {key: _sha(path) for key, path in paths.items()}
    complete_log = complete_log.expanduser().resolve()
    hashes["complete_log_sha256"] = _sha(complete_log)
    manifest = _read(ctx.paths.manifest)
    retrospective = _read(paths["retrospective_audit_sha256"])
    passed = bool(
        ctx.paths.run_dir.name == source["run_name"]
        and raw["count"] == source["raw_count"]
        and raw["total_bytes"] == source["raw_total_bytes"]
        and raw["digest"] == source["raw_inventory_digest"]
        and sorted(str(row["path"]) for row in raw["files"]) == expected_names
        and all(hashes[key] == source[key] for key in hashes)
        and manifest.get("route") == source["required_route"]
        and manifest.get("raw_inventory") == raw
        and manifest.get("package_fingerprint", {}).get("package_revision")
        == source["execution_package_revision"]
        and retrospective.get("forensic_recomputation_passed")
        and retrospective.get("common_prefix_forensic_pass_count") == 9
    )
    if not passed:
        raise ValueError(cfg["routes"]["source_stop"])
    return specs, {"passed": True, "raw_inventory": raw, **hashes}


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
    return output


def _recompute_one(
    ctx: d1r4.Context,
    cfg: Mapping[str, Any],
    spec: Mapping[str, Any],
    library: Mapping[str, Any],
    bundle: Mapping[str, Any],
    selector: Mapping[str, Any],
    primary_row: Mapping[str, Any],
    index: int,
) -> dict[str, Any]:
    raw_path = ctx.paths.raw / f"{spec['experiment_id']}.json.gz"
    result = d1r4._read_raw(raw_path)
    trajectory = list(result["trajectory"])
    source_trace = list(result["controller_trace"])
    payload = _read(ctx.paths.variants / f"payload_{spec['experiment_id']}.json")
    worker = d1r2.s24.s21.s16.s9.t11.t1.r1.LocalPlantReplayWorker(
        payload,
        library,
        bundle,
        f"stage42r3c3t13s24d1r5_independent_{index:03d}",
        selector,
    )
    replay_actions_exact = True
    failure: dict[str, Any] | None = None
    error = ""
    try:
        s21_ctx = ctx.base_d1r2_ctx.base_s24_ctx.base_ctx
        controller = d1r4.CausalSplitReturnSafetySentinelController(
            worker.base_worker,
            bundle,
            d1r4._controller_spec(spec),
            trajectory[0],
            s21_ctx.base_ctx.cfg["lattice_probe"],
            s21_ctx.base_ctx.cfg["active_calibration"],
            s21_ctx.cfg["causal_model"],
            ctx.base_d1r2_ctx.cfg["schedule_contract"],
            split_cfg=ctx.cfg["split_contract"],
        )
        for step in range(20):
            try:
                action, _trace = controller.action(trajectory[step])
            except Exception:
                failure = copy.deepcopy(controller._last_failed_event)
                if step != 19:
                    raise
                break
            if step >= len(source_trace):
                raise ValueError("independent D1R5 expected D1R4 stop at step 19")
            replay_actions_exact = bool(
                replay_actions_exact
                and np.array_equal(
                    np.asarray(action, dtype=float),
                    np.asarray(source_trace[step]["action_norm_tsc"], dtype=float),
                )
            )
            controller.advance(trajectory[step + 1])
        if failure is None:
            raise ValueError("independent D1R5 did not reproduce D1R4 failure")
        recursive = cfg["recursive_contract"]
        baseline = np.asarray(failure["baseline_action_norm_tsc"], dtype=float)
        direct = np.asarray(failure["finish_action_norm_tsc"], dtype=float)
        direct_increment = float(np.max(np.abs(direct - baseline)))
        alpha = float(recursive["continuation_target_increment"]) / direct_increment
        action = baseline + alpha * (direct - baseline)
        applied = controller.actuator.apply(
            np.asarray(trajectory[19]["currents_a_tsc"], dtype=float), action
        )
        fields = tuple(map(str, applied.card15_fields))
        stored = tuple(map(str, failure["stored_center_card15_fields"]))
        target = tuple(map(str, failure["issue_target_card15_fields"]))
        previous = tuple(map(str, failure["intermediate_card15_fields"]))
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
        increment = float(np.max(np.abs(action - baseline)))
        total = float(np.max(np.abs(action)))
        turns = np.asarray(controller.turns_tsc, dtype=float)
        target_current = np.asarray(
            [
                float(d1r2.s24.s21.s16.s9._decimal_field(field)) * 1000.0 / turn
                for field, turn in zip(fields, turns)
            ],
            dtype=float,
        )
        minimum = np.asarray(controller.base.min_current, dtype=float)
        maximum = np.asarray(controller.base.max_current, dtype=float)
        utilization = d1r2.s24.s21.s16.s9._current_utilization(
            target_current, minimum, maximum
        )
        gates = {
            "replay_actions_exact": replay_actions_exact,
            "saved_failure_exact": failure == result["action_failure_event"],
            "direct_increment_exact": math.isclose(
                direct_increment,
                float(failure["incremental_normalized_action_linf"]),
                rel_tol=0.0,
                abs_tol=1e-12,
            ),
            "direct_requires_continuation": direct_increment > 0.24 + 1e-12,
            "direct_exceeds_original_cap": direct_increment > 0.25 + 1e-12,
            "continuation_increment": increment <= 0.18 + 1e-12,
            "original_increment": increment <= 0.25 + 1e-12,
            "total_action": total <= 1.0 + 1e-12,
            "current_bounds": bool(
                np.all(target_current >= minimum) and np.all(target_current <= maximum)
            ),
            "current_utilization": utilization <= 0.55 + 1e-12,
            "exact_fields": all(
                len(field) == 10
                and d1r2.s24.s21.s16.s9.format_number(
                    float(d1r2.s24.s21.s16.s9._decimal_field(field))
                )
                == field
                for field in fields
            ),
            "differs_from_center": list(fields) != list(stored),
            "differs_from_previous": list(fields) != list(previous),
            "expanded_telescope": telescope,
            "no_saturation": not any(applied.action_saturated),
            "no_current_clip": not any(applied.current_limit_clipped),
            "primary_action_exact": np.array_equal(
                action,
                np.asarray(
                    primary_row["continuation_event"]["continuation_action_norm_tsc"],
                    dtype=float,
                ),
            ),
            "primary_fields_exact": list(fields)
            == primary_row["continuation_event"]["continuation_card15_fields"],
        }
        row = {
            "source_experiment_id": spec["experiment_id"],
            "source_raw_sha256": _sha(raw_path),
            "pair_id": spec["pair_id"],
            "history_member": spec["history_member"],
            "sequence_index": int(spec["s24_sequence_index"]),
            "direct_finish_increment": direct_increment,
            "continuation_alpha": alpha,
            "continuation_increment": increment,
            "continuation_total_action": total,
            "continuation_current_utilization": utilization,
            "continuation_action_norm_tsc": action.tolist(),
            "continuation_card15_fields": list(fields),
            "gates": gates,
            "passed": bool(all(gates.values())),
        }
    except Exception as exc:
        error = repr(exc)
        row = {
            "source_experiment_id": spec["experiment_id"],
            "source_raw_sha256": _sha(raw_path),
            "pair_id": spec["pair_id"],
            "history_member": spec["history_member"],
            "sequence_index": int(spec["s24_sequence_index"]),
            "passed": False,
        }
    finally:
        worker.close()
    row["error"] = error
    return row


def run(args: argparse.Namespace) -> dict[str, Any]:
    config_path = args.config.expanduser().resolve()
    cfg = _read(config_path)
    if (
        cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or _sha(
            d1r4._project_root()
            / "docs/codex/reports/"
            "STAGE4_2R3C3T13S24D1R5_RECURSIVE_SPLIT_RETURN_PREFLIGHT_DESIGN.md"
        )
        != cfg.get("design_document_sha256")
    ):
        raise ValueError("independent D1R5 config/design mismatch")
    output_dir = args.output.expanduser().resolve()
    output_path = output_dir / OUTPUT_NAME
    if output_path.exists():
        raise ValueError("independent D1R5 output must be new")
    primary_paths = {
        "detailed": output_dir / "stage4_2r3c3t13s24d1r5_detailed_v1.json",
        "summary": output_dir / "stage4_2r3c3t13s24d1r5_summary_v1.json",
        "manifest": output_dir / "stage4_2r3c3t13s24d1r5_manifest_v1.json",
        "candidates": (
            output_dir
            / "stage4_2r3c3t13s24d1r5_candidate_real_sentinel_specs_v1.json"
        ),
    }
    if not all(path.is_file() for path in primary_paths.values()):
        raise ValueError("independent D1R5 primary output incomplete")
    detailed = _read(primary_paths["detailed"])
    summary = _read(primary_paths["summary"])
    manifest = _read(primary_paths["manifest"])
    candidates = _read(primary_paths["candidates"])
    ctx = _load_context(args)
    specs, source = _source_authentication(ctx, cfg, args.complete_log)
    primary_by_id = {
        str(row["source_experiment_id"]): row for row in detailed["rows"]
    }
    library, bundle, selector = d1r2.s24._library_bundle_selector(
        ctx.base_d1r2_ctx.base_s24_ctx
    )
    rows = [
        _recompute_one(
            ctx,
            cfg,
            spec,
            library,
            bundle,
            selector,
            primary_by_id[str(spec["experiment_id"])],
            index,
        )
        for index, spec in enumerate(specs)
    ]
    recomputed_candidates = _candidate_specs(rows, specs, cfg)
    pass_count = sum(bool(row.get("passed")) for row in rows)
    primary_consistency = bool(
        detailed.get("primary_pass")
        and summary == {key: value for key, value in detailed.items() if key != "rows"}
        and manifest.get("route") == detailed.get("route")
        and manifest.get("candidate_real_sentinel_spec_digest")
        == detailed.get("candidate_real_sentinel_spec_digest")
        == _digest(candidates)
        and candidates == recomputed_candidates
        and detailed.get("continuation_pass_count") == pass_count == 9
    )
    passed = bool(
        source["passed"]
        and len(rows) == 9
        and pass_count == 9
        and primary_consistency
        and detailed.get("route") == cfg["routes"]["pass"]
    )
    output = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "controller_revision": CONTROLLER_REVISION,
        "classification": "independent_raw_original_controller_and_decimal_recomputation",
        "source_authentication": source,
        "primary_file_hashes": {
            key: _sha(path) for key, path in primary_paths.items()
        },
        "strict_raw_count": len(rows),
        "independent_pass_count": pass_count,
        "primary_consistency_passed": primary_consistency,
        "candidate_spec_digest": _digest(recomputed_candidates),
        "minimum_direct_finish_increment": min(
            (float(row["direct_finish_increment"]) for row in rows if row.get("passed")),
            default=0.0,
        ),
        "maximum_direct_finish_increment": max(
            (float(row["direct_finish_increment"]) for row in rows if row.get("passed")),
            default=0.0,
        ),
        "maximum_continuation_increment": max(
            (float(row["continuation_increment"]) for row in rows if row.get("passed")),
            default=0.0,
        ),
        "maximum_continuation_total_action": max(
            (float(row["continuation_total_action"]) for row in rows if row.get("passed")),
            default=0.0,
        ),
        "maximum_continuation_current_utilization": max(
            (float(row["continuation_current_utilization"]) for row in rows if row.get("passed")),
            default=0.0,
        ),
        "new_raw_count": 0,
        "plant_advance_count": 0,
        "ray_gotsc_tsc_executed": False,
        "state20_used": False,
        "formal_tracking_evaluable": False,
        "real_sentinel_execution_authorized": False,
        "mpc_or_learning_authorized": False,
        "route": detailed.get("route"),
        "forensic_recomputation_passed": passed,
        "rows": rows,
    }
    _write(output_path, output)
    return output


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
    result = run(_parser().parse_args())
    print(
        json.dumps(
            {key: value for key, value in result.items() if key != "rows"},
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
