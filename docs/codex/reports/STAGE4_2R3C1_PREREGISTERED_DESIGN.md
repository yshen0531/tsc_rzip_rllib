# Stage4.2R3c1 preregistered design

Date frozen: 2026-07-30 Asia/Shanghai

## 1. Purpose and scientific status

Stage4.2R3c1 is a new controller-development revision created after the
failed Stage4.2R3c result was fully inspected.

R3c proved that causal phase alignment is directionally useful: all 16
prefix-9 cases passed and its first action was much closer to a phase-aligned
R17 action than to phase zero. R3c nevertheless passed only 20/32 because its
phase selector matched against the ideal nominal trajectory, which
systematically underestimated the authenticated actual R17 closed-loop
visible phase.

R3c1 tests one frozen repair: match current visible R/Z/Ip against an
authenticated read-only R17 actual visible-state reference manifold for the
same target and actuator case.

R3c1 reuses the exact R3b snapshots after observing R3b and R3c. It is
development evidence only. It cannot validate independent hidden-history or
different-initial-state generalization.

Planned identities:

```text
stage
  Stage4.2R3c1

package revision
  r42r3c1_authenticated_visible_manifold_phase_mpc_v1

controller revision
  authenticated_visible_manifold_phase_mpc_v42r3c1
```

## 2. Locked source evidence

R3c1 uses the exact authenticated R3b run and R3c result:

```text
R3b source run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3b_runs/
  stage4_2r3b_confirmatory_hidden_history_initial_state_20260730_115526

R3b run inventory digest
  301a3ad2be01c83209d8e260c1a8c80f090d01afafb9c173f63cf9219caac8fc

R3b source fingerprint digest used by R3c
  5c5b6707908cf8777889ef2b00aeef93e7f516d8ac6915687efe7777fa280cee

R3c run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c_runs/
  stage4_2r3c_visible_state_phase_aligned_mpc_20260730_132807

R3c run inventory digest
  278395b364bb355c73b5f6de7461478b4bb239584a3f6bf9bf048aad12be9d13

R3c independent raw-forensics SHA-256
  395427285a5bad0de9611629df0a13ade037ddd4f0e30e993e475a56c3dbafaa
```

The four R3b selected pair identities and all eight exact snapshot manifests
remain unchanged:

```text
p5_q1_a0p900_gap2_settle4
p5_q2_a0p900_gap2_settle4
p9_q1_a0p750_gap2_settle4
p9_q2_a0p750_gap2_settle4
```

## 3. Frozen development matrix

The R3c matrix is reused exactly:

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

No case may be added, removed, or selected by R3c1 outcome.

## 4. Frozen visible reference-manifold construction

For each of the four target/actuator cases, authenticate its exact
Stage4.1R17 source control raw through the locked R3b/R17 source contract.
Extract only:

```text
R[k]
Z[k]
Ip[k]
```

for integer phases `k = 0..20`, inclusive.

The resulting four tables are frozen controller calibration data. Their
canonical content digest, source experiment IDs, raw hashes, and lengths must
be stored in the manifest and control specifications.

The following source fields are forbidden from the controller calibration
table and controller constructor:

```text
source actions
source suffix actions
future actions
future measurements from the current run
source coil currents
source wire currents
source observer or integrator state
snapshot pair identity
history-member identity
```

Using the frozen R17 R/Z/Ip table is explicitly same-digital-twin,
case-conditioned calibration. It is not evidence of unseen-target or
continuous-parameter generalization.

## 5. Causal phase-selection algorithm

At task step zero, select the reference phase using only current visible:

```text
current R
current Z
current Ip
```

For candidate phases 0 through 20, compute against the appropriate frozen
actual-visible R17 table:

```text
((R - reference_R[k]) / 0.03 m)^2
+ ((Z - reference_Z[k]) / 0.03 m)^2
+ ((Ip - reference_Ip[k]) / 2000 A)^2
```

Choose the minimum. An exact tie selects the earliest phase.

Target and actuator case select a static calibration table already present in
the task specification. Snapshot label, pair ID, history member, 48-wire
state, current-run future measurement, and the other member's state are not
inputs.

The selected phase is fixed for the task's initial alignment. There is no
post-result phase offset, per-pair override, or pass/fail-dependent rule.

## 6. Controller and formal-time semantics

All non-selector R3c controller semantics remain unchanged:

```text
task/formal clock starts at zero
reference/model phase starts at selected phase
reference/model phase advances monotonically
nominal reference and velocity use reference phase
model/Jacobian lookup uses reference phase
delay effects and queue priming use reference phase
braking and terminal transitions use aligned phase
fresh integrals and previous correction are zero
visible history contains current state only at start
plant TSC process is fresh
controller actor is fresh
```

Formal timing remains:

```text
slew 1.0: arrival <= 250 ms; hold through 350 ms
slew 0.9: arrival <= 270 ms; hold through 370 ms
```

R/Z tolerance, speed threshold, Ip thresholds, and arrival streak are
unchanged.

## 7. Mandatory offline gates

Before real TSC:

1. Authenticate the exact R3b run, selected pairs, snapshots, R17 control
   sources, and exact R3c run/audit hashes.
2. Prove the visible calibration tables contain only finite R/Z/Ip with
   phases 0..20, exact source experiment IDs, and exact raw hashes.
3. Prove original-start R17 visible states select phase zero in all four
   source cases.
4. Prove original-start streamed R17 trajectories reproduce the frozen
   online actions at machine tolerance.
5. Prove changes to hidden wire state do not change phase or first action.
6. Prove no source action or current-run future value is available to the
   phase selector or controller.
7. Prove task and phase clocks are distinct, monotonic, and recorded.
8. Prove the offline phase executes no real TSC and creates zero control raw.

Any failure stops the campaign.

## 8. Formal acceptance

R3c1 PASS requires:

```text
environment success                         32/32
fresh TSC process                           32/32
fresh controller                            32/32
initial visible restart exact               32/32
initial full-wire restart exact             32/32
causal controller trace                     32/32
phase trace valid                           32/32
future action replay                             0
future measurement use                           0
hidden-wire controller input                     0
formal contract pass                        32/32
both members pass in every pair group       16/16
```

No threshold, phase candidate range, scale, calibration table, case matrix,
or interpretation may change after observing R3c1.

## 9. Reporting and advancement

The result must separately report runtime, deployment, raw/snapshot
integrity, plant restart, causality, phase-design, formal control, and paired
hidden-history outcomes.

If R3c1 fails, preserve all raw evidence and create another development
revision only if raw diagnosis supports a concrete controller change.

If R3c1 passes, proceed only to Stage4.2R3d with newly preregistered,
prospectively generated unseen histories and initial states. R3d may not use
control-result selection.

New targets, continuous parameters, plant/Jacobian uncertainty, noise,
disturbance recovery, long hold, BC, DAgger, and bounded residual RL remain
blocked.
