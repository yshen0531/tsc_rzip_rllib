#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage2_1_shell_common.sh
source "${SCRIPT_DIR}/scripts/stage2_1_shell_common.sh"
stage21_project_init
stage21_find_python
export STAGE2_1_WORKERS="${STAGE2_1_WORKERS:-15}"
stage21_runtime_env
stage21_resolve_existing_run
stage21_sources_from_existing_run "${STAGE2_1_RUN_DIR}"
stage21_detect_source_stage2
stage21_detect_source_stage1

CONFIG="${STAGE2_1_CONFIG:-${PROJECT_DIR}/configs/stage2_1_svd3_dual_archive_tail_cem_100ms.json}"
CONFIG="$(stage21_abspath "${CONFIG}")"
[[ -f "${CONFIG}" ]] || stage21_die "Stage2.1 config not found: ${CONFIG}"

cleanup_on_exit() {
  local status=$?
  trap - EXIT
  set +e
  stage21_ray_stop
  stage21_cleanup_runtime
  exit "${status}"
}
trap cleanup_on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

stage21_ray_stop
stage21_cleanup_runtime
mkdir -p "${TMPDIR}" "${STAGE2_TSC_RUN_ROOT}"

"${PYTHON_BIN}" -u "${PROJECT_DIR}/scripts/stage2_1_trajectory_optimization.py" confirm \
  --config "${CONFIG}" \
  --source-run "${SOURCE_STAGE1_1_RUN}" \
  --source-stage2-run "${SOURCE_STAGE2_RUN}" \
  --run-dir "${STAGE2_1_RUN_DIR}" \
  --backend ray

"${PYTHON_BIN}" -u "${PROJECT_DIR}/scripts/stage2_1_trajectory_optimization.py" analyze \
  --config "${CONFIG}" \
  --source-run "${SOURCE_STAGE1_1_RUN}" \
  --source-stage2-run "${SOURCE_STAGE2_RUN}" \
  --run-dir "${STAGE2_1_RUN_DIR}" \
  --backend serial
