#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${PROJECT_DIR}/scripts/stage4_2r3c3t13s5_shell_common.sh"
stage4_2r3c3t13s5_validate_common
SOURCE_R3B="$(stage4_2r3c3t13s5_find_source_r3b)"
SOURCE_R3C3="$(stage4_2r3c3t13s5_find_source_r3c3)"
SOURCE_BANK="$(stage4_2r3c3t13s5_find_source_bank)"
SOURCE_T1="$(stage4_2r3c3t13s5_find_source_t1)"
SOURCE_T1_AUDIT="$(stage4_2r3c3t13s5_find_source_t1_audit)"
SOURCE_T3_BANK="$(stage4_2r3c3t13s5_find_t3_controller_bank)"
RUN_DIR="${STAGE4_2R3C3T13S5_RUN_DIR:-$(stage4_2r3c3t13s5_new_run_dir)}"
if [[ "${STAGE4_2R3C3T13S5_RESUME}" == 1 ]]; then
  [[ -f "${RUN_DIR}/stage4_2r3c3t13s5_state.json" ]] || { echo "ERROR: resume state missing" >&2; exit 1; }
else
  [[ ! -e "${RUN_DIR}" || -z "$(find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]] || { echo "ERROR: fresh run directory not empty" >&2; exit 1; }
fi
mkdir -p "${RUN_DIR}"
stage4_2r3c3t13s5_export_runtime
printf '[T13S5] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[T13S5] run_dir=%s command=%s backend=%s resume=%s workers=%s\n' "${RUN_DIR}" "${STAGE4_2R3C3T13S5_COMMAND}" "${STAGE4_2R3C3T13S5_BACKEND}" "${STAGE4_2R3C3T13S5_RESUME}" "${STAGE4_2R3C3T13S5_WORKERS}"
printf '[T13S5] 4 formal-end baselines + 64 lattice-native Card15 probes = 68 real TSC rollouts.\n'
printf '[T13S5] Development raw is opened and model-hashed before blind holdout raw.\n'
cd "${PROJECT_DIR}"
args=(
  --config "${STAGE4_2R3C3T13S5_CONFIG}"
  --source-stage4-2r3b-run "${SOURCE_R3B}"
  --source-stage4-2r3c3-run "${SOURCE_R3C3}"
  --source-stage4-2r3c3-bank-dir "${SOURCE_BANK}"
  --source-stage4-2r3c3t1-run "${SOURCE_T1}"
  --source-stage4-2r3c3t1-audit-dir "${SOURCE_T1_AUDIT}"
  --source-stage4-2r3c3t3-controller-bank "${SOURCE_T3_BANK}"
  --run-dir "${RUN_DIR}"
  --command "${STAGE4_2R3C3T13S5_COMMAND}"
  --backend "${STAGE4_2R3C3T13S5_BACKEND}"
)
[[ "${STAGE4_2R3C3T13S5_RESUME}" == 1 ]] && args+=(--resume)
exec "${STAGE4_2R3C3T13S5_PYTHON}" scripts/stage4_2r3c3t13s5_lattice_native_split_holdout.py "${args[@]}"
