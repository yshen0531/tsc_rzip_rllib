#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/tsc_all/tsc_rzip_rllib"
test "$PWD" = "$HOME/tsc_all/tsc_rzip_rllib"
source "$HOME/tsc_all/tsc_simulation/venv_simu/bin/activate"
REVISION="${C2AA2_SOURCE_REVISION:?C2AA2_SOURCE_REVISION is required}"
MODE="${C2AA2_MODE:-offline}"
OUTPUT="${C2AA2_OUTPUT:?C2AA2_OUTPUT is required}"
STAGE="configs/rgeo_zgeo_1ms_nr2r2c2aa2_supported_cube_directions.json"
if [ "$MODE" = offline ]; then
  python scripts/rgeo_zgeo_1ms_nr2r2c2aa2_directions.py offline --stage-config "$STAGE" --source-revision "$REVISION" --output "$OUTPUT"
elif [ "$MODE" = run ]; then
  python scripts/rgeo_zgeo_1ms_nr2r2c2aa2_directions.py run --stage-config "$STAGE" --source-revision "$REVISION" --output "$OUTPUT"
elif [ "$MODE" = independent ]; then
  python scripts/rgeo_zgeo_1ms_nr2r2c2aa2_independent.py --stage-config "$STAGE" --source-revision "$REVISION" --run-dir "$OUTPUT"
else
  printf 'invalid C2AA2_MODE=%s\n' "$MODE" >&2
  exit 2
fi
