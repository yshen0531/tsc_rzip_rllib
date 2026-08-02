#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

sha256sum -c SHA256SUMS
python -m compileall -q configs scripts tsc_rzip_rllib tests
python - <<'PY'
import json
from pathlib import Path

manifest_path = Path('PACKAGE_MANIFEST.json')
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
inventory = manifest['file_inventory']
if len(inventory) != manifest['declared_file_count']:
    raise RuntimeError('PACKAGE_MANIFEST declared_file_count mismatch')
json_paths = [Path(path) for path in inventory if path.endswith('.json')]
for path in json_paths:
    try:
        json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        print(f'JSON FAIL: {path}')
        raise
print(f'DECLARED JSON OK ({len(json_paths)})')
PY
python -m tsc_rzip_rllib.diagnostics.stage4_2r3c3t13s18_pooled_causal_observer_preflight --self-test
python -m unittest tests.test_stage4_2r3c3t13s18_pooled_causal_observer_preflight
printf 'T13S18 PACKAGE OK\n'
