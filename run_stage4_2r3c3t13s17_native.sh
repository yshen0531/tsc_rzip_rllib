#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$PROJECT_ROOT/scripts/stage4_2r3c3t13s17_shell_common.sh"
cd "$PROJECT_ROOT"

python -m tsc_rzip_rllib.diagnostics.stage4_2r3c3t13s17_causal_multi_drift_belief_preflight \
  --config "$CONFIG" \
  --source-run "$SOURCE_RUN" \
  --output-dir "$OUTPUT_DIR" \
  --command "$COMMAND"
