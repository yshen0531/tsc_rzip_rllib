# Fixed-1000 joint allocator Authority G2R1 result

## Verdict

`ONE_MS_NR1000G2R1_JOINT_ALLOCATOR_AUTHORITY_INSUFFICIENT_ACTION_BASIS_REDESIGN`

G2R1 completed all five authentic rollouts and all 320 preregistered one-ms
advances. The independently reparsed audit passed 325 raw states, 320 exact
Card15 actions, 315 observed-current transitions and the critical path replay
with no failures. This is a scientific Authority FAIL, not an execution,
interface, safety, raw, replay or reporting failure.

## What worked

The pre-response lattice correction was valid. Exhaustive offline enumeration
covered 333 cells and 2,392 directed edges; the largest exact issued edge was
`0.20833333333333334 A`, leaving `0.09166666666666665 A` to the unchanged
`0.3 A` observed-current hard limit. No G1-style readback-margin stop recurred.

The first mirrored vertical acquisition was strong and symmetric. At state16,
the two paths reached `+/-0.387523 mm` for `+/-0.45 mm` commands, each with
only `0.062477 mm` endpoint error. The critical positive-then-negative path
replay was exact.

## What failed

The second, reversed command was not acquired. At state36 the mirrored paths
reached only `-/+0.0685615 mm` instead of `-/+0.45 mm`; endpoint error was
`0.3814385 mm` and mirror separation only `0.137123 mm`.

The radial policy also failed its absolute utility gate. Relative to matched
q0 terminal worst distance/speed `23.538658 mm / 0.318027 m/s`, the three
active paths achieved about `20.909--20.910 mm / 0.570576--0.570616 m/s`.
Distance improved only `11.166--11.171%`, below the frozen `15%` threshold,
while speed worsened by about `0.25255 m/s`. Ip remained non-limiting at less
than `0.487%` source offset.

## Route boundary

This closes the exact G2/G2R1 even/odd integer lattice and its early-minus,
current-triggered cross-zero radial policy. No adjacent vertical scale,
neighboring switch threshold, deeper level or third replay is permitted. The
result does not show that R/Z actuation is absent: it directly measured a
clean first vertical acquisition and a large radial trajectory change. It
shows that this two-coordinate basis and schedule do not provide the required
terminal-velocity-aware absolute Authority or reversal.

The sole successor is a prospectively frozen, bounded action-basis discovery
campaign at fixed 1000 ms. It must introduce materially different exact
Card15 directions rather than rescale G2, use signed matched pulses at more
than one causal phase, and gate on persistent task-plane positive span rather
than input rank or transient peaks. It remains development/Authority evidence,
not a model, Recourse, feedback or path-tracking qualification.

## Evidence

- implementation revision: `2a559cb4386c0a6c1d6c9e4470f542668f599775`;
- zero-TSC preflight SHA-256: `3050e8c50cbdd024fe755085c1007267c3f19ee245055061d84fbcff34d65e6d`;
- primary result SHA-256: `b81493d9c0a984af7d89832a507520e88e45a4adeb224919f4c5f6bdfa9c8815`;
- independent audit SHA-256: `966c346c9d8e7b21972c9b51782ecf9d88c617edc09cf66894876abd03869b36`.
