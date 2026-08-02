#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

sha256sum -c SHA256SUMS
python -m compileall -q configs scripts tsc_rzip_rllib tests
python - <<'PY'
import json
from pathlib import Path
for path in Path('.').rglob('*.json'):
    json.loads(path.read_text(encoding='utf-8'))
print('JSON OK')
PY
python -m tsc_rzip_rllib.diagnostics.stage4_2r3c3t13s17_causal_multi_drift_belief_preflight --self-test
python -m unittest tests.test_stage4_2r3c3t13s17_causal_multi_drift_belief_preflight
printf 'T13S17 PACKAGE OK\n'
