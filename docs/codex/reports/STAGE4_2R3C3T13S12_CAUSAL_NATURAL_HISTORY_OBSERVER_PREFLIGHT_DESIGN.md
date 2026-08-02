# Stage4.2R3c3T13S12 causal natural-history observer preflight design

## Status and question

This design is frozen after final T13S11 output and forensics and before any
T13S12 history vector, basis, fit, prediction, or route output is computed.
T13S12 is a zero-new-TSC development preflight over the consumed T13S5 q2
and T13S9 q1 raw.

T13S11 showed that one early calibration transition is insufficient and its
unwhitened interaction coordinate is badly conditioned. T13S12 removes the
active pulse and asks whether the complete causal visible history available
before the braking issue can serve as a persistent observer state for the
later first-effect braking response.

## Immutable sources

Authenticate exactly:

```text
T13S5 q2 raw files / digest
  68 / 09ee846d2fd8c2a516ec01f1b91bcbf8f303885c2377373000ab85dfc45e0f01
T13S5 source audit SHA-256
  dc4d0147ce4fdd8a00105f8fc8ad45466513bac8b012f6843327b1efc271b033
T13S9 q1 raw files / digest
  68 / 9ccc67d5eda2b0710d658812207d99666a50af352e42d950086b694a3fa928ad
T13S9 source audit SHA-256
  df4d7982f98a6216997d89ac5adea9ca2e3b2bf367451c3412d5458ccc5c60e0
final T13S10 audit SHA-256
  f24768f7b4899c73f68fd0a4e3991f524239951883abf3d2809461b5ab82509b
final T13S11 audit SHA-256
  6e595fbd4e86276d449fc953edcb06b676bd282b6f0bd68d4e5ac3effe97ffbe
```

All source data is consumed development evidence. A positive result requires
new sequential TSC confirmation.

## Frozen causal history vector

Use only each context's exact lattice baseline trajectory. The braking issue
state is 16 for delay 0 and 14 for delay 2. At every state from zero through
that issue state, append this fixed deployable vector:

```text
R target error / 0.03 m
Z target error / 0.03 m
Ip target error / 10000 A
backward-causal vR / 0.1 m/s
backward-causal vZ / 0.1 m/s
velocity-known flag
14 measured TSC-order coil currents / declared half ranges
14 backward measured coil-current differences / declared half ranges
coil-history-known flag
```

At state zero, both differences are zero and both known flags are false.
At later states they use only the current and immediately preceding measured
state. Flatten the sequence in chronological order, then append normalized
known delay and slew. Within each easy/hard stratum all context vectors have
the same frozen length.

Requested/source actions, controller outputs, pair/q/history/prefix labels,
source IDs/results, future values, braking response, wire currents, vessel
currents, and outcome labels are forbidden. Targets, known delay/slew, and
measured current/past visible state are allowed.

## Training-only observer and interaction model

Use eight leave-one-context-out folds, four contexts per easy/hard stratum.
For each fold:

1. Center the three training history vectors and compute their affine rank
   from two exact training differences. It must be rank 2.
2. Compute a training-only rank-2 SVD history basis. Project the held history
   only after the basis is frozen.
3. Divide each of the two training history scores by its training RMS. Both
   RMS values must be finite and above `1e-12`. Apply the frozen scaling to
   the held score.
4. Build a training-only rank-4 SVD basis from all measured 14-coil braking
   first-effect inputs. Divide each input coordinate by its training RMS,
   again requiring finite values above `1e-12`.
5. Fit the same zero-at-zero-current 12-column interaction:
   `y = kron((1, s1, s2), u) @ J` by minimum-norm least squares.

Whitening is training-only coordinate scaling. It may improve numerical
condition but cannot change the least-squares prediction or residual span
relative to the same bases.

The interaction design must have rank 12, finite condition `<=30`, and
nonzero signal. The tube remains:

```text
response scales       (0.03 m, 0.03 m, 0.1 m/s, 0.1 m/s, 2000 A)
radius                numerical floor + 1.5 * max training residual
component caps        (0.003 m, 0.003 m, 0.01 m/s, 0.01 m/s, 1000 A)
scaled center error   <= 0.10
```

## Non-vacuous support and exact gates

Do not use the full-rank interaction row as a support gate. Require:

```text
held causal-history residual to training rank-2 affine space   <= 0.15
held braking-current residual to training rank-4 space         <= 0.15
```

Both residuals are computed in the original physically scaled spaces with
only a numerical zero floor.

Exact pass counts:

```text
source raw / trace identity                         68 / 68, 68 / 68, 136 / 136
causal baseline history extraction                                      8 / 8
history finite/schema/length/causality                                   8 / 8
signed braking first-effect extraction                                 64 / 64
braking pre-effect causality                                           64 / 64
training history affine rank                                             8 / 8
training history/current whitening                                       8 / 8
interaction rank/condition/signal                                         8 / 8
non-vacuous interaction tube                                             8 / 8
held causal-history support                                              8 / 8
held braking-current support                                           64 / 64
componentwise containment                                              64 / 64
scaled relative error <= 0.10                                          64 / 64
disjoint exact history/input causal aliases                                    0
forbidden feature/trace/model inputs                                           0
```

Unsupported and nonfinite values fail closed. No history endpoint, schema,
normalization, basis dimension, condition gate, support, tube, error gate,
or effect state may change after output.

## Routes

```text
CAUSAL_NATURAL_HISTORY_OBSERVER_PREFLIGHT_CANDIDATE_Q3_SEQUENCE_TSC_REQUIRED
  every gate passes;
  authorize only a prospectively frozen new-history sequence campaign that
  observes the same causal history before a later probe on one trajectory.

CAUSAL_NATURAL_HISTORY_OBSERVER_PREFLIGHT_INSUFFICIENT_NONLINEAR_OBSERVER_REDESIGN
  any gate fails;
  stop the affine observer and design a recurrent/nonlinear observer plus a
  broader prospective history-identification campaign.
```

The source baseline and braking probe are separate trajectories, so even a
pass is only an optimistic preflight. Neither route authorizes a controller,
MPC, expert data, BC, DAgger, or bounded residual RL. Formal arrival and hold
timing remains unchanged.
