#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${ID2E1_PROJECT_ROOT:-/home/yangshen0711/tsc_all/tsc_rzip_rllib}"
VENV_ROOT="${ID2E1_VENV_ROOT:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu}"
SOURCE_REVISION="${ID2E1_SOURCE_REVISION:?set ID2E1_SOURCE_REVISION to the full implementation commit}"
DEVELOPMENT_RUN="${ID2E1_DEVELOPMENT_RUN_DIR:-$PROJECT_ROOT/rgeo_zgeo_1ms_id2d1r1_runs_20260817_3e5b28b3}"
EVALUATOR_RUN="${ID2E1_EVALUATOR_RUN_DIR:-$PROJECT_ROOT/rgeo_zgeo_1ms_id2c2_runs_20260817_58f24fc0}"
OUTPUT_DIR="${ID2E1_OUTPUT_DIR:-$PROJECT_ROOT/rgeo_zgeo_1ms_id2e1_models_${SOURCE_REVISION:0:8}}"

test "$PROJECT_ROOT" = "/home/yangshen0711/tsc_all/tsc_rzip_rllib"
test -d "$PROJECT_ROOT"
test -f "$VENV_ROOT/bin/activate"
test -d "$DEVELOPMENT_RUN"
test -d "$EVALUATOR_RUN"
test ! -e "$OUTPUT_DIR"
[[ "$SOURCE_REVISION" =~ ^[0-9a-f]{40}$ ]]

cd "$PROJECT_ROOT"
source "$VENV_ROOT/bin/activate"

python scripts/rgeo_zgeo_1ms_id2e1_structured_active_nominal_model.py \
  --repo-root "$PROJECT_ROOT" \
  --development-run-dir "$DEVELOPMENT_RUN" \
  --evaluator-run-dir "$EVALUATOR_RUN" \
  --output-dir "$OUTPUT_DIR" \
  --source-revision "$SOURCE_REVISION"

python scripts/rgeo_zgeo_1ms_id2e1_structured_active_nominal_model_independent.py \
  --repo-root "$PROJECT_ROOT" \
  --development-run-dir "$DEVELOPMENT_RUN" \
  --evaluator-run-dir "$EVALUATOR_RUN" \
  --model-dir "$OUTPUT_DIR" \
  --output "$OUTPUT_DIR/independent_audit.json"

printf 'ID2E1_OUTPUT_DIR=%s\n' "$OUTPUT_DIR"
