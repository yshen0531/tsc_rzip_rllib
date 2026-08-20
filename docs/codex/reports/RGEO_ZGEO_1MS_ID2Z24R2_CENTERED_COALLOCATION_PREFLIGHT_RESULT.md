# ID2Z24R2 centered co-allocation preflight result

## Outcome

ID2Z24R2 passed its server-executed, zero-TSC, zero-fit preflight and the
structurally separate recomputation:

`ONE_MS_ID2Z24R2_CENTERED_COALLOCATION_PREFLIGHT_PASS_CAMPAIGN_DESIGN_ONLY`

The server ran the focused suite `7/7` and the complete one-millisecond suite
`633/633` before the formal preflight. The formal run made zero TSC calls,
zero plant advances, fit zero models, and read no calibration or holdout.

## Exact result

- implementation revision: `6a17ed8a989b320ca25253f6714887b56513a9ff`
- config SHA-256: `2ec1a2ec8de0e4abda50cd0203c9f7f3ee327f14ddb8aa7ee08b3391393bf17c`
- design SHA-256: `915e5137c01977ce2c5ae0632f18aeae77fb1db83e1bbee38339067eafd0324e`
- primary SHA-256: `5fa4e8dd76d1de7c1f5d3186f066dcd134704a3fa69919f8b57faca877647612`
- independent SHA-256: `43c24e64734b9ed1f72854b7d966884bc34a6a28f79f5aac2c5420365f2eb511`
- independently selected nominal share: `0.50`
- all tested shares `0.50, 0.45, 0.40, 0.35, 0.30, 0.25` passed
- selected cell residual rank: `3`
- selected condition range: `1.15429283681721--1.1795306341960452`
- selected maximum issued slew: `0.30000000000001137 A`
- selected minimum absolute-current headroom: `108.7 A`
- all 13 prospective static streams returned to the exact center bytes

The bridge is not the failed v1 repeated `8+8` construction and not the
failed R1 single overloaded finish. Each branch holds `N +/- r` for eight
issues, then uses eight prospectively fixed Decimal/Card15 targets to return
to the independently generated center endpoint. Every intermediate issue is
checked under the unchanged slew and current gates.

## Scientific interpretation and authorization

This PASS establishes only that the centered action cell and the exact return
bridge are digitally executable. It does not observe a new plant response and
does not establish D0 learning readiness, positive span, Authority-L0,
capture, Recourse-L1, or a controller.

It authorizes one separate ID2Z25 campaign with the already fixed maximum of
15 complete 65-advance rollouts: a matched centered baseline, a zero-fit
full-F diagnostic, twelve phase/axis/sign streams, and one zero-fit replay.
The twelve sibling streams and centered baseline are prospectively eligible
only as simulator-development data; replay and full-F diagnostic carry zero
fit weight. No threshold, phase, direction, duration, or data role may be
changed after a plant result.

## Decision record

The project deliberately retained both earlier zero-TSC failures. ID2Z24 v1
showed that numerically symmetric repeated Card15 increments do not guarantee
byte-exact cumulative return. ID2Z24R1 showed that postponing all correction
to the final slot requires `0.4--1.0 A`. R2 distributes the same exact
endpoint over the predeclared return interval; it does not weaken any gate or
reinterpret either failure.
