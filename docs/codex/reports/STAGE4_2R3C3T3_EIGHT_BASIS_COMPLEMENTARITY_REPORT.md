# Stage4.2R3c3T3 eight-basis complementarity report

Date: 2026-07-31 (Asia/Shanghai)

## Result

The prospectively frozen eight-basis audit failed both independent gates:

```text
contexts evaluated                                  32/32
eight-basis rank                                    32/32
eight-basis condition <= 25                         11/32
maximum condition                              78.1544662
R3c1 baseline formal passes                         16/32
optimistic eight-basis formal passes                16/32
failed baseline contexts repaired                    0/16
baseline-pass regressions                            0/16
R3c4 implementation authorized                         no
real TSC executed                                      no
```

This is a genuine pre-execution design failure. It is not a runtime,
deployment, raw-data, restart, statistics, reporting, or real closed-loop
control failure.

## Exact code and paths

```text
branch
  codex/stage4_2r3c3t2-held-transport

audit implementation commit
  1a75fffdd50dfcfde993d31ea1e63194f478235e

audit implementation SHA-256
  e3c067574ebcb98dc6f30d4e29a41521c38368862fa23f01c0714e8d28dac093

prospective design commit
  ca695af

independent result-forensics SHA-256
  45a08ec5071cc7adfd10e531327c9c347ea5643be6474eadc68bb496dbfc91da

result-forensics and compact-evidence commit
  6a08ef78f01b6224e9a24ecf073f9ebadcad1432
```

Server staging directory:

```text
/home/yangshen0711/tsc_software/
stage4_2r3c3t3_eight_basis_1a75fff
```

Server result directory:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t3_eight_basis_feasibility/
stage4_2r3c3t3_eight_basis_feasibility_20260731_1a75fff
```

Server log:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
stage4_2r3c3t3_eight_basis_feasibility_20260731_1a75fff.log
```

Compact local evidence:

```text
docs/codex/audits/
stage4_2r3c3t3_eight_basis_feasibility_20260731_1a75fff/
```

## Input and output authentication

The audit authenticated the exact post-T2 six-basis bank, T1 raw inventory,
T2 raw inventory, R3c1 baseline inventory, frozen six-basis builder, and
frozen formal evaluator recorded in the prospective design.

All four T3 outputs share provenance digest:

```text
a536183fc8e192fafc8c28bdc9897ecf3acb5dc9f0c5ed6257f236e2e8c03935
```

The frozen formal evaluator reproduced all 32 saved pass values with exactly
zero signed-margin error. The manifest inventory exactly matches the three
primary output files.

The large banks remain on the server:

```text
eight-basis audit bank             4,881,221 bytes
  f6cf5ae8642b68fc9947eaa1c2a3d18074e4e3e5be1f422f50ffa03f1a1a1970

eight-basis controller bank        2,551,396 bytes
  6328ef4116ea5a2ecac66d04583fb92af7830ad5ff6ea484486524cbd2021e86
```

Only compact evidence was downloaded:

```text
feasibility JSON
  08c253f7e8b66165704ec22e7b56c7e5c1abb1a30b8738be8b1d240211729744

manifest
  2c9389af0ea8d0f9538a0e4af34e604331981e77cfc0bc9c5bf353617c541b09

independent comparative forensics
  b62cd1e1bb3ee7d463ce6a1c44372955e1fa46850e5fe519ecf9896b6224a7b4

nohup log
  5a0bca4cf91c2b57b96b00a99fd75c407ae2bb72ef11945f8d5e938fbd6b5655
```

The controller-facing bank is explicitly identification-only, is not
demonstration data, and contains no hidden-history labels.

## Formal-feasibility forensics

The 16 failed contexts are exactly the 16 failed old four-basis contexts.
Remaining signed margins are:

```text
best                                            -0.02715917
worst                                           -0.32559332
mean                                            -0.14035887
median                                          -0.10457549
```

Active constraints:

```text
position                                                14
post-arrival speed                                       2
```

Failure strata:

```text
delay 0 / delay 2                                  4 / 12
slew 1.0 / slew 0.9                               4 / 12
nominal / RZ_p10_m10                               4 / 12
minus_first / plus_first                            8 / 8
```

The eight-basis margin improves every failed context relative to each
predecessor, but never reaches zero:

```text
comparison        improved  unchanged  worsened  mean margin gain
old four                16          0         0       0.04217628
T1 six                  16          0         0       0.01799787
T2 six                  16          0         0       0.02290476
```

The improvement is therefore real temporal complementarity, but it is
insufficient causal authority under the frozen `[-1,1]` coefficient
contract.

Coefficient saturation counts over the 16 failed contexts are:

```text
R3c3 early mode0                    16/16
R3c3 early mode1                    16/16
R3c3 deadline mode0                 15/16
R3c3 deadline mode1                 16/16
T1 long-separation mode0            16/16
T1 long-separation mode1            16/16
T2 held-transport mode0             16/16
T2 held-transport mode1             16/16
```

For every failed context, T1 mode0 and T2 mode0 are at `-1`, while T2 mode1
is at `+1`. This repeated boundary direction is strong evidence that the
current authenticated temporal envelope is exhausted. It does not prove
that simply extrapolating the local response beyond the identified amplitude
is valid.

## Condition forensics

All 32 eight-column matrices have rank eight, so this is not rank loss.
However, only 11 meet the preregistered condition limit:

```text
minimum condition                              13.4685916
median condition                               26.9779314
maximum condition                              78.1544662
condition pass / failure                           11 / 21
```

Formal and condition failures are not the same set:

```text
formal fail, condition fail                         11
formal fail, condition pass                          5
formal pass, condition fail                         10
formal pass, condition pass                          6
```

Thus relaxing the condition gate would still leave all 16 formal failures,
and improving formal margins alone would still leave an ill-conditioned
eight-column representation. The added T1 and T2 shapes are useful but
partly redundant.

## Error classification

```text
runtime/environment error                              no
deployment/import error                                no
raw or bank corruption                                 no
statistics/reporting error                             no
plant restart failure                             not run
real closed-loop control failure                  not run
pre-execution design failure                           yes
eight-basis identifiability gate failure               yes
optimistic formal control-design failure               yes
R3c4 implementation authorized                          no
```

The audit process exited normally and no `gotsc` or stage-specific TSC
process was present. Two read-only monitoring commands were malformed by
Windows SSH quote stripping; a subsequent stdin-safe diagnostic established
the actual process exit, complete log, output inventory, and absence of a
stage TSC process. These monitoring-command errors did not affect any audit
input or output.

## Validation and commands actually run

Local/repository validation:

```text
Python compile / compileall                             PASS
repository JSON parse                           1497/1497
focused T3 audit tests                                  3/3
complete unittest discovery                         555/555
git diff --check                                        PASS
compact result SHA-256 verification                     PASS
```

The focused T3 tests and full suite had already passed before the server
audit. After downloading the result, the complete 555-test suite was rerun
and passed. One attempted `python -m pytest -q` invocation did not run tests
because the default local Python has no `pytest`; no package was installed.
The required repository `unittest` suite then ran with the existing Windows
`resource` portability shim and passed completely.

Server-side command classes:

```text
HOME/PWD/project/virtualenv preflight
exact staging and input SHA-256 verification
Python compile under the existing server virtualenv
nohup launch and exact PID/log/output monitoring
stage-process and gotsc absence checks
server-side large-bank comparative postprocessing
direct compact-file scp without archives
```

The audit expected and evaluated 32 contexts. It launched zero Ray/TSC tasks,
created zero plant trajectories, and made no controller or server-project
source change.

## Decision

Do not implement or launch R3c4 from this bank. Do not reinterpret the
result by relaxing the frozen coefficient or condition gates.

The next prospective work must discriminate between two remaining design
routes without running TSC:

1. quantify how much unvalidated response-amplitude extrapolation would be
   required to repair each failed context; and
2. test a richer response model only as a diagnostic if authenticated
   nonlinear terms can be formed.

Any later real identification campaign must be a new identity with newly
frozen amplitudes and schedules. It must independently validate the chosen
authority/model before any real closed-loop R3c4 campaign. BC, DAgger, and
bounded residual RL remain prohibited.
