# ID-2Z22 discrete-vertex moving-nominal preflight design

Date: 2026-08-20

## Purpose

ID-2Z21 rejected continuous inversion of the executed F/A/a/E/e coordinate.
ID-2Z22 is a bounded, server-executed, zero-TSC and zero-fit audit. It asks a
narrower question: whether existing authenticated evidence supports one
prospective moving-nominal campaign using exact Card15 vertices, without
pretending that those vertices form a continuous actuator basis.

This audit does not authorize a controller, model, capture, authority or
recovery claim. It may authorize only the separately implemented ID-2Z23
simulator-development campaign defined below.

## Frozen evidence and candidate vertices

The audit authenticates the final ID-2Z21 result and independent audit, the
ID-2Z17 held-state candidate bank, the ID-2W1 phase-collapse result and the
ID-2Z18 continuing-full-F reference.

Four ID-2Z17 vertices are frozen before this audit runs:

```text
p00_minus4, p05_minus4, p05_plus4, p06_plus4
```

They were selected from development evidence because, relative to the matched
ID-2Z17 hold branch, each has a persistent state-52 to state-56 response and
the set positively spans the measured R/Z plane at both checkpoints. This is
only nomination evidence at one held state. The new campaign must remeasure
the vertices around the continuing moving nominal at two phases.

## Audit gates

The preflight must independently recompute all of the following from compact
evidence and exact action streams:

1. all selected branches share the exact state/action prefix through state 48;
2. each selected branch has at least `0.08 mm` R/Z response at state 52 and
   `0.20 mm` at state 56 relative to the matched hold;
3. each branch has state-52/state-56 response cosine at least `0.95`;
4. at both checkpoints the four response vectors have maximum angular gap at
   most `120 deg` and 64-direction weakest-best projection at least `0.06 mm`;
5. exact issued Card15 increments are nonzero and pairwise distinct;
6. the ID-2W1 state-25 positive-span/state-26 collapse is retained as a phase
   warning, not reinterpreted as authority;
7. the prospective issue-24 and issue-32 schedules use four consecutive exact
   vertex issues in place of F, then resume F from the attained target; every
   issue is exactly representable, has per-coil slew at most `0.3 A`, stays
   within absolute-current limits, and never uses add-and-clip semantics;
8. baseline full-F, eight branches and one preregistered replay give exactly
   ten prospective rollouts, 650 maximum advances and no hidden adaptive arm.

ID-2Z22 passes only if every gate passes. A failure authorizes no TSC and
requires a new action basis or takeover nominal.

## Prospectively frozen successor campaign

If and only if ID-2Z22 passes, ID-2Z23 may implement one ten-rollout campaign:

- one fresh continuing-full-F matched baseline;
- four frozen vertices replacing F at issues 24--27;
- the same four vertices replacing F at issues 32--35;
- one exact replay of `issue24__p05_plus4` with zero fit weight.

Every branch resumes F after its four replacement issues and holds only after
issue 47, matching the full-F horizon. All complete, prospectively declared
causal windows may be simulator-development fit eligible; the replay has zero
fit weight. Runtime support remains an empirical simulator-development
contract with fail-closed current, boundary, Ip, outer-envelope, raw and
effect-timing gates. A post-action stop is not a pre-action plant bound.

ID-2Z23 must evaluate each phase separately. Passing input geometry is
insufficient. At each phase the measured four-vector R/Z family must retain
persistent non-hybrid signal and positive-span geometry. A campaign pass may
authorize bounded event/value-model development and an Authority-L0 design in
parallel; it does not authorize real control or Recourse-L1.

## Stop rule

No threshold, vertex, phase or rollout may be added after observing ID-2Z22 or
ID-2Z23. If either moving-nominal phase loses the preregistered persistent
two-axis geometry, the current exact-vertex grammar closes. The next review
must change the Card15 action basis or takeover nominal rather than add another
nearby amplitude, duration, phase or neural model.
