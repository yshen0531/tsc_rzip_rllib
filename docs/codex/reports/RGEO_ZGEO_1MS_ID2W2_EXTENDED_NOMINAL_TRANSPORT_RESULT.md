# R_geo/Z_geo 1 ms ID-2W2 extended nominal transport result

Date: 2026-08-19

Identity: `rgeo-zgeo-1ms-id2w2-extended-nominal-transport-v1`

Source revision: `1e496b7cb8920d8deabfad4df765056c86ae9e69`

Final route: `ONE_MS_ID2W2_EXECUTION_OR_INTERFACE_FAIL_STOP`

## Outcome

ID-2W2 performed one reset and 79 verified TSC advances, retaining states
0--79 and 400/400 artifacts for the realized prefix. It then stopped after
state 79 and before issue 79. No retry, cleanup action, return action or later
plant advance occurred. The independent full-raw audit passes with no
failures and reproduces the partial inventory digest
`223730fa0a78c4af255f15d3f00882bcfad6c21baa793f95c1caf31354531213`.

The stop was the frozen observed-current slew gate. Issue 78 requested the
exact p03 level-78 target with maximum issued per-coil delta `0.3 A`. Coil 14
readback changed from `-105.10000 A` to `-105.40001 A`, an exact observed
delta of `-0.30001 A`. The implementation therefore retained state 79 and
refused issue 79. This is an actuator/readback-interface gate result, not a
TSC runtime, solver, raw-corruption, paired-boundary, deployment, model,
controller, hold, recovery, waypoint or reachability result. The frozen route
is not changed to a scientific PASS or FAIL.

## Descriptive transport evidence

Although the prospective 80-step scientific gate was not evaluated, all 79
realized steps are valid route/design evidence. Relative to the 1100 ms source:

| state | R offset (mm) | Z offset (mm) | R/Z distance (mm) | Ip offset (A) |
| ---: | ---: | ---: | ---: | ---: |
| 32 | -12.6695 | +14.5491 | 19.2923 | +722.74 |
| 52 | -17.2119 | +16.4808 | 23.8299 | +1071.46 |
| 64 | -18.7892 | +15.2776 | 24.2165 | +1235.11 |
| 79 | -21.1937 | +11.1230 | 23.9352 | +1406.11 |

The minimum after state 32 occurred immediately at state 33 and was
`19.6412 mm`; no observed post-state-32 state entered the frozen 15 mm
corridor. At state 79 the one-ms velocity was approximately
`(-0.1477, -0.3638) m/s`. Continued p03 increasingly reduced the positive-Z
error but kept moving R in the wrong absolute direction. The unissued final
step could not have established the required three-state corridor and is not
needed to decide that blind continuation of this exact staircase should stop.

These facts do not prove that p03 is globally useless. They show that
stride-one continuation alone is not a source-return/hold policy and that its
R/Z trade changes with action age.

## Next finite route

The p03-only ladder now gets one final, bounded braking discriminator rather
than another longer ramp. Two canonical-source branches will replay the
independently audited ID-2W2 prefix and then:

1. freeze at p03 level 52; or
2. freeze at p03 level 64.

Each branch will observe a finite tail through a common later horizon and
test whether either attained command produces a bounded terminal speed/net-
motion window while remaining inside the exact current/Ip/geometry envelope.
Both target levels occur before the observed-slew stop. A clean failure stops
the p03-only nominal/hold route and moves action-basis design to a different
allocation; it will not authorize another p03 hold-level ladder.

## Evidence

- Compact realized trajectory:
  `docs/codex/audits/rgeo_zgeo_1ms_id2w2_20260819_1e496b7c/p03_minus_stride1_levels1_through79.json`
- Primary result:
  `docs/codex/audits/rgeo_zgeo_1ms_id2w2_20260819_1e496b7c/result.json`
- Independent audit:
  `docs/codex/audits/rgeo_zgeo_1ms_id2w2_20260819_1e496b7c/independent_raw_audit.json`
- Offline preflight:
  `docs/codex/audits/rgeo_zgeo_1ms_id2w2_20260819_1e496b7c/offline_preflight.json`
- Frozen design:
  `docs/codex/reports/RGEO_ZGEO_1MS_ID2W2_EXTENDED_NOMINAL_TRANSPORT_DESIGN.md`
