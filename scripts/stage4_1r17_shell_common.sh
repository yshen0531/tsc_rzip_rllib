#!/usr/bin/env bash
set -euo pipefail

STAGE4_1R17_PROJECT_DIR="${STAGE4_1R17_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_1R17_CONFIG="${STAGE4_1R17_CONFIG:-${STAGE4_1R17_PROJECT_DIR}/configs/stage4_1r17_original_deadline_one_sided_robust_braking_closure_370ms.json}"
STAGE4_1R17_PYTHON="${STAGE4_1R17_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_1R17_WORKERS="${STAGE4_1R17_WORKERS:-128}"
STAGE4_1R17_BACKEND="${STAGE4_1R17_BACKEND:-ray}"
STAGE4_1R17_COMMAND="${STAGE4_1R17_COMMAND:-all}"
STAGE4_1R17_RESUME="${STAGE4_1R17_RESUME:-0}"
STAGE4_1R17_OUTPUT_ROOT="${STAGE4_1R17_OUTPUT_ROOT:-${STAGE4_1R17_PROJECT_DIR}/stage4_1r17_runs}"
STAGE4_1R17_TSC_WORKSPACE_ROOT="${STAGE4_1R17_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
STAGE4_1R17_TSC_RUN_ROOT="${STAGE4_1R17_TSC_RUN_ROOT:-${STAGE4_1R17_TSC_WORKSPACE_ROOT}/episode_runs}"
RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage4_1r17_${UID:-0}}"

stage4_1r17_source_r16_complete() {
  local source="$1" required raw_count
  for required in \
    stage4_1r16_manifest.json \
    stage4_1r16_state.json \
    stage4_1r16_config.resolved.json \
    stage4_1r16_analysis/stage4_1r16_verdict.json \
    stage4_1r16_analysis/stage4_1r16_summary.json \
    stage4_1r16_source_audit/summary.json \
    stage4_1r16_source_audit/model_feasibility.csv \
    stage4_1r16_amplitude_envelope_validation/summary.json \
    stage4_1r16_amplitude_envelope_validation/results.json \
    stage4_1r16_amplitude_envelope_validation/results.csv \
    stage4_1r16_amplitude_envelope_validation/central_symmetry.csv \
    stage4_1r16_amplitude_envelope_validation/per_unit_scaling.csv \
    stage4_1r16_amplitude_envelope_validation/closure_candidate.csv; do
    [[ -f "${source}/${required}" ]] || return 1
  done
  raw_count="$(find "${source}/stage4_1r16_amplitude_envelope_validation/raw" -maxdepth 1 -type f -name '*.json.gz' 2>/dev/null | wc -l)"
  [[ "${raw_count}" -eq 32 ]]
}

stage4_1r17_find_source_r16() {
  local explicit="${STAGE4_1R17_SOURCE_STAGE4_1R16_RUN:-}"
  if [[ -n "${explicit}" ]]; then
    [[ -d "${explicit}" ]] || { echo "ERROR: explicit R16 source directory missing: ${explicit}" >&2; return 1; }
    stage4_1r17_source_r16_complete "${explicit}" || { echo "ERROR: explicit R16 source is incomplete or raw coverage is not 32/32: ${explicit}" >&2; return 1; }
    printf '%s\n' "${explicit}"
    return 0
  fi
  local latest_file="${STAGE4_1R17_PROJECT_DIR}/stage4_1r16_runs/latest_stage4_1r16_run.txt"
  if [[ -f "${latest_file}" ]]; then
    local candidate
    candidate="$(tr -d '\r\n' < "${latest_file}")"
    if [[ -d "${candidate}" ]] && stage4_1r17_source_r16_complete "${candidate}"; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  fi
  local candidate
  while IFS= read -r candidate; do
    if stage4_1r17_source_r16_complete "${candidate}"; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done < <(find "${STAGE4_1R17_PROJECT_DIR}/stage4_1r16_runs" -mindepth 1 -maxdepth 1 -type d -name 'stage4_1r16_amplitude_certified_probe_derived_braking_closure_*' -print 2>/dev/null | sort -r)
  return 1
}

stage4_1r17_new_run_dir() {
  mkdir -p "${STAGE4_1R17_OUTPUT_ROOT}"
  local stamp
  stamp="$(date -u +%Y%m%d_%H%M%S)"
  printf '%s\n' "${STAGE4_1R17_OUTPUT_ROOT}/stage4_1r17_original_deadline_one_sided_robust_braking_closure_${stamp}"
}

stage4_1r17_validate_common() {
  [[ -x "${STAGE4_1R17_PYTHON}" ]] || { echo "ERROR: Python not executable: ${STAGE4_1R17_PYTHON}" >&2; return 1; }
  [[ -f "${STAGE4_1R17_CONFIG}" ]] || { echo "ERROR: config missing: ${STAGE4_1R17_CONFIG}" >&2; return 1; }
  [[ "${STAGE4_1R17_WORKERS}" =~ ^[1-9][0-9]*$ ]] || { echo "ERROR: workers must be positive" >&2; return 1; }
  [[ "${STAGE4_1R17_BACKEND}" == ray || "${STAGE4_1R17_BACKEND}" == serial ]] || { echo "ERROR: backend must be ray or serial" >&2; return 1; }
  [[ "${STAGE4_1R17_RESUME}" == 0 || "${STAGE4_1R17_RESUME}" == 1 ]] || { echo "ERROR: resume must be 0 or 1" >&2; return 1; }
  case "${STAGE4_1R17_COMMAND}" in
    all|audit|oracle|calibrated|grid) ;;
    *) echo "ERROR: invalid command ${STAGE4_1R17_COMMAND}" >&2; return 1 ;;
  esac
}

stage4_1r17_export_runtime() {
  export PROJECT_DIR="${STAGE4_1R17_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_1R17_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  export STAGE4_1R17_WORKERS STAGE4_1R17_TSC_WORKSPACE_ROOT STAGE4_1R17_TSC_RUN_ROOT RAY_TMPDIR
  local suffix
  for suffix in R16 R15B R15 R14 R13 R12 R11 R10 R9 R8 R7 R6 R5 R4; do
    export "STAGE4_1${suffix}_TSC_WORKSPACE_ROOT=${STAGE4_1R17_TSC_WORKSPACE_ROOT}"
    export "STAGE4_1${suffix}_TSC_RUN_ROOT=${STAGE4_1R17_TSC_RUN_ROOT}"
  done
  mkdir -p "${RAY_TMPDIR}" "${STAGE4_1R17_TSC_RUN_ROOT}"
}
