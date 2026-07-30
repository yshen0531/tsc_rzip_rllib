#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage4_2r3c3t1_shell_common.sh
source "${PROJECT_DIR}/scripts/stage4_2r3c3t1_shell_common.sh"
stage4_2r3c3t1_validate_common
SOURCE_R3B="$(stage4_2r3c3t1_find_source_r3b)" || exit 1
SOURCE_R3C3="$(stage4_2r3c3t1_find_source_r3c3)" || exit 1
SOURCE_BANK="$(stage4_2r3c3t1_find_source_bank)" || exit 1
if [[ -n "${STAGE4_2R3C3T1_RUN_DIR:-}" ]]; then
  RUN_DIR="${STAGE4_2R3C3T1_RUN_DIR}"
else
  RUN_DIR="$(stage4_2r3c3t1_new_run_dir)"
fi
if [[ "${STAGE4_2R3C3T1_RESUME}" == "1" ]]; then
  [[ -f "${RUN_DIR}/stage4_2r3c3t1_state.json" ]] || {
    echo "ERROR: resume state missing: ${RUN_DIR}/stage4_2r3c3t1_state.json" >&2
    exit 1
  }
else
  [[ ! -e "${RUN_DIR}" || -z "$(find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]] || {
    echo "ERROR: fresh run directory is not empty: ${RUN_DIR}" >&2
    exit 1
  }
fi
mkdir -p "${RUN_DIR}"
stage4_2r3c3t1_export_runtime
printf '[Stage4.2R3c3T1] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[Stage4.2R3c3T1] source_stage4_2r3b_run=%s\n' "${SOURCE_R3B}"
printf '[Stage4.2R3c3T1] source_stage4_2r3c3_run=%s\n' "${SOURCE_R3C3}"
printf '[Stage4.2R3c3T1] source_stage4_2r3c3_bank=%s\n' "${SOURCE_BANK}"
printf '[Stage4.2R3c3T1] run_dir=%s\n' "${RUN_DIR}"
printf '[Stage4.2R3c3T1] command=%s backend=%s resume=%s workers=%s\n' \
  "${STAGE4_2R3C3T1_COMMAND}" "${STAGE4_2R3C3T1_BACKEND}" \
  "${STAGE4_2R3C3T1_RESUME}" "${STAGE4_2R3C3T1_WORKERS}"
printf '[Stage4.2R3c3T1] 128 signed long-separation probes are zero-net and identification-only.\n'
printf '[Stage4.2R3c3T1] Formal timing is unchanged; tracking is diagnostic, not this identification gate.\n'
printf '[Stage4.2R3c3T1] Probe trajectories are forbidden expert data; BC, DAgger and residual RL remain forbidden.\n'
cd "${PROJECT_DIR}"
args=(
  --config "${STAGE4_2R3C3T1_CONFIG}"
  --source-stage4-2r3b-run "${SOURCE_R3B}"
  --source-stage4-2r3c3-run "${SOURCE_R3C3}"
  --source-stage4-2r3c3-bank-dir "${SOURCE_BANK}"
  --run-dir "${RUN_DIR}"
  --command "${STAGE4_2R3C3T1_COMMAND}"
  --backend "${STAGE4_2R3C3T1_BACKEND}"
)
[[ "${STAGE4_2R3C3T1_RESUME}" == "1" ]] && args+=(--resume)
exec "${STAGE4_2R3C3T1_PYTHON}" \
  scripts/stage4_2r3c3t1_long_separation_zero_net_transport_identification.py \
  "${args[@]}"
