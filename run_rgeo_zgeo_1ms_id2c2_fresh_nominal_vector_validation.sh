#!/usr/bin/env bash
set -euo pipefail

PROJECT="${HOME}/tsc_all/tsc_rzip_rllib"
VENV="${HOME}/tsc_all/tsc_simulation/venv_simu"
: "${ID2C2_SOURCE_REVISION:?set ID2C2_SOURCE_REVISION to the implementation commit}"
: "${ID2C2_OUTPUT_DIR:?set ID2C2_OUTPUT_DIR to a new repository-relative directory}"

cd "${PROJECT}"
test "${PWD}" = "${PROJECT}"
test -f "${VENV}/bin/activate"
test ! -e "${ID2C2_OUTPUT_DIR}"
source "${VENV}/bin/activate"

set +e
python scripts/rgeo_zgeo_1ms_id2c2_fresh_nominal_vector_validation.py run \
  --stage-config configs/rgeo_zgeo_1ms_id2c2_fresh_nominal_vector_validation.json \
  --source-revision "${ID2C2_SOURCE_REVISION}" \
  --output "${ID2C2_OUTPUT_DIR}"
primary_status=$?
set -e
if [[ "${primary_status}" -ne 0 && "${primary_status}" -ne 2 ]]; then
  exit "${primary_status}"
fi

python scripts/rgeo_zgeo_1ms_id2c2_fresh_nominal_vector_independent.py \
  --stage-config configs/rgeo_zgeo_1ms_id2c2_fresh_nominal_vector_validation.json \
  --run-dir "${ID2C2_OUTPUT_DIR}" \
  --output "${ID2C2_OUTPUT_DIR}/independent_audit.json"

exit "${primary_status}"
