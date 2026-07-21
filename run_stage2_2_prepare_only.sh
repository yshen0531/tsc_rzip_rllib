#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export STAGE2_2_COMMAND=prepare
export STAGE2_2_BACKEND=serial
exec bash "${SCRIPT_DIR}/run_stage2_2_svd3_corner_native.sh"
