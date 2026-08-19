# ID-2Z8 bounded small sequence-model result

Date: 2026-08-19 Asia/Shanghai  
Implementation revision: `584bc28db2a000325a51d5484f63e621034a422f`  
Server output: `rgeo_zgeo_1ms_id2z8_runs/20260819_584bc28d_v1`

## Result identity

ID-2Z8 read exactly the 15 prospectively fit-weighted ID-2Z6/ID-2Z7
windows: five siblings at each of decision states 49, 53 and 57. Siblings
remained in one whole-context fold. It compared exactly two candidates:

1. a 48-parameter stable B/F fixed-pole response model with one fold-local
   causal context coordinate; and
2. the same backbone plus an ensemble of three hidden-size-four GRU
   residuals (351 parameters per seed).

Server validation passed focused `8/8` and all one-ms `456/456` tests. The
accepted comparison ran zero TSC, zero plant advances, zero controller or
optimizer calls, and read zero calibration or holdout records. Its same-code
deterministic replay audit passed with no differences. This is not an
independent model implementation audit.

Final route:

```text
ONE_MS_ID2Z8_SMALL_MODEL_FAIL_TARGETED_DATA_OR_BASIS_REVIEW
```

No winner or full-data model artifact was emitted.

## Frozen metrics

| candidate | max response NRMSE | max R p95 | max Z p95 | max Ip p95 | min peak cosine | max score regret |
|---|---:|---:|---:|---:|---:|---:|
| stable local memory | 0.22445 | 0.46088 mm | 0.26591 mm | 28.77 A | 0.98997 | 0.19423 |
| backbone + GRU4 | 0.21960 | 0.50298 mm | 0.21300 mm | 14.52 A | 0.98242 | 0.19423 |

Both candidates passed every fold's response-NRMSE, Z, Ip and direction
gate. Both failed the 0.30-mm R gate, and both selected `b4` in every held
context. The measured best arms were instead `f4`, `b2f2`, and `f2b2` at
states 49, 53 and 57. State-49 regret was `0.19423`, above the frozen `0.10`
cap. The stable candidate's three R p95 values were `0.46088`, `0.43847`, and
`0.31881` mm; the GRU values were `0.49284`, `0.37642`, and `0.50298` mm.

A zero-fit post-result attribution found that each arm's largest R error is
concentrated around the macro-to-hold transition: state 54 for the state-49
fold, state 59/60 for state 53, and state 63 for state 57. This supports an
event/finite-support diagnosis but is not a new fitted candidate and does
not alter the frozen FAIL. The GRU did not change any selected arm and made
the worst R p95 larger. With only two independent training contexts per
fold, increasing recurrent capacity is not justified.

The true best-versus-second-best terminal-score gaps were `0.16508`,
`0.00545`, and `0.03733`. Thus state 53 is nearly action-equivalent, while
state 49 contains a material ranking decision that neither model learned.

Primary and deterministic-audit SHA-256:

```text
8c7056826077b3dfd6d3aef447caf5b538d0fd28a2d7571eafa8b98da13ed11c
5265a78921d71806976f024600232fdf911ca66fbd6086c5cb81f8a90652fb9e
```

## Decision and next bounded route

ID-2Z8 does not authorize fresh calibration, blind holdout, Recourse-L1,
controller execution, or a larger network. It also does not show that B/F/H
has no useful authority: the exact branch teacher improved its score in all
three prior decisions, and measured response directions remain predictable.
The unresolved question is whether the grammar continues to provide useful
terminal progress beyond state 57 and whether two additional causal contexts
are enough to remove the obvious support/ranking failure.

The next proposed identity is therefore one bounded late-root branch/data
stage, not another hand-tuned open-loop ladder. It should continue the exact
selected ID-2Z7 prefix, evaluate the unchanged five-arm alphabet at states 61
and 65 through one common terminal state, retain every sibling as
prospectively declared development data, and include one zero-weight replay.
It must keep the existing simulator-development and hard envelopes and exact
Card15/current/prefix gates. If the measured teacher cannot produce a
preregistered material score improvement, this B/F/H grammar closes and the
route returns to action-basis/authority redesign. If it passes, the same two
model classes may be compared once with five whole-context folds; no capacity
ladder is authorized.

The final project goal remains safe causal one-ms two-axis waypoint/path
control from the fixed 1100-ms takeover, eventually including bidirectional
repeated R_mid crossing with continuous belief. ID-2Z8 is only a finite
source-local development-model failure.
