#!/usr/bin/env bash
set -euo pipefail
export STAGE4_2R3C3T11_COMMAND=offline
export STAGE4_2R3C3T11_BACKEND=serial
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/run_stage4_2r3c3t11_common.sh"
