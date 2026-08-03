#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_2R3C3T13S23D1_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
[[ -x "${PYTHON_BIN}" ]] || {
  echo "ERROR: server virtualenv Python not executable" >&2
  exit 1
}
cd "${PROJECT_DIR}"
sha256sum -c SHA256SUMS
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
"${PYTHON_BIN}" - <<'PY'
from __future__ import annotations

import ast
import json
from pathlib import Path

from docs.codex.audit_tools import (
    stage4_2r3c3t13s23d1_bounded_schedule_redesign_search as d1,
)

root = Path.cwd()
manifest = json.loads((root / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
expected = {
    "stage": "Stage4.2R3c3T13S23D1",
    "run_name": "stage4_2r3c3t13s23d1_bounded_schedule_redesign_search",
    "campaign_identity": "bounded_ternary_exact_card15_schedule_redesign_search_v1",
    "package_revision": "r42r3c3t13s23d1_bounded_schedule_redesign_search_v1",
}
for key, value in expected.items():
    if manifest.get(key) != value:
        raise SystemExit(f"PACKAGE_MANIFEST {key} mismatch")
rows = [line for line in (root / "SHA256SUMS").read_text(encoding="utf-8").splitlines() if line.strip()]
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
listed_tree = [item for item in listed if item.split("/", 1)[0] in {"configs", "scripts", "tests", "tsc_rzip_rllib"}]
if actual != listed_tree:
    raise SystemExit("replaced-tree inventory mismatch")
for path in sorted(root.rglob("*.py")):
    if any(part.endswith("_runs") or part in {"logs", "__pycache__", "artifacts", ".codex_tmp"} for part in path.parts):
        continue
    source = path.read_text(encoding="utf-8")
    compile(source, str(path), "exec")
    ast.parse(source, filename=str(path))
for path in sorted((root / "configs").glob("*.json")):
    json.loads(path.read_text(encoding="utf-8"))
cfg = json.loads((root / "configs/stage4_2r3c3t13s23d1_bounded_schedule_redesign_search_v1.json").read_text(encoding="utf-8"))
d1._validate_design(cfg)
print("[T13S23D1 verify] Python/JSON/scientific guards passed.")
PY
mapfile -t SHELLS < <(find . -maxdepth 2 -type f -name '*.sh' -print | sort)
for script in "${SHELLS[@]}"; do
  bash -n "${script}"
done
"${PYTHON_BIN}" -m unittest -v \
  tests.test_stage4_2r3c3t13s23d1_bounded_schedule_redesign_search
printf '[T13S23D1 verify] checksums, shell syntax and focused tests passed.\n'
