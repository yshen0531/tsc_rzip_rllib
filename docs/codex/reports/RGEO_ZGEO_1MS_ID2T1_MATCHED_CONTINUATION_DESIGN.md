# ID-2T1 matched continuation control-utility discriminator design

## Question

ID-2S2 established exact finite replay for four different two-arm f03
histories. ID-2T1 asks one narrower control question: after each exact state-30
history, does the same exact p04+ pulse produce a measurable response that
moves the absolute R_geo/Z_geo error toward the fixed 1100 ms source?

This is a TSC-only empirical shooting discriminator. It is not a model fit,
controller, recovery policy, transition tube, or closed-loop test.

## Frozen campaign

- Four rollouts, one for each exact ID-2S2 sequence history.
- Each rollout replays states 0--30 and issued actions 0--29 exactly.
- Issue 30 and 31 use the same p04+ Card15 target already present at issue 24
  in the qualified action grammar.
- Issue 32 returns exactly to the original q0 continuation; issue 33 remains
  q0. State 34 is recorded and execution stops.
- The sole novel cells are the four history-conditioned p04+ continuations at
  issue 30. There is no retry, resume, extra action, or cleanup action.
- Maximum budget: four resets and 136 one-ms plant advances.

Before issue 30, the live state/action prefix must match the corresponding
ID-2S2 compact at R_geo/Z_geo/R_mid `1e-12 m`, Ip/coil/wire `1e-9 A`, exact
Card15/action fields, and semantic artifact hashes. An invalid paired boundary,
current/slew/Ip/limiter violation, prefix mismatch, insufficient 25 mm/5% inner
clearance, or prior runtime failure stops before the novel issue.

Every successor is checked against the unchanged 50 mm/10% outer envelope and
the empirical 2 mm/2 mm/100 A step trip. These post-action trips are not
pre-action plant bounds.

## Frozen measured gates

For each history, the paired reference is its own exact ID-2S2 q0 continuation
over states 31--34. The following must all hold:

- peak paired R/Z response norm is at least `0.05 mm`;
- peak projection onto the same-state source-error correction direction is at
  least `0.025 mm`;
- the best same-state reduction in absolute source R/Z distance is at least
  `0.025 mm`;
- maximum absolute paired Ip response is at most `100 A`.

The full time series, terminal response, absolute error, correction projection,
and cross-history spread are reported. No gate assumes additivity, odd symmetry,
or a common history-independent gain.

## Evidence and route boundary

All four ID-2T1 trajectories have zero fit, calibration, holdout, expert-data,
and RL weight. A PASS means only that one already known action has finite
absolute control utility after four exactly replayed histories and may support
a separately designed shooting/data decision. It does not establish 2-D
authority, hold, recovery, recursive feasibility, a controller, MPC, transport,
position dependence, R_mid crossing, or reachability.
