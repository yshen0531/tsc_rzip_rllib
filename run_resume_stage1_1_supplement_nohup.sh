#!/usr/bin/env bash
set -euo pipefail
export STAGE1_1_RUN_DIR="${STAGE1_1_RUN_DIR:-$(cat stage1_1_runs/latest_stage1_1_run.txt)}"
exec ./run_stage1_1_supplement_nohup.sh
