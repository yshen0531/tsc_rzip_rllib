#!/usr/bin/env python3
"""Zero-TSC semantic audit of completed fixed-1000 dual restart replays."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_1000_restart_reconstruction import (  # noqa: E402
    _dump, _require_inside_repo, _sha, semantic, semantic_failures,
)
from tsc_rzip_rllib.control.rgeo_zgeo_contract import ContractError  # noqa: E402
from tsc_rzip_rllib.core.runner import TSCConfig  # noqa: E402


CONFIG = ROOT / "configs" / "rgeo_zgeo_1ms_1000_restart_semantic_audit_r2.json"
SOURCE_CONFIG = ROOT / "configs" / "rgeo_zgeo_1ms_1000_nr1_source_interface.json"
FIELDS = {
    "contract_version", "campaign_id", "intended_use", "route_prefix",
    "r3r1_result", "raw_root", "expected_rollouts", "states_per_rollout",
    "stable_artifacts", "outputa_ignored_line_classes",
    "maximum_tsc_invocations", "description",
}
VERSION_RE = re.compile(
    r"^(\s*TSC Version .*?:\s*\d{2}\s+\w{3}\s+\d{2})\s+\d{6}\.\d+\s+\d{8}\s*$"
)
CPU_RE = re.compile(r"^CPU time \(min\).*$")


def load_contract(path: Path) -> dict[str, Any]:
    row = json.loads(path.read_text(encoding="utf-8"))
    if set(row) != FIELDS:
        raise ContractError("semantic-audit fields changed")
    if row["contract_version"] != "rgeo-zgeo-1ms-1000-restart-semantic-audit-r2-v1":
        raise ContractError("semantic-audit version changed")
    if row["intended_use"] != "interface_validation":
        raise ContractError("semantic-audit data role changed")
    if row["route_prefix"] != "ONE_MS_NR1000S0R3R2":
        raise ContractError("semantic-audit route changed")
    if row["expected_rollouts"] != ["r0_replay0", "r0_replay1", "r1_replay0", "r1_replay1"]:
        raise ContractError("semantic-audit rollout set changed")
    if row["states_per_rollout"] != 2 or row["maximum_tsc_invocations"] != 0:
        raise ContractError("semantic-audit budget changed")
    if row["stable_artifacts"] != ["inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv"]:
        raise ContractError("stable artifact set changed")
    if row["outputa_ignored_line_classes"] != ["version_wall_clock", "cpu_timing"]:
        raise ContractError("outputa normalization changed")
    return row


def normalize_outputa(text: str) -> tuple[str, dict[str, int]]:
    counts = {"version_wall_clock": 0, "cpu_timing": 0}
    rows: list[str] = []
    for line in text.splitlines():
        match = VERSION_RE.match(line)
        if match:
            rows.append(match.group(1) + " <WALL_CLOCK>")
            counts["version_wall_clock"] += 1
        elif CPU_RE.match(line):
            rows.append("CPU time (min) <TIMING>")
            counts["cpu_timing"] += 1
        else:
            rows.append(line)
    if counts != {"version_wall_clock": 1, "cpu_timing": 1}:
        raise ContractError(f"unexpected outputa timing-line counts: {counts}")
    return "\n".join(rows) + "\n", counts


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def execute(config_path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "source_revision": source_revision, "passed": False,
        "route": "ONE_MS_NR1000S0R3R2_INPUT_FAIL_NO_TSC",
        "tsc_invocations": 0, "plant_advances": 0, "failures": [],
    }
    try:
        config_path = _require_inside_repo(config_path, label="config")
        output = _require_inside_repo(output, label="output")
        if output.exists():
            raise FileExistsError(f"refusing to overwrite {output}")
        if re.fullmatch(r"[0-9a-f]{40}", source_revision) is None:
            raise ContractError("source revision must be a full lowercase Git SHA-1")
        contract = load_contract(config_path)
        prior = contract["r3r1_result"]
        prior_path = _require_inside_repo(ROOT / prior["path"], label="R3R1 result")
        if _sha(prior_path) != prior["sha256"]:
            raise ContractError("R3R1 result identity changed")
        prior_row = json.loads(prior_path.read_text(encoding="utf-8"))
        if (prior_row.get("route"), prior_row.get("passed"), prior_row.get("tsc_invocations")) != (
                prior["route"], False, prior["tsc_invocations"]):
            raise ContractError("R3R1 result semantics changed")
        rows = prior_row.get("restart_validation", [])
        if [row.get("name") for row in rows] != contract["expected_rollouts"]:
            raise ContractError("R3R1 rollout inventory changed")
        if any(not row.get("passed") for row in rows):
            raise ContractError("R3R1 contains an execution-failed rollout")
        if any(row.get("maximum_issued_delta_a") != 0.0 for row in rows):
            raise ContractError("R3R1 issued command was not exact hold")

        raw_root = _require_inside_repo(ROOT / contract["raw_root"], label="raw root")
        cfg = TSCConfig.from_json(SOURCE_CONFIG)
        reparsed: list[dict[str, Any]] = []
        for row in rows:
            root = row["root"]
            name = row["name"]
            rollout = _require_inside_repo(raw_root / root / name, label=name)
            states = [semantic(rollout / f"{1000 + index}ms", cfg, time_ms=1000 + index)
                      for index in range(2)]
            outputa = []
            for index in range(2):
                text = (rollout / f"{1000 + index}ms" / "outputa").read_text(errors="strict")
                normalized, counts = normalize_outputa(text)
                outputa.append({"normalized_sha256": _digest(normalized), "ignored_line_counts": counts})
            reparsed.append({"name": name, "root": root, "states": states, "outputa": outputa})

        reference = reparsed[0]
        comparisons = []
        for row in reparsed[1:]:
            for state_index in range(2):
                failures = semantic_failures(reference["states"][state_index], row["states"][state_index])
                stable_failures = [name for name in contract["stable_artifacts"]
                                   if reference["states"][state_index]["artifact_sha256"][name]
                                   != row["states"][state_index]["artifact_sha256"][name]]
                output_equal = (reference["outputa"][state_index]["normalized_sha256"]
                                == row["outputa"][state_index]["normalized_sha256"])
                comparisons.append({
                    "name": row["name"], "state_index": state_index,
                    "semantic_failures": failures,
                    "stable_artifact_failures": stable_failures,
                    "normalized_outputa_equal": output_equal,
                })
                if failures or stable_failures or not output_equal:
                    raise ContractError(f"semantic audit mismatch: {row['name']} state{state_index}")

        result.update({
            "passed": True,
            "route": "ONE_MS_NR1000S0R3R2_CANONICAL_1000_RESTART_SEMANTICS_QUALIFIED",
            "r3r1_result_sha256": prior["sha256"],
            "rollouts_reparsed": len(reparsed), "states_reparsed": 2 * len(reparsed),
            "comparisons": comparisons, "normalized_outputa_reference": reference["outputa"],
            "authorization": "FRESH_1000MS_NR1_INTERFACE_DESIGN_ONLY",
        })
    except Exception as exc:
        result["failures"].append(f"{type(exc).__name__}:{exc}")
    result["failures"] = list(dict.fromkeys(result["failures"]))
    _dump(output, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = execute(args.config.resolve(), args.source_revision, args.output.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
