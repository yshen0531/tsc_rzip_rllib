#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/stage3_1_shell_common.sh"
stage31_project_init; stage31_find_python; stage31_resolve_existing_run
export STAGE3_1_COMMAND=confirm STAGE3_1_RESUME=1
exec bash "${SCRIPT_DIR}/run_stage3_1_svd3_adaptive_sqp_mpc_native.sh"
