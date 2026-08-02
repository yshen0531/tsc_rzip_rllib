# Stage4.2R3c3T13S17 final forensic report

## Outcome

Stage4.2R3c3T13S17 is frozen as:

```text
CAUSAL_MULTI_DRIFT_BELIEF_PREFLIGHT_FAIL_ROBUST_OBSERVER_REDESIGN
```

The fixed three-hypothesis causal belief contained all 128 authentic S16
development responses, but none of its 128 hulls satisfied all unchanged
halfwidth caps.  This is a robust-observer residual-set design failure.  It
is not a runtime, deployment, restart, raw, statistics, reporting, real-MPC,
or plant-reachability failure.

S17 ran no controller, optimizer, Ray, `gotsc`, TSC, plant step, or snapshot
creation.  Its 144 source raw files are the already consumed S16 development
evidence and remain on the server.  S17 trajectories remain forbidden from
expert datasets.

## Exact execution identity

```text
branch
  codex/stage4_2r3c3t13s16-whitened-basis

design commit
  be9c316 Freeze S16 result and S17 belief preflight

implementation commit
  65e00c3 Implement S17 causal multi-drift belief audit

package-verification hotfix
  0f9ef6b Fix S17 package JSON validation scope

package revision
  r42r3c3t13s17_causal_multi_drift_belief_preflight_v1

remote output
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s17_audits/
  stage4_2r3c3t13s17_causal_multi_drift_belief_preflight_20260803_0f9ef6b

execution log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t13s17_causal_multi_drift_belief_preflight_20260803_0f9ef6b.log
```

Relevant deployed hashes were:

```text
PACKAGE_MANIFEST.json
  ae651286328dc66c0278cb37c055b97d85b6e16a4b5a376afe6f66678c339e35
SHA256SUMS
  50b114fb162eb92638e964306699acb255aa0904a96dc0b96519fa0bb2300d1a
S17 config
  43df32b8f5cd27a3b33da432c27fb19e8972e169687549520b0167ae912c77ff
S17 diagnostic module
  11457ade110a13aa1dc58326fbb00ee049f4c2e0672bc96a3c7ad6f0313f019b
S17 verify-package script after hotfix
  69410ba297033b7eb1b20a7ec90a9085b1e03a549150a3e2e047d3a1f77a2c8f
```

## Package and execution validation

Local validation after the verification-only hotfix passed:

```text
declared checksums                         379 / 379
declared JSON                               65 / 65
Python compileall                              PASS
S17 self-test                                  PASS
focused unit tests                          11 / 11
```

The Windows host has no usable Linux `bash`; the attempted local shell run
reached the uninstalled WSL launcher and is recorded as not run locally.
The actual server Linux checks closed this limitation:

```text
bash -n declared scripts                       PASS
installed package checksums                 379 / 379
declared JSON                               65 / 65
server self-test                               PASS
server focused tests                         11 / 11
server complete suite               802 tests, 1 skip
```

Server validation logs are:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
stage4_2r3c3t13s17_server_verify_hotfix_20260803_0f9ef6b.log

/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
stage4_2r3c3t13s17_full_tests_20260803_0f9ef6b.log
```

The first two installed verification attempts failed because the original
script recursively parsed every `*.json` under the long-lived remote project.
It encountered historical `.codex_tmp/s14_kernel_sweep.json`, whose contents
are an S14 text log.  The hotfix restricts JSON parsing to the 379-file
manifest inventory and reports a failing path.  No controller, model,
experimental identity, source hash, gate, or physical action changed.  This
was a package-validation/reporting-scope bug, not an experiment error.

The SSH channel repeatedly reset on larger direct packets.  All required
larger text transfers therefore used 512-byte direct chunks and server-side
SHA-256 reassembly.  Small commands continued to connect.  This was a
transfer-channel limitation, not a server or scientific failure.

## Source authentication and inventory

S17 authenticated the exact S16 source recorded in the S16 report:

```text
required compact source files               12 / 12
source snapshots                            16 / 16
source raw parse                            144 / 144
source raw bytes                            8,188,964
source raw inventory digest
  b0bf9c03b94cd353b3ccb68b0de318c46285a4805acfb0c25016704f79057668
new raw files                                         0
new TSC or plant steps                                0
```

The final S17 compact inventory and SHA-256 hashes are:

```text
source_authentication.json
  b02d721f5df86cad77c019df2495bf869d58527e1a0e28b5d93dd43ae1e91d5c
causal_belief_artifact.json
  d8c8ee8f0c3f2e80cb1642c7f6400f47d5280e47459361dfa274421c37fdca76
final_result.json
  98afee17ff682326853e7caa708264186c87ccf88bec92ddf2cd3275855b9a69
server_independent_postprocess.json
  a59355266f94f2013b07a5b58c0857ee3925e9ebcd6c1147a6e2affd4f728326
stage4_2r3c3t13s17_state.json
  141bbc5f6ba670b9a560d02c99830eb02c2c67540fcc2c74f944c5cae88987ef
server_post_failure_forensics.json
  769fc564ccb1dc61d915a566e1369b792e0694a19804e63f6081086c3cdf752b
server_s18_retrospective_architecture_screen.json
  e62739dfb2d6c701c956afcd15260892cc0422431de5c7c4a70fe95b2f23b028
```

The last two files are explicitly post-failure development forensics.  They
do not alter S17's preregistered result and are not validation evidence.

## Frozen gates and exact result

```text
causal response rows                             128 / 128
fixed H1/H2/H3 hypothesis rows                   384 / 384
maximum design condition                         3.1980986512
source response exact match                      128 / 128
belief frozen before state-11 outcome            128 / 128
forbidden predictor inputs                                0
response inside three-hypothesis hull            128 / 128
belief halfwidth cap                               0 / 128
all gates jointly                                  0 / 128
reported summary exact on independent recompute          yes
```

The maximum hull halfwidth was:

```text
R       0.0021893899 m
Z       0.0035035150 m
vR      0.1402725944 m/s
vZ      0.1148451016 m/s
Ip    569.3096776542 A
```

The unchanged caps were `(0.003 m, 0.003 m, 0.010 m/s, 0.010
m/s, 1000 A)`.  Per-component cap counts were `(128, 124, 0, 16, 128)`.
The failure is therefore dominated by velocity uncertainty, with four Z
halfwidth failures as well.

## Failure attribution

Card15 coordinate uncertainty is not the limiting term.  Across the three
hypotheses its maximum propagated input contribution stayed below about
`3.24e-8 m`, `8.30e-8 m`, `2.87e-6 m/s`, and `0.0151 A`.  The regression
residual term produced essentially the full hull width.

The fixed hypotheses separately gave:

```text
degree    contained    cap pass    joint    max vR radius    max vZ radius
1           128/128       0/128    0/128      0.1402726        0.1148451
2           122/128      18/128   18/128      0.0531570        0.0412730
3            85/128      44/128   21/128      0.0335269        0.0367394
```

The hull exceeded the maximum individual-hypothesis radius by zero at the
median in every component.  Hypothesis-center half-spans were much smaller
than residual radii.  Selecting a degree after seeing state 11 or taking the
three-way interval intersection would violate the frozen contract and would
still not solve the problem: only 81/128 actual responses lay in the
intersection, and an oracle choice of a contained, cap-compliant degree
existed for only 31/128 rows.

Thus S17 does not support deleting H1, selecting H2/H3 from current-run
outcomes, weakening caps, or entering MPC with the existing belief.  It
supports replacing the per-trajectory worst-residual tube with a shared
causal observer whose residual set is calibrated on whole-pair data.

## Post-failure route screen

A retrospective, non-validating eight-fold whole-pair screen used only the
causal degree-three point prediction and the four-dimensional issued-action
coordinate as nine model inputs.  Pair/history labels were split metadata,
not predictor inputs.  Each outer fold used seven training pairs; ridge was
selected by inner whole-pair OOF error, and its componentwise inner OOF
maximum residual defined the unexpanded tube.

The point predictor's outer-fold maximum errors were approximately
`(2.73e-7 m, 4.47e-7 m, 2.73e-5 m/s, 4.47e-5 m/s, 2.11 A)`.  The unexpanded
tube contained 125/128 rows.  The largest required retrospective uniform
expansion was `1.30124665`.  A fixed 4x tube contained 128/128 and stayed
inside all caps, with maximum halfwidth
`(1.78e-6 m, 1.92e-6 m, 1.78e-4 m/s, 1.92e-4 m/s, 10.495 A)`.

This screen was run after S17 failed and saw consumed outcomes.  It is only
architecture-selection evidence.  It cannot validate an observer or
authorize MPC.  It justifies the separately frozen S18 development preflight
and, only after an S18 pass, a new prospectively split campaign.

## Error taxonomy and scientific conclusion

```text
runtime/environment error                         none
packaging/deployment error                        none in final package
verification/reporting bug                        one, fixed before execution
raw/snapshot/restart corruption                   none
statistics/final reporting error                  none
observer/uncertainty-set design failure           yes
real closed-loop MPC conclusion                   none; no MPC ran
global reachability conclusion                    none
```

The immutable 250/270 ms arrival and 350/370 ms hold timing is unchanged.
Restart, hidden-history, continuous actuator/model variation, sensing noise,
disturbance recovery, and independent long hold remain prerequisites before
expert-data collection or bounded residual RL.

## Next action

Stage4.2R3c3T13S18 is a zero-new-TSC development preflight of the fixed
nine-feature pooled causal observer and fixed 4x whole-pair OOF tube.  It must
propagate causal current-run Card15 uncertainty, enforce per-fold held-out
outcome access, and independently recompute all gates.  An S18 pass can
authorize only a separately preregistered new training/calibration/fresh-
holdout campaign.  An S18 failure returns to excitation/observer redesign.

