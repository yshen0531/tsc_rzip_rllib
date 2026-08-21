#!/usr/bin/env bash
set -euo pipefail
ROOT="${NR1000_PROJECT_ROOT:-$HOME/tsc_all/tsc_rzip_rllib}"
cd "$ROOT"
: "${NR1000_M0_SOURCE_REVISION:?set NR1000_M0_SOURCE_REVISION}"
VENV="${NR1000_VENV:-$HOME/tsc_all/tsc_simulation/venv_simu}"
. "$VENV/bin/activate"
DEST="${1:?missing output directory}"
python scripts/rgeo_zgeo_1ms_1000_causal_m0.py \
  --config configs/rgeo_zgeo_1ms_1000_causal_m0.json \
  --source-revision "$NR1000_M0_SOURCE_REVISION" \
  --output "$DEST"
