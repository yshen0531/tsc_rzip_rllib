#!/usr/bin/env python3
"""Independent full-raw route audit for ID-2Z15."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_id0_vector_tail import write_new  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2z9_late_root_branch_utility_support_independent as z9i  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2z15_headroom_nominal_frontier as primary  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-id2z15-independent-raw-v1"


def inside(path: Path, label: str) -> Path:
    value = path.resolve()
    try:
        value.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(f"{label} leaves repository") from exc
    return value


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("object required")
    return value


def expected_streams(stage: dict[str, Any], cfg: Any, targets: dict[str, Any],
                     result: dict[str, Any]) -> list[dict[str, Any]]:
    branches = primary.build_matrix(stage, cfg, targets)
    selected = result.get("scientific_metrics", {}).get("selected_arm_id")
    stream = next((value for value in branches if value["arm_id"] == selected), None)
    return [*branches, *([primary.replay_stream(stream)] if stream else [])]


def compact_rows(run_dir: Path, expected: Sequence[dict[str, Any]],
                 failures: list[str]) -> list[dict[str, Any]]:
    excluded = {"result.json", "offline_preflight.json", "independent_raw_audit.json"}
    rows = [load_json(path) for path in sorted(run_dir.glob("*.json"))
            if path.name not in excluded]
    rows = [row for row in rows if "rollout_id" in row]
    order = {row["rollout_id"]: index for index, row in enumerate(expected)}
    rows.sort(key=lambda row: order.get(str(row.get("rollout_id")), 999))
    ids = [str(row.get("rollout_id")) for row in rows]
    expected_ids = [row["rollout_id"] for row in expected]
    if ids != expected_ids[:len(ids)] or len(ids) != len(set(ids)):
        failures.append("COMPACT_ORDER_OR_IDENTITY")
    return rows


def audit(stage_path: Path, run_dir: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    stage_path, run_dir = inside(stage_path, "config"), inside(run_dir, "run")
    result = load_json(run_dir / "result.json")
    try:
        stage, runtime, cfg, targets, reference = primary.load(stage_path)
        expected = expected_streams(stage, cfg, targets, result)
    except Exception as exc:
        failures.append(f"STAGE_LOAD:{type(exc).__name__}:{exc}")
        stage, runtime, cfg, targets, reference, expected = (
            load_json(stage_path), {}, None, {}, {}, [])
    compact = compact_rows(run_dir, expected, failures)
    for row in compact:
        if (row.get("schema_version") != primary.SCHEMA
                or row.get("source_revision") != source_revision):
            failures.append(f"COMPACT_IDENTITY:{row.get('rollout_id')}")
    rollout_root = run_dir / "rollouts"
    actual_ids = (sorted(path.name for path in rollout_root.iterdir() if path.is_dir())
                  if rollout_root.is_dir() else [])
    if actual_ids != sorted(str(row.get("rollout_id")) for row in compact):
        failures.append("ROLLOUT_DIRECTORY_SET")
    raw_rows: list[dict[str, Any]] = []
    inventory_lines: list[str] = []
    inventory_bytes = 0
    if cfg is not None:
        raw_rows, inventory_lines, inventory_bytes = z9i._raw_rows(
            run_dir, cfg, expected, compact, failures)
    digest = hashlib.sha256(
        "".join(f"{line}\n" for line in sorted(inventory_lines)).encode()).hexdigest()
    if digest != result.get("required_artifact_inventory_sha256"):
        failures.append("INVENTORY_SHA256")
    if (len(inventory_lines) != result.get("required_artifact_files")
            or inventory_bytes != result.get("required_artifact_bytes")):
        failures.append("INVENTORY_COUNT_OR_BYTES")
    compact_by_id = {str(row.get("rollout_id")): row for row in compact}
    raw_by_id = {str(row.get("rollout_id")): row for row in raw_rows}
    branches = [raw_by_id[f"branch__{arm}"] for arm in primary.ARM_IDS
                if f"branch__{arm}" in raw_by_id]
    metrics = primary._metrics(branches, stage)
    selected = metrics.get("selected_arm_id")
    replay = raw_by_id.get("critical_replay")
    replay_ok = bool(selected and primary.z6.replay_check(
        raw_by_id.get(f"branch__{selected}"), replay,
        stage["semantic_artifacts"])["passed"])
    prefix_values: list[dict[str, Any]] = []
    for arm in primary.ARM_IDS:
        row = compact_by_id.get(f"branch__{arm}")
        if row:
            prefix_values.append(primary.z6.prefix_check(
                row, reference, 1, 0, stage["semantic_artifacts"]))
    if replay is not None and selected:
        prefix_values.append(primary.z6.prefix_check(
            compact_by_id.get("critical_replay", {}),
            compact_by_id.get(f"branch__{selected}", {}), 49, 48,
            stage["semantic_artifacts"]))
    execution = bool(raw_rows and all(
        row.get("passed") or primary.z6.safe_stop(row, runtime) for row in raw_rows))
    prefixes_ok = bool(prefix_values and all(value.get("passed") for value in prefix_values))
    expected_files = 5 * sum(len(row.get("states", [])) for row in raw_rows)
    raw_ok = bool(execution and len(inventory_lines) == expected_files
                  and not any(value.startswith("MISSING_ARTIFACT") for value in failures))
    route = primary.route_for(stage, execution, raw_ok, prefixes_ok, metrics, replay_ok)
    scientific = {"frontier_metrics": metrics, "selected_arm_id": selected,
                  "selected_capture_passed": metrics.get("selected_capture_passed", False),
                  "selected_headroom_development_passed": metrics.get(
                      "selected_headroom_development_passed", False),
                  "selected_replay_exact_passed": replay_ok}
    if result.get("prefix_checks") != prefix_values:
        failures.append("RECOMPUTE_PREFIX_CHECKS")
    if result.get("scientific_metrics") != scientific:
        failures.append("RECOMPUTE_SCIENTIFIC_METRICS")
    positive = {stage["routes"]["capture_pass"], stage["routes"]["headroom_pass"]}
    if result.get("route") != route or result.get("passed") != (route in positive):
        failures.append("PRIMARY_ROUTE_OR_VERDICT")
    counters = {key: sum(int(row.get(key, 0)) for row in compact) for key in
                ("reset_calls", "advance_attempts", "plant_advance_gotsc_calls",
                 "verified_plant_advances")}
    for key, value in counters.items():
        if result.get(key) != value:
            failures.append(f"COUNTER:{key}")
    failures = list(dict.fromkeys(failures))
    return {"schema_version": SCHEMA, "source_revision": source_revision,
            "stage_config_sha256": primary.CONFIG_SHA256,
            "primary_sha256": primary.io.sha256(run_dir / "result.json"),
            "audit_passed": not failures, "failures": failures,
            "recomputed_route": route, "recomputed_scientific_metrics": scientific,
            "recomputed_prefix_checks": prefix_values,
            "recomputed_required_artifact_files": len(inventory_lines),
            "recomputed_required_artifact_bytes": inventory_bytes,
            "recomputed_required_artifact_inventory_sha256": digest,
            **counters, "models_fit_or_updated": 0,
            "calibration_or_holdout_records_read": 0,
            "claim_boundary": "Independent full-raw audit of finite ID2Z15 only."}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-config", type=Path, default=primary.CONFIG)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    value = audit(args.stage_config, args.run_dir, args.source_revision)
    write_new(inside(args.output, "audit output"), value)
    print(json.dumps(value, indent=2, sort_keys=True, allow_nan=False))
    return 0 if value["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
