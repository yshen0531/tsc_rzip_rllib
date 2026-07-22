#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage3_0_shell_common.sh
source "${SCRIPT_DIR}/scripts/stage3_0_shell_common.sh"
stage30_project_init
stage30_find_python
if [[ -f "${PROJECT_DIR}/SHA256SUMS" ]] && command -v sha256sum >/dev/null 2>&1; then
  (cd "${PROJECT_DIR}" && sha256sum -c SHA256SUMS)
  echo "[Stage3.0 verify] packaged file checksums passed."
fi
bash "${PROJECT_DIR}/run_stage3_0_self_test.sh"
while IFS= read -r -d '' script; do bash -n "${script}"; done < <(find "${PROJECT_DIR}" -maxdepth 2 -type f -name '*.sh' -print0)
echo "[Stage3.0 verify] all shell scripts passed bash -n."
if grep -n -E 'STAGE3_0_BASE_TREE[[:space:]]*=|prepare_stage3_0_complete_tree|git[[:space:]]+(archive|checkout|show|clone)|curl[[:space:]]|wget[[:space:]]' \
  "${PROJECT_DIR}/run_stage3_0_svd3_tail_sqp_native.sh" \
  "${PROJECT_DIR}/run_stage3_0_svd3_tail_sqp_nohup.sh" \
  "${PROJECT_DIR}/run_stage3_0_one_round_native.sh" \
  "${PROJECT_DIR}/run_stage3_0_prepare_only.sh" \
  "${PROJECT_DIR}/run_stage3_0_screen_only.sh" \
  "${PROJECT_DIR}/run_stage3_0_identify_only.sh" \
  "${PROJECT_DIR}/run_stage3_0_confirm_only.sh" \
  "${PROJECT_DIR}/run_stage3_0_analyze_only.sh" \
  "${PROJECT_DIR}/run_stop_stage3_0_now.sh" \
  "${PROJECT_DIR}/scripts/stage3_0_shell_common.sh" \
  "${PROJECT_DIR}/scripts/stage3_0_tail_sqp.py" \
  "${PROJECT_DIR}/tsc_rzip_rllib/diagnostics/stage3_0_tail_sqp.py" 2>/dev/null; then
  stage30_die "standalone Stage3.0 files still contain a Git/network/external base-tree dependency"
fi
echo "[Stage3.0 verify] no Git, network, or external base-tree dependency detected."
