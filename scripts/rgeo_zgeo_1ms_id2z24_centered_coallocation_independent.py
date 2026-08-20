#!/usr/bin/env python3
"""Structurally separate audit for the ID-2Z24R2 zero-TSC preflight."""

from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z24_centered_coallocation_preflight.json"
CONFIG_SHA256 = "2ec1a2ec8de0e4abda50cd0203c9f7f3ee327f14ddb8aa7ee08b3391393bf17c"
SCHEMA = "rgeo-zgeo-1ms-id2z24r2-centered-coallocation-independent-v1"


def _path(path: Path) -> Path:
    value = path.resolve()
    value.relative_to(ROOT)
    return value


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(_path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON object required")
    return value


def _sha(path: Path) -> str:
    return hashlib.sha256(_path(path).read_bytes()).hexdigest()


def _d(fields: Sequence[str]) -> tuple[Decimal, ...]:
    if len(fields) != 14:
        raise ValueError("Card15 width")
    return tuple(Decimal(str(value).strip()) for value in fields)


def _fmt(value: Decimal) -> str:
    text = f"{float(value):.3E}"
    return text[:10] if len(text) > 10 else text + " " * (10 - len(text))


def _step(current: Sequence[str], delta: Sequence[Decimal]) -> tuple[str, ...]:
    return tuple(_fmt(a + b) for a, b in zip(_d(current), delta))


def _interpolate(start: Sequence[str], endpoint: Sequence[str],
                 numerator: int, denominator: int) -> tuple[str, ...]:
    left, right = _d(start), _d(endpoint)
    weight = Decimal(numerator) / Decimal(denominator)
    return tuple(_fmt(a + weight * (b - a)) for a, b in zip(left, right))


def _current(fields: Sequence[str], turns: Sequence[Decimal]) -> np.ndarray:
    return np.asarray([float(value * Decimal(1000) / turn)
                       for value, turn in zip(_d(fields), turns)], dtype=float)


def _delta(row: dict[str, Any], issue: int) -> tuple[Decimal, ...]:
    before = _d(row["actions"][issue - 1]["expected_card15_fields"])
    after = _d(row["actions"][issue]["expected_card15_fields"])
    return tuple(b - a for a, b in zip(before, after))


def _response(row: dict[str, Any], baseline: dict[str, Any], state: int) -> np.ndarray:
    return np.asarray([float(row["states"][state][key] - baseline["states"][state][key])
                       for key in ("r_geo_m", "z_geo_m")], dtype=float)


def _fraction(rows: Sequence[np.ndarray]) -> float:
    matrix = np.asarray(rows)
    mean = np.mean(matrix, axis=0)
    return float(len(matrix) * np.dot(mean, mean) / np.sum(matrix * matrix))


def _cos(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.dot(left, right) / (np.linalg.norm(left) * np.linalg.norm(right)))


def _load(stage: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if _sha(CONFIG) != CONFIG_SHA256:
        raise ValueError("config hash")
    values: dict[str, dict[str, Any]] = {}
    for name, spec in stage["evidence"].items():
        path = _path(ROOT / spec["path"])
        if _sha(path) != spec["sha256"]:
            raise ValueError(f"evidence hash:{name}")
        if path.suffix == ".json":
            values[name] = _json(path)
    return values


def _attribution(stage: dict[str, Any], rows: dict[str, dict[str, Any]],
                 turns: Sequence[Decimal]) -> dict[str, Any]:
    base = rows["baseline_full_f"]
    f = _current(base["actions"][24]["expected_card15_fields"], turns) - _current(
        base["actions"][23]["expected_card15_fields"], turns)
    action_rows = []
    names = ("p00_minus", "p05_minus", "p05_plus", "p06_plus")
    for name in names:
        row = rows[f"issue24_{name}"]
        v = _current(row["actions"][24]["expected_card15_fields"], turns) - _current(
            row["actions"][23]["expected_card15_fields"], turns)
        action_rows.append(v - f)
    response: dict[str, float] = {}
    for phase in (24, 32):
        response[str(phase)] = _fraction([
            np.concatenate([_response(rows[f"issue{phase}_{name}"], base, state)
                            for state in range(phase + 1, phase + 9)]) for name in names])
    cross: dict[str, float] = {}
    for horizon in (4, 8):
        odds = []
        for phase in (24, 32):
            odds.append((_response(rows[f"issue{phase}_p05_plus"], base, phase + horizon)
                         - _response(rows[f"issue{phase}_p05_minus"], base, phase + horizon)) / 2)
        cross[str(horizon)] = _cos(odds[0], odds[1])
    return {"replacement_common_action_energy_fraction": _fraction(action_rows),
            "common_rz_response_energy_fraction": response,
            "p05_odd_cross_phase_cosine": cross}


def _headroom(fields: Sequence[str], turns: Sequence[Decimal],
              lower: np.ndarray, upper: np.ndarray) -> float:
    values = _current(fields, turns)
    return float(np.min(np.minimum(values - lower, upper - values)))


def _candidate(stage: dict[str, Any], rows: dict[str, dict[str, Any]],
               turns: Sequence[Decimal], lower: np.ndarray, upper: np.ndarray,
               alpha: str) -> bool:
    base = rows["baseline_full_f"]
    f = _delta(base, 24)
    nominal = tuple(Decimal(alpha) * value for value in f)
    source_keys = {"issue24__p00_minus4": "issue24_p00_minus",
                   "issue24__p05_plus4": "issue24_p05_plus",
                   "issue24__p06_plus4": "issue24_p06_plus"}
    residuals = [tuple(Decimal(spec["scale"]) * value for value in
                       _delta(rows[source_keys[spec["source_rollout"]]], 24))
                 for spec in stage["residual_axes"]]
    center = [tuple(row["expected_card15_fields"]) for row in base["actions"][:16]]
    current = center[-1]
    for issue in range(16, 65):
        if issue <= 47:
            current = _step(current, nominal)
        center.append(current)
    gate = stage["static_gates"]
    for issue in range(16, 48):
        before = center[issue - 1]
        odd = []
        for residual in residuals:
            plus = _step(before, tuple(a + b for a, b in zip(nominal, residual)))
            minus = _step(before, tuple(a - b for a, b in zip(nominal, residual)))
            dp = _current(plus, turns) - _current(before, turns)
            dm = _current(minus, turns) - _current(before, turns)
            if (np.max(np.abs(dp)) > gate["maximum_absolute_issued_delta_a"]
                    or np.max(np.abs(dm)) > gate["maximum_absolute_issued_delta_a"]
                    or _headroom(plus, turns, lower, upper) < 0
                    or _headroom(minus, turns, lower, upper) < 0):
                return False
            odd.append((dp - dm) / 2)
        singular = np.linalg.svd(np.column_stack(odd), compute_uv=False)
        if (np.sum(singular > singular[0] * gate["structural_svd_relative_tolerance"]) != 3
                or singular[0] / singular[2] > gate["maximum_residual_condition"]):
            return False
    for phase in stage["prospective_phase_issue_steps"]:
        for residual in residuals:
            for first in (1, -1):
                fields = list(center[:16])
                current = fields[-1]
                return_start = None
                for issue in range(16, 65):
                    change = nominal
                    if phase <= issue < phase + 8:
                        change = tuple(a + Decimal(first) * b for a, b in zip(nominal, residual))
                    if issue <= 47:
                        if issue == phase + 8:
                            return_start = current
                        if phase + 8 <= issue < phase + 16:
                            if return_start is None:
                                return False
                            next_fields = _interpolate(
                                return_start, center[phase + 15], issue - phase - 7, 8)
                        else:
                            next_fields = _step(current, change)
                        if np.max(np.abs(_current(next_fields, turns) - _current(current, turns))) > gate["maximum_absolute_issued_delta_a"]:
                            return False
                        current = next_fields
                    fields.append(current)
                if fields[:phase] != center[:phase] or fields[phase + 15] != center[phase + 15]:
                    return False
                if min(_headroom(value, turns, lower, upper) for value in fields) < 0:
                    return False
    return True


def execute(primary_path: Path, source_revision: str) -> dict[str, Any]:
    stage = _json(CONFIG)
    rows = _load(stage)
    primary = _json(primary_path)
    base = rows["base_tsc_config"]
    turns = tuple(Decimal(str(value)) for value in base["turns_display_order"])
    lower = np.asarray(base["min_current_a_display_order"], dtype=float)
    upper = np.asarray(base["max_current_a_display_order"], dtype=float)
    attribution = _attribution(stage, rows, turns)
    passing = [value for value in stage["nominal_share_candidates_descending"]
               if _candidate(stage, rows, turns, lower, upper, value)]
    selected = passing[0] if passing else None
    failures: list[str] = []
    if primary.get("stage_config_sha256") != CONFIG_SHA256:
        failures.append("PRIMARY_CONFIG")
    if primary.get("selected_nominal_share") != selected:
        failures.append("SELECTED_SHARE")
    if primary.get("route") != (stage["routes"]["pass"] if selected else
                                stage["routes"]["exact_lattice_fail"]):
        failures.append("PRIMARY_ROUTE")
    if primary.get("passed") is not bool(selected):
        failures.append("PRIMARY_VERDICT")
    reported = primary.get("attribution", {})
    for key in ("replacement_common_action_energy_fraction",):
        if abs(float(reported.get(key, math.nan)) - float(attribution[key])) > 1e-12:
            failures.append(f"ATTRIBUTION:{key}")
    for group in ("common_rz_response_energy_fraction", "p05_odd_cross_phase_cosine"):
        for key, value in attribution[group].items():
            if abs(float(reported.get(group, {}).get(key, math.nan)) - value) > 1e-12:
                failures.append(f"ATTRIBUTION:{group}:{key}")
    return {
        "schema_version": SCHEMA, "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "primary_sha256": _sha(primary_path),
        "primary_route": primary.get("route"), "primary_passed": primary.get("passed"),
        "independently_selected_nominal_share": selected,
        "independently_passing_nominal_shares": passing,
        "independent_attribution": attribution,
        "audit_passed": not failures, "failures": failures,
        "models_fit_or_updated": 0, "new_tsc_or_plant_advances": 0,
        "claim_boundary": "Independent exact-action audit of zero-TSC ID2Z24R2 only.",
    }


def _write(path: Path, value: dict[str, Any]) -> None:
    output = _path(path)
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
        result = execute(args.primary, args.source_revision)
    except Exception as exc:
        result = {"schema_version": SCHEMA, "source_revision": args.source_revision,
                  "stage_config_sha256": CONFIG_SHA256, "audit_passed": False,
                  "failures": [f"{type(exc).__name__}:{exc}"],
                  "models_fit_or_updated": 0, "new_tsc_or_plant_advances": 0}
    _write(args.output, result)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
