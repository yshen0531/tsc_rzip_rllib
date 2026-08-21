#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

: "${NR1000_SOURCE_REVISION:?set NR1000_SOURCE_REVISION to the deployed implementation revision}"
VENV="${NR1000_VENV:-$HOME/tsc_all/tsc_simulation/venv_simu}"
. "$VENV/bin/activate"

CONFIG="$ROOT/configs/rgeo_zgeo_1ms_1000_nr1_source_interface.json"
MODE="${1:?usage: $0 offline OUTPUT_JSON | run OUTPUT_DIR | audit RUN_DIR}"
DEST="${2:?missing output path}"

case "$MODE" in
  offline)
    python scripts/rgeo_zgeo_1ms_nr1_qualification.py offline \
      --config "$CONFIG" --source-revision "$NR1000_SOURCE_REVISION" \
      --output "$DEST"
    ;;
  run)
    python scripts/rgeo_zgeo_1ms_nr1_qualification.py run \
      --config "$CONFIG" --source-revision "$NR1000_SOURCE_REVISION" \
      --output "$DEST"
    ;;
  audit)
    python scripts/rgeo_zgeo_1ms_nr1_independent.py \
      --config "$CONFIG" --source-revision "$NR1000_SOURCE_REVISION" \
      --run-dir "$DEST"
    ;;
  *)
    echo "unknown mode: $MODE" >&2
    exit 2
    ;;
esac
