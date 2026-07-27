#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/stage4_1r6_shell_common.sh"
stage41r6_project_init
stage41r6_find_python
[[ -f "${PROJECT_DIR}/SHA256SUMS" ]] || stage41r6_die "SHA256SUMS is missing"
(cd "${PROJECT_DIR}" && sha256sum -c SHA256SUMS)
echo "[Stage4.1R6 verify] packaged file checksums passed."
"${PROJECT_DIR}/run_stage4_1r6_self_test.sh"
"${PYTHON_BIN}" - "${PROJECT_DIR}" <<'PY'
from pathlib import Path
import json,subprocess,sys
root=Path(sys.argv[1])
manifest=json.loads((root/'PACKAGE_MANIFEST.json').read_text())
cfg=json.loads((root/manifest['main_config']).read_text())
assert manifest['stage']=='Stage4.1R6'
assert manifest['complete_standalone'] is True
assert manifest['lean_delivery'] is True
assert manifest['default_workers']==128
assert manifest['controller_revision']=='confidence_gated_persistent_prior_physical_handover_v6'
assert manifest['hard_gate_changed_from_stage4_1r5'] is False
assert manifest['precalibrated_persistent_startup_is_primary'] is True
assert manifest['cold_common_prefix_is_diagnostic'] is True
assert manifest['deployment_robustness_validated'] is False
assert manifest['online_estimator_is_finite_hypothesis_bank_poc'] is True
assert cfg['confidence_gate']['minimum_confidence_ratio'] > 1.0
assert cfg['confidence_gate']['consecutive_best_observations'] >= 2
assert cfg['confidence_gate']['require_unique_best'] is True
assert cfg['static_startup']['minimum_persistent_exact_preservation'] == 1.0
assert cfg['static_startup']['minimum_persistent_exact_trace_equivalence'] == 1.0
shells=[root/path for path in manifest['shell_files']]
assert len(shells)==6 and all(path.is_file() for path in shells)
for path in shells:
    subprocess.run(['bash','-n',str(path)],check=True)
checksum_lines=[line for line in (root/'SHA256SUMS').read_text().splitlines() if line.strip()]
assert len(checksum_lines)==manifest['packaged_file_count_excluding_checksum_file']
# Deliberately do not inspect or reject Markdown files elsewhere in the project.
print('[Stage4.1R6 verify] package manifest and scientific guardrails passed; residual Markdown files are ignored.')
PY
echo "[Stage4.1R6 verify] listed shell scripts passed bash -n; no Git, network, or external source-tree recovery is used."
