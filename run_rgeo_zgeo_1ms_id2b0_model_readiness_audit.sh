#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${ID2B0_PROJECT_DIR:-$HOME/tsc_all/tsc_rzip_rllib}"
VENV_ACTIVATE="${ID2B0_VENV_ACTIVATE:-$HOME/tsc_all/tsc_simulation/venv_simu/bin/activate}"
SOURCE_REVISION="${ID2B0_SOURCE_REVISION:?ID2B0_SOURCE_REVISION is required}"
ID2A_RUN_DIR="${ID2B0_ID2A_RUN_DIR:-$PROJECT_DIR/rgeo_zgeo_1ms_id2a_runs_20260815_d25ee2a9}"
OUTPUT_DIR="${ID2B0_OUTPUT_DIR:-$PROJECT_DIR/rgeo_zgeo_1ms_id2b0_readiness_${SOURCE_REVISION:0:8}}"

test -d "$PROJECT_DIR"
test -f "$VENV_ACTIVATE"
cd "$PROJECT_DIR"
test "$PWD" = "$PROJECT_DIR"
test -d "$ID2A_RUN_DIR"
test ! -e "$OUTPUT_DIR"

source "$VENV_ACTIVATE"

python scripts/rgeo_zgeo_1ms_id2b0_model_readiness_audit.py \
  --repo-root "$PROJECT_DIR" \
  --config configs/rgeo_zgeo_1ms_id2b0_model_readiness_audit.json \
  --id2a-run-dir "$ID2A_RUN_DIR" \
  --output-dir "$OUTPUT_DIR" \
  --source-revision "$SOURCE_REVISION"

python scripts/rgeo_zgeo_1ms_id2b0_model_readiness_independent.py \
  --repo-root "$PROJECT_DIR" \
  --config configs/rgeo_zgeo_1ms_id2b0_model_readiness_audit.json \
  --id2a-run-dir "$ID2A_RUN_DIR" \
  --output-dir "$OUTPUT_DIR" \
  --source-revision "$SOURCE_REVISION"

printf 'ID2B0_OUTPUT_DIR=%s\n' "$OUTPUT_DIR"
