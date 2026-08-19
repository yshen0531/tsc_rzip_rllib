#!/usr/bin/env python3
"""Deterministic no-TSC replay audit for ID-2Z8 model evaluation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_id0_vector_tail import sha256, write_new  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2z8_small_sequence_model as primary  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-id2z8-deterministic-replay-audit-v1"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("object required")
    return value


def audit(stage_config: Path, run_dir: Path,
          source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    run_dir = primary.inside(run_dir, "run dir")
    result_path = run_dir / "result.json"
    result = load_json(result_path)
    recomputed, artifact = primary.execute(
        stage_config, source_revision, output=None)
    expected = dict(result)
    expected.pop("model_sha256", None)
    if expected != recomputed:
        failures.append("DETERMINISTIC_RESULT_REPLAY")
    model_path = run_dir / "model.json"
    if result.get("passed"):
        if artifact is None or not model_path.is_file():
            failures.append("MODEL_ARTIFACT_MISSING")
        elif load_json(model_path) != artifact:
            failures.append("MODEL_ARTIFACT_REPLAY")
        elif result.get("model_sha256") != sha256(model_path):
            failures.append("MODEL_SHA256")
    elif model_path.exists() or artifact is not None:
        failures.append("INELIGIBLE_MODEL_ARTIFACT_EMITTED")
    if (result.get("new_tsc_or_plant_advances") != 0
            or result.get("calibration_or_holdout_records_read") != 0
            or result.get("controller_or_optimizer_runs") != 0):
        failures.append("FORBIDDEN_EXECUTION_OR_DATA")
    return {
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "stage_config_sha256": primary.CONFIG_SHA256,
        "audit_passed": not failures,
        "failures": failures,
        "primary_sha256": sha256(result_path),
        "primary_route": result.get("route"),
        "primary_passed": result.get("passed"),
        "recomputed_route": recomputed.get("route"),
        "recomputed_winner": recomputed.get("winner"),
        "model_sha256": result.get("model_sha256"),
        "new_tsc_or_plant_advances": 0,
        "calibration_or_holdout_records_read": 0,
        "claim_boundary": (
            "Same-code deterministic replay audit of the three-context "
            "development comparison; not an independent model implementation."),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-config", type=Path, default=primary.CONFIG)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = audit(args.stage_config, args.run_dir, args.source_revision)
    output = args.output or args.run_dir / "deterministic_replay_audit.json"
    write_new(primary.inside(output, "audit output"), result)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
