# Stage4.2R3c3T10 interaction-aware feasibility design

## Status and purpose

This design was frozen after the certified T9 identification result and before
running the T10 optimizer. T9 passed its identification gates on all 32
contexts, but the fixed linear/separable route passed 0/32 because both the
mixed stress-by-PC3 response and the PC3 response modulation were material.

T10 is a server-side, read-only feasibility audit of those 224 immutable T9
raw trajectories. It executes no new TSC task and no real MPC controller. The
formal 250/270 ms arrival and 350/370 ms hold contract is unchanged.

## Fixed measured-node model

For each authenticated restart context, define `s` as the frozen T9 stress
schedule coordinate and `p` as the PC3 schedule coordinate at the common
factorial amplitude. The six nonbaseline response terms are fitted from the
six nonzero measured nodes:

```text
y(s,p) = y(0,0)
       + s       * B_s
       + p       * B_p
       + s*p     * B_sp
       + s^2     * B_s2
       + p^2     * B_p2
       + s^2*p   * B_s2p
```

The nodes are the standalone PC3 pair `(0, +/-sqrt(2))` and the four T9
factorial corners `(+/-1, +/-1)`. The exact T9 baseline is the seventh node.
The fixed design matrix must have rank 6, condition number no greater than
3.0, and reconstruct all seven raw R/Z/Ip trajectories to absolute error no
greater than `1e-12`.

The optimizer is limited to `s,p in [-1,1]`, the joint schedule envelope
spanned by the four measured factorial corners. It first evaluates a fixed
41-by-41 grid and then uses deterministic per-endpoint bounded SLSQP starts.
All coefficients and reported formal metrics are recomputed from raw data
with the frozen formal evaluator.

## Preregistered acceptance gate

The audit requires:

- exact authentication and parsing of 224/224 T9 raw files;
- exact T9 spec, summary, manifest, state, server-audit, source, package, and
  raw-inventory reproduction;
- 32/32 model-fit passes and exact reproduction of the 16/32 T9 baselines;
- optimistic unchanged-contract formal feasibility 32/32;
- repair of all 16 failed baselines and regression of none of the 16 passes;
- both optimized coordinates inside `[-1,1]`.

## Scientific limitations and next decision

The seven-node surface is an exact interpolant at measured nodes, not a
validated continuous plant model. In particular, the available nodes alias
an unmeasured `s*p^2` term with the stress-linear term and an unmeasured
`s^2*p^2` term with the stress-even term. The standalone PC3 nodes also use
`sqrt(2)` times the common factorial amplitude.

Therefore a favorable T10 result does **not** authorize R3c4. It authorizes
only a prospectively frozen real axis-validation campaign: 64 stress-only
signed probes and 64 PC3-only signed probes at the common amplitude. Those
128 trajectories are needed to de-alias and validate the surface before any
interaction-aware controller is implemented. A failed T10 result instead
means that this measured two-coordinate authority is insufficient even under
the optimistic interpolant.

Probe trajectories remain forbidden from expert datasets. T10 does not
validate independent hidden histories, unseen targets, continuous actuator
parameters, plant error, measurement noise, disturbance recovery, or an
independent long hold. BC, DAgger, and residual RL remain forbidden.
