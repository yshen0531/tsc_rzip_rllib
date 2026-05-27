# B83 checkpoint sweep Ray socket path fix

This patch fixes:

```text
OSError: validate_socket_filename failed: AF_UNIX path length cannot exceed 107 bytes
```

The previous sweep launcher built per-job `RAY_TMPDIR` paths such as:

```text
/tmp/ry_eval_sweep_${USER}/<long_run_name>_<timestamp>/<checkpoint>_<stage>_<mode>/...
```

Ray then appends `session_.../sockets/plasma_store`, which can exceed the Linux AF_UNIX socket path length limit.

## What changed

`eval_checkpoint_sweep.py` now creates short per-job Ray temp dirs:

```text
/tmp/rs<uid>/s<MMDDHHMMSS>/j0001
/tmp/rs<uid>/s<MMDDHHMMSS>/j0002
...
```

This keeps Ray socket paths short while keeping human-readable logs/CSV in `eval_sweeps/...`.

## Install

From project root:

```bash
unzip -o /path/to/tsc_rzip_b83_sweep_socket_fix.zip
chmod +x run_eval_checkpoint_sweep_all_nohup.sh run_eval_checkpoint_sweep.sh stop_eval_checkpoint_sweep.sh
```

## Run all checkpoint sweep again

```bash
./run_eval_checkpoint_sweep_all_nohup.sh \
  ray_checkpoints/train_b83_192worker_5m_20260520_142028 \
  96 \
  2
```

If there are stale failed Ray temp dirs, you may clean them first:

```bash
rm -rf /tmp/rs$(id -u)
```
