#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export STAGE3_0_COMMAND=round
exec bash "${SCRIPT_DIR}/run_stage3_0_svd3_tail_sqp_native.sh"
