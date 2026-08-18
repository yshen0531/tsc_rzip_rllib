# R_geo/Z_geo 1 ms post-ID-2U2 control-utility route review

Date: 2026-08-19

Decision identity: `post-id2u2-control-utility-route-review-v1`

## Final goal retained

The final objective remains a controller that takes over from the fixed
1100 ms source, observes the current same-step paired-boundary
`R_geo/Z_geo` and same-step `Ip` exactly before every 1 ms issue, retains
the complete post-takeover causal observation and controller-owned action
history, and respects exact Card15, queue/effect, absolute-current, per-coil
`|delta I| <= 0.3 A`, Ip, boundary, abort, hold, and recovery constraints.
Within a prospectively finite work domain it must approximately follow a
user-specified relative displacement, waypoint, or path. Later
qualification must include bidirectional and repeated `R_mid` crossings
without resetting belief. Returning toward the source is only a bootstrap
transport problem, not the final objective.

## Evidence and execution boundary

This review used only tracked ID-2U1 compact trajectories, the frozen
ID-2U2 config, primary result, independent audit, implementation, and the
already tracked U0/U1/U2 reports. The numerical recomputation was local and
read-only. It fit no model, opened no calibration or blind family, accessed
no server raw, and ran zero TSC calls, resets, or plant advances.

The pre-review recommendation to add four arrival-history families is not
erased, but it is no longer the automatic next experiment. It is demoted to
one conditional support-repair option after a bounded control-utility and
support-decomposition audit. No U1/U2 gate or verdict is changed.

## What remains valid

- NR0/NR1 paired-boundary signal, fail-closed observation, exact Card15,
  issue-to-effect, and one-ms slew contracts remain necessary.
- Current `R_geo/Z_geo/Ip` are exact observations at every decision; belief
  represents latent response memory and future/model uncertainty, not
  measurement noise in those observables.
- ID-2U0 correctly restored the continuing p03-minus stride-one nominal and
  exact `pause -> probe -> return -> resume` allocation rather than adding a
  residual to a p03 step that already consumes the full slew.
- ID-2U1 is a clean twenty-trajectory moving-nominal development PASS.
- ID-2U2 is a clean model/support-design FAIL. Calibration and blind roles
  remain unopened and no model artifact exists.

## Three distinct ID-2U2 failure layers

The effective independent response contexts are four whole-history
families, not twenty independent trajectories. Each leave-one-family-out
fold trains on three contexts, so the centered response-context feature
rank is necessarily at most two; the reported rank is exactly two.

Support failure is real but not universal. In the local/event candidate the
held-family support distance/threshold ratios are approximately:

```text
u00  6.212 / 11.786   supported
u02 968.176 / 11.197  unsupported
u04  8.560 / 13.094   supported
u06  5.786 / 12.154   supported
```

`u02` is also the wholly held `level 22 x issue 24` corner. Its extreme
distance is driven mainly by recent action-memory/current-history features,
not by evidence that an abstract `paced` label alone is causal.

Model-form and ranking failure remain after support passes. Local/event
held-family response NRMSE for `u00/u04/u06` is approximately
`0.946/1.025/1.142`, with ranking regret `0.947/0.996/1.000`. The small GRU
regresses mean/worst response NRMSE from `1.056/1.142` to `2.412/4.119`.
Increasing recurrent capacity on the same data is therefore not justified.

The `u00` minus branches form a separate regime candidate: their response
is ordinary for the first four horizons, jumps to about `0.71 mm` in one
later frame, and returns close to the ordinary tail in the next frame. It
must not be averaged into a globally smooth point response without a regime
guard, set-valued uncertainty, or fresh matched evidence.

## Control-utility diagnosis

The current p04/p07 exact-return grammar is a valid excitation grammar, but
it is not yet a qualified control grammar. Read-only recomputation gives:

```text
horizon    moving-baseline R/Z motion    largest residual R/Z effect
1 ms       0.301--0.811 mm               0.048--0.050 mm
2 ms       0.814--1.547 mm               0.098--0.106 mm
8 ms       4.276--5.238 mm               0.021--0.026 mm
state 40   not used as a common delta    0.011--0.019 mm
```

The `u00` approximately `0.71 mm` event is transient and has mostly vanished
by horizon eight. Across the four measured families and sixteen direction
queries, the measured best-versus-second-best macro-action utility gap is
only about `1.17--16.10 micrometres`, whereas held-family prediction errors
are hundreds of micrometres. A near-perfect ranking of these four pulses
would therefore still not establish useful drift cancellation, sustained
two-axis reserve, hold, recovery, or waypoint authority.

This does not prove that p03, p04, p07, the plant, or short sequences lack
authority. It proves only that the current two-issue exact-return pulse set
has not yet shown enough persistent, distinguishable control utility to
justify automatically spending another approximately 50 GB on the same
probe grammar.

## Route correction

The immediate successor is ID-2V0, a bounded zero-new-TSC, zero-fit
`control-utility + support-decomposition` audit. It is an implementation and
campaign-design preflight, not a new physical-science qualification result.
It must:

1. persist the feature-block decomposition of the `u02` support distance;
2. recompute absolute moving-baseline motion, paired response, sustained and
   terminal progress, direction coverage, action-equivalence margins,
   hybrid excursion, Ip/current reserve, and earliest safe replanning point;
3. distinguish measured excitation utility from controller-grade authority;
4. freeze one and only one next data/action route.

The route decision is:

- if the existing pulse grammar has prospectively useful sustained utility,
  freeze a minimal `2 x 2 x 2` development history extension, preserve
  `u01/u03/u05/u07` unopened, and require both held-history and
  leave-one-corner-out tests;
- otherwise, stop the same-pulse history expansion and freeze one small,
  exact-Card15, same-prefix multi-arm branch campaign over transport,
  pause/deceleration, signed residual dwell/return/resume, and a finite
  recovery continuation. Its objective must be absolute terminal/sustained
  R/Z progress, velocity/hold, Ip/current margin, and recoverability rather
  than a single response peak.

Existing evidence makes the second route more likely, but ID-2V0 must
record the exact evidence and candidate-budget contract before any new TSC.
Canonical-source prefix replay remains an offline branch/search mechanism;
it is not an already qualified arbitrary-state or one-ms wall-clock Oracle.

## Bounded milestone sequence and stop rules

The route is capped at:

```text
one V0 decision audit
-> one action-grammar or development campaign
-> one structured model plus fresh calibration/blind qualification
-> one source-local small two-axis waypoint, short hold, and recovery gate
```

Stop rules are explicit:

- if measured candidate sequences lack sustained two-axis utility relative
  to baseline motion, redesign action allocation/nominal and do not fit a
  larger network;
- if a fixed-budget branch campaign cannot find finite useful progress and
  a recovery continuation, record a finite action/horizon authority failure,
  not a machine-learning failure or global plant-unreachability claim;
- if one purpose-built fresh data campaign still leaves prediction/tube
  uncertainty larger than the real candidate utility gap, stop the
  surrogate-capacity ladder;
- calibration/blind undercoverage blocks control;
- missing hold or recovery blocks waypoint expansion and all `R_mid`
  crossing work.

Machine learning remains necessary to amortize expensive TSC search and to
map compressed causal history, exact current observation, time/event phase,
and candidate actions to finite-horizon response and uncertainty. The route
does not require complete physical causal identification before learning;
it requires only that the learned action set first have measurable control
value.

