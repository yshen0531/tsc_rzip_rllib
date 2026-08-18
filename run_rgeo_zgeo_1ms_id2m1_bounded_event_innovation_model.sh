#!/usr/bin/env bash
set -euo pipefail

PROJECT="${HOME}/tsc_all/tsc_rzip_rllib"
VENV="${HOME}/tsc_all/tsc_simulation/venv_simu"
[[ "${PWD}" == "${PROJECT}" ]] || { printf 'ERROR: run from %s\n' "${PROJECT}" >&2; exit 2; }
[[ -f "${VENV}/bin/activate" ]] || { printf 'ERROR: missing server virtual environment\n' >&2; exit 2; }
source "${VENV}/bin/activate"
export PYTHONPATH="${PROJECT}/scripts:${PROJECT}${PYTHONPATH:+:${PYTHONPATH}}"

command_name="${1:-}"
revision="${ID2M1_SOURCE_REVISION:-}"
output_dir="${ID2M1_OUTPUT_DIR:-}"
config="${PROJECT}/configs/rgeo_zgeo_1ms_id2m1_bounded_event_innovation_model.json"

case "${command_name}" in
  preflight)
    python scripts/rgeo_zgeo_1ms_id2m1_bounded_event_innovation_model.py preflight --config "${config}"
    ;;
  run)
    [[ -n "${revision}" && -n "${output_dir}" ]] || { printf 'ERROR: set ID2M1_SOURCE_REVISION and ID2M1_OUTPUT_DIR\n' >&2; exit 2; }
    python scripts/rgeo_zgeo_1ms_id2m1_bounded_event_innovation_model.py run \
      --config "${config}" --source-revision "${revision}" --output-dir "${output_dir}"
    ;;
  independent)
    [[ -n "${revision}" && -n "${output_dir}" ]] || { printf 'ERROR: set ID2M1_SOURCE_REVISION and ID2M1_OUTPUT_DIR\n' >&2; exit 2; }
    python scripts/rgeo_zgeo_1ms_id2m1_bounded_event_innovation_model_independent.py \
      --config "${config}" --source-revision "${revision}" --output-dir "${output_dir}"
    ;;
  *)
    printf 'usage: %s {preflight|run|independent}\n' "$0" >&2
    exit 2
    ;;
esac
