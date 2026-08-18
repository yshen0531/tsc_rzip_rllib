# ID-2P1 matched-factorial development design

## Why this stage exists

ID-2O0 completed with zero model fits and zero TSC/reset/plant advances. Its
independent recomputation passed. All six readiness gates failed: K1 has only
eight fit-eligible whole-history families; fit data cover probe duration 3
only; none of the eight N1 probe schedules has exact K1 schedule support;
nearest-prefix response is positive for 5/8 cells with NRMSE 1.06265; maximum
two-action ranking regret is 0.87654. The frozen route is therefore
`ONE_MS_ID2O0_MATCHED_FACTORIAL_DEVELOPMENT_DATA_REQUIRED`.

This is a data-support result, not a model, controller or plant failure.

## Prospective matrix

ID-2P1 adds eight independent history families. Each family has one matched
baseline and all four p04/p07 by plus/minus probe cells. Conditioner order,
sign, duration and issue time are crossed with probe issue times 24--26 and
probe durations 1, 2 and 3. Every rollout starts from the canonical 1100 ms
source, replays the already admitted p03 nominal prefix and ends at state 34,
so every probe has its full frozen 1--8 ms response/return window.

There are 40 unique cells plus two integrity-only replay trajectories: 42
resets, at most 1,428 advances and 1,470 retained states. Replays receive zero
fit weight. The action values are the same exact translated p04/p07 Card15
targets already used by K1/N1; only their prospective history/timing
composition is new.

## Safety and integrity

This is TSC-only empirical identification, not controller-grade safety
qualification. Before every non-nominal issue it requires current exact
paired-boundary R_geo/Z_geo and Ip, Card15/slew/absolute-current checks and the
frozen inner clearance. Every successor is checked against the 2 mm/2 mm/100 A
empirical step cap and 50 mm/50 mm/10% outer envelope. A failure stops before
the next issue; it does not turn the post-action cap into a pre-action tube.

The campaign may start only if the server has at least 118 GB free and the
95 GB estimate leaves at least 23 GB. No archive is used. Complete raw,
semantic artifacts, matched prefixes, both replays, signal and Ip gates must
pass before any record becomes fit-eligible.

## Authorization boundary

A PASS authorizes only a separately frozen, at-most-two-candidate shared-
latent model comparison using K1 plus ID-2P1. A FAIL stops at its classified
layer. Neither route authorizes calibration, blind holdout, a tube, authority,
recovery, controller, MPC, transport, crossing, adaptation, expert data or
RL. N1 calibration remains consumed redesign evidence and is not fit data.

Frozen config SHA-256:
`9572635bb62a9e81609289b53527d329bb5b09f08e46a2cbc886eafa3e93323f`.
