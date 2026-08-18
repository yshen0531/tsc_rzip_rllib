#!/usr/bin/env bash
set -euo pipefail

PROJECT="${HOME}/tsc_all/tsc_rzip_rllib"
VENV="${HOME}/tsc_all/tsc_simulation/venv_simu"
[[ "${PWD}" == "${PROJECT}" ]] || { printf 'ERROR: run from %s\n' "${PROJECT}" >&2; exit 2; }
[[ -f "${VENV}/bin/activate" ]] || { printf 'ERROR: missing server virtual environment\n' >&2; exit 2; }
source "${VENV}/bin/activate"
export PYTHONPATH="${PROJECT}:${PROJECT}/scripts${PYTHONPATH:+:${PYTHONPATH}}"

mode="${1:-}"
revision="${ID2N1_SOURCE_REVISION:-}"
output="${ID2N1_OUTPUT_DIR:-}"
config="${PROJECT}/configs/rgeo_zgeo_1ms_id2n1_fresh_calibration_blind_holdout.json"
[[ -n "${revision}" ]] || { printf 'ERROR: set ID2N1_SOURCE_REVISION\n' >&2; exit 2; }
case "${mode}" in
  offline)
    python scripts/rgeo_zgeo_1ms_id2n1_fresh_calibration_blind_holdout.py offline \
      --stage-config "${config}" --source-revision "${revision}"
    ;;
  run)
    [[ -n "${output}" ]] || { printf 'ERROR: set ID2N1_OUTPUT_DIR\n' >&2; exit 2; }
    python scripts/rgeo_zgeo_1ms_id2n1_fresh_calibration_blind_holdout.py run \
      --stage-config "${config}" --source-revision "${revision}" --output "${output}"
    ;;
  independent)
    [[ -n "${output}" ]] || { printf 'ERROR: set ID2N1_OUTPUT_DIR\n' >&2; exit 2; }
    python scripts/rgeo_zgeo_1ms_id2n1_fresh_calibration_blind_holdout_independent.py \
      --stage-config "${config}" --run-dir "${output}" --source-revision "${revision}" \
      --output "${output}/independent_raw_audit.json"
    ;;
  *) printf 'usage: %s {offline|run|independent}\n' "$0" >&2; exit 2 ;;
esac
