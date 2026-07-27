#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/stage4_1r5_shell_common.sh"
stage41r5_project_init
stage41r5_find_python
[[ -f "${PROJECT_DIR}/SHA256SUMS" ]] || stage41r5_die "SHA256SUMS is missing"
(cd "${PROJECT_DIR}" && sha256sum -c SHA256SUMS)
echo "[Stage4.1R5 verify] packaged file checksums passed."
"${PROJECT_DIR}/run_stage4_1r5_self_test.sh"
"${PYTHON_BIN}" - "${PROJECT_DIR}" <<'PY'
from pathlib import Path
import json,subprocess,sys
root=Path(sys.argv[1])
manifest=json.loads((root/'PACKAGE_MANIFEST.json').read_text())
assert manifest['stage']=='Stage4.1R5'
assert manifest['complete_standalone'] is True
assert manifest['lean_delivery'] is True
assert manifest['default_workers']==128
assert manifest['controller_revision']=='confidence_gated_bumpless_delay_slew_handover_v5'
assert manifest['hard_gate_changed_from_stage4_1r4'] is False
assert manifest['deployment_robustness_validated'] is False
assert manifest['online_estimator_is_finite_hypothesis_bank_poc'] is True
shells=[root/path for path in manifest['shell_files']]
assert len(shells)==6 and all(path.is_file() for path in shells)
for path in shells:
    subprocess.run(['bash','-n',str(path)],check=True)
# Deliberately do not inspect or reject Markdown files elsewhere in the project.
print('[Stage4.1R5 verify] package manifest and scientific guardrails passed; residual Markdown files are ignored.')
PY
echo "[Stage4.1R5 verify] listed shell scripts passed bash -n; no Git, network, or external source-tree recovery is used."
