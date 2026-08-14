# R_geo/Z_geo 1 ms ID-0T1 longer-tail result

Date: 2026-08-14 Asia/Shanghai

Frozen identity: `rgeo-zgeo-1ms-id0t1-long-tail-v1`

Plant implementation revision: `18788cf46eb029821169ae252fa2429bb50e5759`

Reporting-only independent-audit hotfix revision:
`273427f97e9a3e96a12c9084491f416daba6274a`

## Result

The independently reproduced scientific route is:

```text
ONE_MS_ID0T1_STATE32_TAIL_INSUFFICIENT_ROUTE_REVIEW
```

This is a finite identification-design FAIL and the preregistered stop for the
automatic horizon route. It is not a runtime, deployment, Card15, current,
paired-boundary, Ip, limiter, raw, replay-prefix, controller, MPC, recovery or
plant-reachability failure.

```text
rollouts / reset calls                          8 / 8
advance attempts / gotsc / verified       256 / 256 / 256
raw states                                          264
required artifacts                               1,320
required artifact bytes                 15,547,731,936
raw inventory SHA-256      893c920b48c85156d27b8c97f8ab4301e92c5327060bbc99f086efb7b848a607
execution / raw inventory / ID-0 prefix       PASS / PASS / PASS
state32 frozen tail gate                                  FAIL
```

All eight new compact histories matched both applicable consumed ID-0 compact
references through state20 at the frozen tolerances. Independent server-side
reparse of all 264 raw states passed after the separately recorded reporting
hotfix and reproduced the exact primary metrics and route with zero failures.

## State32 metrics

All six arms passed terminal absolute R/Z `<=0.05 mm` and terminal absolute
Ip `<=10 A`. Five passed terminal/peak `<=0.20`; p03-plus did not:

```text
arm          terminal R/Z (mm)   terminal/peak   terminal |Ip| (A)
p03 plus          0.012781261       0.230886777          0.3370   FAIL
p03 minus         0.011402306       0.175607368          0.3552   PASS
p04 plus          0.008532305       0.175862149          0.4456   PASS
p04 minus         0.008857681       0.163136253          0.4352   PASS
p07 plus          0.006597007       0.145046891          0.2011   PASS
p07 minus         0.006275999       0.118642990          0.2087   PASS
```

The failed residual is small in absolute units, but the frozen relative gate
is not weakened after observation. Therefore ID-0T1 does not certify that a
finite 32 ms truncation has closed every signed tail and does not authorize
model fitting or ID-1 execution.

## Tail-shape forensic

A zero-new-TSC compact audit found that endpoint-only closure is also not a
good general memory criterion. Relative R/Z norms are not monotone. Most
notably, p04-minus rose from `0.1457` of peak at state20 to `0.8700` at
state24, then fell to `0.1631` at state32. P03-plus reached `0.2719` at
state27 before ending at `0.2309`; p07-plus reached `0.2896` at state27 before
ending at `0.1450`.

All these absolute excursions remain tiny (`<=0.04724 mm` after state20) and
inside every frozen interface/safety envelope. They nevertheless show that a
single terminal ratio can both reject a small persistent residual and miss a
larger delayed rebound. This is a model-memory/gate-design issue, not a reason
to relabel the current result or automatically extend to state40.

## Independent-audit reporting hotfix

The first independent audit parsed every raw state but failed its prefix
comparisons because it compared post-rewrite raw outgoing `inputa` hashes
with pre-issue compact `inputa` hashes and treated outgoing q0 as issue0's
previous command. Geometry, Ip, 14-coil and 48-wire maxima were all zero.

The reporting-only hotfix verifies raw outgoing `inputa` against the frozen
Card15 stream and reconstructs the unique pre-issue source command from the
fourteen frozen ID-0 references. It changes no plant action, raw, primary
result, threshold or scientific metric and runs zero TSC. The original failed
audit remains preserved; the hotfix writes a separate evidence file.

## Evidence identity and data role

Local compact directory:

```text
docs/codex/audits/rgeo_zgeo_1ms_id0t1_result_20260814_18788cf4/
```

Its twelve JSON files have aggregate SHA-256
`e4fea14c05a9b055b12853bf5d193de05afaefae6e5e9207ec85a2575f3cfcaf`.
Primary result SHA-256 is
`a5e64d304c9b6cc5716047aee2d81d873e650a364390c2cb2705b26f86bc0d0d`;
the preserved original independent FAIL is
`4343c64eb03ab8052b759c92e9c93083b72c62c80e67f915131afad4db006083`;
the independent hotfix PASS is
`457c0f6a14256c91f628c6da96ef6e92a59426dd85a6e1138789a799639c80fb`.

Raw remains on the server and was not downloaded. ID-0T1 is consumed design
evidence only. It is forbidden for model fitting/training, calibration,
holdout, fixtures, expert/Oracle/BC/DAgger/RL, controller safety or recourse.

## Route recommendation and stop

Do not run state40, train a larger recurrent model or enter ID-1 automatically.
The recommended next authorized work is first a zero-new-TSC route review that
replaces the single-endpoint memory claim with a prospective whole-terminal-
window criterion and explicitly chooses between:

1. a stable low-order persistent/oscillatory latent state that models the
   small non-closed tail without requiring literal finite-memory extinction;
2. a newly justified finite tail window only if downstream control sensitivity
   proves that truncation is necessary.

Only after that decision should a separate small-HFS position/time/history
factorization campaign be frozen. The final two-axis path/waypoint goal and
exact/noiseless current R_geo/Z_geo/Ip observation contract remain unchanged.
