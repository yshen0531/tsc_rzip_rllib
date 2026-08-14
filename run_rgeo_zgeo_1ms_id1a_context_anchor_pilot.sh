#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

: "${ID1A_SOURCE_REVISION:?set ID1A_SOURCE_REVISION to the 40-character implementation revision}"
: "${ID1A_OUTPUT:?set ID1A_OUTPUT to a new repository-local output directory}"

if [[ ! "$ID1A_SOURCE_REVISION" =~ ^[0-9a-f]{40}$ ]]; then
  echo "invalid ID1A_SOURCE_REVISION" >&2
  exit 2
fi
if [[ "$ID1A_OUTPUT" != "$ROOT_DIR"/* ]]; then
  echo "ID1A_OUTPUT must be inside the repository" >&2
  exit 2
fi
if [[ -e "$ID1A_OUTPUT" ]]; then
  echo "refusing to overwrite $ID1A_OUTPUT" >&2
  exit 2
fi

set +e
python scripts/rgeo_zgeo_1ms_id1a_context_anchor_pilot.py run \
  --source-revision "$ID1A_SOURCE_REVISION" \
  --output "$ID1A_OUTPUT"
PRIMARY_RC=$?
set -e

if python - "$ID1A_OUTPUT/result.json" <<'PY'
import json
import sys
from pathlib import Path
row = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
raise SystemExit(0 if row.get("execution_passed") and row.get("raw_integrity_passed") else 1)
PY
then
  set +e
  python scripts/rgeo_zgeo_1ms_id1a_context_anchor_pilot_independent.py \
    --run-dir "$ID1A_OUTPUT" \
    --source-revision "$ID1A_SOURCE_REVISION" \
    --output "$ID1A_OUTPUT/independent_audit.json"
  AUDIT_RC=$?
  set -e
  if [[ "$AUDIT_RC" -ne 0 ]]; then
    exit 2
  fi
fi

exit "$PRIMARY_RC"
