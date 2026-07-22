#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export STAGE3_1_COMMAND=prepare STAGE3_1_BACKEND=serial
exec bash "${SCRIPT_DIR}/run_stage3_1_svd3_adaptive_sqp_mpc_native.sh"
