# R_geo/Z_geo 1 ms ID-2Z13 early p04-augmented capture design

Date: 2026-08-20 Asia/Shanghai

## Decision identity

ID-2Z12 cleanly closed the exact signed B/F convex-allocation family at the
selected state-61 causal history. ID-2Z13 is the one bounded successor allowed
by that result: move the decision root back to state 49 and add the actual
p04 Card15 direction to the already measured B/F grammar. It is not a denser
B/F grid and it does not relax the capture or hard-interface gates.

The campaign is a TSC-only finite branch teacher. It fits or updates no model.
It contains nine fixed arms at state 49, the same nine arms after committing
the selected first four issues to state 53, and one fresh replay of the final
selected path. The maximum is 19 resets, 1,463 advances and 7,410 required
artifacts.

## Why p04 is the single new direction

The actual one-issue 14-coil increments reconstructed from ID-2Z1 for
p07-minus (`B`), p03-forward (`F`) and p04-minus have numerical rank three
and condition `1.2840447`; pairwise action cosines are about `-0.13375`,
`0.10263` and `0.17568`. Thus p04 is genuinely outside the B/F actuator
span and is not a renamed convex allocation.

ID-2Z1 also supplies a finite four-issue p04 observation. Relative to its
matched held continuation, p04-minus reaches about
`(+0.396766,+0.007866) mm` at the fourth effect and
`(+0.619301,-0.026013) mm` after the four-state tail; p04-plus reaches about
`(-0.401584,+0.001774) mm` and `(-0.594509,+0.056715) mm`. These responses
are measurable but largely R-directed and remain compatible with the B/F
output cone at that late history. They therefore nominate p04 for a real
earlier-history discriminator; they do not predict capture or justify a
point model.

p09 and other directions are not added. Their available persistent evidence
uses different half-centred or one-effect semantics and would turn this one
discriminator into an unbounded action-basis screen. If p04 augmentation
fails, a later route review must select a new basis under a new identity.

## Frozen action grammar

All streams reproduce the authenticated canonical source prefix through
state 49. Tokens are exact Card15 target translations:

```text
H  hold the current exact target
B  one p07-minus increment
F  one p03-forward increment
U  one p03-unwind increment
P  one p07-plus increment
C  one p04-minus increment
D  one p04-plus increment
```

The arm order is fixed:

```text
h8, b8, f8, u4h4, p4h4, b4f4, f4b4, c4h4, d4h4
```

At round 0 each complete branch is evaluated from state 49 through the common
state 77, but only the first four issues of the selected arm are committed.
At round 1 the same matrix is rebuilt from the exact selected state-53
history and evaluated through state 77. The final selected stream is replayed
from the canonical source in a fresh reset. There is no third round, added
arm, retry, cleanup action or post-result change.

## Selection and capture

For each round, capture has priority. Otherwise selection minimizes, in
order, the six-state terminal worst normalized score, maximum source R/Z
distance, maximum one-step R/Z speed, maximum source-relative Ip fraction,
then stable arm id. A non-hold arm must improve the matched hold score by at
least `0.02` unless it already captures.

Capture is unchanged and must hold at every state 72--77:

```text
source R/Z distance <= 25 mm
one-step R/Z speed  <= 0.1 m/s
|Ip-Ip_source|      <= 5% of |Ip_source|
```

Exact selected-path replay is also mandatory. Relative score improvement is
not capture.

## Safety and evidence boundaries

Every issue is prospectively checked before runner entry for exact Card15
serialization, `<=0.3 A` per-coil slew, absolute current, paired boundary,
Ip, prefix, clock and run-root isolation. The development shell is 35 mm R/Z
and 7.5% Ip inside the unchanged 50 mm/10% outer hard envelope. The empirical
2 mm/2 mm/150 A successor caps and post-action stop do not constitute a
pre-action plant tube.

Only the explicitly whitelisted empirical branch stop may allow the next
sibling reset. Any package, prefix, boundary, actuator, runtime, raw or audit
failure aborts the campaign and cannot be called a scientific failure.

All ID-2Z13 data have zero fit weight and are forbidden from calibration,
holdout, controller, expert, BC, DAgger, RL or fixture use. The campaign is
route and teacher evidence only.

## Frozen routes

- PASS: a non-hold selected path captures for all six terminal states and its
  fresh replay is exact. This authorizes only a separately frozen
  Nominal-H1/Recourse-L1 design.
- Scientific FAIL: all required branches and replay are valid, but the
  selected path does not capture. This closes this exact early p04-augmented
  nine-arm grammar. It does not prove global plant unreachability or failure
  of every 14-D basis. It forbids another p04 depth/grid/adjacent-root ladder
  and requires a new action-basis/reachability review.
- Any execution/interface/raw/prefix/replay failure stops at its own layer and
  authorizes no scientific inference.

## Final-goal boundary

The final goal remains fixed-1100-ms, exact-RZI, full takeover-era causal
history, exact-Card15 two-axis waypoint/path control with independent hard
safety and recovery, ultimately including bidirectional repeated R_mid
crossing without resetting belief. ID-2Z13 is only a finite source-local
capture discriminator.
