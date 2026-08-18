# ID-2P1 matched-factorial development result

## Verdict

ID-2P1 passed as
`ONE_MS_ID2P1_MATCHED_FACTORIAL_DEVELOPMENT_PASS_MODEL_COMPARISON_ONLY`.

The first background launch used the system Python and stopped on syntax
parsing before output creation, reset or TSC. The same frozen identity then
ran under the required existing server virtual environment. This was a
deployment/startup error with zero plant work, not a campaign retry after an
advance.

## Execution and raw evidence

- rollouts: 42/42;
- unique fit-weighted cells: 40;
- whole-history families: 8;
- reset / attempted / gotsc / verified advances: 42 / 1,428 / 1,428 / 1,428;
- retained states: 1,470;
- required artifacts: 7,350 files, 86,572,598,280 bytes;
- inventory digest:
  `8fc24f89ce739ca88985f127fd2bf2d0c9248b1cec18592e81ea03f62e1a4181`;
- matched prefixes: 8/8;
- critical replays: 2/2;
- signal and Ip probe gates: 32/32;
- peak paired R/Z norm range: 0.050240--0.742907 mm;
- maximum paired |Ip|: 50.1365 A.

The independent server process reparsed all 1,470 states and all 7,350
artifacts, reproduced the inventory, counters, prefix checks, replays and
response metrics, and reported zero failures.

Primary / independent / offline SHA-256:

- `8f747e04d8fbd9114615cfa65de436191c1f3245baeb4e1b620c86de71707331`;
- `0c4364a55993d433c4ca156dc956c9bc1698efbf3888e25b87b1d246b9dd124c`;
- `1d530b5d91486196b855445e2412be2b6eb06d54fb7de197199a814a3782b5e5`.

## Meaning

The 40 primary compact records are now eligible only as finite source-local
development-fit data. The two replay rows have zero additional fit weight.
Together with K1 they provide 16 independent history families and probe
durations 1/2/3 for a bounded two-candidate model comparison.

This PASS is not calibration, holdout, uncertainty-tube, authority, recovery,
controller, MPC, transport, crossing, adaptation, expert-data, RL or
reachability evidence. N1 calibration remains consumed redesign evidence and
is not training data.
