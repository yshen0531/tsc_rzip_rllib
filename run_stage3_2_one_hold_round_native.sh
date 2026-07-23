#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/stage3_2_shell_common.sh"
stage32_project_init; stage32_find_python; stage32_resolve_existing_run
export STAGE3_2_COMMAND=hold-round STAGE3_2_RESUME=1
exec bash "${SCRIPT_DIR}/run_stage3_2_svd3_margin_long_hold_mpc_native.sh"
