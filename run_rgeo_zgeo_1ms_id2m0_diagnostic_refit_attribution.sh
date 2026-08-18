#!/usr/bin/env bash
set -euo pipefail

PROJECT="${HOME}/tsc_all/tsc_rzip_rllib"
VENV="${HOME}/tsc_all/tsc_simulation/venv_simu"

if [[ "${PWD}" != "${PROJECT}" ]]; then
  printf 'ERROR: run from %s\n' "${PROJECT}" >&2
  exit 2
fi
if [[ ! -f "${VENV}/bin/activate" ]]; then
  printf 'ERROR: missing server virtual environment\n' >&2
  exit 2
fi

source "${VENV}/bin/activate"
export PYTHONPATH="${PROJECT}/scripts:${PROJECT}${PYTHONPATH:+:${PYTHONPATH}}"

command_name="${1:-}"
revision="${ID2M0_SOURCE_REVISION:-}"
output_dir="${ID2M0_OUTPUT_DIR:-}"
config="${PROJECT}/configs/rgeo_zgeo_1ms_id2m0_diagnostic_refit_attribution.json"

case "${command_name}" in
  preflight)
    python scripts/rgeo_zgeo_1ms_id2m0_diagnostic_refit_attribution.py preflight --config "${config}"
    ;;
  run)
    [[ -n "${revision}" && -n "${output_dir}" ]] || { printf 'ERROR: set ID2M0_SOURCE_REVISION and ID2M0_OUTPUT_DIR\n' >&2; exit 2; }
    python scripts/rgeo_zgeo_1ms_id2m0_diagnostic_refit_attribution.py run \
      --config "${config}" --source-revision "${revision}" --output-dir "${output_dir}"
    ;;
  independent)
    [[ -n "${revision}" && -n "${output_dir}" ]] || { printf 'ERROR: set ID2M0_SOURCE_REVISION and ID2M0_OUTPUT_DIR\n' >&2; exit 2; }
    python scripts/rgeo_zgeo_1ms_id2m0_diagnostic_refit_attribution_independent.py \
      --config "${config}" --source-revision "${revision}" --output-dir "${output_dir}"
    ;;
  all)
    [[ -n "${revision}" && -n "${output_dir}" ]] || { printf 'ERROR: set ID2M0_SOURCE_REVISION and ID2M0_OUTPUT_DIR\n' >&2; exit 2; }
    "$0" preflight
    "$0" run
    "$0" independent
    ;;
  *)
    printf 'usage: %s {preflight|run|independent|all}\n' "$0" >&2
    exit 2
    ;;
esac
