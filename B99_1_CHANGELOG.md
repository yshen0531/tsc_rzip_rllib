# B99.1 10 ms constrained goal-conditioned MPO changelog

B99.1 is a stability and time-scale correction of the B99 from-scratch constrained goal-conditioned run.

## Major changes

1. **Control period changed to 10 ms**
   - `configs/tsc_low_field_side_118.json` now uses `dt_ms = 10`.
   - `current_slew_a_per_ms` remains `0.3`, so the effective per-policy-step current limit is `3 A/step`.
   - The TSC restart file writes current and next current at adjacent times; with TSC linear interpolation, a 3 A node-to-node change over 10 ms respects 0.3 A/ms.

2. **Reach/hold time curriculum relaxed**
   - Stage0: 500 ms reach, 540 ms hold start, 650 ms episode.
   - Stage1: 400 ms reach, 450 ms hold start, 600 ms episode.
   - Stage2: 300 ms reach, 350 ms hold start, 550 ms episode.
   - In 10 ms policy steps these are 50/54/65, 40/45/60, and 30/35/55.

3. **Eval stage alias fixed**
   - `final`, `strict`, and `last` now fall back to the last configured curriculum stage if no exact `stage3` name exists.
   - This fixes the B99 issue where every online probe failed with `Cannot find eval stage 'final'`.

4. **Cost-Q nonnegative stabilization**
   - Actor-side and target-bootstrap cost-Q values use `softplus` by default.
   - This prevents the actor from exploiting negative cost critic predictions as a fake reward.

5. **Dual variables warmed up and ramped**
   - Dual actor penalty and dual updates do not dominate from step zero.
   - Dual max/lr values are reduced to avoid immediate saturation.

6. **From-scratch action scale schedule slowed**
   - Actor output scale now starts at 0.25 and gradually increases to 0.55.
   - This is intended to prevent the large-action template seen in B99.

7. **Worker count reduced**
   - Default workers reduced from 192 to 128.
   - Ray logical CPUs default to 136.
   - The run script attempts `ulimit -n 65535` first, then falls back to 4096 if the hard limit disallows it.

## Removed from clean package

The clean B99.1 zip intentionally does **not** include:

- old B99 configs: `mpo_b99_constrained_goal_from_scratch_192worker_probe.json`, `train_b99_constrained_goal_from_scratch_1ms.json`
- old B99 run scripts: `run_train_b99_native.sh`, `run_train_b99_nohup.sh`, `run_probe_b99_modes.sh`
- historical B81-B98 configs and run scripts
- checkpoint/result/log directories

Use only the B99.1 files in this package.
