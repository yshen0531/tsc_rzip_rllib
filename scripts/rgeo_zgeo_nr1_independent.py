#!/usr/bin/env python3
"""Independent raw audit for the four frozen NR1 rollouts."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tsc_rzip_rllib.control.rgeo_zgeo_contract import RGeoZGeoSignal  # noqa: E402
from tsc_rzip_rllib.core.gfile import parse_gfile, read_coil_currents_csv  # noqa: E402
from tsc_rzip_rllib.core.runner import TSCConfig  # noqa: E402


DEFAULT_CONFIG = REPO_ROOT / "stage1_1_runs" / "stage1_1_svd234_strict_validation_100ms_20260718_025916" / "env_config.resolved.json"
ROLLOUTS = ("hold_primary", "hold_replay", "pulse_primary", "pulse_replay")
TIMES_MS = tuple(range(1100, 1190, 10))


def _format_card15(value: float) -> str:
    result = f"{float(value):.3E}"
    return result[:10] if len(result) > 10 else result.ljust(10)


def _target_fields(path: Path) -> tuple[str, ...]:
    result: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line[:10].strip() == "15":
            result.append(line[30:40])
    if len(result) != 14:
        raise ValueError(f"expected 14 Card15 rows in {path}, got {len(result)}")
    return tuple(result)


def _wire_values(path: Path, column_name: str, raw_to_a: float) -> tuple[float, ...]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, skipinitialspace=True)
        fields = {str(field).strip(): field for field in (reader.fieldnames or [])}
        if column_name not in fields:
            raise ValueError(f"missing {column_name!r} in {path}")
        original = fields[column_name]
        values = tuple(float(row[original]) * raw_to_a for row in reader if str(row[original]).strip())
    if not values or not all(math.isfinite(value) for value in values):
        raise ValueError(f"invalid wire current vector in {path}")
    return values


def _state(folder: Path, cfg: TSCConfig) -> dict[str, Any]:
    required = ("geqdsk", "coil_currents.csv", "wire_currents.csv", "sprsina", "inputa")
    missing = [name for name in required if not (folder / name).is_file()]
    if missing:
        raise FileNotFoundError(f"{folder} is missing {missing}")
    gfile = parse_gfile(folder / "geqdsk")
    time_ms = int(folder.name.rstrip("ms"))
    signal = RGeoZGeoSignal.from_tsc_state(
        {"time_ms": time_ms, "Ip": float(gfile["ip"]), "gfile": gfile, "abnormal": False}
    )
    currents_kat = read_coil_currents_csv(folder / "coil_currents.csv")
    currents_a = tuple(float(value) * 1000.0 / float(turns) for value, turns in zip(currents_kat, cfg.turns_tsc))
    if len(currents_a) != 14 or not all(math.isfinite(value) for value in currents_a):
        raise ValueError(f"invalid coil current vector in {folder}")
    abnormal = "abnormal exit" in (folder / "outputa").read_text(errors="ignore").lower() if (folder / "outputa").is_file() else False
    return {
        "time_ms": time_ms,
        "r_geo_m": signal.boundary.r_geo_m,
        "z_geo_m": signal.boundary.z_geo_m,
        "r_mid_m": signal.limiter.r_mid_m,
        "r_inner_m": signal.limiter.r_inner_m,
        "r_outer_m": signal.limiter.r_outer_m,
        "ip_a": signal.ip_a,
        "actual_current_a_tsc": currents_a,
        "wire_current_a": _wire_values(folder / "wire_currents.csv", cfg.vessel_current_column, cfg.vessel_current_raw_to_a),
        "abnormal": abnormal,
    }


def _expected_targets(source_current_a: Sequence[float], cfg: TSCConfig, prefix: str) -> tuple[tuple[str, ...], ...]:
    turns = tuple(float(value) for value in cfg.turns_tsc)
    q0_fields = tuple(_format_card15(current * turn / 1000.0) for current, turn in zip(source_current_a, turns))
    q0_a = tuple(float(field.strip()) * 1000.0 / turn for field, turn in zip(q0_fields, turns))
    signs = tuple(1.0 if index % 2 == 0 else -1.0 for index in range(14))
    pulse_fields = tuple(
        _format_card15((current + sign * 0.05 * cfg.max_delta_current_a_per_step) * turn / 1000.0)
        for current, sign, turn in zip(q0_a, signs, turns)
    )
    return ((pulse_fields,) if prefix == "pulse" else (q0_fields,)) + (q0_fields,) * (7 if prefix == "pulse" else 7)


def _maximum_vector_difference(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        return math.inf
    return max((abs(float(a) - float(b)) for a, b in zip(left, right)), default=0.0)


def audit(config_path: Path, output_dir: Path, source_revision: str) -> dict[str, Any]:
    cfg = TSCConfig.from_json(config_path)
    failures: list[str] = []
    records: dict[str, list[dict[str, Any]]] = {}
    action_checks = 0
    safety_checks = 0
    source_reference: dict[str, Any] | None = None
    for rollout in ROLLOUTS:
        rollout_dir = output_dir / "rollouts" / rollout
        states: list[dict[str, Any]] = []
        try:
            states = [_state(rollout_dir / f"{time_ms}ms", cfg) for time_ms in TIMES_MS]
        except Exception as exc:
            failures.append(f"RAW_PARSE:{rollout}:{type(exc).__name__}:{exc}")
            records[rollout] = states
            continue
        records[rollout] = states
        source = states[0]
        if source_reference is None:
            source_reference = source
        prefix = "pulse" if rollout.startswith("pulse") else "hold"
        expected = _expected_targets(source["actual_current_a_tsc"], cfg, prefix)
        if len(expected) != 8:
            failures.append(f"INTERNAL_TARGET_COUNT:{rollout}")
        for index, (time_ms, target_fields) in enumerate(zip(TIMES_MS[:-1], expected)):
            observed = _target_fields(rollout_dir / f"{time_ms}ms" / "inputa")
            action_checks += 1
            if observed != target_fields:
                failures.append(f"CARD15_TARGET:{rollout}:{index}")
            target_a = tuple(float(field.strip()) * 1000.0 / float(turn) for field, turn in zip(observed, cfg.turns_tsc))
            if any(value < lower - 1e-9 or value > upper + 1e-9 for value, lower, upper in zip(target_a, cfg.min_current_a_tsc, cfg.max_current_a_tsc)):
                failures.append(f"TARGET_CURRENT:{rollout}:{index}")
            delta = _maximum_vector_difference(states[index]["actual_current_a_tsc"], target_a)
            if delta > cfg.max_delta_current_a_per_step + 1e-9:
                failures.append(f"TARGET_SLEW:{rollout}:{index}")
        for index, state in enumerate(states):
            safety_checks += 1
            if state["abnormal"]:
                failures.append(f"ABNORMAL:{rollout}:{index}")
            if not state["r_inner_m"] <= state["r_geo_m"] <= state["r_outer_m"]:
                failures.append(f"LIMITER_CENTER:{rollout}:{index}")
            if abs(state["r_geo_m"] - source["r_geo_m"]) > 0.05:
                failures.append(f"R_LIMIT:{rollout}:{index}")
            if abs(state["z_geo_m"] - source["z_geo_m"]) > 0.05:
                failures.append(f"Z_LIMIT:{rollout}:{index}")
            if math.copysign(1.0, state["ip_a"]) != math.copysign(1.0, source["ip_a"]):
                failures.append(f"IP_SIGN:{rollout}:{index}")
            if abs(state["ip_a"] - source["ip_a"]) > 0.10 * abs(source["ip_a"]):
                failures.append(f"IP_LIMIT:{rollout}:{index}")
            if any(value < lower - 1e-9 or value > upper + 1e-9 for value, lower, upper in zip(state["actual_current_a_tsc"], cfg.min_current_a_tsc, cfg.max_current_a_tsc)):
                failures.append(f"ACTUAL_CURRENT:{rollout}:{index}")
    maximum = {"geometry_m": 0.0, "ip_a": 0.0, "coil_current_a": 0.0, "wire_current_a": 0.0}
    for prefix in ("hold", "pulse"):
        left = records.get(f"{prefix}_primary", [])
        right = records.get(f"{prefix}_replay", [])
        if len(left) != 9 or len(right) != 9:
            failures.append(f"REPLAY_STATE_COUNT:{prefix}")
            continue
        for index, (a, b) in enumerate(zip(left, right)):
            if a["time_ms"] != b["time_ms"]:
                failures.append(f"REPLAY_TIME:{prefix}:{index}")
            geometry = max(abs(a[key] - b[key]) for key in ("r_geo_m", "z_geo_m", "r_mid_m"))
            ip = abs(a["ip_a"] - b["ip_a"])
            coil = _maximum_vector_difference(a["actual_current_a_tsc"], b["actual_current_a_tsc"])
            wire = _maximum_vector_difference(a["wire_current_a"], b["wire_current_a"])
            maximum["geometry_m"] = max(maximum["geometry_m"], geometry)
            maximum["ip_a"] = max(maximum["ip_a"], ip)
            maximum["coil_current_a"] = max(maximum["coil_current_a"], coil)
            maximum["wire_current_a"] = max(maximum["wire_current_a"], wire)
    if maximum["geometry_m"] > 1e-12:
        failures.append("REPLAY_GEOMETRY_TOLERANCE")
    if maximum["ip_a"] > 1e-9:
        failures.append("REPLAY_IP_TOLERANCE")
    if maximum["coil_current_a"] > 1e-9:
        failures.append("REPLAY_COIL_TOLERANCE")
    if maximum["wire_current_a"] > 1e-9:
        failures.append("REPLAY_WIRE_TOLERANCE")
    unique = list(dict.fromkeys(failures))
    result = {
        "schema_version": "rgeo-zgeo-nr1-independent-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_revision": source_revision,
        "intended_use": "interface_validation",
        "passed": not unique,
        "route": "FIXED_1100MS_PREFIX_REPLAY_INDEPENDENT_PASS" if not unique else "NR1_INDEPENDENT_FAIL",
        "failures": unique,
        "raw_rollout_count": sum(len(records.get(name, [])) == 9 for name in ROLLOUTS),
        "raw_state_count": sum(len(value) for value in records.values()),
        "plant_advance_count": action_checks,
        "action_checks": action_checks,
        "safety_state_checks": safety_checks,
        "maximum_absolute_difference": maximum,
        "source_signal": None if source_reference is None else {
            key: source_reference[key] for key in ("r_geo_m", "z_geo_m", "r_mid_m", "ip_a")
        },
        "claim_boundary": "fixed 1100ms exact-prefix replay only; not arbitrary-state Oracle or control",
    }
    destination = output_dir / "independent_audit.json"
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite {destination}")
    destination.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    result = audit(args.config.resolve(), args.output_dir.resolve(), args.source_revision)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
