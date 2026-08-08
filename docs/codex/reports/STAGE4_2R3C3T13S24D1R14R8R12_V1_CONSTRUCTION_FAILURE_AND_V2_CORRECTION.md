# Stage4.2R3c3T13S24D1R14R8R12 v1 construction failure and v2 correction

Date: 2026-08-07 Asia/Shanghai

## Result

R8R12 v1 is final as:

```text
CAUSAL_CUMULATIVE_DIRECTION2_STAIRCASE_EXECUTION_OR_SAFETY_FAIL_STOP
```

This is a controller-construction implementation failure before any plant
advance. It is not a control result, safety-envelope violation, plant result,
formal-tracking result, raw-corruption result, or global-reachability result.
The v1 run is immutable and may not resume.

The exact run is:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14r8r12_runs/
stage4_2r3c3t13s24d1r14r8r12_causal_cumulative_direction2_staircase_authority_sentinel_20260807_34957c8_v1/
stage4_2r3c3t13s24d1r14r8r12_causal_cumulative_direction2_staircase_authority_sentinel
```

## Package and preflight evidence

The frozen scientific design remains checkpoint `1d09508`, SHA-256
`46d959813a0810970e7ea6ab5a5a097c9afa5949e7642f22fc4b17a19ccd2f16`.
The initial implementation checkpoint was `9d3f4ca`. Two launcher-only helper
resolution corrections were committed at `ea78b65` and `1fe8e67`; both failed
attempts stopped before a run directory was created and therefore produced no
Python, Ray, TSC, state, or raw evidence.

The physical v1 package used for the accepted offline and safety attempt was
checkpoint `34957c8`:

```text
PACKAGE_MANIFEST.json  0f145114e9af51726b997f53f5f8119e0a65139a65a7cd5b51bf94ad0aa0851c
SHA256SUMS             c94e0c8d869231989339f5709e605f4f63c065f17ba0a304d6981ec79aa6e593
controller module      232c840810ee2ff056ebb17c6da110a8b97ae304a16c3048df93660b51d1c170
```

Local, empty direct-copy, server staging, and installed-server validation
passed 1,039 declared hashes, `bash -n`, compilation, focused tests, and the
complete 1,261-test suite. The isolated copies and Linux server had one
expected compact-server-evidence skip. No archive operation or global Python
was used.

Primary offline construction and structurally independent recomputation then
passed exactly:

```text
source R8R7 / R8R11 / lineage authentication       PASS
specifications                                      16/16 exact
level constructions                                 64/64
causal exact-target refresh constructions          352/352
maximum issue incremental action              0.1409259259259261
maximum refresh incremental action            0.0000037037037049
maximum predicted current utilization         0.3905000000000000
new raw / TSC / plant advances                       0 / 0 / 0
primary/independent construction agreement                 exact
```

Accepted offline hashes are:

```text
offline primary      0998b852773769f061f0e85ab705941c99088ab6d3c53bad964094480d408af1
offline independent  7778d15bd677b81dc493e564674c5a3847d975182ccf0359863a50ff276cafa1
```

## Immutable safety raw evidence

Four frozen safety tasks entered the real server worker path. All four wrote
strictly parseable structured raw, but controller construction raised before
the first controller trace or plant advance:

```text
ValueError('D1R14R6 per-spec issue schedule changed')
```

Each raw has exactly one initial trajectory state, zero controller traces,
zero physical actions, no snapshot, and zero post-initial plant states. The
individual immutable raw hashes are:

```text
r8r12_safety_00.json.gz  4310 bytes  5c5d1a4cdbcf250e5e847d288736edb5294325c0e4e5e25330f725fdb96be324
r8r12_safety_01.json.gz  4299 bytes  fc7161cfb67ec144134c46e9294b795e95625e6c02cb9d364c20f5f2f1b81eab
r8r12_safety_02.json.gz  4532 bytes  f84d39b4fa811e762ab03e91178d829361bd2cbfe32b1bdf9e2f569fbb691cc7
r8r12_safety_03.json.gz  4546 bytes  19f48643ef6dd0ca23da22b5fa70f8f95539743de4772f457fb445f0e6e860e3
```

Canonical inventory:

```text
count   4
bytes   17687
digest  f59d7aa22205d995519742b049c516e0403a18840d593b5d0db9e058150d549d
```

Qualification raw count is zero. Candidate formal outcomes were never opened.

## Reporting repair

The initial primary audit correctly marked missing issue/refresh data
fail-closed, but represented the absent maxima as positive infinity. Strict
JSON serialization then failed. This second error was reporting-only and did
not alter raw, execution, or the failing route.

Checkpoint `c9111cc` replaced absent maxima with JSON `null` and added the
read-only `repair-safety-report` command. Its source contains no worker or
controller evaluation call. Package checkpoint `4f14aa3` passed empty-copy,
staging, and installed 1,039-hash validation, focused `10/10`, and complete
`1262/1262` tests. The command authenticated the four immutable failures and
recorded:

```text
raw count                                4
controller initialization failures      4
physical action count                    0
plant advance count                      0
qualification outcomes opened        false
formal outcomes opened               false
```

Independent raw recomputation agreed with the primary report exactly while
correctly retaining `passed=false`. Accepted compact hashes are:

```text
safety raw primary      d277210010a9c155848161443921821c0bfd35ff9a054280ca01a9b5fc68a837
safety raw independent  65f392cccd390a3fdc4a3f10ff7cf5c20ab9fc75229f70744309a16294f3cf1c
stage manifest          01b650cac464e8e8d30fe4e1b3f28a80dcfa8e4f4102d1c909c65677897c9b76
stage state             57217b2cd9025ace78a2eca8dad0b84fd26a21cf6254b4fe6684a5f842d2f858
```

## Root cause

The R8R12 subclass owns the intended post-prefix schedule at task steps
`[10,14,18,22]`, but its constructor passed task step 10 to the inherited R6
signed-probe constructor. R6 accepts only its historical issue set
`(14,18,22)`. The inherited constructor therefore raised even though the
subclass would have overridden all actions from task step 10 onward.

This is an implementation/interface mismatch. It does not invalidate the
prospectively frozen R8R12 staircase geometry or offline Card15/current gates.
It also provides no evidence about the physical response to that staircase.

## Prospectively frozen v2 correction

Before any v2 implementation, offline outcome, raw, or TSC, the corrected
identity is frozen as:

```text
campaign identity   causal_cumulative_direction2_staircase_authority_sentinel_v2
controller revision causal_cumulative_direction2_staircase_v42r3c3t13s24d1r14r8r12_v2
package revision    r42r3c3t13s24d1r14r8r12_causal_cumulative_direction2_staircase_v2
```

The only controller construction correction is that the inherited R6
constructor receives its valid, inert signed-probe placeholder schedule
`issue=14`, `cancel=15`, `zero_after=16`. The R8R12 subclass continues to
delegate only task steps 0--9 and owns every task step from 10 onward, so its
actual prospectively frozen staircase remains exactly `[10,14,18,22]` with
the same direction-2-plus coordinate, exact Card15 construction/refresh,
action/current/saturation gates, state-35/37 endpoint, and no final
cancellation.

All specification contexts, safety/qualification counts, source contracts,
formal timing, scientific repair gate, and learning-data prohibition remain
unchanged. v2 must use a new run directory and may not resume or overwrite v1.
It must repeat offline primary/independent construction, then at most four new
safety trajectories. Qualification remains blocked until exact dual safety
raw agreement. Formal outcomes remain blocked until all 16 v2 raw authenticate.

Neither v1 nor v2 trajectories may enter expert or learning data. R8R12 v2 is
still only an action-authority sentinel; a PASS could authorize only a
separately frozen causal selector/controller design. It is not MPC, Gate A,
expert data, BC, DAgger, or residual RL authorization.
