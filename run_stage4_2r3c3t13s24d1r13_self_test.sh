#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${PROJECT_DIR}/scripts/stage4_2r3c3t13s24d1r13_shell_common.sh"
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
cd "${PROJECT_DIR}"
exec "${STAGE4_2R3C3T13S24D1R13_PYTHON}" -c \
  'import json; from pathlib import Path; from tsc_rzip_rllib.diagnostics.stage4_2r3c3t13s24d1r13_zero_increment_deconfounding_sentinel import self_test; print(json.dumps(self_test(Path("configs/stage4_2r3c3t13s24d1r13_zero_increment_deconfounding_sentinel_370ms.json")), sort_keys=True, indent=2))'
