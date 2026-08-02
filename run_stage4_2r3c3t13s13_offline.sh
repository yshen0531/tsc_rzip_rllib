#!/usr/bin/env bash
set -euo pipefail
export STAGE4_2R3C3T13S13_COMMAND=offline
export STAGE4_2R3C3T13S13_BACKEND=serial
exec bash "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/run_stage4_2r3c3t13s13_common.sh"
