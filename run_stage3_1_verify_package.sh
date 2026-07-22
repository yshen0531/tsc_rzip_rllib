#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage3_1_shell_common.sh
source "${SCRIPT_DIR}/scripts/stage3_1_shell_common.sh"
stage31_project_init
stage31_find_python

if [[ -f "${PROJECT_DIR}/SHA256SUMS" ]] && command -v sha256sum >/dev/null 2>&1; then
  (cd "${PROJECT_DIR}" && sha256sum -c SHA256SUMS)
  echo "[Stage3.1 verify] packaged file checksums passed."
fi

bash "${PROJECT_DIR}/run_stage3_1_self_test.sh"

while IFS= read -r -d '' script; do
  bash -n "${script}"
done < <(find "${PROJECT_DIR}" -maxdepth 2 -type f -name '*.sh' -print0)
echo "[Stage3.1 verify] all shell scripts passed bash -n."

if grep -n -E 'STAGE3_1_BASE_TREE[[:space:]]*=|prepare_stage3_1_complete_tree|git[[:space:]]+(archive|checkout|show|clone)|curl[[:space:]]|wget[[:space:]]' \
  "${PROJECT_DIR}/run_stage3_1_svd3_adaptive_sqp_mpc_native.sh" \
  "${PROJECT_DIR}/run_stage3_1_svd3_adaptive_sqp_mpc_nohup.sh" \
  "${PROJECT_DIR}/run_stage3_1_prepare_only.sh" \
  "${PROJECT_DIR}/run_stage3_1_one_round_native.sh" \
  "${PROJECT_DIR}/run_stage3_1_identify_only.sh" \
  "${PROJECT_DIR}/run_stage3_1_feedback_only.sh" \
  "${PROJECT_DIR}/run_stage3_1_confirm_only.sh" \
  "${PROJECT_DIR}/run_stage3_1_analyze_only.sh" \
  "${PROJECT_DIR}/run_stop_stage3_1_now.sh" \
  "${PROJECT_DIR}/scripts/stage3_1_shell_common.sh" \
  "${PROJECT_DIR}/scripts/stage3_1_adaptive_sqp_mpc.py" \
  "${PROJECT_DIR}/tsc_rzip_rllib/diagnostics/stage3_1_adaptive_sqp_mpc.py" 2>/dev/null; then
  stage31_die "standalone Stage3.1 files still contain a Git/network/external base-tree dependency"
fi
echo "[Stage3.1 verify] no Git, network, or external base-tree dependency detected."

"${PYTHON_BIN}" - "${PROJECT_DIR}" <<'PY'
from pathlib import Path
import json, sys
root = Path(sys.argv[1])
manifest = json.loads((root / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
if manifest.get("package_name") != "stage3_1_complete_standalone":
    raise SystemExit("PACKAGE_MANIFEST.json is not the Stage3.1 standalone manifest")
if not manifest.get("complete_standalone"):
    raise SystemExit("package manifest does not declare a complete standalone tree")
for key in ("requires_git", "requires_network", "requires_external_base_tree"):
    if manifest.get(key):
        raise SystemExit(f"package manifest unexpectedly sets {key}=true")
print("[Stage3.1 verify] package manifest guardrails passed.")
PY
