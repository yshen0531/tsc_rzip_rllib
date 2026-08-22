# Fixed-1000 joint allocator Authority G2R1 design

G2 v1 is immutable as a zero-TSC lattice-construction FAIL. Exact Card15
enumeration found joint diagonal edges of exactly `0.3 A`, despite the
continuous-coordinate expectation of a `<=0.25 A` issued transition. No plant
advance occurred. The failed identity is not reinterpreted or resumed.

G2R1 is an action-construction correction made before any response. It changes
only the vertical single-turn lattice increment from `0.07 A` to `0.06 A` and
tightens the exact issued cap from `0.25 A` to `0.21 A`. Exhaustive design-time
enumeration gives maximum exact adjacent slew
`0.20833333333333333333333334 A`, leaving more than `0.09 A` below the
unchanged observed-current hard limit of `0.3 A`.

All scientific semantics remain those of G2 v1:

- fixed 1000-ms source, 64 issues, five rollouts / 320 advances;
- exact lattice `T(r,z)` with `r in [-4,32]`, `z in [-4,4]`;
- causal radial switch from current exact R/history, bounded to issues 4--8;
- mirrored `+0.45 -> -0.45 mm` and `-0.45 -> +0.45 mm` Z commands;
- matched q0, radial-only, two joint paths and one path replay;
- unchanged 15% terminal distance, 0.03-m/s speed, 5%-Ip, vertical endpoint,
  acquisition and mirror-separation gates;
- zero fit weight for every G2R1 row;
- no clipping, retry, model, calibration, holdout, feedback or Recourse.

The `0.06 A` value is not selected from plant response. It is the largest
tested decimal construction among `0.06/0.05/0.04 A` whose exact joint Card15
adjacency is below the already frozen reserve cap; `0.07 A` is rejected by
geometry. This is a one-time pre-response lattice correction, not an amplitude
ladder. G2R1 FAIL closes the cell and policy without trying another scale.

Only complete server tests, exact installed hashes and a new zero-TSC offline
PASS may authorize the single real campaign. PASS remains finite Authority
development only and may open endpoint-value/risk model design plus Recourse
design in parallel. A real controller still requires all independent gates.
