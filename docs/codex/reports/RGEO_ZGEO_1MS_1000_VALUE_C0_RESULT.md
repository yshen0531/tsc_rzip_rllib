# Fixed-1000 C0 fresh calibration result

C0 completed all `12/12` authentic rollouts and `576/576` verified plant
advances at implementation revision
`5adf91d3af28d316e170b2b8527756cee9caf9e4`. Ten rows were fresh calibration
evaluations and two exact replays carried zero fit weight. The byte-fixed V0
artifact was not updated.

Both negative conditioner histories passed. Every h4/h8 R/Z/Ip component was
contained (`24/24` per history), maximum directional candidate-ranking regret
was zero, and h8 weakest-best progress was `0.277278 mm` for even-minus and
`0.279069 mm` for odd-minus. Best h4 condition/sigma-min were
`1.58421 / 0.205626 mm` and `1.54009 / 0.208018 mm`.

The independent raw audit rebuilt all 588 states, 576 actions and 564 later
observed-slew transitions and reproduced the primary verdict. Both critical
replays were exact. Primary and independent SHA-256 are
`c577e9efcc5f710a09b9c52f60448ae83e9f3a5541407a4d004a27754538288d` and
`bd1c6b9f29663274f7b433c6a2179c6248bda268736dbb771916a2ed74cea5d9`.

The primary route is
`ONE_MS_NR1000C0_FIXED_V0_FRESH_CALIBRATION_PASS_BLIND_DESIGN_ONLY`; the
independent route is `ONE_MS_NR1000C0_INDEPENDENT_PASS`. This qualifies only
design of one prospectively frozen mixed-history blind campaign. It is not a
model refit, Authority, capture, Recourse, feedback or path-tracking result.
