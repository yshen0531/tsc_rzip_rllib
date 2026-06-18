# B96 changelog — fixed/random mixed target curriculum

## Why B96

B95 showed that command/target randomization helped the fixed deployment target slightly:
fixed-target deterministic R error improved to about -0.154 m while Z stayed around +0.050 m.
However, 100% random-target training was not sufficiently focused on the deployment point.

B96 changes the target randomization from "all random targets" to a per-episode fixed/random mix:
fixed deployment-target episodes remain prominent, and random targets act as a regularizer that teaches
R/Z/Ip response directions.

## Main algorithmic changes

1. **Fixed/random target mixture**
   - Each episode is either the fixed deployment target or a random target.
   - The fixed-target probability increases over global env steps:
     - stage0: 50% fixed, 50% outward-biased random until 3.60M env steps
     - stage1: 70% fixed, 30% random until 3.80M env steps
     - stage2: 85% fixed, 15% fine random thereafter

2. **Outward-biased random R targets**
   - Random R ranges are biased outward because the fixed-target policy remains systematically inward:
     - stage0: R in [0.75, 0.80]
     - stage1: R in [0.74, 0.78]
     - stage2: R in [0.745, 0.765]

3. **Keep B95 action/mode constraints**
   - Do not strengthen B94-style gates.
   - Retain B95 mode coefficient scales and weak raw PF vertical diff guard.
   - This avoids repeating B94's strong Z degradation.

4. **Fixed/random split diagnostics**
   - Episode summaries now include fixed-target and random-target counts/fractions.
   - Terminal R/Z/Ip errors are reported separately for fixed and random episodes.

## Default resume

B96 defaults to the last probed B95 checkpoint:

```text
mpo_checkpoints/train_b95_target_curriculum_from_b93_iter500_mpo_192worker_probe_20260616_140102/iter_000550
```

Default stop:

```text
3.90M env_steps
```
