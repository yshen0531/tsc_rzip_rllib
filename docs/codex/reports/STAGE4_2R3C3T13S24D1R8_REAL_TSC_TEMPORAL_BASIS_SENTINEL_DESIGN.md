# Stage4.2R3c3T13S24D1R8 real-TSC temporal-basis sentinel design

## Status and purpose

This design is frozen after the byte-identical D1R7 PASS and before D1R8
implementation, package construction, normalized-spec creation, Ray startup,
or any new TSC trajectory. D1R8 is a 108-rollout development-set real-TSC
safety sentinel for the temporal-basis substitution selected prospectively by
D1R7.

It asks one narrow question: do the six changed/new schedule rows execute all
four causal issue/cancel pairs through the full horizon on all 18 authentic
D1R2 contexts while preserving every original S24/D1R2 safety, restart,
causality, calibration, current, and blindness gate?

D1R8 does not fit a transition model, optimize or run an MPC, establish formal
tracking, validate a full identification grid, or produce expert data.

## Frozen identity

```text
stage
  Stage4.2R3c3T13S24D1R8
run name
  stage4_2r3c3t13s24d1r8_temporal_basis_substitution_safety_sentinel
campaign identity
  temporal_basis_substitution_safety_sentinel_v1
controller revision
  sequential_temporal_basis_card15_probe_v42r3c3t13s24d1r8_v1
package revision
  r42r3c3t13s24d1r8_temporal_basis_substitution_safety_sentinel_v1
```

## Immutable D1R7 source

The only spec source is the first accepted official D1R7 output:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r7_audits/
stage4_2r3c3t13s24d1r7_temporal_basis_substitution_preflight_20260803_212200_0c2311a_v1/
stage4_2r3c3t13s24d1r7_candidate_specs_v1.json
```

It must authenticate:

```text
D1R7 implementation / package checkpoints       da578de / 0c2311a
D1R7 design sha256
  5420e5ebf25efbdc0ad46b39809825d4fb94161fe7e1ee527fb0082d19109b9c
D1R7 candidate file sha256
  76075e12a411dbd4b0c210cc2e91a8978cb4de908b6f88a2c1ecd9cc44b279f7
D1R7 ordered candidate digest
  62869a4a028ff177b9eb83e509e7436a5937882081739cc3e548901989f05619
D1R7 detailed sha256
  7adcb1ef83b23eec5ed380b6717578abb665ea189ad5efbdcaafff99f48b26a2
D1R7 summary sha256
  aba8a400572ae3cd76c58e5c3ddbc3b92fa1222218583b0e97ec6df505aec01d
D1R7 manifest sha256
  c5d014ff3384c001833b54c3ae0a1a8139d6af790cf9f3c78fe418ec3ec58a25
D1R7 compact server forensics sha256
  50710895d8869c7026d7ac54adc1521402e9a76b72c3688e7d0bc2b1334a9eba
requested matrix digest
  c4430a13b679ad8dcceb72c259051a5eebad03da47d86816d46c4385cd811d77
```

The D1R7 route must be exactly
`TEMPORAL_BASIS_SUBSTITUTION_PREFLIGHT_PASS_REAL_SENTINEL_DESIGN_REQUIRED`.
Any mismatch stops before Ray or TSC.

## Exact 108-spec matrix

D1R8 retains the D1R7 candidate rows in their exact order without resampling
or post-result selection:

```text
specs / experiment IDs                       108 / 108
pairs / histories / snapshots                 9 / 18 / 18
horizon 35 / 37                                48 / 60
sequence rows 2,6,10,14,22,23                18 each
```

Every source spec already has the frozen D1R8 stage, campaign, controller,
primitive, schedule, snapshot, target, horizon, and blindness fields. D1R8
may normalize only run-local bookkeeping fields if implementation proves a
deep reversible comparison whose allowed paths were fixed before TSC. No
schedule, snapshot, target, controller, timing, gate, or availability flag may
change.

The direction-2 temporal rows are exactly `++++,+--+,-+-+,--++`; all other
matrix entries and the eight central-sign rows remain the D1R7 matrix.

## Frozen action and controller semantics

D1R8 reuses the exact causal S24/D1R2 Card15 sequential execution path. Each
rollout gets a fresh Ray actor, fresh `gotsc`/TSC process, and fresh causal
controller. The issue steps remain `10,13,15,17`; cancellations remain
`11,14,16,18`; issue/cancel effect states remain `11,14,16,18` and
`12,15,17,19`.

Every issue must pass the unchanged gates:

```text
finite values                                               true
exact 10-character center/target and reproduction          true
minimum active absolute coordinate                       >= 0.18
maximum absolute coordinate error                        <= 0.07
desired/applied current cosine                            >= 0.98
relative off-basis residual                               <= 0.10
incremental normalized action                             <= 0.25
total normalized action                                   <= 1.0
predicted current utilization                             <= 0.55
no saturation or clipping                                   true
```

Every cancellation must reproduce the stored center, exact zero target-jump
net, the same 0.25/1.0/0.55 gates, and the unchanged D1R2 extra online margin:

```text
online cancellation incremental normalized action <= 0.24
```

An action failing a guard is a structured semantic safe stop. It must be
saved and must not be applied or followed by a plant advance. It is not a TSC
runtime failure, but it fails the D1R8 design gate.

## Causality and blindness

The controller may use only current-rollout visible causal state, current
measured coil currents, trusted causal calibration state, task clock, and the
current step's preregistered requested coordinate. It may not use source or
current future values, source outcome/action/coil or wire current,
pair/history/partition/target/failure labels, or hidden wire current. Full
wire current may be recorded only after action choice. All saved forbidden-use
flags must be false and future action/measurement counts must be zero.

## Runtime and resume contract

```text
fresh real-TSC rollouts                                  108
fresh actors / TSC processes / controllers       108 / 108 / 108
full horizons                               48 x 35, 60 x 37
issue/cancel events on a full pass                 432 / 432
fixed Ray campaign capacity                               96
TSC task timeout                                      180 s
```

The initial run is fresh. Resume is allowed only after an infrastructure
interruption when package, config, exact ordered specs, snapshots, controller,
and all scientific fingerprints are unchanged. Every matching complete raw,
including a structured semantic safe stop, is immutable. Only missing or
byte-invalid raw may be rescheduled. Any controller/action/task/gate or
identity change requires a new stage.

## Required full-pass gates

All 108 raw JSON.GZ must strictly parse and match the exact spec and identity.
For every rollout:

```text
success / completed                                      true / true
trajectory / trace length                       horizon+1 / horizon
fresh TSC / controller                                    true / true
authentic restart exact                                         true
online causal trace and returned/recorded actions exact         true
solver success, finite states, no abnormal state                 true
exact eight-event Card15 calibration and zero net                true
exact eight-event sequential schedule                            true
four issue gates / four cancellation gates                       true
all four online cancellation increments <= 0.24                  true
current utilization <= 0.55                                      true
active sequential state cleared at horizon                       true
forbidden-use count                                                 0
```

The immutable 250/270 ms arrival deadlines and 350/370 ms hold endpoints are
recomputed from raw only as diagnostics. D1R8 is an identification safety
sentinel, not a formal-control or long-hold test.

## Independent server-side forensics

A separately packaged implementation must read all raw in place and recompute
strict count/bytes/hashes/inventory digest, exact spec coverage, restart,
causality, calibration, event order, each issue/cancel criterion, all 432
cancellation increments, recorded-action equality, solver/finite/current/
saturation/forbidden-use gates, snapshot/package fingerprints, and diagnostic
formal metrics. Verdict/state/summary alone are insufficient. Raw and
snapshots remain on the server; only compact audits and logs are downloaded.

## Frozen routes

```text
source/package/spec/snapshot failure before TSC
  TEMPORAL_BASIS_SENTINEL_PREFLIGHT_FAIL_NO_TSC

TSC/solver/restart/causality/raw/corruption/runtime failure
  TEMPORAL_BASIS_SENTINEL_RUNTIME_FAIL_STOP

structured action/current/Card15/zero-net/0.24 margin failure
  TEMPORAL_BASIS_SENTINEL_ACTION_MARGIN_FAIL_REDESIGN_REQUIRED

all 108 pass internal and independent raw gates
  TEMPORAL_BASIS_SENTINEL_PASS_FULL_REPLACEMENT_IDENTIFICATION_DESIGN_REQUIRED
```

## Scientific scope

A pass proves only finite clean development-set causal execution and action
headroom for these 108 changed/new rows on 18 authentic contexts. It
authorizes only a separately preregistered full replacement identification
campaign design, not its execution. It does not validate a transition model,
MPC, unseen targets, continuous delay/gain/slew, plant/Jacobian error, sensing
noise, disturbance recovery, independent long hold, expert data, BC, DAgger,
or RL. Probe trajectories are forbidden from expert datasets.

