#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/stage4_1r7_shell_common.sh"
stage41r7_project_init
stage41r7_find_python
[[ -f "${PROJECT_DIR}/SHA256SUMS" ]] || stage41r7_die "SHA256SUMS is missing"
(cd "${PROJECT_DIR}" && sha256sum -c SHA256SUMS)
echo "[Stage4.1R7 verify] packaged file checksums passed."
"${PROJECT_DIR}/run_stage4_1r7_self_test.sh"
"${PYTHON_BIN}" - "${PROJECT_DIR}" <<'PY'
from pathlib import Path
import json
import subprocess
import sys
import numpy as np

root = Path(sys.argv[1])
manifest = json.loads((root / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
cfg = json.loads((root / manifest["main_config"]).read_text(encoding="utf-8"))
assert manifest["stage"] == "Stage4.1R7"
assert manifest["complete_standalone"] is True
assert manifest["lean_delivery"] is True
assert manifest["default_workers"] == 128
assert manifest["controller_revision"] == "precontrol_calibration_queue_consistent_startup_v7"
assert manifest["hard_gate_changed_from_stage4_1r6"] is False
assert manifest["precontrol_calibration"]["separate_reset_episode"] is True
assert manifest["queue_consistent_startup"]["primary_path_uses_online_handover"] is False
assert manifest["queue_consistent_startup"]["weak_slew_controller_variant"] == "control_aware_no_aw"
assert manifest["queue_bookkeeping_fix"]["issued_items_history_records_actual_queued_physical_increment"] is True
assert manifest["deployment_robustness_validated"] is False
assert cfg["controller_revision"] == manifest["controller_revision"]
assert cfg["parallel"]["n_workers"] == 128
cal = cfg["precontrol_calibration"]
plan = np.asarray(cal["mode_command_plan"], dtype=float)
assert plan.shape == (10, 3)
assert cal["calibration_plan_revision"] == "bounded_zero_net_snr_20mA_v2"
assert np.allclose(plan.sum(axis=0), 0.0, atol=1e-12)
assert np.allclose(plan[-2:], 0.0, atol=1e-12)
assert np.max(np.abs(plan[:, 0])) <= 0.72 + 1e-12
assert np.max(np.abs(plan[:, 1])) <= 0.60 + 1e-12
assert np.max(np.abs(plan[:, 2])) <= 0.24 + 1e-12
profiles = {item["profile_id"]: float(item["coil_current_measurement_noise_A"]) for item in cal["profiles"]}
assert profiles == {"clean": 0.0, "noisy_20mA": 0.02}
confidence = cfg["confidence_gate"]
assert confidence["minimum_confidence_ratio"] >= 5.0
assert confidence["consecutive_best_observations"] >= 2
assert confidence["require_unique_best"] is True
startup = cfg["queue_consistent_startup"]
assert startup["primary_path_uses_online_handover"] is False
assert startup["queue_primed_from_calibrated_model_before_first_main_action"] is True
assert startup["weak_slew_controller_variant"] == "control_aware_no_aw"
assert startup["anti_windup_enabled"] is False
assert startup["minimum_oracle_feasible_preservation"] == 1.0
assert startup["minimum_clean_trace_equivalence"] == 1.0
assert startup["minimum_clean_monitor_trace_equivalence"] == 1.0
assert startup["minimum_noisy_monitor_trace_equivalence"] == 1.0
confirmation = cfg["confirmation"]
assert confirmation["paired_calibration_and_main_control"] is True
assert confirmation["repeats_per_group"] == 2
assert confirmation["minimum_distinct_groups"] == 18
shells = [root / value for value in manifest["shell_files"]]
assert len(shells) == 6 and all(path.is_file() for path in shells)
for path in shells:
    subprocess.run(["bash", "-n", str(path)], check=True)
checksum_lines = [line for line in (root / "SHA256SUMS").read_text(encoding="utf-8").splitlines() if line.strip()]
assert len(checksum_lines) == manifest["packaged_file_count_excluding_checksum_file"]
# Deliberately do not scan or reject Markdown/Shell files left elsewhere in the
# server project.  Only files declared by this package are integrity-checked.
print("[Stage4.1R7 verify] package manifest and scientific guardrails passed; residual project Markdown files are ignored.")
PY
echo "[Stage4.1R7 verify] declared shell scripts passed bash -n; no Git, network, or external source-tree recovery is used."
