# Stage4.2R3c3T13S24D1R14R8R14 forensic report

Finalized on 2026-08-08 Asia/Shanghai from the accepted server raw, compact
server-side postprocessing, exact deployed source, and structurally independent
recomputation. Chat summaries are not evidence for this report.

## 1. Final classification

```text
route
  CUMULATIVE_MULTIDIRECTION_ATLAS_AUTHORITY_INSUFFICIENT_SEQUENCE_BASIS_REDESIGN_REQUIRED

integrity gate       PASS
scientific gate      FAIL
real TSC executed    true
new raw              112
formal repairs       0/10 failed baselines
held oracle          6/16
```

R8R14 is a clean finite cumulative multidirection sequence-authority design
failure. Every new trajectory executed through the authentic restart boundary,
and all runtime, prefix, calibration, Card15, action, current, causality,
finite-state, raw, and reporting gates passed. None of the eight measured
constant-direction/sign cumulative staircases repaired any of the ten failed
R8R7 baselines.

This is not a runtime, deployment, source-authentication, restart, causality,
raw-corruption, reporting, formal-evaluator, safety, controller-construction,
plant, real-MPC, Gate A, or global-reachability failure. The identity is
immutable and may not be resumed, enlarged, or tuned. Its route requires a new
sequence basis under a new prospectively frozen identity.

## 2. Frozen identity and package

```text
design checkpoint          d2dbebc
implementation checkpoint  d737000
package checkpoint         9874068
design SHA-256
  06360433fd33fd8706453e145eeadca7e37fa80f4e99193cf779e62ab3af4f0f

PACKAGE_MANIFEST.json
  91489 bytes
  f8cd0cfba43a11b1fd693f0068fcde767686445ba016e00d9a7b7ae053c518f9
SHA256SUMS
  132439 bytes / 1053 declared paths / LF only
  1ddd4b41126e43dedee3b4d5565f01d5b4a809832859b064f99865cffab29efa
```

The package was built by direct-copying all 1,053 declared files into a new
empty repository-local directory and then adding the manifest and checksums,
for 1,055 files before validation caches. It was transferred with `scp -r`;
no archive was created or extracted. The existing project/server virtual
environments were used exclusively.

Exact deployed source hashes were:

```text
config       769ec363f13ffc70c0189479bb0af04f5da5f3d1215550a27028573802763ba7
primary      fc35d438aa1418b9adadf6a93d5852e8119ddd29dcbfa2e995a393377a4c6caf
independent  d4be91ae12a56d10cbc1edcf03c7172fe743356487948783fdbe6b84b44c589f
launcher     d25c8effc4f4315025712c195a1976357ed659af5800a3eb0397ff6ee8598ff6
```

## 3. Validation evidence

After loading the existing Windows `resource` shim, the project virtual
environment passed compilation, focused `10/10`, and full `1279/1279` tests.
The empty direct-copy package passed all 1,053 hashes, compilation, focused
`10/10`, and full `1279/1279`, with one expected isolated-evidence skip.

The existing server virtual environment passed in both staging and the
installed project:

```text
declared hashes       1053/1053
bash -n               PASS
compileall            PASS
focused unittest      10/10
full unittest         1279/1279, one expected skip
```

The first staging log-capture invocation completed every validation and
printed `R8R14_STAGING_VALIDATION_OK`, but Windows PowerShell wrapped unittest's
stderr progress dots as `NativeCommandError` and returned a local failure
status. An unchanged retry merged remote stderr before SSH and passed. This
was a log-capture invocation error, not a package or test failure.

## 4. Exact server run and immutable evidence

```text
run root
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r14r8r14_runs/
  stage4_2r3c3t13s24d1r14r8r14_cumulative_multidirection_staircase_authority_identification_20260808_9874068_v1

stage directory
  stage4_2r3c3t13s24d1r14r8r14_cumulative_multidirection_staircase_authority_identification
```

Accepted hashes are:

```text
offline primary       1eeab03c2f660cb171b87a311cffc7f1c5f4f210ab0c346e8c75eb6e4269d0eb
offline independent   d2642c5b87380350cd919807fcb2887777bab408dbeb9dde1286263659c3de50
safety primary        712f447edc3a4df61b392881047088c5ed5378e9f02a1f6a427d8444f3446a68
safety independent    a2bc8cc8603b9a316a65bfeeac93cad28f7747780f78242d387ab9f0202e8d8b
qualification primary 5616878e54d05e239c9f93aee2a678a0df13633fed45ba84700fdc3dce1f0fb1
qualification independent
                      34a407e6e1fd25ad87675b636f1e1d92d498eeedbe6845e18cca878f79263d18
primary summary       a9a9ee3e6d1ffeec6acf0675176e1c07de8b5220c36754afaa14567689cf33e3
final independent     5ab92427dfea3a3a492373df2fbe14b8bba7bcc4eb20b4ed018879a8ff68f5a5
final report          da8420de6520e8f5fba14a9acf0489a89f7f2e1b9c2f613ebb91ef6e0b011b61
stage manifest        ce980faf285b431910672cd819ea3e3b8da35d8f91507295616fda1a6df7a7f3
stage state           27a2d6001c920aa3149c86a3bf6f52009acd42cf78bf5ac68500f6b3441b1eb3
compact evidence      99af9763a0a468dc6677edf24211e7b57b1c6b5a17c023d1d26a32358bf3dcfd
```

The first final-evidence postprocessing invocation had an SSH quoting error in
an inline f-string and wrote no compact result. The unchanged retry strictly
parsed all raw and created only the new compact evidence file. This was a
postprocessing invocation error, not a raw or scientific failure.

Only eight compact JSON files, totaling 79,262 bytes, were downloaded. All raw
remains on the server. The downloaded files reproduce their server hashes.

## 5. Offline, execution, and raw integrity

Primary and independent offline construction agreed exactly:

```text
specifications                         112/112
exact cumulative issues                448/448
exact stored-target refreshes        2464/2464
maximum issue increment          0.14074074074074103
maximum refresh increment        0.0000037037037048793097
maximum predicted current use     0.39270000000000005
real TSC before dual preflight                     0
```

The safety partition completed and independently authenticated before the
qualification partition was authorized:

```text
                                      safety        qualification       total
raw count                                  28                   84         112
raw bytes                              913832              2757127     3670959
raw digest                         8fd9e0e5...          5bd7e233...          -
runtime/full horizon/prefix             28/28                84/84     112/112
calibration/event/target chain          28/28                84/84     112/112
issues                                    112                  336         448
forbidden trace rows                        0                    0           0
```

All 112 trajectories were finite and completed the frozen horizon. The
maximum measured current utilization was `0.3927`; the rejected-action and
safe-stop paths were not needed. No R8 or R8R1 trajectory was rerun, and no
new snapshot was created.

## 6. Formal outcome

The unchanged evaluator reproduced every existing formal metric exactly; the
maximum signed-margin difference was zero. Baseline and reused R8R12 counts
were both `6/16`. The seven new candidate families produced 39 formal-pass
trajectories in total, but no family repaired a failed baseline:

```text
direction  sign  source  formal  repairs  baseline regressions
0          -     R8R14   5/16    0/10     1/6
0          +     R8R14   6/16    0/10     0/6
1          -     R8R14   6/16    0/10     0/6
1          +     R8R14   5/16    0/10     1/6
2          -     R8R14   6/16    0/10     0/6
2          +     R8R12   6/16    0/10     0/6
3          -     R8R14   5/16    0/10     1/6
3          +     R8R14   6/16    0/10     0/6
```

Across the ten failed baselines, the best measured-candidate minimum-margin
gain was:

```text
minimum  0.025541733333334093
median   0.08895878160707882
maximum  0.1364830983921772
```

The best candidate was direction-2 positive in six failed contexts and
direction-1 negative in four failed contexts. Every best candidate still had
a negative formal margin. Consequently repairs were `0/10`, the do-nothing-
safe held oracle remained `6/16`, and the frozen `>=1/10` / `>=7/16` gate
failed. Primary and independent candidate summaries, numerics, route, and
gate agree exactly.

## 7. Boundary after R8R14

R8R14 rules out only the eight frozen constant-direction/sign cumulative
staircases over the finite 16-context envelope. It does not rule out a
time-varying mixed-direction sequence, a causal selector, MPC, or bounded
learning residual, and it is not evidence of global plant unreachability.

The contrast between direction-2-positive dominance in six failed contexts
and direction-1-negative dominance in four supports a new prospectively
frozen temporal switching basis. Any such campaign must retain the exact
restart, visible-state causality, Card15/action/current/saturation, safe-stop,
formal timing, two-phase, independent-audit, and learning-prohibition
contracts. All R8-family trajectories remain forbidden from expert, BC,
DAgger, and RL data. Gate A remains blocked.
