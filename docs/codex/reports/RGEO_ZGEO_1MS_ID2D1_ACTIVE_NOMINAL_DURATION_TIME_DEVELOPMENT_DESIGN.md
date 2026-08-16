# R_geo/Z_geo 1 ms ID-2D1 active-nominal duration/time development design

Date: 2026-08-17 Asia/Shanghai

Identity: `rgeo-zgeo-1ms-id2d1-active-nominal-duration-time-development-v1`

## Purpose

ID-2C2 independently reproduced the finite source-local active nominal and
six signed one-issue residual arms.  It did not identify a causal dynamics
model: an exact replay lookup could pass that experiment.  ID-2D1 therefore
creates the first fit-eligible development family around the frozen
`p03_minus_stride1` active nominal while deliberately excluding the exact
ID-2C2 issue-16/one-issue cells.

The experiment varies residual issue time and duration.  It is intended to
identify response memory and time dependence, not to claim position/history
factorization, controller safety, a transition tube or recovery.

## Frozen campaign

Every rollout starts from the canonical 1100 ms source.  Issues 0--15 exactly
replay the selected ID-2C1/ID-2C2 active-nominal prefix: q0 at issue 0 and one
exact Card15 p03-minus increment at each issue 1--15.  The resulting issue-15
nominal level is held through issue 31 except for the declared translated
residual target and its exact return.

The 24 fixed rollouts are:

1. two held-nominal baseline replays;
2. p04 and p07, each plus and minus, for five schedule cells:
   issue 16 for 2 or 4 issues, and issue 22 for 1, 2 or 4 issues;
3. exact-centred half-p09 plus and minus for one issue at issue 22 only.

Each rollout has 32 one-ms issues.  The fixed maximum is 24 resets, 768
advance attempts/`gotsc` calls, 768 verified advances and 792 retained states.
There is no retry, adaptive action, cleanup plant action or continuation after
state 32.

The exact issue-16/one-issue cells already present in ID-2C2 are absent from
ID-2D1.  They remain immutable evaluator-only records for the later structured
model and cannot be used for fitting, normalization or hyperparameter choice.
P09 remains a separate hybrid/event coordinate and is never pooled into the
smooth p04/p07 gain model.

## Execution and empirical safety contract

Before every issue the implementation must use current same-step paired-
boundary `R_geo/Z_geo` and same-step `Ip` as exact noiseless observations.  It
must validate exact Card15 serialization, actual issued/readback current,
absolute current and the per-turn adjacent slew `<=0.3 A`, and must refuse
before plant advance on invalid boundary or interface state.  Future
successors remain unknown before issue.

Every observed successor must remain inside the unchanged 50 mm/50 mm/10%
outer envelope and the empirical 2 mm/2 mm/100 A per-step stop cap before a
later issue is permitted.  Residual issues require the 25 mm/25 mm/5% inner
clearance.  These are TSC-only exploration stops, not pre-action tubes or
controller-grade safety evidence.

All 24 rollouts and 768 verified advances are required.  Both baseline
replays must match at every state in paired-boundary geometry, Ip, all 14 coil
currents, all 48 wire currents, issued actions and the four semantic
artifacts.  `sprsina` remains diagnostic rather than semantic byte identity.

## Fit-eligibility and scientific gates

ID-2D1 becomes development-fit eligible only if all execution, raw and
interface gates pass and:

- the two baseline trajectories are exact at the frozen tolerances;
- the three-coordinate virtual residual-action lag block through lag 16 has
  full rank 48, with its condition number reported;
- every p04/p07 schedule arm has at least 25 micrometres peak R/Z response to
  the matched held baseline and at most 150 A absolute Ip response;
- both p09 event arms have at least 25 micrometres peak R/Z response and at
  most 50 A absolute Ip response;
- every response and its complete available tail through state 32 is retained;
- all observed states and steps pass the empirical and hard envelopes.

Duration and issue-time response contrasts are descriptive outputs, not gates
that force nonlinearity or time dependence to exist.  A model may conclude
that a shared stable response is adequate.  Conversely, numerical input rank
does not establish plant controllability, observability, superposition or a
safe response tube.

## Prospective model contract after PASS

A later, separately committed zero-new-TSC model stage may use ID-2D1 only as
development data.  It must:

1. preserve exact actuator, queue/effect timing and the actual 14-dimensional
   issued Card15 action history;
2. represent the held active-nominal trajectory separately from residual
   dynamics;
3. compare an action-blind nominal baseline against the simplest stable
   low-order/fixed-pole causal p04/p07 response model;
4. treat p09 as a separately labelled hybrid/event residual;
5. evaluate recursive response and absolute-state prediction at rolling
   origins without future readback/current leakage;
6. keep ID-2C2 immutable and evaluator-only, in particular its unseen
   issue-16/one-issue cells;
7. refuse GRU/TCN escalation unless the structured candidate leaves a
   reproducible residual on whole-family evaluation.

ID-2D1 is not calibration or blind holdout.  Fresh calibration and whole-
context/history holdout remain later identities.  Siblings and complete
schedule families must remain grouped; step-random splitting is forbidden.

## Authorization boundary

A complete PASS authorizes only the separately frozen structured model stage
above.  A scientific FAIL stops for route review; gates may not be weakened
after raw are observed.  Interface, runtime, safety and raw-integrity failures
remain distinct failures of their own layer.

No outcome directly authorizes uncertainty contraction, controller/MPC,
recourse, transport, `R_mid` crossing, online adaptation, expert data or RL.
The final goal remains safe causal approximate two-axis relative/path/waypoint
tracking from fixed 1100 ms, with continuous history across HFS/LFS crossings
and Ip retained as a coupled observation and safety quantity.
