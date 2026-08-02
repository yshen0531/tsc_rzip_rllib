# Stage4.2R3c3T13S7R1 campaign-specific effect-contract design

## Status and scope

This design is frozen after the final T13S7 output and campaign-specific
source/raw timing forensic, and before any T13S7R1 model, feature-distance,
support, tube, collision, or validation output is computed. T13S7R1 is a new
zero-new-TSC read-only audit identity.

T13S7 remains final as
`CAUSAL_MULTI_HYPOTHESIS_TUBE_INSUFFICIENT_REDESIGN`. T13S7R1 may not rewrite
that result. It repairs one audit-design assumption in a new output: S1 and
S5 have different physical effect contracts.

## Single allowed correction

```text
S1 first/cancel effect states
  issue_step + action_delay_steps + 1
  cancel_step + action_delay_steps + 1
  equivalently the authenticated S1 spec declarations

S5 first/cancel effect states
  issue_step + 1
  cancel_step + 1
```

The extractor must authenticate all 24 S1 and 32 S5 odd-current first-effect
states against the frozen campaign-specific timing forensic. Any mismatch
fails closed.

## Everything else remains frozen

T13S7R1 must preserve T13S7 exactly for:

```text
S1/S5 raw identities and official audit hashes
eight contexts and 112 signed probes
causal feature schema and fixed feature scales
unknown velocity/current-history flags at restart step zero
four leave-one-context-out folds per stratum
two nearest training contexts plus exact-distance ties
0.15 measured-input row-space support threshold
minimum-norm per-context local maps
source-defined expected rank: S1 rank 3, S5 rank 4
numerical floors and 1.5 residual multiplier
3 mm / 0.01 m/s / 1000 A component tube caps
componentwise containment
0.10 nearest scaled center-relative-error threshold
exact feature/input collision audit
formal timing and all prohibitions
```

Allowed selector/model inputs remain only current/past R/Z/Ip, causal
velocity and known flags, measured coil current and past difference, target,
formal issue time, and finite delay/slew. Pair/q/history/prefix/source IDs,
source action/result, wire/vessel currents, and future values remain
forbidden from features, selection, input support, maps, tubes, and
prediction.

## Frozen gates

```text
S1 raw/audit authentication                           52 / 52
S5 raw/audit authentication                           68 / 68
campaign-specific effect timing                       56 / 56
trace identity                                       120 / 120
signed response extraction                           112 / 112
pre-effect causality                                 112 / 112
local rank                                             16 / 16
local non-vacuous tube                                 16 / 16
leave-one-context-out folds                                  8
supported hypothesis coverage                        112 / 112
componentwise containment                            112 / 112
nearest scaled relative error <= 0.10                112 / 112
disjoint exact causal aliases                                0
forbidden feature/trace inputs                               0
```

Unsupported rows remain failures and may not be counted as zero-error
successes. All source data are already consumed and none is blind.

## Outcome routes

```text
CAMPAIGN_SPECIFIC_CAUSAL_MULTI_HYPOTHESIS_CANDIDATE_Q3_HOLDOUT_REQUIRED
  every frozen gate passes;
  authorize only a new prospective q3 independent-history holdout design.

CAMPAIGN_SPECIFIC_CAUSAL_MULTI_HYPOTHESIS_TUBE_INSUFFICIENT_REDESIGN
  any gate fails;
  redesign unified excitation support, causal observer state, or transition
  tube before another physical campaign.
```

Neither route authorizes a controller, real MPC, expert data, BC, DAgger, or
bounded residual RL. No formal threshold or deadline changes.
