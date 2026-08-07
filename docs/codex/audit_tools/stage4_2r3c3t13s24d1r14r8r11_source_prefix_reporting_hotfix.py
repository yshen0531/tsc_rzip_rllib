#!/usr/bin/env python3
"""Repair only R8R11's over-broad source-wrapper prefix reporting gate."""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any, Mapping

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r9_measured_multipulse_authority_audit as r8r9,
)


STAGE = "Stage4.2R3c3T13S24D1R14R8R11"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r11_sustained_exact_target_refresh_authority_sentinel"
PRIMARY_MODULE = (
    "tsc_rzip_rllib/diagnostics/"
    "stage4_2r3c3t13s24d1r14r8r11_sustained_exact_target_refresh_authority_sentinel.py"
)
ORIGINAL_PRIMARY_MODULE_SHA256 = (
    "dd4ed57184d7ce6543b2e93f1425c7a95c31e86df0948a922c8d06e99190fafd"
)
SOURCE_WRAPPER_METADATA_PREFIXES = (
    "r3c3t13s24d1r14r4_",
    "r3c3t13s24d1r14r8r7_",
)
PREFIX_END = 10


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


def _read(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def _gzip(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(
            stream,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inventory(path: Path) -> dict[str, Any]:
    files = sorted(path.glob("*.json.gz"), key=lambda value: value.name)
    digest = hashlib.sha256()
    rows = []
    for value in files:
        size = value.stat().st_size
        sha = _sha(value)
        digest.update(f"{value.name}\0{size}\0{sha}\n".encode())
        rows.append({"name": value.name, "size": size, "sha256": sha})
    return {
        "count": len(rows),
        "bytes": sum(int(row["size"]) for row in rows),
        "digest": digest.hexdigest(),
        "rows": rows,
    }


def _semantic_projection(
    source: Mapping[str, Any], current: Mapping[str, Any]
) -> bool:
    return all(
        current.get(key) == value
        for key, value in source.items()
        if not key.startswith(SOURCE_WRAPPER_METADATA_PREFIXES)
    )


def _differences(
    source: Mapping[str, Any], current: Mapping[str, Any]
) -> list[dict[str, Any]]:
    return [
        {
            "key": key,
            "source": value,
            "current": current.get(key, "<MISSING>"),
            "source_wrapper_metadata": key.startswith(SOURCE_WRAPPER_METADATA_PREFIXES),
        }
        for key, value in source.items()
        if current.get(key, "<MISSING>") != value
    ]


def repair(args: argparse.Namespace) -> dict[str, Any]:
    project = _root()
    cfg = _read(args.config.expanduser().resolve())
    if cfg.get("stage") != STAGE:
        raise ValueError("R8R11 reporting hotfix configuration identity changed")
    if _sha(project / PRIMARY_MODULE) != ORIGINAL_PRIMARY_MODULE_SHA256:
        raise ValueError("R8R11 primary/controller module changed before reporting hotfix")
    stage = args.run_dir.expanduser().resolve() / RUN_NAME
    analysis = stage / "analysis"
    raw = stage / "raw" / "safety"
    source_stage = (
        args.r8r7_run.expanduser().resolve()
        / str(cfg["source_r8r7"]["stage_directory"])
    )
    r8r9._authenticate_r8r7(source_stage, cfg)
    original_primary_path = analysis / "safety_raw_primary.json"
    original_state_path = stage / "stage_state.json"
    preserved_primary = analysis / "safety_raw_primary_pre_source_prefix_reporting_hotfix.json"
    preserved_state = stage / "stage_state_pre_source_prefix_reporting_hotfix.json"
    hotfix_path = analysis / "safety_source_prefix_reporting_hotfix.json"
    if any(path.exists() for path in (preserved_primary, preserved_state, hotfix_path)):
        raise ValueError("R8R11 source-prefix reporting hotfix already attempted")
    primary = _read(original_primary_path)
    state = _read(original_state_path)
    before_inventory = _inventory(raw)
    if (
        state.get("phase_status") != "safety_execution_failed"
        or state.get("finished") is not True
        or int(state.get("new_raw_count", -1)) != 24
        or state.get("verdict", {}).get("route") != cfg["routes"]["execution_fail"]
        or primary.get("passed") is not False
        or int(primary.get("passed_count", -1)) != 0
        or before_inventory != primary.get("raw_inventory")
        or before_inventory["count"] != 24
        or any((stage / "raw" / "qualification").glob("*.json.gz"))
    ):
        raise ValueError("R8R11 reporting hotfix precondition changed")

    corrected = copy.deepcopy(primary)
    corrected_rows = []
    mismatch_key_counts: dict[str, int] = {}
    wrapper_difference_count = 0
    nonwrapper_difference_count = 0
    for row in corrected["rows"]:
        experiment_id = str(row["experiment_id"])
        result = _gzip(raw / f"{experiment_id}.json.gz")
        spec = result["spec"]
        source_id = str(spec["source_r8r7_baseline_experiment_id"])
        source = _gzip(source_stage / "raw" / "baseline" / f"{source_id}.json.gz")
        trace = result.get("controller_trace") or []
        source_trace = source.get("controller_trace") or []
        if len(trace) < PREFIX_END or len(source_trace) < PREFIX_END:
            raise ValueError("R8R11 reporting hotfix prefix trace is incomplete")
        semantic = True
        for current, reference in zip(trace[:PREFIX_END], source_trace[:PREFIX_END]):
            semantic = semantic and _semantic_projection(reference, current)
            for difference in _differences(reference, current):
                key = str(difference["key"])
                mismatch_key_counts[key] = mismatch_key_counts.get(key, 0) + 1
                if difference["source_wrapper_metadata"]:
                    wrapper_difference_count += 1
                else:
                    nonwrapper_difference_count += 1
        required_true = (
            "runtime_success", "full_horizon", "source_prefix_state_exact",
            "calibration_exact", "event_exact", "center_target_exact",
            "zero_non_event_exact", "finite",
        )
        if (
            row.get("source_prefix_trace_exact") is not False
            or not all(row.get(key) is True for key in required_true)
            or int(row.get("forbidden_trace_count", -1)) != 0
            or not semantic
        ):
            raise ValueError("R8R11 reporting hotfix found a non-reporting raw failure")
        row["source_prefix_trace_exact"] = True
        row["passed"] = True
        corrected_rows.append(row)
    if nonwrapper_difference_count != 0 or wrapper_difference_count != 24 * 10 * 13:
        raise ValueError("R8R11 reporting hotfix mismatch classification changed")
    corrected.update(
        {
            "source_prefix_trace_exact_count": 24,
            "passed_count": 24,
            "rows": corrected_rows,
            "passed": True,
            "route": cfg["routes"]["pass"],
            "source_prefix_trace_contract": (
                "all executable source fields exact; source-only R4/R8R7 wrapper metadata excluded"
            ),
            "reporting_hotfix_applied": True,
        }
    )

    shutil.copyfile(original_primary_path, preserved_primary)
    shutil.copyfile(original_state_path, preserved_state)
    _write(original_primary_path, corrected)
    after_inventory = _inventory(raw)
    if after_inventory != before_inventory:
        raise ValueError("R8R11 reporting hotfix changed safety raw")
    hotfix = {
        "schema_version": 1,
        "stage": STAGE,
        "hotfix_kind": "source_wrapper_metadata_reporting_only",
        "primary_controller_module_path": PRIMARY_MODULE,
        "primary_controller_module_sha256": _sha(project / PRIMARY_MODULE),
        "primary_controller_module_unchanged": True,
        "source_authenticated": True,
        "safety_raw_inventory_before": before_inventory,
        "safety_raw_inventory_after": after_inventory,
        "safety_raw_unchanged": True,
        "qualification_raw_count": 0,
        "wrapper_difference_count": wrapper_difference_count,
        "nonwrapper_difference_count": nonwrapper_difference_count,
        "wrapper_mismatch_key_counts": mismatch_key_counts,
        "corrected_prefix_count": 24,
        "corrected_passed_count": 24,
        "preserved_primary_sha256": _sha(preserved_primary),
        "corrected_primary_sha256": _sha(original_primary_path),
        "preserved_state_sha256": _sha(preserved_state),
        "real_tsc_executed_by_hotfix": False,
        "new_raw_count_by_hotfix": 0,
        "controller_or_action_semantics_changed": False,
        "formal_outcomes_opened": False,
        "passed": True,
    }
    _write(hotfix_path, hotfix)
    state.update(
        {
            "phase_status": "safety_primary_ready",
            "finished": False,
            "stop_reason": "",
            "verdict": {},
            "formal_outcomes_opened": False,
            "qualification_outcomes_opened": False,
            "source_prefix_reporting_hotfix_sha256": _sha(hotfix_path),
            "source_prefix_reporting_hotfix_applied": True,
        }
    )
    _write(original_state_path, state)
    return hotfix


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--r8r7-run", type=Path, required=True)
    return parser


def main() -> None:
    result = repair(_parser().parse_args())
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
