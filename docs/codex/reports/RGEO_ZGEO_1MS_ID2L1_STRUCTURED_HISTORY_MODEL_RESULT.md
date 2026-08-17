# R_geo/Z_geo 1 ms ID-2L1 structured history model result

Date: 2026-08-17 Asia/Shanghai

## Verdict

ID-2L1 is final as
`ONE_MS_ID2L1_STRUCTURED_MODEL_FAIL_ROUTE_REVIEW`.

Twenty whole-history fold models were fitted on the 40 unique ID-2K1
development cells. No candidate passed every preregistered development gate,
so no selected-model artifact was emitted and no calibration, holdout,
authority, recovery or controller stage was authorized.

This is a development model-structure FAIL. It is not a TSC, plant,
actuator, raw-data, runtime, calibration, holdout, controller, MPC or
reachability result.

## Execution and reproducibility

- model implementation revision:
  `a6d509b52ed78b554317e11e05c16585129cbd3f`;
- reporting-only launcher follow-up:
  `1fe0a3eb`;
- server output:
  `rgeo_zgeo_1ms_id2l1_model_a6d509b5`;
- server tests: 10/10 focused and 203/203 complete one-ms regression tests;
- preflight: 40 unique cells, eight whole-history families, exact rank-three
  Card15 action basis, zero resets/TSC/plant advances;
- primary result SHA-256:
  `af67b3915afead8c5df2846982c90c4b41ef17aa448a0904b48e24157e7969fd`;
- independent full-refit SHA-256:
  `52a5f8aedaad5a8347b0b9fca9d112c9b482f418b6e9585b563511017034176b`;
- allowed-dataset file SHA-256:
  `fb671210f5ef4c794006ed8d54c193fe6125a8e7e453703b2e080e62b1c525ca`;
- canonical allowed-dataset identity:
  `88137c184be6793eaa405360f51fe16773a1d671c54ee49caa243222f19ea24d`;
- independent refit passed with no failures and maximum numeric difference
  `0.0`;
- ID-2I1/ID-2J0/ID-2C2/calibration/holdout records read: zero;
- reset, TSC and plant-advance count: zero.

The original launcher used `set -e`, so the primary's correct scientific exit
code 2 stopped the shell before independent audit. The preserved primary was
then independently refitted directly. A reporting-only launcher fix now
allows exit code 2 to reach the auditor and returns it afterward. It did not
change data, model, folds, seeds, gates, metrics or the final route.

## Candidate results

### Action-blind comparator

The comparator had mean paired-response NRMSE `1.0` and positive peak
direction `0/32`. Its absolute errors were modest because the time-indexed
nominal captured much of the common drift. This confirms why absolute error
alone is not a sufficient action-model gate.

### Stable signed memory

- mean paired-response NRMSE: `1.080908`;
- positive peak direction: `32/32`;
- per-fold NRMSE: `1.098148, 1.095230, 1.066253, 1.064000`.

The signed model got response direction right but could not represent the
large finite plus/minus magnitude asymmetry.

### Stable signed/even memory

This was the clear best development candidate:

- mean paired-response NRMSE: `0.602347`;
- per-fold NRMSE:
  `0.611556, 0.610980, 0.593700, 0.593153`;
- positive peak direction: `32/32`;
- state-25 free-rollout p95 R error:
  `0.440--0.475 mm`;
- state-25 free-rollout p95 Z error:
  `0.158--0.167 mm`;
- state-25 free-rollout p95 Ip error:
  `7.26--17.65 A`.

It passed paired-response, action-blind-improvement, direction, free-rollout
and catastrophic gates. It nevertheless failed the unchanged short-horizon
absolute gates:

- 1 ms recentered p95 R error was `0.394--0.426 mm`, above the frozen
  `0.300 mm` cap in all four folds;
- in the two composite-history folds, 2 ms recentered p95 R error was about
  `0.791 mm`, above the frozen `0.550 mm` cap.

The gate is not weakened after observing this near miss. The result instead
separates a useful signed/even action-response model from an insufficient
nominal/event-edge/short-time correction model.

### Contextual quadratic model

The high-dimensional contextual interaction overfit badly:

- mean paired-response NRMSE: `7.257824`;
- positive peak direction: `12/32`;
- free R error reached about `4.87--5.41 mm`.

It is rejected, not rescued by regularization tuning after result.

### Structured GRU residual

The width-10 GRU residual improved some teacher-forced absolute errors but
damaged the action response:

- mean paired-response NRMSE: `1.812266`;
- positive peak direction: `28/32`;
- every fold regressed relative to the signed/even backbone.

This is direct evidence against enlarging or promoting the current neural
residual. It does not prove all recurrent residuals are useless.

## Interpretation and next recommendation

The failure is no longer primarily “the action response has the wrong sign.”
The stable signed/even backbone learned the finite held-family response well
enough to pass all response and free-branch gates. The remaining blocker is
the stricter absolute R increment immediately after exact truth recentering,
especially in composite conditioner histories. A large context feature map
and a generic GRU both made this worse.

The next recommended stage is a separately frozen zero-new-TSC, zero-fit
ID-2M0 attribution of the already produced fold predictions. It should locate
the exact issue/event ages responsible for the 1/2 ms R error, separate the
shared time nominal from conditioner/probe edge residual, and compare:

1. baseline-only nominal error;
2. signed/even action-response error;
3. exact-current innovation and recent R/Z/Ip velocity at each failed origin;
4. conditioner issue/return versus probe issue/return events;
5. direct one/two-step correction versus accumulated nine-step response.

If the miss is common nominal drift, the successor should be a bounded
causal innovation correction around the signed/even backbone. If it is tied
to discrete issue/return edges, the successor should use a small hybrid event
head or direct short-horizon head. If neither cleanly explains the error, the
route should stop for new matched transition data rather than another larger
network.

No new TSC or model fit should begin before that attribution and route choice.

## Server cleanup

After the ID-2K1 compact trajectories, primary result, independent raw audit
and ID-2L1 dataset/result were preserved locally and pushed, the exact server
subtree
`rgeo_zgeo_1ms_id2k1_runs_20260817_8416bd6c/rollouts`
was deleted under the user's cleanup authorization. It occupied
90,028,813,364 bytes and is not recoverable from the server. The server's
ID-2K1 top-level compact JSON, primary result and independent audit remain;
free space rose to 160,514,199,552 bytes.
