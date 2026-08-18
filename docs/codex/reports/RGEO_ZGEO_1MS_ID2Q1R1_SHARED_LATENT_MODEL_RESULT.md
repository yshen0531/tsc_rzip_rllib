# ID-2Q1R1 shared-latent model result

## Verdict

ID-2Q1R1 is final as
`ONE_MS_ID2Q1R1_NO_ELIGIBLE_SHARED_LATENT_MODEL_REDESIGN`.

### Reporting erratum (2026-08-18)

The evaluator stored `peak_cosines` and `family_ranking_regret` in sorted
`family_id` order without storing those IDs beside the arrays. The original
prose below therefore misassigned the family names. In q03 the four ridge
wrong-way responses belong to `f03`, not `h03`. In q01 the ridge family
ranking regrets `0.642/0.847/0.024/0.013` map to
`f01/f05/h01/h05`. The proposed `h01/h03/h05` bridge is withdrawn.

This is a reporting/attribution correction only. The result JSON, frozen
metrics, gates, final FAIL, and absence of a model payload are unchanged.
The separately frozen ID-2R0 audit records explicit family IDs before any
new TSC or model decision.

The server fit the two frozen candidates on the 80 primary K1+P1 cells in
four whole-history folds. It ran zero TSC calls, resets or plant advances and
read no N1 fit records. A separate server process retrained every frozen fold
and reproduced the result and absence of a model payload exactly.

Primary and independent SHA-256 are:

- `c60e79c1eeba021573d501493e4fd057132aaf438f7c0a6e159f7a0eda2d262b`;
- `734286c62b23eee2dcda6e3ef03fe8517c4ddafc82a665fbb084108b5cfc2ee4`.

## Candidate evidence

The stable ridge response NRMSE by fold was `0.8813`, `1.2827`, `1.1060`,
and `1.0552` (mean `1.0813`). Peak direction was positive for `60/64`; all
four wrong directions occurred in held family `f03`. Maximum action-ranking
regret reached `0.8470` in fold q01 and belongs to `f05` under the corrected
sorted-family mapping.

The eight-unit GRU residual did not repair generalization. Its fold response
NRMSE was `0.6681`, `1.5627`, `0.9864`, and `1.4439` (mean `1.1653`), with
`55/64` positive peak directions. Maximum action-ranking regret was `0.9569`.
Thus the neural residual improved one fold but materially regressed the
others.

Absolute endpoint errors were not the main failure. Most short-horizon p95
gates passed; the decisive failures were held-history response magnitude,
direction and action ranking. The scaled 104-feature design was also poorly
supported: fold conditions were `6.24e9`--`8.47e9`, far above the frozen
`1e6` cap. The response failures remain even if that condition gate is
ignored.

## Meaning and stop

ID-2P1 successfully supplied new duration/timing families, but the frozen
global shared-response maps still do not predict several K1 causal histories.
This is a finite source-local model/support failure, not runtime, raw,
actuator, TSC, calibration, controller, authority or reachability evidence.
No model was selected and fresh calibration remains unopened.

The same-data model ladder stops here. The next recommended discriminator is
a bounded zero-new-TSC attribution/support audit, not a larger network. It
should persist per-family predictions, compute blockwise rank and causal
history distances, and compare a support-gated local/nearest-history
diagnostic with the failed global maps. Its result must choose prospectively
between (a) a low-dimensional local mixture/LPV successor when nearby causal
support is predictive, (b) a targeted matched bridge campaign around
correctly identified unsupported strata when support is absent, or (c)
earlier qualification of canonical-prefix TSC branch shooting when neither learned
route is reliable. This recommendation is not yet authorized or implemented.
