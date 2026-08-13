#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/tsc_all/tsc_rzip_rllib"
test "$PWD" = "$HOME/tsc_all/tsc_rzip_rllib"
source "$HOME/tsc_all/tsc_simulation/venv_simu/bin/activate"
REVISION="${NR1_SOURCE_REVISION:?NR1_SOURCE_REVISION is required}"
MODE="${NR1_MODE:-offline}"
STAMP="$(date +%Y%m%d_%H%M%S)"
if [ "$MODE" = offline ]; then
  OUTPUT="${NR1_OUTPUT:-$PWD/rgeo_zgeo_1ms_nr1_offline_${STAMP}_${REVISION}.json}"
  python scripts/rgeo_zgeo_1ms_nr1_qualification.py offline --config configs/rgeo_zgeo_1ms_nr1_safety_effect.json --source-revision "$REVISION" --output "$OUTPUT"
elif [ "$MODE" = run ]; then
  OUTPUT="${NR1_OUTPUT:?NR1_OUTPUT run directory is required}"
  python scripts/rgeo_zgeo_1ms_nr1_qualification.py run --config configs/rgeo_zgeo_1ms_nr1_safety_effect.json --source-revision "$REVISION" --output "$OUTPUT"
else
  printf 'invalid NR1_MODE=%s\n' "$MODE" >&2; exit 2
fi
