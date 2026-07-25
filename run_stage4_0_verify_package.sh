#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/stage4_0_shell_common.sh"
stage40_project_init
stage40_find_python
[[ -f "${PROJECT_DIR}/SHA256SUMS" ]] || stage40_die "SHA256SUMS is missing"
(cd "${PROJECT_DIR}" && sha256sum -c SHA256SUMS)
echo "[Stage4.0 verify] packaged file checksums passed."
"${PROJECT_DIR}/run_stage4_0_self_test.sh"
mapfile -t shell_files < <(find "${PROJECT_DIR}" -type f -name '*.sh' -print | sort)
[[ "${#shell_files[@]}" -eq 6 ]] || stage40_die "lean package must contain exactly 6 shell scripts; found ${#shell_files[@]}"
for path in "${shell_files[@]}"; do bash -n "${path}"; done
[[ "$(find "${PROJECT_DIR}" -type f \( -iname '*.md' -o -iname '*.markdown' \) | wc -l)" -eq 0 ]] || stage40_die "lean package must not contain Markdown files"
"${PYTHON_BIN}" - "${PROJECT_DIR}" <<'PY'
from pathlib import Path
import json,sys
root=Path(sys.argv[1]); manifest=json.loads((root/'PACKAGE_MANIFEST.json').read_text())
assert manifest['stage']=='Stage4.0'
assert manifest['complete_standalone'] is True
assert manifest['lean_delivery'] is True
assert manifest['default_workers']==192
assert manifest['silent_worker_fallback'] is False
assert manifest['source_controller_frozen'] is True
assert manifest['hard_gate_changed_from_stage3_4'] is False
assert manifest['finite_test_envelope_only'] is True
assert manifest['deployment_robustness_validated'] is False
assert manifest['shell_script_count']==6
assert manifest['markdown_file_count']==0
print('[Stage4.0 verify] package manifest and scientific guardrails passed.')
PY
echo "[Stage4.0 verify] all 6 shell scripts passed bash -n; no Markdown, Git, network, or external source-tree recovery is used."
