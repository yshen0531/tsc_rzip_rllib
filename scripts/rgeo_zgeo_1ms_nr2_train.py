#!/usr/bin/env python3
"""Fit, calibrate, freeze and evaluate the 1 ms NR2 candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import torch

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr2_models import (  # noqa:E402
    POINT_SCALES, SEEDS, ARXModel, Normalizer, build_residual, fit_arx,
    fit_residual, recursive_rollout,
)
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr2_spec import (  # noqa:E402
    NR2_1MS_CAMPAIGN_ID, build_one_ms_nr2_specs,
)


def _sha(path:Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()
def _write(path:Path,payload:Any)->None:
    if path.exists(): raise FileExistsError(f"refusing to overwrite {path}")
    path.write_text(json.dumps(payload,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")


def load_trajectories(campaign:Path,splits:set[str])->list[dict[str,Any]]:
    output=[]
    for spec in build_one_ms_nr2_specs():
        if spec.split not in splits: continue
        record=json.loads((campaign/"records"/f"{spec.trajectory_id}.json").read_text(encoding="utf-8"))
        if record.get("passed") is not True or record.get("spec")!=spec.to_dict(): raise ValueError(f"invalid record {spec.trajectory_id}")
        states=record["states"]; actions=record["actions"]
        if len(states)!=17 or len(actions)!=16: raise ValueError(f"invalid shape {spec.trajectory_id}")
        plasma=np.asarray([[s["r_geo_m"],s["z_geo_m"],s["ip_a"]] for s in states],dtype=float)
        currents=[list(map(float,states[0]["actual_current_decimal_a_tsc"]))]
        currents.extend([list(map(float,s["structural_current_prediction_decimal_a_tsc"])) for s in states[1:16]])
        command_deltas=np.asarray([list(map(float,a["command_delta_decimal_a_tsc"])) for a in actions])
        currents=np.asarray(currents); frames=[np.concatenate((plasma[s],currents[s],command_deltas[s],[s/16.0,plasma[s,0]-states[s]["r_mid_m"]])) for s in range(16)]
        output.append({"id":spec.trajectory_id,"split":spec.split,"pair_index":spec.pair_index,"plasma":plasma,"currents":currents,"command_deltas":command_deltas,"frames":frames,"r_mid_m":states[0]["r_mid_m"]})
    return output


def _predictions(models:list[tuple[ARXModel,Any|None]],rows:list[dict[str,Any]],normalizer:Normalizer)->list[list[np.ndarray]]:
    return [[recursive_rollout(base,residual,row,normalizer) for base,residual in models] for row in rows]


def _mse(models,rows,normalizer)->float:
    values=[]
    for predictions,row in zip(_predictions(models,rows,normalizer),rows):
        mean=np.mean(predictions,axis=0); values.append(np.mean(((mean[1:]-row["plasma"][1:])/POINT_SCALES)**2))
    return float(np.mean(values))


def _folds(rows:list[dict[str,Any]]):
    for fold in range(5): yield ([x for x in rows if x["pair_index"]%5!=fold],[x for x in rows if x["pair_index"]%5==fold])


def within_interval_caps(half_width:Any)->bool:
    values=np.asarray(half_width,dtype=float)
    if values.ndim!=2 or values.shape[1]!=3 or not np.all(np.isfinite(values)):
        return False
    return bool(np.all(np.max(values,axis=0)<=np.asarray([.004,.004,400.0])))


def select(rows:list[dict[str,Any]])->dict[str,Any]:
    table=[]
    for ridge in (1e-6,1e-4,1e-2):
        scores=[]
        for train,valid in _folds(rows):
            norm=Normalizer.fit(train); scores.append(_mse([(fit_arx(train,norm,ridge),None)],valid,norm))
        table.append({"class":"arx","ridge":ridge,"width":None,"fold_scores":scores,"mean":float(np.mean(scores))})
    selected_ridge=min((x for x in table if x["class"]=="arx"),key=lambda x:x["mean"])["ridge"]
    for kind in ("gru","lstm","tcn"):
        for width in (8,12):
            scores=[]
            for fold,(train,valid) in enumerate(_folds(rows)):
                norm=Normalizer.fit(train); base=fit_arx(train,norm,selected_ridge); residual=fit_residual(kind,width,train,norm,base,SEEDS[0]+fold); scores.append(_mse([(base,residual)],valid,norm))
            table.append({"class":kind,"ridge":selected_ridge,"width":width,"fold_scores":scores,"mean":float(np.mean(scores))})
    chosen={"arx":{"ridge":selected_ridge,"width":None}}
    for kind in ("gru","lstm","tcn"):
        row=min((x for x in table if x["class"]==kind),key=lambda x:(x["mean"],x["width"])); chosen[kind]={"ridge":selected_ridge,"width":row["width"]}
    return {"table":table,"selected":chosen}


def fit_ensembles(rows,normalizer,selected):
    output={}; count=len(rows)
    for kind,params in selected.items():
        members=[]
        for seed in SEEDS:
            rng=np.random.default_rng(seed); indices=rng.integers(0,count,size=count); sampled=[rows[i] for i in indices]
            base=fit_arx(sampled,normalizer,float(params["ridge"])); residual=None if kind=="arx" else fit_residual(kind,int(params["width"]),sampled,normalizer,base,seed)
            members.append((base,residual))
        output[kind]=members
    return output


def calibrate(models,development,calibration,normalizer):
    dev=[]
    for predictions,row in zip(_predictions(models,development,normalizer),development): dev.append(np.abs(np.mean(predictions,axis=0)[1:]-row["plasma"][1:]))
    base=np.quantile(np.asarray(dev),.95,axis=0,method="linear"); base=np.maximum(base,np.asarray([1e-9,1e-9,1e-6]))
    ratios=[]
    for predictions,row in zip(_predictions(models,calibration,normalizer),calibration): ratios.extend(np.max(np.abs(np.mean(predictions,axis=0)[1:]-row["plasma"][1:])/base,axis=1))
    multiplier=float(np.quantile(ratios,.90,method="higher")); half=base*multiplier; coverage=float(np.mean(np.asarray(ratios)<=multiplier+1e-12)); eligible=coverage>=.90 and within_interval_caps(half)
    return {"base_half_width_by_horizon":base.tolist(),"multiplier":multiplier,"half_width_by_horizon":half.tolist(),"joint_coverage":coverage,"eligible":eligible}


def _serialize(ensembles,selection,normalizer,calibration):
    members={}
    for kind,rows in ensembles.items():
        members[kind]=[]
        for base,residual in rows: members[kind].append({"coefficient":base.coefficient,"residual":None if residual is None else residual.state_dict()})
    return {"campaign_id":NR2_1MS_CAMPAIGN_ID,"selected":selection,"normalizer":normalizer.to_dict(),"calibration":calibration,"members":members,"seeds":SEEDS}


def fit_calibrate(campaign:Path,revision:str)->dict[str,Any]:
    audit=json.loads((campaign/"development_calibration_independent.json").read_text(encoding="utf-8"))
    if audit.get("passed") is not True or audit.get("source_revision")!=revision: raise RuntimeError("development/calibration audit not accepted")
    development=load_trajectories(campaign,{"development"}); calibration_rows=load_trajectories(campaign,{"calibration"}); normalizer=Normalizer.fit(development); selection=select(development); ensembles=fit_ensembles(development,normalizer,selection["selected"]); calibration={kind:calibrate(models,development,calibration_rows,normalizer) for kind,models in ensembles.items()}; eligible=sorted(k for k,v in calibration.items() if v["eligible"])
    bundle=campaign/"frozen_models.pt";
    if bundle.exists(): raise FileExistsError(f"refusing to overwrite {bundle}")
    torch.save(_serialize(ensembles,selection["selected"],normalizer,calibration),bundle); digest=_sha(bundle); result={"campaign_id":NR2_1MS_CAMPAIGN_ID,"source_revision":revision,"passed":bool(eligible),"route":"ONE_MS_NR2R1_CALIBRATED_CANDIDATES_FROZEN_HOLDOUT_AUTHORIZED" if eligible else "ONE_MS_NR2R1_CALIBRATION_FAIL_NO_HOLDOUT","selection":selection,"calibration":calibration,"eligible_classes":eligible,"frozen_model_sha256":digest}; _write(campaign/"fit_calibrate.json",result)
    if eligible: _write(campaign/"holdout_authorization.json",{"campaign_id":NR2_1MS_CAMPAIGN_ID,"holdout_authorized":True,"source_revision":revision,"frozen_model_sha256":digest,"eligible_classes":eligible})
    return result


def _deserialize(bundle):
    norm=Normalizer.from_dict(bundle["normalizer"]); output={}
    for kind,rows in bundle["members"].items():
        output[kind]=[]
        for item in rows:
            base=ARXModel(norm,np.asarray(item["coefficient"])); residual=None
            if item["residual"] is not None: residual=build_residual(kind,int(bundle["selected"][kind]["width"])); residual.load_state_dict(item["residual"]); residual.eval()
            output[kind].append((base,residual))
    return norm,output


def evaluate(campaign:Path,revision:str)->dict[str,Any]:
    auth=json.loads((campaign/"holdout_authorization.json").read_text()); audit=json.loads((campaign/"holdout_independent.json").read_text()); bundle_path=campaign/"frozen_models.pt"
    if auth.get("source_revision")!=revision or auth.get("frozen_model_sha256")!=_sha(bundle_path) or audit.get("passed") is not True: raise RuntimeError("holdout authorization/audit mismatch")
    bundle=torch.load(bundle_path,map_location="cpu",weights_only=False); normalizer,ensembles=_deserialize(bundle); rows=load_trajectories(campaign,{"holdout"}); results={}
    for kind in auth["eligible_classes"]:
        scaled=[]; coverage=[]; mse=[]; horizon={h:[] for h in (1,4,8,16)}; finite=True; half=np.asarray(bundle["calibration"][kind]["half_width_by_horizon"])
        for predictions,row in zip(_predictions(ensembles[kind],rows,normalizer),rows):
            mean=np.mean(predictions,axis=0); difference=np.abs(mean[1:]-row["plasma"][1:]); values=np.max(difference/POINT_SCALES,axis=1); scaled.extend(values); coverage.extend(np.all(difference<=half,axis=1)); mse.append(np.mean((difference/POINT_SCALES)**2)); finite=finite and bool(np.all(np.isfinite(mean)))
            for h in horizon: horizon[h].append(values[h-1])
        metrics={"finite":finite,"joint_point_fraction":float(np.mean(np.asarray(scaled)<=1)),"p95_scaled_error":float(np.quantile(scaled,.95,method="linear")),"joint_interval_coverage":float(np.mean(coverage)),"mean_squared_scaled_error":float(np.mean(mse)),"p95_scaled_error_by_horizon":{str(h):float(np.quantile(v,.95,method="linear")) for h,v in horizon.items()},"maximum_structural_current_error_a":audit["maximum"]["structural_current_error_a"]}
        metrics["passed"]=finite and metrics["joint_point_fraction"]>=.90 and metrics["p95_scaled_error"]<=1 and metrics["joint_interval_coverage"]>=.90 and all(v<=1.25 for v in metrics["p95_scaled_error_by_horizon"].values()) and within_interval_caps(half) and float(metrics["maximum_structural_current_error_a"])<=1e-9; results[kind]=metrics
    passing=[k for k,v in results.items() if v["passed"]]; winner=None
    if passing:
        winner=min(passing,key=lambda k:results[k]["mean_squared_scaled_error"])
        if winner!="arx" and "arx" in passing:
            gain=1-results[winner]["mean_squared_scaled_error"]/results["arx"]["mean_squared_scaled_error"]
            if gain<.15 or results[winner]["joint_interval_coverage"]<results["arx"]["joint_interval_coverage"] or results[winner]["p95_scaled_error"]>results["arx"]["p95_scaled_error"]: winner="arx"
    result={"campaign_id":NR2_1MS_CAMPAIGN_ID,"source_revision":revision,"passed":winner is not None,"route":"ONE_MS_NR2R1_CAUSAL_MODEL_QUALIFIED" if winner else "ONE_MS_NR2R1_MODEL_COMPARISON_FAIL_REDESIGN","winner":winner,"models":results,"frozen_model_sha256":_sha(bundle_path)}; _write(campaign/"holdout_evaluation.json",result); return result


def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("mode",choices=("fit_calibrate","evaluate_holdout")); p.add_argument("--campaign-dir",type=Path,required=True); p.add_argument("--source-revision",required=True); a=p.parse_args(); result=fit_calibrate(a.campaign_dir.resolve(),a.source_revision) if a.mode=="fit_calibrate" else evaluate(a.campaign_dir.resolve(),a.source_revision); print(json.dumps(result,indent=2,sort_keys=True)); return 0 if result["passed"] else 2


if __name__=="__main__": raise SystemExit(main())
