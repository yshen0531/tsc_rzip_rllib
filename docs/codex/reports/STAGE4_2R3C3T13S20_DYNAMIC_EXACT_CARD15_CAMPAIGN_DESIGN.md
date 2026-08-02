# Stage4.2R3c3T13S20 dynamic-exact Card15 campaign design

## Status and purpose

This design is frozen before any S20 plant step or response outcome is opened.
S20 is a new experiment identity, not an S19 resume. Its purpose is to test a
prospective pooled causal observer on fresh dynamic-exact calibration inputs.
It is identification only; it is not MPC, expert data, BC, DAgger, or RL.

## Frozen matrix and blindness

The S19 whole-pair split is unchanged:

```text
training pairs / contexts / rollouts       12 / 24 / 216
calibration pairs / contexts / rollouts      4 /  8 /  72
holdout pairs / contexts / rollouts          4 /  8 /  72
total pairs / contexts / rollouts           20 / 40 / 360
```

Each context has one baseline and eight signed response rollouts. Both
hidden-history members remain grouped by pair. Training outcomes may be
opened first. The selected pooled model and its complete artifact are hashed
before any calibration outcome opens. The calibrated residual tube is hashed
before any holdout outcome opens. Outcome-based repartitioning is forbidden.

The 24 S19 training-baseline files are authenticated development evidence
only. S20 re-executes all 360 rollouts and reuses none of them as campaign raw.
S19 contains no training response, calibration, or holdout raw.

## Causal controller contract

The underlying visible-state controller, QR field directions, response issue
and cancellation, horizons, target/delay/slew assignments, restart snapshots,
and source authentication stay frozen. At calibration task steps 0 through 7:

1. Compute the underlying action from only the current visible state and its
   causal controller memory.
2. Apply the actuator model to obtain the current Card15 center.
3. Retain the S16 QR direction frozen at task step zero.
4. Select the nearest exactly representable signed displacement about the
   current center.
5. Record the actual four-dimensional coordinate in the frozen current-domain
   basis.
6. Fail before a plant step if exact encoding, action, current, geometry, or
   zero-net gates fail.

Pair, history, partition, prefix, target label, delay, slew, source actions,
source results, source/current wire currents, future actions, future
measurements, and post-effect currents are forbidden controller inputs.

## Frozen dynamic action gates

Every calibration event must satisfy:

```text
exact ten-character Card15 target                         true
no action saturation or current clipping                  true
signed primary frozen-basis coordinate       [0.85, 1.15]
maximum absolute cross-coordinate                         0.15
minimum desired/actual current cosine                     0.98
maximum relative off-basis residual                       0.15
maximum incremental/total action             unchanged S16 gates
maximum current utilization                  unchanged S16 gate
```

The sum of all eight actual signed calibration field increments must be exactly
zero at task step 7. An unrepresentable or non-zero-net path is an execution
or excitation-design failure, not a plant-control failure.

## Frozen causal feature model

Visible states 1 through 10 provide R, Z, finite-difference vR/vZ, and Ip. For
each trajectory the 10x8 local design is rebuilt from:

```text
columns 0--3  Legendre degree 0--3 drift terms
columns 4--7  recorded input coordinates at steps 0--7,
              then exact zeros at settling steps 8--9
```

Every trajectory requires rank eight and condition number no greater than
`4.0`. The state-11 response action coordinate and its causal Card15
uncertainty are reconstructed from the same trajectory. The nine pooled
features remain the five predicted visible response components plus four
response-action coordinates.

The response projection gates remain cosine at least `0.98` and relative
off-basis residual at most `0.15`.

## Frozen statistical gates

Training selects ridge from:

```text
0, 1e-8, 1e-6, 1e-4, 1e-2, 1, 100
```

Selection uses whole-pair outer grouping and lexicographically minimizes
maximum absolute scaled OOF error, mean squared scaled OOF error, then ridge.
The maximum scaled point error must be at most `0.1` in training, calibration,
and holdout.

The tube is componentwise:

```text
response floor
+ 4 * max(training whole-pair OOF residual,
          calibration absolute residual)
+ exact propagated current-run Card15 feature radius
```

All rows must pass point error, containment, and unchanged component caps:

```text
R 0.003 m, Z 0.003 m, vR 0.01 m/s, vZ 0.01 m/s, Ip 1000 A
```

## Phase boundaries and stop rules

The campaign runs in this order and stops at the first failed boundary:

```text
offline authentication and zero-plant preflight
training baselines -> zero-plant full-path lattice gate
training probes -> whole-pair OOF model -> model hash
calibration baselines -> zero-plant full-path lattice gate
calibration probes -> calibrated tube -> tube hash
holdout baselines -> zero-plant full-path lattice gate
holdout probes -> final and independent raw recomputation
```

Runtime/environment, packaging/deployment, raw corruption, reporting,
excitation design, observer design, and real control conclusions must be
reported separately. Baseline formal tracking is diagnostic only and cannot
be substituted for an observer gate.

## Immutable timing and scientific route

Arrival remains no later than 250 ms for slew 1.0/1.1 and 270 ms for slew 0.9;
formal hold remains through 350/370 ms. R/Z tolerance remains 30 mm, speed
threshold 0.1 m/s, Ip threshold 10 kA, and arrival streak three. No timing or
gate may be relaxed after outcomes are seen.

A complete S20 pass authorizes only offline robust-transport MPC feasibility
and a separately preregistered real MPC campaign. It does not validate
restart transport control, new targets, continuous parameters, noise,
disturbance recovery, long hold, an expert dataset, or any RL stage.
