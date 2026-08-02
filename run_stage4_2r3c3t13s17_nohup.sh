#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$PROJECT_ROOT/scripts/stage4_2r3c3t13s17_shell_common.sh"
cd "$PROJECT_ROOT"

mkdir -p "$PROJECT_ROOT/logs/nohup"
STAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${STAGE4_2R3C3T13S17_LOG_FILE:-$PROJECT_ROOT/logs/nohup/stage4_2r3c3t13s17_causal_multi_drift_belief_preflight_${STAMP}.log}"

nohup env \
  STAGE4_2R3C3T13S17_CONFIG="$CONFIG" \
  STAGE4_2R3C3T13S17_SOURCE_RUN="$SOURCE_RUN" \
  STAGE4_2R3C3T13S17_OUTPUT_DIR="$OUTPUT_DIR" \
  "$PROJECT_ROOT/run_stage4_2r3c3t13s17_all.sh" >"$LOG_FILE" 2>&1 &
PID=$!
printf '%s\n' "$PID" >"$PROJECT_ROOT/logs/nohup/latest_stage4_2r3c3t13s17.pid"
printf '%s\n' "$LOG_FILE" >"$PROJECT_ROOT/logs/nohup/latest_stage4_2r3c3t13s17.log"
printf 'PID=%s\nLOG_FILE=%s\nOUTPUT_DIR=%s\n' "$PID" "$LOG_FILE" "$OUTPUT_DIR"
