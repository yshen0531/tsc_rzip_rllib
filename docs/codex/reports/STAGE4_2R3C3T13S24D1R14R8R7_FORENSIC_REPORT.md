# Stage4.2R3c3T13S24D1R14R8R7 forensic report

## Final classification

Stage4.2R3c3T13S24D1R14R8R7 is final as:

```text
FRESH_MULTIPULSE_STATIC_OBSERVER_INTERACTION_PASS_MPC_DESIGN_REQUIRED
```

The prospectively frozen static observer, fixed short-horizon response model,
and combined tube passed every baseline and fresh multipulse gate.  This is a
finite fresh-interaction model qualification PASS.  It is not a controller,
MPC, formal-control, Gate A, expert-data, BC, DAgger, residual-RL, or global
plant-reachability result.  Adaptation remained disabled and all 48 R8R7
trajectories are forbidden from every expert or learning dataset.

## Frozen identity and validation

```text
branch
  codex/stage4_2r3c3t13s24-sequential-transition
design checkpoint
  6287ff6
implementation checkpoint
  a1a60a9
execution-package checkpoint
  d8d231e
independent inventory reporting fix
  a39c5a9
pre-action runtime hotfix
  4a8b558
runtime hotfix audit checkpoint
  7de7966
declared files / direct-copy total in execution package
  993 / 995
```

The execution package was reconstructed by direct file copy into a new empty
local directory.  All declared hashes, the stage self-test, and focused tests
passed from that copy.  No local or remote archive operation was used.

Local validation used the project virtual environment and loaded the existing
Windows `resource` shim before unittest collection.  The final hotfix source
state passed:

```text
focused tests                                      11 / 11
complete repository tests                       1219 / 1219
local failures / errors / skips                     0 / 0 / 0
```

The direct-copy server staging package first passed package verification,
`bash -n`, compilation, focused `9/9`, and the complete installed suite
`1217/1217` with one expected server skip.  After the two narrow hotfixes, the
server staging source passed focused `11/11` and the complete suite
`1219/1219`, again with one expected server skip.  Every server Python command
used the existing server virtual environment.

## Exact server identity

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14r8r7_runs/
stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_sentinel_20260807_d8d231e_v1
```

The accepted stage manifest retained the original execution-package
fingerprint:

```text
cb816e6473e17c6b8f8bdaf2e67564af381cde756ef0b4eb3526ed1a46ada34c
```

The retry used the separately installed and audited semantics-preserving
campaign source rather than mutating that accepted package in place:

```text
fixed campaign source SHA-256
  eb8c9437bf85c44c4c7b6843fafb8e7026d1cf5010e11d0a65ab7a87ad8aaf02
fixed independent audit SHA-256
  ea8f4b5c8711a101869c2edfdb20c204d63a90a50f0a192b20d574586326284f
```

The fixed campaign supplies an accepted historical R4 issue slot only to the
inherited constructor and immediately restores the frozen R8R7 clock
`(10,14,18,22)` in the overriding controller.  It changes no spec, action,
model, tube, acceptance gate, physical timing, or experiment identity.

## Preserved pre-action failure

The first phase-two invocation created 32 strict failure files, all before
controller construction returned:

```text
files / bytes
  32 / 145407
inventory digest
  7cadf53a6870980802009eef71e3d7c8e5c2707eb446d85f125851e239af160d
post-reset states per file
  1
trace rows / action events / plant advances
  0 / 0 / 0
common failure
  ValueError("D1R14R4 per-spec issue schedule changed")
```

The complete files were authenticated and moved recoverably, without content
change, under the run's `runtime_bug_evidence/pre_hotfix_4a8b558/failed_raw`
directory before retry.  They are not counted as scientific multipulse
trajectories.  The original primary reporter also could not serialize an
unavailable `inf` maximum; the hotfix writes JSON `null` instead.  These are a
pre-action implementation error and a reporting error, not TSC, restart,
safety, controller-design, plant, response-model, MPC, or reachability
evidence.

## Authentic execution and raw integrity

Phase one ran the 16 fresh zero-future-action baselines.  After its primary
and independent raw/model gates passed, phase two ran exactly the same 32
frozen multipulse specifications once under the audited hotfix.

```text
baseline runtime/full-horizon/raw pass             16 / 16
multipulse runtime/full-horizon/raw pass            32 / 32
total valid new authentic raw                       48
restart/source-state/source-trace/calibration        48 / 48
finite raw                                           48 / 48
forbidden trace count                                      0
multipulse exact issue count                       128 / 128
multipulse exact cancellation count                128 / 128
maximum issue/cancel normalized increment
  0.14074074074074103 / 0.14074074074074103
maximum total normalized action                     0.648149691358026
maximum current utilization                         0.3924
```

Raw inventories independently agreed exactly:

```text
baseline files / bytes
  16 / 487298
baseline inventory digest
  46df626a462dfdbfe7cdf9138a50b6b19c03f0ae5e8bb18cf18c6fcbe05c01a5
multipulse files / bytes
  32 / 1068664
multipulse inventory digest
  d8435c8cd61fd082e143d79a3628ad2274780faefc6b676367df917355f49e31
```

Formal tracking was explicitly diagnostic only.  It passed `6/16` baseline
and `12/32` multipulse trajectories and is not reinterpreted as the R8R7
scientific gate or as MPC evidence.

## Frozen model gates

The predictor used only the byte-authenticated R8R6 static observer and the
fixed R8R1 PCA4/RBF-median-times-two/ridge-0.1 40 ms response fit trained on
the immutable 912-row R8 bank.  It performed no R8R7 refit, model selection,
innovation/adaptation, future measurement, pair/history label, or matched-
baseline-future lookup.

```text
baseline point rows                                  64 / 64
baseline tube rows                                   64 / 64
baseline context gates                               16 / 16 at 4/4
multipulse point rows                               128 / 128
multipulse tube rows                                128 / 128
multipulse context gates                             16 / 16 at 8/8
direction gates                                       4 / 4 at 32/32
sign gates                                            2 / 2 at 64/64
finite-exclusion violations                                 0
```

Maximum point errors `[R,Z,vR,vZ,Ip]` in physical units were:

```text
baseline
  [0.0001621501, 0.0002140065, 0.0051867258, 0.0079233521, 7.3286289]
multipulse
  [0.0001802686, 0.0002340930, 0.0059655368, 0.0088394172, 7.9203529]
```

The maximum scaled point errors were `0.0792335213` and `0.0883941718`.

## Independent agreement and fingerprints

The structurally independent audits separately authenticated raw inventories,
reconstructed predictions and tube containment, and reproduced the primary
outcomes.  Primary numerical agreement, outcome agreement, and artifact hash
agreement are all true.

```text
response model
  d2bcca31e135c4faf99a93d64391fdc96bb5de44b8705d177e2219c6c000e84e
response tube
  c31b4d3b84bdc7ab9f399bd3563798989c94e5f373536b42ccb19f8ef06be128
combined tube
  f5afa50a149ce858187833aade6e5ef91433c42016fc7d70986543deecd74759
baseline primary detailed
  64bf4fe446f75b8e12d8b21c6d95eed1cdf1e29d32dee1a828288f89db073104
baseline primary summary
  0c407bc120403024c81d1e7347edddb2f0d41f1baa227ec6d9337ddd0068663e
multipulse raw primary
  37204019206752038244c2b5c8300905a112709d05c3048525e3793f42826972
multipulse primary detailed
  0c64315cbc0c4b08563777bda7ac92378ad51f03a11b9827d9ad6fa7047af2f4
multipulse primary summary
  c67314a48829d5c6d528ac61cfb06b813fb6a21be8b1122bb55bde0aa516d6aa
multipulse independent
  6334c08a1acbc2b6c72cf6207c5210bf9d72fe52f79d271d5ac35c875058a9ae
final report
  9ca6afce52442c1b7470cb8ff13a2eac4aab32de1e05a898d206f5fe76e01005
stage manifest
  ae89fb2df01cd6758676baa895880e2005a1f8967c62ea4ae671ab61ea771e24
final state
  04f643e09f414c5d5a305f1a3584450e12e5a39e8d062d454480df3c8d95fe7e
```

Compact summaries, independent audits, state, manifest, and complete phase
logs are retained under:

```text
docs/codex/audits/
stage4_2r3c3t13s24d1r14r8r7_20260807_d8d231e/
```

No raw trajectory or snapshot was downloaded.

## Handoff boundary

R8R7 demonstrates that the selected static observer and frozen response model
remain accurate and bounded across fresh, causal, exact-Card15 four-pulse
interactions in the finite 16-context envelope.  It does not demonstrate a
receding-horizon optimizer, feedback replanning, solver fallback in closed
loop, formal tracking, continuous robustness, noise/disturbance recovery,
long hold, or residual authority.

The only authorized next step is to freeze a separately identified genuine
receding-horizon MPC design before implementation or outcome inspection.  A
future controller must then pass the deterministic core and every finite
robustness axis in `CURRENT_TASK.md` before Gate A can be claimed.  Learning
remains blocked.
