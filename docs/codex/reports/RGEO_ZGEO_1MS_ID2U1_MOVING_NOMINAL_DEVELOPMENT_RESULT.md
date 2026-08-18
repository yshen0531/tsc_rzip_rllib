# R_geo/Z_geo 1 ms ID-2U1 moving-nominal development result

Date: 2026-08-18

Source revision: `63d498c50e168d5bc2d207a6c37b2e739d9568a2`

Final route:

`ONE_MS_ID2U1_MOVING_NOMINAL_DEVELOPMENT_PASS_MODEL_COMPARISON_ONLY`

## Execution and evidence integrity

The first background launch used the system Python rather than the frozen
server virtual environment and stopped on Python syntax before creating the
output directory, resetting TSC, or advancing the plant. Its log is retained
as a deployment failure. The corrected v2 launch changed no config, code,
action, gate, or scientific identity.

The v2 campaign completed exactly 20/20 rollouts, 20 resets, 800/800 verified
one-ms advances, and 820 states. It retained 4,100 required artifacts totaling
`48,292,197,680` bytes. The full raw inventory digest is
`f42fd452c5b7fe0d718d0232371498b18b3b6068f58556f14dc859c68d979f94`.
All four matched-prefix groups passed, all 16 probe cells passed the signal
and Ip gates, and no calibration or blind-holdout record was read.

The independent server-side raw reconstruction passed over all 20 rollouts,
820 states, and 4,100 artifacts. The tracked primary result SHA-256 is
`297d32bfb5a945238150f5a951d4de5c6df2e28f16a3d13f816778ecc27cc3b4`;
the independent audit SHA-256 is
`bf3c68a26d94406e8c54c4bd96b6d3e621735d923ebdf1ef28c478ac0c6ffd62`.
The 23 directly copied compact JSON files have sorted name/byte/SHA inventory
digest `d095d5042df68cf6a7d0d9d31d55f4fc0861375f8a8ffd53fd08b4e13b230074`,
identical locally and on the server.

Server validation before the run passed 8/8 focused tests and 318/318 one-ms
tests. The corrected launch started with `164,537,294,848` free bytes; the
frozen storage estimate and residual-space gate passed.

## Development response geometry

All 16 paired probe responses were measurable. Peak R/Z norms ranged from
`0.080378 mm` to `0.711723 mm`, and maximum paired absolute Ip response ranged
from `23.904 A` to `43.360 A`.

The moving-nominal matrix localized the old hybrid behavior rather than
making it universal:

- `u00` (level 18, issue 24) retained a large minus-sign delayed response:
  p04-minus and p07-minus peaked at states 29 with `0.711723 mm` and
  `0.707847 mm`, while plus responses were about `0.081 mm`;
- `u02` (level 22, issue 24) had all four peaks near `0.092--0.098 mm` at
  state 26;
- `u04` and `u06` (issues 30, levels 18 and 22) had all four peaks near
  `0.091--0.106 mm` at state 32.

Thus a single smooth response map is not justified, but neither is a blanket
claim that p04/p07 gains reverse. The finite evidence supports an explicit
time/nominal-level/event-age/history guard and tests whether a persistent
causal model can predict the exceptional u00 delayed branch.

## Authorization boundary

The 20 compact trajectories are development-fit eligible. The two paced
calibration families `u01/u03` and two paced blind families `u05/u07` remain
unopened. The next stage may compare only the two prospectively frozen small
model classes and must use whole-family folds, exact one-ms observation
recentering, paired-response metrics, multi-horizon consistency, Ip/current
metrics, and OOD refusal. No development result may alter U1's PASS or open
calibration before a single model artifact and evaluator are frozen.

ID-2U1 is not a transition tube, authority, hold, recovery, controller, MPC,
waypoint/path, R_mid crossing, adaptation, expert-data, RL, or reachability
result.
