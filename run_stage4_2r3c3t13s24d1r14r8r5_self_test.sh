#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export STAGE4_2R3C3T13S24D1R14R8R5_COMMAND=self-test
exec bash "${PROJECT_DIR}/run_stage4_2r3c3t13s24d1r14r8r5_common.sh"
