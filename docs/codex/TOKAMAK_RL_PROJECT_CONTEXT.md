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

## 5. Certified restart foundations

Stage4.2R1 means authentic TSC plant-state restart action replay. Its R1c
result is certified for all 18 finite clean same-source cases:

- exact source-action capture;
- authentic snapshot at 200 ms elapsed / 1300 ms absolute TSC time;
- 18 complete manifests and 144 payload files;
- exact 14-coil and full 48-wire state;
- 18 fresh TSC restart suffixes;
- exact visible, action, and full-wire suffix;
- immutable formal contract 18/18.

R1 intentionally restored no controller state.

Stage4.2R2 then persisted causal controller state: observer history,
integrator, previous correction, pending delay queue, trusted calibration,
modeled delay/slew, controller phase, and source/code fingerprints. It stored
no future action or measurement. The offline gate recomputed 282 suffix
actions exactly, and 18 fresh controller/TSC processes reproduced online
actions, visible state, and full-wire state exactly while preserving the
formal contract 18/18.

Both results are finite same-source restart foundations, not robustness
claims. Their global minimum formal signed margin is only
`1.0456920999768471e-05`.

## 6. Current near-term objective

Stage4.2R3 and R3a completed 54/54 and 72/72 authentic state-generation
rollouts respectively, without runtime or corruption errors. Both remain
failed under their original preregistered hidden-state gates and neither ran
conditional control. R3a did establish that common expert prefixes generate
different authenticated initial-state groups and that delayed counter-pulses
produce a measurable hidden-history difference up to 0.527 A.

Stage4.2R3b is the prospectively gated confirmation experiment. It uses new
prefix lengths and pulse amplitudes, requires all 72 new state rollouts, and
selects one valid pair from each prefix-by-direction stratum before any
conditional control may run.

The pair-generation method, visible matching tolerances, calibrated material
hidden-state separation, safety rules, source fingerprints, and unchanged
formal gates are frozen in
`docs/codex/reports/STAGE4_2R3B_PREREGISTERED_DESIGN.md`.
Full wire state remains audit evidence and must not leak into controller
input. Invalid pairing, observer/history-identification failure, plant
restart failure, and real control failure must be separated.

## 7. Medium-term objectives

After hidden-history and different-initial-state robustness:

1. multiple authenticated restart times;
2. new preregistered R/Z/Ip targets not used for policy selection;
3. bounded plant/Jacobian mismatch;
4. continuously varying delay, gain, and slew rather than a static bank;
5. measurement noise and observer robustness;
6. disturbance injection and recovery;
7. independent long-hold tests after formal arrival, with horizon chosen from
   dynamics rather than route drift.

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
