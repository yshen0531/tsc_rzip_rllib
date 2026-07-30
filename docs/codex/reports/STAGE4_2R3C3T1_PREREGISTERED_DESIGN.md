# Stage4.2R3c3T1 preregistered design

## 1. Purpose

Stage4.2R3c3T1 is an identification-only campaign for bounded,
long-separation, zero-net transport responses around the exact R3c1
target-conditioned baseline.

It exists because the authenticated four-basis R3c3 bank failed the
prospective R3c4 feasibility gate:

```text
R3c1 baseline formal pass                         16/32
four-basis optimistic bounded oracle pass         16/32
failed contexts repaired                           0/16
```

R3c3T1 does not implement R3c4 and cannot be called an MPC control result.
Its trajectories are identification probes and are forbidden from all
expert, BC, DAgger, and RL datasets.

## 2. Frozen source evidence

R3c3 run:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3_runs/
stage4_2r3c3_restart_task_clock_local_response_identification_20260730_182427
```

Required fingerprints:

```text
R3c3 raw inventory
  88bcd02a5dd2ec4def60c1f2e7f2304fb57859836d3b9a34b090bfd91e00e563

R3c3 compact audit bank
  51bb4eeabfc8a4c5cc3983d75469f484a2278e6ef37cf03cf93ac650f9404b32

R3c3 controller bank
  6610dd4c434497240cb89ef0fbaa40716e42df68168efa66cddb919dd8679cf0

R3c3 compact-bank manifest
  a17322dcfc1d019de0455950c95e45b0b7d0f8f29fc3c68a22211481f261a066

R3c3 bank provenance
  5ec49166e59df915105d4411df36a9901db56f365594b83ff08bbc6abf3751f6

R3c1 baseline inventory
  3e82504dde79215ed34626531e4f926f5bd65404832790cba6a2eb2f2cc3a97e
```

The exact four selected snapshot pairs, eight history members, two targets,
and two actuator cases remain the locked development bank.

## 3. New experiment identity

```text
stage
  Stage4.2R3c3T1

run name
  stage4_2r3c3t1_long_separation_zero_net_transport_identification

controller revision
  long_separation_zero_net_transport_probe_v42r3c3t1

package revision
  r42r3c3t1_long_separation_transport_identification_v1

baseline controller
  authenticated_visible_manifold_phase_mpc_v42r3c1
```

R3c3T1 must create a new run directory and new experiment IDs. It may not
resume into or overwrite R3c3.

## 4. Context matrix

```text
4 selected snapshot pairs
× 2 hidden-history members
× 2 targets
× 2 actuator cases
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
gain [1.0, 1.0, 1.0]
```

Every rollout starts a fresh TSC process from the exact authenticated
snapshot and a fresh R3c1 controller. The exact R3c1 raw is the unperturbed
baseline; no baseline TSC rerun is permitted.

## 5. Frozen transport basis

Only modes 0 and 1 are probed:

```text
transport_mode0    mode 0
transport_mode1    mode 1
```

The maximum physical-mode component remains exactly:

```text
amplitude = 0.0075
```

No per-step amplitude expansion is allowed. The new information is temporal
separation, not a larger instantaneous command.

For positive sign, physical effect states are:

```text
states  3, 4, 5, 6, 7, 8       +0.0075
states 15,16,17,18,19,20       -0.0075
```

The negative member is the exact global sign inverse. Each requested
physical-mode schedule has:

```text
12 nonzero effects
exact zero net
maximum absolute component 0.0075
first physical effect at task state 3
last physical effect at task state 20
```

For actual delay `d`, an effect at state `s` is issued at:

```text
issue task step = s - d - 1
```

Therefore:

```text
delay 0 positive issue steps
  2,3,4,5,6,7 and 14,15,16,17,18,19

delay 2 positive issue steps
  0,1,2,3,4,5 and 12,13,14,15,16,17
```

All issue steps are causal and nonnegative. The transport lobe ends before
the unchanged 250/270 ms arrival deadline and leaves measured response
through the complete 350/370 ms hold horizon.

Rollout count:

```text
32 contexts × 2 transport bases × 2 signs = 128
```

No timing, sign, amplitude, basis, target, actuator, or context may be
changed after real outcomes are observed.

## 6. Controller input and causality contract

The probe controller may use only:

- current and past R/Z/Ip;
- current and past 14-coil currents;
- target R/Z/Ip;
- causal task-start actuator delay/gain/slew values;
- the exact R3c1 nominal controller;
- the prospectively fixed transport schedule for its own experiment.

It may not use:

- current-run future state, action, or actuator telemetry;
- R3c1 or R3c3 source actions or formal outcomes;
- source or current 48-wire/vessel current;
- pair ID, history label, prefix label, state-generation identity, or the
  other history member;
- any post-action telemetry when selecting the current action.

Pair/history and probe identities may exist in the orchestrator and audit
files. They must be stripped before controller construction. Hidden-wire
mutation must leave all offline actions and schedules unchanged.

The physical probe is added before the unchanged R3c1 absolute coefficient
bounds, scheduler, actuator delay queue, and 14-coil mapping. Requested and
applied probe deltas must agree to absolute tolerance `1e-12`; clipping is an
identification failure.

## 7. Immutable formal contract

```text
slew 1.0:
  arrive no later than 250 ms
  hold/evaluate through 350 ms

slew 0.9:
  arrive no later than 270 ms
  hold/evaluate through 370 ms

R/Z tolerance                 30 mm
speed threshold               0.1 m/s
Ip thresholds                 unchanged
arrival streak                unchanged
```

Formal tracking is recorded as a diagnostic but is not an identification
acceptance gate.

## 8. Required offline gate

Before real TSC, the exact deployed package must prove:

1. Exact R3b, R3c1, R3c2, R3c3, compact-bank, and baseline fingerprints.
2. Exact reconstruction of 32 contexts and 128 new experiment IDs.
3. Exact 12-effect schedule, sign inverse, `0.0075` maximum, and zero net for
   every spec.
4. Correct delay-aware issue clocks and first effect at task state 3.
5. Finite causal online action calculation for all 128 specs.
6. Exact preservation of the unperturbed R3c1 action when the transport
   coefficient is zero.
7. Hidden-wire and pair/history-label invariance.
8. No source result/action and no future current-run access.
9. Zero raw creation, zero plant advance, and zero real TSC.
10. Complete import closure, package/checksum verification, empty-directory
    deployment simulation, and full tests.

Any failure stops the real campaign.

## 9. Prospective identification gates

Execution:

```text
environment success / completed                     128/128
fresh TSC / fresh controller                        128/128
exact initial visible and 48-wire restart           128/128
causal exact probe trace                            128/128
requested/applied 12-effect schedule                128/128
requested/applied exact zero net                    128/128
runtime / solver / clipping / saturation failures         0
forbidden controller-input count                          0
maximum current utilization                            <= 0.55
```

For each context and transport basis:

```text
odd  = (y+ - y-) / 2
even = (y+ + y-) / 2 - y0
```

Central-symmetry gates:

```text
even R/Z velocity RMSE              <= 0.004 m/s
even R/Z position RMSE              <= 0.0005 m
even Ip RMSE                        <= 20 A
```

Matched-hidden-history gates:

```text
odd-response R/Z velocity RMSE      <= 0.006 m/s
odd-response R/Z position RMSE      <= 0.001 m
odd-response Ip RMSE                <= 40 A
```

Conditioning:

```text
transport-only velocity rank                2/2 per context
transport-only condition number             <= 25
combined R3c3+R3c3T1 velocity rank          6/6 per context
combined condition number                   <= 25
```

All gates apply to every required group. No failed stratum may be dropped or
reweighted after inspection.

## 10. Advancement gate back to R3c4

If identification passes, a new compact combined six-basis bank must be
recomputed server-side. Before R3c4 implementation resumes, the same
audit-only optimistic feasibility test must show:

```text
all 32 development contexts feasible
all six coefficients inside [-1,1]
unchanged formal timing and thresholds
no baseline pass regression
```

If even the optimistic six-basis oracle cannot close 32/32, R3c4 remains
blocked and no real MPC campaign is launched.

Passing R3c3T1 would validate only a finite development-bank transport
response. It would not validate a reliable restart controller, independent
histories, unseen targets, continuous actuator parameters, plant error,
noise, disturbance recovery, or long hold.

BC, DAgger, and bounded residual RL remain prohibited.
