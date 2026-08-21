#!/usr/bin/env bash
set -u
PROJECT_ROOT="${PROJECT_ROOT:-$HOME/tsc_all/tsc_rzip_rllib}"
VENV_ROOT="${VENV_ROOT:-$HOME/tsc_all/tsc_simulation/venv_simu}"
REV="${ID2Z31_SOURCE_REVISION:-}"
OUT="${ID2Z31_OUTPUT:-}"
CONFIG="$PROJECT_ROOT/configs/rgeo_zgeo_1ms_id2z31_event_phase_discriminator.json"
fail() { printf 'ID2Z31_LAUNCH_FAIL: %s\n' "$1" >&2; exit 2; }
test -n "$REV" || fail "ID2Z31_SOURCE_REVISION is required"
test -n "$OUT" || fail "ID2Z31_OUTPUT is required"
test -d "$PROJECT_ROOT" || fail "project root missing"
test -f "$VENV_ROOT/bin/activate" || fail "venv missing"
cd "$PROJECT_ROOT" || fail "cannot enter project root"
test "$PWD" = "$PROJECT_ROOT" || fail "project root mismatch"
case "$OUT" in "$PROJECT_ROOT"/*) ;; *) fail "output leaves project root" ;; esac
test ! -e "$OUT" || fail "output exists"
source "$VENV_ROOT/bin/activate" || fail "venv activation"
python scripts/rgeo_zgeo_1ms_id2z31_event_phase_discriminator.py \
  --config "$CONFIG" --source-revision "$REV" \
  --output "${OUT}.offline.json" --offline || exit 2
set +e
python scripts/rgeo_zgeo_1ms_id2z31_event_phase_discriminator.py \
  --config "$CONFIG" --source-revision "$REV" --output "$OUT"
primary_rc=$?
set -e
if test -f "$OUT/result.json"; then
  python scripts/rgeo_zgeo_1ms_id2z31_event_phase_discriminator_independent.py \
    --config "$CONFIG" --run-dir "$OUT" --source-revision "$REV" \
    --output "$OUT/independent_raw_audit.json" || exit 2
fi
exit "$primary_rc"
