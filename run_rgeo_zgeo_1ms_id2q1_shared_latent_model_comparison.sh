#!/usr/bin/env bash
set -euo pipefail

PROJECT="${HOME}/tsc_all/tsc_rzip_rllib"
VENV="${HOME}/tsc_all/tsc_simulation/venv_simu"
[[ "${PWD}" == "${PROJECT}" ]] || { printf 'ERROR: run from %s\n' "${PROJECT}" >&2; exit 2; }
[[ -f "${VENV}/bin/activate" ]] || { printf 'ERROR: missing server virtual environment\n' >&2; exit 2; }
source "${VENV}/bin/activate"
export PYTHONPATH="${PROJECT}/scripts:${PROJECT}${PYTHONPATH:+:${PYTHONPATH}}"

command_name="${1:-}"
revision="${ID2Q1_SOURCE_REVISION:-}"
output_dir="${ID2Q1_OUTPUT_DIR:-}"
config="${PROJECT}/configs/rgeo_zgeo_1ms_id2q1_shared_latent_model_comparison.json"

case "${command_name}" in
  preflight)
    python - "${config}" <<'PY'
import json
import sys
from pathlib import Path
import rgeo_zgeo_1ms_id2q1_shared_latent_model_comparison as q1
stage = q1.load_stage(Path(sys.argv[1]))
data = q1.load_dataset(stage)
print(json.dumps({
    "config_sha256": q1.CONFIG_SHA256,
    "primary_fit_cells": len(data.cells),
    "whole_history_families": len({cell.group_id for cell in data.cells}),
    "new_tsc_calls": 0,
    "reset_calls": 0,
    "plant_advances": 0,
}, sort_keys=True))
PY
    ;;
  run)
    [[ -n "${revision}" && -n "${output_dir}" ]] || { printf 'ERROR: set ID2Q1_SOURCE_REVISION and ID2Q1_OUTPUT_DIR\n' >&2; exit 2; }
    python scripts/rgeo_zgeo_1ms_id2q1_shared_latent_model_comparison.py \
      --config "${config}" --source-revision "${revision}" --output-dir "${output_dir}"
    ;;
  independent)
    [[ -n "${revision}" && -n "${output_dir}" ]] || { printf 'ERROR: set ID2Q1_SOURCE_REVISION and ID2Q1_OUTPUT_DIR\n' >&2; exit 2; }
    python scripts/rgeo_zgeo_1ms_id2q1_shared_latent_model_independent.py \
      --config "${config}" --source-revision "${revision}" --output-dir "${output_dir}"
    ;;
  *)
    printf 'usage: %s {preflight|run|independent}\n' "$0" >&2
    exit 2
    ;;
esac
