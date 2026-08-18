#!/usr/bin/env bash
set -euo pipefail

PROJECT="${HOME}/tsc_all/tsc_rzip_rllib"
VENV="${HOME}/tsc_all/tsc_simulation/venv_simu"
[[ "${PWD}" == "${PROJECT}" ]] || { printf 'ERROR: run from %s\n' "${PROJECT}" >&2; exit 2; }
[[ -f "${VENV}/bin/activate" ]] || { printf 'ERROR: missing server virtual environment\n' >&2; exit 2; }
source "${VENV}/bin/activate"
export PYTHONPATH="${PROJECT}/scripts:${PROJECT}${PYTHONPATH:+:${PYTHONPATH}}"

command_name="${1:-}"
revision="${ID2R0_SOURCE_REVISION:-}"
output_dir="${ID2R0_OUTPUT_DIR:-}"
config="${PROJECT}/configs/rgeo_zgeo_1ms_id2r0_q1r1_decision_audit.json"

case "${command_name}" in
  preflight)
    python - "${config}" <<'PY'
import json
import sys
from pathlib import Path
import rgeo_zgeo_1ms_id2r0_q1r1_decision_audit as r0
stage, qstage, data, qresult = r0.load_stage(Path(sys.argv[1]))
print(json.dumps({
    "config_sha256": r0.CONFIG_SHA256,
    "q1_original_route": qresult["route"],
    "primary_cells": len(data.cells),
    "whole_history_families": len({cell.group_id for cell in data.cells}),
    "new_candidate_count": 0,
    "new_tsc_calls": 0,
    "reset_calls": 0,
    "plant_advances": 0,
}, sort_keys=True))
PY
    ;;
  run)
    [[ -n "${revision}" && -n "${output_dir}" ]] || {
      printf 'ERROR: set ID2R0_SOURCE_REVISION and ID2R0_OUTPUT_DIR\n' >&2
      exit 2
    }
    python scripts/rgeo_zgeo_1ms_id2r0_q1r1_decision_audit.py \
      --config "${config}" --source-revision "${revision}" --output-dir "${output_dir}"
    ;;
  independent)
    [[ -n "${revision}" && -n "${output_dir}" ]] || {
      printf 'ERROR: set ID2R0_SOURCE_REVISION and ID2R0_OUTPUT_DIR\n' >&2
      exit 2
    }
    python scripts/rgeo_zgeo_1ms_id2r0_q1r1_decision_audit_independent.py \
      --config "${config}" --source-revision "${revision}" --output-dir "${output_dir}"
    ;;
  *)
    printf 'usage: %s {preflight|run|independent}\n' "$0" >&2
    exit 2
    ;;
esac
