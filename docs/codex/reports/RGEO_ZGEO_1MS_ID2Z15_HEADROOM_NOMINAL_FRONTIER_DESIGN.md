# R_geo/Z_geo 1 ms ID-2Z15 headroom nominal frontier design

Date: 2026-08-20 (Asia/Shanghai)

## Identity

`rgeo-zgeo-1ms-id2z15-headroom-nominal-frontier-v1`

This design is frozen before implementation or any ID-2Z15 TSC response.
It follows the final ID-2Z14 source-local grammar failure and the separately
recorded post-ID-2Z14 nominal/reachability review.

## Matrix and clocks

Every rollout starts from the authentic canonical 1100 ms source. Issue 0
is exact q0. Issues 1--31 either hold q0, add the exact declared fraction of
one p03-forward/F increment on every issue, or implement the declared full-F
50% duty cycle. Issues 32--47 hold the attained target. Action issue `k`
affects state `k+1`; the common retained endpoint is state 48. Terminal
metrics use states 43--48 inclusive.

Frozen branches, in order:

```text
q0       alpha_F=0.00 every issue
f25      alpha_F=0.25 every issue
f50      alpha_F=0.50 every issue
f75      alpha_F=0.75 every issue
f100     alpha_F=1.00 every issue
duty50   full F on odd issues 1..31, hold attained target on even issues
```

After all six branches complete, choose capture first and otherwise minimum
terminal normalized score with stable arm-id tie-break. Execute exactly one
fresh selected-branch replay. Maximum budget is `7` resets, `336` plant
advance attempts, `343` retained states and `1715` required artifacts. No
retry, cleanup action, post-result arm or altered horizon is allowed.

## Exact action and safety gates

- same-step paired-boundary R_geo/Z_geo and same-step Ip are exact/noiseless
  before each issue; takeover-era causal observations/actions remain visible;
- future successor is unknown before issue;
- exact Card15 targets and physical 14-current deltas are constructed before
  runner invocation; maximum per-coil issue delta is `0.3 A`, equality
  allowed; legacy clipping may not be relied on;
- action/effect clock is issue `k` to state `k+1`, with no software queue;
- absolute current, paired boundary, finite Ip, abnormal/runtime and exact
  prefix gates fail closed;
- simulator-only prospective step caps are `2 mm / 2 mm / 150 A`; outer
  envelope is `50 mm / 50 mm / 10% Ip`;
- every branch must complete for a scientific route; an allowed safe stop is
  preserved as finite execution evidence but makes the frontier
  scientifically inconclusive;
- run-root isolation, no overwrite, storage, complete five-artifact state
  inventory and structurally separate raw audit are mandatory.

The empirical caps and geometric margin are not a plant tube, controller
safety proof or recourse guarantee.

## Scientific gates and routes

The unchanged six-state capture gate is:

```text
max source R/Z distance <= 25 mm
max one-step R/Z speed   <= 0.1 m/s
max |Ip-Ip_source|       <= 5%
```

If selected capture and fresh replay both pass, route only to prospective
Recourse-L1 design.

If capture fails, a headroom-development route requires a selected arm in
`{f25,f50,f75,duty50}`, exact replay, terminal states all within
`40 mm / 0.60 m/s / 5% Ip`, and normalized terminal score at least `0.10`
lower than both q0 and f100. It authorizes only a fresh fit-eligible matched
residual campaign around the selected nominal. No ID-2Z15 trajectory is
fit-, calibration-, holdout-, controller-, expert-, BC-, DAgger- or
RL-eligible.

Otherwise the constant-rate/duty headroom nominal route closes. The next
review must choose an algorithmic sequence/reachability construction or new
physical basis. It may not add another rate or reinterpret relative
improvement as capture.

## Claim boundary

ID-2Z15 is a finite canonical-source nominal-allocation discriminator only.
It is not a model, tube, controller, MPC, recovery, waypoint/path,
R_mid-crossing or global-reachability result.
