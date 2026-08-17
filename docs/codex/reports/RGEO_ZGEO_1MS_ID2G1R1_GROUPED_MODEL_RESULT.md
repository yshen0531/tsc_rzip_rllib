# R_geo/Z_geo 1 ms ID-2G1R1 grouped model result

Date: 2026-08-17 Asia/Shanghai

Final route:
`ONE_MS_ID2G1R1_GROUPED_MODEL_PASS_FRESH_CALIBRATION_DESIGN_ONLY`

ID-2G1R1 completed on the server at source revision
`ebdb42a01e5ddcc49317df940cdec21abf698795`.  It ran zero TSC calls,
resets or plant advances and read zero ID-2C2, calibration or holdout
records.  An independent raw re-extraction and full deterministic refit
reproduced the primary result with maximum numeric difference zero.

The corrected action-blind comparator has response NRMSE exactly `1.0`.
The causal TCN was the frozen selection:

- three leave-one-context-out response NRMSE values were `0.71370094`,
  `0.66436756` and `0.66486466`;
- mean response NRMSE was `0.68097772`, a `31.9022%` improvement over the
  action-blind comparator;
- positive peak-direction counts were `10/12`, `11/12` and `10/12`;
- worst fold recursive p95 absolute errors were `0.359981 mm R`,
  `0.181205 mm Z` and `10.9505 A Ip`.

The stable LPV and probabilistic ensemble candidates were also eligible,
with mean response NRMSE `0.73987248` and `0.73137246`; neither was within
the frozen five-percent simplicity tie of the TCN.  The small GRU was not
eligible and achieved mean response NRMSE `0.94240979`.

Evidence SHA-256 values are:

- primary result:
  `6d2389d7d7a5d86eea221cadd4fe386b6f95a734405496b36eab07a372856afa`;
- independent audit:
  `614b01bdc8b422bc1ced2472da1ccac3f5d9445ca8baed1c431f8a0dbc1ad83e`;
- selected TCN artifact:
  `14502175c95d1d0b5b36846a35af249af0041405eb6c013f099caa4dd18d176b`;
- canonical allowed-causal dataset content:
  `bfb01c258160c55533ae9ec9fc2580c2f1a556c48df3e7067f80021e5ceaaf85`.

The server dataset itself was not downloaded and is forbidden as a
repository fixture.  The earlier `7841a173` output is retained only as an
evaluator/reporting bug record: its action-blind recursion used the real
future issued action.  The selected weights did not change, but only the
corrected `ebdb42a0` evidence is valid for routing.

This is a finite three-context development-model selection PASS.  It is not
uncertainty calibration, blind holdout, a transition tube, authority,
recourse, controller, MPC or closed-loop qualification.  It authorizes only
a separately frozen fresh whole-history calibration design.
