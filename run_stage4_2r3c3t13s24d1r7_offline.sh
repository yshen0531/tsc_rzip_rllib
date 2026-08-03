#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_2R3C3T13S24D1R7_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
[[ -x "${PYTHON_BIN}" ]] || { echo "ERROR: server virtualenv Python missing" >&2; exit 1; }
OUTPUT="${STAGE4_2R3C3T13S24D1R7_OUTPUT:?set STAGE4_2R3C3T13S24D1R7_OUTPUT to a new directory}"
[[ ! -e "${OUTPUT}" ]] || { echo "ERROR: D1R7 output must be new" >&2; exit 1; }

export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
CONFIG="${PROJECT_DIR}/configs/stage4_2r3c3t13s24d1r7_temporal_basis_substitution_preflight_v1.json"
PRIMARY="${PROJECT_DIR}/docs/codex/audit_tools/stage4_2r3c3t13s24d1r7_temporal_basis_substitution_preflight.py"
INDEPENDENT="${PROJECT_DIR}/docs/codex/audit_tools/stage4_2r3c3t13s24d1r7_independent_forensics.py"

printf '[T13S24D1R7] zero-new-TSC fixed temporal-basis preflight; output=%s\n' "${OUTPUT}"
"${PYTHON_BIN}" "${PRIMARY}" \
  --config "${CONFIG}" --project-root "${PROJECT_DIR}" --output "${OUTPUT}"
"${PYTHON_BIN}" "${INDEPENDENT}" \
  --config "${CONFIG}" --project-root "${PROJECT_DIR}" \
  --primary-output "${OUTPUT}" \
  --output "${OUTPUT}/stage4_2r3c3t13s24d1r7_independent_forensics_v1.json"
printf '[T13S24D1R7] primary and independent recomputation complete; zero plant steps\n'
