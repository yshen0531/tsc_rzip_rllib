#!/usr/bin/env python3
"""Direct support-gated no-action/candidate endpoint-set model."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_1000_baseline_b0 as b0  # noqa: E402

SCHEMA = "rgeo-zgeo-1ms-1000-direct-value-v1"
CONFIG_SHA256 = "0b1669531ba57c0055fbe0e04f8485948bb68492a538670696333ff38e39f942"
DEFAULT_CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_direct_value_v1.json"


class InputIntegrityError(ValueError):
    """Frozen V1 contract or development rows changed."""


def _directory_digest(path: Path) -> tuple[int, str]:
    files = sorted(p for p in path.glob("c_*.json") if "replay" not in p.name)
    text = "".join(f"{p.name}:{b0.sha256(p)}\n" for p in files)
    return len(files), hashlib.sha256(text.encode("utf-8")).hexdigest()


def _feature(row: dict[str, Any], stage: dict[str, Any]) -> np.ndarray:
    s0, s20, s24 = row["states"][0], row["states"][20], row["states"][24]
    scales = stage["feature_scales"]
    codes = np.asarray([stage["axis_signs_tsc_order"][a] for a in ("even","odd","block4")], dtype=float)
    codes /= np.linalg.norm(codes, axis=1)[:, None]
    c0 = np.asarray(s0["actual_current_a_tsc"], dtype=float)
    c20 = np.asarray(s20["actual_current_a_tsc"], dtype=float)
    c24 = np.asarray(s24["actual_current_a_tsc"], dtype=float)
    return np.r_[
        (s24["r_geo_m"]-s0["r_geo_m"])*1000.0/scales["rz_mm"],
        (s24["z_geo_m"]-s0["z_geo_m"])*1000.0/scales["rz_mm"],
        (s24["ip_a"]-s0["ip_a"])/scales["ip_a"],
        ((s24["r_geo_m"]-s20["r_geo_m"])/.004)/scales["velocity_m_per_s"],
        ((s24["z_geo_m"]-s20["z_geo_m"])/.004)/scales["velocity_m_per_s"],
        codes@(c24-c0)/scales["current_projection_a"],
        codes@(c24-c20)/scales["recent_current_projection_a"],
    ]


def _tail(row: dict[str, Any], phase: int, horizon: int) -> np.ndarray:
    a, z = row["states"][phase], row["states"][phase+horizon]
    return np.asarray([(z["r_geo_m"]-a["r_geo_m"])*1000.0,
                       (z["z_geo_m"]-a["z_geo_m"])*1000.0, z["ip_a"]-a["ip_a"]])


def _response(candidate: dict[str, Any], baseline: dict[str, Any], index: int) -> np.ndarray:
    a, z = candidate["states"][index], baseline["states"][index]
    return np.asarray([(a["r_geo_m"]-z["r_geo_m"])*1000.0,
                       (a["z_geo_m"]-z["z_geo_m"])*1000.0, a["ip_a"]-z["ip_a"]])


def load(config_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    config_path = b0.inside_root(config_path, "V1 config")
    if b0.sha256(config_path) != CONFIG_SHA256:
        raise InputIntegrityError("V1 config SHA-256 mismatch")
    stage = json.loads(config_path.read_text(encoding="utf-8"))
    exact = {"schema_version":SCHEMA, "model_id":"rgeo_zgeo_1ms_1000_direct_value_v1",
             "takeover_time_ms":1000, "candidate_issue_phase":24, "horizons":[4,8],
             "contexts":["even_plus","odd_plus","block4_plus","block4_minus"],
             "candidates":["even_plus","even_minus","odd_plus","odd_minus","block4_plus","block4_minus"],
             "direction_grid_count":64,
             "model_form":"candidate_specific_componentwise_median_max_deviation_direct_endpoint_set"}
    for key, expected in exact.items():
        if stage.get(key) != expected: raise InputIntegrityError(f"V1 frozen field mismatch: {key}")
    if stage.get("data_roles") != {"listed_primary_rows":"development_fit_eligible_weight_1",
        "replays":"excluded_zero_fit_weight", "calibration":"unopened", "holdout":"unopened",
        "controller_or_recourse":"forbidden", "fixed_1100_data":"forbidden"}:
        raise InputIntegrityError("V1 roles changed")
    design = b0.inside_root(ROOT/stage["design_path"], "V1 design")
    if b0.sha256(design) != stage["design_sha256"]: raise InputIntegrityError("V1 design changed")
    roots = []
    for spec in stage["dataset_roots"]:
        root = b0.inside_root(ROOT/spec["path"], "V1 dataset root")
        count, digest = _directory_digest(root)
        if count != spec["primary_count"] or digest != spec["primary_digest"]:
            raise InputIntegrityError(f"V1 dataset digest mismatch: {spec['path']}")
        roots.append(root)
    contexts: dict[str, Any] = {}
    for context in stage["contexts"]:
        root = roots[0] if context in ("even_plus","odd_plus") else roots[1]
        baseline_path = root/f"c_{context}__baseline.json"
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        if baseline.get("passed") is not True or baseline.get("repeat_index") != 0:
            raise InputIntegrityError(f"V1 baseline role invalid: {context}")
        candidates = {}
        for candidate in stage["context_candidates"][context]:
            row = json.loads((root/f"c_{context}__{candidate}.json").read_text(encoding="utf-8"))
            if row.get("passed") is not True or row.get("repeat_index") != 0:
                raise InputIntegrityError(f"V1 candidate role invalid: {context}:{candidate}")
            candidates[candidate] = row
        phase = stage["candidate_issue_phase"]
        contexts[context] = {
            "feature": _feature(baseline, stage),
            "no_action": {h:_tail(baseline, phase, h) for h in stage["horizons"]},
            "responses": {candidate:{h:_response(row, baseline, phase+h) for h in stage["horizons"]}
                          for candidate,row in candidates.items()},
        }
    return stage, contexts


def _robust(values: Sequence[np.ndarray], floor: np.ndarray) -> tuple[np.ndarray,np.ndarray]:
    array=np.asarray(values,dtype=float); center=np.median(array,axis=0)
    return center, np.max(np.abs(array-center),axis=0)+floor


def fit(contexts: Mapping[str,Any], stage: dict[str,Any]) -> dict[str,Any]:
    no_floor=np.asarray(stage["no_action_floor_rz_ip"],dtype=float)
    response_floor=np.asarray(stage["response_floor_rz_ip"],dtype=float)
    noop={}; responses={}
    for h in stage["horizons"]:
        center,width=_robust([c["no_action"][h] for c in contexts.values()],no_floor)
        noop[h]={"center":center,"halfwidth":width}
    for candidate in stage["candidates"]:
        eligible=[c for c in contexts.values() if candidate in c["responses"]]
        if not eligible: continue
        responses[candidate]={}
        for h in stage["horizons"]:
            center,width=_robust([c["responses"][candidate][h] for c in eligible],response_floor)
            responses[candidate][h]={"center":center,"halfwidth":width}
    return {"no_action":noop,"responses":responses,"train_contexts":sorted(contexts)}


def _support(contexts: Mapping[str,Any], stage: dict[str,Any]) -> dict[str,Any]:
    labels=["no_action",*stage["candidates"]]; result={}
    for label in labels:
        names=[name for name,row in contexts.items() if label=="no_action" or label in row["responses"]]
        features={name:contexts[name]["feature"] for name in names}
        nearest=[]
        for name in names:
            others=[float(np.linalg.norm(features[name]-features[other])) for other in names if other!=name]
            if not others: raise InputIntegrityError(f"V1 singleton support: {label}")
            nearest.append(min(others))
        result[label]={"context_names":names,"feature_centers":[features[n].tolist() for n in names],
                       "maximum_development_nearest_distance":max(nearest),
                       "refusal_radius":max(nearest)*stage["support_radius_multiplier"]}
    return result


def evaluate(model: dict[str,Any], truth: dict[str,Any], candidates: Sequence[str],
             horizons: Sequence[int], direction_count: int) -> dict[str,Any]:
    noop_components=[]; candidate_components=[]; regrets=[]; weakest={}
    for h in horizons:
        n=model["no_action"][h]; actual_noop=truth["no_action"][h]
        noop_components.extend((np.abs(actual_noop-n["center"])<=n["halfwidth"]+1e-12).tolist())
        available=[c for c in candidates if c in truth["responses"]]
        predicted=[]; actual=[]
        for candidate in available:
            r=model["responses"][candidate][h]
            actual_tail=actual_noop+truth["responses"][candidate][h]
            center=n["center"]+r["center"]; width=n["halfwidth"]+r["halfwidth"]
            candidate_components.extend((np.abs(actual_tail-center)<=width+1e-12).tolist())
            predicted.append(r["center"][:2]); actual.append(truth["responses"][candidate][h][:2])
        predicted=np.asarray(predicted); actual=np.asarray(actual)
        directions=np.asarray([[math.cos(2*math.pi*i/direction_count),math.sin(2*math.pi*i/direction_count)]
                               for i in range(direction_count)])
        progress=[]
        for direction in directions:
            ps=predicted@direction; ts=actual@direction
            chosen=int(np.argmax(np.r_[0.0,ps]))-1
            true_best=max(0.0,float(np.max(ts)))
            chosen_score=0.0 if chosen<0 else float(ts[chosen])
            regrets.append(true_best-chosen_score); progress.append(true_best)
        weakest[str(h)]=min(progress)
    return {"no_action_components":len(noop_components),"no_action_contained":sum(noop_components),
            "all_no_action_contained":all(noop_components),"candidate_components":len(candidate_components),
            "candidate_contained":sum(candidate_components),"all_candidates_contained":all(candidate_components),
            "maximum_directional_ranking_regret_mm":max(regrets),"weakest_best_progress_mm":weakest}


def development(stage: dict[str,Any], contexts: dict[str,Any]) -> dict[str,Any]:
    folds=[]
    for held in stage["contexts"]:
        train={k:v for k,v in contexts.items() if k!=held}
        folds.append({"held_context":held,**evaluate(fit(train,stage),contexts[held],stage["candidates"],
                                                        stage["horizons"],stage["direction_grid_count"])})
    final=fit(contexts,stage); support=_support(contexts,stage)
    max_rz=max(float(np.max(final["no_action"][h]["halfwidth"][:2]+r[h]["halfwidth"][:2]))
               for r in final["responses"].values() for h in stage["horizons"])
    max_ip=max(float(final["no_action"][h]["halfwidth"][2]+r[h]["halfwidth"][2])
               for r in final["responses"].values() for h in stage["horizons"])
    max_response_ip=max(abs(float(c["responses"][a][h][2])) for c in contexts.values()
                        for a in c["responses"] for h in stage["horizons"])
    max_support=max(row["maximum_development_nearest_distance"] for row in support.values())
    gates=stage["gates"]
    gate_rows={
        "no_action_containment":all(f["all_no_action_contained"] for f in folds),
        "candidate_containment":all(f["all_candidates_contained"] for f in folds),
        "width":max_rz<=gates["maximum_final_combined_rz_halfwidth_mm"] and max_ip<=gates["maximum_final_combined_ip_halfwidth_a"],
        "ranking":all(f["maximum_directional_ranking_regret_mm"]<=gates["maximum_each_fold_directional_ranking_regret_mm"] for f in folds),
        "progress":all(f["weakest_best_progress_mm"]["8"]>=gates["minimum_each_context_h8_weakest_best_progress_mm"] for f in folds),
        "ip":max_response_ip<=gates["maximum_observed_absolute_ip_response_a"],
        "support":max_support<=gates["maximum_development_nearest_support_distance"],
    }
    return {"passed":all(gate_rows.values()),"gate_pass":gate_rows,"folds":folds,"model":final,
            "support":support,"final_maximum_combined_rz_halfwidth_mm":max_rz,
            "final_maximum_combined_ip_halfwidth_a":max_ip,
            "maximum_observed_absolute_ip_response_a":max_response_ip,
            "maximum_development_nearest_support_distance":max_support}


def _serial(value: Any) -> Any:
    if isinstance(value,np.ndarray): return value.tolist()
    if isinstance(value,dict): return {str(k):_serial(v) for k,v in value.items()}
    if isinstance(value,list): return [_serial(v) for v in value]
    return value


def execute(config_path: Path, source_revision: str, output_dir: Path) -> dict[str,Any]:
    if output_dir.exists(): raise FileExistsError(f"refusing to overwrite {output_dir}")
    output_dir.mkdir(parents=True)
    try: stage,contexts=load(config_path)
    except Exception as exc:
        result={"schema_version":SCHEMA,"kind":"fixed_1000_direct_candidate_value_development",
                "created_utc":datetime.now(timezone.utc).isoformat(),"source_revision":source_revision,
                "passed":False,"route":"ONE_MS_NR1000V1_INPUT_INTEGRITY_FAIL_ZERO_TSC",
                "failures":[f"{type(exc).__name__}:{exc}"],"plant_advances":0}
        b0.write_new(output_dir/"result.json",result); return result
    report=development(stage,contexts); passed=report["passed"]
    artifact={"schema_version":f"{SCHEMA}-artifact","source_revision":source_revision,
              "model":_serial(report["model"]),"support":report["support"],
              "feature_contract":{"phase":stage["candidate_issue_phase"],"scales":stage["feature_scales"],
                                  "axis_signs_tsc_order":stage["axis_signs_tsc_order"]},
              "qualification":"development_only_fresh_calibration_and_blind_required"}
    if passed: b0.write_new(output_dir/"model_artifact.json",artifact)
    result={"schema_version":SCHEMA,"kind":"fixed_1000_direct_candidate_value_development",
            "created_utc":datetime.now(timezone.utc).isoformat(),"source_revision":source_revision,
            "passed":passed,"route":stage["routes"]["pass"] if passed else stage["routes"]["model_fail"],
            "plant_advances":0,"context_count":len(contexts),"candidate_count":len(stage["candidates"]),
            "gate_pass":report["gate_pass"],"folds":report["folds"],
            "final_maximum_combined_rz_halfwidth_mm":report["final_maximum_combined_rz_halfwidth_mm"],
            "final_maximum_combined_ip_halfwidth_a":report["final_maximum_combined_ip_halfwidth_a"],
            "maximum_observed_absolute_ip_response_a":report["maximum_observed_absolute_ip_response_a"],
            "maximum_development_nearest_support_distance":report["maximum_development_nearest_support_distance"],
            "claim_boundary":"development direct value set only; fresh calibration/blind and Authority/Recourse required"}
    if passed: result["model_artifact_sha256"]=b0.sha256(output_dir/"model_artifact.json")
    b0.write_new(output_dir/"result.json",result); return result


def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--config",type=Path,default=DEFAULT_CONFIG)
    p.add_argument("--source-revision",required=True); p.add_argument("--output",type=Path,required=True)
    a=p.parse_args(); result=execute(a.config.resolve(),a.source_revision,a.output.resolve())
    print(json.dumps(result,indent=2,sort_keys=True)); return 0 if result["passed"] else 2


if __name__=="__main__": raise SystemExit(main())
