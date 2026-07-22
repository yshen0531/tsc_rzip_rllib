#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage3_0_shell_common.sh
source "${SCRIPT_DIR}/scripts/stage3_0_shell_common.sh"
stage30_project_init
stage30_find_python
stage30_resolve_existing_run
stage30_source_from_existing_run "${STAGE3_0_RUN_DIR}"
export STAGE3_0_RESUME=1
export STAGE3_0_COMMAND=analyze
exec bash "${SCRIPT_DIR}/run_stage3_0_svd3_tail_sqp_native.sh"
