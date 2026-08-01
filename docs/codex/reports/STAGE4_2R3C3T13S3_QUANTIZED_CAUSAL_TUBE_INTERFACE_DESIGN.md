# Stage4.2R3c3T13S3 quantized causal tube interface design

## 1. Prospective status

This design is frozen before T13S3 code exists. T13S3 is an offline software
interface stage. It runs no controller rollout, Ray, `gotsc`, TSC, or plant
step and cannot produce a real control result.

Its outcome is exactly one of:

```text
INTERFACE_COMPLETE_HOLDOUT_REQUIRED
INTERFACE_IMPLEMENTATION_FAIL
```

Even a complete interface authorizes only a separately preregistered minimal
lattice-aligned transition holdout. It does not authorize a full
identification campaign or real MPC.

## 2. Quantized actuator primitive

Implement a reusable pure function/object with explicit TSC order and units:

```text
input
  measured current I_k [single-turn A, 14]
  normalized issued action [-1,1, 14]
  current limits [A, 14]
  max slew step [A]
  turn counts [turns, 14]
  fixed development readback bias [1e-6 kA-turn units, 14]
  readback uncertainty radius [grid units, 14]

output
  clipped desired current [A]
  exact ten-character Card15 fields
  exact Card15 target current [A]
  nominal next readback current [A]
  lower/upper next-readback interval [A]
  clipping/zero-effect/grid diagnostics
```

The authenticated development nominal bias is:

```text
[2, 2, 2, 2, 2, 2, 2, 1, 0, 0, 0, 1, 0, 0] * 1e-6 kA-turn
```

It must carry the T13S2R1 report hash as provenance. It is not a universal
constant. Every coil receives a nonzero prospective uncertainty radius of at
least one `1e-6 kA-turn` grid unit. The interval may be enlarged later but
must never be reduced from future outcome inspection without a new
prospective validation.

## 3. Causal restart observer state

Implement an immutable/update-by-return schema containing only:

```text
formal task step
numeric R/Z/Ip target
current and past current-run R/Z/Ip measurements
velocity estimate plus explicit interval/status
measured 14-coil current
commands already issued in the current run
authenticated numeric delay queue
previous correction/integral when causally available
actuator hypothesis set
additive plant-response tube
source/provenance hashes
```

At restart, velocity status is `unknown_interval`; it may not be silently set
to known zero. After a causal difference it becomes `finite_difference` with
an explicit nonzero uncertainty field.

The API must not accept pair, history, prefix, source result/action/current,
wire/vessel current, future measurement, future schedule, or nearest-R17-
phase fields. Unknown extra fields fail closed.

## 4. Set-valued transition interface

The stage does not fit a plant model. It implements a contract that accepts
one or more prospectively supplied plant-transition hypotheses and an
additive tube. Prediction returns:

```text
nominal output trajectory per hypothesis
componentwise lower/upper tube
support class: measured / interpolation / extrapolation / unsupported
formal task clock unchanged
model and actuator provenance
point-model-certified = false
robust-controller-authorized = false
```

An empty hypothesis set or unsupported query fails closed. The interface may
not select a hypothesis from development labels.

## 5. Validation gates

Required focused tests include:

- exact positive/negative/zero Card15 serialization;
- current clipping and active command collapsing to a grid point;
- exact reproduction of the 14-coil development nominal bias;
- nonzero interval width on every coil;
- interval containment under all edge combinations;
- unknown restart velocity and causal finite-difference update;
- queue immutability and formal clock monotonicity;
- forbidden/unknown field rejection;
- multiple-hypothesis union and unsupported fail-closed behavior;
- serialization round-trip and deterministic provenance.

Also run compile, all JSON parse, focused tests, complete tests, import
closure, checksum/package checks, and an isolated empty-directory direct-copy
simulation. Server validation uses the existing virtualenv and runs no TSC.

## 6. Scientific boundary

T13S3 cannot repair T13S1, convert T13S2R1 into an independent holdout,
certify an observer/plant model, or claim control success. Probe trajectories
remain excluded from expert data. Formal timing and physical thresholds are
unchanged. BC, DAgger, and bounded residual RL remain blocked.
