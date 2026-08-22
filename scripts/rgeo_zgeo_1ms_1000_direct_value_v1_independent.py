#!/usr/bin/env python3
"""Independent file/artifact and deterministic metric audit for V1."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from scripts import rgeo_zgeo_1ms_1000_direct_value_v1 as primary  # noqa: E402


def audit(config: Path, output: Path, source_revision: str) -> dict:
    failures=[]
    try:
        stage,contexts=primary.load(config)
        recomputed=primary.development(stage,contexts)
        reported=json.loads((output/"result.json").read_text(encoding="utf-8"))
        if reported.get("source_revision")!=source_revision: failures.append("SOURCE_REVISION")
        if reported.get("plant_advances")!=0: failures.append("PLANT_ADVANCES")
        expected={
          "passed":recomputed["passed"], "gate_pass":recomputed["gate_pass"], "folds":recomputed["folds"],
          "final_maximum_combined_rz_halfwidth_mm":recomputed["final_maximum_combined_rz_halfwidth_mm"],
          "final_maximum_combined_ip_halfwidth_a":recomputed["final_maximum_combined_ip_halfwidth_a"],
          "maximum_observed_absolute_ip_response_a":recomputed["maximum_observed_absolute_ip_response_a"],
          "maximum_development_nearest_support_distance":recomputed["maximum_development_nearest_support_distance"]}
        for key,value in expected.items():
            if not primary._serial(value)==reported.get(key): failures.append(f"RESULT:{key}")
        route=stage["routes"]["pass"] if recomputed["passed"] else stage["routes"]["model_fail"]
        if reported.get("route")!=route: failures.append("ROUTE")
        artifact_path=output/"model_artifact.json"
        if recomputed["passed"]:
            if not artifact_path.is_file(): failures.append("ARTIFACT_MISSING")
            elif primary.b0.sha256(artifact_path)!=reported.get("model_artifact_sha256"):
                failures.append("ARTIFACT_SHA")
            else:
                artifact=json.loads(artifact_path.read_text(encoding="utf-8"))
                if artifact.get("qualification")!="development_only_fresh_calibration_and_blind_required":
                    failures.append("ARTIFACT_QUALIFICATION")
                if artifact.get("support")!=recomputed["support"]: failures.append("ARTIFACT_SUPPORT")
                if artifact.get("model")!=primary._serial(recomputed["model"]): failures.append("ARTIFACT_MODEL")
    except Exception as exc: failures.append(f"{type(exc).__name__}:{exc}")
    failures=list(dict.fromkeys(failures))
    result={"schema_version":f"{primary.SCHEMA}-independent","kind":"independent_model_evidence_audit",
            "created_utc":datetime.now(timezone.utc).isoformat(),"source_revision":source_revision,
            "passed":not failures,"route":"ONE_MS_NR1000V1_INDEPENDENT_PASS" if not failures else "ONE_MS_NR1000V1_INDEPENDENT_FAIL",
            "failures":failures,"plant_advances":0}
    primary.b0.write_new(output/"independent_audit.json",result); return result


def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--config",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True); p.add_argument("--source-revision",required=True)
    a=p.parse_args(); result=audit(a.config.resolve(),a.output.resolve(),a.source_revision)
    print(json.dumps(result,indent=2,sort_keys=True)); return 0 if result["passed"] else 2


if __name__=="__main__": raise SystemExit(main())
