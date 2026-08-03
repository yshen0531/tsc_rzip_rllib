#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_2R3C3T13S24D1R6_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
[[ -x "${PYTHON_BIN}" ]] || { echo "ERROR: server virtualenv Python not executable" >&2; exit 1; }
cd "${PROJECT_DIR}"
sha256sum -c SHA256SUMS
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
"${PYTHON_BIN}" - <<'PY'
from __future__ import annotations

import ast
import json
from pathlib import Path

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r6_recursive_split_return_safety_sentinel as stage,
)

root = Path.cwd()
manifest = json.loads((root / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
expected = {
    "stage": stage.STAGE,
    "run_name": stage.RUN_NAME,
    "campaign_identity": stage.CAMPAIGN_IDENTITY,
    "controller_revision": stage.CONTROLLER_REVISION,
    "package_revision": stage.PACKAGE_REVISION,
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

stage._validate_config(
    json.loads(stage._package_path(manifest, "config_path").read_text(encoding="utf-8")),
    stage._package_path(manifest, "config_path"),
)
print("[T13S24D1R6 verify] Python/JSON/scientific guards passed.")
PY
mapfile -t SHELLS < <(find . -maxdepth 2 -type f -name '*.sh' -print | sort)
for script in "${SHELLS[@]}"; do bash -n "${script}"; done
"${PYTHON_BIN}" -m unittest -v \
  tests.test_stage4_2r3c3t13s24d1r6_recursive_split_return_safety_sentinel
printf '[T13S24D1R6 verify] checksums, inventory, shell syntax, compile, JSON and focused tests passed.\n'
