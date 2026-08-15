#!/usr/bin/env python3
"""Independent deterministic refit/evaluation audit for ID-2B1."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_id2b1_structured_model_development import (  # noqa: E402
    ARTIFACT_SCHEMA,
    CONFIG_SHA256,
    INPUT_FAIL_ROUTE,
    NO_MODEL_ROUTE,
    PASS_ROUTE,
    SCHEMA as PRIMARY_SCHEMA,
    _numeric_max_difference,
    inside,
    load_config,
    load_rows,
    read_json,
    run_development,
    sha256_file,
)


SCHEMA = "rgeo-zgeo-1ms-id2b1-structured-model-independent-v1"


def audit(
    repo_root: Path,
    config_path: Path,
    run_dir: Path,
    output_dir: Path,
    source_revision: str,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    output_dir = inside(repo_root, output_dir, "ID2B1 output directory")
    config = load_config(repo_root, config_path)
    primary_path = output_dir / "result.json"
    artifact_path = output_dir / "model_artifact.json"
    if not primary_path.is_file():
        raise ValueError("missing ID2B1 primary result")
    primary = read_json(primary_path)
    failures: list[str] = []
    if primary.get("schema_version") != PRIMARY_SCHEMA or primary.get("source_revision") != source_revision:
        failures.append("PRIMARY_IDENTITY")
    if primary.get("config_sha256") != CONFIG_SHA256:
        failures.append("PRIMARY_CONFIG")
    if primary.get("route") == INPUT_FAIL_ROUTE:
        failures.append("PRIMARY_INPUT_FAILURE")
    if not artifact_path.is_file():
        failures.append("MISSING_MODEL_ARTIFACT")
        artifact = None
    else:
        artifact = read_json(artifact_path)
        if artifact.get("schema_version") != ARTIFACT_SCHEMA or artifact.get("source_revision") != source_revision:
            failures.append("ARTIFACT_IDENTITY")
        if primary.get("model_artifact_sha256") != sha256_file(artifact_path):
            failures.append("ARTIFACT_HASH")

    _, rows, source_identity = load_rows(repo_root, config, run_dir)
    evaluation, recomputed_artifact = run_development(rows, config)
    recomputed_artifact.update({"source_revision": source_revision, "source_identity": source_identity})
    evaluation_difference = _numeric_max_difference(evaluation, primary.get("evaluation"))
    artifact_difference = math.inf if artifact is None else _numeric_max_difference(recomputed_artifact, artifact)
    if evaluation_difference > 1e-12:
        failures.append("PRIMARY_EVALUATION_RECOMPUTATION")
    if artifact_difference > 1e-12:
        failures.append("MODEL_ARTIFACT_RECOMPUTATION")
    selected = evaluation["selection"]["selected_model_id"]
    expected_passed = selected is not None
    expected_route = PASS_ROUTE if expected_passed else NO_MODEL_ROUTE
    if primary.get("passed") != expected_passed or primary.get("route") != expected_route:
        failures.append("PRIMARY_ROUTE_OR_VERDICT")
    counters = primary.get("counters", {})
    if any(counters.get(key) != 0 for key in ("plant_advances", "tsc_calls", "holdout_records_read", "calibration_records_read")):
        failures.append("PRIMARY_FORBIDDEN_COUNTER")
    if counters.get("models_fit_or_trained") != evaluation["models_fit"]:
        failures.append("PRIMARY_MODEL_FIT_COUNTER")

    result = {
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "config_sha256": CONFIG_SHA256,
        "audit_passed": not failures,
        "failures": list(dict.fromkeys(failures)),
        "primary_result_sha256": sha256_file(primary_path),
        "model_artifact_sha256": None if artifact is None else sha256_file(artifact_path),
        "maximum_evaluation_difference": evaluation_difference,
        "maximum_artifact_difference": artifact_difference,
        "recomputed_route": expected_route,
        "recomputed_scientific_passed": expected_passed,
        "selected_model_id": selected,
        "evaluation": evaluation,
        "counters": {
            "models_refit_for_audit": evaluation["models_fit"],
            "plant_advances": 0,
            "tsc_calls": 0,
            "holdout_records_read": 0,
            "calibration_records_read": 0,
        },
    }
    output = output_dir / "independent_audit.json"
    if output.exists():
        raise FileExistsError(f"refusing to overwrite independent audit: {output}")
    output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path, default=Path("configs/rgeo_zgeo_1ms_id2b1_structured_model_development.json"))
    parser.add_argument("--id2a-run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    run_dir = args.id2a_run_dir if args.id2a_run_dir.is_absolute() else root / args.id2a_run_dir
    output_dir = args.output_dir if args.output_dir.is_absolute() else root / args.output_dir
    result = audit(root, config_path, run_dir, output_dir, args.source_revision)
    print(json.dumps({
        "audit_passed": result["audit_passed"],
        "failures": result["failures"],
        "recomputed_route": result["recomputed_route"],
        "selected_model_id": result["selected_model_id"],
    }, indent=2, sort_keys=True))
    return 0 if result["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
