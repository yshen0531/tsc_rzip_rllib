#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage4_2r3c3t13s1_shell_common.sh
source "${PROJECT_DIR}/scripts/stage4_2r3c3t13s1_shell_common.sh"
stage4_2r3c3t13s1_validate_common
SOURCE_R3B="$(stage4_2r3c3t13s1_find_source_r3b)" || exit 1
SOURCE_R3C3="$(stage4_2r3c3t13s1_find_source_r3c3)" || exit 1
SOURCE_BANK="$(stage4_2r3c3t13s1_find_source_bank)" || exit 1
SOURCE_T1="$(stage4_2r3c3t13s1_find_source_t1)" || exit 1
SOURCE_T1_AUDIT="$(stage4_2r3c3t13s1_find_source_t1_audit)" || exit 1
SOURCE_T3_BANK="$(stage4_2r3c3t13s1_find_t3_controller_bank)" || exit 1
if [[ -n "${STAGE4_2R3C3T13S1_RUN_DIR:-}" ]]; then
  RUN_DIR="${STAGE4_2R3C3T13S1_RUN_DIR}"
else
  RUN_DIR="$(stage4_2r3c3t13s1_new_run_dir)"
fi
if [[ "${STAGE4_2R3C3T13S1_RESUME}" == "1" ]]; then
  [[ -f "${RUN_DIR}/stage4_2r3c3t13s1_state.json" ]] || {
    echo "ERROR: resume state missing: ${RUN_DIR}/stage4_2r3c3t13s1_state.json" >&2
    exit 1
  }
else
  [[ ! -e "${RUN_DIR}" || -z "$(find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]] || {
    echo "ERROR: fresh run directory is not empty: ${RUN_DIR}" >&2
    exit 1
  }
fi
mkdir -p "${RUN_DIR}"
stage4_2r3c3t13s1_export_runtime
printf '[Stage4.2R3c3T13S1] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[Stage4.2R3c3T13S1] source_r3b=%s\nsource_r3c3=%s\nsource_bank=%s\nsource_t1=%s\nsource_t1_audit=%s\nsource_t3_bank=%s\n' \
  "${SOURCE_R3B}" "${SOURCE_R3C3}" "${SOURCE_BANK}" "${SOURCE_T1}" "${SOURCE_T1_AUDIT}" "${SOURCE_T3_BANK}"
printf '[Stage4.2R3c3T13S1] run_dir=%s command=%s backend=%s resume=%s workers=%s\n' \
  "${RUN_DIR}" "${STAGE4_2R3C3T13S1_COMMAND}" "${STAGE4_2R3C3T13S1_BACKEND}" \
  "${STAGE4_2R3C3T13S1_RESUME}" "${STAGE4_2R3C3T13S1_WORKERS}"
printf '[Stage4.2R3c3T13S1] 4 fresh baselines + 48 adjacent inverse signed probes; 52 total.\n'
printf '[Stage4.2R3c3T13S1] Formal 250/270 and 350/370 ms timing is unchanged; 500 ms is identification-only.\n'
cd "${PROJECT_DIR}"
args=(
  --config "${STAGE4_2R3C3T13S1_CONFIG}"
  --source-stage4-2r3b-run "${SOURCE_R3B}"
  --source-stage4-2r3c3-run "${SOURCE_R3C3}"
  --source-stage4-2r3c3-bank-dir "${SOURCE_BANK}"
  --source-stage4-2r3c3t1-run "${SOURCE_T1}"
  --source-stage4-2r3c3t1-audit-dir "${SOURCE_T1_AUDIT}"
  --source-stage4-2r3c3t3-controller-bank "${SOURCE_T3_BANK}"
  --run-dir "${RUN_DIR}"
  --command "${STAGE4_2R3C3T13S1_COMMAND}"
  --backend "${STAGE4_2R3C3T13S1_BACKEND}"
)
[[ "${STAGE4_2R3C3T13S1_RESUME}" == "1" ]] && args+=(--resume)
exec "${STAGE4_2R3C3T13S1_PYTHON}" \
  scripts/stage4_2r3c3t13s1_minimal_transition_sentinel.py "${args[@]}"
