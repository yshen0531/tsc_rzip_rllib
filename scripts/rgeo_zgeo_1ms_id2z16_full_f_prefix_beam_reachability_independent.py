#!/usr/bin/env python3
"""Independent full-raw route audit for ID-2Z16."""

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
from scripts import rgeo_zgeo_1ms_id2z16_full_f_prefix_beam_reachability as primary  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-id2z16-independent-raw-v1"


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
                     parent: dict[str, Any], result: dict[str, Any]) -> list[dict[str, Any]]:
    roots = primary.build_round(stage, cfg, targets, parent, 32, 0, "round0")
    root_by_path = {row["path_id"]: row for row in roots}
    beam = result.get("scientific_metrics", {}).get("round0_selected_parent_path_ids", [])
    children: list[dict[str, Any]] = []
    for path in beam:
        root = root_by_path.get(str(path))
        if root is not None:
            children.extend(primary.build_round(
                stage, cfg, targets, root, 40, 1, f"round1__{root['arm_id']}"))
    selected = result.get("scientific_metrics", {}).get("selected_path_id")
    child = next((row for row in children if row["path_id"] == selected), None)
    return [*roots, *children, *([primary.replay_stream(child)] if child else [])]


def compact_rows(run_dir: Path, expected: Sequence[dict[str, Any]],
                 failures: list[str]) -> list[dict[str, Any]]:
    excluded = {"result.json", "offline_preflight.json", "independent_raw_audit.json"}
    rows = [load_json(path) for path in sorted(run_dir.glob("*.json"))
            if path.name not in excluded]
    rows = [row for row in rows if "rollout_id" in row]
    order = {row["rollout_id"]: index for index, row in enumerate(expected)}
    rows.sort(key=lambda row: order.get(str(row.get("rollout_id")), 999))
    ids, expected_ids = ([str(row.get("rollout_id")) for row in rows],
                         [row["rollout_id"] for row in expected])
    if ids != expected_ids[:len(ids)] or len(ids) != len(set(ids)):
        failures.append("COMPACT_ORDER_OR_IDENTITY")
    return rows


def audit(stage_path: Path, run_dir: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    stage_path, run_dir = inside(stage_path, "config"), inside(run_dir, "run")
    result = load_json(run_dir / "result.json")
    try:
        stage, runtime, cfg, targets, parent, reference = primary.load(stage_path)
        expected = expected_streams(stage, cfg, targets, parent, result)
    except Exception as exc:
        failures.append(f"STAGE_LOAD:{type(exc).__name__}:{exc}")
        stage, runtime, cfg, targets, parent, reference, expected = (
            load_json(stage_path), {}, None, {}, {}, {}, [])
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
    root_rows = [raw_by_id[f"round0__{arm}"] for arm in primary.ARM_IDS
                 if f"round0__{arm}" in raw_by_id]
    root_metrics = primary._metrics(root_rows, stage)
    beam = root_metrics.get("ranked_path_ids", [])[:2] if root_metrics.get("complete") else []
    root_by_path = {row.get("path_id"): row for row in compact}
    child_rows = [row for row in raw_rows if int(row.get("round_index", -1)) == 1]
    child_metrics = primary._metrics(child_rows, stage)
    selected = child_metrics.get("selected_path_id")
    replay = raw_by_id.get("critical_replay")
    selected_raw = next((row for row in child_rows if row.get("path_id") == selected), None)
    replay_ok = bool(selected and primary.z6.replay_check(
        selected_raw, replay, stage["semantic_artifacts"])["passed"])
    prefix_values: list[dict[str, Any]] = []
    for arm in primary.ARM_IDS:
        row = compact_by_id.get(f"round0__{arm}")
        if row:
            prefix_values.append(primary.z6.prefix_check(
                row, reference, 33, 32, stage["semantic_artifacts"]))
    for row in compact:
        if int(row.get("round_index", -1)) != 1:
            continue
        parent_row = root_by_path.get(row.get("parent_path_id"))
        prefix_values.append(primary.z6.prefix_check(
            row, parent_row or {}, 41, 40, stage["semantic_artifacts"]))
    if replay is not None and selected_raw is not None:
        prefix_values.append(primary.z6.prefix_check(
            compact_by_id.get("critical_replay", {}),
            compact_by_id.get(selected_raw.get("rollout_id"), {}), 66, 65,
            stage["semantic_artifacts"]))
    execution = bool(raw_rows and all(
        row.get("passed") or primary.z6.safe_stop(row, runtime) for row in raw_rows))
    prefixes_ok = bool(prefix_values and all(value.get("passed") for value in prefix_values))
    expected_files = 5 * sum(len(row.get("states", [])) for row in raw_rows)
    raw_ok = bool(execution and len(inventory_lines) == expected_files
                  and not any(value.startswith("MISSING_ARTIFACT") for value in failures))
    route = primary.route_for(stage, execution, raw_ok, prefixes_ok,
                              root_metrics, child_metrics, replay_ok)
    scientific = {"round0_metrics": root_metrics,
                  "round0_selected_parent_path_ids": beam,
                  "round1_metrics": child_metrics,
                  "selected_path_id": selected,
                  "selected_capture_passed": child_metrics.get(
                      "selected_capture_passed", False),
                  "selected_replay_exact_passed": replay_ok}
    if result.get("prefix_checks") != prefix_values:
        failures.append("RECOMPUTE_PREFIX_CHECKS")
    if result.get("scientific_metrics") != scientific:
        failures.append("RECOMPUTE_SCIENTIFIC_METRICS")
    if (result.get("route") != route
            or result.get("passed") != (route == stage["routes"]["capture_pass"])):
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
            "claim_boundary": "Independent full-raw audit of finite ID2Z16 only."}


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
