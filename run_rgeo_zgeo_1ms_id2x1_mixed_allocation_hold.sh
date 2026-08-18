#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

: "${ID2X1_SOURCE_REVISION:?set implementation revision}"
: "${ID2X1_OUTPUT:?set new repository-local output directory}"
case "$ID2X1_OUTPUT" in "$ROOT"/*) ;; *) echo "output must be inside repository" >&2; exit 2;; esac
test ! -e "$ID2X1_OUTPUT"

python scripts/rgeo_zgeo_1ms_id2x1_mixed_allocation_hold.py offline \
  --source-revision "$ID2X1_SOURCE_REVISION" > "${ID2X1_OUTPUT}.offline.json"
set +e
python scripts/rgeo_zgeo_1ms_id2x1_mixed_allocation_hold.py run \
  --source-revision "$ID2X1_SOURCE_REVISION" --output "$ID2X1_OUTPUT"
primary_rc=$?
python scripts/rgeo_zgeo_1ms_id2x1_mixed_allocation_hold_independent.py \
  --source-revision "$ID2X1_SOURCE_REVISION" --run-dir "$ID2X1_OUTPUT" \
  --output "$ID2X1_OUTPUT/independent_raw_audit.json"
audit_rc=$?
set -e
if (( audit_rc != 0 )); then exit "$audit_rc"; fi
exit "$primary_rc"
