# Stage4.2R3c3T13S2 quantized-actuation and causal-observability audit design

## 1. Prospective status and purpose

This design is frozen after the final T13S1 scientific FAIL classification
and before T13S2 audit code or output exists. T13S2 is a read-only redesign
audit. It creates no controller and runs no Ray, `gotsc`, TSC, plant step, or
snapshot.

T13S2 asks two source-constrained questions:

1. Can the exact finite-precision Card15 path reconstruct every observed
   T13S1 coil-current transition from the current-run measured current and
   trace action?
2. At the frozen transport and braking issue times, do any distinct T13S1
   histories collide exactly in the causal observable state while producing
   different applied-current/plant transitions?

This audit does not try to make T13S1 pass and does not fit or certify a
plant predictor. It determines the actuator and observer interface that a
later set-valued transition model must use.

## 2. Immutable evidence and identity

```text
stage
  Stage4.2R3c3T13S2
audit identity
  exact_card15_and_causal_observable_sufficiency_v1
source run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s1_runs/
  stage4_2r3c3t13s1_minimal_transition_sentinel_20260801_ecc05f6
raw count
  52 JSON.GZ
raw bytes
  2,463,366
raw digest
  de2be508888aa503628538a795474fbf70788252e7913f87af7603c5bc034603
```

The audit must authenticate the exact official state, manifest, resolved
config, raw inventory, snapshot audit, and package fingerprint before reading
transition values. Raw is read in place on the server and is never copied or
modified. Compact audit JSON may be downloaded directly without an archive.

## 3. Exact actuator reconstruction contract

For every one of the 52 runs and every one of 50 transitions, reconstruct
all 14 next coil currents from only:

```text
current-run measured Icoil_k
current-run trace action_norm_tsc_k
source max_delta_current_a_per_step
source/spec slew scale
source current limits
authenticated TSC-order turn counts
the exact inputa.format_number implementation
```

For coil `i`, the source contract is:

```text
desired_i = clip(Icoil_k,i + action_k,i * max_delta_i,
                 min_current_i, max_current_i)
card15_i  = parse(format_number(desired_i * turns_i / 1000))
predicted_Icoil_k+1,i = card15_i * 1000 / turns_i
```

`max_delta_i` is the exact resolved runner step authority for that run. No
nominal value may be substituted when the resolved config supplies it.

The exact reconstruction inventory is prospectively fixed at:

```text
transitions                         52 * 50 = 2,600
coil components               52 * 50 * 14 = 36,400
```

Report absolute residuals, exact-equality counts, formatted Card15 strings,
grid steps, zero-effect actions, and clipping counts. The source-derived
numerical gate is `1e-9 A` after conversion back to single-turn current; this
gate checks serialization reconstruction, not plant-model quality. Any
failure routes to `ACTUATOR_MAPPING_IMPLEMENTATION_GAP` and forbids new TSC
until the source mismatch is resolved.

The audit must also recompute the 24 signed first-effect groups using actual
reconstructed applied increments. Requested action symmetry, applied-current
symmetry, and plant symmetry remain separate fields. No failed symmetry gate
may be normalized away or reinterpreted.

## 4. Causal observable state

At an issue step `k`, the allowed clean-state feature is constructed only
from the current run:

```text
formal task step k
target R/Z/Ip
R_k, Z_k, Ip_k
backward finite-difference vR_k, vZ_k when k > 0
an explicit unknown-velocity flag/interval when k = 0
measured 14-coil current Icoil_k
all commands already issued at steps < k
the resulting authenticated delay queue
known finite development actuator setting for this task
```

The following are forbidden from the feature and every future controller:

```text
pair/history/prefix labels
source or current wire/vessel currents
source actions or future source actions
source results or formal verdicts
current-run future measurements
future probe schedule
nearest R17 phase as formal time
```

Wire-current differences may appear only in a separately labelled offline
latent-state diagnostic. They may not select a model or change a route.

## 5. Collision and separability audit

For each transport/braking issue group:

1. compare every allowed feature field exactly before normalization;
2. hash the exact causal feature and already-issued queue;
3. group exact feature collisions;
4. within each collision, compare reconstructed applied increments and the
   next plant increment `(R, Z, Ip)`;
5. report finite pairwise distances using fixed physical scales
   `(0.03 m, 0.03 m, 0.1 m/s, 0.1 m/s, 10 kA, source current scales)`;
6. report, but do not threshold-select, nearest cross-history distances and
   response differences.

The route rules are exact and do not depend on a fitted threshold:

```text
same exact causal feature and same exact applied increment,
but different next plant increment
  -> EXACT_OBSERVATIONAL_ALIAS_REQUIRES_SET_VALUED_MODEL

no such exact collision
  -> FINITE_CLEAN_SEPARATION_ONLY
```

`FINITE_CLEAN_SEPARATION_ONLY` is not observer certification. Four
development contexts cannot validate independent hidden histories,
measurement noise, arbitrary restart states, or continuous parameters. In
both routes, unresolved latent effects remain a multi-hypothesis/tube set.

## 6. Scientific classifications and forbidden claims

T13S2 must separately report:

```text
runtime/environment error
packaging/import error
raw/snapshot corruption
statistics/reporting error
actuator serialization/model gap
exact observational alias
finite clean separability
unvalidated observer/noise/history extrapolation
real MPC tested
real TSC executed
```

The last two must be false. T13S2 cannot prove global reachability or
unreachability and cannot repair the official T13S1 result. It cannot use
T13S1 probes as expert trajectories.

## 7. Output and validation contract

The audit writes a new directory containing only:

```text
stage4_2r3c3t13s2_quantized_observability_audit.json
stage4_2r3c3t13s2_quantized_observability_manifest.json
```

The manifest records source hashes, raw digest, output hashes, raw files
copied/modified `0`, and controller/Ray/`gotsc`/TSC/plant steps `0`.

Before server execution:

- local compile and JSON parse;
- focused synthetic tests for positive/negative Card15 fields, current
  clipping, zero action, exact collision, non-collision, and forbidden fields;
- complete repository tests;
- isolated direct-copy import/compile/test simulation;
- package/checksum verification;
- server `bash -n`, package verification, venv import/compile, focused tests,
  and complete tests.

## 8. Authorized continuation after the audit

T13S2 may authorize only implementation and unit validation of:

1. an exact quantized Card15 actuator transition primitive;
2. a causal observer-state schema with unknown initial velocity;
3. a multi-hypothesis/tube transition interface;
4. a separately preregistered minimal lattice-aligned holdout sentinel if
   existing immutable raw cannot validate that interface.

It does not authorize a full identification campaign, a real MPC campaign,
R3c4, a T11 bank, expert data, BC, DAgger, or bounded residual RL.

Formal timing and physical thresholds remain unchanged.
