# R_geo/Z_geo 1 ms ID-2U2 bounded causal model comparison result

Date: 2026-08-18

Implementation revision: `45265ef072180fefe6b29de5cf7576dfe3834fa2`

Final route:

`ONE_MS_ID2U2_NO_ELIGIBLE_CAUSAL_MODEL_REVIEW_REQUIRED`

## Execution and evidence integrity

ID-2U2 ran on the server in the existing project virtual environment. The
focused suite passed `10/10` and the complete one-ms suite passed `328/328`.
Offline preflight loaded exactly the four development families
`u00/u02/u04/u06`, twenty compact trajectories, and the rank-three executed
residual-action subspace.

The primary comparison performed eight preregistered whole-family fold fits
and emitted no final full-fit model. It ran zero TSC calls, zero resets, and
zero plant advances, and read no calibration or blind family. The separate-
process deterministic recomputation reproduced the complete primary result
exactly.

- stage config SHA-256:
  `a7e8c628afeb5335baf3ed321bdf1361883ca104e3daa5731fd76036d649b681`;
- primary result SHA-256:
  `30f303ecd35b21399d3c894f15dfa0f4c3e6c212d5a5f09eabe7eb647ac495a8`;
- independent audit SHA-256:
  `c7a92cc351ae064fb6aceb38aff215098e0c6bd0a54ad647b63754e215f27d05`;
- server log SHA-256:
  `2ca846d882d452877ca87a0c246fd913b4b4d58dfb2b9a6d8dd93a2d9f39fa81`.

Remote evidence remains at
`/home/yangshen0711/tsc_all/tsc_rzip_rllib/rgeo_zgeo_1ms_id2u2_45265ef0`
and the log at
`/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/id2u2_20260818_45265ef0.log`.
There was no runtime, package, input, actuator, queue, raw, or reporting
failure.

## Frozen model result

Neither candidate was eligible.

The `stable_local_event_mixture` had mean/worst held-family paired-response
NRMSE `1.055527 / 1.141862`, minimum peak-direction cosine `-0.979216`, and
maximum time-resolved ranking regret `1.0`:

- `hold_u00`: response, direction and ranking failed; both minus branches
  were predicted in the wrong R/Z half-plane;
- `hold_u02`: support, response, ranking and absolute-p95 failed; all four
  directions were positive, but the causal-prefix distance was about
  `968.18` against an `11.20` support threshold;
- `hold_u04`: all four directions were positive, but response magnitude and
  ranking failed;
- `hold_u06`: all four directions were positive, but response, ranking and
  early absolute-p95 failed.

The `stable_local_event_gru_residual` regressed the mean/worst response NRMSE
to `2.412078 / 4.119342`, with minimum cosine `-0.934156`. It repaired no
fold and added absolute or unique-event failures. Increasing recurrent
capacity is therefore not justified by this result.

Absolute R/Z continuation was not the sole failure. The local model's
held-family R/Z p95 errors were generally sub-millimetre, while paired
response magnitude/ranking failed broadly. Conversely, `u00` retained the
specific wrong-direction minus branch and `u02` was explicitly outside the
training causal-action-memory support. Model and support failures are both
present.

## Route diagnosis

The four ID-2U1 development families are all `frontloaded`. They vary nominal
level (`18/22`) and probe issue (`24/30`) but contain no independent arrival-
pace factor. Every prospective `paced` history was reserved for unopened
calibration or blind use. Thus ID-2U2 asked a history-conditioned model to
generalize arrival-history effects without one development example of that
factor. Counts of twenty trajectories or hundreds of endpoints do not fix
that four-family support geometry.

This does not invalidate exact one-ms observation, the moving nominal,
machine learning, or the high-level history-conditioned rolling-control
architecture. It rejects these two small candidates under the frozen
four-family development contract. It also shows that another capacity
increase on the same data would repeat the earlier model ladder.

## Recommended next decision

Pause before another fit or TSC run. The recommended successor is a new,
prospectively frozen development-data stage with exactly one additional
arrival-history family at each existing `(nominal level, probe issue)`
corner: four new whole-history families and twenty matched
baseline/p04+/p04-/p07+/p07- streams. The arrival schedules must differ from
both the existing frontloaded histories and the still-unopened
`u01/u03/u05/u07` schedules, and must pass a zero-TSC exact Card15, slew,
storage, prefix and event-age preflight first.

This preserves `u01/u03` as paced calibration and `u05/u07` as blind
holdout. If the new data pass, the eight development families may support a
new bounded comparison of the same low-capacity local/event and small
persistent-history classes. The next comparison must use whole-family folds
that test both held arrival history and held level/time corner. It must not
silently widen the GRU or weaken ID-2U2's result.

ID-2U2 is not an uncertainty tube, authority, hold, recovery, controller,
MPC, waypoint/path, R_mid crossing, adaptation, expert-data, RL, or
reachability result. No calibration or blind outcome has been consumed.
