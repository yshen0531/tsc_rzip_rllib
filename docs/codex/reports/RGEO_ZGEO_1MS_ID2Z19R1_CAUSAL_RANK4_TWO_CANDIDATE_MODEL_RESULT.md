# ID-2Z19R1 causal rank-four two-candidate model result

## Execution identity

Server validation at checkpoint `4317cd2f` passed `16/16` focused tests and
`585/585` complete one-millisecond regression tests. The accepted preflight
route was `ONE_MS_ID2Z19R1_PREFIT_READINESS_PASS_FIT_AUTHORIZED`; it read 14
positive-weight development histories and two zero-weight replays, recovered
the complete signed Card15 action space at numerical rank four and made zero
TSC calls.

A first model launcher invocation used an incorrectly transcribed 40-character
source revision. It was stopped by exact PID after writing only a 2,982-byte
preflight file; the orphaned model child was also stopped explicitly. It
produced no result, OOF ledger, independent audit or selected model and is not
a scientific identity. Its remote log and partial output remain preserved.

The accepted v2 identity used the actual source revision
`4317cd2fc74d40bbe852a8aa1bea6299d79ed2db`. It emitted:

```text
result.json                 2f7c0acbec9438153b9481794be45a034d347d8a39a4cb76493983c4e498a214
oof_predictions.json        234e8826b93168f474c237e5a5fcf0e323083c2e311ece90124abaefb7e7358e
independent_audit.json       a977d36ea4b40b32a585e3161ca04c98efeb825ae7e4505b8452aecfbd79ca5e
preflight.json               a3e459c9c6202a216ff73ac5ce11a8687057ce8077ec18e76eda05d016af68a5
```

The independent no-refit evaluator passed with zero failures and reproduced
the no-selection result from all `9,408` OOF rows. Calibration and blind
holdout reads, reset calls, plant advances and new TSC calls were all zero.

## Scientific result

Neither frozen candidate was eligible. The structured rank-four stable-
memory model and the same backbone plus fixed TCN residual both failed:

```text
terminal R/Z velocity p95 gate                8/8 folds
terminal one-step increment p95 gate          8/8 folds
held-support gate                             1/8 folds
horizon-1 endpoint p95 gate                   3/8 folds
```

The support failure was confined to the held `baseline_full_f` family
(`43.45%` coverage); the other seven folds had `100%` held support and still
failed terminal increment/velocity. Across folds, R terminal-increment p95
was approximately `0.519--0.602 mm` for the structured model and
`0.522--0.605 mm` for the TCN model against the frozen `0.5 mm` cap. This is
not solely an OOD result.

Paired response NRMSE remained below the loose frozen `0.75` cap in every
signed fold (`0.124--0.272` structured, `0.125--0.311` TCN), and both models
improved response SSE over their independently refit action-blind baselines.
Those aggregate passes coexist with finite wrong-direction event rows and do
not repair the terminal failure. The TCN failed its relative selection gate:
its worst paired-response criterion regressed by `14.20%`, and its maximum
componentwise critical-metric regression was `35.86%` against the frozen
`10%` allowance.

Final route:

```text
ONE_MS_ID2Z19R1_NO_ELIGIBLE_DEVELOPMENT_MODEL_ONE_ATTRIBUTION_ONLY
```

No model artifact was emitted. The result closes c00--c03 calibration,
v00--v03 blind holdout, a third model, network expansion, grid search and
post-result gate changes. It does not reject the plant, authority, recovery
or final controller architecture. One zero-fit OOF attribution remains
authorized; the independent authority/recovery axis remains open.

