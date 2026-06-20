# B98 change log

## Goal

B98 moves from fixed-target repair iterations to an explicit goal-conditioned MPO policy backbone.
B97's local-grid diagnostic showed that small target jitter was mostly ignored: target_R changes produced almost no terminal_R response.  B98 therefore appends normalized command target features to the deployable observation and expands the actor/critic input layers in a checkpoint-compatible way.

## Main changes

1. **Explicit goal-conditioning features**
   - Appends `target_R_delta_norm`, `target_Z_delta_norm`, and `target_Ip_delta_norm` to every deployable observation.
   - Default scales: `R_scale_m=0.05`, `Z_scale_m=0.05`, `Ip_scale_a=3000`.

2. **Checkpoint-compatible input expansion**
   - Actor GRU input weights are copied for the original observation columns; new goal-feature columns keep initialized weights.
   - Critic GRU input weights preserve the `[old_obs, privileged, action]` mapping after inserting goal features at the end of obs.
   - Optimizer states are intentionally not restored when observation dimensions change.

3. **Training distribution**
   - 50% fixed deployment target.
   - 50% symmetric local targets: `R ∈ [0.72,0.78]`, `Z ∈ [-0.06,+0.06]`, `Ip_delta ∈ [-2000,+2000] A`.
   - No outward-R or downward-Z one-sided bias.

4. **Evaluation**
   - Fixed deterministic/stochastic probes remain anchored to `R=0.75, Z=0, Ip=29779.724`.
   - Local grid eval expands to `R={0.72,0.75,0.78}` and `Z={-0.06,0,+0.06}`.
   - Adds grid sensitivity metrics: `eval_grid_R_target_to_terminal_R_slope` and `eval_grid_Z_target_to_terminal_Z_slope`.

5. **Inherited from B97/B95**
   - B95/B96 intermediate mode gates.
   - Light raw PF vertical diff guard, coefficient `0.010`.
   - Limit-safe Ray startup scripts.

## Default resume

B98 defaults to:

```text
mpo_checkpoints/train_b97_fixed_core_goal_ready_from_b95_iter550_mpo_192worker_probe_20260618_103020/iter_000575
```

This is intentional; it does not default to `final/`.
