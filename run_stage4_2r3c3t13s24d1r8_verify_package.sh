#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${PROJECT_DIR}"
sha256sum -c SHA256SUMS
python_bin="${STAGE4_2R3C3T13S24D1R8_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
"${python_bin}" - <<'PY'
import json
from pathlib import Path
root = Path.cwd()
manifest = json.loads((root / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
for item in manifest["file_inventory"]:
    path = root / item
    if path.suffix == ".json":
        json.loads(path.read_text(encoding="utf-8"))
print("[T13S24D1R8 verify] manifest JSON parse passed")
PY
while IFS= read -r shell_file; do bash -n "${shell_file}"; done < <(find . -maxdepth 2 -type f -name '*.sh' -print)
"${python_bin}" -m py_compile \
  tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r8_real_tsc_safety_sentinel.py \
  docs/codex/audit_tools/stage4_2r3c3t13s24d1r8_real_tsc_safety_sentinel_forensics.py \
  scripts/stage4_2r3c3t13s24d1r8_real_tsc_safety_sentinel.py \
  tests/test_stage4_2r3c3t13s24d1r8_real_tsc_safety_sentinel.py
"${python_bin}" -m unittest -v \
  tests.test_stage4_2r3c3t13s24d1r8_real_tsc_safety_sentinel \
  tests.test_stage4_2r3c3t13s24_sequential_transition_identification \
  tests.test_stage4_2r3c3t13s24d1r7_temporal_basis_substitution_preflight
printf '[T13S24D1R8 verify] checksums, shell syntax, compile, JSON and focused tests passed.\n'
