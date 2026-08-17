#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

: "${ID2L1_SOURCE_REVISION:?set ID2L1_SOURCE_REVISION to the deployed implementation revision}"
: "${ID2L1_OUTPUT_DIR:?set ID2L1_OUTPUT_DIR to a fresh repository-relative output directory}"

source /home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/activate

python scripts/rgeo_zgeo_1ms_id2l1_structured_history_model.py \
  --stage-config configs/rgeo_zgeo_1ms_id2l1_structured_history_model_comparison.json \
  --source-revision "$ID2L1_SOURCE_REVISION" \
  --preflight

set +e
python scripts/rgeo_zgeo_1ms_id2l1_structured_history_model.py \
  --stage-config configs/rgeo_zgeo_1ms_id2l1_structured_history_model_comparison.json \
  --source-revision "$ID2L1_SOURCE_REVISION" \
  --output-dir "$ID2L1_OUTPUT_DIR"
PRIMARY_RC=$?
set -e

if [[ "$PRIMARY_RC" -ne 0 && "$PRIMARY_RC" -ne 2 ]]; then
  exit "$PRIMARY_RC"
fi

python scripts/rgeo_zgeo_1ms_id2l1_structured_history_model_independent.py \
  --stage-config configs/rgeo_zgeo_1ms_id2l1_structured_history_model_comparison.json \
  --primary "$ID2L1_OUTPUT_DIR/result.json" \
  --source-revision "$ID2L1_SOURCE_REVISION" \
  --output "$ID2L1_OUTPUT_DIR/independent_audit.json"

exit "$PRIMARY_RC"
