#!/usr/bin/env python3
"""Read-only audit of the immutable NR1R1 command/readback-coordinate stop."""

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


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _currents(path: Path, cfg: TSCConfig) -> tuple[Decimal, ...]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, skipinitialspace=True)
        key = next(value for value in (reader.fieldnames or []) if "ccoil" in value.lower())
        values = tuple(row[key].strip() for row in reader)
    return decimal_single_turn_currents_a(values, cfg.turns_tsc, name=str(path))


def _target(fields: list[str], cfg: TSCConfig, name: str) -> tuple[Decimal, ...]:
    return decimal_single_turn_currents_a(
        tuple(value.strip() for value in fields), cfg.turns_tsc, name=name
    )


def audit(config: Path, run: Path, output: Path) -> dict[str, object]:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    cfg = TSCConfig.from_json(config)
    qualification_path = run / "qualification.json"
    rollout_path = run / "pattern_a_primary.json"
    offline_path = run / "offline_preflight.json"
    qualification = json.loads(qualification_path.read_text(encoding="utf-8"))
    rollout = json.loads(rollout_path.read_text(encoding="utf-8"))
    offline = json.loads(offline_path.read_text(encoding="utf-8"))
    before_path = run / "rollouts/pattern_a_primary/1100ms/coil_currents.csv"
    after_path = run / "rollouts/pattern_a_primary/1101ms/coil_currents.csv"
    before, after = _currents(before_path, cfg), _currents(after_path, cfg)
    pulse = _target(rollout["actions"][0]["expected_card15_fields"], cfg, "pulse")
    q0 = _target(offline["frozen_prefixes"]["q0"]["card15_fields"], cfg, "q0")
    observed = assert_exact_slew(before, after, name="observed")
    command_return = assert_exact_slew(pulse, q0, name="command_return")
    mixed_delta = max(abs(value - target) for value, target in zip(after, q0))
    expected = "ISSUED_SLEW:pattern_a_primary.issued.1[11] exceeds the exact 0.3 A step limit"
    checks = {
        "nr1r1_route_is_safety_stop": qualification.get("route") == "ONE_MS_NR1R1_SAFETY_FAIL_STOP",
        "plant_advances_are_nine": qualification.get("plant_advances") == 9,
        "pattern_has_one_advance": rollout.get("plant_advances") == 1,
        "reason_is_unique_expected_reason": rollout.get("reasons") == [expected],
        "observed_pulse_maximum_is_point_three": Decimal(str(observed)) == Decimal("0.3"),
        "command_return_maximum_is_point_three": Decimal(str(command_return)) == Decimal("0.3"),
        "mixed_coordinate_exceeds_point_three": mixed_delta > Decimal("0.3"),
        "pf3l_mixed_coordinate_is_point_three_zero_zero_zero_one": mixed_delta == Decimal("0.30001"),
    }
    passed = all(checks.values())
    artifacts = (qualification_path, rollout_path, offline_path, before_path, after_path)
    result: dict[str, object] = {
        "schema_version": "rgeo-zgeo-1ms-nr1r2-failure-forensics-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "route": "ONE_MS_NR1R1_COMMAND_READBACK_MIX_CONFIRMED" if passed else "ONE_MS_NR1R1_STOP_NOT_CONFIRMED",
        "old_run_remains_incomplete": True,
        "new_tsc_or_plant_advance": 0,
        "checks": checks,
        "exact_maximum_observed_pulse_delta_a": str(max(abs(b-a) for a,b in zip(before,after))),
        "exact_maximum_command_return_delta_a": str(max(abs(b-a) for a,b in zip(pulse,q0))),
        "exact_maximum_mixed_coordinate_delta_a": str(mixed_delta),
        "source_artifacts": {
            str(path.relative_to(run)): {"bytes": path.stat().st_size, "sha256": _sha(path)}
            for path in artifacts
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
