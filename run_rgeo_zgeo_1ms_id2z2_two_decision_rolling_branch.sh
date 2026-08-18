#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

: "${ID2Z2_SOURCE_REVISION:?set implementation revision}"
: "${ID2Z2_OUTPUT:?set new repository-local output directory}"
case "$ID2Z2_OUTPUT" in "$ROOT"/*) ;; *) echo "output must be inside repository" >&2; exit 2;; esac
test ! -e "$ID2Z2_OUTPUT"

python scripts/rgeo_zgeo_1ms_id2z2_two_decision_rolling_branch.py offline \
  --source-revision "$ID2Z2_SOURCE_REVISION" > "${ID2Z2_OUTPUT}.offline.json"
set +e
python scripts/rgeo_zgeo_1ms_id2z2_two_decision_rolling_branch.py run \
  --source-revision "$ID2Z2_SOURCE_REVISION" --output "$ID2Z2_OUTPUT"
primary_rc=$?
python scripts/rgeo_zgeo_1ms_id2z2_two_decision_rolling_branch_independent.py \
  --source-revision "$ID2Z2_SOURCE_REVISION" --run-dir "$ID2Z2_OUTPUT" \
  --output "$ID2Z2_OUTPUT/independent_raw_audit.json"
audit_rc=$?
set -e
if (( audit_rc != 0 )); then exit "$audit_rc"; fi
exit "$primary_rc"
