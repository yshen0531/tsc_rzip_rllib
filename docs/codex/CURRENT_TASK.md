# CURRENT_TASK.md — Stage4.2R3 hidden-history and initial-state robustness

## 1. Current evidence checkpoint

Stage4.2R1 means the Stage4.2R1 authentic plant-state restart experiment.
Stage4.1R17 means the frozen Stage4.1R17 finite static-grid controller source.

Stage4.2R1 R1c is certified for authentic same-action plant restart, 18/18.
Stage4.2R2 is now certified for causal persistent-controller-state restart
with online action recomputation, 18/18.

R2 exact identities:

```text
branch              codex/stage4_2r2-controller-checkpoint
code commit         84962ef
controller revision persistent_mpc_controller_checkpoint_replay_v42r2
package revision    r42r2_persistent_controller_checkpoint_v1
remote run          /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r2_runs/stage4_2r2_persistent_controller_checkpoint_replay_20260730_082250
remote log          /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/stage4_2r2_persistent_controller_checkpoint_replay_20260730_082828.log
```

Independent server-side raw/snapshot recomputation established:

```text
controller checkpoints                   18/18
offline causal action recomputation       18/18, 282 suffix actions
future action/measurement use             0/0
real fresh-TSC restart rollouts            18/18
online action / visible / full-wire exact 18/18
immutable formal contract                 18/18
minimum formal signed margin              1.0456920999768471e-05
```

The full report is
`docs/codex/reports/STAGE4_2R2_FORENSIC_REPORT.md`.

## 2. Active task

The active next stage is Stage4.2R3. It must test the reliable MPC expert
under:

1. matched visible R/Z/Ip/coil state with materially different hidden
   vessel/eddy-current histories; and
2. different authenticated initial states.

R3 must first establish a scientifically valid, preregistered pair-generation
method. It must not synthesize an arbitrary hidden-current vector or call two
states "matched visible" merely because a summary metric is close.

The controller must receive only causal observations and the R2 checkpoint
schema. Hidden full-wire current may be recorded for audit and pairing, but it
must not leak into the online controller unless a later observer design
explicitly estimates it from causal measurements.

## 3. Required design before execution

Before changing controller behavior or starting TSC:

- inventory authentic R1/R2 states and available restart times;
- define visible-state matching tolerances separately for R, Z, Ip, all
  controller-visible channels, and 14 coil currents;
- define a minimum hidden-history separation over the full wire/vessel-current
  vector;
- prove each candidate snapshot is complete and restart-authentic;
- preregister target, delay, slew, initial-state, and history-pair matrices;
- preregister safety stops and the unchanged formal gate;
- state whether the current observer is expected to disambiguate the pair
  causally, and over what observation window;
- keep identification/calibration information causal;
- prevent selection on post-result formal success.

If the existing evidence cannot supply valid matched-visible/different-hidden
pairs, create a focused state-generation stage first. Do not weaken matching
or hidden-separation thresholds after seeing outcomes.

## 4. Required result classification

Every result must distinguish:

```text
runtime/environment error
deployment/package/import error
raw/snapshot corruption
summary/statistics/reporting bug
invalid pair or experimental-design flaw
observer/history-identification failure
real closed-loop control failure
finite-envelope success
unvalidated extrapolation
```

An unrun phase is `not_run`, never pass or fail. A valid plant-history effect
must not be mislabeled as a controller software error, and an invalid pair
must not be interpreted as control evidence.

## 5. Immutable formal contract

```text
slew 1.0 or 1.1:
  arrive no later than 250 ms
  hold/evaluate through 350 ms

slew 0.9:
  arrive no later than 270 ms
  hold/evaluate through 370 ms
```

R/Z tolerance, speed threshold, Ip threshold, and arrival streak remain at
the frozen baseline. Longer observation horizons do not move the arrival
deadline. Independent long hold remains a later orthogonal test.

## 6. Evidence-transfer rule

Large raw, JSON.GZ, snapshot, and trajectory trees stay on the server.

For every large run:

1. preserve the raw tree;
2. run a read-only Python postprocessor in the canonical server project with
   the existing virtualenv;
3. parse and hash every required raw/snapshot input and independently
   recompute load-bearing metrics;
4. download only compact audit JSON/CSV, manifests, hash inventories, and
   logs;
5. verify compact local counts and SHA-256 values.

No local compression or extraction is allowed.

## 7. Advancement rule

R3 success must remain a bounded claim over its preregistered state/history
matrix. After hidden-history and different-initial-state robustness, proceed
in order to:

```text
new preregistered targets
continuous actuator and plant/Jacobian variation
measurement noise and observer robustness
disturbance recovery
independent long hold
```

BC, DAgger, and bounded residual RL remain prohibited until the MPC expert is
reliable across restart, hidden history, initial state, continuous parameters,
noise, and disturbance recovery.
