#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$HOME/tsc_all/tsc_rzip_rllib}"
SOURCE_R1_RUN="${SOURCE_R1_RUN:-$PROJECT_DIR/stage4_2r1_runs/stage4_2r1_true_tsc_plant_restart_action_replay_20260729_162619}"
OUTPUT_DIR="${OUTPUT_DIR:-$PROJECT_DIR/stage4_2r3_preflight/existing_bank}"
VENV_ACTIVATE="${VENV_ACTIVATE:-$HOME/tsc_all/tsc_simulation/venv_simu/bin/activate}"
AUDIT_SCRIPT="${AUDIT_SCRIPT:-$PROJECT_DIR/stage4_2r3_preflight/audit_tools/stage4_2r3_existing_bank_pair_feasibility.py}"

test -d "$PROJECT_DIR"
test -d "$SOURCE_R1_RUN"
test -f "$VENV_ACTIVATE"
test -f "$AUDIT_SCRIPT"
cd "$PROJECT_DIR"
test "$PWD" = "$HOME/tsc_all/tsc_rzip_rllib"

mkdir -p "$OUTPUT_DIR"
source "$VENV_ACTIVATE"
export PYTHONPATH="$PROJECT_DIR${PYTHONPATH:+:$PYTHONPATH}"

python "$AUDIT_SCRIPT" \
  --source-r1-run "$SOURCE_R1_RUN" \
  --output-dir "$OUTPUT_DIR" \
  >"$OUTPUT_DIR/preflight.log" 2>&1

(
  cd "$OUTPUT_DIR"
  sha256sum \
    audit.json \
    endpoints.json \
    inventory.json \
    cross_key_pair_diagnostics.json \
    cross_key_pair_diagnostics.csv \
    preflight.log \
    > SHA256SUMS
)
