# Stage2: SVD3 real-TSC CEM — /tmp workspace release

This release keeps the Stage2 optimization algorithm unchanged.

Temporary TSC data are placed under:

- runtime copies: `/tmp/tsc_workspace`
- episode folders: `/tmp/tsc_workspace/episode_runs`

Cleanup behavior:

1. A fresh launcher removes stale `stage2_*` runtime directories and old episode folders before starting.
2. Each candidate removes its episode directory immediately after evaluation.
3. At the end of every generation, Ray actors call `env.close()`, which removes their private TSC runtime directories before the actors are killed.

## Fresh run

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib
unzip -o /path/to/stage2_svd3_real_tsc_cem_tmp_workspace_clean.zip -d .
chmod +x run_stage2_*.sh run_stop_stage2_now.sh

export SOURCE_STAGE1_1_RUN=/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage1_1_runs/stage1_1_svd234_strict_validation_100ms_20260718_025916
./run_stage2_svd3_cem_nohup.sh
```

Log:

```bash
tail -f logs/nohup/latest_stage2_svd3_cem.log
```

Immediate stop:

```bash
./run_stop_stage2_now.sh
```

A later fresh launch cleans stale temporary Stage2 directories automatically.
