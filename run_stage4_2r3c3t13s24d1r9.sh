#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_2R3C3T13S24D1R9_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
OUTPUT_ROOT="${STAGE4_2R3C3T13S24D1R9_OUTPUT_ROOT:-${PROJECT_DIR}/stage4_2r3c3t13s24d1r9_audits}"
OUTPUT_DIR="${STAGE4_2R3C3T13S24D1R9_OUTPUT_DIR:-${OUTPUT_ROOT}/stage4_2r3c3t13s24d1r9_central_row_replacement_preflight_$(date -u +%Y%m%d_%H%M%S)}"
CONFIG="${PROJECT_DIR}/configs/stage4_2r3c3t13s24d1r9_central_row_replacement_preflight_v1.json"

[[ -x "${PYTHON_BIN}" ]] || { echo "ERROR: server virtualenv Python missing" >&2; exit 1; }
[[ -f "${CONFIG}" ]] || { echo "ERROR: D1R9 config missing" >&2; exit 1; }
[[ ! -e "${OUTPUT_DIR}" ]] || { echo "ERROR: D1R9 output must be new" >&2; exit 1; }
mkdir -p "${OUTPUT_ROOT}"
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
cd "${PROJECT_DIR}"
"${PYTHON_BIN}" docs/codex/audit_tools/stage4_2r3c3t13s24d1r9_central_row_replacement_preflight.py \
  --config "${CONFIG}" --project "${PROJECT_DIR}" --output "${OUTPUT_DIR}"
"${PYTHON_BIN}" docs/codex/audit_tools/stage4_2r3c3t13s24d1r9_independent_forensics.py \
  --config "${CONFIG}" --project "${PROJECT_DIR}" --primary-dir "${OUTPUT_DIR}" \
  --output "${OUTPUT_DIR}/stage4_2r3c3t13s24d1r9_independent_forensics_v1.json"
printf '[T13S24D1R9] output=%s zero TSC/plant steps\n' "${OUTPUT_DIR}"

