# R_geo/Z_geo 1 ms ID-2K1 factorized history/sign development result

Date: 2026-08-17 Asia/Shanghai

## Verdict

ID-2K1 completed with the frozen route
`ONE_MS_ID2K1_FACTORIZED_HISTORY_SIGN_DATA_PASS_STRUCTURED_MODEL_ONLY`.
This is a finite source-local development-data qualification PASS. It is not
a model, calibration, uncertainty-tube, authority, recovery, controller,
MPC, transport, crossing, adaptation or reachability result.

## Execution and independent evidence

- implementation revision:
  `8416bd6c5dd59e6b01c493aa58bf4b48a4c1433c`;
- server run directory:
  `rgeo_zgeo_1ms_id2k1_runs_20260817_8416bd6c`;
- 43/43 rollouts completed, comprising 40 uniquely weighted cells and three
  zero-extra-weight critical replays;
- 1,462/1,462 verified one-ms plant advances and 1,505 retained states;
- all eight whole-history families and all 32 probe cells completed;
- the required semantic inventory contains 7,525 files and
  88,633,850,620 bytes with digest
  `97ba08db00d12bc604396b32dbd794d3c415d7549b3402ce59d06c78fba9f158`;
- the complete server rollout tree occupies 90,028,813,364 bytes. The extra
  files are not silently included in the frozen required-artifact claim;
- primary result SHA-256:
  `a7a5f64a86118dd5002b9da44f7cf5e126571f30d6e6ef3d3005b369eb4e6643`;
- independent raw audit SHA-256:
  `69911aaa5d16b7f52381b0f7d211d51b0eee6377a11830dd00812e7183af8444`;
- independent audit passed with no failures and reproduced the required file
  count, byte count and inventory digest exactly.

All eight matched-prefix gates passed. The three critical replay pairs
(`h00/p07-minus`, `h02/p04-minus`, `h06/p07-minus`) were exact in checked
R_geo/Z_geo/Ip, 14-coil current, 48-wire current, action and semantic-artifact
fields. The independent audit did not infer physical identity from `sprsina`
byte identity.

## Descriptive response result

All 32 probe cells passed the frozen signal and Ip gates. Peak paired R/Z
norm ranged from `0.128188 mm` to `0.690277 mm`; the maximum paired absolute
Ip response was `50.1590 A`.

The new matrix directly rejects an odd/static simplification in this finite
domain:

- p04-plus peak R/Z response was `0.148907--0.151093 mm`, whereas p04-minus
  was `0.670910--0.677457 mm`;
- p07-plus was `0.128188--0.145822 mm`, whereas p07-minus was
  `0.684236--0.690277 mm`;
- under the frozen normalized full-tail construction, cosine between a plus
  response and the negated matched minus response was only
  `0.0613--0.2307`, while minus/plus tail norm ratio was
  `1.994--2.503`.

These are development-set descriptive calculations, not central-symmetry
gates, local Jacobians or control-authority claims. Peak response varied only
modestly among the eight conditioner histories within a fixed direction and
sign, but the complete trajectories remain distinct whole-history families.
That observation does not prove history independence and may not be used to
split siblings across folds.

The four probe trajectories per history gave descriptive numerical rank four,
with condition numbers `157.58--1004.81`. This is not an authority PASS and
does not justify inversion of that matrix for control.

## Data role and successor

The 40 unique cells are eligible only for development fitting. Critical
replays have zero extra fit weight. ID-2I1 and ID-2J0 remain diagnosis-only;
ID-2C2 remains consumed evaluator-only. No old calibration or holdout is
reopened.

The authorized successor is a separately frozen ID-2L1 comparison with:

1. exact Card15/queue/current propagation;
2. an explicit time-indexed nominal continuation;
3. stable low-order action-memory states;
4. causal sign/even and history/state interactions;
5. an optional small GRU or TCN residual only on top of that backbone;
6. whole-history held-family evaluation under teacher-forced one-step,
   1/2/4 ms truth recentering and stable/free multi-step rollout.

A development model PASS may authorize only fresh calibration design. A new
blind whole-history holdout remains mandatory before authority, recovery or
controller work.
