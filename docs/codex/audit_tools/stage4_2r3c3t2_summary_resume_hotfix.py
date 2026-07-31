#!/usr/bin/env python3
"""External, source-fingerprint-neutral Stage4.2R3c3T2 summary hotfix.

The authenticated v2h1 run completed all 160 real TSC trajectories before
the runtime summary passed a 50-step result to the frozen 35/37-step formal
evaluator.  This wrapper stays outside PACKAGE_MANIFEST.json, authenticates
the complete raw set, truncates only the argument to the inherited summary
helper, and then executes either the frozen campaign entry point in
``--resume`` mode or the frozen server postprocessor.
"""

from __future__ import annotations

import copy
import gzip
import hashlib
import json
import runpy
import sys
from pathlib import Path
from typing import Any, Mapping

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t2_post_contract_neutralized_held_transport_identification
    as t2,
)


EXPECTED_PACKAGE = (
    "r42r3c3t2_post_contract_held_transport_identification_v2h1"
)
EXPECTED_CONTROLLER = (
    "post_contract_neutralized_held_transport_probe_v42r3c3t2_v2"
)
ALLOWED_TARGETS = {
    "stage4_2r3c3t2_post_contract_neutralized_held_transport_identification.py",
    "stage4_2r3c3t2_server_postprocess.py",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _argument_value(arguments: list[str], name: str) -> str:
    try:
        return arguments[arguments.index(name) + 1]
    except (ValueError, IndexError) as exc:
        raise SystemExit(f"required target argument missing: {name}") from exc


def _authenticate_run(run_dir: Path, target_args: list[str]) -> dict[str, Any]:
    run = run_dir.expanduser().resolve()
    manifest_path = run / "stage4_2r3c3t2_manifest.json"
    state_path = run / "stage4_2r3c3t2_state.json"
    raw_dir = (
        run / "stage4_2r3c3t2_held_transport_identification" / "raw"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    state = json.loads(state_path.read_text(encoding="utf-8"))
    offline = state.get("offline_probe_audit")
    expected_offline = {
        "expected_probe_specs": 160,
        "probe_spec_count": 160,
        "extended_baseline_spec_count": 32,
        "signed_probe_spec_count": 128,
        "probe_schedule_exact_count": 160,
        "finite_causal_action_count": 160,
        "baseline_context_count": 32,
        "hidden_wire_invariant_action_count": 160,
        "payload_and_environment_horizon_exact_count": 160,
        "raw_count": 0,
        "plant_advance_count": 0,
        "real_tsc_executed": False,
        "passed": True,
    }
    offline_exact = bool(
        isinstance(offline, Mapping)
        and all(
            offline.get(key) == value
            for key, value in expected_offline.items()
        )
    )
    raw_paths = sorted(raw_dir.glob("*.json.gz"))
    experiment_ids = set()
    raw_rows = []
    for path in raw_paths:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            result = json.load(handle)
        experiment_ids.add(str(result.get("experiment_id")))
        raw_rows.append(
            {
                "path": path.name,
                "sha256": _sha256(path),
                "size_bytes": int(path.stat().st_size),
                "valid": bool(
                    result.get("stage") == t2.STAGE
                    and result.get("controller_revision")
                    == EXPECTED_CONTROLLER
                    and result.get("completed")
                    and result.get("success")
                    and not result.get("failure_reason")
                    and len(result.get("trajectory") or []) == 51
                    and len(result.get("controller_trace") or []) == 50
                ),
            }
        )
    resume_target = (
        Path(sys.argv[2]).name
        == "stage4_2r3c3t2_post_contract_neutralized_held_transport_"
        "identification.py"
    )
    if resume_target and "--resume" not in target_args:
        raise SystemExit("campaign hotfix target must use --resume")
    if (
        manifest.get("stage") != t2.STAGE
        or manifest.get("controller_revision") != EXPECTED_CONTROLLER
        or manifest.get("package_revision") != EXPECTED_PACKAGE
        or len(raw_paths) != 160
        or len(experiment_ids) != 160
        or not all(row["valid"] for row in raw_rows)
        or not offline_exact
        or bool(state.get("finished"))
    ):
        raise SystemExit("T2 summary-hotfix run authentication failed")
    digest_payload = [
        {
            "path": row["path"],
            "sha256": row["sha256"],
            "size_bytes": row["size_bytes"],
        }
        for row in raw_rows
    ]
    digest = hashlib.sha256(
        json.dumps(
            digest_payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
    return {
        "run_dir": str(run),
        "raw_count": len(raw_paths),
        "raw_inventory_digest": digest,
        "manifest_sha256": _sha256(manifest_path),
        "state_sha256_before": _sha256(state_path),
        "runtime_package_fingerprint_digest": manifest[
            "deployed_package_fingerprint"
        ]["digest"],
        "pending_real_tsc_tasks": 0,
        "raw_files_modified": False,
        "controller_semantics_changed": False,
        "formal_prefix_only": True,
        "cached_initial_offline_audit_reused": resume_target,
        "_cached_initial_offline_audit": dict(offline),
    }


def _formal_prefix_control_row(
    original: Any,
    source_ctx: Any,
    result: Mapping[str, Any],
    state_row: Mapping[str, Any],
) -> dict[str, Any]:
    horizon = int(result["spec"]["formal_horizon_steps"])
    truncated = copy.deepcopy(dict(result))
    truncated["trajectory"] = list(result["trajectory"])[: horizon + 1]
    truncated["controller_trace"] = list(result["controller_trace"])[
        :horizon
    ]
    truncated["spec"] = copy.deepcopy(dict(result["spec"]))
    truncated["spec"]["horizon_steps"] = horizon
    return original(source_ctx, truncated, state_row)


def main() -> None:
    if len(sys.argv) < 4 or sys.argv[1] != "--target-script":
        raise SystemExit(
            "usage: summary_hotfix.py --target-script SCRIPT [SCRIPT_ARGS]"
        )
    target = Path(sys.argv[2]).expanduser().resolve()
    if target.name not in ALLOWED_TARGETS or not target.is_file():
        raise SystemExit(f"unexpected hotfix target: {target}")
    target_args = sys.argv[3:]
    run_dir = Path(_argument_value(target_args, "--run-dir"))
    authentication = _authenticate_run(run_dir, target_args)
    cached_initial_offline_audit = authentication.pop(
        "_cached_initial_offline_audit"
    )
    wrapper = Path(__file__).resolve()
    authentication["wrapper_path"] = str(wrapper)
    authentication["wrapper_sha256"] = _sha256(wrapper)
    print(
        json.dumps(
            {"summary_hotfix_preflight": authentication},
            sort_keys=True,
        ),
        flush=True,
    )
    original = t2.t1.r3b._control_row
    original_offline_audit = t2.run_offline_probe_audit

    def patched(source_ctx, result, state_row):
        return _formal_prefix_control_row(
            original, source_ctx, result, state_row
        )

    t2.t1.r3b._control_row = patched
    if target.name == (
        "stage4_2r3c3t2_post_contract_neutralized_held_transport_"
        "identification.py"
    ):

        def authenticated_cached_offline_audit(ctx, selected_pairs):
            del ctx, selected_pairs
            return copy.deepcopy(cached_initial_offline_audit)

        t2.run_offline_probe_audit = authenticated_cached_offline_audit
    sys.argv = [str(target), *target_args]
    try:
        runpy.run_path(str(target), run_name="__main__")
    finally:
        t2.t1.r3b._control_row = original
        t2.run_offline_probe_audit = original_offline_audit


if __name__ == "__main__":
    main()
