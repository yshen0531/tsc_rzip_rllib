# B97 changelog — fixed-core goal-ready training

## Why B97

B91--B96 progressively improved diagnostics and fixed several action-template issues, but the later runs started to look like local repair: pushing R outward could raise Z, and pushing Z down could recover the old inward-R bias.  B97 resets the training strategy around the actual RL objective: build a fixed-target backbone that is ready for later variable-target / goal-conditioned training.

## Main changes

1. **Resume from B95 iter_000550, not B96 and not final.**
   B95 is the more balanced checkpoint before the B96 R/Z tradeoff drift.

2. **Fixed-core target distribution.**
   Training uses the deployment target in 85% of episodes:

   ```text
   R = 0.75, Z = 0.0, Ip = 29779.724
   ```

   The remaining 15% use a small symmetric local jitter:

   ```text
   R_target  in [0.745, 0.755]
   Z_target  in [-0.015, +0.015]
   Ip_delta  in [-800, +800] A
   ```

   No outward-R or downward-Z one-sided target bias is used.

3. **No new one-sided reward patch.**
   B97 keeps the inherited reward structure and avoids adding another directional R/Z correction.

4. **Keep B95/B96 mode gates.**
   The mode coefficient scales stay at the intermediate B95/B96 values.  B97 is not another action-basis tightening run.

5. **Weaken raw PF vertical diff guard slightly.**
   The raw PF U/L guard coefficient changes from 0.015 to 0.010 to avoid over-constraining Z while still discouraging excessive raw differential action.

6. **Add local target-grid eval.**
   Every 50 iterations B97 runs a deterministic local 3x3 target grid:

   ```text
   R_target in {0.745, 0.750, 0.755}
   Z_target in {-0.015, 0.000, +0.015}
   Ip_target = 29779.724
   ```

   This is diagnostic only; it does not change training data.

## Default checkpoint

```text
mpo_checkpoints/train_b95_target_curriculum_from_b93_iter500_mpo_192worker_probe_20260616_140102/iter_000550
```

## Target stop

```text
3.90M env_steps
```
