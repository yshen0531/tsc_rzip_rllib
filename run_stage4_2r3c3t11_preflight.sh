#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_2R3C3T11_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
CONFIG="${PROJECT_DIR}/configs/stage4_2r3c3t11_persistent_step_response_preflight_v1.json"
T6_PREFLIGHT="${PROJECT_DIR}/docs/codex/audits/stage4_2r3c3t6_new_direction_preflight_20260731_428a0bd/stage4_2r3c3t6_new_direction_preflight_v1.json"
EIGHT_BASIS_BANK="${PROJECT_DIR}/stage4_2r3c3t3_eight_basis_feasibility/stage4_2r3c3t3_eight_basis_feasibility_20260731_1a75fff/stage4_2r3c3t3_eight_basis_controller_bank_v1.json"
T9_PREFLIGHT="${PROJECT_DIR}/docs/codex/audits/stage4_2r3c3t9_pc3_mixed_interaction_preflight_20260731_cbb970b/stage4_2r3c3t9_pc3_mixed_interaction_preflight_v1.json"
T10_DIR="${PROJECT_DIR}/stage4_2r3c3t10_interaction_feasibility/stage4_2r3c3t10_interaction_aware_feasibility_20260731_125505"
OUTPUT_ROOT="${PROJECT_DIR}/stage4_2r3c3t11_preflights"
STAMP="$(date -u +%Y%m%d_%H%M%S)"
OUTPUT_DIR="${STAGE4_2R3C3T11_OUTPUT_DIR:-${OUTPUT_ROOT}/stage4_2r3c3t11_persistent_step_preflight_${STAMP}}"
OUTPUT="${OUTPUT_DIR}/stage4_2r3c3t11_persistent_step_response_preflight_v1.json"
cd "${PROJECT_DIR}"
test "$PWD" = "${PROJECT_DIR}"
test ! -e "${OUTPUT_DIR}"
mkdir -p "${OUTPUT_DIR}"
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
printf '[Stage4.2R3c3T11 preflight] user=%s host=%s output=%s\n' "$(id -un)" "$(hostname)" "${OUTPUT}"
printf '[Stage4.2R3c3T11 preflight] offline only; no Ray, gotsc, TSC, plant step, or controller.\n'
exec "${PYTHON_BIN}" \
  docs/codex/audit_tools/stage4_2r3c3t11_persistent_step_response_preflight.py \
  --config "${CONFIG}" \
  --t6-preflight "${T6_PREFLIGHT}" \
  --eight-basis-bank "${EIGHT_BASIS_BANK}" \
  --t9-preflight "${T9_PREFLIGHT}" \
  --t10-manifest "${T10_DIR}/stage4_2r3c3t10_manifest_v1.json" \
  --t10-audit "${T10_DIR}/stage4_2r3c3t10_audit_v1.json" \
  --t10-feasibility "${T10_DIR}/stage4_2r3c3t10_feasibility_v1.json" \
  --output "${OUTPUT}"
