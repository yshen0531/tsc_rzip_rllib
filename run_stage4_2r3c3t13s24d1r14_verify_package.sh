#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_2R3C3T13S24D1R14_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
[[ -x "${PYTHON_BIN}" ]] || { echo "ERROR: server virtualenv Python not executable" >&2; exit 1; }
cd "${PROJECT_DIR}"
tr -d '\r' < SHA256SUMS | sha256sum -c -
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
"${PYTHON_BIN}" - <<'PY'
from __future__ import annotations

import ast
import json
from pathlib import Path

root = Path.cwd()
manifest = json.loads((root / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
expected = {
    "stage": "Stage4.2R3c3T13S24D1R14",
    "run_name": "stage4_2r3c3t13s24d1r14_zero_baseline_signed_excitation_sentinel",
    "campaign_identity": "zero_baseline_signed_excitation_safety_geometry_sentinel_v1",
    "controller_revision": "zero_baseline_signed_excitation_v42r3c3t13s24d1r14_v2",
    "package_revision": "r42r3c3t13s24d1r14_zero_baseline_signed_excitation_v2",
}
for key, value in expected.items():
    if manifest.get(key) != value:
        raise SystemExit(f"PACKAGE_MANIFEST {key} mismatch")
rows = [
    line
    for line in (root / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
listed = [line.split(None, 1)[1].strip() for line in rows]
if listed != manifest.get("file_inventory") or listed != sorted(set(listed)):
    raise SystemExit("package inventory mismatch")
if len(listed) != manifest.get("declared_file_count"):
    raise SystemExit("declared file count mismatch")
actual = []
for directory in ("configs", "scripts", "tests", "tsc_rzip_rllib"):
    for path in sorted((root / directory).rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            actual.append(path.relative_to(root).as_posix())
listed_tree = [
    item
    for item in listed
    if item.split("/", 1)[0] in {"configs", "scripts", "tests", "tsc_rzip_rllib"}
]
if actual != listed_tree:
    raise SystemExit("replaced-tree inventory mismatch")
required = {
    "AGENTS.md",
    "configs/stage4_2r3c3t13s24d1r14_zero_baseline_signed_excitation_sentinel_370ms.json",
    "docs/codex/reports/STAGE4_2R3C3T13S24D1R14_ZERO_BASELINE_SIGNED_EXCITATION_SENTINEL_DESIGN.md",
    "docs/codex/reports/STAGE4_2R3C3T13S24D1R14_V1_ISSUE_GATE_HOTFIX_AUDIT.md",
    "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14_independent_forensics.py",
    "run_stage4_2r3c3t13s24d1r14_common.sh",
    "run_stage4_2r3c3t13s24d1r14_native.sh",
    "run_stage4_2r3c3t13s24d1r14_nohup.sh",
    "run_stage4_2r3c3t13s24d1r14_self_test.sh",
    "run_stage4_2r3c3t13s24d1r14_verify_package.sh",
    "run_stop_stage4_2r3c3t13s24d1r14_now.sh",
    "scripts/stage4_2r3c3t13s24d1r14_shell_common.sh",
    "scripts/stage4_2r3c3t13s24d1r14_zero_baseline_signed_excitation_sentinel.py",
    "tests/test_stage4_2r3c3t13s24d1r14_zero_baseline_signed_excitation_sentinel.py",
    "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14_zero_baseline_signed_excitation_sentinel.py",
    "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r13_zero_increment_deconfounding_sentinel.py",
}
if not required.issubset(set(listed)):
    raise SystemExit(f"D1R14 required package files missing: {sorted(required - set(listed))}")
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
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14_zero_baseline_signed_excitation_sentinel as d1r14,
)
config = root / "configs/stage4_2r3c3t13s24d1r14_zero_baseline_signed_excitation_sentinel_370ms.json"
cfg = json.loads(config.read_text(encoding="utf-8"))
d1r14._validate_config(cfg, config)
if not d1r14.self_test(config)["passed"]:
    raise SystemExit("D1R14 self-test failed")
for path in (
    root / "run_stage4_2r3c3t13s24d1r14_native.sh",
    root / "run_stop_stage4_2r3c3t13s24d1r14_now.sh",
):
    text = path.read_text(encoding="utf-8")
    if "ray stop --force" in text or "pkill" in text:
        raise SystemExit("broad process termination is forbidden")
print("[T13S24D1R14 verify] Python/JSON/scientific guards passed.")
PY
mapfile -t SHELLS < <(find . -maxdepth 2 -type f -name '*.sh' -print | sort)
for script in "${SHELLS[@]}"; do bash -n "${script}"; done
"${PYTHON_BIN}" -m unittest -v \
  tests.test_stage4_2r3c3t13s24d1r14_zero_baseline_signed_excitation_sentinel
printf '[T13S24D1R14 verify] checksums, shell syntax and focused tests passed.\n'
