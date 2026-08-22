#!/usr/bin/env bash
set -euo pipefail
MODE="${1:?usage: $0 offline|run|audit}"
PROJECT_ROOT="${NR1000_D3_PROJECT_ROOT:-$HOME/tsc_all/tsc_rzip_rllib}"
OUTPUT="${NR1000_D3_OUTPUT:?NR1000_D3_OUTPUT is required}"
SOURCE_REVISION="${NR1000_D3_SOURCE_REVISION:?NR1000_D3_SOURCE_REVISION is required}"
cd "$PROJECT_ROOT"
test "$PWD" = "$PROJECT_ROOT"
source "$HOME/tsc_all/tsc_simulation/venv_simu/bin/activate"
case "$MODE" in
  offline) python scripts/rgeo_zgeo_1ms_1000_discrete_value_d3.py offline --config configs/rgeo_zgeo_1ms_1000_discrete_value_d3.json --source-revision "$SOURCE_REVISION" --output "$OUTPUT" ;;
  run) python scripts/rgeo_zgeo_1ms_1000_discrete_value_d3.py run --config configs/rgeo_zgeo_1ms_1000_discrete_value_d3.json --source-revision "$SOURCE_REVISION" --output "$OUTPUT" ;;
  audit) python scripts/rgeo_zgeo_1ms_1000_discrete_value_d3_independent.py --config configs/rgeo_zgeo_1ms_1000_discrete_value_d3.json --source-revision "$SOURCE_REVISION" --run-dir "$OUTPUT" ;;
  *) echo "unknown mode: $MODE" >&2; exit 2 ;;
esac
