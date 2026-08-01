#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${PROJECT_DIR}/scripts/stage4_2r3c3t13s4_shell_common.sh"
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
exec "${STAGE4_2R3C3T13S4_PYTHON}" "${PROJECT_DIR}/scripts/stage4_2r3c3t13s4_lattice_transition_holdout.py" --self-test
