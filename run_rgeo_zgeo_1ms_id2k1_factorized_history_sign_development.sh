#!/usr/bin/env bash
set -euo pipefail

PROJECT="${HOME}/tsc_all/tsc_rzip_rllib"
VENV="${HOME}/tsc_all/tsc_simulation/venv_simu"
: "${ID2K1_SOURCE_REVISION:?set ID2K1_SOURCE_REVISION to the implementation commit}"
: "${ID2K1_OUTPUT_DIR:?set ID2K1_OUTPUT_DIR to a new repository-relative directory}"

cd "${PROJECT}"
test "${PWD}" = "${PROJECT}"
test -f "${VENV}/bin/activate"
case "${ID2K1_OUTPUT_DIR}" in
  /*|*..*) exit 2 ;;
esac
test ! -e "${ID2K1_OUTPUT_DIR}"
source "${VENV}/bin/activate"

set +e
python scripts/rgeo_zgeo_1ms_id2k1_factorized_history_sign_development.py run \
  --stage-config configs/rgeo_zgeo_1ms_id2k1_factorized_history_sign_development.json \
  --source-revision "${ID2K1_SOURCE_REVISION}" \
  --output "${ID2K1_OUTPUT_DIR}"
primary_status=$?
set -e

python scripts/rgeo_zgeo_1ms_id2k1_factorized_history_sign_development_independent.py \
  --stage-config configs/rgeo_zgeo_1ms_id2k1_factorized_history_sign_development.json \
  --run-dir "${ID2K1_OUTPUT_DIR}" \
  --source-revision "${ID2K1_SOURCE_REVISION}" \
  --output "${ID2K1_OUTPUT_DIR}/independent_raw_audit.json"

exit "${primary_status}"
