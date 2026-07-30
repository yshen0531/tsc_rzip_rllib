#!/usr/bin/env bash
set -euo pipefail

STAGE4_2R3C1_PROJECT_DIR="${STAGE4_2R3C1_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_2R3C1_CONFIG="${STAGE4_2R3C1_CONFIG:-${STAGE4_2R3C1_PROJECT_DIR}/configs/stage4_2r3c1_authenticated_visible_manifold_phase_mpc_370ms.json}"
STAGE4_2R3C1_PYTHON="${STAGE4_2R3C1_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_2R3C1_WORKERS="${STAGE4_2R3C1_WORKERS:-128}"
STAGE4_2R3C1_BACKEND="${STAGE4_2R3C1_BACKEND:-ray}"
STAGE4_2R3C1_COMMAND="${STAGE4_2R3C1_COMMAND:-all}"
STAGE4_2R3C1_RESUME="${STAGE4_2R3C1_RESUME:-0}"
STAGE4_2R3C1_OUTPUT_ROOT="${STAGE4_2R3C1_OUTPUT_ROOT:-${STAGE4_2R3C1_PROJECT_DIR}/stage4_2r3c1_runs}"
STAGE4_2R3C1_TSC_WORKSPACE_ROOT="${STAGE4_2R3C1_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
STAGE4_2R3C1_TSC_RUN_ROOT="${STAGE4_2R3C1_TSC_RUN_ROOT:-${STAGE4_2R3C1_TSC_WORKSPACE_ROOT}/episode_runs}"
RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage4_2r3c1_${UID:-0}}"

stage4_2r3c1_source_r3b_complete() {
  local source="$1" state_count control_count
  for required in \
    stage4_2r3b_manifest.json \
    stage4_2r3b_state.json \
    stage4_2r3b_config.resolved.json \
    stage4_2r3b_pair_analysis/selected_pairs.json \
    stage4_2r3b_pair_analysis/summary.json \
    stage4_2r3b_hidden_history_control/results.json \
    stage4_2r3b_hidden_history_control/summary.json \
    stage4_2r3b_analysis/stage4_2r3b_verdict.json; do
    [[ -f "${source}/${required}" ]] || return 1
  done
  state_count="$(
    find "${source}/stage4_2r3b_state_generation/raw" \
      -maxdepth 1 -type f -name '*.json.gz' 2>/dev/null | wc -l
  )"
  control_count="$(
    find "${source}/stage4_2r3b_hidden_history_control/raw" \
      -maxdepth 1 -type f -name '*.json.gz' 2>/dev/null | wc -l
  )"
  [[ "${state_count}" -eq 72 && "${control_count}" -eq 32 ]]
}

stage4_2r3c1_find_source_r3b() {
  local explicit="${STAGE4_2R3C1_SOURCE_STAGE4_2R3B_RUN:-}"
  local fixed_name source
  fixed_name="stage4_2r3b_confirmatory_hidden_history_initial_state_20260730_115526"
  if [[ -n "${explicit}" ]]; then
    source="${explicit}"
  else
    source="${STAGE4_2R3C1_PROJECT_DIR}/stage4_2r3b_runs/${fixed_name}"
  fi
  [[ "$(basename "${source}")" == "${fixed_name}" ]] || {
    echo "ERROR: Stage4.2R3c1 source R3b identity changed: ${source}" >&2
    return 1
  }
  stage4_2r3c1_source_r3b_complete "${source}" || {
    echo "ERROR: exact Stage4.2R3b source is incomplete: ${source}" >&2
    return 1
  }
  local audit
  audit="${STAGE4_2R3C1_PROJECT_DIR}/stage4_2r3b_audits/${fixed_name}"
  for required in \
    stage4_2r3b_run_inventory.json \
    stage4_2r3b_server_audit.json \
    stage4_2r3b_raw_control_forensics.json \
    stage4_2r3b_snapshot_checks.json; do
    [[ -f "${audit}/${required}" ]] || {
      echo "ERROR: Stage4.2R3b source audit missing: ${audit}/${required}" >&2
      return 1
    }
  done
  printf '%s\n' "${source}"
}

stage4_2r3c1_find_source_r3c() {
  local fixed_name source audit raw_count
  fixed_name="stage4_2r3c_visible_state_phase_aligned_mpc_20260730_132807"
  source="${STAGE4_2R3C1_PROJECT_DIR}/stage4_2r3c_runs/${fixed_name}"
  audit="${STAGE4_2R3C1_PROJECT_DIR}/stage4_2r3c_audits/${fixed_name}"
  for required in \
    stage4_2r3c_manifest.json \
    stage4_2r3c_state.json \
    stage4_2r3c_config.resolved.json \
    stage4_2r3c_phase_aligned_control/results.json \
    stage4_2r3c_phase_aligned_control/summary.json \
    stage4_2r3c_analysis/stage4_2r3c_verdict.json; do
    [[ -f "${source}/${required}" ]] || {
      echo "ERROR: exact Stage4.2R3c evidence missing: ${source}/${required}" >&2
      return 1
    }
  done
  raw_count="$(
    find "${source}/stage4_2r3c_phase_aligned_control/raw" \
      -maxdepth 1 -type f -name '*.json.gz' 2>/dev/null | wc -l
  )"
  [[ "${raw_count}" -eq 32 ]] || {
    echo "ERROR: exact Stage4.2R3c raw count is ${raw_count}, expected 32" >&2
    return 1
  }
  for required in \
    stage4_2r3c_run_inventory.json \
    stage4_2r3c_server_audit.json \
    stage4_2r3c_raw_control_forensics.json; do
    [[ -f "${audit}/${required}" ]] || {
      echo "ERROR: exact Stage4.2R3c audit missing: ${audit}/${required}" >&2
      return 1
    }
  done
  printf '%s\n' "${source}"
}

stage4_2r3c1_new_run_dir() {
  mkdir -p "${STAGE4_2R3C1_OUTPUT_ROOT}"
  local stamp
  stamp="$(date -u +%Y%m%d_%H%M%S)"
  printf '%s\n' \
    "${STAGE4_2R3C1_OUTPUT_ROOT}/stage4_2r3c1_authenticated_visible_manifold_phase_mpc_${stamp}"
}

stage4_2r3c1_validate_common() {
  [[ -x "${STAGE4_2R3C1_PYTHON}" ]] || {
    echo "ERROR: Python not executable: ${STAGE4_2R3C1_PYTHON}" >&2
    return 1
  }
  [[ -f "${STAGE4_2R3C1_CONFIG}" ]] || {
    echo "ERROR: config missing: ${STAGE4_2R3C1_CONFIG}" >&2
    return 1
  }
  [[ "${STAGE4_2R3C1_WORKERS}" == "128" ]] || {
    echo "ERROR: Stage4.2R3c1 Ray capacity is frozen at 128 workers" >&2
    return 1
  }
  [[ "${STAGE4_2R3C1_BACKEND}" == ray || "${STAGE4_2R3C1_BACKEND}" == serial ]] || {
    echo "ERROR: backend must be ray or serial" >&2
    return 1
  }
  [[ "${STAGE4_2R3C1_RESUME}" == 0 || "${STAGE4_2R3C1_RESUME}" == 1 ]] || {
    echo "ERROR: resume must be 0 or 1" >&2
    return 1
  }
  case "${STAGE4_2R3C1_COMMAND}" in
    all|offline) ;;
    *) echo "ERROR: invalid command ${STAGE4_2R3C1_COMMAND}" >&2; return 1 ;;
  esac
}

stage4_2r3c1_export_runtime() {
  export PROJECT_DIR="${STAGE4_2R3C1_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_2R3C1_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  export STAGE4_2R3C1_WORKERS STAGE4_2R3C1_TSC_WORKSPACE_ROOT
  export STAGE4_2R3C1_TSC_RUN_ROOT RAY_TMPDIR
  local suffix
  for suffix in R17 R16 R15B R15 R14 R13 R12 R11 R10 R9 R8 R7 R6 R5 R4; do
    export "STAGE4_1${suffix}_TSC_WORKSPACE_ROOT=${STAGE4_2R3C1_TSC_WORKSPACE_ROOT}"
    export "STAGE4_1${suffix}_TSC_RUN_ROOT=${STAGE4_2R3C1_TSC_RUN_ROOT}"
  done
  export STAGE4_2R1_TSC_WORKSPACE_ROOT="${STAGE4_2R3C1_TSC_WORKSPACE_ROOT}"
  export STAGE4_2R1_TSC_RUN_ROOT="${STAGE4_2R3C1_TSC_RUN_ROOT}"
  export STAGE4_2R2_TSC_WORKSPACE_ROOT="${STAGE4_2R3C1_TSC_WORKSPACE_ROOT}"
  export STAGE4_2R2_TSC_RUN_ROOT="${STAGE4_2R3C1_TSC_RUN_ROOT}"
  export STAGE4_2R3B_TSC_WORKSPACE_ROOT="${STAGE4_2R3C1_TSC_WORKSPACE_ROOT}"
  export STAGE4_2R3B_TSC_RUN_ROOT="${STAGE4_2R3C1_TSC_RUN_ROOT}"
  mkdir -p "${RAY_TMPDIR}" "${STAGE4_2R3C1_TSC_RUN_ROOT}"
}
