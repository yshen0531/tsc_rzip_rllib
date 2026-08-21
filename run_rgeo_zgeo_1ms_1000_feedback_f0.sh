#!/usr/bin/env bash
set -euo pipefail
MODE="${1:?usage: $0 offline|run|audit}"
PROJECT_ROOT="${NR1000_F0_PROJECT_ROOT:-$HOME/tsc_all/tsc_rzip_rllib}"
OUTPUT="${NR1000_F0_OUTPUT:?NR1000_F0_OUTPUT is required}"
SOURCE_REVISION="${NR1000_F0_SOURCE_REVISION:?NR1000_F0_SOURCE_REVISION is required}"
cd "$PROJECT_ROOT"
test "$PWD" = "$PROJECT_ROOT"
source "$HOME/tsc_all/tsc_simulation/venv_simu/bin/activate"
case "$MODE" in
  offline|run) python scripts/rgeo_zgeo_1ms_1000_feedback_f0.py "$MODE" --config configs/rgeo_zgeo_1ms_1000_feedback_f0.json --source-revision "$SOURCE_REVISION" --output "$OUTPUT" ;;
  audit) python scripts/rgeo_zgeo_1ms_1000_feedback_f0_independent.py --config configs/rgeo_zgeo_1ms_1000_feedback_f0.json --source-revision "$SOURCE_REVISION" --run-dir "$OUTPUT" ;;
  *) exit 2 ;;
esac
