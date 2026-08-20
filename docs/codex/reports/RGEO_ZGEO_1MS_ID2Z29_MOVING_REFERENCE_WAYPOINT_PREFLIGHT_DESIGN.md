# ID-2Z29 moving-reference waypoint preflight design

ID-2Z28 remains final: its finite q_R/q_Z model passed internal phase
validation, but the best eight-token sequence improved the source-capture
score by only 4.7500%. ID-2Z29 does not weaken or reinterpret that result.
It asks a different, final-goal-aligned question: can the same measured cell
prospectively support a small two-axis waypoint relative to the time-indexed
moving transition nominal?

This is a zero-new-TSC, zero-new-fit decision audit. The frozen ID-2Z28 model
payload is used without modification. For eight equally spaced R/Z target
directions, the target ramps linearly from zero to a radius of `0.10 mm` over
eight effects. Every one of the `390625` eight-token sequences over
`H,R+,R-,Z+,Z-` is evaluated against that relative reference. The objective
is the maximum R/Z tracking error over all eight effects; ties are broken by
endpoint error, Ip excursion and lexicographic token order.

Readiness requires, in all eight directions:

- maximum predicted path error at most `0.025 mm`;
- endpoint error at most `0.025 mm`;
- endpoint directional progress at least `0.080 mm`;
- maximum predicted paired Ip excursion at most `100 A`;
- exact Card15 construction at both issues 32 and 44, `<=0.3 A` issue slew,
  nonnegative absolute-current headroom and exact eight-slot return closure.

The radius and gates are frozen before execution; there is no amplitude,
duration, phase, kernel or model search. A FAIL closes this q-cell moving-
reference route and returns to a material action-basis/takeover redesign. A
PASS authorizes only a separately identified campaign design containing:

1. a fresh matched center baseline;
2. issue-36 signed calibration families, used only to calibrate fixed-model
   error bounds;
3. issue-44 signed whole-family blind validation, opened only after the
   calibration verdict is frozen; and
4. at most four zero-fit cardinal-waypoint feedback sentinels plus one exact
   replay, run only after calibration and blind PASS.

The future feedback policy must read exact same-step R_geo/Z_geo/Ip and its
own complete causal action history before every issue, replan over at most
eight milliseconds, and use the exact moving nominal plus q-cell allocation
without clipping. Candidate-response data, calibration, blind families and
sentinels remain disjoint by whole trajectory. Simulator exploration guards
do not become controller-grade transition tubes.

Even a PASS is not source capture, terminal-set viability, Authority-L0,
Recourse-L1, controller qualification, arbitrary waypoint size, position
generalization, path tracking or R_mid crossing. Source capture and Recourse
remain independent AND requirements before qualified closed-loop control.
