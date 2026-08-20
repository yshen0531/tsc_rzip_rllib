# ID-2Z29 moving-reference waypoint preflight result

ID-2Z29 ran from implementation revision
`e7cb104b0e4d7260533d28134937264ac3ac6402` after server-focused `5/5` and
complete one-millisecond `671/671` tests passed. It ran zero TSC, zero plant
advances and fit no new model. The independent implementation reproduced the
result with no failure.

Final route:
`ONE_MS_ID2Z29_MOVING_REFERENCE_0P1MM_PREFLIGHT_PASS_FRESH_CALIBRATION_AND_SENTINEL_DESIGN_ONLY`.

Across all eight target directions, exhaustive frozen-sequence evaluation
gave maximum predicted path error `0.0175054 mm`, maximum endpoint error
`0.0152630 mm`, minimum target-direction progress `0.0957568 mm`, and maximum
Ip response `25.6767 A`. All were inside the prospectively frozen `0.10 mm`
waypoint gates.

All sixteen phase-32/phase-44 selected streams passed exact Card15 checks.
Maximum issued slew was `0.300000000000011 A`, minimum absolute-current
headroom was `105.1 A`, and every eight-slot return bridge closed exactly.

Result SHA-256:
`b79da679f4de3aa60989586b8d24ad48eca7cd23dc5b22584ce9b66af5cb7263`.
Independent audit SHA-256:
`a1861f05298509192876c832956fafb67976b89a5de6079608702a55f861131f`.

This PASS does not alter ID2Z28's source-capture FAIL. It only authorizes a
separately frozen fresh campaign in strict order: calibration, unopened blind
whole-family validation, then at most four zero-fit cardinal moving-reference
feedback sentinels and one replay. The model is not refit after calibration.
No Authority-L0, Recourse-L1, controller qualification, arbitrary waypoint,
path or R_mid claim is made.
