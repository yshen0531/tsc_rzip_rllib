# CURRENT_TASK.md — Stage4.2R3c4 restart-integrated deadline MPC

## 1. Certified checkpoint

Terminology:

```text
R1  = Stage4.2R1 authentic TSC plant-state restart
R17 = Stage4.1R17 frozen finite static-grid controller source
```

Certified foundations:

```text
Stage4.1R17 finite clean static grid                    18/18
Stage4.2R1c authentic plant-state restart               18/18
Stage4.2R2 causal controller-state restart              18/18
Stage4.2R3c3 bounded local response identification     256/256
```

Frozen development control results:

```text
R3b fresh phase-zero control                  0/32
R3c ideal-visible phase alignment            20/32
R3c1 authenticated R17 R/Z/Ip alignment      16/32
R3c2 zero-nominal restart regulator          12/32
```

R3b, R3c, R3c1, R3c2, and R3c3 are immutable. Do not overwrite, relabel, or
weaken their gates.

## 2. R3c3 final forensic conclusion

Exact run:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3_runs/
stage4_2r3c3_restart_task_clock_local_response_identification_20260730_182427
```

Independent raw result:

```text
raw / success / exact restart / causal probe       256/256
central-symmetry groups                             128/128
matched-hidden-history groups                         64/64
conditioned rank-4 response groups                    32/32
maximum condition number                              8.0984
maximum current utilization                           0.3904
runtime / restart / causality / solver errors              0
statistics/reporting errors                               0
```

Load-bearing evidence:

```text
run inventory
  1048 files / 25,371,364 bytes
  ef377ce1367d7a969b8f90cdb247445106f50b8706146f4c97b312892e909754

raw inventory
  256 files / 8,933,607 bytes
  88bcd02a5dd2ec4def60c1f2e7f2304fb57859836d3b9a34b090bfd91e00e563

server audit SHA-256
  5172fc54a8446418bbcccd31c84515f62ad2594a52904b831a3b2064d52a44b4

independent raw forensics SHA-256
  1a1d1acb2b6401a726a5e313301d9a37643cf023b4d2013a9f9c37e23f8a097b

formal report
  docs/codex/reports/STAGE4_2R3C3_FORENSIC_REPORT.md
```

R3c3 validates only a bounded local response envelope on the locked
development bank. It does not validate a successful restart MPC, independent
new hidden histories, or new targets. Its 125/256 formal probe result is
diagnostic and is not a controller pass rate.

## 3. Active task

Build Stage4.2R3c4 as a new experiment identity:

```text
purpose
  restart-integrated target-conditioned deadline MPC

source nominal controller
  exact R3c1 authenticated visible-manifold controller

response source
  compact authenticated model recomputed from all R3c3 raw on the server
```

Before controller implementation:

1. Recompute a compact response bank server-side from all 256 R3c3 raw
   trajectories.
2. Authenticate its raw inventory, R3c1 baselines, context identities,
   signed-pair construction, probe amplitudes, first-effect clocks, and
   response-gate metrics.
3. Download only the compact response bank and its inventory/hash.
4. Write and commit
   `docs/codex/reports/STAGE4_2R3C4_PREREGISTERED_DESIGN.md`.
5. Freeze controller identity, optimization variables, objective, bounds,
   fallback semantics, offline gates, task matrix, and acceptance gates
   before any R3c4 real TSC run.

Then implement, test, deploy, run, postprocess, download compact evidence, and
complete independent raw forensics.

## 4. Mandatory R3c4 controller constraints

R3c4 may use only:

- current and past visible R/Z/Ip and coil-current measurements;
- target R/Z/Ip;
- causal actuator delay/gain/slew estimates available at task start;
- the exact R3c1 target-conditioned nominal controller;
- the frozen bounded R3c3 response bank.

Forbidden controller inputs:

- source actions or source results;
- future measurements, actions, or actuator states from the current run;
- source or current full wire/vessel current;
- pair, hidden-history, common-prefix, source-experiment, pass/fail, or
  result labels;
- raw R3c3 trajectory identity;
- any post-action telemetry unavailable at decision time.

The optimization must be causal, finite, bounded inside the authenticated
response envelope, and solved online. A solver failure must use a
prospectively frozen safe fallback and must be reported separately.

R3c3 probe trajectories are not demonstrations and may not enter an MPC
expert, BC, DAgger, or RL dataset.

## 5. Immutable formal contract

```text
slew 1.0:
  arrive no later than 250 ms
  hold/evaluate through 350 ms

slew 0.9:
  arrive no later than 270 ms
  hold/evaluate through 370 ms

R/Z tolerance                 30 mm
speed threshold               0.1 m/s
Ip thresholds                 frozen
arrival streak                frozen
```

R3c4 may not extend a deadline, weaken a threshold, select a later endpoint,
or turn a longer horizon into additional allowed arrival time.

## 6. Required validation and evidence loop

Before real TSC:

- Python compile and all repository JSON parse;
- focused and complete unit tests;
- import closure and package checksum verification;
- exact R3b/R3c1/R3c2/R3c3 source fingerprints;
- exact compact response-bank fingerprint;
- controller-input and future-information guards;
- response-envelope and optimizer-bound tests;
- source-fingerprint and resume-compatibility tests;
- empty-directory direct-copy deployment simulation;
- server preflight, `bash -n`, import, compile, package, and complete tests;
- offline exact R3c1 baseline preservation;
- offline finite causal R3c4 action computation in every context;
- hidden-wire and pair/history-label invariance;
- zero raw and no real TSC in the offline phase.

Execution loop:

```text
freeze compact response bank and preregister design
→ implement and validate locally
→ transfer directly without archives
→ validate staging and canonical server trees
→ run offline no-TSC gate
→ start one new R3c4 real identity
→ monitor exact PID/task/raw/log state
→ postprocess all large raw server-side
→ download compact evidence only
→ independently recompute raw-derived metrics
→ write the final forensic report
```

## 7. Advancement

R3c4 is accepted only if every preregistered development context:

- executes successfully with exact plant restart and controller causality;
- remains inside all controller and actuator bounds;
- satisfies the unchanged formal timing contract.

A partial result is a failed development controller, not a basis for weaker
gates.

Only after R3c4 closes the locked development bank may the project create a
new independent-history/different-initial-state confirmation stage. New
targets, continuous actuator/plant variation, noise, disturbance recovery,
and independent long hold still follow in order.

BC, DAgger, and bounded residual RL remain prohibited.
