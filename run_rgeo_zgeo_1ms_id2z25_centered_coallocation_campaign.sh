#!/usr/bin/env bash
set -u

PROJECT_ROOT="${PROJECT_ROOT:-$HOME/tsc_all/tsc_rzip_rllib}"
VENV_ROOT="${VENV_ROOT:-$HOME/tsc_all/tsc_simulation/venv_simu}"
SOURCE_REVISION="${ID2Z25_SOURCE_REVISION:-}"
OUTPUT="${ID2Z25_OUTPUT:-}"
CONFIG="$PROJECT_ROOT/configs/rgeo_zgeo_1ms_id2z25_centered_coallocation_campaign.json"

fail() { printf 'ID2Z25_LAUNCH_FAIL: %s\n' "$1" >&2; exit 2; }

test -n "$SOURCE_REVISION" || fail "ID2Z25_SOURCE_REVISION is required"
test -n "$OUTPUT" || fail "ID2Z25_OUTPUT is required"
test -d "$PROJECT_ROOT" || fail "project root missing"
test -f "$VENV_ROOT/bin/activate" || fail "venv missing"
cd "$PROJECT_ROOT" || fail "cannot enter project root"
test "$PWD" = "$PROJECT_ROOT" || fail "project root mismatch"
case "$OUTPUT" in "$PROJECT_ROOT"/*) ;; *) fail "output leaves project root" ;; esac
test ! -e "$OUTPUT" || fail "output already exists"

# shellcheck disable=SC1090
source "$VENV_ROOT/bin/activate" || fail "cannot activate venv"
python scripts/rgeo_zgeo_1ms_id2z25_centered_coallocation_campaign.py \
  --stage-config "$CONFIG" --source-revision "$SOURCE_REVISION" \
  --offline-only > "${OUTPUT}.offline.json"
test "$?" -eq 0 || exit 2
set +e
python scripts/rgeo_zgeo_1ms_id2z25_centered_coallocation_campaign.py \
  --stage-config "$CONFIG" --source-revision "$SOURCE_REVISION" --output "$OUTPUT"
primary_rc=$?
set -e
if test -f "$OUTPUT/result.json"; then
  python scripts/rgeo_zgeo_1ms_id2z25_centered_coallocation_campaign_independent.py \
    --stage-config "$CONFIG" --run-dir "$OUTPUT" \
    --source-revision "$SOURCE_REVISION" \
    --output "$OUTPUT/independent_raw_audit.json"
  test "$?" -eq 0 || exit 2
fi
exit "$primary_rc"
