#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/tsc_all/tsc_rzip_rllib"
test "$PWD" = "$HOME/tsc_all/tsc_rzip_rllib"
source "$HOME/tsc_all/tsc_simulation/venv_simu/bin/activate"
REVISION="${NR2_SOURCE_REVISION:?NR2_SOURCE_REVISION is required}"
MODE="${NR2_MODE:-offline}"
OUTPUT="${NR2_OUTPUT:?NR2_OUTPUT is required}"
if [ "$MODE" = offline ]; then
  python scripts/rgeo_zgeo_1ms_nr2_collect.py offline --source-revision "$REVISION" --output "$OUTPUT"
elif [ "$MODE" = development_calibration ]; then
  python scripts/rgeo_zgeo_1ms_nr2_collect.py collect --source-revision "$REVISION" --output "$OUTPUT" --phase development_calibration
elif [ "$MODE" = holdout ]; then
  python scripts/rgeo_zgeo_1ms_nr2_collect.py collect --source-revision "$REVISION" --output "$OUTPUT" --phase holdout --authorization "${NR2_AUTHORIZATION:?NR2_AUTHORIZATION is required}"
else
  printf 'invalid NR2_MODE=%s\n' "$MODE" >&2; exit 2
fi
