# R_geo/Z_geo 1 ms NR2R2C2aA1 level-2 authority design

Status: prospectively frozen before implementation or new TSC.

Date: 2026-08-14 Asia/Shanghai

## Purpose

C2a's two constant 0.15 A-offset searches safely failed to hold and stayed
near q0 over 32 ms. Their isolated favorable state5/state12 deviations were
not persistent. C2aA1 asks only whether the same lower-Ip p07 direction at a
componentwise maximum 0.30 A offset produces a sustained signed response
opposing q0 drift.

This is a development authority discriminator, not nominal-hold validation,
recovery, model fitting or control. Its two trajectories are forbidden from
fixtures, training and expert data. A PASS may authorize only a separate
time-varying C2a nominal-search design.

## Exact schedule and support

Both canonical-source resets replay the same 32-step schedule:

```text
step 0       q0
step 1       level1, the already measured p07 0.15 A-offset target
steps 2..15  level2, exactly twice the Card15 field offset from q0
step 16      level1
steps 17..31 q0, passive tail observation
```

Every adjacent issued target changes each single-turn coil by at most 0.15 A
(some lattice components change 0.10 or 0.145833 A), below but not replacing
the user's hard `<=0.3 A` limit. Level2 remains componentwise within the
q0+/-0.3 A amplitude domain already covered by the consumed NR2R1 dev/cal
campaign; the exact p07 level2 combination and its longer history are new.

The independent empirical successor gate remains prospectively fixed at
`2 mm R / 2 mm Z / 100 A Ip`, versus prior observed maxima below
`0.856 mm / 0.856 mm / 45.995 A`. Before every issue the state must remain in
the 25 mm/5% inner envelope and reserve the full bound inside the 50 mm/10%
outer envelope. A bound/interface failure stops before any next issue.

## Repeatability and authority gates

The two complete rollouts must be exact under C1a's finite source-replay
gates: paired R_geo/Z_geo/R_mid, Ip, 14 coil currents, 48 wire currents,
issued/effect history and the four semantic artifact hashes. `sprsina` stays
diagnostic and cannot establish snapshot identity.

For states 3..16, compare each candidate state with the tracked exact q0
state at the same absolute time and define:

```text
opposition(t) = [R_candidate(t)-R_q0(t)]
              - [Z_candidate(t)-Z_q0(t)]
```

Positive values oppose the observed q0 `(-R,+Z)` drift. Authority PASS
requires, in both exact replays:

```text
mean opposition                         >=0.00025 m
fraction of states with opposition > 0 >=0.50
maximum opposition                      >=0.00150 m
max |Ip_candidate-Ip_q0|                <=100 A
```

The level1 comparator's mean opposition over the analogous states was only
`0.08145 mm`, positive at `2/14` states. These gates require persistent
improvement rather than accepting another isolated peak. They are not a hold
or tracking target.

## Budget and routes

```text
canonical resets             2
steps per reset             32
maximum plant advances      64
```

```text
offline/source/package failure
  ONE_MS_NR2R2C2AA1_OFFLINE_FAIL_NO_TSC

runtime/interface/current/successor-bound failure
  ONE_MS_NR2R2C2AA1_EXECUTION_FAIL_STOP

paired replay mismatch
  ONE_MS_NR2R2C2AA1_REPEATABILITY_FAIL_STOP

safe exact execution but persistent-authority gates fail
  ONE_MS_NR2R2C2AA1_LEVEL2_AUTHORITY_FAIL_REDESIGN

all frozen gates pass
  ONE_MS_NR2R2C2AA1_LEVEL2_AUTHORITY_PASS_TIME_VARYING_C2A_DESIGN_ONLY
```

No route here authorizes Nominal-H1, C2b, response atlas, model, MPC,
adaptation or RL.
