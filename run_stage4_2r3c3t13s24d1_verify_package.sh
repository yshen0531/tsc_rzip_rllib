#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${PROJECT_DIR}"
sha256sum -c SHA256SUMS
python_bin="${STAGE4_2R3C3T13S24D1_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
"${python_bin}" - <<'PY'
import json
from pathlib import Path
root = Path.cwd()
manifest = json.loads((root / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
for item in manifest["file_inventory"]:
    path = root / item
    if path.suffix == ".json":
        json.loads(path.read_text(encoding="utf-8"))
print("[T13S24D1 verify] JSON parse passed")
PY
while IFS= read -r shell_file; do bash -n "${shell_file}"; done < <(find . -maxdepth 2 -type f -name '*.sh' -print)
"${python_bin}" -m py_compile \
  docs/codex/audit_tools/stage4_2r3c3t13s24d1_contracted_amplitude_preflight.py \
  tests/test_stage4_2r3c3t13s24d1_contracted_amplitude_preflight.py
"${python_bin}" -m unittest -v \
  tests.test_stage4_2r3c3t13s24d1_contracted_amplitude_preflight \
  tests.test_stage4_2r3c3t13s24_training_sequence_forensics \
  tests.test_stage4_2r3c3t13s23r1_amplitude_coded_hadamard_preflight
printf '[T13S24D1 verify] checksums, shell syntax, compile, JSON and focused tests passed.\n'
