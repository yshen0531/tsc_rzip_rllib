# Stage4.2R3c3T13S24D1R14R7R2 forensic report

## Result

Stage4.2R3c3T13S24D1R14R7R2 completed its frozen zero-new-TSC
action-conditioned full-history kernel audit. Both implementations
authenticated all 320 immutable source raw files, reconstructed the same 304
matched-baseline responses, selected the same nested whole-pair candidates,
and agreed numerically within the preregistered tolerance.

The result is a clean response-center model-design failure:

```text
response rows / all-gate passes                         304 / 236
finite / point-error passes                        304 / 304 each
relative-L2 / cosine / peak-ratio passes          253 / 247 / 267
tube cap                                                     PASS
worst relative L2                                    1.5695004725
minimum cosine                                       0.2450755612
peak-ratio range                          0.2516766914--2.3254004095
predicted signal                                           304 / 304
canonical rank four / condition <= 20                       64 / 64
operational rank four / condition <= 20                     64 / 64
maximum canonical / operational condition        12.2257239 / 12.1661552
new raw / controller / Ray / gotsc / TSC / plant steps      all zero
route
  ACTION_CONDITIONED_FULL_HISTORY_MODEL_FAIL_NEW_IDENTIFICATION_REQUIRED
```

This is not a runtime, environment, packaging, deployment, source
authentication, raw/snapshot corruption, statistics, reporting, restart,
closed-loop control, plant-unreachability, or real-MPC result.

## Exact code and deployment identity

```text
local branch
  codex/stage4_2r3c3t13s24-sequential-transition
prospective design checkpoint                              5d35db2
implementation checkpoint                                  bcde159
package checkpoint                                         995d81c
design SHA-256
  32d0a5d123b70f9565cd27534e576eb63a6688bb0f6021755746b2f1e98dfdc5
PACKAGE_MANIFEST.json SHA-256
  cd835321f3df8f0636bf72ace28e56a1c4962ffe3f34eadbe3af7a770d5eeb30
SHA256SUMS SHA-256
  2da0c994199937225721f839ce6753e440b62bf8719d787725299f352c60965a
declared package files                                      898
```

The package was transferred directly and uncompressed to:

```text
/home/yangshen0711/tsc_software/
stage4_2r3c3t13s24d1r14r7r2_995d81c
```

It was then installed in the canonical project:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib
```

The exact output and complete log are:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14r7r2_audits/
stage4_2r3c3t13s24d1r14r7r2_action_conditioned_full_history_kernel_20260804_995d81c_v1

/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
stage4_2r3c3t13s24d1r14r7r2_offline_20260804_995d81c_v1.log
```

## Validation actually run

Local/repository validation used only `venv\Scripts\python.exe`:

```text
all repository JSON before packaging                       9,977 parsed
compileall                                                        passed
focused R7R2 tests                                               5 / 5
complete repository suite                                  1,136 / 1,136
empty-directory direct-copy hashes                            898 / 898
empty-directory JSON                                             100 parsed
empty-directory import/config contracts                             passed
empty-directory complete suite                           1,136 / 1,136
expected isolated-data skip                                         1
```

Staging and installed validation used only
`/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python`:

```text
staging hashes                                               898 / 898
staging bash syntax / compile / JSON / import contracts          passed
staging focused tests                                              5 / 5
staging complete suite                                  1,136 / 1,136
installed hashes                                             898 / 898
installed bash syntax / compile / import contracts               passed
installed focused tests                                            5 / 5
installed complete suite                                1,136 / 1,136
expected source-data skip in each isolated/server suite               1
```

No global Python, package installation, server Git, archive operation, or
outbound server network was used.

## Source and output evidence

The two implementations independently authenticated:

```text
R2 raw                                     72 files / 2,254,876 bytes
R4 raw                                    200 files / 6,285,765 bytes
R6 raw                                     48 files / 1,509,679 bytes
total                                     320 files
response bank                 R2 64 + R4 192 + R6 48 = 304
whole physical pairs / contexts                         4 / 8
```

The exact source inventory digests and final/independent source-result hashes
remain frozen in the R7R2 config and were checked before any fit. The final
output inventory is:

```text
detailed      1,626,046 bytes
  0f7c801ed5138260ab7e836b898df31f2f252c9cc9b89a34353b27bc4209f84d
independent   1,564,125 bytes
  743fd3c06ff97ff1d4a1b32e5494658dbf1f9ec33bba99e9d5d65d9d7a7a9bb1
summary           3,602 bytes
  63f099404af1c4b8ed3b57a335b2188ebe768ba257a35cfe3cce44713c73f7b1
manifest          1,065 bytes
  ba99bf0dc46e5c0882630630866dd7c362f893a1def061de551ad0fb09ac874c
complete log      4,820 bytes
  567dac1ad4c0762d0f21e7b7a9118994b256e09372476249f9e54ba85db7380b
```

The two large row-level files remain server-side. Only the compact forensic
artifact, summary, manifest, and complete log were downloaded to:

```text
docs/codex/audits/
stage4_2r3c3t13s24d1r14r7r2_20260804_995d81c/
```

The compact forensic SHA-256 is:

```text
f0e838b4124f3054dfad091964faeecf2cf092e2b54f0396e10b65423d069c8c
```

## Failure localization

The frozen model improved the same-amplitude R2/R4 subset from R7R1's
`150/256` to `200/256`, but it did not close the whole-pair generalization
gate. The new R6 amplitude branch passed only `36/48`, giving `236/304`
overall.

```text
source                         pass / total
R2                               52 / 64
R4                              148 / 192
R6                               36 / 48

request scale
1.0                             200 / 256
1.5                              36 / 48

sign
negative                        118 / 152
positive                        118 / 152

issue step
10                               52 / 64
14                               65 / 80
18                               60 / 80
22                               59 / 80
```

The failure is strongly pair-dependent rather than sign-dependent:

```text
p5_q1_a0p750_gap2_settle4        68 / 76
p5_q1_a0p900_gap4_settle4        70 / 76
p9_q2_a0p750_gap4_settle4        54 / 76
p9_q2_a0p900_gap3_settle4        44 / 76
```

Both histories are similarly affected (`119/152` and `117/152`). Direction
zero has more rows because it contains both amplitudes and passes `79/112`;
directions one through three pass `48/64`, `58/64`, and `51/64`.

All 304 point-error predicates and the componentwise tube cap passed. The
failures are instead dominated by held-pair response direction and relative
amplitude:

```text
all gates                                                   236
cosine + peak ratio + relative L2 failed                     28
cosine + relative L2 failed                                  19
cosine only failed                                           10
peak ratio only failed                                        7
other relative/peak combinations                              4
```

The worst rows occur mainly in the two prefix-9 pairs. For example, the
`p9_q2_a0p900_gap3_settle4 / plus_first / issue 22 / direction 0 /
negative / 1.0x` row has relative L2 `1.5695004725`, cosine `0.6707367`, and
peak ratio `2.309052`. The minimum cosine `0.2450756` occurs in the same pair
at issue 18.

This pattern rules out a global amplitude-only fix. It also shows that adding
complete visible history and a nonlinear kernel does not compensate for only
four physical pairs when one complete pair is held out. It does not establish
that the allowed causal state is globally non-observable; the current data do
not provide dense enough whole-pair support to test that claim.

## Independent agreement and reporting classification

The structurally independent implementation rebuilt source authentication,
request amplitudes, all 304 descriptors and responses, nested selections,
lag-26/27 tails, row metrics, tube, both geometry families, and the route. It
reported `primary_numerical_agreement=true`.

A separate post-result compacting script initially used nonexistent flat
predicate field names and stopped before writing its compact output. Reading
the actual nested `criteria` schema and rerunning that diagnostic produced the
compact artifact above. This was a post-result diagnostic-script field-mapping
error only; it changed no source, model, row, summary, route, or experiment
identity and is not an R7R2 reporting error.

## Scientific conclusion and next action

R7R2 freezes as
`ACTION_CONDITIONED_FULL_HISTORY_MODEL_FAIL_NEW_IDENTIFICATION_REQUIRED`.
The causal model has small absolute errors and preserves predicted authority,
but its response center is not reliable under complete physical-pair holdout.
It cannot be used for MPC.

The next action is a new-identity, partitioned broader deconfounded
identification campaign using the already frozen 20-pair source-context table:

1. retain the four R2/R4/R6 pairs as consumed development data;
2. add the other eight fixed training pairs and require whole-pair nested
   training gates before freezing a model hash;
3. only then run four fresh calibration pairs and freeze a residual tube;
4. only then run four fresh holdout pairs;
5. if and only if all gates pass, preregister a fresh multipulse interaction
   sentinel before any real MPC.

Formal timing remains states `25/35` and `27/37` and was not evaluated as a
success gate here. Probe trajectories remain forbidden from expert data.
Real MPC, reliable-expert, unseen-target, continuous plant/actuator variation,
noise, disturbance recovery, long hold, BC, DAgger, and bounded residual RL
remain unvalidated and blocked.

