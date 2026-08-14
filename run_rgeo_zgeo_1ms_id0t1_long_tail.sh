#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/tsc_all/tsc_rzip_rllib"
test "$PWD" = "$HOME/tsc_all/tsc_rzip_rllib"
source "$HOME/tsc_all/tsc_simulation/venv_simu/bin/activate"
REVISION="${ID0T1_SOURCE_REVISION:?ID0T1_SOURCE_REVISION is required}"
MODE="${ID0T1_MODE:-offline}"
OUTPUT="${ID0T1_OUTPUT:?ID0T1_OUTPUT is required}"
STAGE="configs/rgeo_zgeo_1ms_id0t1_long_tail.json"
if [ "$MODE" = offline ]; then
  python scripts/rgeo_zgeo_1ms_id0t1_long_tail.py offline --stage-config "$STAGE" --source-revision "$REVISION" --output "$OUTPUT"
elif [ "$MODE" = run ]; then
  python scripts/rgeo_zgeo_1ms_id0t1_long_tail.py run --stage-config "$STAGE" --source-revision "$REVISION" --output "$OUTPUT"
elif [ "$MODE" = independent ]; then
  python scripts/rgeo_zgeo_1ms_id0t1_long_tail_independent.py --stage-config "$STAGE" --source-revision "$REVISION" --run-dir "$OUTPUT"
else
  printf 'invalid ID0T1_MODE=%s\n' "$MODE" >&2
  exit 2
fi
