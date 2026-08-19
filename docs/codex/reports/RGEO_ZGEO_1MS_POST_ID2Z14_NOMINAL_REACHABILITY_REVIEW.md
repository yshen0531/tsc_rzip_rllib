# R_geo/Z_geo 1 ms post-ID-2Z14 nominal/reachability review

Date: 2026-08-20 (Asia/Shanghai)

## Scope and decision

This is a zero-new-TSC, zero-fit review of tracked ID-2C1, ID-2W2 and
ID-2Z1--Z14 compact evidence. It preserves every frozen result and closes
the measured source-local B/F/p04/p01/p09 pulse-macro family. The next route
is not another nearby-root macro or a larger predictor. It is one finite
takeover-to-tail nominal-allocation frontier that asks whether deliberately
reserving per-cycle slew produces a useful moving corridor for subsequent
fit-eligible residual identification.

## What the completed search established

ID-2Z14 completed `10/10` authentic runs and selected `f4b4`, but terminal
maxima remained `32.258942 mm / 0.490628 m/s / 1.51172% Ip`. The new p01 and
p09 arms did not improve hold. Earlier p04, signed B/F convex and repeated
B/F stages likewise produced finite local utility without six-state
capture. These clean failures justify closing that finite macro family.

A compact scan over all retained Z-stage trajectories still finds nonzero
but badly timed authority. The closest single observed state was ID-2Z12
`main__f4` state 68 at `26.828692 mm / 0.104928 m/s / 3.71090% Ip`, with
normalized capture score `1.073148`. The best six-state window was ID-2Z5
`b12_f12` states 71--76 at `25.696052 mm / 0.141704 m/s / 3.97673% Ip`,
score `1.417042`. Thus existing actions nearly align position and velocity,
but no measured schedule keeps both inside the capture set. This is evidence
of timing/nominal-allocation failure, not zero action authority.

## Why the nominal must change

ID-2C1's full `p03_minus_stride1` nominal reduced state-32 source distance
from q0's `29.314321 mm` to `19.292295 mm` and speed from `0.889071` to
`0.385555 m/s`. It therefore remains the strongest measured transport
direction. But its physical increment uses the full `0.3 A` per-coil issue
limit, leaving no general simultaneous residual allocation. Blind extension
also failed to hold and eventually hit an observed-slew interface stop.

Using the exact 14-current increments measured in the accepted evidence,
the columns F, B, p04, p01 and p09 have numerical rank five and condition
`3.045764`. If only one half of F is issued, the exact per-coil slew box can
also contain either `+/-0.5 B`, `+/-0.5 p04`, one full half-amplitude p01, or
one full half-amplitude p09 direction. At `0.75 F`, one quarter of a full
B/p04 direction or one half of p01/p09 remains. These are actuator-space
facts only; they do not predict plant response or capture.

## Frozen next discriminator

ID-2Z15 will start from the canonical 1100 ms source and compare six exact
nominals through issue 31, followed by an unchanged 16-issue hold:

1. q0;
2. `0.25 F` each issue;
3. `0.50 F` each issue;
4. `0.75 F` each issue;
5. `1.00 F` each issue;
6. an exact 50% duty-cycle `F,H,F,H,...` nominal.

The common horizon is state 48 and terminal states are 43--48. One fresh
replay of the selected branch is mandatory. This is a nominal frontier, not
a pulse-response campaign. P04/p01/p09/B are not issued in this identity;
their role is only to quantify the residual slew that the chosen nominal
would leave for a separately frozen fit-eligible campaign.

PASS has two distinct meanings and neither may be inflated:

- six-state capture plus exact replay may authorize only Recourse-L1 design;
- without capture, a fractional/duty nominal may authorize only a fresh
  residual-identification design if it has exact replay, retains nonzero
  prospective residual slew, improves normalized terminal score by at least
  `0.10` against both q0 and full-F endpoints, and stays inside the frozen
  `40 mm / 0.60 m/s / 5% Ip` development corridor for all six terminal
  states.

If neither route passes, constant-rate/duty p03 nominal allocation closes.
The project must then use an algorithmic sequence/reachability construction
or a new physical basis; it may not add another fraction after the result.

## Goal boundary

The final goal remains fixed-1100-ms, exact one-ms R_geo/Z_geo/Ip
observation, full takeover-era causal history, exact Card15 and independent
hard safety, followed by safe two-axis waypoint/path control and later
bidirectional repeated R_mid crossing. ID-2Z15 is only a finite nominal and
data-route discriminator. It is not a model, controller, recovery policy,
waypoint, path or global-reachability result.
