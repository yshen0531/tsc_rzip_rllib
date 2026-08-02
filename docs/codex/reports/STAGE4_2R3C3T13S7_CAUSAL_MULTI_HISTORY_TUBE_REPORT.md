# Stage4.2R3c3T13S7 causal multi-history tube report

## Result and classification

T13S7 completed its frozen zero-new-TSC leave-one-context-out audit over all
120 immutable S1/S5 raw files. Its exact preregistered route is:

```text
CAUSAL_MULTI_HYPOTHESIS_TUBE_INSUFFICIENT_REDESIGN
```

The route is final, but source and raw timing forensics prove that its primary
failure is an audit-design error: T13S7 incorrectly assigned the S5
post-queue `issue+1` effect contract to S1, whose probe is inserted before
the inherited delay queue. T13S7 therefore does not test the intended
cross-campaign multi-hypothesis compatibility question cleanly.

This is not a runtime, deployment, raw, snapshot, restart, causality,
statistics, reporting, real-MPC, or global-reachability failure.

## Exact identities and evidence

```text
design checkpoint
  a1143c9  Finalize T13S6 and preregister T13S7
implementation checkpoint
  14ea327  Implement T13S7 causal multi-history audit
local branch
  codex/stage4_2r3c3t13s1-transition-sentinel

staging
  /home/yangshen0711/tsc_software/stage4_2r3c3t13s7_14ea327
server audit
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s7_audits/
  stage4_2r3c3t13s7_causal_multi_history_20260802_14ea327/
  stage4_2r3c3t13s7_causal_multi_history_tube_audit.json
  SHA-256
  b62d7d49f2ce2ac47fa1245884a764a84f5372364f8e7f5f329867b50e1c101c

compact forensic SHA-256
  8a67ed6c1306bb3fcacbae46764be37c24d35dd5cdd9d8f2ee398ac3ac68066c
effect-contract forensic SHA-256
  c78bd97c5c60c526d609ea5da15547abe5cb73927552086573f4a856d12e3f4a
server log SHA-256
  bb89d2731f8f41f48921912d5463ed4260fe2f89b98f6018d96e1856afce3982
```

The four staging file hashes matched the local implementation. Server
focused tests passed 5/5 and the complete local repository suite passed
693/693 before execution. No matching TSC or `gotsc` process existed before
or after the audit.

## Frozen audit result

```text
S1 raw authenticated                                  52 / 52
S5 raw authenticated                                  68 / 68
combined contexts / baselines                          8 / 8
combined signed probes                                    112
trace identity                                       120 / 120
corrected extraction                                 112 / 112
pre-effect causality                                 112 / 112
forbidden feature/trace inputs                               0
local model rank                                      12 / 16
local tube inside cap                                 16 / 16
maximum tube/cap ratio                              0.202075
held-out predictions                                     112
supported hypotheses                                  24 / 112
componentwise containment                             24 / 112
relative-error pass                                   24 / 112
exact feature/input collision groups                         4
disjoint exact causal aliases                                0
```

The finite maximum relative error `0.0` applies only to the 24 supported
rows. The other 88 rows were correctly rejected before prediction because
the selected training maps did not support their measured input. It is not a
112-row accuracy statistic.

All 24 apparent passes are the S1 hard/delay-2 rows. Under the erroneous
`issue+1` extraction those rows have zero odd measured input and zero odd
response, while all four S1 hard local maps have rank zero. Their success is
vacuous and cannot support a transition model claim.

The unsupported rows are exactly:

```text
all S1 easy signed rows                                24 / 24
all S5 easy signed rows                                32 / 32
all S5 hard signed rows                                32 / 32
total                                                  88 / 88
```

## Source and raw effect-contract forensic

S1 source wraps `solve_delay_aware_physical_correction` before calling the
inherited R3c1 controller. It modifies the first correction entering the
software delay queue, and its constructor explicitly validates physical
effects at:

```text
issue_step + action_delay_steps + 1
```

S5 source instead calls the complete inherited action first and replaces the
already post-queue final Card15 action. Its physical effect is therefore at:

```text
issue_step + 1
```

Independent odd-current timing from all signed raw groups found:

```text
S1 campaign-contract first-effect match                 24 / 24
S1 post-queue-immediate match                           12 / 24
S1 delay-2 campaign-contract match                      12 / 12
S1 delay-2 post-queue-immediate match                    0 / 12

S5 post-queue-immediate match                           32 / 32
S5 delay-2 post-queue-immediate match                   16 / 16
```

This is a source-proven and raw-proven campaign-specific semantic difference,
not an inferred plant delay change.

## Error classification and next action

```text
runtime/environment error                              no
packaging/import/deployment error                      no
raw/snapshot corruption                               no
restart or controller causality failure                no
statistics/reporting error                             no
T13S7 cross-campaign effect-contract design error      yes
multi-hypothesis scientific compatibility tested       no, confounded
real controller/MPC executed                           no
global plant unreachability shown                      no
```

T13S7 may not be rewritten or rerun under the same identity. The next stage
is the separately frozen T13S7R1 audit. It preserves the exact T13S7 feature,
LOCO, neighbor, input-support, tube, collision, and acceptance rules and
changes only the campaign-specific raw effect extractor: S1 uses its
queue-aware declared states; S5 uses its post-queue immediate states.

Neither T13S7 nor T13S7R1 authorizes a controller, MPC, expert data, BC,
DAgger, or bounded residual RL. Formal timing remains unchanged and all S1/S5
probe trajectories remain forbidden from expert datasets.
