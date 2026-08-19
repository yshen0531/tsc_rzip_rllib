# ID-2Z14 early remaining-basis capture discriminator design

Date: 2026-08-20 (Asia/Shanghai)

## Question

From the exact canonical selected prefix at state33, can one of the last
prospectively measured p01/p09 constructions, or the retained B/F controls,
produce a six-state finite capture under unchanged hard interfaces?

## Frozen campaign

- decision state: `33`;
- common horizon: `65` issues / terminal state `65`;
- terminal capture states: `60..65` inclusive;
- arms, in order:

```text
h8       HHHHHHHH
b8       BBBBBBBB
f8       FFFFFFFF
b4f4     BBBBFFFF
f4b4     FFFFBBBB
i4h4     IIIIHHHH       p01 plus, four cumulative increments
j4h4     JJJJHHHH       p01 minus, four cumulative increments
k4r3     KHHHLHHH       p09 plus held four issues, exact return
l4r3     LHHHKHHH       p09 minus held four issues, exact return
```

`B` is one p07-minus increment, `F` one p03-minus/forward increment, `I/J`
one exact p01 signed half-vector increment, and `K/L` one exact-centred
half-p09 signed offset. In the p09 arms, the opposite token is the exact
return; it is not a second experimental pulse. No action is clipped.

The selected arm is replayed from the canonical source under a fresh reset.
Maximum budget is `10` resets, `650` plant advances, `660` states and `3300`
required artifacts. Every trajectory has fit weight zero.

## Gates

Execution and evidence gates are unchanged: paired boundary R_geo/Z_geo,
same-state Ip, issue `k -> state k+1`, exact Card15 serialization/readback,
`|delta I| <= 0.3 A`, absolute current limits, complete state33 prefix,
post-successor empirical trip, outer hard envelope, raw inventory and an
independent raw reparse. The state60--65 capture gate is:

```text
source R/Z distance <= 25 mm
one-step R/Z speed   <= 0.1 m/s
absolute Ip offset   <= 5% of source Ip
```

All six states must pass. Relative score improvement without capture is
scientific FAIL. Fresh replay must be exact.

## Routes and stop rule

- PASS: finite capture candidate only; next is Recourse-L1 design and a
  separately frozen continuation/replay qualification.
- scientific FAIL: close the measured p01/p09/B/F/p04 source-local macro
  family at this canonical nominal and enter a materially different
  nominal/authority or reachability-blocker review.
- interface, prefix, raw or audit FAIL: preserve raw and diagnose that layer;
  do not interpret it as plant science and do not retry changed semantics.

No second decision, extra arm, depth change, relaxed gate, model fit,
calibration, holdout, controller or waypoint is allowed in this identity.
