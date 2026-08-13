#!/usr/bin/env python3
"""Read-only scientific audit of the immutable stopped 1 ms NR1 run."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    assert_exact_slew,
    decimal_single_turn_currents_a,
)
from tsc_rzip_rllib.core.runner import TSCConfig  # noqa: E402


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _currents(path: Path, cfg: TSCConfig) -> tuple[Decimal, ...]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, skipinitialspace=True)
        key = next((value for value in (reader.fieldnames or []) if "ccoil" in value.lower()), None)
        if key is None:
            raise ValueError(f"ccoil column missing in {path}")
        values = tuple(row[key].strip() for row in reader)
    return decimal_single_turn_currents_a(values, cfg.turns_tsc, name=str(path))


def audit(config_path: Path, run_dir: Path, output: Path) -> dict[str, object]:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    cfg = TSCConfig.from_json(config_path)
    qualification_path = run_dir / "qualification.json"
    rollout_path = run_dir / "pattern_a_primary.json"
    qualification = json.loads(qualification_path.read_text(encoding="utf-8"))
    rollout = json.loads(rollout_path.read_text(encoding="utf-8"))
    before_path = run_dir / "rollouts" / "pattern_a_primary" / "1100ms" / "coil_currents.csv"
    after_path = run_dir / "rollouts" / "pattern_a_primary" / "1101ms" / "coil_currents.csv"
    before = _currents(before_path, cfg)
    after = _currents(after_path, cfg)
    deltas = tuple(right - left for left, right in zip(before, after))
    assert_exact_slew(before, after, name="immutable_nr1_observed")
    exact_maximum = max(abs(value) for value in deltas)
    expected_reason = "OBSERVED_SLEW:pattern_a_primary.observed.0[11] exceeds the exact 0.3 A step limit"
    checks = {
        "old_route_is_safety_stop": qualification.get("route") == "ONE_MS_NR1_SAFETY_FAIL_STOP",
        "old_plant_advances_are_nine": qualification.get("plant_advances") == 9,
        "old_pattern_has_one_advance": rollout.get("plant_advances") == 1,
        "old_reason_is_unique_expected_reason": rollout.get("reasons") == [expected_reason],
        "exact_decimal_slew_passes": exact_maximum <= Decimal("0.3"),
        "pf3l_is_exact_negative_point_three": deltas[11] == Decimal("-0.30000"),
    }
    result: dict[str, object] = {
        "schema_version": "rgeo-zgeo-1ms-nr1r1-failure-forensics-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "passed": all(checks.values()),
        "route": (
            "ONE_MS_NR1_BINARY64_FALSE_SLEW_STOP_CONFIRMED"
            if all(checks.values())
            else "ONE_MS_NR1_FAILURE_CLASSIFICATION_NOT_CONFIRMED"
        ),
        "old_run_remains_incomplete": True,
        "new_tsc_or_plant_advance": 0,
        "checks": checks,
        "exact_observed_delta_a_tsc": [str(value) for value in deltas],
        "exact_maximum_observed_delta_a": str(max(abs(value) for value in deltas)),
        "source_artifacts": {
            str(path.relative_to(run_dir)): {"bytes": path.stat().st_size, "sha256": _sha256(path)}
            for path in (qualification_path, rollout_path, before_path, after_path)
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.config.resolve(), args.run_dir.resolve(), args.output.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
