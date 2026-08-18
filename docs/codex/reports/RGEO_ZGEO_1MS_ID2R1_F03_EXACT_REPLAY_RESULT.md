# ID-2R1 f03 exact-replay result

## Verdict

ID-2R1 completed with route
`ONE_MS_ID2R1_F03_EXACT_REPLAY_PASS_SEQUENCE_AUTHORITY_DESIGN_ONLY`.
All five authentic fresh rollouts completed: five resets, `170/170` issue
attempts, gotsc calls, and verified one-ms advances, and 175 retained states.
The full raw inventory contains 875 required files and `10,306,261,700`
bytes with digest
`fbb43eee64d7d94e5a7d88801dce8d3d16a7b03287d70a7a4bf69fbb290f9f1b`.

Every fresh baseline/probe pair reproduced its original ID-2P1 trajectory
with zero maximum difference in paired-boundary R_geo/Z_geo/R_mid, Ip,
fourteen actual coil currents, and forty-eight wire currents. All four
matched prefixes passed and all four complete paired-response time series
had exactly zero R/Z/Ip difference. The `f03` anomaly is therefore a
repeatable finite TSC response under this exact source, history, schedule,
and action identity; it is not a single-sample numerical fluctuation.

All fresh records retain zero fit, calibration, holdout, expert, and RL
weight. This is not an authority, recovery, controller, MPC, or reachability
PASS.

## Independent audit correction

The initial independent audit recomputed all 875 raw files, counters,
outgoing Card15 fields, paired boundary values, coil/wire currents, matched
prefixes, and paired responses, but reported `REPLAY_RECOMPUTE`. Its raw
parser compared each retained directory's post-issue `inputa` hash with the
compact state's pre-issue active `inputa` hash. The runner intentionally
rewrites that file with the outgoing issue after recording the compact state.

Reporting-only revision `dfba6f6dbd20b75b8d86cdf4bcdfca393d1148c5`
preserved the failed audit and all raw, changed no action or scientific gate,
and reran no TSC. It audits outgoing `inputa` against all 170 frozen action
fields, checks the final active `inputa`, and retains statewise hash checks
for geqdsk and coil/wire artifacts. The corrected independent raw audit
passed with zero failures and reproduced the PASS route.

Evidence hashes:

- primary result: `f71b19f0ab80f2643a3f1b369412df5a35e1995305c088653aac6e924239190f`;
- preserved initial independent FAIL:
  `8ea1afdd65b7ea76546e690d36b6e4552b3706ad281733fc7dae1c97bfa0d418`;
- corrected independent PASS:
  `a79a26cdaf36255232897281a9307c46f0f0ffc43fc5040e4735dc29727b9c34`.

Server validation passed `10/10` focused and `272/272` complete one-ms tests
after the reporting correction. No local project test was run.

## Route consequence

The next step is not another global response model. It is a bounded,
canonical-prefix, time-resolved sequence-control-utility design. It must use
the exact executable p04/p07 Card15 grammar, distinguish no-fit candidate
selection from real-TSC branch evidence, and cap real branches according to
the remaining server space. Its purpose is to determine whether short action
and return sequences provide useful two-axis directional progress before
another surrogate, calibration, or controller is considered.

