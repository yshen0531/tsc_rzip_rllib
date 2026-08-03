#!/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python
"""Audit and apply the one authorized S24 step-10 representation hotfix."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24_sequential_transition_identification as s24,
)


HOTFIX_REVISION = "s24_fixed_basis_dict_to_ordered_columns_hotfix_v1"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _validate_config(cfg: Mapping[str, Any], config_path: Path) -> None:
    expected = {
        "schema_version": 1,
        "stage": s24.STAGE,
        "hotfix_revision": HOTFIX_REVISION,
        "campaign_identity": s24.CAMPAIGN_IDENTITY,
        "controller_revision": s24.CONTROLLER_REVISION,
        "run_basename": "stage4_2r3c3t13s24_sequential_transition_identification_20260803_111226_0c71836",
        "original_failed_state_sha256": "ff35ed373166f9e363e045b34e2bf6174b42490ccd0670b6488421b7e5f6ee11",
        "original_training_sequence_gate_sha256": "539abee776b77ca8011864200a03bbf4a536c930ecbb5326b9e0075646ba6451",
        "original_package_digest": "90e775a27ae7856e3328c0beb22c4aab6a2f8a92b8000c8d3c7b02b9c53f7320",
        "original_campaign_implementation_sha256": "39ffcb4a37d99d423c068e2fc6d827d31c8f56bb12229cff161c616769e44bc2",
        "failed_sequence_raw_count": 576,
        "failed_sequence_raw_bytes": 13706096,
        "failed_sequence_raw_inventory_digest": "332a227f1fb2ccfb01b773e156beecf2a5b4cb70e86b4c3dc5149a092ef1071c",
        "successful_training_baseline_raw_count": 24,
        "exact_failure_reason": "TypeError(\"float() argument must be a string or a real number, not 'dict'\")",
        "failure_trajectory_length": 11,
        "failure_controller_trace_length": 10,
        "archive_directory_name": "runtime_hotfix_attempt1_failed_sequence_raw",
        "resume_phase_status": "training_baseline_complete",
    }
    for key, value in expected.items():
        if cfg.get(key) != value:
            raise ValueError(f"S24 runtime hotfix {key} changed")
    new_hash = str(cfg.get("hotfixed_campaign_implementation_sha256", ""))
    if len(new_hash) != 64 or new_hash == str(cfg["original_campaign_implementation_sha256"]):
        raise ValueError("S24 runtime hotfix implementation hash is invalid")
    for key in (
        "failure_before_first_sequential_action",
        "preserve_failed_raw_on_server",
        "reuse_successful_baselines_only",
    ):
        if not bool(cfg.get(key)):
            raise ValueError(f"S24 runtime hotfix safety flag {key} changed")
    for key in (
        "controller_semantics_changed",
        "experiment_identity_changed",
        "spec_matrix_changed",
        "formal_timing_changed",
        "scientific_task_changed",
        "reuse_failed_sequence_raw",
        "bc_dagger_or_rl_allowed",
    ):
        if bool(cfg.get(key)):
            raise ValueError(f"S24 runtime hotfix forbidden change {key}")
    expected_path = (
        _project_root()
        / "configs/stage4_2r3c3t13s24_semantics_preserving_runtime_hotfix_v1.json"
    ).resolve()
    if config_path.resolve() != expected_path:
        raise ValueError("S24 runtime hotfix config path changed")


def _inventory(paths: Sequence[Path]) -> dict[str, Any]:
    digest = hashlib.sha256()
    rows = []
    for path in sorted(paths, key=lambda value: value.name):
        size = path.stat().st_size
        sha = _sha256(path)
        digest.update(f"{path.name}\0{size}\0{sha}\n".encode())
        rows.append({"path": path.name, "bytes": size, "sha256": sha})
    return {
        "count": len(rows),
        "total_bytes": sum(row["bytes"] for row in rows),
        "digest": digest.hexdigest(),
        "files": rows,
    }


def _validate_failed_result(
    result: Mapping[str, Any], spec: Mapping[str, Any], cfg: Mapping[str, Any]
) -> None:
    trace = result.get("controller_trace") or []
    trajectory = result.get("trajectory") or []
    if (
        result.get("stage") != s24.STAGE
        or result.get("campaign_identity") != s24.CAMPAIGN_IDENTITY
        or result.get("controller_revision") != s24.CONTROLLER_REVISION
        or result.get("experiment_id") != spec["experiment_id"]
        or result.get("spec") != dict(spec)
        or not bool(result.get("completed"))
        or bool(result.get("success"))
        or result.get("failure_reason") != cfg["exact_failure_reason"]
        or len(trajectory) != int(cfg["failure_trajectory_length"])
        or len(trace) != int(cfg["failure_controller_trace_length"])
        or any(row.get("r3c3t13s24_event") != "none" for row in trace)
        or not all(
            bool(row.get("computed_online")) and bool(row.get("solver_success"))
            for row in trace
        )
        or any(bool(row.get("abnormal")) for row in trajectory)
        or "_basis_current" not in str(result.get("traceback") or "")
        or "not 'dict'" not in str(result.get("traceback") or "")
    ):
        raise ValueError(f"S24 failed raw contract changed: {spec['experiment_id']}")


def audit_and_apply(config_path: Path, run_dir: Path, *, apply: bool) -> dict[str, Any]:
    config_path = config_path.expanduser().resolve()
    run_dir = run_dir.expanduser().resolve()
    cfg = _read_json(config_path)
    _validate_config(cfg, config_path)
    if run_dir.name != cfg["run_basename"]:
        raise ValueError("S24 runtime hotfix run identity changed")
    paths = s24._paths(run_dir)
    state_path = paths.state
    gate_path = paths.analysis / "training_sequence_gate.json"
    if _sha256(state_path) != cfg["original_failed_state_sha256"]:
        raise ValueError("S24 original failed state hash changed")
    if _sha256(gate_path) != cfg["original_training_sequence_gate_sha256"]:
        raise ValueError("S24 original training-sequence gate hash changed")
    state = _read_json(state_path)
    if (
        state.get("phase_status") != "training_sequence_failed"
        or not bool(state.get("finished"))
        or state.get("package_digest") != cfg["original_package_digest"]
        or (state.get("verdict") or {}).get("route")
        != "SEQUENTIAL_IDENTIFICATION_RUNTIME_FAIL"
    ):
        raise ValueError("S24 failed state semantics changed")
    manifest = _read_json(paths.manifest)
    initial_package = manifest["package_fingerprint"]
    module_relative = (
        "tsc_rzip_rllib/diagnostics/"
        "stage4_2r3c3t13s24_sequential_transition_identification.py"
    )
    if (
        initial_package["digest"] != cfg["original_package_digest"]
        or initial_package["hashes"][module_relative]
        != cfg["original_campaign_implementation_sha256"]
    ):
        raise ValueError("S24 initial package provenance changed")
    current_module = _project_root() / module_relative
    if _sha256(current_module) != cfg["hotfixed_campaign_implementation_sha256"]:
        raise ValueError("S24 deployed hotfix implementation hash changed")
    current_package = s24.s21._package_fingerprint()
    if current_package["hashes"][module_relative] != cfg["hotfixed_campaign_implementation_sha256"]:
        raise ValueError("S24 deployed package does not contain the audited hotfix")
    all_specs = _read_json(paths.specs / "all_specs.json")
    if (
        s24._digest(all_specs) != state["spec_digest"]
        or s24._digest(all_specs) != manifest["spec_digest"]
    ):
        raise ValueError("S24 frozen spec matrix changed before hotfix")
    baseline_specs = [row for row in all_specs if row["partition"] == "training" and row["s24_role"] == "baseline"]
    failed_specs = [row for row in all_specs if row["partition"] == "training" and row["s24_role"] != "baseline"]
    if len(baseline_specs) != 24 or len(failed_specs) != 576:
        raise ValueError("S24 hotfix rollout partition changed")
    for spec in baseline_specs:
        if not s24._result_complete(paths.raw / f"{spec['experiment_id']}.json.gz", spec):
            raise ValueError("S24 successful training baseline cannot be reused")
    failed_paths = []
    for spec in failed_specs:
        path = paths.raw / f"{spec['experiment_id']}.json.gz"
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            result = json.load(
                stream,
                parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
            )
        _validate_failed_result(result, spec, cfg)
        failed_paths.append(path)
    inventory = _inventory(failed_paths)
    if (
        inventory["count"] != cfg["failed_sequence_raw_count"]
        or inventory["total_bytes"] != cfg["failed_sequence_raw_bytes"]
        or inventory["digest"] != cfg["failed_sequence_raw_inventory_digest"]
    ):
        raise ValueError("S24 failed raw inventory changed")
    archive = paths.stage_dir / cfg["archive_directory_name"]
    original_state_copy = paths.analysis / "runtime_hotfix_attempt1_original_failed_state.json"
    audit_path = paths.analysis / "runtime_hotfix_attempt1_forensic_and_resume.json"
    if archive.exists() or original_state_copy.exists() or audit_path.exists():
        raise ValueError("S24 runtime hotfix has already been started")
    report = {
        "schema_version": 1,
        "stage": s24.STAGE,
        "phase": "semantics_preserving_runtime_hotfix_audit",
        "hotfix_revision": HOTFIX_REVISION,
        "run_dir": str(run_dir),
        "original_failed_state_sha256": cfg["original_failed_state_sha256"],
        "original_training_sequence_gate_sha256": cfg["original_training_sequence_gate_sha256"],
        "initial_package_fingerprint": initial_package,
        "hotfixed_package_fingerprint": current_package,
        "successful_training_baseline_count": len(baseline_specs),
        "failed_sequence_inventory": inventory,
        "failure_before_first_sequential_action_count": len(failed_specs),
        "runtime_or_environment_error_count": 576,
        "statistics_or_reporting_error_count": 0,
        "design_failure_count": 0,
        "real_sequential_control_result_count": 0,
        "controller_semantics_changed": False,
        "experiment_identity_changed": False,
        "spec_matrix_changed": False,
        "formal_timing_changed": False,
        "scientific_task_changed": False,
        "failed_raw_reused": False,
        "successful_baselines_reused": True,
        "mutation_performed": bool(apply),
        "passed": True,
    }
    if not apply:
        return report
    _write_json(original_state_copy, state)
    archive.mkdir(parents=False, exist_ok=False)
    for path in failed_paths:
        path.replace(archive / path.name)
    archived = _inventory(list(archive.glob("*.json.gz")))
    if archived != inventory:
        raise ValueError("S24 archived failed raw inventory changed")
    remaining = list(paths.raw.glob("*.json.gz"))
    if len(remaining) != 24:
        raise ValueError("S24 hotfix did not preserve exactly 24 successful baselines")
    compact = {
        "hotfix_revision": HOTFIX_REVISION,
        "original_failed_state_sha256": cfg["original_failed_state_sha256"],
        "failed_sequence_raw_inventory_digest": inventory["digest"],
        "archived_failed_sequence_raw_count": inventory["count"],
        "hotfixed_package_digest": current_package["digest"],
        "controller_semantics_changed": False,
        "failed_raw_reused": False,
        "successful_baselines_reused": True,
    }
    manifest["semantics_preserving_runtime_hotfix"] = compact
    _write_json(paths.manifest, manifest)
    state.update(
        {
            "phase_status": cfg["resume_phase_status"],
            "finished": False,
            "primary_pass": False,
            "new_raw_count": 24,
            "package_digest": current_package["digest"],
            "stop_reason": "",
            "verdict": {},
            "semantics_preserving_runtime_hotfix": compact,
        }
    )
    _write_json(state_path, state)
    report["archived_failed_sequence_inventory"] = archived
    report["resumed_state_sha256"] = _sha256(state_path)
    report["updated_manifest_sha256"] = _sha256(paths.manifest)
    _write_json(audit_path, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    result = audit_and_apply(args.config, args.run_dir, apply=bool(args.apply))
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
