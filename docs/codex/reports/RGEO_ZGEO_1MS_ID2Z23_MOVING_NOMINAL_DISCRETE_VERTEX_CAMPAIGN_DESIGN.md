# ID-2Z23 moving-nominal discrete-vertex campaign design

Date: 2026-08-20

## Question

ID-2Z23 is one finite TSC-only development campaign. It tests whether four
exact Card15 replacement vertices that positively span an old held-state
response retain persistent two-axis geometry around the continuing full-F
moving nominal at issues 24 and 32.

It does not fit a model and does not test a controller, capture, recovery or
Recourse. A PASS authorizes bounded event/value model development and an
Authority-L0 design in parallel. Real in-loop execution remains blocked by
fresh model calibration/holdout, Recourse-L1 and the hard interface AND gate.

## Frozen matrix

The campaign has exactly ten canonical-source rollouts, each with 65 advances:

- one fresh `baseline_full_f`;
- `p00_minus4`, `p05_minus4`, `p05_plus4`, `p06_plus4` replacing F for issues
  24--27, followed by resumed F through issue 47;
- the same four replacements at issues 32--35;
- one exact replay of `issue24__p05_plus4`, with fit weight zero.

The baseline and eight unique branches are prospectively fit eligible only if
the complete campaign, raw, replay, prefix, signal, geometry and Ip gates all
pass. Siblings remain one causal-family split group; the replay is never
weighted as an independent sample.

## Runtime contract

Each rollout starts from the authenticated 1100 ms source. Before the first
novel issue, every state/action prefix through the branch decision state must
match the tracked full-F compact exactly. Every issue uses exact Card15 fields,
`issue k -> state k+1`, no software queue, no silent clipping, and per-coil
slew at most `0.3 A`. Current R_geo/Z_geo/Ip are exact noiseless same-step
observables before every issue; future successors remain unknown.

Every successor is checked against the frozen 2 mm/2 mm/150 A empirical trip
and the 50 mm/10% hard outer envelope. These are simulator-development stop
rules, not a transition tube. Any failure stops before another issue and ends
the campaign without scientific PASS. No retry or arm substitution is allowed.

The server storage gate is `85 GB` free before launch, at most `45 GB`
estimated raw and at least `40 GB` remaining. Raw is not compressed.

## Scientific gates

For each branch, response is branch minus the fresh matched full-F baseline at
the same state. Each issue phase is evaluated separately at horizons 4 and 8:

1. each arm has R/Z norm at least `0.05 mm` at h4 and `0.10 mm` at h8;
2. each arm's h4/h8 direction cosine is at least `0.5`;
3. at both horizons the four vectors have maximum angular gap at most `180 deg`
   and 64-direction weakest-best projection at least `0.02 mm`;
4. maximum absolute paired Ip response is at most `350 A`;
5. the preregistered replay is exact in checked R/Z/Rmid/Ip, 14 coil, 48 wire,
   actions and semantic artifacts; sprsina byte identity is diagnostic only;
6. all ten rollouts complete with exact prefix, raw and interface integrity.

Capture metrics over states 60--65 are reported but cannot repair a response
or geometry failure and are not required for data readiness.

## Stop rule

If either phase fails, this p00/p05/p06 moving-nominal vertex grammar is closed.
Do not add a nearby phase, duration, amplitude or third model. The next route
must change the Card15 action basis or takeover nominal. If both phases pass,
freeze all development compacts before any model choice; compare at most one
structured event/value model and the same backbone plus one small causal
residual, with fresh whole-family calibration and blind holdout reserved.

