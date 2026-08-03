"""Primary zero-TSC D1R7 temporal-basis substitution preflight."""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
import math
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


STAGE = "Stage4.2R3c3T13S24D1R7"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def _read_raw(path: Path) -> Any:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(stream)


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _inventory(paths: Iterable[Path]) -> dict[str, Any]:
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


def _assert_hash(path: Path, expected: str, label: str) -> str:
    if not path.is_file():
        raise ValueError(f"D1R7 missing {label}: {path}")
    actual = _sha256(path)
    if actual != expected:
        raise ValueError(f"D1R7 {label} hash mismatch: {actual}")
    return actual


def _validate_config(cfg: Mapping[str, Any], config_path: Path) -> None:
    if (
        cfg.get("schema_version") != 1
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != "temporal_basis_substitution_preflight_v1"
        or cfg.get("package_revision")
        != "r42r3c3t13s24d1r7_temporal_basis_substitution_preflight_v1"
    ):
        raise ValueError("D1R7 identity changed")
    design = (config_path.parents[1] / str(cfg["design_document"])).resolve()
    if _sha256(design) != cfg["design_document_sha256"]:
        raise ValueError("D1R7 frozen design hash mismatch")
    matrix = cfg["matrix_contract"]
    if (
        matrix["issue_task_steps"] != [10, 13, 15, 17]
        or matrix["cancel_task_steps"] != [11, 14, 16, 18]
        or matrix["canonical_direction_amplitudes"] != [0.25, 0.25, 0.29, 0.36]
        or matrix["central_sign_primary_indices"] != [0, 4, 1, 5, 3, 7, 6, 8]
        or matrix["candidate_sentinel_row_indices"] != [2, 6, 10, 14, 22, 23]
        or matrix["requested_matrix_digest"]
        != "c4430a13b679ad8dcceb72c259051a5eebad03da47d86816d46c4385cd811d77"
    ):
        raise ValueError("D1R7 matrix contract changed")
    execution = cfg["execution_contract"]
    if any(
        bool(execution[name])
        for name in (
            "ray_executed",
            "gotsc_executed",
            "tsc_executed",
            "controller_executed",
            "snapshot_creation_allowed",
        )
    ) or int(execution["new_raw_count"]) != 0 or int(execution["plant_steps_executed"]) != 0:
        raise ValueError("D1R7 zero-execution contract changed")
    scope = cfg["scientific_scope"]
    if (
        not bool(scope["development_set_preflight_only"])
        or bool(scope["model_fit_executed"])
        or bool(scope["real_mpc_executed"])
        or not bool(scope["pass_authorizes_real_sentinel_design_only"])
        or bool(scope["pass_authorizes_real_sentinel_execution"])
        or bool(scope["probe_trajectories_allowed_in_expert_dataset"])
        or bool(scope["bc_dagger_or_rl_allowed"])
    ):
        raise ValueError("D1R7 scientific scope changed")


def requested_matrix(cfg: Mapping[str, Any]) -> np.ndarray:
    contract = cfg["matrix_contract"]
    directions = np.asarray(contract["canonical_direction_signs"], dtype=int)
    standard = np.asarray(contract["standard_temporal_basis"], dtype=int)
    direction2 = np.asarray(contract["direction2_temporal_basis"], dtype=int)
    amplitudes = np.asarray(contract["canonical_direction_amplitudes"], dtype=float)
    if (
        directions.shape != (4, 4)
        or standard.shape != (4, 4)
        or direction2.shape != (4, 4)
        or set(map(int, directions.ravel())) != {-1, 1}
        or set(map(int, standard.ravel())) != {-1, 1}
        or set(map(int, direction2.ravel())) != {-1, 1}
    ):
        raise ValueError("D1R7 sign matrices changed")
    primary = []
    for outer_index in range(4):
        for direction in range(4):
            timing = direction2 if direction == 2 else standard
            primary.append(
                np.concatenate(
                    [
                        timing[outer_index, slot]
                        * directions[direction]
                        * amplitudes[direction]
                        for slot in range(4)
                    ]
                )
            )
    pairs = list(map(int, contract["central_sign_primary_indices"]))
    output = np.vstack([*primary, *[-primary[index] for index in pairs]])
    if output.shape != (24, 16) or not np.all(np.isfinite(output)):
        raise ValueError("D1R7 requested matrix invalid")
    if _digest(output.tolist()) != contract["requested_matrix_digest"]:
        raise ValueError("D1R7 requested matrix digest mismatch")
    return output


def _normalized_condition(matrix: np.ndarray) -> float:
    values = np.asarray(matrix, dtype=float)
    norms = np.linalg.norm(values, axis=0)
    if values.ndim != 2 or np.any(norms <= 0.0) or not np.all(np.isfinite(values)):
        return math.inf
    return float(np.linalg.cond(values / norms))


def matrix_metrics(matrix: np.ndarray, cfg: Mapping[str, Any]) -> dict[str, Any]:
    values = np.asarray(matrix, dtype=float)
    contract = cfg["matrix_contract"]
    if values.shape != (24, 16) or not np.all(np.isfinite(values)):
        raise ValueError("D1R7 actual matrix invalid")
    rank = int(np.linalg.matrix_rank(values))
    condition = _normalized_condition(values)
    slot_rows = []
    for slot in range(4):
        block = values[:, 4 * slot : 4 * slot + 4]
        slot_rank = int(np.linalg.matrix_rank(block))
        slot_condition = _normalized_condition(block)
        slot_rows.append(
            {
                "slot": slot,
                "rank": slot_rank,
                "normalized_condition": slot_condition,
                "passed": bool(
                    slot_rank == int(contract["required_slot_rank"])
                    and slot_condition
                    <= float(contract["maximum_slot_normalized_condition"]) + 1e-12
                ),
            }
        )
    slot0 = values[:, :4]
    projector = slot0 @ np.linalg.pinv(slot0)
    residuals = [
        float(
            np.linalg.norm(values[:, column] - projector @ values[:, column])
            / max(float(np.linalg.norm(values[:, column])), 1e-300)
        )
        for column in range(4, 16)
    ]
    return {
        "global_rank": rank,
        "global_normalized_condition": condition,
        "global_pass": bool(
            rank == int(contract["required_global_rank"])
            and condition
            <= float(contract["maximum_global_normalized_condition"]) + 1e-12
        ),
        "slot_rows": slot_rows,
        "slot_pass_count": sum(bool(row["passed"]) for row in slot_rows),
        "late_column_residuals": residuals,
        "minimum_late_column_residual": min(residuals),
        "late_novelty_pass": bool(
            min(residuals)
            >= float(contract["minimum_late_column_residual_outside_slot0_span"])
            - 1e-12
        ),
    }


def _failure_payload(reason: str, marker: str) -> Mapping[str, Any] | None:
    if marker not in reason:
        return None
    payload = reason[reason.index(marker) + len(marker) :]
    start, stop = payload.find("{"), payload.rfind("}")
    if start < 0 or stop < start:
        raise ValueError("D1R7 source failure lost structured JSON")
    return json.loads(payload[start : stop + 1])


def _authenticate_s24(project: Path, cfg: Mapping[str, Any]) -> dict[str, Any]:
    source = cfg["source_contract"]
    stage = project / source["s24_stage_relpath"]
    baseline_path = stage / "specs" / "training_baseline_specs.json"
    sequence_path = stage / "specs" / "training_sequence_specs.json"
    hashes = {
        "baseline_specs": _assert_hash(
            baseline_path, source["s24_baseline_specs_sha256"], "S24 baseline specs"
        ),
        "sequence_specs": _assert_hash(
            sequence_path, source["s24_sequence_specs_sha256"], "S24 sequence specs"
        ),
        "manifest": _assert_hash(
            stage / "stage_manifest.json", source["s24_manifest_sha256"], "S24 manifest"
        ),
        "state": _assert_hash(
            stage / "stage_state.json", source["s24_state_sha256"], "S24 state"
        ),
    }
    specs = [*_read_json(baseline_path), *_read_json(sequence_path)]
    spec_by_id = {str(row["experiment_id"]): row for row in specs}
    inventory = _inventory((stage / "raw").glob("*.json.gz"))
    if (
        len(specs) != 600
        or len(spec_by_id) != 600
        or inventory["count"] != int(source["s24_raw_count"])
        or inventory["digest"] != source["s24_raw_inventory_digest"]
    ):
        raise ValueError("D1R7 S24 inventory changed")
    baseline_success = sequence_success = 0
    failures: Counter[int] = Counter()
    strict = 0
    for path in sorted((stage / "raw").glob("*.json.gz")):
        result = _read_raw(path)
        experiment_id = str(result.get("experiment_id"))
        spec = spec_by_id.get(experiment_id)
        if spec is None or result.get("spec") != spec:
            raise ValueError("D1R7 S24 raw identity/spec mismatch")
        strict += 1
        role = str(spec["s24_role"])
        if bool(result.get("success")):
            if role == "baseline":
                baseline_success += 1
            elif role == "sequential_response":
                sequence_success += 1
            else:
                raise ValueError("D1R7 S24 role changed")
        else:
            if role != "sequential_response":
                raise ValueError("D1R7 S24 baseline failed")
            event = _failure_payload(
                str(result.get("failure_reason", "")), "S24 sequential cancel action failed:"
            )
            if (
                event is None
                or event.get("event") != "sequential_cancel"
                or int(event.get("slot", -1)) != 3
                or int(event.get("task_step", -1)) != 18
                or bool(event.get("passed"))
                or float(event.get("incremental_normalized_action_linf", 0.0)) <= 0.25
            ):
                raise ValueError("D1R7 S24 failure class changed")
            failures[int(spec["s24_sequence_index"])] += 1
    expected_failures = Counter(
        {int(key): int(value) for key, value in source["s24_failure_sequence_counts"].items()}
    )
    if (
        strict != 600
        or baseline_success != int(source["s24_baseline_success_count"])
        or sequence_success != int(source["s24_sequence_success_count"])
        or sum(failures.values()) != int(source["s24_sequence_failure_count"])
        or failures != expected_failures
    ):
        raise ValueError("D1R7 S24 result changed")
    return {
        "stage_dir": str(stage),
        "hashes": hashes,
        "raw_inventory": inventory,
        "strict_parse_count": strict,
        "baseline_success_count": baseline_success,
        "sequence_success_count": sequence_success,
        "sequence_failure_count": sum(failures.values()),
        "failure_sequence_counts": {str(k): failures[k] for k in sorted(failures)},
    }


def _spec_list(value: Any) -> list[Mapping[str, Any]]:
    if isinstance(value, list):
        return value
    if isinstance(value, Mapping):
        for key in ("spec_rows", "specs"):
            if isinstance(value.get(key), list):
                return value[key]
    raise ValueError("D1R7 source spec container changed")


def _authenticate_d1r2(
    project: Path, cfg: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[tuple[str, str], Mapping[str, Any]]]:
    source = cfg["source_contract"]
    stage = project / source["d1r2_stage_relpath"]
    spec_path = stage / "specs" / "normalized_sentinel_specs.json"
    hashes = {
        "specs": _assert_hash(spec_path, source["d1r2_specs_sha256"], "D1R2 specs"),
        "manifest": _assert_hash(
            stage / "stage_manifest.json", source["d1r2_manifest_sha256"], "D1R2 manifest"
        ),
        "state": _assert_hash(
            stage / "stage_state.json", source["d1r2_state_sha256"], "D1R2 state"
        ),
        "independent": _assert_hash(
            stage / "analysis" / "independent_server_forensics.json",
            source["d1r2_independent_sha256"],
            "D1R2 independent",
        ),
        "retrospective": _assert_hash(
            stage / "analysis" / "retrospective_structured_failure_prefix_forensics_v1.json",
            source["d1r2_retrospective_sha256"],
            "D1R2 retrospective",
        ),
    }
    specs = _spec_list(_read_json(spec_path))
    spec_by_id = {str(row["experiment_id"]): row for row in specs}
    inventory = _inventory((stage / "raw").glob("*.json.gz"))
    if (
        len(specs) != 54
        or len(spec_by_id) != 54
        or inventory["count"] != int(source["d1r2_raw_count"])
        or inventory["digest"] != source["d1r2_raw_inventory_digest"]
    ):
        raise ValueError("D1R7 D1R2 inventory changed")
    success = 0
    failures: Counter[int] = Counter()
    contexts: dict[tuple[str, str], Mapping[str, Any]] = {}
    failure_contexts = set()
    for path in sorted((stage / "raw").glob("*.json.gz")):
        result = _read_raw(path)
        experiment_id = str(result.get("experiment_id"))
        spec = spec_by_id.get(experiment_id)
        if spec is None or result.get("spec") != spec:
            raise ValueError("D1R7 D1R2 raw identity/spec mismatch")
        key = (str(spec["pair_id"]), str(spec["history_member"]))
        prior = contexts.get(key)
        if prior is None or str(spec["experiment_id"]) < str(prior["experiment_id"]):
            contexts[key] = spec
        if bool(result.get("success")):
            horizon = int(spec["horizon_steps"])
            if (
                len(result.get("trajectory") or []) != horizon + 1
                or len(result.get("controller_trace") or []) != horizon
            ):
                raise ValueError("D1R7 D1R2 successful horizon changed")
            success += 1
            continue
        event = result.get("action_failure_event") or {}
        criteria = event.get("criteria") or {}
        sequence = int(spec["s24_sequence_index"])
        if (
            result.get("failure_class") != "structured_action_schedule_gate"
            or event.get("event") != "sequential_cancel"
            or int(event.get("task_step", -1)) != 18
            or int(event.get("slot", -1)) != 3
            or bool(event.get("passed"))
            or bool(event.get("failed_candidate_applied", False))
            or criteria.get("online_cancel_margin") is not False
            or sequence not in {6, 10, 18}
        ):
            raise ValueError("D1R7 D1R2 failure class changed")
        failures[sequence] += 1
        failure_contexts.add(key)
    expected = Counter(
        {int(key): int(value) for key, value in source["d1r2_failure_sequence_counts"].items()}
    )
    if (
        success != int(source["d1r2_success_count"])
        or failures != expected
        or sum(failures.values()) != int(source["d1r2_structured_failure_count"])
        or len(contexts) != int(cfg["candidate_spec_contract"]["expected_contexts"])
        or len({key[0] for key in contexts}) != int(cfg["candidate_spec_contract"]["expected_pairs"])
        or len(failure_contexts) != 3
    ):
        raise ValueError("D1R7 D1R2 result changed")
    return (
        {
            "stage_dir": str(stage),
            "hashes": hashes,
            "raw_inventory": inventory,
            "strict_parse_count": len(specs),
            "success_count": success,
            "structured_failure_count": sum(failures.values()),
            "failure_sequence_counts": {str(k): failures[k] for k in sorted(failures)},
            "failure_contexts": [list(key) for key in sorted(failure_contexts)],
            "unique_context_count": len(contexts),
        },
        contexts,
    )


def _authenticate_d1r6(project: Path, cfg: Mapping[str, Any]) -> dict[str, Any]:
    source = cfg["source_contract"]
    stage = project / source["d1r6_stage_relpath"]
    spec_path = stage / "specs" / "sentinel_specs.json"
    hashes = {
        "specs": _assert_hash(spec_path, source["d1r6_specs_sha256"], "D1R6 specs"),
        "manifest": _assert_hash(
            stage / "stage_manifest.json", source["d1r6_manifest_sha256"], "D1R6 manifest"
        ),
        "state": _assert_hash(
            stage / "stage_state.json", source["d1r6_state_sha256"], "D1R6 state"
        ),
        "independent": _assert_hash(
            stage / "analysis" / "independent_server_forensics.json",
            source["d1r6_independent_sha256"],
            "D1R6 independent",
        ),
        "physical_state_hotfix": _assert_hash(
            stage / "analysis" / "physical_state_prefix_reporting_hotfix_v1.json",
            source["d1r6_physical_state_hotfix_sha256"],
            "D1R6 physical state correction",
        ),
    }
    specs = _spec_list(_read_json(spec_path))
    spec_by_id = {str(row["experiment_id"]): row for row in specs}
    inventory = _inventory((stage / "raw").glob("*.json.gz"))
    if (
        len(specs) != 9
        or len(spec_by_id) != 9
        or inventory["count"] != int(source["d1r6_raw_count"])
        or inventory["digest"] != source["d1r6_raw_inventory_digest"]
    ):
        raise ValueError("D1R7 D1R6 inventory changed")
    stops = 0
    sequence_counts: Counter[int] = Counter()
    for path in sorted((stage / "raw").glob("*.json.gz")):
        result = _read_raw(path)
        spec = spec_by_id.get(str(result.get("experiment_id")))
        if spec is None or result.get("spec") != spec:
            raise ValueError("D1R7 D1R6 raw identity/spec mismatch")
        event = result.get("action_failure_event") or {}
        criteria = event.get("criteria") or {}
        if (
            bool(result.get("success"))
            or result.get("failure_class") != "structured_action_schedule_gate"
            or event.get("event") != "sequential_cancel_recursive_deadline_stop"
            or int(event.get("task_step", -1)) != 22
            or int(event.get("continuation_count", -1)) != 3
            or bool(event.get("failed_candidate_applied"))
            or bool(event.get("plant_advance_after_failure"))
            or criteria.get("finish_increment") is not False
            or criteria.get("original_increment") is not False
        ):
            raise ValueError("D1R7 D1R6 stop class changed")
        stops += 1
        sequence_counts[int(spec["s24_sequence_index"])] += 1
    physical = _read_json(stage / "analysis" / "physical_state_prefix_reporting_hotfix_v1.json")
    independent = _read_json(stage / "analysis" / "independent_server_forensics.json")
    if (
        stops != int(source["d1r6_structured_deadline_stop_count"])
        or sequence_counts != Counter({6: 3, 10: 3, 18: 3})
        or not bool(physical.get("reporting_bug_confirmed"))
        or int(physical.get("physical_source_prefix_state_exact_count", -1)) != 9
        or int(physical.get("unexpected_physical_state_difference_count", -1)) != 0
        or not bool(independent.get("forensic_recomputation_passed"))
    ):
        raise ValueError("D1R7 D1R6 forensic result changed")
    return {
        "stage_dir": str(stage),
        "hashes": hashes,
        "raw_inventory": inventory,
        "strict_parse_count": len(specs),
        "structured_deadline_stop_count": stops,
        "failure_sequence_counts": {
            str(key): sequence_counts[key] for key in sorted(sequence_counts)
        },
        "physical_source_prefix_state_exact_count": 9,
    }


def _event_key(slot: int, desired: Sequence[float]) -> tuple[int, tuple[str, ...]]:
    return slot, tuple(format(float(value), ".12g") for value in desired)


def _authenticate_d1r1_and_static_replay(
    project: Path, cfg: Mapping[str, Any], matrix: np.ndarray
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    source = cfg["source_contract"]
    output = project / source["d1r1_output_relpath"]
    detailed_path = output / "stage4_2r3c3t13s24d1r1_geometry_restoring_search_v1.json"
    hashes = {
        "detailed": _assert_hash(
            detailed_path, source["d1r1_detailed_sha256"], "D1R1 detailed"
        ),
        "summary": _assert_hash(
            output / "stage4_2r3c3t13s24d1r1_summary_v1.json",
            source["d1r1_summary_sha256"],
            "D1R1 summary",
        ),
        "manifest": _assert_hash(
            output / "stage4_2r3c3t13s24d1r1_manifest_v1.json",
            source["d1r1_manifest_sha256"],
            "D1R1 manifest",
        ),
    }
    detailed = _read_json(detailed_path)
    events = list(detailed.get("event_rows") or [])
    if (
        detailed.get("route")
        != "GEOMETRY_RESTORING_AMPLITUDE_SEARCH_PASS_REAL_SENTINEL_REQUIRED"
        or len(events) != 3840
    ):
        raise ValueError("D1R7 D1R1 source result changed")
    contexts: dict[tuple[str, str], dict[tuple[int, tuple[str, ...]], Mapping[str, Any]]] = defaultdict(dict)
    for event in events:
        context = (str(event["pair_id"]), str(event["history_member"]))
        key = _event_key(int(event["slot"]), event["desired_coordinate"])
        prior = contexts[context].get(key)
        if prior is not None:
            fields = (
                "actual_coordinate",
                "issue_gate_pass",
                "cancellation_gate_pass",
                "finite_issue_and_cancellation",
                "issue_center_fields",
                "issue_target_fields",
            )
            if any(prior[field] != event[field] for field in fields):
                raise ValueError("D1R7 D1R1 static lookup is non-unique")
        contexts[context][key] = event
    if len(contexts) != 40:
        raise ValueError("D1R7 D1R1 context count changed")
    pair_indices = list(map(int, cfg["matrix_contract"]["central_sign_primary_indices"]))
    rows = []
    totals = Counter()
    for context, index in sorted(contexts.items()):
        actual = np.zeros((24, 16), dtype=float)
        selected: dict[tuple[int, int], Mapping[str, Any]] = {}
        for row_index, row in enumerate(matrix):
            for slot in range(4):
                event = index.get(_event_key(slot, row[4 * slot : 4 * slot + 4]))
                if event is None:
                    raise ValueError("D1R7 candidate block missing from D1R1 catalog")
                selected[(row_index, slot)] = event
                actual[row_index, 4 * slot : 4 * slot + 4] = np.asarray(
                    event["actual_coordinate"], dtype=float
                )
                totals["finite"] += 2 * int(bool(event["finite_issue_and_cancellation"]))
                totals["issue"] += int(bool(event["issue_gate_pass"]))
                totals["cancel"] += int(bool(event["cancellation_gate_pass"]))
        central = 0
        for sentinel, primary in enumerate(pair_indices, start=16):
            for slot in range(4):
                plus = selected[(primary, slot)]
                minus = selected[(sentinel, slot)]
                centers = tuple(Decimal(str(value)) for value in plus["issue_center_fields"])
                plus_targets = tuple(
                    Decimal(str(value)) for value in plus["issue_target_fields"]
                )
                minus_targets = tuple(
                    Decimal(str(value)) for value in minus["issue_target_fields"]
                )
                passed = bool(
                    plus["issue_center_fields"] == minus["issue_center_fields"]
                    and all(
                        plus_value + minus_value == 2 * center
                        for plus_value, minus_value, center in zip(
                            plus_targets, minus_targets, centers
                        )
                    )
                )
                central += int(passed)
                totals["central"] += int(passed)
        metrics = matrix_metrics(actual, cfg)
        totals["global"] += int(bool(metrics["global_pass"]))
        totals["slot"] += int(metrics["slot_pass_count"])
        totals["late"] += int(bool(metrics["late_novelty_pass"]))
        rows.append(
            {
                "pair_id": context[0],
                "history_member": context[1],
                "finite_construction_count": 192,
                "issue_gate_pass_count": 96,
                "cancellation_gate_pass_count": 96,
                "central_sign_gate_pass_count": central,
                "matrix_metrics": metrics,
            }
        )
    gate = cfg["static_gate"]
    expected = {
        "finite": int(gate["finite_construction_count"]),
        "issue": int(gate["issue_gate_pass_count"]),
        "cancel": int(gate["cancellation_gate_pass_count"]),
        "central": int(gate["central_sign_gate_pass_count"]),
        "global": int(gate["global_rank_condition_context_count"]),
        "slot": int(gate["slot_rank_condition_block_count"]),
        "late": int(gate["late_novelty_context_count"]),
    }
    passed = bool(len(rows) == int(gate["context_count"]) and totals == Counter(expected))
    return (
        {
            "output_dir": str(output),
            "hashes": hashes,
            "source_event_count": len(events),
            "context_count": len(rows),
            "counts": dict(totals),
            "maximum_actual_global_normalized_condition": max(
                float(row["matrix_metrics"]["global_normalized_condition"]) for row in rows
            ),
            "maximum_actual_slot_normalized_condition": max(
                float(slot["normalized_condition"])
                for row in rows
                for slot in row["matrix_metrics"]["slot_rows"]
            ),
            "minimum_actual_late_column_residual": min(
                float(row["matrix_metrics"]["minimum_late_column_residual"])
                for row in rows
            ),
            "passed": passed,
        },
        rows,
    )


def _candidate_specs(
    contexts: Mapping[tuple[str, str], Mapping[str, Any]],
    matrix: np.ndarray,
    cfg: Mapping[str, Any],
) -> dict[str, Any]:
    contract = cfg["candidate_spec_contract"]
    issue = list(map(int, cfg["matrix_contract"]["issue_task_steps"]))
    cancel = list(map(int, cfg["matrix_contract"]["cancel_task_steps"]))
    row_indices = list(map(int, cfg["matrix_contract"]["candidate_sentinel_row_indices"]))
    specs = []
    for context in sorted(contexts):
        source = contexts[context]
        for row_index in row_indices:
            spec = copy.deepcopy(source)
            row = matrix[row_index]
            schedule: dict[str, list[float]] = {}
            for slot, (start, stop) in enumerate(zip(issue, cancel)):
                coordinate = row[4 * slot : 4 * slot + 4].tolist()
                schedule[str(start)] = coordinate
                schedule[str(stop)] = (-row[4 * slot : 4 * slot + 4]).tolist()
            identity_seed = {
                "stage": contract["stage"],
                "campaign_identity": contract["campaign_identity"],
                "pair_id": context[0],
                "history_member": context[1],
                "row_index": row_index,
                "requested_matrix_digest": cfg["matrix_contract"]["requested_matrix_digest"],
            }
            experiment_id = "s42r3c3t13s24d1r8_" + _digest(identity_seed)[:20]
            spec.update(
                {
                    "experiment_id": experiment_id,
                    "environment_variant": "stage4_2r3c3t13s24d1r8_" + experiment_id.rsplit("_", 1)[-1],
                    "kind": "stage4_2r3c3t13s24d1r8_temporal_basis_substitution_safety_sentinel",
                    "phase": "prospective_temporal_basis_substitution_safety_sentinel",
                    "campaign_identity": contract["campaign_identity"],
                    "controller_revision": contract["controller_revision"],
                    "probe_primitive_revision": contract["probe_primitive_revision"],
                    "s24_sequence_index": row_index,
                    "s24_requested_matrix_row": row.tolist(),
                    "s24_requested_action_by_task_step": schedule,
                    "s24_schedule_digest": cfg["matrix_contract"]["requested_matrix_digest"],
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
    ids = {str(row["experiment_id"]) for row in specs}
    horizons = Counter(str(int(row["horizon_steps"])) for row in specs)
    snapshots = {str(row["restart_snapshot_dir"]) for row in specs}
    if (
        len(specs) != int(contract["expected_specs"])
        or len(ids) != len(specs)
        or horizons != Counter({str(k): int(v) for k, v in contract["expected_horizon_counts"].items()})
        or len(snapshots) != int(contract["expected_snapshots"])
        or Counter(int(row["s24_sequence_index"]) for row in specs)
        != Counter({index: int(contract["expected_contexts"]) for index in row_indices})
    ):
        raise ValueError("D1R7 candidate spec coverage changed")
    return {
        "schema_version": 1,
        "stage": contract["stage"],
        "campaign_identity": contract["campaign_identity"],
        "requested_matrix_digest": cfg["matrix_contract"]["requested_matrix_digest"],
        "candidate_row_indices": row_indices,
        "selected_spec_count": len(specs),
        "ordered_spec_digest": _digest(specs),
        "source_outcomes_available_to_controller": False,
        "pair_history_partition_label_available_to_controller": False,
        "spec_rows": specs,
    }


def run(config_path: Path, project: Path, output: Path) -> dict[str, Any]:
    config_path = config_path.resolve()
    project = project.resolve()
    output = output.resolve()
    if output.exists():
        raise ValueError("D1R7 output directory must be new")
    cfg = _read_json(config_path)
    _validate_config(cfg, config_path)
    matrix = requested_matrix(cfg)
    requested_metrics = matrix_metrics(matrix, cfg)
    s24 = _authenticate_s24(project, cfg)
    d1r2, contexts = _authenticate_d1r2(project, cfg)
    d1r6 = _authenticate_d1r6(project, cfg)
    d1r1, context_rows = _authenticate_d1r1_and_static_replay(project, cfg, matrix)
    candidate = _candidate_specs(contexts, matrix, cfg)
    source_pass = bool(
        s24["strict_parse_count"] == 600
        and d1r2["strict_parse_count"] == 54
        and d1r6["strict_parse_count"] == 9
    )
    passed = bool(
        source_pass
        and requested_metrics["global_pass"]
        and requested_metrics["slot_pass_count"] == 4
        and requested_metrics["late_novelty_pass"]
        and d1r1["passed"]
        and candidate["selected_spec_count"]
        == int(cfg["candidate_spec_contract"]["expected_specs"])
    )
    route = cfg["routes"]["pass" if passed else "fail"]
    output.mkdir(parents=True)
    candidate_path = output / "stage4_2r3c3t13s24d1r7_candidate_specs_v1.json"
    detailed_path = output / "stage4_2r3c3t13s24d1r7_temporal_basis_substitution_preflight_v1.json"
    summary_path = output / "stage4_2r3c3t13s24d1r7_summary_v1.json"
    manifest_path = output / "stage4_2r3c3t13s24d1r7_manifest_v1.json"
    _write_json(candidate_path, candidate)
    detailed = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": cfg["identity"],
        "package_revision": cfg["package_revision"],
        "route": route,
        "passed": passed,
        "source_authentication_passed": source_pass,
        "source_authentication": {"s24": s24, "d1r2": d1r2, "d1r6": d1r6, "d1r1": d1r1},
        "requested_matrix": matrix.tolist(),
        "requested_matrix_digest": _digest(matrix.tolist()),
        "requested_matrix_metrics": requested_metrics,
        "static_context_rows": context_rows,
        "candidate_specs_sha256": _sha256(candidate_path),
        "candidate_spec_count": candidate["selected_spec_count"],
        "candidate_spec_digest": candidate["ordered_spec_digest"],
        "execution": cfg["execution_contract"],
        "scientific_scope": cfg["scientific_scope"],
    }
    _write_json(detailed_path, detailed)
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": cfg["identity"],
        "route": route,
        "passed": passed,
        "source_raw_counts": {"s24": 600, "d1r2": 54, "d1r6": 9},
        "source_failure_sequence_counts": {
            "s24": s24["failure_sequence_counts"],
            "d1r2": d1r2["failure_sequence_counts"],
            "d1r6": d1r6["failure_sequence_counts"],
        },
        "static_counts": d1r1["counts"],
        "requested_global_rank": requested_metrics["global_rank"],
        "requested_global_normalized_condition": requested_metrics["global_normalized_condition"],
        "maximum_actual_global_normalized_condition": d1r1["maximum_actual_global_normalized_condition"],
        "maximum_actual_slot_normalized_condition": d1r1["maximum_actual_slot_normalized_condition"],
        "minimum_actual_late_column_residual": d1r1["minimum_actual_late_column_residual"],
        "candidate_spec_count": candidate["selected_spec_count"],
        "candidate_spec_digest": candidate["ordered_spec_digest"],
        "new_raw_or_tsc_count": 0,
        "real_sentinel_execution_authorized": False,
        "mpc_or_learning_authorized": False,
    }
    _write_json(summary_path, summary)
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": cfg["identity"],
        "route": route,
        "passed": passed,
        "output_files": {
            detailed_path.name: _sha256(detailed_path),
            summary_path.name: _sha256(summary_path),
            candidate_path.name: _sha256(candidate_path),
        },
        "source_raw_files_copied_or_modified": 0,
        "new_raw_files_created": 0,
        "ray_gotsc_tsc_plant_or_controller_executed": False,
        "pass_authorizes_real_sentinel_design_only": True,
        "pass_authorizes_real_sentinel_execution": False,
    }
    _write_json(manifest_path, manifest)
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    summary = run(args.config, args.project_root, args.output)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
