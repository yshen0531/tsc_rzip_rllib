#!/usr/bin/env bash
# Shared helpers for the complete standalone Stage3.2 launchers.
# No Git, network access, or external source-tree recovery is used.

stage32_die() { echo "ERROR: $*" >&2; exit 2; }

stage32_project_init() {
  local caller_dir
  caller_dir="$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd)"
  export PROJECT_DIR="${PROJECT_DIR:-${caller_dir}}"
  PROJECT_DIR="$(cd "${PROJECT_DIR}" && pwd)"
  export PROJECT_DIR
  export TSC_ALL_ROOT="${TSC_ALL_ROOT:-$(cd "${PROJECT_DIR}/.." && pwd)}"
  export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  cd "${PROJECT_DIR}"
}

stage32_find_python() {
  if [[ -n "${PYTHON_BIN:-}" ]]; then :
  elif [[ -x "${TSC_ALL_ROOT}/tsc_simulation/venv_simu/bin/python" ]]; then
    PYTHON_BIN="${TSC_ALL_ROOT}/tsc_simulation/venv_simu/bin/python"
  elif command -v python3 >/dev/null 2>&1; then PYTHON_BIN="$(command -v python3)"
  elif command -v python >/dev/null 2>&1; then PYTHON_BIN="$(command -v python)"
  else stage32_die "no Python interpreter found; set PYTHON_BIN=/absolute/path/to/python"
  fi
  [[ -x "${PYTHON_BIN}" ]] || stage32_die "Python interpreter is not executable: ${PYTHON_BIN}"
  export PYTHON_BIN
}

stage32_abspath() {
  local value="${1:-}"
  [[ -n "${value}" ]] || return 1
  "${PYTHON_BIN}" - "${PROJECT_DIR}" "${value}" <<'PY'
from pathlib import Path
import sys
root=Path(sys.argv[1]).resolve(); value=Path(sys.argv[2]).expanduser()
if not value.is_absolute(): value=root/value
print(value.resolve(strict=False))
PY
}

stage32_validate_stage31_source() {
  local run_dir="$1" relative
  [[ -d "${run_dir}" ]] || return 1
  local required=(
    "stage3_1_config.resolved.json"
    "stage3_1_manifest.json"
    "stage3_1_state.json"
    "stage3_1_analysis/all_results.json"
    "stage3_1_analysis/stage3_1_analysis_summary.json"
    "stage3_1_confirmations/stage3_1_verdict.json"
    "stage3_1_controller/mpc_poc_bundle.json"
    "stage3_1_best/best_candidate.json"
    "stage3_1_best/best_tsc_result.json.gz"
    "env_config.resolved.json"
    "train_config.resolved.json"
  )
  for relative in "${required[@]}"; do [[ -f "${run_dir}/${relative}" ]] || return 1; done
}

stage32_detect_source_stage31() {
  local candidate=""
  if [[ -n "${SOURCE_STAGE3_1_RUN:-}" ]]; then
    candidate="$(stage32_abspath "${SOURCE_STAGE3_1_RUN}")"
    stage32_validate_stage31_source "${candidate}" || stage32_die "SOURCE_STAGE3_1_RUN is incomplete: ${candidate}"
    SOURCE_STAGE3_1_RUN="${candidate}"; export SOURCE_STAGE3_1_RUN; return
  fi
  if [[ -f "${PROJECT_DIR}/stage3_1_runs/latest_stage3_1_run.txt" ]]; then
    candidate="$(head -n1 "${PROJECT_DIR}/stage3_1_runs/latest_stage3_1_run.txt" | tr -d '\r')"
    [[ -n "${candidate}" ]] && candidate="$(stage32_abspath "${candidate}")"
    if [[ -n "${candidate}" ]] && stage32_validate_stage31_source "${candidate}"; then
      SOURCE_STAGE3_1_RUN="${candidate}"; export SOURCE_STAGE3_1_RUN; return
    fi
  fi
  candidate="$("${PYTHON_BIN}" - "${PROJECT_DIR}" <<'PY'
from pathlib import Path
import sys
root=Path(sys.argv[1])/"stage3_1_runs"; items=[]
if root.is_dir():
  for p in root.glob("stage3_1_svd3_adaptive_sqp_causal_mpc_150ms_*"):
    req=(p/"stage3_1_config.resolved.json",p/"stage3_1_manifest.json",p/"stage3_1_state.json",p/"stage3_1_analysis/all_results.json",p/"stage3_1_confirmations/stage3_1_verdict.json",p/"stage3_1_controller/mpc_poc_bundle.json")
    if p.is_dir() and all(x.exists() for x in req): items.append((p.stat().st_mtime,p.resolve()))
if items: print(max(items)[1])
PY
)"
  [[ -n "${candidate}" ]] || stage32_die "no complete Stage3.1 source found. Set SOURCE_STAGE3_1_RUN=/absolute/path/to/run"
  SOURCE_STAGE3_1_RUN="${candidate}"; export SOURCE_STAGE3_1_RUN
}

stage32_source_from_existing_run() {
  local run_dir="$1" candidate
  candidate="$("${PYTHON_BIN}" - "${PROJECT_DIR}" "${run_dir}" <<'PY'
from pathlib import Path
import json,sys
project=Path(sys.argv[1]).resolve(); run=Path(sys.argv[2]).resolve(); p=run/"stage3_2_manifest.json"
if not p.is_file(): raise SystemExit(0)
data=json.loads(p.read_text()); raw=str(data.get("source_stage3_1_run","")).strip()
if not raw: raise SystemExit(0)
path=Path(raw).expanduser()
if not path.exists():
  fallback=project/"stage3_1_runs"/path.name
  if fallback.exists(): path=fallback
print(path.resolve(strict=False))
PY
)"
  if [[ -z "${SOURCE_STAGE3_1_RUN:-}" && -n "${candidate}" ]]; then
    SOURCE_STAGE3_1_RUN="${candidate}"; export SOURCE_STAGE3_1_RUN
  fi
}

stage32_resolve_existing_run() {
  local value="${STAGE3_2_RUN_DIR:-}"
  if [[ -z "${value}" && -f "${PROJECT_DIR}/stage3_2_runs/latest_stage3_2_run.txt" ]]; then
    value="$(head -n1 "${PROJECT_DIR}/stage3_2_runs/latest_stage3_2_run.txt" | tr -d '\r')"
  fi
  [[ -n "${value}" ]] || stage32_die "no Stage3.2 run selected; set STAGE3_2_RUN_DIR"
  value="$(stage32_abspath "${value}")"
  [[ -f "${value}/stage3_2_manifest.json" ]] || stage32_die "not a prepared Stage3.2 run: ${value}"
  STAGE3_2_RUN_DIR="${value}"; export STAGE3_2_RUN_DIR
}

stage32_find_ray_cli() {
  local candidate="$(dirname "${PYTHON_BIN}")/ray"
  if [[ -x "${candidate}" ]]; then printf '%s\n' "${candidate}"
  elif command -v ray >/dev/null 2>&1; then command -v ray
  else printf '%s\n' ""; fi
}

stage32_ray_stop() {
  local ray_cli; ray_cli="$(stage32_find_ray_cli)"
  if [[ -n "${ray_cli}" ]]; then "${ray_cli}" stop --force >/dev/null 2>&1 || true
  else "${PYTHON_BIN}" - <<'PY' >/dev/null 2>&1 || true
try:
 import ray; ray.shutdown()
except Exception: pass
PY
  fi
}

stage32_validate_tmp_path() {
  local value="$1" label="$2"
  [[ -n "${value}" && "${value}" == /tmp/* && "${value}" != /tmp && "${value}" != /tmp/ ]] || stage32_die "${label} must be below /tmp; got ${value}"
}

stage32_cleanup_runtime() {
  local workspace="${STAGE3_2_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
  local run_root="${STAGE3_2_TSC_RUN_ROOT:-${workspace}/episode_runs}"
  local ray_tmp="${RAY_TMPDIR:-/tmp/stage3_2_$(id -u)}"
  stage32_validate_tmp_path "${workspace}" STAGE3_2_TSC_WORKSPACE_ROOT
  stage32_validate_tmp_path "${run_root}" STAGE3_2_TSC_RUN_ROOT
  stage32_validate_tmp_path "${ray_tmp}" RAY_TMPDIR
  mkdir -p "${workspace}" "${run_root}"
  find "${workspace}" -mindepth 1 -maxdepth 1 -type d \( -name 'stage3_*' -o -name 'stage2_*' \) -exec rm -rf -- {} + 2>/dev/null || true
  find "${run_root}" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} + 2>/dev/null || true
  rm -rf -- "${ray_tmp}" 2>/dev/null || true
}

stage32_runtime_env() {
  export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}" MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}" OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
  export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-1}" VECLIB_MAXIMUM_THREADS="${VECLIB_MAXIMUM_THREADS:-1}" BLIS_NUM_THREADS="${BLIS_NUM_THREADS:-1}"
  export RAYON_NUM_THREADS="${RAYON_NUM_THREADS:-1}" PYTHONUNBUFFERED=1
  export STAGE3_2_WORKERS="${STAGE3_2_WORKERS:-96}"
  # Shared open-loop evaluator consumes STAGE2_WORKERS internally.
  export STAGE2_WORKERS="${STAGE3_2_WORKERS}"
  export STAGE3_2_TSC_WORKSPACE_ROOT="${STAGE3_2_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
  export STAGE3_2_TSC_RUN_ROOT="${STAGE3_2_TSC_RUN_ROOT:-${STAGE3_2_TSC_WORKSPACE_ROOT}/episode_runs}"
  export STAGE2_TSC_WORKSPACE_ROOT="${STAGE3_2_TSC_WORKSPACE_ROOT}" STAGE2_TSC_RUN_ROOT="${STAGE3_2_TSC_RUN_ROOT}"
  export RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage3_2_$(id -u)}"
  export TMPDIR="${TMPDIR:-${RAY_TMPDIR}/tmp}"
  stage32_validate_tmp_path "${STAGE3_2_TSC_WORKSPACE_ROOT}" STAGE3_2_TSC_WORKSPACE_ROOT
  stage32_validate_tmp_path "${STAGE3_2_TSC_RUN_ROOT}" STAGE3_2_TSC_RUN_ROOT
  stage32_validate_tmp_path "${RAY_TMPDIR}" RAY_TMPDIR
  mkdir -p "${STAGE3_2_TSC_WORKSPACE_ROOT}" "${STAGE3_2_TSC_RUN_ROOT}" "${TMPDIR}"
  ulimit -n 1048576 2>/dev/null || true; ulimit -u 262144 2>/dev/null || true
}
