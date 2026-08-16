#!/usr/bin/env bash
set -euo pipefail

PROJECT="${HOME}/tsc_all/tsc_rzip_rllib"
VENV="${HOME}/tsc_all/tsc_simulation/venv_simu"
: "${ID2C0_SOURCE_REVISION:?set ID2C0_SOURCE_REVISION to the implementation commit}"
: "${ID2C0_OUTPUT_DIR:?set ID2C0_OUTPUT_DIR to a new repository-relative directory}"

cd "${PROJECT}"
test "${PWD}" = "${PROJECT}"
test -f "${VENV}/bin/activate"
test ! -e "${ID2C0_OUTPUT_DIR}"
source "${VENV}/bin/activate"

python scripts/rgeo_zgeo_1ms_id2c0_control_relevance_audit.py \
  --config configs/rgeo_zgeo_1ms_id2c0_control_relevance_audit.json \
  --id2a-run-dir rgeo_zgeo_1ms_id2a_runs_20260815_d25ee2a9 \
  --output "${ID2C0_OUTPUT_DIR}/result.json" \
  --source-revision "${ID2C0_SOURCE_REVISION}"

python scripts/rgeo_zgeo_1ms_id2c0_control_relevance_independent.py \
  --config configs/rgeo_zgeo_1ms_id2c0_control_relevance_audit.json \
  --id2a-run-dir rgeo_zgeo_1ms_id2a_runs_20260815_d25ee2a9 \
  --primary "${ID2C0_OUTPUT_DIR}/result.json" \
  --output "${ID2C0_OUTPUT_DIR}/independent_audit.json"
