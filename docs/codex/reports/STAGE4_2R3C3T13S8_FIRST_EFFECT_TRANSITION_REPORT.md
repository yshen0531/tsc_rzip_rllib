# Stage4.2R3c3T13S8 first-effect transition report

## Final route

T13S8 completed its frozen zero-new-TSC audit and ends as:

```text
FIRST_EFFECT_CAUSAL_TRANSITION_INSUFFICIENT_REDESIGN
```

Removing the adjacent cancellation transition improved finite input support
from T13S7R1's 0/112 selected rows to 64/112 rows, but did not satisfy the
unchanged support, containment, or relative-error gates. This is a genuine
transition-model/input-geometry design failure on consumed q1/q2 data. It is
not a runtime, restart, raw-corruption, controller, MPC, or global plant
result.

## Exact evidence

```text
preregistered design checkpoint
  1c5c05e  Finalize T13S7R1 and preregister T13S8
implementation checkpoint
  77b3c59  Implement T13S8 first-effect transition audit
staging
  /home/yangshen0711/tsc_software/stage4_2r3c3t13s8_77b3c59
server audit
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s8_audits/
  stage4_2r3c3t13s8_first_effect_20260802_77b3c59/
  stage4_2r3c3t13s8_first_effect_transition_audit.json
audit SHA-256
  c842fe8632bff9bbcd49d44d5a7ee9a8bf89b817c79b33177952ff677bd2ba3b
log SHA-256
  566a54347d5bfb759cad39569e1540486c854b5a8521b6757c4559b3f2ce6b88
```

Local full tests passed 706/706 and server focused tests passed 18/18. The
compact audit/log are local; all raw remain on the server. No TSC, `gotsc`,
Ray, controller, snapshot, or plant step ran for T13S8.

## Recomputed gates

```text
S1/S5 raw                                      52 / 52, 68 / 68
campaign-specific first-effect timing                  56 / 56
trace identity                                        120 / 120
single-transition extraction                          112 / 112
pre-effect causality                                  112 / 112
local rank                                              16 / 16
local tube                                              16 / 16
maximum tube/cap ratio                                0.132228
held-out support                                       64 / 112
componentwise union containment                        29 / 112
scaled relative error <= 0.10                          39 / 112
maximum finite scaled relative error                   1.530032
disjoint causal aliases                                       0
forbidden inputs                                              0
```

All 48 S1 rows were unsupported, including within-campaign peers. All 64 S5
rows had at least one supported S5 hypothesis. S5 breakdown was:

```text
easy transport     support 16/16, containment 8/16, relative 16/16
easy braking       support 16/16, containment 8/16, relative  7/16
hard transport     support 16/16, containment 8/16, relative  4/16
hard braking       support 16/16, containment 5/16, relative 12/16
```

Thus adjacent cancellation geometry was one real confounder, but the S1
pre-queue excitation remains incompatible even at the first effect. Within
uniform S5 post-queue semantics, cross-history response transfer also fails
the frozen tube/error gates. No unsupported row is counted as inaccurate;
the response statistics above apply only where support exists.

## Classification and action

```text
runtime/deployment error                              no
raw/snapshot/restart/causality error                  no
statistics/reporting error                           no
two-transition cancellation confounding              partly removed
pre-queue versus post-queue excitation incompatibility yes
supported S5 cross-history model failure              yes
real MPC or control conclusion                        none
```

The next stage is a new authentic q1 campaign under exactly the S5-style
post-queue Card15 excitation contract. It is identification only. Its raw
will be combined with the immutable q2 S5 raw in a separately frozen
leave-one-context-out audit before any q3 holdout or controller. Formal
timing and every RL prohibition remain unchanged.
