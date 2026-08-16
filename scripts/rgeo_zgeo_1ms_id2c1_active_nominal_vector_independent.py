#!/usr/bin/env python3
"""Independent raw audit for the finite ID-2C1 development search."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_id0_vector_tail_independent import ARTIFACTS, _fields, _sha, _state  # noqa: E402
from scripts.rgeo_zgeo_1ms_id1a_context_anchor_pilot_independent import _numeric_max_difference  # noqa: E402
from scripts.rgeo_zgeo_1ms_id2c1_active_nominal_vector_search import (  # noqa: E402
    CONFIG_SHA256,
    SCHEMA as PRIMARY_SCHEMA,
    _phase_a_metrics,
    _phase_b_metrics,
    load,
    write_new,
)


SCHEMA = "rgeo-zgeo-1ms-id2c1-active-nominal-vector-independent-v1"


def _inside(path: Path, label: str) -> Path:
    result = path.resolve()
    try:
        result.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} leaves repository root") from exc
    return result


def audit(stage_path: Path, run_dir: Path, destination: Path | None = None) -> dict[str, Any]:
    failures: list[str] = []
    stage_path = _inside(stage_path, "stage config")
    run_dir = _inside(run_dir, "run directory")
    if _sha(stage_path) != CONFIG_SHA256:
        failures.append("STAGE_SHA256")
    try:
        stage, cfg, _, _ = load(stage_path)
    except Exception as exc:
        failures.append(f"STAGE_LOAD:{type(exc).__name__}:{exc}")
        stage = json.loads(stage_path.read_text(encoding="utf-8"))
        cfg = None
    primary_path = run_dir / "result.json"
    primary = json.loads(primary_path.read_text(encoding="utf-8")) if primary_path.is_file() else {}
    if primary.get("schema_version") != PRIMARY_SCHEMA:
        failures.append("PRIMARY_SCHEMA")
    compact_paths = sorted(
        path for path in run_dir.glob("*.json") if path.name not in ("result.json", "offline_preflight.json", "independent_audit.json")
    )
    compact_rows = [json.loads(path.read_text(encoding="utf-8")) for path in compact_paths]
    actual_ids = sorted(path.name for path in (run_dir / "rollouts").iterdir() if path.is_dir()) if (run_dir / "rollouts").is_dir() else []
    expected_ids = sorted(row["rollout_id"] for row in compact_rows)
    if actual_ids != expected_ids:
        failures.append("ROLLOUT_DIRECTORY_SET")
    raw_rows = []
    inventory_lines = []
    inventory_bytes = 0
    if cfg is not None:
        for compact in compact_rows:
            rollout_id = compact["rollout_id"]
            folder = run_dir / "rollouts" / rollout_id
            times = [int(state["time_ms"]) for state in compact["states"]]
            actual_times = sorted(int(path.name[:-2]) for path in folder.iterdir() if path.is_dir() and path.name.endswith("ms"))
            if actual_times != times:
                failures.append(f"STATE_DIRECTORY_SET:{rollout_id}")
                continue
            states = []
            for index, time_ms in enumerate(times):
                state_folder = folder / f"{time_ms}ms"
                try:
                    state = _state(state_folder, cfg)
                    states.append(state)
                except Exception as exc:
                    failures.append(f"RAW_STATE:{rollout_id}:{time_ms}:{type(exc).__name__}:{exc}")
                    continue
                expected = compact["states"][index]
                for key, tolerance in (("r_geo_m", 1e-12), ("z_geo_m", 1e-12), ("r_mid_m", 1e-12), ("ip_a", 1e-9)):
                    if abs(float(state[key]) - float(expected[key])) > tolerance:
                        failures.append(f"STATE_VALUE:{rollout_id}:{time_ms}:{key}")
                if len(state["actual_current_decimal_a_tsc"]) != 14 or len(state["wire_current_a"]) != 48:
                    failures.append(f"STATE_VECTOR_LENGTH:{rollout_id}:{time_ms}")
                for name in ARTIFACTS:
                    path = state_folder / name
                    if not path.is_file():
                        failures.append(f"MISSING_ARTIFACT:{rollout_id}:{time_ms}:{name}")
                        continue
                    size = path.stat().st_size
                    label = path.relative_to(run_dir).as_posix()
                    inventory_lines.append(f"{label}\t{size}\t{_sha(path)}")
                    inventory_bytes += size
            for issue, action in enumerate(compact["actions"]):
                try:
                    observed = list(_fields(folder / f"{1100 + issue}ms" / "inputa"))
                    if observed != action["expected_card15_fields"]:
                        failures.append(f"ISSUED_CARD15:{rollout_id}:{issue}")
                except Exception as exc:
                    failures.append(f"INPUTA:{rollout_id}:{issue}:{type(exc).__name__}:{exc}")
            raw_rows.append({**{key: value for key, value in compact.items() if key not in ("states", "actions")}, "states": states, "actions": compact["actions"]})
    payload = "".join(f"{line}\n" for line in sorted(inventory_lines)).encode()
    inventory_sha = hashlib.sha256(payload).hexdigest()
    if inventory_sha != primary.get("required_artifact_inventory_sha256"):
        failures.append("INVENTORY_SHA256")
    if len(inventory_lines) != primary.get("required_artifact_files") or inventory_bytes != primary.get("required_artifact_bytes"):
        failures.append("INVENTORY_COUNT_OR_BYTES")
    phase_a_rows = [row for row in raw_rows if row.get("phase") == "A"]
    phase_b_rows = [row for row in raw_rows if row.get("phase") == "B"]
    raw_phase_a, raw_selected = _phase_a_metrics(phase_a_rows, stage)
    raw_phase_b = _phase_b_metrics(phase_b_rows)
    if raw_selected != primary.get("selected_nominal_candidate_id"):
        failures.append("SELECTED_NOMINAL")
    if _numeric_max_difference(raw_phase_a, primary.get("phase_a_metrics")) > 1e-12:
        failures.append("PHASE_A_METRICS")
    if _numeric_max_difference(raw_phase_b, primary.get("phase_b_metrics")) > 1e-12:
        failures.append("PHASE_B_METRICS")
    counters = {
        "rollouts_completed": len(compact_rows),
        "reset_calls": sum(row.get("reset_calls", 0) for row in compact_rows),
        "advance_attempts": sum(row.get("advance_attempts", 0) for row in compact_rows),
        "plant_advance_gotsc_calls": sum(row.get("plant_advance_gotsc_calls", 0) for row in compact_rows),
        "verified_plant_advances": sum(row.get("verified_plant_advances", 0) for row in compact_rows),
    }
    for key, value in counters.items():
        if value != primary.get(key):
            failures.append(f"COUNTER:{key}")
    result = {
        "schema_version": SCHEMA,
        "primary_sha256": _sha(primary_path) if primary_path.is_file() else None,
        "audit_passed": not failures,
        "failures": list(dict.fromkeys(failures)),
        "raw_rollouts": len(raw_rows),
        "raw_states": sum(len(row["states"]) for row in raw_rows),
        "recomputed_phase_a_metrics": raw_phase_a,
        "recomputed_selected_nominal_candidate_id": raw_selected,
        "recomputed_phase_b_metrics": raw_phase_b,
        "recomputed_counters": counters,
        "recomputed_inventory_sha256": inventory_sha,
        "claim_boundary": "Independent raw reparse of finite empirical development; not a model, tube, controller or safety qualification.",
    }
    if destination is not None:
        write_new(_inside(destination, "independent output"), result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.stage_config, args.run_dir, args.output)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
