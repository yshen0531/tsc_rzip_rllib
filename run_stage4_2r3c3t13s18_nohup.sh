#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$PROJECT_ROOT/scripts/stage4_2r3c3t13s18_shell_common.sh"
cd "$PROJECT_ROOT"

mkdir -p "$PROJECT_ROOT/logs/nohup"
STAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${STAGE4_2R3C3T13S18_LOG_FILE:-$PROJECT_ROOT/logs/nohup/stage4_2r3c3t13s18_pooled_causal_observer_preflight_${STAMP}.log}"

nohup env \
  STAGE4_2R3C3T13S18_CONFIG="$CONFIG" \
  STAGE4_2R3C3T13S18_SOURCE_RUN="$SOURCE_RUN" \
  STAGE4_2R3C3T13S18_S17_RUN="$S17_RUN" \
  STAGE4_2R3C3T13S18_OUTPUT_DIR="$OUTPUT_DIR" \
  "$PROJECT_ROOT/run_stage4_2r3c3t13s18_all.sh" >"$LOG_FILE" 2>&1 &
PID=$!
printf '%s\n' "$PID" >"$PROJECT_ROOT/logs/nohup/latest_stage4_2r3c3t13s18.pid"
printf '%s\n' "$LOG_FILE" >"$PROJECT_ROOT/logs/nohup/latest_stage4_2r3c3t13s18.log"
printf 'PID=%s\nLOG_FILE=%s\nOUTPUT_DIR=%s\n' "$PID" "$LOG_FILE" "$OUTPUT_DIR"
