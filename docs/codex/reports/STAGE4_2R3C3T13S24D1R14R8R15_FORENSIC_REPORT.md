# Stage4.2R3c3T13S24D1R14R8R15 forensic report

Finalized on 2026-08-08 Asia/Shanghai from the accepted server raw, exact
deployed source, compact server-side postprocessing, and structurally
independent recomputation. Chat summaries are not evidence for this report.

## 1. Final classification

```text
route
  BINARY_TEMPORAL_SWITCHING_STAIRCASE_AUTHORITY_INSUFFICIENT_MODEL_BASED_SEQUENCE_REDESIGN_REQUIRED

integrity gate       PASS
scientific gate      FAIL
real TSC executed    true
new raw              128
formal repairs       0/10 failed baselines
held oracle          6/16
```

R8R15 is a clean finite binary temporal-sequence authority-design failure.
All 128 new trajectories completed the authentic restart boundary and frozen
horizon. Runtime, physical prefix, calibration, exact Card15 target chain,
action, current, causality, finite-state, raw, report, and formal-evaluator
integrity passed. None of the eight newly measured mixed U/V sequences
repaired any of the ten failed R8R7 baselines.

This is not a runtime, deployment, source-authentication, restart, causality,
raw-corruption, reporting, formal-evaluator, safety, controller-construction,
plant, real-MPC, Gate A, or global-reachability failure. The identity is
immutable and may not be resumed, enlarged, or tuned. Its route requires a
new prospectively frozen model-based sequence redesign.

## 2. Frozen identity and package

```text
design checkpoint          e3d5302
implementation checkpoint  222f5d5
package checkpoint         f23c96e
design SHA-256
  bc0651d9c07f25c961bb5251ab508bda45ddc611d2b32f052ea0592cfe938bfe

PACKAGE_MANIFEST.json
  93928 bytes
  9080742da630ea8d2396f99e2e8b24b858fdbee8581ddd1fd6c9ec0c42f19e8d
SHA256SUMS
  134442 bytes / 1059 declared paths / LF only
  746430a19478e37fb6c07458d1e3d1e05f2143f3f815611208cebbd6be0b9cf8
```

The package was built by direct-copying all 1,059 declared files into a new
empty repository-local directory and then adding the manifest and checksums,
for 1,061 files before validation caches. It was transferred with `scp -r`;
no archive was created or extracted. Only the existing project and server
virtual environments were used.

Exact deployed source hashes were:

```text
config       9d7e821bc45b2ed1c3052f7077bd95bfacc261eac681020090227b35d54c19df
primary      ae8c6eac2d3ded32d04cbec8cf377d26266338d0d7ba38ddd68f0ab05c6ff1c0
independent  4733ffb6642b244988df151b463cf10ac877c6873d80dd051d4012dfff50ad4d
launcher     12189db8989c0abe4a2d57a464ca68a7083e45ab7fd91eb101fa8b54b4e0f150
```

## 3. Validation evidence

After loading the existing Windows `resource` shim, the project virtual
environment passed compilation, focused `11/11`, and full `1290/1290` tests.
The empty direct-copy package passed all 1,059 hashes, compilation, focused
`11/11`, and full `1290/1290`, with one expected isolated-evidence skip.

The existing server virtual environment passed in both staging and the
installed project:

```text
declared hashes       1059/1059
bash -n               PASS
compileall            410 files
focused unittest      11/11
full unittest         1290/1290, one expected skip
```

A local focused-test invocation without first loading the repository's
Windows `resource` shim reproduced the known old Linux-test import error. The
unchanged shimmed run passed. This was a Windows collection/invocation issue,
not a code regression.

The remote install copied the complete exact package, but the trailing
inline validation print in that invocation lost dict-key quotes through the
Windows-to-SSH quoting layer and raised `NameError: file_inventory`. No
delete, reinstall, or changed copy followed. A separate read-only validation
proved all 1,059 installed hashes exact, applied launcher execute bits, and
passed bash syntax, compilation, focused, and full tests. This was a
post-copy invocation error, not a package or deployment-content failure.

## 4. Exact server run and immutable evidence

```text
run root
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r14r8r15_runs/
  stage4_2r3c3t13s24d1r14r8r15_binary_temporal_switching_staircase_authority_sentinel_20260808_f23c96e_v1

stage directory
  stage4_2r3c3t13s24d1r14r8r15_binary_temporal_switching_staircase_authority_sentinel
```

Accepted hashes are:

```text
offline preflight     0d2e87a0b18c516878a33211548e28d88c7e12e90ecf08e5d88cb6fa5908241c
offline primary       b99eb06586e45044c36c57bb75cd195088d01105d3447cc83f1826f3741f6990
offline independent   3e1f3d1d1057cdd208c550922304282a1ff91b2e27b6c87e900524a374f70db0
safety primary        9bfae0ace3c930ea535a81ef9f159ceddfe9369396817031ba7a684c78a7551d
safety independent    b9ca4097011ee88f912c66a0fdb5a47ed9c385c0d44ea93decf810f539d8c88a
qualification primary c4843acfdb3b60aec6a3fae28dff4fb43699d231a25770e58f4a29af5a300de8
qualification independent
                      189fc73abe11d1e24ac66cc3be11933af415764bb32deb255ef8b70fd9ee1ff3
primary detailed      d840d54ab1be6e3aef318d7b7859dd58a450b5b478c2bb736d8900be2bd9f024
primary summary       2c5b7e10c74295f82cc54769fee51a87bea69682d7b5992963b99ff33845cde6
final independent     cf896933a7b8d911027389018d1668adda1d04de1e17822b9bb83ee4d493ea34
final report          cd1c37589955137c0b5d38c4f6e410b77a83ddb0d7c55dc803153bd8c0549664
stage manifest        3d704e4167738575d4ee9417ae48f2ee732a1645feee6b357cc3f45f80665ffb
stage state           71d4a0d3472e073ee423a8e0ae305999525264cf217b91dd5e2fbae17e2fce18
compact evidence      cdba408f508e812e9a63eea3b4bbec859b85ed69e2e36b01aa6b7e40c6e82f2b
```

Only six compact JSON files, totaling 19,568 bytes, were downloaded. Their
hashes reproduce the server evidence. All raw, variants, per-row detailed
results, and source snapshots remain on the server.

Two auxiliary read-only SSH invocations had quoting errors: the first
malformed a preflight print/find command, and the second malformed an inline
`python -c` used only to list final files. Neither modified stage data. The
actual preflight, finalization, and evidence generation were rerun with safe
argument forms and passed. These are invocation errors, not run or scientific
failures.

## 5. Offline, execution, and raw integrity

Primary and independent offline construction agreed exactly:

```text
specifications                         128/128
exact cumulative issues                512/512
exact stored-target refreshes        2816/2816
maximum issue increment          0.1409259259259261
maximum refresh increment        0.0000037037037048793097
maximum predicted current use     0.39049999999999996
real TSC before dual preflight                     0
```

The safety partition completed and independently authenticated before the
qualification partition was authorized:

```text
                                      safety        qualification       total
raw count                                  32                   96         128
raw bytes                             1059431              3201665     4261096
raw digest                         7d7a2b4f...          a909e034...          -
runtime/full horizon/prefix             32/32                96/96     128/128
calibration/event/target chain          32/32                96/96     128/128
issues                                    128                  384         512
refreshes                                  704                 2112        2816
forbidden trace rows                        0                    0           0
```

All 128 gzip JSON files were independently strictly parsed again after final
postprocessing. Their phase counts, byte totals, file hashes, and canonical
inventory digests reproduced the independent raw audits exactly. Maximum
measured current utilization was `0.3924`; maximum issue and refresh
increments were `0.1409259259259261` and
`3.7037037048793097e-06`. No rejected-action safe stop was needed. R8, R8R1,
R8R12, and R8R14 were not rerun, and R8R15 created no snapshot.

## 6. Formal outcome

The unchanged evaluator reproduced every existing and new formal metric
exactly; the maximum signed-margin difference was zero. The baseline,
immutable R8R12 `UUUU`, and immutable R8R14 `VVVV` all passed `6/16`.
Every new temporal family also passed exactly `6/16`:

```text
sequence  source  formal  repairs  baseline regressions
UUUU      R8R12   6/16    0/10     0/6
VVVV      R8R14   6/16    0/10     0/6
UVVV      R8R15   6/16    0/10     0/6
UUVV      R8R15   6/16    0/10     0/6
UUUV      R8R15   6/16    0/10     0/6
VUUU      R8R15   6/16    0/10     0/6
VVUU      R8R15   6/16    0/10     0/6
VVVU      R8R15   6/16    0/10     0/6
UVUV      R8R15   6/16    0/10     0/6
VUVU      R8R15   6/16    0/10     0/6
```

The eight new families therefore contain 48 formal-pass trajectories, all in
the same six already passing contexts. Across the ten failed baselines, the
best measured-candidate minimum-margin gain was:

```text
minimum  0.025541733333334093
median   0.08895878160707882
maximum  0.1364830983921772
```

Every best candidate still had a negative formal margin. Repairs were
`0/10`, the do-nothing-safe held oracle remained `6/16`, and the frozen
`>=1/10` / `>=7/16` gate failed. Primary and the structurally independent
implementation agree exactly on every candidate summary, numerical metric,
scientific gate, and route.

## 7. Boundary after R8R15

R8R15 rules out only the frozen binary U/V four-decision temporal basis over
the finite 16-context envelope. It does not establish that other bounded
multidirection actions are useless, that a model-based receding-horizon
sequence cannot work, or that the plant is globally unreachable.

The result does show that choosing among fixed open-loop sequences is not a
causal controller architecture: all ten measured candidates preserve the
same formal partition even though failed-context margins improve. The next
stage must therefore be a separately frozen model-based sequence redesign,
with explicit train/calibration/held-context separation and no post-result
sequence expansion. It must preserve exact authentic restart, visible-state
causality, Card15/action/current/saturation and safe-stop contracts, immutable
formal timing, independent recomputation, and the learning-data prohibition.

Every R8-family trajectory remains probe/control-development evidence and is
forbidden from expert, BC, DAgger, and RL data. Gate A remains blocked.
