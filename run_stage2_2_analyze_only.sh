#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage2_2_shell_common.sh
source "${SCRIPT_DIR}/scripts/stage2_2_shell_common.sh"
stage22_project_init
stage22_find_python
stage22_resolve_existing_run
stage22_sources_from_existing_run "${STAGE2_2_RUN_DIR}"
stage22_detect_source_stage21
stage22_detect_derived_sources
CONFIG="${STAGE2_2_CONFIG:-${PROJECT_DIR}/configs/stage2_2_svd3_corner_feasibility_100ms.json}"
CONFIG="$(stage22_abspath "${CONFIG}")"
[[ -f "${CONFIG}" ]] || stage22_die "Stage2.2 config not found: ${CONFIG}"
exec "${PYTHON_BIN}" -u "${PROJECT_DIR}/scripts/stage2_2_trajectory_optimization.py" analyze \
  --config "${CONFIG}" \
  --source-run "${SOURCE_STAGE1_1_RUN}" \
  --source-stage2-run "${SOURCE_STAGE2_RUN}" \
  --source-stage2-1-run "${SOURCE_STAGE2_1_RUN}" \
  --run-dir "${STAGE2_2_RUN_DIR}" \
  --backend serial
