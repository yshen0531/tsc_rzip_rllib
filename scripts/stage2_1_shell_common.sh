#!/usr/bin/env bash
# Shared shell helpers for the standalone Stage2.1 launchers.
# This file performs local path discovery only. It never uses Git or the network.

stage21_die() {
  echo "ERROR: $*" >&2
  exit 2
}

stage21_project_init() {
  local caller_dir
  caller_dir="$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd)"
  export PROJECT_DIR="${PROJECT_DIR:-${caller_dir}}"
  PROJECT_DIR="$(cd "${PROJECT_DIR}" && pwd)"
  export PROJECT_DIR
  export TSC_ALL_ROOT="${TSC_ALL_ROOT:-$(cd "${PROJECT_DIR}/.." && pwd)}"
  export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  cd "${PROJECT_DIR}"
}

stage21_find_python() {
  if [[ -n "${PYTHON_BIN:-}" ]]; then
    :
  elif [[ -x "${TSC_ALL_ROOT}/tsc_simulation/venv_simu/bin/python" ]]; then
    PYTHON_BIN="${TSC_ALL_ROOT}/tsc_simulation/venv_simu/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python)"
  else
    stage21_die "no Python interpreter found; set PYTHON_BIN=/absolute/path/to/python"
  fi
  if [[ ! -x "${PYTHON_BIN}" ]]; then
    stage21_die "Python interpreter is not executable: ${PYTHON_BIN}"
  fi
  export PYTHON_BIN
}

stage21_abspath() {
  local value="${1:-}"
  [[ -n "${value}" ]] || return 1
  "${PYTHON_BIN}" - "${PROJECT_DIR}" "${value}" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1]).expanduser().resolve()
value = Path(sys.argv[2]).expanduser()
if not value.is_absolute():
    value = root / value
print(value.resolve(strict=False))
PY
}

stage21_validate_stage2_source() {
  local run_dir="$1"
  local required=(
    "stage2_config.resolved.json"
    "cem_state.json"
    "stage2_manifest.json"
    "analysis/all_generation_results.csv"
    "best/best_candidate.json"
  )
  [[ -d "${run_dir}" ]] || return 1
  local relative
  for relative in "${required[@]}"; do
    [[ -f "${run_dir}/${relative}" ]] || return 1
  done
}

stage21_validate_stage1_source() {
  local run_dir="$1"
  local required=(
    "analysis/coil_modes_tsc.npy"
    "analysis/response_tensor_dy_per_a.npy"
    "analysis/baseline_trajectory.csv"
    "candidate_sequences/svd03_target1p00.json"
    "raw_experiments/baseline_r00.json.gz"
    "train_config.resolved.json"
    "env_config.resolved.json"
    "stage1_config.resolved.json"
  )
  [[ -d "${run_dir}" ]] || return 1
  local relative
  for relative in "${required[@]}"; do
    [[ -f "${run_dir}/${relative}" ]] || return 1
  done
}

stage21_detect_source_stage2() {
  local candidate=""
  if [[ -n "${SOURCE_STAGE2_RUN:-}" ]]; then
    candidate="$(stage21_abspath "${SOURCE_STAGE2_RUN}")"
    stage21_validate_stage2_source "${candidate}" || \
      stage21_die "SOURCE_STAGE2_RUN is not a complete Stage2 run: ${candidate}"
    SOURCE_STAGE2_RUN="${candidate}"
    export SOURCE_STAGE2_RUN
    return
  fi

  if [[ -f "${PROJECT_DIR}/stage2_runs/latest_stage2_run.txt" ]]; then
    candidate="$(head -n 1 "${PROJECT_DIR}/stage2_runs/latest_stage2_run.txt" | tr -d '\r')"
    if [[ -n "${candidate}" ]]; then
      candidate="$(stage21_abspath "${candidate}")"
      if stage21_validate_stage2_source "${candidate}"; then
        SOURCE_STAGE2_RUN="${candidate}"
        export SOURCE_STAGE2_RUN
        return
      fi
    fi
  fi

  candidate="$("${PYTHON_BIN}" - "${PROJECT_DIR}" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1]) / "stage2_runs"
required = (
    "stage2_config.resolved.json",
    "cem_state.json",
    "stage2_manifest.json",
    "analysis/all_generation_results.csv",
    "best/best_candidate.json",
)
items = []
if root.is_dir():
    for path in root.glob("stage2_svd3_real_tsc_cem_100ms_*"):
        if path.is_dir() and all((path / rel).is_file() for rel in required):
            items.append((path.stat().st_mtime, path.resolve()))
if items:
    print(max(items)[1])
PY
)"
  [[ -n "${candidate}" ]] || stage21_die \
    "no complete Stage2 source run found. Set SOURCE_STAGE2_RUN=/absolute/path/to/stage2_run"
  SOURCE_STAGE2_RUN="${candidate}"
  export SOURCE_STAGE2_RUN
}

stage21_source_stage1_from_stage2_manifest() {
  "${PYTHON_BIN}" - "${PROJECT_DIR}" "${SOURCE_STAGE2_RUN}" <<'PY'
from pathlib import Path
import json, sys
project = Path(sys.argv[1]).resolve()
run = Path(sys.argv[2]).resolve()
manifest = run / "stage2_manifest.json"
if not manifest.is_file():
    raise SystemExit(0)
try:
    raw = json.loads(manifest.read_text(encoding="utf-8")).get("source_stage1_1_run", "")
except Exception:
    raise SystemExit(0)
if not raw:
    raise SystemExit(0)
path = Path(raw).expanduser()
if not path.is_absolute():
    path = project / path
if not path.exists():
    fallback = project / "stage1_1_runs" / Path(raw).name
    if fallback.exists():
        path = fallback
print(path.resolve(strict=False))
PY
}

stage21_detect_source_stage1() {
  local candidate=""
  if [[ -n "${SOURCE_STAGE1_1_RUN:-}" ]]; then
    candidate="$(stage21_abspath "${SOURCE_STAGE1_1_RUN}")"
    stage21_validate_stage1_source "${candidate}" || \
      stage21_die "SOURCE_STAGE1_1_RUN is not a complete Stage1.1 run: ${candidate}"
    SOURCE_STAGE1_1_RUN="${candidate}"
    export SOURCE_STAGE1_1_RUN
    return
  fi

  candidate="$(stage21_source_stage1_from_stage2_manifest)"
  if [[ -n "${candidate}" ]] && stage21_validate_stage1_source "${candidate}"; then
    SOURCE_STAGE1_1_RUN="${candidate}"
    export SOURCE_STAGE1_1_RUN
    return
  fi

  if [[ -f "${PROJECT_DIR}/stage1_1_runs/latest_stage1_1_run.txt" ]]; then
    candidate="$(head -n 1 "${PROJECT_DIR}/stage1_1_runs/latest_stage1_1_run.txt" | tr -d '\r')"
    if [[ -n "${candidate}" ]]; then
      candidate="$(stage21_abspath "${candidate}")"
      if stage21_validate_stage1_source "${candidate}"; then
        SOURCE_STAGE1_1_RUN="${candidate}"
        export SOURCE_STAGE1_1_RUN
        return
      fi
    fi
  fi

  candidate="$("${PYTHON_BIN}" - "${PROJECT_DIR}" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1]) / "stage1_1_runs"
required = (
    "analysis/coil_modes_tsc.npy",
    "analysis/response_tensor_dy_per_a.npy",
    "analysis/baseline_trajectory.csv",
    "candidate_sequences/svd03_target1p00.json",
    "raw_experiments/baseline_r00.json.gz",
    "train_config.resolved.json",
    "env_config.resolved.json",
    "stage1_config.resolved.json",
)
items = []
if root.is_dir():
    for path in root.iterdir():
        if path.is_dir() and all((path / rel).is_file() for rel in required):
            items.append((path.stat().st_mtime, path.resolve()))
if items:
    print(max(items)[1])
PY
)"
  [[ -n "${candidate}" ]] || stage21_die \
    "no complete Stage1.1 source run found. Set SOURCE_STAGE1_1_RUN=/absolute/path/to/stage1_1_run"
  SOURCE_STAGE1_1_RUN="${candidate}"
  export SOURCE_STAGE1_1_RUN
}

stage21_sources_from_existing_run() {
  local run_dir="$1"
  local output
  output="$("${PYTHON_BIN}" - "${PROJECT_DIR}" "${run_dir}" <<'PY'
from pathlib import Path
import json, sys
project = Path(sys.argv[1]).resolve()
run = Path(sys.argv[2]).resolve()
manifest = run / "stage2_1_manifest.json"
if not manifest.is_file():
    raise SystemExit(0)
data = json.loads(manifest.read_text(encoding="utf-8"))
for key in ("source_stage1_1_run", "source_stage2_run"):
    raw = str(data.get(key, "")).strip()
    if not raw:
        print("")
        continue
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = project / path
    if not path.exists():
        folder = "stage1_1_runs" if key == "source_stage1_1_run" else "stage2_runs"
        fallback = project / folder / Path(raw).name
        if fallback.exists():
            path = fallback
    print(path.resolve(strict=False))
PY
)"
  local first second
  first="$(printf '%s\n' "${output}" | sed -n '1p')"
  second="$(printf '%s\n' "${output}" | sed -n '2p')"
  if [[ -z "${SOURCE_STAGE1_1_RUN:-}" && -n "${first}" ]]; then
    SOURCE_STAGE1_1_RUN="${first}"
  fi
  if [[ -z "${SOURCE_STAGE2_RUN:-}" && -n "${second}" ]]; then
    SOURCE_STAGE2_RUN="${second}"
  fi
  export SOURCE_STAGE1_1_RUN SOURCE_STAGE2_RUN
}

stage21_resolve_existing_run() {
  local value="${STAGE2_1_RUN_DIR:-}"
  if [[ -z "${value}" && -f "${PROJECT_DIR}/stage2_1_runs/latest_stage2_1_run.txt" ]]; then
    value="$(head -n 1 "${PROJECT_DIR}/stage2_1_runs/latest_stage2_1_run.txt" | tr -d '\r')"
  fi
  [[ -n "${value}" ]] || stage21_die \
    "no Stage2.1 run selected. Set STAGE2_1_RUN_DIR or create a run first"
  value="$(stage21_abspath "${value}")"
  [[ -d "${value}" ]] || stage21_die "Stage2.1 run directory does not exist: ${value}"
  [[ -f "${value}/stage2_1_manifest.json" ]] || \
    stage21_die "not a prepared Stage2.1 run: ${value}"
  STAGE2_1_RUN_DIR="${value}"
  export STAGE2_1_RUN_DIR
}

stage21_find_ray_cli() {
  local candidate="$(dirname "${PYTHON_BIN}")/ray"
  if [[ -x "${candidate}" ]]; then
    printf '%s\n' "${candidate}"
  elif command -v ray >/dev/null 2>&1; then
    command -v ray
  else
    printf '%s\n' ""
  fi
}

stage21_ray_stop() {
  local ray_cli
  ray_cli="$(stage21_find_ray_cli)"
  if [[ -n "${ray_cli}" ]]; then
    "${ray_cli}" stop --force >/dev/null 2>&1 || true
  else
    "${PYTHON_BIN}" - <<'PY' >/dev/null 2>&1 || true
try:
    import ray
    ray.shutdown()
except Exception:
    pass
PY
  fi
}

stage21_validate_tmp_path() {
  local value="$1"
  local label="$2"
  [[ -n "${value}" && "${value}" == /tmp/* && "${value}" != "/tmp" && "${value}" != "/tmp/" ]] || \
    stage21_die "${label} must be a non-root path below /tmp; got: ${value}"
}

stage21_cleanup_runtime() {
  local workspace="${STAGE2_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
  local run_root="${STAGE2_TSC_RUN_ROOT:-${workspace}/episode_runs}"
  local ray_tmp="${RAY_TMPDIR:-/tmp/stage2_1_$(id -u)}"
  stage21_validate_tmp_path "${workspace}" "STAGE2_TSC_WORKSPACE_ROOT"
  stage21_validate_tmp_path "${run_root}" "STAGE2_TSC_RUN_ROOT"
  stage21_validate_tmp_path "${ray_tmp}" "RAY_TMPDIR"
  mkdir -p "${workspace}" "${run_root}"
  find "${workspace}" -mindepth 1 -maxdepth 1 -type d \
    \( -name 'stage2_*' -o -name 'stage2_1_*' \) -exec rm -rf -- {} + 2>/dev/null || true
  find "${run_root}" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} + 2>/dev/null || true
  rm -rf -- "${ray_tmp}" 2>/dev/null || true
}

stage21_runtime_env() {
  export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
  export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
  export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
  export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-1}"
  export VECLIB_MAXIMUM_THREADS="${VECLIB_MAXIMUM_THREADS:-1}"
  export BLIS_NUM_THREADS="${BLIS_NUM_THREADS:-1}"
  export RAYON_NUM_THREADS="${RAYON_NUM_THREADS:-1}"
  export PYTHONUNBUFFERED=1
  export STAGE2_WORKERS="${STAGE2_1_WORKERS:-${STAGE2_WORKERS:-192}}"
  export STAGE2_TSC_WORKSPACE_ROOT="${STAGE2_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
  export STAGE2_TSC_RUN_ROOT="${STAGE2_TSC_RUN_ROOT:-${STAGE2_TSC_WORKSPACE_ROOT}/episode_runs}"
  export RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage2_1_$(id -u)}"
  export TMPDIR="${RAY_TMPDIR}/tmp"
  stage21_validate_tmp_path "${STAGE2_TSC_WORKSPACE_ROOT}" "STAGE2_TSC_WORKSPACE_ROOT"
  stage21_validate_tmp_path "${STAGE2_TSC_RUN_ROOT}" "STAGE2_TSC_RUN_ROOT"
  stage21_validate_tmp_path "${RAY_TMPDIR}" "RAY_TMPDIR"
  mkdir -p "${STAGE2_TSC_WORKSPACE_ROOT}" "${STAGE2_TSC_RUN_ROOT}" "${TMPDIR}"
  ulimit -n 1048576 2>/dev/null || true
  ulimit -u 262144 2>/dev/null || true
}
