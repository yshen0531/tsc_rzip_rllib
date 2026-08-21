#!/usr/bin/env python3
"""Read-only forensic of the frozen ID2Z32 compact action streams."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/codex/audits/rgeo_zgeo_1ms_id2z32_20260821_c6b1c5b9_v1"
SCHEMA = "rgeo-zgeo-1ms-id2z32-action-stream-forensic-v1"
EXPECTED = {
    "result.json": "b704bc754d537cd1c4d885541dd687b3bb359b1742f98a03b5c895398f5b0e7d",
    "independent_raw_audit.json": "e478e79f0d5424f2cdb867011d7eaebe909a5c280d4f7a369cf1666dd62b83a9",
    "baseline_transition_center.json": "90d6b70a3f3680816ccb923308cbae500004d3ce3bdeeebccc62c7a11422b1f1",
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _action_key(action: dict[str, Any]) -> tuple[Any, ...]:
    return (
        action.get("issue_step"),
        action.get("effect_state_index"),
        tuple(action.get("expected_card15_fields", [])),
        tuple(action.get("target_current_a_tsc", [])),
        tuple(action.get("probe_virtual_action", [])),
        action.get("maximum_issued_delta_a"),
    )


def execute() -> dict[str, Any]:
    failures: list[str] = []
    for name, expected in EXPECTED.items():
        path = EVIDENCE / name
        if not path.is_file() or _sha(path) != expected:
            failures.append(f"EVIDENCE_IDENTITY:{name}")
    if failures:
        return {"schema_version": SCHEMA, "passed": False, "failures": failures,
                "plant_advances": 0, "models_fit_or_updated": 0}

    primary = _read(EVIDENCE / "result.json")
    audit = _read(EVIDENCE / "independent_raw_audit.json")
    baseline = _read(EVIDENCE / "baseline_transition_center.json")
    if audit.get("audit_passed") is not True or primary.get("verified_plant_advances") != 730:
        failures.append("SOURCE_RESULT_INTEGRITY")

    rows = []
    for phase in (50, 56):
        for axis in ("q_r", "q_z"):
            for sign in ("plus", "minus"):
                family = f"issue{phase}__{axis}__{sign}_then_return"
                branch = _read(EVIDENCE / f"{family}.json")
                if len(branch.get("actions", [])) != len(baseline.get("actions", [])):
                    failures.append(f"ACTION_COUNT:{family}")
                    differing: list[int] = []
                else:
                    differing = [index for index, (left, right) in enumerate(
                        zip(branch["actions"], baseline["actions"]))
                        if _action_key(left) != _action_key(right)]
                rows.append({"family_id": family, "phase_issue": phase,
                             "differing_issue_indices": differing,
                             "differing_issue_count": len(differing),
                             "identical_to_baseline": not differing})

    issue50 = [row for row in rows if row["phase_issue"] == 50]
    issue56 = [row for row in rows if row["phase_issue"] == 56]
    reproduced = all(row["differing_issue_count"] > 0 for row in issue50)
    defect = all(row["identical_to_baseline"] for row in issue56)
    if not reproduced:
        failures.append("ISSUE50_BRANCH_SEPARATION_NOT_REPRODUCED")
    if not defect:
        failures.append("ISSUE56_IDENTITY_DEFECT_NOT_REPRODUCED")
    return {
        "schema_version": SCHEMA,
        "passed": not failures and reproduced and defect,
        "failures": failures,
        "source_primary_sha256": EXPECTED["result.json"],
        "source_independent_sha256": EXPECTED["independent_raw_audit.json"],
        "plant_advances": 0,
        "models_fit_or_updated": 0,
        "rows": rows,
        "issue50_action_separation_reproduced": reproduced,
        "issue56_all_four_streams_identical_to_baseline": defect,
        "corrected_classification": "ACTION_STREAM_CONSTRUCTION_DESIGN_FAIL_NO_SCIENTIFIC_ISSUE56_RESPONSE_TEST",
        "claim_boundary": "Reporting/design forensic only; ID2Z32 raw is not rerun and no plant or model claim is added.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    value = execute()
    text = json.dumps(value, sort_keys=True, allow_nan=False)
    if args.output:
        target = args.output.resolve()
        if ROOT not in target.parents or target.exists():
            raise ValueError("output must be a new repository-local file")
        target.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if value["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
