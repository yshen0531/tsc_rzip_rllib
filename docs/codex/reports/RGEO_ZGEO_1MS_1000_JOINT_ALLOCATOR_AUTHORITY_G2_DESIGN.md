# Fixed-1000 joint allocator Authority G2 design

## 1. Question and boundary

G2 asks one finite question: can a causal, readback-reserved two-coordinate
Card15 allocator combine the measured early radial even-minus role, the late
even-plus braking role, and signed vertical odd authority while improving the
absolute fixed-1000 trajectory relative to a fresh matched q0 continuation?

G2 is not an in-place G1 repair. It does not change G1's `+2` scalar rate to a
neighboring value, and it does not resume the consumed G1 identity. It changes
the action object from one precomputed scalar schedule to a two-dimensional
integer lattice selected from current exact observations and causal policy
state. No G2 row is model, calibration, holdout, controller, expert, Recourse
or recovery data.

## 2. Exact action lattice

Let `q0` be the exact source active Card15 command in TSC order. Define:

```text
even = [1,1,1,1,1,1,1,1,1,1,1,1,1,1]
odd  = [1,1,1,-1,-1,-1,1,-1,1,-1,1,-1,1,-1]

T(r,z) = exact Card15 quantization of
         q0 + 0.14*r*even + 0.07*z*odd  [single-turn A]
```

The frozen lattice is `r in [-4,32]`, `z in [-4,4]`. Every admitted
transition changes each coordinate by at most one. All reachable cells and
transitions must be enumerated offline. Every exact issued transition must be
`<=0.25 A`, leaving at least `0.05 A` nominal design reserve below the
unchanged observed-current hard limit of `0.3 A`. The reserve is an engineering
allocation rule, not a plant theorem. Runtime observed current remains
fail-closed at `0.3 A`; no clipping, target substitution or retry is allowed.

Every cumulative target must be inside the absolute current limits. The final
active target must be exactly `T(32,0)`. A Card15 target return is only command
closure, never plant recovery.

## 3. Causal radial policy

The allocator starts at `(r,z)=(0,0)` and uses the same radial policy in every
non-q0 rollout:

1. issues 0--3 move `r` by `-1` to `r=-4`;
2. beginning at issue4, read the exact current R/Z/Ip and accumulated history;
3. enter the brake phase when inward source displacement is at least `1.0 mm`;
4. if that condition is not met, issue `T(-4,z)` and re-evaluate each cycle;
5. issue8 is the frozen latest switch: it enters brake regardless, preventing
   an outcome-dependent unbounded hold;
6. in brake phase increment `r` by `+1` each issue until `r=32`, then hold.

The source and current state are known before each action. The successor is
not known. The policy has no future TSC access and no tunable post-result
threshold, depth or rate.

## 4. Vertical decisions and paths

`radial_only` keeps `z=0`. Two mirror paths make decisions at issues 8 and 28:

```text
path_pos_neg: target Z-source = +0.45 mm, then -0.45 mm
path_neg_pos: target Z-source = -0.45 mm, then +0.45 mm
```

At each decision, the current exact Z selects the sign that reduces the
remaining waypoint error. The selected odd macro has 12 issues:

```text
levels = sign * [1,2,3,4,4,4,4,4,3,2,1,0]
```

The waypoint is evaluated at h8, states 16 and 36. The two macros do not
overlap. They share each cycle with the radial coordinate through `T(r,z)`;
they do not pause radial transport or replace the whole command by a probe.

## 5. Matrix and budget

```text
matched_q0                 development reference, zero fit
radial_only                Authority qualification, zero fit
path_pos_neg               Authority qualification, zero fit
path_neg_pos               Authority qualification, zero fit
path_pos_neg_replay        integrity only, zero fit
```

The immutable maximum is five resets, 320 advance attempts, 320 `gotsc`
calls and 320 verified plant advances. Any attempted advance consumes its
slot and may not retry. A failure stops the campaign before the next rollout.

## 6. Scientific gates

All raw/interface gates and the exact replay must pass first. Against fresh
matched q0 over terminal states 56--64, each of `radial_only`,
`path_pos_neg`, and `path_neg_pos` must independently:

1. improve worst source R/Z distance by at least `15%`;
2. improve maximum one-ms R/Z speed by at least `0.03 m/s`;
3. keep absolute Ip-source fraction at or below `5%`.

At each vertical decision, the h8 endpoint must be within `0.25 mm` of the
commanded Z-source waypoint and must reduce Z error by at least `0.20 mm`
relative to the exact predecision state. The mirror paths must have the
expected signed ordering and at least `0.50 mm` Z separation at both common
endpoint states. A one-frame event cannot replace endpoint acquisition.

The final target must be `T(32,0)` in all non-q0 primary and replay rows. A
PASS is finite absolute two-axis Authority development only. It authorizes a
separate endpoint-value/risk model design and Recourse-L1 design in parallel;
it does not authorize feedback.

## 7. Failure and stop rules

- Offline Card15/current/lattice/identity failure: zero TSC.
- Any runtime current, observed slew, paired-boundary, clock, solver, Ip or
  hard-envelope failure: stop before the next issue and classify separately;
  do not emit a scientific result.
- Matched q0 incomplete: stop inconclusive before further rollouts.
- Replay mismatch: preserve raw and stop.
- Scientific FAIL: close this exact joint cell, radial policy and waypoint
  matrix. Do not scan adjacent `0.14/0.07`, 1.0-mm switch, issue, depth or
  waypoint values. Redirect to action-basis/nominal co-design.
- Scientific PASS: preserve the artifact and open only the two downstream
  designs named above. A real controller still requires model fresh
  calibration/blind PASS AND Authority PASS AND Recourse PASS AND hard
  interface PASS.

## 8. Final goal

The final goal remains safe causal instruction/path tracking from fixed
1000 ms with true noiseless R_geo/Z_geo/Ip observed before every one-ms issue,
continuous causal history/belief, absolute hold, recovery, and repeated
bidirectional R_mid crossing. G2 is one finite source-local Authority gate,
not completion of that goal.
