#!/usr/bin/env bash
set -u

fail() { printf 'ID2Z24_LAUNCH_FAIL: %s\n' "$1" >&2; exit 2; }

PROJECT="${HOME}/tsc_all/tsc_rzip_rllib"
VENV="${HOME}/tsc_all/tsc_simulation/venv_simu"
REVISION="${ID2Z24_SOURCE_REVISION:-}"
OUTPUT="${ID2Z24_OUTPUT:-}"

test -n "$REVISION" || fail "ID2Z24_SOURCE_REVISION is required"
test -n "$OUTPUT" || fail "ID2Z24_OUTPUT is required"
test -d "$PROJECT" || fail "missing remote project"
test -f "$VENV/bin/activate" || fail "missing remote venv"
cd "$PROJECT" || fail "cannot enter remote project"
test "$PWD" = "$PROJECT" || fail "remote project mismatch"
case "$OUTPUT" in "$PROJECT"/*) ;; *) fail "output leaves remote project" ;; esac
test ! -e "$OUTPUT" || fail "output already exists"

# shellcheck disable=SC1090
source "$VENV/bin/activate" || fail "cannot activate remote venv"
mkdir -p "$OUTPUT" || fail "cannot create output"
python scripts/rgeo_zgeo_1ms_id2z24_centered_coallocation_preflight.py \
  --source-revision "$REVISION" --output "$OUTPUT/result.json"
test "$?" -eq 0 || exit 2
python scripts/rgeo_zgeo_1ms_id2z24_centered_coallocation_independent.py \
  --primary "$OUTPUT/result.json" --source-revision "$REVISION" \
  --output "$OUTPUT/independent_audit.json"
test "$?" -eq 0 || exit 2
