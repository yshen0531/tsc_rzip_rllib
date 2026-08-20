#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "$0")" && pwd)"
OUTPUT="${ID2Z26_OUTPUT:?ID2Z26_OUTPUT is required}"
REVISION="${ID2Z26_SOURCE_REVISION:?ID2Z26_SOURCE_REVISION is required}"
VENV="$HOME/tsc_all/tsc_simulation/venv_simu"

fail() {
  printf '%s\n' "$1" >&2
  exit 2
}

test -d "$ROOT" || fail "repository root missing"
test -f "$VENV/bin/activate" || fail "server virtualenv missing"
case "$OUTPUT" in
  "$ROOT"/*) ;;
  *) fail "output must remain inside repository" ;;
esac
test ! -e "$OUTPUT" || fail "output already exists"
mkdir -p "$OUTPUT" || fail "cannot create output"

. "$VENV/bin/activate" || fail "cannot activate virtualenv"
cd "$ROOT" || fail "cannot enter repository"

python scripts/rgeo_zgeo_1ms_id2z26_dynamic_output_aligned_preflight.py \
  --source-revision "$REVISION" \
  --output "$OUTPUT/result.json" || exit 2

python scripts/rgeo_zgeo_1ms_id2z26_dynamic_output_aligned_preflight_independent.py \
  --primary "$OUTPUT/result.json" \
  --source-revision "$REVISION" \
  --output "$OUTPUT/independent_audit.json" || exit 2

printf 'ID2Z26_ZERO_TSC_PREFLIGHT_COMPLETE=%s\n' "$OUTPUT"
