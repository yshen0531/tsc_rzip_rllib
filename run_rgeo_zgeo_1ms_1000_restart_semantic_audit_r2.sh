#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
: "${NR1000_SEMANTIC_AUDIT_SOURCE_REVISION:?set NR1000_SEMANTIC_AUDIT_SOURCE_REVISION}"
VENV="${NR1000_VENV:-$HOME/tsc_all/tsc_simulation/venv_simu}"
. "$VENV/bin/activate"
python scripts/rgeo_zgeo_1ms_1000_restart_semantic_audit_r2.py \
  --source-revision "$NR1000_SEMANTIC_AUDIT_SOURCE_REVISION" \
  --output "${1:?missing fresh output path}"
