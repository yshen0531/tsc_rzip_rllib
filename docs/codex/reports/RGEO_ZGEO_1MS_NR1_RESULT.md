# R_geo/Z_geo 1 ms NR1 qualification result

Final route: `ONE_MS_NR1R2_INTERFACE_QUALIFIED`

Implementation checkpoint: `8580ac1`

## Result

The restarted 1 ms interface qualification completed at fixed 1100 ms with:

```text
authentic rollouts                         6/6
authentic plant advances                 24/24
raw states                               30/30
exact Card15/action checks               24/24
exact observed-slew checks               24/24
signed first-effect components           56/56
maximum issued single-turn step           0.3 A
maximum observed single-turn step         0.3 A
maximum pulse return/hold readback error     0 A
primary/replay parsed differences            0
```

All states retained valid paired same-boundary `R_geo/Z_geo`, limiter and Ip.
Across the finite campaign, maximum displacement from source was
`0.0028504745 m` in R_geo and `0.0031940035 m` in Z_geo; maximum Ip change
was `29.294 A`. These are interface-sentinel observations, not tracking or
authority claims.

The primary verdict SHA-256 is
`92877b959eb0237efcebd9e5b2ae246021c9da53de0b268644215b37f2790853`.
The independent verdict SHA-256 is
`0c887aa5d3728f00e01cd9c41d86a1647d46491bf71294bbee5da02e0379cad4`.
The server run directory is:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/rgeo_zgeo_1ms_nr1_runs/rgeo_zgeo_1ms_nr1r2_command_readback_20260813_8580ac1
```

Its 219 files total 1,796,246,218 bytes and remain on the server. Only compact
JSON/log evidence was copied into
`docs/codex/audits/rgeo_zgeo_1ms_nr1r2_result_20260813_8580ac1/`.

## Preceding safe stops

Two separate fresh identities stopped safely after nine advances each:

1. NR1 at `129a091` subtracted binary64 current reconstructions and falsely
   classified the exact PF3L `-0.300000 A` change as above 0.3 A. The
   zero-TSC forensic route was
   `ONE_MS_NR1_BINARY64_FALSE_SLEW_STOP_CONFIRMED`.
2. NR1R1 at `2685710` correctly accepted the observed pulse but mixed the
   biased PF3L readback `-135.30001 A` with nominal q0 command `-135.0 A`
   before return. The exact command-to-command and readback-to-readback
   changes were both 0.3 A; only the mixed coordinate was 0.30001 A. The
   zero-TSC forensic route was
   `ONE_MS_NR1R1_COMMAND_READBACK_MIX_CONFIRMED`.

Neither run was resumed or overwritten. Both are numerical/action-coordinate
interface defects, not actual current-limit, TSC, boundary, model, planner or
closed-loop failures.

NR1R2 separately validates exact-decimal adjacent Card15 commands and exact-
decimal adjacent TSC readbacks. It adds no tolerance or hidden reserve:
equality at 0.3 A is accepted, and any exact excess remains rejected.

## Validation evidence

- local focused tests: `19/19`;
- local complete suite: `1680/1680`;
- installed-server focused tests: `19/19`;
- installed-server complete suite: `1667` pass, one expected skip;
- deployed-file SHA-256 values matched local files exactly;
- Linux `bash -n`, Python compilation and public imports passed;
- zero-TSC offline route: `ONE_MS_NR1R2_OFFLINE_PASS`;
- independent raw route: `ONE_MS_NR1R2_INDEPENDENT_PASS`;
- all three primary/replay pairs had zero parsed difference in geometry,
  R_mid, Ip, all 14 coil currents and the full wire-current vector.

## Claim boundary and next gate

This result qualifies only the fixed-source, direct k-to-k+1 1 ms interface,
exact command/readback slew enforcement, reversible pulse and deterministic
prefix replay. It does not qualify arbitrary restart branching, an observer,
world model, finite work domain, controller, NMPC, tracking, teacher, RL, or
physical-machine deployment.

All NR1-family records have `interface_validation` identity and are forever
forbidden from model fitting, training and expert data. NR2 must use a fresh,
prospectively frozen identification/calibration/holdout campaign and explicitly
separate the exact actuator coordinate from learned plasma/history residuals.
