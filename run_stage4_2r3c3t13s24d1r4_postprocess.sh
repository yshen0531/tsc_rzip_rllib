#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export STAGE4_2R3C3T13S24D1R4_COMMAND=postprocess
export STAGE4_2R3C3T13S24D1R4_BACKEND=serial
export STAGE4_2R3C3T13S24D1R4_RESUME=1
exec bash "${PROJECT_DIR}/run_stage4_2r3c3t13s24d1r4_native.sh"
