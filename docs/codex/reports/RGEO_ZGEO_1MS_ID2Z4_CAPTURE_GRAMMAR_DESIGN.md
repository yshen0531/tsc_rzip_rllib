# ID-2Z4 finite two-axis capture-grammar design

## 1. Purpose and boundary

ID-2Z4 is a bounded TSC-only sequence discriminator from the exact ID-2Z3
selected logical state-97 prefix. It asks whether continued p07-minus braking
and a time-shared p03-unwind action can arrest both R/Z velocity components
and leave a capturable held tail near the fixed 1100-ms source.

It fits no model and is not a controller, recovery policy, transition tube,
waypoint result, teacher, or expert-data campaign. A PASS nominates one exact
sequence for a separate fresh replay and recourse design only. A FAIL closes
this two-coordinate capture grammar; it must not start another depth ladder.

## 2. Evidence and causal prefix

The source is the exact logical prefix selected by ID-2Z3:

- p03 virtual level 76 through issue 76;
- five selected four-issue p07-minus macros through issue 96;
- state 97 is the first ID-2Z4 decision boundary;
- state-97 source distance is `24.5653169 mm`;
- state-97 one-step R/Z speed is `0.1903746 m/s`;
- state-97 source-relative Ip is `1354.6975 A`.

The implementation must regenerate every prefix action from the frozen
ID-2Z1/ID-2Z2/ID-2Z3 configs and compare exact action fields plus the tracked
state checkpoints at 0, 32, 64, 69, 73, 77, 81, 85, 89, 93 and 97. Current
same-step paired-boundary R_geo/Z_geo and same-step Ip are exact observable
truth before every issue. Future successors remain unknown before issue.

## 3. Exact candidate grammar

Every rollout has issues 0--120 and states 0--121. Issues 0--96 are the exact
common prefix. Issues 97--108 are the twelve-slot capture window. Issues
109--120 hold the final target and supply a common twelve-ms tail.

Within the capture window:

- `H` holds the current target;
- `B` applies one exact p07-minus increment;
- `U` applies one exact p03-unwind increment.

The eight frozen candidates are:

1. `hold12`: `HHHHHHHHHHHH`;
2. `p07m4`: `BBBBHHHHHHHH`;
3. `p07m8`: `BBBBBBBBHHHH`;
4. `p07m12`: `BBBBBBBBBBBB`;
5. `p07m8_p03u4`: `BBBBBBBBUUUU`;
6. `p07m4_p03u4_p07m4`: `BBBBUUUUBBBB`;
7. `p07m4_p03u2_p07m4_p03u2`: `BBBBUUBBBBUU`;
8. `p03u2_p07m10`: `UUBBBBBBBBBB`.

Only one coordinate changes in an issue. No combined step, projection,
software queue, silent clipping, or post-hoc rescaling is allowed. The exact
Card15 target, issued delta, structural/readback delta, absolute current and
headroom are checked before each TSC advance. Any statically inadmissible
candidate is excluded before reset and remains an explicit result row.

## 4. Execution and safety

- maximum resets: 8;
- maximum attempted/verified advances: 968;
- maximum retained states: 976;
- required semantic artifacts if all complete: 4,880;
- minimum free bytes before run: 120,000,000,000;
- maximum estimated raw bytes: 65,000,000,000;
- minimum estimated residual free bytes: 55,000,000,000;
- retry after any attempted advance: forbidden.

The existing one-ms paired-boundary, limiter, absolute-current, per-coil
`<=0.3 A`, Card15, structural/readback, Ip, inner/outer, and post-successor
empirical stop gates remain fail closed. A failed branch stops before its
next issue. No failed branch can be used to relax a later gate.

## 5. Measurements and frozen route

All candidates are compared with the same `hold12` path. Report:

- paired R/Z/Ip response at every state 98--121;
- R/Z velocity components and norm;
- source distance and its step change;
- minimum actual-current headroom;
- exact action count and capture-action changes;
- terminal states 116--121.

A capture candidate must be complete and, for all six terminal states:

- source R/Z radial distance `<=25 mm`;
- R/Z one-step speed `<=0.1 m/s`;
- absolute source-relative Ip `<=5%`;
- valid paired boundary and every hard interface gate.

At least one non-hold candidate must pass. Select lexicographically by the
terminal maximum speed, terminal maximum source distance, terminal maximum
absolute Ip offset, number of non-hold issues, then fixed candidate id.

Routes are separated as input/offline/storage, execution/interface, raw,
prefix, no capture candidate, and finite capture-candidate PASS. An execution
or raw failure is never interpreted as a scientific grammar failure. A PASS
authorizes only a separate exact replay and Recourse-L1 design; a FAIL ends
this grammar and routes to a broader bounded action allocation/search review.
