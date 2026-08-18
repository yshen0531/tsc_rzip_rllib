# ID-2R1 f03 exact-replay design

## Question

ID-2R0 found that the fixed no-fit local diagnostic is accurate inside the
thirteen supported schedule families, while `f03` is a singleton schedule
stratum with four Q1R1 wrong-way predictions and no integrity replay. ID-2R1
asks one narrow question: are the original `f03` baseline and four signed
p04/p07 probe trajectories exactly repeatable from the canonical 1100 ms
source under the same complete causal prefix and Card15 action schedule?

This is not a data-expansion or model-training campaign. All five new records
have zero fit, calibration, holdout, expert, and RL weight.

## Frozen campaign

The campaign contains exactly five rollouts:

1. `f03__baseline__fresh_r1`;
2. `f03__p04_minus_i24_d2__fresh_r1`;
3. `f03__p04_plus_i24_d2__fresh_r1`;
4. `f03__p07_minus_i24_d2__fresh_r1`;
5. `f03__p07_plus_i24_d2__fresh_r1`.

Each rollout starts from the authentic canonical 1100 ms source, executes the
exact ID-2P1 `f03` issue stream through state 34, and then stops. The budget is
five resets, 170 issue attempts/gotsc calls/verified advances, 175 retained
states, and 875 required artifacts. Retry after any advance attempt is
forbidden. No new action, target, timing, duration, queue, or effect semantic
is introduced.

Before TSC, the stage binds ID-2P1's config, PASS result, independent raw
audit, all five original compact rows, and ID-2R0's result and independent
audit. The server storage gate requires at least 24 GB free, reserves a 12 GB
maximum estimate, and requires at least 12 GB estimated free afterward.
No archive or local raw download is allowed.

## Gates

Every rollout retains the existing one-ms paired-boundary, Ip, Card15, slew,
absolute-current, limiter, queue/effect, inner-clearance, empirical successor,
and outer-envelope gates. Invalid boundary or any interface/runtime/raw error
fails closed before the next issue.

For every fresh/original pair, all 35 state clocks, same-step paired-boundary
R_geo/Z_geo/R_mid, Ip, fourteen actual coil currents, forty-eight wire
currents, all 34 issued Card15 fields, and the four semantic artifact hashes
must match at the already frozen ID-2P1 repeatability tolerances. `sprsina`
must exist and be hashed but is not required to be byte-identical. The five
fresh cells must also retain exact matched prefixes through issue 24, and the
four paired-response time series must reproduce their original ID-2P1 values.

## Routes and boundary

- Any storage or offline/input failure stops before TSC.
- Any execution, interface, runtime, or hard-envelope failure stops before
  the next issue and preserves partial raw.
- Any missing artifact or independent-audit failure is a raw-integrity FAIL.
- Any deterministic replay or response mismatch routes to deep review; it is
  not silently converted into training noise.
- Only complete exact replay routes to
  `ONE_MS_ID2R1_F03_EXACT_REPLAY_PASS_SEQUENCE_AUTHORITY_DESIGN_ONLY`.

A PASS confirms repeatability only for this finite source/history/action
identity. It may authorize a separately frozen canonical-prefix finite
sequence-control-utility shooting design. It does not authorize model fitting,
calibration, a transition tube, authority, recovery, controller, MPC,
transport, R_mid crossing, online adaptation, expert data, or RL.

