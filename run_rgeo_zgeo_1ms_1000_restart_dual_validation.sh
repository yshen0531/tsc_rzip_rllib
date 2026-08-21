#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
: "${NR1000_DUAL_SOURCE_REVISION:?set NR1000_DUAL_SOURCE_REVISION}"
VENV="${NR1000_VENV:-$HOME/tsc_all/tsc_simulation/venv_simu}"
. "$VENV/bin/activate"

MODE="${1:?mode must be offline or run}"
OUTPUT="${2:?missing fresh output path}"
ARGS=(--config configs/rgeo_zgeo_1ms_1000_restart_dual_validation.json
      --source-revision "$NR1000_DUAL_SOURCE_REVISION" --output "$OUTPUT")
case "$MODE" in
  offline) ARGS+=(--offline) ;;
  run) ;;
  *) echo "mode must be offline or run" >&2; exit 2 ;;
esac
python scripts/rgeo_zgeo_1ms_1000_restart_dual_validation.py "${ARGS[@]}"
