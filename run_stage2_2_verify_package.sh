#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage2_2_shell_common.sh
source "${SCRIPT_DIR}/scripts/stage2_2_shell_common.sh"
stage22_project_init
stage22_find_python

if [[ -f "${PROJECT_DIR}/SHA256SUMS" ]] && command -v sha256sum >/dev/null 2>&1; then
  (cd "${PROJECT_DIR}" && sha256sum -c SHA256SUMS)
  echo "[Stage2.2 verify] packaged file checksums passed."
fi
bash "${PROJECT_DIR}/run_stage2_2_self_test.sh"
while IFS= read -r -d '' script; do bash -n "${script}"; done < <(find "${PROJECT_DIR}" -maxdepth 2 -type f -name '*.sh' -print0)
echo "[Stage2.2 verify] all shell scripts passed bash -n."
if grep -n -E 'STAGE2_2_BASE_TREE[[:space:]]*=|prepare_stage2_2_complete_tree|git[[:space:]]+(archive|checkout|show|clone)' \
  "${PROJECT_DIR}/run_stage2_2_svd3_corner_native.sh" \
  "${PROJECT_DIR}/run_stage2_2_svd3_corner_nohup.sh" \
  "${PROJECT_DIR}/run_stage2_2_one_generation_native.sh" \
  "${PROJECT_DIR}/run_stage2_2_prepare_only.sh" \
  "${PROJECT_DIR}/run_stage2_2_confirm_only.sh" \
  "${PROJECT_DIR}/run_stage2_2_analyze_only.sh" \
  "${PROJECT_DIR}/run_stop_stage2_2_now.sh" \
  "${PROJECT_DIR}/scripts/stage2_2_shell_common.sh" \
  "${PROJECT_DIR}/scripts/stage2_2_trajectory_optimization.py" \
  "${PROJECT_DIR}/tsc_rzip_rllib/diagnostics/stage2_2_trajectory_optimization.py" 2>/dev/null; then
  stage22_die "standalone Stage2.2 files still contain an external base-tree/Git dependency"
fi
echo "[Stage2.2 verify] no Git, network, or external base-tree dependency detected."
