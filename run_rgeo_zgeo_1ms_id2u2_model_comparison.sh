#!/usr/bin/env bash
set -euo pipefail

PROJECT="${ID2U2_PROJECT:-$HOME/tsc_all/tsc_rzip_rllib}"
VENV="${ID2U2_VENV:-$HOME/tsc_all/tsc_simulation/venv_simu}"
COMMAND="${ID2U2_COMMAND:-all}"
SOURCE_REVISION="${ID2U2_SOURCE_REVISION:?ID2U2_SOURCE_REVISION is required}"
OUTPUT_DIR="${ID2U2_OUTPUT_DIR:-$PROJECT/rgeo_zgeo_1ms_id2u2_${SOURCE_REVISION:0:8}}"
CONFIG="$PROJECT/configs/rgeo_zgeo_1ms_id2u2_bounded_causal_model_comparison.json"

cd "$PROJECT"
test "$PWD" = "$HOME/tsc_all/tsc_rzip_rllib"
test -f "$VENV/bin/activate"
source "$VENV/bin/activate"

case "$COMMAND" in
  preflight)
    python scripts/rgeo_zgeo_1ms_id2u2_bounded_causal_model_comparison.py \
      --config "$CONFIG" --preflight
    ;;
  primary)
    python scripts/rgeo_zgeo_1ms_id2u2_bounded_causal_model_comparison.py \
      --config "$CONFIG" --source-revision "$SOURCE_REVISION" --output-dir "$OUTPUT_DIR"
    ;;
  independent)
    python scripts/rgeo_zgeo_1ms_id2u2_bounded_causal_model_independent.py \
      --config "$CONFIG" --primary-dir "$OUTPUT_DIR" --output "$OUTPUT_DIR/independent_audit.json"
    ;;
  all)
    test ! -e "$OUTPUT_DIR"
    python scripts/rgeo_zgeo_1ms_id2u2_bounded_causal_model_comparison.py \
      --config "$CONFIG" --source-revision "$SOURCE_REVISION" --output-dir "$OUTPUT_DIR" || primary_rc=$?
    primary_rc="${primary_rc:-0}"
    python scripts/rgeo_zgeo_1ms_id2u2_bounded_causal_model_independent.py \
      --config "$CONFIG" --primary-dir "$OUTPUT_DIR" --output "$OUTPUT_DIR/independent_audit.json"
    exit "$primary_rc"
    ;;
  *)
    printf 'unknown ID2U2_COMMAND=%s\n' "$COMMAND" >&2
    exit 2
    ;;
esac
