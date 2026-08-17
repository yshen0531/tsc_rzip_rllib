# R_geo/Z_geo 1 ms ID-2F1R1 repeated-context development result

Date: 2026-08-17 Asia/Shanghai

Source revision: `4e92c987f0452b23a25bb4336d8caf04c3b9173e`

Final route:
`ONE_MS_ID2F1R1_REPEATED_CONTEXT_DEVELOPMENT_PASS_MODEL_COMPARISON_ONLY`

## Execution and raw evidence

The frozen server campaign completed all 78 authentic rollouts: 39 unique
whole-history cells with two fresh replays per cell.  It made 78 reset calls,
2,652 advance attempts, 2,652 `gotsc` calls and 2,652 verified one-ms plant
advances, retaining 2,730 states.  The independent audit reparsed all raw
states and reproduced the primary counters and metrics.

The required inventory contains 13,650 files and 160,777,682,520 bytes with
digest
`8011fc16959bbe6caea4347b2a35140c14660c26b5f96d5db215352af1fa781f`.
No required artifact is missing.  The primary and independent compact hashes
are respectively
`897d0a8a44c305891d77e29c728d171cd8857869a91d00b3268cac39d6d1e655`
and
`d08c85ec3cd3b027ec2b00f1307c2adf9fb8176d47353ce5a823000d103647e5`.

All 39 replay pairs are exact in checked R_geo/Z_geo/R_mid/Ip, 14-coil,
48-wire, action and semantic-artifact fields.  The maximum checked numeric
difference is zero.

## Frozen development gates

The two-coordinate lag-16 virtual-action block has 2,652 rows, 32 columns,
rank 32, condition `3.1756126323207448` and minimum singular value
`5.099019513592784`.

Every direction/sign family passed the 25 micrometre signal gate.  Maximum
observed R/Z response norms by family were:

- p04 plus: `0.1466765503 mm`;
- p04 minus: `0.7414271561 mm`;
- p07 plus: `0.1609114287 mm`;
- p07 minus: `0.7497605262 mm`.

All arms passed the frozen 150 A baseline-relative Ip gate.  Event occurrence,
odd symmetry, linearity, superposition and mechanism attribution were not
gates and are not inferred from this PASS.

## Scientific meaning and next route

ID-2F1R1 is a finite, source-local, three-context development-data PASS.  Its
39 unique cells may now be used once, with replay members kept in the same
whole-history group and each unique cell receiving unit statistical weight,
for the separately frozen development model comparison.

The comparison must keep current R_geo/Z_geo/Ip as exact same-step
observations, use only causal observed/current/action history, allow candidate
future issued Card15 actions, and forbid future actual readback or future
plasma state.  It compares a stable low-order/LPV model, a small GRU, a causal
TCN and a probabilistic mixture or ensemble under identical leave-one-context-
out folds.  Absolute rolling/recursive prediction and evaluator-only matched-
baseline response metrics are both required; future baseline is not a model
input.

This PASS does not authorize calibration, ID-2C2 access, blind holdout,
controller safety, uncertainty tubes, recourse, MPC, transport/crossing,
adaptation, expert/Oracle/BC/DAgger/RL data or fixtures.  A model-development
PASS is still only a prerequisite for fresh calibration and independent
whole-context/history validation, not a control or reachability result.
