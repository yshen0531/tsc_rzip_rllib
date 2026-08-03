#!/usr/bin/env python3
"""Primary zero-TSC D1R9 central-row replacement preflight."""

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
PACKAGE_REVISION = "r42r3c3t13s24d1r9_central_row_replacement_preflight_v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


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


def _read_raw(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(
            stream,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )


def _inventory(paths: Iterable[Path]) -> dict[str, Any]:
    rows = []
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda value: value.name):
        size = path.stat().st_size
        sha = _sha256(path)
        digest.update(f"{path.name}\0{size}\0{sha}\n".encode())
        rows.append({"path": path.name, "bytes": size, "sha256": sha})
    return {
        "count": len(rows),
        "total_bytes": sum(int(row["bytes"]) for row in rows),
        "digest": digest.hexdigest(),
        "files": rows,
    }


def _package_path(project: Path, relative: str) -> Path:
    project = project.resolve()
    path = (project / relative).resolve()
    if path != project and project not in path.parents:
        raise ValueError("D1R9 package path is outside project")
    return path


def _validate_config(cfg: Mapping[str, Any], config_path: Path) -> None:
    root = config_path.resolve().parents[1]
    if (
        cfg.get("schema_version") != 1
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("package_revision") != PACKAGE_REVISION
        or _sha256(_package_path(root, str(cfg["design_document"])))
        != cfg.get("design_document_sha256")
        or _sha256(_package_path(root, str(cfg["base_d1r7_config"])))
        != cfg.get("base_d1r7_config_sha256")
    ):
        raise ValueError("D1R9 identity or frozen source changed")
    evidence = cfg["evidence_contract"]
    if (
        evidence["schedule_identity"]
        != "sha256_exact_16_value_requested_matrix_row"
        or evidence["primary_exact_safe_indices"]
        != [0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14]
        or evidence["primary_unknown_indices"] != [3, 7, 11, 15]
        or evidence["primary_contradicted_indices"] != []
        or evidence["negative_exact_safe_indices"] != [0, 1, 4, 5, 8]
        or evidence["negative_unknown_indices"] != [3, 7, 9, 11, 12, 13, 15]
        or evidence["negative_contradicted_indices"] != [2, 6, 10, 14]
    ):
        raise ValueError("D1R9 frozen evidence classes changed")
    selection = cfg["selection_contract"]
    if (
        int(selection["combination_count"]) != math.comb(16, 8)
        or int(selection["eligible_combination_count"]) != 495
        or selection["source_ordered_central_primary_indices"]
        != [0, 4, 1, 5, 3, 7, 6, 8]
        or selection["selected_sorted_central_primary_indices"]
        != [0, 1, 3, 4, 5, 7, 8, 9]
        or selection["selected_ordered_central_primary_indices"]
        != [0, 4, 1, 5, 3, 7, 9, 8]
        or selection["changed_matrix_row_indices"] != [22]
        or selection["requested_matrix_digest"]
        != "106dfed384febb16019e4d39ce1da03762ad9dbb5e8e69120a4a9d9acdebc30b"
    ):
        raise ValueError("D1R9 selection contract changed")
    candidate = cfg["candidate_spec_contract"]
    if (
        candidate["row_indices"] != [3, 7, 11, 15, 20, 21, 22]
        or int(candidate["expected_specs"]) != 126
        or int(candidate["expected_contexts"]) != 18
        or candidate["expected_horizon_counts"] != {"35": 56, "37": 70}
    ):
        raise ValueError("D1R9 candidate contract changed")
    execution = cfg["execution_contract"]
    if (
        int(execution["accepted_runs_required"]) != 2
        or not bool(execution["byte_identical_outputs_required"])
        or int(execution["new_raw_files_allowed"]) != 0
        or any(
            bool(execution[key])
            for key in (
                "ray_allowed",
                "gotsc_allowed",
                "tsc_allowed",
                "controller_or_plant_step_allowed",
                "source_raw_copy_or_modification_allowed",
            )
        )
    ):
        raise ValueError("D1R9 zero-TSC execution contract changed")
    scope = cfg["scientific_scope"]
    if (
        not bool(scope["offline_preflight_only"])
        or not bool(scope["pass_authorizes_d1r10_design_only"])
        or bool(scope["pass_authorizes_d1r10_execution"])
        or bool(scope["pass_authorizes_full_identification_campaign"])
        or bool(scope["pass_authorizes_mpc"])
        or bool(scope["probe_trajectories_allowed_in_expert_dataset"])
        or bool(scope["bc_dagger_or_rl_allowed"])
    ):
        raise ValueError("D1R9 scientific scope changed")


def load_config(config_path: Path, project: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    config_path = config_path.resolve()
    project = project.resolve()
    cfg = _read_json(config_path)
    _validate_config(cfg, config_path)
    base_path = _package_path(project, str(cfg["base_d1r7_config"]))
    if _sha256(base_path) != cfg["base_d1r7_config_sha256"]:
        raise ValueError("D1R9 deployed base D1R7 config changed")
    base_cfg = _read_json(base_path)
    d1r7._validate_config(base_cfg, base_path)
    return cfg, base_cfg


def _assert_hash(path: Path, expected: str, label: str) -> str:
    if not path.is_file():
        raise ValueError(f"D1R9 {label} missing")
    actual = _sha256(path)
    if actual != expected:
        raise ValueError(f"D1R9 {label} hash changed")
    return actual


def _authenticate_d1r7(project: Path, cfg: Mapping[str, Any]) -> dict[str, Any]:
    source = cfg["source_contract"]
    root = project / source["d1r7_output_relpath"]
    files = {
        "candidate": (
            "stage4_2r3c3t13s24d1r7_candidate_specs_v1.json",
            source["d1r7_candidate_sha256"],
        ),
        "detailed": (
            "stage4_2r3c3t13s24d1r7_temporal_basis_substitution_preflight_v1.json",
            source["d1r7_detailed_sha256"],
        ),
        "summary": (
            "stage4_2r3c3t13s24d1r7_summary_v1.json",
            source["d1r7_summary_sha256"],
        ),
        "manifest": (
            "stage4_2r3c3t13s24d1r7_manifest_v1.json",
            source["d1r7_manifest_sha256"],
        ),
    }
    hashes = {
        key: _assert_hash(root / name, expected, f"D1R7 {key}")
        for key, (name, expected) in files.items()
    }
    candidate = _read_json(root / files["candidate"][0])
    manifest = _read_json(root / files["manifest"][0])
    specs = list(candidate.get("spec_rows") or [])
    if (
        manifest.get("route") != source["d1r7_route"]
        or not bool(manifest.get("passed"))
        or len(specs) != int(source["d1r7_candidate_count"])
        or candidate.get("ordered_spec_digest") != source["d1r7_candidate_digest"]
        or _digest(specs) != source["d1r7_candidate_digest"]
    ):
        raise ValueError("D1R9 D1R7 accepted result changed")
    return {"hashes": hashes, "candidate_count": len(specs), "passed": True}


def _spec_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [dict(row) for row in value]
    if isinstance(value, Mapping):
        for key in ("spec_rows", "specs"):
            if isinstance(value.get(key), list):
                return [dict(row) for row in value[key]]
    raise ValueError("D1R9 spec container changed")


def _authenticate_d1r8(project: Path, cfg: Mapping[str, Any]) -> dict[str, Any]:
    source = cfg["source_contract"]
    stage = project / source["d1r8_stage_relpath"]
    paths = {
        "specs": stage / "specs" / "sentinel_specs.json",
        "manifest": stage / "stage_manifest.json",
        "state": stage / "stage_state.json",
        "final": stage / "final_result.json",
        "independent": stage / "analysis" / "independent_server_raw_forensics.json",
        "reporting_hotfix": (
            stage / "analysis" / "independent_server_raw_forensics_v2_reporting_hotfix.json"
        ),
    }
    hashes = {
        key: _assert_hash(path, source[f"d1r8_{key}_sha256"], f"D1R8 {key}")
        for key, path in paths.items()
    }
    specs = _spec_list(_read_json(paths["specs"]))
    spec_by_id = {str(row["experiment_id"]): row for row in specs}
    inventory = _inventory((stage / "raw").glob("*.json.gz"))
    manifest = _read_json(paths["manifest"])
    state = _read_json(paths["state"])
    final = _read_json(paths["final"])
    hotfix = _read_json(paths["reporting_hotfix"])
    success = failures = strict = 0
    failure_sequences: Counter[int] = Counter()
    for path in sorted((stage / "raw").glob("*.json.gz")):
        result = _read_raw(path)
        experiment_id = str(result.get("experiment_id"))
        spec = spec_by_id.get(experiment_id)
        if (
            spec is None
            or result.get("spec") != spec
            or not bool(result.get("completed"))
            or result.get("stage") != "Stage4.2R3c3T13S24D1R8"
        ):
            raise ValueError("D1R9 D1R8 raw identity changed")
        strict += 1
        if result.get("success"):
            success += 1
        else:
            event = result.get("action_failure_event") or {}
            if (
                result.get("failure_class") != "structured_action_schedule_gate"
                or event.get("event") != "sequential_cancel"
                or bool(event.get("passed"))
            ):
                raise ValueError("D1R9 D1R8 failure class changed")
            failures += 1
            failure_sequences[int(spec["s24_sequence_index"])] += 1
    expected_failures = Counter(
        {
            int(key): int(value)
            for key, value in source["d1r8_failure_sequence_counts"].items()
        }
    )
    if (
        len(specs) != int(source["d1r8_raw_count"])
        or len(spec_by_id) != len(specs)
        or strict != len(specs)
        or inventory["count"] != int(source["d1r8_raw_count"])
        or inventory["total_bytes"] != int(source["d1r8_raw_total_bytes"])
        or inventory["digest"] != source["d1r8_raw_inventory_digest"]
        or success != int(source["d1r8_success_count"])
        or failures != int(source["d1r8_structured_failure_count"])
        or failure_sequences != expected_failures
        or manifest.get("route") != source["d1r8_route"]
        or final.get("route") != source["d1r8_route"]
        or state.get("verdict", {}).get("route") != source["d1r8_route"]
        or int(hotfix.get("initial_restart_exact_count", -1)) != 108
        or int(hotfix.get("causal_trace_prefix_pass_count", -1)) != 108
    ):
        raise ValueError("D1R9 D1R8 result changed")
    contexts: dict[tuple[str, str], dict[str, Any]] = {}
    for spec in specs:
        key = (str(spec["pair_id"]), str(spec["history_member"]))
        prior = contexts.get(key)
        if prior is None or str(spec["experiment_id"]) < str(prior["experiment_id"]):
            contexts[key] = spec
    if len(contexts) != int(cfg["candidate_spec_contract"]["expected_contexts"]):
        raise ValueError("D1R9 D1R8 context coverage changed")
    return {
        "stage_dir": str(stage),
        "hashes": hashes,
        "inventory": inventory,
        "strict_parse_count": strict,
        "success_count": success,
        "structured_failure_count": failures,
        "failure_sequence_counts": {
            str(key): failure_sequences[key] for key in sorted(failure_sequences)
        },
        "contexts": contexts,
    }


def _evidence_add(
    evidence: dict[str, dict[str, Any]],
    campaign: str,
    result: Mapping[str, Any],
) -> None:
    spec = result["spec"]
    vector = spec.get("s24_requested_matrix_row")
    if vector is None:
        return
    values = np.asarray(vector, dtype=float)
    if values.shape != (16,) or not np.all(np.isfinite(values)):
        raise ValueError("D1R9 source requested row invalid")
    key = _digest(values.tolist())
    row = evidence.setdefault(
        key,
        {
            "requested_row": values.tolist(),
            "success_count": 0,
            "failure_count": 0,
            "campaign_counts": defaultdict(Counter),
        },
    )
    if row["requested_row"] != values.tolist():
        raise ValueError("D1R9 requested-row digest collision")
    outcome = "success" if result.get("success") else "failure"
    row[f"{outcome}_count"] += 1
    row["campaign_counts"][campaign][outcome] += 1


def _collect_evidence(
    project: Path, base_cfg: Mapping[str, Any], d1r8_auth: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    source = base_cfg["source_contract"]
    raw_dirs = {
        "S24": project / source["s24_stage_relpath"] / "raw",
        "D1R2": project / source["d1r2_stage_relpath"] / "raw",
        "D1R8": Path(str(d1r8_auth["stage_dir"])) / "raw",
    }
    evidence: dict[str, dict[str, Any]] = {}
    for campaign, raw_dir in raw_dirs.items():
        for path in sorted(raw_dir.glob("*.json.gz")):
            _evidence_add(evidence, campaign, _read_raw(path))
    output = {}
    for key, row in evidence.items():
        output[key] = {
            **{name: value for name, value in row.items() if name != "campaign_counts"},
            "campaign_counts": {
                campaign: dict(counts)
                for campaign, counts in sorted(row["campaign_counts"].items())
            },
        }
    return output


def _classification(
    evidence: Mapping[str, Mapping[str, Any]], row: Sequence[float]
) -> dict[str, Any]:
    key = _digest(list(map(float, row)))
    found = evidence.get(key)
    success = int(found.get("success_count", 0)) if found else 0
    failure = int(found.get("failure_count", 0)) if found else 0
    classification = (
        "contradicted" if failure else "exact_safe" if success else "unknown"
    )
    return {
        "digest": key,
        "classification": classification,
        "success_count": success,
        "failure_count": failure,
        "campaign_counts": copy.deepcopy(found.get("campaign_counts", {})) if found else {},
    }


def _candidate_matrix(
    primary: np.ndarray, ordered_indices: Sequence[int]
) -> np.ndarray:
    matrix = np.vstack([primary, *[-primary[int(index)] for index in ordered_indices]])
    if matrix.shape != (24, 16):
        raise ValueError("D1R9 candidate matrix shape changed")
    return matrix


def _selection(
    cfg: Mapping[str, Any],
    base_cfg: Mapping[str, Any],
    evidence: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    source_matrix = d1r7.requested_matrix(base_cfg)
    primary = source_matrix[:16]
    primary_rows = [_classification(evidence, row) for row in primary]
    negative_rows = [_classification(evidence, -row) for row in primary]
    expected = cfg["evidence_contract"]
    classes = lambda rows, name: [
        index for index, row in enumerate(rows) if row["classification"] == name
    ]
    if (
        classes(primary_rows, "exact_safe") != expected["primary_exact_safe_indices"]
        or classes(primary_rows, "unknown") != expected["primary_unknown_indices"]
        or classes(primary_rows, "contradicted")
        != expected["primary_contradicted_indices"]
        or classes(negative_rows, "exact_safe")
        != expected["negative_exact_safe_indices"]
        or classes(negative_rows, "unknown") != expected["negative_unknown_indices"]
        or classes(negative_rows, "contradicted")
        != expected["negative_contradicted_indices"]
    ):
        raise ValueError("D1R9 exact-vector evidence classification changed")
    selection = cfg["selection_contract"]
    source_set = set(selection["source_ordered_central_primary_indices"])
    eligible = []
    for indices in itertools.combinations(range(16), 8):
        if any(negative_rows[index]["classification"] == "contradicted" for index in indices):
            continue
        matrix = _candidate_matrix(primary, indices)
        metrics = d1r7.matrix_metrics(matrix, base_cfg)
        if not (
            metrics["global_pass"]
            and int(metrics["slot_pass_count"]) == 4
            and metrics["late_novelty_pass"]
        ):
            continue
        unknown = sum(
            negative_rows[index]["classification"] == "unknown" for index in indices
        )
        replacements = len(set(indices) ^ source_set) // 2
        maximum_slot = max(
            float(row["normalized_condition"]) for row in metrics["slot_rows"]
        )
        objective = (
            unknown,
            replacements,
            maximum_slot,
            -float(metrics["minimum_late_column_residual"]),
            tuple(indices),
        )
        eligible.append((objective, tuple(indices), metrics))
    eligible.sort(key=lambda row: row[0])
    if len(eligible) != int(selection["eligible_combination_count"]):
        raise ValueError("D1R9 eligible combination count changed")
    _, selected_sorted, requested_metrics = eligible[0]
    if list(selected_sorted) != selection["selected_sorted_central_primary_indices"]:
        raise ValueError("D1R9 selected central set changed")
    source_ordered = list(map(int, selection["source_ordered_central_primary_indices"]))
    removed = [value for value in source_ordered if value not in selected_sorted]
    added = [value for value in selected_sorted if value not in source_set]
    if len(removed) != 1 or len(added) != 1:
        raise ValueError("D1R9 expected one central replacement")
    selected_ordered = [added[0] if value == removed[0] else value for value in source_ordered]
    if selected_ordered != selection["selected_ordered_central_primary_indices"]:
        raise ValueError("D1R9 ordered central replacement changed")
    matrix = _candidate_matrix(primary, selected_ordered)
    changed = [
        index
        for index in range(24)
        if not np.array_equal(source_matrix[index], matrix[index])
    ]
    matrix_digest = _digest(matrix.tolist())
    if (
        changed != selection["changed_matrix_row_indices"]
        or matrix_digest != selection["requested_matrix_digest"]
    ):
        raise ValueError("D1R9 selected matrix changed")
    matrix_evidence = [_classification(evidence, row) for row in matrix]
    unknown_matrix_rows = [
        index
        for index, row in enumerate(matrix_evidence)
        if row["classification"] == "unknown"
    ]
    contradicted_matrix_rows = [
        index
        for index, row in enumerate(matrix_evidence)
        if row["classification"] == "contradicted"
    ]
    if (
        unknown_matrix_rows != cfg["candidate_spec_contract"]["row_indices"]
        or contradicted_matrix_rows
    ):
        raise ValueError("D1R9 selected matrix evidence coverage changed")
    return {
        "source_matrix_digest": _digest(source_matrix.tolist()),
        "combination_count": math.comb(16, 8),
        "eligible_combination_count": len(eligible),
        "primary_evidence": primary_rows,
        "negative_primary_evidence": negative_rows,
        "selected_sorted_central_primary_indices": list(selected_sorted),
        "selected_ordered_central_primary_indices": selected_ordered,
        "changed_matrix_row_indices": changed,
        "requested_matrix": matrix.tolist(),
        "requested_matrix_digest": matrix_digest,
        "requested_metrics": requested_metrics,
        "matrix_evidence": matrix_evidence,
        "exact_safe_matrix_row_count": sum(
            row["classification"] == "exact_safe" for row in matrix_evidence
        ),
        "unknown_matrix_row_indices": unknown_matrix_rows,
        "contradicted_matrix_row_indices": contradicted_matrix_rows,
    }


def _static_replay(
    project: Path,
    cfg: Mapping[str, Any],
    base_cfg: Mapping[str, Any],
    selection: Mapping[str, Any],
) -> dict[str, Any]:
    replay_cfg = copy.deepcopy(base_cfg)
    replay_cfg["matrix_contract"]["central_sign_primary_indices"] = copy.deepcopy(
        selection["selected_ordered_central_primary_indices"]
    )
    replay_cfg["matrix_contract"]["requested_matrix_digest"] = selection[
        "requested_matrix_digest"
    ]
    matrix = np.asarray(selection["requested_matrix"], dtype=float)
    result, rows = d1r7._authenticate_d1r1_and_static_replay(
        project, replay_cfg, matrix
    )
    gate = cfg["static_gate"]
    expected_counts = {
        "finite": int(gate["finite_construction_count"]),
        "issue": int(gate["issue_gate_pass_count"]),
        "cancel": int(gate["cancellation_gate_pass_count"]),
        "central": int(gate["central_sign_gate_pass_count"]),
        "global": int(gate["global_rank_condition_context_count"]),
        "slot": int(gate["slot_rank_condition_block_count"]),
        "late": int(gate["late_novelty_context_count"]),
    }
    if (
        not result["passed"]
        or int(result["context_count"]) != int(gate["context_count"])
        or result["counts"] != expected_counts
    ):
        raise ValueError("D1R9 complete static replay failed")
    return {**result, "rows": rows}


def _candidate_specs(
    cfg: Mapping[str, Any],
    base_cfg: Mapping[str, Any],
    contexts: Mapping[tuple[str, str], Mapping[str, Any]],
    selection: Mapping[str, Any],
) -> dict[str, Any]:
    contract = cfg["candidate_spec_contract"]
    matrix = np.asarray(selection["requested_matrix"], dtype=float)
    issue = list(map(int, base_cfg["matrix_contract"]["issue_task_steps"]))
    cancel = list(map(int, base_cfg["matrix_contract"]["cancel_task_steps"]))
    rows = list(map(int, contract["row_indices"]))
    specs = []
    for context in sorted(contexts):
        source = contexts[context]
        for row_index in rows:
            spec = copy.deepcopy(dict(source))
            row = matrix[row_index]
            schedule = {}
            for slot, (start, stop) in enumerate(zip(issue, cancel)):
                coordinate = row[4 * slot : 4 * slot + 4].tolist()
                schedule[str(start)] = coordinate
                schedule[str(stop)] = (-row[4 * slot : 4 * slot + 4]).tolist()
            seed = {
                "stage": contract["stage"],
                "campaign_identity": contract["campaign_identity"],
                "pair_id": context[0],
                "history_member": context[1],
                "row_index": row_index,
                "requested_matrix_digest": selection["requested_matrix_digest"],
            }
            experiment_id = "s42r3c3t13s24d1r10_" + _digest(seed)[:20]
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
                    "s24_schedule_digest": selection["requested_matrix_digest"],
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
    horizons = Counter(str(int(row["horizon_steps"])) for row in specs)
    snapshots = {str(row["restart_snapshot_dir"]) for row in specs}
    row_counts = Counter(int(row["s24_sequence_index"]) for row in specs)
    if (
        len(specs) != int(contract["expected_specs"])
        or len({str(row["experiment_id"]) for row in specs}) != len(specs)
        or len(contexts) != int(contract["expected_contexts"])
        or len(snapshots) != int(contract["expected_snapshots"])
        or horizons
        != Counter({str(key): int(value) for key, value in contract["expected_horizon_counts"].items()})
        or row_counts != Counter({index: int(contract["expected_contexts"]) for index in rows})
    ):
        raise ValueError("D1R9 D1R10 candidate coverage changed")
    return {
        "schema_version": 1,
        "stage": contract["stage"],
        "campaign_identity": contract["campaign_identity"],
        "requested_matrix_digest": selection["requested_matrix_digest"],
        "candidate_row_indices": rows,
        "selected_spec_count": len(specs),
        "ordered_spec_digest": _digest(specs),
        "source_outcomes_available_to_controller": False,
        "pair_history_partition_label_available_to_controller": False,
        "spec_rows": specs,
    }


def compute(config_path: Path, project: Path) -> dict[str, Any]:
    project = project.resolve()
    cfg, base_cfg = load_config(config_path, project)
    d1r7_auth = _authenticate_d1r7(project, cfg)
    s24_auth = d1r7._authenticate_s24(project, base_cfg)
    d1r2_auth, _ = d1r7._authenticate_d1r2(project, base_cfg)
    d1r6_auth = d1r7._authenticate_d1r6(project, base_cfg)
    d1r8_auth = _authenticate_d1r8(project, cfg)
    evidence = _collect_evidence(project, base_cfg, d1r8_auth)
    selection = _selection(cfg, base_cfg, evidence)
    static = _static_replay(project, cfg, base_cfg, selection)
    candidate = _candidate_specs(
        cfg, base_cfg, d1r8_auth["contexts"], selection
    )
    passed = bool(
        d1r7_auth["passed"]
        and s24_auth["strict_parse_count"] == 600
        and d1r2_auth["strict_parse_count"] == 54
        and d1r6_auth["raw_inventory"]["count"] == 9
        and d1r8_auth["strict_parse_count"] == 108
        and selection["eligible_combination_count"] == 495
        and selection["exact_safe_matrix_row_count"] == 17
        and not selection["contradicted_matrix_row_indices"]
        and static["passed"]
        and candidate["selected_spec_count"] == 126
    )
    return {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "package_revision": PACKAGE_REVISION,
        "source_authentication": {
            "d1r7": d1r7_auth,
            "s24": s24_auth,
            "d1r2": d1r2_auth,
            "d1r6": d1r6_auth,
            "d1r8": {key: value for key, value in d1r8_auth.items() if key != "contexts"},
        },
        "selection": selection,
        "static_replay": static,
        "candidate": candidate,
        "new_raw_files_created": 0,
        "ray_gotsc_tsc_controller_or_plant_executed": False,
        "formal_timing_unchanged": True,
        "passed": passed,
        "route": cfg["routes"]["pass"] if passed else cfg["routes"]["fail"],
    }


def run(config_path: Path, project: Path, output: Path) -> dict[str, Any]:
    output = output.resolve()
    if output.exists():
        raise ValueError("D1R9 output directory must be new")
    result = compute(config_path, project)
    output.mkdir(parents=True)
    candidate_path = output / "stage4_2r3c3t13s24d1r9_d1r10_candidate_specs_v1.json"
    detailed_path = output / "stage4_2r3c3t13s24d1r9_central_row_replacement_preflight_v1.json"
    summary_path = output / "stage4_2r3c3t13s24d1r9_summary_v1.json"
    _write_json(candidate_path, result["candidate"])
    detailed = {key: value for key, value in result.items() if key != "candidate"}
    detailed["candidate_spec_count"] = result["candidate"]["selected_spec_count"]
    detailed["candidate_spec_digest"] = result["candidate"]["ordered_spec_digest"]
    _write_json(detailed_path, detailed)
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "passed": result["passed"],
        "route": result["route"],
        "combination_count": result["selection"]["combination_count"],
        "eligible_combination_count": result["selection"]["eligible_combination_count"],
        "changed_matrix_row_indices": result["selection"]["changed_matrix_row_indices"],
        "requested_matrix_digest": result["selection"]["requested_matrix_digest"],
        "exact_safe_matrix_row_count": result["selection"]["exact_safe_matrix_row_count"],
        "unknown_matrix_row_indices": result["selection"]["unknown_matrix_row_indices"],
        "static_counts": result["static_replay"]["counts"],
        "candidate_spec_count": result["candidate"]["selected_spec_count"],
        "candidate_spec_digest": result["candidate"]["ordered_spec_digest"],
        "new_raw_or_tsc_count": 0,
        "d1r10_execution_authorized": False,
        "mpc_or_learning_authorized": False,
    }
    _write_json(summary_path, summary)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    result = run(args.config, args.project, args.output)
    print(
        json.dumps(
            {
                "stage": result["stage"],
                "passed": result["passed"],
                "route": result["route"],
                "changed_matrix_row_indices": result["selection"]["changed_matrix_row_indices"],
                "unknown_matrix_row_indices": result["selection"]["unknown_matrix_row_indices"],
                "candidate_spec_count": result["candidate"]["selected_spec_count"],
            },
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
