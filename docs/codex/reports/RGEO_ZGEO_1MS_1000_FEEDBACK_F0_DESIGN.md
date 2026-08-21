# Fixed-1000 F0 finite moving-reference feedback design

## Purpose and claim boundary

F0 is the first finite path-tracking sentinel after A0 Authority-L0. It tracks
three preregistered two-axis checkpoints relative to the authentic q0
trajectory, not absolute stationary R/Z. This distinction is mandatory: q0
drift is much larger than the currently qualified local radial action.

F0 may establish finite, deterministic, q0-relative macro-feedback tracking.
It is not absolute hold, capture, Recourse-L1, arbitrary path tracking,
disturbance robustness or R_mid crossing.

## Causal controller

The authentic source is fixed 1000 ms. At issues 24, 36 and 48 the controller
reads the exact/noiseless current R/Z/Ip and its complete causal history. It
subtracts the frozen time-indexed B0 q0 reference at the same state, evaluates
the four byte-fixed V0 h8 candidate centers, and selects the candidate that
minimizes Euclidean error to the next commanded q0-relative R/Z checkpoint.
Ties are lexicographic. No future TSC state or rejected branch is visible.

Each selected action is a complete twelve-issue D1 ramp/plateau/exact-q0-return
macro. Macros do not overlap. Once started, the return is mandatory; a failed
pre-action hard gate stops before the next issue. This is a finite hard
continuation rule, not state recovery.

## Frozen paths, matrix and budget

Endpoint states are 32, 44 and 56. Commands are millimetres relative to q0:

- path A: `[+0.28, 0.00]`, `[-0.12, -0.90]`, `[-0.30, -0.75]`;
- path B: `[-0.30, 0.00]`, `[+0.12, +0.90]`, `[+0.30, +0.75]`.

The four fresh 64-issue rollouts are matched q0, path A, path B and a path-A
integrity replay. Maximum budget is four resets / 256 attempts and no retry.

## Gates

- all four executions, exact Card15, issued/observed slew, current, paired
  boundary, Ip, limiter and 50-mm/10%-Ip hard envelope pass;
- fresh q0 is an exact checked replay of frozen B0 through state 64;
- at each of six path checkpoints the measured q0-relative R/Z error norm is
  at most 0.35 mm and each absolute axis error is at most 0.30 mm;
- every selected V0 h8 center has predicted progress toward the current
  checkpoint and absolute predicted Ip response at most 400 A;
- the path-A replay is exact; all terminal active targets are q0.

PASS opens a separately frozen local Recourse-L1 and longer/more frequent
feedback design. FAIL closes this three-checkpoint controller without refitting
or widening V0. All F0 rows are qualification-only zero-fit evidence.

