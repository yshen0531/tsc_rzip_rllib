# ID-2Z27 dynamic output-aligned D0 result

ID-2Z27 completed the one prospectively frozen fresh-TSC campaign. All
eleven rollouts completed: 803/803 plant advances, 814 retained states and
4,070 required artifacts (47,938,840,136 bytes). Exact Card15 execution,
the common prefix, current and outer-envelope gates, matched raw inventory
and the zero-weight replay all passed. No model, calibration, holdout,
controller or optimization was run in this identity.

The frozen scientific route is
`ONE_MS_ID2Z27_DYNAMIC_D0_DATA_PASS_MODEL_AND_AUTHORITY_DESIGN_ONLY`.
Every one of the eight signed q_R/q_Z branches passed. The h4 responses were
0.0509--0.0624 mm, h8 responses 0.1790--0.2311 mm, and h4-to-h8 cosines
0.9924--1.0000. Maximum paired Ip response was 53.03 A. At issues 32 and
40 the four signed directions passed the h4/h8 geometry gates: maximum
angular gaps were 110.44/115.64 and 114.22/118.00 degrees; weakest-best
projections were 0.0334/0.1150 and 0.0301/0.1032 mm.

This is a D0 data-readiness PASS, not control. Capture was 0/11. The
transition-center baseline terminal diagnostic reached 33.644 mm and
0.440 m/s, while continuing full-F reached 28.012 mm and 0.370 m/s. The
measured signed effects are persistent and two-dimensional but much smaller
than the nominal drift. They may support a bounded local event/value model
and an Authority-L0 design; they do not establish capture, recovery,
Recourse-L1, a controller, a waypoint, a path or R_mid crossing.

The first independent audit correctly reparsed all raw states and artifacts
but falsely compared final retained state-k `inputa` (already rewritten with
outgoing issue k) with the compact preissue `inputa`. It is preserved as a
reporting/auditor FAIL. A separately committed reporting-only repair uses
the compact hash only for that overwritten preissue artifact, while retaining
independent raw RZI/current/other-artifact checks and independently checking
the outgoing inputa fields against the frozen action stream. The repaired
audit passed with no new TSC and reproduced the primary route and metrics.

The next bounded step is zero-new-TSC model/action-allocation work. It must
use only the nine prospectively fit-weighted D0 families, keep full-F and the
replay at zero weight, and target 1--8 ms event/velocity/candidate value rather
than another unconstrained absolute-state world model. In parallel it may
design, but not yet claim, an Authority-L0 sentinel. Any later real feedback
still requires fresh model calibration/blind holdout, Authority-L0,
Recourse-L1 and the independent hard interface as an AND gate.
