# Stage4.2R3c2 preregistered design

Date frozen: 2026-07-30 Asia/Shanghai

## 1. Purpose and scientific status

Stage4.2R3c2 is a new controller-development revision created after the
failed Stage4.2R3c1 result was completely audited.

R3c1 authenticated the actual R17 visible R/Z/Ip manifold and eliminated the
old phase-zero reset. It nevertheless passed only 16/32. Static phase
matching repaired none of R3c's failures and regressed four formerly passing
weak-actuator offset-target cases. Exact plant restart and controller
causality were 32/32, so the remaining failure is controller architecture,
not restart fidelity.

R3c1's only four cases that entered target-error anticipatory damping at task
step zero passed 4/4. All other 28 cases began by tracking a suffix of the
R17 nominal trajectory, and 16 failed. The completed raw trajectories also
show nonzero first-sample motion in every case. A single static R/Z/Ip phase
does not restore velocity/history, integral, previous correction, or a
measured pending-action queue.

R3c2 prospectively tests one architectural change:

```text
phase zero
  preserve the existing exact R17 controller path

nonzero visible restart phase
  start frozen target-state regulation MPC at task step zero
```

R3c2 still reuses the inspected R3b snapshots. It is development evidence,
not independent hidden-history or different-initial-state confirmation.

Planned identities:

```text
stage
  Stage4.2R3c2

package revision
  r42r3c2_restart_target_state_regulation_mpc_v1

controller revision
  restart_target_state_regulation_mpc_v42r3c2
```

## 2. Locked evidence

R3c2 authenticates:

```text
R3b source run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3b_runs/
  stage4_2r3b_confirmatory_hidden_history_initial_state_20260730_115526

R3c source run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c_runs/
  stage4_2r3c_visible_state_phase_aligned_mpc_20260730_132807

R3c1 source run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c1_runs/
  stage4_2r3c1_authenticated_visible_manifold_phase_mpc_20260730_143218

R3c1 final run inventory digest
  5bb79906dff14e4128e57f80dcd36576c881b46202e68a63f8dd977777812d2f

R3c1 independent raw forensics SHA-256
  29e37da1d570179228a39700ac4f4c2c66067cf2a7295c2b744f2bfb40d50edd

R3c1 no-TSC restart-regulation diagnostic SHA-256
  9a278b5e97416ae2d98d05b4cff7ad2328ddd0a1ec8f3d14ded0421b184c124d
```

The four selected pair IDs, eight snapshot manifests, 32 control cases, and
four authenticated R17 visible reference manifolds remain byte-identical to
R3c1.

## 3. Frozen development matrix

```text
4 selected pairs
× 2 history members
× 2 targets
× 2 future actuator cases
= 32 controls
```

Targets:

```text
nominal
RZ_p10_m10
```

Actuator cases:

```text
delay 0 / slew 1.0
delay 2 / slew 0.9
```

No case may be selected, removed, added, or reweighted from its R3c1 result.

## 4. Frozen phase and startup rule

R3c2 reuses R3c1's exact phase selector without scale, candidate, table, or
tie-break changes:

```text
visible inputs              current R, Z, Ip only
reference                   authenticated actual R17 R/Z/Ip phases 0..20
scales                      0.03 m, 0.03 m, 2000 A
tie break                   earliest phase
```

The resulting integer phase is used only for:

- the phase-zero versus restart-regulation branch;
- frozen response-model phase;
- nominal delay-queue initialization;
- monotonically recorded reference/model phase.

It is not used to track an R17 nominal suffix after a nonzero restart.

Branch:

```text
selected phase == 0
  use the existing R3c1 path exactly

selected phase > 0
  use restart target-state regulation from task step zero through the
  complete formal horizon
```

There is no per-pair, target-result, history-member, prefix, direction, or
observed-pass override.

## 5. Restart target-state regulation

The regulator reuses the frozen R17 terminal/anticipatory MPC ingredients:

- current target errors in R, Z, and Ip;
- current-run finite-difference vR and vZ;
- frozen terminal position, velocity, and Ip measurement gains;
- frozen delay-aware physical correction solver;
- frozen response-model phase cap;
- frozen controller/model scale;
- frozen gain/slew scheduler and mode/current limits;
- frozen weak-actuator probe schedule;
- frozen nominal delay-queue priming at the visible selected phase.

At task step zero, no previous current-run sample exists. vR and vZ are
causally initialized to zero. From task step one onward, velocity uses only
the current and previous current-run samples.

The regulator's nominal physical trajectory and nominal feature passed to the
correction solver are zero, as in the frozen target-error damping controller.
The response model phase is:

```text
min(selected_phase + task_step, terminal_model_phase_cap)
```

For a normal-actuator source that has only `terminal_template_step`, that
frozen step is also the model-phase cap. No numerical controller gain,
physical limit, response matrix, probe amplitude, or formal threshold is
retuned.

## 6. Causality and forbidden inputs

The online controller may use:

- current R/Z/Ip;
- current 14-coil currents;
- prior current-run visible samples;
- task target and declared actuator case;
- frozen R17 calibration/model data;
- its own causal queue, previous correction, and regulator state.

It may not use:

- R17 source actions or suffix actions;
- current-run future actions or measurements;
- source coil or wire currents;
- current or source 48-wire vessel state;
- snapshot pair ID, history-member label, prefix label, or direction label;
- the other pair member;
- R3c/R3c1 pass/fail or formal margin.

The task/formal clock starts at zero. Waiting for a second velocity sample
does not shift the deadline.

## 7. Frozen no-TSC evidence and mandatory offline gate

The pre-design diagnostic opened all 32 completed R3c1 raw files and
recomputed controller actions only:

```text
development actions finite / solver success          32 / 32
nonzero phase selects restart regulation              32 / 32
step-zero velocity exactly zero                       32 / 32
hidden-wire variant exact                             32 / 32
observed R3c1 first action recomputed exactly         32 / 32
original R17 phase-zero/action preservation             4 / 4
source/current-future forbidden input count                 0
plant advances / real TSC                                  0
```

Its prospective actions differ from observed R3c1 by up to 0.9414, proving
that R3c2 is a new controller identity rather than a resume-compatible fix.
The diagnostic does not claim a counterfactual closed-loop result.

Before real R3c2 TSC execution, the implemented package must repeat and
strengthen this offline gate:

1. Authenticate the exact R3b, R3c, and R3c1 evidence and hashes above.
2. Recompute the four visible manifolds and all 32 experiment IDs.
3. Reproduce all four original-start R17 actions exactly over their complete
   formal horizons using the phase-zero branch.
4. Select restart regulation for all 32 development states.
5. Recompute all 32 frozen diagnostic first actions exactly.
6. Prove hidden-wire invariance and absence of all forbidden inputs.
7. Prove reference/model clocks and task clock are separately valid.
8. Create zero control raw and execute no real TSC in the offline phase.

Any failure stops the campaign.

## 8. Formal acceptance

Formal timing remains:

```text
slew 1.0: arrival <= 250 ms; hold through 350 ms
slew 0.9: arrival <= 270 ms; hold through 370 ms
R/Z tolerance: 30 mm
speed threshold: 0.1 m/s
Ip thresholds and arrival streak: unchanged
```

R3c2 PASS requires:

```text
environment success                         32/32
fresh TSC process                           32/32
fresh controller                            32/32
initial visible/full-wire restart exact     32/32
causal controller trace                     32/32
restart-regulation trace valid              32/32
future action/measurement use                    0
hidden-wire/source-action input                  0
formal contract pass                        32/32
both members pass in every group             16/16
```

The gate, matrix, timing, and physical thresholds may not change after
observing R3c2.

## 9. Reporting and advancement

Runtime, deployment, raw/snapshot integrity, plant restart, controller
causality, regulator trace, formal control, and paired hidden-history
outcomes must be reported separately.

If R3c2 fails, preserve all raw evidence and diagnose it as a new failed
development result. Do not fall back to per-case phase tuning.

If R3c2 passes, proceed only to independently preregistered R3d with newly
generated prospective histories and initial states. R3d may not select cases
from R3c2 outcomes.

New targets, continuous actuator/plant variation, noise, disturbances,
independent long hold, BC, DAgger, and bounded residual RL remain blocked.
