# ID-2Z2 two-decision rolling branch result

## Result identity

- Physical campaign source revision:
  `b7fcce9513e7284503b45bd1f3e730037cbc11ef`.
- Reporting/recovery revision:
  `0cd4a84f318ce66edfe0ab09cdbde23adf2eacb9`.
- Frozen config SHA-256:
  `7560895635e9dfa6e732459ca81dd0f15d96240904f0892b465c53dfcf7318c5`.
- Server output:
  `artifacts/server_runs/rgeo_zgeo_1ms_id2z2_20260819_b7fcce95`.
- Tracked compact evidence:
  `docs/codex/audits/rgeo_zgeo_1ms_id2z2_20260819_b7fcce95`.
- Final route:
  `ONE_MS_ID2Z2_TWO_DECISION_ROLLING_BRANCH_PASS_HOLD_CONTROLLER_DESIGN_ONLY`.

The result is a finite source-local two-decision sequence nomination. It is
not a hold, recovery policy, controller, arbitrary branch Oracle, waypoint,
position generalization, R_mid-crossing or reachability result.

## Execution and reporting integrity

All fourteen canonical-source branches completed:

- 14/14 resets and rollouts;
- 1,106/1,106 attempted, `gotsc`, and verified plant advances;
- 1,120 retained states;
- 5,600 required artifacts and 65,960,074,880 bytes;
- inventory SHA-256
  `fa93bf54b958b6032c7f6741529b6fe0f7b43fc73bd04eaef184096e631e0059`;
- 7/7 Round-A and 7/7 Round-B complete-prefix checks;
- minimum observed absolute-current headroom 95.2 A;
- zero model fit/update and zero calibration/holdout read.

The first launch exposed a reporting/runtime integration bug only after the
first `r0__hold` branch had completed all 77 physical advances and retained
all 78 raw states. The two-round stage omitted the scalar `horizon_steps`
field expected by the reused generic rollout finalizer. No compact or result
was written and the automatically invoked initial independent audit therefore
failed for missing primary evidence. This was not a TSC, actuator, safety or
scientific failure.

The repair did not change the config, candidate matrix, targets, gates or any
physical action. It supplied the frozen per-round horizon, parsed the complete
retained raw branch, revalidated all Card15, current, boundary, Ip, step-cap
and prefix quantities, wrote its compact with zero reset/plant replay, and
continued only the remaining thirteen branches. The final result records
`r0__hold` as recovered and records zero replayed plant rollouts. The initial
failed reporting audit remains tracked separately.

Before continuation, the installed server code passed 13/13 focused tests
and 408/408 complete one-ms tests. A zero-TSC in-memory reconstruction then
verified 77 actions, 78 states and the complete source prefix. The final
structurally separate raw audit subsequently passed with no failures and
reproduced the primary route, counters, inventory, metrics and selected
sequence exactly.

## Measured decisions

Both rounds nominated the same two arms:

| round | arm | peak paired R/Z | active-terminal improvement | terminal improvement | max paired Ip | eligible |
|---|---:|---:|---:|---:|---:|---:|
| A | p03-forward4 | 0.971732 mm | 0.499588 mm | 0.916999 mm | 146.994 A | yes |
| A | p07-minus4 | 0.680796 mm | 0.281031 mm | 0.496098 mm | 108.047 A | yes |
| B | p03-forward4 | 0.961030 mm | 0.501692 mm | 0.871520 mm | 144.760 A | yes |
| B | p07-minus4 | 0.655032 mm | 0.297203 mm | 0.496995 mm | 108.484 A | yes |

The exact lexicographic decision in each round was `p03forward4`; the selected
logical two-macro sequence is therefore:

```text
p03forward4 -> p03forward4
```

The rejected p04-minus branches did make geometry progress, but their maximum
paired Ip response was about 206 A and exceeded the unchanged 150 A gate.
The p03-unwind, p04-plus and p07-plus branches did not provide the required
persistent source-distance improvement.

## What the PASS does and does not establish

The result shows that a second measured branch decision repeats the first
decision rather than invalidating it: at both state69 and the selected state73
prefix, four p03-forward increments beat a matched hold and retain their
finite advantage through the four held effects. It also confirms p07-minus as
a lower-Ip alternate with smaller geometry benefit.

The path is still not a hold. The selected Round-B branch ends at a 24.349695
mm source R/Z distance with source offsets approximately -21.895570 mm R,
+10.653249 mm Z and +1,303.850 A Ip. Its final four R/Z step-speed norms
average about 0.3907 m/s and reach about 0.4129 m/s. Thus neither a terminal
set nor finite recovery/recourse has been reached.

The next design must therefore use this measured two-decision prefix to build
a bounded source-hold/braking rolling search. It must not treat another fixed
manual depth as a controller, and it must keep hold/recovery qualification,
fresh model data, uncertainty calibration and final waypoint control as
separate gates.
