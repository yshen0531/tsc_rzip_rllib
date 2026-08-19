#!/usr/bin/env bash
set -u

PROJECT_ROOT="${PROJECT_ROOT:-$HOME/tsc_all/tsc_rzip_rllib}"
VENV_ROOT="${VENV_ROOT:-$HOME/tsc_all/tsc_simulation/venv_simu}"
SOURCE_REVISION="${ID2Z9_SOURCE_REVISION:-}"
OUTPUT="${ID2Z9_OUTPUT:-}"
CONFIG="$PROJECT_ROOT/configs/rgeo_zgeo_1ms_id2z9_late_root_branch_utility_support.json"

fail() { printf 'ID2Z9_LAUNCH_FAIL: %s\n' "$1" >&2; exit 2; }

test -n "$SOURCE_REVISION" || fail "ID2Z9_SOURCE_REVISION is required"
test -n "$OUTPUT" || fail "ID2Z9_OUTPUT is required"
test -d "$PROJECT_ROOT" || fail "project root missing"
test -f "$VENV_ROOT/bin/activate" || fail "venv missing"
cd "$PROJECT_ROOT" || fail "cannot enter project root"
test "$PWD" = "$PROJECT_ROOT" || fail "project root mismatch"
case "$OUTPUT" in "$PROJECT_ROOT"/*) ;; *) fail "output leaves project root" ;; esac
test ! -e "$OUTPUT" || fail "output already exists"

# shellcheck disable=SC1090
source "$VENV_ROOT/bin/activate" || fail "cannot activate venv"
python scripts/rgeo_zgeo_1ms_id2z9_late_root_branch_utility_support.py \
  --stage-config "$CONFIG" --source-revision "$SOURCE_REVISION" \
  --offline-only > "${OUTPUT}.offline.json"
test "$?" -eq 0 || exit 2
python scripts/rgeo_zgeo_1ms_id2z9_late_root_branch_utility_support.py \
  --stage-config "$CONFIG" --source-revision "$SOURCE_REVISION" --output "$OUTPUT"
primary_rc=$?
if test -f "$OUTPUT/result.json"; then
  python scripts/rgeo_zgeo_1ms_id2z9_late_root_branch_utility_support_independent.py \
    --stage-config "$CONFIG" --run-dir "$OUTPUT" \
    --source-revision "$SOURCE_REVISION" \
    --output "$OUTPUT/independent_raw_audit.json"
  test "$?" -eq 0 || exit 2
fi
test "$primary_rc" -eq 0 || exit 2
exit 0
