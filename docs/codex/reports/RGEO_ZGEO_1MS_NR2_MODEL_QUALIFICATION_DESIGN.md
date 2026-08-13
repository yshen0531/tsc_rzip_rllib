# R_geo/Z_geo 1 ms NR2 structural-actuator model qualification

Status: prospectively frozen before implementation and before any NR2 TSC
plant advance on 2026-08-13 Asia/Shanghai.

## 1. Scope and evidence boundary

```text
contract             rgeo-zgeo-1ms-nr2-v1
campaign             rgeo_zgeo_1ms_nr2_structural_residual_v1
intended use         identification
fixed source         1100 ms
control period       1 ms
single-turn limit    |delta I_i| <= 0.3 A per step, equality allowed
prediction horizon   16 steps / 16 ms
```

NR2 may collect one fresh finite dataset and compare history-conditioned
predictive model classes. It may qualify only finite same-source recursive
prediction and calibrated uncertainty. It does not implement a controller,
reference governor, NMPC, Oracle, RL or expert data.

No NR0/NR1-family record, old 10 ms NR2 raw, historical probe, sentinel or
audit trajectory may enter fitting, normalization, calibration or evaluation.
Every new trajectory and artifact is declared `identification` before
collection and remains ineligible for retrospective expert labels.

## 2. Structural actuator and causal inputs

The old 10 ms NR2 required every candidate to learn recursive coil-current
readback and failed only that gate. NR1R2 then proved that Card15 command and
TSC readback are distinct exact coordinates. NR2 therefore separates them.

At each independent reset, compute in exact decimal arithmetic:

```text
bias_i = source_readback_i - source_active_Card15_command_i
predicted_readback_i[k+1] = issued_Card15_target_i[k] + bias_i
```

This structural propagation is not fitted. Every collected successor must
match it within `1e-9 A`; otherwise the campaign stops as an actuator-interface
failure. Command-to-command and readback-to-readback slew remain separate
exact-decimal `<=0.3 A` gates. There is no software queue and the qualified
effect state is k+1.

The learned output is only the next delta of `(R_geo, Z_geo, Ip)`. Each causal
input frame contains:

- current paired-boundary `R_geo/Z_geo`, same-state Ip and validity;
- all 14 actual current readbacks;
- all 14 next exact Card15 command increments relative to the active command;
- time since 1100 ms and continuous `R_geo-R_mid`;
- the uninterrupted preceding frame history.

Future reference, future state, outcome, trajectory/split ID, source result,
magnetic axis, centroid, hidden TSC state and post-effect future readback are
forbidden. R_mid crossing never resets history.

## 3. Frozen data split and budget

The complete matrix has 18 deterministic base sequences and exact sign mates:

| split | pairs | trajectories | advances | role |
|---|---:|---:|---:|---|
| development | 10 | 20 | 320 | fit and within-class selection |
| calibration | 4 | 8 | 128 | interval scaling only |
| fresh holdout | 4 | 8 | 128 | one final evaluation |
| total | 18 | 36 | 576 | hard maximum |

All 16 transitions and 17 states of both sign mates stay in one split and one
development fold. Step-level splitting is forbidden. Holdout TSC remains
locked until development/calibration raw passes independent audit and all
normalizers, hyperparameters, seeds, weights, uncertainty rules and hashes
are frozen.

The projected raw footprint is about 37 GB, below the read-only preflight's
237 GB available space. Stop before collection if available space falls below
80 GB. Raw stays on the server; no archive is created.

## 4. Prospective exact-Card15 excitation

Every trajectory first issues q0 at step 0, separating the source command
lattice from subsequent targets. Deterministic SHA-256 bits generate 14-coil
directions. For each sign and coil, construct the largest representable
Card15 displacement from q0 not exceeding the declared amplitude; never clip
or substitute after seeing TSC response.

Amplitude classes are:

```text
full       <= 0.30 A from q0
half       <= 0.15 A from q0
```

All components must be nonzero. Pair mates negate the requested direction,
and every split's quantized command-increment matrix must have rank 14.

The 16-step schedule type is `pair_index mod 3`:

1. `impulse`: q0, then four full one-step pulses at steps 1/5/9/13 with q0
   returns between and after them;
2. `dwell`: q0, one half-amplitude four-step dwell, four q0 steps, a second
   half-amplitude four-step dwell, then three q0 steps;
3. `switch`: q0, six half-amplitude two-step direction blocks, then three q0
   steps.

Offline validation must prove every adjacent command transition and
source-to-q0 transition is exactly representable, inside absolute current
limits and at most 0.3 A. Switching directly between half targets may use the
full 0.3 A bound; no hidden reserve is imposed.

## 5. Safety, raw and stage ordering

At every state retain the NR1R2 paired-boundary/limiter/Ip parser and these
campaign stop bounds:

- exact command and observed-current step `<=0.3 A` and structural readback
  error `<=1e-9 A`;
- configured absolute current limits and exact expected Card15 fields;
- no nonzero TSC return, abnormal output, solver/saturation indication,
  non-finite field or missing required artifact;
- R_geo between same-state limiter midplane intersections;
- `|R_geo-R_geo(1100)| <= 0.05 m` and
  `|Z_geo-Z_geo(1100)| <= 0.05 m`;
- Ip sign retained and `|Ip-Ip(1100)| <= 10% |Ip(1100)|`.

A pre-step failure issues nothing. A post-step failure records the successor,
performs no later advance and stops the entire phase. No amplitude adaptation,
replacement trajectory or resume under changed semantics is allowed.

Each state preserves inputa, geqdsk, restart, coil/wire CSV and hashes. A
structurally independent raw parser must reproduce specifications, exact
commands, readbacks, structural bias, timing, safety, counts and split ranks.

Stage order:

1. design and deterministic spec committed;
2. local and installed-server tests plus zero-TSC offline gate pass;
3. collect development/calibration only, at most 448 advances;
4. independent raw audit, fit and freeze candidates/calibration;
5. if at least one class is eligible, create hash-bound holdout authorization;
6. collect fresh holdout once, at most 128 advances;
7. independent raw audit and one frozen evaluation.

## 6. Fair model comparison

The common low-order baseline is a standardized ridge ARX using at most eight
causal frames. Ridge candidates are `1e-6`, `1e-4`, `1e-2`. Neural candidates
are `ARX + residual GRU`, `ARX + residual LSTM`, and `ARX + residual causal
TCN`; they predict only the three-output one-step residual left by the fold's
ARX. Widths `8` and `12` are compared. No neural class receives extra fields,
future labels or teacher-forced state during recursive evaluation.

Development selection uses five grouped folds by complete pair. Final
ensembles use deterministic seeds `1701..1705` and trajectory bootstraps.
Neural models use CPU deterministic algorithms, at most 10,000 trainable
parameters, Adam `1e-3`, gradient norm cap 1.0, at most 2,000 epochs and
patience 200. Normalizers use development only.

All point selection and evaluation use free recursive 16-step rollout. The
known future Card15 sequence drives the structural current path; predicted
plasma state feeds the model's later history. Calibration may scale only
predefined per-horizon ensemble/residual intervals and cannot alter weights or
point predictions.

Prospective point scales are:

```text
R_geo    0.0015 m
Z_geo    0.0015 m
Ip       150 A
```

Report recursive metrics at horizons 1, 4, 8 and 16. A class is holdout-
eligible only if calibration has at least 90% joint coordinate coverage and
maximum 16-step interval half-width no larger than
`0.004 m / 0.004 m / 400 A`.

Final fresh-holdout qualification requires:

1. no invalid/non-finite recursive prediction;
2. at least 90% of all recursive rows jointly within the point scales;
3. p95 maximum-coordinate scaled error `<=1` over all rows;
4. at every reported horizon, p95 maximum-coordinate scaled error `<=1.25`;
5. at least 90% joint calibrated interval coverage;
6. interval half-width caps above; and
7. structural current propagation error `<=1e-9 A` on every row.

Choose the passing class with lowest mean squared scaled error. A neural
residual may displace passing ARX only with at least 15% lower MSE and no worse
joint coverage or p95 scaled error; otherwise select ARX. No candidate may be
enlarged and no gate may be relaxed after holdout.

## 7. Routes and claim boundary

```text
offline/spec failure          ONE_MS_NR2_OFFLINE_FAIL_NO_TSC
safety/interface failure      ONE_MS_NR2_SAFETY_FAIL_STOP
dev/cal raw failure           ONE_MS_NR2_DEV_CAL_AUDIT_FAIL
no calibrated candidate       ONE_MS_NR2_CALIBRATION_FAIL_NO_HOLDOUT
holdout raw failure           ONE_MS_NR2_HOLDOUT_AUDIT_FAIL
no holdout winner             ONE_MS_NR2_MODEL_COMPARISON_FAIL_REDESIGN
qualified winner              ONE_MS_NR2_CAUSAL_MODEL_QUALIFIED
```

A PASS establishes only finite 16 ms same-source prediction under the frozen
excitation envelope. It does not establish a controller, long-horizon
accuracy, different-history restart, cross-R_mid coverage, planning authority,
recursive feasibility, tracking, Oracle, real-machine safety or global
reachability. NR3 requires a separate prospective design and authorization
boundary even after PASS.
