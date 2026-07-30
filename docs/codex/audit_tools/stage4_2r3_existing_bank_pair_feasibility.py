#!/usr/bin/env python3
"""Read-only Stage4.2R3 feasibility audit of the certified R1 snapshot bank."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np


R_TOL_M = 0.0005
Z_TOL_M = 0.0005
IP_TOL_A = 2000.0
VELOCITY_TOL_M_PER_S = 0.02
COIL_MAX_TOL_A = 2000.0
COIL_RMS_TOL_A = 500.0
ACTION_MAX_TOL = 1.0e-12
WIRE_MAX_MIN_A = 1000.0
WIRE_RELATIVE_RMS_MIN = 0.05
EXPECTED_CASES = 18
EXPECTED_WIRES = 48
CHECKPOINT_STEP = 20
DT_S = 0.01


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_json_gz(path: Path) -> Any:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def rms(value: np.ndarray) -> float:
    array = np.asarray(value, dtype=float)
    return float(np.sqrt(np.mean(array**2)))


def case_key(result: Mapping[str, Any]) -> tuple[str, int, float]:
    spec = result["spec"]
    return (
        str(spec["target_id"]),
        int(spec.get("action_delay_steps", spec.get("actual_action_delay_steps"))),
        float(spec.get("slew_scale", spec.get("actual_slew_scale"))),
    )


def state_vector(row: Mapping[str, Any], name: str, size: int) -> np.ndarray:
    value = np.asarray(row.get(name), dtype=float).reshape(-1)
    if value.shape != (size,) or not np.all(np.isfinite(value)):
        raise ValueError(f"invalid {name} shape/value: {value.shape}")
    return value


def snapshot_wire_vector(snapshot_dir: Path) -> np.ndarray:
    path = snapshot_dir / "wire_currents.csv"
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, skipinitialspace=True)
        rows = list(reader)
    if not rows or reader.fieldnames is None:
        raise ValueError(f"empty snapshot wire-current CSV: {path}")
    fields = {str(name).strip(): name for name in reader.fieldnames}
    if "cwire(ka)" not in fields:
        raise ValueError(f"snapshot wire-current column missing: {path}")
    vector = np.asarray(
        [float(str(row[fields["cwire(ka)"]]).strip()) * 1000.0 for row in rows],
        dtype=float,
    )
    if vector.shape != (EXPECTED_WIRES,) or not np.all(np.isfinite(vector)):
        raise ValueError(f"invalid snapshot wire vector: {path}")
    return vector


def verify_snapshot(
    result: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], str, np.ndarray]:
    snapshot = result["restart_snapshot"]
    snapshot_dir = Path(str(snapshot["snapshot_dir"])).expanduser().resolve()
    manifest_path = Path(str(snapshot["snapshot_manifest_path"])).expanduser().resolve()
    if not snapshot_dir.is_dir() or not manifest_path.is_file():
        raise FileNotFoundError(f"snapshot or manifest missing: {snapshot_dir}")
    manifest = read_json(manifest_path)
    if not bool(manifest.get("passed")):
        raise ValueError(f"snapshot manifest not passed: {manifest_path}")
    if str(snapshot["snapshot_manifest_digest"]) != str(manifest["digest"]):
        raise ValueError(f"snapshot manifest digest mismatch: {manifest_path}")
    rows: list[dict[str, Any]] = []
    for item in manifest["files"]:
        path = snapshot_dir / str(item["name"])
        if not path.is_file():
            raise FileNotFoundError(f"snapshot payload missing: {path}")
        size = int(path.stat().st_size)
        digest = sha256_file(path)
        if size != int(item["size_bytes"]) or digest != str(item["sha256"]):
            raise ValueError(f"snapshot payload mismatch: {path}")
        rows.append(
            {
                "path": str(path),
                "size_bytes": size,
                "sha256": digest,
                "snapshot_manifest_digest": str(manifest["digest"]),
            }
        )
    return rows, str(manifest["digest"]), snapshot_wire_vector(snapshot_dir)


def endpoint(result: Mapping[str, Any]) -> dict[str, Any]:
    trajectory = list(result["trajectory"])
    if len(trajectory) <= CHECKPOINT_STEP:
        raise ValueError("capture trajectory does not cover checkpoint")
    now = trajectory[CHECKPOINT_STEP]
    previous = trajectory[CHECKPOINT_STEP - 1]
    wire = state_vector(now, "wire_currents_a", EXPECTED_WIRES)
    return {
        "target_id": case_key(result)[0],
        "delay": case_key(result)[1],
        "slew": case_key(result)[2],
        "experiment_id": str(result["experiment_id"]),
        "R": float(now["R"]),
        "Z": float(now["Z"]),
        "Ip": float(now["Ip"]),
        "vR": (float(now["R"]) - float(previous["R"])) / DT_S,
        "vZ": (float(now["Z"]) - float(previous["Z"])) / DT_S,
        "coil": state_vector(now, "currents_a_tsc", 14),
        "action": state_vector(now, "action_norm_tsc", 14),
        "wire": wire,
        "wire_rms": rms(wire),
        "snapshot_time_ms": int(result["restart_snapshot"]["snapshot_time_ms"]),
        "snapshot_manifest_digest": str(
            result["restart_snapshot"]["snapshot_manifest_digest"]
        ),
    }


def pair_metrics(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    coil_diff = np.asarray(left["coil"]) - np.asarray(right["coil"])
    action_diff = np.asarray(left["action"]) - np.asarray(right["action"])
    wire_diff = np.asarray(left["wire"]) - np.asarray(right["wire"])
    denominator = max(
        1.0, 0.5 * (float(left["wire_rms"]) + float(right["wire_rms"]))
    )
    metrics = {
        "R_abs_difference_m": abs(float(left["R"]) - float(right["R"])),
        "Z_abs_difference_m": abs(float(left["Z"]) - float(right["Z"])),
        "Ip_abs_difference_A": abs(float(left["Ip"]) - float(right["Ip"])),
        "vR_abs_difference_m_per_s": abs(float(left["vR"]) - float(right["vR"])),
        "vZ_abs_difference_m_per_s": abs(float(left["vZ"]) - float(right["vZ"])),
        "coil_max_abs_difference_A": float(np.max(np.abs(coil_diff))),
        "coil_rms_difference_A": rms(coil_diff),
        "action_max_abs_difference": float(np.max(np.abs(action_diff))),
        "wire_max_abs_difference_A": float(np.max(np.abs(wire_diff))),
        "wire_rms_difference_A": rms(wire_diff),
        "wire_relative_rms_difference": rms(wire_diff) / denominator,
    }
    visible_ratios = [
        metrics["R_abs_difference_m"] / R_TOL_M,
        metrics["Z_abs_difference_m"] / Z_TOL_M,
        metrics["Ip_abs_difference_A"] / IP_TOL_A,
        metrics["vR_abs_difference_m_per_s"] / VELOCITY_TOL_M_PER_S,
        metrics["vZ_abs_difference_m_per_s"] / VELOCITY_TOL_M_PER_S,
        metrics["coil_max_abs_difference_A"] / COIL_MAX_TOL_A,
        metrics["coil_rms_difference_A"] / COIL_RMS_TOL_A,
        metrics["action_max_abs_difference"] / ACTION_MAX_TOL,
    ]
    visible_pass = bool(max(visible_ratios) <= 1.0)
    hidden_pass = bool(
        metrics["wire_max_abs_difference_A"] >= WIRE_MAX_MIN_A
        and metrics["wire_relative_rms_difference"] >= WIRE_RELATIVE_RMS_MIN
    )
    same_future_semantics = bool(
        left["target_id"] == right["target_id"]
        and left["delay"] == right["delay"]
        and math.isclose(float(left["slew"]), float(right["slew"]), abs_tol=1e-12)
    )
    return {
        "left_experiment_id": left["experiment_id"],
        "right_experiment_id": right["experiment_id"],
        "left_target_id": left["target_id"],
        "right_target_id": right["target_id"],
        "left_delay": left["delay"],
        "right_delay": right["delay"],
        "left_slew": left["slew"],
        "right_slew": right["slew"],
        "same_checkpoint_step": True,
        "same_snapshot_clock": left["snapshot_time_ms"] == right["snapshot_time_ms"],
        "same_future_semantics": same_future_semantics,
        **metrics,
        "visible_max_normalized_ratio": max(visible_ratios),
        "visible_match_pass": visible_pass,
        "hidden_separation_pass": hidden_pass,
        "valid_r3_existing_pair": bool(
            same_future_semantics
            and left["snapshot_time_ms"] == right["snapshot_time_ms"]
            and visible_pass
            and hidden_pass
        ),
    }


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    records = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not records:
        path.write_text("", encoding="utf-8")
        return
    fields = list(records[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-r1-run", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    source = args.source_r1_run.expanduser().resolve()
    output = args.output_dir.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    raw_dir = source / "stage4_2r1_plant_checkpoint_capture" / "raw"
    raw_paths = sorted(raw_dir.glob("*.json.gz"))
    if len(raw_paths) != EXPECTED_CASES:
        raise ValueError(f"expected {EXPECTED_CASES} capture raws, got {len(raw_paths)}")

    inventory: list[dict[str, Any]] = []
    endpoints: list[dict[str, Any]] = []
    groups: dict[tuple[str, int, float], list[str]] = {}
    snapshot_digests: set[str] = set()
    for raw_path in raw_paths:
        result = read_json_gz(raw_path)
        if not bool(result.get("success")):
            raise ValueError(f"capture raw is not successful: {raw_path}")
        key = case_key(result)
        groups.setdefault(key, []).append(str(result["experiment_id"]))
        raw_hash = sha256_file(raw_path)
        inventory.append(
            {
                "path": str(raw_path),
                "size_bytes": int(raw_path.stat().st_size),
                "sha256": raw_hash,
                "kind": "capture_raw",
            }
        )
        endpoint_row = endpoint(result)
        snapshot_rows, snapshot_digest, snapshot_wire = verify_snapshot(result)
        if not np.array_equal(snapshot_wire, np.asarray(endpoint_row["wire"])):
            raise ValueError(f"snapshot wire vector differs from capture raw: {raw_path}")
        snapshot_digests.add(snapshot_digest)
        inventory.extend({**row, "kind": "snapshot_payload"} for row in snapshot_rows)
        manifest_path = Path(
            str(result["restart_snapshot"]["snapshot_manifest_path"])
        ).expanduser().resolve()
        inventory.append(
            {
                "path": str(manifest_path),
                "size_bytes": int(manifest_path.stat().st_size),
                "sha256": sha256_file(manifest_path),
                "kind": "snapshot_manifest",
            }
        )
        endpoints.append(endpoint_row)

    endpoint_public = [
        {key: value for key, value in row.items() if key not in {"coil", "action", "wire"}}
        for row in endpoints
    ]
    all_pairs = [
        pair_metrics(left, right)
        for left, right in itertools.combinations(endpoints, 2)
        if left["target_id"] == right["target_id"]
    ]
    all_pairs.sort(
        key=lambda row: (
            float(row["visible_max_normalized_ratio"]),
            -float(row["wire_relative_rms_difference"]),
            str(row["left_experiment_id"]),
            str(row["right_experiment_id"]),
        )
    )
    within_key_pair_count = sum(
        len(values) * (len(values) - 1) // 2 for values in groups.values()
    )
    valid_pairs = [row for row in all_pairs if row["valid_r3_existing_pair"]]
    thresholds = {
        "R_abs_difference_m_max": R_TOL_M,
        "Z_abs_difference_m_max": Z_TOL_M,
        "Ip_abs_difference_A_max": IP_TOL_A,
        "vR_abs_difference_m_per_s_max": VELOCITY_TOL_M_PER_S,
        "vZ_abs_difference_m_per_s_max": VELOCITY_TOL_M_PER_S,
        "coil_max_abs_difference_A_max": COIL_MAX_TOL_A,
        "coil_rms_difference_A_max": COIL_RMS_TOL_A,
        "action_max_abs_difference_max": ACTION_MAX_TOL,
        "wire_max_abs_difference_A_min": WIRE_MAX_MIN_A,
        "wire_relative_rms_difference_min": WIRE_RELATIVE_RMS_MIN,
    }
    audit = {
        "schema_version": 1,
        "stage": "Stage4.2R3-preflight",
        "contract": "r42r3_preregistered_existing_bank_pair_feasibility_v1",
        "source_r1_run": str(source),
        "thresholds": thresholds,
        "capture_raw_count": len(raw_paths),
        "unique_case_key_count": len(groups),
        "case_history_counts": [
            {
                "target_id": key[0],
                "delay": key[1],
                "slew": key[2],
                "history_count": len(values),
                "experiment_ids": values,
            }
            for key, values in sorted(groups.items())
        ],
        "snapshot_manifest_count": len(snapshot_digests),
        "snapshot_payload_count": sum(row["kind"] == "snapshot_payload" for row in inventory),
        "inventory_file_count": len(inventory),
        "inventory_total_bytes": sum(int(row["size_bytes"]) for row in inventory),
        "inventory_digest": canonical_digest(inventory),
        "within_same_future_semantics_pair_count": within_key_pair_count,
        "same_target_cross_key_diagnostic_pair_count": len(all_pairs),
        "valid_existing_r3_pair_count": len(valid_pairs),
        "state_generation_required": len(valid_pairs) < 2,
        "passed_as_read_only_inventory": True,
        "scientific_r3_gate_run": False,
        "conclusion": (
            "Existing R1/R2 bank has one history per target/delay/slew key; "
            "a dedicated authentic state-generation phase is required."
        ),
    }
    (output / "audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (output / "endpoints.json").write_text(
        json.dumps(endpoint_public, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (output / "inventory.json").write_text(
        json.dumps(inventory, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (output / "cross_key_pair_diagnostics.json").write_text(
        json.dumps(all_pairs, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    write_csv(output / "cross_key_pair_diagnostics.csv", all_pairs)
    print(json.dumps(audit, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
