#!/usr/bin/env python3
"""Structurally independent raw-directory audit for 1 ms NR1."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal
import json
import math
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    NR1_1MS_CONTRACT_VERSION, NR1_1MS_ROLLOUTS, RETURN_EQUIVALENCE_A,
    assert_exact_slew, build_frozen_one_ms_prefixes, card15_target_decimal_a,
    decimal_single_turn_currents_a,
)
from tsc_rzip_rllib.control.rgeo_zgeo_contract import RGeoZGeoSignal  # noqa: E402
from tsc_rzip_rllib.core.gfile import parse_gfile, read_coil_currents_csv  # noqa: E402
from tsc_rzip_rllib.core.runner import TSCConfig  # noqa: E402


def _fields(path: Path) -> tuple[str, ...]:
    values = tuple(line[30:40] for line in path.read_text(encoding="utf-8").splitlines() if line[:10].strip() == "15")
    if len(values) != 14:
        raise ValueError(f"expected 14 Card15 rows in {path}, got {len(values)}")
    return values


def _wire(path: Path, cfg: TSCConfig) -> tuple[float, ...]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, skipinitialspace=True)
        names = {str(value).strip(): value for value in (reader.fieldnames or [])}
        key = names[cfg.vessel_current_column]
        values = tuple(float(row[key]) * cfg.vessel_current_raw_to_a for row in reader if str(row[key]).strip())
    if not values or not all(math.isfinite(value) for value in values):
        raise ValueError("invalid wire current vector")
    return values


def _state(folder: Path, cfg: TSCConfig) -> dict[str, Any]:
    for name in ("inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv", "sprsina"):
        if not (folder / name).is_file():
            raise FileNotFoundError(f"{folder / name} is missing")
    g = parse_gfile(folder / "geqdsk")
    time_ms = int(folder.name.rstrip("ms"))
    signal = RGeoZGeoSignal.from_tsc_state({"time_ms": time_ms, "Ip": float(g["ip"]), "gfile": g, "abnormal": False})
    kat = read_coil_currents_csv(folder / "coil_currents.csv")
    with (folder / "coil_currents.csv").open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, skipinitialspace=True)
        key = next(value for value in (reader.fieldnames or []) if "ccoil" in value.lower())
        raw_kat = tuple(row[key].strip() for row in reader)
    exact_currents = decimal_single_turn_currents_a(raw_kat, cfg.turns_tsc, name=str(folder))
    currents = tuple(float(value) for value in exact_currents)
    return {"time_ms": time_ms, "r_geo_m": signal.boundary.r_geo_m, "z_geo_m": signal.boundary.z_geo_m,
            "r_mid_m": signal.limiter.r_mid_m, "r_inner_m": signal.limiter.r_inner_m,
            "r_outer_m": signal.limiter.r_outer_m, "ip_a": signal.ip_a,
            "current_a_tsc": currents, "current_decimal_a_tsc": exact_currents,
            "wire_a": _wire(folder / "wire_currents.csv", cfg),
            "abnormal": "abnormal exit" in (folder / "outputa").read_text(errors="ignore").lower() if (folder / "outputa").is_file() else False}


def _maxdiff(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return max(abs(x-y) for x,y in zip(a,b)) if len(a) == len(b) else math.inf


def audit(config_path: Path, run_dir: Path, source_revision: str) -> dict[str, Any]:
    cfg = TSCConfig.from_json(config_path)
    failures: list[str] = []
    rows: dict[str, list[dict[str, Any]]] = {}
    action_checks = observed_checks = effect_checks = 0
    expected_times = tuple(range(1100, 1105))
    for rollout, prefix_name in NR1_1MS_ROLLOUTS:
        try:
            states = [_state(run_dir / "rollouts" / rollout / f"{time}ms", cfg) for time in expected_times]
            rows[rollout] = states
            frozen = build_frozen_one_ms_prefixes(
                source_current_a_tsc=states[0]["current_a_tsc"], turns_tsc=cfg.turns_tsc,
                min_current_a_tsc=cfg.min_current_a_tsc, max_current_a_tsc=cfg.max_current_a_tsc)
            targets = frozen.prefixes[prefix_name]
            source = states[0]
            for step, target in enumerate(targets):
                action_checks += 1
                observed = _fields(run_dir / "rollouts" / rollout / f"{1100+step}ms" / "inputa")
                if observed != target.card15_fields:
                    failures.append(f"CARD15:{rollout}:{step}")
                try:
                    target_decimal = card15_target_decimal_a(
                        target, cfg.turns_tsc, name=f"independent.target.{rollout}.{step}"
                    )
                    assert_exact_slew(states[step]["current_decimal_a_tsc"], target_decimal,
                                      name=f"independent.issue.{rollout}.{step}")
                    assert_exact_slew(states[step]["current_decimal_a_tsc"], states[step+1]["current_decimal_a_tsc"],
                                      name=f"independent.observed.{rollout}.{step}")
                    observed_checks += 1
                except Exception as exc:
                    failures.append(f"SLEW:{rollout}:{step}:{exc}")
            if prefix_name != "hold":
                target_decimal = card15_target_decimal_a(
                    targets[0], cfg.turns_tsc, name=f"independent.effect.{rollout}"
                )
                effect = tuple(b-a for a,b in zip(source["current_decimal_a_tsc"], states[1]["current_decimal_a_tsc"]))
                request = tuple(b-a for a,b in zip(source["current_decimal_a_tsc"], target_decimal))
                effect_checks += 14
                if any(value == 0.0 for value in effect) or any(math.copysign(1, a) != math.copysign(1, b) for a,b in zip(effect, request)):
                    failures.append(f"FIRST_EFFECT:{rollout}")
                for step in (2,3,4):
                    if max(abs(a-b) for a,b in zip(
                        states[step]["current_decimal_a_tsc"], source["current_decimal_a_tsc"]
                    )) > RETURN_EQUIVALENCE_A:
                        failures.append(f"RETURN_HOLD:{rollout}:{step}")
            for step, state in enumerate(states):
                if state["time_ms"] != 1100 + step: failures.append(f"TIME:{rollout}:{step}")
                if state["abnormal"]: failures.append(f"ABNORMAL:{rollout}:{step}")
                if not state["r_inner_m"] <= state["r_geo_m"] <= state["r_outer_m"]: failures.append(f"LIMITER:{rollout}:{step}")
                if abs(state["r_geo_m"] - source["r_geo_m"]) > .05: failures.append(f"R:{rollout}:{step}")
                if abs(state["z_geo_m"] - source["z_geo_m"]) > .05: failures.append(f"Z:{rollout}:{step}")
                if math.copysign(1,state["ip_a"]) != math.copysign(1,source["ip_a"]) or abs(state["ip_a"]-source["ip_a"]) > .1*abs(source["ip_a"]): failures.append(f"IP:{rollout}:{step}")
        except Exception as exc:
            failures.append(f"RAW:{rollout}:{type(exc).__name__}:{exc}")
            rows.setdefault(rollout, [])
    maxima = {"geometry_m": 0.0, "ip_a": 0.0, "coil_a": 0.0, "wire_a": 0.0}
    for prefix in ("hold", "pattern_a", "pattern_b"):
        left, right = rows.get(f"{prefix}_primary", []), rows.get(f"{prefix}_replay", [])
        if len(left) != 5 or len(right) != 5:
            failures.append(f"REPLAY_COUNT:{prefix}"); continue
        for a,b in zip(left,right):
            maxima["geometry_m"] = max(maxima["geometry_m"], *(abs(a[k]-b[k]) for k in ("r_geo_m","z_geo_m","r_mid_m")))
            maxima["ip_a"] = max(maxima["ip_a"], abs(a["ip_a"]-b["ip_a"]))
            maxima["coil_a"] = max(maxima["coil_a"], _maxdiff(a["current_a_tsc"],b["current_a_tsc"]))
            maxima["wire_a"] = max(maxima["wire_a"], _maxdiff(a["wire_a"],b["wire_a"]))
    if maxima["geometry_m"] > 1e-12: failures.append("REPLAY_GEOMETRY")
    if maxima["ip_a"] > 1e-9: failures.append("REPLAY_IP")
    if maxima["coil_a"] > 1e-9: failures.append("REPLAY_COIL")
    if maxima["wire_a"] > 1e-9: failures.append("REPLAY_WIRE")
    failures = list(dict.fromkeys(failures))
    result = {"schema_version":f"{NR1_1MS_CONTRACT_VERSION}-independent", "created_utc":datetime.now(timezone.utc).isoformat(),
              "source_revision":source_revision, "passed":not failures,
              "route":"ONE_MS_NR1R1_INDEPENDENT_PASS" if not failures else "ONE_MS_NR1R1_INDEPENDENT_FAIL",
              "failures":failures, "raw_rollouts":sum(len(v)==5 for v in rows.values()),
              "raw_states":sum(len(v) for v in rows.values()), "action_checks":action_checks,
              "observed_slew_checks":observed_checks, "first_effect_component_checks":effect_checks,
              "maximum_absolute_difference":maxima}
    destination = run_dir / "independent_audit.json"
    if destination.exists(): raise FileExistsError(f"refusing to overwrite {destination}")
    destination.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
    return result


def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--config",type=Path,required=True); p.add_argument("--run-dir",type=Path,required=True); p.add_argument("--source-revision",required=True)
    a=p.parse_args(); result=audit(a.config.resolve(),a.run_dir.resolve(),a.source_revision); print(json.dumps(result,indent=2,sort_keys=True)); return 0 if result["passed"] else 2
if __name__ == "__main__": raise SystemExit(main())
