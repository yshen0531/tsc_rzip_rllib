#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/stage4_1r7_shell_common.sh"
stage41r7_project_init
stage41r7_find_python
export TERM="${TERM:-xterm}"
"${PYTHON_BIN}" -m compileall -q "${PROJECT_DIR}/tsc_rzip_rllib" "${PROJECT_DIR}/scripts" "${PROJECT_DIR}/tests"
"${PYTHON_BIN}" -u "${PROJECT_DIR}/scripts/stage4_1r7_precontrol_calibration_queue_startup.py" --self-test
"${PYTHON_BIN}" -m unittest discover -s "${PROJECT_DIR}/tests" -p 'test_*.py' -v
