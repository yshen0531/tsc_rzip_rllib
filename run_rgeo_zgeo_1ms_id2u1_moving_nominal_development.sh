#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

: "${ID2U1_SOURCE_REVISION:?set implementation revision}"
: "${ID2U1_OUTPUT:?set new repository-local output directory}"
case "$ID2U1_OUTPUT" in "$ROOT"/*) ;; *) echo "output must be inside repository" >&2; exit 2;; esac
test ! -e "$ID2U1_OUTPUT"

python scripts/rgeo_zgeo_1ms_id2u1_moving_nominal_development.py offline \
  --source-revision "$ID2U1_SOURCE_REVISION" > "${ID2U1_OUTPUT}.offline.json"
python scripts/rgeo_zgeo_1ms_id2u1_moving_nominal_development.py run \
  --source-revision "$ID2U1_SOURCE_REVISION" --output "$ID2U1_OUTPUT"
python scripts/rgeo_zgeo_1ms_id2u1_moving_nominal_development_independent.py \
  --source-revision "$ID2U1_SOURCE_REVISION" --run-dir "$ID2U1_OUTPUT" \
  --output "$ID2U1_OUTPUT/independent_raw_audit.json"
