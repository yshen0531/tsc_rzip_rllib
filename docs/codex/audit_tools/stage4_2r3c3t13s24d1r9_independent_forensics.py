#!/usr/bin/env python3
"""Independent zero-TSC recomputation for D1R9."""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import itertools
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r7_temporal_basis_substitution_preflight as d1r7,
)


STAGE = "Stage4.2R3c3T13S24D1R9"
IDENTITY = "central_row_replacement_preflight_v1"


def _sha(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
    )


def _raw(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(
            stream,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )


def _write(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _inventory(paths: Iterable[Path]) -> dict[str, Any]:
    digest = hashlib.sha256()
    count = total = 0
    for path in sorted(paths, key=lambda value: value.name):
        size = path.stat().st_size
        sha = _sha(path)
        digest.update(f"{path.name}\0{size}\0{sha}\n".encode())
        count += 1
        total += size
    return {"count": count, "total_bytes": total, "digest": digest.hexdigest()}


def _record(
    evidence: dict[str, dict[str, Any]], campaign: str, result: Mapping[str, Any]
) -> None:
    vector = result["spec"].get("s24_requested_matrix_row")
    if vector is None:
        return
    values = np.asarray(vector, dtype=float)
    if values.shape != (16,) or not np.all(np.isfinite(values)):
        raise ValueError("independent D1R9 invalid requested row")
    key = _digest(values.tolist())
    row = evidence.setdefault(
        key,
        {
            "row": values.tolist(),
            "success": 0,
            "failure": 0,
            "campaigns": defaultdict(Counter),
        },
    )
    outcome = "success" if result.get("success") else "failure"
    row[outcome] += 1
    row["campaigns"][campaign][outcome] += 1


def _classify(evidence: Mapping[str, Mapping[str, Any]], row: np.ndarray) -> dict[str, Any]:
    key = _digest(row.tolist())
    value = evidence.get(key, {})
    success = int(value.get("success", 0))
    failure = int(value.get("failure", 0))
    return {
        "digest": key,
        "classification": "contradicted" if failure else "exact_safe" if success else "unknown",
        "success_count": success,
        "failure_count": failure,
        "campaign_counts": {
            campaign: dict(counts)
            for campaign, counts in sorted(value.get("campaigns", {}).items())
        },
    }


def _matrix(primary: np.ndarray, indices: Sequence[int]) -> np.ndarray:
    return np.vstack([primary, *[-primary[int(index)] for index in indices]])


def _candidate_specs(
    cfg: Mapping[str, Any],
    base: Mapping[str, Any],
    contexts: Mapping[tuple[str, str], Mapping[str, Any]],
    matrix: np.ndarray,
) -> dict[str, Any]:
    contract = cfg["candidate_spec_contract"]
    issue = list(map(int, base["matrix_contract"]["issue_task_steps"]))
    cancel = list(map(int, base["matrix_contract"]["cancel_task_steps"]))
    specs = []
    for key in sorted(contexts):
        source = contexts[key]
        for row_index in map(int, contract["row_indices"]):
            row = matrix[row_index]
            schedule = {}
            for slot, (start, stop) in enumerate(zip(issue, cancel)):
                coordinate = row[4 * slot : 4 * slot + 4].tolist()
                schedule[str(start)] = coordinate
                schedule[str(stop)] = (-row[4 * slot : 4 * slot + 4]).tolist()
            seed = {
                "stage": contract["stage"],
                "campaign_identity": contract["campaign_identity"],
                "pair_id": key[0],
                "history_member": key[1],
                "row_index": row_index,
                "requested_matrix_digest": cfg["selection_contract"]["requested_matrix_digest"],
            }
            experiment_id = "s42r3c3t13s24d1r10_" + _digest(seed)[:20]
            spec = copy.deepcopy(dict(source))
            spec.update(
                {
                    "stage": contract["stage"],
                    "experiment_id": experiment_id,
                    "environment_variant": "stage4_2r3c3t13s24d1r10_"
                    + experiment_id.rsplit("_", 1)[-1],
                    "kind": "stage4_2r3c3t13s24d1r10_exact_row_completion_safety_sentinel",
                    "phase": "prospective_exact_row_completion_safety_sentinel",
                    "campaign_identity": contract["campaign_identity"],
                    "controller_revision": contract["controller_revision"],
                    "probe_primitive_revision": contract["probe_primitive_revision"],
                    "s24_sequence_index": row_index,
                    "s24_requested_matrix_row": row.tolist(),
                    "s24_requested_action_by_task_step": schedule,
                    "s24_schedule_digest": cfg["selection_contract"]["requested_matrix_digest"],
                    "fresh_tsc_process_required": True,
                    "fresh_controller_required": True,
                    "development_set_only": True,
                    "identification_only": True,
                    "probe_trajectory_allowed_in_expert_dataset": False,
                    "pair_or_history_label_available_to_controller": False,
                    "partition_label_available_to_controller": False,
                    "source_action_available_to_controller": False,
                    "source_coil_current_available_to_controller": False,
                    "source_result_available_to_controller": False,
                    "hidden_wire_current_available_to_controller": False,
                }
            )
            specs.append(spec)
    specs.sort(key=lambda row: str(row["experiment_id"]))
    return {
        "schema_version": 1,
        "stage": contract["stage"],
        "campaign_identity": contract["campaign_identity"],
        "requested_matrix_digest": cfg["selection_contract"]["requested_matrix_digest"],
        "candidate_row_indices": contract["row_indices"],
        "selected_spec_count": len(specs),
        "ordered_spec_digest": _digest(specs),
        "source_outcomes_available_to_controller": False,
        "pair_history_partition_label_available_to_controller": False,
        "spec_rows": specs,
    }


def recompute(config_path: Path, project: Path, primary_dir: Path) -> dict[str, Any]:
    project = project.resolve()
    cfg = _json(config_path.resolve())
    if (
        cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or _sha(project / cfg["design_document"]) != cfg["design_document_sha256"]
        or _sha(project / cfg["base_d1r7_config"]) != cfg["base_d1r7_config_sha256"]
    ):
        raise ValueError("independent D1R9 config identity changed")
    base = _json(project / cfg["base_d1r7_config"])
    d1r7._validate_config(base, project / cfg["base_d1r7_config"])
    source = cfg["source_contract"]
    d1r7_dir = project / source["d1r7_output_relpath"]
    d1r7_files = {
        "stage4_2r3c3t13s24d1r7_candidate_specs_v1.json": source["d1r7_candidate_sha256"],
        "stage4_2r3c3t13s24d1r7_temporal_basis_substitution_preflight_v1.json": source["d1r7_detailed_sha256"],
        "stage4_2r3c3t13s24d1r7_summary_v1.json": source["d1r7_summary_sha256"],
        "stage4_2r3c3t13s24d1r7_manifest_v1.json": source["d1r7_manifest_sha256"],
    }
    if any(_sha(d1r7_dir / name) != expected for name, expected in d1r7_files.items()):
        raise ValueError("independent D1R9 D1R7 source changed")
    s24 = d1r7._authenticate_s24(project, base)
    d1r2, _ = d1r7._authenticate_d1r2(project, base)
    d1r6 = d1r7._authenticate_d1r6(project, base)
    d1r8_stage = project / source["d1r8_stage_relpath"]
    d1r8_paths = {
        "specs": d1r8_stage / "specs" / "sentinel_specs.json",
        "manifest": d1r8_stage / "stage_manifest.json",
        "state": d1r8_stage / "stage_state.json",
        "final": d1r8_stage / "final_result.json",
        "independent": d1r8_stage / "analysis" / "independent_server_raw_forensics.json",
        "reporting_hotfix": d1r8_stage / "analysis" / "independent_server_raw_forensics_v2_reporting_hotfix.json",
    }
    if any(
        _sha(path) != source[f"d1r8_{name}_sha256"]
        for name, path in d1r8_paths.items()
    ):
        raise ValueError("independent D1R9 D1R8 source hash changed")
    d1r8_specs_value = _json(d1r8_paths["specs"])
    d1r8_specs = (
        d1r8_specs_value
        if isinstance(d1r8_specs_value, list)
        else d1r8_specs_value.get("spec_rows") or d1r8_specs_value.get("specs")
    )
    spec_by_id = {str(row["experiment_id"]): row for row in d1r8_specs}
    inv = _inventory((d1r8_stage / "raw").glob("*.json.gz"))
    if (
        inv["count"] != source["d1r8_raw_count"]
        or inv["total_bytes"] != source["d1r8_raw_total_bytes"]
        or inv["digest"] != source["d1r8_raw_inventory_digest"]
    ):
        raise ValueError("independent D1R9 D1R8 inventory changed")
    evidence: dict[str, dict[str, Any]] = {}
    raw_dirs = {
        "S24": project / base["source_contract"]["s24_stage_relpath"] / "raw",
        "D1R2": project / base["source_contract"]["d1r2_stage_relpath"] / "raw",
        "D1R8": d1r8_stage / "raw",
    }
    contexts: dict[tuple[str, str], dict[str, Any]] = {}
    d1r8_success = d1r8_failure = 0
    for campaign, raw_dir in raw_dirs.items():
        for path in sorted(raw_dir.glob("*.json.gz")):
            result = _raw(path)
            if campaign == "D1R8":
                spec = spec_by_id.get(str(result.get("experiment_id")))
                if spec is None or result.get("spec") != spec or not result.get("completed"):
                    raise ValueError("independent D1R9 D1R8 raw identity changed")
                d1r8_success += bool(result.get("success"))
                d1r8_failure += not bool(result.get("success"))
                key = (str(spec["pair_id"]), str(spec["history_member"]))
                prior = contexts.get(key)
                if prior is None or str(spec["experiment_id"]) < str(prior["experiment_id"]):
                    contexts[key] = spec
            _record(evidence, campaign, result)
    if d1r8_success != 105 or d1r8_failure != 3 or len(contexts) != 18:
        raise ValueError("independent D1R9 D1R8 outcome changed")
    source_matrix = d1r7.requested_matrix(base)
    primary = source_matrix[:16]
    primary_class = [_classify(evidence, row) for row in primary]
    negative_class = [_classify(evidence, -row) for row in primary]
    current = set(cfg["selection_contract"]["source_ordered_central_primary_indices"])
    eligible = []
    for indices in itertools.combinations(range(16), 8):
        if any(negative_class[index]["classification"] == "contradicted" for index in indices):
            continue
        matrix = _matrix(primary, indices)
        metrics = d1r7.matrix_metrics(matrix, base)
        if not (metrics["global_pass"] and metrics["slot_pass_count"] == 4 and metrics["late_novelty_pass"]):
            continue
        objective = (
            sum(negative_class[index]["classification"] == "unknown" for index in indices),
            len(set(indices) ^ current) // 2,
            max(float(row["normalized_condition"]) for row in metrics["slot_rows"]),
            -float(metrics["minimum_late_column_residual"]),
            tuple(indices),
        )
        eligible.append((objective, tuple(indices)))
    eligible.sort()
    selected_sorted = eligible[0][1]
    source_ordered = cfg["selection_contract"]["source_ordered_central_primary_indices"]
    removed = [index for index in source_ordered if index not in selected_sorted]
    added = [index for index in selected_sorted if index not in current]
    if len(removed) != 1 or len(added) != 1:
        raise ValueError("independent D1R9 replacement cardinality changed")
    selected_ordered = [added[0] if index == removed[0] else index for index in source_ordered]
    matrix = _matrix(primary, selected_ordered)
    matrix_evidence = [_classify(evidence, row) for row in matrix]
    unknown = [index for index, row in enumerate(matrix_evidence) if row["classification"] == "unknown"]
    contradicted = [index for index, row in enumerate(matrix_evidence) if row["classification"] == "contradicted"]
    replay_cfg = copy.deepcopy(base)
    replay_cfg["matrix_contract"]["central_sign_primary_indices"] = selected_ordered
    replay_cfg["matrix_contract"]["requested_matrix_digest"] = _digest(matrix.tolist())
    static, _ = d1r7._authenticate_d1r1_and_static_replay(project, replay_cfg, matrix)
    candidate = _candidate_specs(cfg, base, contexts, matrix)
    primary_candidate = _json(primary_dir / "stage4_2r3c3t13s24d1r9_d1r10_candidate_specs_v1.json")
    primary_detailed = _json(primary_dir / "stage4_2r3c3t13s24d1r9_central_row_replacement_preflight_v1.json")
    primary_summary = _json(primary_dir / "stage4_2r3c3t13s24d1r9_summary_v1.json")
    primary_match = bool(
        candidate == primary_candidate
        and primary_detailed["selection"]["requested_matrix"] == matrix.tolist()
        and primary_detailed["selection"]["primary_evidence"] == primary_class
        and primary_detailed["selection"]["negative_primary_evidence"] == negative_class
        and primary_detailed["static_replay"]["counts"] == static["counts"]
        and primary_summary["candidate_spec_digest"] == candidate["ordered_spec_digest"]
    )
    passed = bool(
        s24["strict_parse_count"] == 600
        and d1r2["strict_parse_count"] == 54
        and d1r6["raw_inventory"]["count"] == 9
        and len(eligible) == 495
        and list(selected_sorted) == cfg["selection_contract"]["selected_sorted_central_primary_indices"]
        and selected_ordered == cfg["selection_contract"]["selected_ordered_central_primary_indices"]
        and _digest(matrix.tolist()) == cfg["selection_contract"]["requested_matrix_digest"]
        and unknown == cfg["candidate_spec_contract"]["row_indices"]
        and not contradicted
        and static["passed"]
        and candidate["selected_spec_count"] == 126
        and primary_match
    )
    return {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "classification": "independent_raw_evidence_enumeration_static_candidate_recomputation",
        "source_raw_counts": {"s24": 600, "d1r2": 54, "d1r6": 9, "d1r8": 108},
        "d1r8_inventory": inv,
        "primary_evidence": primary_class,
        "negative_primary_evidence": negative_class,
        "combination_count": math.comb(16, 8),
        "eligible_combination_count": len(eligible),
        "selected_sorted_central_primary_indices": list(selected_sorted),
        "selected_ordered_central_primary_indices": selected_ordered,
        "requested_matrix_digest": _digest(matrix.tolist()),
        "unknown_matrix_row_indices": unknown,
        "contradicted_matrix_row_indices": contradicted,
        "static_counts": static["counts"],
        "candidate_spec_count": candidate["selected_spec_count"],
        "candidate_spec_digest": candidate["ordered_spec_digest"],
        "primary_output_exact_match": primary_match,
        "new_raw_or_tsc_count": 0,
        "passed": passed,
        "route": cfg["routes"]["pass"] if passed else cfg["routes"]["fail"],
    }


def run(config: Path, project: Path, primary_dir: Path, output: Path) -> dict[str, Any]:
    output = output.resolve()
    if output.exists():
        raise ValueError("independent D1R9 output must be new")
    result = recompute(config, project, primary_dir.resolve())
    _write(output, result)
    manifest_path = primary_dir.resolve() / "stage4_2r3c3t13s24d1r9_manifest_v1.json"
    if manifest_path.exists():
        raise ValueError("D1R9 manifest must be new")
    names = [
        "stage4_2r3c3t13s24d1r9_d1r10_candidate_specs_v1.json",
        "stage4_2r3c3t13s24d1r9_central_row_replacement_preflight_v1.json",
        "stage4_2r3c3t13s24d1r9_summary_v1.json",
        output.name,
    ]
    files = {name: _sha(primary_dir.resolve() / name) for name in names}
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "passed": result["passed"],
        "route": result["route"],
        "output_files": files,
        "new_raw_files_created": 0,
        "ray_gotsc_tsc_controller_or_plant_executed": False,
        "pass_authorizes_d1r10_design_only": True,
        "pass_authorizes_d1r10_execution": False,
        "mpc_or_learning_authorized": False,
    }
    _write(manifest_path, manifest)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--primary-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    result = run(args.config, args.project, args.primary_dir, args.output)
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
