#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${NR1000_M1_PROJECT_ROOT:-$HOME/tsc_all/tsc_rzip_rllib}"
OUTPUT="${NR1000_M1_OUTPUT:?NR1000_M1_OUTPUT is required}"
SOURCE_REVISION="${NR1000_M1_SOURCE_REVISION:?NR1000_M1_SOURCE_REVISION is required}"

cd "$PROJECT_ROOT"
test "$PWD" = "$PROJECT_ROOT"
source "$HOME/tsc_all/tsc_simulation/venv_simu/bin/activate"

python scripts/rgeo_zgeo_1ms_1000_causal_m1.py \
  --config configs/rgeo_zgeo_1ms_1000_causal_m1.json \
  --source-revision "$SOURCE_REVISION" \
  --output "$OUTPUT"
