# Stage4.2R3c3T13S24D1R14R8R18 forensic report

Finalized on 2026-08-08 Asia/Shanghai from the exact deployed source,
immutable server evidence, primary computation, and structurally independent
recomputation. Chat summaries are not evidence.

## 1. Final classification

```text
route
  SECOND_ORDER_BOOLEAN_RIDGE_MODEL_INADEQUATE_NONPARAMETRIC_SEQUENCE_REDESIGN_REQUIRED

source/integrity gate       PASS
code geometry gate          PASS
tube gate                   PASS
LOCO formal classification  PASS (160/160)
LOCO model gate             FAIL (157/160)
authority gate              NOT OPENED
real TSC executed           false
new raw                     0
```

R8R18 is a clean zero-new-TSC second-order Boolean ridge model-design
failure. All R8R15, R8R16, and R8R17 source authentication, code-only
geometry, component, scaled-point, formal-classification, and tube gates
passed. Three of the 160 prospectively frozen leave-one-code-out trajectory
predictions exceeded the unchanged `0.05` minimum-formal-margin error cap;
the maximum was `0.05685241823211573`.

The authority phase remained closed. Its zero baseline, failure, missing-
prediction, repair, and oracle fields are unrun-phase sentinels, not measured
outcomes. The immutable R8R15 baseline remains `6/16` with ten failures.

This is not a runtime, source, raw, restart, causality, formal-evaluator,
reporting, controller, plant, physical-authority, real-MPC, Gate A, or global-
reachability failure. R8R18 is immutable and may not be relaxed, refit, or
enlarged under the same identity.

## 2. Identity, package, and validation

```text
design checkpoint          1366017
implementation checkpoint 7dae75a
package checkpoint        e5003f5
design SHA-256
  f7de518d1bc65588883d245eb7fd1de5f63b84c679713b38102db6047d28ab9d

PACKAGE_MANIFEST.json
  98244 bytes / 1080 declared paths
  7d89e84c63172c62ca0a46cb1cb72c0f316b7e94f5c8652e0c1c8859944d024c
SHA256SUMS
  136500 bytes
  1f6248c12a00222a5390bb842f0cc16f1fca9b4d75f0a982c09569e568f67abf
```

Exact deployed R8R18 source hashes were:

```text
config       0e08dabcec029f2ae599cb3f1db9ab57fe4fdd882b2daffc11aa32b3cb3c593b
primary      b63adf5f54cd88718b2139aac0ccda760b79b44f8a14646775dff28557b13c12
independent  71e49f0ef2f9a406748aeecaaa337e2df9df1f797d1cc8483ca02cb89ca91e45
launcher     dcf9abf1d5e38f0a5d3e308efb58c19de17e5c2376dfc598803d12c966ad4da7
```

The project virtual environment passed compilation, focused `9/9`, and the
Windows-resource-shimmed full `1317/1317` suite. The empty direct-copy tree
contained 1,080 declared files plus `PACKAGE_MANIFEST.json` and
`SHA256SUMS`; all hashes, compilation, focused `9/9`, and full `1317/1317`
passed, with one expected isolated-evidence skip in the empty tree.

The directory was transferred directly with `scp -r`, without an archive.
Server staging and the installed project, using only the existing server
virtual environment, both passed:

```text
hashes / JSON         1080/1080 / PASS
bash -n               PASS for every shell file
compile               PASS
focused unittest      9/9
full unittest         1317/1317, one expected skip
```

The first guarded install attempt verified the exact project target, removed
only the documented replaceable code directories/root shell files, and then
stopped before copying because its Bash checksum-line parser rejected the
first line. The complete already-validated staging tree was immediately
copied back without an archive; all 1,080 hashes and the complete installed
test suite then passed. No run output, source run, raw, virtual-environment
file, or unrelated server path was touched. This was a deployment-script
error with complete recovery, not a code or scientific failure.

No global Python, server Git, network package operation, or archive operation
was used.

## 3. Exact server result

```text
run root
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r14r8r18_runs/
  stage4_2r3c3t13s24d1r14r8r18_second_order_boolean_ridge_loco_preflight_20260808_e5003f5_v1

stage directory
  stage4_2r3c3t13s24d1r14r8r18_second_order_boolean_ridge_loco_preflight
```

Accepted server hashes are:

```text
primary detailed      d3b71fcf60a014be1f677fb1b03a5c549c467ecbf5a9fadf5f9e350fbe323fcd
primary summary       d67f2080c2256efdd6be9848d61bc88e922adaeb171f15615e7c61085e6f0e82
independent           b53cb99382b551468943148338a0c23f5b71d60761b238fe03f49af7cfd5166d
final report          cfc5c381011ffdadee311acd98478ce9a386b2173c12d2a96ae6a5c274d9bbca
R8R15 authentication  88ed50a9fbe6d303151c264309b919dd0e906be5818513626868791084e9f362
R8R16 authentication  1938c1e6772e704b37e20f26861bddd8b15c706450de42700e11496270162812
R8R17 authentication  9dec20a5e5ed802896c681db3ac4845cc578b70a6a15afb0e31c37e5e29da42d
stage manifest        50b9842de89e90849669979a19a84ba8451f6bb8fe2b590390747d2ce96ef356
stage state           660efeae771da43a966532137ba45a0344a5c95b81905e7cefc8a94ac0bb08a5
final server evidence 9d9fc1adfa0e61d9de31586df3f4e63d3b27e6e7fc87496f8acf133530cfc826
```

The ten compact JSON files total 166,181 bytes. They strictly parse and all
server hashes reproduce locally. The stage has no raw or snapshot directory.

## 4. Model result

The fixed Boolean feature family and code-only stability geometry reproduced:

```text
features                         intercept + four signs + six sign pairs
pair ridge lambda                10
measured rank                    9
full-cube rank / condition       11 / 1.0000000000000007
max LOCO normal condition        31.864801866585626
max LOCO weight L2               1.2644229640823352
max LOCO absolute weight         0.9999999999999976
full normal condition            11.096194077712552
max missing-code weight L2       1.273908766556156
max missing-code absolute weight 0.6585365853658539
```

Prospective LOCO results were:

```text
trajectory gate                       157/160
formal classification                 160/160
maximum R absolute error       0.0001830060142536436 m
maximum Z absolute error       0.00016111424166666668 m
maximum Ip absolute error      13.363038888890514 A
maximum scaled point error     0.0061002004751214535
maximum minimum-margin error   0.05685241823211573
tube gate                              PASS
```

The three failures were all in context
`p5_q2_a0p750_gap3_settle4`: held `UUUU` for both histories and held `VVVV`
for `minus_first`. Their margin errors were `0.05685241823211573`,
`0.050418989738499675`, and `0.056721208655654554`. Their actual and predicted
formal classifications were nevertheless identical failures. These row
identities were opened only after the frozen R8R18 result and route existed.

The primary augmented-SVD and structurally independent normal-equation
implementations agreed on every gate and route. Their maximum numerical
difference was `8.881784197001252e-15`.

## 5. Boundary after R8R18

The same second-order ridge family is vetoed. The result does not show that
all nonparametric finite-sequence models fail, that any missing physical code
lacks authority, or that the plant is unreachable. A new identity may use a
prospectively frozen code-only nonparametric prior and the same ten-code LOCO
test without changing any physical/formal cap. Its design and hyperparameters
must be frozen before its response output is computed.

Only a complete model PASS may open the six missing-code predictions, and
only a robust authority PASS may authorize a separately frozen fresh physical
sentinel. Every R8-family trajectory remains probe/control-development
evidence and is forbidden from expert, BC, DAgger, and RL data. Gate A
remains blocked.
