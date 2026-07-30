#!/usr/bin/env bash
set -euo pipefail

STAGE4_2R3C3T1_PROJECT_DIR="${STAGE4_2R3C3T1_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_2R3C3T1_CONFIG="${STAGE4_2R3C3T1_CONFIG:-${STAGE4_2R3C3T1_PROJECT_DIR}/configs/stage4_2r3c3t1_long_separation_zero_net_transport_identification_370ms.json}"
STAGE4_2R3C3T1_PYTHON="${STAGE4_2R3C3T1_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_2R3C3T1_WORKERS="${STAGE4_2R3C3T1_WORKERS:-128}"
STAGE4_2R3C3T1_BACKEND="${STAGE4_2R3C3T1_BACKEND:-ray}"
STAGE4_2R3C3T1_COMMAND="${STAGE4_2R3C3T1_COMMAND:-all}"
STAGE4_2R3C3T1_RESUME="${STAGE4_2R3C3T1_RESUME:-0}"
STAGE4_2R3C3T1_OUTPUT_ROOT="${STAGE4_2R3C3T1_OUTPUT_ROOT:-${STAGE4_2R3C3T1_PROJECT_DIR}/stage4_2r3c3t1_runs}"
STAGE4_2R3C3T1_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T1_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
STAGE4_2R3C3T1_TSC_RUN_ROOT="${STAGE4_2R3C3T1_TSC_RUN_ROOT:-${STAGE4_2R3C3T1_TSC_WORKSPACE_ROOT}/episode_runs}"
RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage4_2r3c3t1_${UID:-0}}"

# Reuse the already audited exact-source locators without changing R3c3.
STAGE4_2R3C3_PROJECT_DIR="${STAGE4_2R3C3T1_PROJECT_DIR}"
# shellcheck source=scripts/stage4_2r3c3_shell_common.sh
source "${STAGE4_2R3C3T1_PROJECT_DIR}/scripts/stage4_2r3c3_shell_common.sh"

stage4_2r3c3t1_find_source_r3b() {
  stage4_2r3c3_find_source_r3b
}

stage4_2r3c3t1_find_source_r3c3() {
  local fixed_name source raw_count
  fixed_name="stage4_2r3c3_restart_task_clock_local_response_identification_20260730_182427"
  source="${STAGE4_2R3C3T1_PROJECT_DIR}/stage4_2r3c3_runs/${fixed_name}"
  for required in \
    stage4_2r3c3_manifest.json \
    stage4_2r3c3_state.json \
    stage4_2r3c3_config.resolved.json \
    stage4_2r3c3_restart_task_clock_probe_identification/results.json \
    stage4_2r3c3_restart_task_clock_probe_identification/summary.json \
    stage4_2r3c3_analysis/stage4_2r3c3_verdict.json; do
    [[ -f "${source}/${required}" ]] || {
      echo "ERROR: exact Stage4.2R3c3 evidence missing: ${source}/${required}" >&2
      return 1
    }
  done
  raw_count="$(
    find "${source}/stage4_2r3c3_restart_task_clock_probe_identification/raw" \
      -maxdepth 1 -type f -name '*.json.gz' 2>/dev/null | wc -l
  )"
  [[ "${raw_count}" -eq 256 ]] || {
    echo "ERROR: exact Stage4.2R3c3 raw count is ${raw_count}, expected 256" >&2
    return 1
  }
  printf '%s\n' "${source}"
}

stage4_2r3c3t1_find_source_bank() {
  local source
  source="${STAGE4_2R3C3T1_PROJECT_DIR}/stage4_2r3c4_response_bank"
  for required in \
    stage4_2r3c3_compact_response_audit_bank_v1.json \
    stage4_2r3c3_controller_response_bank_v1.json \
    stage4_2r3c3_compact_response_bank_manifest_v1.json; do
    [[ -f "${source}/${required}" ]] || {
      echo "ERROR: exact Stage4.2R3c3 response bank missing: ${source}/${required}" >&2
      return 1
    }
  done
  printf '%s\n' "${source}"
}

stage4_2r3c3t1_new_run_dir() {
  mkdir -p "${STAGE4_2R3C3T1_OUTPUT_ROOT}"
  local stamp
  stamp="$(date -u +%Y%m%d_%H%M%S)"
  printf '%s\n' \
    "${STAGE4_2R3C3T1_OUTPUT_ROOT}/stage4_2r3c3t1_long_separation_zero_net_transport_identification_${stamp}"
}

stage4_2r3c3t1_validate_common() {
  [[ -x "${STAGE4_2R3C3T1_PYTHON}" ]] || {
    echo "ERROR: Python not executable: ${STAGE4_2R3C3T1_PYTHON}" >&2
    return 1
  }
  [[ -f "${STAGE4_2R3C3T1_CONFIG}" ]] || {
    echo "ERROR: config missing: ${STAGE4_2R3C3T1_CONFIG}" >&2
    return 1
  }
  [[ "${STAGE4_2R3C3T1_WORKERS}" == "128" ]] || {
    echo "ERROR: Stage4.2R3c3T1 Ray capacity is frozen at 128 workers" >&2
    return 1
  }
  [[ "${STAGE4_2R3C3T1_BACKEND}" == ray || "${STAGE4_2R3C3T1_BACKEND}" == serial ]] || {
    echo "ERROR: backend must be ray or serial" >&2
    return 1
  }
  [[ "${STAGE4_2R3C3T1_RESUME}" == 0 || "${STAGE4_2R3C3T1_RESUME}" == 1 ]] || {
    echo "ERROR: resume must be 0 or 1" >&2
    return 1
  }
  case "${STAGE4_2R3C3T1_COMMAND}" in
    all|offline) ;;
    *) echo "ERROR: invalid command ${STAGE4_2R3C3T1_COMMAND}" >&2; return 1 ;;
  esac
}

stage4_2r3c3t1_export_runtime() {
  export PROJECT_DIR="${STAGE4_2R3C3T1_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_2R3C3T1_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  export STAGE4_2R3C3T1_WORKERS
  export STAGE4_2R3C3T1_TSC_WORKSPACE_ROOT
  export STAGE4_2R3C3T1_TSC_RUN_ROOT
  export RAY_TMPDIR
  STAGE4_2R3C3_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T1_TSC_WORKSPACE_ROOT}"
  STAGE4_2R3C3_TSC_RUN_ROOT="${STAGE4_2R3C3T1_TSC_RUN_ROOT}"
  stage4_2r3c3_export_runtime
}
