# tsc_rzip_rllib

Standalone RLlib SAC project for TSC-based tokamak R-Z-Ip control.

This project is intended to sit next to the old `tsc_rzip_rl` project:

```text
/home/yangshen0711/tsc_all/
  tsc_rzip_rl/        # old project, not imported by this project
  tsc_rzip_rllib/     # this new project
  tsc_simulation/     # shared TSC tree, unchanged
```

The old TSC runner/environment logic has been copied into this package and
imports have been renamed to `tsc_rzip_rllib.*`. Runtime code does not import
`tsc_rzip_rl`.

## Install

No `pyproject.toml` is needed. Install dependencies only with:

```bash
pip install -r requirements.txt
```

`requirements.txt` installs CPU-only PyTorch and RLlib. No GPU/CUDA dependency is used.

If you are on Linux cluster and the Tsinghua mirror is slow, delete these two
lines from `requirements.txt`:

```text
-i https://pypi.tuna.tsinghua.edu.cn/simple
--trusted-host pypi.tuna.tsinghua.edu.cn
```

## Smoke test without TSC

```bash
bash run_debug_mock.sh
```

On Windows PowerShell, for mock testing:

```powershell
$env:PYTHONPATH = (Get-Location).Path
python scripts/train_rllib_sac.py --config configs/rllib_sac.json --override configs/debug_mock.json
```

## Native TSC training

The default config assumes:

```text
TSC_ALL_ROOT=/home/yangshen0711/tsc_all
TSC executable: $TSC_ALL_ROOT/tsc_simulation/TSC-PCS/gotsc
Simulation root: $TSC_ALL_ROOT/tsc_simulation/HH70-PCS-ENV-LOW-FIELD-SIDE-118
```

If your shared TSC tree differs, edit `configs/tsc_low_field_side_118.json` or set:

```bash
export TSC_ALL_ROOT=/home/yangshen0711/tsc_all
```

Run:

```bash
bash run_train.sh
```

The number of parallel TSC workers is controlled in `configs/rllib_sac.json`:

```json
"parallel": {
  "num_tsc_workers": "auto:0.75",
  "reserve_cpus": 4,
  "num_envs_per_tsc_worker": 1
}
```

Examples:

```json
"num_tsc_workers": 64
```

```json
"num_tsc_workers": 128
```

```json
"num_tsc_workers": "auto:0.70"
```

No separate `cluster_128.json`, `cluster_192.json`, `run_train_128.sh`, or
`run_train_192.sh` is needed.

## Check process fan-out

```bash
python scripts/inspect_parallel.py
```

## Important parallelism rule

Keep:

```json
"num_envs_per_tsc_worker": 1
```

for native TSC. This maps to RLlib `num_envs_per_env_runner=1`, so each Ray
EnvRunner owns one independent TSC environment and one isolated TSC workspace.
Do not pack multiple TSC envs into the same EnvRunner unless you deliberately
want vectorized waiting behavior inside that worker.
