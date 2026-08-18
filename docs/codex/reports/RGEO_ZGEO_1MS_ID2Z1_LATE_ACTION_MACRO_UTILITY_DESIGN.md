# ID-2Z1 late-action macro utility design

## Purpose

ID-2Y1R1 closed the manual p04/p07 ramp-depth ladder: all four exact branches
stopped on negative-R clearance before their hold window. ID-2Z1 is a bounded
same-prefix branch discriminator for the next sequence optimizer. It asks
which, if any, short exact macro-action produces persistent absolute progress
after the common p03 level-64 prefix.

This is not another hold attempt and does not fit a plant model. It compares
all three currently supported virtual directions in both useful local signs,
plus the no-change baseline, before selecting any action grammar.

## Frozen prefix and seven branches

Every rollout starts from the canonical 1100 ms source. Issue 0 is q0 and
issues 1--64 are exact p03-minus stride-one levels 1--64. States0--65 and
actions0--64 must reproduce the independently audited ID-2W3R1 compact.

The horizon is 73 issues, retaining states0--73. The seven branches are:

1. hold p03 level64 for issues65--72;
2. continue p03 to levels65--68, then hold level68 for issues69--72;
3. unwind p03 to levels63--60, then hold level60;
4. add p04-minus levels1--4, then hold;
5. add p04-plus levels1--4, then hold;
6. add p07-minus levels1--4, then hold;
7. add p07-plus levels1--4, then hold.

Exactly one virtual coordinate changes at each issue. Every target is an
absolute exact Card15 command; every per-coil issue delta is at most 0.3 A,
equality is allowed, and the offline minimum absolute-current headroom must
remain at least 95 A. The enumerated v1 streams have at least 97.6 A. No
software queue, silent clipping, cleanup action, retry, adaptation, or future
measured current is permitted.

## Observation and empirical stops

Before issue k, same-step paired-boundary R_geo/Z_geo and same-step Ip are
exact/noiseless observations, together with the complete post-takeover causal
observation/action history. State k+1 remains unknown before issue k.

The simulator-development gates remain:

- before every novel issue, source-relative R/Z must be inside 25 mm per
  axis and Ip inside 5%;
- each successor must remain inside 50 mm per axis and 10% Ip;
- each successor step is capped at 2 mm R, 2 mm Z, and 150 A Ip;
- paired-boundary, Card15, current, readback slew, time, TSC, solver, raw, or
  prefix failure stops before any later issue;
- only the frozen R/Z/Ip preissue-clearance stop may allow the next reset.

These are finite empirical simulator stops, not controller-grade transition
tubes or recovery guarantees.

## Prospective utility gate

The hold branch is the matched absolute baseline. For each nonbaseline arm,
the paired response is candidate minus baseline at states66--73. The final
four states70--73 form the persistence window. An arm is nominated only if:

1. both the arm and baseline complete state73 with all hard/raw/prefix gates;
2. its maximum paired R/Z response norm is at least 0.05 mm;
3. its source-relative R/Z distance improvement over baseline is at least
   0.05 mm in at least three of states70--73;
4. its state73 source-distance improvement is at least 0.10 mm; and
5. its maximum paired absolute Ip response over states66--73 is at most
   150 A.

Eligible arms are ranked lexicographically by largest state73 R/Z-distance
improvement, largest median states70--73 improvement, smallest maximum
one-step R/Z motion over states70--73, smallest absolute state73 source-Ip
offset, then rollout id. At least one nominated arm is required for PASS.
All component responses, velocities, source offsets, current headroom, and
margin are reported even when no arm passes.

This gate excludes a single-frame hybrid spike and a merely measurable but
control-irrelevant action. It does not claim two-axis positive span, hold,
recourse, or a controller.

## Budget, data role, and routes

- seven independent canonical resets;
- at most 511 issue attempts, `gotsc` calls, and verified advances;
- at most 518 retained states and 2,590 required artifacts;
- at least 50 GB free before launch and 25 GB after a 31 GB estimate;
- raw remains uncompressed and receives a separate full-raw audit;
- zero model fitting/training and zero calibration/blind/holdout read;
- all outputs are route/action-utility evidence only and are forbidden from
  controller, expert, BC, DAgger, RL, fixture, calibration, or holdout use.

A clean PASS nominates one late macro for a separate bounded rolling sequence
optimizer. A clean FAIL stops late-state macro expansion and redirects the
optimizer to an earlier decision point or a broader exact action allocation.
It does not authorize another ramp-depth ladder or larger network. Any
execution/interface/raw/prefix failure stops and is diagnosed at its own
layer.
