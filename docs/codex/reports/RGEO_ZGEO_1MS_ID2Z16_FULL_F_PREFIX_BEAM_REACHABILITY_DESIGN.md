# R_geo/Z_geo 1 ms ID-2Z16 full-F-prefix beam reachability design

Date: 2026-08-20 (Asia/Shanghai)

## Identity and reason

`rgeo-zgeo-1ms-id2z16-full-f-prefix-beam-reachability-v1`

This design is frozen after the final ID-2Z15 constant-rate/duty failure and
before any ID-2Z16 implementation or response. ID-2Z15 showed that full-F is
the best measured takeover nominal, while every reserved-headroom fraction
lost terminal utility and no arm captured. Its full-F score was best near
state 35 and then worsened during hold. The remaining finite hypothesis is
therefore a state/history-dependent sequence switch, not another nominal
rate.

## Exact source and search tree

Every rollout restarts from the canonical 1100 ms source and exactly replays
the accepted ID-2Z15 full-F issues 0--31 to state 32. The search uses only
the already exact B/F/H token grammar:

```text
h8     HHHHHHHH
b8     BBBBBBBB
f8     FFFFFFFF
b4f4   BBBBFFFF
f4b4   FFFFBBBB
```

Round 0 branches all five macros at issues 32--39 and holds through issue
64. Rank complete branches by capture first, then terminal normalized score
over states 60--65, with stable arm-id tie-break. Preserve exactly the best
two parents as a beam; this selection is made by measured TSC branch outcome,
not a learned model.

Round 1 branches the same five macros at issues 40--47 from each selected
parent, then holds through issue 64. Rank all ten children by the same frozen
terminal rule. Execute exactly one fresh replay of the selected complete
path. The common endpoint is state 65.

Maximum real budget is `5 + 10 + 1 = 16` resets, `1040` advances, `1056`
states and `5280` required artifacts. Offline construction must first prove
all `5 + 25 = 30` possible one- and two-macro schedules exact and admissible.
No third round, widened beam, added token, retry, cleanup action or post-result
candidate is allowed.

## Gates

- current same-step paired-boundary R_geo/Z_geo and Ip are exact/noiseless
  before issue; takeover-era causal history remains visible;
- future successor is unknown before issue;
- issue `k` affects state `k+1`; no software queue is inserted;
- every target is exact Card15 and every physical per-coil issue delta is at
  most `0.3 A`, equality allowed; legacy clipping is forbidden;
- exact source/full-F prefix, actual/readback current, absolute-current,
  paired-boundary, Ip, abnormal/runtime, artifact and run-root gates fail
  closed;
- the simulator-development shell is `45 mm / 45 mm / 9% Ip`, the outer
  envelope is `50 mm / 50 mm / 10% Ip`, and empirical successor caps remain
  `2 mm / 2 mm / 150 A`; these are not a plant tube or recovery proof;
- all fifteen search branches must complete for a scientific verdict;
- selected replay must be exact through all 65 issues and 66 states;
- storage requires at least `110 GB` before launch and an estimated `40 GB`
  after the frozen `70 GB` maximum raw budget.

The unchanged six-state capture gate is:

```text
states 60--65 max source R/Z distance <= 25 mm
states 60--65 max one-step R/Z speed   <= 0.1 m/s
states 60--65 max |Ip-Ip_source|       <= 5%
```

## Routes and stopping rule

A capture plus exact replay authorizes only prospective Recourse-L1 design.
It is measured open-loop sequence authority, not a feedback controller or
terminal/recoverable set.

If the full beam and replay complete but capture fails, close this exact
full-F-prefix B/F/H two-layer sequence grammar and require a new physical
action basis or a separately justified reachability construction. Do not add
a third round, beam width, nearby state, extra rate or larger model. An
execution, raw, prefix or replay failure remains its own integrity route and
cannot be called scientific sequence failure.

All ID-2Z16 trajectories have zero fit/calibration/holdout/controller/expert/
BC/DAgger/RL weight. PASS or FAIL does not alter ID-2Z15 or any earlier result.

## Goal boundary

The final goal remains safe causal two-axis waypoint/path control from fixed
1100 ms with exact one-ms observation, exact Card15, persistent history,
uncertainty and independent hard/recourse layers, ultimately including
bidirectional repeated R_mid crossing. ID-2Z16 is only one finite authority
discriminator on one HFS source history.
