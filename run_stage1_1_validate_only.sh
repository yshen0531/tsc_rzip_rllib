#!/usr/bin/env bash
set -euo pipefail
RUN_DIR="${STAGE1_1_RUN_DIR:-$(cat stage1_1_runs/latest_stage1_1_run.txt)}"
SOURCE_ARGS=()
if [[ -n "${SOURCE_STAGE1_RUN:-}" ]]; then SOURCE_ARGS=(--source-run "$SOURCE_STAGE1_RUN"); fi
python -u scripts/stage1_1_supplement.py validate \
  --config "${STAGE1_1_CONFIG:-configs/stage1_1_supplement_100ms.json}" \
  --run-dir "$RUN_DIR" \
  --backend ray \
  "${SOURCE_ARGS[@]}"
