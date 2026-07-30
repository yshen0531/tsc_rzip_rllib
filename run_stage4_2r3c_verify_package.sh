#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_2R3C_PYTHON:-${PYTHON:-python3}}"
cd "${PROJECT_DIR}"

for path in \
  PACKAGE_MANIFEST.json SHA256SUMS \
  configs/stage4_2r3c_visible_state_phase_aligned_mpc_370ms.json \
  configs/stage4_2r3b_confirmatory_hidden_history_initial_state_370ms.json \
  configs/stage4_2r2_persistent_controller_checkpoint_replay_370ms.json \
  configs/stage4_2r1_true_tsc_plant_restart_action_replay_370ms.json \
  scripts/stage4_2r3c_visible_state_phase_aligned_mpc.py \
  scripts/stage4_2r3c_server_postprocess.py \
  scripts/stage4_2r3c_shell_common.sh \
  tsc_rzip_rllib/diagnostics/stage4_2r3c_visible_state_phase_aligned_mpc.py \
  tsc_rzip_rllib/diagnostics/stage4_2r3b_confirmatory_hidden_history_initial_state.py \
  tsc_rzip_rllib/diagnostics/stage4_2r2_persistent_controller_checkpoint_replay.py \
  tsc_rzip_rllib/diagnostics/stage4_2r1_true_tsc_plant_restart_action_replay.py \
  tests/test_stage4_2r3c_visible_state_phase_aligned_mpc.py \
  tests/test_stage4_2r3b_confirmatory_hidden_history_initial_state.py \
  tests/test_stage4_2r2_persistent_controller_checkpoint_replay.py \
  tests/test_stage4_2r1_true_tsc_plant_restart_action_replay.py \
  run_stage4_2r3c_visible_state_phase_aligned_mpc_native.sh \
  run_stage4_2r3c_visible_state_phase_aligned_mpc_nohup.sh \
  run_stage4_2r3c_server_postprocess.sh \
  run_stage4_2r3c_self_test.sh run_stage4_2r3c_verify_package.sh \
  run_stop_stage4_2r3c_now.sh; do
  [[ -f "${path}" ]] || {
    echo "ERROR: required packaged file missing: ${path}" >&2
    exit 1
  }
done

sha256sum -c SHA256SUMS
printf '[Stage4.2R3c verify] packaged file checksums passed.\n'
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
    "stage": "Stage4.2R3c",
    "controller_revision": "visible_state_phase_aligned_mpc_v42r3c",
    "package_revision": "r42r3c_visible_state_phase_aligned_mpc_v1",
    "run_name": "stage4_2r3c_visible_state_phase_aligned_mpc",
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
    stage4_2r3c_visible_state_phase_aligned_mpc as r3c,
)

cfg = json.loads(
    (
        root
        / "configs/stage4_2r3c_visible_state_phase_aligned_mpc_370ms.json"
    ).read_text(encoding="utf-8")
)
r3c.validate_config(cfg)
self_test = r3c.self_test()
if not self_test.get("passed"):
    raise SystemExit("Stage4.2R3c self-test failed")
phase = r3c.select_visible_reference_phase(
    np.asarray(
        [[float(step), 0.0, 100.0 * step] for step in range(35)]
    ),
    [12.0, 0.0, 1200.0],
    candidate_min_phase=0,
    candidate_max_phase=20,
    scales=[1.0, 1.0, 100.0],
)
if phase["selected_phase"] != 12 or phase["hidden_wire_used"]:
    raise SystemExit("visible-state phase-selection guard failed")
if r3c._requested_workers(cfg) != 128:
    raise SystemExit("Stage4.2R3c Ray capacity changed")
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
    raise SystemExit("Stage4.2R3c scientific scope changed")
module = (
    root
    / "tsc_rzip_rllib/diagnostics/"
    "stage4_2r3c_visible_state_phase_aligned_mpc.py"
).read_text(encoding="utf-8")
for token in (
    "select_visible_reference_phase",
    "PhaseAlignedTaskController",
    "task_clock_starts_at_zero",
    "reference_clock_separate_from_task_clock",
    "hidden_wire_used",
    "align_delay_queue_priming",
    "run_offline_phase_alignment_audit",
    "maximum_source_action_abs_difference",
    "development_set_only",
    "masked_by_common_mode_both_fail",
    "real_closed_loop_formal_control_failure",
):
    if token not in module:
        raise SystemExit(f"Stage4.2R3c implementation guard missing: {token}")
for path in (
    root / "run_stage4_2r3c_visible_state_phase_aligned_mpc_native.sh",
    root / "run_stop_stage4_2r3c_now.sh",
):
    if "ray stop --force" in path.read_text(encoding="utf-8"):
        raise SystemExit("Stage4.2R3c launcher contains broad Ray termination")
print(
    "[Stage4.2R3c verify] Python compile, JSON parse, import closure and "
    "scientific guardrails passed."
)
PY

mapfile -t SHELLS < <(find . -maxdepth 2 -type f -name '*.sh' -print | sort)
for script in "${SHELLS[@]}"; do
  bash -n "${script}"
done
printf '[Stage4.2R3c verify] declared shell scripts passed bash -n.\n'
"${PYTHON_BIN}" -m unittest discover -s tests -p 'test_*.py'
printf '[Stage4.2R3c verify] complete unittest discovery passed.\n'
