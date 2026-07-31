#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_2R3C3T11_PYTHON:-${PYTHON:-python3}}"
cd "${PROJECT_DIR}"
sha256sum -c SHA256SUMS
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
"${PYTHON_BIN}" -m compileall -q configs scripts tsc_rzip_rllib tests docs/codex/audit_tools
"${PYTHON_BIN}" - <<'PY'
import json
from pathlib import Path
m=json.loads(Path('PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
expected={
 'stage':'Stage4.2R3c3T11',
 'run_name':'stage4_2r3c3t11_persistent_step_response_preflight',
 'controller_revision':'no_controller_offline_preflight_v1',
 'package_revision':'r42r3c3t11_persistent_step_preflight_v1'}
for key,value in expected.items():
    if m.get(key)!=value: raise SystemExit(f'PACKAGE_MANIFEST {key} mismatch')
listed=m['file_inventory']
rows=[line for line in Path('SHA256SUMS').read_text().splitlines() if line]
if listed != [line.split(None,1)[1] for line in rows] or listed != sorted(set(listed)):
    raise SystemExit('package inventory mismatch')
actual=[]
for directory in ('configs','scripts','tests','tsc_rzip_rllib'):
    for path in sorted(Path(directory).rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
            actual.append(path.as_posix())
listed_tree=[x for x in listed if x.split('/',1)[0] in {'configs','scripts','tests','tsc_rzip_rllib'}]
if actual != listed_tree: raise SystemExit('replaced-tree inventory mismatch')
for path in Path('configs').glob('*.json'): json.loads(path.read_text(encoding='utf-8'))
print('[Stage4.2R3c3T11 verify] inventory, compile, and JSON passed.')
PY
mapfile -t SHELLS < <(find . -maxdepth 2 -type f -name '*.sh' -print | sort)
for script in "${SHELLS[@]}"; do bash -n "${script}"; done
"${PYTHON_BIN}" -m unittest \
  tests.test_stage4_2r3c3t10_interaction_aware_feasibility \
  tests.test_stage4_2r3c3t11_persistent_step_response_preflight
printf '[Stage4.2R3c3T11 verify] shell syntax and focused tests passed.\n'
