#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${PROJECT_DIR}/scripts/stage4_2r3c3t13s9_shell_common.sh"
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
exec "${STAGE4_2R3C3T13S9_PYTHON}" "${PROJECT_DIR}/scripts/stage4_2r3c3t13s9_unified_postqueue_q1_identification.py" --self-test
