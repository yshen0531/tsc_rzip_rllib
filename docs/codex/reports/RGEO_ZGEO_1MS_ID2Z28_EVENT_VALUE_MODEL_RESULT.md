# ID-2Z28 bounded event/value model result

ID-2Z28 ran on the server from implementation revision
`ed316968f39bcb4aeb5cb94b796191a054b51a4c`. Server validation passed the
focused suite `9/9` and the complete one-millisecond suite `666/666`. The
stage made zero TSC calls and zero plant advances, read no calibration or
holdout identity, and fit exactly the one prospectively frozen finite FIR
development model.

The independent implementation reproduced the complete result with no
failure. The final route is
`ONE_MS_ID2Z28_MODEL_PASS_Q_CELL_CONTROL_UTILITY_FAIL_REDESIGN_ALLOCATION`.
This is a control-utility/design FAIL, not a model-validation, runtime,
deployment, raw-data, actuator, Authority-L0, capture or plant-reachability
failure.

## Model result

The phase-32 signed odd q_R/q_Z response kernel validated on the held-out
phase-40 families:

- scaled response RMSE: `0.0773842` (gate `0.12`);
- scaled absolute-error p95: `0.162804` (gate `0.20`);
- minimum R/Z direction cosine: `0.993997` (gate `0.98`);
- maximum terminal response-velocity error: `0.0257457 m/s` (gate `0.05 m/s`);
- maximum 64-direction h8 action-ranking regret: `0 m` (gate `0.02 mm`).

The model payload SHA-256 is
`6ba92078da96d770e1c079a6572f6c498c9ff029f86e5ce418d7e79e27f1827b`.
This is only a finite 1--8 ms, exactly recentered, development response model.
It has no calibrated uncertainty, long-rollout or controller qualification.

## Control-utility veto

All `390625` eight-token q-cell sequences were evaluated against both
matched center phases. The unique selected sequence was
`Z+ R- R- Z+ R- H H H`; its sign inverse was also rendered. The robust
worst normalized capture score changed from `4.88408056` to `4.65208609`, an
improvement of only `0.23199446` or `4.750013%`. The prospectively frozen
readiness requirement was `15%`.

All four selected/opposite phase-32/phase-40 Card15 streams were nevertheless
exactly executable: maximum issued slew was `0.300000000000011 A`, minimum
absolute-current headroom was `105.1 A`, and the eight-slot bridge returned
exactly to the qualified transition center. Thus the failure is not an
action-serialization problem. The present `0.50F`-centered q cell is
measurable and predictable, but too weak relative to the source-capture drift
to justify a real Authority sentinel.

The result and independent-audit SHA-256 values are respectively
`617d78d9177898edf677f1a5bc48ff64159effc46d7e5e39ed508c3ea2c44703`
and `1ee44aff9bafe6b8ec1b4d795767bf4067c33db93e30585af073a23660b22d8b`.

## Route decision

Do not run the nominated sequence, loosen the 15% gate, lengthen this FIR,
or add another model. Preserve the q kernel as finite shadow evidence.

The next bounded work is a zero-new-TSC task/terminal and action-allocation
realignment. It must explicitly distinguish source-centered capture, for
which the current cell is insufficient, from a small moving-nominal-relative
two-axis waypoint, for which the measured q response may be useful and which
is directly aligned with the eventual path-following goal.

That audit may nominate only one path: either a materially different
nominal-share/action cell for source capture, or a prospectively frozen
moving-reference development/calibration route. It may not relabel the
present source-capture FAIL as a PASS. Any real feedback execution still
requires a separately frozen exact-action/support/safety contract, fresh
model calibration and blind validation, Authority-L0, Recourse-L1 and the
hard interface before controller qualification.
