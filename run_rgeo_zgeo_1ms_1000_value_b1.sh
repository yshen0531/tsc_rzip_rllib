#!/usr/bin/env bash
set -euo pipefail

MODE="${1:?usage: $0 offline|run|audit}"
PROJECT_ROOT="${NR1000_B1_PROJECT_ROOT:-$HOME/tsc_all/tsc_rzip_rllib}"
OUTPUT="${NR1000_B1_OUTPUT:?NR1000_B1_OUTPUT is required}"
SOURCE_REVISION="${NR1000_B1_SOURCE_REVISION:?NR1000_B1_SOURCE_REVISION is required}"

cd "$PROJECT_ROOT"
test "$PWD" = "$PROJECT_ROOT"
source "$HOME/tsc_all/tsc_simulation/venv_simu/bin/activate"

case "$MODE" in
  offline)
    python scripts/rgeo_zgeo_1ms_1000_value_b1.py offline \
      --config configs/rgeo_zgeo_1ms_1000_value_b1.json \
      --source-revision "$SOURCE_REVISION" --output "$OUTPUT" ;;
  run)
    python scripts/rgeo_zgeo_1ms_1000_value_b1.py run \
      --config configs/rgeo_zgeo_1ms_1000_value_b1.json \
      --source-revision "$SOURCE_REVISION" --output "$OUTPUT" ;;
  audit)
    python scripts/rgeo_zgeo_1ms_1000_value_b1_independent.py \
      --config configs/rgeo_zgeo_1ms_1000_value_b1.json \
      --source-revision "$SOURCE_REVISION" --run-dir "$OUTPUT" ;;
  *) echo "unknown mode: $MODE" >&2; exit 2 ;;
esac
