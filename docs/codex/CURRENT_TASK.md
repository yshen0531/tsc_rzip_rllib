# CURRENT_TASK.md — Stage4.2R3b confirmatory hidden-history robustness

## 1. Current evidence checkpoint

Stage4.2R1 means the Stage4.2R1 authentic plant-state restart experiment.
Stage4.1R17 means the frozen Stage4.1R17 finite static-grid controller source.

Certified foundations:

```text
Stage4.1R17 finite clean static grid         18/18
Stage4.2R1c authentic plant-state restart    18/18
Stage4.2R2 causal controller-state restart   18/18
minimum frozen formal signed margin          1.0456920999768471e-05
```

R2 exact run:

```text
branch
  codex/stage4_2r2-controller-checkpoint

code commit
  84962ef

controller revision
  persistent_mpc_controller_checkpoint_replay_v42r2

package revision
  r42r2_persistent_controller_checkpoint_v1

remote run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r2_runs/
  stage4_2r2_persistent_controller_checkpoint_replay_20260730_082250
```

R3 completed 54/54 authentic state rollouts and 54/54 snapshots. Its
adjacent reversed pulses produced at most 0.048 A of hidden difference, so
0/27 pairs met its frozen 1,000 A gate. Control was `not_run`.

R3a then completed:

```text
real-TSC state rollouts                     72/72
valid snapshot inventories                  72/72
candidate pairs                             36/36
visible-matched pairs                       24/36
different-initial-state pairs               36/36
hidden-separated under frozen 1.0 A gate     0/36
conditional control                         not_run
runtime/deployment/corruption errors         0
```

R3a delayed pulses increased the maximum hidden difference to 0.527 A.
Independent same-clock cross-pair recomputation found no visible-matched
pair above 1.0 A. This is an experimental-design/threshold-calibration
failure, not a code-unit bug, runtime failure, plant-restart failure, or real
closed-loop control failure.

Exact R3a evidence:

```text
implementation commit
  8a3eb670e9db210594f21260c2391cea0a32a255

remote run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3a_runs/
  stage4_2r3a_delayed_counterpulse_hidden_history_initial_state_20260730_110128

run inventory digest
  9be432ee725035b31cee32f9415298aacd1fa576e24190588b8ef2c2be08eae7

report
  docs/codex/reports/STAGE4_2R3A_FORENSIC_REPORT.md

compact evidence
  docs/codex/audits/stage4_2r3a_result_20260730_110128/
```

R3 and R3a remain failed under their original gates. Their results must not
be retroactively relabeled.

## 2. Active task

The active task is Stage4.2R3b. Its prospective design is frozen in:

```text
docs/codex/reports/STAGE4_2R3B_PREREGISTERED_DESIGN.md
```

Implement R3b as a complete standalone package, validate it locally and in
an empty deployment directory, deploy it directly without archives, validate
the staging and canonical server trees, run the no-gotsc gate, then execute
the real-TSC state and conditional control campaign.

R3b must use:

```text
new common-prefix lengths                   5, 9
nullspace directions                        1, 2
new amplitude fractions                     0.60, 0.75, 0.90
inter-pulse gaps                            2, 3, 4
settle steps                                4
history orders                              plus-first, minus-first
candidate pairs                             36
state rollouts                              72
selected pairs if state gate passes          4
conditional control rollouts                32
```

The material hidden-state gate is:

```text
48-wire maximum absolute difference         >= 0.25 A
48-wire vector RMS difference               >= 0.10 A
relative RMS difference                     >= 0.05
```

The visible matching gates and different-initial-state gates are unchanged.
One valid pair is required from each prefix-by-direction stratum. Selection
must finish before any control outcome exists.

## 3. Source, fingerprint, and causality requirements

Before real TSC:

- authenticate prefix-5 and prefix-9 actions against the same frozen nominal
  delay-0/slew-1.0 R17 source;
- validate the exact R3a calibration run, its complete inventory digest, and
  the independent raw-forensics hash;
- include config, module, launchers, package, R2/R1/R17 source, R3a
  calibration, common-prefix, and state-spec fingerprints in manifest and
  resume compatibility checks;
- run compile, all JSON parse, focused/full tests, import closure, package
  hashes, source/resume tests, and an empty-directory deployment simulation;
- run the independent no-gotsc frozen-controller recomputation audit;
- execute all 72 state tasks before pair selection;
- reject a partial or incompatible state grid.

The controller may receive only causal R/Z/Ip observations and the R2
checkpoint schema. Full 48-wire current is pairing/audit telemetry only and
must not be controller input.

## 4. Required result classification

Every result must distinguish:

```text
runtime/environment error
deployment/package/import error
raw/snapshot corruption
summary/statistics/reporting bug
invalid pair or experimental-design flaw
observer/history-identification failure
plant-restart fidelity failure
real closed-loop control failure
finite-envelope success
unvalidated extrapolation
```

An unrun phase is `not_run`, never pass or fail. A server audit integrity
`passed=true` is not itself an experiment PASS.

## 5. Immutable formal contract

```text
slew 1.0 or 1.1:
  arrive no later than 250 ms
  hold/evaluate through 350 ms

slew 0.9:
  arrive no later than 270 ms
  hold/evaluate through 370 ms
```

R/Z tolerance, speed threshold, Ip threshold, and arrival streak remain at
the frozen baseline. Longer horizons do not move the arrival deadline.

## 6. Server and evidence rules

Use `tsc-airgap` by default. If alias resolution fails, use only the exact
fixed public-key fallback documented in `SERVER_WORKFLOW.md`; never inspect
the key or SSH configuration.

Large raw, JSON.GZ, snapshot, and trajectory trees stay on the server:

1. preserve the raw tree;
2. run a read-only postprocessor in the canonical project with the existing
   virtualenv;
3. parse/hash every required raw/snapshot input and recompute metrics;
4. download only compact audit JSON/CSV, manifests, hash inventories, and
   logs;
5. verify compact local counts, sizes, and SHA-256 values.

No local compression or extraction is allowed.

## 7. Advancement rule

If R3b genuinely validates finite-envelope hidden-history and different-
initial-state control, proceed next to new preregistered targets. Then
continue through continuous actuator and plant/Jacobian variation,
measurement noise/observer robustness, disturbance recovery, and independent
long hold.

BC, DAgger, and bounded residual RL remain prohibited until the MPC expert is
reliable across restart, hidden history, initial state, continuous
parameters, noise, and disturbance recovery.
