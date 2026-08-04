#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)";PYTHON_BIN="${STAGE4_2R3C3T13S24D1R14R7R1_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}";cd "${PROJECT_DIR}";tr -d '\r' < SHA256SUMS | sha256sum -c -;export PYTHONPATH="${PROJECT_DIR}"
"${PYTHON_BIN}" - <<'PY'
import json
from pathlib import Path
from docs.codex.audit_tools import stage4_2r3c3t13s24d1r14r7r1_continuous_lag_response_model as p
from docs.codex.audit_tools import stage4_2r3c3t13s24d1r14r7r1_independent_forensics as i
r=Path.cwd();m=json.loads((r/'PACKAGE_MANIFEST.json').read_text());c=json.loads((r/'configs/stage4_2r3c3t13s24d1r14r7r1_continuous_lag_response_model_v1.json').read_text())
assert m['stage']==c['stage'] and m['package_revision']==c['package_revision'];p._validate_config(c);i._validate(c);print('R7R1_VERIFY_OK')
PY
mapfile -t S < <(find . -maxdepth 2 -type f -name '*.sh' -print|sort);for f in "${S[@]}";do bash -n "$f";done
"${PYTHON_BIN}" -m unittest -v tests.test_stage4_2r3c3t13s24d1r14r7r1_continuous_lag_response_model
