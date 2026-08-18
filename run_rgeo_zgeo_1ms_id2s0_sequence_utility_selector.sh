#!/usr/bin/env bash
set -euo pipefail

PROJECT="${HOME}/tsc_all/tsc_rzip_rllib"
VENV="${HOME}/tsc_all/tsc_simulation/venv_simu"
[[ "${PWD}" == "${PROJECT}" ]] || { printf 'ERROR: run from %s\n' "${PROJECT}" >&2; exit 2; }
[[ -f "${VENV}/bin/activate" ]] || { printf 'ERROR: missing server virtual environment\n' >&2; exit 2; }
source "${VENV}/bin/activate"
export PYTHONPATH="${PROJECT}/scripts:${PROJECT}${PYTHONPATH:+:${PYTHONPATH}}"

command_name="${1:-}"
revision="${ID2S0_SOURCE_REVISION:-}"
output_dir="${ID2S0_OUTPUT_DIR:-}"
config="${PROJECT}/configs/rgeo_zgeo_1ms_id2s0_sequence_utility_selector.json"
[[ -n "${revision}" && -n "${output_dir}" ]] || {
  printf 'ERROR: set ID2S0_SOURCE_REVISION and ID2S0_OUTPUT_DIR\n' >&2; exit 2
}

case "${command_name}" in
  run)
    python scripts/rgeo_zgeo_1ms_id2s0_sequence_utility_selector.py \
      --stage-config "${config}" --source-revision "${revision}" \
      --output "${output_dir}/result.json"
    ;;
  independent)
    python scripts/rgeo_zgeo_1ms_id2s0_sequence_utility_selector_independent.py \
      --stage-config "${config}" --source-revision "${revision}" \
      --primary "${output_dir}/result.json" --output "${output_dir}/independent_audit.json"
    ;;
  *) printf 'usage: %s {run|independent}\n' "$0" >&2; exit 2 ;;
esac

