#!/usr/bin/env bash
set -euo pipefail
ROOT="${NR1000_PROJECT_ROOT:-$HOME/tsc_all/tsc_rzip_rllib}"
cd "$ROOT"
: "${NR1000_G2R1_SOURCE_REVISION:?set NR1000_G2R1_SOURCE_REVISION}"
VENV="${NR1000_VENV:-$HOME/tsc_all/tsc_simulation/venv_simu}"
. "$VENV/bin/activate"
MODE="${1:?offline, run, or audit}"
DEST="${2:?missing output}"
CONFIG=configs/rgeo_zgeo_1ms_1000_joint_allocator_authority_g2r1.json
case "$MODE" in
  offline) python scripts/rgeo_zgeo_1ms_1000_joint_allocator_authority_g2r1.py offline --config "$CONFIG" --source-revision "$NR1000_G2R1_SOURCE_REVISION" --output "$DEST" ;;
  run) python scripts/rgeo_zgeo_1ms_1000_joint_allocator_authority_g2r1.py run --config "$CONFIG" --source-revision "$NR1000_G2R1_SOURCE_REVISION" --output "$DEST" ;;
  audit) python scripts/rgeo_zgeo_1ms_1000_joint_allocator_authority_g2r1_independent.py --config "$CONFIG" --source-revision "$NR1000_G2R1_SOURCE_REVISION" --run-dir "$DEST" ;;
  *) echo "unknown mode: $MODE" >&2; exit 2 ;;
esac
