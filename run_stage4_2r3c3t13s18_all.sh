#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$PROJECT_ROOT/scripts/stage4_2r3c3t13s18_shell_common.sh"
cd "$PROJECT_ROOT"

if [[ -e "$OUTPUT_DIR" ]]; then
  printf 'T13S18 output identity already exists: %s\n' "$OUTPUT_DIR" >&2
  exit 1
fi

STAGE4_2R3C3T13S18_COMMAND=prepare "$PROJECT_ROOT/run_stage4_2r3c3t13s18_native.sh"
STAGE4_2R3C3T13S18_COMMAND=evaluate "$PROJECT_ROOT/run_stage4_2r3c3t13s18_native.sh"
STAGE4_2R3C3T13S18_COMMAND=postprocess "$PROJECT_ROOT/run_stage4_2r3c3t13s18_native.sh"
