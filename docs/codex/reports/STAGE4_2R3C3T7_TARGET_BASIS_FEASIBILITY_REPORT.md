# Stage4.2R3c3T7 target-basis feasibility report

Date: 2026-07-31 (Asia/Shanghai)

## Result

T7 repaired the response-matrix representation but did not repair any
failed formal context:

```text
authenticated contexts                                32/32
fixed selected basis count                                8
rank eight / condition <= 25                         32/32
maximum condition                                20.5173470
baseline formal passes                              16/32
optimistic selected-basis formal passes              16/32
failed baseline contexts repaired                     0/16
baseline-pass regressions                             0/16
all preregistered gates pass                            no
next restart MPC implementation authorized              no
real TSC executed                                       no
```

This is a pre-execution linear-authority/design failure. It is not a
runtime, deployment, raw, restart, plant or real closed-loop controller
failure.

## Frozen identity

Local implementation and design commit:

```text
d530ed5  feat(stage4.2r3c3t7): freeze target-basis feasibility audit
```

Fixed global basis:

```text
T3 basis indices                              0, 1, 2, 3, 7
T6 probes                    r17_target_action_residual
                              matched_visible_target_equal_pc1
                              matched_visible_target_equal_pc2
```

The same subset is used for all 32 contexts. Pair and hidden-history labels
cannot influence selection. The tool independently reproduced the
exhaustive 8-of-11 selection:

```text
selected full indices                    0,1,2,3,7,8,9,10
rank-eight/condition pass count                         32
mean condition                                   12.162358
worst condition                                  20.517347
```

The candidate had already been exposed by post-T6 development forensics.
The preregistered, previously unobserved T7 result was formal feasibility
under the unchanged `[-1,1]` coefficient and timing contract.

## Validation and execution

Local:

```text
focused T7 tests                                      3/3
full suite                                         580/580
empty-directory suite                             580/580
package closure                                    195/195
```

Server:

```text
package/checksum and shell syntax                      PASS
focused T6 / T7 tests                              8/8, 3/3
full suite                                         580/580
validation log SHA-256
77a03de28c7034d3fa23ee28dd5e648dcc5dc39195cd44020f1627e370790569
```

Remote output:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t7_basis_feasibility/
stage4_2r3c3t7_basis_feasibility_20260731_d530ed5
```

Remote log:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
stage4_2r3c3t7_basis_feasibility_20260731_d530ed5.log
```

Output hashes:

```text
manifest
e69980452e756686c43ce37b6f3a471b37d6c804b3a6109fa22ea5905921ed74

audit bank
e18f5cfc7fb510f32f0f35128274e108f224c1c4a2afec262ec6fb8d91cf0d61

controller bank
fef1eb299cede180c1f43d8713b3174aa9afd8724ea6af4509b06ad5d92febd8

feasibility
d4dbcd4a114eec10110432d6bf4337182bcb805b27ab83d689a9e216a052ed30

execution log
6f49fe176b3b089698d7ed3b0d4c34315b3ff4d645148b3c01ca36ddef7b1a5b
```

The 5.1 MB audit bank and 3.2 MB controller bank remain on the server. Only
the 21.9 KB feasibility result, manifest and logs were downloaded to:

```text
docs/codex/audits/
stage4_2r3c3t7_basis_feasibility_20260731_d530ed5/
```

The manifest exactly covers all three primary outputs. The controller sample
tree contains no pair/history/source/raw/result/wire/pass/fail/audit data
keys. Its only metadata key containing the word `history` is the root-level
declaration `hidden_history_labels_present=false`.

## Formal-feasibility forensics

The 16 remaining margins are:

```text
best                                           -0.04852195
median                                         -0.13363485
mean                                           -0.16598694
worst                                          -0.34744797
```

Active constraints:

```text
position                                               12
post-arrival speed                                      4
```

All 16 failed contexts are worse than their T3 eight-basis optimistic
solution:

```text
improved / unchanged / worsened                   0 / 0 / 16
mean signed-margin change                         -0.0256281
```

This tradeoff is scientifically useful: removing redundant old columns
fixes conditioning, but the replacement target-residual columns do not
provide enough bounded formal authority at their measured amplitudes.

Coefficient saturation across the 16 failed contexts:

```text
T3 basis 0 / 1 / 2 / 3 / 7             16, 16, 16, 16, 16
R17 target-action residual                          15/16
matched-visible target PC1                         16/16
matched-visible target PC2                         16/16
```

The result is therefore not explained by an interior optimum or an unused
coefficient direction. Under the authenticated odd linear model, the
bounded envelope is exhausted.

Failure strata remain:

```text
offset target / nominal target                      12 / 4
delay 2 weak slew / delay 0 normal slew             12 / 4
minus-first / plus-first                              8 / 8
```

## Error classification

```text
runtime/environment error                                  no
deployment/import error                                    no
input hash or raw corruption                               no
statistics/reporting error                                 no
plant restart or TSC execution                        not run
matrix-conditioning design repaired                       yes
bounded optimistic linear authority failure               yes
real closed-loop controller failure                    not run
R3c4 implementation authorized                             no
```

## Next action

Do not implement or run R3c4 from this bank. The next route discriminator
must quantify whether the unused measured-current envelope can plausibly
close the T7 margins for the newly identified target directions. Such an
offline extrapolation is diagnostic only and cannot authorize control.

If required scale exceeds the current limit, or offset-target contexts
remain failed, the next real identification identity must add genuinely new
target-relevant temporal/actuator authority and measure combined-action
nonlinearity; it must not repeat the old amplitude-only or separable-even
audits. Formal timing remains unchanged.

No restart MPC expert, independent robustness, continuous-parameter
robustness, noise tolerance, disturbance recovery or long hold is validated.
BC, DAgger and bounded residual RL remain prohibited.
