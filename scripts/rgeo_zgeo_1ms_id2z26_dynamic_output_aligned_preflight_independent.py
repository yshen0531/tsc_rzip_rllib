#!/usr/bin/env python3
"""Independent static-stream audit for the zero-TSC ID-2Z26 preflight."""

from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_id2z24_centered_coallocation_preflight as z24  # noqa: E402


CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z26_dynamic_output_aligned_preflight.json"
CONFIG_SHA256 = "0c843a3f4ab61e5f693d7f37aef2961ccd319d7f54d3104c70590878443d8d8d"
SCHEMA = "rgeo-zgeo-1ms-id2z26r1-dynamic-output-aligned-independent-v1"
PRIMARY_SCHEMA = "rgeo-zgeo-1ms-id2z26r1-dynamic-output-aligned-preflight-result-v1"


def _inside(path: Path) -> Path:
    value = path.resolve()
    value.relative_to(ROOT)
    return value


def _sha(path: Path) -> str:
    return hashlib.sha256(_inside(path).read_bytes()).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(_inside(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON object required")
    return value


def _scaled(values: Sequence[Decimal], scale: Decimal) -> tuple[Decimal, ...]:
    return tuple(scale * value for value in values)


def _combine(left: Sequence[Decimal], right: Sequence[Decimal], sign: int) -> tuple[Decimal, ...]:
    return tuple(a + Decimal(sign) * b for a, b in zip(left, right))


def execute(primary_path: Path, source_revision: str) -> dict[str, Any]:
    if _sha(CONFIG) != CONFIG_SHA256:
        raise ValueError("config hash mismatch")
    stage, primary = _read(CONFIG), _read(primary_path)
    failures: list[str] = []
    if (primary.get("schema_version") != PRIMARY_SCHEMA
            or primary.get("source_revision") != source_revision
            or primary.get("stage_config_sha256") != CONFIG_SHA256):
        failures.append("PRIMARY_IDENTITY")
    evidence: dict[str, dict[str, Any]] = {}
    for name, spec in stage["evidence"].items():
        path = _inside(ROOT / spec["path"])
        if _sha(path) != spec["sha256"]:
            failures.append(f"EVIDENCE_HASH:{name}")
        elif path.suffix == ".json":
            evidence[name] = _read(path)
    baseline = evidence.get("baseline_full_f", {})
    base = evidence.get("base_tsc_config", {})
    if not baseline or not base:
        failures.append("EVIDENCE_LOAD")
        return {"schema_version": SCHEMA, "source_revision": source_revision,
                "primary_sha256": _sha(primary_path), "audit_passed": False,
                "failures": failures, "tsc_calls": 0, "plant_advances": 0}
    turns = tuple(Decimal(str(value)) for value in base["turns_display_order"])
    lower = np.asarray(base["min_current_a_display_order"], dtype=float)
    upper = np.asarray(base["max_current_a_display_order"], dtype=float)
    f = z24._field_delta(baseline, 24)
    n = _scaled(f, Decimal("0.50"))
    r5 = z24._field_delta(evidence["issue24_p05_plus"], 24)
    r6 = _scaled(z24._field_delta(evidence["issue24_p06_plus"], 24), Decimal("0.50"))
    axes = {"q_r": _scaled(_combine(r5, r6, -1), Decimal("0.50")),
            "q_z": _scaled(_combine(r5, r6, 1), Decimal("0.50"))}
    if primary.get("nominal_field_increment") != [str(v) for v in n]:
        failures.append("NOMINAL_FIELDS")
    if primary.get("output_aligned_field_increments") != {
            key: [str(v) for v in values] for key, values in axes.items()}:
        failures.append("AXIS_FIELDS")
    streams = primary.get("prospective_static_streams", [])
    if [row.get("rollout_id") for row in streams] != stage["prospective_rollout_ids"]:
        failures.append("ROLLOUT_IDS")
    by_id = {row.get("rollout_id"): row for row in streams}
    expected_prefix = [row["expected_card15_fields"] for row in baseline["actions"][:32]]
    recomputed_rows: list[dict[str, Any]] = []
    for rollout_id in stage["prospective_rollout_ids"]:
        row = by_id.get(rollout_id, {})
        fields = row.get("card15_targets", [])
        local: list[str] = []
        if len(fields) != 73 or any(len(value) != 14 for value in fields):
            local.append("FIELD_SHAPE")
        elif fields[:32] != expected_prefix:
            local.append("FULL_F_PREFIX")
        if not local:
            currents = [z24._currents(value, turns) for value in fields]
            maximum = max(float(np.max(np.abs(currents[i] - currents[i - 1])))
                          for i in range(1, len(currents)))
            headroom = min(float(np.min(np.minimum(value - lower, upper - value)))
                           for value in currents)
            if maximum > stage["static_gates"]["maximum_absolute_issued_delta_a"]:
                local.append("SLEW")
            if headroom < stage["static_gates"]["minimum_absolute_current_headroom_a"]:
                local.append("HEADROOM")
            if abs(maximum - float(row.get("maximum_issued_delta_a", math.nan))) > 1e-9:
                local.append("PRIMARY_SLEW")
            if abs(headroom - float(row.get("minimum_absolute_current_headroom_a", math.nan))) > 1e-9:
                local.append("PRIMARY_HEADROOM")
            if fields[-1] != row.get("terminal_card15_fields"):
                local.append("TERMINAL_FIELDS")
        if rollout_id.startswith("issue"):
            phase = int(rollout_id[5:7])
            center = by_id.get("baseline_transition_center", {}).get("card15_targets", [])
            if fields[:phase] != center[:phase]:
                local.append("BRANCH_PREFIX")
            if len(fields) == 73 and len(center) == 73 and fields[phase + 15] != center[phase + 15]:
                local.append("BRANCH_CLOSURE")
        recomputed_rows.append({"rollout_id": rollout_id, "failures": local,
                                "passed": not local})
        failures.extend(f"STREAM:{rollout_id}:{reason}" for reason in local)
    checks = primary.get("local_vertex_checks", [])
    if len(checks) != 24:
        failures.append("LOCAL_CHECK_COUNT")
    else:
        for row in checks:
            if (row.get("rank") != 2 or row.get("condition", math.inf) > 1.2
                    or row.get("maximum_signed_issued_delta_a", math.inf) > 0.3000000001
                    or row.get("minimum_signed_target_headroom_a", -math.inf) < 0.0
                    or row.get("passed") is not True):
                failures.append(f"LOCAL_CHECK:{row.get('issue')}")
    expected_route = stage["routes"]["pass"] if not failures else primary.get("route")
    if not failures and (primary.get("route") != stage["routes"]["pass"]
                         or primary.get("passed") is not True
                         or primary.get("failures") != []):
        failures.append("PRIMARY_VERDICT")
    return {
        "schema_version": SCHEMA, "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "primary_sha256": _sha(primary_path),
        "primary_route": primary.get("route"), "expected_route": expected_route,
        "audit_passed": not failures, "failures": failures,
        "stream_checks": recomputed_rows,
        "models_fit_or_updated": 0, "tsc_calls": 0, "plant_advances": 0,
        "claim_boundary": stage["claim_boundary"],
    }


def _write_new(path: Path, value: dict[str, Any]) -> None:
    output = _inside(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        value = execute(args.primary, args.source_revision)
    except Exception as exc:
        value = {"schema_version": SCHEMA, "source_revision": args.source_revision,
                 "audit_passed": False, "failures": [f"{type(exc).__name__}:{exc}"],
                 "tsc_calls": 0, "plant_advances": 0}
    _write_new(args.output, value)
    print(json.dumps(value, sort_keys=True))
    return 0 if value["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
