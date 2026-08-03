# Stage4.2R3c3T13S24D1R8 final forensic report

## Result

D1R8 is an immutable real-TSC action-schedule design FAIL, not a runtime,
restart, causality, raw-corruption, or plant-unreachability result. The exact
frozen route is:

```text
TEMPORAL_BASIS_SENTINEL_ACTION_MARGIN_FAIL_REDESIGN_REQUIRED
```

All 108 frozen specs produced complete raw JSON.GZ. Of them, 105 reached the
full horizon and three stopped structurally before the final task-step-18
cancel action was applied. The failed row was sequence 22 in all three cases.
It is the central negative of sequence 6 and requests temporal sign pattern
`-++-` for physical direction 2.

```text
strict raw / exact identity                              108 / 108
full-horizon success                                     105 / 108
structured action-schedule safe stops                      3 / 108
runtime or audit failures                                  0 / 108
initial visible plus 48-wire restart exact               108 / 108
causal / phase / calibration executed prefixes           108 / 108
authentic finite gotsc state prefixes                     108 / 108
issue attempts / passes                                   432 / 432
cancel attempts / complete gate passes                    432 / 429
failed actions applied / later plant advances                 0 / 0
forbidden controller-use traces                                  0
maximum executed current utilization                         0.392
maximum attempted cancellation increment              0.2818504004
```

D1R8 does not authorize a replacement identification campaign, MPC, expert
data, BC, DAgger, or RL. Its trajectories remain development/forensic-only.

## Code, package, and server identity

```text
local branch
  codex/stage4_2r3c3t13s24-sequential-transition

D1R8 design checkpoint
  ec3212b
implementation checkpoint
  640b519
execution package checkpoint
  ebfc9f0
structured-prefix reporting hotfix
  07ffb9f
reporting package checkpoint
  cfe6ece

execution package revision
  r42r3c3t13s24d1r8_temporal_basis_substitution_safety_sentinel_v1
reporting package revision
  r42r3c3t13s24d1r8_structured_prefix_reporting_hotfix_v1

execution PACKAGE_MANIFEST.json sha256
  4e5235e3fe2381cf581c531c6a1bd1dcb2109f7a1fd2d2b64cb143c27f6b5911
execution SHA256SUMS sha256
  1284a3bacd8ff568a70e9084eeae2d15499cee81ff6bf9ff02956dfb4be22ab7
reporting PACKAGE_MANIFEST.json sha256
  ed00a317b3eae06c972772bb00c31444689293575f5f6728a41da4c7602262d6
reporting SHA256SUMS sha256
  0a21a5be25ca46d90f68ba35cac854dae079b122dcf56ccd12f616abf6891409
```

The server execution package was staged at:

```text
/home/yangshen0711/tsc_software/
stage4_2r3c3t13s24d1r8_ebfc9f0
```

The reporting-only hotfix was staged at:

```text
/home/yangshen0711/tsc_software/
stage4_2r3c3t13s24d1r8_reporting_hotfix_cfe6ece
```

The authoritative run and stage directories are:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r8_runs/
stage4_2r3c3t13s24d1r8_temporal_basis_substitution_safety_sentinel_20260803_215303_ebfc9f0_v1/

stage4_2r3c3t13s24d1r8_temporal_basis_substitution_safety_sentinel/
```

## Pre-execution identity normalization

Read-only inspection before TSC found that the D1R7 candidate container was
already labeled D1R8, but every inner spec retained only the source `stage`
value `Stage4.2R3c3T13S24D1R2`. All controller, campaign, schedule, snapshot,
target, horizon, environment, blindness, and physical-action fields were
already exact.

The frozen design allowed a deterministic reversible bookkeeping-only
normalization. D1R8 therefore changed only the inner path `stage` and proved
an exact reverse comparison before Ray/TSC:

```text
source ordered spec digest
  62869a4a028ff177b9eb83e509e7436a5937882081739cc3e548901989f05619
normalized ordered spec digest
  c6aa13057a1032d9ba2b4e3830133bb8399e3a4e818213015327ad622972d14f
changed spec paths
  stage only
deep reverse equality
  true
```

This was an identity/bookkeeping repair before execution, not an action,
controller, task, target, gate, timing, or experimental-semantic change.

## Validation and execution

Every local Python command used the project virtual environment. The execution
package passed compile, strict JSON parsing, import closure, checksum checks,
focused tests, empty-directory deployment simulation, and the complete local
suite. The direct complete-suite invocation initially encountered 27 Windows
imports of Unix `resource`; rerunning with the repository's existing
`tests/conftest.py` compatibility shim passed 998/998. This was a local test
invocation/environment issue, not a D1R8 code or experiment failure.

```text
execution-package focused tests                         24 / 24
execution-package complete local tests                998 / 998
empty-directory declared / actual files              734 / 734
empty-directory focused / complete tests          24 / 24, 998 / 998
```

The reporting hotfix added direct partial-prefix tests and then passed:

```text
focused local tests                                    10 / 10
complete local tests                                  999 / 999
staging package focused tests                          25 / 25
staging complete tests                                999 / 999, skip 1
installed package focused tests                        25 / 25
installed complete tests                              999 / 999, skip 1
```

The server used only:

```text
/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python
```

The real run used the frozen Ray capacity: 96 actors for the first batch and
12 for the second. All 108 raw files completed naturally without restart or
resume. The complete rollout log is 148,297 bytes with SHA-256
`9d73c109a484471988afdc681eb3df0a2de116e0b8ce8c87dad75dfe4deed758`.

## Raw, snapshot, manifest, and log authentication

```text
expected / actual raw JSON.GZ                          108 / 108
raw total bytes                                         6468042
raw name-size-hash inventory digest
  8fd08fd0e8c6c216f4a98c3a6a113f0f6c29aea16dfae92f52cc857e2a801ec2
snapshot exact/pass                                      18 / 18
stage state / manifest / final route consistency              true
stage manifest sha256
  be36beea24709c00591b0301544b79d87f358d3796322f6514311ab73a0eb279
stage state sha256
  0fb985d5dfa031e88ca77690e6d7543a50ae2c8e71ad9edb8c9ac546b2034455
final result sha256
  40cb3889441daddd4a01245d5938df36c2514f473fb7f316a6e7aab7b7b2a777
```

The original independent raw audit is 129,527 bytes with SHA-256
`f196375bc1d07f5a1e8c87f3f1b088b03235a423c9a35c2c459f63d3fed62b8a`.
The reporting-hotfix audit is 199,474 bytes with SHA-256
`5eb46eff8affb08969c437ebc56becb70318090e557ab063dbd7b0375d995687`.
Only this compact audit was downloaded; all JSON.GZ and large trajectory trees
remain on the server.

## Three structured stops

All three stops occurred at sequence index 22, slot 3, task step 18 after all
eight calibration events, four issue events, and the first three cancellation
events had passed and advanced the authentic plant. The attempted final
cancellation requested `[0.29,0.29,-0.29,-0.29]` and exactly restored the
stored Card15 center, but failed both the preregistered 0.24 online margin and
the original 0.25 incremental-action cap:

```text
pair/history                              attempted increment    current use
p5_q2_a0p750_gap4_settle4 / plus_first        0.2818504004        0.38365
p9_q1_a0p900_gap4_settle4 / plus_first        0.2568135885        0.37110
p9_q1_a0p900_gap4_settle4 / minus_first       0.2561834333        0.37105
```

Exact fields, exact zero target-jump net, total action, current utilization,
no saturation, and no clipping all passed. The failure candidate was recorded
but not applied. Every failed raw has 19 authentic state rows and 18 executed
trace rows; no state-19 plant advance followed the rejected action.

This asymmetry is physical/controller-state dependent: sequence 6 (`+--+`)
passed 18/18, while its exact requested central negative, sequence 22
(`-++-`), passed only 15/18. D1R7's static replay evaluated each action around
frozen catalog centers and therefore could not certify the intervention from
the evolved sequential state.

## Reporting bug and corrected interpretation

The inherited R3b full-control helper immediately returned false restart and
causality fields whenever top-level `success=false`. The original D1R8
independent aggregator therefore inspected restart/causality/calibration only
for the 105 full-horizon successes. In addition, D1R8's structured exception
writer did not emit `hidden_history_control_summary`, although it preserved
the complete executed prefix.

Hotfix `07ffb9f` reads the immutable raw directly. It compares the initial
R/Z/Ip, all 14 coil currents, and all 48 wire currents to the authenticated
generated state; verifies every returned/recorded action, online causal trace,
phase, calibration, forbidden-use flag, finite `gotsc` state, and abnormal
flag in the executed prefix; and explicitly reports the missing summary flag.

It changes no raw, source fingerprint, controller, gate, state, final result,
manifest, route, or experiment identity, and it ran no TSC. The corrected
interpretation is:

```text
initial authentic plant restart exact                    108 / 108
executed causal/phase/calibration prefix                  108 / 108
fresh actor/process summary present                       105 / 108
fresh actor/process summary absent in exception branch      3 / 108
```

Thus `restart_pass_count=105` remains the count evaluable through the old
success-only combined helper. It is not evidence of three restart failures.
The authenticated package and rollout architecture created one `max_restarts=0`
Ray actor and one local TSC worker per spec, but the missing raw summary field
is reported honestly rather than retroactively fabricated.

## Formal tracking and design scope

The immutable 250/270 ms arrival deadlines and 350/370 ms hold endpoints were
not changed. Twenty-two of the 105 complete trajectories passed the formal
tracking diagnostic; this number is diagnostic only because D1R8 is an
identification safety sentinel, not a preregistered control acceptance test.
The three safe stops did not reach their formal endpoints and are not formal
tracking failures.

D1R8 tested the six D1R7 changed/new rows `2,6,10,14,22,23`. Exact vector
matching across S24, D1R2, and D1R8 shows that D1R7 row 18 equals the already
successful S24 row 17; it is not the unsafe D1R2/D1R6 row 18 despite sharing
the same index. Sequence indices alone are therefore not valid cross-matrix
identity.

The same exact-vector audit found a different coverage limitation: D1R7 rows
`3,7,11,15,20,21`, all using the geometry-restored direction-3 amplitude
`0.36`, have no exact real sequential raw. Their corresponding S24 rows used
amplitude `0.50`; D1R7 proved only static Card15/action geometry at `0.36`.
Thus even a hypothetical 108/108 D1R8 pass would not by itself dynamically
certify all 24 exact D1R7 matrix rows. The frozen route authorized only a
later design, so no campaign was wrongly executed, but the next design must
cover the new row-22 failure and the six exact untested `0.36` rows.

## Scientific classification and next action

- Runtime/environment/deployment error in the real run: none.
- Packaging/import error in the accepted run: none.
- Raw/snapshot/state corruption: none.
- Statistics/reporting error: the success-only partial-prefix aggregation and
  omitted exception summary; corrected without changing experiment semantics.
- Design defect: the static-center preflight did not bound evolved sequential
  cancellation intervention, and the sentinel left six exact `0.36` matrix
  rows with static-only rather than authentic sequential evidence.
- Real control/plant conclusion: authentic restart and causal executed prefixes
  are exact; three final cancellation candidates genuinely exceed unchanged
  safety gates. This is not evidence of plant unreachability or robust control.
- Formal control conclusion: not an acceptance result; independent long hold
  remains untested.

D1R8 is frozen and may not resume. The next action is a zero-new-TSC exhaustive
global schedule/central-row redesign using all S24, D1R2, D1R6, D1R7, and D1R8
evidence. It must match schedules by exact action vector rather than row index,
reject every schedule contradicted by existing authentic raw, preserve central
symmetry/rank/condition/Card15/action/current/timing gates, and freeze only the
smallest new-identity real-TSC sentinel needed for unseen evolved schedules.
A full replacement campaign remains unauthorized.
