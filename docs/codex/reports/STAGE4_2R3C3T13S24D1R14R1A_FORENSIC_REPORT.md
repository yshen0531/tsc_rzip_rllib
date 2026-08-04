# Stage4.2R3c3T13S24D1R14R1A forensic report

## Outcome

D1R14R1A is final as:

```text
QUANTIZATION_MARGIN_PREFLIGHT_PASS_R2_SENTINEL_DESIGN_REQUIRED
```

The fixed third-column multiplier `1.275` reproduced its frozen float64 matrix
digest and passed all 64 exact static Card15 issue constructions. This is a
zero-new-TSC quantization-margin preflight PASS only. It proves neither the
state-11 online cancellation nor any plant response, response symmetry,
transition model, controller, MPC, robustness, expert-data, imitation, or RL
property.

## Identity and evidence

```text
local branch
  codex/stage4_2r3c3t13s24-sequential-transition

implementation commit
  58912e7

package commit
  b8040b6

package revision
  r42r3c3t13s24d1r14r1a_quantization_margin_preflight_v1

package manifest SHA-256
  c465a4653b5d88e0a3d8ec0eb63ad0456f150b0db3960dd99a11e6b7a4475299

package SHA256SUMS SHA-256
  189bea5c9bf869c49568614ae198b17b8b2a77c86fb2604c253a8a8dfbfbef3b

declared package files
  530
```

Remote package and result paths:

```text
staging package
  /home/yangshen0711/tsc_software/stage4_2r3c3t13s24d1r14r1a_b8040b6_package

installed project
  /home/yangshen0711/tsc_all/tsc_rzip_rllib

formal output
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r14r1a_audits/
  stage4_2r3c3t13s24d1r14r1a_quantization_margin_preflight_20260804_b8040b6_v1

offline log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t13s24d1r14r1a_offline_20260804_b8040b6_v1.log

installed verification log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/
  stage4_2r3c3t13s24d1r14r1a_b8040b6_installed_verify.log
```

Compact output hashes:

```text
detailed  a9ffc98b798d4735d7302b1ca4407dbc60266228007d82d34418a291df2b0e8d
summary   77194861b0406257d055b5ebe0e087b9f9c8222e76600fa443de9d34e7fc682f
manifest  d6b4c53c46b8948d979d3eaee1861885f61d33ac70097a7576110361f0bafa87
log       915d91af05efb2bface9b09c43a291c65df55ac5afc0ee755f57d793d08c134f
```

The local compact copy and its complete transfer inventory are under
`docs/codex/audits/stage4_2r3c3t13s24d1r14r1a_20260804_b8040b6/`.

## Independent result reconstruction

The formal audit authenticated the immutable D1R14 v2 boundary in place:

```text
source raw files / strict parses                         72 / 72
source raw bytes                                      2,239,479
source raw inventory digest
  0433a64ebaea73186bb193d5102686721497219acfcbecbb721e7fad62e8d7a3
source primary final SHA
  1a65a37c301ba52325f586e0948b0b94b1266c540e2f2a332e5bc02df60a7da2
source independent audit SHA
  8e7d3d045477502c1060fe621f2c43235e1d530b59c5d22849337dd20aac3eae
```

It also authenticated the exact D1R14R1 failure boundary: 48/64 static
passes, with all 16 failures confined to direction 2's off-basis predicate.
R1A then regenerated the fixed matrix by scaling only column 2 by `1.275`:

```text
matrix float64 little-endian C-order SHA-256
  c8cd62c00c1f60b46312927789659657dc8cc35717533193433b0e398c1ec94c

predicted minimum odd peak                         0.005999999999999252
required minimum                                                        0.006
predicted maximum unit-column condition                  3.702078001189697
required maximum                                                        4.0
```

The apparent one-ULP-below decimal representation of the minimum odd peak is
inside the prospectively frozen `5e-12` numerical comparison allowance. It is
not a post-result threshold change.

Local independent recomputation from every one of the 64 detailed rows found:

```text
contexts / unique context-direction-sign rows                  8 / 64
all row criteria / row pass                              64 / 64
maximum incremental normalized action            0.14018518518518544
maximum total normalized action                  0.14018518518518544
maximum predicted current utilization                         0.38005
minimum desired/applied current cosine               0.9945784028453954
maximum relative off-basis residual                 0.09907590194856689
maximum linearized cancellation diagnostic         0.14018518518518544
```

Every unchanged gate passed: finite values, exact Card15 center and target,
target reproduction, no saturation/current clipping, actuator gate,
incremental/total action, current utilization, cosine, and off-basis residual.

## Execution and corruption inventory

```text
expected new raw / actual new raw                            0 / 0
Ray / gotsc / TSC / controller / plant steps           0 / 0 / 0 / 0 / 0
new snapshots                                                   0
compact JSON strict parse                                  3 / 3
compact manifest output-hash matches                       2 / 2
remote/local compact size and SHA matches                  5 / 5
```

No new raw or snapshot exists because R1A is deliberately offline. The 72
large D1R14 source raw files and their snapshots remain immutable on the
server; none were downloaded locally.

## Error classification

- Runtime/environment error: none in the formal R1A execution.
- Packaging/import/deployment error: none in the installed verification or
  formal R1A execution.
- Raw/snapshot corruption: none in the authenticated 72-file source boundary;
  R1A created no new raw or snapshot.
- Statistics/reporting error: none in the final output. Row-level independent
  recomputation matches the saved summary and manifest.
- Design defect: the predecessor R1's insufficient Card15 off-basis margin is
  repaired for the fixed development-selected candidate at the static issue
  boundary. The state-11 cancellation boundary remains deliberately untested.
- Real control/plant-restart conclusion: none; R1A executed no controller or
  plant.

An additional exploratory complete server test discovery was run after the
formal result. It ran 1,057 tests and reported 22 `FileNotFoundError` errors
plus three launcher assertions, all caused by historical tests requiring
historical root launchers that the current-stage minimal deployment
intentionally does not install. Its SHA is
`ddcdddf70114a6817ff60a8d0a1d7451751888c57b346a5699577d104145c413`.
This is a test-scope/deployment-layout incompatibility, not a R1A source,
runtime, scientific, or reporting failure. The current-stage installed
verification passed 530/530 package hashes, shell syntax, Python/JSON guards,
and 6/6 focused tests. The complete local repository suite passed 1,057/1,057
before deployment in the repository-local Windows virtual environment.

## Frozen conclusion and next action

R1A is frozen as a finite, development-selected, exact static construction
PASS. The development grid is consumed and may not be described as an
independent holdout. The `0.24` online cancellation margin, authentic response
symmetry, odd signal, rank four, condition at most 20, and plant behavior must
now be tested in a fresh D1R14R2 identity.

D1R14R2 must use 72 fresh authentic trajectories: eight zero baselines and
64 signed probes over the exact fixed mixed matrix. It must reproduce the
source prefix through state 10, apply the issue at task step 10, restore the
stored center causally at task step 11 under both the original `0.25` cap and
the prospective `0.24` online margin, then command exact zero through the
unchanged 35/37-state horizon. Safety and integrity gates precede the frozen
response-geometry gates. Formal tracking remains diagnostic only.

Even a D1R14R2 PASS can authorize only a separately preregistered
time-distributed zero-baseline identification campaign. It cannot authorize a
transition model, MPC, expert dataset, BC, DAgger, or bounded residual RL.

## Commands and validation actually run

- Local repository boundary, Git status, branch, and checkpoint checks.
- Complete reads of `AGENTS.md`, project context, server workflow, current
  task, R1A design/config/implementation/tests/launchers, manifest evidence,
  formal JSON, and complete logs.
- Fixed-endpoint authorized SSH preflight and exact remote output inventory.
- Direct uncompressed `scp` of three JSON files and three logs; local byte and
  SHA-256 verification.
- Repository-local `venv` strict JSON parsing and independent 64-row gate
  aggregation.
- Previously recorded local compile/JSON/import-closure/empty-deployment
  validation and 1,057/1,057 complete tests.
- Installed-server package verification with the existing server virtualenv:
  530/530 hashes, shell syntax, Python/JSON, and 6/6 focused tests.
- Exploratory installed-tree complete discovery: 1,057 run, 22 missing-
  historical-launcher errors, three historical launcher assertions, one
  expected skip; classified above and not concealed as a pass.

No R1A TSC, Ray, `gotsc`, controller, plant step, formal tracking, online
cancellation, or response-geometry experiment was run.
