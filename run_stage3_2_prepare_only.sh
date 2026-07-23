#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export STAGE3_2_COMMAND=prepare STAGE3_2_BACKEND=serial
exec bash "${SCRIPT_DIR}/run_stage3_2_svd3_margin_long_hold_mpc_native.sh"
