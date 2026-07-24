#!/usr/bin/env bash
set -euo pipefail
export TERM="${TERM:-dumb}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage3_4_shell_common.sh
source "${SCRIPT_DIR}/scripts/stage3_4_shell_common.sh"
stage34_project_init
stage34_find_python

required=(
  "configs/stage2_svd3_real_tsc_cem_100ms.json"
  "configs/stage2_1_svd3_dual_archive_tail_cem_100ms.json"
  "configs/stage2_2_svd3_corner_feasibility_100ms.json"
  "configs/stage3_0_svd3_tail_sqp_150ms.json"
  "configs/stage3_1_svd3_adaptive_sqp_causal_mpc_150ms.json"
  "configs/stage3_2_svd3_margin_long_hold_causal_mpc_250ms.json"
  "configs/stage3_3_target_conditioned_receding_horizon_mpc_250ms.json"
  "configs/stage3_4_late_arrival_continuation_mpc_350ms.json"
  "scripts/stage3_4_late_arrival_continuation_mpc.py"
  "scripts/stage3_4_shell_common.sh"
  "tsc_rzip_rllib/diagnostics/stage1_controllability.py"
  "tsc_rzip_rllib/diagnostics/stage2_trajectory_optimization.py"
  "tsc_rzip_rllib/diagnostics/stage2_1_trajectory_optimization.py"
  "tsc_rzip_rllib/diagnostics/stage2_2_trajectory_optimization.py"
  "tsc_rzip_rllib/diagnostics/stage3_0_tail_sqp.py"
  "tsc_rzip_rllib/diagnostics/stage3_1_adaptive_sqp_mpc.py"
  "tsc_rzip_rllib/diagnostics/stage3_2_margin_long_hold_mpc.py"
  "tsc_rzip_rllib/diagnostics/stage3_3_target_conditioned_mpc.py"
  "tsc_rzip_rllib/diagnostics/stage3_4_late_arrival_continuation_mpc.py"
  "tsc_rzip_rllib/utils/ray_runtime.py"
  "tests/test_ray_runtime_capacity.py"
  "tests/test_stage3_4_late_arrival_continuation_mpc.py"
  "tsc_rzip_rllib/envs/rzip_env.py"
)
for relative in "${required[@]}"; do
  [[ -f "${PROJECT_DIR}/${relative}" ]] || stage34_die "standalone package is incomplete: ${relative}"
done

"${PYTHON_BIN}" -u "${PROJECT_DIR}/scripts/stage2_trajectory_optimization.py" self-test
"${PYTHON_BIN}" -u "${PROJECT_DIR}/scripts/stage2_1_trajectory_optimization.py" self-test
"${PYTHON_BIN}" -u "${PROJECT_DIR}/scripts/stage2_2_trajectory_optimization.py" self-test
"${PYTHON_BIN}" -u "${PROJECT_DIR}/scripts/stage3_0_tail_sqp.py" self-test
"${PYTHON_BIN}" -u "${PROJECT_DIR}/scripts/stage3_1_adaptive_sqp_mpc.py" \
  --config "${PROJECT_DIR}/configs/stage3_1_svd3_adaptive_sqp_causal_mpc_150ms.json" \
  --command self-test --backend serial
"${PYTHON_BIN}" -u "${PROJECT_DIR}/scripts/stage3_2_margin_long_hold_mpc.py" \
  --config "${PROJECT_DIR}/configs/stage3_2_svd3_margin_long_hold_causal_mpc_250ms.json" \
  --command self-test --backend serial
"${PYTHON_BIN}" -u "${PROJECT_DIR}/scripts/stage3_3_target_conditioned_mpc.py" \
  --config "${PROJECT_DIR}/configs/stage3_3_target_conditioned_receding_horizon_mpc_250ms.json" \
  --command self-test --backend serial
"${PYTHON_BIN}" -u "${PROJECT_DIR}/scripts/stage3_4_late_arrival_continuation_mpc.py" \
  --config "${PROJECT_DIR}/configs/stage3_4_late_arrival_continuation_mpc_350ms.json" \
  --command self-test --backend serial

"${PYTHON_BIN}" -m compileall -q \
  "${PROJECT_DIR}/scripts" "${PROJECT_DIR}/tests" "${PROJECT_DIR}/tsc_rzip_rllib"

"${PYTHON_BIN}" - "${PROJECT_DIR}" <<'PY'
from pathlib import Path
import json
import sys
root = Path(sys.argv[1])
for path in sorted((root / "configs").glob("*.json")):
    json.loads(path.read_text(encoding="utf-8"))
print("[Stage3.4 self-test] JSON parsing passed.")
PY

"${PYTHON_BIN}" -m unittest discover -s "${PROJECT_DIR}/tests" -p 'test_*.py' -v

echo "[Stage3.4 self-test] standalone tree, compilation, inherited Stage2-Stage3.3 bases, Stage3.4, and all unit tests passed."
