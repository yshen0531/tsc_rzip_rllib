# Stage4.2R3c3T13S24D1R14R8R17 forensic report

Finalized on 2026-08-08 Asia/Shanghai from the exact deployed source,
immutable server evidence, primary computation, and structurally independent
recomputation. Chat summaries are not evidence.

## 1. Final classification

```text
route
  ADJACENT_SWITCH_INTERACTION_MODEL_INADEQUATE_HIGHER_ORDER_REDESIGN_REQUIRED

source/integrity gate       PASS
code geometry gate          PASS
tube gate                   PASS
calibration model gate      FAIL (61/64)
authority gate              NOT OPENED
real TSC executed           false
new raw                     0
```

R8R17 is a clean zero-new-TSC adjacent-switch interaction model-design
failure. It added exactly the prospectively frozen normalized adjacent-slot
persistence feature to R8R16. All source authentication, code-only geometry,
component, scaled-point, formal-classification, and tube gates passed, but
three held calibration trajectories exceeded the unchanged `0.05` minimum-
formal-margin error cap. The maximum was `0.09336026574612744`.

The authority phase remained closed. Its zero baseline, failure, prediction,
repair, and oracle fields are unrun-phase sentinels, not measured outcomes.
The immutable R8R15 baseline remains `6/16` with ten failures.

This is not a runtime, deployment, source, raw, restart, causality, formal-
evaluator, reporting, controller, plant, physical-authority, real-MPC,
Gate A, or global-reachability failure. R8R17 is immutable and may not be
relaxed, refit, or enlarged under the same identity.

## 2. Identity, package, and validation

```text
design checkpoint          614487a
implementation checkpoint 6b62ca6
package checkpoint        d7d291a
design SHA-256
  5432fe3f292800910dc8f70e979fc4db89ffee3fa6053ad22383b9029ebc73d0

PACKAGE_MANIFEST.json
  96380 bytes / 1073 declared paths
  2da58c9d0902607778d714d9b3b6157c8380cfcb0267cec1ed940a161a8db0bc
SHA256SUMS
  135481 bytes / LF only
  dbfb96d9d0a623801dd9aa6e5f8404d26c9df46ff071c708bd105f4eacb78488
```

Exact deployed R8R17 source hashes were:

```text
config       f6eab4310e8a97a25fd43a4a7463a63741fab1bbf0d1aa064186a86c13d1c756
primary      198b2c07b1800c93cb420a4acdd4338b33ecb0b7bd005f731cdb516c29acd1eb
independent  226becdeaf1a806bf8edaf0f5ef42ea79e86f74cfa0973165c43c5097cc12176
launcher     8e9054164e93944c9c9ba4abc7a59adec657568ec04c34f47c827d9f9990ea7f
```

The project virtual environment passed JSON, compilation, focused `9/9`, and
the Windows-shimmed full `1308/1308` suite. The empty direct-copy tree passed
all 1,073 hashes, JSON, compilation, focused `9/9`, and full `1308/1308`,
with one expected isolated-evidence skip. The Windows `bash.exe` was only the
unconfigured WSL launcher, so its local output was not counted as shell-
syntax evidence.

The tree was transferred directly with `scp -r`, without an archive. Server
staging and the installed project, using only the existing server virtual
environment, both passed:

```text
hashes / JSON         1073/1073 / PASS
bash -n               PASS for every declared shell file
compileall            PASS
focused unittest      9/9
full unittest         1308/1308, one expected skip
```

The guarded installation preserved the R8R15 and R8R16 run directories and
all historical raw. No global Python, server Git, network package operation,
or archive operation was used.

## 3. Exact server result

```text
run root
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r14r8r17_runs/
  stage4_2r3c3t13s24d1r14r8r17_adjacent_switch_interaction_binary_cube_preflight_20260808_d7d291a_v1

stage directory
  stage4_2r3c3t13s24d1r14r8r17_adjacent_switch_interaction_binary_cube_preflight
```

Accepted server hashes are:

```text
primary detailed      b57f2afc2009e4f28ea6b90cf8034422356f6c1275c0f6a916269a0a94c49020
primary summary       da1c108b7b800c0c8ab4bc9be5325ad3445ac62f799f28ecf5e59dfec30719b8
independent           2a5e8d30db3707ccd764f4d281b32faff2b111bc4c836fc6f269e06b4264745a
final report          f87fba9b71bfebc95a8d1115c74f5aae6190b7af1e0fcc48558a04ab83356dce
R8R15 authentication  88ed50a9fbe6d303151c264309b919dd0e906be5818513626868791084e9f362
R8R16 authentication  1938c1e6772e704b37e20f26861bddd8b15c706450de42700e11496270162812
stage manifest        e0e850c3d19f945c7f53cfcf9c491a5367186d2d46b01cf45213cc4febaf4440
stage state           6b16d1ada9315276284303c52edd60a1ea5f32d0ce33fb73623d45dec4e56b47
```

The server existing virtual environment strictly parsed all eight JSON
files, totaling 71,953 bytes, and proved there was no raw or snapshot
directory. Those eight files were directly copied to the repository and all
hashes reproduced locally. A first local display-only verifier had an
f-string quoting `SyntaxError`; the corrected here-string verifier passed.
No evidence changed. This was a local verification invocation error, not a
run, package, or scientific failure.

## 4. Model result

The fixed normalized interaction and all three design matrices reproduced:

```text
feature a(q)                   (q10*q14+q14*q18+q18*q22)/3
development rank / condition  6 / 6.699042762912874
measured rank / condition     6 / 2.6131259297527527
cube rank / condition         6 / 1.7320508075688772
```

Held calibration results were:

```text
trajectory gate                       61/64
formal classification                 64/64
maximum R absolute error       0.00025217899999996395 m
maximum Z absolute error       0.00016862979999999583 m
maximum Ip absolute error      16.728599999998565 A
maximum scaled point error     0.008405966666665465
maximum minimum-margin error   0.09336026574612744
tube gate                              PASS
```

Thus physical state prediction remained numerically small in absolute terms,
but the unchanged formal margin diagnostic rejected three trajectories. The
primary explicit-SVD and independent `lstsq` implementations agreed on all
gates and the route; maximum numerical difference was
`2.1316282072803006e-14`.

Compared with R8R16, the single added interaction reduced calibration passes
from `63/64` to `61/64` and increased maximum margin error from
`0.05171944884413282` to `0.09336026574612744`. This rules out only that
fixed feature. It does not show that all higher-order models fail or that any
missing physical sequence lacks authority.

## 5. Boundary after R8R17

The next design must be frozen without using R8R17 failed-row identity. A
genuinely higher-order sequence model cannot be identified from the same six
development rows without an explicit prior. The next zero-new-TSC boundary
therefore uses all ten measured codes only through prospectively specified
leave-one-code-out validation, fixed Boolean interaction features, fixed
regularization, and unchanged physical/formal gates. Missing physical
outcomes remain closed.

Any model PASS may authorize only a separately frozen fresh finite sentinel.
Every R8-family trajectory remains probe/control-development evidence and is
forbidden from expert, BC, DAgger, and RL data. Gate A remains blocked.
