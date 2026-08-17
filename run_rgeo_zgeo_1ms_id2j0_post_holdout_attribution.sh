#!/usr/bin/env bash
set -euo pipefail

PROJECT="${HOME}/tsc_all/tsc_rzip_rllib"
VENV="${HOME}/tsc_all/tsc_simulation/venv_simu"
: "${ID2J0_SOURCE_REVISION:?set ID2J0_SOURCE_REVISION to the implementation commit}"
: "${ID2J0_OUTPUT_DIR:?set ID2J0_OUTPUT_DIR to a new repository-relative directory}"

cd "${PROJECT}"
test "${PWD}" = "${PROJECT}"
test -f "${VENV}/bin/activate"
case "${ID2J0_OUTPUT_DIR}" in
  /*|*..*) exit 2 ;;
esac
test ! -e "${ID2J0_OUTPUT_DIR}"
source "${VENV}/bin/activate"

set +e
python scripts/rgeo_zgeo_1ms_id2j0_post_holdout_attribution.py run \
  --stage-config configs/rgeo_zgeo_1ms_id2j0_post_holdout_attribution.json \
  --source-revision "${ID2J0_SOURCE_REVISION}" \
  --output "${ID2J0_OUTPUT_DIR}"
run_status=$?
set -e

python scripts/rgeo_zgeo_1ms_id2j0_post_holdout_attribution_independent.py raw \
  --stage-config configs/rgeo_zgeo_1ms_id2j0_post_holdout_attribution.json \
  --run-dir "${ID2J0_OUTPUT_DIR}" \
  --source-revision "${ID2J0_SOURCE_REVISION}" \
  --output "${ID2J0_OUTPUT_DIR}/independent_raw_audit.json"

if [[ "${run_status}" -ne 0 ]]; then
  exit "${run_status}"
fi

set +e
python scripts/rgeo_zgeo_1ms_id2j0_post_holdout_attribution.py attribute \
  --stage-config configs/rgeo_zgeo_1ms_id2j0_post_holdout_attribution.json \
  --source-revision "${ID2J0_SOURCE_REVISION}" \
  --run-dir "${ID2J0_OUTPUT_DIR}" \
  --output "${ID2J0_OUTPUT_DIR}/attribution_result.json"
attribution_status=$?
set -e

python scripts/rgeo_zgeo_1ms_id2j0_post_holdout_attribution_independent.py attribution \
  --stage-config configs/rgeo_zgeo_1ms_id2j0_post_holdout_attribution.json \
  --run-dir "${ID2J0_OUTPUT_DIR}" \
  --source-revision "${ID2J0_SOURCE_REVISION}" \
  --attribution "${ID2J0_OUTPUT_DIR}/attribution_result.json" \
  --recompute "${ID2J0_OUTPUT_DIR}/independent_attribution_recompute.json" \
  --output "${ID2J0_OUTPUT_DIR}/independent_attribution_audit.json"

exit "${attribution_status}"
