#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_2R3C3T13S24D1R9_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
cd "${PROJECT_DIR}"
sha256sum -c SHA256SUMS
while IFS= read -r shell_file; do bash -n "${shell_file}"; done < <(find . -maxdepth 2 -type f -name '*.sh' -print)
"${PYTHON_BIN}" -m py_compile \
  docs/codex/audit_tools/stage4_2r3c3t13s24d1r9_central_row_replacement_preflight.py \
  docs/codex/audit_tools/stage4_2r3c3t13s24d1r9_independent_forensics.py \
  tests/test_stage4_2r3c3t13s24d1r9_central_row_replacement_preflight.py
"${PYTHON_BIN}" - <<'PY'
import json
from pathlib import Path
root = Path.cwd()
manifest = json.loads((root / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
for item in manifest["file_inventory"]:
    path = root / item
    if path.suffix == ".json":
        json.loads(path.read_text(encoding="utf-8"))
print("[T13S24D1R9 verify] strict JSON parse passed")
PY
"${PYTHON_BIN}" -m unittest -v \
  tests.test_stage4_2r3c3t13s24d1r9_central_row_replacement_preflight \
  tests.test_stage4_2r3c3t13s24d1r8_real_tsc_safety_sentinel \
  tests.test_stage4_2r3c3t13s24d1r7_temporal_basis_substitution_preflight
printf '[T13S24D1R9 verify] checksums, shell, compile, JSON, and focused tests passed.\n'

