#!/usr/bin/env bash
set -euo pipefail

PROJECT="${HOME}/tsc_all/tsc_rzip_rllib"
VENV="${HOME}/tsc_all/tsc_simulation/venv_simu"
: "${ID2C1_SOURCE_REVISION:?set ID2C1_SOURCE_REVISION to the implementation commit}"
: "${ID2C1_OUTPUT_DIR:?set ID2C1_OUTPUT_DIR to a new repository-relative directory}"

cd "${PROJECT}"
test "${PWD}" = "${PROJECT}"
test -f "${VENV}/bin/activate"
test ! -e "${ID2C1_OUTPUT_DIR}"
source "${VENV}/bin/activate"

python scripts/rgeo_zgeo_1ms_id2c1_active_nominal_vector_search.py run \
  --stage-config configs/rgeo_zgeo_1ms_id2c1_active_nominal_vector_search.json \
  --source-revision "${ID2C1_SOURCE_REVISION}" \
  --output "${ID2C1_OUTPUT_DIR}"

python scripts/rgeo_zgeo_1ms_id2c1_active_nominal_vector_independent.py \
  --stage-config configs/rgeo_zgeo_1ms_id2c1_active_nominal_vector_search.json \
  --run-dir "${ID2C1_OUTPUT_DIR}" \
  --output "${ID2C1_OUTPUT_DIR}/independent_audit.json"
