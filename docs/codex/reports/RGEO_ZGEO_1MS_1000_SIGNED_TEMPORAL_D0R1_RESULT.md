# Fixed-1000 signed temporal D0R1 result

D0R1 is a clean finite development-data PASS at the new 1000 ms source. It
does not use any fixed-1100 trajectory.

The separately frozen implementation revision was
`6113ce54917101417553c55898d21fc30a30afac`. Server validation passed the
focused `8/8` suite after the reporting-only auditor repair and the full one-ms
suite had already passed `748/748` before plant execution. The run completed
all `14/14` authentic resets and `560/560` advances, producing 574 raw states.
The independent raw audit rebuilt 560 actions and 546 later observed-current
slew checks with no failure.

The exact executed action matrix has rank two and maximum single-turn
increment `0.1458333333 A`. Both phase-24 critical replays were exact in
R/Z/Ip, all 14 coil currents, all 48 wire currents and the four semantic
artifacts; sprsina remained diagnostic.

All preregistered science gates passed. The best h4/h8 R/Z odd-response
geometry at phases 8, 10 and 24 used h4 and had condition numbers
`2.81244`, `1.93944` and `1.81024`, with minimum singular values
`0.149968`, `0.071388` and `0.076201 mm`. The odd input coordinate produced
clean signed vertical h4 responses of about `0.138--0.150 mm` and retained
about `0.126--0.134 mm` at h8 with negligible Ip response. The even coordinate
provided radial response, but its minus branch also exposed deterministic
phase-sensitive one-frame excursions: `+0.779518 mm` at phase-8 h4,
`+0.755966 mm` at phase-10 h2 and `-0.663903 mm` at phase-24 h2. These events
are valid development labels, not smooth authority or a qualified tube.

Primary result SHA-256 is
`dba46b4810ee267e36b85f4167580a517476a2d146d40f0e94323a648f6f342f`;
independent audit SHA-256 is
`79d670e4073273a71afbd732ed0a6902eec3fb4041408badf4d40438b94377dd`.
Final routes are
`ONE_MS_NR1000D0R1_SIGNED_TEMPORAL_PASS_MODEL_AND_AUTHORITY_DESIGN_ONLY`
and `ONE_MS_NR1000D0R1_INDEPENDENT_PASS`.

This result proves finite, repeatable, time-dependent two-axis response around
q0. It does not prove cumulative authority, hold, capture, recovery, a model,
feedback, waypoint tracking or R_mid crossing. The next experiment must test
cumulative/sustained exact-Card15 allocation and return before feedback uses
these coordinates.
