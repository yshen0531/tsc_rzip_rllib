#!/usr/bin/env python3
"""Reconstruct and validate an authentic fixed-1000-ms TSC restart."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import shutil
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_nr1_qualification import (  # noqa: E402
    _card15_fields,
    _exact_coil_currents_a,
    _sha,
    _source,
    _wire,
    offline_preflight as source_offline_preflight,
)
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    OneMsNR1SafetyEnvelope,
    assert_exact_slew,
    build_frozen_one_ms_prefixes,
)
from tsc_rzip_rllib.control.rgeo_zgeo_contract import (  # noqa: E402
    ContractError,
    RGeoZGeoSignal,
)
from tsc_rzip_rllib.core.gfile import parse_gfile  # noqa: E402
from tsc_rzip_rllib.core.runner import TSCConfig, TSCStepRunner  # noqa: E402


TIME_RE = re.compile(r"special R\. Taylor output:.*?time\s*=\s*([+-]?[0-9.]+E[+-][0-9]+)", re.I)
RUNTIME_OUTPUTS = (
    "inputa", "geqdsk", "outputa", "coil_currents.csv",
    "wire_currents.csv", "sprsoua", "tsc.cgm",
)


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def load_contract(path: Path) -> dict[str, Any]:
    row = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "contract_version", "campaign_id", "intended_use", "route_prefix",
        "source_config", "source_sprsina_sha256", "source_1100_sprsina_sha256",
        "initial_reconstruction_runs", "restart_validation_runs",
        "restart_validation_steps", "expected_initial_start_s",
        "expected_initial_end_s", "expected_restart_start_s",
        "expected_restart_end_s", "maximum_tsc_invocations", "description",
    }
    if set(row) != expected:
        raise ContractError("restart reconstruction contract fields changed")
    if row["contract_version"] != "rgeo-zgeo-1ms-1000-restart-reconstruction-v1":
        raise ContractError("restart reconstruction contract version changed")
    if row["intended_use"] != "interface_validation":
        raise ContractError("restart reconstruction data role changed")
    if (row["initial_reconstruction_runs"], row["restart_validation_runs"],
            row["restart_validation_steps"], row["maximum_tsc_invocations"]) != (2, 2, 1, 4):
        raise ContractError("restart reconstruction budget changed")
    if row["source_sprsina_sha256"] != row["source_1100_sprsina_sha256"]:
        raise ContractError("the contaminated source identity is not reproduced")
    return row


def _require_inside_repo(path: Path, *, label: str) -> Path:
    resolved = path.resolve()
    if resolved != ROOT and ROOT not in resolved.parents:
        raise ContractError(f"{label} escapes repository: {resolved}")
    return resolved


def _validate_source_files(source_config: Path, source_folder: Path) -> dict[str, Any]:
    payload = json.loads(source_config.read_text(encoding="utf-8"))
    identity = payload.get("source_identity")
    if not isinstance(identity, dict):
        raise ContractError("source config has no source_identity")
    expected_files = identity.get("files")
    required = {
        "inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv",
        "sprsina", "outputa",
    }
    if not isinstance(expected_files, dict) or set(expected_files) != required:
        raise ContractError("source identity file set changed")
    actual: dict[str, Any] = {}
    for name in sorted(required):
        item = source_folder / name
        if not item.is_file():
            raise ContractError(f"source identity file missing: {name}")
        observed = {"sha256": _sha(item), "bytes": item.stat().st_size}
        actual[name] = observed
        if observed != expected_files[name]:
            raise ContractError(f"source identity mismatch: {name}")
    return actual


def preflight(config_path: Path, source_revision: str) -> dict[str, Any]:
    """Run every input/runtime/source check without invoking TSC."""
    result: dict[str, Any] = {
        "source_revision": source_revision,
        "passed": False,
        "route": "ONE_MS_NR1000S0R1_INPUT_FAIL_NO_TSC",
        "tsc_invocation_attempts": 0,
        "tsc_invocations": 0,
        "failures": [],
    }
    try:
        if re.fullmatch(r"[0-9a-f]{40}", source_revision) is None:
            raise ContractError("source revision must be a full lowercase Git SHA-1")
        config_path = _require_inside_repo(config_path, label="config")
        contract = load_contract(config_path)
        source_config = _require_inside_repo(
            ROOT / contract["source_config"], label="source config"
        )
        cfg = TSCConfig.from_json(source_config)
        source_folder = cfg.simulation_root / cfg.start_folder
        source_files = _validate_source_files(source_config, source_folder)
        source_gate = source_offline_preflight(source_config, source_revision)
        if not source_gate["passed"]:
            raise ContractError(
                "frozen source/interface offline gate failed: "
                + ";".join(source_gate.get("failures", []))
            )
        source_1100 = cfg.simulation_root / "1100ms" / "sprsina"
        if _sha(source_folder / "sprsina") != contract["source_sprsina_sha256"]:
            raise ContractError("1000 source sprsina identity changed")
        if _sha(source_1100) != contract["source_1100_sprsina_sha256"]:
            raise ContractError("1100 source sprsina identity changed")
        original_times = output_times_s(
            (source_folder / "outputa").read_text(errors="ignore")
        )
        if abs(min(original_times)) > 5e-7 or abs(max(original_times) - 1.0) > 5e-7:
            raise ContractError("authentic 1000 output internal time changed")
        result.update({
            "passed": True,
            "route": "ONE_MS_NR1000S0R1_OFFLINE_PASS",
            "contract": contract,
            "source_config": str(source_config),
            "source_folder": str(source_folder),
            "source_files": source_files,
            "source_offline_route": source_gate["route"],
            "source_output_time_s": {
                "minimum": min(original_times), "maximum": max(original_times)
            },
            "runtime": {
                "executable": str(cfg.executable),
                "tsc_dir": str(cfg.tsc_dir),
                "workspace_root": str(cfg.resolved_tsc_workspace_root()),
            },
        })
    except Exception as exc:
        result["failures"].append(f"{type(exc).__name__}:{exc}")
    result["failures"] = list(dict.fromkeys(result["failures"]))
    return result


def output_times_s(text: str) -> tuple[float, ...]:
    values = tuple(float(value) for value in TIME_RE.findall(text))
    if not values or not all(math.isfinite(value) for value in values):
        raise ContractError("TSC output has no finite internal-time trace")
    return values


def semantic(folder: Path, cfg: TSCConfig, *, time_ms: int = 1000) -> dict[str, Any]:
    required = ("inputa", "geqdsk", "outputa", "coil_currents.csv", "wire_currents.csv")
    missing = [name for name in required if not (folder / name).is_file()]
    if missing:
        raise ContractError(f"semantic state files missing: {missing}")
    gfile = parse_gfile(folder / "geqdsk")
    signal = RGeoZGeoSignal.from_tsc_state({
        "time_ms": time_ms, "Ip": float(gfile["ip"]), "gfile": gfile,
        "abnormal": False,
    })
    return {
        "time_ms": time_ms,
        "r_geo_m": signal.boundary.r_geo_m,
        "z_geo_m": signal.boundary.z_geo_m,
        "r_mid_m": signal.limiter.r_mid_m,
        "ip_a": signal.ip_a,
        "coil_a": [float(value) for value in _exact_coil_currents_a(folder / "coil_currents.csv", cfg)],
        "wire_a": _wire(folder / "wire_currents.csv", cfg),
        "card15_fields": list(_card15_fields(folder / "inputa")),
        "artifact_sha256": {name: _sha(folder / name) for name in required},
    }


def semantic_failures(left: dict[str, Any], right: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for key, label, tolerance in (
        ("r_geo_m", "R_GEO", 1e-12),
        ("z_geo_m", "Z_GEO", 1e-12),
        ("r_mid_m", "R_MID", 1e-12),
        ("ip_a", "IP", 1e-6),
    ):
        if abs(float(left[key]) - float(right[key])) > tolerance:
            failures.append(label)
    for key, label, tolerance, length in (
        ("coil_a", "COIL", 1e-9, 14),
        ("wire_a", "WIRE", 1e-9, 48),
    ):
        a, b = tuple(left[key]), tuple(right[key])
        if len(a) != length or len(b) != length or max(abs(x - y) for x, y in zip(a, b)) > tolerance:
            failures.append(label)
    return failures


def _note_tsc_invocation(counters: dict[str, Any], maximum: int) -> None:
    if int(counters["tsc_invocation_attempts"]) >= maximum:
        raise ContractError("maximum TSC invocation budget exhausted")
    counters["tsc_invocation_attempts"] += 1
    counters["tsc_invocations"] += 1


def _run_initial(cfg: TSCConfig, source_folder: Path, destination: Path, name: str,
                 counters: dict[str, Any], maximum: int) -> dict[str, Any]:
    runner = TSCStepRunner(cfg, worker_id=f"nr1000_reconstruct_{name}", keep_workspace=False)
    try:
        runtime = runner.runtime_tsc_dir
        for stale in ("inputa", "sprsina", "sprsoua", "geqdsk", "outputa",
                      "coil_currents.csv", "wire_currents.csv", "tsc.cgm"):
            item = runtime / stale
            if item.exists():
                item.unlink()
        shutil.copy2(source_folder / "inputa", runtime / "inputa")
        if (runtime / "sprsina").exists():
            raise ContractError("initial reconstruction must not load sprsina")
        _note_tsc_invocation(counters, maximum)
        returncode, stdout, stderr = runner._run_tsc()
        destination.mkdir(parents=True, exist_ok=False)
        for item_name in RUNTIME_OUTPUTS:
            item = runtime / item_name
            if item.exists():
                shutil.copy2(item, destination / item_name)
        (destination / "subprocess_stdout.txt").write_text(stdout, encoding="utf-8")
        (destination / "subprocess_stderr.txt").write_text(stderr, encoding="utf-8")
        if returncode != 0:
            raise RuntimeError(f"initial gotsc returncode={returncode}")
        for required in ("geqdsk", "outputa", "coil_currents.csv", "wire_currents.csv", "sprsoua"):
            if not (destination / required).is_file():
                raise ContractError(f"initial reconstruction missing {required}")
        return {"returncode": returncode, "destination": str(destination)}
    finally:
        runner.cleanup_runtime_workspace()


def _copy_canonical(source_folder: Path, reconstruction: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    shutil.copy2(source_folder / "inputa", destination / "inputa")
    shutil.copy2(reconstruction / "sprsoua", destination / "sprsina")
    for name in ("geqdsk", "outputa", "coil_currents.csv", "wire_currents.csv", "tsc.cgm"):
        item = reconstruction / name
        if item.exists():
            shutil.copy2(item, destination / name)


def _restart_once(cfg: TSCConfig, name: str, target: Any,
                  envelope: OneMsNR1SafetyEnvelope,
                  counters: dict[str, Any], maximum: int) -> dict[str, Any]:
    runner = TSCStepRunner(cfg, worker_id=f"nr1000_restart_{name}", keep_workspace=False)
    reasons: list[str] = []
    states: list[dict[str, Any]] = []
    try:
        state0 = runner.reset(episode_name=name)
        states.append(semantic(Path(state0["folder"]), cfg, time_ms=1000))
        reasons.extend(envelope.state_reasons(
            RGeoZGeoSignal.from_tsc_state(state0), state0["currents_a_tsc"],
            cfg.min_current_a_tsc, cfg.max_current_a_tsc,
        ))
        _note_tsc_invocation(counters, maximum)
        state1 = runner.step_current_a(target.current_a_tsc)
        states.append(semantic(Path(state1["folder"]), cfg, time_ms=1001))
        if int(state1.get("returncode", 0)) != 0:
            reasons.append(f"RETURNCODE:{state1.get('returncode')}")
        if bool(state1.get("abnormal", False)):
            reasons.append("ABNORMAL")
        if tuple(_card15_fields(Path(state1["folder"]) / "inputa")) != target.card15_fields:
            reasons.append("CARD15")
        try:
            assert_exact_slew(states[0]["coil_a"], states[1]["coil_a"], name=f"{name}.observed")
        except ContractError as exc:
            reasons.append(f"OBSERVED_SLEW:{exc}")
        reasons.extend(envelope.state_reasons(
            RGeoZGeoSignal.from_tsc_state(state1), state1["currents_a_tsc"],
            cfg.min_current_a_tsc, cfg.max_current_a_tsc,
        ))
        times = output_times_s((Path(state1["folder"]) / "outputa").read_text(errors="ignore"))
        if abs(min(times) - 1.0) > 5e-7 or abs(max(times) - 1.001) > 5e-7:
            reasons.append("INTERNAL_TIME")
    except Exception as exc:
        reasons.append(f"EXECUTION:{type(exc).__name__}:{exc}")
    finally:
        runner.cleanup_runtime_workspace()
    return {"name": name, "passed": not reasons and len(states) == 2,
            "reasons": list(dict.fromkeys(reasons)), "states": states}


def execute(config_path: Path, source_revision: str, output_dir: Path) -> dict[str, Any]:
    config_path = _require_inside_repo(config_path, label="config")
    output_dir = _require_inside_repo(output_dir, label="output")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {output_dir}")
    output_dir.mkdir(parents=True)
    result: dict[str, Any] = {
        "source_revision": source_revision, "passed": False,
        "route": "ONE_MS_NR1000S0R1_INPUT_FAIL_NO_TSC",
        "tsc_invocation_attempts": 0, "tsc_invocations": 0, "failures": [],
    }
    try:
        offline = preflight(config_path, source_revision)
        result["offline_preflight"] = offline
        if not offline["passed"]:
            raise ContractError("restart reconstruction offline preflight failed")
        contract = offline["contract"]
        source_config = Path(offline["source_config"])
        cfg = TSCConfig.from_json(source_config)
        source_folder = cfg.simulation_root / cfg.start_folder
        source_state = semantic(source_folder, cfg)

        recon_root = output_dir / "initial_reconstruction"
        recon_rows = []
        for index in range(2):
            destination = recon_root / f"r{index}"
            row = _run_initial(
                cfg, source_folder, destination, f"r{index}", result,
                int(contract["maximum_tsc_invocations"]),
            )
            times = output_times_s((destination / "outputa").read_text(errors="ignore"))
            if abs(min(times)) > 5e-7 or abs(max(times) - 1.0) > 5e-7:
                raise ContractError(f"initial reconstruction r{index} internal time mismatch")
            row["semantic"] = semantic(destination, cfg)
            row["sprsoua_sha256"] = _sha(destination / "sprsoua")
            row["source_failures"] = semantic_failures(source_state, row["semantic"])
            recon_rows.append(row)
            if row["source_failures"]:
                result["route"] = "ONE_MS_NR1000S0R1_SOURCE_SEMANTIC_MISMATCH"
                raise ContractError(f"initial reconstruction r{index} differs from source")
        if recon_rows[0]["sprsoua_sha256"] != recon_rows[1]["sprsoua_sha256"]:
            raise ContractError("reconstructed sprsoua replay mismatch")
        if recon_rows[0]["sprsoua_sha256"] == contract["source_sprsina_sha256"]:
            raise ContractError("reconstructed 1000 restart still equals contaminated 1100 restart")
        if semantic_failures(recon_rows[0]["semantic"], recon_rows[1]["semantic"]):
            raise ContractError("initial semantic replay mismatch")
        result["initial_reconstruction"] = recon_rows

        canonical_parent = output_dir / "canonical_source"
        canonical = canonical_parent / "1000ms"
        _copy_canonical(source_folder, recon_root / "r0", canonical)
        canonical_state = semantic(canonical, cfg)
        if semantic_failures(source_state, canonical_state):
            result["route"] = "ONE_MS_NR1000S0R1_SOURCE_SEMANTIC_MISMATCH"
            raise ContractError("canonical source differs from authentic 1000 state")

        restart_cfg = TSCConfig.from_json(source_config)
        restart_cfg.simulation_root = canonical_parent
        restart_cfg.start_folder = "1000ms"
        restart_cfg.run_root = output_dir / "restart_validation"
        canonical_source = _source(restart_cfg)
        frozen = build_frozen_one_ms_prefixes(
            source_current_a_tsc=canonical_source["currents_a_tsc"],
            source_command_a_tsc=canonical_source["active_command_decimal_a_tsc"],
            turns_tsc=restart_cfg.turns_tsc,
            min_current_a_tsc=restart_cfg.min_current_a_tsc,
            max_current_a_tsc=restart_cfg.max_current_a_tsc,
        )
        envelope = OneMsNR1SafetyEnvelope.from_signal(
            RGeoZGeoSignal.from_tsc_state(canonical_source)
        )
        restart_rows = []
        for name in ("restart_primary", "restart_replay"):
            row = _restart_once(
                restart_cfg, name, frozen.q0, envelope, result,
                int(contract["maximum_tsc_invocations"]),
            )
            restart_rows.append(row)
            if not row["passed"]:
                result["route"] = "ONE_MS_NR1000S0R1_RESTART_1MS_FAIL"
                raise ContractError(f"{name} failed")
        for index in (0, 1):
            if semantic_failures(restart_rows[0]["states"][index], restart_rows[1]["states"][index]):
                result["route"] = "ONE_MS_NR1000S0R1_RESTART_1MS_FAIL"
                raise ContractError(f"restart replay state{index} mismatch")
        result["restart_validation"] = restart_rows
        result["canonical_source"] = {
            "path": str(canonical),
            "sprsina_sha256": _sha(canonical / "sprsina"),
            "semantic": canonical_state,
        }
        result["passed"] = True
        result["route"] = "ONE_MS_NR1000S0R1_CANONICAL_1000_RESTART_QUALIFIED"
    except Exception as exc:
        result["failures"].append(f"{type(exc).__name__}:{exc}")
        if result["tsc_invocations"] and result["route"] == "ONE_MS_NR1000S0R1_INPUT_FAIL_NO_TSC":
            result["route"] = "ONE_MS_NR1000S0R1_INITIAL_RECONSTRUCTION_FAIL"
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
