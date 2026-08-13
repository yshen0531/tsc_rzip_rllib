# R_geo/Z_geo 1 ms NR2R2B0 source q0-baseline design

Status: prospectively frozen on 2026-08-13 before implementation, server
deployment or outcome inspection.

Stage identity:

```text
rgeo-zgeo-1ms-nr2r2b0-source-q0-baseline-v1
```

NR2R2A proved that the existing campaign has no independent all-q0 baseline
and cannot separate common drift from action/history response.  A minimal
read-only server check then proved that the canonical simulation source has a
complete 1100 ms directory but no existing 1101--1116 ms continuation.  The
Card15 hash subcommand in that check had a shell-quoting error and produced no
valid Card15 hash; this is a tooling error only.  It did not run TSC or alter
the directory-existence result.

NR2R2B0 therefore generates a fresh q0-command baseline from the fixed 1100 ms
source.  It asks whether that baseline is reproducible and whether q0 itself
is a usable short source hold/backup candidate.  It does **not** assume q0 is
hold or recovery, introduce a probe, fit a model, or qualify transport.

## 1. Unchanged hard contract

```text
fixed source                                  1100 ms
period                                           1 ms
coil order                                        TSC
per-coil single-turn step                <= 0.3 A absolute
Card15 unit                                  kA-turn
R_geo/Z_geo                      paired same-boundary definition
boundary invalid                              fail closed
Ip                                    observed hard-safety state
```

The exact q0 command is the 14-field Card15 quantization of the source coil
readback using the existing NR1R2 implementation.  The first source-to-q0
transition is retained and labelled as source-to-q0 settling.  It is not
silently discarded or called autonomous drift.

## 2. Frozen experiment matrix and budget

```text
independent reset rollouts                      6
issued q0 commands per rollout                 32
states per rollout                             33
maximum authentic plant advances              192
evidence purpose            interface_baseline_qualification_only
model/expert fitting use                 forbidden
```

All six rollouts use exactly the same q0 Card15 target at every issue step.
There are no signed pairs, pulses, cumulative ramps, waypoint references,
adaptive updates, Oracle branches or controller actions.  A failure stops the
remaining matrix; no resume under changed semantics is allowed.

## 3. Per-step fail-closed boundary

Before every issue and immediately after every successor state, require:

1. the exact paired-boundary parser succeeds and side matches
   `R_geo < R_mid`;
2. TSC return code is zero and state is not abnormal;
3. time is exactly `1100 + state_index` ms;
4. the active 14 Card15 fields equal frozen q0;
5. command-to-command and readback-to-readback single-turn slew are each
   exactly audited and no greater than `0.3 A`;
6. all actual coil currents remain inside unchanged configured absolute
   limits;
7. `R_geo` remains inside the limiter midplane intersection;
8. `|R_geo-R_geo(1100)| <= 0.05 m` and
   `|Z_geo-Z_geo(1100)| <= 0.05 m`;
9. Ip sign is unchanged and
   `|Ip-Ip(1100)| <= 0.10*|Ip(1100)|`.

The rejected action is not applied when a pre-issue check fails.  A failed
post-state is retained and no later action is issued.

## 4. Repeatability qualification

Every rollout is independently reset from the canonical 1100 ms source.  The
first rollout is the reference.  For every later rollout and every matching
state, require maximum absolute difference no larger than:

```text
R_geo/Z_geo/R_mid geometry                  1e-12 m
Ip                                           1e-9 A
14 actual coil currents                      1e-9 A
48 wire-current components                   1e-9 A
active Card15 fields                           exact
artifact SHA-256                               exact
```

This qualifies deterministic same-source q0-baseline replay only.  If the
floor is nonzero, the measured maxima replace zero as a mandatory future
uncertainty floor; thresholds are not weakened after the result.

## 5. Separate q0 hold/backup diagnostic

Completing safely and repeatably is not sufficient to call q0 a hold.  A q0
short-hold candidate additionally requires, in every rollout:

```text
inner source corridor, all states       |dR|,|dZ| <= 0.025 m
inner Ip corridor, all states           |dIp| <= 0.05*|Ip0|
terminal window                                states 24..32
each terminal transition              |Delta R|,|Delta Z| <= 0.0001 m
terminal-window net drift              |Delta R|,|Delta Z| <= 0.001 m
```

The per-transition geometry limit equals `0.1 m/s` per axis at 1 ms and is a
new prospective q0-hold criterion, not revival of the retired old arrival
contract.  Passing it proves only a 32 ms source hold candidate under the q0
baseline.  It does not prove recovery after a perturbation or at another
anchor.  Failing it while the outer boundary and repeatability pass means q0
is a valid baseline but not an active backup/hold.

## 6. Primary and independent evidence

The primary runner saves all 33 compact states, all 32 action records and the
five required artifact hashes per state.  Large raw stays server-side.  A
structurally separate server-side auditor must reparse every saved raw state
directory and independently reproduce Card15, geometry, Ip, current, timing,
repeatability and q0-hold metrics before any result is accepted.

## 7. Frozen routes

```text
offline/package/source gate failure
  ONE_MS_NR2R2B0_OFFLINE_FAIL_NO_TSC

runtime/interface/Card15/slew/current/boundary/Ip failure
  ONE_MS_NR2R2B0_SAFETY_OR_INTERFACE_FAIL_STOP

six complete baselines but repeatability failure
  ONE_MS_NR2R2B0_BASELINE_REPEATABILITY_FAIL_STOP

safe repeatable baseline; q0 fails hold criterion
  ONE_MS_NR2R2B0_BASELINE_REPEATABLE_Q0_NOT_HOLD_ACTIVE_RECOVERY_REQUIRED

safe repeatable baseline; q0 passes short-hold criterion
  ONE_MS_NR2R2B0_Q0_SHORT_HOLD_CANDIDATE_PERTURBATION_RECOVERY_DESIGN_REQUIRED
```

Both last routes complete the baseline objective.  Neither authorizes an
atlas, probe, position-dependent model, moving-prefix Oracle, controller,
MPC, RL or expert data.  If q0 is not a hold, the next stage must design an
active source hold/recovery discriminator before any atlas probe.  If q0 is a
short-hold candidate, a separate perturbation/recovery qualification is still
required.
