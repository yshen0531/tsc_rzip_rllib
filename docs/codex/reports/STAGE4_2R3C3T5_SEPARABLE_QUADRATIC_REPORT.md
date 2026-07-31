# Stage4.2R3c3T5 separable-quadratic report

Date: 2026-07-31 (Asia/Shanghai)

## Result

The authenticated separable even/odd quadratic route failed:

```text
signed raw files / pairs                         512/512, 256/256
odd-response maximum reproduction error                       0.0
signed-endpoint maximum reproduction error                    0.0
T3 pass/margin reproduction                              32/32
optimistic quadratic formal pass                         16/32
failed T3 contexts repaired                               0/16
baseline-pass regressions                                  0/16
unchanged odd condition <= 25                            11/32
R3c4 implementation authorized                              no
real TSC executed                                           no
```

The interaction-free quadratic approximation does not explain or repair the
T3 failures. This is a pre-execution model-route failure, not a real
closed-loop control failure.

## Exact revisions and paths

```text
branch
  codex/stage4_2r3c3t2-held-transport

initial implementation commit
  46e0f60dd0a927043534977927daa92d9f7adb16

prospective design commit
  15dfcf58dafafe3001230b63e9562e2c533e8cc0

numerical-authentication hotfix commit
  ff3b391c672c8ed82c26b402f7c39173ea3adb87

hotfix contract addendum commit
  c6902bddccfac61d5c82ebabec37348d0daa7628

final T5 tool SHA-256
  36668e8d8661bf6ca79ad4083260c9b5bf9e42e0c64cdf6cd994331b45ae7b1e

result-forensics and compact-evidence commit
  4a70c7f71bf20896134e34479c6511ccd4394dbe
```

Final staging:

```text
/home/yangshen0711/tsc_software/
stage4_2r3c3t5_quadratic_h1_ff3b391
```

Final server result:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t5_separable_quadratic/
stage4_2r3c3t5_separable_quadratic_20260731_ff3b391.json
```

Final server log:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
stage4_2r3c3t5_separable_quadratic_20260731_ff3b391.log
```

Compact local evidence:

```text
docs/codex/audits/
stage4_2r3c3t5_separable_quadratic_20260731_ff3b391/
```

## Raw and model authentication

The tool authenticated every exact plus/minus source file referenced by the
T3 bank:

```text
R3c3 local bases                                      256 files
T1 long-separation bases                              128 files
T2 held-transport bases                               128 files
total                                                 512 files
signed pairs                                           256 pairs
file/hash/result/horizon failures                            0
```

All 32 R3c1 baseline files also matched the T3 bank. Raw-derived odd
responses reproduced all stored T3 odd columns exactly. For each individual
basis, the high-precision reconstruction at `c=+1` and `c=-1` reproduced the
corresponding raw endpoint exactly.

T3 optimized results were independently reconstructed:

```text
context/pass matches                                    32/32
maximum T3 signed-margin error                            0.0
```

The model retained exact coefficient bounds `[-1,1]` and the immutable
formal timing contract.

## Even-term inventory

Across 256 context/basis even terms:

```text
maximum R/Z magnitude                             0.00043210 m
median per-term maximum R/Z magnitude              0.00007661 m
maximum Ip magnitude                                  8.1185 A
maximum speed magnitude                          0.00656950 m/s
```

These terms are real per-basis central responses, not zeros or missing data.
The diagnostic nevertheless omits all cross-basis interactions and does not
claim combined-action fidelity.

## Failure forensics

Remaining margins:

```text
best                                            -0.01697797
worst                                           -0.32152175
mean                                            -0.13650941
median                                          -0.10553116
```

Relative to the T3 odd-only result:

```text
improved / unchanged / worsened                    11 / 0 / 5
minimum margin delta                            -0.00918742
maximum margin delta                             0.01078345
mean margin delta                                0.00384946
median margin delta                              0.00574885
```

The even terms have a measurable but mixed effect and repair no context.

Failure strata remain:

```text
delay 0 / delay 2                                  4 / 12
slew 1.0 / slew 0.9                               4 / 12
nominal / RZ_p10_m10                               4 / 12
minus_first / plus_first                            8 / 8
position / post-speed active constraints           15 / 1
```

Coefficient saturation counts over the 16 failures:

```text
R3c3 early mode0                    12/16
R3c3 early mode1                    10/16
R3c3 deadline mode0                 11/16
R3c3 deadline mode1                  9/16
T1 long-separation mode0            16/16
T1 long-separation mode1            13/16
T2 held-transport mode0             16/16
T2 held-transport mode1             14/16
```

The dominant unresolved limitation remains target-relevant bounded causal
authority, not omission of separable per-basis even terms.

## Attempt and error classification

The first T5 attempt used the original implementation and stopped before
optimization/output:

```text
log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t5_separable_quadratic_20260731_46e0f60.log

local log SHA-256
  ec91d06110c36ce5a30cef622c8cb792298f82b6c761b700bab2483662e32945
```

Float64 recomposition of approximately 30 kA Ip incurred exactly one ULP,
`3.637978807091713e-12`, above the frozen `1e-12` identity gate. Odd/raw
agreement was still exactly zero-error. The H1 fix used 80-digit Decimal
only for the defining identity check and retained the original threshold.

Classification:

```text
first-attempt numerical authentication bug                 yes
first-attempt scientific result                             no
first-attempt output created                                no
final runtime/environment error                             no
final deployment/import error                               no
raw or bank corruption                                      no
statistics/reporting error                                  no
pre-execution separable-model route failure                yes
real closed-loop control failure                        not run
```

The final result and logs have hashes:

```text
result
  960a82aea9eef90c85bb2b2bc5f6ebb0772c8a8f263915b1122904a3bd13bf82

final log
  bac22789eeb7d9e229cbb49d4f2a99293ce2941f59e919bb9ab0cb6bf1b84dd4

independent result forensics
  ebbf836510b097c7f7a4bd8550f78cd662e314430744da9a8824c33f0d237d3b
```

## Validation and commands actually run

Local:

```text
focused T5 tests before / after hotfix                  4/4, 5/5
complete repository unittest before / after          563/563, 564/564
Python compile / compileall                                PASS
repository JSON parse                               1501/1501
git diff and line-length checks                            PASS
independent result/bound/aggregate recomputation           PASS
```

Server:

```text
exact project/virtualenv/path preflight
three staging script SHA-256 checks
Python compile and exact-path import
512 raw file and 32 baseline authentication
single exact PID monitoring
server-side row, margin, saturation, and even-term analysis
stage process and gotsc absence checks
direct compact-file scp without archives
```

Actual Ray/TSC task count was zero. Large raw JSON.GZ and banks remained on
the server.

## Decision

Reject the interaction-free separable quadratic route. Do not implement or
launch R3c4 from the current eight directions.

All zero-new-TSC extensions of the existing response directions have now
failed:

```text
T1 or T2 six-basis replacement                 16/32
T3 eight-basis complementarity                 16/32
T4 amplitude extrapolation through 2×          20/32
T5 separable quadratic model                   16/32
```

The next stage must prospectively identify genuinely new target-relevant
temporal or actuator directions. It should first derive the missing direction
from authenticated R17 action residuals and visible target error, then freeze
a new bounded signed-probe campaign. It must not reuse larger versions of
the same eight columns or treat probe trajectories as demonstrations.

R3c4, BC, DAgger, and bounded residual RL remain prohibited.
