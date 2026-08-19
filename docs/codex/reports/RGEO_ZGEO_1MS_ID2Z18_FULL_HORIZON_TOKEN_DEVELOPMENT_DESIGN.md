# ID-2Z18 full-horizon token development design

## Identity and purpose

ID-2Z18 is a one-time simulator-development campaign for a future bounded
model comparison. It does not search for a winning open-loop path and does
not use ID-2Z17 as training data. Its purpose is to generate complete causal
histories in which time-varying transport and signed residual actions coexist.

The exact source/full-F prefix is replayed through issue 15/state 16. Issues
16--47 contain 32 frozen tokens; issues 48--64 hold the last command. The
token alphabet is:

```text
F = exact p03-forward increment
A = exact p06-plus first-event increment
a = exact p06-minus first-event increment
E = exact p08-plus first-event increment
e = exact p08-minus first-event increment
H = exact hold
```

Every issue is an absolute Card15 target and every per-coil change must be
`<=0.3 A` before the runner is called. No clipping is allowed.

## Development matrix

Fourteen unique histories have fit weight one:

- two transport references: `F*32` and `(FFHH)*8`;
- six paired schedule families, each with a declared sign-inverted mate;
- all schedules have 32 tokens, exactly 16 F issues, and balanced temporal
  placement of p06/p08 residual issues.

Two additional trajectories are exact replays of the half-F reference and
the first positive paired schedule. They have fit weight zero and exist only
for execution/history reproducibility.

The four future calibration and four future blind-holdout schedules are also
declared in the machine config. They are not executed or read in ID-2Z18.
Their whole histories remain separate from development, and no sibling or
replay may cross a split.

## Data and signal gates

PASS requires:

1. all 16 rollouts complete with exact interface, source prefix, clocks,
   Card15 targets, readback/slew, current and raw inventory;
2. both critical replays exact over all checked physical observables and
   semantic artifacts;
3. 14 unique positive-weight full histories and zero weight for both replays;
4. exact token count/balance and rank-three F/A/E increment geometry;
5. every one of the six paired schedule families has at least `0.05 mm`
   maximum R/Z separation over states 17--65;
6. no calibration or holdout record read and no model fit.

PASS authorizes only the separately frozen, maximum-two-candidate development
model comparison. It is not a model, tube, authority, capture, recovery,
controller, MPC, waypoint/path or R_mid result.

Any interface, prefix, raw, replay or horizon failure is inconclusive and
preserves raw. A complete scientific signal/support FAIL closes this exact
token campaign and prevents model fitting. Gates are not changed after TSC.

## Budget and cleanup

The maximum is `16` resets, `1040` advance attempts/calls/verified advances,
`1056` retained states and `5280` required artifacts. The raw estimate is
`70 GB`; at least `40 GB` must remain after the estimate. There is no retry
after any advance attempt. Raw may be deleted only after independent full-raw
audit and local/remote compact hash recovery, and only the exact current
identity's `rollouts/` subtree may be removed.
