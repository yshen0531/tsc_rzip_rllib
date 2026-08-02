# Stage4.2R3c3T13S13 recurrent causal sequence-tube identification design

## Status and scientific question

This design is frozen after the final T13S12 result and before any T13S13
model fit, response output, route, new baseline, probe, Ray task, `gotsc`, or
TSC execution. Read-only inspection before freezing was limited to source
identity, factor coverage, snapshot availability, existing q1/q2 field
contracts, and controller/actuator code required to define a deployable
causal interface.

T13S12 proved that an affine observer over only eight consumed histories is
not an adequate response predictor. T13S13 asks a narrower prospective
question: can a deterministic recurrent observer and a fail-closed
set-valued one-step response map generalize across all 72 authentic R3b
restart histories when training, calibration, and fresh holdout are separated
by whole source pairs?

T13S13 is identification only. It is not a controller or MPC test. Probe
trajectories are permanently forbidden from expert data.

## Immutable sources

Authenticate the exact R3b source run:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3b_runs/
stage4_2r3b_confirmatory_hidden_history_initial_state_20260730_115526

pair results SHA-256
  a0bc31e17db452fdda93e27ce89116e352f7ab9dc543a671edc930649f1d726e
state specifications SHA-256
  433621303cb52b7fb5d4a7e3faeb7ce07132f1d98b2f9418a6999fbb2d740b83
state results SHA-256
  de875fb5c9c2f88d4f0ccd274734b5a4a2c107a98927028dd9300e64588f1b57
manifest SHA-256
  4fdd037bfd1f5367e4ea374a9193b8084795ec2f928ad6e87eebb2c1ee4a53fe
server audit SHA-256
  f1e907888e19846d07099714d4b581e26aac80c5675a373364d396db78130831
snapshot checks SHA-256
  a979757e4a62ece89635754a2885308549dbd0b8b88f8e849b03f0e648e0b927
```

The source contains 36 complete pairs and 72 valid, unique restart snapshot
identities:

```text
common prefix       5, 9
nullspace direction 1, 2
amplitude           0.600, 0.750, 0.900
gap                 2, 3, 4
history member      plus_first, minus_first
```

All 72 histories are in scope, including histories that did not pass R3b's
old pair-selection gate. That old gate is an outcome and may not be used to
drop a history. T13S13 baseline safety gates determine whether a phase may
proceed to probes.

The only pre-existing response evidence allowed is:

```text
T13S5 q2 raw files / digest
  68 / 09ee846d2fd8c2a516ec01f1b91bcbf8f303885c2377373000ab85dfc45e0f01
T13S9 q1 raw files / digest
  68 / 9ccc67d5eda2b0710d658812207d99666a50af352e42d950086b694a3fa928ad
```

Those 136 trajectories cover eight contexts from four whole source pairs.
They are consumed training data only. Their controller target is reconstructed
as the authenticated payload base target plus the raw specification offsets.

## Frozen pair split

Splitting is by complete source pair, so its two hidden-history members can
never cross partitions.

```text
training
  all 12 amplitude-0.600 pairs                         24 contexts
  consumed p5 q1/q2 amplitude-0.900 gap-2 pairs        4 contexts
  consumed p9 q1/q2 amplitude-0.750 gap-2 pairs        4 contexts
                                                        32 contexts

calibration
  all amplitude-0.900 pairs except consumed p5 q1/q2 gap-2
                                                        20 contexts

fresh holdout
  all amplitude-0.750 pairs except consumed p9 q1/q2 gap-2
                                                        20 contexts
```

The 32/20/20 partition is exhaustive and disjoint. Split construction may
read only source factor metadata and the frozen consumed-identity list.
`accepted`, `selected`, source control outcomes, future response values, and
snapshot hidden-current contents are forbidden split inputs.

Four controller regimes are used:

```text
A  nominal target    delay 0  slew 1.0
B  nominal target    delay 2  slew 0.9
C  R+10/Z-10 mm      delay 0  slew 1.0
D  R+10/Z-10 mm      delay 2  slew 0.9
```

The two histories of a pair always receive the same regime. The consumed p5
pairs retain D and the consumed p9 pairs retain A. Sort new pairs by exact
`pair_id`; assign training amplitude-0.600 pairs cyclically A/B/C/D from A,
calibration pairs cyclically A/B/C/D from A, and holdout pairs cyclically
A/B/C/D from C. This gives every partition all four regimes without using an
outcome. The resolved context table and its digest are immutable once the
zero-TSC preflight writes them.

Pair, prefix, amplitude, gap, history-member, source experiment ID, and split
labels are audit metadata only. They are forbidden model/controller inputs.

## Frozen action lattice and schedules

Each context has one exact lattice baseline and 16 signed probes:

```text
windows      transport, braking
directions   mode0_without_coil8, mode0_coil8_component, mode1, mode2
signs        -1, +1
```

Use the exact T13S9/S5 Card15 lattice, local grid step, one-sided coil-8
split, return-first cancellation, per-coil readback interval, and guards:

```text
maximum incremental normalized action L-inf   0.25
maximum total normalized action abs           1.00
maximum current utilization                    0.55
minimum coil-space cosine                      0.98
maximum relative off-mode residual             0.15
Card15 output grid                              1e-6 kAt
```

Post-queue schedules are:

```text
delay 0 transport issue/cancel 2/3,   effect states 3/4
delay 0 braking   issue/cancel 16/17, effect states 17/18
delay 2 transport issue/cancel 0/1,   effect states 1/2
delay 2 braking   issue/cancel 14/15, effect states 15/16
```

Every probe must be exact zero net after cancellation. The controller never
receives the future probe schedule. Probe and cancellation are wrappers
around a freshly initialized causal R3c1 controller and are absent from the
baseline controller's information.

## Frozen rollout counts and open order

The complete equivalent matrix is:

```text
contexts                                                72
baselines                                               72
signed probes                                         1152
rollouts per context                                     17
total equivalent raw                                   1224
consumed training raw                                   136
new raw required                                       1088
```

New work is strictly ordered:

```text
Phase A1  24 new training baselines
Phase A2 384 new training probes
Phase B1  20 calibration baselines
Phase B2 320 calibration probes
Phase C1  20 fresh-holdout baselines
Phase C2 320 fresh-holdout probes
```

Before each probe subphase, all new baselines for that partition must pass
runtime, exact restart, trace causality, solver, abnormal-state, saturation,
current-utilization, action-lattice, Card15 interval, and complete-horizon
gates. Formal tracking is recorded but is not a probe-safety gate. Any
baseline safety failure stops the stage; the failed context may not be
dropped.

Phase B raw/spec outputs may not be created or opened until Phase A freezes
an eligible model. Phase C raw/spec outputs may not be created or opened
until Phase B freezes the final tube. A fresh process and an auditable
open-order guard are required at each boundary. Resume may preserve only
complete raw with identical source, controller, probe, split, package, and
formal semantics.

## Frozen deployable causal sequence

For a response whose issue state is `s`, encode states zero through `s` in
chronological order. Each state has exactly 59 fixed-scaled fields:

```text
 3  R/Z/Ip target error divided by 0.03 m, 0.03 m, 10000 A
 2  backward-causal vR/vZ divided by 0.1 m/s
 1  velocity-known flag
14  measured TSC-order coil currents divided by declared half ranges
14  backward measured current differences divided by half ranges
 1  current-difference-known flag
14  previous selected normalized actions
 3  previous issued desired physical mode coefficients
 1  previous-command-known flag
 1  task state index divided by 37
 1  known delay divided by 2
 1  `(slew - 0.95) / 0.05`
 3  absolute target coordinates relative to the frozen base target, divided
    by 0.03 m, 0.03 m, 10000 A
```

At state zero, backward differences and previous commands are zero and their
known flags are false. At state `t>0`, previous-command fields come only from
trace `t-1`. The action being evaluated at the current issue state is never
placed in the history; it is the separate candidate input below.

The observer may use only current-run measurements and commands already
issued by the same controller. Source actions/results, source or current wire
and vessel currents, current-run future measurements/actions, pair/history/
prefix/amplitude/gap/split labels, response outcomes, and post-effect values
are forbidden.

## Frozen pre-action actuator input

The response input is not the measured first-effect current. For the
candidate and no-probe center, run the already frozen pure Card15 actuator
calculation at the identical current issue measurement. Define:

```text
u_center = candidate nominal predicted readback current
           - baseline nominal predicted readback current
```

Scale its 14 TSC-order components by declared half ranges. The causal input
box radius is the componentwise sum of the candidate and baseline frozen
readback radii. Both center and radius exist before writing the candidate
action.

The actual first-effect measured-current difference is outcome evidence. It
must lie inside the pre-action input box, but it is forbidden from the
observer, fit coordinate, prediction center, split, hyperparameter choice,
or tube calibration. This rule corrects the optimistic S12 interface.

## Frozen recurrent observer and response family

Use NumPy only and deterministic `PCG64` seed `20260802`. For each candidate,
the reservoir has width 32. Draw recurrent and input weights from a standard
normal distribution, rescale the recurrent matrix to unit spectral radius,
and update:

```text
candidate = tanh(rho * W @ h + 0.25 * Win @ [1, z_t])
h_next    = (1 - leak) * h + leak * candidate
```

The candidate grid is fixed before data:

```text
rho             0.35, 0.65, 0.85
leak            0.50, 1.00
observer rank   4, 8, 12
ridge           1e-8, 1e-6, 1e-4
```

For each whole-pair training fold, center final reservoir states on fold
training contexts, compute a training-only SVD, retain the requested observer
rank, and whiten retained scores by their training RMS. Build a training-only
rank-4 SVD basis of `u_center` and whiten its coordinates by training RMS.
Fit the zero-at-zero-action readout

```text
y_scaled = kron([1, observer_scores], action_scores) @ J
```

with the declared ridge. The interaction must have exact requested column
rank, finite whitened condition `<=30`, finite signal, and no nonzero
intercept at zero action.

Candidate selection uses leave-one-whole-source-pair-out training CV only.
Ineligible candidates are discarded. Eligible candidates are ordered by:

1. smallest maximum held scaled center-relative error;
2. smallest mean held scaled center-relative error;
3. smaller observer rank;
4. smaller `rho`, then smaller `leak`, then smaller ridge.

No calibration or holdout file, value, count beyond the frozen design, or
outcome may affect this choice. Refit the chosen architecture on all training
contexts and freeze its complete numeric artifact and SHA-256.

## Frozen support, tube, and response gates

The response is the causal first-effect difference from the exact same-
context baseline in R, Z, backward-causal vR, backward-causal vZ, and Ip.
Use scales:

```text
(0.03 m, 0.03 m, 0.1 m/s, 0.1 m/s, 2000 A)
```

Scaled center-relative error is the exact T13S9 norm ratio with its unchanged
numerical floor and must be `<=0.10`.

Support is independent of the interaction design:

* history support compares fixed-scaled, zero-padded 17-state sequences plus
  masks only within the same delay/window. Its radius is 1.25 times the
  maximum leave-one-pair-out nearest-training distance, capped at 0.15;
* action support requires rank 4, original 14-coil projection residual
  `<=0.15`, and each whitened action coordinate inside the training min/max
  interval expanded by 10%.

Unsupported values fail closed. Exact or near-exact causal-history/action
aliases across disjoint source pairs are reported and forbidden.

After Phase A, a provisional component radius is the numerical floor plus
`1.5 * max_abs_training_residual`. It must remain below:

```text
(0.003 m, 0.003 m, 0.010 m/s, 0.010 m/s, 1000 A)
```

Phase B does not refit the center model. The final base radius is the
numerical floor plus `1.10 * max(max_abs_training_residual,
max_abs_calibration_residual)`. For every row, add the exact interval-linear
propagation `abs(J_effective) @ action_input_radius`. The resulting total
radius must remain under the same caps. The complete center model, support,
and final tube are then frozen before Phase C.

Calibration containment is reported but is not independent evidence because
calibration sets the base radius. Phase C is the independent gate. Every
holdout signed row must pass history support, action support, pre-effect
causality, actuator input-box containment, componentwise response
containment, and center-relative error `<=0.10`.

For all newly executed central pairs also retain the unchanged identification
gates: required observed odd current signal, even/odd symmetry `<=0.10`,
zero net, Card15 schedule/application, no saturation, maximum current
utilization `<=0.55`, and no forbidden trace input.

Exact complete-stage counts are:

```text
source snapshot identities                                72 / 72
contexts / baselines / signed probes             72 / 72 / 1152
central signed groups                                    576 / 576
pre-effect causality                                     1152 / 1152
actuator input-box containment                           1152 / 1152
training contexts / response rows                         32 / 512
calibration contexts / response rows                      20 / 320
fresh holdout contexts / response rows                    20 / 320
fresh holdout support / containment / error              320 / 320 each
forbidden input/trace/open-order violations                         0
```

All raw JSON.GZ, snapshots, and large inventories stay on the server. Only
compact audits, manifests, hashes, model/tube artifacts, complete logs, and
row-level compact metrics may be downloaded.

## Formal timing and routes

The observation horizons remain 350 ms for slew 1.0 and 370 ms for slew 0.9.
Arrival remains due by 250/270 ms and hold is evaluated through 350/370 ms.
No deadline, tolerance, streak, action, or current gate changes. This is not
an independent long-hold test.

The only final routes are:

```text
RECURRENT_CAUSAL_SEQUENCE_TUBE_HOLDOUT_PASS_MULTISTEP_AUDIT_REQUIRED
  every frozen gate passes; authorize only a zero-new-TSC causal multistep
  rollout audit over complete held trajectories before any MPC controller.

RECURRENT_CAUSAL_SEQUENCE_TUBE_INSUFFICIENT_REDESIGN
  any gate fails; stop, preserve all evidence, and redesign the observer,
  action envelope, or identification experiment without dropping failures.
```

Neither route authorizes expert-data generation, BC, DAgger, or bounded
residual RL. A passing one-step holdout is necessary but not sufficient for
a reliable MPC expert.
