#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

: "${ID2Z1_SOURCE_REVISION:?set implementation revision}"
: "${ID2Z1_OUTPUT:?set new repository-local output directory}"
case "$ID2Z1_OUTPUT" in "$ROOT"/*) ;; *) echo "output must be inside repository" >&2; exit 2;; esac
test ! -e "$ID2Z1_OUTPUT"

python scripts/rgeo_zgeo_1ms_id2z1_late_action_macro_utility.py offline \
  --source-revision "$ID2Z1_SOURCE_REVISION" > "${ID2Z1_OUTPUT}.offline.json"
set +e
python scripts/rgeo_zgeo_1ms_id2z1_late_action_macro_utility.py run \
  --source-revision "$ID2Z1_SOURCE_REVISION" --output "$ID2Z1_OUTPUT"
primary_rc=$?
python scripts/rgeo_zgeo_1ms_id2z1_late_action_macro_utility_independent.py \
  --source-revision "$ID2Z1_SOURCE_REVISION" --run-dir "$ID2Z1_OUTPUT" \
  --output "$ID2Z1_OUTPUT/independent_raw_audit.json"
audit_rc=$?
set -e
if (( audit_rc != 0 )); then exit "$audit_rc"; fi
exit "$primary_rc"
