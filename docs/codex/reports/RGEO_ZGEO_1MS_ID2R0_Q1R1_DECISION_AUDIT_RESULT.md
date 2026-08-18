# ID-2R0 Q1R1 decision-audit result

## Verdict

ID-2R0 completed on the server with route
`ONE_MS_ID2R0_CRITICAL_SINGLETON_F03_EXACT_REPLAY_REQUIRED`.
The separate-process deterministic audit passed. The run performed zero new
TSC calls, resets, plant advances, candidate comparisons, model payloads, or
N1/holdout reads.

This route corrects the Q1R1 family attribution and chooses a minimal replay
discriminator. It is not a model, authority, recovery, controller, MPC, or
reachability result.

## Reproduced evidence

- The original Q1R1 aggregate and final FAIL were reproduced exactly.
- `14,080` explicit prediction rows and `1,024` paired-response rows were
  persisted with explicit fold, family, cell, origin, and horizon identities.
- The frozen, label-free, no-fit nearest-history diagnostic supported `52/64`
  probe cells. All `52/52` supported peak directions were positive, supported
  response NRMSE was `0.0331969598`, and the largest complete-family action
  ranking regret was `0.0207499131`.
- The twelve unsupported cells are exactly the four p04/p07 signed actions in
  each singleton schedule stratum `f01`, `f03`, and `f05`.
- Q1R1's four q03 ridge wrong-way responses belong to `f03`. That schedule
  stratum has one family and no integrity replay. The previously proposed
  `h01/h03/h05` bridge is withdrawn.

The measured peak vector set was not a positive span in any of the sixteen
families: maximum angular gaps were `303.709`--`327.656` degrees. When all
1--8 ms response samples were retained, all sixteen finite vector sets were
positive spans with gaps `85.787`--`116.782` degrees. This is descriptive
evidence that action utility is sequence- and timing-dependent; it is not a
controllability proof.

## Execution and integrity

The exact deployed bytes passed `9/9` focused tests and `262/262` complete
one-ms repository tests in the existing server virtual environment. Direct
transfer initially lost the launcher's executable bit; that attempt stopped
at the shell before preflight and before any audit computation. The same
hashed launcher was then invoked explicitly with `bash`, without changing
the stage semantics.

Evidence hashes:

- `result.json`: `0eaffe3134e2220ed1a6dfa7c127f318402709951864d5831d132d90e8cdf7f9`
- `predictions.json`: `2eda25889c53ac0b7fa32b13eb2738a33aeeaa25b7422cec79263abfea01dfab`
- `independent_audit.json`: `9a0338d0116ed00a3703820f1888a9d74baf4d9075534c71e6b85c8726f4bab5`

## Route consequence

The next evidence identity is one fresh exact replay of the complete `f03`
baseline and each of its four p04/p07 signed probe cells. These five records
have zero fit weight and answer only whether the anomalous finite response is
repeatable under the exact canonical prefix and action schedule. A replay
PASS may authorize only a separately frozen sequence-control-utility shooting
design. A mismatch stops for route review. It does not authorize another
global model, calibration, authority, recovery, or control.

