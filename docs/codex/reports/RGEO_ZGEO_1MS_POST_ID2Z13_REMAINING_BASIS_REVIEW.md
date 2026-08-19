# Post-ID-2Z13 remaining-basis and earlier-nominal review

Date: 2026-08-20 (Asia/Shanghai)

## Scope

This is a zero-new-TSC, zero-fit design review over tracked compact evidence
and frozen Card15 fields. It does not alter ID-2Z13 and does not qualify a
model, controller, tube, recovery policy or reachable set.

## What ID-2Z13 closed

ID-2Z13 executed the complete frozen state49/state53 nine-arm matrix. The
third full-amplitude p04 actuator direction was never selected; the selected
path remained `b8 -> b4f4` and ended at `29.665859 mm / 0.331634 m/s`.
Adding p04 depth, another adjacent state49 root or a third B/F/p04 round would
therefore repeat the closed grammar rather than introduce a new control
mechanism.

## Remaining measured directions

The only source-local directions with prospective exact-Card15 persistent
evidence that have not been tested in this capture grammar are the p01 and
exact-centred half-p09 pair from ID-1C. Using the actual 14-D signed Card15
half-differences:

| actuator rows | rank | condition |
| --- | ---: | ---: |
| B/F | 2 | 1.243316 |
| B/F/p01 | 3 | 2.292414 |
| B/F/p09 | 3 | 2.338636 |
| B/F/p01/p09 | 4 | 2.735112 |

P01 and p09 each have maximum component `0.07 A` per signed half-vector and
14-D norm `0.204389 A`. These are genuine new actuator-space rows, but rank
is not authority. ID-1C measured p01 as a small, nearly odd persistent
response. It measured p09 as a deterministic non-odd event: p09-minus moved
about `(+0.743,-0.410) mm` at one effect state and returned to ordinary scale
one millisecond later. P09 must therefore be represented as a scheduled
dwell/return event, not accumulated as a smooth gain.

## Earlier decision point

The exact selected canonical prefix at state33 is already present in the
ID-2Z13 replay. Relative to the 1100-ms source it has:

```text
R/Z displacement   (-12.946044, +14.770760) mm
distance             19.641166 mm
one-step speed         0.354401 m/s
absolute Ip offset     2.3712 %
```

It supplies `3.740740 mm` more source-distance runway than state49 while
remaining on the same exact causal prefix. This is an earlier nominal/capture
question, not another state49 perturbation.

## Decision

Run one last finite remaining-basis discriminator from exact state33. It has
one decision only, nine fixed arms and one fresh replay:

- hold, B8, F8, B4F4 and F4B4 as controls;
- four cumulative p01-plus or p01-minus increments followed by hold;
- one exact p09-plus or p09-minus offset held for four issues, exact return,
  then hold.

All branches share horizon state65 and terminal states60--65. The capture
gate remains `25 mm / 0.1 m/s / 5% Ip` for all six terminal states. P09's
transient cannot pass by a one-state excursion. All actions must pass the
exact Card15, `0.3 A` slew, absolute-current, prefix, raw and outer-envelope
gates before scientific interpretation.

PASS authorizes only fresh replay evidence followed by Recourse-L1 design.
Scientific FAIL closes p01/p09 together with the already closed B/F/p04
source-local macro family at this canonical nominal. It must not trigger a
p01/p09 depth ladder or a larger predictor. The successor would be a
materially different nominal/authority construction or an explicit
reachability blocker review, not another nearby macro screen.

