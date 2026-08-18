# R_geo/Z_geo 1 ms ID-2U0 nominal-realignment preflight result

Date: 2026-08-18

Source revision: `a2fe7532dc36332b1730355c9b701a7246ebd7e5`

Final route:

`ONE_MS_ID2U0_NOMINAL_REALIGNMENT_ACTION_GRAMMAR_PASS_U1_DESIGN_ONLY`

## Evidence identity

The server-side primary result is tracked at
`docs/codex/audits/rgeo_zgeo_1ms_id2u0_20260818_a2fe7532/result.json` with
SHA-256
`81f5e37172d7c39d076c7161b0d1b99ab32ebf588dc2716e468226bd1a96f65a`.
The separate-process exact recomputation is `independent_audit.json` in the
same directory, SHA-256
`ad81b3a6292b0b8fedd540aafc3b86cb1b34179d278e91ce6391a2d44945c974`.
It reports `audit_passed=true` and no failures.

ID-2U0 executed zero TSC calls, zero resets, zero plant advances, fit or
trained zero models, and read zero holdout records. Server validation passed
the seven focused tests and all `310/310` one-ms tests. The latter completed
in `127.371 s`.

## Reproduced route facts

- ID-2C1's selected nominal remains `p03_minus_stride1`, with increments at
  every issue 1 through 31. It reduced terminal source R/Z norm from
  `29.314321 mm` for q0 to `19.292295 mm`, a `34.188157%` reduction, while
  maximum source-relative absolute Ip change was `722.743 A`.
- The later held-after-15 identification corridor is not the selected moving
  nominal. At issues 24 and 30 it is respectively 9 and 15 nominal levels
  behind the selected schedule.
- All 16 P1 responses above `0.5 mm` occurred at absolute state 27. The
  largest response outside state 27 was `0.150561 mm`.
- The early and late p04+ direct h1/h2 responses agree closely. The aligned
  h3 R-response difference is `0.687151 mm`, while the h4 difference is
  `0.007680 mm`. This is a return-edge/history event contrast, not evidence
  of a smooth local-gain sign reversal.

## Frozen prospective campaign

The exact Card15 construction contains 8 whole-history groups and 40 streams:
4 development groups, 2 calibration groups, and 2 blind-holdout groups. It
uses a moving-nominal `pause -> two-issue probe -> exact return -> resume`
grammar, so no residual action is silently added to a p03 step that already
uses the full `0.3 A` per-coil slew. Every proposed target passed exact
Card15, absolute-current, and adjacent-slew construction checks.

This PASS authorizes only a separately frozen fresh ID-2U1 campaign with
server-side execution and independent raw audit. It is not response,
transition-tube, authority, hold, recovery, controller, MPC, waypoint,
crossing, adaptation, expert-data, RL, or reachability evidence.

## Server storage action

Before any fresh plant campaign, the server had only `14 GB` available.
Two exact old raw directories were removed after verifying that ID-2J0 had
prospectively declared them unavailable after cleanup and that their compact
results and independent raw audits are tracked:

- `artifacts/server_runs/rgeo_zgeo_1ms_id2h1_20260817_3a057ac3` (`79 GB`);
- `artifacts/server_runs/rgeo_zgeo_1ms_id2i1_20260817_ea84ad0d` (`63 GB`).

The deletion is not recoverable on the server. No ID-2F1R1 development,
ID-2P1, or other raw directory was removed. Available space after cleanup
was `155 GB`.
