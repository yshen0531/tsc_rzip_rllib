# Stage4.2R3c3 preregistered design

Date frozen: 2026-07-30 Asia/Shanghai

## 1. Purpose

Stage4.2R3c3 is an identification-only restart-state local-response campaign.
It is not a candidate controller and is not allowed to claim formal control
closure.

R3c1 retained the target-conditioned R17 nominal suffix but passed only
16/32. R3c2 replaced that suffix with a zero-nominal terminal regulator and
fell to 12/32. All 20 R3c2 failures were real position-limited closed-loop
failures; runtime, plant restart, causality, solver, saturation, and raw
integrity were clean.

The existing lifted model cannot simply be stretched:

- its identified horizon ends at source state 35;
- R14 retained the nominal plan but all 24 cases rebounded after the model
  horizon because delayed tail commands changed semantics;
- R15B validated a small-signal local model only around the old late
  weak-slew state-23 baseline;
- R16 proved that large-amplitude bidirectional extrapolation is invalid;
- R17 validated only a finite one-sided delay-conditioned braking patch.

R3c3 therefore measures a new bounded bidirectional response bank directly
at the authentic R3b restart states and on the formal task clock. It asks two
questions before another MPC is designed:

1. Is a small-signal task-relative response model locally linear enough at
   these restart states?
2. Do matched-visible but different hidden vessel/eddy histories materially
   change that response?

Planned identity:

```text
stage
  Stage4.2R3c3

package revision
  r42r3c3_restart_task_clock_local_response_identification_v1

controller revision
  restart_task_clock_local_response_probe_v42r3c3
```

## 2. Locked source evidence

R3c3 authenticates and freezes:

```text
R3b state/snapshot source
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3b_runs/
  stage4_2r3b_confirmatory_hidden_history_initial_state_20260730_115526

R3c1 baseline controller/result
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c1_runs/
  stage4_2r3c1_authenticated_visible_manifold_phase_mpc_20260730_143218

R3c1 run inventory digest
  5bb79906dff14e4128e57f80dcd36576c881b46202e68a63f8dd977777812d2f

R3c1 raw forensics SHA-256
  29e37da1d570179228a39700ac4f4c2c66067cf2a7295c2b744f2bfb40d50edd

R3c2 failed controller/result
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c2_runs/
  stage4_2r3c2_restart_target_state_regulation_mpc_20260730_164616

R3c2 run inventory digest
  2119d2edad615dbb9594ad4332b758a9cf7ffc2e62b988650c41297aace8cff2

R3c2 raw forensics SHA-256
  644da85280e03015732bb63deb1205bf5fcafeabc53b0f8a9e606565a27efbb2
```

The exact four selected pair IDs, eight restart snapshots, two targets, two
future actuator cases, and authenticated visible-phase selector remain
unchanged.

R3c3 uses R3c1, not R3c2, as its unperturbed baseline because the identified
future controller must retain target-conditioned nominal transport. This is
fixed before seeing probe outcomes.

## 3. Baseline contexts

The context matrix is:

```text
4 selected snapshot pairs
× 2 hidden-history members
× 2 targets
× 2 future actuator cases
= 32 baseline contexts
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

Every context starts a fresh TSC process from its authentic snapshot and a
fresh R3c1 controller. The exact completed R3c1 raw for that context is the
unperturbed baseline; no new baseline TSC task is required.

## 4. Probe basis

The probes are additive physical-mode correction perturbations inside the
R3c1 online controller. They are applied before the unchanged absolute
coefficient limits, gain/slew scheduler, delay queue, and 14-coil mapping.
The R3c1 nominal trajectory, residual feedback, integral, previous
correction, transition logic, and delay queue remain active.

Only the two dominant R/Z modes are probed:

```text
mode 0 amplitude    0.0075
mode 1 amplitude    0.0075
mode 2 amplitude    0
```

Mode 2 is not reidentified in R3c3. R3c2's 20 formal failures were all
position-limited and its Ip margins remained positive. This restriction does
not validate unseen Ip behavior or a full three-mode deployment model.

Four task-relative basis probes are fixed:

```text
early_mode0
early_mode1
deadline_mode0
deadline_mode1
```

For each basis, physical effects use the zero-net pattern:

```text
effect offsets    [0, 1, 3, 4]
sign pattern      [+1, +1, -1, -1]
```

The two first-effect anchors are:

```text
early basis       task state 5
deadline basis    task state 17
```

For actual delay `d`, an effect at task state `s` is issued causally at:

```text
issue task step = s - d - 1
```

Thus every issue step is nonnegative for both delay 0 and delay 2. The late
window ends at task state 21, before the unchanged 250/270 ms arrival
deadlines, leaving a measured response through the formal arrival and hold
windows.

Each basis is run with both global signs `-1` and `+1`:

```text
32 contexts × 4 basis probes × 2 signs = 256 real TSC rollouts
```

No amplitude, timing, basis, context, or sign may be changed after observing
R3c3.

## 5. Causality and safety

The probe controller may use:

- current R/Z/Ip and 14 coil currents;
- prior current-run visible samples;
- target and declared actuator case;
- the frozen R3c1 calibration/controller state;
- its own task-relative probe schedule.

The controller may not use:

- source or current-run future actions/measurements;
- source coil currents;
- source or current 48-wire vessel currents;
- pair ID, history-member label, prefix label, or nullspace direction;
- the other pair member;
- R3c1/R3c2 formal results or margins.

Pair/history/target/actuator/probe identities may be used only by the
experiment orchestrator and postprocessor. Pair/history identity is stripped
before the controller is constructed.

Every requested probe is exactly zero-net in physical-mode coefficient space.
Every applied probe must equal the requested probe without clipping, remain
zero-net to absolute tolerance `1e-12`, and have maximum component exactly
`0.0075`. Any clipping or missing issue is a failed identification row, not a
reason to reinterpret the amplitude.

Current utilization must remain at or below `0.55`. All existing TSC
abnormality/current/scheduler limits remain active.

## 6. Offline gate

Before real TSC, the exact deployed package must prove:

1. Exact R3b, R3c1, and R3c2 source paths, hashes, inventories, and
   experiment-ID sets.
2. Exact reconstruction of all 32 baseline contexts and all 256 probe IDs.
3. Exact R3c1 phase-zero actions over all four original-source horizons.
4. Exact R3c1 unperturbed first actions for all 32 restart contexts.
5. For all 256 probes, finite first action, legal issue steps, exact requested
   amplitude, exact requested zero net, and no forbidden controller key.
6. Hidden-wire mutation leaves every offline first action and probe schedule
   unchanged.
7. The task clock starts at zero and is independent of selected model phase.
8. The earliest probe has no physical effect before task state 5.
9. The offline phase creates zero control raw, advances no plant, and executes
   no real TSC.

Any failure stops the real campaign.

## 7. Identification analysis

For each context and basis, let the exact R3c1 baseline trajectory be
`y0`, and the two signed probe trajectories be `y+` and `y-`.

The measured odd differential response is:

```text
odd = (y+ - y-) / 2
```

The even/nonlinear residual relative to baseline is:

```text
even = (y+ + y-) / 2 - y0
```

Responses include:

```text
R, Z, vR, vZ, Ip
14 coil currents
48 wire/vessel currents for post-action audit only
```

Wire/vessel values are never controller inputs.

The following prospective gates apply to every context/basis unless stated
otherwise:

```text
environment / fresh TSC / fresh controller          256/256
exact initial visible and full-wire restart         256/256
causal trace and valid probe trace                  256/256
requested/applied probe schedule exact              256/256
requested/applied zero net                          256/256
runtime, solver, clipping, saturation failures            0
maximum current utilization                            <= 0.55

central-symmetry even velocity RMSE              <= 0.004 m/s
central-symmetry even position RMSE              <= 0.0005 m
central-symmetry even Ip RMSE                    <= 20 A

matched-history odd-response velocity RMSE       <= 0.006 m/s
matched-history odd-response position RMSE       <= 0.001 m
matched-history odd-response Ip RMSE             <= 40 A

selected R/Z-velocity response condition number      <= 25
```

The condition-number gate is computed per target/actuator/prefix stratum from
the four odd basis responses over task states 5 through the formal horizon.
Nonfinite or rank-deficient strata fail.

Formal tracking PASS is recorded but is not required for an identification
probe. Probe trajectories must never be counted as expert controls or merged
into a future MPC expert dataset.

## 8. Interpretation and advancement

R3c3 PASS means only:

- the preregistered `0.0075` two-mode, two-window response is locally
  bidirectional and sufficiently linear on the inspected restart bank;
- matched hidden histories do not exceed the preregistered response
  disagreement thresholds within that bounded envelope;
- a task-clock local-response model may be constructed for the next
  development controller.

It does not validate:

- formal restart control closure;
- unseen histories or initial states;
- unseen targets;
- mode-2/Ip response reidentification;
- amplitudes above `0.0075`;
- continuous delay/gain/slew;
- plant/Jacobian error, noise, disturbances, or long hold.

If R3c3 passes, Stage4.2R3c4 may be preregistered as a restart-integrated
target-conditioned deadline MPC using only the validated response envelope.
Its model selection may depend on current visible state, current coil
currents, target, and actuator estimate, but not pair/history labels.

If central symmetry fails, do not fit a linear bidirectional MPC at this
amplitude. Reduce the envelope only in a new preregistered identification
stage; do not relabel failed probes.

If matched-history response disagreement fails, do not proceed with a
visible-only restart MPC. Add causal history excitation/observer-state
estimation first.

If conditioning fails, expand the bounded basis prospectively, including
mode 2 or additional temporal shapes as indicated by the raw singular
vectors. Do not select new probes from individual formal outcomes.

BC, DAgger, and bounded residual RL remain blocked.
