#!/usr/bin/env python3
"""Validate byte-distinct fixed-1000 restart reconstructions by fresh replay."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_1000_restart_reconstruction import (  # noqa: E402
    _copy_canonical,
    _dump,
    _require_inside_repo,
    _restart_once,
    _sha,
    _source,
    _validate_file_identity,
    output_times_s,
    semantic,
    semantic_failures,
)
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    OneMsNR1SafetyEnvelope,
    build_frozen_one_ms_prefixes,
)
from tsc_rzip_rllib.control.rgeo_zgeo_contract import (  # noqa: E402
    ContractError,
    RGeoZGeoSignal,
)
from tsc_rzip_rllib.core.runner import TSCConfig  # noqa: E402


FIELDS = {
    "contract_version", "campaign_id", "intended_use", "route_prefix",
    "source_config", "source_config_sha256", "r2r2_result", "reconstructed_roots", "replays_per_root",
    "steps_per_replay", "maximum_tsc_invocations", "require_distinct_restart_hashes",
    "require_exact_checked_artifacts_across_all_replays", "description",
}


def load_contract(path: Path) -> dict[str, Any]:
    row = json.loads(path.read_text(encoding="utf-8"))
    if set(row) != FIELDS:
        raise ContractError("dual restart validation fields changed")
    if row["contract_version"] != "rgeo-zgeo-1ms-1000-restart-dual-validation-v1":
        raise ContractError("dual restart validation version changed")
    if row["intended_use"] != "interface_validation":
        raise ContractError("dual restart data role changed")
    if row["route_prefix"] != "ONE_MS_NR1000S0R3":
        raise ContractError("dual restart route changed")
    if (row["replays_per_root"], row["steps_per_replay"],
            row["maximum_tsc_invocations"]) != (2, 1, 4):
        raise ContractError("dual restart budget changed")
    if set(row["reconstructed_roots"]) != {"r0", "r1"}:
        raise ContractError("dual restart roots changed")
    if not row["require_distinct_restart_hashes"]:
        raise ContractError("distinct restart evidence requirement weakened")
    if not row["require_exact_checked_artifacts_across_all_replays"]:
        raise ContractError("checked-artifact replay requirement weakened")
    return row


def _route(contract: dict[str, Any], suffix: str) -> str:
    return f"{contract['route_prefix']}_{suffix}"


def preflight(config_path: Path, source_revision: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "source_revision": source_revision, "passed": False,
        "route": "ONE_MS_NR1000S0R3_INPUT_FAIL_NO_TSC",
        "tsc_invocations": 0, "tsc_invocation_attempts": 0, "failures": [],
    }
    try:
        config_path = _require_inside_repo(config_path, label="config")
        contract = load_contract(config_path)
        if re.fullmatch(r"[0-9a-f]{40}", source_revision) is None:
            raise ContractError("source revision must be a full lowercase Git SHA-1")
        source_config = _require_inside_repo(ROOT / contract["source_config"], label="source config")
        if _sha(source_config) != contract["source_config_sha256"]:
            raise ContractError("source config identity changed")
        cfg = TSCConfig.from_json(source_config)
        source_folder = cfg.simulation_root / cfg.start_folder
        source_state = semantic(source_folder, cfg)

        prior = contract["r2r2_result"]
        prior_path = _require_inside_repo(ROOT / prior["path"], label="R2R2 result")
        if _sha(prior_path) != prior["sha256"]:
            raise ContractError("R2R2 result identity changed")
        prior_row = json.loads(prior_path.read_text(encoding="utf-8"))
        if (prior_row.get("route"), prior_row.get("passed"), prior_row.get("tsc_invocations")) != (
                prior["route"], False, prior["tsc_invocations"]):
            raise ContractError("R2R2 result semantics changed")
        if prior_row.get("failures") != ["ContractError:reconstructed sprsoua replay mismatch"]:
            raise ContractError("R2R2 failure classification changed")

        roots: dict[str, Any] = {}
        states: dict[str, Any] = {}
        for name in ("r0", "r1"):
            spec = contract["reconstructed_roots"][name]
            folder = _require_inside_repo(ROOT / spec["path"], label=f"{name} reconstruction")
            roots[name] = {
                "path": str(folder),
                "files": _validate_file_identity(folder, spec["files"], label=name),
            }
            times = output_times_s((folder / "outputa").read_text(errors="ignore"))
            if abs(min(times)) > 5e-7 or abs(max(times) - 1.0) > 5e-7:
                raise ContractError(f"{name} output clock changed")
            states[name] = semantic(folder, cfg, require_card15=False)
            if semantic_failures(source_state, states[name]):
                raise ContractError(f"{name} semantic source mismatch")
        if semantic_failures(states["r0"], states["r1"]):
            raise ContractError("reconstructed roots differ semantically")
        if roots["r0"]["files"]["sprsoua"]["sha256"] == roots["r1"]["files"]["sprsoua"]["sha256"]:
            raise ContractError("reconstructed restarts are not the frozen byte-distinct pair")
        result.update({
            "passed": True, "route": _route(contract, "OFFLINE_PASS"),
            "contract": contract, "source_config": str(source_config),
            "source_folder": str(source_folder), "reconstructed_roots": roots,
            "semantic_failures_between_roots": semantic_failures(states["r0"], states["r1"]),
        })
    except Exception as exc:
        result["failures"].append(f"{type(exc).__name__}:{exc}")
    result["failures"] = list(dict.fromkeys(result["failures"]))
    return result


def execute(config_path: Path, source_revision: str, output_dir: Path) -> dict[str, Any]:
    config_path = _require_inside_repo(config_path, label="config")
    output_dir = _require_inside_repo(output_dir, label="output")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {output_dir}")
    output_dir.mkdir(parents=True)
    result: dict[str, Any] = {
        "source_revision": source_revision, "passed": False,
        "route": "ONE_MS_NR1000S0R3_INPUT_FAIL_NO_TSC",
        "tsc_invocations": 0, "tsc_invocation_attempts": 0, "failures": [],
    }
    contract: dict[str, Any] | None = None
    try:
        offline = preflight(config_path, source_revision)
        result["offline_preflight"] = offline
        if not offline["passed"]:
            raise ContractError("dual restart offline preflight failed")
        contract = offline["contract"]
        source_config = Path(offline["source_config"])
        source_cfg = TSCConfig.from_json(source_config)
        source_folder = source_cfg.simulation_root / source_cfg.start_folder
        all_rows: list[dict[str, Any]] = []

        for root_name in ("r0", "r1"):
            root_source = Path(offline["reconstructed_roots"][root_name]["path"])
            canonical_parent = output_dir / "canonical_sources" / root_name
            canonical = canonical_parent / "1000ms"
            _copy_canonical(source_folder, root_source, canonical)
            # The scientific source state is the authenticated target folder;
            # only the missing restart payload comes from the reconstruction.
            for artifact in ("geqdsk", "outputa", "coil_currents.csv", "wire_currents.csv"):
                shutil.copy2(source_folder / artifact, canonical / artifact)
            cfg = TSCConfig.from_json(source_config)
            cfg.simulation_root = canonical_parent
            cfg.start_folder = "1000ms"
            cfg.run_root = output_dir / "restart_validation" / root_name
            start = _source(cfg)
            frozen = build_frozen_one_ms_prefixes(
                source_current_a_tsc=start["currents_a_tsc"],
                source_command_a_tsc=start["active_command_decimal_a_tsc"],
                turns_tsc=cfg.turns_tsc,
                min_current_a_tsc=cfg.min_current_a_tsc,
                max_current_a_tsc=cfg.max_current_a_tsc,
            )
            envelope = OneMsNR1SafetyEnvelope.from_signal(RGeoZGeoSignal.from_tsc_state(start))
            for replay in range(2):
                name = f"{root_name}_replay{replay}"
                row = _restart_once(cfg, name, frozen.q0, envelope, result, 4)
                row["root"] = root_name
                row["replay"] = replay
                all_rows.append(row)
                if not row["passed"]:
                    result["route"] = _route(contract, "RESTART_EXECUTION_FAIL")
                    raise ContractError(f"{name} failed")

        reference = all_rows[0]["states"]
        for row in all_rows[1:]:
            for state_index in (0, 1):
                failures = semantic_failures(reference[state_index], row["states"][state_index])
                if failures:
                    result["route"] = _route(contract, "CROSS_RESTART_SEMANTIC_FAIL")
                    raise ContractError(f"{row['name']} state{state_index} differs: {failures}")
                if reference[state_index]["artifact_sha256"] != row["states"][state_index]["artifact_sha256"]:
                    result["route"] = _route(contract, "CROSS_RESTART_ARTIFACT_FAIL")
                    raise ContractError(f"{row['name']} state{state_index} checked artifacts differ")
        result["restart_validation"] = all_rows
        result["passed"] = True
        result["route"] = _route(contract, "CANONICAL_1000_RESTART_SEMANTICS_QUALIFIED")
    except Exception as exc:
        result["failures"].append(f"{type(exc).__name__}:{exc}")
        if result["tsc_invocations"] and contract is not None and result["route"] == _route(contract, "INPUT_FAIL_NO_TSC"):
            result["route"] = _route(contract, "RESTART_EXECUTION_FAIL")
    result["failures"] = list(dict.fromkeys(result["failures"]))
    _dump(output_dir / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    if args.offline:
        output = _require_inside_repo(args.output.resolve(), label="offline output")
        if output.exists():
            raise FileExistsError(f"refusing to overwrite {output}")
        result = preflight(args.config.resolve(), args.source_revision)
        _dump(output, result)
    else:
        result = execute(args.config.resolve(), args.source_revision, args.output.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
