#!/usr/bin/env bash
set -euo pipefail

STAGE4_2R3C3T2_PROJECT_DIR="${STAGE4_2R3C3T2_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_2R3C3T2_CONFIG="${STAGE4_2R3C3T2_CONFIG:-${STAGE4_2R3C3T2_PROJECT_DIR}/configs/stage4_2r3c3t2_post_contract_neutralized_held_transport_identification_500ms.json}"
STAGE4_2R3C3T2_PYTHON="${STAGE4_2R3C3T2_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_2R3C3T2_WORKERS="${STAGE4_2R3C3T2_WORKERS:-128}"
STAGE4_2R3C3T2_BACKEND="${STAGE4_2R3C3T2_BACKEND:-ray}"
STAGE4_2R3C3T2_COMMAND="${STAGE4_2R3C3T2_COMMAND:-all}"
STAGE4_2R3C3T2_RESUME="${STAGE4_2R3C3T2_RESUME:-0}"
STAGE4_2R3C3T2_OUTPUT_ROOT="${STAGE4_2R3C3T2_OUTPUT_ROOT:-${STAGE4_2R3C3T2_PROJECT_DIR}/stage4_2r3c3t2_runs}"
STAGE4_2R3C3T2_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T2_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
STAGE4_2R3C3T2_TSC_RUN_ROOT="${STAGE4_2R3C3T2_TSC_RUN_ROOT:-${STAGE4_2R3C3T2_TSC_WORKSPACE_ROOT}/episode_runs}"
RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage4_2r3c3t2_${UID:-0}}"

STAGE4_2R3C3T1_PROJECT_DIR="${STAGE4_2R3C3T2_PROJECT_DIR}"
# shellcheck source=scripts/stage4_2r3c3t1_shell_common.sh
source "${STAGE4_2R3C3T2_PROJECT_DIR}/scripts/stage4_2r3c3t1_shell_common.sh"

stage4_2r3c3t2_find_source_r3b() {
  stage4_2r3c3t1_find_source_r3b
}

stage4_2r3c3t2_find_source_r3c3() {
  stage4_2r3c3t1_find_source_r3c3
}

stage4_2r3c3t2_find_source_bank() {
  stage4_2r3c3t1_find_source_bank
}

stage4_2r3c3t2_find_source_t1() {
  local source raw_count
  source="${STAGE4_2R3C3T2_PROJECT_DIR}/stage4_2r3c3t1_runs/stage4_2r3c3t1_long_separation_zero_net_transport_identification_20260730_204441"
  for required in \
    stage4_2r3c3t1_manifest.json \
    stage4_2r3c3t1_state.json \
    stage4_2r3c3t1_transport_response_identification/summary.json \
    stage4_2r3c3t1_analysis/stage4_2r3c3t1_verdict.json; do
    [[ -f "${source}/${required}" ]] || {
      echo "ERROR: exact Stage4.2R3c3T1 evidence missing: ${source}/${required}" >&2
      return 1
    }
  done
  raw_count="$(
    find "${source}/stage4_2r3c3t1_transport_response_identification/raw" \
      -maxdepth 1 -type f -name '*.json.gz' 2>/dev/null | wc -l
  )"
  [[ "${raw_count}" -eq 128 ]] || {
    echo "ERROR: exact Stage4.2R3c3T1 raw count is ${raw_count}, expected 128" >&2
    return 1
  }
  printf '%s\n' "${source}"
}

stage4_2r3c3t2_find_source_t1_audit() {
  local source
  source="${STAGE4_2R3C3T2_PROJECT_DIR}/stage4_2r3c3t1_audits/stage4_2r3c3t1_long_separation_zero_net_transport_identification_20260730_204441"
  for required in \
    stage4_2r3c3t1_server_audit.json \
    stage4_2r3c3t1_six_basis_feasibility_diagnostic_v2.json; do
    [[ -f "${source}/${required}" ]] || {
      echo "ERROR: exact Stage4.2R3c3T1 audit missing: ${source}/${required}" >&2
      return 1
    }
  done
  printf '%s\n' "${source}"
}

stage4_2r3c3t2_new_run_dir() {
  mkdir -p "${STAGE4_2R3C3T2_OUTPUT_ROOT}"
  local stamp
  stamp="$(date -u +%Y%m%d_%H%M%S)"
  printf '%s\n' \
    "${STAGE4_2R3C3T2_OUTPUT_ROOT}/stage4_2r3c3t2_post_contract_neutralized_held_transport_identification_${stamp}"
}

stage4_2r3c3t2_validate_common() {
  [[ -x "${STAGE4_2R3C3T2_PYTHON}" ]] || {
    echo "ERROR: Python not executable: ${STAGE4_2R3C3T2_PYTHON}" >&2
    return 1
  }
  [[ -f "${STAGE4_2R3C3T2_CONFIG}" ]] || {
    echo "ERROR: config missing: ${STAGE4_2R3C3T2_CONFIG}" >&2
    return 1
  }
  [[ "${STAGE4_2R3C3T2_WORKERS}" == "128" ]] || {
    echo "ERROR: Stage4.2R3c3T2 Ray capacity is frozen at 128 workers" >&2
    return 1
  }
  [[ "${STAGE4_2R3C3T2_BACKEND}" == ray || "${STAGE4_2R3C3T2_BACKEND}" == serial ]] || {
    echo "ERROR: backend must be ray or serial" >&2
    return 1
  }
  [[ "${STAGE4_2R3C3T2_RESUME}" == 0 || "${STAGE4_2R3C3T2_RESUME}" == 1 ]] || {
    echo "ERROR: resume must be 0 or 1" >&2
    return 1
  }
  case "${STAGE4_2R3C3T2_COMMAND}" in
    all|offline) ;;
    *) echo "ERROR: invalid command ${STAGE4_2R3C3T2_COMMAND}" >&2; return 1 ;;
  esac
}

stage4_2r3c3t2_export_runtime() {
  export PROJECT_DIR="${STAGE4_2R3C3T2_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_2R3C3T2_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  export STAGE4_2R3C3T2_WORKERS
  export STAGE4_2R3C3T2_TSC_WORKSPACE_ROOT
  export STAGE4_2R3C3T2_TSC_RUN_ROOT
  export RAY_TMPDIR
  STAGE4_2R3C3T1_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T2_TSC_WORKSPACE_ROOT}"
  STAGE4_2R3C3T1_TSC_RUN_ROOT="${STAGE4_2R3C3T2_TSC_RUN_ROOT}"
  stage4_2r3c3t1_export_runtime
}
