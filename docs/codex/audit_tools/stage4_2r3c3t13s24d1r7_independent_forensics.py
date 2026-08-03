"""Independent source/static/spec recomputation for D1R7."""

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


def _bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_bytes(value)).hexdigest()


def _sha(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def _json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def _raw(path: Path) -> Any:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(stream)


def _failure_payload(reason: str, marker: str) -> Mapping[str, Any] | None:
    if marker not in reason:
        return None
    payload = reason[reason.index(marker) + len(marker) :]
    start, stop = payload.find("{"), payload.rfind("}")
    if start < 0 or stop < start:
        raise ValueError("D1R7 independent source failure lost structured JSON")
    return json.loads(payload[start : stop + 1])


def _write(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _inventory(paths: Iterable[Path]) -> dict[str, Any]:
    digest = hashlib.sha256()
    rows = []
    for path in sorted(paths):
        sha = _sha(path)
        size = path.stat().st_size
        digest.update(f"{path.name}\0{size}\0{sha}\n".encode())
        rows.append((path.name, size, sha))
    return {
        "count": len(rows),
        "total_bytes": sum(row[1] for row in rows),
        "digest": digest.hexdigest(),
    }


def _specs(value: Any) -> list[Mapping[str, Any]]:
    if isinstance(value, list):
        return value
    if isinstance(value, Mapping):
        for key in ("spec_rows", "specs"):
            if isinstance(value.get(key), list):
                return value[key]
    raise ValueError("D1R7 independent spec container changed")


def _matrix(cfg: Mapping[str, Any]) -> np.ndarray:
    contract = cfg["matrix_contract"]
    direction = np.asarray(contract["canonical_direction_signs"], dtype=int)
    standard = np.asarray(contract["standard_temporal_basis"], dtype=int)
    changed = np.asarray(contract["direction2_temporal_basis"], dtype=int)
    amplitudes = np.asarray(contract["canonical_direction_amplitudes"], dtype=float)
    primary = []
    for outer in range(4):
        for inner in range(4):
            timing = changed if inner == 2 else standard
            primary.append(
                np.concatenate(
                    [
                        timing[outer, slot] * direction[inner] * amplitudes[inner]
                        for slot in range(4)
                    ]
                )
            )
    pairs = list(map(int, contract["central_sign_primary_indices"]))
    result = np.vstack([*primary, *[-primary[index] for index in pairs]])
    if result.shape != (24, 16) or _digest(result.tolist()) != contract["requested_matrix_digest"]:
        raise ValueError("D1R7 independent matrix mismatch")
    return result


def _condition(matrix: np.ndarray) -> float:
    norms = np.linalg.norm(matrix, axis=0)
    if np.any(norms <= 0.0):
        return math.inf
    return float(np.linalg.cond(matrix / norms))


def _metrics(matrix: np.ndarray, cfg: Mapping[str, Any]) -> dict[str, Any]:
    contract = cfg["matrix_contract"]
    rank = int(np.linalg.matrix_rank(matrix))
    condition = _condition(matrix)
    slots = []
    for slot in range(4):
        block = matrix[:, 4 * slot : 4 * slot + 4]
        slots.append((int(np.linalg.matrix_rank(block)), _condition(block)))
    first = matrix[:, :4]
    projector = first @ np.linalg.pinv(first)
    residuals = [
        float(
            np.linalg.norm(matrix[:, column] - projector @ matrix[:, column])
            / np.linalg.norm(matrix[:, column])
        )
        for column in range(4, 16)
    ]
    return {
        "rank": rank,
        "condition": condition,
        "slot_rows": slots,
        "minimum_late_residual": min(residuals),
        "passed": bool(
            rank == int(contract["required_global_rank"])
            and condition <= float(contract["maximum_global_normalized_condition"]) + 1e-12
            and all(
                slot_rank == int(contract["required_slot_rank"])
                and slot_condition
                <= float(contract["maximum_slot_normalized_condition"]) + 1e-12
                for slot_rank, slot_condition in slots
            )
            and min(residuals)
            >= float(contract["minimum_late_column_residual_outside_slot0_span"])
            - 1e-12
        ),
    }


def _key(slot: int, desired: Sequence[float]) -> tuple[int, tuple[str, ...]]:
    return slot, tuple(format(float(value), ".12g") for value in desired)


def _source_counts(project: Path, cfg: Mapping[str, Any]) -> dict[str, Any]:
    source = cfg["source_contract"]
    s24 = project / source["s24_stage_relpath"]
    s24_specs = [
        *_json(s24 / "specs" / "training_baseline_specs.json"),
        *_json(s24 / "specs" / "training_sequence_specs.json"),
    ]
    s24_by_id = {str(row["experiment_id"]): row for row in s24_specs}
    s24_inventory = _inventory((s24 / "raw").glob("*.json.gz"))
    s24_success = Counter()
    s24_fail = Counter()
    s24_failure_slot_steps = Counter()
    cancel_steps = list(map(int, cfg["matrix_contract"]["cancel_task_steps"]))
    for path in sorted((s24 / "raw").glob("*.json.gz")):
        result = _raw(path)
        spec = s24_by_id.get(str(result.get("experiment_id")))
        if spec is None or result.get("spec") != spec:
            raise ValueError("D1R7 independent S24 identity mismatch")
        if bool(result.get("success")):
            s24_success[str(spec["s24_role"])] += 1
        else:
            reason = str(result.get("failure_reason", ""))
            event = _failure_payload(reason, "S24 sequential cancel action failed:")
            if event is None:
                raise ValueError("D1R7 independent S24 failure class mismatch")
            slot = int(event.get("slot", -1))
            task_step = int(event.get("task_step", -1))
            if (
                event.get("event") != "sequential_cancel"
                or bool(event.get("passed"))
                or slot < 0
                or slot >= len(cancel_steps)
                or task_step != cancel_steps[slot]
                or float(event.get("incremental_normalized_action_linf", 0.0)) <= 0.25
            ):
                raise ValueError("D1R7 independent S24 failure class mismatch")
            s24_failure_slot_steps[(slot, task_step)] += 1
            s24_fail[int(spec["s24_sequence_index"])] += 1
    expected_s24 = Counter(
        {int(key): int(value) for key, value in source["s24_failure_sequence_counts"].items()}
    )
    if (
        s24_inventory["count"] != int(source["s24_raw_count"])
        or s24_inventory["digest"] != source["s24_raw_inventory_digest"]
        or s24_success != Counter({"baseline": 24, "sequential_response": 522})
        or s24_fail != expected_s24
    ):
        raise ValueError("D1R7 independent S24 counts changed")

    d1r2 = project / source["d1r2_stage_relpath"]
    d1r2_specs = _specs(_json(d1r2 / "specs" / "normalized_sentinel_specs.json"))
    d1r2_by_id = {str(row["experiment_id"]): row for row in d1r2_specs}
    d1r2_inventory = _inventory((d1r2 / "raw").glob("*.json.gz"))
    d1r2_success = 0
    d1r2_fail = Counter()
    contexts: dict[tuple[str, str], Mapping[str, Any]] = {}
    for path in sorted((d1r2 / "raw").glob("*.json.gz")):
        result = _raw(path)
        spec = d1r2_by_id.get(str(result.get("experiment_id")))
        if spec is None or result.get("spec") != spec:
            raise ValueError("D1R7 independent D1R2 identity mismatch")
        context = (str(spec["pair_id"]), str(spec["history_member"]))
        old = contexts.get(context)
        if old is None or str(spec["experiment_id"]) < str(old["experiment_id"]):
            contexts[context] = spec
        if bool(result.get("success")):
            d1r2_success += 1
        else:
            event = result.get("action_failure_event") or {}
            if (
                result.get("failure_class") != "structured_action_schedule_gate"
                or event.get("event") != "sequential_cancel"
                or int(event.get("task_step", -1)) != 18
                or int(event.get("slot", -1)) != 3
            ):
                raise ValueError("D1R7 independent D1R2 failure changed")
            d1r2_fail[int(spec["s24_sequence_index"])] += 1
    expected_d1r2 = Counter(
        {int(key): int(value) for key, value in source["d1r2_failure_sequence_counts"].items()}
    )
    if (
        d1r2_inventory["count"] != int(source["d1r2_raw_count"])
        or d1r2_inventory["digest"] != source["d1r2_raw_inventory_digest"]
        or d1r2_success != int(source["d1r2_success_count"])
        or d1r2_fail != expected_d1r2
        or len(contexts) != 18
    ):
        raise ValueError("D1R7 independent D1R2 counts changed")

    d1r6 = project / source["d1r6_stage_relpath"]
    d1r6_specs = _specs(_json(d1r6 / "specs" / "sentinel_specs.json"))
    d1r6_by_id = {str(row["experiment_id"]): row for row in d1r6_specs}
    d1r6_inventory = _inventory((d1r6 / "raw").glob("*.json.gz"))
    d1r6_fail = Counter()
    for path in sorted((d1r6 / "raw").glob("*.json.gz")):
        result = _raw(path)
        spec = d1r6_by_id.get(str(result.get("experiment_id")))
        event = result.get("action_failure_event") or {}
        if (
            spec is None
            or result.get("spec") != spec
            or event.get("event") != "sequential_cancel_recursive_deadline_stop"
            or int(event.get("task_step", -1)) != 22
            or bool(event.get("failed_candidate_applied"))
            or bool(event.get("plant_advance_after_failure"))
        ):
            raise ValueError("D1R7 independent D1R6 stop changed")
        d1r6_fail[int(spec["s24_sequence_index"])] += 1
    if (
        d1r6_inventory["count"] != int(source["d1r6_raw_count"])
        or d1r6_inventory["digest"] != source["d1r6_raw_inventory_digest"]
        or d1r6_fail != Counter({6: 3, 10: 3, 18: 3})
    ):
        raise ValueError("D1R7 independent D1R6 counts changed")
    return {
        "s24_inventory": s24_inventory,
        "s24_failure_counts": {str(k): s24_fail[k] for k in sorted(s24_fail)},
        "s24_failure_slot_task_steps": {
            f"slot_{slot}_step_{task_step}": count
            for (slot, task_step), count in sorted(s24_failure_slot_steps.items())
        },
        "d1r2_inventory": d1r2_inventory,
        "d1r2_failure_counts": {str(k): d1r2_fail[k] for k in sorted(d1r2_fail)},
        "d1r6_inventory": d1r6_inventory,
        "d1r6_failure_counts": {str(k): d1r6_fail[k] for k in sorted(d1r6_fail)},
        "contexts": contexts,
    }


def _static(project: Path, cfg: Mapping[str, Any], matrix: np.ndarray) -> dict[str, Any]:
    source = cfg["source_contract"]
    path = (
        project
        / source["d1r1_output_relpath"]
        / "stage4_2r3c3t13s24d1r1_geometry_restoring_search_v1.json"
    )
    if _sha(path) != source["d1r1_detailed_sha256"]:
        raise ValueError("D1R7 independent D1R1 hash changed")
    events = list(_json(path).get("event_rows") or [])
    index: dict[tuple[str, str], dict[tuple[int, tuple[str, ...]], Mapping[str, Any]]] = defaultdict(dict)
    for event in events:
        context = (str(event["pair_id"]), str(event["history_member"]))
        event_key = _key(int(event["slot"]), event["desired_coordinate"])
        old = index[context].get(event_key)
        if old is not None and old["actual_coordinate"] != event["actual_coordinate"]:
            raise ValueError("D1R7 independent D1R1 lookup changed")
        index[context][event_key] = event
    pairs = list(map(int, cfg["matrix_contract"]["central_sign_primary_indices"]))
    counts = Counter()
    metrics = []
    for _, lookup in sorted(index.items()):
        actual = np.zeros((24, 16), dtype=float)
        selected = {}
        for row_index, row in enumerate(matrix):
            for slot in range(4):
                event = lookup.get(_key(slot, row[4 * slot : 4 * slot + 4]))
                if event is None:
                    raise ValueError("D1R7 independent static block missing")
                selected[(row_index, slot)] = event
                actual[row_index, 4 * slot : 4 * slot + 4] = event["actual_coordinate"]
                counts["finite"] += 2 * int(bool(event["finite_issue_and_cancellation"]))
                counts["issue"] += int(bool(event["issue_gate_pass"]))
                counts["cancel"] += int(bool(event["cancellation_gate_pass"]))
        for sentinel, primary in enumerate(pairs, start=16):
            for slot in range(4):
                plus = selected[(primary, slot)]
                minus = selected[(sentinel, slot)]
                center = [Decimal(str(value)) for value in plus["issue_center_fields"]]
                pvalue = [Decimal(str(value)) for value in plus["issue_target_fields"]]
                mvalue = [Decimal(str(value)) for value in minus["issue_target_fields"]]
                counts["central"] += int(
                    plus["issue_center_fields"] == minus["issue_center_fields"]
                    and all(p + m == 2 * c for p, m, c in zip(pvalue, mvalue, center))
                )
        row_metrics = _metrics(actual, cfg)
        counts["global"] += int(row_metrics["passed"])
        counts["slot"] += sum(
            rank == 4 and condition <= 3.0 + 1e-12
            for rank, condition in row_metrics["slot_rows"]
        )
        counts["late"] += int(row_metrics["minimum_late_residual"] >= 0.5 - 1e-12)
        metrics.append(row_metrics)
    expected = Counter(
        {
            "finite": 7680,
            "issue": 3840,
            "cancel": 3840,
            "central": 1280,
            "global": 40,
            "slot": 160,
            "late": 40,
        }
    )
    if len(index) != 40 or counts != expected:
        raise ValueError(f"D1R7 independent static gates failed: {dict(counts)}")
    return {
        "counts": dict(counts),
        "maximum_global_condition": max(row["condition"] for row in metrics),
        "maximum_slot_condition": max(
            condition for row in metrics for _, condition in row["slot_rows"]
        ),
        "minimum_late_residual": min(row["minimum_late_residual"] for row in metrics),
    }


def _candidate(
    contexts: Mapping[tuple[str, str], Mapping[str, Any]],
    matrix: np.ndarray,
    cfg: Mapping[str, Any],
) -> dict[str, Any]:
    contract = cfg["candidate_spec_contract"]
    issue = list(map(int, cfg["matrix_contract"]["issue_task_steps"]))
    cancel = list(map(int, cfg["matrix_contract"]["cancel_task_steps"]))
    rows = list(map(int, cfg["matrix_contract"]["candidate_sentinel_row_indices"]))
    specs = []
    for context in sorted(contexts):
        source = contexts[context]
        for row_index in rows:
            spec = copy.deepcopy(source)
            row = matrix[row_index]
            schedule = {}
            for slot, (start, stop) in enumerate(zip(issue, cancel)):
                values = row[4 * slot : 4 * slot + 4]
                schedule[str(start)] = values.tolist()
                schedule[str(stop)] = (-values).tolist()
            seed = {
                "stage": contract["stage"],
                "campaign_identity": contract["campaign_identity"],
                "pair_id": context[0],
                "history_member": context[1],
                "row_index": row_index,
                "requested_matrix_digest": cfg["matrix_contract"]["requested_matrix_digest"],
            }
            experiment_id = "s42r3c3t13s24d1r8_" + _digest(seed)[:20]
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
    return {"count": len(specs), "digest": _digest(specs), "specs": specs}


def run(config_path: Path, project: Path, primary: Path, output: Path) -> dict[str, Any]:
    config_path = config_path.resolve()
    project = project.resolve()
    primary = primary.resolve()
    output = output.resolve()
    if output.exists():
        raise ValueError("D1R7 independent output already exists")
    cfg = _json(config_path)
    if cfg.get("stage") != STAGE:
        raise ValueError("D1R7 independent config identity changed")
    design = project / cfg["design_document"]
    if _sha(design) != cfg["design_document_sha256"]:
        raise ValueError("D1R7 independent design hash changed")
    matrix = _matrix(cfg)
    requested = _metrics(matrix, cfg)
    sources = _source_counts(project, cfg)
    static = _static(project, cfg, matrix)
    candidate = _candidate(sources.pop("contexts"), matrix, cfg)
    primary_candidate_path = primary / "stage4_2r3c3t13s24d1r7_candidate_specs_v1.json"
    primary_detailed_path = primary / "stage4_2r3c3t13s24d1r7_temporal_basis_substitution_preflight_v1.json"
    primary_summary_path = primary / "stage4_2r3c3t13s24d1r7_summary_v1.json"
    primary_manifest_path = primary / "stage4_2r3c3t13s24d1r7_manifest_v1.json"
    primary_candidate = _json(primary_candidate_path)
    primary_detailed = _json(primary_detailed_path)
    primary_summary = _json(primary_summary_path)
    primary_manifest = _json(primary_manifest_path)
    passed = bool(
        requested["passed"]
        and candidate["count"] == 108
        and candidate["digest"] == primary_candidate.get("ordered_spec_digest")
        and candidate["specs"] == primary_candidate.get("spec_rows")
        and primary_detailed.get("requested_matrix_digest") == _digest(matrix.tolist())
        and primary_detailed.get("passed") is True
        and primary_summary.get("passed") is True
        and primary_manifest.get("passed") is True
        and primary_manifest.get("output_files", {}).get(primary_candidate_path.name)
        == _sha(primary_candidate_path)
    )
    if not passed:
        raise ValueError("D1R7 independent comparison failed")
    value = {
        "schema_version": 1,
        "stage": STAGE,
        "classification": "independent_raw_static_matrix_and_spec_recomputation",
        "forensic_recomputation_passed": True,
        "route": cfg["routes"]["pass"],
        "source_authentication": sources,
        "requested_matrix_digest": _digest(matrix.tolist()),
        "requested_matrix_metrics": requested,
        "static_recomputation": static,
        "candidate_spec_count": candidate["count"],
        "candidate_spec_digest": candidate["digest"],
        "primary_output_hashes": {
            primary_detailed_path.name: _sha(primary_detailed_path),
            primary_summary_path.name: _sha(primary_summary_path),
            primary_candidate_path.name: _sha(primary_candidate_path),
            primary_manifest_path.name: _sha(primary_manifest_path),
        },
        "new_raw_ray_gotsc_tsc_controller_or_plant_count": 0,
        "real_sentinel_execution_authorized": False,
        "mpc_or_learning_authorized": False,
    }
    _write(output, value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--primary-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = run(args.config, args.project_root, args.primary_output, args.output)
    print(json.dumps(value, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
