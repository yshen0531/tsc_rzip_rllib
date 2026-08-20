# ID-2Z21 moving-nominal temporal-control contract audit result

Date: 2026-08-20

Final route:
`ONE_MS_ID2Z21_SUSTAINED_ALLOCATION_NOT_READY_REDESIGN_ACTION_BASIS_OR_NOMINAL`

## Outcome

The server-side audit completed with zero TSC calls, zero plant advances, zero
model fits and zero calibration/blind-holdout reads. The focused suite passed
`10/10`; the independent implementation reproduced every load-bearing metric
and the exact failing route with no failures.

The audit failed exactly one frozen readiness gate. The actually executed
F/A/a/E/e increment matrix has numerical rank four but condition
`24.2899432952`, above the frozen maximum `10`. ID-2Z21 therefore does not
authorize a fresh campaign. The result is not changed by the fact that its
plant-response gates otherwise passed.

## Recomputed lineage

The independently reparsed ID-2Z20 `dev_hold` and tracked ID-2Z18 full-F
reference agree exactly through state 32. After state 32 their command
semantics differ: `dev_hold` keeps the root target exactly constant while
full-F continues changing its target each issue.

At state 48:

- held-center distance/speed: `26.8067849 mm / 0.587400442 m/s`;
- continuing-full-F distance/speed: `23.2073032 mm / 0.218018108 m/s`;
- held minus full-F: `+3.59948174 mm / +0.369382334 m/s`.

The ID-2Z20 terminal held continuation reaches worst
`35.5565202 mm / 0.567484121 m/s`; the ID-2Z18 full-F terminal window reaches
worst `28.2549188 mm / 0.416472444 m/s`. This directly confirms that the
failed held-center pulse grammar was not a moving-nominal residual test.

## Exact allocation result

Every F/A/a/E/e/H occurrence reproduced one exact 14-coil increment; H is
zero and the largest individual token component is 0.3 A. The nonzero token
singular values are:

```text
1.5519796571, 1.1051959436, 0.7501753672, 0.0638939185, ~0
```

The weak fourth direction is therefore real but poorly conditioned. It is
not a robust continuous coordinate merely because numerical rank is four.

Unconditional addition to a full-F issue is impossible:

| hypothetical sum | maximum component |
|---|---:|
| F + A | 0.600 A |
| F + a | 0.600 A |
| F + E | 0.450 A |
| F + e | 0.450 A |

Any successor design must choose, replace or time-share exact Card15 vertices
inside the per-issue slew polytope. It may not add and clip.

## Sustained plant response

All six signed pair families reached the preregistered persistent response and
terminal-velocity thresholds at their first common-prefix segment. Examples:

- d00 at 4 ms: `0.149638 mm`, velocity separation `0.052264 m/s`;
- d01 at 8 ms: `0.406663 mm`, `0.080677 m/s`;
- d02 at 8 ms: `0.420446 mm`, `0.072964 m/s`;
- d03 at 8 ms: `0.342999 mm`, `0.091352 m/s`.

The best two response vectors were d01/d03 at 8 ms, with condition
`9.35388352` and acute line angle `12.3844503 deg`. This is finite
control-relevant signal, but it is a narrow task-plane wedge rather than
strong two-axis authority.

The independent audit also found that d00/d04/d05 have byte-for-metric
identical admitted early response rows. Their pair IDs must not be counted as
three independent task-plane segments in the successor design. This is a
conservative reporting/support correction; it does not change ID-2Z21's
already failing route.

All fourteen predecessor development trajectories still have zero stationary
six-state captures. ID-2Z21 creates no capture, authority or recovery claim.

## Scientific interpretation

The result is not a failure of all sustained temporal action. It is a
readiness failure of treating the current five discrete tokens as a well-
conditioned continuous rank-four allocation basis. The evidence instead
supports two narrower facts:

1. exact discrete token replacement/time-sharing produces persistent response;
2. the presently observed task-plane directions are weakly separated and do
   not yet justify a fresh controller/data campaign under the frozen contract.

The next zero-TSC work must redesign the action representation and nominal
allocation. A defensible successor may treat exact token targets as discrete
vertices rather than invert the ill-conditioned rank-four matrix, but it must
deduplicate identical segments and prospectively demonstrate a materially
broader control-aligned response family. If that cannot be obtained from
existing qualified evidence, the action basis or takeover nominal changes
before any new TSC.

Primary result SHA-256:
`1898cdbfda0e7b790ae2342f7d062ca5d4e103b3b276a42da2d7f130da0a0e93`.

Independent audit SHA-256:
`1b2608a5109464e26c3e81c56cc8b4eb7b85dea05479ffff2d9079e13a901f03`.
