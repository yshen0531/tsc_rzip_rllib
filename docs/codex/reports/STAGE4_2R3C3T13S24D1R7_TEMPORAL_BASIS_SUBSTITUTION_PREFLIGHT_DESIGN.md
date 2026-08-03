# Stage4.2R3c3T13S24D1R7 temporal-basis substitution preflight design

Status: prospectively frozen after the final D1R6 forensics and exploratory
read-only algebra, but before D1R7 implementation, output, or any new TSC.

## Purpose and claim boundary

D1R2 proved that the geometry-restored standard H16 schedule still had nine
unsafe final cancellations. D1R6 then proved that applying up to three causal
straight-line 0.175 return intermediates does not repair those paths. At task
step 22 every exact-center finish still required 0.3673570430--0.5149905137
relative to the current underlying action.

D1R7 changes the fixed temporal sign basis, not the action thresholds or
return semantics. It is a server-side, zero-new-TSC preflight. It must
authenticate the immutable S24/D1R1/D1R2/D1R6 evidence, assemble one fixed
24-by-16 schedule from the exact D1R1 actual-coordinate catalog, replay every
unchanged static gate in all 40 S21 contexts, and freeze 108 fresh-identity
specifications for a later real safety sentinel.

A D1R7 pass authorizes only prospective design of D1R8. It is not a real
sequence, plant, controller, transition-model, MPC, formal-control,
hidden-history robustness, expert-data, BC, DAgger, or RL result.

## Immutable evidence boundary

```text
S24 active raw count / inventory digest
  600
  fae5f62671296c837e00158fe204a1630fc70aace87be650ad13d75928f20c70

S24 sequential success / structured failure
  522 / 54

D1R1 detailed static replay SHA-256
  81168e646f2b40e443fa85f535193474651eb899ac8a74e1c9cd282b4f66ff98

D1R1 config / implementation / report SHA-256
  860dffbf5a25f7275a0976bdb0e037b859519c35c8365480c364fbbdfd7bde99
  0557961967b3129f0e4ec122b03c6132f8936d6d554b1c93dab5cae1c1cde2e1
  b24cb0773e107d826bf5d69a047c7af412852634403741942eae4c343202f9d7

D1R2 raw count / bytes / inventory digest
  54 / 3078383
  eb4ac8c0e606ce0d8899f0a512b594877f59cc9424c0f6a87e3450bcd036cc83

D1R2 physical result
  45 full horizons / 9 structured safe stops

D1R6 execution package checkpoint
  4177aa2

D1R6 raw count / bytes / inventory digest
  9 / 422133
  351f7484bd3ec2f68f76cc2f17ea6bc93a6227e2078b8be2f0cdf9e84055fd89

D1R6 independent / physical-state correction SHA-256
  e54bfe8369ed35865771a918a8d25dd6ff1ad84d2e73175c0ba67694e4149698
  f64e7e2a1fc50b70804635971450676d83d53c4d2168ac8a710c0d5e925f8229

D1R6 forensic report SHA-256
  5103797bd915185b9e2d086b8d26ea4868e1e54df2f1edc989d2876d498abb7a
```

The implementation must strictly parse and authenticate every S24, D1R2,
and D1R6 raw JSON.GZ in place. It must independently reproduce the S24
per-sequence 24-context inventory, all nine D1R2 structured failures, and all
nine D1R6 task-step-22 safe stops. A mismatch stops before any candidate
output is accepted.

Source raw is development/forensic evidence only. D1R7 may not fit a model,
copy raw, or relabel it as expert data.

## Frozen failure discriminator

Use the four within-slot canonical directions and amplitudes:

```text
direction 0  ++++  0.250
direction 1  +-+-  0.250
direction 2  ++--  0.290
direction 3  +--+  0.360
```

The D1R2/D1R6 unsafe rows are exact direction-2 temporal sign strings:

```text
source sequence 6    +-+-
source sequence 10   ++--
source sequence 18   ----
```

D1R7 must reproduce that exact classification from raw. It may not infer that
the global sign reverse of a failed row is also failed or safe: D1R2 already
showed that sign reversal is nonlinear and context dependent.

## Fixed primary matrix

Directions 0, 1, and 3 retain the standard temporal H4 basis, in this order:

```text
++++
+-+-
++--
+--+
```

Direction 2 replaces only its temporal basis with:

```text
++++
+--+
-+-+
--++
```

The third row above is `-+-+`; leading minus signs are significant. Written
without alignment ambiguity, the exact ordered direction-2 strings are:

```text
[+,+,+,+]
[+,-,-,+]
[-,+,-,+]
[-,-,+,+]
```

Primary rows are ordered outer-major and then direction-major. Therefore the
16 temporal strings by primary row are:

```text
row   direction   temporal signs
 0        0        ++++
 1        1        ++++
 2        2        ++++
 3        3        ++++
 4        0        +-+-
 5        1        +-+-
 6        2        +--+
 7        3        +-+-
 8        0        ++--
 9        1        ++--
10        2        -+-+
11        3        ++--
12        0        +--+
13        1        +--+
14        2        --++
15        3        +--+
```

For direction 2, `++++`, `+--+`, and `-+-+` have prior real development
support but not a complete independent new-identity grid. `--++` is the exact
global sign reverse of the failed source row 10 and has no prior real
trajectory. Its inclusion follows the frozen orthogonal completion, not an
assumed sign symmetry.

## Frozen central-sign sentinels

The eight extra schedule rows are exact negatives of primary rows:

```text
[0, 4, 1, 5, 3, 7, 6, 8]
```

in that exact order. Thus schedule rows 16 through 23 pair with those primary
indices. The direction-2 central pair is primary row 6 (`+--+`) and its new
negative (`-++-`). No direction-2 candidate row equals the three observed
unsafe temporal strings.

The complete requested 24-by-16 matrix canonical digest is:

```text
c4430a13b679ad8dcceb72c259051a5eebad03da47d86816d46c4385cd811d77
```

The digest uses canonical compact JSON over the nested floating-point matrix.
No row permutation, sign substitution, amplitude search, retry, or post-result
candidate selection is allowed.

## Static actual-coordinate replay

D1R7 must read the immutable D1R1 3,840-event catalog and index it by the
physical context, slot, and exact desired four-coordinate block. Every block
in the new schedule must have exactly one consistent catalog construction.
It must then assemble all 40 actual 24-by-16 matrices and recompute, rather
than copy, every gate:

```text
finite issue/cancel constructions                         7680 / 7680
issue gates                                               3840 / 3840
cancellation gates                                        3840 / 3840
exact Decimal central-sign checks                         1280 / 1280
global rank-16 contexts                                      40 / 40
slot rank-4 blocks                                          160 / 160
global normalized condition                                  <= 3.0
slot normalized condition                                    <= 3.0
late-column residual outside slot-0 span                      >= 0.5
```

All original coordinate error, active-coordinate, cosine, off-basis,
incremental-action, total-action, current, exact stored-center, exact-zero,
Card15, saturation, and clipping thresholds remain unchanged.

The pre-design exploratory read-only calculation obtained requested rank 16,
requested normalized condition 2.0364675298, requested maximum slot condition
1.44, and requested minimum late residual 0.9609879512. Those numbers are not
D1R7 evidence; the frozen implementation and independent implementation must
recompute them and all actual-coordinate values.

## Frozen D1R8 candidate boundary

Only the six schedule rows whose full temporal sequence is new, reordered, or
executed at a changed direction-2 amplitude are selected:

```text
[2, 6, 10, 14, 22, 23]
```

The exact 18 unique `(pair_id, history_member)` contexts from the D1R2 raw
boundary are used. They cover nine pairs and both history members. The
Cartesian product is exactly:

```text
18 contexts x 6 rows = 108 fresh candidate specifications
normal 35-step horizon                              48
weak 37-step horizon                                60
unique authenticated restart snapshots              18
```

Each candidate spec must receive a fresh D1R8 experiment identity and retain
the exact source context, target, actuator delay/gain/slew, calibration token,
snapshot, horizon, issue/cancel knots, matrix row, amplitudes, online 0.24
cancellation margin, original 0.25 cap, current cap, and formal timing. The
source sequence outcome and old sequence index may be used by the offline
builder/auditor only and must be stripped before controller construction.

D1R7 produces specifications only. It may not start Ray, `gotsc`, TSC, a
controller rollout, reset a plant, advance a plant, or create a snapshot.

## Formal timing and controller-input veto

The immutable contract remains:

```text
normal: arrive by 250 ms, hold/evaluate through 350 ms
weak:   arrive by 270 ms, hold/evaluate through 370 ms
R/Z tolerance 0.03 m, speed 0.1 m/s, Ip 10000 A, arrival streak 3
```

The future D1R8 controller may use only the current rollout's visible state,
measured coil currents, its own causal state, the fixed global row, and the
current task step. Pair/history/partition/source-outcome labels, source or
future actions, current-run future measurements, source/current wire currents,
and cross-row information are forbidden.

## Independent implementation and determinism

The independent tool must be implemented separately from the primary output
aggregator. It must authenticate source files and raw, rebuild the fixed
matrix, re-index the D1R1 actual-coordinate rows, recompute Decimal symmetry,
rank/condition/novelty, reconstruct the 18 contexts from D1R2 raw, rebuild all
108 specs, and compare the canonical ordered spec digest.

Run D1R7 twice in distinct new output directories. Detailed, summary,
candidate-spec, manifest, and independent outputs must be byte-identical.

## Frozen routes

```text
source/raw/hash/failure-class mismatch
  TEMPORAL_BASIS_SUBSTITUTION_SOURCE_STOP

matrix, static action, exactness, rank, condition, novelty, or spec mismatch
  TEMPORAL_BASIS_SUBSTITUTION_PREFLIGHT_FAIL_REDESIGN_REQUIRED

all primary and independent gates pass twice byte-identically
  TEMPORAL_BASIS_SUBSTITUTION_PREFLIGHT_PASS_REAL_SENTINEL_DESIGN_REQUIRED
```

No route authorizes D1R8 execution directly. A passing result permits only a
separately frozen D1R8 real-TSC safety-sentinel design. The full replacement
campaign, model fitting, MPC, expert data, BC, DAgger, and bounded residual RL
remain prohibited.
