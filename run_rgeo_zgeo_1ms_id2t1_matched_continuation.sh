#!/usr/bin/env bash
set -euo pipefail

PROJECT="${HOME}/tsc_all/tsc_rzip_rllib"
VENV="${HOME}/tsc_all/tsc_simulation/venv_simu"
[[ "${PWD}" == "${PROJECT}" ]] || { printf 'ERROR: run from %s\n' "${PROJECT}" >&2; exit 2; }
[[ -f "${VENV}/bin/activate" ]] || { printf 'ERROR: missing server virtual environment\n' >&2; exit 2; }
source "${VENV}/bin/activate"
export PYTHONPATH="${PROJECT}/scripts:${PROJECT}${PYTHONPATH:+:${PYTHONPATH}}"

command_name="${1:-}"
revision="${ID2T1_SOURCE_REVISION:-}"
output_dir="${ID2T1_OUTPUT_DIR:-}"
config="${PROJECT}/configs/rgeo_zgeo_1ms_id2t1_matched_continuation.json"
[[ -n "${revision}" && -n "${output_dir}" ]] || {
  printf 'ERROR: set ID2T1_SOURCE_REVISION and ID2T1_OUTPUT_DIR\n' >&2; exit 2
}

case "${command_name}" in
  offline)
    python scripts/rgeo_zgeo_1ms_id2t1_matched_continuation.py offline \
      --stage-config "${config}" --source-revision "${revision}"
    ;;
  run)
    python scripts/rgeo_zgeo_1ms_id2t1_matched_continuation.py run \
      --stage-config "${config}" --source-revision "${revision}" --output "${output_dir}"
    ;;
  independent)
    python scripts/rgeo_zgeo_1ms_id2t1_matched_continuation_independent.py \
      --stage-config "${config}" --source-revision "${revision}" \
      --run-dir "${output_dir}" --output "${output_dir}/independent_raw_audit.json"
    ;;
  *) printf 'usage: %s {offline|run|independent}\n' "$0" >&2; exit 2 ;;
esac
