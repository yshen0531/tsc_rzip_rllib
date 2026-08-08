# Stage4.2R3c3T13S24D1R14R8R13 forensic report

Finalized on 2026-08-08 Asia/Shanghai from the accepted server files, the
downloaded compact audit, the exact deployed source, and structurally
independent recomputation. Chat summaries are not evidence for this report.

## 1. Final classification

```text
route
  MEASURED_ADDITIVE_DIRECTION0_ON_DIRECTION2_AUTHORITY_INSUFFICIENT_NEW_SEQUENCE_IDENTIFICATION_REQUIRED

integrity gate       PASS
scientific gate      FAIL
real TSC executed    false
new raw              0
plant advances       0
```

R8R13 is a clean finite measured-additive authority-design failure. Under the
prospectively frozen optimistic R/Z/Ip superposition, no one globally fixed
R8R11 direction-0 transient added to the R8R12 direction-2-positive
staircase repaired any of the ten failed R8R7 baselines. It is not a runtime,
deployment, source-authentication, raw, restart, causality, reporting,
formal-evaluator, safety, combined-action, plant, controller, real-MPC, Gate
A, or global-reachability failure.

The identity is immutable. It may not be rerun with a larger family, a
context-specific oracle, or a weakened gate. The accepted route requires a
new prospectively frozen sequence-identification stage.

## 2. Frozen identity and package

```text
design checkpoint          6a58404
implementation checkpoint  a4f999e
package checkpoint         da1585d
design SHA-256
  f643d4ded6131db8264847f8ce4aff121c4165c49666eb7b7e34211c0c72bc1f

PACKAGE_MANIFEST.json
  89792 bytes
  7d30e86e0cd879367ae04045536a1d9d4a29193a24b8da3570109b2d5285ea6b
SHA256SUMS
  131471 bytes / 1047 declared paths / LF only
  9acc8d70d73e25d4ac173ae3fbeda344f12fd4c5ca85cc36b1c71bab5895008a
```

The package was built by copying all 1,047 declared files into a new empty
repository-local directory and then adding the manifest and sums, for 1,049
files before validation caches. It was transferred with `scp -r`; no archive
was created or extracted. Only manifest-listed files were installed into the
server project.

Local source hashes were:

```text
config       55b203776c91030a3e616a89d51b02ee84c64596384834af93f80ada2bd921e8
primary      ff123e4e2fbf5633060f6837f3a94da0a0f6aa04a3ae469513916f8d510fbbb4
independent  de815119d760cb82bb854cc100e993f17e6415f3f1a90d88c029ca1438248f7a
```

## 3. Validation evidence

The project virtual environment passed compilation, focused `7/7`, and full
`1269/1269` tests after loading the existing Windows `resource` shim. The
empty direct-copy package passed 1,047 hashes, compilation, focused `7/7`,
and full `1269/1269`, with one expected isolated-evidence skip.

The existing server virtual environment then passed, in both staging and the
installed project:

```text
declared hashes       1047/1047
JSON parse            PASS
bash -n               PASS
compileall            PASS
focused unittest      7/7
full unittest         1269/1269, one expected skip
```

The first staging validation command stopped before validation because SSH
shell quoting removed quotes from an inline Python expression. A replacement
using native `sha256sum -c` passed. The first replacement invocation also
expanded the `find -name` wildcard before `find`; an immediately separate
escaped-wildcard invocation completed exact `bash -n` successfully. These
were validation-command invocation errors, not package, implementation, or
scientific failures. No source or result was changed.

## 4. Exact server run

```text
run root
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r14r8r13_runs/
  stage4_2r3c3t13s24d1r14r8r13_measured_additive_direction0_on_direction2_composition_20260808_da1585d_v1

stage directory
  stage4_2r3c3t13s24d1r14r8r13_measured_additive_direction0_on_direction2_composition
```

The stage contains seven compact JSON files totaling 234,211 bytes. It has no
`raw/`, JSON.GZ, or snapshot file. Source raw stayed in its immutable source
directories.

Accepted stage hashes are:

```text
primary detailed     3d0368cde8e0980a1e78d1a355b106ae8479da5781058858ad5f4f7199dcec06
primary summary      579e21f11dcb544440971f84abd7f0b360e43d3a7f2a09d7f1bd725785e2fc83
independent          6cdae996637c73ef28d7696dfbb8e71723c3607baf36ea6c5f73e549f7b96c27
final report         9d874cca8b63b7bad11b255dcfe2b32a14b402534f58ab6f91f12b6d6d564485
source auth          3b63909e0213f478576b3aaf613138702b1149723fa4dc7e6929300ff25eadd3
stage manifest       0ade6f4f901ca372640b960f1e45580964bdbffed99bc3008c2d26567c538d21
stage state          b5adb16665416146826402469c619dcc420173c5ee167c45328ad93aa6702e53
```

The downloaded compact copy reproduced all seven hashes and the final
state/route.

## 5. Authentication and numerical integrity

Both implementations authenticated and strictly parsed:

```text
R8R7 matching baselines       16 raw / formal pass  6
R8R11 direction-0 candidates  96 raw / formal pass 36
R8R12 direction-2 staircases  16 raw / formal pass  6
total                         128 raw
```

For every source family, formal pass, selected arrival, and signed margins
agreed between the two unchanged metric paths; maximum difference was zero.
All sixteen zero-correction controls reproduced the exact R8R12 arrays and
formal rows. The two additive constructions differed by at most
`1.0842021724855044e-19`, below the frozen `1e-12` tolerance. The composed
formal paths again differed by zero.

Primary and the structurally independent implementation agreed exactly on
every candidate summary, ranking, selected candidate, numerical aggregate,
gate, and route.

## 6. Scientific outcome

All six global candidates preserved the six baseline passes, but every one
remained at `6/16` and repaired `0/10` failures:

```text
index  issue  sign  formal  repairs  regressions  failed-margin gain min / median / max
0      14     -     6/16    0/10     0            -0.0112491667 / 0.0890181935 / 0.1362968651
1      14     +     6/16    0/10     0            -0.0111640667 / 0.0887210009 / 0.1366918984
2      18     -     6/16    0/10     0            -0.0113623667 / 0.0891632405 / 0.1364770651
3      18     +     6/16    0/10     0            -0.0110496000 / 0.0887019103 / 0.1364757651
4      22     -     6/16    0/10     0            -0.0118955000 / 0.0891913313 / 0.1362622651
5      22     +     6/16    0/10     0            -0.0108065667 / 0.0886613584 / 0.1366534651
```

The frozen rank is `[5,3,1,0,2,4]`; candidate 5 (issue step 22, positive
sign) wins only on the fourth tie-breaker. It does not meet the required
`>=7/16` and `>=1/10` repair gates.

The large positive median gains arise primarily from the already measured
R8R12 staircase. Adding the short direction-0 transient changes margins but
does not cross a formal boundary. This rules out only the frozen optimistic
additive family. Because no simultaneous action/current trajectory was
constructed or executed, it cannot be used to infer combined-action safety,
nonlinear cross-direction behavior, or real closed-loop performance.

## 7. Boundary after R8R13

R8R13 is frozen and all 128 source trajectories remain forbidden from expert,
BC, DAgger, or RL data. The next result must use a new identity and a genuinely
new prospectively frozen sequence-identification design. A later measured-
authority result can at most authorize a separately frozen causal
selector/controller and then real MPC qualification. Gate A and all learning
remain blocked.
