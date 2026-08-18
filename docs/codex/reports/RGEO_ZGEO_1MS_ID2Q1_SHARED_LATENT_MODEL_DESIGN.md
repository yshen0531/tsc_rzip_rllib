# ID-2Q1 shared-latent model comparison design

## Scope

ID-2Q1 uses only the 40 primary K1 cells and 40 primary ID-2P1 cells. The
five replay trajectories are integrity evidence with zero fit weight. N1
calibration and holdout are forbidden fit inputs. There are 16 independent
whole-history families, split into four fixed folds holding two K1 and two P1
families each.

No new TSC, reset or plant advance is allowed.

## Candidates

Both candidates separate a time-indexed nominal continuation from a causal
response model. At every origin they consume exact current R_geo/Z_geo/Ip,
recent one/four-step velocity, actual-versus-issued current innovation
projected into the admitted p04/p07 action plane, and complete owned issued
action history. Future issued Card15 actions are known to the predictor;
future actual current/readback is forbidden. The current innovation is held
only as a causal origin feature and decays by the frozen factor `0.8` at each
predicted step; it is never refreshed from future truth.

1. `stable_shared_latent_ridge` uses fixed stable poles and a single shared
   increment map across horizons. Predictions at 1--8 ms are cumulative
   rollouts of those increments, not eight unrelated heads.
2. `stable_shared_latent_gru_residual` adds an eight-unit persistent causal
   GRU residual to the same backbone. Its hidden history is never rewritten
   during recenter evaluation. Three frozen seeds form an ensemble mean.

The comparison does not include a larger TCN, a direct policy, online weight
updates or label features.

## Evaluation

Each held family is evaluated from origins 16--26 at horizons 1--8. The gates
cover absolute endpoint p95/max error, matched baseline/probe response NRMSE,
all 16 held probe directions per fold, and p04/p07 signed action-ranking
regret over 16 desired R/Z directions. A zero-response/action-blind reference
is explicit. Candidate selection cannot trade a response improvement for an
unbounded endpoint regression.

A development PASS emits one frozen model artifact and may authorize only a
fresh calibration design plus a genuinely new blind whole-history holdout.
A FAIL stops same-data model enlargement and requires route review. Neither
result authorizes a tube, authority, recovery, controller, MPC, transport,
crossing, adaptation, expert data or RL.

Frozen config SHA-256:
`29b783aa311994a31d9dbfc741fa997b87f62ad468ffc5a84cd008e0f4040c05`.
