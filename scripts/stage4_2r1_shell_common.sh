#!/usr/bin/env bash
set -euo pipefail

STAGE4_2R1_PROJECT_DIR="${STAGE4_2R1_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_2R1_CONFIG="${STAGE4_2R1_CONFIG:-${STAGE4_2R1_PROJECT_DIR}/configs/stage4_2r1_true_tsc_plant_restart_action_replay_370ms.json}"
STAGE4_2R1_PYTHON="${STAGE4_2R1_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_2R1_WORKERS="${STAGE4_2R1_WORKERS:-128}"
STAGE4_2R1_BACKEND="${STAGE4_2R1_BACKEND:-ray}"
STAGE4_2R1_COMMAND="${STAGE4_2R1_COMMAND:-all}"
STAGE4_2R1_RESUME="${STAGE4_2R1_RESUME:-0}"
STAGE4_2R1_OUTPUT_ROOT="${STAGE4_2R1_OUTPUT_ROOT:-${STAGE4_2R1_PROJECT_DIR}/stage4_2r1_runs}"
STAGE4_2R1_TSC_WORKSPACE_ROOT="${STAGE4_2R1_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
STAGE4_2R1_TSC_RUN_ROOT="${STAGE4_2R1_TSC_RUN_ROOT:-${STAGE4_2R1_TSC_WORKSPACE_ROOT}/episode_runs}"
RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage4_2r1_${UID:-0}}"

stage4_2r1_source_r17_complete() {
  local source="$1" required oracle_count calibrated_count
  for required in \
    stage4_1r17_manifest.json \
    stage4_1r17_state.json \
    stage4_1r17_config.resolved.json \
    stage4_1r17_analysis/stage4_1r17_verdict.json \
    stage4_1r17_analysis/stage4_1r17_summary.json \
    stage4_1r17_source_audit/summary.json \
    stage4_1r17_oracle_candidate_validation/summary.json \
    stage4_1r17_oracle_candidate_validation/results.json \
    stage4_1r17_calibrated_confirmation/summary.json \
    stage4_1r17_calibrated_confirmation/results.json \
    stage4_1r17_formal_grid_confirmation/summary.json \
    stage4_1r17_formal_grid_confirmation/results.json; do
    [[ -f "${source}/${required}" ]] || return 1
  done
  oracle_count="$(find "${source}/stage4_1r17_oracle_candidate_validation/raw" -maxdepth 1 -type f -name '*.json.gz' 2>/dev/null | wc -l)"
  calibrated_count="$(find "${source}/stage4_1r17_calibrated_confirmation/raw" -maxdepth 1 -type f -name '*.json.gz' 2>/dev/null | wc -l)"
  [[ "${oracle_count}" -eq 2 && "${calibrated_count}" -eq 4 ]]
}

stage4_2r1_find_source_r17() {
  local explicit="${STAGE4_2R1_SOURCE_STAGE4_1R17_RUN:-}"
  if [[ -n "${explicit}" ]]; then
    [[ -d "${explicit}" ]] || { echo "ERROR: explicit R17 source directory missing: ${explicit}" >&2; return 1; }
    stage4_2r1_source_r17_complete "${explicit}" || { echo "ERROR: explicit R17 source is incomplete or raw coverage is not 2 Oracle + 4 calibrated: ${explicit}" >&2; return 1; }
    printf '%s\n' "${explicit}"
    return 0
  fi
  local latest_file="${STAGE4_2R1_PROJECT_DIR}/stage4_1r17_runs/latest_stage4_1r17_run.txt"
  if [[ -f "${latest_file}" ]]; then
    local candidate
    candidate="$(tr -d '\r\n' < "${latest_file}")"
    if [[ -d "${candidate}" ]] && stage4_2r1_source_r17_complete "${candidate}"; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  fi
  local candidate
  while IFS= read -r candidate; do
    if stage4_2r1_source_r17_complete "${candidate}"; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done < <(find "${STAGE4_2R1_PROJECT_DIR}/stage4_1r17_runs" -mindepth 1 -maxdepth 1 -type d -name 'stage4_1r17_original_deadline_one_sided_robust_braking_closure_*' -print 2>/dev/null | sort -r)
  return 1
}

stage4_2r1_new_run_dir() {
  mkdir -p "${STAGE4_2R1_OUTPUT_ROOT}"
  local stamp
  stamp="$(date -u +%Y%m%d_%H%M%S)"
  printf '%s\n' "${STAGE4_2R1_OUTPUT_ROOT}/stage4_2r1_true_tsc_plant_restart_action_replay_${stamp}"
}

stage4_2r1_validate_common() {
  [[ -x "${STAGE4_2R1_PYTHON}" ]] || { echo "ERROR: Python not executable: ${STAGE4_2R1_PYTHON}" >&2; return 1; }
  [[ -f "${STAGE4_2R1_CONFIG}" ]] || { echo "ERROR: config missing: ${STAGE4_2R1_CONFIG}" >&2; return 1; }
  [[ "${STAGE4_2R1_WORKERS}" =~ ^[1-9][0-9]*$ ]] || { echo "ERROR: STAGE4_2R1_WORKERS must be positive" >&2; return 1; }
  [[ "${STAGE4_2R1_BACKEND}" == ray || "${STAGE4_2R1_BACKEND}" == serial ]] || { echo "ERROR: backend must be ray or serial" >&2; return 1; }
  [[ "${STAGE4_2R1_RESUME}" == 0 || "${STAGE4_2R1_RESUME}" == 1 ]] || { echo "ERROR: resume must be 0 or 1" >&2; return 1; }
  case "${STAGE4_2R1_COMMAND}" in
    all|audit|capture|restart) ;;
    *) echo "ERROR: invalid command ${STAGE4_2R1_COMMAND}" >&2; return 1 ;;
  esac
}

stage4_2r1_export_runtime() {
  export PROJECT_DIR="${STAGE4_2R1_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_2R1_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  export STAGE4_2R1_WORKERS STAGE4_2R1_TSC_WORKSPACE_ROOT STAGE4_2R1_TSC_RUN_ROOT RAY_TMPDIR
  local suffix
  for suffix in R17 R16 R15B R15 R14 R13 R12 R11 R10 R9 R8 R7 R6 R5 R4; do
    export "STAGE4_1${suffix}_TSC_WORKSPACE_ROOT=${STAGE4_2R1_TSC_WORKSPACE_ROOT}"
    export "STAGE4_1${suffix}_TSC_RUN_ROOT=${STAGE4_2R1_TSC_RUN_ROOT}"
  done
  mkdir -p "${RAY_TMPDIR}" "${STAGE4_2R1_TSC_RUN_ROOT}"
}
