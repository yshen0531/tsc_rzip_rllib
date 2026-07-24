#!/usr/bin/env bash
# Shared helpers for the complete standalone Stage3.4 launchers.
# No Git, network access, or external source-tree recovery is used.

stage34_die() { echo "ERROR: $*" >&2; exit 2; }

stage34_project_init() {
  local caller_dir
  caller_dir="$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd)"
  export PROJECT_DIR="${PROJECT_DIR:-${caller_dir}}"
  PROJECT_DIR="$(cd "${PROJECT_DIR}" && pwd)"
  export PROJECT_DIR
  export TSC_ALL_ROOT="${TSC_ALL_ROOT:-$(cd "${PROJECT_DIR}/.." && pwd)}"
  export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  cd "${PROJECT_DIR}"
}

stage34_find_python() {
  if [[ -n "${PYTHON_BIN:-}" ]]; then :
  elif [[ -x "${TSC_ALL_ROOT}/tsc_simulation/venv_simu/bin/python" ]]; then
    PYTHON_BIN="${TSC_ALL_ROOT}/tsc_simulation/venv_simu/bin/python"
  elif command -v python3 >/dev/null 2>&1; then PYTHON_BIN="$(command -v python3)"
  elif command -v python >/dev/null 2>&1; then PYTHON_BIN="$(command -v python)"
  else stage34_die "no Python interpreter found; set PYTHON_BIN=/absolute/path/to/python"
  fi
  [[ -x "${PYTHON_BIN}" ]] || stage34_die "Python interpreter is not executable: ${PYTHON_BIN}"
  export PYTHON_BIN
}

stage34_abspath() {
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

stage34_validate_stage33_source() {
  local run_dir="$1" relative
  [[ -d "${run_dir}" ]] || return 1
  local required=(
    "stage3_3_config.resolved.json"
    "stage3_3_manifest.json"
    "stage3_3_state.json"
    "stage3_3_target_library/target_library.json"
    "stage3_3_confirmations/stage3_3_verdict.json"
    "env_config.resolved.json"
    "train_config.resolved.json"
  )
  for relative in "${required[@]}"; do [[ -f "${run_dir}/${relative}" ]] || return 1; done
  "${PYTHON_BIN}" - "${run_dir}" <<'PY' >/dev/null 2>&1
from pathlib import Path
import json,sys
run=Path(sys.argv[1]); verdict=json.loads((run/'stage3_3_confirmations/stage3_3_verdict.json').read_text()).get('verdict')
allowed={
 'TARGET_CONDITIONED_LIBRARY_INCOMPLETE_MPC_NOT_VALIDATED',
 'PASS_TARGET_CONDITIONED_NOMINAL_LIBRARY_CONFIRMED_MPC_NOT_VALIDATED',
 'PASS_TARGET_CONDITIONED_RECEDING_HORIZON_MPC_TEST_ENVELOPE_CONFIRMED',
}
assert verdict in allowed
library=json.loads((run/'stage3_3_target_library/target_library.json').read_text())
assert int(library.get('n_entries',0)) >= 1
PY
}

stage34_detect_source_stage33() {
  local candidate=""
  if [[ -n "${SOURCE_STAGE3_3_RUN:-}" ]]; then
    candidate="$(stage34_abspath "${SOURCE_STAGE3_3_RUN}")"
    stage34_validate_stage33_source "${candidate}" || stage34_die "SOURCE_STAGE3_3_RUN is incomplete or unsupported: ${candidate}"
    SOURCE_STAGE3_3_RUN="${candidate}"; export SOURCE_STAGE3_3_RUN; return
  fi
  if [[ -f "${PROJECT_DIR}/stage3_3_runs/latest_stage3_3_run.txt" ]]; then
    candidate="$(head -n1 "${PROJECT_DIR}/stage3_3_runs/latest_stage3_3_run.txt" | tr -d '\r')"
    [[ -n "${candidate}" ]] && candidate="$(stage34_abspath "${candidate}")"
    if [[ -n "${candidate}" ]] && stage34_validate_stage33_source "${candidate}"; then
      SOURCE_STAGE3_3_RUN="${candidate}"; export SOURCE_STAGE3_3_RUN; return
    fi
  fi
  candidate="$("${PYTHON_BIN}" - "${PROJECT_DIR}" <<'PY'
from pathlib import Path
import json,sys
root=Path(sys.argv[1])/'stage3_3_runs'; items=[]
allowed={
 'TARGET_CONDITIONED_LIBRARY_INCOMPLETE_MPC_NOT_VALIDATED',
 'PASS_TARGET_CONDITIONED_NOMINAL_LIBRARY_CONFIRMED_MPC_NOT_VALIDATED',
 'PASS_TARGET_CONDITIONED_RECEDING_HORIZON_MPC_TEST_ENVELOPE_CONFIRMED',
}
if root.is_dir():
  for p in root.glob('stage3_3_target_conditioned_receding_horizon_mpc_250ms_*'):
    required=(p/'stage3_3_config.resolved.json',p/'stage3_3_manifest.json',p/'stage3_3_state.json',p/'stage3_3_target_library/target_library.json',p/'stage3_3_confirmations/stage3_3_verdict.json')
    if not (p.is_dir() and all(x.exists() for x in required)): continue
    try: verdict=json.loads((p/'stage3_3_confirmations/stage3_3_verdict.json').read_text()).get('verdict')
    except Exception: continue
    if verdict in allowed: items.append((p.stat().st_mtime,p.resolve()))
if items: print(max(items)[1])
PY
)"
  [[ -n "${candidate}" ]] || stage34_die "no complete Stage3.3 source found. Set SOURCE_STAGE3_3_RUN=/absolute/path/to/run"
  SOURCE_STAGE3_3_RUN="${candidate}"; export SOURCE_STAGE3_3_RUN
}

stage34_source_from_existing_run() {
  local run_dir="$1" candidate
  candidate="$("${PYTHON_BIN}" - "${PROJECT_DIR}" "${run_dir}" <<'PY'
from pathlib import Path
import json,sys
project=Path(sys.argv[1]).resolve(); run=Path(sys.argv[2]).resolve(); p=run/'stage3_4_manifest.json'
if not p.is_file(): raise SystemExit(0)
data=json.loads(p.read_text()); raw=str(data.get('source_stage3_3_run','')).strip()
if not raw: raise SystemExit(0)
path=Path(raw).expanduser()
if not path.exists():
  fallback=project/'stage3_3_runs'/path.name
  if fallback.exists(): path=fallback
print(path.resolve(strict=False))
PY
)"
  if [[ -z "${SOURCE_STAGE3_3_RUN:-}" && -n "${candidate}" ]]; then
    SOURCE_STAGE3_3_RUN="${candidate}"; export SOURCE_STAGE3_3_RUN
  fi
}

stage34_find_ray_cli() {
  local candidate="$(dirname "${PYTHON_BIN}")/ray"
  if [[ -x "${candidate}" ]]; then printf '%s\n' "${candidate}"
  elif command -v ray >/dev/null 2>&1; then command -v ray
  else printf '%s\n' ""; fi
}

stage34_ray_stop() {
  local ray_cli; ray_cli="$(stage34_find_ray_cli)"
  if [[ -n "${ray_cli}" ]]; then "${ray_cli}" stop --force >/dev/null 2>&1 || true
  else "${PYTHON_BIN}" - <<'PY' >/dev/null 2>&1 || true
try:
 import ray; ray.shutdown()
except Exception: pass
PY
  fi
}

stage34_validate_tmp_path() {
  local value="$1" label="$2"
  [[ -n "${value}" && "${value}" == /tmp/* && "${value}" != /tmp && "${value}" != /tmp/ ]] || stage34_die "${label} must be below /tmp; got ${value}"
}

stage34_cleanup_runtime() {
  local workspace="${STAGE3_4_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
  local run_root="${STAGE3_4_TSC_RUN_ROOT:-${workspace}/episode_runs}"
  local ray_tmp="${RAY_TMPDIR:-/tmp/stage3_4_$(id -u)}"
  stage34_validate_tmp_path "${workspace}" STAGE3_4_TSC_WORKSPACE_ROOT
  stage34_validate_tmp_path "${run_root}" STAGE3_4_TSC_RUN_ROOT
  stage34_validate_tmp_path "${ray_tmp}" RAY_TMPDIR
  mkdir -p "${workspace}" "${run_root}"
  find "${workspace}" -mindepth 1 -maxdepth 1 -type d \( -name 'stage3_4*' -o -name 'stage34*' -o -name 'stage2_*' \) -exec rm -rf -- {} + 2>/dev/null || true
  find "${run_root}" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} + 2>/dev/null || true
  rm -rf -- "${ray_tmp}" 2>/dev/null || true
}

stage34_runtime_env() {
  export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}" MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}" OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
  export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-1}" VECLIB_MAXIMUM_THREADS="${VECLIB_MAXIMUM_THREADS:-1}" BLIS_NUM_THREADS="${BLIS_NUM_THREADS:-1}"
  export RAYON_NUM_THREADS="${RAYON_NUM_THREADS:-1}" PYTHONUNBUFFERED=1
  export STAGE3_4_WORKERS="${STAGE3_4_WORKERS:-96}"
  export STAGE2_WORKERS="${STAGE3_4_WORKERS}"
  export STAGE3_4_TSC_WORKSPACE_ROOT="${STAGE3_4_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
  export STAGE3_4_TSC_RUN_ROOT="${STAGE3_4_TSC_RUN_ROOT:-${STAGE3_4_TSC_WORKSPACE_ROOT}/episode_runs}"
  export STAGE2_TSC_WORKSPACE_ROOT="${STAGE3_4_TSC_WORKSPACE_ROOT}" STAGE2_TSC_RUN_ROOT="${STAGE3_4_TSC_RUN_ROOT}"
  export RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage3_4_$(id -u)}"
  export TMPDIR="${TMPDIR:-${RAY_TMPDIR}/tmp}"
  stage34_validate_tmp_path "${STAGE3_4_TSC_WORKSPACE_ROOT}" STAGE3_4_TSC_WORKSPACE_ROOT
  stage34_validate_tmp_path "${STAGE3_4_TSC_RUN_ROOT}" STAGE3_4_TSC_RUN_ROOT
  stage34_validate_tmp_path "${RAY_TMPDIR}" RAY_TMPDIR
  mkdir -p "${STAGE3_4_TSC_WORKSPACE_ROOT}" "${STAGE3_4_TSC_RUN_ROOT}" "${TMPDIR}"
  ulimit -n 1048576 2>/dev/null || true; ulimit -u 262144 2>/dev/null || true
}
