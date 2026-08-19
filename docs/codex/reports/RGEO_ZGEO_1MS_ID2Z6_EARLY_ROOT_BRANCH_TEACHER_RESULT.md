# R_geo/Z_geo 1 ms ID-2Z6 early-root branch-teacher result

Date: 2026-08-19

## 1. Final classification

ID-2Z6 is final as
`ONE_MS_ID2Z6_EXECUTION_OR_INTERFACE_FAIL_STOP`.

This is an implementation/driver failure after authentic TSC work, not a
teacher-utility, action-basis, plant, controller, capture, recovery, waypoint,
or reachability result. The frozen three-round campaign did not finish and
its scientific gate was not evaluated. It must not be resumed or retried
under the ID-2Z6 or ID-2Z6R1 identity.

No model was fitted or updated. Calibration and holdout records read were
zero.

## 2. Evidence identity

```text
original implementation       39a2c3ac8440dff90eb673d83db36b8587edafe2
reporting-only resume          ce5cb4fe4d64682bfd6aadd63a2f3574bc3fd27a
failure finalizer              c7840b5592ca35cac2ec3b7eaf58ef6e4a84272e
independent-audit correction   6e3556bb240e4e76eb01e662d168b3975ae1c56c
```

Server run directory:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
rgeo_zgeo_1ms_id2z6_runs/20260819_39a2c3ac_v1
```

Tracked compact evidence:

```text
docs/codex/audits/rgeo_zgeo_1ms_id2z6_20260819_39a2c3ac_v1
```

The final primary result SHA-256 is
`6f9ebc89f9f0fb9f3666a397cdf960dfd134b3c133abcf93375aaf7b8ac6752b`.
The corrected independent raw audit SHA-256 is
`a98b9747eae86879a2e65bbf3b9e9c88e97d70d696d102acf25b2a04d66943b0`.
Every transferred compact/result/audit/log hash was checked against the
server before raw cleanup.

After this evidence and report were committed and pushed, the exact audited
remote `rollouts/` subtree (`29,484,012,604` filesystem bytes) and the exact
interrupted-run private workspace (`263,600,858` bytes) were irreversibly
removed under canonical-path, process and hash guards. Top-level compact,
metadata, audit and log files remain. Server free space after cleanup was
`141,796,622,336` bytes.

## 3. What executed

The original run passed its package, focused, complete one-ms and zero-TSC
static gates, then completed all five round-0 state-49 branches. A retired
descriptive-margin key caused a reporting exception only after those five
trajectories had finished and before round-1 selection.

The separately frozen reporting-only resume authenticated the complete
round-0 raw, recomputed the unchanged selection, and selected `f4`. It then
completed two round-1 branches (`hold4` and `b4`) and began `f4`. A second
driver defect omitted the run-specific `cfg.run_root`; the new raw was written
under the historical runner default instead of the ID-2Z6 run tree. The
exact owned processes were stopped, the generated directories were preserved
and moved back under the run, and no retry was attempted.

The final authenticated counters are:

```text
resets                                         8
advance attempts / plant-advance gotsc calls  486 / 486
verified successors                           485
complete rollouts                             7
partial rollouts                              1
retained states                               493
required raw artifacts                        2,465
required raw bytes                            29,034,211,532
inventory digest
  4d75fef0b3dc61cfcb3609cac87b3d6bf07745ae70ffd37637c28f2b7b498ef0
```

The partial `r1__f4` path contains three retained states, three attempted
issues/`gotsc` calls and two verified successors. It has zero fitting weight.

## 4. Finite round-0 evidence

All five round-0 branches completed and passed their exact prefix checks.
The frozen terminal worst-normalized scores were:

```text
hold4   4.407677637
b4      3.871057990
f4      3.676826525   selected
b2f2    3.849885839
f2b2    3.841901775
```

`f4` improved the matched-hold score by `0.730851112`; no arm satisfied the
six-state capture gate. This is valid finite state-49 development/selection
evidence. It is not a completed three-decision teacher result, and the two
complete round-1 branches do not make round 1 selectable because the sibling
matrix is incomplete.

## 5. Audit history

The first post-finalization independent audit is retained as a FAIL with the
single discrepancy `RECOMPUTE:prefix_checks`. Its raw reader compared the
state-directory `inputa` after the runner had rewritten it with the outgoing
issue against the online compact pre-issue artifact. This was a reporting
clock/lifecycle mismatch, not a physical prefix mismatch.

The corrected independent auditor uses the compact record for the pre-issue
causal checkpoint and independently authenticates the outgoing action from
raw. It reparsed the complete 493-state/2,465-file tree, reproduced the
inventory, counters, execution route and all available metrics, and passed
with no failures. The original failed audit remains preserved.

The primary flags `raw_integrity_passed=false` and
`execution_integrity_passed=false` because the frozen campaign is incomplete;
they do not contradict the corrected auditor's finding that the retained raw
tree is internally authentic and exactly classified.

## 6. Data role and successor rule

The five complete round-0 windows were prospectively declared development
windows and are retained as finite development/selection evidence. To avoid
mixing a consumed, interrupted resume identity into a successor fit, the two
complete round-1 paths and partial `r1__f4` path receive zero fitting and
selection weight in the successor stage. ID-2Z6 itself never reaches its
frozen minimum of fifteen complete windows and authorizes no model comparison.

A successor must use a new identity. It may bind the independently audited
round-0 result and fixed `f4` parent, then generate a fresh complete round-1
five-arm matrix, a fresh round-2 five-arm matrix and one zero-fit replay. It
must not rerun round 0, reuse the interrupted round-1 outcomes for selection,
or call the new run a resume. Before TSC it must include a server-tested
run-root isolation assertion proving that every raw state directory is created
only under the new output tree.

Only a complete successor teacher/data PASS may open a small-model comparison
or fresh replay/Recourse-L1 design. Another execution defect stops as an
implementation failure; a clean no-utility result closes the B/F/H route and
triggers the already recorded bounded action-basis/authority review.
