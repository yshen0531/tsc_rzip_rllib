#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/stage4_1r3_shell_common.sh"
stage41r3_project_init
stage41r3_find_python
[[ -f "${PROJECT_DIR}/SHA256SUMS" ]] || stage41r3_die "SHA256SUMS is missing"
(cd "${PROJECT_DIR}" && sha256sum -c SHA256SUMS)
echo "[Stage4.1R3 verify] packaged file checksums passed."
"${PROJECT_DIR}/run_stage4_1r3_self_test.sh"
"${PYTHON_BIN}" - "${PROJECT_DIR}" <<'PY'
from pathlib import Path
import json,sys,subprocess
root=Path(sys.argv[1])
manifest=json.loads((root/'PACKAGE_MANIFEST.json').read_text())
assert manifest['stage']=='Stage4.1R3'
assert manifest['complete_standalone'] is True
assert manifest['lean_delivery'] is True
assert manifest['default_workers']==128
assert manifest['controller_revision']=='control_aware_residual_observer_antiwindup_v3'
assert manifest['silent_worker_fallback'] is False
assert manifest['hard_gate_changed_from_stage3_4'] is False
assert manifest['finite_test_envelope_only'] is True
assert manifest['deployment_robustness_validated'] is False
assert manifest['regression_gate']['rollouts']==30
assert manifest['observer_ablation']['rollouts']==64
shells=[root/path for path in manifest['shell_files']]
assert len(shells)==6 and all(path.is_file() for path in shells)
for path in shells: subprocess.run(['bash','-n',str(path)],check=True)
# Deliberately do not inspect or reject Markdown files anywhere in the project.
print('[Stage4.1R3 verify] package manifest and scientific guardrails passed; residual Markdown files are ignored.')
PY
echo "[Stage4.1R3 verify] listed shell scripts passed bash -n; no Git, network, or external source-tree recovery is used."
