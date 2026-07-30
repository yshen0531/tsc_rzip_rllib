#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_2R3C2_PYTHON:-${PYTHON:-python3}}"
cd "${PROJECT_DIR}"

for path in \
  PACKAGE_MANIFEST.json SHA256SUMS \
  configs/stage4_2r3c2_restart_target_state_regulation_mpc_370ms.json \
  configs/stage4_2r3c1_authenticated_visible_manifold_phase_mpc_370ms.json \
  configs/stage4_2r3b_confirmatory_hidden_history_initial_state_370ms.json \
  configs/stage4_2r2_persistent_controller_checkpoint_replay_370ms.json \
  configs/stage4_2r1_true_tsc_plant_restart_action_replay_370ms.json \
  scripts/stage4_2r3c2_restart_target_state_regulation_mpc.py \
  scripts/stage4_2r3c2_server_postprocess.py \
  scripts/stage4_2r3c2_shell_common.sh \
  tsc_rzip_rllib/diagnostics/stage4_2r3c2_restart_target_state_regulation_mpc.py \
  tsc_rzip_rllib/diagnostics/stage4_2r3c1_authenticated_visible_manifold_phase_mpc.py \
  tsc_rzip_rllib/diagnostics/stage4_2r3b_confirmatory_hidden_history_initial_state.py \
  tsc_rzip_rllib/diagnostics/stage4_2r2_persistent_controller_checkpoint_replay.py \
  tsc_rzip_rllib/diagnostics/stage4_2r1_true_tsc_plant_restart_action_replay.py \
  tests/test_stage4_2r3c2_restart_target_state_regulation_mpc.py \
  tests/test_stage4_2r3b_confirmatory_hidden_history_initial_state.py \
  tests/test_stage4_2r2_persistent_controller_checkpoint_replay.py \
  tests/test_stage4_2r1_true_tsc_plant_restart_action_replay.py \
  run_stage4_2r3c2_restart_target_state_regulation_mpc_native.sh \
  run_stage4_2r3c2_restart_target_state_regulation_mpc_nohup.sh \
  run_stage4_2r3c2_server_postprocess.sh \
  run_stage4_2r3c2_self_test.sh run_stage4_2r3c2_verify_package.sh \
  run_stop_stage4_2r3c2_now.sh; do
  [[ -f "${path}" ]] || {
    echo "ERROR: required packaged file missing: ${path}" >&2
    exit 1
  }
done

sha256sum -c SHA256SUMS
printf '[Stage4.2R3c2 verify] packaged file checksums passed.\n'
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
"${PYTHON_BIN}" - <<'PY'
from __future__ import annotations

import ast
import json
from pathlib import Path

import numpy as np

root = Path.cwd()
manifest = json.loads(
    (root / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8")
)
expected = {
    "stage": "Stage4.2R3c2",
    "controller_revision": "restart_target_state_regulation_mpc_v42r3c2",
    "package_revision": "r42r3c2_restart_target_state_regulation_mpc_v1",
    "run_name": "stage4_2r3c2_restart_target_state_regulation_mpc",
}
for key, value in expected.items():
    if manifest.get(key) != value:
        raise SystemExit(
            f"PACKAGE_MANIFEST {key} mismatch: {manifest.get(key)!r}"
        )
rows = [
    line
    for line in (root / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
listed = [line.split(None, 1)[1].strip() for line in rows]
if len(rows) != manifest.get("declared_file_count"):
    raise SystemExit("declared file count mismatch")
if listed != manifest.get("file_inventory"):
    raise SystemExit("manifest inventory differs from SHA256SUMS")
if listed != sorted(set(listed)):
    raise SystemExit("inventory must be sorted and unique")
actual = []
for directory in ("configs", "scripts", "tests", "tsc_rzip_rllib"):
    for path in sorted((root / directory).rglob("*")):
        if (
            path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix != ".pyc"
        ):
            actual.append(path.relative_to(root).as_posix())
listed_tree = [
    item
    for item in listed
    if item.split("/", 1)[0]
    in {"configs", "scripts", "tests", "tsc_rzip_rllib"}
]
if actual != listed_tree:
    raise SystemExit(
        "replaced-tree inventory mismatch "
        f"missing={sorted(set(actual)-set(listed_tree))[:10]} "
        f"extra={sorted(set(listed_tree)-set(actual))[:10]}"
    )

for path in sorted(root.rglob("*.py")):
    if any(
        part.endswith("_runs")
        or part in {"logs", "__pycache__", "artifacts", ".codex_tmp"}
        for part in path.parts
    ):
        continue
    source = path.read_text(encoding="utf-8")
    compile(source, str(path), "exec")
    ast.parse(source, filename=str(path))
for path in sorted((root / "configs").glob("*.json")):
    json.loads(path.read_text(encoding="utf-8"))

modules = set()
module_by_path = {}
for path in sorted((root / "tsc_rzip_rllib").rglob("*.py")):
    module = (
        ".".join(path.parent.relative_to(root).parts)
        if path.name == "__init__.py"
        else ".".join(path.relative_to(root).with_suffix("").parts)
    )
    modules.add(module)
    module_by_path[path] = module


def resolve(package: str, level: int, module: str | None) -> str:
    if level == 0:
        return module or ""
    parts = package.split(".") if package else []
    drop = level - 1
    if drop > len(parts):
        raise SystemExit("invalid relative import")
    parts = parts[: len(parts) - drop]
    if module:
        parts.extend(module.split("."))
    return ".".join(parts)


missing = []
for path, module in module_by_path.items():
    package = module if path.name == "__init__.py" else module.rsplit(".", 1)[0]
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if name.startswith("tsc_rzip_rllib") and not any(
                    name == candidate or name.startswith(candidate + ".")
                    for candidate in modules
                ):
                    missing.append((str(path), name))
        elif isinstance(node, ast.ImportFrom):
            base = resolve(package, node.level, node.module)
            if (
                base.startswith("tsc_rzip_rllib")
                and base not in modules
                and not any(
                    candidate.startswith(base + ".") for candidate in modules
                )
            ):
                missing.append((str(path), base))
if missing:
    raise SystemExit(
        "missing packaged internal imports: " + repr(missing[:20])
    )

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c2_restart_target_state_regulation_mpc as r3c,
)

cfg = json.loads(
    (
        root
        / "configs/stage4_2r3c2_restart_target_state_regulation_mpc_370ms.json"
    ).read_text(encoding="utf-8")
)
r3c.validate_config(cfg)
self_test = r3c.self_test()
if not self_test.get("passed"):
    raise SystemExit("Stage4.2R3c2 self-test failed")
phase = r3c.select_visible_reference_phase(
    np.asarray(
        [[float(step), 0.0, 100.0 * step] for step in range(35)]
    ),
    [12.0, 0.0, 1200.0],
    candidate_min_phase=0,
    candidate_max_phase=20,
    scales=[1.0, 1.0, 100.0],
)
if (
    phase["selected_phase"] != 12
    or phase["hidden_wire_used"]
    or phase["source_action_used"]
    or phase["source_coil_current_used"]
    or phase["source_wire_current_used"]
    or phase["current_run_future_used"]
    or phase["reference_source"]
    != "authenticated_r17_actual_closed_loop_visible_RZI"
):
    raise SystemExit("visible-state phase-selection guard failed")
if r3c._requested_workers(cfg) != 128:
    raise SystemExit("Stage4.2R3c2 Ray capacity changed")
contract = cfg["formal_timing_contract"]
if (
    contract["normal"]["arrival_deadline_step"] != 25
    or contract["normal"]["hold_through_step"] != 35
    or contract["weak"]["arrival_deadline_step"] != 27
    or contract["weak"]["hold_through_step"] != 37
    or contract["arrival_deadline_expansion_allowed"]
):
    raise SystemExit("immutable formal timing changed")
if (
    not cfg["development_set_only"]
    or cfg["independent_hidden_history_confirmation"]
    or cfg["bc_dagger_or_rl_allowed"]
):
    raise SystemExit("Stage4.2R3c2 scientific scope changed")
phase_contract = cfg["phase_alignment"]
if (
    phase_contract["reference_manifold"]
    != "authenticated_r17_actual_closed_loop_visible_RZI"
    or phase_contract["reference_phase_count"] != 21
    or phase_contract["source_actions_allowed"]
    or phase_contract["source_coil_currents_allowed"]
    or phase_contract["source_wire_currents_allowed"]
):
    raise SystemExit("Stage4.2R3c2 visible-manifold contract changed")
regulation_contract = cfg["restart_regulation"]
if (
    regulation_contract["phase_zero_policy"] != "preserve_r3c1_path"
    or regulation_contract["nonzero_phase_policy"]
    != "target_state_regulation_from_task_step_zero"
    or not regulation_contract["nonzero_phase_regulation_persistent"]
    or regulation_contract["step_zero_velocity_initialization"] != "zero"
    or regulation_contract["pair_or_history_label_input_allowed"]
    or regulation_contract["source_result_input_allowed"]
):
    raise SystemExit("Stage4.2R3c2 restart-regulation contract changed")
source_contract = cfg["source_requirements"]
if (
    source_contract["required_stage4_2r3c_run_inventory_digest"]
    != "278395b364bb355c73b5f6de7461478b4bb239584a3f6bf9bf048aad12be9d13"
    or source_contract["required_stage4_2r3c_formal_pass_count"] != 20
    or source_contract["required_stage4_2r3c_formal_failure_count"] != 12
    or source_contract["required_stage4_2r3c_raw_forensics_sha256"]
    != "395427285a5bad0de9611629df0a13ade037ddd4f0e30e993e475a56c3dbafaa"
):
    raise SystemExit("Stage4.2R3c2 failed-R3c evidence contract changed")
if (
    source_contract["required_stage4_2r3c1_run_inventory_digest"]
    != "5bb79906dff14e4128e57f80dcd36576c881b46202e68a63f8dd977777812d2f"
    or source_contract["required_stage4_2r3c1_formal_pass_count"] != 16
    or source_contract["required_stage4_2r3c1_formal_failure_count"] != 16
    or source_contract["required_stage4_2r3c1_raw_forensics_sha256"]
    != "29e37da1d570179228a39700ac4f4c2c66067cf2a7295c2b744f2bfb40d50edd"
    or source_contract[
        "required_stage4_2r3c1_restart_regulation_diagnostic_sha256"
    ]
    != "9a278b5e97416ae2d98d05b4cff7ad2328ddd0a1ec8f3d14ded0421b184c124d"
):
    raise SystemExit("Stage4.2R3c2 failed-R3c1 evidence contract changed")
module = (
    root
    / "tsc_rzip_rllib/diagnostics/"
    "stage4_2r3c2_restart_target_state_regulation_mpc.py"
).read_text(encoding="utf-8")
for token in (
    "select_visible_reference_phase",
    "RestartTargetStateRegulationTaskController",
    "task_clock_starts_at_zero",
    "reference_clock_separate_from_task_clock",
    "hidden_wire_used",
    "align_delay_queue_priming",
    "run_offline_restart_regulation_audit",
    "restart_target_state_regulation",
    "_controller_spec",
    "_r3c1_evidence_fingerprint",
    "_r3c_evidence_fingerprint",
    "_visible_reference_manifold",
    "authenticated_r17_actual_closed_loop_visible_RZI_v1",
    "source_actions_included",
    "source_action_use_count",
    "visible_reference_manifold_exact_fraction",
    "maximum_source_action_abs_difference",
    "development_set_only",
    "masked_by_common_mode_both_fail",
    "real_closed_loop_formal_control_failure",
):
    if token not in module:
        raise SystemExit(f"Stage4.2R3c2 implementation guard missing: {token}")
for path in (
    root / "run_stage4_2r3c2_restart_target_state_regulation_mpc_native.sh",
    root / "run_stop_stage4_2r3c2_now.sh",
):
    if "ray stop --force" in path.read_text(encoding="utf-8"):
        raise SystemExit("Stage4.2R3c2 launcher contains broad Ray termination")
print(
    "[Stage4.2R3c2 verify] Python compile, JSON parse, import closure and "
    "scientific guardrails passed."
)
PY

mapfile -t SHELLS < <(find . -maxdepth 2 -type f -name '*.sh' -print | sort)
for script in "${SHELLS[@]}"; do
  bash -n "${script}"
done
printf '[Stage4.2R3c2 verify] declared shell scripts passed bash -n.\n'
"${PYTHON_BIN}" - <<'PY'
import unittest

import tests.conftest  # installs the Windows-only resource portability shim

suite = unittest.defaultTestLoader.discover("tests", pattern="test_*.py")
result = unittest.TextTestRunner(verbosity=1).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
PY
printf '[Stage4.2R3c2 verify] complete unittest discovery passed.\n'
