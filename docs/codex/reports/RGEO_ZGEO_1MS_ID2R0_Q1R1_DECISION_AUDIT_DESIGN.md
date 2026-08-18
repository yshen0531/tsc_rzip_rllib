# ID-2R0 Q1R1 erratum and route-decision audit design

## Purpose

ID-2Q1R1 remains final as
`ONE_MS_ID2Q1R1_NO_ELIGIBLE_SHARED_LATENT_MODEL_REDESIGN`. This stage does
not weaken that verdict, select a model, or open calibration. It corrects a
reporting attribution error and performs one bounded retrospective audit to
choose the next evidence identity.

The Q1 evaluator appends family metrics in `sorted(group_id)` order but did
not persist the corresponding family IDs beside the arrays. The result
report consequently attributed q03's four ridge wrong-way responses to
`h03`; they belong to `f03`. Likewise q01 ridge family ranking regrets
`0.642/0.847/0.024/0.013` correspond to `f01/f05/h01/h05`, not to a proposed
`h01/h03/h05` bridge. This is a reporting/attribution error only. Q1's model
outputs, gates, final FAIL, and absence of a model artifact are unchanged.

## Frozen evidence and execution boundary

ID-2R0 consumes only:

- the frozen ID-2Q1R1 config, result, and independent audit;
- the 40 primary K1 and 40 primary P1 development cells already consumed by
  Q1;
- their integrity replays with zero statistical weight.

N1 calibration/challenge records, every unopened holdout, server raw outside
the tracked K1/P1 compact identities, and all future outcomes are forbidden.
The stage performs zero TSC calls, zero resets, and zero plant advances.

Because Q1 did not retain fold coefficients or per-cell predictions, ID-2R0
may deterministically refit exactly the eight frozen Q1 fold candidates and
the twelve already frozen GRU members. It may not change a feature, fold,
seed, epoch, loss, ridge value, normalization, candidate, or gate. Exact
reproduction of Q1's aggregate result is an integrity prerequisite. No
full-data fit or model payload is emitted.

## Required explicit evidence

The audit persists prediction and metric rows keyed by
`candidate/fold/family_id/cell_id/origin/horizon`. It reports:

1. corrected per-family response NRMSE, peak cosine, and action-ranking
   regret;
2. nominal, first-effect, dwell, return-edge, and tail attribution using only
   action clocks derivable from the owned issued sequence;
3. blockwise feature rank and condition without treating numerical
   whitening as a scientific repair;
4. exact schedule-stratum support and critical replay coverage;
5. one and only one no-fit nearest-history transfer diagnostic;
6. measured R/Z response-angle coverage both at each action's own peak and
   across all observed 1--8 ms response samples.

The nearest-history diagnostic uses the already frozen O0 96-dimensional
deployable causal prefix: current R_geo/Z_geo/Ip, fixed 1/2/4-step state
deltas, current 14-coil actual current, and fixed 1/2/4/8/16-step owned issued
history, with the O0 physical scales and RMS distance. A training response
is eligible only when its candidate future Card15 sequence over the measured
horizon is exactly equal to the held candidate sequence. Family, sign,
direction, conditioner, and schedule names are forbidden distance features.
There is no search over distance weights, `k`, kernels, normalization, or
thresholds. Unsupported cells are abstentions, not errors silently removed
from the denominator.

The local diagnostic is route evidence only. It cannot become a qualified
model even if it predicts every supported row.

## Route logic

Route precedence is frozen as follows:

1. Any source-hash, compact, Q1 aggregate-reproduction, causal-input, or
   explicit-ID failure stops as
   `ONE_MS_ID2R0_INPUT_OR_REPRODUCTION_FAIL_STOP`.
2. A singleton exact action-schedule stratum with all four Q1 ridge peak
   directions wrong and no exact critical replay routes to
   `ONE_MS_ID2R0_CRITICAL_SINGLETON_F03_EXACT_REPLAY_REQUIRED`.
3. Otherwise, if at least 75% of held probes have exact-stratum support and
   the single fixed local diagnostic has positive direction for every
   supported probe, response NRMSE at most `0.75`, and maximum family ranking
   regret at most `0.25`, remaining unsupported strata route to
   `ONE_MS_ID2R0_TARGETED_MATCHED_BRIDGE_REQUIRED`.
4. If supported histories still reverse or jump, or the measured action
   grammar lacks useful time-resolved directional progress, the same
   surrogate/data ladder stops as
   `ONE_MS_ID2R0_CANONICAL_PREFIX_SEQUENCE_AUTHORITY_SHOOTING_REQUIRED`.
5. Only complete local support plus stable response and useful sequence
   geometry may route to
   `ONE_MS_ID2R0_SUPPORT_GATED_LOCAL_MODEL_DESIGN_ONLY`.
6. If no rule is uniquely satisfied, the route is
   `ONE_MS_ID2R0_INCONCLUSIVE_FRESH_DISCRIMINATOR_REQUIRED`.

The angle/positive-span calculation is descriptive control-utility evidence.
Combining response samples from different times does not prove that they can
be superposed or safely sequenced. Action authority and controller-grade
recovery remain independent gates.

## What each route authorizes

The expected critical-singleton route authorizes only a separately frozen,
minimal fresh replay of the exact `f03` baseline and four exact `f03` probe
trajectories. Those replays test repeatability and retain zero fit weight.
They do not reopen Q1, create a transition tube, or authorize a controller.

If the exact `f03` behavior repeats, short finite canonical-source sequence
shooting should move ahead of another global model comparison. C1a already
qualified finite offline full-prefix replay mechanics; its roughly 56.5 s
worst branch makes it an offline search/teacher, not a 1 ms wall-clock
Oracle. The next authority stage must test time-resolved `+/-R`, `+/-Z`,
braking, return, Ip/current headroom, and hard envelopes. It may search the
real rank-three Card15 action subspace or other prospectively admitted
low-dimensional primitives; it may not assume p04/p07 peak ranking is
two-axis controllability.

Only after both supported local prediction and useful finite sequence
authority exist may the route train a support-gated local/LPV or hybrid
successor, calibrate uncertainty on fresh whole-history families, and begin
recovery-backed constrained control.

## Final goal retained

The final goal remains safe approximate two-axis relative/path/waypoint
tracking from fixed 1100 ms with a 1 ms action boundary and per-coil
`|delta I| <= 0.3 A`, using exact same-step paired-boundary R_geo/Z_geo and
Ip plus the complete causal takeover history. Later qualification must cover
connected positions, hold/recovery, and repeated bidirectional R_mid
crossing without resetting belief. ID-2R0 is only a route discriminator
toward that goal.
