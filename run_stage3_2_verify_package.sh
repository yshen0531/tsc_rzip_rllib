#!/usr/bin/env bash
set -euo pipefail
export TERM="${TERM:-dumb}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/stage3_2_shell_common.sh"
stage32_project_init
stage32_find_python

if [[ -f "${PROJECT_DIR}/SHA256SUMS" ]] && command -v sha256sum >/dev/null 2>&1; then
  (cd "${PROJECT_DIR}" && sha256sum -c SHA256SUMS)
  echo "[Stage3.2 verify] packaged file checksums passed."
fi

bash "${PROJECT_DIR}/run_stage3_2_self_test.sh"

while IFS= read -r -d '' script; do
  bash -n "${script}"
done < <(find "${PROJECT_DIR}" -maxdepth 2 -type f -name '*.sh' -print0)
echo "[Stage3.2 verify] all shell scripts passed bash -n."

dependency_files=(
  "${PROJECT_DIR}/run_stage3_2_svd3_margin_long_hold_mpc_native.sh"
  "${PROJECT_DIR}/run_stage3_2_svd3_margin_long_hold_mpc_nohup.sh"
  "${PROJECT_DIR}/run_stage3_2_prepare_only.sh"
  "${PROJECT_DIR}/run_stage3_2_one_margin_round_native.sh"
  "${PROJECT_DIR}/run_stage3_2_extension_only.sh"
  "${PROJECT_DIR}/run_stage3_2_one_hold_round_native.sh"
  "${PROJECT_DIR}/run_stage3_2_identify_only.sh"
  "${PROJECT_DIR}/run_stage3_2_feedback_only.sh"
  "${PROJECT_DIR}/run_stage3_2_confirm_only.sh"
  "${PROJECT_DIR}/run_stage3_2_analyze_only.sh"
  "${PROJECT_DIR}/run_stage3_2_self_test.sh"
  "${PROJECT_DIR}/run_stop_stage3_2_now.sh"
  "${PROJECT_DIR}/scripts/stage3_2_shell_common.sh"
  "${PROJECT_DIR}/scripts/stage3_2_margin_long_hold_mpc.py"
  "${PROJECT_DIR}/tsc_rzip_rllib/diagnostics/stage3_2_margin_long_hold_mpc.py"
  "${PROJECT_DIR}/tsc_rzip_rllib/utils/ray_runtime.py"
)
if grep -n -E 'STAGE3_2_BASE_TREE[[:space:]]*=|prepare_stage3_2_complete_tree|git[[:space:]]+(archive|checkout|show|clone)|curl[[:space:]]|wget[[:space:]]' \
  "${dependency_files[@]}" 2>/dev/null; then
  stage32_die "standalone Stage3.2 files still contain a Git/network/external base-tree dependency"
fi
echo "[Stage3.2 verify] no Git, network, or external base-tree dependency detected."

"${PYTHON_BIN}" - "${PROJECT_DIR}" <<'PY'
from pathlib import Path
import json, sys
root = Path(sys.argv[1])
manifest = json.loads((root / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
if manifest.get("package_name") != "stage3_2_complete_standalone_ray_capacity_fix":
    raise SystemExit("PACKAGE_MANIFEST.json is not the Stage3.2 Ray-capacity-fixed standalone manifest")
if not manifest.get("complete_standalone"):
    raise SystemExit("package manifest does not declare a complete standalone tree")
for key in ("requires_git", "requires_network", "requires_external_base_tree"):
    if manifest.get(key):
        raise SystemExit(f"package manifest unexpectedly sets {key}=true")
if manifest.get("hard_gate_changed_from_stage3_1"):
    raise SystemExit("package manifest unexpectedly changes the Stage3.1 hard gate")
if manifest.get("robustness_validated"):
    raise SystemExit("package manifest must not claim robustness validation")
print("[Stage3.2 verify] package manifest guardrails passed.")
PY
