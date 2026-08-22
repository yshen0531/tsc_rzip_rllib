#!/usr/bin/env python3
"""Exact-lattice correction for fixed-1000 joint allocator Authority G2R1."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_1000_joint_allocator_authority_g2 as g2  # noqa: E402
from scripts.rgeo_zgeo_1ms_nr1_qualification import _source  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import OneMsNR1SafetyEnvelope  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_contract import RGeoZGeoSignal  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-1000-joint-allocator-authority-g2r1-v1"
CONFIG_SHA256 = "7da7df4c54dcd44fe9f23003974d09a13859db550b41ab6f6c99e7658be8df66"
DEFAULT_CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_joint_allocator_authority_g2r1.json"
b0 = g2.b0


def load(config_path: Path) -> tuple[dict[str, Any], Any, dict[str, Any]]:
    config_path = b0.inside_root(config_path, "G2R1 config")
    if b0.sha256(config_path) != CONFIG_SHA256:
        raise g2.InputIntegrityError("G2R1 config SHA-256 mismatch")
    amendment = json.loads(config_path.read_text(encoding="utf-8"))
    exact = {
        "schema_version": SCHEMA,
        "campaign_id": "rgeo_zgeo_1ms_1000_joint_allocator_authority_g2r1_v1",
        "parent_config_path": "configs/rgeo_zgeo_1ms_1000_joint_allocator_authority_g2.json",
        "parent_config_sha256": g2.CONFIG_SHA256,
        "design_path": "docs/codex/reports/RGEO_ZGEO_1MS_1000_JOINT_ALLOCATOR_AUTHORITY_G2R1_DESIGN.md",
        "design_sha256": "fcd40856a9f0dbeec979fa87f0f8117141d91362744a69f6b1ded83fc4de6fd7",
        "failed_parent_offline_path": "artifacts/server_validation/rgeo_zgeo_1ms_1000_g2_95b7fd7d_v1.offline.json",
        "failed_parent_offline_sha256": "0de041d22c1e0f9f3585b0954a0fbeaa1df973dfc79bdbdedaacc8789d7549de",
        "failed_parent_route": "ONE_MS_NR1000G2_OFFLINE_FAIL_NO_TSC",
        "takeover_time_ms": 1000,
        "control_period_ms": 1,
        "horizon_steps": 64,
        "rollouts": 5,
        "maximum_reset_calls": 5,
        "maximum_advance_attempts": 320,
        "maximum_gotsc_calls": 320,
        "maximum_verified_plant_advances": 320,
        "retry_after_any_advance_attempt": "forbidden",
        "lattice_correction": {
            "vertical_single_turn_increment_a": 0.06,
            "maximum_exact_issued_slew_a": 0.21,
            "maximum_hard_observed_slew_a": 0.3,
            "minimum_nominal_readback_reserve_a": 0.09,
            "enumerated_maximum_exact_adjacent_slew_a": "0.20833333333333333333333334",
            "all_other_parent_semantics_unchanged": True,
        },
        "routes": {
            "offline_pass": "ONE_MS_NR1000G2R1_OFFLINE_PASS_RUN_ONLY",
            "offline_fail": "ONE_MS_NR1000G2R1_OFFLINE_FAIL_NO_TSC",
            "execution_fail": "ONE_MS_NR1000G2R1_EXECUTION_OR_HARD_SAFETY_FAIL_STOP",
            "matched_q0_fail": "ONE_MS_NR1000G2R1_MATCHED_Q0_INCOMPLETE_STOP_INCONCLUSIVE",
            "replay_fail": "ONE_MS_NR1000G2R1_CRITICAL_REPLAY_FAIL_STOP",
            "scientific_fail": "ONE_MS_NR1000G2R1_JOINT_ALLOCATOR_AUTHORITY_INSUFFICIENT_ACTION_BASIS_REDESIGN",
            "pass": "ONE_MS_NR1000G2R1_JOINT_ALLOCATOR_AUTHORITY_PASS_MODEL_AND_RECOURSE_DESIGN_ONLY",
            "independent_pass": "ONE_MS_NR1000G2R1_INDEPENDENT_PASS",
            "independent_fail": "ONE_MS_NR1000G2R1_INDEPENDENT_FAIL",
        },
    }
    for key, expected in exact.items():
        if amendment.get(key) != expected:
            raise g2.InputIntegrityError(f"G2R1 frozen field mismatch: {key}")
    parent_path = b0.inside_root(ROOT / amendment["parent_config_path"], "G2R1 parent config")
    if b0.sha256(parent_path) != amendment["parent_config_sha256"]:
        raise g2.InputIntegrityError("G2R1 parent config hash mismatch")
    design = b0.inside_root(ROOT / amendment["design_path"], "G2R1 design")
    if b0.sha256(design) != amendment["design_sha256"]:
        raise g2.InputIntegrityError("G2R1 design hash mismatch")
    failed = b0.inside_root(ROOT / amendment["failed_parent_offline_path"], "G2R1 failed parent evidence")
    if not failed.is_file() or b0.sha256(failed) != amendment["failed_parent_offline_sha256"]:
        raise g2.InputIntegrityError("G2R1 failed-parent evidence hash mismatch")
    failed_payload = json.loads(failed.read_text(encoding="utf-8"))
    if failed_payload.get("passed") is not False or failed_payload.get("route") != amendment["failed_parent_route"]:
        raise g2.InputIntegrityError("G2R1 failed-parent route changed")
    stage0, cfg, evidence = g2.load(parent_path)
    stage = json.loads(json.dumps(stage0))
    stage["schema_version"] = SCHEMA
    stage["campaign_id"] = amendment["campaign_id"]
    stage["design_path"] = amendment["design_path"]
    stage["design_sha256"] = amendment["design_sha256"]
    stage["lattice"]["vertical_single_turn_increment_a"] = amendment["lattice_correction"][
        "vertical_single_turn_increment_a"
    ]
    stage["lattice"]["maximum_exact_issued_slew_a"] = amendment["lattice_correction"][
        "maximum_exact_issued_slew_a"
    ]
    stage["lattice"]["minimum_nominal_readback_reserve_a"] = amendment["lattice_correction"][
        "minimum_nominal_readback_reserve_a"
    ]
    stage["routes"] = amendment["routes"]
    return stage, cfg, evidence


targets = g2.targets
rollout_specs = g2.rollout_specs
radial_levels_for_switch = g2.radial_levels_for_switch
vertical_levels = g2.vertical_levels
static_action_stream = g2.static_action_stream
_next_radial_level = g2._next_radial_level
_run_one = g2._run_one
compare_rows = g2.compare_rows
scientific_metrics = g2.scientific_metrics


def offline(config_path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    stage = None
    geometry = streams = None
    try:
        stage, cfg, _ = load(config_path)
        source = _source(cfg)
        envelope = OneMsNR1SafetyEnvelope.from_signal(RGeoZGeoSignal.from_tsc_state(source))
        failures.extend(envelope.state_reasons(
            RGeoZGeoSignal.from_tsc_state(source), source["currents_a_tsc"],
            cfg.min_current_a_tsc, cfg.max_current_a_tsc,
        ))
        target_map = targets(stage, cfg, source)
        geometry = target_map["action_geometry"]
        expected_maximum = float(json.loads(config_path.read_text(encoding="utf-8"))[
            "lattice_correction"
        ]["enumerated_maximum_exact_adjacent_slew_a"])
        if abs(geometry["maximum_exact_adjacent_slew_a"] - expected_maximum) > 1e-15:
            raise g2.ContractError("G2R1 enumerated maximum changed")
        streams = []
        for switch_issue in range(stage["radial_policy"]["earliest_switch_issue"],
                                  stage["radial_policy"]["latest_switch_issue"] + 1):
            streams.append({"branch": f"radial_s{switch_issue}", "actions": static_action_stream(
                stage, cfg, source, target_map, switch_issue, (0, 0), f"radial_s{switch_issue}")})
            for signs in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                streams.append({
                    "branch": f"joint_s{switch_issue}_{signs[0]}_{signs[1]}",
                    "actions": static_action_stream(
                        stage, cfg, source, target_map, switch_issue, signs,
                        f"joint_s{switch_issue}_{signs[0]}_{signs[1]}",
                    ),
                })
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    failures = list(dict.fromkeys(failures))
    routes = (stage or {}).get("routes", {})
    return {
        "schema_version": SCHEMA,
        "kind": "offline_preflight",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_revision": source_revision,
        "passed": not failures,
        "route": routes.get("offline_pass") if not failures else routes.get(
            "offline_fail", "ONE_MS_NR1000G2R1_OFFLINE_FAIL_NO_TSC"),
        "failures": failures,
        "authorized_reset_calls": 5,
        "authorized_plant_advances": 320,
        "action_geometry": geometry,
        "enumerated_branch_streams": streams,
        "parent_g2_plant_advances": 0,
    }


def run(config_path: Path, source_revision: str, output_dir: Path) -> dict[str, Any]:
    preflight = offline(config_path, source_revision)
    if not preflight["passed"]:
        raise RuntimeError("G2R1 offline gate failed; TSC forbidden")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {output_dir}")
    output_dir.mkdir(parents=True)
    b0.write_new(output_dir / "offline_preflight.json", preflight)
    stage, cfg, evidence = load(config_path)
    cfg.run_root = output_dir / "rollouts"
    source = _source(cfg)
    target_map = targets(stage, cfg, source)
    envelope = OneMsNR1SafetyEnvelope.from_signal(RGeoZGeoSignal.from_tsc_state(source))
    rows: dict[str, dict[str, Any]] = {}
    for spec in rollout_specs(stage):
        row = _run_one(
            cfg, stage, spec, target_map, envelope, evidence["b0_primary"]["states"][0]
        )
        rows[spec["rollout_id"]] = row
        b0.write_new(output_dir / f"{spec['rollout_id']}.json", row)
        if not row["passed"]:
            break
    matched = rows.get("matched_q0", {}).get("passed") is True
    execution = len(rows) == stage["rollouts"] and all(row["passed"] for row in rows.values())
    replay = compare_rows(rows["path_pos_neg"], rows["path_pos_neg_replay"]) if execution else None
    replay_pass = replay is not None and replay["passed"]
    metrics = scientific_metrics(list(rows.values()), stage) if execution else None
    science = metrics is not None and metrics["passed"]
    passed = execution and matched and replay_pass and science
    route = stage["routes"]["pass"] if passed else (
        stage["routes"]["matched_q0_fail"] if not matched
        else stage["routes"]["execution_fail"] if not execution
        else stage["routes"]["replay_fail"] if not replay_pass
        else stage["routes"]["scientific_fail"]
    )
    result = {
        "schema_version": SCHEMA,
        "kind": "authentic_fixed_1000_joint_allocator_authority_lattice_corrected",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_revision": source_revision,
        "passed": passed,
        "route": route,
        "rollout_count": len(rows),
        "reset_calls": sum(row["reset_calls"] for row in rows.values()),
        "advance_attempts": sum(row["advance_attempts"] for row in rows.values()),
        "gotsc_calls": sum(row["gotsc_calls"] for row in rows.values()),
        "verified_plant_advances": sum(row["verified_plant_advances"] for row in rows.values()),
        "matched_q0_complete": matched,
        "action_geometry": target_map["action_geometry"],
        "critical_replay": replay,
        "scientific_metrics": metrics,
        "parent_g2_plant_advances": 0,
        "claim_boundary": (
            "fixed-1000 finite joint-allocation Authority development only; "
            "no model, hold, recovery, Recourse, controller, or R_mid crossing"
        ),
    }
    b0.write_new(output_dir / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("offline", "run"))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = offline(args.config.resolve(), args.source_revision) if args.mode == "offline" else run(
        args.config.resolve(), args.source_revision, args.output.resolve()
    )
    if args.mode == "offline":
        b0.write_new(args.output.resolve(), result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
