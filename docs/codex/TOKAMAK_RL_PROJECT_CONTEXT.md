# TOKAMAK_RL_PROJECT_CONTEXT.md

## 1. Project identity

Repository:

```text
https://github.com/yshen0531/tsc_rzip_rllib
```

Local development is performed in the VS Code workspace on Windows. The server has a same-name working project but is not Git-managed.

Primary code areas:

```text
configs/
scripts/
tsc_rzip_rllib/
tests/
current-stage root .sh files
```

Historical code and output may be read only when required as scientific source evidence.

## 2. Server environment

```text
SSH alias:             tsc-airgap
actual login:          yangshen0711@10.10.60.108
expected HOME:         /home/yangshen0711
remote project:        $HOME/tsc_all/tsc_rzip_rllib
remote staging root:   $HOME/tsc_software
Python virtualenv:     $HOME/tsc_all/tsc_simulation/venv_simu
root access:           no
outbound internet:     no
server Git usage:      no
```

The remote staging root and project root are not interchangeable. Verify both before work. Run the project from `$HOME/tsc_all/tsc_rzip_rllib`.

Typical historical run pattern:

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib
source /home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/activate
chmod +x ./*.sh
./run_<stage>_nohup.sh
```

Use the exact launcher for the current stage.

## 3. Transfer constraint

Windows local files must not be compressed or extracted. Transfer directly with `scp`/`sftp`.

Do not use ZIP/TAR/7z as an intermediate representation.

For a clean server code replacement, transfer the complete current source directories and current-stage root files. Do not leave stale files in the four primary code directories.

## 4. Scientific history, condensed

### B99 and route change

The B99 series showed that pure actor-critic/MPO training directions were not reliable enough to own the full 14-coil control problem.

The route changed to:

```text
low-dimensional, evidence-backed MPC expert
→ imitation
→ bounded residual RL
```

RL must never restart from unconstrained direct ownership of the 14 coils.

### Stage1/1.1

- real TSC controllability analysis;
- three primary SVD control modes;
- frozen real TSC Jacobian: 175×105.

### Stage2

- low-dimensional CEM trajectory optimization.

### Stage3

- strict trajectories;
- long-hold work;
- goal-conditioned trajectory library;
- receding-horizon MPC;
- Stage3.4 goal-conditioned 350 ms MPC baseline.

### Stage4.1R3–R8

- R3 control-aware residual observer;
- delay-aware and gain/slew-aware control;
- finite weak-slew closure;
- confidence-gated delay/slew identification;
- exact persistent initialization reproduces Oracle;
- separate pre-control calibration;
- correction of queue bookkeeping and untrusted-default-start behavior.

### Stage4.1R9–R11

These stages explored terminal feedback and longer horizons.

Important route correction:

- 550 ms, 750 ms, and 2 s runs are diagnostics;
- they do not change the formal arrival deadline;
- a long observation window must be separated from the arrival specification.

### Restored formal timing

The immutable formal contract is:

```text
normal/strong slew:
  arrival by 250 ms
  hold through 350 ms

weak slew 0.9:
  arrival by 270 ms
  hold through 370 ms
```

The 30 mm R/Z, 0.1 m/s speed, and frozen Ip gates remain unchanged.

### Stage4.1R12–R17

The weak-slew delay=1/2 failures were investigated without changing formal time.

Key findings:

- post-deadline damping cannot repair a metric already failed at the deadline;
- early braking must be delay-pipeline aware;
- handoff that discarded target-conditioned nominal control/integral state was flawed;
- the 175×105 model did not cover all state-36/37 tail dynamics;
- bounded local response probes were used;
- small-signal superposition was validated;
- large-amplitude bidirectional symmetry was not validated;
- one-sided braking remained predictable and monotonic.

Frozen Stage4.1R17 finite baseline:

```text
18/18 formal finite static-grid cases
delay=1 weak-slew patch: 6× one-sided braking
delay=2 weak-slew patch: 7× one-sided braking
trusted calibration token exact replay: yes
```

Limitations:

- same clean digital twin;
- only two targets;
- discrete static delay/slew grid;
- no authentic restart;
- no unseen hidden history;
- no continuous parameter changes;
- no plant/Jacobian mismatch;
- no measurement-noise robustness;
- no disturbance recovery;
- no deployment claim.

The global minimum formal margin is very thin in at least one unchanged source case, so finite-grid PASS is not broad robustness.

## 5. Current Stage4.2R1 purpose

Current work isolates authentic TSC plant-state restart.

R1 source is the frozen R17 formal expert.

R1 should:

1. replay exact source actions;
2. capture at elapsed 200 ms;
3. export authentic snapshot files;
4. preserve full coil and full wire/vessel-current state;
5. start a fresh TSC process from snapshot;
6. replay the remaining source action suffix;
7. compare visible state, coil currents, full wire currents, and action alignment;
8. recombine prefix and suffix without duplicate/missing states;
9. reevaluate the original formal timing contract.

R1 intentionally does not restore controller internal state. It is an action-replay plant test.

R1 must report separately:

```text
plant_restart_fidelity
formal_contract_preservation
```

### Known R1/R1a history

Initial R1:

- 18 capture Ray tasks returned;
- at least one capture was non-comparable;
- old summary returned `inf`;
- strict JSON rejected Infinity and crashed.

R1a changed failure handling:

- preserve partial trajectory;
- preserve failure stage, reason, traceback, and snapshot path;
- use `null` plus mismatch reason rather than `inf`;
- create finite structured summaries/verdicts;
- reuse only complete successful raw plus valid snapshot;
- rerun failed/incomplete captures only.

The final R1a run has completed and its uncompressed logs/results are now local. The first Codex task is to analyze those real files. Do not assume whether plant restart passed or failed.

## 6. Near-term objectives

1. Forensically analyze final Stage4.2R1/R1a.
2. Determine exact capture success/failure distribution.
3. Validate snapshot inventory, hashes, manifests, coil vectors, and full wire vectors.
4. Determine whether fresh restart suffix tasks ran.
5. Separate snapshot/export failure, restart initialization failure, replay mismatch, and formal-gate failure.
6. Fix only proven code bugs.
7. If plant restart is authenticated, advance to controller-state restart.
8. If plant restart fails, isolate the minimum reproducible cause before adding more robustness axes.

## 7. Medium-term objectives

After authentic plant restart:

1. Persist/restore observer history, integrator, previous correction, and pending delay queue.
2. Matched-visible-state / different-hidden-vessel-history testing.
3. Multiple restart times and different initial states.
4. New preregistered R/Z/Ip targets not used for policy selection.
5. Bounded plant/Jacobian mismatch.
6. Continuous delay, gain, and slew changes rather than a discrete static bank.
7. Measurement noise and observer robustness.
8. Disturbance injection and recovery.
9. Independent long-hold tests after formal arrival, with horizon chosen from dynamics rather than arbitrary route drift.

## 8. Long-term objectives

Only after the MPC expert is reliable:

1. Define expert dataset schema with full causal context and safety metadata.
2. Collect MPC expert trajectories across the validated envelope.
3. Behavior Cloning.
4. DAgger with safety shields and expert intervention.
5. Bounded residual RL.
6. Independent evaluation on unseen initial states, histories, targets, perturbations, and continuous parameters.
7. Deployment-oriented safety validation.

Bounded residual RL may correct a reliable MPC expert. It may not directly replace it or own all 14 coils without hard bounds.
