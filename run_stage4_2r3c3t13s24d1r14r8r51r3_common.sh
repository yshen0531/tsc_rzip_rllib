#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${STAGE4_2R3C3T13S24D1R14R8R51R3_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
CONFIG="${STAGE4_2R3C3T13S24D1R14R8R51R3_CONFIG:-${PROJECT_DIR}/configs/stage4_2r3c3t13s24d1r14r8r51r3_single_transport_return_hold_formal_authority_audit.json}"
COMMAND="${STAGE4_2R3C3T13S24D1R14R8R51R3_COMMAND:-primary}"
OUTPUT_ROOT="${STAGE4_2R3C3T13S24D1R14R8R51R3_OUTPUT_ROOT:-${PROJECT_DIR}/stage4_2r3c3t13s24d1r14r8r51r3_runs}"
RUN_NAME="stage4_2r3c3t13s24d1r14r8r51r3_single_transport_return_hold_formal_authority_audit"
R51R2_RUN="${STAGE4_2R3C3T13S24D1R14R8R51R3_R51R2_RUN:-${PROJECT_DIR}/stage4_2r3c3t13s24d1r14r8r51r2_runs/stage4_2r3c3t13s24d1r14r8r51r2_reduced_q0_transport_bridge_whole_pair_causal_model_preflight_20260810_2e96b75_v2}"
R51R1_RUN="${STAGE4_2R3C3T13S24D1R14R8R51R3_R51R1_RUN:-${PROJECT_DIR}/stage4_2r3c3t13s24d1r14r8r51r1_runs/stage4_2r3c3t13s24d1r14r8r51r1_reduced_q0_transport_bridge_q0_gate_integration_sentinel_20260809_1baf670_v1}"
R8R7_RUN="${STAGE4_2R3C3T13S24D1R14R8R51R3_R8R7_RUN:-${PROJECT_DIR}/stage4_2r3c3t13s24d1r14r8r7_runs/stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_sentinel_20260807_d8d231e_v1}"

[[ "${PROJECT_DIR}" == "/home/yangshen0711/tsc_all/tsc_rzip_rllib" ]]
[[ -x "${PYTHON}" ]]
[[ -f "${CONFIG}" ]]
[[ -d "${R51R2_RUN}" ]]
[[ -d "${R51R1_RUN}" ]]
[[ -d "${R8R7_RUN}" ]]
case "${COMMAND}" in
  primary|independent|finalize) ;;
  *) echo "ERROR: unsupported R8R51R3 command ${COMMAND}" >&2; exit 1 ;;
esac

if [[ -n "${STAGE4_2R3C3T13S24D1R14R8R51R3_RUN_DIR:-}" ]]; then
  RUN_DIR="${STAGE4_2R3C3T13S24D1R14R8R51R3_RUN_DIR}"
else
  mkdir -p "${OUTPUT_ROOT}"
  RUN_DIR="${OUTPUT_ROOT}/${RUN_NAME}_$(date -u +%Y%m%d_%H%M%S)"
fi
STAGE_DIR="${RUN_DIR}/${RUN_NAME}"
if [[ "${COMMAND}" == "primary" ]]; then
  [[ ! -e "${STAGE_DIR}" ]]
else
  [[ -f "${STAGE_DIR}/stage_state.json" ]]
fi
mkdir -p "${RUN_DIR}"

export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
cd "${PROJECT_DIR}"
printf '[R8R51R3] user=%s host=%s command=%s run_dir=%s\n' "$(id -un)" "$(hostname)" "${COMMAND}" "${RUN_DIR}"
printf '[R8R51R3] zero new TSC/raw/controller/plant/model/optimization; all sources forbidden learning; not Gate A.\n'

common_args=(
  --config "${CONFIG}"
  --run-dir "${RUN_DIR}"
  --r51r2-run "${R51R2_RUN}"
  --r51r1-run "${R51R1_RUN}"
  --r8r7-run "${R8R7_RUN}"
)
case "${COMMAND}" in
  primary)
    exec "${PYTHON}" -m tsc_rzip_rllib.diagnostics.stage4_2r3c3t13s24d1r14r8r51r3_single_transport_return_hold_formal_authority_audit "${common_args[@]}" --command primary
    ;;
  independent)
    exec "${PYTHON}" docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r51r3_independent_forensics.py "${common_args[@]}"
    ;;
  finalize)
    exec "${PYTHON}" -m tsc_rzip_rllib.diagnostics.stage4_2r3c3t13s24d1r14r8r51r3_single_transport_return_hold_formal_authority_audit "${common_args[@]}" --command finalize
    ;;
esac
