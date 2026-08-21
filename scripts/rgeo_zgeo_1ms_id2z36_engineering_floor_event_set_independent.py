#!/usr/bin/env python3
"""Independent recomputation for the zero-TSC ID2Z36 payload."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z36_engineering_floor_event_set.json"
SCHEMA = "rgeo-zgeo-1ms-id2z36-engineering-floor-event-set-independent-v1"
KEYS = ("r_geo_m", "z_geo_m", "ip_a")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    path = path.resolve()
    path.relative_to(ROOT)
    return json.loads(path.read_text(encoding="utf-8"))


def audit(config: Path, primary: Path, revision: str) -> dict[str, Any]:
    cfg, result = load(config), load(primary)
    failures: list[str] = []
    source_path = ROOT / cfg["evidence"]["id2z34_result"]["path"]
    source_result = load(source_path)
    if digest(source_path) != cfg["evidence"]["id2z34_result"]["sha256"]:
        failures.append("SOURCE_HASH")
    source = source_result["model_payload"]
    payload = result.get("model_payload", {})
    if result.get("source_revision") != revision or result.get("stage_config_sha256") != digest(config):
        failures.append("PRIMARY_IDENTITY")
    if result.get("models_fit_or_updated") != 0 or result.get("plant_advances") != 0 or result.get("id2z35_fit_rows") != 0:
        failures.append("PRIMARY_ZERO_USE")
    if payload.get("point_centers") != source.get("point_centers"):
        failures.append("POINT_CENTERS_CHANGED")
    if payload.get("candidate_b") != source.get("candidate_b"):
        failures.append("NON_EVENT_METRICS_CHANGED")
    events = payload.get("event_sets", [])
    source_events = source.get("event_sets", [])
    if len(events) != 1 or len(source_events) != 1:
        failures.append("EVENT_COUNT")
    else:
        event, old = events[0], source_events[0]
        if (event.get("axis_sign"), event.get("effect_age")) != (cfg["event_coordinate"]["axis_sign"], cfg["event_coordinate"]["effect_age"]):
            failures.append("EVENT_COORDINATE")
        expected = [max(float(old["half_width"][i]), float(cfg["engineering_half_width_floor"][key])) for i, key in enumerate(KEYS)]
        if event.get("half_width") != expected or event.get("full_width") != [2.0 * x for x in expected]:
            failures.append("EVENT_WIDTH")
    payload_without = dict(payload)
    claimed = payload_without.pop("payload_sha256", None)
    if claimed != canonical_sha(payload_without):
        failures.append("PAYLOAD_SHA")
    if result.get("model_payload_sha256") != claimed:
        failures.append("PRIMARY_PAYLOAD_SHA")
    expected_pass = not failures
    if result.get("passed") is not True or result.get("route") != cfg["routes"]["pass"]:
        failures.append("PRIMARY_VERDICT")
    return {
        "schema_version": SCHEMA,
        "source_revision": revision,
        "audit_passed": not failures and expected_pass,
        "failures": failures,
        "primary_sha256": digest(primary),
        "recomputed_payload_sha256": claimed,
        "models_fit_or_updated": 0,
        "plant_advances": 0,
        "id2z35_fit_rows": 0,
        "recomputed_route": cfg["routes"]["pass"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.config, args.primary, args.source_revision)
    out = args.output.resolve(); out.relative_to(ROOT)
    if out.exists(): raise FileExistsError(str(out))
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0 if result["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
