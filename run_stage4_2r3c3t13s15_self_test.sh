#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${PROJECT_DIR}/scripts/stage4_2r3c3t13s15_shell_common.sh"
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
exec "${STAGE4_2R3C3T13S15_PYTHON}" -m tsc_rzip_rllib.diagnostics.stage4_2r3c3t13s15_fixed_basis_local_identification --self-test
