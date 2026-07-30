# Stage4.2R3b preregistered confirmatory hidden-history design

Preregistered: 2026-07-30 Asia/Shanghai

Status: fixed after final R3a forensics and before any R3b TSC result.

## 1. Identity and purpose

R3b is a new experiment identity. R3 and R3a remain failed under their
original frozen absolute hidden-state gates. R3b does not reuse an R3a
snapshot or reinterpret an R3a pair as a formal success.

R3b prospectively tests whether a new common-prefix and delayed-counterpulse
grid can generate:

1. pairs matched in every controller-visible endpoint channel;
2. materially different authentic 48-wire vessel/eddy-current states;
3. authenticated initial states different from the frozen R17 start; and
4. coverage of both new prefix lengths and both nullspace directions.

If and only if the complete state/pair gate passes, R3b starts the frozen
causal MPC expert independently from both members of every selected pair.

## 2. Calibration evidence and non-retroactivity

The calibration source is exactly:

```text
R3a run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3a_runs/
  stage4_2r3a_delayed_counterpulse_hidden_history_initial_state_20260730_110128

R3a run inventory digest
  9be432ee725035b31cee32f9415298aacd1fa576e24190588b8ef2c2be08eae7

R3a independent raw-forensics SHA-256
  3889ef0df2220a4ada253761535945c143f80bca1e0351e7ece0c380abc61e23
```

R3a established:

```text
raw/snapshot integrity                      72/72
endpoint wire RMS range                     1.225588-2.981651 A
observed raw wire-current increment         0.001 A
visible-matched R3a pairs above:
  max absolute >= 0.25 A
  vector RMS >= 0.10 A
  relative RMS >= 0.05                      6
```

R3b therefore freezes the following material hidden-state gate before any
R3b TSC result:

```text
wire-vector length                          exactly 48
maximum absolute full-wire difference       >= 0.25 A
RMS full-wire-vector difference             >= 0.10 A
relative RMS full-wire difference           >= 0.05
```

The absolute gate is 250 observed raw increments. The RMS and relative gates
require a distributed effect of at least 0.10 A RMS and at least five percent
of the pair endpoint scale; a single changed element cannot pass by itself.

This is a prospective R3b calibration. It does not change the R3a requirement
of 1.0 A or its failed result.

## 3. Independent common-prefix grid

Every state member starts from the same frozen TSC start folder. Its common
prefix comes from the authenticated nominal, delay-0, slew-1.0 R17 expert.

R3b uses prefix lengths not present in R3a:

```text
common prefix lengths                       5 and 9 action steps
```

The source experiment ID, maximum-prefix action digest, and the separate
prefix-5 and prefix-9 digests are frozen in every R3b spec and manifest.
Every prefix action must exactly match the authenticated source.

The two prefix groups must each pass the unchanged different-initial-state
gate against the frozen R17 start. Their selected-pair centroids must also
be mutually distinct by at least one of:

```text
R centroid difference                       >= 0.0005 m
Z centroid difference                       >= 0.0005 m
Ip centroid difference                      >= 2,000 A
14-coil centroid RMS difference             >= 500 A
```

## 4. Confirmatory delayed-counterpulse matrix

Use the same first two directions from the orthogonal complement of the
frozen three-mode controller basis:

```text
plus-first:
  +a*q, gap_steps zero actions, -a*q, 4 zero settle actions

minus-first:
  -a*q, gap_steps zero actions, +a*q, 4 zero settle actions
```

The requested net nullspace increment remains zero. R3b uses pulse
amplitudes absent from R3a and a denser short-gap region:

```text
nullspace directions                        1, 2
amplitude fractions                         0.60, 0.75, 0.90
inter-pulse zero gaps                       2, 3, 4 steps
common expert prefix lengths                5, 9 steps
post-counterpulse settle                    4 steps
history orders                              plus-first, minus-first
candidate pairs                             36
state-generation rollouts                   72
```

The pulse maximum is 0.90 normalized units and must remain within the
environment action bound. Common-prefix actions must also remain within the
bound.

No grid value may be changed after an R3b TSC result is observed.

## 5. Visible pair gate

The visible gate remains unchanged:

```text
absolute R difference                       <= 0.0005 m
absolute Z difference                       <= 0.0005 m
absolute Ip difference                      <= 2,000 A
absolute backward-difference vR difference  <= 0.02 m/s
absolute backward-difference vZ difference  <= 0.02 m/s
maximum 14-coil current difference          <= 2,000 A
RMS 14-coil current difference              <= 500 A
maximum endpoint action difference          <= 1e-12 normalized
same TSC transition count/snapshot clock    required
```

All 72 state tasks and all snapshot payload inventories must succeed. A
partial state grid cannot pass.

## 6. Selection without control leakage

The four strata are:

```text
(prefix 5, direction 1)
(prefix 5, direction 2)
(prefix 9, direction 1)
(prefix 9, direction 2)
```

Exactly one state-valid pair is selected from every stratum by:

1. largest relative RMS wire difference;
2. largest wire-vector RMS difference;
3. largest maximum absolute wire difference;
4. smallest visible maximum normalized ratio;
5. lower pulse amplitude;
6. longer gap;
7. lexical pair ID.

The state gate requires exactly four selected pairs, both prefix lengths,
both directions, four different-initial-state passes, and mutual prefix-group
centroid separation.

Selection may read only state-generation raw/snapshot evidence. It may not
read a control result.

## 7. Conditional control matrix

For each of the four selected pairs:

```text
history members                             plus-first, minus-first
targets                                     nominal, RZ_p10_m10
future actuator cases                       delay 0 / slew 1.0
                                             delay 2 / slew 0.9
rollouts per pair                           8
total control rollouts                      32
```

Every rollout starts:

- a fresh TSC process from the hash-verified snapshot;
- a fresh controller at task state index zero;
- measurement history containing only current R/Z/Ip;
- zero integral and previous correction;
- the frozen nominal delay-queue initialization;
- no full-wire input, future action, or future measurement.

The full wire vector remains post-action audit telemetry only.

For each selected pair, both history members must satisfy all four target/
actuator combinations. Pairwise comparison must report action divergence,
visible divergence, restart integrity, controller causality, and formal
contract results separately.

## 8. Formal gates and interpretation

Formal timing is unchanged:

```text
slew 1.0: arrive by 250 ms, hold/evaluate through 350 ms
slew 0.9: arrive by 270 ms, hold/evaluate through 370 ms
```

R/Z tolerance, speed threshold, Ip threshold, and arrival streak remain at
the frozen baseline.

Before real TSC, the fresh controller must reproduce all required frozen
expert actions exactly in a no-gotsc audit.

Possible outcomes must be classified separately:

```text
runtime/environment error
deployment/package/import error
raw/snapshot corruption
summary/statistics/reporting error
invalid state pair or design failure
observer/history-identification failure
plant-restart fidelity failure
real closed-loop formal-control failure
finite-envelope success
unvalidated extrapolation
```

If the state gate fails, control is `not_run`. If valid pairs restart but
their causal controller fails, that is a real finite-envelope controller
result, not a state-generation failure.

## 9. Fingerprints, resume, and evidence

The R3b manifest and resume checks must freeze:

- controller and package revisions;
- R3b config, module, launcher, and package fingerprints;
- R2/R1/R17 source fingerprint;
- exact R3a calibration-run identity and inventory digest;
- exact hash of the independent R3a raw-forensics artifact;
- common-prefix source experiment and prefix-5/prefix-9 action digests;
- complete R3b state-spec digest;
- pair gate and selection rule.

Resume must reject any mismatch.

The R3a calibration source is read-only. R3b must write a new run directory.
Large R3b raw JSON.GZ and snapshot trees remain on the server. An independent
server-side postprocessor must hash and parse the complete raw tree and
recompute all load-bearing metrics before compact evidence is downloaded.

## 10. Advancement rule

R3b can establish only finite-envelope hidden-history and different-initial-
state robustness over this preregistered matrix. It cannot establish unseen
targets, continuous actuator variation, plant/Jacobian robustness, noise,
disturbance recovery, or long hold.

Only after a valid hidden-history result may the project proceed to new
preregistered targets. BC, DAgger, and residual RL remain prohibited.
