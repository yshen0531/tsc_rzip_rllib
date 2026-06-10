# B90 resume-to-1.8M update

Purpose: continue the successful B90 run from `iter_000200` to 1.8M env steps to test whether stage3 can recover R while keeping Z suppressed.

## Modified / added files

- `configs/mpo_b90_resume_to_1p8m_recurrent_192worker_probe.json`
  - Full B90-compatible config for resume.
  - `run_name` changed to a resume-specific name.
  - `stop_env_steps` changed from `1500000` to `1800000`.
  - `early_stop.enabled=false` to avoid stopping again on the already-known `r_error<-0.16` condition.
  - Model dimensions and train config are unchanged, so it is compatible with the B90 `iter_000200` checkpoint.

- `configs/override_b90_resume_to_1p8m_disable_early_stop.json`
  - Minimal override alternative if you prefer to keep using the original B90 config.

- `scripts/train_mpo.py`
  - Adds explicit validation that `--resume <dir>/mpo_checkpoint.pt` exists.
  - Records `resume_checkpoint` in the resolved config.
  - Raises a clear error if `stop_env_steps <= resumed env_steps`.
  - Prints the remaining env-step target after resume.

- `run_train_mpo_native.sh`
  - Adds a shell-level check for the resume checkpoint file before launching Python.

- `run_resume_b90_to_1p8m.sh`
  - New convenience script for background resume from B90 `iter_000200`.

## Default command

```bash
./run_resume_b90_to_1p8m.sh
```

If your B90 checkpoint directory has a different timestamp, pass it explicitly:

```bash
./run_resume_b90_to_1p8m.sh \
  configs/mpo_b90_resume_to_1p8m_recurrent_192worker_probe.json \
  mpo_checkpoints/<your_B90_run_name>/iter_000200
```
