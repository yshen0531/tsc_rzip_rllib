#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-$HOME/tsc_all/tsc_rzip_rllib}"
VENV_ROOT="${VENV_ROOT:-$HOME/tsc_all/tsc_simulation/venv_simu}"
SERVER_RUN_ROOT="${ID2Z21_SERVER_RUN_ROOT:-$PROJECT_ROOT}"
SOURCE_REVISION="${ID2Z21_SOURCE_REVISION:?ID2Z21_SOURCE_REVISION is required}"
OUTPUT_PATH="${ID2Z21_OUTPUT_PATH:-$PROJECT_ROOT/id2z21_result.json}"

cd "$PROJECT_ROOT"
test "$PWD" = "$HOME/tsc_all/tsc_rzip_rllib"
test -f "$VENV_ROOT/bin/activate"
source "$VENV_ROOT/bin/activate"

python scripts/rgeo_zgeo_1ms_id2z21_moving_nominal_temporal_contract.py \
  --repo-root "$PROJECT_ROOT" \
  --server-run-root "$SERVER_RUN_ROOT" \
  --source-revision "$SOURCE_REVISION" \
  --output "$OUTPUT_PATH"
