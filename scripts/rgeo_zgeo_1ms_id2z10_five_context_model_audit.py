#!/usr/bin/env python3
"""Deterministic zero-TSC replay audit for ID-2Z10."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_id2z10_five_context_model as primary  # noqa: E402

SCHEMA = "rgeo-zgeo-1ms-id2z10-deterministic-replay-audit-v1"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("object required")
    return value


def audit(stage_config: Path, run_dir: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    run_dir = primary.base.inside(run_dir, "run dir")
    result_path = run_dir / "result.json"
    result = load_json(result_path)
    recomputed, artifact = primary.execute(stage_config, source_revision)
    expected = dict(result); expected.pop("model_sha256", None)
    if expected != recomputed:
        failures.append("DETERMINISTIC_RESULT_REPLAY")
    model_path = run_dir / "model.json"
    if result.get("passed"):
        if artifact is None or not model_path.is_file():
            failures.append("MODEL_ARTIFACT_MISSING")
        elif load_json(model_path) != artifact:
            failures.append("MODEL_ARTIFACT_REPLAY")
        elif result.get("model_sha256") != primary.base.sha256(model_path):
            failures.append("MODEL_SHA256")
    elif model_path.exists() or artifact is not None:
        failures.append("INELIGIBLE_MODEL_ARTIFACT_EMITTED")
    for key in ("new_tsc_or_plant_advances", "calibration_or_holdout_records_read",
                "controller_or_optimizer_runs"):
        if result.get(key) != 0:
            failures.append(f"FORBIDDEN:{key}")
    return {"schema_version": SCHEMA, "source_revision": source_revision,
            "stage_config_sha256": primary.CONFIG_SHA256,
            "audit_passed": not failures, "failures": failures,
            "primary_sha256": primary.base.sha256(result_path),
            "primary_route": result.get("route"), "primary_passed": result.get("passed"),
            "recomputed_route": recomputed.get("route"),
            "recomputed_winner": recomputed.get("winner"),
            "model_sha256": result.get("model_sha256"),
            "new_tsc_or_plant_advances": 0,
            "calibration_or_holdout_records_read": 0,
            "claim_boundary": "Same-code deterministic five-context replay; not an independent model implementation."}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-config", type=Path, default=primary.CONFIG)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    value = audit(args.stage_config, args.run_dir, args.source_revision)
    output = args.output or args.run_dir / "deterministic_replay_audit.json"
    primary.base.write_new(primary.base.inside(output, "audit output"), value)
    print(json.dumps(value, indent=2, sort_keys=True, allow_nan=False))
    return 0 if value["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
