#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT" || exit 2

: "${ID2Z6R1_RUN_DIR:?set the existing repository-local ID2Z6 run directory}"
: "${ID2Z6R1_EXPERIMENT_SOURCE_REVISION:?set the original ID2Z6 source revision}"
: "${ID2Z6R1_HOTFIX_SOURCE_REVISION:?set the ID2Z6R1 hotfix source revision}"

case "$ID2Z6R1_RUN_DIR" in
  "$ROOT"/*) ;;
  *) echo "run directory must be inside repository" >&2; exit 2 ;;
esac

python scripts/rgeo_zgeo_1ms_id2z6r1_resume.py \
  --run-dir "$ID2Z6R1_RUN_DIR" \
  --experiment-source-revision "$ID2Z6R1_EXPERIMENT_SOURCE_REVISION" \
  --hotfix-source-revision "$ID2Z6R1_HOTFIX_SOURCE_REVISION" \
  --preflight-only || exit 2

set +e
python scripts/rgeo_zgeo_1ms_id2z6r1_resume.py \
  --run-dir "$ID2Z6R1_RUN_DIR" \
  --experiment-source-revision "$ID2Z6R1_EXPERIMENT_SOURCE_REVISION" \
  --hotfix-source-revision "$ID2Z6R1_HOTFIX_SOURCE_REVISION"
primary_rc=$?

python scripts/rgeo_zgeo_1ms_id2z6r1_resume_independent.py \
  --run-dir "$ID2Z6R1_RUN_DIR" \
  --experiment-source-revision "$ID2Z6R1_EXPERIMENT_SOURCE_REVISION" \
  --hotfix-source-revision "$ID2Z6R1_HOTFIX_SOURCE_REVISION" \
  --output "$ID2Z6R1_RUN_DIR/independent_raw_audit.json"
audit_rc=$?
set -e

if [[ $audit_rc -ne 0 ]]; then
  exit 2
fi
exit "$primary_rc"
