# CURRENT_TASK.md — Stage4.2R3c visible-state phase-aligned MPC repair

## 1. Certified evidence checkpoint

Terminology remains:

```text
R1  = Stage4.2R1 authentic TSC plant-state restart
R17 = Stage4.1R17 frozen finite static-grid controller source
```

Certified foundations:

```text
Stage4.1R17 finite clean static grid         18/18
Stage4.2R1c authentic plant-state restart    18/18
Stage4.2R2 causal controller-state restart   18/18
minimum frozen formal signed margin          1.0456920999768471e-05
```

R3b completed its full preregistered campaign:

```text
state rollouts                                72/72
valid authentic snapshots                    72/72
candidate pairs                               36/36
visible-matched pairs                         16/36
hidden-separated pairs                        34/36
accepted pairs                                14/36
selected prefix-by-direction pairs              4/4
fresh restart control rollouts                32/32
formal control pass                            0/32
runtime/deployment/corruption errors               0
plant restart fidelity failures                   0
controller causality failures                     0
```

Exact R3b evidence:

```text
implementation commit
  8fb1534

remote run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3b_runs/
  stage4_2r3b_confirmatory_hidden_history_initial_state_20260730_115526

run inventory digest
  301a3ad2be01c83209d8e260c1a8c80f090d01afafb9c173f63cf9219caac8fc

independent raw forensics SHA-256
  975205eff41f62d319e4f6e22643bb687461e42d3c73c1d09f0424f2a7c5cf32

report
  docs/codex/reports/STAGE4_2R3B_FORENSIC_REPORT.md

compact evidence
  docs/codex/audits/stage4_2r3b_result_20260730_115526/
```

R3b state construction passed, but hidden-history control did not. The result
must not be relabeled as success.

## 2. R3b diagnosis

The R3b fresh controller reset both task time and its R17 nominal reference to
step zero. Raw restart states were closest to R17 visible phases 12--20:

```text
controller nominal start phase                    0
nearest visible source phase                  12--20
first action difference from source phase 0   0--0.0163
first action difference from nearest phase    0.9019--1.4371
```

All nominal cases began inside the 30 mm R/Z box. Offset-target cases entered
by 50--80 ms. All 32 cases then left the box by 80--110 ms and ended at
149--223 mm box error. Position and speed failed in 32/32 cases. Original-
start R17 sources for the same specifications remained 32/32 formal PASS.

This is a controller-design failure: the frozen controller is a time-indexed
trajectory follower without causal visible-state phase alignment or
state-aware replanning. It is not a plant-restart failure.

The R3b summary field
`observer_or_history_identification_failure_count=0` is not evidence of
observer success. Both members failed every pair group under a common-mode
controller failure, so history sensitivity was masked. New summaries must
report that state as inconclusive.

## 3. Active task

Implement Stage4.2R3c as a new controller and experiment identity. R3c is a
development-stage repair on the exact locked R3b selected snapshots. It must
not regenerate R3b results or rewrite the R3b summary.

The prospective design is frozen in:

```text
docs/codex/reports/STAGE4_2R3C_PREREGISTERED_DESIGN.md
```

R3c must:

- authenticate the exact R3b run inventory, audit, raw-forensics hash, four
  selected pair identities, and all eight selected snapshot manifests;
- receive only current/past visible R/Z/Ip and coil currents;
- never expose 48-wire hidden state to phase selection or control;
- choose a causal R17 nominal phase from the initial visible state;
- keep controller task time and formal timing at zero;
- align the nominal reference, model/Jacobian phase, delay-queue priming, and
  braking/terminal phase transitions consistently;
- preserve zero fresh integrals, zero previous correction, and empty visible
  history except for the current state;
- run an offline no-gotsc original-start preservation gate;
- execute the unchanged 32-case R3b development matrix under the new
  controller identity;
- separately report runtime, restart, causality, formal control, and
  masked/assessed hidden-history outcomes.

## 4. Formal and scientific constraints

The formal contract is immutable:

```text
slew 1.0 or 1.1:
  arrive no later than 250 ms
  hold/evaluate through 350 ms

slew 0.9:
  arrive no later than 270 ms
  hold/evaluate through 370 ms
```

R/Z tolerance, 0.1 m/s speed threshold, Ip thresholds, and arrival streak are
unchanged. R3c may not move the formal clock to the selected nominal phase.

R3c reuses snapshots after observing R3b. Therefore:

- R3c is controller-development evidence only;
- an R3c PASS does not independently validate hidden-history robustness;
- a successful R3c must be followed by R3d with new preregistered, unseen
  histories and initial states;
- new targets and continuous parameter work remain blocked until R3d.

## 5. Required validation and server loop

Before real TSC:

- Python compile and all JSON parse;
- focused and complete tests;
- import closure and package hash verification;
- source fingerprint and resume compatibility tests;
- empty-directory deployment simulation;
- no undeclared external source dependency;
- exact remote path preflight;
- server `bash -n`, package verification, import/compile, and complete tests;
- offline original-start source preservation;
- offline proof that no hidden wire or current-run future value enters phase
  selection or action computation.

Then:

```text
deploy directly without archives
→ validate staging and canonical server trees
→ run offline gate
→ safely resume the same identity for 32 real-TSC controls
→ postprocess raw on the server
→ download only compact audit/results/logs
→ verify hashes
→ write the final R3c forensic report
```

Large raw JSON.GZ and snapshot trees stay on the server.

## 6. Advancement rule

If R3c fails, preserve its raw evidence and create a new controller revision;
do not weaken the gate or overwrite R3c.

If R3c passes all 32 development cases, proceed to an independently
preregistered R3d with newly generated unseen hidden histories and initial
states. Only a successful independent confirmation can unblock new target,
continuous actuator/plant, noise, disturbance, and long-hold work.

BC, DAgger, and bounded residual RL remain prohibited.
