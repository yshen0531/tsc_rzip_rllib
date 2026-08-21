#!/usr/bin/env python3
"""Build the frozen zero-TSC ID2Z36 engineering-floor event payload."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z36_engineering_floor_event_set.json"
SCHEMA = "rgeo-zgeo-1ms-id2z36-engineering-floor-event-set-result-v1"
PAYLOAD_SCHEMA = "rgeo-zgeo-1ms-id2z36-engineering-floor-event-payload-v1"
KEYS = ("r_geo_m", "z_geo_m", "ip_a")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical_sha(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def inside(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError("path outside repository: %s" % resolved) from exc
    return resolved


def load_json(path: Path) -> dict[str, Any]:
    with inside(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_new(path: Path, value: Any) -> None:
    path = inside(path)
    if path.exists():
        raise FileExistsError(str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def execute(config: Path, revision: str) -> dict[str, Any]:
    cfg = load_json(config)
    failures: list[str] = []
    exact_contract = {
        "schema_version": "rgeo-zgeo-1ms-id2z36-engineering-floor-event-set-v1",
        "identity": "rgeo-zgeo-1ms-id2z36-engineering-floor-event-set-v1",
        "stage": "ID-2Z36",
        "event_coordinate": {"axis_sign": "q_r:minus", "effect_age": 13},
        "engineering_half_width_floor": {"r_geo_m": 0.000375, "z_geo_m": 0.000075, "ip_a": 30.0},
        "maximum_event_full_width": {"r_geo_m": 0.00075, "z_geo_m": 0.00015, "ip_a": 60.0},
        "fresh_qualification": {"calibration_phase_issue": 48, "blind_phase_issue": 54, "model_refit_after_calibration": False, "blind_open_only_after_calibration_pass": True},
    }
    if any(cfg.get(key) != value for key, value in exact_contract.items()):
        failures.append("EXACT_STAGE_CONTRACT")
    if cfg.get("candidate_count") != 1 or cfg.get("hyperparameter_search") is not False:
        failures.append("CANDIDATE_CONTRACT")
    if cfg.get("models_fit_or_updated") != 0 or cfg.get("plant_advance_gotsc_calls") != 0:
        failures.append("ZERO_EXECUTION_CONTRACT")
    if cfg.get("id2z35_fit_rows") != 0:
        failures.append("ID2Z35_ZERO_FIT")

    loaded: dict[str, dict[str, Any]] = {}
    for name, spec in cfg["evidence"].items():
        path = inside(ROOT / spec["path"])
        if not path.is_file() or sha256(path) != spec["sha256"]:
            failures.append("EVIDENCE_" + name.upper())
            continue
        if path.suffix == ".json":
            loaded[name] = load_json(path)

    z34 = loaded.get("id2z34_result", {})
    z35 = loaded.get("id2z35_result", {})
    z35i = loaded.get("id2z35_independent", {})
    if z34.get("route") != cfg["evidence"]["id2z34_result"]["required_route"]:
        failures.append("ID2Z34_ROUTE")
    source = z34.get("model_payload", {})
    if source.get("payload_sha256") != cfg["evidence"]["id2z34_result"]["required_payload_sha256"]:
        failures.append("ID2Z34_PAYLOAD")
    if z35.get("route") != cfg["evidence"]["id2z35_result"]["required_route"]:
        failures.append("ID2Z35_ROUTE")
    if z35.get("blind_opened") is not False or z35i.get("audit_passed") is not True:
        failures.append("ID2Z35_IDENTITY")

    payload = copy.deepcopy(source)
    payload.pop("payload_sha256", None)
    payload["schema_version"] = PAYLOAD_SCHEMA
    payload["source_payload_sha256"] = cfg["evidence"]["id2z34_result"]["required_payload_sha256"]
    events = payload.get("event_sets", [])
    coordinate = cfg["event_coordinate"]
    if len(events) != 1 or events[0].get("axis_sign") != coordinate["axis_sign"] or int(events[0].get("effect_age", -1)) != coordinate["effect_age"]:
        failures.append("EVENT_COORDINATE")
    else:
        event = events[0]
        original = list(event["half_width"])
        floor = [float(cfg["engineering_half_width_floor"][key]) for key in KEYS]
        updated = [max(float(original[i]), floor[i]) for i in range(3)]
        event["source_half_width"] = original
        event["engineering_half_width_floor"] = floor
        event["half_width"] = updated
        event["full_width"] = [2.0 * x for x in updated]
        caps = [float(cfg["maximum_event_full_width"][key]) for key in KEYS]
        if any(event["full_width"][i] > caps[i] + 1e-15 for i in range(3)):
            failures.append("EVENT_WIDTH_CAP")
        if any(abs(updated[i] - max(float(original[i]), floor[i])) > 1e-15 for i in range(3)):
            failures.append("EVENT_WIDTH_CONSTRUCTION")
    payload["construction"] = "componentwise_max_source_half_width_engineering_floor"
    payload["id2z35_fit_rows"] = 0
    payload["payload_sha256"] = canonical_sha(payload)

    passed = not failures
    route = cfg["routes"]["pass" if passed else ("input_fail" if any(x.startswith("EVIDENCE") or x.endswith("ROUTE") or x.endswith("IDENTITY") for x in failures) else "construction_fail")]
    return {
        "schema_version": SCHEMA,
        "source_revision": revision,
        "stage_config_sha256": sha256(inside(config)),
        "passed": passed,
        "route": route,
        "failures": failures,
        "candidate_count": 1,
        "models_fit_or_updated": 0,
        "plant_advances": 0,
        "tsc_calls": 0,
        "id2z35_fit_rows": 0,
        "calibration_or_holdout_reads": 0,
        "model_payload": payload,
        "model_payload_sha256": payload["payload_sha256"],
        "claim_boundary": cfg["claim_boundary"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = execute(args.config, args.source_revision)
    write_new(args.output, result)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
