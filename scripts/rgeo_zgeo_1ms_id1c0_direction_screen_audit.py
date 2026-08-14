from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path

import numpy as np


DEFAULT_CONFIG = Path("configs/rgeo_zgeo_1ms_id1c0_direction_screen_audit.json")
SCHEMA = "rgeo-zgeo-1ms-id1c0-direction-screen-audit-result-v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _inside(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    path.relative_to(root.resolve())
    return path


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _target(action: dict) -> np.ndarray:
    if "target_current_a_tsc" in action:
        return np.asarray(action["target_current_a_tsc"], dtype=float)
    return np.asarray(action["target"]["current_a_tsc"], dtype=float)


def _rzi(state: dict) -> np.ndarray:
    return np.asarray([state["r_geo_m"], state["z_geo_m"], state["ip_a"]], dtype=float)


def _same_prefix(actual: dict, reference: dict) -> bool:
    scalar = ("time_ms", "r_geo_m", "z_geo_m", "r_mid_m", "ip_a")
    if any(actual.get(key) != reference.get(key) for key in scalar):
        return False
    for key, size in (("actual_current_a_tsc", 14), ("wire_current_a", 48)):
        left = actual.get(key)
        right = reference.get(key)
        if not isinstance(left, list) or not isinstance(right, list):
            return False
        if len(left) != size or len(right) != size or left != right:
            return False
    return True


def _pure_effect_states(spec: dict) -> list[int]:
    schedule = spec["schedule"]
    if len(schedule) < 2 or schedule[0][0] != "zero" or schedule[1][0] == "zero":
        raise ValueError("first event schedule is not q0 then non-q0")
    event = schedule[1]
    last_issue = 1
    while last_issue + 1 < len(schedule) and schedule[last_issue + 1] == event:
        last_issue += 1
    return list(range(2, last_issue + 2))


def ray_geometry(rays: list[np.ndarray], samples: int) -> dict:
    matrix = np.stack(rays, axis=1)
    angles = sorted(float(math.degrees(math.atan2(v[1], v[0])) % 360.0) for v in rays)
    gaps = [(angles[(index + 1) % len(angles)] - angles[index]) % 360.0 for index in range(len(angles))]
    supports = []
    for theta in np.linspace(0.0, 2.0 * math.pi, samples, endpoint=False):
        direction = np.asarray([math.cos(theta), math.sin(theta)])
        supports.append(max(float(direction @ ray) for ray in rays))
    conditions = []
    for left, right in itertools.combinations(range(len(rays)), 2):
        pair = matrix[:, [left, right]]
        if np.linalg.matrix_rank(pair) == 2:
            conditions.append(float(np.linalg.cond(pair)))
    return {
        "rank": int(np.linalg.matrix_rank(matrix)),
        "angles_deg": angles,
        "maximum_angular_gap_deg": max(gaps),
        "minimum_directional_support_m": min(supports),
        "best_two_ray_condition": min(conditions) if conditions else math.inf,
        "minimum_ray_norm_m": min(float(np.linalg.norm(ray)) for ray in rays),
    }


def _inventory(root: Path, stage: dict) -> tuple[list[dict], str, int]:
    identity = stage["input_inventory"]
    nr2 = _inside(root, identity["nr2r1_root"])
    paths = [nr2 / identity["nr2r1_independent"]]
    for index in identity["pair_indices"]:
        for sign in identity["signs"]:
            paths.append(nr2 / identity["nr2r1_record_pattern"].format(pair_index=index, sign=sign))
    paths.extend([_inside(root, identity["q0_baseline"]), _inside(root, identity["id1b_result"])])
    rows = []
    digest = hashlib.sha256()
    total = 0
    for path in paths:
        relative = path.relative_to(root).as_posix()
        size = path.stat().st_size
        file_hash = sha256(path)
        rows.append({"path": relative, "bytes": size, "sha256": file_hash})
        digest.update(f"{relative}\t{size}\t{file_hash}\n".encode("utf-8"))
        total += size
    return rows, digest.hexdigest(), total


def audit(root: Path, stage: dict, source_revision: str) -> dict:
    if stage.get("holdout_records_read") != 0 or stage.get("model_fit_use") != "forbidden":
        raise ValueError("ID1C0 data-use contract changed")
    inventory, inventory_digest, inventory_bytes = _inventory(root, stage)
    frozen = stage["input_inventory"]
    if len(inventory) != frozen["files"] or inventory_bytes != frozen["bytes"]:
        raise ValueError("input inventory count or bytes changed")
    if inventory_digest != frozen["digest_sha256"]:
        raise ValueError("input inventory digest changed")
    if inventory[-1]["sha256"] != frozen["id1b_result_sha256"]:
        raise ValueError("ID1B result identity changed")

    nr2 = _inside(root, frozen["nr2r1_root"])
    independent = _load(nr2 / frozen["nr2r1_independent"])
    if independent.get("passed") is not True or independent.get("phase") != "development_calibration":
        raise ValueError("NR2R1 development/calibration audit is not accepted")
    q0 = _load(_inside(root, frozen["q0_baseline"]))
    id1b = _load(_inside(root, frozen["id1b_result"]))
    if id1b.get("route") != "ONE_MS_ID1B_PERSISTENT_POSITIVE_SPAN_FAIL_DIRECTION_REDESIGN":
        raise ValueError("ID1B final route changed")
    if id1b.get("model_fit_data_eligible") is not False:
        raise ValueError("ID1B data role changed")

    q0_states = q0["states"]
    q0_issue1 = _target(q0["actions"][1])
    directions = []
    direction_rows = {}
    for index in frozen["pair_indices"]:
        direction_id = f"p{index:02d}"
        records = {}
        for sign in frozen["signs"]:
            record = _load(nr2 / frozen["nr2r1_record_pattern"].format(pair_index=index, sign=sign))
            expected_sign = 1 if sign == "plus" else -1
            spec = record["spec"]
            if spec.get("split") != "development" or spec.get("pair_index") != index or spec.get("sign") != expected_sign:
                raise ValueError(f"{direction_id}:{sign} identity mismatch")
            if not _same_prefix(record["states"][0], q0_states[0]) or not _same_prefix(record["states"][1], q0_states[1]):
                raise ValueError(f"{direction_id}:{sign} prefix mismatch")
            records[sign] = record
        states = _pure_effect_states(records["plus"]["spec"])
        if states != _pure_effect_states(records["minus"]["spec"]):
            raise ValueError(f"{direction_id} signed windows differ")
        outputs = {}
        actions = {}
        for sign, record in records.items():
            outputs[sign] = np.mean([_rzi(record["states"][state]) - _rzi(q0_states[state]) for state in states], axis=0)
            actions[sign] = _target(record["actions"][1]) - q0_issue1
        even = (outputs["plus"] + outputs["minus"]) / 2.0
        odd = (outputs["plus"] - outputs["minus"]) / 2.0
        action_center = (actions["plus"] + actions["minus"]) / 2.0
        action_axis = (actions["plus"] - actions["minus"]) / 2.0
        row = {
            "direction_id": direction_id,
            "schedule_type": records["plus"]["spec"]["schedule_type"],
            "pure_effect_state_indices": states,
            "signed_event_tsc": records["plus"]["spec"]["signed_events_tsc"][0],
            "plus_mean_response_rzi": outputs["plus"].tolist(),
            "minus_mean_response_rzi": outputs["minus"].tolist(),
            "even_mean_response_rzi": even.tolist(),
            "odd_half_difference_rzi": odd.tolist(),
            "maximum_action_axis_component_a": float(np.max(np.abs(action_axis))),
            "maximum_action_center_bias_a": float(np.max(np.abs(action_center))),
            "action_axis_l2_norm_a": float(np.linalg.norm(action_axis)),
            "odd_rz_norm_m": float(np.linalg.norm(odd[:2])),
            "maximum_signed_absolute_ip_response_a": max(abs(float(outputs["plus"][2])), abs(float(outputs["minus"][2]))),
        }
        directions.append(row)
        direction_rows[direction_id] = row

    gates = stage["geometry_gates"]
    candidates = []
    for subset in itertools.combinations(direction_rows, stage["selection"]["subset_size"]):
        rays = []
        max_ip = 0.0
        for direction_id in subset:
            row = direction_rows[direction_id]
            rays.extend([np.asarray(row["plus_mean_response_rzi"][:2]), np.asarray(row["minus_mean_response_rzi"][:2])])
            max_ip = max(max_ip, row["maximum_signed_absolute_ip_response_a"])
        geometry = ray_geometry(rays, gates["directional_support_angle_samples"])
        passed = (
            geometry["rank"] == 2
            and geometry["minimum_ray_norm_m"] >= gates["minimum_each_ray_rz_norm_m"]
            and geometry["maximum_angular_gap_deg"] <= gates["maximum_angular_gap_deg"]
            and geometry["minimum_directional_support_m"] >= gates["minimum_directional_support_m"]
            and geometry["best_two_ray_condition"] <= gates["maximum_best_two_ray_condition"]
            and max_ip <= gates["maximum_absolute_ip_response_a"]
        )
        candidates.append({"directions": list(subset), "geometry": geometry, "maximum_absolute_ip_response_a": max_ip, "passed": passed})
    eligible = [row for row in candidates if row["passed"]]
    eligible.sort(key=lambda row: (-row["geometry"]["minimum_directional_support_m"], row["geometry"]["maximum_angular_gap_deg"], row["geometry"]["best_two_ray_condition"]))
    selected = eligible[0] if eligible else None
    route = stage["routes"]["candidate"] if selected else stage["routes"]["no_candidate"]
    return {
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "audit_config_sha256": sha256(_inside(root, DEFAULT_CONFIG.as_posix())),
        "input_inventory": inventory,
        "input_inventory_sha256": inventory_digest,
        "holdout_records_read": 0,
        "new_tsc_or_plant_advances": 0,
        "new_model_fit_or_training": 0,
        "directions": directions,
        "candidate_subsets": candidates,
        "eligible_subset_count": len(eligible),
        "selected_candidate": selected,
        "passed": selected is not None,
        "route": route,
        "claim_boundary": stage["claim_boundary"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    config = args.config if args.config.is_absolute() else root / args.config
    config = config.resolve()
    config.relative_to(root)
    stage = _load(config)
    result = audit(root, stage, args.source_revision)
    output = args.output if args.output.is_absolute() else root / args.output
    output = output.resolve()
    output.relative_to(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(output)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"route": result["route"], "selected_candidate": result["selected_candidate"], "output": str(output)}, indent=2))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
