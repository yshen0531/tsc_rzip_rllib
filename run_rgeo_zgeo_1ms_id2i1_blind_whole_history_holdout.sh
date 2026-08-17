#!/usr/bin/env bash
set -euo pipefail

PROJECT="${HOME}/tsc_all/tsc_rzip_rllib"
VENV="${HOME}/tsc_all/tsc_simulation/venv_simu"
: "${ID2I1_SOURCE_REVISION:?set ID2I1_SOURCE_REVISION to the implementation commit}"
: "${ID2I1_OUTPUT_DIR:?set ID2I1_OUTPUT_DIR to a new repository-relative directory}"

cd "${PROJECT}"
test "${PWD}" = "${PROJECT}"
test -f "${VENV}/bin/activate"
case "${ID2I1_OUTPUT_DIR}" in
  /*|*..*) exit 2 ;;
esac
test ! -e "${ID2I1_OUTPUT_DIR}"
source "${VENV}/bin/activate"

set +e
python scripts/rgeo_zgeo_1ms_id2i1_blind_whole_history_holdout.py run \
  --stage-config configs/rgeo_zgeo_1ms_id2i1_blind_whole_history_holdout.json \
  --source-revision "${ID2I1_SOURCE_REVISION}" \
  --output "${ID2I1_OUTPUT_DIR}"
primary_status=$?
set -e

python scripts/rgeo_zgeo_1ms_id2i1_blind_whole_history_holdout_independent.py raw \
  --stage-config configs/rgeo_zgeo_1ms_id2i1_blind_whole_history_holdout.json \
  --run-dir "${ID2I1_OUTPUT_DIR}" \
  --source-revision "${ID2I1_SOURCE_REVISION}" \
  --output "${ID2I1_OUTPUT_DIR}/independent_raw_audit.json"

if [[ "${primary_status}" -ne 0 ]]; then
  exit "${primary_status}"
fi

set +e
python scripts/rgeo_zgeo_1ms_id2i1_blind_whole_history_holdout.py evaluate \
  --stage-config configs/rgeo_zgeo_1ms_id2i1_blind_whole_history_holdout.json \
  --source-revision "${ID2I1_SOURCE_REVISION}" \
  --run-dir "${ID2I1_OUTPUT_DIR}" \
  --output "${ID2I1_OUTPUT_DIR}/evaluation_result.json"
evaluation_status=$?
set -e

python scripts/rgeo_zgeo_1ms_id2i1_blind_whole_history_holdout_independent.py evaluation \
  --stage-config configs/rgeo_zgeo_1ms_id2i1_blind_whole_history_holdout.json \
  --run-dir "${ID2I1_OUTPUT_DIR}" \
  --evaluation "${ID2I1_OUTPUT_DIR}/evaluation_result.json" \
  --source-revision "${ID2I1_SOURCE_REVISION}" \
  --output "${ID2I1_OUTPUT_DIR}/independent_evaluation_audit.json"

exit "${evaluation_status}"
