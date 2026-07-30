#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_2R3B_PYTHON:-${PYTHON:-python3}}"
cd "${PROJECT_DIR}"

for path in \
  PACKAGE_MANIFEST.json SHA256SUMS \
  configs/stage4_2r3b_confirmatory_hidden_history_initial_state_370ms.json \
  configs/stage4_2r2_persistent_controller_checkpoint_replay_370ms.json \
  configs/stage4_2r1_true_tsc_plant_restart_action_replay_370ms.json \
  scripts/stage4_2r3b_confirmatory_hidden_history_initial_state.py \
  scripts/stage4_2r3b_server_postprocess.py \
  scripts/stage4_2r3b_shell_common.sh \
  tsc_rzip_rllib/diagnostics/stage4_2r3b_confirmatory_hidden_history_initial_state.py \
  tsc_rzip_rllib/diagnostics/stage4_2r2_persistent_controller_checkpoint_replay.py \
  tsc_rzip_rllib/diagnostics/stage4_2r1_true_tsc_plant_restart_action_replay.py \
  tests/test_stage4_2r3b_confirmatory_hidden_history_initial_state.py \
  tests/test_stage4_2r2_persistent_controller_checkpoint_replay.py \
  tests/test_stage4_2r1_true_tsc_plant_restart_action_replay.py \
  run_stage4_2r3b_confirmatory_hidden_history_initial_state_native.sh \
  run_stage4_2r3b_confirmatory_hidden_history_initial_state_nohup.sh \
  run_stage4_2r3b_server_postprocess.sh \
  run_stage4_2r3b_self_test.sh run_stage4_2r3b_verify_package.sh \
  run_stop_stage4_2r3b_now.sh; do
  [[ -f "${path}" ]] || {
    echo "ERROR: required packaged file missing: ${path}" >&2
    exit 1
  }
done

sha256sum -c SHA256SUMS
printf '[Stage4.2R3b verify] packaged file checksums passed.\n'
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
"${PYTHON_BIN}" - <<'PY'
from __future__ import annotations

import ast
import json
from pathlib import Path

root = Path.cwd()
manifest = json.loads(
    (root / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8")
)
expected = {
    "stage": "Stage4.2R3b",
    "controller_revision": "confirmatory_hidden_history_initial_state_mpc_v42r3b",
    "package_revision": "r42r3b_confirmatory_hidden_history_v1",
    "run_name": "stage4_2r3b_confirmatory_hidden_history_initial_state",
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
        or part in {"logs", "__pycache__", "artifacts"}
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
    stage4_2r3b_confirmatory_hidden_history_initial_state as r3,
)

cfg = json.loads(
    (
        root
        / "configs/stage4_2r3b_confirmatory_hidden_history_initial_state_370ms.json"
    ).read_text(encoding="utf-8")
)
r3.validate_config(cfg)
self_test = r3.self_test()
if not self_test.get("passed"):
    raise SystemExit("Stage4.2R3b self-test failed")
directions = r3._nullspace_directions(
    __import__("numpy").zeros((r3.N_COILS, r3.N_MODES), dtype=float)
    + __import__("numpy").pad(
        __import__("numpy").eye(3), ((0, r3.N_COILS - 3), (0, 0))
    )
)
common_prefix = {
    "source_experiment_id": "verify-source",
    "source_initial_action": [0.0] * r3.N_COILS,
    "actions": [
        [0.01 * (step + 1)] * r3.N_COILS for step in range(9)
    ],
    "prefix_action_digests": {
        "5": "verify-prefix-digest-5",
        "9": "verify-prefix-digest-9",
    },
    "action_digest": "verify-prefix-digest",
}
specs = r3._state_spec_grid(directions, cfg, common_prefix)
if len(specs) != 72 or len({row["pair_id"] for row in specs}) != 36:
    raise SystemExit("Stage4.2R3b state-generation matrix changed")
if r3._requested_workers(cfg) != 128:
    raise SystemExit("Stage4.2R3b Ray capacity changed")
contract = cfg["formal_timing_contract"]
if (
    contract["normal"]["arrival_deadline_step"] != 25
    or contract["normal"]["hold_through_step"] != 35
    or contract["weak"]["arrival_deadline_step"] != 27
    or contract["weak"]["hold_through_step"] != 37
    or contract["arrival_deadline_expansion_allowed"]
):
    raise SystemExit("immutable formal timing changed")
module = (
    root
    / "tsc_rzip_rllib/diagnostics/"
    "stage4_2r3b_confirmatory_hidden_history_initial_state.py"
).read_text(encoding="utf-8")
for token in (
    "run_offline_frozen_controller_audit",
    "FreshTaskController",
    "current_visible_state_only_at_new_task_start",
    "hidden_wire_current_available_to_controller",
    "forbid_control_outcome_selection",
    "common_prefix_action_digest",
    "deployed_package_fingerprint",
    "calibration_fingerprint",
    "mutual_prefix_group_separation_pass",
    "prefix_direction_strata_coverage_pass",
    "_control_pair_divergence",
    "real_closed_loop_formal_control_failure",
):
    if token not in module:
        raise SystemExit(f"Stage4.2R3b implementation guard missing: {token}")
for path in (
    root / "run_stage4_2r3b_confirmatory_hidden_history_initial_state_native.sh",
    root / "run_stop_stage4_2r3b_now.sh",
):
    if "ray stop --force" in path.read_text(encoding="utf-8"):
        raise SystemExit("Stage4.2R3b launcher contains broad Ray termination")
print(
    "[Stage4.2R3b verify] Python compile, JSON parse, import closure and "
    "scientific guardrails passed."
)
PY

mapfile -t SHELLS < <(find . -maxdepth 2 -type f -name '*.sh' -print | sort)
for script in "${SHELLS[@]}"; do
  bash -n "${script}"
done
printf '[Stage4.2R3b verify] declared shell scripts passed bash -n.\n'
"${PYTHON_BIN}" -m unittest discover -s tests -p 'test_*.py'
printf '[Stage4.2R3b verify] complete unittest discovery passed.\n'
