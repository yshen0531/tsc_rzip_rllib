# R_geo/Z_geo 1 ms ID-2F1R1 repeated-context development design

Date: 2026-08-17 Asia/Shanghai

Identity: `rgeo-zgeo-1ms-id2f1r1-repeated-context-development-v1`

## Superseded preflight identity

ID-2F1 v1 remains frozen as a zero-TSC action-history-support design FAIL.
Its server-focused test reconstructed a 2,496 by 32 lag-16 virtual-action
block with rank 28, condition infinity and zero minimum singular value. No
gate was weakened and no plant advance occurred.

The cause is finite observation support: an issue-18 conditioner in a
32-issue trajectory is observed at only fourteen lag ages. Moving the probe
or adding more durations at the same late issue does not supply the two
missing ages. A server-side zero-plant design calculation showed that
retaining the same actions and extending the horizon to 34 issues yields
rank 32, condition `3.1756126323207443` and minimum singular value
`5.099019513592783`.

ID-2F1R1 is a new prospective identity. It changes only the observation
horizon and corresponding budgets. It does not reinterpret ID-2F1 v1 as a
PASS.

## Frozen campaign

The 39 unique whole-history cells, two fresh replays per cell, exact
p03-minus stride-one nominal, three contexts, issue-18 one-issue conditioner,
and issue-22 p04/p07 signed durations 1/2/4 are unchanged from ID-2F1 v1.
Every rollout now issues 34 one-ms actions and retains states 0 through 34.
The final two actions hold the exact active nominal and provide the missing
late action ages; they do not introduce a new primitive.

Budgets are 78 rollouts, 78 reset calls, 2,652 advance attempts, 2,652
`gotsc` calls, 2,652 verified plant advances and 2,730 retained states.
Retry after any advance attempt remains forbidden.

## Unchanged contracts and gates

All ID-2F1 causal observability, same-step paired-boundary R_geo/Z_geo,
exact Ip, actual 14-dimensional Card15, 0.3 A per-step slew, absolute-current,
limiter, Ip, raw integrity, replay, family signal and data-use contracts are
unchanged. Both conditioner and probe require their own pre-issue clearance.
Every successor still passes the frozen empirical step cap and outer hard
envelope before another issue.

The campaign is development-fit eligible only if all 78 trajectories and
2,730 states complete, all 39 replay pairs pass, the lag-16 input block is
rank 32 with condition at most 100, every p04/p07 direction-sign family has
at least one response arm of at least 25 micrometres, and every arm remains
within 150 A baseline-relative Ip response. Event occurrence, symmetry,
linearity, superposition and mechanism labels remain non-gates.

## Data and authorization boundary

A complete primary and independent raw PASS permits only whole-history
grouped development model comparison. Calibration, ID-2C2 evaluator access,
blind holdout, controller safety, tube, recourse, constrained control,
transport, crossing, adaptation, expert/Oracle/BC/DAgger/RL and fixture use
remain forbidden.

The run is server-only and uncompressed. It requires at least 400 GB free,
reserves at most 200 GB for new raw and requires at least 200 GB estimated
free afterward. The output path must not exist.
