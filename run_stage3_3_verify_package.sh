#!/usr/bin/env bash
set -euo pipefail
export TERM="${TERM:-dumb}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage3_3_shell_common.sh
source "${SCRIPT_DIR}/scripts/stage3_3_shell_common.sh"
stage33_project_init
stage33_find_python

if [[ -f "${PROJECT_DIR}/SHA256SUMS" ]] && command -v sha256sum >/dev/null 2>&1; then
  (cd "${PROJECT_DIR}" && sha256sum -c SHA256SUMS)
  echo "[Stage3.3 verify] packaged file checksums passed."
fi

bash "${PROJECT_DIR}/run_stage3_3_self_test.sh"

while IFS= read -r -d '' script; do
  bash -n "${script}"
done < <(find "${PROJECT_DIR}" -type f -name '*.sh' -print0)
echo "[Stage3.3 verify] all shell scripts passed bash -n."

# This delivery is intentionally lean: no packaged Markdown and only the
# essential Stage3.3 launch/stop/verification shell files are allowed.
if find "${PROJECT_DIR}" -type f -name '*.md' -print -quit | grep -q .; then
  stage33_die "lean package unexpectedly contains Markdown files"
fi
mapfile -t actual_shells < <(
  find "${PROJECT_DIR}" -type f -name '*.sh' -printf '%P\n' | sort
)
expected_shells=(
  "run_stage3_3_self_test.sh"
  "run_stage3_3_target_conditioned_mpc_native.sh"
  "run_stage3_3_target_conditioned_mpc_nohup.sh"
  "run_stage3_3_verify_package.sh"
  "run_stop_stage3_3_now.sh"
  "scripts/stage3_3_shell_common.sh"
)
if [[ "${actual_shells[*]}" != "${expected_shells[*]}" ]]; then
  printf 'Expected shell files:\n%s\n' "${expected_shells[*]}" >&2
  printf 'Actual shell files:\n%s\n' "${actual_shells[*]}" >&2
  stage33_die "lean package shell-file set differs from the audited set"
fi
echo "[Stage3.3 verify] lean package guard passed: no Markdown and 6 essential shell scripts only."

dependency_files=(
  "${PROJECT_DIR}/run_stage3_3_target_conditioned_mpc_native.sh"
  "${PROJECT_DIR}/run_stage3_3_target_conditioned_mpc_nohup.sh"
  "${PROJECT_DIR}/run_stage3_3_self_test.sh"
  "${PROJECT_DIR}/run_stop_stage3_3_now.sh"
  "${PROJECT_DIR}/scripts/stage3_3_shell_common.sh"
  "${PROJECT_DIR}/scripts/stage3_3_target_conditioned_mpc.py"
  "${PROJECT_DIR}/tsc_rzip_rllib/diagnostics/stage3_3_target_conditioned_mpc.py"
  "${PROJECT_DIR}/tsc_rzip_rllib/utils/ray_runtime.py"
)
if grep -n -E 'STAGE3_3_BASE_TREE[[:space:]]*=|prepare_stage3_3_complete_tree|git[[:space:]]+(archive|checkout|show|clone)|curl[[:space:]]|wget[[:space:]]' \
  "${dependency_files[@]}" 2>/dev/null; then
  stage33_die "standalone Stage3.3 files still contain a Git/network/external base-tree dependency"
fi
echo "[Stage3.3 verify] no Git, network, or external base-tree dependency detected."

"${PYTHON_BIN}" - "${PROJECT_DIR}" <<'PY'
from pathlib import Path
import json
import sys
root = Path(sys.argv[1])
manifest = json.loads((root / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
expected_name = "stage3_3_complete_standalone_ip_tracking_2x_lean_refinement_fix"
if manifest.get("package_name") != expected_name:
    raise SystemExit(f"PACKAGE_MANIFEST.json package_name must be {expected_name}")
if not manifest.get("complete_standalone"):
    raise SystemExit("package manifest does not declare a complete standalone tree")
if not manifest.get("lean_delivery"):
    raise SystemExit("package manifest does not declare lean_delivery=true")
for key in ("requires_git", "requires_network", "requires_external_base_tree"):
    if manifest.get(key):
        raise SystemExit(f"package manifest unexpectedly sets {key}=true")
if manifest.get("hard_gate_changed_from_stage3_2"):
    raise SystemExit("package manifest unexpectedly changes the Stage3.2 R/Z/speed/Ip safety hard gate")
if not manifest.get("explicit_ip_tracking_gate_added"):
    raise SystemExit("package manifest must declare the separate Ip tracking gate")
expected_tolerances = {
    "terminal_abs_tolerance_A": 2000.0,
    "hold_rms_tolerance_A": 2400.0,
    "sustained_max_tolerance_A": 4000.0,
}
if manifest.get("ip_tracking_gate") != expected_tolerances:
    raise SystemExit("package manifest Ip tracking tolerances are not the requested doubled values")
if manifest.get("ip_tracking_revision") != "2x_for_tsc_additional_heating":
    raise SystemExit("package manifest has the wrong Ip tracking revision")
expected_refinement_revision = "dimensionless_central_difference_source_prior_v2"
if manifest.get("refinement_model_revision") != expected_refinement_revision:
    raise SystemExit("package manifest has the wrong refinement model revision")
config = json.loads((root / "configs/stage3_3_target_conditioned_receding_horizon_mpc_250ms.json").read_text(encoding="utf-8"))
tracking = dict(config["gate"]["ip_tracking"])
revision = tracking.pop("revision", None)
if tracking != expected_tolerances or revision != "2x_for_tsc_additional_heating":
    raise SystemExit("Stage3.3 config does not contain the requested doubled Ip tracking gate")
if float(config["gate"]["ip_safety_tolerance_A"]) != 10000.0:
    raise SystemExit("10 kA Ip safety gate must remain unchanged")
if config["refinement"].get("model_revision") != expected_refinement_revision:
    raise SystemExit("Stage3.3 config does not contain the audited refinement model revision")
if manifest.get("initial_state_robustness_validated"):
    raise SystemExit("package manifest must not claim initial-state robustness")
if manifest.get("plant_parameter_robustness_validated"):
    raise SystemExit("package manifest must not claim plant-parameter robustness")
if manifest.get("noise_delay_robustness_validated"):
    raise SystemExit("package manifest must not claim noise/delay robustness")
if manifest.get("residual_rl_primary_controller"):
    raise SystemExit("residual RL must not be the primary Stage3.3 controller")
print("[Stage3.3 verify] package manifest and doubled Ip-tracking guardrails passed.")
PY
