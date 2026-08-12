#!/usr/bin/env python3
"""Independent raw/spec/safety audit for NR2 collection phases."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.rgeo_zgeo_nr1_independent import _state, _target_fields  # noqa: E402
from scripts.rgeo_zgeo_nr2_collect import _read_source_state, _targets  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_nr2_spec import (  # noqa: E402
    NR2_CAMPAIGN_ID,
    NR2_CONTRACT_VERSION,
    build_nr2_specs,
    validate_nr2_specs,
)
from tsc_rzip_rllib.core.runner import TSCConfig  # noqa: E402


DEFAULT_CONFIG = REPO_ROOT / "stage1_1_runs" / "stage1_1_svd234_strict_validation_100ms_20260718_025916" / "env_config.resolved.json"
TIMES_MS = tuple(range(1100, 1190, 10))


def audit(config_path: Path, campaign_dir: Path, phase: str, source_revision: str) -> dict[str, Any]:
    destination = campaign_dir / f"{phase}_independent.json"
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite {destination}")
    cfg = TSCConfig.from_json(config_path)
    source = _read_source_state(cfg)
    source_r = (min(source["gfile"]["boundary_R"]) + max(source["gfile"]["boundary_R"])) / 2.0
    source_z = (min(source["gfile"]["boundary_Z"]) + max(source["gfile"]["boundary_Z"])) / 2.0
    source_ip = float(source["Ip"])
    allowed = {"development", "calibration"} if phase == "development_calibration" else {"holdout"}
    specs = [spec for spec in build_nr2_specs() if spec.split in allowed]
    spec_gate = validate_nr2_specs(build_nr2_specs())
    failures: list[str] = []
    state_checks = 0
    action_checks = 0
    raw_files = 0
    completed = 0
    maximum = {"r_displacement_m": 0.0, "z_displacement_m": 0.0, "ip_fraction": 0.0,
               "target_increment_a": 0.0}
    for spec in specs:
        folder = campaign_dir / "rollouts" / spec.trajectory_id
        try:
            states = [_state(folder / f"{time_ms}ms", cfg) for time_ms in TIMES_MS]
        except Exception as exc:
            failures.append(f"RAW_PARSE:{spec.trajectory_id}:{type(exc).__name__}:{exc}")
            continue
        completed += 1
        raw_files += sum(1 for time_ms in TIMES_MS for name in ("geqdsk", "inputa", "sprsina", "coil_currents.csv", "wire_currents.csv") if (folder / f"{time_ms}ms" / name).is_file())
        targets = _targets(cfg, np.asarray(source["currents_a_tsc"]), spec.normalized_actions_tsc)
        for index, target in enumerate(targets):
            observed_fields = _target_fields(folder / f"{TIMES_MS[index]}ms" / "inputa")
            action_checks += 1
            if observed_fields != target.serialized_card15_fields:
                failures.append(f"CARD15:{spec.trajectory_id}:{index}")
            observed_a = np.asarray([float(value.strip()) for value in observed_fields]) * 1000.0 / cfg.turns_tsc
            current = np.asarray(states[index]["actual_current_a_tsc"])
            increment = float(np.max(np.abs(observed_a - current)))
            maximum["target_increment_a"] = max(maximum["target_increment_a"], increment)
            if increment > cfg.max_delta_current_a_per_step + 1e-9:
                failures.append(f"SLEW:{spec.trajectory_id}:{index}")
            if np.any(observed_a < cfg.min_current_a_tsc - 1e-9) or np.any(observed_a > cfg.max_current_a_tsc + 1e-9):
                failures.append(f"TARGET_CURRENT:{spec.trajectory_id}:{index}")
        for index, state in enumerate(states):
            state_checks += 1
            r_shift = abs(float(state["r_geo_m"]) - source_r)
            z_shift = abs(float(state["z_geo_m"]) - source_z)
            ip_fraction = abs(float(state["ip_a"]) - source_ip) / abs(source_ip)
            maximum["r_displacement_m"] = max(maximum["r_displacement_m"], r_shift)
            maximum["z_displacement_m"] = max(maximum["z_displacement_m"], z_shift)
            maximum["ip_fraction"] = max(maximum["ip_fraction"], ip_fraction)
            if state["abnormal"]:
                failures.append(f"ABNORMAL:{spec.trajectory_id}:{index}")
            if not state["r_inner_m"] <= state["r_geo_m"] <= state["r_outer_m"]:
                failures.append(f"LIMITER:{spec.trajectory_id}:{index}")
            if r_shift > 0.05:
                failures.append(f"R_LIMIT:{spec.trajectory_id}:{index}")
            if z_shift > 0.05:
                failures.append(f"Z_LIMIT:{spec.trajectory_id}:{index}")
            if math.copysign(1.0, state["ip_a"]) != math.copysign(1.0, source_ip) or ip_fraction > 0.10:
                failures.append(f"IP_LIMIT:{spec.trajectory_id}:{index}")
            actual = np.asarray(state["actual_current_a_tsc"])
            if np.any(actual < cfg.min_current_a_tsc - 1e-9) or np.any(actual > cfg.max_current_a_tsc + 1e-9):
                failures.append(f"ACTUAL_CURRENT:{spec.trajectory_id}:{index}")
        record_path = campaign_dir / "records" / f"{spec.trajectory_id}.json"
        try:
            record = json.loads(record_path.read_text(encoding="utf-8"))
            if record["spec"] != spec.to_dict() or record["plant_advances"] != 8 or record["passed"] is not True:
                failures.append(f"RECORD:{spec.trajectory_id}")
        except Exception as exc:
            failures.append(f"RECORD_PARSE:{spec.trajectory_id}:{type(exc).__name__}:{exc}")
    expected_advances = len(specs) * 8
    if completed != len(specs) or action_checks != expected_advances or state_checks != len(specs) * 9:
        failures.append("COUNT_GATE")
    unique = list(dict.fromkeys(failures))
    result = {
        "schema_version": f"{NR2_CONTRACT_VERSION}-independent-v1",
        "campaign_id": NR2_CAMPAIGN_ID,
        "phase": phase,
        "source_revision": source_revision,
        "passed": not unique,
        "route": f"NR2_{phase.upper()}_INDEPENDENT_PASS" if not unique else "NR2_INDEPENDENT_FAIL",
        "failures": unique,
        "expected_trajectories": len(specs),
        "completed_trajectories": completed,
        "plant_advances": action_checks,
        "state_checks": state_checks,
        "raw_required_file_count": raw_files,
        "maximum": maximum,
        "spec_gate": spec_gate,
    }
    destination.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--campaign-dir", type=Path, required=True)
    parser.add_argument("--phase", choices=("development_calibration", "holdout"), required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    result = audit(args.config.resolve(), args.campaign_dir.resolve(), args.phase, args.source_revision)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
