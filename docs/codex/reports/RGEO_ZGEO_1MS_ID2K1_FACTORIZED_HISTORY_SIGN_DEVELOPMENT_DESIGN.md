# R_geo/Z_geo 1 ms ID-2K1 factorized history/sign development design

Date: 2026-08-17 Asia/Shanghai

## Purpose

ID-2J0 showed that exact one-ms truth recentering reduces nominal/free-rollout
error but does not repair three wrong-way minus responses. It also found six
of eight probe prefixes outside the old development support. ID-2K1 therefore
collects prospective fit-eligible development data over a complete
`history x direction x sign` matrix. It is not a controller, tube, authority
or safety qualification.

## Frozen experiment identity

- fixed authentic 1100 ms source and 1 ms issue/effect semantics;
- exact p03-minus stride-1 active nominal through issue 15 and held thereafter;
- horizon 34 issues / 35 retained states;
- eight complete conditioner histories copied from the consumed ID-2I1
  design, but all responses are newly generated under this development-only
  identity;
- within every history: one matched baseline plus p04-plus, p04-minus,
  p07-plus and p07-minus probes;
- every probe is issued at step 25 for exactly three issues, then returns
  exactly to the held nominal;
- one rollout for each of the 40 unique cells;
- one extra integrity replay for each previously wrong-way cell:
  `h00/p07-minus`, `h02/p04-minus`, and `h06/p07-minus`;
- maximum 43 resets, 1,462 plant-advance attempts and 1,505 retained states;
- no retry after any attempted advance and no cleanup plant action.

The probe action is the exact translated 14-dimensional Card15 target. Sign
is a label for the predeclared target; it is not assumed to imply odd plant
response. The campaign does not require central symmetry or additive
superposition.

## Gates

Before TSC, the full 43-stream schedule, exact Card15 fields, adjacent
per-coil slew `<=0.3 A`, absolute current limits, identity hashes and storage
budget must pass. The output directory must not exist.

During every rollout, current same-step paired-boundary R_geo/Z_geo and
same-step Ip are exact/noiseless pre-issue observations. Invalid or unpaired
boundary data, current/interface mismatch, solver/runtime failure, inner
clearance failure or outer-envelope breach stops before the next issue.
Future state and future actual current remain unknown before issue.

The completed data gate requires:

1. all 43 streams and all 1,462 advances complete;
2. independent raw reparse of all 7,525 required state artifacts;
3. in every history, baseline and all four probes have identical physical and
   semantic causal prefixes through the pre-probe state/action boundary;
4. the three critical replay pairs are exact in checked R_geo/Z_geo/Ip,
   14-coil, 48-wire, action and semantic-artifact fields;
5. all 32 unique probes have finite paired responses and peak R/Z norm at
   least `0.02 mm` over states 26--34;
6. every probe's maximum paired absolute Ip response is at most `100 A`;
7. the complete eight-history/four-probe factor matrix is present.

R/Z rank, condition, sign asymmetry, peak time and tail are reported per
history but are descriptive, not fit-eligibility gates. A rank failure may be
an authority limitation while the trajectory remains valid model data.

## Data role and split rules

If and only if all gates pass, the 40 unique cells become development-fit
eligible. The three extra replays are integrity replicates and carry no extra
fit weight. All cells from one conditioner history are a single split family;
steps and sibling cells may not be scattered across folds.

ID-2I1 and ID-2J0 remain consumed diagnosis-only and forbidden for fitting,
calibration or uncertainty shrinking. ID-2C2 remains evaluator-only. ID-2K1
does not open old holdouts. A fresh calibration and a new untouched
whole-history holdout must be generated after a model artifact is frozen.

## Successor model contract

A complete data PASS authorizes only a separately frozen structured model
comparison:

`exact actuator/queue + explicit time-indexed nominal continuation + stable
low-order latent action memory + optional small context-gated residual`.

Current R_geo/Z_geo/Ip truth is injected at every one-ms decision boundary.
The comparison must report teacher-forced one-step, 2/4 ms recentered,
stable/direct multi-step and paired-response metrics. A neural residual is
kept only if it adds fresh whole-family value over the structured backbone.

Authority, recovery, NMPC, transport, R_mid crossing, online adaptation and
RL remain blocked regardless of this campaign's result.
