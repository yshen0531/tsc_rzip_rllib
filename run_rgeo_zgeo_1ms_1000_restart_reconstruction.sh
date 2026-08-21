#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
: "${NR1000_RECON_SOURCE_REVISION:?set NR1000_RECON_SOURCE_REVISION}"
VENV="${NR1000_VENV:-$HOME/tsc_all/tsc_simulation/venv_simu}"
. "$VENV/bin/activate"

MODE="${1:?mode must be offline or run}"
OUTPUT="${2:?missing fresh output path}"
case "$MODE" in
  offline) OFFLINE=1 ;;
  run) OFFLINE=0 ;;
  *) echo "mode must be offline or run" >&2; exit 2 ;;
esac

if [[ "$OFFLINE" == 1 ]]; then
  python scripts/rgeo_zgeo_1ms_1000_restart_reconstruction.py \
    --config configs/rgeo_zgeo_1ms_1000_restart_reconstruction.json \
    --source-revision "$NR1000_RECON_SOURCE_REVISION" \
    --output "$OUTPUT" \
    --offline
else
  python scripts/rgeo_zgeo_1ms_1000_restart_reconstruction.py \
    --config configs/rgeo_zgeo_1ms_1000_restart_reconstruction.json \
    --source-revision "$NR1000_RECON_SOURCE_REVISION" \
    --output "$OUTPUT"
fi
