# Fixed-1000 F0 finite feedback result

## Verdict

F0 completed all four authentic rollouts and all 256 authorized plant
advances. Execution, exact Card15 action, hard envelope, fresh q0 reference
and path-A replay integrity passed. The frozen scientific route is
`ONE_MS_NR1000F0_FINITE_Q0_RELATIVE_TRACKING_FAIL_REDESIGN`.

This is a controller-policy FAIL, not a runtime, raw, reference, replay or
plant-interface failure. It does not revoke A0 Authority-L0 or V0's finite
development/calibration/blind response-set result.

## Measured result

All six measured position checkpoints satisfied the 0.35-mm norm and
0.30-mm per-axis gates:

- path A errors at states 32/44/56 were `0.012232`, `0.018027` and
  `0.150662 mm`;
- path B errors were `0.007333`, `0.018487` and `0.165757 mm`.

The first two decisions on each path had positive frozen-V0 progress. At
issue 48, however, the exact observed errors to the final command were
already only `0.336073/0.338297 mm`. Every available full macro was predicted
to worsen the checkpoint error. F0 nevertheless selected the least-bad macro,
giving frozen predicted progress `-0.001864/-0.003741 mm`; these two failures
trigger the preregistered route.

The minimal correction is therefore a controller grammar change, not a gate
change: deadband membership must admit an explicit q0 no-op, while outside
the deadband an active macro must have strictly positive predicted progress or
the controller must refuse before issuing it.

## Integrity and reporting correction

The independent raw audit passed after a reporting-only schema correction.
The initial audit treated post-run state folders as preissue snapshots and
also compared raw keys `current_a_tsc/wire_a` as if the compact aliases were
missing. Direct recomputation established zero raw-versus-compact and
raw-versus-frozen difference for all 14 coil and 48 wire values; geqdsk,
coil-current and wire-current hashes matched 65/65. State folders 0--63 carry
the runner-rewritten outgoing inputa, which is independently checked by exact
Card15 fields, while the online compact retains the preissue inputa identity.
The failed audit is preserved as
`independent_audit_before_raw_schema_fix.json`; no TSC was rerun.

Final independent counts are 260 raw states, 256 action checks and 252
observed-slew checks with zero failures. The primary and independent SHA-256
values are `ab9c16a1ebf7bf8c854d6b56e0695a461870c9258bee0c2d9a990c4f37248a0e`
and `e78291db93959bee756dea45d8be3234639a1101a29c7a4da1f11466776f4c25`.

## Claim boundary and next route

F0 does not qualify arbitrary paths, absolute hold, Recourse-L1, capture or
R_mid crossing. It closes only the always-issue-one-full-macro version of the
three-checkpoint policy. One separately frozen F1 may test explicit deadband
abstention with the same byte-fixed V0 and gates; no refit, interval widening
or result-dependent command change is allowed.
