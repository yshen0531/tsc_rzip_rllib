# ID-2N1 fresh calibration and unopened blind holdout result

## 1. Frozen identity and execution

ID-2N1 ran once on the server from source revision
`410689abb572b1601928717fc1675ad4a265549d` with stage-config SHA-256
`4b41320e6e79840b5d2234f3bfa7a9a77e0606f0d0e9cf624274b42ed2f64d08`.
The selected ID-2M1 model remained byte-frozen at canonical SHA-256
`681c26da4829170ce166c86db47362f0365f6cb22a26d419463667777e6fae73`.
No coefficient, feature, calibration gate, or action schedule was changed.

The calibration phase completed all 14 rollouts and 476 verified 1 ms plant
advances. The written raw inventory contains 490 states and 2,450 required
files, totalling 28,857,532,760 bytes, with inventory digest
`30e9da0f7553c6bce4107e92a298ec7f1f6786ea1ec8cc1b36c622aad91ee017`.
There are no missing required artifacts. The independent server-side raw
reparse passed with zero failures and reproduced the calibration, counters,
inventory, primary route, and verdict.

The result/calibration/independent/offline file SHA-256 values are:

```text
result.json                 fbb734bf53f98f32c94e7c473d9919d900803dbdb09bbdd147efd597e1b8421e
calibration.json            a1001567bf5b9cee81997807bf33d5f2bcb31e293d4f34783518def2f5fe5f97
independent_raw_audit.json  e307ac02358107e92ff2d7ce08a7e36bacf5efd684c49aea6f9dfdcfcef6f706
offline_preflight.json      4744d123519db7b2e6bdf4248fd6ad0e751e4b00ef6763bfec3ca008e7a98d71
```

The final frozen route is
`ONE_MS_ID2N1_CALIBRATION_MODEL_OR_TUBE_FAIL_HOLDOUT_UNOPENED`.
The four holdout families were never executed.

## 2. Scientific gates

The finite signal and Ip gates passed, but both the short-horizon tube-cap
gate and paired-response gate failed.

The calibrated R half-widths for horizons 1--4 were respectively
`1.7273, 1.6249, 1.5631, 1.5116 mm`, all above the frozen `1.5 mm` cap.
The corresponding maximum R errors were
`1.3819, 1.2999, 1.2504, 1.2093 mm`. Horizons 5--8 remained below their
`3 mm` cap, and all Z/Ip tube caps passed. This is a real fresh-history
short-horizon absolute-model/tube failure; it is not an invitation to widen
the cap after observing the data.

The more decisive failure is action-conditioned response generalization:

```text
combined paired-response NRMSE        2.843308   (required <= 0.75)
positive peak directions                  6/8    (required 8/8)
c01 p04-plus peak cosine              -0.907326
c01 p07-minus peak cosine             -0.740289
```

Family response NRMSE ranged from `2.6889` to `4.8705`. Thus nominal drift
alone cannot explain the result. A read-only server recomputation of the
frozen model and compact trajectories localized representative errors:

- for `c01 p04-plus`, the first paired successor was approximately
  `[+0.6631, -0.2799] mm`, while the model predicted
  `[-0.0464, -0.0016] mm`;
- for `c01 p07-minus`, the second paired successor was approximately
  `[+0.0978, +0.0316] mm`, while the model predicted
  `[-0.6127, +0.2771] mm`;
- in `c00/c02`, similar two-issue probes produced different delayed
  return/tail phase, while the fixed event convolution retained the wrong
  signed tail.

These are finite, source-local observations. They show that the selected
time-indexed nominal plus fixed signed/even event-memory model does not
generalize across the fresh history/duration/issue-time combinations. They
do not prove global stochasticity, plant unreachability, or that a properly
history-conditioned learned model cannot work.

## 3. Correct classification

This is not a packaging, deployment, runtime, solver, Card15, queue,
paired-boundary, raw-corruption, repeatability, reporting, controller, MPC,
or closed-loop failure. Exact current R_geo/Z_geo/Ip remains available before
every action. The missing quantity is the future response under a new causal
history, and the frozen event-memory representation is insufficient for it.

ID-2M1 remains a valid development PASS on its original whole-history folds;
ID-2N1 is the independent fresh calibration rejection that prevents that
development result from becoming a qualified model/tube. The holdout was
correctly kept unopened and must not be run under this failed identity.

## 4. Recommended route adjustment

Do not widen the observed tubes, repair ID-2M1 on calibration data and call
the old holdout blind, continue a hand-coded event ladder, or begin authority,
recovery, MPC, adaptation, or RL.

The calibration trajectories are now consumed redesign/development evidence.
The scheduled but unrun ID-2N1 holdout is also no longer an appropriate blind
test for a successor designed with knowledge of this matrix; it should remain
unrun and a later model should receive a newly frozen calibration and blind
whole-history holdout.

The next model comparison should use machine learning for the unresolved
mapping rather than require complete physical attribution. It should be
small and prospectively bounded:

1. use exact current R_geo/Z_geo/Ip, recent finite differences, actual/readback
   coil current, issued Card15 history, and explicit queue/effect age as causal
   inputs;
2. preserve an explicit nominal head, but predict 1--8 ms action-conditioned
   response with direct multi-horizon heads so a wrong recursive tail is not
   silently compounded;
3. compare at most two clean candidates: a stable low-order state-space/TCN
   residual and a small causal GRU/TCN encoder with corrected persistent-history
   semantics; neither may use context, direction, sign, duration, or source IDs
   as privileged labels;
4. split and weight complete history families, and retain both absolute and
   matched-baseline effect/hold/return/tail gates;
5. only a whole-family development PASS may open a newly generated calibration
   and untouched blind holdout. Authority and recovery remain separate AND
   gates after model/tube validation.

This is a model-representation and data-generalization decision point. The
overall architecture—exact actuator, exact 1 ms observations, causal learned
history state, calibrated uncertainty, then constrained rolling control—still
fits the evidence. The fixed-1100-ms two-axis waypoint and repeated R_mid
crossing goal is unchanged and remains far beyond the source-local validation
completed here.
