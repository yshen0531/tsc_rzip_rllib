#!/usr/bin/env python3
"""Separate-process deterministic recomputation for ID-2V0."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import rgeo_zgeo_1ms_id2v0_control_utility_support_audit as primary


ROOT = Path(__file__).resolve().parents[1]


class AuditError(RuntimeError):
    pass


def canonical(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical(payload)).hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise AuditError(f"refusing overwrite: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(payload))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=primary.CONFIG)
    parser.add_argument("--primary-result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result_path = args.primary_result.resolve()
    output_path = args.output.resolve()
    for path in (result_path, output_path.parent):
        try:
            path.relative_to(ROOT)
        except ValueError as exc:
            raise AuditError("paths must remain inside repository") from exc
    saved = json.loads(result_path.read_text(encoding="utf-8"))
    reproduced = primary.execute(args.config.resolve(), str(saved.get("source_revision")))
    failures = []
    if canonical(saved) != canonical(reproduced):
        failures.append("PRIMARY_RESULT_MISMATCH")
    audit = {
        "schema_version": "rgeo-zgeo-1ms-id2v0-control-utility-support-independent-v1",
        "audit_passed": not failures,
        "failures": failures,
        "primary_result_sha256": hashlib.sha256(result_path.read_bytes()).hexdigest(),
        "recomputed_result_sha256": digest(reproduced),
        "route": saved.get("route"),
        "decision": saved.get("decision"),
        "new_tsc_calls": 0,
        "reset_calls": 0,
        "plant_advances": 0,
        "models_fit_or_trained": 0,
    }
    write_json(output_path, audit)
    print(json.dumps(audit, sort_keys=True))
    return 0 if audit["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

