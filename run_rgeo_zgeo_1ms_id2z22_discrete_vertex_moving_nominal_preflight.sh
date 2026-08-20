#!/usr/bin/env bash
set -u

fail() {
  printf '%s\n' "$1" >&2
  exit 2
}

PROJECT="${HOME}/tsc_all/tsc_rzip_rllib"
VENV="${HOME}/tsc_all/tsc_simulation/venv_simu"
test -d "$PROJECT" || fail "missing remote project"
test -f "$VENV/bin/activate" || fail "missing remote venv"
cd "$PROJECT" || fail "cannot enter remote project"
test "$PWD" = "$PROJECT" || fail "remote project mismatch"

REVISION="${ID2Z22_SOURCE_REVISION:-}"
OUTPUT="${ID2Z22_OUTPUT:-}"
test -n "$REVISION" || fail "ID2Z22_SOURCE_REVISION is required"
test -n "$OUTPUT" || fail "ID2Z22_OUTPUT is required"
case "$OUTPUT" in
  "$PROJECT"/*) ;;
  *) fail "ID2Z22_OUTPUT must remain inside the remote project" ;;
esac
test ! -e "$OUTPUT" || fail "output already exists"

source "$VENV/bin/activate" || fail "cannot activate remote venv"
python scripts/rgeo_zgeo_1ms_id2z22_discrete_vertex_moving_nominal_preflight.py \
  --source-revision "$REVISION" --output "$OUTPUT"
status=$?
test "$status" -eq 0 || exit 2
