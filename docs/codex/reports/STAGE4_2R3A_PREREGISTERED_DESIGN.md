# Stage4.2R3a preregistered delayed-counterpulse design

Preregistered: 2026-07-30 Asia/Shanghai

Status: fixed after final R3 forensics and before any R3a TSC result.

## 1. Identity and purpose

R3a is a new experiment identity. R3 remains failed under its original
1,000 A hidden-state gate and adjacent-pulse matrix.

R3a tests whether a common authentic expert prefix plus a time-separated
counter-pulse can generate:

1. pairs matched in all controller-visible endpoint channels;
2. materially different full 48-wire passive-current histories; and
3. authenticated endpoints different from the frozen R17 initial state.

If and only if the state gate passes, R3a runs the frozen causal MPC expert
from each selected snapshot. No R3 control outcome exists and none is used.

## 2. Threshold calibration

The R3 code correctly converts the configured wire-current column to amperes.
The defect was the absolute threshold magnitude:

```text
authenticated R1 endpoint wire RMS        approximately 0.4-2.3 A
authenticated R1 cross-key wire max diff up to approximately 5.66 A
authenticated R3 endpoint wire RMS        6.35-9.20 A
R3 best adjacent-pulse wire max diff      0.048 A
```

R3a fixes, before execution:

```text
wire-vector length                         exactly 48
maximum absolute full-wire difference      >= 1.0 A
relative RMS full-wire difference          >= 0.05
```

One ampere is above the millampere-scale R3 cancellation residue and within
the authenticated passive-current dynamic range. The relative RMS gate
prevents a single-component numerical outlier from passing.

This is a new-stage calibration, not a retroactive R3 gate change.

## 3. Common initial-state prefix

Every member starts from the same frozen TSC start folder. A common prefix is
taken from the authenticated nominal, delay-0, slew-1.0 frozen expert:

```text
common prefix lengths: 4 and 8 action steps
```

The prefix actions are used only to generate an authentic plant state. They
are never included in a controller checkpoint or exposed to the fresh
controller. Their source experiment ID and action-sequence digest are frozen
in every R3a spec and manifest.

Both prefix lengths must be represented among selected pairs. Selected
centroids must pass the unchanged different-initial-state gate against the
frozen R17 start, and the two prefix groups must also be mutually distinct by
at least one of:

```text
R centroid difference             >= 0.0005 m
Z centroid difference             >= 0.0005 m
Ip centroid difference            >= 2,000 A
14-coil centroid RMS difference   >= 500 A
```

## 4. Time-separated hidden-history excitation

After the common prefix, use a direction from the orthogonal complement of
the frozen three-mode controller basis:

```text
plus-first:
  +a*q, gap_steps zero actions, -a*q, 4 zero settle actions

minus-first:
  -a*q, gap_steps zero actions, +a*q, 4 zero settle actions
```

The requested net nullspace coil increment remains exactly zero. The
inter-pulse gap allows the first passive-current response to evolve before
the counter-pulse restores commanded coil current.

Fixed grid:

```text
nullspace directions             1, 2
amplitude fractions              0.20, 0.40, 0.80
inter-pulse zero gaps            2, 4, 8 steps
common expert prefix lengths     4, 8 steps
post-counterpulse settle         4 steps
history orders                   plus-first, minus-first
candidate pairs                  36
state-generation rollouts        72
```

The nullspace pulse maximum is 0.80 normalized units and may not exceed the
environment action bound. Common prefix actions must exactly match their
authenticated source and also satisfy the environment bound.

## 5. Visible pair gate

The R3 visible-state gate is unchanged:

```text
absolute R difference                         <= 0.0005 m
absolute Z difference                         <= 0.0005 m
absolute Ip difference                        <= 2,000 A
absolute backward-difference vR difference    <= 0.02 m/s
absolute backward-difference vZ difference    <= 0.02 m/s
maximum 14-coil current difference            <= 2,000 A
RMS 14-coil current difference                <= 500 A
maximum endpoint action difference            <= 1e-12 normalized
same TSC transition count and snapshot clock  required
```

All 72 state tasks and snapshots must succeed and pass per-file inventory
verification. A partial grid cannot pass.

## 6. Selection without control leakage

For each `(common_prefix_steps, nullspace_direction)` stratum, select at most
one state-valid pair:

1. largest relative RMS wire difference;
2. largest maximum absolute wire difference;
3. smallest visible normalized ratio;
4. lower pulse amplitude;
5. longer gap;
6. lexical pair ID.

Expected selected pairs are 2-4. At least two, both prefix lengths, two
different-initial centroids, and mutual prefix-group centroid separation are
required. Selection cannot read a control trajectory or formal result.

## 7. Conditional control matrix

For every selected pair:

```text
history members          plus-first, minus-first
targets                  nominal, RZ_p10_m10
future actuator cases    delay 0 / slew 1.0
                         delay 2 / slew 0.9
rollouts per pair        8
total rollouts           16-32
```

Every rollout starts:

- a fresh TSC process from the hash-verified snapshot;
- a fresh controller at task state index zero;
- measurement history containing only current R/Z/Ip;
- zero integral and previous correction;
- the frozen nominal delay-queue initialization;
- no full-wire input, future action, or future measurement.

The full wire vector is recorded only after action selection for audit.

## 8. Formal and integrity gates

Formal timing is unchanged:

```text
slew 1.0: arrive by 250 ms, hold/evaluate through 350 ms
slew 0.9: arrive by 270 ms, hold/evaluate through 370 ms
```

Before real TSC, the fresh controller must again reproduce every required
frozen expert action exactly in a no-gotsc audit.

The R3a manifest must include:

- local/controller/package revision;
- exact hashes of the R3a config, module, launchers, and package manifest;
- R2/R1/R17 source fingerprint;
- common-prefix source experiment and action digest;
- complete state-spec digest.

Resume rejects any mismatch.

Large raw and snapshot trees remain server-side. Independent server Python
postprocessing hashes every raw/snapshot file and recomputes state, pair,
restart, causality, and formal metrics.

BC, DAgger, and residual RL remain prohibited.
