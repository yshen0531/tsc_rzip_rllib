# B95 changelog — target curriculum / command randomization

B95 is based on B94 code, but changes the training strategy rather than adding more local penalties.

## Motivation

B94 showed a clear R/Z tradeoff: stronger PF-vertical/raw guards can improve stochastic or episode-mean R, but Z degrades. This suggests the fixed-target policy has learned a local action template rather than a robust error-feedback direction.

## Key changes

1. **Per-episode target randomization during training**
   - New `target_randomization` block in `configs/train_b95_target_curriculum_mpo_fixed_eval_1ms.json`.
   - Rollout workers sample a new `(R, Z, Ip)` command at each episode reset.
   - Online deterministic/stochastic probes and standalone eval keep the original fixed target.

2. **Absolute global-step target curriculum**
   - Designed for resume from B93 `iter_000500` at about 3.072M env steps.
   - stage0: R 0.74–0.77, Z ±0.025, Ip ±1000 A, until 3.20M.
   - stage1: R 0.73–0.78, Z ±0.035, Ip ±1500 A, until 3.35M.
   - stage2: R 0.72–0.80, Z ±0.05, Ip ±2500 A.

3. **Mode gates between B93 and B94**
   - B94 gates were strong enough to hurt Z.
   - B95 relaxes PF vertical gates relative to B94 but keeps common modes constrained.

4. **Weaker raw PF vertical diff guard**
   - B94 used `coeff=0.03` and hurt Z.
   - B95 uses `coeff=0.015`.

5. **Fixed-target eval protection**
   - `train_mpo.py` disables target randomization inside online policy probes.
   - `eval_mpo_policy.py` also disables it for standalone eval.

## Files changed

- `scripts/train_mpo.py`
- `scripts/eval_mpo_policy.py`
- `scripts/probe_mpo_action_modes.py`
- `tsc_rzip_rllib/mpo/models.py`
- `tsc_rzip_rllib/mpo/privileged.py`
- `tsc_rzip_rllib/mpo/replay.py`
- `tsc_rzip_rllib/mpo/__init__.py`
- `configs/train_b95_target_curriculum_mpo_fixed_eval_1ms.json`
- `configs/mpo_b95_resume_from_b93_iter500_to_3p5m_recurrent_192worker_probe.json`
- `configs/override_b95_resume_disable_early_stop.json`
- `run_train_b95_native.sh`
- `run_resume_b95_from_b93_iter500.sh`
- `run_train_b95_nohup.sh`
- `run_probe_b95_modes.sh`
