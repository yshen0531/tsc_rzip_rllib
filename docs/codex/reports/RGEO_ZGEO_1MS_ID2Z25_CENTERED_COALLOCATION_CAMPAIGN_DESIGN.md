# ID2Z25 centered co-allocation D0 campaign design

## Question and boundary

ID2Z25 asks one finite simulator-development question: after the exact
full-F prefix through issue 15, does the prospectively selected `0.50F`
transition center support safe, persistent, signed plant responses for the
three frozen residual axes at issues 24 and 32?

It is not an Authority-L0, capture, recovery, controller, calibration,
holdout, expert or deployment test. Input rank and exact command return are
only execution prerequisites. Negative or one-sided output geometry remains
valid development data if the signal gates pass; positive span and six-state
capture are reported only as diagnostics.

## Frozen matrix and data roles

Every rollout starts from the authentic canonical 1100 ms reset and executes
65 issues. Issues 0--15 reproduce the tracked full-F prefix exactly. The
matched center then applies the exact Decimal/Card15 `N=0.50F` target stream
through issue 47 and holds its attained target through issue 64.

The matrix has exactly 15 rollouts:

1. one matched centered baseline, prospective development weight one;
2. one fresh full-F diagnostic, fit weight zero;
3. two phases (`24`, `32`) x three residual axes (`p00_minus`, `p05_plus`,
   `p06_plus`) x two starting signs, prospective development weight one;
4. one exact replay of `issue24/p05_plus/plus_then_minus`, fit weight zero.

Each branch applies the frozen signed centered target for eight issues and
then the precomputed eight-slot exact Card15 bridge to the matched center
endpoint. All remaining issues follow that center. The action matrix,
ordering, phase, duration, endpoint, thresholds and roles are fixed before
the first plant advance. Complete 1--8 ms causal windows may be used only by
a later simulator-development identity; incomplete windows are censored, not
labels. All siblings stay in the same future split.

## Runtime and evidence gates

- exact same-step paired-boundary R_geo/Z_geo and same-step Ip are observed
  before every issue; post-takeover causal observation/action history is kept;
- `issue k -> state k+1`, no software queue, no silent clipping;
- every target is exact Card15, per-coil slew is at most `0.3 A`, and absolute
  current/headroom, limiter, paired boundary, Ip and the 50 mm/10% outer
  envelope fail closed;
- the development-only preissue corridor is 45 mm/9%, with post-successor
  empirical trips 2 mm/2 mm/150 A; these are not a plant theorem or recourse;
- baseline must finish before a branch; each branch prefix through its phase
  must match the newly observed centered baseline; the full-F diagnostic
  matches the tracked full-F reference;
- any rollout failure aborts the campaign, with no retry after an advance;
- complete success is 15 resets, 975 advances, 990 states and 4,950 required
  artifacts; free space must be at least 100 GB before launch and retain at
  least 35 GB after the 65 GB estimate;
- independent full-raw reparse and exact replay are mandatory.

## D0 scientific gate

For every one of the twelve branch rows, relative to the matched centered
baseline at the same state:

- R/Z response norm at `h=4` is at least `0.05 mm`;
- R/Z response norm at `h=8` is at least `0.10 mm`;
- the h4/h8 direction cosine is at least `0.5`;
- maximum absolute paired Ip response is at most `350 A`.

The replay must be exact over the checked R/Z/Ip/14-coil/48-wire/action and
semantic-artifact contract. Task-plane angular coverage and source-centered
six-state capture are diagnostics only.

## Routes and stopping

- offline, storage, package, prefix, execution, raw or replay failure is not a
  scientific response verdict and stops the identity;
- D0 signal FAIL closes this exact `0.50F`, two-phase, three-axis, 8+8 centered
  cell. No 0.4/0.6 share, adjacent phase or duration ladder is authorized;
- D0 PASS authorizes only a separately frozen bounded event/value shadow-model
  development and an Authority-L0 design in parallel;
- real feedback remains blocked until fresh model calibration/blind PASS,
  Authority-L0, Recourse-L1 and the exact hard interface all pass.

## Final goal reminder

The final goal remains safe causal tracking of finite two-axis relative
waypoints/paths from fixed 1100 ms takeover, with exact 1 ms R_geo/Z_geo/Ip
observation, Card15/current/slew/Ip hard constraints, persistent belief,
bounded fallback, and ultimately repeated bidirectional R_mid crossing. This
campaign is only a source-local simulator-development data gate.
