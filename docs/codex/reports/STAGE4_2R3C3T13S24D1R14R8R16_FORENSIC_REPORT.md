# Stage4.2R3c3T13S24D1R14R8R16 forensic report

Finalized on 2026-08-08 Asia/Shanghai from the exact deployed source,
immutable server evidence, primary computation, and structurally independent
recomputation. Chat summaries are not evidence for this report.

## 1. Final classification

```text
route
  TEMPORAL_AFFINE_SEQUENCE_MODEL_INADEQUATE_NONLINEAR_SEQUENCE_REDESIGN_REQUIRED

source/integrity gate       PASS
geometry gate               PASS
tube gate                   PASS
calibration model gate      FAIL (63/64)
authority gate              NOT OPENED
real TSC executed           false
new raw                     0
```

R8R16 is a clean zero-new-TSC temporal-affine sequence-model design failure.
The exact source evidence authenticated, all JSON parsed strictly, both design
matrices had full rank and stayed within their frozen condition caps, and the
fixed residual tube passed. One of 64 held calibration trajectories exceeded
only the frozen minimum-formal-margin error cap:

```text
maximum minimum-margin absolute error   0.05171944884413282
frozen cap                              0.05
maximum scaled point error              0.004582066666663117
frozen cap                              0.10
```

The missing-code authority gate remained closed exactly as preregistered.
Consequently the reported zero baseline, failure, prediction, repair, and
oracle counts are not measured control outcomes; they are sentinel values for
an unrun downstream phase. The immutable R8R15 baseline remains `6/16` with
ten failures.

This is not a runtime, deployment, source-authentication, raw-corruption,
restart, causality, formal-evaluator, reporting, controller, plant,
physical-authority, real-MPC, Gate A, or global-reachability failure. R8R16
may not be relaxed or refit after this result. Its frozen route requires a new
prospectively specified nonlinear sequence-model redesign.

## 2. Frozen identity and exact package

```text
design checkpoint          d68aae4
implementation checkpoint d7364e8
package checkpoint        e2325b0
design SHA-256
  2b48e9d6e74222977db1af687009f031aac3da90e9e6b008a856412cc119367b

PACKAGE_MANIFEST.json
  94475 bytes
  4af32064c22951aa6da457aeb400d008dc9174fd5fababcc336c22ffa1a2a79a
SHA256SUMS
  134430 bytes / 1066 declared paths
  4ced275ef6c9490c5bc3a5c8637333529254ee76086955e186ffba644ed78515
```

The package was built by directly copying all 1,066 declared paths into a
new empty repository-local directory and then adding the manifest and
checksums, for 1,068 files before validation caches. It was transferred with
`scp -r`; no archive was created or extracted. Only the existing project and
server virtual environments were used.

Exact deployed R8R16 source hashes were:

```text
config       2dc5518d7cd4e9d522e5a7b02d4f2e8b8366684b0b7c63fa1b0d5aa4f81b9396
primary      b15d468563be5cafee62b6551be79094d3b24af231ec85e5ef51b2ad55eb5cff
independent  4d15ed3d91daffb1aee296f7505fe90d7f0b2d385261629473f6ccf3169943b0
launcher     604f90c6dbaa74857215da680a4695618a5424fceccb8cb8b3ebd99760844089
```

## 3. Validation and deployment evidence

Using the project virtual environment and loading the repository's existing
Windows `resource` shim first, compilation, focused `9/9`, and full
`1299/1299` tests passed locally. The empty direct-copy package passed all
1,066 hashes, compilation, focused `9/9`, and full `1299/1299`, with one
expected isolated-evidence skip.

The direct-copied server staging tree and installed project passed with the
existing server virtual environment:

```text
declared hashes       1066/1066
JSON                  PASS
bash -n               PASS
compileall            PASS
focused unittest      9/9
full unittest         1299/1299, one expected skip
```

The install used an exact project-root guard and replaced only `configs/`,
`scripts/`, `tests/`, `tsc_rzip_rllib/`, declared root shell scripts, and the
two package metadata files. Documentation was overlaid. Existing run trees,
including R8R15 raw, were checked before and after and preserved.

The first installed validation had exit code zero and all tests passed, but
PowerShell rendered unittest stderr progress as `NativeCommandError` text.
An unchanged read-only rerun with remote `exec 2>&1` produced clean evidence.
This was a log-capture invocation issue, not a test, package, or deployment
failure.

## 4. Exact server result and compact evidence

```text
run root
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r14r8r16_runs/
  stage4_2r3c3t13s24d1r14r8r16_temporal_affine_binary_cube_completion_preflight_20260808_e2325b0_v1

stage directory
  stage4_2r3c3t13s24d1r14r8r16_temporal_affine_binary_cube_completion_preflight
```

Accepted server hashes are:

```text
primary detailed      5f8605e45982ace397b364361cb71a2249520f0686c4e39c8879f06a37ebf429
primary summary       be9a7b968a79d2cf95b3f6dd9103e9797d375448215769e53745dea46fb0cff6
independent           8f73d31dd5370a295ed4096ea77a4f8585d2d89c54b1625ecf0ae26f5a29ef7a
final report          f17c4338579fda179739630a35fcf97f07a71d261bb96eafb47f4c69680ef58e
source authentication 88ed50a9fbe6d303151c264309b919dd0e906be5818513626868791084e9f362
stage manifest        605b98ceea86edcb1b1680c87bbcd012f5a727a747c0f6a6d91988922460ef4d
stage state           7b6679436e3a8551f451356e8f817f49a36e097e71b7237ec2f61de680641af3
```

The server existing virtual environment strictly parsed all seven output
JSON files and verified that no raw or snapshot directory exists. The same
seven files, totaling 70,474 bytes, were copied directly into:

```text
artifacts/server_audits/
stage4_2r3c3t13s24d1r14r8r16_20260808_e2325b0_v1/compact/
```

Local strict parsing and all seven downloaded hashes reproduce the server
evidence exactly. Three preliminary read-only evidence-list invocations had
Windows-to-SSH newline, quote, or wildcard handling errors. They exited
without modifying the result tree. The accepted v4 strict parse/hash check
passed; these were auxiliary invocation errors, not run or scientific
failures.

## 5. Source authentication and model result

R8R16 reauthenticated the exact R8R15 final evidence and inventories:

```text
safety raw          32 files / 1059431 bytes / 7d7a2b4f...
qualification raw   96 files / 3201665 bytes / a909e034...
R8R12 source        authenticated
R8R14 source        authenticated
R8R15 final route   authenticated
```

The frozen affine design geometry passed:

```text
development rank / condition   5 / 3.186140661634507
frozen requirement             5 / <= 3.25
full rank / condition          5 / 2.6131259297527527
frozen requirement             5 / <= 2.62
```

Held calibration used exactly `VVUU,VVVU,UVUV,VUVU`, 16 contexts each. All
64 formal classifications were reproduced, but only 63 trajectories passed
every numerical gate. Other worst errors were well inside their caps:

```text
maximum absolute R error    0.0001374619999998935 m
maximum absolute Z error    0.0001083457499999992 m
maximum absolute Ip error   12.699099999999815 A
maximum scaled point error  0.004582066666663117
tube gate                   PASS
```

The primary explicit-SVD pseudoinverse and independent `numpy.linalg.lstsq`
implementation agreed on outcome and route. Their maximum numerical
difference was `5.329070518200751e-15`. Because the model gate failed before
refitting, the six never-executed codes were not predicted or ranked and no
physical sentinel was authorized.

## 6. Boundary after R8R16

R8R16 rules out only the frozen per-context five-parameter temporal-affine
model and its exact 63/64 qualification threshold. It does not show that the
six missing sequences lack authority, that bounded nonlinear or interaction
models cannot predict them, or that a genuine receding-horizon controller
cannot satisfy the finite Gate A envelope.

The next stage must be a new-identity, prospectively frozen nonlinear
sequence-model audit over already consumed development evidence, with an
unchanged held calibration split and fail-closed routes. It must not tune the
R8R16 cap after observing the `0.0517194488` miss. Any later real TSC requires
a separately frozen finite sentinel and the unchanged restart, visible-state
causality, Card15/action/current/saturation, safe-stop, formal timing, and
independent-audit contracts.

Every R8-family trajectory remains probe/control-development evidence and is
forbidden from expert, BC, DAgger, and RL data. Gate A remains blocked.
