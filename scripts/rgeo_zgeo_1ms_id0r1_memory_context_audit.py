from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


SCHEMA = "rgeo-zgeo-1ms-id0r1-memory-context-audit-result-v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _inside(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    path.relative_to(root)
    return path


def _turning_points(values: list[float]) -> int:
    return sum(
        (values[index] - values[index - 1])
        * (values[index + 1] - values[index])
        < 0.0
        for index in range(1, len(values) - 1)
    )


def _sign_changes(values: list[float]) -> int:
    return sum(a * b < 0.0 for a, b in zip(values, values[1:]))


def audit(repo_root: Path, config_path: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    config_path = config_path.resolve()
    config_path.relative_to(repo_root)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config["plant_advances"] != 0 or config["model_fit_or_training"]:
        raise ValueError("audit must remain zero-plant and zero-fit")
    if config["holdout_records_read"] != 0:
        raise ValueError("holdout use is forbidden")

    records: dict[str, dict[str, Any]] = {}
    identities: dict[str, str] = {}
    for spec in config["records"]:
        path = _inside(repo_root, spec["path"])
        actual = _sha256(path)
        if actual != spec["sha256"]:
            raise ValueError(f"evidence hash mismatch: {spec['path']}")
        records[path.stem] = json.loads(path.read_text(encoding="utf-8"))
        identities[spec["path"]] = actual

    baselines = [records["baseline_q0_r0"], records["baseline_q0_r1"]]
    arms = {name: row for name, row in records.items() if name.startswith("early_")}
    if len(arms) != 6 or any(len(row["states"]) != 33 for row in records.values()):
        raise ValueError("unexpected ID0T1 compact matrix")

    def baseline(index: int, key: str) -> float:
        return sum(float(row["states"][index][key]) for row in baselines) / 2.0

    start, stop = config["response_state_range"]
    arm_metrics: dict[str, Any] = {}
    for name, row in sorted(arms.items()):
        response = []
        for index in range(start, stop + 1):
            state = row["states"][index]
            response.append(
                {
                    "state_index": index,
                    "r_mm": (float(state["r_geo_m"]) - baseline(index, "r_geo_m")) * 1000.0,
                    "z_mm": (float(state["z_geo_m"]) - baseline(index, "z_geo_m")) * 1000.0,
                    "ip_a": float(state["ip_a"]) - baseline(index, "ip_a"),
                }
            )
        norms = [math.hypot(item["r_mm"], item["z_mm"]) for item in response]
        peak = max(norms)
        windows = {}
        for first, last in config["late_windows"]:
            selected = [value for item, value in zip(response, norms) if first <= item["state_index"] <= last]
            windows[f"states_{first}_{last}"] = {
                "maximum_rz_norm_mm": max(selected),
                "mean_rz_norm_mm": sum(selected) / len(selected),
                "maximum_peak_fraction": max(selected) / peak,
            }
        peak_index = response[norms.index(peak)]["state_index"]
        arm_metrics[name] = {
            "peak_rz_norm_mm": peak,
            "peak_state_index": peak_index,
            "terminal_rz_norm_mm": norms[-1],
            "terminal_peak_fraction": norms[-1] / peak,
            "terminal_abs_ip_a": abs(response[-1]["ip_a"]),
            "rz_norm_turning_points": _turning_points(norms),
            "r_sign_changes": _sign_changes([item["r_mm"] for item in response]),
            "z_sign_changes": _sign_changes([item["z_mm"] for item in response]),
            "late_windows": windows,
        }

    same_time = {}
    for index in config["same_time_state_indices"]:
        points = []
        for row in arms.values():
            state = row["states"][index]
            points.append(
                (
                    (float(state["r_geo_m"]) - baseline(index, "r_geo_m")) * 1000.0,
                    (float(state["z_geo_m"]) - baseline(index, "z_geo_m")) * 1000.0,
                    float(state["ip_a"]) - baseline(index, "ip_a"),
                )
            )
        same_time[str(index)] = {
            "r_span_mm": max(item[0] for item in points) - min(item[0] for item in points),
            "z_span_mm": max(item[1] for item in points) - min(item[1] for item in points),
            "ip_span_a": max(item[2] for item in points) - min(item[2] for item in points),
        }

    scales = config["descriptive_visible_match_scales"]
    nearest = None
    arm_rows = list(arms.values())
    for left_index, left in enumerate(arm_rows):
        for right in arm_rows[left_index + 1 :]:
            for left_state in range(start, stop + 1):
                a = left["states"][left_state]
                for right_state in range(start, stop + 1):
                    if left_state == right_state:
                        continue
                    b = right["states"][right_state]
                    dr = abs(float(a["r_geo_m"]) - float(b["r_geo_m"])) * 1000.0
                    dz = abs(float(a["z_geo_m"]) - float(b["z_geo_m"])) * 1000.0
                    dip = abs(float(a["ip_a"]) - float(b["ip_a"]))
                    score = (
                        (dr / scales["r_geo_mm"]) ** 2
                        + (dz / scales["z_geo_mm"]) ** 2
                        + (dip / scales["ip_a"]) ** 2
                    )
                    candidate = {
                        "normalized_squared_distance": score,
                        "r_difference_mm": dr,
                        "z_difference_mm": dz,
                        "ip_difference_a": dip,
                        "left_rollout": left["rollout_id"],
                        "left_state_index": left_state,
                        "right_rollout": right["rollout_id"],
                        "right_state_index": right_state,
                    }
                    if nearest is None or score < nearest["normalized_squared_distance"]:
                        nearest = candidate

    maximum_late = max(
        metrics["late_windows"]["states_21_32"]["maximum_rz_norm_mm"]
        for metrics in arm_metrics.values()
    )
    maximum_terminal = max(metrics["terminal_rz_norm_mm"] for metrics in arm_metrics.values())
    result = {
        "schema_version": SCHEMA,
        "audit_id": config["audit_id"],
        "config_sha256": _sha256(config_path),
        "evidence_sha256": identities,
        "counters": {
            "plant_advances": 0,
            "server_accesses": 0,
            "models_fit_or_trained": 0,
            "holdout_records_read": 0,
            "compact_trajectories": len(records),
        },
        "arm_metrics": arm_metrics,
        "same_time_response_spans": same_time,
        "nearest_different_time_different_history_visible_pair": nearest,
        "summary": {
            "maximum_late_window_rz_norm_mm": maximum_late,
            "maximum_terminal_rz_norm_mm": maximum_terminal,
            "all_terminal_absolute_responses_below_0p05mm": maximum_terminal <= 0.05,
            "late_response_is_nonmonotone": any(
                metrics["rz_norm_turning_points"] > 0 for metrics in arm_metrics.values()
            ),
            "single_endpoint_is_not_a_memory_order_certificate": True,
            "existing_records_supply_only_one_source_anchor": True,
            "position_time_history_factorization_supported": False,
            "literal_finite_tail_extinction_required_for_next_model": False,
            "prospective_model_memory_family": "stable_low_order_persistent_and_damped_oscillatory_latent",
            "next_experiment": "fresh_small_hfs_context_anchor_pilot_before_model_fit",
        },
        "data_role": config["input_role"],
        "route": config["route"],
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/rgeo_zgeo_1ms_id0r1_memory_context_audit.json"),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    config = args.config if args.config.is_absolute() else root / args.config
    result = audit(root, config)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        output = args.output if args.output.is_absolute() else root / args.output
        output.resolve().relative_to(root)
        if output.exists():
            raise FileExistsError(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
