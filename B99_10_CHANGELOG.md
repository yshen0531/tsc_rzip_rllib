# B99.10 Train-First — Changes Relative to B99.9

## Purpose

B99.9 successfully protected the actor: ten real-TSC transactions were accepted, no rejected proposal contaminated the deployable actor, and dual wind-up was eliminated. However, every accepted transaction selected the negative search boundary, R/Z improved only by millimetres, and deterministic hold remained zero. The main B99.10 objective is therefore not a more elaborate certification system. It is to make the actor/critics learn a reward that is closer to the actual reach–brake–hold task, while retaining only a lightweight real-TSC safety transaction.

This package supersedes the earlier heavy B99.10 package with seven-scenario validation on every transaction.

## 1. Training objective is now symmetric and hold-aware

B99.9 still contained a strong Z-only progress reward:

- `w_z_signed_progress = 14`
- `w_z_signed_progress_early = 14`

The deterministic transaction score, by contrast, was symmetric in R/Z and dominated by late-window performance. This mismatch is a plausible contributor to the repeated critic-gradient/real-TSC direction disagreement.

B99.10 removes the strong single-axis objective:

- `w_z_signed_progress = 0`
- `w_z_signed_progress_early = 0`
- `w_negative_r_bias = 0`

It adds four symmetric R/Z training terms:

1. `soft_rz_distance_penalty`
   - continuous normalized R/Z distance;
   - active throughout the episode;
   - stronger during the late/hold phase.
2. `soft_rz_progress_bonus`
   - positive when normalized R/Z distance decreases;
   - negative when it increases;
   - applies before and during hold.
3. `soft_rz_outward_velocity_penalty`
   - penalizes radial velocity pointing away from the target.
4. `soft_rz_near_velocity_penalty`
   - smoothly increases braking pressure near the target tube.

Core settings:

```json
{
  "w_soft_rz_distance": 0.35,
  "soft_rz_r_tol_m": 0.08,
  "soft_rz_z_tol_m": 0.08,
  "soft_rz_phase_floor": 0.25,
  "w_soft_rz_progress": 2.0,
  "soft_rz_progress_ref": 0.10,
  "w_soft_rz_outward_velocity": 0.25,
  "w_soft_rz_near_velocity": 0.45,
  "soft_rz_velocity_sigma": 3.0
}
```

The new terms are emitted in environment info and therefore appear in worker timing/metric summaries:

- `soft_rz_distance`
- `soft_rz_progress`
- `soft_rz_distance_penalty`
- `soft_rz_progress_bonus`
- `rz_velocity_norm`
- `soft_rz_radial_velocity`
- `soft_rz_outward_velocity_penalty`
- `soft_rz_near_velocity_penalty`

## 2. Cost critic remains checkpoint-compatible

B99.9 had five cost dimensions: R, Z, Ip, action and vessel. B99.10 keeps exactly those five dimensions, so the B99.9 cost-critic output heads can be loaded.

A small late/terminal R/Z-velocity auxiliary is folded into the existing R and Z cost values:

```json
{
  "aux_info_key": "rz_velocity_norm",
  "aux_terminal_info_key": "terminal_rz_velocity_norm",
  "aux_tol": 0.75,
  "aux_terminal_tol": 0.80,
  "aux_weight": 0.20
}
```

This teaches the existing cost critics that lower position error with excessive crossing speed is not a valid improvement without changing network dimensions.

## 3. Replay is focused more directly on the deployment target

B99.9 used 70% fixed target and 30% local target jitter. B99.10 uses:

- 80% fixed target;
- 20% local jitter;
- R range: `0.74–0.76 m`;
- Z range: `-0.025–+0.025 m`;
- Ip delta: `±1500 A`.

This gives the critics more data at the actual deployment command while retaining modest goal-conditioned robustness.

## 4. Critic transition after the reward change

B99.10 loads B99.9 critic weights but does not restore old critic optimizer momentum, because the reward and R/Z velocity cost target have changed.

- reward/cost critic weights: loaded from B99.9 periodic checkpoint;
- critic optimizer state: reset;
- replay: rebuilt;
- actor/eta optimizers: reset;
- protected actor and dual values: loaded from B99.9 `accepted_latest`;
- first actor transaction delayed for 10 critic-settle iterations.

This preserves useful representations while giving the critics time to fit the new objective before proposing an actor direction.

## 5. Online transaction is lightweight

B99.9 evaluated five alpha candidates on fixed and then used two additional nearby scenarios. The earlier heavy B99.10 design proposed seven scenarios for every transaction. The train-first B99.10 instead uses:

### Normal transaction

1. Evaluate four alpha candidates on fixed:
   - `-1.0`
   - `-0.5`
   - `-0.25`
   - `+0.25` sentinel
2. Validate the fixed-best candidate on one difficult nearby target:
   - `R + 0.01 m`
   - `Z - 0.02 m`
3. Only if rank 1 fails does rank 2 receive the difficult-target validation.

Typical real-TSC episode count when rank 1 passes:

- two baseline episodes on the first transaction;
- four fixed candidate episodes;
- one hard-target validation episode.

After the baseline is cached, a normal transaction usually requires five deterministic episodes rather than eleven to thirty.

### Low-frequency audit

Before every third accepted update, the candidate must also pass five additional nearby targets, producing a seven-scenario audit. The public best score remains the comparable fixed-plus-hard aggregate; audit aggregate is logged separately.

## 6. Adaptive alpha search is retained but capped at four candidates

- negative boundary win: expand outward;
- interior negative win: refine around it;
- rejection: contract toward zero;
- positive sentinel win: restore bidirectional search.

At most four candidates are kept, so line search remains a safety/step-size mechanism rather than becoming the main optimizer.

## 7. Simplified online score

The online acceptance score focuses on a small number of interpretable quantities:

- terminal R/Z;
- late R/Z RMS;
- late normalized R/Z distance mean;
- fraction of late steps within the 2× hold tube;
- late velocity RMS;
- small terminal-velocity, Ip and action terms.

The many extra soft-hold metrics are still recorded for diagnosis but do not all drive online acceptance.

## 8. Transaction schedule and stop rules

- critic settle before first transaction: 10 iterations;
- transaction interval: 6 iterations;
- maximum transactions: 10;
- maximum consecutive rejections: 3;
- stop after three consecutive accepted improvements below `0.008`.

## 9. Immediate stop remains supported

No SIGTERM/SIGINT graceful handler is installed. `run_stop_b99_10_now.sh` sends SIGKILL to the B99.10 process group and forces Ray to stop.

Checkpoint files are written to same-directory temporary files, flushed and atomically replaced. This cannot preserve an in-progress transaction, but it reduces the chance that immediate termination overwrites the previous complete checkpoint with a partial file.

Periodic checkpoint interval is reduced from five to three iterations.

## 10. Intentionally unchanged from B99.9

- 192 TSC workers;
- runtime-only TSC path;
- 10 ms control period;
- 65-step / approximately 500 ms stage;
- 14-dimensional coil action;
- ordinary actor updates suppressed;
- eta updates suppressed outside transactions;
- dual integration frozen;
- full actor/optimizer rollback on failed transaction;
- weak Ip priority and broad Ip safety constraint;
- no directional hard-coded coil command.
