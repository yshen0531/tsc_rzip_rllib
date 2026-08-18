# ID-2S0 sequence-utility selector result

## Verdict

ID-2S0 completed on the server with zero TSC calls, zero resets, zero plant
advances, and zero fitted or updated models. The primary result and the
separate-process deterministic recomputation agree exactly. The frozen route
is `ONE_MS_ID2S0_SEQUENCE_SELECTOR_PASS_FOUR_BRANCH_DESIGN_ONLY`.

This is a no-fit candidate-nomination PASS, not plant, authority, tube,
recovery, controller, MPC, or reachability evidence.

## Frozen selection

The selector evaluated all `1820` four-element subsets of the sixteen
ordered two-arm candidates. It selected:

1. `p04_plus__then__p07_minus`
2. `p07_minus__then__p07_minus`
3. `p07_minus__then__p07_plus`
4. `p07_plus__then__p04_plus`

The minimum of the sixteen directional heuristic progresses was
`0.00004235400000000833 m` (`0.042354 mm`), the mean was
`0.00027537795584210505 m`, and the maximum selected-sample angular gap was
`142.34385602680211 deg`. The frozen gates were `0.00002 m` minimum progress
and an angular gap strictly below `180 deg`.

Every nominated 34-issue Card15 stream passed exact representability and the
per-coil `<= 0.3 A` adjacent-issue slew gate. The result contains sixteen
candidate streams and sixteen fixed additive response constructions.

## Evidence identity

- implementation revision: `d4ea132b5580414640c175b8f3d751b94f686f4a`
- config SHA-256:
  `aaed52b652c935bc6c8246a007af8b3be113b3489d418a236057a9f68086ecb2`
- primary result SHA-256:
  `e0a7e86ead036c55098877304d32adcfb7274f7b5371894b2b390c5fd0807801`
- independent audit SHA-256:
  `7dd86803e25ed868e0300deb540fb763731689a499d21a6939575af5528dbf3e`
- server tests: focused `6/6`; complete one-ms suite `278/278`

The full compact result and independent audit are retained under
`docs/codex/audits/rgeo_zgeo_1ms_id2s0_20260818_d4ea132b/`.

## Route

ID-2S0 PASS may authorize only a separately frozen four-branch TSC
development discriminator with a storage gate. That successor must measure
the selected sequences rather than treating the additive construction as a
plant prediction. It must retain zero fit/calibration/holdout/expert/RL
weight and must stop after the four branches and an independent raw audit.
