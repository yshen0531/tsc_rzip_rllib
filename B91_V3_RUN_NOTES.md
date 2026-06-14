# B91 v3: default iter_000275 + limit-safe 192 worker resume

This package keeps the B91 algorithm unchanged and fixes the launch path.

## Why this package exists

Ray initialization was hanging before entering the training loop when the shell limits were left at the login defaults (`ulimit -u=4096`, `ulimit -n=1024`). After raising limits, local Ray initialization passed at `num_cpus=192`.

## Changes

- `run_resume_b91_from_b90_1p8m.sh` defaults to B90-resume `iter_000275` instead of `final/`.
- `configs/mpo_b91_resume_from_b90_1p8m_to_2p4m_recurrent_192worker_probe.json` also records `iter_000275` as the default `resume_checkpoint`.
- `run_train_b91_native.sh` raises limits before launching Python:
  - `ulimit -u 30000`
  - `ulimit -n 4096`
- `run_train_b91_native.sh` prints shell limits into the run log.
- `scripts/train_mpo.py` prints Python-side `RLIMIT_NPROC` and `RLIMIT_NOFILE` before `ray.init()`.
- `scripts/train_mpo.py` keeps the hotfix: infer spaces without doing a preflight `env.reset()`.

## Recommended run

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib
unzip -o /path/to/b91_v3_iter275_limit_safe_192worker.zip -d .
chmod +x run_train_b91_native.sh run_train_b91_nohup.sh run_resume_b91_from_b90_1p8m.sh

./run_resume_b91_from_b90_1p8m.sh

tail -f logs/nohup/latest_b91_resume.log
```

The log should show:

```text
[run_train_b91_native] limit after set : ulimit -u=30000 ulimit -n=4096
[python limits before ray.init]
  RLIMIT_NPROC = (30000, ...)
  RLIMIT_NOFILE = (4096, 4096)
[train_mpo] after ray.init; inferring spaces without env.reset
```
