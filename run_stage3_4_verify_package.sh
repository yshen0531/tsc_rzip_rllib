#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/stage3_4_shell_common.sh"
stage34_project_init
stage34_find_python

[[ -f "${PROJECT_DIR}/SHA256SUMS" ]] || stage34_die "SHA256SUMS is missing"
(
  cd "${PROJECT_DIR}"
  sha256sum -c SHA256SUMS
)

echo "[Stage3.4 verify] packaged file checksums passed."
"${PROJECT_DIR}/run_stage3_4_self_test.sh"

mapfile -t shell_files < <(find "${PROJECT_DIR}" -type f -name '*.sh' -print | sort)
[[ "${#shell_files[@]}" -eq 6 ]] || stage34_die "lean package must contain exactly 6 shell scripts; found ${#shell_files[@]}"
for path in "${shell_files[@]}"; do bash -n "${path}"; done
[[ "$(find "${PROJECT_DIR}" -type f \( -iname '*.md' -o -iname '*.markdown' \) | wc -l)" -eq 0 ]] || stage34_die "lean package must not contain Markdown files"

echo "[Stage3.4 verify] all 6 shell scripts passed bash -n and no Markdown files are present."

"${PYTHON_BIN}" - "${PROJECT_DIR}" <<'PY'
from pathlib import Path
import json,sys
root=Path(sys.argv[1]); manifest=json.loads((root/'PACKAGE_MANIFEST.json').read_text())
assert manifest.get('stage') == 'Stage3.4'
assert manifest.get('complete_standalone') is True
assert manifest.get('lean_delivery') is True
assert manifest.get('requires_git') is False
assert manifest.get('requires_network') is False
assert manifest.get('requires_external_base_tree') is False
assert manifest.get('latest_allowed_arrival_ms') == 250
assert manifest.get('hold_through_ms') == 350
assert manifest.get('minimum_post_arrival_hold_ms') == 100
assert manifest.get('hard_gate_changed_from_stage3_3') is False
ip=manifest.get('ip_tracking_gate',{})
assert ip == {'terminal_abs_tolerance_A':2000.0,'hold_rms_tolerance_A':2400.0,'sustained_max_tolerance_A':4000.0}
assert manifest.get('online_mpc_deployment_ready') is False
assert manifest.get('initial_state_robustness_validated') is False
assert manifest.get('plant_parameter_robustness_validated') is False
assert manifest.get('noise_delay_robustness_validated') is False
assert manifest.get('residual_rl_primary_controller') is False
assert manifest.get('shell_script_count') == 6
assert manifest.get('markdown_file_count') == 0
print('[Stage3.4 verify] package manifest and scientific guardrails passed.')
PY

echo "[Stage3.4 verify] no Git, network, or external base-tree dependency is used."
