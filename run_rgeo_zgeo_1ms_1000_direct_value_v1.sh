#!/usr/bin/env bash
set -euo pipefail
MODE="${1:?usage: $0 fit|audit}"
ROOT="${NR1000_V1_PROJECT_ROOT:-$HOME/tsc_all/tsc_rzip_rllib}"
OUTPUT="${NR1000_V1_OUTPUT:?NR1000_V1_OUTPUT is required}"
REVISION="${NR1000_V1_SOURCE_REVISION:?NR1000_V1_SOURCE_REVISION is required}"
cd "$ROOT"; test "$PWD" = "$ROOT"
source "$HOME/tsc_all/tsc_simulation/venv_simu/bin/activate"
case "$MODE" in
 fit) python scripts/rgeo_zgeo_1ms_1000_direct_value_v1.py --config configs/rgeo_zgeo_1ms_1000_direct_value_v1.json --source-revision "$REVISION" --output "$OUTPUT" ;;
 audit) python scripts/rgeo_zgeo_1ms_1000_direct_value_v1_independent.py --config configs/rgeo_zgeo_1ms_1000_direct_value_v1.json --source-revision "$REVISION" --output "$OUTPUT" ;;
 *) echo "unknown mode: $MODE" >&2; exit 2 ;;
esac
