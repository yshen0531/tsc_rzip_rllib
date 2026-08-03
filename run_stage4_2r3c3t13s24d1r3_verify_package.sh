#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_2R3C3T13S24D1R3_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
[[ -x "${PYTHON_BIN}" ]] || { echo "ERROR: server virtualenv Python not executable" >&2; exit 1; }
cd "${PROJECT_DIR}"
sha256sum -c SHA256SUMS
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
"${PYTHON_BIN}" - <<'PY'
from __future__ import annotations

import ast
import json
from pathlib import Path

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r3_causal_split_return_preflight as stage,
)

root = Path.cwd()
manifest = json.loads((root / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
expected = {
    "stage": "Stage4.2R3c3T13S24D1R3",
    "run_name": "stage4_2r3c3t13s24d1r3_causal_split_return_preflight",
    "campaign_identity": "causal_split_exact_return_preflight_v1",
    "controller_revision": "causal_split_exact_return_preflight_v1",
    "package_revision": "r42r3c3t13s24d1r3_causal_split_return_preflight_v1",
    "implementation_checkpoint": "1ccd0e3",
}
for key, value in expected.items():
    if manifest.get(key) != value:
        raise SystemExit(f"PACKAGE_MANIFEST {key} mismatch")

lines = [
    line
    for line in (root / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
listed = [line.split(None, 1)[1].strip() for line in lines]
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
    path
    for path in listed
    if path.split("/", 1)[0] in {"configs", "scripts", "tests", "tsc_rzip_rllib"}
]
if actual != listed_tree:
    raise SystemExit("replaced-tree inventory mismatch")

for relative in listed:
    path = root / relative
    if path.suffix == ".py":
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")
        ast.parse(source, filename=str(path))
    elif path.suffix == ".json":
        json.loads(path.read_text(encoding="utf-8"))

config_path = root / "configs/stage4_2r3c3t13s24d1r3_causal_split_return_preflight_v1.json"
config = json.loads(config_path.read_text(encoding="utf-8"))
stage._validate_config(config, config_path)
print("[T13S24D1R3 verify] Python/JSON/scientific guards passed.")
PY
mapfile -t SHELLS < <(find . -maxdepth 2 -type f -name '*.sh' -print | sort)
for script in "${SHELLS[@]}"; do bash -n "${script}"; done
"${PYTHON_BIN}" -m unittest -v \
  tests.test_stage4_2r3c3t13s24d1r3_causal_split_return_preflight \
  tests.test_stage4_2r3c3t13s24d1r2_real_tsc_safety_sentinel \
  tests.test_stage4_2r3c3t13s24d1r2_retrospective_prefix_forensics
printf '[T13S24D1R3 verify] checksums, inventory, shell syntax, compile, JSON and focused tests passed.\n'
