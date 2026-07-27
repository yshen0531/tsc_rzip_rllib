#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/stage4_1r4_shell_common.sh"
stage41r4_project_init
stage41r4_find_python
[[ -f "${PROJECT_DIR}/SHA256SUMS" ]] || stage41r4_die "SHA256SUMS is missing"
(cd "${PROJECT_DIR}" && sha256sum -c SHA256SUMS)
echo "[Stage4.1R4 verify] packaged file checksums passed."
"${PROJECT_DIR}/run_stage4_1r4_self_test.sh"
"${PYTHON_BIN}" - "${PROJECT_DIR}" <<'PY'
from pathlib import Path
import json,sys,subprocess
root=Path(sys.argv[1])
manifest=json.loads((root/'PACKAGE_MANIFEST.json').read_text())
assert manifest['stage']=='Stage4.1R4'
assert manifest['complete_standalone'] is True
assert manifest['lean_delivery'] is True
assert manifest['default_workers']==128
assert manifest['controller_revision']=='targeted_weak_slew_and_online_delay_slew_estimator_v4'
assert manifest['hard_gate_changed_from_stage4_1r3'] is False
assert manifest['weak_slew_latest_arrival_ms']==270
assert manifest['weak_slew_hold_through_ms']==370
assert manifest['deployment_robustness_validated'] is False
shells=[root/path for path in manifest['shell_files']]
assert len(shells)==6 and all(path.is_file() for path in shells)
for path in shells: subprocess.run(['bash','-n',str(path)],check=True)
# Deliberately do not inspect or reject Markdown files anywhere in the project.
print('[Stage4.1R4 verify] package manifest and scientific guardrails passed; residual Markdown files are ignored.')
PY
echo "[Stage4.1R4 verify] listed shell scripts passed bash -n; no Git, network, or external source-tree recovery is used."
