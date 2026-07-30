#!/usr/bin/env bash
set -euo pipefail

STAGE4_2R3_PROJECT_DIR="${STAGE4_2R3_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_2R3_CONFIG="${STAGE4_2R3_CONFIG:-${STAGE4_2R3_PROJECT_DIR}/configs/stage4_2r3_authentic_hidden_history_initial_state_370ms.json}"
STAGE4_2R3_PYTHON="${STAGE4_2R3_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_2R3_WORKERS="${STAGE4_2R3_WORKERS:-128}"
STAGE4_2R3_BACKEND="${STAGE4_2R3_BACKEND:-ray}"
STAGE4_2R3_COMMAND="${STAGE4_2R3_COMMAND:-all}"
STAGE4_2R3_RESUME="${STAGE4_2R3_RESUME:-0}"
STAGE4_2R3_OUTPUT_ROOT="${STAGE4_2R3_OUTPUT_ROOT:-${STAGE4_2R3_PROJECT_DIR}/stage4_2r3_runs}"
STAGE4_2R3_TSC_WORKSPACE_ROOT="${STAGE4_2R3_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
STAGE4_2R3_TSC_RUN_ROOT="${STAGE4_2R3_TSC_RUN_ROOT:-${STAGE4_2R3_TSC_WORKSPACE_ROOT}/episode_runs}"
RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage4_2r3_${UID:-0}}"

stage4_2r3_source_r2_complete() {
  local source="$1" replay_count
  for required in \
    stage4_2r2_manifest.json \
    stage4_2r2_state.json \
    stage4_2r2_config.resolved.json \
    stage4_2r2_analysis/stage4_2r2_verdict.json \
    stage4_2r2_analysis/stage4_2r2_summary.json \
    stage4_2r2_controller_checkpoint_bank/results.json \
    stage4_2r2_controller_checkpoint_bank/summary.json \
    stage4_2r2_offline_controller_recomputation_audit/summary.json \
    stage4_2r2_controller_restart_replay/results.json \
    stage4_2r2_controller_restart_replay/summary.json; do
    [[ -f "${source}/${required}" ]] || return 1
  done
  replay_count="$(
    find "${source}/stage4_2r2_controller_restart_replay/raw" \
      -maxdepth 1 -type f -name '*.json.gz' 2>/dev/null | wc -l
  )"
  [[ "${replay_count}" -eq 18 ]]
}

stage4_2r3_find_source_r2() {
  local explicit="${STAGE4_2R3_SOURCE_STAGE4_2R2_RUN:-}"
  if [[ -n "${explicit}" ]]; then
    [[ -d "${explicit}" ]] || {
      echo "ERROR: explicit Stage4.2R2 source directory missing: ${explicit}" >&2
      return 1
    }
    stage4_2r3_source_r2_complete "${explicit}" || {
      echo "ERROR: explicit Stage4.2R2 source is incomplete: ${explicit}" >&2
      return 1
    }
    printf '%s\n' "${explicit}"
    return 0
  fi
  local latest_file="${STAGE4_2R3_PROJECT_DIR}/stage4_2r2_runs/latest_stage4_2r2_run.txt"
  if [[ -f "${latest_file}" ]]; then
    local candidate
    candidate="$(tr -d '\r\n' < "${latest_file}")"
    if [[ -d "${candidate}" ]] && stage4_2r3_source_r2_complete "${candidate}"; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  fi
  local candidate
  while IFS= read -r candidate; do
    if stage4_2r3_source_r2_complete "${candidate}"; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done < <(
    find "${STAGE4_2R3_PROJECT_DIR}/stage4_2r2_runs" \
      -mindepth 1 -maxdepth 1 -type d \
      -name 'stage4_2r2_persistent_controller_checkpoint_replay_*' \
      -print 2>/dev/null | sort -r
  )
  return 1
}

stage4_2r3_new_run_dir() {
  mkdir -p "${STAGE4_2R3_OUTPUT_ROOT}"
  local stamp
  stamp="$(date -u +%Y%m%d_%H%M%S)"
  printf '%s\n' \
    "${STAGE4_2R3_OUTPUT_ROOT}/stage4_2r3_authentic_hidden_history_initial_state_${stamp}"
}

stage4_2r3_validate_common() {
  [[ -x "${STAGE4_2R3_PYTHON}" ]] || {
    echo "ERROR: Python not executable: ${STAGE4_2R3_PYTHON}" >&2
    return 1
  }
  [[ -f "${STAGE4_2R3_CONFIG}" ]] || {
    echo "ERROR: config missing: ${STAGE4_2R3_CONFIG}" >&2
    return 1
  }
  [[ "${STAGE4_2R3_WORKERS}" == "128" ]] || {
    echo "ERROR: Stage4.2R3 Ray capacity is frozen at 128 workers" >&2
    return 1
  }
  [[ "${STAGE4_2R3_BACKEND}" == ray || "${STAGE4_2R3_BACKEND}" == serial ]] || {
    echo "ERROR: backend must be ray or serial" >&2
    return 1
  }
  [[ "${STAGE4_2R3_RESUME}" == 0 || "${STAGE4_2R3_RESUME}" == 1 ]] || {
    echo "ERROR: resume must be 0 or 1" >&2
    return 1
  }
  case "${STAGE4_2R3_COMMAND}" in
    all|state) ;;
    *) echo "ERROR: invalid command ${STAGE4_2R3_COMMAND}" >&2; return 1 ;;
  esac
}

stage4_2r3_export_runtime() {
  export PROJECT_DIR="${STAGE4_2R3_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_2R3_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  export STAGE4_2R3_WORKERS STAGE4_2R3_TSC_WORKSPACE_ROOT
  export STAGE4_2R3_TSC_RUN_ROOT RAY_TMPDIR
  local suffix
  for suffix in R17 R16 R15B R15 R14 R13 R12 R11 R10 R9 R8 R7 R6 R5 R4; do
    export "STAGE4_1${suffix}_TSC_WORKSPACE_ROOT=${STAGE4_2R3_TSC_WORKSPACE_ROOT}"
    export "STAGE4_1${suffix}_TSC_RUN_ROOT=${STAGE4_2R3_TSC_RUN_ROOT}"
  done
  export STAGE4_2R1_TSC_WORKSPACE_ROOT="${STAGE4_2R3_TSC_WORKSPACE_ROOT}"
  export STAGE4_2R1_TSC_RUN_ROOT="${STAGE4_2R3_TSC_RUN_ROOT}"
  export STAGE4_2R2_TSC_WORKSPACE_ROOT="${STAGE4_2R3_TSC_WORKSPACE_ROOT}"
  export STAGE4_2R2_TSC_RUN_ROOT="${STAGE4_2R3_TSC_RUN_ROOT}"
  mkdir -p "${RAY_TMPDIR}" "${STAGE4_2R3_TSC_RUN_ROOT}"
}
