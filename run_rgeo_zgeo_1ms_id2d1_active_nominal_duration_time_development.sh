#!/usr/bin/env bash
set -euo pipefail

PROJECT="${HOME}/tsc_all/tsc_rzip_rllib"
VENV="${HOME}/tsc_all/tsc_simulation/venv_simu"
: "${ID2D1R1_SOURCE_REVISION:?set ID2D1R1_SOURCE_REVISION to the implementation commit}"
: "${ID2D1R1_OUTPUT_DIR:?set ID2D1R1_OUTPUT_DIR to a new repository-relative directory}"

cd "${PROJECT}"
test "${PWD}" = "${PROJECT}"
test -f "${VENV}/bin/activate"
test ! -e "${ID2D1R1_OUTPUT_DIR}"
source "${VENV}/bin/activate"

set +e
python scripts/rgeo_zgeo_1ms_id2d1_active_nominal_duration_time_development.py run \
  --stage-config configs/rgeo_zgeo_1ms_id2d1r1_active_nominal_duration_time_development.json \
  --source-revision "${ID2D1R1_SOURCE_REVISION}" \
  --output "${ID2D1R1_OUTPUT_DIR}"
primary_status=$?
set -e
if [[ "${primary_status}" -ne 0 && "${primary_status}" -ne 2 ]]; then
  exit "${primary_status}"
fi

python scripts/rgeo_zgeo_1ms_id2d1_active_nominal_duration_time_independent.py \
  --stage-config configs/rgeo_zgeo_1ms_id2d1r1_active_nominal_duration_time_development.json \
  --run-dir "${ID2D1R1_OUTPUT_DIR}" \
  --output "${ID2D1R1_OUTPUT_DIR}/independent_audit.json"

exit "${primary_status}"
