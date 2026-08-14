# R_geo/Z_geo 1 ms NR2R2C1a canonical-source replay result

Date: 2026-08-14 Asia/Shanghai

Final route:

```text
ONE_MS_NR2R2C1A_CANONICAL_SOURCE_REPLAY_QUALIFIED_C2A_DESIGN_ONLY
```

## Identity and execution

The prospective design was committed before execution. The physical runner
and frozen matrix came from `778b454`; the independent-audit hardening and
issue-coordinate correction are `de6f41a` and `85ad3a4`. The server executed
12 fresh canonical 1100 ms resets and 136 authentic 1 ms plant advances:

```text
q0 horizons                 4, 8, 16, 32 steps, two resets each
NR1R2 pattern A/B           4 steps, two resets each
completed rollouts          12/12
completed advances          136/136
raw states                  148
```

The immutable raw tree remains server-side at:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
  rgeo_zgeo_1ms_nr2r2c1a_runs/
  rgeo_zgeo_1ms_nr2r2c1a_canonical_source_replay_20260813_778b454
```

No C1a trajectory is model, fixture, training or expert data.

## Exact result

All six prospectively paired replay families passed. At every paired state,
the maximum absolute difference was exactly zero for paired-boundary
`R_geo/Z_geo`, `R_mid`, Ip, all 14 coil-current readbacks and all 48 wire-
current diagnostics. Issued Card15, action index, direct-successor effect age,
and the four semantic artifact hashes were exact. All state/interface/current/
slew/limiter/outer-envelope gates passed.

Final-raw inventory independently recomputed from every required file:

```text
required files                         740
required bytes                  8,716,152,752
inventory SHA-256  5b00be299251c019c7c4a9cc55d06bf224cd8c8668b11439671770734c6ec12e
```

The longest complete rollout took `56.535548300947994 s`, while all rollout
work totaled `241.4732376965694 s`. Therefore:

```text
offline canonical-source shooting mechanics     qualified in this envelope
online 1 ms rolling Oracle                       not eligible
```

As preregistered, `sprsina` was diagnostic. It was not hash-exact across all
states in any of the six pairs. This preserves B0's whole-artifact FAIL and
does not establish successor snapshot identity, hidden-state equality or an
arbitrary moving-prefix Oracle.

The q0 32 ms repeats independently reproduce B0's finite evolution:
`-17.601295 mm R`, `+23.4419245 mm Z`, and `-335.723 A Ip` at the endpoint.
This is further confirmation that q0 is not a qualified source hold.

## Independent-audit correction

The first independent audit at `de6f41a` is preserved as FAIL. It exposed two
audit/reporting-coordinate errors rather than a changed plant action:

1. after each advance, the retained `state[k]/inputa` contains the outgoing
   Card15 issued from state `k`; the first auditor incorrectly inspected
   `state[k+1]/inputa`;
2. the primary recorder counted state0's reset-template `inputa` before the
   first issue rewrote that file. Final raw is 210 bytes smaller in exactly
   state0 `inputa` for each of 12 rollouts, accounting for the complete
   `-2520` byte difference. No other artifact-size mutation occurred.

V2 was a zero-TSC reparse of the same raw. It recomputed the 12 complete
action streams, all gates, all six pairs, timing, and the final-raw inventory,
and passed with no failures. It did not overwrite the first audit or the
primary result. Compact hashes are:

```text
primary result       0b8eda34bd730aa59e2d3151ab69d445d4e5aeefa8bac6485c1161fecb86cebd
original audit FAIL  fbb584e5b6cf903b853482f87671fcd2e885a6945db84d3db3983e9faa8cbb9a
V2 audit PASS        f69edee36cc02ef8b930dc5f02d548e0828a5723eca2c1fd359d345f1768c294
```

## Validation and claim boundary

- local project-venv focused/adjacent unittest: `24/24`;
- installed server focused unittest: `14/14`;
- deployed auditor hash matched local before V2;
- all copied compact JSON/log SHA-256 values match the server originals.

This is an execution/interface/source-replay-mechanics PASS only. It does not
qualify a novel action, nominal hold, backup, Recourse-L1, response model,
atlas, controller, MPC, adaptive update, RL, tracking, or global
reachability. Its only route consequence is permission to prospectively
design C2a. Any C2a action outside the already measured finite-safe cells
still requires independent pre-result successor support.
