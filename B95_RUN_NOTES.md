# B95 run notes

## Default run

```bash
./run_resume_b95_from_b93_iter500.sh
```

Default resume checkpoint:

```text
mpo_checkpoints/train_b93_actor_limited_modes_from_b92_iter450_mpo_192worker_probe_20260615_135541/iter_000500
```

Default target stop step:

```text
3,500,000 env steps
```

## What to check first

The first log page should contain:

```text
[run_train_b95_native] limit after set : ulimit -u=30000 ulimit -n=4096
[python limits before ray.init]
[train_mpo] after ray.init; inferring spaces without env.reset
[train_mpo] loading resume checkpoint: .../iter_000500/mpo_checkpoint.pt
[train_mpo] target_randomization_stage=stage0_b95_narrow_target_curriculum enabled=True
```

## B95 success criteria

Fixed-target deterministic probe:

```text
R_error > -0.13 m
Z_error < +0.06 m
Ip_error < 2000 A
```

Fixed-target stochastic probe:

```text
R_error > -0.13 m
Z_error < +0.08 m
```

Training episodes should show randomized target columns:

```text
episode_target_R_mean
episode_target_Z_mean
episode_target_Ip_mean
target_randomization_stage
target_randomization_enabled
```

## Why eval stays fixed

B95 trains on randomized commands to break the fixed-target local action template. Evaluation still uses the original command `(R=0.75, Z=0, Ip=29779.724)` so B95 can be compared directly against B91–B94.
