#!/usr/bin/env bash
set -u

PROJECT_ROOT="${PROJECT_ROOT:-$HOME/tsc_all/tsc_rzip_rllib}"
VENV_ROOT="${VENV_ROOT:-$HOME/tsc_all/tsc_simulation/venv_simu}"
SOURCE_REVISION="${ID2Z8_SOURCE_REVISION:-}"
OUTPUT="${ID2Z8_OUTPUT:-}"
CONFIG="$PROJECT_ROOT/configs/rgeo_zgeo_1ms_id2z8_small_sequence_model.json"

fail() {
  printf 'ID2Z8_LAUNCH_FAIL: %s\n' "$1" >&2
  exit 2
}

test -n "$SOURCE_REVISION" || fail "ID2Z8_SOURCE_REVISION is required"
test -n "$OUTPUT" || fail "ID2Z8_OUTPUT is required"
test -d "$PROJECT_ROOT" || fail "project root missing"
test -f "$VENV_ROOT/bin/activate" || fail "venv missing"
cd "$PROJECT_ROOT" || fail "cannot enter project root"
test "$PWD" = "$PROJECT_ROOT" || fail "project root mismatch"
case "$OUTPUT" in
  "$PROJECT_ROOT"/*) ;;
  *) fail "output leaves project root" ;;
esac
test ! -e "$OUTPUT" || fail "output already exists"

# shellcheck disable=SC1090
source "$VENV_ROOT/bin/activate" || fail "cannot activate venv"
python scripts/rgeo_zgeo_1ms_id2z8_small_sequence_model.py \
  --stage-config "$CONFIG" \
  --source-revision "$SOURCE_REVISION" \
  --output "$OUTPUT"
primary_rc=$?
test -f "$OUTPUT/result.json" || exit 2
python scripts/rgeo_zgeo_1ms_id2z8_small_sequence_model_audit.py \
  --stage-config "$CONFIG" \
  --run-dir "$OUTPUT" \
  --source-revision "$SOURCE_REVISION" \
  --output "$OUTPUT/deterministic_replay_audit.json"
audit_rc=$?
if test "$audit_rc" -ne 0; then
  exit 2
fi
if test "$primary_rc" -ne 0; then
  exit 2
fi
exit 0
