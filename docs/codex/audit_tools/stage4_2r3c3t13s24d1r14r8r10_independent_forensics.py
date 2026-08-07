#!/usr/bin/env python3
"""Structurally independent raw recomputation for the frozen R8R10 audit."""

from __future__ import annotations

import argparse
from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import statistics
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification as r8,
)


STAGE = "Stage4.2R3c3T13S24D1R14R8R10"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r10_replacement_scale_formal_authority_audit"
IDENTITY = "replacement_scale_formal_authority_audit_v1"
TIMES = (14, 18, 22)
SIGNS = (-1, 1)


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


def _read(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def _read_raw(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(
            stream,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _sha(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            value.update(block)
    return value.hexdigest()


def _ordered_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def _raw_fingerprint(directory: Path) -> dict[str, Any]:
    value = hashlib.sha256()
    count = size = 0
    for path in sorted(directory.glob("*.json.gz"), key=lambda item: item.name):
        item_size = path.stat().st_size
        item_sha = _sha(path)
        value.update(path.name.encode())
        value.update(b"\0")
        value.update(str(item_size).encode())
        value.update(b"\0")
        value.update(item_sha.encode())
        value.update(b"\n")
        count += 1
        size += item_size
    return {"count": count, "bytes": size, "digest": value.hexdigest()}


def _load_context(args: argparse.Namespace, cfg: Mapping[str, Any]) -> r8.Context:
    inherited = {
        name: getattr(args, name)
        for name in (
            "source_s21_run", "source_s23r1_output", "source_s24_run",
            "source_d1r9_v1", "source_d1r9_v2", "source_d1r10_run",
            "source_d1r10_audit", "source_stage42r3b_run",
            "source_stage42r3c3_run", "source_stage42r3c3_bank_dir",
            "source_stage42r3c3t1_run", "source_stage42r3c3t1_audit_dir",
            "source_stage42r3c3t3_controller_bank", "q1_run", "q2_run",
            "q1_audit", "q2_audit", "r3b_server_audit", "r3b_snapshot_checks",
        )
    }
    return r8.load_config(
        (_root() / str(cfg["source_r8_config"])).resolve(),
        source_d1r11_run=args.source_d1r11_run,
        source_r2_run=args.source_r2_run,
        source_r4_run=args.source_r4_run,
        source_r6_run=args.source_r6_run,
        run_dir=args.r8_run,
        **inherited,
    )


def _assert_hash(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha(path) != expected:
        raise ValueError(f"independent R8R10 {label} changed")


def _legacy_source(run: Path, contract: Mapping[str, Any], name: str) -> tuple[Path, list[dict[str, Any]], dict[str, Any]]:
    stage = run.expanduser().resolve() / str(contract["stage_directory"])
    for path, expected, label in (
        (stage / "analysis/final_result.json", contract["final_result_sha256"], "final"),
        (run.expanduser().resolve() / "server_independent_forensics_v1.json", contract["independent_sha256"], "independent"),
        (stage / "stage_manifest.json", contract["stage_manifest_sha256"], "manifest"),
        (stage / "stage_state.json", contract["stage_state_sha256"], "state"),
    ):
        _assert_hash(path, str(expected), f"{name} {label}")
    state = _read(stage / "stage_state.json")
    specs = _read(stage / "specs/sentinel_specs.json")
    inventory = _raw_fingerprint(stage / "raw")
    passed = bool(
        state.get("finished")
        and state.get("verdict", {}).get("route") == contract["required_route"]
        and state.get("spec_digest") == contract["spec_digest"]
        and len(specs) == int(contract["spec_count"])
        and _ordered_digest(specs) == contract["spec_digest"]
        and inventory == {
            "count": int(contract["raw_count"]),
            "bytes": int(contract["raw_bytes"]),
            "digest": str(contract["raw_digest"]),
        }
    )
    if not passed:
        raise ValueError(f"independent R8R10 {name} source mismatch")
    return stage, specs, inventory


def _r8_source(run: Path, contract: Mapping[str, Any]) -> tuple[Path, list[dict[str, Any]], dict[str, Any]]:
    stage = run.expanduser().resolve() / str(contract["stage_directory"])
    for path, expected, label in (
        (stage / "analysis/training_raw_primary.json", contract["raw_primary_sha256"], "raw primary"),
        (stage / "analysis/training_raw_independent.json", contract["raw_independent_sha256"], "raw independent"),
        (stage / "stage_manifest.json", contract["stage_manifest_sha256"], "manifest"),
        (stage / "stage_state.json", contract["stage_state_sha256"], "state"),
    ):
        _assert_hash(path, str(expected), f"R8 {label}")
    state = _read(stage / "stage_state.json")
    all_specs = _read(stage / "specs/all_specs.json")
    specs = [row for row in all_specs if str(row["partition"]) == "training"]
    inventory = _raw_fingerprint(stage / "raw/training")
    if not (
        state.get("phase_status") == "training_model_failed"
        and state.get("verdict", {}).get("route") == contract["required_route"]
        and state.get("spec_digest") == contract["spec_digest"]
        and not bool(state.get("heldout_outcomes_opened"))
        and len(all_specs) == int(contract["all_spec_count"])
        and len(specs) == int(contract["training_spec_count"])
        and _ordered_digest(all_specs) == contract["spec_digest"]
        and inventory == {
            "count": int(contract["training_raw_count"]),
            "bytes": int(contract["training_raw_bytes"]),
            "digest": str(contract["training_raw_digest"]),
        }
        and _raw_fingerprint(stage / "raw/calibration")["count"] == 0
        and _raw_fingerprint(stage / "raw/holdout")["count"] == 0
    ):
        raise ValueError("independent R8R10 R8 source mismatch")
    return stage, specs, inventory


def _row_identity(source: str, spec: Mapping[str, Any]) -> dict[str, Any] | None:
    fixed = {
        "source_bank": source,
        "experiment_id": str(spec["experiment_id"]),
        "pair_id": str(spec["pair_id"]),
        "history_member": str(spec["history_member"]),
    }
    if source == "R4":
        role = str(spec["d1r14r4_role"])
        if role == "baseline":
            return {**fixed, "role": "baseline", "action_scale": 0.0, "issue_task_step": -1, "sign": 0}
        issue = int(spec["d1r14r4_issue_task_step"])
        if role == "signed_probe" and int(spec["d1r14r4_direction_index"]) == 0 and issue in TIMES:
            return {**fixed, "role": "canonical", "action_scale": 1.0, "issue_task_step": issue, "sign": int(spec["d1r14r4_sign"])}
        return None
    if source == "R6":
        issue = int(spec["d1r14r6_issue_task_step"])
        if str(spec["d1r14r6_role"]) != "signed_probe" or int(spec["d1r14r6_direction_index"]) != 0 or issue not in TIMES:
            return None
        return {**fixed, "role": "replacement", "action_scale": 1.5, "issue_task_step": issue, "sign": int(spec["d1r14r6_sign"])}
    role = str(spec["d1r14r8_role"])
    if role == "baseline":
        return {**fixed, "role": "baseline", "action_scale": 0.0, "issue_task_step": -1, "sign": 0}
    issue = int(spec["d1r14r8_issue_task_step"])
    if role not in {"canonical", "replacement"} or int(spec["d1r14r8_direction_index"]) != 0 or issue not in TIMES:
        return None
    return {
        **fixed, "role": role, "action_scale": float(spec["d1r14r8_action_scale"]),
        "issue_task_step": issue, "sign": int(spec["d1r14r8_sign"]),
    }


def _formal_bank(ctx: r8.Context, name: str, specs: Sequence[Mapping[str, Any]], raw: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    evaluators, _ = r8.d1r11._formal_callback(ctx.d1r11_ctx, specs)
    output = []
    passed = strict = 0
    maximum = 0.0
    same_pass = same_arrival = True
    for spec in specs:
        experiment_id = str(spec["experiment_id"])
        result = _read_raw(raw / f"{experiment_id}.json.gz")
        trajectory = result.get("trajectory") or []
        if result.get("success") is not True or len(trajectory) != int(spec["horizon_steps"]) + 1:
            raise ValueError(f"independent R8R10 incomplete {name} row")
        values = np.asarray([[state["R"], state["Z"], state["Ip"]] for state in trajectory], dtype=float)
        if not np.all(np.isfinite(values)):
            raise ValueError(f"independent R8R10 nonfinite {name} row")
        strict += 1
        evaluator = evaluators[experiment_id]
        compact = evaluator.evaluate(values)
        passed += bool(compact["formal_contract_pass"])
        identity = _row_identity(name, spec)
        if identity is None:
            continue
        full = evaluator.exact_existing_metric(result, values)
        same_pass = bool(same_pass and compact["formal_contract_pass"] == full["formal_contract_pass"])
        same_arrival = bool(same_arrival and int(compact["formal_best_arrival_ms"]) == int(full["formal_best_arrival_ms"]))
        maximum = max(maximum, *(abs(float(compact[key]) - float(full[key])) for key in ("formal_minimum_signed_margin", "formal_mean_signed_margin")))
        output.append({
            **identity,
            "formal_contract_pass": bool(compact["formal_contract_pass"]),
            "formal_minimum_signed_margin": float(compact["formal_minimum_signed_margin"]),
            "formal_mean_signed_margin": float(compact["formal_mean_signed_margin"]),
            "formal_best_arrival_ms": int(compact["formal_best_arrival_ms"]),
        })
    return output, {
        "source_bank": name, "strict_raw_count": strict,
        "formal_pass_count": passed, "selected_row_count": len(output),
        "selected_pass_agreement": same_pass, "selected_arrival_agreement": same_arrival,
        "selected_maximum_margin_abs_difference": maximum,
        "selected_metric_equivalence_passed": bool(same_pass and same_arrival and maximum <= 1e-12),
    }


def _rank(row: Mapping[str, Any]) -> tuple[float, float, int, int, float]:
    return (
        float(row["formal_minimum_signed_margin"]),
        float(row["formal_mean_signed_margin"]),
        -int(row["issue_task_step"]),
        -(0 if int(row["sign"]) == -1 else 1),
        -float(row["action_scale"]),
    )


def _summarize(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[str, str], dict[str, Any]] = defaultdict(lambda: {"baseline": [], "canonical": [], "replacement": []})
    for row in rows:
        grouped[(str(row["pair_id"]), str(row["history_member"]))][str(row["role"])].append(row)
    expected = {(time, sign) for time in TIMES for sign in SIGNS}
    summaries = []
    matched_deltas = []
    for key in sorted(grouped):
        roles = grouped[key]
        canonical = {(int(row["issue_task_step"]), int(row["sign"])): row for row in roles["canonical"]}
        replacement = {(int(row["issue_task_step"]), int(row["sign"])): row for row in roles["replacement"]}
        if len(roles["baseline"]) != 1 or set(canonical) != expected or set(replacement) != expected:
            raise ValueError(f"independent R8R10 incomplete context {key}")
        base = roles["baseline"][0]
        best_c = max(canonical.values(), key=_rank)
        best_r = max(replacement.values(), key=_rank)
        c_repair = bool(not base["formal_contract_pass"] and any(item["formal_contract_pass"] for item in canonical.values()))
        r_repair = bool(not base["formal_contract_pass"] and any(item["formal_contract_pass"] for item in replacement.values()))
        matched_deltas.extend(float(replacement[item]["formal_minimum_signed_margin"]) - float(canonical[item]["formal_minimum_signed_margin"]) for item in sorted(expected))
        summaries.append({
            "pair_id": key[0], "history_member": key[1],
            "baseline_pass": bool(base["formal_contract_pass"]),
            "canonical_repair": c_repair, "replacement_repair": r_repair,
            "replacement_only_repair": bool(r_repair and not c_repair),
            "canonical_gain": float(best_c["formal_minimum_signed_margin"]) - float(base["formal_minimum_signed_margin"]),
            "replacement_gain": float(best_r["formal_minimum_signed_margin"]) - float(base["formal_minimum_signed_margin"]),
            "canonical_oracle_pass": bool(max([base, *canonical.values()], key=_rank)["formal_contract_pass"]),
            "replacement_oracle_pass": bool(max([base, *replacement.values()], key=_rank)["formal_contract_pass"]),
            "combined_oracle_pass": bool(max([base, *canonical.values(), *replacement.values()], key=_rank)["formal_contract_pass"]),
        })
    baseline = sum(item["baseline_pass"] for item in summaries)
    failed_rows = [item for item in summaries if not item["baseline_pass"]]
    cgains = [item["canonical_gain"] for item in failed_rows]
    rgains = [item["replacement_gain"] for item in failed_rows]
    stats = lambda values: (
        {"minimum": min(values), "median": statistics.median(values), "maximum": max(values)}
        if values
        else {"minimum": None, "median": None, "maximum": None}
    )
    return {
        "pair_count": len({item["pair_id"] for item in summaries}),
        "context_count": len(summaries), "selected_row_count": len(rows),
        "baseline_formal_pass_count": baseline,
        "failed_baseline_count": len(summaries) - baseline,
        "canonical_formal_pass_trajectory_count": sum(row["formal_contract_pass"] for row in rows if row["role"] == "canonical"),
        "replacement_formal_pass_trajectory_count": sum(row["formal_contract_pass"] for row in rows if row["role"] == "replacement"),
        "canonical_repaired_failed_baseline_count": sum(item["canonical_repair"] for item in summaries),
        "replacement_repaired_failed_baseline_count": sum(item["replacement_repair"] for item in summaries),
        "replacement_only_repaired_failed_baseline_count": sum(item["replacement_only_repair"] for item in summaries),
        "canonical_oracle_formal_pass_count": sum(item["canonical_oracle_pass"] for item in summaries),
        "replacement_oracle_formal_pass_count": sum(item["replacement_oracle_pass"] for item in summaries),
        "combined_oracle_formal_pass_count": sum(item["combined_oracle_pass"] for item in summaries),
        "failed_baseline_canonical_minimum_margin_gain": stats(cgains),
        "failed_baseline_replacement_minimum_margin_gain": stats(rgains),
        "matched_replacement_minus_canonical_minimum_margin": stats(matched_deltas),
        "failed_baseline_canonical_strict_improvement_count": sum(value > 1e-12 for value in cgains),
        "failed_baseline_replacement_strict_improvement_count": sum(value > 1e-12 for value in rgains),
        "matched_replacement_strictly_better_count": sum(value > 1e-12 for value in matched_deltas),
    }


def _maximum_row_difference(left: Sequence[Mapping[str, Any]], right: Sequence[Mapping[str, Any]]) -> tuple[bool, float]:
    fields = ("formal_minimum_signed_margin", "formal_mean_signed_margin")
    lmap = {str(row["experiment_id"]): row for row in left}
    rmap = {str(row["experiment_id"]): row for row in right}
    if set(lmap) != set(rmap):
        return False, float("inf")
    maximum = 0.0
    same = True
    for key in sorted(lmap):
        a, b = lmap[key], rmap[key]
        same = bool(same and all(a[name] == b[name] for name in (
            "source_bank", "pair_id", "history_member", "role", "action_scale",
            "issue_task_step", "sign", "formal_contract_pass", "formal_best_arrival_ms",
        )))
        maximum = max(maximum, *(abs(float(a[name]) - float(b[name])) for name in fields))
    return same, maximum


def run(args: argparse.Namespace) -> dict[str, Any]:
    cfg = _read(args.config.expanduser().resolve())
    design = _root() / str(cfg["design_document"])
    if cfg.get("stage") != STAGE or cfg.get("identity") != IDENTITY or _sha(design) != cfg["design_document_sha256"]:
        raise ValueError("independent R8R10 frozen config changed")
    output = args.run_dir.expanduser().resolve() / RUN_NAME
    primary_path = output / "analysis/primary_detailed.json"
    manifest_path = output / "stage_manifest.json"
    state_path = output / "stage_state.json"
    primary, manifest, state = map(_read, (primary_path, manifest_path, state_path))
    if _sha(primary_path) != manifest.get("primary_detailed_sha256") or _sha(output / "analysis/primary_summary.json") != manifest.get("primary_summary_sha256"):
        raise ValueError("independent R8R10 primary hash mismatch")
    ctx = _load_context(args, cfg)
    stage4, specs4, inv4 = _legacy_source(args.source_r4_run, cfg["source_r4"], "R4")
    stage6, specs6, inv6 = _legacy_source(args.source_r6_run, cfg["source_r6"], "R6")
    stage8, specs8, inv8 = _r8_source(args.r8_run, cfg["source_r8"])
    rows4, metrics4 = _formal_bank(ctx, "R4", specs4, stage4 / "raw")
    rows6, metrics6 = _formal_bank(ctx, "R6", specs6, stage6 / "raw")
    rows8, metrics8 = _formal_bank(ctx, "R8", specs8, stage8 / "raw/training")
    rows = [*rows4, *rows6, *rows8]
    metrics = {"R4": metrics4, "R6": metrics6, "R8": metrics8}
    summary = _summarize(rows)
    known = bool(
        metrics4["formal_pass_count"] == int(cfg["source_r4"]["formal_pass_count"])
        and metrics6["formal_pass_count"] == int(cfg["source_r6"]["formal_pass_count"])
        and metrics8["formal_pass_count"] == int(cfg["source_r8"]["training_formal_pass_count"])
    )
    equivalence = bool(
        len(rows) == int(cfg["row_contract"]["selected_row_count"])
        and all(item["selected_metric_equivalence_passed"] for item in metrics.values())
    )
    integrity = bool(
        known and equivalence
        and summary["pair_count"] == int(cfg["row_contract"]["pair_count"])
        and summary["context_count"] == int(cfg["row_contract"]["context_count"])
        and inv4["count"] == 200 and inv6["count"] == 48 and inv8["count"] == 624
    )
    gate = cfg["scientific_gate"]
    scientific = bool(
        integrity
        and summary["failed_baseline_count"] >= int(gate["minimum_failed_baseline_count"])
        and summary["replacement_repaired_failed_baseline_count"] >= int(gate["minimum_replacement_repair_count"])
        and summary["replacement_only_repaired_failed_baseline_count"] >= int(gate["minimum_replacement_only_repair_count"])
        and summary["replacement_oracle_formal_pass_count"] > summary["baseline_formal_pass_count"]
        and summary["combined_oracle_formal_pass_count"] > summary["canonical_oracle_formal_pass_count"]
    )
    route = cfg["routes"]["audit_fail" if not integrity else ("pass" if scientific else "authority_fail")]
    row_equal, maximum_row_difference = _maximum_row_difference(rows, primary["formal_rows"])
    primary_summary = {key: value for key, value in primary["authority"].items() if key not in {"context_rows", "matched_scale_rows", "strata"}}
    numerical = bool(row_equal and maximum_row_difference <= 1e-12 and summary == primary_summary and metrics == primary["source_formal_reproduction"])
    outcome = bool(
        integrity == primary.get("integrity_gate_passed")
        and scientific == primary.get("scientific_gate_passed")
        and route == primary.get("route") == state.get("verdict", {}).get("route")
        and scientific == state.get("verdict", {}).get("passed")
    )
    report = {
        "schema_version": 1, "stage": STAGE,
        "phase": "independent_raw_formal_authority_recomputation",
        "source_authentication": {"R4": True, "R6": True, "R8": True},
        "source_inventories": {"R4": inv4, "R6": inv6, "R8": inv8},
        "source_formal_reproduction": metrics,
        "known_source_aggregate_reproduction_passed": known,
        "formal_metric_equivalence_passed": equivalence,
        "authority": summary,
        "maximum_primary_margin_abs_difference": maximum_row_difference,
        "primary_numerical_agreement": numerical,
        "primary_outcome_agreement": outcome,
        "primary_route_agreement": route == primary.get("route"),
        "integrity_gate_passed": integrity,
        "scientific_gate_passed": scientific,
        "route": route,
        "real_tsc_executed": False, "new_raw_count": 0,
        "passed": bool(numerical and outcome),
    }
    _write(output / "analysis/independent.json", report)
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "config", "run-dir", "r8-run", "source-d1r11-run", "source-r2-run",
        "source-r4-run", "source-r6-run", "source-s21-run", "source-s23r1-output",
        "source-s24-run", "source-d1r9-v1", "source-d1r9-v2", "source-d1r10-run",
        "source-d1r10-audit", "source-stage42r3b-run", "source-stage42r3c3-run",
        "source-stage42r3c3-bank-dir", "source-stage42r3c3t1-run",
        "source-stage42r3c3t1-audit-dir", "source-stage42r3c3t3-controller-bank",
        "q1-run", "q2-run", "q1-audit", "q2-audit", "r3b-server-audit",
        "r3b-snapshot-checks",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    return parser


def main() -> None:
    print(json.dumps(run(_parser().parse_args()), indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
