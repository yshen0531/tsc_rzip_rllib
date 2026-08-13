#!/usr/bin/env python3
"""Structurally independent raw/spec/safety audit for 1 ms NR2 phases."""

from __future__ import annotations

import argparse
from decimal import Decimal
import json
import math
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_nr1_independent import _fields, _state  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    assert_exact_slew,
    card15_target_decimal_a,
    decimal_single_turn_currents_a,
)
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr2_spec import (  # noqa: E402
    NR2_1MS_CAMPAIGN_ID,
    NR2_1MS_CONTRACT_VERSION,
    NR2_1MS_HORIZON_STEPS,
    build_one_ms_nr2_specs,
    build_one_ms_nr2_targets,
    validate_one_ms_nr2_specs,
)
from tsc_rzip_rllib.core.runner import TSCConfig  # noqa: E402

STRUCTURAL_CURRENT_ERROR_A = Decimal("1e-9")


def audit(config_path: Path, campaign_dir: Path, phase: str, source_revision: str) -> dict[str, Any]:
    destination = campaign_dir / f"{phase}_independent.json"
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite {destination}")
    cfg = TSCConfig.from_json(config_path)
    allowed = {"development", "calibration"} if phase == "development_calibration" else {"holdout"}
    specs = tuple(value for value in build_one_ms_nr2_specs() if value.split in allowed)
    source_folder = cfg.simulation_root / cfg.start_folder
    source_state = _state(source_folder, cfg)
    source_fields = _fields(source_folder / "inputa")
    source_command = decimal_single_turn_currents_a(
        tuple(value.strip() for value in source_fields), cfg.turns_tsc,
        name="independent.source_command",
    )
    source_readback = source_state["current_decimal_a_tsc"]
    bias = tuple(value-command for value,command in zip(source_readback,source_command))
    spec_gate = validate_one_ms_nr2_specs(
        build_one_ms_nr2_specs(), source_current_a_tsc=source_state["current_a_tsc"],
        turns_tsc=cfg.turns_tsc,
    )
    failures: list[str] = []
    completed = state_checks = command_checks = observed_checks = structural_checks = raw_files = 0
    maximum = {"command_step_a":Decimal(0),"observed_step_a":Decimal(0),
               "structural_current_error_a":Decimal(0),"r_displacement_m":0.0,
               "z_displacement_m":0.0,"ip_fraction":0.0}
    times = tuple(range(1100, 1100 + NR2_1MS_HORIZON_STEPS + 1))
    for spec in specs:
        folder = campaign_dir / "rollouts" / spec.trajectory_id
        try:
            states = [_state(folder / f"{time_ms}ms", cfg) for time_ms in times]
            targets = build_one_ms_nr2_targets(
                spec, source_current_a_tsc=source_state["current_a_tsc"], turns_tsc=cfg.turns_tsc)
            active_command = source_command
            for step,target in enumerate(targets):
                target_a=card15_target_decimal_a(target,cfg.turns_tsc,name=f"independent.{spec.trajectory_id}.{step}")
                observed_fields=_fields(folder/f"{1100+step}ms"/"inputa")
                if observed_fields != target.card15_fields: failures.append(f"CARD15:{spec.trajectory_id}:{step}")
                command_delta=Decimal(str(assert_exact_slew(active_command,target_a,name=f"command.{spec.trajectory_id}.{step}")))
                observed_delta=Decimal(str(assert_exact_slew(states[step]["current_decimal_a_tsc"],states[step+1]["current_decimal_a_tsc"],name=f"observed.{spec.trajectory_id}.{step}")))
                maximum["command_step_a"]=max(maximum["command_step_a"],command_delta)
                maximum["observed_step_a"]=max(maximum["observed_step_a"],observed_delta)
                predicted=tuple(value+offset for value,offset in zip(target_a,bias))
                error=max(abs(value-wanted) for value,wanted in zip(states[step+1]["current_decimal_a_tsc"],predicted))
                maximum["structural_current_error_a"]=max(maximum["structural_current_error_a"],error)
                if error > STRUCTURAL_CURRENT_ERROR_A: failures.append(f"STRUCTURAL_CURRENT:{spec.trajectory_id}:{step}")
                active_command=target_a; command_checks+=1; observed_checks+=1; structural_checks+=1
            for step,state in enumerate(states):
                state_checks+=1
                if state["time_ms"] != 1100+step: failures.append(f"TIME:{spec.trajectory_id}:{step}")
                if state["abnormal"]: failures.append(f"ABNORMAL:{spec.trajectory_id}:{step}")
                if not state["r_inner_m"] <= state["r_geo_m"] <= state["r_outer_m"]: failures.append(f"LIMITER:{spec.trajectory_id}:{step}")
                r=abs(state["r_geo_m"]-source_state["r_geo_m"]); z=abs(state["z_geo_m"]-source_state["z_geo_m"]); ip=abs(state["ip_a"]-source_state["ip_a"])/abs(source_state["ip_a"])
                maximum["r_displacement_m"]=max(maximum["r_displacement_m"],r); maximum["z_displacement_m"]=max(maximum["z_displacement_m"],z); maximum["ip_fraction"]=max(maximum["ip_fraction"],ip)
                if r>.05: failures.append(f"R:{spec.trajectory_id}:{step}")
                if z>.05: failures.append(f"Z:{spec.trajectory_id}:{step}")
                if math.copysign(1,state["ip_a"]) != math.copysign(1,source_state["ip_a"]) or ip>.1: failures.append(f"IP:{spec.trajectory_id}:{step}")
            record=json.loads((campaign_dir/"records"/f"{spec.trajectory_id}.json").read_text(encoding="utf-8"))
            if record.get("passed") is not True or record.get("spec") != spec.to_dict() or record.get("plant_advances") != 16: failures.append(f"RECORD:{spec.trajectory_id}")
            raw_files += sum(1 for time_ms in times for name in ("geqdsk","inputa","sprsina","coil_currents.csv","wire_currents.csv") if (folder/f"{time_ms}ms"/name).is_file())
            completed+=1
        except Exception as exc:
            failures.append(f"RAW:{spec.trajectory_id}:{type(exc).__name__}:{exc}")
    expected_advances=len(specs)*16
    if completed!=len(specs) or command_checks!=expected_advances or observed_checks!=expected_advances or structural_checks!=expected_advances or state_checks!=len(specs)*17: failures.append("COUNT_GATE")
    failures=list(dict.fromkeys(failures)); passed=not failures
    result={"schema_version":f"{NR2_1MS_CONTRACT_VERSION}-independent-v1","campaign_id":NR2_1MS_CAMPAIGN_ID,"phase":phase,"source_revision":source_revision,"passed":passed,"route":f"ONE_MS_NR2_{phase.upper()}_INDEPENDENT_PASS" if passed else "ONE_MS_NR2_INDEPENDENT_FAIL","failures":failures,"expected_trajectories":len(specs),"completed_trajectories":completed,"plant_advances":command_checks,"state_checks":state_checks,"command_checks":command_checks,"observed_slew_checks":observed_checks,"structural_current_checks":structural_checks,"raw_required_file_count":raw_files,"maximum":{key:str(value) if isinstance(value,Decimal) else value for key,value in maximum.items()},"spec_gate":spec_gate}
    destination.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return result


def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--config",type=Path,required=True); p.add_argument("--campaign-dir",type=Path,required=True); p.add_argument("--phase",choices=("development_calibration","holdout"),required=True); p.add_argument("--source-revision",required=True)
    a=p.parse_args(); result=audit(a.config.resolve(),a.campaign_dir.resolve(),a.phase,a.source_revision); print(json.dumps(result,indent=2,sort_keys=True)); return 0 if result["passed"] else 2


if __name__=="__main__": raise SystemExit(main())
