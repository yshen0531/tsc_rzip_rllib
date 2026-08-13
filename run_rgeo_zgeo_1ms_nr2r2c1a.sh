#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/tsc_all/tsc_rzip_rllib"
test "$PWD" = "$HOME/tsc_all/tsc_rzip_rllib"
source "$HOME/tsc_all/tsc_simulation/venv_simu/bin/activate"
REVISION="${C1A_SOURCE_REVISION:?C1A_SOURCE_REVISION is required}"
MODE="${C1A_MODE:-offline}"
OUTPUT="${C1A_OUTPUT:?C1A_OUTPUT is required}"
STAGE="configs/rgeo_zgeo_1ms_nr2r2c1a_source_replay.json"
if [ "$MODE" = offline ]; then
  python scripts/rgeo_zgeo_1ms_nr2r2c1a_source_replay.py offline --stage-config "$STAGE" --source-revision "$REVISION" --output "$OUTPUT"
elif [ "$MODE" = run ]; then
  python scripts/rgeo_zgeo_1ms_nr2r2c1a_source_replay.py run --stage-config "$STAGE" --source-revision "$REVISION" --output "$OUTPUT"
elif [ "$MODE" = independent ]; then
  python scripts/rgeo_zgeo_1ms_nr2r2c1a_independent.py --stage-config "$STAGE" --source-revision "$REVISION" --run-dir "$OUTPUT"
else
  printf 'invalid C1A_MODE=%s\n' "$MODE" >&2
  exit 2
fi
