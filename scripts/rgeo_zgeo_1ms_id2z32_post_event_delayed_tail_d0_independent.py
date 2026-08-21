#!/usr/bin/env python3
"""Independent full-raw audit for ID-2Z32."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_id2z32_post_event_delayed_tail_d0 as primary  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2z27_dynamic_output_aligned_campaign_independent as i27  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2z9_late_root_branch_utility_support_independent as rawio  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-id2z32-post-event-delayed-tail-d0-independent-v1"


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(primary._inside(path, "audit JSON").read_text(encoding="utf-8"))
    if not isinstance(value, dict): raise ValueError("JSON object required")
    return value


def _compact(run_dir: Path, expected: Sequence[dict[str, Any]], failures: list[str]):
    excluded = {"result.json", "offline_preflight.json", "independent_raw_audit.json"}
    rows = [_read(path) for path in sorted(run_dir.glob("*.json")) if path.name not in excluded]
    rows = [row for row in rows if "rollout_id" in row]
    order = {row["rollout_id"]: i for i, row in enumerate(expected)}
    rows.sort(key=lambda row: order.get(row.get("rollout_id"), 999))
    if [row.get("rollout_id") for row in rows] != [row["rollout_id"] for row in expected[:len(rows)]]:
        failures.append("COMPACT_ORDER_OR_IDENTITY")
    return rows


def _response(row: dict[str, Any], baseline: dict[str, Any], state: int) -> np.ndarray:
    return np.asarray([float(row["states"][state]["r_geo_m"])-float(baseline["states"][state]["r_geo_m"]),
                       float(row["states"][state]["z_geo_m"])-float(baseline["states"][state]["z_geo_m"])])


def _scientific(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    by_id = {str(row.get("family_id")): row for row in rows}
    baseline = by_id.get("baseline_transition_center")
    baseline_ok = bool(baseline and baseline.get("passed") and len(baseline.get("states", [])) == 74)
    gates = stage["measurement_gates"]; branches = []; geometry = []; all_signal = baseline_ok
    if baseline_ok:
        for phase in stage["phase_issue_steps"]:
            vectors = {4: [], 8: []}
            for axis in stage["output_aligned_axis_ids"]:
                for sign in stage["initial_signs"]:
                    family = f"issue{phase}__{axis}__{sign}_then_return"; row = by_id.get(family)
                    complete = bool(row and row.get("passed") and len(row.get("states", [])) == 74)
                    if not complete:
                        branches.append({"family_id": family, "complete": False, "passed": False})
                        all_signal = False; continue
                    value = {h: _response(row, baseline, phase+h) for h in (4,8)}
                    norms = {h: float(np.linalg.norm(value[h])) for h in (4,8)}
                    cosine = float(np.dot(value[4],value[8])/(norms[4]*norms[8])) if norms[4] and norms[8] else -1.0
                    max_ip = max(abs(float(row["states"][k]["ip_a"])-float(baseline["states"][k]["ip_a"])) for k in range(phase+1,74))
                    passed = bool(norms[4]>=gates["minimum_each_h4_rz_response_m"] and norms[8]>=gates["minimum_each_h8_rz_response_m"] and cosine>=gates["minimum_each_h4_h8_cosine"] and max_ip<=gates["maximum_absolute_paired_ip_response_a"])
                    events=[]; delayed=stage["delayed_tail_contract"]
                    for k in range(delayed["event_scan_first_state"],delayed["event_scan_last_state"]+1):
                        delta=float(row["states"][k]["r_geo_m"])-float(row["states"][k-1]["r_geo_m"])
                        if delta>delayed["positive_r_event_threshold_m"]: events.append({"effect_state_index":k,"delta_r_m":delta})
                    branches.append({"family_id":family,"complete":True,"h4_response_m":value[4].tolist(),"h8_response_m":value[8].tolist(),"h4_norm_m":norms[4],"h8_norm_m":norms[8],"h4_h8_cosine":cosine,"maximum_absolute_paired_ip_response_a":max_ip,"delayed_positive_r_events":events,"passed":passed})
                    vectors[4].append(value[4]); vectors[8].append(value[8]); all_signal=all_signal and passed
            for horizon in (4,8):
                value=i27._geometry(vectors[horizon],gates["direction_grid_count"])
                value.update({"phase_issue":phase,"horizon":horizon,"passed":bool(value["maximum_angular_gap_deg"]<=gates["maximum_each_phase_horizon_angular_gap_deg"] and value["weakest_best_projection_m"]>=gates["minimum_each_phase_horizon_weakest_best_projection_m"])})
                geometry.append(value); all_signal=all_signal and value["passed"]
    replay=i27._replay(by_id.get(stage["replay_source_family_id"]),by_id.get(stage["replay_family_id"]),stage["semantic_artifacts"])
    return {"baseline_complete":baseline_ok,"branch_metrics":branches,"positive_span_metrics":geometry,"replay_metrics":replay,"passed":bool(all_signal and len(branches)==8 and replay["passed"])}


def audit(config: Path, run_dir: Path, source_revision: str) -> dict[str, Any]:
    failures=[]; run_dir=primary._inside(run_dir,"run")
    result=_read(run_dir/"result.json")
    stage,_,cfg,preflight,tracked=primary.load(config)
    expected=primary.build_streams(stage,cfg,preflight,tracked)
    compact=_compact(run_dir,expected,failures)
    rollout_root=run_dir/"rollouts"
    actual=sorted(path.name for path in rollout_root.iterdir() if path.is_dir())
    if actual!=sorted(str(row.get("rollout_id")) for row in compact): failures.append("ROLLOUT_DIRECTORY_SET")
    raw_rows,inventory_lines,inventory_bytes=rawio._raw_rows(run_dir,cfg,expected,compact,failures)
    digest=hashlib.sha256("".join(f"{line}\n" for line in sorted(inventory_lines)).encode()).hexdigest()
    if digest!=result.get("required_artifact_inventory_sha256") or len(inventory_lines)!=result.get("required_artifact_files") or inventory_bytes!=result.get("required_artifact_bytes"): failures.append("INVENTORY")
    compact_by={row["rollout_id"]:row for row in compact}
    semantic={row["rollout_id"]:i27._preissue_semantic_row(row,compact_by.get(row["rollout_id"],{})) for row in raw_rows}
    centered=semantic.get("baseline_transition_center"); prefixes=[]
    for frozen in expected[:len(compact)]:
        family=frozen["rollout_id"]
        if frozen["kind"]=="center_baseline": reference=tracked; count=33
        else: reference=centered or {}; count=int(frozen["prefix_checkpoint_last_state"])+1
        prefixes.append(primary.z31.z30.z27.z6.prefix_check(semantic.get(family,{}),reference,count,count-1,stage["semantic_artifacts"]))
    execution=bool(raw_rows and all(row.get("passed") for row in raw_rows))
    raw_ok=len(inventory_lines)==5*sum(len(row.get("states",[])) for row in raw_rows) and not any(x.startswith("MISSING_ARTIFACT") for x in failures)
    prefix_ok=len(prefixes)==len(compact) and all(row.get("passed") for row in prefixes)
    scientific=_scientific(raw_rows,stage)
    if not execution: route=stage["routes"]["execution_or_interface_fail"]
    elif not raw_ok: route=stage["routes"]["raw_integrity_fail"]
    elif not prefix_ok: route=stage["routes"]["prefix_mismatch"]
    elif not scientific["replay_metrics"]["passed"]: route=stage["routes"]["replay_fail"]
    elif len(raw_rows)!=10 or not scientific["passed"]: route=stage["routes"]["signal_fail"]
    else: route=stage["routes"]["data_pass"]
    if result.get("prefix_checks")!=prefixes: failures.append("PREFIX_RECOMPUTE")
    if result.get("scientific_metrics")!=scientific: failures.append("SCIENTIFIC_RECOMPUTE")
    if result.get("route")!=route or result.get("passed")!=(route==stage["routes"]["data_pass"]): failures.append("ROUTE_OR_VERDICT")
    counters={key:sum(int(row.get(key,0)) for row in compact) for key in ("reset_calls","advance_attempts","plant_advance_gotsc_calls","verified_plant_advances")}
    for key,value in counters.items():
        if result.get(key)!=value: failures.append(f"COUNTER:{key}")
    if result.get("source_revision")!=source_revision or result.get("stage_config_sha256")!=primary.CONFIG_SHA256 or result.get("models_fit_or_updated")!=0 or result.get("fresh_calibration_or_holdout_records_read")!=0: failures.append("IDENTITY_OR_FORBIDDEN_WORK")
    return {"schema_version":SCHEMA,"source_revision":source_revision,"primary_sha256":hashlib.sha256((run_dir/"result.json").read_bytes()).hexdigest(),"audit_passed":not failures,"failures":failures,"recomputed_route":route,"reparsed_rollouts":len(raw_rows),"reparsed_states":sum(len(row.get("states",[])) for row in raw_rows),"reparsed_required_artifacts":len(inventory_lines),"reparsed_required_bytes":inventory_bytes,"recomputed_scientific_metrics":scientific,"models_fit_or_updated":0,"tsc_calls":counters["plant_advance_gotsc_calls"],"plant_advances":counters["verified_plant_advances"],"claim_boundary":stage["claim_boundary"]}


def main(argv: Sequence[str] | None=None)->int:
    parser=argparse.ArgumentParser(); parser.add_argument("--config",type=Path,default=primary.CONFIG); parser.add_argument("--run-dir",type=Path,required=True); parser.add_argument("--source-revision",required=True); parser.add_argument("--output",type=Path,required=True); args=parser.parse_args(argv)
    try: value=audit(args.config,args.run_dir,args.source_revision)
    except Exception as exc: value={"schema_version":SCHEMA,"source_revision":args.source_revision,"audit_passed":False,"failures":[f"{type(exc).__name__}:{exc}"]}
    primary.z31.z30.z27.io.write_new(args.output,value); print(json.dumps(value,sort_keys=True,allow_nan=False)); return 0 if value["audit_passed"] else 2


if __name__=="__main__": raise SystemExit(main())
