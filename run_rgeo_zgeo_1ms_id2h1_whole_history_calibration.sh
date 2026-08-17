#!/usr/bin/env bash
set -euo pipefail

PROJECT="${HOME}/tsc_all/tsc_rzip_rllib"
VENV="${HOME}/tsc_all/tsc_simulation/venv_simu"
: "${ID2H1_SOURCE_REVISION:?set ID2H1_SOURCE_REVISION to the implementation commit}"
: "${ID2H1_OUTPUT_DIR:?set ID2H1_OUTPUT_DIR to a new repository-relative directory}"

cd "${PROJECT}"
test "${PWD}" = "${PROJECT}"
test -f "${VENV}/bin/activate"
case "${ID2H1_OUTPUT_DIR}" in
  /*|*..*) exit 2 ;;
esac
test ! -e "${ID2H1_OUTPUT_DIR}"
source "${VENV}/bin/activate"

set +e
python scripts/rgeo_zgeo_1ms_id2h1_whole_history_calibration.py run \
  --stage-config configs/rgeo_zgeo_1ms_id2h1_whole_history_calibration.json \
  --source-revision "${ID2H1_SOURCE_REVISION}" \
  --output "${ID2H1_OUTPUT_DIR}"
primary_status=$?
set -e

python scripts/rgeo_zgeo_1ms_id2h1_whole_history_calibration_independent.py raw \
  --stage-config configs/rgeo_zgeo_1ms_id2h1_whole_history_calibration.json \
  --run-dir "${ID2H1_OUTPUT_DIR}" \
  --source-revision "${ID2H1_SOURCE_REVISION}" \
  --output "${ID2H1_OUTPUT_DIR}/independent_raw_audit.json"

if [[ "${primary_status}" -ne 0 ]]; then
  exit "${primary_status}"
fi

python scripts/rgeo_zgeo_1ms_id2h1_whole_history_calibration.py calibrate \
  --stage-config configs/rgeo_zgeo_1ms_id2h1_whole_history_calibration.json \
  --source-revision "${ID2H1_SOURCE_REVISION}" \
  --run-dir "${ID2H1_OUTPUT_DIR}" \
  --output "${ID2H1_OUTPUT_DIR}/calibration_result.json"
calibration_status=$?

python scripts/rgeo_zgeo_1ms_id2h1_whole_history_calibration_independent.py calibration \
  --stage-config configs/rgeo_zgeo_1ms_id2h1_whole_history_calibration.json \
  --run-dir "${ID2H1_OUTPUT_DIR}" \
  --calibration "${ID2H1_OUTPUT_DIR}/calibration_result.json" \
  --source-revision "${ID2H1_SOURCE_REVISION}" \
  --output "${ID2H1_OUTPUT_DIR}/independent_calibration_audit.json"

exit "${calibration_status}"
