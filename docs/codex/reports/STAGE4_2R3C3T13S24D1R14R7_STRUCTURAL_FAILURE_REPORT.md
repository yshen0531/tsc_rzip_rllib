# Stage4.2R3c3T13S24D1R14R7 structural failure report

## Result

D1R14R7 did not produce a model-fit result. Its prospectively frozen
independent-per-lag architecture is structurally undefined in a required
whole-pair fold:

```text
CAUSAL_RESPONSE_MODEL_PIPELINE_STRUCTURAL_FAIL_NO_MODEL_RESULT
```

This is a model/pipeline design failure. It is not a runtime-environment,
raw-corruption, plant-restart, control, MPC, or TSC result. No output/model,
new raw, controller, Ray, `gotsc`, TSC, or plant step was created.

## Evidence

The final installed package was checkpoint `5a17fe0`, revision
`r42r3c3t13s24d1r14r7_causal_response_model_v3_independent_route_schema`.
It passed 1,126/1,126 local tests and 1,126/1,126 staging/installed server
tests with one expected server skip.

The final invocation log is:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
stage4_2r3c3t13s24d1r14r7_offline_20260804_5a17fe0_v3.log
```

All 320 R2/R4/R6 raw files and all frozen result hashes/routes authenticated
before the fit began. The invocation then stopped in the first nested
candidate evaluation with:

```text
ValueError: R7 prediction requests an untrained lag
```

The intended output path is absent. Direct source recomputation shows why:

```text
normal-slew physical pairs        2 pairs / horizon 35
weak-slew physical pairs          2 pairs / horizon 37
```

In an inner whole-pair fold that holds the remaining weak-slew pair, the two
training pairs can both end at state 35. R7 v1 fit an independent response
head for every relative lag, so no training row exists for weak-slew states
36 and 37. The frozen design had no prospective extrapolation rule; silently
copying or inventing a terminal head would change the model semantics.

Two earlier pre-result incidents are separate:

1. Staging package v1 passed checksums/focused tests but its full test suite
   found omitted historical root launchers. The full-closure v2 package fixed
   deployment completeness before installation or R7 execution.
2. The first v2 offline call expected a top-level independent `route`; the
   frozen source schema uses `independent_route` plus
   `official_route_reproduced=true`. It stopped before output or fitting.
   Package v3 added exact schema tests without changing model semantics.

## Classification and next action

```text
runtime/environment error                         no
accepted package/import/deployment error          no
pre-execution packaging closure bug               yes; v1 staging only
pre-fit source-schema authentication bug          yes; v2, zero output
raw/snapshot corruption                           no
statistics/reporting error                        no result to summarize
frozen model architecture coverage defect         yes
real control / plant / restart / MPC conclusion   none; not run
```

D1R14R7 v1 is frozen and may not resume with a changed terminal rule. The
next stage must use a new identity and a prospectively frozen continuous-lag
model whose temporal basis is fitted across all observed lags and is defined
for states 36/37 even when those two lags are absent from an inner training
fold. The response/tube/geometry gates remain unchanged.

