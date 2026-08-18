# Post-ID-2T1 nominal realignment route review

## Decision

The high-level new-round architecture remains valid, but the immediate
experimental centre must move from the held-after-issue-15 corridor back to
the best measured time-varying nominal continuation.  The next active stage
is ID-2U0, a bounded zero-new-TSC nominal-realignment, action-allocation and
hybrid-event preflight.  ID-2U0 may write analysis code and a prospective
campaign specification.  It may not fit a model, run TSC, weaken the
`0.3 A` per-coil per-issue slew limit, or turn S1/S2/T1 into fitting data.

This decision does not change the final goal: from the fixed 1100 ms source,
use exact current same-step paired-boundary `R_geo/Z_geo` and exact `Ip`, plus
the complete takeover-time causal observation/action history, to safely and
causally follow finite two-axis relative displacement, waypoint and path
commands.  Later qualification must include bidirectional and repeated
`R_mid` crossing without resetting belief.

## Evidence correction after ID-2T1

The former shorthand that p04+ was useful at issue 24 and changed sign at
issue 30 is too coarse.  The actual Card15 target and aligned 14-coil path
are the same.  In the f03 issue-24 trajectory the first two paired effects
were approximately

```text
h1 = (-0.048115, -0.001272) mm
h2 = (-0.099619, -0.004169) mm
```

and the four issue-30 ID-2T1 histories had mean effects of approximately

```text
h1 = (-0.047936, -0.001 mm)   # rounded descriptive value
h2 = (-0.092060, -0.005 mm)   # rounded descriptive value
```

The decisive contrast is the return-effect state.  The issue-24 f03 branch
had a one-frame state-27 response of approximately
`(+0.610886, -0.285409) mm`, whereas the four later continuations had a mean
state-33 response near `(-0.076265, -0.006952) mm`.  The h3 R difference was
about `0.6835--0.6913 mm` (mean `0.687151 mm`), while the h4 difference had
already fallen to about `0.0076 mm` in the aligned paired-response comparison.

Across the 32 ID-2P1 probe cells, all 16 response events larger than
`0.5 mm` were aligned to absolute state 27.  Fourteen were minus cells from
seven histories; the two f03 plus cells formed the other branch.  This is
finite evidence for a history/sign-dependent return-edge or hybrid event.
It is not evidence that a smooth p04 local gain simply reverses sign, and it
does not isolate absolute time, position, or passive-state memory.

## Nominal-lineage error

ID-2C1 Phase A selected `p03_minus_stride1`: exact p03-minus Card15 levels
increase at every issue from 1 through 31.  Its measured terminal source R/Z
norm was `19.292295 mm`, versus `29.314321 mm` for q0, a `34.188%`
improvement with maximum source-relative `|Ip|` departure `722.743 A`.

ID-2C1 Phase B intentionally changed the problem for local identification:
it replayed the selected prefix only through issue 15 and then held level 15.
ID-2K1, ID-2P1, ID-2S1, ID-2S2 and ID-2T1 inherited that held corridor.
That data remains valid for its frozen roles, but it is not centred on the
best measured moving nominal.  Continuing to optimise models or action arms
around it would solve an increasingly artificial local problem.

The residual action cannot simply be added to the full stride-one nominal.
The nominal p03 increment already uses the allowed `0.3 A` on at least one
coil.  Several direct p03-plus-p04 issue or return combinations require
roughly `0.583--0.600 A` on a coil and are illegal.  Legacy runner clipping
must not be used to hide this conflict.

## ID-2U0 contract

ID-2U0 shall:

1. authenticate the tracked ID-2C1, ID-2P1, ID-2S1/S2 and ID-2T1 compact
   evidence used for this decision;
2. reproduce the full stride-one and held-after-15 schedule lineage and the
   associated descriptive R/Z/Ip results;
3. align p04/p07 responses by absolute state, issue/effect, dwell and return
   age, explicitly recording the state-27 event map;
4. enumerate exact Card15 headroom for moving-nominal steps and reject every
   combination whose per-coil requested change exceeds `0.3 A` before any
   runner call;
5. compare legal action grammars such as pause-one-nominal-increment, issue a
   residual primitive, exact return to the contemporaneous moving nominal,
   and resume transport;
6. emit one prospective fresh-campaign specification with matched baselines,
   same-clock action alternatives, multiple nominal levels and multiple
   arrival/settle histories, complete onset/dwell/return/tail windows, and
   whole-history development/calibration/blind splits.

ID-2U0 is a design/readiness audit, not a scientific plant PASS.  A passing
preflight may authorize only the separately frozen fresh campaign.  S1/S2/T1
remain zero fitting weight.  No model, controller, recovery, MPC, waypoint,
transport, crossing, adaptation or RL claim follows from ID-2U0.

## Route after ID-2U0

The intended bounded sequence is:

```text
ID-2U0 moving-nominal/action-allocation preflight
  -> one fresh matched moving-nominal campaign
  -> one bounded structured-vs-small-recurrent model comparison
  -> fresh groupwise calibration and blind whole-history holdout
  -> source-local hold/deceleration/recourse and first small 2-D waypoint
  -> multi-position/path expansion and repeated R_mid crossing
```

Control utility must be judged by sustained/terminal progress, same-state
candidate ranking, Ip/current cost and constraint reserve.  A single-frame
peak is not authority.  Canonical-source TSC replay remains eligible as a
bounded offline/asynchronous verifier or teacher; it is not assumed to meet a
one-millisecond wall-clock deadline.  The one-millisecond contract here is
the simulated plant issue period unless a separate wall-clock requirement is
explicitly imposed.
